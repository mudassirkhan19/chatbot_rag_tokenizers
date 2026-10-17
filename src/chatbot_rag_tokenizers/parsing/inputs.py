"""The files a parse run reads, each with the pinned id its Chunks cite and its sha256."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..collection.fulltext import FulltextRecord, file_name
from .chunker import ParsedFile

# A Seed PDF is named "<seed>_<pinned id>.pdf", e.g. "bpe-dropout_1910.13267v1.pdf".
SEED_NAME = re.compile(r"[a-z0-9-]+_(?P<pinned_id>\d{4}\.\d{4,5}v\d+)")
VERSION = re.compile(r"\d{4}\.\d{4,5}(?P<version>v\d+)")
# A preprint's Edition id is its arXiv id pinned to a Version, new-style (2112.06598v2) or old-style (hep-th/9901001v2).
ARXIV_EDITION = re.compile(r"(?P<arxiv_id>\d{4}\.\d{4,5}|[a-z-]+(\.[A-Z]{2})?/\d{7})v\d+")


@dataclass(frozen=True)
class InputFile:
    path: Path
    identity: ParsedFile
    pdf: bytes


def from_paths(paths: list[Path]) -> list[InputFile]:
    """Files passed by hand (`--files`): the pinned id comes from the name, the hash from the bytes.

    A Seed name drops its prefix; any other name is taken as the file name `fetch` gives a pinned id.
    """
    files = []
    for path in paths:
        pdf = path.read_bytes()
        seed = SEED_NAME.fullmatch(path.stem)
        pinned_id = seed["pinned_id"] if seed else path.stem
        version = VERSION.fullmatch(pinned_id)
        identity = ParsedFile(pinned_id, version["version"] if version else "", hashlib.sha256(pdf).hexdigest())
        files.append(InputFile(path, identity, pdf))
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
        pinned_id, version = _pinned(entry.edition_id, entry.file)
        files.append(InputFile(path, ParsedFile(pinned_id, version, entry.sha256), pdf))
    return files, problems


def _pinned(edition_id: str, file: str) -> tuple[str, str]:
    """The pinned id and Version of a recorded file, e.g. v1 of the preprint Edition 2112.06598v2."""
    if arxiv := ARXIV_EDITION.fullmatch(edition_id):
        stem = file.removesuffix(".pdf")
        version = stem.removeprefix(file_name(arxiv["arxiv_id"]).removesuffix(".pdf"))
        if re.fullmatch(r"v\d+", version):
            return arxiv["arxiv_id"] + version, version
    return edition_id, ""
