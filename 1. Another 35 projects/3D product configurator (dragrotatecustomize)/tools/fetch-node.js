#!/usr/bin/env node
/* ============================================================
 * tools/fetch-node.js — one-time setup for build.js
 * Downloads a portable Windows node.exe into dist/node/.
 * Also caches three.js locally so the app works fully offline.
 * ============================================================ */
'use strict';

const https = require('https');
const fs = require('fs');
const path = require('path');

const DIST = path.join(__dirname, '..', 'dist');
const NODE_DIR = path.join(DIST, 'node');
const ASSETS = path.join(__dirname, '..', 'src', 'assets');

const NODE_VERSION = 'v20.19.4';
const NODE_ZIP = `https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-win-x64.zip`;
const THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';

function get(url, redirects) {
  return new Promise((resolve, reject) => {
    if (redirects === undefined) redirects = 5;
    https.get(url, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirects > 0) {
        return resolve(get(res.headers.location, redirects - 1));
      }
      if (res.statusCode !== 200) return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      resolve(res);
    }).on('error', reject);
  });
}

function download(url, dest) {
  return get(url).then(res => new Promise((resolve, reject) => {
    const tmp = dest + '.part';
    const out = fs.createWriteStream(tmp);
    res.pipe(out);
    out.on('error', reject);
    out.on('close', () => {
      try {
        if (fs.existsSync(tmp)) fs.renameSync(tmp, dest);
        console.log('  saved ' + dest + ' (' + (fs.statSync(dest).size / 1048576).toFixed(1) + ' MB)');
        resolve();
      } catch (e) { reject(e); }
    });
  }));
}

async function main() {
  fs.mkdirSync(NODE_DIR, { recursive: true });
  fs.mkdirSync(ASSETS, { recursive: true });
  const nodeExe = path.join(NODE_DIR, 'node.exe');
  const three = path.join(ASSETS, 'three.min.js');

  // three.js (small, always fetch if missing)
  if (!fs.existsSync(three)) {
    console.log('Downloading three.js r128 ...');
    await download(THREE_URL, three);
  } else {
    console.log('three.js already cached: ' + three);
  }

  // node.exe
  if (fs.existsSync(nodeExe)) {
    console.log('Portable node.exe already cached: ' + nodeExe);
  } else {
    console.log(`Downloading portable Node.js ${NODE_VERSION} (win-x64) ...`);
    const zip = path.join(DIST, 'node.zip');
    await download(NODE_ZIP, zip);
    console.log('Extracting node.exe ...');
    const { execFileSync } = require('child_process');
    const powershell = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
    execFileSync(powershell, [
      '-NoProfile', '-Command',
      `Expand-Archive -LiteralPath '${zip}' -DestinationPath '${DIST}\\node-unzip' -Force`,
    ], { stdio: 'ignore', timeout: 300000 });
    fs.copyFileSync(path.join(DIST, 'node-unzip', `node-${NODE_VERSION}-win-x64`, 'node.exe'), nodeExe);
    fs.rmSync(zip, { force: true });
    fs.rmSync(path.join(DIST, 'node-unzip'), { recursive: true, force: true });
    console.log('  saved ' + nodeExe);
  }
  console.log('Setup complete. Now run: npm run build');
}

main().catch(e => { console.error('SETUP FAILED: ' + e.message); process.exit(1); });
