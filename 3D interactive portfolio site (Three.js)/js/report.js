import { PORTFOLIO, categoryById, rightCol } from "./data.js";

const esc = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function today() {
  return new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
}

const REPORT_CSS = `
:root { color-scheme: light; }
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif;
  color: #1c2733; background: #f3f6fb; line-height: 1.55; font-size: 14px;
}
.wrap { max-width: 1000px; margin: 0 auto; padding: 40px 28px 80px; }
header.hero {
  background: linear-gradient(135deg, #0a1530 0%, #123a6d 55%, #1e5fbf 100%);
  color: #fff; border-radius: 18px; padding: 42px 40px; margin-bottom: 30px;
  box-shadow: 0 18px 50px rgba(18,58,109,.35);
}
header.hero h1 { font-size: 30px; letter-spacing: .5px; margin-bottom: 10px; }
header.hero p { color: #cfe3ff; font-size: 15px; }
header.hero .meta { margin-top: 18px; font-size: 12px; color: #9fc3f5; border-top: 1px solid rgba(255,255,255,.18); padding-top: 14px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin: 26px 0; }
.stat {
  background:#fff; border:1px solid #e3eaf4; border-radius:14px; padding:18px 20px;
  box-shadow: 0 6px 20px rgba(18,58,109,.06);
}
.stat b { display:block; font-size: 30px; color: #123a6d; letter-spacing:.5px; }
.stat small { color:#6b7f98; font-size:12px; text-transform:uppercase; letter-spacing:1px; }
h2.title { font-size:20px; color:#123a6d; margin: 34px 0 16px; display:flex; align-items:center; gap:10px; }
h2.title::after { content:""; flex:1; height:1px; background:linear-gradient(90deg,#d6e2f2,transparent); }
.bars { display:grid; gap:10px; margin: 18px 0 8px; }
.bar-row { display:grid; grid-template-columns: 190px 1fr 46px; gap:12px; align-items:center; font-size:13px; }
.bar-row .nm { color:#33465e; font-weight:600; }
.bar-track { height:10px; border-radius:6px; background:#e5ecf6; overflow:hidden; }
.bar-fill { height:100%; border-radius:6px; }
.bar-val { text-align:right; font-weight:700; color:#123a6d; }
section.cat { margin: 30px 0; }
section.cat > h3 {
  font-size:17px; margin-bottom:6px; display:flex; align-items:center; gap:10px;
  color:#123a6d;
}
section.cat > h3 .dot { width:14px; height:14px; border-radius:50%; display:inline-block; }
section.cat > .sub { color:#6b7f98; font-size:12.5px; margin-bottom:14px; }
.grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:14px; }
.card {
  background:#fff; border:1px solid #e3eaf4; border-radius:14px; padding:18px 18px 16px;
  box-shadow: 0 6px 20px rgba(18,58,109,.06); display:flex; flex-direction:column; gap:10px;
}
.card h4 { font-size:15px; color:#10233f; line-height:1.35; }
.card p { font-size:13px; color:#45566d; flex:1; }
.card .tech { display:flex; flex-wrap:wrap; gap:6px; }
.card .tech span {
  font-family:"Cascadia Code", Consolas, monospace; font-size:10.5px;
  background:#eef3fb; color:#123a6d; border:1px solid #dde8f7;
  padding:3px 8px; border-radius:6px;
}
footer { margin-top:44px; text-align:center; color:#8aa0bb; font-size:12px; border-top:1px solid #e0e9f5; padding-top:20px; }
@media print {
  body { background:#fff; }
  .wrap { max-width:100%; padding:0; }
  header.hero { box-shadow:none; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .card, .stat { box-shadow:none; break-inside: avoid; }
}
`;

export function buildPortfolioReport() {
  const cats = PORTFOLIO.categories;
  const skills = PORTFOLIO.skills;
  const maxCount = Math.max(...cats.map((c) => skills.filter((s) => s.category === c.id).length));
  const stacks = new Set(skills.flatMap((s) => s.tech.split(",").map((t) => t.trim())));
  const techList = [...stacks].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase())).join(", ");

  const catSections = cats
    .map((cat) => {
      const list = skills.filter((s) => s.category === cat.id);
      if (!list.length) return "";
      const cards = list
        .map(
          (s) => `
        <div class="card">
          <h4>${esc(s.name)}</h4>
          <p>${esc(s.description)}</p>
          <div class="tech">${s.tech
            .split(",")
            .map((t) => `<span>${esc(t.trim())}</span>`)
            .join("")}</div>
        </div>`
        )
        .join("");
      return `
      <section class="cat">
        <h3><span class="dot" style="background:${cat.color}"></span>${esc(cat.name)} · ${list.length}</h3>
        <div class="sub">${list.length} ${list.length === 1 ? "skill" : "skills"} — discipline area</div>
        <div class="grid">${cards}</div>
      </section>`;
    })
    .join("");

  const bars = cats
    .map((c) => {
      const n = skills.filter((s) => s.category === c.id).length;
      const pct = Math.round((n / maxCount) * 100);
      return `
      <div class="bar-row">
        <span class="nm">${esc(c.name)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${c.color}"></div></div>
        <span class="bar-val">${n}</span>
      </div>`;
    })
    .join("");

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>${esc(PORTFOLIO.meta.title)} — Report</title>
<style>${REPORT_CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>Security Skills Atlas — Portfolio Report</h1>
    <p>${esc(PORTFOLIO.meta.tagline)}</p>
    <div class="meta">
      ${esc(PORTFOLIO.meta.author)} · Generated ${today()} · ${skills.length} skills · ${cats.length} disciplines
    </div>
  </header>

  <div class="stats">
    <div class="stat"><b>${skills.length}</b><small>Skills</small></div>
    <div class="stat"><b>${cats.length}</b><small>Disciplines</small></div>
    <div class="stat"><b>${stacks.size}</b><small>Tech Stacks</small></div>
    <div class="stat"><b>${techList.length}</b><small>Technologies</small></div>
  </div>

  <h2 class="title">Skill Distribution</h2>
  <div class="bars">${bars}</div>

  <h2 class="title">Technologies in Use</h2>
  <p>${esc(techList)}</p>

  <h2 class="title">Detailed Skill Inventory</h2>
  ${catSections}

  <footer>
    ${esc(PORTFOLIO.meta.tagline)}<br/>
    All projects were developed for legal, defensive and lab/authorized use only.
  </footer>
</div>
</body>
</html>`;
  return html;
}

export function buildSkillReport(skill, cat) {
  const tech = skill.tech.split(",").map((t) => t.trim());
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>${esc(skill.name)} — Skill Report</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:"Segoe UI", system-ui, Arial, sans-serif; background:#f3f6fb; color:#1c2733; line-height:1.6; font-size:14px; }
  .wrap { max-width:820px; margin:0 auto; padding:40px 28px; }
  .hero { border-radius:18px; padding:36px; color:#fff; margin-bottom:26px; box-shadow:0 18px 50px rgba(0,0,0,.22); }
  .hero .tag { font-size:11px; letter-spacing:2px; text-transform:uppercase; opacity:.85; }
  .hero h1 { font-size:26px; margin:10px 0 8px; line-height:1.3; }
  .pos { margin-top:16px; font-size:12px; opacity:.9; border-top:1px solid rgba(255,255,255,.25); padding-top:12px; }
  h2 { font-size:16px; margin:26px 0 10px; color:#123a6d; }
  p.desc { font-size:14.5px; color:#33465e; }
  .tech { display:flex; flex-wrap:wrap; gap:8px; }
  .tech span { font-family:Consolas, monospace; font-size:11.5px; background:#eef3fb; border:1px solid #dde8f7; color:#123a6d; padding:5px 10px; border-radius:8px; }
  .foot { margin-top:40px; color:#8aa0bb; font-size:12px; border-top:1px solid #e0e9f5; padding-top:16px; text-align:center; }
</style>
</head>
<body>
<div class="wrap">
  <div class="hero" style="background:linear-gradient(135deg,#0a1530 0%,#123a6d 60%,${cat.color} 130%)">
    <div class="tag">${esc(cat.name)} · ${esc(PORTFOLIO.meta.title)}</div>
    <h1>${esc(skill.name)}</h1>
    <div class="pos">Reported ${today()} · Skill ID: ${esc(skill.id)}</div>
  </div>
  <h2>Description</h2>
  <p class="desc">${esc(skill.description)}</p>
  <h2>Technology Stack</h2>
  <div class="tech">${tech.map((t) => `<span>${esc(t)}</span>`).join("")}</div>
  <div class="foot">${esc(PORTFOLIO.meta.tagline)}</div>
</div>
</body>
</html>`;
  return html;
}

export function downloadReport() {
  const html = buildPortfolioReport();
  downloadHTML(html, `skill-atlas-report-${new Date().toISOString().slice(0, 10)}.html`);
}

export function downloadSkillReport(skill) {
  const cat = categoryById(skill.category);
  downloadHTML(buildSkillReport(skill, cat), `${skill.id}-report.html`);
}

export function downloadHTML(html, filename) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function rightColor(hex) {
  return rightCol(hex);
}