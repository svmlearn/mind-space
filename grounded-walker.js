import * as T from 'three';
import { GLTFLoader } from './vendor/three/loaders/GLTFLoader.js';
import { GroundedRig } from './grounded-rig.js';
import { MeadowGrass } from './meadow-grass.js';
const world = document.querySelector('#walk-world'),
  panel = document.querySelector('#walk-view'),
  hint = document.querySelector('#meadow-hint'),
  W = 16,
  H = W / 1.77683;
// Same depth cue the original 2D walker used (`.5 + (y - 12) / 140`), normalised so the
// character keeps its current size at the starting spot (y = 77) and shrinks towards the tree.
const depthScale = y => (0.5 + (y - 12) / 140) / (0.5 + 65 / 140);
const HERO_URL = 'assets/meadow/hero-v4.glb',
  FALLBACK_URL = 'assets/meadow/character-v3.glb';
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const map = (x, y) => new T.Vector3((x / 100 - 0.5) * W, 0, ((y / 100 - 0.5) * H) / Math.SQRT1_2);
let rig,
  grass,
  blob,
  renderer,
  scene,
  camera,
  loading = false,
  frame = 0,
  last = 0,
  pct = [64, 77],
  moving = false,
  ready = false,
  eyes = null, // hero-v4 eye boxes (glTF extras) for the blink
  blinkStart = 0,
  blinkHeld = false;
// Blink: a short burst of frames every few seconds while the hero stands visible; the render
// loop still sleeps in between, and reduced motion turns it off.
const blinkU = { value: 0 },
  BLINK_MS = 170;
function scheduleBlink() {
  setTimeout(
    () => {
      if (ready && eyes && !blinkHeld && !hidden() && !reduceMotion.matches && !blinkStart) {
        blinkStart = performance.now();
        kick();
      }
      scheduleBlink();
    },
    2600 + Math.random() * 3400,
  );
}
const stage = document.createElement('div');
stage.id = 'grounded-stage';
world.insertBefore(stage, world.querySelector('#tree-place'));
document.querySelector('#walker').hidden = true;
function hidden() {
  return (
    panel.hidden ||
    document.hidden ||
    document.querySelector('#viewer').open ||
    document.querySelector('#tree-dialog').open
  );
}
function stop() {
  cancelAnimationFrame(frame);
  frame = 0;
  last = 0;
}
function tick(t) {
  frame = 0;
  if (hidden()) {
    last = 0;
    return;
  }
  const dt = last ? Math.min((t - last) / 1000, 0.05) : 0.016;
  last = t;
  rig.setScale(depthScale(pct[1]));
  const active = rig.update(dt);
  const w = rig.world,
    s = rig.scale;
  blob.position.set(w.x, 0.004, w.z);
  blob.scale.setScalar(s);
  let settling = false;
  if (grass) {
    grass.setShadow(w.x, w.z, -1.07 * s, 0.8 * s);
    settling = grass.update(dt, w.x, w.z, rig.velocity.length() > 0.12, s);
  }
  let blinking = false;
  if (blinkStart) {
    const u = (t - blinkStart) / BLINK_MS;
    blinking = u < 1;
    blinkU.value = blinking ? Math.sin(Math.PI * Math.max(0, u)) : 0;
    if (!blinking) blinkStart = 0;
  }
  renderer.render(scene, camera);
  if (active || settling || blinking) frame = requestAnimationFrame(tick);
  else last = 0;
}
function kick() {
  if (ready && !frame && !hidden()) frame = requestAnimationFrame(tick);
}
async function activate() {
  if (ready) {
    kick();
    return;
  }
  if (loading) return;
  loading = true;
  hint.textContent = '正在准备人物…';
  try {
    renderer = new T.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    stage.append(renderer.domElement);
    scene = new T.Scene();
    camera = new T.OrthographicCamera(-W / 2, W / 2, H / 2, -H / 2, 0.1, 100);
    camera.position.set(0, 12, 12);
    camera.lookAt(0, 0, 0);
    // Golden-hour light that matches the painted lawn: warm key from the upper right
    // (behind the character, like the sun in the painting), soft cool fill from the camera side.
    scene.add(new T.HemisphereLight('#ffe7bf', '#3f5e45', 1.05));
    const sun = new T.DirectionalLight('#ffc77f', 2.7);
    sun.position.set(8, 15, -6);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -13;
    sun.shadow.camera.right = 13;
    sun.shadow.camera.top = 13;
    sun.shadow.camera.bottom = -13;
    sun.shadow.normalBias = 0.008;
    sun.shadow.bias = -0.0001;
    sun.shadow.radius = 3;
    scene.add(sun);
    const faceFill = new T.DirectionalLight('#dfe8ff', 0.75);
    faceFill.position.set(-5, 8, 12);
    scene.add(faceFill);
    const ground = new T.Mesh(
      new T.PlaneGeometry(70, 70),
      new T.ShadowMaterial({ color: '#173322', opacity: 0.24 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = 0.001;
    ground.receiveShadow = true;
    scene.add(ground);
    blob = contactShadow();
    scene.add(blob);
    // Anime-style hero (hero-v4.glb, built from the painted turnaround) with the hand-built
    // character-v3.glb as fallback: `?walker=v3` forces it, and it loads if v4 fails.
    const loader = new GLTFLoader(),
      wantV3 = new URLSearchParams(location.search).get('walker') === 'v3';
    let gltf,
      hero = false;
    if (!wantV3) {
      try {
        gltf = await loader.loadAsync(HERO_URL);
        hero = true;
      } catch (e) {
        gltf = null;
      }
    }
    if (!gltf) gltf = await loader.loadAsync(FALLBACK_URL);
    stage.dataset.walker = hero ? 'v4' : 'v3';
    const sunView = sun.position.clone().normalize().transformDirection(camera.matrixWorldInverse);
    const meshes = [];
    gltf.scene.traverse(o => {
      if (o.isMesh) meshes.push(o);
      if (hero && o.userData.eyes) eyes = o.userData.eyes;
    });
    for (const o of meshes) {
      o.castShadow = true;
      o.receiveShadow = true;
      o.material = paintedMaterial(o.material, sunView, hero, hero ? eyes : null);
      if (hero) {
        // The generated texture is a little dark under the toon ramp, and the sun sits behind the
        // character: self-light keeps the face readable. hero-v4.glb ships an emissive map that
        // is stronger on the face, ears and hands than on the clothes; without one, use a flat
        // warm share of the albedo.
        o.material.color.setScalar(1.08);
        if (o.material.emissiveMap) o.material.emissive.setScalar(1);
        else {
          o.material.emissive.setRGB(0.2, 0.17, 0.14);
          o.material.emissiveMap = o.material.map;
        }
      }
      if (hero && o.isSkinnedMesh) o.parent.add(outlineOf(o));
    }
    const holder = new T.Group();
    holder.add(gltf.scene);
    scene.add(holder);
    rig = new GroundedRig(gltf.scene, map(...pct), holder);
    rig.setScale(depthScale(pct[1]));
    rig.snap(map(...pct));
    rig.setTarget(map(...pct), moving);
    try {
      grass = new MeadowGrass({
        W,
        H,
        imageUrl: 'assets/meadow/overhead-ground.webp',
        isFree: p => window.MeadowNavigation?.free(p) ?? true,
        depthScale,
      });
      await grass.load();
      grass.setReducedMotion(reduceMotion.matches);
      scene.add(grass.object);
    } catch (e) {
      grass = null; // the character still works on the painted lawn alone
    }
    ready = true;
    hint.textContent = '点击草坪走动，也可以去树洞旁看看';
    const resize = () => {
      renderer.setSize(world.clientWidth || 1000, world.clientHeight || 563, false);
      if (!hidden()) renderer.render(scene, camera);
    };
    new ResizeObserver(resize).observe(world);
    resize();
    kick();
  } catch (e) {
    ready = false;
    hint.textContent = '这个浏览器暂时无法显示 3D 人物，可以先打开「动作小样」看录像';
    renderer?.dispose();
  }
}

// Soft painted contact shadow under the feet (the cast shadow alone looked like a sticker).
function contactShadow() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d'),
    r = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  r.addColorStop(0, 'rgba(18,40,24,0.55)');
  r.addColorStop(0.45, 'rgba(18,40,24,0.3)');
  r.addColorStop(1, 'rgba(18,40,24,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 128, 128);
  const tex = new T.CanvasTexture(c);
  tex.colorSpace = T.SRGBColorSpace;
  const mesh = new T.Mesh(
    new T.PlaneGeometry(1.15, 0.8),
    new T.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.renderOrder = -1;
  return mesh;
}

// Soft three-tone ramp: broad light, a gentle mid tone and a warm-ish shadow band,
// closer to the cel-painted seated artwork than physically based shading.
const ramp = (() => {
  const n = 32,
    data = new Uint8Array(n * 4),
    step = (a, b, x) => {
      const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
      return t * t * (3 - 2 * t);
    };
  for (let i = 0; i < n; i++) {
    const x = i / (n - 1),
      v = 0.5 + 0.3 * step(0.28, 0.4, x) + 0.2 * step(0.62, 0.74, x);
    data.set([v * 255, v * 255, v * 255, 255], i * 4);
  }
  const tex = new T.DataTexture(data, n, 1);
  tex.minFilter = tex.magFilter = T.LinearFilter;
  tex.needsUpdate = true;
  return tex;
})();

// The hero's texture already carries painted shading, so its ramp is flatter (less double
// shading): a high floor and one soft step.
const heroRamp = (() => {
  const n = 32,
    data = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) {
    const x = i / (n - 1),
      t = Math.max(0, Math.min(1, (x - 0.3) / 0.16)),
      v = 0.72 + 0.28 * t * t * (3 - 2 * t);
    data.set([v * 255, v * 255, v * 255, 255], i * 4);
  }
  const tex = new T.DataTexture(data, n, 1);
  tex.minFilter = tex.magFilter = T.LinearFilter;
  tex.needsUpdate = true;
  return tex;
})();

// Ink line for the hero: an inverted hull (back faces pushed out along the normal, in bind
// space so it follows the skinning) in a deep teal that matches the painted line work.
function outlineOf(mesh) {
  const m = new T.MeshBasicMaterial({ color: '#16302f', side: T.BackSide });
  // `_outline` (glTF `_OUTLINE`) is 0 on hair lying flat on the forehead, so no ink crosses the eyes.
  const weighted = !!mesh.geometry.attributes._outline;
  m.onBeforeCompile = shader => {
    shader.vertexShader =
      (weighted ? 'attribute float _outline;\n#define OUTLINE_W _outline\n' : '#define OUTLINE_W 1.0\n') +
      shader.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\n  transformed += normalize(normal) * 0.011 * OUTLINE_W;',
      );
  };
  m.customProgramCacheKey = () => 'hero-outline' + (weighted ? '-w' : '');
  const o = new T.SkinnedMesh(mesh.geometry, m);
  o.name = mesh.name + 'Outline';
  o.bind(mesh.skeleton, mesh.bindMatrix);
  o.position.copy(mesh.position);
  o.quaternion.copy(mesh.quaternion);
  o.scale.copy(mesh.scale);
  o.castShadow = false;
  o.frustumCulled = false;
  return o;
}

// Swap the PBR materials for toon materials with a warm sunset rim on the sun side.
// Colours, vertex colours and the painted eye texture are kept.
function paintedMaterial(src, sunView, hero = false, eyes = null) {
  const m = new T.MeshToonMaterial({
    name: src.name,
    color: src.color,
    map: src.map,
    vertexColors: src.vertexColors,
    emissive: src.emissive,
    emissiveMap: src.emissiveMap,
    gradientMap: hero ? heroRamp : ramp,
    side: src.side,
    transparent: src.transparent,
    opacity: src.opacity,
    alphaTest: src.alphaTest,
  });
  m.onBeforeCompile = shader => {
    if (eyes) addBlink(shader, eyes);
    shader.uniforms.uSunView = { value: sunView };
    shader.uniforms.uRim = { value: new T.Color('#ffcf8c') };
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform vec3 uSunView;\nuniform vec3 uRim;\nvoid main() {')
      .replace(
        '#include <opaque_fragment>',
        `{
          vec3 viewDir = isOrthographic ? vec3(0.0, 0.0, 1.0) : normalize(vViewPosition);
          float fresnel = pow(1.0 - clamp(dot(normal, viewDir), 0.0, 1.0), 2.2);
          float sunSide = smoothstep(-0.15, 0.55, dot(normal, uSunView));
          outgoingLight += uRim * fresnel * sunSide * ${hero ? '0.45' : '0.55'} * diffuseColor.rgb;
          outgoingLight += uRim * fresnel * sunSide * ${hero ? '0.06' : '0.08'};
        }
        #include <opaque_fragment>`,
      );
  };
  m.customProgramCacheKey = () =>
    hero ? 'painted-toon-rim-hero' + (eyes ? '-blink' : '') : 'painted-toon-rim';
  return m;
}

// Eyelids for the painted eyes: in bind space (before skinning) each eye is an ellipse; while
// uBlink rises a skin-coloured lid slides down it and leaves a soft lash curve when closed.
function addBlink(shader, e) {
  Object.assign(shader.uniforms, {
    uBlink: blinkU,
    uEyeL: { value: new T.Vector2(...e.L) },
    uEyeR: { value: new T.Vector2(...e.R) },
    uEyeRad: { value: new T.Vector2(...e.r) },
    uEyeZ: { value: e.zmin },
    uSkin: { value: new T.Color(...e.skin) },
  });
  shader.vertexShader = shader.vertexShader
    .replace('void main() {', 'varying vec3 vBind;\nvoid main() {')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vBind = position;');
  shader.fragmentShader = shader.fragmentShader
    .replace(
      'void main() {',
      'varying vec3 vBind;\nuniform float uBlink, uEyeZ;\nuniform vec2 uEyeL, uEyeR, uEyeRad;\nuniform vec3 uSkin;\nvoid main() {',
    )
    .replace(
      '#include <map_fragment>',
      `#include <map_fragment>
      float lid = 0.0, lash = 0.0;
      if (uBlink > 0.001 && vBind.z > uEyeZ) {
        for (int i = 0; i < 2; i++) {
          vec2 d = (vBind.xy - (i == 0 ? uEyeL : uEyeR)) / uEyeRad;
          float inEye = 1.0 - smoothstep(0.7, 1.0, dot(d, d));
          float edge = mix(1.0, -0.45 + 0.4 * d.x * d.x, uBlink);
          // Only repaint painted eye pixels (whites, iris, lashes); plain skin inside the ellipse is kept.
          vec3 c = diffuseColor.rgb;
          float notSkin = 1.0 - smoothstep(0.36, 0.46, c.r - c.b);
          lid = max(lid, smoothstep(edge - 0.05, edge + 0.05, d.y) * inEye * notSkin);
          lash = max(lash, (1.0 - smoothstep(0.05, 0.13, abs(d.y - edge))) * inEye * smoothstep(0.15, 0.4, uBlink));
        }
        diffuseColor.rgb = mix(mix(diffuseColor.rgb, uSkin, lid), vec3(0.035, 0.04, 0.05), lash * 0.9);
      }`,
    )
    .replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
      totalEmissiveRadiance = mix(totalEmissiveRadiance, uSkin * vec3(0.5, 0.44, 0.38), lid) * (1.0 - lash);`,
    );
}

window.GroundedWalker = {
  get ready() {
    return ready;
  },
  get blinks() {
    return !!eyes;
  },
  // For screenshots/tests: hold the eyelids at `v` (0 open .. 1 closed; null resumes blinking).
  holdBlink(v) {
    blinkHeld = v !== null;
    blinkStart = 0;
    blinkU.value = v ?? 0;
    if (ready && !hidden()) renderer.render(scene, camera);
  },
  activate,
  setPosition(x, y, go) {
    pct = [x, y];
    moving = go;
    if (rig) {
      const p = map(x, y);
      if (reduceMotion.matches) {
        rig.setScale(depthScale(y));
        rig.snap(p);
        if (grass) grass.update(0, p.x, p.z, false, rig.scale);
        if (!hidden()) renderer.render(scene, camera);
      } else {
        rig.setTarget(p, go);
        kick();
      }
    }
  },
  canAdvance(dx, dy) {
    if (!rig) return false;
    const yaw = Math.atan2(dx * W, (dy * H) / Math.SQRT1_2);
    rig.face(yaw);
    kick();
    return Math.abs(Math.atan2(Math.sin(yaw - rig.yaw), Math.cos(yaw - rig.yaw))) < 0.55;
  },
};
new MutationObserver(() => {
  if (panel.hidden) stop();
  else activate();
}).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stop();
  else kick();
});
new MutationObserver(() => {
  if (hidden()) stop();
  else kick();
}).observe(document.querySelector('#viewer'), { attributes: true, attributeFilter: ['open'] });
document.querySelector('#tree-dialog').addEventListener('close', kick);
reduceMotion.addEventListener?.('change', () => {
  grass?.setReducedMotion(reduceMotion.matches);
  kick();
});
scheduleBlink();
if (!panel.hidden) activate();
