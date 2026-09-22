/* ═══════════════════════════════════════════════════════════════════════
   CTF ARENA · main application controller
   wires data → 3D scene → UI (stats, leaderboard, challenges, modal)
   live score simulation, search & filtering, HTML report export.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  const DATA = window.CTF_DATA;
  const state = {
    teams: DATA.teams.slice(),
    challenges: DATA.challenges,
    cats: DATA.categories,
    selectedId: null,
    query: "",
    reportUrl: null,
    tick: 0
  };

  const $ = sel => document.querySelector(sel);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const fmt = n => (n || 0).toLocaleString("en-US");
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  /* ───────────── 3D scene ───────────── */
  function initScene() {
    const ok = SceneManager.start($("#bg-canvas"), state.teams, {
      select: id => openModal(id)
    });
    if (!ok) return;
    SceneManager.buildLabels($("#labels"));
  }

  /* ───────────── stats chips + legend ───────────── */
  function renderStats() {
    const top = state.teams[0];
    const solved = state.teams.reduce((s, t) => s + t.solvedCount, 0);
    const chips = [
      { label: "Teams", value: state.teams.length, cls: "" },
      { label: "Challenges", value: state.challenges.length, cls: "" },
      { label: "Top score", value: fmt(top.score), cls: "accent" },
      { label: "Total solves", value: fmt(solved), cls: "green" },
      { label: "Leader", value: top.name, cls: "" }
    ];
    $("#stat-chips").innerHTML = chips
      .map(c => '<div class="chip ' + c.cls + '"><b>' + c.value + "</b><span>" + c.label + "</span></div>")
      .join("");

    $("#legend").innerHTML =
      '<div class="legend-title">Top standings</div>' +
      state.teams.slice(0, 3)
        .map(t =>
          '<div class="legend-item"><span class="dot" style="background:' + t.color + ';color:' + t.color + '"></span>' +
          "&nbsp;" + t.flag + " " + esc(t.name) +
          "<b>" + t.rank + " · " + fmt(t.score) + "</b></div>"
        )
        .join("");
  }

  /* ───────────── leaderboard ───────────── */
  function renderLeaderboard() {
    const q = state.query.trim().toLowerCase();
    const list = state.teams.filter(t =>
      !q ||
      t.name.toLowerCase().includes(q) ||
      t.tagline.toLowerCase().includes(q) ||
      t.cc.toLowerCase().includes(q) ||
      t.flag.includes(q)
    );
    $("#lb-sub").textContent = list.length + " of " + state.teams.length + " teams";
    $("#search-clear").classList.toggle("show", state.query.length > 0);

    const body = $("#lb-body");
    if (!list.length) {
      body.innerHTML = '<div class="empty">No teams match your search.</div>';
      return;
    }
    body.innerHTML = "";
    const medals = ["🥇", "🥈", "🥉"];
    list.forEach(t => {
      const row = el("div", "lb-row" + (t.rank <= 3 ? " m" + t.rank : "") + (t.id === state.selectedId ? " sel" : ""));
      const ini = t.name.replace(/[^A-Za-z0-9]/g, "").slice(0, 3).toUpperCase();
      row.innerHTML =
        '<div class="lb-rank">' + (t.rank <= 3 ? medals[t.rank - 1] : t.rank) + "</div>" +
        '<div class="lb-ava" style="background:' + t.color + '">' + ini + "</div>" +
        '<div class="lb-meta"><div class="lb-name">' + t.flag + " " + esc(t.name) + "</div>" +
        '<div class="lb-tag">' + esc(t.tagline) + "</div></div>" +
        '<div class="lb-score"><b>' + fmt(t.score) + "</b>" +
        '<span class="delta ' + (t.delta > 0 ? "up" : "flat") + '">' +
        (t.delta > 0 ? "▲ +" + fmt(t.delta) : "—") + "</span></div>";
      row.addEventListener("click", () => openModal(t.id));
      body.appendChild(row);
    });
  }

  /* ───────────── challenges —───────────── */
  function renderChallenges() {
    const wrap = $("#chal-body");
    const panel = $("#challenges");
    wrap.innerHTML = "";

    state.cats.forEach(cat => {
      const chals = state.challenges.filter(c => c.cat === cat.id);
      const block = el("div", "cat-block");
      block.innerHTML =
        '<div class="cat-head"><span class="cat-dot" style="background:' + cat.color + '"></span>' +
        cat.icon + " " + cat.name +
        '<span class="cat-count">' + chals.length + " challenges</span></div>";
      const chips = el("div", "chal-chips");
      chals.forEach(c => {
        const solvers = c.solved.length;
        const solvedByLeader = c.solved.includes(state.teams[0].id);
        const chip = el("span", "chal-chip" + (solvedByLeader ? " solved" : ""));
        chip.style.color = cat.color;
        chip.title = c.title + " · " + solvers + " solver(s) · first blood: " +
          (c.firstBlood ? state.teams.find(t => t.id === c.firstBlood).name : "nobody yet");
        chip.innerHTML = c.catIcon + " " + esc(c.title) + ' <span class="pts">' + fmt(c.pts) + "</span>";
        chip.addEventListener("click", () => {
          const solver = state.teams.find(t => c.solved.includes(t.id));
          if (solver) openModal(solver.id);
        });
        chips.appendChild(chip);
      });
      block.appendChild(chips);
      wrap.appendChild(block);
    });

    $("#chal-count").textContent = state.challenges.length + " live";
    panel.querySelector(".panel-head").addEventListener("click", () => panel.classList.toggle("open"));
  }

  /* ───────────── team modal ───────────── */
  function openModal(id) {
    state.selectedId = id;
    if (SceneManager.selectedId !== id) SceneManager.setSelected(id);
    renderLeaderboard();

    const t = state.teams.find(x => x.id === id);
    if (!t) return;
    const mbody = $("#modal-body");
    const ini = t.name.replace(/[^A-Za-z0-9]/g, "").slice(0, 3).toUpperCase();
    const catBars = state.cats.map(c => ({ label: c.icon, value: t.byCat[c.id] || 0, color: c.color }));

    mbody.innerHTML =
      '<div class="m-head">' +
      '<div class="m-ava" style="background:' + t.color + ';box-shadow:0 0 26px ' + t.color + '">' + ini + "</div>" +
      '<div class="m-title"><h2>' + t.flag + " " + esc(t.name) + "</h2>" +
      '<div class="m-tag">' + esc(t.tagline) + " · " + t.cc + "</div>" +
      '<div class="m-badges">' +
      '<span class="m-badge flag">#' + t.rank + " place</span>" +
      '<span class="m-badge">' + fmt(t.score) + " pts</span>" +
      '<span class="m-badge">' + t.solvedCount + " solves</span>" +
      '<span class="m-badge ' + (t.delta > 0 ? "pos" : "") + '">' +
      (t.delta > 0 ? "▲ +" + fmt(t.delta) : "steady") + " (30m)</span>" +
      "</div></div></div>" +
      '<div class="m-grid">' +
      '<div class="m-card"><h3>Score progression</h3><canvas id="m-line"></canvas></div>' +
      '<div class="m-card"><h3>Points by category</h3><canvas id="m-bars"></canvas></div>' +
      "</div>" +
      '<div class="m-safe"><h3 class="m-subtitle">Solved challenges</h3>' +
      '<div class="m-solved-list">' +
      (t.challenges.length
        ? t.challenges.map(c =>
            '<span class="solved-chip" title="' + esc(c.title) + '">' + c.catIcon + " " +
            esc(c.title) + ' <span class="spts">' + fmt(c.pts) + "</span></span>"
          ).join("")
        : '<span class="empty" style="padding:6px 0">No solves yet — the night is young.</span>') +
      "</div></div>" +
      '<button class="btn btn-primary m-jump">🎯 Jump to tower in 3D</button>';

    requestAnimationFrame(() => {
      Charts.lineChart($("#m-line"), t.history, { color: t.color });
      Charts.barChart($("#m-bars"), catBars);
    });

    mbody.querySelector(".m-jump").addEventListener("click", () => {
      closeModal();
      SceneManager.selectById(id);
    });

    $("#modal-backdrop").classList.remove("hidden");
    $("#modal-close").onclick = closeModal;
    $("#modal-backdrop").onclick = e => { if (e.target === $("#modal-backdrop")) closeModal(); };
  }

  function closeModal() {
    $("#modal-backdrop").classList.add("hidden");
    state.selectedId = null;
    SceneManager.setSelected(null);
    renderLeaderboard();
  }

  /* ───────────── live simulation ───────────── */
  function liveTick() {
    const n = 1 + Math.floor(Math.random() * 2);
    for (let i = 0; i < n; i++) {
      const idx = Math.floor(Math.random() * state.teams.length);
      const t = state.teams[idx];
      if (Math.random() < 0.55 && t.rank > state.teams.length * 0.4) continue;
      const bump = Math.round(25 + Math.random() * 120);
      t.score += bump;
      t.delta += bump;
      t.history.push(t.score);
      if (t.history.length > 60) t.history.shift();
    }
    state.teams.sort((a, b) => b.score - a.score);
    state.teams.forEach((t, i) => (t.rank = i + 1));

    renderLeaderboard();
    renderStats();
    SceneManager.updateScores(state.teams);
  }

  /* ───────────── report / preview ───────────── */
  function buildReport() {
    return Report.generate(DATA);
  }

  function downloadReport() {
    try {
      Report.download(DATA, "ctf-scoreboard-report-" + new Date().toISOString().slice(0, 10) + ".html");
      toast("Report downloaded as HTML 📄");
    } catch (err) {
      toast("Download failed — open the preview instead.");
    }
  }

  function openReportPreview() {
    const frame = $("#report-frame");
    const src = buildReport();
    try {
      frame.srcdoc = src;
    } catch (e) {
      const blob = new Blob([src], { type: "text/html" });
      frame.src = URL.createObjectURL(blob);
    }
    $("#report-backdrop").classList.remove("hidden");
    $("#report-download").onclick = downloadReport;
    $("#report-preview").onclick = () => {
      const w = window.open("", "_blank");
      if (w) { w.document.write(src); w.document.close(); }
      else toast("Popup blocked — allow popups to open the report.");
    };
    $("#report-close").onclick = () => $("#report-backdrop").classList.add("hidden");
    $("#report-backdrop").onclick = e => {
      if (e.target === $("#report-backdrop")) $("#report-backdrop").classList.add("hidden");
    };
  }

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.remove("hidden");
    clearTimeout(t._h);
    t._h = setTimeout(() => t.classList.add("hidden"), 2600);
  }

  /* ───────────── wiring ───────────── */
  function init() {
    initScene();
    renderStats();
    renderLeaderboard();
    renderChallenges();

    $("#search").addEventListener("input", e => {
      state.query = e.target.value;
      renderLeaderboard();
    });
    $("#search-clear").addEventListener("click", () => {
      state.query = "";
      $("#search").value = "";
      renderLeaderboard();
    });

    $("#btn-download").addEventListener("click", downloadReport);
    $("#btn-preview").addEventListener("click", openReportPreview);

    setInterval(liveTick, 4000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();