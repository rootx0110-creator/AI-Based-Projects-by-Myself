"""Capture analysis: produce security score + findings + recommendations."""

ENCRYPTION_SCORE = {
    "WPA3-SAE": 40,
    "WPA3": 40,
    "WPA3-Transition": 32,
    "WPA2/WPA3-Transition": 32,
    "WPA2-PSK": 26,
    "WPA2": 26,
    "WPA": 18,
    "WEP": 6,
    "Open": 0,
}


def _substring_enc(enc):
    enc = (enc or "").upper()
    if "WPA3-SAE" in enc:
        return "WPA3-SAE"
    if "WPA3" in enc:
        return "WPA3-Transition" if "TRANS" in enc else "WPA3"
    if "WPA2/WPA3" in enc or "WPA2/WPA3" in enc:
        return "WPA2/WPA3-Transition"
    if "WPA2" in enc:
        return "WPA2-PSK"
    if "WPA" in enc:
        return "WPA"
    if "WEP" in enc:
        return "WEP"
    return "Open"


def analyze(session, network=None):
    """Takes a session dict (from db) and computes an audit verdict."""
    enc = _substring_enc(network.get("encryption") if network else session.get("encryption", ""))
    enc_pts = ENCRYPTION_SCORE.get(enc, 0)
    msgs = int(session.get("eapol_messages") or 0)

    if msgs >= 4:
        integrity = 40        # full 4-way handshake verifiable offline
        capture_note = "Full 4-way EAPOL handshake captured and verifiable."
    elif msgs == 3:
        integrity = 28
        capture_note = "Three of four EAPOL messages captured (partial - missing ACK)."
    elif msgs == 2:
        integrity = 16
        capture_note = "Two EAPOL messages captured (partial, no session key confirm)."
    elif msgs == 1:
        integrity = 8
        capture_note = "Single EAPOL frame observed (insufficient for cracking)."
    else:
        integrity = 0
        capture_note = "No EAPOL traffic captured."

    score = max(0, min(100, integrity + enc_pts))

    findings = []
    if "WPA3-SAE" in enc:
        findings.append(("POSITIVE", "WPA3-SAE active - resistant to offline",
                         "SAE (Dragonfly) prevents captured-handshake offline attacks."))
    elif "TRANSITION" in enc:
        findings.append(("WARNING", "Transition mode exposes WPA2 downgrade",
                         "Clients can negotiate WPA2, re-enabling captured-handshake cracking. "
                         "Prefer WPA3-only."))
    elif "WPA2" in enc or "WPA" in enc:
        findings.append(("HIGH", "Captured handshake enables offline cracking",
                         "A captured 4-way handshake can be brute-forced offline. "
                         "Passphrase strength is the only mitigation."))
    elif "WEP" in enc:
        findings.append(("CRITICAL", "WEP is effectively broken",
                         "WEP can be cracked passively in minutes. Migrate immediately."))
    elif "Open" in enc:
        findings.append(("CRITICAL", "Open network carries no authentication",
                         "All traffic is unencrypted; any gateway security is absent."))

    if msgs < 4:
        findings.append(("INFO", "Re-run capture with a deauth burst",
                         "A deauth forces the client to re-associate and emit a "
                         "fresh 4-way handshake, improving completeness."))

    recommendations = [
        "Require WPA3-SAE where every device supports it; keep WPA2/WPA3 "
        "transition only for legacy hardware.",
        "Enforce a 12+ character passphrase drawn from multiple character "
        "classes - it is the only defense against offline cracking.",
        "Disable WPS (often reintroduces an 8-digit PIN brute-force vector).",
        "Use per-network isolation for guests and IoT segments.",
        "Re-run periodic audits using this tool and keep each HTML report as evidence.",
    ]
    if "Open" in enc:
        recommendations.insert(0, "Implement WPA3+OOE (Opportunistic Wireless Encryption) or full 802.1X immediately; do not expose open SSIDs.")
    if "WEP" in enc:
        recommendations.insert(0, "Retire WEP infrastructure immediately.")

    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 \
        else "D" if score >= 40 else "F"

    return {
        "score": score,
        "grade": grade,
        "integrity": integrity,
        "encryption_pts": enc_pts,
        "capture_note": capture_note,
        "findings": findings,
        "recommendations": recommendations,
        "encryption": enc,
    }