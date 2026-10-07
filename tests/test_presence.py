from ma_rpc import config
from ma_rpc.ma import ws_url
from ma_rpc.presence import build_activity, pick_cover, render, select_player, start_timestamp

PLAYER = {
    "display_name": "Kitchen", "available": True, "playback_state": "playing",
    "elapsed_time": 30.0, "elapsed_time_last_updated": 1000.0,
    "current_media": {"uri": "library://track/1", "title": "Song", "artist": "Band",
                      "album": "Record", "album_artist": "Band", "duration": 200},
}


def test_select_player_any_and_by_name():
    idle = {**PLAYER, "display_name": "Den", "playback_state": "idle"}
    assert select_player([idle, PLAYER], [])["display_name"] == "Kitchen"
    assert select_player([idle, PLAYER], ["kitchen"]) is PLAYER  # case-insensitive
    assert select_player([idle, PLAYER], ["Den"]) is None
    assert select_player([{**PLAYER, "available": False}], []) is None


def test_start_timestamp_handles_missing_update_time():
    assert start_timestamp(PLAYER, 1010.0) == 1010 - 40
    assert start_timestamp({**PLAYER, "elapsed_time_last_updated": None}, 1010.0) == 1010 - 30
    assert start_timestamp({"elapsed_time": None, "elapsed_time_last_updated": None}, 500.0) == 500


def test_start_timestamp_prefers_media_position_over_resetting_player_clock():
    # Browser players restart player.elapsed_time near 0 on resume; media position is the real one.
    p = {**PLAYER, "elapsed_time": 1.2, "elapsed_time_last_updated": 1000.0,
         "current_media": {**PLAYER["current_media"], "elapsed_time": 155.0, "elapsed_time_last_updated": 1000.0}}
    assert start_timestamp(p, 1010.0) == 1010 - 165


def test_render_missing_and_short():
    assert render("{title} - {artist}", {"title": "A", "artist": "B"}) == "A - B"
    assert render("{nope}x", {}) is None  # too short for Discord
    assert render("{title}", {"title": "x" * 300}) == "x" * 128


def test_pick_cover_never_leaks_api_key():
    lan = {"path": "http://192.168.0.2:8096/Items/abc123/Images/Primary?api_key=SECRET", "remotely_accessible": False}
    spotify = {"path": "https://i.scdn.co/image/xyz", "remotely_accessible": True}
    assert pick_cover([lan]) is None
    assert pick_cover([lan], "https://jf.example.com/") == "https://jf.example.com/Items/abc123/Images/Primary"
    assert pick_cover([lan, spotify]) == "https://i.scdn.co/image/xyz"
    assert "SECRET" not in str(pick_cover([lan], "https://jf.example.com"))
    assert pick_cover([{"path": "http://lan/x.jpg", "remotely_accessible": False}]) is None


def test_build_activity():
    cfg = config.load()
    act = build_activity(cfg, PLAYER, "https://img/x.jpg", 1010.0)
    assert act["details"] == "Song" and act["state"] == "Band" and act["large_text"] == "Record"
    assert act["start"] == 970 and act["end"] == 1170 and act["large_image"] == "https://img/x.jpg"
    cfg["display"].update(show_progress=False, show_cover=False, name="Music Assistant")
    act = build_activity(cfg, PLAYER, "https://img/x.jpg", 1010.0)
    assert "start" not in act and "large_image" not in act and act["name"] == "Music Assistant"


def test_ws_url():
    assert ws_url("http://ma.local:8095") == "ws://ma.local:8095/ws"
    assert ws_url("https://ma.example.com/") == "wss://ma.example.com/ws"
    assert ws_url("192.168.0.9:8095") == "ws://192.168.0.9:8095/ws"
    assert ws_url("ws://h:8095/ws") == "ws://h:8095/ws"
