/* app.js - front-end logic for the XSS Payload Tester UI */

(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const els = {
    url: $("url"),
    param: $("param"),
    method: $("method"),
    location: $("location"),
    custom: $("custom"),
    headers: $("headers"),
    timeout: $("timeout"),
    concurrency: $("concurrency"),
    follow: $("follow"),
    run: $("run"),
    stop: $("stop"),
    status: $("status"),
    download: $("download"),
    kpi: $("kpi"),
    baseline: $("baseline"),
    summary: $("summary"),
    tableWrap: $("table-wrap"),
    rows: document.querySelector("#results-table tbody"),
    empty: $("empty"),
  };

  let currentRun = null;
  let abortCtrl = null;

  /* ---------- payload helper (payloads come from the built-in library) ---------- */
  function selectedPayloadIds() {
    // Grab the ids flagged in the checkbox rack; the server filters by ids.
    const boxes = document.querySelectorAll('input[type="checkbox"][data-pid]');
    return Array.from(boxes)
      .filter((b) => b.checked)
      .map((b) => b.dataset.pid);
  }

  function collectPayloadIds() {
    // Nothing to collect if we haven't loaded the catalog; server uses its own
    // full library plus custom payloads by default (payload_ids omitted = all).
    return null;
  }

  function parseTimeout() {
    const t = parseInt(els.timeout.value, 10);
    return isNaN(t) ? 10 : Math.min(60, Math.max(1, t));
  }

  function readConfig() {
    return {
      url: els.url.value.trim(),
      param: els.param.value.trim(),
      method: els.method.value,
      location: els.location.value,
      custom_payloads: els.custom.value.split("\n").map((s) => s.trim()).filter(Boolean),
      payload_ids: collectPayloadIds(),
      headers: els.headers.value.split("\n").map((s) => s.trim()).filter(Boolean),
      timeout: parseTimeout(),
      concurrency: parseInt(els.concurrency.value, 10) || 4,
      follow_redirects: els.follow.checked,
    };
  }

  /* ---------- rendering ---------- */
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function verdictClass(v) {
    if (!v) return "neutral";
    if (v.startsWith("Executable XSS")) return "bad";
    if (v.includes("event-sink")) return "bad";
    if (v.startsWith("Reflected")) return "warn";
    if (v.startsWith("Partial")) return "warn";
    if (v.startsWith("Not reflected")) return "good";
    return "neutral";
  }

  function highlight(s) {
    let out = escapeHtml(s);
    ["alert(1)", "onerror", "onload", "srcdoc", "document.write", "<script", "javascript:", "alert(document.domain)"].forEach((t) => {
      const safe = escapeHtml(t);
      out = out.split(safe).join('<mark>' + safe + '</mark>');
    });
    return out;
  }

  function renderBaseline(run) {
    const b = run.baseline || {};
    const ok = b.reachable;
    els.baseline.classList.remove("hidden");
    els.baseline.innerHTML =
      "Baseline: <b class='" + (ok ? "" : "err-txt") + "'>" +
      (ok ? "target reachable" : "TARGET UNREACHABLE - check the URL, host, or lab app") +
      "</b> &nbsp;|&nbsp; HTTP <code>" + (b.status ?? "?") + "</code>" +
      " &middot; " + escapeHtml((b.content_type || "-").split(";")[0]) +
      " &middot; " + (b.size || 0) + " bytes" +
      (b.final_url && b.final_url !== run.config.url ? " &middot; redirected to <code>" + escapeHtml(b.final_url) + "</code>" : "");
  }

  function renderKpi(run) {
    const s = run.summary || {};
    const cards = [
      { label: "Payloads", num: s.total || 0, cls: "info" },
      { label: "Executable XSS", num: s.executable || 0, cls: "bad" },
      { label: "Event-sink", num: s.event_sink || 0, cls: "warn" },
      { label: "Reflected", num: s.reflected || 0, cls: "warn" },
      { label: "Partial", num: s.partial || 0, cls: "info" },
      { label: "Filtered", num: s.filtered || 0, cls: "good" },
      { label: "Errors", num: s.errors || 0, cls: "neutral" },
    ];
    els.kpi.innerHTML = cards
      .map((c) => '<div class="card"><b>' + c.label + '</b><div class="num ' + c.cls + '">' + c.num + "</div></div>")
      .join("");
  }

  function renderSummary(run) {
    const s = run.summary || {};
    els.summary.classList.remove("hidden");
    let msg = "Scan complete: ";
    msg += s.executable ? "<b>" + s.executable + " executable XSS</b> candidate(s) landed. " : "";
    msg += s.event_sink ? s.event_sink + " reflected into event-sinks. " : "";
    msg += s.reflected ? s.reflected + " reflected cleanly. " : "";
    if (!s.executable && !s.event_sink && !s.reflected && s.partial) msg += s.partial + " partial reflections. ";
    if (s.filtered && !s.executable && !s.event_sink && !s.reflected) msg += "All payloads were filtered / not echoed back. ";
    els.summary.innerHTML = msg;
  }

  function renderRows(run) {
    const results = run.results || [];
    els.rows.innerHTML = results
      .map((r) => {
        const cls = verdictClass(r.verdict);
        const markers = (r.marker_hits || []).map(escapeHtml).join(", ") || "&mdash;";
        let evidence = "";
        const ev = r.evidence || {};
        if (r.error) {
          evidence = '<span class="err-txt">' + escapeHtml(r.error) + "</span>";
        } else {
          const an = r.analysis || {};
          const bits = [];
          if (an.script_context) bits.push("inside <b>&lt;script&gt;</b>");
          if (an.tag_context) bits.push("inside a tag");
          if (an.prev_sink) bits.push('after sink <code>' + an.prev_sink + '=</code>');
          evidence = bits.join(", ") || "&mdash;";
          if (r.reflected_snippet) {
            evidence += '<span class="snippet">' + highlight(r.reflected_snippet) + "</span>";
          }
        }
        return (
          "<tr>" +
          '<td data-label="ID"><span class="id-col">' + escapeHtml(r.id) + "</span></td>" +
          '<td data-label="Payload"><code>' + escapeHtml(r.payload) + "</code></td>" +
          '<td data-label="Verdict"><span class="pill ' + cls + '">' + escapeHtml(r.verdict || "Error") + "</span></td>" +
          '<td data-label="Confidence">' + escapeHtml(r.confidence || "&mdash;") + "</td>" +
          '<td data-label="Markers">' + markers + "</td>" +
          '<td data-label="Evidence">' + evidence + "</td>" +
          "</tr>"
        );
      })
      .join("");
    els.tableWrap.classList.remove("hidden");
  }

  function showEmpty() {
    els.empty.classList.remove("hidden");
    els.kpi.innerHTML = "";
    els.baseline.classList.add("hidden");
    els.summary.classList.add("hidden");
    els.tableWrap.classList.add("hidden");
    els.rows.innerHTML = "";
  }

  /* ---------- actions ---------- */
  async function runScan() {
    const config = readConfig();
    if (!config.url) {
      setStatus("Enter a target URL first.", "err");
      els.url.focus();
      return;
    }
    if (!/^https?:\/\//i.test(config.url)) {
      config.url = "http://" + config.url;
    }

    abortCtrl = new AbortController();
    els.run.disabled = true;
    els.download.disabled = true;
    els.stop.classList.remove("hidden");
    currentRun = null;
    showEmpty();
    setStatus("Sending payloads to <b>" + escapeHtml(config.url) + "</b> ...", "");

    try {
      const res = await fetch("/api/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
        signal: abortCtrl.signal,
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus("Error: " + (data.error || res.status), "err");
        return;
      }
      currentRun = data;
      els.download.disabled = false;
      renderBaseline(data);
      renderKpi(data);
      renderSummary(data);
      renderRows(data);
      setStatus("Done in " + (currentRun.summary.total || 0) + " requests.", "ok");
    } catch (err) {
      if (err.name === "AbortError") {
        setStatus("Scan stopped by user.", "");
      } else {
        setStatus("Request failed: " + escapeHtml(String(err)), "err");
      }
    } finally {
      els.run.disabled = false;
      els.stop.classList.add("hidden");
      abortCtrl = null;
    }
  }

  function stopScan() {
    if (abortCtrl) abortCtrl.abort();
  }

  async function downloadReport() {
    if (!currentRun) return;
    setStatus("Generating HTML report...", "");
    try {
      const res = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run: currentRun }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setStatus("Report error: " + (j.error || res.status), "err");
        return;
      }
      const blob = await res.blob();
      const dl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = dl;
      const cd = res.headers.get("Content-Disposition") || "";
      const m = cd.match(/filename="?([^";]+)"?/i);
      a.download = m ? m[1] : "xss-report.html";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(dl);
      setStatus("Report downloaded as <b>" + escapeHtml(a.download) + "</b>.", "ok");
    } catch (err) {
      setStatus("Download failed: " + escapeHtml(String(err)), "err");
    }
  }

  function setStatus(text, cls) {
    els.status.innerHTML = text;
    els.status.className = "status" + (cls ? " " + cls : "");
  }

  /* ---------- wire up ---------- */
  els.run.addEventListener("click", runScan);
  els.stop.addEventListener("click", stopScan);
  els.download.addEventListener("click", downloadReport);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA")) {
      if (e.target.id === "url" || e.target.id === "param") {
        e.preventDefault();
        runScan();
      }
    }
  });
})();