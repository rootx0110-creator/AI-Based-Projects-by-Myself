"""Wireless interface discovery + capability detection for live mode.

Uses Scapy + Npcap on Windows, airodump-ng/iw on Linux. Everything in here is
safe to call in simulation mode too (it only ever returns empty/None results
if the live stack is missing) so the app never crashes on import.
"""

import json
import os
import shutil
import sys
import threading

from config import Config, log

_LOCK = threading.RLock()
_OVERRIDE = {"iface": None}   # set at runtime from the UI capture page


def npcap_available():
    """Windows: check Npcap's wpcap.dll exists. Non-Windows: assume libpcap."""
    if os.name != "nt":
        return shutil.which("tcpdump") is not None or _have_scapy()
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    for cand in (
        os.path.join(windir, "System32", "Npcap", "wpcap.dll"),
        r"C:\Program Files\Npcap\wpcap.dll",
        r"C:\Windows\SysWOW64\Npcap\wpcap.dll",
    ):
        if os.path.isfile(cand):
            return True
    return False


def _have_scapy():
    try:
        import scapy  # noqa: F401
        return True
    except Exception:
        return False


def aircrack_available():
    """airodump-ng + aireplay-ng present? (Linux live mode)."""
    return bool(shutil.which("airodump-ng")) and bool(shutil.which("aireplay-ng"))


def list_interfaces():
    """Return [{name, description, is_wifi, is_wlan}] for this machine.

    Windows: uses Scapy's get_windows_if_list (needs Npcap).
    Linux:   reads /sys/class/net and tags wlan*/mon interfaces.
    """
    try:
        if os.name == "nt":
            return _win_interfaces()
        return _nix_interfaces()
    except Exception as exc:
        log(f"interfaces.list_interfaces() error: {exc}")
        return []


def _win_interfaces():
    try:
        from scapy.arch.windows import get_windows_if_list
        ifaces = get_windows_if_list()
    except Exception as exc:
        log(f"interfaces: scapy get_windows_if_list failed: {exc}")
        return []
    out = []
    wlan_hint = ("wireless", "wi-fi", "802.11", "wlan", "wifi")
    for i in ifaces:
        name = (i.get("name") or "").strip()
        desc = (i.get("description") or "").strip()
        if not name:
            continue
        low = (name + " " + desc).lower()
        is_wifi = any(h in low for h in wlan_hint)
        out.append({
            "name": name,
            "description": desc,
            "is_wifi": is_wifi,
        })
    # Prefer physical adapters over virtual/Wi-Fi Direct ones for ordering,
    # then drop the weird -0000 WFP/Npcap filter shims Scapy may echo.
    shim = lambda s: bool(s) and (
        "wfpmac" in s.lower() or "qos packet" in s.lower()
        or "-0000" in s.lower() or "lightweight" in s.lower())
    return [i for i in out if not shim(i["name"])]


def _nix_interfaces():
    out = []
    try:
        for entry in os.listdir("/sys/class/net"):
            name = entry.strip()
            if not name:
                continue
            is_wifi = name.startswith(("wlan", "wlx", "wlp", "wlo")) or name.endswith("mon")
            out.append({"name": name, "description": "", "is_wifi": is_wifi})
    except OSError:
        pass
    return out


def wifi_interfaces():
    return [i for i in list_interfaces() if i.get("is_wifi")]


def default_iface():
    """cheapest sane default: env override, else first Wi-Fi adapter."""
    env = (os.environ.get("AUDITOR_IFACE") or "").strip()
    if env:
        return env
    for i in wifi_interfaces() or list_interfaces():
        return i["name"]
    return "wlan0" if os.name != "nt" else "Wi-Fi"


def current_iface():
    with _LOCK:
        return _OVERRIDE["iface"] or default_iface()


def set_iface(name):
    with _LOCK:
        _OVERRIDE["iface"] = (name or "").strip() or None


def iface_ok(name=None):
    name = name or current_iface()
    names = {i["name"] for i in list_interfaces()}
    return bool(names) and name in names


# ---------------------------------------------------------------------------
# Windows: force a fresh radio scan
# ---------------------------------------------------------------------------
# `netsh wlan show networks` only reports Windows' *cached* scan results. While
# the adapter is connected and idle, that cache often contains just the current
# BSS - so the scanner appears to "find no APs". Calling the native WLAN API's
# WlanScan() triggers a real radio scan; a moment later netsh reflects it.
def force_windows_scan(timeout=6):
    """Trigger a fresh 802.11 scan. Returns True if a scan was requested."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    class WLAN_INTERFACE_INFO(ctypes.Structure):
        _fields_ = [("InterfaceGuid", GUID),
                    ("strInterfaceDescription", wintypes.WCHAR * 256),
                    ("isState", wintypes.DWORD)]

    class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
        _fields_ = [("dwNumberOfItems", wintypes.DWORD),
                    ("dwIndex", wintypes.DWORD),
                    ("InterfaceInfo", WLAN_INTERFACE_INFO * 1)]

    handle = wintypes.HANDLE()
    negotiated = wintypes.DWORD()
    plist = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
    try:
        wlanapi = ctypes.windll.wlanapi
        if wlanapi.WlanOpenHandle(2, None, ctypes.byref(negotiated),
                                  ctypes.byref(handle)) != 0:
            return False
        if wlanapi.WlanEnumInterfaces(handle, None, ctypes.byref(plist)) != 0:
            return False
        if plist.contents.dwNumberOfItems < 1:
            return False
        guid = plist.contents.InterfaceInfo[0].InterfaceGuid
        rc = wlanapi.WlanScan(handle, ctypes.byref(guid), None, None, None)
        log(f"interfaces: WlanScan requested (rc={rc})")
        return rc == 0
    except Exception as exc:
        log(f"interfaces: force_windows_scan failed: {exc}")
        return False
    finally:
        if plist:
            try:
                ctypes.windll.wlanapi.WlanFreeMemory(plist)
            except Exception:
                pass
        if handle:
            try:
                ctypes.windll.wlanapi.WlanCloseHandle(handle, None)
            except Exception:
                pass