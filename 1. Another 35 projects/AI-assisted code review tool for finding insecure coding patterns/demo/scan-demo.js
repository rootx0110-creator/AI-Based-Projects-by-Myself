'use strict';
/** CLI smoke test: scan public/demo/* and print a findings summary. */
const fs = require('fs');
const path = require('path');
const { scanFiles } = require('../backend/analysis/scanner');
const { buildHtmlReport } = require('../backend/report/reporter');

const DIR = path.join(__dirname, '..', 'public', 'demo');
const files = fs.readdirSync(DIR).map(name => ({
  name,
  content: fs.readFileSync(path.join(DIR, name), 'utf8'),
}));

const report = scanFiles(files);
report.meta.durationMs = 1;

console.log('\n  SecuRevealer demo scan');
console.log(`  files: ${report.meta.filesScanned}  lines: ${report.meta.linesScanned}`);
console.log(`  risk: ${report.summary.riskScore}/100 (grade ${report.summary.grade})`);
console.log(`  findings: ${JSON.stringify(report.summary.bySeverity)}\n`);

for (const f of report.files) {
  if (!f.findings.length) continue;
  console.log(`  ▸ ${f.name} (risk ${f.score})`);
  for (const fd of f.findings) {
    console.log(`    [${fd.severity}] ${fd.ruleId} — line ${fd.line}: ${fd.title}`);
  }
}

const out = path.join(__dirname, 'demo-report.html');
fs.writeFileSync(out, buildHtmlReport(report));
console.log(`\n  HTML report written to: demo/demo-report.html\n`);