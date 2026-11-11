# Magnet Spike: mechanics (MHF-Z code -> GU module)

C = seen in code / data (address), S = inferred. MHF addresses: mhfo-hd.dll (ZZ 2019-09-02); `P` = MHF player,
`MS` = the per-player MS block (ext + 0x1c0). GU addresses: MHGU 1.4 main; `p` = hunter object. Static analysis only.
The module side is weapons/magnet_spike/module/ms_act.c (Phase 3).

## Time and units
- MHF counters tick at 30 / s (S: executor tick); motion frames are 1/60 s. GU: `dt` = float p+0x1c in 1/60-s frames
  (C: 0.5 per update at the FPS patch's 120 updates / s, test 13's per-update log; 2.0 at 30-Hz logic), timers do
  `t -= dt` (0x53aa84), the i-frame timer +0x2b40 too. Module: MHF ticks = dt / 2 (tests 1-14 used dt: every MHF
  timer ran twice as fast).
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
| 6 | ext+0x280 = 1: 0x1032f880 keeps P+0x4f0 >= 4 every executor tick (event 5 would clear it; unused). At the start of nearly every action, so P+0x4f0 never reaches 0 while in MS actions: not an i-frame counter (the hit gate 0x108c5910 does not read it; C) | not run |
| 7 / 8 | i-frames P+0x4ee = max(., p) (0x10338240) / max(., 0x10337e30(p)) (0x103382b0): p + prm10 (10) with skill 0xb2 (0x101c06a0(P, 0xb2)) or 0x10a8c3e0(0xfc), else p + prm9 (5) with 0xb1 / 0xfb, else p. Both also clear ext+0x284 (event 9) | 0x2a6760(p, 2p, 0); Evasion level 0x2a69dc(p, 0x1f); `keep_if = 0` |
| 9 | ext+0x284 = 1 (0x10338320): 0x1032f880 keeps P+0x4ee >= 2 every executor tick until a later event 7 / 8 clears it (no other writer in the dll for the MS: C; see "Invincibility") | 0x2a6760(p, 4, 0) each update; the module also clears it at every action start (deviation) |
| 11 / 45 | stamina 75 (evade) / prm80 30 | 0x2a5ebc(p, -150 / -60, 0) |
| 12 | camera shake preset p (local) | 0x2a063c(p, 0xf, 0) (S: GS's landing preset for all) |
| 13 | motion rate p % (P+0xc24) | p+0x50c = p / 100 |
| 17 | task 0x3c (marker effect) | not run (effects) |
| 21 | guard window P+0x418 0x8000: 0 set, 1 clear, 2 / 3 clear unless Guard skills 0x28 / 0x29 | +0x2510 bit 0x10 (0x283238 / 0x28321c); 2 kept with GU's has-skill (0x2864c4) 14 or 15, 3 kept with 15 (S: GU's guard code checks 14 / 15 = Guard +1 / +2) |
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

## Invincibility (all sources; static study 2026-11-11)
- **Hit gate (C):** an attack object reaching an entity goes 0x108b7b60 -> 0x108c5910(attack, ?, target); its first test is
  target+0x4ee == 0, else the whole hit (damage, reaction, the marker store 0x101e84d0) is skipped. The second path
  0x108c69c0 (from 0x108b7c10; player attack kinds 0x77-0x79, S: hunter vs hunter) has the same first test. Further tests there are per attack kind (roar / wind / tremor-like kinds
  against P+0xab3, P+0xcb0 / 0xcb1, the shape mask P+0xb5c) and not touched by the MS code. P+0x4f0 is not read there.
- **Counter (C):** P+0x4ee (u16) -1 per call of 0x10a72ed0 (from the player update 0x10a5d3e0; the same call adds 2 to
  the 60-Hz counters +0x444 / +0x44a, so one call = one 30-Hz tick, S). 0x10a72e70 can raise it from ext+0x52c (not
  written by the MS code).
- **MS writers (C):** events 7 / 8 (above), event 9's keep (above), 0x103339d0 case 99 (pinned QTE): P+0x4ee = 4 each
  tick. No super-armour or "ignore hit" flag in the MS data or code: the guard (event 21, P+0x418 0x8000) blocks, it does
  not make invulnerable. Executor order per tick (0x1032fa80): steps, per-action extras (attraction), frame events,
  0x1032f880 (keeps), cancels; the decrement runs in the player update, so a grant of n covers n hit checks (+-1, S).
- **Capcom's chart "17if" = Evasion +2 (C, arithmetic):** the chart's moves carry event 8 param 7 and the repulsion event
  8 param 14; 7 + prm10 = 17 and 14 + prm10 = 24 = the chart's repulsion "24if". In 60-Hz frames the base values would
  read 14 / 28, so the chart is in 30-Hz ticks with Evasion +2 (the chart's Just Guard "19if" vs 113's 7 + 10 = 17: G).
- **Event 9 persistence: OPEN (S overall; not ported).** What is C: ext+0x284 is set by event 9 (0x10338320) and
  cleared by events 7 / 8 (0x10338240 / 0x103382b0); its only reader is the keeper 0x1032f880, called from the MS
  executor 0x1032fa80 (descriptor slot 9, run only by the group-1 dispatcher 0x109ff060 for actions other than
  0xf0-0xf4), so the keep runs in MS actions (walk 40 / 41 / 44 / 45 included) and not in drawn idle (0x1032d2d0 is
  slot 4, run by the group-0 idle handler 0x109af850) or shared actions. Searched (2026-11-11): every `[reg+0x284]`
  store in the dll (only the weapons' own event-7 / 8 / 9 handlers, each for its weapon type), every memset after
  an ext-index computation (18 sites; none covers ext+0x284: MS 0x1c0 + 0x90, +0x580 + 0xbc, +0x92c + 0x9c), the
  action-change setter 0x10a81af0 (no ext access). Not excludable statically: block writes through passed pointers,
  and hit paths other than 0x108c5910 that skip the +0x4ee gate. If MHF works as the code reads, after 59 / 73 /
  63 / 69 / 94 / 97 the hunter stays invulnerable in every later MS action without event 7 / 8 (the landings
  60 / 64 / 70 / 74, walk 41, attacks 141 / 142, Guard Counter 14) until one with event 7 / 8 (58, 66, 106-108, 135,
  136 from 60) starts; in idle the counter runs out in 2 ticks. Windows (base, no Evasion; 30-Hz ticks):
  attraction alone 0-6 of ~30-42 to the landing; attraction -> Y (59, earliest at 58's f50 = tick 21): 0-6, gap
  7-20 (17-20 with Evasion +2), then 59 + landing 60 covered, idle: 2 more ticks, then none; approach cancel 63: as
  59; pin leap 94 / 97: from its start through 98 / 99 (4 / tick) until 101-104 (20) or 105 / 157 (110) clear
  it. Port: the keep lasts to the end of that action (`keep_if` reset at every action start).

| moves (actions) | MHF (30-Hz ticks from the action start) | port | source |
|---|---|---|---|
| RB moves: Double Slash 11 / 135, Double Swipe 39 / 146, Assault 12 / 51 / 136, 38 / 53 / 138, Retreat Slash 106, 158, Magnetic Evasion 107 / 108 / 116 / 117 | event 8: 7 (0.233 s); 12 / 17 with Evasion +1 / +2 (0.4 / 0.567 s) | same (2n GU frames + GU's Evasion; log "GU timer 14/60 s") | C |
| Just Guard 113, Guard Assault 114 / 115 | event 8: 7 / 12 / 17 | same | C |
| attraction 58 / 61 / 62 / 68 / 71 / 72 | event 8 at the start only: 7 / 12 / 17; nothing until landing (the flight lasts ~20-25 ticks + the fall) | same | C |
| falling attacks 59 / 73, approach cancels 63 / 69 | event 9: >= 2 every tick of the action (C); kept in later MS actions until an event 7 / 8 (open, S) | >= 2 ticks each update of that action only | C / S |
| pin leaps 94 / 97 -> 98 | event 9 as above | as above | C / S |
| pinned QTE 99 | 4 every tick while pinned | 8 GU frames each update, forced | C |
| repulsion 66 / 67 | event 8: 14 / 19 / 24 (0.467-0.8 s) | same | C |
| Guard Counter success 57 / 76 / 77 | event 7: 14 (no Evasion) | same | C |
| QTE 101-104 / Pin Finisher 105 / 157 | event 8: 20; event 7: 110 (3.67 s) | same (where ported) | C |
- GU hit filter (C, 0x16b15c on the hunter loop, 2026-11-11): attack kind +0x3a 0x12 / 0x13 / 0x25-0x2f: hit only if
  vt+0xb0 (= ms_invuln, i-frames) is 0; every other kind (default): only if vt+0x270 and then vt+0xb0 are 0; kinds
  0xc / 0xd / 0x1e: applied WITHOUT the i-frame test, but only while 0x2f63b0 holds (state +0x2506 == 0x80 and action
  +0x250a - 2 in mask 0x36d99), never in our state 0x10; kinds 8 / 9 / 0x34 / 0x45: never applied to a hunter here.
  So every attack object this filter applies honours the grant in MS actions. Not traced: damage outside the attack
  objects (engine reactions such as roars, status / environment), S.
- Port units (C): MS_IFRAMES(p, 2n) sets GU's +0x2b40 in 1/60-s frames, GU takes dt off per update (0.5 at 120
  updates / s), so 2n frames = n MHF ticks. Test 15's hits at motion frames 14 / 18 = ticks 7 / 9: just after MHF's base
  window, so the port matched MHF without Evasion. To check (GU project locked at the time): that GU's hit filter
  0x16b15c asks the i-frame slot (vt+0xb0 = ms_invuln) for every monster attack kind (wind / roar / tremor paths).

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
Module (positional; MHF's MS keyconfig, Rain Client/keyconfig.cfg category 13): tri = top (GU 0x20, Xbox Y), circle =
right (0x100, Xbox B), special(A) = bottom (0x80, Xbox A; also GU's roll), the MS evade (R1 + evade) = left (0x10,
Xbox X; also GU's sheathe), R1 = GU's R role (0x65f93c), R2 / L2 = ZR (aim = ZR without R), SELECT = Minus (C, tests
10 / 13: every press and the GU action it started). GU press combos +0x1444 (2 top, 4 right, 0x40 both). GU's rolls
test common ids 4 / 24 / 38 (1/6) and 49 / 50 (1/13, 1/14); with R held 49 / 50 are cleared, while aiming all five
(test 13: aim + A rolled, as input 23 read the left button).
- Picking (C, 2026-11-11): the cancel engine (0x10a68110) and drawn idle both take ONE input from 0x10337530 ->
  0x10337390: the first, in the priority list 0x11a868d8 (23, 19, 24, 10, 17, 1, 7, 8, 9, 11, 0, 22, 2, 6, 15, 4, 3, 5,
  18, 12, 16, 14, 13, 21, 20), whose check passes and that the current table offers; a passing input the table does not
  offer is skipped. 0x10337330 (all but the aim / stick / level inputs) masks everything while aiming (MS flag 0x1).
  Input 0 (0x10336ad0) = the evade key commands 0x13 / 0x14 + stamina >= 0x10a996a0(P, 0x4b) (0x10336a40), with no R1
  test; input 10 (0x10336ed0) = R1 (key 0xe2) held + key 0xeb (special A) pressed.
- Drawn idle (0x1032d2d0, the descriptor's slot 4, called only from the shared idle handler 0x109af850 <- 0x109b99f0):
  the picked input's entry {group, Cutting, Impact, 0, input}; a costed action (list +0x24) needs stamina P+0x7fc >= 1
  and the gauge (0x1032cff0); if not, the function returns: nothing starts, no roll (C). Input 0 there = shared roll
  28.
- Drawn walk (C, data): the stick starts 40 (Cutting) / 44 (Impact), MS actions whose own tables run while walking
  (window from f40); 41 / 45 the same after attacks. They offer only input 0 (-> shared roll 203), aim + tri / aim +
  special(A), R2, tri, circle, aim + circle, R1 + tri + circle (gauge 1), and Impact R1 + tri -> 146 (gauge 1). No
  R1 + special(A) (106 / 158), R1 + evade (107 / 116), R1 + circle (108 / 117) or Cutting R1 + tri (11). So R1 +
  cross while walking = the roll 203 at any gauge (S: input 0's evade key and special(A) are the same physical button
  in the maintainer's MHF key config: Rain Client/keyconfig.cfg binds command 0x13 (category 0 action 19, crouch /
  evade) and 0xeb (category 14 action 4, special(A)) both to pad bit 0x1, the cross position, and 0xe4 (the MS
  evade, R1 + evade) to bit 0x4; command id = running index over the file's categories, C: 0xdf = category 13
  action 4 "attack R-up / triangle"). R1 alone (input 16) is in neither the walk nor the idle table: holding R1 keeps
  walking (C). 107 / 108 / 116 / 117 / 106 / 158 are in the +0x28 no-turn list and have no turn event: they keep the
  facing, the direction comes from the action (one motion each: 107 1493, 108 1494), not the stick (C). Port: msbuild weapon_commands lists the walk's
  cancels AND all drawn-idle inputs in GU's walk tables 1 / 11 (and the rolls 12 / 13), so RB + A / X / B (and
  Cutting RB + Y) while moving start the RB moves with a bar (test 16): not MHF's; under one bar GU's roll comes out,
  which matches MHF's roll there. Standing under one bar: MHF does nothing (input 10 fails its gauge, C), the port
  lets GU's roll out. Both kept as they are by the maintainer's decision (2026-11-11): deliberate deviations.

## Gauge and Magnetise (C)
- Gauge MS+0x7a 0..10000 (5 bars of 2000). Regen +200 every 30 ticks (+300 with the MS skill at level 4 and
  MS+0x86 > 0). On hit + (600 * MV / 100) * skill % / 100 (skills 0x12e 120, 0x12f 110, 0x130 80). The costed
  actions pay 1 bar at the start (no abort: the conditions gate the entry).
- Magnetise per mode (MS+0x88 state, MS+0x8a value): charge + MV * 80 / 100 per hit in this mode while state 0, cap
  1000; 163 / 164 (condition 13) -> state 1 for 2400 ticks, then lockout 3000 ticks, then state 0 with no charge.
  While on, attacks and specials spawned in that mode deal MV x 1.1 (prm61). Finishing Slash (152 / 154 / 155, motion
  1035) adds special #10 after f38 when magnetised.
- Magnetic Shock 5 x 3 (C): the per-motion extras call 0x1004d3e0(0) at f8 of 1031 / 1032 (159 / 160) and at the
  start of 1082 in 161 / 162; it restarts task kind 0x0f (0x1004d810, one step per tick): special #12 (MV 5, KO 5)
  spawned (0x101e8120(owner, 0, 12, pos, 0)) at ticks 3 / 5 / 7 / 10 on spots (x, z) = (-120, 170), (-90, 250),
  (-30, 400), (40, 550) cm in the hunter's frame (0x1004d650), with MHF effects 0x2d / 0x54 (ticks 0 / 1) and
  0x2e / 0x2f / 0x30. Module: msbuild SHOCK (one hit entry per spot), ms_act.c shock_tick, GS's ground impact (PEL
  105) moved to each spot (S); the hits follow the hunter (S: MHF's stay where spawned).
- Specials' hit shapes (C): mhfsdt kind 0x79 has one shape set per special id (14 sets; the attack-record field
  msbuild read, r[8], is 0 for every special): #5-#7 / #10 / #12 = a 100 cm-radius, 400 cm-tall pillar at the spawn
  point, #8 = 700 cm on weapon bone 7, #11 = 250 cm, #3 = 800 cm, #1 = 30 cm (the projectile). The MV-0 specials (#1,
  #3, #11: detection volumes) are not armed (the module does their jobs in code).
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
- Aim (C, static study 2026-11-04):
  - **Aim flag:** MS flag 0x1 is written only by 0x1033a270, per tick for the local hunter, while drawn:
    - cmd 0xe6 held aims (S: L2);
    - R1 released then held again within about 6 ticks also aims; releasing R1 ends it.
  - **No pose:** there is no aim action, motion, pose or speed change.
  - **Masking:** 0x10337330 masks the other inputs while aiming.
  - **Camera:** the MS camera 0x1033a880 is over the shoulder, pivot = position + a preset offset by yaw.
    - Free look: yaw ±0x240 and pitch ±0x160 per tick, pitch clamped to −0x12e4..+0xd1c.
    - It stays on in idle / walk / runs and in 98 / 99; it is off in the pin actions.
  - **Reticle:** HUD 0x10b87b40 → 0x10339700 draws sprite 0xb6 at the screen centre. Frame 0 = repel possible, 1 = attract possible, 2 = neither. Scale = screen height / 720. No lock-on.
  - **Port (aim view):** GU's gunner aim view for any class (C): the player byte +0x2716 (vt+0x1c8) gates the quest
    camera's aim (0x23ebc) and the scope HUD (0x61e1f4 -> 0x61e834); 0x1baa4(camera manager, 0x2a0520(p)) starts
    the camera's aim. ms_act.c aim_view sets them while the aim flag is on (local hunter, not pinned). Deviations:
    GU's offsets, look speed and crosshair (MHF's reticle frames not drawn).
  - **"Launcher":** not a model. The weapon is one mesh with no part scaling; the shot and effect 0x312 (event 17's task 0x3c, 0x1004d700) both come from bone 18, the −x hand.
- Shot (82 / 84; 0x103333a0, 0x101e8de0 / 0x101e9070 / 0x101eb540, C):
  - **Start:** the hunter takes the camera yaw; the direction = normalize(look-at − eye), pitch included.
  - **Spawn:** bone 18 + R(yaw) (22, 0, 0) + 20 up, at event 4 (f14 in 82, f12 in 84).
  - **Flight:** 500 per tick (prm16), no gravity, sphere r 30, life 150 ticks (mhfsdt kind 0x79 record 1, S).
  - **End:** below the ground or into the map (segment ends raised 50).
  - **Hit:** a monster hit stores the point in the hit volume's bone frame (0x101e84d0). A miss leaves no marker.
  - **Marker:** special #2, 4 global slots, one per hunter, life prm14 = 9000. It follows the bone every tick (0x101e9450) and ends on death, area change or a broken part.
  - **Module:**
    - shot_step every tick: the swept segment against each large monster's hurt volumes, placed by GU's 0x16de70 from bodydata 0x710b0 (push-only records skipped);
    - the surface point toward the shot goes into that joint's frame (joint_mat); marker() rebuilds it from the joint each tick;
    - deviations (S): GU's marker flash every 2 ticks as the shot's look, no wall test (ground − 300 instead);
    - not done: the reticle and the aim camera.
- Ranges (3-D distance to the marker): attract 1400 < d < 4000, repel 0 < d < 1400.
- Attraction (58 / 61 / 62 / 68 / 71 / 72; 0x10331780 start, 0x10332dd0 update, 0x10332ae0 steering, C; MS block =
  ext + 0x1c0):
  - **Marker point (C):** 0x108c5910 stores, for a hit of attack kind 0x79 #1 / #2 (the shot), the contact point
    (from 0x108c4830) via 0x101e84d0: bone = the first field of the monster's hit-shape entry that was hit, offset =
    the point minus the bone position turned into the bone's frame (D3DXVec3TransformNormal; monster type 0xa9 keeps
    the length). The marker special's world point (+0x38) is rebuilt from the bone each tick (0x101e9450): it follows
    the part. No y offset, no ground projection.
  - **Target** T (0x10331540, C from the asm) = M + (0, 100, 0) + RotY(yaw of M - pos) (0, 0, -200), with M = the
    marker special's +0x38 (the y of the rotated vector is zeroed first): 1 m above the marker, 2 m short of it
    horizontally (constants 0x1162b234 = 100, 0x119b623c = -200); no marker: pos + RotY(P+0xe) (0, 0, 700). Nothing
    ties T to the hunter's height. MS+0x24 = T, +0x30 = the marker point. Units MHF = GU (S: assets.md, the skeleton
    offsets match cm for cm).
  - **Direction** D (MS+0xc) toward T at the start, rebuilt from yaw and pitch (0x108e4ad0: pitch = -atan2(y, h))
    with the pitch clamped by 0x103328d0 to 10 deg down (0x71c) / 25 deg up (0xee39) (C, 2026-11-11; the port does
    not clamp: little effect, the steering re-aims from the same tick); then held off the ground: with D x 90,
    D.y >= -(height above the ground) when within 90 of it (0x10331780). Budget B (MS+0x40) = |T - pos| - 300 (3-D;
    700 if not positive). MS+0x3c = the hunter's y, written in the update's first tick (0x10332dd0 case 0).
  - **Steering** (0x10332ae0, called at the end of every update, C): each tick of phases 1-2, when the HORIZONTAL
    |T - pos| > 200 (y zeroed, C; the port tests the 3-D distance) and 0x10331c10 allows it (refuses a listed monster
    species / variant, or a monster in the air / special states unless the marker is above its ground and the hunter's
    ground is within 25 of it): D = normalize(0.2 D + 0.8 toward the new T) (same ground rule, no pitch clamp),
    B = |T new - pos| - |T old - pos| + max(0, B - 252) + 252. So MHF re-targets every tick (C; old notes: "direction
    set at the start").
  - **Phases:** 1 ease-in v = 90 (0.2 n)(2 - 0.2 n) along D, n = 0..4 (252 in all); 2 fly 90 / tick along D for
    max(0, B - 252) / 90 ticks (0x10332930); 3 fall (0x103327a0): x / z / y += D (3-D unit) x 90 x 0.97^N, y += -g n,
    with N = MS+0x45 = ticks since the flight's FIRST tick (cap 255; C from the asm) and n = ticks in phase 3
    (0x103329a0); g 2.3 or event 31's. After ~20 flight ticks the fall starts at 90 x 0.97^20 = 49 / tick, not 90.
    Phase 3 hands over once the y step goes negative (0x10331350); the action ends on landing (event 1 p 2). During 1-2
    the height is kept in [y0 - 550, y0 + 1000] of the START height, B x 0.9 while at the top; the hunter is snapped
    to the ground when within 90 under it. tri -> 59 / 73 falling attacks (condition 9), cross -> 63 / 69 approach
    cancel.
  - Port (test 18): as above, without 0x10331c10's monster-state test (S). Tests 15-17's "too high / off": the port
    had clamped the height around the marker's and re-aimed fully every tick at the marker itself.
  - Fixed 2026-11-11 (ms_act.c att_start / attraction): the fall had restarted at 90 / tick instead of 90 x 0.97^N
    from the flight's first tick (about twice MHF's momentum); the steering gate was 3-D; no start pitch clamp. Offline
    replay (scratch, flat ground, 20 m): marker at hunter height: MHF peak 89 cm / lands +27 cm past the marker, old
    port 92 / +427, new 87 / -12; marker 3 m up: MHF 376 / +356, old 424 / +1166, new 375 / +342. Left: MHF's phase 1
    takes one tick more (N 0-5, 342 cm; the port 252), the marker point is MHF's rule on GU's hurt volumes (S).
    Log per attraction: `msport: attraction end (landed | action change, action A): marker y, target y, start y,
    peak y, end y, horizontal cm to the target, ticks, phase`.
  - GU: move state 2 (vt+0x300), landing 0x2a84d8(p, 0, 0); walls and ground run after the action (0x2e7aa0,
    vt+0x368).
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
MHF's QTE prompt, effects and sounds (MHF dat/effect.bin unstudied: GU stand-ins, phase3.md), the monster hold
during the pin, multiplayer (events 43 / 44, authority).
