(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const state = {
    dashboard: null,
    events: [],
    attackers: [],
    protocolFilter: "",
    typeFilter: "",
    pollTimer: null,
    chartTimeline: null,
    chartProtocol: null,
    interval: 3000,
  };

  /* ---------- Toast ---------- */
  const toast = (msg, type = "info") => {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;
    $("#toastContainer").appendChild(el);
    setTimeout(() => {
      el.classList.add("out");
      setTimeout(() => el.remove(), 320);
    }, 4200);
  };

  /* ---------- Navigation ---------- */
  const navLinks = $$(".nav-link");
  const sections = {};
  $$(".section").forEach((s) => { sections[s.id.replace("section-", "")] = s; });

  document.title = "Honeypot Intelligence Center";

  const pageTitles = {
    dashboard: ["Security Dashboard", "Real-time monitoring of attempted intrusions"],
    events: ["Live Event Stream", "Attacks against SSH and HTTP honeypots"],
    attackers: ["Attacker Fingerprints", "Behavioral signatures of persistent threats"],
    analysis: ["Credential Analysis", "Top usernames and passwords being tried"],
    reports: ["Downloads", "Export intelligence reports"],
  };

  function showSection(name) {
    navLinks.forEach((l) => l.classList.toggle("active", l.dataset.section === name));
    Object.values(sections).forEach((s) => s.classList.remove("active"));
    sections[name]?.classList.add("active");
    const t = pageTitles[name] || ["", ""];
    $("#pageTitle").textContent = t[0];
    $("#pageSubtitle").textContent = t[1];
  }

  navLinks.forEach((l) => l.addEventListener("click", (e) => {
    e.preventDefault();
    showSection(l.dataset.section);
  }));
  $$("[data-jump]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    showSection(a.dataset.jump);
  }));

  /* ---------- Escaping ---------- */
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  /* ---------- Helpers ---------- */
  function riskPill(score) {
    score = parseFloat(score) || 0;
    if (score >= 70) return `<span class="pill pill-bad">CRITICAL ${score.toFixed(0)}</span>`;
    if (score >= 50) return `<span class="pill pill-bad" style="background:rgba(240,136,62,.14);color:#f0883e">HIGH ${score.toFixed(0)}</span>`;
    if (score >= 25) return `<span class="pill pill-warn">MED ${score.toFixed(0)}</span>`;
    if (score > 0) return `<span class="pill pill-muted" style="color:var(--yellow)">LOW ${score.toFixed(0)}</span>`;
    return `<span class="pill pill-muted">UNKNOWN</span>`;
  }

  const timeAgo = (ts) => {
    if (!ts) return "-";
    const diff = (Date.now() - new Date(ts).getTime()) / 1000;
    if (diff < 10) return "just now";
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const shortHash = (h) => (h ? h.slice(0, 12) : "-");

  /* ---------- Chart helpers (canvas, no deps) ---------- */
  function drawBarChart(canvas, labels, series, colors, stacked = false) {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 300 * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = "300px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, 300);

    let max = 0;
    series.forEach((arr) => arr.forEach((v) => { if (v > max) max = v; }));
    const maxVal = max || 1;

    const padL = 36, padR = 10, padT = 16, padB = 28;
    const chartW = rect.width - padL - padR;
    const chartH = 300 - padT - padB;

    // gridlines
    ctx.strokeStyle = "rgba(139,148,158,.12)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padT + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(rect.width - padR, y);
      ctx.stroke();
      const val = maxVal - (maxVal / 4) * i;
      ctx.fillStyle = "#6e7681";
      ctx.font = "10px Segoe UI";
      ctx.textAlign = "right";
      ctx.fillText(Math.round(val).toString(), padL - 6, y + 4);
    }

    const groupPct = stacked ? 1 : 0.35;
    const barCount = labels.length;
    const slot = chartW / barCount;
    const barGroupW = slot * groupPct;
    const barW = stacked ? barGroupW : barGroupW / series.length;

    series.forEach((arr, si) => {
      arr.forEach((v, i) => {
        const x = padL + slot * i + (slot - barGroupW) / 2;
        const h = (v / maxVal) * chartH;
        let bx;
        if (stacked) {
          let offset = 0;
          for (let k = 0; k <= si; k++) offset += (series[k]?.[i] ?? 0);
          bx = x;
          const bh = ((v / maxVal) * chartH);
          const yOffset = padT + chartH - ((offset / maxVal) * chartH);
          ctx.fillStyle = colors[si];
          roundRect(ctx, bx, yOffset, barW, bh, 3);
          ctx.fill();
        } else {
          bx = x + si * barW;
          roundRect(ctx, bx, padT + chartH - h, barW - 2, h, 3);
          ctx.fillStyle = colors[si];
          ctx.fill();
        }
      });
    });

    ctx.textAlign = "center";
    ctx.font = "10px Segoe UI";
    labels.forEach((lab, i) => {
      const x = padL + slot * i + slot / 2;
      ctx.fillStyle = "#8b949e";
      ctx.fillText(lab, x, 300 - 8);
    });
  }

  function roundRect(ctx, x, y, w, h, r) {
    if (h < 1) h = 1;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function drawDoughnut(canvas, labels, values, colors) {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 300 * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = "300px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const total = values.reduce((a, b) => a + b, 0) || 1;
    const cx = rect.width / 2, cy = 150, r = Math.min(110, rect.width / 3);
    let start = -Math.PI / 2;

    values.forEach((v, i) => {
      const angle = (v / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = colors[i];
      ctx.fill();
      start += angle;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.58, 0, Math.PI * 2);
    ctx.fillStyle = "#161b22";
    ctx.fill();

    ctx.fillStyle = "#e6edf3";
    ctx.font = "800 24px Segoe UI";
    ctx.textAlign = "center";
    ctx.fillText(total.toString(), cx, cy + 4);

    // legend
    let ly = 24;
    labels.forEach((lab, i) => {
      ctx.textAlign = "left";
      ctx.font = "11px Segoe UI";
      ctx.fillStyle = colors[i];
      ctx.fillRect(rect.width - 92, ly, 8, 8);
      ctx.fillStyle = "#8b949e";
      ctx.fillText(lab, rect.width - 78, ly + 9);
      ly += 18;
    });
  }

  /* ---------- Rendering ---------- */
  function renderDashboard(data) {
    state.dashboard = data;
    $("#statTotalEvents").textContent = (data.total_events || 0).toLocaleString();
    $("#statAttackers").textContent = (data.total_attackers || 0).toLocaleString();
    $("#statIps").textContent = (data.unique_ips || 0).toLocaleString();
    $("#statSsh").textContent = (data.total_ssh || 0).toLocaleString();
    $("#statHttp").textContent = (data.total_http || 0).toLocaleString();
    $("#statHighRisk").textContent = data.high_risk_attackers || 0;
    $("#trendToday").textContent = `Today: ${data.today_events || 0}`;

    // timeline
    const tl = data.timeline || [];
    const labels = tl.map((t) => {
      const h = (t.hour || "").split(" ")[1] || "";
      return h.slice(0, 5);
    });
    const sshSeries = tl.filter((t) => t.protocol === "ssh").map((t) => t.count);
    const httpSeries = tl.filter((t) => t.protocol === "http").map((t) => t.count);
    const byHour = {};
    tl.forEach((t) => {
      const key = (t.hour || "").split(" ")[1]?.slice(0, 2) || "";
      byHour[key] = byHour[key] || { ssh: 0, http: 0, sshCount: 0, httpCount: 0 };
      if (t.protocol === "ssh") { byHour[key].ssh += t.count; byHour[key].sshCount++; }
      if (t.protocol === "http") { byHour[key].http += t.count; byHour[key].httpCount++; }
    });
    const hours = Object.keys(byHour).sort();
    const sshArr = hours.map((h) => byHour[h].ssh);
    const httpArr = hours.map((h) => byHour[h].http);
    drawBarChart($("#timelineChart"), hours, [sshArr, httpArr], ["#58a6ff", "#bc8cff"], true);

    // protocol doughnut
    const ps = data.protocol_stats || [];
    const pLabels = ps.map((p) => `${p.protocol.toUpperCase()} / ${p.event_type}`);
    const pValues = ps.map((p) => p.count);
    const pColors = ["#58a6ff", "#39c5cf", "#bc8cff", "#d29922", "#3fb950", "#f85149"];
    drawDoughnut($("#protocolChart"), pLabels.slice(0, 5), pValues.slice(0, 5), pColors);

    // top ips table
    const ips = data.top_ips || [];
    $("#topIpsTable tbody").innerHTML = ips.map((r) => `
      <tr>
        <td><code>${esc(r.src_ip)}</code></td>
        <td><span class="pill pill-warn">${r.attempts}</span></td>
        <td>${(r.protocols || "").split(",").map((p) => `<span class="pill ${p === "ssh" ? "pill-ssh" : "pill-http"}">${esc(p)}</span>`).join(" ")}</td>
        <td>${timeAgo(r.last_seen)}</td>
      </tr>`).join("") || `<tr><td colspan="4" style="text-align:center;color:var(--muted)">No data yet</td></tr>`;

    // geo table
    const geo = data.geo_stats || [];
    $("#geoTable tbody").innerHTML = geo.slice(0, 8).map((g) => `
      <tr>
        <td><span class="pill pill-muted">${esc(g.geo_country || "Unknown")}</span></td>
        <td>${g.unique_ips}</td>
        <td><span class="pill pill-ssh">${g.total}</span></td>
      </tr>`).join("") || `<tr><td colspan="3" style="text-align:center;color:var(--muted)">No geo data</td></tr>`;
  }

  function renderEvents(full = false) {
    const rows = full ? state.events : state.events.slice(0, 200);
    $("#eventsTable tbody").innerHTML = rows.map((e) => {
      const risk = riskPill(e.risk_score ?? 0);
      return `
      <tr>
        <td>${timeAgo(e.timestamp)}</td>
        <td><span class="pill ${e.protocol === "ssh" ? "pill-ssh" : "pill-http"}">${esc(e.protocol)}</span></td>
        <td><code>${esc(e.src_ip)}</code>:${esc(e.src_port || "")}</td>
        <td>${esc(e.event_type)}</td>
        <td><code>${esc(e.username || "-")}</code></td>
        <td>${esc((e.raw_data || "").slice(0, 80))}</td>
        <td>${risk}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:30px">Waiting for intrusion attempts...</td></tr>`;
  }

  function renderAttackers() {
    $("#attackersTable tbody").innerHTML = state.attackers.map((a) => `
      <tr>
        <td><code title="${esc(a.fingerprint_hash)}">${esc(shortHash(a.fingerprint_hash))}</code></td>
        <td>${esc(a.first_seen).slice(0, 16)}</td>
        <td>${timeAgo(a.last_seen)}</td>
        <td><span class="pill pill-warn">${a.total_attacks}</span></td>
        <td>${riskPill(a.risk_score)}</td>
        <td>${(function () { try { return JSON.parse(a.tags || "[]").slice(0, 3).map((t) => `<span class="filter-badge" title="${esc(t)}" >${esc(t.toUpperCase())}</span>`).join(" "); } catch (x) { return "-"; } })()}</td>
      </tr>`).join("") || `<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:30px">No attackers fingerprinted yet</td></tr>`;
  }

  function renderAnalysis() {
    fetch("/api/top/usernames").then((r) => r.json()).then((users) => {
      const max = Math.max(...users.map((u) => u.attempts), 1);
      $("#usernamesBars").innerHTML = users.slice(0, 15).map((u) => `
        <div class="bar-row">
          <span class="bar-label">${esc(u.username)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${(u.attempts / max) * 100}%"></div></div>
          <span class="bar-count">${u.attempts}</span>
        </div>`).join("") || `<div class="muted">No credential attempts yet</div>`;
    });
    fetch("/api/top/passwords").then((r) => r.json()).then((pass) => {
      const max = Math.max(...pass.map((p) => p.attempts), 1);
      $("#passwordsBars").innerHTML = pass.slice(0, 15).map((p) => `
        <div class="bar-row">
          <span class="bar-label">${esc(p.password)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${(p.attempts / max) * 100}%"></div></div>
          <span class="bar-count">${p.attempts}</span>
        </div>`).join("") || `<div class="muted">No credential attempts yet</div>`;
    });
  }

  /* ---------- Data fetching ---------- */
  async function loadStatus() {
    try {
      const res = await fetch("/api/status");
      const s = await res.json();
      const sshOn = s.ssh?.running, httpOn = s.http?.running;
      const any = sshOn || httpOn;
      $("#bannerDot").className = `dot large ${any ? "running" : "stopped"}`;
      $("#bannerText").textContent = any
        ? "Honeypots are ACTIVE and capturing intrusions"
        : "Honeypots are STOPPED - click Start to begin capture";
      $("#statusBanner").className = `status-banner ${any ? "live" : "dead"}`;
      $("#bannerSsh").textContent = sshOn ? `:${s.ssh.port} (running)` : "OFF";
      $("#bannerHttp").textContent = httpOn ? `:${s.http.port} (running)` : "OFF";
      $("#serverStatus").innerHTML = `<span class="dot ${any ? "running" : "stopped"}"></span><span>${any ? "Services Active" : "Services Idle"}</span>`;
    } catch (e) {
      $("#serverStatus").innerHTML = `<span class="dot stopped"></span><span>API unreachable</span>`;
    }
  }

  async function loadDashboard() {
    try {
      const res = await fetch("/api/dashboard");
      if (!res.ok) throw new Error("bad status");
      renderDashboard(await res.json());
    } catch (e) {
      toast("Failed to load dashboard: " + e.message, "error");
    }
  }

  async function loadEvents() {
    try {
      const q = new URLSearchParams({ limit: "500" });
      if (state.protocolFilter) q.set("protocol", state.protocolFilter);
      if (state.typeFilter) q.set("event_type", state.typeFilter);
      const res = await fetch("/api/events?" + q.toString());
      if (!res.ok) throw new Error("bad status");
      state.events = await res.json();
      renderEvents();
    } catch (e) {
      toast("Failed to load events: " + e.message, "error");
    }
  }

  async function loadAttackers() {
    try {
      const res = await fetch("/api/attackers?limit=100");
      if (!res.ok) throw new Error("bad status");
      state.attackers = await res.json();
      renderAttackers();
    } catch (e) {
      toast("Failed to load attackers: " + e.message, "error");
    }
  }

  /* ---------- Controls ---------- */
  async function startHoneypots() {
    try {
      const res = await fetch("/api/start", { method: "POST" });
      const data = await res.json();
      toast("Honeypots started on SSH:" + data.state.ssh.port + " HTTP:" + data.state.http.port, "success");
      await loadStatus();
    } catch (e) {
      toast("Failed to start: " + e.message, "error");
    }
  }

  async function stopHoneypots() {
    try {
      const res = await fetch("/api/stop", { method: "POST" });
      const data = await res.json();
      toast("Honeypots stopped", "warning");
      await loadStatus();
    } catch (e) {
      toast("Failed to stop: " + e.message, "error");
    }
  }

  $("#btnStart").addEventListener("click", startHoneypots);
  $("#btnStop").addEventListener("click", stopHoneypots);
  $("#btnRefresh").addEventListener("click", refreshAll);
  $("#btnApplyFilter").addEventListener("click", () => {
    state.protocolFilter = $("#filterProtocol").value;
    state.typeFilter = $("#filterType").value;
    loadEvents().then(() => toast("Filters applied", "success"));
  });

  function refreshAll() {
    loadStatus();
    loadDashboard();
    loadEvents();
    loadAttackers();
  }

  /* ---------- Polling ---------- */
  let activeSection = "dashboard";
  setInterval(() => {
    loadStatus();
    loadDashboard();
    if (activeSection === "events") loadEvents();
    if (activeSection === "attackers") loadAttackers();
    if (activeSection === "attackers") loadAttackers();
    if (activeSection === "analysis") renderAnalysis();
  }, state.interval);

  /* Track active section for polling */
  const observer = new MutationObserver(() => {
    const active = $(".section.active");
    activeSection = active ? active.id.replace("section-", "") : "dashboard";
  });
  observer.observe($(".main"), { childList: true, subtree: true });

  /* Handle window resize for charts */
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (state.dashboard) renderDashboard(state.dashboard);
    }, 200);
  });

  /* ---------- Init ---------- */
  refreshAll();
  renderAnalysis();
  showSection("dashboard");
})();