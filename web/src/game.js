// Juego: un coche libre con físicas (Rapier) por los jardines del castillo. El jugador es
// el copiloto: `start`, `stop`, `back`, `left`, `right`. No hay raíl: si no se dice el giro
// a tiempo, el coche sigue recto, se sale al césped y choca con lo que haya (o cae al río).
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import RAPIER from '@dimforge/rapier3d-compat';

const FWD_SPEED = 12, BACK_SPEED = 5, ACCEL = 4, BRAKE = 8;
// Giro: al recibir `left`/`right` la conductora sigue la línea central (persecución de un punto
// LOOKAHEAD m por delante) girando solo hacia el lado pedido, con radio mínimo TURN_RADIUS, hasta
// haber cambiado el rumbo 90°. Sin orden (o con la contraria) la pista se dobla y ella sigue
// recto. Nota: el giro inmediato a tope (sin seguir la línea) se simuló sobre esta pista y no
// permite completar una vuelta con órdenes a ~11 m de la esquina (arcos de 12 m con huecos de
// solo 4 y 9 m entre ellos); solo funcionaba con órdenes 3-6 m antes (0,3-0,5 s a 12 m/s).
const TURN_RADIUS = 6, LOOKAHEAD = 6, STEER_GAIN = 3, TURN_DONE = THREE.MathUtils.degToRad(80);
const CRASH_DV = 5, CRASH_DROP = 3, CRASH_RESET_MS = 1500;
const WHEEL_R = 0.46;
const STATIC = ['Track', 'Castle', 'Walls', 'Garden', 'Props', 'Ground', 'Outside'];
const HORIZON = 0x1f1a3f, ZENITH = 0x04030c;

const Y = new THREE.Vector3(0, 1, 0);
const wrapAngle = a => Math.atan2(Math.sin(a), Math.cos(a));
const clamp = THREE.MathUtils.clamp;
const moveToward = (x, t, step) => x < t ? Math.min(x + step, t) : Math.max(x - step, t);
const quatYaw = yaw => new THREE.Quaternion().setFromAxisAngle(Y, yaw);

// Línea central de track.json: puntos de Blender (x, y) → three (x, 0, -y), longitud de arco
// acumulada y esquinas detectadas por cambio de rumbo (arcos de vértices consecutivos).
function buildLine(track) {
  const pts = track.points.map(([x, y]) => new THREE.Vector3(x, 0, -y));
  const n = pts.length, cum = [0], yaw = [];
  for (let i = 0; i < n; i++) {
    const a = pts[i], b = pts[(i + 1) % n];
    cum.push(cum[i] + a.distanceTo(b));
    yaw.push(Math.atan2(-(b.x - a.x), -(b.z - a.z)));   // yaw de three: 0 = mirando a -Z
  }
  const L = cum[n], mod = s => ((s % L) + L) % L;
  const corners = [];
  for (let i = 0; i < n; i++) {
    const d = wrapAngle(yaw[i] - yaw[(i + n - 1) % n]);
    if (Math.abs(d) < 0.01) continue;
    const turn = d > 0 ? 'left' : 'right', last = corners[corners.length - 1];
    if (last && last.i1 === i - 1 && last.turn === turn) last.i1 = i;
    else corners.push({ i0: i, i1: i, turn });
  }
  const first = corners[0], last = corners[corners.length - 1];
  if (corners.length > 1 && first.i0 === 0 && last.i1 === n - 1 && first.turn === last.turn) {
    first.i0 = last.i0; corners.pop();                   // arco que cruza el cierre del bucle
  }
  const cornerOf = new Array(n).fill(-1);
  corners.forEach((c, k) => {
    c.s0 = cum[c.i0]; c.s1 = cum[c.i1];
    for (let i = c.i0; i !== (c.i1 + 1) % n; i = (i + 1) % n) cornerOf[i] = k;
  });
  const ok = corners.length === track.turns.length && corners.every((c, k) => c.turn === track.turns[k]);
  console.assert(ok, 'esquinas detectadas ≠ track.turns', corners.map(c => c.turn), track.turns);
  const sp = new THREE.Vector3(track.start[0], 0, -track.start[1]);
  let startIdx = 0;
  pts.forEach((p, i) => { if (p.distanceTo(sp) < pts[startIdx].distanceTo(sp)) startIdx = i; });
  function nearest(p) {                                   // vértice más cercano a p (1 m de paso)
    let i = 0, d2 = Infinity;
    for (let k = 0; k < n; k++) {
      const dx = pts[k].x - p.x, dz = pts[k].z - p.z, e = dx * dx + dz * dz;
      if (e < d2) { d2 = e; i = k; }
    }
    return { i, d: Math.sqrt(d2), s: cum[i] };
  }
  return { pts, n, cum, yaw, L, mod, corners, cornerOf, startIdx, nearest };
}

function makeSky() {                                     // cúpula con degradado nocturno
  const g = new THREE.SphereGeometry(600, 24, 16), pos = g.attributes.position;
  const col = new Float32Array(pos.count * 3), top = new THREE.Color(ZENITH), bot = new THREE.Color(HORIZON);
  for (let i = 0; i < pos.count; i++) {
    const c = bot.clone().lerp(top, THREE.MathUtils.smoothstep(pos.getY(i) / 600, -0.05, 0.5));
    col.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
}

// Colisionador trimesh estático con la malla en coordenadas de mundo.
function addTrimesh(world, mesh) {
  const g = mesh.geometry, pos = g.attributes.position, v = new Float32Array(pos.count * 3), p = new THREE.Vector3();
  mesh.updateWorldMatrix(true, false);
  for (let i = 0; i < pos.count; i++) p.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld).toArray(v, i * 3);
  const idx = g.index ? Uint32Array.from(g.index.array) : Uint32Array.from({ length: pos.count }, (_, i) => i);
  // FIX_INTERNAL_EDGES: sin él, las aristas interiores de la cinta de la pista frenan el coche.
  world.createCollider(RAPIER.ColliderDesc.trimesh(v, idx, RAPIER.TriMeshFlags.FIX_INTERNAL_EDGES));
}

export async function createGame(container) {
  const [track] = await Promise.all([fetch('./track.json').then(r => r.json()), RAPIER.init()]);
  const line = buildLine(track);
  const { corners, mod } = line, N = corners.length, HALF_W = track.road_width / 2;

  // --- render ---
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(HORIZON, 90, 320);
  const camera = new THREE.PerspectiveCamera(60, 1, 0.5, 1000);
  const sky = makeSky();
  scene.add(sky, new THREE.HemisphereLight(0x6070b0, 0x201530, 0.6));
  const moon = new THREE.DirectionalLight(0xaabbff, 1.2);
  const MOON_OFF = new THREE.Vector3(40, 70, 20);
  moon.castShadow = true;
  moon.shadow.mapSize.set(2048, 2048);
  moon.shadow.bias = -0.0005; moon.shadow.normalBias = 0.03;
  Object.assign(moon.shadow.camera, { left: -60, right: 60, top: 60, bottom: -60, near: 1, far: 250 });
  scene.add(moon, moon.target);

  const draco = new DRACOLoader().setDecoderPath('./draco/');
  const gltf = await new GLTFLoader().setDRACOLoader(draco).loadAsync('./scene.glb');
  scene.add(gltf.scene);
  // Con 3 materiales, cada nodo del GLB es un Group con una malla por material ('Sky_0', 'Sky_1'…).
  const group = o => o.name.replace(/_\d+$/, '');
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    o.castShadow = !['Ground', 'Outside', 'Sky'].includes(group(o));
    o.receiveShadow = group(o) !== 'Sky';
    if (group(o) === 'Sky') o.material = new THREE.MeshBasicMaterial({ map: o.material.map, fog: false }); // luna y estrellas: sin luz ni niebla
  });

  const car = gltf.scene.getObjectByName('Car');
  const wheels = ['WheelFL', 'WheelFR', 'WheelRL', 'WheelRR'].map(nm => gltf.scene.getObjectByName(nm));
  const steeringWheel = gltf.scene.getObjectByName('SteeringWheel');
  const heads = ['DriverHead', 'DriverHat'].map(nm => gltf.scene.getObjectByName(nm));
  for (const o of [...wheels, steeringWheel]) o.userData.q0 = o.quaternion.clone();
  const headlight = new THREE.SpotLight(0xffc070, 150, 45, 0.5, 0.6, 1.5);
  headlight.position.set(0, 1, -2); headlight.target.position.set(0, 0, -25);
  car.add(headlight, headlight.target);

  // --- físicas ---
  const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
  for (const nm of STATIC) gltf.scene.getObjectByName(nm).traverse(o => o.isMesh && addTrimesh(world, o));
  const [sx, sy] = track.start, h = THREE.MathUtils.degToRad(track.start_heading_deg);
  const startYaw = Math.atan2(-Math.cos(h), Math.sin(h));
  const body = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
    .setTranslation(sx, 0.3, -sy).setRotation(quatYaw(startYaw))
    .enabledRotations(false, true, false).setCanSleep(false).setCcdEnabled(true));
  // Caja redondeada (2,2 × 1 × 4,3 m) con la base en y=0; los cantos redondos pasan sobre bordillos.
  // Sin rozamiento: la velocidad se impone cada frame y el rozamiento del suelo la frenaría.
  world.createCollider(RAPIER.ColliderDesc.roundCuboid(0.65, 0.05, 1.7, 0.45).setTranslation(0, 0.5, 0)
    .setFriction(0).setFrictionCombineRule(RAPIER.CoefficientCombineRule.Min), body);

  // --- estado del juego ---
  const st = { phase: 'stopped', speed: 0, lap: 0, nextTurn: null, distToTurn: 0, turning: null, queued: null,
               onTrack: true, message: '', fps: 0, physMs: 0 };
  let v = 0, vCmd = 0, target = 0;
  let turn = null, queued = null;   // turn: { dir: +1 izquierda / -1 derecha, yaw0 }; queued: dir en cola
  let crashAt = 0, lastOnTrack = line.startIdx, prevI = line.startIdx;
  let visited = new Set(), lapStart = performance.now(), snapCam = true;
  const carPos = new THREE.Vector3();
  let carYaw = startYaw, omega = 0;

  function apply(action) {
    if (crashAt) return;
    if (action === 'start') {
      if (visited.size === 0 && Math.abs(v) < 0.05) lapStart = performance.now();   // el crono arranca al salir
      target = FWD_SPEED;
    }
    else if (action === 'stop') { target = 0; turn = queued = null; }
    else if (action === 'back') target = -BACK_SPEED;
    else if (action === 'left' || action === 'right') {
      const dir = action === 'left' ? 1 : -1;
      // Con un giro ya en curso (> 8°) la orden se encola para cuando acabe (chicanes); si no,
      // sustituye al pendiente. Repetir el mismo giro no lo reinicia.
      if (turn && Math.abs(wrapAngle(carYaw - turn.yaw0)) > 0.15) queued = dir;
      else if (!turn || turn.dir !== dir) turn = { dir, yaw0: carYaw };
    }
  }

  function respawn() {
    // Último punto de la línea por el que pasó dentro de la pista; si cae en un arco, 8 m antes
    // de su entrada para que haya sitio para pedir el giro.
    let i = lastOnTrack;
    if (line.cornerOf[i] >= 0) i = (corners[line.cornerOf[i]].i0 - 8 + line.n) % line.n;
    const p = line.pts[i];
    body.setTranslation({ x: p.x, y: 0.3, z: p.z }, true);
    body.setRotation(quatYaw(line.yaw[i]), true);
    body.setLinvel({ x: 0, y: 0, z: 0 }, true);
    body.setAngvel({ x: 0, y: 0, z: 0 }, true);
    v = vCmd = target = 0; turn = queued = null; crashAt = 0; st.message = ''; snapCam = true;
    prevI = i;
  }

  function step(dt, now) {
    const p = body.translation(), q = body.rotation();
    carPos.set(p.x, p.y, p.z);
    carYaw = 2 * Math.atan2(q.y, q.w);
    const fx = -Math.sin(carYaw), fz = -Math.cos(carYaw);
    const near = line.nearest(carPos), onTrack = near.d <= HALF_W;
    if (onTrack) lastOnTrack = near.i;

    if (crashAt) {
      if (now - crashAt > CRASH_RESET_MS) respawn();
    } else {
      const lv = body.linvel(), vReal = lv.x * fx + lv.z * fz;
      // Choque: pierde > 5 m/s en un frame, o algo lo bloquea (va a menos de la mitad de lo
      // pedido), o cae más de 3 m bajo el nivel de la pista.
      const blocked = Math.abs(vCmd) > 1 && Math.abs(vReal) < 0.5 * Math.abs(vCmd);
      if (Math.abs(vCmd) - Math.abs(vReal) > CRASH_DV || blocked || p.y < -CRASH_DROP) {
        crashAt = now; st.message = 'crash';
        st.crashWhy = `vCmd ${vCmd.toFixed(1)} vReal ${vReal.toFixed(1)} blocked ${blocked} y ${p.y.toFixed(2)} at ${p.x.toFixed(1)},${p.z.toFixed(1)}`;
        body.setLinvel({ x: 0, y: lv.y, z: 0 }, true); body.setAngvel({ x: 0, y: 0, z: 0 }, true);
        vCmd = v = 0;
      } else {
        v = vReal;
        const limit = onTrack ? 1 : 0.5;                                // césped: velocidad a la mitad
        const tgt = clamp(target, -BACK_SPEED * limit, FWD_SPEED * limit);
        const rate = Math.sign(tgt) === Math.sign(v || tgt) && Math.abs(tgt) > Math.abs(v) ? ACCEL : BRAKE;
        v = moveToward(v, tgt, rate * dt);
        omega = 0;
        if (turn) {
          const dYaw = wrapAngle(carYaw - turn.yaw0);
          // Giro completado: siguiendo la línea el rumbo se acerca a 90° sin pasarse, así que se
          // da por hecho a partir de 80° y se ajusta al valor exacto.
          if (Math.abs(dYaw) >= TURN_DONE) {
            const yaw = turn.yaw0 + Math.sign(dYaw) * Math.PI / 2;
            body.setRotation(quatYaw(yaw), true);
            turn = queued ? { dir: queued, yaw0: yaw } : null; queued = null;
          } else {
            const wMax = Math.abs(v) / TURN_RADIUS;
            if (v > 0.5) {
              // La conductora sigue la línea central (punto LOOKAHEAD m por delante) pero solo
              // girando hacia el lado pedido: si la pista dobla al otro lado, sigue recto.
              const ahead = fx * -Math.sin(line.yaw[near.i]) + fz * -Math.cos(line.yaw[near.i]) >= 0;
              const tp = line.pts[(near.i + (ahead ? LOOKAHEAD : -LOOKAHEAD) + line.n) % line.n];
              const want = wrapAngle(Math.atan2(-(tp.x - p.x), -(tp.z - p.z)) - carYaw) * STEER_GAIN;
              omega = turn.dir > 0 ? clamp(want, 0, wMax) : clamp(want, -wMax, 0);
              // Giro a medias (la orden llegó tarde) y ya en recta alineado con la pista: se da por
              // terminado. Si no, se quedaría activo para siempre y bloquearía las órdenes siguientes.
              if (line.cornerOf[near.i] < 0 && Math.abs(want) < 0.05 && Math.abs(dYaw) > 0.3) {
                turn = queued ? { dir: queued, yaw0: carYaw } : null; queued = null;
              }
            } else omega = turn.dir * v / TURN_RADIUS;                   // marcha atrás: volante a tope
          }
        }
        body.setLinvel({ x: fx * v, y: lv.y, z: fz * v }, true);
        body.setAngvel({ x: 0, y: omega, z: 0 }, true);
        vCmd = v;
      }
    }
    world.timestep = dt;
    const t0 = performance.now();
    world.step();
    st.physMs += (performance.now() - t0 - st.physMs) * 0.05;

    // Siguiente esquina por delante según el rumbo del coche respecto al sentido de la línea.
    const ty = line.yaw[near.i], forward = fx * -Math.sin(ty) + fz * -Math.cos(ty) >= 0;
    let k = 0, best = Infinity;
    corners.forEach((c, i) => {
      const d = forward ? mod(c.s0 - near.s) : mod(near.s - c.s1);
      if (d < best) { best = d; k = i; }
    });
    const c = corners[k];
    st.nextTurn = forward ? c.turn : (c.turn === 'left' ? 'right' : 'left');
    st.distToTurn = best;
    // Vuelta: llegar al vértice de salida avanzando, habiendo visitado todas las esquinas.
    if (onTrack && line.cornerOf[near.i] >= 0) visited.add(line.cornerOf[near.i]);
    const stepFwd = near.i !== prevI && (near.i - prevI + line.n) % line.n < line.n / 2;
    if (onTrack && stepFwd && near.i === line.startIdx) {
      if (visited.size >= N) { st.lap++; st.message = `Lap ${st.lap}: ${((now - lapStart) / 1000).toFixed(1)} s`; }
      visited.clear(); lapStart = now;
    }
    prevI = near.i;
    st.speed = Math.round(v * 10) / 10;
    st.x = p.x; st.z = p.z; st.yaw = carYaw; st.vReal = crashAt ? 0 : v;   // diagnóstico
    st.onTrack = onTrack;
    st.turning = turn ? (turn.dir > 0 ? 'left' : 'right') : null;
    st.queued = queued ? (queued > 0 ? 'left' : 'right') : null;
    st.phase = crashAt ? 'crash' : Math.abs(v) < 0.05 && target === 0 ? 'stopped'
      : v < 0 || (v === 0 && target < 0) ? 'reversing' : 'driving';
  }

  // --- bucle ---
  const camPos = new THREE.Vector3(), camLook = new THREE.Vector3(), _t = new THREE.Vector3(), _q = new THREE.Quaternion();
  const head = new THREE.Vector2(), headVel = new THREE.Vector2();   // muelle de la cabeza (pitch, roll)
  let steer = 0, spin = 0, last = performance.now(), frames = 0, fpsT = last;
  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  addEventListener('resize', resize); resize();

  renderer.setAnimationLoop(now => {
    const dt = Math.min(0.05, (now - last) / 1000) || 1 / 60; last = now;
    const vPrev = v;
    step(dt, now);
    car.position.copy(carPos);
    car.quaternion.copy(body.rotation());

    // Ruedas: las delanteras giran con el volante, las cuatro ruedan con la velocidad.
    steer += (Math.atan(2.6 * omega / Math.max(Math.abs(v), 0.5)) - steer) * Math.min(1, dt * 6);
    spin += v * dt / WHEEL_R;
    wheels.forEach((w, i) => {
      w.quaternion.copy(w.userData.q0).multiply(_q.setFromAxisAngle(Y, spin));
      if (i < 2) w.quaternion.premultiply(_q.setFromAxisAngle(Y, steer));
    });
    steeringWheel.quaternion.copy(steeringWheel.userData.q0).multiply(_q.setFromAxisAngle(Y, steer * 3));
    // Cabeza y sombrero: muelle que se inclina con frenadas (pitch) y giros (roll).
    const aLon = (v - vPrev) / dt, aLat = v * omega;
    const tx = clamp(aLon * 0.02, -0.3, 0.3), tz = clamp(-aLat * 0.03, -0.3, 0.3);
    headVel.x += (60 * (tx - head.x) - 8 * headVel.x) * dt;
    headVel.y += (60 * (tz - head.y) - 8 * headVel.y) * dt;
    head.addScaledVector(headVel, dt);
    for (const o of heads) o.rotation.set(head.x, 0, head.y);

    // Cámara de persecución suavizada.
    const fx = -Math.sin(carYaw), fz = -Math.cos(carYaw);
    _t.set(carPos.x - fx * 10, carPos.y + 4.5, carPos.z - fz * 10);
    if (snapCam) { camPos.copy(_t); snapCam = false; camLook.copy(carPos); }
    camPos.lerp(_t, 1 - Math.exp(-dt * 3));
    camLook.lerp(_t.set(carPos.x + fx * 4, carPos.y + 1.2, carPos.z + fz * 4), 1 - Math.exp(-dt * 5));
    camera.position.copy(camPos); camera.lookAt(camLook);
    sky.position.copy(camPos);
    moon.position.copy(carPos).add(MOON_OFF); moon.target.position.copy(carPos);

    renderer.render(scene, camera);
    if (++frames && now - fpsT >= 1000) { st.fps = Math.round(frames * 1000 / (now - fpsT)); frames = 0; fpsT = now; }
  });

  return { apply, get state() { return st; } };
}
