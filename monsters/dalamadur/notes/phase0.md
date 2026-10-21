# Dalamadur / Shah Dalamadur: Phase 0 (identify), 2026-10-21

C = confirmed in code / data, S = strong, G = guess. 4U = MH4U v1.1 (EUR) code.bin addresses, GU = MHGU 1.4 main
offsets. Scripts: dump/scratch/dalamadur-session/ (factory.py, qscan.py, qboss.py, qrew.py, shahdiff.py, emd.py,
gear_scan.py, armor_skills.py, shells2.py, acts2.py).

## Monsters and classes
| 4U em | name | class | arc | |
|---|---|---|---|---|
| 24 | Dalamadur (main, head + front body) | uEm024 (DTI 0x10b6780, vt 0xe66c20, vt44 0x772fcc, ctor 0x776124) | em024.arc (model, motions, effects, sounds, em024_cmd AND em083_cmd) | C |
| 83 | Dalamadur tail half | uEm083 (DTI 0x10b7b78, vt 0xe69fac, vt44 0x8a1e6c, ctor 0x8a30c8) | em083.arc (same em024 model / motions / sounds, own em083_cmd, no effects) | C |
| 110 | Shah Dalamadur | uEm024 | em110.arc (own model, motions, effects, sounds, em110_cmd) | C |
| 111 | Shah tail half | uEm083 | em111.arc | C |
- 4U factory 0x690228, switch 0x6902a4 on the em number (table 0x6902ac): cases 24 / 110 -> 0x690828 (uEm024 ctor),
  83 / 111 -> 0x691118 (uEm083 ctor). Shah has no class of its own (no uEm110 / uEm111 DTI). C
- The tail is a separate enemy: per frame (vt40 0x8a0050) it looks up its partner through 0x68fd44(mgr, em) with
  em = 24 (or 110 when its own em is 111). C. Hurt volumes (emd word 8): em024 bones 2..16 + 101..107, em083 bones
  140..157. C. Visibility rows (emd +0x88): em024 groups 2..15, 23, 24, 101..105; em083 groups 16..22, 25, 106, 108;
  em110 adds 30..45. C. Each half draws its own part of the shared model. S
- Action tables (disp4u, two levels; deeper sub-dispatchers still to resolve): uEm024 cat 1: 50 numbers, cat 7: 45;
  uEm083 cat 1: 11, cat 7: 26. C (counts), handlers to resolve in Phase 1.
- Shells (direct calls to the per-type post wrappers of factory 0x660e88): uEm024 types 1, 12, 15, 16 (x2), 29;
  uEm083 type 3. S (indirect posts not searched). Type 16 = the beam already ported for Gogmazios.
- Shah branches (C): uEm024 `ldrb W+0x1c0; cmp #110` at 0x76d54c (cat-2 dispatcher 0x76c7b4), 0x76d8ac (vt39 spawn
  0x76d5a0), 0x76de9c (vt40 0x76da88), 0x770e7c / 0x7713b0 / 0x771960 (handlers 0x770954 / 0x770ec0 / 0x7713ec,
  each then calls 0x7753f4 with r1 = 0); uEm083 `cmp #83` at 0x89ff5c, 0x8a0068, 0x8a0420, 0x8a2008, 0x8a27e8,
  0x8a28a8, 0x8a29f8, 0x8a2abc, 0x8a2e9c.
- Shah data (C): em110_cmd == em024_cmd byte for byte; etd 59 bytes differ (same size); emd +448 B; em111 emd ==
  em083 emd, etd 6 bytes differ; 2 extra waves (se_fire_atk, se_fire_pre_atk); 9 extra effects em110_200..210;
  2 extra textures (_06, _09).

## Walking on the body (user: on some parts, mainly head and back, at certain points, only when allowed)
- 4U: emd header word 10 (+0x28) is set only for em024, em083, em110, em111 and em046 (Dah'ren Mohran). C. It points
  to a pointer list (em024: 0x1578 empty, 0x1584, 0x1728; em083: 0xadc, 0xae8) of polygon lists
  {u32 bone, u32 vertex count (4 or 6), u32 -> vertices (12 B each)} closed by 0xffffffff. Word 12 = 2, word 13 ->
  a further block (enable rules? G). = bone-attached ground polygons. S
- 0x937150 (C): W+0x420 = [species row 0x91df20] +0x28 (this polygon block). Readers to trace (enemy common code,
  W+0x420 loads): 0x9402a4, 0x9406e0, 0x942d78 (4 reads each, polygon-loop shape), 0x939c40, 0x920104, 0x946698,
  0x948b9c, 0x94a66c. Other +0x420 hits in the exe are unrelated objects.

## Action tables (C, scratch acttab.py: recursive disp4u on 1cb)
- uEm024: 95 actions on 19 handlers: 1.0-2 0x76df28; 1.3-11 0x76e050; 1.50-55, 1.60-91 (38) 0x76e754; 7.0/2/3/4
  0x76ec80; 7.1 0x76efc8; 7.20/24 0x76f158; 7.21/23/25/26 0x76f518; 7.22 0x76f6bc; 7.40/44 0x76f898; 7.41/43/45/46
  0x76fce8; 7.42 0x7700c4; 7.60 0x7703d4; 7.61 0x7704f0; 7.62 0x77060c; 7.65-67/70-72/75-77 0x770954;
  7.68/69/73/74/78/79 0x770ec0; 7.80-85 0x7713ec; 7.86 0x77199c; 7.87 0x771cb4 (7.88 is in the AI, not resolved).
- uEm083: 37 actions on 10 handlers: 1.0-2/6-8 0x8a00f8; 1.3-5 0x8a0224; 1.50/52 0x8a03e8; 7.0 0x8a05c0; 7.1/2
  0x8a0740; 7.60 0x8a08bc; 7.62 0x8a0aec; 7.65..77 0x8a0c3c; 7.68..79 0x8a0ed0; 7.80-85 0x8a1154.
- AI (EMC): em024_cmd groups [15, 58, 0 x4, 1, ...] (selectors s0-7 and s8-14, the second set adds scripts 56 / 57 =
  7.87 / 7.88); em083_cmd [8, 2, ...] picks only 1.x moves, 7.0-3, 7.20/21, 7.40: the shared attack numbers
  7.60-85 are not in the tail's AI, so the main drives them (S).
- GU precedent (C, data): Nakarkos em084_00.arc carries `collision\em084_00_g00` / `_w00` (SBC, type 0x51fc779f =
  stage collision); Ahtal-Neset em087_00.arc carries g00..g12 / w00..w15. GU em087 (registry index 133, no name) +
  em088 Ahtal-Ka (index 134) is a two-enemy fight like Dalamadur + tail. To trace: how uEm084_00 / uEm087_00 load
  and move their SBC with the joints, and how GU spawns / names em087.

## Arena
- 4U stage 8 Speartip Crag ("S. Crag"): m08a00d (camp), m08a01d (arena: breakables k00..k02, collision a-g00 / a-w00
  and a-g00-shell / a-w00-shell). The fight stays in one area; Dalamadur destroys parts of the arena over time (user).
  GU has no counterpart (stages 1..27): stage alias. Study: notes/speartip-crag.md (helper, 2026-10-21). Key results:
  - The monster breaks the arena (C): stage command 0x6c3400(stage, area 1, mId, 0) from uEm083 0x8a0a80 (k00,
    action 7.60, motion 623 frame 1238), uEm083 0x8a19d8 (k01, 7.61, motion 624 frame 810) and uEm024 0x7708c4
    (k02, 7.62, motion 564 frame 1082). The head's 1.60..1.62 sync the tail and queue 7.60..7.62; the AI picks the
    next piece by HP band (k00 < 90 %, k01 < 62 %, k02 < 44 %) and the highest broken piece (0x7731a4).
  - The two halves share one HP pool: 0x9201a0 for ids 24 / 83 / 110 / 111 (C). GU has no such sync: port it
    (controller-only damage, multiplayer).
  - Breakables k00..k02 = KowareObj mType 9..11, one action Id 0 each, collision swap part 2*mId-1 off / 2*mId on
    (the rule GU shares). The -shell collisions load with the area, nothing swaps them.
  - Host stage candidate GU m18 (S: its kod is exactly three type-0 area-1 entries); which stage m18 is and how GU
    drives its breakables: open (G).
  - bgm_st_08 = Dalamadur's battle theme (seq 11 bgm_em024, seq 12 bgm_em024_2); phase switch not traced.
- BGM (C): sound/bgm/stage/bgm_st_08.stq -> wav/bgm_em024.mca, bgm_em024_2.mca; area streams str_map/m08
  m08_a00d / m08_a01d.

## Quests (C)
| 4U | title | rank byte +0xC3 | bosses (area 1) | fee / reward |
|---|---|---|---|---|
| m10709 | Speartip Menace | 7 | em024 + em083 | 2200 / 21000 |
| m10721 | Here to Eternity | 7 | em024 + em083 | 2600 / 25200 |
| m11030 | Eternal Emperor | 10 | em110 + em111 | 3600 / 35400 |
Objective: hunt the main em only.

## Content (C)
- Materials: 677..684 (Steel, Tail Scale, Gazer, Pectus, Glaive, Talon, Tail Shell, Fanblade), 881 Ticket,
  1369..1375 (+ / Ripper), 1377..1384 (S.Dalamadur), and Vortex Bone, Skyblade Gem, Skyblade Drgnsphire (rewards of
  these 3 quests only), Shattered Omen (source to find). GU has none of them: ~28 items, the DUMMY pool (2977..2990)
  is full.
- Armor: Rebellion (Blademaster) / Riot (Gunner): HR (rarity 7), EX (Ticket, rarity 7), X (G, rarity 10), Z (Shah,
  rarity 10) = 8 series, 40 pieces. Skills: Fury, Avarice, Attack, Edgemaster / SteadyHand, Brutality, Resilience,
  Nimbleness, Frenzy Res, Stalwart, Readiness, Amplify, Hoarding, Status Res, PunishDraw, Rapid Fire, FreeElemnt,
  Expert (to map onto GU trees).
- Weapons: one line in each of the 14 classes (create: GS 104, LS 80, Lance 87, GL 93, SnS 103, DB 101, Hammer 109,
  HH 75, SA 77, IG 32, CB 86, LBG 153, HBG 54, Bow 80; upgrades into HR, G and Shah weapons).
- Out of scope (user, 2026-10-21): other sets / lines that only use Dalamadur parts (Yukumo Sky / Land, EX Kaiser,
  other lines' upgrade steps).

## Decisions (user, 2026-10-21)
- One package `monsters/dalamadur/` (Dalamadur, Shah, both tails, Speartip Crag, all the gear).
- Gear: Dalamadur gear only.
- Goal A (core) approved. Items: APPEND all new items from 2991 upward (contiguous; not GU's other DUMMY slots),
  with the items-obtained bits of IDs >= 3008 moved into the save's reserved zero block (MHGU_Editor: slot +0x50BE,
  S+0x3684, 3444 B, D "only init / save / load touch it") through hooks on the setter 0x1943d4 / clear 0x194408 /
  test 0x19443c. Save facts (MHGU_Editor docs/11-save-map.md, C): obtained map = sItem +0x9c, 94 x u32 = IDs
  0..3007, followed by the Combination List order (+0x214); item box slots hold 12-bit IDs (<= 4095).
  44 GU code sites bound the item count (movw #0xbad / #0xbae / #0xbaf): audit before raising any of them.
