/* ============================================================
 * main.js  —  composition root: UI glue, input, HUD, loop
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};

  const $ = (sel) => document.querySelector(sel);

  const UI = {
    init() {
      this.el = {
        hud: $('#hud'),
        chipCount: $('#chipCount'), objActive: $('#objActive'), objVerb: $('#objVerb'), objNext: $('#objNext'),
        clock: $('#clockDisplay'), alarmLine: $('#alarmLine'), scoreLive: $('#scoreLive'),
        healthfill: $('#healthfill'), healthline: $('#healthline'),
        bFire: $('#bFire'), bSmoke: $('#bSmoke'), bPpe: $('#bPpe'), bPower: $('#bPower'),
        prompt: $('#prompt'), promptText: $('#promptText'), toastZone: $('#toastZone'),
        screenMenu: $('#screen-menu'), screenBrief: $('#screen-brief'),
        screenDecision: $('#screen-decision'), screenReport: $('#screen-report'),
        btnStart: $('#btnStart'), btnHow: $('#btnHow'), btnProfile: $('#btnProfile'),
        btnBriefStart: $('#btnBriefStart'), countdown: $('#countdown'), briefList: $('#briefList'),
        decTitle: $('#decTitle'), decBody: $('#decBody'), decOptions: $('#decOptions'),
        repOutcome: $('#repOutcome'), repRunId: $('#repRunId'), repTime: $('#repTime'), repGrade: $('#repGrade'),
        repScore: $('#repScore'), sSafety: $('#sSafety'), sSpeed: $('#sSpeed'),
        sAccuracy: $('#sAccuracy'), sCoverage: $('#sCoverage'),
        sChecklist: $('#sChecklist'), sDecisions: $('#sDecisions'),
        radar: $('#radar'), btnDownload: $('#btnDownload'), btnRestart: $('#btnRestart'), repFoot: $('#repFoot'),
        mBestScore: $('#mBestScore .mval'), mRuns: $('#mRuns .mval'), mSeal: $('#mSeal .mval')
      };
      this._lastScoreT = 0;
      this._lastResult = null;
      this.bind();
    },

    bind() {
      const el = this.el;
      el.btnStart.addEventListener('click', () => { A.sfx.unlock(); this.startBrief(); });
      el.btnHow.addEventListener('click', () => this.howTo());
      el.btnProfile.addEventListener('click', () => A.profile.show());
      el.btnBriefStart.addEventListener('click', () => this.confirmBrief());
      el.btnDownload.addEventListener('click', () => { if (this._lastResult) A.report.download(this._lastResult); });
      el.btnRestart.addEventListener('click', () => this.toMenu());

      // canvas click → lock pointer
      A.engine.renderer.domElement.addEventListener('click', () => {
        if (A.scenario.phase === 'RUNNING') A.player.requestLock();
      });
    },

    /* --------------- menu helpers --------------- */
    howTo() {
      alert('HOW TO PLAY\n\n' +
        'MOVE ............ WASD\n' +
        'LOOK ............ mouse (click screen to capture)\n' +
        'INTERACT ........ E (near a glowing hotspot)\n' +
        'FLASHLIGHT ...... F\n' +
        'MINIMAP ......... M\n\n' +
        'Follow the runbook in the top-left. Don PPE first, verify and raise\nthe alarm, assess fires, isolate fuel, cut power, then extinguish and\nevacuate. Download your report from the results screen.');
    },

    updateMenu() {
      const m = A.memory.load();
      this.el.mBestScore.textContent = m.metrics.bestScore ? m.metrics.bestScore + '%' : '—';
      this.el.mRuns.textContent = m.metrics.attemptsTotal ? m.metrics.attemptsTotal : '—';
      this.el.mSeal.textContent = A.seals[m.trainee.seal];
    },

    show(el) {
      el.classList.remove('hidden');
    },
    hide(el) {
      el.classList.add('hidden');
    },

    toast(msg, kind) {
      const t = document.createElement('div');
      t.className = 'toast ' + (kind || 'good');
      t.textContent = msg;
      this.el.toastZone.appendChild(t);
      setTimeout(() => t.remove(), 3500);
    },

    setPpe(on) {
      const b = this.el.bPpe;
      b.classList.toggle('off', !on);
      this.setHealthLine();
    },

    setHealthLine() {
      const hp = A.scenario.run ? A.scenario.run.player : { health: 100, ppeOn: false };
      const ppe = hp.ppeOn ? 'PPE ON' : 'NO PPE';
      const color = hp.health > 55 ? '#3df2c0' : hp.health > 25 ? '#ffb23c' : '#ff5246';
      this.el.healthline.style.color = color;
      this.el.healthline.textContent = Math.round(hp.health) + ' HP · ' + ppe;
    },

    flashDamage() {
      const fx = $('#fx');
      fx.style.boxShadow = 'inset 0 0 120px rgba(255,40,20,0.7)';
      setTimeout(() => (fx.style.boxShadow = ''), 180);
    },

    setPower(on) {
      this.el.bPower.classList.toggle('off', !on);
      this.el.bPower.style.borderColor = on ? 'rgba(61,242,192,0.55)' : '';
      this.el.bPower.style.color = on ? '#3df2c0' : '';
    },

    /* --------------- briefing → run start --------------- */
    startBrief() {
      this.hide(this.el.screenMenu);
      this.el.briefList.innerHTML = A.OBJ.map((o, i) =>
        `<div class="bl-item"><span class="n">${i + 1}</span><span>${o.verb}</span></div>`).join('');
      this.show(this.el.screenBrief);
      this.el.countdown.textContent = ' …';
      clearInterval(this._cd);
    },

    confirmBrief() {
      if (this._cd) return;
      this.countdown = 3;
      this.el.countdown.textContent = '3';
      this._cd = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(this._cd); this._cd = null;
          this.goLive();
          return;
        }
        this.el.countdown.textContent = String(this.countdown);
      }, 1000);
    },

    // called from scenario when run starts (scenario.newRun) — no, we drive here:

    goLive() {
      A.sfx.resume();
      const run = A.scenario.newRun();
      this.hide(this.el.screenMenu);
      this.hide(this.el.screenBrief);
      this.hide(this.el.screenReport);
      this.hide(this.el.screenDecision);
      this.show(this.el.hud);
      this.el.chipCount.textContent = '0/' + A.OBJ.length;
      A.scenario.phase = 'RUNNING';
      run.phase = 'RUNNING';
      A.player.x = A.spawn.x; A.player.z = A.spawn.z;
      A.player.yaw = A.spawn.yaw; A.player.pitch = 0;
      const cam = A.engine.camera;
      cam.position.set(A.spawn.x, 1.62, A.spawn.z);
      cam.rotation.set(0, A.spawn.yaw, 0);
      A.player.requestLock();
      A.engine.getMinimapCtx();
      this.setHealthLine();
      this.el.bPpe.classList.add('off');
      this.setPower(false);
      clearInterval(this._cd);
      this.toast('Incident active — Zone 03 UPS-EAST', 'warn');
    },

    /* --------------- decision modal --------------- */
    showDecision(dec, onChoice) {
      this._decisionCb = onChoice;
      this.el.decTitle.textContent = dec.title;
      this.el.decBody.textContent = dec.body;
      this.el.decOptions.innerHTML = '';
      dec.options.forEach(opt => {
        const b = document.createElement('div');
        b.className = 'drop';
        b.innerHTML = `<b style="color:#fff">${opt.label}</b>`;
        b.addEventListener('click', () => {
          A.sfx.resume();
          this.hide(this.el.screenDecision);
          if (this._decisionCb) this._decisionCb(opt);
          if (A.scenario.phase === 'RUNNING') setTimeout(() => A.player.requestLock(), 400);
        });
        this.el.decOptions.appendChild(b);
      });
      this.show(this.el.screenDecision);
      if (document.pointerLockElement) document.exitPointerLock();
    },

    /* --------------- report screen --------------- */
    showReport(res) {
      this._lastResult = res;
      const failed = res.outcome === 'failed';
      this.el.repOutcome.textContent = failed ? 'INCIDENT ESCALATED' : 'INCIDENT CONTAINED';
      this.el.repOutcome.className = 'report-title' + (failed ? ' fail' : '');
      this.el.repRunId.textContent = res.runId + ' · ' + res.outcome.toUpperCase();
      this.el.repTime.textContent = A.fmtTime(res.timeSec);
      this.el.repGrade.textContent = 'GRADE ' + res.grade;
      this.el.repScore.textContent = res.score;
      this.el.sSafety.textContent = res.pillars.safety;
      this.el.sSpeed.textContent = res.pillars.speed;
      this.el.sAccuracy.textContent = res.pillars.accuracy;
      this.el.sCoverage.textContent = res.pillars.coverage;
      this.el.sChecklist.textContent = res.checklist.done + '/' + res.checklist.total;
      this.el.sDecisions.textContent = res.decisions.correct + '/' + res.decisions.total;
      this.el.repFoot.textContent = failed
        ? 'Training outcome: catastrophic. Review the timeline below and retry.'
        : 'Report generated locally · saved to your Downloads';

      A.drawRadar(this.el.radar, res.pillars, 100);
      this.hide(this.el.hud);
      this.show(this.el.screenReport);

      const m = A.memory.record(res);
      this.updateMenu();
      A.sfx.stopAlarm(); A.sfx.stopFire();
    },

    toMenu() {
      A.scenario.phase = 'IDLE';
      A.engine.killFire();
      A.sfx.stopAlarm(); A.sfx.stopFire();
      this.hide(this.el.screenReport);
      this.hide(this.el.hud);
      this.show(this.el.screenMenu);
      this.updateMenu();
    }
  };

  A.ui = UI;

  /* ----------------------------------------------------------
   * gameloop + HUD updates
   * ---------------------------------------------------------- */
  function onTick(dt, t) {
    A.engine.aim.yaw = A.player.yaw;
    A.engine.aim.pitch = A.player.pitch;
    A.player.update(dt);
    A.scenario.tick(dt);
    updateHud(dt, t);
    updateMinimapDot();
  }

  function updateHud(dt, t) {
    const S = A.scenario, r = S.run;
    if (!r) return;

    // clock
    const mm = Math.floor(S.clock / 60), ss = Math.floor(S.clock % 60);
    UI.el.clock.textContent = String(mm).padStart(2, '0') + ':' + String(ss).padStart(2, '0');

    // alarm line
    const alarmLine = UI.el.alarmLine;
    if (r.subsystems.alarmRaised) {
      alarmLine.textContent = 'alarm: RAISED @' + Math.round(r.ticker.alarmAtSec) + 's';
      alarmLine.style.color = '#3df2c0';
    } else if (S.clock > 45) {
      alarmLine.textContent = '⚠ alarm OVERDUE';
      alarmLine.style.color = '#ff5246';
    } else {
      alarmLine.textContent = 'alarm window: ' + Math.max(0, Math.round(45 - S.clock)) + 's';
      alarmLine.style.color = '#ffb23c';
    }

    // objective tracker
    const key = S.activeKey();
    const obj = A.OBJ.find(o => o.key === key);
    if (obj) {
      UI.el.objActive.textContent = obj.label;
      UI.el.objVerb.textContent = obj.verb;
      const nxt = A.OBJ[A.OBJ.indexOf(obj) + 1];
      UI.el.objNext.textContent = nxt ? 'Next → ' + nxt.label : key === 'incident_report' ? 'Near complete — finalize!' : '';
      UI.el.chipCount.textContent = r.objectives.order.filter(k => r.objectives.status[k] === 'done').length + '/' + A.OBJ.length;
    }

    // live score (throttled)
    if (t - UI._lastScoreT > 0.3) {
      UI._lastScoreT = t;
      const res = S.computeScore();
      UI.el.scoreLive.textContent = res.score;
    }

    // health
    const hp = r.player.health;
    UI.el.healthfill.style.width = hp + '%';
    UI.el.healthfill.style.background = hp > 55
      ? 'linear-gradient(90deg,#3df2c0,#2fd0a0)'
      : hp > 25 ? 'linear-gradient(90deg,#ffb23c,#ff8f3c)' : 'linear-gradient(90deg,#ff5246,#ff3d30)';
    UI.setHealthLine();

    // hazard badges
    UI.el.bFire.classList.toggle('off', S.contained || S.fireRadius < 0.1);
    UI.el.bSmoke.classList.toggle('off', !r.hazards.smoke);
    UI.setPower(r.subsystems.powerCut);
    UI.el.bPpe.classList.toggle('off', !r.player.ppeOn);

    // interaction prompt
    UI.el.prompt.classList.add('hidden');
    let nearest = null, bestD = 1e9;
    for (const h of A.HOTSPOTS) {
      if (!S.isAvailable(h.id)) continue;
      const d = A.player.distanceTo(h);
      if (d < h.radius && d < bestD) { bestD = d; nearest = h; }
    }
    if (nearest) {
      UI.el.promptText.textContent = nearest.label + '  ·  ' + nearest.sub;
      UI.el.prompt.classList.remove('hidden');
    }
  }

  function updateMinimapDot() {
    const ctx = A.engine.getMinimapCtx();
    if (!ctx) return;
    A.engine.drawMinimapStatic();
    const b = A.BUILD;
    const x = (A.player.x - b.xMin) / (b.xMax - b.xMin) * 200;
    const z = (A.player.z - b.zMin) / (b.zMax - b.zMin) * 200;
    const S = A.scenario;
    for (const h of A.HOTSPOTS) {
      if (!S.isAvailable(h.id)) continue;
      const hx = (h.x - b.xMin) / (b.xMax - b.xMin) * 200;
      const hz = (h.z - b.zMin) / (b.zMax - b.zMin) * 200;
      ctx.strokeStyle = 'rgba(255,200,80,0.8)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(hx, hz, 6 + Math.sin(performance.now() / 200) * 1.5, 0, Math.PI * 2);
      ctx.stroke();
    }
    // player
    ctx.fillStyle = '#36c7ff';
    ctx.shadowColor = '#36c7ff'; ctx.shadowBlur = 8;
    ctx.beginPath(); ctx.arc(x, z, 4.5, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    const yaw = A.player.yaw;
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.moveTo(x, z);
    ctx.lineTo(x + Math.sin(yaw) * 9, z + Math.cos(yaw) * 9);
    ctx.stroke();
  }

  /* ----------------------------------------------------------
   * boot
   * ---------------------------------------------------------- */
  function boot() {
    A.engine.init(document.getElementById('game'));
    A.engine.attachPlayer();
    A.player.init();
    A.sfx.unlock();
    A.scenario.init();
    A.ui.init();
    A.ui.updateMenu();

    // torch toggle
    document.addEventListener('keydown', (e) => {
      if (e.code === 'KeyF') A.engine.flashlight.intensity = A.engine.flashlight.intensity > 0 ? 0 : 40;
      if (e.code === 'KeyM') {
        const mm = $('#minimap');
        if (mm) mm.style.opacity = mm.style.opacity === '0' ? '1' : '0';
      }
      if (e.code === 'KeyR' && A.scenario.phase === 'RUNNING') {
        const obj = A.OBJ.find(o => o.key === A.scenario.activeKey());
        if (obj) A.ui.toast('NEXT: ' + obj.verb, 'warn');
      }
    });

    document.addEventListener('pointerlockchange', () => {
      if (!A.player.locked) A.player.keys = {};
      if (!A.player.locked && A.scenario.phase === 'RUNNING') {
        A.ui.toast('🎯 Click the viewport to recapture the mouse', 'good');
      }
    });

    A.engine.start(onTick);
  }

  document.addEventListener('DOMContentLoaded', boot);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* wire scenario->ui callbacks (before any run) */
  document.addEventListener('keydown', (e) => {
    if (e.code === 'KeyE') {
      if (A.scenario.phase !== 'RUNNING') return;
      let nearest = null, bestD = 1e9;
      for (const h of A.HOTSPOTS) {
        if (!A.scenario.isAvailable(h.id)) continue;
        const d = A.player.distanceTo(h);
        if (d < h.radius && d < bestD) { bestD = d; nearest = h; }
      }
      if (nearest) A.scenario.interact(nearest.id, nearest);
    }
  });
})();