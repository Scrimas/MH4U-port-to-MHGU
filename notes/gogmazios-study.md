# Gogmazios port: static study (2026-10-17)

Sources: MH4U EUR base (`dump/base/*.3ds`, CTR-P-BFGP) + update 1.1 (`dump/update/*.cia`).
The update CIA holds the full program; all code addresses below are **v1.1**.
Tools: `tools/ctr.py` (3DS image reader), `tools/mkelf3ds.py` (code.bin -> ELF + flat mem.bin),
`tools/a4u.py` (DTI registry, vtables, literals), `tools/arc.py`/`arctypes.py` (from MHGU_Editor).
Disassembly: `llvm-objdump -d --triple=armv6k-none-eabi --mattr=+vfp2` -> `dump/mh4u.asm`.

## IDs (emName_eng order k -> em(k+1))
- Gogmazios = **em089** (`/data/em089.arc`, 7.6 MB)
- Dalamadur = em024 (story fight em083), Shah Dalamadur = em110/em111, Dah'ren Mohran = em046
- MHGU numbering is different (MHGU em024/em046 are other monsters).

## MH4U code facts
- MtDTI ctor = 0x5bfabc(r0 DTI in bss, r1 name, r2 parent, r3 size); 952 DTIs.
- getDTI = vtable slot 5; uEnemy vtable 0xe6b058, 95 slots.
- uEm089: DTI 0x10b7d28, vtable 0xe6a2b4, chain uEm089 < uEnemy < uMHchar < uModel < uBaseModel.
- Every uEmXXX is 0x8d90 bytes = uEnemy (0x8d88) + 8: monster state lives in uEnemy.
- uEm089 overrides 30 slots: 1 4 5 6 9 16 35 36 39 40 42 44 46 47 48 50 51 52 56 57 58 60 64 65 75 76 77 78 79.
- Code blocks are laid out by em number. em089 block ~0x8b6600-0x8cc724:
  88 KB, ~22.6k words, ~100 functions, 144 distinct external callees (1431 calls), 3.7k VFP ops.
  Comparison: em024 Dalamadur 46 KB / 121 ext, em046 Dah'ren 60 KB / 143, em001 Rathian 70 KB / 171.
  Top callee 0x91ab1c (412 calls). Callee counts pickled in dump/em089_ext.pkl.

## Assets (em089.arc vs MHGU em001_00.arc)
- Same MT type hashes. Same versions: LMT motion 0x43, EMC cmd table `EMC 04081220`.
- Different: MOD 0xE6 (4U) vs 0xD4 (GU); MRL 0x20 vs 0x22; TEX 0xA5 (3DS) vs 0xA0 (Switch).
- em089.arc: 13 models (body, tail, gekiryusou = tar spear), 4 LMT (5.5 MB), camera list,
  em089_cmd, ~25 effect lists, ~70 sounds (incl. ship pile bunker = arena gimmick).
- MHGU splits monster data into dtbase/dttune/dtbparts/attackdata/bodydata/cmdtbl/area_*/shell files;
  4U keeps part of it in em_data.arc and in code.

## MHGU side
- Monster factory: table of DTI pointers at 0x1731e2c (enemy type index -> class), ~137 entries,
  includes uEmXXX_00 and small monsters; 0x1851078 = placeholder DTI.
- uEnemy vtable 0x1734798 (>140 slots, different ABI layout); uEm001_00 overrides 43.
- MHGU is AArch32: exlaunch/Skyline (AArch64 only) do not apply.

## Loader (WORKS in game, 2026-10-17)
- module/ = subsdk1 (clang armv7a hard-float, PIC, hidden visibility, ld.lld -shared, link.ld, crt0.S MOD0).
  Ryujinx maps it as image 3 at 0x2e19000 (sdk moves to 0x2e1c000+). rtld links it; DT_INIT runs ~5-6 s into boot
  (called by the game's startup, not at rtld time).
- Hooks: build.py HOOKS list -> IPS32 `FB08F1D20FD1204FE7070672777F869B.ips` (offset = main offset + 0x100) writing
  `ldr pc,[pc,#-4]; .word tramp` at the entry; generated trampoline saves r0-r5,r12,lr,d0-d7, calls name_c(regs),
  nonzero -> `bx lr` with saved r0/r1, else replays the 2 displaced instructions (pc-literal ldr re-materialised)
  and jumps to site+8. Checks: displaceable instructions, no branch into site+4.
- Debug output: svcOutputDebugString -> Ryujinx log `|W| <thread> KernelSvc OutputDebugString: ...` (logf()).
- Tested in a full quest: em_index / em_create / pl_update hooks all fire, no side effects.
- Testing: the user launches the game (headless/hidden runs abort ~1.5 s in; gdb outside the sandbox is denied).
  Install a test build with `GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install`, remove after.

## MHGU enemy registry
- ID = (variant << 8) | em number; small monsters 0x1000 | n. Last large em = 0x58 (088) -> Gogmazios = **0x59**.
- 0x50b64(id) -> index: linear search of 137 (id, index) pairs at 0x1597ea4, -1 if absent. 53 callers.
- Index tables: DTI (class) 0x1731e2c (4-byte entries); 0x1732050 via accessors 0x4ed10/0x4ed48/0x4ed9c/0x4edec
  (special id 0x1063 handled separately).
- Factory 0x4ebcc(id, serial, r2, r3): called from 0x5d72c (quest spawns: large serial 0, small 0x2710+) and 0xcd628.
- Observed: id 0x2b looked up every frame by UI code 0x560cb0/0x616520.

## Registration milestones (in game, 2026-10-17)
- Registry relocation (build.py REG_TABLES/LIT_PATCHES/WORD_PATCHES, GOT 0x1839618 written in module_init) + hooks:
  em_create 0x4ebcc, quest_prep 0x68a70, em_arc_request 0x15334c (the quest loader's kind-48 arc request; without
  it the arc for 0x59 is only requested at spawn -> dtbase null -> crash at 0x71284), em_record 0x69c258
  (per-index record array, count 137 -> null -> crash at 0x69c1cc; index 137 borrows index 0), stats_add/hunted.
- TEST_SWAP + CLONE_RATHIAN: Rathian clone as ID 0x59 / index 137 spawns and loads em089_00.arc. Issues: never
  attacks (roar/flinch/topple only), map icon squashed -> per-ID tables still missing (package D investigating).
- TEST_SWAP only (own class uEm089_00, uFestaEnemy base, Rathian files): spawns, fully inert (no motion, tail
  physics only, no part-break model swaps). Class/DTI/newInstance/ctor/vtable path confirmed.
- **Gogmazios drawn in game (2026-10-17)**: real em089_00.arc (converted MOD/MRL/TEX/LMT + Kushala placeholder data,
  file IDs 0x10700.. via hook 0x152960), own class, slot 125 plays idle motion 2: correct shape, scale 2.5, animating.
  Bugs found on the way: arc entry order (MRL must precede its MOD, else the model loads without materials and is
  never drawn); drawMode 0xE4C0 = hidden proxy meshes (drawn = 0xEFFF); vertex w0 is SIGNED 16-bit (unsigned ->
  spikes only when animated, since w3 = 1 - sum keeps the rest pose clean); dtbase +0x15 float = model scale (4U emd
  +0xC; Gogmazios 2.5, Kushala 0.8). Native Kushala clone renders "rusted" (its metal look is set by its class code).
- Only 3 actions requested (1/15, 2/0, 2/2): our slot 125 never ends an action, so the AI never picks a new one.
- Map icon size table 0x1635354 (89 entries by em number) relocated via data word 0x183fff0 (module_init).
