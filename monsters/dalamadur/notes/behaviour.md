# Dalamadur behaviour port (goals D2-D8), state 2026-10-21

Static RE only, nothing run in game yet. C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
Framework: notes/port.md (GU action model), Gogmazios' em089_act.c (the model). Scratch tools in
dump/scratch/dalamadur-session/: d4.py (4U disassembly with literals, jump tables, names.txt), rxgen.py (reaction
tables), callees.py / fnlist.py (inventories), workread.py (readers of a work-struct field), callee-map.md (helper's
4U -> GU table for the 66 real callees, with confidence).

Class ranges (helper, C): head uEm024 0x76c700..0x776290 (0x75db78..0x76c6ff is uEm023, 0x776290.. uEm025); tail
uEm083 ..0x8a3160 (then uEm088).

## Files (monsters/dalamadur/module)
| file | 4U source | content |
|---|---|---|
| em090.h | - | fields, framework API, the 4U -> GU mappings used by both halves |
| dala.c | slot 89 0x76c700 / 0x89fab8 | framework (begin / chain / end / AI gate), partner, shared HP, paint, attack kind |
| em090_act.c | uEm024 slots 44 / 47 / 51 / 40 (part) | head: cat 0 / 1 / 2, action start (warp, meteors stub, rage end, HP floor), AI conditions, timers |
| em090_act7.c | 0x771e60.. | head category 7: 7.60-7.62, 7.65 group by me; the rest by the translation helper |
| em091_act.c | uEm083 slots 44 / 47 / 51 / 40 | tail: every action, follow table, action start, AI conditions, rage copy |
| dala_react.c | 0x772838 / 0x8a1bf8 + cat 11 | reactions through GU's sequence player 0xa134c, tables converted |
| dala_parts.c | slot 48 0x773304 / 0x8a1fec | hitzones, rec+0x3b4 flags, body attacks per motion, shakes, visibility rows |
| dala_walk.c | slot 48 set rule + 0x94cd6c | walk pieces as sCollision ground (as em084 / em012) |
| dala_stage.c | 0x6c3400 / 0x6c3b94 / 0x7731a4 | arena breaks through GU's KowareObj command 0, stage-8 rage hold |
| dala_meteor.c / .h | 0x77274c / 0x772ac4 / slot 40, uShell029 | meteor machine and the GU meteor shell class |
| dala_efx.c / .h | 0x76d77c / 0x89ffe0 / 0x8a27d0 / 0xc7cf18 / 0xc0819c | code-posted effects (PEL ids 2800..2911) |
| dala_break.c | 0x944e80 (break adder 0x9453b0), emd word 32 | dtbparts break records (both halves), break-count log |
| dala_psl.c | cMhMotionEffect 0x39170c (GU slot 75 0x70028) | test log of the motion (PSL) effect posts and their stop |
| dala_head25.c | head slot 77 0x774aa8, 0x689c08 | heat zone pulse + core hooks dala_heat_zone / dala_map_pos, 10/114 attack |
| dala_mat.c | head slot 39 0x76d668, slot 50 0x7746f0 | material animations (breath / usually / anger / death) |

GU vtable slots overridden by both halves: 1, 5, 38 (hit landed), 75 (PSL post), 118 (spawn), 119 (state), 125
(actions), 129 (action start), 130 (parts), 133 (AI conditions), 140 (= 4U 57), 143 (= 4U 60), 168 (walk), 209
(hit candidate), 240 (paint), 247 (end = 4U slot 89), 253 (AI gate), 264 (carve).

## Mappings settled here (beyond game.h)
| 4U | GU | what | conf. |
|---|---|---|---|
| 0x941dbc / 0x94a50c | 0xb0a30 / 0xb0a6c | at frame (impl r2 = 0 / 1) | C (same thunks into 0x727d0) |
| 0x93906c | 0xb0a60 | motionCheck with impl r2 = 1 | C |
| 0x920058 | GU 0xaff48 (inlined: setMotionEx unless the motion plays) | | C |
| 0x92b178 | 0x76a58 (setAction mode 1) | 4U tail follow chain; port uses setActionNext (MP replay) | C / design |
| 0x914dfc | 0x7df94 = attackEx(slot, idx, 0) | | C |
| 0x9197c0 | 0xa134c | reaction-sequence player; ops 3 (timer) and 0x3a identical | C |
| W+468 | rec+0x1bc | per-action timer (op 3 writes it in both players) | C |
| W+0x150 + W+0x198 | rec+0x0 + rec+0x40 | warp pair (GU 0xe2fd28 / 0xe30164 write both) | C |
| W+0x3f8 | rec+0x380 | HP floor ratio of setHP 0x9a764 | C (GU) / S (pairing) |
| W+0x42c | rec+0x3b4 | detached / state bits (bit 0 tail severed, 0x91a884 = GU 0xa3cb0) | S |
| W+0x530 / 0x93399c / 0x91ad80 | rec+0x518 / 0xbce6c / 0xbd128 | rage byte / set / calm | C / C / S |
| 0x91b268 | 0xbd114 (rec+0x521 = 2) | stage-8 hold while k00 stands | C |
| 0x91b158 | 0xbcb9c(this, 1) | battle state engaged at spawn | S |
| 0x92213c | 0xbd650 (rec+0x5d02 = 1, +0x5d00 = v) | cond-0 visibility (group 23) | S |
| 0x910c6c | 0xc24d8(this, joint, id, 0) | camera shake at a joint | C (Gogmazios) |
| 0x922cd8 / 0x93c6c8 | 0x7fcbc / 0xc0410 | rec+0x36b = 1 / rec+0x3a2 = 2 per frame in the moves | C (game.h) |
| 0xb052c4 | 0x72708 | timer up (work+4 action time, work+8 placement time) | S |
| 0x6c3400 / 0x6c3b94 | KowareObj command 0 (0x514f9c) / action byte +0x185 | arena break / broken | C |
| 0x68fd44 | module registry (dala_register_half) | partner lookup | design |
| 0x910650 | slot 240 base 0xc0908 on both halves | paint | C |
| 0x911cc8 + 40 * i + 0x19 | k_atk_kind[] (dala.c) | attack kind noted at work+0x58 / +0x5c | C (data) |
| 0x661d18 | request 0x48c4f0 (shell 0x122) | tremor (tail 7.0): not wired yet | C |

## Multiplayer
- Every handler runs on every machine (GU replays actions); AI, HP writes only on the controller.
- Tail follow: GU setActionNext starts the action on the controller and queues a local replay elsewhere.
- Arena breaks: every machine breaks its own kobj at the 4U frame; GU's command returns when the action already
  plays and broadcasts it when online, so one break per machine.
- Shared HP: the head's controller applies both halves' HP losses to both (dala_hp_sync); others never write HP.
- Walk pieces / visibility: every machine computes them from the replayed motion, placement, ranks and rage.

## Test 2026-10-21 (third install, TEST_HP_PCT 10; log Ryujinx_..._2026-10-21_17-55-03)
User: tail up in the air (should be about ground level or lower); body missing after the back, an isolated
climbable piece with garbled textures elsewhere; no monster sound; Dalamadur does nothing; not sure damage lands.
Lighting fixed (build_speartip.py filter_4u_only); Gogmazios / Tigerstripe item names fixed (items.c).
Log (C): both halves combat byte rec+0x2c0 = 1 from spawn (setBattleState). HEAD target slot 0 stays kind 1 param
255 (= none) all fight -> its root (g0 s0: blk0a combat, op01 00 00 00 00 -> GU 0x862cc, blk11 slot 0 param != 255)
idles in 1/0. TAIL root has no op01; GU's generic targeting gave it kind 1 param 0 two s after the hunter entered
area 1; the tail flinched (10/7) repeatedly and its break counters moved: hits land on the tail. "gogport: dmg special
path" (~240 / s) is per-frame noise of the damage function's 0x8187c branch, not blocked damage (G: verify HP).
Open: why the head never gets a target (GU 0x862cc refresh / the sensor: head data, joints?); the join (helper on
it: class-study.md "Where the body is cut" was WRONG to call the gap 4U's: 4U motion 1 has a bone-0 track
(-2282.1, 1644.4, -1488.2 + rotation), motion 101 none: something joins the tail's root to the head); no sound.
AI helper result (dala_ai.c): head cond 3 / tail cond 4 = target floor class via GU 0x979cc (= 4U 0x9463d0) and the
4U floor tables (C); at full HP / placement 0 the head's table plays 1/53 whatever cond 3 says.
Fixes for the fourth install (built, installed, not yet tested):
- Join: dala_join.c (class-study.md "Where the body is cut"): the tail's bone 0 = the head's every frame. Log
  "dalaport: join copy|world head mot .. tail mot .. j0 head .. tail .. gap N" (gap ~0 = no lag).
- Head target (C, code + data): op01 00 00 00 00 -> 0x862cc -> setTarget 0xc6e14 -> 0xc5b14 takes only hunters set in
  the noticed mask ai+0x24d, which the sensor 0xc3144 sets (area match, then 0xc3d08: eye near radius > distance, or
  the vision cone). The eye record (dttune +0x78, index ai+0x249, GU 0x71144) was Kushala's (bone 3, near 400): on
  Dalamadur bone 3 is a head-chain segment. 4U etd word 9 = the sensor table: em024 / em083 / em110 / em111 all
  {bone 0, 50000, 50000, 10000, 10000, angles 0x8000 / 0x4000}: 4U Dalamadur notices the hunter anywhere. GU record =
  4U record + two u16 0 after the bone (64 records of the shared monsters: bone 63 / range 61 equal).
  tools/dt_convert.py RECORDS, opt-in `build ... --sensor` (Dalamadur's build.sh dt step; Gogmazios' files unchanged:
  it keeps Kushala's eye, flagged for the user).
- Sound: judge once the head acts (its actions carry the roar and most sounds).

## Test 2026-10-21 (fourth install; log Ryujinx_..._2026-10-21_18-43-34, 120 FPS patch on)
User: "much better". The head targets (frame 1224) and fights: 7/60, 7/61 arena breaks, 1/53, 10/7, 2/3 meteors,
7/62 spire, 7/40, mode 2. Join log: gap 0, tail motion frame = head's or one behind. Remaining:
1. No sound at all (code sounds too). Cause S: arc entry order. GU's own arcs (em024_00 / em001_00 / em071_00, C)
   store waves -> bank -> request; ours had the request (35) before its bank (168) and the waves. Fixed in
   build_dalamadur_arc.py (rank: waves 4, bank 5, request 6 after everything else).
2. Model looks wrong over the whole body (screenshot: grey tiled pattern). Helper (C): textures, mips, UVs, weights,
   normals, slots and feature variants all check out; the tiles are 02_BM's belly plates (tail body: body5_nm,
   body2) drawn in inverted contrast = a term weighted by the specular mask, seen from below. 4U em024 / em110 have
   no environment map on any material (bMaterialStdEnvMap 0) and body4_nm / body5_nm no extend map, but GU's
   'solid' template (em030) reflects a cube map at 0.1: now fReflectiveColor 0 on 'solid' / 'solid_at'. Also
   solid_sphere fSpecularColor (0.7, 0.3, 0.3) (em019's red tint) -> (0.5, 0.5, 0.5). Still open if the pattern
   stays: the sphere materials' reflection 0.5 (4U fMaterialStdReflect 1 on the extend map) and 4U body5_nm's
   fMaterialStdAmbient 1 (others 0; no GU constant found).
3. Head / torso slightly too high, front legs off the ground; 6. body far too low on the peak after an arena break.
   C: both objects at y 301 from the first frame (4U: spawn point (0, 0, 0), build_dalamadur_quest.py). GU's ground
   probe 0xbdf1c / adjust 0xbe010 move enemies onto the ground unless rec+0x5cd5 is set; Ahtal-Ka / Ahtal-Neset
   set it every frame in slot 119 (C). Port: REC_NO_GROUND every frame (dala_state_frame) + y = 0 at both spawn
   setups. S: the peak stance was GU dropping the object when the surface under the origin broke. Log "dalaport:
   obj head|tail at x y z action .. motion .. mode .." on every move over 10 units (should stay 0 0 0).
4. The cm000_002 arrows (2800-2802) never went away; user: in 4U they stay as long as that part is walkable. 4U
   hides them in slot 41 (no caller found, C); port: dala_efx_body_walk on every walk-set change (0 = stopped).
5. Animation "glitch for a frame or two, then normal" during the arena breaks. S: the same ground adjust snapping
   the object onto changing surfaces (breaking kobj, the other half's walk pieces). Check the obj log.
7. Meteors 2x fast (C: kind 4 fell 9300 in 2.18 s, 4U 70 / frame = 4.43 s), visual landing away from the blast,
   no sound. Every Dalamadur shell stepped by its own +28 (1.0 per 60 Hz tick, the monster's 0.5: Gogmazios'
   finding); now dala_shell_dt = the head's EN_DT. S: the 4U meteor effect flies its own path timed to 4U's fall,
   so the 2x shell blew up before the visual arrived. Kind 7 falls round a fixed 4U centre (table 0xfdc964, C).

## Test 2026-10-21 (fifth install; log Ryujinx_..._2026-10-21_19-21-46)
User: sound back; height fixed (objects stayed at 0 0 0: no "obj" line, C); arrows and glitch fixed. Still wrong:
- Model: "specific parts spread across the body, the huge back spines are the perfect example" (7.png = spines from
  below). Not textures / constants / proxies / cross-half skinning (C). Helper 2: per-mesh normals, winding,
  tangents all fine (C); the pattern sits on body1 / body2, the only materials built as 'solid_sphere' (sphere
  reflection 0.5 with 03_BM, shininess 30), and it peaks where the +A mask is low (S). 4U's sphere / reflection ints
  of body1 / body2 equal Gogmazios' body (shipped as 'solid', looks right) and Kushala's (C); only Tigerstripe's E0
  (SpecularColorType 2) need the sphere. Builder: solid_sphere only when iMaterialStdSpecularColorType == 2 ->
  body1 / body2 now 'solid', reflection 0 (4U's extend-map sheen dropped, as Gogmazios'). Helper's 4U render: the
  7.png sheet is a belly plate band (tail mesh 25 / neck mesh 49), the real back blades are mesh 38 (g104 body4_nm)
  -> the test decides. If the 6.png fins stay noisy: 'alpha' material (solid_at, 04_BM dithered alpha, ref 30).
  Faithful sheen later: Capcom's Kushala setup (solid_sphere, tSpecularMap = BM, fReflectiveColor 1).
- Head hitbox sometimes off the model, at least on the peak (mode 2) -> open.
- Meteors: still too fast (C: kind 4 still 2.19 s, so the head's EN_DT moved exactly as the shell's +28) and the
  visual lands away from the blast. Now the Gogmazios clock (dala_shell_tick: quest countdown x 30 / target fps);
  log "dalaport: shell pace clock N/1000 (fps F) head delta D/1000".
- Rewards: only the template's rows -> rows A / B from 4U m10709 (rem_m10709a / b; items_em090 OTHER_4U_GU +9
  name-matched items), slots 2 / 3 the template's, subquest row A.
- Meteors after the death: 4U resets the machine in head slot 52 0x773128, called by the base death path 0x9263a4
  (0x926f04, C) -> dala_meteor_reset + work+0x3c = 0 at the category-11 action start.
- Permanent beam after the death: the beam ends on "owner motion changed" or life (drained by the owner's motion
  step); the death plays 0x329 (cat-11 table) and the dead body stops -> end on owner category 11 (deviation).
- Back not fully walkable (steps to climb, the far end unreachable, camera stuck vertically) -> open.
- No carving -> open.

## Test 2026-10-21 (sixth install; log Ryujinx_..._2026-10-21_20-04-46, 60 FPS this time)
User: meteor speed fine (log: clock 0.5 = head delta 0.5 at 60 fps); rewards fixed; meteors stop at the death.
- Model unchanged: "all over its body", close-up 9.png = dark plates, thin bright lines, 4-point stars = the '+A'
  specular mask over a near-black albedo. Capcom's GU Kushala (same 4U ints, same dark albedo) uses the BM itself as
  tSpecularMap (C, helper 2) -> builder: tSpecularMap = BM for every material, no '+A' textures packed.
- Meteor blast at one fixed arena point: world-position posts (dala_efx_post_at) leave req+0xd0 empty, GU fills
  the owner's model, the place-once record lands at the head's origin (S) -> the blast (dala_shell003.c) and the
  fireball impacts (dala_shell001.c) post on their own shell (4U posts from the shell, C). Gogmazios' em089_efx.c
  world posts may share the bug (flag for the user, not changed).
- Fire at the dead head's mouth repeating; tail alive after the head's death. Helper (C unless noted): GU's
  category-11 tables end with op 7 before 0xff (Kushala 11/0 0x17bb4e8 {0x312, op 7, 0xff}; Gogmazios never reached
  12/255 without it); 4U's are {motion, 0xff}. Ours lacked op 7: the head stayed in 11/0 and 0x33d replayed its
  mouth effect (S) -> op 7 added to T_fdcaa4 / T_ff5e18 (dala_react.c); likely also why carving never started (G).
  Death trigger (both games): only the damage update starts a death (GU 0x97ddc controller-only: rec+0x5d66 test
  0x98be4, HP <= 0 0x98cbc, rec+0x3ae = 1 0x99134, chooser 0x9b2bc -> 0x76afc 11/n; 4U 0x920a24 / W+0x426 /
  0x92c0a4); dala_hp_sync's setHP(0) never runs it. How 4U kills em083 itself: NOT found (pool HP = 0 on both
  halves 0x9201cc). Port: dala_death_sync (dala.c, head slot 119): once one half is in 11 / 12-255, the other's
  controller sets HP 0, floor off, rec+0x5d66 = 1 (GU's own death path), fallback 0x76afc(11, 0) after 60 frames.
  Logs: "dalaport: death head|tail 11/N motion ..", "death sync ..", "death head|tail reached 12/255".
- No Dalamadur armour / weapon in the smithy: create records keep the Akantor template's +8 u16 and the first
  material's flag byte (G: unlock condition / key material) -> open, compare with Gogmazios'.

## Test 2026-10-21 (seventh / eighth install)
- Skin: the spec map = BM change did nothing; the user: right in the first tests (Amatsu arena, first Speartip
  build), wrong since the lighting filter. Cause (C, user-confirmed A/B): build_speartip.py filter_4u_only had
  switched off GU's monster light EM02-InfiniteLight (4U's arena has only EM01 / EM03). Back on = skin right, and
  the user prefers the arena so. The material changes made under the wrong diagnoses stay for now (solid_sphere
  red specular -> 0.5: a real fix; 'solid' reflection 0; body1 / body2 'solid' instead of 'solid_sphere'; tSpecularMap
  = BM): open whether to restore 4U's extend-map sheen (solid_sphere + sphere 03_BM) in a later A/B.
- Meteors: the user's 4U footage = about 2 s from sky to impact = the shell's own +28 pace (9300 in 2.19 s); the
  real-time clock made them "2x slower" -> dala_shell_dt = the shell's +28 again. The earlier "too fast" report was
  the blast showing at the head's origin. Explosions now at the impact (fixed, user).
- Death: the tail died only through the 60-frame fallback; "reached 12/255" never logged (logged from the head's
  slot 119, which may not run for a corpse); no carving; the fire appears only AFTER the death animation (user) ->
  helper (carcass state, carving, post-death effect). Quest ends normally.
- Carcass helper (C unless noted): 12/255 is the body going away, not the carcass. GU's reaction player end
  (0xa16d4) runs a step machine on rec+0x550 in 11/0: step 0 (0xa1734) carcass timer rec+0x1bc + vt slot 264 (base
  0xac6c4) -> 0xaba9c carve point -> rec+0x5d38; step 1 = the carcass; 1->2 releases (0xac898); 2->3 motion fade;
  3->4 = 12/255. Carve point from the dtbparts carve records (obj+0x6c, count +0x8e, 12 B {kind, carves, u16, f32
  radius, u8, joint, u8, u8}); ours were Kushala's placeholders {0, 4, 600, joint 255} = the object position (0, 0, 0)
  inside the spire: nobody could carve. 4U (table 0x1003bec, 0x926044): head 4 carves r 1200 joint 5, tail 4 / 1700 /
  joint 101, severed tail 1 / 350 / 255. dala_carve.c installs them + slot 264 per half; point y = the stage floor
  under the joint (deviation: 4U's W+0x624 for an origin-held object unknown, G). Post-death fire: not proven; the
  death motion 0x33d's PSL posts em024_012 (blue-purple, joint 6 + (0, 600, 500), frames 35-76, 122) -> motion speed
  0 once the sequence is over (G). Logs: "carve records ..", "carve head|tail point ..", "carcass head|tail ..".

## Test 2026-10-21 (ninth install; log Ryujinx_..._2026-10-21_21-27-33)
- Carve: points created (head joint 5 at y 490 r 1200, tail joint 101 at (-5690, 3723, 2900) r 1700, C) but the
  floor probe hit nothing: mapSegment takes (end, start) (the working callers pass the lower point first), ours cast
  upward -> point y = joint y; hunter within 304 of the head point but dy ~-260 (GU window 150). Fixed (args swapped).
  The tail point sits at the tail instance's rest-pose joint 101 (high, far): open, check where 4U puts it (user: 2
  carve spots on the head part + the severed tail).
- Post-death fire: still there with the motion frozen at 747 and no code post after the death (C) -> not the death
  motion's events. Screenshots 7 / 8 also show a purple aura on the hunter: asked the user which it is.
  Correction (fire helper, same day): it IS the death motion's event, posted once and never stopped. 0x33d slot 7 =
  MEF 253 (em024_012 element 1 = the three blue-violet billboards, joint 6 + (0, 600, 500), scale 7, frames 35-72,
  MEF slot mode 1); PEL_TAIL places it once (frame 35) and its EFL loops (S: it outlived the frozen motion).
  4U (C): MEF byte 1 = slot mode; 0x391b50 tracks mode-1 posts in 4 slots, 0x39170c clears their active flags each
  frame, 0x391a18 re-sets them while the event bit is on, 0x390b40 kills (0xc470dc) a mode-1 effect left inactive =
  dies at its range end. GU (C): the PSL player 0x31d218 / 0x31d530 hands each post &ctl[slot] (effect +0x194) and
  pulses bit 2 on the run's falling edge (slot 8 0x31d200), 4 on a motion change, 8 on a wrap; a frozen motion returns
  early; 0x329668 latches them (+0x198 / +0x199 / +0x19a); 0x329dbc: record +0x3a end mode 0 stops on 4 / 8 only, end
  mode 1 on 2 / 4 (a finished one goes to state 3, run as state 0: replayed until the stop, S). Our PEL_TAIL = end
  mode 0 on every MEF record, the dead
  head never changes motion -> forever. Corpus (S, 72 GU enemy arcs): runs > 5 frames end mode 1 in 2130 / 2213,
  1-frame runs end mode 0 in 6795 / 6859; Dalamadur's slot-1 records are exactly its multi-frame runs.
  Fix: build_dalamadur_arc.py pel_slot_end: list-1 records of MEF slot mode 1 (_0 and _1: LMT events name both, 4U
  0x391a18) -> end mode 1 (41 records em090_00u, 53 em090_01u; arcs: only the PEL entries change, 1 byte per record).
  Also ends the breath / beam effects at their range end instead of the motion end (4U behaviour). Log: dala_psl.c
  (slot 75 = PSL post 0x70028): "psl post" (deaths, end-mode-1 posts) and "psl fx" (state / stop latches, end).
  Same latent issue in Gogmazios (12 slot-mode-1 MEF ids with end mode 0; not changed, tools/efl4u2gu.py proposal).
- Smithy: core bug (C): our obtained_test_c (module/items.c) returned the raw bit, GU's 0x19443c returns 0 / 1
  (`movwne r0, #1`) and its callers `cmp r0, #1` (smithy key material 0x6fa928, shop, Trader, Palico smithy ...).
  Gogmazios / Tigerstripe gear showed only because the save had listed it before the hook existed (S). Fixed: 0 / 1.
  Headroom (C, editor save map): the smithy "listed" bitmap holds 576 records per armor part; A00 is at 569 (7 left).

## Test 2026-10-21 (tenth install; log Ryujinx_..._2026-10-21_22-12-23)
- Weapons (weapon helper): holes / shards were GU templates that alpha-test an opaque 4U material against the BM alpha
  (the 4U specular mask); tools/weapon4u2gu.py --alpha-test-4u (build.sh weapons). User: fixed, but the HBG showed
  two long pink planes: its additive strip carried rod005's copied animation (v scroll -1 -> 0 / 500 f) instead of
  4U's u scroll 0 -> 1 / 100 f, sampling other parts of the sheet; the hammers had u reversed. --anim-4u converts the
  4U animation when the template is not Capcom's exact pair and every track maps (mrl_anim.gu_entries): hbg024 /
  hbg047 / ham059 / ham107 MRLs changed; rod006 / rod040 came out byte-identical to their Capcom templates (C, a check
  of the converter). The 7 reflect-colour glows (swo / sou / gaxe) keep their template blocks (same 4U keys, S).
- Post-death fire (C, log): MEF 253 posted at 0x33d frame 35, stop latch at 73, dead by 105; record +0x36 = 3 (a
  follow mode, 0x32a548: S that it follows joint 6). User: the fire is gone; 4U shows a blue-violet glow at the
  mouth for ~1 s that follows the head (user, 4U memory) -> check that it shows at the next kill.
- Tail carve (C): the user could not carve; the log had the hunter inside the tested window of our point (dxz 596,
  dy 11). 0xaba9c takes x / z from 0xc1708(this, joint), the instance's OWN joint (0xabbb0), so the tail's point stayed
  at its rest-pose joint 101 whatever we probed. Fix: dala_carve.c moves the created point (manager *0x1889ec0 +0x24,
  128 x 128 B, handle s16 +0x4c) to the head's joint 101 x / z. Log: "carve tail point N: moved, GU x / z .. -> ..".
- Smithy (smithy helper, read-only, save slot 1 checked): no table bug. 0x6fa928 lists a create entry when its
  condition (file +4 mDispFlag, ours 0 = always) holds and every mKey-2 material (ours: the first) is obtained (C).
  5 of 14 listed (Hammer, Lance, HBG, LS, GL) = exactly those whose key material was obtained; the 57 others are
  upgrade-only (4U: one create per line, C). Cause: quest 11494 is G (template q0011425), 4U m10709 is High Rank,
  so the G carve / break tables run (+ items only): Pectus, Talon, Tail Shell, Fanblade cannot drop. Shattered
  Omen has no source at all. Closes the "Akantor +8 u16" note above: condition 0 and mKey [2,0,0,0] are set by
  weapons4u.py, GU's majority pattern, same as Gogmazios / Tigerstripe (C). Open: the High Rank route (plan.md).

## Open (ordered)
1. Head category 7: DONE (helper translation 2026-10-21, spot-checked against 0x76ec80). Its stubs (logged):
   the look system (W+0x79cc..0x7a12, look point 0x93e974, look mode W+0x79d0 = 3: no GU field), the render flag
   this+0xca8 (0x800 / 0x1000 / 0x4000; 7.40 picks by the ground probe 0x2b9fa8), the shell post 0x77250c (via
   0x661bec, kinds 24 / 25, Shah 88 / 89), the quake post 0x6620c4 (subtype 21, Shah 39), Shah's effect slot
   0x7756d4. Own translation without GU twin: the aim weight 0x948800 (layer-1 weight of 7.21 / 7.23 / 7.40 /
   7.87, target slot rec+464, atan2 as em089_aim.c). Extra mappings: 0x9175a8 = GU 0x76e8c, 0x955478 = 0x7b5f8
   (groundSnap), 0x2fcc50 = 0x4efd74 (sound ids 215 / 216, Shah only), 0xb054e0 = layer1SetWeight 0x726dc,
   W+356 / W+412 = rec+0x14 / rec+0x44. The cond-7 state word is 4U W+0x7a14 (earlier notes said 0x7814).
2. Shells (D5). Meteors DONE (helper 2026-10-21, dala_meteor.c / .h): set-up 0x77274c (dala_meteor_set), reset
   0x772ac4, the slot-40 machine (dala_meteor_frame; pattern / centre tables recovered by emulating static init
   0xd25968), uShell029 as GU class uShellDala029 (init 0xc7cedc, frame 0xc7d268, kill 0xc7da24; our copy of the
   request 0x48c4f0; lifetime 180, fall speed 90 / 70, map segment test, sounds 204 / 205 / 210 / 213). W+0x1d2 =
   GU this+0x73e8, the action's random u16 (setAction draws it and the action packet carries it; GU 0x76560 /
   packet +0x73ee), so every machine computes the same pattern. 4U posts meteors on every machine (no controller
   gate, local shell manager), kept. Placeholder hit data: Kushala's shell family (file 0x8a02, row 175), powers
   80 / 100 instead of 60 / 45; a proper family needs HDS from 4U 0x102dff0 + 40 i (i 2..5) and HTS volume 2 at
   0x102df8c (sphere, bone 1001, r 270). The attached effect (0xc0a2f8 group 35 / Shah 81, element 3) = PEL 2900
   (item 3); the shell waits for it to end before it dies (Gogmazios' deferred kill, forced after 300 frames).
   Stubbed: the impact blast (0x663220 -> uShell003 type 3,
   subtypes 113 / 126 / 160 / 162), the mining point (kinds 3 / 6 -> uShell038 0x6626e8: a 4U gathering node via
   0x9357ec for 1800 frames; GU has no runtime gather-node API found). Not wired: 0x772ac4's other caller 0x773128
   (head vtable 0xe66cf0), Shah's effect expiry loop 0x76de94.
   Other shells: uShell016 (0x6620c4, subtypes 21 / 39 Shah; Gogmazios' em089_shell016.c), uShell005 tremor
   (0x661d18 -> GU 0x48c4f0), 0x77250c's shell (via 0x661bec, kinds 24 / 25, Shah 88 / 89), uShell003 (impact
   blasts, tail), uShell015.
3. Effects (D5): code posts WIRED (helper 2026-10-21, dala_efx.c; build: build_dalamadur_arc.py effects() adds
   the records, efl4u2gu.py pel_record takes per-record `follow` / `colour`). How 4U names the file (C): no MEF
   record; the flat table 0xef895c[group][element] (0xc0a2f8 / 0xc088d8 requests) or uEffect002's id table
   0xfd0b94 {u8 group, u8 element} (28 -> cm000_002; the table also gives Gogmazios' / Zamtrios' known ids).
   PEL ids (both PELs, the tails post their head's, manifest field 17 shared):
   | id | EFL | joint | offset | scale | k | 4U |
   |---|---|---|---|---|---|---|
   | 2800 / 2801 | cm000_002 | 200 / 5 | (3850, -945, -805) / (0, 500, 1000) | 8 | 2 | head spawn 0x76d77c, offsets from static init 0xd25968 |
   | 2802 | cm000_002 | 142 | (970, -110, 865) | 8 | 2 | tail spawn 0x89ffe0, static init 0xd2a860 |
   | 2900 | em024_003 / em110_003 | -1 (shell) | 0 | 1 | -1 | uShell029 init 0xc7cf18, table 0x102e124 |
   | 2910 / 2911 | qe013_002, colour (120, 85, 80) / (143, 76, 58) | 157 | (0, 0, -950) | 4.5 | -1 | tail 10/114 0x8a27d0, 0xc48378 by em 83 / 111 |
   All with the follow tail (PEL_TAIL_PREV: G for joints, shown by test only for shells). The tail smoke keeps 4U's
   local-player-area gate and is stopped after 120 frames (qe013_002 loops in GU, Gogmazios' deviation). Open: the
   scale 8 of cm000_002 vs the model scale (Gogmazios' uEffect002 came out 2.5x too big through the monster: check in
   game); the radial blur 0xc0819c (1.3-1.11 / 2.x, joint 5: logged, no calibrated GU blur, as Gogmazios' roar);
   the heat aura uMhEftCtrl004 0x326a6c (em024_016 / em110_016, joint 4 mask 8 offset (0, -500, 1100) or joint 101
   mask 16 offset (500, 1300, -700); sibling 0x326c40 reads work+0x54) not ported; the 28 draw test 0x19fbf0 (no GU
   counterpart: always drawn) and 4U slot 41 (hides the 28 effects, caller not traced); 4U's 0x94e39c(this, 0, 0,
   &point) before the tail smoke (point (1784, 232, 2397) / placement 1 (-1080, 641, 3750)) not ported. Material
   animations at head spawn (0xcfba14 / 0x636b64 = GU 0xb0bb0c / 0xb0cab0, C; "breath" / "usually", "anger" when
   enraged, "death" when dead, switched by 0x7746f0; MRL animations, GU counterpart of 0x1a4814 unknown): open.
4. Shah (D8): persistent effect states work+0x6c..+0x70 / 120.. (0x7753f4 reset, 0x775f2c expiry), net bytes
   (4U slots 78 / 79 -> GU 171 / 172), Shah hitzones are ported (dala_parts.c).
   DONE 2026-10-22 (helper + me, built, untested; dala_shah.c, header comments hold the 4U reading): crimson bytes
   re-rolled by the controller at the motion end of 2.x / 7.65 / 7.68 / 7.80 (0x7753f4: count table calm / enraged,
   part weights by mode), sent in the action message (GU slots 171 / 172 after GU's base bytes 0 / 1); zones k 0..2
   armed by 0x7756d4 (7.x frames) for 1200 frames on every machine, effects em110_200 / 203 / 204 (PEL 2970..2975,
   world-space files; uEffect003's fade replaced by stop + kill after 40 / 20 frames); the hunter side (0x687280:
   box + floor 2 / 6 / 5) counts as heat for GU's heat tick through dala_heat_zone (GU's Teostra tick values, not
   4U's own -2 damage / effect 114 / sound 36: deviation). Not ported: slot 36's event 48 (all five on, placement 2).
5. AI condition 3 (head) / 4 (tail): 0x93e074 -> 0x9463d0 probes the collision between the monster and target
   slot 0 (0x2b9fa8) and returns a ground / attribute class 0..10 of the target (7 = then a player / Palico state
   test); not mapped (returns 0 now): needs the GU probe and Speartip's SBC attribute values.
   AI audit 2026-10-22 (helper; user: "doesn't have all its moves, spams the same"):
   - TEST_HP_PCT=10 puts both halves in HP band 6 (< 17 %) all fight: 4U's desperation selectors only (head g0
     s7 / s14: ground 1/53 only, peak 7/40 / 7/42 / 7/43 / 7/44 / 7/46, 1/2, 1/65 (+7/88 Shah / G); tail ground
     1/0, peak 1/2 at 99 %). About two thirds of the moves live only in bands 0..5 (S: faithful). No cooldown or
     last-action memory in the table (C). AI tests need a full-HP or TEST_HP_PCT=60 build.
   - GU has no EMC op 0x46 (4U 0x951ff0, switch on the em number W+0x1c0); GU 0x8470c skips the token, so each
     case body ran in turn: the head root g0 s0 called the Shah and the rank selector on every pass (two picks;
     regular HR quests reached the Shah-only 7/86 / 7/87 / 7/88). C. Fix: build_dalamadur_arc.py emc_em_switch
     rewrites the 7 blocks as op 0x6f condition 70, answered by dala_cond_em (24 / 110 from the variant).
   - Interpreter ops 00 / 02 / 0a / 11 / 14 / 1c / 20 / 6a / 6f match 4U (C). Never reachable in either game: 1/52,
     1/54, 1/63, 1/66, 1/70, 1/74..1/78, 7/3, 7/4, 7/25, 7/45. Logs: "ai .. start / think / tally" (dala_ai.c).
   - Open (G): in the Shah test s48 (7/43, 7/46), 1/65 and s57 (7/88) never ran (< 1 % by chance); the tally
     log will show whether those picks are replaced before their first frame.
6. One attack damages one half only (4U 0xbf4d28): DONE 2026-10-22 (built, untested; dala_react.c): GU's Nakarkos
   rule, hit +0xb5 bit 0x20 set after the hit call (slot 38) and refused by slot 209 (vt+0x344, the per-enemy
   candidate test 0x81a14 <- 0x16b450) (C).
7. Rage / KO forwarding tail -> head (4U 0x921d1c, 0x92712c) and shared reactions (0x948b9c).
   DONE 2026-10-22 (built, untested; dala_react.c, core hook dala_dmg_end at GU 0x98e44 = after the rage add 0x98e20,
   before the reaction dispatcher 0x9a828, r0 = this): rage = GU 0xbcc04(this, n) (= 0x933b30, C: hold rec+0x521, HP
   ratio table, at the threshold request 4 in rec+0x362 = 4U W+0x3d8); the tail's meter rec+0x510 goes into the
   head's rage add, then 0 and request bit 4 cleared (0x92b2d0). Shared reactions: 4U posts kinds 1 / 3 / 14 / 31 /
   45 / 46 (part W+0x42a, 14: W+0x42b) to mgr+0x32c / +0x32e and both halves run the kind next frame through the
   dispatcher's switch; GU kinds = 4U's (1 = death in both, C; others one call each, S), kind rec+0x3ae, parts
   rec+0x3b2 / 0x3b3 (C). Port: a half's update ending with 3 / 14 / 31 / 45 / 46 posts; the partner's next update
   takes it when its own kind is 0 (its no-damage path rewrites the kind, so only the hook point is safe; death
   stays with dala_death_sync). Logs "dalaport: rage tail", "shared reaction". KO (field +72 -> 0x935194 = stun add
   with params +0x48): NOT ported (G, low: the tail takes little KO); GU stun add = 0xa3300(this, n) (meter
   rec+0x5d8e, threshold +0x5d90, returns 1 at KO, C), its KO trigger (r10 in the 0x9a4xx status function) not traced.
   Class slots found 2026-10-22 (vtable coverage check; head vtable address point 0xe66c20, tail 0xe69fac, C):
   4U slot 60 (break flinch: part -> 1 plays the break reaction 0x94b9e0) = GU slot 143 (0x9b030 -> 0x9e83c), DONE
   (dala_break_flinch, both halves: parts 0..4 by the head's counts, 7 by the tail's); 4U slot 57 (second-part filter
   for reaction 14) = GU slot 140 (0x989f4), DONE (dala_part_ok); head slot 64 (on-break: W+0x42c bits 0x800..0x8000
   by part rank) DONE in dala_parts.c (per frame; GU slot 214 is a predicate, not on-break); head slot 77
   (0x774aa8, per frame) = dala_head25.c; head slot 50 (0x7746f0, material animation states) = dala_mat.c; slot 82
   (head 0x773174: placement 2 and arena class 3; tail 0x8a1fd0: placement 2; base 1 in both games) = GU slot 175,
   the tail call of 0x8187c (= 4U 0x954778, asked at HP <= 0 for reaction kind 38), DONE (dala_death_kind_ok).
   Slots 78 / 79 = GU 171 / 172 (Shah, helper 2026-10-22). Open: slot 36 (head 0x776074, tail 0x8a3048; after the
   base 0x94dd8c(this, event): event 26 -> idle motion 1 / 101 and end, event 48 -> placement 2, motion 41 / 141
   (head also 0xd12024(work+108, 1)) and end; GU twin not found: GU 141 / 142 are stubs). Head slot 30 (0x76c77c):
   drops the work+0x68 effect controller once its unit is no longer alive (dala_efx_heat does the same for its
   handle). Slots 1 / 4 / 6 / 9 / 16: dtor and thunks to the base (C).
   Rage (C, 2026-10-21; common-branches.md): end of the 4U damage function 0x920104: r9 = the hit's rage damage
   -> 0x933b30(this, r9) (rage meter W+0x528 += n with the params of 0x93863c()+0x28, default threshold 600; skipped
   while the stage-8 hold W+0x539 is set) and, when enraged, 0x93674c. Then tail 83 / 111: the meter's delta of this
   hit (W+0x528 after - before) -> mgr+0x334 (0x68e08c add), W+0x528 = 0, 0x92b2d0(this, 4); head 24 / 110:
   0x933b30(this, 0x68e26c(mgr) = mgr+0x334 read-and-clear). So the tail never enrages by itself: its rage damage
   fills the head's meter (the tail copies the head's rage byte, em091_state_frame). GU: meter = rec+0x510 (u16;
   calm 0xbd128 clears it, C), rage byte rec+0x518, setRage 0xbce6c; GU's twin of 0x933b30 (rage add) NOT located
   (0xcc154..0xcc560 is the net-state receive). Port idea: on the controller each frame, tail meter delta -> the
   head's rage add, tail meter = 0 (no GU damage hook needed).
8. Heat zone (0x689c08 / 0x92d774, counter W+0x7e64 unresolved), map icons, tail target = head (0x9554c8).
   DONE 2026-10-22 (built, untested; dala_head25.c): W+0x7e64 = 2 per frame from head slot 77 0x774aa8 while enraged
   (zone 0, joint 4 + (0, -500, 1100) r 1250) or in motion 3 / motion 0x204 from frame 400 (zone 1, joint 101 +
   (500, 1300, -700) r 1700), counted down by the base update (C); core hook dala_heat_zone on GU 0x6a160 (Teostra's
   test) returns 1 inside it. Heat aura: uMhEftCtrl004 posts em024_016 / em110_016 (group 35 / 81 element 14, C)
   with element mask 8 / 16 at the same joint / offset: PEL 2960 / 2961 (dala_efx_heat). The 10/114 attack window
   of slot 77 (motion 0x304: frame 1 attack 10 param 2, frame 60 reset) ported there too. Map icons: core hook
   dala_map_pos on GU 0xc09c8 (position getter, the icon loop's call at 0x61a10c) -> joint 107 (head) / 154 (tail);
   size class stays 18 (4U 22 / 23 may have no GU icon frame). Material animations (dala_mat.c): materials of type
   1 (m01 eyes) "breath" / "anger" / "death", type 2 (m02 inner) "usually" / "anger" (spawn 0x76d668 + 0x7746f0).
   Tail target = head (0x9554c8 mode 4): the look target (W+0x77e7), part of the look system (E), open.
   Look system (E): DONE 2026-10-22 (helper, built, untested; dala_look.c, its header holds the checks). Corrections
   to the research below (C): the 4U list is emd FILE word 35 (row +0x84 = file + 8 + 0x84): joints 103..107 (kind
   1, index 0..4, limit 364) + joint 5 (index 5, limit 728); GU record = the first 16 B of the 4U 0x18-B record
   (34 / 40 shared monsters byte-identical), count u8 dtbparts +0x8d; current angles 0x7520 and rate 0x7544 are C;
   the base resets mode / flag / rate (0.015) every frame (4U 0x90eb88, GU 0xa5198), so mode 3 holds only while a
   handler writes it; joints re-registered for GU's joint callback (0xa7ff8) after the install; head only (em083
   has no look joint). MP: target slot 0 per machine (G: compare the "look mode" log lines of two LDN logs).
   Research notes (2026-10-22): 4U per-frame 0x9104b8 (from the base update 0x94d5f4,
   after slot 75) = GU 0xa79f8 (from 0xae218, after slot 168; same order of calls, C). GU keeps the fields on the
   object, 4U in the record (C, both functions compared): W+0x79d0 mode -> this+0x7548 (0 off, 2 skip, 3 = the
   tables below), W+0x79d1 fixed-origin flag -> 0x7549, W+0x79e8 fixed origin -> 0x7550, W+0x79d8 look point ->
   0x7560 (4U 0x93e974(this, 0, 0) = GU 0xc2884, same call site), W+0x79f8 yaw reference -> 0x7570 (else rec yaw:
   4U W+0x1ac, GU rec+0x54), apply 0x9342b8 = GU 0xa7bac: step tables W+0x79fc (angle >= 0) -> 0x752c, W+0x7a08
   (< 0) -> 0x7538 (6 u16 each, C), current angles W+0x79be -> 0x7520 (S), rate W+0x79cc -> 0x7544 (S). Joint
   list: 4U 0x94c590 = emd word 33 (+0x84; 0x18-B records {s32 joint (-1 end), u8 kind +4 (1 = look), +8 table
   index, +0xc limit}), GU = the dtbparts object (this+0x75f0) +0x68, count +0x8d (16-B records); ours is still
   Kushala's -> must be installed from 4U (convert by the Kushala pair, as dala_break.c). Values (C): set 0
   (0x76ec80: 7.0-7.4, 7.86): flag 1, rate 0.005, origin (-6500, 0, 1657), yaw 0x43ce, + [182, 364, 546, 728, 910,
   1092], - [8192, 182 x 5]; set 1 (0x76fce8: 7.41-7.46, 7.88): flag 1, rate unchanged, origin (2283.16, 0,
   3886.47), yaw 0x8555, + [3641, 91, 91, 91, 2185, 5461], - [0 x 6]. Mode 3 inside the handlers' frame windows.
   Arrows (cm000_002 uEffect002 28, C 2026-10-22, slot 77 ends): head (work+0x60 / +0x64) shown when 0x19fbf0
   ([0xfb5edc]+0x2b test) is 0, the action is 1/{0,3,6,9,50,53,60,61,63,71,84} or 7/{0..4,60,61,86} AND head part 0
   ranks >= 1; tail (work+4) the same without the part test, actions 1/{0,3,6,50}, 7/{0..3,60,61}; the head's
   work+0x68 controller follows the action test. User (2026-10-22): the head is walkable whenever the back is, as far
   as remembered, no proof either way; 4U's walk rule adds joint 5 (the head) only once part 0 is broken, the same
   condition as the head arrows -> the port now follows the 4U rule (dala_efx_arrows_frame, both halves, slot 119;
   log "dalaport: arrows").
   Render flag this+0xca8 (E): NO EFFECT (C, 2026-10-22): per-class scratch; no 4U base code reads it on an enemy,
   Capcom's GU twins of other classes write the bit index into this+0xb5f8 (read only by class code; pairs
   0x6df15c / 0xd008e8, 0x6e07c8 / 0xd0137c, 0x6f0fb0 / 0xd4f440), and Dalamadur's head / tail never test it.
   User (2026-10-22): the heat is around the TORSO (not the head) and only while ENRAGED; core hook on GU 0x6a160
   and head / tail map icons approved; restore 4U's metallic sheen (extend / sphere map) on the body materials.
   Plan "finish regular Dalamadur" (2026-10-22): A head-tail sync (helper), B AI cond 3 / 4, C walkable back, D head
   hitbox on the peak, E look system + render flag, F meteor kinds 0 / 1 start-up, G visuals (material animations,
   heat aura em024_016, roar blur, cm000_002 scale), H heat damage (core hook), I map icons (core), J carcass carve
   point follows joint 5 (4U slot 48), K body sheen.
   K done (built, untested): 4U 'E1' bodies with an extend map (body1 / body2, Shah also body4_nm / body5_nm) ->
   template 'solid_e1' = Capcom's GU Kushala em024_00_tail mat 0 (same 4U preset: tSphereMap = the 4U extend map,
   tSpecularMap = the BM, Capcom's specular / reflection kept). 'alpha' (alpha-tested, also E1 + extend map) keeps
   solid_at: no alpha-tested Capcom E1 template picked yet. J done (built, untested): the head's carcass point at
   joint 5 rows * (80, 150, 200) + row 3 (4U slot 48 0x773cc8; placed once, the dead head is frozen; y = floor).
9. BGM phase 2 on the first break: the core's BGM hooks live in Gogmazios' em089_bgm.c; a per-package version
   (core module/bgm.c, table-driven like stage_alias.c) is a core restructure: plan to present to the user.
10. Not ported (no GU field): W+0x79a9, W+0x628, W+0x978, W+0x1b79; gather point (no on-body gathering in GU).
11. Tail sever: DONE (dala_parts.c tail_sever: GU sever count of part 7 -> spawnCutPart(0, joint 157) +
    detached bit 1; 4U etd per-part table: part 7 is the only two-level part, 2nd HP 1000). Break visuals follow
    GU's per-part counts (converted dttune) through the rows. Break records DONE (dala_break.c, 2026-10-21): the
    4U part table (emd word 32, 32-B records) -> GU dtbparts records {part, LR, HR, s8 group}, installed once into
    the dtbparts object all four arcs share; GU 0x99f98's negative group = 4U's 0x80 "all records of the group"
    (claws), C in both games; 4U group 8 (no reward) left out (GU would read past its cond table and re-fire);
    GU group = 4U group + 1. Log lines "dalaport: break records" / "head breaks ..." / "tail breaks ...". The
    rest of this item is the earlier analysis:
    Part breaks (D6b): the arcs' dtbparts (field 34) is still Kushala's (manifest note), as it
    was for Gogmazios, whose em089_break.c installs its own break records at runtime into the dtbparts object
    (enemy+0x75f0: records +0x64 {part, LR count, HR count, reward group}, count +0x8c; break counts per part at
    rec+0x3bc + 12 * part, getter 0x9d428 = the partRank the rows / hitzones use) and spawns the cut tail
    (spawnCutPart 0xc2330, detach bits rec+0x3b4). Dalamadur needs the same: head parts 0..4 (cond-6 rows:
    levels 1..4 on part 0, 3 on parts 1 / 2, 1..2 on parts 3 / 4), tail parts 5..7, the tail sever (rows 22 / 108
    cond 1 param 1; cut piece em024_tail = manifest field 1?) and the 4U break list (emd word 33) for the reward
    groups (goal F rewards).

## Fixes 2026-10-25 (user's nine reports; built, installed at TEST_HP_PCT 25, not tested)
Evidence: test log 2026-10-24 17:22 (1618 dalaport lines, no kill), static RE. C / S / G as above.
1. Junction back / tail, 3. no invisible wall, 9. head not hittable and passable: gu-walkable.md 6c (body data off2.z
   bug in tools/emdata4u.py, C: head part 0 took no damage in the whole Oct 24 fight, parts 3 / 4 / 5..7 did; push
   left on as 4U; 4U's ground rule in GU's hunter ground function).
2. Camera on the back: the walk pieces were stage collision for the camera's sweep (C); now off during it.
4. Severed tail always at one place (C): spawnCutPart 0xc2330 with a NULL position uses the object position + 20,
   the piece settles there (ground +-350, 0x74388) and the severed tail's carve point uses it (0xabbc8); our halves
   never leave the spawn point. Now the floor under joint 157 (else 156 .. 140), dala_parts.c.
5. Meteors at half the shells' pace (user, sure this time; log: 60.8 4U frames / s against the monster's 60.0;
   4U velocities C). dala_meteor.c METEOR_PACE, meteor shell only.
6. SnS shield distorted: GU's 2-bone shields bind every mesh to bone 0 (C, w01 16..33), set 0 never moves bone 1
   (C, wg01_L); 4U's sld055 / sld105 blend bones 0 / 1 in every mesh with identical binds -> weapon4u2gu.py
   --shield-bone0 puts their vertices on bone 0 (rest shape unchanged; cause S, GU's draw of bone 1 not traced).
7. DB / HH / SA / LBG / Bow not forgeable: faithful (helper trace, C): both games show a create recipe once every
   key-2 material was obtained; 4U's records key the first material (4U create table 0xf51dfc, key bytes +20,
   filter 0x9be7bc / 0x9e6c3c, obtained bits 0xc1bef8); those five start with Dalamadur Talon or Pectus. Shah
   material weapons are upgrades only (4U and GU list a child under its owned parent, no material gate: 4U
   0xa02048 / 0xa4b488, GU 0x70ac34), so they show from the third weapon of each line.
8. Corpse moving after the death motion: no movement in the earlier logs (motion held at 747 / 748, positions
   constant, jump log > 300 only at the death motion's first frame, 4U's blend 0). Port: dala_carcass_lock
   (dala_carve.c) snapshots the joint locals, look angles and object transform at the first carcass frame and
   writes them back every frame after (slot 168); the jump log now reports > 20 once the pose is locked.

## Fixes 2026-10-25, second pass (test 15:58: 3 / 4 / 6 / 9 fixed, 7 confirmed; 1 / 2 / 5 / 8 not)
Built and installed at TEST_HP_PCT 25 (332 asset files, 0 mismatches); not tested.
8. Corpse: the log's "carcass head jump" lines after the lock: joint 5 (head) eased ~600 with a 7/8 ratio a frame,
   j0 still. GU's slope fit (dtbase +0x7c) kept from the donor Kushala: joints 101 and 140 (101 is an ancestor of
   102..107 -> 5), set up by 0xc1d88, eased by 0xa8724 (`angle += (target - angle) >> 3`), applied by the joint
   callback 0xab1a0 (C). 4U Dalamadur has none: emd word 40 = 0 in all four halves; word 40 is the slope fit (4U em001
   word 40 == GU em001_00 +0x7c, C). tools/dt_convert.py ABSENT drops it.
   Same audit (helper, verified on GU files): Kushala's ailment buildups (+0x98..+0xb4), stamina (+0x94), +0xbc,
   +0xc8 / +0xcc and dtbase joint points (+0xac) were kept although 4U's words are absent: dropped, with the loader's
   gates as GU's own files without them (em012 / em084 / em087 ...). Rage +0x8c[0:56] <- 4U etd word 14 (threshold
   450, duration 4200, x1.0 / 1.3 / 1.0; was Kushala's 700 / 4800 / 1.1 / 1.26 / 0.9). Focus +0xd4 / +0xd8 <- etd
   word 33 (head joint 5, tail 156, radius 1000; was Kushala's joints 2 / 0). Validation: dttune Teostra rebuilt from
   4U 57.6 % -> 96.6 % equal to GU's, Kushala 99.5 % (unchanged). Kept: dtbase +0x94 (never null in GU), +0x84 (4U
   mapping not reproduced), +0x88, +0x90.
1. Junction: in both attempts the hunter ran up j141 under the overlapping j140 (20..100 higher over j141's last
   300, FK of the 4U keys, key formats in gu-walkable.md 6d; motions 2 / 102 and bank 3's 1 / 101) and fell at
   j141's end. GU's contact flipped every 1..2 frames (airborne half the time): the pieces moved continuously, so GU
   filed them in its moving tree and tried to carry the hunter (refused when its sweep is blocked, Gogmazios'
   stage_cart.c). Now still entries (teleport flag 1): 4U's strip query only sets the height (C).
2. Camera: the camera also pushes itself out of the cambodydata capsules (0x17fa4c -> 0x17f750, radius up to 800,
   the strips lie inside by up to 340). rec+0x528 (skipped there) is set on both halves for the camera step only,
   while the local hunter is on the body, then restored; the push and its walls are untouched.
5. Meteors: 4U's code puts the shells on the monster's clock (line 18, every line scale 1.0, global step in 60-fps
   frames; C / S), i.e. 100 %; the user's 4U memory says between 50 and 100: 75 % (G), switch DALA_METEOR_PACE_PCT.
   Note: the 4U monster's own pace was not traced to the frame either (its motions play at 60 / s in the port).
- Seen in the log, not a bug: the tail runs its own AI and motions while the head does something else (head 1/53
  with tail 7/1); both share bone 0 (dala_join.c), as 4U's tail motions are authored in the head's bone-0 frame.
- New report (user, 2026-10-25): "3 idle locations, never seen the third". The test log has the head in placements
  0 and 2 only (mode 1 never). 4U's head EMC (em024_cmd, C, decoded with tools/emc.py): the root picks the selector
  by HP band (g0 s1..s7 High Rank, s8..s14 G rank: bands >= 90 / 84 / 62 / 56 / 44 / 17 / below %); once cond 4
  holds (W_T_MODE >= 2700 in placement 0, 5400 in 1 / 2) a selector switches on the placement: from 0 bands 1..2
  call g1 s52 (1.50 = wait, then 2.0 to placement 1, always), bands 0 / 3 / 4 call s9 (1.50 30 % / 1.53 70 %; 10 / 90
  enraged); bands 5..6 (below 44 %) have no path into placement 1 (only s16 = 1.53 -> placement 2, s17 / s10). Every
  test since 2026-10-24 started at 25 % HP: placement 1 cannot occur there in 4U either. Not changed; seen with
  TEST_HP_PCT 62..90 after 45 s in placement 0. The waits in the log (1/53 x11, 2/3 x3) were cut by reactions (10/7,
  10/114); the move starts when the tail's AI picks its follow (tail 1/50), 4U's two-half design.

## Fixes 2026-10-25, third pass (test 17:27, release build: 5 / 6 / 8 fixed, 7 OK; 1 partly, 2 not; new 9)
Built (release, no defines); not tested. Details: gu-walkable.md 6e.
1. Junction walkable; running off its side toward the wall played no ledge jump (no wall grab). Log: off j140's
   83 deg side the hunter went airborne 337 above the side, then over the floor at -848. GU picks a plain fall for a
   moving hunter whose drop is <= 300 (C, 0x2e8a84 -> 0x2a01d8), else action 4/1 (S: the ledge jump), and its ray saw
   the pieces' steep side. 4U counts a strip only inside a window (local: y - 60 - 50 g on the body, -30 off it; g = 2
   at 30 fps) and the stage otherwise, so its hunter leaves the side over the floor: ledge jump. Port: pieces off for
   every hunter's ray, 4U's windows in dala_ground_c (local per 4U frame of hunter time), the height also into the
   ray's slot GU's landing reads. Remote hunters get 4U's partner window (-300 - 50 g on em024 / em083; user's side
   note, MP).
2. Camera: GU tilts its pitch by the slope under the hunter (0x238e0, 0x23d80: pitch = T (1 - |u| / 8192) + u, no
   stick effect at T = 45 deg; C) and that ray met the walk pieces (S: the cause). Pieces off for it. The 15:58
   camera-body skip (rec+0x528) is removed: not 4U's, and it did not help.
7. Head passable (user: hits land now, still passes through; not a regression). 4U's head push volumes (emd word 8,
   C): record 2 (push only, snout, r 230) and 3 / 4 (push + hurt, head sides, r 340), always on; 57 (snout tip) only
   while walkable; the upper head (records 0 / 1 / 5) is hurt only. GU's push pass 0x17c9d0 -> 0x17cf40 tests the
   area, rec+0x528, vt+0x88 and (player vt+0x270) enemy vt+0x164. Open: where the user passes through (asked).
9. Shah fire on the ground (new). The test armed zone 0 once (7/22, crimson part 4); 7/40 ran with part 3 only (no
   zone 1: 4U's 0x76f898 needs part 0, C). Fireballs: kind 88 (raging) -> burn sequence (4 steps ran), 89 -> blast
   161 only (4U data, C). Open: which attacks and grounds the user means (asked).
- Log: two emulator pauses (00:13:08..00:13:39, 00:15:02..00:16:03: no game lines at all, both halves' frame counters
  stopped); the zone's 81 s and 7/22's 1496 frames in 74 s are those pauses, not a timer bug.
- Test of this build (user, 2026-10-25 evening): 1 (ledge jump off the junction's side, wall grab), 2 (camera on the
  back) and 9 fixed. 7: the hunter still passes through the head entering by the front (the mouth); left as is for
  now (user). Released as Dalamadur 1.0.0 / core 1.5.0 (with Gogmazios 1.1.1: the body data capsule fix).

## Fixes 2026-10-26 (user's online session with friends, 2026-10-25 21:56 log; not tested)
- Stays too long in one placement after flinches / topples (user; friends: not 4U). The placement timer W_T_MODE
  (cond 4: 2700 in placement 0, 5400 in 1 / 2, 4U 0x773f34 clears it only when W+0x1c9 changes: same rule as ours,
  C) advanced through GU 0x72708 -> 0x53aa70 = t += this+28 * s0, and our call never set s0 (every GU caller loads
  1.0 first, C): the timer ran at whatever float s0 held. G quest log: placement 0 from 4:57 to 8:16 (199 s, 45 s in
  4U). em090_state_frame passes 1.0 now (both timers; the tail's cond 5 reads the head's W_T_ACT too).
- Acid / hot-spring damage while standing on the body (user: since the third pass). The ground query 0x18192c writes
  the hit polygon's attributes into hunter+0x1060 / +0x10a0 (C); the pieces are off for it, so over the lake they were
  the lake's and only the height was ours. dala_walk.c report() runs the query again from the strip's height with
  the pieces on: the body's piece fills them, as before the third pass (log line if that second query misses).
- HR and G "the same HP and damage" (user): not a port error. Quest rows (4U's, C): 10792 HP row 40 (x1.30), attack
  105 (x7.0), defence 82 (x0.80); 11494 HP 65 (x2.05), attack 107 (x7.6), defence 79 (x0.80). The log has HP 22880 =
  base 17600 x 1.30 for 10792 (this machine controlled it; 11494's controller was a friend's: 36080 expected, S).
  Times in the log: 11494 11:31, 10792 6:14. The attack rows are nearly equal in 4U itself.
