import * as THREE from './lib/three.bundle.js';

const RAD = Math.PI / 180;

export class Globe {
  constructor(canvas) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
    this.resize();
    this.camera.position.set(0, 0.6, 3.4);
    this.camera.lookAt(0, 0, 0);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.planet = new THREE.Group();
    this.scene.add(this.planet);

    this.rotationTarget = { x: 0.3, y: 0 };
    this.rotation = { x: 0.3, y: 0 };

    this.buildGlobe();
    this.buildFX();
    this.buildLights();

    this.markers = new THREE.Group();
    this.arcs = new THREE.Group();
    this.labels = new THREE.Group();
    this.planet.add(this.markers, this.arcs, this.labels);

    this.liveArcs = [];

    this.bindControls();
    this.clock = new THREE.Clock();
    this._raf = null;

    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => this.resize());
      ro.observe(this.canvas);
      this._resizeObserver = ro;
    }

    window.addEventListener('resize', () => this.resize());
  }

  static latLonToVec3(lat, lon, r = 1) {
    const phi = (90 - lat) * RAD;
    const theta = (lon + 90 + 90) * RAD;
    return new THREE.Vector3(
      -r * Math.sin(phi) * Math.cos(theta),
      r * Math.cos(phi),
      r * Math.sin(phi) * Math.sin(theta)
    );
  }

  buildLights() {
    const amb = new THREE.AmbientLight(0x88aaff, 1.6);
    const sun = new THREE.DirectionalLight(0xbfe0ff, 2.4);
    sun.position.set(5, 3, 6);
    const rim = new THREE.DirectionalLight(0x7c3aed, 1.2);
    rim.position.set(-4, -2, -5);
    this.scene.add(amb, sun, rim);
  }

  makeGlobeTexture() {
    const w = 4096, h = 2048;
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const x = c.getContext('2d');
    x.fillStyle = 'rgba(7, 11, 26, 0.96)';
    x.fillRect(0, 0, w, h);

    x.strokeStyle = 'rgba(34, 211, 238, 0.16)';
    x.lineWidth = 1;
    for (let lat = -90; lat <= 90; lat += 15) {
      const y = (90 - lat) / 180 * h;
      x.beginPath(); x.moveTo(0, y); x.lineTo(w, y); x.stroke();
    }
    for (let lon = -180; lon <= 180; lon += 15) {
      const xx = (lon + 180) / 360 * w;
      x.beginPath(); x.moveTo(xx, 0); x.lineTo(xx, h); x.stroke();
    }

    x.strokeStyle = 'rgba(34, 211, 238, 0.45)';
    x.lineWidth = 2;
    x.beginPath(); x.moveTo(0, h / 2); x.lineTo(w, h / 2); x.stroke();
    x.strokeStyle = 'rgba(34, 211, 238, 0.25)';
    x.beginPath(); x.moveTo(0, (90 - 23.5) / 180 * h); x.lineTo(w, (90 - 23.5) / 180 * h); x.stroke();
    x.beginPath(); x.moveTo(0, (90 + 23.5) / 180 * h); x.lineTo(w, (90 + 23.5) / 180 * h); x.stroke();

    x.fillStyle = 'rgba(120, 200, 255, 0.16)';
    for (let i = 0; i < 4200; i++) {
      const px = Math.random() * w;
      const py = Math.random() * h;
      const r = Math.random() * 1.6 + 0.4;
      x.beginPath(); x.arc(px, py, r, 0, Math.PI * 2); x.fill();
    }

    const seaGlow = x.createRadialGradient(w / 2, h / 2, h * 0.2, w / 2, h / 2, h);
    seaGlow.addColorStop(0, 'rgba(8, 30, 60, 0.35)');
    seaGlow.addColorStop(1, 'rgba(2, 6, 16, 0.0)');
    x.fillStyle = seaGlow;
    x.fillRect(0, 0, w, h);

    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return tex;
  }

  buildGlobe() {
    const tex = this.makeGlobeTexture();
    const mat = new THREE.MeshPhongMaterial({
      map: tex,
      specular: new THREE.Color(0x1e3a8a),
      shininess: 18,
      transparent: true,
      opacity: 0.97
    });
    const geo = new THREE.SphereGeometry(1, 96, 64);
    this.core = new THREE.Mesh(geo, mat);
    this.planet.add(this.core);

    const aura = new THREE.SphereGeometry(0.995, 64, 40);
    const glow = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      uniforms: { c: { value: new THREE.Color(0x22d3ee) } },
      vertexShader: `
        varying vec3 vN;
        void main() {
          vN = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: `
        varying vec3 vN;
        uniform vec3 c;
        void main() {
          float i = pow(0.62 - dot(vN, vec3(0.0, 0.0, 1.0)), 3.2);
          gl_FragColor = vec4(c, i * 0.85);
        }`
    });
    this.aura = new THREE.Mesh(aura, glow);
    this.planet.add(this.aura);
  }

  buildFX() {
    const ringGeo = new THREE.RingGeometry(1.55, 1.85, 128);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x22d3ee,
      transparent: true,
      opacity: 0.16,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    this.ring = new THREE.Mesh(ringGeo, ringMat);
    this.ring.rotation.x = Math.PI / 2.35;
    this.ring.rotation.z = -0.35;
    this.planet.add(this.ring);

    const ringGeo2 = new THREE.RingGeometry(1.95, 2.05, 96);
    const ring2 = new THREE.Mesh(ringGeo2, ringMat.clone());
    ring2.material.opacity = 0.07;
    ring2.rotation.x = Math.PI / 2.1;
    ring2.rotation.y = 0.4;
    this.planet.add(ring2);

    const orbitPts = [];
    for (let i = 0; i <= 128; i++) orbitPts.push(new THREE.Vector3(Math.cos(i / 128 * Math.PI * 2), 0, Math.sin(i / 128 * Math.PI * 2)).multiplyScalar(1.24));
    const orbit = new THREE.Line(new THREE.BufferGeometry().setFromPoints(orbitPts), new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.18 }));
    orbit.rotation.x = Math.PI / 2.6;
    orbit.rotation.z = 0.5;
    this.planet.add(orbit);
  }

  makeMarkerTexture(severity) {
    const color = severity;
    const s = 128;
    const c = document.createElement('canvas');
    c.width = s; c.height = s;
    const x = c.getContext('2d');
    const g = x.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    g.addColorStop(0, color);
    g.addColorStop(0.25, color);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g;
    x.fillRect(0, 0, s, s);
    return new THREE.CanvasTexture(c);
  }

  addMarker(lat, lon, severity, id) {
    const pos = Globe.latLonToVec3(lat, lon, 1.015);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: this.makeMarkerTexture(severity),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    }));
    sprite.position.copy(pos);
    const base = 0.06 + severityRank(severity) * 0.03;
    sprite.scale.set(base, base, 1);
    sprite.userData = { phase: Math.random() * Math.PI * 2, base, pos: pos.clone(), sev: severity, born: performance.now() };
    sprite.frustumCulled = false;
    this.markers.add(sprite);
    if (this.markers.children.length > 400) this.markers.remove(this.markers.children[0]);
    return sprite;
  }

  makeLabel(text, color) {
    const c = document.createElement('canvas');
    const x = c.getContext('2d');
    x.font = '600 26px Segoe UI, Arial';
    const tw = Math.max(40, Math.ceil(x.measureText(text).width));
    c.width = tw + 24; c.height = 54;
    x.fillStyle = 'rgba(6, 10, 24, 0.78)';
    x.beginPath();
    x.roundRect(4, 8, c.width - 8, 36, 8);
    x.fill();
    x.strokeStyle = 'rgba(34, 211, 238, 0.6)';
    x.lineWidth = 3;
    x.stroke();
    x.fillStyle = color;
    x.font = '600 26px Segoe UI, Arial';
    x.textBaseline = 'middle';
    x.textAlign = 'center';
    x.fillText(text, c.width / 2, 27);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    s.scale.set(c.width / 200, c.height / 200, 1);
    s.frustumCulled = false;
    return s;
  }

  addLabel(lat, lon, text, color) {
    const s = this.makeLabel(text, color);
    s.position.copy(Globe.latLonToVec3(lat, lon, 1.16));
    s.userData = { worldPos: s.position.clone() };
    this.labels.add(s);
    return s;
  }

  clearLabels() { while (this.labels.children.length) this.labels.remove(this.labels.lastChild); }

  addArc(startLatLon, endLatLon, severity, speed = 1) {
    const a = Globe.latLonToVec3(startLatLon[0], startLatLon[1], 1.03);
    const b = Globe.latLonToVec3(endLatLon[0], endLatLon[1], 1.03);
    const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(1.0 + a.distanceTo(b) * 0.42);
    const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
    const segments = 100;
    const pts = curve.getPoints(segments);

    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({
        color: severity,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    line.geometry.setDrawRange(0, 2);
    line.frustumCulled = false;
    this.arcs.add(line);

    const beadGeo = new THREE.SphereGeometry(0.012, 8, 8);
    const beadMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 });
    const bead = new THREE.Mesh(beadGeo, beadMat);
    bead.position.copy(a);
    this.arcs.add(bead);

    const entry = {
      line, bead, curve, segments,
      progress: 0,
      speed: (0.65 + Math.random() * 0.5) * speed,
      phase: 'outbound',
      phaseT: 0,
      dead: false,
      born: performance.now(),
      total: a.distanceTo(b) * 0.06 + 1.4,
      color: severity
    };
    this.liveArcs.push(entry);
    return entry;
  }

  bindControls() {
    const el = this.canvas;
    let dragging = false, lx = 0, ly = 0;
    el.addEventListener('pointerdown', (e) => {
      dragging = true;
      lx = e.clientX; ly = e.clientY;
      el.style.cursor = 'grabbing';
    });
    window.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - lx, dy = e.clientY - ly;
      lx = e.clientX; ly = e.clientY;
      this.rotationTarget.y += dx * 0.005;
      this.rotationTarget.x += dy * 0.005;
      this.rotationTarget.x = clamp(this.rotationTarget.x, -1.35, 1.35);
    });
    window.addEventListener('pointerup', (e) => {
      if ((e.pointerType === 'mouse' && e.button !== 0)) return;
      dragging = false;
      el.style.cursor = 'grab';
    });
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      const z = this.camera.position.z + e.deltaY * 0.0018;
      this.camera.position.z = clamp(z, 1.6, 6.5);
    }, { passive: false });

    const hint = document.getElementById('tip');
    let idle = 0;
    setInterval(() => {
      if (this.rotationTarget.y === 0) return;
      this.rotationTarget.y = 0;
    }, 9000);
  }

  lookAt(lat, lon) {
    const v = Globe.latLonToVec3(lat, lon, 1);
    const targetY = Math.atan2(v.x, v.z);
    const targetX = Math.asin(v.y);
    this.rotationTarget.y = -targetY + Math.PI / 2;
    this.rotationTarget.x = targetX;
  }

  resetView() {
    this.rotationTarget.y = 0;
    this.rotationTarget.x = 0.3;
    this.camera.position.set(0, 0.6, 3.4);
  }

  resize() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    if (this.renderer) this.renderer.setSize(w, h, false);
  }

  update(t, dt) {
    this.rotation.x += (this.rotationTarget.x - this.rotation.x) * Math.min(1, dt * 4);
    this.rotation.y += (this.rotationTarget.y - this.rotation.y) * Math.min(1, dt * 4);
    this.planet.rotation.x = this.rotation.x;
    this.planet.rotation.y = this.rotation.y;
    this.camera.lookAt(0, 0, 0);

    for (const m of this.markers.children) {
      const u = m.userData;
      const pulse = 1 + Math.sin(t * 0.003 + u.phase) * 0.45;
      const depth = this.camera.position.distanceTo(u.pos);
      const s = u.base * pulse * (1.2 + depth * 0.22);
      m.scale.set(s, s, 1);
      m.material.opacity = 0.95;
    }

    this.updateArcs(dt);
  }

  updateArcs(dt) {
    for (let i = this.liveArcs.length - 1; i >= 0; i--) {
      const arc = this.liveArcs[i];
      arc.speed += dt * 0.05;
      if (arc.phase === 'outbound') {
        arc.progress += dt * arc.speed;
        const p = Math.min(arc.progress, 1);
        const count = Math.max(2, Math.floor(p * arc.segments));
        arc.line.geometry.setDrawRange(0, count);
        arc.bead.position.copy(arc.curve.getPoint(Math.min(p, 1)));
        if (p >= 1) {
          arc.phase = 'travel';
          arc.phaseT = 0;
        }
      } else if (arc.phase === 'travel') {
        arc.phaseT += dt * 0.9;
        const p = (Math.sin(arc.phaseT * 4) + 1) / 2;
        arc.bead.position.copy(arc.curve.getPoint(p));
        if (arc.phaseT > 2.2) {
          arc.phase = 'fade';
          arc.phaseT = 0;
        }
      } else if (arc.phase === 'fade') {
        arc.phaseT += dt * 1.6;
        const o = Math.max(0, 1 - arc.phaseT);
        arc.line.material.opacity = 0.9 * o;
        arc.bead.material.opacity = o;
        if (arc.phaseT >= 1) {
          this.arcs.remove(arc.line);
          this.arcs.remove(arc.bead);
          arc.line.geometry.dispose();
          arc.line.material.dispose();
          arc.bead.geometry.dispose();
          arc.bead.material.dispose();
          this.liveArcs.splice(i, 1);
        }
      }
    }
  }

  start() {
    let lastW = 0, lastH = 0;
    const loop = () => {
      this._raf = requestAnimationFrame(loop);
      const dt = Math.min(this.clock.getDelta(), 0.05);
      const t = performance.now();
      const w = this.canvas.clientWidth || window.innerWidth;
      const h = this.canvas.clientHeight || window.innerHeight;
      if (w !== lastW || h !== lastH) {
        this.resize();
        lastW = w;
        lastH = h;
      }
      this.update(t, dt);
      this.renderer.render(this.scene, this.camera);
    };
    loop();
  }

  dispose() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this.renderer.dispose();
    this.scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of mats) {
          if (m.map) m.map.dispose();
          m.dispose();
        }
      }
    });
  }
}

function severityRank(s) {
  if (s === '#ff3860') return 3;
  if (s === '#ff9f1a') return 2;
  if (s === '#ffd166') return 1;
  return 0;
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));