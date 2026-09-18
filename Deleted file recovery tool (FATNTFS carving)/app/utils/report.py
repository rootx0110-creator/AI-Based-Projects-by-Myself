"""HTML report generator with a clean, modern design."""
import html
import io
import os
import time
import webbrowser
from typing import List

from ..core.scan_engine import ScanResult


def _size(num):
    if not num or num <= 0:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def _esc(s):
    return html.escape(str(s or ""))


def _icon(ext: str) -> str:
    c = {
        "jpg": "#f39c12", "jpeg": "#f39c12", "png": "#8e44ad", "gif": "#16a085",
        "bmp": "#2980b9", "pdf": "#e74c3c", "doc": "#21618c", "docx": "#21618c",
        "xls": "#1e8449", "xlsx": "#1e8449", "ppt": "#d35400", "pptx": "#d35400",
        "zip": "#7f8c8d", "rar": "#7f8c8d", "7z": "#7f8c8d", "mp3": "#e67e22",
        "mp4": "#c0392b", "avi": "#c0392b", "mkv": "#c0392b", "exe": "#34495e",
        "txt": "#95a5a6", "sqlite": "#3498db", "html": "#e67e22",
    }
    return c.get(str(ext).lower().lstrip("."), "#5d6d7e")


def generate_html_report(result: ScanResult, drive_name: str,
                         details: List[dict]) -> str:
    """Return full HTML document as a string (with embedded CSS)."""
    fs_type = _esc(result.fs_type)
    total_records = len(details)
    total_size = sum(d.get("size", 0) or 0 for d in details)
    fs_ok = result.error == ""
    duration = (result.finished or time.time()) - (result.started or time.time())

    type_counts = {}
    for d in details:
        ext = (d.get("extension") or "other").lower()
        type_counts[ext] = type_counts.get(ext, 0) + 1
    top_types = sorted(type_counts.items(), key=lambda x: -x[1])[:10]

    rows = ""
    for d in details:
        ext = (d.get("extension") or "other").lower()
        color = _icon(ext)
        rows += (
            f"<tr><td><span class='badge' style='background:{color};color:#fff'>{_esc(ext)[:8]}</span></td>"
            f"<td class='fname'>{_esc(d.get('full_name') or d.get('name'))}</td>"
            f"<td>{_size(d.get('size'))}</td>"
            f"<td>{_esc(d.get('attributes'))}</td>"
            f"<td>{_esc(d.get('modified') or d.get('created'))}</td>"
            f"<td><span class='pill'>{_esc(d.get('status'))}</span></td></tr>"
        )
    if not rows:
        rows = "<tr><td colspan='6' class='empty'>No files were found on this scan.</td></tr>"

    type_bars = ""
    max_type = max([c for _, c in top_types] or [1])
    for ext, count in top_types:
        pct = count / max_type * 100
        type_bars += (
            f"<div class='bar-row'><span class='bar-label'>{_esc(ext)}</span>"
            f"<div class='bar'><div class='bar-fill' style='width:{pct:.0f}%'></div></div>"
            f"<span class='bar-count'>{count}</span></div>"
        )

    # file system metadata
    fs_rows = ""
    if result.ntfs_boot:
        b = result.ntfs_boot
        fs_rows += f"<tr><td>Cluster size</td><td>{_size(b.get('cluster_size'))}</td></tr>"
        fs_rows += f"<tr><td>MFT location (LCN)</td><td>{_esc(str(b.get('mft_lcn')))}</td></tr>"
        fs_rows += f"<tr><td>Total sectors</td><td>{_esc(str(b.get('total_sectors')))}</td></tr>"
    elif result.fat_info:
        fs = result.fat_info
        fs_rows += f"<tr><td>FAT type</td><td>{_esc(fs.fs_type)}</td></tr>"
        fs_rows += f"<tr><td>Sector size</td><td>{_size(fs.sector_size)}</td></tr>"
        fs_rows += f"<tr><td>Cluster size</td><td>{_size(fs.cluster_size)}</td></tr>"
        fs_rows += f"<tr><td>Total sectors</td><td>{_esc(str(fs.total_sectors))}</td></tr>"
        fs_rows += f"<tr><td>Volume label</td><td>{_esc(fs.label)}</td></tr>"
    else:
        fs_rows = "<tr><td>Filesystem</td><td>Not parseable / Unknown</td></tr>"

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deleted File Recovery Report</title>
<style>
  :root {{
    --bg: #0f172a; --panel: #1e293b; --border: #334155; --text: #e2e8f0;
    --muted: #94a3b8; --accent: #3b82f6; --accent2: #8b5cf6;
    --green: #22c55e; --amber: #f59e0b; --red: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text);
    padding: 24px; line-height: 1.55;
  }}
  .wrap {{ max-width: 1100px; margin: 0 auto; }}
  .header {{
    display: flex; align-items: center; gap: 16px;
    background: linear-gradient(135deg, #1e293b, #27364d);
    border: 1px solid var(--border);
    border-radius: 14px; padding: 24px 28px; margin-bottom: 20px;
  }}
  .logo {{
    width: 52px; height: 52px; border-radius: 12px; flex-shrink: 0;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: flex; align-items: center; justify-content: center;
    font-size: 26px; font-weight: 700; color: #fff;
  }}
  h1 {{ font-size: 22px; font-weight: 700; }}
  .sub {{ color: var(--muted); font-size: 13px; margin-top: 2px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  @media (max-width: 780px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 22px;
  }}
  .panel h2 {{ font-size: 15px; letter-spacing: .5px; margin-bottom: 14px; color: var(--text); }}
  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
  .stat .num {{ font-size: 26px; font-weight: 700; }}
  .stat .lbl {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
  .stat.fs .num {{ color: var(--accent); }}
  .stat.file .num {{ color: var(--accent2); }}
  .stat.size .num {{ color: var(--green); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #27334a; }}
  th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  tr:hover td {{ background: #25324a; }}
  .table-wrap {{ overflow-x: auto; }}
  .badge {{ padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }}
  .pill {{ padding: 2px 9px; border-radius: 20px; font-size: 11px; background:#1f2b46; color:var(--amber); border:1px solid #334155; }}
  .fname {{ color: var(--text); word-break: break-all; }}
  .empty {{ text-align:center; color: var(--muted); padding: 28px; }}
  .bar-row {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
  .bar-label {{ width: 70px; font-size:12px; color:var(--muted); }}
  .bar {{ flex:1; height:10px; background:#182338; border-radius: 6px; overflow:hidden; }}
  .bar-fill {{ height:100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius:6px; }}
  .bar-count {{ width:36px; text-align:right; font-size:12px; color:var(--muted); }}
  .foot {{ color: var(--muted); font-size: 12px; text-align:center; margin-top: 26px; }}
  .meta-table td {{ font-size: 13px; }}
  .meta-table td:first-child {{ color: var(--muted); width: 40%; }}
  .err {{ color: var(--red); font-size: 13px; margin-bottom: 14px; }}
  .chip {{ display:inline-block; padding:4px 14px; border-radius:20px; font-size:12px; background:#1c2b45; color: var(--accent); border:1px solid #2c3e63; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div class="logo">&#128451;</div>
    <div>
      <h1>Deleted File Recovery Report</h1>
      <div class="sub">{_esc(drive_name)} &nbsp;&bull;&nbsp; Generated {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
    <div style="margin-left:auto"><span class="chip">{_esc(fs_type)}</span></div>
  </div>

  <div class="grid">
    <div class="panel">
      <h2>Scan Summary</h2>
      <div class="stats">
        <div class="stat fs"><div class="num">{total_records}</div><div class="lbl">Files Found</div></div>
        <div class="stat file"><div class="num">{sum(1 for d in details if d.get('status')=='Deleted')}</div><div class="lbl">Deleted</div></div>
        <div class="stat size"><div class="num">{_size(total_size)}</div><div class="lbl">Total Size</div></div>
      </div>
    </div>
    <div class="panel">
      <h2>File System</h2>
      <table class="meta-table">
        {fs_rows}
        <tr><td>Scan duration</td><td>{duration:.1f} seconds</td></tr>
        <tr><td>Size scanned</td><td>{_size(result.sectors_scanned * 512 if result.sectors_scanned else result.total_sectors)}</td></tr>
      </table>
    </div>
  </div>

  {f"<div class='err'>Warning: {_esc(result.error)}</div>" if result.error else ""}

  <div class="grid">
    <div class="panel">
      <h2>File Types (Top 10)</h2>
      <div class="bar-row" style="margin-top:6px">
        {type_bars or "<p class='empty'>No type data</p>"}
      </div>
    </div>
    <div class="panel">
      <h2>Recovery Notes</h2>
      <p style="font-size:13px; color:var(--muted); margin-bottom:12px;">
        Files were recovered using filesystem-level analysis (FAT directory entries &amp; NTFS
        $MFT records) and raw signature carving across the volume. Recovery success depends on
        whether the underlying clusters were reused or overwritten after deletion.
      </p>
      <div style="display:flex; gap:10px; flex-wrap:wrap">
        <span class="chip">FAT deleted entries: {sum(1 for d in details if d.get('fs')=='FAT')}</span>
        <span class="chip">NTFS deleted records: {sum(1 for d in details if d.get('fs')=='NTFS')}</span>
        <span class="chip">Carved files: {sum(1 for d in details if d.get('fs')=='RAW')}</span>
      </div>
    </div>
  </div>

  <div class="panel" style="margin-bottom:20px">
    <h2>Found Files ({total_records})</h2>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Type</th><th>File Name</th><th>Size</th><th>Attributes</th><th>Modified</th><th>Status</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>

  <div class="foot">Generated by Deleted File Recovery Tool &mdash; FAT/NTFS &amp; Raw Carving</div>
</div>
</body>
</html>"""
    return html_doc


def save_html_report(result: ScanResult, drive_name: str, details: List[dict],
                     out_path: str) -> str:
    doc = generate_html_report(result, drive_name, details)
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def open_html_report(result: ScanResult, drive_name: str, details: List[dict],
                     out_dir: Optional[str] = None) -> str:
    if out_dir is None:
        out_dir = os.path.join(os.path.expanduser("~"), "Documents")
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"recovery_report_{stamp}.html")
    save_html_report(result, drive_name, details, path)
    webbrowser.open("file:///" + path.replace("\\", "/"))
    return path