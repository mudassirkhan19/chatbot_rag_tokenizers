"""The files a parse run reads, each with the pinned id its Chunks cite and its sha256."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

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
