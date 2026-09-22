/* ============================================================
   STRIDEForge — app logic: canvas, analysis, report, samples
   ============================================================ */
"use strict";

/* ---------- state ---------- */
const model = {
  name: "Untitled Architecture",
  description: "",
  elements: [],
  flows: [],
  boundaries: [],
};

let tool = "select";
let selectedId = null;
let pendingSource = null;
let drag = { active: false, id: null, ox: 0, oy: 0 };
let boundaryDrag = null;
let analysis = null;
let filter = { stride: "all", risk: "all", q: "" };
let nextId = 1;

const NODE_W = 150, NODE_H = 72;
const STRIDE_COLORS = { S: "#f43f5e", T: "#f59e0b", R: "#ca8a04", I: "#7c3aed", D: "#0284c7", E: "#059669" };
const RISK_COLORS = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };

const TYPES = {
  process: ["generic_process", "web_application", "api_service", "microservice", "worker", "batch_job", "identity_provider", "load_balancer", "firewall", "frontend", "mobile_client", "desktop_client", "iot_device"],
  data_store: ["database", "nosql_database", "cache", "message_queue", "file_storage", "search_index", "config_store"],
  external_entity: ["user", "admin", "browser", "mobile_client", "third_party", "partner_system"],
};
const TYPE_LABELS = {
  generic_process: "Process", web_application: "Web Application", api_service: "API Service",
  microservice: "Microservice", worker: "Worker / Job", batch_job: "Batch Job",
  identity_provider: "Identity Provider", load_balancer: "Load Balancer", firewall: "Firewall",
  frontend: "Frontend (SPA/Web)", mobile_client: "Mobile App", desktop_client: "Desktop App",
  iot_device: "IoT Device",
  database: "Database (SQL)", nosql_database: "NoSQL Database", cache: "Cache",
  message_queue: "Message Queue", file_storage: "File / Object Storage",
  search_index: "Search Index", config_store: "Config / Secrets Store",
  user: "User", admin: "Administrator", browser: "Web Browser", third_party: "Third-Party Service",
  partner_system: "Partner System",
};

const id = (p) => (p.value ? p.value : (p.value = "e" + (nextId++)));

/* ---------- toasts ---------- */
function toast(msg, kind) {
  const t = document.createElement("div");
  t.className = "toast" + (kind ? " " + kind : "");
  t.textContent = msg;
  document.getElementById("toasts").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 3200);
  setTimeout(() => t.remove(), 3600);
}

/* ---------- tabs ---------- */
const tabs = document.getElementById("tabs");
tabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  switchTab(btn.dataset.tab);
});
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  if (name === "analysis") renderAnalysis();
  if (name === "report") buildReportPreview();
  if (name === "canvas") render();
}

/* ---------- escaping ---------- */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ============================================================
   CANVAS RENDERING
   ============================================================ */
const $ = (sel) => document.querySelector(sel);
const svg = $("#svgCanvas");
const G = { nodes: $("#gNodes"), flows: $("#gFlows"), boundaries: $("#gBoundaries"), draft: $("#gDraft") };

function effZone(el) {
  const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
  for (const b of model.boundaries) {
    if (cx >= b.x && cx <= b.x + b.w && cy >= b.y && cy <= b.y + b.h) return b.zone || b.label || "zone";
  }
  return el.zone || "default";
}

function edgePoint(ax, ay, w, h, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const sx = (w / 2) / (Math.abs(dx) || 1e-6);
  const sy = (h / 2) / (Math.abs(dy) || 1e-6);
  const s = Math.min(1, sx, sy);
  return { x: ax + dx * s, y: ay + dy * s };
}

function nodeCenter(el) { return { x: el.x + el.w / 2, y: el.y + el.h / 2 }; }

function render() {
  renderBoundaries();
  renderFlows();
  renderNodes();
  updateDashboard();
}

function nodeMarkup(el) {
  const sel = el.id === selectedId ? ' class="sel node"' : ' class="node"';
  const cx = el.w / 2, cy = el.h / 2;
  const flags = el.flags || {};
  let shape = "";
  if (el.kind === "process") {
    shape = `<rect x="2" y="2" width="${el.w - 4}" height="${el.h - 4}" rx="14" fill="url(#nodeGrad)" stroke="${sel ? "#a78bfa" : "rgba(148,163,184,.55)"}" stroke-width="${sel ? 2.5 : 1.4}"/>`;
  } else if (el.kind === "external_entity") {
    shape = `<rect x="2" y="2" width="${el.w - 4}" height="${el.h - 4}" rx="7" fill="rgba(224,242,254,.06)" stroke="${sel ? "#7dd3fc" : "rgba(125,211,252,.5)"}" stroke-width="${sel ? 2.5 : 1.4}" stroke-dasharray="6 4"/>`;
  } else {
    const rx = (el.w - 28) / 2, ry = 13, topY = 20, botY = el.h - 20;
    shape = `<path d="M14 ${topY} a${rx} ${ry} 0 0 1 ${rx * 2} 0 v${botY - topY} a${rx} ${ry} 0 0 1 ${-rx * 2} 0 z" fill="rgba(6,182,212,.08)"
             stroke="${sel ? "#67e8f9" : "rgba(34,211,238,.55)"}" stroke-width="${sel ? 2.5 : 1.4}"/>
             <ellipse cx="${cx}" cy="${botY}" rx="${rx}" ry="${ry}" fill="none" stroke="${sel ? "#67e8f9" : "rgba(34,211,238,.55)"}" stroke-width="${sel ? 2.5 : 1.4}"/>`;
             if (sel) shape += `<ellipse cx="${cx}" cy="${topY}" rx="${rx}" ry="${ry}" fill="none" stroke="#67e8f9" stroke-width="1"/>`;
  }
  const ty = el.kind === "data_store" ? cy - 10 : cy - 6;
  const label = `<text class="node-label" x="${cx}" y="${ty}" text-anchor="middle" font-size="14">${esc(el.label)}</text>`;
  const sub = el.kind !== "data_store" ? `<text class="node-sub" x="${cx}" y="${ty + 17}" text-anchor="middle" font-size="10.5">${esc(TYPE_LABELS[el.type] || el.type)}</text>` : "";
  let badges = "";
  const bx = el.w - 22, by = 12;
  if (flags.internet) badges += `<circle cx="${bx}" cy="${by}" r="6.5" fill="#fb923c"/><text x="${bx}" y="${by + 3.5}" font-size="8" text-anchor="middle" fill="#0b1020" font-weight="800">W</text>`;
  if (flags.pii || flags.pci || flags.phi) badges += `<circle cx="${bx - 16}" cy="${by}" r="6.5" fill="#38bdf8"/><text x="${bx - 16}" y="${by + 3.5}" font-size="8" text-anchor="middle" fill="#0b1020" font-weight="800">D</text>`;
  return `<g data-kind="node" data-id="${el.id}" transform="translate(${el.x},${el.y})"${sel}>
    ${shape}${label}${sub}${badges}
    ${selectedId === el.id ? `<rect x="0" y="0" width="${el.w}" height="${el.h}" rx="14" fill="none" stroke="#8b5cf6" stroke-dasharray="4 3" stroke-width="1.2"/>` : ""}
  </g>`;
}

function renderNodes() {
  G.nodes.innerHTML = model.elements.map(nodeMarkup).join("");
}

function renderFlows() {
  const byId = {};
  model.elements.forEach((e) => (byId[e.id] = e));
  G.flows.innerHTML = model.flows.map((f) => {
    const s = byId[f.source], t = byId[f.target];
    if (!s || !t) return "";
    const c1 = nodeCenter(s), c2 = nodeCenter(t);
    const p1 = edgePoint(c1.x, c1.y, s.w, s.h, c2.x, c2.y);
    const p2 = edgePoint(c2.x, c2.y, t.w, t.h, c1.x, c1.y);
    const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2, dx = p2.x - p1.x, dy = p2.y - p1.y;
    const len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
    const off = 34;
    const qx = mx + nx * off, qy = my + ny * off;
    const crossing = effZone(s) !== effZone(t);
    const color = f.encrypted ? "#22d3ee" : crossing ? "#fbbf24" : "#8b98b4";
    const dash = crossing ? " stroke-dasharray=\"7 5\"" : "";
    const sel = f.id === selectedId ? true : false;
    const width = sel ? 3.6 : 2.4;
    return `<g data-kind="flow" data-id="${f.id}" class="flow${sel ? " sel" : ""}">
      <path data-kind="flow-hit" data-id="${f.id}" d="M${p1.x},${p1.y} Q${qx},${qy} ${p2.x},${p2.y}" fill="none" stroke="transparent" stroke-width="16" style="cursor:pointer"/>
      <path d="M${p1.x},${p1.y} Q${qx},${qy} ${p2.x},${p2.y}" fill="none" stroke="${color}" stroke-width="${width}"${dash} marker-end="url(#arrow)" style="cursor:pointer"/>
      <circle cx="${p1.x}" cy="${p1.y}" r="3.5" fill="${color}"/>
      ${f.label ? `<text x="${(p1.x + p2.x) / 2}" y="${(p1.y + p2.y) / 2 - 8}" text-anchor="middle" font-size="10.5" fill="#7dd3fc" font-weight="600">${esc(f.label)}</text>` : ""}
    </g>`;
  }).join("");
}

function labelMarkup(b) {
  const lw = Math.min(150, b.w - 8);
  return `<g data-kind="boundary" data-id="${b.id}" class="boundary${b.id === selectedId ? " sel" : ""}">
    <rect class="boundary-hit" data-bid="${b.id}" x="${b.x + 2}" y="${b.y + 2}" width="${b.w - 4}" height="${b.h - 4}" rx="10"
      fill="rgba(148,163,184,.05)" stroke="${b.id === selectedId ? "#a78bfa" : "rgba(148,163,184,.5)"}"
      stroke-width="${b.id === selectedId ? 2.2 : 1.3}" stroke-dasharray="8 6" style="cursor:pointer"/>
    <rect x="${b.x + 14}" y="${Math.max(0, b.y - 15)}" width="${lw}" height="20" rx="10" fill="rgba(139,92,246,.85)"/>
    <text x="${b.x + 14 + lw / 2}" y="${Math.max(0, b.y - 15) + 14}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">${esc(b.label || b.zone || "Boundary")}</text>
  </g>`;
}

function renderBoundaries() {
  G.boundaries.innerHTML = model.boundaries.map(labelMarkup).join("");
}

/* ---------- canvas pointer events ---------- */
function svgPointFromEvent(e) {
  const rect = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const x = vb.x + ((e.clientX - rect.left) / rect.width) * vb.width;
  const y = vb.y + ((e.clientY - rect.top) / rect.height) * vb.height;
  return { x: x, y: y };
}

svg.addEventListener("mousedown", onMouseDown);
svg.addEventListener("mousemove", onMouseMove);
window.addEventListener("mouseup", onMouseUp);

function hitNode(ev) {
  const el = ev.target;
  if (el.closest) {
    const g = el.closest('[data-kind="node"]');
    if (g) return model.elements.find((e) => e.id === g.dataset.id);
  }
  return null;
}
function hitFlow(ev) {
  const el = ev.target;
  if (el.closest) {
    const g = el.closest('[data-kind="flow"], [data-kind="flow-hit"]');
    if (g) return model.flows.find((f) => f.id === g.dataset.id);
  }
  return null;
}
function hitBoundary(ev) {
  const el = ev.target;
  if (el.closest) {
    const g = el.closest('[data-kind="boundary"]');
    if (g) return model.boundaries.find((b) => b.id === g.dataset.id);
  }
  return null;
}

function onMouseDown(ev) {
  const p = svgPointFromEvent(ev);
  const node = hitNode(ev);
  const flow = hitFlow(ev);
  const bnd = hitBoundary(ev);

  if (tool === "process" || tool === "store" || tool === "entity") {
    const kind = { process: "process", store: "data_store", entity: "external_entity" }[tool];
    const defType = kind === "process" ? "generic_process" : kind === "data_store" ? "database" : "user";
    const el = { id: "e" + (nextId++), kind, type: defType, label: "", zone: "default", flags: {}, x: Math.round(p.x - NODE_W / 2), y: Math.round(p.y - NODE_H / 2), w: NODE_W, h: NODE_H };
    el.label = TYPE_LABELS[defType] || defType;
    model.elements.push(el);
    selectedId = el.id;
    tool = "select";
    setTool("select");
    render();
    showProps();
    return;
  }

  if (tool === "boundary") {
    boundaryDrag = { x0: p.x, y0: p.y };
    return;
  }

  if (tool === "flow") {
    if (node) {
      if (!pendingSource) { pendingSource = node.id; toast("Select the target to connect →", ""); highlightPending(); }
      else if (pendingSource === node.id) { /* ignore */ }
      else {
        addFlow(pendingSource, node.id);
        pendingSource = null;
        highlightPending();
      }
    } else { pendingSource = null; highlightPending(); }
    renderDraft();
    return;
  }

  if (tool === "entry") {
    if (node) { node.flags.internet = !node.flags.internet; render(); showProps(); }
    return;
  }

  if (tool === "delete") {
    if (node) delElement(node.id);
    else if (flow) delFlow(flow.id);
    else if (bnd) delBoundary(bnd.id);
    return;
  }

  if (tool === "select") {
    if (node) {
      selectedId = node.id;
      drag = { active: true, id: node.id, dx: p.x - node.x, dy: p.y - node.y };
      render();
      showProps();
    } else if (flow) {
      selectedId = flow.id; render(); showProps();
    } else if (bnd) {
      selectedId = bnd.id; render(); showProps();
    } else {
      selectedId = null; render(); showProps();
    }
  }
}

function onMouseMove(ev) {
  if (boundaryDrag && tool === "boundary") {
    const p = svgPointFromEvent(ev);
    renderDraft(p.x, p.y);
    return;
  }
  if (drag.active && tool === "select") {
    const p = svgPointFromEvent(ev);
    const el = model.elements.find((e) => e.id === drag.id);
    if (el) { el.x = Math.round(p.x - drag.dx); el.y = Math.round(p.y - drag.dy); render(); }
  }
}
function onMouseUp(ev) {
  if (boundaryDrag) {
    const p = svgPointFromEvent(ev);
    let x0 = Math.min(boundaryDrag.x0, p.x), y0 = Math.min(boundaryDrag.y0, p.y);
    const w = Math.abs(p.x - boundaryDrag.x0), h = Math.abs(p.y - boundaryDrag.y0);
    if (w > 30 && h > 30) {
      const name = "Zone " + (model.boundaries.length + 1);
      const b = { id: "b" + (nextId++), label: name, zone: "internal", x: Math.round(x0), y: Math.round(y0), w: Math.round(w), h: Math.round(h) };
      model.boundaries.push(b);
      selectedId = b.id;
      showProps();
    }
    boundaryDrag = null;
    render();
  }
  drag.active = false;
  gDraftClear();
}

function addFlow(src, tgt) {
  model.flows.push({ id: "f" + (nextId++), source: src, target: tgt, label: "", encrypted: false, authenticated: false });
  selectedId = null;
  render();
  toast("Data flow added", "ok");
}

function delElement(nodeId) {
  model.elements = model.elements.filter((e) => e.id !== nodeId);
  model.flows = model.flows.filter((f) => f.source !== nodeId && f.target !== nodeId);
  if (selectedId === nodeId) selectedId = null;
  render(); showProps();
}
function delFlow(fid) { model.flows = model.flows.filter((f) => f.id !== fid); if (selectedId === fid) selectedId = null; render(); showProps(); }
function delBoundary(bid) { model.boundaries = model.boundaries.filter((b) => b.id !== bid); if (selectedId === bid) selectedId = null; render(); showProps(); }

function renderDraft(mx, my) {
  if (!boundaryDrag) { gDraftClear(); return; }
  const x0 = boundaryDrag.x0, y0 = boundaryDrag.y0;
  const p = { x: mx ?? x0, y: my ?? y0 };
  const x = Math.min(x0, p.x), y = Math.min(y0, p.y), w = Math.abs(p.x - x0), h = Math.abs(p.y - y0);
  G.draft.innerHTML = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="rgba(139,92,246,.08)"
    stroke="#8b5cf6" stroke-width="1.5" stroke-dasharray="8 6"/>`;
}
function gDraftClear() {
  if (!boundaryDrag) {
    if (pendingSource) {
      const s = model.elements.find((e) => e.id === pendingSource);
      if (s) G.draft.innerHTML = `<rect x="${s.x - 4}" y="${s.y - 4}" width="${s.w + 8}" height="${s.h + 8}" rx="14" fill="none" stroke="#22d3ee" stroke-width="2.5"/>`;
    } else G.draft.innerHTML = "";
  }
}
function highlightPending() {
  gDraftClear();
  const s = model.elements.find((e) => e.id === pendingSource);
  if (s) G.draft.innerHTML = `<rect x="${s.x - 4}" y="${s.y - 4}" width="${s.w + 8}" height="${s.h + 8}" rx="14" fill="none" stroke="#22d3ee" stroke-width="2.5"/>`;
}

/* ---------- toolbar ---------- */
function setTool(t) {
  tool = t;
  document.querySelectorAll(".tool[data-tool]").forEach((b) => b.classList.toggle("active", b.dataset.tool === t));
  pendingSource = null; boundaryDrag = null; gDraftClear();
}
document.querySelectorAll(".tool[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
document.getElementById("btnClearImage").addEventListener("click", () => {
  const img = $("#bgImageTrace");
  img.style.display = "none"; img.setAttribute("href", "");
  toast("Tracing image removed");
});

/* trace image */
function bindImageInput(inputId) {
  document.getElementById(inputId).addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      const img = $("#bgImageTrace");
      img.setAttribute("href", r.result);
      img.style.display = "block";
      toast("Image loaded - place components over it to trace");
    };
    r.readAsDataURL(f);
    e.target.value = "";
  });
}
["fileImage", "fileImage2"].forEach(bindImageInput);

/* rename on double click */
svg.addEventListener("dblclick", (ev) => {
  const node = hitNode(ev);
  if (!node) return;
  setTool("select"); selectedId = node.id; showProps();
  const lab = $("#pfLabel");
  lab.focus(); lab.select();
});

/* ---------- keyboard ---------- */
document.addEventListener("keydown", (e) => {
  const tag = (e.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return;
  if (e.key === "Delete" || e.key === "Backspace") {
    if (!selectedId) return;
    if (model.elements.find((x) => x.id === selectedId)) delElement(selectedId);
    else if (model.flows.find((x) => x.id === selectedId)) delFlow(selectedId);
    else if (model.boundaries.find((x) => x.id === selectedId)) delBoundary(selectedId);
  } else if (e.key === "Escape") {
    setTool("select");
  } else if (e.key.toLowerCase() === "v") setTool("select");
  else if (e.key.toLowerCase() === "p") setTool("process");
  else if (e.key.toLowerCase() === "s") setTool("store");
  else if (e.key.toLowerCase() === "e") setTool("entity");
  else if (e.key.toLowerCase() === "f") setTool("flow");
  else if (e.key.toLowerCase() === "b") setTool("boundary");
  else if (e.key.toLowerCase() === "d") setTool("delete");
});

/* ---------------- properties panel ---------------- */
function showProps() {
  const empty = $("#propsEmpty"), pe = $("#propsEl"), pf = $("#propsFlow"), pb = $("#propsBoundary");
  empty.style.display = pe.style.display = pf.style.display = pb.style.display = "none";
  $("#modelName").value = model.name;

  if (selectedId) {
    const el = model.elements.find((e) => e.id === selectedId);
    const flow = model.flows.find((f) => f.id === selectedId);
    const bnd = model.boundaries.find((b) => b.id === selectedId);
    if (el) {
      pe.style.display = "block";
      const badge = $("#pfBadge");
      badge.textContent = el.kind === "process" ? "P" : el.kind === "data_store" ? "D" : "E";
      $("#pfLabel").value = el.label || "";
      const typeSel = $("#pfType");
      typeSel.innerHTML = (TYPES[el.kind] || []).map((t) => `<option value="${t}" ${t === el.type ? "selected" : ""}>${TYPE_LABELS[t] || t}</option>`).join("");
      $("#pfZone").value = el.zone || "default";
      document.querySelectorAll("#propsEl [data-flag]").forEach((ch) => {
        const f = ch.dataset.flag;
        ch.checked = !!(el.flags && el.flags[f]);
        ch.closest(".chk").classList.toggle("has", ch.checked);
        ch.closest(".chk").querySelector(".pch").textContent = ch.checked ? "✓" : "";
      });
    } else if (flow) {
      pf.style.display = "block";
      $("#pfFlowLabel").value = flow.label || "";
      const s = model.elements.find((e) => e.id === flow.source);
      const t = model.elements.find((e) => e.id === flow.target);
      $("#pfFlowEnds").innerHTML = `<b>${esc((s && s.label) || flow.source)}</b> ⇢ <b>${esc((t && t.label) || flow.target)}</b>`;
      document.querySelectorAll("#propsFlow [data-fflag]").forEach((ch) => {
        const f = ch.dataset.fflag;
        ch.checked = !!flow[f];
        ch.closest(".chk").classList.toggle("has", ch.checked);
        ch.closest(".chk").querySelector(".pch").textContent = ch.checked ? "✓" : "";
      });
    } else if (bnd) {
      pb.style.display = "block";
      $("#pfBoundaryLabel").value = bnd.label || "";
      $("#pfBoundaryZone").value = bnd.zone || "";
    }
  } else {
    empty.style.display = "block";
    const els = model.elements.length, fl = model.flows.length, bd = model.boundaries.length;
    $("#modelStat").textContent = `${els} components · ${fl} flows · ${bd} boundaries`;
  }
}

/* wiring props inputs */
$("#modelName").addEventListener("input", (e) => { model.name = e.target.value; updateDashboard(); });
$("#pfLabel").addEventListener("input", (e) => {
  const el = model.elements.find((x) => x.id === selectedId);
  if (el) { el.label = e.target.value; render(); }
});
$("#pfType").addEventListener("change", (e) => {
  const el = model.elements.find((x) => x.id === selectedId);
  if (el) { el.type = e.target.value; render(); }
});
$("#pfZone").addEventListener("change", (e) => {
  const el = model.elements.find((x) => x.id === selectedId);
  if (el) { el.zone = e.target.value; render(); }
});
$("#pfFlowLabel").addEventListener("input", (e) => {
  const f = model.flows.find((x) => x.id === selectedId);
  if (f) { f.label = e.target.value; render(); }
});
$("#pfBoundaryLabel").addEventListener("input", (e) => {
  const b = model.boundaries.find((x) => x.id === selectedId);
  if (b) { b.label = e.target.value; render(); }
});
$("#pfBoundaryZone").addEventListener("input", (e) => {
  const b = model.boundaries.find((x) => x.id === selectedId);
  if (b) { b.zone = e.target.value; render(); }
});
document.querySelectorAll("#propsEl [data-flag]").forEach((ch) => ch.addEventListener("change", () => {
  const el = model.elements.find((x) => x.id === selectedId);
  if (!el) return;
  el.flags = el.flags || {}; el.flags[ch.dataset.flag] = ch.checked;
  ch.closest(".chk").classList.toggle("has", ch.checked);
  ch.closest(".chk").querySelector(".pch").textContent = ch.checked ? "✓" : "";
  render();
}));
document.querySelectorAll("#propsFlow [data-fflag]").forEach((ch) => ch.addEventListener("change", () => {
  const f = model.flows.find((x) => x.id === selectedId);
  if (!f) return;
  f[ch.dataset.fflag] = ch.checked;
  ch.closest(".chk").classList.toggle("has", ch.checked);
  ch.closest(".chk").querySelector(".pch").textContent = ch.checked ? "✓" : "";
  render();
}));

/* ---------- dashboard ---------- */
function updateDashboard() {
  $("#modelName").value = model.name;
  const els = model.elements.length, fl = model.flows.length, bd = model.boundaries.length;
  $("#sEls").textContent = els; $("#sFlows").textContent = fl; $("#sZones").textContent = bd;
  $("#dashEls").textContent = `${els} / ${fl}`;
  if (analysis) {
    const s = analysis.summary;
    $("#dashOverall").textContent = s.overall;
    $("#dashTotal").textContent = s.total;
    $("#dashCrit").textContent = s.by_risk.Critical;
    $("#dashHigh").textContent = s.by_risk.High;
    $("#dashMed").textContent = s.by_risk.Medium;
    $("#sThreats").textContent = s.total;
    $("#sAvg").textContent = s.avg_dread;
  }
}

/* ============================================================
   ANALYSIS
   ============================================================ */
async function runAnalysis() {
  const btn = $("#btnAnalyze");
  btn.textContent = "Analyzing…";
  btn.disabled = true;
  try {
    const res = await fetch("/api/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(model),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Analysis failed");
    analysis = data;
    updateDashboard();
    switchTab("analysis");
    toast(`Analysis complete: ${data.summary.total} threats`, "ok");
  } catch (err) {
    toast(err.message || "Analysis failed", "err");
  } finally {
    btn.textContent = "Analyze Risk";
    btn.disabled = false;
  }
}
function rerun() { runAnalysis(); }
document.getElementById("btnAnalyze").addEventListener("click", runAnalysis);
document.getElementById("btnRerun").addEventListener("click", rerun);

function strideChipsHTML() {
  const counts = analysis ? analysis.summary.by_stride : {};
  let html = `<button class="chip ${filter.stride === "all" ? "active" : ""}" data-stride="all">All</button>`;
  for (const [k, name] of Object.entries({ S: "Spoofing", T: "Tampering", R: "Repudiation", I: "Info Disclosure", D: "Denial of Service", E: "Elevation of Privilege" })) {
    const n = counts[k] || 0;
    html += `<button class="chip ${filter.stride === k ? "active" : ""}" data-stride="${k}" style="${filter.stride === k ? `background:${STRIDE_COLORS[k]};border-color:transparent` : ""}">${k} · ${name} (${n})</button>`;
  }
  return html;
}

function bindAnalysisFilters() {
  const chips = $("#strideChips");
  chips.addEventListener("click", (e) => {
    const c = e.target.closest("[data-stride]");
    if (!c) return;
    filter.stride = c.dataset.stride;
    chips.innerHTML = strideChipsHTML();
    renderThreats();
  });
  document.querySelectorAll(".risk-filter .chip").forEach((c) => c.addEventListener("click", () => {
    filter.risk = c.dataset.risk;
    document.querySelectorAll(".risk-filter .chip").forEach((x) => x.classList.toggle("active", x === c));
    renderThreats();
  }));
  $("#threatSearch").addEventListener("input", (e) => { filter.q = e.target.value.toLowerCase(); renderThreats(); });
}

function renderAnalysis() {
  const empty = $("#analysisEmpty"), list = $("#threatList");
  if (!analysis) {
    empty.style.display = "block";
    list.innerHTML = "";
    $("#anGrade").textContent = "—";
    $("#anStats").innerHTML = "";
    $("#strideChips").innerHTML = "";
    return;
  }
  empty.style.display = "none";
  const s = analysis.summary;
  const grade = $("#anGrade");
  grade.className = "an-grade an-grade-" + s.overall.toLowerCase();
  grade.innerHTML = s.overall + "<span>overall risk</span>";
  $("#anStats").innerHTML = `
    <div class="an-stat"><b>${s.total}</b><span>Total threats</span></div>
    <div class="an-stat"><b class="c-crit">${s.by_risk.Critical}</b><span>Critical</span></div>
    <div class="an-stat"><b class="c-high">${s.by_risk.High}</b><span>High</span></div>
    <div class="an-stat"><b class="c-med">${s.by_risk.Medium}</b><span>Medium</span></div>
    <div class="an-stat"><b>${s.avg_dread}</b><span>Avg DREAD</span></div>`;
  $("#strideChips").innerHTML = strideChipsHTML();
  document.querySelectorAll(".risk-filter .chip").forEach((c) => c.classList.toggle("active", c.dataset.risk === filter.risk));
  renderThreats();
}

function threatsBindTopLevel() {} // reserved
function renderThreats() {
  if (!analysis) return;
  const q = filter.q;
  const list = analysis.threats.filter((t) =>
    (filter.stride === "all" || t.stride === filter.stride) &&
    (filter.risk === "all" || t.risk === filter.risk) &&
    (!q || (t.title + " " + t.element_label + " " + t.description + " " + t.mitigation).toLowerCase().includes(q))
  );
  const box = $("#threatList");
  if (!list.length) {
    box.innerHTML = `<div class="empty-state" style="padding:50px"><b>No threats match</b><p>Try clearing filters.</p></div>`;
    return;
  }
  box.innerHTML = list.map(threatCard).join("");
}

function threatCard(t) {
  const dr = ["damage", "reproducibility", "exploitability", "affected_users", "discoverability"];
  const bars = dr.map((k) => {
    const v = t.dread[k] || 0;
    const w = (v / 10) * 100;
    return `<div class="dr"><div class="dr-cap">${shortFactor(k)}</div>
      <div class="dr-track"><div class="dr-fill" style="width:${w}%"></div></div>
      <div class="dr-val">${v}</div></div>`;
  }).join("");
  const notes = (t.context_notes && t.context_notes.length)
    ? `<div class="tc-notes">↳ ${esc(t.context_notes.join("; "))}</div>` : "";
  return `<div class="threat-card tc-${t.stride}">
    <div class="tc-top">
      <div>
        <span class="tc-title">${esc(t.title)}</span>
        <div class="tc-meta">
          <span class="stride-badge sb-${t.stride}">${t.stride} · ${esc(t.stride_name)}</span>
          <span class="risk-badge rb-${t.risk}">${t.risk}</span>
          <span>${t.id}</span>
          <span>${esc(t.element_label)} <span style="text-transform:capitalize">(${esc(t.element_kind.replace("_", " "))})</span> · zone ${esc(t.element_zone || "-")}</span>
        </div>
      </div>
      <div class="tc-total" style="font-size:22px;font-weight:800;color:${RISK_COLORS[t.risk]}">${t.dread_total}<span style="font-size:12px;color:var(--muted);font-weight:600">/50</span></div>
    </div>
    <div class="tc-desc">${esc(t.description)}</div>
    <div class="tc-mit"><b>Mitigation:</b> ${esc(t.mitigation)}</div>
    ${notes}
    <div class="dread-bars" style="margin-top:10px">${bars}</div>
  </div>`;
}
function shortFactor(k) {
  return { damage: "Damage", reproducibility: "Reprod.", exploitability: "Exploit", affected_users: "Affected", discoverability: "Discover" }[k] || k;
}

bindAnalysisFilters();

/* ============================================================
   REPORT
   ============================================================ */
async function buildReportPreview() {
  const frame = $("#reportFrame"), load = $("#reportLoading");
  if (!analysis && !(model.elements.length || model.flows.length)) {
    frame.srcdoc = "";
    return;
  }
  load.style.display = "flex";
  try {
    const title = $("#reportTitle").value.trim() || model.name;
    const doc = await fetchReport({ ...model, name: title });
    frame.srcdoc = doc;
  } catch (e) { toast(e.message, "err"); }
  load.style.display = "none";
}

async function fetchReport(mdl) {
  const res = await fetch("/api/report", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(mdl),
  });
  if (!res.ok) {
    let msg = "Report failed";
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return await res.text();
}

function downloadReport() {
  if (!model.elements.length && !model.flows.length) { toast("Architecture is empty - nothing to report", "err"); return; }
  const title = $("#reportTitle").value.trim() || model.name;
  fetchReport({ ...model, name: title }).then((doc) => {
    const blob = new Blob([doc], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const safe = (title || "threat-model").replace(/[^\w\- ]+/g, "").replace(/ +/g, "_");
    a.download = "Threat_Model_Report_" + safe + ".html";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    toast("Report downloaded", "ok");
  }).catch((e) => toast(e.message, "err"));
}
document.getElementById("btnDownloadReport").addEventListener("click", downloadReport);
document.getElementById("btnGotoReport").addEventListener("click", () => { downloadReport(); switchTab("report"); });
document.getElementById("reportTitle").addEventListener("input", () => buildReportPreview());

/* ============================================================
   SAMPLES
   ============================================================ */
function el(id, kind, type, label, x, y, zone, flags) {
  return { id, kind, type, label, x, y, w: NODE_W, h: NODE_H, zone: zone || "default", flags: flags || {} };
}
function bdry(id, label, zone, x, y, w, h) { return { id, label, zone, x, y, w, h }; }
function flw(id, s, t, encrypted, authenticated) { return { id, source: s, target: t, label: "", encrypted: !!encrypted, authenticated: !!authenticated }; }

const SAMPLES = {
  ecom: {
    name: "E-Commerce Web Application",
    description: "Online storefront with CDN, load balancer, web/API tier, worker, message queue, cache, relational database and payment gateway partner.",
    boundaries: [
      bdry("b1", "Internet", "internet", 0, 20, 420, 860),
      bdry("b2", "DMZ", "dmz", 440, 20, 360, 400),
      bdry("b3", "Internal Network", "internal", 820, 20, 430, 860),
      bdry("b4", "Restricted Data", "restricted", 1260, 20, 340, 400),
    ],
    elements: [
      el("e1", "external_entity", "user", "Customer", 60, 420, "", { internet: true }),
      el("e2", "process", "frontend", "Browser (SPA)", 90, 640, "", { internet: true }),
      el("e3", "process", "load_balancer", "CDN", 500, 560, "dmz", { internet: true }),
      el("e4", "process", "load_balancer", "Load Balancer", 680, 320, "dmz", {}),
      el("e5", "process", "web_application", "Web Application", 480, 120, "dmz", { internet: true, authn: true, rate_limited: true }),
      el("e6", "process", "api_service", "Orders API", 900, 120, "internal", { authn: true, authz: true, pii: true }),
      el("e7", "process", "worker", "Order Worker", 1000, 640, "internal", { pii: true }),
      el("e8", "data_store", "message_queue", "Order Queue", 610, 660, "internal", {}),
      el("e9", "data_store", "cache", "Session Cache", 1040, 520, "internal", {}),
      el("e10", "data_store", "database", "Orders DB", 1340, 120, "restricted", { pci: true, encrypted: true, logged: true }),
      el("e11", "external_entity", "third_party", "Payment Gateway", 1370, 560, "partner", {}),
    ],
    flows: [
      flw("f1", "e1", "e3", true, true), flw("f2", "e2", "e3", true, true),
      flw("f3", "e3", "e4", true, true), flw("f4", "e4", "e5", true, true),
      flw("f5", "e5", "e6", true, false), flw("f6", "e6", "e9", false, true),
      flw("f7", "e6", "e8", false, false), flw("f8", "e8", "e7", false, false),
      flw("f9", "e7", "e10", true, false), flw("f10", "e6", "e10", true, false),
      flw("f11", "e6", "e11", true, true),
    ],
  },
  micro: {
    name: "Microservices Platform",
    description: "API gateway over a service mesh with auth, order and inventory services, per-service databases, Kafka events and a third-party shipping API.",
    boundaries: [
      bdry("b1", "Internet", "internet", 0, 60, 300, 780),
      bdry("b2", "Platform DMZ", "dmz", 330, 60, 330, 780),
      bdry("b3", "Core Services", "internal", 690, 60, 520, 780),
      bdry("b4", "Data & Partners", "restricted", 1240, 60, 360, 780),
    ],
    elements: [
      el("m1", "external_entity", "mobile_client", "Mobile App", 60, 360, "", { internet: true }),
      el("m2", "process", "api_service", "API Gateway", 400, 360, "dmz", { internet: true, authn: true, rate_limited: true }),
      el("m3", "process", "identity_provider", "Auth Service", 760, 160, "internal", { authn: true, logged: true }),
      el("m4", "process", "microservice", "Order Service", 760, 420, "internal", { pii: true, authz: true }),
      el("m5", "process", "microservice", "Inventory Service", 760, 640, "internal", { authz: true }),
      el("m6", "data_store", "message_queue", "Event Bus (Kafka)", 620, 830, "internal", {}),
      el("m7", "data_store", "nosql_database", "Orders Store", 1330, 160, "restricted", { pii: true, encrypted: true }),
      el("m8", "data_store", "database", "Inventory DB", 1330, 420, "restricted", { encrypted: true }),
      el("m9", "external_entity", "third_party", "Shipping API", 1330, 680, "partner", {}),
    ],
    flows: [
      flw("g1", "m1", "m2", true, true), flw("g2", "m2", "m3", false, true),
      flw("g3", "m2", "m4", true, true), flw("g4", "m2", "m5", true, true),
      flw("g5", "m3", "m4", false, true), flw("g6", "m4", "m6", false, false),
      flw("g7", "m5", "m6", false, false), flw("g8", "m6", "m4", false, false),
      flw("g9", "m6", "m5", false, false), flw("g10", "m4", "m7", true, false),
      flw("g11", "m5", "m8", true, false), flw("g12", "m4", "m9", true, true),
    ],
  },
  legacy: {
    name: "Legacy 3-Tier Environment",
    description: "Classic on-premise 3-tier deployment: users, single web server hosting app tier, SQL Server backend and a shared network drive.",
    boundaries: [
      bdry("b1", "Untrusted Network", "internet", 0, 100, 380, 700),
      bdry("b2", "On-Premise LAN", "internal", 420, 100, 520, 700),
      bdry("b3", "Backend & Storage", "restricted", 980, 100, 400, 700),
    ],
    elements: [
      el("l1", "external_entity", "user", "End User", 90, 400, "", {}),
      el("l2", "process", "web_application", "IIS Web Server (App Tier)", 480, 180, "internal", { pii: true }),
      el("l3", "data_store", "database", "SQL Server", 1060, 220, "restricted", { pii: true }),
      el("l4", "data_store", "file_storage", "Shared Network Drive", 1060, 560, "restricted", { pii: true }),
    ],
    flows: [
      flw("k1", "l1", "l2", false, false), flw("k2", "l2", "l3", false, false),
      flw("k3", "l2", "l4", false, false),
    ],
  },
};

function renderSamples() {
  const list = $("#sampleList");
  const items = [
    { key: "ecom", icon: "🛒", title: "E-Commerce Web App", desc: "Storefront with CDN, payment gateway, cache & workers." },
    { key: "micro", icon: "🧩", title: "Microservices Platform", desc: "API gateway, service mesh, event bus, per-service DBs." },
    { key: "legacy", icon: "🏢", title: "Legacy 3-Tier", desc: "On-premise web / app / SQL Server + network drive." },
  ];
  list.innerHTML = items.map((it) => `
    <button class="sample-card" data-key="${it.key}"><div class="sc-icon">${it.icon}</div>
      <div class="sc-t"><b>${it.title}</b><span>${it.desc}</span></div></button>`).join("");
  list.querySelectorAll(".sample-card").forEach((c) => c.addEventListener("click", () => loadSample(c.dataset.key)));
}
function loadSample(key) {
  const s = JSON.parse(JSON.stringify(SAMPLES[key]));
  Object.assign(model, s);
  selectedId = null; analysis = null;
  nextId = 1000;
  $("#reportTitle").value = "";
  switchTab("canvas");
  render(); showProps();
  toast("Sample loaded: " + s.name, "ok");
}
document.getElementById("btnLoadEcom").addEventListener("click", () => loadSample("ecom"));
document.getElementById("btnNewCanvas").addEventListener("click", () => switchTab("canvas"));
document.getElementById("btnNewModel").addEventListener("click", () => {
  model.name = "Untitled Architecture"; model.description = ""; model.elements = []; model.flows = []; model.boundaries = [];
  selectedId = null; analysis = null;
  switchTab("canvas"); render(); showProps();
  toast("Blank architecture created");
});

/* ---------- import / export ---------- */
document.getElementById("btnExport").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(model, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "architecture.json";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
});
document.getElementById("fileImport").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      const d = JSON.parse(r.result);
      if (!d.elements) throw new Error("invalid model");
      Object.assign(model, { elements: d.elements || [], flows: d.flows || [], boundaries: d.boundaries || [] }, d.name ? { name: d.name } : {}, d.description !== undefined ? { description: d.description } : {});
      selectedId = null; analysis = null;
      switchTab("canvas"); render(); showProps();
      toast("Architecture imported", "ok");
    } catch (err) { toast("Import failed: " + err.message, "err"); }
  };
  r.readAsText(f);
  e.target.value = "";
});

/* ============================================================
   INIT
   ============================================================ */
renderSamples();
render();
showProps();