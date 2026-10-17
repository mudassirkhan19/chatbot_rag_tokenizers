"""The files a parse run reads, each with the pinned id its Chunks cite and its sha256."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..collection.fulltext import FulltextRecord, pinned_id_of_file
from .chunker import ParsedFile

# A Seed PDF is named "<seed>_<pinned id>.pdf", e.g. "bpe-dropout_1910.13267v1.pdf".
SEED_NAME = re.compile(r"[a-z0-9-]+_(?P<pinned_id>\d{4}\.\d{4,5}v\d+)")
VERSION = re.compile(r"\d{4}\.\d{4,5}(?P<version>v\d+)")


@dataclass(frozen=True)
class InputFile:
    path: Path
    identity: ParsedFile
    pdf: bytes


def from_paths(paths: list[Path]) -> list[InputFile]:
    """Files passed by hand (`--files`): the pinned id comes from the name, the hash from the bytes.

    A Seed name drops its prefix; any other name is taken as the file name `fetch` gives a pinned id. With no
    record to name the Edition, it is taken the way `fetch` pins one: an arXiv Version's Edition is the latest
    Version of the same arXiv id among the files given, and any other file is its own Edition.
    """
    named = []
    for path in paths:
        pdf = path.read_bytes()
        seed = SEED_NAME.fullmatch(path.stem)
        pinned_id = seed["pinned_id"] if seed else path.stem
        versioned = VERSION.fullmatch(pinned_id)
        named.append((path, pdf, pinned_id, versioned["version"] if versioned else ""))
    latest: dict[str, str] = {}
    for _, _, pinned_id, version in named:
        arxiv_id = pinned_id.removesuffix(version)
        if version and int(version[1:]) > int(latest.get(arxiv_id, "v0")[1:]):
            latest[arxiv_id] = version
    files = []
    for path, pdf, pinned_id, version in named:
        arxiv_id = pinned_id.removesuffix(version)
        edition_id = arxiv_id + latest[arxiv_id] if version else pinned_id
        files.append(InputFile(path, ParsedFile(edition_id, pinned_id, version, hashlib.sha256(pdf).hexdigest()), pdf))
    return files


def from_record(snapshot_dir: Path, pdf_dir: Path) -> tuple[list[InputFile], list[str]]:
    """Every file in the Snapshot's full-text record that has a hash, read from ``pdf_dir``, and what is wrong with
    the ones that can't be parsed: a file missing locally or whose bytes don't match the recorded hash.

    Entries recorded as having no open PDF are skipped. Pinned ids come from the record's Edition id, since a file
    name has unsafe characters replaced: a preprint's file is one of its Versions, a venue Edition's is the Edition.
    """
    files, problems = [], []
    for entry in FulltextRecord(snapshot_dir).all():
        if not entry.sha256:
            continue
        path = pdf_dir / entry.file
        if not path.exists():
            problems.append(f"{path} is missing; the record pins sha256 {entry.sha256}")
            continue
        pdf = path.read_bytes()
        if (digest := hashlib.sha256(pdf).hexdigest()) != entry.sha256:
            problems.append(f"{path} has sha256 {digest}, but the record pins {entry.sha256}")
            continue
        pinned_id, version = pinned_id_of_file(entry.edition_id, entry.file)
        files.append(InputFile(path, ParsedFile(entry.edition_id, pinned_id, version, entry.sha256), pdf))
    return files, problems

