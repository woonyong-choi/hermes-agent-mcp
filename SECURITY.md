# Security

`hermes-agent-mcp` lets a language model operate a Hermes Agent install, which in turn has a terminal. Please read the *Security model* section of the README before deploying it anywhere other than your own machine.

## Design boundary

This server never opens a socket. It is spawned by the MCP client over stdio and calls the `hermes` binary as a child process. If you need remote access to Hermes, that is a different threat model — see [mlennie/hermes-mcp](https://github.com/mlennie/hermes-mcp), which is built for it.

## Reporting

If you find a way for a model to escape the subcommand allowlist, read a credential through the redaction layer, or run a shell command with `HERMES_MCP_ALLOW_SHELL` unset, please open a private security advisory on GitHub rather than a public issue. Include the tool call and the output you observed.

## Out of scope

- Anything `hermes_ask` does *inside* Hermes. That turn runs with the agent's own tools and permissions; this server only relays the prompt and the reply.
- Behaviour with `HERMES_MCP_ALLOW_SHELL=1`. That flag exists so you can hand a terminal to an agent you trust; it is not a sandbox.
