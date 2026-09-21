import pytest

from hermes_mcp.runner import HermesError, Runner, _is_write
from hermes_mcp.settings import Settings


def _settings(**kw):
    base = dict(
        binary="/nonexistent/hermes",
        home=__import__("pathlib").Path("/tmp/hermes-home"),
        timeout=5,
        ask_timeout=5,
        allow_shell=False,
        allow_write=True,
        max_output=1000,
    )
    base.update(kw)
    return Settings(**base)


def test_unknown_subcommand_is_refused():
    with pytest.raises(HermesError, match="not allowed"):
        Runner(_settings()).run(["auth", "add", "openai-codex"])


def test_write_commands_blocked_when_read_only():
    with pytest.raises(HermesError, match="write tools are disabled"):
        Runner(_settings(allow_write=False)).run(["cron", "remove", "abc"])


def test_read_commands_allowed_when_read_only():
    with pytest.raises(HermesError, match="not found"):
        Runner(_settings(allow_write=False)).run(["cron", "list"])


def test_shell_disabled_by_default():
    with pytest.raises(HermesError, match="shell tool is disabled"):
        Runner(_settings()).shell("echo hi")


def test_shell_runs_when_enabled():
    result = Runner(_settings(allow_shell=True)).shell("echo hermes")
    assert result.exit_code == 0
    assert "hermes" in result.stdout


def test_is_write_detection():
    assert _is_write(["cron", "edit", "abc"])
    assert _is_write(["gateway", "restart"])
    assert not _is_write(["cron", "list"])
    assert not _is_write(["doctor"])
