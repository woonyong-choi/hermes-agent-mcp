"""Environment-driven settings for the server.

Nothing is hard-coded to one machine: every path is discovered or overridable,
so the same package works on macOS, Linux and WSL, and inside a container that
mounts someone else's ``~/.hermes``.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one server process."""

    binary: str
    home: Path
    timeout: int
    ask_timeout: int
    allow_shell: bool
    allow_write: bool
    max_output: int

    @classmethod
    def from_env(cls) -> Settings:
        binary = os.environ.get("HERMES_MCP_BIN") or shutil.which("hermes") or "hermes"
        home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()
        return cls(
            binary=binary,
            home=home,
            timeout=_int("HERMES_MCP_TIMEOUT", 120),
            ask_timeout=_int("HERMES_MCP_ASK_TIMEOUT", 900),
            allow_shell=_flag("HERMES_MCP_ALLOW_SHELL"),
            allow_write=_flag("HERMES_MCP_ALLOW_WRITE", True),
            max_output=_int("HERMES_MCP_MAX_OUTPUT", 40_000),
        )

    def describe(self) -> dict[str, object]:
        """A summary safe to hand back to a model."""
        return {
            "binary": self.binary,
            "home": str(self.home),
            "home_exists": self.home.is_dir(),
            "timeout_seconds": self.timeout,
            "ask_timeout_seconds": self.ask_timeout,
            "write_tools_enabled": self.allow_write,
            "shell_tool_enabled": self.allow_shell,
        }
