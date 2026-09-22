import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { PORTFOLIO, categoryById, skillsByCategory } from "./data.js";

const TAU = Math.PI * 2;

/* ------------------------------------------------------------------ */
/* Canvas helpers                                                      */
/* ------------------------------------------------------------------ */

function makeGlowTexture(size = 128) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.28, "rgba(255,255,255,0.65)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(c);
}

function makeLabelSprite(text, color = "#a6d9ff", size = 256) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 96;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  ctx.font = "700 40px 'Segoe UI', system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "rgba(0,0,0,0.9)";
  ctx.shadowBlur = 12;
  ctx.fillStyle = color;
  ctx.fillText(text, c.width / 2, c.height / 2 + 4, 500);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
    opacity: 0.95,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(size, size * (96 / 512), 1);
  return sprite;
}

/* ------------------------------------------------------------------ */
/* Scene builder                                                       */
/* ------------------------------------------------------------------ */

export function createScene(container, { onHover, onClick, onReady } = {}) {
  /* Renderer — try several context configs before giving up */
  let renderer = null;
  const attempts = [
    { antialias: true, alpha: true, powerPreference: "high-performance" },
    { antialias: true, alpha: true },
    { antialias: false, alpha: true },
  ];
  for (const cfg of attempts) {
    try {
      renderer = new THREE.WebGLRenderer(cfg);
      break;
    } catch (e) {
      renderer = null;
    }
  }
  if (!renderer) {
    throw new Error(
      "WebGL is not available in this browser. Enable hardware acceleration (chrome://settings > System, Edge: edge://settings/system), update your GPU driver, or try Chrome/Edge/Firefox."
    );
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  container.appendChild(renderer.domElement);

  /* Scene + camera */
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x04060d, 0.011);

  const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 800);
  camera.position.set(6, 9, 36);

  /* Controls */
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.55;
  controls.minDistance = 7;
  controls.maxDistance = 120;
  controls.target.set(0, 0, 0);
  controls.maxPolarAngle = Math.PI * 0.9;

  /* Post-processing */
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(container.clientWidth, container.clientHeight), 1.15, 0.55, 0.12);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  /* Lights */
  const ambient = new THREE.AmbientLight(0x334466, 0.55);
  scene.add(ambient);
  const keyLight = new THREE.PointLight(0x88ccff, 220, 0, 2);
  keyLight.position.set(20, 26, 18);
  scene.add(keyLight);
  const glowLight = new THREE.PointLight(0x7b5cff, 160, 0, 2);
  glowLight.position.set(-22, -14, -10);
  scene.add(glowLight);

  /* Gradient sky dome */
  const skyGeo = new THREE.SphereGeometry(430, 32, 32);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      topColor: { value: new THREE.Color(0x07101f) },
      midColor: { value: new THREE.Color(0x0a1226) },
      bottomColor: { value: new THREE.Color(0x04060d) },
      offset: { value: 22 },
      exponent: { value: 0.7 },
    },
    vertexShader: `
      varying vec3 vWorld;
      void main() {
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vWorld = wp.xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 topColor; uniform vec3 midColor; uniform vec3 bottomColor;
      uniform float offset; uniform float exponent;
      varying vec3 vWorld;
      void main() {
        float h = normalize(vWorld).y * 0.5 + 0.5;
        vec3 col = mix(bottomColor, mix(midColor, topColor, pow(max(h - 0.28, 0.0) / 0.72, exponent)), clamp(h * 1.4, 0.0, 1.0));
        float halo = smoothstep(0.42, 0.62, h);
        col += vec3(0.02, 0.03, 0.07) * halo;
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  });
  scene.add(new THREE.Mesh(skyGeo, skyMat));

  /* Starfield */
  const starCount = 1600;
  const starPos = new Float32Array(starCount * 3);
  const starSizes = new Float32Array(starCount);
  for (let i = 0; i < starCount; i++) {
    const r = 150 + Math.random() * 240;
    const theta = Math.random() * TAU;
    const phi = Math.acos(2 * Math.random() - 1);
    starPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    starPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.72;
    starPos[i * 3 + 2] = r * Math.cos(phi);
    starSizes[i] = 0.5 + Math.random() * 1.5;
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
  starGeo.setAttribute("size", new THREE.BufferAttribute(starSizes, 1));
  const starMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: { uTex: { value: makeGlowTexture(64) } },
    vertexShader: `
      attribute float size;
      varying float vA;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (360.0 / -mv.z);
        vA = clamp(size / 2.0, 0.25, 1.0);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      uniform sampler2D uTex; varying float vA;
      void main() {
        vec4 t = texture2D(uTex, gl_PointCoord);
        gl_FragColor = vec4(vec3(0.75, 0.85, 1.0), t.a * vA * 0.85);
      }
    `,
  });
  const stars = new THREE.Points(starGeo, starMat);
  scene.add(stars);

  /* Nebula glow sprites for depth */
  const glowTex = makeGlowTexture(128);
  const nebulas = [
    { pos: [-60, 34, -90], scale: 90, color: 0x2956ff, opacity: 0.16 },
    { pos: [80, -20, -120], scale: 110, color: 0x8b30ff, opacity: 0.13 },
    { pos: [20, 70, -60], scale: 70, color: 0x00b4ff, opacity: 0.12 },
    { pos: [-90, -55, -70], scale: 80, color: 0xff3b8d, opacity: 0.09 },
  ];
  for (const n of nebulas) {
    const m = new THREE.SpriteMaterial({
      map: glowTex,
      color: n.color,
      transparent: true,
      opacity: n.opacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const s = new THREE.Sprite(m);
    s.position.set(...n.pos);
    s.scale.set(n.scale, n.scale, 1);
    scene.add(s);
  }

  /* Central core: layered glowing orb */
  const core = new THREE.Group();
  const coreInner = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.9, 2),
    new THREE.MeshStandardMaterial({ color: 0x0b1a3a, emissive: 0x1d4ed8, emissiveIntensity: 1.6, metalness: 0.4, roughness: 0.25, flatShading: true })
  );
  core.add(coreInner);
  const coreWire = new THREE.Mesh(
    new THREE.IcosahedronGeometry(2.6, 1),
    new THREE.MeshBasicMaterial({ color: 0x3b82f6, wireframe: true, transparent: true, opacity: 0.35 })
  );
  core.add(coreWire);
  const coreShell = new THREE.Points(
    (() => {
      const g = new THREE.BufferGeometry();
      const n = 700;
      const pos = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        const r = 3.4 + Math.random() * 1.6;
        const theta = Math.random() * TAU;
        const phi = Math.acos(2 * Math.random() - 1);
        pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        pos[i * 3 + 2] = r * Math.cos(phi);
      }
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      return g;
    })(),
    new THREE.PointsMaterial({ color: 0x4aa8ff, size: 0.06, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  core.add(coreShell);
  const coreHalo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0x2f7bff, transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false }));
  coreHalo.scale.set(16, 16, 1);
  core.add(coreHalo);
  scene.add(core);

  /* ------------------------------------------------------------------ */
  /* Category rings + skill nodes                                        */
  /* ------------------------------------------------------------------ */

  const categoryRoot = new THREE.Group();
  scene.add(categoryRoot);

  const glowSpriteTex = makeGlowTexture(128);
  const nodes = [];
  const rings = [];

  PORTFOLIO.categories.forEach((cat, ci) => {
    const skills = skillsByCategory(cat.id);
    if (!skills.length) return;

    const tiltX = (Math.random() * 0.8 + 0.35) * (ci % 2 === 0 ? 1 : -1);
    const tiltZ = (Math.random() * 0.7 - 0.35) * (ci % 3 === 0 ? 1 : -1);
    const phase = Math.random() * TAU;
    const radius = 7 + skills.length * 1.25;
    const ringSpeed = (ci % 2 === 0 ? 1 : -1) * (0.02 + Math.random() * 0.02);

    const ring = new THREE.Group();
    ring.rotation.set(tiltX, 0, tiltZ);

    /* dashed orbit line */
    const orbitPts = new THREE.BufferGeometry();
    const step = 90;
    const arr = new Float32Array(step * 3);
    for (let i = 0; i < step; i++) {
      const a = (i / step) * TAU;
      arr[i * 3] = Math.cos(a) * radius;
      arr[i * 3 + 1] = Math.sin(a) * radius;
      arr[i * 3 + 2] = 0;
    }
    orbitPts.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    const orbit = new THREE.Points(
      orbitPts,
      new THREE.PointsMaterial({ color: cat.color, size: 0.045, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    ring.add(orbit);
    const orbitRing = new THREE.Mesh(
      new THREE.TorusGeometry(radius, 0.008, 6, 200),
      new THREE.MeshBasicMaterial({ color: cat.color, transparent: true, opacity: 0.22 })
    );
    orbitRing.rotation.x = Math.PI / 2;
    ring.add(orbitRing);

    /* category label sprite */
    const label = makeLabelSprite(cat.name.toUpperCase() + " · " + skills.length, cat.color, radius * 3.4);
    label.position.set(radius + 1.4, radius * 0.42, 0);
    ring.add(label);

    /* skill nodes */
    skills.forEach((skill, si) => {
      const angle = phase + (si / skills.length) * TAU;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      const z = Math.sin(si * 12.9898) * 0.6;

      const group = new THREE.Group();
      group.position.set(x, y, z);

      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.42, 20, 20),
        new THREE.MeshStandardMaterial({
          color: 0x0a1420,
          emissive: cat.color,
          emissiveIntensity: 1.4,
          roughness: 0.3,
          metalness: 0.35,
        })
      );
      mesh.userData.skillId = skill.id;
      mesh.name = "skill-node";
      group.add(mesh);

      const glow = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: glowSpriteTex, color: cat.color, transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      glow.scale.set(2.1, 2.1, 1);
      group.add(glow);

      const ringlet = new THREE.Mesh(
        new THREE.TorusGeometry(0.66, 0.02, 6, 32),
        new THREE.MeshBasicMaterial({ color: cat.color, transparent: true, opacity: 0.28 })
      );
      ringlet.rotation.x = Math.PI / 2;
      ringlet.rotation.z = angle;
      group.add(ringlet);

      ring.add(group);
      nodes.push({
        id: skill.id,
        category: cat.id,
        color: cat.color,
        group,
        mesh,
        glow,
        baseScale: 1,
        targetScale: 1,
        currentScale: 1,
        baseOpacity: 1,
        targetOpacity: 1,
        currentOpacity: 1,
      });
    });

    ring.rotation.z += phase * 0; /* keep phase in node angle only */
    categoryRoot.add(ring);
    rings.push({ group: ring, speed: ringSpeed, label, orbit, orbitRing });
  });

  /* ------------------------------------------------------------------ */
  /* Interaction                                                        */
  /* ------------------------------------------------------------------ */

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2(-10, -10);
  let hovered = null;
  let intersected = null;

  const domEl = renderer.domElement;
  domEl.addEventListener("pointermove", (e) => {
    const rect = domEl.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  });
  domEl.addEventListener("pointerleave", () => {
    pointer.set(-10, -10);
  });
  domEl.addEventListener("click", (e) => {
    if (!intersected || !hovered) return;
    if (onClick) onClick(hovered);
  });

  function pickNode() {
    const visibleNodes = nodes.filter((n) => n.currentScale > 0.001);
    if (!visibleNodes.length) return null;
    raycaster.setFromCamera(pointer, camera);
    const meshes = visibleNodes.map((n) => n.mesh);
    const hits = raycaster.intersectObjects(meshes, false);
    return hits.length ? hits[0].object : null;
  }

  /* ------------------------------------------------------------------ */
  /* Camera focus animation                                              */
  /* ------------------------------------------------------------------ */

  let focus = null;

  function focusSkill(id) {
    const node = nodes.find((n) => n.id === id);
    if (!node) return;
    setActiveId(id);
    const p = node.group.position.clone();
    const world = new THREE.Vector3();
    node.group.getWorldPosition(world);
    const dir = world.clone().normalize();
    focus = {
      startPos: camera.position.clone(),
      startTarget: controls.target.clone(),
      target: world.clone(),
      pos: world.clone().add(dir.multiplyScalar(4.2)),
      progress: 0,
    };
    controls.autoRotate = false;
    controls.enabled = false;
  }

  function setActiveId(id) {
    nodes.forEach((n) => {
      n.mesh.material.emissiveIntensity = n.id === id ? 2.4 : 1.4;
      n.mesh.material.emissive.setHex(n.id === id ? 0xffffff : n.color);
      n.glow.material.opacity = n.id === id ? 1 : 0.75;
    });
  }

  function focusCamera(delta) {
    if (!focus) return;
    focus.progress = Math.min(1, focus.progress + delta * 3.2);
    const t = 1 - Math.pow(1 - focus.progress, 3);
    camera.position.lerpVectors(focus.startPos, focus.pos, t);
    controls.target.lerp(focus.startTarget, focus.target, t);
    if (focus.progress >= 1) {
      focus = null;
      controls.autoRotate = true;
      controls.enabled = true;
    }
  }

  /* ------------------------------------------------------------------ */
  /* Public API                                                          */
  /* ------------------------------------------------------------------ */

  function applyFilter(categoryId) {
    rings.forEach((ring, i) => {
      const cat = PORTFOLIO.categories[i];
      const on = categoryId === "all" || cat.id === categoryId;
      ring.group.visible = on;
    });
    if (categoryId === "all") {
      applySearch("");
    }
  }

  function applySearch(query) {
    const q = query.trim().toLowerCase();
    nodes.forEach((n) => {
      const skill = PORTFOLIO.skills.find((s) => s.id === n.id);
      const text = (skill.name + " " + skill.tech + " " + skill.description).toLowerCase();
      n.targetScale = q && !text.includes(q) ? 0 : 1;
      n.targetOpacity = q && !text.includes(q) ? 0 : 1;
    });
  }

  function expandAll() {
    applyFilter("all");
  }

  /* ------------------------------------------------------------------ */
  /* Animation loop                                                      */
  /* ------------------------------------------------------------------ */

  const clock = new THREE.Clock();

  function animateScene() {
    const delta = Math.min(clock.getDelta(), 0.05);
    const elapsed = clock.elapsedTime;

    /* core motion */
    core.rotation.y += delta * 0.16;
    core.rotation.x = Math.sin(elapsed * 0.12) * 0.12;
    coreInner.rotation.z += delta * 0.1;
    coreShell.rotation.y -= delta * 0.12;
    coreWire.rotation.y += delta * 0.06;
    const pulse = 1 + Math.sin(elapsed * 1.4) * 0.05;
    coreHalo.scale.set(16 * pulse, 16 * pulse, 1);

    /* star drift */
    stars.rotation.y += delta * 0.004;
    stars.rotation.x = Math.sin(elapsed * 0.02) * 0.06;

    /* ring rotation */
    rings.forEach((r) => {
      r.group.rotation.z += delta * r.speed;
    });

    /* node scale/opacity easing */
    nodes.forEach((n) => {
      n.currentScale += (n.targetScale - n.currentScale) * Math.min(1, delta * 6);
      n.currentOpacity += (n.targetOpacity - n.currentOpacity) * Math.min(1, delta * 6);
      const s = n.currentScale * n.baseScale * (n === hovered ? 1.35 : 1);
      n.group.scale.setScalar(s);
      n.glow.material.opacity = 0.75 * n.currentOpacity * (n === hovered ? 1 : 0.85);
      n.glow.material.rotation = hovered === n ? elapsed * 0.8 : 0;
      n.mesh.material.transparent = true;
      n.mesh.material.opacity = n.currentOpacity;
    });

    /* hover */
    intersected = pickNode();
    if (intersected) {
      const node = nodes.find((n) => n.mesh === intersected);
      if (node !== hovered) {
        hovered = node;
        if (onHover) {
          const world = new THREE.Vector3();
          node.group.getWorldPosition(world);
          world.project(camera);
          const rect = container.getBoundingClientRect();
          const sx = rect.left + ((world.x + 1) / 2) * rect.width;
          const sy = rect.top + ((1 - world.y) / 2) * rect.height;
          onHover(node, sx, sy);
        }
      }
    } else if (hovered) {
      hovered = null;
      if (onHover) onHover(null, 0, 0);
    }

    /* camera focus */
    focusCamera(delta);

    if (focus) {
      composer.render();
    } else {
      controls.update();
      composer.render();
    }
    requestAnimationFrame(animateScene);
  }

  function onResize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
    bloom.setSize(w, h);
  }
  window.addEventListener("resize", onResize);

  const api = {
    focusSkill,
    applyFilter,
    applySearch,
    expandAll,
    dispose() {
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
    },
  };

  animateScene();
  if (onReady) onReady({ nodeCount: nodes.length, rings: rings.length });
  return api;
}