export const SEVERITIES = {
  critical: { label: 'Critical', color: '#ff3860' },
  high: { label: 'High', color: '#ff9f1a' },
  medium: { label: 'Medium', color: '#ffd166' },
  low: { label: 'Low', color: '#06d6a0' }
};

export const ATTACK_TYPES = [
  'Ransomware',
  'DDoS Attack',
  'Phishing',
  'Credential Stuffing',
  'SQL Injection',
  'Malware',
  'Zero-Day Exploit',
  'IoT Botnet',
  'Supply Chain',
  'Insider Threat',
  'Brute Force',
  'Data Exfiltration'
];

const CLUSTERS = [
  { type: 'Ransomware', sev: ['critical', 'high', 'high', 'medium'], verbs: ['encrypted', 'locked down', 'exfiltrated', 'took offline'] },
  { type: 'DDoS Attack', sev: ['high', 'high', 'medium'], verbs: ['flooded', 'knocked offline', 'volumetric-surged', 'hit'] },
  { type: 'Phishing', sev: ['medium', 'medium', 'low', 'high'], verbs: ['harvested', 'targeted', 'spoofed', 'compromised'] },
  { type: 'Credential Stuffing', sev: ['high', 'medium', 'medium'], verbs: ['replayed', 'compromised', 'stormed'] },
  { type: 'SQL Injection', sev: ['high', 'critical', 'medium'], verbs: ['injected', 'extracted', 'dumped'] },
  { type: 'Malware', sev: ['medium', 'high', 'low'], verbs: ['propagated', 'infected', 'dropped'] },
  { type: 'Zero-Day Exploit', sev: ['critical', 'critical', 'high'], verbs: ['exploited', 'weaponized', 'chained'] },
  { type: 'IoT Botnet', sev: ['medium', 'high', 'low'], verbs: ['recruited', 'enslaved', 'amplified'] },
  { type: 'Supply Chain', sev: ['critical', 'high', 'high'], verbs: ['poisoned', 'inserted', 'backdoored'] },
  { type: 'Insider Threat', sev: ['medium', 'high', 'low'], verbs: ['leaked', 'sold', 'mishandled'] },
  { type: 'Brute Force', sev: ['medium', 'low', 'high'], verbs: ['hammered', 'cracked', 'assaulted'] },
  { type: 'Data Exfiltration', sev: ['critical', 'high', 'medium'], verbs: ['stole', 'siphoned', 'pillaged'] }
];

const CITIES = [
  { city: 'New York', cc: 'USA', lat: 40.71, lon: -74.01 },
  { city: 'San Francisco', cc: 'USA', lat: 37.77, lon: -122.42 },
  { city: 'Los Angeles', cc: 'USA', lat: 34.05, lon: -118.24 },
  { city: 'Chicago', cc: 'USA', lat: 41.88, lon: -87.63 },
  { city: 'Miami', cc: 'USA', lat: 25.76, lon: -80.19 },
  { city: 'Austin', cc: 'USA', lat: 30.27, lon: -97.74 },
  { city: 'Seattle', cc: 'USA', lat: 47.61, lon: -122.33 },
  { city: 'Toronto', cc: 'CAN', lat: 43.65, lon: -79.38 },
  { city: 'Mexico City', cc: 'MEX', lat: 19.43, lon: -99.13 },
  { city: 'Bogota', cc: 'COL', lat: 4.71, lon: -74.07 },
  { city: 'Sao Paulo', cc: 'BRA', lat: -23.55, lon: -46.63 },
  { city: 'Rio de Janeiro', cc: 'BRA', lat: -22.91, lon: -43.17 },
  { city: 'Buenos Aires', cc: 'ARG', lat: -34.6, lon: -58.38 },
  { city: 'Lima', cc: 'PER', lat: -12.05, lon: -77.04 },
  { city: 'Santiago', cc: 'CHL', lat: -33.45, lon: -70.67 },
  { city: 'London', cc: 'GBR', lat: 51.51, lon: -0.13 },
  { city: 'Paris', cc: 'FRA', lat: 48.86, lon: 2.35 },
  { city: 'Berlin', cc: 'DEU', lat: 52.52, lon: 13.4 },
  { city: 'Amsterdam', cc: 'NLD', lat: 52.37, lon: 4.9 },
  { city: 'Madrid', cc: 'ESP', lat: 40.42, lon: -3.7 },
  { city: 'Lisbon', cc: 'PRT', lat: 38.72, lon: -9.14 },
  { city: 'Rome', cc: 'ITA', lat: 41.9, lon: 12.5 },
  { city: 'Zurich', cc: 'CHE', lat: 47.38, lon: 8.54 },
  { city: 'Stockholm', cc: 'SWE', lat: 59.33, lon: 18.07 },
  { city: 'Oslo', cc: 'NOR', lat: 59.91, lon: 10.75 },
  { city: 'Helsinki', cc: 'FIN', lat: 60.17, lon: 24.94 },
  { city: 'Warsaw', cc: 'POL', lat: 52.23, lon: 21.01 },
  { city: 'Prague', cc: 'CZE', lat: 50.08, lon: 14.44 },
  { city: 'Vienna', cc: 'AUT', lat: 48.21, lon: 16.37 },
  { city: 'Bucharest', cc: 'ROU', lat: 44.43, lon: 26.1 },
  { city: 'Kiev', cc: 'UKR', lat: 50.45, lon: 30.52 },
  { city: 'Moscow', cc: 'RUS', lat: 55.76, lon: 37.62 },
  { city: 'Istanbul', cc: 'TUR', lat: 41.01, lon: 28.98 },
  { city: 'Dubai', cc: 'ARE', lat: 25.2, lon: 55.27 },
  { city: 'Tel Aviv', cc: 'ISR', lat: 32.08, lon: 34.78 },
  { city: 'Johannesburg', cc: 'ZAF', lat: -26.2, lon: 28.05 },
  { city: 'Lagos', cc: 'NGA', lat: 6.52, lon: 3.38 },
  { city: 'Nairobi', cc: 'KEN', lat: -1.29, lon: 36.82 },
  { city: 'Cairo', cc: 'EGY', lat: 30.04, lon: 31.24 },
  { city: 'Mumbai', cc: 'IND', lat: 19.08, lon: 72.88 },
  { city: 'Delhi', cc: 'IND', lat: 28.61, lon: 77.21 },
  { city: 'Bengaluru', cc: 'IND', lat: 12.97, lon: 77.59 },
  { city: 'Karachi', cc: 'PAK', lat: 24.86, lon: 67.01 },
  { city: 'Dhaka', cc: 'BGD', lat: 23.81, lon: 90.41 },
  { city: 'Bangkok', cc: 'THA', lat: 13.76, lon: 100.5 },
  { city: 'Ho Chi Minh City', cc: 'VNM', lat: 10.82, lon: 106.63 },
  { city: 'Kuala Lumpur', cc: 'MYS', lat: 3.14, lon: 101.69 },
  { city: 'Singapore', cc: 'SGP', lat: 1.35, lon: 103.82 },
  { city: 'Jakarta', cc: 'IDN', lat: -6.21, lon: 106.85 },
  { city: 'Manila', cc: 'PHL', lat: 14.6, lon: 120.98 },
  { city: 'Beijing', cc: 'CHN', lat: 39.9, lon: 116.41 },
  { city: 'Shanghai', cc: 'CHN', lat: 31.23, lon: 121.47 },
  { city: 'Shenzhen', cc: 'CHN', lat: 22.54, lon: 114.06 },
  { city: 'Hong Kong', cc: 'HKG', lat: 22.32, lon: 114.17 },
  { city: 'Taipei', cc: 'TWN', lat: 25.03, lon: 121.57 },
  { city: 'Seoul', cc: 'KOR', lat: 37.57, lon: 126.98 },
  { city: 'Tokyo', cc: 'JPN', lat: 35.68, lon: 139.69 },
  { city: 'Osaka', cc: 'JPN', lat: 34.69, lon: 135.5 },
  { city: 'Sydney', cc: 'AUS', lat: -33.87, lon: 151.21 },
  { city: 'Melbourne', cc: 'AUS', lat: -37.81, lon: 144.96 },
  { city: 'Auckland', cc: 'NZL', lat: -36.85, lon: 174.76 }
];

const COMPANIES = [
  { name: 'VertexCloud', industry: 'Cloud Hosting' },
  { name: 'NordBank Group', industry: 'Finance' },
  { name: 'MediCare Plus', industry: 'Healthcare' },
  { name: 'FoodHub', industry: 'Logistics' },
  { name: 'PixelWorks Studios', industry: 'Media' },
  { name: 'SkyTel', industry: 'Telecom' },
  { name: 'RetailPro', industry: 'E-Commerce' },
  { name: 'DataStream Analytics', industry: 'Data Services' },
  { name: 'GreenGrid Energy', industry: 'Utilities' },
  { name: 'NovaPay', industry: 'Fintech' },
  { name: 'InsureFirst', industry: 'Insurance' },
  { name: 'GamesVerse', industry: 'Gaming' },
  { name: 'RoadRunner Logistics', industry: 'Transport' },
  { name: 'HarborMyth Shipping', industry: 'Maritime' },
  { name: 'CodeForge', industry: 'Software' },
  { name: 'AtomLedger', industry: 'Blockchain' },
  { name: 'BloomCraft', industry: 'Perfume & Retail' },
  { name: 'OrbitSat Comms', industry: 'Satellite' },
  { name: 'TechNation', industry: 'Electronics' },
  { name: 'VitalAir Pharma', industry: 'Pharma' }
];

const IP_POOL = new Array(36).fill(0).map((_, i) => `203.0.${(i % 9) * 16 + Math.floor(i / 9) * 3}.${Math.floor(Math.random() * 200) + 20}`);

function pick(arr, rng) { return arr[Math.floor(rng() * arr.length)]; }

function fmtIp() { return `${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`; }

let seq = 0;

function makeEvent(now, rng = Math.random) {
  const cluster = pick(CLUSTERS, rng);
  const src = pick(CITIES, rng);
  let dst = pick(CITIES, rng);
  while (dst === src) dst = pick(CITIES, rng);
  const company = pick(COMPANIES, rng);
  const severity = pick(cluster.sev, rng);
  const records = Math.round((Math.pow(rng(), 2.2) * severityFactor(severity) + 40) / 10) * 10;
  const ts = now - Math.floor(rng() * 240000);
  return {
    id: ++seq,
    ts,
    attack: cluster.type,
    verb: pick(cluster.verbs, rng),
    severity,
    src,
    dst,
    company: company.name,
    industry: company.industry,
    records,
    ip: fmtIp(),
    detail: buildDetail(cluster.type, src.city, dst.city, company.name, severity, records, rng)
  };
}

function severityFactor(s) {
  if (s === 'critical') return 140000;
  if (s === 'high') return 40000;
  if (s === 'medium') return 9000;
  return 1800;
}

function buildDetail(type, srcCity, dstCity, company, severity, records, rng) {
  const victims = Math.max(2, Math.round(records / 4000));
  return `${type} detected ${pick(dstCityWeights, rng)} ${srcCity} -> ${dstCity}. ${company} hit, ~${victims}k affected, ${records.toLocaleString()} records cited.`;
}

const dstCityWeights = ['from cluster', 'originating in', 'launched at', 'spotted from', 'tracked from'];

export class ThreatFeed {
  constructor({ interval = 2100, history = 160, rng = Math.random } = {}) {
    this.interval = interval;
    this.rng = rng;
    this.events = [];
    this.listeners = new Set();
    this.paused = false;
    this.timer = null;
    const now = Date.now();
    for (let i = 0; i < history; i++) {
      this.events.push(makeEvent(now - (history - i) * interval * (0.8 + rng() * 0.5), rng));
    }
    this.events.sort((a, b) => a.ts - b.ts);
    this.dispatch = this.dispatch.bind(this);
  }

  start() {
    if (this.timer) return;
    this.timer = setInterval(() => this.dispatch(), this.interval);
    this.timer.unref?.();
  }

  stop() { if (this.timer) { clearInterval(this.timer); this.timer = null; } }

  dispatch() {
    if (this.paused) return;
    const ev = makeEvent(Date.now(), this.rng);
    this.events.push(ev);
    if (this.events.length > 600) this.events.splice(0, this.events.length - 600);
    this.emit(ev);
  }

  on(cb) { this.listeners.add(cb); return () => this.listeners.delete(cb); }
  emit(ev) { for (const cb of this.listeners) cb(ev); }

  setPaused(p) { this.paused = p; return this.paused; }
  togglePaused() { return this.setPaused(!this.paused); }

  getEventsSince(since) { return this.events.filter(e => e.ts >= since); }
  getRecent(count = 60) { return this.events.slice(-count); }
  todaysEvents() {
    const dayAgo = Date.now() - 864e5;
    return this.events.filter(e => e.ts >= dayAgo);
  }
}

export { CITIES, COMPANIES, makeEvent };
export const randomHex = (n = 6) => Array.from({ length: n }, () => '0123456789abcdef'[Math.floor(Math.random() * 16)]).join('');