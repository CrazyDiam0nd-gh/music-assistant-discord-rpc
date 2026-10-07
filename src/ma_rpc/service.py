"""Run ma-rpc in the background at login: systemd (Linux), launchd (macOS), Startup folder (Windows).

Always launches `<this python> -m ma_rpc run`, so it works the same for pipx, venv or system installs.
"""
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import config

NAME = "ma-rpc"
LAUNCHD_LABEL = "io.github.ma-rpc"


def _run(*cmd, check=False):
    return subprocess.run(list(cmd), check=check, capture_output=True, text=True)


# ---- Linux ---------------------------------------------------------------------------------

def _unit_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "systemd" / "user" / f"{NAME}.service"


def _install_linux():
    unit = _unit_path()
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(
        "[Unit]\nDescription=Music Assistant Discord Rich Presence\n"
        "After=network-online.target\n\n"
        f"[Service]\nType=simple\nExecStart={sys.executable} -m ma_rpc run\n"
        "Restart=on-failure\nRestartSec=10\n\n"
        "[Install]\nWantedBy=default.target\n",
        encoding="utf-8",
    )
    _run("systemctl", "--user", "daemon-reload", check=True)
    _run("systemctl", "--user", "enable", "--now", f"{NAME}.service", check=True)
    print(f"Installed {unit}\nStatus:  systemctl --user status {NAME}\nLogs:    journalctl --user -u {NAME} -f")


def _uninstall_linux():
    _run("systemctl", "--user", "disable", "--now", f"{NAME}.service")
    _unit_path().unlink(missing_ok=True)
    _run("systemctl", "--user", "daemon-reload")


# ---- macOS ---------------------------------------------------------------------------------

def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _install_macos():
    path = _plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    log = config.config_dir() / "ma-rpc.log"
    with open(path, "wb") as fh:
        plistlib.dump({
            "Label": LAUNCHD_LABEL,
            "ProgramArguments": [sys.executable, "-m", "ma_rpc", "run"],
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
        }, fh)
    _run("launchctl", "unload", str(path))
    _run("launchctl", "load", str(path), check=True)
    print(f"Installed {path}\nLogs: {log}")


def _uninstall_macos():
    path = _plist_path()
    _run("launchctl", "unload", str(path))
    path.unlink(missing_ok=True)


# ---- Windows -------------------------------------------------------------------------------

def _startup_script() -> Path:
    return (Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            / "Startup" / f"{NAME}.vbs")


def _pythonw() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


def pid_file() -> Path:
    return config.config_dir() / "ma-rpc.pid"


def _install_windows():
    script = _startup_script()
    script.parent.mkdir(parents=True, exist_ok=True)
    # Hidden window (0), don't wait (False). Doubled quotes escape quotes in VBScript.
    script.write_text(
        'CreateObject("Wscript.Shell").Run """' + _pythonw() + '"" -m ma_rpc run", 0, False\n'
    )
    subprocess.Popen([_pythonw(), "-m", "ma_rpc", "run"],
                     creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    print(f"Installed {script} (starts at login) and started it now.\nStop with: ma-rpc uninstall-service")


def _uninstall_windows():
    _startup_script().unlink(missing_ok=True)
    pf = pid_file()
    if pf.exists():
        _run("taskkill", "/F", "/PID", pf.read_text().strip())
        pf.unlink(missing_ok=True)


# ---- public --------------------------------------------------------------------------------

def install():
    {"linux": _install_linux, "darwin": _install_macos, "win32": _install_windows}.get(
        sys.platform, _unsupported)()


def uninstall():
    {"linux": _uninstall_linux, "darwin": _uninstall_macos, "win32": _uninstall_windows}.get(
        sys.platform, _unsupported)()
    print("Service removed.")


def _unsupported():
    raise SystemExit(f"No service support for {sys.platform}; run `ma-rpc run` manually.")
