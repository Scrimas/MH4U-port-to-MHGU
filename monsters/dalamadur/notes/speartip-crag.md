# Speartip Crag (MH4U stage 8, Dalamadur's arena): static study for a GU stage alias

Static RE only (2026-10-21), nothing run. C = confirmed in code / data, S = strong, G = guess.
4U = v1.1 (dump/exefs_v11/mem.bin, dump/mh4u.asm). GU = 1.4 main. Scratch scripts and dumps:
`dump/scratch/dalamadur-session/stage/` (col.py collision parts, mods.py model bounds, kcalls.py callers,
acts_k.py action resolution, stage8.py stage-8 compare scan, sdl_k0N.txt, u/ = unpacked arcs).

## 0. Summary
- 2 areas: a00 = camp, a01 = the arena (one fight area). C
- 3 breakables in a01 (KowareObj mId 1..3 = schedulers k00..k02). **Dalamadur itself breaks them**: the tail half
  (uEm083 / em111) breaks k00 and k01, the head (uEm024 / em110) breaks k02, each at a fixed motion frame of a
  joint "arena break" action. The head's EMC picks those actions from the **shared HP %** and the number of
  pieces already broken (k00 at HP < 90 %, k01 < 62 %, k02 < 44 %). No stage timer, no quest script.
  C (callers, frames, mIds) / S (EMC gating)
- Each break swaps SBC collision parts (2*mId-1 off, 2*mId on): platforms vanish and fall-out planes / new walls
  come in. Falling under the arena puts you back in the camp (SIS exit). C (data) / S (gameplay reading)
- "-shell" collisions are loaded with the main files at area load (not swapped at runtime) and serve another
  collision query type (0x10 / 0x20). C (load) / S (use = shells / projectiles)
- Stage music: bgm_st_08 holds **Dalamadur's battle theme** (2 streams, phase 1 / 2), there's no stage jingle. C
- Shah Dalamadur (em110 / em111) runs the same classes, EMC and break logic. Its quest m11030 is on map 8. C

## 1. Areas, transitions (Q1)
| | a00 (camp) | a01 (arena) |
|---|---|---|
| 4U area count | table 0xe087b4 [stage] (getter 0x6c2b00): stage 8 -> **2** C | |
| models (m08a00 / m08a01.arc) | m08a00d + a00..a06 (falling rocks rakuseki01..03, Kaminari01..03 lightning, billboard) | m08a01d, -a00, -a01, -sky (+ k00..k02 breakables) C |
| set schedulers (aMap08 lists 0xecd440 / 0xecd450) | m08a00d-a00, -a01, -a02 (+ -col, -f) | m08a01d-a00 (+ -col, -f, -sky, -e00, -e02) C |
| SIS m08aNNd-info | head (-664, 24, 631); point kind 1 (-951, 66, 81) w/h 150; exit -> area 1 at (-1619, **900**, -152) r 500 h 500; arrivals: quest start (-1322, -42, 303), from area 1 (-508, **3782**, 821) | head (970, 215, 3868); exit -> area 0 at (0, **-3350**, 0) **r 10000 h 4000**; arrival from area 0 (1678, 210, 3213) C |
| collision | g00 (1 part), w00 (1 part), cam; **no shells** | g00 (7 parts), w00 (6 parts), g00-shell (5), w00-shell (4), cam C |
| camera | no camp SCD (m19 had etc\m19a00d-cam); only the SBC "-a-cam" | SBC "-a-cam" (one part, id -1) C |
| map UI | lyt\quest\m08\ui288a00, m08a00_ID | ui288a01, m08a01_ID; stage ui258, m08d_ID C |

- Reading (S): the a01 exit is a 10000-radius volume 3350 below the arena, and the camp arrival from area 1 sits
  3782 up: anyone who falls off the crag drops back into the camp. Leaving the camp is through the raised exit zone.
- Stage init 0x6c5a74 (switch on the stage id 0x6c5a94): case 8 creates **aMap08** (0x657040, DTI 0x10823cc,
  vtable 0xe652ec). It's a small per-stage resource task: slot 11 0x656e44 requests the per-area set schedulers
  (string table [0x656f5c] = 0xecd438), slot 10 0x656f68 creates the 3 KowareObj schedulers via
  0x6c2d4c(stage 8, area 1, k 0/1/2) -> "stage\m08d\m08a01d\sdl\m08a01d-k%02d" (0x6c67b8). C
- 4U quests with map byte (+0xC4) = 8: exactly m10709, m10721 (em024 + em083) and m11030 (em110 + em111). C

## 2. The breakables k00 / k01 / k02 (Q2)
All in area 1, one action each (Id 0, moveType 0, startFrame 0, quakeType 6, moveCnt 1). Placements below come
from the scheduler mOffset (model bboxes are local, mods.py).
| sched | mId / mType | model (textures) | animation (frames) | SE (area-1 requests) / effect | world bbox (approx.) |
|---|---|---|---|---|---|
| k00 | 1 / 9 | m08a01d-k00 (rock01 BM/NM), 2 meshes | at (395, -585, 5866): pitches and falls to y -15366 over 600 f; mDrawView 1 -> 0 at f 599 | 11 @0/2, 12 @40; KowareEft 6 @10 (also standalone sched m08a01d-e00) | x -1900..2373, y -2064..54, z 4721..7823 C |
| k01 | 2 / 10 | m08a01d-k01 (rock01 + nobo02), 4 meshes | at (729, -648, 898): drops to y -3459 in 50 f; hidden at f 299 | 11 @0, 16 @2; no effect controller | x -2031..2472, y -1189..203, z 345..2275 C |
| k02 | 3 / 11 | m08a01d-k02 (rock01 + nobo02, BM/NM), 20 meshes | spire at (404, 1062, -112): tips 10 deg by f 40, falls to (1500, -5000, 2000) by f 299 with rot 30 deg; hidden at f 299 | 11 @0, 16 @2, 17 @23, 18 @87, 15 @120; KowareEft 8 @2 (also sched m08a01d-e02) | x -2031..2918, y -3580..2909, z -2973..2211 C |

### Collision swap per break (C: 4U action start 0x1cd494: 0x6c675c(stage, area, 2*mId-1, 0) then (.., 2*mId, 1); same rule as GU 0x513d3c)
| break | OFF part (2*mId-1) | ON part (2*mId) |
|---|---|---|
| k00 (mId 1) | g00 part 1: floor 1, 205 tris, x -1624..2190, y -333..54, z 4603..7575 (the k00 platform); g00-shell part 1 | g00 part 2: flat plane at y -5000 under the same footprint (group w2 0x2000); w00 part 2: 10-tri wall x -1132..1653, z 4615..5316, y -1763..6504 |
| k01 (mId 2) | g00 part 3: floor 2, y -883..21, x -2119..2359, z -221..2078; w00 part 3; both shells' part 3 | g00 part 4: lower floor y -939..-789 (floor 10); w00 part 4; both shells' part 4 |
| k02 (mId 3) | g00 part 5: the spire (floors 3/12/4/11/2, y -229..2909); w00 part 5; both shells' part 5 | g00 part 6: plane at y -5000, x -2031..2507, z -2523..1755 (w2 0x2000); w00 part 6: 42-tri walls x -2091..2427, z -1851..1880 |
- Load state: odd parts on, even parts off (S for 4U, C in GU: the kobj init sets the reverse of the action).
- Group w1 byte 2 (object link) is 1 / 2 / 3 on parts 1 / 3 / (4, 5). The toggle uses the **part id**, not this
  byte (part 4 carries link 3 but is switched by mId 2). C
- Part 0 of every file never changes. The fall planes (g00 parts 2, 6) and new walls (w00 parts 2, 6) don't exist
  in the shells. C
- Break state persistence: 4U state table A 0x6c55d8 -> [0xfcf4c4][8] = (area 1, mId 1, bit 0), (1, 2, bit 1),
  (1, 3, bit 2) = GU kod type-0 entries {1,1,0,0,v} {1,2,1,0,v} {1,3,2,0,v}. C
- "Broken" test: 0x6c3b94(stage, area, mId) -> 0x6c281c find kobj -> 0x1d238c: kobj+0xb1 >= 4. C
- KowareEft index table 0xe06378: 6 -> 0x00090023, 8 -> 0x000b0023 (list 0x23, elements 9 / 11). The effect files
  aren't identified (open; m19 used lists 0x60 / 0x61 = m19a03_NNN). C (values) / G (list meaning)
- SE: snd_m08a01d request ids 1, 2, 11, 12, 13, 15, 16, 17, 18, 35, 36. Bank waves: m05_wind_strong,
  m08_a01_slime_river, rock_break_M, rock_break_S, m08_rock_crush03, sulfuric_acid_ground_dmg01/02,
  fire_ground_dmg01/02. The id -> wave mapping isn't decoded. C (lists)

### What triggers each break (C)
Stage command 0x6c3400(stage, area, mId, cmd, arg) -> find kobj -> 0x1d23a0(kobj, cmd, arg). It has 22 callers;
the ones in the Dalamadur classes are:
| caller | class / action (cat +0x1ca / num +0x1cb) | motion | frame | command |
|---|---|---|---|---|
| 0x8a0a80 | uEm083 (tail) 7/60 = 0x8a08bc (via cat-7 dispatcher 0x8a1604) | 623 | 1238 | area = W+0x14c, **mId 1** (k00), cmd 0 |
| 0x8a19d8 | uEm083 7/61 = inline handler 0x8a1968 (jump table 0x8a16d0) | 624 | 810 | **mId 2** (k01), cmd 0 |
| 0x7708c4 | uEm024 (head) 7/62 = 0x77060c (cat-7 dispatcher 0x771e60) | 563, then 564 | 1082 of 564 | **mId 3** (k02), cmd 0 |
- Entry: head actions 1/60, 1/61, 1/62 (cat-1 dispatcher 0x76e374 -> thunks -> 0x76e754 idx 10/11/12). Phase 0
  stores a posture in W+0x1c9 and calls 0x920058(this, 1 / 21 / 41) (G: wind-up motion). It then raises a sync
  flag (0x76e914) and waits for the partner (0x68fd44 finds em083 if
  W+0x1c0 == 24, else em111; partner+0x8c88 flag), then queue 7/60, 7/61 or 7/62 (0x94ef9c = queue next action:
  W+0x1cf / 0x1d0 / 0x1d1). C. The tail's entry into its 7/60 / 7/61 runs through the head-tail link. Its EMC
  never names 7/60 or 7/61, so the head drives it. S (path not traced)
- Head EMC (em024_cmd = em110_cmd byte-identical) group-0 script 0 switches on op 0x6f custom conditions.
  Slot 51 (0x774888) answers those ids (S: matched by id meaning; the 4U interpreter's op-0x6f call isn't traced):
  id 0 = posture W+0x1c9, id 1 = 0x7731a4 = highest broken mId in the monster's area (3 / 2 / 1 / 0); id 2 = HP band
  from the shared HP (global [[0xf32004]+0x328]) / max (W+0x3ec): < 0.17 -> 6, < 0.44 -> 5, < 0.56 -> 4,
  < 0.62 -> 3, < 0.84 -> 2, < 0.90 -> 1, else 0. C
  - bands 1-2 (HP 62-90 %): broken 0 -> script 3 (1/60, k00);
  - bands 3-4 (44-62 %): broken 0 / 1 -> scripts 3 / 4 (1/61, k01);
  - bands 5-6 (< 44 %): broken 0 / 1 / 2 -> scripts 3 / 4 / 5 (1/62, k02).
  So the order is fixed k00 -> k01 -> k02, gated by HP. The switch sits under two outer conditions,
  `0a 00 / 0a 01 01` and `11 00 00`, that aren't decoded (open). C (bytes and handlers) / S (bytecode reading)
- Shared HP: shared enemy setup 0x920104 (0x9201a0: em id 24 / 83 / 110 / 111) sets W+0x3e8 from
  [[0xf32004]+0x328] via 0x91ad34 -> both halves share one HP pool. C
- No other trigger exists: the stage-8 code paths (section 4) don't send kobj commands, and no 4U stage
  per-frame logic (like m19's 0x6b70cc) exists for m08. The 0x6c5e28 by-mType callers use only mTypes 2 / 24 / 25. C
  Quest-start pre-break (0x1d0c64) is quest 1002 only (Gogmazios notes). C

## 3. "-shell" collisions (Q3)
- Loader 0x6c4140 (per area, 12-byte records at +0x458 / second array +0x554) builds
  `stage\m08d\` + `m08aNNd\collision\m08aNNd-a` + suffix and registers each file with 0x173d40(cm, res, type, area, 1, 0):
  | file | type bits | slot | if missing |
  |---|---|---|---|
  | -g00 | 0x01 | +0x458 | - |
  | -w00 | 0x02 | +0x554 | - |
  | -g00-shell | 0x10 | +0x45c | main g00 gets 0x11 (0x198e70(.., 17)) |
  | -w00-shell | 0x20 | +0x558 | main w00 gets 0x22 |
  | -cam | 0x100 | +0x460 | g00-shell (or g00) gets 0x100 |
  Shell presence: tables 0xe08594 (g00) / 0xe08650 (w00), {count, area list} per stage. Area 0 never has shells,
  count -1 = none, 0 = every other area. Stage 8: count 0 -> a01 has both. Cam table 0xe08700: stage 8 count 0 ->
  both areas. C
- So shells are **not** a runtime swap: they load with the area and answer queries for type 0x10 / 0x20 (S: shell /
  projectile hits, by name; GU ships shells for every area). Kobj toggles reach them by part id. C
- Geometry vs main (col.txt):
  - g00-shell has 5 parts (0, 1, 3, 4, 5), 1287 polys. The main g00 has 7 parts and 1872 polys.
  - Shell part 0 is trimmed to x -4584..2699, z -2878..5388 (main: the +-10000 plane down to y -5000). It drops
    the groups w0 0xfe, w2 0x2000 (fall planes) and 0x0201007f.
  - w00-shell has 4 parts (0, 3, 4, 5), 955 polys. The main w00 has 6 parts and 1313 polys.
  - Shell w00 part 0 spans x -6240..2699, y -3322..8082 (main: -9855..8699, y -12610..17351, the outer boundary).
  C
- m19 comparison: m19a03d-a-w00 parts 0 / 5 / 6. Its w00-shell keeps the same ids 5 / 6 (plus gimmick parts
  11..16, 50..52), so shells carry the toggle parts there too. m19's camp has no shells either. C

## 4. 4U code that tests stage 8 (Q4)
Stage id = [[0xfb6b7c]+0xc8c] & 0xff (scan: stage8.py, base register verified unless noted).
| site | function | effect |
|---|---|---|
| 0x6c5a94 | stage init 0x6c5a74 (switch on stage) | case 8 -> aMap08 (0x657040) C |
| 0x76db24 | uEm024 slot 40 (0x76da88) | stage 8 and k00 (area 1, mId 1) not broken -> W+0x539 = 2 (0x91b268) C |
| 0x8a00b4 | uEm083 slot 40 (0x8a0050) | same C. W+0x539 is a frame countdown (0x916d78) that, while non-zero, skips shared routine 0x933b30 (timer logic, default 600; purpose not traced) |
| 0xb83da4, 0xb858f8, 0xb9a258, 0xb9d3bc | UI code | (128, 128) -> (58, 64) in a map-to-screen transform (0x6c40e0 / 0x6c5678 map dims). S: minimap offsets |
| 0xba355c, 0xba358c | UI 0xba3xxx | stage 8 -> own branches 0xba3610 / 0xba37b0 (layout floats). S (base reg [r11] not resolved) |
| 0x6634f8 | 0x663474, switch on stage | case 8 (also 15) -> r6 = 7, r5 = 1 (purpose not identified) C (value) |
| 0x98cac0 | 0x98ca94 | stage 6 or 8 -> skips a block (not identified) |
| 0xb30a5c | 0xb2f73c | stage 8 -> f32 2.0 instead of r9 at sp+0x10 before 0xc088d8 (not identified) |
| 0x306410 | 0x3056bc | stage 8 and mapped area 0 (camp) -> extra block (not identified) |
- False positives of the scan: 0x1ce768 (compares +0xc90), 0x2fc3bc / 0x2fc830 (not the stage global),
  0xb6bd04 (compares a player byte). Unverified: 0xb6c6e8.
- em ids met: factory 0x690828 (em024 / em110 -> uEm024), 0x691118 (em083 / em111 -> uEm083); shared HP
  0x9201a0 (24 / 83 / 110 / 111); in-class: 0x76e784 (partner 83 for 24, else 111), slots 78 / 79 (0x7751cc /
  0x7751a4) act only when W+0x1c0 != 24 (Shah), slot 48 0x773324. C

## 5. Sound (Q5)
- bgm_st_08 (sound\bgm\stage, 4U STRQ v0x22, type 0x3a6a5a4d): 2 streams, 13 sequences.
  - Stream 0 = bgm_em024: 97.1 s, loop 960624..3176969 at 32728 Hz.
  - Stream 1 = bgm_em024_2: 94.9 s, loop 652680..3106944.
  - Sequences 0..10 have no stream (control rows). **Seq 11 -> bgm_em024 (-0.3 dB), seq 12 -> bgm_em024_2 (-0.5 dB).**
  - No bgm_map_08 jingle: request 10 is empty here, while every other 4U bgm_st_NN uses request 10 = bgm_map_NN.
  - So Dalamadur's theme is a stage theme (wav in sound\bgm\stage\wav), not in bgm_bat. The switch from phase 1
    to phase 2 is not traced (open). C
- str_m08 (sound\bgm\str_map\m08): 3 streams.
  - m08_a00d (28.7 s), m08_a01d (29.4 s) and com rain (26.2 s).
  - Sequences: id 0 -> a00d (-11 dB), 1 -> a01d (-10 dB), 20 -> rain (-6 dB). C
- snd_m08 (0x7bea3086) = 'CFL\0' v1, 6 short records (not decoded). snd_M08d (0x4a4b677c) = 'REV\0' v2 reverb
  presets (3). C
- Area banks: snd_m08a00d has requests 1, 2, 3 and waves m08_fire, m08_rock_fall_1/2 (the camp falling rocks
  use SE 2 / 3). snd_m08a01d is listed in section 2. sound\call\map\m08\m08_a0Nd (SES) not decoded here. C

## 6. Porting implications (Q6)
- **Host:** a GU 2-area stage (area-count table 0x162bbe8: ids 9, 10, 15-21, 25, 27). GU **m18d** is the closest
  fit:
  - its kod already holds exactly {1,1,0,0,200} {1,2,1,0,200} {1,3,2,0,200}, the 4U m08 table A layout;
  - m18d.arc ships m18a01d-k01..k03 schedulers + models.
  The other kod tables: m09 / m10 / m15 / m17 / m21 / m27 have a placeholder {0,0,0,0,50}, m16 one entry,
  m19 4 entries (2 of type 1), m20 2 (type 1), m25 three (vital 100 / 300 / 400).
  - What GU's own code does with m18's kobjs, and which stage m18 is, isn't checked (G).
  - The Battlequarters route (new stage 28 = alias of 26 with m28 paths) works the same way with a 2-area donor
    (new id 29 / m29 paths, or reuse 28 if the two ports never coexist: G).
- **Breakables:** convert 4U k00 / k01 / k02 to GU slots k01 / k02 / k03 (GU file id 0xbbdf + stage*52 + area*4 +
  k-1, created by 0x4fe9c0) with stage4u2gu convert_kobj:
  - drop the 4U Effect controller, kowareModel Draw 0 -> 1, keep SE area 1;
  - keep mIds 1..3: GU's action-0 start does the same part swap (2*mId-1 / 2*mId), so the 4U part ids carry over.
  - kod: 3 type-0 entries (S).
  - mType 9 / 10 / 11: check that GU's KowareObj code has no special case for them (open).
- **Trigger:** the ported uEm024 7/62 and uEm083 7/60 / 7/61 handlers must send GU command 0 at the 4U frames:
  - use 0x514f9c(kobj, 0, 0, 0) on the kobj found by (area, mId), the way module/stage_doors.c does;
  - EMC conditions 0x6f ids 1 / 2 need a GU slot (GU op 0x6f -> monster slot 133) answering "highest broken mId"
    and the shared-HP band.
  - MP: 4U sends the command from every machine's copy (0x6c3400 has no host test). With GU's "damage only on the
    controlling machine" rule, check that the action itself runs on every machine, or post the command from the
    owner + net (open).
- **GU quest-start broadcast:** GU sends cmd 0 to every kobj at quest start (0x42e8 -> 0x500cb4). That would break
  all three at once, so extend the stage_kobj_bcast hook (@0x500d18) to the alias's area-1 kobjs. C (GU, Gogmazios
  notes)
- **Collision:** convert all 5 a01 files (sbc.py). The camp has no shells, so duplicate g00 / w00 as shells (the m19
  camp rule) and convert a00-cam. Keep part ids. The fall planes (w2 0x2000) and the SIS exit (y -3350, r 10000)
  carry the "fall back to camp" behaviour; check that GU treats them the same (test).
- **Stage-8 specials to re-create on the alias:** W+0x539 = 2 while k00 is intact (both halves, slot 40), minimap
  constants 58 / 64 (GU map UI data instead: mapui4u2gu.py), and the unidentified sites in section 4 (camp block
  0x306410, 0x98ca94 skip, 0xb2f73c 2.0f, 0x663474 case 8).
- **Assets:** area models / sky / set schedulers, the area-1 sound bank and requests (11..18 used by the breaks),
  str_m08 streams.
  - The stage STQ's Dalamadur theme belongs with the monster's BGM (GU: battle STQR or the map STQR, as for
    Gogmazios). The 4U phase-2 switch needs tracing.
  - KowareEft 6 / 8 effects: identify list 0x23 elements 9 / 11 and post them at the break (GU has no
    KowareEft controller).
- **Missing in GU (engine):** a two-part monster with a shared HP pool and head-tail action sync (monster side).
  KowareEft stage effects are missing too (as for m19). The kobj command API itself exists. C
- **Walking on Dalamadur's body:** not in the stage data. Every m08 SBC part is accounted for above, so it's
  monster-side collision (open, monster study).

## Open points
1. EMC ops 0x0a / 0x11 that gate the break selector (head g0 s0 prefix).
2. The tail's path into 7/60 / 7/61 (head-tail sync struct at +0x8c88 / the flag written at 0x76e914).
3. KowareEft list 0x23 -> effect files. snd request id -> wave mapping.
4. bgm_em024 -> bgm_em024_2 switch condition.
5. Identity and engine behaviour of GU m18 (host candidate), GU KowareObj handling of mType 9..11.
6. Unidentified stage-8 sites: 0x306410, 0x98cac0, 0xb30a5c, 0x6634f8, 0xb6c6e8 and the 0x933b30 routine that
   W+0x539 suppresses.
