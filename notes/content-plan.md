# Gogmazios content plan: save data, rewards, gear, monster tables, quests (2026-10-20, planning only)

Priority: multiplayer comes first (notes/port-checklist.md "Multiplayer"). Implemented: section 1 (save slot),
2 (rewards), 6 (second quest + subquests); crowns not needed (section 5).
Evidence tags: C = confirmed in code or data, G = guess.
Main sources:
- MHGU_Editor (the user's save editor): docs/02-monster-records.md, docs/10-npc-talk.md, docs/11-save-map.md, data/*.csv.
- notes/registry.md.

## 1. Save data

### Current state (C)
- The save keeps three 137-entry arrays indexed by registry index + 1: hunt tally 0x192B40, captures 0x192C52, size records 0x192D62 (MHGU_Editor docs/02).
- Gogmazios has registry index 137, so it falls outside them. Every save accessor bounds-checks, so it is simply not counted.
- The unbounded quest-end tally 0x3a75c8 and its reader 0x3a3930 are hooked to skip it (module/main.c).

### DONE 2026-10-20 (built, not tested in game yet)
- Simpler than the proposal below: the save is written from the quest's own 137-entry tally (0x3a75c8, hooked
  stats_add), so remapping 0x59 -> 0x1064 there is enough. The quest-end writer 0x38da40 walks all 137 indexes, turns
  index 105 back into 0x1064 (0x50bdc) and calls the save accessors; no accessor hook. stats_hunted (0x3a3930) gets
  the same remap. Size path: 0x55ff98 returns 0x1064 unchanged; 0x1c95a4 ignores IDs above 88.
- Not visible in game (C): the large-monster total sums a fixed 166-ID list (0x162bf0c, used by 0x52308c), and the
  Guild Card monster log is a fixed 87-entry table stored in the save, so neither can gain Gogmazios without a save
  format change. Quest-end screens that name index 105 read monsterName entry 105 = "Gogmazios".

### Proposal: give Gogmazios an unused save slot (no save-format change)
- Unused slots (C):
  - Registry indices 105..111: ids 0x1064..0x106a, the game's dummy1..dummy7 ("106-112 unused" in the editor's numbering).
  - The editor also lists save index 134 as empty, but registry 133 holds id 0x57 (em 87), so don't use it.
  - Pick registry 105 (id 0x1064, dummy1). A vanilla game never shows or writes it.
- Remap id 0x59 -> 0x1064 only inside the save accessors (C: each takes the id in r1 and calls 0x50b64 itself):
  - 0x523104 (9 callers), 0x526d94 (1), 0x526dd4 (14), 0x526e00 (1), 0x526e44 (9), 0x526eb0 (1), 0x526ef8 (1), 0x526f48 (8).
  - 0x52308c loops over every index: check it.
  - Two ways: either one hook on 0x50b64 that answers 105 for 0x59 when lr is one of those return addresses, or an entry hook per accessor that rewrites r1.
- Quest-end tally: replace the skip in stats_add / stats_hunted with the same remap (index 105).
- Still to trace:
  - the bitset 0x551dd0 (index < 137);
  - the Hunter's Notes bits (section 5);
  - the Guild Card monster log (own card +0xF6C, 87 x 8 B, rebuilt from the tallies by 0x161ac8, read by the crown awards): is a dummy slot ever copied into it?
- Save editor: show registry 105 / save index 106 as "Gogmazios (port)" when the mod is used.
- Risk (G): a game path that walks all 137 entries and treats 105 as a real small monster (totals, awards). Check every reader of the three arrays first.
- Effort: M (hooks small; the work is the reader audit).

## 2. Rewards (materials)
Gear research 2026-10-20 (helper, static). Its scripts: scratchpad gear/py (lmd.py = 4U core_common text parser,
gogrec.py, gogw.py, items.py). 4U gear is hard-coded in the 4U exe; only the text is in RomFS (core_common.arc, lmd).
- Current state:
  - Carving gives KUSHALA materials: hagi s0..s4 (manifest fields 46-50) are Kushala's placeholder (C, tools/em089_manifest.json).
  - Quest 11491 rewards are generic G-rank: REM = rem_230088 x2, rem_530072, item 1778.
- GU item table (C): table\itemData in loc/arc/resident.arc, also a byte-identical loose nativeNX/table/itemData.itm in v1.0 and 1.4.
  - 2991 records x 44 B: +4 type, +5 rarity-1, +6 carry, +0x10 icon, +0x11 colour, +0x13 sell, +0x17 buy.
  - Text: itemData_<lang> GMD, name 2k / description 2k+1, 7 languages.
  - Which copy 1.4 loads (arc entry or loose file) is the first thing to test.
- New IDs, recommended: items 2977..2990 are 14 "DUMMY" placeholders.
  - Checked: name DUMMY, rarity 1, icon 1.
  - Unused by any recipe, reward, carve, combo or provision (helper, from the save editor's tables).
  - Using them avoids every item-ID bound.
  - Appending instead (2991..3007) would need ~24 code patches (0xbaf / 0xbad sites: obtained setter 0x1943d4, loaders 0x19a4ec / 0x19e0ac, UI); the save has 12-bit slot IDs and a 3008-bit obtained map.
- 4U materials (C; 4U ids, rarity 8 unless noted, sell price; buy = 10 x sell; 4U icon / colour indexes = GU's):

| 4U id | Name | Rarity | Sell | Icon | Colour |
|---|---|---|---|---|---|
| 1528 | Battlement | 8 | 13000 | 12 | 3 |
| 1529 | Fortress | 8 | 16250 | 50 | 3 |
| 1530 | Gasher | 8 | 22750 | 10 | 3 |
| 1531 | Offenders | 8 | 26000 | 10 | 3 |
| 1532 | Fiberwing | 8 | 23750 | 13 | 3 |
| 1533 | Briartail | 8 | 32500 | 13 | 3 |
| 1534 | Wartorn Dragonsphire | 9 | 40000 | 28 | 1 |
| 1535 | Heavy Drakesbone Oil | 8 | 13000 | 22 | 3 |
| 1713 | Gogmazios Scrap+ (Palico) | | | | |

- 4U drops (contents C; which table is which G):
  - body carve: Battlement 38 / Fortress 28 / Offenders 13 / Fiberwing 10 / Oil 8 / Dragonsphire 3;
  - tail: Briartail 75 / Battlement 22 / Dragonsphire 3;
  - shiny drop: Oil 70 / Old Dragon Treasure 28 / Dragonsphire 2;
  - 4 break-reward tables;
  - m11014 main rewards: Battlement 34, Fortress 25, Offenders 14, Fiberwing 10, Oil 10, Gasher 6, Dragonsphire 1;
  - general rewards: LED Bone, Elder Dragon Blood, armor spheres, charms, orbs.
- DONE 2026-10-20 (built, not tested in game yet):
  - Items 2977..2985 = the 8 materials + Gogmazios Scrap+ (tools/items_em089.py -> module/items_em089.inc, module/items.c).
    UI mods replace both resident arcs (the user's HD UI v4 does), so the module patches the LOADED tables: hook
    0x19237c (rItemData load exit: 56-byte records, rarity / icon / colour / prices / category) and 0xb83c48
    (rGUIMessage load exit: itemData_<lang> string pointers, 4U names + descriptions, eng fre ger ita spa).
    Icon / colour numbers are shared by both games (C: 1033 of 1073 same-name items). Category = the Daora G
    item with the same icon (G).
  - Carves: tools/hagi_em089.py -> em089 arc fields 46-50 (s4 = 4U G body / tail / shiny, s0..s3 = GU's filler,
    byte-identical to GU's). Matches the Kiranico MH4U page data exactly.
  - Quest rewards: rem_891014 (row A, 4U m11014 table 1) + rem_892014 (row B, table 2), single-group GU rem
    (condition 1); row C keeps GU's Accolade XX table. Strong Armor Sphere -> King Armor Sphere (rarity 8).
  - Break rewards: hook 0x3a3874 (break record by monster ID) answers em089's own record: cond 20 head, 30 wings,
    40 breast (neck/chest), 60 back (bone 205, group 5). cond = table 0x162a736 [break group] (C); part names per
    the Kiranico page data (Head, Wing, Breast, Back = 4U table order).
- DONE (built, not tested): 4U "Shiny Drops (Ballista)" = shiny drop set 0 (One-shot Binder 100 %, GU 1731), used
  by the tail-break drop; the rare-drip drop uses set 1 (port-checklist "One-shot Binder shiny drop").
  Base HP: 17500 stays (the EUR v1.1 update ships no monster data; Kiranico's 18000 is another version's).
- Save editor: no core change for DUMMY ids, but its asset / CSV tools read scratch/base_romfs.bin, so they need a module/romfs overlay or the items show as DUMMY.

## 3. Armor and weapons
- Armor "Gogma" (4U, C):
  - Blademaster Helm / Mail / Braces / Faulds / Greaves = 4U ids 550 / 554 / 538 / 538 / 546; Gunner = id + 1.
  - Rarity 10; defense 110 Blademaster / 64 Gunner; 15000 z; slots 1/1/2/2/2.
  - Resists (order F W T I D, G): Blademaster -4/+3/0/-7/+3, Gunner -3/+4/+1/-6/+4.
  - Blademaster skills: Arcana +10, Expert +15, Artillery +10, Avarice +3, Sharpener -10.
  - Gunner skills: Arcana +10, Dead Eye +10, Normal Up +10, Normal S+ +8, Avarice +3, Reload -10.
  - 5 recipes decoded; the Arms piece needs Cosmicite Ore, which GU does not have (substitute needed).
  - Models: pl_{m,f}_{helm,body,arm,wst,leg}352.arc in the 3DS image (tools/ctr.py x), not in dump/romfs.
- GU armor data (C):
  - armorSeriesData: 1287 series x 127 B; the series id is the box id of all 5 parts; field names from DTI strings at 0x1553ad9.
  - armorCreateA00-04 in arc/facility/blacksmith.arc; armorProcessA00; names armorSeriesData_<lang> (10 strings per series).
  - Models: arc/player/com/{m,f}/<model>/{helm,body,arm,wst,leg}.arc, highest model 747.
  - No armor-count constant found in code (G: appending series 1287 / 1288 is data only). Save bounds: smithy list 576 per part (13..59 free), armor map 5248 bits.
- Weapons (4U, C): one create -> upgrade pair per class, 14 classes, no element, a status of type 3 (probably Sleep, G; hidden or not unknown).

| Class | Create (raw) | Upgrade (raw) |
|---|---|---|
| GS | Monument of Lament (280) | Ostracon Oblivion (300) |
| SnS | Valorous Soldier | Kyrie Ruin |
| Hammer | Empty Cage | Desmos Admonition |
| Lance | Fettering Rebuke | Aether Geghard |
| LS | Grim Genuflector | Headsman's Requite |
| SA | Punishable Sin | Wicked Conqueror |
| GL | Towering Demise | Auguring Prophet |
| DB | Recriminators | Eternal Leavetakers |
| HH | Clemency's Peal | Onyx Terpsichore |
| IG | Messenger's Mark | Luminary's Mark (upgrade recipe not found) |
| CB | Forbidden Coffin | Promised Nadir |
| Bow | Unwelcoming Gaol | Calamitous Cupid |
| LBG | Bethorned Dystopia (single) | - |
| HBG | Trembling Lordship (single) | - |

  - Raw 260..310, affinity -10..-20, rarity 10, 80000 z create / 130000 z upgrade.
  - All recipes decoded (appendix); models swo097, one097, ... bow075 in the 3DS image.
- GU weapon data (C):
  - weaponNNBaseData (81..137 per class, derive ids u8, so new ids must stay <= 255), weaponNNLevelData, weaponCreateWNN / weaponProcessWNN (blacksmith.arc).
  - Names weaponNNMsgData_<lang> (6 strings) + index .wNNm.
  - Models arc/weapon/wNN/<model>.arc + snd.
  - Class extras: HH notes, GL shell, phials, bowgun ammo, bow charges.
- Effort:
  - armor data M; weapon data L (14 classes);
  - **models L**: 10 armor pieces x 2 sexes + 14 weapons, 4U -> GU player rig / weapon formats. tools/mod4u2gu.py is a start, not a solution.
- Order: armor data on a placeholder GU model first, one weapon class second, models last.

## 4. Skills
- The set's signature tree is Arcana (4U tree 140): +10..+25 = skill "Enlightened Blade" = Awaken + Element Atk Up + Status Atk Up (C).
  - GU has no Awaken, and GU compound skills are code (skillData holds only per-class flags).
  - Decos: Arcane Jewel 1 / 2 / 3, True Arcane Jewel 3 (4U items 1838-1841, values not decoded).
- Faithful option (M):
  - Append skill tree 206 + skill 328 + names.
  - Hook the GU skill query so skill 328 also counts as Element Atk Up (76) + Status Atk Up (78). Query site not located: start from compound skill 319.
  - Arcane decos into the dummy decoration items 2889..2899 = decoData records 251+ (13 deco-list bits free).
    DONE (built, not tested): 2889-2892; 4U has no recipe for them (reward-only), recipes are a port choice.
  - Awaken: GU weapons have no hidden element; Gogmazios weapons' status may be the 4U-hidden kind. Decide with the user.
- Zero-code fallback (not faithful): give the set GU's Elemental (32) + Status (33) trees.
- Other trees map to existing GU trees (Expert 70, Artillery 90, Sharpener 34, Dead Eye 66, Normal Up 48, Normal S+ 52, Reload 45; Avarice: G, 135 / 137 / 199 to choose).

## 5. Monster tables

| item | state | plan |
|---|---|---|
| HUD icon + name | done (UI 141, GMD name entry 105, tools/ui_em089.py) | - |
| Crown thresholds | not needed | 4U Gogmazios has no size variation (Kiranico MH4U data: crowns 0.0, no crown sizes), and quest 11491 already spawns it at a fixed size: boss size 100 % with variation table 0 (em_size_yure_data table 0 = rate 100 at 100 %). GU monsters without size variation (Nakarkos) have no em_size_scale_data / size record either. |
| Hunter's Notes | DONE (built, not tested; port-checklist "Hunter's Notes") | Large-monster list = 123 entries (unlock 0x554da4, talk condition 44, bits at save +0x32B7, 16 B: bits 123..127 spare, C). Needs a list entry (code table, relocate like the registry tables), notes bit 123, page texts (HN GMDs) and the page data (weaknesses / breakable parts, format to trace). |
| Guild Card log / crown awards | missing | 87 entries (card_pos); depends on section 1. |
| Status tolerances | runtime | 4U em089's status words (etd 15..21) are 0, so the port clears Kushala's blocks every frame (em089_react_status_immune). Plan: dt_convert.py writes them empty, then the runtime clear goes. **Open check:** an MH4U reference says Gogmazios is immune to stun and flash bombs; the Kiranico MH4U page data (2026-10-20) gives 0 for pitfall, flash, shock, sonic and canopy in every state, but no poison / sleep / paralysis values, so those are not settled. Re-trace 4U before calling "immune to everything" faithful. |
| Exhaust / mount | to check | Compare 4U em089 etd mount / exhaust data with our dttune (dt_convert.py) and test a mount. |
| Element weaknesses | done | Hitzones are 4U's, converted (dttune / tar states). |

## 6. Quests
- DONE 2026-10-20 (built, not tested in game): 11492 = 4U m11035 "Advanced: Act of Gog" (`build_gog_quest.py
  --source m11035`): fee 4600z, reward 45900z, sub 15300z, HRP 2440 (11491's HRP per zenny), same stage / spawn /
  stat rows as m11014 (asserted). Board slot: module/stage.c renames quest_group placeholder 1011003 (list index
  1407, the section's other DUMMY) to 11492; quest_unlocked, the stage alias, the stand-in swap, BGM and break
  rewards follow `gog_quest_index()` (1 / 2).
  - 4U spawn byte 3 = 1 in m11035 (faster phase 2: speed 1.155 instead of 1.1, tar drip kind 8). GU's byte at that
    place is the Hyper flag (questData boss +3 = 1 on GU's Hyper quests), so it stays 0 and em089_act.c spawn_b3()
    returns 1 in quest 11492.
  - Conqueror's Seal G (row B, 3 %) has no GU item: dropped, its 3 % added to the row's most likely item.
- DONE: both quests now carry 4U's subquests (11491 had "None"): GU type 8 + code, decimal digits = break groups
  1-6 or 7 tail sever (C, GU quests); m11014 "Wound Gogmazios's back" = 5 (group 5 = bone 205 = back),
  m11035 "Sever Gogmazios's tail" = 7. Sub reward = 4U +0xAC; sub academy / sub HRP = 1/10 as GU. Reward slot 4
  (subquest) = row A's table, as 4U +0x24 and GU q0011413.
- Done earlier: 11491 = 4U m11014 "Advanced: Quagmire Quarrel" (G4 Hub, fee 3600z, reward 35400z, 50 min).
  - Kushala stands in for the board and loader, swapped to 0x59 at spawn.
  - Board icon: the user's HD UI resident_eng.arc patch (memory: HD UI icon patch).
- To port: 4U m11035 "Advanced: Act of Gog" (dump/romfs/loc/data/quest01.arc; fee 4600z, reward 45900z) as a second new quest id. Same builder (tools/build_gog_quest.py --source m11035), HP / attack table rows from it.
- Rewards: 4U reward tables of m11014 / m11035 mapped to the materials of section 2 (instead of the generic rem files).
- Multiplayer: Hub quests are shared with the room; every player needs the mod (notes/release-notes.md).
- Check: unlock conditions (module hooks quest_group_fix / quest_unlocked), and whether an Arena / Event variant is wanted.

## Appendix: 4U Gogmazios data (gear helper, 2026-10-20, from the 4U v1.1 exe in dump/exefs_v11)
4U tables:
- items 0xf029e4 (1937 x 20 B);
- equipment pointer table 0xf58868 (melee 24 B, bowguns / bow / armor 40 B);
- create recipes 0xf3f000..0xf55400 (24 B: u32 2, u16 type, u16 id, 4 x (u16 item, u16 count); type 1..5 armor, 7..20 weapon classes);
- upgrade recipes via pointer table 0xf56974;
- skill trees 0xf5dfb2 (160 x 30 B);
- carves 0x1001c06 / 0x1002136 / 0x10026f2, break rewards 0xf37a8e;
- m11014 rewards: dump/q4u_m19/m11014.1bbfd18e @0x10c0 / 0x1100.

Weapon stats (raw, affinity, status-3 value, slots G), create -> upgrade:

| Class | Create (id) | Raw | Aff | Status | Slots | Upgrade (id) | Raw | Aff | Status | Slots |
|---|---|---|---|---|---|---|---|---|---|---|
| GS | 222 | 280 | -10 | 130 | 1 | 223 | 300 | -20 | 180 | 1 |
| SnS | 227 | 290 | -10 | 70 | 0 | 228 | 310 | -10 | 140 | 0 |
| Hammer | 221 | 270 | -10 | 140 | 1 | 222 | 290 | -15 | 210 | 1 |
| Lance | 198 | 280 | -10 | 100 | 1 | 199 | 300 | -10 | 180 | 1 |
| LS | 199 | 270 | -10 | 90 | 0 | 200 | 290 | -15 | 160 | 0 |
| SA | 180 | 260 | -15 | 110 | 0 | 181 | 280 | -15 | 190 | 1 |
| GL | 201 | 280 | -10 | 120 | 0 | 202 | 300 | -10 | 240 | 0 |
| DB | 208 | 290 | -10 | 70 | 0 | 209 | 310 | -10 | 100 | 0 |
| HH | 164 | 270 | -10 | 110 | 0 | 165 | 290 | -15 | 150 | 0 |
| IG | 130 | 270 | -10 | | | 131 | 280 | -10 | | |
| CB | 98 | 270 | -10 | 80 | 0 | 99 | 290 | -10 | 110 | 0 |
| LBG | 165 | 300 | -10 | | | - | | | | |
| HBG | 141 | 310 | -15 | | | - | | | | |
| Bow | 183 | 280 | -10 | | | 184 | 300 | -15 | | |

Create recipes:

| Class | Materials |
|---|---|
| GS | Battlement 5, Fortress 5, Gasher 2, Oil 2 |
| SnS | Gasher 3, Fortress 5, Briartail 2, Oil 3 |
| Hammer | Battlement 7, Fortress 4, Oil 3, LED Bone 5 |
| Lance | Gasher 2, Offenders 4, Fiberwing 2, Oil 2 |
| LS | Offenders 4, Fiberwing 3, Briartail 2, Oil 3 |
| SA | Battlement 5, Fortress 5, Gasher 3, Briartail 2 |
| GL | Fortress 8, Battlement 4, Fiberwing 2, Oil 4 |
| DB | Offenders 4, Briartail 1, Fortress 4, LED Bone 8 |
| HH | Battlement 4, Fortress 4, Offenders 2, Oil 1 |
| IG | Fortress 3, Oil 4, Dragonsphire 1 |
| CB | Gasher 2, Fortress 8, Offenders 2, Oil 3 |
| LBG | Fortress 8, Offenders 4, Fiberwing 5, Dragonsphire 1 |
| HBG | Fortress 6, Fiberwing 4, Oil 4, Dragonsphire 1 |
| Bow | Fortress 8, Fiberwing 3, Oil 2, Gasher 4 |

Upgrade recipes (each also needs Dragonsphire 1 unless noted):

| Class | Materials |
|---|---|
| GS | Fortress 8, Offenders 2, LED Gem |
| SnS | Offenders 4, Fiberwing 2, LED Gem |
| Hammer | Gasher 4, Fortress 5, LED Gem |
| Lance | Gasher 2, Fortress 4, LED Gem |
| LS | Gasher 4, Fortress 3, Gravios Pallium 1 |
| SA | Gasher 5, Fiberwing 3, LED Gem |
| GL | Offenders 4, Fiberwing 2, LED Bone 5 |
| DB | Oil 4, Gasher 3, LED Gem |
| HH | Fiberwing 4, Gasher 2, LED Gem |
| CB | Fortress 12, Offenders 3, LED Gem |
| Bow | Offenders 5, Briartail 2, LED Gem |

Armor recipes (Blademaster = Gunner):

| Piece | Materials |
|---|---|
| Head | Gasher 2, Battlement 4, Fortress 2, Purecrystal 2 |
| Body | Battlement 3, Dragonsphire 1, Oil 5, Allfire Stone 3 |
| Arms | Offenders 5, Fiberwing 2, Fortress 5, Cosmicite Ore 3 (not in GU) |
| Waist | Fiberwing 2, Fortress 5, Seregios Dissenter 1, Briartail 1 |
| Legs | Fortress 5, Battlement 4, Offenders 5, LED Bone 6 |

Armor skill points per piece (Helm / Mail / Braces / Faulds / Greaves):

| Set | Skill | Points per piece | Total |
|---|---|---|---|
| Blademaster | Arcana | 2 each | 10 |
| Blademaster | Expert | 2/4/2/4/3 | 15 |
| Blademaster | Artillery | -/2/4/3/1 | 10 |
| Blademaster | Avarice | helm only | 3 |
| Blademaster | Sharpener | -1/-1/-3/-3/-2 | -10 |
| Gunner | Arcana | 2 each | 10 |
| Gunner | Dead Eye | 1/3/1/3/2 | 10 |
| Gunner | Normal Up | -/2/4/3/1 | 10 |
| Gunner | Normal S+ | 4/4 | 8 |
| Gunner | Avarice | | 3 |
| Gunner | Reload | -1/-3/-1/-3/-2 | -10 |

Palico gear: F Gog Burden S (helm 143), F Gog Prison S (armor 146).
