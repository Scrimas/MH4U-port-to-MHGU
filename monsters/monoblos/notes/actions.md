# Monoblos: his 4U AI table and actions (stage 2, from 2026-11-05)

The user chose "AI and attacks" (2026-11-05): his 4U AI table and ALL his own attacks. Route B (plan.md "Class
route"): literal C ports of his 4U uEm101 handlers. C = confirmed in code, S = strong, G = guess.

## What runs where
- **AI table** (tools/build_em007_01_arc.py `cmdtbl`, own file in manifest field 37): his 4U em101_cmd (op-0x46 blocks
  reduced to case 101) in GU's language. GU's area language replaces 4U's in g0 s0 (`14 0c` -> `9e 00 00`), g0 s8 (his
  area move = GU's g0 s1 `94 95`), g0 s1 (his patrol = GU's g0 s2 `96 97 4e`), g20 s0; group 7 = GU's, group 16 empty.
  Group 1 = his 65 scripts, then GU's numbers 65..140 empty except the area_act_tbl scripts of the donor index 114
  (Diablos: 121..127, read from resident.arc), which are GU's with their calls imported at 141..143. GU's class picks
  group-1 scripts only through area_act_tbl (C: every synthesized `14 nn` at this+0xba34 comes from 0xb4e58; no
  uEm007_00 code writes the think fields). Ops left that GU's Diablos table never uses: 0x43 (g0 s3), 0x6c (g1 s13)
  have GU handlers (0x84320 -> 0x87e00, 0x844d0 -> 0x8932c, not the no-op 0x8470c); 4U's handlers were not compared
  (4U interpreter table not located): OPEN. 0x80 (g0 s4, 4U rest bodies): GU always skips, as Black Gravios' table.
- **Distance rows**: his 4U row (400, 1000, 2500, 5000) (dt_convert without --keep-ranges, `dttune_ai`), the GU
  retunes moved with the shifted fields (C: equal bytes on both sides of the range block).
- **Natives** (`action_of`): engine actions kept (0/255 = GU END, 11/38 = base 0xa134c = 4U 0x9197c0, C); TWINS = GU's
  same-category action whose handler plays the same motion set with the same side parameter (GU Diablos' handler:
  interim, his 4U handler not ported); every other action (c, n) -> (c, 208 + n), numbers no GU dispatcher handles
  (C), run by module/em007_01_moves.c. GU slot 127 only remaps category 2 <= 16 and slot 129 switches on bounded
  ranges (C), so ours pass both.
- **Dispatch** (module/em007_01_moves.c): GU slot 125 entry hook; for our numbers work+8 = 0, the MV row's port, then a
  C copy of GU's common tail 0xd35f9c (isAction(7, 7) -> work+9; work+16 = 600/300, 900/600, 1200/900 by work+10 and
  slowState; work+12 += dt up to work+16; C), return 1. An action without a row ends at once (logged once).
- **Attack data** (`attack_files`): his 4U em101 attackdata (61 records) and hitsize (32 groups) in manifest fields 27
  / 29 = GU's second attack table (C: 0x70ffc / 0x7105c take indexes >= 1000 from this+0x75d8 / 0x75e0; the 18 GU
  monsters that fill 27 / 29 give them the attackdata / hitsize types; GU's Diablos leaves both empty). His handlers
  attack with 1000 + his 4U index (MB_ATK); GU's pair 26 / 28 stays for GU's handlers. Byte 25 of a record = its
  hitsize group (C: 0x7de00). His 4U values, plus GU's changes of the 4U Diablos records that equal his (GU raised 9 of
  Diablos' 66 powers, byte 4, by 1.1..1.45; which of his records take them: plan.md, gu_retunes).
- **GU's own Diablos code holds GU versions of many of his 4U handlers** (the 4U uEm099 / uEm101 lineage): GU 0xd430a8 =
  his charge 0x8db41c (same steps, motions, attack parameters 154 / 138, timer 300, helper calls), GU 0xd3c7bc = 4U
  0x8defb0, 0xd41050 = 0x8d750c, 0xd3b154 = 0x8e0d34 (S, structure and constants). Their field offsets and calls are
  the evidence for each port's 4U -> GU map (module/em007_01.h); their attack indexes are Diablos', hence the ports.

## Actions (closure of his table: 87 natives + 11 chained (*); r1 = the 4U sub-dispatcher's side / kind parameter)
| 4U handler | ins | actions (r1) | motions | status |
|---|---|---|---|---|
| 0x8d6944 | 76 | 3/0(0) | 10d 113 | 3/0 twin GU 3/3 |
| 0x8d6a74 | 131 | 3/2(2) | 101 | open |
| 0x8d6c80 | 97 | 3/3(3) | 101 | open |
| 0x8d6e04 | 117 | 3/4(4) | 101 104 110 111 | open |
| 0x8d6fd8 | 155 | 3/6*(0) | - | open |
| 0x8d7244 | 178 | 3/7*(0) | 1f 20 21 | 3/7 twin GU 3/7 |
| 0x8d7d8c | 95 | 2/0(0) 2/21(1) 2/25(2) 2/26(3) | 3 5 | open |
| 0x8d7f08 | 73 | 2/2(2) | 1 20f | open |
| 0x8d81d0 | 116 | 2/6(0) 2/22(1) | 3 6 | open |
| 0x8d83a0 | 94 | 2/7(7) | 404 | open |
| 0x8d8518 | 123 | 2/10(10) | 1 3 20f 210 | open |
| 0x8d89d0 | 188 | 2/12(0) 2/14(1) 2/18(2) | 7 | open |
| 0x8d8cc0 | 449 | 2/13(0) 2/15(1) | 419 41a | twins GU 2/19 / 2/20 (GU's ignores 4U W+488, which the charge sets) |
| 0x8d93c4 | 177 | 2/19(0) 2/20(1) 2/23(2) | 3 7 8 | open |
| 0x8d9af8 | 105 | 1/2* | 1 317 318 | ported (mv_a) |
| 0x8d9c9c | 124 | 1/21(1) 1/34(3) | 404 | open |
| 0x8d9e8c | 106 | 1/7 | 1 12 13 | open (only in his patrol, which GU's replaces) |
| 0x8da034 | 48 | 1/9* | 1 14 | open |
| 0x8da0f4 | 31 | 1/10 | 310 | open |
| 0x8da42c | 212 | 1/28(0) 1/29(1) 1/32(2) 1/33(3) | 7 41e 41f 424 425 | open |
| 0x8da77c | 179 | 1/31(1) | 7 418 | open |
| 0x8daa48 | 100 | 7/0(0) 7/18(1) | 201 | twin GU 7/0 (7/18 approximate) |
| 0x8dabd8 | 174 | 7/2(0) 7/19(1) | 204 | open |
| 0x8dae90 | 100 | 7/9 | 214 | twin GU 7/5 |
| 0x8db41c | 351 | 7/3(0) 7/10(1) 7/24(4) 7/25*(5) 7/34(8) | 1 3 6 210 | ported (mv_a) |
| 0x8db998 | 137 | 7/4(0) 7/21(1) | 1 20f 213 | open |
| 0x8dbbbc | 84 | 7/5(0) 7/22(1) | 213 | twin GU 7/131 (7/22 approximate) |
| 0x8dbd0c | 74 | 7/6(0) 7/20(1) | 215 | twin GU 7/6 (7/20 approximate) |
| 0x8dbe34 | 83 | 7/7 | 216 | twin GU 7/7 |
| 0x8dbf80 | 111 | 7/31(0) 7/32(1) | - | open |
| 0x8dc13c | 286 | 7/13(0) 7/14*(1) 7/15*(2) 7/28(3) 7/29*(4) 7/30*(5) 7/33(6) | 1 415 422 | open |
| 0x8dc5b4 | 85 | 6/0(0) 6/17(1) | 17 18 | twins GU 6/0 / 6/20 |
| 0x8dc708 | 77 | 6/2(2) | 212 | open |
| 0x8dcc80 | 336 | 6/4(0) 6/15(1) 6/16(2) 6/20(3) | 20f | open |
| 0x8dd310 | 197 | 6/8(0) 6/9(1) | 1 212 | open |
| 0x8dd624 | 56 | 6/11(0) 6/18(1) 6/19(2) | - | open |
| 0x8dd704 | 121 | 6/12(12) | 20f | open |
| 0x8dd8e8 | 79 | 6/14*(14) | 28 | twin GU 6/26 |
| (base) | - | 11/38 | - | engine |
| sub 0x8d7a78 | - | 0/2 0/255 | 40e | 0/2 twin GU 0/2; 0/255 engine |
| sub 0x8d9688 | - | 3/1 | 101 | open |
| sub 0x8db020 | - | 7/1 7/8 | 201 219 | open |
| sub 0x8dc83c | - | 6/1 6/3 6/7 6/13 | 1 | open |
| sub 0x8dda24 | - | 2/3 2/5 2/16 2/17 2/24 | 210 | 2/16 twin GU 2/21 |
| sub 0x8ddf24 | - | 1/1 1/4 1/6 1/19 1/20 1/22 1/25 1/27* 1/35 | 1 f 10 12 16 301 31e 40e | see port status |

## Port status (2026-11-05, module builds clean; nothing tested in game)
Ported (module/em007_01_mv_a..e.c, s_moves rows in em007_01_moves.c):
- mv_a: charge 0x8db41c (7/3 10 24 25 34), charge runs 0x8d7f08 (2/2) / 0x8d8518 (2/10), stuck horn 0x8d9af8 (1/2:
  attack 40, item drop 100 %, GU's hunter scan 0xd3b154), horn out 1/27 (sub inline).
- mv_b: dig in 0x8da42c (1/28 29 32 33), underground attack 0x8dc13c (7/13 14 15 28 29 30 33); 4U's target-position
  rule `mb_target_pos` (kind 2 Palico and player slot 0 are stand-ins, see the file).
- mv_c: roars 0x8d9c9c (1/21 1/34) / 0x8d83a0 (2/7) (motion 0x404, his bank 4, since 0.4.1; 4U's radial blur
  0xc0819c and sound event 0x390f9c logged, not played: see 0.4.1), scrape 0x8da77c (1/31 -> 7/25).
- mv_d: walk 0x8d7d8c (2/0 21 25 26), run 0x8d81d0 (2/6 22), approach 0x8d93c4 (2/19 20 23), turns 2/3 5 17 24
  (sub inline, 4U records 0xe0e090 / 0xe0e0d0).
- mv_e: idle loop 1/1, one-motion 1/4 1/19 1/35 (his idle 0x40e, bank 4, since 0.4.1) and 1/10 (0x8da0f4, motion
  0x310).
- mv_f: double horn swing 0x8dabd8 (7/2 7/19), half-turn swings 0x8dbf80 (7/31 7/32; GU 0x770a0 = 4U 0x937298,
  C), 7/1 and 7/8 (sub 0x8db020 inline); mv_a: 7/4 7/21 (0x8db998, charge run into the thrust 0x213); mv_d: stalk
  0x8d89d0 (2/12 14 18, W+488 as the turn-rate accumulator in mb_state).
- mv_g: category 3: 3/1 (sub inline), 3/2 0x8d6a74, 3/3 0x8d6c80, 3/4 0x8d6e04 (GU 0xbf0f4 = 4U 0x922b6c, C; GU
  0x7cc08 / 0x7cd60 = 4U 0x93cda8 / 0x93ce98, S; end (0, 3) = GU slot 248).
- mv_h: category 6: rest 6/1 6/7, resting turns 6/3 6/13 6/11 6/18 6/19, waking 6/2, lying down 6/0 6/17, lying
  burrowed 6/8 6/9, burrowed run 6/12, burrowed travel 6/4 6/15 6/16 6/20 (end (0, 7) = GU slot 250, C; state
  flags GU 0xc2768 / 0xc2780, C; species height GU 0xbf6e8, S; the mound and dust trail since 0.4.1, see there).
- mv_f / mv_e: his attack twins ported too (GU's attack with Diablos' records): 7/0 7/18 0x8daa48, 7/5 7/22
  0x8dbbbc, 7/6 7/20 0x8dbd0c, 7/7 0x8dbe34, 7/9 0x8dae90, 1/20 (GU this+0x7588 = 4U W+0x78bc, C), 1/6 and 2/16
  (one motion), 6/0 6/17 0x8dc5b4.
- mv_i: the charge's spin turn 2/13 2/15 0x8d8cc0 (GU 0xb0c40 = 4U 0x936960, C; GU this+0x13b8 = 4U this+0xd58, C;
  root-move factor 0.8 as 4U, GU's Diablos uses 1.6), which resumes the charge as 7/26 / 7/27 (charge kinds 6 / 7:
  a setActionNow chain the closure script had missed).

## 0.4.0 (2026-11-05; static checks only)
Every action his table starts has a C handler (build log: "without a C handler yet: none"). Still on GU's Diablos
handlers (TWINS): 0/2 (idle, the same motion), 3/0 (g12 only; no attack in either game), and the chained 3/7 / 6/14,
which GU's own helpers (0xd3c7bc, 0xd41050) start with GU's work fields. 1/9 needs no port (only 1/7 chains it, and
1/7 sits only in his patrol, which GU's replaces); 1/25 sits only in GU-replaced scripts.
Open: the 7/9 stage object (0x6c3400, logged); the 4U W+0x978 flag and 6/16's probe / overshoot snap; this+68 clamp
of 3/1..3/3; camera ids 0 / 1 / 5 on GU's camera list. His effects: 0.4.1. Attack values: notes/plan.md 0.4.3.
Inline 1/22 -> 1/23 (sleep, W+0x790d, 4U 0x92213c) is not in his table's
reach (build log) but needs a look when category 1's area actions are checked.
Method for each: find GU's version in uEm007_00 (same motion constants and helpers) for the field map, port the 4U
code literally, his attack indexes through MB_ATK. 4U-only fields with no GU field live in `struct mb_state`
(em007_01.h).

## 0.4.1 (2026-11-05, his effects; static checks only)
- Sounds: nothing to build. GU's em007 sound call keeps 4U em099's bank-4 records (keys 0x00 0x01 0x04 0x0e 0x11 0x14
  0x15 0x18 0x19 0x1a 0x1e 0x1f 0x21 0x22 0x24 0x25), which 4U shares between Diablos and Monoblos (his 4U arc loads
  sound\call\em\em099, C). The 0.4.0 note "bank 4 has no GU sound tables" was wrong. So the roars (1/21 1/34 2/7) and
  idles (1/19 1/35) play his bank-4 motions 0x404 / 0x40e again, as 4U (0.4.0: his copies in GU's bank-0 slots).
- Effects (tools/build_em007_01_arc.py effects): PEL u = GU em007_00u (list 1: 20, list 2: 16) + his 66 4U em101_0
  records (list 1); 57 converted 4U EFLs in the Dunes' soil colour (median of 4U m17 areas 1..11); bank-4 PSL (field
  22) from his em101_4 motion events; banks 0..3 keep GU's PSLs (Diablos' animations: Black Gravios' rule, the user
  2026-11-02).
- Roar: 4U's radial blur 0xc0819c (uMhRadialBlurFilter) has no GU spawn helper (dalamadur dala_efx.c). His bank-4
  roar entry gets GU's air slot (PEL c 90 = cm202_050, joint 3, frames 109..151 of GU's bank-0 motion 4, the same
  animation) next to his own 4U slot (roar_air). DEVIATION, as Black Gravios' roar air (the user's choice there).
- Ground effect when burrowed, DEVIATION since 0.4.4 (the user 2026-11-05: GU's Diablos look): 4U posted em101_019 (a
  mound while he lies burrowed, 6/8 6/9, handle class work+0x84) and em101_020 (dust every 6 frames of the burrowed
  run / travel, 6/12, 6/4 6/15 6/16 6/20) through 0xc088d8 (group 76, elements 14 / 15); 0.4.1..0.4.3 shipped them as
  PEL records 4100 / 4101. Now the travels call GU's 0xa4a58(this, 2) at step 0 as GU's 0xd3eb74 does (common effect
  2 in this+0xb7c4, up to 3600 frames; GU's 0xa4878 reposts it on another ground type and finishes it at the slot), and
  6/8 6/9 post the same effect with GU's request into the old mound handle (GU's Diablos has no such action).
- The effects' end: 4U slot 45 0x8df784 releases the mound every frame unless the action is 6/8 6/9 6/10, slot 13
  0x8e1060 (the unit's cleanup) too (C). Ported as mb_mound_frame, every frame from moves_run whatever action runs,
  plus HP 0 (GU's death action runs outside slot 125; G); a trail of his ends there through GU's 0xa4a14 when the action
  is no travel any more. The handle is guarded as Black Gravios' laser handles (vtable of the post, state 1 / 2,
  transform pointers) and mb_state starts afresh in a new quest.
- Sonic bombs (0.4.4; the user's test of 0.4.3: no reaction, no 10/92 in the log). GU's path, C: a shell hit of type
  33 or 37..47 lands only on hurt volumes with bit 4 (0x16c43c; GU's bodydata, shared: 8 volumes, bones 3 103 101 1 2
  140; bones checked with the skeleton); frame code 0x998d4: rec+0x444 hit, status 32 off, rec+0x3a8 & 16 (dtbase +0x6c,
  shared), class slot 145 0xd3a5c8: no area move (this+0x73f0), target mode 4, **not enraged** (rec+0x518 != 1); then
  rec+0x3ae = 11 -> 0x9bfd0 -> (10, 92) for mode 4: GU's table (motion 315) and start code 0xd358f8. 4U has the same
  rage rule (0x8e0694). Nothing on this path reads the action number, his variant or his data: his hits should
  register as Diablos'. His motion 0x20f and GU's 7 hold the body at the same height (bone 0: 213..337 / 270..320), the
  burrow height is dtbase +168 (shared). Not found why the test showed nothing; his rage (4U: 600 damage, 3600 frames,
  9 % of his HP) is the first suspect (G), so the action line logs target mode and rage, every shell hit while burrowed
  gets a line, and moves_run tests the same conditions after GU's frame code and reacts itself if GU's did not (logged
  "did not react, reacting here").
- Sonic bombs, 0.4.5 (the user's test of 0.4.4: they work, but sometimes he sinks away and pops up without an animation;
  log 00:05:05, 00:07:50). While he lies burrowed (his 6/8, 6/9) these handlers set rec+0x3a2 each frame, and then GU's
  frame code drops pending reactions (0x98dd4), so only the module's own check fires, from his 6/216. It called the
  reaction and then let the old handler run in the same frame, on steps the reaction had just cleared: step 1, motion 1,
  the table of 10/92 never started motion 0x315. GU's own path from 6/211 plays 0x315 -> 10/123 -> 10/124 correctly.
  sonic_check now runs first in moves_run, and the action and steps are read after it.
- Motion attacks, 0.4.5 (the user: no block reaction while he digs towards a blocking hunter). 4U uEm101 slot 48 0x8df784
  runs every frame and makes 24 attack calls by motion (table in em007_01_mv_j.c): feet, tail and body while walking or
  turning, the burrowed travel's hit (attack 46: root sphere r 330, power 0, throws a hunter above him; blocking it costs
  stamina) and the burst (56 or 21, then 33). None of them were ported, because the handlers do not call them. GU's slot
  130 0xd38c0c has attacks only on motions 5, 11, 12 (with Diablos' records), so the hook skips it there and lets it run
  on the others for its shakes and ground effects.
- Resistance: GU has no value that weakens the reaction. (10, 92) adds 1 to work+0xa (GU's tail caps it at 2), and the
  tail's burrow cooldown work+16 (read by AI through slot 133 case 1, with the timer work+12) shrinks with it: 1200 / 900,
  900 / 600, 600 / 300 frames. It runs for him as for GU's Diablos, because (10, 92) and gu_tail are GU's code. His 4U
  table has its own burrow rules: whether it asks slot 133 case 1 was not checked.
- Not ported: 4U's ground kind (the effect's material variant; efl4u2gu has no GU place), the 7/9 stage-object
  effect, 1/34's sound event 0x390f9c.
- To check in game: roar (sound, GU's blur on the head), idle, the dust of digging in / out and the scrape, the mound
  and its end (also when a sonic bomb drives him out), the dust trail (stays behind him?), effect sizes (GU's posts on
  the monster take its model scale: em089 / Stygian notes), the frame rate.
