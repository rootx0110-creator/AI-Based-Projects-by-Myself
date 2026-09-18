import json
import os
import platform
import socket
import time
from datetime import datetime

import psutil

from .alerts import SEVERITIES
from .config import APP_NAME, APP_VERSION


def system_info(agent):
    """Collect host + agent status information used by all report formats."""
    try:
        vm = psutil.virtual_memory()
        mem_total = vm.total
        mem_used = vm.used
    except Exception:
        mem_total = mem_used = 0

    dirs = agent.watch_dirs()
    try:
        files = sum(agent.storage.baseline_file_count(d) for d in dirs)
    except Exception:
        files = 0
    try:
        counts = agent.storage.alert_counts()
        open_alerts = sum(c["open"] for c in counts.values())
    except Exception:
        counts = {}
        open_alerts = 0
    try:
        boot = psutil.boot_time()
        uptime_s = int(time.time() - boot)
    except Exception:
        uptime_s = 0

    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "host": {
            "hostname": socket.gethostname(),
            "os": platform.system() + " " + platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "user": os.environ.get("USERNAME") or os.environ.get("USER") or "-",
            "cpu_count": psutil.cpu_count() or 0,
            "cpu_usage": psutil.cpu_percent(interval=None),
            "mem_total_mb": round(mem_total / (1024 * 1024), 1) if mem_total else 0,
            "mem_used_mb": round(mem_used / (1024 * 1024), 1) if mem_used else 0,
            "uptime_sec": uptime_s,
        },
        "modules": {
            "fim_enabled": agent.config.get("fim_enabled", True),
            "process_enabled": agent.config.get("process_enabled", True),
            "paused": agent.paused,
            "fim_interval_sec": agent.config.get("scan_interval_sec", 300),
            "process_interval_sec": agent.config.get("process_interval_sec", 60),
            "hash_algorithm": agent.config.get("hash_algorithm", "sha256"),
            "last_scan": agent.last_scan["time"],
            "last_snapshot": agent.last_snapshot["time"],
        },
        "stats": {
            "watch_dirs": len(dirs),
            "files_monitored": files,
            "processes": agent.last_snapshot["count"],
            "open_alerts": open_alerts,
        },
        "watch_dirs": [
            {"path": d, "files": agent.storage.baseline_file_count(d)} for d in dirs
        ],
        "alert_counts": {str(k): v for k, v in counts.items()},
    }


def alert_rows(alerts_data):
    out = []
    for r in alerts_data:
        out.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
            "severity": SEVERITIES.get(r["severity"], str(r["severity"])),
            "source": r["source"],
            "status": r["status"],
            "title": r["title"],
            "detail": r["detail"] or "",
        })
    return out


def top_processes(limit=15):
    try:
        procs = sorted(
            (r for r in _snapshot_rows() if r.get("cpu") or r.get("mem_mb")),
            key=lambda r: max(r.get("cpu", 0), r.get("mem_mb", 0)),
            reverse=True,
        )
    except Exception:
        return []
    return procs[:limit]


def _snapshot_rows():
    from .process_monitor import snapshot
    return snapshot()


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
def build_html(agent, alert_limit=200, proc_limit=15):
    si = system_info(agent)
    try:
        alerts = agent.storage.alerts(min_severity=1, limit=alert_limit)
    except Exception:
        alerts = []
    rows = alert_rows(alerts)
    procs = top_processes(proc_limit)
    dirs = si["watch_dirs"]
    counts = si["alert_counts"]

    def uptime_fmt(s):
        if not s:
            return "unknown"
        d, r = divmod(s, 86400)
        h, m = divmod(r, 3600)
        m2, s2 = divmod(m, 60)
        parts = []
        if d:
            parts.append(f"{d}d")
        if h:
            parts.append(f"{h}h")
        parts.append(f"{m2}m")
        return " ".join(parts)

    rows_html = "".join(
        f"<tr><td>{r['time']}</td>"
        f"<td><span class='sev sev{r['severity']}'>{r['severity']}</span></td>"
        f"<td>{r['source']}</td>"
        f"<td>{r['status']}</td>"
        f"<td>{_esc(r['title'])}</td>"
        f"<td>{_esc(r['detail'])[:120]}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='6' class='muted'>No events recorded.</td></tr>"

    dirs_html = "".join(
        f"<tr><td>{_esc(d['path'])}</td><td>{d['files']}</td></tr>" for d in dirs
    ) or "<tr><td colspan='2' class='muted'>No directories watched.</td></tr>"

    proc_html = "".join(
        f"<tr><td>{p['pid']}</td><td>{_esc(p['name'])}</td>"
        f"<td>{p['cpu']:.1f}%</td><td>{p['mem_mb']:.1f} MB</td>"
        f"<td>{_esc(p['exe'])}</td></tr>"
        for p in procs
    ) or "<tr><td colspan='5' class='muted'>No process data.</td></tr>"

    count_cells = "".join(
        f"<td><span class='sev sev{int(sev)}'>{SEVERITIES[int(sev)]}</span>"
        f"&nbsp; {v['n']} total / {v['open']} open</td>"
        for sev, v in sorted(counts.items(), key=lambda kv: -int(kv[0]))
    )

    last_scan = si["modules"]["last_scan"]
    last_snap = si["modules"]["last_snapshot"]
    last_scan_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_scan)) if last_scan else "-"
    last_snap_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_snap)) if last_snap else "-"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{APP_NAME} Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0d1117; color:#e6edf3;
         margin:0; padding:24px; }}
  h1 {{ font-size:22px; margin:0; }} h2 {{ font-size:15px; color:#8b98ab; margin:18px 0 8px;
       text-transform:uppercase; letter-spacing:1px; }}
  .wrap {{ max-width:980px; margin:0 auto; }}
  .head {{ background:#161d2e; border:1px solid #2a3444; border-radius:12px; padding:18px; }}
  .pill {{ display:inline-block; background:#1f6feb; color:#fff; border-radius:999px;
          padding:2px 10px; font-size:11px; }}
  .grid {{ display:flex; flex-wrap:wrap; gap:12px; }}
  .box {{ background:#161d2e; border:1px solid #2a3444; border-radius:12px; padding:14px;
         flex:1 1 220px; }}
  .box b {{ display:block; font-size:11px; color:#8b98ab; text-transform:uppercase; }}
  .box .v {{ font-size:24px; font-weight:bold; }}
  table {{ width:100%; border-collapse:collapse; margin-top:6px; }}
  th {{ background:#1c2330; color:#8b98ab; text-align:left; padding:8px;
       font-size:11px; text-transform:uppercase; }}
  td {{ border-bottom:1px solid #1c2330; padding:7px 8px; font-size:12px; }}
  .sev {{ border-radius:4px; padding:1px 7px; font-size:11px; font-weight:bold; }}
  .sevInfo {{ background:rgba(88,166,255,.15); color:#58a6ff; }}
  .sevWarning {{ background:rgba(210,153,34,.15); color:#d29922; }}
  .sevCritical {{ background:rgba(248,81,73,.18); color:#f85149; }}
  .muted {{ color:#8b98ab; }}
  .foot {{ color:#8b98ab; font-size:11px; text-align:center; margin-top:22px; }}
</style></head><body><div class="wrap">
  <div class="head">
    <table style="border:none"><tr><td style="padding:0">
      <h1>{APP_NAME} &mdash; Security Report</h1>
      <div style="color:#8b98ab;font-size:12px">Generated {si['app']['generated']} on
      {_esc(si['host']['hostname'])} ({_esc(si['host']['os'])})</div>
    </td><td style="padding:0;text-align:right">
      <span class="pill">v{APP_VERSION}</span>
      <div style="margin-top:6px;color:#8b98ab;font-size:12px">
        FIM: {'ON' if si['modules']['fim_enabled'] else 'OFF'} &middot;
        Process: {'ON' if si['modules']['process_enabled'] else 'OFF'} &middot;
        {'PAUSED' if si['modules']['paused'] else 'RUNNING'}</div>
    </td></tr></table>
  </div>

  <h2>System Snapshot</h2>
  <div class="grid">
    <div class="box"><b>CPU</b><div class="v">{si['host']['cpu_usage']}%</div><div class="muted">{si['host']['cpu_count']} cores</div></div>
    <div class="box"><b>Memory</b><div class="v">{si['host']['mem_used_mb']} MB</div><div class="muted">of {si['host']['mem_total_mb']} MB used</div></div>
    <div class="box"><b>Files Monitored</b><div class="v">{si['stats']['files_monitored']}</div><div class="muted">{si['stats']['watch_dirs']} directories</div></div>
    <div class="box"><b>Processes</b><div class="v">{si['stats']['processes']}</div><div class="muted">in last snapshot</div></div>
    <div class="box"><b>Open Alerts</b><div class="v">{si['stats']['open_alerts']}</div><div class="muted">system uptime {uptime_fmt(si['host']['uptime_sec'])}</div></div>
  </div>

  <h2>Alert Summary</h2>
  <div class="grid" style="display:flex;gap:8px">
    {count_cells or '<div class="muted">No alerts yet.</div>'}
  </div>

  <h2>Watched Directories</h2>
  <table><tr><th>Path</th><th>Files in baseline</th></tr>{dirs_html}</table>

  <h2>Recent Security Events (last {alert_limit})</h2>
  <table><tr><th>Time</th><th>Severity</th><th>Source</th><th>Status</th><th>Title</th><th>Detail</th></tr>
  {rows_html}</table>

  <h2>Top Processes By Activity</h2>
  <table><tr><th>PID</th><th>Name</th><th>CPU</th><th>Memory</th><th>Executable</th></tr>
  {proc_html}</table>

  <div class="foot">Last FIM scan {last_scan_s} &middot; Last process snapshot {last_snap_s}
  &middot; {APP_NAME} v{APP_VERSION}</div>
</div></body></html>"""


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
def build_json(agent, alert_limit=500, proc_limit=20):
    si = system_info(agent)
    try:
        alerts = agent.storage.alerts(min_severity=1, limit=alert_limit)
    except Exception:
        alerts = []
    return {
        "app": si["app"],
        "host": si["host"],
        "modules": si["modules"],
        "stats": si["stats"],
        "watch_dirs": si["watch_dirs"],
        "alert_counts": si["alert_counts"],
        "alerts": alert_rows(alerts),
        "top_processes": top_processes(proc_limit),
    }


def build_json_str(agent):
    return json.dumps(build_json(agent), indent=2, default=str)


# ---------------------------------------------------------------------------
# TXT
# ---------------------------------------------------------------------------
def build_txt(agent, alert_limit=200):
    si = system_info(agent)
    try:
        alerts = agent.storage.alerts(min_severity=1, limit=alert_limit)
    except Exception:
        alerts = []
    rows = alert_rows(alerts)
    procs = top_processes(10)
    lines = []
    lines.append("=" * 66)
    lines.append(f"  {APP_NAME} v{APP_VERSION} - SECURITY REPORT")
    lines.append("=" * 66)
    lines.append(f"Generated : {si['app']['generated']}")
    lines.append(f"Host      : {si['host']['hostname']}  ({si['host']['os']})")
    lines.append(f"User      : {si['host']['user']}")
    lines.append(f"CPU       : {si['host']['cpu_usage']}% of {si['host']['cpu_count']} cores")
    lines.append(f"Memory    : {si['host']['mem_used_mb']} MB / {si['host']['mem_total_mb']} MB")
    lines.append("")
    lines.append("-" * 66)
    lines.append("MONITORING")
    lines.append("-" * 66)
    lines.append(f"FIM        : {'enabled' if si['modules']['fim_enabled'] else 'disabled'}"
                 f"  (interval {si['modules']['fim_interval_sec']}s,"
                 f" hash {si['modules']['hash_algorithm']})")
    lines.append(f"Process    : {'enabled' if si['modules']['process_enabled'] else 'disabled'}"
                 f"  (interval {si['modules']['process_interval_sec']}s)")
    lines.append(f"Status     : {'PAUSED' if si['modules']['paused'] else 'running'}")
    lines.append(f"Files      : {si['stats']['files_monitored']} across"
                 f" {si['stats']['watch_dirs']} dirs")
    lines.append(f"Processes  : {si['stats']['processes']}")
    lines.append("")
    lines.append("-" * 66)
    lines.append("ALERT SUMMARY")
    lines.append("-" * 66)
    counts = si["alert_counts"]
    for sev in ("3", "2", "1"):
        if sev in counts:
            v = counts[sev]
            lines.append(f"  {SEVERITIES[int(sev)]:<9} : {v['n']:>5} total"
                         f"  ({v['open']} open)")
    lines.append("")
    lines.append("-" * 66)
    lines.append(f"WATCHED DIRECTORIES")
    lines.append("-" * 66)
    for d in si["watch_dirs"]:
        lines.append(f"  {d['files']:<6} files  {d['path']}")
    lines.append("")
    lines.append("-" * 66)
    lines.append(f"RECENT EVENTS (last {len(rows)})")
    lines.append("-" * 66)
    for r in rows:
        lines.append(f"  [{r['time']}] {r['severity'].upper():>8} {r['source']:<7} "
                     f"{r['status']:<5} {r['title']} - {r['detail']}")
    lines.append("")
    if procs:
        lines.append("-" * 66)
        lines.append("TOP PROCESSES BY ACTIVITY")
        lines.append("-" * 66)
        for p in procs:
            lines.append(f"  {p['pid']:>6} {p['cpu']:>6.1f}% {p['mem_mb']:>8.1f} MB  "
                         f"{p['name']}  ({p['exe']})")
        lines.append("")
    lines.append("=" * 66)
    lines.append(f"Generated by {APP_NAME} v{APP_VERSION}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV (alert log)
# ---------------------------------------------------------------------------
def build_csv_rows(alerts_data):
    return [["time", "severity", "source", "status", "title", "detail"]] + alert_rows(
        [{"ts": r["ts"], "severity": r["severity"], "source": r["source"],
          "status": r["status"], "title": r["title"], "detail": r["detail"]}
         for r in alerts_data])


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")