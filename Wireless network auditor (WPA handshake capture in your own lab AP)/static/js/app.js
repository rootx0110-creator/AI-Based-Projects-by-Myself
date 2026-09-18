/* Wireless Network Auditor - client helpers (offline, vanilla JS) */

async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return null;
}
const post = (url, body) => api(url, { method: "POST", body: JSON.stringify(body || {}) });
const get = (url) => api(url, { method: "GET" });

function toast(msg, type = "") {
  const wrap = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = msg;
  wrap.appendChild(el);
  setTimeout(() => { el.style.transition = "opacity .3s"; el.style.opacity = "0"; setTimeout(() => el.remove(), 320); }, 4200);
}
const toastOk = (m) => toast(m, "ok");
const toastErr = (m) => toast(m, "err");

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString();
}

function fmtDur(secs) {
  secs = Number(secs) || 0;
  if (secs >= 60) return (secs / 60).toFixed(1) + " min";
  return secs.toFixed(1) + " s";
}

function encBadge(enc) {
  const e = String(enc || "").toUpperCase();
  if (e.includes("WPA3")) return `<span class="badge b-g">WPA3</span>`;
  if (e.includes("WPA2")) return `<span class="badge b-b">WPA2</span>`;
  if (e.includes("WPA")) return `<span class="badge b-a">WPA</span>`;
  if (e.includes("WEP")) return `<span class="badge b-r">WEP</span>`;
  return `<span class="badge b-m">OPEN</span>`;
}

function sigBars(dbm) {
  dbm = Number(dbm) || -100;
  const bars = dbm >= -48 ? 4 : dbm >= -60 ? 3 : dbm >= -70 ? 2 : dbm >= -80 ? 1 : 0;
  let html = "";
  for (let i = 1; i <= 4; i++) {
    html += `<i class="${i <= bars ? "on" : ""}"></i>`;
  }
  return `<span class="sig">${html}</span> <span class="sub">${dbm} dBm</span>`;
}

function statusBadge(state) {
  const map = {
    IDLE: [ "idle", "Idle" ],
    LISTENING: [ "listening", "Listening" ],
    EAPOL_DETECTED: [ "detect", "EAPOL detected" ],
    HANDSHAKE_COMPLETE: [ "complete", "Handshake complete" ],
  };
  const [cls, txt] = map[state] || ["idle", state || "Idle"];
  return `<span class="chip ${cls}"><span class="dot"></span>${txt}</span>`;
}

/* Inline SVG icons (same set as templates/_icons.html) for use in JS markup. */
const SVG_ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  scanner: '<path d="M12 2 3 8l9 6 9-6z"/><path d="M3 15v1.5a9 9 0 0 0 18 0V15"/><path d="M7 14a5 5 0 0 0 10 0"/>',
  capture: '<path d="M12 2a10 10 0 0 0-10 10c0 4.4 2.8 8.2 6.8 9.6V9.4h-4V7h10v2.4h-4v12.2a10 10 0 0 0 8-8"/><path d="M2 12h2M20 12h2M12 2v2M12 20v2"/>',
  reports: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h5"/>',
  wifi: '<path d="M5 13a10 10 0 0 1 14 0"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M2 9.5a15 15 0 0 1 20 0"/><circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="2"/><path d="M12 6v1.5M12 16.5v1.5M6 12H4M20 12h-2"/>',
  hand: '<path d="M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z"/><path d="M9 15a3 3 0 0 0 6 0"/><path d="M9 16c1 2.5 5 2.5 6 0"/><path d="M9 10h.01M15 10h.01"/>',
  deauth: '<path d="M12 2 4 5v6c0 5 3.4 9.6 8 11 4.6-1.4 8-6 8-11V5z"/><path d="m9.5 12 5 5M14.5 12l-5 5"/>',
  shield: '<path d="M12 2 4 5v6c0 5 3.4 9.6 8 11 4.6-1.4 8-6 8-11V5z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  trash: '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13"/><path d="M10 11v6M14 11v6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  signal: '<path d="M5 12h2M9.5 8.5 11 7"/><path d="M7.4 20a9 9 0 1 1 9.2 0"/>',
  activity: '<path d="M3 12h4l2.5-7 4 14 2.5-7h5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
  play: '<path d="M7 4.5v15l13-7.5z"/>',
  bolt: '<path d="M13 2 4 14h6l-1 8 9-12h-6z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M12 12v4"/>',
  warn: '<path d="M12 3 2 20h20z"/><path d="M12 9v5M12 17h.01"/>',
};
function icon(name, size = 18) {
  const body = SVG_ICONS[name] || '<circle cx="12" cy="12" r="9"/>';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}

/* Surface unexpected JS errors instead of silently freezing the UI. */
window.addEventListener("error", (e) => {
  try { toastErr("<b>Script error.</b> " + esc(e.message)); } catch (err) {}
});

function copyText(txt) {
  const ta = document.createElement("textarea");
  ta.value = txt;
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); } catch (e) {}
  ta.remove();
}

/* sidebar + system poll */
document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.getElementById("menuBtn");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("backdrop");
  if (menuBtn && sidebar && backdrop) {
    menuBtn.addEventListener("click", () => { sidebar.classList.add("open"); backdrop.classList.add("show"); });
    backdrop.addEventListener("click", () => { sidebar.classList.remove("open"); backdrop.classList.remove("show"); });
  }
  pollSystem();
});

async function pollSystem() {
  try {
    const s = await get("/api/system");
    const chip = document.getElementById("sysState");
    const txt = document.getElementById("sysStateTxt");
    const adapter = document.getElementById("adapterChip");
    const dot = chip ? chip.querySelector(".dot") : null;
    if (s.capture_active) {
      txt.textContent = "Capturing";
      if (dot) dot.style.background = "var(--warn)";
      chip.classList.add("detect");
    } else {
      txt.textContent = "Ready";
      if (dot) dot.style.background = "var(--acc-2)";
      chip.classList.remove("detect");
    }
    if (!s.adapter_ok && s.engine !== "simulation") {
      txt.textContent = "Adapter down";
      if (dot) dot.style.background = "var(--danger)";
      toastErr("<b>Adapter unavailable.</b> Live capture requires a monitor-mode interface.");
    }
    if (adapter && s.adapter) {
      adapter.style.display = "";
      adapter.innerHTML = `<span class="dot" style="background:${s.adapter_ok ? "var(--acc-2)" : "var(--danger)"}"></span>${esc(s.adapter)}`;
      if (s.engine !== "simulation" && !s.npcap) {
        adapter.innerHTML += `<span class="dot" style="background:var(--danger)"></span>no-npcap`;
      }
    }
  } catch (e) {}
  setTimeout(pollSystem, 4000);
}