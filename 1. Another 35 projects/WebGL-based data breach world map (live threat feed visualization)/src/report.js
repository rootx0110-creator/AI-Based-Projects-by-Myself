import { SEVERITIES } from './datafeed.js';

export function buildReportHTML(todayEvents, allEvents) {
  const generated = new Date().toISOString();
  const total = todayEvents.length;
  const records = todayEvents.reduce((s, e) => s + e.records, 0);
  const countries = new Map();
  const types = new Map();
  const sevCount = { critical: 0, high: 0, medium: 0, low: 0 };
  const hourly = new Array(24).fill(0);

  for (const e of todayEvents) {
    countries.set(e.dst.cc, (countries.get(e.dst.cc) || 0) + 1);
    types.set(e.attack, (types.get(e.attack) || 0) + 1);
    sevCount[e.severity]++;
    const h = new Date(e.ts).getHours();
    hourly[h]++;
  }

  const topCountries = [...countries.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  const topTypes = [...types.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxCountry = Math.max(1, ...topCountries.map(([, n]) => n));
  const maxHour = Math.max(1, ...hourly);

  const active = todayEvents.filter(e => e.severity === 'critical').length;

  const table = allEvents.slice(-300).reverse().map(e => `
    <tr>
      <td class="sev s-${e.severity}">${SEVERITIES[e.severity].label}</td>
      <td>${e.attack}</td>
      <td>${escapeHtml(e.src.city)} <small>(${e.src.cc})</small></td>
      <td>${escapeHtml(e.dst.city)} <small>(${e.dst.cc})</small></td>
      <td>${escapeHtml(e.company)}</td>
      <td class="num">${e.records.toLocaleString()}</td>
      <td>${escapeHtml(e.ip)}</td>
      <td>${new Date(e.ts).toLocaleString()}</td>
    </tr>`).join('');

  const bars = topCountries.map(([cc, n]) => `
    <div class="row"><span class="rk">${cc}</span>
      <div class="bar"><i style="width:${(n / maxCountry) * 100}%"></i></div>
      <span class="rv">${n}</span>
    </div>`).join('');

  const typeBar = topTypes.map(([t, n]) => `
    <div class="row"><span class="rk">${escapeHtml(t)}</span>
      <div class="bar t"><i style="width:${(n / Math.max(1, topTypes[0][1])) * 100}%"></i></div>
      <span class="rv">${n}</span>
    </div>`).join('');

  const wave = hourly.map((n, i) => {
    const x = (i / 23) * 1000;
    const y = 180 - (n / maxHour) * 160;
    return `${x},${y}`;
  }).join(' ');

  const sevRows = Object.entries(SEVERITIES).map(([k, v]) => `
    <span class="lg" style="--c:${v.color}">${v.label}<b>${sevCount[k]}</b></span>`).join('');

  const now = new Date().toLocaleString();

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>BreachMap Threat Report</title>
<style>
  :root { --cyan:#22d3ee; --violet:#7c3aed; --magenta:#e158ff; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    color: #dbeafe;
    min-height: 100vh;
    background: #04060f;
    overflow-x: hidden;
  }
  /* ---- animated 3D background ---- */
  .bg { position: fixed; inset: 0; z-index: -2; overflow: hidden;
    background: linear-gradient(120deg, #04060f, #07122b, #14082b, #04060f);
    background-size: 400% 400%;
    animation: g 22s ease infinite; }
  @keyframes g { 0%{background-position:0% 0%} 50%{background-position:100% 100%} 100%{background-position:0% 0%} }
  .bg::before { content:""; position:absolute; inset:-10%;
    background:
      radial-gradient(600px 600px at 20% 20%, rgba(34,211,238,.20), transparent 60%),
      radial-gradient(700px 700px at 80% 30%, rgba(124,58,237,.28), transparent 60%),
      radial-gradient(650px 650px at 50% 90%, rgba(225,88,255,.20), transparent 60%);
    animation: b 14s ease-in-out infinite; }
  @keyframes b { 0%,100%{transform:translate3d(-2%,-1%,0) rotate(0deg) scale(1)} 50%{transform:translate3d(2%,1%,0) rotate(4deg) scale(1.08)} }
  .grid { position: fixed; left:-40%; right:-40%; bottom:-30%; height:70%; z-index:-1;
    background-image: linear-gradient(rgba(34,211,238,.12) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(34,211,238,.12) 1px, transparent 1px);
    background-size: 60px 60px;
    transform: perspective(800px) rotateX(62deg);
    -webkit-mask-image: radial-gradient(closest-side at 50% 0%, rgba(0,0,0,.85), transparent 78%);
    mask-image: radial-gradient(closest-side at 50% 0%, rgba(0,0,0,.85), transparent 78%);
    animation: gl 9s ease-in-out infinite; }
  @keyframes gl { 0%,100%{opacity:.5} 50%{opacity:1} }
  .stars { position: fixed; inset: 0; z-index:-1; pointer-events:none;
    background-image:
      radial-gradient(1.4px 1.4px at 22% 32%, #fff, transparent),
      radial-gradient(1.1px 1.1px at 71% 18%, #bfe0ff, transparent),
      radial-gradient(1.6px 1.6px at 45% 71%, #d0dcff, transparent),
      radial-gradient(1px 1px at 84% 56%, #fff, transparent),
      radial-gradient(1.4px 1.4px at 12% 84%, #c3d6ff, transparent);
    background-size: 1100px 900px;
    animation: sd 120s linear infinite; }
  @keyframes sd { to { background-position: -1100px 140px; } }

  .wrap { max-width: 1080px; margin: 0 auto; padding: 40px 28px 80px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;
    margin-bottom: 30px; padding-bottom: 18px; border-bottom: 1px solid rgba(34,211,238,.2); }
  h1 { font-size: 2rem; background: linear-gradient(90deg, var(--cyan), var(--violet), var(--magenta));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    letter-spacing: 1px; }
  .sub { color:#8fa3c8; font-size:.85rem; margin-top:6px; }
  .gen { text-align:right; font-size:.75rem; color:#6482a8; }
  .stats { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:14px; margin-bottom:26px; }
  .stat { border:1px solid rgba(34,211,238,.18); border-radius:14px; padding:16px 18px;
    background: rgba(8,14,32,.6); backdrop-filter: blur(6px); }
  .stat b { font-size:1.5rem; font-variant-numeric: tabular-nums; display:block; margin-top:4px; }
  .stat span { font-size:.68rem; text-transform:uppercase; letter-spacing:1.5px; color:#8fa3c8; }
  .stat.b-crit b { color:#ff3860; } .stat.b-events b { color:var(--cyan); }
  .stat.b-high b { color:#ff9f1a; } .stat.b-rec b { color:#ffd166; }
  .card { border:1px solid rgba(34,211,238,.16); border-radius:16px; padding:20px;
    background: rgba(8,14,32,.55); backdrop-filter: blur(6px); margin-bottom:22px;
    box-shadow: 0 20px 50px rgba(0,0,0,.35); }
  .card h2 { font-size:.85rem; letter-spacing:2px; text-transform:uppercase; color:var(--cyan); margin-bottom:16px; }
  .sevline { display:flex; gap:18px; flex-wrap:wrap; }
  .lg { display:inline-flex; gap:8px; align-items:center; font-size:.8rem; color:#c3d6ff; }
  .lg i { width:10px; height:10px; border-radius:50%; background: var(--c); box-shadow:0 0 10px var(--c); }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  @media (max-width:760px){ .grid2{grid-template-columns:1fr} }
  .row { display:flex; align-items:center; gap:10px; margin-bottom:8px; font-size:.8rem; }
  .rk { width:70px; color:#9fb6e0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .bar { flex:1; height:12px; border-radius:6px; background: rgba(255,255,255,.06); overflow:hidden; }
  .bar i { display:block; height:100%; border-radius:6px;
    background: linear-gradient(90deg, var(--cyan), var(--violet)); box-shadow: 0 0 12px rgba(34,211,238,.5); }
  .bar.t i { background: linear-gradient(90deg, var(--violet), var(--magenta)); box-shadow: 0 0 12px rgba(225,88,255,.5); }
  .rv { width:36px; text-align:right; color:#dbeafe; font-variant-numeric:tabular-nums; }
  svg { width:100%; height:auto; display:block; }
  .table-scroll { overflow-x:auto; border-radius:10px; }
  table { width:100%; border-collapse:collapse; font-size:.78rem; }
  th { text-align:left; padding:9px 10px; color:#8fa3c8; text-transform:uppercase; letter-spacing:1px;
    border-bottom:1px solid rgba(34,211,238,.2); background: rgba(10,16,36,.8); white-space:nowrap; }
  td { padding:8px 10px; border-bottom:1px solid rgba(255,255,255,.05); white-space:nowrap; }
  tr:hover td { background: rgba(34,211,238,.05); }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .sev { font-weight:700; }
  .s-critical{color:#ff3860} .s-high{color:#ff9f1a} .s-medium{color:#ffd166} .s-low{color:#06d6a0}
  footer { margin-top:30px; text-align:center; font-size:.72rem; color:#6482a8; }
  .note { font-size:.72rem; color:#8fa3c8; margin-top:8px; }
</style>
</head>
<body>
  <div class="bg"></div>
  <div class="grid"></div>
  <div class="stars"></div>
  <div class="wrap">
    <header>
      <div>
        <h1>BreachMap &mdash; Threat Report</h1>
        <div class="sub">WebGL world map live threat feed visualization &middot; autonomous summary</div>
      </div>
      <div class="gen">
        Generated: ${now}<br />UTC: ${new Date().toISOString()}<br />Snapshot of the last 24 hours
      </div>
    </header>

    <div class="stats">
      <div class="stat b-events"><span>Events (24h)</span><b>${total.toLocaleString()}</b></div>
      <div class="stat b-crit"><span>Critical Incidents</span><b>${active}</b></div>
      <div class="stat b-high"><span>Countries Hit</span><b>${countries.size}</b></div>
      <div class="stat b-rec"><span>Records Exposed</span><b>${records.toLocaleString()}</b></div>
    </div>

    <div class="card">
      <h2>Severity Breakdown</h2>
      <div class="sevline">${sevRows}</div>
    </div>

    <div class="grid2">
      <div class="card">
        <h2>Top Attack Targets (by country)</h2>
        ${topCountries.length ? bars : '<div class="note">No activity recorded in this window.</div>'}
      </div>
      <div class="card">
        <h2>Attack Vectors</h2>
        ${topTypes.length ? typeBar : '<div class="note">No activity recorded in this window.</div>'}
      </div>
    </div>

    <div class="card">
      <h2>24-Hour Activity Timeline</h2>
      <svg viewBox="0 0 1000 210" preserveAspectRatio="none">
        <defs>
          <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.55"/>
            <stop offset="100%" stop-color="#7c3aed" stop-opacity="0.02"/>
          </linearGradient>
          <linearGradient id="stroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#22d3ee"/>
            <stop offset="100%" stop-color="#e158ff"/>
          </linearGradient>
        </defs>
        <polygon points="0,200 ${wave} 1000,200" fill="url(#fill)"/>
        <polyline points="${wave}" fill="none" stroke="url(#stroke)" stroke-width="3" stroke-linecap="round"/>
        <line x1="0" y1="200" x2="1000" y2="200" stroke="rgba(34,211,238,.25)" stroke-width="1" stroke-dasharray="4 6"/>
      </svg>
      <div class="note">Local-time hour buckets &middot; peak ${maxHour} events/hour</div>
    </div>

    <div class="card">
      <h2>Event Log (${allEvents.length} recorded)</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr><th>Severity</th><th>Attack</th><th>Source</th><th>Target</th><th>Company</th><th>Records</th><th>IP</th><th>Time</th></tr>
          </thead>
          <tbody>${table || '<tr><td colspan="8">No events.</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <footer>BreachMap v1.0 &middot; simulated live threat feed for demonstration &middot; generated ${generated}</footer>
  </div>
</body>
</html>`;
}

export function buildJSONLog(events) {
  return JSON.stringify({ generated: new Date().toISOString(), app: 'BreachMap', events: events.slice(-600) }, null, 2);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}