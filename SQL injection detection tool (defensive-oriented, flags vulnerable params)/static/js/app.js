/* SQLInspect frontend controller */
"use strict";

const $ = (sel, el) => (el || document).querySelector(sel);

window.addEventListener("error", (e) => {
  try {
    const tb = $("#transcript");
    if (tb) {
      const div = document.createElement("div");
      div.className = "t-line t-err";
      div.textContent = "[js-error] " + (e.message || "unknown error");
      tb.appendChild(div);
      tb.scrollTop = tb.scrollHeight;
    }
  } catch (_) {}
});

const state = {
  mode: "url",
  result: null,
  rid: null,
};

const EXAMPLES = {
  url: "http://shop.local/products.php?category=Books&id=1%20UNION%20ALL%20SELECT%20NULL,user(),3--%20&sort=price",
  raw: [
    "POST /search.php HTTP/1.1",
    "Host: shop.local",
    "Content-Type: application/x-www-form-urlencoded",
    "Cookie: session=4f6a2b",
    "",
    "q=books' OR '1'='1&limit=50",
  ].join("\n"),
  list: [
    "# demo log - one URL per line",
    "http://shop.local/products.php?id=5 and 1=1",
    "http://portal.local/account?id=9' AND SLEEP(3)-- -",
    "http://api.local/v1/users?q=admin' UNION SELECT * FROM users--",
    "http://shop.local/static/about.php (no params)",
  ].join("\n"),
};

/* ------------------------------------------------------------------ tabs */
function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  document.querySelectorAll(".tab-pane").forEach((p) => {
    p.classList.toggle("active", p.dataset.pane === mode);
  });
}

function loadExample(e) {
  e.preventDefault();
  const map = { url: "#urlInput", raw: "#rawInput", list: "#listInput" };
  $(map[state.mode]).value = EXAMPLES[state.mode];
  toast("Example loaded into " + state.mode.toUpperCase() + " mode");
}

/* ------------------------------------------------------------------ files */
function initDropzone() {
  const dz = $("#dropzone");
  const input = $("#fileInput");
  dz.addEventListener("click", () => input.click());
  dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("over"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("over"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("over");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => { if (input.files.length) handleFile(input.files[0]); });
}

function handleFile(file) {
  if (file.size > 2 * 1024 * 1024) return toast("File too large (max 2 MB)", true);
  const reader = new FileReader();
  reader.onload = () => {
    $("#listInput").value = reader.result;
    setMode("list");
    toast("Loaded " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)");
  };
  reader.readAsText(file);
}

/* ------------------------------------------------------------------ scan */
function currentInput() {
  const map = { url: "#urlInput", raw: "#rawInput", list: "#listInput" };
  return $(map[state.mode]).value.trim();
}

function logLine(text, cls) {
  const tbody = $("#transcript");
  const div = document.createElement("div");
  div.className = "t-line " + (cls || "");
  div.innerHTML = text;
  tbody.appendChild(div);
  if (tbody.children.length > 400) {
    const kids = [...tbody.children];
    kids.slice(0, 150).forEach((n) => n.remove());
  }
  tbody.scrollTop = tbody.scrollHeight;
}

async function runScan() {
  const data = currentInput();
  if (!data) return toast("Please provide a target URL, request, or file content.", true);
  const consent = $("#consent").checked;
  const liveOn = $("#liveToggle").checked;

  const btn = $("#scanBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> SCANNING';
  $("#results").classList.remove("show");
  $("#transcript").innerHTML = "";
  logLine('<span class="t-lab">[init]</span> SQLInspect engine ready');
  logLine('<span class="t-lab">[mode]</span> ' + state.mode.toUpperCase() + " analysis " +
    (liveOn ? "+ LIVE PROBING (consent given)" : "(offline)"));
  logLine('<span class="t-lab">[target]</span> ' + data.slice(0, 240) + (data.length > 240 ? "…" : ""));
  $("#transcript").scrollIntoView({ behavior: "smooth", block: "center" });

  const body = {
    mode: state.mode,
    data,
    live: {
      enabled: liveOn,
      consent,
      timeout: parseFloat($("#timeout").value) || 8,
      delay_ms: parseInt($("#delay").value, 10) || 0,
    },
  };

  const t0 = performance.now();
  try {
    const resp = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const js = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(js.error || ("HTTP " + resp.status));

    const dt = Math.round(performance.now() - t0);
    logLine('<span class="t-lab">[ok]</span> analysis complete in ' + dt + " ms");
    const s = js.summary;
    logLine('<span class="t-lab">[summary]</span> ' + s.targets + " target(s), " +
      s.total_params + " parameter(s) assessed", "t-dim");
    if (s.live) logLine('<span class="t-lab">[live]</span> behaviour probes executed', "t-warn");
    if (s.critical) logLine('<span class="t-lab">[alert]</span> ' + s.critical +
      " CRITICAL target(s)", "t-crit");
    else if (s.high) logLine('<span class="t-lab">[alert]</span> ' + s.high +
      " HIGH risk target(s)", "t-warn");
    else logLine('<span class="t-lab">[ok]</span> no high/critical risk detected', "t-ok");

    state.result = js;
    state.rid = js.id;
    renderResults(js);
    refreshHistory();
  } catch (err) {
    logLine('<span class="t-lab">[error]</span> ' + err.message, "t-err");
    toast("Scan failed: " + err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></svg> RUN SECURITY SCAN';
  }
}

/* -------------------------------------------------------------- render */
const RISK_COLORS = {
  Critical: "var(--crit)", High: "var(--high)", Medium: "var(--medium)",
  Low: "var(--low)", Safe: "var(--safe)",
};

const TECH_COUNT_LABEL = {
  signature: "Payload signature", pattern: "Syntax pattern", error_signature: "DBMS error",
  keyword_density: "Keyword density", meta_character: "Meta chars", boolean_blind: "Boolean-blind",
  time_based: "Time-based", stacked_queries: "Stacked queries", dbms_fingerprint: "DBMS fingerprint",
  encoding_obfuscation: "Obfuscation",
};

function renderResults(js) {
  const s = js.summary;
  $("#results").classList.add("show");
  $("#overall").scrollIntoView({ behavior: "smooth", block: "start" });

  const col = RISK_COLORS[s.overall_risk] || "var(--cyan)";
  const circ = 2 * Math.PI * 75;
  const arc = $("#gaugeArc");
  arc.style.stroke = col;
  arc.style.strokeDasharray = circ;
  arc.style.strokeDashoffset = circ;
  requestAnimationFrame(() => {
    arc.style.transition = "stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)";
    arc.style.strokeDashoffset = circ * (1 - s.overall_score / 100);
  });
  $("#gaugeVal").innerHTML = '<b style="color:' + col + '">' + s.overall_score +
    '</b><span>' + s.overall_risk + "</span>";

  $("#statTargets").textContent = s.targets;
  $("#statParams").textContent = s.total_params;
  const sv = $("#statVuln");
  sv.textContent = s.vulnerable;
  sv.style.color = s.vulnerable ? "var(--red)" : "var(--safe)";
  const sc = $("#statCrit");
  sc.textContent = s.critical;
  sc.style.color = s.critical ? "var(--crit)" : "var(--muted)";
  const sh = $("#statHigh");
  sh.textContent = s.high;
  sh.style.color = s.high ? "var(--high)" : "var(--muted)";
  $("#statsMeta").textContent = "mode " + s.mode.toUpperCase() + " · scanned " +
    s.scanned_at + " · live " + (s.live ? "ON" : "OFF");

  const counts = {};
  for (const t of js.targets) {
    for (const f of t.findings) {
      for (const tech of f.techniques) {
        if (tech.key === "unreachable") continue;
        counts[tech.key] = (counts[tech.key] || 0) + 1;
      }
    }
  }
  renderBars(counts);

  const fw = $("#findingsWrap");
  fw.innerHTML = "";
  js.targets.forEach((t, ti) => fw.appendChild(targetSection(t, ti)));
}

function renderBars(counts) {
  const wrap = $("#techBars");
  wrap.innerHTML = "";
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 7);
  if (!top.length) {
    wrap.innerHTML = '<div style="color:var(--muted);font-size:13px">No suspicious techniques raised.</div>';
    return;
  }
  const max = Math.max(...top.map(([, c]) => c));
  const palette = ["#22d3ee", "#a78bfa", "#f472b6", "#fbbf24", "#34d399", "#60a5fa", "#fb7185"];
  top.forEach(([key, count], i) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    const c = palette[i % palette.length];
    const pct = (count / max) * 100;
    row.innerHTML =
      '<div class="bl" style="--bc:' + c + '"><span class="dot"></span>' +
      (TECH_COUNT_LABEL[key] || key) + '</div>' +
      '<div class="bar-track"><div class="bar-fill" data-w="' + pct +
      '" style="background:' + c + '"></div></div>' +
      '<div class="bv">' + count + "</div>";
    wrap.appendChild(row);
  });
  requestAnimationFrame(() => {
    wrap.querySelectorAll(".bar-fill").forEach((f) => (f.style.width = f.dataset.w + "%"));
  });
}

function targetSection(t, ti) {
  const sec = document.createElement("div");
  sec.className = "panel panel-pad";
  sec.style.marginTop = "18px";
  const badges = Object.entries(t.counts).filter(([k]) => k !== "Safe")
    .map(([k, v]) => v ? '<span class="risk-badge risk-' + k +
      '" style="margin-right:6px">' + k + ": " + v + "</span>" : "").join("");
  let rows = t.findings.map(findingRow).join("");
  if (!t.findings || !t.findings.length) {
    rows = '<tr><td colspan="7" style="color:var(--muted)">No parameters found to assess.</td></tr>';
  }
  sec.innerHTML =
    '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:8px">' +
    '<span class="risk-badge risk-' + t.risk + '">' + t.risk + "</span>" +
    '<div style="flex:1;min-width:200px">' +
    '<h3 style="font-size:15.5px;font-family:var(--mono);word-break:break-all">' + esc(t.url) + "</h3>" +
    '<div style="font-size:12px;color:var(--muted);margin-top:3px">#' + (ti + 1) + " · " + t.method +
    " · " + t.param_count + " params · " + t.duration_ms + " ms" +
    (t.vulnerable ? '<span style="color:var(--high)"> · FLAGGED</span>' : "") + "</div></div>" +
    "<div>" + badges + "</div></div>" +
    '<div class="table-wrap"><table class="finder">' +
    "<thead><tr><th>Parameter</th><th>Loc</th><th>Risk</th><th style=\"width:110px\">Score</th><th>Detected techniques</th><th>Evidence</th><th></th></tr></thead>" +
    "<tbody>" + rows + "</tbody></table></div>";
  return sec;
}

function findingRow(f) {
  const col = RISK_COLORS[f.risk] || "var(--muted)";
  const chips = f.techniques.slice(0, 3).map((t) => "<code>" + esc(t.key) + "</code>").join(" ") ||
    "<span style='color:var(--muted)'>–</span>";
  const ev = (f.techniques[0] && f.techniques[0].evidence)
    ? esc(f.techniques[0].evidence) : "–";
  return '<tr onclick="toggleRow(event, this)" style="cursor:pointer">' +
    '<td class="param-name">' + esc(f.name) + "</td>" +
    '<td><span style="font-size:12px;color:var(--muted)">' + esc(f.location) + "</span></td>" +
    '<td><span class="risk-badge risk-' + f.risk + '">' + f.risk + "</span></td>" +
    '<td><span class="score-cell" style="color:' + col + '">' + f.score + "</span>" +
    '<span class="mini-bar"><i style="width:' + f.score + ";background:" + col + '"></i></span></td>' +
    "<td>" + chips + "</td>" +
    '<td class="exp-cell">' + ev + "</td>" +
    '<td style="color:var(--muted);font-size:16px">▸</td></tr>' +
    '<tr class="row-expand"><td colspan="7"><div class="detail-box">' +
    '<div style="font-size:12px;color:var(--muted)">sample value</div>' +
    '<code style="color:#cbd5e1;word-break:break-all">' + esc(f.value) + "</code>" +
    '<div class="tech-grid">' + (f.techniques.map(techChip).join("") || "No techniques matched.") + "</div>" +
    '<div class="rec"><b>Recommendation — </b>' + esc(f.recommendation) + "</div>" +
    "</div></td></tr>";
}

function techChip(t) {
  const live = t.live ? ' class="live"' : "";
  return '<div class="tech-chip"' + live + ">" +
    "<b>" + esc(t.label) + '<span class="conf">conf ' + t.confidence.toFixed(2) +
    (t.live ? " · LIVE" : "") + "</span></b>" +
    '<span style="color:var(--muted);font-size:12px">' +
    esc(t.evidence || "matched offline") + "</span></div>";
}

function toggleRow(e, tr) {
  const next = tr.nextElementSibling;
  if (next && next.classList.contains("row-expand")) {
    const open = next.classList.toggle("open");
    tr.querySelector("td:last-child").textContent = open ? "▾" : "▸";
  }
}

/* ------------------------------------------------------------ downloads */
function download(format) {
  if (!state.rid) return toast("Nothing to download yet.", true);
  const a = document.createElement("a");
  a.href = "/api/report/" + state.rid + "/download/" + format;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast("Downloading " + format.toUpperCase() + " report…");
}

/* --------------------------------------------------------------- misc */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

let toastTimer;
function toast(msg, isErr) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.toggle("err", !!isErr);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

function refreshHistory() {
  fetch("/api/history").then((r) => r.json()).then((items) => {
    const wrap = $("#historyList");
    wrap.innerHTML = "";
    if (!items.length) {
      wrap.innerHTML = '<div class="hist-empty">No scans yet.</div>';
      return;
    }
    items.slice().reverse().slice(0, 12).forEach((h) => {
      const el = document.createElement("div");
      el.className = "hist-item";
      el.innerHTML =
        '<span class="risk-badge risk-' + esc(h.overall_risk) + '">' + esc(h.overall_risk) + "</span>" +
        '<div class="h-info"><b>' + esc(h.mode.toUpperCase()) + " · " + h.params +
        " params</b><span>" + esc(h.scanned_at) + " · " + h.targets + " target(s)</span></div>" +
        '<span style="color:var(--muted)">' + h.overall_score + "</span>";
      el.onclick = () => (window.location.href = "/report/" + h.id);
      wrap.appendChild(el);
    });
  }).catch(() => {});
}

function switchLiveUi() {
  const on = $("#liveToggle").checked;
  $("#consentRow").classList.toggle("hidden", !on);
  if (!on) $("#consent").checked = false;
}

/* --------------------------------------------------------------- boot */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.addEventListener("click", () => setMode(b.dataset.mode));
  });
  document.querySelectorAll(".example-link").forEach((l) => {
    l.addEventListener("click", loadExample);
  });
  $("#scanBtn").addEventListener("click", runScan);
  $("#liveToggle").addEventListener("change", switchLiveUi);
  initDropzone();
  refreshHistory();
});