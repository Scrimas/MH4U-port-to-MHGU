# Tigerstripe on the Dunes: why it never changes area (static RE, 2026-10-21)

GU = MHGU 1.4 main offsets (scratch/main.asm). C = confirmed in code / data, S = strong (consistent evidence, not
traced to the last instruction), G = guess. EMC listings below use the real instruction lengths (see section 1a).

## Answer first
- **C: 4U em092's command table never starts GU's area move.** GU replaced 4U's script-driven area move with engine
  opcodes 0x94 / 0x95 / 0x9e (setup, start, per-think step). GU em067_00's group-0 selectors use them; em092's (which
  Tigerstripe ships for selectors 0..28) use 4U's opcodes 0x03 / 0x06 (and 0x36 / 0x4d for patrol), which GU's
  interpreter sends to its default handler 0x8470c (no-op). So no next area, no exit point, no transfer is ever
  computed. 4U's per-map cases also test 4U stage ids (4, 17 = 0x11 Dunes day, 18 = 0x12 Dunes night), never GU's 5.
- **S: the loop is the leftover of 4U's area-move scripts, not an ambush:** selector 10 -> s141 -> s140 ends in a
  dive (1/51); underground, selector 8 / 9 starts 6/1; back at state 2, s144 -> s102 / s140 start 6/3 + 7/13 (surface
  plus emerge attack); state 1 -> dive again. 6/8 is set by 1/51's end but replaced in the same frame.
- **Fix (data only, cmdtbl()):** take GU em067_00's group-0 selectors **s0 and s10** (s0 differs from em092's only in
  the area-move branches and a map-14/map-4 case). Zamtrios' own GU move type (3 = walk to the exit, dive, resurface
  in the next area) then runs on the Diablos area files. Optional: give s181's area-move branch a Dunes case (section
  4), else he dives where he stands after a 210-frame timeout instead of walking to the exit.

## 1. How GU moves a monster to another area

### 1a. EMC instruction lengths (C)
Table 0x1732c8c (167 bytes, decoder 0x50c64 / 0x50ce0). Byte < 0x80 = number of argument bytes. 0x8n = block op:
`XX 00 <n args>` IF / switch, `XX 01 v` CASE (1-byte value; 0x9n 2, 0xAn 3, 0xBn 4 bytes), `XX 02` ELSE, `XX ff` END.
Examples: 0x00 2 (`00 cat num`), 0x01 4, 0x06 2, 0x14 1 (call script), 0x20 1 (goto selector), 0x94 2, 0x95 2, 0x96 2,
0x97 1, 0x9e 2; 0x6f 0x81 (`6f 00 id`), 0x2a / 0x07 / 0x3f / 0x54 / 0x61 / 0x9c 0x80. Script end = 0xff (> 166).
Opcode handlers: jump table 0x837ac (256 entries); 101 opcodes go to 0x8470c = `return 0` (no-op), among them
**0x03, 0x06, 0x36, 0x4d** (C).

### 1b. Conditions used (C)
| op | true when | handler |
|---|---|---|
| 0x2a | switch on the current stage number (cases: GU 0x0e = map 14; em092 uses 4U ids 0x04 / 0x11 / 0x12) | S |
| 0x07 | switch on the current area (this+0x1054) | S |
| 0x3f | this+0x73f3 != 0 (area move requested) | 0x87bfc |
| 0x54 | this+0x73f4 != 0 (area move set up) | 0x88cd8 |
| 0x61 | this+0x73f0 != 0 (area move running) | 0x88ff0 |
| 0x9c | rec+0x2c0 == 1 or this+0xba44 & 2 (bit 1 set by 0x8f004 = during an area move) | 0x8cd1c |
| 0x6f n | monster slot 133 (vt+0x214) id n; id 1 = Zamtrios ground state (1 surface, 2 / 3 underground) | S |

### 1c. The GU sequence (C unless tagged)
1. Request: this+0x73f3 != 0. The writer of 1 was not found by pattern search (G: the area-stay timer 0xb8044,
   this+0x73fc reset to 1800, roll from per-map data this+0x7624). Cleared by 0x8a690 (op95), 0x95ca0 (finish),
   0x82dac (via 0xb31a0), 0xb5d6c (arrival), 0xb7584 (statusReset).
2. Think -> group 0 s0: `3f IF -> 20 0a` = goto selector 10 (same in GU and em092).
3. GU selector 10 = `94 00 00` `95 00 00`:
   - op 0x94 (148) = **0x8f004 setup**: this+0x73f0 = 1, ba44 |= 2; next area = this+0x73f6 if forced, else
     0xb31a0(this, area 0x1054) = area_select (Next / Rand rows, BackArea), 255 = fail (this+0x1404 bit 23); this+0x73f4
     = 1; **move type** this+0xba4e = area_act_tbl entry +8..+0xb [normal main, dying main, normal sub, dying sub]
     (index from 0x817a4 dying and 0xb317c sub-route), then monster slot 227 (vt+0x38c) may override it; if the current
     area is a ceiling area (resident area_link record +6 = mCeilingArea, via this+0x762c) type 6 -> 5 and 0 -> 1;
     exit point 0xb3640 -> this+0xb9e0; route 0xb4b10.
   - op 0x95 (149) = 0x8a690: phase reset, then the first step 0x8d418.
4. Each later think: s0 `61 IF -> 9e 00 00` = op 0x9e (158) -> **0x8d418**, jump table on the move type (0x8d440):
   0 0x95abc/0x96374, 1 0x96374, 2 0x8f460, **3 0x8fb90**, **4 0x8fce4**, 5 0x9089c, 6 0x90b4c, 7 0x90f18, 8 0x915ec,
   **9 0x918d0**, 128..140 more.
5. **Type 3 (Zamtrios normal), 0x8fb90**, phase this+0xba50:
   - 0: if 0x97130 (route follower: walks waypoints 0xb50f0, returns 1 at the exit) or (controlled and this+0xba28 >
     210.0): synthesize the script `14 <0xb4e58(this, 4)> ff ff ff` at this+0xba34 (group 2), i.e. **call the kind-4
     "dive" script** (Zamtrios s184 = `ACT 1/51`); phase 64.
   - 64 (0x96208): **0xb3e4c**(this, area, next, rec+0x40, &yaw) = entry point in the next area -> position + rec+0x54;
     **0xb5d6c(this, 0) = the area transfer** (writes this+0x1054 at 0xb5e04, clears 0x73f3/f4/f5, sets the stay timer
     1800); then the kind-5 "surface" script (Zamtrios s186 = `14 66` -> s102: state 2 -> `6/3, 7/13`); phase 65.
   - 65: 0x95ca0 finish (clears 0x73f0 / 0x73f3 / 0x73f4 / ba50).
   Type 4 (Zamtrios dying, 0x8fce4) uses kinds 4 and 6 (dive, then underground travel: s185 = `6/13, 6/12`). Type 9
   (Diablos) 0x918d0 uses kinds 4, 5, 6 (burrow and travel underground).
6. Walking during the move: the think entry 0x8282c, when this+0x1408 bit 7 is set, runs the kind-1 "move" script
   (0xb4e58(this, 1); Zamtrios s181) toward this+0xba60 copied into the target slot rec+0x1d0 (S: 0x97130 feeds it).

### 1d. Data read (C for the reads, S for the field roles)
| data | where | use |
|---|---|---|
| resident `enemy\area_act_tbl\enemy` (AAT, 137 x 44 B), entry = this+0x7628 | 0x69c258 at 0x70c88 | script per kind (file +0..+31 = object +0x14 + kind), move types (file +32..+35), **Group** (file +36 = object +0xc = this+0x7630), meal ActNo (+37), Flag (+38), mouth distance (+40, float) |
| per-monster area files, fields 40..44 | setter 0x70d20 -> this+0x7634 / 0x7638 / 0x763c / 0x7640 / 0x7644 (S: area_link / area_eat / map_info / area_select / area_patrol in field order) | next area (0xb31a0), exit / entry points |
| resident `enemy\area_link\enemy` (XFS: mMapNo, mKind, A01..A12 rows, mCeilingArea) | this+0x762c = 0x69d9e8(sEnemy+0x258c, map) | ceiling areas (map 5: areas 5, 6, 8, 9) |
| stage route data | 0x4ff9c0 stage -> +0x68; point record +0x30 mask tested with `1 << this+0x7630` (0xb37fc..0xb3828), +0x28 flag bit 4 for some move types | exit point / route |

AAT property names (0x69c4e0, object offsets): 0x14 wait, 0x15 move, 0x16 sleep, 0x17 map-meat eating, 0x18 dive (into
the ground), 0x19 dive (to the surface), 0x1a dive move, 0x1b fly up, 0x1c land, 0x1d fly move, 0x1e move and vanish,
0x1f..0x22 special 0..3, 0x23 / 0x24 jump up / down, 0x25 predation demo, 0x26 / 0x27 vine up / down, 0x28 / 0x29 hover
up / down, 0x2a / 0x2b ground <-> ceiling, 0x2c in-area flight, 0x2d wall to ground.
Entries: Zamtrios (index 56) scripts b4 b5 b6 b7 b8 ba b9 .. bb (wait 180, move 181, sleep 182, meat 183, dive 184,
surface 186, dive move 185, predation 187), move types **3 / 4 / 3 / 4**, Group **0**, meal 0x13, 600.0. Diablos (114 /
115): 79..7f, types **9 / 9 / 9 / 9**, Group 14, 500.0.

### 1e. What makes a GU area move fail
- No area_select entry for (map, area) or all Next = 255 -> 0x8f004 fail path (this+0x1404 bit 23).
- No exit point whose mask has bit Group (this+0x7630) -> 0xb3640 falls back (S).
- A command table whose selectors do not issue 0x94 / 0x9e: nothing is computed (Tigerstripe's case).
Dunes point masks (stage `_point_pos\map05`, 32-B records, last u32) are mostly 0x3fffff / 0x4bfffff / 0xffffffff: bit 0
(Zamtrios' Group) is set on most points (C for the values, S that this u32 is the +0x30 mask).

## 2. The observed loop (variant 1, Dunes, Diablos' area files)
| step | what runs | conf |
|---|---|---|
| request | the stay logic sets 0x73f3 (with Zamtrios' files: no map-5 data -> never set, "never attempted"; with Diablos': set) | S |
| 1/51 (0x447, 3.7 s) | s0 `3f` -> **em092 selector 10** (4U routing: `2a` cases 0x04 / 0x11 / 0x12, op 0x03 = no-op) -> `CALL s141` -> `CALL s140` (4U Dunes cases are 0x11 / 0x12, none match 5) -> tail `6f 01: CASE 01 -> ACT 1/51`; s141's `06 ff 00` = no-op | C (scripts, no-ops), S (path) |
| 6/8 | 1/51's handler 0xf6becc ends with setTargetMode(4) + **setActionW(6, 8)** + think request (0xf6c02c..0xf6c054); the same-frame think replaces it, so the per-frame logger never sees it | C (code), S (same frame) |
| 6/1 (0x415, 3.3 s) | underground state 3: s0 -> `20 08` (combat) or `20 09` (not), em092 selectors 8 / 9 = `ACT 6/1`; 6/1 (0xf711a4) ends through slot 250 | S |
| 6/3 + 7/13 (0x416 1.3 s, 0x414 5.8 s) | state 2: s144 -> `CALL s102` (non-combat path) or s140's head `6f 01: CASE 02 -> 6/3, 7/13` = surface + emerge attack | S |
| back to 1/51 | state 1 + request still set -> selector 10 -> s140 tail again | S |

"6/1 ends after one frame" (log 08:52): motion 0x415 was missing (logged as ffff), so isMotionEnd held at once; fixed
by afae983 (log 09:04: 6/1 plays 3.3 s). One later 6/1 at 04:52 also ended at once, followed by combat (2/29): an
interrupt (G).
Not an ambush: the dive comes from 4U's area-move script s140; nothing in the loop is GU's area move (no 0x94 / 0x9e),
so the transfer 0xb5d6c never runs and this+0x1054 never changes.
Nothing stage-specific is missing for the GU path: no water / swim points or special mask are needed for move type 3
(dive kind 4 and surface kind 5 are plain scripts, Group 0 is set on the Dunes points). GU em067_00's own s140 even
has a map-5 case (dead code in GU), so the 4U design included the Dunes.

## 3. Differences between em092's and GU em067_00's group 0 (C)
- s0: GU `61 IF -> 9e 00 00`, em092 `61 IF -> CALL s141`; GU `54 IF ->` (empty), em092 `54 IF -> CALL s141`; s112
  special for map 0x0e (GU) vs 0x04 (em092). Nothing else.
- s10: GU `94 00 00 95 00 00`; em092 = 4U routing table (`40`, `2a`, `07`, `22`, `4a`, op 0x03) + `CALL s141`.
- s1 / s3 / s9: GU patrol `4e` / `96 00 00` / `97 00`; em092 map-4 cases with 0x36 / 0x4d (no-ops), s1 else `CALL s150`
  (works: the 2/29 / 2/27 patrol in the log), s9 = state 3 -> 6/1.
- s2, s4, s16..s28 differ too (combat, 4U map 4 cases): not area related.
Kind scripts 180..187 (appended from GU) and s102 are identical to GU's; s140 / s141 / s144 / s145 are 4U's.

## 4. Fix
1. **cmdtbl() (build_em067_01_arc.py): replace em092's g0 s0 and g0 s10 by GU em067_00's** (or patch s0's two
   branches only: `61 IF` body -> `9e 00 00`, `54 IF` body -> empty, and s10 -> `94 00 00 95 00 00 ff`). Expected
   in game, normal state: walk toward the exit, `ACT 1/51` dive (em092 motion 0x447) at the exit, transfer to the
   entry point of the next area (Diablos' area_select picks it), surface with `6/3` + `7/13` (0x416 / 0x414). This is
   the dive-out the user remembers (4U em092 s140 also dove in Dunes areas 4 and 10 and walked elsewhere).
2. Walk to the exit (optional, recommended): s181 (kind 1, used while walking) has its area-move branch (`9c IF`) only
   for map 14 (`2a CASE 0e`, per-area); on map 5 it picks no action, so type 3 dives after its 210-frame timeout where
   he stands (S). Data fix in our table: put s181's generic walk (`6f 01` surface cases, then `35 IF -> 2/29 2/33 /
   ELSE -> 2/29 2/27`) into the `2a ELSE` of the `9c` branch (or a `2a CASE 05` copy). GU's own Zamtrios has the same
   gap outside map 14.
3. Keep Diablos' area files (needed by 0xb31a0 and the request). Do not swap area_act_tbl entries: Zamtrios' entry
   (type 3 / 4, Group 0) already gives the dive move; another entry needs a hook on 0x69c258 for variant 1 and its
   kind scripts would not exist in our table.
4. Check before the test (G): dying move type 4 uses kind 6 = s185 `6/13, 6/12`; 6/12 (0xf6fcf4) sets motion
   **0x411**; check em092's bank 4 has 0x411 (and 6/13's motion), else copy them from em022 like 0x415..0x417.
5. Log lines to add for the test: 0x8f004 entry (this+0x73f8 next area, this+0xba4e move type, this+0xb9e0 exit),
   0xb5d6c entry (area before / after), phase this+0xba50 per think.
