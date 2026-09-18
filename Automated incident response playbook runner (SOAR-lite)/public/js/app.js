'use strict';

/* ============================================================
   SOAR-Lite console — view logic
   ============================================================ */

const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function timeAgo(iso) {
  if (!iso) return '—';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return s + 's ago';
  const m = Math.floor(s / 60);
  if (m < 60) return m + 'm ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h / 24) + 'd ago';
}

const COLORS = {
  critical: '#f87171', high: '#fb923c', medium: '#fbbf24', low: '#94a3b8', info: '#60a5fa'
};

const I = {
  play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>',
  dl: '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>',
  redo: '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.76-4.24L13 11h8V3l-3.35 3.35z"/></svg>',
  stop: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
  eye: '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
  edit: '<svg viewBox="0 0 24 24"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>',
  blob: '<svg viewBox="0 0 24 24"><path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3z"/></svg>',
  bolt: '<svg viewBox="0 0 24 24"><path d="M13 2L3 14h8l-1 8 10-12h-8l1-4z"/></svg>',
  inbox: '<svg viewBox="0 0 24 24"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>'
};

/* ------------------------------------------------------------ API */
async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}

/* ------------------------------------------------------------ toast */
function toast(title, msg, type) {
  const root = $('#toastRoot');
  const el = document.createElement('div');
  el.className = 'toast ' + (type || '');
  el.innerHTML = `<div class="tmsg"><b>${esc(title)}</b>${msg ? `<div class="text-dim">${esc(msg)}</div>` : ''}</div><span class="close-ic" data-close>${I.x}</span>`;
  root.appendChild(el);
  const close = () => el.remove();
  $(`[data-close]`, el).onclick = close;
  setTimeout(close, type === 'err' ? 7000 : 4200);
}

/* ------------------------------------------------------------ modal */
function openModal(html, opts) {
  opts = opts || {};
  const root = $('#modalRoot');
  root.innerHTML = `
    <div class="modal-overlay" data-overlay>
      <div class="modal ${opts.wide ? 'wide' : ''}" role="dialog">
        ${html}
      </div>
    </div>`;
  root.querySelectorAll('[data-overlay]').forEach((o) => {
    o.addEventListener('mousedown', (e) => { if (e.target === o) closeModal(); });
  });
  return root.querySelector('.modal');
}

function closeModal() {
  $('#modalRoot').innerHTML = '';
}

function modalHead(title, subtitle) {
  return `<div class="modal-head"><div><h2>${esc(title)}</h2>${subtitle ? `<div class="text-faint" style="font-size:12px">${subtitle}</div>` : ''}</div>
    <button class="icon-btn" data-close-modal>${I.x}</button></div>`;
}

function bindModalClose(el) {
  $$('[data-close-modal]', el).forEach((b) => (b.onclick = closeModal));
}

function downloadUrl(format) {
  const p = new URLSearchParams();
  const r = S.report;
  if (r.from) p.set('from', r.from);
  if (r.to) p.set('to', r.to);
  if (r.severity) p.set('severity', r.severity);
  if (r.category) p.set('category', r.category);
  if (r.status) p.set('status', r.status);
  if (r.playbookId) p.set('playbookId', r.playbookId);
  return `/api/report-download?format=${format}&` + p.toString();
}

function triggerDownload(url, name) {
  const a = document.createElement('a');
  a.href = url;
  a.download = name || '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/* ------------------------------------------------------------ state */
const S = {
  tab: 'dashboard',
  incidents: [],
  playbooks: [],
  runs: [],
  report: { format: 'html', from: '', to: '', severity: '', category: '', status: '', playbookId: '' },
  reportOptions: null,
  openRunLogs: new Set(),
  runningCount: 0
};

/* ------------------------------------------------------------ tabs */
function switchTab(name) {
  S.tab = name;
  $$('#tabs .tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
  $$('.panel').forEach((p) => p.classList.toggle('active', p.id === 'panel-' + name));
  const loaders = { dashboard: loadDashboard, playbooks: loadPlaybooks, incidents: loadIncidents, automation: loadAutomation, reports: loadReports, docs: loadDocs };
  loaders[name]();
}

/* ------------------------------------------------------------ init */
function init() {
  $$('#tabs .tab').forEach((t) => (t.onclick = () => switchTab(t.dataset.tab)));
  $('#btnIngest').onclick = ingestIncident;
  $('#btnIngestDash').onclick = ingestIncident;
  $('#btnNewPlaybook').onclick = () => playbookEditor(null);
  $('#btnRefreshRuns').onclick = loadAutomation;
  $('#runScope').onchange = loadAutomation;

  setInterval(updateClock, 1000);
  setInterval(poll, 1800);
  switchTab('dashboard');
}

function updateClock() {
  const c = $('#clock');
  if (c) c.textContent = new Date().toLocaleTimeString();
}

async function ingestIncident() {
  try {
    await api('POST', '/api/incidents/ingest');
    toast('Incident ingested', 'Sent to intake pipeline. Auto-run configured accordingly.', 'ok');
    refreshAll();
  } catch (e) { toast('Ingest failed', e.message, 'err'); }
}

async function refreshAll() {
  loadDashboard(); loadPlaybooks(); loadIncidents();
  if (S.tab === 'automation') loadAutomation();
  poll();
}

/* ------------------------------------------------------------ poll */
async function poll() {
  try {
    const health = await api('GET', '/api/health');
    const pill = $('#enginePill');
    const online = health.engine === 'online';
    pill.classList.toggle('online', online);
    pill.title = 'Playbook engine: ' + health.engine + (health.autoRun ? ' · auto-run enabled' : ' · auto-run off');
    $('#engineLabel').textContent = online ? 'Engine Online' : 'Engine Paused';

    const runs = await api('GET', '/api/runs');
    const active = runs.data || [];
    S.runningCount = active.length;
    const badge = $('#runningBadge');
    badge.hidden = active.length === 0;
    badge.textContent = active.length;

    if (S.tab === 'automation') {
      const scopeAll = $('#runScope').value === 'all';
      const need = scopeAll ? 'all' : 'active';
      loadAutomation(need);
    }
  } catch (e) { /* server temporarily unreachable */ }
}

/* ------------------------------------------------------------ DASHBOARD */
async function loadDashboard() {
  const body = $('#dashboardBody');
  body.className = 'loading';
  body.textContent = 'Loading dashboard…';
  try {
    const { data: st } = await api('GET', '/api/stats');
    const i = st.incidents, r = st.runs;
    const sevSegs = Object.entries(i.bySeverity).map(([sev, value]) => ({ value, color: COLORS[sev] || '#94a3b8', label: sev }));

    const maxEv = Math.max(1, ...i.trend.map((t) => t.events));
    const trendBars = i.trend.map((t) => `
      <div class="vbar" title="${esc(t.date)} — ${t.events} event(s)">
        <div class="v" style="--h:${Math.round((t.events / maxEv) * 100)}%">
          <div class="bar" style="height:${Math.round((t.events / maxEv) * 100)}%"></div>
        </div>
        <div class="vl">${esc(t.label)}</div>
      </div>`).join('');

    const maxPb = Math.max(1, ...r.playbookBar.map((p) => p.count));
    const pbBars = r.playbookBar.map((p) => `
      <div class="hbar" title="${esc(p.name)}">
        <div class="hn">${esc(p.name)}</div>
        <div class="ht"><div class="hf" style="width:${Math.round((p.count / maxPb) * 100)}%"></div></div>
        <div class="hv">${p.count}</div>
      </div>`).join('');

    const runRows = (await api('GET', '/api/runs?all=1')).data.slice(0, 6);

    const badgeCount = (sev, n, nm) => n ? `${sev} × ${n}` : `${sev} —`;

    body.innerHTML = `
      <div class="cards">
        ${statCard('Total incidents', i.total, `${i.byCategory && Object.keys(i.byCategory).length} categories`, 'acc-blue')}
        ${statCard('Open & in progress', i.open, `${i.critical} critical · ${i.high} high`, 'acc-amber')}
        ${statCard('Resolved', i.resolved, `${i.resolvedRate}% resolution rate`, 'acc-green')}
        ${statCard('Playbook runs', r.total, `${r.successRate}% success`, 'acc-accent')}
        ${statCard('Runs running', r.running, `${r.auto} auto · ${r.manual} manual`, 'acc-accent')}
        ${statCard('Active playbooks', st.playbooks.active, `of ${st.playbooks.total} total`, 'acc-blue')}
      </div>

      <div class="grid-2">
        <div class="card">
          <h3>Incident severity <span class="hint">queue distribution</span></h3>
          <div class="donut-wrap">
            ${donut(sevSegs, i.total)}
            <div class="donut-legend">
              ${Object.entries(i.bySeverity).map(([sev, n]) => `
                <div class="lg-row"><span class="lg-label"><span class="lg-dot" style="background:${COLORS[sev]}"></span>${sev}</span>
                <span class="lg-val">${n}</span></div>`).join('')}
            </div>
          </div>
        </div>
        <div class="card">
          <h3>Incident trend <span class="hint">last 14 days</span></h3>
          <div class="vbars">${trendBars}</div>
          <div class="text-faint" style="font-size:11px;margin-top:8px">Ingestions per day (incidents created)</div>
        </div>
      </div>

      <div class="grid-2-1">
        <div>
          <div class="card" style="margin-bottom:18px">
            <h3>Playbook runs <span class="hint">by playbook</span></h3>
            ${pbBars || '<p class="text-faint">No runs recorded yet.</p>'}
          </div>
          <div class="card">
            <h3>Recent executions</h3>
            <div class="table-wrap">${runsTable(runRows, true)}</div>
          </div>
        </div>
        <div class="card">
          <h3>Activity feed</h3>
          <div class="feed">${st.activity.map(feedItem).join('') || '<p class="text-faint">No activity yet.</p>'}</div>
        </div>
      </div>`;
    body.className = '';
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load dashboard: ' + esc(e.message);
  }
}

function statCard(val, lbl, sub, accent) {
  return `<div class="stat-card ${accent || ''}"><div class="stat-val">${val}</div><div class="stat-lbl">${lbl}</div>${sub ? `<div class="stat-sub">${sub}</div>` : ''}</div>`;
}

function donut(segments, total) {
  const size = 168, stroke = 20;
  const r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const sum = segments.reduce((a, s) => a + s.value, 0) || 1;
  let off = 0;
  let circ = `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="#1a2340" stroke-width="${stroke}"/>`;
  segments.forEach((s) => {
    if (!s.value) return;
    const len = (s.value / sum) * c;
    circ += `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${stroke}"
      stroke-linecap="butt" transform="rotate(${(off / c) * 360 - 90} ${size / 2} ${size / 2})"
      stroke-dasharray="${len} ${c - len}"/>`;
    off += len;
  });
  circ += `<text x="50%" y="47%" text-anchor="middle" fill="#e6ecf7" font-size="30" font-weight="800">${total}</text>
    <text x="50%" y="58%" text-anchor="middle" fill="#6b7897" font-size="10" letter-spacing="1">INCIDENTS</text>`;
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">${circ}</svg>`;
}

function feedItem(a) {
  const ic = a.type === 'incident' ? 'incident' : (a.type === 'run' ? 'run' : 'playbook');
  const icv = a.type === 'incident' ? I.blob : (a.type === 'run' ? I.bolt : I.check);
  return `<div class="feed-item"><div class="feed-ic ${ic}">${icv}</div>
    <div style="flex:1;min-width:0"><div class="feed-title">${esc(a.title)}</div>
    <div class="feed-detail">${esc(a.detail)}</div></div>
    <div class="feed-ts">${timeAgo(a.ts)}</div></div>`;
}

function runsTable(runs, compact) {
  if (!runs || !runs.length) return '<div class="empty-state" style="padding:24px"><b>No runs</b><p>Runs appear here when a playbook executes.</p></div>';
  return `<table class="data-table">
    <thead><tr><th>Run</th><th>Playbook</th><th>Trigger</th><th>Status</th><th>Steps</th><th>When</th></tr></thead>
    <tbody>${runs.map((r) => `
      <tr class="clickable" data-open-run="${r.id}">
        <td class="mono">${esc(r.id)}</td>
        <td><div class="tl">${esc(r.playbookName)}</div><div class="sub">${esc(r.incidentTitle || 'no incident')}</div></td>
        <td><span class="tag ${r.trigger === 'auto' ? 'acc' : 'mut'}">${r.trigger}</span></td>
        <td><span class="pill st-${r.status}">${r.status.replace('_', ' ')}</span></td>
        <td class="mono">${r.steps.length}</td>
        <td class="text-faint">${timeAgo(r.startedAt || r.finishedAt)}</td>
      </tr>`).join('')}</tbody></table>`;
}

/* ------------------------------------------------------------ PLAYBOOKS */
async function loadPlaybooks() {
  const body = $('#playbooksBody');
  body.className = 'loading';
  body.textContent = 'Loading playbooks…';
  try {
    const { data: pbs } = await api('GET', '/api/playbooks');
    S.playbooks = pbs;
    body.className = '';
    body.innerHTML = pbs.length ? `
      <div class="pb-grid">${pbs.map(pbCard).join('')}</div>` :
      `<div class="empty-state">${I.blob}<b>No playbooks yet</b><p>Create your first automated playbook to get started.</p>
       <button class="btn primary" data-action="new-playbook" style="margin-top:12px">${I.plus} Create playbook</button></div>`;
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load playbooks: ' + esc(e.message);
  }
}

function pbCard(pb) {
  const sev = pb.severityMin ? `<span class="pill sev-${pb.severityMin}">min ${pb.severityMin}</span>` : '';
  return `
  <div class="pb-card ${pb.active ? '' : 'off'}">
    <div class="pb-head">
      <div>
        <div class="pb-name">${esc(pb.name)}</div>
        <div class="pb-meta" style="margin-top:5px">
          <span class="tag acc">${esc(pb.category)}</span>
          <span class="tag">v${pb.version}</span>
          <span class="tag">${esc(pb.errorPolicy)}</span>
          <span class="pill ${pb.active ? 'st-active' : 'st-pending'}">${pb.active ? 'active' : 'draft'}</span>
        </div>
      </div>
      <label class="switch" title="Toggle active">
        <input type="checkbox" ${pb.active ? 'checked' : ''} data-action="toggle-pb" data-id="${esc(pb.id)}">
        <span class="sl"></span>
      </label>
    </div>
    <div class="pb-desc">${esc(pb.description || 'No description.')}</div>
    <div class="steps-preview">${pb.steps.map((s) => `<span class="step-chip"><span class="sdot"></span>${esc(s.type)}</span>`).join('')}</div>
    <div class="pb-meta">${pb.steps.length} steps · ${pb.tags.map((t) => `${esc(t)}`).join(' · ')} · updated ${timeAgo(pb.updatedAt)}</div>
    <div class="pb-foot">
      <span class="pb-meta"><b>${pb.postAction ? 'auto-resolves incident' : 'manual closure'}</b></span>
      <div class="pb-actions">
        <button class="btn primary small" data-action="run-pb" data-id="${esc(pb.id)}">${I.play} Run</button>
        <button class="btn small" data-action="view-pb" data-id="${esc(pb.id)}">${I.eye} View</button>
        <button class="icon-btn" data-action="edit-pb" data-id="${esc(pb.id)}" title="Edit">${I.edit}</button>
        <button class="icon-btn" data-action="del-pb" data-id="${esc(pb.id)}" title="Delete">${I.trash}</button>
      </div>
    </div>
  </div>`;
}

function playbookEditor(pb) {
  const isNew = !pb;
  pb = pb || { name: '', description: '', category: 'generic', severityMin: 'medium', errorPolicy: 'stop', active: true, tags: [], steps: [{ id: 's1', type: 'notify', name: 'Notify SOC channel', params: { channel: 'slack-soc' } }] };
  const modal = openModal(modalHead(isNew ? 'New playbook' : 'Edit playbook', isNew ? 'Define an automated response flow.' : pb.id + ' · v' + (pb.version || 1)) + `
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group full"><label>Playbook name</label><input class="field" id="f-name" value="${esc(pb.name)}" style="width:100%" placeholder="e.g. Ransomware containment"></div>
        <div class="form-group full"><label>Description</label><input class="field" id="f-desc" value="${esc(pb.description)}" style="width:100%" placeholder="What does this playbook automate?"></div>
        <div class="form-group"><label>Category</label>
          <select class="field" id="f-cat" style="width:100%">${['phishing', 'malware', 'account', 'network', 'data-exfil', 'brute-force', 'insider', 'generic'].map((c) => `<option ${pb.category === c ? 'selected' : ''}>${c}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Minimum severity</label>
          <select class="field" id="f-sev" style="width:100%">${['low', 'medium', 'high', 'critical'].map((s) => `<option ${pb.severityMin === s ? 'selected' : ''}>${s}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Error policy</label>
          <select class="field" id="f-err" style="width:100%">
            <option value="stop" ${pb.errorPolicy === 'stop' ? 'selected' : ''}>stop — halt run</option>
            <option value="continue" ${pb.errorPolicy === 'continue' ? 'selected' : ''}>continue — mark &amp; proceed</option>
            <option value="abort-incident" ${pb.errorPolicy === 'abort-incident' ? 'selected' : ''}>abort-incident — flag case</option>
          </select>
        </div>
        <div class="form-group"><label>Active</label>
          <select class="field" id="f-act" style="width:100%">
            <option value="1" ${pb.active ? 'selected' : ''}>Yes — matchable</option>
            <option value="0" ${!pb.active ? 'selected' : ''}>No — draft</option>
          </select>
        </div>
        <div class="form-group"><label>Tags (comma separated)</label><input class="field" id="f-tags" value="${esc((pb.tags || []).join(', '))}" style="width:100%"></div>
      </div>

      <div class="section-title">Steps</div>
      <div id="stepEditor">${StepEditors(pb.steps)}</div>
      <button class="btn small" id="addStepBtn" style="margin-top:8px">${I.plus} Add step</button>
    </div>
    <div class="modal-foot">
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn primary" id="savePbBtn">${I.check} ${isNew ? 'Create playbook' : 'Save changes'}</button>
    </div>`);
  bindModalClose(modal);

  let stepSeq = pb.steps.length;
  $('#addStepBtn').onclick = () => {
    stepSeq++;
    $('#stepEditor').insertAdjacentHTML('beforeend', stepEditorRow({ id: 's' + (stepSeq), type: 'notify', name: 'New step', params: {} }, stepSeq));
    bindRemovals();
  };
  bindRemovals();

  $('#savePbBtn').onclick = async () => {
    const steps = collectSteps();
    if (!steps) return;
    if (!steps.length) return toast('Playbook requires steps', 'Add at least one step.', 'err');
    const payload = {
      name: $('#f-name').value.trim(),
      description: $('#f-desc').value.trim(),
      category: $('#f-cat').value,
      severityMin: $('#f-sev').value,
      errorPolicy: $('#f-err').value,
      active: $('#f-act').value === '1',
      tags: $('#f-tags').value.split(',').map((t) => t.trim()).filter(Boolean),
      steps
    };
    try {
      if (isNew) await api('POST', '/api/playbooks', payload);
      else await api('PUT', '/api/playbooks/' + pb.id, payload);
      closeModal();
      toast(isNew ? 'Playbook created' : 'Playbook updated', payload.name, 'ok');
      refreshAll();
    } catch (e) { toast('Save failed', e.message, 'err'); }
  };
}

function StepEditors(steps) {
  return steps.map((s, i) => stepEditorRow(s, i + 1)).join('');
}

function stepEditorRow(s, num) {
  const PARAMS_PRESET = {
    notify: '{ "channel": "slack-soc", "targets": "soc-team" }',
    enrich: '{ "source": "threat-intel", "field": "ip" }',
    extract: '{ "fields": "IOC_IP,IOC_DOMAIN,IOC_HASH" }',
    quarantine: '{ "host": "endpoint-host", "action": "network-isolate" }',
    block: '{ "device": "ngfw-edge", "ioc": "domain,ip" }',
    collect: '{ "target": "edr-fleet,syslog" }',
    command: '{ "host": "target-host", "cmd": "collect-artifacts" }',
    decision: '{ "field": "reputation", "op": "eq", "value": "malicious", "branch": { "match": "s2", "noMatch": "s3" } }',
    escalate: '{ "priority": "high", "assignee": "on-call" }',
    wait: '{ "ms": 800 }',
    resolve: '{ "note": "Closed by playbook." }'
  };
  const paramsVal = s.params && Object.keys(s.params).length ? JSON.stringify(s.params, null, 0) : PARAMS_PRESET[s.type] || '{}';
  return `<div class="step-ed-row" data-step-id="${esc(s.id)}">
    <span class="idx">${num}</span>
    <select class="field" data-step-type>
      ${Object.keys(PARAMS_PRESET).map((t) => `<option ${s.type === t ? 'selected' : ''}>${t}</option>`).join('')}
    </select>
    <input class="field" data-step-name value="${esc(s.name)}" placeholder="Step name">
    <input class="field" data-step-params value='${esc(paramsVal)}' placeholder='{ "param": "value" }' title="JSON params">
    <button class="icon-btn remove" data-step-remove title="Remove step">${I.trash}</button>
  </div>`;
}

function bindRemovals() {
  $$('[data-step-remove]').forEach((b) => {
    b.onclick = () => b.closest('.step-ed-row').remove();
  });
}

function collectSteps() {
  const rows = $$('#stepEditor .step-ed-row');
  let valid = true;
  const steps = rows.map((row, i) => {
    let params;
    try {
      params = JSON.parse($('[data-step-params]', row).value || '{}');
    } catch (e) {
      valid = false;
      toast('Invalid JSON in step ' + (i + 1), e.message, 'err');
      return null;
    }
    return {
      id: row.dataset.stepId || 's' + (i + 1),
      type: $('[data-step-type]', row).value,
      name: $('[data-step-name]', row).value || $('[data-step-type]', row).value,
      params
    };
  });
  return valid ? steps : null;
}

function viewPlaybook(pb) {
  const modal = openModal(modalHead(pb.name, pb.id + ' · v' + (pb.version || 1) + ' · ' + pb.steps.length + ' steps') + `
    <div class="modal-body">
      <p class="text-dim" style="margin-bottom:14px">${esc(pb.description || 'No description.')}</p>
      <div class="kv" style="margin-bottom:18px">
        <dt>Category</dt><dd>${esc(pb.category)}</dd>
        <dt>Min severity</dt><dd>${esc(pb.severityMin)}</dd>
        <dt>Error policy</dt><dd>${esc(pb.errorPolicy)}</dd>
        <dt>Status</dt><dd>${pb.active ? 'Active (matchable)' : 'Draft'}</dd>
        ${pb.postAction ? '<dt>Post-action</dt><dd>Auto-resolve incident on success</dd>' : ''}
        <dt>Created</dt><dd class="mono">${esc(pb.createdAt)}</dd>
      </div>
      <div class="section-title">Execution plan</div>
      ${pb.steps.map((s, i) => `
        <div class="step-line" style="margin-bottom:8px">
          <span class="sic">${i + 1}</span>
          <span class="sname"><b>${esc(s.name)}</b> <span class="tag mut">${esc(s.type)}</span></span>
        </div>`).join('')}
    </div>
    <div class="modal-foot">
      <button class="btn" data-close-modal>Close</button>
      <button class="btn primary" data-action="run-pb" data-id="${esc(pb.id)}">${I.play} Run playbook</button>
    </div>`, { wide: true });
  bindModalClose(modal);
}

function runPlaybookChooser(pb) {
  const opts = S.incidents.slice(0, 20);
  const modal = openModal(modalHead('Run playbook', pb.name + ' — choose the target incident (or none)') + `
    <div class="modal-body">
      <div class="empty-state" style="padding:20px 0">
        <button class="btn" data-action="run-empty" data-id="${esc(pb.id)}" data-inc="">${I.bolt} Run without an incident</button>
        <p style="margin-top:8px">Executes the playbook standalone (not attached to a case).</p>
      </div>
      <div class="section-title">Against an incident</div>
      <div class="table-wrap" style="max-height:320px;overflow-y:auto">
        <table class="data-table"><thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th></tr></thead>
        <tbody>${opts.map((inc) => `
          <tr class="clickable" data-action="run-inc" data-id="${esc(pb.id)}" data-inc="${esc(inc.id)}">
            <td class="mono">${esc(inc.id)}</td>
            <td>${esc(inc.title)}</td>
            <td><span class="pill sev-${inc.severity}">${inc.severity}</span></td>
            <td><span class="pill st-${inc.status}">${inc.status}</span></td>
          </tr>`).join('')}
        </tbody></table>
      </div>
    </div>
    <div class="modal-foot"><button class="btn" data-close-modal>Cancel</button></div>`, { wide: true });
  bindModalClose(modal);
}

async function doRun(pbId, incidentId) {
  try {
    const { data: run } = await api('POST', `/api/playbooks/${pbId}/run`, { incidentId });
    closeModal();
    toast('Playbook started', run.playbookName + ' · ' + run.id, 'ok');
    switchTab('automation');
  } catch (e) { toast('Could not start run', e.message, 'err'); }
}

/* ------------------------------------------------------------ INCIDENTS */
async function loadIncidents() {
  const body = $('#incidentsBody');
  body.className = 'loading';
  body.textContent = 'Loading incidents…';
  try {
    const { data: incs } = await api('GET', '/api/incidents');
    S.incidents = incs;
    populateIncidentFilters(incs);
    body.className = '';
    renderIncidents(body);
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load incidents: ' + esc(e.message);
  }
}

function populateIncidentFilters(incs) {
  const sevs = [...new Set(incs.map((i) => i.severity))];
  const cats = [...new Set(incs.map((i) => i.category))];
  const statuses = [...new Set(incs.map((i) => i.status))];
  const fill = (id, values, label) => {
    const sel = $(id);
    sel.innerHTML = `<option value="">${label}</option>` + values.map((v) => `<option ${sel.value === v ? 'selected' : ''}>${v}</option>`).join('');
  };
  fill('#incSevFilter', sevs, 'All severities');
  fill('#incStatusFilter', statuses, 'All statuses');
  fill('#incCatFilter', cats, 'All categories');
  ['incSearch', 'incSevFilter', 'incStatusFilter', 'incCatFilter'].forEach((id) => { $(id).onchange = () => renderIncidents(); });
}

function renderIncidents(container) {
  container = container || $('#incidentsBody');
  const q = ($('#incSearch').value || '').toLowerCase();
  const sev = $('#incSevFilter').value;
  const status = $('#incStatusFilter').value;
  const cat = $('#incCatFilter').value;
  const incs = S.incidents.filter((i) => {
    if (sev && i.severity !== sev) return false;
    if (status && i.status !== status) return false;
    if (cat && i.category !== cat) return false;
    if (q) {
      const hay = (i.title + ' ' + i.id + ' ' + (i.assignee || '') + ' ' + (i.artifacts || []).map((a) => a.value).join(' ')).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  container.innerHTML = incs.length ? `
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Incident</th><th>Category</th><th>Severity</th><th>Status</th><th>Artifacts</th><th>Playbook</th><th>Source</th><th>Age</th></tr></thead>
      <tbody>${incs.map((i) => `
        <tr class="clickable" data-open-inc="${esc(i.id)}">
          <td><div class="tl">${esc(i.title)}</div><div class="sub">${esc(i.id)} · ${esc(i.assignee || 'unassigned')}</div></td>
          <td><span class="tag acc">${esc(i.category)}</span></td>
          <td><span class="pill sev-${i.severity}"><span class="pdot"></span>${i.severity}</span></td>
          <td><span class="pill st-${i.status}">${i.status.replace('_', ' ')}</span></td>
          <td class="art">${(i.artifacts || []).slice(0, 2).map((a) => `<span class="tag mut">${esc(a.type)}:${esc(a.value)}</span>`).join('')}${(i.artifacts || []).length > 2 ? `<span class="tag">+${i.artifacts.length - 2}</span>` : ''}</td>
          <td>${i.relatedPlaybook ? `<span class="tag acc">${esc(i.relatedPlaybook)}</span>` : '<span class="text-faint">—</span>'}</td>
          <td class="text-faint">${esc(i.source)}</td>
          <td class="text-faint">${timeAgo(i.createdAt)}</td>
        </tr>`).join('')}</tbody>
    </table></div>
    <div class="text-faint" style="margin-top:8px;font-size:12px">${incs.length} incident(s) shown · click a row for full detail</div>`
    : `<div class="empty-state">${I.blob}<b>No incidents match</b><p>Adjust filters or ingest a new incident.</p></div>`;
}

function openIncident(id) {
  const inc = S.incidents.find((x) => x.id === id);
  if (!inc) return;
  const modal = openModal(modalHead(inc.title, inc.id + ' · ' + inc.source) + `
    <div class="modal-body">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <span class="pill sev-${inc.severity}"><span class="pdot"></span>${inc.severity}</span>
        <span class="pill st-${inc.status}">${inc.status.replace('_', ' ')}</span>
        <span class="tag acc">${esc(inc.category)}</span>
        ${inc.relatedPlaybook ? `<span class="tag">matched ${esc(inc.relatedPlaybook)}</span>` : ''}
      </div>
      <p class="text-dim" style="margin-bottom:14px">${esc(inc.description || 'No description.')}</p>
      <div class="kv" style="margin:0 0 16px">
        <dt>Assignee</dt><dd>${esc(inc.assignee || 'unassigned')}</dd>
        <dt>Created</dt><dd class="mono">${esc(inc.createdAt)}</dd>
        <dt>Last update</dt><dd class="mono">${esc(inc.updatedAt)}</dd>
        ${inc.resolutionNote ? '<dt>Resolution</dt><dd>' + esc(inc.resolutionNote) + '</dd>' : ''}
        ${inc.flag ? '<dt style="color:var(--red)">Flag</dt><dd style="color:var(--red)">' + esc(inc.flag) + '</dd>' : ''}
      </div>
      <div class="section-title">Artifacts / IoCs</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">
        ${(inc.artifacts || []).map((a) => `<span class="tag">${esc(a.type)} <b>${esc(a.value)}</b></span>`).join('') || '<span class="text-faint">No artifacts.</span>'}
      </div>
      <div class="section-title">Update case</div>
      <div class="form-grid">
        <div class="form-group"><label>Severity</label><select class="field" id="d-sev" style="width:100%">${['critical', 'high', 'medium', 'low', 'info'].map((s) => `<option ${inc.severity === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div>
        <div class="form-group"><label>Status</label><select class="field" id="d-status" style="width:100%">${['new', 'open', 'in_progress', 'resolved', 'closed'].map((s) => `<option ${inc.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div>
        <div class="form-group"><label>Assignee</label><input class="field" id="d-assignee" value="${esc(inc.assignee || '')}" style="width:100%"></div>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn danger" data-del-inc="${inc.id}">${I.trash} Delete</button>
      <span style="flex:1"></span>
      <button class="btn" data-action="run-inc-any" data-id="${inc.id}">${I.play} Run playbook</button>
      <button class="btn primary" data-save-inc="${inc.id}">${I.check} Save case</button>
    </div>`, { wide: true });
  bindModalClose(modal);

  const saveBtn = $('[data-save-inc="' + id + '"]', modal);
  saveBtn.onclick = async () => {
    try {
      await api('PUT', '/api/incidents/' + id, { severity: $('#d-sev').value, status: $('#d-status').value, assignee: $('#d-assignee').value });
      closeModal();
      toast('Case updated', inc.id, 'ok');
      refreshAll();
    } catch (e) { toast('Update failed', e.message, 'err'); }
  };
  $('[data-del-inc="' + id + '"]', modal).onclick = async () => {
    if (!confirm('Delete incident ' + id + '?')) return;
    try { await api('DELETE', '/api/incidents/' + id); closeModal(); toast('Incident deleted', id, 'ok'); refreshAll(); }
    catch (e) { toast('Delete failed', e.message, 'err'); }
  };
  $('[data-action="run-inc-any"]', modal).onclick = () => {
    runPlaybookOnIncident(id);
  };
}

async function runPlaybookOnIncident(incidentId) {
  const pbs = S.playbooks;
  const modal = openModal(modalHead('Run playbook against incident', incidentId) + `
    <div class="modal-body">
      ${pbs.length ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Playbook</th><th>Category</th><th>Status</th><th>Steps</th></tr></thead>
        <tbody>${pbs.map((p) => `
          <tr class="clickable" data-pb-run data-pid="${esc(p.id)}" ${p.active ? '' : 'style="opacity:.5"'}>
            <td><b>${esc(p.name)}</b></td>
            <td><span class="tag acc">${esc(p.category)}</span></td>
            <td><span class="pill ${p.active ? 'st-active' : 'st-pending'}">${p.active ? 'active' : 'draft'}</span></td>
            <td class="mono">${p.steps.length}</td>
          </tr>`).join('')}</tbody></table></div>`
      : '<p class="text-faint">No playbooks defined yet.</p>'}
    </div>
    <div class="modal-foot"><button class="btn" data-close-modal>Cancel</button></div>`, { wide: true });
  bindModalClose(modal);
  $$('[data-pb-run]', modal).forEach((row) => {
    row.onclick = () => doRun(row.dataset.pid, incidentId);
  });
}

/* ------------------------------------------------------------ AUTOMATION */
async function loadAutomation(forceScope) {
  const body = $('#automationBody');
  const scope = forceScope || ($('#runScope') ? $('#runScope').value : 'active');
  body.className = 'loading';
  body.textContent = 'Loading runs…';
  try {
    const url = scope === 'all' ? '/api/runs?all=1' : '/api/runs';
    const { data: runs } = await api('GET', url);
    const { data: settings } = await api('GET', '/api/settings');
    S.runs = runs;
    body.className = '';
    body.innerHTML = `
      <div class="card" style="margin-bottom:20px">
        <h3>Engine &amp; automation settings <span class="hint">live controls</span></h3>
        <div class="form-grid">
          <div class="form-group"><label>Engine status</label>
            <select class="field" id="set-status" style="width:100%">
              <option value="online" ${settings.engineStatus === 'online' ? 'selected' : ''}>Online — accepting runs</option>
              <option value="paused" ${settings.engineStatus === 'paused' ? 'selected' : ''}>Paused — reject new runs</option>
            </select></div>
          <div class="form-group"><label>Auto-run on ingest</label>
            <div style="display:flex;align-items:center;gap:10px;padding-top:6px">
              <label class="switch"><input type="checkbox" id="set-autorun" ${settings.autoRun ? 'checked' : ''}><span class="sl"></span></label>
              <span class="text-dim">match playbook by severity &amp; category</span>
            </div></div>
          <div class="form-group"><label>Webhook URL (integration)</label><input class="field" id="set-webhook" value="${esc(settings.webhookUrl || '')}" style="width:100%" placeholder="https://hook…"></div>
          <div class="form-group"><label>Operator</label><input class="field" id="set-operator" value="${esc(settings.operator || '')}" style="width:100%"></div>
        </div>
        <div style="margin-top:14px;display:flex;justify-content:flex-end"><button class="btn primary" id="saveSettingsBtn">${I.check} Save settings</button></div>
      </div>

      ${runs.length ? runs.map(runCard).join('') :
        `<div class="empty-state">${I.bolt}<b>No runs in this view</b><p>Start a playbook from the Playbooks tab — or ingest an incident with auto-run enabled.</p></div>`}`;
    $('#saveSettingsBtn').onclick = async () => {
      try {
        await api('POST', '/api/settings', {
          engineStatus: $('#set-status').value,
          autoRun: $('#set-autorun').checked,
          webhookUrl: $('#set-webhook').value,
          operator: $('#set-operator').value
        });
        toast('Settings saved', 'Engine: ' + $('#set-status').value, 'ok');
        poll();
        if (S.tab === 'automation') loadAutomation();
      } catch (e) { toast('Save failed', e.message, 'err'); }
    };
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load runs: ' + esc(e.message);
  }
}

function runCard(run) {
  const done = run.steps.filter((s) => s.status === 'success').length;
  const failed = run.steps.filter((s) => s.status === 'failed').length;
  const total = run.steps.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  const active = run.status === 'running' || run.status === 'queued';
  const fillClass = run.status === 'failed' || run.status === 'error' ? 'bad' : (run.status === 'success' || run.status === 'success_with_warnings' ? 'full' : 'running');
  const showLogs = S.openRunLogs.has(run.id);

  return `<div class="run-item ${active ? 'running' : ''}" id="run-${run.id}">
    <div class="run-head">
      ${active ? '<div class="spinner"></div>' : `<div class="step-line done" style="gap:6px"><span class="sic">${I.check}</span></div>`}
      <div class="run-progress">
        <div class="run-title">${esc(run.playbookName)} <span class="tag ${run.trigger === 'auto' ? 'acc' : 'mut'}">${run.trigger}</span></div>
        <div class="run-meta">
          <span class="mono">${esc(run.id)}</span>
          <span>·</span>
          <span>${esc(run.incidentTitle || 'no incident')}</span>
          <span class="pill st-${run.status}">${run.status.replace('_', ' ')}</span>
          <span>· started ${timeAgo(run.startedAt)}</span>
        </div>
        <div class="progress-track"><div class="progress-fill ${fillClass}" style="width:${active ? Math.max(pct, 4) : pct}%"></div></div>
      </div>
      <div style="display:flex;gap:6px">
        <button class="btn small" data-toggle-logs="${run.id}">${showLogs ? 'Hide logs' : 'Logs (' + run.logs.length + ')'}</button>
        ${active ? `<button class="btn small danger" data-cancel-run="${run.id}">${I.stop} Cancel</button>` : ''}
        ${(run.status === 'failed' || run.status === 'error') ? `<button class="btn small" data-retry-run="${run.id}">${I.redo} Retry</button>` : ''}
      </div>
    </div>
    <div class="run-steps">${run.steps.map((s, i) => stepLine(s, i)).join('')}</div>
    ${showLogs ? `<div class="log-console">${run.logs.map(logLine).join('') || '<span class="text-faint">No log entries.</span>'}</div>` : ''}
  </div>`;
}

function stepLine(s, i) {
  const cls = s.status === 'success' ? 'done' : (s.status === 'failed' ? 'err' : (s.status === 'running' ? '' : 'pending'));
  const right = s.status === 'running'
    ? '<div class="spinner" style="width:11px;height:11px;border-width:2px"></div>'
    : (s.status === 'success' ? `<span class="sdur">${s.duration ? s.duration + 'ms' : 'done'}</span>` : (s.error ? `<span class="sdur" style="color:var(--red)">✗</span>` : ''));
  return `<div class="step-line ${cls}">
    <span class="sic">${i + 1}</span>
    <span class="sname">${esc(s.name)} <span class="tag mut">${esc(s.type)}</span></span>
    ${s.error ? `<span class="text-faint" style="font-size:11px;color:var(--red)">${esc(s.error)}</span>` : ''}
    ${right}
  </div>`;
}

function logLine(l) {
  return `<div class="log-line ${esc(l.l)}"><span class="lt">${fmtTime(l.t)}</span><span class="chev">›</span> ${esc(l.m)}</div>`;
}

async function openRunDetail(id) {
  try {
    const { data: run } = await api('GET', '/api/runs/' + id);
    S.activeRunId = id;
    S.openRunLogs.add(id);
    const modal = openModal(modalHead(run.playbookName, run.id + ' · ' + (run.incidentTitle || run.playbookName)) + `
      <div class="modal-body">
        <div class="run-meta" style="margin-bottom:14px">
          <span class="pill st-${run.status}">${run.status}</span>
          <span>${run.steps.length} steps</span>
          <span>trigger ${run.trigger}</span>
          <span>started ${fmtTime(run.startedAt)}</span>
          ${run.finishedAt ? `<span>finished ${fmtTime(run.finishedAt)}</span>` : ''}
        </div>
        <div class="section-title">Steps</div>
        <div class="run-steps" style="padding:0;border:none">${run.steps.map((s, i) => stepLine(s, i)).join('')}</div>
        <div class="section-title" style="margin-top:18px">Execution log</div>
        <div class="log-console">${run.logs.map(logLine).join('') || '<span class="text-faint">No entries yet.</span>'}</div>
      </div>
      <div class="modal-foot">
        ${(run.status === 'running' || run.status === 'queued') ? `<button class="btn primary" data-dlg-cancel="${run.id}">${I.stop} Cancel run</button>` : ''}
        ${(run.status === 'failed' || run.status === 'error') ? `<button class="btn primary" data-dlg-retry="${run.id}">${I.redo} Retry</button>` : ''}
        <span style="flex:1"></span>
        <button class="btn" data-close-modal>Close</button>
      </div>`, { wide: true });
    bindModalClose(modal);
    const dc = $('[data-dlg-cancel="' + id + '"]', modal);
    if (dc) dc.onclick = async () => { await api('POST', '/api/runs/' + id + '/cancel'); toast('Cancel requested', id, 'ok'); S.openRunLogs.delete(id); closeModal(); loadAutomation(); };
    const dr = $('[data-dlg-retry="' + id + '"]', modal);
    if (dr) dr.onclick = async () => { try { await api('POST', '/api/runs/' + id + '/retry'); toast('Retrying playbook', run.playbookName, 'ok'); closeModal(); loadAutomation(); } catch (e) { toast('Retry failed', e.message, 'err'); } };
  } catch (e) { toast('Could not open run', e.message, 'err'); }
}

/* ------------------------------------------------------------ REPORTS */
async function loadReports() {
  const body = $('#reportsBody');
  body.className = 'loading';
  body.textContent = 'Loading reports…';
  try {
    const { data: opts } = await api('GET', '/api/report-options');
    S.reportOptions = opts;
    body.className = '';
    body.innerHTML = `
      <div class="report-builder">
        <div class="card">
          <h3>Report builder</h3>
          <div class="builder-form">
            <div>
              <label>Time range</label>
              <div class="row" style="gap:6px">
                <button class="btn small" data-range="7">7d</button>
                <button class="btn small" data-range="30">30d</button>
                <button class="btn small" data-range="90">90d</button>
                <button class="btn small" data-range="0">All</button>
              </div>
              <div class="row" style="gap:6px;margin-top:8px">
                <input class="field" type="date" id="r-from" style="width:47%">
                <input class="field" type="date" id="r-to" style="width:47%">
              </div>
            </div>
            <div>
              <label>Severity</label>
              <select class="field" id="r-sev" style="width:100%"><option value="">All severities</option>
                ${opts.severities.map((s) => `<option>${s}</option>`).join('')}</select>
            </div>
            <div>
              <label>Category</label>
              <select class="field" id="r-cat" style="width:100%"><option value="">All categories</option>
                ${opts.categories.map((c) => `<option>${esc(c)}</option>`).join('')}</select>
            </div>
            <div>
              <label>Status</label>
              <select class="field" id="r-status" style="width:100%"><option value="">All statuses</option>
                ${opts.statuses.map((s) => `<option>${s}</option>`).join('')}</select>
            </div>
            <div>
              <label>Playbook</label>
              <select class="field" id="r-pb" style="width:100%"><option value="">All playbooks</option>
                ${opts.playbooks.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}</select>
            </div>
            <div>
              <label>Format</label>
              <div class="format-opt">${opts.formats.map((f) => `
                <div class="format-chip ${S.report.format === f.id ? 'sel' : ''}" data-format="${f.id}">
                  <span class="fic">${f.id === 'html' ? I.dl : I.blob}</span>
                  <div><div class="fname">${esc(f.label)}</div><div class="fnote">${esc(f.note)}</div></div>
                  ${f.primary ? '<span class="ftag">Primary</span>' : ''}
                </div>`).join('')}</div>
            </div>
            <button class="btn primary" id="btnGenerate" style="justify-content:center">${I.check} Generate &amp; preview report</button>
          </div>
        </div>
        <div id="reportPreview" class="card">
          <h3>Report preview <span class="hint">HTML is the primary download format</span></h3>
          <div class="empty-state" id="reportEmpty">${I.dl}<b>No report generated yet</b>
            <p>Pick filters and format on the left, then generate.<br>Reports are also downloadable directly — HTML, JSON, Markdown or CSV.</p></div>
        </div>
      </div>`;

    $('[data-format]', body).forEach((chip) => {
      chip.onclick = () => {
        $$('[data-format]', body).forEach((c) => c.classList.remove('sel'));
        chip.classList.add('sel');
        S.report.format = chip.dataset.format;
      };
    });
    $$('[data-range]', body).forEach((b) => {
      b.onclick = () => {
        const d = Number(b.dataset.range);
        $('#r-from').value = d ? new Date(Date.now() - d * 86400000).toISOString().slice(0, 10) : '';
        $('#r-to').value = '';
      };
    });
    $('#btnGenerate').onclick = generateReport;
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load reports: ' + esc(e.message);
  }
}

async function generateReport() {
  const btn = $('#btnGenerate');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  try {
    const r = S.report;
    r.from = $('#r-from').value;
    r.to = $('#r-to').value;
    r.severity = $('#r-sev').value;
    r.category = $('#r-cat').value;
    r.status = $('#r-status').value;
    r.playbookId = $('#r-pb').value;

    const q = new URLSearchParams();
    ['from', 'to', 'severity', 'category', 'status', 'playbookId'].forEach((k) => { if (r[k]) q.set(k, r[k]); });
    const { data } = await api('GET', '/api/report?' + q.toString());
    const prev = $('#reportPreview');
    const s = data.summary;
    const formatId = r.format;

    let preview;
    if (formatId === 'html') {
      preview = `<iframe class="preview-frame" sandbox="allow-same-origin" srcdoc="${esc(await fetch('/api/report-download?' + q.toString() + '&format=html').then((x) => x.text()))}"></iframe>`;
    } else {
      const text = await fetch('/api/report-download?' + q.toString() + '&format=' + formatId).then((x) => x.text());
      preview = `<pre class="log-console" style="max-height:620px;white-space:pre-wrap">${esc(text.slice(0, 30000))}</pre>`;
    }

    prev.innerHTML = `
      <h3>Report preview <span class="hint">${esc(s.totalIncidents)} incidents · ${esc(s.totalRuns)} runs · ${esc(s.resolvedRate)}% resolved</span></h3>
      <div class="dl-bar" style="margin-bottom:12px">
        <button class="btn primary" id="dlHtml">${I.dl} Download .html</button>
        <button class="btn" data-format="${r.format}" id="dlCurrent">${I.dl} Download .${r.format}</button>
        <span class="spacer"></span>
        <span class="text-faint" style="font-size:12px">Also: <a href="#" data-dl="json">JSON</a> · <a href="#" data-dl="markdown">MD</a> · <a href="#" data-dl="csv">CSV</a></span>
      </div>
      ${preview}`;
    $('#dlHtml', prev).onclick = () => triggerDownload(downloadUrl('html'), 'soar-report.html');
    $('#dlCurrent', prev).onclick = () => triggerDownload(downloadUrl(r.format), 'soar-report.' + r.format);
    $$('[data-dl]', prev).forEach((a) => {
      a.onclick = (e) => { e.preventDefault(); triggerDownload(downloadUrl(a.dataset.dl), 'soar-report.' + a.dataset.dl); };
    });
    toast('Report generated', s.totalIncidents + ' incidents in scope', 'ok');
  } catch (e) {
    toast('Report generation failed', e.message, 'err');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate & preview report';
  }
}

/* ------------------------------------------------------------ DOCS */
async function loadDocs() {
  const body = $('#docsBody');
  body.className = 'loading';
  body.textContent = 'Loading docs…';
  try {
    const { data: docs } = await api('GET', '/api/docs');
    S.docs = docs;
    body.className = '';
    body.innerHTML = `
      <div class="docs-tabs">${docs.map((d, i) => `<button class="docs-tab ${i === 0 ? 'active' : ''}" data-doc="${d.name}">${d.title}</button>`).join('')}</div>
      <div id="docPaper">${docs[0].rendered}</div>`;
    $$('[data-doc]', body).forEach((btn) => {
      btn.onclick = () => {
        $$('[data-doc]', body).forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const d = S.docs.find((x) => x.name === btn.dataset.doc);
        $('#docPaper').innerHTML = '<div class="doc-paper">' + d.rendered + '</div>';
        $('#docPaper').scrollIntoView({ block: 'start' });
      };
    });
  } catch (e) {
    body.className = 'loading';
    body.textContent = 'Failed to load docs: ' + esc(e.message);
  }
}

/* ------------------------------------------------------------ global actions (delegated) */
document.addEventListener('click', (e) => {
  const t = e.target.closest('[data-action]');
  if (t) {
    const { action, id, inc } = t.dataset;
    if (action === 'toggle-pb') {
      e.preventDefault();
      setTimeout(() => api('POST', `/api/playbooks/${id}/toggle`).then(refreshAll).catch((er) => toast('Toggle failed', er.message, 'err')), 0);
    } else if (action === 'run-pb') {
      const pb = S.playbooks.find((p) => p.id === id);
      if (pb) runPlaybookChooser(pb);
    } else if (action === 'run-empty') {
      doRun(id, '');
    } else if (action === 'run-inc') {
      doRun(id, inc);
    } else if (action === 'view-pb') {
      const pb = S.playbooks.find((p) => p.id === id);
      if (pb) viewPlaybook(pb);
    } else if (action === 'edit-pb') {
      const pb = S.playbooks.find((p) => p.id === id);
      if (pb) playbookEditor(pb);
    } else if (action === 'del-pb') {
      if (confirm('Delete this playbook?')) {
        api('DELETE', '/api/playbooks/' + id).then(() => { toast('Playbook deleted', id, 'ok'); refreshAll(); }).catch((er) => toast('Delete failed', er.message, 'err'));
      }
    } else if (action === 'new-playbook') {
      playbookEditor(null);
    }
  }

  const runRow = e.target.closest('[data-open-run]');
  if (runRow) openRunDetail(runRow.dataset.openRun);

  const incRow = e.target.closest('[data-open-inc]');
  if (incRow) openIncident(incRow.dataset.openInc);

  const toggleLogs = e.target.closest('[data-toggle-logs]');
  if (toggleLogs) {
    const id = toggleLogs.dataset.toggleLogs;
    S.openRunLogs.has(id) ? S.openRunLogs.delete(id) : S.openRunLogs.add(id);
    loadAutomation();
  }

  const cancelRun = e.target.closest('[data-cancel-run]');
  if (cancelRun) {
    api('POST', '/api/runs/' + cancelRun.dataset.cancelRun + '/cancel').then(() => { toast('Cancel requested', cancelRun.dataset.cancelRun, 'ok'); loadAutomation(); }).catch((er) => toast('Error', er.message, 'err'));
  }

  const retryRun = e.target.closest('[data-retry-run]');
  if (retryRun) {
    api('POST', '/api/runs/' + retryRun.dataset.retryRun + '/retry').then(() => { toast('Retrying playbook', 'New run created', 'ok'); loadAutomation(); }).catch((er) => toast('Retry failed', er.message, 'err'));
  }
});

/* ------------------------------------------------------------ boot */
init();