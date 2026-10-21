# Dalamadur / Shah Dalamadur: class study (Goal B, 2026-10-21)

C = read in code / data, S = strong, G = guess. 4U = MH4U v1.1 code.bin, GU = MHGU 1.4 main. W = 4U work struct
([this+0xe28]). Scripts: dump/scratch/dalamadur-session/ (walkpoly.py, emcmp.py, rowuse.py, gumap.py).

## Correction to phase0.md
- The species row (0x91df20 -> 0x688854) is emd + 8 (consistent with porting-guide "row +0x48 = emd word 20"). So
  W+0x420 (0x937150) = row +0x28 = emd word 12, a FLAGS word (Dalamadur: 2), tested as bits by the damage code
  (0x9201f8 bit 28, 0x920288 bit 16, 0x9202a0 bit 15). C. The walk sets are emd word 10 = row +0x20, read only by
  0x930990. C.

## Walking on the body
- Data (C): emd word 10 -> pointer list of walk SETS; the active set index is W+0x28e. A set = list of strips
  {u32 bone, u32 n (4..9), u32 -> n x f32[3] bone-local vertices}, closed by 0xffffffff (triangle strips, S).
  | em | set 0 | set 1 | set 2 |
  |---|---|---|---|
  | 024 / 110 (identical) | empty | 34 strips, bones 1..5 | 28 strips, bones 1..4 (= set 1 minus the 6 bone-5 strips) |
  | 083 / 111 | empty | 7 strips, bones 140..142 | - |
- Engine (C, generic, no class code): enemy manager per frame 0x68f4e0 sets mgr+0x1379 = 1 and empties 2 slots
  (mgr + 0x540 + 0x780k). Every class tail-calls the base routine 0x94cd6c, which (W+0x143 == 1, set non-null) copies
  the active set into the next slot through 0x685c94 (max 2 enemies, count mgr+0x1378). Player ground queries test
  the slots: 0x681c84 (from 0x682290 / 0x688740), 0x688654 (from player code 0xc5a4d4 / 0xc7b4f8), 0x681e44 (from
  0xb6c6a8; has its own em 24 / 83 branch at 0x682250). Only Dalamadur, its tail, Shah and Dah'ren (em046, 6 sets)
  carry walk sets.
- Which set (C, 4U slot 48 = GU slot 130, per frame):
  - head 0x773304: mode W+0x1c9 != 0 -> 0. Current motion (layer 0, vt+0x84 = 0xb051a4) in {63, 65, 573..577, 770,
    771, 829} -> 0; motion 3 -> walkable only while 0x93906c(this, 2, 0, 0.0, 186.0) (GU 0xb0a60), else 0;
    otherwise part-0 rank (0x94741c(this, 0), GU 0x9d428) != 0 -> set 1, else set 2. Spawn: set 2 (0x76d620).
  - tail 0x8a1fec: the same with the tail's motions (+100): {163, 165, 673..677, 870, 871, 929} -> 0, motion 103
    conditional, otherwise set 1. Spawn: set 1 (0x89ff34).
  - While walking is off both set flag 0x400 in the halfword W+0x42c (reader not traced).
- GU side (gu-walkable.md): GU lacks this engine (S). Walkable monsters (em012, em084 Nakarkos, em087 Ahtal-Neset)
  register their own SBC files as ordinary stage ground / wall entries in sCollision (0xc47f68, owner 0xc47dc8,
  enable 0xc47dec), move them per frame with a joint or root matrix (0xc4754c) and toggle whole entries by motion
  (em084: only motion 833; em087: per piece on motions 771..784). The player's ground query and carry-along are the
  stage ones (C). Port plan (G): each 4U walk strip set -> per-bone g SBC files (strips are bone-local), registered,
  moved and toggled like em087's pieces, enabled per the 4U set rule above.

## Head and tail
- Partner lookup (C): 0x68fd44(enemy mgr, em) scans the 32 enemy slots for W+0x1c0 == em; the tail asks for 24
  (its em 83) or 110 (em 111), the head for 83 / 111.
- Rage (C): tail slot 40 (0x8a0050) copies the head's rage byte W+0x530 (0x954e48, GU 0x8172c) each frame:
  0x93399c(this, 1) or 0x91ad80(this) (GU 0xbd128, S).
- Actions (C): the tail's idle actions 1.50 / 1.52 (0x8a03e8) poll the head's (cat, num) (0x94d788) against table
  0xff5cd8 and chain (0x92b178) into the mapped action. 39 pairs: 2.0..2.5 -> same; 7.60..62, 7.65..79, 7.80..85 ->
  same; 1.9 / 1.6 -> 1.3, 1.10 / 1.7 -> 1.4, 1.11 / 1.8 -> 1.5, 1.3..1.5 -> same. The tail's own AI picks only 1.x,
  7.0..3, 7.20 / 21, 7.40. The tail's motions are the head's + 100 for the shared moves (C for the walk-rule motions).
- Target (C): at spawn the tail targets the head with the generic setter 0x9554c8(this, head, 0, zero vector, 1.0,
  mode 4) (W+0x77e7 = 4, W+0x77e8 = head).
- Position: none of the tail's overrides copies the head's position (C for slots 39, 40, 41, 46, 47, 48 start, 57,
  60, 77, 82, 89 and handlers 1.50 / 7.60). No Dalamadur motion moves the root: all 47 root tracks (bone 255,
  usage 4) in em024_0 / 2 / 3 are constant zero (C). The whole body moves through bone 0 inside the animations, so
  both halves stay at their common spawn point and only their motions must match (S; check in game in Phase 4).
- Modes W+0x1c9 0 / 1 / 2 (user did not recognise "modes"): three body placements in the arena. Bone 0's
  reference position in the mode idles: motion 1 (-2282, 1644, -1488), motion 21 (-2282, 321, -5097), motion 41
  (-2543, 55, 6442) (C). Long motions move between them (63: 2701 frames from the mode-2 placement, 65: 1553 frames
  from mode 1; both turn walking off). Many handlers take the mode as a parameter (1.0-2, 1.3-5, 1.50-55, 7.65-85);
  attack groups 7.0-4 (mode 0), 7.40-46 (set mode 2). What each placement looks like: see in game / a model render.
- Parts (C): tail slot 60 (0x8a2e80) checks the head's part ranks (0x94741c(head, k)); tail slot 77 (0x8a2a68) reads
  the head's joint 101 (0x930894).
- Shared HP (C): pool = enemy manager ([0xf32004]) +0x328.
  - Setup 0x9244e0 / 0x924ce0: pool = W+0x3e8 (HP) for ems 24 / 83 / 110 / 111.
  - Damage function 0x920104, every frame unless W+0x1d9 == 0 or cat == 14: HP = clamp(pool) (0x91ad34: [0, max HP
    W+0x3ec x W+0x3f8]). On a hit: pool += -damage, clamped to [0, max] (0x687254), then HP = pool (0x920b08).
  - GU port (multiplayer): only the controlling machine (enemy+0x7420) writes the pool and copies it into HP; the
    other machines keep GU's net-synced HP (a stale pool must never overwrite it).
- Who controls each half online (GU, 2026-10-21; scratch ctlw.py): writers of enemy+0x7420 / owner +0x7424:
  - spawn (enemy init 0xad890 -> 0xb167c): owner = the net session's member index +0xd57 (0x49638), the same for
    every enemy; controlled = (owner == local index +0xd56, 0x49694). C
  - takeover (0xb16e0, from the enemy update 0xadb8c): once per enemy (+0x7423), when the machine-global net flag
    +0x23b (0x49554 -> 0x69af4) is set: owner = local index, controlled = 1, message (0xcafe8, 2). Every enemy runs
    it in its own update, so all enemies move to that machine within the same frame. C (code), S (that the flag
    marks a host migration).
  - message unpack 0xccc78 -> 0xb161c: owner = the sender's byte; controlled = (owner == local). C
  - Other owner writers: init only (0x6db40, 0xace74; reset 0xaf37c). GU has no per-enemy area hand-over (S),
    while 4U has one (0x912504) and therefore makes the tail adopt the head's controller (0x912820..0x912864, C).
  - So head and tail always share one controller (S), except within a migration frame. The side note's risk (two
    controllers) does not arise from GU's assignment; keep a log line `ctl head / tail` per action for the MP test.
  - MP test 2026-10-21 (PC + Steam Deck over RyuLDN, goal D1 build): host (Deck, member 0) both halves controlled 1
    owner 0; guest (PC) both controlled 0 owner 0, same frame; when the Deck left, the PC took both halves over in
    the same frame (controlled 1, owner 1). Positions identical on both machines (2250, 30, 522) with the push fix.
    So GU's own assignment keeps one controller for both halves, through a migration too (C for this test).
  - HP design that survives a migration: no stored pool. On the controller, a hit on either half applies the same
    HP delta to the other half (4U semantics: one pool); non-controllers never write HP. A new controller just
    continues from the synced HP of both halves (equal by construction).

## Shah (C)
- No class of its own (uEm024 / uEm083). `cmp W+0x1c0, #110` in uEm024: 0x76d8ac (spawn) and 0x76de9c (slot 40)
  loop over persistent effect slots (this+0x8c88, 48-B records from +120); 0x76d54c, 0x770e7c, 0x7713b0, 0x771960 call
  0x7753f4(this, k), which resets those effects at action end. = the extra effects em110_200..210 (S).
- uEm024 has 17 more functions with `cmp #24` (normal vs Shah or partner choice), e.g. slot 48 0x773324: hitzone
  rows 0x772b44 (em024) vs 0x772cf0 (Shah). 0x772b44: raging -> alt rows (part 0 -> 5, 1 -> 6, 2 -> 7, 3 -> 4,
  4 -> 4, 5 -> 1) through partMeatAlt 0x93415c (GU 0xbabb8); calm -> rows by part rank (partMeatBase 0x936ea8, GU
  0xbab88). uEm083 has 9 `cmp #83` sites (phase0.md).
- Data: walk sets identical (above); em110_cmd == em024_cmd; etd / emd / effects / sounds / textures differ (phase0).

## Model groups and visibility (C, 2026-10-21)
- One shared model (groups 0..13, 15..25, 100..108; Shah adds 30..45). Spawn masks (this+0x108.. = 32 groups per
  word): the head (0x76d5a0) hides 1, 16..22, 25, 106..108 and shows 100; the tail (0x89fe4c) hides 0, 2..13, 15,
  23, 24, 30..45, 100..105 and shows 107. So head = 0, 2..15, 23, 24, 30..45, 100..105; tail = 1, 16..22, 25,
  106..108.
- Rows (emd +0x88, {s32 group, u16 cond, u16 mode, u32 param, u32 threshold}) are evaluated per group by 0x948378
  and written into the same masks by 0x942924. Mode 0 hides while the condition holds, mode 1 while it does not.
  Conditions (switch 0x9483c8): 0 W+0x7a1a != 0; 1 W+0x42c & p (sever flag); 2 / 3 / 9 never; 4 W+0x797e == p;
  5 (p & ~W+0x797e) == 0; 6 part rank (0x94741c) >= threshold; 7 W+0x7814 & p (Shah's effect state, reset by
  0x7753f4); 8 enraged (W+0x530 == 1); 10 W+0x53a or W+0x7e80 bit 5; 11 dead / captured (0x94d7a8).
- Dalamadur uses 6 (break levels 1..4 on records 0..7), 0 (g23), 8 (rage glow g24, g25, g108), 1 (tail sever:
  g22 shown, g108 hidden), 7 (tail g106; Shah g30..45). GU port: these masks change at runtime (breaks, rage,
  sever, Shah state), more than the donor's 12-state XFS can express: the class evaluates the rows each frame
  (port of 0x948378) and sets GU's group visibility; the XFS holds the spawn state.
- At spawn (rank 0, not enraged, no sever / state bit) the rows leave the head 0, 4, 6, 8, 11, 100..104 and the tail
  1, 16, 18, 20, 107 (C, data; test 2026-10-21 logged exactly these bits): 2, 3, 5, 7, 9, 10, 12, 13, 15, 17, 19, 21
  are the broken-part variants (cond 6 mode 1), 23 / 24 / 25 / 108 the cond-0 / rage pieces, 22 the sever stump.

## Where the body is cut (test 2026-10-21, data C / arena S)
- No mesh spans both halves: head meshes use bones 0..16, 101..107, 120..138 only, tail meshes 0, 200, 140..157
  (C, converted model). The body is split at the bind origin: one ~1808 x 1188 cross-section loop, weighted 100 %
  to bone 0, closes neither half (scratch openends.py).
- Each half animates only its own bones (runtime joint log: head instance joint 154 constant, tail instance joint 0 /
  200 = its object position). So the head's cut follows head bone 0 (motion 1: (-2282, 1644, -1488) from the
  object), the tail's cut sits at the tail object's origin (motion 101: bone 200 identity, bone 140 at 0). In 4U
  both objects are at the arena origin, so the two ends are ~3100 apart: the body between them is not modelled.
- 4U arena (k02 spire placed at (404, 1062, -112), speartip-crag.md): the tail's end (origin) is inside the spire's
  base (670 from its centre at y 0, spire radius up to 3120 there); the head's end is ~250 outside the spire's
  surface at its height (1679 vs <= 1424) with a ~900-radius cut face. User (2026-10-21): the ends are hidden in
  the spire, and when Dalamadur moves the whole body shows, every part of it passing through one point (the two
  halves' synced motions N / N + 100 slide the body through the junction). So both objects must sit at exactly
  the same origin (GU pushed them 200 apart, fixed below). In GU's Sanctuary both ends show as flat cuts until
  Speartip Crag is ported (goal E).

## Enemy push (helper trace 2026-10-21; key addresses re-checked)
- GU sHitPush (vtable 0x173ec7c, slot 7 0x17c518): enemy-vs-enemy pass 0x17cbf0 over enemy pairs, sphere from
  0x712e8 = dtbase+0x88 = emd word 21 "PushHit" (Dalamadur: (0, 100, 0), radius 100 on all four ems), equal
  priorities -> each pushed by half the overlap into rec+0x530.., applied by the next update (0xae888) (C). That is
  the 200 gap of the first tests. No em-id check in the pass (C).
- Skip conditions per enemy include rec+0x529 != 0 (read only by this pass) and rec+0x528 (also disables the
  player push: not used). The update clears 0x528..0x52a every frame (0xa5198 from 0xadba4; stores 0xa5320..
  0xa5334, C); GU's Ahtal-Ka / Ahtal-Neset set rec+0x529 = 1 in slot 119 (0x10b6b7c / 0x10a8748, C).
- 4U: same pass (0xbbe244), skipped while W+0x55a / W+0x55b; uEm024 / uEm083 slot 44 tails write W+0x55b = 1 every
  frame (0x77311c / 0x8a1fc4, C), with W+0x79a9, W+0x628, W+0x978 = 1 in the same block (meaning not traced: check
  in D2). 4U W+0x55a..0x55c = GU rec+0x528..0x52a (S).
- Port: dala_state_frame (slot 119, both halves) + once at spawn setup writes rec+0x529 = 1.
- Assets: arcs must list TEX -> MRL -> MOD (a model loads its MRL by path); with the model first nothing was drawn
  while the collision worked (test 2026-10-21, fixed in build_dalamadur_arc.py).

## Overridden vtable slots (C)
- uEm024 (25): 1, 4, 6, 9, 16, 30, 36, 39, 40, 41, 44, 46, 47, 48, 50, 51, 52, 57, 60, 64, 77, 78, 79, 82, 89.
- uEm083 (19): 1, 4, 6, 9, 16, 36, 39, 40, 41, 44, 46, 47, 48, 51, 57, 60, 77, 82, 89.
- Tail slot 82 (0x8a1fd0) returns mode == 2; slot 89 (0x89fab8) handles modes 1 / 2 (mode: 0 ground, 1, 2; what
  modes 1 and 2 look like in game: ask the user).

## User facts (2026-10-21)
- Heat aura near the head: yes, but the user does not remember when it is active. 4U code: 0x689c08 is gated by
  0x92d774(enemy) (0x689c88) before the em 24 / 110 zone (joint 101 r 1700 or joint 4 r 1250, by [this+0x8d88]+0x40):
  port the gate and the zone literally (hook GU 0x6a160), trace 0x92d774 in Phase 4.
- Gathering: the head can be carved during the fight, maybe another body spot (4U item lists 0x1003ed4 for 24 / 110,
  spawned from uEm024 slot 39, S); some meteors leave mining points in the arena (shell -> gather point: trace which
  shell type in Phase 4).
- Map: two icons, head and tail (4U icon classes 22 / 23 at joints 107 / 154, C).
- Music: changes with the phase (= k00 broken, speartip-crag.md).

## 4U common code that names the Dalamadur ems (C list, each still to classify and map to GU)
`ldrb W+0x1c0` then `cmp #24 / #83 / #110 / #111` outside the two classes (emcmp.py, linear 60-instruction window
over compare trees; a lower bound: code that reads the em number some other way is not covered):
0x3046a8 (24, 83 and 46 Dah'ren), 0x308744 (battle-music start: 24 / 110 start it unless W+0x34c == 2, the tails
83 / 111 never do), 0x326a6c / 0x326c40 (110: id 81 instead of 35), 0x681e44 (walk query),
0x689c08 (24 / 110, beside em 32), 0x910650 (all four: W+524 and a flag bit), 0x912504, 0x916160, 0x917d48,
0x91a950, 0x91df44 (map-hit sphere from joint 154), 0x920104 (HP pool), 0x9244e0 / 0x924ce0 (pool setup),
0x9259c0, 0x92712c, 0x92e218, 0x944e80, 0x94e6f4, 0x978c04, 0x9870a8, 0x98897c, 0xbe9c64, 0xbf4a48.
