#!/usr/bin/env node
/* ============================================================
 * build.js — packages ORBIT into a single portable Windows .exe
 *
 * Strategy:
 *   1. assemble payload (portable node.exe + app files)
 *   2. zip it with PowerShell Compress-Archive
 *   3. compile the C# launcher with the .NET Framework compiler (csc)
 *   4. append the zip to the exe, stamped with a 32-byte marker:
 *        "ORBIT1:" + <10-digit size> + "|" + <10-digit checksum> + pad
 *   5. headless self-test of the final exe
 *
 * On run, the exe self-extracts to %LOCALAPPDATA%\Orbit3D\app and
 * launches node src/launch.js, which opens the app window.
 * ============================================================ */
'use strict';

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const DIST = path.join(ROOT, 'dist');
const PAYLOAD = path.join(DIST, 'payload');
const OUT = path.join(ROOT, '3D-Product-Configurator.exe');
const CSC = path.join(process.env.SystemRoot || 'C:\\Windows',
  'Microsoft.NET', 'Framework64', 'v4.0.30319', 'csc.exe');
const PS = path.join(process.env.SystemRoot || 'C:\\Windows',
  'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
const MARKER = 'ORBIT1:';

function log(s) { console.log('  ' + s); }
function fail(s) { console.error('BUILD FAILED: ' + s); process.exit(1); }
function copy(src, dest) { fs.mkdirSync(path.dirname(dest), { recursive: true }); fs.copyFileSync(src, dest); }

// ---------- 1. prerequisites ----------
console.log('[1/6] Checking prerequisites...');
if (process.platform !== 'win32') fail('this build targets Windows.');
if (!fs.existsSync(CSC)) fail('csc.exe not found (need .NET Framework 4.x).');
const NODE_PORTABLE = path.join(DIST, 'node', 'node.exe');
if (!fs.existsSync(NODE_PORTABLE)) fail('portable node.exe missing - run: node tools/fetch-node.js');
for (const f of ['src/launch.js', 'src/app.html', 'src/assets/three.min.js'])
  if (!fs.existsSync(path.join(ROOT, f))) fail('missing ' + f);
log('csc.exe + portable node.exe + app files OK');

// ---------- 2. assemble payload ----------
console.log('[2/6] Assembling payload...');
fs.rmSync(PAYLOAD, { recursive: true, force: true });
fs.mkdirSync(PAYLOAD, { recursive: true });
copy(NODE_PORTABLE, path.join(PAYLOAD, 'node', 'node.exe'));
copy(path.join(ROOT, 'src', 'launch.js'), path.join(PAYLOAD, 'src', 'launch.js'));
copy(path.join(ROOT, 'src', 'app.html'), path.join(PAYLOAD, 'src', 'app.html'));
copy(path.join(ROOT, 'src', 'assets', 'three.min.js'), path.join(PAYLOAD, 'src', 'assets', 'three.min.js'));
log('payload ready');

// ---------- 3. zip payload ----------
console.log('[3/6] Zipping payload...');
const ZIP = path.join(DIST, 'payload.zip');
fs.rmSync(ZIP, { force: true });
execFileSync(PS, [
  '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
  `Compress-Archive -Path '${PAYLOAD}\\*' -DestinationPath '${ZIP}' -Force`,
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 300000 });
const zipBuf = fs.readFileSync(ZIP);
if (zipBuf.length < 1000) fail('payload zip suspiciously small');
log('payload.zip: ' + (zipBuf.length / 1048576).toFixed(1) + ' MB');

// ---------- 4. compile launcher ----------
console.log('[4/6] Compiling C# launcher...');
fs.mkdirSync(DIST, { recursive: true });
const STAGE_EXE = path.join(DIST, 'stage.exe');
fs.rmSync(STAGE_EXE, { force: true });
execFileSync(CSC, [
  '/nologo', '/optimize+', '/target:exe', '/platform:anycpu',
  '/out:' + STAGE_EXE, path.join(ROOT, 'launcher', 'Launcher.cs'),
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 120000 });
log('launcher compiled');

// ---------- 5. stitch exe = launcher + payload + marker ----------
console.log('[5/6] Stitching payload into exe...');
const exeBuf = fs.readFileSync(STAGE_EXE);
let crc = 0;
for (let i = 0; i < zipBuf.length; i++) crc = (crc + zipBuf[i]) % 4294967296;
const marker = Buffer.from(
  (MARKER + String(zipBuf.length).padStart(10, '0') + '|' + String(crc).padStart(10, '0')).padEnd(32, '.'),
  'ascii');
if (marker.length !== 32) fail('marker length bug');
fs.writeFileSync(OUT, Buffer.concat([exeBuf, zipBuf, marker]));
const totalMB = (fs.statSync(OUT).size / 1048576).toFixed(1);
log('stitched ' + OUT + ' (' + totalMB + ' MB)');

// ---------- 6. headless self-test ----------
console.log('[6/6] Self-test (extract + verify payload)...');
try {
  const out = execFileSync(OUT, ['--selftest'], { timeout: 300000, encoding: 'utf8' });
  if (!/SELFTEST PASS/.test(out)) fail('self-test did not pass:\n' + out);
  log(out.trim().split('\n').slice(-1)[0]);
} catch (e) {
  fail('self-test error: ' + (e.stdout || e.message));
}

console.log('');
console.log('  >> ' + OUT);
console.log('  Double-click it to launch the 3D Product Configurator.');
console.log('  (headless check:  3D-Product-Configurator.exe --selftest )');
