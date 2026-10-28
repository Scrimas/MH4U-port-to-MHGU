# Stygian Zinogre quests: survey and plan (2026-10-28; placement approved by the user the same day)

C = read in the 4U quest files (dump/romfs/loc/data/quest00.arc / quest01.arc, tools/quest4u.py offsets) or the
GU RomFS, S = strong, G = guess.

## 1. The 4U quests (C)
| 4U | title | 4U rank / stage | bosses (spawn list +0x28: em, area, byte +0xF) | min | fee / reward / sub | subquest |
|---|---|---|---|---|---|---|
| m10603 | Infernal Overlord | HR6 hub / 4 F. Seaway | 49 (a3, 0) | 50 | 1300 / 12000 / 4000 | wound head |
| m10607 | Advanced: Mega Hunt-a-thon | HR6 hub / 5 H. Mount | 49 (a6); wave 2: 4 Azure Rathalos (a8); wave 3: 26 Seltas Queen (a6) + 25 Seltas (a3) | 50 | 2400 / 23100 / 7700 | deliver Large Wyvern Tear |
| m10608 | Advanced: Dragon Attack | HR6 hub / 11 Arena | 12 Brute Tigrex (a1) + Stygian (second wave, list not read) | 50 | 1700 / 16800 / 5600 | sever Brute Tigrex's tail |
| m10612 | Advanced: Arena Emergency | HR6 hub / 11 Arena | 48 Zinogre (a1, +0xF 2) + Stygian (second wave) | 50 | 2000 / 19800 / 6600 | sever Stygian's tail |
| m10616 | Advanced: Insecticide | HR6 hub / 15 V. Hollow | 49 (a8, +0xF 2) | 50 | 1600 / 15900 / 5300 | wound a front leg |
| m00907 | Forge Ahead | caravan ★9 / 15 V. Hollow | 49 (a8, 0) | 50 | 900 / 8100 / 2700 | wound back |
| m01029 | Advanced: Prickly Pair | caravan ★10 / 4 F. Seaway | 49 (a3, +0xF 1) + Seregios (icon 99) | 50 | 2000 / 19200 / 6400 | deliver Large Wyvern Tear |
| m10925 | Fire Drill | G2 hub / 15 V. Hollow | 44 Brachydios (a2) + Stygian | 50 | 2500 / 24300 / 8100 | sever Stygian's tail |
| m10930 | Mountain Rescue | G2 hub / 5 H. Mount | 49 (a6) | 50 | 1700 / 16800 / 5600 | slay 8 Ioprey |
| m11010 | Into the Heavens | G3 hub / 5 H. Mount | 49 (a6); wave 2: 97 Gore Magala (a6) | 50 | 2800 / 27000 / 9000 | wound Gore Magala's head |
| m21003 | Grudge Match: S. Zinogre | arena (star 5) / 11 Arena | 49 (a1), size 105 % | 30 | 0 / 1800 / 200 | none: DROPPED (user 2026-10-28) |
| m60205 | (event, extdata) | G2 event | Stygian + Gypceros | | | |

- Spawn byte +0xF (open): 1 is a frenzied spawn in Tigerstripe's m10830 (S, its subquest says so). Here m01029's
  Stygian has 1 and m10612's Zinogre / m10616's Stygian have 2, with no frenzy subquest: meaning to settle before
  building those three (G: 1 = frenzy, 2 = another state; GU has no frenzy).
- Second-wave bosses (m10608, m10612, m10925, m01029) are not in the first spawn list: read the 4U wave lists.
- m60205 comes from the user's DLC extdata (tools/extdata4u.py, as Dalamadur's event quests).

- m21003 is a real 4U arena quest (C): the "Grudge Match" series (16 quests 20001..22006, all on the Arena, quest
  type byte +0xA0 = 1 vs 3 on hub quests), client "Arena Bambina", fee 0, the reward drains 200z per faint (+0xAC),
  time ranks in the exe table 0xfc9868 (m21003: 330 / 690 / 1800 s), preset gear (S: index table 0xfc9b40). The
  user dropped it (2026-10-28: "it's no use"), so 11 quests remain.

## 2. Placement (approved) and GU sides
- Hub HR6 (m10603 m10607 m10608 m10612 m10616) -> GU Hub HR7 (IDs 107NN). Caravan (m00907 m01029) -> GU Village ★10.
  Hub G2 / G3 and the event (m10925 m10930 m11010 m60205) -> GU Hub G4 (IDs 114NN). m21003: dropped.
- Stages: F. Seaway -> 14, V. Hollow -> 12, Arena -> 9, H. Mount -> 24 = the stage alias (4U m05 geometry while his
  quests run, folder m30: notes/heavens-mount.md).
- Area data (C): GU Zinogre's area files (em057_00 area_link / eat / select: maps 1 4 6 14 23 24; patrol: 4) cover
  the Frozen Seaway. Volcanic Hollow needs another GU monster's area data, as Tigerstripe did for the Dunes. The
  Arena is one area. Heaven's Mount comes with its stage port.

## 3. Core limits to lift first
- module/port.h PORT_QUESTS = 4 per allocations entry (tools/alloc.py QUESTS_PER_ENTRY): Stygian needs 11.
- Free quest IDs (C, base RomFS: no q%07d.arc and no quest_group entry): Hub HR7 10775..10789 and 10793..10799;
  Hub G4 11426..11430, 11451..11453 and 11497..11499; village ★10 1010, 1023..1025 and 1056..1099. Plenty for the 11.
- Board slots (C): quest_group (loc/arc/village/common.arc 'quest\quest_group', f32 4.0, u32 1509, 7-B entries
  {u32 quest ID, u8 group, u8, u8}) lists every quest, village (338 entries below 10000), hub, arena and event
  alike. Entries usable by the renaming rule (no save can hold them: not in the event catalog 0x1595e98, 200 IDs):
  besides the 9 taken, only 1111010..1111015 (group 127, indexes 1460..1465) and 1020030 / 1120013 (group 128,
  indexes 1481 / 1502) = 8. Stygian needs 11: the rule runs out.
  - Decided (user 2026-10-28): append our quests as new entries after GU's 1509 (in memory, at the loader step, as
    the rename does now) instead of renaming DUMMY slots, so no monster needs a free slot again. The cleared and
    failed maps ([0x1897f78] +0x42c / +0x62c, 512 bytes each) hold 4096 quest bits (S: the gap between them), so
    indexes 1509.. fit; every other per-index array (seen / new flags, sorting buffers, the results scene's own
    list) is to check first. The installed monsters keep their renamed slots (IDs only grow).
- Village quests: the loader step 0x3b7de8 loads loose questData for hub IDs (0x3b8090 filter). Whether village 10NN
  IDs load the same way is to study.
- Append study (2026-10-28, started): both list users (the boards' [[0x188ad90]+0xb4] and the results scene's fresh
  list, 0x6a1f64) load through 0x3b190c = `this+0xb4 = 0x152960(*0x18571e8, file id 0xe34a, type object 0x188abb8)`
  (C; the type object is in .bss, built at run time), released by 0x3b1940 -> 0x887660. So one hook there (or in the
  type's parser, which allocates count x 12 B entries from the file's u32 count) reaches both. Not a shipped
  quest_group: we can read only the v1.0 RomFS, and a v1.0-based copy would drop entries the updates added (S, the
  same reason as for common.arc).
- **Append design (2026-10-28, to show the user before any core change):**
  - The class (C): type object 0x188abb8 is referenced only by its own code (0x39b94c 0x39ba8c 0x39bd48 0x39bd90) and
    by 0x3b1920 (scratchpad xref_gu.py): quest_group is its only file. Object 0x70 B (new-instance 0x39b944): +0x64
    count, +0x68 version, +0x6c entries. Parser = load 0x39bb30(this, stream): version f32 must be 4.0; u32 count;
    block = new[] 0x37a5ec(count * 12 + 8, 16) with cookie {12, count}; entries = block + 8; ctor 0x37a654 each (+0
    element vtable, +4 u32 ID, +8 / +9 / +10 bytes = 0); load 0x37a8bc each (+4 ID, then the three bytes). Release
    0x39b9a8: dtor 0x37a684 per element from the end, delete[] 0x37a628(entries - 8).
  - Hook: entry hook `quest_group_append` at 0x39bb6c (`mov r0, r8; add sp, sp, #24`: displaceable; the parser's
    common exit, r4 = this, after the entries are loaded). If +0x6c != 0 and the list lacks our block: build the
    grown array the game's way (new[] with cookie {12, n + N}, ctor each, copy +4..+10 of the old ones, ours after,
    dtor + delete[] the old block), then +0x6c / +0x64. The game's own release frees ours normally. Every load
    passes there, so the boards' list and the results scene's fresh list both get it (no rename / clear fix needed
    for appended quests).
  - Order and indexes: every allocations entry's appended quests in registry order, installed or not; a monster that
    is not installed gets inert placeholder entries (a copy of a vanilla DUMMY entry, e.g. (1111010, 127, 0, 1):
    vanilla already lists duplicates, q1049 at 313 and 315), so a quest's list index (its cleared / failed bit) never
    moves when other monsters are added or removed (allocations stay append-only).
  - Entry bytes (C: vanilla patterns): group 0, byte +9 = 0, byte +10 = the template quest's (0 on q10724, 1 on the
    G4 hunts). Traced 2026-10-28 (C): +10 = the row of the quest name's colours on the boards: 0x3b22dc(mgr, id)
    returns it (1 for an ID not listed); the board rows 0x6173c4 / 0x618644 index table 0x1635230 {unselected,
    selected} with it (0 -> colour indexes 0x13 / 0x0b, 1 -> 0x11 / 0x12, 2 -> 0x09 / 0x14; the colour table itself
    is filled at run time, bss 0x18993e4). GU's list: Hub IDs 10101..10774 0 (300 of 313; the 13 others, e.g.
    10768 10770..10774, are special quests), Hub G-rank 11101..11457 1 (all), village 0..641 0, 701..1055 1 (all).
    The module uses that rule (quest.c qg_colour): HR7 0, G4 1, village ★10 1 = each template's byte. Found on the
    way: the renamed DUMMY slots keep their +10 = 1, so Dalamadur's Hub HR7 quests 10790..10792 show with the G-rank
    colour row (GU HR7 quests use 0). User 2026-10-28 "Fix it": quest_group_rename now sets +10 by the same rule
    (only Dalamadur's 10790..10792 change; every other renamed quest is G-rank, 1 already).
  - Limits: cleared / failed maps [0x1897f78]+0x42c / +0x62c are 512 B = 4096 bits each (S: the gap between them);
    loader cap 864 (scene 7: 814 GU + 9 ported + Stygian's 9 hub quests = 832, S); village IDs load in the village
    scenes (S, dalamadur plan.md: villages 1-10). quest_unlocked (0x3b2174) already answers 1 for owned IDs.
  - Also: PORT_QUESTS / alloc.QUESTS_PER_ENTRY 4 -> 12 (port.h struct; every monster's data file is rebuilt with the
    core, one release set); a new allocations key for appended quests (the existing monsters keep quest_slots).
    Correction (C, 2026-10-28): no data file holds the struct (only module/out/port_monsters.c and alloc.h use
    QUESTS_PER_ENTRY), so the monsters' data files do not change; only the core does.
- **Built (user's OK "Build it", 2026-10-28; not tested in game yet):** module/quest.c quest_group_append_c (hook
  0x39bb6c, build.py HOOKS), port.c port_quest_present (a quest counts only when its questData_%07d.ext is present,
  so quests not built yet take the placeholder too; cached, logged when missing), port.h PORT_QUESTS 12 +
  quest_append, build.py monsters_c, tools/alloc.py (QUESTS_PER_ENTRY 12, quest_append: no quest_slots, the
  placeholder 1111010 in no pool), allocations.toml (11 IDs in pools.quests; Stygian quests + quest_append = true).
  Module 939956 bytes, clean. Log lines: "mh4uport: quest_group: N entries + 11 appended (indexes N..N+10)", and
  "mh4uport: stygian_zinogre quest Q NOT present (...)" for each quest not built yet. To check in the first test:
  the board lists 10775 at HR7, the clear sets its bit (index 1509 on the v1.0 list; 1.4 may list more), no crash on
  the results screen. Per-index arrays (S, 2026-10-28): the 76 call sites of the entry getter 0x39bd1c (this, i ->
  entries + 12 i, 0 past +0x64) loop to +0x64 or look an ID up; the constants near them are quest IDs (0x259, 0x3ed,
  0x2a10..), save offsets and the cleared map +0x42c; 0x50cc14 counts groups 24..33 (group-indexed); no fixed-size
  per-index array found.
- Test 1, first try (2026-10-28 12:29, C from the log): endless loading at character load. The append worked
  ("1509 entries + 11 appended (indexes 1509..1519)": the loaded 1.4 list also has 1509 entries), but the old
  quest_group_rename matched Stygian's empty quest_slots (0) against GU's own quest 0 (entry 0) and renamed it 11
  times (0 -> 10775 .. 1024); the QDLoader then waited for questData 1024. Fixed: a slot 0 never matches (quest.c).

## 3b. Stat rows (user 2026-10-28)
"See the multiplicators of Stygian compared to Zinogre on 4U. Then check the ones from GU's Zinogre and apply
accordingly so it makes sense (Stygian is one star higher, and harder)." Per quest:
- 4U ratio r per column (HP, attack, defense / status row): the Stygian quest's em_nando_tbl values over the 4U
  Zinogre quest's at the comparable tier and kind (single / multi-monster): Hub HR6 vs Zinogre HR5 (m10520 / m10528),
  caravan vs caravan (m00903), G2 vs G2 (m10903 / m10915), G3 vs G3 (m11016).
- GU base: GU's Zinogre quest at the placement rank and kind (HR7 single q10735, multis q10708 / q10711 / q10742 /
  q10743; G4 single q11478, multis q11461 / q11480 / q11484 / q11488; village ★10 q1049 / q1029 / q1042).
- Target = GU base x r, the nearest GU em_nando_tbl rows, and never below the GU base (he is harder).
The table of 4U ratios, GU bases and chosen rows goes in the builder's docstring and is shown to the user.

Survey (C, scratchpad qstats.py 2026-10-28; values = em_nando_tbl HP column 0 / attack column 1 / defense column 2):
| Stygian 4U quest | kind | Stygian rows | 4U Zinogre comparison | r HP / atk | GU base (rows) | target HP / atk |
|---|---|---|---|---|---|---|
| m10603 Infernal Overlord | HR6 single | 1.24 / 3.05 / 0.85 | m10520 HR5 single 1.21 / 2.90 | 1.03 / 1.05 | q10735 HR7 single 1.66 / 4.30 / 0.80 | 1.70 / 4.52 |
| m10616 Adv. Insecticide | HR6 single, Advanced | 1.42 / 3.40 | m10528 HR5 Advanced 1.27 / 3.10 | 1.12 / 1.10 | q10735 | 1.86 / 4.72 |
| m10612 Adv. Arena Emergency | HR6, Zinogre + Stygian | 0.85 / 3.30 | its own Zinogre 0.88 / 3.20 | 0.97 / 1.03 | q10708 / q10711 HR7 pairs 1.00 / 3.25 | 1.00 (floor) / 3.35 |
| m10608 Adv. Dragon Attack | HR6, B.Tigrex + Stygian | 0.85 / 3.30 | (m10612's ratio) | 0.97 / 1.03 | q10708 / q10711 | 1.00 / 3.35 |
| m10607 Adv. Mega Hunt-a-thon | HR6, 4 monsters | 0.67 / 3.30 | (m10612's ratio) | 0.97 / 1.03 | q10720 HR7, 5 monsters 0.94 / 3.25 | 0.94 (floor) / 3.35 |
| m00907 Forge Ahead | caravan ★9 single | 1.06 / 2.80 / 0.95 | none single (m00903 ★9 is a pair, 0.79 / 2.80) | 1.00 / 1.00 (G) | q905 village ★9 single 1.06 / 2.55, at ★10 | 1.06 / 2.55 + ★10 step (open) |
| m01029 Adv. Prickly Pair | caravan ★10, + Seregios | 0.85 / 3.00 | m00903 pair 0.79 / 2.80 | 1.08 / 1.07 | q1049 village ★10 HR, 3 monsters 0.82 / 3.35 / 0.95 | 0.89 / 3.58 |
| m10930 Mountain Rescue | G2 single | 1.93 / 6.90 / 0.80 | m10903 G2 single 1.93 / 6.70 | 1.00 / 1.03 | q11478 G4 single 3.85 / 7.90 / 0.75 | 3.85 / 8.14 |
| m10925 Fire Drill | G2, Brachydios + Stygian | 1.36 / 6.90 | m10915 G2 pair 1.36 / 6.70 | 1.00 / 1.03 | q11488 G4, 3 monsters 2.05 / 8.20 | 2.05 / 8.45 |
| m11010 Into the Heavens | G3, + Gore Magala | 1.42 / 7.60 | m11016 G3, 4 monsters 1.21 / 6.90 | 1.17 / 1.10 | q11488 | 2.40 / 9.02 |
| m60205 (event) | G2, + Gypceros | (extdata, to read) | m10915 | | q11488 | |
- Defense / status rows: 4U Stygian = 4U Zinogre in every pair (r 1.00), so each quest keeps its GU base's "other"
  row.
- Open: the caravan ★9 -> village ★10 step (GU has no single village ★10 HR Zinogre).

## 3c. GU templates (C, scratchpad qtpl.py 2026-10-28; questData +0x12 stars / +0x13 class: HR7 Hub = 7 / 3,
village ★10 = 10 / 3 (IDs 10NN), G4 Hub = 14 / 5; objective type 1 = hunt, 3 = all large monsters; sub 8 = wound /
sever, 5 = deliver item)
| Stygian quest | template (same placement, stage, kind) | notes |
|---|---|---|
| m10603 HR7 F. Seaway single, wound head | q10724 (stage 14, hunt 0x20, sub 8, 50 min, 1600z / 15300z) | first quest |
| m10616 HR7 V. Hollow single, wound front leg | q10725 (stage 12, hunt 0x4d, sub 8) or q10726 | V. Hollow area data |
| m10612 / m10608 HR7 Arena pairs | q10774 (stage 9, rule 1, two hunts 0x202 + 0x201, sub 9) | 4U second wave: to check against GU's arena pairs |
| m00907 village ★10 V. Hollow single, wound back | q1003 (stage 12, hunt 0x3f, sub 8, 50 min, 900z / 8700z) | ★9 -> ★10 step open |
| m01029 village ★10 F. Seaway, + Seregios, deliver Large Wyvern Tear | q1021 (stage 14, single, 35 min) or q1034 (stage 12, sub 5 deliver) | two hunts: template to choose |
| m10925 G4 V. Hollow, Brachydios + Stygian | q11463 (stage 12, hunt 0x4d + 3 others) / q11443 q11475 (single) | GU G4 has no two-hunt quest on 12 |
| m10607 HR7 H. Mount, 4 monsters, hunt all | q10742 (HR7 Hub hunt-all with Zinogre, stage 104: no HR7 Hub quest on 24, re-staged) | built (5) |
| m10930 G4 H. Mount single, slay 8 Ioprey | q11472 (stage 24, G4 single) | built (5) |
| m11010 G4 H. Mount, + Gore Magala | q11473 (stage 24, G4 two-hunt, rule 1) | built (5) |
GU HR7 Arena multis q10717 q10719 q10720 (objective 3) and G4 q11450 q11480 also exist (stage 9).

## 4. Order
1. The core limits (PORT_QUESTS, pools), then the builder (monsters/stygian_zinogre/tools/build_em057_01_quest.py,
   one QUESTS table as Dalamadur's, templates and rank rows from GU's Zinogre quests at each placement).
2. First quest: m10603 (Frozen Seaway, single Stygian, GU's own area data). It is also the first test quest and the
   Notes unlock (quests[0]).
3. The other hub quests on 14 / 12 / 9, then village and event; Heaven's Mount quests after the stage port.

## 5. Built 2026-10-28 (8 of 11; not tested in game)
build_em057_01_quest.py is now one QUESTS table of dicts (multi-boss, capture, deliver, partners, the event from the
extdata); m10603's output is byte-identical to before the rewrite (cmp). C unless marked.
| GU | 4U | template | stat base | bosses (rows HP/atk/other) | objectives / sub | notes |
|---|---|---|---|---|---|---|
| 10775 | m10603 | q10724 | q10735 | Stygian 53/80/85 | hunt / wound head (1) | unchanged |
| 10777 | m10608 | q10774 (Arena two-hunt) | q10708 | Tigrex 30/65/53, Stygian 30/67/53 | hunt both / sever Tigrex tail (7) | **Brute Tigrex -> Tigrex (DEVIATION: GU has no Brute Tigrex)**; its 4U rewards B.Tigrex Scale+ / Carapace / Claw+ / Fang+ -> the Tigrex ones |
| 10778 | m10612 | q10774 | q10708 | Zinogre 30/65/53 (q10708's own), Stygian 30/67/53 under **0x439** | hunt both / sever Stygian tail (7) | a real Zinogre next to him: allocations standin_alt (core: port_standin) |
| 10779 | m10616 | q10706 (HR7 Hollow capture) | q10735 | Stygian 59/82/85 | **capture** (GU type 2) / wound front leg (3) | |
| 11426 | m10925 | q11463 (G4 Hollow) | q11488 | Brachydios + Stygian 65/110/96 | hunt both (rule 1) / sever tail (7) | |
| 11429 | m60205 (event, extdata) | q11468 (G4 Arena two-hunt) | q11488 | Gypceros + Stygian 65/109/96 | hunt both / none | 1723 Immenseness Ticket: no GU item (its chance to the row's top item) |
| 1023 | m00907 | q1003 (village 10* Hollow) | q1003's boss (GU's 10* single rows 37/66/19: every 10* village single, r 1 G) | Stygian 37/66/19 | hunt / wound back (2) | |
| 1024 | m01029 | q1021 (village 10* F. Seaway) | q1049 | Stygian + Seregios 26/71/19 | hunt both / deliver Large Wyvern Tear (GU 2129) | |
- 4U layouts read (C): objectives +0xCB count, {u32 type (1 hunt, 0x81 capture), u16 em, u16 n} at +0xCC / +0xD4,
  subquest +0xDC {0x204 wound / sever (4U part codes 2 head, 3 front leg, 4 back, 7 tail) | 2 deliver}; stat block
  per first-list spawn +0x34 + 8 i {u16 size, u8, HP, atk, other, ..} in spawn order (S). GU: objective 2 at +0x24,
  clear rule +0x1D = 1 with two targets (GU's two-hunt quests), capture type 2 (q918), deliver sub type 5.
- Spawn byte +0xF (C, ROM survey): 9 = Apex, 1 / 2 on "Advanced:" quests (m10522 "Frenzied Foe" 2, m10830 1): the
  frenzy states; GU has none (dropped as for Tigerstripe): m10612 m10616 m01029 lose it (**DEVIATION**, logged).
- Partners: the base quest's own record of their GU ID (Zinogre / Tigrex in q10708), else Stygian's rows (4U gives
  them his rows in m10925 m01029 m60205); board icons from GU quests with them first (ICON_QUEST).
- setEmMain names: one content per name (GU's 488 names all hold one content, C): Stygian 'b_mSSem057_6k' (k 0 keeps
  b_m14em057_01), partners 'b_mSSemEEE_8k'. Positions are 4U's (GU's Arena / Hollow / Seaway = 4U geometry, S).
- Volcanic Hollow area data: build_em057_01_arc.py area_files (GU Zinogre's + Brachydios em063_00's map 12).
- Village IDs: the loader filter 0x3b8090 passes village stars 7..10 (table 0x162cdc5, C), so 1023 / 1024 load.
- Heaven's Mount quests (built 2026-10-28, not tested in game; the 8 above stay byte-identical, cmp of all 64
  files). Stage = the alias of GU 24 (notes/heavens-mount.md). Opt-in builder keys: waves, hunt_all, tpl_stage,
  ('slay', em, n), zako (build_em057_01_quest.py docstring).
| GU | 4U | template | stat base | bosses (rows HP/atk/other) | objectives / sub | notes |
|---|---|---|---|---|---|---|
| 10776 | m10607 | q10742 (HR7 hunt-all, stage 104 -> 24) | q10720 (r 0.76 / 1.03 -> HP floor 0.94, atk 3.35) | Stygian, Rathalos, Seltas Queen, Seltas, all 28/67/52 (none in q10720: Stygian's rows) | GU type 3 hunt all / deliver Large Wyvern Tear (GU 2129) | **Azure Rathalos -> Rathalos (DEVIATION: not in GU)**; A.Rathalos Scale+ / Carapace / Tail / Wing -> Rathalos'; 480 S.Queen Concentrate: no GU item (NO_GU_4U) |
| 11427 | m10930 | q11472 (G4 single, 24) | q11478 (r 1.00 / 1.03) | Stygian 107/109/97 | hunt / slay 8 Ioprey (GU sub type 1, 0x100b) | 1643 Strong Armor Sphere: no GU item (NO_GU_4U) |
| 11428 | m11010 | q11473 (G4 two-hunt, 24) | q11488 (r 1.17 / 1.10) | Stygian + Gore Magala 77/112/96 | hunt both (rule 1) / wound Gore Magala's head -> GU group 1 "feelers" (G: GU's head break) | |
- Small monsters of the three: 4U's own per-area lists (the stage-24 templates' sets sit on Ruined Pinnacle terrain),
  only species with a GU ID read (Ioprey 0x100b: 4 / 4 / 3 records); Kelbi, Conga, Remobra, Felyne, Melynx and
  Bnahabra are left out (DEVIATION). 4U's per-record count (3..5) has no GU field: one GU record each (G: GU
  respawns small monsters; m10930 needs 8 Ioprey kills from 4 spots).
- Waves: GU has no wave lists; the bosses are listed in 4U's wave order and GU spawns them in record order (S).
