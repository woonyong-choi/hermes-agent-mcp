"""Redaction of secret-looking material from command output.

The Hermes CLI prints configuration, environment and log lines that can contain
bot tokens, API keys and OAuth refresh tokens.  Everything this server returns
passes through :func:`redact` first, so a secret never reaches the model that is
driving the tools.
"""

from __future__ import annotations

import re

# Key-like assignments: TELEGRAM_BOT_TOKEN=123:abc, "api_key": "sk-...", token: gho_x
_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|ACCESS_?KEY|CREDENTIAL)[A-Z0-9_]*)"
    r"(\s*[:=]\s*)"
    r"(\"[^\"\n]*\"|'[^'\n]*'|\S+)"
)

# Shapes that are secrets wherever they appear, even without a label.
_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),  # Telegram bot token
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}\b"),  # Anthropic
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),  # OpenAI style
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),  # GitHub
    re.compile(r"\bxox[abps]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),  # JWT
)

PLACEHOLDER = "[redacted]"


def redact(text: str) -> str:
    """Return ``text`` with anything that looks like a credential removed."""
    if not text:
        return text

    def _assignment(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{PLACEHOLDER}"

    cleaned = _ASSIGNMENT.sub(_assignment, text)
    for shape in _SHAPES:
        cleaned = shape.sub(PLACEHOLDER, cleaned)
    return cleaned
