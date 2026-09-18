/* ===========================================================
   SIEM Correlator – Frontend App (vanilla JS, zero deps)
   =========================================================== */
const API  = { overview:'/api/overview', summary:'/api/summary', logs:'/api/logs',
                events:'/api/events', correlations:'/api/correlations',
                alerts:'/api/alerts', rules:'/api/rules',
                ingest:'/api/ingest', ingestFile:'/api/ingest/file',
                ingestJson:'/api/ingest/json',
                generate:'/api/generate', report:'/api/report',
                ack: id=>`/api/alerts/${id}/ack`,
                close:id=>`/api/alerts/${id}/close`,
                reset:'/api/reset', save:'/api/state/save' };

let pollTimer = null;
let currentView = 'dashboard';
const state = { data:{}, alertsFilter:'' };

/* ---- NAV ---- */
document.querySelectorAll('.nav-item').forEach(btn=>{
  btn.addEventListener('click', e=>{
    e.preventDefault();
    const view = btn.dataset.view;
    switchView(view);
  });
});
function switchView(v){
  currentView = v;
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active', n.dataset.view===v));
  document.querySelectorAll('.view').forEach(sec=>sec.classList.toggle('active', sec.id===`view-${v}`));
  document.getElementById('sidebar').classList.remove('open');
  refreshView();
}

/* ---- HAMBURGER ---- */
document.getElementById('hamburger').onclick = ()=> document.getElementById('sidebar').classList.toggle('open');

/* ---- FILE UPLOAD ---- */
document.getElementById('file-upload').addEventListener('change', async e=>{
  const file = e.target.files[0]; if(!file) return;
  const fd = new FormData(); fd.append('file', file);
  const res = await fetch(API.ingestFile, {method:'POST', body:fd});
  const j = await res.json();
  toast(`${j.normalized||0} events ingested`);
  e.target.value='';
  refreshView();
});

/* ---- JSON INGEST MODAL ---- */
const jsonModal = document.getElementById('json-modal');
document.getElementById('btn-ingest-json').onclick = ()=> jsonModal.showModal();
document.getElementById('json-cancel').onclick = ()=> jsonModal.close();
document.getElementById('json-submit').onclick = async ()=>{
  const raw = document.getElementById('json-input').value.trim();
  if(!raw){toast('Paste JSON first','warn');return}
  try{
    const obj = JSON.parse(raw);
    const res = await fetch(API.ingestJson,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});
    const j = await res.json();
    toast(`Ingested 1 event (${j.normalized||0} normalized)`);
    document.getElementById('json-input').value='';
    jsonModal.close();
    refreshView();
  }catch(e){toast('Invalid JSON','warn')}
};

/* ---- GENERATE ---- */
document.getElementById('btn-generate').onclick = async ()=>{
  const btn = document.getElementById('btn-generate');
  btn.textContent='Generating…'; btn.disabled=true;
  const res = await fetch(API.generate,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({seconds:90, density:1.8, seed: Math.floor(Math.random()*9999)})});
  const j = await res.json();
  toast(`Generated ${j.normalized} events from ${j.raw} raw lines`);
  btn.textContent='Generate Logs'; btn.disabled=false;
  refreshView();
};

/* ---- RESET ---- */
document.getElementById('btn-reset').onclick = async ()=>{
  if(!confirm('Clear all logs, events, correlations and alerts?'))return;
  await fetch(API.reset,{method:'POST'});
  toast('State reset'); refreshView();
};

/* ---- DOWNLOAD REPORT ---- */
document.getElementById('btn-report').onclick = ()=>{ window.open(API.report,'_blank'); };

/* ---- ALERT ACTIONS ---- */
document.addEventListener('click', e=>{
  const btn = e.target.closest('[data-action]');
  if(!btn) return;
  const {action, id} = btn.dataset;
  const url = action==='ack' ? API.ack(+id) : API.close(+id);
  fetch(url,{method:'POST'}).then(r=>r.json()).then(()=>{toast(`Alert #${id} ${action}`);refreshView()});
});

/* ---- ALERT FILTER ---- */
document.getElementById('alert-filter').addEventListener('change', e=>{
  state.alertsFilter = e.target.value; refreshView();
});

/* ---- POLLING ---- */
async function refreshView(){
  try{
    const res = await fetch(API.overview);
    state.data = await res.json();
    renderDashboard(state.data);
    renderLogs(state.data.logs);
    renderEvents(state.data.events);
    renderCorrelations(state.data.correlations);
    renderAlerts(state.data.alerts);
    renderRules(state.data.rules);
    updateBadge(state.data.stats?.open_alerts||0);
  }catch(e){console.error('poll error',e)}
}
setInterval(refreshView, 2500);
refreshView();

function updateBadge(n){
  const b=document.getElementById('alert-badge');
  if(n>0){b.style.display='';b.textContent=n}
  else b.style.display='none';
}

/* ==== DASHBOARD ==== */
function renderDashboard(d){
  const s=d.stats||{};
  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="v">${fmt(s.ingested_raw)}</div><div class="l">Raw Logs</div><div class="sub">ingested</div></div>
    <div class="kpi"><div class="v cyan">${fmt(s.normalized)}</div><div class="l">Events</div><div class="sub">normalized</div></div>
    <div class="kpi"><div class="v ${s.failed?'yellow':''}">${fmt(s.failed)}</div><div class="l">Parse Failures</div><div class="sub">dropped</div></div>
    <div class="kpi"><div class="v">${fmt(s.correlations)}</div><div class="l">Correlations</div><div class="sub">fire rate</div></div>
    <div class="kpi"><div class="v ${s.open_alerts?'red':''}">${fmt(s.open_alerts)}</div><div class="l">Open Alerts</div><div class="sub">${fmt(s.alerts)} total</div></div>
    <div class="kpi"><div class="v green">${fmt(s.ingest_rate||0)}</div><div class="l">Events/min</div><div class="sub">last 60s</div></div>
  `;
  renderTimeline(d.hourly||{});
  renderSeverity(d.severity_counts||{});
  renderBarsV('chart-top-src', d.top_sources||{});
  renderBarsV('chart-top-types', d.events_per_type||{});
  renderDashAlerts(d.alerts||[]);
}

function renderTimeline(hourly){
  const el=document.getElementById('chart-timeline');
  const entries=Object.entries(hourly);
  if(!entries.length){el.innerHTML='<div style="color:var(--text-mute);text-align:center;padding:30px">No timeline data yet</div>';return}
  const mx=Math.max(...entries.map(([,v])=>v),1);
  el.innerHTML=entries.slice(-16).map(([k,v])=>{
    const pct=Math.round(v/mx*100);
    const h=k[11]||'?';
    return `<div class="row"><span class="lbl">${h}h</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div><span class="count">${v}</span></div>`;
  }).join('');
}

function renderSeverity(counts){
  const el=document.getElementById('chart-severity');
  const leg=document.getElementById('sev-legend');
  const total=Object.values(counts).reduce((a,b)=>a+b,0)||1;
  const order=['info','low','medium','high','critical'];
  const colors={info:'var(--accent)',low:'var(--green)',medium:'var(--yellow)',high:'var(--orange)',critical:'var(--red)'};
  el.innerHTML=order.filter(s=>counts[s]).map(s=>{
    const w=counts[s]/total*100;
    return `<div style="flex:1;max-width:${w}%;min-width:4px;height:18px;background:${colors[s]};border-radius:4px;transition:width .4s"></div>`;
  }).join('');
  leg.innerHTML=order.filter(s=>counts[s]).map(s=>`<span style="color:${colors[s]}">● ${s}: ${counts[s]}</span>`).join('');
}

function renderBarsV(id, counter){
  const el=document.getElementById(id);
  const entries=Object.entries(counter).slice(0,8);
  if(!entries.length){el.innerHTML='<div style="color:var(--text-mute);padding:12px;text-align:center">No data</div>';return}
  const mx=Math.max(...entries.map(([,v])=>v),1);
  el.innerHTML=entries.map(([k,v])=>{
    const pct=Math.round(v/mx*100);
    return `<div class="bv-row"><span class="bv-lbl" title="${k}">${k}</span><div class="bv-track"><div class="bv-fill" style="width:${pct}%"></div></div><span class="bv-count">${v}</span></div>`;
  }).join('');
}

function renderDashAlerts(alerts){
  const tbody=document.querySelector('#tbl-dash-alerts tbody');
  const recent=alerts.filter(a=>a.status!=='closed').slice(0,10);
  if(!recent.length){tbody.innerHTML='<tr><td colspan="6" class="empty">No alerts yet — generate logs to start</td></tr>';return}
  tbody.innerHTML=recent.map(a=>`<tr>
    <td>#${a.id}</td><td>${a.title||''}</td>
    <td><span class="pill pill-${a.severity}">${a.severity}</span></td>
    <td>${a.risk||0}</td><td>${a.count||0}</td>
    <td><span class="pill pill-${a.status}">${a.status}</span></td>
  </tr>`).join('');
}

/* ==== LOGS ==== */
function renderLogs(logs){
  document.getElementById('log-count').textContent=`${logs.length} lines`;
  const el=document.getElementById('log-viewer');
  el.innerHTML=logs.slice(0,300).reverse().map(l=>{
    let html=escHtml(l.raw||'');
    html=html.replace(/(\d{1,3}(?:\.\d{1,3}){3})/g,'<span class="src-ip">$1</span>');
    if(/failed|error/i.test(html)) html=`<span class="sev-hi">${html}</span>`;
    else if(/warning|den[iy]/i.test(html)) html=`<span class="sev-md">${html}</span>`;
    return html;
  }).join('\n');
}

/* ==== EVENTS ==== */
function renderEvents(events){
  document.getElementById('event-count').textContent=`${events.length} events`;
  const tbody=document.querySelector('#tbl-events tbody');
  if(!events.length){tbody.innerHTML='<tr><td colspan="9" class="empty">No events yet</td></tr>';return}
  tbody.innerHTML=events.slice(0,400).map(e=>`<tr>
    <td>${e.ingest_id||''}</td>
    <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-mute)">${(e.timestamp||'').slice(11,19)}</td>
    <td><span class="pill pill-info">${e.source||''}</span></td>
    <td style="font-size:11px">${e.event_type||''}</td>
    <td><span class="pill pill-${e.severity}">${e.severity||''}</span></td>
    <td style="font-family:var(--font-mono);font-size:11px">${e.src_ip||''}</td>
    <td style="font-family:var(--font-mono);font-size:11px">${e.dst_ip||''}</td>
    <td>${e.user||''}</td>
    <td style="font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escHtml(e.message||e.raw||'')}">${escHtml(e.message||e.raw||'').slice(0,120)}</td>
  </tr>`).join('');
}

/* ==== CORRELATIONS ==== */
function renderCorrelations(corrs){
  document.getElementById('corr-count').textContent=`${corrs.length} correlations`;
  const tbody=document.querySelector('#tbl-corr tbody');
  if(!corrs.length){tbody.innerHTML='<tr><td colspan="7" class="empty">No correlations yet — need enough events from the same source</td></tr>';return}
  tbody.innerHTML=corrs.slice(0,200).map(c=>`<tr>
    <td style="font-weight:600;color:var(--accent)">${c.rule_name||c.rule}</td>
    <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-mute)">${(c.timestamp||'').slice(11,19)}</td>
    <td><span class="pill pill-${c.severity}">${c.severity||''}</span></td>
    <td>${c.risk||0}</td><td>${c.count||0}</td>
    <td style="font-family:var(--font-mono)">${c.grouped_value||''}</td>
    <td style="font-size:11px;color:var(--text-dim);max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.description||''}</td>
  </tr>`).join('');
}

/* ==== ALERTS ==== */
function renderAlerts(alerts){
  const filter=state.alertsFilter;
  let items=alerts;
  if(filter) items=items.filter(a=>a.status===filter);
  const tbody=document.querySelector('#tbl-alerts tbody');
  if(!items.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No alerts match filter</td></tr>';return}
  tbody.innerHTML=items.slice(0,200).map(a=>`<tr>
    <td>#${a.id}</td>
    <td style="font-weight:600">${a.title||''}</td>
    <td><span class="pill pill-${a.severity}">${a.severity}</span></td>
    <td>${a.risk||0}</td><td>${a.count||0}</td>
    <td style="font-family:var(--font-mono)">${a.grouped_value||a.actor||''}</td>
    <td><span class="pill pill-${a.status}">${a.status}</span></td>
    <td style="white-space:nowrap">
      ${a.status==='open'?`<button class="btn btn-sm btn-ack" data-action="ack" data-id="${a.id}">Ack</button>`:''}
      ${a.status!=='closed'?`<button class="btn btn-sm btn-close" data-action="close" data-id="${a.id}">Close</button>`:''}
    </td>
  </tr>`).join('');
}

/* ==== RULES ==== */
function renderRules(rules){
  const el=document.getElementById('rules-list');
  if(!rules||!rules.length){el.innerHTML='<div style="color:var(--text-mute)">No rules loaded</div>';return}
  el.innerHTML=rules.map(r=>`<div class="rule-card">
    <div class="rule-name">${r.name}</div>
    <div class="rule-id">${r.id}</div>
    <div class="rule-desc">${r.description}</div>
    <div class="rule-meta">
      <span class="tag tag-window">window: ${r.window}s</span>
      <span class="tag tag-thresh">threshold: ${r.threshold}</span>
      <span class="pill pill-${r.severity}">${r.severity}</span>
    </div>
  </div>`).join('');
}

/* ---- HELPERS ---- */
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function fmt(n){return Number(n).toLocaleString()}
function toast(msg,type='ok'){
  const t=document.createElement('div');
  t.textContent=msg;
  Object.assign(t.style,{
    position:'fixed',bottom:'24px',right:'24px',padding:'10px 18px',
    borderRadius:'8px',fontSize:'13px',fontWeight:'600',
    background:type==='ok'?'#10b981':'#f59e0b',
    color:'#fff',zIndex:9999,opacity:0,
    transition:'opacity .2s',pointerEvents:'none',
  });
  document.body.appendChild(t);
  requestAnimationFrame(()=>t.style.opacity=1);
  setTimeout(()=>{t.style.opacity=0;setTimeout(()=>t.remove(),300)},2500);
}