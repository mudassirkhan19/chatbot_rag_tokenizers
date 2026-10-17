"""The parse config file: the pinned GROBID service (ADR 0023)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.config import ConfigError

DEFAULT_PATH = Path("config/parse.toml")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


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


def load_grobid_config(path: Path = DEFAULT_PATH) -> GrobidConfig:
    raw = tomllib.loads(path.read_text())
    if "grobid" not in raw:
        raise ConfigError(f"{path} has no [grobid] section")
    fields = raw["grobid"]
    expected = {"image": str, "tag": str, "digest": str, "port": int}
    if unknown := sorted(set(fields) - set(expected)):
        raise ConfigError(f"[grobid] in {path} has unknown fields: {', '.join(unknown)}")
    for name, kind in expected.items():
        if name not in fields:
            raise ConfigError(f"[grobid] in {path} has no {name}")
        # bool is a subclass of int, so `port = true` would otherwise pass.
        if not isinstance(fields[name], kind) or isinstance(fields[name], bool):
            raise ConfigError(f"GROBID {name} {fields[name]!r} is not a {kind.__name__}")
    grobid = GrobidConfig(**fields)
    if not DIGEST.fullmatch(grobid.digest):
        raise ConfigError(f"GROBID digest {grobid.digest!r} is not sha256: followed by 64 hex digits")
    if not 1 <= grobid.port <= 65535:
        raise ConfigError(f"GROBID port {grobid.port} is not between 1 and 65535")
    return grobid
