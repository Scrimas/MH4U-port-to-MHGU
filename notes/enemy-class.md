# MHGU enemy class interface (static RE, 2026-10-17)

All addresses are MHGU 1.4 main offsets (runtime = 0x704000 + offset). Tools: `tools/gu_enemy.py`
(`classes`, `slots N`), `tools/slotmap.py` (`em001`, `base`). 4U = MH4U v1.1 code.bin addresses.
CONFIRMED = read in code; GUESS = inferred, needs a check.

## Class chain (CONFIRMED)
`uEmXXX_YY < uFestaEnemy < uEnemy < uEnemyBase < ...`
| class | DTI | size | DTI vtable | newInstance | ctor | object vtable |
|---|---|---|---|---|---|---|
| uEnemyBase | — | 0xb740 | 0x17343a4 | 0x6d8bc | 0x6d8c4? | — |
| uEnemy (abstract) | 0x1852d68 | 0xca80 | 0x1734c18 | 0xacc84 (returns 0) | 0xacc8c | 0x1734798 (286 slots) |
| uFestaEnemy | 0x18533f8 | 0xcac0 | 0x17351c4 | 0xc9ce8 | 0xc9cf0 | **0x1734d44** (286 slots) |
| uEm001_00 (Rathian) | 0x1850f58 | 0xcad0 | 0x1732290 | 0x4c48c | 0xcefe98 | 0x179acf8 |
Monster sizes: 0xcad0..0xcf20 (uEm084_00 0x6320 is an exception); `gu_enemy.py classes` lists all 60.
Static DTI init of the monster classes: 0x4f078 (calls 0x7aedcc in sequence).

## MtDTI (CONFIRMED, ctor 0x7aedcc)
`0x7aedcc(dti, name, parent /*0 = root*/, size, [sp]=id /*0 -> crc32(name) & 0x7fffffff via 0x7cbdb4*/, [sp+4]=attr(3 bits), [sp+8]=flags(6 bits))`
Layout (0x20 bytes): +0 vtable (MtDTI base; the caller stores its own DTI-subclass vtable afterwards: `str [GOT]+8, [dti]`),
+4 name, +8 next sibling, +0xC first child, +0x10 parent, +0x14 hash-bucket next,
+0x18 bits 0-22 = size>>2, bits 23-28 flags, bits 29-31 attr, +0x1C id. Linked into parent's child list and the
hash table bucket [id & 0xff].
DTI vtable (Itanium address point = [GOT]+8): slot 1 = dtor?, **slot 2 = newInstance()**.
newInstance (0x4c48c): `a = 0x7aa47c(heap)` (heap from GOT), `mem = a->vt[0x20/4](a, size, 16, dti->id)`, then
tail-call the class ctor with r0 = mem. Delete (0x4c4c4): `a->vt[0x34/4](a, mem)`.

## Constructor pattern (CONFIRMED, uEm001_00 0xcefe98)
```
uFestaEnemy_ctor(this)                 // 0xc9cf0: uEnemy ctor 0xacc8c, vtable 0x1734d44, zeroes +0xca80..+0xcabc
this->vtable = uEm001_00 vtable
*(this+0xcac0) = *(this+0x1428) + 96   // pointer to the monster work area inside the enemy record
*(this+0xcac4..+0xcacc) = 0x19d        // class-specific fields
```
`this+0x1428` = enemy record (HP at +0x370, damage etc., see memory notes). Destructor: slot 0 = thunk to
uFestaEnemy dtor 0xc9d98; slot 1 (deleting) = 0xc9d98 then free (0x4c4c4).

## Factory (CONFIRMED, 0x4ebcc)
`em_create(id, serial, r2, r3, [sp+0x30] u8, [sp+0x34])`:
1. `idx = 0x50b64(id)`; -1 -> return 0. `dti = table_0x1731e2c[idx]`.
2. id 88 only: first allocates a 224-byte control object (0x10b13e8 ctor) and registers it (0xc067ec line 4).
3. `obj = dti->vt[2](dti)` (newInstance).
4. `0x6fb14(obj, id, r3, r2 /*spawn data*/, serial, u8, arg6)` = enemy setup:
   this+0xb5f0 = id, +0xb5f4 = em number (u8), +0xb5f5 = variant, +0xb5f6 = table index (u8), +0xb5f7 = small flag;
   rec+0x1b4 = r3, rec+0x1b5 = u8 arg, rec+0x1b6 (u16) = serial; if spawn data: vcall slot 41 (vt+0xa4) with data[1],
   copies spawn bytes into rec+0x5ce4.., ...
5. `0xc067ec(unit_manager, line, obj, 0, 0)`: line 5 for ids 87 and 76, else 4 (move-line registration).
Callers: 0x5d728 (quest spawns; large serial 0, small 0x2710+), 0xcd624.

## Per-monster files (CONFIRMED path / GUESS lookup)
Path builder 0x15339c, enemy case: `0x4ecf8(id, &small, &num, &variant)` (small = bit 12, num = low byte,
variant = bits 8-11) -> `enemy\em%03d_%02d` (small: `enemy\ems%03d_%02d`) -> arc `nativeNX/arc/enemy/em089_00.arc`
for id 0x59. No `dt_base`/`dtbase`/`cmd_tbl` path strings exist in main: the files inside the arc (dtbase, dttune,
dtbparts, attackdata, bodydata, cmdtbl, area_*, map_info, hagi, doumouka, shell arcs, mod, mot) are probably found
by resource type once the arc is loaded (GUESS; check how uEnemy fetches rEmCmdTbl etc.).

## uFestaEnemy vtable 0x1734d44: what monsters override
57 classes compared (`gu_enemy.py slots 286`). Overrides at 0, 2, 4, 6, 9, 16 are mostly compiler thunks
(`b base`). Real per-monster methods, almost all overriding empty `bx lr` / `mov r0,#0` hooks in the base:
| slot | base | overridden by | called from (framework) | meaning (GUESS unless noted) |
|---|---|---|---|---|
| 1 | 0xc9e80 | 57 | — | deleting dtor (CONFIRMED) |
| 5 | 0xcaeb0 | 57 | — | getDTI (CONFIRMED) |
| 79 | 0xca22c | 49 | 0x72628 (< 0xafda4) | init after data load? |
| 86 | bx lr | 55 | 0x7070c, 0xcf760 | |
| 118 | bx lr | 57 | 0xb8c54 | per-part setup loop (em001: loops [this+0xfc] parts, 0x890adc) |
| 119 | bx lr | 57 | 0xadb3c (< uEnemy slot 9 0xad7b4) | per-frame update hook |
| 123/124 | bx lr | 38 | 0xa5c40 / 0xadb3c | |
| 125 | mov r0,#0 | 57 | 0xa5c40 (< 0xa59fc) | big state switch on this+0x73e0 (em001 2986 instrs) = action/AI dispatcher |
| 127 | bx lr | 55 | 0x76154 | (r1 = byte ptr, r2 out) |
| 129 | bx lr | 57 | 0x755b4 (< 0x76154) | large (647) |
| 130 | mov r0,#0 | 55 | 0xae42c (< uEnemy slot 10 0xae3e8) | large (693), motion-frame float constants |
| 132 | bx lr | 57 | 0xae42c | per-part loop ([this+0xfc]) |
| 133 | mov r0,#0 | 56 | 0x81ff8, 0x9ef3c, 0xa134c, 0xb1d1c | switch on r1-1 (15 cases) |
| 137 | bx lr | 50 | 0xb8c54 | out params *r2 = 0 |
| 141 | | 9 | 0x97ddc (per-frame HP/damage apply) | damage event filter (cmp r1,#7) |
| 169 | | 8 | 0xa4274 | vector length of rec+0x5d10/0x5d18 |
| 170 | bx lr | 46 | 0xadb3c | |
| 171/172 | | 47 | slots 267/268 (0xcb330/0xcc154) | get/set *(work+0x24) (CONFIRMED) - net sync |
| 227 | mov r0,r1 | 28 | 0x8f004 | |
| 230 | | 1 | 0xb6200.. | |

## MH4U uEnemy (0xe6b058, 95 slots) -> MHGU uFestaEnemy slot map
Evidence: Rathian is em001 in both games; uEm001 (4U) vs uEm001_00 (GU) overrides compared by size, immediates,
float literals, field use (`slotmap.py em001`). The compilers differ (armcc vs clang), so instruction sequences
match poorly; constants are the useful signal.
Layout anchors (CONFIRMED): 4U work pointer `this+0x8d88` = GU `this+0xcac0`; 4U record `[this+0xe28]` =
GU `[this+0x1428]`; parts count 4U `[this+0xf8]` = GU `[this+0xfc]`.
| 4U slot | GU slot | confidence | evidence |
|---|---|---|---|
| 0, 1 | 0, 1 | CONFIRMED | dtors |
| 5 | 5 | CONFIRMED | getDTI |
| 78 | 171 | CONFIRMED | `*r1 = work->+0x24` |
| 79 | 172 | CONFIRMED | `work->+0x24 = *r1` |
| 4 | 4 | strong GUESS | 241 vs 239 instrs, imm overlap 0.43 |
| 39 | 118 | GUESS | imm 0.56, seq 0.52 |
| 40 | 119 | GUESS | imm 0.56, float 100.0 |
| 46 | 127 | strong GUESS | imm 0.78, sizes 211/299 |
| 48 | 130 | strong GUESS | 22 floats incl. motion frames 34/86, float+imm 0.41 |
| 50 | 132 | GUESS | both loop over parts ([this+0xf8]/[0xfc]) calling a per-part getter (4U 0x1a4814 / GU 0x890adc) |
| 51 | 133 | GUESS | switch on r1 with ~14-15 cases |
| 54 | 137 | strong GUESS | float 1000.0, out params *r1/*r2 |
| 76 | 169 | GUESS | vector length of a record vector |
| 35 | 141 | GUESS | event-id filter (cmp r1,#59 / cmp r1,#7) then call |
| 36, 44, 47, 66, 77, 82 | ? | open | no convincing match yet |
| 6, 9, 16 | thunks | — | 4U em089 just branches to base |
| em089-only: 42, 52, 56, 57, 58, 60, 64, 65, 75 | ? | open | 75 = 1713 instrs (GU 125-like dispatcher? em001 4U does not override 75) |
uEm089 big methods: 75 (1713), 48 (1599), 39 (415), 47 (394), 50 (184), 60 (124), 64 (114), 77 (97), 40 (95).
Next step for the open slots: match the framework callers (GU 0xad7b4/0xae3e8/0xa59fc/0x76154/0xb8c54) to their
4U uEnemy counterparts, then see which 4U slot each caller invokes.

## Minimal uEm089 class in our module
1. **DTI**: 0x20-byte object in module bss, built in module_init with `0x7aedcc(dti, "uEm089_00",
   parent = uFestaEnemy DTI (0x704000+0x18533f8), size, 0, 0, 0)`; then set its vtable to our copy of a monster DTI
   vtable (e.g. uEm001_00's 0x1732290, copied at runtime from 0x704000+0x1732290) with slot 2 = our newInstance.
2. **newInstance**: same allocator call as 0x4c48c (heap from the same GOT slot), size = 0xcad0 (+ our fields),
   align 16, then our ctor.
3. **ctor**: `0xc9cf0(this)`; vtable = our 286-slot copy of uFestaEnemy's vtable (copy at init from
   0x704000+0x1734d44: main's data is relocated, so copying keeps every pointer valid) with overrides;
   `*(this+0xcac0) = *(this+0x1428) + 96`; own fields after 0xcac0.
4. **Overrides needed at minimum**: 1 (deleting dtor: 0xc9d98 then free like 0x4c4c4), 5 (getDTI -> our DTI).
   Slot 0 can stay as the base dtor. Everything else can start as the uFestaEnemy base, which gives an inert
   monster that loads its arc and stands there. Behaviour then goes into 118/119/125/127/129/130/132/133/137.
5. **Registration**: index 137 must reach our DTI: `0x50b64(0x59) -> 137` and table 0x1731e2c[137] -> our DTI
   (relocated table copy or a factory hook). Factory special cases: ids 88 (control object), 87/76 (line 5).
6. **Files**: `nativeNX/arc/enemy/em089_00.arc` (RomFS addition) with the MHGU-format data files of a monster.
