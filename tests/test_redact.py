from hermes_mcp.redact import PLACEHOLDER, redact


def test_telegram_token_is_removed():
    text = "TELEGRAM_BOT_TOKEN=8123456789:AAH3kLmNopQrsTuvWxYz0123456789abcdef"
    cleaned = redact(text)
    assert "AAH3kLmNop" not in cleaned
    assert PLACEHOLDER in cleaned


def test_bare_token_shape_is_removed():
    text = "connecting bot 8123456789:AAH3kLmNopQrsTuvWxYz0123456789abcdef now"
    assert "AAH3kLmNop" not in redact(text)


def test_provider_keys_are_removed():
    for secret in (
        "sk-ant-oat01-abcdefghijklmnop",
        "ghp_abcdefghijklmnopqrstuvwxyz0123",
        "xoxb-1234567890-abcdefghij",
        "AKIAIOSFODNN7EXAMPLE",
    ):
        assert secret not in redact(f"value: {secret}")


def test_ordinary_output_survives():
    text = "Gateway is supervised by launchd (PID 75335)"
    assert redact(text) == text


def test_empty_input():
    assert redact("") == ""
