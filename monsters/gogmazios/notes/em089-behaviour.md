# MH4U Gogmazios (uEm089) behaviour: spec for the MHGU re-implementation (2026-10-17)

Static RE of MH4U v1.1 (`dump/exefs_v11/mem.bin`, `dump/mh4u.asm`). Tools added:
`tools/dis4u.py` (fast asm lookup), `tools/disp4u.py` (dispatcher emulator), `tools/em089_actions.py`
(action table -> `dump/em089/actions.txt`), `tools/emc.py` (EMC reader). Extracted arc: `dump/em089/`.
Confidence: **C** = read from code, **D** = derived/inferred (names are guesses unless marked C).

## 1. Code block and class layout (C)
- **Correction to gogmazios-study.md**: em089's code is `0x8b661c..0x8ca1f0` (78 KB, 20.2k words,
  ~100 functions, **124 external callees / 1383 calls**, 3.3k VFP ops). `0x8ca1f4..0x8cc724` is em099's
  (Diablos) action code (called from 0x8d4224/0x8d4260). Callee counts: `dump/em089/ext_callees_v2.pkl`.
- `uEm089` = `uEnemy` (0x8d88 bytes) + one word at **+0x8d88 = copy of the work pointer `[this+0xe28]`**.
  No private struct: all state lives in the shared enemy work struct **W = [this+0xe28]**.
- ctor `0x8ca0ec` (calls uEnemy ctor 0x955ff4, sets vtable, stores W at +0x8d88); allocator `0x8ca1bc`
  (heap 0x1076cc, size 0x8d90); both called by the 4U enemy factory at 0x6912ec / 0x691314. Destructor = slot 1.

## 2. Action framework (C)
- W bytes: **+0x1ca = action category (0..13)**, **+0x1cb = action number**, **+0x144 = step** of the
  running action (0 = enter, 1.. = phases), +0x1c9 = mode flag (D: "tar/alt mode", selects alt handlers),
  +0x1c8 = state class (1/3 = special states, D).
- **Slot 44 (0x8c3ac0) is the per-frame action dispatcher**: jump table on +0x1ca ->
  cat 0 `0x8b6f2c`, 1 `0x8bac40`, 2 `0x8bd4b0`, 3 inline (1cb 0/1 -> 0x8b6654(r1), 2 -> 0x8b67e4),
  4 `0x8c2640`, 7 `0x8c0f94`, 10 `0x8c2784`, 11 inline (0x8b6ac8 / 0x8b6da4 when +0x1c9==1 / 0x8b6b80),
  13 inline (num 11: motion 73 action), 5/6/8/9/12 = nothing. Sub-dispatchers switch on +0x1cb.
- Handlers are step machines: `step==0` -> init (set step 1, setMotion, set target/turn mode), later steps
  poll `motion_check(kind, frame)` (0x91ab1c) to fire attacks/effects, and end with `isMotionEnd()`
  (0x b05df4) -> `vcall [vt+0x164]` (= action finished; the EMC interpreter then picks the next action).
- Full table (166 entries incl. engine actions) in `dump/em089/actions.txt`. Summary:
  | cat | meaning (D) | entries | handlers |
  |---|---|---|---|
  | 0 | idle / wander | 5 | 4 (0x8b9aa8, 0x8b999c, 0x8b9844, generic 0x8b8e28) |
  | 1 | movement / turns / repositioning | 24 | 8 |
  | 2 | locomotion incl. flight (motions 0:75-78), roars, threat | 28 | 8 |
  | 3 | sleep/rest? (motions 263-267) | 3 | 2 |
  | 4 | reactions (motions 265, 271) | 11 | 3 |
  | 7 | **attacks** (56 numbers, motions bank 2 = 512+i) | 56 | ~30 |
  | 10 | engine actions (flinch, trap, status...) -> **base uEnemy** (0x9197c0, 0x938620, 0x940b50); only 108/109 em089-specific (0x8bdaec) | 38 | 1 |
  | 11 | special (0x8b6ac8 family) | - | 3 |
- `0x8b8e28(this, motion)` is a generic "play motion r1 to the end" action (used for 0:3, 1:21/24/34, 2:1/2/62).
- Motion ids = `bank << 8 | index` into the 4 LMTs (`em089_0..3.lmt`, version 0x43, **114 motions**:
  bank 0 = 29 (basic), 1 = 8 (reactions), 2 = 44 (attacks), 3 = 33 (special / gimmick sequences)).
  List: `dump/em089/motions.txt`. setMotion = `0x94e350(this, mot, s0, s1)` -> `0x9190c4(this, mot, flags, s0, s1)`.

## 3. EMC (em089_cmd) (C structure, D opcode semantics)
- Same file version as MHGU (`EMC 0x20120804`). 23 groups: g0 = 33 top-level AI selector scripts,
  g1 = 146 action scripts, g2..22 = tiny lists. Scripts are bytecode: `00 cat num` = start native action,
  `14 n` = run g1 script n, `02 00/02 01 w/02 ff` = weighted random, `6f/77/78/1d/0b/0c/2e/57.. 00/01/02/ff`
  = condition blocks. Heuristic reference scan (`emc.py FILE refs`): 101 native refs, **92 match the native
  table**; the rest are tokenizer noise. Category 10 never appears in EMC (engine-driven).
- => **The AI decision layer is data and portable as-is**; the MHGU interpreter is the same format. What must be
  provided natively is the set of (cat, num) handlers.

## 4. Vtable overrides (C; base = uEnemy slot it replaces)
| slot | em089 | base | role |
|---|---|---|---|
| 1 | 0x8ca128 | 0x956154 | destructor (clears quest flags in W+0x574 list, base dtor, free) |
| 5 | 0xd02324 | 0xd02784 | getDTI |
| 6, 9, 16, 65* | thunks/no-ops | | same behaviour as base (6 = bx lr, 9/16 = b base); *65 returns (W+0x1c9==1) instead of 0 |
| 35 | 0x8ca074 | 0x94e6c0 | onMotionChange(mot): base + motion 61 sets model flags (+0x108 \|= 0x200024, +0x10c \|= 8) else +344 float |
| 36 | 0x8c9f4c | 0x94dd8c | spawn/area setup: base + em089 init (reads global +0xaa8 list) |
| 39 | 0x8b9bc8 | no-op | per-frame em089 extra update (tar/material state? uses W+0x7a14) |
| 40 | 0x8ba258 | no-op | per-frame state logic (states +0x1c8/+0x1c9), calls 0x8c2518 / 0x8c352c |
| 42 | 0x8c9d68 | no-op | stage/quest check (global +0x1c == 61, quest id range): special arena logic gate |
| 44 | 0x8c3ac0 | 0x934b40 | **action dispatcher** (section 2) |
| 46 | 0x8c677c | no-op | event filter (W+0x1c9 -> 20) |
| 47 | 0x8c8778 | no-op (ret 0) | onHit/onDamage(type r1 0..7, r2): sets W+0x28d, part/tar reactions |
| 48 | 0x8c6e58 | ret 1 | per-motion processing (switch on current motion 0x90f994) |
| 50 / 56 | 0x8c8da0 / ret 0 | ret 0 | iterate per-part arrays (offsets 84/94 in W) |
| 51 | 0x8c9084 | ret 0 | 29-way event switch (r1 = event id) |
| 52 | ret 1 | ret 0 | capability flag |
| 57 | (W+0x1c8==0) | ret 1 | "can be targeted/act" condition |
| 58 / 64 | ret 1 / 0x8c67c0 | | gimmick / special hit (64: r1==6 path uses 0x94741c, rng 100) |
| 60 | 0x8c9b48 | ret 0 | 7-way state query when +0x1c8 in {1,3} |
| 75 | 0x8c3ca0 | 0x93574c | **per-motion event handler**: big switch on current motion id (21, 28, 29, 65, 73, 264, 268, 274, 5xx, 7xx...) spawning effects/attacks at frames |
| 76 | 0x8c3c4c | ret 0 | angle to target from W+0x7a20 vector (atan2 0x568c8c) |
| 77 | 0x8c99a0 | no-op | per-frame for bank-3 motions (768+31.., 792): gimmick sequences |
| 78 / 79 | get/set byte [W]+0xda | W+0xb15 | net sync / save of one state byte |

## 5. Special mechanics (D unless noted)
- **Tar states (C strings)**: model/material animation names used via name lookup (0xcfba14):
  `Solid, Liquid, Gas, Sol_to_Liq, Liq_to_Sol, Liq_to_Gas, Gas_to_Liq, Sol_to_Gas, Gas_to_Sol`, sizes
  `Small, SmalltoLarge, LargetoSmall, Large`, lights `Light_Gas_Bress(_End)`, `Light_Wing_Attack(_back)`,
  `Light_Wing_Attack_gekiryusou`, `Light_Wing_Attack_houdai`, `Light_Tail_Attack01/02` (table at 0xff6f80).
  => tar coating = material/texture animation states driven by code; tar explosions/laser are attacks (cat 7).
- **Arena gimmicks**: `gekiryusou` = 撃龍槍 = **Dragonator** (its model `em089_gekiryusou` + sounds
  `ship_pilebunker_*` are in em089.arc), `houdai` = 砲台 = **cannons**. Dedicated wing attacks target them;
  slot 42 gates on stage id 61 (Battlequarters, D). Sequence tables at 0xff7020.. hold bank-3 motion chains
  (0x301, 0x303, 0x324...) used by slot 77.
- **Shells/projectiles**: no uShell DTI is referenced; projectiles/attacks go through id-based helpers
  (`0x914dfc/0x933144` attack-collision by index, `0xc0819c` spawn 200-byte net object for the local player,
  `0x6620c4` 16-byte event post). Effect lists: `effect/efl/em/em089/em089_000..051` (25 files).
- **Flight / phases**: flight locomotion = cat 2 handler 0x8b8ca4 (motions 0:75-78); phase/mode = W+0x1c9/+0x1c8.
- Shared code with em099 (0x8d3d20, a target search / "hit check in cone" routine) is called 5x.

## 6. External API (top callees, D names; `all` = callers in the whole game)
| addr | em089 calls | all | guess |
|---|---|---|---|
| 0x91ab1c | 412 | 2228 | motion_check(kind, frame) -> bool (b 0xb06b9c) |
| 0xb05df4 | 92 | 3530 | isMotionEnd() (motion ctrl at this+576) |
| 0x9167ec | 87 | 3492 | setTargetMode / turn mode(mode) |
| 0x94e350 / 0x9190c4 | 82 / 8 | 2866 / 379 | setMotion(mot, s0 speed, s1 blend) |
| 0x910c6c | 75 | 451 | turn toward target / setMotion with turn (mot, r2) |
| 0x914dfc / 0x933144 | 46 / 35 | 817 / 943 | enable attack collision #idx (attack data) |
| 0x9162f8 | 38 | 51 | set attack id byte W+0x78bd |
| 0x911cb4 | 27 | 543 | get speed factor (W+440 * W+444) |
| 0x568c8c | 26 | 792 | atan2 -> u16 angle |
| 0x91db84 | 23 | 632 | move / root-motion helper |
| 0x91150c | 17 | 273 | rotate toward (flags) |
| 0x636b64 / 0x636b54 | 17 / 6 | 135 / 12 | set/get model slot table entry (+72) |
| 0x93d8a8 | 16 | 568 | table lookup by species W+0x1c0 |
| 0x92dd04 / 0x92dc88 | 15 / 13 | 443 / 321 | position/target computations |
| 0x92e9d4 | 14 | 666 | state check (W+0x1c8) |
| 0x94741c | 14 | 243 | rank/difficulty table lookup |
| 0xb0709c | 12 | 1126 | frame compare |
| 0x6620c4 | 12 | 35 | post 16-byte event (sound/effect request) |
| 0x91b3f4, 0x916260 | 11 / 8 | 628 / 99 | stop / reset velocity (W+352) |
| 0x94ef9c, 0x94f440 | 11 / 7 | 682 / 187 | movement-with-motion helpers |
| 0x922cd8, 0x93c6c8, 0x922c78 | 10 / 7 / 6 | 1050 / 577 / 477 | set W flags (+0x3e3, +0x41a...) |
| 0x938620, 0x9399c0, 0x935ac8 | 9 / 4 / 4 | | status / damage-state helpers |
| 0x93093c | 8 | 194 | get target position |
| 0x90f994 | 8 | 312 | current motion id |
| 0x2b02c0 | 3 | 71 | random(n) |
| 0xcfba14 | 3 | 132 | find model joint/anim by name hash |
| 0xc0819c | 3 | 47 | spawn net object (local player) |
| 0xc0bd38 | 6 | 25 | camera shake / quake request |
| 0x93156c | 3 | **3** | uEnemy helper used ONLY by em089 (player/target lookup via global +0xaa8) |
| 0x8d3d20 | 5 | 7 | em099-file helper (target cone search) |
Full list with first instructions: `dump/em089/ext_callees.txt` (old block bounds).
=> **~95% of callees are generic uEnemy services** that every MHGU monster also uses (MHGU has the same
engine lineage); they must be mapped to MHGU addresses, not rewritten. Only 0x93156c and 0x8d3d20 are
Gogmazios-specific outside the block.

## 7. Data resources (C)
- MH4U per-monster data: `em_data.arc` -> `enemy/em089/data/em089` as **rEnemyData** (0x0a0e48d4, 5968 B)
  and **rEnemyTuneData** (0x3d8bbbac, 10508 B); `em089.arc` -> **rEnemyCmd** (EMC).
  MHGU instead uses rEnemyDtBase/DtTune/DtBaseBui/AtkHitData/BodyData/cmdtbl (+ area files): needs conversion.

## 8. Port estimate
- **Data-driven / reusable**: EMC AI (same format), 114 LMT motions (same version), effect lists, sounds;
  hit/attack data after conversion to MHGU's dtbase/attackdata format.
- **Must be re-implemented natively** (C in the module, against MHGU's uEnemy API): the class (vtable with
  ~20 real overrides), the action dispatcher + ~65 handler functions (each 50-600 words, mostly
  setMotion / motion_check / attack-enable / turn calls — mechanical translation once the ~120 API calls
  are mapped to MHGU), slot 75/77/48 motion-event logic, tar material-state logic (slot 39/40), arena-gimmick
  hooks (slots 42/58/64, Dragonator/cannons need MHGU stage support or cutting).
- Rough size: ~20k ARM words of em089 code -> estimated 4-6k lines of C; the gating work is the API map
  (124 callees) and the W-struct field map (4U W offsets -> MHGU W offsets).
