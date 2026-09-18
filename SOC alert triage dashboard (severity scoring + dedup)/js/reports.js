/* ============================================================
   SOC ALERT TRIAGE DASHBOARD - Report Generator
   Generates standalone HTML reports
   ============================================================ */

const SOCReport = (() => {
  'use strict';

  /* ---------- Report CSS (embedded for standalone HTML) ---------- */
  const REPORT_CSS = `
  :root { --crit:#e74c3c; --high:#f39c12; --med:#f1c40f; --low:#3498db; --info:#2ecc71; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', -apple-system, Arial, sans-serif; background:#f6f8fb; color:#1f2937; font-size:13px; line-height:1.6; }
  .container { max-width:1100px; margin:0 auto; padding:32px 20px; }
  .report-header { background:linear-gradient(135deg,#0f1522,#1a2438); color:#fff; padding:32px 28px; border-radius:12px 12px 0 0; position:relative; overflow:hidden; }
  .report-header::after { content:''; position:absolute; top:0; right:0; width:260px; height:100%; background:radial-gradient(circle at 80% 20%, rgba(55,213,222,0.15), transparent 60%); }
  .report-header h1 { font-size:22px; font-weight:800; margin-bottom:4px; }
  .report-header .sub { color:#93a4b8; font-size:13px; }
  .report-meta { display:flex; gap:28px; margin-top:18px; flex-wrap:wrap; }
  .report-meta .meta { font-size:12px; }
  .report-meta .meta b { display:block; font-size:18px; color:#37d5de; }
  .report-section { background:#fff; border:1px solid #e5e7eb; border-top:none; padding:24px 28px; }
  .report-section h2 { font-size:16px; font-weight:700; margin-bottom:14px; color:#0f1522; padding-bottom:8px; border-bottom:2px solid #f0f2f5; }
  .report-section h3 { font-size:13px; font-weight:700; margin:16px 0 8px; color:#374151; }
  .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; }
  .summary-card { background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:14px; text-align:center; }
  .summary-card .num { font-size:24px; font-weight:800; color:#0f1522; }
  .summary-card .lbl { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; margin-top:2px; }
  .summary-card.critical .num { color:var(--crit); } .summary-card.high .num { color:var(--high); }
  .summary-card.medium .num { color:var(--med); } .summary-card.low .num { color:var(--low); }
  .severity-table { width:100%; border-collapse:collapse; }
  .severity-table th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.6px; color:#6b7280; padding:8px 10px; background:#f9fafb; border:1px solid #e5e7eb; }
  .severity-table td { padding:9px 10px; border:1px solid #e5e7eb; font-size:12.5px; }
  .sev-badge { display:inline-block; padding:2px 9px; border-radius:10px; font-weight:700; font-size:11px; }
  .sev-Critical { background:#fdecea; color:#c0392b; } .sev-High { background:#fef5e7; color:#d68910; }
  .sev-Medium { background:#fef9e7; color:#b7950b; } .sev-Low { background:#ebf5fb; color:#217dbb; }
  .sev-Info { background:#eafaf1; color:#1e8449; }
  .st-badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; background:#f3f4f6; color:#374151; }
  .mono { font-family:Consolas, Menlo, monospace; font-size:11.5px; }
  .bar-wrap { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
  .bar-label { width:80px; font-size:11.5px; color:#4b5563; text-align:right; }
  .bar-track { flex:1; height:14px; background:#f1f5f9; border-radius:3px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:3px; min-width:3px; }
  .bar-count { width:34px; font-size:11.5px; font-weight:600; color:#374151; }
  .alert-table { width:100%; border-collapse:collapse; }
  .alert-table th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#6b7280; padding:8px 8px; background:#f9fafb; border:1px solid #e5e7eb; position:sticky; top:0; }
  .alert-table td { padding:7px 8px; border:1px solid #e5e7eb; font-size:12px; vertical-align:top; }
  .alert-table tr:hover { background:#f8fafc; }
  .dup-flag { display:inline-block; font-size:10px; padding:1px 7px; border-radius:9px; background:#fef5e7; color:#b7950b; font-weight:600; }
  .unique-flag { display:inline-block; font-size:10px; padding:1px 7px; border-radius:9px; background:#eafaf1; color:#1e8449; font-weight:600; }
  .footer { text-align:center; padding:20px; color:#9ca3af; font-size:11px; background:#fff; border:1px solid #e5e7eb; border-top:none; border-radius:0 0 12px 12px; }
  .highlight-box { background:#fffbeb; border:1px solid #fde68a; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:6px; margin:12px 0; font-size:12.5px; }
  .score-bar { display:inline-block; width:60px; height:6px; background:#edf2f7; border-radius:3px; position:relative; margin-left:6px; vertical-align:middle; overflow:hidden; }
  .score-fill { position:absolute; left:0; top:0; bottom:0; border-radius:3px; }
  .print-btn { position:fixed; top:16px; right:16px; background:#0f1522; color:#fff; border:none; padding:10px 18px; border-radius:8px; font-weight:600; cursor:pointer; font-size:13px; box-shadow:0 4px 12px rgba(0,0,0,0.2); }
  .print-btn:hover { background:#1a2438; }
  @media print { .print-btn { display:none; } body { background:#fff; } .report-section{ border:none; padding:12px 0;} .container{ padding:0; max-width:100%;} }
  `;

  /* ---------- Helper: staggered severity color for chart bars ---------- */
  function sevColor(sev) {
    const map = {
      'Critical': '#e74c3c',
      'High': '#f39c12',
      'Medium': '#f1c40f',
      'Low': '#3498db',
      'Info': '#2ecc71'
    };
    return map[sev] || '#94a3b8';
  }

  /* ---------- Build DATE stamp ---------- */
  function nowStamp() {
    return new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  }

  /* ---------- Build the summary section HTML ---------- */
  function buildSummary(alerts, allAlerts) {
    const total = allAlerts.length;
    const unique = alerts.length;
    const dups = total - unique;
    const dedupRate = total > 0 ? Math.round((dups / total) * 100) : 0;

    const sevCounts = { Critical: 0, High: 0, Medium: 0, Low: 0, Info: 0 };
    alerts.forEach(a => { sevCounts[a.severity] = (sevCounts[a.severity] || 0) + 1; });

    const avgScore = alerts.length ? (alerts.reduce((s, a) => s + a.severityScore, 0) / alerts.length).toFixed(1) : '0.0';

    const srcDist = {};
    alerts.forEach(a => { srcDist[a.dataSource] = (srcDist[a.dataSource] || 0) + 1; });

    let html = `
      <h2>Executive Summary</h2>
      <div class="summary-grid">
        <div class="summary-card"><div class="num">${total}</div><div class="lbl">Total Alerts</div></div>
        <div class="summary-card"><div class="num">${unique}</div><div class="lbl">Unique</div></div>
        <div class="summary-card"><div class="num">${dups}</div><div class="lbl">Duplicates</div></div>
        <div class="summary-card"><div class="num">${dedupRate}%</div><div class="lbl">Dedup Rate</div></div>
        <div class="summary-card"><div class="num">${avgScore}</div><div class="lbl">Avg Score</div></div>
      </div>
      <div style="margin-top:18px">
        <h3>Severity Distribution</h3>
        ${['Critical','High','Medium','Low','Info'].map(s => {
          const count = sevCounts[s] || 0;
          const pct = unique ? Math.round((count / unique) * 100) : 0;
          return `<div class="bar-wrap"><span class="bar-label">${s}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%; background:${sevColor(s)}"></div></div>
            <span class="bar-count">${count} (${pct}%)</span></div>`;
        }).join('')}
      </div>
      <h3>Top Alert Sources</h3>
      <table class="severity-table">
        <tr><th>Source</th><th>Count</th><th>% of Unique</th></tr>
        ${Object.entries(srcDist).sort((a,b) => b[1]-a[1]).map(([src, cnt]) =>
          `<tr><td>${src}</td><td>${cnt}</td><td>${unique ? Math.round(cnt/unique*100) : 0}%</td></tr>`).join('')}
      </table>
    `;
    return html;
  }

  /* ---------- Build deduplication section ---------- */
  function buildDedupSection(alerts) {
    const originals = alerts.filter(a => (a.dupCount || 0) > 0);
    const totalDeduped = alerts.reduce((s, a) => s + (a.dupCount || 0), 0);

    let html = `<h2>Deduplication Report</h2>`;
    html += `<div class="highlight-box">
      <b>${totalDeduped}</b> duplicate alerts identified and merged into <b>${originals.length}</b> deduplication groups.
      Deduplication reduced alert noise by analyzing source IP, destination IP, threat type, and time-window proximity.
    </div>`;

    if (originals.length === 0) {
      html += `<p style="color:#6b7280">No deduplication groups found in the current view.</p>`;
      return html;
    }

    html += `<table class="alert-table"><tr>
      <th>Group</th><th>Original Alert</th><th>Source IP</th><th>Threat Type</th><th>Merge Count</th><th>Time Window</th>
    </tr>`;

    originals.slice(0, 25).forEach(g => {
      const dupTimestamps = [];
      alerts.forEach(a => {
        if (a.isDuplicate && a.duplicateOf === g.id) {
          dupTimestamps.push(new Date(a.timestamp));
        }
      });
      const oldest = dupTimestamps.length ? new Date(Math.min(...dupTimestamps.map(d => d.getTime()))).toISOString().substring(11,16) : '-';
      const latest = dupTimestamps.length ? new Date(Math.max(...dupTimestamps.map(d => d.getTime()))).toISOString().substring(11,16) : '-';
      html += `<tr>
        <td class="mono">GRP-${String(g.dedupGroup || 0).padStart(3, '0')}</td>
        <td>${esc(g.title)}</td>
        <td class="mono">${esc(g.sourceIP)}</td>
        <td>${esc(g.threatType)}</td>
        <td><b>${g.dupCount + 1}</b> alerts</td>
        <td class="mono">${oldest} - ${latest}</td>
      </tr>`;
    });

    if (originals.length > 25) {
      html += `<tr><td colspan="6" style="text-align:center; color:#6b7280">... and ${originals.length - 25} more groups (top 25 shown)</td></tr>`;
    }
    html += `</table>`;
    return html;
  }

  /* ---------- Escape HTML ---------- */
  function esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /* ---------- Build alert details section ---------- */
  function buildAlertDetails(alerts) {
    let html = `<h2>Alert Details (${alerts.length} Alerts)</h2>`;
    html += `<table class="alert-table"><tr>
      <th>ID</th><th>Time</th><th>Severity</th><th>Score</th><th>Alert</th>
      <th>Source IP</th><th>Dest IP</th><th>Category</th><th>Status</th><th>Dedup</th>
    </tr>`;

    alerts.slice(0, 150).forEach(a => {
      const color = sevColor(a.severity);
      html += `<tr>
        <td class="mono">${esc(a.id)}</td>
        <td class="mono">${esc(a.timestamp.substring(0, 19).replace('T', ' '))}</td>
        <td><span class="sev-badge sev-${esc(a.severity)}">${esc(a.severity)}</span></td>
        <td class="mono"><b>${a.severityScore.toFixed(1)}</b>
          <span class="score-bar"><span class="score-fill" style="width:${Math.round(a.severityScore * 10)}%; background:${color}"></span></span>
        </td>
        <td style="max-width:280px">${esc(a.title)}</td>
        <td class="mono">${esc(a.sourceIP)}</td>
        <td class="mono">${esc(a.destIP)}</td>
        <td>${esc(a.category)}</td>
        <td><span class="st-badge">${esc(a.status)}</span></td>
        <td>${a.dupCount > 0 ? `<span class="dup-flag">${a.dupCount + 1} merged</span>` : `<span class="unique-flag">unique</span>`}</td>
      </tr>`;
    });

    if (alerts.length > 150) {
      html += `<tr><td colspan="10" style="text-align:center;color:#6b7280">Showing top 150 alerts. Total: ${alerts.length}</td></tr>`;
    }

    html += `</table>`;
    return html;
  }

  /* ---------- Build top risks section ---------- */
  function buildTopRisks(alerts) {
    const sorted = [...alerts].sort((a, b) => b.severityScore - a.severityScore).slice(0, 10);
    let html = `<h2>Top Risk Alerts</h2>`;
    html += `<table class="alert-table"><tr>
      <th>#</th><th>Alert</th><th>Score</th><th>Severity</th><th>Source</th><th>Threat Type</th><th>Recommendation</th>
    </tr>`;
    sorted.forEach((a, i) => {
      html += `<tr>
        <td>${i + 1}</td>
        <td style="max-width:250px"><b>${esc(a.title)}</b><br><span class="mono" style="color:#6b7280">${esc(a.id)}</span></td>
        <td class="mono"><b style="color:${sevColor(a.severity)}">${a.severityScore.toFixed(1)}</b></td>
        <td><span class="sev-badge sev-${esc(a.severity)}">${esc(a.severity)}</span></td>
        <td>${esc(a.dataSource)}</td>
        <td>${esc(a.threatType)}</td>
        <td style="font-size:11.5px; color:#4b5563; max-width:260px">${esc(a.recommendation)}</td>
      </tr>`;
    });
    html += `</table>`;
    return html;
  }

  /* ---------- Main report builder ---------- */
  function generateReport(alerts, options = {}) {
    const {
      includeSummary = true,
      includeStats = true,
      includeAlerts = true,
      includeDedup = true
    } = options;

    const now = new Date();
    const filename = `SOC_Alert_Report_${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}.html`;

    // Compute stats for the header
    const total = alerts.length;
    const critical = alerts.filter(a => a.severity === 'Critical').length;
    const high = alerts.filter(a => a.severity === 'High').length;
    const medium = alerts.filter(a => a.severity === 'Medium').length;
    const low = alerts.filter(a => a.severity === 'Low').length;
    const info = alerts.filter(a => a.severity === 'Info').length;
    const duplicates = alerts.filter(a => a.dupCount > 0).length;
    const dedupRate = total ? Math.round((duplicates / total) * 100) : 0;
    const avg = total ? (alerts.reduce((s, a) => s + a.severityScore, 0) / total).toFixed(1) : '0.0';
    const investigating = alerts.filter(a => a.status === 'Investigating').length;
    const resolved = alerts.filter(a => a.status === 'Resolved').length;

    // Time range of data
    const sortedByTime = [...alerts].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const timeStart = sortedByTime.length ? sortedByTime[0].timestamp.substring(0, 19).replace('T', ' ') : '-';
    const timeEnd = sortedByTime.length ? sortedByTime[sortedByTime.length - 1].timestamp.substring(0, 19).replace('T', ' ') : '-';

    let body = '';

    if (includeSummary) body += buildSummary(alerts, alerts);

    if (includeStats) {
      body += `<h2>Statistics</h2>
      <div class="summary-grid">
        <div class="summary-card critical"><div class="num">${critical}</div><div class="lbl">Critical</div></div>
        <div class="summary-card high"><div class="num">${high}</div><div class="lbl">High</div></div>
        <div class="summary-card medium"><div class="num">${medium}</div><div class="lbl">Medium</div></div>
        <div class="summary-card low"><div class="num">${low}</div><div class="lbl">Low</div></div>
        <div class="summary-card"><div class="num" style="color:#2ecc71">${info}</div><div class="lbl">Info</div></div>
      </div>
      <div style="margin-top:14px">
        <b>Status breakdown:</b> ${investigating} investigating, ${resolved} resolved, 
        ${alerts.filter(a => a.status === 'New').length} new, 
        ${alerts.filter(a => a.status === 'False Positive').length} false positive.
      </div>
      <div style="margin-top:8px; color:#4b5563">
        <b>Deduplication:</b> ${duplicates} duplicate alerts detected (${dedupRate}% of total), reducing analyst workload significantly.
        <b>Average severity score:</b> ${avg}/10.
      </div>`;
    }

    if (includeDedup) body += buildDedupSection(alerts);

    body += buildTopRisks(alerts);

    if (includeAlerts) body += buildAlertDetails(alerts);

    const reportHTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOC Alert Triage Report - ${now.toISOString()}</title>
<style>${REPORT_CSS}</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">Print / Save PDF</button>
<div class="container">
  <div class="report-header">
    <h1>SOC Alert Triage Report</h1>
    <div class="sub">Automated severity scoring &amp; deduplication analysis</div>
    <div class="report-meta">
      <div class="meta"><b>${total}</b>Total Alerts</div>
      <div class="meta"><b>${dedupRate}%</b>Dedup Rate</div>
      <div class="meta"><b>${avg}</b>Avg Severity</div>
      <div class="meta"><b>${critical}</b>Critical</div>
      <div class="meta"><b>${high}</b>High</div>
    </div>
  </div>
  <div class="report-section">${body}</div>
  <div class="footer">
    Generated by SOC Shield Alert Triage Dashboard on ${esc(nowStamp())}<br>
    Report window: <span class="mono">${esc(timeStart)} → ${esc(timeEnd)}</span>
    &nbsp;|&nbsp; Confidential - For internal security team use only
  </div>
</div>
</body>
</html>`;

    return { html: reportHTML, filename };
  }

  return {
    generateReport,
    nowStamp
  };
})();

if (typeof window !== 'undefined') {
  window.SOCReport = SOCReport;
}