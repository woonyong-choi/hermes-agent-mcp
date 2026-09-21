# Claude Code

```
claude mcp add hermes -- uvx hermes-agent-mcp
```

Read-only, for a shared machine:

```
claude mcp add hermes -e HERMES_MCP_ALLOW_WRITE=0 -- uvx hermes-agent-mcp
```

With the shell tool, for a machine you control:

```
claude mcp add hermes -e HERMES_MCP_ALLOW_SHELL=1 -- uvx hermes-agent-mcp
```
