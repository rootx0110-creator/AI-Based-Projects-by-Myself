(function () {
  'use strict';

  /* =====================================================================
   * Utilities
   * ===================================================================== */
  const $ = (id) => document.getElementById(id);
  const rand = (min, max) => min + Math.random() * (max - min);
  const randI = (min, max) => Math.floor(rand(min, max + 1));
  const choice = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const pad = (n) => (n < 10 ? '0' + n : '' + n);
  const hex = (n) => n.toString(16).padStart(2, '0');

  function timeStr() {
    const d = new Date();
    return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }

  function tsStamp() {
    const d = new Date();
    return '' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      '-' + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
  }

  function fmt(n) {
    return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : '' + Math.round(n);
  }

  /* =====================================================================
   * SOC Simulator - core
   * ===================================================================== */
  const sim = {
    tick: 0,
    activeThreats: new Set(),
    counters: { events: 0, blocked: 0, latency: 0, load: 0, packets: 0, badlogon: 0, authRate: 100 },
    history: { events: [], blocked: [], latency: [], packets: [], badlogon: [] }
  };

  const HIST = [];

  const THREAT_TYPES = [
    'SQL Injection', 'Brute Force', 'Port Scan', 'Malware Beacon',
    'Privilege Escalation', 'Data Exfiltration', 'DDoS', 'Phishing',
    'Zero-Day Exploit', 'Credential Stuffing', 'Ransomware', 'C2 Callback'
  ];

  function randomIP() {
    return '10.' + randI(0, 255) + '.' + randI(0, 255) + '.' + randI(1, 254);
  }
  function randomExtIP() {
    return randI(1, 223) + '.' + randI(0, 255) + '.' + randI(0, 255) + '.' + randI(1, 254);
  }

  /* =====================================================================
   * SOC Simulator - EVTX (Windows Event Log)
   * ===================================================================== */
  const HIST_EVTX = [];
  const evtxCounters = { security: 0, system: 0, powershell: 0, clearedCount: 0 };

  const USERS = ['Administrator', 'jsmith', 'sql_svc', 'backup_acct', 'devops', 'svc_backup', 'svc_patch', 'auditor'];
  const FULL_USERS = USERS.map((u) => 'SOC-CORP\\' + u);
  const HOSTS = ['SOC-WKS-01', 'SOC-WKS-02', 'SOC-SRV-01', 'SOC-DC-01', 'SOC-DB-01', 'SOC-WEB-01'];

  const PROC_NAMES = ['explorer.exe', 'svchost.exe', 'powershell.exe', 'cmd.exe', 'sqlservr.exe', 'chrome.exe', 'notepad.exe', 'msiexec.exe', 'python.exe'];

  function evtxEvent() {
    const roll = Math.random();
    let e;
    if (roll < 0.58) e = securityEvent();
    else if (roll < 0.82) e = systemEvent();
    else e = powershellEvent();

    evtxCounters[e.log.toLowerCase()]++;
    e.ts = timeStr();
    if (e.eid === 1102) {
      evtxCounters.clearedCount++;
      e.level = 'cleared';
      e.src = 'Microsoft-Windows-Security-Auditing';
      e.msg = 'The audit log was cleared.';
      e.detail = 'Subject: SYSTEM (S-1-5-18) | Category: Authentication Policy Change';
    }
    return e;
  }

  function securityEvent() {
    const eid = choice([4624, 4625, 4634, 4672, 4688, 4697, 4720, 4722, 4725, 4732, 4625, 4624, 4688]);
    const user = choice(FULL_USERS);
    const host = choice(HOSTS);
    const ip = Math.random() < 0.75 ? randomIP() : randomExtIP();
    const proc = choice(PROC_NAMES);
    switch (eid) {
      case 4624:
        return {
          log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'An account was successfully logged on.',
          detail: 'Account: ' + user + ' | Logon Type: ' + choice([2, 3, 10, 12]) + ' | Source: ' + ip + ' | Process: ' + proc
        };
      case 4625:
        return {
          log: 'Security', eid, level: 'fail', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'An account failed to log on.',
          detail: 'Account: ' + choice(USERS) + ' | Failure: ' + choice(['Unknown user or bad password', 'Account locked out', 'Password expired']) + ' | Source: ' + ip + ' | Logon Type: 3'
        };
      case 4634:
        return {
          log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'An account was logged off.',
          detail: 'Account: ' + user + ' | Logon Type: ' + choice([2, 10]) + ' | Source: ' + ip
        };
      case 4672:
        return {
          log: 'Security', eid, level: 'warn', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'Special privileges assigned to new logon.',
          detail: 'Account: ' + user + ' | Privileges: SeTcbPrivilege, SeBackupPrivilege, SeRestorePrivilege'
        };
      case 4688:
        return {
          log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A new process has been created.',
          detail: 'Process: ' + proc + ' (' + randI(1000, 90000) + ') | Creator: ' + user + ' | Target: ' + host
        };
      case 4697:
        return {
          log: 'Security', eid, level: 'warn', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A service was installed in the system.',
          detail: 'Service: ' + choice(['SocAgentSvc', 'UpdaterService', 'SqlWatchdog', 'BackupSvc']) + ' | Account: ' + choice(USERS)
        };
      case 4720:
        return {
          log: 'Security', eid, level: 'warn', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A user account was created.',
          detail: 'New Account: SOC-CORP\\' + choice(['temp_employ', 'test_user', 'g_user07']) + ' | Subject: ' + choice(FULL_USERS) + ' | Manager: ' + host
        };
      case 4722:
        return {
          log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A user account was enabled.',
          detail: 'Account: ' + choice(USERS) + ' | Subject: ' + choice(FULL_USERS)
        };
      case 4725:
        return {
          log: 'Security', eid, level: 'warn', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A user account was disabled.',
          detail: 'Account: ' + choice(USERS) + ' | Subject: ' + choice(FULL_USERS)
        };
      case 4732:
        return {
          log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing',
          msg: 'A member was added to a security-enabled local group.',
          detail: 'Member: ' + choice(FULL_USERS) + ' | Group: ' + choice(['Administrators', 'Remote Desktop Users', 'Backup Operators'])
        };
      default:
        return { log: 'Security', eid, level: 'win', src: 'Microsoft-Windows-Security-Auditing', msg: 'Security audit event.', detail: user };
    }
  }

  function systemEvent() {
    const eid = choice([7036, 7045, 1074, 6005, 7040]);
    const svc = choice(['Security Accounts Manager', 'WinHTTP Web Proxy Auto-Discovery', 'Windows Defender Antivirus', 'Remote Desktop Services', 'DNS Client', 'Update Orchestrator Service']);
    switch (eid) {
      case 7036:
        return {
          log: 'System', eid, level: 'win', src: 'Microsoft-Windows-Service Control Manager',
          msg: 'The ' + svc + ' service entered the ' + choice(['running', 'stopped', 'paused']) + ' state.',
          detail: 'Host: ' + choice(HOSTS) + ' | ServiceType: user mode'
        };
      case 7045:
        return {
          log: 'System', eid, level: 'warn', src: 'Microsoft-Windows-Service Control Manager',
          msg: 'A new service was installed in the system.',
          detail: 'Service: ' + choice(['ntfslog', 'drivehealth', 'watchdog']) + ' | Image: ' + choice(['C:\\Windows\\System32\\svchost.exe', 'C:\\Program Files\\Agent\\agent.exe'])
        };
      case 1074:
        return {
          log: 'System', eid, level: 'warn', src: 'Microsoft-Windows-Kernel-Power',
          msg: 'The system has been shut down by the user.',
          detail: 'Reason: ' + choice(['Application: Maintenance', 'Operating System: Update', 'Hardware: Maintenance']) + ' | Process: winlogon.exe'
        };
      case 6005:
        return {
          log: 'System', eid, level: 'win', src: 'Microsoft-Windows-EventLog',
          msg: 'The Event log service was started.',
          detail: 'Host: ' + choice(HOSTS)
        };
      default:
        return {
          log: 'System', eid, level: 'win', src: 'Microsoft-Windows-WindowsUpdateClient',
          msg: 'The update installer started a servicing operation.',
          detail: 'Caller: wuauclt | Host: ' + choice(HOSTS)
        };
    }
  }

  function powershellEvent() {
    const eid = choice([4104, 4103]);
    const script = choice([
      'Get-Process | Where-Object {$_.CPU -gt 100}',
      'Start-Service ' + choice(['Spooler', 'wuauserv']),
      'Invoke-WebRequest -Uri http://192.0.2.' + randI(1, 9) + '/load.php',
      'Get-ADUser -Filter * -Properties LastLogon',
      'New-Item -Path HKLM:\\SOFTWARE\\Temp -Force',
      'schtasks /create /tn upd /tr cmd.exe /sc daily'
    ]);
    return {
      log: 'PowerShell', eid, level: eid === 4104 && Math.random() < 0.5 ? 'warn' : 'win',
      src: 'Microsoft-Windows-PowerShell',
      msg: 'Script block logging was enabled.',
      detail: 'ScriptBlock: ' + script + ' | Host: ' + choice(HOSTS) + ' | User: ' + choice(USERS)
    };
  }

  /* =====================================================================
   * SOC Simulator - Application / Service logs
   * ===================================================================== */
  const HIST_APP = [];

  const APP_WEB = {
    'Apache': [
      { lvl: 'info', m: 'GET /api/v2/alerts HTTP/1.1 200 OK (%d ms)' },
      { lvl: 'info', m: 'GET /healthz HTTP/1.1 200 OK' },
      { lvl: 'warn', m: 'GET /admin HTTP/1.1 403 Forbidden - %s' },
      { lvl: 'error', m: 'POST /api/upload HTTP/1.1 500 Internal Server Error' },
      { lvl: 'error', m: 'mod_security: Request blocked - rule 942100 (SQL Injection)' }
    ],
    'Nginx': [
      { lvl: 'info', m: '%s - GET /events/stream 200' },
      { lvl: 'error', m: 'upstream prematurely closed connection while reading response header' },
      { lvl: 'warn', m: 'client sent too large request body to /api/config' }
    ]
  };
  const APP_DB = {
    'MySQL': [
      { lvl: 'info', m: 'Query: SELECT severity,COUNT(*) FROM alerts GROUP BY severity (%d rows)' },
      { lvl: 'warn', m: 'Slow query: %d s > 0.2 s threshold (UPDATE sessions SET token=...)' },
      { lvl: 'error', m: 'Lost connection to MySQL server during query' },
      { lvl: 'info', m: 'Connection established: %s' }
    ]
  };
  const APP_DNS = {
    'BIND': [
      { lvl: 'info', m: 'client %s#%d: query: soc.local IN A' },
      { lvl: 'warn', m: 'client %s: query (cache) denied' },
      { lvl: 'error', m: 'child failed to start for zone external.db' }
    ]
  };
  const APP_FW = {
    'Firewall': [
      { lvl: 'warn', m: 'BLOCK: TCP %s:%d -> %s:%d [policy drop]' },
      { lvl: 'warn', m: 'BLOCK: UDP %s -> %s:53 [port scan heuristic]' },
      { lvl: 'info', m: 'ALLOW: stateful rule established %s -> %s' },
      { lvl: 'error', m: 'DROP: ICMP flood from %s (rate exceeded)' }
    ]
  };

  function appLog() {
    const ctx = choice([APP_WEB, APP_WEB, APP_DB, APP_DNS, APP_FW]);
    const svc = choice(Object.keys(ctx));
    const tpl = choice(ctx[svc]);
    const ip = randomExtIP();
    const tokens = [ip, randI(1024, 65535), ip, ip, randI(1, 4000)];
    let msg = tpl.m.replace(/%d/g, () => String(randI(12, 4800)));
    tokens.forEach((t) => { msg = msg.replace('%s', String(t)); });
    return { ts: timeStr(), svc, lvl: tpl.lvl, msg };
  }

  /* =====================================================================
   * SOC Simulator - Login attempts
   * ===================================================================== */
  const HIST_LOGIN = [];
  const loginStats = { ok: 0, fail: 0, lock: 0 };
  const loginWindow = [];
  const loginFailPerTick = [];

  const GOOD_USERS = ['jsmith', 'Administrator', 'sql_svc', 'auditor', 'devops', 'svc_backup', 'mgibson'];
  const BAD_USERS = ['guest', 'admin', 'admin123', 'test', 'root', 'sales2', 'temp', 'root2', 'sa'];
  const PROTOCOLS = ['RDP', 'SSH', 'Kerberos', 'NTLM', 'WinRM', 'SMB'];
  const LOGON_TYPES = { RDP: 10, SSH: 3, Kerberos: 3, NTLM: 3, WinRM: 10, SMB: 3 };
  const SOURCE_HOSTS = ['SOC-WKS-01', 'SOC-WKS-02', 'SOC-SRV-01', 'SOC-DC-01'];

  function loginAttempt() {
    const roll = Math.random();
    const outcome = roll < 0.6 ? 'ok' : roll < 0.93 ? 'fail' : 'lock';
    const rdp = Math.random() < 0.5;
    const user = outcome === 'ok' ? choice(GOOD_USERS) : choice(BAD_USERS.concat(GOOD_USERS));
    const proto = choice(PROTOCOLS);
    const srcIP = outcome === 'ok' ? (rdp ? randomIP() : randomExtIP()) : choice([randomExtIP(), randomExtIP(), randomIP()]);
    const dst = choice(SOURCE_HOSTS);
    if (outcome === 'ok') loginStats.ok++;
    if (outcome === 'fail') loginStats.fail++;
    if (outcome === 'lock') loginStats.lock++;
    return {
      ts: timeStr(), outcome, user, proto, srcIP, dst,
      type: LOGON_TYPES[proto],
      status: outcome === 'ok' ? 'SUCCESS' : outcome === 'fail' ? 'FAILURE' : 'LOCKED OUT',
      reason: outcome === 'fail' ? '0xC000006A - bad password' : outcome === 'lock' ? '0xC0000234 - account locked (threshold exceeded)' : ''
    };
  }

  /* =====================================================================
   * SOC Simulator - Netflow / DNS / EDR / VULN / INTEL
   * ===================================================================== */
  const HIST_FLOW = [];
  const HIST_DNS = [];
  const HIST_EDR = [];
  const HIST_VULN = [];
  const INTEL = [];
  const traffic = {
    proto: { HTTPS: 0, HTTP: 0, DNS: 0, SSH: 0, SMB: 0, RDP: 0, TLS: 0, SMTP: 0, ICMP: 0, NTP: 0 },
    bytes: 0,
    sessions: 0
  };
  const talkerBytes = {};
  const dnsAgg = { total: 0, nxdomain: 0, domains: {} };

  const PROTO_POOL = ['HTTPS', 'HTTPS', 'HTTP', 'HTTPS', 'DNS', 'SSH', 'SMB', 'RDP', 'TLS', 'SMTP', 'ICMP', 'NTP'];
  const FLOW_ACTIONS = ['allow', 'allow', 'allow', 'monitor', 'detect'];
  const QUERY_POOL = [
    ['soc.local', 'NOERROR', 'A'], ['autoupdate.corp.lan', 'NOERROR', 'A'],
    ['mail.relay.corp.lan', 'NOERROR', 'MX'], ['gw', 'NOERROR', 'AAAA'],
    ['prod-srv-03', 'NOERROR', 'A'], ['files.soc.local', 'NOERROR', 'A'],
    ['update-check.lan', 'NXDOMAIN', 'A'], ['id-mrhp.invalid', 'NXDOMAIN', 'A'],
    ['cdn-c2resolver.buzz', 'NXDOMAIN', 'A'], ['beacon-poc.tk', 'NXDOMAIN', 'TXT'],
    ['intranet.corp.lan', 'NOERROR', 'A'], ['s3.eu-west-2.amazonaws.com', 'NOERROR', 'AAAA']
  ];
  const ATTACK_TECH = [
    ['T1059.001', 'PowerShell', 'PSH-Script-Exec'], ['T1136.001', 'Local-Account', 'User-Create'],
    ['T1567.002', 'Exfiltration', 'SMB-Share-Tx'], ['T1027', 'Obfuscated-Files', 'Payload-Dropper'],
    ['T1543.003', 'Create-Modify-Service', 'Win32-Svc-Install'], ['T1041', 'C2-Channel', 'HTTP-Beacon'],
    ['T1078', 'Valid-Accounts', 'Logon-Anomaly'], ['T1566.001', 'Phishing', 'OLE-Susp'],
    ['T1496', 'Resource-Hijacking', 'Miner-Child-Proc'], ['T1036', 'Masquerading', 'Rename-Proc']
  ];
  const VULN_POOL = [
    ['CVE-2026-22184', 9.8, 445, 'smbv1'], ['CVE-2026-09177', 8.6, 22, 'openssh'],
    ['CVE-2025-40143', 8.1, 443, 'nginx'], ['CVE-2026-11802', 9.1, 1433, 'mssql'],
    ['CVE-2026-00319', 7.5, 53, 'bind'], ['CVE-2024-30981', 7.2, 3389, 'rdp'],
    ['CVE-2026-45772', 9.8, 80, 'apache'], ['CVE-2025-71466', 6.5, 8443, 'paloalto']
  ];
  const COUNTRIES = ['RU', 'CN', 'KP', 'IR', 'BR', 'IN', 'VN', 'RO', 'TR', 'UA'];
  const INTEL_CATS = ['SCAN', 'C2', 'BOTNET', 'EXFIL', 'BRUTE'];

  function flowEvent() {
    const proto = choice(PROTO_POOL);
    const srcExt = Math.random() < 0.55;
    const srcIP = srcExt ? randomExtIP() : randomIP();
    const dstIP = srcExt ? randomIP() : randomExtIP();
    const action = choice(FLOW_ACTIONS);
    const bytes = randI(80, 400000);
    traffic.proto[proto]++;
    traffic.bytes += bytes;
    traffic.sessions++;
    if (srcExt && Math.random() < 0.5) {
      const country = choice(COUNTRIES);
      INTEL.unshift({ ts: timeStr(), country, cat: choice(INTEL_CATS), indicator: srcIP + ':' + randI(1, 65535), action });
      if (INTEL.length > 60) INTEL.pop();
    }
    const e = { ts: timeStr(), proto, srcIP, dstIP, bytes, action };
    HIST_FLOW.unshift(e);
    if (HIST_FLOW.length > 120) HIST_FLOW.pop();
    talkerBytes[srcIP] = (talkerBytes[srcIP] || 0) + bytes;
    if (Object.keys(talkerBytes).length > 40) delete talkerBytes[Object.keys(talkerBytes)[0]];
    return e;
  }

  function dnsQuery() {
    const q = choice(QUERY_POOL);
    dnsAgg.total++;
    if (q[1] === 'NXDOMAIN') dnsAgg.nxdomain++;
    dnsAgg.domains[q[0]] = (dnsAgg.domains[q[0]] || 0) + 1;
    const e = { ts: timeStr(), qname: q[0], rcode: q[1], type: q[2], srcIP: Math.random() < 0.5 ? randomIP() : randomExtIP() };
    HIST_DNS.unshift(e);
    if (HIST_DNS.length > 60) HIST_DNS.pop();
    return e;
  }

  function edrDetection() {
    const t = choice(ATTACK_TECH);
    return {
      ts: timeStr(), technique: t[0], name: t[1], det: t[2],
      sev: Math.random() < 0.3 ? 'critical' : 'high', host: choice(HOSTS),
      process: choice(PROC_NAMES),
      hash: Array.from({ length: 8 }, () => 'ab0123456789def'[randI(0, 15)]).join(''),
      verdict: choice(['BLOCKED', 'QUARANTINED', 'CLEANED', 'ISOLATED'])
    };
  }

  function vulnEvent() {
    const v = choice(VULN_POOL);
    return {
      ts: timeStr(), cve: v[0], cvss: v[1], port: v[2], pkg: v[3],
      host: choice(HOSTS), status: choice(['NEW', 'NEW', 'REOPENED', 'VERIFIED'])
    };
  }

  /* =====================================================================
   * SOC Simulator - step
   * ===================================================================== */
  function stepSim() {
    sim.tick++;
    const c = sim.counters;
    c.events = clamp(c.events + rand(-220, 240), 300, 4200);
    c.blocked = clamp(c.blocked + rand(-30, 42), 20, 1600);
    c.latency = clamp(c.latency + rand(-5, 5), 8, 120);
    c.load = clamp(c.load + rand(-4, 4), 20, 92);
    c.packets = clamp(c.packets + rand(-120, 130), 150, 4800);

    ['events', 'blocked', 'latency', 'packets', 'badlogon'].forEach((k) => {
      sim.history[k] = sim.history[k] || [];
      sim.history[k].push(k === 'badlogon' ? c.badlogon : c[k]);
      if (sim.history[k].length > 60) sim.history[k].shift();
    });

    // ---- windows event log stream
    const nEvtx = randI(1, 3);
    for (let i = 0; i < nEvtx; i++) {
      const e = evtxEvent();
      HIST_EVTX.unshift(e);
      if (HIST_EVTX.length > 120) HIST_EVTX.pop();
      renderEVTX(e);
    }

    // ---- application logs
    const nApp = randI(1, 3);
    for (let i = 0; i < nApp; i++) {
      const a = appLog();
      HIST_APP.unshift(a);
      if (HIST_APP.length > 80) HIST_APP.pop();
      renderApp(a);
    }

    // ---- login attempts
    const nLog = randI(1, 3);
    let oTick = 0, fTick = 0;
    for (let i = 0; i < nLog; i++) {
      const l = loginAttempt();
      HIST_LOGIN.unshift(l);
      if (HIST_LOGIN.length > 80) HIST_LOGIN.pop();
      if (l.outcome === 'ok') oTick++;
      if (l.outcome === 'fail') fTick++;
      renderLogin(l);
    }
    loginWindow.push({ ok: oTick, fail: fTick });
    while (loginWindow.length > 60) loginWindow.shift();
    loginFailPerTick.push(fTick);
    while (loginFailPerTick.length > 60) loginFailPerTick.shift();

    const tot = loginWindow.reduce((s, w) => s + w.ok + w.fail, 0);
    const okTot = loginWindow.reduce((s, w) => s + w.ok, 0);
    c.authRate = tot === 0 ? 100 : Math.round((okTot / tot) * 100);
    c.badlogon = loginWindow.reduce((s, w) => s + w.fail, 0);

    // ---- netflow / dns / edr / vuln
    const nFlow = randI(2, 5);
    for (let i = 0; i < nFlow; i++) flowEvent();
    const nDns = randI(2, 4);
    for (let i = 0; i < nDns; i++) renderDns(dnsQuery());
    if (Math.random() < 0.3) { const dd = edrDetection(); HIST_EDR.unshift(dd); if (HIST_EDR.length > 40) HIST_EDR.pop(); renderEDR(dd); }
    if (Math.random() < 0.22) { const vv = vulnEvent(); HIST_VULN.unshift(vv); if (HIST_VULN.length > 30) HIST_VULN.pop(); renderVuln(vv); }
    renderTraffic();
    renderIntel();
    updateSources();

    tryResolveThreats();
    if (Math.random() < 0.5) emitAlert();
    drawLoginChart();
  }

  function tryResolveThreats() {
    if (sim.activeThreats.size && Math.random() < 0.28) {
      const id = choice(Array.from(sim.activeThreats));
      sim.activeThreats.delete(id);
      const node = topo.nodes.find((n) => n.id === id);
      if (node) node.compromised = false;
    }
  }

  function emitAlert() {
    const roll = Math.random();
    const severity = roll < 0.28 ? 'info' : roll < 0.48 ? 'low'
      : roll < 0.68 ? 'medium' : roll < 0.9 ? 'high' : 'critical';
    const type = choice(THREAT_TYPES);
    const host = choice(topo.nodes);
    const entry = {
      ts: timeStr(),
      severity,
      host: host.name,
      ip: host.ip,
      type,
      msg: type + ' detected at ' + host.name,
      detail: 'src ' + randomIP() + ' via ' + choice(['eth0', 'eth1', 'pcap0'])
    };
    HIST.unshift(entry);
    if (HIST.length > 80) HIST.pop();
    if (severity === 'high' || severity === 'critical') {
      const id = host.id;
      if (sim.activeThreats.add(id)) {
        host.compromised = true;
        markNodeAlert(host, severity);
      }
    }
    renderFeed(entry);
  }

  /* =====================================================================
   * Network Topology
   * ===================================================================== */
  const NODE_TYPES = [
    { type: 'gateway', color: 0x53e6ff, r: 0.52, names: ['FIREWALL-01', 'EDGE-GW', 'VPN-HUB'] },
    { type: 'service', color: 0x7b8cff, r: 0.4, names: ['SIEM-CORE', 'WAF', 'IDS-ENGINE', 'AUTH-SRV', 'DNS-SRV'] },
    { type: 'db',      color: 0xffc44d, r: 0.38, names: ['DB-CLUSTER-1', 'DB-REPLICA', 'VAULT'] },
    { type: 'edge',    color: 0xff7aa2, r: 0.3, names: ['SCADA-GW', 'IOT-BRIDGE', 'CAM-FEED', 'PRINT-SRV'] },
    { type: 'host',    color: 0x2fd7a8, r: 0.3, names: ['WS-01', 'WS-02', 'APP-01', 'APP-02', 'DEV-01', 'MAIL-SRV', 'PROXY', 'SHARE', 'BUILD-AGENT'] }
  ];

  const topo = { nodes: [], links: [], nextPktId: 0 };

  function buildTopology() {
    const hubs = [];
    hubs.push({ name: 'CORE-ROUTER', type: 'gateway', x: 0, y: 0, z: 0 });
    hubs.push({ name: 'DMZ-SW', type: 'gateway', x: -6, y: 2, z: 3 });
    hubs.push({ name: 'CORE-SW', type: 'gateway', x: 6, y: -2, z: -3 });

    let k = 0;
    hubs.forEach((h) => {
      const node = {
        id: 'n-' + (k++),
        name: h.name,
        type: h.type,
        ip: randomIP(),
        x: h.x, y: h.y, z: h.z,
        compromised: false,
        alertSev: null
      };
      topo.nodes.push(node);
    });
    hubs.forEach((h, i) => { hubs[i].index = i; });

    ['service', 'service', 'db', 'db', 'edge', 'host', 'host', 'host', 'host', 'host', 'host',
     'service', 'db', 'edge', 'host', 'host'].forEach((reqType) => {
      const def = NODE_TYPES.find((d) => d.type === reqType);
      const hub = hubs[k % hubs.length];
      const a = Math.random() * Math.PI * 2;
      const rad = rand(2.2, 5.4);
      const node = {
        id: 'n-' + (k++),
        name: choice(def.names),
        type: def.type,
        ip: randomIP(),
        x: hub.x + Math.cos(a) * rad,
        y: hub.y + rand(-2.4, 2.4),
        z: hub.z + Math.sin(a) * rad,
        compromised: false,
        alertSev: null
      };
      node.hubIndex = hubs[k % hubs.length].index;
      topo.nodes.push(node);
    });
  }

  function buildLinks() {
    const used = new Set();
    topo.nodes.forEach((node) => {
      if (node.hubIndex === undefined) return;
      const hub = topo.nodes[node.hubIndex];
      const key = [node.id, hub.id].sort().join('|');
      if (!used.has(key) && node.id !== hub.id) {
        used.add(key);
        topo.links.push({ a: node.id, b: hub.id, base: 0x33558a, active: 0 });
      }
    });
    let extra = 6;
    while (extra-- > 0) {
      const n1 = choice(topo.nodes);
      const n2 = choice(topo.nodes);
      if (n1 === n2) continue;
      const key = [n1.id, n2.id].sort().join('|');
      if (!used.has(key)) {
        used.add(key);
        topo.links.push({ a: n1.id, b: n2.id, base: 0x5076b0, active: 0 });
      }
    }
  }

  /* =====================================================================
   * Three.js scene
   * ===================================================================== */
  const wrap = $('scene-3d');
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  wrap.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, wrap.clientWidth / wrap.clientHeight, 0.1, 200);
  camera.position.set(14, 6, 14);
  camera.lookAt(0, 0, 0);

  scene.add(new THREE.AmbientLight(0x8797c4, 0.65));
  const keyLight = new THREE.DirectionalLight(0xbfd4ff, 0.9);
  keyLight.position.set(8, 12, 6);
  scene.add(keyLight);
  const glowLight = new THREE.PointLight(0x53e6ff, 1.4, 40);
  glowLight.position.set(6, 4, 8);
  scene.add(glowLight);

  const starGeo = new THREE.BufferGeometry();
  const starCount = 1800;
  const starPos = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    const r = rand(24, 60);
    const theta = rand(0, Math.PI * 2);
    const phi = Math.acos(rand(-1, 1));
    starPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    starPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    starPos[i * 3 + 2] = r * Math.cos(phi);
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  const stars = new THREE.Points(
    starGeo,
    new THREE.PointsMaterial({ color: 0x9fb8ff, size: 0.14, transparent: true, opacity: 0.8 })
  );
  scene.add(stars);

  const grid = new THREE.GridHelper(26, 26, 0x2a3d6e, 0x16233f);
  grid.position.y = -5.5;
  scene.add(grid);

  const topoGroup = new THREE.Group();
  scene.add(topoGroup);

  function haloTexture() {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 128;
    const ctx = cv.getContext('2d');
    const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(255,255,255,0.55)');
    g.addColorStop(0.35, 'rgba(255,255,255,0.18)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(cv);
  }
  const haloMap = haloTexture();

  function labelTexture(text, color) {
    const cv = document.createElement('canvas');
    const ctx = cv.getContext('2d');
    ctx.font = '600 28px "Segoe UI", sans-serif';
    const w = Math.ceil(ctx.measureText(text).width) + 24;
    cv.width = w; cv.height = 40;
    ctx.font = '600 28px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 8;
    ctx.fillStyle = color;
    ctx.fillText(text, w / 2, 22);
    const tex = new THREE.CanvasTexture(cv);
    tex.anisotropy = 4;
    return tex;
  }

  const nodeMeshes = [];
  const nodeData = new Map();

  function baseColorInt(n) {
    const def = NODE_TYPES.find((d) => d.type === n.type);
    return def.color;
  }

  topo.nodes.forEach((n) => {
    const def = NODE_TYPES.find((d) => d.type === n.type);
    const geo = new THREE.SphereGeometry(def.r, 32, 24);
    const mat = new THREE.MeshPhongMaterial({
      color: def.color,
      emissive: def.color,
      emissiveIntensity: 0.35,
      shininess: 80,
      transparent: true,
      opacity: 0.95
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(n.x, n.y, n.z);
    topoGroup.add(mesh);

    const halo = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: haloMap, color: def.color, transparent: true, opacity: 0.22, depthWrite: false })
    );
    halo.scale.set(2.4, 2.4, 1);
    mesh.add(halo);

    const label = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: labelTexture(n.name, '#cfe3ff'), transparent: true, depthWrite: false })
    );
    label.scale.set(3.4, 0.62, 1);
    label.position.set(0, def.r + 0.85, 0);
    mesh.add(label);

    mesh.userData.node = n;
    nodeMeshes.push(mesh);
    nodeData.set(mesh, { node: n, mesh, halo, mat });
  });

  const linkMeshes = [];
  linkMeshes.length = topo.links.length;

  topo.links.forEach((lk, i) => {
    const na = topo.nodes.find((x) => x.id === lk.a);
    const nb = topo.nodes.find((x) => x.id === lk.b);
    const geo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(na.x, na.y, na.z),
      new THREE.Vector3(nb.x, nb.y, nb.z)
    ]);
    const mat = new THREE.LineBasicMaterial({ color: lk.base, transparent: true, opacity: 0.45 });
    const line = new THREE.Line(geo, mat);
    topoGroup.add(line);
    linkMeshes[i] = line;
  });

  const packets = [];
  const packetGeo = new THREE.SphereGeometry(0.11, 12, 10);

  function spawnPacket(suspicious) {
    const lk = choice(topo.links);
    const na = topo.nodes.find((x) => x.id === lk.a);
    const nb = topo.nodes.find((x) => x.id === lk.b);
    const color = suspicious ? 0xff4d6a : 0x53ffbe;
    const mat = new THREE.MeshBasicMaterial({ color });
    const mesh = new THREE.Mesh(packetGeo, mat);
    const p = {
      mesh,
      a: new THREE.Vector3(na.x, na.y, na.z),
      b: new THREE.Vector3(nb.x, nb.y, nb.z),
      t: 0,
      speed: rand(0.45, 0.9),
      suspicious
    };
    mesh.position.copy(p.a);
    topoGroup.add(mesh);
    packets.push(p);
  }

  function updatePackets(dt) {
    for (let i = packets.length - 1; i >= 0; i--) {
      const p = packets[i];
      p.t += p.speed * dt;
      if (p.t >= 1) {
        topoGroup.remove(p.mesh);
        p.mesh.geometry.dispose();
        p.mesh.material.dispose();
        packets.splice(i, 1);
        continue;
      }
      p.mesh.position.lerpVectors(p.a, p.b, p.t);
      const s = 0.8 + Math.sin(p.t * Math.PI) * 0.5;
      p.mesh.scale.set(1, 1, s);
    }
    if (packets.length < 40 && Math.random() < 0.6) spawnPacket(false);
    if (sim.activeThreats.size && Math.random() < 0.35) spawnPacket(true);
  }

  function markNodeAlert(node) {
    const mesh = Array.from(nodeData.keys()).find((m) => m.userData.node === node);
    if (!mesh) return;
    const d = nodeData.get(mesh);
    d.mat.color.set(0xff4d6a);
    d.mat.emissive.set(0xff2d55);
    d.mat.emissiveIntensity = 0.85;
    d.halo.material.color.set(0xff4d6a);
    d.halo.material.opacity = 0.5;
    updateLabel(node);
  }

  function markNodeClean(node) {
    const mesh = Array.from(nodeData.keys()).find((m) => m.userData.node === node);
    if (!mesh) return;
    const d = nodeData.get(mesh);
    const base = baseColorInt(node);
    d.mat.color.setHex(base);
    d.mat.emissive.setHex(base);
    d.mat.emissiveIntensity = 0.35;
    d.halo.material.color.setHex(base);
    d.halo.material.opacity = 0.22;
    updateLabel(node);
  }

  function updateNodeMats() {
    topo.nodes.forEach((n) => {
      if (n.compromised) markNodeAlert(n);
      else markNodeClean(n);
    });
  }

  function updateLabel(node) {
    const mesh = Array.from(nodeData.keys()).find((m) => m.userData.node === node);
    if (!mesh) return;
    const d = nodeData.get(mesh);
    const col = node.compromised ? '#ffb3c0' : '#cfe3ff';
    d.mesh.children.filter((c) => c.isSprite && c !== d.halo).forEach((c) => {
      c.material.map.dispose();
      c.material.map = labelTexture(node.name, col);
      c.material.needsUpdate = true;
    });
  }

  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let dragging = false;
  let lastX = 0, lastY = 0;
  let rotY = 0.6, rotX = -0.12, zoomDist = 17, autoRot = true, hovered = null;

  function toNDC(e) {
    const rect = renderer.domElement.getBoundingClientRect();
    ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  }

  renderer.domElement.addEventListener('pointerdown', (e) => {
    dragging = true;
    autoRot = false;
    lastX = e.clientX;
    lastY = e.clientY;
  });
  window.addEventListener('pointermove', (e) => {
    toNDC(e);
    if (dragging) {
      rotY += (e.clientX - lastX) * 0.005;
      rotX = clamp(rotX + (e.clientY - lastY) * 0.004, -1.25, 0.55);
      lastX = e.clientX;
      lastY = e.clientY;
    }
  });
  window.addEventListener('pointerup', () => {
    dragging = false;
    setTimeout(() => (autoRot = true), 3500);
  });
  renderer.domElement.addEventListener('wheel', (e) => {
    e.preventDefault();
    zoomDist = clamp(zoomDist * (e.deltaY > 0 ? 1.07 : 0.93), 7, 26);
  }, { passive: false });
  renderer.domElement.addEventListener('click', (e) => {
    toNDC(e);
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(nodeMeshes, false);
    if (hits.length) showInspector(hits[0].object.userData.node, hits[0].object);
    else showInspector(null);
  });

  function animate() {
    requestAnimationFrame(animate);
    if (autoRot && !dragging) rotY += 0.0014;

    const cx = zoomDist * Math.cos(rotX) * Math.sin(rotY);
    const cy = zoomDist * Math.sin(rotX);
    const cz = zoomDist * Math.cos(rotX) * Math.cos(rotY);
    camera.position.set(cx, cy, cz);
    camera.lookAt(0, 0, 0);

    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(nodeMeshes, false);
    const hit = hits[0] ? hits[0].object : null;
    if (hit !== hovered) {
      if (hovered) {
        const d = nodeData.get(hovered);
        const n = hovered.userData.node;
        const base = baseColorInt(n);
        d.mat.emissive.setHex(base);
        d.mat.emissiveIntensity = n.compromised ? 0.85 : 0.35;
        d.halo.scale.set(2.4, 2.4, 1);
      }
      hovered = hit;
      renderer.domElement.style.cursor = hit ? 'pointer' : 'grab';
      if (hit) {
        const d = nodeData.get(hit);
        d.mat.emissive.setHex(0xffffff);
        d.mat.emissiveIntensity = 1;
        d.halo.scale.set(3.2, 3.2, 1);
      }
    }

    const t = performance.now() * 0.001;
    nodeData.forEach((d) => {
      const n = d.node;
      const freq = n.compromised ? 5.5 : 1.2;
      const pulse = n.compromised ? 0.22 : 0.07;
      const s = 1 + Math.sin(t * freq + n.x) * pulse;
      d.mesh.scale.setScalar(s);
      d.mesh.rotation.y = t * 0.4 + n.z;
    });

    glowLight.position.x = Math.sin(t * 0.25) * 10;
    glowLight.position.z = Math.cos(t * 0.25) * 10;
    glowLight.position.y = 3 + Math.sin(t * 0.4) * 2;
    stars.rotation.y = t * 0.008;

    updatePackets(0.016);
    renderer.render(scene, camera);
  }

  /* =====================================================================
   * UI - KPIs
   * ===================================================================== */
  const sparkCtxs = {};
  document.querySelectorAll('.kpi-spark').forEach((cv) => {
    sparkCtxs[cv.dataset.kpi] = cv.getContext('2d');
  });

  function drawSpark(key, color) {
    const ctx = sparkCtxs[key];
    if (!ctx) return;
    const w = ctx.canvas.width, h = ctx.canvas.height;
    ctx.clearRect(0, 0, w, h);
    const data = sim.history[key] || [];
    if (data.length < 2) return;
    const min = Math.min.apply(null, data);
    const max = Math.max.apply(null, data);
    const span = max - min || 1;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - 3 - ((v - min) / span) * (h - 6);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.18;
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function renderKPIs() {
    $('kpi-events').textContent = fmt(sim.counters.events);
    $('kpi-threats').textContent = sim.activeThreats.size;
    $('kpi-blocked').textContent = fmt(sim.counters.blocked);
    $('kpi-latency').textContent = Math.round(sim.counters.latency);
    $('kpi-badlogon').textContent = sim.counters.badlogon;
    $('kpi-auth').textContent = sim.counters.authRate + '%';
    $('kpi-load').textContent = Math.round(sim.counters.load) + '%';
    $('kpi-packets').textContent = fmt(sim.counters.packets);
    $('auth-fill').style.width = sim.counters.authRate + '%';
    $('load-fill').style.width = sim.counters.load + '%';

    $('hc-evtx').textContent = 'EVTX ' + fmt(HIST_EVTX.length);
    $('hc-login-fail').textContent = 'LOGIN-FAIL ' + loginStats.fail;

    const bars = $('kpi-threat-bars');
    bars.innerHTML = '';
    const n = Math.max(sim.activeThreats.size, 0);
    for (let i = 0; i < Math.max(n, 1); i++) {
      const b = document.createElement('i');
      if (i >= n) { b.style.background = 'rgba(255,255,255,0.06)'; b.style.opacity = 1; }
      b.style.height = (8 + Math.random() * 24) + 'px';
      bars.appendChild(b);
    }

    drawSpark('events', '#53e6ff');
    drawSpark('blocked', '#7b8cff');
    drawSpark('latency', '#ffc44d');
    drawSpark('packets', '#2fd7a8');
    drawSpark('badlogon', '#ff4d6a');

    $('hud-nodes').innerHTML = 'nodes <b>' + topo.nodes.length + '</b>';
    $('hud-links').innerHTML = 'links <b>' + topo.links.length + '</b>';
    $('hud-pkts').innerHTML = 'packets <b>' + packets.length + '</b>';
  }

  /* =====================================================================
   * UI - log feeds
   * ===================================================================== */
  const feed = $('feed');
  const MAX_FEED = 50;

  function renderFeed(entry) {
    sim.activeThreats.forEach((id) => {
      const h = topo.nodes.find((x) => x.id === id);
      if (h && !h.compromised) markNodeClean(h);
    });

    const item = document.createElement('li');
    item.className = 'feed-item sev-' + entry.severity;
    item.innerHTML =
      '<span class="ts">' + entry.ts + '</span>' +
      '<span class="sev-label">' + entry.severity.toUpperCase().slice(0, 4) + '</span>' +
      '<span class="f-msg"><b>' + entry.type + '</b> · ' + entry.host +
      ' <span class="sev-note">(' + entry.ip + ')</span></span>';
    feed.prepend(item);
    while (feed.children.length > MAX_FEED) feed.removeChild(feed.lastChild);
    item.addEventListener('click', () => {
      const h = topo.nodes.find((x) => x.name === entry.host);
      if (h) showInspector(h);
    });
  }

  /* ---- EVTX feed ---- */
  const evtxFeed = $('evtx-feed');
  let evtxFilter = 'all';
  const EVTX_TRIM = 45;

  function renderEVTX(e) {
    if (e.eid === 1102) {
      evtxFeed.innerHTML = '';
    }
    const item = document.createElement('li');
    item.className = 'evtx-item lvl-' + e.level;
    item.innerHTML =
      '<span class="e-id">' + e.eid + '</span>' +
      '<div>' +
      '<div class="evtx-meta"><span class="ts">' + e.ts + '</span><span class="evtx-src">' + e.src + '</span></div>' +
      '<div class="evtx-msg">' + e.msg + '</div>' +
      (e.detail ? '<div class="evtx-detail">' + e.detail + '</div>' : '') +
      '</div>';
    evtxFeed.prepend(item);
    evtxFeed.querySelectorAll('li').forEach((li, i) => { if (i > EVTX_TRIM) li.remove(); });
    item.addEventListener('click', () => {
      showDetail(toLogStr(e));
    });
  }

  /* ---- App log feed ---- */
  const appFeed = $('app-feed');
  let appFilter = 'all';
  const APP_SVC_GROUP = { Apache: 'web', Nginx: 'web', MySQL: 'db', BIND: 'dns', Firewall: 'fw' };

  function renderApp(a) {
    const item = document.createElement('li');
    item.className = 'app-item lvl-' + a.lvl;
    item.innerHTML =
      '<span class="lvl">' + a.lvl.toUpperCase() + '</span>' +
      '<div><span class="svc">[' + a.svc + ']</span> <span class="a-msg">' + a.msg + '</span></div>';
    appFeed.prepend(item);
    appFeed.querySelectorAll('li').forEach((li, i) => { if (i > 40) li.remove(); });
  }

  /* ---- Login feed ---- */
  const loginFeed = $('login-feed');
  const loginChartCtx = $('login-chart').getContext('2d');

  function renderLogin(l) {
    const item = document.createElement('li');
    item.className = 'login-item ' + l.outcome;
    const stat = l.outcome === 'ok' ? 'OK' : l.outcome === 'fail' ? 'FAIL' : 'LOCK';
    item.innerHTML =
      '<span class="ts">' + l.ts + '</span>' +
      '<span class="stat">' + stat + '</span>' +
      '<div>' +
      '<span class="l-user">' + l.user + '</span> <span class="svc">via ' + l.proto + ' (' + l.type + ')</span>' +
      '<div class="l-detail">src ' + l.srcIP + ' → ' + l.dst + (l.reason ? ' | ' + l.reason : '') + '</div>' +
      '</div>';
    loginFeed.prepend(item);
    loginFeed.querySelectorAll('li').forEach((li, i) => { if (i > 40) li.remove(); });

    $('login-success').textContent = loginStats.ok + ' succ';
    $('login-fail').textContent = loginStats.fail + ' fail';
    $('login-locked').textContent = loginStats.lock + ' lockout';
  }

  function drawLoginChart() {
    const w = loginChartCtx.canvas.width, h = loginChartCtx.canvas.height;
    loginChartCtx.clearRect(0, 0, w, h);
    const data = loginFailPerTick;
    if (data.length === 0) return;
    const max = Math.max.apply(null, data.concat([1]));
    const bw = w / 60;
    data.forEach((v, i) => {
      const bh = Math.max(2, (v / max) * (h - 8));
      const x = w - (data.length - i) * bw;
      loginChartCtx.fillStyle = v === 0 ? 'rgba(255,255,255,0.10)' : 'rgba(255,77,106,0.85)';
      loginChartCtx.fillRect(x, h - bh, bw - 2, bh);
    });
    loginChartCtx.strokeStyle = 'rgba(255,77,106,0.35)';
    loginChartCtx.beginPath();
    loginChartCtx.moveTo(0, h - 1);
    loginChartCtx.lineTo(w, h - 1);
    loginChartCtx.stroke();
  }

  function toLogStr(e) {
    return '[' + (e.ts || timeStr()) + '] ' + e.src + ' - ' + e.msg + (e.detail ? '\n' + e.detail : '');
  }

  /* ---- Netflow / DNS / EDR / VULN / INTEL render ---- */
  function renderTraffic() {
    const wrap = $('proto-break');
    if (!wrap) return;
    wrap.innerHTML = '';
    const entries = Object.entries(traffic.proto).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
    const total = entries.reduce((s, [, v]) => s + v, 0);
    for (const [name, v] of entries) {
      const row = document.createElement('div');
      row.className = 'proto-row';
      const pct = total ? Math.round((v / total) * 100) : 0;
      row.innerHTML =
        '<span class="p-name">' + name + '</span>' +
        '<div class="proto-bar"><i style="width:' + pct + '%"></i></div>' +
        '<span class="p-num">' + pct + '%</span>';
      wrap.appendChild(row);
    }
    $('flow-bytes').textContent = (traffic.bytes / 1024).toFixed(1) + ' KB';
    $('flow-sessions').textContent = traffic.sessions + ' sess';

    const talkersUl = $('talkers');
    talkersUl.innerHTML = '';
    Object.entries(talkerBytes)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .forEach(([ip, bytes]) => {
        const rec = HIST_FLOW.find((f) => f.srcIP === ip);
        const li = document.createElement('li');
        li.className = 'talker';
        li.innerHTML =
          '<span title="' + ip + '">' + ip + '</span>' +
          '<span class="t-bytes">' + fmt(bytes) + ' B</span>' +
          '<span class="t-proto">' + (rec ? rec.proto : '?') + '</span>';
        talkersUl.appendChild(li);
      });
  }

  function renderDns(e) {
    const ul = $('dns-list');
    const li = document.createElement('li');
    li.className = 'dns-item';
    li.innerHTML =
      '<span class="d-name">' + e.qname + '</span>' +
      '<span class="d-rcode ' + (e.rcode === 'NXDOMAIN' ? 'nx' : 'ok') + '">' + e.rcode + '</span>' +
      '<span class="d-count">' + e.type + '</span>';
    ul.prepend(li);
    while (ul.children.length > 20) ul.removeChild(ul.lastChild);
    const rate = dnsAgg.total ? Math.round((dnsAgg.nxdomain / dnsAgg.total) * 100) : 0;
    $('nx-rate').textContent = 'NXDOMAIN ' + rate + '%';
  }

  function renderEDR(d) {
    const ul = $('edr-list');
    const li = document.createElement('li');
    li.className = 'edr-item';
    li.innerHTML =
      '<span class="e-tech">' + d.technique + '</span>' +
      '<div><div class="e-msg">' + d.name + ' &middot; ' + d.det + '</div>' +
      '<div class="e-dim">' + d.host + ' | ' + d.process + ' | sha256&hellip;' + d.hash + ' | ' + d.verdict + '</div></div>';
    ul.prepend(li);
    while (ul.children.length > 20) ul.removeChild(ul.lastChild);
    $('edr-count').textContent = HIST_EDR.length + ' detections';
  }

  function renderVuln(v) {
    const ul = $('vuln-list');
    const li = document.createElement('li');
    li.className = 'vuln-item' + (v.cvss >= 9 ? ' high' : '');
    li.innerHTML =
      '<span class="v-cve">' + v.cve + ' (v' + v.cvss.toFixed(1) + ')</span>' +
      '<div><div>' + v.pkg + ' @ :' + v.port + '</div>' +
      '<div class="v-dim">' + v.host + ' | ' + v.status + '</div></div>';
    ul.prepend(li);
    while (ul.children.length > 15) ul.removeChild(ul.lastChild);
    $('vuln-count').textContent = HIST_VULN.length + ' vulns';
  }

  function renderIntel() {
    const bars = $('intel-bars');
    if (!bars) return;
    bars.innerHTML = '';
    const agg = {};
    INTEL.forEach((i) => { agg[i.country] = (agg[i.country] || 0) + 1; });
    Object.entries(agg)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 7)
      .forEach(([c, n]) => {
        const row = document.createElement('div');
        row.className = 'intel-row';
        const pct = Math.min(100, n * 14);
        row.innerHTML =
          '<span class="i-code">' + c + '</span>' +
          '<div class="intel-bar"><i style="width:' + pct + '%"></i></div>' +
          '<span class="i-num">' + n + '</span>';
        bars.appendChild(row);
      });
  }

  function updateSources() {
    $('ps-siem').textContent = HIST.length;
    $('ps-evtx').textContent = HIST_EVTX.length;
    $('ps-apps').textContent = HIST_APP.length;
    $('ps-auth').textContent = loginStats.ok + loginStats.fail + loginStats.lock;
    $('ps-flow').textContent = traffic.sessions;
    $('ps-dns').textContent = dnsAgg.total;
    $('ps-edr').textContent = HIST_EDR.length;
    $('ps-vuln').textContent = HIST_VULN.length;
    $('ps-intel').textContent = INTEL.length;
  }

  /* =====================================================================
   * UI - tabs & filters
   * ===================================================================== */
  function bindTabs() {
    document.querySelectorAll('#tabs-bar .tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#tabs-bar .tab').forEach((b) => b.classList.toggle('active', b === btn));
        document.querySelectorAll('#tab-stage .tab-panel').forEach((p) => {
          p.classList.toggle('active', p.id === 'tab-' + btn.dataset.tab);
        });
      });
    });

    const filterMap = null;
    function bindFilter(id, applyFilter) {
      document.querySelectorAll(id + ' .chip').forEach((c) => {
        c.addEventListener('click', () => {
          applyFilter(c.dataset.filter);
          document.querySelectorAll(id + ' .chip').forEach((x) => x.classList.toggle('active', x === c));
        });
      });
    }
    bindFilter('#evtx-filters', (f) => {
      evtxFilter = f;
      rebuildEVTX();
    });
    bindFilter('#app-filters', (f) => {
      appFilter = f;
      rebuildApp();
    });
  }

  function rebuildEVTX() {
    evtxFeed.innerHTML = '';
    let shown = 0;
    for (const e of HIST_EVTX) {
      if (evtxFilter !== 'all' && e.log.toLowerCase() !== evtxFilter) continue;
      if (shown++ >= EVTX_TRIM) break;
      const item = document.createElement('li');
      item.className = 'evtx-item lvl-' + e.level;
      item.innerHTML =
        '<span class="e-id">' + e.eid + '</span>' +
        '<div>' +
        '<div class="evtx-meta"><span class="ts">' + e.ts + '</span><span class="evtx-src">' + e.src + '</span></div>' +
        '<div class="evtx-msg">' + e.msg + '</div>' +
        (e.detail ? '<div class="evtx-detail">' + e.detail + '</div>' : '') +
        '</div>';
      evtxFeed.appendChild(item);
    }
  }

  function rebuildApp() {
    appFeed.innerHTML = '';
    let shown = 0;
    for (const a of HIST_APP) {
      if (appFilter !== 'all' && APP_SVC_GROUP[a.svc] !== appFilter) continue;
      if (shown++ >= 40) break;
      const item = document.createElement('li');
      item.className = 'app-item lvl-' + a.lvl;
      item.innerHTML =
        '<span class="lvl">' + a.lvl.toUpperCase() + '</span>' +
        '<div><span class="svc">[' + a.svc + ']</span> <span class="a-msg">' + a.msg + '</span></div>';
      appFeed.appendChild(item);
    }
  }

  /* =====================================================================
   * UI - inspector
   * ===================================================================== */
  function showInspector(node) {
    const body = $('insp-body');
    if (!node) {
      body.className = 'muted';
      body.textContent = 'Click a node or a log entry in the 3D scene to inspect it.';
      return;
    }
    body.className = '';
    const sev = node.compromised ? 'critical' : node.alertSev;
    const risk = node.compromised ? 'badge crit' : 'badge ' + (node.alertSev ? 'warn' : 'ok');
    const alerts = HIST.filter((a) => a.host === node.name).length;
    const logins = HIST_LOGIN.filter((l) => l.dst === node.name).length;
    body.innerHTML =
      '<h3>' + node.name + '</h3>' +
      '<div class="kv"><span>Type</span><span>' + node.type + '</span></div>' +
      '<div class="kv"><span>IP</span><span>' + node.ip + '</span></div>' +
      '<div class="kv"><span>Status</span><span>' + (node.compromised ? 'COMPROMISED' : 'NOMINAL') + '</span></div>' +
      '<div class="kv"><span>Links</span><span>' + (topo.links.filter(l => l.a === node.id || l.b === node.id).length) + '</span></div>' +
      '<div class="kv"><span>Correlated alerts</span><span>' + alerts + '</span></div>' +
      '<div class="kv"><span>Login events</span><span>' + logins + '</span></div>' +
      '<div class="insp-row">' +
      '<span class="' + risk + '">' + (sev || 'secure') + '</span>' +
      '<span class="badge">' + node.type + '</span>' +
      '</div>';
  }

  function showDetail(text) {
    const d = $('insp-body');
    d.className = '';
    d.innerHTML = '<h3>Log Detail</h3><div style="font-family:var(--mono);font-size:11px;white-space:pre-wrap;">' + text + '</div>';
  }

  // clock
  setInterval(() => { $('clock').textContent = timeStr(); }, 1000);
  $('clock').textContent = timeStr();

  /* =====================================================================
   * Boot
   * ===================================================================== */
  buildTopology();
  buildLinks();
  renderTraffic();
  renderIntel();
  updateSources();
  bindTabs();

  /* ---- HTML report export ---- */
  const toast = $('toast');
  let toastTimer;
  function toastMsg(msg, isErr) {
    toast.className = isErr ? 'show err' : 'show';
    toast.innerHTML = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.className = ''; }, 3200);
  }

  $('btn-report').addEventListener('click', async () => {
    toastMsg('Generating report&hellip;');
    try {
      const html = buildHTMLReport(collectReportData());
      const res = await window.socApp.saveReportHtml(html, 'SOC-Report-' + tsStamp() + '.html');
      if (res.canceled) toastMsg('Report export cancelled');
      else toastMsg('Report saved: <span class="ok">' + res.filePath + '</span>');
    } catch (err) {
      toastMsg('Report failed: ' + (err && err.message ? err.message : err), true);
    }
  });

  setInterval(() => {
    stepSim();
    updateNodeMats();
    renderKPIs();
  }, 1000);

  window.addEventListener('resize', () => {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  animate();

  function collectReportData() {
    const talkers = Object.entries(talkerBytes)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([ip, bytes]) => {
        const rec = HIST_FLOW.find((f) => f.srcIP === ip);
        return { ip, bytes, proto: rec ? rec.proto : '?' };
      });
    const intel = {};
    INTEL.forEach((i) => { intel[i.country] = (intel[i.country] || 0) + 1; });
    return {
      generatedAt: new Date().toString(),
      version: '1.2.0',
      tick: sim.tick,
      counters: Object.assign({}, sim.counters),
      hist: HIST.slice(0, 40),
      histEvtx: HIST_EVTX.slice(0, 40),
      histApp: HIST_APP.slice(0, 30),
      histLogin: HIST_LOGIN.slice(0, 40),
      loginStats: Object.assign({}, loginStats),
      loginPrc: loginFailPerTick.slice(),
      evtxCounters: Object.assign({}, evtxCounters),
      traffic: { proto: Object.assign({}, traffic.proto), bytes: traffic.bytes, sessions: traffic.sessions },
      talkers,
      dnsAgg: Object.assign({}, dnsAgg),
      topDomains: Object.entries(dnsAgg.domains).sort((a, b) => b[1] - a[1]).slice(0, 8),
      histFlow: HIST_FLOW.slice(0, 30),
      histEdr: HIST_EDR.slice(0, 30),
      histVuln: HIST_VULN.slice(0, 25),
      intel,
      nodes: topo.nodes.map((n) => ({
        name: n.name, type: n.type, ip: n.ip,
        compromised: !!n.compromised,
        links: topo.links.filter((l) => l.a === n.id || l.b === n.id).length
      }))
    };
  }

  window.__soc = { sim, topo, HIST, HIST_EVTX, HIST_APP, HIST_LOGIN, HIST_FLOW, HIST_DNS, HIST_EDR, HIST_VULN, INTEL, showInspector, showDetail, collectReportData };
})();