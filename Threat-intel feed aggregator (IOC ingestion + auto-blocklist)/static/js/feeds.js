"use strict";

let editingId = null;

async function loadFeeds() {
  const rows = await window.api.get("/api/feeds");
  const body = document.getElementById("feedBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="8" class="muted">No feeds configured — add one above.</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .map((f) => {
      const statusBadge =
        f.last_status === "success"
          ? `<span class="badge badge-ok">ok</span>`
          : f.last_status
          ? `<span class="badge badge-err">${window.escapeHtml(f.last_status.slice(0, 24))}</span>`
          : `<span class="badge badge-off">never</span>`;
      return `
    <tr>
      <td><b>${window.escapeHtml(f.name)}</b><div class="muted mono">${window.escapeHtml(f.url)}</div></td>
      <td><span class="badge badge-URL">${window.escapeHtml(f.format)}</span></td>
      <td>
        ${(f.ioc_types || "")
          .split(",")
          .filter(Boolean)
          .map((t) => window.badgeForType(t.trim()))
          .join(" ")}
      </td>
      <td class="mono">${Number(f.reputation).toFixed(2)}</td>
      <td>${statusBadge}</td>
      <td class="muted">${window.fmtDate(f.last_check_at)}</td>
      <td>
        <span class="badge ${f.auto_ingest ? "badge-ok" : "badge-off"}">${f.auto_ingest ? "auto" : "manual"}</span>
        <span class="badge ${f.enabled ? "badge-ok" : "badge-off"}">${f.enabled ? "on" : "off"}</span>
      </td>
      <td style="text-align:right; white-space:nowrap">
        <button class="btn btn-sm btn-ingest" data-id="${f.id}">Ingest</button>
        <button class="btn btn-sm edit-feed" data-id="${f.id}">Edit</button>
        <button class="btn btn-sm btn-danger del-feed" data-id="${f.id}">Del</button>
      </td>
    </tr>`;
    })
    .join("");

  body.querySelectorAll(".btn-ingest").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      b.textContent = "…";
      try {
        const data = await window.api.post(`/api/feeds/${b.dataset.id}/ingest`);
        const r = data.results[0];
        window.toast(
          r && r.status === "success" ? `${r.feed}: ${r.new} new / ${r.total} total` : `Feed error: ${r?.error || "?"}`,
          r && r.status === "success" ? "ok" : "err"
        );
      } catch (e) {
        window.toast("Ingest failed: " + e.message, "err");
      }
      loadFeeds();
    })
  );

  body.querySelectorAll(".edit-feed").forEach((b) =>
    b.addEventListener("click", () => {
      const f = rows.find((r) => r.id == b.dataset.id);
      openForm(f);
    })
  );

  body.querySelectorAll(".del-feed").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!confirm("Delete this feed?")) return;
      await window.api.del(`/api/feeds/${b.dataset.id}`);
      window.toast("Feed deleted", "ok");
      loadFeeds();
    })
  );
}

function openForm(f) {
  editingId = f ? f.id : null;
  document.getElementById("feedForm").classList.remove("hidden");
  document.getElementById("feedFormTitle").textContent = f ? "Edit Feed" : "Add New Feed";
  document.getElementById("fName").value = f ? f.name : "";
  document.getElementById("fUrl").value = f ? f.url : "";
  document.getElementById("fFormat").value = f ? f.format : "TXT";
  document.getElementById("fTypes").value = f ? f.ioc_types : "IP,DOMAIN,URL,HASH";
  document.getElementById("fRep").value = f ? f.reputation : 0.8;
}

function closeForm() {
  editingId = null;
  document.getElementById("feedForm").classList.add("hidden");
}

async function saveFeed() {
  const name = document.getElementById("fName").value.trim();
  const url = document.getElementById("fUrl").value.trim();
  const format = document.getElementById("fFormat").value;
  const ioc_types = document.getElementById("fTypes").value;
  const reputation = parseFloat(document.getElementById("fRep").value || 0.8);
  if (!name || !url) {
    window.toast("Name and URL are required", "err");
    return;
  }
  const payload = { name, url, format, ioc_types, reputation };
  try {
    if (editingId) {
      await window.api.put(`/api/feeds/${editingId}`, payload);
      window.toast("Feed updated", "ok");
    } else {
      await window.api.post("/api/feeds", payload);
      window.toast("Feed added", "ok");
    }
    closeForm();
    loadFeeds();
  } catch (e) {
    window.toast("Save failed: " + e.message, "err");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadFeeds();
  document.getElementById("btnNewFeed").addEventListener("click", () => {
    editingId = null;
    openForm({ name: "", url: "", format: "TXT", ioc_types: "IP", reputation: 0.8 });
  });
  document.getElementById("fSave").addEventListener("click", saveFeed);
  document.getElementById("fCancel").addEventListener("click", closeForm);
});