# GU EFL move block (w3): particle motion, and how to carry MHF position curves

Static study, 2026-11-05 (MHGU 1.4 main, Ghidra project dump/gu/ghidra; corpus = the 1648 unique EFLs of the GU
romfs, 15086 entries). Marks: **C** traced in code, **S** strong inference (data / code shape), **G** guess.
Complements gu-efl-units.md (whose "Move block, kind 2" table this confirms and corrects, see the end).

## 1. Move block

### Dispatch (C)
- Kind = w3 low nibble -> gen +0x40 bits 16-19 and 20-23. The bind step 0xa59ce4 rewrites bits 20-23:
  kinds 1 / 2 / 8 with **move +0x03 bit 0** (the common `+0x00 = 0x01000000`) become kinds **9 / 10 / 11** =
  "simple" variants (init 0xa62b1c: no curves, no collision; steps 0xa67520 / 0xa676bc / 0xa63db4). 7713 of 9068
  GU kind-2 entries have it (S). **Kind 5 without a curve at +0x70 fails generator creation** (0xa59ce4 returns 0).
  Kinds 5 / 6 get a 0x20-B side record (gen +0x1b8, path scale, below).
- Init per particle: 0xa5d538 (called by the particle creator 0xa5ca24) -> common 0xa5f77c, then by kind:
  0 inline (copy the spawn record), 1 inline, 2 / 8 0xa6015c, 5 / 6 inline, 9-11 0xa62b1c.
- Per frame: 0xa62db8 (called by every generator class's particle loop, Billboard 0xa7dd74) switches on bits
  20-23: 0 0xa62f78 -> 0xa64a04, 1 -> 0xa64dd8, 2 -> 0xa65404(p, 1), 5 -> 0xa66790, 6 -> 0xa66ec4, 8 0xa63c34 ->
  0xa65404(p, 0) + 0xa7ac70, 9 / 10 / 11 simple. Each loop first does age += 1 (particle +0x14), then the step;
  step returns 0 -> particle freed.
- Note: 0xa6a004 / particle +0x60 is the **UV-animation** state (reads unit +0x44), not motion (C). The motion
  record is a separate array: `gen +0x24 + gen +0xc8 + (particle +8 lo16) * gen +0xda`.

### Motion record (per particle; float index [n] = byte n*4) (C)
| off | meaning |
|---|---|
| +0x00..+0x08 | last non-zero move direction / delta |
| +0x10 [4] | bits 0-1 state: 0 frozen (step does nothing), 1 with collision (gen +0xf0 set), 2 free, 3 dead; bit 2 = gravity x emitter scale-y; bits 24-31 = move +0x04 byte 0 |
| +0x14 [5] | move +0x08 + r x +0x0c (arg of the owner hook when [4] >> 24 != 0) |
| +0x20 [8] | speed (kinds 1/2) |
| +0x24 [9] | kind 2: damping factor; kind 1: acceleration magnitude |
| +0x28 [10] | gravity per frame; +0x2c [11] accumulated fall speed (subtracted from Y each frame) |
| +0x30..+0x40 | per-particle randoms for the curves (angle x/y/z, speed, fall) |
| +0x44 [0x11] | flags: 1 path mode (kind 5), 2 rotate the path, 0x10 angle curve live, 0x20 integer angle curve, 0x40 speed curve live, 0x80 fall curve live, 0x100 / 0x200 follow emitter, 0x400 follow timer; hi16 = frame countdown |
| +0x50 [0x14..] | kinds 1/2: velocity (world, units / frame); kind 5: spawn position (emitter local) |
| +0x60 [0x18..] | kind 1: acceleration vector (dir x [9]) |
| +0x70 [0x1c..] | kind 5: path rotation (Euler, rad); +0x80 [0x20..]: path-curve randoms |

### Direction = Euler angles (C: 0xa77288 -> 0x9bd8e0 -> 0x321694)
dir = axis . R(angles, order), row-vector, then x emitter scale (gen +0x18 +0xe0..+0xe8) and x emitter rotation
(gen +0x18 rows 0-2) -> world. Fixed at spawn unless an angle curve is live (then re-rotated by the *current*
emitter matrix every frame).
- axis = move +0x04 bits 8-11: 0 +X, 1 -X, 2 +Y, 3 -Y, 4 +Z, 5 -Z (C for the negatives; the positives are
  runtime-initialised constants 0x191e880 / 890 / 8a0, S).
- order = move +0x04 bits 12-15 (corpus: always 4, or 0). **Order 4 = v . Rz . Rx . Ry** (C, disassembled case,
  checked numerically), with Rx = [[1,0,0],[0,c,s],[0,-s,c]] etc. So +Z axis -> (sin y cos x, -sin x, cos x cos y);
  +Y axis (0x4200, rz = 0) -> (sin x sin y, cos x, sin x cos y): x = cone angle from +Y, y = azimuth.
  Order 0 = v . Rx . Ry . Rz (S, row 0 only). Orders 1-3, 5 not decoded (jump table 0x3216bc).
- Units: radians (S: corpus ranges 2 pi); integer angle curves use 2 pi / 4096 per unit (C, 0xafccc0).

### Kinds 1 / 2 / 8 layout (0x50 B + appended curves; offsets are from the move block)
| off | type | meaning | ev |
|---|---|---|---|
| +0x00 | u32 | bit 1 clear -> gravity x emitter scale-y; 0x08 -> follow emitter translation (record 0x300); 0x20 -> follow for +0x48 frames (0x700); bit 4 -> gen +0xdc bit 25; bit 24 -> simple kind 9-11 (above) | C |
| +0x04 | u32 | byte 0 -> record [4] >> 24 (!= 0: owner vfunc +0x104 each frame, G: field hook); bits 8-11 axis; 12-15 order; hi16 = offset of a collision sub-block (gen +0xf0; set -> state 1, ground test 0xa77ce0 / 0xa7784c) | C |
| +0x08, +0x0c | f32 pair | -> record [5] | C |
| +0x10/14, +0x18/1c, +0x20/24 | f32 pairs | Euler angles x / y / z + random range (rad) | C |
| +0x28, +0x2c | f32 pair | initial speed + range (units / frame) | C |
| +0x30, +0x34 | f32 pair | gravity + range (units / frame^2, +down, world Y), x owner (gen +8) +0x1bc | C |
| +0x38 lo16 | u16 | offset of an angle vec3 curve (direction over age) | C |
| +0x3a | u16 | offset of a **speed curve** (scalar): speed = curve(age); dir = current velocity normalised | C |
| +0x3c | u16 | offset of a **fall-speed curve**: record [11] = curve(age) x emitter scale-y (world Y, +down) | C |
| +0x40, +0x44 | f32 pair | kind 2: damping per frame (velocity and speed x= d); kind 1: acceleration along the spawn direction | C |
| +0x48 | u16 / u16 | follow-emitter frames + random (with +0x00 0x20) | C |
| +0x50.. (kind 8, 0xc0 B) | | kind 8 = kind 2 without collision + 0xa7ac70; +0xa0..+0xa8 = 1, 1, 1 in the corpus | G |

Curves live per frame only when the header's bit 31 is clear; bit 31 set = evaluated once at spawn (C).

Per-frame order, kind 2 (0xa65404, C): age += 1; **pos += vel - (0, fall, 0)**; if angle curve: dir =
R(curve(age)); elif speed curve: dir = vel / |vel| (kept raw if |vel| < 1.19e-7 = FLT_EPSILON); vel = dir x speed
(speed = curve(age) if the speed curve is live, else record speed); fall = fall curve(age) if live; speed x= d,
vel x= d; fall += gravity; then collision (state 1) and follow (pos += emitter translation delta). Kind 1 (0xa64dd8)
is the same with vel += accel vector instead of the damping. The velocity used in step A was computed at age A - 1
(the spawn velocity in step 1). Motion never stops by itself (only d < 1, a curve going to 0, or a ground hit).

### Kind 0 (16 B) (C)
+0x00 flags (bit 1 gravity scaling, unused), +0x04 mode word (byte 0 hook, hi16 collision), +0x08/+0x0c pair ->
[5]. Each frame position = emitter matrix x (spawn local position x emitter scale) (0xa64a04): **attached to the
emitter, no motion**.

### Kind 5 = position curve ("path"), 0x80 B + appended vec3 curve (C: init 0xa5d538 case 5, step 0xa66790, position 0xa79c90)
**pos(age) = E . ((spawn_local + Rp . (S * curve(age))) * emitter scale)**, E = the current emitter matrix (gen
+0x18: rotation rows + translation), recomputed every frame (so the particle follows the emitter). Rp = Euler
rotation of +0x10..+0x24 (order = +0x04 bits 12-15), applied only when non-zero (record flag 2). S = path scale.

| off | type | meaning | ev |
|---|---|---|---|
| +0x00 | u32 | only bit 1 (gravity scaling after release) and the follow bits matter | C |
| +0x04 | u32 | order nibble (bits 12-15) for Rp; hi16 = collision block offset | C |
| +0x10..+0x24 | f32 pairs | path rotation x / y / z + range (rad); or +0x38 lo16 = an angle curve (live: flag 0x32) | C |
| +0x28/+0x2c, +0x30/+0x34, +0x3a, +0x3c, +0x48/+0x4c | | speed / gravity / speed curve / fall curve / acceleration **after release** (0xa7a164) | C |
| +0x40 | u32 | byte 0: release mode (0 none, 1 path speed, 2 speed +0x28/+0x2c, else 0); bit 8: release at the last key; bit 9: **die at the last key**; hi16: offset of an int curve for the countdown | C |
| +0x44 | u16 / u16 | release countdown frames + random (record hi16; release when it reaches 0, only with byte 0 != 0) | C |
| +0x50..+0x6c | f32 pairs | path scale x, y, z, uniform (value + range) -> gen +0x1b8: S = (x, y, z) x uniform (0xa59268) | C |
| +0x70 | u32 | **offset of the position curve** (vec3), required | C |

Release = switch to the kind-1 step with dir = last path delta (0xa7a164). After the last key the curve clamps,
so with +0x40 = 0 the particle simply stays at the last offset (C).

### Curves (C: 0xaf7958 scalar, 0xafb2bc vec3 float, 0xafca74 vec3 int, time 0xaed74c)
Header `u32 = count | type << 8 | flags << 24`; type byte 1: 2 = float (corpus), bit 0 set = integer vec3 keys.
- flags (byte 3): bits 24-26 time source (0 = particle age +0x14, 1 generator time, 2 / 3 owner +0x10c, 4 global);
  bits 27-29 interpolation (0 **linear**, 1 cubic through the neighbours, 2 another routine 0xaf7750, 3 hold the
  previous key; 4-7 -> 0); bit 30 loop (time wrapped into [first, last]); bit 31 = evaluate once at spawn.
- Keys: scalar 12 B `{u32 age, f32 value, f32 range}`; vec3 28 B `{u32 age, x, x range, y, y range, z, z range}`.
  Value = v + range x r, r = the particle's draw in [0, 1) (one per component).
- Age <= first key -> first value; age >= last -> last value; equal -> that key; between -> interpolated (C).
- Linear (mode 0) = (1 - t) a + t b for both scalar and vec3 (C scalar, S vec3: same code shape at 0xafb468).

## Corpus evidence (S)
| kind | entries | block size | typical values |
|---|---|---|---|
| 0 | 4998 | 16 | attached sprites / models |
| 1 | 543 (+32 Lite) | 0x50 | speed mostly 0, gravity +-0.1, +0x40 accel 0 (569 / 575) |
| 2 | 9005 (+63 Lite) | 0x50 (+ curves: 0x70, 0x80) | +0x04 0x4200 (5015) / 0x4400 / 0x4500; speed 10, 5, 1, 2, 6; gravity 0.1-0.5; damping 1.0 (4782), 0.98, 0.95, 0.9; angle x -0.175 + 0.349 |
| 5 | 239 (34 Billboards, 3 Polygons, 199 Models) | 0x80 + curve (0xc0 for 2 keys) | +0x50.. = 1,0,1,0,1,0,1,0 and +0x70 = 0x80 in all; +0x40 = +0x44 = 0 in all; header 0x00000202..05 (linear, age) |
| 6 | 2 | 0x80 | em021_00_004: +0x28 15 / 20, +0x78 200 / 300 (G: orbit) |
| 8 | 77 (59 Billboards) | 0xc0 | kind-2-like values |

Move-block curves in kinds 1 / 2: 1 speed curve (em019_04 `effect\em\em019\em019_04_900` entry 2: +0x00 = 0, i.e.
not simple; speed 40, gravity 2, speed curve at +0x50: {0: 40}, {30: 20}), 12 fall curves (em013_02
`em013_00_002`, em058_00 `em058_00_021_s` with header 0x18000202 = hold interpolation, em033_00 `em033_00_007`).

Kind 5 Billboards (position curve, offsets in emitter-local units, ages):
- `player/quest/w15.arc` `effect\cm\cm130_120` entry 6: keys {0: (0, 0, 0)}, {40: (0, 0, 150)}, +0x04 0x4400.
- `enemy/em083_00.arc` `effect\em\em083\em083_00_000` entry 0: {0: (0, 0, 1500)}, {30: (0, 0, 0)} (converging).
- `enemy/em012_00.arc` `effect\em\em012\em012_00_004` entry 0: rot x 0.0873, {0: 0}, {41: (0, 60, 400)}.
- `stage/m27d/a01.arc` `effect\em\em088\em088_00_014` entry 10 (Model): 5 keys {11: (0, 110, 0)} .. {63: (120, 420, -300)}.
- `player/quest/w04.arc` `effect\cm\cm123_041` entry 6 (Model): {1: 0}, {20: (0, 0, -20)}.

## 2. Recipe: MHF position curve -> GU kind 5 (exact for any number of linear keys)
MHF: pos(t) = spawn + R_spawn . curve(t), linear between keys, first / last value outside. GU kind 5 evaluates
the same thing directly (no integration, no off-by-one): pos(age) = E . (spawn_local + Rp . curve(age)).

1. Entry w3 = `(off - 0x30) << 8 | 0x05` (Lite bit 4 clear; a Billboard keeps cParticleGeneratorBillboard) (C).
2. Block = 0x80 B + curve, padded to 16 (S: corpus layout):
   ```python
   def move_path(keys, rot=(0, 0, 0), rot_r=(0, 0, 0), order=4, die_at_end=False, loop=False):
       """keys [(GU age, (x, y, z))] -> kind-5 move block (w3 type 0x05)"""
       b = bytearray(0x80)
       struct.pack_into('<II', b, 0, 0, order << 12 | 4 << 8)            # +0x04: Euler order, axis +Z (unused)
       for k in range(3):
           struct.pack_into('<ff', b, 0x10 + 8 * k, rot[k], rot_r[k])     # path rotation (0 = none)
       struct.pack_into('<I', b, 0x40, 0x200 if die_at_end else 0)
       struct.pack_into('<8f', b, 0x50, 1, 0, 1, 0, 1, 0, 1, 0)           # path scale
       struct.pack_into('<I', b, 0x70, 0x80)                              # curve offset
       c = struct.pack('<I', len(keys) | 2 << 8 | (0x40 << 24 if loop else 0)) + b''.join(
           struct.pack('<I6f', t, x, 0.0, y, 0.0, z, 0.0) for t, (x, y, z) in keys)
       blk = bytes(b) + c
       return blk + b'\0' * (-len(blk) % 16)
   ```
3. Key times: the converter's existing map `tm(f) = D + round(f x ls)` (GU ages, 2 per MHF tick, as the scale /
   colour curves). No key is needed before D: the curve clamps to the first value (C).
4. Key values: the MHF offsets in the same units as the PEL-record spawn base. The curve carries the whole offset
   (p0 included), so do not also add p0 to the spawn base. Note: particles() today only flags varying position
   curves; a constant non-zero position curve is dropped (no offset applied) (S, from reading mhffx2gu.py).
5. Spawn rotation: if the MHF rotation range is 0, rotate the keys by R_spawn in the converter and leave
   +0x10..+0x24 = 0 (order irrelevant; exact). With a random range, put (rot - range, 2 range) per axis in
   +0x10..+0x24 with the order nibble that matches MHF (GU: 4 = Z, X, Y; 0 = X, Y, Z) (C for GU; MHF order G).
   GU draws this rotation independently of the sprite roll (unit +0x170), so a correlated MHF draw is lost (C/G).
6. MHF loop flag (first key bit 0) -> header bit 30 (time wrapped into [first, last]) (C GU side, G match).
7. Life stays in the emit block. Optional `die_at_end` (+0x40 bit 9) kills the particle at the last key (C).

2-key case: keys [(tm(f0), p0), (tm(f1), p1)]: linear p0 -> p1 between the ages, p0 before, p1 after (C).
Multi-key: one GU key per MHF key, same values: exact (C; only the per-age sampling of the time map rounds).

Caveats: E is the **current** emitter matrix (C), so the particle moves with an emitter that moves or turns;
MHF keeps it at its spawn frame (S). Fine for effects posted at a fixed point; for attached posts the offset follows.
Whether gen +0x18 includes the element +0xbe transform is not traced (G).

Fallback (no kind 5, e.g. a class that rejects it): kind 2 with +0x00 = 0 (bit 24 clear, else the curves are
ignored), angles giving dir = normalize(p1 - p0) (order 4, +Z axis: x = -asin(dy), y = atan2(dx, dz)), damping
1.0, gravity 0, and a speed curve at +0x3a with linear keys {f0 - 1: eps}, {f0: v}, {f1 - 1: v}, {f1: eps}
(v = |p1 - p0| / (f1 - f0), eps = 1e-5: a zero speed loses the direction, FLT_EPSILON test above). Position after
age A = sum over k < A of speed(k), so the hold must end at f1 - 1 (C). Multi-key with turns needs an angle curve
too (re-rotated by the current emitter every frame). Kind 5 is simpler and exact.

## Corrections to gu-efl-units.md
- Move +0x10..+0x24: Euler angles, now C (0xa6015c / 0xa77288); +0x28 speed, +0x30 gravity, +0x40 damping: C.
- +0x48: follow-emitter frames (u16 + random), not a mode.
- +0x50..+0x6c of the "0xc0-B kinds" is the **path scale** of kinds 5 / 6 (gen +0x1b8, read by 0xa79c90), not a
  light colour; the 0xc0 size of kind 5 is 0x80 + a 2-key curve.
- `+0x00 = 0x01000000` selects the simple kinds 9-11 (no curves), C.
