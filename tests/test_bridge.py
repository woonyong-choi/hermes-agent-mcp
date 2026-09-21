import hashlib
import hmac
import json
import sqlite3
from pathlib import Path

from hermes_mcp import bridge
from hermes_mcp.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        binary="/nonexistent/hermes",
        home=tmp_path,
        timeout=5,
        ask_timeout=5,
        allow_shell=False,
        allow_write=True,
        max_output=1000,
    )


def test_status_before_setup(tmp_path):
    assert bridge.status(_settings(tmp_path))["configured"] is False


def test_state_roundtrip_is_private(tmp_path):
    s = _settings(tmp_path)
    state = bridge.BridgeState(secret="x" * 64, platform="telegram", chat_id="123")
    bridge._save_state(s, state)
    assert oct((tmp_path / bridge.STATE_NAME).stat().st_mode)[-3:] == "600"
    loaded = bridge.load_state(s)
    assert loaded.chat_id == "123" and loaded.echo_route == "claude-echo"


def test_guess_chat_picks_latest(tmp_path):
    db = tmp_path / "state.db"
    con = sqlite3.connect(db)
    con.execute(
        "create table sessions "
        "(id text, source text, chat_id text, display_name text, started_at real)"
    )
    con.execute("insert into sessions values ('a','telegram','111','old',1.0)")
    con.execute("insert into sessions values ('b','telegram','222','new',2.0)")
    con.execute("insert into sessions values ('c','discord','333','other',3.0)")
    con.commit()
    con.close()
    assert bridge._guess_chat(_settings(tmp_path), "telegram") == ("222", "new")


def test_read_reply_finds_assistant_message(tmp_path):
    s = _settings(tmp_path)
    state = bridge.BridgeState(secret="x", platform="telegram", chat_id="1")
    db = tmp_path / "state.db"
    con = sqlite3.connect(db)
    con.execute("create table sessions (id text, chat_id text)")
    con.execute(
        "create table messages (id integer primary key, session_id text, role text, content text)"
    )
    con.execute("insert into sessions values ('s1','webhook:claude:abc')")
    con.execute("insert into messages (session_id, role, content) values ('s1','user','hi')")
    con.execute("insert into messages (session_id, role, content) values ('s1','assistant','')")
    con.execute("insert into messages (session_id, role, content) values ('s1','assistant','done')")
    con.commit()
    con.close()
    assert bridge.read_reply(s, state, "abc") == "done"
    assert bridge.read_reply(s, state, "nope") is None


def test_signature_matches_hermes_v2_scheme():
    secret, ts, body = "s3cr3t", "1700000000", json.dumps({"text": "hi"}).encode()
    expected = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert len(expected) == 64
