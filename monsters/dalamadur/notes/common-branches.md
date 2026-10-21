# Dalamadur: 4U common code that names em 24 / 83 / 110 / 111 (static study, 2026-10-21)

C = read in code / data, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4 main. W = 4U work struct
([this+0xe28]); "mgr" = 4U enemy manager [0xf32004]. Read class-study.md first. Scripts:
`dump/scratch/dalamadur-session/common/` (who.py callers + vtable slots, gu_emcmp.py GU em-number compares,
gu_field.py GU field users, scan2.py / scan3.py / idx.py second pass).

Em names used below: 4U em 32 = Teostra (Capcom pair 4U em032 / GU em027_00, S), 46 = Dah'ren, 89 = Gogmazios.
GU ems (dump/gu_classes.pkl, C): 24 = Kushala, 27 = Teostra, 80 = Glavenus, 83 = Gammoth, 84 = Nakarkos,
87 = Ahtal-Neset, 88 = Ahtal-Ka. GU common code that names 24 / 83 means Kushala / Gammoth (0x8b0d0, 0xc3dd4): our
new em ids never reach those branches.

## Already known (not redone)
0x920104 damage + HP pool (0x9201a0, 0x920a4c..0x920b18); 0x9244e0 / 0x924ce0 pool setup; 0x308744 battle music;
0x326a6c / 0x326c40 uMhEftCtrl004 id 81 (Shah) vs 35; 0x681e44 walk query; 0x91df44 joint-154 sphere. New on
0x91df44 (C): its callers 0xb954ec / 0xb9d374 are the map-UI functions that also call 0x917d74 (below).

## Table

| 4U fn | role (callers) | Dalamadur branch | GU counterpart | port need |
|---|---|---|---|---|
| 0x3046a8 | SE variant pick for a model's sound request (0x30a174 / 0x3d9b84 sound-command parser) -> 0x3ac65c(table, rec, variant) (C) | mode 1, player standing on an enemy (player+0xa29c: +0x9a8 on-enemy flag, +0x9c2 enemy index, both written by the walk query 0x6822f8 / 0x682388): ground material = 1 for em 24 / 83, 37 for em 46 (0x30473c); 110 / 111 fall through with an unwritten stack byte (C) | not found; GU walk-on-monster = SBC collision (gu-walkable.md), material would come from the SBC attribute (G) | data: material of the converted body SBC (footstep SE on the body); Shah unclear in 4U itself |
| 0x689c08 | heat-aura zone test (mgr, area, pos): 32 enemy slots, same area, alive; returns 1 / 2 (C). Callers: 0xb1aa14 (hot-area drain skipped inside the zone) and 0xb2f73c (heat damage tick: zone result 2 -> flag 0x80000000, 1 -> 8) (C; "heat" S) | em 32 (Teostra): joint 2 x 750 / 825 or joint 3 x 600 by stage type (0x69ae70 == 4 / 6). em 24 / 110: class field [this+0x8d88]+0x40 == 1 -> joint 101 + offset (500, 1300, -700), radius 1700, else joint 4 + (0, -500, 1100), radius 1250, x size scale; returns 2 (0x689ca0 / 0x689cb0). Tails: none (C) | **GU 0x6a160** (same radii 600 / 750 / 825, joints 2 / 3, stage types 4 / 6): only `ldrh id == 27` at 0x6a254, returns 0/1; callers 0x2a3814, 0x2a5344 (heat damage, ORs 0x48d4cc) (C) | core hook on GU 0x6a160 (return 1 inside our head's zone) if the 4U heat zone is wanted; what it looks like in 4U: ask the user (G) |
| 0x910650 | paint mark: W+0x20c = 36000.0 (frames), W+0x7e19 bit 0 (net flag). Callers: hit handler 0xbeb658 (paint hit) and net handler 0x82755c flag bit 0 (C) | ems 81 / 84 / 85 / 86 / 87 / 104 / 123: never painted. em 24 / 83 / 110 / 111: paints EVERY enemy whose em is 24 / 83 / 110 / 111 (loop 0x9106dc), i.e. both halves (C) | **GU vt slot 240 = 0xc0908** (rec+0x1c4 = 36000.0, this+0x7429 \|= 1; skipped when this+0x15e9 bit 2: data flag instead of an em list). Net: recv flags msg = slot 272 0xccc88, bit 0 -> slot 240 (same bit order as 4U 0x8275e0) (C) | class code: override slot 240 in both classes (paint self via 0xc0908 + paint the partner). MP: remote machines get the paint via slot 272 -> the override paints the partner there too (S) |
| 0x912504 | net control hand-over per frame (from base update 0x94d26c): W+0x1da = controlling player index, W+0x1d9 = this machine controls (0x920104 runs only then); hands control to a player in the enemy's area, sends msg 0x917e84(this, 2, 0) (C) | when no player of the area takes it: em 25 / 94 -> their class routine 0x787014; tails 83 / 111 -> controller = the head's (partner 0x68fd44(mgr, 24 / 110), copy head W+0x1da if it differs and != 255) (0x9127dc..0x912864) (C) | GU control: this+0x7424 controller, this+0x7420 = local (0xb161c set, 0xb167c / 0xb16e0 take, msg 0xcafe8(this, 2, 0) = 4U 0x917e84); area logic 0xad7b4 / 0xadb3c (em 84 at 0xadaa4). Exact counterpart of the hand-over not located (S / G) | **MP critical**: both halves must have the same controller (pool, tail action mirroring). Class code in the tail: each frame adopt the head's +0x7424 (0xb161c) or hook GU's hand-over; also the 4U W+0x1d9 gate = GU +0x7420 (S) |
| 0x916160 | "enemy may be shown" predicate for map / UI (callers 0xb86d88 -> map 0xb954ec, 0xb93788, 0xba092c, 0xbff6e4, 0xc01594): false if W+0x1dd == 1, W+0x556, or mode 4 with W+0x180 < 0.9 x row+116 (C; UI role S) | em 24 / 83 / 110 / 111 (and 79): also require W+0x7eec != 0 (writer not found; 103 the same) (C) | not found (G) | class code / G: decide in Phase 5 with the map icon |
| 0x917d74 (scan said 0x917d48: leaf fn) | enemy map-icon point (out, enemy); callers 0xb954ec / 0xb9d374 (map UI, also call 0x91df44 and the map scale 0x5a5f14) (C) | head 24 / 110 -> joint 107, tail 83 / 111 -> joint 154 (0x93093c = GU 0xc1708); others W+0x198 (C) | GU map icon cUIOQuestMapIcon 0x61a994 (api-map.md), icon point source not traced (G) | core hook (GU icon position) or accept the root position; whether 4U shows a tail icon: ask the user (G) |
| 0x91a950 | per enemy, from 0x682a24 (loop, player code 0xb348c8): enemy alive, W+0x34c == 1 (engaged), player bit in W+0x290, range test 0x91f8bc, then angle between player facing and enemy outside +-45 deg -> 1 (C; meaning G: player look-back / tension reaction) | tails 83 / 111 -> 0 (never counted); heads 24 / 110 -> joint 4 instead of W+0x198; em 46 in area 1 -> W+0x198 alt (C) | not found (G) | none / cosmetic (G) |
| 0x9259c0 | full enemy-state net packet (msg kind 5, 108 B), built from 0x917e84 (C) | packet+102: tails send mgr+0x334 read-and-clear (0x68e26c), others W+0x528 (0x925a78); packet+74 / +78: heads send mgr+0x32c (0x68d920) / mgr+0x32e, others W+0x7976 / W+0x7a76 (0x925a9c) (C) | **GU vt slot 269 0xcba54** (send, msg 2, calls part rank 0x9d428 like 4U 0x94741c) / recv slot 270 0xcc86c (sets controller 0xb161c); no em list (S) | MP: class code (override 269 / 270) only if the shared block (below) lives in the module and must reach remote machines; simplest: same controller for both halves + GU HP sync (S) |
| 0x920104 tail part (0x921d1c, 0x921da4; outside the known ranges) | end of the damage function (C) | 0x921d1c: head 24 / 110 takes mgr+0x334 (read-and-clear) into 0x933b30 (rage meter, params +0x28, default 600); tail 83 / 111 adds its W+0x528 delta to mgr+0x334 and clears it -> damage on the tail enrages the head (C; rage S). 0x921da4: the four ems skip 0x939c40 (generic flinch / reaction choice -> 0x949634 cat-10 actions) and tail-call 0x948b9c (shared reactions, second pass) (C) | GU damage function not located (G) | class code (both halves' damage handlers); controller-only (MP) |
| 0x92712c | status build-up per hit (from damage fn 0x920948): fields +64 / +70 / +72 / +74 of the hit record (C) | field +72 (KO by the +72 / +74 pairing, G): tail 83 / 111 adds it to mgr+0x336 (0x68c7f8) instead of applying it; head 24 / 110 adds mgr+0x336 (read-and-clear 0x68cb60) to its own value before 0x935194 (C) | not found (G) | class code: tail forwards its +72 build-up to the head; controller-only (MP) |
| 0x92e218 | predicate (enemy, flag): W+0x1c8 in {0, 3, 4}, W+0x5f8 bit 13, and (stage?, area, W+0x5f5) not listed in species row +0x38. Callers: damage fn 0x920840, 0x954778 (current area), 0x9394cc (C); meaning G (area change / flee when weak) | 24 / 83 / 110 / 111 -> always 0 (0x92e22c) (C) | not found; GU area moves need an area_act_tbl entry (api-map.md: index >= 137 -> none) (S) | none / data (no area_act entry or an all-zero one) (S) |
| 0x944e80 | per-part effect spawn from species row +0x78 records (type 2..8 -> flags, joint +8) through 0xc088d8 (type 16) (C); from damage fn 0x9207ec / 0x9211ac and setup 0x93c2a0 (<- pool setups) | id field = 35 for em 24 / 83, 81 for every other em incl. Shah 110 / 111 (0x945058) (C); matches uMhEftCtrl004 35 / 81 (0x326a6c) (S) | not found (G) | class code / effects data (Phase 4 effects) |
| 0x94e6f4 | uEnemy init (from uEnemy ctor 0x955ff4, every class): this+0xd64 = 3, 0x957b84(this, N) = N animation layers (this+0x234; per layer 52 B x joint count at this+0x368 + 0x130 k) (C; "layers" S) | 24 / 83 / 110 / 111 -> 4 layers, others 2 (0x94e718) (C) | not found (G) | class code (ctor) only if uEm024 / uEm083 use layers 2 / 3 (not checked, G) |
| 0x978c04, 0x98897c | uOtomo (Palico) target filters (22 + 2 callers in 0x97..0x99 uOtomo code) (C) | mode 2: em 83 rejected (0x978d14, 0x988b84); 111 NOT rejected (C) | not found (G) | G / low: GU Palico may target the tail in that mode |
| 0x9870a8 | Palico aim point on an enemy (C) | head 24 / 110 -> joint 107; others the data centre joint 0x935644 (C) | not found (G) | data / low |
| 0xbe9c64 | player attack hits enemy (hit record r4, enemy r7; from 0xbee32c <- 0xbf4a48) (C) | 0xbe9f88: hit record +0x95 \|= 8 when the enemy is 24 / 83 / 110 / 111 (C) | **GU 0x171350** (same +0x95 bit 1 rule moved to +0xb5 at 0x171464, no em list there) (S) | see 0xbf4a48 |
| 0xbf4a48 | sHitcheck slot 7 (0xbf44c4 -> b) attack-vs-enemy loop (C) | 0xbf4d28: skip the enemy when it is 24 / 83 / 110 / 111 and the attack already carries +0x95 bit 3 -> one attack damages only ONE half (C). Same loop: attack types 14 / 64 / 66 / 53 limited to ems 46 / 77 / 78 / 79 / 82 / 89 (C) | GU sHitcheck vtable 0x173ec34 (slot 7 0x16ab18, S). GU group rule for Nakarkos: 0x16c990 sets hit +0xb5 \|= 0x20 for em 84 (or em 99 child) after the enemy's vt+0x98 hit call; readers in Nakarkos class code 0x106f964 / 0x1080f38; 0x16938c = enemy-attack friendly-fire test for 84 / 99 (C) | class code: in both halves' hit handler (vt+0x98, slot 38) ignore a hit whose record already carries our "hit the other half" bit, else set it (S); or core hook on GU 0x16c990. MP: hits are checked on the attacker's machine (G) |

## Second pass (missed by the cmp scan)
scan2.py follows the em-number register (moves, +- offsets) for jump tables, indexed loads and shifts; scan3.py looks
for em constants passed to manager lookups and compares of em-like values loaded from other fields.
- 0x948b9c (C, new): reached only from the damage function's Dalamadur exit (0x921de0). Shared damage reactions in
  the mgr block: mgr+0x330 (u16, active, 0x68d914), +0x32c (code), +0x32e (part), +0x332 (part copy). A half with a
  pending reaction (W+[0x949618] = 1 / 3 / 14 / 31 / 45 / 46) posts it with its part W+0x42a / 0x42b via 0x68aa80;
  when active both halves run the matching cat-10 action (0x92b1d4) and copy the part. Also em 64 cases inside.
  Port: class code (shared reaction state in the module); MP: controller-only, and 4U ships mgr+0x32c / 0x32e in
  the state packet (0x925d10).
- mgr block summary (C): +0x328 pool, +0x32c / +0x32e / +0x330 / +0x332 shared reaction, +0x334 tail -> head rage,
  +0x336 tail -> head KO(?) build-up. Reset at 0x68f448; set by pool setup 0x924ce0 (0x924ffc, 0x92501c).
- em-indexed data tables (C; table base, entry at 24 / 83 / 110 / 111):
  | user | table | values | meaning | port |
  |---|---|---|---|---|
  | 0x9357ec (callers: uEm024 slot 39 spawn 0x76d848, player 0xc7f2c0 / 0xc846c0, classes 0x7ff1c4 / 0x857060) | u16 0x1003ed4 | 0x414 / none / 0x458 / none; only 12 ems have rows (9, 10, 24, 38, 39, 46, 48, 49, 64, 101, 110, 114) | item list index (+ record byte x 4 + rank) into 0x1002a5c: weighted {%, n, item} lists -> a gatherable point on the monster (S; Dah'ren mining analogue, G for Dalamadur: ask the user) | class code + data (GU gathering on our body), Phase 5b |
  | 0x911f58 (= GU 0xac0ec, apimap2) | u16 0x1003ddc | 0xffff for all four (also 46, small ems) | no shiny drop (S) | GU 0xac0ec: em 84 skip + vt slot 262 (0x418) query -> class code override if needed (S) |
  | 0x6a6a20 (hunt record, per-em counters at +0xaf00) | u8 0xfc96dc | 64 / 0 / 64 / 0 | per-hunt points; tails 0 (do not count as a hunt) (S) | content (save / Notes), Phase 5b |
  | 0xb9b390 (map UI) | u8 0xdeef04 | 22 / 23 / 22 / 23 | map icon class (S) | core: GU icon table copy 0x1635354 (api-map.md) needs our ems |
  | 0x93f388 (base update) | u32 0xffeaa4 (88 entries) | default list for 24 / 83; 110 / 111 read past the end (also em 89) | per-em joint list for a per-frame joint tracker (S) | none |
  | 0x948174 / 0x94c878 | s16 0xffecb8 / 0xfff186 / 0xffedae | 195 / 180 / 180 / 180 (24: 195, 180, 180) | per-em durations x rank factor (G) | data (GU per-monster data) |
  | 0xc564ec (player) | u8 0xe0fe8c (124) | 1 / 0 / 1 / 0 (also 1 for 22, 23, 46, 89) | per-em flag stored at player+0x278 (G) | unknown (G) |
  | 0x30f4f0 (sound) | 2 x f32 0xfcd71c | +-100 for 24 / 25 / 83 / 110 / 111 | generic per-em sound range (G) | none |
- Jump tables on the em number (C): 0x949634 (cat-10 reaction choice) sends em 24 to its default; the others are in
  monster classes or index other ems. No em jump table singles out 24 / 83 / 110 / 111.
- Em constants elsewhere (C, ranges 0x900000..0x960000, 0x680000..0x6c0000): only 0x912800 / 0x91289c (partner
  lookups in 0x912504). Other `cmp #110 / #24` hits there compare action numbers (W+0x1cb).
- Not covered: code that copies the em number into another struct before comparing, and float / data-driven
  differences in the species rows (emd) themselves.

## Port summary
- MP (enemy+0x7420 controller): one controller for both halves (0x912504), pool / rage / KO / reactions only on it
  (0x920104 gate W+0x1d9), paint via slot 240 / 272, per-attack one-half rule.
- Class code: slot 240 (paint both), slot 38 hit handler (one half per attack), damage handlers (rage, KO,
  reactions forwarded to the head), ctor (4 layers if used), effects id 35 set, gathering point.
- Core hooks: GU 0x6a160 (heat zone, only if wanted), map icon table / position, GU 0x16c990 (alternative to the
  class-code hit rule).
- Ask the user: heat zone near the head, map icons (tail icon?), gathering on Dalamadur's body.
