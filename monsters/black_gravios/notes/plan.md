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
| quests | 10780 11430 10781 1025 1056 10782 10783 11451 | 4U m10611 m10923 m10601 m00911 m00902 m10606 m10615 m10927 |
| items, gear | 3036..3040; [monster.append] | materials; armor / weapon records appended (allocations.toml) |

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
- 0.3.0 (PR #12 review): 1056 = m00902 Black Rock Down (village ★10, template / base q1003, r = 1, wound back -> 2),
  10782 = m10606 Advanced: Dance with Dragons (HR7, 3 waves, hunt all: template q10742 re-staged 104 -> 12, small
  monsters of q10707, base its 0x39 record, r = 1, Brute Tigrex -> Tigrex: texts and B.Tigrex rewards -> Tigrex items),
  10783 = m10615 Advanced: Gravios Fortunes (HR7, capture, as m10601, wound head -> 1), 11451 = m10927 Advanced: A
  Black Day (G4, + Tigrex, template / base q11487, r = 1, Tigrex claws -> 2, C: q11405). Arena m21006 not ported.

## 4U data em040 vs em041, all of it (C, 2026-11-01)
em_data em041 vs em040: emd 24 bytes (word-32 part colours, darker; no GU field), etd 60 bytes: word 5 part
table (2 B), words 7 / 8 per-part tables (47 B; em041 zeroes many values) -> all in the dttune via dt_convert; word 24
(10 B, lower values in em041) -> dttune +0x358 by unconverted_blocks (role G: durations of a repeated condition);
header word 4: em040 points to a 52-byte record list (GU em005_00 holds the same record at +0x4ee),
em041 to an empty list (ff ff): role unknown, NOT ported (open). Attack / hit / body data, motions, command table,
sounds, effects: byte-equal. So his attacks differ from Gravios' only by the quest attack row (ported per quest) and
the two code branches below.

## His AI (PR #12 review: "13 moves never appear"; read 2026-11-01, C unless marked)
My earlier "AI byte-equal, so no own moves" was wrong: em041.arc ships em040_cmd, but the script branches on the em
number itself. EMC op 0x46 = a switch on the em number (cases 38 / 39 / 40 / 41 / 115; GU's em005_00 / em004_00
tables have no op 0x46 at all):
- g0 s2 (top selector): case 41 jumps (op 0x20) to selectors 0x11 0x12 0x10 0x07 0x08 0x09 0x0a, 0x14 / 0x0d / 0x0d
  where case 40 takes 0x0e 0x0f 0x10 0x07 0x08 0x09 0x0a, 0x13 / 0x0b / 0x03: his own attack weights.
- g1 s39 / s70: case 41 native 7/71 where 40 / 115 / else take 7/57 (GU: both run d2da3c, r1 = 2 vs 0).
- g1 s65..s73 (11 sites): case 41 native 7/79 where else takes 2/3 (GU: 7/79 -> d2ef2c).
GU uEm004_00's attack dispatcher d2fa94 (switch on num 0..90, cat 7) has its own handlers for 7/57, 7/71, 7/79 and every
other 4U cat-7 action of em040_cmd (only 6 numbers go to its default d2ffc0). GU's em005_00 AI is GU's own rewrite
(group 1: 95 scripts vs 4U's 74, ~60 of the shared 74 differ; GU-only area-move style scripts appended) and never calls
7/71 / 7/79. Decided and built in 0.4.0: section "His own AI and effects" below.

## His own AI and effects (0.4.0, 2026-11-01; static checks only until the test log)
GU's AI language (C): GU's EMC op handlers = jump table 0x837ac (entry + table address). 0x46 and 0xa6 -> 0x8470c
(no-op: a 4U 0x46 block would run every case body in turn); GU's 0x91 (0x852bc) = switch on the em number (this+0xb5f4,
5 for Gravios and Black Gravios alike), 0x92 = switch on the variant (this+0xb5f5); 0x83 (0x89d34) = if this+0x1068
bit 6 (0x81f90; meaning G), an op 4U's table already uses 9 times. GU's em005_00 table = GU's rewrite of em040_cmd:
4U's 0x46 blocks became 0x91 blocks with case 4 (Basarios) and the else only (g1 s0 s6 s8 s65), so every case-41 body
is gone; GU emptied what its Gravios no longer uses (`a6 ff`: g0 s20 = his G-rank selector, g1 s35 s39 s42 s44 s45
s59 s60 s61 s70 s71); dropped 4U's rest bodies (op 0x80, GU's handler always skips them) and 3/7 in g0 s2 / g6 s0;
added 0x83 turn-away wraps (23 scripts), the selector g0 s22 (via a 0x4b test in g0 s2), 1/2 in g4 s0, another op-0x01
value in g12 s0 (0x12 -> 0x16, meaning G), group 16 removed, and its area language (g0 s0 s1 s4, g20 s0; scripts 74..82
= area_act_tbl entry 113: wait, move, sleep, meal, dive kinds, move types 2 / 2 / 3 / 3, group 15). GU's uEm004_00
code (0xd25000..0xd32000) reads only the em number, never the variant (C: no `#0xb5f5` there).

Approach (a), built (tools/build_em005_01_arc.py cmdtbl(), own file 0x10909, manifest field 37): 4U em040_cmd with
every 0x46 block reduced to its case-41 body (Stygian's rule), GU's g0 s0 s1 s4 and g20 s0, GU's (empty) group 16, GU's
g0 s22 and g1 s74..s94 appended; asserted: no 0x46 / 4U 0x91 left, no 4U area op in a script GU changed, the scripts
GU's taken / appended group-1 scripts call equal GU's, every GU entry number present. em 41 differs from em 40 in
g0 s2 g1 s39 s65..s73 (C). His own selectors (g0 s2 case 41): 0x11 0x12 0x10 0x07..0x0a, rank 5 0x14, rank 2 0x0d,
else 0x0d (Gravios: 0x0e 0x0f .., 0x13 / 0x0b / 0x03). (b) was dropped: GU's table has no trace of his selectors.

Dispatch check (C, unicorn emulation of 4U slot 44 0x807e5c and GU slot 125 0xd31128 for every native of both tables;
handler pairs by motion / attack sets): every action his table uses reaches the GU handler of 4U's handler with 4U's
parameters, among them 7/57 7/58 7/71 -> d2da3c r1 0 / 1 / 2 (= 4U 0x803e6c, motion 1084; GU keeps all four r1 == 2
branches), 7/79 7/80 -> d2ef2c (= 0x805eec: motions 562 7 1042 1045, attack 72), 7/28 7/31..33 7/42..45 -> d2d3a0
(= 0x8036f0: motions 1049 1079 1082 774), 3/7 -> d29e6c (= 0x7fe678), 2/13 -> d28d18 r1 1. Differences:
| actions | 4U | GU | his table |
|---|---|---|---|
| 1/38, 1/41 | 0x8011a4 (0, 1), 0x800b24 (3, 1) | 0xca10c = END | only g16 s0 (rest): group dropped, DEVIATION |
| 7/75 76 82..85 | 0x803230 (r1, r2 = 1 / 2): shots 33 / 50 via 0x8081b0 -> 0x661f6c | d2d194 (r1, 0): GU dropped r2 and the shots | only g1 s59, which no script calls (who picks it in 4U: open, G): not ported |
| 7/25, 7/30, 7/56, 2/16, 1/10 .. 1/36, 6/0 .. 6/4, 7/0, 7/8, 7/9 | 4U handlers | GU's own handlers (same motions where checked) | used by GU's Gravios table too: GU's version kept (S) |
Reachable from his selectors (C): g1 0..2 6..9 11 12 21..27 31 32 34 38..42 47..51 54..57 61 68..70; scripts no script
calls (3..5 10 13..20 ...) are picked by code (GU keeps their numbers: same numbers, his 4U content).
4U em==41 sites beyond plan.md's list: 0x800e60 in 1/18 (0x800d60): stamina cost 0x93bac0(1, 20) for em 39 / 41, 30
for 38 / 40 / 115; GU d27c8c calls 0x9cf7c(this, 1), cost = float [this+0x75f0]+196 (a per-monster data record, field
not identified): not ported in 0.4.0; ported in 0.4.1 (hooks d27d58 / d27d64, see "Found and fixed in 0.4.1").

Checks of the three gaps (2026-11-01, before the first 0.4.0 test):
- Group 16 (4U rest script) never runs in GU (S): every write of the think group byte this+0x72fc (153 sites) stores
  0, 1, 2 or 18 or restores a saved pair (this+0x7340 / 0x7350), and the group accessors 0x825ac / 0x825d0 / the
  direct reads ask for 3..14 and 17 only; GU's own Gravios table has no group-16 entry. Taking GU's empty group is
  GU-equivalent; nothing to port.
- g1 s59 (7/75 7/76 7/82..7/85, the shots): no script calls it (no token names 59 at all, C); no 4U code stores 59
  as a script number (every `mov #59` before a call in 4U is an attack / action / motion number: 0x933144 0x914dfc
  0x94ef9c 0x94d788 0x94e350, S); GU emptied it (C). Not ported; the action log would show 7/75 .. 7/85 if anything
  picks it.
- 1/18 stamina cost: the 4U difference is C; GU's cost record [this+0x75f0] is not a normal manifest field (field 36
  is -1 / -2 in GU's manifests, the loader callback slots this+0x7698..0x7710 do not map 1:1 to fields), so its file
  is unknown: the diag logs its values (+196 / +200) at BG's first dispatch to settle it after the test.

Effects (C, effects() / psl_merge(), own files 0x1090a..0x1090c, fields 17 20 22): em041.arc loads MEF em040_0 (ids
0..1032) and em041_1 (28 records 2004..2062, on em040_002 013 200 201 and em041_002); the shared 4U motions name the
20xx ids in banks 2 (motions 3 4 19 21 24 27 30 33 46 50) and 4 (59 60), so only Black Gravios plays them. GU renumbered
Gravios' motion effects (PSL kind 3 = PEL c list 1, ids 0..3000; kind 4 = PEL u list 1, ids 230..390; C). Ours: PEL u =
GU em005_00u + his 28 records in list 1 (GU's list 2 = class posts unchanged); PSLs 2 / 4 = GU's with his slots added
at 4U's frames (GU's motions there have 4U's frame counts, asserted; slots GU's mask and runs leave free); his EFLs and
their resources converted under 4U paths (efl4u2gu effect_set, Volcanic Hollow soil median). Not in: 4U em040_0's own
records (GU's versions play), em041_101 (converted, no record names it), 4U ids without a record (2008..2011
2017..2020 3002 1100: none in 4U either).
Test log: lines "bgport: em005_01 action c/n (motion m)" (module/em005_01_diag.c, hook d31128) show his picks.

Test 1 of 0.4.0 (2026-11-01, user log 19-21-37: 11430 for 1:40, 10783 to the kill): his AI ran (7/73 beam, 7/89, 7/50,
2/14, 1/17, 1/9); the diag logged the first quest only (fixed: per quest). User: (1) "killed, nothing happens"
(10783: the tally and the clear ran, kill not logged: open, asked), (2) "the new spit to the ground has no animation",
(3) "explosion and sleep gas at the same time", (4) mouth fire and the head / body effects after the explosion look
wrong. Found and fixed in 0.4.1 (C unless marked):
- MEF byte 0 is a condition bit: 4U's motion-effect component (this+0xc78; post 0x391a18, check 0x391a7c / 0x391b18)
  posts a record only while bit b0 of its mask (this+0xca8) is set; the handlers set it per frame for their variant
  (r1) and the component clears it after the frame (0x393524). All 28 em041_1 records have one (1 2 6 7 9 10), so
  both variants of every pair played at once. Action -> bit from the 4U dispatcher emulation + the handlers' stores
  (7ff4a8 801d94 / table 0x802084 80270c 802b38 8031dc 8036d8 803e24 804490 805100 805c74 805f18 807958); GU keeps the
  idea only as this+0xb5f8 = 1 / 2 in d2ef2c (7/79 7/80). Gate: module/em005_01_fx.c, mid hook 0x70050 in uFestaEnemy's
  PSL post (exit 0x7016c), its record table asserted against the MEF by effects().
- Beam burst: frame 120 posted GU message 3, which is GU's gas (d2ba30's request-8 message: 4U 0x802498 posts request
  8 = (50, 8) = em040_020 unconditionally and the burst only when heated); 4U's burst effect is request 6 = (50, 6) =
  em040_013 + sound 216, and GU posts no effect for request 6 anywhere (its bursts are attack 26 / 57 alone). Frame 120
  post removed; attack 26 / 57 at 140 stays. Repeated bursts in 7/89 are 4U's: every beam of a series ends with it
  (0x805a3c..0x805a9c chains 7/89 / 7/90).
- 7/50 spit (4U 0x802768 r2 1): 4U posts request 8 (the gas) at frame 150 of step 1 (always for r2 == 1, else heated
  bit 2 without 4); GU d2bd2c posts no message (C). Hook d2c734 (step-1 tail) posts GU's gas message there (S: the
  message GU gives request 8 in d2ba30). Its shell (4U kind 11 / 17 by state bit 0, GU subtype 2 / 6) and the forced
  burst (attack 26 / 57 at frame 100) are GU's.
- 1/18 eating cost: GU's record [this+0x75f0]+196 = 30.0 for him (log), 4U 20: hooks d27d58 / d27d64 put 20.0 in for
  his call of 0x9cf7c(this, 1) only (the record is shared with Gravios).

Test 2 of 0.4.1 (2026-11-01, log 20-25-46, quest 10781, 5:40, no kill: cleared at 91 % HP, no hunt tally, so ended
through the subquest, S): the gate posts only the action's variant (7/7 -> 2006 / 2007, 7/10 -> 2004 / 2005, 7/17
and 7/50 -> 2030 2031 2032 2041; the bit-2 twins skipped), the 7/50 puff posts at frame 150 (C, log). The kill of
test 1 (10783) ran the hunt tally (0x3a75c8 kind 0 = hunts +0x114, kind 1 = captures, C) and the quest cleared, so
what "nothing happens" means is open (asked). Kill test: core build with GOG_DEFINES=BG_TEST_HP_PCT=10 (diag: start at
10 % HP; it also logs the frame his HP reaches 0, as the death action 12/255 runs outside slot 125).

User after test 2: (a) the kill was in the capture quest 10783, which should have failed ("game over"), not cleared;
(b) not satisfied with the effects, "import them from 4U"; (c) the new attack that had no visual is no longer used;
(d) "does he really use the 4U AI?". Findings (C unless marked):
- (a) 10783's objective is GU type 2 = capture (as GU's q918 "Take it captive", q734, q612). GU's objective flags come
  from table 0x162a760 by type (1 hunt 0x1, 2 capture 0x81, 3 all 0x1000, ...; | 8 at setup 0x3abf98); the tally
  0x3a75c8 (kind 0 slain, 1 captured: +0x114 / +0x116) loops the 3 objectives (stride 12 from quest+0xec, target
  +0xf0): slain with 0x80 sets 0x40 and quest+0x5e = 1 (0x3a798c), so a slain capture target fails it in GU. His
  tally ran with kind 0 and the quest cleared: what the loop saw for him is not known; logged now (em005_01_objlog at
  0x3a7ed8). Open until a capture-kill log.
- (d) His selectors are 4U em41's: g0 s2 routes by op 0x79 (target relation) to the selectors he shares with Gravios
  (s7 s8 s9 s10 s16 s17 s18) and otherwise by rank to his own s13 (HR) / s20 (G); 7/50 and 7/17 come from the shared
  s23 (also s24 s68 s69), his own moves only from s13 / s17 / s18 (s39: 7/58, 7/71), s20 / s21 (s68..s70: 7/79): test 2
  (HR, 5:40) drew none of s39 (random, S). The action log now names the script (this+0x72fc / 0x72fd) per action.
- (b) effects() now takes all of 4U's motion effects: PEL u list 1 = GU's 16 + 4U em040_0 (57 with an EFL; group 115
  files of 1027 1028 1030 are not in em041.arc) + em041_1 (28) records; every motion whose 4U events name one and whose
  GU frames are 4U's plays only 4U's slots (psl_4u, all five PSLs, own file IDs 0x1090d..f); GU's entries stay for bank
  0 motion 103 (GU retimed, 261 vs 433 frames), bank 3 motion 122 (past GU's 122-entry PSL) and bank 3 motion 23 (GU
  only). 4U ids without a record (1100 2008..2011 2017..2020 3002) post nothing in 4U either (0x391a18: ids < 2000 look in
  MEF 0 = em040_0). The gate covers em040_0's conditioned records too: 31 32 bit 16 (7/26 7/29), 33 bit 17 (6/3:
  0x80774c case 3, S), 500 501 bits 30 / 31 (the component's ground bits 0x3934b8 by 4U stage W+0x14b and area: GU
  stage 12 = 4U 15 -> 31, GU 13 = 4U 3 -> areas 2 6 -> 30, 7 -> 31, S).

0.4.3 (2026-11-02, static checks only; on upstream main after 514c75c, Ash Kecha Wacha removed from the core):
- User again: killed in the capture quest, not failed. GU's loop (0x3a7940..0x3a7ed4, C) fails a capture objective
  (flags 0x80, | 9 at setup) on a slain target with its ID; why it did not for him is still not in a log. The objlog
  hook (0x3a7ed8, before the completion check 0x3a400c) now applies that rule itself for his ID (kind != 1: flag 0x40,
  0x20 cleared, quest+0x5e = 1) and logs "bgport: capture objective .. quest failed"; a tally of another ID in his
  quest is logged too (a stand-in ID would explain it).
- Checked: the em005_01 model's skeleton equals GU em005_00's (37 bones, same parents / ids / positions, C), so GU-
  and 4U-effect joints land where they do on GU Gravios; a misplaced effect is not a joint mismatch.
- PR #12 review point 3 (roar effect not at the mouth, too short): 1/17 plays motion 0x68 = bank 0 motion 104 (test 1
  log; that it is the roar is G), which plays 4U's slots since 0.4.2 (arc.log "PSL bank 0"); bank 0 motion 103 keeps
  GU's (retimed by GU). Not seen in a test yet.
- Open, needs a test log: the user's "spit to the ground in front has no animation" (7/50 = 4U 0x802768 r2 1, motions
  0x21b / 0x21e; GU's shell subtype 2 / 6 and 4U's em041_1 2030..2032 2041 post, test 2), and the general "moves and
  effects look wrong". The action / motion log names every pick: the tester should note the time of the move.

0.4.4 (2026-11-02; user log 18-54-29 of 0.4.3: quest 10781, 3:30, no kill):
- His AI is 4U em41's (C, log): 7/57 at 4:24 and 4:32 from g1 s39, a script only his table fills (GU emptied it).
  BG-only cat-7 actions of the table vs GU em005_00's (C): 7/28 7/31..33 (g1 s35), 7/42..45 (g1 s44 s45), 7/57 7/58
  7/71 (g1 s39 s70), 7/79 7/80 (g0 s20, g1 s60 s61 s65..s73) = 13, plus 7/75 7/76 7/82..85 (g1 s59, called by no
  script) and 3/7 (g0 s2, g6 s0). 7/50 ("spit to the ground", user) is in GU's own table too (g1 s23 s24 s68 s69,
  called from GU's g0 s3 s7..s19 s21 s22: C), so GU's Gravios has that move.
- User rule: his 4U AI and every 4U difference of his (beam heat burst, 7/50 gas puff, eating cost) stay; effects are
  GU's; a motion GU gives no effect takes 4U's. psl_4u now keeps GU's entry wherever GU's PSL has an effect slot
  (0.4.2 / 0.4.3 replaced every motion with 4U's: "beams and gas look odd"); 4U's slots go only to bank 0 motions 23
  26 29 (4U id 7), bank 2 19 21 33 50 (em041_1; 50 = 7/79's motion 562) and bank 3 112 (id 6). Bug fixed on the way:
  an empty 4U slot (id 0) counted as em040_0's record 0.
- Animations (C): every 4U em040 motion (banks 0..4, which em041 ships) is in GU em005_00's motion lists with the same
  frame count, except bank 0 motion 103 (GU 261 frames, 4U 433); none to convert.

Test of 0.4.4 (2026-11-02, log 19-42-14, quest 10781): user "much better overall"; 7/50 ("spit to the ground", 2:23
2:56 3:05, g1 s24) "has no beam" and killed him. 1/17 ran at 1:57.
- 7/50 in 4U (C): 0x802768 posts a uShell016 (subtype 11, or 17 with state bit 0; life 76 / 40) via 0x6620c4. Init
  0xc69ddc case 0xc6a0f0, second switch on subtype - 9: 11 -> 0xc6a26c, 17 -> 0xc6a2ac, each two 0xc07ecc posts =
  effect-manager event 15 = uEffect015 (kind = [eff+200]; u16 {group, file} at 0xfd16ac, 20-B record at 0xfd16d0):
  kinds 3 + 4 (11) or 3 + 10 (17). Kind 3 = flat-table group 35 file 7 = em024_009 (mask 1); kinds 4 / 10 = group 50
  file 13 = em040_100 (mask 2, other parameter records). So the 4U move shows a beam from the mouth into the ground;
  the frame-150 request 8 (em040_020) is a visual only.
- 7/50 in GU (C): d2bd2c posts at d2c730 with owner this+0xcacc. Owner slots by em number (d316b0): em 5 -> 0xcac8 =
  109, 0xcacc = 110, 0xcad0 = 111; shell table 0x1763448 rows -> files 0x89bb / 0x89bc / 0x89bd = em005_00_shell01 /
  shell02 / shell13. 7/50 = shell02 entry 2 / 6, effect (ef byte 0x19d) PEL u list-2 id 130 / 131 = em005_00_002_s;
  its ef files are identical to the gas entries' (3 7 8 9), only the id 130 / 131 differs. GU's beam look
  (em005_00_000, built on em024_00_001 = 4U's em024 beam model) is on shell13 entries 1 / 2 (id 150) only: the heat
  beam d2e330 (owner 0xcad0). So GU dropped the beam from 7/50 for its own Gravios too (how it looks in GU: S, not
  seen). No GU code posts list-2 ids 130 / 131 / 150 directly (only shells).
- Our frame-150 hook (em005_01_spit_c) posts shell02 entry 3 = a full gas shell with hit record 1 (hit003), where 4U
  posts only a visual: an extra hit 4U does not have (S that it is what killed the user; the log has no hit lines).
- PR #12 point 3 (C): GU's roar (bank 0 motion 104) = one slot, kind 3 = PEL c list-1 id 90 = cm202_050, joint -1 (not
  on a joint), frames 109..128 (20 of 498). 0.3.0 (the reviewed build) had GU em005_00's PSLs / PELs byte for byte,
  and 0.4.4 has the same slot again (GU's PSL has an effect there, so psl_4u keeps it). 4U's: id 16 at 112 and id 17
  every ~16 frames 118..389 on joint 3 (em040_0 group 13 files 3 / 4), id 10 at 23 on joint 80. So 0.4.4 is the
  reviewed state: point 3 open (4U's slots for this motion = the 0.4.2 / 0.4.3 state, needs the user's OK: the GU-first
  rule).

0.4.5 (2026-11-02, static checks only; module/em005_01_spit.c, build_em005_01_arc.py SPIT_FX):
- Spit 7/13 7/14 7/50 (same 4U path for all three, C): GU's shell (hit, life) stays; at frame 142 the two 4U uEffect015
  effects are posted as PEL list-2 world records 4040 (em024_009 k 0) and 4041 (em040_100 k 1) at Q along the 4U
  direction (pitch to target slot 0 from rec+64 to rec+464 clamped +-12743 + rec+0x50, yaw rec+0x54; 0xaacc90 at
  frame 142, 4U takes it in step 0: S), x / y scale from the 4U curves each frame (xf+0x60 / +0x64: S that GU reads
  it), ended with GU's 4U rule (life 76 / 40 minus the owner's motion step, or the motion changes; HP 0 too). Tick
  from em005_01_act_c. em024_009 + ef_em024 come from 4U em024.arc (joined to efl4u2gu's 4U sources at the lowest
  priority). Logs: "spit beam (kinds 3 + 4 / 10 ...) ... scale x1000", "spit beam end (...)".
- Frame 150: 4U's request 8 = record 4042 (em040_020 k 0) on the monster, no shell, no hit ("spit puff" log).
- Roars (PR #12 point 3): the user wants GU's look, "not out of place" (2026-11-02), not 4U's qe013 rings. GU's own
  monsters that put the same air (cm202_050) on the head use GU Gravios' record with only the joint changed (Tigrex
  em007_00 id 90: joint 3, 43 frames; others joint 3 / 4 up to 200 frames, C: GU romfs survey). roar_head(): PEL u
  list-1 id 3900 = GU em005_00c id 90 with joint 3 (4U's qe013 joint), in bank 0 motion 104 (1/17) frames 109..389
  and motion 4 frames 116..227 (GU's first frame to 4U's last em040_0 id-17 pulse; GU had no joint, 109..128 /
  116..133); motion 4's other GU slots stay.

Test of 0.4.5 (2026-11-02, user; log not in the folder yet): roar air on the head "looks really good". A "huge blue
explosion at the head" in a beam move followed by the body explosions: new in 0.4.5, so the spit effects (S: 7/50 =
beam into the ground + step-2 burst; em024_009 / em040_100 at Q) -> to be removed (GU gives that shell its own
effect 130 / 131: the GU-first rule). "The move that should get an animation" is NOT 7/50 (the earlier 7/50 mapping
was a guess): user: red fire at the mouth, hits in front first, then he lifts his face and hits at range, a laser.
That is 7/57 / 7/71 (C, static):
- 4U 0x803e6c (r1 0 / 2): frame 160 uShell016 33 / 35 (state bit 0; life 162, attack 29 / 30), joint 3, offset
  (0, 0, 180), length 6400, angles 0; per frame 0xc6b848 re-placed: Q = J3 + M3 (0, 0, 180), P = Q + M3 (0, 0, 6400)
  (the head's z axis, so it sweeps as the head lifts); init 0xc6a378: two uEffect002 id 41 (masks 1 / 2, scale 1.0)
  on the shell; id 41 = table 0xfd0b94 0x1333 = flat group 51 file 19 = **em041_101**, Black Gravios' own file (no
  MEF record names it: code only). Frame 250 request 8 (gas) with bit 2 not 4, frame 390 0x808410(0) burst.
- GU d2da3c: frame 160 shell02 entry 4 | bit0 << 3 (4 / 12: life 162, ef effect 0xffff = none) at d2dfe4, message
  vector zero. So GU's laser has a hit and no visual. 7/57 is BG-only (his table 2 calls, GU's 0).

0.4.6 (2026-11-02, user: "build both"; static checks only):
- 7/57 / 7/71 laser: module/em005_01_laser.c, hook em005_01_laser at d2dfe0 (before GU's frame-160 post; the bl is
  displaced through ip). em041_101 as list-2 world records 4043 (k 0) / 4044 (k 1) at Q = J3 + M3 (0, 0, 180) along
  M3's z axis, re-placed every frame (efx_set_pos / efx_set_rot as Gogmazios), stopped (efx_stop(eff, 0)) when the
  4U life 162 minus the owner's motion step runs out, the motion changes or HP is 0. Logs: "laser em041_101 (entry
  4 / 12) at ... scale x1000", "laser end (...)". Not ported: 4U's frame-250 gas visual (request 8 with bit 2 not 4;
  GU dropped it, open).
- Spit 7/13 7/14 7/50: 0.4.5's 4U uShell016 effects (records 4040 / 4041, em024_009 from em024.arc) removed; the
  frame-150 puff 4042 (em040_020, no hit) stays.

Test of 0.4.6 (2026-11-02, user, no log): smithy preview of his armor fine; "the spit move" (S: the laser 7/57 / 7/71 the
user described in the 0.4.5 test) still shows no visual. Left open and named in the PR #12 update comment (the user's
choice: send 0.4.6 as it is); em005_01_laser.c stays as the attempt.

## 4U behaviour of em 41 (static read 2026-11-01, S; whole-exe re-scan 2026-11-03 below)
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

Phase 1 variant map (2026-11-03): every `cmp #41` of the whole 4U exe (118) whose register comes from an
`ldrb [.., #0x1c0]` within the 10 instructions before it is one of the 10 sites of this plan (the 9 above and 0x800e60,
1/18's eating cost; S: a test on an em number loaded earlier or another way is not covered, nor is a table indexed by
the em number, G). GU's uEm004_00 reads only the em number, 5 for Gravios and him alike, never the variant (section
"His own AI and effects", C), so everything of his own runs through his AI table (dispatch check, C) and our hooks.

## Known deviations from 4U (listed for review)
- Effects: GU Gravios' wherever GU's PSL has one for the motion (user rule 2026-11-02); 4U's only where GU has none.
- Roar: GU's air effect (cm202_050) on joint 3 for 4U's length instead of 4U's qe013 rings (user's choice).
- Laser 7/57 / 7/71: no visual in game (GU posts the shell with no effect; em005_01_laser.c's em041_101 does not show,
  user test of 0.4.6); 4U's frame-250 gas visual of it not ported. 7/50's 4U ground beam: GU's gas effect only.
- Beam heat burst: 4U's request 6 (effect em040_013 + sound 216) not posted, the hit (attack 26 / 57) only (G: no GU
  request for it found).
- Rest group 16 (1/38, 1/41) and g1 s59 (7/75 7/76 7/82..7/85): not ported, no GU or 4U path reaches them (S).
- etd header word-4 record list (empty in em041) and emd word-32 part colours: not ported (role unknown / no GU field).
- Quests: 4U ranks moved to GU's (Hub HR6 -> HR7, G2 -> G4, caravan ★9 -> village ★10, as Stygian's); frenzy spawn
  bytes dropped (GU has no frenzy); Brute Tigrex in m10606 -> GU Tigrex; arena m21006 not ported.
- Rewards: 4U Gravios Shell has no same-name GU item; break groups 1 / 7 (frenzy) and 6 (Deviljho items) left out.
- Armor: 4U Flame Aura has no GU tree (dropped). No Hunter's Notes entry (save bits 123..127 are taken).

## Open
1. Test log of 0.4.6 (user plays, the log is read): his own 7/58 7/71 7/79 7/80 and 7/28 7/31..33 7/42..45 have not
   shown in a log yet (7/57 has, g1 s39); the laser lines "laser em041_101 ..."; a capture-kill objlog line.
2. The laser visual: asked in PR #12.
3. The burst's request 6 (em040_013 + sound 216): find what GU plays for it, if anything.

## Beams and their hits (2026-11-03, maintainer review of 0.4.6; module/em005_01_laser.c)
Test 2026-11-03 (log 16-52-51, quest 11430): lasers "condensed, not full height / width" (7/71), "absent" (7/79).
- C: em041_101 is a model-unit beam (EFL unit type 5). 4U scales it every frame: uEffect002 41 (0x1b5aa0) x = y =
  curve(t), t += owner motion step: mask 1 0xfd0f3c (1 -> 3 at 20 -> 13 at 40), mask 2 0xfd0e4c / 0xfd0f0c (subtype
  33 / 35: 1 -> 6 at 22 -> 3.2 / 1.6 to 147 -> 0 at 162). 0.4.6 left scale 1.0. Now applied (z = 1.0, both transform
  objects).
- C: 7/79 (4U 0x805eec r1 0; 7/80 = r1 1 posts none) fires uShell016 43 / 44 at frame 99 of motion 0x232 (life 100,
  joint 3, offset (0, -50, 100), length 6400) whose init posts uEffect015 kinds 16 + 14 / 15 = em041_101 masks 1 / 2
  (kind -> u16 0xfd16ac, 20-B records 0xfd16d0 {flags, curve A, curve B, 1000, mask}); 0x1c4fd0 t += dt then x = y =
  A(t); after the shell, 0x1c4b84 releases kind 16 and shrinks 14 / 15 with B (3.2 / 1.6 -> 0 over 15). GU d2ef2c
  posts no shell (attackEx at d2f300 / d2f4ec only). Now posted from em005_01_act_c (records 4043 / 4044).
- Crash 2026-11-03 (log 17-21-11): efx_set_pos on a freed effect (+0x150 held a float) on the 8th laser: handles are
  now validated each frame (vtable, state, transform pointers).
- Hits (user test 2026-11-03, open): 7/79 "doesn't hurt" (GU has no beam hit) -> GU's laser hit shell02 entry 4 / 12
  posted at frame 99 as a stand-in (S; GU life 162 vs 4U 100: may hit after the beam ends). Laser 7/57 / 7/71 hits
  "inconsistent": GU's shell02 entry 4 geometry vs 4U's head-following capsule not compared yet (GU shell class not
  read). "Walks forward and fires a series of small projectiles (instead of lasers)": not identified in a log; his
  4U-only 7/28 7/31..33 7/42..45 (4U 0x8036f0: motion 0x419, N shots via 0x806c94 -> 0x661f6c type 14 / 16) never
  ran in the three logs; best candidate 7/73 -> 7/89 (4U 0x8050e0 fires projectile shells via 0x661f6c / 0x661bec;
  GU d2e0b4 posts at d2e330 d2e3d0, more at d2ed44 d2ee00 d2eebc). Next: compare GU's shells with 4U's per move.
- Not explained: MEF 2061 / 2062 (frame 100 of motion 0x232) never reached the PSL gate in the 16-52-51 log while
  2051 / 2052 did.
- Hits, done (static, 2026-11-03; module/em005_01_shell016.c): GU's laser shell02 entry 4 / 12 = uShellEm005_sp_02, a
  projectile placed once (setup 0xd33cfc, shared move 0x3fca34), not 4U's head-following capsule. Replaced for him by
  a uShellEnemy class (Tigerstripe's framework) placing 4U's capsule every frame: 33 / 35 (Q = J3 + M3 (0, 0, 180),
  life 162) and 43 / 44 (Q = J3 + M3 (0, -50, 100), life 100, 7/79 frame 99), P = Q + M3 (0, 0, 6400). Damage =
  GU's own shell02 HDS entries 5 / 6 / 1 / 3 = 4U records 29 / 30 / 43 / 44 (Capcom's conversion, HTS r 360 / 240 /
  180 / 110 = 4U volumes 14 / 15 / 6 / 10, C). GU's laser post skipped (MID_EXIT d2dfe8, message freed). The
  stand-in of the previous build is gone.
