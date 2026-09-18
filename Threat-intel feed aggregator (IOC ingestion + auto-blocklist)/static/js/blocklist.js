"use strict";

async function loadRuns() {
  const rows = await window.api.get("/api/blocklist/runs");
  const body = document.getElementById("runsBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="8" class="muted">No blocklist runs yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .map(
      (r) => `
    <tr>
      <td class="muted">${window.fmtDate(r.generated_at)}</td>
      <td><span class="badge badge-URL">${window.escapeHtml(r.format)}</span></td>
      <td class="mono">${r.ioc_count}</td>
      <td>${r.ip_count}</td>
      <td>${r.domain_count}</td>
      <td>${r.url_count}</td>
      <td>${r.hash_count}</td>
      <td style="text-align:right">
        <button class="btn btn-sm dl-run" data-file="${window.escapeHtml(r.blocklist_path)}">Download</button>
        <button class="btn btn-sm refresh-run" data-id="${r.id}">Regen</button>
      </td>
    </tr>`
    )
    .join("");

  body.querySelectorAll(".dl-run").forEach((b) =>
    b.addEventListener("click", () => {
      const parts = b.dataset.file.split(/[\\/]/);
      const fname = parts[parts.length - 1];
      window.location.href = `/api/blocklist/download/${encodeURIComponent(fname)}`;
    })
  );
  body.querySelectorAll(".refresh-run").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      const res = await window.api.post(`/api/blocklist/${b.dataset.id}/refresh`);
      window.toast(`Blocklist regenerated: ${res.total} entries`, "ok");
      loadRuns();
      loadSummary();
    })
  );
}

async function loadSummary() {
  const rows = await window.api.get("/api/blocklist/runs");
  const el = document.getElementById("blockSummary");
  if (!rows.length) {
    el.className = "muted";
    el.textContent = "No run yet.";
    return;
  }
  const last = rows[0];
  el.innerHTML = `
    <div class="hint" style="margin-top:0">
      <b>${last.ioc_count}</b> IOCs at conf ≥ ${Number(last.threshold_conf).toFixed(2)} · ${window.fmtDate(last.generated_at)}
    </div>
    <div class="hint">
      IP ${last.ip_count} · Domain ${last.domain_count} · URL ${last.url_count} · Hash ${last.hash_count}
    </div>`;
}

async function generate() {
  const btn = document.getElementById("btnGenBlock");
  const conf = parseFloat(document.getElementById("bConf").value || 0.5);
  const fmt = document.getElementById("bFmt").value;
  const types = document.getElementById("bTypes").value;
  btn.disabled = true;
  btn.textContent = "⏳ Generating…";
  try {
    const res = await window.api.post("/api/blocklist/generate", { threshold_conf: conf, format: fmt, types });
    window.toast(`Blocklist ready: ${res.total} entries (${res.format})`, "ok");
    window.location.href = `/api/blocklist/download/${encodeURIComponent(res.filename)}`;
    loadRuns();
    loadSummary();
  } catch (e) {
    window.toast("Generation failed: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Blocklist";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadRuns();
  loadSummary();
  document.getElementById("btnGenBlock").addEventListener("click", generate);
  document.getElementById("btnRefreshRuns").addEventListener("click", loadRuns);
});