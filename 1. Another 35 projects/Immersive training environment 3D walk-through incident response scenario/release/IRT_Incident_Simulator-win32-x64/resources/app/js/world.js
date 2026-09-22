/* ============================================================
 * world.js  —  Floor plan, walls, hotspots, spawn data
 * Builds deterministic facility geometry for the simulator.
 * ============================================================ */
(function () {
  'use strict';
  const W = window.__IRT = window.__IRT || {};

  W.BUILD = {
    xMin: -21, xMax: 21,
    zMin: -21, zMax: 21,
    ceilingY: 3.0, wallH: 3.0, wallT: 0.5
  };

  /* ---- wall segments : {x1,z1,x2,z2} (axis aligned) ---- */
  function wall(x1, z1, x2, z2) { return { x1: Math.min(x1, x2), z1: Math.min(z1, z2), x2: Math.max(x1, x2), z2: Math.max(z1, z2) }; }

  const WALLS = [];
  const outer = W.BUILD;

  /* --- outer shell with door gaps (gap between two coords = opening) --- */
  // south outer (z = 21)  door x -2.5..2.5
  WALLS.push(wall(outer.xMin, outer.zMax, -2.5, outer.zMax));
  WALLS.push(wall(2.5, outer.zMax, outer.xMax, outer.zMax));
  // north outer (z = -21) doors x -7.5..-6.5 (emergency),  x 5..7
  WALLS.push(wall(outer.xMin, outer.zMin, -7.5, outer.zMin));   // -21..-7.5
  WALLS.push(wall(-6.5, outer.zMin, 5, outer.zMin));            // -6.5..5
  WALLS.push(wall(7, outer.zMin, outer.xMax, outer.zMin));      // 7..21
  // west outer (x = -21) door z 2..4 (delivery)
  WALLS.push(wall(outer.xMin, outer.zMin, outer.xMin, 2));
  WALLS.push(wall(outer.xMin, 4, outer.xMin, outer.zMax));
  // east outer (x = 21)  door z -9..-7 (fire exit)
  WALLS.push(wall(outer.xMax, outer.zMin, outer.xMax, -9));
  WALLS.push(wall(outer.xMax, -7, outer.xMax, outer.zMax));

  /* --- interior ring (rooms inside ; corridors on the outside ring) ---
   * interior room block spans x -14..14, z -14..14  */
  // south interior wall z = 14  doors x -6..-4 (cold store), x 4..6 (ops)
  WALLS.push(wall(-14, 14, -6, 14));
  WALLS.push(wall(-4, 14, 4, 14));
  WALLS.push(wall(6, 14, 14, 14));
  // north interior wall z = -14  doors x -8..-6 (server hall), x 5..7 (ups)
  WALLS.push(wall(-14, -14, -8, -14));
  WALLS.push(wall(-6, -14, 5, -14));
  WALLS.push(wall(7, -14, 14, -14));
  // west interior wall x = -14  doors z -8..-6 (server hall), z 6..8 (cold)
  WALLS.push(wall(-14, -14, -14, -8));
  WALLS.push(wall(-14, -6, -14, 6));
  WALLS.push(wall(-14, 8, -14, 14));
  // east interior wall x = 14  doors z -10..-8 (ups bay), z 2..4 (ops)
  WALLS.push(wall(14, -14, 14, -10));
  WALLS.push(wall(14, -8, 14, 2));
  WALLS.push(wall(14, 4, 14, 14));

  /* --- quadrant dividers (central 2x2 block) --- */
  // vertical  x=0 : north half (server|ups) door z -4..-2
  WALLS.push(wall(0, -14, 0, -4));
  WALLS.push(wall(0, -2, 0, 0));
  // vertical  x=0 : south half (cold|ops) door z 5..7
  WALLS.push(wall(0, 0, 0, 5));
  WALLS.push(wall(0, 7, 0, 14));
  // horizontal z=0 : west half (server|cold) door x -10..-8
  WALLS.push(wall(-14, 0, -10, 0));
  WALLS.push(wall(-8, 0, 0, 0));
  // horizontal z=0 : east half (ups|ops) door x 6..8
  WALLS.push(wall(0, 0, 6, 0));
  WALLS.push(wall(8, 0, 14, 0));

  /* --- furniture (solid obstacles + decorative) : {x1,z1,x2,z2,h,kind} --- */
  const SOLID = [];
  function block(x1, z1, x2, z2, h, kind) {
    const o = wall(x1, z1, x2, z2);
    o.h = h || 1.0; o.kind = kind || 'box';
    SOLID.push(o);
    return o;
  }

  // Server hall racks : rows at z -12,-9,-6,-3 ; racks along x
  for (const rz of [-12, -9, -6, -3]) {
    for (let rx = -12.5; rx <= -4.5; rx += 1.9) {
      block(rx, rz - 0.4, rx + 1.3, rz + 0.4, 2.2, 'rack');
    }
  }
  // UPS / electrical bay : cabinets row near fire + panel stand
  for (let ux = 2; ux <= 11.5; ux += 2.4) {
    block(ux, -6.6, ux + 1.8, -5.2, 2.0, 'ups');      // cabinet row (fire sits on this)
  }
  block(12.4, -6.6, 13.5, -5.2, 2.0, 'ups');           // end cabinet
  block(12.6, -8.5, 13.5, -7.9, 2.0, 'panel');         // breaker / E-stop stand
  block(1.4, -1.6, 2.7, -0.6, 0.9, 'valve');           // fuel isolation skid
  // cold store shelves (west half, south quadrant)
  for (let sz = 2.5; sz <= 11; sz += 2.8) {
    block(-13.4, sz, -12.2, sz + 2.0, 2.0, 'shelf');
  }
  // ops room : desks + low wall
  block(2.2, 3.2, 4.4, 4.6, 0.9, 'desk');
  block(8.2, 1.6, 9.4, 2.6, 0.9, 'desk');
  block(11.2, 3.2, 12.6, 4.6, 0.9, 'desk');
  block(10.6, 6.0, 13.4, 6.8, 1.8, 'monwall');
  // lobby bench + bollards
  block(-5.4, 17.8, -4.2, 19.0, 0.5, 'bench');
  block(5.6, 16.4, 7.0, 17.2, 0.4, 'bench');

  W.WALLS = WALLS;
  W.SOLID = SOLID;

  /* merge solid walls + furniture into a single collision list */
  W.colliders = function () { return WALLS.concat(SOLID.filter(o => !o.open)); };

  /* ================= hotspots ================= */
  W.HOTSPOTS = [
    { id: 'don_ppe',  key: 'don_ppe',       label: 'Don Protective Kit',     x: -4.6, z: 18.6, color: 0x3df2c0, radius: 2.4, sub: 'Helmet · Visor · Gloves · Boots' },
    { id: 'panel',    key: 'verify_alarm',  label: 'Fire Alarm Panel',       x: 2.8,  z: 20.1, color: 0x36c7ff, radius: 2.6, sub: 'Zone 03 / UPS-EAST  —  status: ACTIVE' },
    { id: 'pull',     key: 'raise_alarm',   label: 'Raise the Alarm (Pull)', x: 5.0,  z: 20.1, color: 0xffb23c, radius: 2.4, sub: 'Manual call-point · Zone 03' },
    { id: 'fire',     key: 'assess_fire',   label: 'Assess the Blaze',       x: 6.5,  z: -5.6, color: 0xff5246, radius: 3.2, sub: 'UPS-EAST · electrical fire' },
    { id: 'valve',    key: 'isolate_fuel',  label: 'Isolate Fuel Valve',     x: 2.05, z: -1.1, color: 0xff8f3c, radius: 2.6, sub: 'Diesel back-feed · close NOW' },
    { id: 'estop',    key: 'electrical_iso',label: 'E-Stop & Breaker',       x: 13.05,z: -8.2, color: 0xffd23c, radius: 2.6, sub: 'Isolate UPS-EAST power' },
    { id: 'ext',      key: 'extinguish',    label: 'Engage Suppression',     x: 6.5,  z: -5.6, color: 0x5b7cff, radius: 3.4, sub: 'Use correct agent' },
    { id: 'coworker', key: 'coworker',      label: 'Coworker Down',          x: 12.2, z: 12.6, color: 0xc86bff, radius: 2.6, sub: 'Civilian in ops annex · needs aid' },
    { id: 'exit',     key: 'evacuate',      label: 'Evacuate → Muster Point',x: 20.6, z: -8.0, color: 0x7dff5b, radius: 2.6, sub: 'Fire exit · do not re-enter' }
  ];

  W.spawn = { x: 0, z: 19.2, yaw: Math.PI };   // facing into building/north
  W.firePos = { x: 7.2, z: -5.6 };             // visual fire anchor
  W.muster = { x: 24.2, z: -8.0 };             // outside the fire exit

  /* minimap basics for scenes drawn from this data */
  W.layoutRooms = [
    { name: 'LOBBY',        x: -6, z: 16, w: 12, h: 5 },
    { name: 'SERVER HALL',  x: -14, z: -14, w: 14, h: 14 },
    { name: 'UPS & ELEC',   x: 0, z: -14, w: 14, h: 14 },
    { name: 'COLD STORE',   x: -14, z: 0, w: 14, h: 14 },
    { name: 'OPS',          x: 0, z: 0, w: 14, h: 14 }
  ];
})();