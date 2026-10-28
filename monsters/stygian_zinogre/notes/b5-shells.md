# Stygian Zinogre B5: shells and code-posted effects (design, 2026-10-28, static study, nothing built)

Scope: plan.md B5 (+ the B4 effect items that belong to the same posts). 4U = MH4U v1.1 (`dump/mh4u.asm`,
`tools/dis4u.py`), GU = MHGU 1.4 main (`MHGU_Editor/scratch/main.asm`). W = 4U `[this+0xe28]`, rec = GU `[this+0x1428]`.
C = read in code / data this session or in a cited note, S = strong, G = guess. Every 4U address below was read.
Precedents used: Tigerstripe `notes/shells.md` + `em067_01_shells.c` / `em067_01_gaps.c` / `em067_01_shell016.c`;
Gogmazios `em089_shell*.c`, `port-checklist.md` "Multiplayer"; Dalamadur `dala_shell.h/.c`, `dala_shell003.c`.

## 0. Corrections to phase1-variant-map.md / the stubs (all C)
| # | earlier note | fact |
|---|---|---|
| 1 | "0x6639a0 = uShell010 (event 10)", stub `sz_shell010` (em057_01_mv_d.c) | 0x6639a0 -> 0x661c5c -> 0x660e88 **type 3 = uShell003** (case 0x661044: alloc 696 = uShell003 DTI size 0x2b8, ctor 0xc55b10). uShell010 is type 10 (case 0x661178, 672 B, ctor 0xc602d8). The stub's own comment already says "message 3". Zinogre's 129 / 235 are uShell003 too |
| 2 | 858428 "effect 0xc094e8 (58, 12)" vs batch D "0xc094e8 is pure" | both right: 0xc094e8 = surface class of the ground hit, stored at effect request +0x18 (0x858454 -> sp+0x40); the post is **0xc08628** at 0x85849c (request sp+40: +6 = 58 / 57, +8 = 12 / 3). Charged: sound 205 at the point first (0x858410) |
| 3 | uShell044 3 sites: 847098, 84dfc8 | also **2/40** (0x84516c r1 = 1): 0x84538c / 0x845580 post subtype 3 (frame tables 0xfebb28 / 0xfebbb8), no em test (phase2-actions.md line for 84516c) |
| 4 | 0xc0819c "event-20 effect object" | new **uMhRadialBlurFilter** (200 B, ctor 0x3e3cbc, vtable 0xe6313c -> DTI 0x10b87b0), unit line 20 (0x64608c), only when the area = the local player's (*0xfb6b7c +0xc90): a screen blur, not an EFL. Gogmazios (em089_efx.c `em089_efx_roar_blur`) and Dalamadur (`dala_efx_radial_blur`) left it a logged deviation |
| 5 | "charged Stygian ... posts subtypes 0 / 2 / 3" | homing subtypes 2 / 3 only at quest rank >= 5 (G) or action param 4 == 5 (7/211 212); the vt77 orbs (subtype 4) only at rank >= 5 (0x85601c). Uncharged Stygian posts orbs too (one) |
| 6 | 72-B orb records "copied by rank" | the records and the 24-B frame tables hold only their floats in .data; their vectors are 0 in the image and filled by a static init (refs 0xd2827c 0xd28284 0xd282c4 0xd288b4 0xd288b8 0xd288bc). **Vector values not read yet** (step 1) |

## 1. 4U behaviour

### 1a. uShell046: the orbs (C unless marked)
Class: DTI 0x10bc210, size 0x338, vtable 0xe6e6ac: ctor 0xc8a754 (event 46, case 0x6617a8), slot 22 init 0xc89184, 23
per frame 0xc892f0, 24 kill = base 0x9ab16c (0xc8a750), 4 = `bx lr`. Only uEm048 posts type 46 (callers of 0x6629bc:
0x84f124 0x8561f0 0x856234 0x856278 0x8562dc 0x856330).
Poster 0x6629bc(mgr *0xef3cf0, owner, sub, &rec.off, [sp] &rec.A, &rec.B, &origin, &angles, u16 0xffff; s0-s5 = rec
floats); wrappers 0x84f0e4 (sub 0), 0x85629c (2), 0x8562f0 (3), 0x855fe4 (4). Origin = W+408 (monster position),
angles = [work]+68 / +72 / +0x4c = W+424 / W+428 / W+0x1b0 (the monster's angle triple; 0x856150..0x856194).

Post sites:
| 4U site | actions (4U params r1 r2 r3 [sp]) | rule |
|---|---|---|
| 0x84c280 step 1, frame 88 (s19, 0x84c620; em test 84c6a0) | 7/32 (1,0,2,0) 33 (0,0,3,0) 34 (0,0,4,0) 61 (1,2,2,1) 62 (0,2,0,1) 63 (1,2,0,1) 66 (0,0,0,0) 87 (1,0,0,0) -> our rows -> GU efa930; 7/211 (0,0,0,5) 212 (1,0,0,5) KEEP -> GU efa930 | r7 = param 2 (0x84c290), r8 = param 4 (0x84c2ac). Record kind k = 0 if r7 in {0, 1} else 1. **Uncharged**: one orb, record (k, 0) (0x84c91c..0x84ca18). **Charged**: two orbs, (k, 0) + (k, 1) (0x84c6dc.., 0x84ca1c, 0x84cb60). Subtype: if r8 == 5 or questRank >= 5: charged -> 3 + 2 (0x84caa8..0x84cadc), uncharged -> 2; else 0 (+ 0) |
| 0x84c280 step 2, frame 58 (0x84cd34; em test 84cd50) | same actions | same scheme with kind-1 records idx 2 / 3 (0x84cd98..0x84cdc0) (S: block 0x84cd60..0x84d23c to transcribe) |
| vt77 0x857ba8, 7 motion events (857f9c 8580d4 858278 85860c 858704 8587d8 858830) -> 0x855fe4(case 0..6) | any action playing those motions | rank >= 5 only. Records kind 2 (0xfec098) pairs per case: 0 (2,3), 1 (0,1), 2 (4,5), 3 (6,7), 4 (8,9), 5 = 0, 6 = 1; A.y += 300 (0x856148); charged: both posted as subtype 4, uncharged: the first only (0x8561b8..0x856278) |

Records: 0x856900(this, out, kind, idx) (rank = questRank 0x69ae70): rank < 5: kind 0 -> 0xfebc18, else 0xfebd38; rank >= 5:
kind 1 -> 0xfebf78, kind 2 -> 0xfec098 (idx <= 9), else 0xfebe58 (idx <= 3). 72 B = off, A, B (float[4], static init) +
f0..f5. Floats (C):
| table | f0 speed to A | f1 speed to B | f2 age limit | f3 arc | f4 wobble radius | f5 wobble speed |
|---|---|---|---|---|---|---|
| 0xfebc18 (HR, kind 0) | 4 / 2 / 25 / 20 | 50 50 35 35 | 600 | -300 -500 300 500 | 50 | 50 |
| 0xfebd38 (HR, kind 1) | 70 | 7 15 7 15 | 300 | 500 | 50 | 3 |
| 0xfebe58 (G, kind 0) | 6 3 6 3 | 35 | 600 | -300 -500 300 500 | 50 | 50 |
| 0xfebf78 (G, kind 1) | 4.2 4.5 2.1 2.25 | 7 15 7 15 | 800 800 900 900 | 500 | 50 | 3 |
| 0xfec098 (G, vt77, 10 rows) | 4 2.8 4 2.8 2.6 2 4.5 3.8 3.5 3.5 | 55 | 600 | +-300 / +-500 | 50 | 50 |
(The column names are uses, not 4U names: f0 0xc8a1fc in phase 0, f1 in phase 2, f2 0xc89430 / 0xc8977c / 0xc89cb8,
f3 0xc8a6b8, f4 / f5 0xc8a334.)

Ctor 0xc8a754: pos +0x100 = origin + Ry Rx Rz(angles) * off; A +0x278 and B +0x288 the same with rec.A / rec.B; f0..f2 ->
+0x298..+0x2a0, f3 +0x2e0, |f4| +0x2f8, f5 +0x2fc / +0x300; area +0x130 = W+0x14c. **Target** (sub 2 / 3 / 4, owner em 49
only, 0xc8ab40..0xc8ac58): W+0x278 in {0, 1} and W+0x27c != 255 -> t = 0x92c960(owner, W+0x27a), kept when
0x91f8bc(owner, t, 0) (t in the owner's area, t state +0x371 != 8, 0x6832c8 test); +0x324 = t, +0x328 = t's position
([t+0xe30]+0x10) with the **y rule** (y <= 0: y + 150; 0 < y <= 150: 150; else unchanged).
Init 0xc89184: subtype < 5 and owner, else dies; effect (58, 20) = **em049_015** on the shell (table 0x10308a8, request
+0x5c = shell; no effect -> dies, 0xc89254); attack record = subtype (0x10307e0 + 40 sub, all five identical: window 0+99,
power 60, type 0x1f, +0x0c 0x21, +0x10 0x80, +0x12 4, vol 0 = bone 1001 r130), arm 0x9ab120(.., 23, 2); u16 != 0xffff ->
request group +412; then the first per-frame.
Per frame 0xc892f0 (phase +0xf2):
| phase | sub 0 / 1 (path 0xc89430) | sub 2 / 4 (0xc89cb8) | sub 3 (0xc8977c) |
|---|---|---|---|
| 0 -> 1 | velocity = unit(A - pos) * f0, leg time T = abs(A - pos) / f0 (0xc8a1fc) | same | same |
| 1 -> 2 | when the leg timer reaches T | sub 4: v = 0 and 30 more frames (0xc89d74..0xc89dbc) | same as 0 / 1 |
| 2 -> 3 | B = record B | sub 2: B = t's position NOW (y rule; t invalid -> record B) (0xc89fc4); sub 4: B = +0x328 (0xc89dd0) | B = t's position now (y rule), then B += unit(B - owner pos) * **600** (0xc8986c..0xc8996c) |
| 3 | leg to B at f1; offset f3 * sin(pi t / T) along axis *0x10e63a8 turned by the leg's pitch / yaw (0xc8a664; axis value G); sound 224 on the shell at the leg start | same | same |
| 4 | straight on with v = (cur - prev) / dt (0xc89604) | same | same |
| wobble | sub 0 / 1 only, phases 3 / 4 (0xc8a714, C): offset +0x310 moves at f5, re-aimed about +-22.5 deg (+-4096) when u16 [*0xfb6b7c]+0x22 < 4096 (G: a global random), reversed at radius abs(f4) (0xc8a334; details S) | no | no |
Ends (all paths, C): owner gone (0x917620) -> slots off, state 3; attack slot inactive (+0x16d == 0, 0xc89338) -> state 2,
no effect; age >= 18000 (0xc89344); flight effect dead (0xc89368); age >= f2 -> end effect (58, 22) = **em049_017** at the
position, state 2; collision 0xc8a288: slot byte +0x16e != 255 (the attack connected) -> "2" at the position, else map
segment 0x2b96e4(prev -> pos, mask 48) -> 0 (wall, bits 0x22) / 1 -> impact effect (58, 22) at the point + sound 216 there
(0x312484), state 2. ~~The slot goes inactive when start + length run out: an orb lives at most 99 frames~~ (wrong,
8g: the per-frame resets the slot's window length to 100 every frame, so the age limit f2 or an impact ends an orb).
Sounds: 215 on the shell every 22 frames (0xc893a8), 224 at the B leg, 216 at the impact.
Arm (23, 2): the attack is a sphere r130 on bone 1001 = the shell's capsule pos -> prev pos (+0x120 = prev each frame,
0xc8a500) (S: swept test).

### 1b. uShell044 subtype 3: the dragon pillars (C unless marked)
Class: DTI 0x10bc1d0, size 0x2e0, vtable 0xe6e5cc: ctor 0xc8835c (case 0x661750), init 0xc87f10, per frame 0x9a9a3c.
Poster 0x662904(mgr, owner, sub, &ofs, [sp] &angles, u16 grp, u8 b8, s0 f): the posters pass the offset already turned by
the yaw; the ctor adds owner +224..+232 (S: the owner's base position vector, base slot 15 0x6d3e5c adds to it).
| 4U site | actions | GU today | spawn |
|---|---|---|---|
| 0x84716c (0x846ec4, em test 847098) | 1/6 15 16 17 28-33 (charge stance) | ef4280 / ef4488: same loop, post removed (ef4484 `== 1` test) | rows 0xfeba98 (24 B: frame, -, offset): frames 64, 128, 128, 182, 182; offset turned by yaw (0x8470ec..0x847148) |
| 0x84538c / 0x845580 (0x84516c r1 = 1) | 2/40 (charge walk) | ef62e4(1): no post (GU-wide, like Zinogre) | rows 0xfebb28 (40, 90, 90, 140, 140) and 0xfebbb8 (30, 78, 78), one per step |
| 0x84dff4 (0x84dd44, em test 84dfc8) | 7/113 7/115 (charge transition) | ported (em057_01_mv_f.c), stub `sz_shell044` | 12 ring points |
Subtypes 1 (Zinogre) and 3 (Stygian) run the same code (init case 0xc88070, per-frame case 0x9aa458); only the tables
and the burst effect (`cmp #1`, 0x9aa4b8) differ:
| | sub 1 (Zinogre) | sub 3 (Stygian) |
|---|---|---|
| gather effect (init, 0xc880ec, table 0x1030260) | (57, 19) em048_020 | (58, 25) **em049_020** |
| burst effect at window start (0x9aa4a4) | (57, 18) em048_019 | (58, 24) **em049_019** |
| record (0x10300d0 + 40 sub) | window 50+10, power 80, type 0x1f, +8 0x40, +0x0c 0x41, +0x10 0x40, +0x12 4, vol 1 | same except +0x0c **0x21**, +0x10 **0x80** |
| arm (0x10302b0) | (7, 2) | (7, 2) |
Life: init sound 217 on the shell; capsule +0x120 = pos + (0, 2000, 0) every frame (vol 1 = bone 1001 r200: a vertical
column 2000 high); at frame 50 (slot start timer +444 <= 0, once): burst effect at the position, gather effect released
(0xc470dc), sound 218 on the shell; dies when the window ends (frame 60) or at age 400 (table 0x10302c4) or when its
effect is gone (0x9a9b4c).

### 1c. uShell003 135 / 236: the slam blasts (C)
Class: DTI 0x10bb32c, size 0x2b8, vtable 0xe6d3dc (ctor 0xc55b10, init 0xc544d0, per frame 0xc54b04, kill 0xc5598c),
already ported for Dalamadur's subtypes (dala_shell003.c). 129 / 135 and 235 / 236 all take the init **default** path
(0xc54628..0xc54648 -> 0xc54ad4; table 0xc546f4 for 233..239: 235 / 236 -> 0xc54ad4): only data differ.
| | 129 (Z) | 135 (S) | 235 (Z) | 236 (S) |
|---|---|---|---|---|
| record 0x101f230 + 40 sub | window 0+10, power 100, type 2, +8 80, +0xb 50, **+0x0c 0x41**, +0x10 0, +0x12 0, +0x1c 0x1c | +0x0c **0x21** | as 129 | +0x0c **0x21** |
| volume (0x101efbc[+0x19]) | 106: bone 255 r200 | 110: r180 | 152: r220 | 153: r200 |
| effect 0x101dfcc (8 B {grp, elem, -, mask}) | (57, 22) em048_023 | (58, 27) **em049_022** | (57, 22) | (58, 27) |
| sound 0x101e7c4 (8 B) | kind 2, id 226 | same | same | same |
| arm 0x101ddcc | (31, 2) | same | same | same |
Event (stub comment, C): {owner, 1, sub, pos = paw joint at the ground height, rot = euler of the ground-aligned basis,
kind = surface class (0xc094e8) -> effect variant, area, grp = the slam's hit group, sub2 = hit attribute bits}. Ends:
window end (10 frames) or age 200 (dala_shell003.c). Sites: 0x84f900 (7/190 191), 0x850164 (7/217), 0x8508fc (7/218),
0x852968 (7/220) = batch D's `slam_shell` (0x850ef4 = 7/219, not ported).

### 1d. Code-posted effects outside the shells (C unless marked)
| 4U | what | GU today | plan |
|---|---|---|---|
| 0x856f0c (charge state change, from vt47 via 0x856344) | partMeatBase 0..5; effect 0xc088d8 on the monster: (58, 11) **em049_002**, in cat 11 (58, 14) **em049_005** (Zinogre (57, 2) / (57, 5)); sound 210 / 213 at a joint (0x304c34) | eefda4: same partMeatBase, then controller this+0xb640 vt[0x1d0/4](id): 0x3ec if cat 11 and v == 0, else 0x3ed (v1: 0x3ed) | entry hook eefda4 for v1: same body with our effect + sound (step 9) |
| vt77 0x8583c8..0x85849c (one motion event) | 0xc08628 (58, 12) **em049_003** at a point, request +0x18 = surface class; charged: sound 205 there | nothing for any variant (no 57 / 58 ids in uEm057_00) | effects batch (step 9): post from the vt170 hooks when the 4U case is matched |
| 0x847274 frame 66, joint 4 (roar 1/39 42 43, ported: stub `sz_effect_c0819c`; KEEP 1/9 34 37 38 run GU ef45e0, which drops it, plan.md E2) | 0xc0819c radial blur | none | logged deviation as Gogmazios / Dalamadur (question 6) |
EFL group 58 = list 0xef6fbc (table 0xef895c): elements 9..28 = em049_000..023 (11 -> 002, 12 -> 003, 14 -> 005,
20 -> 015, 22 -> 017, 24 -> 019, 25 -> 020, 27 -> 022). All eight files are in em049.arc and already converted into
em057_01.arc (build_em057_01_arc.py `effects`, em049's EFL family).

## 2. GU mechanism

### 2.0 Precedents (C, their notes and code)
| port | 4U shell | GU vehicle | data / visuals | MP |
|---|---|---|---|---|
| Tigerstripe balls | uShell012 40-43 (= Zamtrios 8-11 code) | GU's own uShellEm067_sp_13 (id 292) via GU's request: mid hooks f72700 / f735c0 / f73870 set the variant byte to 0, `em067_01_post` (0x48c4f0 entry) restores 1 | Tigerstripe data in em067_01.arc under GU's paths and file IDs (4U records as HDS, asserted on GU's own; PEL list-2 records repointed to em092 EFLs); accepted cost: first-loaded data wins when both monsters load (no such quest) | posts from the replayed handlers on every machine; synced inputs only |
| Tigerstripe blast | uShell016 38 / 49 | own class uShellEm067TsBlast (em067_01_shell016.c), own request, resource = GU family 0x8a76 (its own data in the arc) | own PEL records 4238 / 4249 / 4300, sounds 0x4efd74 / 0x4efb98 / 0x4eff24 with 4U ids | every machine |
| Gogmazios | uShell050 / 051 / 016 / 005 | own classes (em089_shell*.c), own request, Kushala's family 00 copy as HDS / HTS | own PEL records (em089_efx.c), shell outlives its effect | target = slot-0 hunter (em089_target_hunter), never gated on EN_CONTROLLED |
| Dalamadur | uShell001 / 003 / 005 / 016 / 029 / 038 | own classes on a shared framework (dala_shell.c) | family em090_00_shell00 (Kushala's copy, HDS / HTS from 4U), def file ID from its range | no net test in 4U, each machine posts its own |

### 2a. What GU has (C)
- Shell table 0x1763448 (12-B rows {class DTI, param DTI, def file ID}): 247 uShellEm057_sp_01 (EmBase01, 0x8a4a =
  `shell\em\em057_00_shell01\em057_00_01`), 248 uShellEm057_sp_18 (EmBase00, 0x8a4b = `..._shell18\em057_00_18`);
  Thunderlord 249 sp_01 0x8a4c, 250 sp_11 0x8a4d, 251 sp_18 0x8a4e. uEm057_00 (0xeee9d4..0xeeea60): this+0xcafc = 247 / v4
  249, +0xcb00 = 248 / v4 251, +0xcb04 = 413 (none) / v4 250, preloaded with 0x48c388. Variant 1 uses 247 / 248. The
  table has no free row and ids stop at 412 (em089_shell.c).
- em057_00_shell01 (sp_01): kinds 0..13. Hit params: kinds 0..11 -> HDS 0, 12 -> 1, 13 -> 2. HDS 0 = 4U uShell044 record
  1 (Zinogre pillar) converted by the em089 rule **byte for byte**; HDS 1 / 2 = 4U uShell003 129 / 235 except +0x2c = 2
  (the em089 rule gives 0 from +0x12 = 0) and 0x1c 0x1c -> 6. HTS: g0 bone 1001 r200 with +4 = 1, g1 bone 255 r200, g2
  bone 255 r220 (= 4U vols 1 / 106 / 152). Kinds 0..11 carry two floats each in their sh params (1300 / 350, 600 / 40,
  ...): the 7/113 ring of 12 baked into kinds (S), so GU's 7/113 (efb5f0 -> efb884) posts kinds by ring index.
- em057_00_shell18 (sp_18): kinds 0..5, 42..51, 54, 55, one HDS = 4U uShell044 record 0 retuned (window 0+9999,
  +0x0c 0x241 vs 0x1001, HTS r100 vs 4U r130): GU Zinogre's thunder orb (S), posted by f03708 (v0 only).
- Nothing for uShell046 in GU (no 0x21-element HDS in em057's families, no Stygian kind; Thunderlord rows are v4 only).
- GU efa930 = 4U 0x84c280 with the same params: entry `push {r4-r9, r11, lr}; vpush {d8-d11}`; r7 = r1, r6 = r2, r8 = r3,
  r9 = [sp] (0xefa944..0xefa964). Its two v0 posts match 4U's two sites: frame 88 = 4U s19 (GU 0xefaa58 literal
  0xefae24 = 88.0) and frame 58 = 4U 0x84cf64 (GU 0xefaaa0 literal 0xefae28 = 58.0).
- GU vt170 ef27b0 = 4U vt77: per current motion (r5) and atFrame, then the variant test and `b 0xef2dac(k)`: sites
  (movw, k): ef2aa8 6, ef2b48 0, ef2b84 1 (`== 0` test), ef2bd4 2, ef2c80 3, ef2cbc 4, ef2cec 5.
- GU's 1/6 loop ef4484: `movw r0,#0xb5f5; ldrb r0,[r4,r0]; cmp #1`, rows = GU's own copy of 0xfeba98 at bss 0x2132a50
  (32-B rows, filled by a GU static init: readable at run time).
- No direct branch lands on efaa70, efaab8, ef4488 or the second word of any vt170 site (rg on main.asm: none; ef4484
  itself is a branch target from ef4444, which is allowed). Computed jumps not excluded (S).

### 2b. Decision (recommended)
1. **Own GU classes, literal 4U translations** (the Gogmazios / Dalamadur / Tigerstripe-blast pattern): uShellEm057_01Orb
   (uShell046, all five subtypes; Stygian uses 0, 2, 3, 4), uShellEm057_01Pillar (uShell044 subtype-1/3 path), and
   uShellEm057_01Blast (uShell003 default path, from dala_shell003.c). Each derives from uShellEnemy (0x43b3f8, 0x15d0 B)
   with our DTI and vtable copy (slot 1 delete, 5 getDTI, 9 move, 16 kill, 79 setup), posted by **our own request**
   (copy of 0x48c4f0's tail: live count < 144, cSetupParamEmBase01, newInstance, 0x4a1c84 setResource(fileResource(our
   def ID)), slot 79, 0xc067ec(unit mgr, 18), 0x48c6c8), never through rows 247 / 248.
2. Why not Tigerstripe's variant-byte trick: GU's v0 post (f03708, row 248 sp_18) is GU Zinogre's thunder orb (4U
   uShell044 0, other motion, other data), not uShell046; and Tigerstripe's "our data under GU's paths" works only when
   no quest loads both monsters, while **m10612 has Zinogre and Stygian** (quests.md): one of them would get the other's
   shell data (rows are preloaded per id).
3. Why not GU's sp_01 for the pillars: its kinds 0..11 take their positions from per-kind params (the 7/113 ring), so the
   1/6 and 2/40 positions do not fit (S). The blasts could ride sp_01 kinds 12 / 13 with our family (alternative), but the
   literal port keeps 4U's effect, sound and surface-class handling in one file and reuses dala_shell003.c's checked code.
4. **One resource family** for HDS / HTS: copy of GU em057_00_shell01 -> `shell\em\em057_01_shell01\em057_01_01`
   (same-length rename, the def's PEL path `effect\pel\em\em057_00u` -> `em057_01u`), one new def file ID in 0x108c0..0x108ff
   (22 used). HDS / HTS = Capcom's conversion delta-patched where a Zinogre twin exists (Tigerstripe's dttune method),
   the em089 rule elsewhere, all asserted (table in 3).
5. **Effects** by PEL list-2 records in em057_01u (a free id block, e.g. 3200+, asserted free; today list 2 is a copy of
   GU em057_00u's): em049_002 003 005 015 017 019 020 022, posted the em089 / dala way (shell = attach target, the shell
   outlives its effect, live effects moved each frame). **Sounds**: 4U request ids through GU 0x4efe58 (on an object) /
   0x4efb98 (at a point) with the owner, as em089_snd / dala_snd.

### 2c. Hooks and posts (all gated on EN_ID == 0x139; mid hooks always return 0)
| site | kind | instructions moved | variant-1 action |
|---|---|---|---|
| 0xefa930 GU efa930 | entry, return 0 | push / vpush (C) | store r1..r3, [sp] (the 4U params) for this monster (covers our rows and KEEP 7/211 212) |
| 0xefaa6c | mid | `movw r0,#0xb5f5; ldrb r0,[r4,r0]` | sz_orb_volley(self, step 1) = 4U 0x84c6b0..0x84cae0 (Stygian branch) with the stored params; GU then skips its own post (v != 0, 4) |
| 0xefaab4 | mid | same pair | sz_orb_volley(self, step 2) = 4U 0x84cd60..0x84d23c |
| 0xef2aa8 0xef2b48 0xef2b84 0xef2bd4 0xef2c80 0xef2cbc 0xef2cec (vt170) | mid x7 | same pair (r4 = this) | sz_orb_event(self, k) = 4U 0x855fe4(k), k from the site table in 2a; each GU (motion, frame) to be matched with its 4U vt77 site (S: GU kept 0x856680's case numbering) |
| 0xef4484 (1/6.. loop) | mid | same pair | 4U 0x847098 loop: atFrame(row frame) -> pillar at the yaw-turned row offset; rows from GU's runtime table 0x2132a50 (cross-checked once against step 1's 4U values) |
| 0xf03620 em057_01_act (existing slot-125 hook) | add a post scheduler | - | 2/40: 4U 0x84516c's two frame-table loops (0xfebb28, 0xfebbb8 by step) -> pillars (S: atFrame gives the same answer before GU's handler as inside it) |
| 0xeefda4 GU charge effect | entry, return 1 for v1 | push / mov (check at build) | partMeatBase 0..5, effect em049_002 / em049_005 on the monster, sound 210 / 213 (4U 0x856f0c) |
| our handlers (em057_01_mv_f.c 7/113 115, em057_01_mv_d.c 7/190 191 217 218 220) | direct calls | - | stub bodies replaced: `sz_shell044` -> pillar post, `sz_shell010` renamed `sz_shell003` -> blast post |
build.py checks the moved pairs (no pc-relative, no branch); the efa930 / eefda4 prologues to re-check at build.

### 2d. Files
- New: `module/em057_01_shell.c` (framework: copy of dala_shell.c with sz_ names; request, arm, timers, sounds, efx posts),
  `em057_01_shell046.c` (orb class), `em057_01_shell044.c` (pillar + blast classes), `em057_01_orbs.c` (volley / event /
  1/6 / 2/40 posts + the hooks above), `em057_01_shelldata.h` (vectors from step 1, record floats, frame tables).
- Changed: em057_01.h (prototypes, `sz_shell010` -> `sz_shell003`), em057_01_mv_d.c / _mv_f.c (stub bodies),
  em057_01_moves.c or _diag.c (2/40 scheduler in the slot-125 hook), module/build.py HOOKS (efa930, efaa6c, efaab4, 7 x
  vt170, ef4484, eefda4), tools/build_em057_01_arc.py (family, HDS / HTS, PEL extra2), manifest / FILE regenerated
  (FILE only gains the def). install.sh only if a new switch appears (e.g. `SZ_NO_SHELLS`).

## 3. Assets
| need | 4U source | tool status |
|---|---|---|
| EFLs em049_002 003 005 015 017 019 020 022 | em049.arc | converted (build_em057_01_arc.py `effects`) |
| PEL list-2 records for them (scale, attach, loop flags from the 4U requests) | 4U request fields (0xc891c8.., 0xc880ec, 0xc5540c, 0x856f5c..) | **missing**: efl4u2gu effect_set `extra2` entries + a free id block |
| surface-class variants (request +0x18) for em049_003 / em049_022 | 0xc094e8 classes 0..5 | **open** (G): how GU expresses a 4U material variant (efl4u2gu `soil`?) |
| shell family + def file ID | GU em057_00_shell01 (template) | **missing**: `shell_family` / `shell_hds` / `shell_hts` like build_dalamadur_arc.py |
| HDS entries | uShell046 0 (= 1..4); uShell044 3; uShell003 135, 236 | 044 3 = GU entry 0 + 4U delta (+0x0c, +0x10); 135 / 236 = GU entries 1 / 2 + delta (+0x0c, +0x19 group); 046 = em089 rule (validated exactly on uShell044 1 -> GU entry 0); asserts: GU entries 0..2 == rule / twin |
| HTS groups | u046 vol 0 (bone 1001 r130), u044 vol 1 (r200), u003 vols 110 (bone 255 r180), 153 (r200) | GU g0 with r130 / g0 as is / g1 with r180 / g1 as is (keeps GU's +4 = 1 for bone 1001) |
| vectors of the 5 orb tables, 0xfebb28, 0xfebbb8 (and 0xfeba98 for the cross-check), axis *0x10e63a8 | 4U static init (0xd28xxx), MT constants | **missing**: run the 4U static inits under unicorn (MHGU_Editor venv, as guemu.py / Tigerstripe's 0xd25830 run) and bake the values with asserts |
| sounds 205 210 213 215 216 217 218 224 226 | 4U call em048 + bank snd_em049 (lbug_fly_lp, lbug_bomb*, ...) | converted request (snd4u2gu monster_entries): **assert** these ids exist in em057_01's request |

## 4. Multiplayer (C unless marked)
- GU sends no shell request and no damage over the network: handlers (slot 125), vt170 and efa930 run on every machine,
  so each machine posts its own shells from the replayed action, as GU's own shells and 4U do (4U 0x660e88: unit add,
  no send; Gogmazios port-checklist "Multiplayer" finding 7). Hits on hunters are applied by the machine that simulates
  the hunter (S, as Tigerstripe notes).
- Inputs are synced: action + serial and target slots 0 / 1 (rec+0x1d0, rec+0x230..0x23c) travel in the action message;
  questRank is the quest's; GU's own orb post reads isCharged (rec+0x5df3) on every machine (f0371c), so the charge flag
  is expected consistent (S). No W+0x1d9 test anywhere in uShell046 / 044 code or the post sites (scan of the ranges
  above): nothing is gated on EN_CONTROLLED.
- Homing: the target index comes from rec+0x230 (= 4U W+0x278..0x27c; em089_act.c `slot_hunter` decodes it) -> the
  same hunter on every machine; its position is read locally, so on the target's own machine the orb aims exactly at
  him (the hit counts there); elsewhere it aims at the local view (visual only). Never the local-hunter fallback.
- Wobble (sub 0 / 1): 4U reads a global u16 (G); the port uses a per-shell LCG seeded from the action serial and the
  shell index so all machines draw the same path (behaviour-equivalent, MP-safe).
- Test (memory: two local Ryujinx instances over LDN): log per post `serial, action, rank, charged, target index, sub`
  on both and compare; log each shell's end reason and age.

## 5. Risks and open questions
| mark | item |
|---|---|
| C | m10612 loads GU Zinogre and Stygian together: GU rows 247 / 248 and GU's family files must stay GU's (decision 2b.2) |
| C | 4U orb life <= 99 frames; GU raised its own Zinogre orb to 9999. Keep 99 (faithful); confirm in game (question 2) |
| S | orb step-2 block (0x84cd60..0x84d23c) not transcribed; the step-1 scheme is C |
| S | vt170 k -> 4U vt77 case: match the 7 (motion, frame) pairs before wiring |
| S | GU twins: 0x92c960 -> 0xc2f88 (apimap2, 2 / 2 votes); 0x91f8bc (same area, state +0x371 != 8, 0x6832c8) has none: translate it with GU's hunter fields; hunter position = the twin of [t+0xe30]+0x10 (base position, not a joint) |
| S | uShell044 origin = owner +224 (base position vector); check that GU's equivalent (rec position) gives the same point |
| S | element / status bytes: Stygian vs Zinogre differ only in +0x0c (0x21 / 0x41) and +0x10 (0x80 / 0x40): dragon / dragonblight vs thunder / thunderblight (Tigerstripe's paralysis +0x10 = 4 fits); copied as 4U bytes, so the meaning is not needed for fidelity |
| S | +0x2c (level) of the blasts: GU's twins hold 2 where the em089 rule gives 0 -> delta-patch GU's entries (not the rule) |
| G | arc axis *0x10e63a8 (bss MT constant): lateral or vertical arcs; read it in step 1 |
| G | wobble source u16 [*0xfb6b7c]+0x22 (random or counter); find its writer |
| G | 4U effect material variant (+0x18) -> GU: unknown (em049_003, em049_022) |
| S | effect controller ids 0x3ec / 0x3ed resolve in a file Stygian shares with GU Zinogre: today v1 shows a Zinogre effect on charge changes |
| S | GU class code may still pick GU-only actions from the appended scripts (plan.md B6) whose handlers post GU Zinogre kinds for v1 (f00684 kind 12, efd9ac kind 13): watch the log for 7/166-169, 7/251 252 |
| G | the 4U arm flags (23, 2), (7, 2), (31, 2) -> GU slot 80 (a, b) unchanged (dala mapping, S there) |
| S | `sz_shell044`'s grp / b8 / f arguments: grp 0xffff, b8 0, f 0.0 at every Stygian site; unused by subtype 3 (no read of +0x26c / +0x26e in the sub-1/3 paths seen) |

## 6. Implementation plan (one helper at a time; each step builds clean)
| # | step | size | test alone |
|---|---|---|---|
| 1 | Extract the static-init vectors (orb tables, 0xfeba98 / 0xfebb28 / 0xfebbb8, 0x10e6378..) with a unicorn run of the 4U inits; bake into em057_01_shelldata.h with asserts | tool ~150 lines + header | offline: values plausible, 0xfeba98 == GU 0x2132a50 at run time (log once) |
| 2 | Family, def file ID, HDS / HTS (asserts on GU's three entries and the deltas) in build_em057_01_arc.py | ~150 lines | offline build |
| 3 | PEL list-2 records for the eight EFLs + sound-id asserts | ~60 lines | offline; in game via step 4 |
| 4 | Framework copy (em057_01_shell.c) + blast class (dala_shell003.c default path, subtypes 135 / 236) + `sz_shell003` posts | ~250 + 150 | first test: 7/190 191, 7/220, 7/217 218 (G-rank lead-ins): em049_022 blast and a hit at each slam |
| 5 | Pillar class + posts: 7/113 115 (stub), 1/6.. (ef4484 hook), 2/40 (scheduler) | ~200 | charge stance / walk / transition: gather -> burst at frame 50, hit frames 50..60 |
| 6 | Orb class (5 phases, homing, y rule, wobble LCG, collisions, effects, sounds, 99-frame window) | ~500 | with step 7 |
| 7 | Orb volleys: efa930 entry + 2 mid hooks (4U 0x84c6b0.. / 0x84cd60.. Stygian branches) | ~200 | HR quest: sub 0 orbs (1 / 2 by charge); G quest: 3 + 2 homing |
| 8 | vt170 orbs: 7 mid hooks + case table (G rank only) | ~80 | G quest: hovering orbs that fly to the spawn-time position |
| 9 | Effects: eefda4 for v1 (em049_002 / 005 + 210 / 213); vt77 em049_003 + 205 (after the variant question); radial blur stays a logged deviation unless the user asks | ~100 | charge on / off, knockdown uncharge |
| 10 | MP: two-instance LDN run with the post / end logs of 4 | - | compare logs |

## 7. Questions for the user (gameplay the code does not settle)
1. High Rank: do Stygian's orbs rise and then jitter along a fixed curve without aiming at you, while in G Rank they
   rise, stop, and shoot straight at you (when charged one aimed a bit past you and one at you)? Do G-rank orbs also
   appear in other moves, hover about a second, then fly to where you stood when they appeared?
2. Do orbs that miss burst on the ground, or can they vanish in mid-air after about 3 s?
3. Charged = two orbs per volley, uncharged = one: does that match your memory?
4. Charge walk and charge stance: are there red pillars striking around him (they hit about 1.7 s after the red glow
   appears), and a ring of them when he becomes fully charged?
5. Paw slams (the double slam and the G-rank combos): a red dragon blast under the paw at each impact?
6. Roar radial blur: 4U blurs the screen on roars; GU has no calibrated blur (Gogmazios and Dalamadur ship without it).
   Keep it as a listed deviation, or worth a research step?

### 7b. User's answers (2026-10-28; the plan is approved: "Continue on the port")
1. Orbs: "they stop then shoot at you"; HR vs G difference not remembered (the code decides).
2. Missed orbs: "pretty sure they always burst into the ground" (4U: no effect when the 99-frame window runs out
   first, C; the flight times decide whether that ever shows: check in step 6 / test).
3. Volley: 1 uncharged then 2 charged, or 2 then 3: not remembered (the code decides: 1 / 2 in the HR tables, C).
4. Pillars: yes, exactly: the red pillars are dragon bugs that explode, like the orbs.
5. Slams: the red blast under the paw shows "when charged". No charged test in the four 4U slam handlers before their
   post (C: 0x84f900 0x850164 0x8508fc 0x852968; 0x84f744's two 0x90f90c calls at 0x84fa70 / 0x84fb2c set the speed).
   Step 4 must trace where the charge gates it: uShell003 init / effect table (0x101dfcc mask?) or the AI picking
   these slams only when charged; if 4U posts it uncharged too, report before deviating.
6. Roar blur: research it (step 9: find GU's radial blur filter or an equivalent, then decide with the user).

## 8. Step-4 review (2026-10-28; user: Dalamadur's shells have issues, issue #6, "do not straight up copy them")
### 8a. The charged paw blast (answer 5): found, no deviation (C)
- The uShell003 135 / 236 effect has no charge gate: 0xc5540c posts (58, 27) em049_022 with table 0x101dfcc mask -1,
  sound kind 2 id 226, scale 1.0 for 129 / 135 / 235 / 236 alike; 7/186 / 187 chain to 7/190 / 191 on the timer only
  (0x84f6c4, no 0x90f90c). So the shell blast shows on every 7/190 191 217 218 220 slam, charged or not.
- The red blast is vt77 0x8582b0: motion 0x201 / 0x202 (0x857f68), category 7 except 190 / 191, atFrame(57.0)
  (literal 0x858630), joint 50 for 0x202 else 40, ground ray y + 100 .. (0x858634 = 100.0), basis to the ground normal,
  then 0xc08628 (58, 12) = em049_003 with request mask (+0x10) 2 and sound 205 at the point (0x858410) when charged
  (0x90f90c), mask 1 when not; r5 = 2 from 0x857f40 (the only r5 writes in 0x857ba8: 0x857bfc / 0x857c0c pointer,
  0x857f40, 0x858134 on another case): record 3253's S is now C. These are the plain paw slams 7/2 3 6 7 16 68 69
  188 189 (0x848310, motions 0x201 / 0x202; charged they also take attack rows 55 / 56 instead of 4 / 7).
  em049_003's elements (C): 0-2 element mask 3 ground 0x22, 3-6 mask 3 ground 0x54, 7-10 mask 3 ground 0x8, 11-14
  mask 2 ground all: elements 11-14 appear only charged = the red blast the user remembers.
### 8b. Ground variants: a shared converter gap (C unless marked)
- 4U: 0xc07440 copies request +0x18 (ground kind, 0xc094e8 for the slams) to effect +0x239 and turns it into flags
  (2 << kind) | 1 (jump table 0xc074c8: kinds 0..5 -> 2 / 4 / 8 / 16 / 32 / 64), passed with the element mask to
  0xafd76c (effect +0x1c8 mask, +0x1cc flags). The build keeps an EFL element only when (mask & element word 0) and
  (flags & element word 4) (predicate 0xafc574..0xafc5ec). So one EFL holds a set per ground: em049_003 / em049_019,
  qe006_000 / 001 / 003 / 005 / 007, em048_006 / 008 / 014 / 021, em049_007 / 012 / 018 (normal 0x22 = kinds 0 / 4,
  water / poison 0x54 or 0x14, lava 0x8).
- GU: the same element words (our converted EFLs keep them; GU's own cm202 / em057_00_003 use them too, plus GU-only
  bits 0x80 / 0x100). The PEL record holds the flags at +0x4c next to the element mask +0x48: GU bakes 0x22 into its
  Zinogre slam records 210 / 211 / 220 / 221 (em057_00_003) and 0x7e into 290 (em057_00_007); its code records 150 /
  905 keep 0xffffffff. The request body mirrors the record (0x31beb4 defaults: +0x58 mask -1, +0x5c flags -1) and a
  code post overrides per field: req+0x14 bit 18 -> element mask req+0x68, bit 19 -> flags req+0x6c (0x179d90..
  0x179dec, GU's own post helper, then 0x40978).
- Ours: efl4u2gu.PEL_TAIL writes +0x4c = 0xffffffff into every converted record and no module post sets bit 19. A
  code post with that record and no override draws every ground set at once (dust + water / poison splash + lava).
  Gogmazios' 3100 (qe006_000: 0x22 / 0x14 / 0x54 / 0x8 / 0x8) is such a post: the likely cause of issue #6 Gogmazios
  3 ("snow debris" on both arm slams) (S, test needed). Stygian's code records 3203 / 3253 (em049_003) and 3219
  (em049_019) are in the same case; 28 motion records (list 1) carry 0xffffffff too, but test 3 showed no extra
  splashes, so motion posts likely get the ground from the engine (S, not traced).
- GU has no twin of 0xc094e8's bit tests (scan: no function with tst 0x800000 / 0x200 / 6 / 0x1040 / 8): the surface
  class of a GU hit stays 4U's rule on GU's attribute word (S, as sz_effect_c094e8).
### 8c. Other issue-#6 items checked for step 4
- Dust colour: 4U tints mode-5 units by the stage's ground colour (+0x239 picks soil / water / lava / poison / vines);
  GU has no tint; our arc bakes the 4U Arena soil (176, 146, 107) (arena_soil, known deviation).
- Placement: GU's own Zinogre slams post the blast as a GU shell at the ground point with the monster's angles (f00684
  0xf00a70, efd9ac 0xefddf4: the ground basis is computed but the request takes this+0xfe8). Dalamadur's "charging at
  the wrong location" comes from its motion-effect lists / shell spawn points (Dalamadur-specific, not traced).
- Collision mask: Dalamadur's burn passes 16 to 0x1838fc like 22 of GU's own shell calls (others 32 / 48 / 2): not
  the cause of its missing burns (a log is needed).
- Textures: the last arc build logged no MISSING resource for any EFL (C).
- Row id param+4: GU base code reads it (0x4a1b38) only for ids 22 / 26 / 41 / 42 / 48-51 (player / enemy hit code)
  and in each GU shell class's own methods (0xf084d0: 247 / 249 = uShellEm057's): 247 or 175 behave alike for our class.
### 8d. Step 4 as built (2026-10-28, user "Go ahead"; test 4 installed 14:59)
- 4U uShell003 135 / 236 (C, read for this step): message 3 fields -> ctor 0xc55b10 (+0xf3 = 1 when a rotation is
  passed: the slam passes the ground-turned euler); init default path: arm (31, 2), effect 0xc5540c em049_022 with
  flags 256 (no player-area gate), ground kind +0x274, rotation +0x278, scale 1.0; sound 226 kind 2 at the position
  (0x312484); 0xc55034 nothing (flags 0); per frame: age += dt, end when the slot's active byte is 0 or age 200; kill:
  base kill + 0xc470dc (a one-shot effect is asked to finish, mode 1 only is cut).
- em057_01_shell.c: own GU uShellEnemy base (class copy of uShellEnemy's vtable + DTI, GU's request tail, arm through
  slot 80) and the blast class; param as GU's own slam (row this+0xcafc, kind 12 / 13, position, the monster's
  angles, hit group). GU's arm sets the slot's active byte at once (0x168ec0), so 4U's end test works from the first
  frame; a logged guard ends a shell whose slot is still active 2 frames after the window.
- Effects (em057_01_efx.c sz_efx_world): point posts through 0x53b500 (not 0x6ff74, which attaches every post to the
  monster's model: its scale and frame), rotation override (degrees, req+0x14 bit 1), ground override (bit 19,
  (2 << kind) | 1). The blast's effect is asked to finish at the shell's kill (0x32a400 mode 0 = 4U's release).
- vt77 em049_003 (em057_01_slam_fx_frame, every frame from the slot-125 hook): motions 0x201 / 0x202, category 7 except
  190 / 191, frame 57, ground under joint 50 / 40; charged: sound 205 + mask 2 (record 3253), else mask 1 (3203); only
  in the local player's area (4U request flags 0).
- Logs: "blast N sub .. at .. rot .. kind .. group .. hit .. efx ..", "blast N effect placed at (asked)", "blast N end
  at age ..: reason", "slam hit fx 7/n motion .. frame 57 [charged] ground kind ..", "slam hit fx placed at (asked)",
  "c094e8 flags .. -> ground kind ..". Placement read back from the effect's transform node +0x40 (0x32a45c).
- Open for the test: GU's ground kind on this quest's stage (4U's bit rule, S on GU stages), whether GU's mode-0 stop
  at frame 10 shortens the blast compared with 4U, the rotation order on slopes (flat ground: yaw only).
- Test 4 showed no slam: Stygian's AI picks paw slams only at quest rank >= 5 (the charged 7/14 lead-in from 4), and
  his HR quests are rank 3 in 4U and GU (C for the gate, em057_01_ai.c header; plan.md test 4). Slam tests need a G
  quest or the test switch TEST_QUEST_RANK=5 (test 5).

### 8e. Test 5: the point posts were drawn away from the point (2026-10-28)
- Log 15-34-45: 5 blasts (7/190 191 at G rank), 7 vt77 ground hits (7/6 7 160 164), all posted, no crash; every
  read-back "placed at 0 0 0" (read in the post's frame). User: the red blast is "visually far from the paw impact on
  the ground", for every charge state; "shifted, towards the left of his body. But unsure"; "parts never show".
- Point and joints are right (C): jointPos 0xc1708 -> 0x53ab30 looks the joint up by bone ID (this+0x498 map -> joint
  array +0x494, position +0x40), as 4U 0x93093c (0xb054ac); our model keeps 4U's IDs: 40 / 50 = the left / right
  front paw tips (bind pose (+-103, -321, 244), ground about -330).
- The effect side (C): 0x40978 copies the request body (req+0x10..) to effect +0x80 (0x329308 -> 0x31c280). The unit
  setup (slot 32 0x32aa44) attaches the root node to the target in transform modes 0-2 (skipped without a target,
  r5+0xf0 = 0) and copies a world position (r5+0xe0) into node +0x40 in modes 3 / 4. Mode from the record (0x32a548):
  +0x36 4 -> 0, 1 -> 2, 0 -> (+0x38 == 1 ? 1 : 0), else (+0x3e == 6 ? 3 : 4). PEL_TAIL (+0x36 1 = mode 2) is an
  attach tail: Gogmazios' / Dalamadur's world posts work with it because 0x6ff74 adds the monster as target (flags
  1 | 2, hence its 2.5x scale); GU's shells pass their own attach model (0x4a1d34: flags 3, target vt+0x130(shell),
  position shell +0x40, scale from the def by req+0x14 bit 30). sz_efx_world posts with no target (S: drawn where
  the node starts, not at the point).
- GU's own joint -1 code posts: 298 em PEL u list-2 records carry +0x36 3, almost all with +0x3e 6 = mode 3; the most
  common tail (44: em001_00u 31..34 ...) = PEL_TAIL_PREV with +0x36 3, +0x38 2, +0x39 1, +0x3a 0. Fix: efl4u2gu
  PEL_TAIL_WORLD (record key world, opt-in; no other builder sets it) for Stygian's joint -1 placed-once records
  (3203 3253 3217 3267 3219 3220 3222), asserted against GU's record 31 in the build. Read-backs moved to after the
  unit build (blast: shell age 3; vt77: 4 frames on).
- Not changed: the blast's finish at the shell's end (4U 0xc470dc finishes it too, its end mode 0 / 2 -> vt+0x70;
  GU 0x32a400 mode 0 -> slot 39 0x32a034 stops the unit nodes, state 2). GU's base shell kill 0x4a247c stops no
  effect. "Parts never show" may follow from the placement (the Stygian model ef_em049 renders in the auras); if it
  stays after test 6: element timing vs the finish, or 4U posts not yet ported (the bugs).
- 0x32a45c = set position of the unit nodes (+0x150 / +0x154, +0x40), 0x32a4c4 = set rotation (x constant ->
  0x8a7dc4): used by shells that move their effects (27 / 23 callers), not by the post.
- Test 6 (log 16-07-24, user: "All good"): 5 vt77 hits and 4 blasts, every read-back "placed at" = "asked" (C):
  the world tail fixed the placement; no part reported missing.

### 8f. Step 5 as built: the dragon pillars (2026-10-28)
- 4U uShell044 subtype 3 read in full (C; em057_01_shell.c pillar section): ctor 0xc8835c (position = offset + owner
  +0xe0, the uCoord world-matrix translation), init 0xc87f10 (gather em049_020 posted on the shell, arm (7, 2) with
  record 3, sound 217; the state is 1 after the init even when the effect post failed), per frame 0x9a9a3c case
  0x9aa458 (column end +2000 every frame; once, when the slot's start delay reaches 0: burst em049_019 at the position
  + sound 218, the gather effect released); ends: owner gone / leaving, slot inactive (frame 60), age 400, gather
  effect gone; kill = the base kill. Request defaults 0xc0ca90 (C): ground kind +0x18 = 0, mask +0x10 = -1.
- GU (C): the slot's start delay = slot +0x5c (4U +84: arms 0x168ee0 / 0xb7014c), counted down by 0x169260 as 4U
  0xb70024, then the length, then the active byte cleared; grp 0xffff keeps the arm's own hit group (0x4a2884, as 4U:
  each pillar hits on its own); the base set-up 0x4a24f8 loads the def's PEL lists and posts nothing by kind, so GU's
  pillar kind 0 goes in the param (GU's 7/113 post efb884 passes kind and grp 0xffff the same way).
- Posts: 7/113 115 (em057_01_mv_f.c, the stub replaced) and three mid hooks inside GU's handlers, which kept 4U's
  frame loops without their posts (C): 0xef4484 (1/6.. step 1 with r1 == 0, before GU's `variant == 1` loop; table
  0xfeba98), 0xef6450 / 0xef6338 (2/40 = ef62e4(1), steps 1 / 2; tables 0xfebb28 / 0xfebbb8; r1 == 1 tested, no em
  test in 4U). This replaces the design's slot-125 scheduler (2c): the 4U loop now runs at its own place in the
  handler (C instead of S).
- Effects: world posts at the position (3220 gather, finished at the burst and at the kill; 3219 burst with ground
  flags 3 = the request's kind 0). em049_020's elements all carry ground mask ffffffff (the owner's ground kind 4U
  passes picks nothing, not passed); em049_019's elements 3 / 4 carry 0x22 (kept by kind 0). Sounds 217 / 218 follow
  the shell (GU 0x4efe58, called as GU's own shells call it, 0x400e7c).
- Deviation-free except: 4U's init tail-calls the first per-frame (its effects before the window: the column end, set
  in the set-up here, and one dt of age; the 400 limit is never reached); a guard ends a pillar whose slot is still
  active 10 frames after the window (logged).
- Module 953132 bytes with TEST_HP_PCT=50 TEST_QUEST_RANK=5, 0 warnings; trampolines displace GU's pairs (movw / ldrb,
  cmp / movw x2). Logs: "pillar N sub 3 at x y z (4U site) area .. hit .. efx ..", "pillar N burst at age ..: efx ..",
  "pillar N end at age ..: reason" (120 lines).
- For the test: charge stance (1/6..: 5 pillars at frames 64 / 128 / 182), charge walk (2/40: 5 + 3), charge
  transition (7/113 115: 12 around him); gather glow then a burst at frame 50, the hit from frame 50 to 60. The base
  sits at the monster's height (4U adds the offset to his position, y offset 0): on slopes the column starts above or
  below the ground, as in 4U.

### 8g. Steps 6 and 7 as built: the dragon orbs and their volleys (2026-10-28; user: "Continue to the orbs first")
- 4U uShell046 read in full (C; em057_01_shell046.c header): message 46 layout (poster 0x6629bc), ctor 0xc8a754
  (position / A / B = origin + Ry Rx Rz(angles) * record vector; wobble velocity starts at (f5, 0, 0); the target of
  subtypes 2-4 with the y rule), init 0xc89184, per frame 0xc892f0 with the three subtype paths, the leg helper
  0xc8a1fc, the move 0xc8a4ec (path, sine arc in phase 3, wobble offset turned by the flight angles), the wobble
  0xc8a334, the collision 0xc8a288 (hit byte, else the map segment from the position to the capsule end, mask 48).
- Corrections to section 1a (C): (1) the per-frame sets the slot's window length (+448) to 100 every frame, so no
  99-frame life: an orb ends at its age limit f2 (em049_017 mask 2), at an impact (hit byte or map: em049_017 mask 1 +
  sound 216) or when its flight effect dies; (2) the wobble reads u16 [*0xfb6b7c + 0x22] twice in the same frame: the
  re-aim needs it below 4096, so its bit 13 is clear and the turn is always -4096 (-22.5 deg); the u16's writers are
  state copies (0xc27830 / 0xc2789c, 0xc1d8fc) and a save / restore around 0x2f4c5c (G: what it is), so the port draws
  only the 1-in-16 chance, from a per-orb LCG seeded with the action serial and the orb's record index (the same on
  every machine); (3) the arc axis is (cos yaw, 0, -sin yaw) of the B leg, horizontal, to its side.
- GU twins (C unless marked): target = 0xc2eb4 (4U 0x92c960, the same 255 / mask 10 / index rules + uPlayer test);
  4U 0x91f8bc as GU translated it inline (0xc29a4..0xc29c8 vs 4U 0x92cfac..): present (0x49240(pl+0x1051) == 0, for
  4U 0x6832c8) and in the monster's area (pl+0x1054); 4U's player state-8 test is absent there and left out (S); the
  hunter's position pl+0x40; map segment 0x1838fc / flags 0x4a2a8c; the slot's hit byte +6 (slot ctors 0x1685cc /
  0xb70428 set 255) and window length +0x60. GU's volley step 0 copies the angle triple to work +0x44..0x4c
  (0xefb044, as 4U 0x84c51c): the posts read it there.
- Posts (em057_01_posts.c; the pillar frame-table hooks moved here from em057_01_shell.c): entry hook 0xefa930 keeps
  the 4U parameters (r1-r3 and the caller's [sp]: GU keeps r2 / [sp] in r6 / r9, out of a mid hook's reach); mid hooks
  0xefaa6c (frame 88, step 1) and 0xefaab4 (frame 58, step 2), where GU posts its own orb for variant 0 and nothing
  for 1. The volley rule (both 4U blocks read in full): k = 0 when r2 is 0 / 1, else 1; index 0 (step 1) / 2 (step 2);
  uncharged 1 orb, charged 2 (index + 1); homing ([sp] == 5 or quest rank >= 5): subtype 2, or 3 + 2; else 0. Records
  by rank (0x856900, literals 0x856a2c..0x856a3c).
- Effects: flight em049_015 (record 3215, k 0) posted ON the orb (em057_01_efx.c sz_efx_on: GU shells' own request
  style from Gogmazios' em089_efx.c, attach model vt+0x130 + position + unit + area), finished at the kill (S: 4U's is
  attached and ends with the shell); expiry / impact em049_017 (3267 / 3217) as world posts. No ground variants in
  em049_015 / 017 (C). Sounds: 215 every 22 frames and 224 at the B leg on the orb (GU 0x4efe58), 216 at the impact
  point (GU 0x4efb98).
- Framework: em057_01_shell.h now exports the shell framework (sz_cls_register / new / free, sz_shell_param / start /
  arm / live, sz_snd_obj) to em057_01_shell.c (blast, pillar), em057_01_shell046.c (orb) and em057_01_posts.c.
- Module 965412 bytes (TEST_HP_PCT=50 TEST_QUEST_RANK=5), 0 warnings; trampolines: efa930 push / vpush, the two
  movw / ldrb pairs. Logs: "orb volley a/b (p1, p2, p3, p4) step s (4U ..): rank .. charged .. record (k, i) sub ..",
  "orb N sub S at .. A .. B .. f .. target i (kind k) hit .. efx ..", "orb N leg to B ..", "orb N impact: attack
  connected / map (r) at ..", "orb N expired ..", "orb N end at age ..: reason".
- Step 8 (user: "Continue first"), the vt77 orbs: 4U vt77's motion tree (0x857f2c.., read in full) calls 0x855fe4(k)
  for Stygian at (motion, frame, k): 0x20f 117 0, 0x212 117 1, 0x218 6 2, 0x21a 72 3, 0x21e 89 4, 0x226 81 5, 0x225
  81 6 (C). GU's vt170 ef27b0 did not keep this numbering (its k 5 at frame 89, k 6 at 138, k 1 for variant 0 only)
  and posts nothing for variant 1, so instead of the design's 7 mid hooks the 4U table runs every frame from the
  slot-125 hook (em057_01_posts.c em057_01_orb_event_frame, as the paw-slam ground hit of the same vt77). 0x855fe4
  (C): rank >= 5 only; record pairs of the vt77 table (kind 2) 0 (2, 3), 1 (0, 1), 2 (4, 5), 3 (6, 7), 4 (8, 9), 5 =
  0, 6 = 1; A.y += 300; the angle triple copied to work+68 now; charged both as subtype 4, else the first. The
  charged-only sounds 204 / 208 / 222 of those branches are left to the sounds batch. Module with steps 5-8: 967464
  bytes (test defines), 0 warnings. Log: "orb event k .. (4U ..) a/b motion ..: rank .. charged .. records (2, i)".

### 8h. Step 9: effects and the roar blur research (2026-10-28)
- Already in place (C): the charge-change effect and sound of 4U 0x856f0c (em049_002 / 005 + 210 / 213) through the
  effect gateway since test 1 (em057_01_efx.c ids 1004 / 1005), the vt77 paw-slam ground hit since step 4.
- Roar radial blur (user 7b.6: research it, then decide together). Builds on Gogmazios' rounds 4-5 (its
  port-checklist.md, "Roar radial blur"): 4U 0xc0819c makes a uMhRadialBlurFilter (3DS fixed-function, a code ramp 0
  -> 0.035 -> 0.025 -> 0 over 74 frames centred on the joint, line 20, local player's area only). GU's DTI registry
  holds the framework's uRadialBlurFilter (DTI 0x21209b4, shader, properties mBlurStart / mBlurWidth / mSamples /
  mCenter / mWPos...; newInstance 0x8b8a9c) and no MH radial subclass. New this round (C): every GU code reference
  to the filter DTIs is a DTI registration, a getter thunk, a newInstance or the draw (uRadialBlurFilter 0x8b8aa4
  0x8b904c 0x8ea2b0 0x8ea60c; uMhFilter 0x696ba8.. its newInstance); the game only finds data-placed filters by name
  (the stage controller 0x505b9c..0x505bf8: 0x9680bc(scheduler, DTI, name)). So GU never creates a filter from code:
  a code-made blur needs the untraced draw registration and a guessed 4U -> GU strength mapping.
- User 2026-10-28: "Keep it as deviation" (sz_effect_c0819c stays a logged stub, as Gogmazios / Dalamadur). And: the
  roar's effect must move with the head as in 4U; "right now it's spawned on the ground for all ported monsters".
- Roar effect (C unless marked): 4U's motion-effect post 0x391b50 copies the MEF record flags into the effect (+0x274
  bits, 0xc4800c(flag bit 0) -> 0xafeeb8 sets every unit's local-space bit), and the effect's slot 6 (0xc481f8 ->
  0xc4838c, the per-frame slot by alignment with the shell vtables, S) takes the record's joint world position as the
  base every frame (0xc499a4..); only MEF flag bit 1 (-> +0x274 bit 0) puts y on the owner's ground (0xc49a84..). So a
  joint record without bit 1 rides its joint: Stygian's roar records 1000 / 1001 / 1002 / 1004 / 1005 (qe013_000 /
  001, qe008_000, qe000_001, qe008_004 on joint 3, flags 0x281 / 0x280). Ours: tools/efl4u2gu.py writes PEL_TAIL
  (transform mode 2: placed where posted) into every motion record. GU's own joint-attached motion records mostly
  use mode 0 (+0x36 0: 475 of ~1000 joint records over GU's em PELs, scratch meftail2 / peltails), the mode
  Gogmazios' moving shells already use (PEL_TAIL_PREV, they follow their unit). A cross-game flag -> mode table from
  Capcom's conversions is too noisy to use (as Gogmazios' notes found); Zinogre's own 0x225 joint records became mode
  1, its 0x226 world record mode 2. Changing it touches every ported monster's motion records (joint records without
  the ground flag: Gogmazios 20, Dalamadur 49, Shah 30, Tigerstripe 32, Stygian 22 + 8): plan sent to the user.
- User: "4U rule, all joint effects". Built (tools/efl4u2gu.py mef_follows, pel_record(motion=True) for PEL list 1
  only, the list-2 copies of Gogmazios / Dalamadur byte-identical): a MEF record on a joint without the ground flag
  takes PEL_TAIL_LOCAL (Capcom's tail of Zinogre's em048_004 joint records 560 / 561, 4U flags 0x225: mode 1;
  asserted against GU em057_00u by build_em057_01_arc.py) when its local-space flag (bit 0) is set, else PEL_TAIL_PREV
  (mode 0, GU's most common joint motion tail); ground-flag and joint -1 records keep PEL_TAIL. Stygian's roars 1000 /
  1001 / 1002 / 1005 (0x281) -> local, 1004 (0x280) -> follow. Rebuilt all ports' arcs, diffed against the previous
  builds (scratch peldiff.py): only PEL list-1 tails changed (Stygian 30 records: 18 local + 12 follow; Gogmazios 20:
  6 + 14; Tigerstripe 32: 22 + 10; Dalamadur 52 and 58, Shah the same PELs), every other arc entry and list 2
  identical; all seven data files re-pack identical to the installed ones. To test: each monster's roar rides the
  head; the paw / foot dust still stays on the ground.
- For the test (G rank forced): 7/32-34 61-63 66 87 211 212: one orb per post uncharged, two charged, two posts per
  action (frames 88 / 58); at G rank they rise to A, then fly at the target hunter (subtype 3 aims 600 past him).
