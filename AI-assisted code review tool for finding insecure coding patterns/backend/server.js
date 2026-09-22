'use strict';
/**
 * server.js — zero-dependency HTTP API + static hosting for SecuRevealer.
 *   POST /api/scan    { files:[{name,content}] } | multipart form | raw text (?name=)
 *   POST /api/report  same bodies → downloadable HTML report
 *   GET  /api/health  → { ok:true }
 *   GET  /*           → static files from public/
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { scanFiles } = require('./analysis/scanner');
const { buildHtmlReport } = require('./report/reporter');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, '..', 'public');

const MIME = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
};

function readBody(req, limit = 20 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > limit) { req.destroy(); reject(new Error('body too large')); return; }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

/** Minimal multipart/form-data parser (handles browser FormData file uploads). */
function parseMultipart(buf, boundary) {
  const files = [];
  const delim = Buffer.from('--' + boundary);
  let idx = buf.indexOf(delim);
  while (idx !== -1) {
    const next = buf.indexOf(delim, idx + delim.length);
    if (idx === -1 || next === -1) break;
    const part = buf.slice(idx + delim.length, next);
    // part: \r\nheaders...\r\n\r\n<content>\r\n
    const headerEnd = part.indexOf('\r\n\r\n');
    if (headerEnd !== -1) {
      const headers = part.slice(0, headerEnd).toString('utf8');
      const content = part.slice(headerEnd + 4, part.length - 2); // strip trailing \r\n
      const nameMatch = /name="([^"]*)"(?:; filename="([^"]*)")?/.exec(headers);
      if (nameMatch && nameMatch[2]) {
        files.push({ name: nameMatch[2], content: content.toString('utf8') });
      }
    }
    idx = next;
  }
  return files;
}

function json(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) });
  res.end(body);
}

async function readScanPayload(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const ctype = req.headers['content-type'] || '';
  const body = await readBody(req);

  if (ctype.includes('multipart/form-data')) {
    const m = /boundary=(?:"([^"]+)"|([^;]+))/.exec(ctype);
    if (!m) throw new Error('missing multipart boundary');
    const boundary = (m[1] || m[2]).trim();
    const files = parseMultipart(body, boundary);
    if (!files.length) throw new Error('no files in multipart payload');
    return files;
  }
  if (ctype.includes('application/json')) {
    const parsed = JSON.parse(body.toString('utf8') || '{}');
    if (!Array.isArray(parsed.files)) throw new Error('expected {"files":[{"name","content"}]}');
    return parsed.files.map(f => ({ name: String(f.name || 'untitled.txt'), content: String(f.content || '') }));
  }
  // raw text upload: /api/scan?name=app.js
  const name = url.searchParams.get('name') || 'pasted.txt';
  return [{ name, content: body.toString('utf8') }];
}

function serveStatic(res, urlPath) {
  let rel = decodeURIComponent(urlPath.replace(/^\/+/, '')) || 'index.html';
  const abs = path.normalize(path.join(PUBLIC_DIR, rel));
  if (!abs.startsWith(PUBLIC_DIR)) { res.writeHead(403); return res.end('forbidden'); }
  fs.readFile(abs, (err, data) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain' }); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(abs)] || 'application/octet-stream' });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  try {
    if (req.method === 'GET' && url.pathname === '/api/health') {
      return json(res, 200, { ok: true, tool: 'SecuRevealer', version: '1.0.0' });
    }
    if (req.method === 'POST' && (url.pathname === '/api/scan' || url.pathname === '/api/report')) {
      const t0 = Date.now();
      const files = await readScanPayload(req, res);
      const report = scanFiles(files);
      report.meta.durationMs = Date.now() - t0;

      if (url.pathname === '/api/report') {
        const html = buildHtmlReport(report);
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Content-Disposition': 'attachment; filename="securevealer-report.html"',
        });
        return res.end(html);
      }
      return json(res, 200, report);
    }
    if (req.method === 'GET') return serveStatic(res, url.pathname);

    res.writeHead(405); res.end('method not allowed');
  } catch (e) {
    json(res, 400, { error: e.message || 'bad request' });
  }
});

function openBrowser(url) {
  try {
    if (process.platform === 'win32')
      spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' }).unref();
    else if (process.platform === 'darwin')
      spawn('open', [url], { detached: true, stdio: 'ignore' }).unref();
    else
      spawn('xdg-open', [url], { detached: true, stdio: 'ignore' }).unref();
  } catch { /* headless environment — ignore */ }
}

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n  ✖ Port ${PORT} is already in use.`);
    console.error(`    Pick another port first:   set PORT=3001`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, () => {
  console.log(`  ┌─────────────────────────────────────────┐`);
  console.log(`  │  SecuRevealer v1.0.0                    │`);
  console.log(`  │  http://localhost:${PORT}                  │`);
  console.log(`  │  Ctrl+C to stop                         │`);
  console.log(`  └─────────────────────────────────────────┘`);
  // auto-open the UI when running as a packaged desktop exe
  if (process.pkg && process.env.SECUREVEALER_NO_OPEN !== '1') openBrowser(`http://localhost:${PORT}`);
});