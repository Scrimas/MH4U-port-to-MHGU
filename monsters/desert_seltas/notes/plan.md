# Desert Seltas and Desert Seltas Queen port: plan (from 2026-11-09)

One package (`monsters/desert_seltas`), two allocations.toml entries (`desert_seltas`, `desert_seltas_queen`), as
Dalamadur and Shah Dalamadur: the Queen's 4U quests always bring her Desert Seltas. Facts: C = read in code / data,
S = strong, G = guess. 4U addresses: the v1.1 exe (dump/exefs_v11), read 2026-11-09.

## Phase 0: identification (C)
- 4U: Desert Seltas = em 94 (emName 94), run by 4U's uEm025 with Seltas (slot 44 0x777b18); Desert Seltas Queen =
  em 95, run by 4U's uEm026 with Seltas Queen (slot 44 0x7957c4). Arcs em094.arc / em095.arc.
- GU: Seltas 0x4c (em076, registry 61), Seltas Queen 0x45 (em069, registry 58); GU ships em076_00 / em069_00 only.
- Port IDs: Desert Seltas 0x14c (Seltas variant 1, registry 148), the Queen 0x145 (Seltas Queen variant 1, registry
  149). GU's classes uEm076_00 (vtable 0x17ecf54, slot 125 0xfdc074) and uEm069_00 (0x17e7f88, slot 125 0xf9c8b4) run
  them (package.toml gu_classes, one class per entry: module/build.py).

## Classes and species tests (C)
- GU kept 4U's species tests of em 94 / 95 as variant tests: the variant byte (this+0xb5f5) is read 31 times in
  uEm076_00 and 86 times in uEm069_00, where 4U tests em 94 / 95. GU's EMC tables keep their 4U bodies as op-0x92
  variant-1 blocks: in every such script the variant-1 body equals 4U's em-94 / 95 body.
- Their AI tables: 4U em025_cmd (em 94) / em095_cmd (em 95) in GU's language (tools/build_seltas_arc.py cmdtbl()).
  GU's variant-1 body where the engine needs GU's language. The Queen's group 14 script 0 is in 4U's em095_cmd only (em026's
  and GU's group 14 are empty; it runs 16/4): appended since 0.1.1 (0.1.0 dropped it). GU's class asks for group 14 where
  4U's does (GU f8c7c0 `mov r1, #14; strb r1, [r0, #0x18]` = 4U 0x798418), so it runs for her as in 4U (S: what sets
  that request is not traced further).
- Action closure, checked again 2026-11-09 (0.1.0's list of "GU-dropped" Queen handlers was WRONG: its GU dispatch reader
  took shared case tails for stubs, missed GU's cat-6 table and GU's motion call 0xb058c). GU's dispatchers send every
  action of their tables to GU's twin of the 4U handler with 4U's parameters: Queen 1/31 -> 0xf92528 (motions 0x41c /
  0x477 by variant), 6/0 6/4 -> 0xf954d0(0 / 1), 6/2 -> 0xf957a8, 6/3 -> 0xf9590c, 7/1 -> 0xf964d0 (s0 -200), 7/26 7/30 ->
  0xf9739c(0 / 1, 0), 7/35 7/39 -> 0xf9768c(0 / 1, 0), 16/0..16/5 = 4U's 0x792224.. (4U 0x79a184). The twins keep 4U's
  species tests as variant tests: 4U's Queen class has 97 (80 in handlers, 17 in its dispatchers), GU's class 86 variant
  reads plus GU's dispatch moving 4U's inline cases into functions (7/7 -> 0xf96954, 7/55 -> 0xf9852c, 7/63 -> 0xf99454,
  each with its variant test and her motions 0x47b / 0x474 / 0x494); the 8 em-95 tests of 4U (1/31, 1/35 x2, 7/2,
  7/11, 7/23 x2, 0x7915dc) each have their GU twin with the same attacks (58 + 61, 65 / 43, 62 / 23, 59 / 14, 68 / 56).
  Desert Seltas: a GU handler for each, as found before.
- Reactions (category 10, requested by the engine, not by the AI: outside that closure check). The 0.1.1 test froze her
  in her first flinch twice (10/7 with her last attack's motion for 69 s / 53 s, until her death). 4U 0x79463c tests
  the species (W+0x1c0 == 26 -> 0x7946a4, else em 95's switch 0x794660, 46 numbers, her own motions 0x33c..0x347);
  GU 0xf9be10 keeps the normal Queen's switch and returns at once for any variant (`popne` after the variant read, C).
  Ported 0.1.2 (module/seltas_react.c, tables from tools/react_seltas.py): an entry hook runs em 95's switch; the 19
  numbers whose 4U table is the normal Queen's play GU's normal-Queen table (GU shortened 30 31 99..102 105 187 there:
  a DEVIATION, she does what GU's normal Queen does). Other early variant returns in GU's Queen class (scan of every
  `ldrb [this+0xb5f5]`): 0xf8af44 (variant 3 only) and 0xf8d0a8 (an AI condition, stage 9 / 10 only). Desert Seltas:
  4U's Seltas class 0x785b58 has no species test in its reactions and GU's 0xfdb3b8 none either (C).
- Shots (open): GU kept the species tests around the Desert Seltas' shell posts but posts nothing for variant 1 in
  0xfd5010 0xfd5e58 (shell 0x13b) and the second shot of 0xfd7c78 (shell 0x139) (`ldrb [this+0xb5f5]; cmp #0; bne`
  past the post, C; 0xfd745c's test picks a follow-up action, 0xfd4b00's skips a block not read yet), where 4U posts his own
  uShell012 subtypes (0x661f6c: 58 / 56 in 0x77f618 and 0x7802e0, 59 / 57 in 0x7819d4 and 0x781eb8; the Seltas' are
  7 / 6 and 24 / 13). So those attacks of his have no projectile in GU (the user, 2026-11-09: "spit attacks without
  spit effects"). The Queen: 4U 0x78e688 (7/9 7/15 7/34 7/79) and 0x796928 post subtype 92 for her where the normal
  Queen's is 1 (0x661bec); GU's twin 0xf96a38 posts the normal Queen's shell 0x127 kinds 0 / 1 / 2 for both.
  Colour (0.1.6; the user on 0.1.5: his spit on her back is green, C unless marked): the species' 4U shot EFLs
  em025_001 / 002 / 005 take a code colour (colour block), theirs (em094_201..203, em095_020 / 021) have none: 4U draws
  their shots in the EFLs' own colours. GU keeps the species' colours in its list-2 records (em076_00u ids 0 / 11 sand
  aa9650, 1 / 21 green 788c46, RGB lerp at factor 1.0; records 0 and 1 differ only in id, mask and colour), and our
  copies had kept them: his shell37 kinds 6-8 (7/57 on her back) and shell00 (7/52) were green, the rest sand. Now
  white at factor 0 in all three copies (shots_seltas.py NEUTRAL, check_colours asserts the 4U facts); the arcs differ
  from 0.1.5 only in em076_01a / 01b / em069_01a. S: that GU applies the record colour through the shell kinds (the
  record's +0x70 is 0).
  Ported 0.1.3 (tools/shots_seltas.py, module/seltas_shots.c). Their shots differ from the species' only in effects
  and some record bytes (C, asserted in the tool): uShell012 56..59 fly / hit with (70, 10) / (70, 12) = em094_201 /
  203, mask -1, records 38..41 (the Seltas' 6 / 7 / 13 / 24: (36, 1) / (36, 5), records 5 / 6 / 12 / 20); uShell001
  117 / 118 with (70, 10) / (70, 12) / (70, 11), records 89 / 90 (36 / 74: (36, 1) / (36, 5) / (36, 2), 33 / 69); the
  Queen's 92 with (71, 16) / (71, 17) = em095_020 / 021, record 1 as her kind 1. More sites: 0xfd7c78's mode-0 shot
  (7/52 7/60 7/63, 4U 0x787270: 117 / 118, its modes 1 / 2 post the shared 90 / 91) and the Queen's 7/56 (0xf9866c,
  4U 0x796928) also skip for a variant. GU caches a family's def per shell id for every monster (0x48c388; the 412
  ids are all taken), so new kinds or a changed def would reach a normal Seltas in the same quest (11140). Instead,
  copies of GU's defs under our paths (on our own PELs: GU's list-2 records of the ids the kinds post, 0 / 1 / 11 /
  21 for shell37, 1 / 21 for shell00, 10 / 21 for hers, on their 4U EFLs; and our hit data: GU's entries with the
  bytes where the Desert record differs from GU's source record) are swapped into the request's cache read for their
  posts only (0x48c5e4, back at the exit 0x48c54c). GU's kinds, directions and timing stay. Sound: the def's GU pts
  as before (4U plays request 201 of the owner's bank for every one of these subtypes; whether his 201 sounds other
  than the Seltas' is not checked, G). Not played.
- Attacks: GU moved her 4U attacks 69 / 70 (7/26 7/30 16/0 / 7/35 7/39) to its records 47 / 51 (GU 47 / 51 = 4U 69 / 70
  but for GU's retune bytes 28 / 31; GU's 69 is an empty record) and its twins post 47 / 51 where 4U's post 69 / 70 for
  her (C). So her attackdata is GU's 70 records (0.1.0 also carried 4U's 70 / 71, which nothing posts).

## The pair (C, 0.1.4: module/seltas_pair.c)
- 4U: a male of either species pairs with either Queen (0x77cdc4 / 0x784a80: em 26 or 95 into [W+0x8d88]+0x50; the Queen
  0x78c008: em 25 or 94). Before an area move his slot 66 (0x788c64, no species test on that path) moves him to her area
  ([W+0x1f4] = her [W+0x14c]) or keeps him where she is.
- GU does it in its area-move engine: her slot 9 (0xf8c108, every 300 frames) and her call 0xf96230 (phase 0) hand her
  area to the monster with ID 0x4c (0xbe5ec: record +0x5dc4 bit 0, +0x5dc5 = area); his slot 152 (0xfc768c, asked by the
  requester 0xb8568) finds the Queen with ID 0x45, sets this+0x1404 bit 27 (no random move, 0xb83ec) and keeps him in
  her area. Both compare the full 16-bit ID (variant byte included): a Desert Queen calls a normal Seltas, her Desert
  Seltas never finds her. GU's other partner searches in the Seltas class (0xfc72bc, 0xfc7340, 0xfc75a0) compare the em
  byte and find her (his joint moves ran). The 0.1.3 test (log 21-19-17): the two in the same area 210 of 720 s; he
  wandered alone (areas 3, 10, 7) and died in area 10.
- Port: 0xbe5ec entry: at her two calls (lr 0xf8c17c / 0xf962dc) a Desert Queen calls 0x14c (her quests bring him; 4U
  would take either male). 0xfc768c entry: for the Desert Seltas GU's own code with the Queen found by her em number
  (either Queen, as 4U). The normal pair keeps GU's code.
- His jump out of the sand at her call: buried (6/3, GU 0xfd440c = 4U 0x784308) he waits for his partner's motion 0x465
  (her 7/72, 0xf99504) past frame 328, then 6/4 (motion 0x45c). 4U 0x784498 asks the partner's frame (0x91ab1c(partner,
  1, 0, 328.0, 0.0)); GU 0xfd4590 asks his own (`mov r0, r4` before 0xb0a24), and his buried loop (motion 1, 301 frames)
  never reaches 328: in the test he stayed 60 s buried through six of her calls, then dug out (6/1). A GU slip in code
  only a variant runs. Port: a mid hook at 0xfd4594 hands the test his partner.
- Not played. The log shows `dsq calls her Desert Seltas to area N`, `ds stays with his Queen` / `ds may leave his
  area`, and his 6/4.

## The launched flights (0.1.5: a test log, C unless marked)
- The Queen's launch (her 16/4 -> 16/5 -> 16/6, his 7/66 -> 7/67) is the Desert pair's own: of the four tables only 4U's
  em095_cmd starts a 16/x action (g14 s0 `00 10 04`); em026_cmd and GU's em069_00 start none. GU kept the code but no GU
  table reaches it, so GU never ran it. Their scripts here are 4U's byte for byte (her g14 s0, his g7 s18 `00 07 42`).
- His side: 7/66 (GU 0xfd9d94 = 4U 0x7835b4) rides on her; step 6 waits for her 16/5 and plays 0x44f, step 7 waits for
  her frame, step 8 sets 7/67 (GU 0x76984 = 4U 0x94ef9c). 7/67 = GU 0xfd9438(this, 1) = 4U 0x782da8(this, 1) (7/64 ->
  7/65: the same flight aimed at her target, mode 0). Steps (GU rec+0x1a1): 0 set up (motion 0x44f, attack 34, the probe vector
  rec+0x900), 2 the flight until a wall contact (rec+0x8f0, counted by GU's stage contact 0xa75f4 = 4U W+0x958) or its
  timer rec+0x1bc runs out (36 frames in mode 1, 60 in mode 0, counted down by this+0x1c), 3 the crash (velocity 0,
  attack 35), 4 nothing more. Neither game's handler ends the action, and 0x44f loops (61 frames, loop 0, both games).
- GU drops two 4U posts from it: the launch effect (4U 0x79a2c8(her, him, 2): effect 59 kind 2 on him) and the crash
  blast (4U 0x663220 at joint 1: uShell003 subtype 240, init 0xc548c8 adds flag 0x800000; GU calls joint 1's getter and
  drops the result). Not ported.
- While in 7/64..7/67 he takes no new command from her (GU slot 119 0xfc8a88: `num & 0xfc == 64` skips 0x7fc5c).
  After 7/65 / 7/67 both games expect category 11 or 12: 11/8 (the fall; GU 0xfdbdb4 case 8 = 4U 0x77c91c, from message
  type 6: GU 0x667e0 -> 0x9c2b4 = 4U 0x687b44 -> 0x948614) or 12 (his entry, S; GU slot 119 at 0xfc9104 = 4U
  0x77cfdc), each setting the pair's +0x6a.
- GU's same-action watchdog (0xad7b4 = 4U 0x93f6e4): 7200 frames in one action (this+0x13f8) end it; its gate is byte
  +0x2a2c bit 1 of the object behind the pointer at MAIN 0x1838bc0.
- The 0.1.4 test (log 15-48-15, 11372): her 16/5 at 04:51.1, his 7/67 from 04:51.3 in 0x44f until the quest ended at
  06:32 (101 s), no further line of his. The user: he glitched when she shot him and he flew against the wall, then
  "flies forever as in free fall".
- What ends it in 4U (S, monsterhunterwiki.org Desert_Seltas_Queen_(MH4U), read 2026-11-10; the user has no video):
  her "Beetle Cannon" fires him from her tail pincers and "shatters him", her tail launch kills him "leaving behind no
  carvable remains", then she digs up a new one. So he dies at the end of the flight: that is why the handler ends no
  action. The killing blow in 4U's code is NOT found (his crash step's uShell003 240 has power 10, type 10; neither class
  writes his HP; the Queen's 16/5 helpers 0x798fe0 / 0x799e24 / 0x799cac / 0x7993dc aim and post effects). What both
  games have (C): in his death state (category 12) after a launched flight his corpse time rec+0x5cc4 (set at death
  from 0xbd7e0, counted down at 0xc93e4; 4U W+0x798c) is zeroed: GU slot 119 0xfc9104..0xfc9168 once the pair's +0x6a
  is set (his crash step sets it), 4U 0x77cfdc..0x77d21c. No corpse, nothing to carve.
- 0.1.7 (the user: "Ja, so einbauen"): seltas.c launch_end. SHATTER_DELAY (10) frames after his crash step (rec+0x1a1
  past 3, the pair's +0x6a set) in 7/65 or 7/67: HP 0 through GU's setHP 0x9a764 (a negative value = 0), then GU's down
  decision 0x9b2bc(this, 0), which requests the death reaction for his movement state rec+0x1ba (0 -> 11/0, 1 / 3 ->
  11/1, 2 -> 11/2, 4 -> 11/3, 5 -> 11/5, 6 -> 11/4; r6 = 0 unless rec+0x3aa bit 1; the 0.1.3 test's death was 11/0). GU's
  death and its corpse-time rule do the rest; her quests' restore count brings him back. The delay keeps GU's crash
  attack 35 (frames 0..10). OPEN: whether 4U counts him as hunted (here GU's death counts), the 4U shatter effect (the
  crash blast) not ported, multiplayer not tested.
- Searched again 2026-11-10 (0.1.8, the user: "prüfe mh4u gründlicher"): 4U's Seltas reaction dispatcher 0x77c91c,
  on reason 8 ([W+0xe28]+0x1cb) while in 7/65 or 7/67, sets the pair's +0x6a, requests the reaction behind 0xfdd684 (its
  first word 11, i.e. category 11; G which number) and calls 0x78968c, which takes her target, skips it unless it is a
  live hunter and measures his distance to it against his size (S: the wiki's guaranteed stun at the impact). What
  sends reason 8 (S: the crash blast GU drops) and what kills him: still NOT found. 0.1.7's death stays.
- The 0.1.5 log (seltas.c flight_log) shows each step, the wall contacts, the timer, his height over the ground, the
  pair flags, the watchdog time and the action that follows, for a normal Seltas too.
- 4U's slot 54 (0x7890a8; GU's twin slot 137 0xfc96dc gives the category-12 action that GU's reset 0xb8c54 then
  sets: his entry) gives the Desert Seltas 12/1 (`[W+0x1c0] != 25` -> flag 1) where GU's slot 137 gives 12/0 to every
  variant (12/1 only on stage 15). 4U's 12/1 (0x777c6c) buries him (6/3) for her pull: ported in 0.1.10 (seltas.c
  buried_entry, History).

## Assets (C)
- tools/build_seltas_arc.py: em076_01.arc (606 entries, file IDs 0x10a00..) and em069_01.arc (632 entries, 0x10a40..):
  GU's own variant layout (em001_02.arc): their own files under emNNN_01, the files shared with variant 0 under
  emNNN_00's paths and IDs (no file under a GU path may differ from GU's: m10818 has a real Seltas next to him).
- Model: 4U MOD + MRL from GU templates, albedo + GU specular maps. Parts states: GU's layout; 4U group 50 (the frenzy
  look, 4U's part rows show it only in state 10) hidden in the base states GU's slot 132 applies every frame
  (Seltas 0xfc95e8 states 0 / 8, Queen 0xf8d71c / 0xf8d728).
- Motions: their 4U lists (LMT 67) with GU's finer tracks where GU has the motion, only where the track keys are equal.
- Data: their 4U dttune values + GU's retunes of the species where theirs equal the species' (difflib-aligned:
  Desert Seltas' dttune is longer than GU's); Desert Seltas' dtbase (3 own bytes) and bodydata (21 records); the Queen's
  attackdata (GU's 70 records, above), hitsize (her 4U groups, GU's where equal) and bodydata.
- Carves (tools/hagi_seltas.py): 4U G body / shiny tables in s4, GU's filler in s0..s3.
- Sound: their 4U call / waves / bank / request (tools/snd4u2gu.py). 4U has no battle music of theirs
  (sound/bgm/battle holds no em025 / 026 / 094 / 095 file; the selection code is not read, G).

## Effects
- tools/efl4u2gu.py effect_set: their EFLs and the qe families their MEF names under 4U paths, PEL u list 1 from the
  MEF, list 2 = GU's (the GU class posts its ids: shell and code effects stay GU's, a DEVIATION where 4U's differ).
- GU's common effects on the motions GU shares with them (the user's rule); 4U's ground-flag records as world records
  on their ground (module/seltas_fx.c on Tidal Najarala's two PSL hook sites, which call it first); grey rock chunks
  hidden (hide_grey_models 'chunks', issue #6); 4U's common dust qe006_* at 1x (DUST_1X).
- Their sand (0.1.4; the user on 0.1.3: "light sand swirls, bright yellow, almost white"): their own EFLs that MEF
  ground-flag records name (his em094_008 / 010 / 011, hers em095_000 / 011 / 012 / 013 / 014 / 024) had 4U's Intensity
  1 baked x2 into the soil-multiplied grey, e.g. em095_000 (178, 178, 178) -> (255, 230, 162). Now 1x (own_sand()):
  (147, 115, 81), the brown of GU's Dunes dust (C, the built arcs read back). And where GU's motion has its own dust
  (cm202_*), their own ground sand is left out for it (the rule on environment effects): her walk 0x8 (517, every 15
  frames next to GU's steps), 0x48 (7), 0x403 / 0x419 (501), 0x422 / 0x42b (522, 523), 0x424 / 0x425 (21, 17); his 0x41,
  0x21c, 0x21d (4). Their 4U sand stays (at 1x) where GU's motion has no dust or GU has no such motion: his hover
  sand (4) in 0x119 0x218 0x21b 0x21e 0x226, his dig in / out (10 / 11, the user's open choice), her steps and slides in
  her own 4U motions (the arc log lists every one). A DEVIATION from 4U's brightness, for GU's look.
- Desert Seltas' dig in / out (his own 4U effects em094_010 / 011, sand): GU has no own effect for this move. The user
  (2026-11-10): "du kannst auch mh4u sand nehmen hauptsache er ist nicht grell gelb". So 4U's sand stays.
- 0.1.8, the rest of their dust (the user on 0.1.4: the dust is bright yellow when the Queen pulls him out of the
  ground): own_sand() took only the ground-flag files; the soil-coloured ones off the ground kept the x2 bake. Her pull
  (7/72, motion 0x465: em095_028 x4 + em095_029; then 0x477: em095_025 / 026, not soil-coloured) came out (255, 231,
  163). Now every own EFL whose units 4U multiplies by the soil (area colour block or mode-5 units) is drawn at 1x: his
  em094_006 / 007 / 008 / 010 / 011, hers em095_000 / 011..014 / 023 / 024 / 028 / 029 (each holds soil units only,
  asserted). Not seen in the game yet.

## Routes (C)
- tools/routes_seltas.py: their 4U maps on GU's maps (area_link / area_eat / map_info / area_select): Desert Seltas
  on the Dunes (4U 17 -> GU 5: sleep 3, eat 10) and the Ancestral Steppe (4U 1 -> GU 11: sleep 9, eat 8), the Queen on
  the Dunes (sleep 5, eat 4); 4U's night Dunes (18) has one more 3 - 7 link than the day one (noted, the day map used).

## Quests (C, tools/build_seltas_quest.py docstring for every source)
| GU | 4U | where | what |
|---|---|---|---|
| 1068 | m01030 caravan | village 10 star G, Dunes | hunt Desert Seltas; sub: break his horn |
| 11138 | m10805 guild G1 | hub G1, Steppe | hunt Desert Seltas; Rajang intrudes (slot 2) |
| 11139 | m10815 guild G1 | hub G1, Dunes | slay 30 Bnahabra (sub: 8 Konchu); Desert Seltas intrudes |
| 11140 | m10818 guild G1 | hub G1, Steppe | hunt a Seltas, then Desert Seltas (standin_alt 0x45); sub: deliver a Queen Substance |
| 11372 | m10924 guild G2 | hub G3, Dunes | hunt the Queen, her Desert Seltas comes back (restore 5); sub: wound her tail |
| 11373 | m10928 guild G2 | hub G3, Dunes | a Cephadrome, then the Queen and her Desert Seltas; sub: her tail (4U's frenzy sub has no GU state) |
- Not ported: m10812 (Purple Gypceros on the Sunken Hollow, Desert Seltas its 50 % intruder: GU has neither); no
  event quests (the user, 2026-11-09); no quest waits for a GU monster's own quest (the user, 2026-11-09).
- 4U's m10928 text names a Shrouded Nerscylla, its file spawns a Cephadrome (em 105): the text here names the
  Cephadrome (German: the accusative, as 4U's "einen Cephadrome", m00715).
- GU intruders: boss slot 2 (GU's quests hold them in 2..4), +0xCC bytes of GU's G1 one-intruder hunt q11124 and
  +0x16F bit 3 (set on exactly GU's 417 quests with +0xCC). 4U's intruder list (+0x30): {u32 chance, spawn record}
  closed by 0xffff + 0xffffffff; its stat block is 2.
- Small monsters: 4U's first set as a GU emSetList (format in the builder's docstring); Delex (GU has none) left out.

## Hitzones, parts, breaks (C)
- Their hitzones and break / sever groups are 4U's (hitsize, dtbase / dttune). Break rewards (tools/items_seltas.py):
  4U's G groups on GU's species records (Seltas conds 10 / 20 = 4U groups 0 / 2; the Queen's 10..50 = 4U's 0 / 2 / 3 /
  4 / 5); 4U group 1 (the Queen's frenzy crystals) has no GU part.

## Items, armor, weapons
- Materials: 4U 1388..1390 -> 3055..3057 (his), 1397..1401 -> 3058..3062 (hers); 4U 1396 D.S.QueenConcentrate is
  GU's item 1032. S.Queen Concentrate (no GU item) -> D.S.QueenConcentrate in every recipe and table.
- Armor (tools/gear_seltas.py, the Queen's entry): 4U Seltas Z, models 430 / 431, template GU Seltas X (914 / 915),
  defense scaled by Seltas X's GU / 4U ratio, the template's 5 level rows with Hyper S.Queen Cortex -> D.S.Queen Cortex.
  4U's Faulds Z resists differ from the other four parts; GU's series holds one set: the four parts' (DEVIATION).
  Colour: 4U's 0x07 on both dye slots (tools/gear4u.py colour rule). Every tinted (type 3) material of the 20 model arcs
  already selects plain FTransparency (C, 2026-11-09, the built arcs read back), so GU draws the colour in full and
  --opaque-tint (build.py, notes/porting-guide.md "Armor colour") changes nothing: the 20 arcs rebuilt with it are
  byte-equal to 0.1.1's. Not yet compared with 4U in the smithy.
- Weapons (tools/gear_weapons_seltas.py): his SnS (3), GL Monsieur Gore+, DB (3); her Hammer, LBG Battalion Strafer,
  GL Seltas Fortitude, Bow (2). Own models 101 / 93 / 105 / 82; GU's models 50 / 80 / 84 for the lines GU's normal
  Seltas weapons carry. Left out for review: IG Cannibal Happa, CB Maximinsect (half theirs).
- No 4U Palico piece is named after them (C).
- Names: the 2026-11-09 check (none of the 22, 12 weapons and 10 armor pieces, a GU name) was WRONG: GU has its own
  "Battalion Strafer" (weapon06MsgData 206, Machine Strafer's final form) and "Seltas Fortitude" (weapon09MsgData 290),
  equal in all five languages (C, 2026-11-11, scratchpad name_clash.py over every GU weapon / armor name). Her LBG and
  GL lines carry Monoblos' " (4U)" label in every language since 0.1.18 (gear_weapons_seltas.py LABEL_4U); then none
  of the 22 equals a GU name (C).

## Notes, names, icons
- Hunter's Notes entries 132 / 133, threat 6 (tools/notes_seltas.py), each right after its GU species; names = 4U
  emName 94 / 95 in monsterName's dummy5 / dummy4 (tools/name_seltas.py); board / quest icons: their cells (ui_icon 208
  / 209, icon_4u 103 / 104).

## Core change: guest_in
- allocations.toml `guest_in` = quests of another entry of the same package where this one is a further boss under its
  standin_id: module/main.c standin_swap and em_arc_request, module/items.c bui_record_c (break rewards), module/notes.c
  notes_live (Notes unlock), module/port.c port_guest; tools/alloc.py checks it (a lessee, not a companion, each quest
  owned by exactly one other entry of the package). module/save.c: two lessees in one quest take one slot each.

## Limits (notes/porting-guide.md)
- Save: both lease a slot per quest (save = "lease"); armor create record past the save's 576 listed bits: the mod's
  store (module/gear.c). Removal leaves the save as GU's.

## Deviations
- Shell / code effects GU's where 4U's differ; frenzy (m10818, m10928) left out (GU has none); 4U's night Dunes ->
  GU's Dunes; m10928's frenzy subquest -> her tail subquest; Seltas Z waist resists; recipe substitutes (T.Najarala
  Splasher -> Najarala Ampsounder, D.Mohran Allbrace -> Lrg ElderDragon Bone, S.Queen Concentrate -> D.S.QueenConcentrate);
  raw / element on GU's balance (weapons4u.gu_scale, as Shrouded Nerscylla's).

## Open (a test log tells)
- In-game: the test builds 0.1.1 .. 0.1.17 were played on cores 1.9.0 / 2.0.0 (History, the last on 2026-11-12);
  0.1.18, the PR's state on core 3.0.0, was not. The items below are the notes of each version; the History says what
  a test settled. Still open after the 0.1.17 test: her pin (History, the user on 0.1.16 (a); she did not pin in that
  run), his trail from her back (there, (c)), her fast run and her 4U actions no log has shown (7/21 7/25 7/29 7/34
  7/50 7/52 7/55 7/56 7/57 7/60 7/66 7/67 7/68 7/77; 7/24 came on 2026-11-12), 4U's respawn delay (not found) and its
  stun check 0x78968c. Up to 0.1.17 the `dsport:` lines showed each unit's actions, motions, HP and part counters (her
  16/x lines are her joint attacks with her Desert Seltas, 16/4 the one her group 14 script starts); 0.1.18 keeps only
  the working hooks' short lines.
- Desert Seltas' dig effects: the user chose 4U's sand if it is not bright yellow (2026-11-10); 0.1.8 not seen yet.
- His and her 4U shots (above, "Shots"): ported in 0.1.3, not played. The log shows each swapped post
  (`dsport: ds shot: GU shell 0x13b with their own 4U family`).
- Her Desert Seltas at 0 % HP on her back (0.1.1 test: he stayed in 7/65 until 27 s after her death, then flew on at
  0 %); with her reactions back this may change; the HP lines (0.1.2) show when he reaches 0 and what he does then.
  0.1.3 test: he died normally (11/0 at 0 %, away from her), not on her back.
- The pair (0.1.4, "The pair" above): whether he now stays with her, comes when she calls and jumps out of the sand at
  her call (6/4). His shots from GU shell 0x139 (7/52 7/60 7/63 7/57 7/61 7/58 7/62) were not used in the 0.1.3 test.
- Their sand at 1x and GU's dust on the shared motions (0.1.4): the user's eyes.
- Seltas Z in the smithy: each of the five pieces, Blademaster and Gunner, against 4U (colour; the user's eyes).
- Whether GU's intruder bytes give 4U's 100 % (11138 Rajang, 11139 Desert Seltas): the test shows if they come.
- His launched flight after her 16/5 (above, "The launched flights"): 0.1.7 makes him die at its end (the 4U wiki's
  "shatters"), not played. Also not ported: the crash blast, the launch effect, his entry 12/1.
- 0.1.8, his volley's ground splash (tools/shots_seltas.py "The ground splash"): green before, his em094_202 now; and
  its hit carries his paralysis bytes instead of the species' (S, "Status"). The log shows each splash
  (`dsport: ds shot: GU shell 0x13a with their own 4U family`). Not played.
- 0.1.10: his shots' child splash (GU's shell callback) and her shots' ground splash in their own 4U effects; a new
  Desert Seltas enters buried under his Queen (4U's 12/1) and should come out at her pull. The log shows `ds enters
  buried as in 4U` / `ds enters as GU's Seltas` and each effect post (`fx in`: "his 0x13a copy", "her 0x128 copy").
  Not played. Still open: the respawn delay (188 s of play in the 0.1.9 test), how often she leaves an area (her 4/0
  burrow exists).
- 0.1.11: his launch death is 4U's death by impact (11/8, motion 0x350 with the burst em094_204); the log line `ds
  shatters ...: 4U's death by impact` and his next action line (`ds 1 action 11/8`, then `motion 350`) show it. Not
  played. Not ported: 4U's stun check at its end (0x78968c), the camera request (id 59).
- 0.1.17 (History): her underside glow off but in her anger (Capcom's setup); the pin log (`dsport: pin`): why her
  16/2 lets go; his trail from her back (Capcom's second set of em076_00_001, node +0x70 = 150) not ported yet.
- Left as GU's (0.1.8 audit): 7/63's two shots (GU shell 0x139 kind 3, 4U kinds 90 / 91 shared with the species: the
  species' em025 effects, green for 90, uncoloured for 91; GU draws both green); his volley's element mask (GU's 2 for
  every shot, 4U picks 117 / 118 = mask 1 / 2 by 0x93731c, G what it tests); his shots of subtypes 58 / 59 take the
  hit bytes +0x08 / +0x18 of 56 / 57 (GU has two hit entries); the night Dunes' extra hop 3 - 7 in 11372 (4U stage 18).

## History
- 0.1.0 (2026-11-09): first build: both arcs, AI tables, routes, effects, data, carves, items, names, Notes, 6 quests,
  Seltas Z, 12 weapons; core: guest_in, per-entry gu_classes, their log hooks. Not played.
- 0.1.1 (2026-11-09): the action closure checked again (above): GU runs all of the Queen's 4U actions, 0.1.0's "missing
  handlers" were a reading error, so no C port. Her group 14 script 0 now in her table; her attackdata = GU's records.
  em069_01.arc: only its cmdtbl and attackdata entries differ from 0.1.0 (632 entries, same order); em076_01.arc, the
  quests, gear and both FILE sections unchanged; core unchanged. Not played.
  Later the same day: build.py's armor step passes --opaque-tint (porting-guide rule since Shrouded Nerscylla 0.1.15,
  whose tool change came in from the #23 session); output unchanged (above), so still 0.1.1.
- 0.1.1 test (2026-11-09 evening, log 19-30-35: 11372 twice, 11138): she froze in her first flinch both times; her
  Desert Seltas reached 0 % on her back without dying; the user: "many things are wrong", spit attacks without spit
  effects. 0.1.2 (same day): her 4U reactions (seltas_react.c, hook 0xf9be10), HP log lines; assets unchanged. Not
  played.
- 0.1.3 (2026-11-09, the user: "rebuild them"): their own 4U shots ("Shots" above): six skips bypassed, three posts
  marked, our family copies swapped in per post (12 hooks); both arcs gain the copies at their end (his 606 -> 612
  entries, hers 632 -> 634), the FILE sections the defs' IDs 0x10a1c / 0x10a1d / 0x10a59. Not played.
- 0.1.3 test (2026-11-09 evening, log 21-19-17, 11372 once): her reactions ran (10/7 10/20 10/148, she recovered); 24 of
  his shots (7/2 x7, 7/7) and 9 of hers (7/9 x3) with their own family; both died normally (he at 12:53 in area 10,
  she at 14:18), both save leases and tallies right. The user: they are rarely together, and light sand swirls are
  bright yellow, almost white. Found: GU names the pair by the normal species' IDs, GU's buried-male test asks his own
  frame, and their sand had 4U's x2 brightness ("The pair", "Effects").
- 0.1.4 (2026-11-09): the pair (seltas_pair.c, 3 hooks: 0xbe5ec, 0xfc768c, 0xfd4594) and their sand (own_sand(), GU's
  dust on the shared motions). Arcs: same entries and order; only their 9 sand EFLs and the PSLs of his banks 0 / 2 and
  her banks 0 / 4 differ from 0.1.3. Not played.
- 0.1.4 test (2026-11-10, logs 15-40-11 and 15-48-15, 11372): the pair worked (her calls every 300 frames, his rides
  7/66 on her 7/73 and 16/x); after her launch (16/5) he stayed in 7/67 101 s until the quest ended (the user: he
  glitched when she shot him against the wall). The AI checked: their tables are 4U's in GU's language, this attack's
  scripts byte for byte. 0.1.5 (same day): the flight log (seltas.c flight_log, "The launched flights"); data files
  only the version byte, arcs unchanged; behaviour unchanged. Not played.
- The user on 0.1.5 (not played, from the 0.1.4 test): "when a wall comes he glitches and flies forever as in free
  fall", and his spit on her back is green. 0.1.6 (same day): their shots without GU's tint ("Shots", Colour); the
  flight log stays; module unchanged (= 0.1.5's), data files only the version byte. Not played. The flight end in 4U
  is still not found ("The launched flights"); asked the user what 4U does after the wall.
- 0.1.7 (same evening; the user has no video, the MH4U wiki says he shatters; the user: "Ja, so einbauen"): he dies
  when her launch ends his flight, through GU's own death (seltas.c launch_end; "The launched flights"). Module changed
  (subsdk1, and the IPS, whose literal patches follow the module's data); arcs = 0.1.6's; data files only the version
  byte. Not played.
- 0.1.8 (2026-11-10 night; the user with a picture: "die grünen Schüsse sind nicht behoben", green splashes and a
  green puddle where he fires from her back; and the dust is bright yellow when she pulls him out of the ground): the
  green was GU's ground splash, a second shell 0x13a GU's shell class posts at a ground hit, which the 0.1.3 swap never
  reached (0.1.6 had fixed the shots' own records only). Now his copy of it (em094_202, no tint, his paralysis status;
  hook 0xfdcbe4, file ID 0x10a1e) and all their soil-coloured dust at 1x ("Effects"). Audit the same night: attack
  status bytes ("Status" in tools/shots_seltas.py), the AI condition with the Desert test (4U 0x788600 = GU 0xfc85bc),
  the sleep / eat areas (4U slot 66, stage 1 sleep 9 for him), the launch reaction (above). Arcs (C, read back
  against 0.1.7's): his + 3 entries at the end (612 -> 615: PEL em076_01d, hit data and def of the splash family) and
  em094_006 / 007 at 1x; hers em095_023 / 028 / 029 at 1x; nothing else differs. FILE gains 0x10a1e; module + 1 hook.
  Not played.
- 0.1.8 test (2026-11-10, log 20-11-54, 11372; 0.1.7 log 19-02-31 too): every logged shot of his took our copy (60
  lines, the log's cap per quest), the splash 0x13a once after a volley. The user: on her back his shots are still
  green, alone they are right, and some shots leave no effect on the ground. Read since (C): GU's shell takes its
  effect lists from the def it is created with (0x4a2564..0x4a25fc: [def + 0x78 + 4 * i], 0x48a8e0), inside the
  request (0x4a1c84 / slot 0x13c before the exit 0x48c54c), and posts list 2 record uniqueId of list listId (0x4a1e50);
  the kinds' ef files: shell37 kinds 0-5 (0, 0) (0, 11) (0, 11), 6-8 (0, 1) (0, 21) (0, 21), shell00 every kind
  (0, 1) (0, 21) (0, 21), shell01 0 (0, 10), 1 / 2 (0, 20), 3 none. So statically their copies draw, and fused and
  unfused draw the same EFLs: the green on her back is NOT explained. Also found: the Queen's class posts a second
  family 0x128 (em069_00_shell01: kinds 0 / 1 nothing, 2 (u, 20) her ground splash, 3-6 (c, 31..33) cm200_040) from
  nine places and from her shell class's ground hit (0xf9dd08), never swapped; and his PEL u list 2 still holds GU's
  ids 1000 (cm202_060 in the normal Seltas' body green 5f7757, colour on: the part-break / hit chips GU's class
  posts) and the Queen's 1005..1035 likewise (her chips in the normal Queen's colours). OPEN, for the next test.
- 0.1.9 (2026-11-10 night; the user: "pass den seltas port an das neue system an", MHGU Definitive Edition v2.0.0):
  the port on upstream main e38a25d (v2.0.0 2404c26 + installer fixes), worktree MH4U-seltas-v2, branch
  wip/desert-seltas-v2: the 21 port files as they were, the core and tool changes (guest_in, gu_classes, hooks,
  res_majority, materials list, Tidal's dispatch, allocations entries) applied again on 2.0.0's files (the same
  hunks), the lessons in notes/porting-guide.md; package.toml with 2.0.0's keys (kind, subtitle, requires = []) and
  requires_core 2.0.0 (the next core release carries their hooks: the maintainer's number). New: a test log of
  their shells' effect posts (seltas_shots.c seltas_shot_fx, hook 0x4a1e50: def ours / GU's, list, id, the PEL's path,
  the shell's kind, the owner's action; 48 distinct lines per quest). Arcs = 0.1.8's (74 files equal, C); data files:
  version byte. tools/alloc.py: 13 monsters OK. Not played.
- 0.1.9 test (2026-11-11, log 17-50-03, 11372; paused 11 min while the user played 4U for comparison). The user: in
  4U a launched Desert Seltas always bursts and the Queen soon digs a new one out of the ground, here neither; alone
  his shots are right, on her back their ground hits are green again; in 4U she sometimes leaves an area by
  burrowing, never seen here. The log (C): (a) green = two posts still on GU's defs: his 7/57 shots' child 0x13a kind 1
  (em076_00u id 20 = em076_00_002, GU's green) from GU's Seltas shell callback 0xfc6a30 (requests 0xfc6c08 /
  0xfc6df0, id = this+0xcac8), and her 7/9 shots' ground splash 0x128 kind 2 (em069_00u id 20 = em069_00_012, the
  normal Queen's hit effect) from her shell class 0xf9dc80 (request 0xf9dda4); every other post took our copies.
  (b) his launch death ran ("shatters", 11/1 at 03:59), the new male came 188 s of play later as GU's 12/0 (fly-in,
  motion 0x101). (c) she stayed in area 4 for 6.5 min of play (the 0.1.8 test: her 4/0 from AI script 1/28 after 5.8
  min, motions 0x406 / 0x411, 3 s before that quest ended).
  Read in 4U since (C unless marked): the Seltas class's entry slot 54 (0x7890a8) gives the Desert Seltas 12/1 and
  clears the pair's +0x6a; his 12/1 (0x777c6c) = sleepFlagA, sleepFlagB, W+0x978 = 1, setTargetMode(4),
  vertSet(0x93e7b4), setActionNext(6, 3): he enters buried and waits for her pull (6/3 = GU 0xfd440c = 4U 0x784308;
  without a partner he digs out, 6/1). GU's 12/1 is only its stage 15's (4U's first three steps, then a fixed point).
  The crash blast uShell003 240's effect is (2, 2) = lb000_002 (the init 0xc544d0 reads 2 bytes per subtype from
  0x101ddcc; Zinogre's 129 / 135 / 235 / 236 read (2, 31) = lb000_031): a hit spark, so it is not the burst (S). The
  launch post 0x79a2c8 (her 16/6) calls 0xc0a56c(mgr, 59, area, him, mode 2): what id 59 draws is NOT found yet. The
  respawn delay (GU's death / restore state machine on rec+0x5cc1, 0xa66d4) is NOT traced in 4U.
  0.1.10 (same evening): (a) mid hooks 0xfc6c00 / 0xfc6de0 mark his child posts (our 0x13a copy, em094_202) and
  0xf9dd9c her ground splash: a new family copy of 0x128 (em069_01_shell01 on PEL em069_01b: ids 20 / 21 =
  em095_021, 4U kind 92's ground and wall effect, neutral; GU's hit data; file ID 0x10a5a). (b) seltas.c
  buried_entry: on a Desert Seltas' first frame of 12/0 the pair's +0x6a cleared and, with his Queen in his area,
  4U's 12/1 body with GU's twins instead of the fly-in, his buried point = her position (S; what 4U holds in W+0x218
  at an entry is not traced); without her in his area GU's fly-in stays (a DEVIATION). Arcs (C, read back against
  0.1.9's): hers + 2 entries (634 -> 636: PEL em069_01b, def em069_01_shell01), nothing else; his unchanged; module
  + 3 hooks; data files: version byte. Not played. Open: the burst itself (id 59 / his death look), the respawn delay,
  her area moves (the move exists; how often 4U makes it is not compared).
- 0.1.11 (same evening; the user: "Erst Platzen suchen"). Found (C): 4U's id 59 post (0x79a2c8 -> 0xc0a56c ->
  0xc0a614 -> 0xc0765c(mgr, 2, ...)) is a camera request (target him, offset (0, 500, 300), pitch -60 degrees as u16
  angles, 1.0), at the start of his launched flight (0x78321c) and at her 16/6: not the burst, not ported. 4U's em
  message dispatcher 0x687998 has two death messages: type 5 = the death decision 0x92c0a4 (= GU 0x9b2bc, the same
  start), type 6 = 0x948614 (= GU 0x9c2b4: 0x921dfc(13) bits into W+0x7993, then 11/8). His 11/8 (4U 0x77c91c case 8 =
  GU 0xfdbdb4 case 8, KEPT by GU) runs after a launched flight its own script (4U 0xfdd684 = GU 0x17ee3e0: (b, 0) (4, 1)
  (2c, jump-arc data) (37, 2) (d, 0x8c) (0, motion 0x350)); motion 0x350 is Desert-only (4U em094 bank 3 slot 0x50, 165
  frames; GU's em076_00 bank 3 has 71 slots, ours 81) and posts MEF id 14 = em094_204 at frame 1 (our PSL em076_01_3
  entry 0x50 and PEL u list 1 id 14 carry it): the burst. 0.1.7's death took the type-5 decision (11/1, a plain
  death in the air). Now launch_end: setHP(-1), then GU's type-6 reaction 0x9c2b4 (11/8 with that script). What sends
  4U's type-6 message at his crash is NOT traced (S: the crash blast GU dropped); the timing stays 10 frames after the
  crash. Not ported: 4U's stun check 0x78968c at the end of that 11/8 (GU's twin stores rec+0x2bd into the pair's
  +0x78). buried_entry also needs his HP > 0 (never a corpse). Module only (subsdk1 + IPS); arcs = 0.1.10's (74 files
  equal); data files: version byte. Not played.
- 0.1.11 test (2026-11-11, log 19-08-08, 11372). The user: right after the burst a new Desert Seltas spawns again, and
  the green shots are not gone. The log (C): his 7/64 -> 7/65 throw (her 7/80..7/82), the shatter at 03:02.69, 11/8
  with motion 0x350 for 138 frames (the burst ran), then at 03:05.08 (2.4 s after) the restore: buried_entry ->
  6/3, and one frame later 6/1 (he dug out by himself). Her shots' ground splash took her 0x128 copy; two of his 0x13a
  posts were still GU's (kind 1 at 02:58.43 in 7/64 after his 7/57 shots, kind 0 at 03:18.69 in 7/2), with no mark
  before them: not from 0xfdca90 nor 0xfc6a30. Read since (C): every shell is created in the request (0x4a1c84 has
  one caller, 0x48c62c); the restore comes as soon as the body is gone (no corpse after a launched flight in both
  games); 6/3 (4U 0x784308 = GU 0xfd440c) digs him out when the pair's timer +0x54 runs out (timerDown 0x72128 = 4U
  0xb0709c) before his partner's 7/72, after testing partner present, her rec+0x2c0 == 1 (GU 0xbcb9c: 0 / 1 / 2, set
  to 1 by the damage handlers, S: in combat) and the same area; only his dig-in sets the timer (GU 0xfd3ec4 at its
  motion end, 3600 frames); 4U's 12/1 skips the dig-in, so the timer was 0. What fills it for a new male in 4U: NOT
  found (the other 4U writes to a +84 are timers of other states or of other objects).
  0.1.12: seltas_shots.c seltas_shot_any (hook 0x48C4F8, the request's start after Tigerstripe's entry hook: every
  0x13a whose owner, found among the 10 monster slots, is the Desert Seltas takes our copy); seltas.c buried_entry sets
  the pair's timer to the dig-in's 3600 frames (a DEVIATION until 4U's source is found: the user saw the Queen pull the
  new one out in 4U). Module only; arcs = 0.1.11's; data files: version byte. Not played.
- 0.1.12 test (2026-11-11, log 19-27-56, 11372, paused 5 min). The user: his shots fine also on her back now; every
  hit of his shots paralyses at once ("in MH4U wohl nicht so", not sure; "es geht nicht um den Bodenfleck"); her
  three big shots too bright; the discovery sound plays when she pulls the new one out; her very fast run with him on
  her back never came, her sprint is too slow. The log (C): no GU 0x13a left (18 fx lines, only GU's 2/20 cm200_040
  dust); 5 launches (7/80..7/82 -> his 7/64 / 7/65 -> burst), each new male buried (6/3) and pulled out by her 7/72
  1.3 s later (6/4); her fused charges 7/30 (motion 0x49c) x1, 7/39 (0x4a3) x3, alone 7/26 (0x499) x3; 7/73 -> 7/74
  x2 (take-off and landing), no 16/x.
  Read (C unless marked): paralysis = attack record +0x10 bit 2. Every GU paralysis record of every monster has +0x14
  = 0 (scan of GU's 137 enemy / ems arcs: Najarala, Nerscylla, Genprey ...); in 4U only the Desert shot records and
  4U Nerscylla's bite record 45 (em027 / em096) carry +0x14 = 4, and GU's own Nerscylla has 0 there. What 4U's hunter
  code does with it is NOT found (two heuristic scans of both codes found DTI walks only). The MH4U wiki: Beetle
  Cannon "always performed while fused if her target is Paralyzed" (S: the 5 launches). Her 7/73 (GU 0xf995f8):
  wind-up 0x48f, take-off 0x4a5 / 0x4ab with attacks 55 / 56 / 68, then 0xc752c(this, 0) (a target player for whom
  0x2c7d6c holds, S: paralysed) -> 8/0 (her flight, from which group 14 starts 16/x) or none -> 7/74 (land). Her two
  shots' EFLs carry 4U's Intensity 1 (em095_020 ff708c87 / ffb5fff0, em095_021 ff609e90 / ff7fb299), x2 nearly white;
  his em094_201 has none. Alert state rec+0x2c0 through 0xbcb9c(this, v): 0xa4444 plays the unit's request 22 only on
  0 -> 2 (noticing, 0x7eb28 / 0x7eee0), 23 on 2 -> 0; damage sets 1; the reset leaves 0.
  0.1.13: build_seltas_arc.py SHOT_1X (em095_020 / 021 at 1x, a DEVIATION as the dust); seltas.c buried_entry sets his
  alert state to 1 through 0xbcb9c when his Queen is not calm (no request 22; a DEVIATION by the user's rule, 4U's way
  not traced). Arcs (C, against 0.1.12's): only em095_020 / 021 differ; module; data files: version byte. Not played.
  Asked the user: paralysis on every hit in 4U?, and how the very fast run starts (stomps / horn / flight).
- 0.1.13 tested (2026-11-11; NO log arrived: the newest in Ryubing logs is still 19-27-56). The user: colours and
  brightness of all shots right; paralysis right (in 4U he had paralysis resist on by mistake: every hit paralyses in
  4U too, so the Desert shots' +0x14 = 4 stays as 4U's); the discovery sound still plays at each pull-out; the fast run
  still missing. So the sound is not his own request 22 (0.1.13 gave him alert state 1 at the entry, S: if that
  entry ran). Read (C): sSoundControl 0x4e4224 tracks the units' alert states (rec+0x2c0 reads at 0x4e4a7c / 0x4e4b40
  / 0x4e4cd8 / 0x4e4d28, unit slots at ctl+0x1b14 / +0x1b5a); GU's restore entry 12/0 (0xfcf3bc mode 2) sets rec+0x5c8c
  = 1 (as many classes' entries do; 0xaf3f8 reads it for this+0x10 bit 3), 4U's 12/1 does not. Dalamadur's port: 4U
  0x91b158 = GU 0xbcb9c(this, 1) at spawn.
  0.1.14: buried_entry also sets rec+0x5c8c = 1 (S: GU's restore-entry mark; the sound was not reported while he flew
  in, up to 0.1.9); test logs seltas_alert (hook 0xBCB9C: their alert changes, "its sound request 22" on 0 -> 2) and
  seltas_snd (hook 0x4E34AC, after the core's bgm_play entry hook: every stream request ch / kind / slot / id / next /
  force / lr while their quest runs, 80 per quest). Module only; arcs = 0.1.13's; data files: version byte. Not played.
- 0.1.13 / 0.1.14 tested (2026-11-11, logs 20-14-11 = 0.1.13 and 20-33-50 = 0.1.14, 11372). The user: the discovery
  sound still at each pull-out; the fast run still missing. The 0.1.14 log (C): the first discovery = his alert 0 -> 2
  (lr 0x7eb2c, request 22) + sSoundControl stream ch 4 kind 6 slot 0 id 0xa (lr 0x4e528c); at the restore (02:38.76)
  his alert 0 -> 1 from our entry (silent), then at 02:43.15, still buried, the same stream ch 4 kind 6 id 0xa. So the
  sound is sSoundControl's discovery sting: its unit scan 0x4e4224 raises ctl+0x1b9d at 0x4e4ef8 for a unit in battle
  whose slot mark +0x1b5c is 0 (and sets the mark), clears the mark while the unit's alert is 0 (0x4e4b18; his death
  set 0 through 0x75c40); 0x4e51c8 posts it from the flag (0x4e5240..0x4e5288, id 10, 14 for variant 4). Her moves in
  0.1.14: 7/35 x2, 7/61 -> 7/63 (with his 3/63 / 3/64, motions 0x493 0x448 / 0x494; his 0x447 / 0x449), 7/73 x6 ->
  7/74 x5 / 8/0 x1 -> 7/76 (landing, 0x486 / 0x50); 0.1.13: 7/26 x2, 7/30, 7/54, 7/59. Her charge handler 7/26 / 7/30
  (4U 0x78f0e8 = GU 0xf9739c) holds the same constants in both games (80, -60, 4, 60, -80, 1, -1, 30, 20, 104; C).
  Never seen in any log: 7/21 7/24 7/25 7/29 7/34 7/50 7/52 7/55 7/56 7/57 7/60 7/66 7/67 7/68 7/77.
  0.1.15: seltas.c seltas_sting (hook 0x4E5240): from his buried entry until 180 frames after he left the ground
  (QUIET_MAX 3600) the flag is cleared before the post (a DEVIATION from GU's sound control, the user's rule; other
  discoveries stay). Module only; arcs = 0.1.14's; data files: version byte. Not played. The fast run: the user to
  describe it (stomps / horn / flight, the end).
- 0.1.15 tested (2026-11-11, log 20-50-47, 11372). The user: the sound is gone; at one sprint "Steine am Boden, komplett
  schwarz"; when a new one appears under the ground the hunter stops briefly "wie erschrocken". The log (C): at each
  restore the sting flag was raised 21 ms after the buried entry (our "not played" line), i.e. sSoundControl announced
  him as a new unit right away (his alert 1 from the entry; the announce mark cleared at his death). Her rock units
  (C, tools: hide_grey_models on our arc): her ground EFLs em095_000 / 011 / 012 / 013 / 014 draw grey model units
  with her own effect model ef_em095 (3 materials), which the shared 'chunks' rule (CHUNK_MODELS) does not name, so
  they stayed (4U ff333333 / 727272 / 828282 / 999999 / cdcdcd / 787878 / 8e8e8e); GU draws them black. His ef_em094:
  none. The hunter's startle source is NOT traced (the announce flags are read only in sSoundControl 0x4e51c8).
  0.1.16: build_seltas_arc.py effects(): hide_grey_models with {ef_em09N} on their own soil EFLs (9 units, her five
  files; issue #6's rule, a DEVIATION as there); seltas.c seltas_mark (hook 0x4E4B18, MID_EXIT 0x4E4B20): the scan's
  clear of his announce mark skipped while his Queen fights (S: then his restore is no new unit and nothing is
  announced); test log seltas_hreact (hook 0x2F1C68 after Gogmazios' entry hook on 0x2f1c60): the hunter's reaction
  types while her new male is quiet. Arcs (C, against 0.1.15's): only those five EFLs differ; module; data files:
  version byte. Not played.
- The user on 0.1.16 (2026-11-11 evening, no new log: the newest, 20-57-54, ran 0.1.15): (a) a pin: "dieser Balken ist
  super winzig um sich zu befreien, man ist quasi sofort frei"; (b) "am Schwanz der Königin wirken die Texturen an der
  Unterseite des Schwanzes komisch"; (c) his shots from her back: the trail "muss immer zum Hinterleib gerichtet sein"
  (a shooting star), there it is "oft komisch verschoben".
  (b) C: her 4U 'XfB__m03_add' (mesh 29, g14: 112 vertices on the underside of thorax and abdomen, 54 % of the normals
  down, 90 on body vertices, bones 1 / 142..144) is a constant-colour additive overlay (CBMaterialConstant base (2, 2,
  2, 1), states BSAddAlpha + BSBlendBlendAddDestColor, RSMeshBias10); 4U em095 = em026 byte for byte, its 4 animations
  too. GU's em069_00 (Capcom's conversion) draws it on a constant shader (FAlbedoMapConstant, FConstantColorNoVertexColor,
  FConstantOutputLite, FTransparencyAlphaConstant) with the 4U keys 1:1 on $Globals.fConstantColor; the entry names are
  GU strings: 'Normal' (alpha 0 = off), 'Angry_Start' / 'Angry_Repeat' / 'Angry_End'. Ours was on 'add' (lit, cube
  reflection, alpha = the albedo's) and its 4 entries had no tracks (TRACK_MAP has no CBMaterialConstant), so it never
  went off. Fix (0.1.17): template 'add_const' = GU em076_00 mat 3 'XfB__m02_add' (its words and block equal em069_00's
  m03_add but the material type, and it has no animation block), gu_entries(extra=mrl_anim.CONSTANT_MAP). Our material
  now = em069_00's but the texture index; its animation block = GU's byte for byte (C); mrl_check OK. The other 4U
  materials with such tracks (em024 em040 em041 em042 em110 ...) keep their output (gu_entries unchanged without
  extra: 3734 animation sets compared, identical). His 'XfB__m02_add' (no animations) stays 'add': GU's em076_00 draws
  it on the same constant shader (a follow-up if the user sees it).
  (a) C: her 16/2 (GU 0xf9b250 = 4U 0x7924a8; GU dropped only the body-volume call 0x799e24(1)) went to 7/75 1.5 s in.
  Both games: from the attack frame (attack 57, GU's record in our file) while this machine controls her (this+0x7420 =
  EN_CONTROLLED, not a catch flag) the target check 0xc7318(3, rec+0x234, rec+0x230) = 0 -> 7/75; at the motion end = 1
  -> 16/3. The check (kind 1): hunter [[0x1885c58]+0x1c+4i], vt+0x88, the area, hunter+0x3266 = her record +0x1b6
  (+0x3266 = +0x321a at the hunter's reaction 0x2f6458 for cat 128 types 0 6 7 16 19 / cat 64 type 38). Why it fails is
  NOT traced; 0.1.17 logs it (seltas.c pin_watch: `dsport: pin ...` while she is in 16/x or 7/75 and 3 s after; hunter
  reactions `near her pin`). The 8/0 before it is a wait (0xf94540 group: motions 0x487 / 0x48b fused).
  (c) C: 4U posts (70, 10) = em094_201 with mask -1 for all four Desert subtypes 56..59 (standalone and from her back);
  the species' 6 / 13 share mask 1 of em025_001. Capcom's em076_00_001 is rebuilt (8 entries): mask 1 for kinds 0-5,
  mask 2 for kinds 6-8 (on her back), the two sets equal but for GU's tints and entry 6 (the 4U-derived 384-byte type-5
  unit): node +0x70 = 150.0 (0 in set 1) and unit +0x120 = 0 (0x12c000 in set 1). Our copy posts em094_201 (all units)
  for both ids, as 4U. Meaning of node +0x70 not traced (G: an offset or a delay) -> no change in 0.1.17. Kinds 6-8
  sh (FUP ints 144 200 0 -1, v1 (100, 0, 0), v2 (0, 275, 625)) differ from 0-5; 4U's subtype 57 motion not compared.
  0.1.17: her m03_add (above), pin_watch. Arc (C, against 0.1.16's): only her MRL; his arc identical; data files:
  version byte; module. Not played.
- 0.1.18 (2026-11-11 late, for the PR; the user: "bereite hier den PR vor ... diese Funktionen die für Testzwecke was
  loggen zu entfernen"): on upstream main e27c6ba (PRs #33 all languages, #35 core 3.0.0: the mod's own save files,
  Harvest Tours; #36). Main's 96 changed files taken as they are (git restore from origin/main, the Monoblos rebase's
  way), our hunks of the 9 files both changed re-applied by hand (allocations.toml, module/build.py items.c main.c
  notes.c port.c port.h, notes/porting-guide.md, tools/alloc.py). Main's Heaven's Mount G3 tour took 11372: her
  m10924 is now 11374 (checked free: no q%07d.arc, no quest_group entry, not in the event catalog 0x1595e98; 11369 and
  11373..11399 free too). package.toml: `class = "Neopteron"` (main's key; subtitle gone), requires_core 3.0.0.
  name_seltas.py on portdata.name_section. Chinese text (lang/zh_TW.toml, zh_CN.toml, 154 keys each, by hand: apply
  would rewrite the tables from this checkout, where the other monsters are not built): 29 strings are GU's own (exact
  English match in GU's GMDs and quests, e.g. "Netting Neopterons" = GU q11114's text, the client titles, "Reward
  hits 0..."), the rest this project's on GU's terms (沙漠 = GU's "Desert", 徹甲蟲 / 穿甲虫 Seltas, 重甲蟲 / 重甲虫 Queen,
  her items as GU's S.Queen ones, "+" = 改, 單手劍, chS 工坊); the two names this project's (no Chinese release or fan
  name found). translate.py check: 0 missing, 0 stale, 0 unseen glyphs (訕 蟑 replaced). Her LBG / GL lines carry
  " (4U)" (GU's own Battalion Strafer / Seltas Fortitude, above "Names"). Test logs left out: diag, part_watch,
  flight_log, pin_watch, seltas_hreact, seltas_alert, seltas_snd, seltas_dsq_act (hooks 0xF9C8B4 0xBCB9C 0x4E34AC
  0x2F1C68) and seltas_shot_fx (0x4A1E50); the short lines inside the working hooks stay (as the other ports').
  Checks on the PR tree (Tools\pr_folder_desert_seltas.py's): check_repo rules over all 508 blobs, alloc (13 OK), py_compile 191, ci_compile 117
  C files, build.py --list; tools/test_save.py fails 4 checks on main e27c6ba itself (unchanged by this port).
  Package (C, against 0.1.17's): 11372's files gone, 11374's and the 12 chT / chS quest GMDs new, the five other quest
  arcs changed (their Chinese GMDs), every monster / armor / weapon arc identical. Not played on 3.0.0.
- 0.1.17 tested (2026-11-12, log 14-35-47, core 2.0.0, 11372 = m10924; the quest ended after 4 min 22 s with her at
  68 %). The log (C): three launched flights (7/64 -> 7/65), each ended in his burst (11/8, motion 0x350, no corpse);
  each time a new Desert Seltas entered buried under her (12/1 -> 6/3) and she pulled him out (her 7/72, his 6/4); the
  first one rode her again (7/66) and fired on their own shell families; her reactions 10/7 from her 4U table (4 times);
  the discovery sting cleared 3 times, and no hunter reaction logged while they came out; she was angry for 90 s; her
  7/24 and her burrow 4/0 / 4/3 once each; no pin (no `pin` line); no error line of the mod. The user (asked about what
  no log shows): her tail underside glows only in her anger (0.1.17), no black stones any more (0.1.16), and the hunter
  no longer flinches when a new one comes out (0.1.16). The user's choice: the PR goes with this test, so 0.1.18 is not
  played on 3.0.0 (the PR text lists what it changes against 0.1.17).
