'use strict';
/**
 * scanner.js — scan pipeline.
 * files: [{ name, content }] → { summary, files:[{ name, findings[], score }] }
 */

const { RULES } = require('./detectors');
const { mapCommentsAndStrings, inRanges } = require('./ast');
const { adviceFor } = require('./aiadvice');

const SEVERITY_WEIGHT = { CRITICAL: 10, HIGH: 7, MEDIUM: 4, LOW: 1 };
const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

const EXT_LANG = {
  js: 'js', mjs: 'js', cjs: 'js', jsx: 'js',
  ts: 'ts', tsx: 'ts',
  py: 'py', rb: 'rb', php: 'php',
  java: 'java', cs: 'cs', go: 'go',
  sql: 'sql', sh: 'sh', bash: 'sh', zsh: 'sh',
  json: 'json', yml: 'yaml', yaml: 'yaml',
  env: 'env', ini: 'env', conf: 'env',
  html: 'html', css: 'css', md: 'md',
};

function sniffLanguage(name) {
  const base = name.split('/').pop().toLowerCase();
  if (/^\.env|^\.flaskenv/.test(base)) return 'env';
  const ext = base.includes('.') ? base.split('.').pop() : '';
  return EXT_LANG[ext] || 'text';
}

function scanFile(fileName, content) {
  const lang = sniffLanguage(fileName);
  const findings = [];
  const ranges = (lang === 'js' || lang === 'ts') ? mapCommentsAndStrings(content) : null;
  const lines = content.split('\n');

  for (const rule of RULES) {
    if (rule.languages.includes('*') || rule.languages.includes(lang)) {
      let m;
      const re = new RegExp(rule.pattern.source, rule.pattern.flags.includes('g') ? rule.pattern.flags : rule.pattern.flags + 'g');
      while ((m = re.exec(content)) !== null) {
        if (m[0].length === 0) { re.lastIndex++; continue; }
        // false-positive filter: skip hits fully inside comments/strings (JS/TS only)
        if (ranges && inRanges(m.index, ranges.comments)) {
          if (re.lastIndex === m.index) re.lastIndex++;
          continue;
        }
        const before = content.slice(0, m.index);
        const line = before.split('\n').length;
        const col = m.index - before.lastIndexOf('\n');
        const lineText = (lines[line - 1] || '').trim().slice(0, 200);
        findings.push({
          ruleId: rule.id,
          title: rule.title,
          severity: rule.severity,
          cwe: rule.cwe,
          owasp: rule.owasp,
          language: lang,
          line,
          col,
          snippet: lineText,
          match: m[0].slice(0, 120),
          ...adviceFor(rule.id),
        });
        if (re.lastIndex === m.index) re.lastIndex++;
      }
    }
  }

  // dedupe: same rule hitting same line keeps first occurrence only
  const seen = new Set();
  const deduped = findings.filter(f => {
    const k = f.ruleId + ':' + f.line;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  deduped.sort((a, b) =>
    SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity) || a.line - b.line
  );

  const score = Math.min(100, deduped.reduce((s, f) => s + SEVERITY_WEIGHT[f.severity], 0));

  return { name: fileName, language: lang, lines: lines.length, findings: deduped, score };
}

function grade(score) {
  if (score === 0) return 'A';
  if (score < 10) return 'B';
  if (score < 25) return 'C';
  if (score < 45) return 'D';
  if (score < 70) return 'E';
  return 'F';
}

/**
 * @param {{name:string,content:string}[]} files
 */
function scanFiles(files) {
  const scanned = files.map(f => scanFile(f.name, String(f.content || '')));
  const bySeverity = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const f of scanned) for (const find of f.findings) bySeverity[find.severity]++;

  const totalScore = Math.min(100, scanned.reduce((s, f) => s + f.score, 0));

  return {
    meta: {
      tool: 'SecuRevealer',
      version: '1.0.0',
      scannedAt: new Date().toISOString(),
      filesScanned: scanned.length,
      linesScanned: scanned.reduce((s, f) => s + (f.lines || 0), 0),
      durationMs: 0,
    },
    summary: {
      totalFindings: Object.values(bySeverity).reduce((a, b) => a + b, 0),
      bySeverity,
      riskScore: totalScore,
      grade: grade(totalScore),
      filesAffected: scanned.filter(f => f.findings.length > 0).length,
    },
    files: scanned,
  };
}

module.exports = { scanFiles, scanFile, sniffLanguage, grade };
