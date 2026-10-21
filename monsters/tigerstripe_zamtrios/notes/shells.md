# Tigerstripe Zamtrios: paralysis shells (design, 2026-10-21, helper, static only)

Tags: C = confirmed in code / data, S = strong, G = guess. 4U = MH4U v1.1 (dump/mh4u.asm), GU = MHGU 1.4 main.
Scratch scripts: /tmp/claude-1000/-home-scrimas-Projects-MH4U-MHGU-port/aa473438-013b-4411-b8ca-5d2f95908e85/scratchpad/shells/.

Short version: Tigerstripe's paralysis balls are 4U uShell012 subtypes 40-43 (+ an invisible uShell003 residue sphere,
subtypes 169-172, at the impact). Their code is the same as Zamtrios' 8-11: only data changes (effect group, attack
records). GU already ports Zamtrios' 8-11 as the data-driven class **uShellEm067_sp_13** (shell id 292). So the cheap
route is GU's class plus a Tigerstripe copy of its shell families (TS attack / effect data), asked for through our own
request, for variant 1 only. A small derived class (slot 92 = target point) then brings back the 4U rules GU dropped:
mode-1 / mode-2 targets and the 2100 minimum range. No full 4U class port is needed.

## 1. 4U side

### 1a. Post sites (uEm022, used by em092)
| site | actions (C: dispatcher 0x756264, index = num - 6, num > 86 at 0x7564ec) | what is posted |
|---|---|---|
| 0x74e288(this, mode) | mode 0: 7/12, 7/13, 7/24 (S, case window); mode 1: **7/202**, mode 2: **7/203** (C) | uShell012 ZM 8 / 9, TS **40 / 41** |
| 0x74f1b0 | 7/33, 7/34, 7/54..56 (phase-1 note) | ZM 11 then 2 x 10; TS **43** then 2 x **42** |
| 0x74ebd8, 0x750e10 | motions 0x43b/0x43c, 0x438/0x43c/0x45a/0x45c (phase 1) | uShell016 ZM 13 (f 3000), TS **40 (f 2000)** |
| 0x750590 | motions 0x439/0x43a | uShell016 ZM 47, TS **48** |
EMC (heuristic tools/emc.py refs on our em067_01_cmdtbl): 7:12 x3, 7:13 x23, 7:24 x4, 7:202 x2, 7:203 x2, 7:33, 7:34,
7:54 x4, 7:55 x4 (G: tokenizer). So mode 1 / 2 are probably reachable.

0x74e288 (C):
- step 0: setMotion 0x75d9f0 motion 0x425 (ZM) / **0x46c** (TS), blend 6; W+0x145 = W+0x146 = 0.
- step 1: each time 0x941dbc(140) fires: W+0x145++. Table T = 0x10b6300 (mode 0), 0x10b6300 + 160 (mode 1),
  0x10b6440 (mode 2), 16-B entries, index W+0x145 - 1. Entry (-1, -1, -1) sets W+0x146 = 1 (end). The tables are
  bss, filled by a static init (0xd25830 / 0xd258c4), so they were not compared with GU's.
- spawn = owner pos (W+408) + Rz(W+0x1b0) Rx(W+0x1a8) Ry(W+0x1ac) * ((10, 495, 135) * sizeFactor 0x911cb4).
- target = pos + R * (T[i] * {1, 0.5, 1.5}[mode] * size). Mode 2 and W+0x145 in {3, 7}: 0x92d0d4(this, 0, 0), then
  target = W+0x218 (target slot = the hunter).
- velocity: 0x925fac(this, spawn, target, 0, out) -> 0x938d2c (C, decoded): d = target - spawn; |d| < min: d *= min/|d|;
  |d| > max: d.xz scaled to max; h = |d.xz|; v_fwd = s1 + h * s2; t = h / v_fwd; v_y = (d.y - g t^2 / 2) / t; then
  rotated by the yaw of d. Arguments: g = -2, s1 = 13, s2 = 0.0125, min = 600 (**2100 for em92, mode 2, W+0x145 in
  {3, 7}**), max = 3000.
- subtype: W+0x145 % 3 == 1 -> 9 / **41** (big), else 8 / **40** (small).
- post: 0x663e60(mgr *0xef3cf0, this, sub, &offset, [sp] &vel, &(0, -2, 0) accel, &target, u16 0xffff) -> event type 12.

0x74f1b0 (C): sub 11 / **43** = one big ball toward the target, distance clamped to [800, 4000] * size along the
facing (g -1, s1 22.5, s2 0.0125). If r1 == 0: two sub 10 / **42** balls at offsets (336, 0, 1367) and (-285, 0, 1220)
(g -0.2, s1 12.5, min 500, max 3000). **TS only:** the event u16 (+74 -> shell +0x270 -> +412) = u16 at [this+0x8d88]+18
for 42 / 43 (ZM: 0xffff). Meaning not traced (G: attack-data override; GU keeps the same u16 at param+0x34 ->
shell+0x1588 and passes it to the attack arm at 0x405c34).

### 1b. uShell012 class (C)
- event 0x660e88 type 12: alloc 688 B (0xc63bd8), ctor 0xc636d8, vtable 0xe6d7cc: slot 22 init 0xc61058, slot 23 per
  frame 0xc61b80, slot 24 end 0xc6362c. Fields: +0xfd sub, +0x278 offset, +0x140 velocity, +0x150 accel, +0x288 target,
  +0x270 u16, +0x274 effect, +0x26c life.
- **8<->40, 9<->41, 10<->42, 11<->43 run the same code**: the three subtype jump tables (ctor 0xc63858, init 0xc6125c,
  per frame 0xc61cc4) give equal targets, and no instruction tests 40..43 (scratch s012cmp.py). They differ only in
  these per-subtype tables (s012tabs.py):

| table | ZM 8 / 9 / 10 / 11 | TS 40 / 41 / 42 / 43 |
|---|---|---|
| 0x1027488 flight effect {grp, elem, mask} | 33 / 11 = **em022_012**, mask 1 / 2 / 1 / 2 | 68 / 9 = **em092_012**, mask 1 / 2 / 1 / 2 |
| 0x10276b0 impact effect, impact kind 1 | em022_013, mask 1 / 2 | **em092_013**, mask 1 / 2 |
| 0x10278d8 impact effect, impact kinds 0 / 2 | em022_013, all | **em092_013**, all |
| 0x10290b0 attack record (base 0x1028904 + 84) | 7 / 8 / 9 / 10 | **29 / 30 / 31 / 32** |
| 0x10287f0 / 0x10286dc impact posts (uShell003, kind 0 / 1) | -,68,-,72 / 63,72,71,72 | **-,170,-,172 / 169,172,171,172** |

  The effect groups come from the EFL-list table 0xef895c (group 65 = em089, checked; 33 = em022, 68 = em092 list, where
  index 9 = em092_012 and index 10 = em092_013). The impact post tables hold one 4-byte entry per subtype {1, sub,
  class 0 = 0x663220 -> 0x661c5c = event 3 uShell003, -}, and class 0xff = no post.
- Identical for ZM and TS: life 180 (0x10291c8), scale 1.0 (0x10292dc), colour white (bss 0x10bb4e8, static init
  0xd36b48 emulated), spawn sound 201 (0x1027b00 type 2), impact sound 206 (0x10278d8 + 1104), volumes 4 / 6 / 7 / 8 =
  spheres on bone 1001, radius 50 / 100 / 50 / 100. The impact sound is 202 / 203 by map material (0xc620dc compares a
  hit-info byte with 11, not the subtype).
- If no effect can be created, the init kills the shell (+0xf1 = 2). That is one reason a ball without its effect
  never appears.

### 1c. Attack records (C, 4U bytes 0..0x27)
| record | window | power | type +6 | +0x0b | +0x0c u32 | +0x10 | +0x12 | +0x18 | vol |
|---|---|---|---|---|---|---|---|---|---|
| uShell012 7 / 9 (ZM small) | 0+99 | 20 | 21 | 0x10 | 0x4081 | 0 | 0x08 | 0 | 4 / 7 |
| uShell012 8 / 10 (ZM big) | 0+99 | 20 | 21 | 0x29 | 0x4081 | 0 | 0x08 | 0 | 6 / 8 |
| uShell012 **29 / 31** (TS small) | 0+99 | 20 | **1** | 0x10 | **0x0001** | **4** | 0x08 | **50** | 4 / 7 |
| uShell012 **30 / 32** (TS big) | 0+99 | 20 | **1** | 0x29 | **0x0001** | **4** | 0x08 | **50** | 6 / 8 |
| uShell003 63 / 71 / 68 / 72 (ZM residue) | 10+10 | 20 / 20 / 40 / 40 | 21 | | 0x4081 | 0 | | 0 | 49 / 54 / 52 / 55 |
| uShell003 **169 / 171 / 170 / 172** (TS) | 10+10 | 20 / 20 / 40 / 40 | **1** | | **0x0001** | **4** | | **50** | same |
| uShell016 12 (ZM 13 / 47) | 0+99 | 80 | 2 | 0x29 | 0x81 | 0 | 0x14 | 0 | 7 |
| uShell016 **38** (TS 40 / 48) | 0+99 | 80 | 2 | 0x29 | **0x11** | 0 | 0x14 | 0 | 7 |

- The paralysis is encoded as type 1 + byte 0x10 = 4 + byte 0x18 = 50, against Zamtrios' type 21 + flags 0x4081 (S:
  these fields appear only in the TS ball / residue records; their meaning was not traced in the hit code. GU 0x168e98
  copies u32 +0x0c, u32 +0x10 and u8 +0x18 into the attack slot).
- uShell016 38 lacks that pattern, so it does not look like a paralysis attack (G). It differs from 12 only in flag
  bit 4 vs bit 7.
- Residue volumes (uShell003 base 0x101efbc): 49 r200, 52 r350, 54 r200, 55 r300, spheres on bone 255. uShell003 has
  no effect for 63..72 / 169..172 (its effect table 0x101dfcc has group 0xff), so the visible splash is the ball's
  impact effect.

### 1d. uShell016 40 / 48 (C unless tagged)
- life 192 / 50 (0x102bbbc), record 38 (0x102bad8; ZM 12), vol 7 = capsule on bone 1001, r130. The init cases differ
  from ZM's:
  - 13 / 47: 0xc07ecc(mgr *0x10572a4, 1, area, shell, 0, 0)
  - 40: 0xc07ecc(..., **7**, ..., scale (0.3, 0.3, 0.5))
  - 48: 0xc07ecc(..., **7**, ..., scale (0.3, 0.3, 0.25))
- 0xc07ecc is effect-manager event 15 (0xc0765c). It probably attaches a common marker / trail effect of kind 1 or 7
  (G, not resolved to an EFL). The breath visual itself is probably a motion (MEF) effect (G).

## 2. GU side

### 2a. Sites (C)
| GU | 4U | variant 1 today | request |
|---|---|---|---|
| f722d0 (called f75b58 r1 0, f75d80 r1 1, f75d90 r1 2) = 0x74e288 | balls | target / spawn computed for both variants (f72520..f726fc, mode table and scale, mode 2 count 3 / 7 -> 0xc46c8 + rec+0x1d0); **f72708 `variant != 0` -> f7283c skips** the ballistic 0xc1190 and the post | id 292, kind = count % 3 == 1, param+0x30 = count - 1 |
| f735d0 | 43 | skips f73668 | id 292 kind 4 |
| f73870 (reads `[sp+0xc]` = &variant) | 42 x 2 | skips f738f0 | id 292 kind 3, +0x10 = pos (r10), +0x30 = loop index r6 |
| f72dd4 / f755ec | uShell016 13 | posts ZM's shell | id 291 kind 0 |
| f746e4 | uShell016 47 | posts ZM's shell | id 291 kind 1 |
| f7c094 -> f7c0d8 -> `b 0x48c4f0` (in the sp_13 class) | uShell003 residue | ZM's residue (posted only by ZM balls) | id 290, kind = 0x16a7d10[ball kind] = {8, 9, 8, 10, 11} |
The 42 / 43 sites run GU's own ballistic (0xc1190, 4U parameters) before their variant test. So the velocity exists on
the stack for variant 1 too (f735bc -> sp+80, f7386c).

### 2b. GU classes and data (C)
- Shell table 0x1763448 (12-B rows {class DTI, param DTI, file id}):
  - 290 uShellEm067_sp_01 (EmBase01, 0x8a75)
  - 291 uShellEm067_sp_02 (EmBase02, 0x8a76)
  - 292 uShellEm067_sp_13 (EmBase13, 0x8a77)
  - Only Zamtrios' set exists. Other variant monsters have a second row set (em066 282-289, em071 301-308), and the
    table has no free row.
- uShellEm067_sp_13: DTI 0x1894248 (static init 0x4a6548), size 0x16a0, new 0x49f3b8, ctor 0xf7ba30 (parent EmBase13
  ctor 0x404fbc), vtable 0x17e60cc + 8. Overrides vs EmBase13 (0x1756440 + 8):
  - slot 83 0xf7baac: loads the sh params. Ints 0..3 -> +0x15c8..+0x15d4. Floats via 0x4a3164:
    - f0 speed -> +0x15f8, f1 per-distance -> +0x15f4, f2 gravity -> +0x15ec
    - f3 min range x size -> +0x1600, f4 max -> +0x160c, f5 x size -> +0x15fc
    - vector list 0 (kinds < 2) or 9+ (kind 3) -> +0x167c.
  - slot 84 0xf7c048 (impact event 0 / 1 / 2): events 0 / 1 post the sp_01 residue, then 0x404f28 effect, then slot 82
    kill.
  - slot 92 0xf7c208 = **target point**:
    - kinds 0 / 1: list[param+0x30] * size, rotated by the owner angles (rec+88 / +80 / +84), + owner pos
    - kind 3: list[9 + i], y = rec+0x1d4
    - other kinds: rec+0x1d0 (the target slot).
  - EmBase13 slot 90 0x40616c calls slot 92 and the sh floats (launch).
  - Setup 0x405144: param+0x20 vec -> +0x1650, +0x30 -> +0x1640, u16 +0x34 -> +0x1588.
- em067_00.arc carries the three families: shell\em\em067_00_shell01 / 02 / 13. Each has a def XFS 0x4aa69872 that
  names `effect\pel\em\em067_00u` and `sound\pts\em\em067_00u`, per-kind ef / snd / hit / sh FUPs, HDS and HTS.
  - shell13: kinds 0, 1, 3, 4.
    - sh000 / 001 = {13, 0.0125, -2, 600, 3000, 180, (10, 495, 135)}, the 4U ball values.
    - sh003 = {12.5, .0125, -0.2, 500, 3000, 180, (7.4, 520, 461)}.
    - sh004 = {22.5, .0125, -1, 800, 4000, ...}.
    - ShellCmnParam holds the pattern vectors (its last two are the 4U sub-10 offsets).
    - HDS entries 0..3 = **4U records 7..10, byte for byte**, with: byte 0x12 & 3, +0x2c = 4U 0x12 >> 2 (= 2), byte
      0x19 = group 0..3, byte 0x1c = 8, +0x28 = 1.0. This is the same conversion as em089's shell_hds, except byte
      0x1c (8 here). HTS groups = 4U vols 4 / 6 / 7 / 8 (r50 / 100 / 50 / 100).
    - ef params (listId, uniqueId per event): kind 0 / 3 = [0, 1, 1, 1], kind 1 / 4 = [10, 11, 11, 11].
  - shell02: sh000 {life 192, length 3000, 30}, sh001 {life 45 (4U 50), length 4000, 110, 12}. HDS 0 = 4U record 12
    (s16 +2 = 9999, level 5, byte 0x1c 6). ef [30, 31].
  - shell01: kinds 8..11 -> HDS 5 / 7 / 6 / 7 = 4U records 63 / 72 / 71 / 72 (byte 0x1c 0xfe), HTS r125 / 200 / 125
    (4U 200 / 300 / 200). ef008..011 -> PEL 1 / 11.
- GU PEL em067_00u list 2 (code list): 0 = em067_00_012 mask 1, 1 = em067_00_014, 10 = em067_00_012, 11 =
  em067_00_014, 30 = em067_00_013, 31 = em067_00_018, 60 = em067_00_019 (shell ids). The class's own code posts use
  ids >= 1000 (S). Our em067_01u list 2 is a copy, so it holds the same ids and points at GU's EFLs. Our arc also
  carries em067_00u, the three GU families, em092_012 / em092_013 (no MEF record names them: in 4U they are code
  posts) and the em092 shell waves.

### 2c. Can GU's class + data express Tigerstripe?
- **Yes, for the look and the damage, and for the mode-0 balls (7/12, 7/13, 7/24) and 42 / 43** (S):
  - same flight parameters (C), same pattern
  - effects and attack are per-kind data: a TS family + TS PEL records + 4U TS HDS
  - residue: sp_01 with TS HDS.
- **Not as is** (GU dropped these rules for Zamtrios too, S):
  - The shell never sees the mode: the param has no mode, and slot 92 uses list 0 x 1.0. So the 7/202 (x0.5, table
    +10) and 7/203 (x1.5, table 0x10b6440) targets are lost, as are the mode-2 aimed balls at count 3 / 7 (rec+0x1d0)
    and their 2100 minimum range.
  - GU scales the minimum range by size (4U: 600 / 2100 unscaled at 0x74e288).
  - One residue per ball kind (4U: per impact kind; small balls post none on a kind-0 impact).
  - 43 aims at rec+0x1d0 (4U: along the facing, distance clamped).
  - The 42 / 43 u16 (T+18) is not passed.
- These gaps are all target or post rules. A derived class (vtable copy of 0x17e60cc + 8) overriding **slot 92** with
  the 4U target (captured from the GU action's own stack, see 5) and patching +0x1600 for the aimed balls closes the
  main ones. A full port (em089_shell016-style, from uShell012 0xc61b80 and uShell003) is only needed if GU's flight
  itself turns out wrong in game. Its per-frame path (0xc61ea0..0xc624dc) is not transcribed yet.
- uShell016 40 / 48: GU's sp_02 + TS data:
  - HDS 0 byte 0x0c 0x81 -> 0x11 (record 38)
  - sh000 length 3000 -> 2000
  - sh001 life 45 -> 50 (4U)
  - the effect (4U event-15 kind 7, scaled) is unresolved.

## 3. em089 shell framework: what is reusable
| piece | reuse |
|---|---|
| our request (em089_shell.c `em089_shell_post` tail: live count < 144 over mgr+0x6d8c, cSetupParamEmBase01 alloc, newInstance, 0x4a1c84 setResource, slot 79 setup, 0xc067ec(unit mgr, 18), 0x48c6c8) | **as is**, generalised to (class DTI, param, file id). For GU classes the param is GU's own (EmBase13 64 B vtable 0x1756be4 + 8 from 0x404e14(64, 16); EmBase02 48 B vtable 0x175585c + 8 from 0x3fc428), and the DTI = shell-table row[0] |
| fileResource 0x152960 + our file IDs (file_id hook) | as is (one def file ID per TS family) |
| ids: param+4 only matters through 0x4a1b38, whose 34 callers never test 290..292 (em089 notes) | keep GU's ids 290..292 |
| HDS conversion (tools/build_em089_arc.py shell_hds) | as is, but byte 0x1c = GU em067's value (8 for sp_13, 6 sp_02, 0xfe sp_01), not 6 |
| family copy with same-length path rename (shell_family) | as is: em067_00_shellNN -> em067_01_shellNN, plus `effect\pel\em\em067_00u` -> `...em067_01u` in the def |
| efl4u2gu extra_records / pel_record | as is for the TS records |
| uShellEnemy-derived class skeleton (vtable copy, DTI, dtor, deferred kill for attached effects) | only for the derived sp_13 (copy 0x17e60cc + 8 and the DTI 0x1894248 vtable instead) or for a full port |
| em089_efx_post_on / em089_snd_* | not needed with GU classes (effects and sounds come from the family's ef params + PEL-tied SE) |
| em089_shell016 / 051 / 005 geometry and per-frame code | em089-specific (subtypes, joints, booms) |

## 4. Multiplayer
- GU, quoting monsters/gogmazios/notes/port-checklist.md "Multiplayer":
  - "Handlers (slot 125) run on every machine. So motions, shells, effects and sounds are local, and the action serial
    ... is the controller's."
  - "setActionNext on a non-controller only marks a replay"
  - finding 7: "GU never sends damage over the network. Every machine tests every attack (local swings, replayed remote
    swings, shells) against its own monster copy ... only the controller applies them".
- em089 respected this: shells are posted from the handlers on every machine, never gated on EN_CONTROLLED (gating is
  kept only for the 4U owner-only branches W+0x1d9). Targets use the synced target slot (em089_target_hunter, F_TGT),
  not the local hunter. The pile and cannon hit shells are spawned on every machine.
- TS shells:
  - Post from GU's handler path on every machine (our hooks sit inside it).
  - Use only synced inputs:
    - the action serial and the W counters (W+0x1a2) advanced by the replayed motions
    - the target slot rec+0x1d0 (in the action message)
    - the GU stack target, which is built from those.
  - No local-hunter fallback, no RNG outside the action serial (4U uShell012 has none).
- Hunter damage / paralysis from an enemy shell is applied by each machine to the hunters it simulates (S, not traced;
  this is the same for GU's own shells, so it needs nothing from us).

## 5. Implementation plan

### 5.0 Decision (main session, 2026-10-21): data via Tigerstripe's own shell arc, not a request redirect
- GU's request 0x48c4f0 does not load a family by file ID: it takes the resource the shell manager preloaded for the
  shell id (r7 = [mgr + 0x1c + 4 * id], 0x48c5e4), checks the param DTI against the table row, news the row's class,
  0x4a1c84(shell, resource), setup (vt +0x13c), 0xc067ec unit add, 0x48c6c8 manager add. r7 is not in the hook regs.
- So: build our own shell arc (manifest field 25, today GU's shared arc\shell\em\em067_00_shell) holding the three
  families under GU's internal paths with Tigerstripe data (HDS from 4U records, def PEL path em067_01u, breath
  tweaks), with a new file ID. A quest with Tigerstripe then preloads Tigerstripe's families for ids 290-292; GU's
  Zamtrios quests never load our arc. Cost: a quest with both Zamtrios and Tigerstripe gets the first-loaded data
  (no such quest exists).
- Code: only the three mid hooks of 5a option 1 (variant byte 0 around GU's own post) + the restore in the existing
  0x48c4f0 entry hook (em067_01_gaps.c), keyed on the three return addresses.

### 5a. Hooks (all gated on `EN_ID + 5` (0xb5f5) == 1, i.e. TIGERSTRIPE_ZAMTRIOS_EM_ID; in module/em067_01_shells.c)
| hook | kind | variant-1 action |
|---|---|---|
| 0xf72700 (`movw r1,#0xb5f5; ldrb r1,[r4,r1]`, displaceable) | mid hook, return 0 | **option 1 (least code):** set monster+0xb5f5 = 0 so GU runs its own post; the 0x48c4f0 hook below restores it. **Option 2:** post ourselves: same param (kind count%3==1, +0x30 = rec+0x1a2 - 1), target = caller sp+32, spawn sp+48 (caller sp = regs + 32 B) |
| 0xf735c0 (`movw r0,#0xb5f5; mov r1,r4`) | mid hook, return 0 | same for 43 (kind 4) |
| 0xf73870 (`ldr r0,[sp,#0xc]; ldrb r0,[r0]`) | mid hook, return 0 | same for 42 (kind 3); option 2 needs r6 / r10, which are not in regs -> option 1 |
| existing `em067_01_post` = 0x48c4f0 entry | entry, return 1 = replaced | LR 0xf7283c / 0xf7366c / 0xf738f4 (the three posts above): restore variant = 1, then our request (class: sp_13, or the derived class in stage 2; param = r1 as GU built it; resource = TS shell13). LR 0xf72dd8 / 0xf746e8 / 0xf755f0: our request with TS shell02. LR 0xf7c098 (sp_01 residue, owner = param+0xc): our request with TS shell01. regs[R0] = shell |
- Mid hooks must always return 0: a nonzero return does `bx lr` from inside GU's function. No branch lands on
  site+4 of the three mid-hook sites (C; f72700 itself is a branch target, which is allowed).
- Option 1 is safe because f72710..f72838, f735d8..f73668 and f73880..f738f0 are straight-line code that always reaches
  0x48c4f0 (C; GU does not check the param allocation).
- Stage 2 (fidelity), derived sp_13 class:
  - At the 0x48c4f0 hook (LR 0xf7283c), store the 4U target in our fields: caller sp+32, which already holds the mode
    table / scale and the mode-2 hunter target. Store the mode from the action number (7/202 -> 1, 7/203 -> 2) or from
    an entry hook on 0xf722d0 (r1).
  - slot 92 returns that target.
  - After slot 83, write the unscaled 4U minimum range (600, or 2100 when mode 2 and count in {3, 7}) to +0x1600 (G:
    check how slot 90 uses it).

### 5b. Data (monsters/tigerstripe_zamtrios/tools/build_em067_01_arc.py)
- **As built (shell_data / ball_fx_list2):** the shell arc (field 25, `arc\shell\em\em067_00_shell`, ARCS) and the
  three families are entries of GU's monster arc em067_00.arc, so em067_01.arc keeps them under GU's paths and file
  IDs (no rename, no new file ID) with Tigerstripe's data. The three defs' PEL path -> `em067_01u` (same length); GU's
  em067_00u then leaves our arc. Same first-loaded cost as 5.0. The HDS conversion asserts GU's own entries equal 4U
  Zamtrios records 7..10 / 63, 71, 72 converted before writing Tigerstripe's. shell02 not touched yet.
- (Plan, superseded:) Three families: shell\em\em067_01_shell13 / 01 / 02 = copies of GU's, with the path rename and
  the def's PEL path `em067_01u` (same lengths). Keep `sound\pts\em\em067_00u` (shared). One new file ID per def.
- shell13 HDS entries 0..3 <- 4U uShell012 records 29 / 30 / 31 / 32 (0x1028904 + 84 + 40 i), with the GU conversion
  and byte 0x1c = 8. HTS unchanged.
- shell01 HDS 5 / 6 / 7 <- 4U uShell003 169 / 171 / 172 (0x101efbc + 628 + 40 sub), byte 0x1c 0xfe. HTS groups 5..7 ->
  4U r200 / 200 / 300 (faithful), GU had 125 / 125 / 200. Entries 0..4 stay GU's.
- shell02: HDS 0 byte 0x0c = 0x11 (4U record 38); sh000 length 2000; sh001 life 50.
- PEL em067_01u list 2 (built): by path, `effect\em\em067\em067_00_012` (records 0 / 2, flight) ->
  `effect\efl\em\em092\em092_012` and `em067_00_014` (records 1 / 3, impact) -> `em092_013`, state bytes kept, so the
  ef params stay byte-identical to GU's. (The plan's indices 0 / 10, 1 / 11, 30 / 31 counted another list.)

### 5c. Open risks / questions
1. 0xc07ecc kind 7 (uShell016 40 / 48 effect, event 15): which EFL is it? Is the visible TS breath a motion effect?
2. The meaning of the TS 42 / 43 u16 (4U [this+0x8d88]+18 -> shell +412; GU +0x1588 -> attack arm) and its GU
   counterpart. Paralysis might depend on it (G).
3. PEL-tied sounds: the families use PTS em067_00u (GU Zamtrios' shell SE), while 4U TS plays its own 201 / 206 from
   the em092 bank (our arc has em092_se_shell_*). Check by ear; may need a TS PTS.
4. GU event semantics of slot 84 (0 / 1 / 2) vs 4U impact kinds 0 / 1: residue per kind (stage 2 / slot-84 override if
   it matters).
5. Pattern tables: 4U 0x10b6300 / 0x10b6440 and GU 0x2135090 are bss (static inits 0xd25830 / 0xd258c4, GU
   unknown). Only the 4 sub-10 vectors in GU's ShellCmnParam were matched (C). Emulate the inits if exact patterns
   matter.
6. 7/202 / 7/203 reachability comes from the heuristic EMC tokenizer: confirm with the action log (tzreport.py)
   before stage 2.
7. In game: the log should show our request lines; the balls must appear with the em092_012 effect and paralyse; the
   residue should paralyse inside r200 / 300 for 10 frames. **Confirmed 2026-10-21** (user: "All fixed"): the three
   hooks fired (f72700 x9, f73870 x6, f735c0 x5), GU posted id 292 kinds 0 / 1 / 3 / 4 and the residue id 290 kinds
   8..11 (from f7c098), no crash. Ball effects: shells look up PEL list-2 records by id (state +0x30): 0 / 10 =
   flight (em092_012), 1 / 11 = impacts (em092_013); the breath shell's 30 / 31 are untouched.
