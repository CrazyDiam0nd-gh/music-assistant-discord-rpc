"""Config file handling. Location follows each OS's convention:

Linux/macOS: $XDG_CONFIG_HOME/ma-rpc/config.json (default ~/.config/ma-rpc/)
Windows:     %APPDATA%\\ma-rpc\\config.json

Set MA_RPC_CONFIG_DIR to override the directory, MA_RPC_TOKEN to override the token.
"""
import copy
import json
import os
from pathlib import Path

DEFAULTS = {
    "music_assistant": {"url": "http://localhost:8095", "token": ""},
    "discord": {"application_id": ""},
    # Player display names to show. Empty list = any player that is playing.
    "players": [],
    "poll_seconds": 5,
    "display": {
        # Placeholders: {title} {artist} {album} {album_artist}
        "details": "{title}",
        "state": "{artist}",
        "large_text": "{album}",
        "show_cover": True,
        "show_progress": True,
        # Keep presence up while paused (players that report "paused"; browser players report "idle").
        "show_paused": True,
        "paused_state": "⏸ Paused · {artist}",
        # Optional: replaces the app name shown after "Listening to".
        "name": "",
    },
    # Optional. Lets Jellyfin Rich Presence tools take priority, and lets covers
    # from a Jellyfin library be shown (Music Assistant only has a LAN URL for them).
    "jellyfin": {"url": "", "public_url": "", "api_key": "", "username": ""},
}


def config_dir() -> Path:
    override = os.environ.get("MA_RPC_CONFIG_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ma-rpc"


def config_path() -> Path:
    return config_dir() / "config.json"


def _merge(base: dict, new: dict) -> dict:
    for key, value in new.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    path = config_path()
    if path.exists():
        _merge(cfg, json.loads(path.read_text(encoding="utf-8")))
    if os.environ.get("MA_RPC_TOKEN"):
        cfg["music_assistant"]["token"] = os.environ["MA_RPC_TOKEN"]
    return cfg


def save(cfg: dict) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)  # contains the token
    return path


def validate(cfg: dict) -> list:
    problems = []
    if not str(cfg["discord"]["application_id"]).strip():
        problems.append("discord.application_id is empty (create an app at "
                        "https://discord.com/developers/applications)")
    if not cfg["music_assistant"]["url"].strip():
        problems.append("music_assistant.url is empty")
    return problems
