// Headless E2E: run the real exe with ORBIT_DONT_OPEN=1, poll /health, fetch app + three.js, then kill.
const { spawn, execSync } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const EXE = process.argv[2];
if (!EXE) { console.error('usage: node e2e.js <exe>'); process.exit(2); }

function get(port, p) {
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port, path: p }, res => {
      let chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks) }));
    }).on('error', reject);
  });
}

(async () => {
  const results = [];
  const check = (name, ok, extra) => { results.push([name, ok, extra]); console.log((ok ? 'PASS ' : 'FAIL ') + name + (extra ? '  -> ' + extra : '')); };

  // pick exe port by scanning our fixed range
  let port = null;
  const child = spawn(EXE, [], {
    env: Object.assign({}, process.env, { ORBIT_DONT_OPEN: '1' }),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  child.stdout.on('data', d => { log += d; });
  child.stderr.on('data', d => { log += d; });

  try {
    // wait for server banner to learn the port
    const t0 = Date.now();
    while (Date.now() - t0 < 60000) {
      const m = log.match(/Local server: http:\/\/127\.0\.0\.1:(\d+)/);
      if (m) { port = +m[1]; break; }
      await new Promise(r => setTimeout(r, 300));
    }
    check('exe starts and prints server URL', !!port, port ? String(port) : log.slice(0, 200));

    if (port) {
      await new Promise(r => setTimeout(r, 800));
      const h = await get(port, '/health');
      check('/health 200', h.status === 200, h.body.toString().slice(0, 80));
      const a = await get(port, '/');
      check('app.html served', a.status === 200 && /ORBIT/.test(a.body.toString()) , a.status + ', ' + a.body.length + ' bytes');
      const t = await get(port, '/assets/three.min.js');
      check('three.js served', t.status === 200 && t.body.length > 500000, t.status + ', ' + t.body.length + ' bytes');
      const b = await get(port, '/beacon');
      check('/beacon alive', b.status === 204, String(b.status));
    }

    // graceful stop
    const t1 = Date.now();
    let stopped = false;
    execSync('taskkill /PID ' + child.pid + ' /T /F', { stdio: 'ignore' });
    // wait a moment and confirm port freed
    while (Date.now() - t1 < 8000) {
      try { await get(port, '/health'); await new Promise(r => setTimeout(r, 400)); }
      catch (e) { stopped = true; break; }
    }
    check('exe + server stop on kill', stopped, stopped ? 'port freed' : 'still responding');

    const allOk = results.every(r => r[1]);
    console.log(allOk ? 'E2E PASS' : 'E2E FAIL');
    process.exit(allOk ? 0 : 1);
  } catch (e) {
    console.error('E2E ERROR', e);
    try { execSync('taskkill /PID ' + child.pid + ' /T /F', { stdio: 'ignore' }); } catch (_) {}
    process.exit(1);
  }
})();
