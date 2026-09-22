/* ============================================================
 * report.js  —  HTML after-action report + trainee memory
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};

  const memoryKey = 'irtrn.memory';
  const memoryDefault = () => ({
    schemaVersion: 1,
    trainee: {
      name: 'First Responder', callsign: 'RESPONDER-01', branch: 'Site Defense',
      seal: 0,
      skillProfile: { safety: 0, speed: 0, accuracy: 0, coverage: 0 }
    },
    attempts: [],
    metrics: { attemptsTotal: 0, attemptsCompleted: 0, bestScore: 0, bestTimeSec: 0, avgScore: 0 }
  });

  const Memory = {
    load() {
      try {
        const raw = localStorage.getItem(memoryKey);
        if (!raw) return memoryDefault();
        const m = JSON.parse(raw);
        return Object.assign(memoryDefault(), m);
      } catch (e) { return memoryDefault(); }
    },
    save(m) { try { localStorage.setItem(memoryKey, JSON.stringify(m)); } catch (e) {} },

    record(res) {
      const m = this.load();
      m.attempts.push({
        id: res.runId,
        completedAt: new Date().toISOString(),
        outcome: res.outcome,
        score: res.score,
        grade: res.grade,
        timeSec: res.timeSec,
        checklist: res.checklist,
        decisions: res.decisions,
        pillars: res.pillars,
        incidents: res.incidents
      });
      const done = res.outcome === 'protected' || res.outcome === 'contained';
      if (done) m.metrics.attemptsCompleted++;
      m.metrics.attemptsTotal = m.attempts.length;
      m.metrics.bestScore = Math.max(m.metrics.bestScore, res.score);
      if (done) m.metrics.bestTimeSec = m.metrics.bestTimeSec
        ? Math.min(m.metrics.bestTimeSec, res.timeSec) : res.timeSec;
      const scores = m.attempts.map(a => a.score);
      m.metrics.avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
      // rolling skill profile (last 5)
      const recent = m.attempts.slice(-5);
      for (const p of Object.keys(m.trainee.skillProfile)) {
        m.trainee.skillProfile[p] = Math.round(recent.reduce((s, a) => s + (a.pillars[p] || 0), 0) / recent.length);
      }
      // seal rank
      const good = m.attempts.filter(a => a.score >= 70).length;
      const total = m.attempts.length;
      m.trainee.seal = total >= 12 && good > total * 0.75 ? 4
        : total >= 8 && good * 2 >= total ? 3
        : total >= 4 && good * 2 >= total ? 2
        : total >= 1 ? 1 : 0;
      this.save(m);
      return m;
    }
  };

  const SEALS = ['NOVICE', 'RESPONDER', 'OPERATOR', 'COMMANDER', 'DIRECTOR'];

  /* ---------------- radar chart ---------------- */
  function drawRadar(canvas, pillars, max) {
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2, cy = canvas.height / 2 + 6, R = canvas.width / 2 - 26;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const keys = ['safety', 'speed', 'accuracy', 'coverage'];
    const labels = ['SAFETY', 'SPEED', 'ACCURACY', 'COVERAGE'];
    const n = keys.length;
    const ang = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;

    // rings
    for (let ring = 1; ring <= 4; ring++) {
      ctx.beginPath();
      for (let i = 0; i <= n; i++) {
        const a = ang(i % n);
        const r = R * ring / 4;
        const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.strokeStyle = 'rgba(90,160,255,0.18)'; ctx.lineWidth = 1; ctx.stroke();
    }
    for (let i = 0; i < n; i++) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(ang(i)) * R, cy + Math.sin(ang(i)) * R);
      ctx.strokeStyle = 'rgba(90,160,255,0.25)'; ctx.stroke();
    }
    // data polygon
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const a = ang(i % n);
      const v = (pillars[keys[i % n]] || 0) / (max || 100);
      const x = cx + Math.cos(a) * R * v, y = cy + Math.sin(a) * R * v;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(54,199,255,0.28)';
    ctx.fill();
    ctx.strokeStyle = '#36c7ff'; ctx.lineWidth = 2.4;
    ctx.shadowColor = '#36c7ff'; ctx.shadowBlur = 14;
    ctx.stroke();
    // labels + values
    ctx.shadowBlur = 0;
    ctx.font = '700 11px Orbitron, sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i < n; i++) {
      const a = ang(i);
      const lx = cx + Math.cos(a) * (R + 18), ly = cy + Math.sin(a) * (R + 18);
      ctx.fillStyle = '#8fa3c4'; ctx.fillText(labels[i], lx, ly);
      const vx = cx + Math.cos(a) * (R * ((pillars[keys[i]] || 0) / (max || 100)) - 12);
      const vy = cy + Math.sin(a) * (R * ((pillars[keys[i]] || 0) / (max || 100)) - 12);
      ctx.fillStyle = '#eaf3ff'; ctx.fillText(pillars[keys[i]] || 0, vx, vy);
    }
    ctx.font = '900 13px Orbitron';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('SKILL RADAR', cx, canvas.height - 6);
  }

  function radarDataURL(pillars) {
    const c = document.createElement('canvas'); c.width = 560; c.height = 560;
    drawRadar(c, pillars, 100);
    return c.toDataURL('image/png');
  }

  /* ---------------- report builder ---------------- */
  function fmtTime(sec) {
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return m + ':' + String(s).padStart(2, '0');
  }

  function badges(res) {
    const out = [];
    if (res.timeSec <= 200) out.push('⚡ FAST RESPONDER');
    if ((res.incidents || {}).injuries === 0) out.push('🛡 NO-HARM');
    const coop = res.run.decisions.some(d => d.id === 'd3' && d.choice === 'd3_signal');
    if (coop) out.push('🤝 CREW-CARE');
    if (res.grade === 'A') out.push('📖 BY-THE-BOOK');
    if (res.run.objectives.status.don_ppe === 'done') out.push('🎽 PPE-DISCIPLINED');
    if (!out.length) out.push('📋 COMPLETED');
    return out;
  }

  function buildReport(res) {
    const d = new Date();
    const pill = res.pillars;
    const done = res.checklist.done;
    const rows = A.OBJ.map(o => {
      const st = res.run.objectives.status[o.key];
      const icon = st === 'done' ? '✔' : st === 'active' ? '○' : '·';
      return `<tr><td>${icon}</td><td>${o.label}</td><td class="${st === 'done' ? 'ok' : 'dim'}">${st === 'done' ? 'COMPLETE' : st.toUpperCase()}</td></tr>`;
    }).join('');

    const decRows = res.run.decisions.map(dec => {
      const dMeta = Object.values(A.DECISIONS).find(x => x.id === dec.id);
      const title = dMeta ? dMeta.title : dec.id;
      const flag = dec.correct ? 'CORRECT' : dec.soft ? 'ACCEPTABLE' : 'WRONG';
      return `<tr><td>${title}</td><td>${dec.choice.toUpperCase()}</td><td class="${dec.correct ? 'ok' : 'bad'}">${flag}</td><td>${fmtTime(dec.t)}</td></tr>`;
    }).join('') || '<tr><td colspan="4" class="dim">No decision prompts completed.</td></tr>';

    const tRows = res.run.events.map(e => {
      const col = e.ok ? '#3df2c0' : '#ff5246';
      return `<tr><td>${fmtTime(e.t)}</td><td class="lbl">${e.label}</td><td style="color:${col}">${e.ok ? 'OK' : '—'}</td></tr>`;
    }).join('') || '<tr><td colspan="3" class="dim">Empty log.</td></tr>';

    const b = badges(res).map(x => `<span class="chip">${x}</span>`).join(' ');
    const radar = radarDataURL(pill);

    return `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>After-Action Report — ${res.runId}</title>
<style>
  :root { --cyan:#36c7ff; --green:#3df2c0; --red:#ff5246; --orange:#ffb23c; --ink:#0b0f18; --dim:#8fa3c4; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Segoe UI',Rajdhani,Arial,sans-serif; background:linear-gradient(160deg,#050810,#0d1526 60%,#070a12);
    color:#eaf3ff; padding:40px 24px; }
  .wrap { max-width: 900px; margin: 0 auto; background: rgba(13,20,34,0.85); border:1px solid rgba(90,160,255,0.28);
    border-top: 4px solid var(--cyan); border-radius: 14px; padding: 34px; box-shadow: 0 0 60px rgba(54,199,255,0.12); }
  .kicker { font-size:10px; letter-spacing:.4em; color:var(--cyan); text-transform:uppercase; margin-bottom:8px; }
  h1 { font-family:'Orbitron','Segoe UI',sans-serif; font-size:34px; letter-spacing:.06em; text-transform:uppercase; }
  .outcome { color: var(--green); } .outcome.fail { color: var(--red); }
  .meta { color:var(--dim); font-size:12px; letter-spacing:.14em; margin:8px 0 30px; }
  .grid { display:grid; grid-template-columns: auto 1fr; gap: 0 26px; align-items:center; margin-bottom: 30px; }
  .score { font-family:'Orbitron'; font-weight:900; font-size:84px; line-height:.9; color:#fff;
    text-shadow: 0 0 30px rgba(61,242,192,.6); }
  .score small { font-size:20px; color:var(--dim); }
  .grade { font-family:'Orbitron'; font-size:22px; letter-spacing:.2em; font-weight:900; }
  .pillars { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:30px; }
  .pillar { background:rgba(18,30,52,.9); border:1px solid rgba(90,160,255,.25); border-radius:10px; padding:12px; text-align:center; }
  .pillar b { display:block; font-family:'Orbitron'; font-size:26px; color:#fff; }
  .pillar span { font-size:10px; letter-spacing:.24em; color:var(--dim); }
  .badges { margin-bottom:30px; display:flex; flex-wrap:wrap; gap:8px; }
  .chip { background:rgba(61,242,192,.12); border:1px solid rgba(61,242,192,.5); color:var(--green);
    border-radius:20px; padding:4px 12px; font-size:11px; font-weight:700; letter-spacing:.08em; }
  table { width:100%; border-collapse:collapse; margin-bottom:26px; font-size:13px; }
  th { font-family:'Orbitron'; font-size:10px; letter-spacing:.24em; color:var(--dim); text-transform:uppercase;
    text-align:left; padding:6px 8px; border-bottom:1px solid rgba(90,160,255,.3); }
  td { padding:6px 8px; border-bottom:1px solid rgba(90,160,255,.12); color:#cfe2ff; }
  td.ok { color:var(--green); } td.bad { color:var(--red); } td.dim { color:var(--dim); }
  td.lbl { color:#e6eeff; }
  h2 { font-family:'Orbitron'; font-size:13px; letter-spacing:.3em; color:var(--cyan); margin:22px 0 10px; text-transform:uppercase; }
  .radar { text-align:center; margin: 6px 0 24px; }
  .radar img { width:260px; height:260px; }
  .foot { margin-top:26px; padding-top:14px; border-top:1px dashed rgba(90,160,255,.25);
    font-size:11px; letter-spacing:.15em; color:var(--dim); display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }
  @media print { body { background:#fff; color:#111; } .wrap { box-shadow:none; } }
  @media (max-width:640px){ .grid{ grid-template-columns:1fr; } .pillars{ grid-template-columns:repeat(2,1fr);} }
</style></head><body>
<div class="wrap">
  <div class="kicker">IMMERSIVE TRAINING ENVIRONMENT · AFTER-ACTION REPORT</div>
  <h1>DATA-CENTER FIRE <span class="outcome ${res.outcome === 'protected' ? '' : 'fail'}">· ${res.outcome.toUpperCase()}</span></h1>
  <div class="meta">${res.runId} &nbsp;·&nbsp; ${d.toLocaleString()} &nbsp;·&nbsp; ZONE 03 UPS-EAST &nbsp;·&nbsp; duration ${fmtTime(res.timeSec)}</div>

  <div class="grid">
    <div class="score">${res.score}<small>/100</small></div>
    <div>
      <div class="grade">GRADE ${res.grade}</div>
      <div class="meta" style="margin:4px 0 0">Checklist ${done}/${res.checklist.total} · Decisions ${res.decisions.correct}/${res.decisions.total} · Injuries ${res.incidents.injuries}</div>
    </div>
  </div>

  <div class="pillars">
    <div class="pillar"><b style="color:var(--green)">${pill.safety}</b><span>SAFETY 25%</span></div>
    <div class="pillar"><b style="color:var(--cyan)">${pill.speed}</b><span>SPEED 20%</span></div>
    <div class="pillar"><b style="color:var(--orange)">${pill.accuracy}</b><span>ACCURACY 30%</span></div>
    <div class="pillar"><b style="color:var(--red)">${pill.coverage}</b><span>COVERAGE 25%</span></div>
  </div>

  <div class="badges">${b}</div>

  <h2>SKILL RADAR</h2>
  <div class="radar"><img src="${radar}" alt="skill radar"></div>

  <h2>RUNBOOK CHECKLIST</h2>
  <table><tr><th></th><th>Objective</th><th>Status</th></tr>${rows}</table>

  <h2>DECISION LOG</h2>
  <table><tr><th>Decision</th><th>Choice</th><th>Verdict</th><th>Time</th></tr>${decRows}</table>

  <h2>EVENT TIMELINE</h2>
  <table><tr><th>Time</th><th>Event</th><th>Result</th></tr>${tRows}</table>

  <div class="foot">
    <span>IRT // SIM · v1.0 · generated locally on trainee device</span>
    <span>Sign-off: ______________________ &nbsp;Date: ${d.toLocaleDateString()}</span>
  </div>
</div>
</body></html>`;
  }

  /* ---------------- downloader ---------------- */
  const Report = {
    download(res) {
      const html = buildReport(res);
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      a.href = url;
      a.download = `IRT_Report_${res.runId}_${stamp}.html`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 800);
    }
  };

  /* ---------------- profile overlay ---------------- */
  const Profile = {
    show() {
      const m = Memory.load();
      const old = document.getElementById('profileOverlay');
      if (old) old.remove();
      const s = m.trainee.seal;
      const rows = [...m.attempts].reverse().map(a =>
        `<tr><td>${a.id}</td><td>${a.outcome}</td><td><b>${a.score}</b></td><td>${a.grade}</td>
         <td>${Math.floor(a.timeSec / 60)}:${String(a.timeSec % 60).padStart(2, '0')}</td>
         <td>${(a.pillars || {}).safety ?? '—'}</td>
         <td>${(a.pillars || {}).accuracy ?? '—'}</td></tr>`).join('') ||
        '<tr><td colspan="7" style="color:var(--dim)">No sessions yet.</td></tr>';

      const el = document.createElement('div');
      el.id = 'profileOverlay';
      el.style.cssText = 'position:fixed;inset:0;z-index:40;background:rgba(3,6,14,.92);' +
        'display:flex;align-items:center;justify-content:center;';
      el.innerHTML = `<div style='background:#0d1422;border:1px solid rgba(90,160,255,.3);border-radius:14px;' +
        'width:min(860px,92vw);max-height:90vh;overflow:auto;padding:28px'>
        <div style='font:700 11px Orbitron,monospace;letter-spacing:.4em;color:var(--cyan,#36c7ff)'>TRAINEE PROFILE</div>
        <div style='font:900 26px Orbitron,monospace;color:#fff;margin:6px 0 2px'>${m.trainee.callsign} · ${m.trainee.branch}</div>
        <div style='color:#8fa3c4;font-size:13px'>${SEALS[s]} SEAL &nbsp;|&nbsp; ${m.metrics.bestScore} PR &nbsp;|&nbsp; ${m.metrics.attemptsCompleted}/${m.metrics.attemptsTotal} completed &nbsp;|&nbsp; avg ${m.metrics.avgScore}</div>
        <canvas width='300' height='300' style='width:260px;height:260px;margin:14px 0' id='profRadar'></canvas>
        <table style='width:100%;border-collapse:collapse;font-size:13px;color:#cfe2ff'>
         <tr style='color:#8fa3c4;font-size:10px;letter-spacing:.2em;text-align:left'>
          <th>RUN</th><th>OUTCOME</th><th>SCORE</th><th>GRADE</th><th>TIME</th><th>SAFETY</th><th>ACC</th></tr>
         ${rows}</table>
        <div style='margin-top:18px;text-align:right'>
         <button style='font:700 12px Orbitron,monospace;background:#36c7ff;color:#03121f;border:0;border-radius:8px;padding:10px 18px;cursor:pointer' onclick='document.getElementById("profileOverlay").remove()'>CLOSE</button>
        </div></div>`;
      document.body.appendChild(el);
      // clear seed canvas line breaks
      const radar = el.querySelector('#profRadar');
      drawRadar(radar, m.trainee.skillProfile, 100);
    }
  };

  A.memory = Memory;
  A.report = Report;
  A.profile = Profile;
  A.seals = SEALS;
  A.drawRadar = drawRadar;
  A.buildReportHtml = buildReport;
  A.fmtTime = fmtTime;
})();