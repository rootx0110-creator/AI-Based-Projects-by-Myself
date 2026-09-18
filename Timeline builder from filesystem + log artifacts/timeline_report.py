import html as html_mod
import json
from datetime import datetime

TYPE_COLORS = {
    "created": "#22c55e",
    "modified": "#3b82f6",
    "accessed": "#a855f7",
    "log": "#f59e0b",
}
TYPE_LABELS = {
    "created": "Created",
    "modified": "Modified",
    "accessed": "Accessed",
    "log": "Log line",
}


def _fmt_date(iso):
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso


def _bucket_key(ts, mode):
    if mode == "day":
        return ts.strftime("%Y-%m-%d"), "day"
    if mode == "week":
        monday = ts.date() - __import__("datetime").timedelta(days=ts.weekday())
        return monday.strftime("%Y-%m-%d"), "week"
    return ts.strftime("%Y-%m"), "month"


def _build_buckets(events, span_days):
    if span_days <= 120:
        mode = "day"
    elif span_days <= 1100:
        mode = "week"
    else:
        mode = "month"
    counts = {}
    for e in events:
        key, _ = _bucket_key(e.ts, mode)
        counts[key] = counts.get(key, 0) + 1
    items = sorted(counts.items())
    return mode, items


def build_html_report(events, stats, options=None):
    options = options or {}
    payload = {"events": [e.to_dict() for e in events], "stats": stats}
    data_json = json.dumps(payload, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")

    mode, buckets = _build_buckets(events, stats.get("span_days", 0.0))
    buckets_json = json.dumps([{"label": l, "count": c} for l, c in buckets],
                              ensure_ascii=False)
    counts = stats.get("counts", {})
    type_rows = "".join(
        '<span class="legend-item"><i style="background:{c}"></i>{n} &middot; '
        '<b>{v}</b></span>'.format(
            c=TYPE_COLORS[t], n=TYPE_LABELS.get(t, t), v=counts.get(t, 0)
        )
        for t in ("created", "modified", "accessed", "log")
    )

    root = html_mod.escape(stats.get("root") or "")
    first = html_mod.escape(_fmt_date(stats.get("first")))
    last = html_mod.escape(_fmt_date(stats.get("last")))
    scanned = html_mod.escape(stats.get("scan_time") or "")
    total = stats.get("total", len(events))
    files = stats.get("files", 0)
    dirs = stats.get("dirs", 0)
    logfiles = stats.get("log_files", 0)
    loglines = stats.get("log_lines", 0)
    errors = stats.get("errors", 0)
    span = stats.get("span_days", 0.0)
    if span and span < 1:
        hours = round(span * 24)
        span_txt = "{} hour{}".format(hours, "s" if hours != 1 else "")
    else:
        span_txt = "{} day{}".format(int(span), "s" if int(span) != 1 else "")

    title = html_mod.escape(options.get("title") or "Timeline Report")

    page = _TEMPLATE
    page = page.replace("__TITLE__", title)
    page = page.replace("__ROOT__", root)
    page = page.replace("__SCANNED__", scanned)
    page = page.replace("__FIRST__", first)
    page = page.replace("__LAST__", last)
    page = page.replace("__SPAN__", span_txt)
    page = page.replace("__TOTAL__", str(total))
    page = page.replace("__FILES__", str(files))
    page = page.replace("__DIRS__", str(dirs))
    page = page.replace("__LOGFILES__", str(logfiles))
    page = page.replace("__LOGLINES__", str(loglines))
    page = page.replace("__ERRORS__", str(errors))
    page = page.replace("__TYPE_ROWS__", type_rows)
    page = page.replace("__BUCKETS__", buckets_json)
    page = page.replace("__BUCKET_MODE__", mode)
    page = page.replace("__DATA__", data_json)
    colors_json = json.dumps(TYPE_COLORS)
    page = page.replace("__COLORS__", colors_json)
    return page


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --bg:#f6f7fb; --card:#ffffff; --ink:#1f2430; --muted:#6b7280;
    --line:#e5e7eb; --accent:#4f46e5; --accent2:#6d28d9; --chip:#eef2ff;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       background:var(--bg);color:var(--ink);font-size:14px}
  header{position:sticky;top:0;z-index:10;background:linear-gradient(120deg,#312e81,#4f46e5 55%,#7c3aed);
         color:#fff;padding:22px 28px;box-shadow:0 2px 12px rgba(49,46,129,.25)}
  header .kicker{font-size:11px;letter-spacing:.18em;text-transform:uppercase;opacity:.85}
  header h1{margin:4px 0 6px;font-size:22px;font-weight:700}
  header .meta{font-size:12.5px;opacity:.92}
  header .root{font-family:ui-monospace,Consolas,Monaco,monospace;font-size:11.5px;opacity:.85;
               word-break:break-all}
  .tools{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
  header button{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);
                color:#fff;padding:8px 16px;border-radius:9px;cursor:pointer;font-size:13px;
                font-weight:600}
  header button:hover{background:rgba(255,255,255,.24)}
  main{max-width:1180px;margin:22px auto 60px;padding:0 20px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;
        box-shadow:0 1px 3px rgba(16,24,40,.05)}
  .metric .num{font-size:24px;font-weight:700;color:var(--accent)}
  .metric .lbl{font-size:12px;color:var(--muted);margin-top:2px}
  .panel{margin-top:16px;padding:18px}
  .panel h2{margin:0 0 14px;font-size:15px;color:#312e81;letter-spacing:.02em}
  .legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--muted);margin-bottom:14px}
  .legend-item i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
  .legend-item b{color:var(--ink)}
  .chart{display:flex;align-items:flex-end;gap:3px;height:150px;padding-top:6px;overflow-x:auto}
  .bar{flex:1 0 8px;min-width:3px;background:linear-gradient(180deg,var(--accent2),var(--accent));
       border-radius:3px 3px 0 0;position:relative;cursor:pointer}
  .bar:hover{filter:brightness(1.15)}
  .bar:hover::after{content:attr(data-tip);position:absolute;bottom:calc(100% + 6px);left:50%;
       transform:translateX(-50%);background:#111827;color:#fff;padding:4px 8px;border-radius:6px;
       font-size:11px;white-space:nowrap;z-index:5}
  .bar-empty{flex:1 0 8px;min-width:3px;border-radius:3px;border-bottom:2px solid var(--line)}
  .chart-x{margin-top:8px;font-size:11px;color:var(--muted);display:flex;justify-content:space-between}
  .filters{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0 12px}
  .filters input[type=search],.filters select{border:1px solid var(--line);border-radius:9px;
       padding:8px 10px;font-size:13px;background:#fff;color:var(--ink)}
  .filters input[type=search]{flex:1 1 220px;min-width:200px}
  .chk{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--ink);
       background:var(--chip);border-radius:999px;padding:6px 12px;cursor:pointer;user-select:none}
  .chk input{accent-color:var(--accent);margin:0}
  .result-note{font-size:12.5px;color:var(--muted);margin-left:auto}
  table{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border:1px solid var(--line);
        border-radius:12px;overflow:hidden}
  thead th{position:sticky;top:0;background:#eef0f8;text-align:left;padding:10px 12px;font-size:12px;
        font-weight:700;color:#374151;cursor:pointer;white-space:nowrap;border-bottom:1px solid var(--line)}
  thead th:hover{color:var(--accent)}
  thead th .sort{opacity:.45;font-size:11px}
  tbody td{padding:9px 12px;border-bottom:1px solid #f1f3f8;vertical-align:top}
  tbody tr{cursor:pointer}
  tbody tr:hover{background:#f5f6fe}
  tbody tr.sel{background:#eef2ff}
  td.mono,code{font-family:ui-monospace,Consolas,Monaco,monospace;font-size:12px}
  .badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;
        color:#fff}
  .tiny{font-size:12px}
  .muted{color:var(--muted)}
  .ellip{max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pager{display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-top:12px}
  .pager button{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 12px;
        cursor:pointer;font-size:12.5px}
  .pager button:disabled{opacity:.4;cursor:default}
  .pager span{font-size:12.5px;color:var(--muted)}
  #details{display:none;margin:0 0 14px;padding:14px 18px;background:var(--card);border:1px solid var(--line);
        border-radius:12px}
  #details h3{margin:0 0 8px;font-size:13.5px;color:#312e81}
  #details .row{display:flex;gap:8px;margin:4px 0;font-size:13px}
  #details .k{min-width:110px;color:var(--muted);font-weight:600}
  #details .v{word-break:break-all}
  .empty{text-align:center;color:var(--muted);padding:40px 0;font-size:14px}
  footer{text-align:center;color:var(--muted);font-size:12px;padding:18px 0 30px}
  @media print{
    header{position:static;box-shadow:none}
    #printBtn,.filters,.pager,.bar:hover::after,.bar::after{display:none}
    table{box-shadow:none}
    body{background:#fff}
  }
</style>
</head>
<body>
<header>
  <div class="kicker">Timeline Builder &middot; __SCANNED__</div>
  <h1>__TITLE__</h1>
  <div class="meta">Root: <span class="root">__ROOT__</span></div>
  <div class="tools">
    <button onclick="window.print()" id="printBtn">Print</button>
  </div>
</header>
<main>
  <div class="grid">
    <div class="card metric"><div class="num">__TOTAL__</div><div class="lbl">Total events</div></div>
    <div class="card metric"><div class="num">__FILES__</div><div class="lbl">Files</div></div>
    <div class="card metric"><div class="num">__DIRS__</div><div class="lbl">Folders</div></div>
    <div class="card metric"><div class="num">__LOGFILES__</div><div class="lbl">Log files</div></div>
    <div class="card metric"><div class="num">__LOGLINES__</div><div class="lbl">Log lines</div></div>
    <div class="card metric"><div class="num">__SPAN__</div><div class="lbl">Time span</div></div>
  </div>

  <div class="grid" style="margin-top:12px">
    <div class="card metric"><div class="num" style="font-size:15px">__FIRST__</div><div class="lbl">Earliest event</div></div>
    <div class="card metric"><div class="num" style="font-size:15px">__LAST__</div><div class="lbl">Latest event</div></div>
    <div class="card metric"><div class="num" style="font-size:15px">__ERRORS__</div><div class="lbl">Scan errors</div></div>
  </div>

  <section class="card panel">
    <h2>Event frequency (per __BUCKET_MODE__)</h2>
    <div class="chart" id="chart"></div>
    <div class="chart-x" id="chartX"></div>
  </section>

  <section class="card panel">
    <h2>Timeline</h2>
    <div class="legend">__TYPE_ROWS__</div>
    <div class="filters">
      <input type="search" id="q" placeholder="Search paths, sources, details&#8230;">
      <span class="chk"><input type="checkbox" id="t0" data-t="created" checked>Created</span>
      <span class="chk"><input type="checkbox" id="t1" data-t="modified" checked>Modified</span>
      <span class="chk"><input type="checkbox" id="t2" data-t="accessed" checked>Accessed</span>
      <span class="chk"><input type="checkbox" id="t3" data-t="log" checked>Log</span>
      <select id="pp">
        <option value="50">50 / page</option>
        <option value="100">100 / page</option>
        <option value="250">250 / page</option>
        <option value="0">All</option>
      </select>
      <span class="result-note" id="note"></span>
    </div>
    <div id="details"></div>
    <div style="max-height:560px;overflow:auto;border-radius:12px">
      <table id="tbl">
        <thead><tr>
          <th data-k="ts">Time <span class="sort">&#9660;</span></th>
          <th data-k="type">Type</th>
          <th data-k="source">Source</th>
          <th data-k="path">Path</th>
          <th data-k="details">Details</th>
          <th data-k="size" style="text-align:right">Size</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="pager">
      <button id="firstP" onclick="goto(0)">&#171;</button>
      <button id="prevP" onclick="goto(state.page-1)">&#8249; Prev</button>
      <span id="pageInfo"></span>
      <button id="nextP" onclick="goto(state.page+1)">Next &#8250;</button>
      <button id="lastP" onclick="goto(999999)">&#187;</button>
    </div>
  </section>
</main>
<footer>Generated by Timeline Builder</footer>

<script>
var DATA = __DATA__;
var COLORS = __COLORS__;
var state = {q:"", types:{"created":true,"modified":true,"accessed":true,"log":true},
             sortK:"ts", sortD:1, page:0, pp:50};

function fmtSize(n){ if(n==null) return "-"; if(n<1024) return n+" B";
  if(n<1048576) return (n/1024).toFixed(1)+" KB";
  if(n<1073741824) return (n/1048576).toFixed(1)+" MB"; return (n/1073741824).toFixed(2)+" GB"; }
function fmtTs(iso){ var d=new Date(iso); return isNaN(d)?iso:
  d.getFullYear()+"-"+("0"+(d.getMonth()+1)).slice(-2)+"-"+("0"+d.getDate()).slice(-2)+" "+
  ("0"+d.getHours()).slice(-2)+":"+("0"+d.getMinutes()).slice(-2)+":"+("0"+d.getSeconds()).slice(-2); }

function drawChart(){
  var el=document.getElementById("chart");
  var max=1; var bs=__BUCKETS__;
  bs.forEach(function(b){ if(b.count>max) max=b.count; });
  if(!bs.length){ el.innerHTML='<div class="empty">No events to chart</div>'; return; }
  var html=""; var step=Math.ceil(bs.length/48);
  bs.forEach(function(b,i){
    var h=Math.max(4, Math.round(140*b.count/max));
    html+='<div class="'+ (b.count? "bar":"bar-empty") +'" style="height:'+h+'px"'+
      ' data-tip="'+b.label+' &middot; '+b.count+' events"></div>';
  });
  el.innerHTML=html;
  var x=document.getElementById("chartX");
  if(bs.length){ x.innerHTML='<span>'+bs[0].label+'</span><span>'+bs[bs.length-1].label+'</span>'; }
}
function drawLegend(){
  var note=document.getElementById("note");
  note.textContent="";
}
function applyTypes(){
  ["created","modified","accessed","log"].forEach(function(t){
    var c=document.querySelector('input[data-t="'+t+'"]');
    state.types[t]=c.checked;
  });
}
function filtered(){
  var q=state.q.toLowerCase();
  return DATA.events.filter(function(e){
    if(!state.types[e.type]) return false;
    if(!q) return true;
    return (e.label+" "+e.path+" "+e.details+" "+e.source).toLowerCase().indexOf(q)>=0;
  });
}
function render(){
  applyTypes();
  var rows=filtered();
  var sortK=state.sortK, dir=state.sortD;
  rows.sort(function(a,b){
    var va=a[sortK], vb=b[sortK];
    if(sortK==="ms") return (a.ms-b.ms)*dir;
    if(sortK==="size"){ va=va==null?-1:va; vb=vb==null?-1:vb; return (va-vb)*dir; }
    va=(va==null?"":String(va)); vb=(vb==null?"":String(vb));
    return va.localeCompare(vb)*dir;
  });
  var pp=parseInt(document.getElementById("pp").value,10)||0;
  state.pp=pp;
  var total=rows.length;
  var pages= pp? Math.max(1,Math.ceil(total/pp)) : 1;
  if(state.page>=pages) state.page=pages-1;
  if(state.page<0) state.page=0;
  var slice= pp? rows.slice(state.page*pp, state.page*pp+pp) : rows;
  var tbody=document.querySelector("#tbl tbody");
  var html="";
  slice.forEach(function(e){
    html+='<tr data-i="'+e.ms+'" onclick="show(this)">'+
      '<td class="tiny mono">'+fmtTs(e.ts)+'</td>'+
      '<td><span class="badge" style="background:'+ (COLORS[e.type]||"#999") +'">'+
         (e.type.charAt(0).toUpperCase()+e.type.slice(1))+'</span></td>'+
      '<td class="tiny">'+esc(e.source)+'</td>'+
      '<td class="tiny mono"><div class="ellip" title="'+esc(e.path)+'">'+esc(e.path)+'</div></td>'+
      '<td class="tiny"><div class="ellip" title="'+esc(e.details)+'">'+esc(e.details)+'</div></td>'+
      '<td class="tiny mono" style="text-align:right">'+fmtSize(e.size)+'</td></tr>';
  });
  tbody.innerHTML= html || '<tr><td colspan="6"><div class="empty">No matching events.</div></td></tr>';
  document.getElementById("note").textContent= total+" of "+DATA.events.length+" events";
  document.getElementById("pageInfo").textContent=
    pp? "Page "+(state.page+1)+" of "+pages+" ("+slice.length+" shown)" : "All \u00b7 "+slice.length+" shown";
  document.getElementById("prevP").disabled= state.page<=0;
  document.getElementById("nextP").disabled= state.page>=pages-1;
  document.getElementById("firstP").disabled= state.page<=0;
  document.getElementById("lastP").disabled= state.page>=pages-1;
  document.querySelectorAll("#tbl thead th").forEach(function(th){
    th.querySelector(".sort").innerHTML= (th.dataset.k===sortK)? (dir<0?"\u25b2":"\u25bc") : "";
  });
}
function esc(s){ s=(s==null?"":String(s)); var d=document.createElement("div"); d.textContent=s; return d.innerHTML; }
function show(tr){
  var ms=parseInt(tr.dataset.i,10);
  var e=filtered().filter(function(x){return x.ms===ms;})[0];
  if(!e) return;
  var box=document.getElementById("details");
  box.style.display="block";
  box.innerHTML='<h3>Event detail</h3>'+[
    ["Time", fmtTs(e.ts)],
    ["Type", e.type],
    ["Source", e.source],
    ["Path", e.path],
    ["Details", e.details],
    ["Size", fmtSize(e.size)]
  ].map(function(r){ return '<div class="row"><span class="k">'+r[0]+'</span>'+
     '<span class="v">'+esc(r[1])+'</span></div>'; }).join("");
  document.querySelectorAll("#tbl tbody tr").forEach(function(r){r.classList.remove("sel");});
  tr.classList.add("sel");
}
function goto(p){ state.page=p; render(); window.scrollTo(0, document.getElementById("details").offsetTop); }
document.getElementById("q").addEventListener("input", function(e){ state.q=e.target.value; state.page=0; render(); });
document.getElementById("pp").addEventListener("change", function(){ state.page=0; render(); });
document.querySelectorAll('input[data-t]').forEach(function(c){
  c.addEventListener("change", function(){ state.page=0; render(); });
});
document.querySelectorAll("#tbl thead th").forEach(function(th){
  th.addEventListener("click", function(){
    var k=th.dataset.k;
    if(!k) return;
    if(state.sortK===k){ state.sortD*=-1; } else { state.sortK=k; state.sortD=1; }
    state.page=0; render();
  });
});
drawChart(); render();
</script>
</body>
</html>
"""