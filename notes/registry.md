# MHGU per-monster registry (static RE, MHGU 1.4 main, 2026-10-17)

Addresses are main offsets (runtime = 0x704000 + offset). Helper: tools/gu.py (pc-relative resolver on top of
MHGU_Editor/scratch/py/asm.py); all pc-relative refs cached in dump/gu_pcrefs.pkl.
C = CONFIRMED from code/data, G = GUESS.

## IDs and monster object fields
- ID u16 = (small << 12) | (variant << 8) | em number. Decoder 0x4ecf8(id, &small, &em, &variant) is pure bit ops. C
- Large ems in MHGU: 001..088. New monster: **ID 0x59 (em089 variant 0), index 137**. C
- Monster object: +0xb5f0 u16 ID, +0xb5f4 u8 em number, +0xb5f6 u8 registry index (0x6fb14 stores 0x50b64(id)),
  +0xb5f7 u8 small flag. C

## The index lookup
- 0x50b64(id) -> index, -1 if absent; 0x50bdc(index) -> id, 0xffff if absent (14 callers).
  Both search the (id, index) pair table **0x1597ea4** (137 x 8 B) with an unrolled 2-per-iteration loop
  bounded by `cmp rX, #137` (0x50b94 `e3530089`, 0x50c10 `e3510089`). With 138 entries the loop reads
  entry [138] once -> keep a sentinel pair (0xffffffff, 0xffffffff) after the new entry. C
- Pair-table literal sites (literal = table - (use + 8)):
  | literal @ | used by add @ |
  |---|---|
  | 0x50bd0 | 0x50b74 |
  | 0x50bd4 | 0x50b78 |
  | 0x50bd8 | 0x50bb8 |
  | 0x50c50 | 0x50be8 |
  | 0x50c54 | 0x50bf0 |
  | 0x50c58 | 0x50c34 |
  No other code refs. C

## Static tables indexed by the registry index (no bounds check -> must hold an entry 137)
| table | entries | content | code refs (literal @ -> add/ldr @) |
|---|---|---|---|
| 0x1731e2c DTI | 137 x 4 | class DTI* per index (relocated pointers); factory 0x4ebcc: `dti->vt[2]()` = newInstance, then init 0x6fb14 | lit 0x4ece8 -> add 0x4ebfc (only ref). C |
| 0x1732050 CRO | 137 x 4 | char* "roEmNNN.cro" (virtual module registry, 20 slots, refcounted: acquire 0x3ccff8 / release 0x3cd308 / 0x3cd...; an unknown name gets a new slot via 0x3cce34, no file I/O seen) | 0x4ed10 lit 0x4ed44 -> add 0x4ed34; 0x4ed48 lit 0x4ed94 -> 0x4ed6c; 0x4ed9c lit 0x4ede4 -> 0x4edc0; 0x4edec lit 0x4ee38 -> 0x4ee10. Special id 0x1063 bypasses the table. C (no-file G) |
| 0x1732a68 FILES | 137 x 4 | pointer to a 0xCC-byte manifest: 51 file IDs (-1 = none), field k = resource kind (see below) | ~40 code sites, ALL through ONE GOT slot **0x1839618** (data word, R_ARM_RELATIVE addend in place = 0x1732a68). Patch that word to (copy - 0x704000) to relocate every user. C (IPS on data segment G) |
| 0x159f4dc FLAGS | 137 x 4 | per-monster attribute bitfield (0x440241, 0x404c0201, ...); accessor 0x6b3fc(_, id) (13 callers: sEnemy, every uEm), id 0x1063 -> 0x400c2080; unknown id -> 0 | lit 0x6b43c -> add 0x6b430 (only ref). C (bit meanings G) |
| 0x162e7f8 ICON | 137 x 4 | UI index (0..140; s100 variants share 109): accessor 0x560ca4 (15 callers: uUIMonNyan, cUIOHNMonsterListLow, uUIResult, quest counter...) -> icon/name slot G | lit 0x560cc0 -> add 0x560cb4 (only ref). C |
| 0x159fb3a U16 | 138 x 2, read at [index+1] | u16 2502..2629 (1716 = default); 0xaca40 stores it in rec+0x5d58 (rec = [monster+0x1428]) | lit 0xacba8 -> add 0xacb38. (0xac57c refs 0x159fb31 = a different byte table.) C (meaning G: text/msg id?) |

FILES manifest fields (from em001_00, types = MT DTI hashes; arc em001_00.arc has exactly these types):
0 rModel 0x58a15856, 1 second model, 2 third model (0x4bcd4 picks field 1 or 2), 3 0x7cd0e77e, 4-8 rMotionList
0x76820d81, 11 camera 0x39c52040, 12 0x10ebe843 (sound call), 13 0x1bcc4966 (snd), 14-15 0x4541367c (pts), 16-17
0x5a525c16 (pel), 18-22 0x254309c9 (psl), 25 0x73850d05 (shell arc), 26 attackdata 0x70bb64ba, 28 hitsize 0x5653c1b0,
30-31 bodydata 0x1ac7b52d, 32 dtbase 0x59d9c3da, 33 dttune 0x48e8ac29, 34 dtbparts 0x1bbc291e, 35 0x496f8f22 (some
monsters), 37 cmdtbl 0x3aabba02, 38-39 doumouka 0x1f149aec, 40 area_link 0x4bf84f6f, 41 area_eat 0x56d892d0,
42 map_info 0x197e4d7a, 43 area_select 0x15e98d21, 44 area_patrol 0x0947f3c8, 45 extra motion, 46-50 hagi 0x33a84e14. C
Consumers: 0x4a858 (load, caller 0x7079c), 0x4acc4, 0x4afe4, 0x4b0e0, 0x4b1d8, 0x4b554, 0x4bc2c, 0x4bc5c, 0x4bcd4,
0x4bd24, 0x4be20, 0x4befc, 0x4c124: each `if (manifest[k] != -1) resource = 0x152960(mgr, manifest[k])`. C

## Global file-ID table (needed for the new manifest)
- 0x152960(_, fileId): `if (fileId-1 > 0x106cf) return 0;` entry = 0x15a0ce0[fileId] (8 B: path hash, type DTI hash),
  then `mgr = [[GOT 0x2126a64]]; tail-call mgr->vt[0x38/4](mgr, ?, hash, type)` (find a loaded resource by hash). 692
  callers; the ONLY code ref to 0x15a0ce0 (lit 0x1529a0 -> add 0x15297c). C
- Path hash = ~crc32(path) with the arc-internal path, e.g. ~crc32("enemy\\em001\\em001_00\\mod\\em001_00") =
  0x23cf2b99, ".../mot/em001_00_0" = 0x1bdd7717. C
- File IDs end at 0x106d0; new IDs must be handled by a hook on 0x152960 (both first instructions displaceable:
  `e30026cf movw r2,#0x6cf`, `e2410001 sub r0,r1,#1`) or by relocating the 538 KB table + patching the bound. G (design)

## Arc loading (works for 0x59 without a table)
- Quest spawn prep 0x68a70 (sQuest/aQuest): `if (0x50b64(id) != -1) 0x152c68(mgr, 48, id, 0, ...)`.
- Request kind 48 in builder 0x15339c (jump table 0x153434, case @0x15407c): 0x4ecf8 decode, then
  sprintf "enemy\\em%03d_%02d" (0x155734f) or "enemy\\ems%03d_%02d" (small) after an "arc\\" prefix
  -> romfs `nativeNX/arc/enemy/em089_00.arc` for ID 0x59. C (prefix/concat details G)
- Factory 0x4ebcc(id, serial, r2, r3) (callers 0x5d728 quest spawn, 0xcd624): idx = 0x50b64(id) (-1 -> return 0);
  dti = DTI[idx]; id 88 builds an extra control unit; obj = dti->vt[2](); 0x6fb14(obj, id, ...); added to the move
  line 4 (5 for ids 87 / 76). C

## Index consumers that are SAFE for index 137 (bounds-checked or data-driven)
- Save-side arrays of 137 entries (hunt tallies, captures 0x112 B apart, size records): 0x52308c, 0x523104,
  0x526d94, 0x526dd4, 0x526e00, 0x526e44 (`cmp r0, #136; bhi -> 0`); 0x526eb0/0x526ef8/0x526f48 (runtime count
  check); bitset 0x551dd0 (`cmp #136`). Gogmazios just won't be counted. C
- 0x672a4 / 0x67310 (uEnemy, UI): search a loaded list ([obj+0x2584]+0x64/0x6c, 32-B entries, +4 = index,
  +28 = float), default 1.0 / 0xff when absent. C
- 0x69c258 (from 0x70a6c via +0xb5f6): runtime array, `count at +0x68` checked. C
- 0x5bb24: special-cases indices 105-111, 77-78, 132 only. C
- 0x68a70, 0x3c5b50 (aResult), 0x3c7034 / 0x3c7134 (uUIResult): only test -1 / pass the index on. G (not traced deeper)
- 0x4be20: uses the id for a resource request, no table. C

## Index consumers that are UNSAFE for index 137
- **0x3a75c8** (callers 0x3a6dbc in 0x3a6108, 0x3a82b8 in 0x3a7f40; quest-end statistics): increments u16 at
  `obj + 0x114/0x116 + index*8` with no bound -> index 137 writes 8 bytes past a 137-entry array (0x114..0x55c).
  Hook the entry (`e92d4ff0`, `e24dd064` displaceable) and skip when r1 == 0x59. C (skip return value G)
- **0x3a3930** (caller 0x2626c4, uUIResult): reads the same array (`+index*8 + 0x116 / 0x114`), out of bounds read
  only (returns "hunted" bool). Hook: return 0 for r1 == 0x59. C
- 0x3a5bbc (sQuest): keeps the index in r5 for later use — not traced. G

## Em number used directly (not via the index)
- Shared code bounds em number with 88 and skips otherwise: sSoundControl 0x4ed8b0 (`+0xb5f4 > 88` -> no monster
  BGM/sound table), uUIMonNyan 0x1ac338 / 0x1c95a4 (hunted-at-rank bits, `> 88` -> skip). C
- Nakarkos (87/88) special cases at +0xb5f0 compares (0x20100, 0x1125bd8, 0x1138574, 0x4ebcc) do not match 0x59. C
- 0x5ceb4 = monster-unit slot getter (slot < 10), not ID-keyed. C
- Not yet checked: quest-file monster validation, Hunter's Notes / monster name text (likely ICON or U16 tables),
  guild card monster log (87 entries in the card).

## Recommended minimal patch set to register 0x59 (index 137)
1. Module copies (138 entries + sentinel) of: pairs 0x1597ea4 (+ (0x59, 137), sentinel), DTI 0x1731e2c (+ own DTI),
   CRO 0x1732050 (+ "roEm089.cro" or reuse an existing name), FILES 0x1732a68 (+ own 0xCC manifest), FLAGS
   0x159f4dc (+ flags copied from a comparable elder dragon), ICON 0x162e7f8 (+ existing icon index first), U16
   0x159fb3a (139 x u16, entry [138] = 1716 default). Pointer entries in the copies = 0x704000 + main offset.
2. IPS literal patches: 6 pair-table literals + 2 bounds (0x50b94 `e353008a`, 0x50c10 `e351008a`); 1 DTI literal;
   4 CRO literals; 1 FLAGS literal; 1 ICON literal; 1 U16 literal; FILES: 1 data word (GOT 0x1839618) instead of
   ~40 literals. New literal = (copy_runtime - 0x704000) - (use + 8).
3. Hooks: 0x152960 (file IDs >= our base -> own (hash, type) table, same tail call); 0x3a75c8 and 0x3a3930
   (skip / return 0 for id 0x59).
4. RomFS addition: nativeNX/arc/enemy/em089_00.arc whose internal paths hash to the manifest entries.
