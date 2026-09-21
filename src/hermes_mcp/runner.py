"""Safe execution of the Hermes CLI.

Two rules make this boring on purpose:

* commands are built as argument lists and run without a shell, so nothing the
  model writes can be interpreted as shell syntax;
* only an explicit allowlist of Hermes subcommands can be reached, so a prompt
  injection cannot talk the server into ``hermes auth`` or an arbitrary binary.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .redact import redact
from .settings import Settings

# Subcommands this server is willing to run. Auth and secret management are
# deliberately absent: those are for a human at a terminal.
ALLOWED_SUBCOMMANDS: frozenset[str] = frozenset(
    {
        "--version",
        "config",
        "cron",
        "doctor",
        "gateway",
        "model",
        "portal",
        "profile",
        "sessions",
        "skills",
        "tools",
    }
)

READ_ONLY_SUBCOMMANDS: frozenset[str] = frozenset({"--version", "doctor", "portal", "sessions"})

# Second-level verbs that change state. Used to honour HERMES_MCP_ALLOW_WRITE.
WRITE_VERBS: frozenset[str] = frozenset(
    {
        "create",
        "add",
        "edit",
        "set",
        "remove",
        "rm",
        "delete",
        "pause",
        "resume",
        "restart",
        "start",
        "stop",
        "install",
        "uninstall",
        "update",
        "run",
        "tick",
        "enable",
        "disable",
    }
)


class HermesError(RuntimeError):
    """Raised when a command is refused before it runs."""


@dataclass
class Result:
    """Outcome of one CLI invocation, already redacted and truncated."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "ok": self.exit_code == 0 and not self.timed_out,
        }


def _is_write(args: list[str]) -> bool:
    if not args:
        return False
    if args[0] in READ_ONLY_SUBCOMMANDS:
        return False
    return any(part in WRITE_VERBS for part in args[1:3])


class Runner:
    """Runs allowlisted Hermes commands on behalf of the MCP tools."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["HERMES_HOME"] = str(self.settings.home)
        # Keep the CLI's output parseable: no spinners, no colour escapes.
        env.setdefault("NO_COLOR", "1")
        env.setdefault("TERM", "dumb")
        return env

    def _truncate(self, text: str) -> str:
        limit = self.settings.max_output
        if len(text) <= limit:
            return text
        head = text[: limit - 200]
        return f"{head}\n...[{len(text) - limit + 200} characters truncated]"

    def run(self, args: list[str], *, timeout: int | None = None) -> Result:
        """Run ``hermes <args>`` and return a redacted result."""
        if not args:
            raise HermesError("no command given")
        if args[0] not in ALLOWED_SUBCOMMANDS:
            allowed = ", ".join(sorted(ALLOWED_SUBCOMMANDS))
            raise HermesError(f"subcommand {args[0]!r} is not allowed. Allowed: {allowed}")
        if _is_write(args) and not self.settings.allow_write:
            raise HermesError(
                "this command changes state and write tools are disabled "
                "(set HERMES_MCP_ALLOW_WRITE=1 to enable)"
            )

        argv = [self.settings.binary, *args]
        printable = " ".join(["hermes", *args])
        try:
            completed = subprocess.run(  # noqa: S603 - argv list, shell=False
                argv,
                capture_output=True,
                text=True,
                timeout=timeout or self.settings.timeout,
                env=self._env(),
                check=False,
            )
        except FileNotFoundError as exc:
            raise HermesError(
                f"Hermes CLI not found at {self.settings.binary!r}. "
                "Install Hermes Agent or set HERMES_MCP_BIN."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            return Result(
                command=printable,
                exit_code=-1,
                stdout=self._truncate(redact(exc.stdout or "")),
                stderr="command timed out",
                timed_out=True,
            )

        return Result(
            command=printable,
            exit_code=completed.returncode,
            stdout=self._truncate(redact(completed.stdout)),
            stderr=self._truncate(redact(completed.stderr)),
        )

    def run_raw(self, args: list[str], *, timeout: int | None = None) -> Result:
        """Run the CLI with top-level flags that are not subcommands (e.g. ``-z``).

        Still argv-based and still redacted; it only skips the subcommand
        allowlist, which does not apply to flags.
        """
        argv = [self.settings.binary, *args]
        printable = " ".join(["hermes", *args])
        try:
            completed = subprocess.run(  # noqa: S603 - argv list, shell=False
                argv,
                capture_output=True,
                text=True,
                timeout=timeout or self.settings.timeout,
                env=self._env(),
                check=False,
            )
        except FileNotFoundError as exc:
            raise HermesError(
                f"Hermes CLI not found at {self.settings.binary!r}. "
                "Install Hermes Agent or set HERMES_MCP_BIN."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            return Result(
                command=printable,
                exit_code=-1,
                stdout=self._truncate(redact(exc.stdout or "")),
                stderr="command timed out",
                timed_out=True,
            )
        return Result(
            command=printable,
            exit_code=completed.returncode,
            stdout=self._truncate(redact(completed.stdout)),
            stderr=self._truncate(redact(completed.stderr)),
        )

    def shell(self, command: str, *, timeout: int | None = None) -> Result:
        """Run an arbitrary shell command. Disabled unless explicitly enabled."""
        if not self.settings.allow_shell:
            raise HermesError(
                "the shell tool is disabled. Set HERMES_MCP_ALLOW_SHELL=1 to enable it, "
                "and only do that on a machine you control."
            )
        try:
            completed = subprocess.run(  # noqa: S602 - opt-in by design
                ["/bin/sh", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout or self.settings.timeout,
                env=self._env(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return Result(
                command=command,
                exit_code=-1,
                stdout=self._truncate(redact(exc.stdout or "")),
                stderr="command timed out",
                timed_out=True,
            )
        return Result(
            command=command,
            exit_code=completed.returncode,
            stdout=self._truncate(redact(completed.stdout)),
            stderr=self._truncate(redact(completed.stderr)),
        )
