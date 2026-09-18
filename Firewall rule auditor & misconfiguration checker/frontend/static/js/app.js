/* ============================================================
   FRAMC frontend application
   ============================================================ */
'use strict';

/* ---------------- state ---------------- */
const state = {
  route: 'dashboard',
  formats: [],
  format: 'iptables',
  fileName: '',
  analyzing: false,
  report: null,
  rules: { search: '', action: '', sev: '', page: 1, pageSize: 12 },
  findings: { sev: 'ALL', shown: 20 },
  theme: localStorage.getItem('framc.theme') || 'cyber',
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'NONE'];

/* ---------------- api ---------------- */
async function getJSON(url) {
  const r = await fetch(url);
  const j = await r.json().catch(() => null);
  return { status: r.status, body: j };
}

async function analyze() {
  const name = $('#configName').value.trim() || state.fileName || 'configuration';
  setAnalyzing(true);
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: state.format, name, content: $('#configText').value.trim() }),
    });
    let body = null;
    try { body = await res.json(); } catch (e) { /* non-JSON error page */ }
    if (!res.ok || !body || !body.ok) {
      toast((body && body.error) || `Analysis failed (HTTP ${res.status})`, 'error');
      return;
    }
    state.report = body.data;
    state.fileName = name;
    const fmts = await getJSON('/api/formats');
    if (fmts.body && fmts.body.ok) state.formats = fmts.body.data.formats.map(f => f.id);
    renderAll();
    setRoute('dashboard');
    toast('Analysis complete', 'ok');
  } catch (err) {
    toast(`Could not reach the audit engine: ${err.message || 'network error'}`, 'error');
  } finally {
    setAnalyzing(false);
  }
}

/* ---------------- rendering helpers ---------------- */
function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function toast(msg, kind = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function setAnalyzing(on) {
  state.analyzing = on;
  $('#loadingOverlay').hidden = !on;
  $('#analyzeBtn').disabled = on;
}

function setRoute(route) {
  state.route = route;
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.route === route));
  $$('.route-panel').forEach(p => p.classList.toggle('active', p.dataset.panel === route));
  if (route === 'report') renderReport();
}

function hasReport() {
  return !!state.report;
}

function renderAll() {
  const has = hasReport();
  $('#dashEmpty').hidden = has;
  $('#dashFilled').hidden = !has;
  $$('.empty-state[data-for]').forEach(e => {
    const target = e.dataset.for;
    if (!target) return;
    const filled = target === 'rules' ? $('#rulesFilled')
      : target === 'findings' ? $('#findingsFilled')
      : target === 'report' ? $('#reportFilled') : null;
    if (filled) filled.hidden = !has;
    e.hidden = has;
  });
  if (has) {
    renderDashboard();
    renderRules();
    renderFindings();
    updateNav();
  } else {
    updateNav();
    destroyCharts();
  }
}

function updateNav() {
  const r = state.report;
  const rc = $('#navRules'), fc = $('#navFindings'), pm = $('#postureMini');
  if (!r) { rc.hidden = true; fc.hidden = true; pm.hidden = true; return; }
  rc.hidden = false;
  rc.textContent = r.summary.total;
  fc.hidden = false;
  fc.textContent = r.findings.length;
  pm.hidden = false;
  const deg = r.posture.score;
  pm.style.setProperty('--deg', deg);
  $('#pmScore').textContent = deg;
  $('#pmGrade').textContent = r.posture.grade;
}

/* ---------------- dashboard ---------------- */
let charts = {};

function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch (e) {} });
  charts = {};
}

function renderDashboard() {
  const r = state.report;
  const p = r.posture, s = r.summary;
  $('#pcScore').textContent = p.score;
  $('#pcGrade').textContent = p.grade;
  $('#pcGrade').className = `pc-grade grade-${p.grade}`;
  $('#pcAllow').textContent = `${s.allow_count} allow`;
  $('#pcDeny').textContent = `${s.deny_count} deny`;
  const sev = p.by_severity || {};
  $('#kpiCrit').textContent = sev.CRITICAL || 0;
  $('#kpiHigh').textContent = sev.HIGH || 0;
  $('#kpiMed').textContent = sev.MEDIUM || 0;
  $('#kpiRules').textContent = s.total;
  $('#dashSub').textContent =
    `Auditing “${esc(r.name)}” (${esc(r.format)}) — posture ${p.score}/100 · grade ${p.grade}`;

  drawGauge('gaugeCanvas', p.score);
  drawSevChart(sev, p.severity_weights);
  drawMixChart(s);
  renderTopRules();
  renderTopFindings();
}

function drawGauge(canvasId, score) {
  const cv = document.getElementById(canvasId);
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const cx = W / 2, cy = H - 16, rad = Math.min(W / 2 - 14, H - 26);
  ctx.clearRect(0, 0, W, H);
  const start = Math.PI, end = 2 * Math.PI;
  const grad = ctx.createLinearGradient(0, 0, W, 0);
  const color = score >= 85 ? '#34d399' : score >= 70 ? '#22d3ee' :
                score >= 55 ? '#fbbf24' : score >= 40 ? '#fb923c' : '#fb7185';
  grad.addColorStop(0, color); grad.addColorStop(1, color);

  ctx.lineWidth = 13; ctx.lineCap = 'round';
  ctx.strokeStyle = 'rgba(128,150,210,0.16)';
  ctx.beginPath(); ctx.arc(cx, cy, rad, start, end); ctx.stroke();
  const frac = Math.max(0.02, score / 100);
  ctx.strokeStyle = color;
  ctx.shadowColor = color; ctx.shadowBlur = 14;
  ctx.beginPath(); ctx.arc(cx, cy, rad, start, start + frac * Math.PI); ctx.stroke();
  ctx.shadowBlur = 0;
  ctx.fillStyle = '#e6ecff';
  ctx.font = '800 30px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText(String(score), cx, cy - 12);
  ctx.fillStyle = 'rgba(147,162,196,0.9)';
  ctx.font = '600 10px "Inter", sans-serif';
  ctx.fillText('POSTURE', cx, cy + 4);
}

function chartStyle() {
  const cs = getComputedStyle(document.documentElement);
  return {
    text: cs.getPropertyValue('--text').trim() || '#e6ecff',
    dim: cs.getPropertyValue('--text-dim').trim() || '#93a2c4',
    line: cs.getPropertyValue('--line-strong').trim() || 'rgba(120,200,255,0.28)',
    grid: cs.getPropertyValue('--line').trim() || 'rgba(120,160,255,0.14)',
    accent: cs.getPropertyValue('--accent').trim() || '#22d3ee',
    accent2: cs.getPropertyValue('--accent-2').trim() || '#818cf8',
  };
}

const SEV_COLORS = {
  CRITICAL: '#fb7185', HIGH: '#fb923c', MEDIUM: '#fbbf24',
  LOW: '#38bdf8', INFO: '#94a3b8', NONE: '#475569',
};

function drawSevChart(bySev, weights) {
  const ctx = $('#chartSev').getContext('2d');
  const keys = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
  const labels = keys.map(k => `${k} (×${weights ? weights[k] : 0})`);
  const data = keys.map(k => bySev[k] || 0);
  if (charts.sev) charts.sev.destroy();
  charts.sev = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: keys.map(k => SEV_COLORS[k]),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '66%',
      plugins: {
        legend: { position: 'right', labels: { color: chartStyle().dim, font: { size: 11 }, boxWidth: 11, padding: 12 } },
        tooltip: { callbacks: { label: c => ` ${c.label}: ${c.raw}` } },
      },
    },
  });
}

function drawMixChart(summary) {
  const ctx = $('#chartMix').getContext('2d');
  if (charts.mix) charts.mix.destroy();
  const actions = Object.entries(summary.by_action || {});
  const protos = Object.entries(summary.by_protocol || {});
  const labels = [...actions.map(a => `${a[0]} rules`), ...protos.map(p => `proto:${p[0]}`)];
  const values = [...actions.map(a => a[1]), ...protos.map(p => p[1])];
  const palette = ['#34d399', '#fb7185', '#fbbf24', '#818cf8', '#38bdf8', '#94a3b8', '#f472b6', '#fbbf24'];
  charts.mix = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: labels.map((_, i) => palette[i % palette.length]),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {} },
      scales: {
        x: { ticks: { color: chartStyle().dim, font: { size: 10 } }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: chartStyle().dim }, grid: { color: chartStyle().grid } },
      },
    },
  });
}

function renderTopRules() {
  const el = $('#topRules');
  const top = [...(state.report.rules || [])]
    .sort((a, b) => b.risk - a.risk).slice(0, 6);
  el.innerHTML = top.length ? top.map(x => `
    <div class="mini-item">
      <span class="mi-id">${esc(x.id)}</span>
      <span class="mi-txt">${esc(x.action)} — ${esc(x.src_ip)} → ${esc(x.dst_ip)}:${esc(x.dst_port)}</span>
      <span class="mi-risk" style="color:${riskColor(x.risk)}">${x.risk}</span>
    </div>`).join('')
    : '<p class="panel-sub">No rules audited.</p>';
}

function renderTopFindings() {
  const el = $('#topFindings');
  const top = (state.report.findings || []).filter(f => f.severity !== 'INFO').slice(0, 5);
  el.innerHTML = top.length ? top.map(f => `
    <div class="mini-item">
      <span class="badge ${esc(f.severity)}">${esc(f.severity)}</span>
      <span class="mi-txt">${esc(f.title)}</span>
    </div>`).join('')
    : '<p class="panel-sub">No non-informational findings — good hygiene.</p>';
}

function riskColor(r) {
  return r >= 70 ? '#fb7185' : r >= 45 ? '#fbbf24' : '#34d399';
}

/* ---------------- rules table ---------------- */
function renderRules() {
  const q = state.rules;
  let rows = (state.report && state.report.rules) || [];
  const term = q.search.trim().toLowerCase();
  rows = rows.filter(r => {
    if (q.action && r.action !== q.action) return false;
    if (q.sev && r.worst_severity !== q.sev) return false;
    if (term) {
      const hay = `${r.src_ip} ${r.src_port} ${r.dst_ip} ${r.dst_port} ${r.description} ${r.protocol} ${r.id}`.toLowerCase();
      if (!hay.includes(term)) return false;
    }
    return true;
  });
  $('#rulesCount').textContent = `${rows.length} rule(s)`;
  const totalPages = Math.max(1, Math.ceil(rows.length / q.pageSize));
  if (q.page > totalPages) q.page = totalPages;
  const slice = rows.slice((q.page - 1) * q.pageSize, q.page * q.pageSize);
  const tpl = $('#ruleRow').innerHTML;
  $('#rulesBody').innerHTML = slice.map(r => tpl
    .replace('{id}', esc(r.id))
    .replace('{action-class}', esc(r.action))
    .replace('{action}', esc(r.action))
    .replace('{direction}', esc(r.direction))
    .replace('{protocol}', esc(r.protocol))
    .replace('{src}', esc(r.src_ip))
    .replace('{sport}', esc(r.src_port))
    .replace('{dst}', esc(r.dst_ip))
    .replace('{dport}', esc(r.dst_port))
    .replace('{risk}', r.risk)
    .replace('{sev}', sevLabels(r.findings))
  ).join('') || `<tr><td colspan="10" class="center">No matching rules.</td></tr>`;
  $('#rulesPageInfo').textContent = `Page ${q.page} / ${totalPages}`;
  $('#rulesPrev').disabled = q.page <= 1;
  $('#rulesNext').disabled = q.page >= totalPages;
}

function sevLabels(counts) {
  if (!counts) return '<span class="sev-label sev-NONE">clean</span>';
  const parts = [];
  SEV_ORDER.slice(0, 5).forEach(s => {
    if (counts[s]) parts.push(`<span class="sev-label sev-${s}">${s}·${counts[s]}</span>`);
  });
  return parts.length ? parts.join('') : '<span class="sev-label sev-NONE">clean</span>';
}

/* ---------------- findings ---------------- */
function renderFindings() {
  const sev = state.findings.sev;
  let list = (state.report && state.report.findings) || [];
  if (sev !== 'ALL') list = list.filter(f => f.severity === sev);
  const total = list.length;
  const shown = list.slice(0, state.findings.shown);
  const tpl = $('#findingCard').innerHTML;
  $('#findingsList').innerHTML = shown.map(f => tpl
    .replace(/\{sevclass\}/g, esc(f.severity))
    .replace(/\{sev\}/g, esc(f.severity))
    .replace(/\{tags\}/g, '')
    .replace('{title}', esc(f.title))
    .replace('{detail}', esc(f.detail))
    .replace('{category}', esc(f.category))
    .replace('{rules}', esc(f.rule_ids.join(', ')))
    .replace('{fix}', esc(f.recommendation))
  ).join('') || '<div class="center panel-sub">No findings for this filter.</div>';
  $('#findingsMore').style.display = total > state.findings.shown ? '' : 'none';
  $('#findingsMore').textContent = `Load more (${total - state.findings.shown} remaining)`;
}

/* ---------------- report ---------------- */
function renderReport() {
  const r = state.report;
  if (!r) return;
  const p = r.posture;
  const meta = [
    ['Config', r.name || '—'], ['Format', r.format], ['Audited at', r.generated_at.replace('T', ' ').slice(0, 19) + ' UTC'],
    ['Rules', r.summary.total], ['NAT rules', (r.nats || []).length], ['Findings', r.findings.length],
    ['Grade', `${p.grade} · ${p.score}/100`], ['Warnings', r.meta.warnings.length],
  ];
  $('#reportMeta').innerHTML = meta.map(m => `
    <div class="rm-item"><span class="rm-label">${m[0]}</span><span class="rm-value">${esc(m[1])}</span></div>`).join('');

  // contribution chart
  const ctx = $('#chartContrib').getContext('2d');
  if (charts.contrib) charts.contrib.destroy();
  const keys = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
  const bySev = p.by_severity || {};
  const contrib = keys.map(k => (bySev[k] || 0) * (p.severity_weights ? p.severity_weights[k] : 0));
  charts.contrib = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: keys,
      datasets: [{
        label: 'Posture penalty',
        data: contrib,
        backgroundColor: keys.map(k => SEV_COLORS[k]),
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { color: chartStyle().dim }, grid: { color: chartStyle().grid } },
        y: { ticks: { color: chartStyle().dim } },
      },
    },
  });

  // remediation checklist
  const sevs = bySev;
  const items = [
    { t: 'No CRITICAL findings remaining', done: !(sevs.CRITICAL || 0) },
    { t: 'No HIGH findings remaining', done: !(sevs.HIGH || 0) },
    { t: 'Default-deny rule present', done: r.rules.some(x => x.rule_type === 'DEFAULT_DENY') },
    { t: 'All ALLOW rules log traffic', done: r.rules.filter(x => x.action === 'ALLOW' && x.enabled).every(x => x.log !== undefined ? x.log : true) },
    { t: 'Rule-set smoke-tested after change', done: false },
  ];
  $('#remediationChecklist').innerHTML = items.map(i => `
    <div class="check-item ${i.done ? 'ck-done' : 'ck-pending'}">
      <span class="ck">${i.done ? '✓' : '!'}</span><span>${i.t}</span>
    </div>`).join('');

  const warns = r.meta.warnings || [];
  $('#reportWarnings').innerHTML = warns.length
    ? warns.map(w => `<li>${esc(w)}</li>`).join('')
    : '<li class="ok">No parse warnings.</li>';
}

/* ---------------- formats ---------------- */
async function loadFormats() {
  try {
    const res = await getJSON('/api/formats');
    if (res.body && res.body.ok) {
      state.formats = res.body.data.formats;
      renderFormats();
    }
  } catch (err) {
    setConnOffline();
  }
}
function renderFormats() {
  $('#formatGrid').innerHTML = state.formats.map(f => `
    <div class="fmt-card${f.id === state.format ? ' active' : ''}" data-fmt="${esc(f.id)}">
      <div class="fmt-name">${esc(f.name)}</div>
      <div class="fmt-id">${esc(f.id)}</div>
    </div>`).join('');
  $$('#formatGrid .fmt-card').forEach(el => el.addEventListener('click', () => {
    state.format = el.dataset.fmt;
    renderFormats();
    localStorage.setItem('framc.lastFormat', state.format);
  }));
}

/* ---------------- samples ---------------- */
const SAMPLES = [
  { file: 'samples/iptables.txt', fmt: 'iptables', label: 'iptables' },
  { file: 'samples/cisco_asa.txt', fmt: 'cisco-asa', label: 'Cisco ASA' },
  { file: 'samples/fortigate.txt', fmt: 'fortigate', label: 'FortiGate' },
  { file: 'samples/pfsense.txt', fmt: 'pfsense', label: 'pfSense' },
  { file: 'samples/windows.txt', fmt: 'windows', label: 'Windows' },
  { file: 'samples/paloalto.txt', fmt: 'paloalto', label: 'Palo Alto' },
  { file: 'samples/plain.txt', fmt: 'plain', label: 'Plain table' },
];

async function loadSample(index) {
  const s = SAMPLES[index % SAMPLES.length];
  try {
    const r = await fetch(s.file);
    const text = await r.text();
    $('#configText').value = text;
    state.format = s.fmt;
    $('#configName').value = s.label + ' sample';
    renderFormats();
    $('#analyzeBtn').disabled = false;
    toast(`Loaded ${s.label} sample — ready to analyze`, 'ok');
  } catch (e) {
    toast('Could not load sample from server.', 'error');
  }
}

/* ---------------- analyze interactions ---------------- */
function wireAnalyze() {
  const dz = $('#dropzone'), fi = $('#fileInput'), ta = $('#configText');
  dz.addEventListener('click', () => fi.click());
  fi.addEventListener('change', () => {
    if (fi.files[0]) readFile(fi.files[0]);
  });
  ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => {
    e.preventDefault(); dz.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => {
    e.preventDefault(); dz.classList.remove('dragging');
  }));
  dz.addEventListener('drop', e => {
    if (e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]);
  });
  ta.addEventListener('input', () => {
    $('#analyzeBtn').disabled = !ta.value.trim();
    if (ta.value.trim()) guessFormatFromText(ta.value.trim());
  });
  $('#analyzeBtn').addEventListener('click', () => analyze());
  $('#sampleLink').addEventListener('click', () => loadSample(4));
  $('#loadSample').addEventListener('click', () => { setRoute('analyze'); loadSample(0); });
}

function readFile(file) {
  if (file.size > 2 * 1024 * 1024) { toast('File exceeds the 2 MB limit.', 'error'); return; }
  const reader = new FileReader();
  reader.onload = () => {
    $('#configText').value = String(reader.result || '');
    state.fileName = file.name;
    $('#configName').value = file.name;
    $('#analyzeBtn').disabled = false;
    guessFormatFromText($('#configText').value);
    toast(`Loaded ${file.name}`, 'ok');
  };
  reader.readAsText(file);
}

function guessFormatFromText(text) {
  const t = text.slice(0, 4000);
  let fmt = null;
  if (/access-list\s+\S+\s+(extended\s+)?(permit|deny)/i.test(t)) fmt = 'cisco-asa';
  else if (/^-A\s+\S+/m.test(t) || /^\*filter/m.test(t)) fmt = 'iptables';
  else if (/config\s+firewall\s+policy/i.test(t)) fmt = 'fortigate';
  else if (/<pfsense>|<filter>|<rule>/i.test(t)) fmt = 'pfsense';
  else if (/begin\s+rule[\s\S]*?end\s+rule/i.test(t) || /add\s+rule/i.test(t)) fmt = 'windows';
  else if (/set\s+rulebase\s+security\s+rules/i.test(t)) fmt = 'paloalto';
  if (fmt && fmt !== state.format) {
    state.format = fmt;
    renderFormats();
  }
}

/* ---------------- wiring ---------------- */
function wireNav() {
  $$('.nav-item').forEach(n => n.addEventListener('click', () => setRoute(n.dataset.route)));
  $$('[data-go]').forEach(el => el.addEventListener('click', () => setRoute(el.dataset.go)));

  $('#dashAnalyzeBtn').addEventListener('click', () => setRoute('analyze'));
  $('#dashEmptyGo').addEventListener('click', () => setRoute('analyze'));

  $('#rulesSearch').addEventListener('input', e => { state.rules.search = e.target.value; state.rules.page = 1; renderRules(); });
  $('#rulesFilterAction').addEventListener('change', e => { state.rules.action = e.target.value; state.rules.page = 1; renderRules(); });
  $('#rulesFilterSev').addEventListener('change', e => { state.rules.sev = e.target.value; state.rules.page = 1; renderRules(); });
  $('#rulesPrev').addEventListener('click', () => { state.rules.page--; renderRules(); });
  $('#rulesNext').addEventListener('click', () => { state.rules.page++; renderRules(); });

  $('#findingsSevFilter').addEventListener('change', e => { state.findings.sev = e.target.value; state.findings.shown = 20; renderFindings(); });
  $('#findingsMore').addEventListener('click', () => { state.findings.shown += 20; renderFindings(); });

  // theme
  $$('.ts-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.themeKey === state.theme);
    b.addEventListener('click', () => {
      state.theme = b.dataset.themeKey;
      document.documentElement.setAttribute('data-theme', state.theme);
      localStorage.setItem('framc.theme', state.theme);
      $$('.ts-btn').forEach(x => x.classList.toggle('active', x === b));
      if (hasReport()) renderDashboard();
      if (state.route === 'report') renderReport();
    });
  });

  // export links always point at last report api
  ['exportJson', 'exportRules', 'exportFindings'].forEach(id => {
    const a = $('#' + id);
    a.addEventListener('click', e => {
      if (!state.report) { e.preventDefault(); toast('Run an analysis first.', 'error'); }
    });
  });
}

function connectCheck() {
  getJSON('/api/formats').then(res => {
    const pill = $('#connPill'), label = $('#connLabel');
    if (res.status === 200) {
      pill.className = 'conn-pill ok'; label.textContent = 'engine online';
    } else { setConnOffline(); }
  }).catch(() => setConnOffline());
}

function setConnOffline() {
  const pill = $('#connPill'), label = $('#connLabel');
  if (!pill || !label) return;
  pill.className = 'conn-pill err';
  label.textContent = 'offline';
  toast('Engine unreachable — is the FRAMC server running?', 'error');
}

/* ---------------- loader animation ---------------- */
function animateLoader() {
  const arc = $('#loaderArc');
  if (!arc) return;
  let deg = 0;
  setInterval(() => {
    deg = (deg + 4) % 360;
    arc.setAttribute('stroke-dasharray', `${(deg / 360) * 310} 310`);
  }, 30);
}

/* ---------------- init ---------------- */
async function init() {
  wireNav();
  wireAnalyze();
  animateLoader();
  await loadFormats();
  await connectCheck();

  const lastFmt = localStorage.getItem('framc.lastFormat');
  if (lastFmt && state.formats.some(f => f.id === lastFmt)) {
    state.format = lastFmt;
    renderFormats();
  }

  // restore or empty
  renderAll();
  if (!hasReport()) $('#dashSub').textContent = 'Upload a firewall configuration to begin an audit.';
}

document.addEventListener('DOMContentLoaded', init);

// Safety net: if anything throws, never leave the full-screen loader stuck.
window.addEventListener('error', hideLoader);
window.addEventListener('unhandledrejection', hideLoader);
function hideLoader() {
  const ov = $('#loadingOverlay');
  if (ov) ov.hidden = true;
}