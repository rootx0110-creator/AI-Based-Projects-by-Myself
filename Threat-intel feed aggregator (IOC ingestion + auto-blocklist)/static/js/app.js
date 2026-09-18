"use strict";

const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async put(path, body) {
    const res = await fetch(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async patch(path, body) {
    const res = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async del(path) {
    const res = await fetch(path, { method: "DELETE" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

function toast(msg, kind = "info", ms = 4200) {
  const wrap = document.getElementById("toastWrap");
  const el = document.createElement("div");
  el.className = "toast" + (kind === "err" ? " err" : kind === "ok" ? " ok" : "");
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

function fmtDate(iso) {
  if (!iso) return "—";
  const parts = iso.replace("T", " ").split(".")[0];
  return parts;
}

function fmtSize(bytes) {
  if (!bytes && bytes !== 0) return "—";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(2) + " MB";
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function badgeForType(t) {
  return `<span class="badge badge-${escapeHtml(t)}">${escapeHtml(t)}</span>`;
}

function badgeForSeverity(s) {
  return `<span class="badge badge-${escapeHtml(s || "low")}">${escapeHtml(s || "low")}</span>`;
}

function truncate(v, n = 44) {
  v = String(v);
  return v.length > n ? v.slice(0, n - 3) + "…" : v;
}

async function ingestAllFeeds(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Ingesting…"; }
  try {
    const data = await api.post("/api/ingest-all");
    const ok = data.results.filter((r) => r.status === "success").length;
    const err = data.results.length - ok;
    toast(`Ingestion complete: ${ok} feeds OK, ${err} failed`, err ? "err" : "ok");
  } catch (e) {
    toast("Ingestion failed: " + e.message, "err");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "↻ Ingest All Feeds"; }
  }
}

function watchClock() {
  const el = document.getElementById("clock");
  if (!el) return;
  const tick = () => {
    const d = new Date();
    el.textContent = d.toLocaleString([], { hour12: false, dateStyle: "short", timeStyle: "medium" });
  };
  tick();
  setInterval(tick, 1000);
}

function highlightNav() {
  const page = location.pathname.split("/")[1] || "index";
  document.querySelectorAll(".nav-link").forEach((a) => {
    a.classList.toggle("active", a.dataset.page === page);
  });
  const titles = { index: "Dashboard", feeds: "Feeds", iocs: "Indicators", blocklist: "Blocklist", reports: "Reports", settings: "Settings" };
  const pt = document.getElementById("pageTitle");
  if (pt) pt.textContent = titles[page] || "Dashboard";
}

function setupSysPill() {
  const pill = document.getElementById("sysPill");
  const text = document.getElementById("sysText");
  if (!pill) return;
  (async () => {
    try {
      await api.get("/api/stats");
      pill.classList.add("online");
      text.textContent = "online";
    } catch (_) {
      text.textContent = "offline";
    }
  })();
}

document.addEventListener("DOMContentLoaded", () => {
  highlightNav();
  watchClock();

  const hb = document.getElementById("hamburger");
  const sb = document.getElementById("sidebar");
  if (hb && sb) hb.addEventListener("click", () => sb.classList.toggle("open"));

  const btnAll = document.getElementById("btnIngestAll");
  if (btnAll) btnAll.addEventListener("click", () => ingestAllFeeds(btnAll));

  setupSysPill();
  window.toast = toast;
  window.escapeHtml = escapeHtml;
  window.api = api;
  window.fmtDate = fmtDate;
  window.fmtSize = fmtSize;
  window.badgeForType = badgeForType;
  window.badgeForSeverity = badgeForSeverity;
  window.truncate = truncate;
});