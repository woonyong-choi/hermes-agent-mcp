# hermes-agent-mcp

**Operate your local [Hermes Agent](https://github.com/NousResearch/hermes-agent) install from any MCP client — without exposing it to the network.**

`hermes-agent-mcp` is a Model Context Protocol server that wraps the local `hermes` CLI over stdio. Point Claude Code, Cursor, Codex or any other MCP-capable agent at it and they can hand Hermes a task, read and change its config, manage cron jobs, restart the gateway and run `hermes doctor` — without a terminal and without ever seeing a token.

```
uvx hermes-agent-mcp
```

That is the whole install. No ports, no tunnel, no OAuth. It runs as a child process of your MCP client, on the same machine as Hermes, and nothing leaves the box.

<sub>mcp-name: io.github.woonyong-choi/hermes-agent-mcp</sub>

## Why this exists

Hermes is a great always-on agent, but everything about *operating* it happens in a terminal: `hermes cron edit`, `hermes config set`, `hermes gateway restart`. If the agent that wants to do those things has no terminal — a desktop app, a coding assistant sandboxed away from your shell — it is stuck asking a human to type for it.

There is already a good project called [hermes-mcp](https://github.com/mlennie/hermes-mcp) by mlennie. It solves a *different* problem: reaching Hermes **remotely**, over HTTP through a cloudflared tunnel with OAuth, so a hosted client can delegate tasks. If that is what you need, use it.

This project was written by someone who did not want that. Opening a Hermes gateway to the internet means an agent with a shell is one leaked token away from anyone. `hermes-agent-mcp` stays local on purpose:

- it never listens on a port — MCP over stdio only
- it never handles credentials — it calls the CLI, which already has them
- it exposes the *operations* surface (cron, config, gateway, doctor, skills), not just "send a prompt"

| | hermes-agent-mcp (this) | hermes-mcp (mlennie) |
|---|---|---|
| Transport | stdio, local process | HTTP, tunnel + OAuth |
| Reachable from | MCP clients on the same machine | Anywhere |
| Surface | 16 tools: ask + cron, config, gateway, doctor, skills, sessions | 4 tools: ask, check, cancel, reset |
| Typed `config.yaml` writes | Yes | — |
| Network exposure | None | By design |

## Tools

| Tool | What it does |
|---|---|
| `hermes_status` | Server config, whether the CLI answers, which tools are enabled |
| `hermes_ask` | Hand the agent a task and get its reply (one non-interactive turn) |
| `doctor` | `hermes doctor` health report |
| `gateway_status` / `gateway_restart` | Messaging gateway state and restart |
| `cron_list` / `cron_create` / `cron_edit` / `cron_run` / `cron_runs` | Scheduled jobs, including per-job model and reasoning effort |
| `config_get` / `config_set` | Typed reads and writes against `config.yaml` |
| `skills_list` | Installed skills |
| `sessions_list` | Recent sessions |
| `model_info` | Default model, provider and Nous Portal status |
| `shell` | Run a shell command on the host — **off by default** |

### `config_set` fixes a real trap

`hermes config set platforms.telegram.reply_to_mode off` stores the YAML boolean `False`, not the string `"off"`. Several Hermes options compare against the string, so the setting silently does nothing. `config_set` takes an explicit `value_type` (`str`, `int`, `float`, `bool`, `null`, `json`), writes a `.bak` before touching the file, and returns the resulting section so you can see what landed.

## Setup

### Claude Code

```
claude mcp add hermes -- uvx hermes-agent-mcp
```

### Cursor / Windsurf / Claude Desktop

```json
{
  "mcpServers": {
    "hermes": {
      "command": "uvx",
      "args": ["hermes-agent-mcp"]
    }
  }
}
```

### Hermes itself

Hermes can drive its own install — useful for a supervisor profile that manages other profiles. Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  hermes:
    command: uvx
    args: ["hermes-agent-mcp"]
```

### From a clone

```
git clone https://github.com/woonyong-choi/hermes-agent-mcp
cd hermes-agent-mcp
uv tool install -e .
```

## Configuration

Everything is an environment variable, so the same server works on macOS, Linux, WSL and inside a container that mounts someone else's `~/.hermes`.

| Variable | Default | Meaning |
|---|---|---|
| `HERMES_HOME` | `~/.hermes` | Hermes data directory |
| `HERMES_MCP_BIN` | `hermes` on `PATH` | Path to the CLI |
| `HERMES_MCP_ALLOW_WRITE` | `1` | Allow tools that change state (cron edit, config set, restart). Set `0` for read-only |
| `HERMES_MCP_ALLOW_SHELL` | `0` | Enable the `shell` tool |
| `HERMES_MCP_TIMEOUT` | `120` | Seconds for ordinary CLI calls |
| `HERMES_MCP_ASK_TIMEOUT` | `900` | Seconds for `hermes_ask` |
| `HERMES_MCP_MAX_OUTPUT` | `40000` | Characters returned per call before truncation |

## Security model

This server gives a language model the ability to operate an agent that has a terminal. The design assumes the model is talking to untrusted content and keeps the blast radius small:

- **Argument lists, never a shell.** Every CLI call is `subprocess.run([...])` with `shell=False`. Prompt text cannot become shell syntax.
- **Subcommand allowlist.** Only `config`, `cron`, `doctor`, `gateway`, `model`, `portal`, `profile`, `sessions`, `skills`, `tools` and `--version` are reachable. `hermes auth` and anything that handles credentials is not, on purpose.
- **Redaction on every return.** Telegram bot tokens, Anthropic/OpenAI/GitHub/Slack/AWS keys and JWTs are replaced with `[redacted]` before output reaches the model. `.env` is never read.
- **Read-only mode.** `HERMES_MCP_ALLOW_WRITE=0` blocks every state-changing verb.
- **Shell is opt-in.** `shell` refuses to run until you set `HERMES_MCP_ALLOW_SHELL=1`, and you should only do that on a machine you control, for an agent you trust.

See [SECURITY.md](SECURITY.md) for reporting.

## Releasing

Tag a version and CI publishes to PyPI via Trusted Publishing and attaches the wheel to a GitHub release:

```
git tag v0.1.0 && git push --tags
```

`server.json` at the repo root is the manifest for the [MCP Registry](https://registry.modelcontextprotocol.io); publish it with `mcp-publisher publish` after the PyPI release exists.

## Development

```
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
ruff check .
```

Tests do not need a Hermes install; the runner is exercised against a missing binary and the config writer against a temp directory.

## Compatibility

Built against Hermes Agent 0.21.x. The CLI is moving fast — if a subcommand's flags change, the tool returns the CLI's own error text rather than guessing. Issues and PRs that track upstream changes are welcome.

## License

MIT. Hermes Agent is MIT-licensed by Nous Research; this project is independent and not affiliated with them.
