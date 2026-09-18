"use strict";

async function loadStats() {
  const stats = await window.api.get("/api/stats");
  const grid = document.getElementById("statGrid");
  const typeStat = Object.entries(stats.by_type)
    .map(([t, c]) => `${t}:${c}`)
    .join(" · ");

  const cards = [
    { label: "IOCs Total", value: stats.total, cls: "acc", sub: typeStat || "no IOCs yet" },
    { label: "Blocklisted", value: stats.blocklisted, cls: "grn", sub: "in current artifacts" },
    { label: "Active Feeds", value: stats.feed_count, cls: "vio", sub: "configured sources" },
    { label: "High Severity", value: stats.severity.high || 0, cls: "red", sub: `med ${stats.severity.medium || 0} · low ${stats.severity.low || 0}` },
  ];

  grid.innerHTML = cards
    .map(
      (c) => `
    <div class="stat">
      <div class="label">${c.label}</div>
      <div class="value ${c.cls}">${Number(c.value).toLocaleString()}</div>
      <div class="pct">${c.sub}</div>
    </div>`
    )
    .join("");
}

async function loadTrend() {
  const rows = await window.api.get("/api/trend");
  const labels = rows.map((r) => r.date.slice(5));
  const data = rows.map((r) => r.count);
  window.lineChart("trendChart", labels, data);
}

async function loadFeedHealth() {
  const rows = await window.api.get("/api/feeds/status");
  const body = document.getElementById("feedHealthBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="3" class="muted">No feeds yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .map(
      (r) => `
    <tr>
      <td class="mono">${window.escapeHtml(r.name)}</td>
      <td><span class="badge ${r.last_status === "success" ? "badge-ok" : "badge-err"}">${window.escapeHtml(r.last_status || "never")}</span></td>
      <td class="muted">${window.fmtDate(r.last_check_at)}</td>
    </tr>`
    )
    .join("");
}

async function loadHistory() {
  const rows = await window.api.get("/api/ingest-history");
  const body = document.getElementById("historyBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="5" class="muted">No ingestion runs yet. Click “Ingest All Feeds”.</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .slice(0, 10)
    .map(
      (r) => `
    <tr>
      <td class="mono">${window.escapeHtml(r.feed_name)}</td>
      <td><span class="badge ${r.status === "success" ? "badge-ok" : "badge-err"}">${window.escapeHtml(r.status)}</span></td>
      <td>${r.new_iocs}</td>
      <td>${r.total_iocs}</td>
      <td class="muted">${window.fmtDate(r.fetched_at)}</td>
    </tr>`
    )
    .join("");
}

async function refresh() {
  await loadStats();
  await loadFeedHealth();
  await loadHistory();
  await loadTrend();
}

document.addEventListener("DOMContentLoaded", refresh);