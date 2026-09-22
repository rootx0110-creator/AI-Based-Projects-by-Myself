/* NEON GRID CTF — frontend runtime
   matrix rain · live feed · live scoreboard · toasts · charts · flag modal */
"use strict";

/* ----------------------------------------------------------------- helpers */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};
const MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

function toast(message, type = "info", ms = 3600) {
  let host = $("#toasts");
  if (!host) { host = document.createElement("div"); host.id = "toasts"; document.body.appendChild(host); }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .4s"; setTimeout(() => el.remove(), 420); }, ms);
}

/* ------------------------------------------------------------- matrix rain */
function startMatrix() {
  const canvas = document.getElementById("matrix");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const glyphs = "アイウエオカキクケコｱｲｳｴｵ01<>{}[]$#@%&*+=?;:/\\|";
  let cols, drops, w, h, fontSize = 15;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    cols = Math.floor(w / fontSize);
    drops = Array.from({ length: cols }, () => Math.random() * -100);
  }
  resize();
  window.addEventListener("resize", resize);

  let last = 0;
  (function frame(ts) {
    requestAnimationFrame(frame);
    if (ts - last < 50) return; // ~20fps, cheap
    last = ts;
    ctx.fillStyle = "rgba(4,7,13,0.14)";
    ctx.fillRect(0, 0, w, h);
    ctx.font = `${fontSize}px monospace`;
    for (let i = 0; i < cols; i++) {
      const ch = glyphs[(Math.random() * glyphs.length) | 0];
      const x = i * fontSize, y = drops[i] * fontSize;
      ctx.fillStyle = Math.random() < 0.03 ? "#bafff0" : "#00ffc3";
      ctx.fillText(ch, x, y);
      if (y > h && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  })(0);
}

/* ------------------------------------------------------------------- feed */
function connectFeed() {
  const feedEl = document.getElementById("feed");
  if (!feedEl) return;

  const add = (html, cls) => {
    const div = document.createElement("div");
    div.className = `feed-item ${cls}`;
    div.innerHTML = `<span class="t">${fmtTime(new Date().toISOString())}</span>${html}`;
    feedEl.prepend(div);
    while (feedEl.children.length > 40) feedEl.lastChild.remove();
  };

  const handle = (msg) => {
    try { msg = JSON.parse(msg); } catch (_) { /* already object */ }
    switch (msg.kind) {
      case "solve":
        add(`🏁 <b>${esc(msg.user)}</b> solved <b>${esc(msg.challenge)}</b> <span style="color:var(--amber)">+${msg.points}</span>`, "solve");
        if (window.__refreshBoard) window.__refreshBoard();
        break;
      case "attempt":
        add(`✖ <b>${esc(msg.user)}</b> fired at <b>${esc(msg.challenge)}</b> — miss`, "attempt");
        break;
      case "user_join":
        add(`👋 <b>${esc(msg.user)}</b> joined the grid`, "info");
        break;
      case "user_login":
        add(`🔓 <b>${esc(msg.user)}</b> came online`, "info");
        break;
      case "admin":
        add(`🛠 <b>ADMIN</b> — ${esc(msg.message || "update")}`, "info");
        break;
      default:
        add(`· ${esc(msg.kind || "event")}`, "info");
    }
  };

  const poll = () => {
    // Fallback polling of recent solves so the feed stays alive without ws.
    fetch("/api/scoreboard").then(r => r.json()).catch(() => {});
  };

  let ws = null, closed = false, retry = 0;
  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    try { ws = new WebSocket(`${proto}://${location.host}/ws/feed`); }
    catch (_) { return; }
    ws.onopen = () => { retry = 0; };
    ws.onmessage = (e) => handle(e.data);
    ws.onclose = () => { if (!closed) setTimeout(open, Math.min(5000, 800 * ++retry)); };
  };
  open();
  window.addEventListener("beforeunload", () => { closed = true; ws && ws.close(); });
  setInterval(poll, 15000);
}

/* --------------------------------------------------------------- scoreboard */
function initScoreboard() {
  const tbody = $("#board tbody");
  if (!tbody) return;
  let prev = new Map(); // id -> row element

  const render = (rows) => {
    const maxScore = Math.max(1, ...rows.map(r => r.score));
    const seen = new Set();
    rows.forEach((r, idx) => {
      let tr = prev.get(r.id);
      const isNew = !tr;
      if (!tr) {
        tr = document.createElement("tr");
        tr.dataset.uid = r.id;
        tbody.appendChild(tr);
      }
      tr.className = [
        r.rank <= 3 ? `rank-${r.rank}` : "",
        window.__meId === r.id ? "me" : "",
        isNew ? "bump" : "",
      ].filter(Boolean).join(" ");
      tr.innerHTML = `
        <td>${MEDALS[r.rank] || ""} ${r.rank}</td>
        <td>${esc(r.name)}</td>
        <td>${r.score}</td>
        <td>${r.solves}</td>
        <td style="min-width:120px">
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round(100 * r.score / maxScore)}%"></div></div>
        </td>
        <td class="muted">${fmtTime(r.last_solve_at)}</td>`;
      prev.set(r.id, tr);
      seen.add(r.id);
    });
    // remove departed players
    for (const [id, tr] of prev) {
      if (!seen.has(id)) { tr.remove(); prev.delete(id); }
    }
    // keep order correct
    rows.forEach(r => { const tr = prev.get(r.id); tr && tbody.appendChild(tr); });
  };

  const refresh = async () => {
    try {
      const res = await fetch("/api/scoreboard");
      const data = await res.json();
      render(data.board);
      const st = await (await fetch("/api/stats")).json();
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set("stat-teams", st.teams); set("stat-chals", st.challenges);
      set("stat-subs", st.submissions); set("stat-acc", st.accuracy + "%");
    } catch (_) { /* offline */ }
  };
  window.__refreshBoard = refresh;
  refresh();
  setInterval(refresh, 5000);
}

/* ------------------------------------------------------------------ charts */
function drawLineChart(canvas, series) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr; ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  // time domain
  let times = [];
  series.forEach(s => s.points.forEach(p => times.push(new Date(p.t).getTime())));
  if (!times.length) return;
  let t0 = Math.min(...times), t1 = Math.max(...times);
  if (t1 - t0 < 60000) t1 = t0 + 60000;
  let maxScore = 0;
  series.forEach(s => s.points.forEach(p => maxScore = Math.max(maxScore, p.score)));

  const padL = 46, padB = 26, padT = 14, padR = 12;
  const x = t => padL + (W - padL - padR) * (t - t0) / (t1 - t0);
  const y = v => H - padB - (H - padB - padT) * (v / Math.max(1, maxScore));
  const COLORS = ["#00ffc3", "#38bdf8", "#ff2d78", "#ffb020", "#a78bfa", "#4ade80"];

  // grid + axes
  ctx.strokeStyle = "rgba(125,147,168,.18)"; ctx.fillStyle = "#7d93a8";
  ctx.font = "10px monospace"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const gy = padT + (H - padB - padT) * i / 4;
    const gv = Math.round(maxScore * (1 - i / 4));
    ctx.beginPath(); ctx.moveTo(padL, gy); ctx.lineTo(W - padR, gy); ctx.stroke();
    ctx.fillText(String(gv), 6, gy + 3);
  }
  for (let i = 0; i <= 4; i++) {
    const gt = t0 + (t1 - t0) * i / 4;
    ctx.fillText(new Date(gt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      x(gt) - 22, H - 8);
  }

  series.forEach((s, i) => {
    const color = COLORS[i % COLORS.length];
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.shadowColor = color; ctx.shadowBlur = 8;
    ctx.beginPath();
    s.points.forEach((p, j) => {
      const px = x(new Date(p.t).getTime()), py = y(p.score);
      j ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;
    const lastP = s.points[s.points.length - 1];
    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(x(new Date(lastP.t).getTime()), y(lastP.score), 3.5, 0, 7); ctx.fill();
  });
}

function initCharts() {
  const canvas = document.getElementById("score-chart");
  if (!canvas) return;
  const load = async () => {
    try {
      const data = await (await fetch("/api/graph")).json();
      drawLineChart(canvas, data.series);
      // category chips
      const host = document.getElementById("cat-chips");
      if (host) {
        host.innerHTML = Object.entries(data.categories).map(([cat, d]) => `
          <div class="stat">
            <div class="num">${d.solved}</div>
            <div class="lbl">${esc(cat)} · ${d.solved}/${d.total} solves</div>
          </div>`).join("");
      }
    } catch (_) {}
  };
  load();
  window.addEventListener("resize", () => load());
  setInterval(load, 15000);
}

/* ---------------------------------------------------------- flag modal */
function initChallenges() {
  const modal = $("#ch-modal");
  if (!modal) return;   // not on the challenges page
  let active = null;

  // Event delegation on document: works no matter how many category
  // grids the page renders (cards may be added dynamically too).
  document.addEventListener("click", async (e) => {
    const card = e.target.closest(".ch-card");
    if (!card || !card.dataset.id) return;
    active = { id: card.dataset.id, title: card.dataset.title,
               desc: card.dataset.desc, meta: card.dataset.meta };
    $("#m-title").textContent = active.title;
    $("#m-meta").innerHTML = active.meta;
    $("#m-desc").textContent = active.desc;
    $("#m-flag").value = "";
    $("#m-msg").textContent = "";
    modal.classList.add("open");
    setTimeout(() => $("#m-flag").focus(), 60);
  });

  $("#m-close").addEventListener("click", () => modal.classList.remove("open"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("open"); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") modal.classList.remove("open"); });

  const submit = async () => {
    if (!active) return;
    const flag = $("#m-flag").value.trim();
    if (!flag) { $("#m-msg").textContent = "Enter a flag."; return; }
    const res = await fetch("/api/submit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: Number(active.id), flag }),
    });
    const data = await res.json();
    const msg = $("#m-msg");
    msg.textContent = data.message;
    msg.style.color = data.ok ? "var(--neon)" : "var(--red)";
    if (data.ok) {
      const card = $(`.ch-card[data-id="${active.id}"]`);
      if (card) card.classList.add("solved");
      toast(`✔ ${data.message}`, "ok");
      setTimeout(() => modal.classList.remove("open"), 900);
    } else {
      toast(data.message, "err");
    }
  };
  $("#m-submit").addEventListener("click", submit);
  $("#m-flag").addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
}

/* ------------------------------------------------------------------- admin */
function initAdmin() {
  const root = document.getElementById("admin-root");
  if (!root) return;
  const listEl = $("#ch-list");
  const form = $("#ch-form");

  const load = async () => {
    const data = await (await fetch("/admin/api/overview")).json();
    // challenges
    listEl.innerHTML = data.challenges.map(c => `
      <tr data-id="${c.id}">
        <td>${c.id}</td>
        <td>${esc(c.title)}</td>
        <td>${esc(c.category)}</td>
        <td>${c.points}${c.dynamic ? ' <span class="tag dyn">dyn</span>' : ""}</td>
        <td>${c.hidden ? "🚫 hidden" : "visible"} · ${c.solves} solves</td>
        <td>
          <button class="btn small" data-edit="${c.id}">Edit</button>
          <button class="btn small danger" data-del="${c.id}">Del</button>
        </td>
      </tr>`).join("");
    // config
    $("#cfg-name").value = data.config.ctf_name || "";
    $("#cfg-reg").checked = !!data.config.registration_open;
    $("#cfg-comp").checked = !!data.config.competition_open;
  };

  const fillForm = (c = {}) => {
    form.dataset.id = c.id || "";
    $("#f-title").value = c.title || "";
    $("#f-cat").value = c.category || "misc";
    $("#f-pts").value = c.points ?? 100;
    $("#f-desc").value = c.description || "";
    $("#f-flag").value = c.flag || "";
    $("#f-hint").value = c.flag_hint || "";
    $("#f-dyn").checked = !!c.dynamic;
    $("#f-hidden").checked = !!c.hidden;
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      id: form.dataset.id || null,
      title: $("#f-title").value, category: $("#f-cat").value,
      points: Number($("#f-pts").value), description: $("#f-desc").value,
      flag: $("#f-flag").value, flag_hint: $("#f-hint").value,
      dynamic: $("#f-dyn").checked, hidden: $("#f-hidden").checked,
    };
    const res = await fetch("/admin/api/challenge", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    toast(data.message, data.ok ? "ok" : "err");
    if (data.ok) { form.reset(); fillForm(); load(); }
  });

  listEl.addEventListener("click", async (e) => {
    const edit = e.target.closest("[data-edit]");
    const del = e.target.closest("[data-del]");
    if (edit) {
      const data = await (await fetch("/admin/api/overview")).json();
      const c = data.challenges.find(c => String(c.id) === edit.dataset.edit);
      if (c) { fillForm(c); window.scrollTo({ top: 0, behavior: "smooth" }); }
    }
    if (del) {
      if (!confirm("Delete this challenge?")) return;
      await fetch(`/admin/api/challenge/${del.dataset.del}`, { method: "DELETE" });
      toast("Challenge deleted.", "info");
      load();
    }
  });

  $("#cfg-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await fetch("/admin/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ctf_name: $("#cfg-name").value,
        registration_open: $("#cfg-reg").checked,
        competition_open: $("#cfg-comp").checked,
      }),
    });
    const data = await res.json();
    toast(data.message || "Saved.", data.ok ? "ok" : "err");
  });

  load();
}

/* -------------------------------------------------------------- boot */
document.addEventListener("DOMContentLoaded", () => {
  startMatrix();
  connectFeed();
  initScoreboard();
  initCharts();
  initChallenges();
  initAdmin();
});
