"""Pure functions: turn Music Assistant player data into a Discord activity."""
import re
import string


def select_player(players: list, wanted: list):
    """First available, playing player with media. `wanted` empty = any player."""
    names = {w.casefold() for w in wanted}
    for p in players:
        if names and (p.get("display_name") or "").casefold() not in names:
            continue
        if p.get("available") and p.get("playback_state") == "playing" and p.get("current_media"):
            return p
    return None


def start_timestamp(player: dict, now: float) -> int:
    """Unix time the track 'started', so Discord's progress bar lines up.

    Uses the current media's position: the player's own elapsed_time restarts near 0 on every
    resume (browser players), so it is only a fallback. MA also briefly reports
    elapsed_time_last_updated=None right after a skip.
    """
    media = player.get("current_media") or {}
    src = media if media.get("elapsed_time") is not None and media.get("elapsed_time_last_updated") else player
    elapsed = (src.get("elapsed_time") or 0) + (now - (src.get("elapsed_time_last_updated") or now))
    return int(now - elapsed)


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def render(template: str, fields: dict, limit: int = 128):
    """Fill a template. Returns None if the result is too short for Discord (<2 chars)."""
    text = string.Formatter().vformat(template, (), _SafeDict(fields)).strip()[:limit]
    return text if len(text) >= 2 else None


def pick_cover(images: list, jellyfin_public_url: str = ""):
    """A cover URL Discord's servers can fetch, or None.

    - Remotely accessible https images (Spotify, Tidal, ...) are used as-is.
    - Jellyfin images only have a LAN URL (with an API key in the query string) in MA, so they are
      rewritten to `jellyfin.public_url` with the key removed. Without it they are skipped.
    The API key is never returned.
    """
    for img in images or []:
        path = img.get("path") or ""
        match = re.search(r"/Items/([0-9a-fA-F]+)/Images/Primary", path)
        if match:
            if jellyfin_public_url:
                return f"{jellyfin_public_url.rstrip('/')}/Items/{match.group(1)}/Images/Primary"
            continue
        if img.get("remotely_accessible") and path.startswith("https://") and "api_key" not in path:
            return path
    return None


def cover_images(item: dict) -> list:
    """Album art first, then the track's own art."""
    album = (item.get("album") or {}).get("metadata") or {}
    return (album.get("images") or []) + ((item.get("metadata") or {}).get("images") or [])


def build_activity(cfg: dict, player: dict, cover, now: float) -> dict:
    """kwargs for pypresence's update(). Omits any field that would be empty."""
    media = player["current_media"]
    disp = cfg["display"]
    fields = {
        "title": media.get("title") or "",
        "artist": media.get("artist") or "",
        "album": media.get("album") or "",
        "album_artist": media.get("album_artist") or "",
    }
    activity = {}
    for key, tmpl_key in (("details", "details"), ("state", "state"), ("large_text", "large_text")):
        value = render(disp.get(tmpl_key, ""), fields)
        if value:
            activity[key] = value
    if disp.get("name"):
        activity["name"] = disp["name"][:128]
    if disp.get("show_progress", True):
        start = start_timestamp(player, now)
        activity["start"] = start
        if media.get("duration"):
            activity["end"] = start + int(media["duration"])
    if disp.get("show_cover", True) and cover:
        activity["large_image"] = cover
    return activity
