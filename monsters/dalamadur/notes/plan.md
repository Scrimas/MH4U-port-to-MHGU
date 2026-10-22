# Dalamadur / Shah Dalamadur: plan for goals C-F (draft 2026-10-21, waiting for the user's OK)

Facts behind each step: phase0.md, class-study.md, gu-walkable.md, speartip-crag.md, common-branches.md.
Order: C (assets) -> D1 (classes register, both halves spawn and draw) -> E (arena) -> D2.. (behaviour) -> F (content).
Every goal ends with a test the user plays; multiplayer is checked in every goal (two local Ryujinx instances over
LDN), not left to the end.

## Multiplayer rules for the whole port
- One machine controls both halves (GU gives every enemy the session's controller at spawn and moves all of them
  together on a migration: class-study.md). As in 4U (0x912504), the tail still adopts the head's controller
  whenever they differ (GU setter 0xb161c), as insurance. Log line per action: `ctl head / tail`, so an MP test
  shows it.
- Shared fight state (4U enemy-manager block, common-branches.md) lives in the module, written only by the
  controller: shared flinch / reaction (both halves react together), tail damage -> head rage, tail KO build-up ->
  head. Remote machines get the results through the replayed actions and GU's HP / part sync.
- Handlers run on every machine; AI, action choice and damage only on the controller. The tail's follow table uses
  setActionNext, so non-controllers replay the controller's tail actions.
- Shared HP without a stored pool: on the controller a hit on one half applies the same HP delta to the other.
  Non-controllers never write HP.
- Arena breaks, BGM phase, walk collision: computed on every machine from the replayed actions and the local
  arena state; GU's stage break command checked for host-only / broadcast behaviour before use (Gogmazios'
  stage_kobj_bcast precedent).
- Shah's persistent-effect state travels in the per-action net bytes (4U slots 78 / 79 -> GU 171 / 172).
- FPS: every timer / step scaled by the unit delta, as for Gogmazios (mixed 30 / 60 / 120 FPS sessions).

## Goal C: assets (converters only, no game code)
1. Models, textures, materials: mod em024 (56 bones, one vertex format the converter handles), em024_tail
   piece, ef_em024; Shah's model and 2 extra textures. mod4u2gu / tex.py / mrl_build / mrl_anim.
2. Motions and AI: 3 LMTs (copied), e024_cam (lcm4u2gu), em024_cmd / em083_cmd (Shah's is identical).
3. Monster data per half and per variant: emd / etd -> bodydata, hitsize, attackdata, XFS, dtbase, dttune
   (emdata4u, dt_convert).
4. Effects: 23 EFL + 2 MEF, Shah + 9 (efl4u2gu). Sounds: 73 waves + banks, Shah + 2 (snd4u2gu).
5. BGM: bgm_em024 / bgm_em024_2 -> Opus + STQR entries (snd_bgm), ids 0x902 / 0x903.
6. Walk collision (new tool): each 4U walk set -> per-bone GU ground SBC (strips are bone-local; sbc.py writer).
   Head bones 1..5 (bone 5 separate: it is the set 1 / set 2 difference), tail bones 140..142.
7. Arcs: one per em (head, tail, Shah head, Shah tail). Both halves carry the shared model / motions / sounds under
   the same paths, as 4U does (the resource manager loads them once, S).
- Checks: each converter validated on 4U / GU pairs first; Gogmazios' and Tigerstripe's outputs byte-identical
  after any shared-tool change.

## Goal D: behaviour (C classes, Gogmazios' em089 as the template)
1. Registry and skeleton: the 4 allocations entries + package.toml [classes]; two classes (head, tail), Shah as
   variant 1 of each; both halves spawn together (GU Ahtal-Ka precedent: bosses [head, tail], objective = head).
   Test: both halves visible, idle, in a test arena; solo + MP.
2. Head: 95 actions on 19 handlers, 25 overridden slots; tail: 37 actions on 10 handlers, 19 slots. Literal
   translation, 4U frames and timers unchanged.
3. Head-tail sync: follow table, rage copy, target, shared part ranks, shared HP (MP rule above).
4. Walk: register the SBC pieces, move them each frame with their bones, enable them by the 4U set rule (mode,
   motion list, part-0 rank).
5. Shells: types 1, 12, 15, 16 (Gogmazios' beam exists), 29 (head), 3 (tail); effect controller id 35 / 81.
6. Arena breaks: k00..k02 at the 4U frames of 7.60 / 7.61 / 7.62, AI bands < 90 / 62 / 44 % HP; BGM phase 2 when
   k00 breaks.
7. Common 4U code that names the Dalamadur ems (common-branches.md):
   - class code: shared reactions (4U 0x948b9c), rage / KO forwarding, paint both halves (GU slot 240), one attack
     damages only one half (hit handler, slot 38), 4 animation layers if the handlers use them, footstep material
     of the body collision, effect ids 35 / 81;
   - core: map icons for the new ems (GU icon table 0x1635354; 4U icon points joint 107 head / 154 tail);
   - MP: body gather points and meteor mining points must be the same on every machine (spawned from replayed
     actions or synced: check GU's gather-point messages);
   - confirmed by the user: heat zone near the head (hook GU 0x6a160, 4U gate 0x92d774 decides when), carving /
     gathering on the head during the fight (4U item lists for 24 / 110), meteors leaving mining points in the
     arena, two map icons (head and tail);
   - none: area-change predicate (no area move), shiny drop (none in 4U), Palico filters (low).
8. Shah: variant branches (effects, hitzones, net bytes), its own data.
- Tests per handler group (kill tests with TEST_HP_PCT=5), then a full fight solo and in MP.

## BGM phases (core restructure: approved 2026-10-21, DONE, built, not tested)
module/bgm.c (hooks + port_bgm_register, port.h struct port_bgm), Gogmazios' em089_bgm.c = its registration +
phase getter (called from em089_register_class), Dalamadur's dala_bgm.c (from em090_register_class; ids 0x902 /
0x903, STQR file 0x107a0, phase = dala_arena_broken(1)). Test: Gogmazios' theme still switches at its phase roar
(log "gogport: em089 bgm theme 901"); Dalamadur "dalaport: em090 bgm theme 902" then 903 after the first spire
break. TODO: assert the 0x107a0 bgm_stqr file ID in build_dalamadur_arc.py (as Gogmazios' build does).
Original plan:
Today the three BGM hooks (module/build.py bgm_select 0x4e60d4, bgm_stqr 0xb6d72c, bgm_play 0x4e34a4) are
implemented in Gogmazios' package (monsters/gogmazios/module/em089_bgm.c), so a second monster cannot have its own
battle theme. 4U Dalamadur (C, speartip-crag.md): bgm_em024 in phase 1, bgm_em024_2 from the first arena break,
the same for Shah; the files are converted and in the arcs (GU ids 0x902 / 0x903, STQR sound\bgm\battle\bgm_em090).
1. New core module/bgm.c owns the three hooks; a package registers {em types (head, tail, Shah, the quests'
   stand-in while its quest runs), STQR file ID, the two sequence ids, int (*phase)(void *unit)} from its class
   registration (same pattern as em090_register_class).
2. em089_bgm.c keeps only Gogmazios' registration and phase getter (F_PHASE2): same ids, same stand-in rule,
   same log lines (Gogmazios' behaviour unchanged).
3. Dalamadur registers 0x5a / 0x15a / 0x5b / 0x15b (the tail half is a quest boss too), phase = the first arena
   break (dala_arena_broken), computed on every machine from its own replayed state (4U: the sound state is local).
4. Checks: module build; Gogmazios quest 11491 theme 1 -> 2 at its phase roar; Dalamadur 1 -> 2 at the first spire
   break, solo and MP.

## Goal E: Speartip Crag
1. Stage alias: a new stage id hosted on GU m18 (the Sanctuary, 2 areas), redirected to new m29 paths while the
   quest runs (the Battlequarters route).
2. Convert m08a00d (camp) and m08a01d (arena): models, textures, collision incl. -shell, SIS, lighting, kobj
   k00..k02 -> GU k01..k03, map UI, area sounds, camp falling rocks.
3. Break wiring with D6; GU KowareObj check for mType 9..11.
- Test: walk both areas solo and in MP, then the fight with breaks.

## Goal F: content
Approach (2026-10-21): the content tools are shared (tools/items4u.py, hagi4u.py, notes4u.py, gear4u.py,
weapons4u.py, quest4u.py, armor4u2gu.py, weapon4u2gu.py, wsnd4u2gu.py); each monster gives a spec in its own
wrapper (Gogmazios: monsters/gogmazios/tools/items_em089.py, hagi_em089.py, notes_em089.py, gear_em089.py,
gear_weapons_em089.py, build_gog_quest.py). Dalamadur: the same wrappers in monsters/dalamadur/tools/, items
APPENDED from 2991 (allocations.toml [monster.append] items = n and items = [2991, 2991 + n - 1]; core:
notes/items-append.md).
4U item IDs (text_4u, C): 677 Dalamadur Steel, 678 Dalam Tail Scale, 679 Dalamadur Gazer, 680 Dalamadur Pectus,
681 Dalamadur Glaive, 682 Dalamadur Talon, 683 Dalam Tail Shell, 684 Dalamadur Fanblade, 685 Vortex Bone, 686 Skyblade
Gem, 687 Shattered Omen, 881 Dalamadur Ticket, 951 Dalamadur Scrap, 1369 Dalamadur Steel+, 1370 Glaive+, 1371
Pectus+, 1372 Dalamadur Ripper, 1373 Fanblade+, 1374 Dalam Tail Scale+, 1375 Dalam Tail Shell+, 1376 Skyblade
Drgnsphire, 1377 S.Dalamadur Steel+, 1378 S.Dalamadur Glaive+, 1379 S.Dalamadur Gazer, 1380 S.Dalamadur Pectus+,
1381 S.Dalamadur Ripper, 1382 S.Dalam Fanblade+, 1383 S.Dalam Tail Scale+, 1384 S.Dalam Tail Shell+, 1700 Dalamadur
Scrap+ (30). Final list = what the carve / reward / recipe tables of both variants reference (derive, do not guess).
4U carves (hagi4u.carve_record_4u, C; points past a monster's own read other monsters' data): head em024 point 0
(High: Steel 65, Pectus 12, Talon 8, Vortex Bone 13, Skyblade Gem 2 %; G: Steel+ 64, Pectus+ 12, Ripper 8, Vortex
Bone 10, Skyblade Gem 4, Skyblade Drgnsphire 2); tail em083 point 0 (High: Tail Scale 45, Steel 25, Vortex Bone 27,
Skyblade Gem 3; G: Tail Scale+ 46, Steel+ 30, Vortex Bone 16, Skyblade Gem 5, Drgnsphire 3) and point 1 = severed
tail (High: Tail Shell 75, Glaive 22, Skyblade Gem 3; G: Tail Shell+ 75, Glaive+ 22, Drgnsphire 3); Shah em110 /
em111: G only, S.* items, same layout. Not in carves: Gazer, Fanblade(+), Talon in G, Shattered Omen, Ticket,
Scraps (break / quest rewards: to read). Break rewards (C, 2026-10-21; lookup as monsters/tigerstripe_zamtrios/notes/
content-data.md section 0: [0xf386c0 + 4 * (s32 [0xf384d0 + 4 * em] + 4 * group + rank)], rank 0 low / 2 high / 3 G,
group 8 refused; scratch brk4u2.py): em 24 base 376, em 83 844, em 110 1192, em 111 1208. Groups = the 4U part table
(emd word 32, module/dala_break.c): head g0 = part 0 (Gazer; G 85 Gazer / 8 Gem / 5 Drgnsphire), g1 = part 3
(Pectus / Pectus+), g2 = part 4 (Fanblade / Fanblade+), g3 = parts 1 + 2, both needed (Talon / Ripper); tail g0 =
part 5 (Vortex Bone / Glaive / Tail Scale), g1 = part 6 (Tail Shell); Shah G only (S.* items). Head / tail groups 4..7
are other tables (generic G rewards, frenzy crystals 690 / 1645), not reached by the part table. GU break rewards are
per rank file quest\bui\bui_s<rank> (0x3a3874: file ID 0xf05f + s8 [[quest + 0xa4] + 44]); every file lists all 94
GU monsters; Kushala (em 24): s1 = Low (Daora Horn), s2 = High (Horn+), s4 = G (Hardhorn), s0 / s3 empty (C).
GU cond of a group = 10 * (GU group + 1) (table 0x162a736); dala_break.c uses GU group = 4U group + 1.
The core hook (module/items.c bui_record_c) answers one record per monster for every rank: per-rank records need a
core change (user request 2026-10-21: rewards per quest rank and monster; plan presented, waiting for the OK).
Progress 2026-10-21 (built, not tested in game):
- Items: tools/items_em090.py -> the 30 materials appended as GU 2991..3020 (4U ID order, allocations.toml dalamadur
  items + [monster.append] items = 30), TBLA (GU DUMMY 2977 as the record template) + TXTA (5 languages); category
  = the most common one among GU materials with the same icon. Core: items4u.Materials.append_sections,
  tools/alloc.py no longer pool-checks appended items; module item patches / obtained hooks now active (n = 30).
- Break rewards per rank (user request 2026-10-21): BUI2 (High) / BUI4 (G) per entry, Shah G only; core
  module/items.c picks BUI<rank> (GU rank s8 [[quest + 0xa4] + 44]) with BUI as the fallback; break records in
  module/dala_break.c. Gogmazios' BUI section byte-identical.
- Carves: tools/hagi_em090.py (fields 46-50 per entry: s2 High, s4 G, filler elsewhere; tail = severed-tail kind;
  no 4U shiny set: base 0xffff). Wired: build_dalamadur_arc.py hagi_em090.files -> fields 46-50 (C, 2026-10-21).
- Names: tools/name_em090.py (NAME, both heads; tails share the entry). Notes: tools/notes_em090.py (Dalamadur:
  description only, threat 8, after Nakarkos, unlocked by quest 11494); Shah's entry needs a quest ID first.
- Armor DONE 2026-10-21 (approved; built, not tested): tools/gear4u.armors (several pairs; armor() = one pair,
  Gogmazios / Tigerstripe gen/ byte-identical), monsters/dalamadur/tools/gear_em090.py (choices in its docstring:
  templates Akantor HR / Akantor X, defense HR 75 / 38, EX 73 / 37 (below HR: GU weakened EX sets, to review),
  X 132 / 77, Z 134 / 78; PunishDraw -> GU 'Punish Draw', FreeElemnt dropped), allocations armor_series 8 /
  create 4 / process 28 / models 193..453; models: build.sh armor (80 arcs, tools/armor4u2gu.py; 4U m_arm298's
  untextured Scene_Material -> null slots, Capcom's rule from GU m/008/leg; Gogmazios / Tigerstripe arcs identical).
  Weapons: next (helper).
- Gear (original plan): tools/gear4u.armor builds exactly ONE series pair per
  monster (asserts armor_series == 2, armor_create == 1); Dalamadur has 4 pairs (Rebellion / Riot HR, EX, X, Z: 8
  series, 40 pieces, phase0.md). Plan: gear4u.armor takes a list of series specs (each: 4U piece IDs, GU template
  pair, defense anchor, model pair, recipes) and appends them in order; Gogmazios / Tigerstripe pass a one-element
  list (their TBLA / TXTA byte-identical, checked). allocations.toml dalamadur [monster.append] armor_series = 8,
  armor_create = 4, armor_process = the templates' rows, armor_models = the 4U model pairs (count from the 4U
  records: HR / EX and X / Z may share models). Weapons: tools/weapons4u.py lines per class (14 lines, 4U create
  IDs in phase0.md, upgrades into HR, G and Shah weapons), models / sounds through weapon4u2gu.py / wsnd4u2gu.py,
  as Gogmazios (gear_weapons_em089.py) and Tigerstripe (gear_em067_01.py). The same rules as those ports for the
  choices (templates of the same rarity, defense scaled by a set both games share, skills by tree name, recipe items
  GU lacks -> same-monster GU items), listed for review.
1. Items: ~30 appended (2991..), all languages, icons and colours.
2. Carves (head and tail), break / capture / quest rewards.
3. Armor: Rebellion / Riot HR, EX, X, Z: 40 pieces, male and female models, skills mapped to GU trees.
4. Weapons: every Dalamadur weapon in all 14 classes, models and sounds; elemental support in weapons4u.py.
5. Hunter's Notes (2), names in every language, map and quest-board icons.
6. Quests: Speartip Menace, Here to Eternity, Eternal Emperor on Speartip Crag.
   Full 4U set (wiki + data, 2026-10-21): Dalamadur: Advanced: Speartip Menace (Hub 7, ROM m10709), Advanced: Here to
   Eternity (Hub 7, HR100, ROM m10721), Pillar of Strength (event 7, m60131), The Speartip's King (event G3, m60209:
   the regular G Dalamadur = source of the "+" items); Shah: Advanced: Eternal Emperor (G3, 5th Aged Text, ROM
   m11030), The Crimson Shah (event G3, m60213). Event quests come from the user's DLC extdata (dump/extdata_4u,
   decrypted: quest1 / quest2, checksums OK, same 'v005' format; memory reference-4u-dlc-extdata). Their rank byte
   +0xC3 reads 0 (event): stars from the wiki until the field is found.
   Constraints found 2026-10-21 (C, monsters/gogmazios/notes/stage.md section 8, module/quest.c): GU loads loose
   questData files only for Hub G-rank IDs (filter 0x3b8090: stars 11-14), so a High Rank quest (4U Speartip
   Menace) needs another route or goes in as G (then its break rewards are the G ones: BUI4) -> ask the user.
   Faithful = 4U's ranks (the goal of every port, never a separate decision): a real High Rank quest AND a real
   G-rank quest (user 2026-10-21; HR drops forced into a G quest rejected). The G4-only quest was a DEVIATION.
   Today 11494 is G4 (template q0011425) with 4U m10709's text: only the G "+" items drop, so Pectus / Talon /
   Tail Shell / Fanblade (HR) cannot be obtained and 9 of 14 create weapons stay unlisted (smithy audit, C).
   HR route (quest helper 2026-10-21, v1.0 RomFS / 1.4 main; C unless noted): rank is questData DATA, not the ID.
   Raw questData 0x12 = star / board (HR 7), 0x13 = rank class (0x3a8d68: 0 village LR, 1 Hub LR, 3 HR, 5 G; ~900
   monster-code sites, G column when > 4), record +44 (raw 0x2E, S; 0x2E/0x2F/0x30 = 2/2/2 on every Hub HR quest,
   4/9/4 on G) = the bui_s / hagi / results rank (1 low, 2 high, 4 G; getter 0x3a8bdc, thunk 0x499a0), 0x1A = 7 on
   HR7 / 12 on G4. The quest_group loader filter 0x3b8090 is per scene ([[0x188ca48]+0x4c]): scene 0 Hunters Hub
   loads Hub 1-7 + Permit + Arena and REJECTS G (is_G 0x3b9e50), scene 7 Wycademy hub loads Hub 1-7 and G1-4
   (gogmazios stage.md section 8 "stars 11-14" holds for scene 7 only), villages 1-10; cap 864 loaded (scene 7: 814 +
   ours). So a real HR quest = an HR ID (Hub 107NN: 10790 / 10791 free, no file / list entry; avoid 10766 / 10767 /
   10769: orphan files) on our existing DUMMY-slot rename (module/quest.c), template q0010764 (HR7 Amatsu stage 18,
   bytes 7/3/7/2/2/2), no new hook. is_G(id) is also read by results (guild card G clear counter 0x38e9fc, G-star
   progress 0x38f29c / 0x38f3d4), so a G ID with HR bytes would be a hybrid: rejected. Slots: the pool is full
   (4 / 4); free catalog-safe DUMMY slots 1010007 (index 1307), 1010177 (1329). Checked: hagi s2 is wired
   (build_dalamadur_arc.py hagi_em090.files) and dala_break.c holds the same count in its LR / HR columns. Open:
   unlock gate (our hook answers 1); MP join / board / results traced statically only.
   Shattered Omen (user, 4U): mined from the fallen meteor scales during the fight (item 7 above, "meteors leaving
   mining points"): no source in the port yet.
   Meteor scale research (2026-10-21, C unless noted):
   - 4U: meteor kinds 3 / 6 -> 0x6626e8 -> uShell038; its init 0xc846c0 spawns the scale model (0xc08698, model by
     this+0xfd) and calls 0x9357ec(owner = shell+0x134 (the head), record 0x102fab4, pos shell+0x100, area
     shell+0x130, 0) -> handle at shell+0x26e; 1800 frames, removed 0x5b90c0 / 0x5b9ebc or when its floor piece
     breaks (0x6c5e88). 0x9357ec = 4U point kind 1 (0x5b90fc(mgr, 1)): +0x34 pos, +0x4c radius = rec f0 350, +0x50
     height = rec f4 200, +0x54 type = rec b8 29, +0x2e = rec b9 4, u16 +0x30 = rec h10 1, +0x2f area, +0x1a = 1,
     +0x28 item list = [0x1002a5c + 4 * (u16 0x1003ed4[em] + rec b12 0 * 4 + rank)], +0x78 = 0; register 0x5b9aa8.
   - Lists (em 24 base 1044; em 110 base 1112): High (rank 2) Shattered Omen 50 %, Gossamite Ore 30 %, Yoldspar Ore
     12 %, Novacrystal 8 %; G (rank 3, em 24 and 110) Shattered Omen 80 %, Cosmicite Ore 12 %, Purecrystal 8 %.
     Tails (83 / 111): none.
   - GU: same point manager (*0x1889ec0, 0x31b6e0(mgr, kind 0 carve / 1 pickup)), fields +0x4 pos, +0x40 life
     (3600 / 7200 f), +0x44 radius, +0x48 height, u16 +0x4e / +0x50 counts, +0x60, +0x64 type, +0x56, area
     0x3191a0, icon / kind 0x3191d8, item table 0x319358(point, table, flag), register 0x31abac(mgr, point, 0).
     Types seen: carve 1 / 17, shiny drop 17 (0xac0ec), 23 (0x1134a54 / 0x12176e8), 14, 15, 21, 31, 32. Stage gather
     points come from 36-B data records (0x31a4f4: type = rec +0x1e, icon = +0x1f, counts +0x1c / +0x1d, radius
     +0x10, height +0x14, item table 0x319eb8(data, rec +0)). GU's mining type value and the item-table format:
     to read from a GU stage's gather data (open). Files (C): /nativeNX/(loc/)arc/stage/map_com/mNN.arc hold
     rItemPopSet 52776ab1 'stage\mNNd\mNNd' (magic IPS, point placements) and rItemPopList 25fd693f
     'stage\mNNd\mNNd_{easy,low,high,g,tuto,clctN}' (item lists by rank) plus rSetItemData 0c6d4399. GU has 4U
     stages (Ancestral Steppe, Volcanic Hollow, Primal Forest, Frozen Seaway): compare their 4U / GU records to map
     4U type 29 (meteor scale) to GU's mining type.
   Mining helper (2026-10-21, C unless noted; scratch scratchpad/mining/): IPS / IPL formats are the same in both
   games (4U 0x5b9d18 / 0x5ba9b0, GU 0x31a4f4; IPL lists {u8 weight, u8 qty, u16 item} closed by weight 0xff, = the
   4U list format; GU rolls them weighted with 0x31b37c). Types match between the games (4U m01-m05 vs GU): 0 hand,
   2 mining (icon 9 outcrop, 10 rare), 3 bugs, 1 carve; GU dispatch 0x3007c4: 2 / 18 = mining, NO pickaxe in GU.
   4U meteor scale type 29 = treated as 2 by 4U (S); GU's 29 is something else (item 1733 slot): use GU type 2, icon
   0 (4U leaves +0x55 unset, S; 9 would show the ore icon). GU point (128 B): +0x38 item table (0x319358(p, t, 0);
   a static table in the 4U list format works), +0x40 life frames (0 = none), u16 +0x4e max gathers, +0x50 sure
   gathers, +0x55 area, +0x5c state, +0x64 type, +0x68 icon, follow +0x3c / +0x6c / +0x59 (0x319554; mode 1 =
   joint position, no offset); a used-up point frees itself 20 frames later (0x318b9c -> 0x31aaf4); release by
   handle: 0x31b16c(mgr, h) then 0x31aaf4(mgr, p). GU's own runtime template: uEm056 0xee4a68. Points are per
   machine (no net calls); the meteor's impact point comes from the synced action random -> same spot everywhere.
   Correction: uShell038 draws an EFFECT, not a model: init 0xc846c0 = 1800-frame timer + em024_006 / em110_006
   ({35 / 81, 5}) on the shell; ends on owner gone / dead, timer, or its floor kobj broken (0x6c5e88(stage, area,
   kobj +0x26c): kobj +0xb1 in 3..8 / 10); end 0xc84920: em024_007 / em110_007 at the point, sound 214, point freed.
   Point: type 2, 350 / 200, 1 gather (+0x30 = 1). Lists: meteor High idx 1046, G 1047 (Shah 1115 same); every qty 1.
   Head on-body point (4U slot 39 0x76d848, record 0xfdc924): {radius 400, height 600, type 1 (carve), count 2 +
   carve skill bonus (GU 0x69bfc)}, list b12 1: High (1050) Gazer 20 / Glaive 80, G (1051) Gazer 20 / Glaive+ 80, Shah
   G (1119) S.Gazer 20 / S.Glaive+ 80; moved each frame (slot 48 0x773c24) to joint 5 matrix * (0, 350, 400); never
   released (lasts until used up). GU items: Omen 3001, Gazer 2993, Glaive 2995, Glaive+ 3005, S.Glaive+ 3013,
   S.Gazer 3014 (S), Novacrystal 332, Purecrystal 333, Fucium 334 (Yoldspar), Meldspar 331 (Cosmicite); Gossamite Ore:
   no GU item -> dropped, its weight to Shattered Omen (user 2026-10-21); scale icon 0 = none, as 4U (user); plan
   approved (meteor scales + head point), implementation helper 2026-10-21. Open: which kobj the meteor hit (4U info byte 3 of 0x2b96e4; ours passes no info);
   carving a LIVE head with a type-1 point (GU 0x3009f4, untested); 0xbdc1f8 in the shell init not traced.
   Implemented (2026-10-21, not yet tested in game): module dala_gather.c (points, head point), dala_shell038.c
   (uShellDala038), section GPTS (tools/gather_em090.py, build.sh step gather), PEL records 2950 / 2951. Floor-piece
   end = a ground probe under the point (y +- 100) standing in for 0x6c5e88. Head point offset (0, 350, 400): x = s16
   = 0.0 (0x77333c, C). Seen on the way (S): 4U slot 48 also moves the carcass carve point W+0x7a48 to joint 5 * (s17
   = 80.0 if unchanged since 0x7734dc, 150, 200) every frame (0x773cc8); dala_carve.c places it once.
   port_monster holds 2 quests / 2 board slots per entry (dalamadur: 11494 + 1, shah_dalamadur: 2). Quest IDs
   11495..11509 have no GU quest file; their quest_group DUMMY slots still need the event-catalog check
   (0x1595e98) that 1011048 / 1011049 passed.
- Test: craft, equip, quest rewards; MP quest join (both players need the mod).

## Coverage audit (2026-10-22, static; scratch scripts dala_quests.py / mat_sources.py)
- Quests (C): every 4U quest with em 24 / 83 / 110 / 111 among its bosses, ROM quest00 / quest01 + the user's DLC
  extdata: m10709, m10721, m11030 (ROM), m60131, m60209, m60213 (extdata) = the six ported. All spawn records are
  plain (area 1, origin, byte +8 0xff): no quest starts Dalamadur in another state.
- Armor (C, phase0 gear scan): Rebellion / Riot HR, EX, X, Z(Shah) = 8 series, 40 pieces, all built. Palico gear:
  4U's Palico name tables (OtHelm / OtArmor / OtWeapon) hold only Gogmazios' pieces; none for Dalamadur / Shah.
- Weapons (C): 71 = one line in each of the 14 classes (gear_weapons_em090.py). Out of scope: other monsters' lines
  that use a Dalamadur part in an upgrade (e.g. LS 186 Barwell the Swift, Chameleos); SA 186 "Shah Bloodseeker"
  upgrades from Machalite / Earth Crystal / Monster Fluid (no Dalamadur material, S).
- Materials: every appended material has a source at its rank (carves HR / G / Shah G, break rewards r2 / r3, quest
  rows A / B / sub; Shattered Omen from mining); Dalamadur Scrap / Scrap+ have none: Palico-side items, no 4U armor /
  weapon recipe uses them (create table checked, C), 4U's scrap source (Palico rewards) has no GU counterpart (S).
- Moves (C): the 4U dispatchers' number tables against ours: head category 0 (0/1), 1 (0-11, 50-55, 60-92; 56-59
  default in both), 2 (0-5), 7 (0-4, 20-26, 40-46, 60-62, 65-88), 10 / 11; tail 1 (0-8, 50-52), 7 (0-3, 20, 21,
  40, 60-85), 10 / 11. Every number has a handler. Remaining module stubs: head cond 3 floor-7 player state, 11.x
  0x926014, meteor kinds 0 / 1 (not Dalamadur's).
