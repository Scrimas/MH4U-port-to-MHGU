# uEm089 behaviour port (module/em089_act.c), 2026-10-17

Static RE only. GU = MHGU 1.4 main offsets, 4U = MH4U v1.1. C = confirmed in code, S = strong, W = guess.

## How GU runs a monster's actions (C)
Per frame the enemy update **0xa59fc** does, in order:
1. think check: `0x82538(this, 0)` = (slot 253 returns 0) && category != 13 && this+0x73dd == 0 &&
   this+0x7420 != 0 (monster controlled here) && **this+0x72f0 != 0 (think requested)**; if true and
   this+0x75c8 == 0 -> **AI think 0x82ddc** (else 0xc46c8 x2).
2. 0xa5c40: network replay (this+0x73e5) or **death**: if the action is (12, 255) (`0x6ff44(this, 12, 255)`) the
   framework runs 0xa6bb8 and slot 125 is skipped; otherwise slot 123 (vt+0x1ec, unless this+0xb736) then
   **slot 125 (vt+0x1f4) = the monster's action dispatcher**.
3. a second think + same-frame restart when the action changed (this+0x73ea).

AI think **0x82ddc**: needs this+0x72f8 (current think entry) != 0, counts the think timer this+0x7300 down
(0x72128), then walks the candidate lists (this+0x72fc / +0x7340 / +0x73c0) and runs the selector
**0x82f80** (3283 instructions; weighted (cat, num) candidates on the stack; condition helpers 0x86668..0x88ba8;
action-type table 0x1732c8c via 0x50c64/0x50ce0), which starts the chosen action with setAction wrappers
0x75574 / 0x76008. Its data: this+0x72f4 = `[this+0x75f4] + 0x68` = the group array of **rEnemyCmd, the
command table of manifest field 37** (loader 0x4bac8 -> member-function callback at this+0x76f0 = setter
0x70a5c -> this+0x75f4). So the cmdtbl in our arc is what the AI chooses from.

### Ending an action (C)
A handler ends its action by calling one of the base virtuals (never overridden by monsters except 247 x6):
| slot | base | does |
|---|---|---|
| **247** (vt+0x3dc) | 0x75224 | setTargetMode(0); setAction(0, 0/1/2 by state, mode 2); `0x82510(this, 0)` = this+0x72f0 = 1 |
| 248 (vt+0x3e0) | 0x75338 | 0xbf590, 0xbca40; setAction(0, 3, mode 2); 0x82510 |
| 249 / 250 | 0x75394 / 0x753ec | setTargetMode(3 / 4); setAction(0, 6 / 7, mode 2); 0x82510 |
Rathian ends idle with 247 (after its rec+0x1bc timer) and most other actions with 248; unhandled categories
go to 0xca118 / 0xca10c = slot 247. The 4U counterpart is `vcall vt+0x164` (all 42 em089 action ends).
A handler that never calls one of these keeps the monster in that action and the AI never runs again: the
reason the first build only ever saw 3 requested actions.

### setAction 0x76154(this, cat, num, mode, [sp] 0) (C)
Writes this+0x73e0/+0x73e1 (cat, num), +0x73e2/3 previous pair, +0x73e8 serial, clears rec+0x1a1..0x1a3 (step
bytes), runs **slot 127** (vt+0x1fc) in a loop with (&cat, &num) when mode == 1 (or online and mode != 3),
then slot 128, then on-start bookkeeping 0x755b4(this, cat, num) (action attribute lookup through
`[[this+0x75f4]+0x94]`, group 11). Slot 127 = the monster may rewrite a requested action (Rathian: e.g. category
2-7 requests remapped by state); base = bx lr. **We do not need it** (the AI requests em089's own pairs).

### What the base does NOT do (C)
Base slot 125 is `mov r0, #0`. Reactions are the monster's job: Rathian's category 10 handler switches over
~200 numbers; most call **0xa134c(this, sequence table, flag)**, a reaction-sequence player whose tables are
per-monster data (16-byte entries -> motion lists, terminated 0xff/0xfe); unlisted numbers end at once.
Category 11 likewise uses 0xa134c; category 17 -> base 0xaf598; categories 5, 6, 14, 15, 16 -> end.
Only death (12/255) and network replay are generic.

## The framework in module/em089_act.c
- `em089_act_run(self)` (slot 125): looks up (cat, num) in `s_ported` (one function per 4U handler, r1 variant in
  the table), then category 17 -> 0xaf598, 10/11 -> placeholder reaction, category 0 -> idle, anything else -> end
  (slot 247). The generated fallback table (em089_actions.inc) is gone: all 129 em089 pairs have handlers. Logs each
  action start (`gogport: em089 <obj> action c/n (<how>) ...`, 300 lines max) and every stub call (60 max).
- Step bytes rec+0x1a1/0x1a2/0x1a3 = 4U W+0x144/145/146. Own fields (EM089_SIZE = base + 0x50): busy serial,
  timer (4U W+468), aim point (W+392), aim rate (work+0xdc), target latch (work+0xc9), shake latch (work+0xca),
  arena heading (work+0xda), tar amounts per part (work+0..0x1c), port-only safety timer.
- Every handler: `begin()` (busy + step 1) then the 4U entry calls in order; `chain()` for 4U setActionNext; ends
  with slot 247 (4U vt+0x164), slot 249 (4U 0x9559a8) or setTargetMode(0) + setActionW(1, 20) + thinkRequest(0).
  4U frame / timer values are used unchanged with the engine's speed-scaled helpers; motionCheck's r2 is an out
  float* (window fraction) used by the per-tick turns. Frame events 0x8b8e28 are skipped everywhere.
- Targets: `sync_target()` writes the local hunter's root joint into target slot rec+464 before the engine helpers
  that read it (move sequences, setStopDist/inRange, which also steers); `face()` = 4U 0x91db84 toward the hunter.
- Aiming: `lead_point()` = 4U 0x93156c (target + offset rotated by the hunter's yaw from its root joint quaternion
  at joint +96: W, logged as `lead point`), `aim_setup/aim_rate/aim_turn` = the 7/7-style rate (ceil(angle /
  window), capped) and angle step 0x8bdc9c.
- Status per action and every GU mapping with evidence: notes/port-checklist.md (kept current).

### Port state (2026-10-17, second pass: faithful translations)
| category | state |
|---|---|
| 0 | faithful (0/9: 0x920058's guard simplified); 0/2 shares 0/0 (port-only) |
| 1 | faithful step machines; net events 0x93457c, net object 0xc0819c, camera shake, 1/33-34 motion layers stubbed |
| 2 | faithful, all 28 numbers; 2/1, 2/2, 2/62, 2/67 use the real engine move sequence (tables converted) |
| 3, 4, 13 | faithful (4/0-4/3: 4U this+0xc78 write skipped; 13/11: 0xb05934 stub) |
| 7 | all 56 numbers have their handler; simplified: lead point yaw-only, aim layers (0x9200a4, 0x935ff0, 0x918e80, 0x92d0d4, 0xb052d8), shells 0x8c9dd4, effect posts 0x6620c4, attack-slot shortening 0x8c34a0, 7/32 part-break interruption, 7/47 arena wall probe 0x2b9cd4 + turn chain |
| 10 | engine reactions, placeholder (unchanged) |
| 11 | not portable yet: em089's 0x8b6ac8 / 0x8b6da4 / 0x8b6b80 end through unmapped 0x926044 and GU owns category 11 numbering; placeholder kept |

AI conditions (C, 2026-10-17): GU's selector opcode table is at 0x837ac (164 opcodes). em089's most used condition,
opcode 0x6f (111 uses), evaluates `switch (vt+0x214(this, id))` = object slot 133 (base returns 0), i.e. 4U em089
slot 51 (0x8c9084, ids 0..28). Now ported (em089_cond). Also mapped: 4U 40 -> GU 119 (per frame), 47 -> 129
(setAction bookkeeping 0x755b4 calls it with (cat, num)), 50 -> 132. rec+464 is the AI's random move destination
(this+0xba60 from wanderPoint 0xc46c8, copied at think time), not the target; the angle conditions use the target
object at rec+0x5c30. Per-slot status: notes/port-checklist.md "Vtable overrides".

Steering (C now): 4U 0x91db84 is turnToTarget (GU 0x76cc4), not a move helper; GU 0x76c28 is its explicit-position
twin. inRange 0x78c34's tail 0x78f7c steers toward the target slot, which is how 4U's run (2/0) turns.
`setTargetMode` (0xbc8b0) is the locomotion state class (rec+0x1ba), not a target; 4U 0x910c6c is an effect/net
spawn at a joint, not a turn. Attack hits in some motions (e.g. the 7/105 breath) come from 4U slot 75 (per-motion
handler 0x8c3ca0), not from the actions: not ported yet.

## Tar (goudron) coating, 2026-10-17 (static RE; nothing tested in game yet)
**Cause of the missing tar pieces (C from the files, in-game effect S): depth bias.** The 10 tar meshes (materials
`XfBAN__EW_1__m01..m05_liquid_*`, groups 3, 4, 6, 7, 9, 11, 14, 15, 22, 34) are coplanar overlays of the body: 60-97 %
of their triangles lie exactly on a body triangle (arms 97 %, head g3 83 %, chest g7 83 %, tail 60 %). 4U separates
them with the material raster state: tar RSMeshBias5 (tail, r_arm) / 10 (l_arm, head) / 12 (chest), body
RSMeshBias2, eye/wing/add 12, gekiryusou 1. Our MRL takes the templates' RSMesh for every material, so the tar
z-fights with the body and loses wherever the body wins. Not the cause, checked: drawMode (all tar meshes 0xEFFF),
material IA (IASkinTBNLA2wt is used on 0x14D40022 meshes in GU), alpha clip (template `solid_nm` = Rathian's wing
material, FTransparency variant of alpha materials, but its $Globals fAlphaClipThreshold = 0; 04_BM alpha >= 119),
group visibility (default all drawn, see below).
- Fix (asset): `tools/mrl_build.py` now takes an optional 4th tuple element, state names replacing the template's
  BS*/DS*/RS* state (`state_word(name)` = `(~crc32(name) & 0xFFFFF) << 12 | GU record`). build_em089_arc.py must
  pass the 4U RS state: `mats.append((mname, key, gslots, [s for s in states if s.startswith('RS')]))` (all 4U
  RSMeshBias1..12 names exist in GU's package).
- Material animations: the 4U tar states (Solid / Liquid / Gas, transitions, Small..Large, Light_*) are material
  animations **inside the 4U MRL** (hashes `~crc32(name)` at em089.mrl 0x1ab4..0x1f34), looked up by 4U slot 39
  0x8b9bc8 through the model's material-anim controllers (this+0xf4 list, type 1..5 = the 5 tar parts, 6 = lights,
  50 = size; 0xcfba14 = find anim by name hash, 0x636b64(ctrl, slot, anim) = play). Our MRL has no animation blocks
  (GU templates have none either), so the tar shows its static texture. Porting them = converting the 4U MRL anim
  block to GU's (w12/w14) format + the GU controller API: not done.
- 4U tar state word **W+0x7814** (S: bit set read by the emd cond-7 visibility rows): 0x8c69b8(this, mode, part)
  sets part k (parts 0, 7, 2, 3, 6 -> k 0..4) one-hot to bit k (mode 0), 1 << (5+k) (mode 1) or 1 << (10+k)
  (mode 2). Slot 39 at spawn: parts 0, 7 mode 1, parts 2, 3, 6 mode 0 = 0x7c. Rows: g34 hidden by bit 0, g4 shown /
  g22 hidden by bit 1, g7 shown by 0x800, g15 shown by 0x400, g13 shown by 0x10, g3 hidden by 0x8000, g14 hidden by
  0x10000, g102/17/18/19/5/2 shown by 0x20000/0x40000/0x80000/0x100000/0x200000/0x400000.
- **GU group visibility is monster code** (C): bits this+0x110 (1 = drawn); the spawn setup 0xb8c54 sets all 512
  (memset 0xff @0xba258) then calls slot 118. The field-3 XFS (stored at this+0x1420 by callback 0x70854) is only
  applied by `applyPartsState(this, state)` 0x72d34, which each monster calls itself (Rathian @0xcf5a18: state 0,
  then one of each break pair by break count; Kushala sets 0xb610/14/18 via 0x71454(this, 1, 6, -1) for the generic
  0x6f5a4). So without code the XFS does nothing and every group (incl. 4U alternates) is drawn.
- Module: slot 118 `em089_spawn_setup` (em089.c) applies XFS states 0, 2, 3, 4, 5 (base + intact breaks + tail
  intact, layout of emdata4u.partsvis) and logs `gogport: em089 spawn setup ... parts <mgr> states <n> groups
  <bits 0-127>`. Expected bits with the current XFS: word 0 = groups 0-31 minus 2, 4, 5, 7, 12, 15, 16, 17, 18, 21,
  25, 27, 29, 31.
- XFS detail for agent C: the 4U spawn word is 0x7c, not 0, so g19 (mesh 55, add glow) is hidden at spawn (row
  0x100000 mode 1) but the tail-intact state 5 sets it visible; g13 visible is right (bit 0x10 set).

## To do next
1. Turn the AI to Gogmazios' table: build the arc with `tools/build_em089_arc.py --cmdtbl gog` (4U em089_cmd
   in 21 groups as field 37). With Kushala's table the AI requests Kushala's pairs (1/15, 2/0, 2/2 seen).
2. Attack data: our attackdata/hitsize are Kushala's (bone IDs not remapped); convert em089's (4U rEnemyData)
   before enabling -DEM089_ATTACK_HIT, else the indexes above select Kushala's hit volumes.
3. Reactions: Gogmazios reaction-sequence tables for 0xa134c (decode the 16-byte entry format from Rathian's
   tables at 0x179bxxx) and the 4U category 3/4 reactions (motions 263-274).
4. Steering (0x91150c -> 0x7cab8, 0x91ab28 -> 0xc0e78 in the API map), frame events 0x8b8e28 (sound/effect
   triggers), em089 tar state changes (W+0x7814 -> XFS states, MRL material animations; see "Tar" above).
