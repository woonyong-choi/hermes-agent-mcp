"""Typed reads and writes against ``config.yaml``.

``hermes config set x off`` parses ``off`` as YAML, which stores the boolean
``False``.  Several Hermes options compare against the *string* ``"off"``, so the
setting silently does nothing.  These helpers take an explicit type instead of
guessing, which makes the failure impossible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

VALUE_TYPES = ("str", "int", "float", "bool", "null", "json")


class ConfigError(RuntimeError):
    """Raised for a malformed key path or an unusable value."""


def coerce(value: str, value_type: str) -> Any:
    """Turn the string ``value`` into the requested Python type."""
    if value_type not in VALUE_TYPES:
        raise ConfigError(f"unknown value_type {value_type!r}; use one of {', '.join(VALUE_TYPES)}")
    if value_type == "str":
        return value
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "on"}:
            return True
        if lowered in {"false", "no", "0", "off"}:
            return False
        raise ConfigError(f"cannot read {value!r} as a boolean")
    if value_type == "null":
        return None
    return yaml.safe_load(value)


def _split(key: str) -> list[str]:
    parts = [part for part in key.split(".") if part]
    if not parts:
        raise ConfigError("key must not be empty")
    return parts


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def get(path: Path, key: str) -> Any:
    node: Any = load(path)
    for part in _split(key):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"key {key!r} is not set in {path.name}")
        node = node[part]
    return node


def set_value(path: Path, key: str, value: Any) -> dict[str, Any]:
    """Write ``value`` at ``key`` and return the enclosing section."""
    data = load(path)
    parts = _split(key)
    node = data
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value

    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {parts[-1]: value} if len(parts) == 1 else {parts[-2]: node}
