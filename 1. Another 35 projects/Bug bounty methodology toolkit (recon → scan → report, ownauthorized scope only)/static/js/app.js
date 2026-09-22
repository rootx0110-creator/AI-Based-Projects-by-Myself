/* BBM Toolkit frontend */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const state = {
  scope: [],
  authorization: { confirmed: false },
  findings: [],
  runs: [],
  runtime: { status: "idle", log: [], stage: null, progress: 0, hosts_total: 0, hosts_done: 0 },
  polling: null,
  logRendered: 0,
};

/* ---------------- utils ---------------- */
function toast(msg, kind = "ok") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast show ${kind}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.className = "toast"), 4200);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* ignore */ }
  if (!res.ok) {
    const err = new Error(data.error || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------- tabs ---------------- */
$$(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    $$(".tab").forEach(b => b.classList.remove("active"));
    $$(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#panel-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "report") refreshReportMeta();
    if (btn.dataset.tab === "toolkit") generateCmds();
  });
});

/* ---------------- state sync ---------------- */
function renderPills() {
  const auth = $("#authPill");
  if (state.authorization.confirmed) {
    auth.textContent = "AUTH: ON";
    auth.classList.add("on");
  } else {
    auth.textContent = "AUTH: OFF";
    auth.classList.remove("on");
  }
  const ins = state.scope.filter(e => e.status === "in").length;
  $("#scopePill").textContent = `SCOPE: ${ins}`;

  const r = state.runtime;
  const run = $("#runPill");
  const map = {
    idle: ["IDLE", ""], starting: ["STARTING…", "run"], running: ["RUNNING", "run"],
    done: ["DONE", "done"], cancelled: ["CANCELLED", "err"], error: ["ERROR", "err"],
  };
  const [label, cls] = map[r.status] || [String(r.status).toUpperCase(), ""];
  run.textContent = label;
  run.className = `pill pill-run ${cls}`;

  const n = state.findings.length;
  $("#findBadge").textContent = n;
  $("#findBadge").classList.toggle("hot", n > 0);
}

function renderGate() {
  const box = $("#gateBox");
  const open = state.authorization.confirmed;
  box.classList.toggle("open", open);
  $("#gateIcon").textContent = open ? "OPEN" : "LOCK";
  $("#gateText").innerHTML = open
    ? `Pipeline gate is <strong>open</strong>. Only in-scope targets will be tested.`
    : `Pipeline gate is <strong>closed</strong>. Sign the attestation to enable the run.`;
  $("#authCheck").checked = open;
  $("#authStatement").value = open ? (state.authorization.statement || "") : $("#authStatement").value;
  $("#authMeta").textContent = open
    ? `Attested at ${state.authorization.confirmed_at || ""}`
    : "Not attested.";
  $("#authBtn").textContent = open ? "Update attestation" : "Confirm authorization";
}

function renderScope() {
  const tbody = $("#scopeTable tbody");
  tbody.innerHTML = state.scope.map(e => `
    <tr>
      <td><code>${esc(e.value)}</code></td>
      <td><span class="chip chip-type">${esc(e.type)}</span></td>
      <td><span class="chip chip-${e.status === "in" ? "in" : "out"}">${e.status === "in" ? "in scope" : "out"}</span></td>
      <td>${esc(e.note || "—")}</td>
      <td><button class="del-x" data-del="${esc(e.id)}" title="remove">✕</button></td>
    </tr>`).join("");
  $("#scopeEmpty").style.display = state.scope.length ? "none" : "block";
  $$("[data-del]", tbody).forEach(b => b.addEventListener("click", async () => {
    try {
      const r = await api("/api/scope", { method: "POST", body: { action: "remove", id: b.dataset.del } });
      state.scope = r.scope;
      renderScope(); renderPills();
      toast("Scope entry removed");
    } catch (e) { toast(e.message, "err"); }
  }));
}

const SEV_RANK = { high: 0, medium: 1, low: 2, info: 3 };

function renderFindings() {
  const list = $("#findingsList");
  const fs = [...state.findings].sort(
    (a, b) => (SEV_RANK[a.severity] ?? 9) - (SEV_RANK[b.severity] ?? 9));
  const counts = { high: 0, medium: 0, low: 0, info: 0 };
  fs.forEach(f => counts[f.severity] = (counts[f.severity] || 0) + 1);
  $("#cHigh").textContent = `${counts.high} high`;
  $("#cMed").textContent = `${counts.medium} medium`;
  $("#cLow").textContent = `${counts.low} low`;
  $("#cInfo").textContent = `${counts.info} info`;

  if (!fs.length) {
    list.innerHTML = `<p class="empty">No findings yet — complete a run on the Pipeline tab.</p>`;
    return;
  }
  list.innerHTML = fs.map(f => `
    <article class="finding ${esc(f.severity)}">
      <div class="fid">${esc(f.id || "")} · ${esc(f.category || "general")} · ${esc(f.timestamp || "")}</div>
      <h4><span class="sev sev-${esc(f.severity)}">${esc(f.severity)}</span> ${esc(f.title)}</h4>
      <div class="detail">Target: <code>${esc(f.target)}</code></div>
      <div class="detail">${esc(f.detail)}</div>
      ${f.why ? `<div class="detail" style="color:#94a3b8">Impact: ${esc(f.why)}</div>` : ""}
      ${f.recommendation ? `<div class="fix"><b>Fix:</b> ${esc(f.recommendation)}</div>` : ""}
      ${f.evidence ? `<pre>${esc(f.evidence)}</pre>` : ""}
    </article>`).join("");
}

/* ---------------- runtime rendering ---------------- */
function renderRuntime() {
  const r = state.runtime;
  $("#progBar").style.width = `${r.progress || 0}%`;
  $("#progPct").textContent = `${(r.progress || 0).toFixed(1)}%`;
  $("#stageLabel").textContent = r.stage_label || r.stage || "Idle";
  $("#hostMeter").textContent = `${r.hosts_done || 0} / ${r.hosts_total || 0}`;
  $("#currentHost").textContent = r.current_host || "—";

  const order = $$("#stageList li").map(li => li.dataset.stage);
  const idx = order.indexOf(r.stage);
  $$("#stageList li").forEach((li, i) => {
    li.classList.remove("active", "done");
    if (r.status === "done" || (idx >= 0 && i < idx)) li.classList.add("done");
    else if (i === idx && (r.status === "running" || r.status === "starting")) li.classList.add("active");
    else if (r.status === "done") li.classList.add("done");
  });

  const running = r.status === "running" || r.status === "starting";
  $("#startBtn").disabled = running || !state.authorization.confirmed;
  $("#stopBtn").disabled = !running;

  renderLog(r.log || []);
  renderPills();
}

function renderLog(lines) {
  const term = $("#terminal");
  if (state.logRendered > lines.length) { term.innerHTML = ""; state.logRendered = 0; }
  for (let i = state.logRendered; i < lines.length; i++) {
    const raw = lines[i];
    const div = document.createElement("div");
    div.className = "term-line";
    if (raw.includes("[warn]")) div.classList.add("term-warn");
    else if (raw.includes("[error]")) div.classList.add("term-error");
    else if (raw.includes("[info]")) div.classList.add("term-info");
    div.textContent = raw;
    term.appendChild(div);
  }
  state.logRendered = lines.length;
  while (term.children.length > 500) term.removeChild(term.firstChild);
  term.scrollTop = term.scrollHeight;
}

/* ---------------- polling ---------------- */
async function poll() {
  try {
    const r = await api("/api/recon/status");
    const wasRunning = ["running", "starting"].includes(state.runtime.status);
    state.runtime = r;
    renderRuntime();
    const nowRunning = ["running", "starting"].includes(r.status);
    if (wasRunning && !nowRunning) {
      toast(`Run ${r.status}${r.findings ? ` — ${r.findings.length} finding(s)` : ""}`,
            r.status === "done" ? "ok" : "err");
      await loadState({ silent: true });
    }
  } catch (_) { /* server restarting */ }
}
setInterval(poll, 900);

async function loadState({ silent = false } = {}) {
  try {
    const data = await api("/api/state");
    state.scope = data.state.scope || [];
    state.authorization = data.state.authorization || { confirmed: false };
    state.findings = data.state.findings || [];
    state.runs = data.state.runs || [];
    state.runtime = data.runtime || state.runtime;
    renderScope(); renderGate(); renderFindings(); renderRuntime(); renderPills();
    if (!silent) toast("State loaded");
  } catch (e) {
    if (!silent) toast(`Load failed: ${e.message}`, "err");
  }
}

/* ---------------- scope form ---------------- */
$("#scopeForm").addEventListener("submit", async ev => {
  ev.preventDefault();
  const value = $("#scopeValue").value.trim();
  const status = $("#scopeStatus").value;
  const note = $("#scopeNote").value.trim();
  if (!value) return;
  try {
    const r = await api("/api/scope", { method: "POST", body: { action: "add", value, status, note } });
    state.scope = r.scope;
    $("#scopeValue").value = ""; $("#scopeNote").value = "";
    renderScope(); renderPills();
    toast(`Added ${status === "in" ? "in-scope" : "out-of-scope"}: ${r.entry.value} (${r.entry.type})`);
  } catch (e) { toast(e.message, "err"); }
});

$("#clearScopeBtn").addEventListener("click", async () => {
  if (!confirm("Clear ALL scope entries?")) return;
  try {
    const r = await api("/api/scope", { method: "POST", body: { action: "clear" } });
    state.scope = r.scope;
    renderScope(); renderPills();
    toast("Scope cleared");
  } catch (e) { toast(e.message, "err"); }
});

/* ---------------- authorization ---------------- */
$("#authBtn").addEventListener("click", async () => {
  if (!$("#authCheck").checked) {
    toast("Tick the confirmation checkbox first", "err");
    return;
  }
  const statement = $("#authStatement").value.trim();
  if (statement.length < 10) {
    toast("Write a meaningful attestation statement (min 10 chars)", "err");
    return;
  }
  try {
    const r = await api("/api/authorize", { method: "POST", body: { confirmed: true, statement } });
    state.authorization = r.authorization;
    renderGate(); renderPills(); renderRuntime();
    toast("Authorization confirmed — gate open");
  } catch (e) { toast(e.message, "err"); }
});

$("#revokeBtn").addEventListener("click", async () => {
  try {
    const r = await api("/api/authorize", { method: "POST", body: { confirmed: false } });
    state.authorization = r.authorization;
    renderGate(); renderPills(); renderRuntime();
    toast("Authorization revoked — gate closed");
  } catch (e) { toast(e.message, "err"); }
});

/* ---------------- pipeline ---------------- */
$("#startBtn").addEventListener("click", async () => {
  if (!state.authorization.confirmed) {
    toast("Confirm authorization on the Scope tab first", "err");
    $$(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === "scope"));
    $$(".panel").forEach(p => p.classList.toggle("active", p.id === "panel-scope"));
    return;
  }
  try {
    $("#terminal").innerHTML = "";
    state.logRendered = 0;
    const r = await api("/api/recon/start", { method: "POST" });
    toast(`Run started — ${r.targets.length} target(s)`);
    state.runtime.status = "starting";
    renderRuntime();
  } catch (e) { toast(e.message, "err"); }
});

$("#stopBtn").addEventListener("click", async () => {
  try {
    await api("/api/recon/stop", { method: "POST" });
    toast("Stop requested…");
  } catch (e) { toast(e.message, "err"); }
});

$("#clearLogBtn").addEventListener("click", () => {
  $("#terminal").innerHTML = `<div class="term-line term-dim">// cleared</div>`;
  state.logRendered = (state.runtime.log || []).length;
});

/* ---------------- findings ---------------- */
$("#clearFindingsBtn").addEventListener("click", async () => {
  if (!confirm("Clear all stored findings?")) return;
  try {
    await api("/api/findings", { method: "DELETE" });
    state.findings = [];
    renderFindings(); renderPills();
    toast("Findings cleared");
  } catch (e) { toast(e.message, "err"); }
});

/* ---------------- report ---------------- */
function refreshReportMeta() {
  const latest = state.runs[0];
  const rows = [
    `findings   : ${state.findings.length}`,
    `last run   : ${latest ? `${latest.id} (${latest.status})` : "—"}`,
    `in-scope   : ${state.scope.filter(e => e.status === "in").length} entries`,
    `attestation: ${state.authorization.confirmed ? "confirmed" : "NOT confirmed"}`,
  ];
  $("#reportMeta").innerHTML = rows.map(r => `<div>${esc(r)}</div>`).join("");
}

$("#previewBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/api/report/html");
    const text = await res.text();
    $("#reportFrame").srcdoc = text;
    $("#reportHint").textContent = `Preview generated ${new Date().toLocaleString()} (${(text.length / 1024).toFixed(1)} KB)`;
    toast("Preview refreshed");
  } catch (e) { toast(e.message, "err"); }
});

$("#downloadBtn").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = "/api/report/download";
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast("Report download started");
});

/* ---------------- toolkit commands ---------------- */
const COMMANDS = [
  { label: "subfinder — passive subdomain enumeration",
    cmd: "subfinder -d {D} -all -silent -o subs-{D}.txt",
    why: "Passive sources only. Stay within program rules." },
  { label: "amass (passive) — subdomain enum",
    cmd: "amass enum -passive -d {D} -o amass-{D}.txt",
    why: "No touching of targets; purely OSINT." },
  { label: "httpx — probe discovered hosts",
    cmd: "httpx -l subs-{D}.txt -status-code -title -tech-detect -follow-redirects -o live-{D}.txt",
    why: "HTTP GET only; aligns with passive-first methodology." },
  { label: "dnsx — DNS resolution sweep",
    cmd: "dnsx -l subs-{D}.txt -resp -a -aaaa -cname -o dns-{D}.txt",
    why: "DNS queries against in-scope names." },
  { label: "nmap — service versions (if policy allows active scanning)",
    cmd: "nmap -sV -Pn --top-ports 1000 -iL in-scope-ips.txt -oA nmap-{D}",
    why: "ACTIVE — confirm the program permits port scanning first." },
  { label: "nuclei — template scan (if policy allows)",
    cmd: "nuclei -l live-{D}.txt -severity info,low,medium -rl 5 -o nuclei-{D}.txt",
    why: "ACTIVE — use low rate limits; read template policy." },
  { label: "feroxbuster — content discovery (if policy allows)",
    cmd: "feroxbuster -u https://{D} -w /path/to/wordlist -t 5 --rate-limit 50 -o ferox-{D}.txt",
    why: "ACTIVE — heavy traffic; only when content discovery is in-scope." },
  { label: "testssl.sh — deeper TLS review",
    cmd: "testssl.sh --quiet --protocols --vulnerabilities https://{D}",
    why: "Mostly passive handshake analysis." },
];

function generateCmds() {
  const d = ($("#toolDomain").value || "example.com").trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "") || "example.com";
  $("#cmdList").innerHTML = COMMANDS.map((c, i) => `
    <div class="cmd">
      <div class="cmd-main">
        <div class="cmd-label">${esc(c.label)}</div>
        <code id="cmd${i}">${esc(c.cmd.replaceAll("{D}", d))}</code>
        <div class="why">${esc(c.why)}</div>
      </div>
      <button class="btn btn-ghost btn-sm" data-copy="cmd${i}">Copy</button>
    </div>`).join("");
  $$("[data-copy]").forEach(b => b.addEventListener("click", async () => {
    const text = $(`#${b.dataset.copy}`).textContent;
    try {
      await navigator.clipboard.writeText(text);
      toast("Command copied");
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
      toast("Command copied");
    }
  }));
}
$("#genBtn").addEventListener("click", generateCmds);

/* ---------------- boot ---------------- */
loadState({ silent: true });
poll();
