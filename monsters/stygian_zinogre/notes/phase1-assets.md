# Stygian Zinogre: Phase 1 assets and data (static, 2026-10-28)

4U = em049.arc / em048.arc / em_data.arc (dump/romfs/data), GU = base RomFS (tools/paths.py). C = confirmed in data,
S = strong, G = guess. Code-side study: [phase1-variant-map.md](phase1-variant-map.md).

## 1. Files Stygian has of its own in 4U (C, em049.arc vs em048.arc)
| kind | Stygian's own | shared with Zinogre (em048 paths) |
|---|---|---|
| model | enemy\em049\mod\em049 (+ _tail): MOD, MRL, 6 textures (01/02/03/04 BM, 01/04 NM_MIRROR) | |
| motions | none | em048_0 / _2 / _3 (LMT) |
| camera | none | e048_cam (LCM) |
| AI | none | enemy\em048\data\em048_cmd (EMC) |
| effects | EFL em049_000..005, 007, 010..013, 015..023 (23); effect model ef_em049 (MOD + MRL), em049_000 (MRL + BM_NOMIP); MEF em049_1 | MEF em048_0 |
| sound | bank snd_em049 (2 files) + 19 waves em049_se_fx_*: elec1..4, elec_base, get_bug, lbugDA, lbug_bomb1 / 2, lbug_bomb_burst, lbug_bomb_elec, lbug_disappear, lbug_fly_lp, lbug_start, lbug_start2, tailAT_elec, transform, transform_end | sound call em048, 51 em048 waves (voice, steps) |
| BGM | none (only bgm_em048.mca exists) | Zinogre's theme (S) |
Every same-path file is byte-for-byte the same size in both arcs (C).

## 2. Motions (C)
| bank | 4U em048 slots / used | GU em057_00 slots / used | 4U only | GU only |
|---|---|---|---|---|
| 0 | 49 / 48 | 49 / 46 | **30, 31** (59 frames each, 46 tracks) | |
| 2 | 100 / 50 | 100 / 50 | **14** (43 frames) | 42 |
| 3 | 29 / 27 | 29 / 27 | | |
Every animation present in both has the same track count and frame count (C, headers only; bytes not compared).
GU dropped exactly three 4U animations: candidates for Stygian-only motions (S; which motion IDs they are comes
from the code study). GU em057_04 (Thunderlord) adds its own bank em057_04_9 (5 animations) and reuses 0 / 2 / 3.
Plan: em057_01 gets GU's banks with 4U slots 0:30, 0:31, 2:14 spliced into the same (empty) indices
(tools/lmt.py splice), keeping GU's 2:42 (GU class code may request it).

## 3. AI table (C)
- GU em057_00_cmdtbl (19280 B) is shared by em057_00 and em057_04. 4U em048_cmd (14560 B) is shared by em048 and
  em049. Groups: GU 21 [23, 180, 6, 1, 1, 2, 1, 0, 2, 1, 0, 0, 1, 1, 0, 0, 1, 0, 5, 0, 1]; 4U 23 [19, 94, ...,
  1, 1, 0]: 4U's group 21 is NOT empty (one script `46 00 46 01 72 6f 00 0b ...`), so tools/emc.py to_gu() refuses
  this file (it asserts groups 21 / 22 empty).
- Identical scripts: group 0 8 of 19, group 1 44 of 94; groups 2..6, 9, 18 identical; 8, 12, 13, 16, 20 differ.
- Kinds of difference:
  - area move / patrol (GU language, as Tigerstripe's notes/area-move.md): 4U g0 s1 (872 B -> GU 7 B), g0 s2 (636 ->
    12), g20 s0 (752 B map-case routing with `2a` stage cases -> GU `88 a0 00 00 a1 00 ff`).
  - action renumbering / reworked moves: 116 native actions in 4U's table, 157 in GU's. 4U-only: 0/70 0/109 1/39
    1/40 1/43 2/47..2/52 2/61 2/62 2/75..2/77 3/6 3/9 5/8 6/2 7/14 7/40 7/54 7/62 7/63 7/115 7/192..7/197.
    GU-only: 0/17 0/32 0/97 1/10 1/32 1/33 1/44 1/45 2/2 2/71 2/81 2/83..2/87 3/0 3/5 3/13 3/14 7/4 7/5 7/20 7/32
    7/52 7/53 7/61 7/112 7/118..7/122 7/126 7/158..7/165 7/198 7/201 7/203 7/206..7/208 7/210 7/214 7/217 7/227
    7/228 7/230..7/243 7/246 7/249 7/250 7/253 7/254 13/111. Example: 4U g1 s4 (2/47, 2/48) -> GU 2/83 2/84 7/158
    7/159 7/231 7/232; 4U g1 s24 (7/194) -> GU 2/85 2/86 7/158 7/159 7/230..7/232.
- Answered (phase1-variant-map.md 5): GU restructured whole move families; the 4U handlers it lacks get ported.
- **em switches (C):** 4U op 0x46 (switch on the em number; GU skips it) blocks: case 49 in g0 s12, s13, s14, g8 s0
  (Stygian's own AI); case 114 / else only in g0 s0, g1 s18 s19 s20 s31 s57 s74 s80 and group 21 (em 114's: empty for
  em 49). GU replaced each with its own op 0x92 (S: a variant switch). The 4U area / patrol / routing ops (0x03,
  0x06, 0x36, 0x4d, stage switches 0x2a) sit only in g0 s1, s2, g1 s59, s62, s63, s88, g20 s0 (no em switch there);
  GU g0 s0 = 4U g0 s0 for em 49 with GU's engine op 0x9e where 4U called its area script s88 (C).
- **Built (B6, build_em057_01_arc.py cmdtbl()):** 4U em048_cmd reduced to em 49 (128 scripts), GU's versions of
  the 8 area scripts (g0 s0 s1 s2, g1 s59 s62 s63 s88, g20 s0), GU's extra entries appended (selectors 19..22,
  scripts 94..179: no script of ours calls them, C; GU class code may pick them by number), group 21 dropped. Every
  script tokenizes with GU's length table main 0x1732c8c (C).
- **B7 (done 2026-10-28, module/em057_01_ai.c header):** ops 0x79 (g0 s3), 0x82 arg 0 (g0 s3), 0x87 (g0 s12): SAME
  (S; C for the structure). Conditions (op 0x6f, 4U slot 51 0x8579fc vs GU slot 133 0xef2fd0): id 0 charged, id 5
  counter >= 100 (clamp), id 10 uncharged and counter >= 100 (2 uses in the 4U scripts + 2 in GU's kept ones): SAME
  (C). DIFFERENT (C), all on 4U's rest flags GU removed: id 11 (4U 0x857b48: W+0x544 || W+0x545; GU 0; g16 s0 picks
  1/35 on 0, else 1/39), op 0x80 (4U: body if W+0x53a; GU 0xc9b58 always skips to the else), op 0x91 (4U: body if
  W+0x7e80 & 32; GU 0x852bc switches on the em number, no case). cmdtbl() merges 4U g0 s3's `80 00 R 80 02 91 00 R 91
  02 91 ff 80 ff` into `80 00 R 80 02 80 ff` (GU's own form; only g0 s3 changes). Hooks written, NOT wired:
  ('em057_01_cond', 0xEF2FD0) and ('em057_01_op80', 0xC9B58), both entry hooks on push prologues; wire them with the
  rest-state port (plan.md). 0x6d is gone after the em-49 reduction (C).
- Stage cases: GU's area scripts carry GU Zinogre's stages; GU Zinogre is never on Volcanic Hollow (12) or Heaven's
  Mount: their area cases and area files (manifest 40..44) are quest-step work (Tigerstripe used another GU
  monster's area files for the Dunes).

## 4. Body and stat data (C, em_data.arc)
- etd: same size (9486 B); header word 4 = 0x14b4 (em048) vs 0x13ec (em049) (S: base HP 5300 vs 5100); other
  differences in the tables at words 5..10 (0xa0..0x1cc, S: hitzones), 13 / 14, 25, after word 29 (0x100c..0x1158)
  and 0x246c..0x2488. Attack records (word 28..29, 0x3e8..0xfa0, 75 x 40 B) are IDENTICAL: the dragon element is not
  in the attack records (S: element table after word 29, or code).
- emd: 16372 vs 16900 B; header word 9 (cambodydata) 0x5c0 vs 0xc4, words 13..26 shifted by 0x210: Stygian's body
  data differs.
- Converted (tools/dt_convert.py build emNNN em057_00, GU venv; outputs dump/converted/em049/dt_em048, dt_em049):
  the converter reproduces Capcom's pair: 4U em048 -> dttune differs from GU em057_00's own in 3 bytes only (C).
  dttune em049 vs em048: 103 bytes (0x38..0x114), none on GU's 3 retuned bytes -> **em057_01 dttune = GU
  em057_00's + those 103 bytes** (Tigerstripe's method, asserted at build). dtbase em049 == em048 (C) -> shared.
- bodydata (emd word 8): em048 == em049 (28 records, C); GU em057_00 has 27 (GU's retune) -> shared.
- cambodydata (emd word 9): em048 has its own 16 records, **em049's is a byte copy of its bodydata (28 records)**
  (C); GU em057_00 has 19 (retune of em048's 16) -> em057_01 gets 4U em049's converted (28 records).
- hitsize (etd word 27..28, 0x368..0x3e8) and attack records: no em048 / em049 difference (C) -> shared.
- GU em057_04 (variant precedent) ships its own attackdata, hitsize, bodydata, cambodydata, dtbase, dttune,
  dtbparts, actiontune, area files (5), hagi s0..s4, shells (em057_04_shell01 / 11 / 18), effects
  (em057_04_0NN), sound bank snd_em057_04 + waves, motion bank _9, model + textures; it reuses em057_00's
  cmdtbl and motion banks 0 / 2 / 3.

## 4b. Carves and shiny drops (C, tools/hagi4u.py on the 4U exe; low rank null: Stygian is HR + G only)
| table | HR | G |
|---|---|---|
| body carve | 534 S.Zinogre Carapace 44, 540 S.Zinogre Dragonhair 24, 536 S.Zinogre Claw+ 15, 538 S.Zin Drakeshell 14, 541 S.Zinogre Umbrage 3 | 1508 S.Zinogre Cortex 44, 1507 S.Zin Dragonlocks 24, 1510 S.Zinogre Hardclaw 15, 1511 S.Zinogre Drakehold 14, 1513 S.Zinogre Skymerald 3 |
| shiny | 825 Wyvern Tear 25, 826 Large Wyvern Tear 50, 534 Carapace 15, 539 Dracophage Bug 9, 541 Umbrage 1 | 1507 Dragonlocks 10, 826 Large Wyvern Tear 55, 1508 Cortex 28, 541 Umbrage 5, 1513 Skymerald 2 |
Zinogre em048's tables have the same shape (HR 522 / 524 / 528 / 531 / 533, G 1501 / 1500 / 1503 / 1504 / 1506).
Stygian's 4U materials are 534..541 and 1507..1513 (tail, break and reward tables to read at the content step):
about 15 new GU items, appended after Dalamadur's (3021..).

## 4c. Gear scope (C: 4U create recipes 0xf3f000..0xf55400 that use Stygian materials)
- Armor: two 4U series, Blademaster / Gunner: HR "Zinogre U" (head 140 / 141, body 141 / 142, arms 136 / 137, waist
  135 / 136, legs 137 / 138) and G "Zinogre Z" (head 598 / 599, body 602 / 603, arms 586 / 587, waist 586 / 587,
  legs 594 / 595) = 20 pieces (male + female models). Other monsters' armor using a Stygian item as an extra
  (Fatalis Crimson, White Fatalis, GX Tempest / Welkin) is out of scope.
- Weapons: superseded by notes/weapons.md (2026-10-28). The class pairing that used to be here was wrong. The
  Stygian lines are 4U's "Brimstren Drake*" weapons in 12 classes (no CB, no IG): Brimstren X -> X+ -> "Stygian
  <vice / virtue>", plus a "Charonian" weapon for LS and Bow, 37 weapons in all. They branch off the Zinogre weapons
  ("Despot's" / "Usurper's ... +"), which GU already has as the B / A names of its levelled Zinogre weapons.
- Armor tool built (gear_em057_01.py): templates EX Zinogre 458 / 459 (HR) and Zinogre X 920 / 921 (G); defense 53 /
  27 -> 54 / 27 (anchors Agnaktor, Regios S), 94 / 51 -> 125 / 75 (anchor Zinogre X); every 4U tree exists in GU by
  name (C); ore substitutes and level-row swaps listed in its docstring for review.

## 5. Quest placement (user's rule, 2026-10-27: Stygian vs Zinogre in 4U, then among GU's Zinogre quests)
4U (C, star byte +0xC2, stat rows +0x34 -> 4U em_nando_tbl; star scale S: HR 7, G1 8, G2 9, G3 10):
| | Zinogre | Stygian |
|---|---|---|
| Hub HR | HR5: m10520 HP 1.21 atk 2.90, m10528 1.27 / 3.10 | HR6: m10603 1.24 / 3.05, m10607 0.67 / 3.30, m10608 0.85 / 3.30 (+B.Tigrex), m10612 0.88 / 3.20 (+Zinogre), m10616 1.42 / 3.40 |
| caravan (HR stats) | ★9 m00903 0.79 / 2.80 (+em40) | ★9 m00907 1.06 / 2.80; ★10 m01029 0.85 / 3.00 (+Seregios) |
| Hub G | G2 m10903 1.93 / 6.70, m10915 1.36 / 6.70; G3 m11016 1.21 / 6.90 (multi) | G2 m10930 1.93 / 6.90, m10925 1.36 / 6.90 (+Brachydios), event m60205 1.36 / 6.90 (+Gypceros); G3 m11010 1.42 / 7.60 |
| arena | | m21003 "Grudge Match" (star 5) 0.94 / 2.90 |
GU Zinogre (C, questData class +0x13 / stars +0x12, rows -> GU em_nando_tbl): Hub HR6 multi (q10609 1.30 / 2.65,
q10624 / q10626 1.03 / 2.70), HR7 (q10708 / q10711 1.00 / 3.25, q10712, q10720, single q10735 1.66 / 4.30,
q10742 / q10743 1.21 / 4.40), village HR ★9 (q905 1.06 / 2.55) and ★10 (q1049 0.82 / 3.35), G3 multi (q11308 /
q11355 2.23 / 5.70), G4 (single q11478 3.85 / 7.90; multis q11461 q11480 q11484 q11488), village class 5 ★10
(q1029, q1042).
Stage IDs (S: vote over GU quest texts naming a map vs their questData +0x14, 2026-10-28; validated on Frozen Seaway
= 14 and Dunes = 5, both known): 4U 4 F. Seaway -> GU 14 (34 / 34), 4U 15 V. Hollow -> GU **12** (33 / 33), 4U 11
Arena -> GU **9** (64; 17 / 15 / 10 also appear: Slayground = 10), 4U 5 H. Mount -> none (step 7). Others for
reference: Ancestral Steppe 11, Primal Forest 13, Deserted Island 6, Marshlands 7, Volcano 8, Ruined Pinnacle 24,
Jurassic Frontier 1 / 101, Verdant Hills 2 / 102, Arctic Ridge 3 / 103, Misty Peaks 4 / 104, Fortress 26.
Placement (approved by the user 2026-10-28): Hub HR6 -> GU Hub HR7 (4U puts Stygian one star above
Zinogre's HR5; GU's Zinogre already sits at HR6 / HR7, HR7 is the top); caravan -> GU Village ★10; Hub G2 / G3 and
the event -> GU G4 (4U puts Stygian level with or above Zinogre's G2; GU's single Zinogre G quest is G4, the top
regular rank); arena m21003: dropped by the user (2026-10-28; a 4U preset-gear time-trial quest, notes/quests.md 1).
