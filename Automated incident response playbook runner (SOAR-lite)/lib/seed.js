'use strict';

const STEP_TYPES = [
  'notify', 'enrich', 'extract', 'quarantine', 'block', 'collect',
  'command', 'decision', 'escalate', 'wait', 'resolve'
];

function seed(state, { uid, now, daysAgo }) {
  // ------------------------------------------------------------------ playbooks
  const playbooks = [
    {
      id: 'pb_phishing', name: 'Phishing Triage & Response', version: 3,
      description: 'Validate a reported phishing email, extract IoCs, block C2 endpoints and notify the user.',
      category: 'phishing', severityMin: 'medium', active: true,
      errorPolicy: 'stop',
      tags: ['email', 'phishing', 'user-reported'],
      createdAt: daysAgo(30), updatedAt: daysAgo(2),
      postAction: { incidentStatus: 'resolved', note: 'Phishing incident remediated by playbook.' },
      steps: [
        { id: 's1', type: 'extract', name: 'Extract indicators from email', params: { fields: 'IOC_EMAIL,IOC_URL,IOC_HASH' } },
        { id: 's2', type: 'enrich', name: 'Enrich sender & URL reputation', params: { source: 'threat-intel', field: 'url' } },
        { id: 's3', type: 'decision', name: 'Verify maliciousness', params: { field: 'reputation', op: 'eq', value: 'malicious', branch: { match: 's4', noMatch: 's7' } } },
        { id: 's4', type: 'block', name: 'Block phishing URL at proxy', params: { device: 'sec-proxy-01', ioc: 'url' } },
        { id: 's5', type: 'command', name: 'Delete email from mailbox', params: { host: 'exch-mbx-02', cmd: 'remove-email -site <user> -subject <subject>' } },
        { id: 's6', type: 'notify', name: 'Notify user & SOC channel', params: { channel: 'slack-soc', targets: 'user, soc-team' } },
        { id: 's7', type: 'resolve', name: 'Mark remediated', params: { note: 'IOC block & mailbox cleanup confirmed.' } }
      ]
    },
    {
      id: 'pb_compromised', name: 'Compromised Account Response', version: 2,
      description: 'Contain a compromised user account: isolate, reset, sweep sessions and verify no data exfiltration.',
      category: 'account', severityMin: 'high', active: true,
      errorPolicy: 'continue',
      tags: ['identity', 'account', 'impossible-travel'],
      createdAt: daysAgo(25), updatedAt: daysAgo(1),
      postAction: { incidentStatus: 'resolved', note: 'Account secured and sessions revoked.' },
      steps: [
        { id: 's1', type: 'quarantine', name: 'Isolate endpoint & disable account', params: { host: '<hostname>', action: 'restrict-login' } },
        { id: 's2', type: 'command', name: 'Revoke active sessions', params: { host: 'idp-01', cmd: 'revoke-sessions -user <account>' } },
        { id: 's3', type: 'collect', name: 'Gather sign-in & OAuth audit logs', params: { target: 'azure-ad,okta' } },
        { id: 's4', type: 'decision', name: 'Exfiltration check', params: { field: 'signin_geo', op: 'eq', value: 'foreign', branch: { match: 's5', noMatch: 's6' } } },
        { id: 's5', type: 'escalate', name: 'Escalate - possible data theft', params: { priority: 'critical', assignee: 'orchestrator' } },
        { id: 's6', type: 'notify', name: 'Notify account owner & manager', params: { channel: 'email', targets: 'owner,manager' } },
        { id: 's7', type: 'resolve', name: 'Confirm containment', params: { note: 'Sessions revoked; creds reset; monitoring 7 days.' } }
      ]
    },
    {
      id: 'pb_malware', name: 'Malware Outbreak Containment', version: 4,
      description: 'Contain a host-based malware outbreak: isolate endpoints, block C2, sweep and rebuild if required.',
      category: 'malware', severityMin: 'medium', active: true,
      errorPolicy: 'continue',
      tags: ['malware', 'edr', 'containment'],
      createdAt: daysAgo(20), updatedAt: daysAgo(3),
      postAction: { incidentStatus: 'resolved', note: 'Outbreak contained and hosts reimaged.' },
      steps: [
        { id: 's1', type: 'collect', name: 'Collect EDR telemetry & process dumps', params: { target: 'edr-fleet' } },
        { id: 's2', type: 'enrich', name: 'Enrich malware hash', params: { source: 'vt-mirror', field: 'hash' } },
        { id: 's3', type: 'extract', name: 'Extract C2 & file hashes', params: { fields: 'IOC_HASH,IOC_DOMAIN,IOC_IP' } },
        { id: 's4', type: 'quarantine', name: 'Isolate infected endpoints', params: { host: '<host>', action: 'network-isolate' } },
        { id: 's5', type: 'block', name: 'Block C2 domains & IPs', params: { device: 'ngfw-edge, dns-01', ioc: 'domain,ip' } },
        { id: 's6', type: 'command', name: 'Kill & remove malware process', params: { host: '<host>', cmd: 'terminate -proc <process> -purge' } },
        { id: 's7', type: 'decision', name: 'Rootkit detection', params: { field: 'edr_rootkit', op: 'eq', value: 'true', branch: { match: 's8', noMatch: 's9' } } },
        { id: 's8', type: 'escalate', name: 'Reimage affected host', params: { priority: 'high', assignee: 'sysadmins' } },
        { id: 's9', type: 'notify', name: 'Notify security stakeholders', params: { channel: 'slack-soc', targets: 'gold-customer-shield' } },
        { id: 's10', type: 'resolve', name: 'Confirm containment & log closure', params: { note: 'C2 blocked; hosts clean or reimaged.' } }
      ]
    },
    {
      id: 'pb_network', name: 'Network Anomaly Investigation', version: 1,
      description: 'Investigate suspicious north-south traffic, correlate with firewall logs and contain rogue connections.',
      category: 'network', severityMin: 'low', active: false,
      errorPolicy: 'stop',
      tags: ['network', 'anomaly', 'north-south'],
      createdAt: daysAgo(15), updatedAt: daysAgo(10),
      postAction: { incidentStatus: 'resolved', note: 'Anomaly investigated and traffic validated.' },
      steps: [
        { id: 's1', type: 'enrich', name: 'Enrich destination IPs', params: { source: 'greynoise', field: 'ip' } },
        { id: 's2', type: 'collect', name: 'Pull firewall & netflow evidence', params: { target: 'firewall-a, netflow-b' } },
        { id: 's3', type: 'decision', name: 'Check against known C2 list', params: { field: 'cnc_badge', op: 'eq', value: 'true', branch: { match: 's4', noMatch: 's5' } } },
        { id: 's4', type: 'block', name: 'Block rogue connections', params: { device: 'firewall-a', ioc: 'ip' } },
        { id: 's5', type: 'notify', name: 'Notify network team', params: { channel: 'email', targets: 'netops' } },
        { id: 's6', type: 'resolve', name: 'Close with findings', params: { note: 'Traffic validated against threat intel.' } }
      ]
    }
  ];

  // ------------------------------------------------------------------ incidents
  const mkInc = (id, title, category, severity, status, ageDays, assignee, artifacts, source) => ({
    id, title, category, severity, status, assignee, source: source || 'SIEM',
    description: `Automated notification for correlated ${category} signals. Enrichment and response coordinated by SOAR-Lite.`,
    artifacts,
    createdAt: daysAgo(ageDays, 8 + (ageDays % 7)),
    updatedAt: daysAgo(Math.max(ageDays - 1, 0), 14),
    relatedPlaybook: null
  });

  const incidents = [
    mkInc('inc_1', 'Phishing: fake Office 365 login page', 'phishing', 'high', 'closed', 13, 'analyst.jane', [
      { type: 'ip', value: '45.133.4.17' }, { type: 'url', value: 'hxxp://account-verify-m365.tk/login' }, { type: 'email', value: 'billing@securecheck.tk' }
    ], 'email'),
    mkInc('inc_2', 'Brute-force spike on SSH bastion', 'brute-force', 'medium', 'resolved', 12, 'analyst.jane', [
      { type: 'ip', value: '103.97.8.210' }, { type: 'ip', value: '185.220.101.1', tag: 'TOR' }
    ]),
    mkInc('inc_3', 'Ransomware beacon detected on host CO-LAP-034', 'malware', 'critical', 'open', 11, null, [
      { type: 'hash', value: 'ba7c3f5f8a5d9c0c2f7e1b4a8d9e6f3c', tag: 'ransomware' }, { type: 'domain', value: 'dropgate.pw' }, { type: 'ip', value: '185.141.24.99' }
    ]),
    mkInc('inc_4', 'Impossible travel sign-in for hr.global@acme', 'account', 'high', 'in_progress', 10, 'analyst.kofi', [
      { type: 'account', value: 'hr.global' }, { type: 'ip', value: '93.184.7.33', tag: 'foreign' }, { type: 'geo', value: 'RU' }
    ]),
    mkInc('inc_5', 'Data exfiltration attempt via cloud sync', 'data-exfil', 'critical', 'in_progress', 9, 'analyst.kofi', [
      { type: 'account', value: 'finance.lead' }, { type: 'domain', value: 'storage-public.cloudp.io' }
    ]),
    mkInc('inc_6', 'Malicious document macro execution', 'malware', 'high', 'resolved', 8, 'analyst.jane', [
      { type: 'hash', value: '41e2bf1a2b9c...' , tag: 'macro' }, { type: 'domain', value: 'macro-doc.example' }
    ]),
    mkInc('inc_7', 'Dual-use tool download flagged (Mimikatz)', 'insider', 'medium', 'open', 7, null, [
      { type: 'hash', value: '8a2b9f...' }, { type: 'account', value: 'anya.dev' }
    ]),
    mkInc('inc_8', 'Suspicious TLS beacon to novel domain', 'network', 'medium', 'resolved', 6, 'analyst.kofi', [
      { type: 'ip', value: '162.159.134.13' }, { type: 'domain', value: 'technews-nowz.xyz' }
    ]),
    mkInc('inc_9', 'Phishing: fake payroll notification', 'phishing', 'medium', 'resolved', 5, 'analyst.jane', [
      { type: 'url', value: 'hxxp://payroll-pulse-24.tk/login' }, { type: 'email', value: 'hr.payroll@strikeapps.tk' }
    ]),
    mkInc('inc_10', 'Vault password dump posted on paste site', 'data-exfil', 'critical', 'new', 4, null, [
      { type: 'domain', value: 'pastebin-dump.example' }, { type: 'account', value: 'svc_vault_ro' }
    ]),
    mkInc('inc_11', 'Endpoint isolation alert - crypto miner', 'malware', 'medium', 'in_progress', 3, 'analyst.kofi', [
      { type: 'hash', value: 'c9f2e11d...', tag: 'miner' }, { type: 'ip', value: '212.129.32.80' }
    ]),
    mkInc('inc_12', 'Recon scan against public web farm', 'network', 'low', 'resolved', 2, 'analyst.jane', [
      { type: 'ip', value: '198.47.120.95' }
    ]),
    mkInc('inc_13', 'Okta user enumeration sweep', 'account', 'medium', 'new', 1, null, [
      { type: 'ip', value: '45.155.205.233' }, { type: 'account', value: 'idp-bulk-probe' }
    ]),
    mkInc('inc_14', 'Phishing: fake Azure MFA challenge', 'phishing', 'high', 'new', 0, null, [
      { type: 'url', value: 'hxxp://secure-ms-authportal.tk/verify' }, { type: 'email', value: 'alerts@ms-auth-support.tk' }, { type: 'ip', value: '91.219.236.89' }
    ])
  ];

  // relate some incidents to playbooks
  incidents[0].relatedPlaybook = 'pb_phishing';
  incidents[2].relatedPlaybook = 'pb_malware';
  incidents[3].relatedPlaybook = 'pb_compromised';
  incidents[5].relatedPlaybook = 'pb_malware';
  incidents[8].relatedPlaybook = 'pb_phishing';
  incidents[13].relatedPlaybook = 'pb_phishing';

  // ------------------------------------------------------------------ historical runs
  const stepTmpl = (s) => ({ id: s.id, type: s.type, name: s.name, status: 'success', startedAt: null, endedAt: null, duration: Math.round(600 + Math.random() * 1600), output: {} });
  const mkRun = (id, pb, inc, status, ageDays, trigger, stepsOut) => ({
    id, playbookId: pb.id, playbookName: pb.name, incidentId: inc ? inc.id : null,
    incidentTitle: inc ? inc.title : null,
    trigger, status, startedAt: daysAgo(ageDays, 9), finishedAt: daysAgo(ageDays, 9),
    steps: stepsOut, logs: [{ t: daysAgo(ageDays, 9), l: 'info', m: `Playbook "${pb.name}" finished with status ${status}.` }]
  });

  const baseDelays = [900, 1100, 1300, 1500, 1700];
  function runSteps(pb, ageDays) {
    return pb.steps.map((s, i) => ({
      id: s.id, type: s.type, name: s.name, status: 'success',
      startedAt: daysAgo(ageDays, 9), endedAt: daysAgo(ageDays, 9),
      duration: baseDelays[i % baseDelays.length] + Math.round(Math.random() * 800),
      output: {}
    }));
  }

  const runs = [
    mkRun('run_1', playbooks[0], incidents[0], 'success', 13, 'auto', runSteps(playbooks[0], 13)),
    mkRun('run_2', playbooks[2], incidents[2], 'failed', 11, 'auto', (() => {
      const st = runSteps(playbooks[2], 11);
      st[3].status = 'failed'; st[3].error = 'EDR agent offline: host CO-LAP-034 unreachable';
      st[4].status = 'failed'; st[4].error = 'Skipped segment (errorPolicy=continue)';
      return st;
    })()),
    mkRun('run_3', playbooks[1], incidents[3], 'success', 10, 'auto', runSteps(playbooks[1], 10)),
    mkRun('run_4', playbooks[2], incidents[5], 'success', 8, 'manual', runSteps(playbooks[2], 8)),
    mkRun('run_5', playbooks[3], incidents[7], 'success', 6, 'auto', runSteps(playbooks[3], 6)),
    mkRun('run_6', playbooks[0], incidents[8], 'success', 5, 'auto', runSteps(playbooks[0], 5)),
    mkRun('run_7', playbooks[3], incidents[11], 'success', 2, 'manual', runSteps(playbooks[3], 2))
  ];

  // ------------------------------------------------------------------ activity
  const act = (type, title, detail, ageDays) => ({ id: uid('evt'), type, title, detail, ts: daysAgo(ageDays, 9 + (ageDays % 3)) });
  const activity = [
    act('run', 'Playbook "Phishing Triage & Response" completed (auto)', 'inc_1 · 7 steps · success', 13),
    act('incident', 'Critical incident opened', 'inc_3 · Ransomware beacon detected on host CO-LAP-034', 11),
    act('run', 'Playbook "Malware Outbreak Containment" failed', 'inc_3 · EDR agent offline', 11),
    act('incident', 'High severity incident escalated', 'inc_4 · Impossible travel sign-in', 10),
    act('run', 'Playbook "Compromised Account Response" completed (auto)', 'inc_4 · 7 steps · success', 10),
    act('incident', 'Critical incident opened', 'inc_5 · Data exfiltration attempt via cloud sync', 9),
    act('run', 'Playbook "Phishing Triage & Response" completed (auto)', 'inc_9 · 7 steps · success', 5),
    act('incident', 'Critical incident opened', 'inc_10 · Vault password dump posted on paste site', 4),
    act('incident', 'New incident ingested', 'inc_14 · Phishing: fake Azure MFA challenge', 1)
  ];

  state.playbooks = playbooks;
  state.incidents = incidents;
  state.runs = runs;
  state.activity = activity.concat(state.activity || []);
  return state;
}

module.exports = { seed, STEP_TYPES };