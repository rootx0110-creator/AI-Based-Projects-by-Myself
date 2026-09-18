'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const store = require('./lib/store');
const seed = require('./lib/seed');
const engine = require('./lib/engine');
const reports = require('./lib/reports');
const { markdownToHtml } = require('./lib/markdown');

const PORT = Number(process.env.PORT) || 8787;
const HOST = '127.0.0.1';
const PUBLIC_DIR = path.join(__dirname, 'public');
const DOCS_DIR = path.join(__dirname, 'docs');

// --------------------------------------------------------------------------- boot
store.storeOrLoad(seed.seed);
const state = store.getState();

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8'
};

// --------------------------------------------------------------------------- helpers
function sendJson(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(body)
  });
  res.end(body);
}

function sendError(res, code, message) {
  sendJson(res, code, { error: message });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > 2 * 1024 * 1024) {
        reject(new Error('Payload too large'));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => {
      if (!chunks.length) return resolve({});
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
      } catch (e) {
        reject(new Error('Invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

function serveStatic(res, filePath) {
  const abs = path.resolve(PUBLIC_DIR, '.' + filePath);
  if (!abs.startsWith(path.resolve(PUBLIC_DIR))) {
    return sendError(res, 403, 'Forbidden');
  }
  fs.readFile(abs, (err, data) => {
    if (err) {
      return sendError(res, 404, 'Not found');
    }
    const ext = path.extname(abs).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Content-Length': data.length
    });
    res.end(data);
  });
}

const json = (o) => JSON.stringify(o);
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// --------------------------------------------------------------------------- simulated connector
const INGEST_POOL = [
  { title: 'Phishing: fake SSO consent page', category: 'phishing', sevs: ['medium', 'high', 'high'] },
  { title: 'Brute-force on VPN gateway', category: 'brute-force', sevs: ['low', 'medium', 'high'] },
  { title: 'Unusual PowerShell execution', category: 'malware', sevs: ['medium', 'high', 'critical'] },
  { title: 'Privileged account reuse alert', category: 'account', sevs: ['medium', 'high', 'high'] },
  { title: 'DNS tunneling beacon', category: 'network', sevs: ['low', 'medium'] },
  { title: 'Sensitive share mass download', category: 'data-exfil', sevs: ['high', 'critical'] },
  { title: 'File integrity anomaly on payroll DB', category: 'insider', sevs: ['medium', 'high'] }
];
const ARTIFACT_POOL = [
  { type: 'ip', value: '185.87.12.190' }, { type: 'ip', value: '103.152.36.4' },
  { type: 'domain', value: 'update-check-serv.tk' }, { type: 'domain', value: 'cdn-verify-panel.xyz' },
  { type: 'hash', value: '9f2b6c4e1a7d5f0c8b3e2a9d1c6f7a04' },
  { type: 'email', value: 'support@securecheck-alerts.tk' },
  { type: 'account', value: 'svc_reporting' }, { type: 'url', value: 'hxxp://portal-verify-mm.tk/auth' }
];

function makeRandomIncident() {
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const t = pick(INGEST_POOL);
  const artifacts = [];
  const n = 1 + Math.floor(Math.random() * 2);
  const used = new Set();
  while (artifacts.length < n) {
    const a = pick(ARTIFACT_POOL);
    if (!used.has(a.type + a.value)) { used.add(a.type + a.value); artifacts.push({ ...a }); }
  }
  return {
    title: t.title,
    category: t.category,
    severity: pick(t.sevs),
    status: 'new',
    assignee: null,
    source: 'SIEM',
    description: `Automatically ingested from simulated connector feed. Correlated by SOAR-Lite intake pipeline.`,
    artifacts
  };
}

// --------------------------------------------------------------------------- stats
function computeStats() {
  const incs = state.incidents;
  const runs = state.runs;
  const sev = (s) => incs.filter((i) => i.severity === s).length;
  const open = incs.filter((i) => i.status !== 'resolved' && i.status !== 'closed');
  const resolved = incs.length - open.length;
  const byStatus = {};
  incs.forEach((i) => { byStatus[i.status] = (byStatus[i.status] || 0) + 1; });
  const byCategory = {};
  incs.forEach((i) => { byCategory[i.category] = (byCategory[i.category] || 0) + 1; });
  const bySeverity = { critical: sev('critical'), high: sev('high'), medium: sev('medium'), low: sev('low'), info: sev('info') };

  const trend = [];
  for (let d = 13; d >= 0; d--) {
    const day = new Date(Date.now() - d * 86400000).toISOString().slice(0, 10);
    trend.push({
      date: day,
      label: new Date(day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      events: incs.filter((i) => i.createdAt.slice(0, 10) === day).length
    });
  }

  const pbHits = {};
  state.playbooks.forEach((p) => { pbHits[p.name] = 0; });
  runs.forEach((r) => { if (pbHits[r.playbookName] !== undefined) pbHits[r.playbookName]++; });

  const playbookBar = Object.entries(pbHits)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const running = runs.filter((r) => r.status === 'running' || r.status === 'queued').length;

  return {
    incidents: {
      total: incs.length,
      open: open.length,
      resolved,
      resolvedRate: incs.length ? Math.round((resolved / incs.length) * 100) : 0,
      critical: bySeverity.critical,
      high: bySeverity.high,
      bySeverity,
      byCategory,
      byStatus,
      trend
    },
    runs: {
      total: runs.length,
      running,
      success: runs.filter((r) => r.status === 'success').length,
      failed: runs.filter((r) => r.status === 'failed' || r.status === 'error').length,
      successRate: runs.length ? Math.round((runs.filter((r) => r.status === 'success').length / runs.length) * 100) : 0,
      auto: runs.filter((r) => r.trigger === 'auto').length,
      manual: runs.filter((r) => r.trigger === 'manual').length,
      playbookBar
    },
    playbooks: { total: state.playbooks.length, active: state.playbooks.filter((p) => p.active).length },
    activity: state.activity.slice(0, 12),
    settings: state.settings
  };
}

// --------------------------------------------------------------------------- router
function route(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || HOST}`);
  const p = url.pathname.replace(/\/+$/, '') || '/';
  const parts = p.split('/').filter(Boolean);

  // static / index
  if (parts[0] !== 'api') {
    if (p === '/') return serveStatic(res, '/index.html');
    return serveStatic(res, p);
  }

  const [ , ...args ] = parts; // api/[resource]/[id]/[action]

  // ------------------------------ API helpers -----------------------------
  const routeMap = {
    async health() {
      sendJson(res, 200, {
        ok: true,
        app: 'SOAR-Lite',
        version: '1.0.0',
        engine: state.settings.engineStatus,
        autoRun: state.settings.autoRun,
        uptime: Math.round(process.uptime()) + 's',
        time: new Date().toISOString()
      });
    },
    async meta() {
      sendJson(res, 200, { app: 'SOAR-Lite', version: '1.0.0', name: 'Automated Incident Response Playbook Runner (SOAR-Lite)', generatedAt: new Date().toISOString() });
    },
    async stats() {
      sendJson(res, 200, { data: computeStats() });
    },
    async activity() {
      const limit = Math.min(Number(url.searchParams.get('limit')) || 15, 100);
      sendJson(res, 200, { data: state.activity.slice(0, limit) });
    },
    async settings() {
      if (req.method === 'GET') return sendJson(res, 200, { data: state.settings });
      if (req.method === 'POST') {
        const body = await readBody(req);
        Object.assign(state.settings, {
          autoRun: body.autoRun !== undefined ? !!body.autoRun : state.settings.autoRun,
          engineStatus: body.engineStatus || state.settings.engineStatus,
          webhookUrl: body.webhookUrl !== undefined ? String(body.webhookUrl) : state.settings.webhookUrl,
          operator: body.operator !== undefined ? String(body.operator) : state.settings.operator
        });
        store.save();
        return sendJson(res, 200, { data: state.settings });
      }
      sendError(res, 405, 'Method not allowed');
    },

    // ------------------------------ playbooks -----------------------------
    async playbooks() {
      if (req.method === 'GET') return sendJson(res, 200, { data: state.playbooks });
      if (req.method === 'POST') {
        const body = await readBody(req);
        if (!body.name || !Array.isArray(body.steps) || !body.steps.length) {
          return sendError(res, 400, 'Playbook requires a name and at least one step.');
        }
        const pb = {
          id: store.uid('pb'),
          name: String(body.name),
          description: body.description || '',
          category: body.category || 'generic',
          severityMin: body.severityMin || 'low',
          active: body.active !== false,
          errorPolicy: body.errorPolicy || 'stop',
          tags: Array.isArray(body.tags) ? body.tags : [],
          postAction: body.postAction || null,
          steps: body.steps.map((s, i) => ({
            id: s.id || 's' + (i + 1),
            type: s.type,
            name: s.name || s.type,
            params: s.params || {},
            failRate: s.failRate
          })),
          version: 1,
          createdAt: store.now(),
          updatedAt: store.now()
        };
        state.playbooks.push(pb);
        store.save();
        store.addActivity('playbook', `Playbook created: "${pb.name}"`, `${pb.id} · ${pb.steps.length} steps`);
        return sendJson(res, 201, { data: pb });
      }
      sendError(res, 405, 'Method not allowed');
    },
    async playbook() {
      const [, id, action] = args;
      const pb = state.playbooks.find((x) => x.id === id);
      if (!pb) return sendError(res, 404, 'Playbook not found');

      if (req.method === 'GET') return sendJson(res, 200, { data: pb });

      if (action === 'run' && req.method === 'POST') {
        const body = await readBody(req);
        if (state.settings.engineStatus !== 'online') return sendError(res, 409, 'Engine is paused.');
        const incident = body.incidentId ? state.incidents.find((i) => i.id === body.incidentId) : null;
        const run = engine.startRun(state, { playbook: pb, incident, trigger: 'manual' });
        return sendJson(res, 201, { data: run });
      }

      if (action === 'toggle' && req.method === 'POST') {
        pb.active = !pb.active;
        pb.updatedAt = store.now();
        store.save();
        return sendJson(res, 200, { data: pb });
      }

      if (req.method === 'PUT') {
        const body = await readBody(req);
        if (body.name !== undefined) pb.name = String(body.name);
        if (body.description !== undefined) pb.description = String(body.description);
        if (body.category !== undefined) pb.category = String(body.category);
        if (body.severityMin !== undefined) pb.severityMin = String(body.severityMin);
        if (body.active !== undefined) pb.active = !!body.active;
        if (body.errorPolicy !== undefined) pb.errorPolicy = String(body.errorPolicy);
        if (body.tags !== undefined) pb.tags = body.tags;
        if (Array.isArray(body.steps) && body.steps.length) {
          pb.steps = body.steps.map((s, i) => ({ id: s.id || 's' + (i + 1), type: s.type, name: s.name || s.type, params: s.params || {}, failRate: s.failRate }));
        }
        pb.version = (pb.version || 1) + 1;
        pb.updatedAt = store.now();
        store.save();
        store.addActivity('playbook', `Playbook updated: "${pb.name}"`, `v${pb.version}`);
        return sendJson(res, 200, { data: pb });
      }

      if (req.method === 'DELETE') {
        state.playbooks = state.playbooks.filter((x) => x.id !== id);
        store.save();
        store.addActivity('playbook', `Playbook deleted: "${pb.name}"`, id);
        return sendJson(res, 200, { data: { ok: true } });
      }

      sendError(res, 405, 'Method not allowed');
    },

    // ------------------------------ incidents -----------------------------
    async incidents() {
      if (req.method === 'GET') return sendJson(res, 200, { data: state.incidents });
      if (req.method === 'POST') {
        const body = await readBody(req);
        const inc = {
          id: store.uid('inc'),
          title: String(body.title || 'Untitled incident'),
          description: body.description || '',
          category: body.category || 'generic',
          severity: body.severity || 'medium',
          status: body.status || 'new',
          assignee: body.assignee || null,
          source: body.source || 'manual',
          artifacts: Array.isArray(body.artifacts) ? body.artifacts : [{ type: 'ip', value: '10.0.0.1' }],
          createdAt: store.now(),
          updatedAt: store.now(),
          relatedPlaybook: null
        };
        return ingestIncident(res, inc, body.skipAutoRun);
      }
      sendError(res, 405, 'Method not allowed');
    },
    async ingest() {
      if (req.method !== 'POST') return sendError(res, 405, 'Method not allowed');
      const inc = { id: store.uid('inc'), ...makeRandomIncident(), createdAt: store.now(), updatedAt: store.now(), relatedPlaybook: null };
      return ingestIncident(res, inc, false);
    },
    async incident() {
      const [, id] = args;
      const inc = state.incidents.find((x) => x.id === id);
      if (!inc) return sendError(res, 404, 'Incident not found');
      if (req.method === 'GET') return sendJson(res, 200, { data: inc });
      if (req.method === 'PUT') {
        const body = await readBody(req);
        ['title', 'description', 'category', 'severity', 'status', 'assignee', 'source'].forEach((k) => {
          if (body[k] !== undefined) inc[k] = body[k];
        });
        if (body.artifacts !== undefined) inc.artifacts = body.artifacts;
        inc.updatedAt = store.now();
        store.save();
        return sendJson(res, 200, { data: inc });
      }
      if (req.method === 'DELETE') {
        state.incidents = state.incidents.filter((x) => x.id !== id);
        store.save();
        return sendJson(res, 200, { data: { ok: true } });
      }
      sendError(res, 405, 'Method not allowed');
    },

    // ------------------------------ runs ---------------------------------
    async runs() {
      if (req.method !== 'GET') return sendError(res, 405, 'Method not allowed');
      const showAll = url.searchParams.get('all') === '1';
      let list = state.runs;
      if (!showAll) list = list.filter((r) => r.status === 'running' || r.status === 'queued');
      sendJson(res, 200, { data: list });
    },
    async run() {
      const [, id, action] = args;
      const run = state.runs.find((x) => x.id === id);
      if (!run) return sendError(res, 404, 'Run not found');
      if (req.method === 'GET') return sendJson(res, 200, { data: run });
      if (action === 'cancel' && req.method === 'POST') {
        engine.cancelRun(run);
        store.addActivity('run', `Cancel requested for run`, `${run.id} · ${run.playbookName}`);
        return sendJson(res, 200, { data: { ok: true, requested: true } });
      }
      if (action === 'retry' && req.method === 'POST') {
        if (state.settings.engineStatus !== 'online') return sendError(res, 409, 'Engine is paused.');
        const incident = run.incidentId ? state.incidents.find((i) => i.id === run.incidentId) : null;
        const newRun = engine.retryRun(state, run, incident);
        return sendJson(res, 201, { data: newRun });
      }
      sendError(res, 405, 'Method not allowed');
    },

    // ------------------------------ docs ---------------------------------
    async docs() {
      const list = ['architecture', 'state', 'memory'].map((name) => {
        const f = path.join(DOCS_DIR, name + '.md');
        const exists = fs.existsSync(f);
        return { name, title: name.charAt(0).toUpperCase() + name.slice(1), exists, rendered: exists ? markdownToHtml(fs.readFileSync(f, 'utf8')) : '<p>Not found.</p>' };
      });
      sendJson(res, 200, { data: list });
    },
    async doc() {
      const [, name] = args;
      if (!/^[a-z-]+\.?[a-z]*$/.test(name || '')) return sendError(res, 400, 'Bad name');
      const file = path.join(DOCS_DIR, name + '.md');
      if (!fs.existsSync(file)) return sendError(res, 404, 'Document not found');
      const raw = fs.readFileSync(file, 'utf8');
      sendJson(res, 200, { data: { name, raw, html: markdownToHtml(raw) } });
    },

    // ------------------------------ reports ------------------------------
    async report() {
      const q = url.searchParams;
      const opts = {
        from: q.get('from') || undefined,
        to: q.get('to') || undefined,
        severity: q.get('severity') || undefined,
        category: q.get('category') || undefined,
        status: q.get('status') || undefined,
        playbookId: q.get('playbookId') || undefined
      };
      const report = reports.buildReport(state, opts);
      sendJson(res, 200, { data: report });
    },
    async reportOptions() {
      sendJson(res, 200, {
        data: {
          formats: [
            { id: 'html', label: 'HTML report', primary: true, note: 'Styled, printable, self-contained' },
            { id: 'json', label: 'JSON (machine)', note: 'Full structured data' },
            { id: 'markdown', label: 'Markdown', note: 'Portable & diff-friendly' },
            { id: 'csv', label: 'CSV (incidents)', note: 'Spreadsheet friendly' }
          ],
          severities: ['critical', 'high', 'medium', 'low', 'info'],
          statuses: ['new', 'open', 'in_progress', 'resolved', 'closed'],
          categories: [...new Set(state.incidents.map((i) => i.category))],
          playbooks: state.playbooks.map((p) => ({ id: p.id, name: p.name }))
        }
      });
    },
    async reportDownload() {
      const q = url.searchParams;
      const format = q.get('format') || 'html';
      if (!['html', 'json', 'markdown', 'csv'].includes(format)) return sendError(res, 400, 'Unsupported format');
      const opts = {
        from: q.get('from') || undefined,
        to: q.get('to') || undefined,
        severity: q.get('severity') || undefined,
        category: q.get('category') || undefined,
        status: q.get('status') || undefined,
        playbookId: q.get('playbookId') || undefined
      };
      const report = reports.buildReport(state, opts);
      const renderer = { html: reports.renderHtml, json: reports.renderJson, markdown: reports.renderMarkdown, csv: reports.renderCsv }[format];
      const body = renderer(report, opts);
      const ctype = { html: 'text/html; charset=utf-8', json: 'application/json; charset=utf-8', markdown: 'text/markdown; charset=utf-8', csv: 'text/csv; charset=utf-8' }[format];
      const fname = reports.filename(format);
      res.writeHead(200, {
        'Content-Type': ctype,
        'Content-Disposition': `attachment; filename="${fname}"`,
        'Content-Length': Buffer.byteLength(body)
      });
      res.end(body);
    }
  };

  // dispatch
  const [r0, r1, r2] = args;
  let handler = null;

  if (args.length === 1) {
    handler = routeMap[r0]
      || (r0 === 'report-options' ? routeMap.reportOptions : null)
      || (r0 === 'report-download' ? routeMap.reportDownload : null)
      || (r0 === 'report' ? routeMap.report : null);
  } else if (r0 === 'playbooks') {
    handler = routeMap.playbook;
  } else if (r0 === 'incidents') {
    handler = r1 === 'ingest' ? routeMap.ingest : routeMap.incident;
  } else if (r0 === 'runs') {
    handler = routeMap.run;
  } else if (r0 === 'docs' && args.length === 2) {
    handler = routeMap.doc;
  }

  if (!handler) return sendError(res, 404, 'Not found: ' + p);

  handler().catch((e) => {
    if (!res.headersSent) sendError(res, 500, e && e.message ? e.message : 'Server error');
    else try { res.end(); } catch (_) {}
  });
}

// ingest pipeline (shared by manual + simulated)
async function ingestIncident(res, inc, skipAutoRun) {
  state.incidents.unshift(inc);
  store.save();
  store.addActivity('incident', `Incident ingested (${inc.severity})`, `${inc.id} · ${inc.title}`);

  let run = null;
  if (state.settings.autoRun && !skipAutoRun && state.settings.engineStatus === 'online') {
    const pb = engine.findMatchingPlaybook(state, inc);
    if (pb) {
      inc.relatedPlaybook = pb.id;
      await delay(350);
      run = engine.startRun(state, { playbook: pb, incident: inc, trigger: 'auto' });
    }
  }
  sendJson(res, 201, { data: { incident: inc, autoRun: run ? { runId: run.id, playbook: run.playbookName } : null } });
}

// --------------------------------------------------------------------------- server
const server = http.createServer((req, res) => {
  const t0 = Date.now();
  const onErr = (e) => {
    try { sendError(res, 500, e && e.message ? e.message : 'Server error'); } catch (_) { /* socket closed */ }
  };
  try {
    route(req, res);
    process.nextTick(() => {});
  } catch (e) {
    onErr(e);
  }
  res.on('finish', () => {
    const code = res.statusCode || 0;
    if (code >= 400) console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} -> ${code} (${Date.now() - t0}ms)`);
  });
});

server.listen(PORT, HOST, () => {
  console.log('');
  console.log('  ┌─────────────────────────────────────────────────────────────┐');
  console.log('  │   SOAR-Lite · Automated Incident Response Playbook Runner  │');
  console.log('  └─────────────────────────────────────────────────────────────┘');
  console.log('');
  console.log(`  Console      :  http://127.0.0.1:${PORT}`);
  console.log(`  Engine       :  ${state.settings.engineStatus} (autoRun=${state.settings.autoRun})`);
  console.log(`  Playbooks    :  ${state.playbooks.length}  ·  Incidents: ${state.incidents.length}  ·  Runs: ${state.runs.length}`);
  console.log(`  Data store   :  ${path.join(__dirname, 'data', 'soar.json')}`);
  console.log('');
  if (process.env.SOAR_NO_OPEN !== '1' && process.platform === 'win32') {
    exec(`start "" http://127.0.0.1:${PORT}`, { windowsHide: true });
  }
});

module.exports = { state };