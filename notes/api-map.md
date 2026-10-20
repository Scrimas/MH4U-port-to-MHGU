# MH4U -> MHGU mapping layer for the uEm089 port (static RE, 2026-10-17)

4U = MH4U v1.1 code.bin addresses; GU = MHGU 1.4 main offsets (runtime = 0x704000 + offset).
**C** = confirmed in code (structure/fields checked), **S** = strong (call-sequence alignment, >= 4 consistent
votes), **W** = weak candidate. Tools: `tools/apimap.py` (Rathian constant-argument signatures),
`tools/apialign.py` / `tools/apialign2.py` (anchor pairing + LCS alignment of call sequences, pooled over the
31 monsters present in both games -> `dump/apimap2.pkl`, 122 mappings), `tools/fieldmap.py` (record-offset
co-occurrence over 1100+ paired functions -> `dump/em089/fieldmap.txt`).
Coverage: the mapped callees account for **85% of em089's 1370 external calls** (58 of 111 distinct callees);
full table in the appendix.

## Answers first

### Q3: why a Rathian clone at index 137 roars/flinches but never attacks (C)
Not a registry table: the clone runs Rathian's class code `uEm001_00`, which is shared by IDs 0x01/0x201/0x401
(Rathian) and 0x02/0x202/0x402 (Rathalos) and **selects attack data by em number** (`this+0xb5f4`: 1 = Rathian,
2 = Rathalos) with no default for anything else. With em number 89 (ID 0x59):
- `0xcf71ac` (in 0xcf6c70): em 1 -> motion ids 0x40c..0x40f, em 2 -> 0x41f..0x422, **else all four = 0**.
- `0xcff304`, `0xcff380` (in 0xcfd8e0, called from 0xcf45d8): em 1 -> setMotion 0x414 / 0x415, em 2 -> the
  Rathalos motions, **else setMotion is skipped** (jump to 0xcff3ec).
- Slot 86 `0xd0ca90` (setup): only em 1/2 (by variant 0/2/4) initialise the class fields `this+0xcac4..0xcacc`;
  otherwise they keep the ctor default 0x19d.
- 147 sites in uEm001_00 test em number (67) or variant (+0xb5f5, 80); most only add variant behaviour.
Roar and flinch are engine reactions: framework handlers (0x9a7b8.., 0x9b2bc.., 0x9b5ac..) start category-10
actions through the setAction wrapper 0x76afc without looking at the em number.
=> For a clone test give it em number 1: e.g. after setup 0x6fb14 set `this+0xb5f4 = 1` for the clone only
(side effects: Rathian sound table and hunting-log bits). The real port is unaffected: uEm089 has its own code.

Other per-index data found on the way (not the attack cause, but entries are missing for index 137):
- **Resident `enemy\area_act_tbl\enemy`** (rAreaActTblData, `nativeNX/loc/arc/resident.arc`, 137 x 44-byte
  entries, sEnemy+0x2590): enemy init 0x70c5c calls `0x69c258(tbl, this+0xb5f6)`, which returns 0 for index
  >= 137 (count check), so `this+0x7628` (entry) = 0 and `this+0x7630` (area type byte = entry+0xc) is never set.
  Entries list area-move action numbers 0xba..0xc5 (= 4U category-10 actions 187..197); Nakarkos/Ahtal-Ka/
  Valstrax (133-136) are all-zero. Effect: the monster never picks area moves (map-point searches 0xb29bc..0xb6e50
  test `1 << this+0x7630`). Fix: give index 137 an entry (resident.arc mod, or hook 0x69c258 / patch 0x70c88 to
  return an existing entry such as Rathian's, index 0, or a module-built one).
- Resident tables NOT keyed by monster: em_nando_tbl (141 rows = quest difficulty levels), em_resident_dtbase
  (small monsters only, `tst id, #0x1000`), em_size_scale_data (searched by index with default 1.0, see registry).
- uFestaEnemy framework switches on em number (0x22414.., 0xb1d1c queries, 0xb88f8, 0x6f3a4 bitmask 58..88,
  sSoundControl 0x4ed8b0 `> 88` skip): em 89 takes the default branch everywhere.

### Q4: distorted map icon (C)
`cUIOQuestMapIcon` 0x61a994: `size_class = table[em number]` with **table 0x1635354 = 89 u32 entries
(em 0..88)**, no bound: em 89 reads 55133 (next data), the size switch at 0x61aacc (`class - 7`, cases 7..24)
takes the default. Size classes: Rathian 7, Kushala/Chameleos/Teostra/Fatalis 18, Tigrex 7, Nakarkos 26/27,
-1 = none. Only reference: GOT data word **0x183fff0** (R_ARM_RELATIVE, addend in place = 0x1635354), used by
`ldr r2, [pc, r2]` at 0x61aac4.
Fix: module copy with 90 entries (`copy[89] = 18`, elder-dragon size) and patch the data word to
`copy_runtime - 0x704000` (same technique as the FILES table word 0x1839618). The em-number-indexed table scan
found no other data table (other em-number uses are bounded switches). Icon picture: ICON table 0x162e7f8
(registry) is used by quest board/result/MonNyan UIs, not by the quest map.

## Layout anchors (C)
| | MH4U | MHGU |
|---|---|---|
| enemy record (embedded) | `W = this+0xe30`, pointer `[this+0xe28]` (uEnemy ctor 0x956024) | `rec = this+0x1440`, pointer `[this+0x1428]` (ctor 0x6d8ec) |
| monster work pointer | `[this+0x8d88]` = W (em089 ctor 0x8ca0ec) | `[this+0xcac0]` = rec + 96 |
| motion controller | `this+576` | `this+1200` (`this+0x4b0`) |
| current motion id | `[this+576]+4` (0x90f994) | `this+0x4b4` (0xb0a00) |
| setAction | **0x90efac**(this, cat, num, mode) | **0x76154**(this, cat, num, mode) (both test mode==1 first) |
| action dispatcher | vtable slot 44 on W+0x1ca / +0x1cb | vtable slot 125 on this+0x73e0 / +0x73e1 (caller 0xa5c40) |
| action remap hook | slot 46 (byte* cat, byte* num) | slot 127 (`vt+0x1fc`, called by setAction until stable), then slot 128 |
| EMC (rEnemyCmd) | 23 groups | **21 groups** (same version 0x20120804; groups 0..20 align 1:1 in Rathian, 4U groups 21/22 are empty in em001 and em089 -> drop them) |

## Q3 (engine): how actions run in GU vs 4U (C unless noted)
- 4U: EMC opcode `00 cat num` (interpreted by shared uEnemy code) -> 0x90efac -> W+0x1ca/+0x1cb; slot 44
  dispatches every frame; handlers step on W+0x144 and end via `vcall [vt+0x164]`.
- GU: setAction 0x76154 (15 wrappers 0x752ec..0x76afc; 0x752ec/0x76984 are used ~750x by monster code, 0x76afc
  by engine reactions, 0x75510/0x76a10 by network replay) writes this+0x73e0 = cat, +0x73e1 = num,
  +0x73e2/+0x73e3 = previous pair, +0x73e8 (u16) = action serial (0x496f0), clears rec+0x1a1..0x1a3 (step bytes),
  lets the monster remap the request through slot 127. The per-frame update 0xa5c40 calls slot 125, the
  monster's dispatcher (Rathian: jump table on 0x73e0, 18 categories, sub-switches on 0x73e1).
- A monster "declares" its native actions only through its slot-125 dispatcher (switch on cat/num) and the
  slot-127 remap; categories the monster does not handle fall to the uFestaEnemy base (slot 125 base returns 0).
- rEnemyCmd (GU DTI 0x1851cb8; class methods 0x51e24..0x523bc; loader 0x4bac8 via FILES field 37, delivered by
  the member-function callback at this+0x76f0 = setter 0x70a5c -> **this+0x75f4**): parsed into 21 group
  pointers at +0x68. **The AI is 0x82ddc (think, per frame from 0xa59fc when this+0x72f0 = think requested)
  -> selector 0x82f80**, reading the groups through this+0x72f4 = [this+0x75f4] + 0x68 (C, see notes/port.md).
- Action end (C): slot 247 (0x75224) / 248 / 249 / 250 = setAction(0, n, mode 2) + `0x82510(this, 0)` (this+0x72f0
  = 1). Death (12/255) is run by the framework (0xa5c40 -> 0xa6bb8), never by slot 125. Details: notes/port.md.
- Port consequence: em089's EMC can be loaded as cmdtbl after truncating to 21 groups; em089's native
  (cat, num) handlers go into our slot 125 (4U categories map 1:1 onto the GU category byte - GU has 18 categories,
  4U 14; check the category numbering against Rathian before relying on it).

## Q2: enemy record fields used by em089 (4U W offset -> GU rec offset; GU this offset = rec + 0x1440)
| 4U W+ | meaning | GU rec+ (this+) | conf | evidence |
|---|---|---|---|---|
| 0x1ca | action category | 0x5fa0 (0x73e0) | C | dispatchers + setAction |
| 0x1cb | action number | 0x5fa1 (0x73e1) | C | same |
| 0x1cc / 0x1cd | previous category / number | 0x5fa2 / 0x5fa3 (0x73e2/3) | C | both setActions copy cur -> prev |
| 0x1cf | (cleared by setAction) | 0x5fa5 (0x73e5) | S | same position in both setActions |
| 0x1d2 (u16) | action serial | 0x5fa8 (0x73e8) | S | setAction stores u16; co-occurrence |
| 0x144 / 0x145 / 0x146 | action step bytes | 0x1a1 / 0x1a2 / 0x1a3 | C | GU setAction clears 0x1a1..0x1a3; 734/939 pairs for 0x144 |
| 0x1c8 | state class | 0x1ba | S | lift top (8/21), same -0xe shift as 0x1c9 |
| 0x1c9 | mode flag | 0x1bb | S | 11/66, -0xe shift |
| 0x1d9 | (byte) | 0x5fe0 | S | 88/115 pairs |
| 0x14c | (byte, compared with global +0xc90) | ? (0x5fb2 W) | W | sparse |
| 0x1c0 | species/table index byte | ? | W | dominated by common fields |
| 0x78bd | attack id byte (0x9162f8) | 0x6143 (this+0x7583) | C | setter 0xb1a14 identical shape |
| 0xb00 | (byte) | 0x990 | S | 35/62 |
| 0xda (via +0x8d88) | net-sync state byte (slots 78/79) | work+0x24 = rec+0x84 (slots 171/172) | C | enemy-class slot map |
| 0x370 / 0x374 | HP / max HP | 0x370 / 0x374 | C | both read in damage code (4U em089 data, GU 0x9a7b8) |
| 440 / 444 (f) | speed factors (0x911cb4) | 428 / 432 | C | getter pair 0x911cb4 / 0xbe5d4 |
| table rows (+i*6) at 0x94741c | per-index rank bytes | +0x3bc + i*12 (0x9d428) | C | getter pair |
| 0xf0..0x104 (f), 0xf8/0xfc (w) | parts / position vectors | not resolved | W | GU candidates in fieldmap.txt (0xb68c ...) |
| 0x7a14, 0x7a20 (w/f) | em089 tar/target vector area | 0x5cfc? | W | 4/7 pairs |
Rule of thumb from the confirmed rows: fields moved in blocks (0x1c8.. -0xe, 0x1ca.. +0x5dd6, 0x144.. +0x5d),
so every remaining field needs its own evidence; `fieldmap.py map OFF` gives candidates.

## Q1: framework API (most-called em089 callees)
| 4U | calls | GU | conf | signature / role |
|---|---|---|---|---|
| 0x91ab1c -> 0xb06b9c | 400 | 0xb0a24 -> 0x727d0 | C | `bool motionCheck(this, kind, x, s0 frame)`; identical thunk `mov r3,r2; mov r2,#0; b` |
| 0x94e350 -> 0x9190c4 | 87 / 8 | 0xaff40 -> 0xafda4 | C | `setMotion(this, mot, s0 speed, s1 blend)` / `setMotionEx(this, mot, flags, s0, s1)`; motion ids identical (Rathian 123/179 constants shared) |
| 0x910c6c | 89 | 0xc24d8 | S | turn/setMotion-with-target (mot, r2) |
| 0xb05df4 | 75 | 0xb0a84 | C | `bool isMotionEnd(this)` (motion ctrl +6 bit 2) |
| 0x9167ec | 72 | 0xbc8b0 | C | `setTargetMode(this, mode)` (103/106 constants shared) |
| 0x914dfc -> 0x933144 | 55 / 34 | 0x7df94 -> 0x7dc2c | C | `attack(this, slot, index)` -> `attackEx(this, slot, index, param)`: slot 0/1 = 152-byte attack slot, index = attackdata entry |
| 0xb0709c | 8 | 0x72128 | C | `timerDown(this, float *t, scale)` -> 1 when t <= 0 (t -= speed * scale) |
| vt+0x164 (slot 89) | 42 | slot 247 (vt+0x3dc) | C | end action -> AI think (see notes/port.md) |
| 0x9197c0 | 48 | ? (0x701a8 W) | - | 4U base handler for category-10 numbers (em089 tail-branches); in GU let unhandled categories fall to the base |
| 0x9162f8 -> 0x9347cc | 47 | 0xb1a14 -> 0xb18f8 | C | `setAttackId(this, id)`: byte store, 255 = none |
| 0x94ef9c | 25 | 0x76984 | C | setAction wrapper `(this, cat, num)`: reads the current category, then 0x90efac / 0x76154 (em089 chains its own next actions with it) |
| 0x935ac8 | 4 | 0x752ec | C | setAction wrapper (returns early when current category == 11, same test in both) |
| 0x568c8c | 24 | 0x13efd70 (PLT import) | S | atan2 -> u16 angle (GU imports libm) |
| 0x911cb4 | 21 | 0xbe5d4 | C | speed factor rec+428*rec+432 |
| 0x91db84 | 21 | 0x76cc4 | S | root-motion / move helper |
| 0x91150c | 16 | 0x7cab8 | S | rotate toward (flags) |
| 0x91df20 | 14 | 0x712a4 | S | species table lookup |
| 0x94741c | 13 | 0x9d428 | C | rank table byte getter (row size 6 -> 12) |
| 0x91b3f4 / 0x916260 | 12 / 8 | 0x7bdd4 / 0x7b5d4 | S | stop / reset velocity |
| 0x94f440 | 9 | 0xaffac | S | motion helper |
| 0x938620 | 9 | 0x9e994 | S | status flag query |
| 0x90f994 | 8 | 0xb0a00 | C | current motion id |
| 0x92e9d4, 0x92dd04, 0x93093c | 7 each | 0xbca40, 0x78c34, 0xc1708 | S | state / target geometry |
| 0x93d8a8, 0xb054e0, 0x93457c, 0x922c78 | 6 each | 0xbf590, 0xb09e4, 0xaa418, 0xb0870 | S | |
| 0x92dc88, 0x916bcc, 0x936ea8 | 5 each | 0x78b88, 0xc6e14, 0xbab88 | S | |
| 0x9276b4, 0x927730, 0x915d7c, 0x92d0d4 | 4 each | 0xa6d04, 0x82510, 0xbf7d8, 0xc46c8 | S | see appendix |
| 0x6620c4 | 12 | ? | - | posts a 16-byte event (sound/effect request) via 0x660e88; not in Rathian -> pick via another monster |
| 0x636b64 / 0x636b54 | 17 / 6 | ? | - | model slot table set/get (+72 + i*8) |
| 0x93156c, 0x8d3d20, 0xcfba14, 0xc0bd38 | <= 6 | ? | - | em089/em099-only helpers (re-implement) |
Notes: 0x1076cc (allocator for a DTI) = GU 0x7aa47c (C, enemy-class notes). 4U setAction wrappers (callers of
0x90efac) map onto GU wrappers (callers of 0x76154); check the category test when choosing among the 15 GU ones.

## Changes needed in module/ (coordinator)
1. Map icon: table copy (90 x u32 from main 0x1635354, entry 89 = 18) + IPS patch of data word 0x183fff0 to
   `copy_runtime - 0x704000` (needs IPS on the data segment; else hook 0x61a994).
2. Area act: an entry for index 137 (hook 0x69c258: if r1 == 137 return Rathian's entry `0x69c258(tbl, 0)` or a
   module-built entry; for Gogmazios 0 = no area moves is acceptable at first).
3. Clone tests only: em number 1 for the clone object (or real uEm089 code).
4. EMC: write em089's cmdtbl with 21 groups (drop 4U groups 21/22).

## Appendix: em089 callee -> GU (generated from dump/apimap2.pkl)
Full table of all 111 callees: `dump/apimap_table.md` (rebuild: `python3 tools/apialign2.py`, then the table
snippet = for each em089 callee print apimap2 map / votes). "seed" rows were structure-checked, "aligned n/m" rows
are S when n >= 4, "candidate" rows W, "no evidence" rows are mostly single calls into em089/em099-only code.
