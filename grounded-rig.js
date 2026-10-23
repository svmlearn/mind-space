import * as T from 'three';
const UP = new T.Vector3(0, 1, 0),
  V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z),
  clamp = (x, a, b) => Math.max(a, Math.min(b, x)),
  smooth = x => {
    x = clamp(x, 0, 1);
    return x * x * (3 - 2 * x);
  },
  delta = (a, b) => Math.atan2(Math.sin(b - a), Math.cos(b - a));
function frame(h, t, yaw) {
  const y = t.clone().sub(h).normalize(),
    right = V(Math.cos(yaw), 0, -Math.sin(yaw)),
    x = right.addScaledVector(y, -right.dot(y)).normalize(),
    z = V().crossVectors(x, y).normalize();
  return new T.Matrix4().makeBasis(x, y, z).setPosition(h);
}

// Gait constants, in character units (the model is ~2 units tall at scale 1).
const HIP = 0.89, // resting hip height
  ANKLE = 0.16, // ankle height above ground when planted
  SEG = 0.405, // thigh / shin length
  REACH = 2 * SEG - 0.012, // keep a hint of knee bend: never fully straight, never stretched
  SIDE = 0.185, // half stance width
  HEAD_SCALE = 0.92; // slightly smaller head reads closer to the painted turnaround

/*
 * Grounded rig.
 *
 * The rig works in "character space" (`position`, `feet`). The holder group that owns the
 * model is then scaled for depth (`setScale`) around the on-screen position (`world`).
 * Character-space motion is world motion divided by the scale, so a planted foot stays
 * exactly where it touched the lawn at any depth (no foot sliding when small/far away).
 *
 * Walking is phase driven: while moving, steps alternate on a cadence that depends on speed,
 * each foot is placed predictively so it lands ahead of the hip and stays put through stance.
 * When not moving (start, stop, turning on the spot) the feet catch up with short settle steps.
 */
export class GroundedRig {
  constructor(model, position, holder = null) {
    this.model = model;
    this.holder = holder;
    this.scale = 1;
    this.world = position.clone(); // last on-screen position (world units)
    this.position = position.clone(); // character-space hip position
    this.target = position.clone();
    this.yaw = 0;
    this.yawVel = 0;
    this.targetYaw = 0;
    this.velocity = V();
    this.feet = {};
    this.swing = null;
    this.next = 'L';
    this.clock = 0;
    this.sinceLand = 1;
    this.moving = false;
    this.walk = 0; // 0..1 blend between standing and walking posture
    this.bones = {};
    this.correction = {};
    this.length = {};
    const rest = {
      body: [
        [0, 0.9, 0],
        [0, 1.48, 0],
      ],
      head: [
        [0, 1.47, 0],
        [0, 2.02, 0],
      ],
    };
    for (const [s, x] of [
      ['L', -SIDE],
      ['R', SIDE],
    ]) {
      rest['thigh' + s] = [
        [x, 0.91, 0],
        [x, 0.54, 0.04],
      ];
      rest['shin' + s] = [
        [x, 0.54, 0.04],
        [x, 0.16, 0],
      ];
      rest['foot' + s] = [
        [x, 0.16, 0],
        [x, 0.16, 0.22],
      ];
      rest['arm' + s] = [
        [Math.sign(x) * 0.34, 1.37, 0],
        [Math.sign(x) * 0.44, 0.91, 0],
      ];
      this.feet[s] = { p: position.clone().add(V(x, ANKLE, 0)), yaw: 0 };
    }
    this.resetHolder();
    model.updateMatrixWorld(true);
    for (const [n, [a, b]] of Object.entries(rest)) {
      const bone = model.getObjectByName(n);
      if (!bone) throw Error('Missing bone ' + n);
      this.bones[n] = bone;
      const h = V(...a),
        t = V(...b);
      this.length[n] = h.distanceTo(t);
      this.correction[n] = frame(h, t, 0)
        .setPosition(0, 0, 0)
        .invert()
        .multiply(bone.matrixWorld.clone().setPosition(0, 0, 0));
    }
    this.pose();
  }
  setTarget(p, moving) {
    this.target.copy(p);
    this.moving = moving;
  }
  setScale(s) {
    this.scale = clamp(s, 0.3, 2);
  }
  face(yaw) {
    this.targetYaw = yaw;
  }
  /** Jump straight to a spot (reduced motion): no steps, feet placed under the hips. */
  snap(p) {
    this.target.copy(p);
    this.world.copy(p);
    this.position.copy(p);
    this.velocity.set(0, 0, 0);
    this.swing = null;
    this.moving = false;
    this.walk = 0;
    this.yaw = this.targetYaw;
    this.yawVel = 0;
    for (const side of ['L', 'R']) {
      this.feet[side].p.copy(this.sideTarget(side));
      this.feet[side].yaw = this.yaw;
    }
    this.pose();
  }
  rot(p, yaw = this.yaw) {
    return p.applyAxisAngle(UP, yaw);
  }
  sideTarget(side, p = this.position, yaw = this.yaw) {
    return p.clone().add(this.rot(V(side === 'L' ? -SIDE : SIDE, ANKLE, 0), yaw));
  }
  setBone(n, h, t, yaw = this.yaw, s = 1) {
    const b = this.bones[n],
      m = frame(h, t, yaw)
        .multiply(this.correction[n])
        .multiply(new T.Matrix4().makeScale(s, h.distanceTo(t) / this.length[n], s));
    b.parent.updateWorldMatrix(true, false);
    b.parent.matrixWorld.clone().invert().multiply(m).decompose(b.position, b.quaternion, b.scale);
    b.updateWorldMatrix(false, false);
  }
  resetHolder() {
    if (!this.holder) return;
    this.holder.position.set(0, 0, 0);
    this.holder.scale.set(1, 1, 1);
    this.holder.updateMatrixWorld(true);
  }
  placeHolder() {
    if (!this.holder) return;
    const s = this.scale;
    this.holder.scale.setScalar(s);
    this.holder.position.set(this.world.x - s * this.position.x, 0, this.world.z - s * this.position.z);
    this.holder.updateMatrixWorld(true);
  }
  /** Cadence and swing time for a character-space speed. */
  timing(speed) {
    const period = clamp(0.4 - 0.09 * speed, 0.27, 0.4); // time per step
    return { period, swing: period * 0.8 };
  }
  startSwing(side, duration, end, lift) {
    end.y = ANKLE;
    this.swing = {
      side,
      t: 0,
      duration,
      lift,
      start: this.feet[side].p.clone(),
      end,
      yaw: this.feet[side].yaw,
      endYaw: this.yaw,
    };
  }
  update(dt) {
    this.clock += dt;
    // World motion -> character-space motion (divide by depth scale).
    const step = this.target.clone().sub(this.world);
    step.y = 0;
    this.world.copy(this.target);
    this.position.addScaledVector(step, 1 / this.scale);
    const raw = step.multiplyScalar(dt ? 1 / (dt * this.scale) : 0);
    this.velocity.lerp(raw, 1 - Math.exp(-dt * 14));
    if (raw.lengthSq() < 1e-8 && this.velocity.lengthSq() < 1e-4) this.velocity.set(0, 0, 0);
    const speed = this.velocity.length();

    // Turn with a critically damped spring instead of a constant rate: eases in and out.
    const err = delta(this.yaw, this.targetYaw),
      k = 70;
    this.yawVel += (k * err - 2 * Math.sqrt(k) * this.yawVel) * dt;
    this.yawVel = clamp(this.yawVel, -7, 7);
    this.yaw += this.yawVel * dt;
    if (Math.abs(err) < 0.002 && Math.abs(this.yawVel) < 0.01) {
      this.yaw = this.targetYaw;
      this.yawVel = 0;
    }

    const moving = this.moving && speed > 0.12;
    this.walk += ((moving ? 1 : 0) - this.walk) * (1 - Math.exp(-dt * (moving ? 6 : 4)));
    const { period, swing } = this.timing(speed);
    this.sinceLand += dt;

    let landed = false;
    if (this.swing) {
      const s = this.swing,
        f = this.feet[s.side];
      s.t += dt;
      // Keep steering the airborne foot towards where the hip will be when it lands.
      if (moving && s.t < s.duration * 0.75) {
        const remaining = s.duration - s.t;
        s.end = this.sideTarget(s.side, this.position.clone().addScaledVector(this.velocity, remaining + period - s.duration / 2));
        s.end.y = ANKLE;
        s.endYaw = this.yaw;
      }
      const u = Math.min(1, s.t / s.duration),
        v = smooth(u);
      f.p.copy(s.start).lerp(s.end, v);
      f.p.y += s.lift * Math.sin(Math.PI * u) ** 1.5;
      f.yaw = s.yaw + delta(s.yaw, s.endYaw) * v;
      if (u === 1) {
        f.p.copy(s.end);
        f.yaw = s.endYaw;
        this.swing = null;
        this.next = s.side === 'L' ? 'R' : 'L';
        this.sinceLand = 0;
        landed = true;
      }
    }

    if (!this.swing && !landed) {
      const other = s => (s === 'L' ? 'R' : 'L'),
        error = s => {
          const d = this.feet[s].p.clone().sub(this.sideTarget(s));
          d.y = 0;
          return d.length();
        };
      if (moving) {
        // Phase driven: next foot lifts after a short double-support pause.
        const side = this.next;
        if (this.sinceLand >= period - swing) {
          const end = this.sideTarget(side, this.position.clone().addScaledVector(this.velocity, swing + period - swing / 2));
          this.startSwing(side, swing, end, 0.07 + 0.03 * Math.min(1, speed));
        }
      } else {
        // Settle: move whichever foot is furthest from its rest spot, one at a time.
        let side = this.next;
        if (error(side) < error(other(side)) - 0.02) side = other(side);
        const turn = Math.abs(delta(this.feet[side].yaw, this.yaw));
        if ((error(side) > 0.05 || turn > 0.22) && this.sinceLand > 0.04) {
          this.startSwing(side, 0.2, this.sideTarget(side), 0.05);
        }
      }
    }
    this.pose();
    return (
      this.moving ||
      !!this.swing ||
      speed > 0.001 ||
      this.walk > 0.01 ||
      Math.abs(delta(this.yaw, this.targetYaw)) > 0.002 ||
      Math.abs(this.yawVel) > 0.01 ||
      ['L', 'R'].some(s => {
        const d = this.feet[s].p.clone().sub(this.sideTarget(s));
        d.y = 0;
        return d.length() > 0.05 || Math.abs(delta(this.feet[s].yaw, this.yaw)) > 0.22;
      })
    );
  }
  pose() {
    this.resetHolder();
    const s = this.swing,
      u = s ? Math.min(1, s.t / s.duration) : 0,
      active = s ? Math.sin(Math.PI * u) : 0,
      walk = this.walk,
      fw = this.rot(V(0, 0, 1)),
      right = this.rot(V(1, 0, 0));

    // Weight shift: hips drift over the stance foot while the other foot is in the air.
    const stanceSign = s ? (s.side === 'L' ? 1 : -1) : 0; // +x is the right foot
    const hip = this.position.clone();
    hip.addScaledVector(right, stanceSign * 0.028 * active * (0.5 + 0.5 * walk));
    // Inverted pendulum bob: highest mid-swing, lowest at heel strike.
    hip.y = HIP - 0.02 * walk + 0.022 * active * walk;
    // Never let the legs over-stretch: drop the hips instead (no rubbery shins).
    for (const [side, x] of [
      ['L', -SIDE],
      ['R', SIDE],
    ]) {
      const f = this.feet[side].p,
        joint = hip.clone().add(this.rot(V(x, 0.02, 0))),
        horiz = Math.hypot(f.x - joint.x, f.z - joint.z),
        maxY = f.y + Math.sqrt(Math.max(0, REACH * REACH - horiz * horiz)) - 0.02;
      if (maxY < hip.y) hip.y = Math.max(HIP - 0.12, maxY);
    }

    // Torso: lean into the walk, slight roll towards the stance side.
    const lean = 0.05 * walk + 0.012 * active,
      top = hip
        .clone()
        .add(V(0, 0.58, 0))
        .addScaledVector(fw, lean)
        .addScaledVector(right, stanceSign * 0.01 * active);
    this.setBone('body', hip, top);
    // Head leads turns a little and stays steadier than the torso.
    const look = this.yaw + clamp(delta(this.yaw, this.targetYaw) * 0.45, -0.45, 0.45);
    const headBase = top.clone();
    const headTop = headBase
      .clone()
      .add(V(0, 0.55 * HEAD_SCALE, 0))
      .addScaledVector(fw, -lean * 0.4);
    this.setBone('head', headBase, headTop, look, HEAD_SCALE);

    for (const [side, x] of [
      ['L', -SIDE],
      ['R', SIDE],
    ]) {
      const f = this.feet[side],
        h = hip.clone().add(this.rot(V(x, 0.02, 0))),
        d = f.p.clone().sub(h),
        length = Math.min(REACH, d.length()),
        dir = d.clone().normalize(),
        bend = fw.clone().addScaledVector(dir, -fw.dot(dir)).normalize(),
        knee = h
          .clone()
          .addScaledVector(dir, length / 2)
          .addScaledVector(bend, Math.sqrt(Math.max(0.0004, SEG ** 2 - length ** 2 / 4)));
      const ankle = h.clone().addScaledVector(dir, length);
      this.setBone('thigh' + side, h, knee);
      this.setBone('shin' + side, knee, ankle);
      // Swing foot: toe points down after push-off, then lifts slightly before heel strike.
      const pitch = s && s.side === side ? (u < 0.5 ? -0.32 : -0.18) * Math.sin(2 * Math.PI * u) : 0,
        toe = this.rot(V(0, 0, 0.22 * Math.cos(pitch)), f.yaw);
      toe.y = 0.22 * Math.sin(pitch);
      this.setBone('foot' + side, ankle, ankle.clone().add(toe), f.yaw);

      // Arms swing opposite to the leg on the same side, scaled by how far that foot is
      // in front of / behind the hip: smooth, zero when standing, no snapping.
      const footFwd = f.p.clone().sub(this.position).dot(fw),
        armSwing = clamp(-footFwd * 0.55, -0.17, 0.17) * (0.35 + 0.65 * walk),
        sh = hip
          .clone()
          .add(this.rot(V(Math.sign(x) * 0.34, 0.48, 0)))
          .addScaledVector(fw, lean * 0.8);
      this.setBone(
        'arm' + side,
        sh,
        sh.clone().add(this.rot(V(Math.sign(x) * (0.1 - 0.02 * walk), -0.45 + Math.abs(armSwing) * 0.15, armSwing))),
      );
    }
    this.model.updateMatrixWorld(true);
    this.placeHolder();
  }
}
