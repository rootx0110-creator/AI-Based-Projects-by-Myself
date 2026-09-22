/* SOAR-Lite shared front-end helpers */
window.SOAR = (function () {
  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(path, {
      method: opts.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { const j = await res.json(); msg = j.error || msg; } catch (e) {}
      throw new Error(msg);
    }
    return res.json();
  }

  function toast(msg, kind) {
    kind = kind || "info";
    const root = document.getElementById("toast-root");
    const el = document.createElement("div");
    el.className = "toast " + kind;
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .25s"; }, 3200);
    setTimeout(() => el.remove(), 3500);
  }

  const esc = (s) =>
    String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  function rowClick(el, href) {
    el.style.cursor = "pointer";
    el.addEventListener("click", (e) => {
      if (e.target.closest("button, a, input, select, textarea, .no-nav")) return;
      window.location.href = href;
    });
  }

  function openModal(id) { document.getElementById(id).classList.add("open"); }
  function closeModal(id) { document.getElementById(id).classList.remove("open"); }
  document.addEventListener("click", (e) => {
    if (e.target.classList && e.target.classList.contains("modal-backdrop")) {
      e.target.classList.remove("open");
    }
    const x = e.target.closest("[data-close]");
    if (x) x.closest(".modal-backdrop").classList.remove("open");
  });

  // ---- inline SVG helpers (zero-dependency charts) ----
  function donut(canvasSel, items) {
    const el = document.querySelector(canvasSel);
    if (!el) return;
    const size = 170, r = 64, cx = size / 2, cy = size / 2, sw = 20;
    const total = items.reduce((s, it) => s + it.value, 0) || 1;
    let start = -Math.PI / 2;
    let g = "";
    items.forEach((it) => {
      const frac = it.value / total;
      const ang = frac * 2 * Math.PI;
      const p = arcPath(cx, cy, r, start, start + ang);
      g += `<path d="${p}" fill="none" stroke="${it.color}" stroke-width="${sw}"
             stroke-linecap="butt" opacity="${it.value ? 1 : 0}">
             <title>${esc(it.label)}: ${it.value}</title></path>`;
      start += ang;
    });
    const center = el.dataset.center || "0";
    el.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="transform:rotate(0)">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#10141c" stroke-width="${sw}"></circle>
        ${g}
      </svg>
      <div class="center"><div><div class="v">${esc(center)}</div>
      <div class="k">${esc(el.dataset.centerLabel || "total")}</div></div></div>`;
  }

  function arcPath(cx, cy, r, a0, a1) {
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const large = a1 - a0 > Math.PI ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
  }

  function bars(sel, rows) {
    const el = document.querySelector(sel);
    if (!el) return;
    const max = Math.max(1, ...rows.map((r) => r.value));
    el.innerHTML = "";
    rows.forEach((r) => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `<span class="k">${esc(r.label)}</span>
        <div class="track"><div class="fill" style="width:${(r.value / max) * 100}%;background:${r.color}"></div></div>
        <span class="num" style="text-align:right;font-family:var(--mono)">${r.value}</span>`;
      el.appendChild(row);
    });
  }

  function spark(el, points, color) {
    if (!el) return;
    const w = 120, h = 30;
    const min = Math.min(...points), max = Math.max(...points);
    const step = w / Math.max(points.length - 1, 1);
    const pts = points.map((v, i) => {
      const y = h - 4 - ((v - min) / Math.max(max - min, 1)) * (h - 8);
      return `${i * step},${y.toFixed(1)}`;
    }).join(" ");
    el.innerHTML = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
      <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="0" y1="${h - 2}" x2="${w}" y2="${h - 2}" stroke="#262b36" stroke-width="1"/></svg>`;
  }

  function clockTick() {
    const el = document.getElementById("utc-clock");
    if (el) el.textContent = new Date().toISOString().replace("T", " ").replace("Z", " UTC");
  }
  setInterval(clockTick, 1000);
  clockTick();

  // defaults for modal form fields: close when ESC pressed
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") document.querySelectorAll(".modal-backdrop.open").forEach((m) => m.classList.remove("open"));
  });

  return { api, toast, esc, rowClick, openModal, closeModal, donut, bars, spark };
})();

document.addEventListener("DOMContentLoaded", () => {
  window.SOAR.api("/api/health").then((h) => {
    const n = document.querySelectorAll("[data-health]").length;
  }).catch(() => {});
});