"""What every writer of a cache shares."""

from pathlib import Path


def write_atomically(path: Path, text: str) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file in the cache.

    Always UTF-8 with "\\n" line ends, so the bytes don't depend on the machine's locale.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8", newline="\n")
    partial.replace(path)
