# Black Gravios port: plan (draft 2026-10-31)

Source: MH4U em041 (class uEm038, shared with Basarios em038, Ruby Basarios em039 and Gravios em040). Target: GU's
Basarios / Gravios class uEm004_00, **variant 1** of Gravios (GU ID 0x105, arc `nativeNX/arc/enemy/em005_01.arc`).
Same route as Tigerstripe Zamtrios and Stygian Zinogre (their notes/plan.md). Process: notes/porting-guide.md.
Confidence: **C** confirmed in code / data, **S** strong, **G** guess.

## Phase 0: identification
- 4U em numbers (C, 4U emName): 38 Basarios, 39 Ruby Basarios, 40 Gravios, 41 Black Gravios, 115 'Gravios' again.
- 4U class (C): no uEm040 / uEm041 DTI exists. uEm038 (DTI 0x10b70d0, vtable 0xe67ccc, slot-44 dispatch 0x807e5c)
  holds every em-38..41 test: `ldrb [.., #0x1c0]` followed by `cmp #41` at 7ffb8c 805320 805920 808fb8 80910c
  8091f0 919c38 9303bc 931e80 (scan of tests within 6 instructions of the load: under-counts, as Tigerstripe's did).
  808fb8 tests `41 || 115 || 40` together: what em115 is stays open (G: a quest-only Gravios variant).
- GU (C): Gravios = em 0x5 (em005_00), registry index 113; Basarios = 0x4, index 112. Both registry entries point at
  DTI 0x18518f8, which GU's static init at 0x503d8 builds with the name "uEm004_00" (gu_pcrefs). 0x105 is free.
- Size record (C, 4U 0xf32008 + 16 x 41): 2098.7 cm, 0.97 / 1.17 / 1.23 (package.toml [size]).

## IDs (allocations.toml)
| what | value | note |
|---|---|---|
| GU ID | 0x105 | em 5, variant 1 |
| registry index | 144 | after Stygian Zinogre 143 |
| save slot / name entry | 111 / 111 | `dummy7`, the last free slot |
| Notes entry | none | save bits 123..127 all taken: `notes = false` (tools/alloc.py); a Notes page needs new save bits (open) |
| UI icon | 204 | 4U icon 43 (its quests' board icon; Gravios' is 42) |
| file IDs | 0x10900..0x1093f | |
| quests, items, gear | later | quests need the placement decision below; items / gear counts come from the 4U tables |

## 4U quests with Black Gravios (C: dump/romfs/loc/data/quest00 / 01.arc, spawn list +0x28)
| 4U | title | stage | spawns (em, area, byte +0xF) | fee / reward / sub |
|---|---|---|---|---|
| m00902 | Black Rock Down | 15 V. Hollow | 41 (a8, 0) | 900 / 8100 / 2700 |
| m00911 | Advanced: Whale of a Hammer | 15 V. Hollow | 41 (a8, 1) + 41 (a7, 1) | 2100 / 20400 / 6800 |
| m10601 | Ore D'oeuvre | 3 Primal Forest | 41 (a5, 0) | 1300 / 12000 / 4000 |
| m10606 | Advanced: Dance with Dragons | 15 V. Hollow | 41 (a8); wave 2: 12 (a4); wave 3: 44 (a2) | 2300 / 22200 / 7400 |
| m10611 | Advanced: Armor Amore | 15 V. Hollow | 40 Gravios (a8, 2) + 41 (a9, 3) | 2000 / 19800 / 6600 |
| m10615 | Advanced: Gravios Fortunes | 3 Primal Forest | 41 (a5, 2) | 1600 / 15900 / 5300 |
| m10923 | Hollow Promise | 15 V. Hollow | 41 (a8, 0) | 1700 / 16800 / 5600 |
| m10927 | Advanced: A Black Day | 3 Primal Forest | 41 (a5, 1) + 12 (a5, 1) | 2900 / 28200 / 9400 |
| m21006 | Grudge Match: Dos Gravi | 12 Arena | 40 + 41 (a1, 2) | 0 / 2700 / 300 (arena: as Stygian's m21003, probably dropped) |

- Both stages exist in GU (Volcanic Hollow 12, Primal Forest): no stage alias needed (S: GU stage numbers to check).
- Spawn byte +0xF 1 / 2 / 3 (frenzy / Apex states, GU has neither): settle per quest before building, as Stygian.
- m10611 has a real Gravios next to him: like Stygian's m10612, that quest needs `standin_alt` (S).
- Area data (open): GU Gravios' area files must cover both stages, else borrow another GU monster's (Stygian notes).

## First test build (2026-10-31, rebuilt on core 1.7.3 2026-11-01; static checks only, not played yet: the first
## attempt ran the old 1.7.2 subsdk1, log "7 monster(s)")
- 4U em041.arc ships em040's motions, camera, AI, sound call (em038) and effects byte for byte (78 files), and em041's
  attackdata / hitsize / bodydata equal em040's (C). So the arc (tools/build_em005_01_arc.py) owns only the models
  (body + tail: textures, MRL on GU templates, 'solid_sphere' with em041_03_BM as GU's own em005_00 binds it), the
  parts XFS (GU states minus group 19, group 50 hidden) and the dttune; everything else is GU Gravios' (em005_00 paths
  and file IDs, area data incl. map 12).
- dttune (C): GU em005_00's = the dt_convert of 4U em040 at 50 of the 51 bytes where em040 and em041 differ; ours
  takes em041's values there. Since core 1.7.3 dt_convert writes the 4U AI distance ranges (etd words 10 / 11, issue
  #11) at +0x18e: em040's and em041's are equal (2 rows, no offsets), GU keeps its own there (the "retunes" seen at
  +0x1b0 under 1.7.2), and past them GU's file ends with the em041 conversion's tail.
- Supply box (core 1.7.3 quest4u.supp_4u, generalized 2026-11-01): 4U list entry byte +1 = slot count; box = kind 0 +
  kind 1 slots (12 + 20 or 8 + 24 in every Black Gravios quest), delivery = kind 3 (8), kind 2 always 0 slots (S).
  Gogmazios' boxes stay byte-identical. Reward slots 3 / 4 = GU's empty rem_000000 (Stygian's issue #8 fix).
- tools/emdata4u.py parse_xfs_states now follows the object layout: its byte scan misread GU em005_00's array size
  0x5e0 as a group object (16 more GU XFS failed the same way); the 104 GU files it read before give the same states.
- Quest 10780 = 4U m10611 Advanced: Armor Amore on GU Hub HR7 (template q10707, stat base q10767): Gravios 0x5 rows
  54 / 90 / 86, Black Gravios named by Basarios 0x4 (standin_alt) rows 54 / 92 / 86, subquest sever the tail (8, 0x105,
  7), board icons Gravios 121 / ours 208.
- Deviations of this build: em041's own effects (MEF em041_1, em041_002 / em041_101, ef_em041) not in, GU Gravios'
  play; emd word-32 colour table not ported (no known GU field); rewards: B.Gravios Carapace / Scalp -> Gravios
  Carapace / Scalp (TEST STAND-INS), 4U Gravios Shell has no same-name GU item (its 10 % went to row A's top item);
  4U spawn bytes +0xF (Gravios 2, Black Gravios 3) dropped; GU carves (hagi) are Gravios'.
- To watch in the test: variant 1 in GU's uEm004_00 (no Phase 1 map yet: GU may branch on the variant byte), the
  look of the converted model (no normal maps, as Tigerstripe), the quest board name of the Basarios stand-in.

## Content 0.2.0 (2026-11-01, static checks only; quest 10780 with 0.1.0 played: he spawns and fights, user)
- Materials (C): 4U 565 566 1469 1470 1471 (B.Gravios Carapace / Scalp / Cortex / Crown / Pallium) -> GU 3036..3040
  appended (tools/items_em005_01.py); the quest rewards use them (the 0.1.0 Gravios stand-ins are gone).
- Break rewards (C): GU Gravios' conds 10 / 20 / 30 / 40 / 50 = 4U em040 groups 0 / 2 / 3 / 4 / 5 (same item mixes);
  em041's own groups there -> BUI2 / BUI4. 4U groups 1 / 7 (Frenzy) and 6 (Deviljho items) left out.
- Carves (C): 4U em041 body / tail / shiny, High in hagi s2, G in s4, GU em005_00's layout (tools/hagi_em005_01.py).
- Armor (C): 4U Gravios U (HR) and Gravios Z (G), the 4U sets crafted from Black Gravios (no "Black Gravios" set
  exists in 4U): models 185 / 186 / 394 / 395 (free in GU), templates GU Gravios / Gravios X, defense scaled by the
  plain Gravios S -> GU Gravios and Gravios X -> GU Gravios X ratios. 4U Flame Aura (torch effect) dropped: no GU
  tree (DEVIATION).
- Weapons (C): the 6 4U lines of his materials (18 weapons, tools/gear_weapons_em005_01.py docstring): SnS Red Demonic
  / Efreet's Flame (4U's Black Doom / Red Divine Flame before them are GU weapon 114), Hammer Venom Crater line, Lance
  Black Gravios Spear line, HBG Gravios Roar line, GL Black Gunlance line, DB Melting Wail line. 4U weapons of other
  lines that only add one Black Gravios part are not ported. Dalamadur's recipes still substitute B.Gravios ->
  Gravios (gear_weapons_em090.py): could now name ours (Dalamadur's call, not changed here).
- G quest 11430 = 4U m10923 Hollow Promise (Hub G2 -> GU Hub G4): template q11443, ratio over 4U m10904 (G2 Gravios,
  same stage), base GU q11438 (G4 Gravios): rows 107 / 109 / 97; subquest wound the chest -> GU code 3 (S).
- Core tools: quest4u.supp_4u reads the 4U list's slot counts (Gogmazios' boxes byte-identical), SUPP_GU_NAME Water S.
- Quest 10781 = 4U m10601 Ore D'oeuvre (Hub HR6 urgent -> GU Hub HR7, regular: an appended quest gates nothing):
  Primal Forest = GU stage 13 (S, Stygian's vote), template q10739, ratio over m10524 (HR5: 4U has no HR6 single
  Gravios, G) -> rows 57 / 98 / 86; wound the back -> GU code 2 (S).
- Quest 1025 = 4U m00911 Advanced: Whale of a Hammer (caravan ★9 -> GU village ★10): two Black Gravios (frenzy byte
  dropped), template and base q1035 (village ★10 "hunt 2 Gravios", stage 12), ratio 1 over m00903; deliver 2 Coal.
- Not built yet: m00902, m10606, m10615, m10927 (+ arena m21006).

## 4U data em040 vs em041, all of it (C, 2026-11-01)
em_data em041 vs em040: emd 24 bytes (word-32 part colours, darker; no GU field), etd 60 bytes: word 5 part
table (2 B), words 7 / 8 per-part tables (47 B; em041 zeroes many values) -> all in the dttune via dt_convert; word 24
(10 B, lower values in em041) -> dttune +0x358 by unconverted_blocks (role G: durations of a repeated condition);
header word 4: em040 points to a 52-byte record list (GU em005_00 holds the same record at +0x4ee),
em041 to an empty list (ff ff): role unknown, NOT ported (open). Attack / hit / body data, motions, command table,
sounds, effects: byte-equal. So his attacks differ from Gravios' only by the quest attack row (ported per quest) and
the two code branches below.

## 4U behaviour of em 41 (static read 2026-11-01, S; full Phase 1 map still open)
Of the 9 `cmp #41` sites in uEm038, 7 treat em 41 exactly as Gravios em 40 (7ffb8c 808fb8 80910c 8091f0 919c38 9303bc
931e80: shared branches, rank-5 G-rank tweak, sound 213 posts, state setup). Two are his own (with em 115):
- 805320: in an attack's frame check, posts effect request 8 (0x809ae0(this, 8, 0), kind 50) when the state flag
  [+0x8c88]+0x28 bit 1 is set and bit 2 is not; Gravios never posts it there.
- 805920: in the attack that fires shells 45 / 46 / 47 (1 or, from rank 5, 3 of them), em 41 always runs 0x808410(1):
  at its frames effect 6 (with 8 if flag bit 2) and shell 26 (57 if bit 2), plus sound 216; Gravios runs it only when
  the flag says so. So no new move: an extra heat burst / effect on two existing attacks (which attacks: G).
Both sites are in the beam handler 0x8050e0 (C, 2026-11-01), every frame of its step 1 (805918 is reached from both
the volley and the no-volley path): frame 10 effect request 8 (state bit 2, not 4); 0x808410(1, 120): frame 120 effect
request 6, frame 140 attack 26 (57 with state bit 4) = the heat burst after the beam; sound 216 at 120. So his beam
ends in a heat explosion Gravios' does not have. Ported (module/em005_01_beam.c, hook GU d2e3ec in GU's beam handler
d2e0b4 = 4U 0x8050e0, C; same frames in both games, C; effect ids as GU's own copies post them, S; sound not ported, G).

## Next
1. User: placement of the quests (hub / village rank, which ones; m21006 or not), then quest IDs from the free lists
   in monsters/stygian_zinogre/notes/quests.md section 3 (pool extended in allocations.toml).
2. Phase 1 variant map (as monsters/tigerstripe_zamtrios/notes/phase1-variant-map.md): every 4U em==41 site in
   uEm038 against GU uEm004_00's variant handling.
3. Phase 2: arc em005_01.arc from 4U em041 (build_em067_01_arc.py as template), name, build.sh.
