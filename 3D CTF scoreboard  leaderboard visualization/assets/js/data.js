/* ═══════════════════════════════════════════════════════════════════════
   CTF ARENA · deterministic sample data generator
   Produces teams, score history, challenges and per-team solves.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const CATEGORIES = [
    { id: "web",    name: "Web",       icon: "🌐", color: "#22d3ee" },
    { id: "pwn",    name: "Pwn",       icon: "🔧", color: "#f87171" },
    { id: "crypto", name: "Crypto",    icon: "🔐", color: "#c084fc" },
    { id: "for",    name: "Forensics", icon: "🕵️", color: "#fbbf24" },
    { id: "rev",    name: "Reverse",   icon: "🔄", color: "#34d399" },
    { id: "misc",   name: "Misc",      icon: "🎯", color: "#f472b6" }
  ];

  const CHALLENGES_DEF = [
    { cat: "web",    title: "HTTP Smuggling Heist", pts: 450 },
    { cat: "web",    title: "JWT Charisma",         pts: 800 },
    { cat: "web",    title: "SQLi Symphony",         pts: 1150 },
    { cat: "pwn",    title: "Format String Frenzy", pts: 600 },
    { cat: "pwn",    title: "ROP Star",              pts: 1100 },
    { cat: "pwn",    title: "Heap Dreams",           pts: 1400 },
    { cat: "crypto", title: "RSA Retread",           pts: 500 },
    { cat: "crypto", title: "Curve Whisperer",       pts: 950 },
    { cat: "crypto", title: "Oraclicious",           pts: 1300 },
    { cat: "for",    title: "Pixel Pudding",         pts: 400 },
    { cat: "for",    title: "Log Peek",              pts: 750 },
    { cat: "for",    title: "Memory Mine",           pts: 900 },
    { cat: "rev",    title: "Baby's First Crackme",  pts: 350 },
    { cat: "rev",    title: "VM Tetris",             pts: 1000 },
    { cat: "rev",    title: "Obfushuffle",           pts: 1200 },
    { cat: "misc",   title: "Stegano Hideout",       pts: 300 },
    { cat: "misc",   title: "OSINT Hunt",            pts: 650 },
    { cat: "misc",   title: "Surprise Clicker",      pts: 700 }
  ];

  const TEAM_META = [
    ["HackpHaven",   "The fortress that never sleeps", "US"],
    ["ByteBrigade",  "Semantics over syntax",          "UK"],
    ["NULLTERMIN8",  "We end .str and also careers",   "DE"],
    ["HexGhost",     "Spectral in the shell",          "JP"],
    ["OverflowOps",  "Living on the edge",             "NL"],
    ["CryptoCove",   "A bottomless pool of keys",      "FR"],
    ["ShellShockers","Bash first, ask later",          "BR"],
    ["PacketPirates","Sailing the TCP sea",            "CA"],
    ["ZeroDayz",     "We keep no sleep schedule",      "IN"],
    ["QuantumFang",  "Superposed exploit hunters",     "KR"],
    ["BinBerserk",   "Strings? We think in bytes",     "PL"],
    ["NoSleepCTF",   "All-nighter professional team",  "MX"]
  ];

  const PALETTE = [
    "#22d3ee", "#f87171", "#c084fc", "#fbbf24",
    "#34d399", "#f472b6", "#60a5fa", "#fb923c",
    "#a3e635", "#2dd4bf", "#e879f9", "#facc15"
  ];

  const FLAGS = {
    US: "🇺🇸", UK: "🇬🇧", DE: "🇩🇪", JP: "🇯🇵", NL: "🇳🇱",
    FR: "🇫🇷", BR: "🇧🇷", CA: "🇨🇦", IN: "🇮🇳", KR: "🇰🇷",
    PL: "🇵🇱", MX: "🇲🇽"
  };

  const EVENT_CALLS = [
    "just pwned a challenge", "posted a juicy writeup",
    "cracked a password hash", "exploited three services",
    "took first blood on Pwn", "reverse-engineered a binary",
    "found a flag in the pcap", "bypassed the WAF",
    "decrypted Alice's message", "winning the side-channel war"
  ];

  function build() {
    const rng = mulberry32(20260920);
    const teams = TEAM_META.map((m, i) => {
      const strength = 0.32 + rng() * 0.66; // top-ish spread
      return {
        id: "t" + i,
        name: m[0],
        tagline: m[1],
        cc: m[2],
        flag: FLAGS[m[2]],
        color: PALETTE[i % PALETTE.length],
        strength: strength,
        shape: rng()
      };
    });

    const catMap = {};
    CATEGORIES.forEach(c => (catMap[c.id] = c));

    // Assign solves per challenge, weighted by team strength & difficulty.
    const challenges = CHALLENGES_DEF.map((def, idx) => {
      const difficulty = def.pts / 1500; // 0.2 .. 0.93
      const solved = [];
      teams.forEach(t => {
        const p = t.strength * (1.18 - difficulty) * 1.6;
        if (rng() < p) solved.push(t.id);
      });
      return {
        id: "ch" + idx,
        cat: def.cat,
        catName: catMap[def.cat].name,
        catIcon: catMap[def.cat].icon,
        catColor: catMap[def.cat].color,
        title: def.title,
        pts: def.pts,
        solved: solved,
        firstBlood: solved.length ? solved[0] : null
      };
    });

    // Guard: recompute solves so the BOTTOM team still holds at least ~8%.
    teams.forEach(t => {
      if (challenges.reduce((n, c) => n + (c.solved.includes(t.id) ? 1 : 0), 0) < 2) {
        const easy = challenges.filter(c => c.pts <= 450 && !c.solved.includes(t.id));
        easy.slice(0, 2).forEach(c => (c.solved.push(t.id), (c.firstBlood = c.firstBlood || t.id)));
      }
    });

    // Per-team score aggregation + rank.
    teams.forEach(t => {
      t.challenges = challenges.filter(c => c.solved.includes(t.id));
      t.total = t.challenges.reduce((s, c) => s + c.pts, 0);
      t.byCat = {};
      CATEGORIES.forEach(c => (t.byCat[c.id] = 0));
      t.challenges.forEach(c => (t.byCat[c.cat] += c.pts));
    });

    teams.sort((a, b) => b.total - a.total);
    const N = teams.length;
    teams.forEach((t, i) => {
      t.rank = i + 1;
      t.lead = teams[0].total - t.total;
      t.overT = Math.max(t.total, 1) / Math.max(teams[0].total, 1);
    });

    // Score history: monotonic curve + wobble over the last 3 hours (5-min steps).
    const STEPS = 36;
    teams.forEach(t => {
      const end = t.total;
      const start = Math.round(end * (0.10 + t.shape * 0.10));
      const mid = 0.45 + t.shape * 0.4;
      const wobA = 0.5 + t.shape * 1.1, wobB = 1 + t.shape * 2;
      const hist = [];
      for (let k = 0; k <= STEPS; k++) {
        const p = k / STEPS;
        const base = start + (end - start) * (1 / (1 + Math.exp(-8 * (p - mid))));
        const wob = Math.sin(p * Math.PI * wobA + t.shape * 9) * 18 * wobB * (1 - Math.abs(p - 0.5) * 1.8 + 0.5);
        hist.push(Math.max(0, Math.round(base + wob)));
      }
      t.history = hist; // index 0 = start of event, last = now
      t.score = hist[hist.length - 1];
      t.prevScore = hist[Math.max(0, hist.length - 7)];
      t.delta = t.score - t.prevScore;
      t.recent = EVENT_CALLS[Math.floor(t.shape * EVENT_CALLS.length)];
      t.solvedCount = t.challenges.length;
    });

    // Sorted ranks used by UI.
    teams.sort((a, b) => b.score - a.score);
    teams.forEach((t, i) => (t.rank = i + 1));

    return {
      event: {
        name: "CTF Arena Global Finals 2026",
        time: "48:00:00",
        start: "Day 2 · LIVE",
        host: "CyberRange @ arena.hq"
      },
      categories: CATEGORIES,
      challenges: challenges,
      teams: teams,
      maxScore: Math.max(...teams.map(t => t.score)),
      generatedAt: new Date().toISOString()
    };
  }

  window.CTF_DATA = build();
})();