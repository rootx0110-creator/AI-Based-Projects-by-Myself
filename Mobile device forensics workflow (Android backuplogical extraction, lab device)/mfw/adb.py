"""Thin ADB wrapper (external adb.exe via subprocess)."""
from __future__ import annotations

import os
import subprocess

COMMON_ADB_PATHS = [
    r"C:\platform-tools\adb.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
    os.path.expandvars(r"%ANDROID_HOME%\platform-tools\adb.exe"),
    r"C:\Android\platform-tools\adb.exe",
    "/usr/bin/adb",
    "/opt/homebrew/bin/adb",
]

ADB_TIMEOUT = 15


def find_adb() -> str | None:
    """Locate adb.exe on PATH or common SDK locations."""
    from shutil import which
    found = which("adb")
    if found:
        return found
    for p in COMMON_ADB_PATHS:
        if os.path.isfile(p):
            return p
    return None


def _run(adb: str, args: list[str], timeout: int = ADB_TIMEOUT) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [adb, *args], capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "[adb] timed out"
    except OSError as exc:
        return 1, f"[adb] failed to launch: {exc}"


def adb_version(adb: str) -> str:
    rc, out = _run(adb, ["version"])
    if rc != 0:
        return "unavailable"
    for line in out.splitlines():
        if line.startswith("Android Debug Bridge"):
            return line.strip()
    return out.strip().splitlines()[0] if out.strip() else "unavailable"


def list_devices(adb: str) -> list[dict[str, str]]:
    rc, out = _run(adb, ["devices", "-l"])
    devices: list[dict[str, str]] = []
    if rc != 0:
        return devices
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            dev = {"serial": parts[0], "state": parts[1]}
            for part in parts[2:]:
                if ":" in part:
                    k, _, v = part.partition(":")
                    dev[k] = v.strip()
            devices.append(dev)
    return devices


def device_info(adb: str, serial: str) -> dict[str, str]:
    """Read selected system properties via getprop."""
    props_wanted = {
        "ro.product.manufacturer": "manufacturer",
        "ro.product.model": "model",
        "ro.product.device": "device",
        "ro.build.version.release": "android_version",
        "ro.build.version.sdk": "sdk",
        "ro.build.version.security_patch": "security_patch",
        "ro.serialno": "serial",
        "ro.build.display.id": "build",
    }
    info: dict[str, str] = {}
    for prop, key in props_wanted.items():
        rc, out = _run(adb, ["-s", serial, "shell", "getprop", prop])
        info[key] = out.strip() if rc == 0 and out.strip() else ""
    return info


def run_backup(adb: str, serial: str, out_path: str, timeout: int = 240) -> tuple[bool, str]:
    """Logical acquisition: adb backup of contacts/sms/settings providers."""
    args = [
        "-s", serial, "backup",
        "-noapk", "-noobb", "-noshared", "-all",
        "-f", out_path,
    ]
    try:
        proc = subprocess.run(
            [adb, *args], capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 1024
        return ok, out.strip() or ("backup written" if ok else "backup failed or empty")
    except subprocess.TimeoutExpired:
        return False, f"[adb backup] timed out after {timeout}s (was 'Back up my data' confirmed on device?)"
    except OSError as exc:
        return False, f"[adb backup] failed to launch: {exc}"


def list_packages(adb: str, serial: str, third_party: bool = True) -> tuple[bool, str]:
    flag = "-3" if third_party else "-s"
    rc, out = _run(adb, ["-s", serial, "shell", "pm", "list", "packages", flag], timeout=60)
    return rc == 0, out


def screenshot(adb: str, serial: str, out_path: str) -> tuple[bool, str]:
    try:
        with open(out_path, "wb") as fh:
            proc = subprocess.run(
                [adb, "-s", serial, "exec-out", "screencap", "-p"],
                stdout=fh, stderr=subprocess.PIPE, timeout=30,
            )
        ok = proc.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 500
        return ok, "screencap ok" if ok else f"screencap failed: {proc.stderr.decode(errors='replace')[:200]}"
    except subprocess.TimeoutExpired:
        return False, "[screencap] timed out"
    except OSError as exc:
        return False, f"[screencap] failed: {exc}"
