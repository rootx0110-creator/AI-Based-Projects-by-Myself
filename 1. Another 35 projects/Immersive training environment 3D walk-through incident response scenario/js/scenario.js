/* ============================================================
 * scenario.js  —  runbook, decision prompts, fire model, scoring
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};

  /* ---------------- runbook definition ---------------- */
  const OBJ = [
    { key: 'don_ppe',        label: 'Don Protective Kit',        verb: 'Don the full PPE rack in the lobby' },
    { key: 'verify_alarm',   label: 'Verify Fire Alarm',         verb: 'Check the alarm panel — Zone 03 UPS-EAST' },
    { key: 'raise_alarm',    label: 'Raise Alarm',               verb: 'Pull the manual call-point' },
    { key: 'assess_fire',    label: 'Assess the Blaze',          verb: 'Approach the UPS bay fire and assess it' },
    { key: 'isolate_fuel',   label: 'Isolate Fuel',              verb: 'Close the diesel back-feed valve' },
    { key: 'electrical_iso', label: 'Electrical Isolation',      verb: 'Hit E-Stop & cut power to UPS-EAST' },
    { key: 'extinguish',     label: 'Extinguish Fire',           verb: 'Engage suppression with the right agent' },
    { key: 'evacuate',       label: 'Evacuate',                  verb: 'Use the fire exit to the muster point' },
    { key: 'incident_report',label: 'Incident Report',           verb: 'Finalize the digital incident report' }
  ];

  const DECISIONS = {
    assess_action: {
      id: 'd1', key: 'assess_fire', title: 'FIRE CONFIRMED · UPS-EAST',
      body: 'The blaze is growing on the energized UPS rack. What is your first move?',
      options: [
        { id: 'd1_immediate', label: 'Suppress immediately', verdict: 'IMPULSIVE' },
        { id: 'd1_isolate',   label: 'Isolate fuel & power first', correct: true, verdict: 'TEXTBOOK' },
        { id: 'd1_wait',      label: 'Withdraw & wait for team', verdict: 'PASSIVE' }
      ]
    },
    suppressant: {
      id: 'd2', key: 'extinguish', title: 'SELECT SUPPRESSION AGENT',
      body: 'Which agent do you deploy on the energized rack fire?',
      options: [
        { id: 'd2_co2',    label: 'CO₂ Gas (electrically safe)', correct: true, verdict: 'CORRECT' },
        { id: 'd2_powder', label: 'Dry powder', soft: true, verdict: 'ACCEPTABLE' },
        { id: 'd2_foam',   label: 'Foam', verdict: 'WRONG' },
        { id: 'd2_water',  label: 'Water', verdict: 'WRONG' }
      ]
    },
    coworker_action: {
      id: 'd3', key: 'coworker', title: 'COWORKER DOWN',
      body: 'A coworker is injured in the ops annex as smoke spreads. You are the last responder.',
      options: [
        { id: 'd3_alone', label: 'Evacuate alone', verdict: 'MISSED' },
        { id: 'd3_signal', label: 'Signal alarm & full evacuation, stay with them', correct: true, verdict: 'CORRECT' },
        { id: 'd3_drag',   label: 'Drag them out through the smoke', verdict: 'RISKY' }
      ]
    }
  };

  const TIME_TARGET = 260;
  const ALARM_WINDOW = 45;

  const Scenario = {
    phase: 'IDLE', run: null, clock: 0,
    activeIndex: 0,
    fireRadius: 1.6, fireGrown: false, smokeLevel: 0,
    contained: false, extinguishT: 0,
    smokeTimer: 0, escalateTimer: 0,

    init() {
      this.phase = 'IDLE';
      this.run = null;
    },

    newRun() {
      const id = 'RUN-' + String(Math.floor(Math.random() * 9000 + 1000));
      this.run = {
        runId: id, phase: 'INTRO', elapsedSec: 0,
        player: { health: 100, ppeOn: false },
        objectives: {
          order: OBJ.map(o => o.key),
          status: Object.fromEntries(OBJ.map((o, i) => [o.key, i === 0 ? 'active' : 'locked']))
        },
        decisions: [],
        hazards: { fire: { stage: 'active', radius: 1.6 }, smoke: false },
        subsystems: { fuelIsolated: false, powerCut: false, evacSignal: false, alarmRaised: false },
        events: [],
        ticker: { alarmAtSec: null, injuries: 0, containedSec: null, evacTimeSec: null }
      };
      this.clock = 0;
      this.fireRadius = 1.6;
      this.smokeLevel = 0;
      this.contained = false;
      A.engine.spawnFire();
      A.sfx.startFire();
      return this.run;
    },

    activeKey() {
      if (!this.run) return null;
      const st = this.run.objectives.status;
      for (const k of this.run.objectives.order) {
        if (st[k] === 'active') return k;
      }
      return 'done';
    },

    isAvailable(hotspotId) {
      if (!this.run || this.phase !== 'RUNNING') return false;
      const map = {
        don_ppe: 'don_ppe', panel: 'verify_alarm', pull: 'raise_alarm',
        fire: 'assess_fire', valve: 'isolate_fuel', estop: 'electrical_iso',
        ext: 'extinguish', coworker: 'coworker', exit: 'evacuate'
      };
      const key = map[hotspotId];
      if (!key) return false;
      const st = this.run.objectives.status;
      if (key === 'fire') return st.assess_fire === 'active';
      if (key === 'ext')  return st.extinguish === 'active' && st.assess_fire === 'done';
      if (key === 'exit') return st.extinguish === 'done';
      if (key === 'coworker') return st.raise_alarm === 'done' && st.coworker !== 'done' &&
                               st.extinguish !== 'done';
      return st[key] === 'active';
    },

    interact(hid, hdef) {
      if (!this.isAvailable(hid)) return;
      switch (hid) {
        case 'don_ppe': this.donePPE(hdef); break;
        case 'panel': this.verifyAlarm(hdef); break;
        case 'pull': this.raiseAlarm(hdef); break;
        case 'fire': this.assessFire(hdef); break;
        case 'valve': this.isolateFuel(hdef); break;
        case 'estop': this.eStop(hdef); break;
        case 'ext': this.extinguishStart(); break;
        case 'coworker': this.coworkerBanner(); break;
        case 'exit': this.evacuate(); break;
      }
    },

    log(type, label, ok) {
      this.run.events.push({ t: this.clock, type, label, ok: ok !== false });
    },

    complete(key, label) {
      this.run.objectives.status[key] = 'done';
      this.log('objective', label, true);
      const i = OBJ.findIndex(o => o.key === key);
      if (i >= 0 && i + 1 < OBJ.length && OBJ[i + 1].key !== 'incident_report') {
        this.run.objectives.status[OBJ[i + 1].key] = 'active';
      }
      A.sfx.chime(true);
      A.ui.toast('✓  ' + label, 'good');
      return true;
    },

    donePPE() {
      if (!this.complete('don_ppe', 'Protective kit donned')) return;
      this.run.player.ppeOn = true;
      A.ui.setPpe(true);
    },

    verifyAlarm() {
      this.complete('verify_alarm', 'Alarm verified — Zone 03 UPS-EAST active');
    },

    raiseAlarm() {
      if (!this.complete('raise_alarm', 'Alarm raised across facility')) return;
      this.run.ticker.alarmAtSec = this.clock;
      this.run.subsystems.alarmRaised = true;
      this.run.subsystems.evacSignal = true;
      A.sfx.startAlarm();
      A.ui.toast('⚠  EVACUATION SIGNAL ACTIVE — use fire exit when cleared', 'warn');
    },

    assessFire() {
      this.complete('assess_fire', 'Blaze assessed — electrical fire on UPS rack');
      A.ui.showDecision(DECISIONS.assess_action, (choice) => {
        this.recordDecision(DECISIONS.assess_action, choice);
        if (choice.correct) {
          A.ui.toast('Plan locked: isolate fuel & de-energize first', 'good');
        } else if (choice.id === 'd1_immediate') {
          this.escalate('Premature suppression without isolation effects');
          A.ui.toast('Pre-emptive suppression — fire flares, hazard expands', 'bad');
        } else {
          A.ui.toast('Passive wait — fire closes the window…', 'bad');
          this.run.hazards.fire.windowLost = true;
        }
      });
    },

    isolateFuel() {
      if (!this.complete('isolate_fuel', 'Diesel back-feed valve closed')) return;
      this.run.subsystems.fuelIsolated = true;
      this.log('subsystem', 'Fuel isolated', true);
    },

    eStop() {
      if (!this.complete('electrical_iso', 'E-Stop pressed · power cut to UPS-EAST')) return;
      this.run.subsystems.powerCut = true;
      A.sfx.flash();
      A.ui.toast('⚡ UPS-EAST DEPOWERED — safe to suppress', 'good');
    },

    extinguishStart() {
      const r = this.run;
      const d = DECISIONS.suppressant;
      A.ui.showDecision(d, (choice) => {
        this.recordDecision(d, choice);
        const agentOK = choice.correct || choice.soft;
        const prepped = r.subsystems.fuelIsolated && r.subsystems.powerCut;
        if (!agentOK) {
          this.escalate('Water/foam on live electrical — flashover!');
          this.run.player.health = Math.max(0, this.run.player.health - 28);
          r.ticker.injuries++;
          A.sfx.flash();
          A.ui.toast('⚡ FLASHOVER from wrong agent — 28 HP', 'bad');
          return;
        }
        if (!prepped) {
          A.ui.toast('Right agent — but isolate fuel & cut power FIRST', 'warn');
          return;
        }
        this.contained = true;
        r.ticker.containedSec = this.clock;
        r.hazards.fire.radius = 0;
        this.complete('extinguish', 'Fire suppressed · contain');
        A.sfx.stopFire();
        A.sfx.chime(true);
        window.setTimeout(() => A.engine.killFire(), 900);
        A.ui.toast('🔥 EXTINGUISHED — fire contained, smoke venting', 'good');
      });
    },

    coworkerBanner() {
      A.ui.showDecision(DECISIONS.coworker_action, (choice) => {
        this.recordDecision(DECISIONS.coworker_action, choice);
        if (choice.correct) {
          this.complete('coworker', 'Coworker handed over to evac team');
        } else if (choice.id === 'd3_drag') {
          this.complete('coworker', 'Coworker rescued — but smoke exposure');
          this.run.player.health = Math.max(0, this.run.player.health - 10);
          A.ui.toast('Risky rescue worked, but smoke exposure -10 HP', 'warn');
        } else {
          this.run.player.health = Math.max(0, this.run.player.health - 12);
          A.ui.toast('Coworker left behind — morale + liability penalty', 'bad');
          this.log('decision', 'Coworker abandoned', false);
        }
      });
    },

    recordDecision(d, choice) {
      this.run.decisions.push({ id: d.id, choice: choice.id, correct: !!choice.correct, soft: !!choice.soft, t: this.clock });
      this.log('decision', d.title + ' → ' + choice.label, !!choice.correct);
      if (choice.correct) A.sfx.chime(true); else A.sfx.chime(false);
    },

    escalate(msg) {
      this.fireGrown = true;
      this.run.hazards.fire.windowLost = true;
      this.fireRadius += 1.4;
      this.log('hazard', msg, false);
    },

    evacuate() {
      if (!this.complete('evacuate', 'Evacuated to muster point')) return;
      this.run.ticker.evacTimeSec = this.clock;
      A.sfx.stopAlarm();
      this.endRun('protected');
    },

    endRun(outcome) {
      if (this.phase === 'REPORT') return;
      this.phase = 'REPORT';
      this.run.phase = 'REPORT';
      this.run.outcome = outcome;
      if (outcome === 'protected') {
        this.run.objectives.status.incident_report = 'active';
        this.complete('incident_report', 'Incident report finalized');
      }
      const res = this.computeScore();
      A.ui.showReport(res);
    },

    /* ---------------- per-frame update ---------------- */
    tick(dt) {
      if (this.phase !== 'RUNNING' || !this.run) return;
      const r = this.run;
      this.clock += dt;
      r.elapsedSec = this.clock;

      // fire growth
      const alarmOk = r.ticker.alarmAtSec !== null && r.ticker.alarmAtSec <= ALARM_WINDOW;
      let growth = 0.011;
      if (!alarmOk) growth *= 1.35;
      if (!r.subsystems.fuelIsolated) growth *= 1.2;
      if (!r.subsystems.powerCut) growth *= 1.15;
      if (this.fireGrown) growth *= 1.5;

      if (!this.contained && this.fireRadius < 4.4) {
        this.fireRadius = Math.min(4.4, this.fireRadius + growth * dt);
      }
      r.hazards.fire.radius = this.fireRadius;

      // auto toasts + alarm nag
      if (!r.subsystems.alarmRaised && this.clock > 20 && this.clock - 20 < dt + 0.01) {
        A.ui.toast('⏱ Fire growing — raise the alarm quickly', 'warn');
      }
      if (!r.subsystems.alarmRaised && this.clock > ALARM_WINDOW && this.escalateTimer <= 0) {
        this.escalateTimer = 8;
        A.ui.toast(`⏰ Alarm not raised by ${ALARM_WINDOW}s — fire intensifying`, 'bad');
      }
      this.escalateTimer -= dt;

      // smoke level
      if (!this.contained) {
        const wantsSmoke = this.fireRadius > 2.3 || this.clock > 75;
        if (wantsSmoke) this.smokeLevel = Math.min(1, this.smokeLevel + dt * 0.007);
      } else {
        this.smokeLevel = Math.max(0, this.smokeLevel - dt * 0.02);
      }
      r.hazards.smoke = this.smokeLevel > 0.25;
      A.engine.setSmokeLevel(this.smokeLevel);

      // smoke puffs near fire
      this.smokeTimer -= dt;
      if (this.smokeLevel > 0.2 && !this.contained && this.smokeTimer <= 0) {
        this.smokeTimer = 0.5;
        A.engine.emitSmokePuff(7 + Math.random() * 3, -5 + Math.random() * 3);
      }

      // damage zones
      const pl = this.playerPos();
      const dx = pl.x - A.firePos.x, dz = pl.z - A.firePos.z;
      const fireDist = Math.sqrt(dx * dx + dz * dz);
      if (!this.contained && fireDist < this.fireRadius) {
        const base = r.player.ppeOn ? 2.5 : 8.5;
        const dmg = base * dt;
        r.player.health = Math.max(0, r.player.health - dmg);
        A.ui.flashDamage();
      }
      if (!r.player.ppeOn && this.smokeLevel > 0.4) {
        r.player.health = Math.max(0, r.player.health - 1.2 * dt);
      }
      if (r.player.health <= 0) {
        r.player.health = 0;
        A.ui.toast('☠ FATAL INJURY — advance must halt', 'bad');
        A.engine.killFire();
        this.endRun('failed');
        return;
      }
    },

    playerPos() { return { x: A.player.x, z: A.player.z }; },

    /* ---------------- scoring ---------------- */
    computeScore() {
      const r = this.run;
      const t = this.clock;

      // SAFETY
      let safety = 100;
      if (!r.player.ppeOn) safety -= 25;
      safety -= r.ticker.injuries * 18;
      const hpLost = 100 - r.player.health;
      safety -= hpLost * 0.55;
      safety = this.clamp(safety);

      // SPEED
      const speed = this.clamp(100 * (1 - Math.max(0, t - 120) / (TIME_TARGET - 90)));

      // ACCURACY
      let decided = 0, accPoints = 0;
      for (const d of r.decisions) {
        decided++;
        if (d.correct) accPoints += 1;
        else if (d.soft) accPoints += 0.5;
      }
      const accuracy = decided ? this.clamp(accPoints / decided * 100) : 0;

      // COVERAGE
      let cov = 0;
      if (r.ticker.alarmAtSec !== null) cov += r.ticker.alarmAtSec <= ALARM_WINDOW ? 25 : 15;
      if (r.subsystems.fuelIsolated) cov += 25;
      if (r.subsystems.powerCut) cov += 25;
      if (r.objectives.status.evacuate === 'done') cov += 25;
      const coverage = this.clamp(cov);

      const score = Math.round(
        safety * 0.25 + speed * 0.2 + accuracy * 0.3 + coverage * 0.25
      );
      const grade = score >= 85 ? 'A' : score >= 70 ? 'B' : score >= 55 ? 'C' : score >= 40 ? 'D' : 'F';

      return {
        runId: r.runId,
        outcome: r.outcome || 'aborted',
        score, grade,
        pillars: { safety: Math.round(safety), speed: Math.round(speed), accuracy: Math.round(accuracy), coverage },
        timeSec: Math.round(t),
        checklist: { done: r.objectives.order.filter(k => r.objectives.status[k] === 'done').length, total: OBJ.length },
        decisions: { total: r.decisions.length, correct: r.decisions.filter(d => d.correct).length },
        incidents: { injuries: r.ticker.injuries, missedSteps: OBJ.length - r.objectives.order.filter(k => r.objectives.status[k] === 'done').length },
        ticks: this,
        run: r
      };
    },

    clamp(v) { return Math.max(0, Math.min(100, Math.round(v))); }
  };

  A.OBJ = OBJ;
  A.DECISIONS = DECISIONS;
  A.scenario = Scenario;
})();