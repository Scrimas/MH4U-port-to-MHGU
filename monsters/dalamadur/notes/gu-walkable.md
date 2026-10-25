# GU walkable monsters (SBC on the body): static study for Dalamadur

Static RE only (2026-10-21), nothing run. C = read in code / data, S = strong, G = guess. GU = MHGU 1.4 main
(addresses = main offsets), 4U = MH4U v1.1. Scratch scripts: `dump/scratch/dalamadur-session/walk/`
(arcls.py arc listing, fileids.py file IDs + immediate sites + manifest field 36, d.py disassembly with literals,
gotref.py pc-relative refs, sbcinfo.py SBC summaries; em08x_ls.txt listings).

## 0. Summary
- GU has ONE walk-on-monster mechanism: the monster registers its own SBC files (rCollision, the stage format) in
  the stage collision system sCollision as ordinary ground (type 1) / wall (type 2) entries, owned by the
  monster, and moves them with a matrix (root or joint) each frame. Players stand on them through the same ground
  queries as on the stage. C (load, register, move, query) / S (player carry-along, section 4).
- Loading is class code (vtable slot 87), triggered by data: FILES manifest field 36 = -2. Joint binding is a
  table / immediates in class code, not in the SBC and not in the file name. Enable / disable is class code keyed
  on the current motion. C.
- Three GU users: em012 (Lao-Shan, 1 g + 1 w, joint 1, per frame), em084 (Nakarkos, 1 g + 1 w, root transform,
  placed once in motion 833), em087 (Ahtal-Neset, 12 pieces, joints / root / external objects, per frame). C.
- The 4U strip engine (walk sets in emd word 10) is not in GU: none of its code signatures exist (section 6). S.
- Port recipe for Dalamadur (G, design): convert each 4U walk set into per-bone g SBC files (the 4U strips are
  already bone-local), register them like em087 (0xc47f68 type 1, owner = the monster), switch them with
  0xc47dec by the 4U set rule (class-study.md), and push the joint matrices every frame with 0xc4754c.

## 1. Who loads `collision\emXXX_YY_gNN / _wNN` (Q1)
- Generic trigger (C): FILES loader 0x4b554 (part of the per-monster manifest load, see registry.md) reads manifest
  field 36 (+0x90). Value -2 -> calls the loader callback at loader+0x8c, which uEnemy slot 82 (0x7051c) sets to
  0x70a10 (store 0x706e0 to this+0x76d8; loader = this+0x764c). 0x70a10 = `this->vt[87]()` (ldr [vt, #0x15c]).
  Base slot 87 = 0x6be98 `bx lr`.
- Field 36 = -2 only for registry indices 69 (em084), 70 (em085), 116 (em012), 132 (em086), 133 (em087),
  134 (em088) (fileids.py manifest). Slot-87 overrides: em084 0x1068220, em012 0xd784bc, em087 0x10a6f74 (vtable
  0x1800bbc, gu_enemy.py misses it), plus em085 / em086 / em088 (no SBC in their arcs: their hook loads other
  things, S). C
- The SBC is found by FILE ID, hard-coded in the class (C): 0x152960(sResource, fileId, DTI rCollision 0x2125dd4)
  (the DTI name is registered at 0xb78e24). IDs (path = ~crc32 of the arc path, table 0x15a0ce0):
  | em | g | w | sites |
  |---|---|---|---|
  | em084 | 0x7fdd | 0x7fde | movw 0x106823c / 0x1068280 |
  | em012 | 0x84a2 | 0x84a3 | 0xd784d8 / 0xd78574 |
  | em087 | table 0x16aa12c (12 ids, one g per piece) | table 0x16aa15c (3 per piece, -1 = none) | loop 0x10a7080 |
- Registration (C), em084 0x1068220: `res = 0x152960(..)`; `this+0x262a8 = g res`, `this+0x262ac = w res`
  (addref 0x887648 / 0x887660); then for w then g:
  `h = 0xc47f68(sCollision, res, type (1 = g, 2 = w), area = this+0x1054, 1, 0)`; `0xc47dc8(sCol, this, h)`
  (owner); `0xc47dec(sCol, 0, h)` (disabled). Handles: g this+0x262a0, w this+0x262a4.
  em087 does the same per piece: g handle this+0xcb18+4i, g res this+0xcb48+4i, w handles this+0xcb80+4k.
- sCollision = the singleton at [GOT 0x21270e0] (written by ctor 0xc0c8ac at 0xc0d434; DTI names at 0xc113ec). The
  stage loader 0x4ff9dc uses the same calls (0x152960 with rCollision, 0xc47f68 types 1 / 2 / 16). C
- 0xc47f68 -> 0xc19940(sCol+0xb8, res, type, area, a5, a6): allocates a 0x70-byte sCollision::Sbc entry (DTI
  0x21275d0): +5 enabled (1), +8 handle, +0x10 type, +0xc area data (0xb12fe8), +0x1c owner, +0x20 refcount,
  +0x2c cSbcMoveMatrix (0xc0c60c), +0x54 resource, +0x58 / +0x5c parts array (sCollision::Sbc::Parts, 64 B each),
  +0x60 = a6; inserts the bbox into a dynamic BVH (0xc98880, sCol+0xd8 + 64 * tree). With a5 = 0 an entry that
  already holds the same resource is returned instead of a new one (loop 0xc19970, gated on [sp+0x38] = a5; corrected
  2026-10-22, the earlier text had a5 / a6 swapped). The monster calls pass a5 = 1: always a new entry. C (field
  names from the DTI list, S)

## 2. How it follows the monster (Q2)
- API (C): 0xc4754c(sCol, handle, pos*, quat*, flag) builds a 4x4 from quaternion + position, then 0xc473c0 queues a
  move request (cSbcMoveReserveInfo: entry, matrix, flag; refused when the entry has no resource or +5 == 0,
  0xc18038) into a per-thread queue (sCol+0x6ec0); 0xc0f618 (sCollision, S: its frame update) drains the queues
  through 0xc1a548: new matrix into the entry's cSbcMoveMatrix (0xb13638, compares new vs old with 0x9c49ac, S)
  and re-files the entry between two BVH trees (container sCol+0xb8, trees +0x820 / +0x1020 + 64 * tree; S: static
  vs moving). C (calls). flag: em084 1, em012 0, em087 piece byte; meaning G (force / teleport vs. move).
- Binding is class code (C):
  - em012 slot 168 0xd79a98 (per frame while this+0xcac0): M = joint 1 (0xc1660(this, 1, out), joint matrix,
    fallback joint 0) -> quat 0x72ea8 -> 0xc4754c for both handles (this+0xcac4 / +0xcac8).
  - em084: one placement, 0x106e0e0: root position rec+0x40..0x48 and rotation from rec+0x50..0x58 (u32 angles ->
    sinf 0x13efde8 / cosf 0x13efdf4) (rec = [this+0x1428]) -> 0xc4754c(.., flag 1) for g and w.
  - em087: per frame, slot 20 0x10a6f44 tail-calls 0x10ad580; piece table 0x16aa288 (12 x {joint, 1, mode, 1}):
    | piece | joint | g | w |
    |---|---|---|---|
    | 0 | 160 | g02 | w02 |
    | 1 | 161 | g00 | w00 |
    | 2 | 0 | g01 | w01, w12 |
    | 3..8 | 255 = root | g04, g03, g10, g11, g12, g05 | w04, w03, w13, w14, w15, w11 |
    | 9..11 | 130..132 = external objects ([GOT 0x2139968] + 16k: pos +80, angles +128) | g07..g09 | w07..w09 |
    Joint matrix = `this->vt[52](joint)` (0x53aad8: [this+0x498] joint map, [this+0x494] 160-B joints, +0x10); 255 =
    `vt[21](-1)` (0xc1628 -> this+0xb0, the object matrix). Mode (table col 3) chooses extra paths (0x7c6914 for mode
    1, others at 0x10adadc / 0x10adffc) not traced. C (joint path), G (mode meaning)
- The SBC carries no bone data: each file has 1 part (id 0) whose vertices are in the bound joint's / root's local
  space (section 5). C (data), S (local-space reading from the bboxes).

## 3. Enable / disable (Q3)
- Whole entry on / off: 0xc47dec(sCol, value, handle) writes entry+5; 0xc47e10 reads it. Queries (e.g. 0xc402c0) and
  move requests (0xc18048) skip +5 == 0. C. Parts of an entry also carry flags (Parts +0xc / +0x1f / +0x20, read in
  0xc1d6a0..; kobj-style part toggles), unused by the monster files (1 part each). C (reads) / S (use)
- em084: slot 170 0x106cd00 (per frame): curMotion (0xb0a00) == 0x341 (833) and this+0xcb20 == 0 -> 0x106e0e0
  (enable both, place, +0xcb20 = 1). Slot 129 (action start) 0x1069d8c -> 0x106ca48 at 0x106ab40: disable both,
  +0xcb20 = 0. So Nakarkos is walkable only during motion 833 (which motion that is in game: open). C
- em087: slot 170 0x10a8948 -> 0x10a8bd8: switch on curMotion 0x303..0x310 (771..784) sets piece flags
  (this+0xcb00+i) and toggles handles (0xc47dec; 74 call sites, most in 0x10a8bd8 / 0x10a87f8 / 0x10a8788).
  Per piece, per motion. C (switch), S (per-piece meaning).
- em012: on while this+0xcac0 is set (slot 168 gate); writer not traced. C (gate)

## 4. How a player ends up on it (Q4)
- Same system as the stage: the entries live in sCollision next to the stage g00 / w00 (same DTI rCollision, same
  0xc47f68, same type bits 1 / 2). Generic query 0xc4009c (vtable 0x18454ac slot 28) skips entries that are
  disabled, have no resource, are owned by the querying object (owner == query owner: the monster ignores its own
  SBC), or miss the type mask (+0x10) or the +0x14 mask (S: area bits). C
- Moving ground (S): sCollision has move support built in (classes sCollision::cSbcMoveMatrix,
  cSbcMoveReserveInfo / ...All, cSbcMoveResetReserveInfo; moving BVH tree). Player side: slot 10 of 15 related
  vtables (0x17491e4 .. 0x1751614, 0x8cc apart; G: the player / weapon classes) = 0x29c368 calls 0x4f594c(obj+0x2f00)
  -> 0xc3eb0c(sCol, ..) -> 0xc1d5f0(contact record): takes the stored contact (entry index +8, part +0xc, local point
  +0x80..+0x88), rebuilds its world position through the entry's current matrix (0x183c0c) and returns the owner
  (entry+0x1c). That is the carry-along: the player's last ground contact is re-evaluated in the moved collision.
  C (code path) / S (meaning). No class code is needed for it.
- Area: the entry is registered with the monster's current area (this+0x1054, S). Re-registration on area change
  not checked (irrelevant for a one-area arena). G

## 5. SBC content (Q5, sbcinfo.py; all GU format, 1 part id 0, 1 BVH node)
| file | tris | verts | polys | groups | bbox (local) | normals |
|---|---|---|---|---|---|---|
| em084_00_g00 | 27 | 23 | 27 | 2 | (96 -89 179)..(569 553 1962) | 27 floor |
| em084_00_w00 | 115 | 75 | 104 | 3 | (-554 -291 -84)..(642 2136 1962) | 113 wall, 2 floor |
| em012_00_g00 | 16 | 15 | 16 | 1 | (-458 96 -67)..(458 313 421) | 16 floor |
| em012_00_w00 | 48 | 40 | 48 | 2 | (-608 -173 -388)..(608 707 421) | 40 wall, 8 floor |
| em087 g00..g12 (12) | 2..117 | | | 1..4 | joint / root local | all floor |
| em087 w00..w15 (13) | 6..94 | | | 1..4 | | all wall |
- g = ground (only up-facing triangles, registered type 1), w = wall (vertical triangles, type 2). C (data + type
  argument)
- Group words: g 0x0200004c / w1 0x3d000007, 0x3d000000 (em084), 0x33000001 (em012) / w2 0x40040000, 0x40000000;
  w 0x0200004d / 0x0200004e (w2 = 1), em012 also 0x0200047d. Same vocabulary as the stage files (sbc.py). Triangle
  extra bytes = the usual edge flags, both trailing words 0. No bone or per-triangle owner field. C (values), G
  (meaning of the bits)

## 6. The 4U strip engine in GU (coordinator lead)
- 4U (C, class-study.md): walk sets = emd word 10 (row +0x20, 0x930990) indexed by W+0x28e; base routine 0x94cd6c
  copies the active set into one of 2 manager slots (0x685c94; stride `rsb r2, r4, r4, lsl #4; rsb r2, r2, r4,
  lsl #7` then `lsl #4` = 0x710; slot bytes +0x540 / +0x541, max 25 strips of 72 B); player queries 0x681c84 /
  0x688654 / 0x681e44.
- GU search (S: absent): no `rsb x, y, y, lsl #4` + `rsb z, x, y, lsl #7` pair anywhere in main; no `ldr x, [y,
  #0xc]!` + `cmn x, #1` strip walk except an unrelated bitmap allocator (0x86c364); the only functions storing a
  byte pair at +0x540 / +0x541 (0x61d1d4, 0x85d174) are a 3-entry list and a field reset, not the slot code; no
  x72 indexing with a bound of 25. GU's species data is dtbase (0x712a4 = 4U 0x91df20, porting-guide), no
  equivalent of row +0x20 found. Nothing in GU feeds such an engine; GU's walkable monsters all use section 1-4.
- Port consequence: either rebuild the 4U engine in the module (manager slots + player ground query hook), or (S,
  simpler) convert the strips to SBC and use sCollision, which already handles moving ground and multiplayer
  (every machine runs its own collision; only the motion-keyed switches must match).

## 6b. Walk study 2026-10-22 (push volumes, 4U probe, seams)
- CORRECTED (hurtbox study, same day, C): the push volumes are field 30 "bodydata" (4U emd word 8, enemy+0x75cc,
  loader 0x709e0, getter 0x710b0), the same list as the hurtboxes (shape cache 0x16abac and hurt pass 0x16c1bc call
  0x710b0 too; hurtboxes need the hitzone / part fields only bodydata has). Push skips records with +10 & 0x80d2
  (+10 0x80 = hurt only, 0x100 = push only, 0 = both; same meaning in 4U 0xbbea80) and records whose +12 bits slot 220
  (rec+0x3b4) reports. Field 31 "cambodydata" (word 9, +0x75d0, getter 0x710d0) is read only by the quest camera's
  radius-20 sphere (uQuestCamera 0x26934 -> 0x17fa4c -> 0x17f750), falling back to field 30 when empty. The player
  and camera passes skip an enemy whose rec+0x528 is set (0x17caa4, 0x17fabc); the update clears it every frame
  (0xa5334) before slot 168 (0xae1f4). 4U Dalamadur never writes the twin W+0x55a (C).
- The strip measurement below used word 9 (the camera list), not the push list: the push on a rider is S only.
  Measured (word 9, head 34 capsules, tail 19, radius up to 800; FK of motions 1 / 101): walk-strip vertices sit
  inside them by up to 340 (chest j4 14 / 73 vertices, junction j140 7 / 14, j1, j3, head j5). C. Ahtal-Neset ships an
  empty cambodydata (em087_00 / em088_00: 0 records), so the camera sphere ignores it. Port until 2026-10-24 (removed
  2026-10-25, section 6c): dala_walk.c walk_push set rec+0x528 on both halves while
  the LOCAL hunter's ground contact (hunter+0x2f00: +0x100 found, +0x10+8 handle, +0x10+0x34 SBC; S) is a walk
  piece, plus 45 frames. G against 4U's own rule (not traced).
- 4U strip query (C, 0x681e44 -> 0x681c84 -> 0x5a4680): vertical segment from y+50 (x [global+0x5c]) down to y-30
  off the monster, y-60 on it in state 0xd04fbc, else y-120, y-300 for em024 / em083 only; hit = point inside the
  triangle's XZ projection, down normals flipped (two-sided), highest hit wins. No slope limit, no walls.
- GU ground probe 0x4f57f0: type mask 1, owner = the hunter, +-30 (+-300 in one state, 0x29c278). GU's step-up /
  slope rule for sCollision ground not found. Data hint that it is stricter: GU walkable g files are <= 40 deg at rest
  (em084 / em087 / em012), stage g files 98 % under 50 deg. C (data)
- Ours in motions 1 / 101: back 20-45 deg, chest / neck 35-55, flanks 60-90. Seams (step from one piece's open edge
  onto the next): tail 140|141|142 <= 35; head 1->2 and 3->4 p90 ~90-300; tail 140 -> head 1 median +105 up, p90
  +393. The junction is an overlap (3D gap median ~45). Modes 1 / 2 have 103 / 86 of 135 triangles facing down, but
  walking is off when mode != 0 (C). No geometry change until GU's tolerance is known.
- uQuestCamera tests sCollision with type mask 3 (0x26934 -> 0x183724 -> 0xc17aa0), so it sees our type-1 ground
  like em087's. C

## 6c. 2026-10-25 rework (user: junction back / tail not walkable, no invisible wall, camera stuck, head passable)
- Body data bug (C): tools/emdata4u.py zeroed bytes 42..43 of every 4U body record = the high half of off2.z (a
  float at +40 in both games: GU Rathian em001_00 record 4 = 4U's (0, 10, -215)). Every capsule's far end fell to
  z ~0: the head's records 0..6 (off2.z 525..1350 along the snout) shrank to the head joint (no head hits, hunters
  walked through it), the walls 57..60 / tail 23 moved. Fixed; Gogmazios' em089 has 24 / 53 such records (its arc
  picks the fix up when rebuilt).
- Push left on while walking, as 4U (C): 4U's player pass 0xbbe688 -> 0xbbf4d8 gates on the local player
  (0xd04fbc), W+0x55a and the area only; sphere = feet + 50, radius 50 (GU 0x17cf40 the same), horizontal unless
  player +0x370 == 2; GU keeps only x / z of the hunter's push (0x17d548..0x17d5a8). The +12 bit 0x400 records
  (head 57..60, tail 23; push only, active only while walkable) are 4U's invisible walls at the ends of the walk.
  The rec+0x528 rule (dala_walk.c until 2026-10-24) removed them and the head's volumes.
- Ground: GU's hunter ground function 0x2e846c (stage_cart.c notes): ray 0x18192c, the highest hit up to y + 100;
  a grounded hunter > 30 above it goes airborne (0x2e86fc). Hook dala_ground at 0x2e85ac (r0 hit, r1 ground y, r4
  hunter): 4U's strip query over both halves' active pieces ([y - 400, y + 100], highest, two-sided, no slope limit)
  wins when GU found nothing or lower ground; a grounded hunter on the body last frame follows it down up to 150 a
  frame. Test 2026-10-24 17:22: walking j1 -> tail, the feet followed j140's height (y 1985 at z -442) but GU's
  contact never named j140 (no tail push-off), so the tail's volumes shoved him off; with push on and the ground
  rule this no longer depends on the contact handle.
- Camera: hooks dala_cam_begin / dala_cam_end at the camera step's entry 0x26934 and only exit 0x26e34 switch the
  walk pieces off for its stage sweep. 4U's camera tests only the monsters' word-9 bodies (0xc02444 -> 0xbbe810 ->
  0xbbfc1c mode 1, no em exception, C); its strips are not stage collision.

## 6d. 2026-10-25 second pass (test 15:58: junction and camera still failing)
- Junction, FK with the 4U keys decoded (LMT key types 4 / 6 / 7 C: type 6 = x, y, z, w 14-bit at bits 42 / 28 /
  14 / 0, / 4096, frames >> 56; types 4 / 7 = bounds {mult[4], add[4]}): motions 2 / 102 frames 560..600 and bank 3's
  1 / 101 frames 240..290 put j140 20..100 above j141 over j141's last 300 (x -2600..-2200), then j140 alone
  rising to j1, which takes over 30 lower: walkable with a +100 window. The log shows the hunter's feet on j141's
  level up to its end (z -300) and off below j140 there, both attempts. The "walk contact" lines logged the
  hunter's joint 0 (hip, ~90 above the feet): GU's j141 matched the strips. GU's contact flipped j141 / none every
  1..2 frames: the hunter was airborne half the time, so neither GU's ground nor ours lifted him onto j140 (an
  airborne hunter lands only while falling, 0x2e8658).
- Cause (S, C mechanism): colMove with flag 0 and a changed matrix files the entry in GU's moving tree, the only one
  the carry probe 0x4f57f0 searches; GU's carry moves the hunter by the entry's old -> new matrix only when its sweep
  is not blocked (0x4f594c -> 0xc3eb0c), else he stays while the ground slides (Gogmazios' stage_cart.c, logs
  2026-10-23/24). The static j140 (its key holds 255 frames) stayed in the still tree: GU's contact never named it.
- Fix: flag 1 (still, teleported each frame) for every piece, as the cart: no carry, the ground query (still and
  moving trees) still finds the pieces; height = 4U's rule (dala_ground_c). The walk logs now report our own query
  (piece changes, leaving the body, a trace while j140 lies over or under the hunter: "walk trace").
- Camera: the camera's monster pass (0x17fa4c -> 0x17f750) pushes its radius-20 sphere out of cambodydata (4U word
  9, always on: +10 = 0, +12 = 0 but two head records); standing on the back the camera sits inside those capsules.
  It skips an enemy whose rec+0x528 is set (0x17fabc): set on both halves for the camera step only (dala_cam_begin /
  end), while the local hunter was on the body within 60 frames, restored after (the player push keeps its walls).

## 6e. 2026-10-25 third pass (test 17:27: junction walkable, no ledge jump off its side; camera still stuck)
- 4U window (C, 0x681e44 -> 0x6821a0..0x682300, floats 0x682210..0x68222c = 0, 1, -60, -300, -120, -30, 50, -80):
  top y + 50 g; bottom y - 30 - 50 g when the player was not on the monster last frame (+0x9a8), y - 60 - 50 g for the
  local player on it (0xd04fbc = "is the local player", C), y - 300 - 50 g for a remote player on em024 / em083
  (-120 on other monsters); g = [sMain+0x5c] (below 1: top + 50, bottom - 80). A hit there above the player's stage
  ground (+0x468) sets his position (0x6822c8); none -> +0x9a8 = 0 and his ground is the stage's. Corrects 6b / 6c:
  the -300 is the remote players' window, the local one is -60 - 50 g.
- GU airborne choice (C, 0x2e86d0..0x2e8af8): a grounded hunter > 30 above r1 -> air state 2 (vt+0x300), then by
  state; default: flags +0x2510 high word & 24 (moving) and a drop <= 300 -> 0x2a01d8 (fall without an action: vy -12,
  gravity -0.227), else action 4/1 (S: the ledge jump). Off j140's 83 deg side GU's ray saw the side 100..300 below:
  plain fall, no wall grab (user). The landing test 0x2e88e4 and its store 0x2e8908 read the ray's slot [sp+0x1c]
  (r5), not r1.
- Port: dala_ground_pre (0x2e8590) switches the pieces off for every hunter's ray; dala_ground (0x2e85ac) puts them
  back and applies 4U's window: the local hunter's per 4U frame (his heights over the last 2 time units of
  hunter+0x1c, C 0x2e9a54), remote hunters' per call (300); a hit -> r0 / r1 / [sp+0x1c] = h and a grounded hunter more
  than 30 above it is set to it. GU's ground function is a virtual of every hunter class (vtables 0x1749524..), so it
  should run for remote hunters too (S; LDN test: "walk ground remote hunter" lines).
- Camera tilt (C): 0x238e0 (called from 0x23720 / 0x24e78) casts every 4 frames a type-1 ray (0x182f70) from y + 100
  to y - 3000 under the hunter, normal -> cam+0xa40, pitch along the view -> cam+0xa54; reset when 0x2a80e8(player)
  or (cam+0x438 and airborne). 0x23d80: k = (8192 - min(|cam+0x9e0|, 8192)) / 8192 when player flags +0x2510 bit 0
  and cam+0xa30 = 0, else 1; cam+0xa5c eases toward k T; pitch cam+0x9d8 = cam+0xa5c + cam+0x9e0. At T = 45 deg the
  stick no longer moves the pitch. The ray met the walk pieces (S: the stuck camera); hooks 0x238e0 / 0x23938 switch
  them off for it. The second ray 0x25f08 (type 2, only with cam+0x438) cannot see type-1 pieces. The rec+0x528
  camera-body skip of 6d is removed (not 4U's: its camera pushes out of the camera bodies too, C).

## 7. Open
- What em084 motion 833 is in game (S: a down / lying state) and why its placement is a one-shot.
- The 0xc4754c flag (1 = still / teleport, 0 = continuous: Gogmazios' stage_cart.c) and em087 piece modes
  (0x16aa288 col 3).
- Camera on the back: the terrain-tilt ray (6e) is the S cause; to confirm in game ("cam tilt" log lines).
- File IDs for new SBC files: 0x152960 rejects IDs > 0x106cf (registry.md); a port must hook it or look the
  resource up by path hash itself (sResource vt[0x38/4](mgr, ?, ~crc32(path), DTI rCollision)). G (design)
