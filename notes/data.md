# Gogmazios data files + HUD icon/name (workstream C, 2026-10-17)

C = confirmed (code/data/round trip), G = guess. GU = MHGU 1.4 main offsets. Build: `tools/build_em089_arc.py
--cmdtbl gog` (file IDs unchanged: 0x10700..0x1071c, field 37 = 0x1071b, gekiryusou 0x1071c), `tools/ui_em089.py`.

## em089_00.arc data fields (manifest field -> source)
| field | file | source | check |
|---|---|---|---|
| 3 | parts visibility XFS | 4U emd rows (+0x88) in Kushala's 12-state layout (`emdata4u.partsvis`) | XFS writer round-trips 5 GU files byte-exact (C); state mapping G |
| 26 | attackdata (HDE) | 4U etd words 28..29, 61 records (`emdata4u.attackdata`) | Kushala/Teostra rebuilt from 4U: 96-98 % equal bytes (C). No bone IDs in this format (C) |
| 28 | hitsize (HTS) | 4U etd word 27, 48 groups; bone 13 -> 201 (`build_em089_arc.HTS_BONE_FIX`) | 95-96 % on Kushala/Teostra (C); 13 -> 201 G |
| 30 / 31 | bodydata = HURT volumes / cambodydata (BDD) | 4U emd words 8 / 9; bone B kept on shape-2 (two-bone) capsules (fix: was forced to 0xFFFF, collapsing 27 em089 capsules) | 96-99.7 % (C); all bone IDs exist in em089.mod (asserted) |
| 32 | dtbase | Kushala object + 4U emd scalars/blocks voted over 40 shared monsters (`dt_convert.py`, unicorn venv), scale 2.5 at +0x15 | Kushala self-rebuild 97.9 % (the 2.1 % = GU retunes of emd word 38) |
| 33 | dttune | same, etd | Kushala self-rebuild 99.6 % |
| 34 | dtbparts | **still Kushala's** (see below; behaviour gauges, not breaks) | |
| (33) | dttune part table obj+0x68 | 4U etd word 5, 8 x 10 B per part (HP, levels, next HP, kind); converted 2026-10-17 | 29/40 exact over shared monsters |

Bone IDs: the converted MOD keeps 4U's bone IDs and remap, so 4U data needs no remap (C). Only exception: 4U
em089 hitsize names bone 13 (records 3->13 r200, 4->13 r100 in groups 3/4), absent from em089.mod. In every GU
skeleton 13 is the arm/claw joint between 12 and 50, but here it pairs with the neck/head bones 3/4, so it is
mapped to 201 (head tip on the 3-4-201 axis, bind z 680/710/815). G. Without the fix the GU joint lookup gets
remap[13] = 255.

Attack slots for `-DEM089_ATTACK_HIT`: attackEx(slot, index) indexes Gogmazios' own 4U hitsize groups and
attackdata records now (4U attack IDs = indexes as in em089's 4U code).

## Damage, parts, HP (C unless noted)
- bodydata record: u16 @6 = hitzone row (dttune meat table), u16 @8 = part index. Player hit code calls
  vt+0x2f8(monster, hit, dmg) for HP, then 0x9d6f8(monster, ldrb [record+8], dmg, kind): part counters
  rec+0x488 + 2*part (scaled by rec+0x388; parts >= 8 -> vt+0x310). 4U and GU records are identical (Kushala).
- em089 parts (4U @8): 0 head, 1 back + bone 200 (the Dragonator spear joint; row 1, all-zero hitzones), 2 / 3
  wing limbs, 4 front legs / abdominal, 5 rear legs / waist, 6 tail, 7 chest (bone 205). Names = Kiranico's MH4U
  stagger list order (head 650, back 600, wing limbs 750, front legs / abdominal 800, rear legs / waist 850, tail
  750, chest 600); confirmed in game 2026-10-20 (the part-7 break was the chest). Was "1 neck/chest, 7 bone 205".
  Rows (@6): 0 head, 2/3 wings, 4 tail tip, 5 bone 205, 6 legs/tail, 7 body.
- Base HP = dttune obj+0x64 (file +0x38) = 4U etd +0x10: Kushala 4200 (both games), Gogmazios 17500. Quest HP =
  base x quest table 91 (Kushala G4: 53375 / 17500 = 3.05). Defense rate rec+0x388 = 0.75 (quest table 93, G).

## dtbparts (DTP 0x01339ecb): layout decoded, semantics not (stopped here)
Loader 0x5575C (vtable 0x1733048), from the loader trace (C):
- 0x08: u8 counts/flags[16] -> obj+0x8c..; 0x18 f32 x2; 0x20 u16 x14; 0x3c f32 x3 (5400, 15, 40 on Kushala); 0x48 u32; 0x4c u8.
- then arrays sized by the count bytes: [0] x 4 B (obj+0x64); [1] x 13 B {u32,u8,u32,u32} (+0x68); [2] x 12 B
  {u8 part, u8, u16, f32 HP, u8 x4} (+0x6c; Kushala (0,4,600.0), (1,1,200.0)); [4] x 15 B {u16 x5, u8 x5} (+0x74);
  [5] x 24 B (+0x78); [7] x 5 B (+0x80; Kushala 12 = its 12 XFS states); [8] x 4 B {u16 3005.., u8, u8} (+0x84);
  Rathian adds a 4-byte f32 block (+0x88).
- 4U correspondence is weak: the vote (dump/dtmap/dtbparts.json) matches only 4/40 monsters for one block.
  4U em089 emd word 33 = break list (groups 105, 13, 14, 20, 101), word 35 = sever/detach records (tail bones
  141-143, bone 200). Converting needs the meaning of the 5-byte state records and the break records, i.e. GU
  code reading obj+0x6c/+0x80. Kushala's file stays: consistent with the 12-state XFS above, part indexes 0/1
  are in range of Gogmazios' dttune part table, so no out-of-bounds read; break behaviour = Kushala's (wrong parts).

## XFS states (field 3)
Every value = the group's full 4U evaluation (all its rows) at spawn state word 0x7c (D: em089's tar state at
spawn), intact, unsevered; a break/sever state flips only its own condition (`emdata4u.row_visible`). State 0 =
spawn visibility; 2-4 / 7-9 = 4U break records 0, 1, 2 intact / broken; 5 / 10 = sever (cond 1 param 1) intact /
severed (group 19 = add-material glow, hidden in both). D's slot 118 applies 0, 2-4, 5 at spawn. Materials also
carry the 4U RS* raster states (tar RSMeshBias5/10/12) into mrl_build (D). Not represented: 4U breaks 3, 6, 7 (groups 28/29, 105/35, 32/33) and every
cond-7 row (state-bit visibility = **tar meshes**, bits 0x400000, 0x8000, 1, 2, 0x200000, 0x800, 0x40000, 0x80000,
0x400, 0x10, 0x10000, 0x20000, 0x100000) and cond 11. Those need GU code that toggles groups: XFS states could
be appended after index 11 (one on/off pair per bit) once the GU "apply state" function is known. Leads: object
rMonsterPartsManager, mPartsVisibleGroupList MtArray at +0x64 (property registration 0x5990c, reset 0x59a88);
field 3 reaches the enemy through the loader-callback table set up at 0x705a0.. (setters 0x709c0..0x70a5c, data
words 0x1839b38..). Not finished.

## HUD icon (C)
- reg_icon[index] = UI icon index (0x560ca4). Setter 0x56ef50(ui, obj, kind, i, table): `i < 196`, texture =
  table[i / 98] (0x1635228 = micon00, micon01), rect = 0x560918 kind 3: local = i % 98, col = local % 7,
  row = local / 7, 36 units per cell (72 px in the HD atlases).
- The game uses 0..140; micon01 cells 43-48 (i 141-146) are empty in all 5 languages, and GU's micon01 (512x512,
  72-px cells) like HD UI v4's (1024x1024, 144-px cells) holds only cells 0..48 (i 98..146). micon00/01 come from
  resident_<lang>.arc, which HD UI v4 replaces, so patching them is not shippable.
- **Since 2026-10-26: a third atlas (C for the code paths, untested in game).** UI index 196 + k = cell k of
  romfs nativeNX/mh4uport/micon_sd.tex / micon_hd.tex (tools/ui_icons.py: GU micon01's size and grid, 4U art 2x / 4x
  nearest; cell 0 = 4U '?'). module/icons.c hook 0x56ef58: GU skips the bind (i >= 196) and sets rect i % 98 = k;
  the hook points the sprite (as 0x546f48: [gui +0xf8 / +0x294][obj] +0xd8 [kind]) at a copy of the .gui's micon01
  texture entry (0xb80fd0([sprite +0x78], ids[1]); 64 B: +4 flags, +8..+0xe s16 rect, +0x28 rTexture) with +0x28 = our
  rTexture (sResource vt[0x30](mgr, rTexture DTI 0x21255d0, "mh4uport\\micon_sd|hd", 1), picked by micon01's
  +0xdc / +0xe0 size), sprite +0x100 = 0x4d480000 (0xa4faf0 rebinds any real ID). No atlas -> cell 146 instead.
- Quest board bytes (0x3a3178): < 142 = UI index + 1, 142..186 = hyper (table 0x162a63c + badge at 0x613318),
  > 186 = none in GU; icons.c maps 200.. to our cells (tools/alloc.py board_byte) and hands the board loop byte 0
  (hook 0x6132e0) so no hyper badge shows. The HD UI v4 icon cheat patches 0x3a3188 / 0x613318 only: compatible.
- Art: MH4U eng core_common.arc `cmn_micon_BM_MQ_NOMIP`, 36x36 pixel art; 4U index i: i < 98 -> column i % 7, row
  i // 7; else x 256 + 36 * ((i - 98) % 7), row (i - 98) // 7 (the right block starts at 256, not 252; allocations.toml
  icon_4u). 4U quest board icons = u16
  +0xE8 = icon index + 1 (Tigerstripe m10821: 102 = icon 101; icon 102 is Tidal Najarala, C by its art); Dalamadur /
  Shah / Gogmazios quests: 0, shown here as '?'.
- Users: menus/results/Hunter's Notes/quest counter GUIs (14 .gui files name micon00/01), the target camera / enemy
  panel (0x657044 -> setter, IDs {2,7}); the map does not (map = shape atlas + size class, already relocated).

## Name (C, partial coverage)
- monsterName_<lang>.gmd: 268 strings, entry k = registry index k for 0..136; 137-252 repeat the large monsters
  (second list), 253-267 classes. Entry 133 = empty (reserved code 0x57), 105-111 = dummy1-7 (unused codes 0x1064..).
- Lookup: 0x55bc4c(mgr, 3, k) = GMD #3 string k; 0x55bda4(mgr, id) = 0x50b64(id) gives k for 14 callers.
- Implementation: entry 105 'dummy1' -> 'Gogmazios' (5 languages, GMD v0x010302: strings are the last
  u32@0x20 bytes, no offset table), hook name_index (0x55bda4, replacement hook) maps 137 -> 105.
- Not covered: 30 other `0x55bc4c(.., 3, k)` callers compute k themselves (lists, quest data); they may show
  entry 137 ("Rathian") or nothing. Japanese text: no monsterName_jpn in the RomFS.
- Base files are the v1.0 RomFS; v1.4 might ship different copies (no NCA keys here to compare).
