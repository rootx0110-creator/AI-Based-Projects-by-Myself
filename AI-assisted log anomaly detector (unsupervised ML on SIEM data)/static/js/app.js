"use strict";

const $ = (id) => document.getElementById(id);

let pendingFile = null;

/* ---------- drag & drop ---------- */
const drop = $("drop");
const fileInput = $("file");
let fileBadge = null;

drop.addEventListener("click", () => fileInput.click());
["dragover", "dragenter"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => {
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if (f) setFile(f);
});
fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(f) {
  pendingFile = f;
  if (!fileBadge) {
    fileBadge = document.createElement("span");
    fileBadge.className = "filebadge";
    drop.appendChild(fileBadge);
  }
  fileBadge.textContent = f.name + "  (" + fmtBytes(f.size) + ")";
  setStatus("Ready to analyse \u2014 press Run.", "");
}

function fmtBytes(n) {
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
  return (n / 1048576).toFixed(2) + " MB";
}

/* ---------- mode chips ---------- */
const chips = $("chips");
chips.addEventListener("change", (e) => {
  if (e.target.type === "checkbox") e.target.closest("label").classList.toggle("sel", e.target.checked);
});

/* ---------- sensitivity slider ---------- */
const contam = $("contam");
contam.addEventListener("input", () => { $("contamOut").textContent = contam.value + "%"; });

/* ---------- status ---------- */
function setStatus(msg, cls) {
  const s = $("status");
  s.textContent = msg;
  s.className = "status" + (cls ? " " + cls : "");
}
function busy(on) {
  $("btnRun").disabled = on;
  const s = $("status");
  if (on) {
    const sp = document.createElement("span");
    sp.className = "spinner";
    s.innerHTML = "";
    s.appendChild(sp);
    s.appendChild(document.createTextNode("  analysing \u2014 "));
  }
}

/* ---------- run ---------- */
$("btnRun").addEventListener("click", run);

async function run() {
  busy(true);
  setStatus("Uploading and running the ensemble \u2026", "working");
  const fd = new FormData();
  if (pendingFile) fd.append("file", pendingFile);
  else {
    fd.append("sample", "1");
    setStatus("Generating bundled sample feed and detecting \u2026", "working");
  }
  fd.append("contamination", (contam.value / 100).toFixed(2));
  const models = Array.from(document.querySelectorAll('#chips input:checked')).map((i) => i.value);
  fd.append("models", models.length ? models.join(",") : "if");

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error((data && data.error) || "analysis failed");
    busy(false);
    setStatus("Detection complete in " + (data.timings.total || 0).toFixed(1) + "s.", "working");
    render(data);
  } catch (err) {
    busy(false);
    setStatus("\u274c " + err.message, "");
  }
}

/* ---------- sample download ---------- */
$("btnSample").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = "/api/sample";
  a.download = "sample_siem_events.csv";
  a.click();
});

/* ---------- report download ---------- */
$("btnReport").addEventListener("click", async () => {
  try {
    setStatus("Rendering report \u2026", "working");
    const res = await fetch("/api/report", { method: "POST" });
    if (!res.ok) throw new Error("report unavailable");
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "anomaly_report_" + ts() + ".html";
    a.click();
    URL.revokeObjectURL(a.href);
    setStatus("Report downloaded.", "working");
  } catch (e) { setStatus("\u274c " + e.message, ""); }
});

function ts() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "_" + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds());
}

/* ---------- rendering ---------- */
function render(data) {
  const s = data.summary;
  $("results").style.display = "block";
  $("runMeta").textContent =
    s.events + " events \u00b7 " + s.flagged + " flagged (" + (s.rate || 0).toFixed(1) + "%) \u00b7 " +
    s.incidents + " incident clusters \u00b7 " + s.features + " feature dims \u00b7 " + s.models + " detectors \u00b7 " +
    (s.format || "sample");

  const lvl = s.level === "critical" ? "crit" : s.level === "attention" ? "" : "good";
  $("cards").innerHTML = [
    card("events", s.events, "events analysed"),
    card("flagged", s.flagged, "anomalies flagged", lvl),
    card("incidents", s.incidents, "incident clusters", lvl),
    card("rate", (s.rate || 0).toFixed(1) + "%", "detection rate", lvl),
    card("features", s.features, "feature dimensions"),
    card("models", s.models, "ensemble members"),
  ].join("");

  renderIncidents(data.incidents || []);
  renderTable(data.anomalies || []);
  renderVotes(data.models || []);
  window.scrollTo({ top: $("results").offsetTop - 10, behavior: "smooth" });
}

function card(key, num, lbl, cls) {
  return '<div class="card ' + (cls || "") + '"><div class="num" id="c_' + key + '">' +
    esc(num) + '</div><div class="lbl">' + lbl + "</div></div>";
}

function renderIncidents(incs) {
  $("incidents").innerHTML = incs.map((c) => {
    const srcs = c.src_ips.join(", ") + (c.more_srcs > 0 ? " (+" + c.more_srcs + " more)" : "");
    const sevCls = c.severity >= 8 ? "sev8" : c.severity >= 6 ? "sev" : "";
    return '<div class="incident">' +
      '<div class="row1"><span class="etype">' + esc(c.event_type) + "</span>" +
      '<span class="score">' + c.max_score.toFixed(2) + '</span></div>' +
      '<div class="meta">' +
      '<span class="badge">' + c.size + " events</span>" +
      '<span class="badge ' + sevCls + '">sev ' + c.severity + '</span>' +
      (c.flagged ? '<span class="badge" style="background:rgba(217,164,65,.16);color:var(--accent-soft);border-color:rgba(217,164,65,.45)">flagged</span>' : "") +
      '<br><b>user</b> ' + esc(c.users) +
      '<br><b>sources</b> ' + esc(srcs) +
      '<br><b>rep.</b> ' + esc(c.top_event.ts) + " \u00b7 " +
      esc(c.top_event.src_ip) + " \u2192 " + esc(c.top_event.dst_ip) +
      "<br><span class=muted>" + esc(c.top_event.message) + "</span>" +
      "</div></div>";
  }).join("") || '<div class="empty" style="grid-column:1/-1">No incident clusters found.</div>';
}

function renderTable(rows) {
  const body = $("tblBody");
  body.innerHTML = rows.map((r, i) => {
    const pct = Math.min(100, Math.round(100 * r.score / 1.5));
    const sevCls = r.sev >= 8 ? "hi" : r.sev >= 6 ? "mid" : "";
    const whyLen = (r.why || []).length;
    return '<tr>' +
      '<td><div class="score-cell"><span style="font-weight:700">' + r.score.toFixed(2) + "</span>" +
      '<div class="score-bar"><i style="width:' + pct + '%"></i></div></div></td>' +
      '<td><span class="sev-pill ' + sevCls + '">' + (r.sev || "-") + "</span></td>" +
      '<td class="mono">' + esc(r.ts) + "</td>" +
      '<td>' + esc(r.event_type) + "</td>" +
      '<td class="mono">' + esc(r.src_ip) + "</td>" +
      '<td class="mono">' + esc(r.dst_ip) + "</td>" +
      '<td>' + esc(r.user) + "</td>" +
      '<td><span class=muted>' + esc(r.message) + "</span></td>" +
      '<td>' + (whyLen ? '<span class="expand" data-i="' + i + '">why</span>' : "") + "</td>" +
      "</tr>" +
      '<tr class="row-reason" data-w="' + i + '"><td colspan="9" class="reason-cell">' +
      '<b class="tag" style="color:var(--accent)">Why this event is anomalous</b><ul>' +
      (r.why || []).map((w) => "<li><b class='tag'>" + esc(w.reason) + "</b>" +
        " &mdash; deviation " + w.weight.toFixed(1) + "</li>").join("") +
      "</ul></td></tr>";
  }).join("");
  body.querySelectorAll(".expand").forEach((el) => el.addEventListener("click", () => {
    const i = el.dataset.i;
    const r = document.querySelector('[data-w="' + i + '"]');
    r.classList.toggle("open");
  }));
}

function renderVotes(models) {
  $("votes").innerHTML = models.map((m) =>
    '<div class="vote' + (m.flagged > 0 ? " hot" : "") + '"><b>' + esc(m.name) + "</b>" +
    "voted " + m.flagged + " anomalies</div>").join("");
}

function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}