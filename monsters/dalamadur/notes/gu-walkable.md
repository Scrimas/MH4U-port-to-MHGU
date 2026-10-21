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
  +0x60 = a5; inserts the bbox into a dynamic BVH (0xc98880, sCol+0xd8 + 64 * tree). With a6 = 0 an entry that
  already holds the same resource is returned instead of a new one (loop 0xc19970). C (field names from the DTI
  list, S)

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

## 7. Open
- What em084 motion 833 is in game (S: a down / lying state) and why its placement is a one-shot.
- The 0xc4754c flag and em087 piece modes (0x16aa288 col 3).
- File IDs for new SBC files: 0x152960 rejects IDs > 0x106cf (registry.md); a port must hook it or look the
  resource up by path hash itself (sResource vt[0x38/4](mgr, ?, ~crc32(path), DTI rCollision)). G (design)
