# Changelog

## 0.2.0

- Bridged prompts are prefixed with the caller (`HERMES_MCP_CALLER` or the `caller` argument) using one quiet marker — `▸ Claude Code · …` — so a shared chat shows who asked without a zoo of emoji. `HERMES_MCP_LABEL_FORMAT` changes the template.
- `bridge_ask` waits for the gateway session to end before reading the reply, so interim progress lines are never returned as the answer.
- **Bridge**: `bridge_setup`, `bridge_status`, `bridge_ask`, `bridge_check`. Runs the turn inside the gateway via Hermes's own webhook adapter and mirrors both the prompt and the reply into the user's chat (Telegram by default), so an MCP-driven conversation stays visible on their phone. Loopback-only, HMAC-signed, secret stored 0600.
- `webhook subscribe` added to the CLI allowlist for the bridge setup.

## 0.1.1

- README carries the MCP Registry ownership marker; no code changes

## 0.1.0

First release, published as `hermes-agent-mcp` (the PyPI name `hermes-mcp` belongs to mlennie's remote-access bridge; this project is the local, no-network counterpart).

- Works with both `mcp` 1.x (`FastMCP`) and 2.x (`MCPServer`)

- Tools: `hermes_status`, `hermes_ask`, `doctor`, `gateway_status`, `gateway_restart`, `cron_list`, `cron_create`, `cron_edit`, `cron_run`, `cron_runs`, `config_get`, `config_set`, `skills_list`, `sessions_list`, `model_info`, `shell`
- Subcommand allowlist, read-only mode, opt-in shell
- Redaction of Telegram, Anthropic, OpenAI, GitHub, Slack, AWS tokens and JWTs
- Typed `config_set` with `.bak` backup
