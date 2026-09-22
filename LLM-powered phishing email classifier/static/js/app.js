/* PhishGuard frontend */
"use strict";

const $ = (id) => document.getElementById(id);

const STATE = { last: null, llmSettings: null };

const CHIP = {
  safe:       { label: "SAFE",       color: "#22d3a7", icon: "\u2714" },
  suspicious: { label: "SUSPICIOUS", color: "#fbbf24", icon: "\u26a0" },
  phishing:   { label: "PHISHING",   color: "#f43f5e", icon: "\u26a0" },
};

function esc(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

function escapeUrl(u) {
  try { return new URL(u).href; } catch (_) { return u; }
}

/* ---------- toast ---------- */
let toastTimer = null;
function toast(msg, isErr) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.toggle("err", !!isErr);
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3400);
}

/* ---------- LLM status ---------- */
async function refreshStatus() {
  try {
    const [health, settings] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/settings").then((r) => r.json()),
    ]);
    STATE.llmSettings = settings.llm || { enabled: "0" };
    const on = !!(health.llm_enabled);
    const pill = $("llmStatus");
    pill.classList.toggle("on", on);
    pill.classList.toggle("off", !on);
    $("llmStatusText").textContent = on
      ? "LLM on · " + (health.llm_model || "model")
      : "LLM off";
    $("useLlm").checked = on;
  } catch (e) {
    $("llmStatusText").textContent = "LLM unavailable";
  }
}

/* ---------- scan ---------- */
$("scanForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("btnScan");
  const original = btn.innerHTML;

  const body = $("content").value.trim();
  if (!body) { toast("Paste an email first, then scan.", true); return; }

  btn.disabled = true;
  btn.classList.add("loading");
  btn.querySelector(".scan-btn-label").textContent = "Analyzing…";

  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: body,
        sender: $("from").value.trim(),
        recipient: $("to").value.trim(),
        subject: $("subject").value.trim(),
        use_llm: $("useLlm").checked ? true : null,
      }),
    });
    const data = await res.json();
    if (!res.ok) { throw new Error(data.error || "Scan failed"); }
    STATE.last = data;
    renderResult(data);
  } catch (err) {
    toast("Scan failed: " + err.message, true);
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
    btn.innerHTML = original;
    btn.querySelector(".scan-btn-label").textContent = "Analyze Email";
    refreshStatus();
  }
});

/* ---------- result rendering ---------- */
function renderResult(d) {
  const card = $("resultCard");
  const key = d.verdict in CHIP ? d.verdict : "suspicious";
  const chip = CHIP[key];

  card.classList.remove("reveal", "result-verdict-safe", "result-verdict-warn", "result-verdict-phish");
  card.hidden = false;

  $("verdictIcon").textContent = chip.icon;
  $("verdictText").textContent = chip.label;
  $("resultKicker").textContent = "ANALYSIS COMPLETE · " + (d.scanned_at || "");
  $("verdictSub").textContent = d.suggested_action || "";

  card.classList.add("result-verdict-" + key);

  animateRisk(d.risk, d.confidence, chip.color);
  renderMeta(d);
  renderEvidence(d.evidence || []);
  renderTactics(d.tactics || []);
  renderReasons(d.reasons || []);
  renderLLM(d.llm);

  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  card.classList.add("reveal");
}

function animateRisk(risk, conf, color) {
  const num = $("riskNum");
  const fill = $("riskFill");
  fill.style.background = color;
  num.textContent = "0";
  const t0 = performance.now();
  const dur = 1000;
  function step(t) {
    const p = Math.min(1, (t - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    num.textContent = Math.round(risk * eased);
    fill.style.width = (risk * eased).toFixed(1) + "%";
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
  const c = $("confNum");
  c.textContent = "0%";
  setTimeout(() => { c.textContent = (conf != null ? conf : 0) + "%"; }, 450);
}

function renderMeta(d) {
  const meta = $("metaRow");
  const em = d.email || {};
  const bits = [];
  if (em.from_email) bits.push("From: " + esc(em.from_email));
  if (em.subject) bits.push("Subject: " + esc(em.subject));
  if (d.analysis_id) bits.push("Report: " + esc(d.analysis_id));
  meta.innerHTML = bits.map((b) => "<span>" + b + "</span>").join("");
}

function renderEvidence(evidence) {
  const list = $("evidenceList");
  const flagged = evidence.filter((e) => (e.points || 0) > 0);
  if (!flagged.length) {
    list.innerHTML = `<li><span class="l">No weighted signals triggered — looks benign.</span></li>`;
    return;
  }
  list.innerHTML = flagged.map((e) => {
    const detail = esc(e.detail || "");
    const linkified = detail.replace(/https?:\/\/[^\s<]+/g, (u) =>
      `<a class="ev-link" href="${escapeUrl(u)}" target="_blank" rel="noopener">${esc(u)}</a>`);
    return `<li>
      <span class="w">${Math.round(e.points || 0)}</span>
      <span class="l">${esc(e.label)}<span class="d">${linkified}</span></span>
    </li>`;
  }).join("");
}

function renderTactics(tactics) {
  const box = $("tacticsList");
  if (!tactics.length) {
    box.innerHTML = `<span class="tactic" style="color:var(--muted);border-color:var(--line)">none identified</span>`;
    return;
  }
  box.innerHTML = tactics.map((t) => `<span class="tactic" style="color:var(--accent2);border-color:rgba(154,109,255,.4)">${esc(t)}</span>`).join("");
}

function renderReasons(reasons) {
  const list = $("reasonsList");
  list.innerHTML = (reasons || []).map((r) => `<li>${esc(r)}</li>`).join("");
}

function renderLLM(llm) {
  const panel = $("llmPanel");
  if (!llm) { panel.hidden = true; return; }
  panel.hidden = false;
  const body = $("llmBody");
  if (llm.failed || llm.error) {
    body.innerHTML = `<div class="lm"><span class="k">status</span><span>LLM call failed — ${esc(llm.error)}</span></div>`;
    return;
  }
  const v = (llm.verdict || "suspicious").toUpperCase();
  const color = CHIP[llm.verdict] ? CHIP[llm.verdict].color : "#fbbf24";
  body.innerHTML = `
    <div class="lm"><span class="k">verdict</span><span style="color:${color};font-weight:800">${esc(v)}</span></div>
    <div class="lm"><span class="k">confidence</span><span>${Math.round(llm.confidence || 0)}%</span></div>
    <div class="lm"><span class="k">model</span><span>${esc(llm.model || "unknown")}</span></div>
    <div class="lm"><span class="k">reasons</span><span>${esc((llm.reasons || []).join(" · "))}</span></div>
    <div class="lm"><span class="k">suggested</span><span>${esc(llm.suggested_action || "")}</span></div>`;
  if ((llm.tactics || []).length) {
    body.innerHTML += `<div class="lm"><span class="k">tactics</span><span>${esc(llm.tactics.join(", "))}</span></div>`;
  }
}

/* ---------- report download ---------- */
$("btnReport").addEventListener("click", () => {
  if (!STATE.last) { toast("Nothing to download yet.", true); return; }
  window.location.href = "/api/report/" + encodeURIComponent(STATE.last.analysis_id);
});

/* ---------- new scan ---------- */
$("btnNew").addEventListener("click", () => {
  $("resultCard").hidden = true;
  $("content").focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ---------- settings modal ---------- */
const modal = $("settingsModal");

$("btnSettings").addEventListener("click", openSettings);
$("btnCloseSettings").addEventListener("click", closeSettings);
$("btnCancelSettings").addEventListener("click", closeSettings);
modal.addEventListener("click", (e) => { if (e.target === modal) closeSettings(); });

function openSettings() {
  const s = STATE.llmSettings || { enabled: "0", api_base: "", api_key: "", model: "", timeout: "30" };
  $("setEnabled").checked = !!(s.enabled && String(s.enabled) !== "0");
  $("setBase").value = s.api_base || "https://api.openai.com/v1";
  $("setKey").value = s.api_key || "";
  $("setModel").value = s.model || "gpt-4o-mini";
  $("setTimeout").value = s.timeout || "30";
  modal.hidden = false;
}

function closeSettings() { modal.hidden = true; }

$("btnSaveSettings").addEventListener("click", async () => {
  const payload = {
    enabled: $("setEnabled").checked ? "1" : "0",
    api_base: $("setBase").value.trim(),
    api_key: $("setKey").value.trim(),
    model: $("setModel").value.trim(),
    timeout: String(Math.max(5, Math.min(120, parseInt($("setTimeout").value, 10) || 30))),
  };
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ llm: payload }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not save");
    STATE.llmSettings = data.llm;
    closeSettings();
    toast("LLM settings saved.");
    refreshStatus();
  } catch (err) {
    toast("Save failed: " + err.message, true);
  }
});

/* ---------- sample filler ---------- */
try {
  if (location.search.includes("demo=1")) {
    $("from").value = 'security@paypal-verify-info.com';
    $("subject").value = "URGENT: Your PayPal account has been suspended";
    $("content").value = `Dear PayPal customer,

We have detected unusual activity on your account and it has been temporarily suspended.

To restore your access, please verify your information immediately within 24 hours:

Click here to confirm your account: http://paypa1-secu.re.vip/verify/5330e1f2

Failure to verify will result in permanent account closure.

Regards,
PayPal Security Center`;
  }
} catch (_) { /* ignore */ }

window.addEventListener("DOMContentLoaded", refreshStatus);