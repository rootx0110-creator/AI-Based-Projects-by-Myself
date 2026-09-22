/* ============================================================
 * engine.js  —  three.js scene, meshes, lighting, render loop
 * Builds visual geometry from world.js data tables.
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};
  const W = A.BUILD;

  const Engine = {
    renderer: null, scene: null, camera: null,
    clock: null, fireLight: null, smokeLight: null, flashlight: null,
    playerGroup: null, aim: null,
    fire: null, fireParticles: null, smoke: null, smokeSprites: [],
    hotspots: {}, minimapCtx: null, minimapReady: false,
    onTick: null, running: false, lastT: 0,

    init(canvas) {
      const W3 = window.THREE;
      const renderer = new W3.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.toneMapping = W3.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
      this.renderer = renderer;

      const scene = new W3.Scene();
      scene.background = new W3.Color(0x05070c);
      scene.fog = new W3.FogExp2(0x05070c, 0.030);
      this.scene = scene;

      const camera = new W3.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 300);
      camera.position.set(A.spawn.x, 1.6, A.spawn.z);
      camera.rotation.order = 'YXZ';
      this.camera = camera;

      this.clock = new W3.Clock();

      this.buildLights();
      this.buildGeometry();

      window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      });
    },

    buildLights() {
      const W3 = window.THREE;
      const hemi = new W3.HemisphereLight(0x8fb4ff, 0x0a0c12, 0.6);
      this.scene.add(hemi);
      const key = new W3.DirectionalLight(0xffe0b0, 0.55);
      key.position.set(6, 9, 4);
      this.scene.add(key);
      this.flashlight = new W3.SpotLight(0xffffff, 0, 18, Math.PI / 4, 0.5, 28);
      this.flashlight.position.copy(this.camera.position);
      this.scene.add(this.flashlight);
    },

    /* ---------- world geometry ---------- */
    buildGeometry() {
      const W3 = window.THREE;
      const G = this.scene;

      // materials
      const mat = {
        wall:  new W3.MeshStandardMaterial({ color: 0x2a3040, roughness: 0.9, metalness: 0.05 }),
        wallSlab: new W3.MeshStandardMaterial({ color: 0x141820, roughness: 0.95 }),
        floor: new W3.MeshStandardMaterial({ color: 0x242a38, roughness: 0.85 }),
        floorLine: new W3.MeshStandardMaterial({ color: 0xffb23c, emissive: 0x332200, roughness: 0.8 }),
        danger: new W3.MeshStandardMaterial({ color: 0xffaa22, emissive: 0x552000, roughness: 0.7 }),
        rack:  new W3.MeshStandardMaterial({ color: 0x0d1420, roughness: 0.4, metalness: 0.7 }),
        rackLed: new W3.MeshStandardMaterial({ color: 0x1a2440, emissive: 0x0a2d55, emissiveIntensity: 1.2, roughness: 0.3 }),
        ups:   new W3.MeshStandardMaterial({ color: 0x11161f, roughness: 0.5, metalness: 0.5 }),
        panel: new W3.MeshStandardMaterial({ color: 0x20242e, emissive: 0x0c1018, roughness: 0.3 }),
        valve: new W3.MeshStandardMaterial({ color: 0x8a3020, roughness: 0.5 }),
        table: new W3.MeshStandardMaterial({ color: 0x26303c, roughness: 0.7 }),
        shelf: new W3.MeshStandardMaterial({ color: 0x1c222c, roughness: 0.6, metalness: 0.4 }),
        glass: new W3.MeshStandardMaterial({ color: 0x9fd4ff, emissive: 0x0a2c44, transparent: true, opacity: 0.28, roughness: 0.15 }),
        exitSign: new W3.MeshStandardMaterial({ color: 0x0a2a12, emissive: 0x39ff5e, emissiveIntensity: 1.6 }),
        light:  new W3.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff4d8, emissiveIntensity: 1.4 })
      };

      const box = (w, h, d, m, x, y, z) => {
        const o = new W3.Mesh(new W3.BoxGeometry(w, h, d), m);
        o.position.set(x, y, z);
        G.add(o); return o;
      };
      const build = A.BUILD;

      // floor slab
      box(build.xMax - build.xMin, 0.2, build.zMax - build.zMin, mat.floor, 0, -0.1, 0);

      // ceiling slab + light panels
      box(build.xMax - build.xMin, 0.3, build.zMax - build.zMin,
        new W3.MeshStandardMaterial({ color: 0x0b0e14, roughness: 0.95 }), 0, build.ceilingY + 0.1, 0);
      for (const p of [
        [-9, -9], [-2, -9], [8, -9], [-9, -1], [0, -1], [8, -1],
        [-9, 8], [0, 8], [8, 8], [-9, 19], [0, 19], [8, 19], [16, -9], [16, 8]
      ]) box(2.2, 0.06, 1.0, mat.light, p[0], build.ceilingY - 0.05, p[1]);

      // walls
      for (const w of A.WALLS) {
        const horizontal = (w.z1 === w.z2);
        const len = horizontal ? (w.x2 - w.x1) : (w.z2 - w.z1);
        const cx = (w.x1 + w.x2) / 2, cz = (w.z1 + w.z2) / 2;
        const wd = horizontal ? len + build.wallT : build.wallT;
        const dp = horizontal ? build.wallT : len + build.wallT;
        box(wd, build.wallH, dp, mat.wall, cx, build.wallH / 2, cz);
      }

      // wall cap trim (neon accents)
      for (const w of A.WALLS) {
        const cx = (w.x1 + w.x2) / 2, cz = (w.z1 + w.z2) / 2;
        const horizontal = (w.z1 === w.z2);
        const len = horizontal ? (w.x2 - w.x1) : (w.z2 - w.z1);
        const strip = new W3.Mesh(new W3.BoxGeometry(horizontal ? len : 0.1, 0.04, horizontal ? 0.1 : len),
          new W3.MeshStandardMaterial({ color: 0x10202a, emissive: 0x265d7a, emissiveIntensity: 0.7 }));
        strip.position.set(cx, 0.16, cz);
        G.add(strip);
      }

      // emergency exit signs over exits
      for (const [sx, sz, ry] of [[21, -8, 0], [-21, 3, 0], [-7, -21, 0], [0, 21, Math.PI]]) {
        const s = box(0.7, 0.7, 0.12, mat.exitSign, sx, 2.35, sz);
        s.rotation.y = ry;
      }

      // solid furniture blocks
      const matKind = { rack: mat.rack, ups: mat.ups, panel: mat.panel, valve: mat.valve,
        desk: mat.table, shelf: mat.shelf, bench: mat.table, monwall: mat.panel };
      for (const o of A.SOLID) {
        const m = matKind[o.kind] || mat.table;
        const cx = (o.x1 + o.x2) / 2, cz = (o.z1 + o.z2) / 2;
        const w = o.x2 - o.x1, d = o.z2 - o.z1;
        const mesh = box(w, o.h, d, m, cx, o.h / 2, cz);
        if (o.kind === 'rack') {
          // front LED dots
          for (let i = 0; i < 3; i++) {
            const led = new W3.Mesh(new W3.BoxGeometry(w * 0.85, 0.06, 0.06),
              new W3.MeshStandardMaterial({ color: i === 1 ? 0x2dff8a : 0x2f6bff, emissive: i === 1 ? 0x0a5c2a : 0x0a2c66, emissiveIntensity: 1.4 }));
            led.position.set(cx, o.h - 0.35 - i * 0.22, cz + (d / 2) + 0.08);
            G.add(led);
          }
        }
        if (o.kind === 'valve') {
          const wheel = new W3.Mesh(new W3.TorusGeometry(0.28, 0.07, 8, 18),
            new W3.MeshStandardMaterial({ color: 0xd8491f, roughness: 0.4, metalness: 0.4 }));
          wheel.position.set(cx, o.h + 0.3, cz);
          wheel.rotation.x = Math.PI / 2;
          G.add(wheel);
        }
      }

      // server hall centre warning chevrons
      for (let i = -4; i <= 4; i++) {
        const o = new W3.Mesh(new W3.BoxGeometry(0.5, 0.02, 0.35), mat.danger);
        o.position.set(0, 0.03, -6.2 + i * 0.6);
        G.add(o);
      }

      // fire exit glow ramp (east corridor)
      box(9.5, 0.02, 1.0, new W3.MeshStandardMaterial({ color: 0x13ff7a, emissive: 0x0a5c2c, emissiveIntensity: 0.6 }), 16.5, 0.02, -8);

      // glasses over ops divider + interior window in UPS bay wall
      box(8, 0.9, 0.08, mat.glass, 0, 1.7, 6.0);          // ops window on x=0 divider
      box(0.5, 0.9, 5.8, mat.glass, 13.75, 1.7, -5.4);     // UPS bay looking window

      this.buildHotspots();
    },

    buildHotspots() {
      const W3 = window.THREE;
      for (const h of A.HOTSPOTS) {
        const g = new W3.Group();
        const col = h.color;
        // floating marker (octahedron orbiting)
        const marker = new W3.Mesh(new W3.OctahedronGeometry(0.4, 0),
          new W3.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 1.6, roughness: 0.2 }));
        marker.position.y = 1.9;
        g.add(marker);
        // beacon column
        const beam = new W3.Mesh(new W3.CylinderGeometry(0.08, 0.08, 2.6, 8, 1, true),
          new W3.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.28, side: W3.DoubleSide }));
        beam.position.y = 1.3;
        g.add(beam);
        // ground ring
        const ring = new W3.Mesh(new W3.RingGeometry(0.9, 1.5, 40),
          new W3.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.35, side: W3.DoubleSide }));
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.05;
        g.add(ring);
        g.position.set(h.x, 0, h.z);
        g.userData.hotspotId = h.id;
        this.scene.add(g);
        this.hotspots[h.id] = { group: g, marker, ring, phase: Math.random() * Math.PI * 2 };
      }
    },

    /* ---- dynamic fire & smoke on/off ---- */
    spawnFire() {
      const W3 = window.THREE;
      if (this.fire) return;
      const fire = new W3.Group();
      const p = A.firePos;
      fire.position.set(p.x, 0.0, p.z);

      const flame = new W3.Mesh(new W3.ConeGeometry(0.7, 2.4, 12),
        new W3.MeshBasicMaterial({ color: 0xff7a24, transparent: true, opacity: 0.9 }));
      flame.position.y = 1.2;
      fire.add(flame);
      const inner = new W3.Mesh(new W3.ConeGeometry(0.4, 1.6, 10),
        new W3.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.95 }));
      inner.position.y = 0.9;
      fire.add(inner);

      this.fireLight = new W3.PointLight(0xff6a20, 2.2, 18, 1.8);
      this.fireLight.position.set(p.x, 2.2, p.z);
      this.scene.add(this.fireLight);
      this.fire = fire;
      this.scene.add(fire);

      // particle sparks
      const N = 180, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), size = new Float32Array(N);
      for (let i = 0; i < N; i++) {
        pos[i * 3] = Math.random() * 2 - 1; pos[i * 3 + 1] = Math.random() * 2; pos[i * 3 + 2] = Math.random() * 2 - 1;
        col[i * 3] = 1; col[i * 3 + 1] = 0.35 + Math.random() * 0.4; col[i * 3 + 2] = 0.08;
        size[i] = 0.12 + Math.random() * 0.3;
      }
      const geo = new W3.BufferGeometry();
      geo.setAttribute('position', new W3.BufferAttribute(pos, 3));
      geo.setAttribute('color', new W3.BufferAttribute(col, 3));
      geo.setAttribute('size', new W3.BufferAttribute(size, 1));
      const pm = new W3.PointsMaterial({ size: 0.22, vertexColors: true, transparent: true, opacity: 0.95, blending: W3.AdditiveBlending, depthWrite: false });
      const pts = new W3.Points(geo, pm);
      pts.position.set(p.x, 0.5, p.z);
      this.fireParticles = pts;
      this.fireParticleData = { pos, N, seed: null, seedArr: pos.slice() };
      this.scene.add(pts);

      spawnSmoke(this);
    },

    killFire() {
      const f = this.fire;
      if (f) {
        const g = f.children;
        window.setTimeout(() => { /* animated shrink handled in lerp loop */ }, 0);
        this.fire = null;
      }
      if (this.fireParticles) { this.scene.remove(this.fireParticles); this.fireParticles = null; }
      const fp = this.fireParticles;
      if (fp) this.scene.remove(fp);
      if (this.fireLight) { this.scene.remove(this.fireLight); this.fireLight = null; }
      if (this.smoke) { this.scene.remove(this.smoke); this.smoke = null; }
      for (const s of this.smokeSprites) this.scene.remove(s);
      this.smokeSprites = [];
    },

    setSmokeLevel(v) {
      // v in 0..1 → fog density + darkening
      const base = 0.030;
      this.scene.fog.density = base + v * 0.06;
      this.scene.background.setHSL(0.62, 0.5, 0.02 + v * 0.012);
    },

    /* ---------- player rig ---------- */
    attachPlayer() {
      const cam = this.camera;
      if (!this.playerGroup) {
        const g = new (window.THREE.Group)();
        g.add(cam);
        this.scene.add(g);
        this.playerGroup = g;
      }
      this.aim = { yaw: A.spawn.yaw, pitch: 0, x: A.spawn.x, z: A.spawn.z };
    },

    /* ---------- minimap ---------- */
    getMinimapCtx() {
      if (this.minimapCtx) return this.minimapCtx;
      const c = document.getElementById('minimap');
      if (!c) return null;
      c.width = 200; c.height = 200;
      this.minimapCtx = c.getContext('2d');
      this.minimapReady = true;
      this.drawMinimapStatic();
      return this.minimapCtx;
    },

    drawMinimapStatic() {
      const ctx = this.getMinimapCtx(); if (!ctx) return;
      const b = A.BUILD;
      const map = (x, z) => [ (x - b.xMin) / (b.xMax - b.xMin) * 200, (z - b.zMin) / (b.zMax - b.zMin) * 200 ];
      ctx.fillStyle = 'rgba(8,12,20,0.9)';
      ctx.fillRect(0, 0, 200, 200);
      for (const r of A.layoutRooms) {
        const [x1, z1] = map(r.x, r.z), [x2, z2] = map(r.x + r.w, r.z + r.h);
        ctx.fillStyle = 'rgba(38,60,90,0.4)';
        ctx.fillRect(x1 + 2, z1 + 2, x2 - x1 - 4, z2 - z1 - 4);
      }
      ctx.strokeStyle = 'rgba(120,180,255,0.5)';
      ctx.lineWidth = 3;
      ctx.strokeRect(0, 0, 200, 200);
      // hotspots
      for (const h of A.HOTSPOTS) {
        const [x, z] = map(h.x, h.z);
        ctx.fillStyle = '#' + h.color.toString(16).padStart(6, '0');
        ctx.beginPath(); ctx.arc(x, z, 4, 0, Math.PI * 2); ctx.fill();
      }
      // fire exit arrow
      const [fx, fz] = map(20.6, -8);
      ctx.fillStyle = '#39ff5e';
      ctx.beginPath(); ctx.arc(fx, fz, 5, 0, Math.PI * 2); ctx.fill();
    },

    /* ---------- main loop ---------- */
    start(onTick) {
      this.onTick = onTick;
      this.running = true;
      this.lastT = performance.now();
      const loop = (now) => {
        if (!this.running) return;
        const dt = Math.min((now - this.lastT) / 1000, 0.05);
        this.lastT = now;
        this.animate(dt, now / 1000);
        if (this.onTick) this.onTick(dt, now / 1000);
        if (this.camera) {
          this.flashlight.position.copy(this.camera.position);
          this.flashlight.target.position.set(
            this.camera.position.x + Math.sin(this.aim.yaw) * 8,
            this.camera.position.y,
            this.camera.position.z + Math.cos(this.aim.yaw) * 8);
          this.flashlight.target.updateMatrixWorld();
        }
        this.renderer.render(this.scene, this.camera);
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    },

    animate(dt, t) {
      // hotspot bobbing
      for (const h of A.HOTSPOTS) {
        const o = this.hotspots[h.id]; if (!o || !o.group) continue;
        o.phase += dt * 2;
        o.marker.position.y = 1.9 + Math.sin(o.phase) * 0.22;
        o.group.rotation.y += dt * 1.4;
        o.ring.scale.setScalar(1 + Math.sin(o.phase * 0.7) * 0.12);
      }
      // fire animation
      if (this.fire) {
        const s = 1 + Math.sin(t * 9) * 0.12;
        this.fire.scale.set(s, s, s);
        if (this.fire.children[0]) this.fire.children[0].position.y = 1.2 + Math.sin(t * 11) * 0.2;
        if (this.fireLight) this.fireLight.intensity = 2.0 + Math.sin(t * 13) * 0.9 + Math.random() * 0.4;
      }
      if (this.fireParticles) {
        const d = this.fireParticleData;
        for (let i = 0; i < d.N; i++) {
          let x = d.pos[i * 3], y = d.pos[i * 3 + 1], z = d.pos[i * 3 + 2];
          y += dt * 1.6;
          x += Math.sin(t * 3 + i) * dt * 0.5;
          z += Math.cos(t * 4 + i) * dt * 0.5;
          if (y > 2.6) { y = 0; x = (Math.random() * 2 - 1); z = (Math.random() * 2 - 1); }
          d.pos[i * 3] = x; d.pos[i * 3 + 1] = y; d.pos[i * 3 + 2] = z;
        }
        this.fireParticles.geometry.attributes.position.needsUpdate = true;
      }
      for (let i = 0; i < this.smokeSprites.length; i++) {
        const s = this.smokeSprites[i];
        s.position.y += dt * 0.5;
        s.material.opacity = Math.max(0, s.material.opacity - dt * 0.05);
        s.scale.multiplyScalar(1 + dt * 0.25);
        if (s.material.opacity <= 0.02) { this.scene.remove(s); this.smokeSprites.splice(i, 1); i--; }
      }
    },

    emitSmokePuff(x, z) {
      const W3 = window.THREE;
      const tex = smokeTexture(W3);
      const sp = new W3.Sprite(new W3.SpriteMaterial({ map: tex, color: 0x9aa4b0, transparent: true, opacity: 0.5, depthWrite: false }));
      sp.position.set(x + (Math.random() - 0.5), 0.5 + Math.random() * 0.6, z + (Math.random() - 0.5));
      sp.scale.set(2.5, 2.5, 1);
      this.smokeSprites.push(sp);
      this.scene.add(sp);
    }
  };

  /* helpers ------------------------------------------------------------------- */
  function spawnSmoke(eng) {
    if (eng.smoke) return;
    const W3 = window.THREE;
    const g = new W3.Group(); g.position.set(A.firePos.x, 0, A.firePos.z);
    for (let i = 0; i < 5; i++) {
      const sp = new W3.Sprite(new W3.SpriteMaterial({ map: smokeTexture(W3), color: 0x77808c, transparent: true, opacity: 0.35, depthWrite: false }));
      sp.position.set((Math.random() - 0.5) * 4, 0.4 + Math.random() * 1.6, (Math.random() - 0.5) * 4);
      sp.scale.set(3 + Math.random() * 2, 3 + Math.random() * 2, 1);
      g.add(sp);
    }
    eng.smoke = g; eng.scene.add(g);
  }

  let _smokeTex = null;
  function smokeTexture(W3) {
    if (_smokeTex) return _smokeTex;
    const c = document.createElement('canvas'); c.width = 64; c.height = 64;
    const g = c.getContext('2d');
    const grad = g.createRadialGradient(32, 32, 4, 32, 32, 30);
    grad.addColorStop(0, 'rgba(200,205,215,0.9)');
    grad.addColorStop(1, 'rgba(200,205,215,0)');
    g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
    _smokeTex = new W3.CanvasTexture(c);
    return _smokeTex;
  }

  A.engine = Engine;
})();