"""HTML report generation for redaction runs."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, List, Optional

from core.redactor import RedactionResult, Redactor


def _row_color(key: str) -> str:
    mode = Redactor.MODES.get(key)
    return mode.color if mode else "#64748b"


def _safe_preview(value: str, strategy: str) -> str:
    """A short masked preview so the report never embeds raw values."""
    if not value:
        return "\u2013"
    value = value.strip()
    keep = min(3, len(value))
    return html.escape(value[:keep] + "***")


_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
  min-height: 100vh; padding: 40px 24px;
}
.wrap { max-width: 980px; margin: 0 auto; }
header { text-align: center; padding-bottom: 28px; border-bottom: 1px solid #334155; margin-bottom: 28px; }
header h1 {
  font-size: 30px; font-weight: 700; letter-spacing: .3px;
  background: linear-gradient(90deg, #38bdf8, #a78bfa, #f472b6);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
header p { margin-top: 8px; color: #94a3b8; font-size: 14px; }
.badge { display:inline-block; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:600; margin-top:12px;
  background:#1e293b; color:#38bdf8; border:1px solid #334155; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }
.metric { background:#1e293b; border:1px solid #334155; border-radius:14px; padding:18px; text-align:center; }
.metric .num { font-size: 30px; font-weight: 800; color: #38bdf8; }
.metric .lbl { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-top:6px; }
.card { background:#1e293b; border:1px solid #334155; border-radius:14px; padding:22px; margin-bottom: 24px; }
.card h2 { font-size: 17px; font-weight: 600; margin-bottom: 4px; }
.card .sub { color: #94a3b8; font-size: 13px; margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing:.8px; border-bottom:1px solid #334155; }
td { padding: 10px 12px; border-bottom: 1px solid #1e293b; vertical-align: top; word-break: break-word; }
tr:last-child td { border-bottom: none; }
.typepill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; color:#fff; }
.code { font-family: "Cascadia Code", Consolas, monospace; font-size: 13px; }
pre {
  background:#0b1220; border:1px solid #1e293b; border-radius:10px; padding:16px;
  font-family:"Cascadia Code", Consolas, monospace; font-size:13px; line-height:1.55;
  max-height: 420px; overflow:auto; white-space: pre-wrap; word-break: break-all;
}
footer { text-align:center; color:#64748b; font-size:12px; margin-top:32px; }
.conf { color:#34d399; }
.warn { color:#fbbf24; }
.danger { color:#f87171; }
"""


def build_html_report(
    result: RedactionResult,
    config: Dict[str, object],
    original: str,
) -> str:
    """Return a complete, self-contained HTML document describing the run."""
    ts = datetime.now()
    now = ts.strftime("%Y-%m-%d %H:%M:%S")
    strategy = config.get("strategy", Redactor.DEFAULT_STRATEGY)
    strategy_label = strategy.upper()

    total = result.total_redactions
    chars_before = len(original)
    chars_after = len(result.text)
    reduction = chars_before - chars_after
    reduction_pct = (reduction / chars_before * 100.0) if chars_before else 0.0

    # Table rows by count
    table_rows = ""
    for key, count in sorted(result.counts.items(), key=lambda kv: -kv[1]):
        mode = Redactor.MODES.get(key)
        label = mode.label if mode else key
        color = _row_color(key)
        samples = result.samples.get(key, [])
        sample_str = _safe_preview(samples[0], strategy) if samples else "\u2013"
        counts = f"{count}"
        more = (
            f'<span style="color:#64748b;font-size:12px">+{len(samples) - 1} more</span>'
            if len(samples) > 1
            else ""
        )
        table_rows += (
            f"<tr>"
            f'<td><span class="typepill" style="background:{color}">{html.escape(label)}</span></td>'
            f"<td class=\"code\">{sample_str} {more}</td>"
            f"<td style=\"text-align:right;font-weight:700\">{counts}</td>"
            f"</tr>"
        )

    if not table_rows:
        table_rows = (
            '<tr><td colspan="3" style="text-align:center;color:#94a3b8">'
            "No sensitive patterns were detected.</td></tr>"
        )

    config_lines = []
    enabled = config.get("enabled", {})
    if enabled:
        on = ", ".join(Redactor.LABELS.get(k, k) for k, v in enabled.items() if v)
        off = ", ".join(Redactor.LABELS.get(k, k) for k, v in enabled.items() if not v)
        config_lines.append(f"Detection modules: <b>{on or 'none'}</b>"
                            + (f" (off: {off})" if off else ""))
    else:
        config_lines.append("Detection modules: <b>all enabled</b>")
    config_lines.append(f"Redaction strategy: <b class=\"conf\">{strategy_label}</b>")
    if strategy == Redactor.STRATEGY_MASK:
        config_lines.append("Masking: keep first chars + "
                            f"<b class=\"conf\">{Redactor.MASK_SUFFIX}</b>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Log Anonymization Report \u2014 {now}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Log Anonymization Report</h1>
    <p>Generated safely &#128274; \u2014 no original sensitive values are included below</p>
    <span class="badge">Run # {ts.strftime("%H%M%S")}</span>
  </header>

  <section class="metrics">
    <div class="metric"><div class="num">{total}</div><div class="lbl">Items Redacted</div></div>
    <div class="metric"><div class="num">{reduction:,}</div><div class="lbl">Chars Removed</div></div>
    <div class="metric"><div class="num">{reduction_pct:.1f}%</div><div class="lbl">Data Reduction</div></div>
    <div class="metric"><div class="num">{result.elapsed_ms:.0f} ms</div><div class="lbl">Processing Time</div></div>
  </section>

  <section class="card">
    <h2>Redaction Summary</h2>
    <div class="sub">Sensitive categories detected and desensitized.</div>
    <table>
      <thead><tr><th>Category</th><th>Sample (truncated)</th><th style="text-align:right">Count</th></tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>Configuration</h2>
    <div class="sub">Settings used for this anonymization pass.</div>
    <p style="line-height:2">{"<br>".join(config_lines)}</p>
  </section>

  <section class="card">
    <h2>Redacted Output</h2>
    <div class="sub">Below is the sanitized log. Copy it with confidence.</div>
    <pre>{html.escape(result.text[:8000])}</pre>
  </section>

  <footer>
    Generated by Log Anonymizer &amp; Redactor \u2014 {now}<br>
    Report produced locally; nothing was sent over the network.
  </footer>
</div>
</body>
</html>"""


def save_html_report(result: RedactionResult, config: Dict[str, object], original: str, path: str) -> str:
    """Write the report to ``path`` and return it."""
    doc = build_html_report(result, config, original)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path