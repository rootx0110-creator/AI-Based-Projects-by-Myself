/* ============================================================
 * audio.js  —  procedural WebAudio SFX (no asset files)
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};

  const Sfx = {
    ctx: null,
    master: null,
    alarmNodes: null,
    fireNodes: null,
    steps: 0,

    unlock() {
      if (this.ctx) return;
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.5;
      this.master.connect(this.ctx.destination);
    },

    resume() { if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume(); },

    startAlarm() {
      if (!this.ctx || this.alarmNodes) return;
      const ctx = this.ctx, t = ctx.currentTime, d = ctx.duration || 0;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = 'square';
      osc.frequency.value = 880;
      g.gain.value = 0.0;
      osc.connect(g); g.connect(this.master);
      osc.start(t); osc.stop(t + 120);
      // two-tone beep
      const lfo = ctx.createLFO ? null : makeLFO2(ctx);
      if (lfo) { lfo.connect(osc.frequency); }
      this.alarmNodes = { osc, g, lfo };
      const on = () => {
        if (!Sfx.alarmNodes) return;
        g.gain.cancelScheduledValues(ctx.currentTime);
        g.gain.setValueAtTime(0, ctx.currentTime);
        g.gain.linearRampToValueAtTime(0.14, ctx.currentTime + 0.03);
        g.gain.linearRampToValueAtTime(0.0, ctx.currentTime + 0.42);
      };
      this.alarmTimer = setInterval(on, 560);
      on();
    },
    stopAlarm() {
      if (this.alarmTimer) clearInterval(this.alarmTimer);
      if (this.alarmNodes) {
        try { this.alarmNodes.osc.stop(); this.alarmNodes.g.disconnect(); } catch (e) {}
        this.alarmNodes.lfo && this.alarmNodes.lfo.disconnect();
        this.alarmNodes = null;
      }
    },

    startFire() {
      if (!this.ctx || this.fireNodes) return;
      const ctx = this.ctx;
      const len = ctx.sampleRate, buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
      const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
      const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 480;
      const g = ctx.createGain(); g.gain.value = 0.0;
      src.connect(f); f.connect(g); g.connect(this.master);
      src.start();
      this.fireNodes = { src, g, f };
      const on = () => {
        if (Sfx.fireNodes) {
          const v = 0.05 + Math.random() * 0.1;
          g.gain.setTargetAtTime(v, ctx.currentTime, 0.12);
          f.frequency.setTargetAtTime(300 + Math.random() * 500, ctx.currentTime, 0.2);
          src.playbackRate.setTargetAtTime(0.8 + Math.random() * 0.5, ctx.currentTime, 0.2);
        }
      };
      this.fireTimer = setInterval(on, 140);
      on();
    },
    stopFire() {
      if (this.fireTimer) clearInterval(this.fireTimer);
      if (this.fireNodes) {
        try { this.fireNodes.src.stop(); } catch (e) {}
        this.fireNodes = null;
      }
    },

    step(walk) {
      if (!this.ctx) return;
      const ctx = this.ctx, t = ctx.currentTime;
      const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * 0.08), ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) * 0.6;
      const src = ctx.createBufferSource(); src.buffer = buf;
      const f = ctx.createBiquadFilter(); f.type = 'lowpass';
      f.frequency.value = walk ? 420 : 1800;
      const g = ctx.createGain(); g.gain.value = walk ? 0.24 : 0.05;
      src.connect(f); f.connect(g); g.connect(this.master);
      src.start(t);
    },

    blip(freq, dur, vol) {
      if (!this.ctx) return;
      const ctx = this.ctx, t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = freq || 720;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol || 0.2, t + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, t + (dur || 0.18));
      o.connect(g); g.connect(this.master);
      o.start(t); o.stop(t + (dur || 0.2));
    },

    chime(correct) {
      if (!this.ctx) return;
      const seq = correct ? [660, 880, 1320] : [330, 220, 160];
      seq.forEach((fr, i) => setTimeout(() => Sfx.blip(fr, 0.16, 0.22), i * 90));
    },

    flash() {
      if (!this.ctx) return;
      const ctx = this.ctx, t = ctx.currentTime;
      for (let i = 0; i < 30; i++) {
        const o = ctx.createOscillator(); o.type = 'sawtooth';
        o.frequency.value = 200 + Math.random() * 3800;
        const g = ctx.createGain();
        g.gain.setValueAtTime(0.05, t + i * 0.012);
        g.gain.exponentialRampToValueAtTime(0.001, t + i * 0.012 + 0.05);
        o.connect(g); g.connect(this.master);
        o.start(t + i * 0.012); o.stop(t + i * 0.012 + 0.06);
      }
    }
  };

  function makeLFO2(ctx) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = 'square'; o.frequency.value = 1.8; g.gain.value = 430;
    o.connect(g); o.start(); return g;
  }

  A.sfx = Sfx;
})();