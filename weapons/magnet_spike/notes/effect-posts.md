# Magnet Spike: where and when MHF posts its effects

Static study, 2026-11-04 (mhfo-hd.dll ZZ 2019-09-02, Ghidra copy dump/scratch/ghidra_fx; nothing run). Marks: **C** traced
in code, **S** strong inference, **G** guess. Action / motion numbers as in behaviour.md and msact.py. Effect runtime
(sets, A / E records): assets.md "## Effects".

## Conventions
- **Post forms** (C):
  - **EFX** `0x113d61f0` (fastcall, edx = set; stack: id, pos*, v*, scale*, rot*, 0) -> 0x113d35a0. World point,
    given once. v = (0, 0, 0) at every MS site (meaning open). scale = (1, 1, 1) unless noted. rot = radians,
    (pitch, yaw, roll): (0, hunter yaw, 0) unless noted.
  - **EFX0** `0x113d6500` (set, id; edx = pos*): the same with rot 0, scale 1.
  - **TASK** `0x113d66b0` (set, id, bone, x, y, z, flags) -> 0x1146aa50 (0x40 task). Attached: position = hunter
    bone `bone` matrix x translation (x, y, z) (getter 0x1146ab60 -> 0x10999ce0; bones < 21 = the hunter skeleton).
    Rotation getter 0x1146ac30. The task stores the owner id (P+0x7f8) but the call itself has no local gate.
  - **CARRIER** = MS special kind 4: `0x101e8120(owner, 0, 4, pos*, 0)` via 0x101e82b0(id, bone, scale) /
    0x101e8300 (id 0x4e) / 0x101e83d0 (set 0xfc6). Data: id, bone (-1 = none), scale, set. Init 0x101ea030 posts the
    set's `id | 0x8000` attached to the special (0x113d62d0, owner's client only) and gives it 120 ticks (+0x6a).
    Position getter 0x101e8b20: bone >= 0 -> that hunter bone's position (+ the spawn offset turned by the bone
    matrix for 0xfc5 1 / 2, 0xfc6 0x1e / 0x1f); else the special's own point. Per-id updates 0x101ea2a0 (0xfc5) /
    0x101ea930 (0xfc6) move or end some of them (noted per row). Scale getter 0x101e8cf0: (s, s, s); 0xfc5 2 and
    0xfc6 0x1e / 0x1f = (1, 1, s) (a length).
  - **HP(x, y, z)** = `0x1004d650`: hunter bone 0 position + R(yaw) (x, y, z), evaluated when posted (C). From the
    Magnetic Shock spots: z = forward, y = up (S).
- **MS task** `0x1004d700` (task type byte +2 = 0x3c, sub-kind byte +3; update 0x1004d810, one step per MHF tick, step
  counter +8 from 0). Created by 0x1004d3e0(kind in AL, param -> data +0x5a) (local hunter only, 0x1004d380) or
  directly (sub-kinds 0, 4, 6, 0xa, 0xd, 0xe). "t" below = this counter.
- **Frames**: "fN" = the first update with motion frame >= N (0x108ff7a0: frame +0x1dc >= N), armed only if the motion
  was seen before N (step bytes P+5 / P+6). Motion frames are 1/60 s.
- **Gates**: L = 0x10a94cb0 (the owner is this client's hunter); O = 0x10a82500 (owner's slot == the client's slot
  byte DAT_1e7fff3c+0x23f8, or offline); L+O = 0x1032fb30. M = Magnetise on in the current mode (0x1033c3c0(mode)).
  Mode = MS+0x64, 0 Cutting / 1 Impact (S: 0x10337cf9 sets 1 when MS flag 0x8000 "Impact origin" is set).
- Rumble calls (0x10b43370, 0x103362e0) are listed only as timing markers; they draw nothing.

## Posts
| site | set:id | form, where | when | gate | mark |
|---|---|---|---|---|---|
| **Triple Strike charge (34, block 0x10333c8c)** |
| 10333d7b | fc6:11 | TASK bone 10 (0, 0, 0) | level 0 -> 1: counter P+0xb24 >= T(kind) (20 ticks); same moment MS task kind 4 (10333d89) + rumble 7 | L+O | C |
| 10333d11 | fc6:e | TASK bone 10 (0, 0, 0) | counter >= the second threshold (34) at level >= 1: level := prm35 (0), post because 0 < 1, then auto-release 0x10337970. Once | L+O | C |
| 1004d9c1 | fc5:15 | TASK bone 14 (0, 0, 40 t/4) | MS task kind 4: t = 4, 8, 12 (z 40, 80, 120), then ends | - | C |
| 10338b8e | fc6:12 | CARRIER on bone 10 | event 26 (34 f50): the charge aura. 0x101ea930: removed once counter >= T - 1 (level 1); if the action is left first, posts fc6:13 (next row) and ends | owner | C |
| 101eaa34 | fc6:13 | TASK bone 10 (0, 0, 0) | charge released before level 1 (carrier fc6:12 still alive outside 34 / 18) | L+O | C |
| **Down Swipe variants (18-22, 52, 132, 133, 143, block 0x10333de3)** |
| 10333ee3 | fc6:f | TASK bone 10 | level 0 -> 1. The counter runs only with MS flag 0x20 (set only by event 26 = action 34; S: cleared on action change, 0x1032f030), and fc6:f has no A record: nothing visible | L+O | C |
| 10333e7f | fc6:e | TASK bone 10 | second threshold; level := prm32 (1), the "< 1" gate fails: never | L+O | C |
| **Magnetic Shock, MS task kind 0xf** (159 / 160: f8 of 1031 / 1032, 103354af; 162: first update of 1082, 1033441f) |
| 1004e738 | fc6:2d | EFX HP(-90, 0, 0) | t0 (+ rumble 0x17, 5) | L | C |
| 1004e7b6 | fc6:2d | EFX HP(-120, 0, 80) | t0 | L | C |
| 1004e88b | fc6:2d | EFX HP(-130, 0, 130) | t1 | L | C |
| 1004e8fe | fc5:54 | EFX HP(-30, 140, 250) | t1 | O, L | C |
| 1004e9d3 | fc6:2e | EFX HP(-120, 0, 170) | t3, with special #12 there | L | C |
| 1004eae7 | fc6:2e | EFX HP(-90, 0, 250) | t5, with #12 | L | C |
| 1004ebff | fc6:2f | EFX HP(-30, 0, 400) | t6 (#12 at t7) | L | C |
| 1004ed2f | fc6:30 | EFX HP(40, 0, 550) | t8 (#12 at t10, task ends) | L | C |
| **Magnetic Shock (whiff), kind 0x10** (95 / 96: f8 of 1031 / 1032; 161: first update of 1082) |
| 1004ee60 | fc6:32 | EFX HP(-150, 0, 0) | t0 (+ rumble 0x17, 5) | L | C |
| 1004ef58 | fc6:32 | EFX HP(-180, 0, 70) | t1 | L | C |
| 1004efcb | fc5:53 | EFX HP(-30, 140, 250) | t1 | O, L | C |
| 1004f0a4 | fc6:32 | EFX HP(-170, 0, 140) | t2 (shared call, S) | L | C |
| 1004f17d | fc6:33 | EFX HP(-110, 0, 270) | t3 | L | C |
| 1004f252 | fc6:34 | EFX HP(-20, 0, 450) | t5, task ends (shared call, S) | L | C |
| **Double Swipe extra, kind 0x11** (motion 1424 = 39 / 146 second motion, f20, O and M; 10336128) |
| 1004f32e | fc6:32 | EFX HP(-40, 0, -120) | t0 | L | C |
| 1004f0a4 | fc6:32 | EFX HP(-190, 0, -50); HP(-180, 0, 110); HP(-80, 0, 270) | t0; t1; t3 (shared call, S) | L | C |
| 1004f252 | fc6:33 | EFX HP(150, 0, 260) | t4, task ends (shared, S) | L | C |
| **Attraction (58 / 61 / 62 Cutting, 68 / 71 / 72 Impact)** |
| 1004f59f | fc5:3 | TASK bone 14 (30, 0, -20) Cutting / (20, 0, 140) Impact | action start -> MS task kind 0x12 / 0x13 by mode (10333fc1); t1 (+ rumble) | - | C |
| 1004f646 | fc5:4 | TASK bone 14 (30, 0, 150) / (-10, 0, 170) | same task, t3, ends | - | C |
| 10335729 | fc5:5 | CARRIER bone 14, offset (60, 0, 60) in motion 1472, else (0, 0, 170) | f10 of 1069 / 1079 / 1414 / 1415 / 1460 / 1472 (block 0x1033565d; group 1, 0x1032fb70, 0x100068d0 > 1: S marker valid) | owner | C |
| 10335782 | fc5:7 | EFX0 at the marker point (0x1033b6b0) | same f10 | O, L, marker | C |
| 103357d8 | (task) | MS task kind 9 | same motions, f24 | O | C |
| 1004dcfb | fc5:0 | CARRIER, world point on the hunter -> marker line at 300 + 220 n (MS block +0x18 / +0x30, S) | kind 9: every 2nd tick, n = t/2 up to (d - 300)/220, only while d (MS+0x40) > 500. 0x101ea2a0 turns it to the marker each tick and ends it within 350 | owner | C / S |
| 103358a2 | fc5:1 | CARRIER bone 14, (60, 0, 60) in 1472, else (0, 0, 170) | same motions, f30 | owner | C |
| 103358b9 | fc5:2 | CARRIER bone 14, (60, 0, 60) / (0, 0, 150), scale (1, 1, d/4000), d = marker distance | f30 (the beam; 0x101ea2a0 keeps it aimed at the marker) | owner | C |
| **Repulsion (66 Cutting -> kind 0xb, 67 Impact -> kind 0xc; action start, 103341b7 / 103341a4)** |
| 1004e21e | fc5:4e | CARRIER, world: bone 0 + 150 up + 100 / 200 / 300 toward the marker (d <= 500 / <= 1000 / more), pitch clamped (0x101ea2a0), scale 0.8 / 1.0 / 1.3 by the same bands; re-placed every tick | t2, marker present | O | C |
| 1004e278 | fc5:1 | TASK bone 14 (60, 0, 60) [66] / (0, 0, 170) [67] | t2 | - | C |
| 1004e2b2 | fc5:4d | EFX0 at the marker point | t2 | O, L | C |
| 1004df9c | fc5:4d | EFX bone 0 + R(yaw) (0, 100, -100) | t3, then the task ends | O, L | C |
| 1004dfcf | fc5:14 | EFX same point | t3, the not-O branch | L | C |
| **Guard (0x10332430, called from 0x10915290: S the guard reaction; group 1, local hunter)** |
| 1004dd68 | fc5:46 | TASK bone 14 (30, 0, -70) | action 14 with guard hits (MS+0x66, 0x1032b4f0) < 2 -> MS task kind 0xa; t0 (+ rumble 0xc) | - | C |
| 1004dd9e | fc5:47 | TASK bone 14 (40, 0, 100) | kind 0xa t0 | - | C |
| 1004de46 | fc5:15 | TASK bone 14 (30, 0, -100); (60, 0, 10); (30, 0, 100) | kind 0xa t4; t6; t8 (ends) | - | C |
| 1033259d | fc5:16 | EFX bone 0 + M0 (0, 120, 100); rot = (pitch, yaw) of bone 0's z axis | action 112 (Impact guard) | L | C |
| 103326e4 | **fc4**:2 | EFX on the ground (0x108cf000) under bone 0 + M0 (0, 0, 100); same rot | action 112 (edx = 0xfc4 at 103326b9) | L | C |
| 1004d9c1 | fc5:15 | TASK bone 14 (0, 0, 40); (0, 0, 100); (0, 0, 170) | action 112 -> MS task kind 6: t0; t6; t12 (ends) | - | C |
| **Guard Counter success (57 / 76 / 77, motion 1034 f32; not in 14)** |
| 103342f2 | fc5:38 | TASK bone 0 (30, 140, 250) | f32, with special #5 / #6 / #7 | - | C |
| 10334325 | fc5:14 | TASK bone 0 (30, 140, 250) | f32 (+ rumble 0xe) | - | C |
| **Charged Strike (35, motion 1082)** |
| 103344a2 | fc5:3 | TASK bone 14 (10, 0, 160) | f4 (armed before f14) (+ rumble) | - | C |
| 1033453d | fc5:3 | TASK bone 0 (120, 160, 30) | f10 | O, M | C |
| 103345b9 | fc5:3 | TASK bone 0 (-10, 230, -30) | f20 | O, M | C |
| 1033461e / 10334683 / 103346e8 | fc5:15 | TASK bone 14 (10, 0, 80) / (10, 0, 160) / (10, 0, 240) | f36 / f44 / f52 | O | C |
| 10334748 | fc5:14 | TASK bone 0 (0, 130, 200) | f60 (+ rumble 0x17) | - | C |
| 103347cb | fc5:3b (M) / fc5:37 | TASK bone 0 (0, 130, 200) | f60 | O | C |
| **Supplex second motion 1062 (26, 30, 31, 37, 43, 144)** |
| 10334906 | fc6:11 | TASK bone 10 (0, 0, 0) | f40 (shared call) | O, M | C |
| 103349a4 | fc5:3 | TASK bone 14 (70, -50, 130) | f68 (+ rumble) | O, M | C |
| 10334a5a | fc5:3 | TASK bone 14 (-30, -40, 130) | f78 | O, M | C |
| 10334af4 | fc5:3a (M) / fc5:30 | TASK bone 0 (0, 100, 300) | f104 (shared call) | O | C |
| **Magnetic Assault (Leap), Cutting motion 1012 (12, 51, 136)** |
| 10334ccc | fc5:39 | EFX HP(-20, 120, 250) | f44 | O, M, L | C |
| 10334d13 | fc5:3e | TASK bone 0 (-20, 120, 50) | f44 | O, not M | C |
| 10334e24 | fc5:22 | EFX HP(0, 0, 250) | f46 | O, not M, L | C |
| 10334e6a | fc5:5e | EFX HP(0, 0, 250) | f46 when not O, or M | L | C |
| 10334f7a | fc5:45 | EFX HP(10, 100, 150) | f48 (+ rumble 0x11) | O, M, L | C |
| **Magnetic Assault (Leap), Impact motion 1013 (38, 53, 138)** |
| 1033503d | fc5:3d | TASK bone 0 (-30, 180, 70) | f44 | O, not M | C |
| 10334e24 / 10334e6a | fc5:22 / fc5:5e | EFX HP(30, 0, 250) | f46, same split as 1012 (jumps into 1012's calls, S) | L | C |
| 1033526a | fc5:45 | EFX HP(20, 100, 200) | f48 (+ rumble 0x11) | O, M, L | C |
| **Magnetic Double Slash motion 1045 (11, 135)** |
| 103353b7 | fc5:4f | EFX HP(0, 110, 50) | f62 | O, M, L | C |
| 10335424 | fc5:40 | EFX HP(0, 140, 70) | f62, when not (O and M) | L | C |
| **Finishing Slash (152 / 155 / 154: lead-ins 1406 / 1418 / 1446, block 0x10335ab5; then 1035)** |
| 10334906 | fc6:11 | TASK bone 10 (0, 0, 0) | first update at frame >= 6 (shared call) | O, M | C |
| 10334e6a | fc5:3 | EFX HP(70, 80, 0) | f20 (shared call, S) | O, M, L | C |
| 10335d32 | fc5:3 | EFX HP(-60, 140, 0) | f30 | O, M, L | C |
| 101eb344 | fc6:22 | CARRIER, bone param 4, offset = special #10's local vector (not read) | special #10 init (0x101eb2b0); #10 = motion 1035 f38 when M (10334b8b) | owner | C / S |
| **Magnetic Pin slam, motion 1421 (94 / 97 second motion)** |
| 103355fd | fc5:28 | CARRIER, world, ground-snapped (0x108cbe30) point near the hunter (offset not read) | f30 when the hunter is < 200 above the ground (P+0x708 >= y - 200); 0x101ea2a0 ends it when the pin task 0x10331ec0(0) is gone | owner | C / S |
| 10335630 | fc5:1a | TASK bone 0 (0, 50, 100) | same moment | - | C |
| 10334af4 | fc5:1c | TASK bone 0 (0, 0, 100) | same moment (shared call) | - | C |
| **Pin Finisher motion 1488 (105, 157)** |
| 10335a98 | fc5:5d | TASK bone 0 (0, 0, 170) | f184 (+ rumble 0x1b; f114 only rumble 0x1a) | - | C |
| **Guard Assault motion 1410 (114, 115)** |
| 10334906 | fc5:3d | TASK bone 0 (-30, 160, 90) | f30 (shared call) | O, M | C |
| 10335f87 + 10335fdf | fc5:5e + fc5:30 | EFX HP(0, 0, 300) + HP(0, 120, 300) | f34 | O, not M, L | C |
| 10336082 | fc5:3a | EFX HP(0, 120, 300) | f34 | O, M, L | C |
| 10336082 | fc5:5e | EFX HP(0, 0, 300) | f34, not O (shared call, S) | L | C |
| **Magnetise on (0x1033c700, from 0x103333a0 / 0x103336f0: state 1 set in the current mode, only if it was not on) -> MS task kind 0xd (Cutting) / 0xe (Impact)** |
| 1004e3ab | fc6:10 | CARRIER, offset (-80, 0, 40) [0xd] / (20, 0, 80) [0xe] from the weapon matrix 0x1032bb60 (S: weapon), re-placed every tick (0x101ea930) | t = 18 [0xd] / 17 [0xe] | O | C |
| 1004e59b | fc5:57 [0xd] / fc5:58 [0xe] | CARRIER, weapon matrix + offset, 5 spots in turn: 0xd (45, 0, 20), (-45, 0, 20), (0, 0, 0), (-90, 0, 30), (90, 0, 30); 0xe (0, 0, 140), (0, 0, 30), (0, 0, 70), (0, 0, -10), (0, 0, 100) | after that, every 10 ticks (O) / 25 ticks (not O) while Magnetise is on, the weapon drawn (P+0x12) and the mode = the task's mode; the task ends when Magnetise ends | L | C |
| 1004e617 / 1004e64b | fc5:55 [0xd] / fc5:56 [0xe] | CARRIER, weapon + (-80, 0, 40) / (20, 0, 80) | every 20 ticks, same conditions | O, L | C |
| **Shot and marker (specials)** |
| 101e9059 | fc5:b | attached to the shot (special #1, init 0x101e8de0) | event 4: f14 of 82, f12 of 84 | owner | C |
| 101eb0a1 | fc5:a | EFX at special #9's point; rot = the shot's direction angles | the shot drops a #9 each time its flight passes 100, 300, 600, 1000, 1500 (0x101e9070); #9 waits its stagger count (+8), posts, ends | L | C |
| 101e938a | fc5:e | attached to the marker (special #2, init 0x101e9320); 0x101e9450 keeps the marker on the hit bone | a monster hit; lives with the marker (prm14) | owner | C |
| 10338670 | (no set) | MS task kind 0 on bone 18: 3 meshes of a model, below | event 17: f6 of 82 / 84, 16 ticks (event param) | L | C |
| **Dead or unused** |
| 103385ec | fc6:11 | EFX at bone 10's position (0x10848420(P, 10)) + MS task kind 4 | event 15 handler 0x10338550: no action uses event 15 | L | C |
| **Pin (0x101bc000..0x101be000, special #3 update 0x101e9b70): found, conditions partly read** |
| 101e9e2a | fc5:2a | EFX0 (point in edx, not read) | special #3: the pin takes hold (owner's P+0x828 == 5) (+ rumble 0x12) | owner | C / S |
| 101e9cd0 | fc6:1e | CARRIER, from the hunter + offset aimed at the pinned monster's pin bone (0x101bbd60), scale (1, 1, distance) | while held, every 12 ticks | owner | C |
| 101e9c98 | fc5:2c | EFX0 | special #3 step +8 == 2 and MS flag 0x10 | owner | C / S |
| 101e9fd1 | fc5:2b | CARRIER, world | MS flag 0x10, count below 0x101bd380() | owner | S |
| 101bd5de | fc5:1d | EFX0 | 98 / 99 (group 1) while MS+0x57 > 6, then MS+0x57 = 0 | L | C / S |
| 101bc127 / 101bd2d5 / 101bd355 | fc5:30 / 2e / 2d | CARRIER, world (0x2d / 0x2e end unless P+0x828 == 5) | pin code, not traced | - | S |
| 101bdad9 / 101bdaf9 | fc5:4a / 49 | CARRIER on a bone from 0x101bbd60 (S: pinned monster's pin bone) | pin code; 0x4a re-spawns itself every 10 ticks while 0x101bc8e0() | O | C / S |
| 1004db04 | fc5:31 / 36 | CARRIER at the hunter bone data +0x58 | MS task kinds 7 / 8 (created by 0x101bcc00, pin code) at t = data +0x5a | L | C / S |
| 1004da39 | fc5:15 | TASK bone 14 (0, 0, 150) | MS task kind 5 (creator not found outside 0x101bcc00), t4, ends | - | C / S |

## Per-motion effect keys (mhfdat, found 2026-11-05; C unless marked)
The effects on the RB moves, the Finishing Slash lead-in 1418 and the ground dust are not code posts: MHF's shared
hunter update keys them per motion.
- **Table:** mhfdat header u32 0x618 -> per weapon type {i32 count, records*} (Magnet Spike = 13: 132 motions);
  record {u16 motion, u16 count, u32 keys*}, sorted by motion and binary-searched (0x1099b180, from 0x109a2ba0).
- **Key** (16 B): u16 frame, u16 kind, u16 a, u16 b, u8 c, u8 d, s16 x, y, z. 0x1099af70 fires a key when the motion
  frame crosses it and calls handler 0x11a42488[kind](P, a, b, c, d, x, y, z); for the Magnet Spike it then calls
  0x103362e0 (the rumble helper, only for fc5 3 / 4 / 0x46 / 0x47).
- **Kinds:** 0 / 1 = sounds (S: 0x11413d70 / 0x114252b0; MS motions use kind 1 446 times: a = id, b = 100);
  2 / 3 / 6 / 7 = an effect (a = set, b = id) on bone c (0-20 the hunter's; 21+ = weapon bone c - 21, 0x10999ce0 ->
  0x1032bb60), 6 / 7 with the offset (x, y, z) in the bone's frame; 2 / 6 copy the bone matrix once (fixed), 3 / 7
  re-read it (follow); d = follow mode (0x1099a720: 3 / 4 position + the hunter's yaw (+ 90 deg), 5 no update);
  4 / 5 (0x1099a970) = at the bone's position snapped to the ground (0x108cbe30), fixed; 8 = the face slots
  (0x1099af40 -> 0x10886860: blinks), not effects.
- **Magnet Spike use:** 208 effect keys on 53 motions (msfxposts.motion_keys): sets 0xfae / 0xfaf (the move flashes,
  swooshes, sparks) and 0xfc3 ids 5-15 (ground dust: kind 5). E.g. 1493 (107 Retreat): f34 fae:23 on bone 10 +
  (0, 10, 0), faf:0 on weapon bone 0 + (10, 50, 40); f64-f76 faf:13 on weapon bone 0 every 6 frames. The Double Slash
  1045, Finishing Slash 1035 and lead-ins 1406 / 1446 have no keys.
- **Port:** msbuild.fx_post_tables (modes 'att' PEL on the joint, 'fix' / 'gnd' placed by ms_act.c fx_fixed at the
  joint's world point; weapon bones: 'att' on the holding hand at the bone's pose (msgrip), 'fix' on the drawn weapon's
  joint). Deviation (S): MHF's follow modes 3 / 4 / 5 are treated as full follow.

## More code posts found (2026-11-05)
| site | set:id | form | when | mark |
|---|---|---|---|---|
| 1033af46 / 1033af82 | fc6:28 / fc6:29 | TASK-like 0x113d6620(set, id, bone 10, 3) | ext+0x684 flag 0x4000 (set by 0x1033adc0 from the hunter status queue 0x1137f350: a queued entry with bit 0x80, the hunter not in i-frames; S: a monster-zone status) starts a timer prm50 x 30 ticks | C |
| 1033b016 | fc6:2a | the same on bone 14 | every 15 ticks (30 when not local) while that timer runs | C |
| 1033dea2 | 0xbcb:1 | 0x113d6250 at an entity's position | 0x109f5c50 (not traced; S: a magnetised monster's spark) | S |
Not ported: they belong to statuses triggered outside the weapon's moves.

## F emitters (the A flag 1 particles; C, 0x113d0b60 / 0x113d2700 / 0x113d2190 / 0x113d11c0)
A physics particle with its own look (mesh +8, D group +0xa, colour group +0x6e, UV mode +0x6c with +0x70 / +0x72,
camera-offset curve +0x74 as E +0x22), not a trail: +0xc life (age units, 2 per tick); velocity +0x14 + U x +0x20
per tick in the effect's yaw frame, multiplied each tick by curve +0xe; gravity +0x5c (vy -= g per tick; negative =
rises: the dust); angular speed +0x2c + U x +0x38 (curve +0x10); scale growth +0x44 + U x +0x50 per tick, clamped at
0 (curve +0x12); ground: restitution +0x60, friction +0x64, child effect +0x78 per bounce (up to +0x7c), +0x7a at the
end, +0x7e a timeline (D-like keys (frame, effect id)) of child effects. The MS sets' F records seen so far use no
children.

## Notes
- **Event 17 "effect 0x312" is not an effect id** (C): 0x1004d700 writes u16 0x312 to task data +0x58, i.e. byte
  +0x58 = 0x12 (bone 18) and byte +0x59 = 3 (part count). 0x1004d410 takes 3 entries of the draw list 0x1ecde5e0
  (0x20 B each, callback 0x1004f7b0). Every tick for 16 ticks (data +0x5a = event param) the task copies bone 18's
  matrix and sets the origin to bone 18 + M18 (-4, -4, 2). Each entry draws one mesh: 0x13, 0x74, 0x97 of the model
  held at global 0x1ed7d6a0 (mesh index via 0x11406cf0, at most 0xd8; which model is open). Each mesh gets 9 constants
  from 0x1004d4b0; the first six are scaled by 0.95. Read as position / scale / rotation (S):
  - part 0: (0, -10, 8.5), (0.9, 0.9, 0.9), (-1.920, 0, 1.571);
  - part 1: (-13, -18, 0), (0.3, 0.8, 0.3), (0.785, 1.571, -0.785);
  - part 2: (-13, 0, -35), (2.5, 2.5, 2.0), (0, 1.571, 0).
  This is the shot's hand piece. Port: tools/msgun.py, one GU effect model of the three meshes (the effect model
  pack's model0.fmod meshes 19 / 116 / 151, parts baked), a one-shot Model entry posted on joint 12 at f6 of 82 / 84
  for 32 frames.
- **The marker's look** = fc5:e attached to special #2 (C). The shot's look = fc5:b; its trail = fc5:a at 100, 300,
  600, 1000 and 1500 cm along the flight.
- **Triple Strike** (corrects the earlier reading): fc6:11 is posted once, at level 1 (20 ticks). fc6:e is posted
  once, at the second threshold (34 ticks), together with the auto-release. Both are on bone 10. The rising fc5:15
  spots on bone 14 come at t4 / 8 / 12 after level 1. The aura is fc6:12 on bone 10 from f50 until level 1. A release
  before level 1 posts fc6:13. GU's current stand-in (msfx PEL 1300 = 0xfc6 0xe) matches the release moment.
- **Gates for the port**: EFX posts carry L and often O; TASK posts have none in the call. With one local hunter,
  O = L = true, and every row applies except the "not O" branches (1004dfcf fc5:14, 10334e6a / 10336082 fc5:5e,
  10335424 fc5:40). In multiplayer those branches pick what the other hunters' clients show (S).
- **Following**: EFX / EFX0 are world points fixed at post time. TASK posts carry their bone (S: they follow it; the
  getters re-read the matrix). Carriers follow their bone, the weapon, or their per-id update, as noted. The Magnetic
  Shock spots are re-evaluated each tick from the hunter, so they move with the hunter (C, matches mechanics.md).
- **Bones**: 0 = root, 10 = S: upper body (Triple Strike charge, Magnetise, Supplex f40), 14 = +x hand / weapon, 18 = -x hand
  (assets.md skeleton notes).
- **Not MS**: 0x101eb9d0 (0x1d via 0x113d6250) and 0x101ebe00 (0x13) sit in other objects' state tables (0x11933fe8,
  0x119340e4). 0x103362e0 is a rumble / flag helper for fc5 3 / 4 / 0x46 / 0x47.

## Open
- The meaning of the zero vector v in EFX, and the set flags word (0 at every MS site).
- Where 0x1032bb60 (the weapon matrix used by the Magnetise carriers) points, and bone 10's place on the body.
- The pin effects (0x101bc000..0x101be000, special #3): triggers and positions only partly read.
- Special #10's carrier offset (0x101eb2b0) and the fc5:28 ground point's horizontal offset.
- Whether TASK posts on non-local hunters show on this client (0x1146aa50 path).
