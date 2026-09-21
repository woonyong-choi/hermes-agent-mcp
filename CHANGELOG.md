# Changelog

## 0.1.1

- README carries the MCP Registry ownership marker; no code changes

## 0.1.0

First release, published as `hermes-agent-mcp` (the PyPI name `hermes-mcp` belongs to mlennie's remote-access bridge; this project is the local, no-network counterpart).

- Works with both `mcp` 1.x (`FastMCP`) and 2.x (`MCPServer`)

- Tools: `hermes_status`, `hermes_ask`, `doctor`, `gateway_status`, `gateway_restart`, `cron_list`, `cron_create`, `cron_edit`, `cron_run`, `cron_runs`, `config_get`, `config_set`, `skills_list`, `sessions_list`, `model_info`, `shell`
- Subcommand allowlist, read-only mode, opt-in shell
- Redaction of Telegram, Anthropic, OpenAI, GitHub, Slack, AWS tokens and JWTs
- Typed `config_set` with `.bak` backup
