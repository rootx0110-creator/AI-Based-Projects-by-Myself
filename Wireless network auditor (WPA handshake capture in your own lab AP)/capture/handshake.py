"""Handshake capture state machine.

Runs a single background thread per capture. It only mutates the ACTIVE
registry - all database persistence happens from the Flask request thread
(when status is polled and a terminal state is reached) as documented in
memory.md and state.md.
"""

import os
import random
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone

from config import Config, log
from capture import interfaces

STATE_IDLE = "IDLE"
STATE_LISTENING = "LISTENING"
STATE_DETECTED = "EAPOL_DETECTED"
STATE_COMPLETE = "HANDSHAKE_COMPLETE"

ACTIVE = {
    "running": False,
    "session_id": None,
    "ssid": None,
    "bssid": None,
    "channel": None,
    "state": STATE_IDLE,
    "eapol_messages": 0,
    "packets": 0,
    "deauth_sent": 0,
    "deauth_used": False,
    "started_at": None,
    "last_updated": None,
    "terminal": False,
    "seed": "",
    "error": None,
}
_LOCK = threading.RLock()


def status():
    with _LOCK:
        return dict(ACTIVE)


def _set(**kwargs):
    with _LOCK:
        ACTIVE.update(kwargs)
        ACTIVE["last_updated"] = datetime.now(timezone.utc).isoformat()


def is_running():
    with _LOCK:
        return bool(ACTIVE["running"])


def stop():
    """Gracefully request capture stop. Returns final dict."""
    with _LOCK:
        was = dict(ACTIVE)
        ACTIVE["running"] = False
        ACTIVE["state"] = STATE_IDLE
        ACTIVE["terminal"] = True
    return was


def reset():
    with _LOCK:
        for k in ("session_id", "ssid", "bssid", "channel", "seed"):
            ACTIVE[k] = None
        ACTIVE["state"] = STATE_IDLE
        ACTIVE["eapol_messages"] = 0
        ACTIVE["packets"] = 0
        ACTIVE["deauth_sent"] = 0
        ACTIVE["deauth_used"] = False
        ACTIVE["started_at"] = None
        ACTIVE["terminal"] = False
        ACTIVE["error"] = None


# ---- simulation thread -----------------------------------------------------

def _sim_worker(params):
    seed = _rand(params["ssid"] + "|" + params["bssid"])
    rng = random.Random(seed)
    _set(state=STATE_LISTENING)
    listening_for = _rand_range(2.0, 3.5, seed)
    t0 = time.time()
    while is_running() and time.time() - t0 < listening_for:
        tick = rng.uniform(0.25, 0.6)
        time.sleep(tick)
        if is_running() and ACTIVE["state"] == STATE_LISTENING:
            _set(packets=ACTIVE["packets"] + rng.randint(1, 3))
    if not is_running():
        return

    _set(state=STATE_DETECTED, eapol_messages=1)
    # Without deauth, client must roam/reassociate naturally.
    delay = 1.2 if params.get("deauth") else _rand_range(4.0, 6.0, seed + 1)
    t0 = time.time()
    while is_running() and time.time() - t0 < delay:
        time.sleep(rng.uniform(0.3, 0.8))
        if is_running():
            _set(packets=ACTIVE["packets"] + rng.randint(0, 2))
            if params.get("deauth"):
                extra = min(ACTIVE["eapol_messages"] + rng.randint(1, 3), 4)
                _set(eapol_messages=extra)
                if ACTIVE["eapol_messages"] >= 4:
                    break
    if is_running():
        _set(eapol_messages=max(ACTIVE["eapol_messages"], (
            4 if params.get("deauth") else 4)))
        time.sleep(0.6)
        _set(state=STATE_COMPLETE, eapol_messages=4, terminal=True, running=False)


def _rand(text):
    import hashlib
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2 ** 32)


def _rand_range(lo, hi, seed):
    rng = random.Random(seed)
    return lo + (rng.random() * (hi - lo))


# ---- live-mode helpers ------------------------------------------------------

def _live_pcap_name(ssid, bssid):
    import hashlib
    tag = hashlib.sha256(bssid.encode()).hexdigest()[:6]
    safe = "".join(c if c.isalnum() else "_" for c in ssid)
    return f"{safe}-{tag}.cap"


def _live_worker(params):
    """Real capture: prefer the Scapy EAPOL sniffer when available, otherwise
    fall back to airodump-ng (both write to captures/)."""
    if interfaces.npcap_available():
        try:
            return _scapy_worker(params)
        except Exception as exc:
            log(f"scapy worker failed ({exc}); trying airodump-ng")
    if shutil.which("airodump-ng"):
        return _airodump_worker(params)
    _set(state=STATE_IDLE, terminal=True, running=False,
         error="Live capture unavailable: need Npcap/libpcap (or airodump-ng).")


def _scapy_worker(params):
    """Passively sniff the selected interface for EAPOL (0x888E) frames.

    Works on:
      - Windows with Npcap in managed mode while connected to the target AP
        (captures the 4-way handshake that runs when a device joins/rejoins).
      - Any libpcap/platform with monitor mode for true passive capture.

    The capture is tailed like the simulation: one background thread advances
    the ACTIVE registry; the Flames request thread persists when terminal.
    """
    if not interfaces.npcap_available():
        _set(state=STATE_IDLE, terminal=True, running=False,
             error="Npcap/libpcap is required for live capture and was not found.")
        return
    try:
        import warnings
        warnings.filterwarnings("ignore")
        from scapy.all import sniff, wrpcap
        from scapy.layers.eap import EAPOL
        from scapy.layers.dot11 import Dot11
    except Exception as exc:
        _set(state=STATE_IDLE, terminal=True, running=False,
             error=f"Scapy import failed: {exc}")
        return

    iface = interfaces.current_iface()
    if not interfaces.iface_ok(iface):
        _set(state=STATE_IDLE, terminal=True, running=False,
             error=f"Interface '{iface}' not found. Pick one from the Scanner page.")
        return
    if params.get("channel"):
        _try_set_channel(iface, params["channel"])

    ssid = params.get("ssid") or "unknown"
    prefix = os.path.join(Config.CAPTURE_DIR, _live_pcap_name(ssid, params.get("bssid") or "unknown").replace(".cap", ""))
    pcap = prefix + "-01.cap"
    if os.path.exists(pcap):
        try:
            os.remove(pcap)
        except OSError:
            pass
    pkts = []
    seen_eapol = set()
    packet_total = 0

    def _on(pkt):
        nonlocal packet_total, seen_eapol
        if not is_running():
            return
        packet_total += 1
        pkts.append(pkt)
        is_eapol = (EAPOL in pkt) or (hasattr(pkt, "type") and pkt.type == 0x888e) or (
            Dot11 in pkt and hasattr(pkt, "subtype") and pkt.subtype == 0)
        if is_eapol:
            key = _eapol_key(pkt)
            seen_eapol.add(key)
            _set(eapol_messages=min(len(seen_eapol), 4))
            if ACTIVE["state"] == STATE_LISTENING:
                _set(state=STATE_DETECTED, eapol_messages=1)
            if len(seen_eapol) >= 4:
                _set(state=STATE_COMPLETE, eapol_messages=4, terminal=True, running=False)
        _set(packets=packet_total)

    _set(state=STATE_LISTENING)
    t0 = time.time()
    scan_wall = int(params.get("timeout") or 120)
    try:
        while is_running() and time.time() - t0 < scan_wall:
            sniff(iface=iface, prn=_on, store=False, timeout=1.0)
    except Exception as exc:
        _set(state=STATE_IDLE, terminal=True, running=False,
             error=f"Capture failed on '{iface}': {exc}")
        return

    # persist raw frames
    _set(packets=packet_total, eapol_messages=min(len(seen_eapol), 4))
    if pkts:
        try:
            wrpcap(pcap, pkts)
        except Exception:
            pass
    if is_running():
        _set(state=(STATE_COMPLETE if len(seen_eapol) >= 4
                    else (STATE_DETECTED if seen_eapol else STATE_LISTENING)),
             terminal=bool(seen_eapol) or len(seen_eapol) >= 4,
             running=False)


def _eapol_key(pkt):
    """Distinguish EAPOL frames so 4 messages != 4 copies of one frame.
    Uses a per-message number extracted from the EAPOL-Key descriptor when
    available; otherwise falls back to (src, dst, type) coarse identity."""
    try:
        raw = bytes(pkt.payload)
        if len(raw) > 5 and raw[0] == 3:  # 802.1X authentication
            # EAPOL-Key descriptor fields: version(1) type(1) length(2) then key descriptor
            if len(raw) > 7:
                return (pkt.src, pkt.dst, raw[2] & 0xFF, raw[3] & 0xFF)
        if len(raw) >= 4:
            return (pkt.src, pkt.dst, raw[0], raw[1])
    except Exception:
        pass
    return (getattr(pkt, "src", ""), getattr(pkt, "dst", ""),
            getattr(pkt, "type", 0))


def _try_set_channel(iface, channel):
    try:
        if os.name != "nt":
            subprocess.Popen(["iwconfig", iface, "channel", str(channel)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _airodump_worker(params):
    if not shutil.which("airodump-ng"):
        _set(state=STATE_IDLE, terminal=True)
        return
    prefix = os.path.join(Config.CAPTURE_DIR, _live_pcap_name(params["ssid"], params["bssid"]).replace(".cap", ""))
    cmd = ["airodump-ng", "-c", str(params["channel"]), "--bssid",
           params["bssid"], "--write", prefix, "--write-format", "cap",
           interfaces.current_iface()]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    _set(state=STATE_LISTENING)
    pcap = prefix + "-01.cap"
    last_msgs = 0
    while is_running() and not ACTIVE.get("terminal"):
        time.sleep(1.0)
        pkt = _count_packets(pcap)
        eapol = _count_eapol(pcap)
        _set(packets=pkt, eapol_messages=eapol)
        if eapol and ACTIVE["state"] == STATE_LISTENING:
            _set(state=STATE_DETECTED)
        if eapol >= 4:
            _set(state=STATE_COMPLETE, eapol_messages=4, terminal=True, running=False)
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        pass


def _count_packets(path):
    if not os.path.exists(path):
        return 0
    size = os.path.getsize(path)
    return int(size / 210)


def _count_eapol(path):
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        return data.count(b"\x88\x8e")
    except Exception:
        return 0


def start_capture(ssid, bssid, channel, seed="", deauth=False):
    """Begin a capture. Returns the ACTIVE status dict immediately."""
    with _LOCK:
        if ACTIVE["running"]:
            return dict(ACTIVE)
        ACTIVE.update({
            "running": True,
            "session_id": None,
            "ssid": ssid,
            "bssid": bssid,
            "channel": channel,
            "seed": seed or "",
            "state": STATE_LISTENING,
            "eapol_messages": 0,
            "packets": 0,
            "deauth_sent": 0,
            "deauth_used": deauth,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": None,
            "terminal": False,
            "error": None,
        })
    worker = _sim_worker if Config.ENGINE != "live" else _live_worker
    threading.Thread(target=worker, args=({"ssid": ssid, "bssid": bssid,
                                           "channel": channel,
                                           "deauth": deauth},),
                     daemon=True).start()
    return dict(ACTIVE)