# Battlequarters (Gogmazios' arena) as a NEW MHGU stage — package E (static research, 2026-10-17)

C = CONFIRMED in code/data, G = GUESS. MHGU addresses = 1.4 main offsets (runtime 0x704000 + off).
4U = MH4U v1.1 code.bin addresses / EUR RomFS. Nothing was run in game.

## 1. The arena in MH4U
- **Battlequarters = stage m19** (4U map-name GMD `eng\msg\common\mapName_eng` in core_common.arc: index k -> m(k+1);
  18 = Battlequarters -> m19). C
- Quest data (loc/data/quest00/01.arc, type 0x1bbfd18e, "v005"): byte **+0xC4 = map number** (19 in both
  Gogmazios quests m11014 / m11035, rare in others), +0xD0 / +0xE0 = 89 (main target em089). C
  em089 slot 42 compares a global's byte +0x1c with **61** and a quest-id window 1033..1096 (0x8c9d68) -> a runtime
  code, NOT the quest-file map number (61 does not appear at a common offset in the two quests). G (likely a
  quest-category/stage-variant id; only toggles model flag 0x20000).
- Files (all extracted to dump/romfs):
  - `/loc/data/m19.arc` (1.9 MB, 181 entries): collision for the 4 areas (`stage\m19d\m19aNNd\collision\m19aNNd-a-g00`
    ground / `-a-w00` wall, type 0x51fc779f "SBC"), stage IPS/IPL (0x52776ab1 / 0x25fd693f, m19d, m19d_high, m19d_g),
    area info `m19aNNd-info` (0x065375d5 "SIS" v6), item boxes, pitfall models (`m19-trap`), gimmick models
    `m19d-etc\m19d-ballista`, `-ballista1`, `canon00_BM` texture, a Castle Schrade ballista (`m10d-ballista3`),
    area-3 extras (`m19a03d-s00/s01` + SDL, `m19a03d_yari02_BM` = spear/Dragonator texture), stage effects
    (`effect\...\st\m19a03`, `qe000/qe001`), BGM refs `sound\bgm\stage\bgm_st_19`, `str_map\m19`.
  - `/loc/data/m19a00..a03.arc`: per-area geometry (MOD/MRL/TEX), SDL schedulers (`sdl\m19aNNd-*`), camera
    (`etc\m19aNNd-cam`, 0x6b41a2f9 "SCD" v0x13), area SE/sound calls. **a03 is the arena**: ballista launch/hit SE,
    breakable sets `m19a03d-k01..k03` (KowareObj, 3 damage stages each = destructible cannons G), rain set.
  - `/eng|fre|ger|ita|spa/data/m19*_map.arc`: map layout (lyt). `/snake/...m19*_.arc`: New-3DS HD copies.
- 4U code: per-stage gimmick model path table in .rodata (`stage\mNNd\mNNd-etc\mNNd-ballista1/2`, `-ballista`,
  `-gekiryusou` for m06d, m10d, **m19d**, ...; strings near 0xe8d710..0xe8d9a0) used by `uStageGimmick`
  (DTI 0x10bc938, size 0xce8, parent uModel, vtable 0xe60250). Breakables: uKowareModel (0x10b9140) / uKowareSdl.
  Stage framework classes are the SAME names as in GU: rStageAreaInfo, rStageInfoSet, rStageCameraData, uStage,
  uStageSet, uStageDataSet, sStage. C
- Gogmazios side: its own arc holds the **Dragonator** model `em089_gekiryusou` and the pile-bunker SEs
  (`em089_se_ship_pilebunker_*`); em089 motion banks 3 (768+) are gimmick sequences, model-animation names
  `Light_Wing_Attack_gekiryusou` / `_houdai` (houdai = cannons). Slots 42 / 58 / 64 / 77 = arena hooks
  (notes/em089-behaviour.md). C

## 2. MHGU stage system
### Files (C)
- `nativeNX/arc/stage/mNNd/mNNd.arc` + `aXX.arc`: geometry (MOD/MRL/TEX), SDL schedulers (lights/filters/sets),
  stage SE, BGM `sound\bgm\map\mNNd\bgm_mNNd` (STQR) + `sound/bgm/map/mNNd/wav/mNNaXXd.opus`.
- `nativeNX/loc/arc/stage/map_com/mNN.arc` (Fortress 18 MB, 573 entries): **all gameplay data**: collision SBC
  (`stage\mNNd\mNNaXXd\collision\...-a-g00`), area info SIS, IPS/IPL, cameras (XFS: cmnData.areaNo/camType/
  panParam/railParam...), navigation (`stage\_point_pos\mapNN\mNNaXX`, `stage\_way_point\mapNN\mNNaXX`,
  `relation\mNN\mNNaXX` = RouteFindDataResource floors/routes), `enemy\area_patrol\_mapNN`,
  `enemy\area_select\_mapNN`, stage shells (`shell\st\st003...`, `arc\stage\quest\shell\st003`), gimmick models
  (`stage\mNNd\mNNd-etc\mNNd-ballista1/2`, **`mNNd-gekiryusou`** in m10, m25, m26, m27), stage tables.
- `nativeNX/table/stage/{floorLvData,kowareObjData,setItemData}/mNNd.{fld,kod,sid}`.
- `nativeNX/arc/stage/quest/shell/st0NN.arc` (stage shell/effect packs; Fortress uses st003).
- UI: `nativeNX/<lang>/GUI/*_quest/map/mNN*`, `<lang>/arc/stage/mapUI/mNNd/aXX_ui_*`, HD_gmk_mNN map textures.
- Path builder 0x15339c builds stage arcs from the number: `stage\m%02dd\m%02dd`, `stage\m%02dd\a%02d`,
  `stage\m%02dn\...` (night), `stage\mapUI\m%02dd\a%02d_ui_%s`, `stage\map_com\m%02d` (strings 0x1557361..0x1557439,
  refs 0x153c30 / 0x153d2c / 0x153db8 / 0x1540e4 / 0x1540f0). A new folder m28d needs NO path table. C

### Stage IDs (C)
- Quest file (329 B, MHGU_Editor tools/quest_info.py): +0x14 = stage 1..27 (101..104 night versions); stage N ->
  folders mNNd. Existing: 9 Arena, 10 V. Slayground, 19 Ingle Isle, 25 Castle Schrade, **26 Fortress** (4 area arcs,
  ballistas + cannons + big cannon + Dragonator model), 27 Forlorn Citadel. Next free: **28**.
- Runtime current stage: byte `[[g]+0x48]` (area = +0x49; night flag [[g]+0x1a2] bit 0) read by sStage/uStage. C

### File IDs per stage are COMPUTED (C)
- Stage files go through the file-ID table like monster files (0x152960). Per-area kinds use
  `fileId = base + stage*13 + area` (13 area slots per stage per kind; contiguous 0..27 stages):
  - sStage 0x4ff9dc: collision kinds bases 0xa229 (a-g00), 0xa395 (a-w00), 0xa501, 0xa66d, 0xa7d9; the loop count is
    the **per-stage area-count byte table 0x162bbe8** (28 entries: 2,12,13,10,10,12,11,11,12,2,2,11,11,11,10,2,2,2,2,2,
    2,2,12,11,10,2,3,2; entry 28 = garbage 245).
  - aQuest 0x4fddec: 0xa945 (area info SIS), 0xd270 (G: camera-related).
  - uStage 0x518c40: 0xc73f (area model, day) / 0xc8ab (night) + stage*13 + area.
  - cameras: base 0xd0cc (m01 a00 = 0xd0d9). Gimmick models have irregular IDs (m26: geki 0xd41e, ballista
    0xd41f/0xd420; m10: 0xd410/0xd412/0xd413; m27: 0xd430..32) -> a per-stage gimmick ID source still to find (G).
- **Stage 28 computes IDs that collide with the next kind's stage 0..** (0xa229 + 28*13 = 0xa395 = stage 0 wall
  collision). Fix: our existing file_id hook (0x152960) maps `base_k + 28*13 + area` to our own file IDs WHEN the
  current stage is 28 (stage 0 data is never loaded at the same time). Every kind's base must be listed.

### Tables that need an entry for a new stage (C unless noted)
- Area count: 0x162bbe8 (u8 x 28), referenced pc-relatively from 0x4ff9dc (literal 0x4ffd30 used by `add r0, pc, r0` at 0x4ffa20; other refs to find).
- Quest-board / counter / map-icon UI: data words (GOT-like) 0x183ff2c..0x183ffec -> tables 0x1634aa4..0x1635324
  (stage-name text index 0x1634f74 via 0x183ff9c: u32 per stage, 0 4 6 8 10 12 13 14 15 26 27 16 ...; readers
  uUIQuestBoard 0x61225c, uUIQuestCounter 0x616574.., cUIOQuestCounterDailyInfo 0x61297c, uUITitleMenu 0x6135fc,
  cUIOQuestMapIcon 0x61912c/0x61a218). Same relocation technique as reg_mapicon (module_init redirect).
- 203 `cmp rX, #27|#28` sites in main: stage range checks/switches somewhere among them -> audit needed for a true
  stage 28 (biggest unknown). G
- Gimmick setup per stage (ballista/cannon/Dragonator placement + which Mediate types exist) — source not found
  yet (no path strings in code; IDs not stored as u16/u32 tables) -> next RE step. G

### Gimmick classes in MHGU (C)
- Hunter side: `cMediateManager` (one instance built at title, 0x1cce60, with cMediateBallista / cMediateCannon /
  cMediateHugeCannon / cMediateRailCannon) + net sync classes `netPlUse{Request,Response,Announce,Release}{Ballista,
  Cannon,HugeCannon,RailCannon}`; `uShellPlcom_BallistaShell` (0x468ff0..); `rPlayerGimmickType` /
  `cPlayerGimmickTypeXML`; breakables `netStageKowareBreak`, KowareObj SDL sets (`mActList, mAtPos0/1, mAtRadius,
  mAtType, mKowareSeReq*`) — the same KowareObj schema as 4U's m19a03d-k01..k03.
- Dragonator: GU has models `mNNd-gekiryusou` (m10, m25, m26, m27) but no "Dragonator" class name -> implemented
  inside a stage/set class (G). **Reuse it** rather than porting 4U uStageGimmick.

## 3. Formats 4U -> GU
| data | 4U | GU | status |
|---|---|---|---|
| geometry MOD/MRL/TEX | 0xE6 / 0x20 / 0xA5 | 0xD4 / 0x22 / 0xA0 | package C converters (monster MODs); stage MODs may use other vertex formats (lightmap UVs, vertex colour) -> extend mod4u2gu |
| collision SBC (0x51fc779f) | `SBC\xff`, bbox at word 10 | `SBC\xff`, header grown (bbox at word 12, counts repacked) | **new converter needed** |
| area info SIS (0x065375d5) | v6 | v6 | same header, likely 1:1 (check field count 240 vs 260 B) |
| stage IPS / IPL | v3 | v3 | same header |
| camera (0x6b41a2f9) | "SCD" v0x13 | XFS (cmnData/panParam/railParam) | converter (fields map by name) |
| SDL schedulers (0x4c0db839) | v0x15 | v0x16 | converter (same tracks: Draw, KowareObj, SoundControl...) |
| navigation | not present in m19 (4U AI uses SIS/collision) | point_pos / way_point / relation / area_patrol / area_select | generate (single-arena = trivial graphs; template from Fortress) |
| stage tables | — | fld / kod / sid | write from Fortress templates |
| BGM | STRQ (3DS streams, `str_m19`, bgm_st_19) | STQR + Opus | audio conversion (decode 3DS -> Opus) |
| stage SE | 3DS banks | GU banks | replace with GU stage SE (Fortress ballista/cannon SE already exist) |
| effects | EFL/EAN (4U versions) | newer | re-author / borrow GU effects |

## 4. Plan
**Recommended path: (A) "Fortress-typed alias" first, then (B) a true stage 28.**

A. Alias (fast, low risk) — 2-3 sessions
1. A quest flag (our own quest, see D) marks "Battlequarters". The game keeps stage index 26 (Fortress) for every
   code table, UI table, range check and gimmick system, but **files** resolve to ours: hook 0x152960 maps Fortress's
   computed IDs (bases above + 26*13 + area, and the gimmick IDs 0xd41e..0xd420) to our converted Battlequarters
   files (served from our file-ID range, like em089), and the arc requests for `stage\m26d\...` / `map_com\m26` are
   redirected to `m28d` / `map_com\m28` (hook the stage cases of builder 0x15339c or the kind requests).
   Fortress stays intact for its own quests (addition, not replacement).
2. Area mapping: Fortress area-count 3 (+camp arc a00..a03) vs Battlequarters a00..a03 -> 1:1.
3. Gimmicks come for free from Fortress's logic; their **positions** come from Fortress data -> re-author
   Battlequarters' gimmick placement in our converted data (needs the placement source, still G).
B. True stage 28 — 3-5 sessions after A
1. Relocate the area-count table (+1 entry) and the ~21 UI data-word tables (module_init redirect).
2. file_id hook: stage-28 mapping for every computed base.
3. Audit the 203 `cmp #27/#28` sites; patch the stage-range ones (literal/IPS) and switches that need a case.
4. Quest-board stage name text (GMD) entry for "Battlequarters".
C. Conversion (needed for both) — 3-6 sessions
1. Geometry: m19a00..a03 MOD/MRL/TEX with package C's tools (+ static-model vertex formats).
2. New converters: SBC collision, SCD camera -> XFS, SDL v0x15 -> v0x16 (KowareObj sets for the destructible
   cannons), SIS (verify), IPS/IPL (copy).
3. Navigation + area_select/patrol + fld/kod/sid: generate from Fortress templates (single arena area).
4. BGM: 3DS stream -> Opus (STQR wrapper copied from a GU stage).
D. Gimmicks + Gogmazios interaction — 2-4 sessions
1. Find GU's per-stage gimmick setup (where Fortress decides "2 ballistas + Dragonator + cannons", the
   Dragonator trigger + damage to the monster) and feed it Battlequarters positions.
2. em089 port (package D): wing attacks targeting Dragonator/cannons (slots 42/58/64/77, motion bank 3) against
   GU's gimmick objects; destructible cannons = KowareObj sets.
E. Quest (addition) — 1-2 sessions
- MHGU quest file: 329 B questData (stage +0x14, target +0x20, ...). Convert 4U m11014/m11035 parameters
  (time, HP/size tables, rewards) to a NEW quest id; ship it as an extra event/DLC quest (MHGU loads event quests
  from its save DLC area -> MHGU_Editor already knows that format) with stage 26 (+flag, plan A) or 28 (plan B) and
  monster 0x59 -> no more TEST_SWAP.

## Biggest risks
1. Hard-coded stage logic (203 range compares, per-stage switches) for a true new ID -> plan A avoids it.
2. Collision/navigation: SBC layout change + nav data that 4U doesn't have; a wrong nav graph = the monster cannot
   move/chase. Single-area arena keeps this small.
3. Gimmick placement/logic source in GU not found yet (may be hard-coded per stage ID) -> could force porting
   4U uStageGimmick logic into the module.
4. Audio (3DS stream codecs -> Opus) and effects formats.
5. Fortress-alias side effects: Fortress-specific scripted behaviour (big cannon, Fortress quest scripts) leaking
   into our arena; mitigated by gating on our quest flag.

# Session 2 (2026-10-17): alias build, converters, hook, quest

## 5. Alias design (final)
- Our arcs keep the FORTRESS internal paths (`stage\m26d\m26aNNd\...`). Every file ID the game computes for stage 26
  (base + 26*13 + area, gimmick IDs) is resolved by path hash at 0x152960 -> it finds OUR resources. No file-ID
  remap, no table edits. The arcs ship at NEW RomFS paths: `nativeNX/arc/stage/m28d/{m28d,a00,a01,a02,a03}.arc`,
  `nativeNX/loc/arc/stage/map_com/m28.arc`. Fortress files untouched -> Fortress quests unchanged (addition). C
- The only runtime change is the arc PATH: hook 0x15339c (module/stage.c, section 7) writes 28 for 26 while our quest
  runs. The request key stays (kind, 26, area, owner), so lookups/releases (0x152c68 / 0x152ef8) are unaffected. C
- Area mapping (Fortress area count 3 stays): m19a00 (camp) -> a00, m19a01 -> a01, m19a03 (Dragonator arena) -> a02;
  m19a02 dropped for the alias. a03.arc = Fortress copy (sound only, 3 entries). C
- Discovery: GU Fortress gimmick models ARE the 4U Battlequarters assets (same AABBs): m26d-a00/a01 = m19a03d-a00/a01,
  m26d-s00..s03 = m19a03d-s01..s04, m26d-gekiryusou / ballista1/2 = m19d-gekiryusou / ballista1/2. Fortress area-2
  ground heights match too (y = 0 and a 1700 ledge in both collision sets, both span +-10000..15000) -> no
  coordinate offset applied (G: horizontal match not verified); gimmick models stay GU's. C

## 6. Converters (tools/stage4u2gu.py)
`python3 tools/stage4u2gu.py alias` (1.5 s) -> module/romfs/nativeNX/arc/stage/m28d/*.arc + loc/.../map_com/m28.arc,
report dump/stage_alias_report.json, texture cache dump/stage_cache/.
| data | status |
|---|---|
| geometry MOD | **done**: static 4U models 0x59DC400B (28 B: f32 pos, snorm8 N, f32 uv, rgba8) and 0x3F78800C (32 B: + 2nd rgba, dropped) -> GU **IANonSkinBC 0x207D603B** (24 B: f32 pos, Normal = packed R10G10B10A2 unorm n = v/511.5-1 with top bits 3 (all 71984 GU stage vertices), f16 uv (v flipped), rgb + alpha). Layout read from AppShaderPackage.mfx IA records (element word: comps = (w>>11)&31, type = (w>>6)&31, offset = w>>22). Several 4U models merged into one GU model (materials renamed `<name>_<k>` per source). Envelopes: 4U stage models carry the same 144-B bone-255 records -> copied. drawMode copied (0xE4C1/0xE5C5/0xE7CD shared by both games). Self-check: positions exact, normals 1e-3, uv 5e-4 (f16), strip topology identical. |
| MRL | **done** (template): GU entries + blocks from Fortress m26a02d/m26a01d materials used only by IANonSkinBC meshes; picked by blend state, lit (4U tLut*/GU FLighting) vs unlit (4U IAFilter2 / GU FConstantColor), raster state, name prefix; animated (UV scroll) templates excluded. Only tAlbedoMap is set (GU stage lit materials have tSpecularMap = 0 too). |
| TEX | **done**: ETC1 -> BC1, ETC1A4 -> BC3 (tex.py), 4U paths kept. |
| arcs a00/a01/a02 | **built**: Fortress arc minus the replaced main model + its now-unused textures, + our TEX/MRL/MOD (TEX -> MRL -> MOD order). a00 = m19a00d, a01 = m19a01d + sky00, a02 = m19a03d + sky00 + c04 (c00..c03 moved to the set scheduler, session 5). **Session 5**: the area set scheduler "-a00" is replaced by the converted 4U one (section 11) with its props converted under 4U paths, the Fortress props it drew (m26a00d-a00, m26a01d-a00/-vr, m26a02d-a00/-a01/-c00) and every Fortress texture they used are dropped; the "-f" filter scheduler keeps GU's structure with 4U light/fog values. Verified (scratch check_arc): every MOD material in its MRL, every MRL texture earlier in the arc, every scheduler model reference earlier in the arc. |
| m28d.arc, map_com m28.arc | **session 5**: m28d.arc = Fortress copy with the breakables replaced / hidden (section 11). map_com m28.arc = Fortress copy with the 14 area SBC entries + 3 SIS converted from 4U and the gimmick shell data edited (st003 FUP + st003_sh001, cart path scheduler m26d-etc-a00; section 11); cameras, IPS/IPL, nav, tables, gimmick collision (m26d-etc) stay Fortress's. |
| collision SBC | **done** (session 3, tools/sbc.py, see "SBC collision" below): a00 g00/w00 <- m19a00d (its shells <- the same main files, 4U camp has no shells; cam = Fortress's), a01 all 5 <- m19a01d, a02 all 5 <- m19a03d. m19a03d's gimmick files (-a-g00-s01, -a-w00-s01, -a-w00-a00-shell) not used: GU's m26d-etc versions (same gimmick models) stay. |
| camera 0x6b41a2f9 | only the camp has one in both games (4U m19a00d-cam "SCD" v0x13, 1160 B, ~8 keyed entries with positions; GU m26a00d-cam XFS, 1905 B, almost no values: zoomDist 953.7). Fortress's kept (no SCD -> XFS converter): 4U camp camera presets not reproduced. |
| SDL 0x4c0db839 | **done** (session 5): tools/sdl.py reader/writer/converter, byte-identical re-layout on 709 GU + 703 4U stage SDLs (section 11). |
| SIS area info | **done** (session 4): same format, copied from m19 with area numbers remapped (section 10). |
| nav (point_pos / way_point / relation / area_select / patrol) | Fortress's kept (same ground layout in area 2, see above). |

### SBC collision (0x51fc779f) — DECODED (session 3, collision agent; full layout in the tools/sbc.py docstring)
- Corpora: all 976 GU SBC files of the base RomFS map_com arcs and 529 of 530 4U files (4U base m01..m21 stage arcs;
  the odd one is an older +0x0C = 0 file) were extracted with scratch scripts (not in the repo). C
- Both games serialize the SAME blocks with the same record formats; only the header, the part records and the
  block ORDER differ. nP parts (each with its own grid), nG attribute groups, nA polygons, nB triangles, nC vertices:
  - polygon AABB 28 B {min[3], u32 local idx, max[3]}: vertex box widened by 1 (by 2 on a flat axis);
  - BVHC (class hash 0x77b17b24): 4-wide BVH over the PARTS (not triangles), 64-B header + 112-B nodes {u8 mask x4
    (high nibble = leaf slots, low nibble = inner-node slots), u16 idx[4], u32 pad (4U garbage, GU 0), SoA boxes};
  - triangle 32 B {normal[3], u16 v[3] local, u16 group, 0, u8[4] edge flags, 0}; vertex 16 B {xyz, 0};
  - group 32 B {u32 w0 collision mask/kind (0x2000000 | bits), u32 w1 (b3 surface/material class, b2 object link,
    b0 sub-type), u32 w2 flags, w3/w4 params, w5..w7 runtime pointers (GU: constant 0x02ac8b30 in w6)};
  - polygon 10 B {u16 tri0, u16 tri1 (0xffff = single triangle), u8[4] quad order, u16 group};
  - grco (class hash 0x77c09c94) per part: XZ grid nx = max(1, floor(extent / cell)), cell 300/600/900 per file,
    z-major (count, offset) table, x-major u16 polygon lists; a cell lists every polygon whose AABB touches it.
  - GU header word +0x50 = 112 * BVH nodes + sum(8 * cells + 2 * list length) (runtime allocation size).
  - Order 4U: header 0x48, parts 0x48 each, polygons, triangles, vertices, groups, (grco + that part's AABBs) x nP,
    BVHC. GU: header 0x54, parts 0x50 each, all AABBs, BVHC, triangles, vertices, groups, polygons, grco x nP.
- Validation: parse + rewrite of all 976 GU files byte-identical; AABB + grid builders byte-exact on both corpora
  (GU 976/976 AABB arrays, 1510/1511 grids; 4U 529/529, 924/924) -> 4U and GU tools build the acceleration data the
  same way, the converter rebuilds it and asserts equality with the 4U copy. The 4U gimmick file
  m19a03d-a-w00-a00-shell converted by us equals Capcom's own GU m26d-a-w00-a00-shell except ONE byte (group w1
  byte 2: 4U 2, GU 0 = object link removed by Capcom for the Fortress gimmick). C
- Attribute mapping: kept 1:1 (every 4U w0/w2/triangle/polygon byte value also occurs in GU). Only change: w1 low
  byte 0x21 (4U-only, 70 triangles, m19 camp) -> 0x23 (what GU's Fortress camp uses) G. Part ids kept (4U m19a03d-w00
  parts 5/6 = two thin walls at z = -4710, x 631..766, probably gimmick-toggled in 4U; GU Fortress uses ids 1/3).
- Size: our area totals 796 KB (a00, shells duplicated) / 342 KB / 728 KB, within GU's range (max m00a01d 1.22 MB).

### Still Fortress data on Battlequarters geometry (after session 4)
- SIS area info: converted (section 10).
- **Navigation**: Fortress's point_pos (12 B, empty), way_point (153 B, empty, identical for all areas) carry no
  graph; relation\m26\m26a01/a02 (RouteFindDataResource XFS: FloorID / mFloorNo / RouteAttr) lists Fortress floors
  (G: floor numbers = collision part ids; our converted g00 files have one part 0, Fortress a02 had 0/3/1) ->
  monster pathing over the 4U ledges is NOT converted; the arena floor (y 0, where Gogmazios spawns) is one
  continuous floor. area_patrol / area_select (_map26) stay Fortress's (single-monster quest, no area changes
  expected for em089 G). Not cheap without decoding the XFS route tables -> left.
- **Camera** (a00 SCD vs XFS), **IPS/IPL**, **minimap/mapUI** stay Fortress's. Area SDLs and gimmick placement:
  converted / relocated in session 5 (section 11). Floor ids: the 4U arena collision groups carry floor numbers in
  group w1 byte 3 (arena floor 1, west/east 950 ledges 2/6, ballista platforms 3/4, north 1700 ledge 5, south 1700
  ledge 7, abyss plane 0 at y -700); the Fortress relation table (RouteFind floors) knows Fortress's floors only.

## 10. Area info + Battlequarters quest variant (session 4, stage agent)
- **SIS v6 decoded** (tools/sis.py; identical format in both games, 194 GU + 124 4U files round-trip): header pos,
  then 4 sections {u32 n, records}: points 28 B {0, pos, u16 kind (camp 0/1/2 bed/boxes G, 3 ballista, 5 Dragonator
  G), w, h}; exits 28 B {0, pos, u8 variant, u8 TARGET area, junk, radius, height}; arrivals 20 B {0, pos, u8 variant,
  u8 SOURCE area (0xff = quest start)}; spheres 24 B. Exit variant v leads to the target's arrival with variant v
  (Fortress links a00 <-> a01 twice this way). C (format), G (semantics, from the data).
- 4U topology: 0 <-> 1, 0 <-> 3, 1 <-> 2, 1 <-> 3, 2 <-> 3 (3 = arena). Alias conversion (stage4u2gu.py convert_sis,
  built into map_com m28.arc by `alias`): m19a00d/a01d/a03d info copied, areas 0 -> 0, 1 -> 1, 3 -> 2; the dropped 4U
  a02's two passages become variant 1 of a01 <-> a02. Camp start = 4U (-2440, 690, -380); every arrival point
  probed on the converted collision floor (camp 627, a01 -3..-23, arena 1700 / 948 / 951). Fall-off exit of the
  arena ((0, -3250, 0) r 10000 -> camp) kept.
- **Quest --bq** (build_gog_quest.py): stage 26, start area 0 (camp), questPlus_0000 (no siege), setEmMain
  b_m26em024_00 area 2, (angle 0, x 633.5, y 0, z 1510.8) = 4U m11014's boss record (+0x1200: em 89, area byte 3,
  pos) on the 4U arena floor y 0. setEmMain floats = (angle, x, y, z): C (GU Arena / Kushala template points lie
  exactly on their stage floors). No-siege evidence: only 3 GU stage-26 quests exist; Lao's carry siege questPlus
  0026/0069 (0026 = ..., 600, 600: fortress HP G), the dummy q0090016 runs stage 26 with questPlus_0000 -> the
  fortress-HP fail belongs to the siege questPlus (G, not traced in code). Options --hp-table N (default 91),
  --icon N (default 24; 142 = Gogmazios UI 141 + 1, unverified).
- Point/arrival u16 after kind / area = facing angle (65536 = 360 deg), point +0 = f32 point id (ballistae 1.0..):
  both copied from 4U unchanged (session 5 finding; GU 0x5027bc hands the point angle to the ballista).
- **Test recipe (main agent; the arena agent never installs)** — state 2026-10-18 session 5: module/romfs ALREADY
  holds the --bq quest and the session-5 alias arcs (rebuilding is only needed after tool changes):
  1. (optional rebuild) `python3 -I tools/stage4u2gu.py alias` (~10 s; writes module/romfs/nativeNX/arc/stage/m28d/
     {m28d,a00,a01,a02,a03}.arc + module/romfs/nativeNX/loc/arc/stage/map_com/m28.arc, report
     dump/stage_alias_report.json) and `python3 -I tools/build_gog_quest.py --bq` (quest 11491 files). --bq is THE
     test variant and, since session 5, also the builder's default (no flag = --bq; the old layout = --legacy):
     stage 26 alias, camp start, questPlus_0000 (no siege), Gogmazios at alias area 2 (633.5, 0, 1510.8).
  2. module: `GOG_DEFINES="GOG_STAGE_ALIAS" GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install`
     (add the other agents' defines to the same GOG_DEFINES string if the main agent uses any).
  3. romfs files to install (all new paths, nothing of the game replaced): nativeNX/arc/stage/m28d/{m28d,a00,a01,a02,
     a03}.arc, nativeNX/loc/arc/stage/map_com/m28.arc, nativeNX/loc/arc/quest/q0011491.arc,
     nativeNX/loc/quest/questData/questData_0011491.ext, nativeNX/loc/quest/questLink/questLink_0011491.qdl,
     nativeNX/{eng,fre,ger,ita,spa}/quest/questData/questData_0011491_<lang>.gmd (+ the em089 files as before).
  4. Expected log (tools/gogreport.py): `gogport: stage path kind 54/56/58 area N -> m28` for every stage arc,
     `gogport: stage gimmicks: spawner this=.. stage 26 flags 3ec alias 1 (quest 11491)`, then the usual em089 lines.
  5. Visual checks for the user (only things a log cannot show): camp = 4U Battlequarters camp with its torch/props
     (m19a00d-a00_0x), warm fog; area 1 = 4U m19a01d with its c00..c04 props and background ring; arena = dark blue
     fog, 2 ballistae on the west/east platforms (4U positions/facing), the Dragonator spears under the north ledge
     below the switch (0, 1765, 3610), the rail-cannon cart parked on the north ledge at (895, 1700, 4355), the 4U
     breakables k01 (east, around (5225, 950, 1370)) and k02 (west, around (-4540, 950, 1485)) in their intact state;
     NO Fortress gates/props floating; no invisible walls; Gogmazios walks on the arena floor.
  6. If the game crashes / hangs while an area loads (last log = `stage path kind 58 area N`): rebuild with
     `python3 -I tools/stage4u2gu.py alias --keep-sets` (then `--keep-filters`, `--keep-koware`, `--keep-gimmicks`),
     each flag restoring the Fortress data of one session-5 change (all four = the session-4 build + 4U SIS), and
     reinstall the m28 arcs.

## 7. Hook (module/stage.c; wired in build.py HOOKS: stage_path, quest_group_fix, quest_unlocked, utf8_null_guard,
## stage_gimmicks (session 5, log-only entry hook on the gimmick spawner 0x50249c, section 11))
- Hook entry of **0x15339c**(_, String *out, kind, p1 = stage, [sp] p2 = area) -> bool, the arc path builder; the
  only user of the stage path strings, all 7 call sites (generic request 0x1529a8 calls it at 0x152a50). Stage
  kinds: 49 mapUI `stage\mapUI\m%02dd\a%02d_ui_%s`, 54 `stage\map_com\m%02d` (loc), 55 `stage\map_com\m%02d_%s`,
  56 `stage\m%02dd\m%02dd`, 57/59 night (Fortress has none), 58 `stage\m%02dd\a%02d`. stage_path_c sets r3 = 28 for
  kinds 54/56/58 (+49 with STAGE_ALIAS_UI, default on since 2026-10-19; +55 with STAGE_ALIAS_WHOLEMAP, nothing
  ships for it yet) when r3 == 26 and the alias is active. Site words `e92d41f0` push /
  `e24dd010` sub sp: displaceable, no branch into site+4 (checked with build.py's displaced_ok/branch_into). C
- Requests come from 0x50373c, releases 0x503854, both with stage = byte `[[0x188ca48]+0x48]`, kinds 53..59. The
  request list is keyed by (kind, p1, p2, owner) -> changing p1 at the request would break 0x152c68/0x152ef8, changing
  only the path string does not. 0x1529a8 always creates a new record (no path-based reuse). C
- Quest gate: the stage byte is written at 0x6c0380 from 0x3bd2a8(`[[0x188ae38]+0xd68]`) = the quest ID whose record
  gives the stage -> stage.c tests that field == GOG_QUEST_ID (so "stage 26 and our quest" is consistent by
  construction). Second copy `[[0x188ad90]]+0xe0` = running quest ID (0x14fd9c is `return id == 308`; set 0x3adf1c,
  cleared 0x39f230), only logged. G: 0x6c0380 runs before 0x50373c on every quest load.
- Plan-B finding: 0x3bd2a8 computes stage = (questfile stage % 100) % 28 (0x92492493 magic, 0x3bd2f0..0x3bd308) ->
  a quest-file stage 28 becomes stage 0; plan B must patch it too. C
- **Patch spec for module/build.py (owner C):** (1) `HOOKS += [('stage_path', 0x15339C), ('quest_group_fix',
  0x3B7DE8), ('quest_unlocked', 0x3B2174)]` (all three sites checked: displaceable, no branch into site+4);
  (2) add `'stage.c'` to the sources tuple in main(); (3) GOG_QUEST_ID defaults to 11491 in stage.c (override with
  -DGOG_QUEST_ID=...); nothing in module_init, no IPS words. Build WITHOUT TEST_SWAP to test the quest. Test define `TEST_STAGE_ALIAS` = every Fortress load uses our files (any Fortress quest
  + TEST_SWAP shows the arena before the quest exists). Area maps (mapUI m28d, tools/mapui4u2gu.py) + record hook
  stage_maprec @0x61c394: port-checklist.md "Arena 4", Map UI bullet (transform, addresses).
- Stays Fortress's for now: language map_com (whole map), quest shell st003,
  BGM, loose nativeNX/table/stage/* (fld/kod/sid live inside map_com, which is ours). Risk: resident resources are
  found by internal path hash; stage arcs are released at quest end (G), shared entries are byte-identical anyway.

## 8. The quest (tools/build_gog_quest.py, ID **11491**, G4 Hub, an addition)
- Why not event/DLC: event quests (10xxxxx) are listed only when the SAVE holds them (lookup 0x3a2c0 over the save's
  event slots + download catalog 0x1595e98); romfs copies are only download sources -> rejected (save + table edits). C
- Hub list: `quest_group` (loc/arc/village/common.arc), in memory `[[0x188ad90]+0xb4]` (count +0x64, entries +0x6c,
  12 B: +4 quest ID, +8 group byte). Loader step 0x3b7de8 walks it; IDs passing the per-place filter 0x3b8090 (Hub,
  stars 11-14, NN 1-99) get loose `loc/quest/questData/questData_%07d.ext` loaded; 0x3bb318 sorts by star byte +0x12
  into boards of <= 99 (G4 has 81). Board filler 0x54b994 shows a quest only if 0x3b2174(_, id) (script
  check_quest_unlocked) returns 1. At quest start: `loc/arc/quest/q%07d.arc` + questLink. C
- Hooks (in module/stage.c, see section 7 spec): quest_group_fix @0x3b7de8 renames the unused DUMMY entry 1011009
  (list index 1412) to 11491 in memory (no real quest replaced; its cleared/seen bits live at index 1412);
  quest_unlocked @0x3b2174 answers 1 for 11491. Not shipping an edited common.arc: only v1.0 is readable here (no
  v1.4 title key) and a v1.0-based 14 MB arc could undo update changes.
- Files (new): module/romfs/nativeNX/loc/arc/quest/q0011491.arc, loc/quest/questData/questData_0011491.ext,
  loc/quest/questLink/questLink_0011491.qdl, {eng,fre,ger,ita,spa}/quest/questData/questData_0011491_<lang>.gmd.
  Self-checks: the GMD writer reproduces the template's files, the arc reads back identical.
- Content: template = Kushala G4 Hub q0011413 ("Steel Yourself", plain hunt) diffed byte by byte; stage 26, start in
  camp, 50 min, 3 carts, every board, hunt 0x59 x1, no subquest; fee 3600z / reward 35400z from 4U m11014, HRP 1880,
  academy 2832 (chosen); stat tables = the 4U quest's rows (m11014 65/109/79, m11035 69/115/83, since 2026-10-20;
  before: 116/98/98 read from the 4U icon field, port-checklist.md), difficulty 1, size fixed 100 %
  (no size data for index 137), board icon Kushala's (24); generic G rewards (spheres/bones); supply box from the
  template; text = 4U m11014 in 5 languages ("Advanced: Quagmire Quarrel", client "His Immenseness").
- Spawn: setEmMain `b_m26em089_00` = area 1 with Lao-Shan's Fortress floats (-124, 15776, 0, 16592) (layout of the
  4 floats not confirmed). **Our arena is area 2** in the alias -> rebuild with `--area 2 --pos ...` once the
  setEmMain float layout is known (4U m11014 places Gogmazios at (633.5, 0, 1510.8)). `--siege` = Lao's siege data.
- Open (G): questData +0x1A (12 as on the Kushala/Lao G4 quests); setEmMain fields; a regular quest in an event
  section of quest_group; "all G4" set awards may now require 11491; title does not name Gogmazios (4U title kept).

## 9. Quest start path (static trace, quest agent, 2026-10-17)
- Accept 0x784e94(ui, id, mode): [[0x188ae38]+0xd68] = id (0x784ec8). Start state machine 0x5d74 (state +0xc8):
  0x60d0 reads d68; 0x3ba100 / 0x3b9ff8 filter only downloaded-event IDs (digits 1x2xxxx) -> regular IDs request
  `loc\quest\q%07d.arc` = path builder 0x15339c kind 2, p1 1 (p1 0/2/3 = gq / vq / gq2), p2 = id. The section /
  group byte of the quest_group entry plays no part (ID-based). C
- 0x7544: arc = 0x152c68(mgr, 2, 1, id); questData = arc entry [count-1] (0x3ba6dc), questLink = entry [count-9]
  with "Link" in its path (0x3ba840; also 0x3bf088, 0x3c4820). v1.0 main (decompressed NSO) used [count-7]
  (0x3b9e08) -> v1.4 quest arcs carry 2 more entries between questLink and questData. Our v1.0-layout arc gave
  [count-9] = supp -> null link -> setup 0x3ade34(quest [0x188ad90], arc, qd, link) bails at 0x3adef4: no
  +0x1324 monster list (spawn loader 0x3adbcc never calls 0x68a70), quest+0xe0 stays 0, no text/resource
  pointers (+0x13dc..). Fix: 2 inert filler GMDs (jpn, kor) after the 5 languages. C
- Quest ID: d68 is cleared at 0x7608 just after the setup; the running ID is [[0x188ad90]+0xe0] (0x3adf1c, from
  questData record +8; records are parsed 272-byte structs, [quest+0xa4]). stage.c gog_quest_id() = d68 ?: e0. C
- Event quests (save-held, (id/1e6)%10 == 1) build their resources in 0x3c3990 (from 0x3c3800) instead. C

## 11. Session 5 (arena agent, 2026-10-18): --bq validation, gimmicks, looks
### Validation (static)
- Floors (scratch probe = vertical ray on the converted SBC triangles): camp start (-2440, 690, -380) -> floor 627;
  camp arrivals 627; a01 arrivals -3 / -23 / -9; arena arrivals 1700 / 948 / 951; Gogmazios spawn (633.5, 1510.8)
  -> arena floor y 0 (floor id 1). C
- Formats: SBC (sbc.py, byte-exact builders), SIS (same format), schedulers (sdl.py, byte-exact re-layout), quest arc
  read back (setEmMain area 2, floats (0, 633.5, 0, 1510.8); questData stage 26 / start area 0 / questPlus_0000). C
- Area numbering: 4U 0 -> 0, 1 -> 1, 3 -> 2 in SIS exits/arrivals (4U a02's passages -> variant 1 links). C
- Not converted (Fortress data kept, risk noted): camp camera XFS (4U SCD presets), RouteFind relation tables
  (Fortress floor list vs 4U floor ids 0..7, see "Still Fortress data"), area_select/patrol, IPS/IPL item pops,
  floorLv/kod/sid tables, minimap/mapUI.
- em089 AI facts (for the behaviour agent, also in the checklist): Battlequarters = alias stage byte 26
  ([[0x188ca48]+0x48]) area 2 while `stage_alias_active()` (stage.c, exported) is true; arena floor id 1 spans
  x -3919..3867, z -5622..5527 (y 0, floor vertices within r 5825 of (123, -180)); ledges: west 950 (id 2,
  x -5170..-2408), ballista platforms 950 (ids 3/4, west side z 554..5527), east 950 (id 6), north 1700 (id 5,
  z 3401..6556: Dragonator switch (0, 1765, 3610), spears in the alcove below), south 1700 (id 7, z -7600..-4710);
  abyss plane y -700 (id 0) + fall-off exit (0, -3250, 0) r 10000 -> camp. Wall probes (4U 0x2b9cd4) see the 4U
  walls: the collision IS 4U's.

### Fortress gimmicks are code-spawned shells (C, 1.4 main)
- 0x50249c(stage mgr) at stage setup: `flags = u16[stage] @0x162bd60` (stage 26 = 0x3ec), stage switch at 0x502510
  (26: 4 spears, sub-type 1, area r4 = 1):
  - bit 0x04: st003 x4 (0x4929f4 spawn data, shell 0x194) = Dragonator spears. uShellSt003 slot 79 0x492a6c: model
    0xd41e (m26d-gekiryusou) for stage 26 (0xd41a stage 25, 0xd430 stage 27, 0xd405 stage 10), position =
    0x4a2f14(this, index + 3) = st003 FUP vec[3 + i]; (pitch, yaw) degrees = 0x4a3164(this, 0/1, -1) = floats of
    st003_sh00<sub-type> (sub-type = spawn byte +8 = 1 for stage 26); FUP floats 0..2 -> +0x15dc/+0x15e0/+0x15d8.
  - bits 0x88: loop over every area's SIS points (0x4fc69c): kind 3 -> st004 ballista (0x493864, shell 0x195;
    pos = point pos, angle = point u16 +0x12, id = point +0 float, area); kind 6 -> st008 (0x498a68, shell 0x199).
  - bit 0x20: st006 x2 (0x494c48, shell 0x197; spawn byte +0x10 = area 1 / 2): rail-cannon cart, models
    m26d-s00..s03 (0xd422..0xd425) + collision g00-s00 / w00-s00 (0xd426/7) + path scheduler m26d-etc-a00 (0xd421).
  - bit 0x40: st007 (0x497698, shell 0x198): gate m26d-a00/a01 (0xd429/0xd42a) + collision w00-a00-shell (0xd42b),
    pos = st007 FUP vec 0.
- Shell parameters live in map_com (`shell\st\st00N\...`, rFreeUseParam "FUP": 'FUP\0', u32 2, u32 nInt, u32 nFloat,
  u32 nVec3, ints, floats, vec3s). The same files sit in arc/stage/quest/shell/st0NN.arc, which nothing requests
  (no path string; only "stage\quest\shell\com"), so map_com m28.arc's copies are the only ones loaded -> editing
  them changes only the alias.
- Model correspondences (same AABBs; GU re-meshed): m26d-a00/a01 = 4U m19a03d-a00/a01 (4U gate scheduler a00, KowareObj
  mType 22), m26d-s00..s03 = 4U m19a03d-s01..s04 (4U s00 cart scheduler, mType 21, + s01 lever 24, s02 25),
  m26d-gekiryusou / ballista1 / ballista2 = 4U m19d-*; m26d-a02/a03 (st008) ~ 4U s05..s10 (4U s03/s04, mType 23).

### What the alias does with them (stage4u2gu.py GIMMICK_EDITS / build_stage_arc)
- Ballistae (st004): automatic from the converted SIS: 2 at 4U (-1930, 950, 2135) angle 20025 (110 deg) and
  (2945, 950, 2160) angle 49153 (270 deg), ids 1.0 / 3.0. C (data), behaviour = GU's ballista.
- Dragonator (st003): st003 FUP vec 3..6 -> (+-380, 1080, 3615.4), (+-740, 610, 3612.6); st003_sh001 -> (0, 180).
  DEVIATION/G: 4U places its m19d-gekiryusou from code (uStageGimmick list 0xef5874) and the transforms were not
  traced; positions derived from GU's own Fortress rule (spears 312 / 308 behind the arena-facing wall, y 1080 /
  610 under a 1700 ledge, under the switch) applied to 4U's straight wall face z 3303.4 under the kind-5 switch
  (0, 1765, 3610); 4U's visual mesh has the matching alcove (wall at z ~3990 for y < 1200, x -875..1000). Facing
  -z = yaw 180 as Forlorn Citadel's sh003. Count 4 = GU's (4U count not confirmed). The switch logic is GU's
  (kind-5 point = 4U's; whether GU reads it or a spear-relative volume was not traced).
- Rail-cannon cart (st006): path scheduler keys all = 4U start pose (895, 1700, 4355), yaw pi -> parked on the north
  ledge. DEVIATION: 4U's cart runs a 4-station route (118 keys, 14500 frames: north / west (-3097, 950, 590) / south
  (0, 1700, -5210) / east (3535, 950, 840)); GU st006's state machine (FUP stop frames 0, 800, 1000, 1800, 2000,
  3000, 4000, 4800) was not traced, so no travel. The area-1 instance sits at the same coordinates in area 1 (outside
  m19a01d's walls).
- Gate (st007): untouched: Fortress FUP v0 (-5980, 2050, -16200) in area 1 = outside our area 1 (harmless).
  DEVIATION: 4U's arena gate (m19a03d-a00/a01 at (0, 2200, -8110), scheduler a00) is not shown (st007 is tied to
  area 1 by the stage switch; moving it would put an area-1 object at arena coordinates).
- st008: not spawned (4U's arena info has no kind-6 point). DEVIATION: 4U's s03/s04 cannons (s05..s10 at (1975 /
  2045 / 2050, 0, 1230) and (-1500 / -1570 / -1575, 0, 1230)) not reproduced: GU's st008 = Fortress big cannon with
  different models; adding kind-6 points would spawn GU's cannon (not 4U's) -> left out.
- Breakables (m28d.arc): area-2 KowareObj slots m26a02d-k01/k02 <- 4U m19a03d-k01/k02 converted (mType 0, 3 damage
  states each, 4U positions via mBasePos (5225, 950, 1370) / (-4540, 950, 1485); the a06 smoke billboard, a
  uKowareModel in object category 9 that GU never uses for that class, is dropped - it only shows after a break)); mId set to
  the Fortress slot value (1 / 2: no such collision part in our arena). 4U k03 (165, 1700, 6315) dropped (the kod
  table has 2 area-2 slots). Removed: 4U "Effect" controllers (class 0x5a17f498, unused by GU) and SoundControl (4U
  SE ids 300-320 / area 3 of the 4U m19a03d bank). DEVIATION: no GU attack sphere (mAt*) -> not breakable, no break
  SE/effects. Area-1 slots (Fortress gates): kowareModel mOffset y -50000, Draw 0, mAtRadius 0 (hidden).
- NOT ported (4U-only scheduled gimmicks): a01 side doors a02/a03 + sinking wall a04 (KowareObj mType 0, mId 3;
  collision parts 5/6 at z -4710 belong to a04), lever s01 (mType 24), s02 (mType 25), the 4U uStageGimmick
  pile-bunker logic. The em089 "detached bit 8" (Dragonator spear on part 1) is GU-side the behaviour agent's.

### Looks
- Area set schedulers "-a00" <- converted 4U schedulers: camp m19a00d-a00 (uStageSet x many: m19a00d-a00_00/01/02),
  a01 m19a01d-a00 (uBaseModel m19a01d-a00 background ring + uStageSet c00..c04), arena m19a03d-a02 (c00..c03 at 0).
  Every 4U track name exists for the same class in GU's scheduler corpus (no track dropped). Fortress props gone.
- Filter schedulers "-f": GU structure kept (PL player lights, AmbientLight, StableShadow, MhFilter_top stay), 4U
  values copied for same-class objects: env infinite light (EM01/DEF01 <- base01), hemisphere (EM03/DEF03 <-
  base01-Hemi), s2 light (incl. Draw), ColorFog (Draw, color, density, start, end), MhFilter (Draw + 8 gradient
  colors); arena: 4U draws no MhFilter -> MhFilter and MhFilter_top Draw 0. Arena fog = 4U dark blue (0.225, 0.248,
  0.375) density 0.4. Not copied (G): bloom threshold/colour, tone curves, GU fog curve/distance type.
- Not ported: 4U rain variants (-f02/-f03 + m19d-rain00), the 4U sky scheduler motion (sky00 merged static), stage
  effects (4U schedulers m19a03d-e01..e10 / -col use the "Effect" controller class GU lacks; EFL st/m19a03 +
  qe000/qe001 -> effects agent), camp camera presets.
- Stage SE / BGM: the area SE banks / calls / footstep tables stay Fortress's (GU Fortress a02's bank carries the
  4U m19a03d bank's wave names: ballista / big_cannon / ship_pilebunker / taihou / v05_* identical). BGM: GU
  plays the stage streams of `sound\bgm\map\m26d\bgm_m26d` (rSoundStreamRequest "STQR" in m28d.arc: 4 streams =
  areas 0..3, entry 36 B {u32 pathOff, u32 file size, u32 samples, u32 channels, u32 rate 48000, u32 loopStart,
  u32 loopEnd, u32 0x15542770, u32 0}, paths `sound\bgm\map\m26d\wav\m26a0Nd` -> loose nativeNX/.../*.opus).
  4U equivalents: `sound\bgm\str_map\m19\str_m19` (STRQ: m19_a00d..a03d + com rain streams = area streams) and
  `sound\bgm\stage\bgm_st_19` (bgm_map_19, the stage BGM). Hookup for the sound agent: write the converted opus
  files to module/romfs/nativeNX/sound/bgm/map/m28d/wav/m28a0Nd.opus (area 0 <- 4U a00, 1 <- a01, 2 <- a03) and
  give the arena agent (or main agent) samples / loop points; the STQR copy in m28d.arc then gets the paths renamed
  m26d -> m28d (same string length) and the sizes / samples / loops written. DONE 2026-10-18 (sound agent,
  tools/snd_bgm.py): dump/converted/bgm_m28.json + m28a00d/01d/02d.opus written, `alias` re-run, streams 0..2 = 4U
  a00 / a01 / a03 (stream 3 Fortress). The battle-BGM selector of GU = 0x4e60d4 (em type switch 12..88), hooked by
  module/em089_bgm.c for em089 (themes appended to bgm_bt.stqr, ids 0x900 / 0x901): notes/port-checklist.md
  "Sound + BGM". Area SE banks / calls stay Fortress's (area call format 0x2543b93e not decoded).
  UPDATE (arena-2): area SE packed after all (section 12, "Sound").

## 12. Arena 2 (arena-2 agent, 2026-10-18): Dragonator, route finding, gimmick visuals, sound packing
C = code/data traced, S = statistics over GU data, G = guess. 4U = v1.1 code.bin, GU = 1.4 main offsets.

### Dragonator (C)
- 4U placement: per-stage classes aMapNN (DTI names; vtables 0xe65140.. step 0x38; aMap19 = m19 vtable 0xe6556c, setup
  slot 0x6594b4) build uStageGimmick (DTI 0x10bc938, ctor 0x33ce00, param {u8 type, u8 sub, u8 area, pad, vec pos,
  vec rot}) via 0x6c1cc0 (type 2) / 0x6c53d4 (1) / 0x6c66f0 (3) / 0x5b8d50 (0, from the set list) into stage slots
  +0x664..+0x670. aMap19: type 2 at (+-495, 800, 4105) rot (0, pi, 0) area 3 (literals 0x6596c8..0x6596d8);
  type 3 sub 0 and type 2 sub 3 at 0 (no model). Model = per-stage list [0xef5964][stage][2] (m19: 0xef5874 ballista,
  ballista1, ballista2, m10d-ballista3, gekiryusou) indexed by table 0x1032f80 {1, 5, 4, 1}[type] -> type 2 =
  m19d-gekiryusou (= GU m26d-gekiryusou). Updates per type: 0 0x33b044, 1 0x33b968, 2 0x33c7c8, 3 0x33bdf8.
- 4U spear (type 2, sub 0) 0x33c7c8: state 0 waits for global [0xfbeffc]+0xdd28 != 0 and bit 0 of +0xdd29 (fire);
  -60 frame lead, spin-up 60 frames (SE 58), thrust 8 frames to 1600 (1400 + 200, SE 59), back to 1400 in 8, hold to
  180, retract (SE 60). Sub 3 (pile bunker): bit 1, 150 + 30 thrust, finds em 89 (0x68fd44(.., 89)) for its SE
  218 / 219. Switch: player interaction -> 0x6bc9dc (sets bit 0, time +0xdc98, +0xdd1c = fps * 600); re-arm in
  0x6b0ce0 when elapsed >= fps * r9 * 60 with r9 = 10 (2 for quest 351) -> 4U reuse = 600 s; usable at quest start.
- GU: st003 spear update 0x492db4 has the same constants (8 / 1600 / 1400 / 180 / retract), so 4U's motion = GU's.
  Spawner 0x50249c: stage 26 -> 4 spears (r11), sub-type 1, positions FUP vec 3..6, (pitch, yaw) st003_sh001.
  Controller = stage gimmick manager [0x18977a0] (0x503c7c per frame; state +0x36c, timer +0x370, flags +0x1a2:
  bit 1 Dragonator present, bit 2 fired, bit 3 ...). Init 0x503c18: timer = questPlus mGekiryuStartTime * 60.
  State 1 waits for quest+0x2f (quest started, 0x39fc84), then stage 26 -> state 2: needs SIEGE PHASE 3 (0x3a5ec4 =
  byte quest+0x1776, call 0x503d54); others / after: start timer -> state 5 ready (+ message 12), reuse = mGekiryuReuse
  Time * 60 (state 7, messages 65 / 66 "ready in N min", 70 = no reuse). Ready check 0x503b88 (flags & 2 && state 5)
  from the player interaction 0x2ed1c4 (interaction kind 11 = Dragonator, from the SIS point kind 5); fire 0x503bb0:
  flags |= 4, +0x15e5 = 1 on each non-null spear slot +0x35c..+0x368.
- cQuestPlus (rQuestPlus 0x26bec21c, entries 24 B at +0x6c; getters 0x3a35a4.. 0x3a3740): u8 mIsRail +4, u8
  mIsRailStart +5, u16 RailOpen/Start/Reuse +6/+8/+10 (stage 9 only: 0x504e64), u8 mIsGekiryu +12 (stage 10 spawner
  0x502588, HUD 0xfe102c), u16 GekiryuStart/Reuse +14/+16 (seconds), u16 FortHpS/L +18/+20. File: f32 1.0, u32 1, then
  the fields packed (25 B). GU survey (80 files): Castle Schrade / stage 10 use mIsGekiryu 1 start 600 reuse 0.
- Alias (done): st003 FUP vec 3/4 = 4U spears, sh001 = (0, 180); module/stage_gimmick.c: stage_spear_count @0x502694
  (loop ends after 2 spears), stage_siege_phase @0x3a5ec4 (returns 3 when lr = 0x503d58 and the alias runs),
  stage_dragonator_fire @0x503bb0 (log); build_gog_quest.py --bq: questPlus_1491 (mIsGekiryu 1, start 0, reuse 600).
  Expected log: `gogport: stage dragonator: 2 spears spawned`, `... siege phase check answered 3`, after the switch
  `... fire (state 5, flags .., spears <2 pointers> 0 0)`.
- em089 sever link (break agent): GU st003 hits use the st003 HDS (0x4eb68cee) entries 0..3 (st003_hit00k ints [k]):
  attack type byte +6 = 0x20 (32), power 180 / 200 / 180 / 40. 4U em089's part-1 detach row expects damage type 126;
  which hit field GU's sever counter (0x97ddc, dttune row +4/+5) compares was not traced -> the dmg_recv diagnostic
  log of a Dragonator hit gives the GU kind to put in the em089 dttune part-1 row.
- 4U uShell020 (Eiyu BGM lead): only built by player code 0x835cf8 (factory 0x660e88 case 20 via 0x6621a0, kind 0);
  no stage gimmick spawns shells.

### Route finding (C format, S rules)
- relation\m26\m26aNN = RouteFindDataResource XFS (0x1e329efc; classes 0x1e329efc root {mQuality, obj}, 0x71134d41
  {mAutoDelete, mpArray}, 0x729c691f {u8 mFloorNo, mRelationArray}, 0x77a3e1a3 {u8 RouteAttr, u8 RouteAttrDir, s16
  TblCnt, u8 FloorID0..7}); XFS v0x10.8: header +8 = object count, defs 8 + 0x28 per member, objects {u16 2*def+1,
  u16 id, u32 size}, every member = u32 count + values. Loaded per area by sStage 0x4fded0 -> stage+0x3c0+4*area;
  cRelationData +4/+5/+6/+8 (registration 0x4f5cb8). Floor ids = collision group w1 byte 3.
- Rules (78 GU tables): see stage4u2gu.py "monster route finding". Generated for the alias: m26a01 <- m19a01d (floors
  0/1), m26a02 <- m19a03d (0..7: 1-2 4, 1-3 1, 1-4 1, 1-5 8, 1-6 4, 1-7 8, 2-3 1, 3-4 1). The generator applied to
  Fortress a01/a02 reproduces Capcom's topology and every path; attr differs on 2 floors (Capcom 16 for a 1700
  platform, 4 for a 400..1000 ramp floor where the median gives 2). G: how the AI uses attr (ability mask).

### Gimmick visuals / logic
- 4U KowareObj gimmicks are scheduler-driven (uKowareObj: action list {Id, startFrame, moveFrame}; play action
  0x1d23a0, by mType 0x6c5e28): cart mType 21 auto-chains its 8 actions (0x1cf090: timer expiry -> 0x1cf55c next
  action, no host check) = 4-station loop; gate mType 22 (ids 53..55); cannons mType 23 (51..55); lever mType 24
  and s02 mType 25 driven by the type-3 controller 0x33bdf8 (0x6c5e28(stage, 25 / 24, 39)); pile bunker fired by a
  player interaction -> 0x5ba3cc case 36 -> 0x6a1f18 (bit 1 of +0xdd29).
- Static in the alias (frame-0 pose, extra uStageSet clones of c00 in the arena set scheduler, camera fade off):
  side doors a02 / a03, sinking wall a04 (its thin collision walls at z -4710 were invisible before), cannons s03 /
  s04 parts s05..s10. `--keep-doors` removes them.
- [-] Cart travel: GU st006 = siege one-way rail trip (path m26d-etc-a00: moves at frames 0-800, 1000-1800,
  2000-3000 in area 1, 4000-4800 in area 2 = FUP ints; state byte +4 0..13 with network sync, update 0x495c20 /
  0x495dac / 0x496500); 4U = KowareObj auto loop. Different drivers -> cart stays parked at 4U's north station.
- [-] Gate (rotated frame-0 pose, no rotation track in uStageSet; GU st007 tied to area 1), lever / s02 / pile bunker
  (no GU interaction kind, no shell, needs new player-interaction + em089 damage code), cannon / door animations.
- Sky motion: none to port (4U m19a01d-sky and the m19a03d-f sky00 object have constant transforms). Rain variants
  (4U -f02 / -f03 filter schedulers): GU's area arc loads only "-f" -> not portable without a variant selector.
  Camp camera presets: 4U SCD v0x13 vs GU XFS camera (no converter) -> Fortress camp camera kept.

### Sound (for the sound agent)
- stage4u2gu.py area_sound(): dump/converted/area_snd.json -> a00 / a01 Fortress area SE replaced by 4U m19a00d /
  m19a01d (same paths), a02 call replaced (0 records); bgm_stqr() uses dump/converted/bgm_m28d.stqr (5 streams,
  stream 4 = camp jingle sequence 0x32). `--keep-sound` = Fortress area SE + old STQR handling.

### Test recipe changes (section 10)
- Rebuild: `python3 -I tools/stage4u2gu.py alias` and `python3 -I tools/build_gog_quest.py` (now ships
  questPlus_1491 inside q0011491.arc). Module: build.py has 3 new hooks (stage_gimmick.c), alias define unchanged.
- Fallback flags: --keep-sets / --keep-filters / --keep-gimmicks / --keep-koware / --keep-sound / --keep-relation /
  --keep-doors.
- Visual checks added: doors / wall at the arena's west, east, south walls; two cannon assemblies on the arena floor
  at about (2000, 0, 1230) and (-1540, 0, 1230); TWO Dragonator spears in the north alcove under the switch; at the switch (0, 1765, 3610)
  the Dragonator prompt appears from quest start, firing thrusts both spears out of the wall; message "ready" again
  after 10 min.

## 13. Arena 3 (arena-3 agent, 2026-10-18): sever kind, interactions, cart loop, gimmick triggers
C = traced in code/data. 4U = v1.1, GU = 1.4 main. Checklist section "Arena 3" holds the same facts as a resume list.

### Dragonator sever link (C): nothing to change
- GU 0x97ddc part loop: sever row = 0x711f8 (dttune+0x68 row + 2): limit vs rec+0x3bd+12p; row+4 / row+5 = damage
  KINDS, mapped by 0x710f0 through the 3-byte list dttune obj+0x6c to accumulators rec+0x498+16*idx+2p. 0x9d6f8
  (called by all 5 hit handlers of the hit dispatch 0x170968) adds every part hit to kinds 126 AND 127; 0x9d8b4
  handles kinds 0..17. 4U: 0x921f?? adds every hit to 126 / 127 (lookup 0x933e08, 2-byte list = etd word 6), and
  0x9178e8 adds special damage to 126. -> 126 = any damage. em089: 4U list [1, 126], ours [126, 1, -1] (Kushala's,
  same kinds); part-1 row (600, 1, 126/-1, 1200) = 4U's -> the embedded spear (groups 20 / 21 / 101) detaches after
  1200 damage of any source on part 1, Dragonator hits included, as in 4U.

### 4U interaction records (C)
- Player: 0xd059d8 -> 0x5b904c / 0x5ba754 nearest record of list stage+0x481c (148-B records: +0x2f area, +0x34
  pos, +0x4c radius, +0x50 height, +0x54 kind, +0x61 mask bit, +0x28 / +0x7c.. attach object + offset) -> player
  interaction number (kind 8 -> 1 ballista, 11 -> 2 Dragonator, 35 -> 11, 36 -> 12 ...) -> case table 0xb0efc4.
  Executed after the motion by 0x5ba3cc(kind 30..36). [0xfb6b7c]+0xc8c low byte = stage number, +0xc90 = area.
- Record creators: SIS points via table 0xfb8ab8 (0x5b9988), item pops (0x5b93c4 / 0x5b9d40 / 0x5ba9c0), 0x5b9fec
  (callers 0x5b921c: 2 x kind 35 on m19; 0x5ba4e0: cart kinds 30..33 on m19 area 3), 0x25ddb4 (19..26), enemies.

### Pile bunker (C): not reachable in 4U m19 -> not ported
CORRECTION 2026-10-20: reachable. The kind-36 record is created by em089's fallen Dragonator spear (cut object 1,
0x926044 at 0x926294); the pile is that spear, ported in module/em089_pile.c (notes/port-checklist.md content
section). "net message 10" below is the uShell022 kind passed to 0x663474, not a packet id.
- Trigger 0x6a1f18 (stage +0xdd29 |= 2, time +0xdd9c, net message 10) only from interaction kind 36; no creator
  of a kind-36 record exists on m19 (list above). One-shot (0x6b0ce0 re-arms bit 0 only). The type-2 sub-3
  gimmick (0x33c7c8 with r6 = 1: 55-frame lead, 85-frame wait (state 7), em089 SE 218 at frame 30 of state 1,
  219 at 90, thrust 150 + 30) plays sounds only (no 0x1a4814 attack enable, unlike the spear on m19); em089 code
  reads only bit 0 (Dragonator fired, 0x6bc67c at 0x8b46d4).

### Rail-cannon cart (C): PORTED as a 4U loop on GU st006 (module/stage_cart.c)
- 4U: player-driven (corrects section 12 "auto loop"): 0x5b9a8c (m19 area 3) -> 0x5ba4e0 registers 5 records on the
  cart: kind 33 (340, 165, 170) r 200, 32 (-340, 165, 170) r 200, 30 (+-280, 0, -415) r 100, 31 (0, 165, -105)
  r 150. 33 / 32 -> 0x6b93b0 type 4 / 3 -> KowareObj (mType 21) cmd 33 / 32 -> next action 43 + station / 47 +
  station (station N0 W1 S2 E3; 0x1d2950 / 0x1d290c) after a 50-frame timer (0x1d2a0c, `r2 = 0` path); each action
  plays s00 frames [startFrame, +moveFrame]: 43 N->W 0+800, 44 W->S 3000+950, 45 S->E 11000+950, 46 E->N 7000+800,
  47 N->E 8500+800, 48 W->N 1000+800, 49 S->W 4500+950, 50 E->S 12500+950 (keys verified). Action end 0x1cead4 ->
  0x1d1318 re-enables the station records. Kind 31 / 30 = charge + fire (type-3 controller 0x33bdf8: KowareObj 25
  actions 40/42/44 charge, lever 24 action 39, shell via 0xc08698).
- GU st006 = Capcom's port: interaction table 0x18929a0 (0x495924) = the same 5 points (GU kinds 27 = 4U 33, 28 = 4U
  32, 25 = 4U 30, 26 = 4U 31); availability 0x495b40 (25 load: stop state && charge < 9; 26 fire: charge > 2; 27
  lower stop exists; 28 higher stop exists); player gimmick actions 0x2cdec4 cases 2 / 3 / 4 -> 0x504254 -> request
  handler 0x497040 (0 / 1 = move to lower / higher stop, 3 / 4 = load / fire with the player); state byte +4: stops
  0..3 (area 1, FUP ints 0 / 2 / 4 / 5) and 10 / 11 (area 2, FUP 6 / 7), moves 4..6 / 7..9 (0x496500), stop entry
  writes the path scheduler frame (+0x15cc unit: +0x34 frame, +0x38 last, +0x40 paused, 0x966140 / 0x966164). Only
  the track differs (linear rail vs 4U loop).
- Port: stage4u2gu.py edit_cart_path writes the 4U s00 cart keys (118 mOffset / mRot keys, same frames +
  interpolation bits, frame count 25000) into m26d-etc-a00 "Model" mPos / mAngle; edit_st006 sets FUP ints 6 / 7 =
  0 / 800 (GU's own area-2 stops = 4U N / W: fallback when the driver is off). module/stage_cart.c (alias, area-2
  cart = [0x18977a0]+0x33c): hook 0x497040 requests 0 / 1 -> 4U legs 43+s / 47+s (lever geometry mapping), 50-frame
  delay, then plays the leg frames with the scheduler step (+0x1c); hook 0x495b40 -> kinds 25..28 off while a leg
  runs, 27 / 28 on at every station; hook 0x495d0c (st006 update after 0x495dac) writes the frame, keeps it paused.
  4U s00 Effect controller (CreateKowareEft index 12 = m19a03_001, group 0, area 3, (0, 1270, -5100) at frames 3935 /
  13445 = arrival at S) posted via em089_efx_stage_kowareeft.
- Deviations: requests are not sent over the network (single player); GU's load / fire / charge logic is GU's (=
  Capcom's port, not compared line by line with 4U's type-3 controller); 4U s00 mActType pulses (10 frames, twice
  per leg) not reproduced (meaning not traced); the area-1 st006 instance (in our area 1) follows the 4U keys at GU's
  area-1 stop frames 0 / 1000 / 2000 / 3000. Fallbacks: `--keep-cart` (parked path + Fortress FUP) or module define
  STAGE_CART_PARKED (driver off; GU logic then runs N <-> W).
- Expected log: `gogport: stage cart: 4U loop driver on st006 .. (start N, frame 0)`, per lever `... lever 27 ->
  4U action 43 (N -> W) after 50 frames`, `... arrived W (frame 800)`, at S `... 4U s00 effect m19a03_001 at frame
  3935 (posted)`. Test: ride / walk to the cart on the north ledge (895, 1700, 4355); the +x lever (kind 27) runs
  N -> W -> S -> E -> N, the -x lever (28) the other way; both prompts at every station, none while moving.

### Floor cannons s03 / s04 (C): traced, NOT ported
- 0x5b921c (m19): kind-35 records at (2050, 0, 1230) angle 49152 and (-1575, 0, 1230) angle 16384, r 100 ->
  interaction 11 (0xb0f424: ready 0x6b1a58 on the carried item kind 1 / 2 = cannonball; player action 171) ->
  0x6b91b4 type 6 -> KowareObj (mType 23, actions 51..55) via 0x6aafec (net). The projectile is a uShell022 subtype
  9 fired from the m19 stage logic 0x6b70cc -> 0x6b985c / 0x6b9d68 (effects agent: impact = m19a03_007 + explosion
  attack 0x9ab120 record 31, launch m19a03_006, trail m19a03_012). GU has no counterpart (st008 = siege cannon,
  single instance, mgr+0x350 siege state machine 0x5042e4, gimmick action case 6 spawns shell type 29). Needs:
  own interaction prompt + cannonball carry check + projectile shell + KowareObj animation -> left (models static).

### Doors / sinking wall a01 (C): traced, NOT ported
- m19 per-frame 0x6b70cc: KowareObj (area 3, mId 3 = scheduler a01) action 0 via 0x6c3400 when the boss HP%
  (0x6ae768: HP * 100 / max of the first large monster) <= 40 and remaining time (+0xad5c min * fps * 60 - +0x803c)
  > fps * 600 (quest 1002: HP <= 50 only; 62211: <= 90 and > 1 min), then HUD message 0x5aa0f0(21) once. Action:
  doors a02 / a03 swing to +-pi/2, wall a04 (x 631..766) sinks 360 over 200 frames, SE 309..312. The a01 scheduler
  moves no collision; collision groups linked to object 3 (w1 byte 2 = 3): a-w00 part 6 group 36 and part 5 group
  37 (135-wide slab at z -4710). Not ported: needs a runtime-driven KowareObj (GU KowareObj action API not traced;
  the 2 area-2 kod slots hold the breakables) + the linked-collision rule; the static frame-0 clones stay.

### Camp camera (C format, not converted)
- 4U m19a00d-cam SCD v0x13: header {7 zones, 6, 1, 0, off 0x28, off 0x2c8, off 0x418}; 7 zone records of 0x44 B
  (bytes {id, 2, 2, 2, 7, ..}, 8 floats = 2 x (x, z, x, z)-like bounds), a 7x7 connection table of 4-B entries
  {u8 to, u8 frames (0x3c / 0x50 / 0x5a / 0x78 / 0xf0), u16 flag}, 7 parameter records of 48 B (vec target, fov 240?,
  45, cam pos ...), one rail block (0x418: 2 points). GU m26a00d-cam = XFS (cmnData.areaNo / camType / panType /
  panTarget / zoomDist / zoomRate, panParam.fov / roll / camPos / target, railParam.railType / target / keyNum,
  connectArray, railPtArray). Camp-only camera framing, no fight effect; a field-by-field mapping is G without a
  GU-side trace of the XFS reader -> Fortress's camp camera kept.

## 14. Arena 4 (arena-4 agent, 2026-10-18): doors / sinking wall, floor cannons
C = traced. 4U = v1.1, GU = 1.4 main. Resume list + all addresses: checklist "Arena 4".

### GU KowareObj = 4U KowareObj (C)
- uKowareObj ctor 0x51155c, vtable 0x176a840; fields +0x182 area (= scheduler +0x59, 0x516b34), +0x184 status (3
  requested, 6/7 playing), +0x185 current action id (255 initial), +0x188 mId, +0x189 mType, +0x158 scheduler
  (+0x34 frame), action list +0x140 (KowareActionParam: +0x30 Id, +0x31 moveType, +0x2c startFrame, +0x28 moveFrame,
  +0x2a quakeType, default moveCnt 1). Manager [0x18977a0]: +0x1bc scheduler slots, +0x21c kobj[24] (0x500d40),
  +0x27c count, +0x280 state bits, +0x3fc kod. Command 0x514f9c(kobj, cmd, a, b); play action 0x515328(kobj, id, 0,
  0, 0) (= 4U 0x1d2a10); action start 0x513d3c; Id 0 start: collision part 2*mId-1 off, 2*mId on (init: the
  reverse), 0x4ffdc4(mgr, area, partId, en) -> 0xc46cfc per collision object; ids 29 / 30 other swaps.
- Creation: 0x4fe9c0 makes the k01..k04 schedulers of every area: file id 0xbbdf + stage*52 + area*4 + k-1
  (0x500bb4(mgr, area, slot k, file id, 1, 0)); the file table holds m26a02d-k03 (0xc131) / -k04 (0xc132) and
  m26a03d-k01 (0xc133) although the Fortress ships none of them.
- kod (table\stage\kowareObjData\mNNd, map_com): f32 1.1, u32 n, n x {u8 area, u8 mId, u8 idx, u8 type, u16 vital};
  type-0 entries keep a played bit idx (0x5011c0 / 0x501864) = 4U state table A 0x6c55d8 (m19: (3, 3, 0)).
- GU quest start (0x42e8 -> 0x500cb4, non-siege host) sends command 0 = action Id 0 to every kobj (Fortress
  barricades open). 4U m19 start 0x6c222c sends nothing (k01..k03 pre-broken only for quest 1002).
- Quest time: 4U quest +0x803c / GU sQuest+0x1c = REMAINING frames (countdown; GU 0x3a0160 decrements it), so
  "limit * fps * 60 - it" (4U 0x6b7474, GU 0x61cff4) = ELAPSED frames. fps = int([[0x2126764]+56]).

### Doors / sinking wall (PORTED)
- 4U 0x6b70cc (m19): kobj (area 3, mId 3) idle and not done, boss HP% <= 40 (0x6ae768) and ELAPSED > fps * 600 ->
  action 0 (0x6c3400 -> cmd 0) + HUD 0x5aa0f0(21) once. (arena-3 wrote "remaining > 10 min": corrected.)
- Data: 4U m19a03d-a01 converted as m26a02d-k03 (stage4u2gu.py convert_kobj: 4U "Effect" controller dropped,
  kowareModel Draw 0 -> 1, SE area 3 -> 2) + its models a02 / a03 / a04 in m28d.arc; a02.arc loses the arena-2
  static clones; kod + {2, 3, 5, 0, 100}. Collision: GU's own action-0 swap toggles SBC parts 5 (wall slab, groups
  36/37 area) off / 6 on in a-w00 (+ w00-shell parts 9 / 10) as 4U.
- Module stage_doors.c: stage_frame @0x503c7c (per-frame tick, also drives stage_cannon.c) = the 4U trigger with
  GU's elapsed time and the boss HP (sEnemy [0x1851fe0] slot getter 0x5ceb4, first large monster, rec+0x370/374),
  cmd 0 via 0x514f9c, HUD 0x65dd68(1, 93, 0), the a01 Effect controller's CreateKowareEft 16 (m19a03_008) at
  scheduler frame 2 (world (0, 0, 0), area 2). stage_kobj_bcast @0x500d18 turns GU's quest-start command 0 into
  the no-op command 1 for every area-2 kobj (doors + arena-2's k01 / k02 breakables).
- Deviations: HUD text (4U "All clear to use the Demolisher!" -> GU "The Demolisher is ready for use.", the closest
  QuestDialog line; kind-1 ids match only up to 12); boss "alive" test = HP > 0 (4U W+0x1b4 bit 0 not mapped).
  NOTE for the pile bunker: 4U announces the Demolisher right when the wall sinks, but arena-3 found no creator of
  the kind-36 record on m19 -> worth a re-check (not done here).
- Expected logs: `gogport: stage doors: quest-start command 0 blocked for area-2 KowareObj .. (mId 1/2/3)` x3,
  later `... boss HP NN % <= 40, NNN s elapsed > 600 -> KowareObj .. action 0`, `... HUD message 93 (4U 21) -> ..`,
  `... frame 2 effect m19a03_008 (KowareEft 16) posted`. Test: fight past 10 min, bring the HP under 40 %: doors at
  the west / east walls swing open, the south wall (700, 0, -4745) sinks 360 over ~7 s, sounds; walking through
  the old wall line at z -4710 works afterwards. Fallback: module define STAGE_DOORS_OFF, converter
  `--keep-static-doors` (old static clones, no kobj).

### Floor cannons s03 / s04 (PORTED, with deviations)
- 4U (corrects arena-3: no cannonball is carried): see stage_cannon.c header and the checklist for the full trace
  (enable at quest setup 0x6aa2d0 when em 89 is in the quest, used until 3 min, 10-min reuse, auto barrel up 25 deg
  when ready, 55 deg after 3 min at 25 deg, ready check 0x6b1a58, switch action 0xb5b2a0 type 6, fire 0x6adb20 /
  0x6ab7f8, uShell023 kind 1 (start offsets (0, 40, 190) / bonus (0, 95, 155), pitch -25 / -55 deg, 125 per
  frame, life 120 / 60), end 0xc776a0 lowers the barrel).
- GU: s03 -> m26a02d-k04, s04 -> m26a03d-k01 (created by the module for area 2 with 0x500bb4 at 0x4fdf7c); two
  interaction records (kind 11 = Dragonator switch, mgr [0x1889ec0], alloc 0x31aa6c, register 0x31abac, free
  0x31aaf4; record +0x4 pos, +0x44 height, +0x48 radius, +0x58 area, +0x60 type, +0x64 kind); ready answered in
  the 0x503b88 hook (lr 0x2ed448 = kind-11 check), fire in stage_gimmick.c's 0x503bb0 hook (lr 0x2d9514 = switch
  action type 0), Dragonator follow-up 0x503a5c skipped for that press; projectile = GU uShellPlcom_009 (shell type
  29, the st008 cannon's shot; setup param 0x4632ec(20, 16) {vt 0x175f7b0+8, type 29, mode 1, owner, u8 0}, post
  0x48c4f0([0x1892550], param); its mode-1 init reads st008 = [mgr+0x34c] (none here) else the owner, then pitch
  +0xfe8 = FUP float 2 (-15 deg), yaw +0xfec, pos +0x40 = base + rotY * FUP vec (0, 40, 100)); hook 0x46365c
  writes 4U's start / pitch / yaw before the start call; uShell base dtor 0x4a18b4 = 4U shell end.
- pl_com_009 = Capcom's port of uShell023 (C): HDS entries 0 / 1 = 4U records 0x102cc60 + 40 * kind (same window
  0..99 / layout; GU power 0 for 4U 1, attack type 75 for 4U 64 = Capcom's renumbering, 14 = 14), HTS = 4U volume 0
  (bone 1001, radius 50), FUP floats 120 life / 600 stick time / -15 pitch, 125 / frame in the shared flight code
  (0x4692d0), the stick-on-monster state (+0x15e8 / +0x15a8 / offset +0x15b0) = 4U state 3. Mode 1 = variant 1
  (hit001 / ef001 / snd001) = 4U kind 1 = the floor cannon -> flight, damage, effects and sound are 4U's as Capcom
  converted them; no own uShell023 class / HDS rebuild needed (no ARC LOCK use).
- Deviations: the bonus shell keeps life 120 (4U 60, GU life field not located); prompt text/icon = GU's
  Dragonator-switch prompt; single player (no net requests); 4U's online-only re-arm shortcut (0x6b1004) not ported.
- Demolisher / pile bunker: NOT reachable in 4U (no kind-34 / kind-36 record in code, m19 data or any m19 quest;
  checklist "Arena 4" item 4); Demolisher = gate KowareObj a00 (actions 53/54/55) for the record.
- Expected logs: `gogport: stage cannon: s04 scheduler (file c133) -> <non-zero>`, `... interaction records (kind
  11) ..`, `... enabled, both used until 180 s ..`, after 3 min `stage cannon 1/2: re-armed` + `action 51 (ready:
  barrel up 25 deg)`, at the cannon `prompt check -> 1`, press: `FIRE (25 deg, 1 shell(s) ..)`, `shell .. start
  (1860, 40, 1230) pitch ee39 yaw c000`, then `action 52 (last shell gone: barrel down)`; 10 min later again; after
  3 min at 25 deg `action 55`, next press a bonus volley (2 shells, pitch d8e4 + ee39). Fallback: module define
  STAGE_CANNONS_OFF; converter `--keep-static-cannons` (old static clones, no kobjs).

### Camp camera: not done (time; section 13 has the SCD layout).

## 2026-10-19: camp dark wedges (2nd attempt, after the w6-bit-31 "lit" change did not remove them)
- Ruled out (C, offline): (a) blend: the camp torch billboards m19a00d-a00_00..02 (4U BSAddAlpha, glow fan + flame
  flipbook quad) convert to the same entry as GU's own billboarded BSAddAlpha stage cards (m02a05d-a00, m02a11d-a01:
  class 5fb0ebe4, w7 8f900000, identical parameter list); main-model blended meshes are clouds / sky. (b) geometry:
  all 193 + 6 meshes IANonSkinBC, indices inside each mesh, no NaN / huge positions, topology = 4U (check); 4U
  strips use degenerate stitching (6491 repeats, no 0xFFFF), GU strips 0xFFFF restarts: both valid strips.
- Only structural outlier (C): the converted camp set scheduler m26a00d-a00 had KEYLESS tracks (0 keys, offsets 0)
  on 2 of the 24 torch uStageSets (mBillboard 3): v05a00-a10-00 (595, 825, 105) mScale + mAngle, -a10-01
  (-655, 825, -89) mScale. Across all 708 GU stage schedulers, no uStageSet (0x2516a76b) has a keyless track and
  none lacks keys on mScale (GU leaves the track out; 97 keyless tracks exist only on other classes, mostly
  0x45a468ee Draw / mAngle). Screenshot: 2 wedges, each converging on a torch flame.
- Cause G: GU's evaluation of a keyless mScale on a billboarded uStageSet (the GU evaluator / billboard code was not
  traced; GU's loader 0xb4f190 only turns offset 0 into a null pointer).
- Fix: tools/sdl.py convert_4u(drop_keyless=True) removes 0-key value tracks (property keeps its class default =
  4U meaning); stage4u2gu.py passes it for the set schedulers and the kobj schedulers. Rebuild: only
  m26a00d-a00 changed (3 entries, -96 B); every other entry of a00..a03 / m28d / map_com m28 byte-identical.
- If the wedges remain: `alias --keep-sets` (no 4U torch props) decides torch props vs main model; next suspect is
  GU's mBillboard 3 semantics on 4U glow fans (4U and GU both use 3, meaning not traced).

## 2026-10-19 night: black triangles (test 4 screenshots, 3rd attempt)
User facts: pure black (rgb 0..6, no fog tint), fixed in the world, drawn correctly from the other side, vanish on
small camera moves; camp (wedges whose tips sit at the torch flames) and arena (thin lines from the sky down to the
wall tops). Pure-black masks of the screenshots: scratchpad mask32/33/34.png (user-confirmed = the triangles).
- Ruled out (C, offline): texture alpha (all 279 m19 stage textures are ETC1 / ETC1A4, converted to BC1 / BC3);
  prim type / drawMode / index base (same as GU: prim 4 strips, indices absolute, minV / maxV = vertex range);
  winding vs normals (>= 0.97 agree on all but 3 small meshes); UV range (|uv| <= 33); vertex data: GU's own
  Fortress meshes carry alpha-0 vertices, constant-UV meshes and black (rgb 0) blockers too (m26d-a03, m26d-s00).
- GU uStageSet (0x51a5f0 ctor, 0x51b21c update, 0x51b4d0 camera test, 0x51bc8c billboard 3): bitfield at +0xfd1:
  byte 0xfd1 = mControlFlag (default 0), byte 0xfd2 bits 0 mSort, 1 mCameraCheck, 2 mCameraClipping, 3
  mCameraCheckPosUse, 4 mCheckCapsuleUse, 5 mCheckCylinderUse, 6 mAlphaAnimation, 7 mUpdateMatrix (default 1);
  mBillboard = byte 0xfd0, mCameraDistance +0xfdc. Update: camera check / clipping run unless sStage+0x1c is 3 or 6
  ([0x188ca48], 0x3f865c) and mControlFlag bit 3 is clear; inside the check volume the set fades out (alpha
  +0x158). Billboard 3 = yaw about the set's Y axis toward the camera view direction (quaternion, no scaling).
- Arena cause (C): 4U m19a03d-c04 (sky cards, cliffs, wall tops above the arena) is a uStageSet of 4U's FILTER
  scheduler m19a03d-f with mCameraCheck 1, distance 6000, cylinder height 1300 around (0, 0, 0): hidden while the
  camera is low inside the arena. The alias merged it into the main model (always drawn). Black blockers c00..c03
  (rgb 0, constant UV, set scheduler) carry 4U mDrawMode 5; every GU camera-checked set / kowareModel carries 13.
- Fix (test 5): FILTER_SETS: c04 appended to the arena set scheduler with all its 4U tracks (clone of c00);
  DRAWMODE_CAMCHECK 5 -> 13 on camera-checked uStageSets (c00..c04). Rebuild diff: a02 main model + MRL (c04 out),
  set scheduler, + c04 MOD / MRL; a01, m28d, map_com byte-identical.
- Camp: no camera-checked sets there; a diagnostic build without the torch glow fans still showed the wedges, and
  so did the arena after the c04 change (screenshots 35 / 36: some stripes textured with wood / rope = real model
  triangles with one corner far away). The module logs sStage+0x1c (`stage gimmicks: ... mode N`).
- ROOT CAUSE (C, user-confirmed fixed 2026-10-19 night): GU ends EVERY mesh's index run with one 0xFFFF restart
  (m26a00d / m26a02d: gap 1 after all meshes, value 0xffff) and its draw reads it; convert_models wrote none (it only
  padded odd runs with a repeat). The strip then ran on into the next mesh's first index: one triangle per mesh
  stretched to that vertex (83 non-degenerate in a00, 61 with an edge > 1000, 25 > 5000, max 326923; 56 in a02).
  Fix: 0xFFFF after every mesh (all area models, props, kobj models of m28d). The c04 camera check (FILTER_SETS) and
  DRAWMODE_CAMCHECK stay (4U data), the glow-fan diagnostic is removed.

