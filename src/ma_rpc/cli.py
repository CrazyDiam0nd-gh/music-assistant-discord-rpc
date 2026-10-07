import argparse
import asyncio
import getpass
import os
import sys

from . import __version__, config, service
from .ma import MAClient, MAError
from .runner import run


def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default and not secret else (" [keep current]" if default else "")
    answer = (getpass.getpass if secret else input)(f"{prompt}{suffix}: ").strip()
    return answer or default


async def _list_players(cfg: dict) -> list:
    async with MAClient(cfg["music_assistant"]["url"], cfg["music_assistant"]["token"]) as ma:
        return await ma.players()


def cmd_players(_args) -> int:
    try:
        players = asyncio.run(_list_players(config.load()))
    except MAError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for p in players:
        state = p.get("playback_state") if p.get("available") else "offline"
        print(f"{p.get('display_name')}  ({state})")
    return 0


def cmd_setup(_args) -> int:
    cfg = config.load()
    ma, dc = cfg["music_assistant"], cfg["discord"]
    print("ma-rpc setup. Press Enter to keep the value in [brackets].\n")
    ma["url"] = _ask("Music Assistant URL", ma["url"])
    print("\nCreate a token in Music Assistant: Settings > Profile > Long-lived access tokens.")
    ma["token"] = _ask("Token", ma["token"], secret=True)
    print("\nCreate a Discord application at https://discord.com/developers/applications "
          "(its name is shown on your profile),\nthen copy its Application ID.")
    dc["application_id"] = _ask("Discord Application ID", str(dc["application_id"]))

    try:
        players = asyncio.run(_list_players(cfg))
    except MAError as exc:
        print(f"\nCould not reach Music Assistant: {exc}")
        if input("Save the config anyway? [y/N]: ").strip().lower() != "y":
            return 1
        players = []
    if players:
        print("\nPlayers:")
        for i, p in enumerate(players, 1):
            print(f"  {i}. {p.get('display_name')}")
        picked = input("Show which players? Numbers separated by commas, Enter for any: ").strip()
        try:
            cfg["players"] = [players[int(n) - 1]["display_name"] for n in picked.split(",") if n.strip()]
        except (ValueError, IndexError):
            print("Didn't understand that; showing any player.")
            cfg["players"] = []

    path = config.save(cfg)
    print(f"\nSaved {path}")
    for problem in config.validate(cfg):
        print(f"warning: {problem}")
    print("Next: `ma-rpc run` to try it, then `ma-rpc install-service` to start it at login.")
    return 0


def cmd_run(args) -> int:
    cfg = config.load()
    problems = config.validate(cfg) if not args.dry_run else []
    if problems:
        print("Config problems (run `ma-rpc setup`):\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    config.config_dir().mkdir(parents=True, exist_ok=True)
    pid = service.pid_file()
    if sys.platform == "win32":  # lets `uninstall-service` stop the hidden background process
        pid.write_text(str(os.getpid()))
    try:
        asyncio.run(run(cfg, dry_run=args.dry_run))
    except KeyboardInterrupt:
        pass
    finally:
        pid.unlink(missing_ok=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ma-rpc", description="Discord Rich Presence for Music Assistant")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="interactive first-time setup").set_defaults(func=cmd_setup)
    sub.add_parser("players", help="list Music Assistant players").set_defaults(func=cmd_players)
    runp = sub.add_parser("run", help="run in the foreground")
    runp.add_argument("--dry-run", action="store_true", help="print the activity instead of sending it to Discord")
    runp.set_defaults(func=cmd_run)
    sub.add_parser("install-service", help="start automatically at login").set_defaults(
        func=lambda _a: service.install() or 0)
    sub.add_parser("uninstall-service", help="remove the login service").set_defaults(
        func=lambda _a: service.uninstall() or 0)
    sub.add_parser("config-path", help="print the config file location").set_defaults(
        func=lambda _a: print(config.config_path()) or 0)
    args = parser.parse_args(argv)
    return args.func(args)
