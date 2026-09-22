import { readdirSync, existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/*
 * sync-skills.mjs — keep the portfolio in step with the workspace.
 * Every skill in js/data.js carries a `dir` field naming the exact project
 * folder it was built from. This script compares those folders against what
 * is actually on disk and reports any drift.
 *
 * Usage:
 *   node scripts/sync-skills.mjs
 */

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE_ROOT = resolve(HERE, "..");
const WORKSPACE = resolve(SITE_ROOT, "..", "..");
const NESTED = join(WORKSPACE, "1. Another 35 projects");
const EXCLUDED = new Set(["1. Another 35 projects", "3D interactive portfolio site (Three.js)"]);
const DATA_FILE = join(SITE_ROOT, "js", "data.js");

function foldersUnder(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith(".") && !EXCLUDED.has(e.name))
    .map((e) => e.name);
}

function countBy(arr) {
  const map = new Map();
  for (const x of arr) map.set(x, (map.get(x) || 0) + 1);
  return map;
}

const onDisk = countBy([...foldersUnder(WORKSPACE), ...foldersUnder(NESTED)]);

const dataSrc = readFileSync(DATA_FILE, "utf8");
const dirFields = [...dataSrc.matchAll(/dir:\s*"((?:[^"\\]|\\.)*)"/g)].map((m) =>
  m[1].replace(/\\u2192/g, "\u2192").replace(/\\"/g, '"')
);
const inData = countBy(dirFields);

const diskMissingFromData = [...onDisk.keys()].filter((d) => (onDisk.get(d) || 0) > (inData.get(d) || 0));
const dataMissingFromDisk = [...inData.keys()].filter((d) => (inData.get(d) || 0) > (onDisk.get(d) || 0));
const noDirField = (dataSrc.match(/{\n\s*id: "[^"]+",\n\s*name: "[^"]+",\n(?!\s*dir:)/g) || []).length;

console.log(`Project folders on disk : ${[...onDisk.values()].reduce((a, b) => a + b, 0)}`);
console.log(`Skills in data.js        : ${[...inData.values()].reduce((a, b) => a + b, 0)}`);
console.log(`Skills missing a dir field: ${noDirField}`);

if (diskMissingFromData.length)
  console.log("\nOn disk but NOT covered by data.js:\n" + diskMissingFromData.map((m) => `  - ${m} (${onDisk.get(m)})`).join("\n"));
if (dataMissingFromDisk.length)
  console.log("\nIn data.js but no matching folder:\n" + dataMissingFromDisk.map((m) => `  - ${m} (${inData.get(m)})`).join("\n"));

const ok = !diskMissingFromData.length && !dataMissingFromDisk.length && noDirField === 0;
console.log(`\nIn sync : ${ok ? "YES" : "NO"}`);
process.exit(ok ? 0 : 1);