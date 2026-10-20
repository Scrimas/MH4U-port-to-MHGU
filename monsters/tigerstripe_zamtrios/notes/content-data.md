# Tigerstripe Zamtrios: MH4U content data for Phase 4 (static, 2026-10-20)

Source: 4U v1.1 EUR exe `dump/exefs_v11/mem.bin` (address A = file offset A - 0x100000), 4U RomFS text
(`dump/romfs/<lang>/data/core_common.arc`, lmd), quests `dump/romfs/loc/data/quest01.arc`. GU side: MHGU_Editor
`scratch/base_romfs.bin` (resident.arc, resident_eng.arc, blacksmith.arc, result.arc). Read-only research; scratch
scripts: `/tmp/claude-1000/-home-scrimas-Projects-MH4U-MHGU-port/aa473438-013b-4411-b8ca-5d2f95908e85/scratchpad/content/t*.py`.
Tags: C confirmed in code/data, S strong, G guess. "GU id" = GU item / tree / weapon found by identical English name.
TS materials -> GU slots (allocations.toml order, S): 1357 -> 2986, 1358 -> 2987, 1359 -> 2988, 1360 -> 2989, 1361 -> 2990.

## 0. Table locations found (new, C unless noted)

| what | 4U location | index |
|---|---|---|
| carve points per monster | u32 [0x1003bec + 4*em] -> 16-B records {u16 base, u16 carves (S), f32 (450 for em22/92; G radius), u8 +11 part/0xff, ...} | record = carve point (code 0x926044: `[r7]` base + rank) |
| carve / shiny tables | u32 [0x1002a5c + 4*idx] -> GU-format table {u16 count<<8 \| chance, u16 item} closed by 0xFFFF | carve idx = base + rank; shiny idx = u16[0x1003ddc + 2*em] + 4*set + rank (0x911f58) |
| rank | 0x6bc55c(...): 0 / 1 low / 2 high / 3 G (G = 3 as in hagi_em089) | |
| shiny set | 0x930bdc: special cases em 17/18/22/44/50/66/67/89 only; **any other em (92) returns 0** | |
| break rewards | i32 [0xf384d0 + 4*em] = base (-1 none) -> u32 [0xf386c0 + 4*(base + 4*group + rank)], rank clamped to 3, idx <= 0x573 (getter 0x68effc; one caller 0xabf818, quest-end list quest+0xAD9C {s16 em, u8 group, u8 count, u16 flags}) | group 0..7 (8 refused) |
| break adder | 0x6a8920(mgr, em, group, flags): monster-side callers 0x91dc54, 0x9453b0 (part table from 0x91df20()+0x78, 32-B records, group = byte +4 & 0x7f), 0x949eb0 | part -> group map of em092 NOT traced |
| weapon tree | upgrade table record (24 B per weapon id, via 0xf56974): +0 4 x {u16 item, u16 count} = materials to MAKE this weapon by upgrade; **+16 4 x u16 = child weapon ids** (C: every TS line links up) | IG table 0xf569a8 has no child ids |
| em_nando_tbl | 0xf3a330, 32-B rows {HP, attack, defense, 5 status}; 5 pointers to it at 0xf3c960..0xf3c970; monster work +0x416 = HP row byte (0x91ca94) | |

Cross-check: em089 through these tables gives exactly hagi_em089's records (0x1002f70 = 0x1002a5c + 4*(324+1), body
base 324; tail base 568) and items_em089's break table (0xf3946c = 0xf386c0 + 4*(872+3)). The "filler" 4th column
hagi_em089 reads is the next record's rank-0 slot (harmless).

## 1. Materials (4U 1357..1361) (C)

4U item record (0xf029e4 + 20k): all type 0, carry 99, flags 0. Rarity 8 for all five.

| 4U id | Name | Icon | Colour | Sort | Sell | Buy | GU slot | GU template (icon, cat) |
|---|---|---|---|---|---|---|---|---|
| 1357 | T.Zamtrios Shard | 12 | 4 | 565 | 8650 | 86500 | 2986 | 944 Zamtrios Shard (12, cat 3) |
| 1358 | T.Zamtrios Piel | 11 | 4 | 564 | 4790 | 47900 | 2987 | 942 Zamtrios Piel (11, cat 2) |
| 1359 | T.Zamtrios Grandfin | 13 | 4 | 566 | 9710 | 97100 | 2988 | 946 Zamtrios Grandfin (13, cat 4) |
| 1360 | T.Zamtrios Sawtooth+ | 10 | 4 | 567 | 6240 | 62400 | 2989 | 948 Zamtrios Sawtooth+ (10, cat 4) |
| 1361 | T.Zamtrios Tailbrand | 13 | 4 | 568 | 5610 | 56100 | 2990 | 950 Zamtrios Tailbrand (13, cat 5) |

- Icon 13 is ambiguous inside GU's Zamtrios set (Grandfin cat 4, Tailbrand cat 5): take the same-name counterpart.
- 4U plain Zamtrios uses colour 6, TS colour 4 (own colour). GU's G Zamtrios records end `.. 9x 00` at +0x1c (0x91 on
  all G mats, 0x90 on rare-6; +0x1d = 0x0d/0x0e on Hyper mats only).
- GU retuned plain Zamtrios prices (GU Sawtooth+ 9000, Tailbrand 8100 vs 4U 4800 / 4320): use 4U's TS prices (as Gogmazios).
- English descriptions (itemExp_eng; fre / ger / ita / spa also present, short names e.g. "Éclat Zamtrios tigré"):
  - 1357 "A hard, thick scale whose\nsmooth surface was created\neither by or for the sand."
  - 1358 "A thick, elastic hide that\nretains water well, making\nit perfect for desert hunts."
  - 1359 "A huge dorsal fin that makes\ncaravan merchants uneasy\nwhen sighted in the sands."
  - 1360 "A triangular tooth that, in\ntandem with its brothers,\ndigs in and saws prey apart."
  - 1361 "A huge tail with a barb on\nthe end. Mows targets down\nin the blink of an eye."
- No T.Zamtrios scrap / Palico item exists in 4U (C: only 1357..1361 carry the "T.Zamtrios" name).

## 2. Carves and shiny drops (C)

TS (em 92) is **G rank only**: ranks 1 / 2 null, rank 0 = First-aid Med filler (as em089).

| table | 4U address | entries (count 1 each): chance %, 4U item -> GU |
|---|---|---|
| body (only carve point; 3 carves, S) | 0x1001c52 | 33 Piel -> 2987; 25 Shard -> 2986; 16 Omniplegia Sac 1604 -> 455; 10 Grandfin -> 2988; 8 Sawtooth+ -> 2989; 8 Tailbrand -> 2990 |
| tail | none | em092 has ONE carve-point record (em022 too: no tail carve in 4U) |
| shiny set 0 (the only set) | 0x1002722 | 55 Large Toad Tear 824 -> 2123; 35 Shard -> 2986; 10 Paddock Cream 1607 -> 927 |

- 4U entry order (file order): Shard 25, Sawtooth+ 8, Piel 33, Omniplegia 16, Grandfin 10, Tailbrand 8.
- Shiny base 928 (em 93 starts at 932): set 1 would read Tidal Najarala's table, but 0x930bdc returns 0 for em 92.
- GU layout to copy (GU em067_00 hagi_s4, C): body = table 0, shiny set 1 = header byte +14, set 2 = +15
  (GU's set 2 = Zamtrios' ice-armor shiny, Ice Crystal 75 %): TS fills set 1 only (or both with the same table, port choice).
- GU's own G Zamtrios body carve differs from 4U em022's (GU: Shard 27, Scale+ 8, Sawtooth+ 8, Piel 20, Cryo 14, Grandfin 15,
  Tailbrand 8): GU retuned, so take nothing from GU's numbers.

## 3. Break rewards (C contents; part names S/G)

em 92 base 928, 6 groups (em 93 at 952); ranks 0..2 empty, G (rank 3) tables at 0xf37ba0..0xf37c04.

| 4U group | table | entries (chance, count, 4U item -> GU) | part | GU cond |
|---|---|---|---|---|
| g0 | 0xf37ba0 | 36 Piel x1 -> 2987; 20 Shard -> 2986; 14 Sawtooth+ -> 2989; 20 Omniplegia Sac -> 455; 10 Paddock Cream -> 927 | ? (G; GU keeps the same kind of table at cond 10 = group 0) | 10 |
| g1 | 0xf37bc0 | 50 Vile Frenzy Crystal 690 x1 -> 2136; 25 Vile Frenzy Crystal x2 -> 2136; 25 Pure Frenzy Crystal 1645 -> no GU item | Frenzy overcome (S: frenzy crystals; same table on em022) | none |
| g2 | 0xf37bd4 | 100 Sawtooth+ -> 2989 | head (S) | 20 |
| g3 | 0xf37bdc | 24 Shard -> 2986; 65 Grandfin -> 2988; 11 Piel -> 2987 | **dorsal fin (C: m10821 subquest "Wound T.Zamtrios's dorsal fin" = code 3)** | 30 |
| g4 | 0xf37bf0 | 32 Grandfin -> 2988; 44 Shard -> 2986; 24 Piel -> 2987 | ? (G: front legs) | 40 |
| g5 | 0xf37c04 | 24 Shard -> 2986; 65 Tailbrand -> 2990; 11 Piel -> 2987 | tail (S) | 50 |

How the mapping was made:
- GU em067 (Zamtrios) break record bui_s4 (result.arc, file record 462 B: u16 em, 18 x {u8 cond, u8 count}, entries
  {u8 chance, u8 count, u16 item} + ff terminator per group) has conds 10/20/30/40/50 whose item mixes equal 4U
  em022's g0/g2/g3/g4/g5 (C: Piel/Shard/Sawtooth+/Cryo/Cream; Sawtooth+ 90; Grandfin 63; Grandfin 40 / Shard 30 / Piel
  20; Tailbrand 75); 4U g1 (frenzy) has no GU counterpart.
- GU cond = 10 * (GU break group + 1) (module/items.c); GU Zamtrios subquests (C): code 1 "Wound Zamtrios's head",
  2 "top fin", 14 "head and tail" -> GU group 1 head, 2 top fin, 4 tail.
- So 4U group k (k >= 2) = GU group k - 1, 4U g0 = GU g0 (S, valid as long as variant 1 keeps GU em067's break parts).
- The 4U part -> group map of em092 itself is NOT traced (break adder callers above).

## 4. Quests m10821 / m10830 (quest01.arc, both 'v005') (C unless noted)

| field (4U offset) | m10821 "Grand Finals Confrontation" | m10830 "Advanced: Tiger-sharq" |
|---|---|---|
| +0xC0 quest no / +0xC2 stars | 10821 / 8 (= G1, S) | 10830 / 8 |
| +0xC4 stage | 17 (Dunes day) | 17 |
| +0xA4 fee / +0xA8 reward / +0xAC sub reward | 1100 / 11100 / 3700 (= reward / 3) | 1400 / 13200 / 4400 |
| +0xB0 (HRP? G) / +0xB8 (?) | 3000 / 30 | 3300 / 30 (m11014: 4200 / 0) |
| +0xB4 minutes | 50 | 50 |
| +0xA0 bytes / +0xC5 | 03 22 40 00 / 0x20 | 03 02 40 02 / 0x20 |
| objective +0xCC / +0xD0 | 01.. / hunt em 0x5c x1 | same |
| subquest +0xDC / +0xE0 | 04 02 / {em 0x5c, code 3}: "Wound T.Zamtrios's dorsal fin" (= 4U break g3) | 04 **40** / {em 0x5c, 2}: **"Suppress its Frenzy (2x)"** |
| boss spawn (+0x28 -> rec) | 0x1960: em 92, x1, area byte 4, +0xF = 0, pos (x -996, y 57, z 2142), 4th f32 0 | 0x1820: same, **+0xF = 1** (only difference: a frenzied TS, S; description "a frenzied Zamtrios") |
| monster rows +0x34 (8 B, S) | {u16 size 100, u8 0x1c (size table? G), **HP row 60, attack row 100, other row 82**, 04, 02} | same bytes |
| rows +0x44 / +0x4c / +0x54 (G) | 00 00 1c 36 64 38 04 02 / same / 00 00 1d 41 69 52 04 02 | 1c 36 64 38 / 1b 36 64 38 / 1d 41 6b 52 (same pattern) |
| row +0x5c (small monsters? G) | 64 00 00 3e 58 25 00 00 | same |
| icons +0xE8 5 x u16 (S) | 102, 84, 98, 98, 98 | 102, 88, 84, 98, 98 |
| text client / other monsters | Bumbling Entrepreneur / "Bnahabra\r\nHermitaur" | The Professor / same |
| supplies (+0x08 list {u8 kind, u8 n, ptr}) | kind 0: Map, Torch, Cool Drink 2 (x4 each); kind 1: First-aid Med+ 2 x4, Ration 2 x4, Mini Whetstone 2 x2, Paintball x2, Normal S Lv2 30, Pellet S Lv1 10, Recover S Lv1 5, Freeze S 15, Poison Coating 15, Empty Phial 10, Nulberry 2 x2; kind 3 (8): First-aid Med+ 2, Ration 3, Mini Whetstone 2, Pellet S Lv1 10, Poison Coating 15 | same (+ Nulberry 2 in kind 3) |
| small spawns +0x30 (44-B records) | em 0x32 (area 7), em 0x28 (area 2), em 0x0a (area 7) | same layout |

Rows (S): HP 60 = 1.9, attack 100 = 6.5, defense row 82 = 0.8 (em_nando_tbl). Order {HP, attack, other} chosen because
the values match GU's own G1 Zamtrios quest 11207 in size (rows 67 / 86 / 85) and every 4U quest's three bytes grow with
star level; **not confirmed in code**. Icons +0xE8: value = em + ~2 for every monster over all 508 4U quests (Zamtrios
24, TS 102), 98 = empty; so these are NOT stat rows (S).
- **Consequence for Gogmazios (outside this port, S):** build_gog_quest.py / port-checklist read "row 98 for all three"
  for m11014; 98 is the empty-icon filler. m11014's +0x34 record is {100, 0, 65, 109, 79, 0, 0} (HP 2.05, attack 8.2,
  def 0.8), m11035 {100, 0, 69, 115, 83, 0, 1} (the 1 at +7 is probably the "spawn byte 3" seen at runtime, G).

Rewards (both quests identical; GU via the material slots):

| row | 4U list flags | entries (chance, count, item -> GU) |
|---|---|---|
| A (+0x1C) = subquest (+0x24) | 0x8000 | 22 Piel -> 2987; 16 Grandfin -> 2988; 16 Shard -> 2986; 14 Omniplegia Sac -> 455; 12 Sawtooth+ -> 2989; 10 Paddock Cream -> 927; 10 Massive Bone 1613 -> 426 |
| B (+0x20) | **0x8003** | 10 Eltalite Ore 1635 -> 330; 7 Carbalite Ore 216 x2 -> 329; 8 Dragonbone Relic 276 -> 427; 12 Hot Pepper 185 x2 -> 280; 8 Lazurite Jewel 958 -> 342; 8 Hard Armor Sphere 228 x2 -> 349; 16 Heavy Armor Sphere 229 -> 350; 9 Shining Charm 37 -> 354; 6 Timeworn Charm 38 -> 355; 10 Stam Nectar: Water 135 -> no GU item; 6 Power+ Nectar: Fire 147 -> no GU item |

- quest4u.rem_4u / build_gog_quest assert list flags == 0x8000: row B's 0x8003 fails that assert (130 of 508 4U row-B lists
  use 0x8003; meaning of the low bits not traced, G: draw count / condition).
- GU subquest for m10821: type 8, code 2 (GU top-fin group, S). m10830's frenzy subquest has no GU equivalent (G: GU
  has no frenzied monsters), nor does its frenzied spawn flag.
- Exe copies of TS reward lists exist at 0xfcc830 (= row A) and 0xed5d08.. (100 % Piel + a second list): probably
  Guild Quest / other modes (not traced, not needed).

## 5. Armor (C)

One series uses the TS materials: 4U **"Zamtrios Z"** (G rank). GU has only Zamtrios (series 373 / 374, rarity 5) and
Zamtrios X (851 / 852, rarity 8): no Z series (C, armorSeriesData_eng names). 4U models 436 (Blademaster) / 437
(Gunner), male = female number; no GU series and no GU file uses 436 / 437 (C).

Create recipe types (C, Gogma cross-check): 5 head, 1 body, 2 arms, 3 waist, 4 legs; equipment pointer table 0xf58868
entries 33 / 29 / 30 / 31 / 32. Blademaster = even id, Gunner = id + 1 (same recipe).

| part | 4U ids (B / G) | Blademaster / Gunner name | slots | recipe (B = G) |
|---|---|---|---|---|
| head | 528 / 529 | Zamtrios Helm Z / Cap Z | 0 | Shard 2, Piel 4, Sawtooth+ 2, Meaty Piel 1618 3 (no GU item) |
| body | 532 / 533 | Zamtrios Mail Z / Vest Z | 0 | Grandfin 2, Shard 2, Paddock Cream 1, Crushing Fang 1619 3 (GU 437) |
| arms | 516 / 517 | Zamtrios Braces Z / Guards Z | 2 | Piel 4, Shard 2, Paddock Cream 3, Meaty Piel 2 |
| waist | 516 / 517 | Zamtrios Faulds Z / Coat Z | 3 | Piel 4, Grandfin 2, Tailbrand 1, Omniplegia Sac 1 |
| legs | 524 / 525 | Zamtrios Greaves Z / Leggings Z | 2 | Shard 2, Piel 4, Grandfin 2, Omniplegia Sac 3 |

- All pieces: rarity 8, price 7000 z, defense 86 Blademaster / 46 Gunner; resist F W T I D: Blademaster 2 / 3 / -4 / 0 / -5,
  Gunner 3 / 4 / -3 / 1 / -4. Record byte +4 = 0x07 (head 0x0f) Blademaster, 0x1b (head 0x1f) Gunner.
- For the GU defense: 4U Zamtrios X = 84 / 45, GU Zamtrios X = 102 / 61 (ratios 1.21 / 1.36; GU also changed X's resists).
- Skills (4U tree id -> GU tree id by name), points head / body / arms / waist / legs:

| tree (4U id) | GU tree | Blademaster | Gunner | total |
|---|---|---|---|---|
| Stam Recov (100) | 80 | 1 / 4 / 1 / 1 / 3 | 2 / 4 / 1 / 1 / 2 | 10 |
| Rec Speed (111) | 118 | 4 / 4 / 2 / 3 / 2 | same | 15 |
| Tremor Res (123) | 7 | 2 / 1 / 3 / 2 / 2 | same | 10 |
| FreeElemnt (17) = Awaken tree | **none in GU** | 3 / - / 2 / - / - | same | 5 |
| Bleeding (135) | 17 | -4 / -1 / -2 / -2 / -1 | same | -10 |

- Descriptions: 4U HeadExp etc. via the EXP_4U index tables of gear_em089 resolve to TS texts (e.g. head "Head armor made
  from rubbery\nTigerstripe Zamtrios parts. ...").
- Another series' piece also uses TS Piel: legs 830 / 831 Kita Star Hakama / Umi Ocean Hakama (Argosy Ticket 1876 1 (no GU
  item), T.Zamtrios Piel 3, Fine Black Pearl 1 (GU 970); rarity 8, def 84 / 45). GU already has Kita Star (423 / 424) and
  GX Kita Star (1223 / 1224) with its own recipes: nothing to port (S).

## 6. Weapons (C)

Melee record decode per notes/gear-weapons.md section 7 (status type 2 = Paralysis; negative value = hidden). Sharpness
= index into 0xf581e4 (7 cumulative u16, red..purple) / level (base bar 150 + 50 x level, +50 Handicraft, cap 450;
GU mKireLevel = 2 x level). Price = the record's u32 (create cost 1.5x of it per the Gogmazios notes, G). "upg" =
materials to make the weapon by upgrade from its parent. None of these weapons exists in GU by name (C).

TS lines (Kiranico's 17, all confirmed, + the Lance line Kiranico's list lacks):

| class | id | name | raw | aff | status | slots | sharp idx/lv: cumulative | rare | price | extra | parent (4U) -> GU parent |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SnS | 175 | Agate Saw | 240 | 0 | Para 100 | 1 | 92/4: 160 190 250 300 330 420 450 | 8 | 70000 | - | 57 Sharfinisher (4U G, not in GU) <- 56 Sharfin Sword = GU SnS 44 |
| SnS | 176 | Zamtrista Saw | 280 | 0 | Para 130 | 1 | 63/5: 70 110 160 310 380 430 450 | 9 | 110000 | - | 175 |
| Hammer | 177 | Puffer Smash | 220 | 0 | Para 200 | 2 | 81/4: 100 160 200 270 320 420 450 | 8 | 70000 | - | 54 Pressure Cooker (not in GU) <- 53 Meaty Press = GU 40 |
| Hammer | 178 | Pufferpounder | 260 | 0 | Para 260 | 2 | 68/5: 30 60 230 310 350 430 450 | 9 | 110000 | - | 177 |
| Lance | 167 | Carnelian Lance | 240 | 0 | Para 320 hidden | 2 | 88/5: 80 130 180 340 380 450 450 | 8 | 70000 | - | 60 Omnivoracious (not in GU) <- 59 Omnivicious = GU 52 |
| Lance | 168 | Crystalis | 270 | 0 | Para 360 hidden | 2 | 56/5: 70 110 230 320 380 440 450 | 9 | 100000 | - | 167 |
| GL | 144 | Tetrozonata | 230 | 0 | Para 200 | 2 | 88/5 (as above) | 8 | 70000 | shell 9 = Normal Lv4 (formula G) | 33 Deep Gunbuster (not in GU) <- 32 Deepbuster = GU 15 |
| GL | 145 | Velenofragola | 260 | 0 | Para 250 | 2 | 75/5: 110 220 270 330 360 440 450 | 9 | 110000 | 9 | 144 |
| SA | 130 | Allagi Tigermaw | 230 | 0 | Para 200 | 0 | 92/4 | 8 | 70000 | phial 0 Power | 31 Notched Oppressor (not in GU) <- 30 Notched Tyrant = GU 14 |
| SA | 131 | Zamtreacherous Maw | 270 | 0 | Para 240 | 0 | 91/5: 100 180 220 280 350 430 450 | 9 | 110000 | 0 | 130 |
| CB | 63 | The Haboob | 220 | 0 | Para 180 | 1 | 81/4 | 8 | 70000 | phial 0 Impact | 22 Squaliarmada (not in GU) <- 21 Squaliarma / 122 Deceadeus (neither name in GU) |
| CB | 64 | Desert Rose | 250 | 0 | Para 220 | 1 | 73/5: 80 200 270 310 340 430 450 | 9 | 110000 | 0 | 63 |
| DB | 151 | Sandgnashers | 230 | 0 | Para 100 | 1 | 2/4: 70 100 200 290 360 400 400 | 8 | 70000 | - | 34 Frozen Cleavers (not in GU) <- 33 Cool Cleavers = GU 12 |
| DB | 152 | Psammophages | 280 | 0 | Para 150 | 1 | 80/5: 180 200 260 330 380 430 450 | 9 | 110000 | - | 151 |
| IG | 72 | Sand Fauchard | 230 | 0 | Para 100 | 0 | 60/3: 80 100 190 260 360 420 450 | 8 | 56667 | kinsect 0 Cutting | create only (IG table has no tree) |
| IG | 73 | Sand Fauchard+ | 260 | 0 | Para 120 | 0 | 81/4 | 9 | 95000 | upg kinsect field 7 | 72 (G: consecutive ids) |
| IG | 74 | Iörovellir | 280 | 0 | Para 150 | 0 | 59/5: 90 160 240 300 370 420 450 | 9 | 130000 | upg kinsect field 10 | 73 (G) |
| Bow | 122 | Quartzlight | 260 | 0 | none decoded | 3 | - | 8 | 70000 | charges 07 08 03 03 (Spread3 Spread4 Rapid4 Rapid4 by the G enum), +15 = 3 | 24 Freezing Alighter (not in GU) <- 23 Ice Cold Alighter = GU 27 |
| Bow | 123 | Crystal Lode | 290 | 0 | none decoded | 3 | - | 9 | 110000 | 08 09 03 04 (Spread4 Spread5 Rapid4 Rapid5) | 122 |

Models (u16 +0): SnS 104, Hammer 106, Lance 90, GL 89, SA 84, CB 34, DB 95, IG 38, Bow 83 (same for both of a line).
Bow element: bytes +18/+19 (elem) and +20/+21 are 0 on both bows (C), so no element/status unless it sits in an
undecoded byte (check Kiranico).

Recipes (create = 4U create table; upg = upgrade table of the weapon itself):

| weapon | create | upg |
|---|---|---|
| Agate Saw | Grandfin 6, Shard 8, Paddock Cream 4, Omniplegia 8 | Grandfin 4, Piel 3, Sawtooth+ 4, Omniplegia 4 |
| Zamtrista Saw | - | Grandfin 6, Shard 5, Paddock Cream 4, Brach Crown 4 (GU 1078) |
| Puffer Smash | Grandfin 7, Sawtooth+ 6, Paddock Cream 5, Massive Bone 7 | Grandfin 3, Shard 7, Piel 5, Rhenoplos Bone 1615 4 (no GU) |
| Pufferpounder | - | Grandfin 4, Massive Bone 8, B.Diablos Cortex 1542 2 (no GU), Omniplegia 5 |
| Carnelian Lance | Sawtooth+ 6, Piel 8, Omniplegia 6, Rhenoplos Bone 8 (no GU) | Sawtooth+ 3, Piel 5, Omniplegia 4, Rhenoplos Bone 3 |
| Crystalis | - | Tailbrand 4, Grandfin 3, Paddock Cream 3, Tigrex Hardfang 1303 5 (GU 1388) |
| Tetrozonata | Grandfin 6, Piel 8, Tailbrand 4, Fey Wyvern Gem 1606 1 (GU 439) | Grandfin 4, Piel 6, Tailbrand 2, Sawtooth+ 2 |
| Velenofragola | - | Shard 8, Paddock Cream 4, Diablos Tailcase+ 1540 2 (GU 1433), Diablos Hardhorn 1539 1 (GU 1430) |
| Allagi Tigermaw | Tailbrand 5, Omniplegia 8, Cephalos Grandfin 1564 3 (GU 809), Cephalos Hardfang 1567 5 (GU 812) | Grandfin 4, Tailbrand 4, Omniplegia 4, Massive Bone 5 |
| Zamtreacherous Maw | - | Grandfin 5, Sawtooth+ 5, D.S.Queen Pectus+ 1398 3 (no GU; GU has S.Queen Pectus+ 1024), D.S.QueenConcentrate 1396 1 (GU 1032) |
| The Haboob | Grandfin 6, Sawtooth+ 3, Paddock Cream 5, Omniplegia 7 | Grandfin 4, Paddock Cream 3, Omniplegia 5 |
| Desert Rose | - | Shard 6, Sawtooth+ 2, Blackcurl Stouthorn 1544 2 (no GU), Diablos Tailcase+ 2 |
| Sandgnashers | Grandfin 6, Piel 6, Omniplegia 8, Tailbrand 4 | Grandfin 6, Piel 4, Omniplegia 4, Tailbrand 3 |
| Psammophages | - | Shard 8, Paddock Cream 4, B.Diablos Cortex 4 (no GU), Diablos Hardhorn 1 |
| Sand Fauchard | Piel 3, Grandfin 2, Cephalos Hardfang 3 | - |
| Sand Fauchard+ | - | Shard 3, B.Tigrex Hardfang 1309 3 (no GU; GU Tigrex Hardfang 1388) |
| Iörovellir | - | Sawtooth+ 3, Dire Blastheart 1316 1 (no GU) |
| Quartzlight | Sawtooth+ 6, Omniplegia 6, Tailbrand 5, Lrg Wyvern Gem 1610 1 (GU 441) | Grandfin 3, Shard 3, Omniplegia 4, Sawtooth+ 4 |
| Crystal Lode | - | Piel 6, Paddock Cream 4, D.S.Queen Pectus+ 2 (no GU), Monster Slogbone 1611 5 (GU 417) |

Other lines whose recipes also use a TS material (not TS weapons; GU has none of them, C):

| class | id | name | stats | TS use | tree |
|---|---|---|---|---|---|
| SA | 148 | Vermilion Bloodaxe | 220 raw, Para 400, 2 slots, phial 1, sharp 104/5, rare 8 | upg: Volvidon Cortex 4 (GU 676), Shard 6, Paddock Cream 2, Omniplegia 3 | 55 Vermilingua <- 54 Binding Roller = GU SA 40 |
| HH | 124 | Crabby Castanet | 230, def 40, no element, notes 7, rare 8 | upg: Hermitaur Purpshell 4, Purpclaw 2, Ceanataur Terraclaw 2 (none in GU), Sawtooth+ 3 | 121 Shell Castanet = GU HH 38 -> 125 Klick-Klack |
| HH | 130 | Parahazard Call+ | 240, Para 240, notes 10, rare 8 | upg: Najarala Cortex 4 (GU 956), Ampsounder 5 (GU 954), Heart-stopping Beak 1 (GU 966), Tailbrand 3 (also a create recipe without TS mats) | 54 Parahazard Call <- 53 Hazardous Call = GU 25 -> 131 Para Calamity |
| HH | 169 | Hunter Master | 240, aff 30, Fire 180 hidden, 3 slots, rare 10 | create: Festival Drum Music 1908 3 (event item, no GU), Piel 7, Beastly Fang 1321 6 (GU 765), Massive Bone 5 | no tree (event weapon, S) |

## 7. Decorations (C)

None: no record of the 4U decoration recipe table (0xf553e0, 229 x 24 B, items from +8) uses 1357..1361 or Omniplegia
Sac. A scan of 0xe80000..0x1010000 for {u16 TS item, u16 1..30} finds only the tables above (carves, breaks, create /
upgrade / IG recipes) and the two exe reward lists of section 4.

## 8. Other 4U items used above -> GU (by English name, C)

| 4U | name | GU | | 4U | name | GU |
|---|---|---|---|---|---|---|
| 769 | First-aid Med | 1716 | | 1604 | Omniplegia Sac | 455 |
| 824 | Large Toad Tear | 2123 | | 1607 | Paddock Cream | 927 |
| 690 | Vile Frenzy Crystal | 2136 | | 1645 | Pure Frenzy Crystal | none (GU: Frenzy Shard 2134, Crystal 2135, Vile 2136) |
| 1613 | Massive Bone | 426 | | 1635 | Eltalite Ore | 330 |
| 216 | Carbalite Ore | 329 | | 276 | Dragonbone Relic | 427 |
| 185 | Hot Pepper | 280 | | 958 | Lazurite Jewel | 342 |
| 228 | Hard Armor Sphere | 349 | | 229 | Heavy Armor Sphere | 350 |
| 37 | Shining Charm | 354 | | 38 | Timeworn Charm | 355 |
| 135 | Stam Nectar: Water | none | | 147 | Power+ Nectar: Fire | none |
| 1618 | Meaty Piel | none (GU Meaty Hide+ 940, rare 6) | | 1619 | Crushing Fang | 437 |
| 1615 | Rhenoplos Bone | none | | 1606 | Fey Wyvern Gem | 439 |
| 1564 | Cephalos Grandfin | 809 | | 1567 | Cephalos Hardfang | 812 |
| 1610 | Lrg Wyvern Gem | 441 | | 1482 | Brach Crown | 1078 |
| 1542 | B.Diablos Cortex | none (Diablos Cortex 1425) | | 1303 | Tigrex Hardfang | 1388 |
| 1398 | D.S.Queen Pectus+ | none (S.Queen Pectus+ 1024) | | 1396 | D.S.QueenConcentrate | 1032 |
| 1540 | Diablos Tailcase+ | 1433 | | 1539 | Diablos Hardhorn | 1430 |
| 1611 | Monster Slogbone | 417 | | 1309 | B.Tigrex Hardfang | none |
| 1316 | Dire Blastheart | none | | 1544 | Blackcurl Stouthorn | none |
| 1765 | Volvidon Cortex | 676 | | 1560 / 1561 | Hermitaur Purpshell / Purpclaw | none |
| 1759 | Ceanataur Terraclaw | none | | 1363 / 1365 / 1364 | Najarala Cortex / Ampsounder / Heart-stopping Beak | 956 / 954 / 966 |
| 1908 | Festival Drum Music | none | | 1321 | Beastly Fang | 765 |
| 1876 | Argosy Ticket | none | | 1558 | Fine Black Pearl | 970 |

## Open questions
1. Quest stat rows: confirm in 4U code that +0x34 = {size, size table, HP, attack, other, ?, ?} (and that +0xE8 are icons);
   this also changes Gogmazios' quests (row 98 came from the icon field, S). Bytes +6 / +7 (04 02) and +0x44..+0x5c rows unknown.
2. 4U break groups g0 / g4 part names and em092's part -> group map (break adder callers 0x9453b0 / 0x949eb0, part table
   0x91df20()+0x78); g1 = Frenzy overcome is S.
3. m10830: frenzied TS (spawn byte +0xF = 1) and "Suppress its Frenzy (2x)": GU equivalent? (port choice: plain spawn +
   another subquest, e.g. a break).
4. Row B list flags 0x8003 (vs 0x8000): meaning, and how quest4u.rem_4u should take it.
5. 4U +0xB0 (3000 / 3300) = HRP? +0xB8 = 30? +0xA0 bytes, +0xC5 = 0x20.
6. Capture rewards: no per-monster capture table looked for (4U or GU); check how GU builds them for em067 before the quests.
7. Bow element / coatings / arc shot of Quartzlight / Crystal Lode not decoded (only raw, slots, charges); Kiranico for these.
8. IG tree (72 -> 73 -> 74) and Sand Fauchard's parent: not in the IG upgrade table; Kiranico.
9. Kiranico's TS weapon list lacks the Lance line Carnelian Lance / Crystalis that 4U's tables tie to TS (create + both
   upgrades use TS mats): port it or not (user).
10. FreeElemnt (Awaken) +5 on the Z set has no GU tree (no skill at +5 anyway); Meaty Piel (head, arms) has no GU item:
    substitute needed (e.g. GU Meaty Hide+ 940 is rarity 6).
11. Crown sizes (Kiranico page, S): mini < 1474.0, large > 1777.9, king > 1869.1; 4U size table byte 0x1c = 28 not mapped to GU.
