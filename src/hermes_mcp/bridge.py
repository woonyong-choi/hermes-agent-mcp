"""Mirror MCP traffic into a messaging chat through the Hermes gateway.

``hermes_ask`` runs a one-shot CLI turn: it works, but it runs *outside* the
gateway, so nothing shows up in the user's Telegram (or Slack, Discord...)
conversation and the reply cannot be delivered there.  The bridge fixes that by
going through the gateway's own webhook adapter, which Hermes ships for exactly
this — "an external service pokes the agent, the agent answers into a chat".

Two routes are registered on the gateway, both bound to loopback and HMAC-signed:

* ``<route>-echo`` — ``deliver_only``: posts the caller's prompt into the chat,
  so the person sees what was asked;
* ``<route>`` — runs the agent inside the gateway with an elevated toolset and
  delivers the reply into the same chat.

The reply is then read back from ``state.db`` so the MCP caller gets it too.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import configfile
from .runner import Runner
from .settings import Settings

STATE_NAME = "hermes-agent-mcp.json"
DEFAULT_ROUTE = "claude"
DEFAULT_PORT = 8644
# What the bridged agent may touch. Trusted by construction: loopback + HMAC.
DEFAULT_TOOLSETS = ["terminal", "file", "code_execution", "web", "memory", "skills", "cronjob"]


class BridgeError(RuntimeError):
    """Raised when the bridge is not set up or the gateway refuses a request."""


@dataclass
class BridgeState:
    """Persisted in ``$HERMES_HOME/hermes-agent-mcp.json`` (mode 0600)."""

    secret: str
    platform: str
    chat_id: str
    route: str = DEFAULT_ROUTE
    port: int = DEFAULT_PORT
    label: str = "🖥 Claude"

    @property
    def echo_route(self) -> str:
        return f"{self.route}-echo"

    def url(self, route: str) -> str:
        return f"http://127.0.0.1:{self.port}/webhooks/{route}"


def _state_path(settings: Settings) -> Path:
    return settings.home / STATE_NAME


def load_state(settings: Settings) -> BridgeState | None:
    path = _state_path(settings)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return BridgeState(**data)


def _save_state(settings: Settings, state: BridgeState) -> None:
    path = _state_path(settings)
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def _guess_chat(settings: Settings, platform: str) -> tuple[str, str] | None:
    """Most recently active chat on ``platform``: (chat_id, display_name)."""
    db = settings.home / "state.db"
    if not db.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = con.execute(
            "select chat_id, display_name from sessions "
            "where source = ? and chat_id is not null "
            "order by started_at desc limit 1",
            (platform,),
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return None
    return (str(row[0]), str(row[1] or "")) if row else None


def setup(
    settings: Settings,
    runner: Runner,
    *,
    platform: str = "telegram",
    chat_id: str | None = None,
    route: str = DEFAULT_ROUTE,
    port: int = DEFAULT_PORT,
    toolsets: list[str] | None = None,
) -> dict[str, Any]:
    """Register the two webhook routes and bind the adapter to loopback."""
    guessed = None
    if not chat_id:
        guessed = _guess_chat(settings, platform)
        if not guessed:
            raise BridgeError(
                f"no {platform} chat found in state.db; pass chat_id explicitly "
                "(send the bot one message first if the chat is new)"
            )
        chat_id = guessed[0]

    existing = load_state(settings)
    secret = existing.secret if existing else secrets.token_hex(32)
    state = BridgeState(secret=secret, platform=platform, chat_id=chat_id, route=route, port=port)

    # 1. Adapter on, loopback only. DEFAULT_HOST in Hermes is None (all interfaces).
    cfg = settings.home / "config.yaml"
    configfile.set_value(cfg, "platforms.webhook.enabled", True)
    configfile.set_value(cfg, "platforms.webhook.extra.host", "127.0.0.1")
    configfile.set_value(cfg, "platforms.webhook.extra.port", port)

    # 2. Routes via the CLI so Hermes owns the subscriptions file format.
    common = ["--deliver", platform, "--deliver-chat-id", chat_id, "--secret", secret]
    echo = runner.run(
        [
            "webhook",
            "subscribe",
            state.echo_route,
            "--deliver-only",
            "--prompt",
            "{text}",
            "--description",
            "hermes-agent-mcp: echo of the caller's prompt",
            *common,
        ],
    )
    main = runner.run(
        [
            "webhook",
            "subscribe",
            route,
            "--prompt",
            "{text}",
            "--description",
            "hermes-agent-mcp: bridged agent turn",
            *common,
        ],
    )
    if echo.exit_code != 0 or main.exit_code != 0:
        raise BridgeError(
            "hermes webhook subscribe failed:\n"
            + (echo.stderr or echo.stdout)
            + (main.stderr or main.stdout)
        )

    # 3. Elevated toolsets for the main route (the CLI has no flag for it).
    subs = settings.home / "webhook_subscriptions.json"
    if subs.is_file():
        data = json.loads(subs.read_text(encoding="utf-8"))
        target = data.get(route) if isinstance(data, dict) else None
        if target is None and isinstance(data, dict):
            for key in ("routes", "subscriptions"):
                if isinstance(data.get(key), dict) and route in data[key]:
                    target = data[key][route]
        if isinstance(target, dict):
            target["toolsets"] = toolsets or DEFAULT_TOOLSETS
            subs.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    _save_state(settings, state)
    restart = runner.run(["gateway", "restart"], timeout=180)
    return {
        "ok": restart.exit_code == 0,
        "platform": platform,
        "chat_id": chat_id,
        "chat_guessed_from": guessed[1] if guessed else None,
        "routes": [state.echo_route, route],
        "listen": f"127.0.0.1:{port}",
        "toolsets": toolsets or DEFAULT_TOOLSETS,
        "gateway_restart": restart.stdout.strip() or restart.stderr.strip(),
        "note": "the secret is stored in "
        + str(_state_path(settings))
        + " (0600); it is never returned",
    }


def _post(state: BridgeState, route: str, text: str, delivery_id: str) -> dict[str, Any]:
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    ts = str(int(time.time()))
    sig = hmac.new(state.secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        state.url(route),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": ts,
            "X-Webhook-Signature-V2": sig,
            "X-Request-ID": delivery_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - loopback only
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise BridgeError(f"gateway returned {exc.code} for {route}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise BridgeError(
            f"cannot reach the gateway webhook at {state.url(route)}: {exc.reason}. "
            "Is the gateway running with the webhook adapter enabled? Run bridge_setup."
        ) from exc


def read_reply(settings: Settings, state: BridgeState, delivery_id: str) -> str | None:
    """Last assistant message of the session the gateway opened for this delivery."""
    db = settings.home / "state.db"
    if not db.is_file():
        return None
    chat = f"webhook:{state.route}:{delivery_id}"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = con.execute(
            "select m.content from messages m join sessions s on s.id = m.session_id "
            "where s.chat_id = ? and m.role = 'assistant' and m.content is not null "
            "and length(trim(m.content)) > 0 order by m.id desc limit 1",
            (chat,),
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def ask(
    settings: Settings,
    prompt: str,
    *,
    wait_seconds: int = 45,
    echo: bool = True,
) -> dict[str, Any]:
    """Post ``prompt`` through the bridge and wait up to ``wait_seconds`` for the reply."""
    state = load_state(settings)
    if state is None:
        raise BridgeError("bridge is not set up; call bridge_setup first")
    delivery_id = uuid.uuid4().hex
    if echo:
        _post(state, state.echo_route, f"{state.label}: {prompt}", f"{delivery_id}-echo")
    ack = _post(state, state.route, prompt, delivery_id)

    deadline = time.time() + max(0, wait_seconds)
    reply: str | None = None
    while time.time() < deadline:
        reply = read_reply(settings, state, delivery_id)
        if reply:
            break
        time.sleep(2)
    return {
        "ok": True,
        "delivery_id": delivery_id,
        "chat": {"platform": state.platform, "chat_id": state.chat_id},
        "gateway_ack": ack,
        "reply": reply,
        "status": "done" if reply else "pending",
        "hint": None if reply else "call bridge_check(delivery_id) to fetch the reply later",
    }


def check(settings: Settings, delivery_id: str) -> dict[str, Any]:
    state = load_state(settings)
    if state is None:
        raise BridgeError("bridge is not set up; call bridge_setup first")
    reply = read_reply(settings, state, delivery_id)
    return {
        "ok": True,
        "delivery_id": delivery_id,
        "reply": reply,
        "status": "done" if reply else "pending",
    }


def status(settings: Settings) -> dict[str, Any]:
    state = load_state(settings)
    if state is None:
        return {"configured": False, "hint": "call bridge_setup"}
    return {
        "configured": True,
        "platform": state.platform,
        "chat_id": state.chat_id,
        "routes": [state.echo_route, state.route],
        "listen": f"127.0.0.1:{state.port}",
    }
