Title: hermes-agent-mcp — operate your Hermes install from Claude Code, Cursor or any MCP client

I built a small MCP server that wraps the `hermes` CLI so an agent without a terminal can still operate Hermes: hand it a task (`hermes_ask`), list/edit/run cron jobs, read and write `config.yaml` with explicit types, check `hermes doctor`, restart the gateway.

Repo: https://github.com/woonyong-choi/hermes-agent-mcp
Install: `uvx hermes-agent-mcp` (or `claude mcp add hermes -- uvx hermes-agent-mcp`)

Why I made it: I run Hermes on a MacBook and drive it from Telegram, but the agents I use for coding live elsewhere and had no way to touch Hermes without me typing in a terminal. mlennie's hermes-mcp already covers remote delegation over a tunnel — this is the opposite end: local only, stdio only, no network exposure, and it covers the operations surface (cron, config, gateway, doctor) rather than just sending prompts.

Design notes, since this hands a model the controls of an agent that has a shell:
- argv-only subprocess calls, never a shell; `hermes auth` and credential commands are not reachable
- every output is redacted (Telegram/Anthropic/OpenAI/GitHub/Slack/AWS tokens, JWTs) before the model sees it
- `HERMES_MCP_ALLOW_WRITE=0` for read-only, `shell` tool is opt-in
- `config_set` takes a `value_type` because `hermes config set x off` stores the boolean False, and options like `reply_to_mode` compare against the string — bit me on day one

Works with mcp 1.x and 2.x. MIT. Feedback on which subcommands you'd want exposed is welcome — I kept the allowlist tight on purpose.
