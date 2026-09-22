#!/usr/bin/env node
/* ============================================================
 * ORBIT 3D Product Configurator — app server / launcher
 *
 * Boots a local-only server and opens the app in a chromeless
 * browser window (Chrome app mode / Edge fallback).
 *
 * Environment (set by the native launcher):
 *   ORBIT_HEARTBEAT=<file>   launcher touches this file; if it goes
 *                            stale >3s, the app exits (shuts down the
 *                            server when the .exe is killed)
 *   ORBIT_VERSION=<v>        shown in the banner / health endpoint
 *   ORBIT_DONT_OPEN=1        do not auto-open a browser (headless tests)
 * ============================================================ */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

const PORT_RANGE = [8642, 8652];           // first..last port to try
const ROOT = __dirname;                    // launch.js sits inside src/
const HEARTBEAT = process.env.ORBIT_HEARTBEAT || null;
const VERSION = process.env.ORBIT_VERSION || 'dev';
const DONT_OPEN = process.env.ORBIT_DONT_OPEN === '1';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'text/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff2':'font/woff2',
  '.glb':  'model/gltf-binary',
};

function send(res, code, body, type) {
  res.writeHead(code, { 'Content-Type': type || 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(body);
}

const server = http.createServer((req, res) => {
  let urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  if (urlPath === '/') urlPath = '/app.html';

  if (urlPath === '/health') {
    return send(res, 200, JSON.stringify({ ok: true, app: 'ORBIT 3D Product Configurator', version: VERSION }), 'application/json');
  }

  // page-alive beacon: the UI pings this every second; if it stops
  // (window closed / navigated away) the server shuts itself down.
  if (urlPath === '/beacon') {
    lastPageBeacon = Date.now();
    return send(res, 204, '');
  }

  // path traversal guard
  const file = path.normalize(path.join(ROOT, urlPath));
  if (!file.startsWith(ROOT)) return send(res, 403, 'Forbidden');

  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) return send(res, 404, 'Not found: ' + urlPath);
    const ext = path.extname(file).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
});

let lastPageBeacon = 0;

function listenOn(port, cb) {
  const srv = http.createServer();           // probe socket
  srv.once('error', () => cb(false));
  srv.listen(port, '127.0.0.1', () => srv.close(() => cb(true)));
}

function findPort(start, end, cb) {
  if (start > end) return cb(null);
  listenOn(start, ok => (ok ? cb(start) : findPort(start + 1, end, cb)));
}

function findBrowser() {
  const pf64 = process.env['ProgramFiles'] || 'C:\\Program Files';
  const pf86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
  const local = process.env.LOCALAPPDATA || '';
  return [
    path.join(pf64, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    path.join(pf86, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    path.join(local,  'Google', 'Chrome', 'Application', 'chrome.exe'),
    path.join(pf86, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
    path.join(pf64, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } }) || null;
}

function exit() { try { server.close(() => process.exit(0)); } catch (e) {} setTimeout(() => process.exit(0), 400); }

findPort(PORT_RANGE[0], PORT_RANGE[1], port => {
  if (!port) {
    console.error('[ORBIT] No free port available in range ' + PORT_RANGE.join('-'));
    process.exit(1);
  }

  // --- launcher watchdog: stay alive only while the .exe is running ---
  if (HEARTBEAT) {
    try { fs.writeFileSync(HEARTBEAT, String(process.pid)); } catch (e) {}
    let prevM = 0;
    let lastChange = Date.now();
    try { prevM = fs.statSync(HEARTBEAT).mtimeMs; } catch (e) {}
    setInterval(() => {
      let m = 0;
      try { m = fs.statSync(HEARTBEAT).mtimeMs; } catch (e) {}
      if (m !== prevM) { prevM = m; lastChange = Date.now(); return; }
      if (Date.now() - lastChange > 3000) exit();   // launcher stopped touching it
    }, 700);
  }

  // --- page-alive watchdog: exit if the app window stops pinging ---
  setInterval(() => {
    if (lastPageBeacon && Date.now() - lastPageBeacon > 6000) exit();
  }, 1000);

  server.listen(port, '127.0.0.1', () => {
    const url = 'http://127.0.0.1:' + port + '/';
    console.log('--------------------------------------------------');
    console.log('  ORBIT - 3D Product Configurator ' + VERSION);
    console.log('  Local server: ' + url);
    console.log('  Press Ctrl+C to quit.');
    console.log('--------------------------------------------------');

    if (DONT_OPEN) return;                 // headless / CI mode

    const browser = findBrowser();
    if (!browser) {
      console.log('  No Chrome/Edge found. Open ' + url + ' manually.');
      return;
    }
    // isolated profile => app window lives in its own process tree,
    // so closing the window cleanly ends that browser process.
    const profile = path.join(os.tmpdir(), 'orbit-app-profile');
    const child = spawn(browser, [
      '--app=' + url,
      '--window-size=1280,860',
      '--user-data-dir=' + profile,
      '--no-first-run',
      '--no-default-browser-check',
    ], { stdio: 'ignore', detached: false });
    child.on('error', () => console.log('  Browser launch failed. Open ' + url + ' manually.'));
    child.on('exit', () => exit());        // app window closed -> shut down
  });

  process.on('SIGINT', exit);
  process.on('SIGTERM', exit);
  process.on('SIGHUP', exit);
});
