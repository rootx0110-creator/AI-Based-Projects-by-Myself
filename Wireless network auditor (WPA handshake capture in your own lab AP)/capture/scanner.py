"""Network discovery.

Simulation engine: deterministic fake lab data for offline evaluation.
Live engine:     Windows -> real scan via `netsh wlan show networks mode=bssid`
                 (no monitor mode required, works with the normal Wi-Fi adapter).
                 Linux   -> if airodump-ng exists use it; otherwise fall back to
                 a passive Scapy beacon/probe sniff on the selected interface.
"""

import hashlib
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone

from config import Config
from capture import interfaces

SCAN_CACHE = {}


def _rand_seed(text):
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def _stable(n, lo, hi, seed):
    return lo + (seed % (hi - lo + 1))


def _bssid_for(name, n=__import__("random")):
    seed = _rand_seed(name)
    parts = []
    for i in range(6):
        parts.append((seed >> (8 * i)) & 0xFF)
    return ":".join(f"{p:02X}" for p in parts)


def _sim_ap(ssid, channel, sig, enc, clients, seed_extra=0):
    seed = _rand_seed(ssid) + seed_extra
    return {
        "ssid": ssid,
        "bssid": _bssid_for(ssid),
        "channel": channel,
        "signal_dbm": sig,
        "encryption": enc,
        "clients": clients,
        "seed": str(seed),
    }


def _simulator():
    """Deterministic set of lab access points (same every scan)."""
    aps = [
        _sim_ap("LAB-AP-2.4G", 6, -47, "WPA2-PSK", 4, 1),
        _sim_ap("LAB-AP-5G", 149, -52, "WPA3-Transition", 3, 2),
        _sim_ap("Lab_AccessPoint", 1, -61, "WPA2-PSK", 2, 3),
        _sim_ap("lab-iot-hub", 11, -58, "WPA2-PSK", 5, 4),
        _sim_ap("LabGuest-Net", 6, -66, "Open", 1, 5),
        _sim_ap("LAB-AP-SECURE", 36, -49, "WPA3-SAE", 2, 6),
        _sim_ap("lab-legacy-wep", 1, -73, "WEP", 1, 7),
        _sim_ap("LabTesting-Box", 100, -55, "WPA2-PSK", 3, 8),
        _sim_ap("lab-testbench", 7, -44, "WPA2/WPA3-Transition", 0, 9),
    ]
    for ap in aps:
        if _stable(1, 1, 100, _rand_seed(ap["ssid"] + "handshake")) > 68:
            ap["has_handshake"] = True
    return aps


def _live_scan():
    """Real scan, best backend for the current platform."""
    if os.name == "nt":
        return _windows_netsh_scan()
    if shutil.which("airodump-ng") and interfaces.iface_ok():
        return _live_scan_airodump()
    if interfaces.npcap_available():
        return _live_scan_scapy()
    raise RuntimeError(
        "No live scan backend available. On Windows make sure Npcap is "
        "installed; on Linux install aircrack-ng (airodump-ng) or libpcap.")


def _run_netsh():
    """Run netsh and return stdout decoded as text (netsh emits UTF-8)."""
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("netsh not found - run the app on a machine with a Wi-Fi adapter.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("netsh timed out listing networks. Is Wi-Fi enabled?")
    raw = out.stdout or b""
    for enc in ("utf-8", "cp1252", "cp850"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _windows_netsh_scan(force=True):
    """Parse `netsh wlan show networks mode=bssid` - real, no admin needed.

    Windows only scans the radio periodically, so netsh usually shows just the
    connected BSS. We first ask the WLAN API for a fresh scan, then read netsh.
    """
    if force:
        interfaces.force_windows_scan()
        time.sleep(3)
    text = _run_netsh()
    records = _parse_netsh(text)
    if not records and force:
        interfaces.force_windows_scan()
        time.sleep(4)
        text = _run_netsh()
        records = _parse_netsh(text)
    if not records:
        if "There are 0 networks currently visible" in text:
            raise RuntimeError(
                "Windows reports 0 visible networks. Make sure Wi-Fi is on, "
                "you are near access points, and try again.")
        raise RuntimeError("netsh returned no parseable access points.")
    return records


def _parse_netsh(text):
    """netsh net output -> AP records.

    Format (per SSID block):
      SSID 1 : MyLab
          Network type ...
          Authentication ... WPA2-Personal
          Encryption ... CCMP
          BSSID 1 : aa:bb:...
               Signal      : 92%
               Radio type  : 802.11ac
               Channel     : 1
    """
    records = []
    lines = text.splitlines()

    found = []

    # Re-derive blocks from SSID-marked lines only (avoid split-on-BSSID bug).
    blocks = []
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*SSID\s+\d+\s*:", line):
            if start is not None:
                blocks.append(lines[start:i])
            start = i
    if start is not None:
        blocks.append(lines[start:])

    for blk in blocks:
        ssid = "<hidden>"
        m = re.match(r"^\s*SSID\s+\d+\s*:\s*(.*)$", blk[0]) if blk else None
        if m:
            ssid = m.group(1).strip() or "<hidden>"
        body = "\n".join(blk[1:]) if len(blk) > 1 else ""
        auth = ""
        m = re.search(r"Authentication[ \t]*:[ \t]*(.+)", body)
        if m:
            auth = m.group(1).strip()
        enc_raw = ""
        m = re.search(r"Encryption[ \t]*:[ \t]*(.+)", body)
        if m:
            enc_raw = m.group(1).strip()
        bssid = ""
        m = re.search(r"BSSID[ \t]+\d+[ \t]*:[ \t]*([0-9A-Fa-f:]{17})", body)
        if m:
            bssid = m.group(1).upper()
        if not bssid:
            continue
        channel = 0
        m = re.search(r"Channel[ \t]*:[ \t]*(\d+)", body)
        if m:
            channel = int(m.group(1))
        signal_pct = 0
        m = re.search(r"Signal[ \t]*:[ \t]*(\d+)%", body)
        if m:
            signal_pct = int(m.group(1))
        encryption = auth or "Open"
        enc_clean = enc_raw.strip().upper()
        if enc_clean and enc_clean not in ("CCMP", "TKIP", "AES", "GCMP"):
            encryption = f"{auth}-{enc_raw.strip()}" if auth else enc_raw.strip()
        records.append({
            "ssid": ssid, "bssid": bssid, "channel": channel,
            "signal_dbm": _pct_to_dbm(signal_pct) if signal_pct else -100,
            "encryption": encryption, "clients": 0, "seed": "",
        })
    return records


def _pct_to_dbm(pct):
    """Rough Windows signal-percent -> dBm (pct 100 ~ -40 dBm)."""
    return int(round(-40 - (100 - max(0, min(100, pct))) * 0.55))


def _live_scan_airodump():
    """Run airodump-ng for a few seconds and parse CSV into records."""
    if not shutil.which("airodump-ng"):
        raise RuntimeError("airodump-ng not found in PATH (install aircrack-ng)")
    tmp_dir = os.path.join(Config.CAPTURE_DIR, ".airodump_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    prefix = os.path.join(tmp_dir, "scan")
    proc = subprocess.Popen(
        ["airodump-ng", "--band", "abg", "--write", prefix,
         "--write-format", "csv", "--output-format", "csv",
         "-a", interfaces.current_iface()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(8)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    csv_path = prefix + "-01.csv"
    records = _parse_airodump_csv(csv_path) if os.path.exists(csv_path) else []
    return records


def _live_scan_scapy():
    """Passive beacon/probe sniff for a few seconds (libpcap/Npcap backends).

    Note: on Windows a normal Wi-Fi adapter in managed mode usually only sees
    its own BSS - in that case this returns an empty list and the app falls
    back to urging the user to use netsh (the default Windows backend).
    """
    if not interfaces.npcap_available():
        raise RuntimeError("Npcap/libpcap not available for passive sniffing")
    try:
        from scapy.all import sniff, RadioTap, Dot11
        from scapy.layers.dot11 import Dot11Beacon, Dot11ProbeResp
    except Exception as exc:
        raise RuntimeError(f"Scapy unavailable: {exc}")
    found = {}
    iface = interfaces.current_iface()

    def _on(pkt):
        try:
            if not (RadioTap in pkt or Dot11 in pkt):
                return
            sub = pkt.getlayer(Dot11)
            if sub is None or sub.type != 0 or sub.subtype not in (8, 5):
                return
            bssid = sub.addr2 or sub.addr3
            if not bssid:
                return
            ssid, chan, sig = "<hidden>", 0, -100
            if Dot11Beacon in pkt:
                ssid = pkt.getlayer(Dot11Beacon).info.decode(errors="replace") or "<hidden>"
            elif Dot11ProbeResp in pkt:
                ssid = pkt.getlayer(Dot11ProbeResp).info.decode(errors="replace") or "<hidden>"
            rssi = getattr(pkt.getlayer(RadioTap), "dBm_AntSignal", None)
            if rssi is not None:
                sig = int(rssi)
            if bssid not in found:
                found[bssid] = {"bssid": bssid, "ssid": ssid, "channel": 0,
                                "signal_dbm": sig, "encryption": "WPA2-PSK",
                                "clients": 0, "seed": ""}
        except Exception:
            pass

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sniff(iface=iface, prn=_on, store=False, timeout=6)
    except Exception as exc:
        raise RuntimeError(f"Sniff failed on '{iface}': {exc}")
    return list(found.values())


def _parse_airodump_csv(path):
    records = []
    with open(path, "r", errors="replace") as fh:
        content = fh.read()
    sections = content.split("\n\n")
    ap_section = sections[0] if sections else ""
    lines = [ln for ln in ap_section.splitlines() if ln.strip()]
    header_idx = None
    for i, ln in enumerate(lines):
        if "BSSID" in ln and "CH" in ln and "ESSID" in ln:
            header_idx = i
            break
    if header_idx is None:
        return records
    headers = [h.strip() for h in lines[header_idx].split(",")]
    for ln in lines[header_idx + 1:]:
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        cells = [c.strip() for c in ln.split(",")]
        if len(cells) < max(len(headers), 6):
            continue
        def pick(name):
            try:
                return cells[headers.index(name)]
            except ValueError:
                return ""
        bssid = pick("BSSID")
        if not bssid or re.match(r"^[0-9A-Fa-f:]{17}$", bssid) is None:
            continue
        ssid = pick("ESSID") or "<hidden>"
        try:
            ch = int(pick("CH"))
        except ValueError:
            ch = 0
        try:
            sig = int(pick("PWR")) if pick("PWR") else -100
        except ValueError:
            sig = -100
        enc = pick("ENC")
        cipher = pick("CIPHER")
        auth = pick("AUTH")
        encryption = f"{enc}-{cipher}" if cipher and cipher != "" else enc
        try:
            clients = int(pick("# Data") or 0) + 1
        except ValueError:
            clients = 0
        records.append({
            "ssid": ssid, "bssid": bssid, "channel": ch,
            "signal_dbm": sig, "encryption": encryption,
            "clients": clients, "seed": "",
        })
    return records


def scan():
    """Returns list of network dicts and caches it."""
    if Config.ENGINE == "live":
        nets = _live_scan()
    else:
        nets = _simulator()
    SCAN_CACHE["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    SCAN_CACHE["networks"] = nets
    return nets


def last_scan():
    return SCAN_CACHE.copy()