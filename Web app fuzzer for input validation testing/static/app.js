/* Web App Fuzzer — frontend logic */
(() => {
  "use strict";

  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));

  const els = {
    run: $("#btn-run"),
    stop: $("#btn-stop"),
    progressFill: $("#progress-fill"),
    progressText: $("#progress-text"),
    progressCount: $("#progress-count"),
    liveDot: $("#live-dot"),
    placeholder: $("#result-placeholder"),
    resultsArea: $("#results-area"),
    resultBody: $("#result-body"),
    summary: $("#summary-cards"),
    sevFilter: $("#sev-filter"),
    filterInput: $("#in-filter"),
    reportBtn: $("#btn-report"),
    threadsVal: $("#threads-val"),
    delayVal: $("#delay-val"),
    suggestBox: $("#suggest-box"),
  };

  const state = {
    token: null,
    results: [],
    config: null,
    running: false,
    pollTimer: null,
    sevFilter: "all",
    textFilter: "",
  };

  /* ---------- slider widgets ---------- */
  const threads = $("#in-threads");
  threads.addEventListener("input", () => (els.threadsVal.textContent = threads.value));
  const delay = $("#in-delay");
  delay.addEventListener("input", () => (els.delayVal.textContent = Number(delay.value).toFixed(2)));

  /* ---------- field suggestions ---------- */
  let suggestTimer = null;
  const inFields = $("#in-fields");
  inFields.addEventListener("input", () => {
    clearTimeout(suggestTimer);
    suggestTimer = setTimeout(updateSuggestions, 320);
  });

  function updateSuggestions() {
    const raw = inFields.value;
    const picked = (raw === "" ? [] : raw.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean));
    els.suggestBox.innerHTML = "";
    if (!picked.length) return;
    const promiseCells = picked.map(f =>
      fetch(`/api/suggest/${encodeURIComponent(f)}`).then(r => r.json()).then(list => ({ f, list }))
        .catch(() => ({ f, list: [] }))
    );
    Promise.all(promiseCells).then(cells => {
      const good = cells.filter(c => c.list.length);
      if (!good.length) return;
      const lines = good.map(c => {
        const names = c.list.map(id => CATEGORY_NAMES[id] || id).join(", ");
        return `<div class="sug"><b>${esc(c.f)}</b> → ${esc(names)}</div>`;
      });
      els.suggestBox.innerHTML = `<div class="sug-wrap">${lines.join("")}</div>`;
    });
  }

  /* ---------- category bulk toggles ---------- */
  const catChecks = $$(".cat-check");
  const catBarHost = $("#cat-grid");
  const catBar = document.createElement("div");
  catBar.className = "cat-bar";
  catBar.innerHTML = `<button type="button" id="cat-all" class="mini-btn">Enable all</button>
    <button type="button" id="cat-none" class="mini-btn">Disable all</button>
    <button type="button" id="cat-classic" class="mini-btn">Core web set</button>
    <span class="cat-bar-note" id="cat-selected"></span>`;
  catBarHost.parentNode.insertBefore(catBar, catBarHost);

  const saved = JSON.parse(localStorage.getItem("wfz_selected") || "null");
  if (saved && Array.isArray(saved)) {
    catChecks.forEach(c => { c.checked = saved.includes(c.value); });
  }
  $("#cat-all").addEventListener("click", () => { catChecks.forEach(c => c.checked = true); saveSelection(); });
  $("#cat-none").addEventListener("click", () => { catChecks.forEach(c => c.checked = false); saveSelection(); });
  $("#cat-classic").addEventListener("click", () => {
    const classic = ["sql", "xss", "cmd", "traversal", "template", "ssrf", "redir"];
    catChecks.forEach(c => { c.checked = classic.includes(c.value); });
    saveSelection();
  });
  catChecks.forEach(c => c.addEventListener("change", saveSelection));
  saveSelection();

  function saveSelection() {
    const sel = catChecks.filter(c => c.checked).map(c => c.value);
    localStorage.setItem("wfz_selected", JSON.stringify(sel));
    const note = $("#cat-selected");
    if (note) note.textContent = `${sel.length} of ${catChecks.length} categories selected`;
    updateTotals();
  }

  function updateTotals() {
    // per-category payload counts are server rendered; nothing to change here
  }

  const CATEGORY_NAMES = {};
  catChecks.forEach(c => {
    const card = c.closest(".cat-card");
    if (card) CATEGORY_NAMES[c.value] = $(".cat-name", card).textContent.trim();
  });

  /* ---------- run / stop ---------- */
  els.run.addEventListener("click", runScan);
  els.stop.addEventListener("click", cancelScan);

  function readConfig() {
    const fields = inFields.value;
    const selected = catChecks.filter(c => c.checked).map(c => c.value);
    const url = $("#in-url").value.trim();
    return {
      url,
      method: $("#in-method").value,
      cookies: $("#in-cookies").value,
      threads: +threads.value,
      delay: +delay.value,
      timeout: +$("#in-timeout").value,
      user_agent: $("#in-user-agent").value,
      fields,
      categories: selected,
      shuffle: $("#in-shuffle").checked,
      use_baseline: $("#in-baseline").checked,
      verify_ssl: $("#in-ssl").checked,
      params: $("#in-params").value,
      data: $("#in-data").value,
      headers: $("#in-headers").value,
      inject_params: $("#in-inject-params").checked,
      inject_data: $("#in-inject-data").checked,
      inject_headers: $("#in-inject-headers").checked,
    };
  }

  function runScan() {
    const cfg = readConfig();
    if (!cfg.url) { toast("Please enter a target URL.", "error"); $("#in-url").focus(); return; }
    if (!cfg.fields) { toast("Please enter at least one field to fuzz.", "error"); $("#in-fields").focus(); return; }
    if (!cfg.categories.length) { toast("Select at least one payload category.", "error"); return; }

    setRunning(true);
    els.progressFill.style.width = "0%";
    els.progressText.textContent = "Starting scan…";
    els.liveDot.classList.add("live");
    $(".log-box") && $(".log-box").remove();
    appendLog(`Target: ${cfg.url}  [${cfg.method.toUpperCase()}]`);
    appendLog(`Fields: ${cfg.fields}`);
    appendLog(`Categories: ${cfg.categories.length} selected, ${countTotalPayloads(cfg.categories)} payloads queued per field.`);

    fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "Failed to start scan.");
        state.token = d.token;
        state.config = cfg;
        startPolling();
      })
      .catch(err => {
        setRunning(false);
        toast(err.message, "error");
      });
  }

  function countTotalPayloads(cats) {
    let n = 0;
    catChecks.forEach(c => { if (cats.includes(c.value)) { n += CATEGORY_COUNTS[c.value] || 0; } });
    return n;
  }

  const CATEGORY_COUNTS = {};
  catChecks.forEach(c => {
    const card = c.closest(".cat-card");
    const el = card && $(".cat-count", card);
    if (el) {
      const m = el.textContent.match(/(\d+)/);
      CATEGORY_COUNTS[c.value] = m ? +m[1] : 0;
    }
  });

  function cancelScan() {
    if (!state.token) return;
    appendLog("Cancelling…");
    fetch(`/api/scan/${state.token}/cancel`, { method: "POST" }).catch(() => {});
  }

  function startPolling() {
    stopPolling();
    state.pollTimer = setInterval(poll, 750);
    poll();
  }
  function stopPolling() { if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; } }

  let lastLogLen = 0;
  let lastResultsLen = 0;
  function poll() {
    if (!state.token) return;
    fetch(`/api/scan/${state.token}`)
      .then(r => r.json())
      .then(updateFromServer)
      .catch(() => {});
  }

  function updateFromServer(data) {
    const p = data.progress || { done: 0, total: 0 };
    const total = p.total || 0;
    const done = p.done || 0;
    const pct = total ? Math.min(100, Math.round(done / total * 100)) : 0;
    els.progressFill.style.width = pct + "%";
    els.progressCount.textContent = `${done} / ${total}`;

    if (data.log && data.log.length !== lastLogLen) {
      lastLogLen = data.log.length;
      const lines = data.log.slice(lastLogLen ? 0 : 0);
      renderLog(data.log);
    }

    if (total && !pct) {
      els.progressText.textContent = data.done ? "Scan complete" : "Running scan…";
    } else if (data.done) {
      els.progressText.textContent = "Scan complete";
    } else {
      els.progressText.textContent = "Running scan…";
    }

    if (data.results && data.results.length !== lastResultsLen) {
      lastResultsLen = (data.results || []).length;
      state.results = data.results;
      renderResults(data.results);
    }

    if (data.done) {
      stopPolling();
      setRunning(false);
      els.liveDot.classList.remove("live");
      els.progressText.textContent = "Scan complete";
      if (state.results.length) toast(`Scan complete: ${state.results.length} findings.`, "ok");
    }
  }

  function renderLog(lines) {
    let box = $(".log-box");
    if (!box) {
      box = document.createElement("div");
      box.className = "log-box";
      const zone = $("#results");
      zone.appendChild(box);
    }
    box.innerHTML = lines.map(l => `<b>&gt;</b> ${esc(l)}`).join("\n");
    box.scrollTop = box.scrollHeight;
  }

  function appendLog(line) {
    let box = $(".log-box");
    if (!box) {
      box = document.createElement("div");
      box.className = "log-box";
      $("#results").appendChild(box);
    }
    box.insertAdjacentHTML("beforeend", `<b>&gt;</b> ${esc(line)}\n`);
    box.scrollTop = box.scrollHeight;
  }

  /* ---------- results rendering ---------- */
  function renderResults(results) {
    els.placeholder.style.display = "none";
    els.resultsArea.style.display = "block";
    renderSummary(results);
    renderTable(results);
  }

  function renderSummary(results) {
    const counts = { high: 0, medium: 0, low: 0, info: 0, ok: 0 };
    results.forEach(r => { counts[r.severity] = (counts[r.severity] || 0) + 1; });
    const total = results.length;
    const order = [["high", "High risk"], ["medium", "Medium"], ["low", "Low"], ["info", "Info"], ["ok", "OK"]];
    els.summary.innerHTML = order.map(([k, label]) =>
      `<div class="sum-card s-${k}"><span class="n">${counts[k] || 0}</span><span class="t">${label}</span></div>`
    ).join("") + `<div class="sum-card"><span class="n">${total}</span><span class="t">Total</span></div>`;
  }

  function severityValue(sev) { return { high: 0, medium: 1, low: 2, info: 3, ok: 4 }[sev] ?? 9; }
  const SEV_CLASS = { high: "high", medium: "medium", low: "low", info: "info", ok: "ok" };

  function filteredResults() {
    return state.results
      .filter(r => state.sevFilter === "all" || r.severity === state.sevFilter)
      .filter(r => {
        if (!state.textFilter) return true;
        const t = state.textFilter.toLowerCase();
        return [
          r.field, r.category_name, r.payload, r.title, (r.matched || []).join(" "),
        ].some(v => String(v || "").toLowerCase().includes(t));
      })
      .sort((a, b) => severityValue(a.severity) - severityValue(b.severity) ||
        b.risk - a.risk || String(a.field).localeCompare(String(b.field)));
  }

  function renderTable(results) {
    els.resultBody.innerHTML = "";
    results.forEach(r => renderRow(r));
  }

  function renderRow(r) {
    const tr = document.createElement("tr");
    const sev = SEV_CLASS[r.severity] || "info";
    tr.className = `sev-${sev}`;
    tr.innerHTML = `
      <td><span class="field">${esc(r.field)}</span></td>
      <td><span class="cat">${esc(r.category_name || r.category || "")}</span></td>
      <td><span class="payload" title="${esc(r.payload)}">${esc(r.payload)}</span></td>
      <td>${r.status || "err"}</td>
      <td>${Math.round(r.elapsed_ms || 0)} ms</td>
      <td><div class="tags">${(r.matched || []).slice(0, 3).map(m => `<span>${esc(m)}</span>`).join("") || "—"}</div></td>
      <td><span class="sev-pill ${sev}">${sev.toUpperCase()}</span></td>
      <td>${r.reflected ? "<b>reflected</b>" : ""}</td>`;
    tr.addEventListener("click", () => toggleDetail(tr, r));
    els.resultBody.appendChild(tr);
  }

  function toggleDetail(tr, r) {
    const existing = tr.nextElementSibling;
    if (existing && existing.classList.contains("row-detail")) {
      existing.remove();
      return;
    }
    if (existing) return;
    const tpl = $("#row-detail-tpl");
    const node = tpl.content.cloneNode(true);
    $("#rd-payload", node).textContent = r.payload;
    $("#rd-field", node).textContent = `${r.field}  ·  HTTP ${r.status || "timeout/err"}  ·  ${Math.round(r.elapsed_ms || 0)} ms`;
    const analysis = $("#rd-analysis", node);
    analysis.innerHTML = "";
    const details = (r.details || []).length ? r.details : ["No additional detail."];
    details.forEach(d => { const li = document.createElement("li"); li.textContent = d; analysis.appendChild(li); });
    const tags = $("#rd-tags", node);
    tags.innerHTML = (r.matched || []).map(m => `<span>${esc(m)}</span>`).join(" ") || "<span>none</span>";
    const wrap = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 8;
    td.appendChild(node);
    wrap.appendChild(td);
    wrap.className = "row-detail";
    tr.after(wrap);
  }

  /* ---------- filters ---------- */
  els.sevFilter.addEventListener("click", (e) => {
    const chip = e.target.closest(".f-chip");
    if (!chip) return;
    $$(".f-chip", els.sevFilter).forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    state.sevFilter = chip.dataset.sev;
    renderTable(filteredResults());
  });
  els.filterInput.addEventListener("input", () => {
    state.textFilter = els.filterInput.value;
    renderTable(filteredResults());
  });

  /* ---------- report ---------- */
  els.reportBtn.addEventListener("click", downloadReport);

  function downloadReport() {
    if (!state.results.length) {
      toast("No results to report yet. Run a scan first.", "error");
      return;
    }
    els.reportBtn.disabled = true;
    els.reportBtn.textContent = "Generating…";
    const visible = filteredResults();
    const payload = {
      results: visible,
      config: {
        url: (state.config && state.config.url) || "",
        method: (state.config && state.config.method) || "GET",
        fields: (state.config && state.config.fields) || "",
        categories: ((state.config && state.config.categories) || []).join(", "),
        threads: (state.config && state.config.threads) || "-",
        timeout: (state.config && state.config.timeout) || "-",
        "verify_ssl": state.config ? state.config.verify_ssl : false,
      },
      generated_at: new Date().toLocaleString(),
    };
    fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(r => {
        if (!r.ok) throw new Error("Report generation failed.");
        return r.blob();
      })
      .then(blob => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `fuzzer-report-${stamp()}.html`;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
        toast("Report downloaded.", "ok");
      })
      .catch(err => toast(err.message, "error"))
      .finally(() => {
        els.reportBtn.disabled = false;
        els.reportBtn.textContent = "Download HTML report";
        els.reportBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg> Download HTML report`;
      });
  }

  /* ---------- misc ---------- */
  function setRunning(running) {
    state.running = running;
    els.run.disabled = running;
    els.stop.disabled = !running;
    if (running) {
      els.run.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg> Scanning…`;
    } else {
      els.run.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg> Start fuzzing`;
    }
  }

  let toastTimer = null;
  function toast(msg, type = "ok") {
    let box = $("#toast");
    if (!box) {
      box = document.createElement("div");
      box.id = "toast";
      document.body.appendChild(box);
    }
    box.className = `toast show ${type}`;
    box.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => box.classList.remove("show"), 3200);
  }

  function stamp() {
    const d = new Date();
    const p = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* ---------- keyboard shortcut: Ctrl+Enter = run ---------- */
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !state.running) runScan();
  });
})();