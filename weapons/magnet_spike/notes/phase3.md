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
