/* ═══════════════════════════════════════════════════════════════════════
   CTF ARENA · standalone HTML report generator
   Produces a fully self-contained .html file: summary, leaderboard,
   category matrix, per-team detail with SVG sparklines, challenge table.
   ═══════════════════════════════════════════════════════════════════════ */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmt(n) {
    return (n || 0).toLocaleString("en-US");
  }

  function svgSpark(series, color, w, h) {
    if (!series || series.length === 0) return "";
    const min = Math.min(...series), max = Math.max(...series);
    const span = Math.max(max - min, 1);
    const n = series.length;
    const pts = series
      .map((v, i) => {
        const x = (i / (n - 1)) * w;
        const y = h - ((v - min) / span) * (h - 4) - 2;
        return x.toFixed(1) + "," + y.toFixed(1);
      })
      .join(" ");
    const last = series[n - 1];
    const lx = w, ly = h - ((last - min) / span) * (h - 4) - 2;
    return (
      '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h +
      '" preserveAspectRatio="none" style="display:block">' +
      '<polyline points="' + pts + '" fill="none" stroke="' + color + '" stroke-width="2"/>' +
      '<circle cx="' + lx + '" cy="' + ly + '" r="2.6" fill="' + color + '"/></svg>'
    );
  }

  function generate(data) {
    const teams = data.teams;
    const challenges = data.challenges;
    const cats = data.categories;
    const ev = data.event;
    const now = new Date();
    const stamp = now.toLocaleString();

    // ── challenge matrix: category × solves ──
    let matrixRows = "";
    teams.forEach(t => {
      let cells = "";
      cats.forEach(c => {
        const pts = t.byCat[c.id] || 0;
        const solved = t.challenges.filter(ch => ch.cat === c.id).length;
        cells +=
          '<td class="cat-cell"><b>' + fmt(pts) + "</b><span>" + solved + " solved</span></td>";
      });
      matrixRows +=
        "<tr><td class='rank'>" + t.rank +
        "</td><td class='team'><span class='dot' style='background:" + t.color + "'></span>" +
        t.flag + " " + esc(t.name) +
        "</td>" + cells + "<td class='total'>" + fmt(t.score) + "</td></tr>";
    });

    // ── per team detail rows ──
    let teamRows = "";
    teams.forEach(t => {
      const chips = t.challenges
        .map(c =>
          '<span class="s-chip" style="border-color:' + c.catColor + '">' +
          c.catIcon + " " + esc(c.title) + ' · <b>' + fmt(c.pts) + "</b></span>"
        )
        .join("");
      teamRows +=
        "<tr><td>" + t.rank + "</td><td>" + t.flag + " " + esc(t.name) +
        "<div class='sub'>" + esc(t.tagline) + "</div></td>" +
        "<td>" + svgSpark(t.history, t.color, 200, 42) + "</td>" +
        "<td class='num'>" + fmt(t.score) +
        "<div class='sub " + (t.delta > 0 ? "up" : "") + "'>" +
        (t.delta > 0 ? "+" + fmt(t.delta) + " (30m)" : "steady") + "</div></td>" +
        "<td class='num'>" + t.solvedCount + "/" + challenges.length + "</td>" +
        "<td>" + chips + "</td></tr>";
    });

    // ── challenges table with first blood ──
    let chalRows = "";
    challenges.forEach(c => {
      const fb = c.firstBlood ? teams.find(t => t.id === c.firstBlood) : null;
      chalRows +=
        "<tr><td>" + c.catIcon + " " + esc(c.catName) + "</td>" +
        "<td>" + esc(c.title) + "</td><td class='num'>" + fmt(c.pts) + "</td>" +
        "<td class='num'>" + c.solved.length + "</td>" +
        "<td>" + (fb ? fb.flag + " " + esc(fb.name) : "—") + "</td></tr>";
    });

    // top 3 podium
    let podium = "";
    teams.slice(0, 3).forEach(t => {
      podium +=
        '<div class="pod" style="border-color:' + t.color + '">' +
        '<div class="pod-rank">#' + t.rank + "</div>" +
        '<div class="pod-name">' + t.flag + " " + esc(t.name) + "</div>" +
        '<div class="pod-score">' + fmt(t.score) + "</div></div>";
    });

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CTF Arena — Scoreboard Report</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;background:#eef2f7;padding:34px 18px}
  .wrap{max-width:1080px;margin:0 auto}
  .head{background:linear-gradient(135deg,#0b1220,#1b2b4a);color:#fff;border-radius:16px;padding:26px 28px;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px}
  .head h1{font-size:24px;letter-spacing:1px}
  .head p{color:#9db4d6;margin-top:4px;font-size:13px}
  .stamp{font:12px ui-monospace,monospace;color:#8ea3c4;text-align:right}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}
  .card{background:#fff;border:1px solid #e3e9f2;border-radius:12px;padding:14px 16px}
  .card b{font-size:22px;display:block}
  .card span{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280}
  .podium{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}
  .pod{border:2px solid;border-radius:12px;background:#fff;padding:14px;text-align:center}
  .pod-rank{font:700 12px ui-monospace,monospace;color:#6b7280}
  .pod-name{font-weight:700;margin-top:6px}
  .pod-score{font:700 20px ui-monospace,monospace;margin-top:4px}
  section{background:#fff;border:1px solid #e3e9f2;border-radius:12px;padding:20px;margin-bottom:18px;overflow:hidden}
  h2{font-size:16px;margin-bottom:12px;color:#0b1220}
  h2 small{font-weight:400;color:#6b7280;font-size:12px;margin-left:8px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#f3f6fb;color:#374151;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.8px;padding:9px 10px;border-bottom:2px solid #e3e9f2}
  td{padding:9px 10px;border-bottom:1px solid #edf1f7;vertical-align:top}
  tr:last-child td{border-bottom:none}
  .rank{font:600 12px ui-monospace,monospace;color:#6b7280}
  .team{font-weight:600}
  .total{font:700 13px ui-monospace,monospace}
  .num{font:600 12.5px ui-monospace,monospace;text-align:right}
  .dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
  .sub{font-size:11px;color:#6b7280;font-weight:400}
  .sub.up{color:#059669}
  .s-chip{display:inline-block;font-size:11px;border:1px solid;border-radius:999px;padding:2px 8px;margin:2px 2px 0 0;white-space:nowrap}
  .cat-cell b{display:block;font:700 13px ui-monospace,monospace}
  .cat-cell span{font-size:10.5px;color:#6b7280}
  .foot{text-align:center;color:#6b7280;font-size:12px;margin-top:14px}
  @media(max-width:760px){.cards{grid-template-columns:repeat(2,1fr)}.podium{grid-template-columns:1fr}}
  @media print{body{background:#fff;padding:0}section,.head{box-shadow:none;border-radius:8px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <h1>🏆 ${esc(ev.name)} — Scoreboard Report</h1>
      <p>${esc(ev.host)} · status: ${esc(ev.start)} · uptime ${esc(ev.time)}</p>
    </div>
    <div class="stamp">generated: ${esc(stamp)}<br>source: CTF Arena 3D Scoreboard</div>
  </div>

  <div class="cards">
    <div class="card"><b>${teams.length}</b><span>Teams</span></div>
    <div class="card"><b>${challenges.length}</b><span>Challenges</span></div>
    <div class="card"><b>${fmt(teams[0].score)}</b><span>Leader score</span></div>
    <div class="card"><b>${teams[0].solvedCount}</b><span>By #1 team</span></div>
  </div>

  <section>
    <h2>Podium</h2>
    <div class="podium">${podium}</div>
  </section>

  <section>
    <h2>Leaderboard <small>ranked by total score</small></h2>
    <table>
      <thead><tr><th>Rank</th><th>Team</th><th>Score trend</th><th>Score</th><th>Solved</th><th>Challenges</th></tr></thead>
      <tbody>${teamRows}</tbody>
    </table>
  </section>

  <section>
    <h2>Category Matrix <small>points per team per category</small></h2>
    <table>
      <thead><tr><th>#</th><th>Team</th>${cats.map(c => "<th>" + c.icon + " " + esc(c.name) + "</th>").join("")}<th>Total</th></tr></thead>
      <tbody>${matrixRows}</tbody>
    </table>
  </section>

  <section>
    <h2>Challenge Index <small>first blood = earliest solver</small></h2>
    <table>
      <thead><tr><th>Category</th><th>Challenge</th><th>Points</th><th>Solvers</th><th>First blood</th></tr></thead>
      <tbody>${chalRows}</tbody>
    </table>
  </section>

  <div class="foot">Generated automatically by CTF Arena · open the PDF export via your browser's print dialog (Ctrl/Cmd+P → Save as PDF)</div>
</div>
</body>
</html>`;
  }

  function download(data, filename) {
    const html = generate(data);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "ctf-scoreboard-report.html";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    return url;
  }

  global.Report = { generate, download };
})(window);