'use strict';

const { escapeHtml } = require('./markdown');

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

function inRange(iso, from, to) {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  if (from && t < from.getTime()) return false;
  if (to && t > to.getTime()) return false;
  return true;
}

function buildReport(state, opts) {
  opts = opts || {};
  const from = opts.from ? new Date(opts.from) : null;
  const to = opts.to ? new Date(opts.to) : from ? null : null;

  const incidents = state.incidents.filter((inc) => {
    if (!inRange(inc.createdAt, from, to)) return false;
    if (opts.severity && inc.severity !== opts.severity) return false;
    if (opts.category && inc.category !== opts.category) return false;
    if (opts.status && inc.status !== opts.status) return false;
    return true;
  });

  const runs = state.runs.filter((run) => {
    const t = run.startedAt || run.finishedAt;
    if (!inRange(t, from, to)) return false;
    if (opts.playbookId && run.playbookId !== opts.playbookId) return false;
    return true;
  });

  const activity = state.activity.filter((a) => inRange(a.ts, from, to));

  const resolved = incidents.filter((i) => i.status === 'resolved' || i.status === 'closed').length;
  const sevCount = (s) => incidents.filter((i) => i.severity === s).length;
  const runStatus = (s) => runs.filter((r) => r.status === s).length;

  const byCategory = {};
  incidents.forEach((inc) => {
    byCategory[inc.category] = byCategory[inc.category] || { critical: 0, high: 0, medium: 0, low: 0, info: 0, total: 0 };
    byCategory[inc.category][inc.severity] = (byCategory[inc.category][inc.severity] || 0) + 1;
    byCategory[inc.category].total++;
  });

  const summary = {
    window: { from: from ? from.toISOString() : null, to: to ? to.toISOString() : null },
    totalIncidents: incidents.length,
    critical: sevCount('critical'), high: sevCount('high'), medium: sevCount('medium'), low: sevCount('low'),
    resolved, open: incidents.length - resolved,
    resolvedRate: incidents.length ? Math.round((resolved / incidents.length) * 100) : 0,
    totalRuns: runs.length,
    runsSuccess: runStatus('success'), runsFailed: runStatus('failed'),
    runsRunning: runStatus('running') + runStatus('queued'),
    successRate: runs.length ? Math.round((runStatus('success') / runs.length) * 100) : 0,
    autoRuns: runs.filter((r) => r.trigger === 'auto').length,
    manualRuns: runs.filter((r) => r.trigger === 'manual').length,
    playbooksActive: state.playbooks.filter((p) => p.active).length,
    totalPlaybooks: state.playbooks.length
  };

  return { meta: { appName: 'SOAR-Lite', appVersion: '1.0.0', generatedAt: new Date().toISOString() }, filters: opts, summary, incidents, runs, activity, byCategory };
}

// --------------------------------------------------------------------------- HTML
function renderHtml(report, filters) {
  const s = report.summary;
  const card = (label, value, sub, accent) => `<div class="card ${accent || ''}"><div class="card-val">${value}</div><div class="card-label">${label}</div>${sub ? `<div class="card-sub">${sub}</div>` : ''}</div>`;

  const sevBar = report.byCategory;
  const sevTable = Object.entries(sevBar).length
    ? `<h2>Severity by Category</h2>
       <div class="table-wrap"><table>
       <thead><tr><th>Category</th>${SEVERITY_ORDER.map((se) => `<th>${se.charAt(0).toUpperCase() + se.slice(1)}</th>`).join('')}<th>Total</th></tr></thead>
       <tbody>${Object.entries(sevBar).map(([cat, v]) => `<tr><td>${escapeHtml(cat)}</td>${SEVERITY_ORDER.map((se) => `<td>${v[se] || 0}</td>`).join('')}<td><strong>${v.total}</strong></td></tr>`).join('')}</tbody>
       </table></div>`
    : '';

  const incRows = report.incidents.length
    ? `<h2>Incidents (${report.incidents.length})</h2>
       <div class="table-wrap"><table>
       <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Severity</th><th>Status</th><th>Created</th></tr></thead>
       <tbody>${report.incidents.map((i) => `<tr><td>${escapeHtml(i.id)}</td><td>${escapeHtml(i.title)}</td><td>${escapeHtml(i.category)}</td><td><span class="sev sev-${i.severity}">${i.severity}</span></td><td><span class="st">${i.status}</span></td><td>${escapeHtml(new Date(i.createdAt).toLocaleString())}</td></tr>`).join('')}</tbody>
       </table></div>`
    : '<h2>Incidents</h2><p class="none">No incidents match the selected criteria.</p>';

  const runRows = report.runs.length
    ? `<h2>Playbook Executions (${report.runs.length})</h2>
       <div class="table-wrap"><table>
       <thead><tr><th>Run ID</th><th>Playbook</th><th>Incident</th><th>Trigger</th><th>Status</th><th>Steps</th><th>Started</th></tr></thead>
       <tbody>${report.runs.map((r) => `<tr><td>${escapeHtml(r.id)}</td><td>${escapeHtml(r.playbookName)}</td><td>${escapeHtml(r.incidentTitle || '—')}</td><td>${r.trigger}</td><td><span class="st st-${r.status}">${r.status}</span></td><td>${r.steps.length}</td><td>${escapeHtml(r.startedAt ? new Date(r.startedAt).toLocaleString() : '—')}</td></tr>`).join('')}</tbody>
       </table></div>
       <details class="run-detail"><summary>Show step-level detail</summary>
       ${report.runs.map((r) => `<div class="run-block"><h3>${escapeHtml(r.id)} — ${escapeHtml(r.playbookName)} <span class="st st-${r.status}">${r.status}</span></h3>
       <div class="table-wrap"><table><thead><tr><th>#</th><th>Step</th><th>Type</th><th>Status</th><th>Duration</th><th>Output</th></tr></thead>
       <tbody>${r.steps.map((st, i) => `<tr><td>${i + 1}</td><td>${escapeHtml(st.name)}</td><td>${escapeHtml(st.type)}</td><td><span class="st st-${st.status}">${st.status}</span></td><td>${st.duration ? st.duration + 'ms' : '—'}</td><td>${escapeHtml(describeStep(st))}</td></tr>`).join('')}</tbody></table></div></div>`).join('')}
       </details>`
    : '<h2>Playbook Executions</h2><p class="none">No executions match the selected criteria.</p>';

  const actRows = report.activity.length
    ? `<h2>Activity Feed (${report.activity.length})</h2><ul class="act">${report.activity.slice(0, 30).map((a) => `<li><span class="act-ts">${escapeHtml(new Date(a.ts).toLocaleString())}</span> <strong>[${escapeHtml(a.type)}]</strong> ${escapeHtml(a.title)} — ${escapeHtml(a.detail)}</li>`).join('')}</ul>`
    : '<h2>Activity Feed</h2><p class="none">No activity in range.</p>';

  const f = report.filters || {};
  const filterLine = [
    f.from ? `From: ${new Date(f.from).toLocaleString()}` : '',
    f.to ? `To: ${new Date(f.to).toLocaleString()}` : '',
    f.severity ? `Severity: ${f.severity}` : '',
    f.category ? `Category: ${f.category}` : '',
    f.status ? `Status: ${f.status}` : '',
    f.playbookId ? `Playbook: ${f.playbookId}` : ''
  ].filter(Boolean).join('  ·  ') || 'All data';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SOAR-Lite Incident Response Report — ${escapeHtml(report.meta.generatedAt)}</title>
<style>
  :root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--accent:#0e7490;--red:#dc2626;--amber:#d97706;--green:#16a34a;--blue:#2563eb}
  *{box-sizing:border-box} body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--ink);background:var(--bg);padding:40px}
  .wrap{max-width:1000px;margin:0 auto}
  header.rpt{border-bottom:3px solid var(--accent);padding-bottom:16px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:flex-end}
  header.rpt h1{margin:0;font-size:24px} header.rpt .meta{color:var(--muted);font-size:12px;text-align:right}
  .filters{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:13px;color:var(--muted);margin-bottom:24px}
  h2{font-size:16px;margin:26px 0 10px;color:var(--accent)}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:8px}
  .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(15,23,42,.05)}
  .card-val{font-size:26px;font-weight:700} .card-label{font-size:12px;color:var(--muted);margin-top:2px} .card-sub{font-size:11px;color:var(--muted)}
  .accent-red .card-val{color:var(--red)} .accent-amber .card-val{color:var(--amber)} .accent-green .card-val{color:var(--green)} .accent-blue .card-val{color:var(--blue)}
  table{width:100%;border-collapse:collapse;font-size:13px;background:#fff}
  .table-wrap{border:1px solid var(--line);border-radius:10px;overflow:hidden}
  th{background:#0f172a;color:#fff;text-align:left;padding:8px 10px;font-weight:600}
  td{padding:8px 10px;border-top:1px solid var(--line)}
  tr:nth-child(even) td{background:#f8fafc}
  .sev,.st{font-size:11px;font-weight:700;border-radius:20px;padding:2px 9px;color:#fff;text-transform:uppercase;letter-spacing:.4px}
  .sev-critical,.st-failed,.st-error{background:var(--red)} .sev-high{background:#ea580c}
  .sev-medium,.st-cancelled{background:var(--amber)} .sev-low,.st-success{background:#64748b}
  .st-success_with_warnings{background:var(--amber)}
  .st-running,.st-queued{background:var(--blue)} .sev-info{background:#94a3b8}
  code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
  details.run-detail{border:1px solid var(--line);border-radius:10px;padding:12px;background:#fff;margin-top:12px}
  summary{cursor:pointer;font-weight:600;font-size:13px}
  .run-block{margin-top:14px} .run-block h3{font-size:13px;border-bottom:1px dashed var(--line);padding-bottom:6px}
  ul.act{list-style:none;padding:0;font-size:13px} ul.act li{padding:7px 0;border-bottom:1px solid var(--line)}
  .act-ts{color:var(--muted);font-size:12px;margin-right:8px}
  footer{margin-top:32px;color:var(--muted);font-size:11px;text-align:center}
  .none{color:var(--muted);font-style:italic}
  @media print{body{padding:0} .cards{break-inside:avoid} details.run-detail{open:true}}
</style>
</head>
<body><div class="wrap">
  <header class="rpt">
    <div><h1>SOAR-Lite — Incident Response Report</h1><div style="color:var(--muted);font-size:12px">Automated playbook execution &amp; incident intelligence summary</div></div>
    <div class="meta">Generated: ${escapeHtml(new Date(report.meta.generatedAt).toLocaleString())}<br>SOAR-Lite v${escapeHtml(report.meta.appVersion)}</div>
  </header>
  <div class="filters">Filters: ${escapeHtml(filterLine)}</div>

  <h2>Executive Summary</h2>
  <div class="cards">
    ${card('Total Incidents', s.totalIncidents, `Critical: ${s.critical}`, 'accent-red')}
    ${card('High', s.high, 'Severity count', 'accent-amber')}
    ${card('Resolved', s.resolved, `${s.resolvedRate}% resolved rate`, 'accent-green')}
    ${card('Playbook Runs', s.totalRuns, `${s.successRate}% success`, 'accent-blue')}
    ${card('Runs Failed', s.runsFailed, 'Across all executions')}
    ${card('Active Playbooks', s.playbooksActive, `of ${s.totalPlaybooks} total`)}
  </div>

  ${sevTable}
  ${incRows}
  ${runRows}
  ${actRows}

  <footer>Generated by SOAR-Lite Automated Incident Response Playbook Runner · v1.0.0</footer>
</div></body></html>`;
}

function describeStep(st) {
  const out = st.output || {};
  const bits = [];
  for (const k of ['reputation', 'ruleId', 'host', 'messageId', 'signin_geo', 'edr_rootkit', 'ticketId', 'result']) {
    if (out[k] !== undefined && out[k] !== '') bits.push(`${k}=${out[k]}`);
  }
  if (st.error) bits.push(`error: ${st.error}`);
  return bits.join('  ');
}

// --------------------------------------------------------------------------- JSON
function renderJson(report) {
  return JSON.stringify(report, null, 2);
}

// --------------------------------------------------------------------------- Markdown
function renderMarkdown(report) {
  const s = report.summary;
  const lines = [];
  const md = true;
  lines.push('# SOAR-Lite Incident Response Report', '');
  lines.push(`> Generated ${report.meta.generatedAt} · SOAR-Lite v${report.meta.appVersion}`, '');
  lines.push('## Executive Summary', '');
  lines.push(`| Metric | Value |`);
  lines.push(`| --- | --- |`);
  lines.push(`| Total incidents | ${s.totalIncidents} |`);
  lines.push(`| Critical / High | ${s.critical} / ${s.high} |`);
  lines.push(`| Resolved (rate) | ${s.resolved} (${s.resolvedRate}%) |`);
  lines.push(`| Playbook runs | ${s.totalRuns} (${s.successRate}% success) |`);
  lines.push(`| Runs failed | ${s.runsFailed} |`);
  lines.push(`| Active playbooks | ${s.playbooksActive} of ${s.totalPlaybooks} |`);
  lines.push('');
  lines.push('## Incidents', '');
  lines.push(`| ID | Title | Category | Severity | Status |`);
  lines.push(`| --- | --- | --- | --- | --- |`);
  report.incidents.slice(0, 200).forEach((i) => lines.push(`| ${i.id} | ${i.title} | ${i.category} | ${i.severity} | ${i.status} |`));
  lines.push('');
  lines.push('## Playbook Executions', '');
  lines.push(`| Run | Playbook | Trigger | Status | Started |`);
  lines.push(`| --- | --- | --- | --- | --- |`);
  report.runs.slice(0, 200).forEach((r) => lines.push(`| ${r.id} | ${r.playbookName} | ${r.trigger} | ${r.status} | ${r.startedAt || '—'} |`));
  return lines.join('\n');
}

// --------------------------------------------------------------------------- CSV
function renderCsv(report) {
  const esc = (v) => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
  const rows = [['incident_id', 'title', 'category', 'severity', 'status', 'created_at', 'updated_at', 'assignee'].map(esc).join(',')];
  report.incidents.forEach((i) => {
    rows.push([i.id, i.title, i.category, i.severity, i.status, i.createdAt, i.updatedAt, i.assignee || ''].map(esc).join(','));
  });
  return rows.join('\n');
}

function filename(format) {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `soar-report-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}.${format === 'html' ? 'html' : (format === 'json' ? 'json' : format)}`;
}

module.exports = { buildReport, renderHtml, renderJson, renderMarkdown, renderCsv, filename };