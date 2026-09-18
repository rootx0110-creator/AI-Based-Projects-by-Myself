"use strict";

function lineChart(canvasId, labels, data, color = "#22d3ee") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  const W = rect.width;
  const H = rect.height;
  ctx.clearRect(0, 0, W, H);

  const pad = { l: 40, r: 16, t: 16, b: 28 };
  const max = Math.max(1, ...data);
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  // grid
  ctx.strokeStyle = "rgba(31,44,74,0.5)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#7d8db0";
  ctx.font = "11px Inter, sans-serif";
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (ch / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(W - pad.r, y);
    ctx.stroke();
    const val = Math.round(max - (max / 4) * i);
    ctx.fillText(String(val), 6, y + 4);
  }

  if (!labels.length) {
    ctx.fillStyle = "#7d8db0";
    ctx.fillText("No data yet — ingest some feeds.", pad.l + 10, pad.t + ch / 2);
    return;
  }

  // points
  const pts = data.map((v, i) => {
    const x = labels.length === 1 ? pad.l + cw / 2 : pad.l + (cw / (labels.length - 1)) * i;
    const y = pad.t + ch - (v / max) * ch;
    return [x, y];
  });

  // area fill
  const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ch);
  grad.addColorStop(0, color + "55");
  grad.addColorStop(1, color + "05");
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pad.t + ch);
  pts.forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.lineTo(pts[pts.length - 1][0], pad.t + ch);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // line
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";
  ctx.stroke();

  // dots
  pts.forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  });

  // x labels
  ctx.fillStyle = "#7d8db0";
  ctx.font = "11px Inter, sans-serif";
  labels.forEach((lb, i) => {
    const [x] = pts[i];
    ctx.fillText(lb, x - 14, H - 8);
  });
}

window.lineChart = lineChart;