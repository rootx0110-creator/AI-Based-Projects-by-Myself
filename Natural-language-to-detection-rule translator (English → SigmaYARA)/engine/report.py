# =============================================================================
#  Self-contained HTML report generation (dark SOC style, printable)
# =============================================================================
import html as html_mod
from datetime import datetime

REPORT_CSS = """
:root{--bg:#0b0f17;--panel:#111827;--panel2:#0f1624;--line:#1f2a3f;--txt:#dbe4f0;
--mut:#64748b;--cy:#22d3ee;--gr:#34d399;--ma:#f472b6;--am:#a78bfa;--rd:#f87171;--ye:#fbbf24}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Segoe UI,system-ui,Arial,sans-serif;background:var(--bg);color:var(--txt);line-height:1.55;padding:32px}
.wrap{max-width:1060px;margin:0 auto}
.head{display:flex;gap:24px;align-items:center;padding:8px 0 20px;border-bottom:1px solid var(--line)}
.brand{font-size:12px;letter-spacing:3px;color:var(--cy);text-transform:uppercase;font-weight:700}
.brand b{color:var(--gr)}
h1{font-size:26px;margin:6px 0 2px;background:linear-gradient(90deg,var(--cy),var(--gr));-webkit-background-clip:text;background-clip:text;color:transparent}
.meta{font-size:13px;color:var(--mut);margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:22px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.card .k{font-size:11px;letter-spacing:1.5px;color:var(--mut);text-transform:uppercase}
.card .v{font-size:24px;font-weight:800;margin-top:4px}
.card .v.cy{color:var(--cy)} .card .v.gr{color:var(--gr)} .card .v.ma{color:var(--ma)}
.card .v.am{color:var(--am)} .card .v.rd{color:var(--rd)} .card .v.ye{color:var(--ye)}
.section{margin-top:26px}
h2{font-size:16px;letter-spacing:1px;text-transform:uppercase;color:var(--cy);margin-bottom:12px}
h2 span{color:var(--mut);font-weight:400;letter-spacing:0}
.box{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
pre{background:#060a12;border:1px solid var(--line);border-radius:10px;padding:18px;
font-family:'Cascadia Code','Consolas',monospace;font-size:12.5px;overflow-x:auto;white-space:pre;color:#c8e0ff}
.kw{color:#7dd3fc}.st{color:#86efac}.co{color:#64748b}.id{color:#e2e8f0}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:#0e2230;border:1px solid #123d55;color:#67e8f9;font-size:12px;padding:6px 12px;border-radius:999px;font-family:'Consolas',monospace}
.chip b{color:#a5f3fc;font-weight:700}
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:top}
.tbl tr:last-child td{border-bottom:none}
.tactic{font-size:11px;color:var(--am);letter-spacing:.5px}
.foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--mut);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.tag{display:inline-block;background:#101a2b;border:1px solid var(--line);color:var(--mut);
font-size:11px;padding:3px 10px;border-radius:999px;margin:3px 4px 0 0}
.lv{display:inline-block;font-weight:800;font-size:12px;padding:3px 12px;border-radius:999px;text-transform:uppercase}
.lv.critical{background:#2a1212;color:#f87171;border:1px solid #7f1d1d}
.lv.high{background:#2a1a10;color:#fb923c;border:1px solid #7c2d12}
.lv.medium{background:#20260f;color:#facc15;border:1px solid #4d7c0f}
.lv.low{background:#101a2b;color:#94a3b8;border:1px solid #1e293b}
.input-quote{font-style:italic;color:#94a3b8;font-size:13.5px;border-left:3px solid var(--cy);padding-left:14px}
@media print{body{background:#fff;color:#111}.panel,pre{background:#fff}.co{display:none}}
"""


def _esc(text):
    return html_mod.escape(str(text or ""))


def _tagged_yaml(yaml_text):
    """Very small YAML highlighter (keys, values noted by :, comments)."""
    out = []
    for line in yaml_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out.append(f'<span class="co">{_esc(line)}</span>')
            continue
        if ":" in line:
            key, _, rest = line.partition(":")
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{_esc(indent)}<span class="kw">{_esc(key)}</span>:'
                       f'<span class="st">{_esc(rest)}</span>')
        else:
            out.append(_esc(line))
    return "<br>".join(out)


def _tagged_meta_only(text):
    """For YARA: highlight <rule> name, meta ids, string ids."""
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("rule "):
            name = stripped.split(" ", 1)[1]
            out.append(f'<span class="kw">rule</span> <span class="id">{_esc(name)}</span>')
        elif " = " in stripped:
            key, _, rest = stripped.partition(" = ")
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{_esc(indent)}<span class="kw">{_esc(key)}</span> = '
                       f'<span class="st">{_esc(rest)}</span>')
        elif stripped.startswith(("$", "strings:", "condition:", "{", "}")):
            out.append(_esc(line))
        else:
            out.append(_esc(line))
    return "<br>".join(out)


def build_report_html(results, version="1.0.0"):
    """Build a fully self-contained styled HTML report."""
    confidence = results.get("confidence_pct", 0)
    entities = results.get("entities_summary", {})
    mitre = results.get("mitre", [])
    concepts = results.get("concepts", [])
    level_cls = results.get("level", "medium")

    # entities sections
    ent_html = []
    for cat, items in entities.items():
        chip_html = "".join(
            f'<span class="chip"><b>{_esc(it["value"])}</b>'
            + (f' <small style="color:#475569">{_esc(it.get("hint",""))}</small>' if it.get("hint") else "")
            + "</span>" for it in items
        )
        ent_html.append(
            f'<div style="margin-bottom:14px"><div style="font-size:12px;'
            f'letter-spacing:1px;color:#64748b;text-transform:uppercase;'
            f'margin-bottom:8px">{_esc(cat)} ({len(items)})</div>'
            f'<div class="chips">{chip_html}</div></div>'
        )
    entities_block = "".join(ent_html) if ent_html else \
        '<span class="tag">No explicit artifacts detected</span>'

    concept_rows = "".join(
        f'<tr><td>{_esc(k.get("label",""))}</td>'
        f'<td style="font-size:12px;color:#94a3b8">{" / ".join(_esc(p) for p in k.get("phrase",[])[:5])}</td>'
        f'<td class="tactic">{_esc(k.get("mitre",""))}</td></tr>'
        for k in concepts
    )
    concept_block = f'<table class="tbl">{concept_rows}</table>' if concept_rows else \
        '<span class="tag">No detection concepts matched</span>'

    mitre_rows = "".join(
        f'<tr><td class="tactic">{_esc(m["id"])}</td>'
        f'<td>{_esc(m["name"])}</td>'
        f'<td style="color:#34d399">{m.get("score",1)}x</td></tr>' for m in mitre
    )
    mitre_block = f'<table class="tbl">{mitre_rows}</table>' if mitre_rows else \
        '<span class="tag">No technique mapped</span>'

    tags = "".join(
        f'<span class="tag">attack.{m["id"].lower().replace(".", ".")}</span>'
        for m in mitre[:8]
    )

    ls = results.get("logsource", {})
    logsource_str = f'{ls.get("category","-")} / {ls.get("product","-")}'

    level_label = results.get("level", "medium").upper()
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Detection Rule Report - NL2Rule</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <div class="brand">Natural Language &#8594; Detection Rules <b>// REPORT</b></div>
      <h1>Sigma &amp; YARA Detection Rule Package</h1>
      <div class="meta">Generated {_esc(results.get("generated_at",""))} &middot;
        Version {version} &middot; Confidence {confidence}%</div>
    </div>
  </div>

  <div class="grid">
    <div class="card"><div class="k">Confidence</div><div class="v cy">{confidence}%</div></div>
    <div class="card"><div class="k">Artifacts Found</div><div class="v gr">{results.get("entities_count",0)}</div></div>
    <div class="card"><div class="k">Concepts Detected</div><div class="v ma">{len(results.get("concepts",[]))}</div></div>
    <div class="card"><div class="k">MITRE Techniques</div><div class="v am">{len(results.get("mitre",[]))}</div></div>
    <div class="card"><div class="k">Level</div><div class="v ye"><span class="lv {level_cls}">{level_label}</span></div></div>
    <div class="card"><div class="k">Logsource</div><div class="v" style="font-size:15px">{_esc(logsource_str)}</div></div>
  </div>

  <div class="section">
    <h2>Input <span>// original description</span></h2>
    <div class="box"><div class="input-quote">&ldquo;{_esc(results.get("input",""))}&rdquo;</div></div>
  </div>

  <div class="section">
    <h2>Extracted Artifacts <span>// entities</span></h2>
    <div class="box">{entities_block}</div>
  </div>

  <div class="section">
    <h2>Detection Concepts <span>// what was understood</span></h2>
    <div class="box">{concept_block}{tags and ('<div style="margin-top:12px">' + tags + '</div>') or ''}</div>
  </div>

  <div class="section">
    <h2>MITRE ATT&CK Mapping</h2>
    <div class="box">{mitre_block}</div>
  </div>

  <div class="section">
    <h2>Sigma Rule</h2>
    <pre>{_tagged_yaml(results.get("sigma",""))}</pre>
  </div>

  <div class="section">
    <h2>YARA Rule</h2>
    <pre>{_tagged_meta_only(results.get("yara",""))}</pre>
  </div>

  <div class="foot">
    <span>Generated by <b>NL2Rule Translator</b> {version}</span>
    <span>For legitimate detection engineering &amp; blue-team lab use only.</span>
  </div>
</div>
</body>
</html>"""
    return html_doc


def render_to_file(results, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_report_html(results))
    return path