"""The parse config file: the pinned GROBID service (ADR 0022).

Run as a module, it prints the GROBID settings as shell assignments for the justfile.
"""

import re
import shlex
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

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


class ConfigError(ValueError):
    pass


def load_grobid_config(path: Path) -> GrobidConfig:
    raw = tomllib.loads(path.read_text())
    if "grobid" not in raw:
        raise ConfigError(f"{path} has no [grobid] section")
    grobid = GrobidConfig(**raw["grobid"])
    if not DIGEST.fullmatch(grobid.digest):
        raise ConfigError(f"GROBID digest {grobid.digest!r} is not sha256: followed by 64 hex digits")
    return grobid


def main(argv: list[str] | None = None) -> None:
    """Print GROBID_REFERENCE, GROBID_TAG and GROBID_PORT as shell assignments."""
    args = sys.argv[1:] if argv is None else argv
    grobid = load_grobid_config(Path(args[0]) if args else Path("config/parse.toml"))
    for name, value in [("GROBID_REFERENCE", grobid.reference), ("GROBID_TAG", grobid.tag), ("GROBID_PORT", grobid.port)]:
        print(f"{name}={shlex.quote(str(value))}")


if __name__ == "__main__":
    main()
