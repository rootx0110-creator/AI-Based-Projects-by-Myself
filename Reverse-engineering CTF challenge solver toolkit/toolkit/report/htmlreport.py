"""HTML report generation for the solver toolkit.

Produces self-contained, dark-themed reports with an inline stylesheet and
markup so they can be saved / downloaded from the UI or opened directly.
"""

from __future__ import annotations

import datetime
import html
import json

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0f1117;color:#d6dbe5;line-height:1.6;padding:24px}
.wrap{max-width:1100px;margin:0 auto}
header{border-bottom:2px solid #2dd4bf;padding-bottom:16px;margin-bottom:24px}
h1{font-size:26px;color:#e7ebf3}
h1 span{color:#2dd4bf}
.meta{color:#8b93a5;font-size:13px;margin-top:6px}
h2{font-size:19px;color:#2dd4bf;margin:26px 0 12px;border-left:4px solid #2dd4bf;padding-left:10px}
h3{font-size:15px;color:#a7b6d0;margin:14px 0 6px}
table{width:100%;border-collapse:collapse;margin:8px 0 16px;font-size:13px}
th,td{border:1px solid #2a3142;padding:7px 10px;text-align:left;vertical-align:top}
th{background:#1a2130;color:#9fd8c9;font-weight:600}
tr:nth-child(even) td{background:#141925}
td.k{color:#8b93a5;width:170px;font-weight:600}
code,pre{font-family:Consolas,'Cascadia Code',monospace}
pre{background:#0d1017;border:1px solid #263048;border-radius:8px;padding:12px;overflow:auto;font-size:12.5px;color:#c6d3ea}
.mono{font-family:Consolas,monospace}
.tag{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700;margin-right:6px}
.t-ok{background:#0f3d2e;color:#4ade80}
.t-warn{background:#3d2e0f;color:#facc15}
.t-info{background:#12303d;color:#38bdf8}
.t-bad{background:#3d1216;color:#f87171}
.cards{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}
.card{flex:1 1 200px;background:#141925;border:1px solid #263048;border-radius:10px;padding:14px}
.card .v{font-size:22px;color:#2dd4bf;font-weight:700}
.card .l{font-size:12px;color:#8b93a5;margin-top:4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
footer{margin-top:38px;color:#5d6678;font-size:12px;text-align:center;border-top:1px solid #263048;padding-top:14px}
.ent-bar{height:14px;background:#0d1017;border-radius:7px;overflow:hidden;margin:6px 0;border:1px solid #263048}
.ent-fill{height:100%;background:linear-gradient(90deg,#4ade80,#facc15,#f87171);width:0%}
.small{font-size:12px;color:#8b93a5}
span.ent-val{font-weight:600;color:#d6dbe5}
"""


def _esc(s) -> str:
    return html.escape(str(s))


class HtmlReport:
    def __init__(self, title: str = "RE CTF Toolkit Report"):
        self.title = title
        self.parts: list[str] = []
        self.created = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _doc(self) -> str:
        return self.parts

    def header_block(self, file_name: str, source_desc: str) -> None:
        self.parts.append(
            f'<header><h1><span>&#x1F50E;</span> Reverse-Engineering CTF Toolkit Report</h1>'
            f'<div class="meta">Target: <b>{_esc(file_name)}</b> &middot; {_esc(source_desc)}'
            f' &middot; Generated {_esc(self.created)}</div></header>'
        )

    def card_row(self, cards: list[tuple[str, str]]) -> None:
        inner = "".join(
            f'<div class="card"><div class="v">{_esc(v)}</div><div class="l">{_esc(l)}</div></div>'
            for v, l in cards
        )
        self.parts.append(f'<div class="cards">{inner}</div>')

    def section(self, name: str, tag: str | None = None) -> None:
        t = f' <span class="tag t-info">{_esc(tag)}</span>' if tag else ""
        self.parts.append(f"<h2>{_esc(name)}{t}</h2>")

    def subsection(self, name: str) -> None:
        self.parts.append(f"<h3>{_esc(name)}</h3>")

    def kv_table(self, rows: list[tuple[str, str]]) -> None:
        body = "".join(
            f"<tr><td class='k'>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
            for k, v in rows
        )
        self.parts.append(f"<table><tbody>{body}</tbody></table>")

    def table(self, headers: list[str], rows: list[list], mono_cols: set[int] | None = None) -> None:
        mono_cols = mono_cols or set()
        head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
        body_r = []
        for row in rows:
            cells = "".join(
                f"<td class='mono'>{_esc(c)}</td>" if i in mono_cols else f"<td>{_esc(c)}</td>"
                for i, c in enumerate(row)
            )
            body_r.append(f"<tr>{cells}</tr>")
        self.parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_r)}</tbody></table>")

    def codeblock(self, text: str, max_chars: int = 12000) -> None:
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"
        self.parts.append(f"<pre>{_esc(text)}</pre>")

    def text(self, text: str) -> None:
        self.parts.append(f"<p>{_esc(text)}</p>")

    def pre_only(self, preview: str) -> None:
        self.parts.append(f"<pre class='small'>{_esc(preview)}</pre>")

    def render(self) -> str:
        body = "\n".join(self.parts)
        footer = (
            f'<footer>Generated by <b>Reverse-Engineering CTF Challenge Solver Toolkit</b> '
            f'at {_esc(self.created)}. Use the flag candidates with care &#8212; '
            f'this tool performs stateless heuristics, not full decompilation.</footer>'
        )
        return (
            "<!DOCTYPE html>\n<html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_esc(self.title)}</title><style>{CSS}</style></head>"
            f"<body><div class='wrap'>{body}{footer}</div></body></html>"
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render())


def build_file_report(info: dict, strings: list[dict] | None,
                      entropy: dict | None, hex_rows: list[dict] | None,
                      frequency: list[dict] | None, findings: list[str]) -> str:
    """Convenience builder for a whole-file static analysis report."""
    r = HtmlReport(f"Analysis - {info.get('file', 'target')}")
    r.header_block(info.get("file", "target"), info.get("path", "unknown"))
    r.card_row([
        (info.get("size_human", "?"), "File size"),
        (info.get("file_type", "?"), "Identified type"),
        (f"{entropy['overall']:.2f} bits" if entropy else "?", "Shannon entropy"),
        (info.get("sha256", "?")[:12], "SHA-256 (prefix)"),
    ])

    r.section("File Metadata", "static")
    r.kv_table([
        ("File", info.get("file", "")),
        ("Path", info.get("path", "")),
        ("Size", f"{info.get('size_human')} ({info.get('size')} bytes)"),
        ("Magic bytes", info.get("magic_hex", "")),
        ("Detected type", info.get("file_type", "")),
        ("MD5", info.get("md5", "")),
        ("SHA-1", info.get("sha1", "")),
        ("SHA-256", info.get("sha256", "")),
        ("CRC32", info.get("crc32", "")),
    ])

    extra = info.get("extra", {})
    for k in ("pe_label", "pe_machine", "pe_type", "pe_entry_point_rva", "pe_sections",
              "elf_label", "elf_class", "elf_endian", "elf_type", "elf_machine"):
        if k in extra and extra[k]:
            r.kv_table([(k.lstrip("pe_").lstrip("elf_").replace("_", " ").title(), str(extra[k]))])

    if entropy:
        r.section("Entropy Analysis", "heuristic")
        pct = min(100.0, entropy["overall"] / 8.0 * 100.0)
        r.kv_table([
            ("Overall entropy", f'{entropy["overall"]:.3f} bits / byte'),
            ("Block minimum", f'{entropy["block_min"]:.3f}'),
            ("Block maximum", f'{entropy["block_max"]:.3f}'),
            ("Block average", f'{entropy["block_avg"]:.3f}'),
            ("Verdict", entropy.get("verdict", "")),
        ])
        r.parts.append(
            f"<label class='small'>Overall entropy:</label>"
            f"<div class='ent-bar'><div class='ent-fill' style='width:{pct:.1f}%'></div></div>"
        )

    if strings is not None:
        r.section("Extracted Strings", "strings")
        r.text(f"{len(strings)} strings found.")
        rows = [[s["offset"], s["kind"].upper(), s["value"]] for s in strings[:400]]
        r.table(["Offset", "Type", "String"], rows, mono_cols={0, 1})

    if hex_rows:
        r.section("Hex Dump Preview", "binary")
        rows = [["0x%08X" % h["offset"], h["hex"], h["ascii"]] for h in hex_rows[:200]]
        r.table(["Offset", "Hex", "ASCII"], rows, mono_cols={0, 1, 2})

    if frequency:
        r.section("Letter Frequency", "crypto")
        freq_rows = []
        for f in frequency:
            bar = min(100.0, f["percent"] * 3.0)
            cell = f"<span class='ent-fill' style='{'width:%.1f%%' % bar}'></span>"
            freq_rows.append([f["letter"], f"{f['percent']:.2f}%", cell])
        head = "<th>Letter</th><th>%</th><th>Distribution</th>"
        body = "".join(
            f"<tr><td class='mono'>{_esc(x)}</td><td class='mono'>{_esc(y)}</td>"
            f"<td><div class='ent-bar'>{z}</div></td></tr>"
            for x, y, z in freq_rows
        )
        r.parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")

    if findings:
        r.section("Notable Findings", "conclusions")
        r.parts.append("<table><tbody>" + "".join(f"<tr><td>{_esc(f)}</td></tr>" for f in findings) + "</tbody></table>")

    return r.render()


def build_solver_report(kind: str, payload_desc: str, results: list[dict],
                        note: str = "") -> str:
    """Builder for cipher / encoding solver result reports."""
    r = HtmlReport(f"Solver report - {kind}")
    r.header_block(payload_desc, kind)
    r.text(note or f"Results for {kind} analysis on: {payload_desc}.")
    for i, res in enumerate(results, start=1):
        expected = {"name": "Encoding", "key": "Key", "shift": "Shift",
                    "key_len": "Key length", "score": "Score"}.get(
            next((k for k in ("name", "key", "shift", "key_len") if k in res), "score"), "Value")
        label_val = next((res[k] for k in ("name", "key", "shift", "key_len") if k in res), "")
        r.section(f"Candidate #{i}", f"score {res.get('score', 0):.1f}")
        rows = [(expected, str(label_val))]
        if res.get("key_hex"):
            rows.append(("Key (hex)", res["key_hex"]))
        if res.get("method"):
            rows.append(("Method", res["method"]))
        r.kv_table(rows)
        r.subsection("Output")
        r.pre_only(_preview(res.get("data", res.get("decoded", ""))))
    return r.render()


def _preview(v, limit: int = 2048) -> str:
    if isinstance(v, bytes):
        try:
            v = v.decode("ascii")
        except UnicodeDecodeError:
            v = v.hex(" ").upper()
    v = str(v)
    if len(v) > limit:
        v = v[:limit] + " ..."
    return v