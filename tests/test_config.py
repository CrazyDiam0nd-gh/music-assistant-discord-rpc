import json

from ma_rpc import config


def test_defaults_and_merge(tmp_path, monkeypatch):
    monkeypatch.setenv("MA_RPC_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("MA_RPC_TOKEN", raising=False)
    (tmp_path / "config.json").write_text(json.dumps({"discord": {"application_id": "1"}, "display": {"state": "{album}"}}))
    cfg = config.load()
    assert cfg["discord"]["application_id"] == "1"
    assert cfg["display"]["state"] == "{album}" and cfg["display"]["details"] == "{title}"  # untouched default kept
    assert config.validate(cfg) == []


def test_env_token_and_save_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MA_RPC_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("MA_RPC_TOKEN", "from-env")
    cfg = config.load()
    assert cfg["music_assistant"]["token"] == "from-env"
    cfg["players"] = ["Kitchen"]
    config.save(cfg)
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["players"] == ["Kitchen"]
    assert config.validate(cfg)  # application_id empty


def test_dir_conventions(monkeypatch):
    monkeypatch.delenv("MA_RPC_CONFIG_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    monkeypatch.setenv("APPDATA", "C:\\Users\\me\\AppData\\Roaming")
    assert config.config_dir().name == "ma-rpc"
