# Stygian Zinogre: 4U em==49 sites vs GU uEm057_00 variant 1 (static RE, 2026-10-28)

4U = MH4U v1.1 code (`dump/mh4u.asm`), class uEm048 (em 48 Zinogre, 49 Stygian, 114 = third "Zinogre", shares every em48
path), code 0x841390..0x85a2c4 (C: cat-3 handlers start at 0x8413f4, uEm050 code at 0x85a2c4), vtable 0xe68464,
W = `[this+0xe28]`, work = `[this+0x8d88]`, em byte W+0x1c0, action W+0x1ca / W+0x1cb.
GU = MHGU 1.4 main, class uEm057_00 (0xeee870..0xf09734), vtable 0x17d19bc, variant byte `this+0xb5f5`, action
`this+0x73e0` / `this+0x73e1`, rec = `[this+0x1428]`, work = `[this+0xcac0]`.
Confidence: **C** confirmed in code/data, **S** strong, **G** guess. "not verified" = check incomplete.
Scratch scripts (not in the repo): /tmp/claude-1000/-home-scrimas-Projects-MH4U-MHGU-port/f1f458ee-797d-4e55-beaf-a811c32a8ba2/scratchpad/p1/
`u48.py` / `g57.py` (class listings), `emflow.py` (4U em-byte CFG dataflow), `gvar.py` (GU variant reads incl. pointer
forms), `site4.py` / `siteg.py` (em48 vs em49 / variant 0-1-4 path summaries), `case.py` (dispatcher emulation, both
games, r1..r3 / [sp] / s0-s1 params), `pair.py` / `actmap.py` (4U handler -> GU handler by motion + attack sets),
`scanem.py` (whole-exe em-byte scan).

## 0. Method and counts

Method (Tigerstripe model): every load of W+0x1c0 in the class, followed by CFG may-dataflow (copies, stack spills, both
branch directions) to every compare; em 48 and em 49 emulated through the compare chain to the two paths; the em49 path
summarised (calls with constant args, conditional stores). GU: every read of this+0xb5f5 (direct `ldrb [rT, rY]` with
`movw rY,#0xb5f5`, pre-index writeback, post-index `ldr [rP], rY`, `add rP, rT, rY`, conditional `ldrbeq [rP]`), same
dataflow, ladder emulated for variant 0 / 1 / 4. 4U function -> GU function by vtable slot or by motion + attack-index
sets (`pair.py`), checked by reading both listings.

**4U class (C):** 85 loads of W+0x1c0:
- 7 `cmp #49`: 84328c 8432f4 844f14 845190 8453b4 8468c4 847098.
- 63 `cmp #48; cmpne #114` (or `cmp #114; cmpne #48`): Stygian takes the other branch. The earlier "64" = these 63 +
  8566cc (`cmp #48` alone).
- 8566cc `cmp #48` only, 856ea0 `cmp #114` only.
- 13 dead loads (the em byte loaded into r1 and overwritten by a sound id: inlined sound calls): 8481c4 84db88 84df18
  84e224 84f590 857000 8584f8 858548 8585d4 8586cc 8587a0 858920 858998. No em test.
- **Under-counted (dataflow): 857758 / 857760** (`cmp r1,#48 / #114` on the byte loaded at 8570a8, vt47 10/112):
  Stygian-specific. 84c738 and 84cde8 (`cmp #114` on the byte loaded at 84c6a0 / 84cd50): em114 vs em48 only.
- No em-indexed table and no em getter in the class (C: no non-compare use of the byte except the dead loads).
- **Dispatcher:** slot 44 resolves every (cat, num) of 0..17 x 0..255 to the same handler and params for em 48 and 49
  except **10/110** (reaction table passed to 0x9197c0) (C, `case.py` emulation).

**Stygian-specific 4U sites: 68** = 7 + 60 pairs + 857758 (3 pairs are not Stygian-reachable or shared, section 1F).
**Verdicts: MATCHED 10, DIFFERENT 23, MISSING 33, UNRESOLVED 2.** Plus 6 sites in shared 4U code (section 3).

**GU class: 208 reads of the variant byte** (137 direct `movw #0xb5f5` + 71 pointer / conditional forms) (C for the
forms scanned; exhaustiveness S):
| test | reads | what variant 1 does |
|---|---|---|
| `== 4` only | 151 | Thunderlord-only code; variant 1 follows variant 0 (Zinogre) |
| ladder `== 4` / `== 0` / else | 17 | 13 charged-attack-index ladders: v1 = default = **uncharged Zinogre index, charge ignored**; 4 orb posts: v1 = **nothing** |
| `(v \| 4) == 4` (v in {0,4}) | 8 | v1 takes the 4U-Stygian branch (vt129 table row, vt119 skip) or returns (vt170) |
| `== 1` | 9 | **4U Stygian leftovers** (all 9, section 2) |
| `== 0` | 6 | v1 treated like v4 (none reaches Thunderlord code) |
| stored as an argument | 17 | orb helpers f03708 (x6) / f04260 (x11); reached only for v0 / v4 |
The quick scan's lists (register not checked) had 4 false hits: ef5a04 and ef62f0 compare the r1 parameter, ef9d0c an
atFrame result, eefefc / ef16bc a call result (C).

## 1. Groups (4U site -> GU)

### A. Charge walk, move-class flag, charge sounds (cmp #49) - 6 MATCHED, 1 DIFFERENT
4U this+0xca8 is a flag word set per move (`orr #2/4/8/16/32/128/512`); GU stores the same information as an enum byte
this+0xb5f8 (4U bit 1 -> 1, bit 2 -> 2, bit 3 -> 3, bit 4 -> 4, bit 5 -> 5: C on 13 handler pairs), read by GU vt79
f05914 (motion-range collision flags this+0x13f4; meaning G).
| 4U site (fn, actions) | 4U em49 | GU | verdict |
|---|---|---|---|
| 84328c (0x843264 r1=v, 2/38 2/39 v=1; 2/5 2/6 v=0), every frame | v==1: this+0xca8 \|= 4 | ef59ec ef5a04: r1==1 && variant==1 -> this+0xb5f8 = 2 | MATCHED C |
| 8432f4 (same, step 1) | v==1: motionCheck(3, 28, 140): timer W+468 -> 48 + sndJoint 207; timer work+44 -> 70 + sndJoint 209 | ef5ae8: same window, rec+0x1bc -> 48.0, work+0x2c -> 70.0; **no sound** (GU class posts no sound at all, 0 calls to 0x4efd74/.. vs 32 in 4U) | MATCHED C (sounds: data side) |
| 844f14 (0x844f00, 2/41 2/42 r1=1; 2/16 2/17 r1=0) | r1==1: \|= 4 | 2/41, 2/42 inline in ef7990: ef7ee0 / ef7f40 variant==1 -> b5f8 = 2 (2/16, 2/17 = GU END) | MATCHED C |
| 845190 (0x84516c, 2/21 r1=0, 2/40 r1=1) | r1==1: \|= 4 | ef62e4 ef62f0: r1==1 && variant==1 -> b5f8 = 2 | MATCHED C |
| 8453b4 (same, walk loop, any r1) | motionCheck(3, 21, 266): timers 48 / 70 + snd 207 / 209 | ef64ac: variant==1, same window and timers, no sound | MATCHED C |
| 8468c4 (vt40 0x846738, uncharged, in 7/85 198 203 206 210) | skip W+0x7844 = 2 | vt119 ef24c8 ef26ec: same action list, variant==1 skips rec+0x5d34 = 2 | MATCHED C |
| 847098 (0x846ec4 r1/r2, 1/6 15 16 17 28-33) | frame table 0xfeba98 (24-B rows: frame, x, y, z): at each frame post **uShell044 subtype 3** (0x662904) at a yaw-rotated offset | ef4280 ef4488: variant==1 runs the same frame loop (32-B rows) calling only atFrame, **post removed** | DIFFERENT C |
- 1/6 15-17 28-33 are the **charge** actions: their action start (4U vt47 857234 / 85721c) calls 0x858bfc -> charge add
  0x84ece4 (work+0 s16, cap 100) (C). This and group D (8570a8) are the Stygian charge differences found.

### B. Attack-index swaps (Stygian attack record vs Zinogre's) - 11 DIFFERENT, 28 MISSING
GU pattern (C, 13 ladders + 9 `== 4` sites): `idx = uncharged; if v==0: idx = charged ? Zc : uncharged; if v==4:
idx = charged ? 1000+n : Zc` -> **variant 1 always gets the uncharged Zinogre index**. GU never requests 4U's Stygian
indices (48-62, 66, 69, 72, 73).
| 4U site (fn, actions) | 4U Zinogre -> Stygian | GU (handler, actions, v1 result) | verdict |
|---|---|---|---|
| 843720 (0x8435fc, 2/9, 2/46), charged at frame 68 | attackEx(0, 41 -> **60**, 3) (uncharged 11) | ef5bdc ef5cb4 (2/46): v1 -> 11 even when charged; 2/9 = GU END | DIFFERENT C |
| 846dc4 (0x846d58, 1/4 1/21) step 1, charged only | attackEx(1, 25 -> **51**, 1024) | ef3f28 ef3fa8: v1 -> attackEx(1, **25**) at frame 26 **also when uncharged** (Zinogre: -1 = none) | DIFFERENT C |
| 846e5c (same, step 0) | attackEx(0, 33 -> **54**, 5120) | ef3ff4: v1 -> 33 | DIFFERENT C |
| 847e74, 8480d4 (0x847d58, 7/0 7/1 7/207 7/208) charged | 39 -> **59** | ef9918 ef9c64 / ef9d60: v1 -> 1 | DIFFERENT C |
| 84b0d4 (0x84ab60, 7/22 51 52 53 112 201 202) | 10 -> **50** | efbe1c efc4dc: v1 -> 10 (7/202 = GU END) | DIFFERENT C |
| 84b770 (0x84b548, 7/35 36 37 54 67) charged | 41 -> **60** | efcfe8 efd210: v1 -> 11 (7/54 = GU END) | DIFFERENT C |
| 84dc44 (0x84daa4, 7/89) | 68 -> **69** | efb364 efb3dc: v1 -> 28 | DIFFERENT C |
| 84e2b0 (0x84dd44, 7/94 113 114 115) | 32 -> **53** | efb5f0 efb824 (7/113 only): v1 -> 32; 7/94 114 115 = GU END | DIFFERENT C |
| 84f24c (0x84f138, 7/109 7/127) | 40 -> **66** | efbb04 efbb70: v1 -> 31 | DIFFERENT C |
| 84f38c (0x84f2cc, 7/125 7/126) | 26 -> **52** | efbc58 efbddc: v1 -> 26 | DIFFERENT C |
| 8484e8, 848574 (0x848310, 7/2 3 6 7 16 68 69 79 80 116 117 128 129 184 185 188 189) | 34/35 -> **55/56** | no GU case for any of these numbers; look-alike efeedc (7/231-234, 248, motions 201 202): v1 -> 7 / 4 (efef58, eff080) | MISSING C |
| 848efc, 848fa8 (0x848bf4, 7/8 9 12 13 70 71 81 82 118 119 130 131) | 34/35 -> **55/56** | no case (GU 7/118 119 = orb handler f00c6c, another move) | MISSING C |
| 849f88, 84a014, 84a0fc, 84a14c (0x849c8c, 7/10 7/11) | 34/35 -> **55/56** | no case (look-alikes eff878 / eff488, 0.47) | MISSING C |
| 84a4f8 (0x84a444, 7/15) | 34 -> **55** | no case; look-alike f0035c (7/247): v1 -> 34 | MISSING C |
| 84beec (0x84bdc4, 7/42) charged | 41 -> **60** | no case | MISSING C |
| 84fa4c, 84fb00 (0x84f744, 7/190 7/191) | 45 -> **48**, 46 -> **49** | no case; look-alike f00684 (7/251 252): v1 -> 45 / 46 | MISSING C |
| 85028c, 850340 (0x84ff7c, 7/217); 850aa8, 850b00 (0x850714, 7/218); 8510a4, 851144 (0x850d0c, 7/219); 852a88, 852b38 (0x852780, 7/220) | 71 / 70 -> **73 / 72** | GU 7/217-219 = other handlers (efe384, efe5e8), 7/220 = END; look-alike efd9ac (7/166-169): Zinogre indices for v1 | MISSING C (8 sites) |
| 8539b0, 853a04 (0x853704, 7/160-175) | 36 / 37 -> **57 / 58** | GU 7/160-171 = other handlers (efd5e0, efd9ac), 172-175 END; look-alike eff488 (7/235-238): v1 -> 23 / 22 | MISSING C |
| 854410, 8544ec (0x854088, 7/176 177) | 43 / 44 -> **61 / 62** | no case; look-alike eff878 (7/239 240): v1 -> 75 / 74 | MISSING C |
| 854678, 8546cc (0x8545d8, 7/178-181) | 35 / 34 -> **56 / 55** | no case | MISSING C |
| 8549ec, 854a38 (0x85490c, 7/182 183) | 34 / 35 -> **55 / 56** | no case | MISSING C |
The 4U Stygian indices exist only in em049's attack data; their content (dragon element) is phase1-assets work.

### C. Shells and effects - 11 DIFFERENT, 5 MISSING, 1 UNRESOLVED
| 4U site (fn, actions) | 4U Zinogre -> Stygian | GU | verdict |
|---|---|---|---|
| 84c6a0, 84cd50 (0x84c280 r1 r2 r3 [sp], 7/32-34 61-63 66 87 105-108 122-124 139-153 211-213): the orb attack | Zinogre: 0x8550cc + 0x84ee48 (uShell044). Stygian, charged: 0x856900 copies 72-B records (rank<5: 0xfebc18 / 0xfebd38; rank>=5: 0xfebe58 / 0xfebf78 / 0xfec098) and posts **uShell046** subtypes 0 / 2 / 3 (0x84f0e4 / 0x85629c / 0x8562f0 -> 0x6629bc) | efa930 (7/105-108 211-213) efaa70 / efaab8 and f00c6c (7/32-34 61 66 87 118-122 221-226 243-245) f00d54 / f00e44: v0 -> f03708, v4 -> f04260, **v1 -> no post** | DIFFERENT C (2 sites) |
| 857f9c 8580d4 858278 85860c 858704 8587d8 858830 (vt77 0x857ba8, 7 motion events) | Zinogre -> 0x856680; Stygian -> **0x855fe4**: kind-2 records idx 0..9 (0xfec098), uShell046 subtype 4 | vt170 ef27b0: 6 `(v\|4)==4` + 1 `v==0` tests (ef2aac ef2b4c ef2b88 ef2bd8 ef2c84 ef2cc0 ef2cf0): v in {0,4} -> ef2dac(k); **v1 -> return** | DIFFERENT C (7 sites) |
| 84dfc8 (0x84dd44, 7/94 113-115) | uShell044 subtype 1 -> **3** | efb5f0 (7/113) posts GU's own shell kind for every variant (efb884 -> 0x3faf28 at frames 66..246; corrected by port batch E2) | DIFFERENT C |
| 856f90 (0x856f0c, from vt47 via 0x856344; partMeatBase 0..5 = charge state change) | effect 0xc088d8 (mgr *0x10572a4), halfwords (57, cat11 ? 5 : 2) -> **(58, cat11 ? 14 : 11)** | eefda4: effect controller this+0xb640 vt[0x1d0/4](id): 0x3ec if (cat 11 && v==0) else 0x3ed: v1 = 0x3ed (Zinogre's non-cat-11 id) | DIFFERENT S |
| 84f8a0 (0x84f744, 7/190 191) | uShell010 (0x6639a0) subtype 129 -> **135** | no case; look-alike f00684 posts GU shell kind 12 for v0/v1 (22 for charged v4) | MISSING C |
| 850100 (7/217), 850898 (7/218), 850e90 (7/219), 852904 (7/220) | uShell010 subtype 235 -> **236** | no same-number case; look-alike efd9ac posts kind 13 for v0/v1 (39 for charged v4) | MISSING C (4 sites) |
| 858428 (vt77) | effect 0xc094e8, halfwords (57, 3) -> **(58, 12)** | no 57/58 effect constants anywhere in uEm057_00 (one unrelated `mov r1,#57` in vt118) | UNRESOLVED |
- Halfword pairs (57, n) / (58, n) = em048 / em049 effect lists (G: file group, effect id, as Tigerstripe's (13, 68)).
  Correction 2026-10-28 (C, test 1): (group, element) of the flat table 0xef895c ((58, 9) = em049_000, (58, 17) =
  em049_011). GU posts by id through the class's own slot 116 0xf060c4 (ids -> PEL list-2 records), so "no 57/58
  constants" did not mean "no post"; eefda4's "controller this+0xb640" is slot 116 itself (`ldr r0, [r2], r0` loads
  [this]; req = this+0xb640). The class scan also missed 4U's aura controller 0x322f18 (outside 0x841000..0x85a2c4,
  `cmp #48 / #114` there): plan.md test 1, em057_01_efx.c.

### D. Tables, charge gain, reactions - 4 MATCHED, 1 UNRESOLVED
| 4U site (fn, actions) | 4U em49 | GU | verdict |
|---|---|---|---|
| 8570a8 (vt47 0x857060, charge actions 1/6 15-17 28-33) | charge-gain row of table 0xe0d0ac (20-B rows, index rank*2) **+20**: Stygian halfwords (15, 20, 25, 25, 25, 0...) vs Zinogre (10, 15, 20, 25, 20, ..., 30); 0x858bfc picks one by HP ratio / state and calls charge add 0x84ece4 | vt129 eefed0 eeff08: row = (rank ? 2 : 0) + ((v\|4) != 4); table 0x16a6284: rows 1 / 3 (Stygian) **byte-identical** to 4U rows 1 / 3 (GU retuned Zinogre row 0 only) | MATCHED C |
| 857758 / 857760 (vt47, 10/112) | Zinogre: charge +50 (0x84ece4(50, 0)); Stygian: none | vt129 ef0378: (v\|4)==4 -> work+0 += 50; v1 skips | MATCHED C |
| 854e20 (cat 10 0x854ad0, 10/110) | reaction table 0xfec878 (Zinogre 0xfec818) | f0229c f02758: variant==1 -> table 0x17d2920, top level equal to 0xfec878 (3, 0x3a, 6, 0, 0, p, 6, 0, 0, p, 0xfe, 0, 0x37, 0, 5, 0x64, 0xa, p, ...); else default | MATCHED S (sub-tables not compared) |
| 84679c (vt40) | Zinogre: W[0x7e6b] != 0 -> 0x94c5c4(1); Stygian skips | vt119 ef25d4: v in {0,4} && charged -> 0xc2780(1); v1 skips | MATCHED S (GU condition differs; equivalence of the two calls not verified) |
| 8475d0 (0x8474d4, 1/14) | 0x93bac0(1, 20 -> **15**, 0.4) | ef4728 calls 0x9cf7c(this, 1) with no count argument, for every variant | UNRESOLVED (G: count moved to data) |

### F. Not Stygian-specific (no verdict)
- 857c70 (vt77): both branches select 137 when byte [r5]+0x35 != 0 (S: equivalent).
- 85512c (0x8550cc), 855950 (0x855760), 8566cc (0x856680): reachable only on the em48/114 paths (0x8550cc only from
  0x84c280's Zinogre branch, 0x856680 only from vt77's Zinogre branch) (C).
- 856ea0 (vt48), 84c738, 84cde8: `cmp #114` only, Stygian = Zinogre (C).

## 2. GU variant tests: what they gate, variant-1 risks
- **`== 1` (9 reads) = 4U Stygian code kept by GU (C):** ef26f0 (vt119, group A), ef448c (1/6.., loop without post),
  ef5a10 / ef5af0 (2/38 39), ef6300 / ef64b0 (2/21 40), ef7ee0 / ef7f40 (2/41 42), f0275c (10/110 table).
  `(v|4)==4` (8): eeff10 (vt129 row: Stygian row), ef25d8 (vt119 skip), vt170 x6 (return).
- **No Thunderlord-only path is reachable for variant 1** at the 208 reads (C for those reads): every TL attack id
  (1000+), TL shell (kinds 22, 39, f04260) and TL branch is behind `== 4`; ladders and `== 0` tests send v1 to the
  default, to the 4U-Stygian branch or to nothing.
- Variant-1 behaviour that matches neither 4U Stygian nor GU Zinogre (risks):
  | GU site | what v1 does |
  |---|---|
  | 13 attack ladders (ef3fa8 ef5cb4 ef9c64 ef9d60 efb3dc efbb70 efd210 efef58 eff080 eff6c0 eff764 effa9c effb10) | uncharged index **regardless of charge**; ef3fa8 arms attack 25 at 1/4 frame 26 when uncharged (Zinogre: none) |
  | efaa70 efaab8 f00d54 f00e44, vt170 x7 | orb attack and motion-event orbs: **no projectile** |
  | ef4488 | frame loop with no post |
  | eefe14 (eefda4) | effect id 0x3ed (TL value) |
  | eeef0c (vt118) | skips eef1a4 (v0-only, when rec[0x5cb6]==1), like v4 |
  | eef390 (vt127 remap) | skips the v0 rank>=5 remap of 7/249-254 (GU-only actions) |
  | ef3128 (vt133 AI conditions, 16 conditions vs 4U's 12) | v0 && rank > 4 condition = false (GU-only condition) |
  | ef2dc8 (ef2dac) | not reached by v1 |
- GU code outside the class that reads the variant (attack data / arc selection, size tables) was not scanned.

## 3. Sites in shared 4U code (outside uEm048)
| 4U | what | verdict |
|---|---|---|
| 0x9431f4 queries 65 (943834: em in {3,4,8,10,12,18,35,37,39,41,43,49} -> 1) and 64 (9437b4: 0 for those + 5,6,80) | Stygian answers like a subspecies, Zinogre not. Reached through uEm048 slot 94 0x857b6c (C); NOT used by the AI script (C, port batch B7: the EMC interpreter 0x94f8cc / 0x92b50c never calls slot 94; its only virtual call, 0x3d9c4c, sits in another bytecode evaluator 0x3d9b84 with no direct caller) | no AI fix needed; GU counterpart not identified |
| uShell046 setup 0xc8a754 (shellPost case, `alloc 824` = uShell046 size) c8ab64 | owner em==49 -> homing target from W+0x278 / 0x27a / 0x27c (0x92c960, 0x91f8bc) | part of the uShell046 port: MISSING S |
| 933b7c (0x933b30) | em in {48,49} and 0x69ae70() >= 6: timer r5 -= 150 | shared, no Stygian difference (C); GU equivalent not checked |
| 9434e0 (0x9431f4 query 30) | em in {48,49,114}: extra checks 0x94d788(1, 9 / 34) | shared (C) |
| 949668 (0x949634) | em in {48,49,88} -> 0x9497ec | shared (C) |
GU's framework switches on the em number (57 for both variants), so the shared cases carry over (S, not verified).

## 4. Stygian-only actions, motions, shells, effects (questions 3, 4)
- **Stygian-only actions: none** (C: dispatcher identical for em 48 / 49 except 10/110's reaction table). Stygian's
  differences live inside actions both species have.
- **Stygian-only motions: none found** (S: no setMotion on any em49-only path; em049 uses em048's banks, C).
- Charge (user: slow walk during which it charges): 4U code adds charge timers + sounds 207 / 209 and the move flag
  to the r1=1 walk / turn actions 2/21 2/38-2/42 (group A), uses its own charge-gain row (group D) and skips the +50 of
  10/112. Which actions Stygian's AI picks comes from em048_cmd (shared) plus the condition path (section 3, G).
- Shell / effect posts on Stygian paths (record only):
  | helper | class / type | subtype / id | 4U sites |
  |---|---|---|---|
  | 0x662904 | uShell044 (event 44, ctor size 0x2e0) | 3 (Zinogre 1 / none) | 847098, 84dfc8 |
  | 0x6629bc via 0x84f0e4 / 0x85629c / 0x8562f0 / 0x855fe4 | uShell046 (event 46, size 0x338) | 0, 2, 3 / 4 | 84c280 orb paths; 0x855fe4 from vt77 x7 |
  | 0x856900 | 72-B orb records | kind 0/1 (rank<5), 1/2/other (rank>=5) | tables 0xfebc18 0xfebd38 0xfebe58 0xfebf78 0xfec098 |
  | 0x6639a0 | uShell010 (event 10) | 135 (Z 129), 236 (Z 235) | 84f8a0; 850100 850898 850e90 852904 |
  | 0xc088d8 (mgr *0x10572a4) | effect | (58, 11 / 14) (Z (57, 2 / 5)) | 856f90 |
  | 0xc094e8 | effect | (58, 12) (Z (57, 3)) | 858428 |
  | 0x2fcc50 sndJoint | sound | 207, 209 | 8432f4, 8453b4 paths |
  GU equivalents: GU posts shells as requests (alloc 0x3faf28 + kind at +8, 0x48c4f0): Zinogre orbs f03708 (kind 3..),
  Thunderlord f04260, uShell010-like kinds 12 / 13 (Zinogre) and 22 / 39 (Thunderlord). No GU kind exists for Stygian.

## 5. Action coverage (question 5)

### 5a. Case maps (C, `case.py`: own case = differs from the num-255 default)
| cat | 4U slot 44 (0x855a60) own cases | GU slot 125 (0xf03620) own cases |
|---|---|---|
| 0 | 0-3 (0x842fa0) | 0-3 (ef3a70) |
| 1 | 0-10, 12, 14-43 | 0-6, 9-10, 12, 14-38, 44-45 |
| 2 | 0-17, 19, 21-82 | 0-4, 10, 15, 19, 21-46, 71-73, 78-87 |
| 3 | 0-12 | 0-14 |
| 4, 5, 6 | none (bx lr) | none (END 0xca118) |
| 7 | 0-16, 20-63, 65-75, 79-133, 139-153, 160-198, 200-213, 215-220 | 0-1, 4-5, 20, 22, 32-37, 51-53, 61, 65-67, 85-91, 100, 105-109, 112-113, 118-122, 125-127, 156-171, 198, 201, 203-214, 217-219, 221-254 |
| 8 / 12 | 0 | 0 |
| 9 | 0-2 | 0-2 |
| 10, 11 | reaction tables (0x9197c0) | reaction tables (0xa134c); not compared case by case |
| 13 | 0-7 | 0-7 |
| 17 | none | base 0xaf598 (GU-only category) |
4U defaults return without ending the action; GU defaults end it at once (0xca10c / 0xca118 = slot 247).

### 5b. The 32 actions in 4U's script only
| 4U action | 4U handler (params) | GU same number | verdict |
|---|---|---|---|
| 0/70, 0/109, 5/8, 6/2 | none in 4U either (cat-0 default, cats 5/6 empty) | END | tokenizer artifacts (G) |
| 3/6, 3/9 | 0x842054 (= 3/5, 12/0; r1 unused) | ef8e08 (= 3/5, 12/0; r1 unused) | **same** C |
| 1/39, 1/43 | 0x847274 r1=3 / 5 (motion 0x314, atk 19) | END; ef45e0 keeps r1 0-2 (1/9 34 37 38) | missing (handler kept, params dropped) |
| 1/40 | 0x847a40 r1=1 (motion 0xf) | END; ef4c74 keeps 1/35 (r1=0) | missing |
| 2/47 2/48 2/49 2/50 2/51 2/52 2/61 2/62 | 0x845fe8 (r1 = 0/1 turn side, r2 = 2,3,6,7,68,69,188,189 = follow-up) motions 0x204 0x205 | END | missing; look-alike GU 2/79 80 83-86 (ef7108: 0x204 0x205 + 0x22b 0x22c, 0.50) |
| 2/75 2/76 2/77 | 0x843d58 inline (motion 0x1c) | END | missing; GU keeps 2/71-73, 87 (ef7588) |
| 7/14 | 0x84a234 (motion 0x1d) | END | moved: GU 7/246 (f00108, motion 0x1d, 0.70) S |
| 7/40, 7/192-197 | 0x84bad8 (r1 2/7/255, r2 = follow-up; motion 0x21d, atk 17 18) | END | moved: GU 7/204, 7/230 (efeb30, 0x21d, atk 17 18, 0.85) S |
| 7/54 | 0x84b548 (0,0,2) | END; efcfe8 keeps 7/35-37 67 214 | missing (param) |
| 7/62, 7/63 | 0x84c280 (0/1, 2, 0, 1): orb attack | END; f00c6c / efa930 keep other param sets | missing (param) |
| 7/115 | 0x84dd44 r1=3 | END; efb5f0 keeps 7/113 | missing (param) |
**Counts (32):** 2 same (3/6, 3/9); 4 artifacts; 26 without a GU case, of which 8 moved to a new number with a
matching handler (7/14 -> 7/246; 7/40 and 7/192-197 -> 7/204 / 7/230), 8 have only a partial look-alike (2/47-52,
2/61, 2/62 -> 2/79-86) and 10 are missing outright (1/39 1/40 1/43, 2/75-77, 7/54, 7/62 7/63, 7/115: GU kept the
handler but not these parameter sets).

### 5c. GU's renumbered look-alikes (motions / attack sets, `pair.py`)
| GU actions (handler) | 4U look-alike (score) | note |
|---|---|---|
| 2/83-86, 2/79 80 (ef7108) | 2/47-70 (0x845fe8) + 7/186 187 (0x84f50c) (0.50) | merged turn + attack |
| 7/158-165, 170 171 (efd5e0) | 7/215 216 (0x84fbe4) (0.44) | 4U 7/160-171 numbers reused |
| 7/166-169 (efd9ac) | 7/217-220 (0x84ff7c / 0x850714 / 0x850d0c / 0x852780) (0.77) | Stygian sites in group B / C |
| 7/204, 7/230 (efeb30) | 7/40, 7/192-197, 7/204 (0x84bad8) (0.85) | |
| 7/231-234, 248 (efeedc) | 7/190 191 (0x84f744) (0.70), 0x848310 family (0.32) | |
| 7/235-238 (eff488) | 7/176-181 (0x854088 / 0x8545d8) (0.56) | |
| 7/239 240 (eff878) | 7/176 177 (0x854088) (0.60) | |
| 7/246 (f00108), 7/247 (f0035c), 7/251 252 (f00684) | 7/14, 7/15 (0.80), 7/190 191 (0.76) | |
| 7/118-122, 221-226, 243-245 (f00c6c), 7/211-213 (efa930) | 0x84c280 orb family (0.67 / 1.00) | |
| 7/217 228 / 218 241 (efe384), 7/219 229 (efe5e8), 7/227 (efdffc), 7/249 250 253 254 (f004c8) | none | GU-only moves (G) |
| 1/44 (ef4d60), 1/45 (ef4e58) | 1/6.. (0x846ec4), 1/3 1/20 (0x846bac) (1.00) | GU extra entries |
| 3/13, 3/14 | 3/4 / 3/12, 3/0 (same handlers) | |
GU same-number cases for 4U numbers mostly run the same handler (scores 0.7-1.0) except the GU-restructured
families above.

**Answer:** 4U's em048_cmd cannot run on GU's class as is: 26 of its native actions end at once in GU, and every
4U handler family with Stygian sites in group B/C rows marked MISSING (7/2-13, 7/15, 7/42, 7/160-220 families) has
no same-number GU case. GU's look-alikes are restructured moves (other motion sets) whose variant-1 path is Zinogre's
uncharged data. Porting Stygian faithfully needs the 4U handlers for those families (with their Stygian indices,
shells and effects), or a remap that accepts Zinogre-GU moves.

## Open questions
- GU counterpart of 4U 0x9431f4 queries 64 / 65 (subspecies flags). em048_cmd does not use them (C, port batch B7).
- 858428 effect (58, 12) and 1/14 0x93bac0 count (15 vs 20): GU counterparts not found.
- 84dfc8: what GU 7/113 shows instead of uShell044 for Zinogre.
- GU base-class reads of the variant (outside 0xeee870..0xf09734) not scanned.
