# Magnet Spike: mechanics (MHF-Z code -> GU module)

C = seen in code / data (address), S = inferred. MHF addresses: mhfo-hd.dll (ZZ 2019-09-02); `P` = MHF player,
`MS` = the per-player MS block (ext + 0x1c0). GU addresses: MHGU 1.4 main; `p` = hunter object. Static analysis only.
The module side is weapons/magnet_spike/module/ms_act.c (Phase 3).

## Time and units
- MHF counters tick at 30 / s (S: executor tick); motion frames are 1/60 s. GU: `dt` = float p+0x1c in 1/60-s frames
  (2.0 at 30-Hz logic, S; logged once per run), timers do `t -= dt` (0x53aa84). Module: MHF ticks = dt / 2.
- Distances: MHF units = GU units (S: both ~cm). Stamina: MHF 75 = a roll, GU 150 = a roll (GU = 6 x displayed,
  S) -> GU = 2 x MHF.

## MS parameters (mhfdat block 0xdc1a20 + 0x14, i16; C)
Full table: 0:0 1:1 2:2 3:2200 4:20 5:5 6:2200 7:20 8:5 9:5 10:10 11:3000 12:10 13:30 14:9000 15:180 16:500 17:10000
18:10000 19:2000 20:200 21:30 22:10 23:100 24:70 25:100 26:55 27:15 28:90 29:280 30:20 31:30 32:1 33:20 34:14 35:0
36:200 37:600 38:100 39:30 40:4 41:70 42:40 43:200 44:60 45:150 46:2 47:13 48:300 49:103 50:30 51:110 52:120
53:120 54:110 55:80 56:1000 57:0 58:80 59:3000 60:2400 61:10 62:240 63:0 64:34 65:240 66:0 67:34 68..79: (240,0,34)
x4 80:30 81:60 82:2.
Lists: +0x24 gauge cost (1 bar at the start): 11 12 38 39 51 53 58 61 62 66 67 68 71 72 94 97 106 107 108 116 117
135 136 138 146 158. +0x28 not turned to the stick: 98 99 106 107 108 116 117 158. +0x30 monster types refusing
the marker: 29 87 88 118 168. +0x34 max turn: 95/96/159-162 60 deg, 110/111/114/115 30 deg.

## Frame events (handler table 0x11926b40; C) -> module
| id | MHF | module |
|---|---|---|
| 1 | `P+0x410 = (p&2)?2:0` (ends on landing), p&1 airborne | `air` (GU move state 2), `end_on_land` |
| 2 | P+0x12 = p (drawn) | the action start's vt+0x46c(p, 1) |
| 3 / 4 | attack (mhfsdt 0x78) / special (0x79) | arm the event's hit-data entry (+ MS_MAG_BASE magnetised) |
| 6 | keep P+0x4f0 >= 4 (meaning unknown) | not run |
| 7 / 8 | i-frames P+0x4ee = max(., p) / + Evasion (+5 skill 0xb1, +10 0xb2) | 0x2a6760(p, 2p, 0); Evasion level 0x2a69dc(p, 0x1f) |
| 9 | i-frames >= 2 every tick until 7 / 8 | 0x2a6760(p, 4, 0) each update |
| 11 / 45 | stamina 75 (evade) / prm80 30 | 0x2a5ebc(p, -150 / -60, 0) |
| 12 | camera shake preset p (local) | 0x2a063c(p, 0xf, 0) (S: GS's landing preset for all) |
| 13 | motion rate p % (P+0xc24) | p+0x50c = p / 100 |
| 17 | task 0x3c (marker effect) | not run (effects) |
| 21 | guard window P+0x418 0x8000: 0 set, 1 clear, 2 / 3 clear unless Guard skills 0x28 / 0x29 | +0x2510 bit 0x10 (0x283238 / 0x28321c); 2 / 3 always clear (S) |
| 24 | MS+0x6a guard level (5) | class 5 guards with GS's rules (build.py patches) |
| 25 | per tick y -= p * 0.1 * t; t++ | `grav`, `grav_t` |
| 26 | MS flag 0x20: charge counting | same |
| 27 / 28 | forward / vertical drive, int8 p per tick | `fwd` along the facing, `vert` (> 0 = airborne) |
| 29 / 30 | drive curve nibble (0x10338c90 jump table: p 0 -> 0, 1 -> 1, 2 -> 2, 3 -> 4; 30 << 4, S: same table). Drive 0x1032f700 (asm): n = ticks since the drive started, this tick's displacement 0 at n = 0, then speed x 0.97^n (bit 1), n x speed (bit 2), else speed; forward = R(yaw) (0, 0, d) | the same (`curve`, `fwd_n` / `vert_n`, 0.97^n kept as a running factor) |
| 31 | MS flag 0x80, gravity p * 0.01 for the attraction fall | `fall_g`, accumulating `vy` |
| 33 | p ticks of zero velocity | zero p+0x1010.. |
| 36 / 37 / 38 | attraction vector reset / forward / vertical drive reset | `att = 0` / `fwd = 0` / `vert = 0` |
| 39 | face the pinned monster | yaw to the pinned monster |
| 40 | MS flag 0x8000 = Impact (the pin's origin) | same |
| 41 | run toggle (authority) | not run |
| 42 / 43 / 44 | special #11 at the owner / #8 on the pinned monster (43 host side, 44 the other side) | arm 42 / 43; 44 skipped (S: MP) |
Unused by the data: 5, 10, 14-16, 18-20, 22, 23, 32, 34, 35.

## Conditions (0x11926c5c) and inputs (0x11926bf8; C)
Conditions: 0 always; 1-5 stamina >= 1 and gauge >= N bars; 6 MS flag 0x8; 7 no active pin; 8 guard-counter hits
>= 1; 9 y >= ground + 200; 10 stamina, 1 bar, marker 1400 < d < 4000; 11 the same, 0 < d < 1400; 12 MS flag
0x20000 (setter not found in the MS code; it gates only 116 / 117 -> 160 / 159 and 158 -> 162, the stronger
Magnetic Shocks = "the evasion went through an attack", behaviour.md; module: set when GU's hit filter asks the
invulnerability slot 44 about an overlapping attack during 116 / 117 / 158, S); 13 this mode's Magnetise ready
(state 0, charge >= 1000).
Inputs: 0 evade + stamina; 1 stick; 2 / 3 / 4 tri / circle / tri+circle pressed; 5 SELECT; 6 stick + circle;
7-11 R1 held + tri / circle / tri+circle / special(A) / SELECT; 13 R2; 14 / 15 circle held / NOT held (levels);
16 R1 pressed; 17 R1 + evade; 19 / 23 / 24 aiming (MS flag 0x1) + circle / special(A) / tri; 20 always; 21 tri NOT
held; 22 stick + tri; 12 / 18 never.
Module (positional, user-confirmed for tri / circle / SELECT / R2): tri X, circle A, special(A) B, R1 = GU's R role
(0x65f93c), R2 ZR, SELECT Minus, L2 aim = 0x400 (L / ZL), R1 + evade = R + Y (S; R + B is R1 + special). GU press
combos +0x1444 (2 X, 4 A, 0x40 X + A). With R held, GU's common evade ids 49 / 50 (+0x1418 bits 17 / 18,
plcmd_com_0x0001_013a / 014a) are cleared (S).

## Gauge and Magnetise (C)
- Gauge MS+0x7a 0..10000 (5 bars of 2000). Regen +200 every 30 ticks (+300 with the MS skill at level 4 and
  MS+0x86 > 0). On hit + (600 * MV / 100) * skill % / 100 (skills 0x12e 120, 0x12f 110, 0x130 80). The costed
  actions pay 1 bar at the start (no abort: the conditions gate the entry).
- Magnetise per mode (MS+0x88 state, MS+0x8a value): charge + MV * 80 / 100 per hit in this mode while state 0, cap
  1000; 163 / 164 (condition 13) -> state 1 for 2400 ticks, then lockout 3000 ticks, then state 0 with no charge.
  While on, attacks and specials spawned in that mode deal MV x 1.1 (prm61). Finishing Slash (152 / 154 / 155, motion
  1035) adds special #10 after f38 when magnetised. Magnetic Shock 5 x 3 (special #12) path: not traced.
- Module: `gauge`, `mag[]`, `mag_v[]`; the hit callback (slot 37, below) adds gauge and charge with the MV of the
  armed entry (`ms_hit_mv`); msbuild writes every hit twice (k and k + MS_MAG_BASE, MV x 1.1).

## Guard (C)
- Guard Counter 14: window f0-f26 (f28 / f30 with the Guard skills). Impact guard 112: f0-f32 (f34 / f36).
- A guarded hit: MS+0x66 += 1 and MS flag 0x8. 14 -> condition 8 in f26-f32 -> shared 207: 1 hit 57, 2 hits 76,
  3+ 77 (motion 1034; special #5 / #6 / #7 = MV 80 / 95 / 120 at f32). 112 -> condition 6 until f106 -> 113 (Just
  Guard reaction, i-frames 7) -> tri 114 / tri + circle 115 (Guard Assault).
- GU: the can-guard check 0x2f2ba0 rejects class 5 before any class slot; build.py adds class 5 to the Great
  Sword's movw masks at 0x2f2bc8 (0xc20b -> 0xc22b), 0x2f2d8c (angle rule, 0xc081 -> 0xc0a1) and 0x2f07c0 (level
  thresholds, 0xc001 -> 0xc021). "Guarding now" = +0x2510 bit 0x10 (per action). The reaction is vtable slot 356
  (+0x590)(p, level, p+0x3214, int *dmg): the module counts the hit, sets flag 0x8, pays GU's guard stamina
  (0x2a609c) and keeps the action (GU's default 0x2f4b20 would start class-motion knock-backs). Blademasters take
  no chip damage.

## Triple Strike charge (C)
34 (motion 1080, 3 loops): event 26 @f50 starts counting P+0xb24. >= T: level 1 (effect 0xfc6/0x11, rumble 7);
>= T again: level 0 and auto-release. Thresholds 0x103332f0(kind) (asm; jump table 0x10333380): kind 0 prm30 20,
2 prm30 + prm31 50, 3 prm33 20, 5 prm33 + prm34 34, others 0; 0x10a6a510 scales them by skills 0x12e / 0x12f /
0x130. Motion 1080's code compares kind level + 3 (level 1 at 20 ticks, effect 0xfc6/0x11) and kind 5 (34 ticks,
effect 0xfc6/0xe, release), one counter. Release = input 15 (circle not held) -> 208: level > 0 -> 35 Charged
Strike, else 36 Triple Strike 3; the hold expiring (step kind 2) -> 36. Module: 20 / 34 ticks (skills not
scaled), GS's charge flash as the cue.

## Marker, attraction, repulsion
- Shot (82 / 84, event 4 special #1 + event 17): MHF aims with the camera and fires a projectile that sticks (4
  global slots, life 9000 ticks, frozen during the attraction). Module (S): the hunter faces the camera at the
  start; the shot marks the nearest large monster within 0.6 rad and 5000 units; marker position = the monster's
  origin + 300 up (GU has no shot point).
- Ranges (3-D distance to the marker): attract 1400 < d < 4000, repel 0 < d < 1400.
- Attraction (58 / 61 / 62 / 68 / 71 / 72): face the marker; phases 1 ease-in along the flight direction,
  v = 90 (0.2t)(2 - 0.2t) per tick while t <= 4 (0x10332dd0 case 1, C), 2 fly 90 / tick toward the marker until
  300 short (re-targeted, S: 90-tick cap), y in
  [target - 550, target + 1000], 3 fall: horizontal 90 * 0.97^t, vertical v0 - g t (g 2.3 or event 31's); the
  action ends on landing. During the flight: tri -> 59 / 73 falling attacks (condition 9), cross -> 63 / 69 approach
  cancel (event drives). GU: move state 2 (vt+0x300), landing 0x2a84d8(p, 0, 0); walls and ground run after the
  action (0x2e7aa0, vt+0x368).
- Repulsion (66 / 67): face the marker; the motion pushes away (no drive events).

## Magnetic Pin
- 94 (Impact) / 97 (Cutting) leap (event 1 airborne, 25 gravity, 28 drives) with the pin attack (MV 1); on a hit
  (module: slot 37 callback, started next update) -> 98 (special #3) -> 99 QTE hold.
- MHF QTE (0x101bd650): tri / circle presses, cooldown 4 ticks, + prm40 (4) to the bar and the hold (cap from the
  monster), hold -1 / tick; success at prm41 70 %; i-frames forced 4 ticks. Over -> 100 (Cutting) / 156 (Impact
  origin, flag 0x8000); success -> Pin Finisher 105 / 157 (event 39 face, 43 / 44 special #8 MV 600 at f184).
- Cap 0x101bc490 (asm): the monster's own pin value (its data + 0x3e) + prm44 60 when the pinner holds weapon
  type 0xe; ratio 0x101bc5a0 = MS+0x50 / (cap x (1 - prm39 30 x 0.01)), success at prm41 70 %. GU monsters have no
  MHF pin value.
- Module (S): hold starts at 60 ticks (cap 90), success at 70 points; the hunter rides the monster (offset in the
  monster's yaw frame) through 98 / 99 / 105 / 157. GU's monster is NOT held yet (MHF's monster side 0x101bc*
  not traced; GU's status pipeline 0x97ddc -> reaction kind rec+0x3ae -> 0x76afc(m, 10, n), kind for trap /
  paralysis unknown: one logged test to settle).

## GU side used by the module (gu_systems research, C unless marked)
| what | where |
|---|---|
| i-frames: timer float +0x2b40 (1/60 s), grant 0x2a6760(p, n, force); hit filter 0x16b15c also skips +0x274a bit 0 | 0x2a680c |
| stamina float +0x13e0 / max +0x13e4; cost 0x2a5ebc(p, -n, flag) (Constitution); test 0x2a5cbc | 0x2a5ebc |
| position +0x40.., yaw u16 +0xfec, target yaw +0x14a0, velocity +0x1010.., move state +0x2505 | 0x2807a0 |
| ground y +0x10f0 (probe in vt+0x368, S) | 0x2e846c |
| our attack hit a monster: owner vt+0x94 (slot 37, `bx lr` in every class)(owner, attack, monster, 1); attack = p + 0x3020 + 0xb8 * slot | 0x16c93c |
| monsters: manager *(MAIN 0x1851fe0), 0x5ceb4(mgr, i) i < 10; rec = *(m + 0x1428): pos +0x40.., yaw u16 +0x54, HP s32 +0x370; small m+0xb5f7; hit-pass filter m+0xb5f9, u8 m+0x7652 == 1, rec+0x1a0, !rec+0x444 | 0x16b15c |
| camera *(*(MAIN 0x2126504) + 0x54): eye +0x40, look-at +0x60 | 0x27f678 |
| effects: vt+0x39c(p, id, p + 0x2550, 1) (id space of class 5 unknown) | 0x282624 |
| HUD per-class gauge switch 0x665ad8 (class 5 word 0x665b34 = GS's case; CB's phial gauge = 0x264, S) | 0x665ad8 |

## Not yet ported (Phase 3 open)
MHF's QTE prompt, effects and sounds (MHF dat/effect.bin unstudied: GU stand-ins), the monster hold during the
pin, the Guard skills' window extension,
Magnetic Shock 5 x 3 (special #12: not spawned by the per-motion extras 0x103339d0 for motions 1031 / 1032 / 1082;
S: a multi-hit property of the attack record), multiplayer (events 43 / 44, authority).
