"""HTML report generation for the honeypot."""
import json
from datetime import datetime


def _risk_badge(score):
    score = float(score or 0)
    if score >= 70:
        return f'<span class="risk risk-critical">CRITICAL ({score:.0f})</span>'
    if score >= 50:
        return f'<span class="risk risk-high">HIGH ({score:.0f})</span>'
    if score >= 25:
        return f'<span class="risk risk-medium">MEDIUM ({score:.0f})</span>'
    if score > 0:
        return f'<span class="risk risk-low">LOW ({score:.0f})</span>'
    return '<span class="risk risk-unknown">UNKNOWN</span>'


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_html_report(data, generated_at=None):
    generated_at = generated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    stats = data.get("stats", {})
    attackers = data.get("attackers", [])
    events = data.get("events", [])
    top_ips = data.get("top_ips", [])
    top_users = data.get("top_usernames", [])
    top_pass = data.get("top_passwords", [])
    geo = data.get("geo_stats", [])
    protocols = data.get("protocol_stats", [])
    timeline = data.get("timeline", [])

    attacker_rows = "".join(
        f"""<tr>
            <td>{_escape(a['fingerprint_hash'][:16])}</td>
            <td><code>{_escape(a['first_seen'])}</code> - <code>{_escape(a['last_seen'])}</code></td>
            <td>{a['total_attacks']}</td>
            <td>{_risk_badge(a['risk_score'])}</td>
        </tr>"""
        for a in attackers
    )

    ip_rows = "".join(
        f"""<tr><td><code>{_escape(i['src_ip'])}</code></td><td>{i['attempts']}</td>
            <td>{_escape(i['first_seen'])}</td><td>{_escape(i['last_seen'])}</td></tr>"""
        for i in top_ips
    )

    user_rows = "".join(
        f"<tr><td><code>{_escape(u['username'])}</code></td><td>{u['attempts']}</td></tr>"
        for u in top_users
    )
    pass_rows = "".join(
        f"<tr><td><code>{_escape(p['password'])}</code></td><td>{p['attempts']}</td></tr>"
        for p in top_pass
    )

    geo_rows = "".join(
        f"<tr><td><code>{_escape(g['geo_country'])}</code></td><td>{g['unique_ips']}</td><td>{g['total']}</td></tr>"
        for g in geo
    )

    protocol_rows = "".join(
        f"<tr><td>{_escape(p['protocol']).upper()}</td><td>{_escape(p['event_type'])}</td><td>{p['count']}</td></tr>"
        for p in protocols
    )

    event_rows = "".join(
        f"""<tr>
            <td>{_escape(e['timestamp'])}</td>
            <td><span class="proto">{_escape(e['protocol']).upper()}</span></td>
            <td><code>{_escape(e['src_ip'])}</code></td>
            <td>{_escape(e['event_type'])}</td>
            <td><code>{_escape(e.get('username') or '-')}</code></td>
            <td><code>{_escape(e.get('raw_data') or '-')}</code></td>
        </tr>"""
        for e in events[:200]
    )

    if not event_rows:
        event_rows = '<tr><td colspan="6" style="text-align:center">No events recorded</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Honeypot Intelligence Report</title>
<style>
:root {{
  --bg: #0d1117;
  --card: #161b22;
  --border: #30363d;
  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --orange: #d29922;
  --yellow: #e3b341;
  --text: #c9d1d9;
  --muted: #8b949e;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); }}
.container {{ max-width:1200px; margin:0 auto; padding:30px 24px; }}
header {{ border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:30px; }}
h1 {{ font-size:26px; color:#fff; background:linear-gradient(90deg,var(--accent),#bc8cff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
header p {{ color:var(--muted); margin-top:6px; font-size:14px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:30px; }}
.stat-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:18px; }}
.stat-card .value {{ font-size:30px; font-weight:700; color:#fff; }}
.stat-card .label {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; margin-top:4px; }}
section {{ margin-bottom:34px; }}
h2 {{ font-size:18px; color:#fff; margin-bottom:16px; border-left:3px solid var(--accent); padding-left:10px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--border); border-radius:8px; overflow:hidden; font-size:13px; }}
th,td {{ padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); }}
th {{ background:#21262d; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:0.06em; }}
tr:last-child td {{ border-bottom:none; }}
code {{ font-family:'Cascadia Mono',Consolas,monospace; font-size:12px; color:var(--green); }}
.proto {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.proto.SSH {{ background:rgba(88,166,255,.15); color:var(--accent); }}
.proto.HTTP {{ background:rgba(188,140,255,.15); color:#bc8cff; }}
.risk {{ display:inline-block; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.risk-critical {{ background:rgba(248,81,73,.18); color:var(--red); }}
.risk-high {{ background:rgba(248,81,73,.10); color:#f0883e; }}
.risk-medium {{ background:rgba(210,153,34,.15); color:var(--orange); }}
.risk-low {{ background:rgba(227,179,65,.12); color:var(--yellow); }}
.risk-unknown {{ background:rgba(139,148,158,.15); color:var(--muted); }}
footer {{ margin-top:40px; padding-top:16px; border-top:1px solid var(--border); color:var(--muted); font-size:12px; text-align:center; }}
@media print {{ body {{ background:#fff; color:#000; }} table {{ background:#fff; border-color:#ccc; }} }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Honeypot Intelligence Report</h1>
    <p>Generated: <strong>{_escape(generated_at)}</strong> &nbsp;|&nbsp; Source: SSH-HTTP Honeypot with Attacker Fingerprinting</p>
  </header>

  <div class="stats-grid">
    <div class="stat-card"><div class="value">{stats.get('total_events',0):,}</div><div class="label">Total Events</div></div>
    <div class="stat-card"><div class="value">{stats.get('total_attackers',0):,}</div><div class="label">Fingerprinted Attackers</div></div>
    <div class="stat-card"><div class="value">{stats.get('unique_ips',0):,}</div><div class="label">Unique IPs</div></div>
    <div class="stat-card"><div class="value">{stats.get('total_ssh',0):,}</div><div class="label">SSH Attempts</div></div>
    <div class="stat-card"><div class="value">{stats.get('total_http',0):,}</div><div class="label">HTTP Probes</div></div>
    <div class="stat-card"><div class="value" style="color:var(--red)">{stats.get('high_risk_attackers',0)}</div><div class="label">High-Risk Attackers</div></div>
  </div>

  <section>
    <h2>Top Attacker IPs</h2>
    <table><thead><tr><th>Source IP</th><th>Attempts</th><th>First Seen</th><th>Last Seen</th></tr></thead>
    <tbody>{ip_rows}</tbody></table>
  </section>

  <section>
    <h2>Fingerprinted Attackers</h2>
    <table><thead><tr><th>Fingerprint</th><th>Active Window</th><th>Attacks</th><th>Risk</th></tr></thead>
    <tbody>{attacker_rows}</tbody></table>
  </section>

  <section>
    <h2>Protocol Activity</h2>
    <table><thead><tr><th>Protocol</th><th>Event Type</th><th>Count</th></tr></thead>
    <tbody>{protocol_rows}</tbody></table>
  </section>

  <section>
    <h2>Geographic Distribution</h2>
    <table><thead><tr><th>Country</th><th>Unique IPs</th><th>Total Hits</th></tr></thead>
    <tbody>{geo_rows}</tbody></table>
  </section>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
    <section>
      <h2>Top Usernames Tried</h2>
      <table><thead><tr><th>Username</th><th>Attempts</th></tr></thead><tbody>{user_rows}</tbody></table>
    </section>
    <section>
      <h2>Top Passwords Tried</h2>
      <table><thead><tr><th>Password</th><th>Attempts</th></tr></thead><tbody>{pass_rows}</tbody></table>
    </section>
  </div>

  <section>
    <h2>Event Log (Last 200)</h2>
    <table><thead><tr><th>Timestamp</th><th>Protocol</th><th>Source IP</th><th>Event</th><th>Username</th><th>Raw Data</th></tr></thead>
    <tbody>{event_rows}</tbody></table>
  </section>

  <footer>Generated by Honeypot Intelligence System • {_escape(generated_at)}</footer>
</div>
</body>
</html>"""


def generate_json_report(data):
    return json.dumps(data, indent=2, default=str)