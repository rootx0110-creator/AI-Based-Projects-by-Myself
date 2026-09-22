'use strict';
/* SecuRevealer UI logic */
const $ = (id) => document.getElementById(id);
const SEV_COLOR = { CRITICAL: '#ff4d6d', HIGH: '#ff9f43', MEDIUM: '#f9c74f', LOW: '#4dd0e1' };
const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const esc = (s) => String(s).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>').replace(/"/g, '"');

let picked = [];        // files chosen for the NEXT scan
let lastScanFiles = []; // exact files behind lastReport (for the report button)
let lastReport = null;
let sevFilter = 'ALL';

/* ── tabs ──────────────────────────────────────────────── */
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  $('tab-drop').classList.toggle('hidden', t.dataset.tab !== 'drop');
  $('tab-paste').classList.toggle('hidden', t.dataset.tab !== 'paste');
}));

/* ── file input ────────────────────────────────────────── */
const dz = $('dropzone');
dz.addEventListener('click', () => $('file-input').click());
$('file-input').addEventListener('change', (e) => addFiles([...e.target.files]));
['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); }));
['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('drag'); }));
dz.addEventListener('drop', (e) => addFiles([...e.dataTransfer.files]));

async function addFiles(fileObjs) {
  const MAX = 512 * 1024;
  for (const f of fileObjs.slice(0, 50)) {
    try {
      if (f.name.toLowerCase() === 'package-lock.json' || f.size > MAX) continue;
      picked.push({ name: f.name, content: await f.text() });
    } catch { /* unreadable */ }
  }
  renderPicked();
  if (fileObjs.length) toast(`${fileObjs.length} file(s) added`, 'ok');
}

function renderPicked() {
  $('filelist').innerHTML = picked.map((f, i) =>
    `<span class="file-chip"><b>${esc(f.name)}</b> ${f.content.split('\n').length} ln <span class="rm" data-i="${i}">✕</span></span>`
  ).join('');
  $('filelist').querySelectorAll('.rm').forEach(x => x.addEventListener('click', () => {
    picked.splice(+x.dataset.i, 1); renderPicked();
  }));
}

/* ── scan ──────────────────────────────────────────────── */
$('btn-scan').addEventListener('click', runScan);
$('btn-demo').addEventListener('click', loadDemo);

async function runScan() {
  const isPaste = document.querySelector('.tab.active').dataset.tab === 'paste';
  if (isPaste) {
    const code = $('paste-code').value;
    if (!code.trim()) return toast('Paste some code first', 'err');
    return postScan([{ name: $('paste-name').value.trim() || 'pasted-snippet.js', content: code }], 'pasted snippet');
  }
  if (!picked.length) return toast('Add files or load the demo set first', 'err');
  return postScan(picked, `${picked.length} local file(s)`);
}

async function loadDemo() {
  const names = ['app.js', 'app.py', 'app.php', 'config.env', 'query.sql'];
  try {
    const files = await Promise.all(names.map(async n => ({
      name: n, content: await (await fetch('demo/' + n)).text(),
    })));
    picked = files; renderPicked();
    await postScan(files, 'demo fixture set');
  } catch { toast('Demo files not reachable — run the app via backend/server.js', 'err'); }
}

async function postScan(files, label) {
  const meta = $('scan-meta');
  meta.textContent = 'analyzing ' + label + ' …';
  meta.classList.add('busy');
  $('btn-scan').disabled = true;
  try {
    const res = await fetch('/api/scan', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files }),
    });
    const report = await res.json();
    if (report.error) throw new Error(report.error);
    lastReport = report;
    lastScanFiles = files;
    renderReport(report);
    $('btn-report').disabled = false;
    meta.textContent = `done in ${report.meta.durationMs}ms — ${report.summary.totalFindings} finding(s), ${report.meta.filesScanned} file(s), ${report.meta.linesScanned} lines`;
    meta.classList.remove('busy');
    toast(`Scan complete: ${report.summary.totalFindings} findings, grade ${report.summary.grade}`, 'ok');
  } catch (e) {
    meta.textContent = ''; meta.classList.remove('busy');
    toast('Scan failed: ' + e.message, 'err');
  } finally {
    $('btn-scan').disabled = false;
  }
}

/* ── render ────────────────────────────────────────────── */
function renderReport(r) {
  $('empty').classList.add('hidden');
  $('results').classList.remove('hidden');
  $('s-critical').textContent = r.summary.bySeverity.CRITICAL;
  $('s-high').textContent = r.summary.bySeverity.HIGH;
  $('s-medium').textContent = r.summary.bySeverity.MEDIUM;
  $('s-low').textContent = r.summary.bySeverity.LOW;

  const deg = Math.round((r.summary.riskScore / 100) * 360);
  $('risk-ring').style.background = `conic-gradient(var(--accent) ${deg}deg, #1f2937 0)`;
  $('risk-score').textContent = r.summary.riskScore;

  drawDonut(r.summary.bySeverity);
  renderFindings();
}

function drawDonut(sev) {
  const cv = $('donut'), ctx = cv.getContext('2d');
  const total = Object.values(sev).reduce((a, b) => a + b, 0);
  ctx.clearRect(0, 0, cv.width, cv.height);
  const cx = 75, cy = 75, radius = 49;
  if (!total) {
    ctx.strokeStyle = '#1f2937'; ctx.lineWidth = 18;
    ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke();
    return;
  }
  let angle = -Math.PI / 2;
  for (const k of SEV_ORDER) {
    if (!sev[k]) continue;
    const a = (sev[k] / total) * Math.PI * 2;
    ctx.beginPath(); ctx.strokeStyle = SEV_COLOR[k]; ctx.lineWidth = 18;
    ctx.arc(cx, cy, radius, angle, angle + a); ctx.stroke();
    angle += a;
  }
  ctx.fillStyle = '#e5e7eb'; ctx.font = '700 20px Segoe UI';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(total, cx, cy);
}

function renderFindings() {
  const rows = allFindings(lastReport)
    .filter(f => sevFilter === 'ALL' || f.severity === sevFilter)
    .sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity) || a.line - b.line);

  $('findings-body').innerHTML = rows.length ? rows.map((f, i) => `
    <div class="finding-row" style="--c:${SEV_COLOR[f.severity]}" data-i="${i}">
      <span class="badge ${f.severity}">${f.severity}</span>
      <div class="f-title">
        <b>${esc(f.title)}</b>
        <span class="f-loc">${esc(f.file)} : ${f.line}</span>
      </div>
      <div class="f-tags">
        <span class="tag">${esc(f.ruleId)}</span>
        <span class="tag">${esc(f.cwe)}</span>
        <span class="tag">${esc(f.language)}</span>
      </div>
    </div>`).join('') : '<p style="color:var(--muted)">No findings at this severity.</p>';

  document.querySelectorAll('.finding-row').forEach(el =>
    el.addEventListener('click', () => openViewer(rows[+el.dataset.i])));
}

function allFindings(r) {
  return r.files.flatMap(f => f.findings.map(fd => ({ ...fd, file: f.name })));
}

/* ── code viewer ───────────────────────────────────────── */
function openViewer(f) {
  $('viewer-content').innerHTML = `
    <h3>${esc(f.title)}</h3>
    <div class="sub">${esc(f.file)} : ${f.line}:${f.col} · ${esc(f.ruleId)} · ${esc(f.cwe)} · ${esc(f.owasp)}</div>
    <div class="snippet"><span class="ln hit">${esc(f.snippet) || ' '}</span></div>
    <div class="aiblock why"><h4>Root cause</h4><p>${esc(f.why)}</p></div>
    <div class="aiblock exploit"><h4>Exploitation scenario</h4><p>${esc(f.exploit)}</p></div>
    <div class="aiblock fix"><h4>Suggested fix</h4><pre>${esc(f.fixSnippet)}</pre></div>
    ${f.refs && f.refs.length ? `<div class="refs">🔗 ${f.refs.map(u => `<a href="${esc(u)}" target="_blank">${esc(u)}</a>`).join(' · ')}</div>` : ''}`;
  $('viewer').classList.remove('hidden');
}
$('viewer-close').addEventListener('click', () => $('viewer').classList.add('hidden'));
$('viewer').addEventListener('click', (e) => { if (e.target === $('viewer')) $('viewer').classList.add('hidden'); });

/* ── report download ───────────────────────────────────── */
$('btn-report').addEventListener('click', async () => {
  if (!lastReport) return;
  try {
    const res = await fetch('/api/report', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: lastScanFiles }),
    });
    if (!res.ok) throw new Error('report endpoint failed');
    const blob = await res.blob();
    triggerDownload(blob, 'securevealer-report.html');
    toast('HTML report downloaded', 'ok');
  } catch {
    downloadJson(lastReport);
    toast('Server unreachable — downloaded JSON fallback', 'err');
  }
});

function triggerDownload(blob, filename) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function downloadJson(r) {
  triggerDownload(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' }), 'securevealer-scan.json');
}

/* ── toasts / health ───────────────────────────────────── */
function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('toasts').appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

fetch('/api/health')
  .then(() => { $('health').textContent = '● engine ready'; })
  .catch(() => { $('health').textContent = '● offline'; $('health').className = 'pill err'; });