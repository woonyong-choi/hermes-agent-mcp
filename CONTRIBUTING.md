# Contributing

Small, focused pull requests are easiest to review.

## Adding a tool

1. If it maps to a CLI subcommand, make sure the subcommand is in `ALLOWED_SUBCOMMANDS` in `runner.py` and that any state-changing verb is in `WRITE_VERBS`.
2. Add the tool to `server.py` with a docstring — the docstring is what the model reads.
3. Route output through `runner.run()` so it is redacted and truncated.
4. Add a test. Tests must pass without a Hermes install.

## Tracking upstream

Hermes Agent changes its CLI often. When a flag moves, prefer surfacing the CLI's own error over adding compatibility shims; the server should stay thin.

## Style

`ruff check .` and `ruff format .` before you push. Line length is 100.
