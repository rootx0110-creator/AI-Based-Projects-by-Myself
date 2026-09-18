"""Windows-only helpers: link-speed lookup and PDH counter fallbacks.

Link speed comes from WMI first and the registry as a fallback. On non-Windows
platforms every function degrades to a safe stub so tests run on any OS.
"""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"


def link_speed_bps(iface_name: str) -> int:
    """Return link speed in bits/sec for an interface, 0 when unknown.

    Tries WMI (Win32_NetworkAdapter.Speed), then the registry
    (HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4D36E972-...}) via _winreg.
    """
    if not IS_WINDOWS:
        return 0
    speed = _link_speed_wmi(iface_name)
    if speed:
        return speed
    return _link_speed_registry(iface_name)


def _link_speed_wmi(iface_name: str) -> int:
    """Query Win32_NetworkAdapter.Speed via WMI; 0 on failure."""
    try:
        import wmi  # type: ignore[import-not-found]

        for adapter in wmi.WMI().Win32_NetworkAdapter(NetConnectionID=iface_name):
            return int(adapter.Speed or 0)
    except Exception as exc:  # wmi missing, COM not ready, access denied...
        log.debug("WMI link-speed lookup failed for %s: %s", iface_name, exc)
    return 0


def _link_speed_registry(iface_name: str) -> int:
    """Read '*Speed' / 'SpeedDuplex' from the NIC registry class key; 0 on failure."""
    try:
        import winreg  # type: ignore[import-not-found]

        key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                with winreg.OpenKey(root, sub) as key:
                    try:
                        name, _ = winreg.QueryValueEx(key, "NetCfgInstanceId")
                    except OSError:
                        continue
                    friendly = ""
                    try:
                        friendly, _ = winreg.QueryValueEx(key, "DriverDesc")
                    except OSError:
                        pass
                    if iface_name in (name, friendly):
                        for value_name in ("*Speed", "SpeedDuplex"):
                            try:
                                return int(winreg.QueryValueEx(key, value_name)[0])
                            except OSError:
                                continue
    except Exception as exc:
        log.debug("Registry link-speed lookup failed for %s: %s", iface_name, exc)
    return 0


def pdh_bytes_per_sec(iface_name: str) -> tuple[int, int] | None:
    """Return (bytes_sent/sec, bytes_recv/sec) from PDH counters, or None.

    Used as a fallback when psutil deltas look implausible (e.g. some VPN
    adapters that never bump their psutil counters).
    """
    if not IS_WINDOWS:
        return None
    try:
        import win32pdh  # type: ignore[import-not-found]

        counter_paths = [
            rf"\Network Interface({iface_name})\Bytes Sent/sec",
            rf"\Network Interface({iface_name})\Bytes Received/sec",
        ]
        query = win32pdh.OpenQuery()
        try:
            counters = [win32pdh.AddCounter(query, p) for p in counter_paths]
            win32pdh.CollectQueryData(query)
            vals = [win32pdh.GetFormattedCounterValue(c, win32pdh.PDH_FMT_DOUBLE) for c in counters]
        finally:
            win32pdh.CloseQuery(query)
        return int(vals[0]), int(vals[1])
    except Exception as exc:
        log.debug("PDH fallback failed for %s: %s", iface_name, exc)
        return None


def is_admin() -> bool:
    """True when the current process has elevated (Administrator) rights."""
    if not IS_WINDOWS:
        import os

        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
