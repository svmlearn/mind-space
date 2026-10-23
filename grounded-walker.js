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
  ready = false;
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
  renderer.render(scene, camera);
  if (active || settling) frame = requestAnimationFrame(tick);
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
    const gltf = await new GLTFLoader().loadAsync('assets/meadow/character-v3.glb');
    const sunView = sun.position.clone().normalize().transformDirection(camera.matrixWorldInverse);
    gltf.scene.traverse(o => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        o.material = paintedMaterial(o.material, sunView);
      }
    });
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

// Swap the PBR materials for toon materials with a warm sunset rim on the sun side.
// Colours, vertex colours and the painted eye texture are kept.
function paintedMaterial(src, sunView) {
  const m = new T.MeshToonMaterial({
    name: src.name,
    color: src.color,
    map: src.map,
    vertexColors: src.vertexColors,
    emissive: src.emissive,
    emissiveMap: src.emissiveMap,
    gradientMap: ramp,
    side: src.side,
    transparent: src.transparent,
    opacity: src.opacity,
    alphaTest: src.alphaTest,
  });
  m.onBeforeCompile = shader => {
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
          outgoingLight += uRim * fresnel * sunSide * 0.55 * diffuseColor.rgb;
          outgoingLight += uRim * fresnel * sunSide * 0.08;
        }
        #include <opaque_fragment>`,
      );
  };
  m.customProgramCacheKey = () => 'painted-toon-rim';
  return m;
}

window.GroundedWalker = {
  get ready() {
    return ready;
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
if (!panel.hidden) activate();
