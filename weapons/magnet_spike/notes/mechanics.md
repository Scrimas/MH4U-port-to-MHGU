# Magnet Spike: mechanics (MHF-Z code -> GU module)

C = seen in code / data (address), S = inferred. MHF addresses: mhfo-hd.dll (ZZ 2019-09-02); `P` = MHF player,
`MS` = the per-player MS block (ext + 0x1c0). GU addresses: MHGU 1.4 main; `p` = hunter object. Static analysis only.
The module side is weapons/magnet_spike/module/ms_act.c (Phase 3).

## Time and units
- MHF counters tick at 30 / s (S: executor tick); motion frames are 1/60 s. GU: `dt` = float p+0x1c in 1/60-s frames
  (C: 0.5 per update at the FPS patch's 120 updates / s, test 13's per-update log; 2.0 at 30-Hz logic), timers do
  `t -= dt` (0x53aa84), the i-frame timer +0x2b40 too. Module: MHF ticks = dt / 2 (ms_act.c tick_len; tests 1-14 used
  dt: every MHF timer ran twice as fast).
- Which number is which (C on the code, 2026-11-11): MHF motion frames = GU motion frames (both 1/60 s), so motion,
  step, event and cancel-window frames carry over 1:1 (msmot.py, msbuild.py, phase2.md "Frames"); counts in MHF's
  30-Hz ticks become 2 frames a tick where they turn into frame data (an attack's live time: HDP [3] = 2 x mhfsdt
  raw[1], msbuild; task ticks t after a motion frame f0: frame f0 + 2 t, msfxposts; effect ages and timelines, which
  MHF counts 2 a tick, carry over 1:1, mhffx2gu), and stay ticks in the module's timers (tick_len). assets.md's old
  "divide by 2" (Phase 1, for 30-fps lists) does not apply: GU's motion lists run at 60 frames / s.
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
| 6 | ext+0x280 = 1: 0x1032f880 keeps P+0x4f0 >= 4 every executor tick (event 5 would clear it; unused). At the start of nearly every action, so P+0x4f0 never reaches 0 while in MS actions: not an i-frame counter (the hit gate 0x108c5910 does not read it; C). Every action change clears ext+0x280 (0x10a80050, see "Invincibility"; C) | not run |
| 7 / 8 | i-frames P+0x4ee = max(., p) (0x10338240) / max(., 0x10337e30(p)) (0x103382b0): p + prm10 (10) with skill 0xb2 (0x101c06a0(P, 0xb2)) or 0x10a8c3e0(0xfc), else p + prm9 (5) with 0xb1 / 0xfb, else p. Both also clear ext+0x284 (event 9) | 0x2a6760(p, 2p, 0); Evasion level 0x2a69dc(p, 0x1f); `keep_if = 0` |
| 9 | ext+0x284 = 1 (0x10338320): 0x1032f880 keeps P+0x4ee >= 2 every executor tick of that action; events 7 / 8 and every action change (0x10a80050) clear it, so it never outlives the action (C, 2026-11-11; see "Invincibility") | 0x2a6760(p, 4, 0) each update of that action; `keep_if` cleared by 7 / 8, at every action start and when GU takes over (same as MHF); log lines `event-9 i-frame keep on / off` |
| 11 / 45 | stamina 75 (evade) / prm80 30 | 0x2a5ebc(p, -150 / -60, 0) |
| 12 | camera shake preset p (local) | 0x2a063c(p, 0xf, 0) (S: GS's landing preset for all) |
| 13 | motion rate p % (P+0xc24) | p+0x50c = p / 100 |
| 17 | task 0x3c: the shot's hand piece on bone 18 ("0x312" = bone 18, 3 parts: not an effect id; effect-posts.md "Notes") | msgun.py's model posted as a motion key on joint 12 at f6 of 82 / 84 (msbuild) |
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
- **Event 9 does not carry over (C, 2026-11-11, step H).** ext+0x284 is set by event 9 (0x10338320), cleared by
  events 7 / 8 (0x10338240 / 0x103382b0) AND by 0x10a80050, which every action change runs: it writes ext+0x280,
  +0x284 and +0x288 = 0 unconditionally (after resetting the weapon-type part of the ext block), for any hunter with
  P+0x10 == 0 (the same test event 9's handler makes). Its callers (571) include the general action setter 0x10a80a00
  (straight-line after its early returns, which return without changing the action) and the neutral setter
  0x10a81af0 (when P+0x411 == 0). MS action changes: the cancel engine 0x10a68110 and the step runner 0x10a67790 both
  change the action through the executor's callback 0x10337c50 -> 0x10337c00 -> 0x10a80a00; the landing handler
  0x10331350 through 0x1032fc10 (-> 0x10a80050, 0x10a81af0); the extras 0x103339d0 call 0x10a80a00 directly; the
  end of the action / neutral through 0x10a81af0. The executor 0x1032fa80 also skips the keeper on a tick whose steps
  or extras changed the action. So the keep lasts from event 9 (start of 59 / 73 / 63 / 69 / 94 / 97) to the end of
  that action; at the change +0x4ee holds >= 2, which runs out in 2 ticks (0x10a72ed0). The earlier "no other
  writer" missed 0x10a80050 because its ext pointer comes from the player, not from an `add reg, 0x1e2a32f0` site
  followed by a store, and 0x10a81af0 reaches it through a call.
  - (a) ext block (C): a static array of 8 x 0x9d0 bytes at 0x1e2a32f0 (index P+0xc < 8; uninitialised section,
    zero at load); getter 0x10a7e850 (346 callers). Writers covering +0x284: the three MS handlers, 0x10a80050, and
    other weapon types' own event handlers (10275960 ... 11327750, via 0x10a7e850, run only for their weapon type).
    Scanned: every ext-base computation (962) followed through register copies, lea, pushes and the callees taking
    the pointer; every memset / rep movs / rep stos those reach (none covers +0x284: MS +0x1c0 / 0x90, +0x6c / 0xa0,
    +0x11c / 0xa0, +0x580 / 0xbc, +0x92c / 0x9c); no whole-entry (0x9d0 / 0x274 dwords) or whole-array copy of the ext
    array. Not followed: ext pointers saved in stack locals and reloaded (about 80 sites); 0x10a80050 already settles
    the question.
  - (b) hits (C for the attack objects, S beyond): 0x108c5910 and 0x108c69c0 test +0x4ee first (above). Damage that
    is not an attack object (status ticks, environment) not traced. The answer to "carried over" does not depend on
    (b): the flag is gone at the next action change.
  - (c) what ends it: any action change (the landings 60 / 64 / 70 / 74 included, whatever events they carry), events
    7 / 8, sheathing, items, rolls, being hit (all action changes). Drawn idle never sees it set.
  - (d) invulnerable ticks (30 Hz, base, no Evasion; +5 / +10 on event 8 with Evasion +1 / +2):
    - attraction 58, no follow-up: 0-6 (event 8: 7), then none through the flight, the fall and the landing.
    - 58 -> Y 59 (from 58's f50, tick 21) -> landing 60 -> stand 3 s -> walk 3 s -> Y: 0-6, none 7-20, all of 59 to the
      landing, 2 ticks into 60, then none (60, idle, walk and the plain Y carry no event 7 / 8 / 9).
    - approach cancel 63 / 69: all of 63 from its start, 2 ticks into the next action.
    - pin leap 94 / 97: all of the leap, 2 ticks into 98, none in the rest of 98, 4 every tick of 99 (pinned QTE,
      0x103339d0), then 4 ticks into 100 / 156, or event 8 20 in 101-104, event 7 110 in 105 / 157.
  - The maintainer's memory ("RT + Y is invincible from input to the moment the player reaches the ground") does not
    match MHF's code for the attraction alone: 58 grants 7 ticks (0.23 s; 17 = 0.57 s with Evasion +2) and nothing
    during the flight. It matches RT + Y followed by Y (59): from 59's start to the ground, plus 58's first 7 ticks;
    the gap between them is 14 ticks (0.47 s) at the earliest Y. Not settled by statics: per-kind hit tests after the
    +0x4ee gate for an airborne hunter (S).
  - Port (C, same as MHF): `keep_if` from event 9 to the action's end (action_start, events 7 / 8, GU's own action),
    4 GU frames (2 ticks) each update while set, so 2 ticks remain after the change. Log: `msport: event-9 i-frame
    keep on in action A (frame F)` / `msport: event-9 i-frame keep off (action change | event 7 / 8 | GU action, next
    N) after T ticks of action A, GU timer G/60 s`.

| moves (actions) | MHF (30-Hz ticks from the action start) | port | source |
|---|---|---|---|
| RB moves: Double Slash 11 / 135, Double Swipe 39 / 146, Assault 12 / 51 / 136, 38 / 53 / 138, Retreat Slash 106, 158, Magnetic Evasion 107 / 108 / 116 / 117 | event 8: 7 (0.233 s); 12 / 17 with Evasion +1 / +2 (0.4 / 0.567 s) | same (2n GU frames + GU's Evasion; log "GU timer 14/60 s") | C |
| Just Guard 113, Guard Assault 114 / 115 | event 8: 7 / 12 / 17 | same | C |
| attraction 58 / 61 / 62 / 68 / 71 / 72 | event 8 at the start only: 7 / 12 / 17; nothing until landing (the flight lasts ~20-25 ticks + the fall) | same | C |
| falling attacks 59 / 73, approach cancels 63 / 69 | event 9: >= 2 every tick of the action, cleared at the next action change (0x10a80050): 2 ticks remain | same | C |
| pin leaps 94 / 97 -> 98 | event 9 as above | as above | C |
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
  0x2e / 0x2f / 0x30. Module: msbuild SHOCK (one hit entry per spot), ms_act.c shock_tick, MHF's spot effects as motion rows
  (msfxposts SHOCK_HIT / SHOCK_WHIFF; GS's ground impact PEL 105 only with the MHF effects off); the hits follow the hunter (S: MHF's stay where spawned).
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
scaled), MHF's fc6:11 + fc5:15 x 3 as the cue (msfxposts CHARGED; GS's charge flash only with the MHF effects off).

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
  - **Look (C, 0x1033a880 re-traced 2026-11-11):** each tick the camera controls (commands 0x20 / 0x21 / 0x22 /
    0x23 held: digital, no tilt scaling; MHF's invert options 0x1082f610 / 0x1082f660) step the camera's own yaw by
    0x240 and its pitch by 0x160. The pitch starts from the camera's (0x1033a750) and is clamped −0x12e4..+0xd1c
    (camera setting 0; other settings / distances move the bounds). The hunter's body does not turn; the shot's
    start (82 / 84) turns him to the camera's yaw.
  - **Port (aim view):** GU's gunner aim view, any class (C):
    - The player byte +0x2716 (vt+0x1c8) gates the quest camera's aim (0x23ebc) and the scope HUD. 0x1baa4(camera
      manager, 0x2a0520(p)) starts the camera's aim (+0xacc on, mode +0xac8, settled +0xa60).
    - **Same-update clear (tests 18-21: no crosshair, no aim camera):** 0x29fb8c, at the end of the player update
      0x29b8e8 (slot 139 runs earlier, inside 0x27c97c), clears the byte and +0x2714 every update for a drawn hunter
      that is no bowgun (0x27c7ec kind 0) outside common actions 1/97-98 (0x29fe90). The camera saw 0 and ended its
      aim in the first frame. Fix: slot 45 (+0xb4, called right after 0x29fb8c) sets the byte and the pitch again and
      calls 0x1baa4 (a no-op while +0xacc is on; it restarts the aim after GU's 0x2a0624 ends it on an action change).
    - **Scope widget:** cUIOQuestScope (layer 7) is made for every class by 0x6658ec; the Charge Blade redirect
      (0x665ad8, layers 5 / 6 / 0x10) does not touch it. Update 0x61e1f4: 0x61e438 gives state 8 for class 5 (vt+0x1c4
      / 0x6e0 / 0x6e4 / 0x558 all 0), then byte 1 -> +0x4c 1 -> 0x61e834 with +0x58 0 = element 0 (the crosshair)
      shown, element 1 (gauge) off.
    - **Camera mode 0** (0x23f24, every frame): yaw +0x9dc = hunter +0x14a0 + 0x8000, pitch +0x9d8 = (s16) +0x2714,
      then vt+0x410(p, out, 0). +0x14a0 is the turn target (GU writes it with +0xfec; GU's gunner look 0x2a07a8 ->
      0x2a1738 puts body yaw + look there, so bowgunners turn). Ours (slot 260) writes the look into +0x9dc / +0x9d8
      instead: the hunter does not turn (MHF). Releasing the aim: 0x23ebc copies +0x9d8 / +0x9dc into the normal
      camera's +0x9e0 / +0x9e4 / +0x9e8 / +0x9ec, so it keeps the aimed view.
    - **Look input:** GU's aim reader 0x27d5c4(p, source 1) = the stick at +0x140c angle / +0x1410 magnitude (pad
      +0x6bac / +0x6bb0, 0x2a7b14), the one 0x2a07a8 reads alone while the hunter can walk aimed (the move stick
      +0x140e / +0x1412 is source 2): the right stick. dirs 4 / 8 = yaw + / −, 1 / 2 = pitch + / − (0x2a07a8, VSELEQ
      at 0x2a154c), after GU's invert options (vt+0x1b0 0x400000 inside, global *0x188ca48 +0x66 in 0x2a07a8, both
      applied). Steps per MHF tick (tick_len): 0x240 yaw, 0x160 pitch.
    - Deviations: GU's over-the-shoulder offsets (camera preset 6); the pitch starts level, not from the camera's (GU's pitch sense against the view not traced); the
      pitch is clamped ±0xd1c, since which of MHF's bounds (−0x12e4 / +0xd1c) is up in GU's sense is not traced (G).
    - **MHF's reticle (2026-11-11, ported on GU's scope HUD; test 22):**
      - MHF, C: 0x10b87b40 draws it for weapon class 13 when 0x10b86b20 says so: the local hunter's MS flag bit 0
        (aim, 0x1033a160) on and its action not in the table at 0x11994f30 (0x1033a130). 0x10339700:
        0x1096bca0(sprite 0xb6, frame, screen centre, scale = min(screen height x 0.0013885 (1/720), 1); width
        0x1ebee5a0, height 0x1ebee59c); with the camera mode byte 0x11c4a409 = 2 it is drawn at a projected point
        instead, and skipped off screen.
      - Frame (C): 0 if 0x10331e20 (repel possible), else 1 if 0x10331d80 (attract possible), else 2. Both need the
        marker (0x1033b470, state +6 = 2) and 3-D d = |marker point (+0x38) - hunter position (+0xac)|: repel
        0 < d < 1400, attract 1400 < d < 4000 (strict); then 0x10331c10 ("MHF's target test" below; refused = the
        next frame down, so white in either range). Gauge and stamina are not asked. The port computes it each aim
        tick (ms_act.c aim_view, without 0x10331c10: deviation) and logs it (`msport: aim reticle frame`).
      - MHF's art, C: 0x10339700 calls 0x1096bca0 with HUD context EAX = 4. Context i = 12-byte record at
        0x11882178 + 12 i (file `dat\mhf_90c.bin`, bank entry id, texture-ID list); 0x1096bba0 loads each bank
        (0x113ecae0: the entry copied, 0x113f12f0 relocates its chunk tree) into 0x1e7fe468[i]. Context 4 = entry 20,
        textures (0x0b14, 0x0b47, 0x0b09, 6). The lookup (0x113ed9c0 asm): table T = bank +0x10 (entry 20 +0x1c: count
        0xb9 at +0xc, u16 offsets at T + [T+8]); sprite S = T + offset[id]; u16 frame count, then 28-byte cells from
        +4. Sprite 0xb6: 3 frames, one cell (+2 texture index 0, +4 ARGB, +8 u 1, v 323, +0xc 46 x 46, +0x10 origin
        −23 −23, +0x14 drawn 46 x 46); the three differ only by colour: 0xff0b99ff blue, 0xffc62900 red, 0xffffffff
        white (0x113ecc60 multiplies the cell colour into the vertex colour; it binds texture ID list[index] through
        0x1ecda320). Texture ID 0x0b14 = mhf_90c entry 4 (the loader at 0x1096ce81 walks 23 (entry, ID) pairs at
        0x11881658; entry 4 -> 0x0b14), the PNG kept as dump/mhf/ui/mhf_90c_04.png (pixel-identical in the .bin and
        .xbox banks): a white reticle, four corner brackets around a small diamond, mirror-symmetric about its column
        22 and between rows 22 / 23 (3 pixels differ by <= 21 / 255). On screen: 46 x 46 px at heights >= 720.
      - GU, C: the scope .gui is chosen by 0x61e13c from the text language (options object *0x188ca48 +0xa5: 1 eng,
        2 fre, 3 spa, 4 ger, 5 ita, 6 file 0xd81d; > 6 = 1): file IDs 0xe246 / 0xe266 / 0xe286 / 0xe2a6 / 0xe2c6 =
        <lang>\GUI\01_quest\hud\hud6_scope (quest_<lang>.arc; the HD UI v4 mod ships the same eng file byte for byte,
        only its textures differ: HD_hud01 512 x 1024 = 2x). File (GUI v0x22715, 1280 x 720, header 72 x u32 H):
        7 texture entries of 64 B at H[58] (+0xe8; count H[28]; +0 id, +0xc size u16 pair, +0x20 1 / size, +0x2c path;
        ids 3 hud01, 6 hud00, 7 / 9 cmn_icon, 8 / 10 hud_icon, 11 custom_pnl2; the loader fills +0x28 = rTexture);
        26 instances of 36 B at H[43] (+8 next, +0xc child, +0x10 name, +0x14 DTI hash, +0x18 first param, +0x20
        TextureSet block), 8 objects of 36 B at H[47] (same links, +0x18 hash, +0x1c first param), 5 animations of
        24 B at H[41] (id, instance count, first instance...), 563 params of 20 B at H[45] (+4 type, +0xc name, +0x10
        value: type 2 f32 / 7 Texture / 0xb AnimationId / 0x10 SequenceId = 4 bytes at H[68] + value, type 4 = 4 floats
        at H[69] + value, type 3 = a byte at H[67] + value; type | 0x100 = animated), strings H[65]. The vertex buffer:
        file +0x120 (0x4950), H[36] = 0x930 bytes of 24-byte vertices (x y z colour u v, u v in the .gui's texel
        units); 0xb7f988 copies it into a GPU buffer at rGUI +0x80.
      - GU's elements, C: the cGUI's object array +0xf8 is built by 0x91a7d0 from the file's objects in file order
        (count file +0x44 -> +0x298, 0x5448a8), so element k = object k: 0 Anm_scope, 1 Anm_zoom, 2 Anm_simple_scope,
        3 Nul_scope (their root), 4 Anm_target_scope, 5 Nul_i_club2, 6 Anm_align, 7 Null_target. An Anm object plays
        animation AnimationId at its PosX / PosY: Anm_scope = animation 12 = instances 0-9 (tree "scope") at
        (640, 360). For our class 5 the widget runs state 1 mode 0 (0x61e1f4 / 0x61e438 / 0x61e834): elements 0 and 3
        on, 1 (zoom gauge) only with the weapon's bit 8; 2 / 6 (projected crosshairs, 0x61e5d4) run in states 0 / 2
        only, 4 / 7 (target scope) by 0x61e95c. Tree "scope": TexS_scope (cGUIObjTextureSet, hud01, white, no
        animated params) = 4 quads (−240..0 x −240..0 and its mirrors, all UV (0, 32)-(240, 272): the faint 480-unit
        ring; texel (240, 272) at the screen centre) + 4 side bars UV (0, 272)-(160, 312) / (46, 272)-(130, 312); its
        children TextureSet / TextureSet0 (bars, UV (0.5, 272.5)-(119.5, 311.5), rotated 90); Nul_target (animated
        scale / rotation) -> ColAj_target -> Txt_target1-4: 16 x 16 red arrows at ±66, mTextureRect (168, 16)-(184,
        32). A TextureSet block (H[70] + instance +0x20) = (count, first vertex, count rects); 0xa52024 keeps them at
        +0x12c / +0x134 / +0x130, the draw 0xa515f8 strips count x 6 − 2 vertices of rGUI +0x80 from the first; the
        draw binds the 64-byte entry (+0x104) through 0x542aa0, which reads entry +0x28 each time.
      - Every hud01 user in hud6_scope (tools/mshud.py scope_users): TexS_scope, TextureSet, TextureSet0,
        Txt_target1-4 (tree scope), Txt_zoom (0, 0)-(168, 32) and TexS_pointer (168, 0)-(184, 16) (zoom),
        Txt_s_scope (0, 312)-(96, 408) (simple_scope; red vertex colour), Txt_s_scope and Txt_target1-4 (target_scope).
        TexS_align samples hud00, Txt_No custom_pnl2.
      - Port: mshud.py build_reticle writes mh4uport\ms_reticle0 / 1 / 2 (the live HD_hud01's size, 512 x 1024 BC3
        with the HD UI mod, 512 KB each; GU's 256 x 512 otherwise), empty but for MHF's reticle quarter in frame N's
        colour at TexS_scope's quadrant centre corner (every other user blanked: they are bound only while the local
        class-5 hunter aims, so GU's ring, arrows, bars, zoom gauge and crosshairs vanish then, as MHF), 2 texels per HUD unit (+1 texel of
        edge padding); the four mirrored quads rebuild the 46 x 46 reticle = 46 HUD units, MHF's size at 720 lines
        (at 1080 lines MHF's is 46 of 1080 = 31 units: the port takes MHF's 720 reference). Checks (the build stops on
        a failure): the hud01 users are exactly the decoded ones, the painted texels lie inside the atlas and the
        quadrant (+ padding) and 1 texel away from every other user's rect, nothing else is non-empty, and the four
        quads rendered from the copy match MHF's reticle. ms_class.c scope_look (hook 0x61e1f4, the widget's update entry): while
        the local class-5 hunter aims (ms_reticle from aim_view, refreshed every aim tick, 8 widget updates of grace),
        the scope .gui's HD_hud01 entry +0x28 points at the frame's copy (same size required, one reference added per
        swap, as hud_look: each colour change leaves one count on the copy it replaces, never released, harmless as the
        copies stay resident; GU's release call not traced); otherwise, and for every other class, back to HD_hud01.
        Kept GU: Txt_No (custom_pnl2, target scope only) and TexS_align (hud00, states 0 / 2), other entries.
        Deviations: the reticle sits half a unit
        right of MHF's (its centre column on the centre); MHF's 0x10331c10 target test is not asked (below).
  - **"Launcher":** not a model. The weapon is one mesh with no part scaling; the shot and event 17's hand piece (task 0x3c, 0x1004d700: three meshes, "0x312" is bone 18 + 3 parts, not an effect id) both come from bone 18, the −x hand.
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
    - deviation (S): no wall test (ground − 300 instead); the looks: MHF's fc5:b / fc5:a / fc5:e (below; GU's marker flash
      only with the MHF effects off, test 21 row 12);
    - the aim camera and MHF's reticle on GU's scope HUD: "Port (aim view)" above (test 22).
    - test 21 (C by elimination, ms_act.c): a marker placed by a hit ended on the same tick ("alive 0"): the shot's
      em_ok had just passed (in the manager, not small, HP > 0), so the area test (monster +0x1054 != the hunter's;
      +0x1054 is the unit's area, as 0x53b500 / 0x42eac read it) ended it: the monster was in another area than the
      hunter. The Instant Kill cheat cannot cause it (the shot deals no damage). The log line now names the failing part.
    - looks (fc5:e on the marker, fc5:b on the shot): posted once and moved every update (0x32a45c), re-posted only
      when the effect ended or the marker moved over 150 cm; tests 17-21 killed and re-posted them every tick and they
      never showed (S, effect-posts.md "GU's post handle").
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
    with the pitch clamped by 0x103328d0 to 10 deg down (0x71c) / 25 deg up (0xee39) (C, 2026-11-11; the port clamps the
    same since 2026-11-11, ms_act.c att_start); then held off the ground: with D x 90,
    D.y >= -(height above the ground) when within 90 of it (0x10331780). Budget B (MS+0x40) = |T - pos| - 300 (3-D;
    700 if not positive). MS+0x3c = the hunter's y, written in the update's first tick (0x10332dd0 case 0).
  - **Steering** (0x10332ae0, called at the end of every update, C): each tick of phases 1-2, when the HORIZONTAL
    |T - pos| > 200 (y zeroed, C) and 0x10331c10 allows it ("MHF's target test" below; refused = no re-aim that
    tick, the flight keeps D and B): D = normalize(0.2 D + 0.8 toward the new T) (same ground rule, no pitch clamp),
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
  - Port (test 18): as above, without 0x10331c10 (deviation, "MHF's target test"). Tests 15-17's "too high / off": the port
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
- **MHF's target test 0x10331c10 (C, asm, 2026-11-11 step H)**, P = the asking hunter, M = the marker special
  (0x1033b470, its point +0x38 only while state +6 == 2), E = the marked monster (marker +0xac):
  1. no marker or no E: allow.
  2. E's (+0x15, +0x14) (S: action group / action, the hunter's own layout) in the list of the mhfemd.bin block at
     header +0x4c (u16 count +0x1a, 4-byte entries at +0x1c, bytes 1 / 2 compared): refuse. The ZZ data
     (dat/mhfemd.bin, decoded: ECD CRC ok, JPK size ok) has count 0: never refuses.
  3. E type +3 = 0x3b (59, Chameleos, G: community id list) in group 3 action 0x1d: refuse.
  4. "special" = E+0x410 == 4, or E+0xca6 != 0, or type 0x30 (48, Daimyo Hermitaur, G) in motion +0x32c 0x40a /
     0x40b / 0x40c / 0x418 / 0x421 / 0x443 (0x436 / 0x442 / 0x444 by a frame test 0x108ff810), or type 0x43 (67,
     Shogun Ceanataur, G) in 0x40a / 0x40b / 0x418 / 0x41a / 0x421 (0x436 by frame), or E+0x410 == 1 with type 0x4d
     (77, Akantor, G) (0x10f972c0 / 0x10f97370). What E+0x410 / +0xca6 mean is not traced (G: airborne / dug in).
  5. ground rule: g = the ground probe 0x108cbe30 from M + (0, 500, 0); M.y >= g and P+0x708 (S: the hunter's
     ground y, 0x10a80a00 compares it with P+0xb0) <= g + 25: allow.
  6. otherwise allow unless "special".
  The ids match the marker-refusal list's 29 / 87 / 88 / 118 (rocks, gorge objects, dummy) in the same community
  list, hence G for the names. Callers: cond 10 / 11 (0x10336710 / 0x10336760: stamina P+0x7fc > 0, the gauge >= prm19
  (0x1033be30), then 0x10331d80 / 0x10331e20 = range + this test): refused = the cancel entry does not qualify, the
  attraction / repulsion does not start, and while aiming the other inputs are masked (0x10337330), so nothing starts
  (S for "nothing"); drawn idle 0x1032d2d0 skips the entries for 58 / 68 (attract) and 66 / 67 (repel) the same way;
  the reticle 0x10339700 drops to the next frame (white); the steering 0x10332ae0 skips the re-aim; also asked by
  0x103399c0 (HUD) and 0x1003cb90 / 0x1003cfc0 / 0x1003d3d0 (marker look, not ported).
  Port: none of steps 2-5 maps onto a traced GU field: GU has the four species, but MHF's actions / motions and
  E+0x410 / +0xca6 have no traced GU counterpart (the module reads only em_ok's spawned / active / small / hurt / HP
  fields), and the ground rule only matters for a "special" monster. So the attraction start, the repulsion start, the
  steering and the reticle all skip it, and agree (deviation: MHF refuses Chameleos in 3/0x1d always, and the four
  "special" cases when the marker is below the monster's ground or the hunter stands more than 25 above that ground).
  To port: GU fields for a flying / burrowed / submerged monster (one logged test), then E+0x410 / +0xca6 in MHF.

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
| effects: the class PEL (+0x3304, effect\pel\pl\w05_000) list 1 through 0x282548 (ms.h ms_post, phase3.md test 5 row 2; vt+0x39c returned 0 for class 5) | 0x282548 |
| HUD per-class gauge switch 0x665ad8 (class 5 word 0x665b34 = GS's case; CB's phial gauge = 0x264, S); the port sends class 5 to CB's case (hook 0x646560, phase3.md "Status" HUD) | 0x665ad8 |

## Not yet ported (2026-11-11)
Ported (phase3.md "Status"): the moveset, inputs, hits, gauge and Magnetise, guard, Triple Strike, i-frames, the pin
(hunter side), the shot and marker, attraction and repulsion, the aim view and MHF's reticle; MHF's effects are
converted and posted (effect-posts.md, assets.md "Conversion"; their look is still being tested). Open:
- MHF's weapon sounds (Great Sword stand-ins; MHF plays them from code and from per-motion keys of kind 0 / 1).
- The pin: MHF's QTE prompt, the monster hold (GU's status pipeline above: one logged test), MHF's hold / cap values.
- MHF's target test 0x10331c10 and the marker's part-break end (above).
- Triple Strike's skill scaling (0x10a6a510).
- Multiplayer: event 44 (the other side's pin finisher), the run toggle / authority (event 41), the "not O" effect
  branches (effect-posts.md "Gates for the port").
