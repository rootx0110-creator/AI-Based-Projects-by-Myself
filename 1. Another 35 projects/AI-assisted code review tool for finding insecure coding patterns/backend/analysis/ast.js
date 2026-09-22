'use strict';
/**
 * ast.js — tolerant JS/TS assist pass. Not a full parser: a fast scanner that
 * maps comment / string / template-literal byte ranges so the detector pass
 * can discard regex hits inside them (the classic false-positive class),
 * plus a bracket-balance sanity check for "is this even parseable JS".
 */

/**
 * Scan code and return { comments:[{start,end}], strings:[{start,end}] }.
 * Handles: // /* *​/ comments, '…"…', "…", `…${…}` templates (nested braces
 * are simply skipped as opaque text — good enough for range mapping).
 */
function mapCommentsAndStrings(code) {
  const comments = [];
  const strings = [];
  let i = 0;
  const n = code.length;
  let inStr = null; // "'", '"', '`'
  let strStart = -1;

  while (i < n) {
    const c = code[i];
    const next = code[i + 1];

    if (inStr) {
      if (c === '\\') { i += 2; continue; }
      if (c === inStr) {
        strings.push({ start: strStart, end: i + 1 });
        inStr = null; strStart = -1;
        i++; continue;
      }
      i++; continue;
    }

    if (c === '/' && next === '/') { // line comment
      const start = i;
      while (i < n && code[i] !== '\n') i++;
      comments.push({ start, end: i });
      continue;
    }
    if (c === '/' && next === '*') { // block comment
      const start = i;
      const close = code.indexOf('*/', i + 2);
      i = close === -1 ? n : close + 2;
      comments.push({ start, end: i });
      continue;
    }
    if (c === '\'' || c === '"' || c === '`') {
      inStr = c; strStart = i;
      i++; continue;
    }
    i++;
  }
  return { comments, strings };
}

function inRanges(pos, ranges) {
  for (const r of ranges) if (pos >= r.start && pos < r.end) return true;
  return false;
}

/**
 * Bracket balance sanity check for JS-family sources.
 * Returns { ok: boolean, reason?: string }.
 * Line comments/strings are blanked out first so braces inside them don't count.
 */
function hasBalancedSyntax(code) {
  const { comments, strings } = mapCommentsAndStrings(code);
  const masked = code.split('');
  for (const r of [...comments, ...strings]) {
    for (let k = r.start; k < r.end && k < masked.length; k++) {
      if (masked[k] !== '\n') masked[k] = ' ';
    }
  }
  const stack = [];
  const pairs = { ')': '(', ']': '[', '}': '{' };
  for (const ch of masked) {
    if (ch === '(' || ch === '[' || ch === '{') stack.push(ch);
    else if (ch === ')' || ch === ']' || ch === '}') {
      const top = stack.pop();
      if (top !== pairs[ch]) return { ok: false, reason: 'unbalanced brackets' };
    }
  }
  if (stack.length) return { ok: false, reason: 'unclosed brackets' };
  return { ok: true };
}

module.exports = { mapCommentsAndStrings, inRanges, hasBalancedSyntax };
