import * as T from 'three';
import { GLTFLoader } from '../vendor/three/loaders/GLTFLoader.js';

const $ = selector => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const W = 16, H = W / 1.77683;
const map = (x, y) => new T.Vector3((x / 100 - .5) * W, 0, (y / 100 - .5) * H / Math.SQRT1_2);
const world = $('#world'), viewport = $('#viewport');
const file = './meadow-hero.glb';
const scene = new T.Scene();
const camera = new T.OrthographicCamera(-2, 2, 2, -2, .1, 100);
let renderer, model, gltf, loading = false, generation = 0;
let dimensions = new T.Vector3(1.5, 2.4, 1), center = new T.Vector3(0, 1.2, 0);
let currentView = 'meadow', theta = 0, phi = Math.PI / 4, zoom = 1;
let paintFaithful = params.get('color') !== 'aces';
let headPose = 'lookup', headNode = null, headBaseline = null;
const headPivot = new T.Vector3(0, 1.52, 0);
const lookUpRotation = new T.Matrix4().makeTranslation(...headPivot.toArray())
  .multiply(new T.Matrix4().makeRotationX(T.MathUtils.degToRad(-12)))
  .multiply(new T.Matrix4().makeTranslation(...headPivot.clone().negate().toArray()));
const group = new T.Group();
scene.add(group);

// These values are copied verbatim from grounded-walker.reference.js.
// In particular faceFill is included: do not add preview-only lights.
const lighting = {
  hemisphere: { sky: '#fff0cf', ground: '#335b4b', intensity: 1.65 },
  sun: { color: '#ffdb9b', intensity: 2.4, position: [8, 15, -6] },
  faceFill: { color: '#fff5e8', intensity: 1.2, position: [-5, 8, 12] },
  exposure: 1.12,
};
scene.add(new T.HemisphereLight('#fff0cf', '#335b4b', 1.65));
const sun = new T.DirectionalLight('#ffdb9b', 2.4);
sun.position.set(8, 15, -6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -13;
sun.shadow.camera.right = 13;
sun.shadow.camera.top = 13;
sun.shadow.camera.bottom = -13;
sun.shadow.normalBias = .008;
sun.shadow.bias = -.0001;
scene.add(sun);
const faceFill = new T.DirectionalLight('#fff5e8', 1.2);
faceFill.position.set(-5, 8, 12);
scene.add(faceFill);
const ground = new T.Mesh(new T.PlaneGeometry(70, 70), new T.ShadowMaterial({ opacity: .32 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = .001;
ground.receiveShadow = true;
scene.add(ground);

function fail(error) {
  window.ready = false;
  $('#status').textContent = '模型暂时无法显示';
  $('#status-dot').className = 'dot error';
  $('#loading').hidden = false;
  $('#loading').classList.add('failed');
  $('#loading-message').textContent = '模型加载失败，请点击重新加载；也可以先看右侧的模型渲染图。';
  window.verification = { loaded: false, file, error: String(error), lighting };
}

try {
  renderer = new T.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  $('#stage').append(renderer.domElement);
} catch (error) {
  fail(error);
  $('#loading-message').textContent = '浏览器暂时无法显示三维模型，可以先看右侧的模型渲染图。';
}

function render() {
  if (renderer) renderer.render(scene, camera);
}

function updateCamera() {
  const aspect = Math.max(world.clientWidth, 1) / Math.max(world.clientHeight, 1);
  if (currentView === 'full') {
    camera.left = -W / 2; camera.right = W / 2;
    camera.top = H / 2; camera.bottom = -H / 2;
    camera.position.set(0, 12, 12);
    camera.lookAt(0, 0, 0);
  } else {
    // Fit a sphere around the actual bounds so every cardinal view and orbit stays legible.
    const fit = Math.max(dimensions.y, Math.hypot(dimensions.x, dimensions.z)) * 1.25;
    const span = Math.max(fit, fit / aspect);
    camera.left = -span * aspect / 2; camera.right = span * aspect / 2;
    camera.top = span / 2; camera.bottom = -span / 2;
    const radius = Math.max(dimensions.length() * 4, 12);
    camera.position.copy(center).add(new T.Vector3(
      radius * Math.sin(phi) * Math.sin(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.cos(theta),
    ));
    camera.lookAt(center);
  }
  camera.zoom = zoom;
  camera.updateProjectionMatrix();
  if (renderer) renderer.setSize(Math.max(world.clientWidth, 1), Math.max(world.clientHeight, 1), false);
  render();
}

function fitWorld() {
  if (currentView === 'full') {
    const width = Math.min(viewport.clientWidth, viewport.clientHeight * 1.77683);
    world.style.width = `${width}px`;
    world.style.height = `${width / 1.77683}px`;
  } else {
    world.style.width = '';
    world.style.height = '';
  }
  updateCamera();
}

const views = {
  front: { theta: 0, phi: Math.PI / 2, label: '正面' },
  left: { theta: -Math.PI / 2, phi: Math.PI / 2, label: '左侧' },
  back: { theta: Math.PI, phi: Math.PI / 2, label: '背面' },
  right: { theta: Math.PI / 2, phi: Math.PI / 2, label: '右侧' },
  meadow: { theta: 0, phi: Math.PI / 4, label: '45° 草坪视角 · 近看人物' },
  full: { theta: 0, phi: Math.PI / 4, label: '草坪全景 · 原页面视角' },
};

function setView(view = 'meadow') {
  if (!views[view]) view = 'meadow';
  currentView = view;
  theta = views[view].theta; phi = views[view].phi; zoom = 1;
  document.body.classList.toggle('full-meadow', view === 'full');
  group.position.copy(view === 'full' ? map(64, 77) : new T.Vector3());
  $('#view-label').textContent = views[view].label;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
  setHeadPose(view === 'meadow' || view === 'full' ? 'lookup' : 'neutral');
  fitWorld();
  return cameraState();
}

// Capture the imported local matrix once, before applying any preview pose.
// The pivot/rotation are expressed in the native glTF scene coordinate system.
function captureHeadBaseline() {
  headNode = model.getObjectByName('painted-head');
  headBaseline = null;
  if (!headNode?.isMesh) { headNode = null; return; }
  model.updateMatrixWorld(true);
  if (headNode.matrixAutoUpdate) headNode.updateMatrix();
  const nativeFromParent = new T.Matrix4().copy(model.matrixWorld).invert()
    .multiply(headNode.parent.matrixWorld);
  headBaseline = {
    matrix: headNode.matrix.clone(),
    matrixAutoUpdate: headNode.matrixAutoUpdate,
    position: headNode.position.clone(),
    quaternion: headNode.quaternion.clone(),
    scale: headNode.scale.clone(),
    nativeFromParent,
    parentFromNative: nativeFromParent.clone().invert(),
  };
}

function setHeadPose(mode = 'neutral') {
  headPose = mode === 'lookup' ? 'lookup' : 'neutral';
  if (headNode && headBaseline) {
    if (headPose === 'lookup') {
      // P^-1 * pivotRotation * P * originalLocalMatrix. Always start from the
      // imported baseline, never from the previous pose: repeated clicks cannot drift.
      headNode.matrix.copy(headBaseline.parentFromNative)
        .multiply(lookUpRotation)
        .multiply(headBaseline.nativeFromParent)
        .multiply(headBaseline.matrix);
      headNode.matrixAutoUpdate = false;
      headNode.matrix.decompose(headNode.position, headNode.quaternion, headNode.scale);
    } else {
      headNode.position.copy(headBaseline.position);
      headNode.quaternion.copy(headBaseline.quaternion);
      headNode.scale.copy(headBaseline.scale);
      headNode.matrix.copy(headBaseline.matrix);
      headNode.matrixAutoUpdate = headBaseline.matrixAutoUpdate;
    }
    headNode.matrixWorldNeedsUpdate = true;
    model.updateMatrixWorld(true);
  }
  const supported = Boolean(headNode && headBaseline);
  $('#head-neutral').disabled = !supported;
  $('#head-lookup').disabled = !supported;
  $('#head-neutral').setAttribute('aria-pressed', String(headPose === 'neutral'));
  $('#head-lookup').setAttribute('aria-pressed', String(headPose === 'lookup'));
  $('#head-pose-label').textContent = supported ? '头部姿态' : '头部姿态暂不可用';
  const state = { mode: headPose, supported, node: 'painted-head', pivot: headPivot.toArray(), matrixRotationXDegrees: headPose === 'lookup' ? -12 : 0 };
  if (window.verification) window.verification.headPose = state;
  render();
  return state;
}
$('#head-neutral').addEventListener('click', () => setHeadPose('neutral'));
$('#head-lookup').addEventListener('click', () => setHeadPose('lookup'));

function setColorMode(mode = 'paint') {
  paintFaithful = mode !== 'aces';
  model?.traverse(object => {
    if (!object.isMesh) return;
    for (const material of [].concat(object.material)) { material.toneMapped = !paintFaithful; material.needsUpdate = true; }
  });
  $('#paint-faithful').setAttribute('aria-pressed', String(paintFaithful));
  $('#runtime-aces').setAttribute('aria-pressed', String(!paintFaithful));
  if (window.verification) window.verification.colorMode = paintFaithful ? 'paint-faithful' : 'runtime-aces';
  render();
  return paintFaithful ? 'paint-faithful' : 'runtime-aces';
}
$('#paint-faithful').addEventListener('click', () => setColorMode('paint'));
$('#runtime-aces').addEventListener('click', () => setColorMode('aces'));

function cameraState() {
  return {
    view: currentView, theta, phi, zoom, headPose,
    camera: camera.position.toArray(),
    modelPosition: group.position.toArray(),
    target: currentView === 'full' ? [0, 0, 0] : center.toArray(),
    frustum: [camera.left, camera.right, camera.top, camera.bottom],
  };
}

function customOrbit() {
  if (currentView === 'full') {
    const retainedHeadPose = headPose;
    setView('meadow');
    setHeadPose(retainedHeadPose);
  }
  currentView = 'orbit';
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', 'false'));
  $('#view-label').textContent = '自由旋转视角';
}
function orbit(dx, dy) {
  customOrbit();
  theta -= dx * .008;
  phi = T.MathUtils.clamp(phi + dy * .008, .08, Math.PI - .08);
  updateCamera();
}
function zoomBy(factor) { zoom = T.MathUtils.clamp(zoom * factor, .35, 4); updateCamera(); }

// Pointer capture keeps drags working outside the viewport; two fingers pinch to zoom.
const pointers = new Map();
let pinchDistance = 0;
viewport.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  viewport.setPointerCapture(event.pointerId);
  viewport.focus({ preventScroll: true });
  pinchDistance = 0;
});
viewport.addEventListener('pointermove', event => {
  const before = pointers.get(event.pointerId);
  if (!before) return;
  const after = { x: event.clientX, y: event.clientY };
  pointers.set(event.pointerId, after);
  if (pointers.size === 1) orbit(after.x - before.x, after.y - before.y);
  else {
    const [a, b] = [...pointers.values()];
    const distance = Math.hypot(a.x - b.x, a.y - b.y);
    if (pinchDistance) zoomBy(distance / pinchDistance);
    pinchDistance = distance;
  }
});
function clearPointer(event) { pointers.delete(event.pointerId); pinchDistance = 0; }
for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) viewport.addEventListener(type, clearPointer);
viewport.addEventListener('wheel', event => { event.preventDefault(); zoomBy(Math.exp(-event.deltaY * .001)); }, { passive: false });
viewport.addEventListener('dblclick', () => setView('meadow'));
viewport.addEventListener('keydown', event => {
  const keys = { ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, -12], ArrowDown: [0, 12] };
  if (keys[event.key]) { event.preventDefault(); orbit(...keys[event.key]); }
  else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomBy(1.15); }
  else if (event.key === '-' || event.key === '_') { event.preventDefault(); zoomBy(1 / 1.15); }
  else if (event.key === 'Home') { event.preventDefault(); setView('meadow'); }
});
window.addEventListener('blur', () => { pointers.clear(); pinchDistance = 0; });
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
$('#zoom-in').addEventListener('click', () => zoomBy(1.15));
$('#zoom-out').addEventListener('click', () => zoomBy(1 / 1.15));
$('#reset').addEventListener('click', () => setView('meadow'));
new ResizeObserver(fitWorld).observe(viewport);

function disposeModel(root) {
  const textures = new Set(), geometries = new Set(), materials = new Set();
  root?.traverse(object => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of [].concat(object.material || [])) {
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  textures.forEach(texture => texture.dispose());
  materials.forEach(material => material.dispose());
  geometries.forEach(geometry => geometry.dispose());
}
async function loadModel() {
  if (loading || !renderer) return;
  const request = ++generation;
  loading = true; window.ready = false;
  $('#reload').disabled = true;
  $('#loading').hidden = false; $('#loading').classList.remove('failed');
  $('#loading-message').textContent = '正在准备人物…';
  $('#status').textContent = '正在加载模型…'; $('#status-dot').className = 'dot';
  try {
    const url = new URL(file, location.href);
    url.searchParams.set('previewReload', String(Date.now()));
    const loaded = await new GLTFLoader().loadAsync(url.href, progress => {
      if (progress.total) $('#status').textContent = `正在加载模型… ${Math.round(progress.loaded / progress.total * 100)}%`;
    });
    if (request !== generation) { disposeModel(loaded.scene); return; }
    group.clear(); disposeModel(model);
    gltf = loaded; model = gltf.scene;
    captureHeadBaseline();
    const nativeBounds = new T.Box3().setFromObject(model);
    const nativeCenter = nativeBounds.getCenter(new T.Vector3());
    dimensions = nativeBounds.getSize(new T.Vector3());
    if (!Number.isFinite(dimensions.length()) || dimensions.length() <= 0) throw new Error('GLB has no visible mesh bounds');
    // Normalize only the display position. Geometry, materials and scale remain untouched.
    const display = new T.Group();
    display.position.set(-nativeCenter.x, -nativeBounds.min.y, -nativeCenter.z);
    display.add(model); group.add(display);
    center = new T.Vector3(0, dimensions.y / 2, 0);
    const meshes = [], materials = new Map(); let triangles = 0;
    model.traverse(object => {
      if (!object.isMesh) return;
      object.castShadow = true; object.receiveShadow = true;
      const geometry = object.geometry;
      const count = (geometry.index?.count || geometry.attributes.position?.count || 0) / 3;
      triangles += count;
      meshes.push({ name: object.name, type: object.type, triangles: count, vertices: geometry.attributes.position?.count, uv: geometry.attributes.uv?.count, color: geometry.attributes.color?.count });
      for (const material of [].concat(object.material)) materials.set(material.uuid, {
        name: material.name, type: material.type, vertexColors: material.vertexColors,
        map: material.map ? { width: material.map.image?.width, height: material.map.image?.height, colorSpace: material.map.colorSpace, flipY: material.map.flipY } : null,
      });
    });
    window.verification = {
      loaded: true, file, threeRevision: T.REVISION, triangles, meshes, materials: [...materials.values()],
      dimensions: dimensions.toArray(), nativeBounds: { min: nativeBounds.min.toArray(), max: nativeBounds.max.toArray() },
      lighting, renderer: { toneMapping: 'ACESFilmicToneMapping', outputColorSpace: 'srgb', exposure: renderer.toneMappingExposure, pixelRatio: renderer.getPixelRatio(), shadowMap: 'PCFSoftShadowMap' },
      animations: gltf.animations.length, skinnedMeshes: meshes.filter(mesh => mesh.type === 'SkinnedMesh').length,
      originalRuntimeCamera: { position: [0, 12, 12], target: [0, 0, 0], elevationDegrees: 45, W, H },
    };
    $('#status').textContent = '实际模型 · 可拖动旋转'; $('#status-dot').className = 'dot loaded';
    $('#model-stats').textContent = '真实三维模型 · 当前仅检查造型';
    $('#loading').hidden = true;
    setColorMode(paintFaithful ? 'paint' : 'aces');
    setView(params.get('view') || 'meadow');
    window.ready = true;
  } catch (error) { fail(error); }
  finally { loading = false; $('#reload').disabled = false; }
}
$('#reload').addEventListener('click', loadModel);
window.preview = { setView, pose: setView, setColorMode, setHeadPose, reload: loadModel, render, cameraState, getScene: () => scene, getCamera: () => camera, getModel: () => model, lighting };
setView(params.get('view') || 'meadow');
await loadModel();
