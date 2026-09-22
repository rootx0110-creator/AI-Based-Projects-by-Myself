'use strict';
/**
 * reporter.js — self-contained HTML report (inline CSS, no CDN, no JS deps).
 */

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const SEV_COLOR = { CRITICAL: '#ff4d6d', HIGH: '#ff9f43', MEDIUM: '#f9c74f', LOW: '#4dd0e1' };

function badge(sev) {
  return `<span class="badge" style="background:${SEV_COLOR[sev]}22;color:${SEV_COLOR[sev]};border:1px solid ${SEV_COLOR[sev]}55">${esc(sev)}</span>`;
}

function ring(score, gradeLetter) {
  const deg = Math.round((score / 100) * 360);
  return `<div class="ring" style="--deg:${deg}deg"><div class="ring-inner"><span class="grade">${esc(gradeLetter)}</span><span class="score">${score}/100</span></div></div>`;
}

function buildHtmlReport(report) {
  const { meta, summary, files } = report;
  const affected = files.filter(f => f.findings.length > 0);

  const severityRows = Object.entries(summary.bySeverity)
    .map(([sev, n]) => `<tr><td>${badge(sev)}</td><td class="num">${n}</td><td><div class="bar"><div style="width:${Math.min(100, n * 5)}%;background:${SEV_COLOR[sev]}"></div></div></td></tr>`)
    .join('');

  const fileSections = affected.map(f => `
    <section class="file">
      <h3>${esc(f.name)} <span class="meta">(${esc(f.language)}, ${f.findings.length} finding${f.findings.length > 1 ? 's' : ''}, risk ${f.score})</span></h3>
      ${f.findings.map(fd => `
      <div class="finding" style="border-left:4px solid ${SEV_COLOR[fd.severity]}">
        <div class="fhead">
          ${badge(fd.severity)}
          <strong>${esc(fd.title)}</strong>
          <span class="mono loc">line ${fd.line}:${fd.col}</span>
          <span class="chip mono">${esc(fd.ruleId)}</span>
          <span class="chip mono">${esc(fd.cwe)}</span>
        </div>
        <p class="why"><em>Why it matters:</em> ${esc(fd.why)}</p>
        <p class="exploit"><em>Exploitation scenario:</em> ${esc(fd.exploit)}</p>
        <pre class="code"><code>${esc(fd.snippet || fd.match)}</code></pre>
        <pre class="fix"><code>${esc(fd.fixSnippet)}</code></pre>
        ${fd.refs && fd.refs.length ? `<p class="refs">References: ${fd.refs.map(r => `<a href="${esc(r)}">${esc(r)}</a>`).join(' · ')}</p>` : ''}
      </div>`).join('')}
    </section>`).join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SecuRevealer Report — risk ${summary.riskScore}/100 (${summary.grade})</title>
<style>
  :root { --bg:#0b0f17; --panel:#111827; --text:#e5e7eb; --muted:#9ca3af; --accent:#22d3ee; }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.6 'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); }
  .wrap { max-width:960px; margin:0 auto; padding:32px 20px; }
  header { display:flex; align-items:center; gap:24px; border-bottom:1px solid #1f2937; padding-bottom:24px; }
  h1 { margin:0; font-size:24px; } h1 .sub { display:block; color:var(--muted); font-size:13px; font-weight:400; margin-top:4px; }
  h2 { font-size:18px; margin:32px 0 12px; color:var(--accent); letter-spacing:.5px; text-transform:uppercase; }
  h3 { margin:20px 0 8px; font-size:16px; } h3 .meta { color:var(--muted); font-weight:400; font-size:13px; }
  .ring { --deg:${Math.round((summary.riskScore / 100) * 360)}deg; width:110px; height:110px; border-radius:50%; flex:0 0 auto;
    background:conic-gradient(var(--accent) var(--deg), #1f2937 0); display:flex; align-items:center; justify-content:center; }
  .ring-inner { width:88px; height:88px; border-radius:50%; background:var(--bg); display:flex; flex-direction:column; align-items:center; justify-content:center; }
  .grade { font-size:28px; font-weight:700; color:var(--accent); }
  .score { font-size:11px; color:var(--muted); }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; margin:20px 0; }
  .stat { background:var(--panel); border:1px solid #1f2937; border-radius:10px; padding:14px; text-align:center; }
  .stat b { display:block; font-size:22px; }
  .stat span { color:var(--muted); font-size:12px; }
  table { width:100%; border-collapse:collapse; margin-top:8px; }
  td, th { padding:8px 10px; border-bottom:1px solid #1f2937; text-align:left; }
  td.num { text-align:right; width:40px; font-variant-numeric:tabular-nums; }
  .bar { height:8px; background:#1f2937; border-radius:4px; overflow:hidden; }
  .badge { padding:2px 10px; border-radius:99px; font-size:11px; font-weight:700; letter-spacing:.5px; }
  .chip { background:#1f2937; color:var(--muted); border-radius:6px; padding:2px 8px; font-size:11px; }
  .mono { font-family:'Cascadia Code',Consolas,monospace; font-size:12px; }
  .loc { color:var(--accent); }
  .finding { background:var(--panel); border:1px solid #1f2937; border-radius:10px; padding:14px 16px; margin:12px 0; }
  .fhead { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px; }
  .why, .exploit, .refs { color:var(--muted); font-size:13.5px; margin:6px 0; }
  .why em, .exploit em { color:var(--accent); font-style:normal; font-weight:600; }
  .refs a { color:var(--accent); word-break:break-all; }
  pre { background:#0b0f17; border:1px solid #1f2937; border-radius:8px; padding:12px; overflow-x:auto; font:12.5px/1.5 'Cascadia Code',Consolas,monospace; margin:8px 0; }
  pre.fix { border-color:#14532d; }
  pre.fix::before { content:'SUGGESTED FIX'; display:block; color:#34d399; font-size:10px; letter-spacing:1px; margin-bottom:6px; }
  footer { margin-top:40px; border-top:1px solid #1f2937; padding-top:16px; color:var(--muted); font-size:12px; }
  @media print { body { background:#fff; color:#111; } .ring { background:conic-gradient(#0ea5e9 var(--deg), #ddd var(--deg)); } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    ${ring(summary.riskScore, summary.grade)}
    <h1>Security Review Report
      <span class="sub">SecuRevealer v${esc(meta.version)} · ${esc(new Date(meta.scannedAt).toLocaleString())}</span>
    </h1>
  </header>

  <div class="stats">
    <div class="stat"><b>${summary.totalFindings}</b><span>findings</span></div>
    <div class="stat"><b>${summary.filesAffected}</b><span>files affected</span></div>
    <div class="stat"><b>${meta.filesScanned}</b><span>files scanned</span></div>
    <div class="stat"><b>${meta.linesScanned}</b><span>lines scanned</span></div>
  </div>

  <h2>Severity Breakdown</h2>
  <table>${severityRows}</table>

  <h2>Detailed Findings</h2>
  ${fileSections || '<p style="color:#9ca3af">No findings. Nothing insecure detected in the provided files.</p>'}

  <footer>
    Generated by <strong>SecuRevealer</strong> — AI-assisted insecure-pattern review · ${esc(new Date(meta.scannedAt).toISOString())}<br>
    Educational tool: patterns are heuristic; verify findings before acting.
  </footer>
</div>
</body>
</html>`;
}

module.exports = { buildHtmlReport };