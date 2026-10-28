# Stygian Zinogre weapons (study 2026-10-28; built 2026-10-28)

C = read in the 4U v1.1 exe / GU 1.4 RomFS tables (or in code), S = strong, G = guess. Tools: tools/weapons4u.py
readers (weapon_4u, the upgrade table UPGRADE_4U, the create recipes CREATE_4U, the DB second elements DB2_4U), GU
weaponNNBaseData / LevelData / MsgData (6 strings per weapon: A, B, C names with their descriptions).
Generator: monsters/stygian_zinogre/tools/gear_weapons_em057_01.py (build.sh steps `weapons`, `gearw`).

## 1. The Stygian lines (C)
phase1-assets.md 4c had the classes wrong (it paired the "Despot's" names with the wrong class lists). The lines
whose recipes use Stygian materials are 4U's "Brimstren Drake*" weapons. Each branches off a Zinogre weapon (or
Distant Thunder for the Bow), and goes "Brimstren X" (HR, rarity 6) -> "Brimstren X+" (G, rarity 9) -> "Stygian
<vice / virtue>". LS and Bow end in a "Charonian" weapon with its own model. That is 12 classes (none for CB or IG)
and 37 weapons. The links (parent -> first weapon -> ... -> last, no child) are checked by the generator.

| GU | 4U parent (stage) | line (4U IDs) | models | element (4U value) |
|---|---|---|---|---|
| 00 GS | Despot's Blackstorm 28 (B) | 29 Drakepride, 155 +, 156 Stygian Acedia | 38 | dragon 44 / 49 / 55 |
| 01 SnS | Despot's Crookbolt 27 (B) | 28 Drakescale, 159 +, 160 Stygian Luxuria | 42 | dragon 35 / 39 / 43 |
| 02 Hammer | Despot's Crackle 25 (B) | 26 Drakemaw, 159 +, 160 Stygian Industria | 46 | dragon 36 / 40 / 44 |
| 03 Lance | Despot's Cacophony 53 (B) | 56 Draketail, 161 +, 162 Stygian Ira | 54 | dragon 35 / 38 / 42 |
| 04 HBG | Oppressor's Wedge 95 (B of Loyal Thunder) | 97 Drakemouth (G), 98 Stygian Humilitas | 46 | - |
| 06 LBG | Despot's Wildfire 17 (B) | 18 Drakekiss, 19 Drakevow (rarity 7), 103 Drakevow+, 104 Stygian Invidia | 30 | - |
| 07 LS | Usurper Boltslicer+ 41 (A+) | 43 Drakebone, 152 Stygian Gula, 153 Charonian Gula | 36, 82 | dragon 36 / 38 / 41 |
| 08 SA | Despot's Cloudburst 25 (B) | 26 Drakefang, 124 +, 125 Stygian Vanagloria | 38 | dragon 28 / 31 / 35 |
| 09 GL | Usurper's Roar+ 54 (A+) | 56 Drakeblood, 165 +, 166 Stygian Avaritia | 26 | dragon 26 / 33 / 37 |
| 10 Bow | Distant Thunder II 39 (GU: Usurper's Rumble, model 4); 41 also has a create recipe | 41 Drakegaze, 42 Drakeglare, 132 Stygian Patientia, 133 Charonian Patientia | 34, 81 | dragon 13 / 16 / 20 / 22 |
| 11 DB | Despot's Blitz 63 (B) | 65 Drakeclaws, 169 +, 170 Stygian Superbia | 40 | thunder 30 / 31 / 33 + dragon 28 / 32 / 36 |
| 12 HH | Usurper's Growl+ 23 (A+); 25 also has a create recipe | 25 Drakesong, 111 +, 112 Stygian Tristitia | 28 | dragon 24 / 30 / 36 |

- Models (C): every one of them is free in GU (no BaseData record, no arc/weapon/wNN/NNN.arc, no snd arc; checked by
  the generator) and against the other monsters' allocations.toml weapon_models (tools/alloc.py: OK).
- Out of scope, as with the armor rule: other monsters' weapons that use a Stygian item as one ingredient (Fatalis,
  Najarala, Zamtrios, Dah'ren Mohran, Gore / Seltas Queen lines and others).

### DB second element: settled (C)
The 4U melee record's +17 on a DB is an index into a 4-byte table at 0xf588f4 (weapons4u.DB2_4U): {u8 element, s8
value, u8 status, s8 value}, the melee record's own types and units; index 0 = single element. Read by 0x2f8a00 /
0x2f8d64 (DB only: create type 17) through the +17 getter 0x2f81c4. Indexes 1..30 are the 28 4U dual-element DBs
(0 on the 202 others); every GU same-name weapon of them has a mElement2 (Twin Nails: record blast 16 + table ice 40,
"fire and ice" text; GU e1 blast, e2 ice). Stygian: 3 / 18 / 19 = dragon 28 / 32 / 36 (280 / 320 / 360 shown).
GU order: mElement1 = the record's, mElement2 = the table's (S: the GU same-name dual DBs).

## 2. GU parents (C)
GU folded each 4U Zinogre line into one levelled weapon with three names (A Lv1..mMaxLv HR, B limit-broken G, C final;
notes/gear-weapons.md section 5, G). They serve as the stand-ins (section 4).

| GU | weapon (A / B / C) | levels | derive slots used |
|---|---|---|---|
| 00/9 | Usurper's Storm / Despot's Blackstorm / Oppressor's Forger | 4+3 | none |
| 01/19 | Usurper's Firebolt / Despot's Crookbolt / Oppressor's Bounty | 4+3 | none |
| 02/47 | Usurper's Thunder / Despot's Crackle / Oppressor's Sway | 4+3 | none |
| 03/42 | Usurper's Coming / Despot's Cacophony / Oppressor's Genesis | 4+3 | none |
| 04/101 | Loyal Thunder / Oppressor's Wedge / Orcus Quarcus | 2+1 | none |
| 06/18 | Usurper's Crime / Despot's Wildfire / Oppressor's Rift | 5+3 | Lv1 -> 19, Lv3 -> 104 |
| 07/28 | Usurper's Boltslicer / Despot's Boltbreaker / Oppressor's Law | 4+2 | Lv4 -> 121 |
| 08/25 | Usurper's Downpour / Despot's Cloudburst / Oppressor's Deluge | 4+3 | none |
| 09/36 | Usurper's Roar / Despot's Phlogiston / Oppressor's Skyfall | 4+3 | none |
| 10/3 | Usurper's Rumble (4U Distant Thunder, model 4) | - | - |
| 11/20 | Usurper's Fulgur / Despot's Blitz / Oppressor's Miracle | 4+3 | none |
| 12/43 | Usurper's Growl / Despot's Thunderclap / Oppressor's Boon | 4+3 | Lv2 -> 101 |

## 3. Plan (user 2026-10-28: standalone forging)
- Standalone lines, no GU weapon record touched. The first weapon's forge recipe is its own 4U create recipe where 4U
  has one (Bow 41 Drakegaze, HH 25 Drakesong), else its 4U upgrade recipe's materials (the parent weapon left out).
  Every later weapon is an upgrade of the previous one with its 4U upgrade recipe.

## 4. Built (2026-10-28)
Files: tools/gear_weapons_em057_01.py (new), build.sh (`weapons`, `gearw` in ALL before `pack`), allocations.toml
stygian_zinogre ([monster.weapon_models], append kireaji = 20, [monster.append.weapons] 37 rows),
tools/weapons4u.py (class spec `first_upgrade`; DB2_4U second element; Gogmazios / Tigerstripe / Dalamadur weapon
sections byte-identical before / after, cmp). Outputs: gen/TBLA-weapons.sec, gen/TXTA-weapons.sec (packed into
gen/stygian_zinogre.bin), romfs/nativeNX/arc/weapon/wNN/<model>.arc (14) and snd/<model>.arc (13).

| GU ID | weapon | rar | raw | aff | element | slots | recipe (C: the 4U exe's) |
|---|---|---|---|---|---|---|---|
| GS 144 | Brimstren Drakepride | 6 | 170 | 0 | dragon 440 | 2 | forge: Carapace 4, Dragonhair 5, Claw+ 3, Horn+ 2 |
| GS 145 | Brimstren Drakepride+ | 9 | 240 | 0 | dragon 490 | 2 | Cortex 3, Hardhorn 2, Drakehold 3 |
| GS 146 | Stygian Acedia | 10 | 270 | 0 | dragon 550 | 3 | Dragonlocks 6, Zinogre Lash 2, Lrg ElderDragon Bone 5, Skymerald 1 |
| SnS 138 | Brimstren Drakescale | 6 | 160 | 0 | dragon 350 | 0 | forge: Dragonhair 4, Horn+ 2, Carapace 4, Dracophage Bug 4 |
| SnS 139 | Brimstren Drakescale+ | 9 | 250 | 0 | dragon 390 | 0 | Dragonlocks 4, Hardhorn 2, Cortex 4, Lash 3 |
| SnS 140 | Stygian Luxuria | 9 | 270 | 0 | dragon 430 | 0 | Drakehold 4, Hardclaw 4, Skymerald 1, Chaos Scale 2 |
| Ham 141 | Brimstren Drakemaw | 6 | 170 | 0 | dragon 360 | 1 | forge: Carapace 4, Dragonhair 5, Drakeshell 3, Dracophage Bug 4 |
| Ham 142 | Brimstren Drakemaw+ | 9 | 270 | 0 | dragon 400 | 1 | Cortex 4, Dragonlocks 5, Drakehold 3, Dragonbone Artifact 3 |
| Ham 143 | Stygian Industria | 9 | 270 | 0 | dragon 440 | 1 | Hardclaw 4, Drakehold 4, Skymerald 1, Deviljho Hardfang 3 |
| Lan 136 | Brimstren Draketail | 6 | 180 | 0 | dragon 350 | 2 | forge: Horn+ 2, Drakeshell 5, Dragonhair 4, Dracophage Bug 10 |
| Lan 137 | Brimstren Draketail+ | 9 | 260 | 0 | dragon 380 | 2 | Hardhorn 2, Drakehold 5, Dragonlocks 4, Lash 2 |
| Lan 138 | Stygian Ira | 9 | 270 | 0 | dragon 420 | 2 | Cortex 5, Hardclaw 3, Skymerald 1, Deviljho Hardfang 4 |
| HBG 115 | Brimstren Drakemouth | 9 | 280 | 0 | - | 2 | forge: Cortex 4, Hardhorn 2, Drakehold 3, Dracophage Bug 10 |
| HBG 116 | Stygian Humilitas | 9 | 300 | 0 | - | 2 | Dragonlocks 5, Hardclaw 5, Lrg ElderDragon Bone 5, Skymerald 1 |
| LBG 116 | Brimstren Drakekiss | 6 | 190 | 10 | - | 1 | forge: Carapace 5, Dragonhair 6, Horn+ 2, Dracophage Bug 8 |
| LBG 117 | Brimstren Drakevow | 7 | 210 | 10 | - | 1 | Drakeshell 6, Claw+ 3, Umbrage 1, Elder Dragon Blood 1 |
| LBG 118 | Brimstren Drakevow+ | 9 | 280 | 10 | - | 1 | Cortex 5, Dragonlocks 6, Hardhorn 2, Dragonbone Artifact 3 |
| LBG 119 | Stygian Invidia | 9 | 300 | 10 | - | 1 | Drakehold 6, Hardclaw 3, Skymerald 1, Lrg ElderDragon Bone 5 |
| LS 134 | Brimstren Drakebone | 6 | 170 | 0 | dragon 360 | 2 | forge: Horn+ 2, Carapace 5, Claw+ 6, Umbrage 1 |
| LS 135 | Stygian Gula | 9 | 250 | 0 | dragon 380 | 2 | Drakehold 4, Dragonlocks 2, Lash 1, Dragonbone Artifact 6 |
| LS 136 | Charonian Gula | 9 | 260 | 0 | dragon 410 | 2 | Hardhorn 2, Hardclaw 6, Deviljho Ripper 3, Skymerald 1 |
| SA 119 | Brimstren Drakefang | 6 | 170 | 0 | dragon 280 | 0 | forge: Horn+ 2, Carapace 4, Dragonhair 5, Dracophage Bug 5 |
| SA 120 | Brimstren Drakefang+ | 9 | 250 | 0 | dragon 310 | 0 | Hardhorn 2, Cortex 4, Dragonlocks 5, Dragonbone Artifact 3 |
| SA 121 | Stygian Vanagloria | 9 | 280 | 0 | dragon 350 | 0 | Hardclaw 3, Drakehold 4, Skymerald 1, Lrg ElderDragon Bone 6 |
| GL 124 | Brimstren Drakeblood | 6 | 180 | 0 | dragon 260 | 0 | forge: Carapace 4, Dragonhair 5, Claw+ 3, Horn+ 1 |
| GL 125 | Brimstren Drakeblood+ | 9 | 260 | 0 | dragon 330 | 0 | Cortex 4, Dragonlocks 4, Hardclaw 3, Hardhorn 2 |
| GL 126 | Stygian Avaritia | 9 | 280 | 0 | dragon 370 | 0 | Hardhorn 3, Drakehold 8, Skymerald 1, Lrg ElderDragon Bone 4 |
| Bow 117 | Brimstren Drakegaze | 6 | 180 | 0 | dragon 130 | 0 | forge (4U create): Carapace 5, Horn+ 3, Claw+ 4, Umbrage 1 |
| Bow 118 | Brimstren Drakeglare | 6 | 190 | 0 | dragon 160 | 0 | Dragonhair 6, Umbrage 1, Deviljho Scale 6, Elder Dragon Blood 1 |
| Bow 119 | Stygian Patientia | 9 | 250 | 0 | dragon 200 | 1 | Cortex 4, Hardhorn 2, Hardclaw 3, Dragonbone Artifact 2 |
| Bow 120 | Charonian Patientia | 9 | 270 | 0 | dragon 220 | 2 | Dragonlocks 6, Skymerald 1, Bloodied Ebonhide 6, Lrg ElderDragon Bone 6 |
| DB 135 | Brimstren Drakeclaws | 6 | 180 | 0 | thunder 300 + dragon 280 | 1 | forge: Horn+ 2, Dragonhair 4, Zinogre Carapace 4, Zinogre Claw+ 3 |
| DB 136 | Brimstren Drakeclaws+ | 9 | 240 | 0 | thunder 310 + dragon 320 | 1 | Hardhorn 2, Zinogre Hardhorn 2, Dragonlocks 4, Zinogre Electrofur+ 4 |
| DB 137 | Stygian Superbia | 9 | 260 | 0 | thunder 330 + dragon 360 | 1 | Lash 3, Zinogre Lash 3, Skymerald 1, Deviljho Ripper 3 |
| HH 119 | Brimstren Drakesong | 6 | 170 | 0 | dragon 240 | 1 | forge (4U create): Horn+ 4, Carapace 7, Drakeshell 6, Umbrage 1 |
| HH 120 | Brimstren Drakesong+ | 9 | 250 | 0 | dragon 300 | 1 | Hardhorn 2, Cortex 4, Drakehold 3, I.Lagi D-Shocker 4 -> Deathly Shocker 4 |
| HH 121 | Stygian Tristitia | 9 | 270 | 0 | dragon 360 | 1 | Drakehold 4, Dragonlocks 5, Skymerald 1, Lrg ElderDragon Bone 5 |

(Short item names = the S.Zinogre / S.Zin items; rarity as 4U shows it, GU mRare = that - 1. Raw is true raw.)

C (from the 4U records, weapons4u): raw, affinity, defense 0, slots, rarity, prices (55000 / 95000 / 120000; LBG
35000 / 50000; Bow 65000), elements (none hidden, no status), sharpness (20 4U entries appended to kireajiData as
GU 208..227, mKireLevel = 2 x the 4U level: 8 HR, 10 / 8 G), GL Long Lv3 / Lv4 / Lv4 (4U extra 7 / 10 / 10), SA Power
phial, HH note set 6 = GU fueMusicData 6, bowgun ammo counts and loadable flags, bow charges (4U +22 + 1: Drakegaze / Drakeglare
Pierce 2 / Rapid 3 / Rapid 4 / Spread 4, Patientia ... / Spread 5, Charonian ... / Rapid 5 / Spread 5), 3 charge levels,
coatings Power / Poison / C.Range / Paint (4U mask 0x66), names and descriptions in the 5 languages (4U's).
C: models = 4U's numbers; motion sets: GU's pl_wNN record at each number points at a gNN arc GU has (no PWLF fix);
sounds: every 4U arc holds its own model's set (mSrqrNo = model, converted, `wsnd4u2gu.py check`: no missing wave),
except hbg046 = set 19 = Oppressor's Wedge's (4U model 19 = GU Loyal Thunder 19): mSrqrNo 19, GU's own snd/019.arc.

### Stand-ins and deviations from 4U (each one explicit)
1. Bow arc shot (G): not in the 4U record (weapons4u notes) -> the stand-in Usurper's Rumble's mKyoku 1 (GU's form
   of the Brimstren bow's 4U parent line Distant Thunder). 4U's value for the Brimstren bows unread.
2. Bowgun recoil / reload / deviation / rapid (LBG) or crouch (HBG) fire / special ammo / ammo slot 32 (G): from the
   GU parent's final level row (HBG Loyal Thunder 101 Lv3 = Orcus Quarcus: recoil 7, reload 5, mBure 0, crouch
   [45, 24, 4]; LBG Usurper's Crime 18 Lv8 = Oppressor's Rift: recoil 7, reload 5, mBure 0, rapid [16, 27]). 4U
   deviation +5 = 0 on all six records = mBure 0 (agrees). Recoil / reload / rapid / special maps are unresolved.
3. 4U loadable ammo without a GU slot, left out: HBG Slicing (3 / 4), 4U 32 (1), 37 (1), 38 (2); LBG Slicing 4,
   4U 31 / 32 (Demon / Armor, 1 each).
4. Recipe item GU lacks (G): I.Lagi D-Shocker (Ivory Lagiacrus, not in GU) -> Deathly Shocker (Lagiacrus' G shell,
   same part and rank), Brimstren Drakesong+ upgrade.
5. First weapon's forge recipe for the 10 lines without a 4U create recipe: the materials of its 4U upgrade recipe
   (user's choice; 4U forges none of them, it upgrades the Zinogre parent).
6. Model lan054 / lbg030 (open, item 1 below): converted with a sphere-map fallback not yet in tools/weapon4u2gu.py:
   lan054's alpha-tested XfBA0 material -> GU ham025 mat 3 (alpha test as 4U, no sphere map; the converter's choice,
   CB blade011, has a sphere map the 4U material lacks), lbg030's env material XfB__E (4U tExtendMap index 0: no env
   texture) -> GU two034 mat 1 instead of its exact pair lan039 (sphere map).

### Open
1. tools/weapon4u2gu.py refuses lan054 (with --alpha-test-4u) and lbg030 (always): "template ... has a sphere map, 4U
   material none". The arcs in romfs/ were made with a wrapper (session scratchpad wconv_nosphere.py) whose rule is:
   pick_template, when its choice has a tSphereMap slot and the 4U material no real tExtendMap texture, picks again
   among the templates without a sphere map. Every conversion that succeeds today is unchanged by it (it only runs
   where convert() exited). Until that rule is in the converter, `build.sh weapons` stops at lan054.
2. In-game test: smithy listing (first recipe item owned), models / motion / sounds of all 14 arcs, the DB dual
   element display, the bow arc shot.
