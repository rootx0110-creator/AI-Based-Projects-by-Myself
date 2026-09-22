/* ═══════════════════════════════════════════════════════════════════════
   CTF ARENA · Three.js 3D scoreboard scene
   - team towers scaled by score, arranged in a circle
   - manual orbit (drag) + zoom (wheel) + gentle auto-rotate
   - HTML labels projected from 3D to 2D each frame
   - click / hover raycasting
   ═══════════════════════════════════════════════════════════════════════ */
(function (global) {
  "use strict";

  const SceneManager = {
    els: {},
    callbacks: { select: null, hover: null },
    selectedId: null,
    hoverId: null,
    autoRotate: true,
    lastInteract: performance.now(),
    active: false,
    meshes: {},

    start(container, teams, callbacks) {
      if (typeof THREE === "undefined") {
        container.innerHTML =
          '<div style="color:#8ea3c4;font:600 14px Inter,sans-serif;padding:40px;text-align:center">' +
          "3D engine (Three.js) failed to load — check your internet connection and refresh.</div>";
        return false;
      }
      this.callbacks = callbacks || {};
      this.els.container = container;
      this.teams = teams;
      this.init(teams);
      return true;
    },

    init(teams) {
      const w = this.els.container.clientWidth || window.innerWidth;
      const h = this.els.container.clientHeight || window.innerHeight;

      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0x060a14, 45, 95);

      this.camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 300);
      this.camera.position.set(0, 22, 34);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
      this.renderer.setSize(w, h);
      this.renderer.shadowMap.enabled = true;
      this.els.container.appendChild(this.renderer.domElement);

      // Lights
      const hemi = new THREE.HemisphereLight(0x3a5f9e, 0x0a1020, 0.85);
      this.scene.add(hemi);
      const dir = new THREE.DirectionalLight(0xbfe3ff, 1.15);
      dir.position.set(18, 30, 12);
      this.scene.add(dir);
      const rim = new THREE.PointLight(0x22d3ee, 0.9, 60);
      rim.position.set(-22, 14, -18);
      this.scene.add(rim);
      const rim2 = new THREE.PointLight(0xa78bfa, 0.7, 60);
      rim2.position.set(22, 10, -12);
      this.scene.add(rim2);

      // Ground grid
      const grid = new THREE.GridHelper(60, 30, 0x1d3a5c, 0x14233d);
      grid.material.opacity = 0.5;
      grid.material.transparent = true;
      grid.position.y = -0.02;
      this.scene.add(grid);
      const floor = new THREE.Mesh(
        new THREE.CircleGeometry(40, 64),
        new THREE.MeshBasicMaterial({ color: 0x0a1022, transparent: true, opacity: 0.55 })
      );
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = -0.06;
      this.scene.add(floor);

      // Ambient star field
      const starGeo = new THREE.BufferGeometry();
      const starN = 700;
      const pos = new Float32Array(starN * 3);
      for (let i = 0; i < starN; i++) {
        pos[i * 3] = (Math.random() - 0.5) * 120;
        pos[i * 3 + 1] = Math.random() * 50 + 2;
        pos[i * 3 + 2] = (Math.random() - 0.5) * 120;
      }
      starGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const stars = new THREE.Points(
        starGeo,
        new THREE.PointsMaterial({ color: 0x8fb3ff, size: 0.18, transparent: true, opacity: 0.7 })
      );
      this.scene.add(stars);

      this.buildTowers(teams);

      // Orbit state
      this.az = 0.0;
      this.el = 0.55;
      this.dist = 34;
      this.target = new THREE.Vector3(0, 8, 0);
      this.isDragging = false;
      this.lastX = 0;
      this.lastY = 0;

      this.bindEvents();
      this.loop();
    },

    buildTowers(teams) {
      const R = 14;
      const maxH = 20;
      const maxScore = CTF_DATA.maxScore || 1000;
      const matCache = {};

      teams.forEach((t, i) => {
        const ang = (i / teams.length) * Math.PI * 2;
        const x = Math.sin(ang) * R;
        const z = Math.cos(ang) * R;
        t.lookAng = ang;

        const col = new THREE.Color(t.color);
        const mat = new THREE.MeshStandardMaterial({
          color: col,
          emissive: new THREE.Color(t.color).multiplyScalar(0.18),
          roughness: 0.25,
          metalness: 0.4,
          transparent: true,
          opacity: 0.95
        });

        // group: unit cylinder (height 1) scaled by score
        const group = new THREE.Group();
        const cyl = new THREE.Mesh(new THREE.CylinderGeometry(1, 1.15, 1, 24, 1), mat);
        cyl.rotation.z = 0;
        group.add(cyl);
        const cap = new THREE.Mesh(
          new THREE.CylinderGeometry(1.35, 1.35, 0.16, 24),
          new THREE.MeshStandardMaterial({
            color: new THREE.Color(t.color),
            emissive: new THREE.Color(t.color).multiplyScalar(0.5),
            roughness: 0.2, metalness: 0.6
          })
        );
        cap.position.y = 0.5;
        group.add(cap);

        // selection ring (hidden until selected)
        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(2.1, 0.06, 8, 48),
          new THREE.MeshBasicMaterial({ color: 0x22d3ee, toneMapped: false })
        );
        ring.rotation.x = Math.PI / 2;
        ring.position.y = 0.02;
        ring.visible = false;
        group.add(ring);

        const h = Math.max(0.8, (t.score / maxScore) * maxH);
        cyl.scale.y = h;
        cyl.position.y = h / 2;
        cap.position.y = h + 0.04;

        group.position.set(x, 0, z);
        group.userData = { id: t.id, height: h, targetHeight: h };
        this.scene.add(group);

        // base glow disc
        const glow = new THREE.Mesh(
          new THREE.CircleGeometry(1.6, 32),
          new THREE.MeshBasicMaterial({
            color: col,
            transparent: true,
            opacity: 0.16,
            depthWrite: false
          })
        );
        glow.rotation.x = -Math.PI / 2;
        glow.position.set(x, 0.02, z);
        this.scene.add(glow);

        this.meshes[t.id] = group;
      });

      this.maxHeight = maxH;
      this.maxScore = maxScore;
      this.radius = R;
    },

    updateScores(teams) {
      // animated heights
      teams.forEach(t => {
        const g = this.meshes[t.id];
        if (!g) return;
        const h = Math.max(0.8, (t.score / this.maxScore) * this.maxHeight);
        g.userData.targetHeight = h;
        const cyl = g.children[0];
        const cap = g.children[1];
        const cur = g.userData.height;
        const next = cur + (h - cur) * 0.06;
        g.userData.height = next;
        cyl.scale.y = next;
        cyl.position.y = next / 2;
        cap.position.y = next + 0.04;
      });
    },

    setSelected(id) {
      const prev = this.meshes[this.selectedId];
      if (prev) prev.children[2].visible = false;
      this.selectedId = id;
      const cur = this.meshes[id];
      if (cur) cur.children[2].visible = true;
      this.refreshLabels();
    },

    selectById(id) {
      const t = this.teams.find(x => x.id === id);
      if (!t) return;
      const x = Math.sin(t.lookAng) * this.radius;
      const z = Math.cos(t.lookAng) * this.radius;
      const target = new THREE.Vector3(x * 0.5, 9, z * 0.5);
      this.target.lerp(target, 0.05);
      this.setSelected(id);
      if (this.callbacks.select) this.callbacks.select(id);
    },

    bindEvents() {
      const el = this.els.container;
      el.addEventListener("pointerdown", e => {
        this.isDragging = true;
        this.autoRotate = false;
        this.lastInteract = performance.now();
        this.lastX = e.clientX;
        this.lastY = e.clientY;
        el.setPointerCapture(e.pointerId);
      });
      el.addEventListener("pointermove", e => {
        if (this.isDragging) {
          const dx = e.clientX - this.lastX;
          const dy = e.clientY - this.lastY;
          this.lastX = e.clientX;
          this.lastY = e.clientY;
          this.az -= dx * 0.005;
          this.el = Math.max(0.12, Math.min(1.25, this.el + dy * 0.004));
          this.lastInteract = performance.now();
          this.autoRotate = true;
        }
        const rect = el.getBoundingClientRect();
        const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        const hit = this.pick(nx, ny);
        this.setHover(hit ? hit.userData.id : null);
      });
      const end = e => {
        if (!this.isDragging) return;
        this.isDragging = false;
        const rect = el.getBoundingClientRect();
        const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        const hit = this.pick(nx, ny);
        if (hit) this.selectById(hit.userData.id);
      };
      el.addEventListener("pointerup", end);
      el.addEventListener("pointercancel", end);
      el.addEventListener("wheel", e => {
        e.preventDefault();
        this.dist = Math.max(16, Math.min(70, this.dist + e.deltaY * 0.03));
        this.lastInteract = performance.now();
        this.autoRotate = true;
      }, { passive: false });
      el.addEventListener("dblclick", e => {
        const rect = el.getBoundingClientRect();
        const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        const hit = this.pick(nx, ny);
        if (hit) this.sceneCenter = hit.userData.id;
      });

      window.addEventListener("resize", () => {
        const w = this.els.container.clientWidth, h = this.els.container.clientHeight;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
      });
    },

    setHover(id) {
      if (this.hoverId === id) return;
      this.hoverId = id;
      this.els.container.style.cursor = id ? "pointer" : "grab";
      Object.keys(this.meshes).forEach(mid => {
        const m = this.meshes[mid].children[0];
        if (mid === id) {
          m.material.emissive.setHex(0x3b82f6).setScalar(0.4);
        } else if (mid !== this.selectedId) {
          const t = this.teams.find(x => x.id === mid);
          m.material.emissive.set(t.color).multiplyScalar(0.18);
        }
      });
      this.refreshLabels();
    },

    pick(nx, ny) {
      const raycaster = new THREE.Raycaster();
      const ndc = new THREE.Vector2(nx, ny);
      raycaster.setFromCamera(ndc, this.camera);
      const groups = Object.keys(this.meshes).map(k => this.meshes[k]);
      const hits = raycaster.intersectObjects(groups, true);
      for (const hit of hits) {
        let obj = hit.object;
        const view = new THREE.Vector3().subVectors(this.camera.position, hit.point);
        if (view.y < -0.5) continue; // ignore back-of-tower hits
        const src = obj.userData && obj.userData.id
          ? obj
          : obj.parent && obj.parent.userData && obj.parent.userData.id
            ? obj.parent
            : (obj.parent ? obj.parent.parent : null);
        const id = src && src.userData && src.userData.id;
        if (id) return src;
      }
      return null;
    },

    refreshLabels() {
      const box = this.els.labelsBox;
      if (!box) return;
      const children = box.children;
      this.teams.forEach((t, i) => {
        const node = children[i];
        if (!node) return;
        node.innerHTML =
          '<span class="rank" style="color:' + t.color + '">' + t.rank + "</span>" +
          '<span class="tag">' + t.name + "</span>" +
          '<span class="pts">' + fmt(t.score) + "</span>";
        const g = this.meshes[t.id];
        const topY = (g.userData.height || 0) + 0.7;
        const p = new THREE.Vector3(
          Math.sin(t.lookAng) * this.radius,
          topY,
          Math.cos(t.lookAng) * this.radius
        );
        p.project(this.camera);
        if (p.z > 1 || p.z < -1) {
          node.style.opacity = "0";
          return;
        }
        const sx = (p.x * 0.5 + 0.5) * box.clientWidth;
        const sy = (-p.y * 0.5 + 0.5) * box.clientHeight;
        node.style.opacity = "1";
        node.style.left = sx + "px";
        node.style.top = sy + "px";
        node.classList.toggle("sel", this.selectedId === t.id);
        node.classList.toggle("top", t.rank <= 3);
      });
    },

    buildLabels(box) {
      this.els.labelsBox = box;
      box.innerHTML = "";
      this.teams.forEach(t => {
        const d = document.createElement("div");
        d.className = "tlabel";
        d.innerHTML =
          '<span class="rank" style="color:' + t.color + '">' + t.rank + "</span>" +
          '<span class="tag">' + t.name + "</span>" +
          '<span class="pts">' + fmt(t.score) + "</span>";
        box.appendChild(d);
      });
    },

    loop() {
      requestAnimationFrame(() => this.loop());
      if (this.autoRotate && performance.now() - this.lastInteract > 6000) {
        this.az += 0.0012;
      }
      // camera orbit
      const cx = this.target.x + Math.sin(this.az) * Math.cos(this.el) * this.dist;
      const cy = this.target.y + Math.sin(this.el) * this.dist;
      const cz = this.target.z + Math.cos(this.az) * Math.cos(this.el) * this.dist;
      this.camera.position.lerp(new THREE.Vector3(cx, cy, cz), 0.08);
      this.camera.lookAt(this.target);
      this.renderer.render(this.scene, this.camera);
      this.refreshLabels();
    },

    destroy() {
      cancelAnimationFrame.bind(this);
      if (this.renderer) {
        this.renderer.dispose();
        this.els.container.innerHTML = "";
      }
    }
  };

  function fmt(n) {
    return n >= 10000 ? (n / 1000).toFixed(1) + "k" : String(n);
  }

  global.SceneManager = SceneManager;
})(window);