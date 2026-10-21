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

## Goal E: Speartip Crag
1. Stage alias: a new stage id hosted on GU m18 (the Sanctuary, 2 areas), redirected to new m29 paths while the
   quest runs (the Battlequarters route).
2. Convert m08a00d (camp) and m08a01d (arena): models, textures, collision incl. -shell, SIS, lighting, kobj
   k00..k02 -> GU k01..k03, map UI, area sounds, camp falling rocks.
3. Break wiring with D6; GU KowareObj check for mType 9..11.
- Test: walk both areas solo and in MP, then the fight with breaks.

## Goal F: content
1. Items: ~30 appended (2991..), all languages, icons and colours.
2. Carves (head and tail), break / capture / quest rewards.
3. Armor: Rebellion / Riot HR, EX, X, Z: 40 pieces, male and female models, skills mapped to GU trees.
4. Weapons: every Dalamadur weapon in all 14 classes, models and sounds; elemental support in weapons4u.py.
5. Hunter's Notes (2), names in every language, map and quest-board icons.
6. Quests: Speartip Menace, Here to Eternity, Eternal Emperor on Speartip Crag.
- Test: craft, equip, quest rewards; MP quest join (both players need the mod).
