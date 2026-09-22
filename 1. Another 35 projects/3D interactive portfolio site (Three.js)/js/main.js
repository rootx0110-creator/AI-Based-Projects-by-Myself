import { PORTFOLIO, categoryById, skillById, rightCol } from "./data.js";
import { createScene } from "./scene.js";
import { build2DGrid } from "./fallback-2d.js";
import { downloadReport, downloadSkillReport } from "./report.js";

const $ = (sel) => document.querySelector(sel);

/* ------------------------------------------------------------------ */
/* DOM references                                                      */
/* ------------------------------------------------------------------ */
const container = $("#scene-container");
const loader = $("#loader");
const loaderFill = $("#loader-fill");
const chipsEl = $("#chips");
const tooltip = $("#tooltip");
const modal = $("#modal");
const aboutModal = $("#about-modal");
const searchInput = $("#search-input");

/* ------------------------------------------------------------------ */
/* Build category chips                                                */
/* ------------------------------------------------------------------ */
const catTotals = {};
PORTFOLIO.skills.forEach((s) => {
  catTotals[s.category] = (catTotals[s.category] || 0) + 1;
});

PORTFOLIO.categories.forEach((cat) => {
  const btn = document.createElement("button");
  btn.className = "chip";
  btn.dataset.cat = cat.id;
  btn.textContent = `${cat.name} · ${catTotals[cat.id] || 0}`;
  btn.style.setProperty("--chip-color", cat.color);
  btn.addEventListener("click", () => setActiveFilter(cat.id));
  if (catTotals[cat.id]) chipsEl.appendChild(btn);
});

const allChip = chipsEl.querySelector(".chip.active");
allChip.innerHTML = `All · ${PORTFOLIO.skills.length}`;

let activeFilter = "all";
let sceneAPI = null;

function setActiveFilter(id) {
  activeFilter = id;
  chipsEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
  const target = chipsEl.querySelector(`[data-cat="${id}"]`) || allChip;
  target.classList.add("active");
  const color = id === "all" ? "#29e6ff" : (categoryById(id) || {}).color || "#29e6ff";
  target.style.background = color;
  target.style.color = rightCol(color);
  if (sceneAPI) sceneAPI.applyFilter(id);
}

/* ------------------------------------------------------------------ */
/* Stats                                                               */
/* ------------------------------------------------------------------ */
const stacks = new Set(PORTFOLIO.skills.flatMap((s) => s.tech.split(",").map((t) => t.trim().toLowerCase())));
$("#stat-skills").textContent = PORTFOLIO.skills.length;
$("#stat-cats").textContent = PORTFOLIO.categories.filter((c) => catTotals[c.id]).length;
$("#stat-tech").textContent = stacks.size;

/* ------------------------------------------------------------------ */
/* Hover tooltip                                                       */
/* ------------------------------------------------------------------ */
function showTooltip(node, x, y) {
  const skill = skillById(node.id);
  const cat = categoryById(node.category);
  if (!skill || !cat) return;
  tooltip.hidden = false;
  tooltip.innerHTML = `
    <div class="tt-name">${esc(skill.name)}</div>
    <span class="tt-cat" style="background:${cat.color};color:${rightCol(cat.color)}">${esc(cat.name)}</span>
  `;
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
}
function hideTooltip() {
  tooltip.hidden = true;
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ------------------------------------------------------------------ */
/* Detail modal                                                        */
/* ------------------------------------------------------------------ */
function openSkillModal(id) {
  const skill = skillById(id);
  const cat = categoryById(skill.category);
  if (!skill || !cat) return;
  $("#modal-chip").textContent = `${cat.name} / ${catTotals[skill.category]}`;
  $("#modal-chip").style.background = cat.color;
  $("#modal-chip").style.color = rightCol(cat.color);
  $("#modal-title").textContent = skill.name;
  $("#modal-desc").textContent = skill.description;
  const tags = $("#modal-tech-tags");
  tags.innerHTML = "";
  skill.tech.split(",").forEach((t) => {
    const span = document.createElement("span");
    span.textContent = t.trim();
    tags.appendChild(span);
  });
  modal.hidden = false;
  modal._skillId = id;
  if (sceneAPI) sceneAPI.focusSkill(id);
}

$("#modal-close").addEventListener("click", () => (modal.hidden = true));
modal.addEventListener("click", (e) => {
  if (e.target === modal) modal.hidden = true;
});
$("#modal-report").addEventListener("click", () => {
  if (modal._skillId) downloadSkillReport(skillById(modal._skillId));
});

$("#about-close").addEventListener("click", () => (aboutModal.hidden = true));
aboutModal.addEventListener("click", (e) => {
  if (e.target === aboutModal) aboutModal.hidden = true;
});
$("#btn-about").addEventListener("click", () => (aboutModal.hidden = false));

/* ------------------------------------------------------------------ */
/* Search                                                              */
/* ------------------------------------------------------------------ */
searchInput.addEventListener("input", () => {
  if (sceneAPI) sceneAPI.applySearch(searchInput.value);
});

/* ------------------------------------------------------------------ */
/* Keyboard shortcuts                                                  */
/* ------------------------------------------------------------------ */
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }
  if (e.key === "Escape") {
    modal.hidden = true;
    aboutModal.hidden = true;
  }
});
chipsEl.addEventListener("click", (e) => {
  if (e.target.classList.contains("chip") && e.target.dataset.cat === "all") setActiveFilter("all");
});

/* ------------------------------------------------------------------ */
/* Scene bootstrap                                                     */
/* ------------------------------------------------------------------ */
function boot() {
  let steps = 0;
  const tick = (i) => {
    steps = Math.max(steps, i);
    loaderFill.style.width = `${Math.min(100, steps * 14)}%`;
  };

  try {
    tick(1);
    sceneAPI = createScene(container, {
      onHover: (node, x, y) => (node ? showTooltip(node, x, y) : hideTooltip()),
      onClick: (node) => openSkillModal(node.id),
      onReady: ({ nodeCount }) => {
        tick(9);
        const colours = new Set();
        PORTFOLIO.skills.forEach((s) => colours.add(s.category));
        $("#stat-cats").textContent = colours.size;
        setTimeout(() => {
          loader.classList.add("hidden");
        }, 420);
      },
    });
    tick(2);
  } catch (err) {
    console.error("3D scene init failed:", err && err.stack ? err.stack : err);
    activateFallback(err);
  }
}

function activateFallback(err) {
  loaderFill.style.width = "100%";
  loader.classList.add("hidden");
  container.style.display = "none";
  const fallbackEl = document.getElementById("fallback");
  if (!fallbackEl) return;
  fallbackEl.hidden = false;
  sceneAPI = build2DGrid(fallbackEl, { onSelect: openSkillModal });
  if (!/webgl/i.test(err.message)) {
    const meta = document.createElement("div");
    meta.style.cssText = "position:fixed;bottom:12px;left:50%;transform:translateX(-50%);z-index:120;background:#3a0f16;border:1px solid #ff6a6a;color:#ffd0d0;padding:8px 16px;border-radius:999px;font-family:monospace;font-size:12px;max-width:92vw;text-align:center;";
    meta.textContent = "Unexpected error: " + err.message + " (2D view active)";
    document.body.appendChild(meta);
  }
}

$("#btn-report").addEventListener("click", () => downloadReport());

window.addEventListener("DOMContentLoaded", boot);
setTimeout(() => {
  if (loader && !loader.classList.contains("hidden")) loader.classList.add("hidden");
}, 2600);