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

## Test 16 (built 2026-11-04, commit dc1c514; played 2026-11-04)
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

### Test 16 results and fixes
Log: dump/mhf/test_logs/ms_test16_Ryujinx_1.3.3_2026-11-04_16-39-33.log. The maintainer: RB + A and the Guard
Counter's Y + B fixed; no shot / marker visual, reticle or hand piece yet; the attraction still janky. Effects now
draw, but every one is the same huge white sphere (about 10x the hunter), some stay at a fixed point, even through an
area change; none on RB moves, plain Y / B attacks or the Guard Counter follow-ups.

| # | issue | cause (C unless marked) | change (test 17) |
|---|---|---|---|
| 7 | every effect = one huge sphere | GU's billboard quad comes from the EAN frame's texels (0xa7e768: corners from frame w / h; GU's hunter billboards in w00.arc: size 0.2-1.25 on 256-px frames). Ours were cm (R x scale: 50-2000 on 32-128-px cells), 16-64x too big, so the camera sat inside each sprite and they all looked alike (S) | size = cm / (cell px / 2) (G: 1 cm per texel at size 1, not traced to the shader); Polygon width / height = the cell's half size, no width curves (G) |
| 7 | spheres stay, through area changes | only the marker / shot effects (fc5:e / fc5:b, particles 631-848 s) live long: the stop call 0x32a400(eff, 0) only ends the emission (em089_efx.c kills with 1), and their once-emitted world-space particles do not follow 0x32a45c | kill (mode 1); the marker / shot effect re-posted at its point every MHF tick, the previous one killed (S: its UV scroll restarts); the marker also ends when its monster's area (+0x1054) is not the hunter's (MHF) |
| 7 | none on RB moves, Y / B, GC follow-ups | MHF posts no code effect there (notes/effect-posts.md); no action uses event 15. Their look comes from another MHF source (S: the weapon trail / per-motion data, not mapped) | none yet: next study |

## Test 17 (built and installed 2026-11-04)
1. Effects at all the moments of test 15 step 7: their size next to MHF's (still one global factor if wrong),
   colour, placement; no sphere left behind (also after an area change).
2. RT + B at a monster: the marker's look on it, following it; the shot's look.


### Test 17 results and fixes
Log: dump/mhf/test_logs/ms_test17_Ryujinx_1.3.3_2026-11-04_16-58-35.log. The maintainer: better, but still too
bright / the wrong colour ("ours wash to white", a different hue); plain Y / B attacks show only ground smoke in MHF,
the Y + B finisher (as the Guard Counter follow-up) an effect on the weapon and mostly where it hits the ground; RB +
Y / B / X / A have a swing trail (on the weapon, and on the hunter for the side moves) and an initial glow; the
attraction and repulsion have effects too (reference video, scratchpad frame sheets).

| # | issue | cause (C unless marked) | change (test 18) |
|---|---|---|---|
| 1 | washed to white | every unit was additive; MHF's E draw byte +0x15 picks it: 1 additive, 0 / 2 alpha blend (assets.md "Blend") | per draw byte (mhffx2gu) |
| 2 | no RB / Y / B / finisher effects | MHF's per-motion key table (mhfdat 0x618, effect-posts.md "Per-motion keys"): 208 effect keys on 53 motions, fixed / attached / ground | all ported as motion rows (fix / att / gnd) |
| 3 | still particles where MHF's move | position curves and F emitters were not converted | GU move kind 5 paths (gu-efl-move.md; 880 entries) |
| 4 | attraction janky, too high | target, steering, budget and height band not MHF's (mechanics.md "Attraction") | MHF's start / update / steering / budget / band |
| 5 | no Magnetise / attraction / repulsion looks | MS tasks 0xb-0xe posts (effect-posts.md) | magz_look, att_carriers, rep_posts |
| 6 | no aim camera, reticle or hand piece | not ported | GU's gunner aim view (camera + scope HUD, ms.h MS_AIM_BYTE); the hand piece as a model (msgun.py) |

## Test 18 (built and installed 2026-11-05)
Deviations in this build (S): the aim view is GU's (its over-the-shoulder offsets and look speed, GU's crosshair:
MHF's red / blue / white reticle frames are not drawn); the hand piece's part transforms are read as T R S (S); F
particles' bounces and child effects, UV modes 1 / 7 (7 particles) and the fc5:2 beam length scale are not ported.
1. Plain Y and B: ground smoke only. Y + B finisher: the weapon effect and the ground impact.
2. RB + Y / B / X / A: the trails and the start glow; colours next to MHF's (no white wash).
3. Hold RT (aim): the camera goes over the shoulder, a crosshair in the screen centre; release: back to normal.
4. RT + B (shot): the hand piece in the left hand for about half a second, the shot and the marker.
5. RT + Y from 14-40 m to the marker (attraction) and RT + A under 14 m (repulsion): the hunter's path and height,
   and their effects.
6. Magnetise: its flash, spots and pulses.
Play, then close the game; the log answers the rest. Ask only about visuals: colours and look next to MHF's (the
reference video), the camera and the crosshair, the hand piece's size and place.

### Test 18 results and fixes
Log: dump/mhf/test_logs/test18.log. The maintainer: exactly as test 17, no regression but no progression: none of
the new effects drew (the old ones unchanged). Every post that should fire fired with a handle (the log); the arc
order, the PEL (561 / 512 records, no count cap in GU's loader 0x322fd4, records well formed) and the blend table
(AppShaderPackage.mfx: 0 BSBlendAddAlpha, 1 BSBlendBlendAlpha) were ruled out.

| # | issue | cause (C unless marked) | change (test 19) |
|---|---|---|---|
| 1 | no new effect drew | mhffx2gu baked every particle mesh into a sprite by its x / y projection, assuming MHF's meshes are flat there. 404 / 942 particles are not: XZ / YZ planes (93, 121, 42, 401, 335, 334: empty cells) and 3-D arcs, rings, domes (291, 337, 340, 53, 379, 61, 143, 329: slivers). 14 of the 81 effects had no flat particle; the new per-motion keys are mostly these | world-oriented 3-D meshes (266) -> GU Model units on the mesh as a model (mhfmodel.py: MOD + w00 cm010_000 material + its texture; mhffx2gu.model_unit from w04 cm123_041 entry 0, whole). Camera-facing ones (138 + the flat ones): the spawn rotation x / y and the scale y / z relative to x baked before the front view, as MHF's matrix order (0x113ce4d0: scale x rotation, then the camera) |
| 2 | no hand piece | the unit was em001_00_500 entry 1 cut at 0x140, its +0x134 value-block offset (0x170, 0xa6b824 via 0xa99f40) pointing past the cut; vertex colour (0, 0, 0, 255) where GU's weapon-effect models store 7f grey + alpha; v unflipped | msgun on mhfmodel and the whole Model template |
| 3 | plain Y / B: little | MHF has few keys there: action 1's motion 1405 two (f40 posted in the log), action 3's 1401 one at f58 (the log's attack was cancelled at f13), 4 / 48 none | none (MHF's) |

Still near-empty sprites (10 / 86), as MHF draws them: camera-facing meshes seen edge-on (93 / 42 in the XZ plane
with no rotation, 26 turned 90 degrees about y) and thin-line textures (379, 31).

## Test 19 (built and installed 2026-11-05)
Deviations in this build (S): the 3-D meshes' UV scroll (MHF modes 2-6 on the swing arcs) is not animated (GU's
model UV layers, unit +0x136 / +0x138, not decoded far enough); GU's Euler order for the Model rotation is assumed
X, Y, Z as MHF's; camera-facing sprites bake the base rotation x / y (their random range not); the effect-model
vertex neutral 0x7f is Capcom's convention (S); plus test 18's (aim view, reticle frames, F bounces, UV modes 1 / 7,
the beam length scale).
1. RB + Y / B / X / A: the swing trails (weapon and, on the side moves, the hunter) and the start glow.
2. Y + B finisher (and the Guard Counter's follow-up): the weapon effect and the ground impact.
3. Plain Y / B (let a Y combo play out): the ground smoke.
4. RT + B: the hand piece in the left hand for about half a second, the shot and the marker.
5. RT + Y from 14-40 m (attraction), RT + A under 14 m (repulsion): their effects; Magnetise: flash, spots, pulses.
Play, then close the game; the log answers the rest. Ask only about visuals: which effects show, their shape, size,
orientation and colour next to MHF's (the reference video).

### Test 19 results and fixes
Log: dump/mhf/test_logs/test19.log. The maintainer: no effect at all, old ones included (Guard Counter, attraction,
repulsion). Every post returned a handle; billboard-only effects failed too (3096 = ms_fc5_014, 7 Billboards,
unchanged since test 18 but for its atlas index), so not the Model units. The build's global change: the atlas grew to
1024 x 2048 RGBA8 = 8 MB (86 sprites), plus 8 RGBA8 model textures; w05.arc unpacked 27.0 MB (test 18 about 20.7 MB,
GU's largest weapon arc w13 18.7 MB, GU's largest weapon-arc file 1.2 MB). S: the class resource budget is not traced.

| # | issue | cause | change (test 20) |
|---|---|---|---|
| 1 | no effect at all | the 8 MB atlas / 27 MB arc (S) | the atlas and the model textures in BC3 (2 MB + 64 KB each, GU's effect format): w05.arc 19.7 MB unpacked, largest file the motions (2.3 MB) |

## Test 20 (built and installed 2026-11-05)
Test 19's checklist and deviations unchanged; the sprites are BC3 (4 x 4 blocks: soft edges on the smallest
sprites, S).

### Test 20 results and fixes
Log: dump/mhf/test_logs/test20.log. The maintainer: the old effects are back (Guard Counter, attraction, repulsion),
still the wrong hue; nothing new (test 17's state): no Model unit shows. Ruled out statically: our MODs parse like
Capcom's cm010_000 (tools/mod.py) and match efl4u2gu's in-game-proven effect MODs; the element ground masks are -1;
the colour keys are RGBA (the RB-move keys read 17-22 degrees = MHF's orange in the reference video, swapped they
would be blue); the MHF images and vertex colours decode full-range; GU's 208 effect textures are RGBA8 (no sRGB).
Found (C): an effect's build (0x9bda64) fails whole when one generator's ready check fails (the Model's, 0xa94b48:
its model at runtime record +0x18, every material checked); the gun's EFL tails (copied from cm123_041) held offsets
into cm123_041's blocks.

| # | issue | change (test 21) |
|---|---|---|
| 1 | no Model unit shows | the model material = efl4u2gu's efx_blend (em024 cm101_000), the one its converted effect models drew with (S); a log of the first 30 motion-row effects' build state (ms_act.c fxw_*: flags, each generator's class, draw mode, model / EAN, live particles) |
| 2 | gun | its EFL head / tails from em001_00_500 (no foreign offsets) |
| 3 | hue | not found statically: needs a screenshot next to the video |

## Test 21 (built and installed 2026-11-05)
Test 19's steps. The log now shows whether each posted effect built and whether its models resolved.

### Test 21 static follow-up (2026-11-11)
Cause (C, gu-efl-units.md "Unit block, Model (type 5)"): every Model unit kept cm123_041 entry 0's +0x100 = frame 1
and its scene-model bit (+0x1a bit 0). In that mode GU draws the particle as a model unit showing only mesh j == frame
for j < the mesh count (0xa99a38, 0xa94c10); our MODs have one mesh (group 0), so nothing was shown (tests 18-20).
Ruled out statically: model / MRL / textures resolve in w05.arc before their EFLs, every material name is in its
MRL with the effect class, MOD version 0xd4, kind-5 curves present. Change: mhffx2gu.model_frame (frame 0, no range)
on every MHF Model unit and the gun; mhfmodel merges a model's parts into one mesh (the gun's three); effcheck.py
replays the conditions and stops msbuild on a problem (gen/report.txt). The installed test 21 build is stale: rebuild
and reinstall before test 21. Then (coordinator's decision) the units moved to GU's effect draw, as efl4u2gu's
models and 10795 / 11359 GU Model units: mhffx2gu.model_effect_mode clears +0x1a bit 0 and the template's
scene-mode values (+8 = 0, +0x10c = 0: its bits 20-23 and the +0x10e bit 4 flag are 0 in effect-mode GU units);
blend = MHF's draw byte in unit byte 3 (S: the effect path takes it, gu-efl-units.md "Blend"); materials now pass
the ready check's class test (effcheck: 0 problems; also 0 on GU's w00 / w04 / w13 and efl4u2gu's em089-091 arcs).
Log (ms_act.c fxw_*, first 30 motion-row posts, 2 and 12 ticks after): `msport: fxwatch ID tT eff E flags F built B
res R gens G` (flags +0xf0 bit 0x2000000 = build failed, built +0x118 bit 0x1000000 = built) and per generator
`msport: fxwatch ID  gen K vt V mode M ed D rec R rflags L ean A model O part P live N`: vt 0x17907fc = Model, mode
= gen +0x46 (5 / 0x1e effect draw, 0x37 scene model), ed bit 2 = scene mode, rflags = record +0 (0x10 model / 8 EAN
not found, 0x2000 / 0x1000 empty path), model = the rModel, live = particles alive. The test must still show the
look: MHF's additive meshes add (not alpha), sizes, orientation (Euler order G), and the gun's three parts.

### Test 21 static follow-up (gameplay, 2026-11-11)
The maintainer's test-15 answers, traced in MHF (mechanics.md "Invincibility", "Conditions and inputs", "Marker,
attraction, repulsion"). Changed (ms_act.c): the attraction's fall now keeps MHF's 0.97^N momentum from the flight's
first tick (0x103327a0; the port had restarted it at 90 / tick: about twice the speed, landing 4-8 m past MHF's spot
and up to 50 cm higher in an offline replay), the steering gate is the horizontal distance (0x10332ae0) and the start
pitch is clamped to 25 deg up / 10 deg down (0x103328d0). New log line, once per attraction at its end: `msport:
attraction end (landed | action change, action A): marker y M, target y T, start y Y0, peak y P, end y E, D cm to
the target horizontally, N ticks, phase K` (target = marker + 100; phase 3 = falling). Not changed: the RB-move
i-frames (MHF's own 7 ticks, 17 = with Evasion +2, C), the falling attacks' carried-over i-frames (MHF event 9,
open: S) and RB + A while moving (MHF rolls at any gauge; the port's 106 with a bar, and GU's roll on RB + A
standing under one bar where MHF does nothing, are kept by the maintainer's decision of 2026-11-11: deliberate
deviations). The maintainer's answers behind this (2026-11-11): the RT + Y attraction itself went too high (not the
Y follow-up); MHF's RB + A under one bar not remembered; the MHF set's Evasion not known, but the weapon is known
for long invincibility on RT + Y and the RB moves (to be verified). Look at in the test: RT + Y at a standing monster's body and at its head, no follow-up: does the
hunter now land at the monster instead of past it, and how high is the arc next to MHF's (the log line gives the
numbers); then RT + Y, Y.

Rebuilt and installed 2026-11-11 from commit cf80391 (MS_SLICE, the maintainer's Ryujinx mods folder): test 21 =
test 19's steps plus the two attraction checks above; not played yet.

### Test 21 results and fixes
Log: dump/mhf/test_logs/test21.log (commit cf80391; 33 Ryujinx cheats on, among them Instant Kill, Invincible, Inf HP,
Attack Rate x99, Charge Blade Phials Max / Red Charged). The maintainer: (1) RB + Y / B / X / A: some effects show,
"definitely wrong"; (2) the Y + B finisher triggers now, wrong effects; (3) plain Y / B ground smoke right; (4) RT +
B: the hand piece shows, never clear and at the wrong place, no reticle, no projectile; (5) / (6) the attraction
flight and RT + Y, Y fixed; (7) RT + A and RT + Y show no effect (test 20 showed the old ones). Magnetise not tried
(charged: "Cutting Magnetise ready", never switched on).

| # | issue | cause (C unless marked) | change (test 22) |
|---|---|---|---|
| 1 | RB moves: wrong effects | the ids are MHF's: 11 / 135 fc5:40 at f62 of 1045 (the unmagnetised branch), 107 / 108 the mhfdat keys of 1493 / 1494, at MHF's frames and bones. Extra: GS's swing crescent on 1045 (msfx arcs, effect-posts.md "Port vs MHF"). The rest is the look (conversion), row 4 and row 10 | GS's crescents no longer posted with the MHF effects on (msbuild; the swing sounds stay) |
| 2 | finisher: wrong effects | 152 / 154 without Magnetise: MHF posts nothing (1406 / 1446 / 1035: M-gated code posts, no keys); the port posts nothing MHF either, so what shows is GS's crescent on 1035. 155: 1418's keys fae:17 / faf:0, posted | crescent dropped (row 1); question: was the reference video's finisher Magnetised? |
| 3 | hand piece | posted on joint 12 at f6 (event 17), MHF's offset; msgun assembled its three parts wrongly. A Model-only effect that shows: effect-mode Model units can build (S) | msgun fixed: fxplace 0.0 cm against MHF's 0x1004f7b0 |
| 4 | no attraction / repulsion effect | the posts are those of test 20 (same ids and frames in both logs); the effect files changed (ebe2340): MHF Model units in GU's effect draw now run the Model ready check 0xa94b48, which scene mode skipped (generator +0xed bit 2), and one failing generator fails the whole effect (0x9bda64). Every attraction / repulsion effect but the hand flashes 3073 / 3074 holds Model units (3078, 3084, 3089, 3332, carriers 3416 / 3417 / 3482 / 3483), and so do the mixed RB-move ones (3343, 3349) and the Guard Counter's 3092. S: their material fails the class test 0xb91ef0 (effcheck: passes; the class is a runtime DTI, not proven) | fxwatch made real (row 7) to show it; carriers kept alive (row 5); one-build A/B on the draw mode (row 11) |
| 5 | no projectile (and no marker look since test 17) | the shot (fc5:b, 3486) and the marker (fc5:e, 3480) were killed and re-posted every update / tick: the proxy creates its effect in its own start step and the effect builds on its first update, so the kill came first (S; test 16's moved version showed them) | posted once, moved every update (0x32a45c), re-posted when ended or (marker) moved over 150 cm; killed at the end (fx_follow) |
| 5 | no reticle, no aim camera | GU's 0x29fb8c (end of the player update, after slot 139) clears the aim byte +0x2716 and +0x2714 every update for a drawn non-bowgun (0x29fe90): the quest camera ended its aim in the first frame and the scope HUD (cUIOQuestScope, made for every class; the Charge Blade redirect does not touch it) read 0. Mode 0 would also have followed the turn target +0x14a0 (no look) | slot 45 sets the byte / pitch / camera aim again after 0x29fb8c; MHF's look (0x240 yaw / 0x160 pitch per MHF tick, digital) on GU's right stick through GU's aim reader 0x27d5c4 and invert options; slot 260 writes it into the camera's yaw / pitch, the hunter does not turn. Deviations: pitch starts level, clamp ±0xd1c (G: sense), MHF's reticle (2026-11-11, mechanics.md "MHF's reticle"): sprite 0xb6 = one 46 x 46 cell of mhf_90c entry 4 tinted blue / red / white; GU's scope widget shows element 0 (tree "scope") for class 5, whose TexS_scope quads (HD_hud01 UV (0, 32)-(240, 272), mirrored about the centre) carry it: mshud.py writes three HD_hud01 copies (mh4uport\ms_reticle0-2, 512 KB each) and the module points the scope .gui's HD_hud01 entry at the frame's copy while the local class-5 hunter aims (hook 0x61e1f4); the copies are empty but for the reticle, so GU's ring, arrows, bars and gauges vanish while aiming |
| 6 | 3 shots missed | shot 1 flew away from the monster (direction opposite to shot 2's: aimed or camera, G); shot 4 pitched 14 deg down into the ground (4 ticks); shot 6 life over (750 m); shots 3 / 5 were replaced in flight by the next one (no end logged). Shot 2's marker ended the same tick: the area test (monster +0x1054 != the hunter's), by elimination (mechanics.md). No cheat explains these (the shot deals no damage) | logs: closest pass to a hurt volume, every monster's em_ok gates and distance to the line, the camera at the shot, replaced shots, why a marker ended |
| 7 | logs | fxwatch read the proxy as the effect (effect-posts.md "GU's post handle"); carrier lines printed 0 for unkept handles and a 32-bit mask hid the attraction's beam / rail (32 / 34 folded onto 0 / 2); GS's marker flash ran beside MHF's every other update | fxwatch follows proxy -> effect -> generators with vtable / PEL-id checks ("invalid" otherwise), for every post kind (2 per PEL id, 48 ids); carriers logged with their PEL and first handle; the GS flash only without MHF effects |
| 8 | attraction timing | fc5:7 at the marker came at the start (MHF f10); fc5:3 / fc5:4 both on the first update (the 'act' rows count from frame 0, 1472 starts at f8: MHF f10 / f14) | fc5:7 1 tick after the start; the 'act' rows now add the first step's start frame (msbuild.fx_post_tables) |
| 9 | Model placement | GU draws a Model particle in the emitter's frame = the PEL record's T R x the joint's full matrix (gu-efl-units.md "Model transform") | tools/fxplace.py replays both sides on the built arc: 253 Model units, median 0.00 / max 1.97 cm, 0.00 deg (posts without rotation) |
| 10 | swing effects: "can't tell direction" (part) | MHF's per-motion keys carry a follow mode d (0x1099a720 / 0x1099ae30, C; msfxposts.key_mode). Our 124 attached keys (kind 7) all use d 0 = the bone's full rotation, so the 'att' PEL on the joint is right (the old "treated as full follow" deviation did not apply). But 20 fixed keys (kind 6: fae:c, fae:d, faf:0, faf:2 = plain Y's smoke, 107 / 108 / 1418's) use d 3 = (0, the hunter's yaw at the key, 0), which the port posted with the joint's full rotation; 2 ground keys use d 4 = yaw + 90 deg | modes 'fixyaw' / 'fixyaw90' / 'gnd90' (ms_act.c fx_fixed 3 / 4 / 5). fxplace, hunter yaw 30 deg, joint turned Rx 40 Rz 25 against it, 12 Model units: before median 257.8 / max 299.5 cm, after median 0.0 / max 23.0 cm (the rest = MHF's Euler sum against GU's matrix product, as the --yaw check) |
| 11 | which draw mode builds | statics cannot settle why the mixed effects vanished (row 4): the Model-only plain-Y smoke (fae:b / c / d) and the gun showed in effect mode. Other ways a build fails (C, effect-posts.md "GU's post handle"): a generator allocation, the effect's work block, a slot init | test-22 split (mhffx2gu.SCENE_TEST22, gen/report.txt): the Model units of fc5:1 / 2 / 5 / 7 / 0x38 / 0x4d / 0x4e (attraction, repulsion, Guard Counter: 45 units) in SCENE mode, frame 0; every other MHF Model unit in effect mode; fxwatch prints scene / effect per effect and which build step stopped |
| 12 | GS stand-ins in the module | with the MHF effects on (gen/ms_data.inc MS_FXQ_ON 1, MS_NFXPOSTS 251) every GS stand-in post sits in a constant-false branch: marker flash (flash_at; MHF: fc5:e on the marker, fc5:b / fc5:a for the shot), Magnetise aura (MHF task 0xd / 0xe: fc6:10, fc5:55-58), guard flash (MHF fc5:46 / 47 / 15; Impact guard fc5:16, fc4:2, fc5:15), Magnetise-on flash (fc6:10 at t18 / 17), Magnetic Shock (task 0xf / 0x10 spot posts), Triple Strike charged (fc6:11 + fc5:15 x 3) | the marker flash's branch now tests MS_FXQ_ON itself (it ran beside MHF's in test 21) |

## Test 22 (built 2026-11-11: msbuild.py + `GOG_DEFINES=MS_SLICE` module; not installed yet)
In this build: rows 1-12 above (carriers kept alive, real fxwatch, no GS crescents, follow modes, the gun fixed, the
draw-mode split); MHF's reticle on the scope HUD (step 4). Model units scroll their UVs as MHF (132 / 266, unit +0x134);
look for moving swing-arc textures, half brightness (vertex x2, unit +0x20 = 2.0 fix) and arcs hiding each other
(DSZTestWrite). Before playing, switch off these Ryujinx cheats: Instant Kill, Attack Rate x99, Invincible, Inf HP
(markers, guards and Magnetise need a live monster and real hits), Charge Blade Phials Max and Charge Blade Red
Charged (the magnet HUD is the Charge Blade's phial widget). Play, then close the game; the log answers the rest.
Xbox letters.
1. Plain Y combo (let it play out): the ground smoke, and its direction along the hunter's facing.
2. RB + Y, RB + B, RB + X, RB + A, once each, standing: the swing effects and which way they face.
3. Y combo into Y + B (the finisher): no white crescent any more; what shows.
4. Hold RT (aim): the camera goes over the shoulder, and in the screen centre MHF's reticle (four corner brackets
   around a small diamond, about a fifteenth of the screen height) is the only crosshair: GU's faint ring, four
   small red arrows and side bars are gone while aiming. The right stick turns the view (left / right and
   up / down; the hunter does not turn; the left stick still walks). With no marker the reticle is white. Aim at a
   large monster's body, standing still, press B; three shots, one at a time. Once a shot sticks (the marker), the
   reticle turns blue within 14 m of the marker (repulsion possible), red at 14-40 m (attraction possible), white
   beyond 40 m: walk away and back to see it change. Then release RT: the reticle goes, the normal camera comes back
   looking the same way. Say: did the reticle show, its colours and size, any GU crosshair art left while aiming, did
   the right stick move the view the right way round (up = up), was it too fast or slow, did the projectile fly to
   the reticle, the marker's look on the part.
5. RT + Y from 14-40 m to the marker (attraction), no follow-up: its effects (hand flashes, beam, rail, landing).
6. RT + A under 14 m (repulsion): its effects.
7. RB + RT into a monster attack (Guard Counter), then Y + B: the counter's effects.
8. Magnetise: hit the monster in one mode (stay in Cutting) until it is ready (charge MV x 0.8 per hit to 1000:
   20-40 hits; the log says "Cutting Magnetise ready"; the HUD's first phial changes, S), then hold RB and press
   Back (View); then RB + Y once: the flash, spots and pulses.
Ask only about visuals: for each step, did an effect show, where, which way it faced.
What the draw-mode split means (fxwatch "scene" count per effect; steps 5-7 = the scene-mode set, 2 / 3 / 8 the
effect-mode mixed ones, 1 effect-mode Model only):
- scene set built and seen, effect-mode mixed set "failed (0x2000000)" with all its generators, block and slots:
  the effect-mode Model ready check (0xa94b48, material class) -> scene mode for every MHF Model unit, or fix the
  material.
- both sets built (built, live particles) but one not seen: a draw-time problem (blend, layer, alpha), not the build.
- a set "failed" with gens below the entries or block 0: a generator / work-block allocation (budget), not the mode.
- the scene set fails too: the mode is not the cause; compare with step 1's lines (effect mode, seen in test 21).
New log lines: `msport: fxwatch ID tT proxy H unit U state S step K kind N efl R (flags F) effects C`; per effect
`msport: fxwatch ID  effect I E unit U built|not built[, failed (0x2000000)][, no resource / init (0x4000000)] res R
(N entries): gens G, block B, slots S` and `msport: fxwatch ID   N gens: Model M (scene S, live L), Billboard ...`
(a generator with record flags gets its own line), or `... invalid: REASON`; `msport: mhf carrier K (N rows, PEL P)
at X Y Z: H`; `msport: mhf carrier PEL P stopped (WHY) after N ticks, alive A`; `msport: aim view on (camera mode M, manager H, quest camera C, yaw Y deg)`; `msport: aim tick: byte B cam aim A mode M settled S yaw Y deg pitch P deg (+0x2714 R)` (the first 10 updates of each aim; byte 1 and cam aim 1 = the fix holds); `msport: aim reticle frame F (WHAT), marker D cm` (on every change while aiming); `msport: reticle textures A B C` (three non-zero = loaded); `msport: scope reticle entry E: MHF frame F` / `... back to HD_hud01` (the first 40 swaps); `msport: scope reticle: HD_hud01 WxH, ours WxH: GU's crosshair kept` (no swap: the HD UI pack's HD_hud01 is not the size the build used); `msport: marker shot: camera now
...`, `... closest pass ...`, `... monster I ... ok ...`, `msport: marker shot replaced in flight`; `msport: marker
gone (..., in manager, small, hp, area, hunter area)`; `msport: mhf effect ... mode 3` = a hunter-yaw key.
