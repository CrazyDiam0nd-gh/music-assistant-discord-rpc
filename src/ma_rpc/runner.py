"""Main loop: poll Music Assistant, keep Discord presence in sync."""
import asyncio
import json
import time

from . import jellyfin
from .ma import MAClient, MAError
from .presence import build_activity, cover_images, pick_cover, select_player, start_timestamp


async def _session(cfg: dict, dry_run: bool):
    rpc = None
    if not dry_run:
        from pypresence import ActivityType, AioPresence
        rpc = AioPresence(str(cfg["discord"]["application_id"]))
        await rpc.connect()

    def log(msg):
        print(msg, flush=True)

    shown = None  # (uri, start, paused) last sent
    cover = None
    jellyfin_on = bool(cfg["jellyfin"]["url"] and cfg["jellyfin"]["api_key"])
    async with MAClient(cfg["music_assistant"]["url"], cfg["music_assistant"]["token"]) as ma:
        log(f"connected to Music Assistant {ma.server_info.get('server_version', '?')}")
        while True:
            player = select_player(await ma.players(), cfg["players"], cfg["display"].get("show_paused", True))
            if player and jellyfin_on and await asyncio.to_thread(jellyfin.is_playing, cfg):
                player = None  # Jellyfin has priority
            if player:
                media = player["current_media"]
                now = time.time()
                start = start_timestamp(player, now)
                paused = player["playback_state"] == "paused"
                if (shown is None or shown[0] != media["uri"] or shown[2] != paused
                        or (not paused and abs(shown[1] - start) > 3)):
                    if shown is None or shown[0] != media["uri"]:
                        cover = None
                        if cfg["display"].get("show_cover", True):
                            try:
                                cover = pick_cover(cover_images(await ma.item_by_uri(media["uri"])),
                                                   cfg["jellyfin"]["public_url"])
                            except MAError:
                                pass
                    activity = build_activity(cfg, player, cover, now)
                    if dry_run:
                        log(json.dumps(activity, ensure_ascii=False))
                    else:
                        await rpc.update(activity_type=ActivityType.LISTENING, **activity)
                    shown = (media["uri"], start, paused)
            elif shown:
                if dry_run:
                    log("(cleared)")
                else:
                    await rpc.clear()
                shown = None
            await asyncio.sleep(cfg["poll_seconds"])


async def run(cfg: dict, dry_run: bool = False):
    """Run forever, reconnecting on failure."""
    while True:
        try:
            await _session(cfg, dry_run)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"ma-rpc: {exc!r}; retrying in 10s", flush=True)
            await asyncio.sleep(10)
