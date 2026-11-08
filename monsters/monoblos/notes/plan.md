# Monoblos port: plan (draft 2026-11-04, issue #16)

Source: MH4U em101 (class uEm101). Target: GU Diablos' class uEm007_00, **variant 1** (GU ID 0x107, arc
`nativeNX/arc/enemy/em007_01.arc`). Process: notes/porting-guide.md, built on v1.8.0 (main 8ddac17) with the save
store core (notes/save-store.md: `save = "lease"`). White Monoblos (4U em102) is left for later: its only 4U quest is
in the Everwood (stage 13), a map GU does not have (user, issue #16). Maintainer (issue #16, 2026-11-04): another,
bigger project is already working on the Everwood, so it stays out of this port. Confidence: **C** confirmed in code /
data, **S** strong, **G** guess.

**Status (2026-11-07):** 0.4.7 (the PR #17 review, below) on the save store core (the user's go, 2026-11-05: "build Monoblos in, with his 4U AI and
attacks, like Black Gravios"). Played solo on Ryujinx: quests 10784, 10785, 11452 (logs of 2026-11-05 and 11-06), two real
hunts of 10784 through the store. yuzu / Eden and the PC recomp not run. Not in a saved log yet: the village quests 1057..1059,
a broken horn, sleeping and eating, a kill in a capture quest. Test log lines: "mbport: em007_01 ..." (actions / motions),
"mbport: parts", "mh4uport: monoblos leases save slot". The dated sections below are the build's history.

## Phase 0: identification
- 4U em numbers (C, 4U emName): 99 Diablos, 100 Black Diablos, 101 Monoblos, 102 White Monoblos, 119 'Diablos'
  again.
- 4U class (C, tools/a4u.py): unlike Black Gravios (no uEm041 DTI, run by uEm038), Monoblos has its own class.
  uEm099 = DTI 0x10b7dd8, vtable 0xe6a438, slot-44 action dispatch 0x8d41b8. uEm101 = DTI 0x10b7e88, vtable 0xe6a5bc,
  slot-44 dispatch 0x8df448. Both have the same parent DTI (0x10b8770) and size (36240 B). Among the first 99 slots, 26
  differ (1, 4, 5, 6, 9, 16, 36, 39, 40, 44, 46, 47, 48, 50, 51, 54, 57, 60, 61, 62, 66, 76, 77, 78, 79, 98), among
  them 40 (state frame), 44 (actions), 47 (action start), 50 (parts), 51 (AI conditions). Where the vtable ends is
  not settled yet (the slot scan ran into the following data).
- 4U arcs (C): dump/romfs/data/em099.arc .. em102.arc.
- GU (C, registry pairs 0x1597ea4): Diablos = em 7 (ID 0x7, index 114), Bloodbath Diablos = 0x407 (index 115).
  GU arcs: em007_00, em007_04. The variant ID 0x107 is free (not in GU's pairs, no arc, no port claims it).
- GU lacks Monoblos (C: no GU name or registry entry).
- GU class (C, 2026-11-05, registry DTI table 0x1731e2c -> static init 0x50410 "uEm007_00" -> DTI vtable 0x17328a0 ->
  newInstance 0x4e308 (size 0xcaf0) -> ctor 0xd34c50 -> vtable symbol 0x17a0594, vptr 0x17a059c): slot 125 (actions)
  0xd35e58, slot 127 (remap) 0xd35318, slot 129 (action start) 0xd3545c. Slot 125 switches on the category
  (this+0x73e0, 0..17), calls the category's dispatcher (0 d360d0, 1 d36310, 2 d368fc, 3 d36fb4, 6 d37044, 7 d37454,
  10 d37f10, 11 d3884c, 13 d389d8) and then runs a common tail at 0xd35f9c (unlike Zinogre's tail-branch switch).

## 4U quests with Monoblos (C: quest00 / 01.arc, every spawn list; no DLC extdata on this PC, not checked)
| 4U | board | rank (C: his materials in its rewards) | stage |
|---|---|---|---|
| m00801 | Caravan 8 | High (Carapace, Thoracic) | 17 Dunes (day) |
| m00818 | Caravan 8 | High (Carapace, Thoracic) | 18 Dunes (night) |
| m01018 | Caravan 10 | G (Cortex, Chine) | 17 Dunes (day) |

- GU has the Dunes as stage 5 (4U 17 -> 5, porting-guide 5b), no night Dunes (G: m00818 on the day Dunes).
- White Monoblos (em102): m01021, Caravan 10, stage 13 Everwood (C). Not in this port.
- No Gathering Hall (multiplayer) quest has him in these files; his G materials come only from G carves / breaks
  (s4, BUI4: Cortex, Chine, Scarlet Stouthorn) and m01018's rewards (Cortex, Chine) (C, 2026-11-05).

## Quest ranks and hub quests (0.4.2, the user 2026-11-05)
The user: "make the ranks make sense in MHGU's single player for High and G rank; on that basis build multiplayer
quests for High and G rank; mind that hub HP differs from single player". Until 0.4.1 all three sat on village ★10
High Rank and the ★8 ones divided by 4U m01025 (a G quest): HP x0.91 / attack x1.50 at village HR, under GU's own
Diablos there (x1.21 / x3.30); 1059 (4U G) was High Rank, so his G carves / breaks (Scarlet Stouthorn) had no
source. GU facts (C, read from GU's quest files): questData +0x13 tier 3 = High, 5 = G; GU's village ★10
holds both (29 High, 16 G quests); every village ★10 single hunt uses rows 37 / 66 / 19 (High) or 51 / 97 / 85 (G);
GU's hub Diablos hunts: HR7 q10768 (49 / 82 / 84, x1.57 / x4.70), G4 q11448 (107 / 108 / 97, x3.85 / x7.90).
| GU | 4U | place | template | rows | HP / attack |
|---|---|---|---|---|---|
| 1057 | m00801 hunt | village ★10 High | q1002 (stage 22 -> 5) | 37 / 64 / 19 | x1.21 / x3.20 |
| 1058 | m00818 capture | village ★10 High | q1036 | 37 / 64 / 19 | x1.21 / x3.20 |
| 1059 | m01018 hunt | village ★10 G | q1012 (stage 2 -> 5) | 51 / 95 / 85 | x1.63 / x6.00 |
| 10784 | m00801 hunt | hub HR7 | q10768 | 49 / 81 / 84 | x1.57 / x4.60 |
| 10785 | m00818 capture | hub HR7 | q10706 (stage 12 -> 5, as Stygian's 10779) | 49 / 81 / 84 | x1.57 / x4.60 |
| 11452 | m01018 hunt | hub G4 | q11448 (stage 22 -> 5) | 107 / 108 / 97 | x3.85 / x7.90 |
Rows = GU's base x r, r = 4U Monoblos / Diablos at the same tier (m01018 / m01025: HP 1.00, attack 0.967, C; the
High quests take it too: 4U has no High Diablos quest, G). The hub quests are not 4U quests (a DEVIATION the user
asked for): 4U text, spawns and rewards of the same 4U quest. IDs 10784 / 10785 / 11452 checked free (C).

## 0.4.3 (2026-11-05, after the user's test of 0.4.2: log 15-18-36; he used the instant-clear cheat, so no tally)
- Log (C): HP 6572 in 10785 = 4186 x 1.57, 16116 in 11452 = 4186 x 3.85; his AI, handlers and effects ran, no "no port
  yet" line. No lease / tally lines because the cheat ended both quests at 97 % / 99 % HP: the store is still untested.
- Emergency quest: questData +0x16F bit 0 = urgent (C: 28 quests, one per star); q10768 is HR7's. 10784's template is
  now q10728, a plain HR7 Dunes hunt (rows and box still q10768's); the build asserts no template has the bit.
- Supply boxes: every box starts with the Map(s) only (map_only_start; C: all GU HR / G boxes read); hub boxes = GU's
  (supp_tpl: q10768, q10706, q11448: 4 Maps, 4 players); 1058's Hot Drinks -> Cool Drinks (day Dunes, DEVIATION).
- Icon: icon_4u 111 -> 110. Board values from 98 up are atlas index + 1 (allocations.toml Tigerstripe, Stygian); cells
  108..111 = Diablos, Black Diablos, Monoblos, White Monoblos (C, rendered).
- Attacks (build_em007_01_arc.py gu_retunes): GU's changes of 4U Diablos records go to his records equal but for hitsize
  group, GU's code byte and the knockback bits: M16 M57 <- D5 (55 -> 70), M41 <- D6 (40 -> 55), M30 <- D7 (55 -> 65), M35
  <- D9 (60 -> 70, byte 6 3 -> 2), M42 <- D24 (40 -> 55), M48 M49 M51 <- D52 (byte 30 0 -> 5, role not traced, G). No such
  twin for D4, D26, D29, D44: his 4U values stay.
- Platforms (Ryujinx, yuzu / Eden, PC recomp; only Ryujinx tested): no new hooks; all GU addresses through MAIN / FN;
  the mound guard has no address range (the heap differs per platform).
- Open: Black Gravios' ptr_ok has the same address range (its author's code; not changed here).

## 0.4.8 (2026-11-08, after the user's long hunts on 0.4.7: log 13-52-00, quests 11452 and 10784 to the end; 13-39-17, 11452)
- **What the logs show (C).** 37 of his 4U actions ran (plus GU's engine actions below), among them 6/0 6/3 6/4 6/8 6/16 7/13 7/31
  1/20 1/21 1/28, which the maintainer had not seen; no "has no port yet" line. `mbport: parts`: horn broken, back broken, tail cut
  (the horn for the first time in a log). Name entry 221 (`monster name entry 221 = Monoblos`). He slept for the first time: at 6 %
  in 10784 he went to area 5 and ran s123 (2/2, 1/5) there. His area moves while burrowed and tired (tm 4) run GU's engine scripts
  g1 s126 / s127 with GU Diablos' handlers 6/18, 6/42, 6/45 (area_act_tbl, as s123 / s124 for sleeping and eating): GU's engine
  replaced 4U's rest group 16 (see 0.4.6, "Eating and sleeping"), so these stay GU's, a DEVIATION as 0/2 3/0 3/7 6/14.
- **Fixed: his ways to eat and to sleep (C).** At 6 % in 10784 he went 7 -> 3 -> 5, but his 4U hops are 7: 2 / 10, 3: 1 / 4, 5: 4.
  routes_em007_01 had kept area_link kinds 2 (hunger, 0xb82cc) and 4 (weakened, reason 1, 0xb870c) as GU Diablos' rows. Now
  kinds 1 and 2 are his 4U hop table and kind 4 his way to area 5 in GU's sparse form (each row names only the areas on
  that way): 7 -> 10 -> 4 -> 5, 2 -> 7 -> 10 -> 4 -> 5, 1 / 3 -> 4 -> 5. Only enemy\area_link\em007_01 in his arc and his
  data file's version byte change. Not played yet.

## 0.4.7 (2026-11-07, the maintainer's test of PR #17; static checks only, not played yet)
The review: 29 of 79 actions seen (unseen: all of category 3, most of 6, 7/1 7/8 7/10 7/13 7/21 7/24 7/31..34, 1/1 1/4 1/10
1/19..21 1/28 1/29 1/31, several 2/x), slow idle turns in the fight, rage maybe too fast, name entry 109 = save slot 109.
- **Fixed: g0 s0's two natives (C).** cmdtbl() counted g0 s0 as GU-made (only its area step is GU's), so its `00 06 08` (lying
  burrowed, when op 0x0c = 4 at a think's start) and `00 01 23` (1/35, op 0x68) stayed raw GU numbers: GU's base rest 0xd37270
  ran for 6/8 and GU Diablos' dig-in 0xd3c3c8 (motion 0x425) for 1/35, with GU's fields, where his 6/216 / 1/243 belong. Every
  think starts in g0 s0, so each burrowed phase began on GU's rest. Now converted; the built table differs in these two tokens.
- **Not his normal table's (C).** 7/10 7/33 1/31 sit only in g1 s47 / s50 / s59, called only from g0 s12 s15 s20, which only
  White Monoblos' case 102 of g0 s4 reaches (0.4.6 section). 7/8 (g1 s25 s27), 7/21 (s55), 7/24 (s58), 1/1 (s5) sit in scripts
  no script of any group calls, and no uEm101 code sets the think fields (4U setThink 0x93d584 and every W+0xb0c / 0xb0d writer
  are base code: 0x9184c0 0x936100 0x9412f0 0x944540 0x945d40 0x946130 0x950b4c 0x954460): 4U's Monoblos never runs them either.
- **Event lists (S).** 7/1 1/10 (g8), 1/19 (g9), 1/20 1/21 7/31 7/32 (g13), 1/4 3/x 6/2 6/7 6/15 6/20 (g2..g6, g11, g12, g18)
  run only from the engine's think lists. GU 0x8282c picks the same group numbers on the same tests as 4U 0x945e60 (13: a
  timer > 0, 8: rec+0x59c / 0x5a4 > 0, 14: category 16, ...) and GU's Diablos table fills the same groups: not his code. The
  action log names the group / script of every action (`mbport: em007_01 action ... script gN sM`): the next log shows whether they come.
- **Burrowed actions (C).** 6/3 6/4 6/8 6/9 6/12 6/16 run only when op 0x0c (state rec+0x1ba, 4U W+0x1c8: the same handler in
  both) is 4, set by the burrowing 6/0 / 6/17 end (slot 250) through g1 s62; the selectors reach that from g0 s17 (op 0x87),
  s24 (cond 4 case 3) and s10 / s11 / s14 (target class 0x4110). With the g0 s0 fix the phase runs his handlers from its start.
- **AI ops compared (C).** 4U interpreter 0x94f488 vs GU 0x837ac: 0x0b (distance row) and 0x0c (state) read the same; 0x24 =
  tired (4U 0x92e998: W+0x51c in {2, 3}; GU 0x816f0 also takes rec+0x505 = 1, not when enraged), 0x1c = enraged (4U 0x954e48
  W+0x530 = 1, GU 0x81744 rec+0x518 = 1); slot 133 (cond) = 4U slot 51 0x8e0804 case by case (2 motion 0x20f, 3 target, 4 stage
  object, 11 counter; 5..10 answer 0 in both).
- **Turns: 4U as it is (C).** His 2/3 (the turn of nearly every attack script after the op 0x1d angle test) is 4U 0x8dda24 case
  3: record 0xe0e090 (motions 0x09 / 0x0a, window 0..90) with flags 1. 4U Diablos' 2/3 (0x8d1594 case 3) takes 0xe0e034 (0x0b
  / 0x0c, window 2..20) and GU's Diablos the same (0x16a2d50, d36ca8). So 4U's Monoblos turns slower than Diablos; not changed.
- **Rage: 4U as it is (C).** 4U etd word 14: Monoblos 600 / 3600 frames, x1.3 / x1.5; Diablos 500 / 5400, x1.25 / x1.4 (GU's
  Diablos = 4U's). His values stand.
- **Name entry 221** (allocations.toml): 109 = 'dummy5' is also what GU reads for save slot 109 (the Dalamadur tails' tally
  slot); the second list's 'dummy1' is no save slot. tools/alloc.py NAME_DUMMY as in the later ports.
- **GS line "(4U)"** after every name of his GS line (gear_weapons_em007_01.py LABEL_4U), all languages (the maintainer's
  choice). Black Gravios' ptr_ok lost its address range (1.0.1).

- **The log of 0.4.7 (2026-11-07 20-15-35, quest 10784 = HR, a 7-minute hunt; C for the log and the table).** The user: "gräbt glaube
  ich immer noch viel zu wenig ein". He dug in 4 times by the dig-in attack (g1 s49: 7/236 1/241 7/238, every time s49 was picked, so
  cond 11 answered 1) and lay down burrowed 4 times (g1 s62 from s14 / s15 / s16: 6/208 6/211 6/212 6/216, then 7/217 or a sonic bomb),
  8 of 52 picks = 15 %. His 4U table picks the selector by quest rank (g0 s4: op 0x79 case 0x1041, mode 0, op 0x6a case 5 -> g0 s14, else
  g0 s11; GU 0x3a8d68 gives 3 for HR, 5 for G, as 4U's quest byte): g0 s11 (HR) gives a burrowing script 16..24 % per pick by distance row,
  g0 s14 (G) 29..51 % (g1 s57 only there). So the HR rate is 4U's; at G rank (1059, 11452) he burrows about twice as often. The
  log reached 29 of his table's actions, no "has no port", 6/216 runs his handler. Not changed.
- **How often he burrows, HR against G (2026-11-08; C for the table, the logs as counted).** The maintainer's review says he burrows
  too little; this is what 4U's own table gives. A pick = one script of group 1 started by the selector (g1 s41, called by s52..s56,
  and g1 s62, called by s14..s18, are not picks of their own; nor the unaware phase g4 / g5 / g1 s121 / s122). Burrowing scripts:
  the dig-in attacks g1 s48 / s49 / s57 and every script that starts with the lie-down g1 s62 (s14..s18, s21, s26, s28..s30, s37,
  s38, s61). Their share of the weights of each row (his 4U cmdtbl as built, op 0x24 = tired, op 0x1c = enraged, op 0x0b rows
  0..3 and default):

  | state    | row 0 | row 1 | row 2 | row 3 | default |
  |----------|-------|-------|-------|-------|---------|
  | HR (g0 s11), normal  | 20 % | 16 % | 17 % | 24 % | 20 % |
  | G (g0 s14), normal   | 29 % | 40 % | 44 % | 51 % | 49 % |
  | HR, enraged          | 23 % | 17 % | 24 % | 19 % | 17 % |
  | G, enraged           | 32 % | 39 % | 51 % | 48 % | 47 % |
  | tired (both ranks)   | 24 % | 16 % | 21 % | 21 % | 33 % |

  About 20 % of the picks at HR and 45 % at G: 2.2 times as many. The tired rows are the same in both selectors. In the logs:
  quest 10784 (HR, log 2026-11-07 20-15-35): 8 burrows in 52 picks = 15 % over 405 s, 1.2 a minute; quest 11452 (G, log 2026-11-08
  08-38-41): 5 in 13 picks = 38 % over 109 s, 2.8 a minute (a short hunt, few picks). Both match the table. So he burrows as often
  as in 4U at each rank; GU's own Diablos family is not a measure for him. Nothing changed. If the maintainer wants him to burrow
  more at HR, that is a deviation from 4U and their call.

## 0.4.6 (2026-11-06, after the user's test of 0.4.5: log 11-02-46 and a screenshot)
The user's test: smithy order, his hit shapes and Black Gravios' Notes page are fine; red eye and pink veins from the start of
the fight, still; a 4U video (youtube NDpzz4MgFRo, no frenzy in it: 1:57 and 2:00 show his face without either).
- **The pink eye, the real cause (C for the code and data, S for "frenzy").** His texture em101_04_BM holds, by the meshes' UV
  ranges: amber eye = group 2, red eye = group 50, pink veins = group 51 (all material 'm01_eye'), and a dark red plate =
  'm02_angry' (group 0). So 0.4.5's reading was wrong: the rage material never was the pink. His 4U rows (emd +0x88; 4U
  em099 has the same on its 50 / 51; GU's Diablos model dropped both): group 2 hidden and 50 / 51 shown under cond 10
  (evaluator 0x948378: W+0x53a or W+0x7e80 bit 5; G -> S: the frenzy look, as Tigerstripe's and Stygian's group 50), all
  three hidden when dead (cond 11).
- **Why they showed (C).** Every group starts drawn (0xba258), only a monster's own code switches them. uEm007_00 does it in
  slot 132 0xd39fc8, whose first test returns for variants other than 0 and 4 (0xd39fe4). HIDDEN_GROUPS sat in state 0, and
  nothing reads state 0 for him: GU's 0x6f5a4 (every frame from slot 10 0xae3e8) reads only the numbers slot 118 gave it
  (0xd35130: closed 1, open 2, other -1; slot 114 returns 0). GU's Gravios, Zamtrios and Najarala classes apply state 0 in their
  own function, which has no such test before it (C: 0xd27128, 0xf66984, 0xf89c74), so a variant's hidden groups stay
  hidden. Stygian's issue #8 had the same symptom when its slot 132 was skipped (em057_01_fix.c).
- **The same cause hid every break (C).** All groups drawn: horn (102) with its stump (3) inside, tail (101) with its stump (4)
  inside, back (103) never gone. GU's state numbers were wrong for him as well (his groups are not Diablos': PART_ROWS).
  Fix: states from his rows (build_em007_01_arc.py PART_STATES: 1 / 2 eyes, 5..10 breaks), hook on slot 132 (em007_01_mat.c):
  GU's eye rule (rec+0x5d02, as 0x6f5a4, which sits behind a flag of the enemy manager), part 6 rank >= 2, part 0 rank >= 1, tail
  severed, every frame, logged on change (`mbport: parts`). A closed eye hides group 2, as GU's hides Diablos' 5 (4U leaves it
  under the lid: no visible difference). Simulated against his rows: spawn, each break, all breaks, dead: the same groups.
- **White Monoblos (C), the user asked.** Model, textures, attack and body data: em101.arc only; em102.arc has its own. The AI
  table is one file for both (em102.arc carries enemy\em101\data\em101_cmd): with the op-0x46 cases reduced only g0 s4 differs,
  and only in which selectors it jumps to (normal g0 s22 23 24 6 7 16 14 11, White 25 26 27 18 19 20 15 12). Reached from the
  roots through scripts: actions only White 1/31 2/13 2/15 2/16 7/10 7/33, only normal 7/18, 72 both. His built table reaches no
  White-only selector, script or action (scratch check), and no log shows those numbers. In the class the only species test is
  0x8d9f94 `cmp #101` in 1/7 (his patrol, which GU's replaces). 2/13 also comes from the charge's own code (mv_a.c), shared by
  both in 4U, so it is no White move as such.
- **Eating and sleeping (C for the code, not seen in game).** Places: sleep area 5, eat area 7, as 4U's slot 66 0x8e0bd4 and GU's
  Diablos (map_info words 2 / 1). GU replaced 4U's rest group 16 by its engine: hunger move 0xb8034 (from 0xb882c, needs word 1
  or 3), weakened move by area_select Status 4 (his: first step toward 5), then area_act_tbl kinds 2 / 3 (entry 114, GU's scripts
  in his table): s123 `2/2 1/5`, s124 `1/37 2/2 1/3`. They run GU Diablos' handlers: 1/5 0xd3a994 motions 0x12, 0x14; 1/3 0xd3a8cc
  motion 0x10. His 4U handlers play the same ones (sub 0x8ddf24: 1/22 motion 0x12 -> 1/23 motion 0x14, 1/25 motion 0x10), and his
  banks 0..3 are Diablos' animations. Eyes: 4U 1/22 calls 0x92213c (cond 0, GU's 0xbd650); GU's 1/5 does not, GU sets the same
  flag rec+0x5d02 in its base code (0xaf124; when: not traced), and that flag now also hides his eye through state 1. No log has
  s123 / s124: the only real hunt (10784, log 21-11-28) went 18 % 7 -> 10, 12 % 10 -> 4 (the weak route; 2/25 from 14 %), dead a
  minute later, so he never reached 5. To test: hurt him to about 15 % and wait.
  Group 12 (his 3/0 chain, `01 00 05 09 00`) keeps 4U's point number 9 (GU: the area's flags-0x10 point for his group, every area
  of his has one, C); GU's Diablos has 22 there (first area_patrol point). Left as 4U's: both exist.
- **Core: the data pool (C).** With his data file the module's pool held 261280 of its 262144 bytes, and he loads last: any data file
  growing by 865 bytes would have left him on his donor's manifest, as a plain Diablos, with one log line. So 512 KB now (tools/alloc.py
  DATA_POOL), and module/build.py refuses a build that does not fit (notes/porting-guide.md). His files did not change for it.
- **Logs of 0.4.6 (C, 2026-11-06: 12-56-19 and 16-30-40; quests 10784 and 11452).** `mbport: parts` switches for the back and the tail;
  the horn was not broken in either. 29 of the 77 handlers in his AI table ran, plus the chained 7/237 and 7/238, and no "has no port
  yet" line. A second real hunt of 10784 went through the store (notes/save-store.md). Still no s123 / s124 and no area 5 in either.
- **Core: a record's size on the Notes page (C).** After that hunt the store held smallest 98 and largest 114, and his page showed 0
  and 0. GU's 0x67310 turns a record into its crown and cm by searching em_size_scale_data for the ID's registry index, and a ported
  index has no element. Fixed by the core's hook size_lookup (module/save.c, notes/save-store.md), for every ported monster: his page
  shows his records now (the user, on screen, 2026-11-06). His files did not change for it.

## 0.4.5 (2026-11-05, after the user's test of 0.4.4: log 21-11-28; static checks only, not played yet)
- **Hit shapes.** His 24 attacks tied to motions were never ported (actions.md). His hit capsules had the far end in the
  wrong place (`emdata4u.hitsize`: GU's record has 4 more bytes before off2, proof in notes/data.md). His own 4U hurt and
  camera volumes replace GU Diablos' (fields 30 / 31: one centre horn and a frill; zones and parts number the same).
- **Hitzones: checked, nothing to change.** dttune +0x8e = 4U etd word 7, 8 rows x 10 B, his rows are 4U em101's; GU
  Diablos' are 4U Diablos' (no GU retune to carry over); zone numbers equal (C).
- **Pink glow: WRONG reading, see 0.4.6.** 'XfBA1__m02_angry' (type 2) and 'XfBA1__m01_eye' are BSBlendAlpha in 4U; the build
  took them through the additive 'add' template with alpha 1 and nothing started the rage material's animations. Now: template
  'blend' (GU em009_00 mat 4), 4U's constants (eye unlit, rage material lit), it starts at alpha 0, and em007_01_mat.c ports 4U's
  material code (0x8d9930, 0x8e06cc): 'Angry_Start' in rage, 'Angry_End' after it. Right in itself, but not what the user saw.
- **Sonic bomb teleport.** See actions.md.
- **Notes:** Black Gravios took entry 128, he moved to 129 (unreleased; these entries leave no trace in a save).
- **Smithy:** see below, the 0.4.4 code had no effect.

## Shiny drops: checked, nothing built (2026-11-05, the user asked)
The mechanic is the same in both games (C): item drop 0x911f58 (4U) = 0xac0ec (GU), chance % as an argument, a counter of
drops left (4U W+0x7a64, GU rec+0x5d54, start = dtbase block +0x94 byte 0, 4U 0x91df20 object +0x60: Diablos / Monoblos
3, Gravios 2, Zinogre 3, Dalamadur 2, Zamtrios 100) that a lost item gives back (GU 0xa4d60), three items at a time, the
item from the monster's shiny table (hagi header byte 14 + set; 0xff = nothing). Total damage plays no part. The triggers
are single moments per monster: reaction tables with op 24 (`{24, chance}`, interpreter GU 0x9f7cc = 4U 0x931fb8) and
direct calls in the class (111 in GU, 71 in 4U). 4U uEm101: stuck horn pulled (ported, em007_01_mv_a.c), two reaction
tables at 100 % (0xff9c70, 0xff9808; S: falls). GU's Diablos: stuck horn, and 10/167 (start code d35930, 100 %), no table.
Ours: shiny tables are there for Monoblos (s2, s4), Black Gravios (s2, s4), Stygian (s2, s4), Tigerstripe (s4), Gogmazios
(s4, two sets), counters as above. Hosted monsters keep GU's triggers for GU's action numbers. Dalamadur and Shah: hagi has
no shiny table and no trigger is ported (4U: em90 has two sets of 3 rows, one call at 0x76b340), so they really have none.
To see in a test: module/port.c logs every call for a ported monster ("item drop call").

## Smithy order (core, built 2026-11-05 with 0.4.4, the user asked; rarity fixed in 0.4.5)
GU's builder 0x6f9438 walks the create records in order and lists entries {u16 record, u8 sub, u8, u16} at this+204
(count this+98, 1280 slots); the "listed" bits in the save are keyed by record index x 4 + sub (0x5249f4 / 0x524980, 576
records per armor part: head 575 with him, so 1 left), set in the builder's loop. module/gear.c smithy_list_c (hook on
the exit 0x6f9644) moves ported entries to their rarity among GU's, in the list only: all readers go through the
entry's record number, so record indexes and save bits stay, with the mod and after removing it. GU's entries keep their
order. GU's armor and weapon lists run by ascending rarity up to the highest, then a tail of low event gear (survey, C:
all 5 armor parts and all weapon classes), so a ported entry goes before the first GU entry of a higher rarity outside
the tail, with none before the tail, without a tail last. Rarity = the gear object's vtable slot 7 (vt+0x1c, as GU's own
call at 0x6f92ac; armor record +0x73, weapons +0xf, both mRare, C). 0.4.4 called slot 3, which returns 1 for everything
(a walk over the vtable that stopped at a small PLT address), so every entry looked equally rare and his stayed last.
Decorations stay as they are. The 576 limit needs its own answer before the next monster with armor.

## Hunter's Notes past the save map (core, built 2026-11-05 with 0.4.4)
All 128 bits of S+0x35b0 are taken (GU 123 + 5 ports). Entries from 128 (Black Gravios 128, him 129) have no bit:
module/notes.c shows them as soon as any quest of the monster is cleared (the cleared map S+0x42c) and writes nothing, so
a save without the mod holds no trace. The two talk loops, the only writers of the map, stop at 128; the list screen, its
NEW mark and 0x524728 are hooked. C for all code sites of 0x35b0 / 0x35c0; the user's test of 0.4.4 showed his page.

## First-sighting scene: feasibility only (2026-11-05, the user asked; not built)
How GU does it (C): one arc per scene, arc/ev/000..083.arc: GUI\01_quest\demo\boss_demo + its font + an SDL (type
0x4c0db839, tools/sdl.py reads it), 450..565 frames, objects TestCamera (keys), MonsterUnitConductor (mGenus, mSpecies,
mZakoFlg, mMotionNo, mFrame, mSpeed, mScale, mPos, mAngle), DemoControler (mUnitActiveFlag, stops the units),
DemoFestaGUIScheduler (boss_demo, FlowId 3 -> 5, msgType, PosOffset), SoundControl (SE 950 / 951). The scene belongs to
a quest, not to the monster: table 0x15a06fc (107 x 12 B: u8 kind, u8 event, u8, u8 area, u8, u8 special, 2 x 0, u32
quest; about 20 code sites, bound 107) names quest + area -> event; 0x14c7dc plays a row of kind 1 whose quest and area
are the current ones and whose bit is clear in [0x18570d0]+0x64 (row index, set at 0x14e4f4 afterwards, saved through
0x3df378); 0x14fcbc requests arc kinds 51 (ui\questUIDemo_lang) and 68 (ev\NNN). GU's Diablos has none: no event names
genus 7 (genera with one: 1 2 3 8 9 11 12 14..20 22 30 32 37 45..47 56 57 60..63 66 68 71 72 77 79..86 88), so there is
no Diablos scene to clone; any other event is a template (S).
For him it would take: ev/084.arc from a template (mGenus 7, mSpecies 1, his roar 0x404 as mMotionNo 1028, mPos / camera
keys moved to his Dunes area), a table copy with his rows (as notes_list: literals + bounds, or a hook on the two
lookups), and his name. Save: no new bit needed if "played" comes from the quest being cleared (as his Notes entry), else
a bit past row 106 of GU's map (to check how many words that map has). All platforms: data and table only. Open (G):
what msgType maps to (name text, font glyphs in all languages), whether MonsterUnitConductor finds a variant 1, and the
camera keys need play tests.

## IDs (allocations.toml)
- Save slot: `save = "lease"` (save store core, notes/save-store.md): the pool [105, 111] is full; the maintainer
  rejected a monster without a slot (issue #16, 2026-11-04: the quest-end tally and the size reads have no bound
  check, C). With a lease it borrows a free slot per quest and its counts go to the mod's store.
- Name entry 109 ('dummy5', the last free monsterName entry; C: no monster names it).
- notes_entry 129: past the save map, no save bit (section "Hunter's Notes past the save map"; 0.1.0..0.4.3 had none,
  0.4.4 had 128).
- Registry index 145, file IDs 0x10940..0x1097f, ui_icon 205 (C: free in allocations.toml, 2026-11-05).
- Checked in GU code (2026-11-04, C): 53 calls of the id -> index lookup 0x50b64 (returns -1 when not found).
  The six u16 save-tally accessors (0x5230b8, 0x523110, 0x526da4, 0x526de0, 0x526e10, 0x526e50: hunts at +0,
  captures at +0x112 = 137 x 2) test `cmp #136` and answer 0 past it. The quest-end tally 0x3a75c8 (+1 at
  obj + 0x114 / 0x116 + index x 8) and its reader 0x3a3930 test nothing (module/save.c handles the lease there).
- GU registry index 133 (ID 0x57, em087_00) is a real boss (C): questData of gq2.arc, q0011432 and q1011030 name
  it. Not a free slot.

## Phase 1 (2026-11-04; scratch scripts arc_cmp / mot_cmp / gu_mot / varmap / varmap2 / motmap, not in the repo)
- Assets (C, md5 per arc entry): em101.arc shares with em099.arc 15 of its EFLs, the base texture, the camera list
  and every sound (sound call em099, bank snd_em099 and its waves). Own: model (40 bones, as em099's), tail, textures,
  em101_cmd, MEF em101_0, ef_em101 and 9 EFLs (002 007 011 014 018 021 022 024, 025 = em099_024).
- Motions (C, frames + tracks + buffers compared, events not): banks 0..3 hold the same animations as em099's at the
  same indexes (28 / 20 / 10 / 30). Bank 4 is Monoblos' own: 13 animations (indexes 4 14 20 21 24 25 26 30 31 33 34
  36 37), none in em099 / em100 (Black Diablos ships em099's banks) and none in GU em007_00 / em007_04; White
  Monoblos (em102) ships em101's banks. Monoblos' bank 0 lacks em099's 4, 14 and 39: his code asks for bank 4's 4 and
  14 instead (0x404 roar, 0x40e idle; their frame counts equal em099's 0x004 / 0x00e: 293 / 343).
- GU motions (C, 2026-11-05, frame counts per slot): GU em007_00 keeps 4U em099's numbering in banks 0..3 (every 4U
  animation at the same index with the same frame count; GU re-encoded the data, no byte match) and adds bank 0
  index 21 (307 frames). GU's manifest field 8 (bank 4) is -1. GU's uEm007_00 still asks for bank-4 motions in some
  handlers (0x418 d3c128, 0x425 d3c3c8, 0x419 / 0x41a d3d1ec, ported from 4U uEm099's 8cda90 / 8cdc60 / 8cbe90, which
  ask for the same motions while 4U's Diablos arcs have no bank 4): Monoblos' bank 4 fills them.
- Actions (C, tools/disp4u.py on both slot-44 dispatchers, the natives each cmd table uses): uEm101 has its own
  handler for every action (0x8d7d8c..0x8defb0); none is uEm099's function, and no handler body equals a uEm099 one
  with branches and literal loads masked. The numbering differs too (Monoblos 7/3 7/10 7/24 = one handler 0x8db41c
  r1 0 / 1 / 4; Diablos 7/3 7/4 = 0x8ce0a8 r1 0 / 1). So em101_cmd cannot run on GU's Diablos handlers as it is.
- Variant map (C, 2026-11-05, unicorn emulation of 4U slot 44 0x8df448 / 0x8d41b8 (two levels: the slot-44 switch
  calls a sub-dispatcher per category) and GU slot 125 0xd35e58, every (cat, num); scratch disp_uc.py / pairmap2.py):
  em101_cmd uses 80 natives. Monoblos' handlers differ from their Diablos twins (same motion set) in shape: instruction
  similarity with immediates and branch targets masked 0.08..0.74, except 0x8d6944 (3/0, 0.99) and 0x8dae90 (7/9 vs
  Diablos 7/5, 0.91). Twins by motion set (Monoblos -> Diablos): 1/28 1/29 1/32 1/33 -> 1/32..1/35 (0x41e 0x41f 0x424
  0x425), 1/31 -> 1/30 1/31 (0x418), 2/13 2/15 -> 2/19 2/20 (0x419 0x41a), 3/0 -> 3/3, 6/0 -> 6/0, 7/0 7/18 -> 7/0,
  7/6 7/20 -> 7/6, 7/7 -> 7/7, 7/9 -> 7/5, 7/13 7/28 7/33 -> 7/64..7/70 (0x415 0x422). Own moves with no twin: his
  roars 1/21 1/34 2/7 (0x404), the charge family 7/3 7/10 7/24 7/34 (0x8db41c), 7/4 7/21 (0x8db998), 7/5 7/22
  (0x8dbbbc), 7/2 7/19 (0x8dabd8, 0x204), 7/31 7/32 (0x8dbf80) and others (scratch pairmap2.txt).

## Class route (decided 2026-11-05)
Route B for the behaviour: his 4U handlers translated literally (one C handler per 4U handler, 4U call order and
values), run from a hook on GU slot 125 for variant 1 (Stygian Zinogre's em057_01_moves.c pattern), with his 4U AI
table (em101_cmd in GU's language). Reason (C, variant map): no Monoblos handler equals its Diablos twin, so GU's
Diablos handlers would run Diablos' timings and attack indexes, not his. GU's class keeps the engine side (reactions,
traps, death, area moves) until the variant map of those categories is done.

## Stages
- Stage 1 (0.1.0, the first test): his model, textures, own motions (bank 4 in manifest field 8; his roar 0x404 and
  idle 0x40e in GU bank 0's slots 4 / 14), dtbase / dttune from 4U em101, name, icon, size, lease save, his three 4U
  quests on the GU Dunes. Behaviour = GU Diablos' AI table and handlers (a DEVIATION until stage 2), diag hook logging
  every action and motion.
- Stage 2+: his AI table and his 4U handlers (route B), family by family, each tested in game; then his own effects,
  attack data, materials, carves, gear. (Built: gear 0.3.0, AI / handlers / attack data 0.4.0, effects 0.4.1:
  notes/actions.md.) With his own table the dttune takes 4U's distance range row (dt_convert
  without --keep-ranges: (400, 1000, 2500, 5000), Diablos' 4U row is (500, 1000, 3000, 5000), C).

## 0.3.0 (2026-11-05, static checks only; the user chose "materials, armor, weapons" next)
- Materials (tools/items_em007_01.py): 4U 1545..1551 (Monoblos Carapace, Cortex, Thoracic, Chine, Scarlet Finehorn,
  Scarlet Stouthorn, Monoblos Heart) appended as GU 3041..3047 (after Black Gravios' 3036..3040). Left out: White
  Monoblos' (1552..1554), 1696 Monoblos Scrap+ (in none of his tables or gear recipes, C).
- Breaks (C): GU Diablos' bui record (em 0x7) conds 10 / 20 / 30 hold the mixes of 4U em099's groups 0 / 2 / 3 (body,
  horn, back); his groups 0 / 2 / 3 -> conds 10 / 20 / 30 (BUI2 High, BUI4 G); group 1 (Frenzy) and 4..7 (White
  Monoblos, same em101 table) left out. Carves (tools/hagi_em007_01.py): 4U body / tail / shiny High in s2, G in s4,
  GU em007_00's layout (C: tail set at byte 8, shiny at 14, as GU's own s2 / s4).
- Armor (tools/gear_em007_01.py): Mono S (4U 668 672 656 656 664, models 368 / 369) and Mono X (670 674 658 658 666,
  370 / 371); templates GU Diablos 738 / 739 and Diablos X 976 / 977; defense via 4U Diablos X -> GU Diablos X (G)
  and 4U Gravios S -> GU Gravios (HR: 4U has no Diablos S, C); level rows: Majestic Horn -> Scarlet Finehorn, Hyper
  Diablos Cortex -> Monoblos Cortex, Diablos Hardhorn -> Scarlet Stouthorn; FreeElemnt (Awaken) dropped (GU has no
  such tree, C). Defense: S 57 / 29 -> 58 / 29, X 96 / 52 -> 124 / 73.
- Weapons (tools/gear_weapons_em007_01.py): 5 lines, 14 weapons (GU IDs GS 147-148, SnS 143-145, Lance 142-145, HBG
  120-121, LS 137-139), stand-ins GU Diablos' (GS 124, SnS 115, Lance 115, HBG 97) and LS 81 Centenarian Dagger;
  substitutes B.Tigrex Hardclaw -> Tigrex Hardclaw, Brutal Horn+ -> Rajang Horn+ (G); GU's own GS "Executioner" (41)
  shares his 4U Executioner's name (open for review). Lines end where 4U continues with others' materials
  (OTHER_CHILDREN, asserted).
- Quest rewards now carry his materials (4U-only items GU lacks still left out, logged).
- Data file 0.3.0: 10 sections (BUI2 BUI4 FILE NAME, TBLA / TXTA x 3), 27192 B; romfs 75 files (16 MB).

## 0.2.0 (2026-11-05, static checks only; the user: values "adapted to MHGU so it is fair", AI / attacks from 4U,
## spawns and routes from 4U, materials / armor / weapons, Hunter's Notes entry)
- dttune on GU's balance (tools/build_em007_01_arc.py dttune_gu): GU em007_00 vs dt_convert of 4U em099 on it (both
  with --keep-ranges) differ at exactly 10 bytes (C): +0x38 base HP (4500 / 4300), +0x370 u16 (100 / 120, role G),
  +0x5ec f32 (680 / 780, role G), and the (type, sub) bytes of the etd word-29 records 0..2 at +0x3ac / +0x3c4 /
  +0x3dc (4U (4, 0) -> GU (22, 2)). Rule (Black Gravios' unconverted_blocks): his 4U value where GU kept Diablos';
  quantities x GU / 4U Diablos (HP 4186, 42, 523.08); codes = GU's (his 4U sub byte 4 where Diablos has 0: DEVIATION
  to check, G). Every other GU byte is 4U Diablos' conversion, so his 4U values stand there.
- Routes (tools/routes_em007_01.py, own fields 40 / 42 / 43): 4U em101 on stage 17 = 4U em099 byte for byte (hop table,
  stay areas, timers, routing script g0 s8 vs g0 s1; C), and 4U slot 66 (uEm101 0x8e0bd4 = uEm099 0x8d65e0): sleep 5,
  eat 7 on stages 17 / 18 (C). GU em007_00's map 5 differs (C): its hop table links 1 <-> 2, its next-area shares and
  stay timers are its own (e.g. area 1 90 / 30 / 180 s vs 4U 120 / 90 / 180). Built: area_link kind 1 = his 4U hop
  table (kinds 2 / 4 GU's until 0.4.7, since 0.4.8 his 4U hops and his way to 5), area_select from his 4U routing (Status 2 per origin, 4 = first step
  toward sleep area 5, 0 = default), map_info block 5 = his areas / eat 7 / sleep 5 / prey 0 / his 4U timers. Other
  maps byte-identical to GU's (C, checked).
- Next (order to agree with the user): his AI table + handlers (route B); materials / carves / BUI / rewards / armor /
  weapons; Hunter's Notes (core: Notes bits past 127 into the store). His own attackdata on GU's balance comes with
  his handlers: GU retuned 4U Diablos' attack records (byte 4 power in many, byte 28 GU's per-record code 6..9; C),
  his 61 records are his own order, so the rule needs his record -> Diablos record twins (open).

## 0.1.0 build facts (2026-11-05)
- Arc (tools/build_em007_01_arc.py, own file IDs 0x10940..0x10945): model + tail (materials: body01 / body02 / tail
  'solid_nm', eye and 'angry' 'add', wing 'tar'; 4U types m00 / m01 / m02 / m50 = GU em007_00's numbering for the
  shared ones), XFS (GU em007_00's 11 states; its groups 5 and 104 not in em101; em101 groups 50 / 51, eye material,
  hidden: G), bank 0 (GU's with slots 4 / 14 = his), bank 4 (field 8), dttune. Everything else GU em007_00's.
- Skeleton (C): em101 and GU em007_00 have the same 40 bone ids with the same parent ids; the file order differs
  (em101 lists the chains 6..9 / 61 60 and 15..18 / 80 81 first); largest bind position difference 19.3 (bone 4).
- 'XfBA1__m02_angry' lists RSMeshBias5 and RSMeshCNBias8; GU has no RSMeshCNBias* record: RSMeshBias5 kept (C).
- dtbase: 4U em099 and em101 convert to GU em007_00's bytes (C): shared. dttune: dt_convert em101 on em007_00 with
  --keep-ranges (GU's 3 range rows: GU's file is 56 B = 2 x (16 + 12) longer than a 4U-ranges conversion, S), 125 of
  1536 bytes differ from GU's.
- Quests (tools/build_em007_01_quest.py): 1057 = m00801, 1058 = m00818 (capture, deliver 4U item 791 -> GU 2065),
  1059 = m01018; templates GU q1002 (village ★10 hunt, stage 22 re-staged to 5, small monsters of q1036) and q1036
  (village ★10 capture, stage 5); ratio over 4U m01025 (caravan ★10 Diablos): ★8 rows 27 / 30 / 19 (r 0.73 / 0.45,
  rows may go below the base: a change from Black Gravios' rule, logged in the tool), ★10 rows 37 / 64 / 19.
  (Replaced in 0.4.2: "Quest ranks and hub quests" above.)
  Subquest "horn" = 4U part 2 -> GU code 1 (C: quest texts). His 4U materials have no GU item: left out (logged).
- Open for the test: does he look right, do his own roar / idle and the bank-4 motions play (motion 0x4xx lines), the
  lease lines, the quest result's name / icon / crown; a capture-kill in 1058 (Black Gravios' fix em005_01_objlog is
  his only: if killing Monoblos clears 1058, the hook needs a core dispatcher).
