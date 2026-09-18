"use strict";

async function loadReports() {
  const rows = await window.api.get("/api/reports/list");
  const body = document.getElementById("reportsBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="4" class="muted">No generated files yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .map(
      (r) => `
    <tr>
      <td class="mono">${window.escapeHtml(r.name)}</td>
      <td class="muted">${window.fmtSize(r.size)}</td>
      <td class="muted">${new Date(r.mtime * 1000).toLocaleString()}</td>
      <td style="text-align:right">
        <button class="btn btn-sm dl-report" data-file="${window.escapeHtml(r.name)}">Download</button>
      </td>
    </tr>`
    )
    .join("");
  body.querySelectorAll(".dl-report").forEach((b) =>
    b.addEventListener("click", () => {
      window.location.href = `/api/reports/download/${encodeURIComponent(b.dataset.file)}`;
    })
  );
}

async function generate() {
  const btn = document.getElementById("btnGenReport");
  const payload = {
    format: document.getElementById("rFmt").value,
    type: document.getElementById("rType").value || "",
    severity: document.getElementById("rSev").value || "",
    q: document.getElementById("rSearch").value.trim() || "",
  };
  btn.disabled = true;
  btn.textContent = "⏳ Generating…";
  try {
    const res = await window.api.post("/api/reports/generate", payload);
    document.getElementById("rResult").textContent = `Report generated with ${res.rows} IOCs. Downloading ${res.filename}…`;
    window.location.href = `/api/reports/download/${encodeURIComponent(res.filename)}`;
    loadReports();
  } catch (e) {
    window.toast("Report failed: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadReports();
  document.getElementById("btnGenReport").addEventListener("click", generate);
});