"""Optional: detect Jellyfin playback so another Rich Presence tool (e.g. jellyfin-rpc) can win."""
import json
import urllib.request


def is_playing(cfg: dict) -> bool:
    jf = cfg["jellyfin"]
    if not (jf["url"] and jf["api_key"]):
        return False
    req = urllib.request.Request(f"{jf['url'].rstrip('/')}/Sessions", headers={"X-Emby-Token": jf["api_key"]})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            sessions = json.load(resp)
    except Exception:
        return False
    return any(
        s.get("NowPlayingItem") and not s.get("PlayState", {}).get("IsPaused")
        and (not jf["username"] or s.get("UserName") == jf["username"])
        for s in sessions
    )
