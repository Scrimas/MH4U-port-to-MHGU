# Tidal Najarala port: plan (from 2026-11-06)

Source: MH4U em093 (class uEm023, shared with Najarala em023 and Apex Tidal Najarala em120). Target: GU Najarala's class
uEm068_00, **variant 1** (GU ID 0x144, arc `nativeNX/arc/enemy/em068_01.arc`). Process: notes/porting-guide.md, closest
models: monsters/tigerstripe_zamtrios (a 4U subspecies run by GU's own class), monsters/stygian_zinogre (same, with ported
handlers and shells). Built on the save store core + Monoblos (folder Workspace\MH4U-najarala, branch wip/tidal-najarala,
local base commit c248e6b = the uncommitted MH4U-savestore work). On the README's roadmap. C = confirmed in code / data,
S = strong, G = guess.

## Phase 0: identification (C)
- 4U emName: 23 Najarala, 93 Tidal Najarala, 120 Tidal Najarala again (Apex, as 119 is Apex Diablos). 4U class: only uEm023
  (DTI 0x10b6540, size 36328, vtable 0xe66a9c, slot 44 0x7693c8, slot 39 0x761768, slot 40 0x761ab8, slot 46 0x769bf8, slot 47
  0x76ace4, slot 48 0x76a010, slot 50 0x76b4e4, slot 51 0x76b624, slot 66 0x76c000, slot 77 0x76bac8).
- GU: Najarala = ID 0x44, registry index 57, arc em068_00 only (0x144 free). Class uEm068_00: DTI 0x1851418, new 0x4d364, size
  0xcb40, ctor 0xf7c70c, vptr 0x17e6250: slot 118 0xf7c890, 119 0xf7de98, 125 0xf8903c, 127 0xf7cab0, 129 0xf7ced8, 130
  0xf8ab20, 132 0xf89afc, 133 0xf89e90, 170 0xf894c4, 247 0xf7e634.
- GU category dispatchers: 0 f7e700, 1 f7f230, 2 f826e8, 6 f83184, 7 f868b8, 8 f86d08, 10 f86eec, 11 f87f90, 12 f82c3c, 13 f88938, 16
  f88a78. No category 3.

## Assets, 4U vs GU (C: md5 per arc entry, frames per motion slot)
- em093.arc shares with em023.arc: AI table `enemy\em023\data\em023_cmd`, camera `e023_cam`, sound call `em023`, bank 3 (under the
  name em093_3, same bytes). Own: model (+ tail), 4 textures, effect base, 14 EFLs, MEF em093_0 / _1, sound bank + 28 waves
  (`em093_fx_shell_water_*`, `em093_vo_*`), banks em093_0, _2, _4. em120.arc ships em093's banks, its own `em120_cmd`.
- Motions: GU em068_00 banks 0 / 2 / 3 = 4U em023's (65 / 69 / 49 animations, same frames in every slot). em093 bank 0 lacks em023's
  138 139, bank 2 lacks 61 64-68 70-74, shared slots have equal frames. em093 bank 4 = 2 animations, slots 2 and 3 (0x402, 0x403);
  GU has no bank 4 but its handler f861b0 still asks for 0x402 / 0x403 (= 4U 0x765810, 7/48-51 62-65).

## AI table (C)
em023_cmd has 23 groups (24, 83, 3, 0, 1, 2, 1, 0, 2, 1, 3, 0, 1, 1, 1, 0, 1, 0, 4, 0, 1, 1, 0), op-0x46 cases: 23 x26, 93 x3, 120 x3. Natives
for em 93: 104, closure with chains 124. Only for 93: 7/54 7/60 7/61. Only for 23: 2/68-71, 7/22 7/27 7/41 7/42. em120_cmd has the
same natives as case 93.

## Handlers, 4U vs GU (C for the pairing: both dispatchers emulated under unicorn; scratch tn_closure.py, tn_pairs.py)
Every native but those below reaches a GU handler with the same parameters as 4U's (0x7625e0 <-> f8322c ...). GU kept 27 of the 4U
`em == 23` tests as `variant == 0` (this+0xb5f5). Missing in GU (dispatcher ends them): 1/23 1/26 1/27 (4U 0x761c1c r1 3 4 5), 1/24 (0x762300
r1 1), 1/25 (0x762490 r1 1). To read: 16/1..4 and 8/0 (no class handler either side).
Where GU's handler has fewer tests than 4U's (to read side by side): 7/3 7/60 7/61 (shells, below), 7/0, 7/20, 7/24, 7/25, 2/30-33.

## Shells: the water scales (C unless marked)
4U uShell015 (DTI 0x10bba1c, 760 B, vtable 0xe6d91c: slot 22 0xc680c8, tail 0xc68174, slot 23 0xc68cf0) = the scale shells. 4U keeps four of
them alive from spawn (slot 39, 0x761900 loop, poster 0x6620a4, handles at work +4..+0x10) and arms a free one through 0x7612e8(this, kind, count,
offset, [sp] param). 21 kinds (jump table 0xc68290). Em tests in the class: `+0x2da` = 2 for 93 / 120, else 0 (0xc681a8); blast uShell003 subtype on
detonation 64 (em 23) / 157 (em 93) / 199 (em 120) (0xc69600); 3 % item drop on detonation, not for em 23 (0xc698d8), a shiny drop; rank >= 5 and
em 23: +0x2ac = 2.
Najarala's handlers post kinds 19 / 20 where Tidal's post 9 / 10 with the handler's param (7/3 7/60 7/61: 0x7638a0 -> 0x7612e8) and 0 where Tidal's
post 9 (7/25: 0x765300).
GU: shell ids 0x125 uShellEm068_sp_01 (DTI 0x1894268, family em068_00_shell01, 3 kinds) and 0x126 uShellEm068_sp_36 (DTI 0x1894288, family
em068_00_shell36, 11 kinds, has its own bodydata). GU's f7d634(this, case, count) requests new shells: cases 0 / 1 / 2 = kinds (0, 1) (2, 3) (4, 5), 3 / 4 / 5 =
kinds 8 / 9 / 10; no variant test, so GU's variant 1 would fire Najarala's scales. So the water scales need work.

Built (tools/build_em068_01_arc.py, module/em068_01.c): sp_36 = the generic EmBase36 (slot 9 0x41a5fc, detonation 0x41af34 posting 0x125 kind 2 at 0x41b100), its kinds are
data: the def XFS is a ShellInfoList of N objects, each with ef / snd / hit / sh files. So her launches are 10 more kinds (21 instead of 11), nothing in code but the requests:

| Our kind | 4U launch | Action |
|---|---|---|
| 0, 1 (GU's) | (9, 0), (10, 0) at the default offset | 7/45, 7/47 (start hook) |
| 2, 3 (GU's) | 4U 11, 12 | 7/53, 7/55 (start hook) |
| 9, 10 (GU's kinds, data changed) | (9, 0), (10, 0) at OFF1 / OFF2 | 7/3 (GU's f7d634 cases 4, 5: no code) |
| 11, 12 | (9, 2), (10, 2) | 7/60 (fire hook) |
| 13, 14 | (9, 3), (10, 3) | 7/61 (fire hook) |
| 15, 16 | 4U 13, 14 | 7/57 (start hook) |
| 17, 18 | 4U 15, 16 | 7/59 (start hook) |
| 19, 20 | (9, 0), (10, 0) at OFF3 | 7/25 (fire hook) |

Hit data: scale hits = 4U attack record 5 (Tidal; Najarala 0). 4U's rage record 6 is not ported: GU's family has no rage variant either (a DEVIATION). Blast on detonation = 4U uShell003
record 157 in family shell01 entry 2 (flags 0x11, volume r350). Effects: 4U table 0x102a938, {group, element} by state +0x2f4, 8 per species: Najarala 0 flight em023_000, 2 planted em023_001, 4 rattle em023_014, 6 blast em023_002, 7 gone em023_004; Tidal 0 em093_030, 2 em093_031, 7 em093_004, 4 and 6 none (C). By a PEL list 2 repoint of
GU's paths (000 / 001 / 004; 012 and 002 on em093_004, they cannot come up for her). Masks: 1 = plain, 2 only with W+0x53a or the Apex bit (0xc68b90, +0x2f0 from 0x76145c; S: W+0x53a = frenzy), so GU's second flight post is off through her ef files (id -1). 7/24's blasts: GU's post with the variant byte at 0 between two mid hooks
(Tigerstripe's way). Slots: GU's handles at work +4..+0x10, same four as 4U's.
How a scale of hers ends (C): one hit, the jet's or a hunter's (4U +0x2ac = 1, 2 only for em 23 at G rank; GU's rank table is Najarala's, hers 1), or after 7200 frames. **She has no rattle blast**: all seven 0x769f80(this, 1, ..) signals are behind em == 23 in 4U and variant 0 in GU (list in em068_01_jet.c), and the scale detonates only on that signal, so blast 157 is for a Najarala beside her.
Scale model em093_tuning: GU's material of em068_00_001 with her texture. That is Capcom's conversion of its sibling em023_tuning (same material, 24 vertices). The first build used efx_solid with white vertices, which drew a flat white block (vertex RGB 127 = 1.0). Her other solid effect meshes (qe000_001) use efx_solid at RGB 127.
The kinds' files lie before the def in the arc: the def finds only what is loaded by then.

## The water jet (C unless marked; module/em068_01_jet.c has the 4U and GU details)
Found after the user's test of 0.1.1 ("no spit animation"). 7/48-51 and 7/62-65 play her own motions 0x402 / 0x403 on GU's f861b0, the twin of 4U's 0x765810: every turn and frame test is there, but GU cut the shot at frame 105 (4U 0x661f6c -> uShell012 subtypes 52 / 53) and the choice of a target among her scales (0x76c1bc), because GU's Najarala has neither. An earlier check of this handler compared attack indexes and species tests only; it has neither, so it passed (lesson in notes/porting-guide.md).
- What it is in 4U: a water jet from joint 13 at 37.5 per frame (46.9 enraged), life 300, power 35. Aimed at one of her scales if one is out, not claimed, in front (+-60 degrees) and over 1100 away, else at the hunter. Each time its attack connects it plays its impact and takes a new leg: subtype 53's first leg goes on to a second scale, then the hunter of the post, else 1000 straight on.
- Port: an own class on uShellEnemy (Stygian's framework), family shell01 entry / group 3 = 4U record 36 / volume 16, effects em093_019 (flight) and em093_020 (impact) as PEL list 2 records 3300 / 3301, sounds 218 / 219 / 220 with 4U's ids. Posted from the slot 125 hook before GU's handler runs; GU's handler then does the rest of the action as before.
- The hit byte: 0 = it connected with a scale, 2 = with a hunter (log of 0.2.0; 4U turns only on 0). The attack connects with a scale's body in GU as in 4U, and GU's scale counts the hit itself (+0x151e). 0.2.0 also tested the distance to its target scale: every bounce came twice, one frame apart (log), so that is gone.
- Water: record 36 has +0x0c = 0x11, water as GU's Plesioth and Royal Ludroth shells (Tigerstripe's beam, tested). So its hit carries Waterblight; a game test of the status itself is still to come. Her other water attack is blast 157 (0x11), which does not come up alone; 7/24's 156 / 158 and the scale's 5 have 0x01 in 4U.
- Not ported: the effect's z scale growing after a bounce (GU's effect object not read), the Palico as a target (the leg flies straight on instead), sound 219's stop at the end (a short sound repeated every 15 frames).
- When she takes it (C): only scripts g1 s74 and s78 start it. They switch on condition 19, her scales out within +-90 degrees of her front, at most 3 (GU f8a964 = 4U 0x76ba20): 3: 7/49 or 7/51; 2: 7/49, 7/51 or 7/48 (40 / 40 / 20); 1: 7/48; 0: 7/50 or 7/46 (50 / 50), 7/50 being the jet straight at the hunter and 7/46 a new launch (s78 the same with 62-65, 7/48 for 1). s74 comes from g0's selectors (many rows, also as "launch, then s74") and from the launch scripts when all 4 slots are full (s49 s73 s75 s76: 60 %, at G rank; op 0x6a = quest rank class, 5 = G, 0x49938, all her quests). GU's conditions 16, 17, 19, 21 count as 4U's do, over its slots (4U tests 0xc69ccc, GU's slots are empty when no scale is out).
- The attack's hit byte (S): the slot's frame writes 255 first (GU 0x16919c = 4U 0xb6ff88), the hit code sets it after that, and 4U's jet never clears it itself, so a connect is seen once.

## What GU dropped from 4U, ported in module/em068_01.c (C)
Checked in the class: 71 species tests in 4U uEm023 (0x75db78..0x76d000: 45 for em 23 outside 0x768094, 26 in it, 7 Apex). GU keeps them as `variant` tests except:
- the scale launches above (slot 47 0x76ace4 cases, 0x7638a0, 0x7651ec);
- 7/24's posts (0x764e88);
- 7/20 at G rank plays at speed 1.5 (0x764790, slot 125 hook);
- her reactions wait 60 frames longer (0x768094 tables: 360 -> 420, 600 -> 660; 4 pairs at 0xfdb274..0xfdb684; GU's tables are copied at run time, hook 0xa134c; tables with op 0x3a keep theirs, 4U has one
  such table for both);
- 3 % shiny on every scale that ends, hit or timed out (uShell015 0xc698f0 at the end of its state 3; hook 0x41b1dc in GU's state 4, until 0.2.1 at the blast 0x41b104, which she never reaches).
Apex tests left out, see Deviations. Kept in GU, read side by side: slot 40's 0.96 (4U 0x761bf4 = f7e008), 7/0's attack 43 (4U 0x7627b4 = f834f8), the chains of 0x764ad4 = f854f4 (r1 -> 7/23 28 34 36 45 47 53 55 57 59).
Slot 48 0x76a010 = slot 130 f8ab20 (C, 2026-11-06): same 16 motions (529 530 531 541 587 787 823 829 830 833 834 842 845 849 850 853), same frames, same calls 0x910c6c = 0xc24d8(-1, 1 or 9): camera shakes (Monoblos' em007_01_mv_j.c names 0x910c6c). uEm023 has no attacks
tied to motions, unlike uEm101 (lesson "Attacks tied to motions"). Every attack index the 4U class passes to 0x933144 / 0x93334c / 0x914dfc also appears at GU's 0x7dc2c / 0x7df94 (scan of the whole class, conditional moves too; 1/23 1/26 1/27's index 10 stays GU's single use, see Handlers).

## Data, 4U vs GU (C)
- attackdata em23 == em93. GU's differs only in byte 28 of each record and record 25 (bytes 26, 28): GU's file is hers.
- hitsize em23 == em93. GU's file = 4U's with the correct far ends (the 6 bytes of the far-end rule, notes/data.md row 28): hers, so no far-end bug here.
- bodydata / cambodydata em23 == em93. GU's: 37 / 26 records against 4U's 40, same bones and sizes with GU's own adjustments (head 120 against 110 and so on). GU's files are hers: the skeleton is identical (44 bones, largest bind
  position difference 0.0), so GU's shapes fit her model as they fit Najarala's. "Hitboxes fit" rests on that (S until played).
- dtbase equal (GU retuned 11 bytes: kept). dttune: GU em068_00's + the 103 bytes 4U's em093 differs from em023 in (GU retuned 19 other bytes, no overlap, asserted). Base HP 4850 (Najarala 4350).
- Shiny counter: dtbase block +0x94 byte 0, GU's Najarala's (hers = the same file).

## Materials (C)
XfB_0__m00_eye unlit, XfB__E0__m00_body solid_sphere, XfBA1__m02_Virs add (group 50: hidden, the frenzy veins), XfB_0__m01_alpha blend. Her MRL's 6 animations on body and alpha are the frenzy steps (hash -> name by brute force over the exe's
strings: Normal_to_VirusLv1, VirusLv1_to_Normal, Normal_to_VirusLv2, VirusLv2_to_Normal, VirusLv1_to_VirusLv2, VirusLv2_to_VirusLv1). GU has no frenzy, nothing starts them: she stays in the rest state (first frame of Normal_to_VirusLv1, 4U's look when not frenzied).
tools/mrl_anim.py `material_anims(d, tail)`: em093's MRL ends 4 B before its last key (frame 15, as every other key).

## Motions, effects, sound
Banks 0 / 2 / 3 / 4 from em093 (bank 4 = 0x402, 0x403, manifest field 8). Slots she lacks are filled with GU's where they lie inside her table (bank 2: 61 64-68 70-74). Bank 0 slots 138, 139 lie past her table of 132 and stay out (C: asked only
by 2/68-71, 4U 0x75ef64 / 0x75f97c with r2 = 1 = GU f80294 / f809e4, Najarala's natives, not in her closure). Roar = motion 0x32; 4U's radial blur has no helper in GU, so GU's air effect (PEL c slots, id 60), the user's rule ("for the roar GU's may be used") as with Monoblos and Black Gravios.
**Tracks since 0.2.2: GU's for all 170 shared slots** (build_em068_01_arc.py motion_bank, tools/lmt.py with_tracks). Every shared slot of hers is 4U em023's track for track, only bank 4 is her own (C, md5 of the tracks). GU em068_00 has the same animations (equal frames, loop, end vectors, track keys; the skeletons have the same joints, parents and bind offsets, only the table order differs, skeleton_check) stored far finer: data 1406800 / 1483521 / 1133650 B against 710504 / 725980 / 519332 B, rotation mostly 11 and 9 bits against 7, bone 0 position 16 bits against 8. Her 4U event blocks stay (sound and effect timing; her PSLs are built from them). The user's rule fits ("Wenn es in MHGU schon Animationen geben sollte ... kannst du aus MHGU nehmen"). I had shipped the coarse 3DS forms until then: on a long chain of bones the 7-bit rotations add up, which is the best lead for "stockt" and for the small jump after the roar (S, not proven: see "After the roar").
The user's rule since 2026-11-06 for every animation that is the same in GU: GU's effects. tools/build_em068_01_arc.py gu_common_effects: in 39 motions GU's common effects (PEL c, cm*: air, dust, spray) go into her entry and replace her 4U common ones there (qe*, 4U's dust); her em093_* effects stay, GU's Najarala-only em068_* / em077_* do not come; a motion where GU has no common effect keeps hers.
Effects: 14 EFLs + MEF em093_0 / _1 converted (tools/efl4u2gu.py), area colour = median of the 4U Frozen Seaway soil. Log note "MEF id 1100 ... not in the MEF": 6 of her PSLs name an id her own MEF does not have, so 4U plays nothing there either.
MEF ids 1027, 1028, 1030 = group 120 (Apex EFLs, not in em093's arc). Sound: 61 waves, bank + request from em093, 20 + 17 common requests from GU's em068_00.

## Snow (the user's test of 0.2.1: "in mh4u kommen so schnee effekte ... immer wenn Sie sich bewegt, die fehlen noch"; C unless marked, module/em068_01_fx.c)
The effect: em093_003 (= em023_003), 2 billboard elements of cm000, on 18 MEF records + 2018, with events in nearly every move (joints 10, 145, 4, 5, 6, 8, 13 ...). It was shipped all along. Four things made it unlike 4U, all checked in code:
1. **Colour.** ffa5a5a5 x the stage's soil (211, 226, 233) x 4U's Intensity 1 = RGB scale 2 (unit +0x18 bits 12-15; the 3DS combiner, tools/efl4u2gu.py UNIT_INTENSITY) = white in 4U. GU has no such field and the converter clears it, so she drew a grey (136, 146, 150) on a white stage. Now spec `intensity` (opt-in, efl4u2gu.intensity_bake): every particle unit of her set takes 2^n in its colour words and curve keys, clamped; alpha stays. Texture cm000 averages RGB 212 where it is visible, so the clamp on the colour instead of on colour x texture costs little. Model units keep their colours: Intensity on them is not proven.
2. **Height.** 0x391b50 copies the MEF flags; 0x227 has the ground flag: 0xc4838c.. takes x, z from the joint + the offset turned by her angles and y from her ground W+0x624 every frame (0xc49a84; on water, lava, poison kinds another height W+0x618, not ported). GU has no such tail and efl4u2gu's PEL_TAIL places the effect at the joint: inside her body. Now her 28 ground-flag joint records are world records (mode 3, pel_ground_records), and a hook on the PSL post (0x700d4) gives the point: joint x, z + offset turned by her yaw, y = rec+0x5b4. A DEVIATION: the point does not ride the joint during the effect's short life. k_ground in the module is asserted against her MEF files at build.
3. **Ground set.** Elements 0x22 (kinds 0, 4), 0x54 (kinds 1, 3, 5); GU's default draws both at once. The hook names the set: Stygian's ray under her (0x183ad0, mask 64), 4U's bit rule on GU's word (S), req+0x14 bit 19 / req+0x6c. Her map has no lava, so a word read as lava counts as kind 0: em093_003 has no lava element and nothing would draw (a guard; GU's word is not proven to mean what 4U's means, `tnport: ground word` logs it).
4. **Scale and end.** MEF bit 5 multiplies her size in (4U 0xc47f98); a world post has no attach model to bring it: req+0x14 bit 30, req+0x40 (GU 0x31c858) with speedFactor (S that this is 4U's this+0x60). Slot mode 1 = the effect ends with its event range (0x391f00.., 0x390b40): end mode 1 on the 24 such records (Dalamadur's pel_slot_end has the code reading). GU's own list 1 has no mode-3 record, list 2 has 64, 22 of them with end mode 1; the code does not tell lists apart (C).
Also: `hide_grey_models` is off for her. The chunks that came out white on Dalamadur and Stygian (their stage is brown) are snow on hers, 4U draws them, and SOLID_FILL removed the 2x. GU's common effects stay as the user's rule says (cm202 takes GU's own stage tint, table 7, +0x70 / +0x73 / +0x64).
The user's test of 0.2.2 (log 21-51-59): the effects are on the ground, "sehen von der Positionierung gut aus"; asks whether MHGU has effects that look better, as GU monsters fight in this area.
**GU's snow since 0.2.3 (C unless marked):**
- Survey: GU's quests on stage 14 have em 67 (19 quests), 3, 83, 42, 61, 66, 34, 43, 32, 57, 24, 86. All step and slide with the common cm202_001 / 002 / 020 / 021 (PEL c and u, for example em 43: cm202_001 on 83 motion posts). The monsters' own em0NN files on that stage are their own looks (ice breath and so on), not ground dust.
- These files hold one set of elements per ground: 0x22 and 0x2 plain, 0x54 water, 0x4, 0x8 lava, 0x80 dark, **0x100 white**: a soft cloud cm101_000 (78ffffff), snow clods cm202_022_g (ff8e8e8e, twice), cm100_008 (ffffffff) and a ground smear cm090_011 (ffffffff) in cm202_001 / 002. Capcom bakes 0x100 into 71 cm202 records of em 38, 42, 61, 66, 67, 83, 86, all monsters of snow (S for what 0x100 means, from those and from its colours), Zamtrios' steps on joints 80, 90 among them. 2408 other records have -1.
- cm202_002 is in her arc from GU em068_00 and has the same element words as cm202_001, the steps' file. Her 18 ground records of em093_003 now play it: GU's own record 3 of em068_00c (its stage tint included) as a world record with mask 0x100000, GU's usual one, 4U's scales and her points. 4U's em093_003 stays on the 2 records without the ground flag. pel_ground_records; a DEVIATION, wanted. The 4U EFL stays in the arc.
- A record finds what the arc has loaded (S for a PEL): cm202_002 and the 25 files it names now come before her PEL u (snow_first), asserted to be found there.
- The set: her ground word on this stage logs as 0 (only that value, area 2), so the attribute does not tell snow. Both her quests are on map 14, so em068_01_fx.c gu_set names the snow set (0.2.3..0.2.8 kept the plain set for the Arena quest 11497 by its number; that quest is gone since 0.2.9, the test since 0.2.10). GU's common effects she posts (kind 3, hook 0x70068) take the same set: all their files have a 0x100 set or elements for every ground (tn_gu24). How GU picks a set for its own -1 records was not found: no request override on the PSL path (C), and the element test 0x9be8c4 takes the effect's flags as they are (C). So the set is named for her, which is right if GU has a picker elsewhere too. A word with water or the like keeps 4U's rule, which fits GU's sets.
Seen in game since 0.2.3 (the user's test of 0.2.3: "die Eis-Effekte auf dem Boden sehen nun richtig gut aus, bitte so lassen"); 0.2.7 added the qe006 family (Porting history).

## After the roar (the user's test of 0.2.1: "hackt ganz kurz nach dem Entdeckungs-Sound und der Animation, scheint sich minimal zu teleportieren"; log 20-45-21)
Log (C): roars at 00:01:59.083, 03:19.106, 05:35.917. Discovery: 2/45 (0x10) -> 2/46 (0x15) -> 1/0 (0x32) for 5.78 s -> 04.866 2/45 (0x10, 0.57 s) -> 2/46 (0.45 s) -> 2/33. No stop of the game thread: `gogport: dmg special path` lines stay 3.33 s apart over the roar's end. Motion speed 0.925 out of rage, 1.085 in rage: 321 frames = 5.78 / 4.93 s, no hold at the end. The only other line there: AudioRenderer "Unmap of memory pool failed", 1176 times in that log from second 16 on, so not hers.
Code (C): GU's handlers of 2/45, 2/46, 1/0 match 4U's (f80fd0 = 0x75fe54, f81c10 = 0x760798, f7e820 = 0x761c1c; speed 1.2 / 1.8; blends 0xb0170 = 0x93947c), nothing writes her position in that path, root track static in both games, end vectors zero.
So what is left is the animation data itself (S): the coarse tracks above, now GU's. **`tnport: jump` proves it either way in the next log:** per frame her position, yaw and joint 6; a line for every sudden step, and every frame for 45 frames after each roar. If the step stays in her position or yaw after 0.2.2, it is code, not data.
**The log of 0.2.2 (21-51-59) corrects that (C for the numbers, S for the reading):** with GU's tracks the frames after each roar are smooth: joint 6 steps 0 to 1 unit. The step is **before** the roar, right at the discovery: 01:56.214 motion 0x2c (2/4, her slither), 01:56.232 2/45, 01:56.251 motion 0x10: joint 6 moves 222 units in one frame (27 the frame before); the same at 05:19.756, 0x2b -> 0x10: 252 units (12 before), her position 25. The roar comes 1 s later. So it was not the coarse tracks. In the whole log there are 7 such lines: these 2, 3 x 0x402 -> 0x403 (66 units), 1 x inside 0x233 at frame 1 (128 units), 1 at her first frame.
Cause (S): the AI stops her mid-slither, her body stretched out, and 2/45 starts the turn with a blend of 8 frames (GU f81128.. = 4U 0x7601d4.., 0xb0170 = 0x93947c, s0 = 8.0, at speed 1.2 about 8 ticks; C), far too short for a whole body: joint 6 is still 815 from her origin at that frame and 595 when the pose is reached, so it is a blend and not a cut. The other path of 2/45 (motion 0xb first) showed no step. GU's motion start has a one-shot "no blend" bit (this+0x1408 bit 0x800, 0xafe1c), its setter was not found, so a cut is not ruled out: `tnport: jump` now logs 14 frames after each sudden step, which tells the two apart.
0.2.3: hook 0xb0170, for her from 0x2b..0x2d into 0xb..0x18: 30 frames (`tnport: long blend`). 4U has the same 8 (C), so it is a DEVIATION, cosmetic and wanted ("bitte Ursache finden und lösen"). GU's tracks stay: they are the same animation, finer.
**The log of 0.2.3 (2026-11-07 08-36-08) corrects that too (C for the numbers):** the user: "am Anfang des Kampfes teleportiert sie sich immer noch". 00:04:20.344 long blend 0x2c -> 0x10: joint 6 steps 78, then 669 in one frame, then 0 to 1 unit a frame; 00:09:16.726 from 0x2b: 90, 534, then 0 to 1. So a cut, not a blend, one frame after the start, whatever the frames given. My "S: it is a blend" above was wrong.
The cut (C): 2/45 is a cross-fade of two layers. Motions 0x10..0x14 hold her body turned by 90 degrees each (joint 6 at 90-degree steps, forward kinematics from the tracks, a scratch script); layer 1's weight is the body angle / 90 (this+0x638, 0xf81454..). 0xf81abc starts another pair when that angle crosses a quadrant, with blend 0.0 (0xf81b34, 0xf81c0c, through 0xb0230). Her first step 3 frame does exactly that: step 0 took the pair of the remembered quadrant. Between turns this is invisible (weight near 0, same pose); on a pose from her slither it throws away the blend.
0.2.5: hook 0xb0230: while the cut's blend runs, a pair switch takes what is left of it (`tnport: pair switch`). The engine saves the model's joints as a blend's start at each motion start (0x951504..0x951734, C), so the second start goes on from where she is. Not seen in game yet.
**The logs of 0.2.5 (2026-11-07 19-27-11 and 20-15-35, quest 11368 three times; C for the numbers):** the user: "teleportiert sich am Anfang des Kampfes immer noch". The cut at the discovery is gone: 2b -> b runs as a blend, joint 6 moves 78, 79, 84, 85, 81, 74, 66 ... 20 units a frame (14 frames, `tnport: pair switch ... 15 frames left` after it) instead of 669 in one frame. Still some 600 units in 0.25 s. Two real one-frame steps remain, both about 13 s after the discovery, at the first spit:
- **The spit 7/48-51 62-65 (GU f861b0 = 4U 0x765810):** at frame 134 of 0x402 both games start 0x403 with blend 0 and frame 0 (GU f86708: s0 = s1 = 0.0; 4U 0x765e80: s0 = s1 = s19 = 0.0, frame test 134.0 at 0x765fe4). Joint 6 moves 74 / 61 units in that frame, 15 to 30 in the frames around it. Her bank 4 is 4U's own (GU has none), so 4U shows the same step (S).
- **A single motion after the 2/45 pair (S):** 0xafda4's tail sets layer 1's weight this+0x638 to 0.0 at once (0xafeb4 = 0x726dc, C) and 0x53a164 gives layer 1 motion 0xffff with blend 0 (C). After 2/45 that layer holds the turned pose: 19-27-11 03:23.292, 2/45 (0x13) -> 7/29 (0x20e, blend 20): joint 6 moves 58 units in the first frame, then 4, 6, 8, 11 (a blend from another pose). GU's own Najarala runs the same code (S).
0.2.6: the cut slither blends 60 frames (BLEND_STOP); hook em068_01_spit403 at 0xf8672c (r0 = this, before its `movw r1, #0x403; bl 0xaff40`) gives 0x403 a blend of 8 frames when it follows 0x402 (`tnport: spit 402 -> 403`). Both DEVIATIONS, cosmetic. The layer drop is only logged (`tnport: layer weight N% dropped at once`): giving it a fade would keep layer 1 on a motion GU has just cleared, which cannot be tested here. Not played yet.

## Routes (C)
GU em068_00's area files + map 14 (Frozen Seaway, no GU Najarala map; record shapes from GU em067_00): her 4U data of stage 4: areas 2, 3, 6, 7; hops {2: 3 7, 3: 2 6, 6: 3 7, 7: 2 6}; sleep 6, eat 7 (slot 66); spawn area 2; stay timers and routing from
g0 s9 as 4U's. The Arena needs none of it: GU's own. g0 s18's stage case 4 -> GU 14 (AI table).

Corrected in 0.1.1 by reading what GU's engine does with them (C, tools/routes_em068_01.py has the addresses; 0.1.0 never reached them, see "Porting history"):
- **area_link kind 4 is the way to the sleep area** (reason 1, 0xb870c): GU Zamtrios' leads to his area 7, so she could never have started her move to 6. Hers now: 2 -> 7 -> 6, 3 -> 6, 7 -> 6.
- **area_eat had no map 14**: the only reader 0xb7e90 then gives chance 0, so she would never have gone to eat. GU Najarala's own eating row now (20 % when tired, rec+0x505 state 2 / 3, else 10 % at stamina up to 100).
- **4U's step 2 -> 3 does not exist on GU's stage** (a DEVIATION): she dives (types 4 / 3) and surfaces at the next area's flags-0x20 point whichever area she left, but travels to the current area's exit point of that step, and area 2 has none (exits to 1 and 7 only; area 3 has one to 2, for all groups, variant 0). Without the point nothing is written and she would travel toward the last exit she knew. So area 2 only leaves to 7, her 30 % for 3 included, and the weakened way from 2 runs through 7, not 3. 3 -> 2 stays, as all her other steps.
- area_patrol stays GU's (nothing on her maps, as GU's Zinogre on map 14). Sleep in 6 and eating in 7 are places GU's own monsters use on this map (em003 / em066 sleep in 6; most eat in 7).

## Items, carves, breaks, shiny (C)
Items: 4U 1366 T.Najarala Piel, 1367 Cortex, 1368 Splasher -> 3048..3050. Others by same English name (Flood Sac, Heart-stopping Beak, Large Wyvern Tear, Lrg Wyvern Gem, Monster Slogbone: asserted). She is G rank only in 4U: hagi s4 = body + shiny, s0..s3 GU's filler.
Breaks BUI4: 4U groups 0 / 2 / 3 / 4 / 5 -> GU Najarala's conds 10 / 20 / 30 / 40 / 50. Group 1 (frenzy crystals) has no GU part.
Shiny triggers: the mechanic is monsters/monoblos/notes/plan.md "Shiny drops". In uEm023 one direct call, 100 % at 0x76b340 (GU f7d5fc); uShell015's 3 % (ported); no op 24 in its reaction tables (C: scan of both games' tables). GU adds a second one for both variants (f8ca28, 60 %, a GU action):
stays (the rule for hosted monsters). Logged as "item drop call".

## Gear
Armor Najarala Z (4U), Blademaster + Gunner, models 432 / 433, template GU Najarala X (867, 868): defense 88 -> 115, 47 -> 68, the template's level rows. tools/gear_em068_01.py lists tree and item substitutions (PunishDraw -> Punish Draw, Rhenoplos Bone -> Large Herbivore Bone).
Weapons: 7 lines, 17 records (tools/gear_weapons_em068_01.py): SnS Lepis Prism line, Lance Jingana line, HBG Azure Blast line, LS Hyddra line, SA Cryoseism line, HH Naja Warning line, IG Medusa line (kinsect Mauldrone: tools/weapons4u.py insect_4u). Values = 4U's. Recipes: 4U's, items GU lacks =
SUBSTITUTES (list in the tool, G, for review). No sound arcs: each 4U arc's set is one GU ships.

## Name, icon, Notes
monsterName's first-list dummies are all taken and the Notes detail page reads the name entry as a byte (0x5b2298), so a TXTA-appended 268 fails: hers = 'dummy7' of the second list, entry 227 (when she was ported 221..226 were free; since Nerscylla 226 and Monoblos 221: 222..225; tools/alloc.py NAME_DUMMY). Icon cell 206 (4U icon 102). Notes entry 130 after entry 68 (Najarala),
threat 6, no save bit (module/notes.c), count 131 (odd: NOTES_PAIR_BOUND handles it).

## Quests (tools/build_em068_01_quest.py has the rules, C unless marked)
| ID | 4U | Placement | Template | Rows HP / attack / other (values) | Size | Subquest |
|---|---|---|---|---|---|---|
| 11368 | m10822 | hub G3 | q11330, base q11339's Najarala | 102 / 108 / 96 (3.6 / 7.9) | 100 | wound head |
| 11453 | m11022 | hub G4 | q11433 | 116 / 109 / 97 (4.3 / 8.2), r as above | 130 | wound tail |
r of m11022 (S): 4U's rows over the median of 4U's 4 plain single hub hunts at star 10; the 10 Apex hunts of that star sit at 2.29-2.35 / 7.6-8.2. Hub boxes = the template's (4 Maps, C: all 548 GU hub quests hold 0 or 4). Only her 4U quests, where 4U has them (the user, 2026-11-08): both are guild quests, so hub only. Until 0.2.8 she also had village copies 1060 / 1061 (hub quests moved to the village: one Map, C: all 343 GU village quests hold 0 or 1), and until 0.2.9 m11016 as hub Arena quest 11497 (q11480, GU's version of that quest).

Not ported: **m22002** "Grudge Match: Tidal Najarala" (Arena, quest type 1, stats 26 / 72 / 133, fee 0): preset gear and time ranks live in exe tables keyed by quest number (Stygian's notes/quests.md 1), as Stygian's m21003 and Black Gravios' m21006.

## Limits this port reached (notes/porting-guide.md)
- Sharpness: mKireType is a byte. GU 164 + the earlier ports 88 + her 4 = 256: full. Her other 5 4U entries take the nearest GU row (KIRE_NEAR, weapons4u logs them) as the fallback; since 0.2.10 her 7 weapons on them read their own 4U row through the core (KIRX, notes/gear-weapons.md section 6). The next port: `kire_reuse`, `kire_near` and KIRX.
- Armor "listed" bits: 576 records per part, head full with her 1 record (record 575). The next monster with armor needs an answer first.
- monsterName: entries 222..225 left (Monoblos took 221, Shrouded Nerscylla 226).

## Deviations
1. Apex state (em 120, 4U W+0x7e80 bit 32, spawn byte 9) not ported: m11022 runs as the normal Tidal, with the stat step above. GU's variant 3 code stays unused. Her Apex quests keep 4U's size 130.
2. Rage scale hit record 6 not ported (GU's family has no such variant).
3. Rattle and blast effects -> em093_004 where GU posts one and 4U none; they cannot come up for her alone.
4. Sharpness: none left since 0.2.10 (KIRX). With a core without that hook, 5 rows take the nearest GU row (differences 10..40 of 450, at the bars' end).
5. Recipe substitutes (tools).
6. Frenzy materials and group 50 stay off (GU has no frenzy).
7. Roar: GU's air effect instead of 4U's radial blur.
8. m22002 not ported. 4U's Hub G1 / G3 become GU's G3 / G4, with GU's money.
9. Event quests: this machine has no 4U DLC extdata (tools/extdata4u.py); any event quest of hers is unread.
10. Her 4U step from area 2 to 3 is not taken: GU's stage has no exit point for it ("Routes").
11. GU's common effects replace 4U's dust and roar effects where the animation is GU's (the user's rule, "Motions, effects, sound").
12. Water jet: no z growth of its effect after a bounce, no Palico target ("The water jet").
13. Open, not changed: GU's scale class arms a small hit on landing for every kind (0x41b6f0); 4U's kinds 9..18 have none (0xc69030). Power 0, a status hit of 20 frames.
14. Open, not read to the end: 4U 0x769a40.. keeps a list at work+120+48i with 0xc07bb8 kind 10 + 0x684b00, and 0xc08628 at 0x76aca4 (ground marks, S: cosmetic; GU's twin not searched); 0xc0819c at 0x76c9b0; the sound calls 0x390f9c / 0x2fd110 / 0x2fff1c at 0x761d50.. and 0x76254c...
15. Motions: GU's tracks instead of 4U's for the 170 shared slots, her event blocks stay ("Motions, effects, sound"). Same animation, finer form.
16. Snow: GU's cm202_002 snow set instead of 4U's em093_003 on her ground records; placed once at the post instead of riding the joint; 4U's water height not ported; a ground word read as lava counts as normal ground ("Snow").
17. A blend of 60 frames instead of 8 when her slither is cut short by 2/45 ("After the roar"; 30 in 0.2.3..0.2.5).
18. Her spit's switch 0x402 -> 0x403 blends 8 frames instead of cutting (both games cut; "After the roar", 0.2.6).

## Read through for the user's test of 0.2.1 (2026-11-06; no fault found, nothing changed but a log line; not seen in game unless marked)
- Hitzones (C): dttune tables at +0x8e (normal) and +0xde (tired, rec+0x505 in {2, 3}: 4U 0x92e998 = GU 0x816d0 at slot 48 / 130) are 4U em093's byte for byte, rows 0..6; row 7 is GU's and no volume uses it. GU's Najarala rows are 4U em023's, so GU retuned none. Body volumes are GU's file; (part, zone) pairs equal 4U em093's (11 pairs). Cut / impact / shot by zone: 0 head 20 / 24 / 16, 1 inner neck 27 / 25 / 23, 2 body 25 / 20 / 18, 3 neck, mid body and tail tip 45 / 40 / 40, 4 tail 30 / 25 / 20, 5 front legs 55 / 50 / 60, 6 hind legs 23 / 25 / 50 (front and hind by the bones' bind positions).
- Breaks (C): part table at +0x3c is 4U's (stagger values 80, 180, 250, 350 then 1050, 200, 200, 160, 160). slot 132 f89afc has no variant test; dtbparts' values head 2, parts 2 3 7 6 one equal 4U's emd part rows (the same for em 23 and 93); her model has all the groups of the states (3 / 102, 5 / 103, 7 / 101, 12 / 104, 14 / 105). The tail only breaks: one model in GU and no tail carve in 4U (state 10, no severed object). Rewards: BUI4 groups 0 2 3 4 5 on conds 10..50. Log of 0.2.0: 10 staggers (10/7 x 9, 10/114), the actions run; breaks themselves were not logged, `tnport: part` now does.
- Area moves: log of 0.2.0: 2 -> 7 at 75 % HP by dive (6/2 6/3 6/2 6/3 6/1), 7 minutes after the start, and no other in 10 minutes. Scripts s83..s90 are GU's, each action has a handler. Which timer asks for a move in combat was not read to the end (0xb83ec: +0x7404 .. +0x7410).
- Eating: area 7; 1/10 plays motion 0x3a three times, then 1/11; motions present. Sleep: area 6; 1/12 plays 0x33, 0x38; motions present. Not seen in a log yet (that fight ended at 51 % HP).

## Checked
tools/alloc.py, check_repo --all, ci_compile, test_save, py_compile, build.py --list (2026-11-06, again 2026-11-08 for 0.2.10). Played: 0.1.1 .. 0.2.7 (Porting history; the long hunt of 0.2.7 to the end); 0.2.8 .. 0.2.10 change only her quest list, sharpness and a dead test, not played yet. Logs "tnport:" show each action and motion with HP and rage, "tnport: scale" (kind, state, hits, effect handle, place, then each state change), "tnport: scale kinds", "tnport: spit aims at scale", "tnport: jet" (post, legs, impacts, end), "tnport: reaction table", "tnport: part", "tnport: ground word", "tnport: ground post", "tnport: common post", "tnport: long blend", "tnport: jump", "item drop call". Yuzu / Eden and the PC recomp could not be run here;
the code keeps the core's rules (no fixed ranges, no exotic instructions, all GU addresses through MAIN / FN).

## Porting history
- 2026-11-06: 0.1.0, everything above, on the local base c248e6b (save store core + Monoblos 0.4.5 + Black Gravios 1.0.1), first local test build.
- 2026-11-06, the user's first test: "looks like a normal one and is completely buggy" (no log of it). **Cause (C, from the code and the file sizes, not seen in a log):** the core's data pool was 256 KB and her 21680 bytes came after 261280 of 262144, so port.c refused her file with one log line. A monster without its data keeps its donor's manifest, which is GU Najarala's model, motions, AI and tuning (em068_00.arc is loaded for the stand-in anyway); with no items, gear, Notes or name of hers, while her hooks asked for shell kinds GU's family does not have. My fault: I packed the file without adding up the pool.
- 2026-11-06: 0.1.1. On the current Monoblos core (0.4.6, slot 132 hook), which now holds the bigger pool as well (512 KB, tools/alloc.py DATA_POOL, and module/build.py refuses a build that does not fit); the routes above. **So the first real run of her model and data is still to come.**
- 2026-11-06, the user's test of 0.1.1 (log 17-55-22, quest 11453, 2 minutes): right colour; "behaves strangely, stutters often, no spit animation, no scales". Her data loaded (`tidal_najarala data 0.1.1 loaded`) and her 4U AI ran: 26 actions, none without a handler, no "motion ffff" after the first frame. She fired scales only twice, at the very end (7/57 and 7/47: `scale kinds 15 16 x 2`, `0 1 x 2`, the handles came back, so the shells exist; whether their effect showed is not in that log). No 7/48-51 came up in those 2 minutes. Half a minute of it she had not noticed the hunter (scripts 1/83 1/84: 2/4, then 7 s of 1/5). Frame times were steady (GU's 3.33 s counter, a few steps of 0.2-0.3 s), so the stutter is not the emulator (S). Per action in the fight: 2/45 + 2/46 (0.6 + 0.45 s, the turn to the target) before most attacks: the best candidate for "stutters" (G), to ask the user. Those turns are 4U's own: speed 1.2 in 2/45 (4U 0x75fea8, GU f80ffc) and 1.8 in 2/46 for her, 1.5 for Najarala (4U 0x7607ac); the log's 0.45 s = 49 frames / (60 x 1.8), and 0x10 -> 0x11 in 2/45 keeps the frame, so no motion was cut short (C). AI: s74 ran once in that fight, with none of the 2 scales just launched in front (S: it took 7/46, which only the "0 in front" branch has), and drew 7/46 over 7/50, so one 50 % draw decided that no jet came up even apart from the missing shot.
- 2026-11-06: 0.2.0. The water jet (above); GU's common effects on her motions; the log shows per scale its kind, state and effect handle, per action HP and rage. Not played yet.
- 2026-11-06, the user on the 0.1.1 test: the scales were not seen (the log has 2 launches, in the last 10 s of the fight). 0.2.0 changes nothing in how they draw. Read through, no fault found (C): GU's scale setup 0x419e84 posts through the family def's PEL (0x4a2508 -> +0x1388, her def names em068_01u), list 2 records 0 and 3 -> em093_030, kind ef files equal to GU's; the scale's entry 3 (em093_tuning, BSSolid, same size as GU's model) matches GU's em068_00_000 entry 0 word for word but for the path, unit +4 bit 8 (GU set, hers clear) and the 0.67 scale (GU in the element, hers in the unit). Other difference: GU's scale mesh has format 0xa7d7d03a, hers the effect format with the efx_solid template. (That read-through was wrong in its conclusion: see the next entry. It compared only what kinds 0 and 1 use.)
- 2026-11-06, the user's test of 0.2.0 (log 19-59-15, quest 11368, 10 minutes; screenshot): she spits, the jet bounces. "Scales and some attacks look odd", the scales glow blue, show as flat white blocks, and do not really break or go. The new log line showed it at once: kinds 15..18 "efx 0 0" and no launch offset, kinds 0 and 1 fine. Causes (C unless marked): (1) kinds 11..20 lay behind the def in the arc, so they had no effect, hit data or offset: invisible at her feet; (2) the white vertex fill on her solid model; (3) GU's second flight post drew her special-state look (mask 2) over the plain one; (4) GU's "gone" effect stood on em093_031, a new whole scale, where 4U has em093_004 (my mapping); (5) two hits at G rank, Najarala's; (6) every bounce came twice; (7) the shiny hook sat where she never comes. The user's question whether her scales should burst: not in 4U (above). Time per action in that fight: 2/45 72 s (65 times) + 2/46 17 s of 610 s, 4U's own turns; the user's "stutters" was not repeated, no time given.
- 2026-11-06: 0.2.1. All of the above fixed; the log adds each scale's state changes with its hits. Not played yet. Which "some attacks" look odd is still open: her other solid chunks got the same brightness fix, the rest needs the user's naming (S that the fix covers them).
- 2026-11-06, the user's test of 0.2.1 (log 20-45-21, quest 11368): the log confirms the scale fixes: kinds 15..18 now have effect handles and fly (`efx` non-zero, state 1 -> 2 -> 4 at 0 hits), the jet aims at scales and bounces. The user names two things: a hitch and a small jump after the discovery roar, and 4U's snow on the ground when she moves ("After the roar", "Snow"). Not named again: the scales. That log has no `tnport: part` line.
- 2026-11-06: 0.2.2. GU's tracks, the snow, `tnport: jump`. Not played yet. Whether the tracks take the hitch away is open until the next log.
- 2026-11-06, the user's test of 0.2.2 (log 21-51-59, quest 11368): data 0.2.2 loaded, the effects on the ground are placed well (user). Asks for GU's effects to look better. The log: the step is still there, in another place than I had said ("After the roar").
- 2026-11-06: 0.2.3. GU's snow ("Snow"), the longer blend ("After the roar"), action lines for a repeated quest. Not played yet.
- 2026-11-07: 0.2.4. One Map at the start of the village quests 1060 / 1061 (seen while porting Shrouded Nerscylla, the user: "Ja, ändern"). Compared with 0.2.3: in her package only those two quest arcs differ, inside them only the box file (the 3 extra Maps gone, delivery 1 and group 4 the same items in the same order); her data file differs in the version byte alone; the module is unchanged. Not played yet.
- 2026-11-07, the user's test of 0.2.3 (log 08-36-08, quest 11368 twice): "die Eis-Effekte auf dem Boden sehen nun richtig gut aus, bitte so lassen"; the teleport at the start of the fight is still there.
- 2026-11-07: 0.2.5. The cause of that teleport ("After the roar"). Her package files stay as in 0.2.4, the new code is in the core. Not played yet.
- 2026-11-07, the user's test of 0.2.5 (logs 19-27-11, 20-15-35): "teleportiert sich am Anfang des Kampfes immer noch". The discovery cut is gone; the spit's cut 0x402 -> 0x403 and the layer drop after 2/45 remain ("After the roar").
- 2026-11-07: 0.2.6. 60-frame blend at the discovery, 8 frames at the spit's switch, a log line for the layer drop. Her package files stay as in 0.2.4; the code and the data file's version byte are in the core. Not played yet.
- 2026-11-08, the user on 0.2.6 (log 11-04-37, quest 11368, screenshot): no jump any more; the ice splinters "top, so lassen"; but a yellow-orange cloud now and then while she moves. The log (C): record 2016 (4U's common dust qe006_001 on joint 13, motion 0x2b frame 40) posts with set 3 (4U's soil rule on ground word 0), every slither; her other ground records of the qe006 family (2000 2002 2006 2011 2013 2014 2017) are the same kind. 0.2.7: is_snow_record takes the qe006 family too, so all 26 of them play GU's cm202_002 with set 0x100 (k_ground's snow column); em093_007 (2008 / 2009) stays 4U's. Against 0.2.6: only PEL u in em068_01.arc, the data file's version byte, em068_01_fx.c. Not played yet.
- 2026-11-08: 0.2.8 (the user: no village quests where 4U has none): her three 4U quests m10822 / m11022 / m11016 are guild quests, so hub only: 11368 / 11453 / 11497. Gone: the village copies 1060 / 1061 (allocations.toml, QUESTS with k renumbered, romfs, test folder); the core changes too (port_monsters' quest list); her Notes record now names 11368 (quests[0]). The quest table above still lists 1060 / 1061.
- 2026-11-08: 0.2.9 (the user: "Arena Quests sollen auch raus"): m11016 (11497, the guild Arena quest) is out too, so she has 11368 and 11453. module/em068_01_fx.c keeps QUEST_ARENA 11497 (the plain ground set off the Frozen Seaway): with no such quest the branch never runs, her snow on her two quests is as before; left untouched as the user approved her look (S: removable later). Only port_monsters' quest list changed in the core.
- 2026-11-08: 0.2.10 (the user: "ich will schon die originalen werte"): her 7 weapons on KIRE_NEAR rows read their own 4U row through the core (KIRX). Her data file changed (a KIRX section, the version), and em068_01_fx.c gu_set lost the Arena quest's test (no quest of hers matched it since 0.2.9: the same set for every quest she has); her package files are the same as in 0.2.9. Not played yet.
