import html
from datetime import datetime

STATUS_COLORS = {"solved": "#3fb950", "in_progress": "#d29922", "todo": "#6e7681"}
DIFF_COLORS = {"Easy": "#3fb950", "Medium": "#d29922", "Hard": "#f85149"}


def _ts(iso):
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        return iso


def render_report(stats, challenges, hint_log, generated_at):
    stat_cells = "".join(
        f'<div class="stat"><span class="n">{v}</span><span class="l">{k}</span></div>'
        for k, v in [
            ("Total Challenges", stats["total"]),
            ("Solved", stats["solved"]),
            ("In Progress", stats["in_progress"]),
            ("To Do", stats["todo"]),
            ("Hints Given", stats["hints"]),
            ("AI Hints", stats["ai_hints"]),
        ]
    )

    cat_rows = "".join(
        f'<div class="cat"><span>{html.escape(r["category"])}</span>'
        f'<div class="track"><div class="fill" style="width:{r["c"]/max(stats["total"],1)*100:.1f}%"></div></div>'
        f'<b>{r["c"]}</b></div>'
        for r in stats["categories"]
    )

    ch_rows = []
    for i, c in enumerate(challenges, 1):
        st = STATUS_COLORS.get(c["status"], "#6e7681")
        df = DIFF_COLORS.get(c["difficulty"], "#8b949e")
        ch_rows.append(
            f'<tr><td class="num">{i}</td>'
            f'<td><div class="tt">{html.escape(c["title"])}</div>'
            f'<div class="by">#{c["id"]}</div></td>'
            f'<td><span class="badge" style="--c:{df}">{html.escape(c["difficulty"])}</span></td>'
            f'<td>{html.escape(c["category"])}</td>'
            f'<td><span class="badge" style="--c:{st}">{html.escape(c["status"])}</span></td>'
            f'<td>{c["hint_count"]}</td><td>{c["ai_count"]}</td>'
            f'<td class="nowrap">{_ts(c["created_at"])}</td>'
            f'<td class="nowrap">{_ts(c["solved_at"])}</td></tr>'
        )

    log_rows = []
    for h in hint_log:
        src = "AI" if h["source"] == "ai" else ("Prepared" if h["source"] == "authored" else "Engine")
        log_rows.append(
            f'<tr><td class="num">{html.escape(h["challenge_title"])}</td>'
            f'<td>#{h["level"]}</td>'
            f'<td><span class="src">{src}</span></td>'
            f'<td>{html.escape(h["content"])}</td>'
            f'<td class="nowrap">{_ts(h["created_at"])}</td></tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CTF Hint Engine — Progress Report</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:"Segoe UI",Roboto,Arial,sans-serif; background:#0b0e14; color:#c9d1d9; }}
header {{ padding:28px 36px; background:linear-gradient(135deg,#0f2440,#0d1117 70%,#11151c); border-bottom:1px solid #21262d; }}
h1 {{ margin:0 0 6px; font-size:24px; color:#e6edf3; }}
h1 span {{ color:#58a6ff; }}
.sub {{ color:#8b949e; font-size:13px; margin-top:2px; }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:20px; }}
.stat {{ background:#12161f; border:1px solid #21262d; border-radius:10px; padding:10px 16px; min-width:104px; text-align:center; }}
.stat .n {{ display:block; font-size:22px; font-weight:700; color:#58a6ff; }}
.stat .l {{ font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:.5px; }}
main {{ padding:22px 36px; }}
h2 {{ font-size:17px; color:#e6edf3; border-bottom:1px solid #21262d; padding-bottom:8px; margin:30px 0 14px; }}
.cats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; }}
.cat {{ display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; font-size:13px; }}
.cat b {{ color:#58a6ff; }}
.track {{ height:8px; background:#161b22; border-radius:6px; overflow:hidden; }}
.fill {{ height:100%; background:linear-gradient(90deg,#58a6ff,#3fb950); border-radius:6px; }}
table {{ width:100%; border-collapse:collapse; background:#0d1117; border:1px solid #21262d; border-radius:10px; overflow:hidden; }}
th {{ text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#8b949e; padding:10px 12px; background:#161b22; border-bottom:1px solid #30363d; }}
td {{ padding:10px 12px; border-bottom:1px solid #161b22; font-size:13px; vertical-align:top; }}
tr:last-child td {{ border-bottom:none; }}
tr:hover td {{ background:#11151c; }}
.num {{ color:#484f58; }}
.tt {{ font-weight:600; color:#e6edf3; }}
.by {{ font-size:11px; color:#484f58; }}
.badge {{ display:inline-block; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:600; color:#000; background:var(--c); }}
.src {{ display:inline-block; padding:1px 8px; border-radius:12px; font-size:11px; font-weight:600; background:#1f6feb; color:#fff; }}
.nowrap {{ white-space:nowrap; }}
.wrap {{ max-width:480px; }}
footer {{ padding:16px 36px; color:#484f58; font-size:12px; border-top:1px solid #21262d; }}
@media (max-width:720px) {{ main,header,footer {{ padding:16px; }} table {{ font-size:12px; }} }}
</style>
</head>
<body>
<header>
  <h1>AI-Driven CTF Hint Engine <span>&#9679; Progress Report</span></h1>
  <div class="sub">Training platform skill — generated {generated_at}</div>
  <div class="stats">{stat_cells}</div>
</header>
<main>
  <h2>Challenges by Category</h2>
  <div class="cats">{cat_rows}</div>
  <h2>Challenge Overview ({stats["total"]})</h2>
  <table>
    <thead><tr><th>#</th><th>Challenge</th><th>Difficulty</th><th>Category</th><th>Status</th><th>Hints</th><th>AI Hints</th><th>Created</th><th>Solved</th></tr></thead>
    <tbody>{''.join(ch_rows)}</tbody>
  </table>
  <h2>Hint Activity Timeline ({len(hint_log)})</h2>
  <table>
    <thead><tr><th>Challenge</th><th>Level</th><th>Source</th><th>Hint</th><th>Time</th></tr></thead>
    <tbody>{''.join(log_rows)}</tbody>
  </table>
</main>
<footer>Exported from the AI-Driven CTF Hint Engine. Hints are training aids, not answers — flags are never disclosed.</footer>
</body>
</html>"""