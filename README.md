<p align="center"><img src="docs/icon.png" alt="Music Assistant Discord Rich Presence" width="128"></p>

<h1 align="center">Music Assistant Discord Rich Presence</h1>

Show what's playing in [Music Assistant](https://music-assistant.io) as your **Discord Rich Presence**: title, artist, album, cover art and a live progress bar, shown as "Listening to ...".

Works on **Linux**, **Windows** and **macOS**. Install, answer a few questions, done.

```
$ ma-rpc setup
$ ma-rpc install-service     # starts automatically at login
```

## Requirements

- Music Assistant 2.x reachable from the PC running Discord (the Home Assistant add-on works; default port `8095`)
- The **Discord desktop app** running on the same PC (Rich Presence talks to it locally; the web app isn't supported)
- Python 3.9 or newer

## Install

### Linux / macOS

```bash
# pipx keeps it isolated (sudo apt install pipx  /  brew install pipx)
pipx install git+https://github.com/CrazyDiam0nd-gh/music-assistant-discord-rpc
ma-rpc setup
ma-rpc install-service
```

### Windows (PowerShell)

```powershell
py -m pip install --user pipx
py -m pipx ensurepath          # then open a new PowerShell window
pipx install git+https://github.com/CrazyDiam0nd-gh/music-assistant-discord-rpc
ma-rpc setup
ma-rpc install-service
```

No pipx? `pip install git+https://github.com/CrazyDiam0nd-gh/music-assistant-discord-rpc` works too.

## Setup walkthrough

You need two things. `ma-rpc setup` asks for both.

**1. A Music Assistant token.** In the Music Assistant web UI: *Settings > Profile > Long-lived access tokens > Create token*. Copy it somewhere; it is shown once.

**2. A Discord application.** Go to <https://discord.com/developers/applications>, click **New Application**, and give it the name you want to see on your profile (for example "Music Assistant"). Copy the **Application ID** from *General Information*. Each person makes their own, so the name and any icon are yours.

Then:

```
ma-rpc setup          # URL, token, Application ID, pick your players
ma-rpc run            # try it in the foreground (Ctrl+C to stop)
ma-rpc install-service
```

`ma-rpc run --dry-run` prints what *would* be sent without touching Discord, which is handy for checking the config.

## What it shows

| | |
|---|---|
| Top line | track title |
| Second line | artist |
| Hover text on the cover | album |
| Progress bar | elapsed / duration, kept in sync across seeks and skips |
| Cover art | album art when Discord can fetch it (see below) |

Presence clears when playback pauses or stops.

### Cover art

Discord's servers load the image, so it has to be a public URL:

- **Spotify, Tidal, Qobuz, etc.:** works automatically.
- **Jellyfin library:** Music Assistant only knows your server's LAN address (with an API key in the URL, which this tool never sends to Discord). Set `jellyfin.public_url` to the address your Jellyfin server has on the internet and the cover is rewritten to use it.
- **Other local libraries (filesystem, SMB):** no public URL exists, so no cover is shown.

## Commands

| Command | |
|---|---|
| `ma-rpc setup` | interactive setup, safe to re-run |
| `ma-rpc players` | list player names |
| `ma-rpc run [--dry-run]` | run in the foreground |
| `ma-rpc install-service` | start at login (systemd / launchd / Startup folder) |
| `ma-rpc uninstall-service` | stop and remove it |
| `ma-rpc config-path` | where the config file is |

## Configuration

`ma-rpc setup` writes the file; edit it for anything else. Location:

| OS | Path |
|---|---|
| Linux | `~/.config/ma-rpc/config.json` |
| macOS | `~/.config/ma-rpc/config.json` |
| Windows | `%APPDATA%\ma-rpc\config.json` |

```jsonc
{
  "music_assistant": { "url": "http://192.168.0.10:8095", "token": "..." },
  "discord": { "application_id": "123456789012345678" },
  "players": ["Kitchen speaker"],     // display names; [] = any player that is playing
  "poll_seconds": 5,
  "display": {
    "details": "{title}",             // placeholders: {title} {artist} {album} {album_artist}
    "state": "{artist}",
    "large_text": "{album}",
    "show_cover": true,
    "show_progress": true,
    "name": ""                        // optional: replaces the app name after "Listening to"
  },
  "jellyfin": {                       // all optional
    "public_url": "https://jellyfin.example.com",
    "url": "http://192.168.0.5:8096", "api_key": "...", "username": "me"
  }
}
```

- Emoji in templates work: `"details": "🎧 {title}"`.
- The token can come from the `MA_RPC_TOKEN` environment variable instead of the file. `MA_RPC_CONFIG_DIR` changes the config folder.
- On Linux/macOS the config file is created with `600` permissions because it holds your token. Don't commit it.
- Browser players (the Music Assistant web UI) are listed as e.g. `Web (Firefox on Linux)`. They are matched **by name**, since their IDs change every session.

### Using it alongside jellyfin-rpc

If you also run [jellyfin-rpc](https://github.com/Radiicall/jellyfin-rpc), fill in `jellyfin.url`, `api_key` and `username`. While that Jellyfin user is playing something, ma-rpc clears its own presence and lets jellyfin-rpc show. Without these, both tools update the same Discord client and the last one wins.

## Running at login

`ma-rpc install-service` registers it in the usual place for each OS:

| OS | Mechanism | Logs / control |
|---|---|---|
| Linux | systemd **user** unit `ma-rpc.service` | `systemctl --user status ma-rpc`, `journalctl --user -u ma-rpc -f` |
| macOS | launchd agent `io.github.ma-rpc` | `~/.config/ma-rpc/ma-rpc.log` |
| Windows | hidden script in your Startup folder | stop with `ma-rpc uninstall-service` |

It runs the same Python that installed it, so pipx installs work as-is. Restart after config changes (Linux: `systemctl --user restart ma-rpc`).

> The Windows and macOS service installers are untested by the author on real machines. Reports and fixes welcome.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Nothing shows on Discord | Discord **desktop** app must be running. *Settings > Activity Privacy > Share my activity* on. Run `ma-rpc run --dry-run` to confirm it sees playback. |
| `Authentication is required` | Missing or revoked token. Create a new one and run `ma-rpc setup`. |
| `cannot connect to Music Assistant` | Check the URL and port, and that the PC can reach it. |
| Wrong name after "Listening to" | That's your Discord application's name. Rename it, then fully quit Discord (tray icon > Quit) and reopen; Discord caches names. |
| No cover art | See *Cover art*. The track's source needs a public image URL. |
| Shows the wrong player | Set `players` to the names from `ma-rpc players`. |
| Flatpak/Snap Discord on Linux | The IPC socket may be inside the sandbox. Flatpak: `ln -sf $XDG_RUNTIME_DIR/app/com.discordapp.Discord/discord-ipc-0 $XDG_RUNTIME_DIR/discord-ipc-0` |

## Development

```bash
git clone https://github.com/CrazyDiam0nd-gh/music-assistant-discord-rpc && cd music-assistant-discord-rpc
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

The pure logic (player selection, timestamps, templates, cover URL handling) lives in `src/ma_rpc/presence.py` and is unit-tested; CI runs the tests on Linux, Windows and macOS.

## License

MIT
