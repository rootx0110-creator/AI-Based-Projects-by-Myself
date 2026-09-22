"""
report.py -- analyst HTML report generator.

Produces a self-contained dark-themed report (no external assets, no JS
dependencies) documenting the beacon campaign: metadata, event timeline,
decrypted message table, decryption exercise stats, and the MITRE-style
detection notes. The UI offers this as a download; blue-teamers attach it
to the exercise write-up.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import html as html_mod
import os
import time


def esc(s) -> str:
    return html_mod.escape(str(s))


_CSS = """
:root {
  --bg:#0b0f14; --panel:#121821; --panel2:#0e141c; --line:#1d2633;
  --text:#d7e1ee; --muted:#7d8ca1; --accent:#22d3ee; --accent2:#a78bfa;
  --good:#34d399; --warn:#fbbf24; --bad:#f87171;
  --mono:'Consolas','JetBrains Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
  font:14px/1.6 'Segoe UI',system-ui,sans-serif;padding:32px 20px}
.wrap{max-width:1100px;margin:0 auto}
header{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.logo{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;
  justify-content:center;font-size:22px;
  background:linear-gradient(135deg,#0e7490,#155e75)}
h1{font-size:22px;letter-spacing:.3px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 26px}
.chip{background:var(--panel);border:1px solid var(--line);color:var(--muted);
  padding:5px 12px;border-radius:999px;font-size:12px}
.chip b{color:var(--text);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:12px;margin-bottom:26px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px}
.card .k{color:var(--muted);font-size:11px;text-transform:uppercase;
  letter-spacing:.8px}
.card .v{font-size:24px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}
.card .v.accent{color:var(--accent)}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:20px 22px;margin-bottom:18px}
h2{font-size:15px;letter-spacing:.4px;margin-bottom:12px;display:flex;
  align-items:center;gap:8px}
h2 .dot{width:8px;height:8px;border-radius:50%;background:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--muted);text-align:left;font-weight:600;font-size:11px;
  text-transform:uppercase;letter-spacing:.6px;padding:8px 10px;
  border-bottom:1px solid var(--line)}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.mono,span.mono{font-family:var(--mono);font-size:12px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;
  font-weight:600}
.pill.tls{background:rgba(34,211,238,.12);color:var(--accent)}
.pill.c2{background:rgba(167,139,250,.12);color:var(--accent2)}
.pill.alert{background:rgba(248,113,113,.12);color:var(--bad)}
.pill.info{background:rgba(125,140,161,.12);color:var(--muted)}
.dir-b{color:var(--good)} .dir-c{color:var(--warn)}
pre.dump{background:var(--panel2);border:1px solid var(--line);border-radius:10px;
  padding:14px;font-family:var(--mono);font-size:11.5px;line-height:1.5;
  overflow-x:auto;color:#9fb3c8;white-space:pre}
.note{background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.25);
  border-radius:10px;padding:12px 14px;font-size:13px;color:#fde68a}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:26px}
@media print{ body{background:#fff;color:#111} }
"""


def _event_row(e) -> str:
    kind_cls = e.kind if e.kind in ("tls", "c2", "alert", "info") else "info"
    dir_cls = "dir-b" if e.direction.startswith("->") else "dir-c"
    return (
        "<tr><td class='mono'>{ts}</td>"
        "<td><span class='pill {cls}'>{kind}</span></td>"
        "<td class='{dcls}'>{direction}</td>"
        "<td class='mono'>{beacon}</td>"
        "<td>{summary}</td></tr>"
    ).format(ts=esc(e.hhmmss), cls=kind_cls, kind=esc(e.kind.upper()),
             dcls=dir_cls, direction=esc(e.direction),
             beacon=esc(e.beacon), summary=esc(e.summary))


def _decrypt_row(i, r) -> str:
    return (
        "<tr><td class='mono'>{i}</td>"
        "<td><span class='pill c2'>{name}</span></td>"
        "<td class='mono'>{nonce}</td>"
        "<td class='mono'>{size} B</td>"
        "<td class='mono'>{pt}</td></tr>"
    ).format(i=i, name=esc(r["msg_name"]), nonce=esc(r["nonce"]),
             size=len(r["plaintext"]),
             pt=esc(r["plaintext"].decode("utf-8", "replace")[:90]))


def build_report(campaign: str, events, frames, nonce: bytes,
                 passphrase: str) -> str:
    """Render the full HTML report as a string."""
    from . import decrypt as decrypt_mod

    results, failures = decrypt_mod.decrypt_capture(frames, passphrase, nonce)
    stats = decrypt_mod.analysis_summary(results)

    mix_rows = "".join(
        "<tr><td>{k}</td><td class='mono'>{v}</td></tr>".format(k=esc(k), v=v)
        for k, v in sorted(stats["message_mix"].items())) or \
        "<tr><td colspan=2 class='mono'>no frames decrypted</td></tr>"

    dec_rows = "".join(_decrypt_row(i, r) for i, r in enumerate(results)) or \
        "<tr><td colspan=5 class='mono'>no frames decrypted</td></tr>"

    ev_rows = "".join(_event_row(e) for e in events[:400]) or \
        "<tr><td colspan=5 class='mono'>no events captured</td></tr>"

    generated = time.strftime("%Y-%m-%d %H:%M:%S")

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GLM Beacon Lab Report - {campaign}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="logo">&#128737;</div>
  <div>
    <h1>GLM Beacon Lab &mdash; C2 Traffic Analysis Report</h1>
    <div class="sub">TLS-wrapped beacon simulation &middot; traffic decryption exercise for blue-team study</div>
  </div>
</header>

<div class="chips">
  <span class="chip">Campaign <b>{campaign}</b></span>
  <span class="chip">Generated <b>{generated}</b></span>
  <span class="chip">Events <b>{n_events}</b></span>
  <span class="chip">Frames decrypted <b>{n_ok}</b> / {n_frames}</span>
</div>

<div class="grid">
  <div class="card"><div class="k">Beacon check-ins</div><div class="v accent">{n_ping}</div></div>
  <div class="card"><div class="k">Frames captured</div><div class="v">{n_frames}</div></div>
  <div class="card"><div class="k">Decrypted OK</div><div class="v" style="color:var(--good)">{n_ok}</div></div>
  <div class="card"><div class="k">Failed auth</div><div class="v" style="color:var(--bad)">{n_fail}</div></div>
</div>

<section>
  <h2><span class="dot"></span>Campaign metadata</h2>
  <table>
    <tr><th style="width:220px">Field</th><th>Value</th></tr>
    <tr><td>Campaign passphrase</td><td class="mono">{passphrase}</td></tr>
    <tr><td>Listener endpoint</td><td class="mono">tls://127.0.0.1:8443 (lab.local)</td></tr>
    <tr><td>Transport</td><td>TLS 1.3 tunnel &rarr; GLM1 framed packets (CBCS&trade; CTR + truncated HMAC-SHA256)</td></tr>
    <tr><td>Key derivation</td><td class="mono">HKDF-SHA256(passphrase, "glm-lab-salt", "glm-beacon-lab/v1/session-keys", 48)</td></tr>
  </table>
</section>

<section>
  <h2><span class="dot"></span>Event timeline</h2>
  <table>
    <tr><th>Time</th><th>Kind</th><th>Direction</th><th>Beacon</th><th>Summary</th></tr>
    {ev_rows}
  </table>
</section>

<section>
  <h2><span class="dot"></span>Decrypted messages</h2>
  <table>
    <tr><th>#</th><th>Type</th><th>Nonce</th><th>Size</th><th>Plaintext (first 90 B)</th></tr>
    {dec_rows}
  </table>
</section>

<section>
  <h2><span class="dot"></span>Message mix</h2>
  <table>
    <tr><th>Message type</th><th>Count</th></tr>
    {mix_rows}
  </table>
</section>

<section>
  <h2><span class="dot"></span>Blue-team detection notes</h2>
  <div class="note">
    <b>Detection ideas demonstrated by this campaign:</b>
    <ul style="margin:8px 0 0 18px">
      <li><b>Periodic beacons with jitter</b> &mdash; regular check-ins (8s &plusmn; 25%) are highly visible in flow-size/time-series analytics.</li>
      <li><b>Self-signed certificate</b> &mdash; CN=lab.local, 10-year validity, CA:TRUE on a leaf: all instant flags in TLS inventory tools (JA3/JA4 fingerprinting catches the client side too).</li>
      <li><b>Hard-coded key material</b> &mdash; the campaign passphrase derives every session key; one dictionary hit (see decrypt.py brute_force_hint) burns the whole channel.</li>
      <li><b>Truncated 4-byte HMAC</b> &mdash; weak integrity tag; any analyst holding the key detects tampering instantly.</li>
      <li><b>Nonce reuse</b> &mdash; every frame in a session reuses one nonce, visible as identical nonce fields after the first HMAC break.</li>
    </ul>
  </div>
</section>

<section>
  <h2><span class="dot"></span>Sample frame hexdump</h2>
  <pre class="dump">{hexdump}</pre>
</section>

<footer>
  GLM Beacon Lab &mdash; educational simulation. Generated by GLM Beacon Lab (blue-team study build).<br>
  All traffic in this report was produced locally by a simulated implant. Not for use on systems you do not own.
</footer>

</div>
</body>
</html>""".format(
        css=_CSS,
        campaign=esc(campaign),
        generated=generated,
        n_events=len(events),
        n_frames=len(frames),
        n_ok=len(results),
        n_fail=len(failures),
        n_ping=sum(1 for e in events if "PING" in e.summary),
        passphrase=esc(passphrase),
        ev_rows=ev_rows,
        dec_rows=dec_rows,
        mix_rows=mix_rows,
        hexdump=esc(_first_frame_dump(results)),
    )


def _first_frame_dump(results) -> str:
    if not results:
        return "(no decrypted frames)"
    r = results[0]
    from .crypto_tools import hexdump
    return ("frame #{idx}  {name}  nonce={nonce}  mac={mac}\n\n"
            "-- ciphertext --\n{ct}\n\n"
            "-- recovered plaintext --\n{pt}").format(
        idx=r.get("index", 0), name=r["msg_name"], nonce=r["nonce"], mac=r["mac"],
        ct=hexdump(r["ciphertext"][:64]),
        pt=r["plaintext"].decode("utf-8", "replace"))


def write_report(html: str, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
