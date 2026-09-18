(function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function sevColor(s) {
    return ({ info: '#9db0ff', low: '#53e6ff', medium: '#ffc44d', high: '#ff8a5c', critical: '#ff4d6a' })[s] || '#53e6ff';
  }

  function bars(rows, color) {
    const max = Math.max.apply(null, rows.map(([, v]) => v).concat([1]));
    return '<div class="bars">' + rows.map(([l, v]) => {
      const w = Math.round((v / max) * 100);
      return '<div class="bar-row">' +
        '<span class="bar-lab">' + esc(l) + '</span>' +
        '<div class="bar"><i style="width:' + w + '%;background:' + color + '"></i></div>' +
        '<span class="bar-val">' + v + '</span>' +
        '</div>';
    }).join('') + '</div>';
  }

  function table(rows, cols) {
    return '<table><tr>' + cols.map((c) => '<th>' + c + '</th>').join('') + '</tr>' + rows.map((r) =>
      '<tr>' + cols.map((c, i) => '<td>' + (typeof r === 'function' ? r(c) : esc(r[i])) + '</td>').join('') + '</tr>'
    ).join('') + '</table>';
  }

  function loginChartBars(series) {
    const max = Math.max.apply(null, series.concat([1]));
    return '<div class="failbars">' + series.map((v) => {
      const h = Math.max(2, Math.round((v / max) * 110));
      return '<div class="failbar' + (v === 0 ? ' zero' : '') + '" style="height:' + h + 'px"></div>';
    }).join('') + '</div>';
  }

  window.buildHTMLReport = function (d) {
    const c = d.counters;
    const sevRows = {};
    d.hist.forEach((a) => { sevRows[a.severity] = (sevRows[a.severity] || 0) + 1; });

    const protoRows = Object.entries(d.traffic.proto).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);

    const body = []
      .concat(blocks.header(d, c))
      .concat(blocks.threats(d, sevRows))
      .concat(blocks.auth(d))
      .concat(blocks.logins(d))
      .concat(blocks.evtx(d))
      .concat(blocks.apps(d))
      .concat(blocks.traffic(d, protoRows))
      .concat(blocks.dns(d))
      .concat(blocks.edr(d))
      .concat(blocks.vuln(d))
      .concat(blocks.topology(d))
      .join('\n');

    return '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>' +
      '<title>SOC 3D Dashboard — Report</title><style>' +
      ':root{--bg:#070b16;--panel:#0e1526;--line:#1b2440;--txt:#d6e4ff;--mut:#6d7fa3;--acc:#53e6ff;--ok:#34f5a5;--warn:#ffc44d;--crit:#ff4d6a;}' +
      '*{box-sizing:border-box;margin:0;padding:0}' +
      'body{background:linear-gradient(160deg,#0a1120,#070b16 60%);color:var(--txt);font-family:"Segoe UI",system-ui,sans-serif;padding:28px 34px;}' +
      'h1,h2,h3{letter-spacing:1px}' +
      'h1{font-size:22px;color:var(--acc)}' +
      'h2{font-size:14px;color:var(--acc);text-transform:uppercase;margin:26px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}' +
      'h2:first-of-type{margin-top:4px}' +
      '.head{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}' +
      '.head .sub{color:var(--mut);font-size:12px;margin-top:3px}' +
      '.logo{width:34px;height:34px;border-radius:50%;background:radial-gradient(circle at 30% 30%,#7be9ff,#53e6ff 45%,#123b52 100%);' +
      'border:2px solid rgba(83,230,255,.6);box-shadow:0 0 14px rgba(83,230,255,.45)' +
      ';display:inline-block;vertical-align:middle;margin-right:12px}' +
      '.pill{font-family:Consolas,monospace;font-size:11px;color:var(--ok);border:1px solid rgba(52,245,165,.4);border-radius:999px;padding:4px 12px}' +
      '.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:8px}' +
      '.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}' +
      '.card .label{font-size:10px;letter-spacing:1.5px;color:var(--mut);text-transform:uppercase}' +
      '.card .val{font-size:24px;font-weight:700;font-family:Consolas,monospace;margin-top:4px}' +
      '.card .val.acc{color:var(--acc)}.card .val.ok{color:var(--ok)}.card .val.warn{color:var(--warn)}.card .val.crit{color:var(--crit)}' +
      'table{width:100%;border-collapse:collapse;font-size:11px;margin-top:6px}' +
      'th{color:var(--mut);text-align:left;font-size:9.5px;text-transform:uppercase;letter-spacing:1px;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}' +
      'td{padding:5px 8px;border-bottom:1px solid rgba(27,36,64,.6);vertical-align:top;font-family:Consolas,monospace}' +
      'tr:hover td{background:rgba(83,230,255,.04)}' +
      '.sev{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}' +
      '.badge{font-size:9px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--mut);white-space:nowrap}' +
      '.badge.ok{color:var(--ok);border-color:rgba(52,245,165,.45)}.badge.warn{color:var(--warn);border-color:rgba(255,196,77,.45)}' +
      '.badge.crit{color:var(--crit);border-color:rgba(255,77,106,.5)}' +
      '.bars{display:grid;gap:5px;margin-top:6px}.bar-row{display:grid;grid-template-columns:180px 1fr 44px;gap:10px;align-items:center;font-size:11px}' +
      '.bar{height:9px;border-radius:5px;background:rgba(255,255,255,.06);overflow:hidden}.bar i{display:block;height:100%}' +
      '.bar-lab,.bar-val{font-family:Consolas,monospace}.bar-val{color:var(--txt)}' +
      '.failbars{display:flex;align-items:flex-end;gap:2px;height:112px;margin-top:8px;border-bottom:1px solid var(--line)}' +
      '.failbar{flex:1;background:#ff4d6a;border-radius:2px 2px 0 0;min-width:1px}.failbar.zero{background:rgba(255,255,255,.08)}' +
      '.foot{margin-top:30px;padding-top:12px;border-top:1px solid var(--line);color:var(--mut);font-size:10.5px;line-height:1.7}' +
      '@media (max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.bar-row{grid-template-columns:110px 1fr 40px}}' +
      '</style></head><body>' + body +
      '<div class="foot">Generated ' + esc(d.generatedAt) + ' &middot; SOC 3D Dashboard v' + esc(d.version) + ' &middot; tick ' + d.tick +
      '<br/>All telemetry is simulated demonstration data generated by the in-app sensor streams.</div>' +
      '</body></html>';
  };

  const blocks = {};

  blocks.header = (d, c) => [
    '<div class="head"><div><span class="logo"></span><h1>SOC 3D Dashboard &mdash; Security Report</h1>' +
    '<div class="sub">Session snapshot &middot; ' + esc(d.generatedAt) + ' &middot; ' + d.tick + ' simulator ticks &middot; v' + esc(d.version) + '</div></div>' +
    '<span class="pill">' + (c.threatsActive > 0 ? 'THREAT ACTIVE' : 'ALL SYSTEMS NOMINAL') + '</span></div>',
    '<div class="grid">' +
    kpi('Events / sec', c.events, 'acc') + kpi('Active threats', c.threatsActive, c.threatsActive > 0 ? 'crit' : 'ok') +
    kpi('Blocked attempts', c.blocked, 'warn') + kpi('Packet rate', c.packets, 'acc') + '</div>',
    '<div class="grid">' +
    kpi('Detection load', c.load + '%', c.load > 80 ? 'crit' : '') + kpi('Auth success', c.authRate + '%', c.authRate < 70 ? 'crit' : 'ok') +
    kpi('Failed logins', c.badlogon, c.badlogon > 5 ? 'crit' : 'warn') + kpi('Response (ms)', c.latency + ' ms', '') + '</div>'
  ];

  function kpi(label, val, cls) {
    return '<div class="card"><div class="label">' + label + '</div><div class="val ' + cls + '">' + esc(val) + '</div></div>';
  }
  blocks.kpi = kpi;

  blocks.threats = (d, sevRows) => [
    '<h2>1. SIEM &mdash; Threat Feed</h2>' +
    '<p style="font-size:11px;color:var(--mut);margin-top:4px">' + d.hist.length + ' recent alerts (session total: severity mix below).</p>',
    bars(Object.entries(sevRows).sort((a, b) => b[1] - a[1]), '#ff4d6a'),
    '<h2>Threat Detections (latest)</h2>',
    table(
      d.hist.map((a) => [a.ts, '<span class="sev" style="background:' + sevColor(a.severity) + '"></span>' + a.severity.toUpperCase(), a.type, esc(a.host), esc(a.ip), esc(a.msg)]),
      ['Time', 'Severity', 'Type', 'Host', 'IP', 'Message']
    )
  ];

  blocks.auth = (d) => [
    '<h2>2. Authentication &mdash; Summary</h2>' +
    '<div class="grid"><div class="card"><div class="label">Success</div><div class="val ok">' + d.loginStats.ok + '</div></div>' +
    '<div class="card"><div class="label">Failures</div><div class="val crit">' + d.loginStats.fail + '</div></div>' +
    '<div class="card"><div class="label">Lockouts</div><div class="val warn">' + d.loginStats.lock + '</div></div>' +
    '<div class="card"><div class="label">Auth rate</div><div class="val acc">' + d.counters.authRate + '%</div></div></div>',
    '<h2>Failed Logins / Tick (last 60)</h2>',
    loginChartBars(d.loginPrc)
  ];

  blocks.logins = (d) => [
    '<h2>3. Authentication &mdash; Attempts</h2>',
    table(
      d.histLogin.map((l) => [l.ts, l.outcome.toUpperCase(), esc(l.user), l.proto, esc(l.srcIP), esc(l.dst), l.reason ? esc(l.reason) : '&mdash;']),
      ['Time', 'Result', 'User', 'Protocol', 'Source', 'Target', 'Failure reason']
    )
  ];

  blocks.evtx = (d) => [
    '<h2>4. Windows Event Log &mdash; EVTX</h2>' +
    '<p style="font-size:11px;color:var(--mut);margin-top:4px">Security ' + d.evtxCounters.security + ' &middot; System ' + d.evtxCounters.system + ' &middot; PowerShell ' + d.evtxCounters.powershell + ' &middot; audit clears ' + d.evtxCounters.clearedCount + '</p>',
    table(
      d.histEvtx.map((e) => [e.ts, e.eid, e.log, e.level.toUpperCase(), esc(e.src), esc(e.msg)]),
      ['Time', 'ID', 'Channel', 'Level', 'Source', 'Message']
    )
  ];

  blocks.apps = (d) => [
    '<h2>5. Application Logs</h2>',
    table(
      d.histApp.map((a) => [a.ts, a.lvl.toUpperCase(), a.svc, esc(a.msg)]),
      ['Time', 'Level', 'Service', 'Message']
    )
  ];

  blocks.traffic = (d, protoRows) => {
    const total = protoRows.reduce((s, [, v]) => s + v, 0);
    return [
      '<h2>6. Network Traffic &mdash; NetFlow</h2>' +
      '<p style="font-size:11px;color:var(--mut);margin-top:4px">' + d.traffic.sessions + ' sessions &middot; ' +
      (d.traffic.bytes / 1048576).toFixed(2) + ' MB observed &middot; recent flows: ' + d.histFlow.length + '</p>',
      '<table><tr><th>Protocol</th><th>Share</th><th style="width:40%">Volume</th><th>Count</th></tr>' +
      protoRows.map(([name, v]) => {
        const pct = total ? Math.round((v / total) * 100) : 0;
        return '<tr><td>' + name + '</td><td>' + pct + '%</td>' +
          '<td><div class="bar"><i style="width:' + pct + '%;background:#53e6ff"></i></div></td><td>' + v + '</td></tr>';
      }).join('') + '</table>',
      '<h2>Top Talkers</h2>',
      table(d.talkers.map((t) => [t.ip, t.proto, (t.bytes / 1024).toFixed(1) + ' KB']), ['Source IP', 'Protocol', 'Volume'])
    ];
  };

  blocks.dns = (d) => [
    '<h2>7. DNS Activity</h2>' +
    '<p style="font-size:11px;color:var(--mut);margin-top:4px">Queries ' + d.dnsAgg.total + ' &middot; NXDOMAIN rate ' +
    (d.dnsAgg.total ? Math.round((d.dnsAgg.nxdomain / d.dnsAgg.total) * 100) : 0) + '% (suspicious lookups highlighted)</p>',
    '<h2>Top Queried Names</h2>',
    bars(d.topDomains.map(([n, v]) => [n, v]), '#53e6ff')
  ];

  blocks.edr = (d) => [
    '<h2>8. Endpoint Detection &amp; Response</h2>',
    table(
      d.histEdr.map((e) => [e.ts, e.technique, esc(e.name), '<span class="badge crit">' + e.sev.toUpperCase() + '</span>', esc(e.host), esc(e.process), e.verdict]),
      ['Time', 'Technique', 'Detection', 'Severity', 'Host', 'Process', 'Verdict']
    )
  ];

  blocks.vuln = (d) => [
    '<h2>9. Vulnerability Scanner</h2>',
    table(
      d.histVuln.map((v) => [v.ts, v.cve, 'v' + v.cvss.toFixed(1), esc(v.pkg + ' @ :' + v.port), esc(v.host), v.status]),
      ['Time', 'CVE', 'CVSS', 'Package', 'Host', 'Status']
    )
  ];

  blocks.topology = (d) => [
    '<h2>10. Network Topology &mdash; Asset Inventory</h2>',
    table(
      d.nodes.map((n) => [esc(n.name), esc(n.type), esc(n.ip), n.links, n.compromised ? '<span class="badge crit">COMPROMISED</span>' : '<span class="badge ok">NOMINAL</span>']),
      ['Host', 'Role', 'IP', 'Links', 'Status']
    )
  ];
})();