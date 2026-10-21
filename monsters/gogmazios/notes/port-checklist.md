# em089 action port checklist (resume file), 2026-10-17

Status: [x] faithful, [~] simplified (what), [ ] not started (still fallback / old port), [-] not portable (why).
Handler = real 4U handler from the dispatchers (cat 0 0x8b6f2c, 1 0x8bac40, 2 0x8bd4b0, 4 0x8c2640, 7 0x8c0f94,
3/11/13 inline in slot 44 0x8c3ac0), r1 variant in brackets. Everywhere skipped: frame events 0x8b8e28.
Code: module/em089_act.c (one function per 4U handler). Tools (scratchpad, not in repo): p4u.py / h4u.py listings.
"scratchpad" below = the last Gogmazios session's scratchpad, archived locally in dump/scratch/gogmazios-session/
(2026-10-21; older sessions' scratch files are gone).

## Fidelity plan (main agent, 2026-10-18) — the goal and who owns what
Goal (user): a FUNCTIONAL build faithful to 4U Gogmazios in looks, arena, behaviour, music and sound effects, ported
as far as possible without the user; then one test. Every value comes from 4U code/data, never from memory; each
deviation is written in the owner's section. Workstreams and EXCLUSIVE file ownership (others: report call sites to
the main agent, who wires them):
- behaviour agent: module/em089_act.c, module/em089.c, em089.h. Remaining action/slot stubs, slots 46/48, cat 11,
  7/32 break interruption, 7/47 wall probe, 0x8c34a0, camera shake/quake, tar refill/chest event, phase-2 path.
- effects agent: tools/efl*.py / mef tools (new), module/em089_efx.c/.h (new, incl. the 4U slot-75 per-motion event
  port as em089_slot75 for the main agent to register), effect files.
- sound agent: tools/snd*.py (new), module/em089_snd.c/.h (new, if code is needed), SE banks/requests/calls, BGM.
- arena agent: module/stage.c, tools/stage4u2gu.py, sbc.py, sis.py, tools/build_gog_quest.py, m28 romfs, notes/stage.md;
  Battlequarters look + gimmicks (cannons, ballistae, Dragonator / pile bunker), stage BGM/SE hookup.
- review agent: DONE (fixed stale effect handles on retry: em089_efx_forget). Main agent: em_arc_request now skips
  our arc in Kushala quests when another quest ID is known. Raw-pointer effect polling -> effects agent; cart state
  reset per quest -> arena-4.
- arena-3: cart loop ported (stage_cart.c); spear sever needs no change (kind 126 = any damage); pile bunker [-]
  (unreachable in 4U m19 - being re-checked). arena-4: doors + sinking wall (HP <= 40 % AND > 10 min elapsed;
  TEST_DOORS_SEC shortens it) and floor cannons (GU cannonball as the shot) PORTED. Re-check running: the Demolisher
  (pile bunker) is announced by 4U when the wall sinks, then the cannon shot as uShell023.
- Final test build (when all done): GOG_DEFINES="GOG_STAGE_ALIAS TEST_HP_PCT=45 TEST_RAGE=60 TEST_DOORS_SEC=120".
- shell agent: uShell016 attack shells (em089_shell016.c, 9 sites wired by the behaviour agent) + uShell051 ground
  shells (em089_shell051.c, blob splash wired in em089_shell.c by the main agent; em089_snd_splash queue now
  unused) DONE. Unverified: slot-0 scale field this+0x13bc (log "scale 0" = wrong), moving beam sound (ported 2026-10-19).
- arena / arena-2: DONE (--bq validated, 4U props/lighting/area SE/music packed, ballistae, Dragonator 2 spears +
  siege-phase hook + questPlus_1491, generated relation tables, static doors/wall/cannons). arena-3 RUNNING: spear
  sever kind (may edit em089_break.c), pile bunker, cart loop, door/wall/gate behaviour, camp camera - with own code.
- effects agent: round 1 DONE (31 EFL + EAN/TEX/effect models, PEL u + 4 PSL from MEF/LMT events = motion effects
  play from data; slot 75 -> GU 168, registered, off until W+0x434 is mapped). Round 2 running: blob attach
  effects (may edit em089_shell.c), code-posted effects (stub lines in em089_act.c), W+0x434, m19a03 break EFLs.
- behaviour agent: 2 rounds DONE (phase 2 = first rage at HP <= 50 %, slots 127/130, camera shakes + em089 LCM,
  7/32, 7/47, wing/lights, tar chest sound). Left: uShell016 attack shells -> shell agent (new em089_shell016.c),
  then the behaviour agent wires its call sites; cat 11 / slot 36 stage-61 / slot-47 cat-10 = not portable (see its
  section).
- sound agent: SE + battle BGM (2 phases) + arena area streams DONE (static). Main agent wired em089_snd_tail_break
  (em089_break.c), em089_snd_shell_spawn / _land (em089_shell.c), em089_snd_tick (em089.c slot 132); tar chest
  sound wired by the behaviour agent. Round 2 DONE: camp jingle m28cmpd + area SE converted (arena-2 packs them),
  splash sound 220. Eiyu theme [-]: no 4U poster of a kind-9 uShell020 found.
- shell-data agent: DONE (em089_00_shell00 = file 0x1071d, 4U powers 5/40, radius 80). Open (main agent): 4U
  passes 23 / 16 as attack-slot field +8, our em089_shell.c arm() passes GU uShellEnemy's 31 (GU convention kept).
- tar-look agent: DONE incl. follow-up (alpha-tested tar + wing, w7 bias, 4U alpha bytes, all materials audited);
  em089_wing_update / em089_light_play handed to the behaviour agent to wire. Left: wing extend map 05_BM unused.
  Original plan below.
- tar-look agent (was queued; needs the ARC LOCK): the 4U tar flow uses the diffuse alpha (w)
  term GU's shader ignores, so the animation runs but barely shows. Plan: (1) list the MRL animation tracks GU's
  monster shaders DO render visibly (UV scroll / transform on albedo, normal, emissive, colour factors — taken from
  GU materials with moving surfaces, e.g. lava/slime monsters), (2) re-target each 4U tar track to the nearest
  visible GU parameter with the 4U speeds/periods, (3) if still flat, bake the w-modulated look into the albedo
  and scroll it (and/or a second scrolling layer). Done = flow/shimmer visible at fight distance, same speed and
  areas as 4U (4U frame captures as reference); deviations written down. It owns tools/mrl_build.py, mrl_anim.py,
  mrl_check.py, the material parts of mod4u2gu.py and module/em089_tar.c.
- Test 3 prep (main agent, 2026-10-19): music fixed by the sound agent (own STQR in the em089 arc + hook 0xB6D72C);
  stage materials fixed (see "Tar look" STAGE materials). ICON CAUSE (C, files): GU loads HD_cmn_micon00/01 from
  nativeNX/eng/arc/resident_eng.arc, so our loose module/romfs .../99_texture/HD_cmn_micon01 is never read. The
  user's "HD UI v4" mod ships its own resident_eng.arc (micon01 = 1024x1024 BC3, 144-px cells; cells 141, 143-145 =
  Alatreon / Fatalis, 146.. empty; its header has a stray bit 24 in HD_load00's size field, arcpack.read asserts on
  it). DONE with the user's OK: tools/ui_icon_hdui.py patches cell 146 of that arc's micon01 (backup
  resident_eng.arc.pre-gogmazios next to it; `ui_icon_hdui.py restore` undoes it). Art = 4U's '?' (4U has no
  Gogmazios icon, user-confirmed; its quests use icon 0), not the old by-eye cell (0, 8). MAP UI (not done): 4U area maps = small sprite atlases (256x128 ETC1A4: map ~100 px + area numbers, digits,
  arrows) placed by 4U lyt 0x15302ef4 ui299aNN; GU = one baked 256x256 BC3 image per area (HD_m26a0Ndn) + GUI
  layout m26a0Ndn + fort_icn; marker world->map transform source not traced -> next job (arena-4 resume point).
- Test 3 (2026-10-19, log 12-00-00) main-agent items. Board icon: GU 0x3a3178 maps quest bytes 142..186 through a
  hyper remap table (+ badge 0x613318), so byte 147 showed Hyper Khezu; the user's HD UI cheat makes bytes > 186 =
  UI index + 46 without badge -> build_gog_quest.py --icon default 192 (quest rebuilt). Map icon: our reg_mapicon
  already gives size class 18 (Kushala / Teostra / Fatalis); the user says the map icon is wrong -> ask what 4U shows
  (4U table not found by value search). BLACK TRIANGLES still there (camp a00), cause NOT found. Ruled out (C, data):
  strip joins (4U: 5616 paired degenerate joins + 18 single parity repeats, standard on any GPU), mesh lod / visible /
  shape / sort fields (same as GU), vertex alpha (GU's own lit #20/#32 and unlit #3-5 blend meshes carry vertex
  alpha 0..255, so the templates use it). Candidates left: 4U per-mesh 'alpha' field 11 / 12 (meshes 74-78, 97:
  bcloud / sky cards, GU never uses > 4), mesh 23 (enkei01 distant-view billboard, 4 verts, 7838 x 14827, AT), lit
  vertex-colour convention (GU lit blend meshes rgb ~50, 4U 109..127).
  LIKELY FIXED (main agent, afternoon): the biggest triangles of a00 are meshes 96 (mori03, distant forest, areas
  1.4e10) and 49 (sky03 dome), both converted with a LIT template: stage4u2gu decided lit by tLutShininess, which
  every opaque 4U material has. 4U's lit flag is w6 bit 31 (clear on exactly 14 m19 materials: sky / sora / cloud /
  mori03 / effect cards; GU's own sky 'sora' = FConstantColor). Now lit = w6 bit 31: a00 sky03 / mori03 / cloud /
  sky01 -> unlit templates; side effect: 17 a01 / a02 materials without tLutShininess (arena ground, walls, cliffs,
  props) go unlit -> LIT (their vertex colours match GU's lit Fortress meshes: rgb mean 67 / p10 36 / p90 110 vs 66 /
  33 / 109). Ruled out too: mesh 'alpha' 11 / 12 (GU uses up to 203, 11 on its own XfBAW_10 cards = sort priority),
  binflip / bridge bits (0 in all three), 0xFFFF / out-of-range indices (none), enkei01 alpha (27 % transparent,
  BC3). Visual check for the user: camp sky / distant forest, arena lighting (ground / walls now lit).
Shared files: game.h and module/build.py = append/one-line edits only, re-read right before each Edit.
tools/build_em089_arc.py + module/romfs em089 arc = ONE agent at a time: write `ARC LOCK: <agent> <time>` on the
next line before editing/rebuilding, and `ARC LOCK: free` after; wait (do other work) while it is held. After a
rebuild, em089_files.inc may only GAIN entries (existing IDs identical; diff in your report).
ARC LOCK: free

## Content plan (2026-10-20): notes/content-plan.md
Save data, rewards / materials, armor and weapons, skills, monster tables, quests.
- [~] Built 2026-10-20 (161584 B, not tested in game): materials in DUMMY items 2977-2985 (module/items.c, load
  hooks 0x19237c / 0xb83c48), 4U carves (tools/hagi_em089.py, arc fields 46-50; ARC LOCK taken + released, only the
  5 hagi entries changed, em089_files.inc identical), 4U quest rewards (rem_891014 / rem_892014), 4U break rewards
  (hook 0x3a3874), save slot dummy1 (main.c stats_add remap 0x59 -> 0x1064). Crowns: not needed (fixed size, as 4U).
  + quest 11492 = 4U m11035 "Advanced: Act of Gog" (board slot 1011003, stage.c gog_quest_index(), spawn_b3() = 1)
  and 4U subquests on both quests (back = code 5, tail sever = code 7). Module 161748 B.
  TEST 2026-10-20 09:46 (user): both quests on the G4 board (10/11 Act of Gog, 11/11 Quagmire Quarrel) with 4U
  text, fees, sub rewards and subquests; items received and saved (quest finished with a cheat, no kill, so no
  quest-end tally line). Log: 9 items + 9 names set (eng), both quest_group renames, quest 2 spawn byte3 1 (GU 0),
  break-reward lookup x3 for id 0x59. Not checked yet: save slot 105 tally (needs a kill), subquest completion.
  TEST 2026-10-20 10:01 (5 % HP, log 10-01-22): Act of Gog tail-sever subquest completed (user). Quagmire Quarrel:
  (1) the kill did not end the quest, Gogmazios looped a flying motion: category 11 (death) fell to act_react
  (motion 0x10f + action end -> the death restarted). Fix: em089_react.c plays 4U's death motion 781 through GU's
  reaction player, whose end op sends a dead monster to 12/255 (0xa18ac / 0xa1b28). (2) the CHEST break (part 7)
  completed "Wound back": parts 1 / 7 were misnamed; Kiranico's stagger order = 0 head, 1 back, 7 chest -> subquest
  code 3, break conds Breast 60 / Back 40. The quest-end tally reached save slot 0x1064 (kill counted).
  Retest installed (161964 B): kill -> quest end + carving; back break -> subquest.
  TEST 10:13 (log 10-13-41): the death motion played but no quest end, and the back could not be hit. Cause: a GU
  death table ends with op 7 before 0xff (Kushala 11/0 {motion, op 7, 0xff}, 11/1 fall / land / op 7); ours had
  no op 7, so 12/255 never came. Fix (170616 B, with the armor + Arcana hooks of gear.c): 11/0 = motion 781 + op 7,
  11/1 = Kushala's flying-death shape with 4U 0x8b6b80's motions (0x315 launch, fall, landing 0x317). The back
  (part 1) has all-zero hitzones in 4U's data: normal hits cannot break it, the Dragonator is the likely way (G).
  Test: finish quest 11491 (carve body + tail), check the reward screen rows A / B / break row, the item names and
  icons in the item box, and the log lines `item data`, `item text`, `break rewards`, `quest-end tally`.
  TEST 10:24 (log 10-24-03): death 11/0 played, tally reached save slot 0x1064, still no quest end. Cause (C): the
  stats_add hook swapped the ID at 0x3a75c8's entry, and the objective loop of the same function compares that ID
  with the objective target (obj+0xf0 at 0x3a7960) -> 0x1064 != 0x59, hunt never marked done. Fix: hook moved to
  0x3a75fc (after `bl 0x50b64`), remaps only the index 137 -> 105. (The 12/255 handoff runs through 0x76908 /
  0x76a10, not the logged 0x76154, after a 4-step rec+0x550 machine at the table end.) Back (part 1) broke at the
  first flinch -> "Wound back" done; the spear detached at the second (1200 damage), no falling object (stub).
  Armor: all 5 Blademaster/Gunner pieces listed except the helm: its recipe's first material (flag 2 = unlock) is
  Gogmazios Gasher, not obtained yet (GU rule). Look = Akantor X stand-in model (models still to port).
  Weapons appended (196504 B, gear_weapons_em089.inc + 45 hooks); not tested.
  TEST 10:39 (log 10-39-53, user): QUEST COMPLETE after the kill (tally "index 105"); Gogma Helm listed once the
  Gasher was owned; Gogma weapons listed in the smithy with stand-in looks (Agnaktor, Rajang for Hammer / Lance /
  IG / LBG). Log: kireaji 164 -> 167, all 14 Base / Level / Msg / Create / Process appends, 14 name blocks. Left:
  4U armor + weapon models.
  Armor models (tools/armor4u2gu.py, helper report): player bones 0-19 identical in both games, 20+ = cloth bones
  driven by the CTC; MOD via mod4u2gu unchanged, BM -> BC3 + BM+A (BC4), MRL from Capcom's own 4U -> GU pairs,
  CTC chains +8 B. 20 arcs (pl_{m,f}_<part>{352,353} from the 3DS image, tools/ctr.py x) -> module/romfs/nativeNX/
  arc/player/com/{m,f}/{352,353}/<part>.arc; series 1287 / 1288 model = 352 / 353 (4U numbers, unused in GU).
  Known gaps: no edge/shadow meshes, helm XFS (hair flags) copied from GU 354, nearest-match material constants.
  TEST 11:00 (log 11-00-21, user): Gogma Blademaster and Gunner armor render correctly in the smithy. Next: the 14
  weapon models (same pipeline, tools/weapon4u2gu.py).
  Weapon models (helper report, C unless noted): GU kept 4U weapon model numbers, all 14 Gogma ones are free; one
  model per class (create + upgrade share it); Capcom added only BM+A textures to converted 4U weapon arcs. mModelID
  = 4U record model (GS 97, SnS 97, Ham 99, Lance 82, HBG 40, LBG 47, LS 79, SA 77, GL 82, Bow 75, DB 87, HH 71,
  IG 25, CB 27) -> module/romfs/nativeNX/arc/weapon/wNN/<model>.arc. pwl (motion set mGmkMotNo, mem +4) = 4U's
  gimmick byte except HBG 40 (1 -> 0) and SA 77 (8 -> 20, no g08.arc): gear.c gear_pwl @0x272910. Sounds = GU
  stand-in sets (mSrqrNo). Gaps: LS / DB glow meshes lose 4U vertex colour (0x6D grey, brighter glow), 10 materials
  from a "relaxed" match (other weapons' glow colours). 197156 B, not tested.
  TEST 13:02 (log 13-02-42, user): all 14 Gogma weapons show up correctly in the smithy. Log: gear pl_w04 model 40
  motion set 0, pl_w08 model 77 motion set 20 (both fixes applied). Uninstalled.
  Built 2026-10-20 afternoon, NOT tested in game (216892 B test build, 215420 B release, 0 warnings):
  - Descriptions (C): 4U's own armor / weapon texts. Index = u16 table per part / class in the 4U exe (armor head
    0xef1308, body 0xeef4f8, arm 0xeefc90, waist 0xef0408, leg 0xef0b80; weapons 0xef1ae2.. per class,
    gear_weapons_em089.EXP_4U), found by vote over the gear GU took from 4U (532/564 head pairs). 4U v1.1 text =
    base text (the update's core_common msg files are identical, 5 languages).
  - Arcane jewels (C data, port-choice recipes): 4U decoration table 0xf578dc (8 B: item, size, tree, pts, tree,
    pts; record = item record +10 minus 1): Arcane 1/2/3/True 3 = size 1/2/3/3, Arcana +2/+4/+5/+6. They are
    reward-only in 4U (absent from the 229-record recipe table 0xf553e0; weighted lists 0xf61198..). GU crafts
    every decoration, so recipes in GU's G pattern (tools/gear_em089.py DECO_RECIPES). Items 2889-2892 (DUMMY
    decorations, items.c checks icon 44 / sell 40); decoData +4 (record k = item 2638 + k; getter 0x194230 allows
    <= 2899, bound = loaded count), decoCreate +4 (smithy bits 288 > 279). Hooks gear_deco 0x191a20,
    gear_deco_create 0x4c0cb0 (gu_class).
  - Quest clear mark (test 2026-10-20 17:34: 11491 not marked cleared, so no Notes entry). Cause (helper, C):
    save maps [0x1897f78]+0x42c cleared / +0x52c seen / +0x62c failed, 2048 bits each, indexed by quest-list
    position (unknown ID -> index 0). The clear is written by 0x388d40 in the results scene, which loads its own
    fresh quest list (0x6a1f64 -> 0x3b190c) without our rename -> bit 0. Fix (built): hook quest_clear_fix @0x388d40
    runs the rename first (bit 1412 / 1407). The user must clear 11491 once more; earlier clears set bit 0 (entry
    ID 0, harmless, left as is). Expected log at the results: `quest_group entry 1412: 1011009 -> 11491`.
  - Hunter's Notes (C): entry 123 = Gogmazios (module/notes.c, tools/notes_em089.py): list 0x162d9f0 via data word
    0x183ec4c (module_init redirect), unlock 0x162d1f8 + order 0x1631ef4 via literals, 7 loop bounds 123 -> 124
    (build.py WORD_PATCHES; two unrolled loops read a padding record). Name = monsterName 105, icon by em ID,
    Elder Dragon, threat 8 (G: 4U's table not found, three searches), texts 220 / 221 = 4U emExp[89] + tip
    "Tar" HunterNote[179] / [435]; unlock = quest 11491 cleared (kind 2), via the usual talk action 6. Hunted count:
    hook save_hunts 0x523104 remaps 0x59 -> 0x1064 (save slot 105). Size records off (+14 = 0: 0x526f48 is unbounded).
  - One-shot Binder shiny drop (C): 4U drop 0x911f58 table = [0x1002a5c + 4 * (base + 4 * set + rank)], set
    0x930bdc = em 89: work+0xed == 1. Set 0 G = One-shot Binder 100 %, set 1 G = Oil / Treasure / Dragonsphire. Tail
    break clears +0xed then drops (0x8c67f8), the rare-drip splash sets it then drops (0xc908b0). GU: enemy vt slot
    149 (0xac0ec) picks hagi byte 14 + set -> em089 slot 149 = em089_drop_set (F_SHELL_ED), hagi s4 shiny sets 1/2
    = binder / shiny. Arc rebuilt (--cmdtbl gog, 5 s; the ARC LOCK line was not rewritten, no other arc user):
    only hagi_s4 changed, em089_files.inc + manifest identical.
  - Flying-mode death (C): 4U 11/0 with W+0x1c9 == 1 -> 0x8b6da4 = motion 781 + layer-1 motion 805, weight 1 -> 0
    over frames 30..70 (time scale * frac * 0.025); em089_react.c death_layer on top of the ground death table.
  - Base HP stays 17500 (C): the v1.1 update ships no monster data, so EUR etd = 17500 (Kiranico's 18000 is
    another version's data).
  - Falling Dragonator spear = a one-shot PILE BUNKER (2026-10-20, built, NOT tested). 4U (C, two helper traces;
    scratchpad spear/spec.md): part-1 sever -> cut object 1 (emd word 36 record: type 3, 160 fall frames, gravity
    -0.45, rest 20*scale, reward flag 8 = a no-op in 0x6a8920; only em089 uses type 3 in 4U) falls from joint 200
    to the ground under the monster, lands (SE 211, dust em089_024 mask 1), and one frame later em089's own
    0x926044 registers an interaction record of KIND 36 (radius 100*scale, height 300). A switch press there (player
    action 172 = switch action type 7) -> 0x6a1f18: stage +0xdd29 |= 2 (one shot) + uShell022 kind 10 owned by
    the hunter. The hidden m19 uStageGimmick type 2 sub 3 runs the timeline (85 f wait, 60 f spin-up SE 218, SE 219
    + 8 f thrust to 180, 180 f hold at 150, then 5 -> 6); the spear copies its matrix into joint 2, wobbles joint 0
    (+-0.75 / +-1.5 deg, periods 15 / 20 f), sparks (SE 213 / 21 f), effects masks 2 / 16, explodes (SE 214, mask
    4), collapses 296 f (mask 8 + SE 212 at 127) and sinks 292 f, then is hidden for good (no timeout before use).
    The shell hits 4 times, 8 f apart, after 158 f (arena Dragonator record, sphere 500 at the pile tip).
    GU port: manifest field 2 = em089_gekiryusou (GU cut slot 1, type 2); module/em089_pile.c (GU side) +
    em089_pile_port.c (helper's faithful C port of 0xc2e478 / 0xc2d364 em89 parts / 0xc2e96c / 0x33c7c8):
    spawnCutPart(this, 1, 0, 200, 0) with reward flag 6 pre-set (no reward, as 4U), slot-10 takeover through a
    copied vtable (GU's port of the class has no em89 branches), kind-11 record routed by stage_cannon.c (works with
    or without the alias), uShellEm089Pile (HDS 25 / HTS 15 = 4U record + volume, armed with 4U's (2, 8) = GU's
    player side) on every machine for every press (online: only the controller's copy deals damage, see
    Multiplayer 7), PEL 6200 + k (em089_024), em089 SE 210-214 / 218 / 219.
    Expected log: `em089 pile: spear launched`, `pile: landed`, `interaction record`, `ACTIVATED`, `pile hit 1/4`..
    `4/4`, `pile: explode`, `pile: hidden`. Risks to watch: hits register (side 8 on a monster-owned shell); joint-1
    rest pose (4U leaves Rx(-390) on joint 1 AND on the object: -60 deg net; PILE_LANDING_J1_IDENTITY=1 if it looks
    doubled); mesh groups 1-4 via GU +0x110; model scale (0xbe5d4). Deviations: kind-11 prompt / GU switch motion,
    joint-attached effects posted at the joint (not attached), remote-copy smoothing and moving floors not ported.
    - [x] Test 2026-10-20 17:34 (30 % HP, solo; user: "lays flat on the ground, wrong size, can't activate it").
      Log: launched, "landed" on frame 1 at (499, 89) while the record sat at the target (-1094, -256); every ground
      ray missed and the ground follow raised y by 50 per frame (y 348150 later); activated anyway after the kill (4
      hits at a stale joint-2 point); the sequence ran 2x fast (165 4U frames in 2.7 s). Causes + fixes (built):
      (1) GU's slot 10 ends by rebuilding the drawn matrices (0x94e224 world = slot 19, 0x94e250 joints = slot 20,
      slot 24) - our replacement skipped them, so the spear kept its spawn matrix (flat, unscaled) and joint world
      positions were stale (instant landing): now called after every port frame and at the sever. (2) pj_ground_y:
      lower point first (as em089_shell.c), then reversed; a miss answers the last ground (first: rec+0x5b4 under
      the monster = 4U's target), never a miss. (3) the GU record now follows the spear (4U c2e3d4). (4) dt: the cut
      object's and the hit shell's unit field +28 advanced 1.0 per 60 Hz tick -> both now step by the quest
      countdown (clock_dt: real time, 0 for a second call in a frame).
    - [ ] FOUND, not fixed (needs the user's go): every em089 shell runs 2x fast under the user's 60/120 FPS patch.
      Blob kind 0 (v0 0, gravity -0.2/f^2) from y 534 hits the ground after 1.2 s (4U: 73 frames = 2.4 s); same
      ratio for the next three blobs. Their unit field +28 is 1.0 per 60 Hz tick (the monster's is 0.5). Fix
      option: em089 shells step by clock_dt as the pile does (attack windows inside GU's attack code would still
      run on GU's own step).
  - Looks (helper report, arcs pass `check`, not seen in game):
    - Armor edge meshes (C, 2936 armor MOD pairs): one extra mesh per mesh with a hard edge (9260/9296 meshes
      agree): zero-area quads along hard edges + corner fills, vertex format 0x0CB68015 (20 B), drawMode = normal
      & 0x1020, numbered right after their mesh. tools/mod4u2gu.py convert(edges=True) (off = byte-identical, em089
      included), armor4u2gu.py default on (--no-edges). All 20 armor arcs rebuilt; m/352/body meshes re-sorted by
      material as GU does. G: corner fills with 4+ normals (fan), ~1 % of quads differ from Capcom's.
    - Helm XFS (hair): format decoded (32 x {u16 mDispFlag0, u16 mDispFlag1}, one per hairstyle; bit g = hair group
      g shown, S) but no rule found (296 different Capcom tables over 683 helms; nothing in the 4U head record,
      exe or arcs predicts them). Placeholder from GU 354 kept (male hides all hair).
    - Weapon glow colour (C, 17/17 pairs): 4U 0x7BA7401B -> GU 0xCBF6C01A (24 B, RGBA kept, drawMode 0xECD3 ->
      0xECF3); only LS ken079 and DB sou_l/r087 have it: w07/079 and w11/087 rebuilt (grey 0x6D restored). If the
      glow vanishes in game: mod4u2gu COLOUR_DM = {} reverts the drawMode.
  - Weapon edge meshes + drawMode (helper 2, C on 598 weapon MOD pairs, the armor rule holds unchanged: 2229/2257
    meshes, record fields 1259/1259): weapon4u2gu convert() now uses edges=True; glow (vertex-colour) meshes get
    none (Capcom 131/132). drawMode by vote: material = exactly BSAddAlpha + DSZTest + RSMesh -> 0xECF3 (153/153),
    other visible -> 0xEFFF; 0xEEFB (27 meshes) has no rule. Changes one Gogma mesh: CB blade027's glow. 14 model
    arcs rebuilt (66 edge meshes in 20 parts), normal meshes byte-unchanged. Backups scratchpad/wsnd/before.
  - Weapon sounds (helper 2): tools/wsnd4u2gu.py -> module/romfs/nativeNX/arc/weapon/wNN/snd/<model>.arc (14 new).
    GU weapon banks / requests are per-class templates; from 4U only the waves (lossless), each bank key's wave
    and the request IDs that exist; volumes and the rest from the GU class majority (Capcom's own vote; Lance w2
    from 4U, 9-0). Trailer gain per class, category bits dropped, HBG/LBG bank ID 3 dropped, horn echo IDs 115,
    165-167, 215-219 filled from the class entry, GU-only `_90` wave copied. selftest on 578 Capcom pairs: kept
    waves 857/857 identical, banks 590/647, bank entries 5146/5310. mSrqrNo = mModelID in gear_weapons_em089.py
    (path `weapon\w%02d\snd\%03d` in the GU main). Ear checks: SnS IDs 1-3, horn 15-17, CB 3-5 now at GU class
    volume (4U was 0.5-1.5 dB louder). mSndMaterial stays 1 (iron hit set; GU-only, 4U hit sounds are class-wide,
    the stand-ins used 0 for GS / SnS / Ham / Lance / GL / Bow / DB / HH / IG / CB): port choice.
    Needs scratchpad/weapons/4u/data (extracted 4U pl_*.arc) to re-run `gogma` / `selftest`.

## Multiplayer (priority 1 since 2026-10-20; the user has nobody to test with)
How GU runs a monster online (C, static):
- Only the machine that controls the monster (this+0x7420) runs the AI think (0x82538).
- setAction 0x76154 with mode 0 / 5 returns at once on the other machines.
- On the controller it queues the message: this+0x73eb / 0x73ec / 0x73ee serial, then 0xcafe8 -> vt+0x42c = pack slot 267 0xcb330.
- The message carries the action, the serial, target slots 0 / 1 (rec+0x1d0, kind / sub / param / flags rec+0x230..0x23c) and 20 monster bytes (slot 171, buffer + 132).
- setActionNext 0x76984 on a non-controller only marks a replay (this+0x73e5 / 0x73e6 / 0x73e7); 0xa5c40 then waits (0x75510 -> 0xc0644) for the controller's message.
- Unpack is slot 268 0xcc154 -> slot 172.
- Handlers (slot 125) run on every machine. So motions, shells, effects and sounds are local, and the action serial (tar-blob rand seed) is the controller's.
- Our chain() uses setActionNext, so it already follows this.

Findings (2026-10-20):
- [~] 1. Target = the local hunter on every machine (sync_target / target_pos / em089_aim.c / tar shots).
  - On the host it always hunted the host; on guests it aimed at the guest (positions diverge, shots land elsewhere).
  - Fix in code: em089_target_hunter(). Slot 0 kind 1 -> hunter index (resolver 0xc4ba8 case 1: param 0..3, sub 10 = bit mask), looked up in the hunter list *(main+0x1885b58) + 0x1c + 4 i with the resolver's DTI test (0x1898670).
  - Kept in F_TGT (+0x91), net-synced; the host's own hunter before the first kind-1 target; local hunter fallback.
  - Solo should be unchanged. Check: log lines `hunters ...` and `slot0 k/s/p tgt N local N ctl N`.
- [x] 2. 4U owner-only branches (W+0x1d9): all four in the em089 range are ALREADY ported with EN_CONTROLLED: 7/32 [0x8bc950], 7/45 [0x8bcbec, 0x8bccdc], 7/47 turn chain [0x8bd2fc]. (The fifth read, 0x8cabb0, is a helper called only from 0x8ce684.., outside em089's handlers.)
- [~] 3. Net byte: 4U slots 78 / 79 [0x8c9d50 / 0x8c9d38] send work+0xda only (base bytes dropped).
  - GU slots 171 / 172 are now overridden: em089_net_get / em089_net_set, byte 0 F_HEADING.
  - Port-only bytes 1 F_NOSYNC (the arena point is set by the host-only AI hook set_target_c) and 2 F_TGT.
- [~] 4. Battlequarters gimmicks (static, 2026-10-20). Player gimmick actions are replayed for every player on
  every machine: the switch actions 0x2d9504 / 0x120f7f8 call the Dragonator fire 0x503bb0 for any player, then
  0x503a5c only when 0x27bcd0(player) == 1 (local). The cart levers likewise (0x2d9578 / 0x11ff930 / 0x120f86c ->
  0x504254 -> 0x497040). GU's 0x497040 handles a request only on one machine when online (index compare
  0x227ae4) and broadcasts the new state as message 106 (0x227b3c(net, 106) -> 0x21ba6c).
  - Cart: our hook runs before that check on every machine that replays the lever press, so each machine starts
    the same 4U leg from its own station. Consistent while every press is replayed; no host authority (deviation).
    MP test: compare the `stage cart` lines.
  - Doors: every machine evaluates the 4U trigger (synced boss HP, elapsed time). The quest-start command is
    host-only and blocked by stage_kobj_bcast. OK.
  - [x] Cannons: BUG fixed. The fire hook picked the cannon from the LOCAL hunter's position. Another player's
    cannon press then fell through to GU's Dragonator fire on every machine whose hunter stood elsewhere. Now
    the pressing player (r4 of the switch action) decides. The second switch action (lr 0x120f808, class from
    0x1207e6c, presumably the Prowler) is accepted too: before, a Prowler's cannon press fired the Dragonator
    even solo. skip_post only for a local press.
  - Dragonator: GU's own code (the fire runs on every machine from the replayed switch action).
- [x] 7. Damage authority (helper trace 2026-10-20, C; scratchpad mp/spec.md). GU never sends damage over the
  network. Every machine tests every attack (local swings, replayed remote swings, shells) against its own monster
  copy and fills the part accumulators rec+0x488+2p (0x9d6f8), but only the controller applies them: 0x97ddc
  returns at once when enemy+0x7420 == 0; on the controller it subtracts HP (0x98bb8), counts flinch / break
  (+0x3bc) / sever (+0x3bd), picks the reaction. Leftovers elsewhere are cleared each frame (0xade78 / 0x9d67c).
  HP and the part block (first 2 severable parts; em089 has exactly 2: spear 1, tail 6) travel in message 60
  (action, 0xcb330 / 0xcc154, unpacked by slot 266 0xcb22c BEFORE setAction) and 61 (full state). Detached bits
  rec+0x3b4 are in no message: spawnCutPart sets them locally (Kushala's (10, 114) handler does it on every machine).
  Consequences, applied: em089_pile.c spawns the hit shell on EVERY machine for every press (was: presser only ->
  no damage when a non-controller pressed); a remote press matches the spear within 1500 (height +-500) and is
  queued until that machine's spear lands; stage_cannon.c matches a remote cannon press within 300 and fires it
  whenever no shell is in flight (the controller's shell is the one that counts; each machine posts one shell per
  press, as GU's st008). Cut objects keep polling the synced sever count on every machine (em089_break_update).
  Builds 236624 / 235168 B, 0 warnings. MP test: press a cannon and the spear from the NON-host machine and
  compare Gogmazios' HP on both screens (one hit each, not two, not zero).
- [x] 6. FPS patches (user, 2026-10-20: vanilla online works with mixed 30 / 120 FPS, the mod must too).
  - The user's cheats write the target fps float at [[main+0x18A6210]+0x243C] (60 / 120).
  - The engine scales each unit's step by its delta this+28 (timer step 0x53aa84, turn step 0xc0e78, scheduler 0x966164).
  - The quest countdown sQuest+0x1c steps by the delta in 30-fps frames (0x3a0160), and the game itself combines it with [[0x2126764]+56], as our stage timers do.
  - Audit of the module:
    - shells, effects, sounds, tar decay, timers and the cart all step by a unit delta;
    - motion windows go through motionCheck;
    - turns truncate like GU's own 0xc0e78.
  - Fixed: tar_add got the delta truncated to an integer (4U's u16 of this+20, 1 at 30 fps). At 60 / 120 fps that is 0, so no tar built up. Now the float delta: identical at 30 fps, same per second otherwise.
  - Observed: the user plays with the 120 FPS cheat, but em089's logged delta (tar anim line, tests 07-17 / 07-32 / 07-46) was 0.500 in ~95 % of samples and never lower, up to 1.12 on frame drops. So in practice logic ran at a 60-fps pace or less: vsync at 60, or an engine floor at 0.5 (not traced). Every test before this fix therefore added tar only on frame drops.
  - Fixed: the cannon "shot never initialised" timeout counted frames; now 90 quest frames.
  - Build 153932 B, 0 warnings.
  - MP test: run the two machines at different FPS patches on purpose.
- [ ] 5. Release notes: every player needs the same mod version. Unmodded players have neither quest 11491 nor em 0x59 (not fixable on their side).
- Safe already: save arrays bounded at index 136 (Gogmazios not counted); the unbounded quest-end tally 0x3a75c8 / 0x3a3930 is hooked (main.c).

Plan:
- [x] Step 1: diagnostic (action log tail: slot 0 kind/sub/param, F_TGT, local index, controller flag, serial, yaw; `hunters` list once; `net send/receive`). Solo test 2026-10-20 08:51 (log 08-51-50): all 50 actions `tgt 1 local 0 ctl 1`, no net lines (offline), no crash.
- [x] Step 2: fixes 1 + 3 (+ cannon fix, tar FPS fix). Same solo test: the user saw nothing abnormal; tar part changes 13 in 6.6 min (earlier tests 13 / 22).
- [ ] Step 3: real two-machine test, PC + the user's Steam Deck over RyuLDN (user's choice, 2026-10-20).
  - Topology: the Deck hosts the room (controls the monster), the PC joins and plays. Glitches show on the
    non-controlling copy, which is then the PC's screen, and the PC log shows `ctl 0` + `net receive`.
  - Same module build (same GOG_DEFINES) on both machines.
  - Tool: `python3 tools/mpdiff.py LOG_PC LOG_DECK` (written, checked on synthetic logs). Matches non-idle actions
    by serial; reports cat/num / tgt / slot 0 differences, position and yaw gaps, one-sided actions, gimmick events.
  - Fallback without the Deck: second instance on ryuroot/ with a re-IDed save copy (own guild card +0x8B0).
- [~] Step 4: gimmicks (finding 4). Cannon bug fixed (build 154076 B, 0 warnings); cart and doors need the MP test.
- [ ] Step 5: release-notes text.

## Category 2 (done)
- [x] 2/0 0x8b70dc(0), 2/65 (1), 2/66 (2) run; port-only safety timer 3000
- [x] 2/1 inline (table 0xe0de8c), 2/2 inline (0xe0de94): real engine move sequence, tables converted
- [x] 2/62 inline (0xe0de9c)
- [x] 2/6 0x8b7b38(0), 2/19 (1), 2/20 (2), 2/21 (3), 2/22 (4), 2/28 (5), 2/60 (7)
- [x] 2/15 0x8b7ea0(1): end call 0x9399c0 = GU thinkListAfter 0x8282c(this, 1) (behaviour agent); 2/27 (0) [x]
- [x] 2/35 0x8b7fb8 (takeoff): tremor shell + ground-impact effect ported (both skip at the +1800 hover, as in 4U)
- [x] 2/33 0x8b818c(0,0), 2/34 (1,0), 2/45 (0,1), 2/46 (1,1)
- [x] 2/61 0x8b836c(0), 2/63 (1), 2/64 (2) (safety timer)
- [x] 2/67 0x8b8b28
- [x] 2/68..2/71 0x8b8ca4(0..3)

## Category 7 (done: every number of dispatcher 0x8c0f94 has its handler)
- [~] 7/7 0x8bb5b0(0), 7/52 (1), 7/55 (2): lead point uses the hunter yaw only (W, from joint quaternion)
- [x] 7/17 0x8bb958
- [~] 7/19 0x8bbaf8(0), 7/20 (1): render flag this+0xca8 skipped; 0x8c34a0 ported (2026-10-18)
- [x] 7/25 0x8bbe04(0), 7/53 (1)
- [~] 7/26 0x8bc288(1), 7/30 (0), 7/54 (2): step-2 turn skipped while blending (this+644 = GU MOT_BLEND 0x4f4,
  ported 2026-10-19); left: the 0.6 write to 4U this+0xd38 (not 0xc78: this + 3072 + 312), a body-bend input of the
  model code 0x956bfc (vtable entry 0xe5c7f4, sin / cos of it), GU twin not found (visual only)
- [x] 7/27 0x8bbf9c: 0x8c34a0 ported (2026-10-18)
- [x] 7/32 0x8bc5cc(0), 7/93 (1): interruption (-> 4/6) ported 2026-10-18 (map-contact list, behaviour section 3)
- [x] 7/45 0x8bcbb8(0), 7/60 (1), 7/62 (2), 7/64 (3), 7/66 (4)
- [x] 7/47 0x8bcdd4(0), 7/61..7/67 (1..4): wall probe (GU 0x1835b8) + turn chain by dash frame + stop blend ported
  2026-10-18 (behaviour section 3)
- [x] 7/105 0x8bdd2c: pitch aim layer (em089_aim) + uShell016 53 / 36 by aim weight (refreshed 2026-10-19: the
  "stubbed" / "skipped" notes on 7/105..7/146 predate the aim / uShell016 / tar-shot wiring)
- [x] 7/106 0x8be1a8: uShell016 37 at frame 350
- [x] 7/107 0x8be434(0), 7/110 (1), 7/120 (2), 7/129 (3): 7/110 yaw aim pair (em089_aim), uShell016 41
- [~] 7/109 0x8bed30: lead point yaw-only (as 7/7)
- [x] 7/112 0x8bf060: 0x8c34a0 ported (2026-10-18)
- [~] 7/114 0x8bf19c(0), 7/115 (1): 7/115 window bounds register-carried, taken as 78..160
- [x] 7/118 0x8bf5bc(0), 7/127 (1)
- [~] 7/122 0x8bf7e0(0,0), 7/123 (1,0), 7/124 (0,1), 7/125 (1,1): lead point yaw-only
- [x] 7/126 0x8bfe80: uShell016 41 at frame 240
- [~] 7/133 0x8c0090: render flag this+0xca8 skipped
- [x] 7/135 0x8c02b0: pitch-down aim layer (em089_aim), uShell016 41 at frame 240
- [x] 7/136 0x8be910(4), 7/137 (5)
- [x] 7/138 0x8c0680: 7 tar shots 0x8c9dd4 (tar_shot)
- [x] 7/139 0x8c07d8: 0x8c34a0 ported (2026-10-18)
- [x] 7/140 0x8c0a64(0), 7/141 (1): 0x8c34a0 ported (2026-10-18)
- [x] 7/142 0x8c0c70: tar rain, 13 tar shots + 12 drips in 4U call order
- [x] 7/143 0x8c1300(0), 7/147 (1), 7/148 (2)
- [x] 7/144 0x8c1630(0), 7/145 (1): 0x8c34a0 ported (2026-10-18)
- [x] 7/146 0x8c17bc (work+0xd9 = 1 at end not kept)

## Category 1 (done)
- [~] 1/0 0x8ba3e4; 1/3 0x8ba4f8(0), 1/8 (1), 1/25 (2), 1/26 (3); 1/29..1/32 0x8bb3a8(0..3): radial blur 0xc0819c
  and uEffect002 0xc0bd38 (effects agent), camera event 0x93457c (GU 0xaa418, needs em089's LCM) stubbed
- [x] 1/1, 1/4, 1/18, 1/21, 1/24 inline
- [~] 1/5 0x8ba6fc(0), 1/17 (1); 1/20 0x8baaac(0), 1/28 (1): net events stubbed
- [~] 1/16 0x8ba84c(0), 1/27 (1): net events stubbed
- [x] 1/22 0x8bb0f4(0), 1/23 (1), 1/33 (2), 1/34 (3): layers 80 / 81 (em089_aim_layer); forward speed
  speedFactor * 150 * motion speed / 16 and the velocity rotation while blending ported 2026-10-19. 4U layer 0 =
  this+576, GU this+0x4b0, same inner layout (C): +68 blend frames left (4U this+644, GU 0x4f4, getter 0xb0a8c),
  +80 frame (0xb09e4), +92 motion speed (4U this+668, GU 0x50c, getter 0xb09bc; 4U 0x8cb9ec / GU twin 0xd3d108 of
  pair 0x8cb898 -> 0xd3cdb8 divide the same timer by it). game.h MOT_BLEND / MOT_SPEED.

## Category 0 / 3 / 4 / 11 / 13
- [x] 0/0 0x8b9aa8, 0/1 0x8b999c; 0/2 shares it (port-only: 4U has no 0/2, GU slot 247 can request it)
- [x] 0/3 inline, 0/6 0x8b9844
- [~] 0/9 inline: 0x920058's busy-layer guard not mapped (plain setMotionEx); 0x94e654 composed
- [x] 3/0 0x8b6654(0), 3/1 (1), 3/2 0x8b67e4 (sleep flags 0x7fcbc / 0xc0410, rec+0x990 S)
- [~] 4/0 0x8b905c(0), 4/2 (1), 4/3 (2): 4U this+0xd38 body-bend write (window 34..112, 0x8b929c) skipped (see 7/26)
- [x] 4/4 0x8b938c; 4/5 0x8b9584(0,0), 4/7 (1,0), 4/8 (2,0), 4/9 (0,1), 4/10 (1,1), 4/11 (2,1); 4/6 inline
- [-] 11/0 0x8b6ac8 (0x8b6da4 when mode == 1), 11/1 0x8b6b80: end through unmapped 0x926044 (x2), net/model
  calls 0x9399c0 / 0x94283c / 0x9110c8 / 0x942258, and GU's engine owns category 11: reaction placeholder kept
- [x] 13/11 inline: 0xb05934 = GU modelRefresh 0x53a984 (2026-10-18)
- cat 10 stays as is (engine reactions)
- Fallback table removed: every em089 pair has a handler (module/em089_actions.inc is now an obsolete stub)

## GU API mappings added (game.h)
C = same body shape checked; S = strong.
- seqStart2/seqPoll2 0x7a340/0x7a364 = 4U 0x91db5c/0x91db7c (C); seqStart1/seqPoll1 0x7a314/0x7a338 = 4U
  0x911c44/0x92f720 (C); record layout identical except s32 -> float blend/start (4U Rathian 0xe0bc10 = GU 0x16a2a64)
- setStopDist 0x78b88(this, flags, 0, dist) = 0x92dc88 (C); inRange 0x78c34 = 0x92dd04 (C, tail 0x78f7c steers)
- findTarget 0xa6cd8 = 0x9128e4 (C); findTargetEx 0xa6d04 = 0x9276b4 (C)
- setTarget 0xc6e14 = 0x916bcc (S)
- turnToTarget 0x76cc4 = 0x91db84 (C; it is a turn, not a move)
- rotateVel 0x7cab8 = 0x91150c (C); speedFactor 0xbe5d4 (C); resetVel 0x7b5d4 = 0x916260 (C); stopMove 0x7bdd4 (C)
- vertAccel 0xbf7d8 = 0x915d7c (C); restValue/restApply 0xbf590/0xbca40 = 0x93d8a8/0x92e9d4 (S)
- setActionW 0x752ec = 0x935ac8 (C); thinkRequest 0x82510 = 0x927730 (C); slot 249 = 0x9559a8 (C)
- attackReset 0x7e048 = 0x90f934 (C); setMotionSpeed 0xb0870 = 0x922c78 (C); netEvent2 0xaa704 = 0x93e590 (S)
- sinf/cosf PLT 0x13efde8/0x13efdf4 = 4U sin/cos tables 0x568bf0/0x568bb8 (C)
- fields: W+352 vel -> rec+0x10, W+424 angles -> rec+0x50, W+384 -> rec+0x5c, W+0x1c7 -> rec+0x1b9,
  W+0x1c8 -> rec+0x1ba (C), W+0x1c9 -> rec+0x1bb (S), W+0x1d9 owner -> this+0x7420 (C), this+20 dt -> this+28 (C),
  motionCheck r2 = out float* (window fraction)
- mapped 2026-10-18 (behaviour agent): 0x8c34a0 (slot fields), 0x9399c0 -> 0x8282c, 0xb05934 -> 0x53a984, 0x910c6c
  -> 0xc24d8 (camera shake, was mislabelled "turn"), 0x93457c -> 0xaa418 (camera event).
- unmapped (stubs): 0x954e5c (effect), 0x9200a4, 0xb052d8,
  0x935ff0, 0x918e80, 0x2b9cd4, 0x6620c4 (effects), 0x8c9dd4 (shell spawn), 0x93156c pitch/roll part

## Vtable overrides (4U em089 slot -> GU slot)
Key finding: the AI's most used condition, EMC opcode 0x6f (111 uses in em089_cmd), is `switch (vt+0x214(this, id))`
(GU selector 0x844e8 -> 0x81ff8) = GU slot 133, base returns 0: every such condition was false before. em089's EMC
never uses the other monster-virtual opcodes (0xa3 -> slot 134, 0x4f -> slot 256).
- [~] 51 (0x8c9084, 29-way condition) -> GU 133 (C by semantics: ids 0..28 = cases): cases 0-3, 8-13, 22-27 ported;
  arena cases 4-7 / 14-21 (Speartop Crag points 0x936894) return 0 (logged); 28 = spawn byte 3 rec+0x5cb6 == 2
  (2026-10-18, behaviour agent). Slot 133 is also
  queried by GU engine code (0x9ef3c, 0xa134c, 0xb1d1c) as 4U 51 is (0x9238ec, 0x931d14, 0x943958, 0x94a434): S.
- [~] 40 (0x8ba258, per-frame state) -> GU 119 (S: positional match of the per-frame updates 4U 0x94d26c (43, 40,
  77, 75) / GU 0xadb3c (.., 119, 170, .., 124)): data set 0/1/2 (0xc833c), rage roll work+0xcc, cooldown
  work+0xd0 countdown (from 77) ported; tar machine 0x8c2518 (incl. W+0x40c = rec+916 since 2026-10-18) / 0x8c352c
  ported (tar-machine agent); attack-slot reset ported 2026-10-18 (run at the start of slot 125).
- [~] 47 (0x8c8778, action start (cat, num)) -> GU 129 (C: setAction bookkeeping 0x755b4 calls vt+0x204(cat, num)):
  flying-attack counter work+0xcb, lights tail 0x8c8a40.. (2026-10-18) ported; W+0x28d and the cat-10 knock-down
  branch not.
- [x] 50 (0x8c8da0, per-part material loop) -> GU 132: em089_tar_update (tar agent), wired.
- [x] 39 spawn part: em089_tar_spawn wired at the end of GU slot 118 (em089_spawn_setup). Per-frame state part of 39
  (tar amounts -> part modes, W+0x7814, head / tail visibility in steady Solid) not ported yet.
- [ ] 75 (0x8c3ca0, per-motion events: hits + effects) -> GU 124 (S-, positional). Its hits only matter once the
  attack data is converted (EM089_ATTACK_HIT); not ported.
- [~] 77 (0x8c99a0) -> run from our slot 119 right after the slot-40 logic (4U order in 0x94d26c; GU 170 by position
  not used): 0x8c5768 per-motion mode table ported (mode 0 / 1 + attack id at fixed frames, work+0xe4, cooldown
  10800 on motions 0x10b / 0x316), 0x31f / 0x32c yaw windows, cooldown countdown. 0x8c5768's middle part
  [0x8c5d68..0x8c5e34] = the map-hit sphere morph (NOT locomotion speeds; GU 0x712a4 block = dtbase+0x84) ported
  2026-10-19 as maphit_frame (In-game test 5 "High ground (test 6)"). Not ported: work+0xe8 -> work+0xe5. The work+0xe4 /
  0xca reset tail [0x8c5e38..0x8c622c] is ported 2026-10-18 (behaviour agent: e4 cleared outside the glow motions /
  windows in phase 2, log `em089 work+0xe4 reset`; brings em089_efx_aura back). Earlier text:
  work+0xe5. 0x8c64b8 (wing) and 0x8c6300 (lights) ported 2026-10-18. FIX of the "stuck biped" bug (2026-10-17 test): without it nothing returned the
  mode to 0 after 7/118-7/120 (4U does it from the motions: 0x24b / 0x24c f220, 0x24d / 0x24e f290, 0x246 f250).
- Time scale (bug 2 check): 4U counts with this+20 = GU this+28 (timerDown also uses it). Both are in motion-frame
  units, 60 per second: em089's aim rates are angle / window length in motion frames, applied with this+20 over that
  window (7/7: 122, 7/109: 54). The 120FPS game measured ~60 units/s, so this+28 is already frame-rate normalised.
  4U tar 130 -> 100 = 15 x 180 = 2700 units = 45 s (observed 42 s); the 84 s figure assumed 30 units/s. No change.
- [x] 46 (0x8c677c) -> GU 127 (C: the remap both setActions loop on, same condition): 0/0, 0/1 -> 1/5 (1/20 in
  mode 1). em089_action_remap, behaviour agent section.
- [x] 48 (0x8c6e58) -> GU 130 (C/S: per-frame, result unused in both; content = camera shakes): 115-entry table
  (emulated), jointFx 0x910c6c = GU camShakeJoint 0xc24d8. em089_motion_frame.
- [-] 60 (reaction capability by type via rank table 0x94741c), 65 (mode == 1), 57 (state == 0), 52 / 58 (return 1),
  64: called only by 4U engine reaction code (0x947e68, 0x9468d8, 0x920104, 0x9263a4, 0x944e80); GU counterparts
  of those callers not found yet (not in apimap2). Not AI-related.
- [-] 35 (0x8ca074): base onMotionChange 0x94e6c0, then motion 61 -> model flags this+0x108 / +0x10c / +0x114
  (render flags) else this+344 = 1.5: no behaviour, GU model-flag map unknown.
- [-] 36 (0x8c9f4c, (this, stage byte global+0x1c), called by 4U 0x19fa60 / 0x1a046c / 0x1a0638): base setup
  0x94dd8c, per player W+0x28f bits + 0x934498 (engine target registration), this+344 = 1.2; only when the byte is 61:
  model flags, position (80, 0, 900), yaw 0x8000 and setAction(13, 11) (0x91f744: the dive-in entry). The meaning of
  61 is unknown (notes/stage.md: not the quest map number), so the 61 branch is not ported; 13/11 itself is.
- [-] 42 (0x8c9d68): stage byte 61 and quest id 1033..1096 -> model flag this+0x108 bit 17 (quest id > 1096
  clears): render flag only.
- [-] 56: returns 0 like the base.
- [x] 78 / 79 = GU 171 / 172, net sync of work+0xda. Ported 2026-10-20 (em089_net_get / em089_net_set, see Multiplayer).
- [-] 76 (0x8c3c4c): pitch of the W+0x7a20 vector in range; only caller 4U engine 0x91a758 (right after a species-89
  special case writing W+0x792c) -> 0x390f9c(.., 1020, -1) = cMhMotionEffect request (effects agent's finding:
  0x390f9c is the motion-effect request), i.e. an effect choice, not AI. GU slot 169's caller 0xa4324 is a vcall
  on another object (this+0xb64c), so 76 -> 169 is wrong; the GU counterpart of 0x91a730 is not identified.
- Slot 42 / 7/47 with the arena facts (arena agent): stage_alias_active() is the Battlequarters gate, but slot 42
  only toggles a model render flag (nothing to gate), and 7/47 is blocked on the GU sweep output layout (normal +
  attribute byte), not on the gate; when ported, the 4U wall types 2..5 come from the 1:1 converted SBC attributes.

## Remaining systems: shells, aim layers, slot 75, hits (2026-10-17 night)
- [x] Attack hits ON by default (em089_act.c: EM089_ATTACK_HIT unless -DEM089_NO_ATTACK_HIT). Safe: GU attackEx
  0x7dc2c looks the index up through 0x70ffc, which checks the attackdata count and returns 0 (attackEx bails).
  0x8c34a0 (shorten an active hit window: timer 30 + flag 4) stays a logged stub: GU attack slots are embedded objects
  at rec+0x998 + slot * 184 (flags word at +0x30 = rec+0x9c8, u16 at +0x34; 4U: W+0xc08 + slot * 152, index +52,
  flags +0x3c, timer +72); timer / index offsets not pinned.
- [ ] Tar shells (the missing tar: shots, rain, drips, beam blobs). Findings:
  - 4U event poster 0x660e88(mgr *0xef3cf0, type, data) constructs uShell000..059 objects (types 0..59); em089's tar
    shell is type 50 = uShell050 (688 bytes, ctor 0xc8fc1c, base 0x9ab18c, vtable 0xe6e86c), posted by 0x6637a4 from
    0x8c9dd4 (7/138, 7/142 ...) AND by 0x662b00 from the frame-event helper 0x8b8e28: that helper is NOT
    sounds/effects but tar drips (part p in a tar mode matching the mask -> a type-50 shell at frame*2, capped by
    work+0xcd, random by work+0xec/0xed). Effect posts 0x6620c4 = type 16 (uShell016, effect object).
  - GU has no 4U-style poster for monster shells: monster code allocates a cSetupParamEmBaseNN (allocator 0x3faf28
    (size, 16), 512 monster call sites; e.g. Rathian 0xcf560c fills owner this+0xcac8, type 15, this, ...) and builds
    a generic uShellEmBaseNN (00..61, DTIs constructed at 0x3fade4..0x43b374, sizes 5616..5984) or a per-monster
    uShellEmXXX_sp_NN class; uShellEnemy (0x43c100) / uShell (0x4a38ec) are the bases; 0x4a2f5c..0x4a3164 (~900
    monster calls) are uShell setup helpers. Manifest field 25 = the monster's shell arc (still Kushala's 0x7a67).
  - GU request API (C, Rathian 0xcf5610..0xcf56a4): param = alloc 0x3faf28(64, 16); param+0 = param-class vtable
    (selects the shell class), +4 = this+0xcac8, +8 = 15 (shell kind), +0xc = owner (this), +0x10/+0x14/+0x18 =
    rec+0x40 / rec+0x5b4 / rec+0x48, +0x1c = 0, +0x20..+0x28 = a global vector, +0x2c = 0, +0x30..+0x38 =
    this+0xfe8..0xff0, u16 +0x3c = 0xffff; then tail call 0x48c4f0(shell manager singleton, param, 0, 0) = GU's
    counterpart of the 4U poster 0x660e88 (request, probably net-synced).
  - Rathian's parameter class (literal 0xcf56ac -> GOT 0x183cd48 -> vtable 0x1755698 + 8) = cSetupParamEmBase01
    (methods 0x3fc1xx). 0x48c4f0(mgr = *0x1892550, param, 0, 0): id = param+4 must be < 412; max 144 live shells;
    static id table 0x1763448 (412 x 12 B: class DTI, param DTI, shell resource FILE ID) and class table 0x1765bd8
    (id * 12); requires a loaded resource at mgr+0x1c+id*4 (from the monster's shell arc), else drops the request;
    then class->newInstance, 0x4a1c84(shell, resource), shell vt+0x13c(param) setup, unit add 0xc067ec, 0x48c6c8.
    Examples: ids 84-89 uShellEm001_sp_00 / cSetupParamEmBase00 (files 0x89a7..), 90-95 uShellEm001_sp_01 /
    cSetupParamEmBase01 (Rathian fireball, files 0x89ad..; Rathian stores its id in this+0xcac8), 96-100 _sp_11.
    Name map of all GU DTIs (bss address -> name): scratchpad gudti.pkl (rebuild: DTI ctor 0x7aedcc call scan).
  - 4U em089 has NO shell data file: uShell050 is code (vtable 0xe6e86c; methods 0xc8e938 / 0xc8f028 / 0xc8fc18 /
    0xc90a3c, base uShell 0x9ab18c) using em089's EFLs (em089_0NN.efl in the arc). Kinds: 0x8c9dd4 posts kind 4 / 5,
    0x8b8e28 kind 1 / 7 (drip; 7 while work+0xca).
  - Plan (not started): (A) new module class uShellEm089 (em089_shell.c, derived from GU uShellEnemy 0x43c100,
    5584 B) translating uShell050 (falling blob, landing, hit, EFLs), registered in a free row of the id table
    (runtime patch of 0x1763448 / 0x1765bd8, the table is relocated data) with em089's own resource; or (B) a GU
    generic uShellEmBaseNN whose behaviour matches, fed converted data (needs the rShell format). (A) is the faithful
    route. Then `em089_shell(self, kind, pos)` replaces the stubs in 7/138, 7/142, 0x8c9dd4 and the skipped 0x8b8e28.
  - For the data agent: (1) the GU shell resource format (file at table+8, e.g. Rathian 0x89ad: type hash and
    layout) and whether a resource is mandatory for a module-created class; (2) em089's EFL list wiring (which
    em089_0NN.efl the shell and the tar beam use: read from uShell050 / slot 48 once ported); (3) manifest field 25
    (shell arc) must stop pointing at Kushala's 0x7a67 once em089's shell data exists.
- [ ] Aim layers (head tracking): 4U 0x9200a4(this, mot, s0 frame, s1) = setMotion on motion LAYER 1 via 0xb07be4
  -> 0xb054ec(this, layer 1, mot, flags 0, s0, frame, speed) + weight 1 - s1 (0xb054e0 = layer-1 weight at
  this+880+72; 0xb052d8 = getter); 0x918e80 smooths W+916 toward a target; 0x935ff0 = yaw + pitch layer pair
  (motions 0x255 / 0x256, frame from this+656 and W+916). The aim pose motions encode the angle as the frame.
  GU: setMotion goes 0xafda4 -> 0x72628 -> model vt+0x13c (slot 79) on layer 0; the GU layer-1 API is not found yet
  (apimap: 0xb054e0 ~ 0xb09e4 is a getter of this+0x500, not confirmed). Next: find a GU monster with head tracking
  (layer-1 setMotion with an angle-as-frame motion) and match 0xb054ec.
- [-] Slot 75 (0x8c3ca0, 1713 instr.): no attacks, no effects. Per current motion it evaluates curves (0xaac930 on
  tables at 0xff76bc, sinf / cosf) into floats +240 / +244 / +256 / +260 and words +0xf8 / +0xfc of an object
  (collision / lock-on geometry, unidentified). Low priority; the beam's tar is the shells above.

## Build state
- `GOG_MOD_ROOT=/tmp/x python3 module/build.py` OK (59752 bytes, hits on), no warnings (clang -fsyntax-only on
  em089_act.c, em089.c, em089_tar.c; build.py hides warnings on success).

## Where I am / next step
- Done: all action categories; vtable slots 133, 119 (+77), 129, 132 / 118; hits on by default; shell system of GU
  mapped (request API, id table, Rathian example). Next (in order): read 4U uShell050 in full and write
  em089_shell.c (plan (A) under "Remaining systems"), then the aim layers (GU layer-1 setter), slot 48.

## Behaviour fidelity (behaviour agent)
Owns module/em089_act.c, em089.c, em089.h (2026-10-18).
Build-size note (answer to the main agent): the shrink 94224 -> ~78 KB is NOT from this agent. My first build this
session (after only adding cond 28 / refill / drip-kind-8 / logs, no removals) was already 76908 B; my later edits
only added code (76908 -> 78480 B: slots 127 / 130, 13/11). I removed nothing and added no #if around handlers;
s_ported still has 124 (cat, num) pairs (gogreport's regex count). em089_tar.c (00:39) / em089_tar.h (00:42) and
em089_shell.c (00:20) were changed by other agents in that window. Current objects (-O2): em089_act 52.6 KB,
shell 4.8 KB, break 4.6 KB, tables.S 4.5 KB, em089 3.4 KB, tar 3.4 KB, main 2.1 KB, aim 1.9 KB, stage 0.8 KB.
Drip sites present: 142 drip_t table entries + 75 tar_drip( calls; 21 tar_shot calls.
Tool: scratchpad emcdis.py (EMC listing with GU's op length
table main 0x1732c8c, as read by 0x50c64 / 0x50ce0; GU opcode jump table 0x837ac, evaluator 0x8e144; 4U interpreter
0x94f488, evaluator 0x92b50c: same op ids and "kinds" (e.g. op 0x5f = HP % kind 2 in both, op 0x0b kind 4)).
### 1. Phase 2 (C, done in code; needs the in-game check)
- EMC: g0 s0 -> s16: op 0x0a (rec+0x2c0, combat) -> cond 2 (work+0xca) case 1 -> g0 s10 (phase-2 dispatcher) else
  s3 (phase 1). work+0xca is set ONLY by the roar 1/25 (1/31 flying) [4U 0x8ba4f8 r1 = 2, frame 208, + camera shake
  0xc0bd38(57)], which only EMC group 6 s0 requests: `cond 2 == 0: HP% <= 50 -> CALL 45, 1/25 (1/31), CALL 47, CALL
  96 (7/146) else 1/26 (1/32)`; with work+0xca: HP% <= 25 and cond 22 latch -> 1/25 again + 47 + 96.
- Group 6 = the rage group (C): rEnemyCmd +0x68 = 21 group POINTERS (4 B, loader 0x51e24), so [cmd+0x68]+0x18 =
  group 6. GU addAnger 0xbcc04(this, dmg): anger rec+0x510 += dmg * factors, threshold by HP decile from data block
  +0x28 (default 600); at the threshold, not enraged (rage timer rec+0x514 <= 0) -> setThinkEvent 0x7fc40(this, 4)
  (rec+0x362 |= 4); the think-event dispatcher 0x7f0cc: rec+0x362 & 4 and list 6 allowed (0x825ac) -> list 6,
  [this+0x72f4]+0x18 (0x7f960) -> EMC group 6 s0. Rathian's GU g6 s0 = its rage roar 1/9, Kushala's 1/27 (checked).
  (Correction of a first reading: [cmd]+0x30 = group 12, used by 4U 0x939500 / 0x92e218 and GU 0x82ddc / 0xb6f0c
  on the W+0x5f8 bit 13 / this+0x1069 bit 5 state = the weak / limp -> sleep group: Rathian / Kushala g12 = op01 +
  category 3/4 sleep actions; em089 g12 = op01 only.) So: phase 2 = first rage at HP <= 50 %. Engine-driven; our part
  (cond 2, 1/25, work+0xca) was already right. Previous tests: no rage seen (no 1/25 / 1/26 in the logs;
  TEST_HP_PCT=60 > 50 anyway).
- Phase 2 effects now ported: 0x8c2518 also writes W+0x40c = GU rec+916 (second motion-speed factor; 4U 0x941dd4 vs
  GU 0xb000c same shape, C) = 1.1, or 1.155 when spawn byte 3 is 1 / 2 (every frame while work+0xca).
- cond 28 (W+0x797e == 2) mapped: W+0x797e = spawn-record byte 3 (4U 0x91e360 copies record bytes 0..5 to W+0x79ba,
  W+0x14c, W+0x797f, W+0x797e, W+0x7982, W+0x7988; GU 0x6fb14 copies the same bytes to rec+0x5ce4, slot 41,
  rec+0x5cb7, rec+0x5cb6, rec+0x5cba, rec+0x5cbf: C). 4U m11014 = 0, m11035 = 1, so cond 28 is 0 in both 4U
  Gogmazios quests (the s25..s32 scripts are for byte 3 == 2 only). Also used: drip kind 8 (byte 3 in {1, 2} + work+0xca).
- Logs: `em089 phase inputs: spawn byte3 B, enraged E, anger A, work+0xca S, hp P%` (spawn), `em089 rage on/off
  (hp .., anger ..)` (rage timer rec+0x514 > 0 edges, S: only read as "already enraged" by addAnger),
  `em089 phase 2: roar 1/25 sets work+0xca`, `em089 phase 2 refill: tar 255, speed2 x1000 1100 (spawn byte3 B)`.
- Test aid (new): GOG_DEFINES="TEST_HP_PCT=45 TEST_RAGE=60" calls the engine's addAnger(this, 30000) once 60 s after
  spawn (log `em089 test rage: addAnger -> anger .., think events ..`), so the rage group runs with HP <= 50 % and
  1/25 starts phase 2 in a short session.
- EMC op semantics checked in GU 0x8e144: HP% (kind 2) `case N` = HP% <= N, cases in order.
### 2. Slots 46 / 48 (C, done)
- 4U slot 46 = GU slot 127: 4U setAction 0x90efac calls vt+0xb8 (0x90f1c8) in a loop until (cat, num) is stable,
  GU 0x76154 calls vt+0x1fc (0x764b0) likewise, then vt+0x200; condition in both: mode 1, or owner (W+0x1d9 /
  this+0x7420) and mode != 3. em089 0x8c677c: (0, 0) / (0, 1) -> (1, W+0x1c9 == 1 ? 20 : 5). This also remaps slot
  247's end-of-action idle (mode 2). Log `em089 remap 0/N -> 1/M (slot 46)` (20 max).
- 4U slot 48 = GU slot 130: called per frame by 4U 0x919f60 (after W+0x1dd) / GU 0xae830, 0xaf19c (after
  this+0x7426), result ignored in both. 0x8c6e58 = only motionCheck(0, f) + jointFx 0x910c6c(joint, id) + 0x91a884
  (W+0x42c & 1, tail severed). jointFx = camera shake at a joint: 4U 0x910c6c and GU 0xc24d8 same shape (area ==
  player area, joint -1 -> 0xbfd348 / 0x49e5c, else joint pos -> 0xbfe98c / 0x49eac; GU target 0x19148 -> mgr+0x54
  object of DTI uFestaCamera). Table of 115 (motion, frame, joint, id, tail) extracted by emulation (scratchpad
  emu4u.py: unicorn, 4U mem.bin, stubs for curMotion / motionCheck / jointFx / 0x91a884), cross-checked with the 89
  static call sites. Log `em089 camera shake id I joint J (motion M frame F)` (40 max).
### 3. Remaining handler stubs (status 2026-10-18)
- [x] 0x8c34a0 attack-window shorten: GU slot = rec+0x998 + slot*184; the 4U arm 0xb700f8 and GU arms 0x168be8 /
  0x168e98 copy the same attack record in the same order: serial 4U +52 = GU +52, record +0xc flags 4U +0x3c = GU
  +0x40, record byte +0x18 4U +72 = GU +80 (C layout, S semantics). Ported: serial != 0xffff -> +80 = 30, +0x40 |= 4;
  plus the slot-40 per-frame undo (+80 = 0, flag 4 clear) at the start of our slot 125 (placement deviation: 4U does
  it in slot 40; done before the handler so "reset, then shorten" holds whatever GU's slot order). Log `em089 attack
  slot S shortened` (20 max).
- [x] 13/11 0xb05934 = GU 0x53a984 modelRefresh (C: GU monsters call it right after setMotion 0xaff40).
- [x] 2/15 end 0x9399c0 = 0x945e60(this, 1) = GU 0x8282c(this, 1) post-action think-list choice (C). Log `em089 2/15
  end: thinkListAfter -> list N`.
- [x] wing size 0x8c64b8 (tar-look agent's em089_wing_update) called from em089_slot77 in 4U order, word bit 17
  set / clear + tar_vis. Log `em089 wing large/small (motion M), word W` (40 max).
- [x] lights: slot-47 tail (0x8c8a40..0x8c8be4, jump table 0x8c8b58) -> lights_action_start: bits 18-20 cleared at
  every action start; cat 7: breath attacks 107 110 114 115 118 120 126 127 129 135-137 143 146-148 -> light 0 +
  bit 22 + state 1 (+ bit 21 if chest tar not Solid); 139 l2/b18, 27 l2/b19, 112 l3/b19, 144 l4/b18, 145 l4/b19, 140
  l5/b18, 141 l5/b19, 133 l6/b20, 19/20 l7/b20 (light k = 4U work+0xa8+4k = name k of 0xff6fb4, slot 39 0x8b9ee4).
  0x8c6300 -> lights_frame (per frame from slot 77): state machine work+0xc8 (F_LIGHT): breath -> 1 (bit 21 follows
  the chest tar), else 1 -> 2 -> light 1 (Gas_Bress_End) -> 3 -> when that anim is at its last frame: 0, bits 21/22
  cleared. Spawn: state 0, light stop (slot 39). Logs `em089 light K for 7/N, word W`, `em089 light 1 (breath end)`,
  `em089 light off` (40 max). Own helper light_end_done (reads the type-6 material through em089_tar.h constants);
  an `em089_light_done()` in em089_tar.c could replace it (tar-look agent).
- [x] 0x93457c "net event" = camera event type 4 (id = kind) for the local target, GU 0xaa418 (C). ON by default
  since 2026-10-18 (-DEM089_NO_CAM_EVENTS = stub). The arc's field 11 was Kushala's LCM ("placeholder (em024_00,
  renamed)"); now converted from 4U e089_cam by NEW tools/lcm4u2gu.py (v4 -> v5: 16-zero-byte record prefix as in
  all 689 GU records, offset fields +40/+60/+76/+96/+112/+132/+152 shifted by 16 * records; validated: every
  relocated offset points at the same bytes, Rathian 4U vs GU differ only in those fields and sizes). Camera code
  0x1d4a0 reads list data +6 = 256 ids, +8 + 4 id = record (0 = skip), so absent ids are harmless. Arc rebuilt
  under the ARC LOCK (`python3 tools/build_em089_arc.py --cmdtbl gog`), em089_files.inc byte-identical, LCM in the
  arc = v5, 33164 B. Log `em089 camera event K (0x93457c -> GU 0xaa418)` (30 max).
- [-] For the effects agent (comments at the call sites): 0xc0819c = uMhRadialBlurFilter at joint 3 (roars);
  0xc0bd38 = uEffect002 id 57 (phase-2 roar); 0x954e5c (2/35) = ground-impact effect (shell posts 0x661d18 types
  1/2/11/12/26/27/28). Not camera shakes / quakes (the old names were wrong).
- [x] tar chest event 0x2fcc50(203): it is sSoundControl (sound agent: sound 203 at joint 2 = em089_se_oil_flow;
  my "UI notification" reading was wrong). Now `em089_snd_tar_chest(self)` (em089_snd.h).
- [x] 7/32 interruption (2026-10-18): the list is the monster's MAP-CONTACT list (not hits, not breaks): 4U W+0x810
  count / W+0x630 + 48 i, filled by 0x9185d8 from the collision dispatcher 0x2ba7fc after the polygon-info filler
  0x2b95a4 = GU count rec+0x7a0 / rec+0x5c0 + 48 i, filled by 0xa75f4 from the dispatcher 0x18285c (target type
  +0x1052 == 1) after the filler 0x1815a4 (C). Record +5 = polygon attribute >> 24 (wall type). 4U 0x8bc8b8: 7/32
  only, findTargetEx(0, -1, 0x2000, 4) != -1, a contact of type 4 / 5, owner, kind-1 check of 310 not passed ->
  inside 0..308 (kind 3) step 2 (4/6 at 308), else 4/6 + stopMove now. Log `em089 7/32 interrupted by a type-4/5
  map contact` (20 max).
- [-] slot-47 category-10 branch (10/108, 109, 114, 202, 203: knock-down reactions; 10/114 builds a 200-B object
  via the effect manager 0xc088d8 and calls 0xc48378(42, 29, 25); 108/109/202/203 work+0xe5++ / work+0xe8 = 900):
  category 10 is engine-owned in GU; not ported (logged).
- [x] 7/47 wall probe (2026-10-18): 4U 0x2b9cd4(col, owner, from = pos, to = pos + yaw-rotated (0, 0, speedFactor
  * 1567), s0 10, area, pos out, normal out, info out, mask 0x3fff0000) = GU 0x1835b8 (same prologue; core 4U
  0x2b9904 = GU 0x182f70 with pos / normal / info out pointers; info filler 4U 0x2b95a4 = GU 0x1815a4: +5 = wall
  type in both, face normal at info +0x18 (4U) / +0x20 (GU): C from GU code). Accept |atan2(nx, nz) + 0x8000 - yaw|
  < 50 deg (var 0) / 60, type by variant (0: 2-5, 1: 5/2, 2: 3, 3: 4, 4: 2/5) -> timer 0, work+0xda = type (2 / 3
  also W+0x145 = 1), 4 or 5. Dash end with the timer already out (and controlled here) -> 1/22 or 1/23 (1/33 / 1/34
  with W+0x145) by dash frame ([152, 178] / [230, 252] / other -> 22, [0, 152) / (178, 230) -> 23); else the stop
  motion with blend 20 in frames 0..121 / 170..217, else 6. Wall types come from the 1:1 converted SBC attributes
  (arena agent); in the Fortress-only build the attribute values are Fortress's. Logs `em089 7/47 wall probe:
  type T ...` (30 max), `em089 7/47 wall turn -> 1/N` (20 max).
- [-] cat 11 (0x8b6ac8 / 0x8b6da4 / 0x8b6b80): unchanged decision (unmapped 0x926044 end, GU engine owns cat 11).
- [-] "Dragonator fired" stage flag (+0xdd29 bit 0 via 0x6bc67c): NOT read by em089. The call at 0x8b46dc is in
  0x8b4638 = slot 51 (vtable entry 0xe6a1fc) of uEm088 (vtable 0xe6a130, getDTI 0xd022bc), which lies before
  em089's block (0x8b661c..0x8ca1f0). The other callers are 0xb1ab88 and 0xb89ed4 (outside both monsters). em089's
  block has no literal of the stage global 0xfbeffc and no 0xdd29 offset. Nothing to port; stage_gimmick.c left
  unchanged.
- [ ] 0x6620c4 = uShell016 posts: these are ATTACK shells (the breath / beam / explosion hits), a missing damage
  source; port needs a shell class (em089_shell.c, shell agent) — spec (all from 4U code):
  - 0x6620c4(mgr *0xef3cf0, owner, &pos-struct, r3 subtype, [sp] u16, s0..s2) -> 0x660e88 type 16 = uShell016 (DTI
    0x10bba1c+0x20 = 0x10bba3c, 704 B, vtable 0xe6d98c; slot 22 init 0xc69ddc, slot 23 per frame 0xc6ac64, 24 kill).
  - em089 sites (subtype): 7/105 0x8be100 (53), 0x8be138 (36); 7/106 0x8be3c8 (37); 7/107.. 0x8be84c (41); 7/136
    0x8beac8 (51); 7/114 0x8bf560 (41); 7/126 0x8bffcc (41); 7/135 0x8c0620 (41); 7/143 0x8c14e0 (54); 7/146
    0x8c23b0 (52), 0x8c246c (55), 0x8c248c (56).
  - init: every em089 subtype except 6 first posts a uEffect002 via 0xc0b470 (effect manager *0x10572a4; ids 50 /
    53 ...: effects agent), then the default path arms the shell attack 0x9ab120(shell, records 0x102b3d0 + 96,
    index = table 0x102bad8[subtype], [sp] 31, 2) and sets the life +0x2b0 = 600. Attack records (40 B, same format
    as uShell050's): 6 -> rec 6 (power word 0x0063), 36 / 53 -> 31 (0x0078 = 120), 37 -> 32 (0x0080), 41 -> 36
    (0x0096 = 150), 51 -> 40 (0x0104 = 260), 52 / 55 / 56 -> 41 (0x02a8 = 680, the 7/146 finale), 54 -> 42
    (0x008b). Record words (index: w0..w7): 6: 00630000 00030078 32000100 00000001 0 0 00020400 00001900;
    31: 00780000 00020050 28000020 00000001 00080000 0 00021200 00001400; 32: 00800000, rest as 31; 36: 00960000
    ... 00021400 00001400; 40: 01040000 ... 00021400 00001400; 41: 02a80000 00010014 05000020 00000001 00080000 0
    00021600 0; 42: 008b0000 ... 00021400 00001400 (address 0x102b3d0 + 96 + 40 * index, 4U mem.bin).
  - per frame (0xc6ac64, case table 0xc6acd8 by subtype - 2): 37 / 41 / 51 / 52 / 54-56 follow monster joints
    (jointPos 0x93093c + jointMtx 0x930894 every frame); 36 / 53 (the 7/105 breath) track the owner's motion
    (0x90f994) and aim with atan2 (0xc6e9b4, 0x94460c); 6 uses jointMtx only.
  [x] WIRED 2026-10-18 (em089_shell016_post(self, subtype, 0), module/em089_shell016.h), frames and branches from
  the 4U code: 7/105 step 1 frame 160 (with the step++; 53 when the aim-layer weight 0xb052d8 is 0, else 36);
  7/106 step 1 frame 350 (37); 7/107/110/120/129 step 2 at frame 240 or the motion end, every variant (41); 7/114
  step 2 frame 240 (41; s0 loaded at 0x8bf1e8 from literal 0x8bf4b0 = 0x43700000 = 240.0 on the path to the
  check 0x8bf4ec, verified); 7/126 step 1 frame 240 (41; s0 loaded at 0x8bfeac from literal 0x8c0068 = 240.0
  before the branch to 0x8bff50, verified); 7/135 step 1 frame 240 (41); 7/136 variants 4/5 frame 238
  (51); 7/143 frame 218, every variant, between the two rise windows (54); 7/146 frame 572 after the drips, serial
  % 3: 1 -> 55, 2 -> 56, else 52. Builds 99864 / 100468 B (with em089_shell016.c), 0 warnings in my files.
### In-game test 2 fixes (behaviour agent, 2026-10-19)
- ROOT CAUSE of "HP never drops / anger 0 / no phase 2" AND "melee never hurts": our slot 253 override
  (em089_think_blocked) returned 1 during every running action (the F_BUSY think block). Slot 253 is queried by
  ~130 engine sites, not only the think check 0x82538: the damage update 0x97ddc (0x97ea4: 1 -> 0x98e40, skips the
  part loop, HP subtraction 0x98bb8 and addAnger 0x98e20; also no flinch / break counting), the death check
  0x9e3dc, and the attack code 0x7e104 / 0x7e13c / 0x7e194 (attack slots treated as inactive -> body attacks never
  hit; the uShell016 beam is its own unit, so it still hurt). Evidence from the log: 40 `dmg recv part N damage D`
  lines but no HP change in 10 min, no break flinch lines. FIX: the busy block now answers only the think check
  (`__builtin_return_address(0) == MAIN(0x82554)`), every other caller gets the base 0x7ff90 answer.
- TEST_RAGE aid: addAnger(30000) overflowed the s16 anger rec+0x510 (39000 > 32767 -> negative -> clamped to 0 =
  the logged "anger 0"). Now 2000 (x gains 0.9..2.0, threshold 700 = Kushala's dttune table, verified by emulating
  the GU loader on our dttune: obj+0x8c table thr 700, gains 1.3/1.1/0.9/1.0/1.25/1.5/1.0/2.0/1.5/1.5).
- Fortress interactions: the same slot-253 bug suppressed every damage-driven reaction (flinches, falls, traps,
  Dragonator / ballista / cannon hits all go through the damage update), which likely explains most of "missing
  interactions". Still open (traced, not ported): em089_cond arena cases 4-7 / 14-21 read 4U 0x936894 -> 0x689f7c:
  em089's emd has no point table (header +0x40 = 0), so 4U uses the fixed table 0x1004b78 = {stage 13 (global
  +0xc8c), area 1, points in bss 0x10b8854 (runtime-filled, writer not found yet)}; GU counterpart not identified.
  7/47 wall probe + turns (ported) use the converted SBC wall types.
- Expected in the next test (GOG_DEFINES="GOG_STAGE_ALIAS TEST_HP_PCT=35 TEST_RAGE=60 TEST_DOORS_SEC=120"):
  `em089 damage #n: -d -> hp` lines and `hp N%` steps as the hunter hits; break lines `part N ... flinch count`;
  natural `rage on` (or at 60 s `test rage: addAnger -> anger >= 700, think events 4`), then action 1/25 or 1/31 and
  `phase 2: roar 1/25 sets work+0xca` + `phase 2 refill`; engine reactions (category 10 actions) in the action
  list; the hunter taking damage from body attacks (ask the user).
- Builds 131288 B plain / 132164 B with the test defines, 0 warnings in em089_act.c / em089.c.

### In-game test 3 (behaviour agent, 2026-10-19, usage window nearly out: analysis only, no code change)
Log 2026-10-19_12-00-00. Test-2 fixes confirmed (HP 34 -> 25 %, rage on 03:06 -> 1/25 at 03:11 -> work+0xca 03:14).
- Item 2 (phase-2 transition attack): it DID run. After 1/25 the AI ran 2/35 (03:20) and 7/146 (03:31..03:54, motion
  0x26f), and its frame-572 finale shell spawned at 03:39 (`attack shell 1 spawn sub 56 ... -753 1545 601 -> -10319
  -21537 667`). It was not recognisable because of the beam geometry (item 3). EMC: g6 s0 phase-2 branch = CALL 45,
  1/25, CALL 47 (cond 10 -> CALL 80 / move / 2/35), CALL 96 (7/146 in state class 1 / 3).
- Item 3 (beam / pile position): the uShell016 segment is joint 3 + M * rotX(offset + (0, 0, 10000)) with M = GU
  jointMtx (em089_shell016.c s016_place). The logged segment is ~25000 long (2.5 x 10000 = the model scale inside
  the matrix) and points down / -x, not at the hunter (at ~(-441, 4393)). Next: check GU jointMtx 0xc1660 layout
  (row vs column basis, scale) against 4U 0x930894 and normalise the basis; the pile / explosion are the shell's
  end-of-segment events (4U 0xc6e9b4), only partly ported.
- Item 5 (tail): no sever happened. `part 6 (tail) flinch count 0 -> 1 BROKEN` is the tail's first BREAK level
  (dttune row: flinch HP 750); the sever needs 1500 more cut damage (row sever HP 1500, type 1 cut), so no cut-tail
  object / sever motion was due. The break-look mesh rows for g13 / g14 / g19 are clear-only in em089_break_update
  because tar_vis owns their cond-7 rows (known conflict, not fixed).
- Item 6 (permanent puddle): ground shells sub 1 (uShell051, life 660 frames = 11 s) spawn at every drip impact
  (shell kinds 0 / 1 from the 4U drip helper sites, 0x8b8e28). In phase 2 every tar part is Gas, so every drip site
  fires and puddles overlap continuously. Faithful to the ported code; still to compare: 4U uShell051 sub-1 life
  and the PEL 5101 effect length.
- Item 4 (ground height): ground shells land at y 0..4 on the arena floor (log), ground-impact effect skips when
  1800 above ground (4U rule: > 900). No wrong-height evidence found in the log yet.
- Item 1 (biped on high ground): needs the 4U arena point table (fixed table 0x1004b78, stage 13 area 1, points
  filled at runtime at 0x10b8854; filler not found). Not ported.

### In-game test 4 (2026-10-19 evening, log 16-53-41) + fixes (main agent)
User: (1) phase-2 laser invisible, its tar heaps and explosions far too big; (2) drip puddles short now, but a big
puddle stays under him and follows the model; (3) explosions OK; (4) after the tail break a white smoke every ~2 s
forever, 3 extra "breaks" before the cut, wrong break / cut animations; (5, 9) camp black triangles still there;
(6) corner minimap perfect; (7) 7/146 laser stays on one point, its exploding heaps float in the air, some hitboxes
wrong; (8) flying turns fine; (10) the tar beam does not come out of his mouth.
- [x] Beam capsule re-checked against 4U at every step (C): 41/54 0xc6c904, 36/53 init 0xc6a720 (per frame
  0xc6e8d4 = sound only), joint from the caller struct +0 (7/107 0x8be7a8: joint 3, offset (0, -50, 130), x angle
  0x1800), ctor 0xc6f948 (+0x2a4 joint, +0x270 offset, +0x290 x angle + W+0x1a8, +0x294 yaw + W+0x1ac); GU jointMtx
  0xc1660 = joint entry +16 (160-B entries, pos +64) = 4U 0x930894 entry +8 (168 B, pos +56): the same world matrix.
  So the steep (55-67 deg) capsules are 4U's own; the visual difference is in the effect.
- [x] Effect reference model (C/G): pos-only posts (flag 1) through the monster get the monster's attach model as
  target (0x6ff74 fills req+0xd0 only when 0); the follow step 0x329668 runs only with effect byte +0x1a0 bit 1
  (request flag 2). G: the target still seeds the transform (2.5 model scale, hover height) -> ground shells now
  posted like GU shells (target = the shell, flags 3, em089_efx_post_on) with em089_shell.c's deferred kill (slot 16
  waits for the effect, forced after 300 frames; dtor kills); beam records 4200 / 4300 scale 2.5 -> 1.0. New logs:
  `efx beam ID transform scale x1000 ...` and `ground shell sub N effect scale x1000 ...` settle it next test.
- [x] Puddle glued under him (S, corpus): the PEL record tail was the most common record over ALL GU PELs; over the 2648
  GU monster PEL u records the most common exact tail (177) differs at +0x36 +0x38 +0x3a +0x52 +0x53 +0x5c +0x64 +0x70
  +0x73 +0x86 and is the tail of Capcom's converted 4U footsteps (GU em071 / em072 ids 12 / 13, joints 63 / 73, 4U
  MEF flags 0x2a6). em089's footsteps (MEF 42 / 43, joints 63 / 73, flags 0x2a2) fire in nearly every idle / walk
  motion -> tools/efl4u2gu.py PEL_TAIL = that tail (all records). MEF flags / b0 do not map to single PEL bytes
  (no byte follows a flag bit over the 105 matched records).
- [x] Tail smoke: qe013_002 loops in GU; 4U's request flags (+0x60 / +0x61 of 0xc088d8) have no PEL field -> stopped
  after one cycle (120 frames, em089_efx.c tail_tick).
- [x] Camp wedges (helper): 2 of the 24 torch billboards of m26a00d-a00 had zero-key scale / angle tracks (GU never
  writes those on stage-set objects); tools/sdl.py drop_keyless, alias rebuilt (notes/stage.md). G until seen.
- [ ] Reactions (category 10 / 11): 4U em089 has its own handlers (vt44 -> 0x8c2784 / 0x8c3b7c), never ported (the
  port played act_react) -> react agent (module/em089_react.c).
- [ ] 7/146 single point: the capsule is 4U's; the sweep needs a check of what moves it in 4U (motion 0x26f head vs
  x angle) once the visual is back. Hitboxes "wrong": not analysed.

### White effects after the PEL_TAIL change (helper, 2026-10-19 ~18:45, static; arc rebuilt)
User: roar, some tar-puddle explosions, step smoke and the tail-cut effect render WHITE (were black).
- [x] Cause (C): the GU monster-majority PEL_TAIL switched on GU's per-record colour override. Old vs new tail differ
  at 10 bytes; 3 of them are colour: +0x64 (u16) 0 -> 7, +0x70 0 -> 1, +0x73 0 -> 1. Loader 0x323264 reads the
  160-B struct to record object +0x20 (effect +0x90). 0x327cb8 / 0x32b4f4 recolour the effect only when +0x70 == 1;
  colour from 0x3214f0: +0x56 -> table A[+0x64], else +0x73 -> global table B[+0x64] entry u16 +0x66, else RGBA
  +0x60; mode +0x71 = 3 = RGB lerp toward that colour by f32 +0x68 = 0.5, alpha kept. So every em089 effect was
  pulled halfway to table B[7] entry 0 (G: the stage ground-dust colour; the table itself is not identified).
- [x] Corpus (S, 5612 deduped GU monster PEL records): +0x70 / +0x73 / +0x64 = 1 / 1 / 7 in 1131 of 1432 list-1
  records on cm202 ground dust, but only 445 of 1250 on the monsters' own EFLs (627 have 0 / 0 / 0). 4U MEF records
  carry no colour, and over the 60 matched 4U / GU records (em001/024/027/071/072/077) no MEF flag bit separates
  +0x70 (bit 0x4: set 24 on / 4 off, clear 32 on / 0 off).
- [x] The other 7 bytes (kept from the new tail): +0x36 / +0x38 = transform mode (0x32a548: +0x36 4 -> 0, 1 -> 2,
  0 -> (+0x38 == 1 ? 1 : 0), 2 / 3 -> 3 if +0x3e == 6 else 4; old tail = mode 0, new = mode 2, the puddle fix);
  +0x3a = end mode (0x329dbc: 1 ends with the effect, 2 timed by u16 +0x44); +0x52 / +0x53 = ground-distance check
  (0x3293d0: +0x52 compares the height above ground with f32 +0x58 = 900; its effect on play not traced); +0x86 =
  player bitmask, read only when +0x36 == 4 (0x31d834); +0x5c not traced.
- [x] Fix: tools/efl4u2gu.py PEL_COLOUR_OFF (+0x64/+0x65/+0x70/+0x73 = 0 = the old tail's values) applied in
  pel_record to every record (4U sets no colour on any of them; for the beams per the uShell016 notes, not
  re-checked). Area colours (4U m19a00d-col MhEffect area_color_soil ...) are not involved: a GU record reads a
  table colour only through +0x70 = 1, now 0 everywhere; no stage file touched.
- [x] Same test: blob drips 3000 / 3001 (posted on their shell) no longer fell = the new tail's +0x36 1 (transform
  mode 2, placed once). pel_follows(): 3000 / 3001, 4200 / 4300 + sub (beams, moved every frame by code) and
  5100 + sub (uShell051, posted on the shell) take PEL_TAIL_PREV (the whole previous tail = their test-4 state);
  MEF motion records, 3100, 3300, 57xx, 6000+ keep PEL_TAIL (mode 2). Arc rebuilt twice (--cmdtbl gog): only
  effect\pel\em\em089_00u changed (292 records: 3 colour bytes; 70 of them also the previous attach bytes),
  em089_files.inc byte-identical, manifest identical.
- [ ] Check in game: dark effects black again; drips fall with their blob; step puddles stay on the ground (not
  glued to the model). Open: 5701-5704 (em089_050 on joint 1, 4U uEffect002 with an update 0x1b6520) and MEF joint
  effects stay mode 2 (placed at the joint, no follow); whether any 4U motion effect follows its joint is not checked.
  Possible follow-up: the tail-break smoke 3300 has a 4U code colour (37, 46, 49) (0xc48378) that could now go
  through +0x70 / +0x60, but 4U's blend for it is unknown.

### EFL unit +0x18 vs the white effects (helper2, 2026-10-19 ~21:40, static; arc rebuilt)
Question: is EFL unit +0x18 bits 12-15 (kept 4U value) a darkening blend that GU loses? Answer: NO.
- [x] Corpora (S): every EFL of the 4U ROM (13525 units) and of the GU romfs minus quest / sound arcs (13754 units);
  Capcom conversions = 31 GU files with a 4U original of the same unit layout at >= 97 % unit-byte identity (4U em027
  -> GU em070, em077 -> em013, qe008 -> cm200 ...; 59 units). Scripts: scratchpad eflcorp / eflconv / eflconvtab .py.
- [x] Meaning (C): bits 12-15 = 4U 'Intensity' (4U property list 0x2547e0: getter 0xcd8b10 = draw state bits 26-29,
  'Blend state' 0xcd8b7c = bits 5-15); 0x2e8864 copies them, the draw 0x35c440 picks one of 9 combiner set-ups with
  it. em089's black smoke units have Intensity 0 (colour 000000 / 271a12), its orange fire units 1 / 2 -> not a
  darkening mode. Blend index = unit +0 byte 3, kept by Capcom (57 / 58 converted units) and by us.
- [x] GU (S + C): bits 12-15 set in 0 of 13754 GU units (4U: 9446 of 13525), dropped in 21 / 21 converted units; no
  GU effect read of them found (GU state word 0xa7c210 = byte 3 + unit +0x50 bits 8/9/12; 4U reads those +0x50 bits
  too). GU-only bit 19: on every GU Billboard / Polyline / Polygon with blend != 14 and unit +4 bit 14 clear (2801 /
  2801; the 259 without = exactly those GU-only cases), added in 12 / 12 converted units, never in 4U; meaning not
  traced. +0x50 byte 2 (4U 0..37, GU mostly 0) is NOT a GU-only field: same index * 32 lookup in both games (4U
  0x402e64 = GU 0xa7c1ac); kept.
- [x] Fix (tools/efl4u2gu.py unit_4u_to_gu): every unit +0x18 bits 12-15 -> 0; types 0 / 1 / 2 -> bit 19 set.
  Arc rebuilt (--cmdtbl gog): 1110 entries, none added / removed, em089_files.inc + manifest identical; 45 EFLs
  changed only at unit +0x19 / +0x1a. Same rebuild (coordinator): effect MODs get a 0xFFFF after every mesh's index
  run (convert_effect_mod, as mod4u2gu): 7 effect MODs + em089_00 / _tail / _gekiryusou changed; all 42 MODs in the
  arc checked: every run ends with 0xFFFF.
- [ ] In game: no visible change expected from bits 12-15 (GU does not read them); bit 19 untraced, so look for any
  change in em089 billboard / ribbon effects (fire, smoke, roar). If the roar / step dust / 3300 tail smoke stay
  white, the EFL is not the cause. Note (S): between test 4 (black) and test 5 (white) only the PEL changed; with
  PEL_COLOUR_OFF the MEF / 3100 / 3300 records still differ from the test-4 tail at +0x36 / +0x38 / +0x3a / +0x52 /
  +0x53 / +0x5c / +0x86 (records 3000 / 3001 / 42xx / 43xx / 51xx use the full test-4 tail); +0x5c has no traced
  reader. 3300 also lacks its 4U code colour (37, 46, 49).

### Test-3 fixes (main agent, 2026-10-19 afternoon, static; build 131660 B, 0 warnings, arc rebuilt)
- [x] Beam visual vs hit (items 3 / 10): the capsule math already equals 4U 0xc6c904 (joint 3 matrix with the 2.5
  model scale in both games, so the 25000 length is 4U's too); the log fits a head pitched ~33 deg down by the
  animation + 33.75 deg. The mismatch was the EFFECT: posted on joint 3 with a joint-frame x rotation, while 4U
  uEffect002 0x1b5ba0 places it EVERY FRAME at the capsule start (shell +0x120) with the segment's pitch / yaw (+40
  for id 54, +35 for id 50) and scale 2.5. Now: PEL world records 4200 + sub / end 4300 + sub (efl4u2gu.py; old
  4000 / 4100 joint records dropped), posted at the start with the segment angles, moved every frame by
  em089_efx_shell016_move (called by em089_shell016.c after s016_place) with GU's live-effect setters, found in
  GU's own beam 0x10ab3d8: 0x32a45c(eff, pos, 0) and 0x8a7dc4(eff+0x150 object, rotation in RADIANS). The shell
  now places its capsule before posting the effect.
- [x] Item 6 (permanent puddle) FIXED (first analysis was wrong, user checked a 4U video: puddles, but short, none
  permanent): +0x16d is NOT only cleared by kill / owner gone. It is byte +5 of the shell's attack object (+0x168,
  set up by 0x9ab120 -> 0x9a9624 -> init 0xb700f8, which sets +5 = 1); its update 0xb6ff88 counts the record's start
  (+84) then length (+88) down and clears +5 at 0xb700a8 when the length runs out (also when the owner's motion
  changes for flag-0x100 attacks). uShell051's per frame (0xc9008c) and uShell005's (0xc598f4) end the shell on
  +0x16d == 0, so each ground shell lives start + length, not 660: sub 1 / 16 208 (was 660 = 3.2x too long), 6 / 17
  / 19 / 20 78, 3 220, 9 / 10 160, 11 165, 12 172, 13 155, 14 220 (its own 120 first), 15 142, 4 88, 5 / 18 20, 8
  15 (records 0x1031ca4 + 52 + 40 * sub); quake sub 1 24 (14 + 10) instead of 100. Ported as k_sub `end`
  (em089_shell051.c, counted with the age's step) and in s005_move. uShell016 / uShell050 per frames do not read
  +0x16d. Other facts kept: sub 1 also checks 0x6c5e88 (stage object); the drip helper doubles the frame itself;
  the ground-shell effect is posted once at init (0xc904d0). Not mapped: effect +256 = 2.0 (sub 14) / 1.25 (18).
- [x] Item 9 (arena behaviour) ported: the Battlequarters is stage 19, so 0x689f7c reads em089's emd point table
  (header +0x40 = 0) -> every point is (0, 0, 0) (the stage-13 table is another map). [CORRECTED 2026-10-19 late:
  record +0x40 = emd file word 18 = 19 real points; see In-game test 5 "High ground".] em089_cond 4..7 / 14..21 =
  the MONSTER's 3D distance to the origin ([this+0xc28] is the work record: same +0x7814 flags as [this+0xe28]):
  4..7 -> 80 + 10k within 450, else 2k within 750 / 800 (odd k), else 2k + 1; 14..21 -> within 1500. EMC scripts
  g1 s8 / s9 / s28 / s29 then move to a point (`01 00 05 08 n`): GU resolves kind 5 sub 8 in map_info (0xb3d5c,
  Kushala's placeholder, no stage-26 entry -> the monster's own position, radius 300) -> new hook set_target @0xC6E14
  writes (0, 0, 0) into the slot and converts to kind 6 / 254 (GU's own conversion for its instant subs). High
  ground itself is case 8 (target height: <= 300 ground 4, <= 1200 ledge 1 / 3 by x, else 0 / 2 by z; already
  ported, 4U 0x8c953c); the 4U arena collision m19a03d g00 has levels at y 0, 800-900, 1600-1700 and 2139 (around
  z 5200, where the hunter stood in test 3). New log lines: action lines end with `hunter y N`; `cond 8 (hunter
  height) a -> b at x y z`; `arena point n (slot s) -> (0, 0, 0)`.
- [ ] Item 11 (tail): the log shows the first BREAK (no sever, count 0). Rows: g105 hidden / g35 shown on the break
  (4U emd cond-6 rows; both groups exist in the model). Ask the user whether the tail tip look changed; the walk-
  through hitboxes and the "cut" motion are unexplained (no sever count, no stub clears flag 4).
  [x] Tail-break stub ported (4U slot 64 0x8c67c0, part 6, first break): item drop 0x911f58(this, W+408, 100, 0) =
  GU 0xac0ec (helper-traced), effect 0xc088d8 group 1 file 138 = qe013_002 (flat table 0xef895c) on joint 143,
  offset (0, 30, -100), scale 2 = PEL 3300 (colour (37, 46, 49) via 0xc48378 not mapped), then the sound. Log
  `tail break: item drop -> N, effect 3300, sound`. [-] The flag-4 clear: 4U's only reader is the player hit code
  (0xbe9c64 -> 0x68eb10, hit feedback on breakable volumes: flag 4 is on the head / chest / wing / tail / part-7
  records only); no GU reader or writer of record +12 bit 4 found -> left out. The [this+0x8d88]+0xed clear is
  skipped (written, never read).
  [x] Moving-beam effect request now mirrors GU's own beam post (0x10b04c4: req+8 = 3, req+0xc = area).
- [x] Item 7 lead (4U behaviour: 2/35 is a takeoff, see RESOLVED below): both 2/35 landings in test 3 hit the ground-impact frame with the monster at y 1800 over
  floor 0 (4U collision m19a03d g00 at (-529, 1909) = 0), so the 4U landing descent (motion 264, no mode write in
  4U 0x8b7fb8 either) did not bring him down in GU; the hunter stood on the 1701 ledge. rec+0x5b4 as ground is
  plausible (GU Rathian passes rec+0x40 / +0x5b4 / +0x48 to shells). Action log lines now end with `hunter y N
  em y N ground N mode N` to see where the height is held (flight mode rec+0x1bb vs motion root y).
  2026-10-19 later: the 1800 does NOT come from motion 264 (C, em089_1.lmt anim 8): its root track (bone 0xff,
  usage 4) is constant (0, 0, 0) and bone 0's local y stays 241..545 (end-frame vectors: 264 (0, 0, 0), 268 / 263
  (0, 720, 0)); joints 72 / 62 / 141 were at y 697 / 937 / 213 at the frames 24 / 30 / 50 drips. In test 3 the
  sequence was 1/25 (roar, grounded) -> 0/1 -> 1/5 -> 2/35 with no flight in between, while the hunter stood on
  the ~1700 ledge (dest -1165, 5319). RESOLVED (C, data): 2/35 is the TAKEOFF, not a landing. Motion 268's root
  track (bone 0xff, usage 4, type 4) is y 720 from frame 0 (x sways -204..361), 263's is constant (0, 720, 0):
  720 x 2.5 (model scale) = 1800 = the logged height; 264's end raises the hips (bone 0 y 297 -> 545, x 2.5 = 1362)
  so the body is continuous across 264 -> 268. 0/6 (next action) loops 263 = hover idle, then 7/146 sweeps from the
  air. So the height is 4U's own. The y itself is written by the rest pair BEFORE setMotion(268): 4U 0x92e9d4
  (state class W+0x1c8 in {0, 3, 6}: W+412 += value * W+440 * W+444, then 0x9167ec(1)) = GU restApply 0xbca40
  (rec+0x1ba in {0, 3, 6}: rec+0x44 += value * sizeFactor, state class -> 1); value 720 -> +1800. So 4U's 0x954e5c
  (height 900) also sees 1800 and skips the dust / tremor at this call: faithful, nothing to fix (setMotionEx
  writes no position in either game; GU vt+0x3d8 = 0x6c23c is empty). New trace (em089_slot77): `height up/down: y Y ground G action C/N motion M frame F mode D` when the
  monster goes more than 300 above its ground (rec+0x5b4) or comes back (40 lines).
- [~] Damage dealt (user: "he doesn't do much damage"), checked statically, no 4U/GU formula gap found (C):
  - Quest rates: GU em_nando_tbl (loc/arc/resident.arc, file 0xde1a, 32-B rows {HP, attack, defense, ...}) via
    0xbaaac(this, kind) -> rec+0x39c + kind; 0xc0528: attack rate rec+0x384 = row[attack byte][+4] * rec+0x390
    (init 1.0, 0xb8f18), defense rec+0x388 = row[other][+8]. 4U has the same table at 0xf3a330 (81 / 141 rows
    identical). 4U m11014 / m11035 use row 98 for all three (HP 4.3, attack 6.3, def 0.75) - the SAME row as 4U's
    Kushala G quest m10709. Our quest used GU Kushala G4's rows 91 / 108 / 93 (HP 3.05, attack 7.9, def 0.75);
    NOW (user: use his own) build_gog_quest.py writes HP row 116 (GU row with HP 4.3 = 4U row 98's; GU row 98 has
    3.4) and attack / other row 98 (6.3 / 0.75 as 4U; status fields = GU's row 98: 2.9 / 2.5 / 2.0 / 2.0 / 2.8 vs
    4U 3.4 / 2.5 / 2.0 / 2.0 / 2.6, no GU row matches 4U's exactly). Quest rebuilt (bytes 01 74 62 62 checked).
  - **2026-10-20 correction (C):** 98 was the 4U board-icon field (+0xE8, 98 = no icon), not the stat rows. The rows
    are at 4U +0x34 {u16 size, u8, HP, attack, other, u8, u8} (copied to monster work +0x414..+0x416 at 0x68aa30;
    HP 0x934084, attack 0x922d48, defense 0x922d78). m11014 65 / 109 / 79 (HP 2.05, attack 8.2, def 0.8; statuses
    1.5 / 1.5 / 1.15 / 1.3 / 1.15), m11035 69 / 115 / 83 (2.17, 10, 0.8); GU's rows of the same numbers hold the same
    values. User (same day): use them -> build_gog_quest.py reads them (tools/quest4u.py stats_4u). The old build had
    about 2.1x 4U's HP and 77 % (11491) / 63 % (11492) of its attack, which fits the user's "doesn't attack hard
    enough".
  - Powers: attackdata record +4 (u16 2) = power -> slot +0x38 (0x168c68); Kushala's 4U and GU records are
    identical, so GU did not rescale powers; em089's are 60 / 75 / 90 (Kushala 35-65). Body hits: power * owner rate
    (0x169548 -> 0x173c74); shells: power * owner rate at arm (0x4a2998).
  - Windows: record +0 start (absolute motion frame) / +2 length, shifted by the current frame at arming; 4U
    attackEx 0x93334c does the same (motion layer this+0x240 +68 / +80 vs GU this+0x4b0 +0x44 / +0x50).
  - So the per-hit damage should exceed GU Kushala's. Suspects: hits not connecting (test 3: beam misaimed, no
    explosions - both fixed), hit volumes. New log: `attack slot S index I active A power P rate R -> P*R`.

### Status / next (behaviour agent, 2026-10-18)
- Builds: plain 84376 B, GOG_STAGE_ALIAS TEST_HP_PCT=60 85000 B, 0 warnings in em089_act.c / em089.c (also with
  -DTEST_RAGE=60 -DEM089_CAM_EVENTS); s_ported 124 pairs.
- Test build suggestion: GOG_DEFINES="GOG_STAGE_ALIAS TEST_HP_PCT=45 TEST_RAGE=60".
- New log lines: `phase inputs`, `rage on/off`, `test rage`, `phase 2: roar 1/25 sets work+0xca`, `phase 2 refill`,
  `remap 0/N -> 1/M (slot 46)`, `camera shake id I joint J`, `attack slot S shortened`, `2/15 end: thinkListAfter`,
  `wing large/small`, `light K for 7/N`, `light 1 (breath end)`, `light off`; stub texts renamed (`roar radial blur`,
  `uEffect002 post`, `ground impact effect`, `camera event 0x93457c (no em089 LCM)`). tools/gogreport.py may want
  sections for rage / phase 2 / lights (not edited: not my file).
- 2026-10-18 later: 7/32 interruption, 7/47 wall probe + turns, camera events (with em089's LCM converted) done;
  build 86696 B plain / 87308 B alias, 0 warnings. Remaining: uShell016 attack shells (spec above, needs the shell
  class), cat 11, slot-47 cat-10 branch, slot 36's stage-61 entry.

## Tar material animations (tar agent)
Status 2026-10-17 (tar agent; owns tools/mrl*.py, mod4u2gu.py, build_em089_arc.py, module/em089_tar.[ch]):
- [x] 1. Cause check. Material animation hypothesis REFUTED: 4U anim blocks (tools/mrl_anim.py dump) only drive
  CBMaterial.fUVTransform (v scroll 0 -> 1 in Liquid/Gas) and CBMaterialStd AlbedoColor / Specular / Diffuse
  (Solid = albedo 0.5-1.0, spec.w 0.1; Liquid = albedo 1, spec.w 0.8). All tar materials are BSSolid; no
  alpha/dissolve track. The 4U static constants are Solid minus the tint. GU constants were fine too (template
  fAlphaClipThreshold 0, fAlbedoColor 1, fTransparency 1); textures fine (04_BM dark, alpha >= 119).
  Visibility bits from the log (groups 55d06f4b ...): tar groups 3, 6, 9, 11, 14, 22, 34 drawn (= 4U spawn 0x7c).
  Tar triangles: same winding as the coincident body triangles (group 0 body meshes), normals outward.
  Remaining suspects: depth (exact coplanarity; GU bias -32*N not honoured / not enough) and the old solid_nm
  template = Rathian WING (FTransparencyAlpha, wing flags w6 0x264dc020 / w7 0x8d901400).
- [x] 2. Static fix in the arc: (a) tar vertices lifted 2.0 model units (31 position steps, x2.5 model scale)
  along their normals (mod4u2gu.convert push=, build TAR_LIFT); (b) solid_nm template -> Rathian BODY mat 2
  (FTransparency, w6 0x200dc020, w7 0x8c800000); (c) Solid frame 0 albedo tint baked into $Globals.fAlbedoColor
  (head 0.5, chest 0.7, arms 0.8, tail 1.0) and specular rgb*gloss into fSpecularColor; 4U RS bias states
  kept. mrl_check: all OK; only tar positions differ from the previous MOD; em089_files.inc byte-identical.
- [x] 3a. Format: GU MRL animation block = 4U's, byte for byte (tools/mrl_anim.py, checked on all GU enemy
  MRLs). Converted: the 5 tar materials get their 9 entries (same names/order), tracks remapped 4U
  CBMaterialStd -> GU $Globals (albedo -> fAlbedoColor, specular rgb*w -> fSpecularColor), fUVTransform kept,
  Diffuse/Emission dropped; 'Solid' flagged autoplay (flags bit 1, GU 0xb0cbe0) so it plays with no code.
  Material type = 'mNN' of the name in w6 bits 21-28 (tar 1..5, add 6, wing 50, rest 0). Wing (Small/Large) and
  lights anims not converted (diffuse.w / emission only).
- [x] 3b. GU runtime (C): materials = this+0xf8[i < this+0xfc]; type = (mat+0x18 >> 22) & 0xff; animset
  mat+0x74; find 0xb0bb0c(set, name); play 0xb0cab0(mat, slot, idx); current 0xb0ffb8(mat, slot); em049 drives
  its own from object slot 132 (0xec4e64 -> 0xec534c). 4U: spawn slot 39 plays Liquid on head/chest (types 1, 2)
  and Liq_to_Sol on arms/tail; per frame 0x8c8da0 plays the transition on a mode change (work T=*(this+0x8d88),
  u16 T+0x54+2k target, T+0x5e+2k previous), then the steady anim when it ends; it also sets W+0x7814 bit
  0x8000 (head) / 0x10000 (tail) while in steady Solid (= hide g3 / g14) -> visibility, not ported here.
- [x] 3c. module/em089_tar.c/.h written (compiles clean standalone with build.py's CFLAGS, no data relocs).
  NOT wired: needs build.py source 'em089_tar.c', em089_spawn_setup -> em089_tar_spawn(self), a per-frame call
  em089_tar_update(self) (object slot 132 or existing per-frame hook), and em089_tar_set_mode(self, k, mode)
  wherever ported 4U code writes T+0x54+2k (or em089_tar_set_part next to 0x8c69b8 calls).
- Arc state: rebuilt with `python3 tools/build_em089_arc.py --cmdtbl gog`, safe to install (works without the
  module change: tar shows Solid). Backup of the previous arc: none kept in the project.
- Next step: in-game test. Expect tar visible (black, matte Solid) on head, chest, arms, tail; log line
  "gogport: em089 tar spawn: N materials, 5 tar" once wired. If tar is still missing, test TAR_LIFT 6.0.
- [x] 4. Fogged/washed-out body (user test 2026-10-17). Cause (C, files): the 'solid' template (em004_00 mat 0)
  is an UNLIT GU material (fEmissionColor 1, fDiffuseColor 0, fSpecularColor 0, no spec texture), so body, wing,
  tail and spear rendered flat (no lighting), which the fog greys out. Not the RS state or the baked constants
  (no body material has an animation). Fix: 'solid' = em030_00 mat 0 (lit, no normal map, emission 0, diffuse 0.9,
  spec 0.5, FAlbedoMapColorOnly); 'unlit' = em004 mat 0 kept for 4U-emissive materials (eye: 4U emission 1, diffuse
  0; chosen from the 4U CBMaterialStd). Also tSpecularMap now = generated '<BM>+A' textures (BM alpha in RGB,
  alpha 255, as GU's em001_00_BM+A), not the BM itself (which made specular follow the albedo colour).
  mrl_check: 12/12 OK (also picks the closest template when words match, fixing the "no template" reports).
  Arc rebuilt (845 entries, +5 '+A' textures), em089_files.inc byte-identical, TAR_LIFT 8.0 kept.
- [~] 5. "Tar not animated" (user test). Static RE of the GU advance path (C): material vt slot 8 = 0xb0ffc4 ->
  0xb0ea4c: frame += mat+0x20 (speed, ctor 0xb0c568 sets 1.0) * dt, loop = entry flags bit 0, tracks applied via
  mat vt slot 22. Called only from unit virtual 0x88f45c (uFestaEnemy slot 24, not overridden) for materials with
  an animation set, gated by byte this+0x168 = !(this+0x1404 bit 13), rewritten every frame by enemy code
  0x71fd4; the only setter of bit 13 (0x723a4) is called from a non-enemy class (0x1068724), so for em089 the
  gate should be open. Block format, play, indices: verified (log slot0 4 / 1 = Liq_to_Sol / Liquid). Cause not
  pinned statically. Added to em089_tar.c (em089_tar_update -> tar_advance): if a tar material's slot-0 frame did
  not move since the last call although it should, call 0xb0ffc4(mat, this+0x1c) ourselves; log every ~10 s:
  "em089 tar anim: on <this+0x168> flags1404 dt speed part0 anim frame" and "calls N forced M". Module builds
  (`GOG_MOD_ROOT=/tmp/x python3 module/build.py`, 60764 B), no data relocs, em089_files.inc identical.
  Also note: the visible 4U state difference is partly the dropped fMaterialStdDiffuse.w (Solid 0 -> Liquid 0.85
  -> Gas 1; 4U LUT term, no GU equivalent mapped), so Solid vs Liquid in GU differ only in gloss, tint and the
  slow v scroll (1 tile per 250 frames). Next: read the two log lines; forced > 0 = engine was not advancing.

## Tar look (tar-look agent)
Status 2026-10-18 (owns tools/mrl_build.py, mrl_anim.py, mrl_check.py, material parts of mod4u2gu.py,
module/em089_tar.[ch]; scratch scripts tl_*.py in the session scratchpad).
- [x] 1. Visible GU tracks (survey of every animated material in nativeNX/arc/enemy, 132 materials): CBMaterial
  fDiffuseColor (182 tracks; 4-float kind 0x11 = rgb + fTransparency at f3), fTransparency (150), $Globals
  fConstantColor (97), CBMaterial fUVTransform (77; v/u scroll, e.g. em071_00 mat 2 BSSolid v 0 -> -1 / 200 f,
  em013_02 mat 5 BSSolid normal-mapped, ems007 face flipbook), fEmissionColor (76), fAlbedoColor (67),
  fSpecularColor (36), fUVTransform2 (20), fReflectiveColor (20), fAlbedoBlendColor, tAlbedoMap swap, distortion.
  Every GU monster material (templates included) has FUVTransformPrimary = FUVTransformOffset and FUVAlbedoMap /
  FUVNormalMap / FUVSpecularMap = FUVPrimary, so fUVTransform scrolls albedo + normal + specular together.
- [x] Cause of the flat look (C, data of both games): 4U fMaterialStdDiffuse.w is the material ALPHA, and the tar
  is ALPHA-TESTED. Proof: (a) Capcom's own 3DS -> GU conversions write the 3DS diffuse rgba as ONE 4-float track at
  CBMaterial f0 = fDiffuseColor rgb + fTransparency (em025_00 / em079_04 BSSolid NM parts: w 0 -> 1 in 30 f); (b)
  MRL entry w7 has the same layout in both games: bits 16-19 = RSMeshBias N (GU 72/72 B12 etc.), bit 24 = alpha
  test (GU 0x8d.. BSSolid+FTransparencyAlpha vs 0x8c.. opaque), bits 8-15 = alpha reference; 4U tar w7 0x8595/9a/
  9c4b00 = alpha test, ref 75 (0.294), 4U wing 0x859c2800 = ref 40, body 0x8482.. = none; (c) tar CBMaterialStd
  bMaterialStdVertexAlpha = 1 (tar only) and the tar vertices' N.w byte = 0 / 63 / 95 (/127) while every other
  mesh has 127 = per-vertex alpha. So 4U draws a tar texel iff BM.a * vtx.a * diffuse.w > 0.294. The w differs
  per material and state: head Solid 0 -> 0.025 (hidden), chest Solid 0.9, arms Solid 1.0, tail Solid 1.0 (its
  group g14 is hidden in steady Solid anyway); Liquid head 0.85, chest 0.7 -> 0.8 -> 0.9 -> 0.7 (500 f pulse),
  arms 0.74, tail 0.89; Gas 0.75..1. In the vtx.a 0.5 zones (most of head, tail, back) only the drip streaks of
  the 04_BM alpha survive (head Liquid: BM.a > 0.69 = 17 % of texels) and they scroll down with fUVTransform v
  (1 tile / 300 f head + arms Liquid, 500 f chest, 250 f tail; Gas 200 / 250 / 120 / 150 f) = the flow; the
  0.75 zones (arms, chest front) are nearly solid; edges (vtx.a 0) are cut; transitions grow / recede the drips.
  GU had all of this dropped (opaque template, no w track).
- [x] 2./3. Re-target (C, static): 4U diffuse rgba -> GU CBMaterial.fDiffuseColor 4-float track + fTransparency
  1-float track (Capcom's mapping, mrl_anim.TRACK_MAP); albedo -> fAlbedoColor, specular rgb*w -> fSpecularColor
  (unchanged); fUVTransform v offset NEGATED (Capcom's rule, proven on 4U em032 / GU em027_00 mat 42b876fc and
  4U em011 / GU em032_00 mat 6eae2464: the previous build scrolled the tar UPWARD). Same frames / keys / speeds.
  Tar template 'tar' = GU em082_04 mat 4 'XfBAN__EW_1__m52_far' (same Capcom 'XfBAN__EW_1' preset name as the
  4U tar; BSSolid + FTransparencyAlpha + FAlbedoMap + FBumpNormalMap, IASkinTBNLA2wt; other features = old
  solid_nm em001 mat 2; template constants kept: fShininess 50, fFresnelSchlick 0.9, fReflectiveColor 0.1).
  w7 alpha test ref 75 + bias nibble (5/10/12) from the 4U w7 (mrl_build 'alpha_ref' / 'bias'). Vertex alpha:
  each tar mesh split by triangle mean vtx.a (mod4u2gu.VALPHA_CLASSES: [0.375, 0.625) -> 0.5, >= 0.625 -> 0.75,
  below dropped = never drawn by 4U in Liquid) into '<name>_va50' / '_va75' meshes + materials (same type mNN,
  w scaled by the class) -> em089_00 has 15 materials (GU material array is allocated per model, 0x88eff8:
  count * 4, no fixed cap; largest GU monster model has 10, cm100_000 16, stages 96). No baked texture layer
  needed: the 4U look is reproduced by the same alpha test on the same texture (step 3 not applicable).
- [x] em089_tar.c: last-frame check per material index (TAR_MATS 24) instead of per part; with 2 materials per
  part the per-part value made the second material look stalled -> advanced twice per frame.
- [x] Validation: mrl_check 15/15 OK (tar: w7 alpha-test 1 ref 75 bias = RS state; constants changed only
  fAlbedoColor / fSpecularColor / fDiffuseColor / fTransparency; 9 anim entries, cb words valid); built anim
  blocks decoded (tracks above, fTransparency = w * class); MOD: 65 meshes, 15 materials, 36091 indices, meshIndex
  unique, mod4u2gu.check positions / weights / UVs as before; convert() without valpha is byte-identical to the
  previous arc MOD (regression). Coverage of the 04_BM alpha test per class (mip 0 / 4): head va50 Liquid 17 % /
  17 %, va75 100 %, arms va75 Liquid 95 % / 92 %, chest va50 Liquid 5 -> 35 % (pulse), tail va50 35 % / 25 %,
  Gas va50 69 %. Offline texture-space preview: scratchpad tl_preview.png. Arc rebuilt twice (ARC LOCK taken and
  released); only enemy\em089\em089_00\mod\em089_00 MRL + MOD changed, em089_files.inc byte-identical.
- [x] Follow-up 2026-10-18 ~00:50 (coordinator: fix the fidelity deviations). Arc rebuilt under the ARC LOCK
  (released); vs the pre-task arc only em089_00 MRL + MOD differ; em089_files.inc byte-identical; mrl_check
  15/15 + 1 + 1 OK; module compiles, em089_tar.c clean with -Wall -Wextra.
  (a) Wing (4U 'XfBA_E1__m50_wing', type 50): 4U w7 0x859c2800 = alpha test ref 40. New template 'solid_at' = GU
  em058_00 mat 5 'XfBAN__E0__m52_face_d' (BSSolid + FTransparencyAlpha + FAlbedoMap, IASkinTB2wt; else = 'solid'
  em030 mat 0). Small / SmalltoLarge / LargetoSmall / Large converted (fDiffuseColor + fTransparency: 0.165 <->
  1.0 in 30 f), 'Small' autoplays = 4U spawn (slot 39 [0x8ba04c] plays T+0x90 = Small; name table 0xff6fa4).
  02_BM alpha: 10486 texels 0, 39534 = 255: Small shows only the opaque membrane core, Large the whole torn
  membrane; the alpha-0 holes, drawn until now, are cut in both (preview scratchpad tl_wing.png). Driver: 4U
  0x8c64b8 (called by slot 77 [0x8c9aa0], "not ported" in em089_act.c) ported as em089_wing_update(self) in
  em089_tar.c: motion 0x108 frame 148 -> SmalltoLarge + W+0x7814 |= 0x20000; 0x10b frame 128, 0x30b / 0x30c
  frame 30 -> LargetoSmall + clear; other motions: steady Large -> LargetoSmall when rec+0x1ba (4U W+0x1c8) == 0
  and not dead (0x94d7a8); finished transitions continue to Large / Small. Returns EM089_WING_SET / _CLEAR for
  the caller's state word (bit 17 = emd row: group 102 shown while set). NEEDS WIRING by the main agent: call it
  each frame from em089_slot77 (em089_act.c, after motion_mode) and apply the bit to F_TAR_WORD + tar_vis.
  Break / visibility rows untouched (wing groups 0 / 8 / 15 keep their rows; break groups 28-31 are body).
  (b) w7 depth-bias nibble = the 4U w7 for every material (body 1, eye 2, wing 12, lights 12, spear 0, tail /
  gekiryusou models 0) = their RS states, as in every GU MRL (the template values 0 / 4 were inconsistent).
  (c) Mesh data1 alpha byte (RevilLib 'AlphaType'): GU uses it only in the draw-list SORT KEY (C, 0x893978..
  0x893a94: key = pass | (byte [| depth << 12]) << 5; no shader use) -> 4U values restored on the tar meshes
  (1, head g15 / g34: 2, chest g4: 0); the 2026-10-17 visibility fix was the lift (arms appeared at TAR_LIFT 20).
  (d) Audit of every em089 material vs 4U (w7 alpha test, static w, tracks): body (bias 1), eye (2), spear on the
  body model (0), em089_tail 'm00_tail' and em089_gekiryusou 'm00_gekiryusou_b' (0): no alpha test, w 1, no
  animation -> only the bias nibble. Lights 'm06_add' (BSAddAlpha, type 6, no alpha test): 8 Light_* entries
  (emission 1 <-> 2 + w 0 <-> 1) now converted ($Globals.fEmissionColor 4-float, Capcom's GU track type, +
  diffuse/fTransparency), not autoplayed (slot 39 stops them: play index -1); the variables they drive start at
  the 4U statics (emission 2, diffuse 0, w 1). em089_light_play(self, k) = 4U 0x8c62c0 (k = 4U name-table index
  0xff6fb4, Light_Gas_Bress .. Light_Tail_Attack02) for whoever ports the callers (0x8c6300 / slot 47 lights,
  0x8c8b9c ..); the light meshes (groups 2/5/17/18/19) are drawn only with state-word bits 18-22 anyway. Tar:
  per-material w differences confirmed and kept (see above). Tracks dropped anywhere: none any more.
- Deviations left: (1) per-vertex alpha quantised per triangle (2 classes; 4U interpolates per pixel), edge
  triangles (mean vtx.a < 0.375) dropped; (2) GU lighting (shininess / fresnel / env of the templates) instead of
  4U's LUTs; specular colour = 4U rgb * w; (3) 4U diffuse rgb 0.8 now drives GU fDiffuseColor on tar / wing
  (template 1.0 / 0.9); (4) the wing's 4U extend map (05_BM, sphere / UV-extend reflection) still unused; (5)
  wing Large / lights only once em089_wing_update / em089_light_play are wired (without: wing Small, lights off).
- Expect in game: head / chest tar = black glossy drip streaks crawling DOWN (head 1 tile per 10 s), denser rims;
  arms nearly solid black, matte in Solid; head tar gone in Solid (4U); transitions = drips growing / receding
  over 200 f; Gas = denser streaks with cyan highlights. If NO tar shows at all: the alpha test kills it -> first
  check the log line "em089 tar spawn: 15 materials, 10 tar", then try alpha_ref 0 in build_em089_arc.
  Wing: torn membrane with holes; small (opaque core only) until em089_wing_update is wired, then it spreads
  (30 f) from frame 148 of motion 0x108 and folds back on 0x10b / 0x30b / 0x30c or when the state class is 0.
- [x] STAGE materials DONE 2026-10-19 by the main agent (static; tar-look agent not resumed for this). build_mrl in
  tools/stage4u2gu.py now: picks the template by opaque/blended class + lit + alpha-test (animated templates allowed:
  every Fortress IANonSkinBC template selects the same FUVTransform* features, so UV anims work on any of them), then
  sets the 4U BS / DS / RS states (gu_state: 4U RSMeshCNBias4/8 -> RSMeshCN, GU has no CN+bias record), copies the 4U
  w7 bits 8-19 (alpha ref + bias nibble) and the BSSolid alpha-test bit 24, and converts the 4U anims with
  mrl_anim.gu_entries (4U loop + autoplay flags kept; anim blocks 16-aligned after the parameter blocks). Result: 16
  alpha-tested cards (kusari, pod, enkei01, komono00/04, happa02, syokudai00, rope00, 10_BM, ss03, ki01/02, kusa00)
  w7 0x8d9x8000, RSMeshCN where 4U is double-sided; torch fire a00_00/01/02 = BSAddAlpha DSZTest + 4x4 flipbook (16
  keys, 32 f, autoplay loop); water00 / sky03 / sky00 / bcloud / cloud / kumo01 animated. Rebuild diff: only MRLs
  changed (a00 4, a01 3, a02 1, m28d 3), no entry added/removed. Not done: 4U material constants (albedo colour etc.)
  still come from the template; vertex alpha not checked. Original notes: Test 2: grass drawn as
  opaque squares, camp torch fire wrong / not animated, big flat black one-sided triangles in the camp. Allowed: the
  material parts of tools/stage4u2gu.py (gu_templates / pick_template / build_mrl), rebuild with
  `python3 -I tools/stage4u2gu.py alias` (no ARC LOCK needed: stage arcs); other parts = arena-4 agent.
  Found so far (C, data; audit script scratchpad tl_stage_audit.py -> tl_stage_audit.txt, 128 materials):
  - build_mrl copies a Fortress template entry + block per material (pick_template: blend / lit / RS similarity,
    templates WITH anims skipped), sets only tAlbedoMap (every other texture slot -> 0), keeps the TEMPLATE's RS
    state and w7, never converts 4U anim blocks, never sets alpha test: so 4U's alpha-tested materials are opaque.
  - 4U alpha-tested = every 'XfBAW_1__' / 'XfBAW_3__' BSSolid material, w7 0x859x8000 = alpha test ref 128:
    a00 kusari, pod (x3, one RSMeshCNBias4, one RSMeshBias8), enkei01, komono04, happa02 (leaves), syokudai00
    (torch stand), komono00, rope00, 10_BM (RSMeshCN), ss03; a01 ki01 / ki02 (trees, RSMeshCN), kusa00 (GRASS,
    RSMeshCNBias8, 6 meshes), prop c04 ki02 (RSMeshCN). -> cause of (a) and very likely of (c): alpha cards drawn
    opaque show their black transparent texels, and RSMeshCN (cull none, double-sided) materials got culling
    templates, so they vanish from the back (a03 XfB_W_0__m00_142 is RSMeshCN without alpha test too).
  - Torch fire (b) = props m19a00d-a00_00/_01/_02: 'XfBAW_11__m00_1' (vertex alpha 1) and 'XfBAW_10__m00_2',
    BSAddAlpha, DSZTest, texture honoo00_BM, anim 'f05cf980' 32 frames fUVTransform (flipbook/scroll) -> needs an
    additive template + the converted UV track (mrl_anim TRACK_MAP: v negated) + autoplay (4U f05cf980 = default
    anim name, check its flags). Other 4U UV anims: a00 water00 (1000 f), sky03 (3500), bcloud x2 / cloud (350 /
    1500, BSBlendAlpha), a01 kumo01 (512), sky00 (3000): all dropped today.
  - BSBlendAlpha 'XfBAW_10/11' + 'XfBAN_W_10' (decals, clouds, jimen blends) have bMaterialStdVertexAlpha 1: GU stage
    vertices carry u8 VertexAlpha @23 (IANonSkinBC) -> keep a template that uses vertex alpha.
  Next steps: (1) list Fortress (dump/gu_stage) IANonSkinBC templates with FTransparencyAlpha / BSAddAlpha /
  BSBlendAlpha and their FUVTransform / vertex-alpha features and w7; (2) in build_mrl: set the 4U RS state
  (mrl_build.state_word), w7 bias + alpha ref from the 4U w7 (bit 24 -> FTransparencyAlpha template, ref 128),
  convert 4U anims with mrl_anim.gu_entries (cb words of the chosen template) + autoplay, keep other slots;
  (3) list the black-triangle meshes: camp = a00 m19a00d meshes of the AT1 / RSMeshCN materials above (verify with
  per-mesh normals / winding vs 4U); (4) rebuild alias, check, report. Nothing edited yet for this task.

## Quest 11491 (quest agent)
- [x] Cause found (static, v1.4 vs v1.0 main): quest start 0x5d74 state machine requests loc\quest\q%07d.arc
  (kind 2, p1 1, p2 = id from [[0x188ae38]+0xd68], set at accept 0x784ec8), finds it (0x152c68 @0x7560), then
  questData = arc entry [count-1] (0x3ba6dc) and questLink = arc entry [count-9] whose path contains "Link"
  (0x3ba840; v1.0 had [count-7] at 0x3b9e08). v1.4 quest arcs have 2 more entries between questLink and questData;
  ours (copied from the v1.0 layout, 15 entries) gave entry 6 = supp -> link null -> 0x3ade34 skips the whole
  quest setup (no +0x1324 monster list, quest+0xe0 = 0, no text pointers).
- [x] Fix: builder adds 2 filler GMDs after questLink (count-9 = questLink, asserted); stage.c gog_quest_id() = d68
  (until setup, cleared at 0x7608) else [[0x188ad90]+0xe0] (set at 0x3adf1c); main.c swap uses it; hook
  utf8_null_guard @0x7CA340 (build.py HOOKS) as safety net. Romfs currently = `--plain` build; module compiles.
- Next step: user installs module + romfs (--plain) and tests: expect log "quest_prep quest 11491 (obj 11491)
  id=18" then "quest_prep id=59 lr=3adcf8", Gogmazios spawns in the stage-23 jungle, abandon works. Then `python3 -I tools/build_gog_quest.py` (Fortress)
  and retest; if the Fortress still fails at once, compare with `--siege` and check the stage-path logs.

## Tar state machine (tar-machine agent)
Status 2026-10-17: ported, compiles (`GOG_MOD_ROOT=/tmp/x python3 module/build.py`, 56532 B, 0 warnings with
build.py's CFLAGS). Not tested in game. Code: module/em089_act.c "tar state machine" block; EM089_SIZE base + 0x90.
- [x] 4U logic (C, read from the code): parts 0 head, 7 chest, 2 l_arm, 3 r_arm, 6 tail (k 0..4); amount work+4*part,
  decay timer work+0x20+4*part, mode u16 work+0x54+2k. Slot 39: amounts 0, head/chest 130, modes head/chest Liquid,
  rest Solid, word W+0x7814 = 0x7c. 0x8c352c per frame: dead (cat 11/14, 12/255) -> amounts 0; amount > 0: timer -=
  dt, at <= 0 amount -= 2 (min 0), timer = 180; mode = <=100 Solid, <=160 Liquid, >160 Gas (0 = Solid); on change:
  hitzone row (Solid 0x936ea8 base row, Liquid 0x93415c alt row, Gas 4U table 0xff6fd4; rows head 0, chest 5, arms
  2/3, tail 4), 0x8c69b8 one-hot word bits (k / 5+k / 10+k), mode store (-> slot 50 animation). Chest Liquid alive:
  work+0xd4 += dt, > 210 -> event 0x2fcc50(203) (stub). 0x8c2518: while work+0xca (roar variant 2, never cleared)
  all parts = 255 every frame -> permanent Gas; also W+0x40c = 1.1/1.155 (stub). Amounts otherwise only grow via
  0x8b69f4 (attack windows, cap 159 = at most Liquid). No em089 code removes tar on hits/breaks (only callers of
  0x8c69b8: slot 39 and 0x8c352c; of 0x8b69f4: cat-7 attacks), so no onDamage path is needed.
- [x] Slot 50 bits: 0x8000 (head) / 0x10000 (tail) set when a transition to Solid ends (steady Solid), cleared
  while the part is not Solid: em089_tar_update now returns the "entered steady Solid" mask -> em089_tar_steady.
- [x] Visibility: the 14 emd cond-7 rows evaluated on the word -> bits this+0x110 (tar_vis, on word change, logged
  "em089 tar word"). Groups: g3 head (hidden steady Solid), g34 head (hidden Solid), g15 head (Gas only), g4 chest
  (Solid only), g22 chest (hidden Solid), g7 chest/back 409 verts (Gas only), g6 chest (no row, always), g9/g11 arms
  (no row, always), g14 tail 295 verts (hidden steady Solid), g13 body-material tail piece (shown tail Solid).
  Break/sever rows (g34, g13/14/19) taken as intact; bits 17-22 (eye/add glow, slot 47 lights) stay 0.
- [x] Hitzones: GU 0xbab88 / 0xbabb8 = 4U 0x936ea8 / 0x93415c (C, same bodies, rec+0x418 = W+0x460), guarded on
  *(this+0x75ec). Gas rows point at a module copy of 0xff6fd4 (GU row order assumed = 4U, S: same 10-byte stride).
- Spawn per 4U: head Liquid (g3 + g34), chest Liquid (only small g6 + g22; the big back/neck g7 needs Gas), arms
  Solid (g9, g11 always), tail Solid: g14 drawn only during Liq_to_Sol, then hidden (g13 shown). Head/chest decay
  130 -> 100 in 15 steps (first at frame 1, then every 180) ~ 84 s at 30 fps -> Solid: head g3/g34 hidden.
  Full-body Gas (g7 back, g14 tail, g15 head) only after the roar that sets work+0xca (cond 2 / 1/x variant 2).
- [x] Zero-damage report (HP stuck at 34 % for 5 min): hitzone switching checked statically, not the cause.
  GU 0xbab88 / 0xbabb8 / default init 0xbabf4 (8 rows, part i -> base row i, from 0xa4c4c) use 10-byte rows like
  4U (GU KO reader 0x9db54 takes byte 8 = 4U layout). The data block *(this+0x75ec) (setter 0x70a1c) has its tables
  at obj+0x70 / +0x74 = dttune blocks <- 4U etd words 7 / 8; dump/converted/em089/dttune.bin holds em089's 4U rows
  at 0x8f / 0xdf. Values: base (Solid) 22-23 cut / 23-27 impact, alt (Liquid) 35-45 / 35-45. Row 1 is 0 (as in 4U).
  KO byte 0 in every row (4U data). So the switching only swaps between nonzero rows of the same tables. With it
  skipped, every part keeps its base row (also nonzero). Next suspects: hits not registering (bodydata part / meat
  index fields, parts >= 8 -> vt+0x314) or a quest defence multiplier.
- [x] Diagnostics: spawn logs "em089 meat data / meat row i" (the 8 rows the damage code reads); slot 119 logs
  "em089 damage #n: -d -> hp" (first 20 drops, then every 5 % of max HP). Control build: GOG_DEFINES="TAR_NO_MEAT".
- Next step: in-game test; check the log lines "em089 tar word 7c", "tar part N -> mode M", "meat row", "damage",
  and that g14 hides after ~1 s (tail transition) and the head tar goes at ~84 s. Then port the W+0x40c and
  0x2fcc50(203) stubs.

## Battlequarters collision (collision agent)
Status 2026-10-17: SBC layout decoded for both games (all 976 GU SBC files of the base RomFS parse to the byte;
corpus extracted with a scratch script, not in repo). 4U and GU carry the SAME blocks (polygon AABBs, BVHC, tris,
verts, groups, polygon records, grco) in a different ORDER, with different header/part-record layouts.
- [x] tools/sbc.py: parse both, write GU (976/976 GU files byte-identical), AABB + grid builders byte-exact on both
  corpora (GU 976/976 AABB, 1510/1511 grids; 4U 529/529, 924/924). 4U m19a03d-a-w00-a00-shell converted == Capcom's
  own GU m26d-a-w00-a00-shell except 1 attribute byte.
- [x] map_com m28.arc rebuilt by `python3 tools/stage4u2gu.py alias`: 14 SBC entries replaced (a00 <- m19a00d,
  a01 <- m19a01d, a02 <- m19a03d; a00 cam stays Fortress's), all other 559 entries unchanged.
- [x] SIS decoded (tools/sis.py, same format both games, 194 GU + 124 4U files round-trip): 4 sections points /
  exits (target area) / arrivals (source area, 0xff = quest start) / spheres. stage4u2gu.py convert_sis(): m19 info
  copied with areas remapped (4U 3 -> 2; 4U a02's passages -> variant-1 link a01 <-> a02).
- [x] build_gog_quest.py --bq: stage 26, camp start, questPlus_0000, setEmMain area 2 (angle 0, 633.5, 0, 1510.8).
- [x] map_com m28.arc rebuilt with SIS (in module/romfs); module compiles with and without GOG_DEFINES=GOG_STAGE_ALIAS;
  --hp-table / --icon options added. Nav (relation floors) NOT converted (notes/stage.md "Still Fortress data").
- Next step (main agent, recipe in notes/stage.md section 10): `python3 -I tools/build_gog_quest.py --bq`, build with
  GOG_DEFINES=GOG_STAGE_ALIAS, install, test camp start / exits / Gogmazios in the arena.

## Monster data (data agent)
Details: notes/data.md. Build: `python3 tools/build_em089_arc.py --cmdtbl gog` (em089_files.inc must stay identical).
- [x] Hurt volumes = **bodydata (field 30, BDD)**: 44-B records {u16 bone A, u16 bone B, u16 shape (0 sphere,
  1 capsule on A, 2 capsule A -> B), hitzone/part u16s, f32 radius, off1, off2} (C: GU Rathian/Kushala files).
  hitsize (28) = attack volumes, cambodydata (31) = camera; 11/35/40-50 hold no volumes (hagi = 346-B tables).
- [x] FIX 2026-10-17: emdata4u.bodydata forced bone B = 0xFFFF on every record -> em089's 27 two-bone capsules
  (neck, wings, legs, tail) collapsed onto bone A. GU keeps B on shape 2 (179 of 185 such records in 32 shared
  monsters); selftest Kushala 98.8 -> 99.7 %, Rathian 98.2 -> 98.7 %. Needs an in-game check.
- [x] Donor bone remap (13->11, 130->200, ...) only touched Kushala's placeholder BDD, which is replaced by the
  converted file: no Kushala volume data is left in the arc. 4U bone IDs = model IDs (all asserted present).
- [~] hitsize bone 13 -> 201 (absent bone, guess). [ ] dtbparts (34) still Kushala's. [ ] tar state XFS states.
- [x] HUD icon (UI 141) + name (GMD entry 105 via hook name_index): tools/ui_em089.py, module romfs, 5 languages.
- [x] Damage path (static, C): player hit code (0x171b70, 0x1733b8, 0x174208, 0x175300, 0x17777c) calls
  vt+0x2f8(monster, hit, dmg) (HP) then 0x9d6f8(monster, **BDD record byte +8**, dmg, kind) = per-PART damage
  counters rec+0x488+2*part (x rec+0x388, parts >= 8 -> vt+0x310). So "part" = bodydata u16 @8; @6 = hitzone
  row. Same layout and numbering in 4U and GU (Kushala 4U vs GU records identical): no remap needed.
  em089 parts: 0 head, 1 neck/chest (+ bone-200 tar sac, row 1 = all 0), 2/3 wings, 4 body/arms, 5 hind legs,
  6 tail, 7 bone 205. Tonight's "only parts 5/6" = the collapsed-capsule arc (head/neck/wing/arm/body capsules
  broken, only leg spheres + tail left) -> retest with the current arc.
- [x] HP: dttune obj+0x64 = base HP (= 4U etd +0x10; Kushala 4200 in both games). em089 = 17500 (4U value).
  53375 = 17500 x 3.05 (quest HP table 91, Kushala G4's). Faithful to 4U's ratio (Gog = 4.17 x Kushala).
  Damage 1-42/hit with rate 0.75 (table 93) + hitzones 22-45 = weapon dependent, data side OK.
- [x] PART HP / BREAKS were Kushala's in **dttune** (not dtbparts): dttune obj+0x68 = 8 x 10 B per-part table
  {u16 part HP, u8 levels, u8, u8, u8, u16 next-level HP / 0xffff, u16 kind} = 4U etd word 5 verbatim (29/40
  monsters exact, 98.6 % bytes; dt_convert skipped it because etd word 5 = 0xa0 sat below its pointer filter).
  Now converted (tools/dt_convert.py, unicorn venv -> dump/converted/em089/dttune.bin, arc rebuilt, IDs same).
  em089: head 650, p1 600/1200, wings 750+750, p4 800, legs 850, tail 750/1500, p7 600. Also 0x7c <- etd word 10
  row 0 (thresholds 600/2050/3300/5000; GU rows = header byte +0x0a, donor count 1 kept). Validation: Teostra
  55.8 -> 57.6 %, Rathian 33.8 -> 35.5 %, Kushala self 99.5 %.
- [~] dtbparts (field 34, DTP) = enemy+0x75f0 (setter 0x70a4c, loader slot L+0x9c, L = enemy+0x764c). Framework
  readers (39 sites < 0xcef000): heap0 obj+0x64 4-B records {?, LR count, HR count, ?} checked against 0x9d428(this,
  k) (b25a0); obj+0x6c 12-B records by type byte (type 0 -> 0xaba9c(this, i, 1, 0) -> rec+0x5d38, type 1 -> mode 2;
  f32 +4 = 600/200 Kushala, 440/200 Rathian; looks like rage/fatigue-type gauges, NOT part breaks); counts +0x8c..
  +0x95, f32 +0xc0, u32 +0xcc. The 12 five-byte records (obj+0x80) are read only by monster class code (0xcef000+),
  i.e. our uEm089 decides. No 4U counterpart (vote 4/40). Kept Kushala's: elder-dragon tuning, consistent.
- [ ] Breaking in game needs class code (porter/D): framework adds part damage (rec+0x488+2*part); the monster
  class compares with the dttune part table and applies XFS states 2-4/7-9 (break) and 5/10 (sever).
- [~] Shells (field 25, ARCS 0x73850d05 = list of 792 (hash, type) refs) = Kushala's 6 projectile families
  shell\em\em024_00_shellNN\: XFS 0x4aa69872 (shell def), HDS 0x4eb68cee (hit data), HTS (hit volumes), FUP
  0x496f8f22 (283 small param blocks: sh/hit/snd), XFS 0x1eb12c38 (94 effect refs). **4U em089 has no shell
  files** (em089.arc: model/mot/cmd/cam/CTC/effects/sounds only; projectiles are code-driven via id helpers), so
  nothing to convert: Gogmazios' tar shots/beam must be authored as GU shells from Kushala's templates (or done in
  code with attack volumes). Effects: 25 EFL (v0x30111104 vs GU 0x20120306), EAN, MEF, 6 textures, 1 effect MOD/MRL
  in em089.arc: version differs -> re-author with GU effects; the textures/model convert with our tools.

## Tar shells (shell agent)
Status 2026-10-17 (shell agent; owns module/em089_shell.c, shell parts of em089_act.c / game.h). Code DONE (untested in game).
4U findings (complete, verified in the disassembly):
- uShell050 vtable 0xe6e86c: slot 22 = 0xc8e938 (init, first frame), 23 = 0xc8f028 (per frame), 24 = 0xc8fc18
  (b 0x9ab16c = kill: +0xf1 = 3), 1 = 0xc8fd40 dtor. (0xc90a3c in the old notes = uShell051's dtor, not ours.)
- Spawner 0x8c9dd4(this, r1 = arg, s0 = frame, s1 = spread): at motion frame s0 * 2 (motionCheck kind 0):
  r = LCG(action serial this+0x73e8) iterated work+0xcd + 1 times (0x2b02c0: x = s*176 (s=0 -> 1), x mod 65363,
  u16), target = random point in a disk of radius spread * (r & 0xff) / 255 at angle (r & 0xff00) around target
  slot 0 (W+536 = rec+464) (0x934f7c / 0xaad008); posts kind 4 (5 when work+0xca), param+0 = arg (joint, 255 =
  owner matrix), offset (0, -50, 0); work+0xcd++.
- Drip helper 0x8b8e28(this, r1 = joint, r2 = tar part k < 5, r3 = mask of tar modes (bit m: work+0x54+2k == m),
  s0 = frame): at frame s0 * 2: kind 0 (1 when work+0xca); if work+0xec <= 3 and r % 500 == 0: kind 6 (7),
  work+0xec++, work+0xed = 1; if W+0x797e in {1, 2} and work+0xca and kind != 7: kind 8. Offset (0, -50, 0);
  work+0xcd++. 243 call sites in the em089 handlers.
- Init (slot 22): kind >= 10 or no owner -> dead. pos = joint (0x930894(owner, joint) matrix row 3; joint 255 =
  owner+0xb0 matrix) + offset rotated by the owner yaw; vel = table[kind] rotated by (x +0x110, y = owner yaw,
  z +0x118); accel = table[kind] rotated by yaw. vel: kinds 2/3 (0, 15, 20), others 0. accel y: kinds 0/1/6-9
  -0.2, 2/3 -1.4, 4/5 -0.7. Kinds 4/5: ballistic to the target point: horizontal distance capped at 2750, flight
  time 80 frames, vy = (dy - 0.5 a t^2) / t. Lifetime +0x26c = 480 frames. Attack: 0x9ab120(shell, inline 40-B
  attack records 0x1031990 [kind -> 0,1,2,3,2,3,0,1,1,1], 2, [sp] 23 (kinds 0/2/4/6) or 16 (others), 2).
  Records 0/2 = power 5 (0x3f0005), 1/3 = power 40 (0x3f0028): the shell's own attack, NOT em089 attackdata.
  Sound 215 at spawn for kinds 2-5. Effect: group 65 element 2 (kinds 0,1,6-9) / 14 (kinds 2-5), attached.
  Ground shadow marker 0xc07d54 (size 1.0) at the ground point below the spawn.
- Per frame (slot 23): owner gone -> kill; lifetime timerDown -> dead; prev = pos; pos += vel*dt; vel +=
  accel*dt (0x9ab0a0); ray prev -> pos against the map (0x2b96e4, mask 48); hit: pos = hit point, dead, impact
  sound 0xd8 (drips) / 0xd9 (shots), and on GROUND (hit flags & 34 == 0) a uShell051 (generic ground effect
  shell, type 51) with subtype 1 (kinds 0, 2, 4), 16 (kind 6), 6 (1, 3, 5), 17 (7), 19 (8), 20 (9) = the tar
  splash / puddle. Kinds 2-5 orient along the velocity.
GU findings:
- Shell table 0x1763448 (only user besides the request: 0x48c388): 412 rows, NO free row. Ids are hard-limited by
  the manager layout (mgr+0x1c + id*4 resources, mgr+0x68c + id*64 users, mgr+0x6d8c 144 live).
- 0x48c388(mgr, owner, id) registers owner as a user of id and, if mgr+0x1c+id*4 is empty, fills it with
  0x152960(_, row[2] file id) (= our file_id hook: our own file IDs work). Kushala does it for ids 175..180
  (0xdf2108; families shell\em\em024_00_shellNN, files 0x8a02..0x8a07).
- Request 0x48c4f0(mgr, param, flag, 0): owner param+0xc alive, id param+4 < 412, < 144 live, param DTI id ==
  row[1] DTI id, resource != 0; shell = row[0]->newInstance; 0x4a1c84(shell, res) with addref 0x887648 /
  release 0x887660; shell vt+0x13c(param) must return 1; 0xc067ec(*0x2126f48, 18 | flag & 1, shell, 0, 0)
  (unit add); 0x48c6c8(mgr, shell) (live list).
- uShell / uShellEnemy (GU): object vtable 0x175b260+8 (83 slots), DTI 0x188ee88 (parent uShell, 0x15d0 B), ctor
  0x43b3f8, dtor 0x43b488 (uShell dtor 0x4a18b4 deletes the param +0x136c and releases the resource +0x1384).
  Slots: 9 move (0x4a2304: kill if the owner is gone), 11 attack-slot update, 16 kill (0x4a247c: 3 attack slots
  this+0x13a8 + i*184 off, unit state +0xc = 3), 79 setup(param) (0x43b4bc: uShell setup 0x4a24f8 + owner+0x1052
  == 1), 80 arm attack (0x43b51c -> 0x4a2790(this, slot, HDS index, -1, 31, 2, 0xffff) -> 0x168e98 with the
  resource's HDS entry (56 B, 4U-record-like) and HTS volumes; owner rec+900 scales the power). Position this+0x40,
  angles this+0xfe8 (u32 x3), dt this+28, area this+0x1054. A NULL resource is accepted by the setup (no hits /
  effects). Resource = family XFS 0x4aa69872 -> per-kind entries (param+8) + family-wide HDS / HTS / EFL lists.
- Map segment test 0x1838fc(*0x21270e0, from, to, area, out, info, mask, flags) = 4U 0x2b96e4 (EmBase classes);
  ground height 0x183ad0 = 4U 0x2bad24.
Status (2026-10-17): DONE, builds with zero warnings (not tested in game):
- module/em089_shell.c (+ .h): class uShellEm089 (DTI registered lazily at the first blob), our request (no shell
  table row needed), 4U init / per-frame translated (joint spawn - 50, kind velocity / gravity tables, kind 4/5
  ballistic lob, 480-frame lifetime, integration, segment test mask 48, impact -> kill, velocity orientation).
  Hits: attack slot 0 armed with HDS entry {0,1,2,3,2,3,0,1,1,1}[kind] of resource EM089_SHELL_FILE (default
  Kushala family 00, 0x8a02, loaded from our arc: powers 80/100/80/100 instead of 4U 5/40/5/40). Logs: spawn,
  impact (ground / wall), timeout, drops. Not ported: effects, sounds, ground marker, the uShell051 splash.
- em089_act.c: tar_shot (= 0x8c9dd4, frames x2, 4U rand on the action serial), tar_drip / tar_drips (= 0x8b8e28),
  F_SHELL_N / F_SHELL_RARE / F_SHELL_ED fields (F_END = 0x98 = EM089_SIZE), F_SHELL_N reset in slot 47 (0x8c8bec).
  7/138 (7 shots) and 7/142 (13 shots + 12 drips) wired in 4U call order. build.py: 'em089_shell.c' added.
Data needs (for the data agent): an em089 shell family to replace Kushala's (set EM089_SHELL_FILE to its file ID):
  copy shell\em\em024_00_shell00 -> shell\em\em089_00_shell00 (XFS em089_00_00 0x4aa69872 with >= 1 entry, its
  sh/hit/ef/snd FUPs, HDS, HTS); HDS = 4 entries from the 4U records (0x1031990 + 40*i, i = 0..3; 0/2 power 5,
  1/3 power 40; bytes in the 4U dump), HTS = 1 sphere (4U radius not decoded yet: 0x9a9624 setup). Effects per
  kind: 4U effect group 65 element 2 (drips, kinds 0/1/6-9) and element 14 (shots, kinds 2-5) = em089 EFL of
  group 65 in em089.arc (which em089_0NN.efl is group 65: to be confirmed by the data agent).
- Drips: all 244 4U sites (243 bl + 1 tail call in 7/25) placed in the 44 handlers, per step / variant branch, in
  4U order (branchy handlers checked in the raw disassembly: 2/33, 7/19, 7/26, 7/32, 7/107, 7/118, 7/136, 2/1-2/2).
  Frames are 4U values (x2 inside tar_drip, as 0x8b8e28 does). Build: 94208 B, zero warnings.
To verify in game (log lines "gogport: em089 shell ..."): spawn positions (joint ids = 4U ids in the converted
  model), impacts (mask 48 / flags of the segment test), hits (owner+0x1052 must be 1 for the uShellEnemy setup,
  else "setup failed"), that the unit line 18 runs our slot 9 every frame.
Next step: data agent's em089 shell family (above), then effects (EFL group 65) and the uShell051 splash.
**BUG to fix in em089_shell.c (blob class; sound agent's file now, I did not touch it):** GU builds a bone-1001
  hit volume as a CAPSULE from this+0x40 to this+0x1000 for char-type owners (GU 0x16e46c..0x16e5f8, shape not
  checked; EmBase classes write +0x1000 themselves, e.g. 0x3fe7b4). The blob never writes this+0x1000, so its
  capsule runs from the blob to wherever +0x1000 is (0,0,0 after the ctor's zeroing?). Fix: in shell_move after the
  integration (and in shell_setup) copy S_PREV (4U +0x120 = previous position, the swept sphere) to this+0x1000..
  +0x1008 (pos itself for a plain sphere).

## Attack shells uShell016 (shell agent)
Status 2026-10-18: code + data DONE, builds (99464 B, 0 warnings), not tested in game. Behaviour agent wires the
call sites (below).
- module/em089_shell016.c / .h: class uShellEm089Atk (uShellEnemy-derived, own request as em089_shell.c),
  `em089_shell016_post(void *self, uint32_t subtype, const float *pos)` (pos = optional joint-space offset; 0 = the
  4U value). Ported from 4U uShell016 (vtable 0xe6d98c, ctor 0xc6f900, init 0xc69ddc, per frame 0xc6ac64, common
  tail 0xc6e8d4): joint 3, length 10000, angles x = P+26 (+ owner x angle rec+0x50 except 36), y = P+28 (+ yaw
  except 36 / 53); capsule second point = joint + M*offset, point = joint + M*rotX(x)(offset + (0,0,len)) (53 also
  rotY(y) and flattened to the second point's height), M = joint matrix GU 0xc1660 (= 4U 0x930894); 36 / 53 placed
  once, 37 / 41 / 51 / 52 / 54-56 every frame; life (0x102bbbc) 120 / 128 / 150 / 260 / 680 / 139 frames counted
  with the owner's motion step (4U 0x94460c owner+668 * dt; GU: rec+0x398 motion speed * this+28, S-); ends when
  the owner's motion changes or the life is out; angles from the segment. Capsule in GU = this+0x40 .. this+0x1000.
- Per-site arguments (all em089 sites, extracted from the 4U stack setup, scratchpad s16sites2.py): P = {joint 3,
  offset (0,0,0) for 36 / 37 / 53, (0,-50,130) for the others, byte 0, x 0x1556 (36) / 0x1c00 (37) / 0 (53) /
  0x1800 (others), y 0xf400 (53) / 0}, len 10000, [sp] u16 0xffff (7/146: literal 0x8c2408), floats 0.
- Hit data (C): 4U records 0x102b370 + 96 + 40*i, i = 31 / 32 / 36 / 40 / 41 / 42 (subtypes 36+53 / 37 / 41 / 51 /
  52+55+56 / 54) -> HDS entries 4..9 of em089_00_shell00 (power 80 / 80 / 80 / 80 / 20 / 80, type 2, 41: type 1;
  s16 +2 = 120..680 = the life values); volumes 4U byte 0x19 = 18 / 20 / 22 (capsule, bone 1001, radius 330 / 70 /
  30) -> HTS groups 1..3 (byte 0x19 remapped). Built by tools/build_em089_arc.py shell_hds / shell_hts (S016_*),
  arc rebuilt under the ARC LOCK with --cmdtbl gog: only _hitdata / _hitsize changed (1085 entries, none added /
  removed), em089_files.inc byte-identical. Blob entries 0..3 / group 0 unchanged.
- For the effects agent (hook `em089_shell016_fx(shell, owner, subtype, efx_id)`): called at init with the 4U
  uEffect002 id (0xc0b470): 36 / 53 -> 48, 37 -> 50, 41 / 52 / 54 / 55 / 56 -> 53, 51 -> 54; called AGAIN once when
  the life drops to <= 10 (end flare, 4U 0xc6cb88 / 0xc6dd34 / 0xc6e878, offset (0, -50, 130), mode 2): 41 / 54 and
  52 / 55 / 56 -> 53, 51 -> 54.
- [x] (2026-10-18 later) per-frame extras ported (C, from 0xc6c904 / 0xc6d250 / 0xc6e54c):
  - map test of the capsule (tip -> start, mask 16; GU 0x1838fc) into the hit point; timer +696 (41 / 52 / 54-56: 8,
    51: 4) counted down with the owner step;
  - 41 / 54: timer out + ground hit -> uShell051 15 at the hit point (y = ground height, GU 0x183ad0 = 4U 0x2bad24),
    timer 9999 (once);
  - 51: owner frame 242 + ground hit -> uShell051 3; owner frames 473 / 483 / 488 / 491 -> segment B -> A (mask 48)
    between owner-relative points (k_boom: x mirrored for motion 0x266, * speedFactor, rotated by the yaw, + owner
    position) -> uShell051 9 / 10 / 11 / 12 at the hit;
  - 52 / 55 / 56: first ground hit after the timer -> uShell051 13 and timer 171, then 14 every 24 / 25 / 26 (by
    subtype) owner frames while the beam hits the ground;
  - camera shakes 4U 0xbfe98c(mgr, owner, id, pos) = GU 0x49eac(owner, id, pos, 0) (C: GU jointFx 0xc24d8 calls it
    after the same player-area test, 0x4971c): 41 / 54 owner frames 242 (id 1), 252..362 every 10 (id 7); 51 242,
    252..442; only when the capsule hits the map and the owner is in the player's area;
  - sound 0xc6e9b4 at the capsule point nearest to the listener (here: the local hunter, joint 0): 36 / 37 / 53 id 209,
    41 / 51 / 54 id 201 (started once; 4U moves it every frame with 0x301074: GU counterpart not found, not
    ported), 52 / 55 / 56 also 202 every 167 frames from frame 340 (+688). em089_snd_pos (GU 0x4efb98).
    [x] 2026-10-19 (main agent): the move IS ported. 4U 0x301074(mgr, id, owner, owner, pos) = owner sound object
    (+0xd90) -> 0xbcaecc = queue command 6 sub 0 with the position; GU 0x4eff24 is the same (owner +0x111c, 0x4d5e14,
    0xbf0a84 = command 6 sub 0 -> 0xbf07c4; GU shells call it like that, e.g. 0x3fde7c) -> em089_snd_move. Per frame
    (4U table 0xc6e9f4): 36 / 37 / 53 and 41 / 51 / 54 move 209 / 201 once started; 52 / 55 / 56 also move 202 while
    the timer is in 173..340 (restart at 340 -> 173), then 201.
- Not ported: the +0x2ac / +412 u16 (0xffff here); the extras are not run in the spawn frame (4U runs the per-frame
  once at the end of the init).
Call sites for the behaviour agent (4U address -> subtype), em089_act.c:
  7/105 0x8be100 (53) / 0x8be138 (36): one site, branch on 0xb052d8 (aim layer weight == 0 -> 53, else 36);
  7/106 0x8be3c8 (37); 7/107.. 0x8be84c (41); 7/136 0x8beac8 (51); 7/114 0x8bf560 (41); 7/126 0x8bffcc (41);
  7/135 0x8c0620 (41); 7/143 0x8c14e0 (54); 7/146 0x8c23b0 / 0x8c246c / 0x8c248c (52 / 55 / 56 by action serial
  % 3: 1 -> 55, 2 -> 56, else 52). Call: `em089_shell016_post(self, subtype, 0)`.

## Ground shells uShell051 (shell agent)
Status 2026-10-18: code + data DONE, builds (107112 B, 0 warnings), not tested in game.
- module/em089_shell051.c / .h: class uShellEm089Gnd, `em089_shell051_post(owner, subtype, pos, yaw)`. 4U uShell051
  (type 51; posters 0x663d88 (11 users) / 0x663a60 (blob) -> 0x662b44; ctor 0xc90914, init 0xc8fda4, per frame
  0xc90048). Event: +8 pos ptr, +0xc angles ptr (blob: zero vector), +0x10 area, +0x11 / +0x12 / +0x14 / +0x1c /
  +0x20 (stage-object index, u16 id, material...) not needed. Init: prev = pos, x / z angles 0, attack record =
  subtype (0x1031ca4 + 52 + 40 * subtype, volume table 0x1031ca4, slot-80 args table 0x1031b28 = (2, 23 / 31 / 16)),
  2 / 13 / 15 velocity (0, 0, 6) by the yaw, 6 / 17 / 19 / 20 timer 58, sound 207 following the shell for 3 / 9-15
  (table 0x1031bfc; none for the blob splashes). Per frame: see the file header (age, scale growth into GU slot 0
  scale this+0x13bc = 4U shell +380 = slot+20, movement, ends, sound 220 at timer 58 for 6 / 17 / 19 / 20).
- Hit data (C): HDS entries 10..19 = 4U records 1, 3, 6, 9..15 (power 5 / 10 / 40 / 80 x4 / 10 / 10 / 10, windows
  s16 +0 / +2 = 8+200, 0+220, 58+20, 0+160..172, 0+155, 0+220, 0+142), HTS groups 4..9 = 4U volumes 1 / 2 / 3 / 6
  / 9 / 10 (spheres on bone 255 = the shell, radius 220 / 250 / 214 / 260 / 105 / 175). tools/build_em089_arc.py
  S051_*; arc rebuilt under the ARC LOCK (--cmdtbl gog): only _hitdata / _hitsize changed, em089_files.inc
  byte-identical.
- Users: em089_shell016.c (15, 3, 9-12, 13, 14, see above) and the blob ground impact (1 / 6 / 16 / 17 / 19 / 20):
  em089_shell.c impact branch must call (effects agent's file now; one line, replaces the em089_snd_splash call):
  `if (ground) em089_shell051_post(FIELD(void *, FIELD(void *, self, 0x136c), 0xc), k_splash[kind], pos, 0);`
  + `#include "em089_shell051.h"`. The splash plays 220 itself -> em089_snd_splash / its delay queue can go.
- Not ported: the stage-object check 0x6c5e88 (blob splashes end when non-zero), effects (0xc904d0).
- [x] End function 0xc906d8 (shell051-end helper, 2026-10-19; code + data DONE, builds 132556 B / 0 warnings, not
  tested in game). 4U uShell051 vtable 0xe6e8dc: slots 22 / 23 / 24 = init / per frame / end; the base move 0x9aae2c
  dispatches on state +0xf1 (0 / 1 / 2 / 3 -> slots 22..25), so the end runs once after the per frame set state 2
  (or the alive flag +0x16d dropped / the owner died). Ported as s051_end, called by s051_kill before the kill slot
  (= 4U order: posts, then 0x9ab16c + effect finish 0xc470dc). Switch on subtype - 2 < 16 (jump table 0xc90700):
  2 / 13 / 15 -> uShell051 4 + shake 4; 3 -> 5 + shake 4; 14 -> 18 + shake 7; 7 / 9-12 -> 8 + shake 7 (post =
  0x6635e8 -> 0x662b44 at shell +0x100, zero angles -> our yaw 0; shake 0xbfe98c = GU 0x49eac only when the owner's
  area = the player's, GU unit +0x1054 vs 0x4971c as em089_shell016.c); 16 / 17 [0xc908b0]: T+0xed = 1 (T =
  owner+0x8d88) + enemy item drop 0x911f58(owner, pos, 100, 0) = GU 0xac0ec (same arguments: rand % 100 vs chance,
  remaining-drop byte 4U W+0x7a64 = GU rec+0x5d54, sound 202 inside). Today's em089 end posts: 13 / 15 -> 4, 3 -> 5,
  9-12 -> 8, 14 -> 18; the rare-drip splashes 16 / 17 -> item drop at age 660.
  New subtypes 4 / 5 / 8 / 18 (init 0xc8fda4, per frame 0xc90048 jump table 0xc900b8): no velocity / timer; sound
  208 at the position (table 0x1031bfc type 2 -> 0xc8ffe4 = 0x312484, em089_snd_pos); slot-80 args (2, 31); scale
  growth 4: +0.35 dt to 7 (7 from age 20, 0xc9025c), 5 / 18: +0.33 dt to 2 (from age 6, 0xc90330), 8: +0.3 dt to 1.8
  (from age 6, 0xc90368); end at age 660, no end post. Hit data: 4U records 0x1031ca4 + 52 + 40 * sub -> HDS entries
  21..24 (appended after uShell005's 20: power 100 / 80 / 80 / 80, attack type 3, bytes 0x0c = 4 / 0x10 = 0x10 / 0x18
  = 50 / 40 copied, windows 0+88 / 0+20 / 0+15 / 0+20); volumes 4 / 5 / 8 / 11 -> HTS groups 11..14 (bone 255 spheres
  radius 300 / 562.5 / 500 / 560). tools/build_em089_arc.py S051E_RECS / S051E_VOLS. Effects: table 0x1031b54
  {65, element 12 = em089_014, mask 1 / 2 / 2 / 2} -> PEL 5104 / 5105 / 5108 / 5118 with k 0 / 1 / 1 / 1, scale
  0x1032020 1.0 / 1.3 / 1.0 / 1.0 (tools/efl4u2gu.py extra_records). Arc rebuilt under the ARC LOCK (--cmdtbl gog):
  HDS 21 -> 25 entries, HTS 11 -> 15 groups, PEL +4 records, em089_files.inc byte-identical.
  Logs: `em089 ground shell N (sub S) end: post sub X -> <shell> at x y z, shake I[ (other area: none)]` and
  `... end: item drop at x y z -> <ret>` (40 total).
  Not ported / deviations: the T+0xed write (= em089_act.c F_SHELL_ED, written by the drip helper, read by no em089
  code in 4U or the port); 4U also posts after the base move dropped a dead owner (owner 0, no shake / drop), ours
  needs the owner; the end runs in the same frame as the kill instead of the next one; effect +256 = 1.25 for 18
  (as 14's 2.0) not mapped. Open: the 4U slot scale +380 = radius multiplier assumption makes 4 reach 300 x 7 = 2100
  (5: 1125, 8: 900, 18: 1120) - check the explosion size in game.

## Quake shell uShell005 (shell agent)
Status 2026-10-18: code + data DONE, builds (118360 B, 0 warnings), not tested in game.
- module/em089_shell005.c / .h: class uShellEm089Quake, `em089_shell005_ground_impact(self, kind, off, scale, height)`
  = the shell part of 4U 0x954e5c (uEnemy ground impact): returns when pos y (W+412 = rec+0x44) > ground y (W+0x624
  -> rec+0x5b4, S) + height; position = (pos.x, ground y, pos.z) + off * size factor (4U 0x923fc8 = GU 0xbecf0) *
  scale rotated by the yaw; kind 1..7 -> uShell005 subtype 1 / 2 / 11 / 12 / 26 / 27 / 28 (event type 5, poster
  0x661d18). uShell005 (ctor 0xc59944, init 0xc59698, per frame 0xc598d0): slot scale = size * scale (+0x270 ->
  +0x17c = slot+20 = GU this+0x13bc), attack record = subtype (records 0x1025b58 + 112, volumes 0x1025b58, args 7 /
  5, 2), life 100 frames (dt).
- Hit data: HDS entry 20 = 4U record 1 (attack type 6 = tremor, power 0, active frames 14..24, byte 0x1c = 1 kept:
  first 4U record with a non-zero 0x1c), HTS group 10 = volume 0 (sphere on bone 255, radius 600). Only subtype 1
  (em089's) is converted; other kinds log and return. Arc rebuilt under the ARC LOCK (--cmdtbl gog): only _hitdata
  / _hitsize changed (1108 entries), entries 0..19 identical, em089_files.inc byte-identical.
- Call for em089_act.c 2/35 (before the effects line, 4U order: shell 0x661d18, then effect 0xc08628), with
  `#include "em089_shell005.h"`: `em089_shell005_ground_impact(self, 1, k_off, 0.8f, 900.0f);`
- Note for the effects agent: em089_efx_ground_impact scales the offset by speedFactor and uses the monster's y;
  4U uses the size factor (0x923fc8 = GU 0xbecf0) and the ground y (W+0x624 ~ rec+0x5b4), and skips everything when
  the monster is more than `height` above the ground.

## Part breaks (break agent)
Status 2026-10-17: module/em089_break.c/.h written, in build.py sources, `GOG_MOD_ROOT=/tmp/x python3
module/build.py` OK (64220 B), 0 warnings with build.py's CFLAGS, no data relocs. NOT called yet; not tested.
- [x] GU mechanism (C, static): the FRAMEWORK does flinch / break / sever counting, not only accumulation. 0xa5900
  (per frame) -> 0x97ddc: per part with dttune row HP != 0 (data block *(this+0x75ec)+100 -> +4 = obj+0x68): flinch
  HP rec+0x3be+12p runs down; at 0: reaction rec+0x3ae, break count rec+0x3bc+12p ++ (cap 14), 0x99db8 refills,
  0x99f98 = dtbparts records obj+0x64 {part, LR, HR, group} (count obj+0x8c): count == required -> 0xa44e8 (slot
  214 + net event) and reward flag bit group of rec+0x5cbe. Sever (row +2 limit, +4/+5 damage types, +6 HP):
  rec+0x3c0+12p -> rec+0x3b3 = part -> sever count rec+0x3bd+12p ++, reaction 14. dttune row = {u16 flinch HP, u16
  sever limit, u8 type, u8 type, s16 sever HP, u16 kind} (the data agent's "next-level HP" is the sever HP).
- [x] Monster side in GU: visibility (Rathian slot 132 0xcf56b4: XFS pair by count >= dtbparts count), cut tail
  spawnCutPart 0xc2330(this, 0, 0, joint 143, 0) at the sever reaction (Kushala slot 129, action (10, 114)): sets
  rec+0x3b4 |= 1 (detached bits = 4U W+0x42c), reward bit 7 (0x9d458), object this+0x7720 (field-1 model).
- [x] 4U: emd row evaluator 0x948378: cond 6 = break count(param) >= threshold (em089: parts 0, 1, 2, 3, 6, 7, all 1),
  cond 1 = W+0x42c & param (1 tail, 8 = spear / bone 200 = part 1, the Dragonator). 4U slot 64 0x8c67c0 = on-break
  hook (GU slot 214 counterpart): tail break effect + hurt-volume flag 4 clear (stubs, logged).
- [x] em089_break_update: installs 6 break records into dtbparts (MT heap new/delete, the resource frees obj+0x64):
  (0,1,1,1) (2,1,1,2) (3,1,1,2) (1,1,1,3) (6,1,1,4) (7,1,1,5); XFS 7/8/9 on parts 0/1/2 breaking, 10 on tail
  sever; every frame the 22 cond-6/1 rows -> group bits (g13/14/19/34 clear-only: tar_vis owns their cond-7 row);
  tail sever count -> spawnCutPart(this, 0, 0, 141, 0) (4U em089 chain 141-143; Kushala GU 143 = its 4U 0x8f);
  part-1 sever -> rec+0x3b4 |= 8 (no object: gekiryusou model not in a manifest model field; no reward flag).
- [ ] Data fix (better than the runtime override): dtbparts (field 34) heap0 = the 6 records above.
- [x] Wired (main agent): em089.c includes em089_break.h, em089_slot132 calls em089_break_update after
  em089_tar_steady, em089_spawn_setup ends with em089_break_spawn. Both build variants compile (64236 / 64812 B),
  em089_files.inc unchanged. Not tested in game yet. Expect "em089 break records: dtbparts .. had 2 .., now 6", then per hit
  "part N (...) flinch count 0 -> 1 BROKEN" with the broken mesh (head g27, wings g29/g31 ...) and, after ~1500 cut
  damage on the tail, "tail severed: cut object spawned" + the em089_00_tail model on the ground.

## Head aim (aim agent)
Status 2026-10-18: GU layer-1 API found and verified statically (all C); module/em089_aim.[ch] written, in
build.py, compiles without warnings (build 86640 B, em089_files.inc unchanged). NOT wired yet (em089_act.c belongs
to the main / shell agents): call sites below. Not tested in game.
Owns module/em089_aim.c / .h only (+ game.h tail defines, build.py source list).
- Model layers: 4U layer k at this+576 + k*304 (weight +72 -> layer 1 weight this+952); GU layer k at this+0x4b0 +
  k*0x140 (C: 0x53a1dc `add r1, r6, r6, lsl #2; lsl #6`; 4U +0x246 flag = GU +0x4b6, 4U +108 = GU +0x6c), so layer 1
  motion id this+0x5f4, weight this+0x638, layer-0 frame this+0x500 (4U this+656). Layer count this+0x4a4: uModel
  ctor 0x9396a8 sets 4, uMHModel ctor 0x539bac sets 1, uEnemy ctor 0xacc8c -> 0xacd9c -> setLayerNum 0x957480(this, 2):
  every uFestaEnemy (ours too) has layer 1.
- Mapping 4U -> GU (C = same body shape):
  0xb054ec layer setMotion -> 0x53a1dc (uFestaEnemy vt slot 49 = vt+0xc4); 0xb07be4 (layer 1) -> 0x53a1c4;
  0xb07ba4 (layer 1 + engine speed 0x941dd4) -> 0xb000c(this, mot, flags, blend, start);
  0x9200a4 (layer 1 at start frame, weight 1 - s1) -> 0xb03e8(this, mot, start, s1);
  0x935ff0 (yaw pair: s1 < 0 -> mot B, weight |W+916|) -> 0xb0694(this, motA, motB, frame, s1) (vselge at 0xb06f4);
  0xb054e0 weight setter -> 0x726dc (enemy) / 0x53a454 (model) = this+0x638; 0xb052d8 getter -> 0x726f8;
  0x918e80 smoothing (step rate * dt, clamp [-1, 1]) -> 0xb07d0 on rec+0x308 (4U W+916);
  0x918f28 aim reset -> 0xafeec (also done inside setMotionEx 0xafda4 = 4U 0x9190c4: weight 0, rec+0x308/30c/310 = 0);
  0x941dd4 speed (W+1028 * W+1036 * status, cat 10/11/13 excluded) -> inline in the GU wrappers (rec+908 * rec+916);
  0x93093c joint position -> 0xc1708 (jointPos, already in game.h). Rathian uses the same yaw pattern (0xcf82d0:
  atan2 to rec+464 - yaw, 0xb07d0, 0xb09e4 frame, 0xb0694(0x109, 0x10a)).
- em089 users (4U): 7/105 0x8bdd2c (pitch up, motion 0x26b, joint 3, clamp 30 deg, only when target above the head;
  re-evaluated once at frame 158 if weight != 0); 7/135 0x8c02b0 (pitch down, 0x27f, target + 100 up, clamp 45 deg;
  re-evaluated once at frame 238); 7/110 0x8be434 r1 = 1 (yaw: rel. angle / 20 deg smoothed at 0.3/frame into
  W+916, pair 0x255 / 0x256 at the main frame, step 2 every frame; step 3 re-applies the pair with the held weight);
  1/33, 1/34 0x8bb0f4 (full-weight layer motion 80 / 81 over the turn, flags 2, blend 16); 11/0 mode 1 0x8b6da4
  (0x325, cat 11 not ported). All layer motions exist in em089_2.lmt / em089_0.lmt (0x26b / 0x241 both 429 frames,
  0x255 / 0x256 / 0x27f / 0x247 / 0x27e 925).
- API (em089_aim.h): em089_aim_start(self, kind), em089_aim_update(self, kind), em089_aim_stop(self),
  em089_aim_weight(self), em089_aim_layer(self, mot, flags, blend, start, weight); kinds PITCH_UP (7/105),
  PITCH_DOWN (7/135), YAW (7/110 step 2), YAW_HOLD (7/110 step 3). game.h tail: layer1MotionW 0xb03e8, layer1Motion
  0xb000c, layer1Pair 0xb0694, layer1SetWeight 0x726dc, layer1Weight 0x726f8, aimSmooth 0xb07d0, aimReset 0xafeec,
  motionFrame 0xb09e4, REC_AIM_W 0x308.
- Call sites for em089_act.c (`#include "em089_aim.h"`), replacing the stubs:
  act_1_22 step 0: `if (var >= 2) em089_aim_layer(self, var == 2 ? 80 : 81, 2, 16.0f, 0.0f, 1.0f);`
  act_7_105 case 0: `em089_aim_start(self, EM089_AIM_PITCH_UP);` (after setMotion 0x241);
    case 1, before the frame-160 check: `if (at_frame(self, 158.0f)) em089_aim_update(self, EM089_AIM_PITCH_UP);`
  act_7_107 case 0: `if (var == 1) em089_aim_start(self, EM089_AIM_YAW);`; case 2 first line:
    `if (var == 1) em089_aim_update(self, EM089_AIM_YAW);`; default, after the tar_add window, before isMotionEnd:
    `if (var == 1) em089_aim_update(self, EM089_AIM_YAW_HOLD);`
  act_7_135 case 0: `em089_aim_start(self, EM089_AIM_PITCH_DOWN);` (after setMotion 0x27e);
    case 1, before the frame-240 check: `if (at_frame(self, 238.0f)) em089_aim_update(self, EM089_AIM_PITCH_DOWN);`
- Deviations: target = hunter root joint (4U W+536 target slot, refreshed by 0x92d0d4 from the kind-2 check of
  frame 250 in 7/110); 7/105's effect choice by weight at frame 160 stays with the (stubbed) effect posts.
- [x] Wired (main agent): all call sites above in em089_act.c (1/22, 7/105, 7/107, 7/135). Both build variants
  compile (93840 / 94432 B with the shell agent's work in progress), em089_files.inc unchanged.
- Next: in-game check (log lines `em089 aim start/update/yaw/layer`; ask the user whether the head follows them).

## Shell data (shell-data agent)
Status 2026-10-18: DONE (static; not tested in game). ARC LOCK released.
- [x] Family shell\em\em089_00_shell00\ = copy of Kushala's em024_00_shell00 (108 files: XFS 0x4aa69872 def with 26
  entries x ef/snd/hit/sh params, ShellCmnParam FUP em089_00_00, HDS _hitdata, HTS _hitsize). Only the def names
  files: 107 paths renamed (same length, structure untouched); its pel/pts lists stay Kushala's (kept in the arc).
  ef/snd/sh/hit params unchanged (entry 0 = what em089_shell.c uses, param+8 = 0). Builder: tools/build_em089_arc.py
  shell_family / shell_hds / shell_hts; def = new file ID **0x1071d** (EM089_FILE_SHELL00, appended; all older IDs
  identical). module/em089_shell.c EM089_SHELL_FILE = 0x1071du. Module builds, 0 warnings.
- [x] HDS layout (C): GU 0x168e98 and 4U 0xb700f8 read entry bytes 0x00..0x23 at identical offsets (s16 0/2, u16
  power 4, u8 attack type 6, u16 8, u8 a/b, u32 c/10/14, u8 18, u16 1a, u8 1c, s8 1d, u8 1e..23); byte 0x19 = HTS
  group index (GU 0x4a2790 with -1, 4U 0x9a9624). GU-only tail: f32 +0x28 (1.0 in all 1237 GU entries), u8 +0x2c
  = level -> slot+0x9e (table 0x173ec24 {0,5,15,25,40,50,100,200}, added to the target's +52 on hit), +0x26/+0x2e/
  +0x30 read only for owner types 0/2 (monster owners are 1).
  Written per record = 4U bytes 0..0x23 except: byte 0x12 = 4U & 3 and +0x2c = 4U byte 0x12 >> 2 (= 2; GU moved the
  level out, as GU HDE byte 31 / emdata4u.attackdata; correlation on aligned etd records, noisy), byte 0x1c = 6 (4U
  0 everywhere, GU 6..10, 6 = commonest/Kushala's/HDE converter), +0x28 = 1.0.
  Values: records 0/2 power 5, 1/3 power 40 (Kushala 80/100/80/100); type 63 (Kushala 3; same ID space: aligned 4U/GU
  attack records map types identically, GU switches 8..69 send 63 to their default case); byte 0x0b 5 / 30
  (Kushala 40); 0x1d 10 (20); 0x22 50 (0); level 2 (4).
- [x] HTS radius (C): 4U volume table 0x1031690[record byte 0x19 = 0] -> 0x1031ad4 = one 40-B hitsize record
  {bone 1001, shape 0 sphere, f32 +0x0c = **80.0**}, then 0xFFFF; same layout as GU's 48-B record (emdata4u.hitsize).
  Written: Kushala's file with radius 80.0 (was 200.0); GU's constant +0x0a = 0x0848 kept (4U 0).
- [x] EM089_SHELL_ID 175 stays: the id is only consumed through 0x4a1b38 (sole direct reader of param+4), whose 34
  callers compare it with specific ids (22, 25, 26, 41, 42, 48-51, 95, 113, 190-192, 216, 225-229, 247-251, 264-268,
  0x12f-0x137, 308/312, 0x149/0x14b, 0x177, 380), none 175-180; the shell-table row (file 0x8a02) is only used by
  the 0x48c388/0x48c4f0 request path that em089_shell.c bypasses. No reason to change it.
- [~] Effects (not converted): 4U em089 EFL list = pointer table 0xef7228 (25 entries: 000, 002, 003, 005-016,
  020-024, 030-032, 050, 051; referenced from 0xef8a60 / 0xefb728). Group 65 element 2 / 14 = either list index
  (-> em089_003 / em089_016) or file number (-> em089_002 / em089_014); the 4U resolver was not traced, so open.
  Note: the copied ef params still point at Kushala's pel list (as before with family 00).
- Note for the shell owner (code, not data): 4U passes slot+0x8 = 23 (kinds 0/2/4/6) or 16 (others) and slot+0x66
  = 2 to the attack setup (0x9ab120 stack args); GU uShellEnemy slot 80 passes 31 / 2 (looks like a target mask).
Next: in-game hit check (log "gogport: file 1071d ..." must show a non-zero resource; blobs should do 4U damage),
then effects (resolve group 65) by the effects agent.

## Arena (arena agent)
Owns module/stage.c (+ new module/stage_*.c), tools/stage4u2gu.py, sbc.py, sis.py, build_gog_quest.py, m28 romfs,
notes/stage.md. Status 2026-10-18: steps 1-4 DONE (details + deviations: notes/stage.md section 11; test recipe:
section 10). module/romfs holds the session-5 alias arcs + the --bq quest; module compiles with/without
GOG_STAGE_ALIAS (84376 / 84872 B at the last check). New: tools/sdl.py, build.py hook ('stage_gimmicks', 0x50249C)
(log only), stage4u2gu.py `alias --keep-{sets,filters,gimmicks,koware}` fallbacks for bisecting a load failure.
- [x] 1. --bq validation. Done (C): every start/arrival/spawn point lies on the converted floor (probe: camp 627,
  a01 -3..-23, arena 0 / 1700 / 948 / 951; Gogmazios spawn (633.5, 0, 1510.8) on y 0); SIS format identical.
  FOUND (C): GU Fortress gimmicks are code-spawned SHELLS, not set data: 0x50249c (flags u16[stage] 0x162bd60, stage 26
  = 0x3ec): st003 x4 Dragonator spears (uShellSt003, model 0xd41e, pos = st003 FUP vec[3..6], yaw/pitch = st003_sh001),
  st004 ballista per SIS point kind 3 (pos/angle from the point, +0x12 u16 -> ballista param), st008 per SIS kind 6,
  st006 x2 rail-cannon cart (models m26d-s00..s03 = 4U m19a03d-s01..s04, path = SDL m26d-etc-a00, stop frames = FUP
  ints), st007 gate (m26d-a00/a01 = 4U m19a03d-a00/a01, pos = st007 FUP v0 (-5980, 2050, -16200), area 1). Shell data
  lives in map_com (ours = m28.arc); quest shell arcs st0NN.arc are never requested (no path string) -> editing the m28
  copies changes ONLY the alias. (SIS point +0x12 u16 = angle, +0 = f32 point id: found, copied from 4U.)
- [x] tools/sdl.py (new): rScheduler v0x15/v0x16 reader/writer/converter; re-layout byte-identical on 709 GU + 703 4U
  stage SDLs; 4U->GU = 24->32 B entries + kind renumbering (6,7,8,9,a,b,c,d,e -> 6,8,9,b,c,d,e,f,10).
- [x] 2. gimmicks (stage4u2gu.py GIMMICK_EDITS / build_stage_arc): ballistae = 4U SIS points (automatic, GU st004);
  Dragonator spears st003 moved under 4U's switch (G: derived from GU's Fortress rule, 4U transforms not traced);
  rail-cannon cart st006 parked at 4U's start pose (no travel); st007 gate left in area 1 (harmless, 4U gate not
  shown); area-2 breakables <- 4U k01/k02 (static: no attack sphere), 4U k03 dropped, Fortress area-1 gates hidden.
  Not ported: 4U-only scheduled gimmicks (a01 doors/a04 wall, lever s01, s02, s03/s04 cannons), pile-bunker logic.
- [x] 3. looks: area set schedulers <- converted 4U ones (camp props, a01 c00..c04 + background ring, arena
  c00..c03), Fortress props + their textures dropped; filter schedulers: 4U light dirs/colours, fog, MhFilter.
  Not ported: rain variants, sky motion, stage effects (4U "Effect" controller class absent in GU -> effects
  agent: EFL st/m19a03 + qe000/qe001, schedulers m19a03d-e01..e10/-col), camp camera presets, RouteFind tables.
- [ ] BGM (sound agent converts; arena wiring ready to do): write module/romfs/nativeNX/sound/bgm/map/m28d/wav/
  m28a0{0,1,2}d.opus (area 0 <- 4U str_m19 m19_a00d, 1 <- m19_a01d, 2 <- m19_a03d; 4U stage BGM bgm_map_19 in
  bgm_st_19) + per stream samples / channels / rate / loopStart / loopEnd here; then stage4u2gu.py renames the m28d.arc
  STQR paths m26d -> m28d and writes the sizes (format: notes/stage.md section 11 "Looks"). Until then the alias
  plays the Fortress streams.
- [x] 4. test recipe: notes/stage.md section 10 (romfs already built; install list; expected logs; visual checks).
- For the behaviour agent (em089_act.c; facts, C): Battlequarters = stage byte 26 + area 2 while
  `int stage_alias_active(void)` (module/stage.c, exported) is true -> usable as the slot-42 "Battlequarters" gate
  (4U: global +0x1c == 61). Arena floor id 1 (collision group w1 >> 24) x -3919..3867, z -5622..5527, y 0; ledges
  950: west id 2, ballista platforms ids 3/4 (west), east id 6; 1700: north id 5 (z 3401..6556; Dragonator switch
  (0, 1765, 3610), GU spears at (+-380, 1080, 3615) / (+-740, 610, 3613) facing -z), south id 7 (z -7600..-4710);
  abyss y -700 (id 0). Ballistae at (-1930, 950, 2135) and (2945, 950, 2160). Gogmazios spawn (633.5, 0, 1510.8).
  The wall probe sees the real 4U walls (collision converted 1:1). The Fortress RouteFind (relation) tables are NOT
  converted: route queries between 4U floors 1..7 use Fortress floor data (G risk for ledge-to-ledge pathing).

## Effects (effects agent)
Owns tools/efl4u2gu.py (new), module/em089_efx.c/.h (new), effect files in the em089 arc (under ARC LOCK).
Status 2026-10-18: DONE round 2 (static; not tested in game): converter, arc, module code, blob / attack / ground
shell effects, aura, ground impact, slot-75 gate, stage effects converted (hookup = arena-2 agent); roar radial blur
[-]. Scratch tools/corpora:
scratchpad efx/ (eflscan, fdiff, pel2, psl, lmtev, mefpel .py; c4u/cgu/cpel/cmef .pkl).
Findings (C = code, S = corpus statistics, 1469 4U / 1115 GU EFLs, 7430 GU PEL records, 5680 GU PSL motions):
- [x] 4U effect pipeline (C): motion-synced effects = LMT v67 animation events (anim +0x34 -> 4 groups x {u16
  remap[32], u32 n, u32 ptr} -> n x {u32 active bits, u32 frames}, run-length); group 2 remap = MEF ids, played by
  cMhMotionEffect (enemy+0xc78; request 0x390f9c, create 0x391b50). MEF (rMhMotionEffect, 72-B records, loader
  0x398fbc): {u8 b0, u8 slot mode, u8, u8 list kind (5 = monster, 1 = common qe), u16 id, u16 group (89 = em089,
  6 = qe006, 13 = qe013), u16 file (EFL number), s16 joint (bone id, -1 none), u32 flags (0x200 = transform),
  s32 k (element group: mask 1 << k, -1 = all), f32 repeat interval, vec4 pos, vec4 rot (deg), vec4 scale}.
  em089: 68 MEF ids; 70 motions carry group-2 events (42/43 = steps, 11-70 attacks/roars/wings, 1100 unused).
  0x6620c4 (12 em089 calls, ids 36/37/41/51-56) is NOT an effect post: it spawns uShell016 generic shells
  (camera/quake objects, subtype = r3; e.g. 0xc0b470(mgr, 48/50/53...)). The tar shells (uShell050) carry
  their own effect (group 65 elem 2/14). 4U common EFLs: core_quest.arc (qe*), core_common.arc (cm000/cm007).
- [x] GU counterpart (C): PEL = rProofEffectList v15 (loader 0x323014): 'PEL\0', u32 15, 3 lists {u32 n, n x
  {u8 len + EFL path, u8 len2 (+string if >= 2, else skip), 160-B struct}}. Struct: vec4 pos, vec4 rot (deg),
  vec4 scale, u16 id, u16 joint (0xffff none), u16 1, flag bytes +0x36.., u32 element mask +0x48 (0xffffffff /
  1 << k: matches MEF k), defaults (S majority) elsewhere. PSL = rProofEffectMotSequenceList v2 (loader 0x324b48):
  'PSL\0', u16 2, u16 motions, u32 offsets; entry {u32 frames, u16 0, u8 32, u8 flags, u32 data, u32 0}; data
  {u32 slot mask, u16 id[32], u32 kind[32] (3 = PEL c list 1, 4 = PEL u list 1, S 99 %), u32[32] 0, u32 n,
  u32 events -> n x {bits, frames}} = the 4U LMT event group with the same run-length encoding.
  Enemy: manifest 16 = PEL c -> this+0x1358, 17 = PEL u -> this+0xb624, 18..21 = PSL per motion list.
  Code post: 0x6ff74(this, 2, id, req) = PEL u list 2 (0x6fe90 = PEL c); req = 0x40b10 ctor (~0xe0 B),
  dtor 0x40b50; returns uMHProofEffect*; stop = 0x32a400(eff, 0); uFestaEnemy slots 115/116 wrap them.
- [x] EFL layout (S + C loaders 0x23d6ac / 0xb5c5f0): same container in both versions (header, 16-B entries of 4
  block words (off - 0x30) << 8 | type, n2 0x70-B tail records). Block sizes identical except unit type 9
  (Filter 0xc0 -> 0xe0). Unit type byte -> class (4U factory 0xafe9e0): 0 Billboard, 1 Polyline, 2 Polygon,
  3 Texline, 4 Line, 5 Model, 7 LensFlare, 9 Filter, 0x14 SizeBillboard ...; em089 uses 0, 1, 2, 5, 9.
  Differing fields: unit +0x18 bits 12-15 (4U only; 4U draw bits 26-29, GU reads draw bits from +0x50 bits
  8/9/12 instead), GU-only +0x18 bits 4-11/17/19, +0x14 bytes 2/3, element header +8 bit 27; textures RGBA8 NOMIP
  in GU (4U ETC1/ETC1A4); EAN identical except GU sets byte +0xf = 1.
- [x] tools/efl4u2gu.py (2026-10-18): 31 EFL (25 em089 + qe006_001/003/035/036 + qe013_003/004 named by the MEF)
  + 4 EAN + 10 TEX (RGBA8) + 5 effect models (own boneless converter -> GU effect format 0x207D603B: f32 pos,
  10:10:10:2 normal, f16 uv, RGBA; MRL from GU cm101_000 + 4U BS/DS/RS states) + PEL u (68 MEF records, lists 1
  and 2) + 4 PSL (114 motions with group-2 events; slots with MEF id 1100 dropped: no MEF defines it, 4U plays
  nothing either; run lengths trimmed to GU's frames - 1 total). Only EFL change besides the version: the two
  Filter units (em089_011 / 014) re-laid out. Paths = 4U paths (no clash in any of the 13933 GU arcs).
- [x] Arc rebuilt under the lock (04:34): 1025 -> 1085 entries (+60, 0 removed, 0 changed); files.inc gains
  0x10720 PEL u, 0x10721..0x10724 PSL 0..3; manifest 17..21 = ours (were Kushala's 0x7a60..0x7a64; 16 = PEL c
  0x7a5f kept = GU common effects). --donor-efx rebuilds with Kushala's for bisecting. Module unchanged by this (generic file-ID hook).
- [x] module/em089_efx.c/.h + generated em089_slot75.inc (tools/em089_slot75_gen.py), in build.py, 0 warnings.
  em089_efx_post / _post_at / _stop (0x6ff74 / 0x40b10 / 0x32a400). Slot 75 = GU slot **168** (not 124: GU 124 is
  only called when this+0xb736; Rajang 0xde5f80 and 0xd53f64 override 168 to drive joints with 0x72438).
  Gate W+0x434: resolved in round 2 (below).
- Call site (done by the main agent): em089.c `s_vt[2 + 168] = (uint32_t)&em089_slot75;`.
- [x] Round 2 (2026-10-18 ~05:50, static, compile OK 113308 B / 0 warnings, arc rebuilt twice under the lock,
  em089_files.inc byte-identical, PEL 68 -> 141 records, arc entries +23: qe006_000, qe016_003, m19a03_000..013 +
  ef_m19a03 model/MRL + m19a03_000_BM_NOMIP). Code-post records (tools/efl4u2gu.py extra_records / stage_records):
  3000 / 3001 blob drip / shot, 3100 ground impact, 4000 + sub / 4100 + sub uShell016 init / end, 5100 + sub
  uShell051, 5701 / 5702 / 5704 aura, 6000 + 4 * index + group KowareEft, 6100 + n m19a03_NNN.
  - [x] Slot 75 gate (C): 4U W+0x434 = 0x94741c(this, 1) = byte W+0x42e + 6i, i = 1 = break count of part 1 (the
    spear, bone 200); GU 0x9d428(this, 1) = rec+0x3bc + 12 = rec+0x3c8 (notes/api-map.md, C; written by the
    framework break counter 0x97ddc). em089_slot75 now reads it every frame: the joint-200 drive runs while part 1
    has broken exactly once (as 4U: 0 or >= 2 = off). Not network-only.
  - [x] Tar blob effect (em089_shell.c): 4U table 0x1031694 (kinds 2-5 em089_016, others em089_003, mask -1,
    scale 1) posted on the owner with the blob as attach target (req+0xd0 = shell vt+0x130, flag 2). The proof
    effect reads its target every frame (0x43244), so slot 16 is overridden: disarm the attack bytes, stop the effect
    (0x32a400(h, 0)), keep the shell until the effect is dead (GU EmBase pattern 0x3fa540), then the base kill
    0x4a247c; forced 0x32a400(h, 1) after 300 frames; dtor kills a live effect. All death paths (life, impact, owner
    gone in uShell_move) go through slot 16.
  - [x] uShell016 uEffect002 (hook em089_shell016_fx -> em089_efx_shell016_fx, installed at run time by
    em089_efx_init / every em089 frame): 4U 0xc0b470 packet (joint 255, offset, mode 1 = element mask) -> uEffect002
    (ctor 0x1b6fb0, update 0x1b4038: ids 48/50/53/54 -> 0x1b5ba0 = at the shell's start point along the capsule,
    scale 2.5, id 50 / 54 pitch +35 / +40 u16; owner gone -> finish; 53/54 finish at life <= 10 = 0x1b5d68). GU:
    record on the owner's joint 3 with the subtype's offset / x angle (36 30.0, 37 39.4, 41/52/54-56 33.75, 51
    33.97, 53 y -16.9 deg). End effect (shell's second call, mode 2) = 4100 + sub, finished 2 frames later. Effect
    end mirrors the 4U shell rule (motion change / life by owner motion step) + optional em089_efx_shell016_end.
    Round 3 (fixed): request field overrides traced (0x31c280 -> 0x31c3a8: req+0x14 bit 0 offset req+0x20, bit 1
    rotation in degrees req+0x30, bit 30 scale multiplier req+0x40; GU 0x10b04c4 posts a beam with world position +
    pitch/yaw this way). Moving subtypes: joint-3 record + rotation override x = P+26 + owner x angle (rec+0x50 = 4U
    W+0x1a8, except 36) (+ id 50 / 54 extra). 36 / 53: world-position post (records 4236 / 4253, joint -1) at the
    spawn point q with the segment angles (pitch, yaw) computed like s016_place (53: y 0xf400 + flattening dy = 0 ->
    pitch 0), i.e. static as in 4U. Remaining: moving subtypes carry the joint's roll (4U: yaw / pitch only).
  - [x] 7/105 breath choice by aim weight: wired by the behaviour agent (53 / 36 via em089_shell016_post); its effect
    (id 48, record 4053 / 4036) comes from the hook.
  - [x] uEffect002 57 (em089_act.c roar stub -> em089_efx_aura(self, &F_SHAKE, &F_FLAG_E4)): 4U 0xc0bd38 packet
    (joint 1, mode 1) -> update 0x1b6520 = persistent phase-2 aura: finish when work+0xca == 0, work+0xe4 == 1 or dead
    (0x94d7a8); self re-post in mode 4 while W+0x1c8 != 0 (rec+0x1ba), 2 while W+0x1c9 == 1 (rec+0x1bb), else 1;
    re-posted by slot 39 (0x8ba1a0) and the 0x8c5768 tail when e4 is reset. Port: em089_050 records 5701/5702/5704
    on joint 1; ticked from slot 168: on while ca && e4 != 1 && alive, re-posted on mode change / when it becomes
    wanted again. The behaviour agent ported the e4 reset (round 3): no explicit re-post call is needed, the tick
    re-posts in the 4U mode (4 if rec+0x1ba, 2 if flying, else 1) as soon as e4 != 1.
  - [x] 2/35 ground impact (em089_act.c stub -> em089_efx_ground_impact(self, 1, {0,0,800}, 0.8, 900)): 4U 0x954e5c =
    (round 3, with the shell agent's trace) skipped when pos y > ground y (W+0x624 = GU rec+0x5b4) + height; pos =
    (x, ground y, z) + yaw-rotated offset * size factor (0x923fc8 = GU 0xbecf0) * s0; kind 1 -> tremor shell
    (em089_shell005.c, shell agent) + 0xc08628 dust = group 1 file 64 = qe006_000, scale s0 * 0.8 -> PEL 3100 (scale
    0.64). Deviation: material variant 0xc094e8 ignored.
  - [-] Roar radial blur, round 4 calibration: DISABLED (em089_efx_roar_blur logs only, record 3200 / em089_roarblur
    no longer built). Corpus: 4U calls the code blur 0xc0819c from 47 sites (every roaring monster, same class ramp);
    GU enemy arcs hold only 17 EFL Filter units (cm202_050, em013/027/033/038/068/071/072/086), 4U 21; their words
    32..35 (4U 28..31) are a colour + alpha ((1,1,1,1) x8, (0.924,0.871,0.849,1) em033, (1,1,1,0.277) em071/072,
    (1,1,1,0.15) em068 ...), the same values in both games (Capcom's conversion copies them), none identifiable as a
    roar blur; no Filter / EAN curve drives a strength over lifetime in these files. GU code never instantiates
    uRadialBlurFilter. So no 4U -> GU strength mapping and no ramp: a guessed full-screen filter is worse than none.
    Round 5 (own-code route via GU uRadialBlurFilter, DTI 0x21209b4), still [-]:
    (a) CONFIRMED: its draw 0x8b9070 -> 0x8b9094 selects AppShaderPackage.mfx entries by index (MFX v53, 2862
        entries): PS_RadialBlurFilter 0x823 (0x8b9ad4), FRadialBlurAlphaOcclusion 0x821, FRadialBlurWidthOcclusion
        0x81f, FRadialFilterAlphaColor 0x81d, FRadialFilterMaskDisable 0x81b, FRadialFilterSampleColorScaleFade 0x819,
        SSRadialFilterClampLinear 0x2ae; TRadialBlurFilter (2826) and CBRadialBlurFilter (685: fRadialBlurCenter /
        Start / Width / Color / Threthold / WidthScale / WidthOffset) exist in the package.
        Properties (createProperty 0x8bba10): mSamples (u16 +0x30 = 5), mBlurStart +0x84 (1.0), mBlurWidth +0x88
        (-0.1), mBrightThreshold +0x8c, mColor +0x60, mCenter +0x40 (0.5, 0.5), mWPos +0x50, mStartH/EndH/StartW/EndW
        +0x98/+0x9c/+0xa0/+0xa4, +0x90 / +0x94 (10000).
    (b) NOT established: newInstance = 0x8b8a9c (240 B, vtable 0x178a1e4, defaults above), but no GU code creates
        any uFilter at run time (uRadialBlur / uFade / uMh / uColor / uBlur / uMotionBlur newInstance have no direct
        callers; filters come from data, e.g. scheduler sets found by DTI 0x9680bc); its unit line getters (vtable
        slots 18 / 19) are null, so the proof-effect style registration (line = vt[0x48]()) does not apply, and the
        line / filter-manager registration that makes slot 12 draw is untraced (4U used 0x64608c line 20).
    (c) NOT established: 4U's base uRadialBlurFilter (192 B, draw 0x3b272c) is the 3DS fixed-function version
        (layered zoomed quads; 4U +0x68/+0x6c ramp 0 -> 0.035, +0x84 0.35, world pos +0x58), GU's is a shader with
        mBlurStart / mBlurWidth / mSamples in screen space: a plausible but unproven mapping is mBlurWidth = -ramp,
        mWPos = joint 3. EM089_ROAR_BLUR not added; em089_efx_roar_blur stays a logged no-op.
  - [~] In-game test 2 (log 2026-10-18_11-17-26): only 3000 / 5101 posts logged (shared 80-line budget); blob effects
    ended normally (no forced stop). Fix 1 (blob effect under the monster): attached posts now fill the request like
    GU's own shells (0x4a1d34 via e.g. 0x3f9560): req+0x1c |= 3 (world position + attach), req+0xc0 = unit position,
    req+0x4 = unit, req+0xc = unit area, attach = unit vt+0x130 (shell+0xfd0, uModel base ctor 0x5398a8 member whose
    vt[1] delegates through +0xfd4). Joints audited (C): 4U 0x93093c / 0x930894 and GU 0xc1708 / 0xc1660 and the
    proof effect's PEL joint (0x32a3b4) all go through the joint ID table (4U +0x228, GU +0x498), joint world matrix
    4U +8 / GU +0x10 (pos row 3); tools/mod4u2gu.py keeps bones, local / inverse-bind matrices and the id remap, so
    4U ids are GU ids: 3 = neck/head junction (index 6, bind z 680), 4 = head (710), 201 / 202 = jaw (815). Every id
    used (0, 1, 2, 3, 4, 14, 18, 60-65, 71, 74, 75, 140, 142, 143, 200) exists in the model. 4U places the breath /
    beam at joint 3 (+ (0, -50, 130) for 41/51/52/54-56) too, i.e. behind the mouth. Log: sub 36 capsule from (-713,
    561, 606) aimed 16 deg UP (head pose at frame 160 + x 30 deg), 41 aimed 55 deg down (x 33.75 + owner x angle
    rec+0x50), 53 flat. Added a diagnostic line per attack-shell post (joints 3 / 4 / 202 world positions) and a
    separate log budget for frequent posts, to settle the origin question in the next test.
  - [x] Pre-test review: effect handle lifetime. GU has no effect-side clearing of an owner's handle: GU's EmBase shells
    (0x3fa330..0x3fa36c) poll their raw handles +0x1624 / +0x1628 every frame with (h+0xc & 7) - 1 >= 2 -> h = 0, and
    0x3fa540 waits for the zeroed handle before the kill (0x3fa52c is a timer branch, not a callback). Ours now follow
    the same rule everywhere: em089_shell.c polls S_EFX every frame (added; before only at kill time), shell051 every
    frame, shell016 slots / aura every em089 frame (slot 168). Residual risk = GU's own: a handle read after the
    unit manager freed a dead effect within one frame; and our shell016 / aura slots are polled only while em089's
    slot 168 runs. em089_efx_forget (coordinator) clears all static per-monster state (s_s016, s_aura, s_s75,
    s_efx_owner); no other static state added.
    Round 3 attempt (kept for the record): em089_act.c -> em089_efx_roar_blur(self): player's area only (as 4U),
    PEL 3200 on joint 3 = port-made EFL effect\efl\em\em089\em089_roarblur (tools/efl4u2gu.py make_roar_blur): em089's
    own 4U radial-blur Filter entry (em089_011 entry 5, its element header / Filter unit / param blocks / tail record),
    offset zeroed, tail word 1 (lifetime 40 in em089_011) = 148 frames at 60 fps = the 4U ramp (7 + 50 + 16.7 frames
    at 30 fps). Deviations: strength = em089_011's Filter words (0.844), constant (no 0 -> 0.035 -> 0.025 -> 0 ramp):
    4U uMhRadialBlurFilter is a 3DS render-target filter (base 0x3b2994, only used by this class), the 4U EFL Filter
    unit is a different class (type 9, 448 B, ctor 0x415c4c), and GU's radial blur constants are uploaded as a block
    by 0x8b9094 (fields +0x40 centre 0.5/0.5, +0x84 1.0, +0x88 -0.1, +0x94 10000 ...), so 0.035 has no traced GU
    counterpart; tail word 1 = lifetime is inferred (S: em089_011 40 frames), not traced. In-game check needed.
  - [x] uShell051 effects (em089_shell051.c): 4U 0xc904d0 -> 0xc08628 table 0x1031b54 {65, file, mask} + scale table
    0x1032020 -> PEL 5100 + sub at the shell position (world), handle dropped when dead, finished by our slot 16 /
    dtor. Not mapped: yaw, material byte, subtype-14/18 field +256.
  - [x] m19a03 stage effects converted (all 14 + qe016_003); 4U CreateKowareEft handler 0xc0afa8: index -> table
    0xe06378 (2 qe016_003, 11 m19a03_000, 12..17 m19a03_001/002/003/004/008/009), mask 1 << KowareEftGroup, area gate.
    API em089_efx_stage_kowareeft(index, group, pos, area) / em089_efx_stage_efl(n, pos); interface sent to the
    arena-2 agent. Hookup waits for breakables (arena-2 agent: none can break yet).
  - [x] Round 3, other stage-effect triggers (call sites sent to the arena-3 agent):
    - m19a03_007 (the Filter one): (a) explosion of the 4U uShell022 subtype-9 projectile at impact (per frame
      0xc74b78 / 0xc75168: m19a03_007 + material + explosion attack 0x9ab120 rec 31; launch m19a03_006 (96/4) once,
      trail m19a03_012 (96/8) looping, handle +0x288), fired by 4U quest-manager stage-event code (0x6b985c /
      0x6b9d68; exact scripted trigger not resolved, not the Dragonator spears); (b) hit spark of attacks with hit
      effect type 39 (attack data +74; hit-spark function 0xbf203c case 39). API added: em089_efx_stage_efl_on(n, unit).
    - e04 (m19a03_001 at (0, 1270, -5100), frames 3935 / 13445, likely the a04 wall) and e08 (m19a03_008 at frame 2)
      are gimmick-scheduler driven; m19a03d-col tint not representable. No other trigger for m19a03_005/010/011/013.
  - Round 3 arc: rebuilt under the lock (06:40), em089_files.inc byte-identical, effects 84 entries (+ em089_roarblur),
    PEL 144 records (+ 3200, 4236, 4253). Module 120704 B, 0 warnings.
- Not done / deviations: unit +0x18 bits 12-15 kept (4U draw field, GU semantics differ), EAN flag 0, effect
  material constants = GU template's, MEF b0 / slot mode / flag bits / repeat interval not mapped (template).
- [~] Stage effects (arena request), analysed, NOT hooked (stage.c untouched): the 11 4U schedulers of the class
  0x5a17f498 are (a) m19a03d-col "MhEffect" = area tint colours for common effects (soil / water / tuta / poison /
  lens flare), (b) e01..e10 "Effect" = KowareEft* (area, pos, colour, group, scale, ground type, CreateKowareEft
  events {frame: effect index}): e01/e02/e03 sit on the breakables k01 (5225, 950, 1370) / k02 (-4540, 950, 1500) /
  k03 (165, 1700, 5500) with indices 11 at frames 10/20 and 2 at 201/226 = the break sequence; e04 (0, 1270, -5100)
  index 12 at 3935 / 13445; e05..e10 at pos 0 (relative to their gimmick object). None is ambient: all are played
  by 4U KowareObj breaks / gimmicks, which the alias does not port (breakables static, no pile-bunker logic). GU has
  no such controller (no KowareEft / MhEffect / stage-effect class in its DTI names). Hookup when breaks exist:
  convert effect\efl\st\m19a03\m19a03_0NN (14 EFL, same converter; index -> file mapping still to trace in the 4U
  controller) and post them at the scheduler positions from the break event with em089_efx_post_at (owner = the
  monster) or a stage-owned PEL. qe000/qe001 resources the em089 EFLs need are already converted (qe001_000 model,
  qe001 textures / EAN).
Next (effects): in-game check of `gogport: file 10720..10724`, `gogport: em089 efx post id ...` (non-zero handles
for 3000/3001, 4036.., 5701.., 3100, 51xx), the blob trail following the blob and fading after impact, breath/beam
effects at the mouth, the phase-2 aura after the 1/25 roar, the roar radial blur (3200: visible? strength / length
plausible?), 7/105 breath effect staying at the spawn point.

## Sound + BGM (sound agent)
Owns tools/snd*.py (new), module/em089_snd.c/.h (new, if needed), em089 sound call/bank/request (under ARC LOCK), BGM.
Status 2026-10-18: DONE (static; not tested in game): em089 SE converted + in the arc, battle BGM + arena streams
converted and wired; code-sound call sites listed below for the owners; area SE banks NOT converted (item 6).
- Type map (from arcs): 4U MSS 6e171a6e -> GU 10ebe843 (sound\call\em\emNNN); 4U SNDB 14b5c8e6 -> GU 15d782fb
  (bank, sound\se\em\emNNN_00\snd_emNNN_00); 4U SREQ 2618de3f -> GU 1bcc4966 (request, same path); 4U MADP
  67195a2e -> GU 79c47b59 (wave, ...\wav\<name>). GU SE base = MHGU_Editor/scratch/base_romfs.bin.
- [x] 1. formats (C, from Capcom's own 4U->GU conversions: 4U em031 Kushala -> GU em024_00 and 4 more pairs, 43
  pairs for request statistics; GU loaders SRQR 0xb67a0c, MSS 0x4d9c7c). Full field map in the tools/snd4u2gu.py
  docstring. Waves: both games mono DSP-ADPCM -> data copied bit for bit (header rewrite, 4U rates 8-16 kHz kept).
  Bank: records/entries reorder only (key moved to the entry end). Request: 92 -> 132 B entries, w5 category remapped,
  common-bank entries (ids 311..345, bank 1) taken from GU Kushala (4U snd_common -> GU snd_com_qst). MSS: identical
  layout, version 0x20120123 -> 0x20131015 only.
- [x] 2. tools/snd4u2gu.py: `convert` (-> dump/converted/em089/snd, 72 files: call, 69 waves, bank, request),
  `wav DIR` (decode for listening), `selftest`; build_em089_arc.py imports `em089_entries()`.
  DEVIATION: request volumes -2 dB (Capcom's dominant GU re-level of 4U requests; `--keep-volume` = 4U values).
- [x] 3. trigger mechanism (C). DATA for almost everything: the MSS sound call (field 12) keys request IDs to
  motion frames (1731 events in 144 motion records: footsteps, wings, voices, tar), the engine's generic reactions
  (hits 311..345, flinch / roar voices by standard IDs) use the request (field 13). The em089 handlers have NO direct
  sound calls; CODE sites (all 4U callers of the sSoundControl queue in em089 + uShell050):
    em089 0x8c352c (slot 40 tar helper) id 203 joint 2; slot 64 0x8c67c0 tail first break id 0 joint 143;
    uShell050 slot 22 spawn 215 (kinds 2-5, follows shell); slot 23 map impact 216 (kinds 0,1,6-9) / 217 (2-5) at
    the impact point; slot 50 re-arm 207 (2,3,7,9 follows) / 208 (4,5,8 at pos), kind 6 arms 58 f; slot 51 kind 6
    timer -> 220 at pos. (The shell agent's "0xd8/0xd9 impact" = 216/217, confirmed; 207/208/220 are slots 50/51,
    not ported in em089_shell.c.) GU API (same queue, same args, as GU shells/monsters call it): 4U 0x2fcc50 ->
    GU 0x4efd74, 0x304d3c -> 0x4efe58, 0x312484 -> 0x4efb98, mgr *(main+0x1896f5c), area = unit+0x1054.
  module/em089_snd.c/.h (new, in build.py): em089_snd_joint/obj/pos + named helpers. Compiles (80352 B).
  CALL SITES for the owners (main agent wires): em089_act.c:2375 `em089_snd_tar_chest(self);` (replace the stub);
  em089_break.c:151 tail branch `em089_snd_tail_break(self);`; em089_shell.c shell_setup after shell_init:
  `em089_snd_shell_spawn(self, owner, kind, FIELD(uint8_t, self, SH_AREA));`; shell_move impact branch before
  shell_kill: `em089_snd_shell_land(self, FIELD(void *, FIELD(void *, self, 0x136c), 0xc), kind, pos,
  FIELD(uint8_t, self, SH_AREA));` (owner = param+0xc, as 0x4a1b6c reads it). (slots 50/51: see item 7)
- [x] 4. BGM DONE (tools/snd_bgm.py `all`, ~3 min). Findings (C):
  4U: bgm_em089.mca (id 32, 0.0 dB) / bgm_em089_2.mca (id 33, -0.9 dB) in bgm_bat.stq; 4U picks 33 when sound
  state +0x1838 == 1, set by 0x309004 when the em089 has work+0xca == 1 (phase-2 roar; module F_SHAKE); state 2
  (0x6a1b40, an event) -> id 29 = bgm_Eiyu (not ported). MCA = stereo MADP v5, DSP-ADPCM interleave 0x100.
  GU: boss theme id = 0x4e60d4(ctl, entry {u16 em descriptor, .., u16 unit key @+6}, u8 *has, u32 *id), a switch on
  em 12..88 (Kushala 24 = bgm_em024_Daola); em > 88 -> map default; id looked up in bgm_bt.stqr (ids = sequence w0,
  140-B sequences, stream index @+92, dB @+36). GU .opus = Capcom header + Nintendo Opus (CELT 20 ms stereo CBR 240 B,
  pre-skip 120, per-packet final range: verified 20/20 against libopus) -> encoded with system libopus via ctypes.
  Plan: opus bgm_em089_Gogmazios1/2 + 2 streams/sequences (0x900 / 0x901) APPENDED to bgm_bt.stqr (all GU entries
  byte-identical), hook 0x4e60d4 in new module/em089_bgm.c (em 0x59, or 0x18 in quest 11491 -> 0x900; 0x901 once
  F_SHAKE is set). Arena: dump/converted/bgm_m28.json + m28d/wav/m28a0{0,1,2}d.opus (4U a00/a01/a03).
  Result: module/romfs/nativeNX/sound/bgm/battle/wav/bgm_em089_Gogmazios1.opus (115.6 s, loop 456405-5550098 @48k),
  ...Gogmazios2.opus (93.8 s), battle/bgm_bt.stqr = GU's 61 streams / 63 sequences byte-identical + streams 61/62,
  sequences 0x900 / 0x901 (template = GU Kushala's sequence). Levels: GU dB = 4U dB + median(GU - 4U) over 6 themes
  present in both games (rms measured on the decoded audio) = -1.48 -> -1.48 / -2.38 dB. Opus round-trip SNR 18-20 dB.
  module/em089_bgm.c + build.py hook ('bgm_select', 0x4E60D4); compiles (84936 B). Log: `gogport: em089 bgm theme 900`.
  Arena: m28d/wav/m28a00d/01d/02d.opus + dump/converted/bgm_m28.json written; `stage4u2gu.py alias` re-run -> m28d.arc
  STQR streams 0..2 = ours (report row "streams -> m28d..."); stream 3 stays Fortress's.
  Stage jingle (round 2): 4U bgm_st_19 = 1 stream bgm_map_19 (28.5 s, no loop) at request 10 (-2.7 dB, w1 = 1),
  the same shape as every 4U bgm_st_NN (request 10 = bgm_map_NN). GU counterpart = the camp jingle mNNcmpd.opus
  (19 maps, 20-30 s, no loop) at map-STQR request 0x32 (category w1 = 1); GU sSoundControl requests 0x32 from the map
  STQR slot at 0x4de5fc (0x4e3478(ctl, 0, 9, 3, id 50)). Fortress m26d has none -> m28cmpd.opus (new) + stream 4 /
  sequence 0x32 (template GU m09d's, -2.7 + -1.48 dB) in dump/converted/bgm_m28d.stqr = full replacement of the
  m28d.arc STQR (handed to the arena-2 agent to pack). The condition before 0x4de5fc wasn't traced.
  Eiyu (4U state 2), traced (C): set by uShell020 slot 29 0xc74a3c (vtable 0xe6db4c): a uShell020 of kind (+0xfd) 9
  that hits a monster of em type 89 while the BGM state is 1 (phase 2) -> state 2 offline (0xc752e8), or net message
  type 33 online (0x6b27d4 -> receiver 0x6a162c case 33 -> 0x6a1b40). The only local uShell020 poster (0x6621a0,
  from 0x835d08) passes kind byte 101; nothing writes kind 9 locally, so the kind-9 creator wasn't found and has no
  GU counterpart -> NOT ported (em089_bgm.c returns ID1/ID2 only).
  [-] Settled (follow-up): the check sits in uShell020's per-frame 0xc74b78 (called 0xc754ac; slot 29 0xc74a3c is
  a 9-instruction stub), r4 = the shell for the whole function, so +0xfd is the SHELL's own kind (read before r4
  becomes the hit target shell+0x1f8). The kind comes only from the ctors: 0xc74520 (param ctor, +0xfd = param byte
  +4) and 0xc749c4 (+0xfd = 0); no other uShell020 code writes +0xfd. Param byte +4 = r2 of 0x6621a0 = 0 at both
  call sites (0x835d88 / 0x835dc8, the player function; its r3 = 101 lands in the u32 at +8, not the kind). So every
  4U uShell020 has kind 0: the kind-9 / em089 / state-1 branch (state 2 = bgm_Eiyu) is unreachable in 4U's code as
  shipped (the online message 33 carries the same local condition) -> nothing to port. The 4U Eiyu stream was not
  converted. Factory check (2nd follow-up, C): the factory 0x660e88 is a 60-way switch on r1 (shell id); all 81
  callers pass a constant id. 0x661bb4 passes r1 = r4 = 0 (set by mov r4, #0), and the wrappers 0x662664 / 0x6629bc
  / 0x662b44 pass constants 36 / 37 / 46 / 51 / 52. Only 0x662204 (inside 0x6621a0) passes 20. Case 20 (0x661330)
  is reached only from that switch. The only other creation path is the DTI newInstance 0xd0f238 (DTI vtable
  0xe7fe24), which leaves +0xfd at the base ctor's 0. No stage, gimmick or item table can bypass these, since the id
  is always an immediate at the call -> [-] stands.
  RISKS: bgm_bt.stqr is the BASE RomFS file (v1.4 lists the same 61 battle streams; contents not comparable without
  NCA keys); GU's marker table (opus header, optional) written empty.
- [x] 4b. TEST 2 FIX (no music, 2026-10-19). Cause (C): GU loads `sound\bgm\battle\bgm_bt` from
  nativeNX/loc/arc/quest.arc (arc scan: every STQR lives in an arc: quest.arc bgm_bt + event_quest, resident.arc
  bgm_com, stage/village arcs the map ones), so our loose bgm_bt.stqr was never read. bgm_select returned 0x900, and
  the lookup in GU's bgm_bt failed, so no battle theme played at all. Fix: em089's own STQR
  `sound\bgm\battle\bgm_em089` (2 streams, sequences 0x900 / 0x901; snd_bgm.py build_em089_stqr ->
  dump/converted/bgm_em089.stqr) packed into the em089 arc (file 0x10725 = EM089_FILE_BGM_STQR, appended; arc
  +1 entry, files.inc +1 define +1 row, nothing else changed; ARC LOCK taken + released); loose bgm_bt.stqr deleted.
  module/em089_bgm.c: hook ('bgm_stqr', 0xB6D72C) = rSoundStreamRequest get-by-id: for ids 0x900/0x901, r0 :=
  our STQR resource (0x152960(0, 0x10725)). All 52 callers re-resolve (stqr, id) and then read only entry fields
  (+8, +32, +0x88 pre-resolved stream object), so the redirect is consistent. bgm_select now keeps GU's theme when
  our STQR isn't loaded (no more silent fallback). Log-only hook ('bgm_play', 0x4E34A4): every stream play request in
  quest 11491 (slot, id, follow-up, STQR pointer). gogreport.py: new "sound / BGM" section (bgm theme / stqr lines,
  play requests by slot+id, code SE counts). Both build variants compile, 0 warnings.
  Area music: the alias STQR in m28d.arc is consistent (byte-identical to dump/converted/bgm_m28d.stqr; sizes, samples,
  loops match the loose opus; format byte-identical to GU m26a00d apart from the date stamp). No fault found in our
  files. Note: in both games these area streams are ambience (rms -25..-29 dBFS, played at -6 dB; GU Fortress the
  same). 4U Battlequarters has no area music, only the bgm_st_19 jingle, which is now the 0x32 camp jingle. The
  next log will show whether GU requests them: `bgm play ... slot S id 0..2 / 32`.
- [x] 5. arc rebuild (lock taken + released): tools/build_em089_arc.py imports snd4u2gu (`--donor-sound` = old
  Kushala sound), run with `--cmdtbl gog` (as before). Arc 953 -> 1025 entries (+72 sound, 0 changed / removed, old
  order kept). em089_files.inc: FILE_COUNT 30 -> 32, manifest[12] 0x7a5d -> 0x1071e (sound\call\em\em089),
  manifest[13] 0x7a5e -> 0x1071f (sound\se\em\em089_00\snd_em089_00 request), two file-ID rows appended; every
  other ID identical. NOTE for later rebuilds: keep `--cmdtbl gog`.
- [x] 6. Area SE converted (round 2, tools/snd_area.py, format in its docstring). PACKED by arena-2: stage4u2gu.py
  alias reads area_snd.json (a00 -9 Fortress / +6 ours, a01 -41 / +8, a02 call only) and bgm_m28d.stqr as is;
  `--keep-sound` = Fortress area sound + old STQR handling (bisect if the empty a02 SES upsets the loader).
  SES decoded from 596 4U + 1205 GU records: same record, GU inserts one word after the radius (u16 0 | u16 x,
  0 in 517/650 records) and the 4U u16 near/far pair moves to the next word; table at 0x10, record = header + path[64]
  + n points. 4U Battlequarters calls: a00 4 emitters (river, cave wind, camp fire) + reverb zone, a01 5 + reverb,
  a03 (arena) reverb zone only. Converted: a00 <- m19a00d, a01 <- m19a01d (bank + request + waves + call, Fortress
  paths); a02: call only (0 emitters) because GU's a02 bank/request = Capcom's conversion of 4U m19a03d (request
  IDs 40-61 / 304-336 match, my rules reproduce them) that the GU gimmick code uses. snd4u2gu.bank_rec_gu now keeps
  stage groups without bit 15 unchanged (as Capcom's a02). Output: dump/converted/area_snd/ + area_snd.json (remove /
  add list per arc). DEVIATIONS: reverb/EQ zones (type 3/4 records naming 4U REV 'snd_M19d') dropped: REV v2 vs GU
  REVR have different layouts; GU word x written 0; request volumes 4U (no -2 dB); footstep banks (pl/otomo fs) not
  carried (GU area arcs have none). Risk: a zero-record SES in a02 (GU's smallest has 1).
- [x] 7. Blob sounds, slots 50/51 (round 2): those slots are NOT uShell050's. Its vtable 0xe6e86c holds two
  28-slot tables, and slots 50/51/52/57 are slots 22/23/24/29 of uShell051 = the ground SPLASH uShell050 posts.
  Subtypes 1/6/16/17/19/20 have no init sound (table 0x1031bfc = -1); 6/17/19/20 (blob kinds 1, 3, 5, 7, 8, 9)
  play id 220 at the splash 58 frames later. Ported as em089_snd_splash(owner, subtype, pos, area), called by
  em089_shell.c at a ground impact (subtype table k_splash), + a 16-entry delay queue advanced by
  em089_snd_tick(owner, dt). WIRING NEEDED (em089.c owner): call `em089_snd_tick(self, dt)` once per frame in the
  monster update (dt = the per-frame time step em089 already uses). em089_snd_shell_rearm/_timer removed (wrong
  attribution). Deviation: 4U needs the splash to still be alive at frame 58 (its lifetime isn't ported). Compiles.

## Arena 2 (arena-2 agent)
Owns tools/stage4u2gu.py, sdl.py, sbc.py, sis.py, m28 romfs files, new module/stage_*.c, notes/stage.md (section 12).
Shared: module/stage.c, tools/build_gog_quest.py (small edits). Status 2026-10-18: STARTED.
- [x] 1. Dragonator (C): 4U aMap19 setup 0x6594b4 -> 2 uStageGimmick type-2 spears (gekiryusou) at (+-495, 800, 4105)
  yaw pi; GU st003 motion = 4U's (0x33c7c8 constants). Alias: st003 FUP vec 3/4 + sh001 (0, 180); new
  module/stage_gimmick.c hooks stage_spear_count @0x502694 (2 spears), stage_siege_phase @0x3a5ec4 (GU stage-26
  Dragonator waits for siege phase 3 -> answered 3 for lr 0x503d58), stage_dragonator_fire @0x503bb0 (log);
  build_gog_quest.py --bq ships questPlus_1491 (mIsGekiryu 1, start 0, reuse 600 s = 4U 10 min). Switch = converted
  SIS kind-5 point (GU ready check 0x503b88 / fire 0x503bb0). Sever link: report to break agent (see final report).
- [x] 2. Monster pathing (C format / S rules): relation\m26\m26a01 / a02 GENERATED from the converted 4U collision
  floors (stage4u2gu.py relation_*; XFS serializer reproduces Capcom's files byte for byte). Rules from all 78 GU
  tables: direct pairs ledge<->ground 1 + same-height ledges sharing vertices, attr by height (1 walk / 2 ~500 /
  4 ~1000 / 8 big), BFS ascending paths (1095/1170), attr = first non-walk hop (472/472). Re-generating Fortress
  a01/a02 gives Capcom's topology + paths exactly; attr differs only on 2 special floors (Capcom 16 / ramp 4).
  Arena: 1-2 4, 1-3/1-4 walk (ramps), 1-5/1-7 8, 1-6 4, 2-3/3-4 walk; a01 = floors 0/1. `--keep-relation` = Fortress.
- Eiyu lead (main agent): 4U uShell020 is only created by player code 0x835cf8 (factory 0x660e88 case 20 via
  0x6621a0, kind byte 0, r3 101); no stage gimmick (uStageGimmick spears / pile) spawns shells.
- Sound agent request DONE: stage4u2gu.py area_sound() (area_snd.json) + bgm_m28d.stqr; `--keep-sound` fallback.
- [-] 3. Cart travel: GU st006 = siege one-way rail trip (path frames 0-800/1000-1800/2000-3000 area 1, 4000-4800
  area 2, state byte 0..13 + net sync, 0x495c20/0x496500); 4U cart = KowareObj mType 21 auto-chained 8-action loop
  (0x1cf090 -> 0x1cf55c). Different drivers -> parked at 4U north station (unchanged). [~] s03/s04 cannons: models
  s05..s10 drawn static in their frame-0 pose (no firing: GU st008 is a different cannon).
- [~] 4. Side doors a02/a03 + sinking wall a04 drawn static (frame 0) as uStageSet clones in the arena set scheduler
  (`--keep-doors`). [-] gate (frame-0 rot x -1.134, uStageSet has no rotation), lever s01 / s02 / pile bunker (4U:
  player interaction -> 0x5ba3cc case 36 -> 0x6a1f18 bit 1; type-3 controller 0x33bdf8 plays KowareObj 24/25 action
  39; pile = type-2 sub 3, em089 SE 218/219): no GU interaction kind / shell -> would need new code. Details:
  notes/stage.md section 12.
- [x]/[-] 5. Sky motion: none in 4U data (constant transforms) -> nothing to port. [-] rain variants (GU loads only
  "-f"), camp camera presets (SCD v0x13 vs XFS, no converter).
Status: DONE (static; nothing run in game). Test recipe additions: notes/stage.md section 12 "Test recipe changes".

## Pre-test review (review agent)
Static crash / hang / corruption review before the one in-game test (2026-10-18 ~09:00-10:00; files as of then).
Both build variants compile (`GOG_MOD_ROOT=/tmp/rvx python3 module/build.py`, + `GOG_DEFINES="GOG_STAGE_ALIAS
TEST_HP_PCT=45 TEST_RAGE=60"`), 0 warnings per file with the build's CFLAGS (build.py hides warnings).
Checked OK (no change needed):
- uEm089_00 layout: F_* in em089_act.c tile +4..+0x97 without overlap, F_END = +0x98 = EM089_SIZE; em089_bgm.c's
  EM089_F_PHASE2 (+0x25) = F_SHAKE; no other file adds object fields (tar / break / efx / aim / snd / cart keep
  per-monster state in static tables keyed by pointer). Shell classes: em089_shell.c last field +0x48 < +0x50,
  shell016 S_HIT float[4] +0x3c..+0x4b < +0x50, shell051 +0x24 < +0x30, shell005 +0xc < +0x10.
- Vtables: uFestaEnemy 286 and uShellEnemy 83 slots verified in main (next words 0, 0, 0x32c = next vtable
  header); overrides em089.c {1, 5, 118, 119, 125, 127, 129, 130, 132, 133, 168, 253}, shells {1, 5, 9, 16, 79},
  no duplicate writer, all in range; DTI vtables 3 slots.
- Hooks: all 26 HOOKS entries have a `_c` handler (link would fail otherwise); build.py's displacement / branch-in
  checks pass. Mid-function sites (dmg_sub 0x98af4, dmg_special 0x98ac4, stage_spear_count 0x502694,
  stage_cart_tick 0x495d0c): no condition flags / FPSCR live across the trampoline (flags are set after the site
  or the site follows a bl). Only recursion: em_arc_request_c -> 0x15334c with 0x59 -> passes through (one level).
  Gating: stage_path / spear / siege / dragonator / cart hooks need stage_alias_active() (GOG_STAGE_ALIAS + quest
  11491); bgm_select only for em type 0x59 or (0x18 and quest 11491); set_action / dmg / setHP hooks only log
  for EN_ID 0x59 (cheap reads for every enemy).
- Relocations: 165 R_ARM_RELATIVE, all in .data / .got (writable); none in the R-- segment (pointer tables like
  k_seq_2_1 / s_ported land in .data.rel.ro -> .data via link.ld). rtld relocates them; "no data relocs" comments
  in efx / tar are caution, not a build restriction.
- em089_files.inc: all 37 (path, type) pairs exist in module/romfs/nativeNX/arc/enemy/em089_00.arc (1109 entries)
  and every hash = ~crc32(path) (scratchpad arccheck.py). bgm_bt.stqr: 63 streams / 65 sequences, appended ids
  0x900 / 0x901 -> streams 61 / 62, opus sizes match the stream table.
- Logging: every per-frame logf is capped or change-triggered (tar_advance: 2 lines / 300 calls; dmg_special
  every 600; stage_path alias line per path request only). Loops: all bounded; em089_slot75.inc has one backward
  goto (into a straight block ending in `goto end`), curve_eval terminates on the -1 sentinel of every table.
- Player / owner pointers: hunter_model / target_pos / listener_pos null-check the player chain and its joint
  tables; shells read the owner through param+0xc only after uShell_move (engine owner check, same as GU shells).
  EN_CONTROLLED (this+0x7420) must be non-zero for the AI think check 0x82538 to pass, so 7/45's "wait for
  control" step cannot stall in solo.
FIXED:
- [x] em089_efx.c (+ em089_efx.h, em089.c ctor / slot 1): static effect state (s_s016 / s_aura / s_s75 keyed by
  the monster pointer, s_efx_owner) survived the monster. A quest retry allocates the new em089 at the same
  address -> aura_tick polled / stopped the previous quest's freed effect (`em089_efx_stop` on a stale pointer if
  the quest ended in phase 2 with the aura on); s_efx_owner dangled for the stage posts. New
  em089_efx_forget(self) zeroes every slot keyed to self (without touching the effects) and clears s_efx_owner;
  called from em089_ctor and em089_delete.
RISKS LEFT (not changed; severity for the one test):
- [medium, other quests] main.c em_arc_request_c requests our 19 MB em089_00.arc whenever Kushala's (0x18) arc is
  requested, in EVERY quest with Kushala (+19 MB resident; GU memory is tight in multi-monster quests). Gate on
  gog_quest_id() == 11491 if the quest ID is known at that call (comment says it is not; stage.c says the
  accepted-quest ID is valid from board accept on - worth checking which caller 0x3b512c is).
- [medium] Effect handles are raw uMHProofEffect pointers polled with em089_efx_alive (state at +0xc) - the GU shell
  pattern, but if an effect is freed between two polls (owner not updated that frame, area change) the next poll
  reads freed memory, and a reused block that looks alive gets 0x32a400 called on it. Affects em089_shell.c S_EFX
  (deferred slot-16 kill), shell051 S_EFX, aura, shell016 slots. GU's own EmBase shells (0x3fa540) wait on a handle
  the effect system clears instead. Watch for crashes inside 0x32a400 / 0x31c... in the log.
- [low-medium] em089_efx_stage_efl_on(n, unit) (new, effects agent): the effect is attached to a stage unit; that
  unit must outlive the effect (same rule as the blob shells) or the effect reads a freed attach model.
- [low] em089_00.arc: 1109 entries / 19 MB; no GU arc entry-count limit known to have been tested at this size.
- [low, retry only] address-keyed statics in em089_act.c: TEST_HP_PCT (s_hp_set) and TEST_RAGE (s_rage_self) are
  not re-applied to a new em089 at the same address (retry starts at 100 % HP, no forced rage); damage / phase
  logs not reset. stage_cart.c s_c keeps leg / station / frame for a new cart at the same address (cart appears at
  the previous quest's station, or finishes the old leg). Neither crashes.
- [low] em089_bgm.c: `type == 0x59` / `0x18` is tested on the entry's low byte without the kind nibble
  ((e[0] >> 8) & 0xf); kind-4 entries use the low byte for something else (0x4e60e4). Harmless unless such an entry
  has low byte 0x59 / 0x18 (0x18 only in quest 11491).
- [low] tar_meat (Gas) points rec+0x418 rows at module rodata (R-- page): any GU write into a hitzone row would
  fault (none known; GU swaps row pointers).
For other agents:
- effects agent: em089_efx_forget() is now at the end of em089_efx.c; keep it (and extend it) if you add more
  self-keyed static state; a full-file rewrite must carry it over (em089.c calls it).
- arena-3 agent: stage_cart.c state is keyed by the st006 pointer only (see above); consider re-init when the
  quest changes (e.g. gog_quest_id / stage load), and only post stage effects through em089_efx_stage_* (they now
  return 0 after the monster is deleted).

## Arena 3 (arena-3 agent)
Owns module/stage_gimmick.c, new module/stage_*.c, tools/stage4u2gu.py, sdl.py, m28 romfs, notes/stage.md (section
13), module/em089_break.c (task 1). Status 2026-10-18: DONE (round 1; static, not run in game). Test: rebuild
`python3 -I tools/stage4u2gu.py alias` (only map_com m28.arc changes) + module; expected logs in stage.md 13. Scratch tools: scratchpad/ar3/gl.py (GU listing
with PIC literals), fs.py (containing function + callers), dtt.py (dttune sever table survey, scratch venv).
- [x] 1. Spear sever link (C, no change needed): GU sever counter 0x97ddc part loop: slot 141 (base 0x6bf5c = 1)
  -> row = 0x711f8(this, p) = dttune+0x68 row + 2 -> [row+2] limit vs sever count rec+0x3bd+12p, row+4 / row+5 =
  damage KINDS looked up by 0x710f0 in the 3-byte list dttune obj+0x6c -> accumulator rec+0x498+16*idx+2p.
  Accumulators are fed by 0x9d6f8 (kinds 126 AND 127 for EVERY part hit; called by all 5 hit handlers
  0x171350 / 0x172b18 / 0x17394c / 0x174b48 / 0x1769f8 of the dispatch 0x170968) and 0x9d8b4 (kinds 0..17). So 126 =
  "any damage", not a Dragonator kind; the st003 hit (attack type 0x20) reaches 0x9d6f8 like every other hit. 4U
  is identical: 0x921f?? adds the hit to kinds 126/127 (0x921fc4 / 0x921ff0, lookup 0x933e08 in a 2-byte list =
  etd word 6), plus 0x9178e8 (special damage) to 126. em089 4U list (etd+0xf0) = [1, 126]; our dttune +0x6c =
  donor Kushala [126, 1, -1] = same kinds (index order irrelevant); part-1 row (600, 1, 126/-1, 1200) = 4U's. ->
  part 1 detaches after 1200 damage of any source on part 1 incl. Dragonator hits, as in 4U. GU survey: 126 is
  the horn/head kind of Kushala, Teostra, Lunastra..., 1 = cut (tails). No dttune/arc change -> no ARC LOCK use.
- 4U interaction plumbing (C, needed for 2-4): player query 0xd059d8 -> nearest interaction record (list
  stage+0x481c, 148-B records, +0x34 pos, +0x4c r, +0x50 h, +0x54 KIND) -> player case table 0xb0efc4. Record kinds:
  SIS point kind k -> table 0xfb8ab8[k] (0x5b9988; SIS 3 ballista -> 8, SIS 5 Dragonator -> 11); kinds 30..36 =
  gimmick interactions, executed after the player motion by 0x5ba3cc (30..34 -> 0x6b93b0 type 1..5, 35 -> 0x6b91b4
  type 6, 36 -> 0x6a1f18 pile). [0xfb6b7c]+0xc8c low byte = STAGE number (19 = m19); +0xc90 = area.
- [x] CORRECTION 2026-10-20: the pile bunker IS reachable: em089's falling Dragonator spear creates the kind-36
  record itself (0x926044, `cmp r9, #3` / em 89 -> +0x54 = 36 at 0x926294), ported in module/em089_pile.c (see the
  content section). The survey below missed that registrar.
- [-] 2. Pile bunker: NOT REACHABLE in 4U m19. Its only trigger 0x6a1f18 (sets +0xdd29 bit 1, one-shot: re-arm
  0x6b0ce0 skips bit 1) runs from interaction kind 36, and no kind-36 record is created: registrars of +0x54 =
  0x5b9fec (callers 0x5b921c / 0x5ba4e0 pass 30..35 only), SIS table (<= 17), item-pop data 0x5b93c4 / 0x5b9d40 /
  0x5ba9c0 (m19 IPS/IPL kinds 0), 0x25ddb4 (19..26), 0x1a0560, enemy/shell 0x9357ec (callers outside em089). The
  sub-3 gimmick (0x33c7c8 r6 = 1) only plays em089 SE 218 / 219 (no attack enable: 0x1a4814 runs for sub 0 only)
  and em089 code never reads bit 1 (only bit 0 via 0x6bc67c = "Dragonator fired", em089 0x8b46d4 -> behaviour
  agent). Not ported (porting it would add a gimmick 4U players never get).
- [-] 3b. Floor cannons s03/s04 (traced, not ported: needs own prompt + cannonball + uShell022-9 projectile; see
  stage.md 13) (C): 0x5b921c (m19 only) registers 2 kind-35 records at (2050, 0, 1230) angle 49152
  and (-1575, 0, 1230) angle 16384, r 100, index 24 / 25 -> player interaction 11 (0xb0f424: ready 0x6b1a58 on the
  carried item kind 1 / 2 = cannonball, action 171) -> 0x6b91b4 type 6 -> KowareObj (mType 23) action via
  0x6aafec (net). = player-loaded cannons. GU counterpart st008 (Fortress siege cannon, ONE instance at mgr+0x34c,
  pos/angles from st008 FUP, spawned per SIS kind-6 point; models 0xd42d/0xd42e).
- [x] 3a. Rail-cannon cart PORTED (module/stage_cart.c, hooks 0x497040 / 0x495b40 / 0x495d0c; stage4u2gu.py
  edit_cart_path = 4U s00 keys, edit_st006 FUP 6/7 = 0/800; m28.arc rebuilt, other alias arcs byte-identical;
  build.py +3 hooks +1 source; both variants compile, 0 warnings). GU st006 = Capcom's port of the 4U cart (same 5
  interaction points, table 0x18929a0); only the track differed. Details / deviations / logs: notes/stage.md 13.
  Original trace: (C, corrects arena-2): NOT self-driving. 0x5b9a8c (m19, area 3) -> 0x5ba4e0 registers
  5 cart-relative records: kind 33 (340, 165, 170), 32 (-340, 165, 170), 31 (0, 165, -105), 30 (+-280, 0, -415).
  Kind 32 -> 0x6b93b0 type 3 -> KowareObj cmd 32 (0x1d290c: next action = station + 47), kind 33 -> cmd 33
  (station + 43); 50-frame delay (0x1d2a0c) unless immediate. Action ids 43..46 / 47..50 = legs (scheduler s00
  frames 0-800 .. 12500-13450). Station getter 0x6b8b8c. Kind 31 = rail-cannon charge / fire (type-3 controller
  0x33bdf8 at the kind-31 record: KowareObj 25 actions 40/42/44 = charge level, 39 + lever 24 action 39 + shell
  via 0xc08698). Cart action end 0x1cead4 -> 0x1d1318 enables the station's records.
- [-] 5. Camp camera: SCD v0x13 layout decoded (stage.md 13), not converted (camp only, GU XFS reader not traced).
- [-] 4. Doors/wall (traced, not ported: runtime KowareObj action API in GU not traced; visual + 135-wide slab) (C): m19 per-frame 0x6b70cc: KowareObj (area 3, mId 3 = scheduler a01: doors a02/a03 swing
  0 -> +-pi/2, wall a04 sinks y -360, 200 frames, SE 309-312) plays action 0 via 0x6c3400 when boss HP%
  (0x6ae768 = HP*100/max of the first large monster) <= 40 and remaining time ([+0xad5c] min * fps * 60 -
  [+0x803c]) > fps * 600 (quest 1002: HP <= 50; 62211: <= 90 and > 1 min); then HUD message 0x5aa0f0(21) once.
  Collision groups linked to object 3 (w1 byte 2 = 3): w00 part 6 grp 36, part 5 grp 37 (x 631..766, z -4710).

## Arena 4 (arena-4 agent)
Owns new module/stage_cannon.c, module/stage_doors.c, tools/stage4u2gu.py, tools/sdl.py, m28 romfs, notes/stage.md
(section 14). Scratch: scratchpad/ar4/. Status 2026-10-18: DONE (static, both module variants compile, 0 warnings;
romfs a02.arc / m28d.arc / map_com m28.arc rebuilt, a00/a01/a03 byte-identical). Details + logs: stage.md 14.
Also taken over from arena-2: GU's quest-start command 0 blocked for the k01/k02 breakables; stage_cart.c EFT_AREA 2.
Done on the side: stage.c exports stage_setup_serial() (bumped in the 0x50249c spawner hook = once per stage load);
stage_cart.c re-inits its state when it changes (pre-test review request).
- [x] 2. Doors / sinking wall a01 PORTED (static, compiles 0 warnings): stage4u2gu.py convert_doors / edit_kod (m28d.arc
  + m26a02d-k03 and its 3 models, a02.arc loses the static door clones, map_com kod + entry; `--keep-static-doors` =
  old clones), module/stage_doors.c (hooks stage_frame @0x503c7c = per-frame tick for doors + cannons,
  stage_kobj_bcast @0x500d18; define STAGE_DOORS_OFF). Logs `gogport: stage doors: ...`. Findings (C):
  - GU KowareObj = 4U's (Capcom port). uKowareObj ctor 0x51155c (vt 0x176a840); fields +0x182 area, +0x183 cnt,
    +0x184 status, +0x185 current action (255 initial), +0x188 mId, +0x189 mType, +0x158 its scheduler, +0x140
    action list (KowareActionParam +0x30 Id, +0x31 moveType, +0x28 moveFrame, +0x2c startFrame, defaults moveCnt 1).
    Registered in mgr [0x18977a0]+0x21c[24] (0x500d40), count +0x27c. Command 0x514f9c(kobj, cmd, a, b): cmd 0 ->
    play action Id 0 (0x515328) = 4U 0x1d23a0 cmd 0. Action start 0x513d3c: scheduler frame = startFrame, end =
    +moveFrame, quake if quakeType != 255; Id 0 start toggles collision PART ids 2*mId-1 off / 2*mId on (init: 2*mId-1
    on, 2*mId off) via 0x4ffdc4(mgr, area, partId, en) -> 0xc46cfc (4U: same code 0x1cd494, 0x6c675c -> 0x177c5c:
    link = SBC part id, not group w1 byte 2). Doors a01 mId 3 -> parts 5 (wall slab grp 37, on) / 6 (grp 34/36,
    off) of a-w00 (+ w00-shell parts 9/10) -> GU does the 4U collision swap itself.
  - Creation: 0x4fe9c0 creates per area k01..k04 schedulers, file id 0xbbdf + stage*52 + area*4 + k-1 (0x500bb4);
    m26a02d-k03 = 0xc131 exists in the GU file table (Fortress ships no such file) -> ship the converted 4U a01 as
    stage\m26d\m26a02d\sdl\m26a02d-k03 in m28d.arc. kod (map_com table\stage\kowareObjData\m26d, mgr+0x3fc): f32 1.1,
    u32 n, n x {u8 area, u8 mId, u8 idx, u8 type, u16 vital}; type-0 lookup 0x5011c0 -> state bit idx in mgr+0x280
    (0x501864) = 4U table A 0x6c55d8 m19 [(3, 3, 0)] -> add {2, 3, 5, 0, 100}.
  - GU quest start (0x42e8 -> 0x500cb4, non-siege + host) sends cmd 0 to EVERY kobj -> blocked for every area-2
    kobj of the alias (doors + arena-2's converted breakables k01/k02, whose action Id 0 = frames 20..25 would
    show from the start) in the 0x500d18 hook (r1 = 1 = no-op command). 4U m19 stage start 0x6c222c plays nothing
    on them (0x1d0c64 pre-breaks k01..k03 for quest 1002 only).
  - 4U trigger (0x6b70cc, m19 only): kobj idle && not done && HP% (first large monster, HP*100/max) <= 40.0 &&
    ELAPSED (limit min * fps * 60 - countdown +0x803c) > fps * 600 -> 0x6c3400(stage, 3, 3, cmd 0, 0) + HUD
    0x5aa0f0(21, 0) once (stage+0x1c bit 2). Quests 1002 (50 %) / 62211 (90 %, 1 min) special. CORRECTION of
    arena-3 ("remaining > 10 min"): +0x803c / GU sQuest+0x1c is the remaining-time COUNTDOWN (GU 0x3a0160
    decrements it per frame; 4U re-arm 0x6b0f18 needs a countdown). GU: elapsed = [sQuest+0xcc] *
    int([[0x2126764]+56]) * 60 - [sQuest+0x1c] (0x61cff4); HP: sEnemy [0x1851fe0] slots 0..9 (0x5ceb4), enemy
    +0x1428 rec (HP +0x370 / max +0x374), +0xb5f7 small flag.
  - HUD: kind-1 message table = 4U QDialog (lmd) / GU QuestDialog (GMD): id 12 = Dragonator ready in both. 4U 21 =
    "All clear to use the Demolisher!"; GU has no such line (GU 21 = "Quest failed...") -> GU 93 "The Demolisher is
    ready for use." via 0x65dd68(1, 93, 0) (GU Dragonator uses 0x65dd68(1, 12, 0)). DEVIATION (text).
  - a01 effect controller: CreateKowareEft index 16 (m19a03_008) at scheduler frame 2, world (0,0,0), area 3 (GU 2),
    group 0 (4U 0xc0afa8: pos = KowareEftPos as is). SoundControl (mSdlSeReq*, SE 309..312) is understood by GU.
  - 4U old-schema a01: kowareModels carry Draw 0 (4U's visible cart/gate models too) -> GU Draw 1 (GU k models).
  - BUG found in stage_cart.c: EFT_AREA 3 = 4U area; em089_efx_stage_kowareeft compares with GU playerArea() (arena
    = 2) -> the cart's m19a03_001 never posts. Fix: 2.
- [~] 1. Floor cannons s03/s04 PORTED (projectile = GU uShellPlcom_009 variant 1 = Capcom's own port of uShell023
  kind 1: HDS / HTS / FUP / 125-per-frame flight / stick logic checked against 4U, see stage.md 14; left: bonus shell
  life 120 vs 60, prompt = GU kind-11 switch prompt): stage4u2gu.py CANNONS_KOWARE (s03 -> m26a02d-k04, s04 ->
  m26a03d-k01 path, models s05..s10 in m28d.arc, static clones gone; `--keep-static-cannons`), module/stage_cannon.c
  (hooks stage_cannon_ready @0x503b88, stage_dragonator_post @0x503a5c, stage_cannon_shot @0x46365c,
  stage_shell_dtor @0x4a18b4, stage_kobj_extra @0x4fdf7c, stage_cleanup @0x4ff074; fire through stage_gimmick.c's
  0x503bb0 hook -> stage_cannon_fire; define STAGE_CANNONS_OFF). Findings (C), correcting arena-3:
  - NO cannonball: interaction 11 ready check 0x6b1a58(stage, k) (k = 1/2 from the record +0x1a via 0xd009b4) =
    [+0xdd25] (cannons enabled) && !([+0xdd24] bit k) && s8 [+0xdd26/27] <= 0 (shots in flight) && kobj (area 3,
    mId 4/5) idle && its action not in {52, 54, 255}. Player action 171 = the shared switch action 0xb5b2a0 type 6
    (Dragonator = type 0, cart levers 2..4, rail cannon 5, pile 7) -> 0x5ba3cc(kind 35) -> 0x6b91b4 type 6 ->
    0x6aafec: request bits in the player word (0x80000 / 0x800000 + area, bonus flag) -> m19 frame 0x6b72fc.. ->
    0x6adb20(stage, 3, k, bits): if kobj action in {52,54,255} cmd 34 (action 51, barrel 25 deg) or 39 (action 53,
    55 deg) when the bonus flag; 0x6ab7f8: bit k in +0xde24, use time +0xdca0+4k, shots +0xdd26 += 1 per shell,
    shell(s) via 0x663720 -> factory 0x660e88 case 23 = uShell023 (712 B, ctor 0xc77834, vt 0xe6dc9c, init 0xc77068,
    frame 0xc7678c, end 0xc776a0); packet {owner, 0, kind 1, area, 0, k, bonus}. Bonus shot (2 shells) when
    time word [+0xdd00 + 20*(k-1)] - elapsed >= fps*180. Shell end 0xc776a0: shots -= 1; last -> cmd 35 (action 52)
    after a 25 deg shot / cmd 40 (action 54) after 55 deg; else stores the time word.
  - s03/s04 KowareObj (mId 4/5, mType 23): actions 51 0..150 (barrel s05 rot z -> -25 deg, s06 +120 x, s07 +75 y),
    52 200..350 (back), 53 400..550 (-55 deg), 54 600..750 (back), 55 800..860; SE 304/305.
  - The m19a03_006/007/012 effects + uShell020 kind 9 belong to the RAIL CANNON path (0x6b985c = cart processor),
    not to the floor cannons.
  - GU interaction records: mgr [0x1889ec0], alloc 0x31aa6c (128-B records), +0x64 kind, +0x48 radius, +0x58 area,
    attach 0x319554, register 0x31abac (st006 example 0x495924). GU Dragonator ready 0x503b88 is called from the
    player interaction 0x2ed1c4 (kind 11), fire 0x503bb0 from the switch action 0x2cdec4.
- [ ] 3. Camp camera (only if time remains).
- RESUME POINT (in-game test 2, 2026-10-18, paused by the coordinator; nothing changed since):
  - [ ] BUG (cause found, fix NOT applied): stage_doors.c stage_frame_c bails when `FIELD(uint32_t, g, 0x60) == 0`,
    but in GU's 0x503c7c [game+0x60] == 0 is the NORMAL state (0x503c94: +0x60 == 0 -> 0x503d38: skip only if byte
    [game+0x64] != 0, i.e. paused). So neither the doors nor the cannon tick ever ran (log: no `stage cannon:
    enabled`, no `stage doors: ...`). Fix: replace the test with
    `if (!FIELD(uint32_t, g, 0x60) && FIELD(uint8_t, g, 0x64)) return 0;` (line ~160), rebuild both variants.
    (Doors also untested because the test HP was 45 % > 40 %: test setup, not a bug.) The quest-start broadcast
    block (0x500d18) did not log either: GU's 0x500cb4 is skipped when quest byte +0x1777 != 0 (probably set by
    the fortress-HP quest setting); harmless, nothing to block then.
  - [x] stage_frame skip fix: applied by the coordinator (2026-10-19).
  - Map UI progress (2026-10-19, usage-limited; scratch tools gone with the old scratchpad):
    GU mapUI m26d/aNN_ui_eng.arc = HD_m26aNNdn_BM_NOMIP (256x256), HD_gmk_m26_BM_NOMIP (a01/a02), HD_map_icon_GSM,
    GUI map_icon, m26\fort_icn, m26\m26aNNdn (GUI 0x22948394). Map UI classes: cUIOQuestMap (DTI GOT 0x184002c, users
    0x61d328..), cUIOQuestMapIcon (0x183ffdc: 0x618f7c, 0x61907c, 0x61b9bc, 0x61c630), cUIOWholeMap (0x183fffc),
    cUIOEnlargeMap (0x184000c). 0x61b908 / 0x61c5bc: panel geometry (256 / 128 px, screen scale) only - NOT the
    world -> map transform. Not yet found: where an icon's world x/z becomes map pixels (next: follow cUIOQuestMapIcon
    update, look for reads of unit +0x40/+0x48 or of the SIS head ref point +8 and a per-area scale; the GUI
    m26aNNdn may carry the bounds).
  - [x] Map UI, area maps (2026-10-19, arena-4 agent; built, NOT yet seen in game):
    - Transform GU (C): cUIOQuestMap (0x61d4d4) owns a cUIOWholeMap (+0x58, DTI 0x183fffc, vtable 0x1774d78) and a
      cUIOEnlargeMap (+0x5c, DTI 0x184000c, vtable 0x17754f4) = the current-area map. Icons (cUIOQuestMapIcon update
      0x619494 -> per-kind 0x619bf8 / 0x619ebc / 0x61a064 ...) call parent vtable+0x6c with the unit pos (+0x40/+0x48)
      and set PosX/PosY (0x545a40 / 0x545ac0). Enlarge map +0x6c = 0x61cacc: map = (x, z) * this+0x70 +
      2 * (rec.s16[+0x30], rec.s16[+0x32]), HD px from the centre of the 256x256 map texture; this+0x70 =
      rec.f32[+0x2c] * 128 / 10000 (0x61c5e0..0x61c5f8); rec = [this+0x15c] = table[stage][area] (0x1774dec, 14
      pointers per stage; table 0x177540c when 0x55df28 < 3; both read only by 0x61c288 / 0x61c318). Record 0x34 B
      (.rodata): +0..+0x10 GUI file IDs per language (loader 0x61c288, lang byte +0xa5), +0x1c / +0x24 / +0x28 GUI
      object ids, +0x2c f32, +0x30 / +0x32 s16. Stage 26 = 0x16382ac (3.5, 16, -28), 0x16382e0 (0.6, 0, 7), 0x1638314
      (0.9338, 0, 0). Data check: Fortress SIS camp box / exits / ballistae land on the baked Fortress art. C
    - Whole map +0x6c = 0x61bde8 (C): 0x50089c adds per-area s32 offsets (+4 / +8 of 24-byte records, count +0x64,
      0x4f9040) from file ID 0xaab1 + stage (type 0x6ff78212 = map_com `stage\m26d\m26d`, 68 B: f32 1.1, u32 3, 3 x 20 B
      {s32 x, s32 z, s32 10000, ...}: Fortress (16600, -6600), (4100, 14000), (-18000, -18000)), then * this+0x70 (=
      256 * rec.f34 / (dims[stage].w / 2), dims via 0x50094c, rec this+0xe0 from 0x61b5e8) + 2 * rec.f3c / f40.
    - Transform 4U (C): 0x5a5f14 reads table 0xeebe0c + 0x18 * stage, +0xc -> {f32 scale, s16 x, s16 y} per area
      (index 0x69dbf0 = area except stage 13); icon 0xb82e38: u = x_off + (x * scale + 20000 * 0.5) / 20000 * 128,
      in pixels of the 128x128 map picture (pane map1, atlas left half 1:1; checked: 4U m19 SIS camp / exits land on
      the atlas pieces). m19 (0xeebfd4 -> 0xeebb10): a00 (1.8, 17, 11), a01 (2.0, 0, -8), a02 (1.8, 12, 37), a03
      (1.1, 0, -1). GU map / 2 + 64 == 4U (u, v) with the 4U record -> GU record = 4U scale / offsets, texture = 4U
      picture at 2x, no fit. The same-format records were found by value in 4U (GU stages 5, 9..14, 16, 19, 20, 25).
    - Built: tools/mapui4u2gu.py (new) -> module/romfs/nativeNX/<lang>/arc/stage/mapUI/m28d/a0N_ui_<lang>.arc (eng
      fre ger ita spa; Fortress arcs with the same internal paths -> the record's GUI file IDs still resolve):
      HD_m26a0Ndn = 4U m19a00 / a01 / a03 atlas left 128x128 at 2x; exit labels = 4U glyphs (atlas digit row, rects
      from ui299aNN; camp = 4U cmn_icon cell of pane ui299a01_camp) 13 4U px outside every exit of OUR SIS (map_com
      m28.arc, alias numbers; a02's interior exit (0, -3250, 0) skipped); a03's baked '3' replaced by 4U a02's big '2'.
      GUI m26a0Ndn: a00 Tex_area01 / Tex_area02 (exit highlights, cmn_icon ring) moved onto our '1' / '2' labels,
      Tex_area01a + AnimP_fort1/2 (fort HP icon players) moved off-screen (new floats appended to the float pool,
      header offsets shifted); HD_gmk_m26 (Fortress gimmick icons Tex_k01..04) blanked. module/stage.c: STAGE_ALIAS_UI
      default on (kind 49 -> m28 while the alias runs; kind 55 only with STAGE_ALIAS_WHOLEMAP) + hook stage_maprec
      @0x61c394 (build.py HOOKS): Fortress record copy with the 4U k / offsets (logs "gogport: area map record").
    - Deviations: 4U label / arrow panes (ui299 l_area, suji, l_yaji, positions far outside the picture) are moved
      by runtime layout code not decoded -> labels placed from SIS exits (G: distance 13 px), no arrows; labels use
      alias numbers (arena = 2, as GU's HUD calls it) instead of 4U's 3.
    - User check (visual): in-quest minimap of camp / area 1 / arena shows the 4U pictures; player + Gogmazios
      icons on the right spot (arena: Gogmazios spawn (633.5, 1510.8) -> map (+9, +19) HD px from the centre);
      labels readable, exit highlight rings (camp map) on the '1' / '2' labels, no Fortress gimmick / fort icons.
  - [~] Map UI, whole map (kind 55 map_com <lang>, map26dn + HD_map_26dn 256x256 BC1 + HD_map_mask_ID): still the
    Fortress' art; icons there use the Fortress area offsets of m28.arc `stage\m26d\m26d` (0x6ff78212) -> misplaced.
    Needs the 4U whole map (m19_map.arc: m19d_ID 128x128 + ui269) and 4U's whole-map placement (not traced), then
    a stage4u2gu.py function for the 0x6ff78212 offsets + an m28_<lang>.arc + -DSTAGE_ALIAS_WHOLEMAP.
    - 2026-10-19 result. Transform 4U (C): icon branch 0xb832ac ([this+0x129] = 0): 0x6c40e0 adds s32 per-area
      offsets (stage obj [0xfcf45c] +0x154 / +0x158 + 24 * area), 0x6c5678 W = obj+0x150, u = (x + off + W * 0.5) / W
      * 128 px of m19d_ID (pane ui269_map 128x128, UV 0..1). Filled by 0x6c2ac8(obj, W, recs, n) from the per-stage
      class vtable +0x10; m19 class (vtable 0xe65564, +0x1c = 0x6594b4 passes stage 19) -> 0x6596dc: W = 40000, recs
      0xdee2b4 x 4 (24 B): a00 (15300, -5200), a01 (3700, 1000), a02 (-8200, 17300), a03 (-9700, -12200).
      Transform GU (C): 0x61bde8 map = (x + off) * this+0x70 + 2 * rec.f3c / f40, this+0x70 = 128 * rec.f34 /
      (dims.w / 2) (0x61b934..0x61b964); dims[stage] = runtime table 0x18977a8 written at 0x5058d0: stage 26 = 60000;
      whole-map rec = table 0x1774cf0[stage] (0x1774d60 when 0x55df28 < 3), stage 26 = 0x1635b5c: k 1.0, offset 0;
      offsets = file +0 / +4 of the 20-B records. Data checks: Fortress SIS land on HD_map_26dn, 4U SIS on m19d_ID.
      -> GU icon = 2 * (4U u - 64) when the offsets are 4U's and k = 60000 / 40000: no fit, texture = m19d_ID at 2x.
    - Built: tools/stage4u2gu.py wholemap_offsets (alias build): m28.arc `stage\m26d\m26d` offsets = 4U a00 / a01 /
      a03 (other record fields = Fortress'). tools/mapui4u2gu.py wholemap() (run by main()): m28_<lang>.arc (eng fre
      ger ita spa, Fortress m26_<lang> copy, same internal paths): HD_map_26dn = m19d_ID at 2x, BC1 with punch-through
      alpha (new encoder, alpha checked); GUI map26dn: area01 / area02 highlights = 4U ui269_area01 / area03 (pos, size
      44 * scale, rotation 0), AnimP_fort1/2 off-screen. module/stage.c: STAGE_ALIAS_WHOLEMAP default on
      (-DNO_STAGE_ALIAS_WHOLEMAP), hook stage_wholerec @0x61b608 (build.py HOOKS): record copy with k = 1.5, offset 0
      (logs "gogport: whole map record"). Check: our 9 SIS exits land on the 4U art; area arcs byte-identical.
    - Deviations (G): labels as on the area maps (arena '3' -> '2', 4U a02's '2' erased, its piece left as a passage);
      ui269 pane frame read as minus the picture pixel (matches the SIS of a01 / a02 / a03). 0x50089c / 0x5008f4 are
      also called by the generic wrappers 0x4974c / 0x49770 (area <-> stage frame) -> they now use 4U's frame.
    - Left: user visual check of the whole map in quest (art, player / Gogmazios icons, highlight ellipses).
  - Map icon of em 0x59 (C, report only): 0x61a994 picks the map_icon GUI sequence 0xf4240 + state (table 0x1635324,
    6 x 2 ids) and, for large monsters ([[enemy+0x1428]+0x1a8] bit 0), the size / shape class 0x1635354[em byte
    +0xb5f4] (our reg_mapicon: 89 -> 18 = Kushala / Chameleos / Teostra / Fatalis class; cases 7..24 tweak it at
    0x61aacc), drawn from HD_map_icon_GSM_NOMIP (inside the mapUI / map_com arcs, so our m28 copies could carry a
    custom cell). HD_cmn_micon01 cell 146 is the quest board / HUD icon only, not the map.
  - [ ] Coordinate alias-arc rebuilds with the tar-look agent (ae710cd3e86ecffde, editing stage MATERIALS in
    stage4u2gu.py): only one of us runs `stage4u2gu.py alias` at a time.
- [-] 4. Demolisher / pile bunker (coordinator lead, traced 2026-10-18, NOT ported: the records do not exist) (C):
  (2026-10-20: wrong for the pile: the fallen em089 spear registers the kind-36 record, module/em089_pile.c.)
  - Data check (2026-10-18, 4U EUR ROM dump/base/*.3ds via tools/ctr.py): every 4U quest with map byte +0xC4 = 19
    (quest00/01.arc: m01002 Kushala story quest, m11003, m11005, m11007, m11014, m11019, m11024, m11028, m11032,
    m11035; copies in dump/q4u_m19/) holds no interaction record (its only arena coordinates are the boss spawn:
    (1133, 0, -2519) or (634, 0, 1511) for m11014 / m11035); the m19 stage item-pop points (m19d IPS 0x52776ab1, 15
    points: kind byte +0x1e = 0 everywhere, no byte 34 / 36 in the file) and IPL lists hold none either; the m19 arcs
    carry no other record source. Together with the code survey below: no kind-34 (Demolisher = gate a00) and no
    kind-36 (pile) record is ever created on m19 in 4U 1.1 -> both unreachable in 4U; not ported (adding them would
    add a gimmick 4U players never get). The doors' HUD line 21 is shown regardless (kept, see item 2).
  - 4U player interaction numbers from record kinds (0xd059d8): 8 -> 1 ballista, 10 -> 3, 11 -> 2 Dragonator, 12 -> 4,
    30 -> 9, 31 -> 8, 32 -> 6, 33 -> 7, 34 -> 10, 35 -> 11 floor cannon, 36 -> 12. 0x5ba3cc runs kinds 30..34 through
    0x6b93b0 types 1..5 and 35 / 36 through 0x6b91b4 / 0x6a1f18.
  - The DEMOLISHER is the gate KowareObj m19a03d-a00 (mId 2, mType 22, at (0, 2200, -8110) south, behind the wall a04
    that sinks at 40 % HP): action 53 0..150, action 54 150..400 (quakeType 9, part a01 thrusts -300 z at frame
    156 = the strike), action 55 400..700 (retract + material animation); SE 300..303; ScrollCollisionSbc
    (w00-a00-shell, type 34, group 8). It is fired by gimmick-use type 5 (0x6b93b0 case 5: 0x6c3400(stage, player
    area, mId 2, cmd 36 = action 53), camera shake 0xc01d64(6)) = record kind 34 (interaction 10).
  - The PILE (uStageGimmick type 2 sub 3, 0x33c7c8 with r6 = 1) runs on +0xdd29 bit 1, set once by 0x6a1f18 (only
    caller: 0x5ba3cc kind 36 = interaction 12, ready 0xb0f498 = [+0xdd28] && !bit 1, player action 172); it only
    plays em089 SE 218 / 219 (arena-3). +0xdd28 = "stage gimmicks on" (1 normally; quest 1002: 0 until HP <= 70 %,
    0x6b7148); the spears also need it (0x33c870).
  - No creator of a kind-34 or kind-36 record exists in the 4U code: record registrars 0x5b921c (35), 0x5ba4e0 (33,
    32, 31, 30, 30), 0x5b9988 (SIS table 0xfb8ab8, max 17; m19a03d SIS has only kinds 3 / 3 / 5), 0x5b93c4 / 0x5b9d40
    / 0x5ba9bc (item-pop data byte +4 / +0x1e, files not in the m19 arcs), 0x5ba22c (17), 0x25da98 (19..26), no
    other writer of record +0x54 in the gimmick ranges. The doors trigger still shows "All clear to use the
    Demolisher!" -> either a data-driven record (quest / item-pop file not in our dump) or a feature disabled in
    4U 1.1. Without the record POSITION, porting would mean guessing the switch location -> not done.
  - GU counterpart (for a later port): GU's Demolisher = st007 (models m26d-a00/a01 = 4U a00/a01): controller state
    mgr+0x344 (0x504600: 5-min timer 18000, messages 93 / 94), ready 0x5048e8 (state 2), fire 0x5048fc (flags |= 0x80,
    [mgr+0x340] st007 -> 0x498720 = fire with the player); GU switch action type 5 (0x2d95cc).

## Reactions (react agent), 2026-10-19
Code: module/em089_react.c (`em089_react_run`, called from the em089_act.c dispatch line; returns 0 -> the old
`act_react` placeholder). Static RE only, nothing tested in game. C = confirmed in code, S = strong, G = guess.
- Player (C): 4U 0x9197c0(this, table, flag) = GU 0xa134c, the same reaction-sequence player (same step byte role
  rec+0x1a1 = W+0x144, table/index/descriptor fields W+0x594/0x588/0x5a0 = rec+0x554/0x548/0x560, interpreter
  0x93188c = 0x9ef3c with identical opcode numbers, movement setup 0x92a8d0 = 0x9ecac, sequence end -> action-end
  slots 247/249..252 by state class). Table and flag are only read on the first frame. Port = call 0xa134c with the
  em089 tables converted: entries {u32 op, u32 arg} unchanged; 24-byte motion descriptors with blend / start as
  float (4U s32); type-2 movement data from 4U .bss 0x10b7cc8 / 0x10b7ce0 (static init 0xd2ab1c: velocity
  (0, 40, 0) / accel (0, -0.8, 0) and (0, 20.4, 0) / (0, -0.4, 0)). The brief's "16-byte entries" do not exist:
  GU tables are 8-byte entries like 4U (C, 0x9ef80 `add r5, r9, r1, lsl #3`).
- Conditions (C unless noted): flying = rec+0x1bb == 1 (4U W+0x1c9, S); hit direction 0x938620 = GU 0x9e994 (bits
  3..5 of 4U W+0x7993 = rec+0x5ccb); 0x940b50 = rec+0x5ccb & 7; W+0x78bf = this+0x7585.
- Numbers mean the same in both games (C for 110..115: 4U 0x943024 = GU 0x9c5d8; 10/7 = state-0 flinch of 4U
  0x947ffc; GU Kushala's (10, 114) is its sever reaction, see em089_break.h).
- Ported category 10 numbers (4U case address; table = 4U address; first motions):
  | num | 4U | plays |
  |---|---|---|
  | 7 | 0x8c2930 | ground: dir 2..5 0xff7024 (0x301) else 0xff7054 (0x302); flying: dir 1 0xff710c (fall 0x329, down loop 0x307 360 f, get up 0x308), dir 3/6/7 0xff7044 (0x325), else 0xff7034 (0x324) (C) |
  | 8 | 0x8c2abc | dir 2/3/7 0xff7194 (hop 0x315 + 0x316 + down 0x307 + 0x308), else 0xff71e4 (0x314); flag 1 (C) |
  | 15, 181 | 0x8c2eb0 | 0xff71e4 (0x314), flag 1 (C) |
  | 20 | 0x8c29b8 | ground: dir 3 0xff70e4 (0x306/0x307/0x308) else 0xff7064 (0x303/0x304/0x305); flying: dir 2/5/7 0xff70bc (0x328/0x304/0x305) else 0xff710c (C) |
  | 21 / 150 | 0x8c2af0 / 0x8c2b90 | 0xff7194, flag 1 / 0 (C) |
  | 27, 148, 175 | 0x8c2b74 | 0xff7054 (0x302) (C) |
  | 32 | 0x8c2b14 | rec+0x5ccb & 7 == 2: 0xff725c (0x303/0x304/0x305, then 0xfe chain) else 0xff723c (0x306/0x307/0x308, chain) (C) |
  | 37 | 0x8c2b58 | 0xff729c (hop 0x315 + 0x316/0x307/0x308), flag 1 (C) |
  | 42, 43, 112 | 0x8c2d90 | 0xff727c (0x30b) (C) |
  | 106 | 0x8c2f0c | flying 0xff7564 (0x328 ...) else 0xff753c (0x303/0x304 360 f/0x305) (C) |
  | 114 | 0x8c2a68 | sever (S): flying 0xff7304 (0x318 from frame 40), else 0xff72e4 (0x318); then 0x307, 0x308 (C) |
  | 136 | 0x8c2ecc | flying 0xff750c (0x338, 0x337 ...) else 0xff74e4 (0x337/0x304 600 f/0x305) (C) |
  | 144 | 0x8c2e10 | 0xff74c4 (0x108, setTargetMode 3, 0x10c) (C) |
  | 155 | 0x8c2bac | flying 0xff7334 (0x32d) else 0xff7324 (0x320), 0xfe chain (C) |
  | 157 | 0x8c2bec | 0xff7344 (hop 0x315 from frame 28, 0x316), flag 1, chain (C) |
  | 161 | 0x8c2cfc | this+0x7585 ? 0xff7484 (0x32e) : 0xff7464 (0x321), both with camera event 0x2e (C) |
  | 167 | 0x8c2d44 | 0xff708c (0x303/0x304 600 f/0x305/0x30b) (C) |
  | 169 | 0x8c2d60 | this+0x7585 ? 0xff728c (0x324) : 0xff727c (0x30b) (C) |
  | 171, 173 | 0x8c2dac / 0x8c2dc4 | this+0x7585 ? 0xff74b4 (0x32c) : 0xff74a4 (0x31f) (C) |
  | 180 | 0x8c2e6c | flying 0xff7034 (0x324) else 0xff7024 (0x301) (C) |
  | 187 | 0x8c2c08 | this+0x7585 ? 0xff73ac : 0xff7384 (0x307 loop 180 f), chain (C) |
  | 188 | 0x8c2c50 | 0xff73d4 (0x308) (C) |
  | 189 / 190 | 0x8c2c6c / 0x8c2cb4 | this+0x7585 ? 0x325 loop : 0x30b loop (60 f, op 6), chain (C) |
  | 210 | 0x8c2e2c | flying 0xff7164 (0x329 ...) else 0xff7134 (0x306/0x307/0x308), op 0x3a (C) |
  | other | 0x8c2914 | end the action at once (slot 247 = 4U vt+0x164) (C) |
- Log: `gogport: em089 react 10/<n> seq motion <first motion> flag <f> mode <rec+0x1bb> dir <d> flag78bf <b>` once per
  start (80 lines); `... not ported -> placeholder`, `... no 4U case -> end` (20 each).
- The 2026-10-19 test log (10/7 x3, 10/114 x1): with this port 10/7 plays the short flinches (0x301 / 0x302 on the
  ground) and 10/114 the fall + down + get-up. The "tail broke 4 times" is not a reaction issue: GU counts every part
  flinch as a break count (em089_break.h), so check the break visibility code (break agent) (S).
- Left:
  - [ ] 10/108, 109, 202, 203 (0x8c2f78 / 0x8c2f4c / 0x8c3440 / 0x8c33f0): need the GU counterpart of 4U
    [this+0x8d88]+0xe5 (>= 2 -> 0xff758c / 0xff7644, flag 3 or 1) and a port of em089 0x8bdaec (step2 machine:
    timer, setTarget(5, 8, 18), wanderPoint) + 0xff71f4. Placeholder for now.
  - [ ] 10/200, 228 (0x8c2fa4): step2 machine (setTarget(5, 8, 9 | 8) + wanderPoint, then per-motion motionCheck(9)
    windows + turnToTarget for motions 792 / 816 / 817 / literal 0x8c3324 (+1, +5), fallback turn 86 while blending)
    + 0xff75e4 / 0xff7614 (flying). Placeholder for now.
  - [ ] category 11 (0x8c3b7c): 11/0 -> 0x8b6ac8 (0x8b6da4 flying), 11/1 -> 0x8b6b80, every other number 0x8b6ac8;
    own step machines (setMotion 781 = 0x30d with blend 6, then 0x926044(this, i, 1, 0) for i = 0, 1 and no action
    end), motions 789 / 791; not the sequence player. Needs 0x926044 mapped. Placeholder kept.
  - [ ] Visual check in game (all 27 motion ids used are in dump/em089/motions.txt, C).
  - [ ] em089_act.c comment above the dispatch line still says "10: engine reactions (unchanged)": stale, left
    for the owner (react agent was limited to the dispatch line + include).

### In-game tests 6 / 7 (2026-10-19 late, logs 19-56-36 / 20-37-57) (main agent)
- Test 6: drips fall, Dragonator camera fixed, no model artifacts; effects still white; tar beam not drawn, some
  lasers gone (beam records on the previous tail, fixed in test 7); high-ground loop at z 1903 (map-hit sphere).
- Test 7: smoke colours correct (4U colour multiply); lasers correct; high ground correct (hands on the real edge,
  platform attacks, no loop); dashes stop at the wall correctly. Open: phase-2 tar explosions still partly white
  (lead: em089_014 unit 7, the only em089 unit with blend 6, helper on it); tar beam not seen (check next test).
- Test 8 (log 21-58-53): phase-2 roar interrupted by 10/31 at 00:05:24.597 (3.25 s in, before the frame-208
  latch), so work+0xca / BGM 901 / aura never came; the script went on to 2/35, 7/146. 10/31 = PARALYSIS (C):
  GU dispatcher 0x9a828 (kind rec+0x3ae) kind 5 -> 0x9b90c, state rec+0x1ba 0 -> 0x76afc(10, 31) at 0x9bab4; kind
  5 written only at 0x995bc (0x97ddc) when the status evaluator 0x9a34c returns 2 = 0xa2b10 (params
  [0x71078()+0x3c] = data block +0xa0; 0 -> no buildup). 4U has the same chain (0x939c40 kind 5 -> 0x9402a4,
  state 0 -> 10/31 at 0x9403cc; requestAction 0x92b1d4 only gates on W+0x1ca == 11, no roar / super-armour gate),
  but em089's etd words 15..21 are 0 and the paralysis check 0x917bf8 -> 0x93fcc4 stops at 0x93fcfc on a 0
  pointer: 4U em089 never builds poison / sleep / paralysis / stun and never gets 10/29 / 10/31. The port's
  dttune kept Kushala's status blocks (dt_convert.py keeps the donor block when the 4U word is absent). Fix
  (module/em089_react.c em089_react_status_immune, called per frame from em089_state_update): clear data block
  +0x98 / +0x9c / +0xa0 / +0xa4 (all GU readers check 0, reset 0x564bc frees only non-zero). Log: `em089 status
  immunity: ... -> 0` once per spawn; react default now tags 10/29 / 10/31 "status immunity failed?". Re-roar (S):
  the roar comes from rage group 6 s0 while cond 2 (work+0xca) == 0, so a roar cut by a real flinch (test 8
  00:03:44, 10/7) is retried at the next rage, as in 4U (seen: re-roar at 00:05:21). Later: make dt_convert.py
  null these blocks for em089 on the next arc rebuild, then drop the runtime clear. Test 9 (log 06-48-28): immunity
  line once at spawn, roar 1/25 latched work+0xca at 00:09:59.977, bgm 901 played (user-confirmed), no 10/29 / 10/31.

### In-game test 5 (2026-10-19 night, log 17-48-14) (main agent)
User: glued puddle gone; phase-2 laser, heaps and sweep puddles correct; tar beam from the mouth; tail smoke /
flinch / cut animations good; camp + arena black triangles still there (priority 1); some effects white instead of
black (roar, some puddle explosions, ground smoke while moving, tail cut); phase-2 drips: more puddles than usual
and the falling-drop effect sits just above the ground; on the high platform he dashes at the hunter forever, no
biped attack; Dragonator camera shows only terrain.
- [x] Black triangles FIXED (user-confirmed, camp + arena): GU ends every mesh's index run with a 0xFFFF restart
  and its draw reads it; the stage converter wrote none -> one stretched triangle per mesh (notes/stage.md "black
  triangles"). Also ported: arena c04 drawn with its 4U camera check, camera-checked sets mDrawMode 5 -> 13.
- [~] White effects still white after PEL_COLOUR_OFF (user, same evening): helper 2 on the unmapped EFL unit +0x18
  bits 12-15 draw field (4U values 0 / 1 / 2 on em089 units; GU draw bits at +0x50). Result: not the cause (4U
  "Intensity", see the helper2 section). Test 6 (coordinator's whole test-4 tail except the transform mode): still
  white, and test 4 already had white tail smoke (user, 15:09) -> "black in test 4" was never true; the PEL tail is
  not the cause. Reverted. Lead: 4U effect colour setter 0xc48378 (effect +0x24c = 1, +0x25c = RGBA) is called from
  em089 code (0x8a2818, 0x8c6918, 0x8c89c4) and from the MEF player (0x39154c, 0x392190).
  [x] CAUSE FOUND + fixed (white-effects helper, 2026-10-19 ~20:30, static; arc rebuilt, not tested in game): the
  white effects' units are LIGHT GREY in the EFL; 4U MULTIPLIES them by a run-time colour, GU did nothing.
  - Effects (S, scratchpad wh/mef.py, ucol.py): steps = MEF 42 / 43 (+ 13 / 14 / 18 / 19 / 44 / 45 / 69 / 70)
    em089_031 on joints 63 / 73 (billboards ff8b8b8b / ffa2a2a2 / ffcccccc, model ff2f2f2f); roar motion 0/4 =
    42 / 43 + 50 qe013_003 + 51 qe013_004; roar dust em089_032 = MEF 40 / 41 (0/8, 0/25, 1/11, 2/70, 2/77, 2/78;
    a5 / a4 / 46 greys); explosion dust em089_021 (MEF 11 / 12 / 20 / 21 / 30 / 31 / 68, models 7f / 4a, smoke
    8b..db) and em089_023 (MEF 25); qe006 ground dust (15..17, 46..49, 1008, 3100); tail break 3300 qe013_002
    (ff / 9b / af / ad). Tar beam / puddles (em089_005 / 012 / 002 / 008 / 013..015) carry their real dark or
    orange colours and no colour block -> unaffected, as the user saw.
  - 4U (C): EFL header +0x2c = offset of a 16-B block (loader 0x23d6ac: res+0x90 = hdr +0x2c, res+0x68 = data). The
    effect's slot 26 0xafa89c: word 0 bit 4 -> effect +0x228 |= 1, block +0xc byte 2 == 0 -> |= 2. Present ONLY in
    em089_021 / 023 / 031 / 032, qe006_* (0x10, 1, 0, 0) and em089_050 / qe013_002 (0x10, 1, 0, 0x10000).
    Unit colour hook = slot 60 0xc474c0 of the MH effect class (vt 0xe6d130; the base classes' slot 60 0xafc570 =
    bx lr): unit colour mode (generator +0x3c bits 24-27 = unit +0x18 bits 0-3, generator setup 0x39f984; 0 on
    every em089 unit) 0 and +0x228 bit 0 -> bit 1 ? area colour *0xc0813c(sEffect, effect +0x239) : +0x24c == 1 ?
    +0x25c : unchanged; mode 5 -> area colour. 0xc48274 = per-channel a * b / 255 (RGBA) -> MULTIPLY.
    Effect +0x239 = 0xc09908(owner) ground state (0 normal -> sEffect +0x1df0 area_color_soil; 1 / 5 water, 2 lava
    +0x1e04, 3 poison +0x1dfc, 4 vines +0x1df8; names at 0xc08bd4..); m19a03d-col / -f / -f02 / -f03 MhEffect
    soil = (0.5373, 0.4588, 0.3569, 1) = (137, 117, 91, 255). Code colours (0xc48378) on qe013_002 from em089
    code: tail break 0x8c6918 (37, 46, 49, 255) = PEL 3300; spear break 0x8c89c4 (42, 29, 25, 255) and 0x8a2818
    (joint 157, (120, 85, 80) / (143, 76, 58)) are NOT ported (no records). The MEF player's 0xc48378 calls
    (0x39154c / 0x392190) need MEF flag 0x8: no em089 MEF record has it. em089_050 (aura, code-colour block): no
    em089 code colour found -> unchanged (its units are black anyway).
  - GU (C): 0x327cb8 (uMHProofEffect slot 52, after the unit build 0x9bda64) walks the units (+0x1f0, next +0xc);
    cParticleGenerator units: colour = record +0x60 RGBA (with +0x56 / +0x73 = 0, 0x3214f0), combined per +0x71:
    0 RGBA lerp by +0x68, 1 = 0x9b67e4 (replace, or lerp by the EFL block's u16 +0xc if its bit 4 is set: 0 for 4U
    blocks), 2 = per-channel a * b >> 8 (254 -> 255) = 4U's multiply, 3 = RGB lerp, alpha kept. GU reads the EFL
    block differently (bit 4 = lerp factor; Capcom's conversions turn 0x10 into 0x08), so the 4U block alone does
    nothing in GU, and with the override off the grey units were drawn as they are = white.
  - Fix (tools/efl4u2gu.py pel_colour / pel_record): records whose 4U EFL block selects the area colour get +0x70
    1, +0x71 2, +0x60 = (137, 117, 91, 255); 3300 gets (37, 46, 49, 255) (CODE_COLOUR). 31 records x 2 lists; all
    other records keep PEL_COLOUR_OFF; pel_follows / PEL_TAIL / transform bytes untouched. Arc rebuilt (--cmdtbl
    gog): only effect\pel\em\em089_00u changed, at +0x60 / +0x61 / +0x62 / +0x70 / +0x71 of those 62 structs (none
    of 3000 / 3001 / 42xx / 43xx / 51xx); 1110 entries, em089_files.inc + manifest identical.
  - Expected in game: step dust, roar dust, em089_021 / 023 explosion dust, qe006 dust brown-dark (grey * soil, e.g.
    cc -> (110, 94, 73), a5 -> (89, 76, 59), model 2f -> (25, 22, 17)); tail-break smoke near-black slate (37, 46,
    49) * grey. Not changed: qe013_003 (roar shockwave, white ff / 8f in 4U too) and qe013_004 (its black model
    79000000 is the unit's own colour; if the roar still shows a white ring, check that model's colour / blend).
  - Open (I): the slot-60 call site was not found (the hook's data path is traced, its caller is not); 4U's extra
    effect lighting 0xc47174 (RGB * effect +0x23c + effect +0x260 when 0x19fbf0, not traced) and the soil scale
    (sEffect +0x1e0c when the ground-state byte +1 > 0) are not mapped; the colour is fixed to the arena soil (water
    / lava ground states not mapped); GU's rounding (>> 8) differs from 4U's (/ 255) by <= 1.
- [ ] Phase-2 tar explosion white (test 7) (blend-6 helper, 2026-10-19 evening; static; NO data change, arc not rebuilt).
  - Video (S, recording 20-42-28, video t = log - 272 s; scratchpad vid/sheet_b.png, sheet_c.png): after the sub-14 shell
    ends (post sub 18 = 5118 = em089_014, v 210.98 .. 219.50) every explosion site keeps a flat soft-edged disc on the
    ground, SATURATED white (bright pixels mean (250, 248, 245), p90 (255, 255, 255)), tar heap / red core in the middle,
    >= 2 s; small white specks ("snow") float in the orange haze in the same frames. Only em089_014 is posted at shell
    ends in that window (no em089_008), so the video cannot separate em089_014 from em089_008 units.
  - Lead "blend 6 is different in GU" REFUTED (C): 4U unit +0 byte 3 -> draw state bits 5-12 (0x2e8848) -> draw
    0x35c4e8 (particles) / 0x64284c (model mesh helper, called from 0x625a40) -> handle table 0xe39f34 (copied by
    0x229f68, clamp > 32 -> 1); GU 0xa7c210 same bits -> 0xb95038 (particles; +17 when flag 0x20000) / 0xb007fc (model
    helper, called from the mesh draw 0xc90b50 at 0xc928ec) -> table 0x16a23f8 (copied by 0xc7a3cc, clamp > 34 -> 1).
    Handles = jamcrc(name) & 0xfffff << 12 | object index; names resolved from 4U /system/ltshader/LtShaderPackage.lfx
    and GU AppShaderPackage.mfx: 0 BSBlendAddAlpha, 1 BSBlendBlendAlpha, 2 AddColor, 3 BlendColor, 4 Add,
    5 BSBlendRevSubAlpha, 6 BSBlendRevSubBlendAlpha, 7 RevSubColor, 8 RevSubBlendColor, 9 RevSub, 10 Min, 11 Max,
    12 / 14 AddDestColor, 13 BlendAddDestColor, 15 BlendAddDestAlpha; 4U 16..31 = the RGB variants, GU inserts
    BSBlendNoBlend at 16 (GU 17..32 = 4U 16..31). Same index -> same name in 0..15, and the blend-state records are
    byte-identical in both packages (5: src*a, ONE, reverse-subtract; 6: src*a, 1-a, reverse-subtract). GU's model
    draw also picks a fog function per index (table 0x16a2480: 0 / 5 / 6 -> FBlendFogPrimAlpha). Data (S): GU uses
    blend 6 on 216 Model / 79 Billboard units, with blue-ish colours (e.g. em001 cm150_000 78662800) = an orange
    scorch by subtraction, like 4U. So em089_014 unit 7 (cm000_000, b4ffe2aa, blend 6) can only DARKEN in GU (dst *
    (1 - a) - src * a <= dst); it cannot be the saturated white. No Capcom conversion (eflconv.pkl, >= 0.97 identity,
    31 files / 59 units) contains blend 5 or 6 (only 0 / 1, all kept); the "57 / 58" line was 59 / 59 when re-run;
    lower-identity pairs (0.85 .. 0.96) are other monsters' files (noise, not evidence).
  - Unit +0x18 bit 31 (em089_014 units 8 / 16 / 18, em089_008 unit 5) (C): 4U generator setup copies +0x18 bits 24-31
    to generator +0x4e (0x39f9a4..0x39f9ac); GU copies the same byte to generator +0x52 (0xaeca68..0xaeca6c), with the
    same neighbours (bits 0-3 -> +0x3c / +0x40 bits 24-27, bit 17 -> bit 31). Consumer not traced in either game. Set
    on 46 % of 4U and 34 % of GU Model units -> an ordinary shared flag (I), not a GU-only meaning.
  - Intensity (+0x18 bits 12-15) (C, refines helper2): combiner index = base + Intensity (0x35bf68 / 0x35c440), scale
    table 0xe352a0 = 0 / 1 / 2 -> combiner scale field (0x35bb48) = PICA RGB x1 / x2 / x4 (I: PICA encoding). GU has no
    such field -> Intensity-1 / -2 units are drawn darker than in 4U, never whiter.
  - Remaining candidates (I, untested): saturated white needs additive / overbright output, so not 5 / 6 units.
    em089_014: Polygons 0 / 14 (flat, ff121a27, cm000_GSM_HQ_NOMIP) would be white discs if their colour were lost;
    Billboards 10 / 15 (blend 0 additive, ff4d8be1 / ff2f7ae1, Intensity 1) saturate when stacked; black Billboards 1 /
    13 (b4000000 / ff000000) are the debris that would read as "snow" if their colour were lost; Model 18 (qe001_000,
    5affe2aa, bit 31) is pale blue at 35 %. Next step: one test arc per candidate with that unit's alpha zeroed
    (em089_014 only), user looks at a sub-14 explosion.
  - Lead "+0x52 picks an EAN colour / alpha / UV track that GU reads differently" REFUTED (tar-white helper,
    2026-10-19 ~21:30; static; comment-only edit of tools/efl4u2gu.py; module arc rebuilt byte-identical, NOT changed).
    - (C) +0x52 = index into the unit's EAN (path at unit +0x130; em089_014's cm000 units -> effect\base\cm\cm000\
      cm000, 40 entries). 4U 0x402e64: [[unit obj +0x24] +0x14] +0x6c + idx * 32 -> +0x10 / +0x14 / +0x18 / +0x1c to
      obj +0x208..+0x214. GU 0xa7c1ac: [[r7 +0x28] +0x14] +0x6c + idx * 32 -> +0x10 / +0x18 / +0x1c passed to a
      virtual (0xa7c1ec); frame step 0xa7c9f4 reads entry +0 (data offset) and the frame's first 8 bytes. GU
      rEffectAnim load 0xce461c (magic / 0x20120224 check): +0x64 = size, +0x6c = copy of file +0x10.., +0x68 = count
      | (byte +0xf != 0) << 24; the saver 0xce47b8 writes +0x68 back to +0xc. No runtime reader of +0x68 bit 24 found
      (no bit-24 test after any +0x68 load; the only effect-range +0x6b byte load, 0xb412e8, is a serialiser).
    - (S) The EAN is a UV ATLAS, no colour / alpha: entry {data off, frame count (hi 16 = loop flags), pivot x, y, x,
      y, cols | rows << 16, cell w | h << 16}, frame 24 B {x | y << 16, w | h << 16, u0 v0 u1 v1}. Identical layout in
      the 78 4U / 96 GU EANs (GU's multi-entry cm099_000 / cm200_200 / em019_00_004 decode the same way); unit +0x60 /
      +0x64 = the selected entry's pivot in 8575 / 8965 4U and 2917 / 3060 GU units (not a texture-size field). No GU
      arc has an effect\...\cm000 name (no resource collision). Capcom's conversions keep the colour and the blend of
      such units and only swap texture + EAN (4U em077_010 cm000 cell 3 ff121b32 -> GU em013_00_010 cm090_011 ff121b32);
      em107 -> em019 keeps idx 1 / 2 into the 3-entry em019_00_004. The appended curve tables (header count | 2 << 8 |
      property << 24; 0 = colour, 0x40 = scale; keys {time, A, B}) have the same format in both games.
    - Decoded (S): u0 / u14 / u10 / u15 -> cell 16 = (256, 0) 64x64 of cm000_GSM_HQ_NOMIP (512x256): RGB pure white,
      alpha = a round speckle cloud denser in the middle (scratchpad ean/cells.png). u1 / u5 / u13 -> cell 3 (64, 0):
      grey smoke puff. GU selects the same cell (same table, index, layout, texture size). u14's colour curve: t 2
      (255, 122, 40) -> t 17 (67, 34, 16) -> t 60 (15, 10, 7); u13's the same; u1's alpha 125 -> 184 -> 0.
    - Reading (I): cell 16 drawn WITHOUT its colour = the symptom twice: u0 / u14 (ground Polygons, life 200 / 30) =
      the soft white "disc" (speckle cloud, white RGB), u10 / u15 = white specks ("snow"). So the question is why
      their colour (39, 26, 18) / orange is not applied, not which cell. Not explained statically.
    - [ ] DIAGNOSTIC arc (one user test; not installed): scratchpad diag/em089_00.arc (sha1 376d7427..., built by
      diag/make_diag.py from the current module arc; only em089_014 differs, same size). G1 Polygons u0 / u14 ->
      pure RED + atlas cell 33 (thin ring); G2 additive Billboards u10 / u15 -> pure GREEN + cell 12 (8-ray star); G3
      Billboards u1 / u5 / u13 -> alpha 0 (base + curves); G4 Models u7 / u8 / u9 / u12 / u16 / u18 -> pure BLUE;
      u2 / u3 / u4 / u19 / u6 / u17 / u11 unchanged. Read one screenshot after a sub-14 explosion: disc -> red ring =
      Polygons, colour applied; white ring = Polygons, colour lost; specks -> green / white stars = u10 / u15; disc
      turns blue = models; disc gone = u1 / u5 / u13; unchanged white speckle disc = control units or another file
      (em089_008).
      [x] RESULT test 8 (user-confirmed): red rings, green stars and blue appeared, u1 / u5 / u13 gone, but the white
      soft disc AND the white specks were UNCHANGED. So unit colours are applied; the white is an untagged em089_014
      unit (Models u2 / u3 / u4 / u19 ef_em089, Billboards u6 / u17 em089_001_BM, Filter u11) or another file.
  - Filter u11 (type 9) REFUTED as the source (filter helper, 2026-10-19 late; static; comment-only edit of
    tools/efl4u2gu.py at FILTER_GU_W24_31, module arc NOT rebuilt).
    - (C) 4U: vtable 0xe63da8 (DTI 0x110c598 'cParticleGeneratorFilter'), draw slot 20 0x415bc0: owner checks, unit
      +0x40 byte 0 must be 0 -> 0x4156c0: 184-B request (0x2ff080) per particle: RGB = particle +0x80 lerp through the
      owner colour hook vt[0x94] (0x415ac8), alpha = particle +0xa0 lerp * 0.5 * colour alpha (0x415b0c), fixed 0.045
      (0x415aa4) / 3 (0x4158f4); unit w24 byte 2 == 1 (0x4157bc) -> centre = particle world position + unit w20 / w21
      (0 / 5000) -> request +0x48 / +0x4c, else screen centre w26 / w27 (0x41586c). Submit 0xaf3610 -> 0xaf3450
      (sEffect +384, 8 per-viewport slots, type byte must be 0): allocates a 96-B object via DTI 0x110cb50 =
      uMultiBlurFilter (name 0xd4a570), line registration 0x64608c.
    - (C) GU: filter vtable 0x17903fc (DTI getter 0xa86f7c; the 0x179047c table is cParticleGeneratorForce), draw
      slot 20 0xa855f4: unit +0x40 byte 0 (0..3, `bxhi lr` above) -> 0xa85684 / 0xa85bfc / 0xa861fc / 0xa867d8 ->
      0xb92024 / b92330 / b923a0 / b92410 -> 0xb92098 on sEffect +0x278 / +0x2a0 / +0x2c8 / +0x2f0, whose type words
      are set at 0xb8fd90..0xb8fe1c to 0 / 1 / 2 / 3 = uMultiBlurFilter (0xc63ca4) / uMultiColorCorrectFilter /
      uMultiGodRaysFilter / uMultiBloomFilter. em089_014 u11 has byte 0 = 0 -> blur. Case 0 reads w24 (byte 1 =
      samples 16, reduced by a quality setting; byte 2 = centre mode: 0 / 3 = screen centre w36 / 37 + w28..31, else
      particle world position + w20 / w21 = 4U's world mode), w25, w26; particle init 0xcafe30: w20 / w21 -> particle
      +0x60 / +0x64, w27 * scale -> +0x68 / +0x78, colour = w32..35 (0xcafed4) -> particle +0x80 / +0x90.
    - (S) eflcorp.pkl: 68 4U (0xc0) and 29 GU (0xe0) type-9 units; GU w24..31 identical in all 29; 4U w24 = 0x10000 in
      all 68. 7 Capcom conversions (4U units with equal words 0..23 + colour) are byte-identical to filter_4u_to_gu:
      em023_010 #0 / #2 -> em068_00_009 #2 / #6, em023_016 -> em068_00_011, em028_016 -> em071_00_000 / em072_00_008,
      em116_011 -> em038_00_008, d0502_004 -> em027_00_010 (scratchpad flt/fpair.py). Conversion faithful; not changed.
    - Reading (I): a full-screen radial blur, one per viewport (8 slots, last request wins), resampling the frame;
      it draws no texture or mesh, so it cannot make soft discs at several explosion sites nor specks. Not traced:
      how uMultiBlurFilter combines the colour (multiply / add); 4U's strength (0.045 / 3) vs GU's unit words (w26 1.0,
      w27 -0.1, 16 samples) differ by design (Capcom uses the same GU words).
    - [ ] DIAGNOSTIC arc 2 (test 9, not installed): scratchpad diag2/em089_00.arc
      (sha1 a95c7f0e7c0b2f8d373e9789f2a40444fe2622d3), built by diag2/make_diag2.py from the current module arc (sha1
      b93e844b...); only em089_014 and em089_008 differ. em089_014 u11 Filter off (+0x40 byte 0 = 4: GU's draw 0xa85644, particle init 0xa86c8c and
      update 0xa86ea0 all skip values > 3); u2 / u3 / u4 / u19 -> pure YELLOW; u6 / u17 -> pure CYAN; every
      em089_008 unit -> pure MAGENTA (base + colour / alpha curve RGB, alpha kept). Read one screenshot after a sub-14
      explosion: disc yellow = ef_em089 models u2 / u3 / u4 / u19; cyan = Billboards u6 / u17; magenta = em089_008;
      specks likewise; still pure white = none of these (another file / non-EFL source, e.g. a shell model or
      decal); disc gone or changed in shape only = the Filter after all. Caveat: em089_008 u3 / u4 are additive
      (blend 0); magenta added over yellow saturates toward white / pink, so look at the disc rim colour.
      [x] RESULT test 9 (user + recording 2026-10-20 06-58-54, 27 s clip = log 10:20..10:47): drip puddles
      (em089_008) magenta, but the disc under the LASER heaps stayed white; white specks unchanged. Video v 14..19:
      the saturated white soft disc appears where the falling streak of 7/146 (attack shell sub 52, PEL 4252 =
      em089_012) touches the ground, BEFORE the orange heap (sub 14 ground shell, PEL 5114 = em089_015 u0 / u3, lava
      texture visible = texture applied) rises on it; the sub-14 explosions (sub 18 = em089_014) come later. So the
      disc is in em089_012 or em089_015, not em089_014 / 008. Status immunity log line present, bgm 901 played.
    - [ ] DIAGNOSTIC arc 3 (test 10, not installed): scratchpad diag3/em089_00.arc (sha1 3a7c6c84a2659883d47d09c2575c9856f50621a2),
      built by diag3/make_diag3.py from the module arc b93e844b...; only em089_012 / em089_015 differ. em089_012 u1
      (additive ground Billboard, ffd6d081 pale) GREEN; u8 (additive ground Billboard, ff093eff) BLUE; u0 / u7
      (Billboards 9687abe8) RED; Polylines u2 / u4 / u6 YELLOW; em089_015 u1 (Model ef_em089 ffbcbcbc) CYAN; u2
      (Billboard em089_001_BM) MAGENTA. Lasers 4241 / 4341 / 4251 / 4351 / 4254 use em089_012 too (odd colours expected).
      [x] RESULT test 10 (user + recording 07-22-39): laser RED (em089_012 u0 / u7 = the laser body), disc CYAN =
      em089_015 u1 (Model ef_em089, ffbcbcbc), bright cyan although its 4U textures are dark; white smoke after the
      explosions; specks still white. Straight beam fixed (user-confirmed).
    - [x] Cause (S, C for the data): colourless 4U effect meshes (vertex format 0x82917009) were filled with WHITE
      (255, 255, 255, 255); GU's effect material (FDiffuseVertexColorMD, FEmissionConstantEflEmu, same features as
      Capcom's converted em013_00_000) doubles the vertex colour -> 2x = saturated white. Capcom's own conversion
      writes (0, 0, 0, 255): 4U ef_em077 group 3 (88 vertices, colourless) -> GU em013_00_000 group 3 (88 vertices,
      constant (0, 0, 0, 255)); other groups keep the 4U colours byte for byte. GU corpus (60 enemy arcs, 274 meshes
      of format 0x207D603B): constant white 0, constant (0, 0, 0, 255) 22. Fix tools/efl4u2gu.py convert_effect_mod:
      fill (0, 0, 0, 255). Arc rebuilt (lock taken + released, `--cmdtbl gog`): sha1 fdb33cd38ce0f4e36b75c5f608a92e04b7548a9a,
      files.inc / manifest identical; only 7 MODs changed, only vertex-colour bytes of colourless meshes: cm000_000 (12
      of 14 meshes), cm000_002, ef_em089 (groups 3 / 4 / 8 / 9 / 10), qe000_000, qe000_001, qe001_000, ef_m19a03.
      Backup scratchpad em089_00.arc.vcol_before (b93e844b...). Check in test 11: heap disc, explosion smoke, specks,
      and that no effect vanished (risk: a mesh drawn only through its vertex colour would go dark / invisible).
      [x] RESULT test 11 (user): heap disc and explosion smoke right colour, snow specks gone, nothing missing. Still
      white: the dust of the tail sweep (7/20, motion 0x23d) and the big arm slam + swipe.
- [ ] Dust white on tail sweep / slams (test 11). Motions 0x23c / 0x23d / 0x243 / 0x25d / 0x25e / 0x268 / 0x269 / 0x26a /
  0x27c / 0x20c post em089_022 / 024 / 030 (no header colour block -> no PEL multiply). Their dust units (grey
  818181 / a2a2a2 / 999999 / 3f3f3f ...) have unit +0x18 bits 0-3 = 5 (the old note "0 on every em089 unit" was wrong).
  (C) 4U hook 0xc474c0: mode 5 -> area colour 0xc0813c multiplied in (0xc478dc(.., 1) -> 0xc48274 = trunc(a/255 *
  b/255 * 255), float32) regardless of the header block; mode 0 -> header block path; other modes -> unchanged. GU:
  no tint for mode 5 found (the 0x9bf1b4 reader of that field is a transform case); (S) 404 / 519 4U mode-5 units grey,
  GU's 29 coloured. Fix tools/efl4u2gu.py (UNIT_AREA_MODE, unit_4u_to_gu area, convert_efl): bake the Battlequarters
  soil into words 18 / 19 of mode-5 units in files without a header block (assert: no code-coloured file, no colour
  curves). Arc rebuilt (lock taken + released): sha1 9bf11914c7091ba45d63b271e6fda687d6c36b43, files.inc / manifest
  identical; only em089_022 (10 units), 024 (4), 030 (6), 051 (10), qe016_003 (2) changed, only unit words 18 / 19
  (e.g. 818181 -> 453b2e RGB). Backup scratchpad em089_00.arc.area_before (fdb33cd3...). Test 12 (log 07-46-57, no
  crash): arm slam + sweep dust no longer white (user-confirmed; 7/26, 7/139, 7/122..125 seen). Tail sweep 7/19 / 7/20
  not used this test (same files em089_022 / 024 / 030): check when it appears.
- [ ] Straight tar beam (7/105, shell016 sub 53, PEL 4253) drawn behind him while it hits in front (test 9; the
  sweep 7/106 sub 37 was perfect). 36 / 53 got their effect position / rotation only from the post request, the moving
  subtypes every frame (em089_efx_shell016_move). Fix: em089_shell016.c s016_move calls em089_efx_shell016_move for
  every subtype (36 / 53 keep their placed capsule). Built 153528 B; check in test 10.
  - Lead "the em089 shell family still posts Kushala's shell effects / sounds" REFUTED (shell-family helper,
    2026-10-19 late; static; NO data change, build script untouched, arc NOT rebuilt: module arc still sha1 b93e844b...,
    files.inc 59cb3db8..., manifest e10398ae...).
    - (S) shell\em\em089_00_shell00\em089_00_00 (rShell, XFS 0x4aa69872) = Kushala's family 00 renamed: ShellInfoList
      26 x cShellInfo {ShellScale, EffectParam (rShellEffectParam 0x1eb12c38), SoundParam / HitParam / ShellParam
      (rFreeUseParam FUP 0x496f8f22)}, EffectLists[0] = effect\pel\em\em024_00u, PelTiedSeList[0] =
      sound\pts\em\em024_00u (rFestaPelTiedSe), SoundList / BodyDataList null, HitData / HitSize = ours, ShellCmnParam.
      No model / trail resource anywhere in the def. Decoded (scratchpad shfx/decode.py; byte-identical to em024's):
      ef001..026 = 4 cParam {listId, uniqueId} each, slot 0 = list 0 id 62 (entries 1-9, 11, 13), 80 (10, 12), 72
      (14-26), slots 1-3 = 999 / -1; ids 62 / 72 / 80 = em024_00u records 15 / 17 / 18 = effect\em\em024\em024_00_000
      (I: Kushala's wind, from the name only). snd001..026 = EMPTY FUP (0 ints / floats / vectors) -> no sound at all. hit = 1 int (0..3,
      an HDS index for subclass code), sh = 3 ints + 1 vector (subclass parameters), cmn = (3; 72.0; 2 vectors).
    - (C) How GU uses them: cShellInfo getters 0x48b074 (+8 EffectParam), 0x48b0c4 (+0xc Sound), 0x48b114 (+0x10
      Hit), 0x48b164 (+0x14 Shell); their only callers are the uShell accessors 0x4a2f5c getEffectParam(slot, kind)
      / 0x4a2fe4 / 0x4a3060 / 0x4a30dc, 0x4a3164, 0x4a31f0 (kind < 0 -> setup param +8). The effect is posted only by
      0x4a1e50(shell, cParam, req): listId > 7 or uniqueId < 0 -> returns 0 (so 999 / -1 = "no effect" is honoured),
      else handle this+0x1388 + 4 * listId, extra arg rShell+0x98[listId] (0x48a950; I: PelTiedSeList, while the
      +0x78 list read by 0x48a8e0 is EffectLists, the one setup registers), post via vt slot 78
      (0x4a1e08 -> 0x53b500); request prepared by 0x4a1d34 (scale = ShellScale). Sounds with the shell's SoundList
      (rShell+0xb8, 0x48a9c0): 0x4a2000 / 0x4a209c(id), explicit ids. ALL callers of 0x4a2f5c / 0x4a1d34 / 0x4a1e50
      / 0x4a2000 / 0x4a209c / 0x4a3060 are per-class code (e.g. uShellOt004 0x43c1c8: getEffectParam(0, -1) ->
      0x4a1e50 at init). Call-graph walk (depth 6, scratchpad shfx/reach2.py) from all 83 uShellEnemy vtable slots
      (0x175b268; our classes copy them), the request path 0x4a1c84 / 0x48c6c8 / 0xc067ec, ctor 0x43b3f8 and dtor
      0x4a18b4: none reaches any of these getters / posters (sanity check: 0x43c1c8 and 0x3f94e4 do). The base setup
      0x4a24f8 only registers EffectLists[0..7] with the effect manager (0x3268d8: table insert + refcount, no post;
      released by the dtor via 0x326c78). module/*.c never calls them (em089_efx_post_on posts em089's own PEL u
      on the owner) and every em089 shell uses resource entry 0 (param +8 = 0).
    - Reading (C for the code paths above, I for "nothing else"): our uShell050 / 051 / 016 / 005 translations post
      no Kushala effect and no Kushala sound through the shell family, so the family is NOT the white disc / snow.
      Neutralising ef001..026 (999 / -1) would be a no-op for every existing path and would change the arc that test
      9's diag2 was built from, so it was not done. Next suspects stay as listed above (non-EFL source, a file not yet
      colour-tagged).
- [~] Beams (test 6: tar beam not drawn, some lasers gone / not reaching the impact): 4200 / 4300 + sub had the
  previous tail since helper 1's pel_follows (as in test 4: laser gone); test 5 (PEL_TAIL) drew them from the mouth.
  pel_follows no longer includes them (PEL_TAIL + colour off). Rebuild vs helper 1's arc: PEL changes only on those
  15 ids x 2 lists, files.inc / manifest identical.
- [ ] High ground (test 6): the sequence now runs (point 10, 7/61, type-5 wall at z 3403, 1/23, 1/24 mode 1) but he
  always ends at z 1903 (3 times, x -238 / -483 / -533): ~1500 short of the face. Mode-1 s100 needs him within 1500
  of point 14 (-128, 0, 3625): 1722 -> lands and dashes again = the loop; user: hands on an invisible wall in front
  of the real one.
  [~] FIXED in em089_act.c (helper 2026-10-19, static; module 153208 B, 0 warnings, not installed; no data change, arc
  not rebuilt). Cause (C, addresses): the map-hit (wall collision) sphere. GU 0xa71ac (per frame, from 0xa6400 /
  0xa6478) puts it at pos + rotated rec+0x900 * rec+0x910, radius = block +48 * rec+0x914 (0xa756c, size factor only
  outside 0.6..1.95), adjusts it on the map (0x49a84) and moves pos x / z by the push. Block = GU 0x712a4 =
  [dtbase+0x84] (+52 when rec+0x5cb6 == 103) = 4U 0x91df20()->+0x48 = emd word 20 (already 4U's own data:
  stand (0, 250, 375), fly (0, -200, 0), wall (0, 0, 0), +36 (0, -200, 0), radius 1125; no x2.5, not the donor's).
  Offset by state rec+0x1ba (1 / 2 fly, 5 wall, 6 +36, else stand), copied by GU 0xbc8b0 = 4U 0x9167ec (= our
  setTargetMode = setState; 1/22..1/24 call it with 0 -> stand). Facing the face: 375 + 1125 = 1500 -> z 1903,
  exactly the log. 4U (C): em089's 0x8c5768 [0x8c5d68..0x8c5e34] (slot 77, every frame, state 0 only) morphs that
  block in place: mode 1 -> radius 750 and stand z 0 (25 per tick on motions 0x41 / 0x42 / 0x50 / 0x51 = the 1/22..
  1/34 turns, else 10); mode 0 dash motions 0x217..0x219 -> 1125 / z 950; other mode 0 -> 1125 / z 375; then
  setState(state) re-copies the offset. The port had skipped it (misread as "locomotion speeds", "no GU twin of row
  +0x48": 0x712a4 returns the block itself). In 1/23 (mode 1 from its entry) 4U's sphere is 750 centred on the
  monster -> he can reach z 2653 at the face, 972 from point 14 (I: if 1/23's movement carries him that far; it moved
  >= 2447 in test 6 before the stop). Port: maphit_frame (called in motion_mode after the mode switch, 4U order) +
  log `em089 1/24 start: pos X Z, map-hit radius R (block R) offset z Z (block Z), state S mode M, point 14 at D`
  (cap 20). Expect radius 750, offset z 0, D < 1500 -> no 1/24 re-dash after the wall turn; the next think in mode 1
  picks the high-ground sets (s6 / s25: 2/63, 7/144, 7/145 ...), hands on the real platform face.
- [~] White effects / drop effect not falling: helper on tools/efl4u2gu.py PEL tail (blend vs follow bytes).
- [~] High ground: three port deviations found and fixed in em089_act.c (real emd point table, sync_target
  overwriting the EMC point, 7/47 wall hit taking the stop instead of the turn); needs the in-game check. See
  "High ground (helper, 2026-10-19 late)" below.
- [~] Dragonator camera (helper, 2026-10-19; static, module 152408 B, 0 warnings, not installed; no arc changed).
  The camera is NOT map_com data in either game: both hard-code per-stage records in code.
  - GU (C): switch action 0x2d9504 (/ 0x120f7f8): fire 0x503bb0, then for the local hunter (0x27bcd0 == 1) tail-call
    0x503a5c(mgr): bit 0x40 of flags +0x1a2 set -> release 0x1b794(cam, 0, 1.0); stage 10 / 25 / 26 / 27 -> record
    0 / 1 / 2 / 3 of the 64-B table 0x1897640 (.bss, written from code literals by the static initializer 0x505538;
    record 4 = siege camera of 0x50491c) -> 0x1b08c(cam = [0x184d750], record, 1, 1.0) -> 0x162a8 pushes it on the
    camera override stack; result 1 -> bit 0x40, countdown +0x374 = 240.0 (0x50396c subtracts the frame step,
    releases at <= 0). Record = +0x00 fov, +0x10 eye, +0x20 target, +0x30 up (up = global [0x191e890]); 0x15460
    blends them into uCamera +0x3c fov / +0x40 mCameraPos / +0x50 up / +0x60 mTargetPos (property registration
    0x898790 / 0x898804): world coordinates. Stage 26 = record 2: fov 50, eye (-1300, 2000, -2000), target (1000,
    100, -5500) (Fortress spears at z -5500, st003 FUP vec 3 (380, 1080, -5500)).
  - Root cause (C by data, the symptom itself not re-checked in game): the alias runs as stage 26, so the camera
    flies to Fortress coordinates: from mid-arena it looks into the south ledge (y 1700 floor, z -7600..-4710) ->
    terrain only, hunter at the north switch and Gogmazios at the spears out of frame.
  - 4U (C): fire 0x6bc9dc, for the local hunter (0xd04fbc), picks the camera by stage / area (6/1 0, 6/2 1, 10/1 2,
    12/1 3, 14|21/1 4, 19/3 5) and calls 0xc01d64(cam, k): table 0xf2d440, 32-B {eye, target, fov, duration}
    (vectors from the static initializer 0xd48f90, fov / duration in .data); 0xc06f00 ends it when timer > duration.
    m19 area 3 = record 5: eye (-2300, 2030, 1730), target (470, 890, 2990), fov 50, duration 300. Field order:
    GU record 1 = 4U record 2 value for value (eye (3031.07, 720.25, 1916.07), target (1008.15, 261.34, -141.83), fov
    56) = Capcom's port, so 4U's first vector is the eye (I: 4U's own camera reader not traced to the lookAt).
  - Fix (module, runtime, since the data is code): stage_gimmick.c `stage_dragonator_camera` = 0x503a5c's body for
    the alias with 4U record 5 (up = GU's own record-2 up vector) and 4U's duration 300 (GU: 240 for every stage);
    called by stage_cannon.c's existing 0x503a5c hook when the press was not a floor cannon. GU's table untouched
    (Fortress quests keep record 2). tools/gogreport.py "misc" now lists `stage dragonator: fire|camera`.
  - Log to read (cap 10): `stage dragonator: camera 4U m19a03 eye (-2300, 2030, 1730) target (470, 890, 2990) fov 50
    up (0, 1000, 0)/1000 for 300 frames -> push 1 (GU Fortress record: eye (-1300, 2000, -2000) target (1000, 100,
    -5500))`. push 0 = GU's camera refused the override (camera type not 1 / 2, same as GU's own path).
  - Expected view: from high above the west side of the arena (y 2030, south of the west ballista platform) looking
    north-east and down at the north wall in front of the +x spear (spears thrust from z 4105 to z 2505); the switch
    (0, 1765, 3610) sits about 15 deg above and 15 deg sideways of the view centre (fov 50; vertical / horizontal
    semantics not traced), so the hunter should be in the upper part of the frame and Gogmazios in frame when he
    stands in front of the spears. 300 frames (~10 s if the step is 1 per 30-fps frame).
  - Open: 4U eye / target order inferred (above); duration units assumed equal (4U adds a per-frame step, GU
    subtracts [[0x2126764]+0x68]); blend speed / mode (1.0 / 1) are GU's; whether 4U also plays a sound or a
    letterbox with this camera was not compared (0x6bc9dc's 0x663474 call before the camera is not traced).

#### High ground (helper, 2026-10-19 late; static, build 151572 B, 0 warnings, not installed)
- 4U path (C, EMC listing with GU's op-length table 0x1732c8c + 4U interpreter 0x94f488): every think starts in g0
  s16: `01 00 00 00 00` (slot 0 = kind 0, the hunter) + cond 25 (save slot 0), then s3 / s10: op 0x79 (class of the
  slot-0 target, 0x93ed2c) case 0x4020 -> cond 8: 0 / 2 (top) -> mode 0: g0 s8 -> g1 s100, mode 1: s6 / s25;
  1 / 3 (ledge) -> mode 0: s7 (30 % s4 turn + s124, 70 % s100), mode 1: s5 / s26; 4 -> the normal sets. g1 s100,
  mode 0: cond 8 0 / 1 / 2 / 3 -> `01 00 05 08 n` with n = 10 / 11 / 12 / 13, then s101..s104: op 0x1d (0x950958:
  |angle to slot 0 - yaw| <= 0x5500, else 2/2 turn toward slot 0) + dash 7/60 / 7/62 / 7/64 / 7/66 (-> 7/61, 63, 65,
  67); then cond 26 restores the saved target. Mode 1: only when NOT within 1500 of point 14 / 15 / 16 / 17 (cond
  14 / 15 / 16 / 17 == 0) -> s80 (1/24) + the same point + dash; else nothing.
- The point (C): op 0x01 -> 0x92ce98 -> setTarget 0x916bcc (0x92ed9c leaves kind 5 sub 8 unresolved) -> 0x92d0d4 ->
  0x93aab4 sub 8 [0x93b2a0] -> 0x689f7c(record, (area << 8) | n). record = 0xf3a024[species][0] = rEnemyData +0x64
  data + 8 (writer 0x68959c), so record +0x40 = emd file word 18 (em009: word 18 parses in 0x689f7c's layout, 16 /
  17 do not). The old "+0x40 = 0" read word 16: em089 word 18 = 0xd40 = stage 19, area 3, 19 points (scratchpad
  emdpts.py), e.g. 10 = (-128, 0, 6500) behind the high platform, 11 = (6000, 0, 1422), 12 = (-215, 0, -7500),
  13 = (-4000, 0, 2250), 14 = (-128, 0, 3625). Item 9's "(0, 0, 0)" is wrong; cases 4..7 / 14..21 now use them.
- The end (C): 7/47 [0x8bcdd4] entry sets no target; it ends on inRange(0, 0) (setStopDist 0), the motion end, the
  timer 9999, or the wall probe: an accepted wall zeroes the timer AND sets r6 = 1 [0x8bd214], so the same frame
  chains 1/22 / 1/23 (1/33 / 1/34 with W+0x145) by dash frame. Wall type = attribute index 0 = SBC group word 1 >> 24
  (4U 0xcd4064 = GU 0xc1c2fc: [col+0x48][poly] + 48 + 4; matches test 5's "type 0" hit at (-2973, -1502), whose
  groups all have word 1 = 0). m19a03d-a-w00: the high platform face z 3400..3403 is type 5 (word 1 0x05000000),
  accepted by 7/61 (types 5 / 2): -> 1/22 / 1/23 (mode 1, heading 0) -> next think in mode 1 -> s6 / s25 (top) with
  s63 (2/63 moves, 7/144 / 7/145), s13, s30, s60, s139, s140. The four dash variants pair with the four points
  (10 +z: 5 / 2, 11 +x: 3, 12 -z: 4, 13 -x: 2 / 5).
- Deviations fixed: (1) set_target_c wrote (0, 0, 0); now k_arena_pts[n] (em089_cond cases too). (2) sync_target
  overwrote slot 0 with the hunter in 7/61 (entry + every frame) and 2/1 / 2/2: the dash and the turn aimed at the
  hunter (test 5: dash into the platform at z ~1900). Now F_NOSYNC = 2 holds the point until the next setTarget on
  slot 0 (the think's `01 00 00 00 00` or cond 26). (3) act_7_47 read only the frame-start timer, so a wall hit took
  the stop motion; now the probe's accept sets it too.
- Open (S): a type-0 skin (group 0x02000055 / word 1 0) sits at z 3301..3307 in front of the type-5 face; if the
  sweep returns it first, 7/61 ignores it and the dash ends at the motion end (loop toward point 10). Mask
  0x3fff0000 semantics not traced (0x198250 stores it; filter not read).
- Log to read: `arena point 10 (slot 0) -> (-128, 0, 6500)`, `7/47 wall probe: type 5 ... (var 1) -> stop` (own cap
  now), `7/61 dash end: wall ... (arena point)`, `7/47 wall turn -> 1/22|23`, `arena point released by setTarget
  0/0/0`, `cond N (arena) -> r`; then mode-1 actions (2/63, 7/144, 7/145 ...). User: does he rear up at the
  platform and attack the hunter there?
