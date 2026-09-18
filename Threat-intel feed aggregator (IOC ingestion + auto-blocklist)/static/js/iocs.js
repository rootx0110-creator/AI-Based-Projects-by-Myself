"use strict";

const PAGE_SIZE = 50;
let allRows = [];
let page = 0;

function filters() {
  const q = new URLSearchParams();
  const type = document.getElementById("fType").value;
  const sev = document.getElementById("fSeverity").value;
  const block = document.getElementById("fBlock").value;
  const search = document.getElementById("qSearch").value.trim();
  if (type) q.set("type", type);
  if (sev) q.set("severity", sev);
  if (block !== "") q.set("blocklisted", block);
  if (search) q.set("q", search);
  return q.toString();
}

async function loadIocs() {
  const rows = await window.api.get("/api/iocs?" + filters());
  allRows = rows;
  page = 0;
  render();
}

function render() {
  const body = document.getElementById("iocBody");
  const start = page * PAGE_SIZE;
  const slice = allRows.slice(start, start + PAGE_SIZE);
  if (!slice.length) {
    body.innerHTML = `<tr><td colspan="8" class="muted">No indicators match${allRows.length ? " this page" : " — ingest some feeds first"}.</td></tr>`;
  } else {
    body.innerHTML = slice
      .map(
        (r) => `
      <tr>
        <td>${window.badgeForType(r.type)}</td>
        <td class="mono" title="${window.escapeHtml(r.value)}">${window.escapeHtml(window.truncate(r.value, 60))}</td>
        <td class="muted">${window.escapeHtml(r.source_feed || "—")}</td>
        <td class="mono">${Number(r.confidence).toFixed(2)}</td>
        <td>${window.badgeForSeverity(r.severity)}</td>
        <td class="muted">${window.fmtDate(r.last_seen)}</td>
        <td>
          ${r.blocklisted
            ? `<span class="badge badge-ok">blocked</span>`
            : `<span class="badge badge-off">open</span>`}
        </td>
        <td style="text-align:right">
          <button class="btn btn-sm toggle-block" data-id="${r.id}" data-state="${r.blocklisted ? 1 : 0}">${r.blocklisted ? "Unblock" : "Block"}</button>
        </td>
      </tr>`
      )
      .join("");
    body.querySelectorAll(".toggle-block").forEach((b) =>
      b.addEventListener("click", async () => {
        const id = b.dataset.id;
        const next = b.dataset.state === "1" ? 0 : 1;
        await window.api.patch(`/api/iocs/${id}`, { blocklisted: next });
        window.toast(next ? "IOC blocked" : "IOC unblocked", "ok");
        loadIocs();
      })
    );
  }

  const pages = Math.max(1, Math.ceil(allRows.length / PAGE_SIZE));
  const paging = document.getElementById("paging");
  paging.innerHTML = `
    <button class="btn btn-sm" id="pgPrev" ${page <= 0 ? "disabled" : ""}>‹</button>
    <span>page ${page + 1} / ${pages} · ${allRows.length} results</span>
    <button class="btn btn-sm" id="pgNext" ${page >= pages - 1 ? "disabled" : ""}>›</button>`;
  document.getElementById("pgPrev").addEventListener("click", () => { page--; render(); });
  document.getElementById("pgNext").addEventListener("click", () => { page++; render(); });
}

async function downloadCsv() {
  const qs = filters();
  const res = await window.api.post("/api/reports/generate", { format: "csv", ...Object.fromEntries(new URLSearchParams(qs)) });
  window.location.href = `/api/reports/download/${encodeURIComponent(res.filename)}`;
}

document.addEventListener("DOMContentLoaded", () => {
  loadIocs();
  ["qSearch", "fType", "fSeverity", "fBlock"].forEach((id) => {
    const el = document.getElementById(id);
    el.addEventListener("change", loadIocs);
    el.addEventListener("input", () => { clearTimeout(el._t); el._t = setTimeout(loadIocs, 300); });
  });
  document.getElementById("btnClearFilters").addEventListener("click", () => {
    document.getElementById("qSearch").value = "";
    document.getElementById("fType").value = "";
    document.getElementById("fSeverity").value = "";
    document.getElementById("fBlock").value = "";
    loadIocs();
  });
  document.getElementById("btnDownload").addEventListener("click", downloadCsv);
});