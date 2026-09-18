'use strict';

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function inline(md) {
  let s = escapeHtml(md);
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  return s;
}

function markdownToHtml(md) {
  const lines = String(md || '').split(/\r?\n/);
  const rows = [];
  let i = 0;
  let para = [];

  const flushPara = () => {
    if (para.length) {
      rows.push('<p>' + inline(para.join(' ')) + '</p>');
      para = [];
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    // fenced code block
    if (/^```/.test(line)) {
      flushPara();
      const lang = line.replace(/^```\s*/, '');
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) {
        buf.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      rows.push(`<pre class="code-block"${lang ? ` data-lang="${escapeHtml(lang)}"` : ''}><code>${escapeHtml(buf.join('\n'))}</code></pre>`);
      continue;
    }

    // table
    if (/^\s*\|/.test(line)) {
      flushPara();
      const tbl = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) {
        tbl.push(lines[i].replace(/^\s*\|/, '').replace(/\|\s*$/, ''));
        i++;
      }
      const parseRow = (r) => r.split('|').map((c) => c.trim());
      let html = '<div class="table-wrap"><table>';
      tbl.forEach((r, ri) => {
        const cells = parseRow(r);
        const isHeader = ri === 0 || /^\s*:?-{2,}:?\s*$/.test(cells.join('') || '') || /^-{2,}$/.test(r.replace(/[|:\s]/g, ''));
        const tag = (ri === 0) ? 'th' : 'td';
        if (/^:?-{2,}:?$/.test(cells[0] || '') && cells.length <= 1) return; // separator row
        html += '<tr>';
        for (const c of cells) {
          let classAttr = '';
          if (c.startsWith(':') && c.endsWith(':')) classAttr = ' class="is-center"';
          else if (c.endsWith(':')) classAttr = ' class="is-right"';
          html += `<${tag}${classAttr}>${inline(c.replace(/^:|:$/g, ''))}</${tag}>`;
        }
        html += '</tr>';
      });
      rows.push(html + '</table></div>');
      continue;
    }

    if (/^\s*#/.test(line)) {
      flushPara();
      const m = line.match(/^(#{1,4})\s+(.*)$/);
      if (m) {
        const lvl = m[1].length;
        rows.push(`<h${lvl}>${inline(m[2])}</h${lvl}>`);
      }
      i++;
      continue;
    }

    if (/^\s*(?:-|\*)\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*(?:-|\*)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*(?:-|\*)\s+/, ''));
        i++;
      }
      rows.push('<ul>' + items.map((it) => `<li>${inline(it)}</li>`).join('') + '</ul>');
      continue;
    }

    if (/^\s*(\d+)\.\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i++;
      }
      rows.push('<ol>' + items.map((it) => `<li>${inline(it)}</li>`).join('') + '</ol>');
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      flushPara();
      const buf = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ''));
        i++;
      }
      rows.push('<blockquote>' + inline(buf.join(' ')) + '</blockquote>');
      continue;
    }

    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      flushPara();
      rows.push('<hr>');
      i++;
      continue;
    }

    if (line.trim() === '') {
      flushPara();
      i++;
      continue;
    }

    para.push(line.trim());
    i++;
  }
  flushPara();
  return rows.join('\n');
}

module.exports = { markdownToHtml, escapeHtml };