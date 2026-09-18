'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, '..', 'data');
const STATE_FILE = path.join(DATA_DIR, 'soar.json');

let state = null;

function uid(prefix) {
  return prefix + '_' + crypto.randomBytes(6).toString('hex').slice(0, 12);
}

function now() {
  return new Date().toISOString();
}

function daysAgo(n, hourOffset) {
  const d = new Date(Date.now() - n * 86400000);
  if (hourOffset) d.setUTCHours(hourOffset, Math.floor(Math.random() * 50) + 5, 0, 0);
  return d.toISOString();
}

function load() {
  try {
    state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch (e) {
    state = null;
  }
}

function ensure() {
  if (!state) {
    load();
    if (!state) throw new Error('Store not initialised. Call storeOrLoad() first.');
  }
}

function save() {
  ensure();
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  const tmp = STATE_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(state, null, 2));
  fs.renameSync(tmp, STATE_FILE);
}

function storeOrLoad(seedFn) {
  load();
  if (!state) {
    state = {
      meta: { seededAt: now(), version: '1.0.0' },
      settings: {
        autoRun: true,
        engineStatus: 'online',
        webhookUrl: '',
        operator: 'SOC-Desk'
      },
      playbooks: [],
      incidents: [],
      runs: [],
      activity: []
    };
    if (seedFn) seedFn(state, { uid, now, daysAgo });
    save();
  }
  return state;
}

function addActivity(type, title, detail) {
  ensure();
  const evt = { id: uid('evt'), type, title, detail: detail || '', ts: now() };
  state.activity.unshift(evt);
  if (state.activity.length > 500) state.activity.length = 500;
  save();
  return evt;
}

function getState() {
  ensure();
  return state;
}

module.exports = { uid, now, daysAgo, storeOrLoad, save, addActivity, getState };