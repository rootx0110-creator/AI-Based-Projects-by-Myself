"""Self-contained HTML report builder (report download capability).

Produces a single HTML file with embedded CSS and inline base64 QR images -
no external assets, works fully offline, safe to e-mail / archive.
"""

import html
import os
from datetime import datetime

from wgbuilder import __version__, __title__
from wgbuilder.core import configs, qr
from wgbuilder.core.store import derive_pub_or_none

_CSS = """
:root{--bg:#0e141b;--panel:#161f2a;--panel2:#1b2634;--line:#263443;--txt:#e8eef6;
--muted:#8fa3b8;--acc:#2dd4bf;--acc2:#38bdf8;--warn:#fbbf24;--good:#34d399;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.55 "Segoe UI",Arial,sans-serif}
header{background:linear-gradient(135deg,#101c27,#0d2b2b);border-bottom:1px solid var(--line);
padding:28px 40px}
h1{margin:0;font-size:24px;letter-spacing:.2px}
.sub{color:var(--muted);margin-top:4px;font-size:13px}
.wrap{max-width:1080px;margin:0 auto;padding:28px 40px 64px}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;
margin:22px 0;padding:20px 24px;overflow:hidden}
h2{margin:0 0 14px;font-size:16px;color:var(--acc2)}
h3{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin:18px 0 8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}
td:first-child{color:var(--muted);white-space:nowrap}
pre{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:14px;
font:12px/1.5 Consolas,"Courier New",monospace;overflow-x:auto;white-space:pre}
.kv{display:grid;grid-template-columns:220px 1fr;gap:2px 16px}
.kv b{color:var(--muted);font-weight:600}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.b-ok{background:rgba(52,211,153,.15);color:var(--good)}
.b-warn{background:rgba(251,191,36,.15);color:var(--warn)}
.b-mut{background:rgba(143,163,184,.15);color:var(--muted)}
.peer{display:flex;gap:18px;align-items:flex-start;border-top:1px solid var(--line);
padding:16px 0}
.peer:first-of-type{border-top:none}
.peer img{width:132px;height:132px;border-radius:8px;border:1px solid var(--line);flex:none}
.qrblk{text-align:center;color:var(--muted);font-size:11px}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:34px}
.mono{font-family:Consolas,monospace;word-break:break-all}
.tag{color:var(--muted);font-size:12px}
"""


def _h(text: str) -> str:
    return html.escape(str(text))


def _badge(ok: bool, yes: str, no: str) -> str:
    cls = "b-ok" if ok else "b-warn"
    return f'<span class="badge {cls}">{_h(yes if ok else no)}</span>'


def build_report(state: dict, events: list[dict], title_suffix: str = "") -> str:
    server = state["server"]
    peers = state["peers"]
    exports = state.get("exports") or []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def s_key(priv: str) -> str:
        return derive_pub_or_none(priv or "")

    has_keys = bool(server.get("private_key")) and bool(server.get("public_key"))
    ready = bool(server.get("endpoint_host")) and has_keys

    out = ["<!DOCTYPE html>", "<html lang='en'><head><meta charset='utf-8'>",
           f"<title>{_h(__title__)} - Report</title>",
           f"<style>{_CSS}</style></head><body>"]
    out.append("<header><h1>" + _h(__title__) +
               "</h1><div class='sub'>WireGuard tunnel builder &middot; run report" +
               (f" &middot; {_h(title_suffix)}" if title_suffix else "") +
               f" &middot; generated {_h(now)}</div></header>")
    out.append("<div class='wrap'>")

    # Summary
    out.append("<section><h2>Summary</h2><div class='kv'>")
    out.append("<b>Tunnel ready</b><span>" + _badge(ready, "Yes - deployable", "Incomplete") + "</span>")
    out.append("<b>Server keypair</b><span>" + _badge(has_keys, "Generated", "Missing") + "</span>")
    out.append(f"<b>Interface</b><span class='mono'>{_h(server.get('interface_name') or 'wg0')}</span>")
    out.append(f"<b>Listen port (UDP)</b><span class='mono'>{int(server.get('listen_port') or 51820)}</span>")
    out.append(f"<b>Subnet</b><span class='mono'>{_h(server.get('subnet') or '-')}</span>")
    out.append(f"<b>Server address</b><span class='mono'>{_h(server.get('address') or '-')}</span>")
    out.append(f"<b>Endpoint host</b><span class='mono'>{_h(server.get('endpoint_host') or '(unset)')}</span>")
    out.append(f"<b>Peers configured</b><span>{len(peers)} device(s)</span>")
    out.append(f"<b>Exports</b><span>{len(exports)}</span>")
    out.append("</div></section>")

    # Server detail
    out.append("<section><h2>Server</h2><div class='kv'>")
    out.append("<b>Private key</b><span class='mono'>" + _h(server.get("private_key") or "&ndash;") + "</span>")
    client_pub = s_key(server.get("private_key"))
    out.append("<b>Public key</b><span class='mono'>" +
               _h(client_pub or server.get("public_key") or "&ndash;") + "</span>")
    out.append("<b>DNS</b><span class='mono'>" + _h(server.get("dns") or "1.1.1.1") + "</span>")
    out.append("<b>MTU</b><span class='mono'>" + _h(server.get("mtu") or "1420") + "</span>")
    out.append("<b>PostUp / PostDown</b><span class='mono'>" +
               _h(server.get("post_up") or "&ndash;") + " &nbsp;/&nbsp; " +
               _h(server.get("post_down") or "&ndash;") + "</span>")
    out.append("</div></section>")

    # Peer inventory
    out.append("<section><h2>Peer inventory</h2>")
    if peers:
        out.append("<table><tr><th>Device</th><th>Address</th><th>Allowed IPs</th>"
                   "<th>Keepalive</th><th>Public key</th></tr>")
        for p in sorted(peers, key=lambda x: x.get("name", "")):
            out.append(f"<tr><td><b>{_h(p.get('name'))}</b></td>"
                       f"<td class='mono'>{_h(p.get('ip') or '-')}</td>"
                       f"<td class='mono'>{_h(p.get('allowed_ips') or (str(p.get('ip')) + '/32') if p.get('ip') else '-')}</td>"
                       f"<td>{int(p.get('keepalive') or 0) if p.get('keepalive') else '-'}</td>"
                       f"<td class='mono'>{_h(p.get('public_key') or '-')}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p class='tag'>No peers configured yet.</p>")
    out.append("</section>")

    # Server config block
    out.append("<section><h2>Server configuration - wg0.conf</h2>")
    try:
        srv = dict(server)
        server_cfg = configs.build_server_config(srv, peers)
        out.append("<pre>" + _h(server_cfg) + "</pre>")
    except Exception as exc:  # noqa: BLE001
        out.append(f"<p class='tag'>Missing details to render server config ({_h(exc)}).</p>")
    out.append("</section>")

    # Per-peer client configs + QR
    out.append("<section><h2>Client configurations &amp; QR codes</h2>")
    if peers:
        for p in sorted(peers, key=lambda x: x.get("name", "")):
            out.append("<h3>" + _h(p.get("name")) + "</h3>")
            try:
                client_cfg = configs.build_client_config(server, p, __title__)
                uri = qr.qr_data_uri(client_cfg)
            except Exception as exc:  # noqa: BLE001
                client_cfg = None
                uri = None
                err = str(exc)
            out.append("<div class='peer'>")
            if uri:
                out.append("<div>" + f"<img src='{uri}' alt='QR'>" +
                           "<div class='qrblk'>scan to import</div></div>")
            else:
                out.append(f"<div class='qrblk'><img alt='' width='132' height='132'>"
                           f"<br>{_h(err or 'unavailable')}</div>")
            if client_cfg:
                out.append("<div style='flex:1'><pre>" + _h(client_cfg) + "</pre></div>")
            out.append("</div>")
    else:
        out.append("<p class='tag'>Add peers in the Peers &amp; Devices tab, then regenerate this report.</p>")
    out.append("</section>")

    # Export history
    if exports:
        out.append("<section><h2>Export history</h2><table><tr><th>When</th><th>Folder</th><th>Peers</th></tr>")
        for e in exports[::-1]:
            out.append(f"<tr><td class='mono'>{_h(e.get('at'))}</td>"
                       f"<td class='mono'>{_h(e.get('folder'))}</td>"
                       f"<td>{int(e.get('peer_count') or 0)}</td></tr>")
        out.append("</table></section>")

    # Event log
    out.append("<section><h2>Activity log</h2>")
    if events:
        out.append("<table><tr><th>Time</th><th>Level</th><th>Event</th></tr>")
        for e in events[::-1][:40]:
            lvl = str(e.get("level") or "info")
            b = "b-ok" if lvl == "info" else ("b-warn" if lvl == "warn" else ("b-warn"))
            out.append(f"<tr><td class='mono'>{_h(e.get('at'))}</td>"
                       f"<td><span class='badge {b}'>{_h(lvl)}</span></td>"
                       f"<td>{_h(e.get('message'))}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p class='tag'>No activity recorded.</p>")
    out.append("</section>")

    out.append(f"<footer>{_h(__title__)} v{__version__} &middot; offline report &middot; "
               "treat exported configs as secrets</footer>")
    out.append("</div></body></html>")
    return "\n".join(out)


def default_filename() -> str:
    return "vpn-tunnel-builder-report.html"