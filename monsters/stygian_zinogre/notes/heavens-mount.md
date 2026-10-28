# Heaven's Mount (4U stage 5, m05) as a GU stage alias, for Stygian's three Heaven's Mount quests

Built 2026-10-28 offline (no game test possible). C = read in code / data, S = strong, G = guess.
Tools: tools/build_heavens_mount.py (stage arcs, map_com, streams), tools/build_heavens_mount_ui.py (maps); build.sh
steps `stage`, `stageui`. Core: module/stage_alias.c (unchanged), allocations.toml `stage_alias = [24, 30]`,
package.toml [stage]. Precedent: monsters/dalamadur/notes/speartip-crag.md section 7 (same route, 2 areas).
Report: dump/converted/em049/heavens_mount_report.json. Previews: build_heavens_mount_ui.py --preview DIR.

## 1. Host choice: GU stage 24 (Ruined Pinnacle) -> folder m30
- 4U m05 has **9 areas** (camp + 8; 4U area-count table 0xe087b4[5] = 9, C; arcs m05a00..a08). GU has **no 9-area
  stage**: area-count table 0x162bbe8 = 2, 12, 13, 10, 10, 12, 11, 11, 12, 2, 2, 11, 11, 11, 10, 2 x 7, 12, 11, 10, 2,
  3, 2 (C). The 10-area stages are 3 (Arctic Ridge), 4 (Misty Peaks), 14 (Frozen Seaway: one of his quest stages,
  excluded) and 24 (Ruined Pinnacle). 4U area N = GU area N (N = 0..8): the 4U SIS ships unchanged; GU area 9 is
  left over (no 4U exit leads there: S, unreachable).
- Why 24 over 3 / 4 (C unless marked):
  - gimmick flags u16[stage] @0x162bd60: 24 = 0x101 (fewest), 4 = 0x111, 3 = 0x511 (bit 0x400 only on 3); none sets
    0x88 (SIS kind-3 / kind-6 ballista spawns) or 0x04 / 0x20 / 0x40 (Fortress gimmicks);
  - no night variant (3 / 4 have 103 / 104 and kinds 57 / 59, not redirected);
  - Arctic Ridge is a cold map (G for the hot / cold rule), Heaven's Mount is temperate;
  - quests: stage 24 hosts G4 singles (q11472 ...), the G4 two-hunt q11473 and q11488 (hunt all, with Zinogre: the
    stat base of his G4 multis); stage 4 has HR7 singles and the G4 q11404; no HR7 Hub quest is on 24;
  - stage switches in main (scratchpad stscan.py / jtcase.py over every `ldrb [.., #0x48]` switch): 24 takes the
    common case everywhere except 0xdd1a10 (a per-stage list lookup, own table) and 0x5003b0 (returns 1 for stage 24,
    area 2, byte +0x4b == 5; stage 4 has the same with area 7 / +0x4b 3; caller 0x2ad964): both hosts have such sites,
    their meaning is not traced (G).
- Folder 30 (pools.stage_folder; 28 / 29 taken), `tools/alloc.py check` OK.

## 2. What was converted (per area / file kind)
| file | content |
|---|---|
| a00..a08.arc (from GU m24 aNN) | main model m24aNNd <- 4U m05aNNd; set schedulers -a00.. <- 4U sets: a00 {a01, a02, a03, sky}, a04 {a00, sky}, a08 {a00..a03, sky}, the others {a01, sky}; filter -f: GU's minus its props (uBaseModel sky_normal, Grass2, MhBillboard-kiri), 4U lights / fog / bloom / colour, Speartip's light rule (GU-only lights off, EM02 kept); area SE = 4U bank / request / waves / call (snd_area) |
| a09.arc | GU m24 a09.arc unchanged (17.6 MB copy, shipped so a request for it still finds a file) |
| m30d.arc (GU m24d) | GU kobjs a03 k01, a04 k01 / k02, a07 k01 / k02 dropped with their models; 4U m05a06d-k01..k04 -> m24a06d-k01..k04 (hit-breakable rocks: mAt* spheres, mId 1..4, mType 13 / 14 / 15 / 0, models); 4U m05a08d-k00 -> m24a08d-k01 (mId 8, 12 actions ids 3..14 with reactType 3..6, model -s00 + 3 ScrollCollisionSbc whose SBCs ship at their 4U paths); STQR bgm_m24d = 4U str_m05 (sequence = area: 0..3 own, 4 -> a03d, 5..7 own, 8 -> a01d; GU 9 / 10 -> a01d; 0x32 m24cmpd stays GU's), 7 opus at sound\\bgm\\map\\m30d\\wav\\m30_aNNd |
| map_com m30.arc (GU m24) | collision 5 kinds x 9 areas (4U; missing shells: a00, a04 both, a08 g00 -> main files); SIS verbatim; item pops 4U m05d (IPS + IPL low / high / g); PEL m24_000 / _100 emptied; whole-map offsets 4U (W 60000); kod = 4U state table A {6, 1..4, bits 0..3}, vital 100 (G); relation a01..a08 regenerated from the 4U floors; point_pos a01..a08 from the 4U SIS (section 4), a00 / way_point = GU's empty forms; area_patrol emptied; camera XFS of areas 0 / 2 / 5 / 7 / 8 removed |
| mapUI m30d aNN_ui (5 languages) | 4U area pictures + exit labels (4U digit glyphs / camp icon); areas 0..3 at 2x with 4U records (maprec); 4..8 resampled to GU m24 records; GU exit highlights moved off-screen; a09 GU's |
| map_com m30_<lang> | 4U m05d_ID at 2x (k 1.0), highlights area01..08 = 4U ui255 panes, area09 off-screen; 58 / 64 SIS points on the art (every arrival; off: far section-0 points and one a06 exit at the art's edge) |

Shared tools touched (additive, other monsters' outputs byte-identical: Speartip 6 files + Battlequarters 6 files
rebuilt into dump/scratch/hm-check and cmp'd): stage4u2gu read_mesh_4u (4U vertex format 0x82917009, 24 B = the 28-B
layout without colour, as tools/efl4u2gu EFX_4U; m05a02d -sky00 / -river), snd4u2gu bank_ent_gu (4U byte 2 = 0 on
m05a08d's bank, written 0 as before), sbc.parse / convert_4u (m05a01d-a-cam: two BVHs, no grid: AABBs rebuilt by the
game rule, 1 x 1 grid, first BVH kept, G).

## 3. Monster route data (Stygian's area files, build_em057_01_arc.py alias_routes)
- GU Zinogre's own map-24 records describe the Ruined Pinnacle graph. They are rebuilt from the 4U area graph (SIS
  exits, made two-way: 4 -> 3 is a one-way drop for hunters): 1 [2 3 5], 2 [1 6], 3 [1 4 5 8], 4 [3 5 6 8],
  5 [1 3 4 6], 6 [2 4 5 7], 7 [6], 8 [3 4] (C). area_select: every neighbour, equal shares, Status 0 only (G: GU's
  Status-4 rows have no 4U source); area_link kinds 1 / 2 / 4 = BFS hop counts (G for kind 4). Area 4 (the vine
  climb) is taken out (build_em057_01_arc.py HUNTER_ONLY): no 4U monster enters it (user 2026-10-28; test 2026-10-28
  he jumped from 6 into 4 and looped there) -> 3 [1 5 8], 6 [2 5 7], 8 [3]. area_eat / map_info
  stay Zinogre's. Only these two files of em057_01.arc changed (cmp of the 813 entries).
- 4U keeps no route data (its AI walks on SIS + collision, S); no GU monster roams this graph.

## 4. Deviations and guesses
- DEVIATION: GU area 9 exists (GU's files) with no 4U counterpart; unreachable (S).
- Monster entry / exit points (test 2026-10-28: with GU's empty point_pos he entered area 7 at his area-6
  coordinates, map icon outside the map, after one huge jump): point_pos of areas 1..8 are built from the 4U SIS
  (build_heavens_mount.py point_pos_4u). GU reads them for Zinogre's move type 2 (area_act_tbl entry 44 = [2, 2, 6,
  5], group 0; C): exit 0xb3640 = the current area's point with flags bit 1, area = next, the asked variant (0 = the
  edge the route follower 0x97130 walks to, 2 = the far point of the exit script, 0x8f460); entry 0xb3e4c = the next
  area's point with flags bit 0, area = the one left, variant 0; none found = no write (the old position stays). Per
  4U neighbour: far = the SIS exit centre toward it, edge = the SIS arrival from it (hunters' points: 4U keeps no
  monster points, S), angle = the arrival facing; + one flags-0x34 point per area (types 0 / 1 / 5 / 6 / 8). Record
  layout in the tool. G: the walk / jump between edge and far point is GU Zinogre's own motion (4U's area-6 -> 7 exit
  is a climb of several wall jumps, user 2026-10-28; GU's exit script is one move).
- DEVIATION: way_point stays GU's empty form (no 4U waypoints: the route follower walks straight to the edge point);
  area_patrol emptied (no patrol walks).
- DEVIATION: the partners (Rathalos, Seltas Queen, Seltas, Gore Magala) use their own GU map-24 area files = the Ruined
  Pinnacle graph, which differs from 4U's: a partner may move to an area not adjacent in 4U (arrival point: G).
- Weather (test 2026-10-28: area 1's lighting / lightning wrong): 4U -f01 of areas 1, 5..8 is the area's weather
  cycle (1000 frames, StageDataSet Weather-* keys: clear 0..100, change, storm 300..400 with the gradient filter on and
  colour corrector 3 = the flash at 200..300, back by 600). GU runs the same system (Ruined Pinnacle areas 1, 2, 5..8
  carry Weather-* keys; 15 GU stages do), so the GU -f of those areas takes -f01 (build_heavens_mount.py
  port_weather: scheduler length, Weather-* keys, MhFilter state / position keys, all 4 colour correctors: GU's last
  element cloned). G: GU's area 2 keeps its own Weather-* keys (4U area 2 has no -f01) over 4U's static values.
- DEVIATION: the -col / -e0N Effect schedulers (incl. a08's effect models qe000_001 / ef_m05a08) not ported (GU lacks
  the Effect controller); 4U grass (Grass2 in -f01) absent.
- Area 3: 4U mesh XfBAW_1__m00_52 (31 vertices, unlit rock00 over a 6700 x 2900 x 6300 span, vertex alpha 0
  everywhere) is dropped (stage4u2gu hidden_4u; S: 4U draws nothing with alpha 0, GU's template ignores it and drew a
  flat fogged sheet, test 2026-10-28). The only such mesh of 1836 in m05 / m08 / m19 (C).
- Board name: his stage-24 quests show 4U's "H. Mount" (mapName[5], 5 languages) instead of "Ruined Pinnacle"
  (module/stage_alias.c stage_name hooks, tools/stage_name_em057_01.py, allocations.toml append.stage_name). The
  board's detail panel reads table 0x1634c00 (hook stage_name_board @0x613410; the first two hooks alone did not
  reach it, test 2026-10-28). DEVIATION: the board's stage picture (words 0 / 1 of 0x1634c00 / 0x1634804) stays the
  Ruined Pinnacle's.
- DEVIATION: area maps 4..8 use GU's records (core limit, section 5): pictures resampled x0.75..1.23 of 2x; a06's
  label "7" falls outside the frame. GU exit highlight overlays hidden, no arrows; a02's second picture (map2) unused.
- G: kod vital 100 for the four rocks (4U keeps mLevel 1, no vital); what breaks them in GU = the same class's hit
  spheres (S). k01's 4U model Draw 0 is forced to 1 like every converted kobj (stage4u2gu rule).
- G: a08 k00 (mId 8): its 4U trigger is not traced; GU's quest-start command 0 finds no action 0 (ids 3..14), so it
  stays at frame 0 unless GU's KowareObj reacts to hits by reactType (not checked).
- G: collision group flags kept as converted (sbc.convert_4u); relation of a08 has floors 0 / 2 only (no floor 1, no
  direct pairs).
- GU-only kept: stage SE snd_m24d, pec_m24d, snd_fs_ase24, setItemData m24d, stage shells, the GU view / ambience code
  of stage 24 (section 1 sites).

## 5. Core module: what it still needs (not changed here)
- **maprec for more than 4 areas**: module/port.h `map_k[4]`, `map_x[4]`, `map_y[4]`; module/stage_alias.c
  `static uint32_t s_maprec[4][MAPREC_SIZE / 4]`; module/build.py monsters_c pads to 4 and stage_alias() asserts
  `len(maprec) <= 4`. Raising all to 13 (GU's table holds 14 pointers per stage) would let areas 4..8 take 4U's
  records and 2x pictures like 0..3 (then build_heavens_mount_ui.py MAPREC_CORE = 9 and package.toml maprec gets 9
  rows).
- hold_kobj_areas is a u8 mask (areas 0..7; build.py asserts `< 8`, stage_alias.c returns for area >= 8): fine here
  (area 6), a limit for any alias with breakables in area 8+.

## 6. Test (when possible): what to look for
- Log: `port: stygian_zinogre stage path kind 54/56/58/49/55 area N -> m30`, `area map record area 0..3 -> k ...`,
  `whole map record -> k 1000/1000`, `stage: quest-start command 0 held for area-6 KowareObj .. (mId 1..4)` x4.
- Visual: every area = 4U Heaven's Mount geometry, sky and lighting; area 6's four rocks standing and breakable;
  maps show the 4U pictures with labels; area changes follow 4U's exits; Stygian changes areas along the 4U graph.
