'use strict';

const store = require('./store');

// Per-process cancellation registry (runs survive restarts only when finished).
const cancellations = new Map();

const SEVERITY = { info: 0, low: 1, medium: 2, high: 3, critical: 4 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rnd = (min, max) => Math.floor(min + Math.random() * (max - min));
const chance = (p) => Math.random() < p;

function stepDelay(step) {
  if (step.type === 'wait' && step.params && step.params.ms) {
    return Math.min(Number(step.params.ms) || 800, 3000);
  }
  return rnd(650, 1900);
}

// --------------------------------------------------------------------------- value resolution
function buildCtx(incident) {
  if (!incident) return { severity: 'medium', category: 'unknown', title: 'no incident' };
  const ctx = {
    title: incident.title || '',
    severity: incident.severity || 'medium',
    category: incident.category || 'unknown',
    status: incident.status || 'new'
  };
  (incident.artifacts || []).forEach((a) => {
    ctx[a.type + '_list'] = ctx[a.type + '_list'] || [];
    ctx[a.type + '_list'].push(a.value);
  });
  return ctx;
}

function resolveField(field, ctx, outputs) {
  if (!field) return undefined;
  if (field.startsWith('output:')) {
    const [stepId, key] = field.slice(7).split('.');
    return outputs[stepId] ? outputs[stepId][key] : undefined;
  }
  if (ctx[field] !== undefined) return ctx[field];
  for (const key of ['title', 'severity', 'category', 'status']) {
    if (field === key) return ctx[key];
  }
  return undefined;
}

function evaluate(value, op, target) {
  switch (op) {
    case 'eq': return String(value) === String(target);
    case 'neq': return String(value) !== String(target);
    case 'contains': return String(value || '').toLowerCase().includes(String(target || '').toLowerCase());
    case 'gt': return parseFloat(value) > parseFloat(target);
    case 'lt': return parseFloat(value) < parseFloat(target);
    case 'exists': return value !== undefined && value !== null && value !== '';
    default: return String(value) === String(target);
  }
}

// --------------------------------------------------------------------------- simulation
function simulateStep(step, ctx, incident) {
  const type = step.type;
  const p = step.params || {};
  const out = { type };
  let logMessage = `${step.name} executed.`;

  switch (type) {
    case 'notify': {
      const channel = p.channel || 'slack-soc';
      out.channel = channel;
      out.messageId = 'msg-' + Math.random().toString(36).slice(2, 8).toUpperCase();
      out.targets = (p.targets || 'soc-team').split(',');
      out.delivered = true;
      logMessage = `Alert pushed to ${channel} (${out.messageId}).`;
      break;
    }
    case 'enrich': {
      const source = p.source || 'threat-intel';
      out.source = source;
      if (source === 'greynoise') {
        out.reputation = chance(0.3) ? 'scanning' : 'benign';
        out.noise = chance(0.5) ? 'noise' : 'benign';
        out.cnc_badge = chance(0.45);
      } else if (source === 'vt-mirror') {
        out.detections = rnd(4, 58);
        out.reputation = out.detections > 20 ? 'malicious' : (chance(0.5) ? 'malicious' : 'suspicious');
        out.score = out.detections;
      } else {
        out.reputation = chance(0.55) ? 'malicious' : (chance(0.5) ? 'suspicious' : 'benign');
        out.score = out.reputation === 'malicious' ? rnd(62, 99) : rnd(4, 45);
        out.relatedSamples = rnd(1, 9);
      }
      logMessage = `${source} lookup: reputation=${out.reputation}, score=${out.score || 'n/a'}.`;
      break;
    }
    case 'extract': {
      const arts = (incident && incident.artifacts) || [];
      out.patterns = (p.fields || 'IOC_IP,IOC_DOMAIN').split(',');
      out.count = arts.length;
      out.indicators = arts.map((a) => `${a.type}:${a.value}`);
      logMessage = `Extracted ${out.count} indicator(s) from incident.`;
      break;
    }
    case 'quarantine': {
      const host = p.host || ctx.hostname || 'endpoint-unknown';
      out.host = host;
      out.action = p.action || 'network-isolate';
      out.isolated = true;
      out.method = 'EDR agent v9';
      logMessage = `Host ${host} isolated (${out.action}) via EDR.`;
      break;
    }
    case 'block': {
      out.ruleId = 'BLK-' + rnd(1000, 9999);
      out.iocType = p.ioc || 'ip';
      out.devices = (p.device || 'ngfw-edge').split(',');
      out.entries = rnd(1, 4);
      out.action = 'blocked';
      logMessage = `Rule ${out.ruleId} pushed to ${out.devices.join(', ')}.`;
      break;
    }
    case 'collect': {
      const target = p.target || 'edr-fleet';
      out.target = target;
      out.sources = target.split(',');
      out.evidence = ['sys.' + rnd(100, 999) + '.evtx', 'netflow.bin', 'proc.dmp'].slice(0, rnd(1, 3));
      if (target.includes('azure-ad') || target.includes('okta')) {
        out.signin_geo = chance(0.6) ? 'foreign' : 'domestic';
        out.risk = chance(0.5) ? 'high' : 'medium';
        out.failedLogons = rnd(0, 24);
      }
      if (target.includes('edr')) {
        out.edr_rootkit = chance(0.3);
        out.hosts_affected = rnd(1, 6);
      }
      if (target.includes('firewall') || target.includes('netflow')) {
        out.cnc_badge = chance(0.5);
        out.sessions = rnd(120, 1800);
      }
      logMessage = `Evidence collected from ${target}.`;
      break;
    }
    case 'command': {
      const cmd = p.cmd || 'investigate';
      const host = p.host || ctx.hostname || 'target-host';
      out.host = host;
      out.command = cmd;
      out.exitCode = chance(0.08) ? 1 : 0;
      out.stdout = out.exitCode === 0
        ? `[ok] ${cmd.replace(/</g, '').replace(/>/g, '').split('-')[0]} completed on ${host}`
        : `[err] command failed on ${host}`;
      logMessage = `Command ran on ${host} (exit ${out.exitCode}).`;
      break;
    }
    case 'decision': {
      const value = resolveField(p.field, ctx, outputsRef());
      const matched = p.field ? evaluate(value, p.op || 'eq', p.value) : true;
      out.field = p.field; out.value = value; out.op = p.op; out.target = p.value;
      out.result = matched ? 'match' : 'no-match';
      out.takenBranch = matched ? (p.branch && p.branch.match) : (p.branch && p.branch.noMatch);
      logMessage = `Decision ${p.field || '-'} "${value || 'missing'}" ${matched ? 'matched' : 'did not match'} ${p.value || 'n/a'}.`;
      break;
    }
    case 'escalate': {
      out.priority = p.priority || 'high';
      out.assignee = p.assignee || 'on-call';
      out.ticketId = 'ESC-' + rnd(10000, 99999);
      out.SLO = '30 min';
      logMessage = `Escalated to ${out.assignee} (${out.priority} priority).`;
      break;
    }
    case 'wait': {
      out.waited = Math.min(Number(p.ms) || 800, 3000);
      logMessage = `Held for ${out.waited}ms.`;
      break;
    }
    case 'resolve':
    default: {
      out.note = p.note || 'Closed by SOAR-Lite playbook.';
      out.resolution = 'resolved';
      logMessage = out.note;
      break;
    }
  }
  return { output: out, logMessage };
}

// live reference to current run outputs for decisions mid-loop
let outputsRef = () => ({});

function describeOutput(out) {
  const frag = [];
  for (const k of ['reputation', 'ruleId', 'host', 'messageId', 'signin_geo', 'edr_rootkit', 'ticketId', 'count', 'result']) {
    if (out && out[k] !== undefined) frag.push(`${k}=${out[k]}`);
  }
  return frag.join('  ');
}

// --------------------------------------------------------------------------- matching
function findMatchingPlaybook(state, incident) {
  const sev = SEVERITY[incident.severity] ?? 2;
  return state.playbooks.find((pb) =>
    pb.active
    && (!pb.severityMin || (SEVERITY[pb.severityMin] ?? 0) <= sev)
    && (!pb.category || pb.category === incident.category)
  );
}

// --------------------------------------------------------------------------- runner
function startRun(state, { playbook, incident, trigger }) {
  const run = {
    id: store.uid('run'),
    playbookId: playbook.id,
    playbookName: playbook.name,
    incidentId: incident ? incident.id : null,
    incidentTitle: incident ? incident.title : null,
    trigger: trigger || 'manual',
    status: 'queued',
    currentStep: null,
    startedAt: null,
    finishedAt: null,
    steps: playbook.steps.map((s) => ({
      id: s.id, type: s.type, name: s.name, status: 'pending', error: null,
      startedAt: null, endedAt: null, duration: null, output: {}
    })),
    logs: []
  };
  state.runs.unshift(run);
  store.save();
  store.addActivity('run', `Playbook "${playbook.name}" ${trigger === 'auto' ? 'auto-started' : 'started'}`, `${run.id} · ${playbook.steps.length} steps`);

  // fire-and-forget execution
  execute(run, playbook, incident);
  return run;
}

async function execute(run, playbook, incident) {
  try {
    const live = store.getState();
    run.startedAt = store.now();
    run.status = 'running';
    run.currentStep = 0;
    addLog(run, 'info', `Execution started (${run.trigger === 'auto' ? 'automatic' : 'manual'} trigger).`);

    const outputs = {};
    outputsRef = () => outputs;
    let idx = 0;
    let failures = 0;

    while (idx != null && idx < playbook.steps.length) {
      if (cancellations.get(run.id) === true) {
        run.status = 'cancelled';
        run.finishedAt = store.now();
        run.currentStep = null;
        addLog(run, 'warn', 'Run cancelled by operator.');
        store.save();
        return;
      }
      const step = playbook.steps[idx];
      const stateStep = run.steps[idx];
      stateStep.status = 'running';
      stateStep.startedAt = store.now();
      run.currentStep = idx;
      addLog(run, 'info', `[${idx + 1}/${playbook.steps.length}] ${step.name} (${step.type})…`);
      store.save();

      const delay = stepDelay(step);
      await sleep(delay);

      const { output, logMessage } = simulateStep(step, buildCtx(incident), incident);
      outputs[step.id] = output;
      stateStep.output = output;
      stateStep.duration = delay;
      stateStep.endedAt = store.now();

      const failRate = step.params && step.params.failRate != null ? Number(step.params.failRate) : 0.06;
      const failed = chance(failRate);

      if (failed) {
        failures++;
        stateStep.status = 'failed';
        stateStep.error = errorMessage(step);
        addLog(run, 'error', `Step failed: ${stateStep.error}`);
        const policy = playbook.errorPolicy || 'stop';
        if (policy === 'continue') {
          addLog(run, 'warn', 'errorPolicy=continue — continuing with next step.');
        } else if (policy === 'abort-incident') {
          if (incident) { incident.status = 'open'; incident.flag = 'aborted-by-playbook'; }
          run.status = 'failed';
          run.finishedAt = store.now();
          run.currentStep = null;
          addLog(run, 'error', 'errorPolicy=abort-incident — incident flagged for manual review.');
          store.save();
          store.addActivity('run', `Playbook "${playbook.name}" aborted incident`, `${run.id} · flagged for manual review`);
          return;
        } else {
          run.status = 'failed';
          run.finishedAt = store.now();
          run.currentStep = null;
          addLog(run, 'error', 'errorPolicy=stop — run halted.');
          store.save();
          store.addActivity('run', `Playbook "${playbook.name}" failed`, `${run.id} · halted at ${step.name}`);
          return;
        }
        idx++;
        continue;
      }

      stateStep.status = 'success';
      addLog(run, 'info', `  OK — ${logMessage}`);
      if (step.type !== 'decision' && output) addLog(run, 'debug', `    ${describeOutput(output)}`);

      if (step.type === 'decision') {
        const matched = output.result === 'match';
        const targetId = matched ? (step.params.branch && step.params.branch.match) : (step.params.branch && step.params.branch.noMatch);
        if (targetId) {
          const ti = playbook.steps.findIndex((s) => s.id === targetId);
          idx = ti === -1 ? idx + 1 : ti;
          addLog(run, 'info', `  Branch → ${matched ? 'match' : 'no-match'} (${targetId}).`);
        } else {
          idx++;
        }
      } else {
        idx++;
      }
      store.save();
    }

    // postAction
    if (playbook.postAction && incident) {
      const pa = playbook.postAction;
      if (pa.incidentStatus) {
        incident.status = pa.incidentStatus;
        incident.resolutionNote = pa.note || 'Resolved by SOAR-Lite.';
        addLog(run, 'info', `Post-action: incident marked "${pa.incidentStatus}".`);
      }
    }

    run.status = failures && playbook.errorPolicy === 'continue' ? 'success_with_warnings' : 'success';
    if (run.status === 'success_with_warnings') addLog(run, 'warn', `Run finished with ${failures} failed step(s).`);
    run.finishedAt = store.now();
    run.currentStep = null;
    addLog(run, 'info', `Playbook completed with status "${run.status}".`);
    store.save();
    store.addActivity('run', `Playbook "${playbook.name}" completed`, `${run.id} · ${playbook.steps.length} steps · ${run.status}`);
  } catch (err) {
    run.status = 'error';
    run.finishedAt = store.now();
    addLog(run, 'error', 'Engine error: ' + (err && err.message ? err.message : err));
    store.save();
  }
}

function errorMessage(step) {
  const msgs = {
    notify: 'Notification provider unreachable (webhook timeout).',
    enrich: 'Threat intel API returned 429 / quota exceeded.',
    extract: 'No parseable indicators found.',
    quarantine: 'EDR agent offline on target host.',
    block: 'Policy push rejected by control point.',
    collect: 'Log source unavailable / credentials rotated.',
    command: 'Command execution timed out on target host.',
    decision: 'Condition evaluation failed.',
    escalate: 'Pager duty API unavailable.',
    resolve: 'Closure ticket creation failed.',
    wait: 'Timeout interrupted by scheduler.'
  };
  return msgs[step.type] || `Step "${step.name}" failed (simulated error).`;
}

function addLog(run, level, message) {
  run.logs.push({ t: store.now(), l: level, m: message });
  if (run.logs.length > 400) run.logs.splice(0, run.logs.length - 400);
}

function cancelRun(run) {
  cancellations.set(run.id, true);
}

function retryRun(state, run, incident) {
  const playbook = state.playbooks.find((p) => p.id === run.playbookId);
  if (!playbook) return null;
  return startRun(state, { playbook, incident, trigger: 'manual' });
}

module.exports = {
  startRun, cancelRun, retryRun, findMatchingPlaybook, cancelMap: cancellations
};