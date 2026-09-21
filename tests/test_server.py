"""Smoke test: the server module imports and registers its tools on mcp 1.x and 2.x."""

from hermes_mcp import server

EXPECTED = {
    "hermes_status",
    "hermes_ask",
    "doctor",
    "gateway_status",
    "gateway_restart",
    "cron_list",
    "cron_create",
    "cron_edit",
    "cron_run",
    "cron_runs",
    "config_get",
    "config_set",
    "skills_list",
    "sessions_list",
    "model_info",
    "shell",
}


def test_server_imports():
    assert server.mcp.name == "hermes-mcp"


def test_all_tools_are_defined():
    for name in EXPECTED:
        assert callable(getattr(server, name)), name
