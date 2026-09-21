import pytest
import yaml

from hermes_mcp import configfile


def test_off_stays_a_string(tmp_path):
    path = tmp_path / "config.yaml"
    configfile.set_value(path, "platforms.telegram.reply_to_mode", configfile.coerce("off", "str"))
    written = yaml.safe_load(path.read_text())
    assert written["platforms"]["telegram"]["reply_to_mode"] == "off"
    assert written["platforms"]["telegram"]["reply_to_mode"] is not False


def test_bool_type_is_explicit(tmp_path):
    path = tmp_path / "config.yaml"
    value = configfile.coerce("off", "bool")
    configfile.set_value(path, "display.suppress_warning_notifications", value)
    assert yaml.safe_load(path.read_text())["display"]["suppress_warning_notifications"] is False


def test_existing_keys_are_preserved(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"model": {"default": "solar"}, "display": {"skin": "default"}}))
    configfile.set_value(path, "display.streaming", True)
    data = yaml.safe_load(path.read_text())
    assert data["model"]["default"] == "solar"
    assert data["display"]["skin"] == "default"
    assert data["display"]["streaming"] is True


def test_backup_is_written(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"a": 1}))
    configfile.set_value(path, "a", 2)
    assert yaml.safe_load(path.with_suffix(".yaml.bak").read_text()) == {"a": 1}


def test_get_missing_key_raises(tmp_path):
    with pytest.raises(configfile.ConfigError):
        configfile.get(tmp_path / "config.yaml", "nope.nothing")


def test_unknown_type_raises():
    with pytest.raises(configfile.ConfigError):
        configfile.coerce("1", "decimal")
