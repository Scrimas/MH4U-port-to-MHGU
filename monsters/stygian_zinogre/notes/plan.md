# Stygian Zinogre port: plan (approved 2026-10-27)

Source: MH4U em049 (class uEm048, shared with Zinogre em048 and em114). Target: GU Zinogre class uEm057_00,
**variant 1** (GU ID 0x139, arc `nativeNX/arc/enemy/em057_01.arc`). Process: notes/porting-guide.md; closest model:
monsters/tigerstripe_zamtrios/ (a 4U subspecies run by GU's own class). Phase 0 raw notes:
dump/scratch/stygian-session/phase0-notes.md. C = confirmed in code/data, S = strong, G = guess.

## User's answers (2026-10-27)
- **Quest ranks:** "Adapt to MHGU, because 4U's G2 isn't equal to GU's G2. Look to the Stygian quest compared to
  regular zinogre on 4U, then look at regular zinogre quests on GU and place the stygian zinogre quest accordingly
  (he's harder than regular zinogre). Both High Rank and G-rank."
- **Heaven's Mount:** port it faithfully (4U stage 5; three quests: m10607, m10930, m11010).
- **Charge:** "rather similar (not identical, but similar enough) to regular zinogre, his animation isn't the same:
  it's a slow walk during which he charges, and when he's fully charged the transition between the two forms
  (uncharged/charged) is the same as zinogre".
- **Extra step:** edit install.sh (gitignored): the new switches in SWITCHES, the monster in its list.

## Phase 0 facts
- 4U em049 = "Stygian Zinogre" (C, emName). Class uEm048 (C: no uEm049 DTI), vtable 0xe68464, code about
  0x843000..0x859000 (S). em114 is also named "Zinogre" and shares every em test with em048 (C).
- 4U em-number tests in uEm048 (C, under-counted scan): 64 `cmp #48` + `cmp #114` pairs (Stygian takes the other
  branch) and 7 `cmp #49` = about 71 Stygian sites.
- 4U em049.arc (C): own model (+ tail), textures, materials, 29 EFL, MEF em049_1. Shared with em048: the motion
  banks em048_0/2/3, camera e048_cam, AI file em048_cmd, sound call em048, SE files (70 vs 68).
- GU: uEm057_00 ctor 0xeee870, size 0xcb20, vt 0x17d19bc, code 0xeee870..0xf09734 (C / S). Arcs em057_00 and
  em057_04 (Thunderlord) only (C). Variant byte this+0xb5f5: 99 `cmp #4`, 7 `cmp #0`, 7 `cmp #1` (C, unverified
  registers).
- BGM: 4U has only bgm_em048 (C); GU ships bgm_em057_Zinogre (C): probably nothing to port (S).
- 4U icon index 50 (C: board value 50 on its quests, 49 on Zinogre's; the preview PNG shows 50 = Stygian's art).
- Quests (C): Hub HR6 m10603 (F. Seaway), m10607 (H. Mount), m10608 (Arena, + Brute Tigrex), m10612 (Arena,
  + Zinogre), m10616 (V. Hollow); G2 m10925 (V. Hollow, + Brachydios), m10930 (H. Mount); G3 m11010 (H. Mount);
  caravan m00907 (V. Hollow), m01029 (F. Seaway, + Seregios); arena m21003 "Grudge Match: S. Zinogre"; event
  m60205 "A Song of Extremes" (Arena, + Gypceros). GU has Frozen Seaway (GU 14, C), Volcanic Hollow and an Arena
  (S); Heaven's Mount is not in GU (S).

## IDs (proposed; written to allocations.toml in step 2 after `tools/alloc.py` checks them)
| what | value | note |
|---|---|---|
| GU ID | 0x139 | em 57, variant 1 |
| registry index | 143 | after shah_dalamadur_tail (142) |
| save slot / name entry | 110 / 110 | was 110 / 109: the quest result's size record names the save slot, so it showed 'dummy6' (test 2026-10-28; tools/alloc.py now checks name entry = save slot) |
| Notes entry | 127 | the last free Notes save bit (123..127): a later monster needs the table extended |
| ui_icon / icon_4u | 203 / 50 | checked visually 2026-10-28 (49 is Zinogre) |
| file IDs | the next range after 0x108bf | |
| items | appended after Dalamadur's 30 (from 3021) | 4U material list |
| quests, board slots | step 6 | placement by the user's rank rule |
| stage alias | step 7 | Heaven's Mount |

## Phase 1 results (2026-10-28; details in phase1-variant-map.md and phase1-assets.md)
- 68 Stygian-specific 4U sites: MATCHED 10, DIFFERENT 23, MISSING 33, UNRESOLVED 2; no Stygian-only actions or
  motions; no Thunderlord-only path reachable for variant 1 (C). GU kept the charge walk (flag, timers), the
  charge-gain rows, the 10/112 skip and 10/110's table; GU dropped every Stygian charged attack index (variant 1
  gets the uncharged Zinogre index), the orb / shell / effect posts, and whole 4U move families (7/2-13, 7/15, 7/42,
  7/160-220, turn 2/47-62, 2/75-77 and some parameter sets): 26 of the actions 4U's script names end at once in GU.
- Assets: 4U motions (GU re-encoded all of Zinogre's), 4U camera, own cambodydata / dttune / attackdata (GU retuned 16
  shared attack records; Stygian's own indices 48-73 unchanged), shared dtbase / bodydata / hitsize.
- Decision (faithful rule): port the 4U handlers of the families GU dropped or restructured (GU's look-alikes are
  other moves: other motions), run from our slot-125 hook for variant 1; keep GU's handlers where GU's same-number
  case runs the same 4U handler, with hooks for the DIFFERENT sites; port the shells (uShell046 orbs, uShell044
  subtype 3, uShell010 135 / 236) and effects; AI table = 4U em048_cmd in GU's language (area moves), 4U numbering.

## Behaviour plan (step 3)
- B1: reachable 4U actions = closure of em048_cmd's native actions + the follow-ups handlers chain to.
- B2: per reachable action: GU same handler and parameters (keep) / GU handler without that parameter set / no GU
  case (port).
- B3: port the 4U handlers (literal, 4U call order and values; notes/port.md framework), dispatched for variant 1.
- B4: DIFFERENT fixes in kept GU handlers: 13 attack-index ladders, 4 orb posts + 7 vt170 event posts, the 1/6 charge
  frame-loop posts, the charge-change effect id.
- B5: shells: uShell046 (orb records, homing on em 49), uShell044 subtype 3, uShell010 135 / 236.
- B6: AI table translation (GU area-move scripts, map cases 4 -> 14, 15 -> 12, 11 -> 9, 5 -> the Heaven's Mount alias;
  GU's extra group-1 scripts its class picks by number; 4U's group 21).
- B7: AI conditions: 4U slot 51 vs GU slot 133 per sub-code; 4U base query 0x9431f4 cases 64 / 65 (Stygian = subspecies).
- B8: own attackdata (4U em049 + GU's records 75 / 76, GU byte 28).

## Phase 2 action study (2026-10-28, phase2-actions.md)
- 208 reachable 4U actions (C, the same for em 48 / 49): KEEP 89, GU-PARAMS equivalent 11 (7/21, 7/31, 7/40, orb
  family 7/32-34 61-63 66 87 = GU efa930 with 4U params + our shell post), GU-PARAMS not equivalent 20, PORT-chain 16
  (GU handler minus 4U's follow-up: GU ends with setActionW(2, 4) + think = a 120-frame wait, then GU's AI), PORT 55
  (12 4U functions, ~4150 instructions: 0x845fe8, 0x84383c, 0x848310, 0x84dd44, 0x853704, 0x854088, 0x84f50c,
  0x84f744, 0x84fbe4, 0x84ff7c, 0x850714, 0x852780), n/a 17.
- 4U's remap (slot 46) is needed too: GU slot 127 lacks 2/63<->64 .. 69<->70, 7/4<->5, 7/186/187 -> 215/216 (rank >= 5).

## Behaviour work order
- W1 framework: ported handlers run from the slot-125 hook for variant 1 (replace the dispatch for our actions; GU
  dispatch for KEEP); GU-PARAMS-equivalent actions call GU's handler with 4U's params; remap hook on GU slot 127.
- W2 PORT-chain + GU-PARAMS-not-equivalent: GU handler with the 4U follow-up / branch restored, or ported.
- W3 PORT handlers (literal 4U translations), in families; one helper at a time owns new files.
- W4 the DIFFERENT fixes in KEEP handlers (B4); W5 shells (B5); W6 conditions / ops (B7).
  Attack indices (C, 4U sites read 2026-10-28): one entry hook on GU attackEx 0x7dc2c (GU attack 0x7df94 = attackEx
  with flags 0 tail-branches into it; first two instructions push / sub sp: displaceable), GU charged test 0x81790
  (GU's own ladders use it). Table (action, slot, GU's variant-1 index -> 4U Stygian index, condition):
  1/4 1/21 slot 1 25 -> 51 charged, none uncharged (846dc4); 1/4 1/21 slot 0 33 -> 54 always (846e5c); 2/46 0 11 -> 60
  charged (843720); 7/0 7/1 7/207 7/208 0 1 -> 59 charged (847e74 8480d4); 7/22 7/112 7/201 0 10 -> 50 always
  (84b0d4); 7/89 0 28 -> 69 charged (84dc44); 7/109 0 31 -> 66 charged (84f24c); 7/126 0 26 -> 52 always (84f38c:
  handler param r5 != 0). GU's flags kept (S). Ported actions pass 4U's indices themselves (not in the table).
- W7 first in-game test (user's go), then iterate on the log.

## Status (2026-10-28 morning; nothing installed, nothing committed)
- Done: allocations entry (registry 143, items 3021..3035, armor 4 series / 2 create / 14 process, models 169 170
  438 439); package.toml; build.sh steps dt / arc / name / items / gear / pack (all pass); arc em057_01 (own model +
  tail, textures, materials + 4U material animations, XFS, 4U motion banks + GU 2:42, 4U camera, translated AI table,
  effects, sound bank, attackdata, cambodydata, dttune, carves); NAME; materials + BUI2 / BUI4; armor (Zinogre U /
  Z; ore substitutes and level-row swaps listed for review in gear_em057_01.py).
- Module: em057_01_diag.c (action / motion log, TEST_HP_PCT), em057_01_moves.c (dispatch table: GU-PARAMS = rows,
  4U remap hook on slot 127); hooks em057_01_act 0xf03620, em057_01_remap 0xeef31c (module/build.py). Core builds.
- Shared-tool change: tools/mod4u2gu.py reads 4U vertex format 0x6180300A (rigid + tangent; other outputs unchanged by
  construction: that format used to abort).
- Done: port batch A (em057_01_mv_a.c, 27 rows: 2/47-52 2/61-70 turns, 2/72 73 75-77 79 80 backstep, 7/4 7/5, 7/14,
  7/15; no guessed mapping); attack-index hook (em057_01_fix.c, GU attackEx 0x7dc2c, the W4 table).
- Done: port batch B (em057_01_mv_b.c, 22 rows: 0x848310 7/2 3 6 7 16 68 69 188 189 with its G-rank lead-in to
  7/217; 0x84f50c 7/186 187; 0x84fbe4 7/215 216; 0x84b548 7/35 36 67 54 200; 0x84ab60 7/51-53 202). One guess (G):
  the sound posts (GU 0x4efd74 with 4U's request ids 209 / 225 and joints; log "szport: snd", 4 lines per 4U site).
  S: 0x92e9d4 = restApply, W+0x1d2 = this+0x73e8. Shared 4U -> GU map moved to em057_01.h (batch A, the dispatcher
  and the fix compile to identical code; batch B's sound helper is now sz_snd / sz_snd_pair).
- Done: port batch C (em057_01_mv_c.c, 18 rows: 0x853704 7/160-175 with its own G-rank lead-in to 7/218, 0x854088
  7/176 177 with its own G-rank gate to 7/215 / 7/216; no new guess). 7/135 / 7/136 (from 7/171 / 7/175 at frame
  80, G rank only): no 4U handler, the 4U dispatch is a no-op (C) and no generic timeout was found (S), so 4U likely
  holds the monster in a dead action until a reaction (S). No row added: GU ends them at once (0xca10c). To settle
  with the user's 4U memory once 7/217 / 7/218 run (open).
- Done: port batch D (em057_01_mv_d.c, 5 rows: 0x84f744 7/190 191, 0x84ff7c 7/217, 0x850714 7/218, 0x852780 7/220;
  no new guess). The uShell010 post goes to the logged stub sz_shell010 for B5; 0xc094e8 is no post but a pure
  function (the ground hit's surface class), kept literal in sz_effect_c094e8 (S: GU's attribute bits mean the same;
  logged). New maps (C): ground ray 0x2bad24 = 0x183ad0, 0xaad40c = 0x2329b8, 0xd076b0 = 0x7c6914, W+0xd3a = rec+0xb0a.
- Fixed in batch B (found by batch D, checked in 4U): lead_217 stored (side, 0x3f, 0x3e) in work+0x115..0x117; 4U
  stores 0x848310's (side, r2, r3) (C: 0x848a78..0x848a8c, only entry 0x848390, before r5 / r7 are reloaded), so
  7/217 would have hung at frame 62 in G rank.
- Done: port batch E1 (em057_01_mv_e.c, 12 rows: 0x84a59c 7/205 209, 0x84bad8 7/192-197 204 with class 0x855c38,
  0x84d488 7/203 206, 0x842b44 13/3). One guess (G): 13/3's rest-target test, 4U class 0x852d74 (partner object in
  11/8 11/9 14/1, else a type-6 map object), runs as GU 0xb2ddc at the same site (GU's own target; GU returns 1 with
  no target where 4U returns 0); log "szport: 13/3 rest target". S: GU 0xb0eb0's scale vector {1, 1, 1} (logged
  once). C: 0x94461c = 0xb0eb0, 0x936ac0 = 0xc43bc, 0x92d0d4 = 0xc46c8, 0x911c44 / 0x92f720 = seqStart1 / seqPoll1.
  Batch B now logs its (unreached) r3 4 / >= 6 case at frame 102, as batch D does.
- Done: port batch E2 (em057_01_mv_f.c, 7 rows: 0x847274 roar 1/39 42 43, 0x847a40 lying wait 1/40 -> 1/41,
  0x847bdc stand-up 1/41 -> 1/42, 0x84dd44 7/113 115 = the charge transition (S: sound 207 and uShell044 3 as the
  charge walk, burst hitbox 53 at frame 278; the charged flag is not set there, its source not traced). No guess in
  executed code. Logged stubs: sz_shell044 (B5), sz_effect_c0819c (event-20 effect), sounds sz_snd_312484 (sndPos)
  and sz_snd_390f9c (sound events) plus local ones (GU's class posts no sound: a sound batch decides how GU plays
  them). 4U 0xc0ca90 builds a stack descriptor nothing reads: left out. Open (G, matters): 1/43's 0x939c00(32)
  (W+0x7e80 |= 32, W+0x7e81 &= ~32, status timers 0x91de40) and 0x94c980 (W+0x540 = 3600) are logged no-ops; 4U vt47
  0x8572e0 / 0x8572ec calls them too, so map them through GU vt129 eefed0 (B7). B4 addition: GU ef45e0 (KEEP 1/9 34
  37 38) drops 4U's frame-66 joint-4 effect 0xc0819c.
- Done: batch S (em057_01_start.c, 2026-10-28): 4U vt47 0x857060's action-start work vs GU vt129 for every s_moves
  row. vt47 switches on cats 1 2 3 10 11 (tables 0x857118 0x857330 0x857398 0x857510 0x8577f8), then a common tail
  0x857914 (all cats but 11) whose cat-7 part is the charge drain 0x858cec(num) (charged and work+0 >= 1; cost 1 / 3 /
  5, at rank >= 2 -5 -> -2, -3 -> -1, -1 -> none; clamp 1..100) = GU ef0c68 with GU's own 249-row cost table (C).
  GU's cost is 0 for 22 ported rows (7/2 3 21 31 166-169 172-177 186-189 200 215 216): sz_action_start adds 4U's
  (C). Since 2026-10-28 (user's OK) it runs from an entry hook on GU vt129 0xeefed0 (em057_01_start@eefed0), at the
  action start itself (the first-dispatch-frame call and its pending-request skip are gone). Nothing to undo (GU adds no start work 4U lacks, C). 1/39-43 stores
  (W+0x53a 0x544 0x545 0x790d, 0x9482d4 / 0x94c980 = W+0x540 3600, 0x939c00(32)) have no GU field or site: logged
  no-ops. Bit 32 of W+0x7e80 (GU rec+0x5e08) is not rage (rage = W+0x530 == 1, dalamadur class-study.md): G, a rested
  state after waking (4U also sets it in spawn state 9 of 0x93f6e4); GU tests bit 32 at 50 sites but never sets it (S).
  Limit: start work runs on the first dispatch frame, not inside setAction (a vt129 hook would need the user's OK).
  Open (MP sound): 7/176 177's G-rank branch repeats sz_snd_pair every frame on non-controlling machines until the
  action arrives (4U not checked).
- Done: B7 (AI ops / conditions; phase1-assets.md B7 bullet). Found 4U's **rest state**, which GU removed (C): flags
  W+0x53a (1 at the starts of 1/36 1/39, rewritten per hit 0x924b18, cleared by 0x937664 which hands it to W+0x544),
  W+0x544 (starts of 1/36 1/39), W+0x545 (starts of 1/41 1/43), bit 32 of W+0x7e80 = GU rec+0x5e08 (0x939c00 at 1/41
  and 1/43; GU tests it at 50 sites, never sets it, S), timer W+0x540 = 3600 (1/36 1/39 1/41: 0x9482d4 / 0x94c980;
  while > 0 the status build-up 0x93732c skips a branch); 0x93f6e4 clears and sets them in its spawn states. Readers:
  condition 11 (g16 s0: lie down 1/35 or roar 1/39), op 0x80 / 0x91 (g0 s3: a 5 % target pick, kind 5), 0x93732c. KEEP
  starts with rest work: 1/35 (W+0x790d = 1), 1/36 (W+0x53a, W+0x540, W+0x544, W+0x790d = 3), 1/37 (W+0x790d = 4, S).
  Today 4U's answers on our state equal GU's (nothing sets the flags). To port as one unit (setters + clears + timer +
  readers, then wire the two B7 hooks); what it does in play: ask the user.
- Done: B5 design study (notes/b5-shells.md, 2026-10-28; awaiting the user's answers and OK). Corrections (C): 0x6639a0
  posts uShell003 (sz_shell010 is misnamed; Zinogre's 129 / 235 are uShell003 too); the (58, 12) effect is 0xc08628 at
  0x85849c (0xc094e8 stays the surface class); 2/40 (charge walk) also posts uShell044 3 (0x84538c 0x845580); 0xc0819c
  is a screen radial blur (uMhRadialBlurFilter). Recommended: our own GU shell classes, literal 4U ports, own request
  and resource file (never GU rows 247 / 248: m10612 loads Zinogre and Stygian together); a 10-step plan there.
- User 2026-10-28 (third round): B5 answers in b5-shells.md 7b, plan approved ("Continue on the port"); roar blur:
  research it; the vt129 action-start hook is OK (start work at the exact action start instead of the first dispatch
  frame); rest state: "what you described doesn't fit what I remember, but maybe my memories are wrong" (trace what
  the rest state does in play before porting it); 7/135 / 7/136 wait for the first play.
- Done 2026-10-28: B5 steps 1-3 (helper, reviewed): tools/shelldata4u_em057_01.py (unicorn run of the 4U static inits
  0xd27970 / 0xd1daf0 and GU's 0xf06104; --check = module/em057_01_shelldata.h matches the run), the header (orb
  records, pillar frame tables, axis (1, 0, 0, 0): was G, now C; GU 0x2132a50 = 4U 0xfeba98, C), and
  build_em057_01_arc.py: shell family shell\em\em057_01_shell01 (GU em057_00_shell01 renamed, def file ID 0x108d6 as
  an EXTRA_ORDER extra), HDS 0 pillar / 1 blast 135 / 2 blast 236 / 3 orb and HTS groups 0..3 (each asserted against
  the 4U records and GU's twins), PEL list 2 extra records 3202 3205 3203 3253 3215 3217 3267 3219 3220 3222, the
  shell sound ids asserted in our request. No shared tool changed; arc 802 entries; module unchanged (937848 bytes).
  For step 4: GU row 247 likely goes at param+4 (S, as Dalamadur / Gogmazios pass Kushala's 175); the module ends
  record 3220 itself (4U releases it at frame 50).
- User 2026-10-28 (fourth round): quest core change approved ("Build it").
- Done 2026-10-28: the quest core change (notes/quests.md 3 "Built"; byte +10 traced = the board colour row) and
  quest 10775 = 4U m10603 (build_em057_01_quest.py; 23 bytes differ from template q10724, all intended). The
  reward rows needed OTHER_4U_GU (items_em057_01.py): every same-name item of the 10 ROM quests' rows mapped; 9 4U
  items have no same-name GU item (S.Queen Concentrate, Azure Rathalos x3, Brute Tigrex x4, Strong Armor Sphere),
  to decide with m10607 / m10608 / m10930.
- User 2026-10-28: "Test now"; Dalamadur's HR7 colour row "Fix it" (quest_group_rename sets +10); then, asked
  whether to let him use many moves: one test at 50 % HP (at 5 % he would start in his weak / limping state, S).
  Test 1 installed 12:23:17 (GOG_DEFINES="TEST_HP_PCT=50", subsdk1 940852 bytes, cmp OK): quest list append, quest
  10775 on the HR7 board, the clear-write index log, every ported move so far (action log lines now carry HP % and
  charge, cap 3000 lines); shells still log only (no orbs / pillars / blasts). First try: endless loading (the
  rename matched Stygian's empty slots against GU's quest 0, notes/quests.md 3); fixed and reinstalled 12:31:37.
  Second try: the quest loaded, Stygian spawned (test HP 4156 / 8313, action 2/32), then a crash 0.16 s later in GU
  slot 132 0xef3214 (0xb0cab0 writing through this+0xcac4 = 0): GU's material charge glow needs GU Zinogre's type-52
  material ('normal_Loop' / 'tyoutaiden_Loop' / 'Death'); 4U's matching slot 50 is the empty `bx lr` and Stygian's 4U
  model has no such material (C, em057_01_fix.c em057_01_glow_c). Hook em057_01_glow@ef3214 skips slot 132 for
  Stygian; reinstalled 12:41:10 (940972 bytes, cmp OK).
  Third try (log 12-41-36, C): no crash, 6.7 min, 51 charged actions, clear write "list index 1509 of 1520", quest
  shown cleared. User: GU Zinogre assets on him ("Furr, draconic energy, small aura on his back") and "dummy" as the
  size record's name. Found (C):
  - size record: the result screen names the save slot (110) while his name sat in entry 109 (the tails take slot 109
    without a name of their own): name_entry 110 (allocations.toml; tools/alloc.py now requires name_entry =
    save_index for every monster with its own slot).
  - effects: GU posts its Zinogre effects through its own slot 116 0xf060c4(self, id, req) (ids -> PEL list-2 records;
    phase 1 looked for 4U-style (57, n) constants and found none; the "effect controller this+0xb640 vt[0x1d0]" of
    phase1-variant-map.md C is a misread: `ldr r0, [r2], r0` loads [this], so it is the monster's own slot 116, and
    req = this+0xb640). The 4U twin of GU's looping charge effects is an aura controller OUTSIDE uEm048, 0x322f18
    (one looping effect per state: em049_000 masks 2 / 4 / 1 by charge stage, em049_011 when enraged; Zinogre
    em048_000 / em048_011 = GU's em057_00_000 records 30 / 31 / 32 and em057_00_011 records 1120 / 1121, same joint
    and masks). em057_01_efx.c (hook em057_01_efx@f060c4) swaps 4U Stygian's records in (3200 / 3225 / 3250 / 3211,
    charge change 3202 / 3205 + 4U sound 210 / 213); GU-only Hyper id 48 (em057_00_500) not posted, logged.
  - em049.arc ships nine em048 EFLs (004 006 008 014 018 021 030 031 102), exactly the group-48 files MEF em048_0
    names; the arc builder dropped them as "not shipped": 17 motion-effect records were missing. Now converted.
  - fur: Stygian's own 4U texture (em049_04_BM, fur area a warm beige-tan about b8a488) with the same 4U material
    constants as Zinogre's (fur diffuse 0.9 in both; 4U Zinogre's fur texture is olive-yellow about b8bd95, GU
    Zinogre's a saturated gold); the 4U icon shows Stygian's fur ash grey. User 2026-10-28: sent 4U shots (forest) and
    the MH4U HD project's textures (look only, not used). Measured (C): the fur's chromaticity in the 4U shots equals
    ours ((0.352, 0.342, 0.306) / (0.352, 0.340, 0.307)), ours ~15 % brighter; the HD fur is the same hue, ~20 %
    darker. Cause found (C): 4U's iMaterialStdSpecularMaskType 2 (body, head, fur, tails; Gogmazios' are type 1)
    takes the mask from the NM_MIRROR's left-half alpha (means 28..36, fur 18), not the BM alpha (255); the builder
    used the BM alpha (em089 rule), so body and fur shone at a near-full mask. Fixed in textures() (spec_type);
    em057_01_01 / _04 BM+A means now 36 / 28 (fur 18). Dalamadur's em090 body01 / far are type 2 too (to check
    with the user: their output would change).
  - not done in this round: vt77's ground hit em049_003 + 205 (needs the vt77 / vt170 matching of B5), the aura loop
    sounds 201 / 202 / 203 (sounds batch).
  Test 2 (log 13-51-10, build 13:50:36): no crash; user: "everything is fine" but auras stacked into "a full ball of
  effect", fps falling, cleared when the monster changes area. Cause (C): the swap put 4U's looping em049_011 into
  GU's enraged post (uEnemy 0xa4274, every 30 s, handle discarded: GU's em057_00_011 ends by itself). Fix: 4U's aura
  controller 0x322f18 ported (em057_01_efx_frame, every frame from slot 125): one aura (state none / enraged / charged
  / stage by work+0 25 / 50 / 75, 4U slot 51 query 1 0x857a5c), a new state kills the old one (GU 0x32a400 mode 1:
  mode 0 only asks it to finish), handle in GU's type-52 fields +0xcac4 / +0xcacc (written only for a type-52
  material, read only by the skipped slot 132: C), dropped untouched on an area change; GU's aura and enraged ids
  answer 0. This also gives 4U's priority (enraged aura instead of the charge aura). Also found: the test-2 data file
  was the 11:44 one (gen/*.sec rewritten but not re-packed with tools/portdata.py pack), so the name entry was still
  109 in that test (one byte, offset 721; FILE identical). Re-packed and installed 14:08:41 (942252 bytes, cmp OK).
  Test 3 (log 14-09-33, C): name entry 110 = Stygian Zinogre on the result screen; auras 0 -> 1 -> 2 -> 3 -> 4 -> 3 ->
  0 in area 3, 0 -> 1 -> 0 in area 9, one kill per change; clear write list index 1509; no crash. User: "Done, it's
  all good". The first frame logged "255 -> 0": GU's ctor sets +0xcac4 = 0 and +0xcacc = -1 (eee8f8 / eee950),
  harmless (em057_01_efx.c comment corrected).
  B5 step 4 review against issue #6 (user 2026-10-28: "do not straight up copy" Dalamadur's shells): charge gate of
  the paw blast and the ground-variant problem found (C), notes/b5-shells.md 8; revised step-4 plan sent for OK.
  User: "Go ahead" (step 4 as revised); the other ports' ground fix "Not now", written to the uncommitted ISSUE_6.md.
  Done: B5 step 4 (notes/b5-shells.md 8d): em057_01_shell.c (GU uShellEnemy base written from the 4U / GU code +
  the uShell003 135 / 236 blast class), em057_01_mv_d.c (sz_shell010 stub -> sz_shell003, the ground ray shared,
  em057_01_slam_fx_frame = 4U vt77 em049_003 with mask 1 / 2 + sound 205), em057_01_efx.c (point posts through
  0x53b500 with rotation and ground overrides, sz_snd_at), em057_01_diag.c (the per-frame call). No data change.
  Test 4 installed 14:59:16 (TEST_HP_PCT=50, 948180 bytes, 0 warnings; cmp OK: subsdk1; arc and data unchanged).
  Test 4 (log 15-04-45; user: "he never did his paw slams, neither charged nor uncharged"): 150 actions in 6.5 min,
  no slam, no crash; tests 2 and 3 had none either (0 of 443). Cause (C, em057_01_ai.c header): the AI gates them
  by quest rank. Stygian's selectors g0 s15 / s16 open with op 0x6a (quest rank, 4U 0x69ae70 = GU 0x3a8d68), case 5
  = rank >= 5 (type 26 in both evaluators); g1 s84's 7/14 lead-in needs rank >= 4. 4U ranks (quest file byte 0x8b, S):
  his HR hub quests 3, caravan 2, G 5; our GU quest 3. So 4U's HR Stygian never paw-slams (the log's picks match the
  rank-3 lists); regular Zinogre's table does below G (7/194 / 195 -> 2/63-70). Test switch TEST_QUEST_RANK (user:
  "Force G rank in tests"): GU's rank getter answers it in Stygian's quests (em057_01_rank hook, test builds only;
  install.sh SWITCHES). Test 5 installed 15:33:35 (TEST_HP_PCT=50 TEST_QUEST_RANK=5, 948436 bytes, 0 warnings; cmp
  OK: subsdk1, arc, data).
  Test 5 (log 15-34-45): 5 blasts and 7 vt77 ground hits posted, no crash. User: the red blast is "visually far from
  the paw impact", for every charge state, "shifted, towards the left of his body. But unsure"; "parts never show".
  Cause (C for the code, S for the effect; notes/b5-shells.md 8e): our world records carried efl4u2gu's attach tail
  (transform mode 2), which needs a target; sz_efx_world posts with none. Fix: efl4u2gu PEL_TAIL_WORLD (GU's world
  code-post tail, mode 3, opt-in record key world) on Stygian's 7 joint -1 placed-once records; arc rebuilt (only PEL
  u list 2 records 3203 3217 3219 3220 3222 3253 3267 changed; data file unchanged); read-backs after the unit build.
  Test 6 installed 16:06:38 (user: "Install test 6"; TEST_HP_PCT=50 TEST_QUEST_RANK=5, 948532 bytes, 0 warnings;
  cmp OK: subsdk1, arc, data).
  Test 6 (log 16-07-24; user: "All good"): 91 actions, no crash; 5 vt77 ground hits (7/6, 160, 164, 172, 177; three
  charged with sound 205) and 4 blasts (sub 236, each ended at age 11), every read-back "placed at" = "asked" (C).
  Placement fixed; B5 step 4 done.
  Done: B5 step 5, the dragon pillars (notes/b5-shells.md 8f; user "continue the port"): 4U uShell044 subtype 3 as
  uShellEm057_01Pillar in em057_01_shell.c (gather em049_020, burst em049_019 at the slot's start, sounds 217 / 218,
  HDS 0), posted by 7/113 115 (stub replaced) and three mid hooks where GU kept 4U's frame loops without the posts
  (0xef4484 charge stance, 0xef6450 / 0xef6338 charge walk steps 1 / 2; module/build.py HOOKS). Built 953132 bytes, 0
  warnings; not installed yet. User: "Continue to the orbs first" (test pillars and orbs together).
  Done: B5 steps 6 and 7, the dragon orbs (notes/b5-shells.md 8g): 4U uShell046 as uShellEm057_01Orb
  (em057_01_shell046.c: legs, sine arc, wobble, homing with GU's own target twins, impacts, effects, sounds) and the
  volleys (em057_01_posts.c: entry hook 0xefa930 + mid hooks 0xefaa6c / 0xefaab4; the pillar frame-table hooks moved
  there); the shell framework shared through em057_01_shell.h. Corrected: no 99-frame orb life (the window is reset to
  100 every frame), the wobble always turns -22.5 deg. Built 965412 bytes, 0 warnings; not installed yet.
  User: "Continue first" (step 8 before the test). Done: B5 step 8, the vt77 orbs (G rank): 4U vt77's seven (motion,
  frame, case) orb events ported as a per-frame table from the slot-125 hook (GU's vt170 renumbered them), event
  0x855fe4 in em057_01_posts.c (notes/b5-shells.md 8g). Built 967464 bytes, 0 warnings; not installed yet.
  B5 step 9 (notes/b5-shells.md 8h): roar blur kept a deviation (user); roar effect fix for all ports (user: "4U rule,
  all joint effects": tools/efl4u2gu.py mef_follows; all ports' arcs rebuilt, only PEL list-1 tails changed).
  Test 7 installed 17:28 (user: "Install test 7"; TEST_HP_PCT=50 TEST_QUEST_RANK=5, 967464 bytes, 0 warnings; cmp OK:
  subsdk1 and the 7 arcs; data files identical to the previous install).
  Test 7 result (log 17-33-09, user: "Visually everything checks out"): no crash; 29 pillars (sites 84538c 845580
  84716c, burst at age 50, end at 60), 12 orbs (5 volleys, all 7/211 (0,0,0,5) step 1; 7 vt77 events k 1 / 3 / 4;
  3 connected, 9 map impacts within ~150 of B). User issues: (1) the pillars come one step after the audio cue; (2)
  the orbs aim like an aimbot. Re-traced (C): (1) 4U init 0xc88090 plays 217 at the spawn, the burst + 218 wait for
  the record's start delay 50 (4U 0xb70024 counts by dt, as GU 0x169260); the charge-walk rows are 50 frames apart,
  so the strike lands on the next step, as in 4U. Request 217 / 218 = bank group 20 entries 17 / 18 =
  em049_se_fx_lbug_bomb1 / bomb2 (S: w6 >> 16 = group, w0 byte 2 = entry; 215 = lbug_fly_lp, 216 = lbug_disappear,
  224 = lbug_start2 fit their uses). The earlier "burst ~1.7 s later" was wrong: 50 frames = 0.83 s. (2) 4U
  0xc89cb8..0xc8a06c: subtype 2 takes the target's position once, at the end of leg A; subtype 4 flies to the
  position taken at the spawn; no steering in flight; the y rule matches (C). m10603 is a 4U HR quest (rank 3):
  there only 7/211 212 ([sp] == 5) home, and the vt77 orbs (rank >= 5) never come; TEST_QUEST_RANK=5 gave the test
  the G-rank orbs. User (after the trace): "it's normal 4U behaviour for the audio/visual missmatch. I got
  confirmation on footage" -> both closed, no change.
- Done (sounds batch, part 1): sz_snd_312484 plays: 4U sndPos 0x312484 = GU 0x4efb98 (C, already used by the shells
  through sz_snd_at), so 7/113 115's sound 220 at frame 0x84e238's point now sounds (4U request id 220 present,
  own bank; logged "snd 312484 .."). Module 967496 bytes, 0 warnings (TEST_HP_PCT=50 TEST_QUEST_RANK=5); not
  installed. Still stubs: 0x390f9c (the unit's sound-event component, ids 1000..1032: needs its GU twin), 0x2fd110,
  0x2fff1c, 0x310104; open: vt77 charged sounds 204 / 208 / 222, aura loop sounds 201 / 202 / 203.
- Next test: drop TEST_QUEST_RANK for m10603 (4U HR, rank 3) unless a G-rank path is under test.
- Done 2026-10-28 (user: "Continue the port ... without my input"; nothing installed or tested in game):
  - Weapons (helper): 37 weapons / 12 Brimstren lines, notes/weapons.md; tools/weapons4u.py first_upgrade + the 4U
    DB second element (table 0xf588f4: Stygian's DBs thunder + dragon); tools/weapon4u2gu.py pick_template falls
    back to a template without a sphere map when the 4U material has no extend map (lan054 / lbg030; every model
    that converted before picks the same template); allocations weapon_models / kireaji / append.weapons.
  - Quests: 8 of 11 built (notes/quests.md 5): m10608 m10612 m10616 m10925 m60205 m00907 m01029 added; core
    allocations standin_alt [0x439, 10778] (module/port.c port_standin, main.c standin_swap / em_arc_request,
    items.c bui_record, build.py), so m10612's real Zinogre stays Zinogre. Deviations: Brute Tigrex -> Tigrex
    (m10608), the 4U frenzy spawn states (m10612 m10616 m01029), m60205's Immenseness Ticket.
  - Volcanic Hollow area data (build_em057_01_arc.py area_files: GU Zinogre's + Brachydios em063_00's map 12); file
    IDs: 40..44 moved after 26 in OWN_ORDER (nothing shipped), shell def 0x108d6 -> 0x108db (em057_01_shell.h).
  - Hunter's Notes: tools/notes_em057_01.py (entry 127 after Zinogre 93, threat 6, emExp[49], no tip), notes_text 1.
  - Sounds: sz_snd_312484 plays (GU 0x4efb98); the aura loop sounds 201 / 202 / 203 + 206 / 208 (4U 0x322d90, two
    timers in the free type-52 fields +0xcad0 / +0xcad4, em057_01_efx.c); vt77's lost sounds (em057_01_vt77.c:
    137 / 138 toggle at joint 4, 204 207 208 222 223 by motion and frame; GU's vt170 kept the timers, flags and
    move class but has no sound call).
  - Correction (C): vt77 reloads its frame register with 138 above motion 0x21a, so the orb events of 0x225 / 0x226
    fire at 138 (were 81 in em057_01_posts.c).
  - Still stubs (no GU site found): 0x390f9c (the unit event component, ids 1000..1032: not sounds but vibration /
    camera kinds 8 / 13, C 0x391134), 0x2fd110, 0x2fff1c, 0x310104. Rest flags: W+0x53a is also written per attack
    per received hit in 0x9244e0 (0x924b18: 1 when the hit has flag 0x100000, else 0) and read by base helpers
    (0x90f720, 0x922e30: category 2 / 4 / 7 branches). 0x937664 (52 callers, the framework's 0x903ff0 / 0x90403c,
    per-em cases 112..122) tests W+0x7e80 bit 32 first, then ends W+0x53a and sets W+0x544 (0x9379f8): bit 32 reads
    as 4U's sleep / rest status, W+0x53a "asleep, not yet hit awake", W+0x544 "woken". So in 4U a Stygian woken
    from his rest picks the roar 1/39 in g16 s0 instead of the lying wait 1/35 (G for the in-play reading). GU
    dropped bit 32 and these bytes and runs its own sleep; porting means mapping GU's sleep end to these flags:
    left unported (no way to test it offline; the user's memory differs from the B7 reading).
  - Armor models (gap found): the armor records named models 169 / 170 / 438 / 439 but no arc was converted.
    Extracted pl_{m,f}_{helm,body,arm,wst,leg}{169,170,438,439} from the 3DS image (tools/ctr.py x, 40 arcs) and
    converted them (tools/armor4u2gu.py; every arc passes `check`); m_arm169's env material needed the same
    sphere-map fallback as the weapons (tools/armor4u2gu.py pick_template; Dalamadur's m/193/helm, f/452/body,
    m/349/arm reconvert byte-identical). build.sh step armor added.
  - Heaven's Mount (helper, notes/heavens-mount.md): 4U m05 as an alias of GU stage 24 (Ruined Pinnacle, folder 30);
    m10607 (10776) m10930 (11427) m11010 (11428) built: all 11 quests now exist. Deviations: Azure Rathalos ->
    Rathalos, 4U small monsters other than Ioprey dropped, unported -f01 filters and effect schedulers, G route
    data. Core limit left: 4 map records per alias (port.h map_k[4], stage_alias.c s_maprec[4]); areas 4..8 use
    resampled GU records until it is raised to 9+.
  - Module 968532 bytes (TEST_HP_PCT=50), 0 warnings.
- Next: shells (B5) and the stubs; the rest state; the orb posts and other B4 items; weapons (notes/weapons.md: 12 Brimstren lines, 37 weapons, standalone;
  a helper, Dalamadur's gear_weapons_em090.py as model); quests (notes/quests.md: the core quest-list append and
  PORT_QUESTS first, then the builder, m10603 first); Notes (quests[0]); first test.
- User 2026-10-28: the draft quest placement is approved (Hub HR6 -> GU Hub HR7, caravan -> Village ★10, Hub G2 /
  G3 and the event -> GU G4; the arena quest was dropped later the same day); icon preview approved and done
  (icon_4u fixed to 50).
- User 2026-10-28 (second round): weapons = standalone forging (no GU weapon record patched; notes/weapons.md 3);
  quest slots = append new quest_group entries in the core (notes/quests.md 3); stat rows = 4U Stygian / Zinogre
  ratio applied to GU's Zinogre rows at the placement, never below them (notes/quests.md 3b). The arena quest m21003
  (4U "Grudge Match", preset gear, time ranks) is dropped ("it's no use"): 11 quests.
- Open questions to the user: early looks test (not answered; default: none, the first test comes with the quests),
  the helper rule slips.

## Steps
1. **Phase 1, static study** (no game files touched):
   - phase1-variant-map.md: every 4U Stygian site (the 71 and the under-counted ones) mapped to GU uEm057_00:
     MATCHED / DIFFERENT / MISSING; GU's variant tests (does a Thunderlord `!= 0` test catch variant 1?);
     Stygian-only actions and motions; shell and effect posts.
   - phase1-assets.md: GU's em057 motion banks vs 4U's (Stygian motions present?), EMC (4U em048_cmd vs GU's
     table, every op the Stygian paths use), em049 data (emd / etd: stats, hitzones, dragon attacks), effects,
     sounds, shells, quest stat rows.
2. **Register and build the arc:** allocations.toml entry, monsters/stygian_zinogre/package.toml (gu_class
   uEm057_00), arc em057_01 from 4U em049 with the existing converters; other monsters byte-identical.
3. **Behaviour:** hooks gated on variant 1 for every DIFFERENT / MISSING site, shells, effects; owner-only parts
   gated on enemy+0x7420 (multiplayer).
4. **install.sh:** the monster and every new switch.
5. **First test** (user's go): swap switch on a GU Zinogre quest; read the log; ask only about visuals.
6. **Content:** save slot, materials, carves / breaks / rewards per rank, Hunter's Notes, names (5 languages), icon,
   size records, quests (rank rule above), armor (every piece, BM / G, M / F, every 4U rank), weapons (every class
   and path, models, sounds), skills and decorations.
7. **Heaven's Mount:** stage alias of a GU field (areas, collision, gathering, map UI, lighting rule), then its
   three quests.
8. **Release** on the user's OK.
