# Gogmazios weapons: GU table spec and 4U data (weapons helper, 2026-10-20, research only)

Evidence tags: C = confirmed in data or code, G = guess. "C(k)" = taken from kiranico's 4U page data
(embedded JSON), cross-checked against the 4U exe where a matching field exists.
Sources:
- GU 1.4 main: XFS property registrations give names, types and in-memory offsets; per-record parse functions give the file -> memory mapping.
- GU base RomFS tables.
- 4U v1.1 exe (dump/exefs_v11/mem.bin).
- kiranico 4U weapon pages (scratchpad/web_w, 27 pages).

Scripts are in scratchpad/weapons/:
- layout.py CLASS: property registrations plus the parse map, i.e. the file layout.
- gl.py: GU tables decoded with those layouts.
- m4u.py: 4U records.
- kira.py: kiranico JSON.

## 0. GU class numbering (C)

NN = box type - 7:

| NN | 00 | 01 | 02 | 03 | 04 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| class | GS | SnS | Hammer | Lance | HBG | LBG | LS | SA | GL | Bow | DB | HH | IG | CB |
| model prefix | two | one+sld | ham | lan+sld | hbg | lbg | swoNNN/ken | axe | gun+sld | bow+ya | sou_l/_r | hue | rod | gaxe: blade+sld |

## 1. weaponNNBaseData (loc/arc/resident.arc, f32 2.10, u32 n, packed records)

Classes, loaders and record sizes (C):
- rWeaponNNBaseData: load 0x12f5bc (00) ... 0x13b0c8 (14).
- The in-memory record is 40 B; +0 is the vtable.
- File stride: 33 B (00 01 02 03 07 10 12), 34 B (08 09 11 13 14), 32 B (04 06).

Base layout (33 B, e.g. 00; file -> mem):

| file | type | mem | property | meaning / proposed use |
|---|---|---|---|---|
| +0 | u32 | +4 | mIndex | weapon ID = record index = box ID (C: all 14 classes) |
| +4 | u16 | +8 | mModelID | model: arc/weapon/wNN/%03d.arc and the pwl entry (C) |
| +6 | u16 | +10 | mSrqrNo | sound set: always names an existing arc/weapon/wNN/snd/%03d.arc; usually = model (C), meaning G |
| +8 | u8 | +12 | mSndMaterial | 0/1 (snd/mat_b vs mat_i, bone/iron, G) |
| +9 | u8 | +13 | mMaxLv | levels before the G-rank limit break (C: mMaxLv + mMaxLvForLimit = LevelData rows, every weapon) |
| +10 | u8 | +14 | mMaxLvForLimit | extra levels after the limit break (C) |
| +11 | u8 | +15 | mRare | 0-based; 10 = deviant weapons, shown as RARE X (C data, display G) |
| +12 | u32 | +16 | mPrice | the only zenny field of the weapon tables (C); forge cost, upgrade costs derived (G) |
| +16 | u8 | +20 | mPriceChangeLv | 0/2..6, meaning G |
| +17 | u8 | +21 | mElement | 0 none, 1 fire, 2 water, 3 thunder, 4 dragon, 5 ice, 6 poison, 7 para, 8 sleep, 9 blast (C by names: Scylla Blade 8, Dios Blade 9) |
| +18 | u8 | +22 | mColorIndex | 0, except 3 weapons at 101/102/109 |
| +19 | u16 | +24 | mSortID | list order (max: GS 215, SnS 215, Ham 201, Lan 185, HBG 108, LBG 109, LS 194, SA 165, GL 184, Bow 107, DB 204, HH 174, IG 148, CB 129) |
| +21 | bool | +26 | mNamed | 17 GS = 1; use 0 |
| +22 | u8 | +27 | mSpecialSkill | 0, except 1-3 special weapons; use 0 |
| +23..+32 | 5x(u8,u8) | Lv +28..+32, ID +33..+37 | mDeriveLv[k], mDeriveID[k] | upgrade tree: child ID (u8) and level needed (C) |

Class variants (C):
- 34-B classes have an extra u8 at file +18 -> mem +22:
  - 08 SA mBinType; 14 CB mBinType;
  - 09 GL mShootType;
  - 11 DB mElement2 (file +17 = mElement1);
  - 13 IG mInsectType.
  - After it: mColorIndex f+19 -> m+23, mSortID f+20 -> m+24, mNamed f+22 -> m+26, mSpecialSkill f+23 -> m+27, derive pairs f+24..+33 (same memory offsets).
- Bowguns 04/06 (32 B) have no mElement: mColorIndex f+17 -> m+21, mSortID f+18 -> m+22, mNamed f+20 -> m+24, mSpecialSkill f+21 -> m+25, mDeriveLv m+26..+30, mDeriveID m+31..+35.
- No raw, affinity, slots or sharpness here: they are per level (section 2).

Class enums:
- SA mBinType (C: data; names G): 0 Power, 1 Element; types 2..5 carry a LevelData mBinElementValue (Dragon / Poison / Para / Exhaust, order G).
- CB mBinType (C data, G names): 0 Impact (Petrified / Dios Strongarm), 1 Element (Serrated Glace).
- GL mShootType (G, from UI string order 279..281): 0 Normal, 1 Long, 2 Wide.
- IG mInsectType = starting kinsect, an insectData index (C: insectData_eng 1 Culldrone, 12 Mauldrone; 23..25 special).

Counts and new IDs (C): count n, max ID n-1; new IDs from n up to 255 (mDeriveID is u8).

| NN | 00 | 01 | 02 | 03 | 04 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n | 137 | 129 | 132 | 127 | 109 | 110 | 127 | 110 | 115 | 108 | 126 | 112 | 83 | 81 |
| new IDs | 137,138 | 129,130 | 132,133 | 127,128 | 109 | 110 | 127,128 | 110,111 | 115,116 | 108,109 | 126,127 | 112,113 | 83,84(,85) | 81,82 |

## 2. weaponNNLevelData (resident.arc, f32 1.20; one row per weapon level)

Row rules (C):
- Rows are sorted by weapon (mNo non-decreasing) and mIndex = row number.
- A weapon's rows are those with mNo = ID; levels run 1..mMaxLv+mMaxLvForLimit.
- Append new rows at the end with mIndex continuing.

Melee layout (00 01 02 03 07 13: 15 B file -> 20 B mem):

| file | type | mem | property | note |
|---|---|---|---|---|
| +0 | u32 | +4 | mIndex | row number |
| +4 | u8 | +8 | mNo | weapon ID |
| +5 | u8 | +9 | mLevel | 1.. |
| +6 | u8 | +10 | mKireType | kireajiData index (section 6) |
| +7 | u8 | +11 | mKireLevel | bar length step, even values 0..12 (section 6) |
| +8 | u16 | +12 | mAttack | true raw, displayed as is (C: GS raw 50..390; no class bloat in GU) |
| +10 | u8 | +14 | mDefense | |
| +11 | u8 | +15 | mAffinity | two's complement (236 = -20) |
| +12 | u16 | +16 | mElementValue | element/10, the same unit as 4U (Red Wing 22..44) |
| +14 | u8 | +18 | mSlotCount | |

Extras (C), file -> mem:
- 08 SA and 14 CB (17 B, mem 24 B): +14 u16 mBinElementValue -> m+18, +16 mSlotCount -> m+20.
- 09 GL (16 B): +14 u8 mShootLevel -> m+18 (0..4 = Lv1..5, G), +15 slots -> m+19.
- 12 HH (16 B): +14 u8 mFueMusicType -> m+18 (the note set, per level), +15 slots -> m+19.
- 11 DB (17 B): +12 mElementValue1 -> m+16, +14 mElementValue2 -> m+18, +16 slots -> m+20.
- 10 Bow (31 B, mem 36 B), no sharpness:
  - +6 attack -> m+10, +8 defense -> m+12, +9 affinity -> m+13, +10 u16 element -> m+14, +12 slots -> m+16.
  - +13 mKyoku -> m+17, +14 mTameDankai -> m+18.
  - +15..+18 mCShotKind[4] -> m+19..22.
  - +19..+30 mLoadEnableBottle[12] -> m+23..34.
- 04 HBG / 06 LBG (100 B, mem 104 B), no sharpness and no element:
  - +6 attack -> m+10, +8 defense -> m+12, +9 affinity -> m+13, +10 slots -> m+14.
  - +11 mBure -> m+15, +12 mReloadSpeed -> m+16, +13 mRecoil -> m+17.
  - +14..18 mDownShot[5] (HBG) / mQuickShot[5] (LBG) -> m+18..22.
  - +19.. five triples (mUniqueShell, mUniqueHaveShellCount, mUniqueShellCount) -> m+23+k / +28+k / +33+k.
  - +34.. 33 pairs (mLoadShellCount[k], mLoadEnableShell[k]) -> m+38+k / m+71+k.

Bow enums (G, from StartMenuMsg string order):
- mKyoku: 0 Focus, 1 Wide, 2 Blast.
- mCShotKind (values 1..20): 1-5 Rapid Lv1-5, 6-10 Spread, 11-15 Pierce, 16-20 Heavy. First charges peak at 2/7/12.
- mTameDankai: 2/3/4, 3 on 656 of 736 rows.
- mLoadEnableBottle (0/1, 2 = boosted?) follows the coating items 208..218:
  - [0] Power Lv1, [1] Power Lv2, [2] Elem Lv1, [3] Elem Lv2, [4] C.Range, [5] Poison, [6] Para, [7] Sleep, [8] Exhaust, [9] Blast, [10] Paint;
  - [10] and [11] are 1 on every row.

Bowgun enums (G):
- The 33 ammo slots follow the ammo item order 100..131: 0-2 Normal 1-3, 3-5 Pierce, 6-8 Pellet, 9-11 Crag, 12-14 Clust, 15 Flaming, 16 Water, 17 Thunder, 18 Freeze, 19 Dragon, 20-21 Poison 1-2, 22-23 Para, 24-25 Sleep, 26-27 Exhaust, 28-29 Recover, 30 Paint, 31 Tranq, 32 unknown (max 3). The maximum count per slot fits this order (Dragon max 3, Paint and Tranq max 2).
- mLoadEnableShell is 0/1. Count > 0 with enable 0 occurs (~4200 times per class): the ammo is listed but not loadable.
- mUniqueShell values 33..74 are the special ammo (Slicing, Wyvern, ...); the ID map is not resolved.
- mRecoil 5..8 (mode 7), mReloadSpeed 3..7 (mode 5) and mBure 0..6 (0 on ~75 % of rows) are internal values. The UI has 8 recoil, 8 reload and 6+1 deviation strings; the map is not resolved.

## 3. pl_wNN (weapon\wNN\pwl\pl_wNN in resident.arc): rPlayerWeaponList

Layout (C):
- f32 2.0, u32 n, 16-B records -> 20-B mem.
- Fields: +0 u32 mGmkMotNo, +4 u32 mDispType, +8 u32 mCarryType, +12 u8 mSubParam[4].
- Indexed by **model ID**: n = highest mModelID + 1 in all 14 classes (C).
- GL varies in mSubParam. mGmkMotNo probably picks arc/weapon/wNN/gNN.arc (motion arcs wgNN_00), G.

Highest model (= pwl n - 1), C:

| GS | SnS | Ham | Lan | HBG | LBG | LS | SA | GL | Bow | DB | HH | IG | CB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 199 | 196 | 192 | 180 | 146 | 150 | 186 | 161 | 173 | 163 | 181 | 157 | 117 | 110 |

Model files (C):
- arc/weapon/wNN/%03d.arc (model number) holds weapon\wNN\<pfx>NNN\<pfx>NNN (mod) plus _BM textures; shields and arrows are separate files in the same arc.
- arc/weapon/wNN/snd/%03d.arc (by mSrqrNo) holds sound\se\pl\wp\<pfx>\NNN.
- Numbers have gaps (GS: 134 arcs for 1..199).
- A new model number needs a new arc, a snd arc (or reuse via mSrqrNo) and a pwl record appended at index = model (copy a similar model's pwl record).
- A stand-in needs nothing new: set mModelID / mSrqrNo to the stand-in's values.

## 4. weaponCreateWNN / weaponProcessWNN (arc/facility/blacksmith.arc, f32 1.00)

rWeaponCreateData: load 0x4ca0c4, parse 0x4be4c4. 38 B -> 44 B mem (C):

| file | type | mem | property | note |
|---|---|---|---|---|
| +0 | u16 | +4 | mLv | level the forged weapon starts at (1; 2..6 on a few) |
| +2 | u16 | +6 | mNo | weapon ID |
| +4 | u16 | +8 | mDispFlag | 0 normally; other values on ~10 records (unlock condition, G) |
| +6 / +10 / +14 / +18 | u16 | +10/12/14/16 | mItem[0..3] | |
| +8 / +12 / +16 / +20 | u8 | +18..21 | mNum[0..3] | |
| +9 / +13 / +17 / +21 | u8 | +22..25 | mKey[0..3] | 2 on the 1st material of 85/95 GS recipes, 1 on 3, else 0 (key item that reveals the recipe, G) |
| +22 | u16 | +26 | mCategory | provision group |
| +24 | u16 | +28 | mRank | provision value (u16; the editor's "u8 value" is the low byte) |
| +26/+30/+34 | u16 | +30/32/34 | mPiece[0..2] | scraps given back |
| +28/+32/+36 | u16 | +36/38/40 | mPieceNum[0..2] | |

rWeaponProcessData: load 0x4ca540, parse 0x4bf6cc. 32 B -> 36 B mem (C):
- +0 mNo -> m+4, +2 mLv -> m+6.
- Four packed (u16 mItem, u8 mNum) at +4/+7/+10/+13 -> items m+8..14, counts m+16..19.
- +16 mCategory -> m+20, +18 mRank -> m+22.
- mPiece +20/+24/+28 -> m+24/26/28; mPieceNum +22/+26/+30 -> m+30/32/34.

Which records a weapon needs (C, checked on GS 1/3/8/11/12/95/136):
- **One process record per level 1..max**, forgeable or not.
- Level 1 holds the upgrade-from-parent materials. A weapon without a parent still has an all-zero level-1 record.
- A forgeable weapon also has one create record.
- No zenny field in either table: zenny = BaseData mPrice (G).

## 5. Names (eng\table\weaponNNMsgData_eng.gmd in eng/arc/resident_eng.arc, every language)

- **6 strings per weapon**: GMD entries 6*ID .. 6*ID+5 = [name A, desc A, name B, desc B, name C, desc C] (C: entry count = 6n in all 14 classes). The old helper's wgu.py used 3*k, which is wrong.
- Name A covers Lv1..mMaxLv; B the limit-broken levels; C the final level (Iron Sword / Carbalite Sword / Eltalite Sword, Petrified / Scholarly / Sophos Blade), G.
- For our 1-level weapons, write the 4U name into A, B and C.
- Index file eng\table\weaponNNMsgData (no _eng), rWeaponNNMsgData:
  - Layout: f32 2.0, u32 n, n x u32 mIndex (8-B mem record).
  - Today it is the identity 0..n-1 and n = BaseData n in all classes (C).
  - Append mIndex = new ID in every language arc (G: that it is needed).
- 4U descriptions (*Exp_eng.lmd) have 113 entries for 246 GS; the index map is not resolved, so write new descriptions.

## 6. Sharpness

GU (C):
- table\kireajiData (resident.arc, f32 1.2, rKireajiData) has 164 entries of 7 cumulative u16 (mSlash[0..6]: red..purple end points; last = 450). Memory record 20 B: +4..+16.
- Bar length (fn 0xf4760) = 150 + 25*(mKireLevel + x), and 450 when the sum exceeds 12. Here x is the caller's argument, the Handicraft bonus (G).
- Data: mKireLevel is even 0..12; 12 on 407 rows means a full 450 bar.
- Slash getter 0xf4724 = kireaji[vt+0x20()].mSlash[colour].

4U (C):
- The melee record's u16 at +2 is two bytes: **+2 = sharpness index, +3 = kire level**.
- Table 0xf581e4: 119 x 7 cumulative u16, the same units as GU (end 400 or 450).
- Base bar = 150 + 50*(+3), and Handicraft +1 adds 50 (cap 450). Checked against kiranico on 4 weapons:
  - Iron Sword: 23/1 -> 200, +1 250.
  - Lacerator Blade: 3/3 -> 300, +1 350.
  - Accursed Blade: 35/3 -> 300, +1 350.
  - Red Wing: 42/3 -> 300.
- So **GU mKireLevel = 2 x 4U level**.
- Gogma level 6 = full 450: Handicraft does nothing (kiranico: the +1 bar equals the base bar).

| 4U idx | used by | cumulative (red..purple) | kiranico widths (x5) | closest GU entry |
|---|---|---|---|---|
| 88 | every create melee + Luminary's Mark | 80,130,180,340,380,450,450 | 16,10,10,32,8,14,0 | 18 (80,150,190,330,380,450) |
| 100 | every upgrade melee + Limbo Lacrimosa | 120,240,260,280,370,440,450 | 24,24,4,4,18,14,2 | 26 (110,210,260,320,370,450) |
| 89 | Messenger's Mark | 100,150,280,350,390,450,450 | 20,10,26,14,8,12,0 | 80 (110,150,250,340,390,450) |

Proposal:
- Append these three as GU kireaji 164/165/166 (needs the in-memory rKireajiData array grown by 3).
- Use mKireLevel 12, faithful to 4U.
- Fallback without growing kireaji: the closest entries above.

## 7. 4U records (v1.1 exe, pointer table 0xf58868)

Melee 24-B record (C):

| off | type | meaning |
|---|---|---|
| +0 | u16 | model: two097 etc., matches kiranico weaponmodels |
| +2 | u8 | sharpness index |
| +3 | u8 | kire level |
| +4 | u32 | price: create cost = 1.5x (80000 -> 120000 z, kiranico), upgrade cost = 1x (130000) |
| +8 | u16 | true raw (display = raw x class modifier, GS 280 x 4.8 = 1344) |
| +10 | u8 | defense |
| +11 | s8 | affinity |
| +12, +13 | u8, s8 | element type (1 fire, 2 water, 3 thunder, 4 dragon, 5 ice), value/10 |
| +14, +15 | u8, s8 | status type (1 poison, 2 para, 3 sleep, 4 blast), value/10 |
| +16 | u8 | slots |
| +17 | u8 | class extra (below) |
| +18 | u8 | ? |
| +19 | u8 | rarity - 1 |
| +20 | u16 | sort |
| +22 | u8 | flags: 0x01 create, 0x21 upgrade-only (G) |
| +23 | u8 | ? |

Values:
- Value bytes are signed: **negative = hidden, needs Awaken**, magnitude x10 (C: Lacerator 0xE7 = hidden Fire 250, Accursed 0xE7 = hidden Blast 250, IG 0xF8 = hidden Sleep 80; all match kiranico awaken_required).
- Class extra +17:
  - GL: (level-1)*3 + type; Normal Lv5 = 12 (C value, formula G).
  - HH: note set 3 = purple/red/blue (C(k)).
  - SA 0 = Power, CB 0 = Impact, IG 0 = Cutting (C(k)).
- Bows and bowguns are 40 B:
  - model +0, rarity-1 +4, price +8, raw +12 (display x1.2 bow, x1.3 LBG, x1.5 HBG), slots +16, affinity +17.
  - Bow charges at +22: 08 03 08 03 = Spread4 Rapid4 Spread4 Rapid4, upgrade 08 03 09 04 (4U enum Rapid n = n-1, Spread n = n+4, G).
  - The rest is not decoded; kiranico values are used below.

Gogma weapons (C exe; status, sharpness and extras also C(k)). Status is Sleep everywhere, visible except IG. Defense 0, rarity 10, models as listed.

| Class | 4U id | Name | Raw | Aff | Sleep | Slots | Sharp | Price | Extra / 4U model |
|---|---|---|---|---|---|---|---|---|---|
| GS | 222 | Monument of Lament | 280 | -10 | 130 | 1 | 88/6 | 80000 | two097 |
| GS | 223 | Ostracon Oblivion | 300 | -20 | 180 | 1 | 100/6 | 130000 | |
| SnS | 227 | Valorous Soldier | 290 | -10 | 70 | 0 | 88 | 80000 | one097 + ones097 |
| SnS | 228 | Kyrie Ruin | 310 | -10 | 140 | 0 | 100 | 130000 | |
| Hammer | 221 | Empty Cage | 270 | -10 | 140 | 1 | 88 | 80000 | ham099 |
| Hammer | 222 | Desmos Admonition | 290 | -15 | 210 | 1 | 100 | 130000 | |
| Lance | 198 | Fettering Rebuke | 280 | -10 | 100 | 1 | 88 | 80000 | lan082 + lan082s |
| Lance | 199 | Aether Geghard | 300 | -10 | 180 | 1 | 100 | 130000 | |
| LS | 199 | Grim Genuflector | 270 | -10 | 90 | 0 | 88 | 80000 | ken079 |
| LS | 200 | Headsman's Requite | 290 | -15 | 160 | 0 | 100 | 130000 | |
| SA | 180 | Punishable Sin | 260 | -15 | 110 | 0 | 88 | 80000 | Power phial; axe077 |
| SA | 181 | Wicked Conqueror | 280 | -15 | 190 | 1 | 100 | 130000 | Power |
| GL | 201 | Towering Demise | 280 | -10 | 120 | 0 | 88 | 80000 | Normal Lv5; gun082 + s |
| GL | 202 | Auguring Prophet | 300 | -10 | 240 | 0 | 100 | 130000 | Normal Lv5 |
| DB | 208 | Recriminators | 290 | -10 | 70 | 0 | 88 | 80000 | sou087l/r |
| DB | 209 | Eternal Leavetakers | 310 | -10 | 100 | 0 | 100 | 130000 | |
| HH | 164 | Clemency's Peal | 270 | -10 | 110 | 0 | 88 | 80000 | notes purple/red/blue; hue071 |
| HH | 165 | Onyx Terpsichore | 290 | -15 | 150 | 0 | 100 | 130000 | same notes |
| IG | 130 | Messenger's Mark | 270 | -10 | (80) hidden | 1 | 89 | 60000 | Cutting, kinsect Lv1-6; rod025 |
| IG | 131 | Luminary's Mark | 280 | -10 | (100) hidden | 1 | 88 | 120000 | kinsect Lv7-10 |
| IG | 132 | Limbo Lacrimosa | 290 | -10 | (110) hidden | 1 | 100 | 130000 | 2nd upgrade, kinsect Lv11-12 |
| CB | 98 | Forbidden Coffin | 270 | -10 | 80 | 0 | 88 | 80000 | Impact phial; blade027 + sld027 |
| CB | 99 | Promised Nadir | 290 | -10 | 110 | 0 | 100 | 130000 | Impact |
| LBG | 165 | Bethorned Dystopia | 300 | -10 | - | 1 | - | 80000 | lbg047 |
| HBG | 141 | Trembling Lordship | 310 | -15 | - | 1 | - | 80000 | hbg040 |
| Bow | 183 | Unwelcoming Gaol | 280 | -10 | - | 1 | - | 80000 | arc Blast; Spread4 / Rapid4 / Spread4 / Rapid4; bow075 |
| Bow | 184 | Calamitous Cupid | 300 | -15 | - | 1 | - | 130000 | Spread4 / Rapid4 / Spread5 / Rapid5 |

Cross-check with content-plan Appendix:
- Raw, affinity, status value and slots all match.
- New: the status is Sleep and visible, except the IG (hidden).
- The IG line has a third weapon. Luminary's Mark upgrade recipe (kiranico) = Gasher 2, Offenders 2. Limbo Lacrimosa = Briartail 2, Wartorn Dragonsphire 1.

Other kiranico values:
- Bow coatings (both bows), C(k): Power, Sleep, Paint, Blast.
- Bowguns, C(k): recoil Average, reload Average, deviation none (both). Ammo (n = clip, (n) = kiranico parentheses, meaning G: listed but not loadable without a skill):

| Ammo | LBG Bethorned | HBG Trembling |
|---|---|---|
| Normal 1/2/3 | 6/(10)/(10) | 4/(10)/(10) |
| Pierce 1/2/3 | (4)/6/8 | 4/8/6 |
| Pellet 1/2/3 | 6/8/8 | (4)/7/7 |
| Crag 1/2/3 | (2)/2/2 | (3)/(3)/3 |
| Clust 1/2/3 | (2)/(2)/2 | (2)/2/2 |
| Para 1 / Sleep 1,2 / Exhaust 1,2 | 2 / 3,3 / 3,3 | 2 / 3,3 / 3,3 |
| Recover 1,2 / Paint / Tranq | 2,2 / 2 / 2 | 2,2 / 2 / 2 |
| Special | Slicing 3, Slime 3, Demon 1 | Slicing 3, Slime 3, Armor 1, Wyvern (1) |
| Rapid / crouch fire | Pierce2 x3, Pellet1 x3, Sleep1 x2 | crouch: Pierce3 20, Pellet3 20, Sleep2 4 |

Recipes: content-plan Appendix (C), plus the IG fix above.

## 8. Proposed GU records (G: concrete values)

Common to all 28 entries:
- mMaxLv 1, mMaxLvForLimit 0, a single LevelData row (mLevel 1).
  - The only (1,0) record in GU today is the dummy record 0, so a 1-level real weapon is untested (G).
  - Fallback: 1+1 with a duplicated row.
- mRare 9 (shown as RARE 10; 10 = X is the deviant tier).
- mPrice = 4U price (80000 / 130000; IG 60000 / 120000 / 130000), mPriceChangeLv 0.
- mSndMaterial 1, mColorIndex 0, mNamed 0, mSpecialSkill 0.
- mSrqrNo = mModelID (2026-10-20): the 4U sounds converted by tools/wsnd4u2gu.py into wNN/snd/<model>.arc.
- mSortID: class max + 1 / + 2.
- mElement 8 (DB: mElement1 8, mElement2 0). mElementValue = 4U value/10 (13, 18, ...); mDefense 0.
- mAffinity = byte (-10 = 246, -15 = 241, -20 = 236).
- mSlotCount as in 4U. mKireLevel 12. mKireType 164 (idx 88), 165 (idx 100), 166 (Messenger's).
- Create weapon:
  - mDeriveLv[0] 1, mDeriveID[0] = upgrade ID.
  - A create record: mLv 1, mNo, mDispFlag 0, the 4U materials, mKey[0] 2, no provision, no scraps.
  - An all-zero process record for level 1.
- Upgrade weapon:
  - No create record.
  - A process record for level 1 with the 4U upgrade materials (Wartorn Dragonsphire 1 + listed).
- Names: A = B = C = the 4U name. MsgData index appended.
- **IG hidden sleep:** GU has no Awaken. Options: (a) visible Sleep 8/10/11 (proposed), (b) mElement 0.

Per class (new ID: create / upgrade; stand-in = existing GU weapon whose mModelID/mSrqrNo to copy):

| NN | IDs | Raw | Aff | mElemVal | Slots | Extras | Stand-in (ID: model) |
|---|---|---|---|---|---|---|---|
| 00 GS | 137 / 138 | 280 / 300 | 246 / 236 | 13 / 18 | 1 / 1 | - | Akantor Broadsword (71: 37) |
| 01 SnS | 129 / 130 | 290 / 310 | 246 / 246 | 7 / 14 | 0 / 0 | - | Akantor Duo (63: 155) |
| 02 Ham | 132 / 133 | 270 / 290 | 246 / 241 | 14 / 21 | 1 / 1 | - | Demonlord Hammer (18: 104) |
| 03 Lance | 127 / 128 | 280 / 300 | 246 / 246 | 10 / 18 | 1 / 1 | - | Demonlord Spear (48: 87) |
| 07 LS | 127 / 128 | 270 / 290 | 246 / 241 | 9 / 16 | 0 / 0 | - | Akantor Katana (68: 32) |
| 08 SA | 110 / 111 | 260 / 280 | 241 / 241 | 11 / 19 | 0 / 1 | mBinType 0 (Power), mBinElementValue 0 | Akantor Switch Axe (56: 19) |
| 09 GL | 115 / 116 | 280 / 300 | 246 / 246 | 12 / 24 | 0 / 0 | mShootType 0 (Normal), mShootLevel 4 (Lv5) | Akantor Gunlance (60: 9) |
| 11 DB | 126 / 127 | 290 / 310 | 246 / 246 | V1 7 / 10, V2 0 | 0 / 0 | mElement1 8, mElement2 0 | Akantor Blades (63: 36) |
| 12 HH | 112 / 113 | 270 / 290 | 246 / 241 | 11 / 15 | 0 / 0 | mFueMusicType 2 = fueMusicData (2,3,4) purple/red/blue (G: colour enum 1 white, 2 purple, 3 red, 4 blue; first note is always 1/2) | Akantor Horn (60: 3) |
| 13 IG | 83 / 84 (/85) | 270 / 280 (/290) | 246 | 8 / 10 (/11) | 1 | mInsectType 1 (Culldrone, cutting) | Demonlord Cudgel (43: 31) |
| 14 CB | 81 / 82 | 270 / 290 | 246 / 246 | 8 / 11 | 0 / 0 | mBinType 0 (Impact) | Akantor C. Blade (41: 19) |

Gunners (no sharpness, no element, mKire* absent):

| NN | ID | Raw | Aff | Slots | Extras | Stand-in |
|---|---|---|---|---|---|---|
| 06 LBG | 110 | 300 | 246 | 1 | ammo per the table and slot map in section 2: plain n -> enable 1, count n; (n) -> enable 0, count n (G); specials and rapid fire copied from a GU LBG with Slicing/Blast (IDs unresolved); mRecoil 7, mReloadSpeed 5, mBure 0 (GU modes, G = "Average/none") | Demonlord Blaster (58: 53) |
| 04 HBG | 109 | 310 | 241 | 1 | the same rules; crouch fire Pierce3 / Pellet3 | Akantor Cannon (55: 17) |
| 10 Bow | 108 / 109 | 280 / 300 | 246 / 241 | 1 / 1 | mKyoku 2 (Blast); mTameDankai 3 (4U 4th charge needs Load Up, G); mCShotKind (9,4,9,4) / (9,4,10,5); bottles [0]=[1]=1 Power, [7] Sleep 1, [9] Blast 1, [10]=[11]=1, rest 0 ([4] C.Range = 1 if following the GU norm) | Akantor Bow (56: 3) |

Checklist of appends per class (in memory):
- BaseData +1/2 (n + mIndex);
- LevelData +1/2 rows (mIndex continues);
- MsgData index +1/2;
- GMD +6 strings each;
- Create +1;
- Process +1/2 (the create weapon's zero row and the upgrade row);
- kireajiData +3, once;
- pwl only when real 4U models get new numbers.

## 9. Generator (tools/gear_weapons_em089.py, 2026-10-20)

Outputs:
- `module/gear_weapons_em089.inc`: 71 tables (14 x Base / Level / MsgData index / Create / Process, plus kireajiData) and the 14 name blocks (6 strings per weapon, 5 languages).
- `module/gear_hooks.txt`: 45 load-exit hooks (14 x 3 classes, plus rWeaponCreateData, rWeaponProcessData, rKireajiData).
- `gear_weapons_em089.py show` prints the per-weapon summary, the tables and the hooks, and writes nothing.

Built from (C):
- Records: each one is a copy of the stand-in's record, then the fields are set. LevelData copies the stand-in's final level row.
- Hammer / Lance / IG stand-ins have no create recipe. They lend the table's first plain recipe instead (weapons 38 / 31 / 30), which is fully overwritten.
- 4U stats, prices, sharpness entries and recipes are read from the v1.1 exe:
  - upgrade recipes: pointer table 0xf56974, index = create type - 7, 24 B per ID;
  - IG upgrades: 0xf569a8, 12 B per ID: u16 ID, u16 kinsect level, 2 pairs.
- The recipes are checked against content-plan's Appendix. Items are mapped by English name to GU itemData_eng: LED Gem 1553, LED Bone 419, Gravios Pallium 1170, our materials 2977..2984.
- Class functions and hook sites come from each class's generated loader, which is checked by the script:
  - exit site `mov r0, r8; add sp, sp, #24`;
  - count in res+0x64, array in res+0x6c;
  - the version literal equals the file's f32.

Kept from the stand-in's last row for the bowguns, because those maps are unresolved (G):
- HBG (Akantor Cannon): recoil 7, reload 4, mBure 1, crouch fire (2,5,12,3,0), special ammo, slot 32.
- LBG (Demonlord Blaster): recoil 7, reload 5, **mBure 6**, rapid fire (16,28), special ammo, slot 32.
- 4U has deviation "none" on both, so the LBG's mBure 6 is probably a visible drift.

MsgData index parse (C):
- 0xf7c40 reads its single u32 through reader vt+0xc = 0x8263f8, the same u32 read the loader uses.
- So the record is 4 B.
