import * as T from 'three';

/*
 * Interactive grass for the walking view.
 *
 * The lawn itself stays the painted image. On top of it we scatter small instanced
 * blades whose colours are sampled from that painting at each blade's root, so an
 * unbent blade almost disappears into the picture. Blades only fade in around the
 * character (and around its recent footprints), are pushed away from it in the
 * vertex shader, and spring back with a damped wobble once it has passed.
 * All per-blade work is on the GPU; the CPU only keeps a short trail of positions.
 */

const TRAIL = 16;
const LIFE = 2.2; // seconds a footprint keeps influencing the grass

const vertexShader = /* glsl */ `
  uniform vec4 uTrail[${TRAIL + 1}];
  uniform int uCount;
  uniform float uSpring;
  uniform float uWind;
  uniform float uTime;
  uniform vec2 uFade;
  uniform float uRadius;
  uniform float uReach;
  uniform vec4 uShadow; // xy: character root, zw: shadow direction * length
  attribute vec3 aRoot;  // x, z, yaw
  attribute vec3 aShape; // height, width, lean
  attribute vec3 aBase;
  attribute vec3 aTip;
  varying vec3 vColor;
  varying float vFade;

  void main() {
    float h01 = position.y;
    vec2 root = aRoot.xy;
    // Cheap early-out: blades far from the character (beyond the trail) are never drawn.
    if (distance(root, uTrail[0].xy) > uReach) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    vec2 bend = vec2(0.0);
    float vis = 0.0;
    for (int i = 0; i < ${TRAIL + 1}; i++) {
      if (i >= uCount) break;
      vec4 t = uTrail[i];
      vec2 d = root - t.xy;
      float dist = length(d);
      float life = t.z <= 0.0 ? 1.0 : 1.0 - smoothstep(${(LIFE * 0.45).toFixed(2)}, ${LIFE.toFixed(2)}, t.z);
      vis = max(vis, (1.0 - smoothstep(uFade.x, uFade.y, dist)) * life);
      float influence = 1.0 - smoothstep(0.0, uRadius, dist);
      float resp = t.z <= 0.0 ? 1.0 : mix(1.0, exp(-t.z * 3.2) * cos(t.z * 9.0), uSpring);
      vec2 dir = dist > 1e-4 ? d / dist : vec2(1.0, 0.0);
      bend += influence * resp * t.w * dir;
    }
    vFade = vis;
    if (vFade <= 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }

    float bl = length(bend);
    if (bl > 1.0) { bend /= bl; bl = 1.0; }

    float height = aShape.x;
    float c = cos(aRoot.z), s = sin(aRoot.z);
    vec3 p = vec3(position.x * aShape.y, h01 * height, aShape.z * h01 * h01 * height);
    vec3 w = vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z);
    w.xz += bend * (0.8 * height) * h01 * h01;
    w.y -= bl * bl * 0.3 * height * h01;
    if (uWind > 0.0) {
      float sway = sin(uTime * 1.7 + root.x * 1.3 + root.y * 0.7) * 0.025 * uWind;
      w.x += sway * h01 * h01;
    }

    // Soft contact shade: blades inside the character's cast shadow get darker.
    vec2 a = uShadow.xy, ab = uShadow.zw;
    float k = clamp(dot(root - a, ab) / max(dot(ab, ab), 1e-4), 0.0, 1.0);
    float sd = length(root - (a + ab * k));
    float wid = mix(0.16, 0.3, k) * length(ab) / 1.33;
    float shade = 1.0 - 0.3 * (1.0 - smoothstep(wid * 0.6, wid, sd));
    vColor = mix(aBase, aTip, h01 * h01) * shade;
    gl_Position = projectionMatrix * viewMatrix * vec4(root.x + w.x, w.y, root.y + w.z, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vFade;
  void main() {
    if (vFade < 0.02) discard;
    gl_FragColor = vec4(vColor, vFade);
    #include <colorspace_fragment>
  }
`;

export class MeadowGrass {
  constructor({ W, H, imageUrl, isFree, depthScale = () => 1, count = 22000 }) {
    this.depthScale = depthScale;
    this.W = W;
    this.H = H;
    this.imageUrl = imageUrl;
    this.isFree = isFree;
    this.count = count;
    this.object = new T.Group();
    this.trail = [];
    this.last = null;
    this.time = 0;
    this.reduced = false;
    this.uniforms = {
      uTrail: { value: Array.from({ length: TRAIL + 1 }, () => new T.Vector4()) },
      uCount: { value: 0 },
      uSpring: { value: 1 },
      uWind: { value: 0 },
      uTime: { value: 0 },
      uFade: { value: new T.Vector2(0.75, 1.6) },
      uRadius: { value: 0.55 },
      uReach: { value: 4 },
      uShadow: { value: new T.Vector4(0, 0, -1.07, 0.8) },
    };
  }

  toPct(x, z) {
    return { x: (x / this.W + 0.5) * 100, y: ((z * Math.SQRT1_2) / this.H + 0.5) * 100 };
  }

  async load() {
    const img = new Image();
    img.decoding = 'async';
    img.src = this.imageUrl;
    await img.decode();
    const cw = img.naturalWidth,
      ch = img.naturalHeight;
    const canvas = document.createElement('canvas');
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, cw, ch).data;
    const sample = (px, py) => {
      let r = 0, g = 0, b = 0, n = 0;
      for (let dy = -1; dy <= 1; dy++)
        for (let dx = -1; dx <= 1; dx++) {
          const x = Math.min(cw - 1, Math.max(0, Math.round(px) + dx));
          const y = Math.min(ch - 1, Math.max(0, Math.round(py) + dy));
          const i = (y * cw + x) * 4;
          r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
        }
      return [r / n / 255, g / n / 255, b / n / 255];
    };

    // Blade template: two segments, five vertices, x in [-0.5, 0.5], y = height fraction.
    const base = new T.BufferGeometry();
    base.setAttribute(
      'position',
      new T.Float32BufferAttribute([-0.5, 0, 0, 0.5, 0, 0, -0.32, 0.5, 0, 0.32, 0.5, 0, 0, 1, 0], 3)
    );
    base.setIndex([0, 1, 2, 2, 1, 3, 2, 3, 4]);
    const geo = new T.InstancedBufferGeometry();
    geo.index = base.index;
    geo.attributes.position = base.attributes.position;

    const roots = [], shapes = [], bases = [], tips = [];
    const zMin = -this.H / 2 / Math.SQRT1_2, zMax = this.H / 2 / Math.SQRT1_2;
    const color = new T.Color(), tip = new T.Color();
    let placed = 0, tries = 0;
    while (placed < this.count && tries < this.count * 4) {
      tries++;
      const x = (Math.random() - 0.5) * this.W;
      const z = zMin + Math.random() * (zMax - zMin);
      const pct = this.toPct(x, z);
      if (pct.y < 18 || pct.y > 99 || !this.isFree(pct)) continue;
      const [r, g, b] = sample((pct.x / 100) * cw, (pct.y / 100) * ch);
      // Root a touch darker (the shaded gaps between painted strokes), tip lighter and warmer
      // (the sunlit blade edges); a small per-blade variation keeps it from looking uniform.
      const v = 0.88 + Math.random() * 0.24;
      color.setRGB(r * 0.82 * v, g * 0.85 * v, b * 0.8 * v, T.SRGBColorSpace);
      tip.setRGB(Math.min(1, (r * 1.24 + 0.06) * v), Math.min(1, (g * 1.17 + 0.05) * v), Math.min(1, b * 1.02 * v), T.SRGBColorSpace);
      // Blades further up the lawn are further away in the painting: draw them smaller.
      const ds = this.depthScale(pct.y);
      roots.push(x, z, (Math.random() - 0.5) * 1.2);
      shapes.push((0.14 + Math.random() * 0.17) * ds, (0.028 + Math.random() * 0.02) * ds, (Math.random() - 0.5) * 0.5);
      bases.push(color.r, color.g, color.b);
      tips.push(tip.r, tip.g, tip.b);
      placed++;
    }
    geo.setAttribute('aRoot', new T.InstancedBufferAttribute(new Float32Array(roots), 3));
    geo.setAttribute('aShape', new T.InstancedBufferAttribute(new Float32Array(shapes), 3));
    geo.setAttribute('aBase', new T.InstancedBufferAttribute(new Float32Array(bases), 3));
    geo.setAttribute('aTip', new T.InstancedBufferAttribute(new Float32Array(tips), 3));
    geo.instanceCount = placed;

    this.material = new T.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader,
      fragmentShader,
      side: T.DoubleSide,
      transparent: true,
      toneMapped: false,
    });
    this.mesh = new T.Mesh(geo, this.material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 1;
    this.object.add(this.mesh);
    this.geometry = geo;
    return this;
  }

  setReducedMotion(on) {
    this.reduced = !!on;
    this.uniforms.uSpring.value = on ? 0 : 1;
    if (on) this.trail.length = 0;
  }

  /** Shadow footprint (world units) for the darkening term; dir = shadow direction * length. */
  setShadow(x, z, dx, dz) {
    this.uniforms.uShadow.value.set(x, z, dx, dz);
  }

  /** Returns true while blades are still springing back and need more frames. */
  update(dt, x, z, moving, scale = 1) {
    this.time += dt;
    this.uniforms.uTime.value = this.time;
    if (this.reduced) {
      this.trail.length = 0;
      this.last = null;
    } else {
      for (const p of this.trail) p.age += dt;
      while (this.trail.length && this.trail[this.trail.length - 1].age > LIFE) this.trail.pop();
      if (moving && (!this.last || Math.hypot(x - this.last.x, z - this.last.z) > 0.12 * scale)) {
        this.trail.unshift({ x, z, age: 1e-3, strength: 1 });
        if (this.trail.length > TRAIL) this.trail.length = TRAIL;
        this.last = { x, z };
      }
    }
    const u = this.uniforms.uTrail.value;
    u[0].set(x, z, 0, moving ? 1 : 0.55);
    this.trail.forEach((p, i) => u[i + 1].set(p.x, p.z, p.age, p.strength));
    this.uniforms.uCount.value = 1 + this.trail.length;
    let reach = 0;
    for (const p of this.trail) reach = Math.max(reach, Math.hypot(p.x - x, p.z - z));
    const f = 0.6 + 0.4 * scale;
    this.uniforms.uFade.value.set(0.75 * f, 1.6 * f);
    this.uniforms.uRadius.value = 0.55 * scale;
    this.uniforms.uReach.value = reach + 1.6 * f + 0.1;
    return !this.reduced && this.trail.length > 0;
  }

  dispose() {
    this.geometry?.dispose();
    this.material?.dispose();
  }
}
