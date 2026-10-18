"""What every config file loader shares."""

from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """A config file is malformed: a missing, unknown or mistyped field, or a value out of range."""


def read_table(raw: dict, name: str, expected: dict[str, type], path: Path) -> dict[str, Any]:
    """The fields of one TOML table, such as [grobid], checked against the names and types expected."""
    if name not in raw:
        raise ConfigError(f"{path} has no [{name}] table")
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
