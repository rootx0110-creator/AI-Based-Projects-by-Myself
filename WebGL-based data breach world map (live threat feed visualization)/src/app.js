import { Globe } from './globe.js';
import { ThreatFeed, SEVERITIES, ATTACK_TYPES, CITIES } from './datafeed.js';
import { buildReportHTML, buildJSONLog } from './report.js';

const sevColor = (k) => SEVERITIES[k].color;

const globe = new Globe(document.getElementById('webgl-canvas'));
globe.start();

const feed = new ThreatFeed({ interval: 1900, history: 190 });
feed.start();

const state = {
  filterType: 'all',
  filterSev: 'all',
  search: '',
  paused: false
};

function setupFilters() {
  const typeSel = document.getElementById('filter-type');
  const sevSel = document.getElementById('filter-sev');
  for (const t of ATTACK_TYPES) {
    const o = document.createElement('option');
    o.value = t; o.textContent = t;
    typeSel.appendChild(o);
  }
  typeSel.addEventListener('change', () => { state.filterType = typeSel.value; renderFeed(); });
  sevSel.addEventListener('change', () => { state.filterSev = sevSel.value; renderFeed(); });
  document.getElementById('search-inp').addEventListener('input', (e) => {
    state.search = e.target.value.toLowerCase();
    renderFeed();
  });
  document.getElementById('pause-btn').addEventListener('click', () => {
    const p = feed.togglePaused();
    state.paused = p;
    document.getElementById('pause-btn').innerHTML = p ? '&#9654;' : '&#10074;&#10074;';
    document.getElementById('live-pill').style.opacity = p ? 0.5 : 1;
  });
}

const feedList = document.getElementById('feed-list');
const MAX_LIST = 80;

function fmtTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour12: false });
}

function feedItemHTML(e) {
  const sc = e.severity;
  return `<li data-id="${e.id}">
    <span class="sev sev-${sc}" style="box-shadow:0 0 8px ${sevColor(sc)}"></span>
    <div class="feed-main">
      <div class="ft" style="color:${sevColor(sc)}">${e.attack}</div>
      <div class="fd">${e.src.city} &#10142; ${e.dst.city}</div>
      <div class="fn">${e.company} &middot; ${e.industry}</div>
    </div>
    <span class="feed-time">${fmtTime(e.ts)}</span>
  </li>`;
}

function renderFeed() {
  const items = feed.getRecent(MAX_LIST * 2).filter(matchFilter);
  feedList.innerHTML = items.slice(0, MAX_LIST).map(feedItemHTML).join('');
}

function matchFilter(e) {
  if (state.filterType !== 'all' && e.attack !== state.filterType) return false;
  if (state.filterSev !== 'all' && e.severity !== state.filterSev) return false;
  if (state.search) {
    const hay = (e.attack + ' ' + e.src.city + ' ' + e.dst.city + ' ' + e.company + ' ' + e.industry + ' ' + e.ip).toLowerCase();
    if (!hay.includes(state.search)) return false;
  }
  return true;
}

const statEls = {
  events: document.getElementById('stat-events'),
  active: document.getElementById('stat-active'),
  countries: document.getElementById('stat-countries'),
  rate: document.getElementById('stat-rate'),
  records: document.getElementById('stat-records')
};

function computeStats() {
  const today = feed.todaysEvents();
  const now = Date.now();
  const active = today.filter(e => now - e.ts < 10 * 60000 && (e.severity === 'critical' || e.severity === 'high')).length;
  const countries = new Set(today.map(e => e.dst.cc)).size;
  const records = today.reduce((s, e) => s + e.records, 0);
  const recent = today.filter(e => now - e.ts < 5 * 60000).length;
  const rate = Math.round(recent / 5);
  return { total: today.length, active, countries, rate, records };
}

function renderStats() {
  const s = computeStats();
  statEls.events.textContent = s.total.toLocaleString();
  const activeEl = statEls.active;
  activeEl.textContent = s.active;
  activeEl.className = s.active > 12 ? 'heat-crit' : (s.active > 5 ? 'heat-high' : '');
  statEls.countries.textContent = s.countries;
  statEls.rate.textContent = s.rate;
  statEls.records.textContent = s.records > 1e6 ? (s.records / 1e6).toFixed(1) + 'M' : s.records.toLocaleString();
}

let labelMap = new Map();
let markerCount = 0;
const cityMarkerCount = new Map();

function ensureCityMarker(city) {
  const key = `${city.city}:${city.cc}`;
  const count = cityMarkerCount.get(key) || 0;
  if (count > 3) return null;
  cityMarkerCount.set(key, count + 1);
  const sprite = globe.addMarker(city.lat, city.lon, '#22d3ee', `city-${key}`);
  markerCount++;
  return sprite;
}

function handleEvent(e) {
  globe.addArc([e.src.lat, e.src.lon], [e.dst.lat, e.dst.lon], sevColor(e.severity), e.severity === 'critical' ? 1.5 : 1);
  globe.addMarker(e.dst.lat, e.dst.lon, sevColor(e.severity), e.id);

  if (e.severity === 'critical') {
    globe.addMarker(e.src.lat, e.src.lon, sevColor('critical'), `src-${e.id}`).scale.set(0.045, 0.045, 1);
  }

  if (e.severity === 'critical' && !labelMap.has(e.dst.cc)) {
    const lbl = globe.addLabel(e.dst.lat, e.dst.lon, e.dst.cc, '#ff3860');
    labelMap.set(e.dst.cc, lbl);
  }

  const li = document.createElement('li');
  li.innerHTML = feedItemHTML(e);
  li.style.animation = 'none';
  feedList.prepend(li);
  li.style.animation = '';
  while (feedList.children.length > MAX_LIST) feedList.removeChild(feedList.lastChild);

  if (!matchFilter(e)) li.style.display = 'none';
  renderStats();
}

let initDone = false;
function initialRender() {
  const today = feed.todaysEvents();
  for (const e of today) {
    ensureCityMarker(e.dst);
  }
  for (const cc of new Set(today.map(e => e.dst.cc))) {
    if (cc.length === 3) continue;
    const c = CITIES.find(c => c.cc === cc);
    if (!c) continue;
    globe.addLabel(c.lat, c.lon, cc, '#22d3ee');
  }
  renderFeed();
  renderStats();
  initDone = true;
}

function tickClock() {
  document.getElementById('utc-clock').textContent = new Date().toUTCString().slice(17, 25);
}
setInterval(tickClock, 1000);
tickClock();

const TOOLTIP = document.createElement('div');
TOOLTIP.id = 'tooltip';
document.body.appendChild(TOOLTIP);

function showTooltip(html, x, y) {
  TOOLTIP.innerHTML = html;
  TOOLTIP.style.opacity = 1;
  TOOLTIP.style.transform = 'translateY(0)';
  const pad = 14;
  const r = TOOLTIP.getBoundingClientRect();
  TOOLTIP.style.left = Math.min(x + pad, window.innerWidth - r.width - pad) + 'px';
  TOOLTIP.style.top = Math.min(y + pad, window.innerHeight - r.height - pad) + 'px';
}
function hideTooltip() {
  TOOLTIP.style.opacity = 0;
  TOOLTIP.style.transform = 'translateY(4px)';
}

feedList.addEventListener('mouseover', (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  const id = Number(li.dataset.id);
  const ev = feed.events.find(x => x.id === id);
  if (!ev) return;
  const sev = SEVERITIES[ev.severity];
  showTooltip(`
    <b style="color:${sev.color}">${ev.attack}</b><br />
    ${ev.src.city}, ${ev.src.cc} &#10142; ${ev.dst.city}, ${ev.dst.cc}<br />
    ${ev.company} (${ev.industry})<br />
    Records: ${ev.records.toLocaleString()} &middot; IP: ${ev.ip}<br />
    <span style="color:#8fa3c8">${fmtTime(ev.ts)}</span>
  `, e.clientX, e.clientY);
});
feedList.addEventListener('mouseleave', hideTooltip);
window.addEventListener('mousemove', (e) => {
  if (TOOLTIP.style.opacity === '1') {
    const pad = 14;
    const r = TOOLTIP.getBoundingClientRect();
    TOOLTIP.style.left = Math.min(e.clientX + pad, window.innerWidth - r.width - pad) + 'px';
    TOOLTIP.style.top = Math.min(e.clientY + pad, window.innerHeight - r.height - pad) + 'px';
  }
});

let toastTimer = null;
function toast(msg, ok = true) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = ok ? 'show ok' : 'show err';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = 'hidden'; }, 4200);
}

async function downloadReport() {
  if (!initDone) return;
  try {
    const today = feed.todaysEvents();
    const html = buildReportHTML(today, feed.events);
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const res = await window.breachmap.saveTextFile({
      defaultName: `BreachMap-Report-${stamp}.html`,
      content: html
    });
    if (res && !res.canceled) {
      toast(res.error ? `Save failed: ${res.error}` : `Report saved: ${res.path.split(/[\\/]/).pop()}`, !res.error);
    }
  } catch (err) {
    toast(`Could not save report (${err.message})`, false);
  }
}

async function downloadJSON() {
  if (!initDone) return;
  try {
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const res = await window.breachmap.saveTextFile({
      defaultName: `BreachMap-Log-${stamp}.json`,
      content: buildJSONLog(feed.events)
    });
    if (res && !res.canceled) {
      toast(res.error ? `Save failed: ${res.error}` : `JSON log saved: ${res.path.split(/[\\/]/).pop()}`, !res.error);
    }
  } catch (err) {
    toast(`Could not save JSON (${err.message})`, false);
  }
}

document.getElementById('btn-report').addEventListener('click', downloadReport);
document.getElementById('btn-json').addEventListener('click', downloadJSON);
document.getElementById('btn-reset').addEventListener('click', () => globe.resetView());

document.getElementById('chk-arcs').addEventListener('change', (e) => {
  globe.arcs.visible = e.target.checked;
});
document.getElementById('chk-labels').addEventListener('change', (e) => {
  globe.labels.visible = e.target.checked;
});

feed.on(handleEvent);
setupFilters();
initialRender();

window.addEventListener('beforeunload', () => {
  feed.stop();
  globe.dispose();
});