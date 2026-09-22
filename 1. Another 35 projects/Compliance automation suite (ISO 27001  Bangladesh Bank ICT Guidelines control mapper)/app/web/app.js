/* Compliance Automation Suite — front-end logic */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const STATUSES = ["Implemented", "Partially Implemented", "Planned", "Not Implemented", "Not Applicable"];
const STATUS_COLORS = {
  "Implemented": "#10b981",
  "Partially Implemented": "#f59e0b",
  "Planned": "#3b82f6",
  "Not Implemented": "#ef4444",
  "Not Applicable": "#64748b",
  "": "#475569",
};
const FW_NAMES = { iso27001: "ISO 27001", bbict: "BB ICT", nistcsf: "NIST CSF 2.0" };

let state = {
  fw: "iso27001",
  catalog: [],
  summary: null,
  gaps: [],
  mapFw: "iso27001",
};

/* ---------------- helpers ---------------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 2600);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

function badge(status) {
  const cls = "st-" + String(status || "none").replace(/\s+/g, "");
  return `<span class="badge ${cls}">${esc(status || "Unassessed")}</span>`;
}

function riskPill(r) {
  const cls = r >= 6 ? "risk-hi" : r >= 4 ? "risk-md" : "risk-lo";
  return `<span class="risk ${cls}">${r.toFixed(1)}</span>`;
}

/* ---------------- navigation ---------------- */
const TITLES = {
  dashboard: ["Dashboard", "Real-time compliance posture across frameworks"],
  assess: ["Control Register", "Assess controls, assign owners and record evidence"],
  mapper: ["Control Mapper", "Map any control to equivalent controls in the other frameworks"],
  gaps: ["Gap Analysis", "Prioritized open findings with risk scores and recommendations"],
  matrix: ["Crosswalk", "Framework-to-framework coverage matrix"],
  report: ["Reports", "Generate and download the auditor-ready HTML report"],
};

function show(view) {
  $$(".view").forEach(v => v.classList.add("hidden"));
  $("#view-" + view).classList.remove("hidden");
  $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $("#viewTitle").textContent = TITLES[view][0];
  $("#viewSub").textContent = TITLES[view][1];
  if (view === "dashboard") loadDashboard();
  if (view === "assess") loadAssess();
  if (view === "gaps") loadGaps();
  if (view === "matrix") loadMatrix();
}

$$(".nav-item").forEach(b => b.addEventListener("click", () => show(b.dataset.view)));

/* ---------------- dashboard ---------------- */
async function loadDashboard() {
  try {
    const s = await api("/api/summary");
    state.summary = s;
    $("#connState").textContent = "● connected";
    $("#connState").className = "ok";
    $("#overallScore").textContent = s.overall.score.toFixed(1) + "%";
    $("#overallMaturity").textContent = `Overall maturity: Level ${s.overall.maturity.level} — ${s.overall.maturity.label}`;
    $("#orgName").value = s.organization || "";

    // framework cards
    $("#fwCards").innerHTML = Object.values(s.frameworks).map(f => `
      <div class="fw-card" style="--ac:${f.accent}">
        <div class="fw-name">${esc(f.short)}</div>
        <div class="fw-desc">${esc(f.description)}</div>
        <div class="fw-score" style="color:${f.accent}">${f.score.toFixed(1)}%</div>
        <div class="bar"><div style="width:${f.score}%;background:${f.accent}"></div></div>
        <div class="fw-meta">
          <span class="chip">L${f.maturity.level} ${esc(f.maturity.label)}</span>
          <span class="chip">✓ ${f.implemented}/${f.total}</span>
          <span class="chip">◐ ${f.partial} partial</span>
          <span class="chip">✗ ${f.not_implemented} open</span>
        </div>
      </div>`).join("");

    // bars
    $("#dashBars").innerHTML = Object.values(s.frameworks).map(f => `
      <div class="bar-row">
        <div>${esc(f.short)}</div>
        <div class="bar"><div style="width:${f.score}%;background:${f.accent}"></div></div>
        <div style="text-align:right;font-weight:700">${f.score.toFixed(1)}%</div>
      </div>`).join("");

    // status distribution
    const totals = { "Implemented": 0, "Partially Implemented": 0, "Planned": 0, "Not Implemented": 0, "Not Applicable": 0 };
    Object.values(s.frameworks).forEach(f => {
      totals["Implemented"] += f.implemented;
      totals["Partially Implemented"] += f.partial;
      totals["Planned"] += f.planned;
      totals["Not Implemented"] += f.not_implemented;
      totals["Not Applicable"] += f.not_applicable;
    });
    const grand = Object.values(totals).reduce((a, b) => a + b, 0) || 1;
    $("#statusLegend").innerHTML = Object.entries(totals).map(([k, v]) =>
      `<div class="legend-item"><span class="dot" style="background:${STATUS_COLORS[k]}"></span> ${esc(k)} <span class="muted">· ${v}</span></div>`).join("");
    $("#statusBar").innerHTML = Object.entries(totals).filter(([, v]) => v > 0).map(([k, v]) =>
      `<div style="width:${(100 * v / grand).toFixed(2)}%;background:${STATUS_COLORS[k]}" title="${esc(k)}: ${v}"></div>`).join("");

    // theme heatmap (ISO themes)
    const themes = {};
    state.catalog.filter(c => c.framework === "iso27001").forEach(c => {
      themes[c.theme] = themes[c.theme] || { done: 0, tot: 0 };
      themes[c.theme].tot++;
      if (c.status === "Implemented") themes[c.theme].done++;
    });
    $("#themeHeat").innerHTML = "<h3>ISO 27001 themes — implemented</h3>" + Object.entries(themes).map(([t, v]) => `
      <div class="bar-row" style="grid-template-columns:120px 1fr 56px">
        <div>${esc(t)}</div>
        <div class="bar"><div style="width:${v.tot ? 100 * v.done / v.tot : 0}%;background:var(--purple)"></div></div>
        <div style="text-align:right">${v.done}/${v.tot}</div>
      </div>`).join("");
  } catch (e) {
    $("#connState").textContent = "● offline";
    $("#connState").className = "err";
    $("#heroStatus").textContent = "Cannot reach the local server.";
  }
}

/* ---------------- assess ---------------- */
async function loadAssess() {
  const data = await api("/api/catalog");
  state.catalog = data.catalog;

  // populate bulk status dropdown once
  const bulkSel = $("#bulkStatus");
  if (bulkSel.options.length <= 1) {
    STATUSES.forEach(s => bulkSel.add(new Option(s, s)));
  }

  renderAssess();
}

function renderAssess() {
  const q = ($("#assessSearch").value || "").toLowerCase();
  const rows = state.catalog.filter(c => c.framework === state.fw)
    .filter(c => !q || (c.id + " " + c.title + " " + c.theme + " " + (c.notes || "")).toLowerCase().includes(q));

  $("#assessTable tbody").innerHTML = rows.map(c => `
    <tr data-key="${esc(c.framework + "::" + c.id)}">
      <td><input type="checkbox" class="rowSel" data-id="${esc(c.id)}"></td>
      <td><strong>${esc(c.id)}</strong><div class="cell-sub">${esc(c.theme)}</div></td>
      <td>
        <div class="cell-title">${esc(c.title)}</div>
        ${c.description ? `<div class="cell-sub">${esc(c.description)}</div>` : ""}
        ${c.evidence ? `<div class="cell-sub">📎 ${esc(c.evidence)}</div>` : ""}
      </td>
      <td>
        <select class="input stSel" data-id="${esc(c.id)}" style="padding:6px 8px">
          <option value="">Unassessed</option>
          ${STATUSES.map(s => `<option value="${s}" ${c.status === s ? "selected" : ""}>${s}</option>`).join("")}
        </select>
      </td>
      <td><input class="input ownInp" data-id="${esc(c.id)}" value="${esc(c.owner)}" placeholder="Owner" style="padding:6px 8px"></td>
      <td><input class="input noteInp" data-id="${esc(c.id)}" value="${esc(c.notes || "")}" placeholder="Notes / evidence ref" style="padding:6px 8px"></td>
      <td><span class="row-tools" title="Save row" data-id="${esc(c.id)}">💾</span></td>
    </tr>`).join("") || `<tr><td colspan="7" class="muted" style="padding:24px">No controls match.</td></tr>`;

  $("#selCount").textContent = "0 selected";
}

function wireAssess() {
  $("#fwTabs").addEventListener("click", e => {
    const t = e.target.closest(".tab");
    if (!t) return;
    $$("#fwTabs .tab").forEach(x => x.classList.toggle("active", x === t));
    state.fw = t.dataset.fw;
    renderAssess();
  });

  $("#assessSearch").addEventListener("input", renderAssess);

  $("#assessTable").addEventListener("change", e => {
    if (e.target.classList.contains("stSel")) saveRow(e.target.dataset.id);
  });
  $("#assessTable").addEventListener("click", e => {
    const tool = e.target.closest(".row-tools");
    if (tool) saveRow(tool.dataset.id);
    const cb = e.target.closest(".rowSel");
    if (cb) updateSelCount();
  });
  $("#assessTable").addEventListener("keydown", e => {
    if (e.key === "Enter" && (e.target.classList.contains("ownInp") || e.target.classList.contains("noteInp"))) {
      e.preventDefault(); saveRow(e.target.dataset.id);
    }
  });
  $("#selAll").addEventListener("change", () => {
    $$(".rowSel").forEach(cb => { cb.checked = $("#selAll").checked; });
    updateSelCount();
  });
  $("#bulkApply").addEventListener("click", async () => {
    const ids = $$(".rowSel:checked").map(cb => cb.dataset.id);
    const status = $("#bulkStatus").value;
    if (!ids.length || !status) return toast("Select rows and a status first");
    await api("/api/bulk", { method: "POST", body: JSON.stringify({ framework: state.fw, ids, status }) });
    toast(`Updated ${ids.length} controls → ${status}`);
    loadAssess();
    updateSaved();
  });
}

function updateSelCount() {
  $("#selCount").textContent = $$(".rowSel:checked").length + " selected";
}

async function saveRow(id) {
  const tr = $(`tr[data-key="${state.fw}::${CSS.escape(id)}"]`);
  if (!tr) return;
  const payload = {
    framework: state.fw,
    id,
    status: $(".stSel", tr).value,
    owner: $(".ownInp", tr).value,
    notes: $(".noteInp", tr).value,
  };
  await api("/api/status", { method: "POST", body: JSON.stringify(payload) });
  const c = state.catalog.find(x => x.framework === state.fw && x.id === id);
  Object.assign(c, payload);
  toast(`${id} saved`);
  updateSaved();
}

function updateSaved() {
  $("#lastSaved").textContent = "Saved " + new Date().toLocaleTimeString();
}

/* ---------------- gaps ---------------- */
async function loadGaps() {
  const data = await api("/api/gaps");
  state.gaps = data.gaps;
  renderGaps();
}

function renderGaps() {
  const q = ($("#gapSearch").value || "").toLowerCase();
  const rows = state.gaps.filter(g => !q || (g.id + " " + g.title + " " + g.framework_name + " " + (g.owner || "")).toLowerCase().includes(q));
  $("#gapTable tbody").innerHTML = rows.map(g => `
    <tr>
      <td>${riskPill(g.risk)}</td>
      <td>${esc(g.framework_name)}</td>
      <td><strong>${esc(g.id)}</strong></td>
      <td><div class="cell-title">${esc(g.title)}</div><div class="cell-sub">${esc(g.theme)}</div></td>
      <td>${badge(g.status)}</td>
      <td>${esc(g.owner || "—")}</td>
      <td class="muted">${esc(g.recommendation)}</td>
    </tr>`).join("") || `<tr><td colspan="7" style="padding:24px" class="muted">🎉 No open findings — all controls implemented or N/A.</td></tr>`;
}

function wireGaps() {
  $("#gapSearch").addEventListener("input", renderGaps);
  $("#gapSave").addEventListener("click", async () => {
    const r = await api("/api/findings", { method: "POST", body: JSON.stringify({ findings: state.gaps }) });
    toast(`Saved ${r.saved} findings snapshot`);
  });
}

/* ---------------- mapper ---------------- */
async function loadMapper() {
  const fw = $("#mapFw").value || state.mapFw;
  const data = await api("/api/catalog");
  const items = data.catalog.filter(c => c.framework === fw);
  $("#mapControl").innerHTML = items.map(c => `<option value="${esc(c.id)}">${esc(c.id)} — ${esc(c.title)}</option>`).join("");
}

async function doMap() {
  const fw = $("#mapFw").value;
  const id = $("#mapControl").value;
  if (!id) return;
  const r = await api(`/api/map?framework=${fw}&id=${encodeURIComponent(id)}`);
  const src = r.source;
  $("#mapSourceTitle").textContent = `Source — ${src.id} (${FW_NAMES[fw]})`;
  $("#mapSource").innerHTML = `
    <div class="map-card">
      <span class="map-tag" style="background:${STATUS_COLORS[src.status] || "#475569"}">${esc(src.status || "Unassessed")}</span>
      <div class="cell-title">${esc(src.title)}</div>
      <div class="cell-sub">${esc(src.theme)} · ${esc(src.description || "")}</div>
    </div>`;

  const blocks = [];
  [["iso27001", "ISO 27001 Annex A"], ["bbict", "BB ICT Guideline"], ["nistcsf", "NIST CSF 2.0"]].forEach(([fwk, label]) => {
    if (fwk === fw) return;
    const items = r[fwk] || [];
    blocks.push(`<div style="margin-bottom:14px">
      <div class="map-tag" style="background:#22304d;color:#93c5fd">${label}</div>
      ${items.map(c => `
        <div class="map-card">
          <div class="cell-title">${esc(c.id)} — ${esc(c.title)}</div>
          <div class="cell-sub">${esc(c.theme)} · ${esc(c.status || "Unassessed")}</div>
        </div>`).join("") || `<div class="muted">No mapping.</div>`}
    </div>`);
  });
  $("#mapResults").innerHTML = blocks.join("");
}

function wireMapper() {
  $("#mapFw").addEventListener("change", () => { state.mapFw = $("#mapFw").value; loadMapper(); });
  $("#mapBtn").addEventListener("click", doMap);
  $("#mapControl").addEventListener("change", doMap);
}

/* ---------------- matrix ---------------- */
async function loadMatrix() {
  const data = await api("/api/matrix");
  const rows = data.matrix.map(r => `
    <div class="mx-grid" style="border:1px solid var(--line);border-radius:12px;margin-bottom:10px;background:var(--panel2)">
      <div class="mx-cell"><span class="mx-id">${esc(r.id)}</span> ${esc(r.title)}</div>
      <div class="mx-cell" style="text-align:center;font-weight:800;color:#93c5fd">${r.iso}</div>
      <div class="mx-cell" style="text-align:center;font-weight:800;color:#fcd34d">${r.nist}</div>
      <div class="mx-cell mx-sub">${esc(r.iso_ids.join(", "))} → ${esc(r.nist_ids.join(", "))}</div>
    </div>`).join("");
  $("#matrixWrap").innerHTML = `
    <div class="mx-grid">
      <div class="mx-head">BB ICT Domain</div><div class="mx-head" style="text-align:center">ISO</div>
      <div class="mx-head" style="text-align:center">NIST</div><div class="mx-head">Mapping</div>
    </div>` + rows;
}

/* ---------------- report preview ---------------- */
function wireReport() {
  $("#previewBtn").addEventListener("click", async () => {
    const res = await fetch("/api/report");
    const html = await res.text();
    const box = $("#reportPreview");
    box.style.display = "block";
    box.innerHTML = `<iframe title="Report preview"></iframe>`;
    box.querySelector("iframe").srcdoc = html;
  });
}

/* ---------------- org ---------------- */
function wireOrg() {
  $("#saveOrg").addEventListener("click", async () => {
    await api("/api/organization", { method: "POST", body: JSON.stringify({ name: $("#orgName").value }) });
    toast("Organization saved");
    updateSaved();
  });
}

/* ---------------- init ---------------- */
async function init() {
  wireAssess();
  wireGaps();
  wireMapper();
  wireReport();
  wireOrg();
  const data = await api("/api/catalog");
  state.catalog = data.catalog;
  show("dashboard");
}
init();
