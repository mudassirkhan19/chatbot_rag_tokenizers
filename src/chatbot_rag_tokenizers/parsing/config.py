"""The parse config file: the pinned GROBID service (ADR 0023) and the chunking config (ADR 0025)."""

import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from chatbot_rag_tokenizers.config import ConfigError

DEFAULT_PATH = Path("config/parse.toml")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class GrobidConfig:
    image: str  # Docker Hub repository, e.g. "grobid/grobid"
    tag: str  # a readable label for the release; the digest decides what runs
    digest: str  # "sha256:..." of the image index
    port: int  # localhost port the service is published on

    @property
    def reference(self) -> str:
        """The image reference Docker pulls and runs: by digest only."""
        return f"{self.image}@{self.digest}"

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    @property
    def parser_key(self) -> str:
        """Names the parser in the parse cache: the tag to read, a short digest to decide."""
        return f"grobid-{self.tag}-{self.digest.removeprefix('sha256:')[:12]}"


@dataclass(frozen=True)
class ChunkingConfig:
    token_budget: int  # most tokens of text per Chunk, header not included
    tokenizer: str  # the Hugging Face repo the tokenizer file comes from
    tokenizer_revision: str  # the commit of that repo the file was taken from
    tokenizer_file: Path  # resolved against the config file's directory
    tokenizer_sha256: str
    min_sections: int  # the quality gate (ADR 0027): a file with fewer Sections fails
    min_body_characters: int  # and so does one with less text in its Sections

    def describe(self) -> dict[str, Any]:
        """The settings that decide the Chunks, as the report shows them (the file's location doesn't count)."""
        settings = asdict(self)
        del settings["tokenizer_file"]
        return settings


@dataclass(frozen=True)
class ParseConfig:
    grobid: GrobidConfig
    chunking: ChunkingConfig


def _section(raw: dict, name: str, expected: dict[str, type], path: Path) -> dict[str, Any]:
    if name not in raw:
        raise ConfigError(f"{path} has no [{name}] section")
    fields = raw[name]
    if unknown := sorted(set(fields) - set(expected)):
        raise ConfigError(f"[{name}] in {path} has unknown fields: {', '.join(unknown)}")
    for field, kind in expected.items():
        if field not in fields:
            raise ConfigError(f"[{name}] in {path} has no {field}")
        # bool is a subclass of int, so `port = true` would otherwise pass.
        if not isinstance(fields[field], kind) or isinstance(fields[field], bool):
            raise ConfigError(f"[{name}] {field} {fields[field]!r} is not a {kind.__name__}")
    return fields


def _grobid(raw: dict, path: Path) -> GrobidConfig:
    fields = _section(raw, "grobid", {"image": str, "tag": str, "digest": str, "port": int}, path)
    grobid = GrobidConfig(**fields)
    if not DIGEST.fullmatch(grobid.digest):
        raise ConfigError(f"GROBID digest {grobid.digest!r} is not sha256: followed by 64 hex digits")
    if not 1 <= grobid.port <= 65535:
        raise ConfigError(f"GROBID port {grobid.port} is not between 1 and 65535")
    return grobid


def _chunking(raw: dict, path: Path) -> ChunkingConfig:
    expected = {name: str for name in ("tokenizer", "tokenizer_revision", "tokenizer_file", "tokenizer_sha256")}
    counts = {name: int for name in ("token_budget", "min_sections", "min_body_characters")}
    fields = _section(raw, "chunking", {**counts, **expected}, path)
    chunking = ChunkingConfig(**{**fields, "tokenizer_file": path.parent / fields["tokenizer_file"]})
    if chunking.token_budget < 1:
        raise ConfigError(f"[chunking] token_budget {chunking.token_budget} is not a positive number of tokens")
    if chunking.min_sections < 0 or chunking.min_body_characters < 0:
        raise ConfigError("[chunking] min_sections and min_body_characters must not be negative")
    if not SHA256.fullmatch(chunking.tokenizer_sha256):
        raise ConfigError(f"[chunking] tokenizer_sha256 {chunking.tokenizer_sha256!r} is not 64 hex digits")
    return chunking


def load_grobid_config(path: Path = DEFAULT_PATH) -> GrobidConfig:
    return _grobid(tomllib.loads(path.read_text()), path)


def load_parse_config(path: Path = DEFAULT_PATH) -> ParseConfig:
    raw = tomllib.loads(path.read_text())
    return ParseConfig(grobid=_grobid(raw, path), chunking=_chunking(raw, path))
