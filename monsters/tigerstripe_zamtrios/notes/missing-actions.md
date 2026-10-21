# Tigerstripe Zamtrios: 4U actions with no GU uEm067_00 handler (static RE, 2026-10-21)

4U = MH4U v1.1 (`dump/mh4u.asm`), class uEm022, W = `[this+0xe28]`, work = `[this+0x8d88]`. GU = MHGU 1.4 main, class
uEm067_00, rec = `[this+0x1428]`, work = `[this+0xcac0]`. Tags: **C** confirmed in code, **S** strong, **G** guess.
Scratch scripts (not in the repo): dump/scratch/tigerstripe-session/`miss/` (`ann.py` = 4U listing with literals and apimap2 names, `d2.py`
= dispatcher emulation with r1..r3, `g7.py` / `gtab.py` = GU jump tables).

## 1. The gap list

GU dispatch (C):
- slot 125 `0xf78f98`, jump table `0xf79000`: categories 3, 4, 5, 9, 14, 15 -> `f790cc` -> `bl 0xca118` -> `b f79188`.
  `0xca118` (and `0xca10c`) = `ldr r1,[r0]; ldr r1,[r1,#0x3dc]; bx r1` = slot 247 = action end. The action ends on
  the frame it starts.
- Category 7: `0xf75678`, table `0xf756a4` (num - 6, 198 entries). It handles 6-13, 24-35, 52-56, 58, 61-69, 71-76,
  202 and 203. Every other number goes to `f75b38` -> `b 0xca10c` (end).
- Category 2: table `0xf6eb40` handles 0..37 only. 38+ -> `0xca10c`.
- Categories 8 and 12 handle only num 0.
- Remap slot 127 `0xf69184` = 4U slot 46 `0x759488`: 0/0..2 -> 1/5 in mode 2, 2/0 -> 2/6, 1/0 -> 1/1, 1/22 -> 1/65.
  It touches no gap action.
- `tools/tzreport.py` treats categories 2, 8 and 12 as fully handled, so a 2/n>=38 or an 8/12 n!=0 would not be
  flagged.

4U uEm022 dispatch (C): slot 44 `0x758880`. Category 3 = `0x747084`:
- 3/0..3 -> `0x747a78(r1 = num)`
- 3/4 -> `0x747554`
- 3/80..85 -> `0x74714c(r1 = num % 3, r2 = num >= 83)` (Zamtrios)

Category 7 = `0x756240` (num - 6 table `0x75626c`, 87+ in compare trees).

| (cat,num) | 4U handler | reached by | GU | tag |
|---|---|---|---|---|
| 3/3 | 0x747a78 r1=3 | em092 EMC g1 s154 `14 01 00 03 03` | base end | C (seen in game x9) |
| 3/4 | 0x747554 | EMC s157, s158, s165 | base end | C (seen) |
| 7/70 | 0x74ff88 | EMC s153 `... 00 07 46` | default f75b38 | C (seen) |
| 7/77, 7/78 | 0x751464 r1=0/1 | EMC s152, s171 (`2e` if/else pair) | default | C (7/78 seen) |
| 7/200 | 0x7549a4 | EMC s167 | default | C |
| 7/201 | 0x754be8 | EMC s168 | default | C |
| 3/0, 3/1, 3/2 | 0x747a78 r1=0/1/2 | only the ledge chain 0x7550f8 (section 4) | base end | S: unreachable in our port |
| 3/83..85 | 0x74714c | the ledge chain with mode 2 (only from 2/82), any em | base end | S: unreachable |

- **No missing handler chains to another action.** All six end through vt+0x164 (C).
- The tokenizer's other gap refs are artifacts (G); 4U uEm022 has no handler for them either:
  - 1/111, 4/111, 7/111, 8/111: 0x6f is an opcode byte.
  - 5/0, 5/1, 5/8: 4U category 5 has no case.
  - 12/1: category 12 handles only num 0 in both games.
  - 0/11, 0/73, 0/78, 0/87, 0/255: category 0 = {0, 1, 2, 7} in both games.
- 4U cat-7 numbers 80-139 and 1/82 (also absent in GU) are out of scope (S):
  - em092's EMC never references them.
  - They chain only among themselves: 1/82 -> 7/116; 7/118, 7/119, 7/135..139 -> 7/116..139.
- GU's own em067_00_cmdtbl has the same 3:3, 3:4, 7:70/77/78/200/201 byte patterns. GU Zamtrios has the same dead
  references.

GU action start (slot 129 -> `f6925c` = 4U vt47 `0x75b758`) runs even for unhandled actions. Its TS list
(`f694a8`) already does:
- 3/0..4 -> `0xac0ec(this, rec+0x40, 3, 0)`
- the work+0xf counter: 3/3 and 7/70 reset it, other category-7 actions increment it

**Missing in GU's list (C): 7/77 and 7/78.** 4U `0x75bb10` calls `0x911f58(this, &W+408, 3, 0)` for them. Meaning: an
RNG chance (%) gated by W+0x7a64 > 0, probably a drop roll (G). GU = `0xac0ec` (S 99/99).

## 2. Shared translation tables

### 2a. Callees (4U -> GU)
| 4U | GU | role |
|---|---|---|
| 0x94e350 / 0x9190c4 | setMotion 0xaff40 / setMotionEx 0xafda4 | C |
| 0x75d9f0 / 0x749fd4 / 0x753d24 | GU inlines them: setMotion / setMotionEx / setMotionSpeed 0xb0870, then **TS flag** `work[0x10] = 1` (variant 1 and category in {1,2,3,7}) | C (phase1 A) |
| 0x91ab1c(kind, s0, s1) | motionCheck 0xb0a24(self, kind, NULL, s0, s1) | C |
| 0x941dbc(f) | at_frame 0xb0a30 = motionCheck(0, f, 0) | C (same thunk) |
| 0xb05df4 | isMotionEnd 0xb0a84 | C |
| vt+0x164 | slot 247 (vt+0x3dc) | C |
| 0x9167ec | setTargetMode 0xbc8b0 | C |
| 0x91b3f4 | stopMove 0x7bdd4 | C/S |
| 0x91db84(step, off) | turnToTarget 0x76cc4 | C |
| 0x914dfc / 0x933144 | attack 0x7df94 / attackEx 0x7dc2c | C |
| 0x922cd8 | 0x7fcbc (rec+0x36b = 1) | S 99/99 |
| 0x93c6c8 | 0xc0410 (rec+0x3a2 = 2) | S 99/99 |
| 0x92e9d4(v) | 0xbca40: if state class rec+0x1ba in {0,3,6}: pos.y += v * rec+428 * rec+432; then setTargetMode(1) | 4U body C, map S |
| 0x916140(v) | 0xbf7bc: rec+0x5c = v, rec+0x1b9 = 1 | C (same body) |
| 0x93e4e8(h) | 0xbf5e8: 1 when pos.y <= ground query (+ h * size factor) | S 99/99 |
| 0x9110c8 | 0x7d718: pos += v*dt + a*dt^2/2, then v += a*dt (world space) | S 99/99, body shape C |
| 0x9165cc(angles, 1) | accelVel 0x7a8dc(self, rec+0x50, 1) | C (game.h) |
| 0x91150c(angles, 1) | rotateVel 0x7cab8(self, rec+0x50, 1) | C |
| 0x936ea8(i) | partMeatBase 0xbab88 | C |
| 0x91ad80 | 0xbd128 (anger reset; Tigerstripe skips it) | C (phase 1) |
| 0x93cfd4(n) | 0x9d104 (status timer rec+0x5d32 / 0x5d30 = max(1, n * table(2)+12)) | C (same body) |
| 0x910c6c(j, id) | camShakeJoint 0xc24d8(self, j, id, 0) | C (em089) |
| 0x9200a4(m, s0, s1) | layer1MotionW 0xb03e8 | C (game.h) |
| 0xb054e0(w) | layer1SetWeight 0x726dc (this+0x638) | C |
| this+656 | motionFrame 0xb09e4 (this+0x500) | C |
| 0x93093c / 0x930894 | jointPos 0xc1708 / joint matrix 0xc1660 | C (em089) |
| 0x568c8c(y, x) -> u16 | atan2f 0x13efd70, radians -> x 65536/2pi | S |
| 0xaacda4(a, b) | inline sqrt(dx^2 + dz^2) | C (4U body) |
| 0x9276b4(0, m1, m2, [sp] 4) | findTargetEx 0xa6d04 (map-point search, -1 = none) | C (7/10 pairing) |
| 0x924040(pt, s) | 0xa77b0(self, pt, s): ground y at the point | C (7/10 pairing) |
| 0x955478 | 0x7b5f8 | C (7/10 pairing) |
| 0x91df20()->+0x48 | 0x712a4(self) returns the vec3 pointer itself | C (7/10 pairing) |
| 0xb0709c(&t) | timerDown 0x72128(self, &t, 1.0f) (4U has no scale arg) | C |
| 0x9175a8(ang, a, b) | 0x76e8c: in window a..b, yaw += ang / (b - a) * frac * motion speed | C (same body) |
| 0x911cb4 | speedFactor 0xbe5d4 | C |
| 0x94ef9c | setActionNext 0x76984 | C |
| 0x661d18 (uShell005 tremor) | GU request 0x48c4f0, shell id 0x122 (sp_01), kind by scale (section 2c) | C |
| 0x6620c4 (uShell016) | GU id 0x123 (sp_02) has only kinds 0 = 4U 13 and 1 = 4U 47 | UNMAPPED for 38 / 49 |
- apimap_table.md is wrong on one row: 0xb054e0 is the layer-1 weight setter, not 0xb09e4 (C).

### 2b. Fields (4U -> GU)
| 4U | GU | tag / evidence |
|---|---|---|
| W+0x144 / 0x145 / 0x146 | rec+0x1a1 / 0x1a2 / 0x1a3 | C |
| W+352 / 356 / 360 / 364 (vel) | rec+0x10 / 0x14 / 0x18 / 0x1c | C |
| W+372 (accel y) | rec+0x24 | C |
| W+384 | rec+0x5c | C |
| W+408 / 412 (pos, pos.y) | rec+0x40 / 0x44 | C |
| W+396 (ground y) | rec+0x34 | C (7/10) |
| W+424 (angles) | rec+0x50 | C |
| W+0x1ac (yaw) | rec+0x54 | C |
| W+468 (timer) | rec+0x1bc | C (7/10) |
| W+536 (target slot 0) | rec+0x1d0 | S |
| W+0x1c9 (mode) | rec+0x1bb | C |
| W+0x55a / 0x55c | rec+0x528 / 0x52a | C (7/10; 0x74838c = f78578) |
| W+0x628 | rec+0x5bc | C (7/10) |
| W+0x979 | rec+0x919 | C (7/10) |
| W+0x958 (count) | rec+0x8f0 | C (7/10) |
| W+0x820 + 32i (u32 angle) | rec+0x7bc + 32i | C (7/10) |
| W+0x960..0x96c | rec+0x900..0x90c | C (7/10) |
| W+0x7438 / 0x7739 | **this**+0x7452 / this+0x7453 | C (12/0: 4U 0x754fa8 = GU f77ff8) |
| W+0x77e8 | rec+0x5b58 | C |
| W+0x1f1, 0x1f2, 0x1f3 = 0, W+0x1f4 = 255 | GU calls 0xb7584(this) (this+0x73f3 / 0x73f5 / 0x73f4 = 0, 0x73f6 = 255) | C |
| W+0x7a34 (f) / 0x7e70 (b) / 0x7a38 (h) | rec+0x5d24 / 0x5df8 / 0x5d28 | C (mode-2 block, below) |
| work+0, +0xc, +0xf, +0x10, +20 | same offsets on [this+0xcac0] | C for 0 / 0xc / 0x10, S for 0xf / 20 |
| W+0x1d9 (controller) | this+0x7420 (EN_CONTROLLED) | C |
| this+20 (dt) | this+28 | C |
| W+0x7948 = 1 | **UNMAPPED**: also set by 4U 0x75c850 when state class == 1 (with selectDataSet(1)); no counterpart found in uEm067. Weak fieldmap candidate: rec+0x5c8c | S (airborne marker) |
| W+0x14b (stage, 17 = 4U Dunes day) | **UNMAPPED**; GU current stage = `[[MAIN+0x188ca48]+0x48]` (stage.c), Dunes = 5 | S |
| this+0x8d20 (u32 angle, = W+0x7ef0) | **UNMAPPED**: read only at 0x750144 | G (some pitch) |

**Mode-2 entry block (C).** GU has this block at `f69e88..f69f70`, inside its own action-start for 10/175 from
mode 1:
- rec+0x1bb = 2
- work[0] = 4800.0f
- partMeatBase(0..7)
- work[0xc]++; if (work[0xc] >= 3) work[0xc] = 2
- if (variant == 0) 0xbd128(self)
- 0x9d104(self, 1000)
- 0xb7584(self)
- rec+0x5d24 = 0 (float), rec+0x5df8 = 0 (byte), rec+0x5d28 = 0 (half)

4U 3/x frame 24 (`0x747c6c..0x747d74`) is the same sequence. G: mode 2 is the puffed / inflated state.

### 2c. Tremor post (C)
4U `0x661d18(*0xef3cf0, this, &W+408, subtype 13, [sp] 0xffff, s0 scale)`. GU encodes the scale as the sp_01 kind.
Kind k uses HTS group k, with radii 600 / 780 / 990 / 1080 / 240 for kinds 0..4:
- 13 x 1.3 = kind 1 (f6e528, f73e90)
- 13 x 1.8 = kind 3 (f71f14)
- 5 x 0.4 = kind 4
- **13 x 1.65 = 990 = kind 2.** GU's code never posts kind 2; it is the leftover of the 3/x landing. Our arc keeps
  GU's shell01 kinds 0..4.

Post = copy of GU `f71ef8..f71fb4` with kind 2:
- `p = 0x3faf28(64, 16)`
- `p+0` = `MAIN(0x1755698) + 8`, `+4` = 0x122, `+8` = kind, `+0xc` = self
- `+0x10..0x18` = rec+0x40..0x48, `+0x1c` = 0
- `+0x20..0x28` = the vec3 at `MAIN(0x191e850)`, `+0x2c` = 0
- `+0x30..0x38` = rec+0x50..0x58
- `+0x3c` (u16) = 0xffff
- then `0x48c4f0(*(void **)MAIN(0x1892550), p, 0, 0)`

## 3. Handlers (transcription order; `flag()` = the TS speed flag `work[0x10] = 1`)
Every handler ends through slot 247. **All step bytes are rec+0x1a1 / 0x1a2 / 0x1a3.** `mc(k, a, b)` =
motionCheck(self, k, 0, a, b).

### 3a. 3/0..3/3 `0x747a78(v = num)`: Tigerstripe's jump (3/3 aimed at the target, G: puff-up body slam)
Every frame: `0x7fcbc(self)`. In steps != 0, h = 556.
- **Step 0:**
  - step = 1; setTargetMode(0); rec[0x52a] = 1; stopMove()
  - setMotionEx(0x450, 2, 4.0, 0.0); flag()
  - v = 0 / 1 / 2: vel.y = 66 / 110 / 40, vel.z = 20. v = 3: nothing.
- **Step 1:**
  - setMotionSpeed(0.85); flag()
  - if `mc(9, 28, 64)` and v == 3: turnToTarget(455, 0)
  - if `mc(1, 68, 0)`: this[0x7452] = 0, this[0x7453] = 0, rec[0x5b58] = 1
  - rec[0x52a] = 1
  - if at_frame(24): mode-2 block (2b; Tigerstripe skips 0xbd128)
  - if isMotionEnd:
    - step = 2; 0xc0410(); 0xbca40(556)
    - 0xbf7bc(DT * 350 - 700)
    - setMotion(0x451, 1e-7, 0); flag()
    - Peak height H = 870 / 1540 / 545 / 1500 for v = 0..3 (300 otherwise).
    - v == 3 only: d = (target - pos).xz normalized; s = |target - pos|.xz / 60; vel = (d.x s, 0, d.z s); rec[0x1c] = 0.
      Target = rec+0x1d0.
    - Then for every v: accel.y (rec+0x24) = -2H/900; vel.y = 2H/30. The apex is reached after 30 frames.
- **Step 2:**
  - 0xbf7bc(0); rec[0x919] = 1; rec[0x52a] = 1; 0xc0410()
  - movement: v == 3 -> 0x7d718(self) (world-space ballistic); else accelVel(rec+0x50, 1) (local velocity)
  - W+0x7948 = 1 (unmapped)
  - if `mc(9, 0, 60)`: turnToTarget(273, 0)
  - if vel.y < 0 and 0xbf5e8(556):
    - step = 3; setTargetMode(0); setMotion(0x452, 0, 0); flag()
    - attack(0, 54); attackEx(1, 67, 64)
    - tremor kind 2 (2c)
    - camShakeJoint(-1, 1, 0)
- **Step 3:** isMotionEnd -> end.
- em tests: only `0x747d14` (skip 0x91ad80 for 92).

### 3b. 3/4 `0x747554` (no em test; aimed jump without the mode change)
Every frame: `0x7fcbc`.
- **Step 0:** step = 1; setTargetMode(0); rec[0x52a] = 1; setMotionEx(0x46b, 2, 6.0, 0.0); flag().
- **Step 1:**
  - setMotionSpeed(0.85); flag(); rec[0x52a] = 1
  - if at_frame(4): layer1MotionW(0x450, 4.0, 0.0)
  - if `mc(3, 4, 28)`: layer1SetWeight(1 - (28 - motionFrame()) / 24)
  - if at_frame(28): step = 2; setTargetMode(0); stopMove(); setMotion(0x450, 0.0, 28.0); flag()
- **Step 2:** same as 3a step 1 with v = 3, without the frame-24 block. At the motion end, step = 3 and H = 1500.
- **Step 3:** = 3a step 2 with v == 3 (0x7d718).
- **Step 4:** isMotionEnd -> end.

### 3c. 7/70 `0x74ff88` (G: deflate blast, leaves mode 2)
- **Step 0:** step = 1; setTargetMode(0); setMotion(0x455, 4.0, 0.0); flag().
- **Step 1:** turnToTarget(242, 0). At at_frame(90): step = 2, then:
  - Spawn point: J = jointPos(131); M = jointMatrix 0xc1660(131); P = J - 60 * M.row1 (rows of 16 B, offset (0, -60, 0)).
  - Aim: T = rec+0x1d0 with T.y += 100. a = u16(atan2(-(T.y - P.y), |T - P|.xz)) - u32 this+0x8d20 (**unmapped**).
  - Clamp a: if a < 0x8000, a = min(a, 0xe39) (20 deg); else a = max(a, 0xf555) (-15 deg).
  - Post uShell016: subtype 38 if W+0x14b == 17 (4U Dunes) else 49.
    - Event struct: +0 u32 joint 131; +8 offset (0, -60, 0, 0); +0x18 u8 0; +0x1a u16 a (x angle); +0x1c u16 0.
    - Length s0 = 4000; [sp] 0xffff, 0, 0.
  - 38 / 49 (C): life 21 frames, attack records 33 / 39: window frames 7..21, power 80, type 2, +0x0b 0x3c, flags 0x11,
    volume 19 / 21. Same spawn SE (201) as 13 / 40.
  - The uShell016 ctor adds the owner's x angle (W+0x1a8) to +0x1a (em089_shell016.c notes).
  - GU has no kind for 38 / 49. Two options: generalise `monsters/gogmazios/module/em089_shell016.c` (a 4U uShell016
    port) with Tigerstripe's records, or add kinds 2 / 3 to our shell02 family (the sp_02 param carries no pitch: G).
- **Step 2:** at_frame(134): rec+0x1bb = 0. isMotionEnd -> end.

### 3d. 7/77, 7/78 `0x751464(v = 0 / 1)`: rolling along walls with ledge steps
GU already has the same step as 7/10's variant-1 path `f71894..f71c44` (C, side by side). Differences: the masks, the
window, and the wall loop.
- **Step 0:** step = 1; rec[0x1a2] = 0; setTargetMode(0); setMotion(v ? 0x456 : 0x454, 4.0, 0.0); flag();
  attack(0, v ? 66 : 65). Also call the missing `0xac0ec(self, rec+0x40, 3, 0)` (section 1).
- **Step 1, Zamtrios:** only the motion-end check.
- **Step 1, Tigerstripe:**
  - **If rec[0x1a2] != 0:**
    - 0x7fcbc(); 0xc0410(); rec[0x528] = 1, rec[0x5b58] = 1, rec[0x5bc] = 1; if rec[0x1a2] == 2: rec[0x919] = 1
    - if findTargetEx(0, 66560, **20480**, 4) == -1: wall loop
    - 0x7b5f8(self)
    - if ground (rec+0x34) <= pos.y (rec+0x44) and rec[0x1a2] == 1: stopMove(); pos.y = ground
    - if pos.y <= ground and rec[0x1a2] == 2: same
    - if timerDown(&rec[0x1bc], 1.0): stopMove(); pos.y = ground; rec[0x900..0x908] = *0x712a4(self);
      rec[0x90c] = 0; rec[0x1a2] = 0
  - **Else, if `mc(9, 105, 137)`:**
    - r = findTargetEx(0, 1024, 20480, 4). If r != -1: rec[0x1a2] = 1.
    - Else r = findTargetEx(0, 65536, 20480, 4). If r == -1: go to the end check. Else rec[0x1a2] = 2.
    - g = 0xa77b0(r, 1.8); rec[0x34] = g; dy = g - rec[0x44]
    - if |dy| > 700: rec[0x1a2] = 0 and **return (no end check this frame)**
    - stopMove()
    - rec[0x1a2] == 1: vel.y = dy / 34; rec[0x900..] = vec + (0, dy + 100, 0); rec[0x90c] = 0. Else: vel.y = dy / 68.
    - rec[0x1bc] = 68
  - End check: isMotionEnd -> end.
- **Wall loop**, for i < rec[0x8f0], with a = u32 rec[0x7bc + 32i]:
  - (1) if (a - 8193) < 0x3fff (u32): target = a + (v ? 0x4000 : 0xc000)
  - (2) re-read a; if (a - 40961) < 0x2fff: target = a + (v ? 0xc000 : 0x4000)
  - For each hit, turn the yaw toward target by at most step = u32(DT * 1280):
    - d = u16(target - yaw)
    - if d < 0x8000: yaw = d >= step ? u16(yaw + step) : target
    - else: yaw = (0x10000 - d) >= step ? u16(yaw - step) : target
  - 4U stores the unmasked target in the "else" cases. GU's 7/10 does the same; mask it to u16 if unsure.
- 7/10 uses 4096 (search) / 16384 (active) and window 140..242. It turns only when (a - 16384) > 32768.

### 3e. 7/200 `0x7549a4`
- **Step 0:** step = 1; setTargetMode(0); setMotion(0x46a, 6.0, 0.0); flag(); attackEx(0, 59, 2); rec[0x1bc] = 600.
  Zamtrios: 0x40a / index 9.
- **Step 1:** if `mc(1, 140, 0)`: step = 2.
- **Step 2:**
  - 0x76e8c(self, 0xff4a, 0.0, 600.0). The literal is the u32 65354: a slow positive spin (~0.6 deg / frame), not
    -182 (C: 4U `vcvt.f32.s32` of a 32-bit word).
  - if !timerDown(&rec[0x1bc], 1.0) and findTargetEx(0, 66560, 8192, 4) == -1: return
  - if `mc(1, 310, 0)`: step = 3; setMotion(0x466, 20.0, 0.0); flag(). Zamtrios: 0x406.
- **Step 3:** isMotionEnd -> end.
- 0x46a loops from frame 156, so the action runs until the 600-frame timer runs out or a map point is found (S).

### 3f. 7/201 `0x754be8` (motion 0x46b for both ems: Tigerstripe-only in practice)
- **Step 0:**
  - step = 1; setTargetMode(0); rec[0x1a2] = 3; rec[0x1a3] = 0; stopMove()
  - vel = (-10.8, 0, 16.6667) * speedFactor(); rec[0x1c] = 0
  - setMotion(0x46b, 6.0, 0.0); flag()
- **Step 1:** step = 2; attack(0, 61). Falls through to step 2 in the same frame.
- **Step 2:**
  - if `mc(9, 115, 175)`: 0xc0410(); rotateVel(rec+0x50, 1)
  - if at_frame(172): camShakeJoint(-1, 5, 0)
  - At at_frame(190), Zamtrios posts a tremor (13 x 1.8); **Tigerstripe skips it** (C, 0x754d74).
  - if rec[0x1a3] == 0 and findTargetEx(0, 66560, 8192, 4) != -1: rec[0x1a3]++; rec[0x1a2] = 1
  - else if rec[0x1a2] > 1 and `mc(1, 210, 0)`: rec[0x1a1] = 1; rec[0x1a2]--; vel.x = -vel.x;
    setMotion(0x46b, 20.0, 80.0); flag()
  - isMotionEnd -> end.
- Result: up to 3 side slides that alternate direction. They stop early once a map point is found.

### 3g. Hook points (GU)
- **Category 7:** entry hook on `0xf75678`. It pushes {r4, lr}, and its only caller is `f790f0 bl`, followed by
  `b f79188`. For variant 1 and num in {70, 77, 78, 200, 201}: run ours, return "replaced". The dispatcher tail
  `f79188` (work[0x10] -> setMotionSpeed(rec+0x398 x 0.95)) still runs (C).
- **Category 3:** there is no function of its own. Entry hook on `0xca118` keyed on LR == MAIN(0xf790dc) (the
  `bl` at f790d8, followed by `b f79188`), then return "replaced".
  - 0xca118 is a 12-byte thunk with many callers: check that the hook framework can patch it.
  - A mid hook at f790cc cannot skip the bl.
  - Either way, GU's dispatcher head (mode-2 0xaa20c, rec+0x5d34) has already run.

## 4. Ledge chain `0x7550f8(this, mode)` -> 1 if chained (C)
```
if (!controller) return 0;                                  // W+0x1d9 == 1 -> GU this+0x7420
if (findTargetEx(0, 0x8000000, 8192, 4) != -1) return 0;
r = findTargetEx(0, 1024, 8192, 4);
if (r != -1) {
    dy = 0xa77b0(r, 1.6) - pos.y;                        // compared as signed bits: dy < 0 counts as <= 500
    if (dy <= 500)  { work[20] = dy; n = mode == 2 ? 83 : em92 ? 0 : 80; }
    else if (dy <= 2200) { work[20] = dy; n = mode == 2 ? 84 : em92 ? 1 : 81; }
    else return 0;
} else {
    r = findTargetEx(0, 65536, 8192, 4); if (r == -1) return 0;
    0xa77b0(r, 1.6);                                        // result unused
    n = mode == 2 ? 85 : em92 ? 2 : 82;
}
setActionNext(3, n); return 1;
```
- The 3/0..2 handler (3a) never reads work[20]. The heights are fixed per v.

**Callers (C, emulated with d2.py).** Correction to phase1 section E: for em 92 it is **not** called from 2/0, 2/1
or 2/6.
- `0x748ca0` (2/0, 2/27, 2/35, 2/87, 2/89) calls it in step 1 only when r1 == 1. That means 2/87 and 2/89; 2/0
  passes r1 = 0.
- `0x748db4` (2/1, 2/15..20, 2/28, 2/80, 2/82, 2/88) calls it after timerDown only when r2 is 1 or 2. That means
  2/80, 2/88 (mode 1) and 2/82 (mode 2).
- `0x7494c0` (2/6, 2/32, 2/33) calls it only for em 21 / 91.

**Reachability (S): none of 2/80..89 is reachable in our port.**
- No em092 EMC bytes `00 02 50..59`.
- No constant chain in uEm022.
- No remap to them.
- GU category 2 stops at 37.

GU hook points if needed:
- 2/0 is inlined at `f6ec04`.
- 2/87, 2/89 would be `f6d83c` (= 0x748ca0, the r1 test dropped): step 1 at `f6d8f4`, before inRange(0, 32).
- 2/1 -> `f6d944(0, 0)` (= 0x748db4): the chain point is right after timerDown at `f6dbcc`.
- 2/6 -> `f6e268`.
- A runtime log line for any 2/n >= 38 would settle reachability.

## 5. Motions (C: em092 LMT headers, our arc ships em092's banks unchanged)
Header = track pointer, track count, frames, loop frame.

| id | bank / index | frames | loop | used by |
|---|---|---|---|---|
| 0x450 | 4/80 | 77 | - | 3a start, 3b layer-1 + main |
| 0x451 | 4/81 | 69 | 52 | airborne (3a, 3b) |
| 0x452 | 4/82 | 143 | - | landing |
| 0x454 / 0x456 | 4/84 / 4/86 | 275 | - | 7/77 / 7/78 |
| 0x455 | 4/85 | 195 | - | 7/70 |
| 0x466 | 4/102 | 103 | - | 7/200 end |
| 0x46a | 4/106 | 325 | 156 | 7/200 |
| 0x46b | 4/107 | 323 | - | 3/4 start, 7/201 |

- The phase-1 variant-1 set is present: 0x462..0x46e = bank 4 98..110, 0x370 / 0x372 = bank 3 112 / 114.
- None of these exist in GU em067_00.
- 0x453 (4/83) is empty in em092. Only vt168's motion test names it.

## 6. Multiplayer
GU runs slot 125 on every machine. setActionNext on a non-controller only marks a replay. Damage is not sent over the
network (shells.md section 4). So:
- **Run every handler on every machine, ungated:** motions, flags, velocities, attack arming (each machine tests its
  own hunters), the tremor and uShell016 posts. GU's own tremor posts (f71ef0, f6e528) are not gated either (C).
- **Controller only:** the ledge chain (4U gates it on W+0x1d9; GU this+0x7420), because it calls setActionNext. It is
  unreachable anyway.
- **Synced inputs:**
  - Target slot rec+0x1d0: 3/3 and 3/4 jump direction and distance, 7/70 pitch. Resolved from the target kind sent in
    the action message (S).
  - Mode byte rec+0x1bb (game.h: net-synced).
- **May diverge per machine (S):**
  - Map-point searches (7/77, 7/78, 7/200, 7/201, 4U and GU 7/10 alike: ungated) and timers can take different
    branches when positions differ. They only steer local movement; GU's position sync corrects it.
  - 0xac0ec (7/77-78 action start) rolls the RNG. GU's slot 129 does the same for its other actions on every machine.

## 7. Open (what a runtime log should capture)
1. `this+0x8d20` at 7/70 frame 90, next to rec+0x50 (x angle) and the joint-131 matrix. This decides the pitch base.
2. W+0x7948 meaning. Log the GU candidates (rec+0x5c8c) while airborne in 3/x, or skip the store.
3. 0xa6d04 results with mask2 20480 (7/77-78) and 8192 (7/200, 7/201) on GU Dunes stage 5. The area data is shared
   from em067_00 and may not cover stage 5 (plan.md risk).
4. GU attackdata records 54, 59, 61, 65, 66, 67 against 4U em092 (GU differs from 4U in 34 of 69 records; not checked
   per index).
5. Whether any 2/n >= 38 or 3/0..2 ever starts. tzreport needs categories 2, 8 and 12 added to its decode.
6. The uShell016 38 / 49 visuals: the effect and volume tables were not resolved to EFL / radii.
