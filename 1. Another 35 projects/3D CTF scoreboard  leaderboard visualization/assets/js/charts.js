/* ═══════════════════════════════════════════════════════════════════════
   CTF ARENA · lightweight canvas chart helpers (no dependencies)
   ═══════════════════════════════════════════════════════════════════════ */
(function (global) {
  "use strict";

  function fit(canvas) {
    const dpr = global.devicePixelRatio || 1;
    const w = canvas.clientWidth || canvas.parentNode.clientWidth;
    const h = canvas.clientHeight || 120;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  }

  function lineChart(canvas, series, opts) {
    opts = opts || {};
    const { ctx, w, h } = fit(canvas);
    ctx.clearRect(0, 0, w, h);
    if (!series || series.length === 0) return;

    const color = opts.color || "#22d3ee";
    const pad = { t: 8, r: 6, b: 8, l: 6 };
    const min = opts.min != null ? opts.min : Math.min(...series);
    const max = opts.max != null ? opts.max : Math.max(...series);
    const span = Math.max(max - min, 1);

    const x = i => pad.l + (i / (series.length - 1)) * (w - pad.l - pad.r);
    const y = v => pad.t + (1 - (v - min) / span) * (h - pad.t - pad.b);

    // baseline + fill
    ctx.beginPath();
    ctx.moveTo(x(0), y(series[0]));
    for (let i = 1; i < series.length; i++) ctx.lineTo(x(i), y(series[i]));
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, hexA(color, 0.28));
    grad.addColorStop(1, hexA(color, 0));
    ctx.lineTo(x(series.length - 1), h - pad.b);
    ctx.lineTo(x(0), h - pad.b);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // end point glow
    const lx = x(series.length - 1), ly = y(series[series.length - 1]);
    ctx.beginPath();
    ctx.arc(lx, ly, 3.2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function barChart(canvas, data, opts) {
    opts = opts || {};
    const { ctx, w, h } = fit(canvas);
    ctx.clearRect(0, 0, w, h);
    const items = data || [];
    if (items.length === 0) return;
    const pad = { t: 14, r: 4, b: 6, l: 4 };
    const barW = Math.min(22, (w - pad.l - pad.r - (items.length - 1) * 4) / items.length);
    const totalW = items.length * barW + (items.length - 1) * 4;
    const startX = pad.l + (w - pad.l - pad.r - totalW) / 2;
    const maxV = Math.max(...items.map(i => i.value), 1);

    items.forEach((it, i) => {
      const bx = startX + i * (barW + 4);
      const bh = Math.max(3, (it.value / maxV) * (h - pad.t - pad.b));
      const by = h - pad.b - bh;
      const col = it.color || opts.color || "#22d3ee";
      ctx.fillStyle = hexA(col, 0.85);
      roundRect(ctx, bx, by, barW, bh, 3);
      ctx.fill();
      // value label
      ctx.fillStyle = col;
      ctx.font = "600 9px 'JetBrains Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText(String(it.value), bx + barW / 2, by - 3);
      // axis label
      ctx.fillStyle = "rgba(142,163,196,0.9)";
      ctx.font = "600 9px 'Inter', sans-serif";
      ctx.fillText(it.label, bx + barW / 2, h - 1);
    });
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function hexA(hex, a) {
    const h = hex.replace("#", "");
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + a + ")";
  }

  global.Charts = { lineChart, barChart, hexA };
})(window);