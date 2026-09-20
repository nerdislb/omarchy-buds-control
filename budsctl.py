#!/usr/bin/env python3
"""Local JSON bridge for pbpctrl and an already-running BudsLink service.

Adapted from nerdislb/nbshell/plugins/buds-control (MIT, see THIRD_PARTY.md).
No pairing, installs, service termination, BlueZ configuration or network calls.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from typing import Any

SERVICE = "io.github.maniacx.BudsLink"
MANAGER_PATH = "/io/github/maniacx/BudsLink"
MANAGER_IFACE = SERVICE + ".DeviceManager"
DEVICE_IFACE = SERVICE + ".Device"
CLIENT_ID = "io.github.nerdislb.omarchy-buds-control"
DEVICE_PATH = re.compile(r"^/io/github/maniacx/BudsLink/Devices/[A-Za-z0-9_]+/[A-Za-z0-9_]+$")
PIXEL_PATH = re.compile(r"^pixel:([0-9A-F]{2}(?::[0-9A-F]{2}){5})$")
DEVICE_LINE = re.compile(r"^Device\s+([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s+(.+)$")
PIXEL_NAME = re.compile(r"\bPixel Buds Pro(?: 2)?\b", re.IGNORECASE)
PBP_MODES = {1: ("Off", "off"), 2: ("Transparency", "aware"),
             3: ("Noise Cancellation", "active"), 4: ("Adaptive", "adaptive")}


def run_text(command: list[str], timeout: float = 8) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          timeout=timeout, env={**os.environ, "LC_ALL": "C", "NO_COLOR": "1"}).stdout.strip()


def busctl(*arguments: str) -> Any:
    output = run_text(["busctl", "--user", "--json=short", *arguments])
    # Void D-Bus methods (HoldService, ReleaseService, UiAction) print nothing.
    return json.loads(output) if output else {}


def call(method: str, *arguments: str) -> Any:
    return busctl("call", SERVICE, MANAGER_PATH, MANAGER_IFACE, method, *arguments)


def property_value(path: str, name: str) -> Any:
    reply = busctl("get-property", SERVICE, path, DEVICE_IFACE, name)
    return reply.get("data")


def budslink_has_owner() -> bool:
    reply = busctl("call", "org.freedesktop.DBus", "/org/freedesktop/DBus",
                   "org.freedesktop.DBus", "NameHasOwner", "s", SERVICE)
    return reply.get("data") == [True]


@contextlib.contextmanager
def held_budslink():
    # Never auto-start BudsLink as a side effect of background polling.
    if not budslink_has_owner():
        raise RuntimeError("Open BudsLink first to use its headset controls.")
    call("HoldService", "s", CLIENT_ID)
    try:
        yield
    finally:
        try:
            call("ReleaseService", "s", CLIENT_ID)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass


def mode_options(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"label": str(config[f"toggle1Button{i}Name"])[:80], "value": i}
            for i in range(1, 5) if config.get(f"toggle1Button{i}Name")]


def connected_pixel_buds() -> tuple[str, str] | None:
    output = run_text(["bluetoothctl", "devices", "Connected"], timeout=5)
    for line in output.splitlines():
        match = DEVICE_LINE.fullmatch(line.strip())
        if not match:
            continue
        address, alias = match.groups()
        if PIXEL_NAME.search(alias):
            return address.upper(), alias[:120]
        # Bluetooth aliases can be changed; BlueZ's original Name is stable.
        info = run_text(["bluetoothctl", "info", address], timeout=5)
        name = re.search(r"^\s*Name:\s*(.+)$", info, re.MULTILINE)
        if name and PIXEL_NAME.search(name.group(1)):
            return address.upper(), alias[:120]
    return None


def pbp_mode_options() -> list[dict[str, Any]]:
    help_text = run_text(["pbpctrl", "set", "anc", "--help"], timeout=5)
    match = re.search(r"possible values:\s*([^\]]+)\]", help_text)
    # Fail closed if an incompatible CLI changes its grammar.
    if not match:
        raise RuntimeError("This pbpctrl version has an unrecognized noise-control interface.")
    supported = {v.strip() for v in match.group(1).split(",")}
    return [{"label": label, "value": value}
            for value, (label, command) in PBP_MODES.items() if command in supported]


def parse_pbp_battery(text: str) -> dict[str, tuple[int, str]]:
    batteries = {}
    names = {"case": "battery3", "left bud": "battery1", "right bud": "battery2"}
    for line in text.splitlines():
        match = re.fullmatch(r"\s*(case|left bud|right bud):\s+(unknown|(\d{1,3})%\s+\(([^)]+)\))\s*", line, re.IGNORECASE)
        if not match:
            continue
        key = names[match.group(1).lower()]
        if match.group(2).lower() == "unknown":
            batteries[key] = (0, "not-reported")
            continue
        level = int(match.group(3))
        if level > 100:
            continue
        detail = match.group(4).lower()
        status = {"charging": "charging", "not charging": "discharging", "discharging": "discharging", "full": "full"}.get(detail, "unknown")
        batteries[key] = (level, status)
    return batteries


def read_pbp_status(address: str, alias: str) -> dict[str, Any]:
    modes = pbp_mode_options()
    mode = run_text(["pbpctrl", "-d", address, "get", "anc"]).lower()
    modes_by_name = {command: value for value, (_, command) in PBP_MODES.items()}
    # A new/unknown mode must not hide otherwise valid battery readings.
    state: dict[str, Any] = {"toggle1State": modes_by_name.get(mode, 0), "toggle1Visible": bool(modes)}
    batteries = parse_pbp_battery(run_text(["pbpctrl", "-d", address, "show", "battery"]))
    if not batteries:
        raise RuntimeError("Pixel Buds returned unrecognized battery data. Refresh to retry.")
    for i in range(1, 4):
        level, status = batteries.get(f"battery{i}", (0, "not-reported"))
        state[f"battery{i}Level"], state[f"battery{i}Status"] = level, status
    # The bar summarises the earbuds, not the often-stale case charge.
    levels = [level for key, (level, status) in batteries.items()
              if key != "battery3" and status != "not-reported"]
    state["computedBatteryLevel"] = min(levels) if levels else None
    return {"ok": True, "available": True, "backend": "pbpctrl",
            "version": run_text(["pbpctrl", "--version"], 5).removeprefix("pbpctrl "),
            "devices": [{"path": f"pixel:{address}", "alias": alias, "config": {}, "state": state, "modes": modes}]}


def json_object(value: Any) -> dict[str, Any]:
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict):
        raise ValueError("BudsLink returned an invalid device object.")
    return result


def read_budslink_status() -> dict[str, Any]:
    with held_budslink():
        version = call("ServiceVersion").get("data", [])
        data = call("ListDevices").get("data", [])
        paths = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else []
        devices = []
        for path in paths[:8]:
            if not isinstance(path, str) or not DEVICE_PATH.fullmatch(path):
                continue
            config = json_object(property_value(path, "Config"))
            state = json_object(property_value(path, "State"))
            devices.append({"path": path, "alias": str(property_value(path, "Alias") or "Bluetooth earbuds")[:120],
                            "config": {}, "state": state, "modes": mode_options(config)})
        return {"ok": True, "available": True, "backend": "budslink",
                "version": str(version[0]) if version else "unknown", "devices": devices}


def read_status() -> dict[str, Any]:
    # Never terminate someone else's running headset application.
    if budslink_has_owner():
        result = read_budslink_status()
        if not result["devices"]:
            result["message"] = "No headset reported by BudsLink. Close BudsLink to use direct Pixel Buds controls."
        return result
    pixel = connected_pixel_buds()
    installed = bool(shutil.which("pbpctrl"))
    if pixel and installed:
        return read_pbp_status(*pixel)
    return {"ok": True, "available": installed, "backend": "pbpctrl" if installed else "",
            "version": "", "devices": [], "message":
            "Connect your Pixel Buds in Bluetooth, then refresh." if installed else
            "Install pbpctrl for Pixel Buds. BudsLink is optional for other supported headsets."}


def set_pbp_mode(path: str, value: int) -> dict[str, Any]:
    match = PIXEL_PATH.fullmatch(path)
    if not match or value not in PBP_MODES:
        raise ValueError("Invalid Pixel Buds mode request.")
    if budslink_has_owner():
        raise RuntimeError("BudsLink is running. Close it before using direct Pixel Buds controls.")
    device = connected_pixel_buds()
    if not device or device[0] != match.group(1):
        raise RuntimeError("This Pixel Buds device is no longer connected. Refresh first.")
    if value not in {int(option["value"]) for option in pbp_mode_options()}:
        raise ValueError("This pbpctrl version does not support the selected mode.")
    target = PBP_MODES[value][1]
    run_text(["pbpctrl", "-d", match.group(1), "set", "anc", target])
    actual = run_text(["pbpctrl", "-d", match.group(1), "get", "anc"]).lower()
    if actual != target:
        raise RuntimeError("The earbuds did not confirm the requested noise-control mode.")
    return {"ok": True, "confirmed": True, "path": path, "value": value}


def set_mode(path: str, value: int) -> dict[str, Any]:
    if PIXEL_PATH.fullmatch(path):
        return set_pbp_mode(path, value)
    if not DEVICE_PATH.fullmatch(path) or value not in range(1, 5):
        raise ValueError("Invalid headset mode request.")
    with held_budslink():
        data = call("ListDevices").get("data", [])
        if not data or path not in data[0]:
            raise RuntimeError("This headset is no longer connected. Refresh first.")
        config = json_object(property_value(path, "Config"))
        state = json_object(property_value(path, "State"))
        if state.get("toggle1Visible") is not True or value not in {o["value"] for o in mode_options(config)}:
            raise ValueError("This headset does not expose the selected mode.")
        busctl("call", SERVICE, path, DEVICE_IFACE, "UiAction", "si", "toggle1State", str(value))
        for _ in range(3):
            time.sleep(0.15)
            state = json_object(property_value(path, "State"))
            if state.get("toggle1State") == value:
                return {"ok": True, "confirmed": True, "path": path, "value": value}
    return {"ok": True, "confirmed": False, "path": path, "value": value}


@contextlib.contextmanager
def device_lock():
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if runtime.stat().st_uid != os.getuid():
        raise RuntimeError("The desktop runtime directory is not owned by this user.")
    fd = os.open(runtime / "omarchy-buds-control.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
            raise RuntimeError("Invalid headset control lock.")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def interrupted(_signum, _frame):
    # subprocess.run kills its child on exceptions; no orphan pbpctrl on reload.
    raise InterruptedError("Headset operation cancelled.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Read connected headset status as JSON")
    mode = commands.add_parser("mode", help="Change noise control and read it back")
    mode.add_argument("device", help="Device path returned by status")
    mode.add_argument("value", type=int, choices=range(1, 5))
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with device_lock():
            result = read_status() if args.command == "status" else set_mode(args.device, args.value)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except BlockingIOError:
        error = "Another headset operation is running. Try again shortly."
    except FileNotFoundError as exc:
        error = f"{Path(exc.filename or 'A required command').name} is not installed or unavailable."
    except subprocess.TimeoutExpired:
        error = "The headset did not respond in time. Check the connection and refresh."
    except subprocess.CalledProcessError:
        # Raw stderr may include addresses and protocol dumps; keep errors local and concise.
        error = "The headset backend failed. Check Bluetooth, close competing headset apps and refresh."
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        error = str(exc)[:300]
    installed = bool(shutil.which("pbpctrl"))
    print(json.dumps({"ok": False, "available": installed, "backend": "pbpctrl" if installed else "", "devices": [], "error": error}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
