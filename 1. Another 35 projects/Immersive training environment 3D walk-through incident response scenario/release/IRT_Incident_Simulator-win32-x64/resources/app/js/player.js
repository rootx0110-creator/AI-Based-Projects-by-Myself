/* ============================================================
 * player.js  —  first-person movement, collision, pointer lock
 * ============================================================ */
(function () {
  'use strict';
  const A = window.__IRT = window.__IRT || {};

  const Player = {
    x: 0, z: 0, yaw: 0, pitch: 0,
    vx: 0, vz: 0, speed: 4.2, radius: 0.34,
    locked: false,
    keys: {},
    prevStepT: 0,
    onInteract: null,
    onLockChange: null,

    init() {
      const cam = A.engine.camera;
      this.x = A.spawn.x; this.z = A.spawn.z;
      this.yaw = A.spawn.yaw; this.pitch = 0;
      cam.position.set(this.x, 1.62, this.z);
      cam.rotation.set(0, this.yaw, 0);

      const canvas = A.engine.renderer.domElement;
      document.addEventListener('mousemove', (e) => this.onMouseMove(e));
      canvas.requestPointerLock = canvas.requestPointerLock || canvas.mozRequestPointerLock;
      document.addEventListener('pointerlockchange', () => {
        this.locked = (document.pointerLockElement === canvas);
        if (this.onLockChange) this.onLockChange();
      });
      document.addEventListener('pointerlockerror', () => { this.locked = false; if (this.onLockChange) this.onLockChange(); });

      document.addEventListener('keydown', (e) => {
        if (e.code === 'Escape' && this.locked) { document.exitPointerLock(); return; }
        this.keys[e.code] = true;
        if (e.code === 'KeyE' && this.onInteract) this.onInteract();
      });
      document.addEventListener('keyup', (e) => { this.keys[e.code] = false; });
    },

    requestLock() {
      const canvas = A.engine.renderer.domElement;
      if (!this.locked && canvas && canvas.requestPointerLock) canvas.requestPointerLock();
      this.locked = true;
    },

    onMouseMove(e) {
      if (!this.locked) return;
      const sens = 0.0022;
      this.yaw -= e.movementX * sens;
      this.pitch -= e.movementY * sens;
      this.pitch = Math.max(-1.35, Math.min(1.35, this.pitch));
    },

    update(dt) {
      if (!this.locked) return;
      const k = this.keys;
      let f = 0, s = 0;
      if (k.KeyW || k.KeyZ || k.ArrowUp) f -= 1;
      if (k.KeyS || k.ArrowDown) f += 1;
      if (k.KeyA || k.KeyQ || k.ArrowLeft) s -= 1;
      if (k.KeyD || k.ArrowRight) s += 1;

      const moving = f !== 0 || s !== 0;
      const acc = this.speed;
      const mvx = (-Math.sin(this.yaw) * f + Math.cos(this.yaw) * s) * acc;
      const mvz = (-Math.cos(this.yaw) * f - Math.sin(this.yaw) * s) * acc;
      const tx = this.x + mvx * dt;
      const tz = this.z + mvz * dt;

      // walking noise
      if (moving) {
        this.prevStepT -= dt;
        if (this.prevStepT <= 0) {
          A.sfx.step(true);
          this.prevStepT = 0.42;
        }
      }

      // attempt axis-wise moves with collision
      this.tryMove(tx - this.x, 0);
      this.tryMove(0, tz - this.z);

      const cam = A.engine.camera;
      cam.position.set(this.x, 1.62, this.z);
      cam.rotation.set(this.pitch, this.yaw, 0);
    },

    tryMove(dx, dz) {
      const nx = this.x + dx, nz = this.z + dz;
      if (!this.collides(nx, nz)) { this.x = nx; this.z = nz; }
    },

    collides(x, z) {
      const r = this.radius;
      for (const c of A.colliders()) {
        if (x + r > c.x1 && x - r < c.x2 && z + r > c.z1 && z - r < c.z2) return true;
      }
      // building bounds safety
      return x < A.BUILD.xMin + 0.5 || x > A.BUILD.xMax - 0.5 ||
             z < A.BUILD.zMin + 0.5 || z > A.BUILD.zMax - 0.5;
    },

    distanceTo(h) {
      const dx = this.x - h.x, dz = this.z - h.z;
      return Math.sqrt(dx * dx + dz * dz);
    }
  };

  A.player = Player;
})();