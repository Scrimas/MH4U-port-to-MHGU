# Magnet Spike Phase 3: full moveset and mechanics

Goal: every MHF Magnet Spike action, mechanic and effect on GU's class 5 (Guild style, shared Hunter Arts), then
the weapons and the smithy (phases 4-5 folded in: a handful of endgame weapons, forgeable). Branch magnet-spike,
switch MS_SLICE (test builds only).

## Status (2026-10-30)
| part | state |
|---|---|
| actions | every MHF action that plays Magnet Spike motions (160; msbuild ACTIONS), steps / cancels / events from mhfdat |
| inputs | one class id per (MHF input, condition) pair (21 pairs, x2 modes); conditions run in the translator |
| hits | 140 attack / special entries + magnetised copies (MV x 1.1); code specials #5-#7, #10, Magnetic Shock 5 x 3 (#12 x 4 spots, MHF's task 0x0f); specials' shapes by special id (were all empty); MV-0 specials not armed |
| gauge, Magnetise | regen, on-hit gain, bar costs, Magnetise charge / on / lockout (log only: no HUD yet) |
| guard | Guard Counter 14 -> 207 -> 57 / 76 / 77, Impact guard 112 -> 113 -> 114 / 115 (GU guard patched for class 5) |
| charge | Triple Strike 34 -> 208 -> 35 / 36, overcharge release |
| marker / attraction / repulsion | marker stand-in (nearest monster in front), flight phases, falling attacks, approach cancel |
| pin | leap -> pin on hit -> QTE (X / A mash) -> finisher / pin over; the hunter rides the monster |
| HUD | the Charge Blade's phial widget (class 5's HUD case -> CB's, hook 0x646560): 5 phials = gauge bars, colour = mode, first element = Magnetise (ready 2 / on 1 / lockout 5, S) |
| swing arcs | GU has no blade ribbon: a swing = GS's ring mesh (cm010_000, crescent texture) posted once by the class PSL. msfx.py fits each attack's blade-tip path (MHF FK, live frames) and writes its own PEL list-1 record (ids 1000+: plane, head on the blade, scale = tip radius; GU's effect Euler order = MHF's, 0x8a7dc4 case 0): 34 arcs on 29 motions (attacks with no weapon capsule or < 35 deg of sweep: none). MHF's swings: radius 1.4-4.5 m, sweeps 70-480 deg |
| effects | GU stand-ins posted by code (vt+0x39c = PEL list 1; GS's 0-5 / 20 / 21 = its slash arcs, 6-11 / 30 / 31 its charge flashes): Triple Strike charged = flash 7, guarded hit = flash 9, Magnetise on = flash 11; Magnetic Shock 5 x 3 = GS's ground impact (105) at each spot; the marker = flash 9's copy (1200, no sound) at the marker point every 2 s (world-position request 0x40b10, as em089_efx.c); Magnetise running = flash 11's copy (1201) on the weapon hand every 1.5 s (S). MHF's own effects (dat/effect.bin, Frontier's format) not converted; MHF's 0x10b43370 calls are rumble presets |
| sounds | the motion sound sequence pl_wp05 (msfx.py): GS's records on GS's motion slots, ours = GS's whoosh_b + layered whoosh (fast in Cutting, slow in Impact) 2 frames before each attack. Class 5's weapon sound requests were "no file" (resolver 0x4ea0dc's class-5 case): hook ms_snd_file asks as class 0, so our record's mSrqrNo 1 / material give GS's two001 / two_bcom, packed into w05.arc. GS's flash sound plays with the flashes (its PTS). MHF's weapon banks (wkNNN.snd) = MOMO + JPK-packed Sony HD + PS-ADPCM: decodable, but MHF plays them from code (0x103339d0 per-action extras), triggers not traced; GU waves are DSP-ADPCM (needs an encoder) |
| weapons, smithy | 6 forgeable weapons in a 15th forge category (below) |
Mechanics and deviations: mechanics.md. Hit / motion pipeline: phase2.md.

## Weapons and smithy
| ID | weapon (MHF id, model) | GU raw | element | recipe (GU item IDs) |
|---|---|---|---|---|
| 2 | Demon Flamespike "Flash" (17516, wk595 -> mbg002) | 352 | fire 24 | Teostra Hardhorn 2, Cortex 4, Gem 1, Firecell Stone 5 |
| 3 | Volnoborin IV (17563, wk606 -> mbg003) | 310 | water 45 | Lagiacrus Mantle 2, Plate 3, Plesioth Hardfang 4, Novacrystal 5 |
| 4 | Torid Pillar "Uzi" (16964, wk414 -> mbg004) | 309 | thunder 47 | Zinogre Hardhorn 2, Hardclaw 4, Jasper 1, Eltalite Ore 5 |
| 5 | Anoru Pillar "Wandemu" (16968, wk415 -> mbg005) | 303 | ice 50 | Barioth Cortex 6, Novacrystal 6, Meldspar Ore 5, Eltalite Ore 5 |
| 6 | Apophis Pillar "Flash" (16933, wk404 -> mbg006) | 352 | dragon 24 | Valstrax Hardclaw 3, Cortex 4, Gore Magala Mantle 1, Novacrystal 5 |
| 7 | Apophis Pillar "Clear" (16936, wk407 -> mbg007) | 374 | - | Rajang Hardhorn 2, Hardfang 3, Deviljho Gem 1, Eltalite Ore 5 |
All: rarity 8, 3 slots, affinity 0, GU kireaji 106 (level 10), 60000 z, one level, no upgrades, always listed (no
key material). Stats scaled from MHF (raw x 0.55, element x 0.3; S, user's call). Models: GU's file table names
weapon\w05\mbg001-007 (ids 21815-21821, C), so models 2-7 need no file-ID work.
Smithy (static research gu_smithy, C unless marked): the forge's category cursor {kind 8, 7 per page, count 14} at
0x165007e (count -> 15, page 3 = the Magnet Spike); category -> type u8[14] 0x1650022, labels (LbShop_EqMakeMsg IDs)
0x1650058, top-panel icons 0x176f3e4 kind 8: module copies (build.py MS_LIT_PATCHES); the create / process getters
0x6f9658 / 0x70153c hooked for type 12; label 206 "Magnet Spike" appended to LbShop_EqMakeMsg (count 206 checked);
CommonMsg 90 (class 5's name, "Med. Bowgun (Removed)") replaced; names / descriptions from the base vtable's
+0x3c / +0x40 / +0xbc / +0xc0; list icon of type 12 = the Great Sword's (0x1650018). Not done: forge counter
0x162e0c counts type 12 as LBG; the scrap list (0x73bcec) skips class 5; a real Magnet Spike icon.

## Deviations (S, to settle in tests)
Marker = nearest large monster within 0.6 rad / 5000 units of the camera's aim, at the monster's origin + 300; the
QTE (hold 60 / cap 90, 70 points); every
MHF camera-shake preset = GU 0xf; the monster is not held during the pin; Guard skills = GU's has-skill 14 / 15;
the Magnetic Shock spots follow the hunter; R1 + evade = R + Y.

## Test 1 results (user, 2026-10-30) and fixes
| # | report | cause (log / data) | fix |
|---|---|---|---|
| 5, 12, 13 | no attack while walking, none after a roll, R moves not from idle | the common tables (0 idle / walk, 11 walk start, 12 / 13 rolls) lost GS's weapon commands and ours sat after GU's move / Hunter Arts commands (GU takes the first ready one; our idle block even had the stick's move before X / A) | ours in place of GS's, with GS's windows; no move command inside our block; GU's move last among equal priorities |
| 11 | no jumping attacks | tables 18 / 19 (jumps 1/4, 1/5, 1/137, 1/140) lost GS's jump attack | tri = MHF's falling attacks 59 / 73 (the attraction flight's tri) |
| 14 | sheathing while walking rolls | slot 9 (common 1/3, sheathe while moving) played MHF 1021, an Impact-form evade | slots 9 / 11 = GS's motions |
| 15 | jumps / rolls always in the Cutting form | GU's rolls play 5012 / 5013 in both modes; bank-0 motions (jumps) give the weapon motion 1 | Impact: 5012 / 5013 -> 5032 / 5033 (MHF 1010 / 1011), idle variants 5005-5007 -> 5020; the weapon sync picks by mode as SA's (hooks 0x308ddc / 0x308e68) |
| 8 | no Triple Strike cue | every MHF timer ran at half speed (tick = dt x 0.5; gauge regen measured ~100 / s), so the cue needed ~2.2 s of holding | tick = dt (cue ~1.5 s after the third hit starts); release logged (frame, A, charge) |
| 10 | L / ZL = camera reset / lock-on | - | user's choice: ZR held = aim, R + ZR = Guard Counter |
| R + B | sheathed at idle | GU's sheathe command 1/2 (common id 0xd) precedes ours | common ids 0xd / 0xe cleared when an R input of ours fires |
| 16 | crescent too big | scale = tip radius / 109 cm (2.4x GS's for a 2.6 m reach) | scale = tip radius / 260 cm (GS's blade reach at scale 1) |
| 4 | models lie flat in the viewer | the viewer stands a weapon on model z (GS: z -80..224); ours lay along x | model + weapon motions' root turned Ry(-90) (msgrip.TURN), the hand grip undoes it |
| 1 | descriptions out of the box | one long line | GU's 3 lines of <= 32 characters |
| 2 | same sharpness / rarity / affinity / slots | MHF's own records of the six: rarity 12, 3 slots, 0 % affinity (user: keep MHF's); sharpness ids differ (2 / 13 / 17 / 21): mhfdat header +0xac -> per-type pointers, MS = 0x18ff500, 8 cumulative thresholds of 400 (C) | MHF's bars as 4 appended kireajiData rows (gear.c, MS_SLICE; GU = 7 cumulative of 450: purple = MHF purple + 8th colour + Handicraft's 50) |
| 9 | X + A after the Guard Counter | MHF: only after a guarded hit (57 / 76 / 77, from f68); 57's table had GU's move before it | move last (above) |
| 17 | hits miss | capsules checked against MHF's mesh in the hand frame (they match bone by bone); the oversized crescent suggested a reach the blade does not have | crescent fix; to re-check in test 2 |
| 6 | no sound | not diagnosed (no log of the resolver) | resolver calls logged |
| 3 | GS / bowgun icons | three type -> icon id tables (0x162e7dc / 0x164ff08 / 0x165000c), only the forge's was patched; HD_cmn_icon = 64-px cells, 10 per row, id n = cell (n % 10, n // 10) | MHF-Z's Magnet Spike icon (UI bank dat/mhf_90c.bin.xbox PNG 6) in the empty cell 121 of the user's HD UI atlas (tools/ms_icon_hdui.py, backup .pre-magnet-spike; GU's own atlas: cell empty, a release needs a module-side atlas); type 12 -> 121 in the three tables and the forge's category icons |
| 7 | CB's HUD | class 5 drives CB's gauge widget; its .gui (hud14_chargeAx, quest_eng.arc) draws vials / shield from HD_hud00 | MHF's MS HUD art (UI bank PNG 4: horseshoe head, 5-cell bar, red / blue / grey horseshoes) painted over CB's vials / shield in a copy of HD_hud00 (tools/mshud.py -> mh4uport\ms_hud00), swapped into that .gui's texture entry while a Magnet Spike hunter drives it (ms_class.c hud_look). Layout = CB's (5 cells where the vials sit), not MHF's bar |

## Test 2 results (user, 2026-10-30; smithy / village only: every quest crashed) and fixes
| # | report | cause (log / data) | fix |
|---|---|---|---|
| crash | entering a quest crashes | hud_look walked the gauge .gui's objects as sprites; a non-sprite's +0x78 went to GU's lookup 0xb80fd0 as a table (read 0xff000000) | no object walk: 0xb80fd0's first argument is the rGUI (loader 0xb7f988: file +0x64, table +0xe8, count +0x70); module/icons.c's hook on it hands each rGUI to ms_gui_seen, the gauge's = path hud14_chargeAx |
| 3 | icon = a piece of other icons, same everywhere | 0x560918 kinds 0 / 1 (16 / 24 units of a 256 x 512 space; GU's atlas 2x, HD UI's 4x): ids < 95 on a 10-column grid, 95..106 from lists 0x162e208 / 0x162e1a0; 121 read past them = (52, 348) (matched in the screenshot). Every grid cell is taken in both atlases | hook 0x560920 (after the kind check): MS_ICON_ID -> spots empty in both atlases, (184, 48) x 16 and (208, 32) x 24; ms_icon_hdui.py paints them, test 1's cell restored |
| 4 | viewer still flat; the back turned 90 deg | GU weapon roots are identity; the viewer replaces joint 0's transform, so the turn on our root cancelled (in the root's bind frame the vertices still ran along x); GS's carry records do not undo the turn | the turn moves to the root's child (no vertex is skinned to the root; animated frames unchanged); the carry records GU applies off-hand get the turn undone (ms_class.c back_record, quaternion record (x) grip) |
| 2 | bars do not follow red .. purple; 3 slots, 10 % affinity | the bars are MHF's (type 13 rows skip colours: id 2 = red 170, white 30, purple 50, sky 150); level row +15 mAffinity = 0 (10 % = the user's cheats) | none (reported) |

## Test 3 results (user, 2026-10-30) and fixes
The user names buttons by the Xbox pad's letters (HD UI shows Xbox glyphs; Ryujinx maps by position: Switch A = Xbox B,
B = A, X = Y, Y = X). Test notes must use them. GU's player bits (+0x13f4) under the user's control type: d-pad 0x1-0x8,
B 0x10, X 0x20, R 0x40, Y 0x80, A 0x100, ZL 0x200, L 0x400, ZR 0x800 (roles 0x65f93c / 0x65f8ec / 0x65f9b4 swap
0x40 / 0x800 and 0x200 / 0x400 with the other type; 0x400 = GU's camera-reset handler 0x27e970). Minus is not 0x200.
| # | report | cause | fix |
|---|---|---|---|
| 10 | ZL switches modes | MHF's SELECT read 0x200 = ZL | SELECT = bits 0xf000 (S, Minus not identified: the "other buttons" log) |
| 13 | R + left does the back step, R + bottom the left step | R1 + special / R1 + evade on Y / B | swapped: R + left (Y) = 106 / 158, R + bottom (B) = 107 / 116 |
| 5, 12 | walking / after a roll: the idle attacks | GU's walk shared table 0; MHF's walk (40 / 44) has its own attacks (48 / 49 / 51 / 61, 52 / 54 / 53 / 146 / 71: a quicker lead-in into chain swing 2) | table 1 (pick392 for 2/0), 11, 12, 13: the walk's attacks first (user: after a roll = "the second Y -> Y, B -> B, faster") |
| 17 | visible hits miss ("A misses, A misses, A hits") | MHF counts attack life in 30 Hz ticks, motions run 2 frames a tick (Triple Strike cue: 20 ticks = f40); Impact 1 / 2 (14) and 3 (22) share one shape | live frames = 2 x MHF's; hit view: the marker flashes at both ends of each armed hit's capsule (ms_act.c MS_HIT_VIEW) |
| 8, 9, 11, 18 | no charged strike, no X+A after GC, no jump attack, no pin | wrong buttons (Switch letters in the checklist; the log: B mashed during the charge, the GC caught hits) | instructions in Xbox letters |
| 20 | a second GC before the first ends | MHF's GC 14 cancels to 14 from f60 (of 133) | none (MHF) |
| 3 | the icon is wrong | MHF's type icon was not the one | the user's icon (dump/mhf/ui/ms_icon_user.png), pure white cleared |
| 4 | viewer too close | the viewer frames as GS's (sphere centre (8, 0, 72)); ours sat at (-22, 0, 0) | bind pose moved by (30, 0, 72) (fmod2gu VIEW_SHIFT; every motion keys the bones, so only the viewer sees it) |
| 16 | crescent slightly too small | scale = r / 260 | r / 200 |
| 2 | same slots / affinity | MHF's six share them (record +19 slots, +14 affinity) | MHF's 16932 (3 slots, 50 %), 16926 / 17511 (0 slots, sharpness id 0: a full red-to-purple bar) added |
| 6 | sound only on draw / sheathe | not traced yet | - |

## Test 4 results (user, 2026-10-30) and fixes

| # | report | cause | fix |
|---|---|---|---|
| 9 | hits miss across the weapon | every Cutting attack has the same two r50 capsules (the U's prongs, checked in MHF's FK: they stay on the blade, 0 cm drift) and arms 2-6 frames before the swing's fastest frames, yet in the quest short fast swings landed 0-1 of 5-8 (actions 4 / 12 / 0, tip 160-180 cm a motion frame) and long sweeps 6 of 8 (action 11, tip 70 cm a frame): GU tests the shapes at each update's pose, the blade steps over monster parts. GU's fast weapons (LS, SnS, DB, SA, IG, Hammer's spin set) pair every blade shape with a type-5 shape (b.x = the blade's far end on the joint's z), GS / Lance / GL none: a trail, fields not decoded; our capsules lie up to 171 cm off the hand's z | msbuild `ghosts`: each weapon capsule gets a copy half a motion frame behind at the live window's fastest frame (hand frame; 2 -> 4 shapes, GU's max per set), offsets 12-164 cm |
| - | element never dealt | MS_ARM flags 0: 0x2b76cc sets the element only for non-zero flags; GU's classes pass 3 or 0 | flags 3 |
| user | no Frontier effect but the crescents | code posts (vt+0x39c) read PEL list 2 (GS's 500-517: its code-posted charge glows; list 1 = the PSL's, as em089's mode 2); ours were list-1 ids (the marker's post returned 0) | msfx CODE records in lists 1 and 2; flashes 1300-1302 on joint 8. MHF's own effects (dat/effect.bin): a later phase (user: wanted) |
| 1 | Back and Plus both switch modes | BTN_MINUS 0xf000 | log: Back held 0x4000 (pressed 0x5000): 0x4000 |
| 2 | RB + Back does nothing at a full gauge | Magnetise has its own charge per form (MV x 0.8 per hit, 1000; the user's Cutting reached 772); the 5 bars are the gauge | none (MHF's rule) |
| 8 | R + Y / B while walking = the walk's Y / B | plain tri / circle matched with R held | inputs 2 / 3 / 4 need R up (R1 is a modifier) |
| 6 | pin never starts | the leap's grab (MHF attack 17, MV 1, the same capsules) must land: missed like the swings | ghosts |
| 5 | no jump attack | log: only GU's 12-frame step-down hop (1/137, table 2018); the button log had run out | jump-press log (cap 40) |
| 10 | smithy viewer still too close | - | header bounding sphere x 1.6 (fmod2gu VIEW_RADIUS, S) |
| 11 | sheathed weapon carried like a GS | GS's carry record; MHF's: a ∩ on the back (curve behind the shoulders, prongs down past the hips), MHF keys it in code or its draw / sheathe motions (1471-1473 candidates) | later |
| - | test 4's armed-hit log (cap 60) ran out in the village | - | quest-only, with the nearest monster's distance (cap 400) |

## Test 5 results (user, 2026-10-30) and fixes

| # | report | finding | change |
|---|---|---|---|
| 1 | not every visible hit lands, some late; the crescent late too | with a large monster 1.5-3 m away most armed attacks landed (ghosts), but actions 48 / 5 / 3 / 4 (armed f6-f13) landed 0.34-0.45 s later, at motion frames 33-35 whatever their arming frame, while MHF's blade peaks f15-21 (motion 1047: f18): the capsule does not sit where GU draws the blade (MHF FK: 0 cm). The crescents posted at the live window's middle, 14-24 frames after arming since test 3 doubled the windows | hit check log (ms_act.c hit_check: capsule end via the hunter's joint vs the same point on the drawn weapon's bone, at arming and +8 frames); msfx posts each arc at the swing's fastest frame (4-5 frames after arming) |
| 2 / 4 | no charged / marker flash | GU's code post vt+0x39c is called as GU's classes do (p, id, p + 0x2550, 1; GS: 6 / 7 / 36 = list 1, so test 4's list-2 reading was wrong) and returned 0 for every id under class 5 (GS's own 7 in test 3). The class list exists: 0x29adbc reads file ID 0x162868c[class] (class 5 = 0x89a = effect\pel\pl\w05_000) into +0x3304 | ms.h ms_post: 0x282548(p, +0x3304, list 1, id, req, 0) -> 0x53b500 -> 0x40978 (extra 0 null-checked); the guard log prints the handle |
| 4 | marker never placed | all six shots "missed": no large monster alive (em_ok, large only) | none (aim at the large monster) |
| 5 | pin | the leap's grab never hit (2 landings) | waits on 1 |
| 6 | jump attack | three hops (1/137, 0.7 s): no press logged in any | the jump log adds held buttons |
| 8 | no element (smithy, hits) | the attack's element comes from the hunter's stats vt+0x15c (0x11 type, 2 value), filled at equip time; the smithy reads the weapon data through per-class code (13 class readers of mElement, 0x1014d8..0x125350) | log of the hunter's stats at the first quest frame |
| 9 | viewer unchanged | the bounding sphere does not set its framing | reverted |
| user | ghost size (test 5 note, kept below) | see below | see below |

## Test 6 results (maintainer, 2026-10-30) and fixes
Log: dump/mhf/test_logs/ms_test6_Ryujinx_..._2026-10-30_16-13-37.log (956 msport lines; hit check, element stats,
jump held-button and effect-handle logs inside). The maintainer's answers (Demon Flamespike equipped):
- crescent with the swing now: yes
- Triple Strike full-charge flash (Impact B, B, hold B): no
- flash on a guarded hit (RB + RT): yes
- marker blink on the large monster (RT + B): no
- jumping attack (Y in the air off a ledge): still none

| # | issue | log / cause | change (test 7) |
|---|---|---|---|
| 1 | hits late (test 5) | NOT placement (C): the capsule end = the drawn blade, 0 cm at 31 of 37 checks, 16-18 cm at a few arming frames. Every hit lands at motion frame >= ~33 whatever its arming frame: f11 -> +0.37 s (9 of 9, also on a small monster 22 m from the large one), f27 -> +0.10 s, f31 -> +0.04 s, f33+ -> at once. No re-hit lockout (+0.37 s even 5 s after the previous hit). GS's HDP [0] / [1] are not start / live frames (GS: 96..280 / 75), 0x2b72d4 uses [0] only with flag 0x4000 clear | hit check off; slot trace: the armed slot (p+0x3020 + slot x 0xb8) per update for 40 updates, 6 early arms |
| 2 | no element | hunter stats key 0x11 = 0, key 2 = 0, raw 389 (C): lost at equip time. The 13 "per-class mElement readers" are save serialisers (0x1014d8: stream writes), not the fill; the fill is not 0xdee34 (skills) nor 0xe1bbc. The type -> class table 0x159fdcc: gunner types 11 / 13 / 17, so `type - 11 < 3` tests (0x5402dc, 0x6ceda4, 0x6d2fa0, 0x11ffe4c) count type 12 as a gunner (S: the smithy's missing element; not patched, what they gate is unread) | stand-in elem_fix: the record's element into stats +0x342 / +0x324 (hunter data +0x320 + 2 key) while GU left them 0; weapon entry copy at hunter data +0x18 (+4 type, +6 id). Element skills are lost while it stands in |
| 3 | no charge flash | posted (handle 47efcf80) through the guard flash's path: GS flash 7 itself is unseen | CHARGED = flash 9 (the guard's) |
| 4 | no marker blink | 5 posts with handles at the monster: the request had no owner (req+4) nor area (req+0xc), which em089_efx.c's world posts set | req+4 = hunter, req+0xc = the area of the hunter's request +0x2550 |
| 5 | no jump attack | one jump (1/140, table 2019): no input until RB at frame 41 (the log fires on any change: nothing was pressed, or the class input is not polled before frame 41) | log the first input frame of each jump |

## Test 7 results (maintainer, 2026-11-03) and fixes
Log: dump/mhf/test_logs/ms_test7_Ryujinx_1.3.3_2026-11-03_19-25-59.log. The maintainer: hits still late in both
forms; the charge flash showed a GS slash, not GS's charge glow; the marker shot animates but nothing shows on the
monster, attraction / repulsion never trigger; no jump attack on Y in the air.

| # | issue | log / cause | change (test 8) |
|---|---|---|---|
| 1 | hits late | C: slot +0x5c (start countdown, -0.5 per update) = 21.9 at f12, live at ~f34, +0x60 (live) = 10.0. HDP [2] is the absolute motion frame the hit goes live on (0x2b72d4: [2] - current frame), [3] the live frames: mshit wrote MHF's live frames into [1] and kept GS's [2] = 34 / [3] = 10 (Impact: MHF's KO went into [2] = its start frame) | [2] = 0 (live at the ATTACK event), [3] = MHF's live frames; MHF's KO has no GU field yet (template's) |
| 2 | charge flash = a GS slash | template 9 = a GS slash trail | GS's charge flash 7 on its own joint (65535; test 6 forced it onto joint 8) |
| 3 | no marker blink; attract / repulse never | two marks landed (37 m, 16 m); 5 flashes posted with template 9 (a slash trail: nothing at a still point). One attraction (58) started. MHF's rule: attract = aim (RT) + Y with the mark 14-40 m away, repulse = aim + A within 14 m, both 1 gauge bar + stamina | marker = GS's charge glow 6; refused aim + Y / A logged with the mark's distance |
| 4 | no jump attack | three hops 1/137, input polled from frame 0, no change logged | every jump frame logged (held, pressed, combo) |
| 5 | element (stand-in) | elem_fix never ran: the weapon is not equipment slot 0 (slot by type, 0xdae68) | scans the 8 entries at hunter data +0x18 + 0x2c k for type 12 |

## Test 8 results (maintainer, 2026-11-03) and fixes
Log: dump/mhf/test_logs/ms_test8_Ryujinx_1.3.3_2026-11-03_19-48-39.log. The maintainer: hit boxes now in sync with
the weapon (FIXED); the charge flash shows an effect but the wrong one (no MHF-ZZ effect is drawn at all: the MHF
effects port is its own phase); no marker blink; aim (RT) + Y / A did the plain Y / A attacks; no jump attack, and
running off a small step is enough for one in GU (not only high ledges).

| # | issue | log / cause | change (test 9) |
|---|---|---|---|
| 1 | aim + Y / A = plain attacks | 7 "aim Y refused: marker -1": no mark, so the plain tri pair matched; MHF's "aim:" inputs mask the plain ones while aiming | plain tri / circle / tri+circle need aim off |
| 2 | no marker blink | posted (handles) at the mark; the request's ground word (req+0x6c, body field 19) was 0: an effect keeps only elements whose word meets (2 << kind) \| 1 (em089_efx.c) | req+0x14 bit 19, req+0x6c = 3, as em089's posts |
| 3 | no jump attack | four hops (1/137, 0.6 s, table 2018): held stays 0 on every frame in three; X (0x80) in one; nothing pressed in the class input during any hop, and no ground attack after them | every press while airborne logged (any action, height) |
| 4 | element (stand-in) | still no fix line: a type-12 entry found, its id gave no element | logs the entry |

## Test 9 results (maintainer, 2026-11-03) and fixes
Log: dump/mhf/test_logs/ms_test9_Ryujinx_1.3.3_2026-11-03_20-00-47.log. The maintainer: no projectile, no blink;
aim + Y does nothing, aim + A rolls on its first frame; aim + Y unmarked does nothing (OK); still no jump attack.

| # | issue | log / cause | change (test 10) |
|---|---|---|---|
| 1 | no jump attack | every airborne Y came in 4/14 (the SHEATHED jump, table 2024) as sheathed command 5 = GS's jumping draw attack; s_ind_stand[5] = {1, 0, 0} (nothing). The jump code watched drawn jumps (category 1) only | command 5 in category 4 -> {0x10, 59}: MHF's falling attack 59, with the draw flag |
| 2 | aim + A rolls | GU's common roll ids (+0x1418 bits 17-18) come before ours; only R held stripped them | stripped while aiming too |
| 3 | no element | the equipped box entry is id 7 = Apophis Pillar "Clear", the one Magnet Spike with no element (stats raw 389 = its 374 + 15; "Flash" would be 352 + 15): likely no element bug at all | none; retest with Demon Flamespike "Flash" (id 2) |
| 4 | no projectile, no blink (-> MHF effects port, the maintainer's call after test 10) | the projectile is not built (stand-in: the nearest large monster within 0.6 rad of the facing, 50 m); test 9's 3 shots found none in that cone, so no mark, no blink. The blink effect failed tests 6-8 with a mark | open: GS-template stand-ins at a world point never showed; MHF's projectile + mark effects belong to the effects port |

| (test 5) | ghost size | tuned to ~60 updates / s (the 120 FPS cheat, dt 0.5): native 30 fps moves 2 frames per check | before release: a hunt without the cheat, resize (a dt-based second set would pass GU's 255-set limit) |

## Test 1 (Phase 3; save backup dump/save_backups/2026-10-29_before_magnet_spike)
Test 2 changes the buttons: ZR held = aim, R + ZR = Guard Counter.
Buttons (MHF -> Switch by position): tri X, circle A, tri + circle X + A, special B, R1 R, R2 ZR, SELECT Minus,
aim L (or ZL). The gauge starts empty and fills 1 bar / 10 s and by hits; R moves cost 1 bar.
1. Chains in both modes (Minus switches), Transform Attacks (Minus after a horizontal).
2. Triple Strike: circle, circle, hold circle; release at the cue (camera shake) = Charged Strike.
3. Guard Counter (ZR) into a monster attack, then X + A; Impact guard (ZR in Impact), then X / X + A.
4. R + X, R + A, R + X + A, R + B, R + Y (check against Hunter Arts), R + Minus when Magnetise is ready (log).
5. Aim (hold L) + A at a monster (marker), aim + X (attraction; X in flight = falling attack, B = cancel), aim + B
   close to it (repulsion).
6. After R + X (double slash), R + X + A = Magnetic Pin; mash X / A.
7. Smithy: Forge Weapons -> page 3 "Magnet Spike": 6 weapons listed with names, stats, recipes; forge one, equip
   it (model).
8. HUD: the Charge Blade's phial gauge = the magnet gauge (5 bars); its first element's look when Magnetise is
   ready / on / locked out.
9. Arcs and sounds: a white crescent along each swing (does it follow the blade, the right side, the right way
   round?), whooshes on swings, a flash (+ GS's flash sound) at Triple Strike charged / guarded hit / Magnetise on,
   a silent flash on the marked monster every 2 s and on the weapon every 1.5 s while magnetised.
10. Magnetic Shock 5 x 3: evade through a monster attack with R + Y (or R + A) in Impact, then X / A: four ground
   impacts marching forward, each hitting (log "Magnetic Shock 5 x 3").
Report: crashes, stuck actions, which aim button worked, what looked wrong.

## Test 10 results (maintainer, 2026-11-03) and fixes
Log: dump/mhf/test_logs/ms_test10_Ryujinx_1.3.3_2026-11-03_20-08-12.log. The maintainer: Demon Flamespike "Flash"
shows no fire element in the smithy; the sheathed jump attack starts (airborne part) but goes back to idle on
landing; aim + A still rolls. Effects: port MHF-ZZ's own (next phase).

| # | issue | log / cause | change (test 11) |
|---|---|---|---|
| 1 | no element in the smithy | the quest's weapon was still box id 7 (Apophis "Clear", no element). The smithy / equipment rows test `type - 11 < 3` (HBG 11, LBG 13) at 0x5402dc, 0x6ceda4, 0x6d2fa0: type 12 = a bowgun row, no element line | build.py MS_GUNTYPE_SITES: type in {11, 13} (cmp / cmpne / bne) |
| 2 | falling attack cut on landing | 59 ended on landing (kind-5 step) | landing 59 -> 60, 73 -> 74 (MHF's landing actions: motions 1015 / 1014, shake) |
| 3 | aim + A rolls | no "aim A refused" line: aim + A never matched (aim + Y did) | every press while aiming logged with GU's common ids |

Test 11 (smithy screenshots, maintainer): still no "Elem." line for Demon Flamespike "Flash" (GS Chicken Decapitator
shows its fire 18 there), affinity 20 % (ours: 0). Cause (C on the code): the second base-record getter 0x13eef8
(type - 7 switch over sEquip BaseData +0x50.., find by id 0x12f7ac; callers: the smithy 0x6eb6c0..0x70361c, equip
0x26ec84) has no type-12 case: null base record, so no element type. Hook ms_base_find = ms_base (test 12); the
gunner-type patch of test 10 stays (harmless, unconfirmed).

## Tests 12-14 (maintainer, 2026-11-03 / 04) and fixes
Logs: dump/mhf/test_logs/ms_test13_..., ms_test14_Ryujinx_1.3.3_2026-11-04_08-59-10.log. Test 12: the 0x13eef8 hook
never ran for type 12 (wrong lead). The maintainer after test 14: RT + A rolls; no element in the smithy; RT + Y
attracts but nothing can follow it, too fast and too far; R + Y / A / X / B have no i-frames; no Guard Counter
follow-up on "X + A"; no reticle, projectile nor launcher while aiming; MHF's effects missing.

| # | issue | cause (C unless marked) | change (test 15) |
|---|---|---|---|
| 1 | RT + A rolls | tests 10 / 13 (each press and the GU action it started): 0x80 starts GU's rolls 1/6, 1/13, 1/14 = the bottom button (Xbox A), 0x10 the sheathe 1/3 = the left one; the module's BTN_* names had them swapped. MHF's MS keyconfig: special(A) (key 0xeb, the repulsion input 23) = bottom, so input 23 read the left button. The aim strip cleared ids 49 / 50 only, while 1/6 tests common ids 4 / 24 / 38 (plcmd_com_0x0001_006d..f) | PAD_L / U / D / R names by position; 23 = aim + bottom; aiming clears ids 4, 24, 38, 49, 50 (S: MHF's evade input 0 has no aim test) |
| 2 | no element (smithy, quest) | the element getters by box entry 0xdb984 (type) / 0xdba5c (value) answer only types in the mask 0x3bc780 (no bit 12). Callers: the panel's element line 0x586574 and the equip-time stat fill 0xdee34 (hunter stats 0x11 / 2). The 20 % affinity is the panel's skill-inclusive view (hunter stat 0x10) | build.py MS_ELEMENT_MASKS: movw #0xc780 -> #0xd780 at 0xdb9a4 / 0xdba78; ms_act.c elem_fix logs GU's own values and writes only if GU still left type 0 |
| 3 | attraction: nothing follows, too fast | (a) GU's dt counts 1/60 s (test 13: 40 updates in 0.326 s at dt 0.5; test 14: regen 2 x MHF): MHF's tick = dt / 2, the module used dt, so every MHF timer and drive ran twice as fast; the flight landed by motion frame ~49, before MHF's follow-up window (58 / 61: tri -> 59, cross / aim + special -> 63 from f50). (b) msbuild turned MHF's evade cancels of the attractions (input 0 -> 63 / 69, the approach cancels) into GU's rolls. (c) the fall moved along the horizontal-normalised direction; MHF (0x103327a0) along the 3-D unit one, 90 x 0.97^n, plus n x g down. MHF's flight (0x103317c6, 0x10332dd0): budget = |marker - hunter| - 300 = ease-in 252 + 90 per tick, so "300 short" is MHF's; "too far" = the stand-in marker point (the monster's origin + 300, inside its body; MHF's sticks where the shot hit) | tick = dt / 2; APPROACH (63, 69) commands on our input 0 (bottom + stamina 150); MHF's fall step; the marker point waits for the projectile (item 6) |
| 4 | R moves without i-frames | MHF: event 8 = param (7 ticks) + 5 / + 10 with Evasion +1 / +2 (0x10337e30: skills 0xb1 / 0xb2 or their other sources): Capcom's chart's 17 = 7 + 10. The module grants 2 x 7 GU frames (+0x2b40 in 1/60 s, = MHF's 7 ticks) with GU's Evasion. Test 14's hit in RB + Y came 0.53 s in (after 7 ticks, inside 17) | none (MHF's values); log of each grant and of every hit during an MS action |
| 5 | no Guard Counter follow-up | 57 / 76 / 77's tables have MHF's tri + circle -> 154 (f28 / f68) and tri -> 16 (f46-f76) = Xbox Y + B / Y (MHF keyconfig: tri + circle = pad bits 0xa, top + right); "X + A" was the test-3 checklist's Switch letters; test 6's one try rolled | press log during 57 / 76 / 77 / 114 / 115 |
| 6 | aim: no reticle, projectile, launcher | MHF (static study, mechanics.md "Aim" / "Shot"): a projectile flies 500 per tick along the camera's 3-D view and sticks to the hit bone (a miss = no marker); the reticle is HUD sprite 0xb6; there is no launcher model (the left hand + effect 0x312). The stand-in picked the nearest monster in a cone and used its origin + 300 (item 3's "too far") | MHF's shot against GU's hurt volumes (0x710b0 / 0x16de70), the marker on the hit joint; reticle, aim camera and effect 0x312 open |

## Test 15 (built 2026-11-04, commit d32b247; played 2026-11-04)
Build: `GOG_DEFINES=MS_SLICE` (items 1-6 above). Play, then close the game; the log answers the rest. Xbox letters.
1. RT + B at a large monster's body: the shot log says hit (joint, point) or miss; the marker stays on that part.
2. RT + Y from 14-40 m to the marker, then Y or A in the air (MHF's 58 / 61 follow-ups).
3. RT + A from under 14 m: repulsion, no roll.
4. Guard Counter (RB + RT) into an attack, then Y + B (follow-up 154).
5. An RB move (RB + Y / A / X / B) through an attack: the log prints each i-frame grant and any hit.
6. The smithy element line of Demon Flamespike "Flash" (and the element in a quest).
7. (Added 2026-11-04) MHF's own effects, converted (mhffx2gu.py) and posted where MHF posts them (msfxposts.py,
   notes/effect-posts.md; the log prints each "mhf effect" post): Triple Strike (charge to the flash, then let it
   overcharge), a guard (RB) and an Impact guard, Magnetic Shock (hit and whiff), the attraction and repulsion,
   Guard Counter success, Charged Strike, Supplex, Magnetic Assault, Double Slash, Finishing Slash, the pin slam
   and finisher, Guard Assault; some only while Magnetised (as MHF). Still GS stand-ins: the marker, the shot,
   Magnetise's aura. If the game crashes when a quest loads with the Magnet Spike, it is the new
   effect files in w05.arc (say so; MS_MHF_FX=0 for msbuild.py leaves them out).
Ask only about visuals: did the attraction look too fast / too far, what the shot looked like; the effects' size
(too big / small: one global factor), colour, placement (on the hand / ahead / on the ground) next to MHF's.

### Test 15 results and fixes
Log: dump/mhf/test_logs/ms_test15_Ryujinx_1.3.3_2026-11-04_16-05-36.log. The maintainer: (1) no shot, marker or
launcher visual, and the marker "consumed too fast"; (2) the attraction works but is janky (sometimes too high and too
slow on the follow-up, the attracted-to point slightly off or behind); (3) RT + A fixed, but RB + A while moving
rolls; (4) still no Y + B after a Guard Counter; (5) RB moves still seem to have no i-frames; (6) the smithy element
is right; (7) no MHF effect at all.

| # | issue | cause (C unless marked) | change (test 16) |
|---|---|---|---|
| 1 | marker gone too soon | "marker gone" 1.8-4.3 s after each hit, at the attraction's landing: the marker life test used em_ok, the hit pass's filter, whose hurt gates (rec+0x1a0 / +0x444, m+0x7652) drop for moments. MHF ends the marker on death, area change or a broken part (life prm14 = 9000 ticks) | em_alive: still in the monster manager, not small, HP > 0 (S: area / part ends not ported) |
| 1 | no shot / marker look | stand-ins only (GS's flash, never seen in tests 6-15) | MHF's fc5:e on the marker, fc5:b on the shot, fc5:a at 100 / 300 / 600 / 1000 / 1500 of its flight (msfxposts 'MARKER' / 'SHOT' / 'TRAIL'): posted at the point (post_at), moved every tick (0x32a45c), stopped at the end (0x32a400). Trail rotation (pitch, yaw, 0) in GU's beam order: S. Reticle, aim camera, hand piece still open |
| 2 | attraction janky, follow-up too high / slow | the log: Y in the flight -> 59, which climbs 111-124 cm before its slam. That is MHF's 59 (f0: drive up 15 / tick x 0.97^n, gravity 4 x 0.1 t; f54: the slam, gravity 60, drive -81). MHF's attraction update 0x10332dd0 runs only in 58 / 61 / 62 / 68 / 71 / 72 (its caller 0x103339d0), so 59 drops the flight's motion, as here. The flight re-targets the marker each tick (S; MHF's direction is set at the start) | none (no confirmed cause); question to the maintainer |
| 3 | RB + A rolls while moving | every roll came with the gauge under one bar (1200, 0): R1 + special(A) costs a bar (condition 1, MHF), so GU's roll took the press; with 2000 it gave 106 | with our command set under R, GU's moving roll ids (4 / 24 / 38) are cleared too (they could take it, S). Under one bar GU still rolls: question (MHF's) |
| 4 | no Y + B after a Guard Counter | both counters: Y + B at f32-f50 (combo 0x40, kept for 154 at f68), then B and Y 8 ms apart at f43 / f62: GU combo 0x42 = tri and the chord, tri's priority 20 (-> 16, f46-f76) beat the chord's 0 -> 16. MHF reads tri + circle as its own key action (0xe1 / 0xdc, 0x10336c70) and gives tri the higher priority inside the chord's go window, so a chord press is not tri there (S: the key layer 0x108f7010 not traced) | inputs 2 / 3 / 7 / 8 (tri, circle, R1 + tri / circle) not when the press is the chord (combo 0x40) |
| 5 | RB moves: no i-frames | the log: 7 ticks granted in each RB move (11, 106, 107, 108, 135); the hits came at motion frames 14 and 18 (the window is 0-14). MHF decrements +0x4ee once per tick (0x10a72ed0, 0x10ad23f0): 7 ticks = 14/60 s, as here; Evasion +1 / +2 = 12 / 17 | none: MHF's value (question: was the maintainer's MHF set on Evasion?) |
| 7 | no MHF effect | posts returned handles, nothing drew: the 41 EFLs and their atlas came after effect\pel\pl\w05_000 in w05.arc. GU's arcs always hold a PEL's EFLs before it (781 / 781 references) and resolve paths while loading (test 1 had the same with a command list): S, the PEL loader not traced | the atlas, then the EFLs, then the PEL (w05.arc entries 91 / 93-136 / 137) |

## Test 16 (built and installed 2026-11-04)
Build: `GOG_DEFINES=MS_SLICE`. Play, then close the game; the log answers the rest. Xbox letters.
1. Any MHF effect at all (step 7 of test 15: guard, Triple Strike, attraction, Magnetic Shock...). If a quest with
   the Magnet Spike crashes on load: say so (MS_MHF_FX=0 for msbuild.py leaves the effects out).
2. RT + B at a large monster: the shot's look and its trail; the marker's look on the hit part, following it;
   several attractions on one marker (it should last).
3. Guard Counter (RB + RT) into an attack, then Y + B pressed together (154 comes at MHF's frame 68, about 0.6 s
   after the counter's start).
4. RB + A while moving, with at least one gauge bar.
Ask only about visuals: the effects' size (too big / small = one global factor), colour, placement (hand / ahead /
ground); the marker and shot looks.

