/* ============================================================
   SOC ALERT TRIAGE DASHBOARD - Data Engine
   Severity Scoring & Deduplication
   ============================================================ */

/* ---------- Alert Data Store ---------- */
const SOCData = (() => {
  'use strict';

  /* ---------- Constants ---------- */
  const SEVERITY_LEVELS = {
    CRITICAL: { min: 9.0, max: 10.0, label: 'Critical', order: 5 },
    HIGH:     { min: 7.0, max: 8.9,  label: 'High',     order: 4 },
    MEDIUM:   { min: 4.0, max: 6.9,  label: 'Medium',   order: 3 },
    LOW:      { min: 2.0, max: 3.9,  label: 'Low',      order: 2 },
    INFO:     { min: 0.0, max: 1.9,  label: 'Info',     order: 1 }
  };

  const SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'Info'];

  /* ---------- Sample Data Generation ---------- */
  const SOURCES = [
    { name: 'Suricata', baseWeight: 0.9, categories: ['Network', 'Exploit', 'C2'] },
    { name: 'CrowdStrike', baseWeight: 0.95, categories: ['Endpoint', 'Malware', 'Ransomware'] },
    { name: 'Splunk', baseWeight: 0.8, categories: ['Authentication', 'Reconnaissance', 'Data Exfil'] },
    { name: 'Windows Defender', baseWeight: 0.85, categories: ['Endpoint', 'Malware', 'Phishing'] },
    { name: 'AWS CloudTrail', baseWeight: 0.75, categories: ['Insider Threat', 'Reconnaissance', 'Authentication'] },
    { name: 'Zeek', baseWeight: 0.7, categories: ['Network', 'Protocol Anomaly', 'C2'] }
  ];

  const THREAT_TEMPLATES = [
    {
      type: 'Brute Force Attack', mitre: 'T1110', category: 'Authentication',
      threatWeight: 0.8,
      titles: [
        'Multiple failed login attempts detected from {src}',
        'Brute force attack against SSH service from {src}',
        'RDP brute force pattern observed from {src}'
      ],
      descriptions: [
        'Alert trigger: {n} failed authentication attempts from {src} towards {dst} within a 10-minute window. This may indicate a credential attack in progress.',
        'Brute force attempt detected: repeated login failures against {dst} originating from {src}. Account lockout policies may have been bypassed.'
      ],
      recommendation: 'Immediately block the source IP at the perimeter firewall. Implement account lockout policy and enable multi-factor authentication. Review any successful logins that occurred during the attack window.',
      assetPattern: ['Active Directory', 'Email Gateway', 'Web Server', 'File Server', 'Database Server']
    },
    {
      type: 'SQL Injection', mitre: 'T1190', category: 'Exploit',
      threatWeight: 0.9,
      titles: [
        'SQL injection attempt detected from {src}',
        'SQLi payload in HTTP request from {src} against {dst}'
      ],
      descriptions: [
        'Web application firewall detected SQL injection patterns in requests from {src} to {dst}. Probe strings include UNION SELECT and OR 1=1 patterns.',
        'Multiple SQL injection attempts logged from {src}. The requests appear to target login forms and search functionality on {dst}.'
      ],
      recommendation: 'Verify web application input validation. Review database logs for unauthorized queries. Patch vulnerable endpoints immediately. Consider deploying a Web Application Firewall (WAF).',
      assetPattern: ['Web Server', 'Database Server', 'API Gateway']
    },
    {
      type: 'Malware Detection', mitre: 'T1204', category: 'Malware',
      threatWeight: 0.85,
      titles: [
        'Malware signature detected on {dst}', 
        'Suspicious executable downloaded and executed on {dst}'
      ],
      descriptions: [
        'Endpoint protection identified malware signature "{sig}" on {dst}. The file was delivered from {src} and has been quarantined.',
        'Heuristic analysis flagged untrusted executable behavior on {dst}. Process "svchost_tmp.exe" attempted to modify registry keys and establish persistence.'
      ],
      recommendation: 'Isolate the affected endpoint immediately. Extract and submit the malware sample to the sandbox for analysis. Check for lateral movement using network forensics.',
      assetPattern: ['Workstation', 'Server', 'Laptop', 'Endpoint']
    },
    {
      type: 'Phishing Campaign', mitre: 'T1566', category: 'Phishing',
      threatWeight: 0.7,
      titles: [
        'Phishing email detected from {src}',
        'Malicious attachment received from {src} at {dst}'
      ],
      descriptions: [
        'Email security gateway flagged {n} phishing emails from {src} addressed to users at {dst}. The emails contain links to credential harvesting pages.',
        'Spear-phishing attempt detected: email from {src} contains a malicious macro-enabled document targeting {dst} employees.'
      ],
      recommendation: 'Notify affected users. Block the sender domain. Add indicators to email filter blocks. Verify with users whether any links were clicked or attachments opened.',
      assetPattern: ['Users', 'Email Gateway', 'Human Resources', 'Finance Department']
    },
    {
      type: 'C2 Communication', mitre: 'T1071', category: 'C2',
      threatWeight: 0.95,
      titles: [
        'Command and Control beacon detected from {dst}',
        'C2 server communication observed from {dst}'
      ],
      descriptions: [
        'Network monitoring detected regular beaconing behavior from {dst} to {src} with consistent intervals and payload sizes characteristic of C2 communication.',
        'DNS tunneling detected: {dst} is making unusual DNS queries to {src} with encoded payloads in subdomains, indicating covert C2 channel.'
      ],
      recommendation: 'Contain the infected host by isolating it from the network. Capture full packet capture for analysis. Block the C2 domain/IP at the firewall and DNS sinkhole.',
      assetPattern: ['Workstation', 'Server', 'Laptop']
    },
    {
      type: 'Ransomware Activity', mitre: 'T1486', category: 'Ransomware',
      threatWeight: 1.0,
      titles: [
        'Ransomware encryption activity detected on {dst}',
        'Ransom note creation observed on {dst}'
      ],
      descriptions: [
        'Endpoint monitoring detected mass file encryption on {dst}. Multiple file extensions changed and ransom notes are being written. Likely ransomware infection from {src}.',
        'Behavioral detection flagged process on {dst} for encrypting files at high velocity. Investigation suggests ransomware strain distributed from {src}.'
      ],
      recommendation: 'IMMEDIATELY disconnect the affected host from the network. Preserve evidence (memory and disk images). Identify the ransomware family. Check backup integrity and restore from clean backups.',
      assetPattern: ['File Server', 'Database Server', 'Workstation', 'Domain Controller']
    },
    {
      type: 'Data Exfiltration', mitre: 'T1041', category: 'Data Exfil',
      threatWeight: 0.9,
      titles: [
        'Suspicious data transfer detected from {dst} to {src}',
        'Large outbound data volume to {src}'
      ],
      descriptions: [
        'Data loss prevention flagged {n} MB of sensitive data being transferred from {dst} to {src} over FTP/HTTP in a short timeframe.',
        'DNS exfiltration suspected: {dst} transmitting encoded data to {src} via DNS queries, bypassing traditional DLP controls.'
      ],
      recommendation: 'Block the external destination immediately. Investigate which data was accessed. Check for credential compromise. Review DLP policies and consider egress filtering.',
      assetPattern: ['Database Server', 'File Server', 'Workstation']
    },
    {
      type: 'Privilege Escalation', mitre: 'T1068', category: 'Lehmann',
      threatWeight: 0.85,
      titles: [
        'Privilege escalation attempt detected on {dst}',
        'Unexpected admin access obtained by {src}'
      ],
      descriptions: [
        'Security logs show {src} performed a privilege escalation on {dst}. Process invoked with elevated privileges without proper authorization chain.',
        'Local privilege escalation exploit detected on {dst}. Exploit technique matches known vulnerability exploitation from {src}.'
      ],
      recommendation: 'Audit the affected account\'s activity. Verify whether escalation was legitimate. Patch the exploited vulnerability. Enable sysmon or equivalent for detailed process logging.',
      assetPattern: ['Domain Controller', 'Server', 'Workstation']
    },
    {
      type: 'Reconnaissance Scan', mitre: 'T1595', category: 'Reconnaissance',
      threatWeight: 0.55,
      titles: [
        'Port scan detected from {src}',
        'Network reconnaissance activity from {src}'
      ],
      descriptions: [
        'IDS observed a full TCP SYN scan from {src} against {dst} covering {n} ports. This is typically the precursor to an attack.',
        'Service enumeration attempts from {src} detected. Multiple port probes against {dst} included fingerprinting signatures.'
      ],
      recommendation: 'Block the scanning IP. Increase monitoring on targeted services. Correlate with other SOC data to determine if this is automated scanning or targeted reconnaissance.',
      assetPattern: ['Network Segment', 'DMZ', 'Web Server']
    },
    {
      type: 'Anomalous Login', mitre: 'T1078', category: 'Authentication',
      threatWeight: 0.75,
      titles: [
        'Login from unusual location by user {src}',
        'Impossible travel login detected for {src}'
      ],
      descriptions: [
        'User {src} logged into {dst} from a geographically impossible location. Previous login 10 minutes prior was from a different country. Possible account compromise.',
        'Off-hours login detected: account {src} accessed {dst} at unusual hour. No prior access pattern matches this behavior.'
      ],
      recommendation: 'Verify the login with the user. Force password reset and session termination if unauthorized. Enable conditional access policies. Monitor for further anomalous activity.',
      assetPattern: ['Active Directory', 'Cloud Console', 'Email Gateway']
    },
    {
      type: 'Unusual DNS Query', mitre: 'T1048', category: 'Reconnaissance',
      threatWeight: 0.35,
      titles: [
        'Unusual DNS query observed from {src}',
        'Rare DNS record request from {src} to {dst}'
      ],
      descriptions: [
        'DNS log analysis flagged {src} querying an unusual domain record to {dst}. The domain is not in the safe list and has low reputation.',
        'Algorithmically generated domain (DGA) candidate found in DNS log from {src}. Domain pattern matches known malware families.'
      ],
      recommendation: 'Investigate the user device for malware that uses DGA. Verify the query source. Add the domain to the block list pending review.',
      assetPattern: ['Workstation', 'Laptop', 'Endpoint']
    },
    {
      type: 'Failed Login Audit', mitre: 'T1110', category: 'Authentication',
      threatWeight: 0.3,
      titles: [
        'Repeated failed logins on {dst}',
        'Password spray behavior against {dst}'
      ],
      descriptions: [
        'Audit log shows a pattern of {n} failed login attempts against {dst} from {src}. Small number of passwords across many accounts indicates password spraying.',
        'Lockout threshold reached for multiple accounts on {dst}. Source of attempts: {src}.'
      ],
      recommendation: 'Reset affected accounts. Verify no successful logins followed the failures. Enable audit logging and alerting on lockout events.',
      assetPattern: ['Active Directory', 'Email Gateway', 'VPN Gateway']
    },
    {
      type: 'Protocol Anomaly', mitre: 'T1046', category: 'Network',
      threatWeight: 0.4,
      titles: [
        'Protocol anomaly detected from {src}',
        'Non-standard protocol behavior targeting {dst}'
      ],
      descriptions: [
        'Zeek detected anomalous protocol behavior: packets from {src} to {dst} violate expected RFC grammar on configured ports.',
        'Traffic analysis flagged {src} sending malformed protocol frames to {dst}, suggesting fingerprinting or exploit scanning.'
      ],
      recommendation: 'Inspect the flow for payload data. Correlate with other sources. Block the anomalous traffic if confirmed malicious.',
      assetPattern: ['Network Segment', 'DMZ', 'Load Balancer']
    },
    {
      type: 'Configuration Drift', mitre: 'T1574', category: 'Security Posture',
      threatWeight: 0.3,
      titles: [
        'Security configuration drift detected on {dst}',
        'Firewall rule change requiring review on {dst}'
      ],
      descriptions: [
        'Configuration management detected unauthorized change to security policy on {dst}. Drift from the baseline configuration exceeded the allowed threshold.',
        'Endpoint protection state changed on {dst}: real-time protection disabled or version out of date. Change originated from {src}.'
      ],
      recommendation: 'Verify the change against the change management process. Restore the baseline configuration if unauthorized. Harden the affected host.',
      assetPattern: ['Firewall', 'Server', 'Endpoint']
    },
    {
      type: 'Suspicious URL Click', mitre: 'T1566', category: 'Phishing',
      threatWeight: 0.45,
      titles: [
        'User clicked flagged URL from {src}',
        'Blocked URL access attempt by {dst} via {src}'
      ],
      descriptions: [
        'Web proxy blocked repeated access attempts from {dst} to a URL associated with {src}. The URL matches a phishing or malware campaign pattern.',
        'DLP/web gateway flagged {dst} visiting a credential harvesting page referenced by {src}.'
      ],
      recommendation: 'Ask the user about the email/page context. Check for subsequent credential compromise. Block the domain and any related infrastructure.',
      assetPattern: ['Workstation', 'Laptop', 'Users']
    }
  ];

  const IP_POOL = [
    '45.33.21.8', '91.213.124.7', '185.220.101.34', '103.79.77.2',
    '210.4.78.34', '198.51.100.10', '203.0.113.45', '192.168.10.15',
    '10.0.2.44', '172.16.8.5', '194.26.192.5', '89.248.168.12',
    '104.236.18.3', '162.244.8.101', '45.155.205.23', '192.168.10.66',
    '10.0.3.15', '172.16.4.22', '80.82.65.122', '5.183.211.5'
  ];

  /* Severity factor weights (total = 1.0) */
  const FACTOR_WEIGHTS = {
    source: 0.25,
    threat: 0.30,
    asset: 0.20,
    temporal: 0.15,
    context: 0.10
  };

  let alertCounter = 0;
  let dedupGroups = new Map();
  let dedupIndex = new Map();
  let alertsStore = [];

  /* ---------- Utility functions ---------- */
  function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0;
    }
    return Math.abs(hash).toString(36);
  }

  function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function randomFloat(min, max) {
    return Math.random() * (max - min) + min;
  }

  function randomPick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function randomIP(fromPool = true) {
    if (fromPool && Math.random() > 0.3) return randomPick(IP_POOL);
    return `${randomInt(1, 223)}.${randomInt(0, 255)}.${randomInt(0, 255)}.${randomInt(1, 254)}`;
  }

  function pad2(n) { return n.toString().padStart(2, '0'); }

  function formatTime(ts) {
    const d = new Date(ts);
    return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
  }

  function timeAgo(date) {
    const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  function relativeTime(date) {
    return timeAgo(date);
  }

  /* ---------- Severity Scoring Engine ---------- */
  function scoreFromSeverity(severity) {
    const s = SEVERITY_LEVELS[severity] || SEVERITY_LEVELS.INFO;
    return randomFloat(s.min, s.max);
  }

  function clampScore(v) {
    return Math.min(10, Math.max(0.5, parseFloat(v.toFixed(2))));
  }

  function calculateSeverityScore(alert) {
    // jitter in [-1, 1] derived from per-alert intensity
    const j = ((alert.intensity || 0.5) - 0.5) * 2;

    /* Factor 1: Source credibility (0-10) */
    let sourceWeight = 5.0;
    const sourceMeta = SOURCES.find(s => s.name === alert.dataSource);
    if (sourceMeta) sourceWeight = sourceMeta.baseWeight * 10;
    if (alert.dataSource === 'Unknown') sourceWeight = 3;
    sourceWeight = clampScore(sourceWeight + j * 3.5);

    /* Factor 2: Threat type weight (0-10) */
    let threatWeight = 5.0;
    const template = THREAT_TEMPLATES.find(t => t.type === alert.threatType);
    if (template) threatWeight = template.threatWeight * 10;
    threatWeight = clampScore(threatWeight + j * 4.0);

    /* Factor 3: Asset criticality (0-10) */
    let assetWeight = 5.0;
    const criticalAssets = ['Domain Controller', 'Database Server', 'File Server'];
    if (alert.asset) {
      if (criticalAssets.includes(alert.asset)) assetWeight = 9;
      else if (alert.asset === 'Web Server') assetWeight = 7.5;
      else if (alert.asset === 'API Gateway') assetWeight = 7;
      else if (alert.asset.includes('Server')) assetWeight = 6.5;
      else assetWeight = 5;
    }
    assetWeight = clampScore(assetWeight + j * 2.5);

    /* Factor 4: Temporal recency (0-10) - newer = higher */
    const ageHours = (Date.now() - new Date(alert.timestamp).getTime()) / 3600000;
    let temporalWeight = Math.max(2, 10 - (ageHours * 0.5));
    temporalWeight = clampScore(temporalWeight + j * 1.5);

    /* Factor 5: Context score (0-10) */
    let contextWeight = 5.0;
    if (alert.isDuplicate) contextWeight = 3;
    else if (alert.status === 'Investigating') contextWeight = 7;
    else if (alert.status === 'Resolved') contextWeight = 4;
    else if (alert.status === 'False Positive') contextWeight = 1.5;
    else contextWeight = 6;
    contextWeight = clampScore(contextWeight + j * 2.0);

    /* Store factor values for breakdown display */
    alert._factors = {
      source: sourceWeight,
      threat: threatWeight,
      asset: assetWeight,
      temporal: temporalWeight,
      context: contextWeight
    };

    /* Compute weighted final score */
    const weightedScore =
      sourceWeight * FACTOR_WEIGHTS.source +
      threatWeight * FACTOR_WEIGHTS.threat +
      assetWeight * FACTOR_WEIGHTS.asset +
      temporalWeight * FACTOR_WEIGHTS.temporal +
      contextWeight * FACTOR_WEIGHTS.context;

    return clampScore(weightedScore);
  }

  function scoreToSeverity(score) {
    const levels = Object.entries(SEVERITY_LEVELS);
    for (const [key, val] of levels) {
      if (score >= val.min && score <= val.max) return val.label;
    }
    if (score > 10) return 'Critical';
    return 'Info';
  }

  function getScoreColor(score) {
    if (score >= 9) return 'var(--sev-critical)';
    if (score >= 7) return 'var(--sev-high)';
    if (score >= 4) return 'var(--sev-medium)';
    if (score >= 2) return 'var(--sev-low)';
    return 'var(--sev-info)';
  }

  /* ---------- Deduplication Engine ---------- */
  function generateFingerprint(alert) {
    return hashString(
      `${alert.sourceIP}|${alert.destIP}|${alert.threatType}|${alert.dataSource}`
    );
  }

  function titleSimilarity(a, b) {
    const norm = (s) => s.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(Boolean);
    const aWords = norm(a), bWords = norm(b);
    if (aWords.length === 0 || bWords.length === 0) return 0;
    const setA = new Set(aWords), setB = new Set(bWords);
    const intersect = [...setA].filter(w => setB.has(w)).length;
    return intersect / Math.sqrt(setA.size * setB.size);
  }

  function performDeduplication(alerts) {
    dedupIndex.clear();
    dedupGroups.clear();
    let groupCounter = 0;

    for (const alert of alerts) {
      const fp = generateFingerprint(alert);
      const match = dedupIndex.get(fp);

      if (match) {
        // Exact fingerprint match found - check time window (60 min)
        const timeWindowMs = 3600000;
        const timeDiff = Math.abs(new Date(alert.timestamp).getTime() - match.timestamp);
        const titleSim = titleSimilarity(alert.title, match.alertTitle);

        if (timeDiff < timeWindowMs || titleSim > 0.8) {
          alert.isDuplicate = true;
          alert.duplicateOf = match.alertId;
          alert.dedupGroup = match.groupId;
          match.count++;
          match.latestTimestamp = alert.timestamp;
          const group = dedupGroups.get(match.groupId);
          if (group) {
            group.count = match.count;
            group.alerts.push(alert.id);
          }
          continue;
        }
      }

      // Not a duplicate - register as new
      alert.isDuplicate = false;
      alert.duplicateOf = null;
      alert.dedupGroup = ++groupCounter;
      dedupIndex.set(fp, {
        alertId: alert.id,
        alertTitle: alert.title,
        timestamp: new Date(alert.timestamp).getTime(),
        count: 1,
        groupId: groupCounter
      });
      dedupGroups.set(groupCounter, {
        id: groupCounter,
        representative: alert.id,
        count: 1,
        alerts: [alert.id]
      });
    }

    // Update dedup counters on all alerts
    for (const alert of alerts) {
      if (!alert.isDuplicate && alert.dedupGroup) {
        const group = dedupGroups.get(alert.dedupGroup);
        alert.dupCount = group ? group.count - 1 : 0;
      } else {
        alert.dupCount = 0;
      }
    }

    return { dedupGroups, dedupIndex };
  }

  /* ---------- Alert Generation ---------- */
  function generateAlerts(count = 480) {
    const alerts = [];
    const now = Date.now();

    /* Build realistic "campaign" clusters to exercise the dedup engine:
       multiple alerts share attacker IP / target IP / threat type within
       a short time window. ~70% of alerts are part of campaigns. */
    const numCampaigns = Math.max(8, Math.round(count * 0.24));
    const campaignAlerts = Math.round(count * 0.7);
    let alertsMade = 0;

    for (let c = 0; c < numCampaigns && alertsMade < count; c++) {
      const template = randomPick(THREAT_TEMPLATES);
      const sourceMeta = randomPick(SOURCES);
      const attackerIP = randomIP(true);
      const numTargets = randomInt(1, 3);
      const targets = Array.from({ length: numTargets }, () => randomIP(Math.random() < 0.5));
      const campaignSize = randomInt(4, Math.min(12, Math.max(3, Math.round((count - alertsMade) * (0.7 / numCampaigns)) + 3)));
      const campaignStart = now - randomInt(10, 1200) * 60000 * 0.5;
      const isInternalSrc = Math.random() < 0.2;
      const sourceIP = isInternalSrc ? randomIP(false) : attackerIP;

      for (let k = 0; k < campaignSize && alertsMade < count; k++) {
        const destIP = randomPick(targets);
        const intensity = randomFloat(0.12, 0.95);

        const title = randomPick(template.titles)
          .replace('{src}', sourceIP)
          .replace('{dst}', destIP);

        const asset = randomPick(template.assetPattern);
        const status = randomPick(['New', 'New', 'New', 'Investigating', 'Resolved', 'False Positive']);

        const alert = {
          id: `ALT-${String(++alertCounter).padStart(4, '0')}`,
          timestamp: new Date(campaignStart + k * randomInt(2, 5) * 60000).toISOString(),
          title: title,
          description: randomPick(template.descriptions)
            .replace('{src}', sourceIP)
            .replace('{dst}', destIP)
            .replace('{n}', String(randomInt(5, 120))),
          sourceIP: sourceIP,
          destIP: destIP,
          ports: randomInt(80, 65535),
          category: template.category,
          threatType: template.type,
          dataSource: sourceMeta.name,
          asset: asset,
          mitre: template.mitre,
          status: status,
          recommendation: template.recommendation,
          intensity: parseFloat(intensity.toFixed(2)),
          isDuplicate: false,
          duplicateOf: null,
          dedupGroup: null,
          dupCount: 0,
          severity: null,
          severityScore: null,
          factors: null
        };

        alerts.push(alert);
        alertsMade++;
      }
    }

    /* Remaining alerts as standalone / unique events (~30%) */
    while (alertsMade < count) {
      const template = randomPick(THREAT_TEMPLATES);
      const sourceMeta = randomPick(SOURCES);
      const sourceIP = randomIP(Math.random() < 0.5);
      const destIP = randomIP(Math.random() < 0.5);
      const intensity = randomFloat(0.10, 0.95);

      const title = randomPick(template.titles)
        .replace('{src}', sourceIP)
        .replace('{dst}', destIP);

      const alert = {
        id: `ALT-${String(++alertCounter).padStart(4, '0')}`,
        timestamp: new Date(now - randomInt(5, 1000) * 60000).toISOString(),
        title: title,
        description: randomPick(template.descriptions)
          .replace('{src}', sourceIP)
          .replace('{dst}', destIP)
          .replace('{n}', String(randomInt(5, 120))),
        sourceIP: sourceIP,
        destIP: destIP,
        ports: randomInt(80, 65535),
        category: template.category,
        threatType: template.type,
        dataSource: sourceMeta.name,
        asset: randomPick(template.assetPattern),
        mitre: template.mitre,
        status: randomPick(['New', 'New', 'New', 'Investigating', 'Resolved', 'False Positive']),
        recommendation: template.recommendation,
        intensity: parseFloat(intensity.toFixed(2)),
        isDuplicate: false,
        duplicateOf: null,
        dedupGroup: null,
        dupCount: 0,
        severity: null,
        severityScore: null,
        factors: null
      };

      alerts.push(alert);
      alertsMade++;
    }

    // Calculate severity scores
    for (const alert of alerts) {
      const baseScore = calculateSeverityScore(alert);
      alert.severityScore = baseScore;
      alert.severity = scoreToSeverity(baseScore);
      alert.factors = computeFactorBreakdown(alert);
    }

    // Perform deduplication
    performDeduplication(alerts);

    alertsStore = alerts;
    return alerts;
  }

  function computeFactorBreakdown(alert) {
    const f = alert._factors || {};
    const criticalAssets = ['Domain Controller', 'Database Server', 'File Server'];

    const reusable = (key, label, note) => ({
      label,
      value: f[key] != null ? f[key] : 5,
      weight: FACTOR_WEIGHTS[key],
      note
    });

    return {
      source: reusable('source', 'Source', `${alert.dataSource} credibility`),
      threat: reusable('threat', 'Threat', alert.threatType),
      asset: reusable('asset', 'Asset', alert.asset),
      temporal: reusable('temporal', 'Recency', ageNote(alert.timestamp)),
      context: reusable('context', 'Context', alert.status === 'New' ? 'Unverified' : alert.status)
    };
  }

  function ageNote(timestamp) {
    const ageHours = (Date.now() - new Date(timestamp).getTime()) / 3600000;
    if (ageHours < 1) return 'Fresher than 1h';
    return `${Math.round(ageHours)}h old`;
  }

  /* ---------- Query Operations ---------- */
  function getAlerts() { return alertsStore; }

  function refreshAlerts() {
    const fresh = generateAlerts(alertsStore.length || 480);
    return fresh;
  }

  /* ---------- Exports ---------- */
  return {
    generateAlerts,
    getAlerts,
    refreshAlerts,
    calculateSeverityScore,
    scoreToSeverity,
    getScoreColor,
    performDeduplication,
    generateFingerprint,
    SEVERITY_LEVELS,
    SEVERITY_ORDER,
    SOURCES,
    hashString,
    formatTime,
    timeAgo,
    relativeTime,
    randomInt
  };
})();

if (typeof window !== 'undefined') {
  window.SOCData = SOCData;
}