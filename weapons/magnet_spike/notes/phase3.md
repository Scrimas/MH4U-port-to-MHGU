# Magnet Spike Phase 3: full moveset and mechanics

Goal: every MHF Magnet Spike action, mechanic and effect on GU's class 5 (Guild style, shared Hunter Arts), then
the weapons and the smithy (phases 4-5 folded in: a handful of endgame weapons, forgeable). Branch magnet-spike,
switch MS_SLICE (test builds only).

## Status (2026-10-30)
| part | state |
|---|---|
| actions | every MHF action that plays Magnet Spike motions (160; msbuild ACTIONS), steps / cancels / events from mhfdat |
| inputs | one class id per (MHF input, condition) pair (21 pairs, x2 modes); conditions run in the translator |
| hits | 142 attack / special entries + magnetised copies (MV x 1.1); code specials #5-#7, #10 |
| gauge, Magnetise | regen, on-hit gain, bar costs, Magnetise charge / on / lockout (log only: no HUD yet) |
| guard | Guard Counter 14 -> 207 -> 57 / 76 / 77, Impact guard 112 -> 113 -> 114 / 115 (GU guard patched for class 5) |
| charge | Triple Strike 34 -> 208 -> 35 / 36, overcharge release |
| marker / attraction / repulsion | marker stand-in (nearest monster in front), flight phases, falling attacks, approach cancel |
| pin | leap -> pin on hit -> QTE (X / A mash) -> finisher / pin over; the hunter rides the monster |
| HUD | the Charge Blade's phial widget (class 5's HUD case -> CB's, hook 0x646560): 5 phials = gauge bars, colour = mode, first element = Magnetise (ready 2 / on 1 / lockout 5, S) |
| effects, sounds | not yet (GS's effect / sound lists as placeholders) |
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
charge threshold 45 ticks; the QTE (hold 60 / cap 90, 70 points); drives at constant speed (curves not run); every
MHF camera-shake preset = GU 0xf; the monster is not held during the pin; Guard skills don't extend the windows;
R1 + evade = R + Y.

## Test 1 (Phase 3; save backup dump/save_backups/2026-10-29_before_magnet_spike)
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
Report: crashes, stuck actions, which aim button worked, what looked wrong.
