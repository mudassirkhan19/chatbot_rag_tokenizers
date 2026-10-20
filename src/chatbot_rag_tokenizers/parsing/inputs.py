"""The files a parse run reads, each with the pinned id its Chunks cite and its sha256."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..collection.fulltext import FulltextRecord, pinned_id_of_file
from ..collection.manifest import read_manifest
from .chunker import ParsedFile

# A Seed PDF is named "<seed>_<pinned id>.pdf", e.g. "bpe-dropout_1910.13267v1.pdf".
SEED_NAME = re.compile(r"[a-z0-9-]+_(?P<pinned_id>\d{4}\.\d{4,5}v\d+)")
VERSION = re.compile(r"\d{4}\.\d{4,5}(?P<version>v\d+)")


@dataclass(frozen=True)
class InputFile:
    path: Path
    identity: ParsedFile
    pdf: bytes


class NotFiles(ValueError):
    """Paths passed by hand that aren't files, each with what is there instead, worded for the person running it."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        count = "1 path given with --files isn't a file" if len(problems) == 1 else f"{len(problems)} paths given with --files aren't files"
        super().__init__("\n".join([f"{count}; nothing was parsed:", *(f"  {problem}" for problem in problems)]))


def from_paths(paths: list[Path]) -> list[InputFile]:
    """Files passed by hand (`--files`): the pinned id comes from the name, the hash from the bytes.

    A Seed name drops its prefix; any other name is taken as the file name `fetch` gives a pinned id. With no
    record to name the Edition, it is taken the way `fetch` pins one: an arXiv Version's Edition is the latest
    Version of the same arXiv id among the files given, and any other file is its own Edition.

    Raises NotFiles, before any file is read, when a path is missing or isn't a file: the files given decide
    each other's Editions, so none is parsed until every one is there.
    """
    problems = [f"{path}: {'a directory' if path.is_dir() else 'no such file'}" for path in paths if not path.is_file()]
    if problems:
        raise NotFiles(problems)
    named = []
    for path in paths:
        pdf = path.read_bytes()
        seed = SEED_NAME.fullmatch(path.stem)
        named.append((path, pdf, seed["pinned_id"] if seed else path.stem))
    editions = editions_by_name([pinned_id for _, _, pinned_id in named])
    return [
        InputFile(path, ParsedFile(editions[pinned_id][0], pinned_id, editions[pinned_id][1], hashlib.sha256(pdf).hexdigest()), pdf)
        for path, pdf, pinned_id in named
    ]


def editions_by_name(pinned_ids: list[str]) -> dict[str, tuple[str, str]]:
    """The (Edition id, Version) of each pinned id of files passed by hand, the way `from_paths` takes them: an arXiv
    Version's Edition is the latest Version of the same arXiv id among them, and any other id is its own Edition."""
    versions = {pinned_id: versioned["version"] if (versioned := VERSION.fullmatch(pinned_id)) else "" for pinned_id in pinned_ids}
    latest: dict[str, str] = {}
    for pinned_id, version in versions.items():
        arxiv_id = pinned_id.removesuffix(version)
        if version and int(version[1:]) > int(latest.get(arxiv_id, "v0")[1:]):
            latest[arxiv_id] = version
    editions = {}
    for pinned_id, version in versions.items():
        arxiv_id = pinned_id.removesuffix(version)
        editions[pinned_id] = (arxiv_id + latest[arxiv_id] if version else pinned_id, version)
    return editions


def editions_in_manifest(manifest_path: Path) -> dict[str, tuple[str, str]]:
    """The (Edition id, Version) of each pinned id the manifest's included Editions hold a file of, as `from_record`
    gives them."""
    editions = {}
    for file, edition_id in included_files(manifest_path).items():
        pinned_id, version = pinned_id_of_file(edition_id, file)
        editions[pinned_id] = (edition_id, version)
    return editions


def included_files(manifest_path: Path) -> dict[str, str]:
    """The Edition id of each file the manifest's included Editions are pinned to, by file name, from ``pdf_files``."""
    return {
        entry.split(" ", 1)[0]: row["edition_id"]
        for row in read_manifest(manifest_path)
        if row["relevance_verdict"] == "included"
        for entry in row["pdf_files"].split("|")
        if entry
    }


def from_record(snapshot_dir: Path, pdf_dir: Path, manifest_path: Path) -> tuple[list[InputFile], list[str]]:
    """Every file in the Snapshot's full-text record that an included Edition is pinned to, read from ``pdf_dir``,
    and what is wrong with the ones that can't be parsed: a file missing locally or whose bytes don't match the
    recorded hash.

    The manifest says which files those are. A file the record keeps for an excluded Edition, such as a withdrawn
    preprint, or for a Version the Edition is no longer pinned to, is skipped, and so are entries recorded as having
    no open PDF. The Edition id comes from the manifest, since a file kept across a re-pin is recorded under the old
    one. Pinned ids come from it too, not from the file name, which has unsafe characters replaced: a preprint's file
    is one of its Versions, a venue Edition's is the Edition.
    """
    wanted = included_files(manifest_path)
    files, problems = [], []
    for entry in FulltextRecord(snapshot_dir).all():
        if not entry.sha256 or entry.file not in wanted:
            continue
        path = pdf_dir / entry.file
        if not path.exists():
            problems.append(f"{path} is missing; the record pins sha256 {entry.sha256}")
            continue
        pdf = path.read_bytes()
        if (digest := hashlib.sha256(pdf).hexdigest()) != entry.sha256:
            problems.append(f"{path} has sha256 {digest}, but the record pins {entry.sha256}")
            continue
        edition_id = wanted[entry.file]
        pinned_id, version = pinned_id_of_file(edition_id, entry.file)
        files.append(InputFile(path, ParsedFile(edition_id, pinned_id, version, entry.sha256), pdf))
    return files, problems

