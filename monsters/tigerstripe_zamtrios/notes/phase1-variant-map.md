# Tigerstripe Zamtrios: 4U em==92 sites vs GU uEm067_00 variant 1 (static RE, 2026-10-20)

4U = MH4U v1.1 code (`dump/mh4u.asm`), class uEm022 (em 22 and 92), W = `[this+0xe28]`, work = `[this+0x8d88]`.
GU = MHGU 1.4 main, class uEm067_00 (0xf68df4..0xf7b4d8), variant byte `this+0xb5f5`, rec = `[this+0x1428]`.
Confidence: **C** confirmed in code/data, **S** strong, **G** guess. "not verified" = check incomplete.
Action numbers: 4U CAT7 jump table has `sub #6` (num = index + 6); GU CAT7 the same (0xf756a0, 198 entries).
Scratch scripts used (local archive dump/scratch/tigerstripe-session/): `scan92.py`, `u22.py`/`catmap4.py` (4U), `g67.py`/`gsites.py`/`gptr.py` (GU),
`assets.py` (arcs). Not part of the repo.

## 0. Counts
- 4U scan (`cmp rN,#92` <= 6 instrs after `ldrb rN,[rX,#0x1c0]`): **71 sites** (C), = 68 in uEm022 + 0x3238ac + 0x91a1d4 + 0x91a530.
  - 12 uEm022 sites are `cmp #22; beq X; cmp #92; beq X` (22 and 92 take the same branch; the else path is dead
    code for an em that never runs this class): 748efc 749a34 749c44 74bbc8 74c1d4 74ced0 74d324 74dfb8 74f24c
    753344 753630 755068 -> **SHARED, nothing to port** (C). Same for 0x91a1d4 / 0x91a530 (see section 3).
  - 57 Tigerstripe-specific sites: verdicts below. **MATCHED 39, DIFFERENT 7, MISSING 10, UNRESOLVED 1.**
- The scan under-counts 4U em==92 tests (C): 58 more `cmp rN,#92` in uEm022 where the em byte was loaded
  earlier: 25 TS tests in CAT10 0x757068 (choice of the reaction tables passed to 0x9197c0), 4 in CAT11 0x749c94
  (749edc 749f18 749f38 749f68, same), the rest are `cmp #22; cmpne #92` shared tests or 21/22/91/92 chains (shared).
  4U em==22-only tests (Tigerstripe takes the non-22 path) also exist: see section 2b.
- GU: 179 `movw #0xb5f5` reads (C: 123 `cmp #1`, 54 `cmp #0`, 2 `cmp #2` hits that are other registers:
  f71ce0 = mode r5; f7743c not checked). Plus reads through a pointer register (`ldrb rN,[rP]` after
  `ldrb [rP, r0]!`, >= 31 found: f764a8, f69634, f69f24, f69f9c, 27 flag sites) and one via
  `this+0x1428+0xa1cd` (f6a280). The pointer forms were found by a partial scan: **count not exhaustive**.
- **119 of the 123 GU `cmp #1` sites (and 25 pointer-read sites) are one inlined pattern** (group A).
  GU uses `variant != 0` (cmp #0) for all motion/attack/shell choices.

## 1. Groups (4U site -> GU)

### A. Motion-speed flag (4 sites) - MATCHED (C)
| 4U sites | 4U behaviour | GU | verdict |
|---|---|---|---|
| 75da04 (setMotion wrapper 0x75d9f0), 75da8c (set-if-different 0x75da40), 749fe8 (setMotionEx wrapper 0x749fd4), 753d38 (motion-speed wrapper 0x753d24) | em92 and action category in {1,2,3,7}: work+0x10 = 1; the slot-44 dispatcher end 0x758b44 then clears it and calls 0x922c78(rec+0x410 * 0.95) | inlined after every setMotion: `variant==1 && cat<=7 && (142 >> cat)&1` -> work+0x10 = 1 (119 movw sites + 25 pointer sites); slot-125 dispatcher end f79188: work+0x10 -> 0xb0870(rec+0x398 * 0.95) | MATCHED C |

### B. Motion / attack-index swaps (24 sites)
| 4U sites (function, action) | 4U Zamtrios -> Tigerstripe | GU (variant != 0 path) | verdict |
|---|---|---|---|
| 7556a0 (CAT1 inline, 1/4) | mot 0x403 -> 0x464, attack slot1 33 -> 58 (0x75da40) | f6a700 0x464, f6a760 #58 | MATCHED C |
| 755784 (1/5) | 0x401 -> 0x462 | f6a8c0 0x462 | MATCHED C |
| 755d28 (1/65) | 0x366 -> 0x372 | f6c39c `movweq 0x366 / movwne 0x372` | MATCHED C |
| 7493c8, 749470 (0x749340, 2/4) | 0x405 -> 0x465, attackEx0 46 -> 63; 0x406 -> 0x466 | f6e008 0x465, f6e058 #63, f6e0c0 | MATCHED C |
| 753684, 7536c8 (CAT2 inline, 2/5) | turn table 0xe0a434 {0x409,0x407,0x408} -> 0xe0a474 {0x469,0x467,0x468} (0x92f720 / 0x911c44) | f6e1c8 / f6e1e8 -> table 0x16a7b2c {0x469,0x467,0x468} (0x7a338 / 0x7a314) | MATCHED C |
| 749740 (0x749670, 2/7) | 0x442 -> 0x46e, attack 30 -> 60 | f6e49c 0x46e, f6e4ec #60 | MATCHED C |
| 749d20 (0x749c94, 2/36, 2/37, CAT11) | 0x408/0x407 -> 0x468/0x467 | f6e9e4 (0x467 / 0x407 / 0x468 seen) | MATCHED S (0x408 operand not seen) |
| 74d48c, 74d55c (0x74d3f4, 7/10) | 0x40a -> 0x46a, attackEx0 9 -> 59; 0x406 -> 0x466 | f71764 0x46a, f717b4 #59, f71844 | MATCHED C |
| 74d9d4, 74da0c, 74dc40, 74ddb4 (0x74d918, 7/11 58 65 66 68 69) | 0x40c -> 0x46b, attack 10 -> 61; 0x40a -> 0x46a, 9 -> 59; 0x406 -> 0x466 | f71ce0/f71df4 0x46b #61, f7200c 0x46a, f7205c #59, f71d90 | MATCHED C |
| 74e318, 74e82c (0x74e288, 7/24 202 203) | 0x425 -> 0x46c; 0x426 -> 0x46d | f7233c, f72880 | MATCHED C |
| 74fce0, 74fe0c, 74fedc (0x74fc48, 7/67) | 0x442 -> 0x46e, 30 -> 60; 0x40a -> 0x46a, 9 -> 59; 0x406 -> 0x466 | f73dc4 f73e14, f73f8c f73fdc, f74040 | MATCHED C |
| 751c2c (0x751b4c, 16/2) | attack slot1 47 -> 64 | f764a8 `movne #64 / moveq #47` | MATCHED C |
| 75ccd8 (0x75c9e0, from vt77) | attack 12 -> 62 | f79524 `movne #62 / moveq #12` | MATCHED C |
| 754a3c, 754b84 (0x7549a4, **7/200**) | 0x40a -> 0x46a, attackEx0 9 -> 59; 0x406 -> 0x466 | GU CAT7 case 200 = default f75b38 (no handler) | **MISSING** C |

### C. Tremor shell uShell005 (0x661d18, event type 5) skipped by Tigerstripe (6 sites)
| 4U site | 4U | GU | verdict |
|---|---|---|---|
| 74db80 (0x74d918) | ZM posts subtype 13 scale 1.8, TS skips | f71ef0 `variant==0` -> request id 0x122 kind 3 -> 0x48c4f0 | MATCHED C |
| 74deac (0x74de00, 7/12 7/13 1/67) | subtype 5 scale 0.4 | f6c598 variant==0 gate, post f6c65c | MATCHED C |
| 74fd8c (0x74fc48, 7/67) | subtype 13 scale 1.3 | f73e6c gate, post f73f30 | MATCHED C |
| 754f48 (CAT12 0x754edc, 12/0) | subtype 5 scale 0.4 | f77ef8 gate, post f77fbc | MATCHED C |
| 7496b4 (0x749670, 2/7) | subtype 13 scale 1.3, TS skips | f6e5c8: posted at frame 150 with **no variant test** | **DIFFERENT** C (GU posts the tremor for TS) |
| 754d74 (0x754be8, **7/201**) | subtype 13 scale 1.8 | no GU 7/201 handler | **MISSING** C |

### D. Projectile shells (6 sites) - all DIFFERENT
| 4U site | 4U Zamtrios -> Tigerstripe | GU | verdict |
|---|---|---|---|
| 74e630 (0x74e288) | uShell012 (0x663e60 -> event 12) subtype 8/9 -> **40/41**; TS in mode 2, W+0x145 in {3,7}: range 600 -> 2100 | f72708: variant != 0 jumps over the whole shell post (f72838) | DIFFERENT C (GU TS fires nothing) |
| 74f4f4, 74f760 (0x74f1b0, 7/33 34 54-56) | uShell012 subtype 11 -> **43**; 10 -> **42** | f735d0: variant != 0 skips post f73668 and (f73870) the second post f738f0 | DIFFERENT C (GU TS fires nothing) |
| 74ec90 (0x74ebd8 = GU f72c80, motions 0x43b/0x43c) | uShell016 (0x6620c4) subtype 13, f 3000 -> **40, 2000** | post f72dd4, no variant test | DIFFERENT S (GU posts the ZM shell for TS) |
| 7506b0 (0x750590 = GU f744a4, 0x439/0x43a) | uShell016 subtype 47 -> **48** | post f746e4, no variant test | DIFFERENT S |
| 751394 (0x750e10 = GU f74e78, 0x438/0x43c/0x45a/0x45c) | uShell016 13/3000 -> **40/2000** | post f755ec, no variant test | DIFFERENT S |

### E. Tigerstripe-only logic, skips, effects (17 sites)
| 4U site | 4U behaviour on em92 | GU | verdict |
|---|---|---|---|
| 74d590 (0x74d3f4, 7/10 step 1) | extra step: motionCheck 9 [140..242] -> map-point search 0x9276b4 (masks 1024/4096, then 65536/4096) -> W+0x145 = 1/2 -> ground y 0x924040(1.8) -> \|dy\| <= 700: stop, W+356 = dy/68, W+468 = 68 | f71894 `variant==1`: 0xa6d04 masks 1024/4096 and 65536/4096, 0xa77b0(1.8), 700 | MATCHED C |
| 7514a8 (0x751464, **7/77, 7/78**, motions 0x454/0x456) | same ledge step (masks 66560/20480) | GU CAT7 77/78 = default; motions 0x454/0x456 not used anywhere in uEm067 | **MISSING** C |
| 74ff10 (0x74fc48, 7/67 end) | TS only: tail call 0x92d0d4(this,0,0) | f74090 variant==1 -> 0xc46c8(this,0,0) | MATCHED C |
| 758bb4 (vt75 0x758b94) | mode 2 and cur motion 0x453 or outside 0x450..0x456: bone id 201 scaled x0.7 (0x960270) | vt168 f7a37c, same motion test, joint `[this+0x498]+0xc9`, 0.7 | MATCHED C |
| 75a690 (0x75a680 from vt77) | TS returns at once (skips W+0x7814 flags from work+4 bits / rank bytes 6,1,2) | f79704 variant==1 -> skip (rec+0x5cfc \|= 2 ...) | MATCHED C |
| 74a4d0 (vt40 0x74a474) | 0x91b268 (W+0x539 = 2): ZM in state 4 or mode 2, TS only state 4 | vt119 f6a280: `(variant==0 && mode==2) \|\| state==4` -> 0xbd114 | MATCHED C |
| 75b9bc, 75bb5c (0x75b758 action start, vt47) | per-(cat,num) 0x911f58 values: TS 1/46->30, 3/0..4->3, 7/10,11,58,65,66,67,77,78->3, 10/13,67,135->30, 10/167->100 (ZM 50 + work+0xe); TS counter work+0xf | f6925c (=0x75b758): f694a8 TS list (7/77,78 absent), f69634 counter | MATCHED S |
| 75bd84, 75c2d8 (0x75b758 end) | TS skips 0x91ad80 | f69f9c / f69f24 variant==0 -> 0xbd128 | MATCHED S |
| 747d14 (0x747a78, **3/0..3**) | TS skips 0x91ad80 in its own category-3 actions | GU has **no category-3 handler** (dispatcher case 3 -> base 0xca118) | **MISSING** C |
| 7551b0, 75522c, 7552c8 (0x7550f8, called from 2/0 2/1 2/6 ...) | ledge chain (W+0x1d9 == 1, map points mask 0x8000000/8192, 1.6): ZM -> setAction(3, 80..85), TS -> (3, 0/1/2) | no counterpart: no mask 0x8000000 search, no setAction to category 3 in uEm067 | **MISSING** C |
| 74a238 (vt39 init) | effect-manager request 0xc08290(mgr *0x10572a4, id 7 -> **8**, this) | not in GU vt118 (f68e40..f690b8); GU equivalent not found | **MISSING** S |
| 3238ac (uMhEftCtrl000 0x323790) | see section 3 | no uMhEftCtrl class in GU dti.pkl | **MISSING** S |
| 74e198 (0x74de00) | TS skips effect 0xc0aa20(mgr *0x10572a4, 6, W+0x14c, ...) | f6c418 has no variant test after f6c598; ungated 0x40b10/0x40b50 calls at f6c7b0/f6c840 may be the counterpart | UNRESOLVED G |

### 2b. 4U em==22-only tests (Tigerstripe takes the non-22 path) - checked ones
| 4U | em22 only | GU | verdict |
|---|---|---|---|
| 74a1e4 (vt39) | setTargetMode(4) + 0x91f744(6,0) | f68fd8 variant==0 -> 0xbc8b0(4), 0x76ab0(6,0) | MATCHED C |
| 748dfc / 7494d8 | special branch on num 28 / 33 | f6d968 / f6e280 variant==0 && num 28 / 33 | MATCHED S |
| 74be4c (0x74bca4) | ZM path vs isMotionEnd path | f6ac80 variant==0 | MATCHED S |
| 759f10 (vt51) | ZM: mode/work+4 path; TS: 0x954e48 | vt133 f78b28 variant==0 / 0x8172c | MATCHED S |
| 759d8c (vt50) | ZM runs 0x75c3bc (isAction(1,66), parts loop); **TS returns** | vt132 -> f79a38 runs it for both, no variant test | DIFFERENT C (moot if TS never runs 1/66: em092 cmd has no 1:66 ref, heuristic tokenizer) |
| 74c5d4 (0x74c5b0) | 0x947258 only for em22 | GU f6b694 not checked | not verified |
| CAT10 0x757068 / CAT11 0x749c94 (em92 tests outside the scan) | TS reaction tables (motions 0x370..0x377, 0x462..0x464) | CAT10 0xf76de0: 21 variant==0 sites, CAT11 f77c88..f77d24: 4 sites -> tables (e.g. 0x17e5720 -> 0x17e4ca4 mot 0x364 vs 0x17e5730 -> 0x17e4cbc mot 0x370) | MATCHED S (tables not compared entry by entry) |

GU variant paths without any 4U counterpart: **none found** (every GU variant test located has a 4U em92 or em22 test).

## 3. Sites outside uEm022
- **0x3238ac** in 0x323790 = uMhEftCtrl000 (DTI 0x10b9878; only caller 0x323df0, a virtual method: vtable word
  0xe5fb1c, 14 words after the getDTI slot, i.e. slot 19 if getDTI is slot 5): effect
  controller of the owner monster; when the owner's motion is 0x411 and uEm022 0x75328c returns 2/3 it builds an
  effect request and calls 0xc08698 (mgr *0x10572a4): em22 -> halfwords (sp+8 = 15, sp+6 = per-kind id),
  em92 -> (13, 68); others nothing (C for the code, meaning of the two halfwords G: file group / effect id).
  GU: no uMhEftCtrl* DTI in `MHGU_Editor/scratch/dti.pkl` (2911 names); GU motion 0x411 users in uEm067 have no
  variant test. Counterpart not found (MISSING S).
- **0x91a1d4, 0x91a530** in shared uEnemy 0x919f38 (motion 0x3f5 nearby): species switch where 22 and 92 share
  the case (0x91a2ac / 0x91a5a4: actions 6/2, 6/11, 7/35). No Tigerstripe difference (C). GU counterpart not
  identified; GU's framework switches on the em number (api-map notes), which is 67 for both variants, so the
  shared treatment carries over (S, not verified).

## 4. Assets used by the GU variant-1 code
- Motion ids requested on variant != 0 (C, collected from setMotion/setMotionEx/0xaffac/0xc24d8 r1 operands and the
  variant tables): 0x462 0x463 0x464 0x465 0x466 0x467 0x468 0x469 0x46a 0x46b 0x46c 0x46d 0x46e, 0x370 0x372;
  motion test 0x450..0x456 / 0x453 (vt168). **All exist only in 4U em092** (bank 4 idx 98..110, bank 3 idx 112..119,
  bank 4 80..86). The variant-0 counterparts (0x364 0x366 0x401..0x40c 0x425 0x426 0x442) exist only in em022/GU.
- Shared GU paths (no variant test) also request Zamtrios-only ids absent from em092: 0x215 (f6ad00 1/16.., f79ac4
  vt132), 0x321 0x322 (6/17), 0x415 (f6a16c, 1/10, 6/18, 6/1), 0x416 (6/3), 0x417 (6/2), 0x41e (f72244, f79550),
  0x445 0x446 (f73bac, f73cf0, f74400). Same in 4U (no em92 test there), so these belong to actions Tigerstripe is
  not expected to run (G; em092 cmd table not cross-checked per action).
- Attack data indices on variant 1: 58 59 60 61 62 63 64 (+ the shared ones). 4U em022 and em092 attack data
  (em_data.arc etd words 28..29) are **byte-identical, 69 records**; GU em067_00_attackdata has 69 records and
  differs from both in the same 34 records (C). -> GU's attackdata serves variant 1 (S).
- Shells: GU variant 1 posts no TS-specific shell (section D). 4U TS shells: uShell012 subtypes 40 41 42 43,
  uShell016 subtypes 40 48. GU em067_00.arc has `shell\em\em067_00_shell01\...` sets; TS subtype data would have
  to be built (not inspected further).
- Effects / sounds: no variant-specific effect or sound id found in GU (only the gated tremor request id 0x122).
  4U em092.arc has its own efl set (`effect\efl\em\em092\em092_000..102`, 23 efl) and 53 sound waves.
- 4U em092 cmd table (heuristic `tools/emc.py refs`): same 23-group shape as em022 (29/180 scripts), refs native
  actions incl. 3:3 3:4 7:70 7:77 7:78 7:200 7:201, which GU uEm067 does not handle (G, tokenizer is heuristic).

## 5. Skeleton and motions
| | 4U em022 | 4U em092 | GU em067_00 |
|---|---|---|---|
| bones | 49 | 49 | 49 |
| bone IDs | 0-4 6-21 80 90 100 130-142 150-159 200 201 | same | same |
| parent by ID, bone positions | - | = em022 | = em092 |
| joint order | - | differs from em022 | differs from em092 |
| mot_0 slots / non-empty | 35 / 21 | 35 / 21 | 35 / 21 |
| mot_2 | 24 / 16 | 24 / 15 (no idx 21) | 24 / 16 |
| mot_3 | 110 / 34 (max 109) | 120 / 30 (max 119) | 110 / 34 |
| mot_4 | 93 / 54 (max 92) | 111 / 54 (max 110) | 93 / 54 |
- GU em067_00 motions = 4U em022 motions (same slots, same non-empty indices, same frame counts in all 4 banks) (C).
- em092 vs em022: bank 3 adds 112..119, drops 29 32-34 100-103 106-109; bank 4 adds 80-82 84-86 98-110, drops
  1-3 5-10 12 21-23 30 37 38 66 69 70; shared indices have equal frame counts (C). The dropped ids are exactly the
  Zamtrios motions the em92 branches replace.
- LMT tracks address bone IDs; IDs, hierarchy and bind positions match, so em092's LMTs fit the GU skeleton by ID
  (S; one em092 track parsed with bone id 0x3f800000 = parse artifact, not investigated).
- **Recommendation: a variant-1 arc must use 4U em092's motion banks (copied as is, LMT 67), not GU em067_00's.**
  Evidence: every variant-1 motion GU's own code requests (0x462..0x46e, 0x370, 0x372, 0x463) is absent from
  em067_00 and present in em092; shared ids requested by both variants exist in both sets except the Zamtrios-only
  list above (same situation as 4U).

## 6. What a port must add on top of GU's uEm067_00 for variant 1
1. Arc: em092 motions (+ model/textures/efl/sounds from em092); GU attackdata / bodydata can stay (attack records
   are identical in 4U).
2. Missing actions (also absent for GU Zamtrios): 7/200 (0x7549a4), 7/201 (0x754be8, with the TS tremor skip),
   7/77-78 (0x751464, TS ledge step), category 3 (TS 0x747a78 3/0..3 incl. skipping 0x91ad80; ZM 0x747554 /
   0x74714c) and the ledge chain 0x7550f8 -> (3,0..2). Needed if em092's cmd table reaches them (heuristic: yes for
   3:3 3:4 7:77 7:78 7:200 7:201).
3. Shells: TS subtypes uShell012 40/41 (+range 2100 rule), 42, 43; uShell016 40 (f 2000) and 48 - GU skips or posts
   the Zamtrios shell.
4. Gate the CAT2/7 tremor (f6e5c8) with variant == 0.
5. Effects: vt39 effect-manager id 8 (4U 0xc08290), uMhEftCtrl000 (13, 68), and check 0x74de00's 0xc0aa20 skip.
6. Optional: vt132 body skip for TS (4U vt50), only matters if TS ever runs action 1/66.

## 7. Re-checks after the report (2026-10-20)
- Section 5 motion claims (C): banks 0/2/3/4 of GU em067_00 = 4U em022 (indices and frame counts); the 15 motion
  ids of section 4 are all in em092 and none in em067_00.
- f738f0 (C): `[sp+0xc]` = `&this->variant` (stored at f735cc); f73870 reads it and skips the second post too, so
  GU variant 1 fires neither uShell012 post of f735d0.
- Dispatcher f78f98 (C): jump table at f79000 on `this+0x73e0`, cases 3, 4, 5 = default f790cc -> base 0xca118
  (case 1 -> f6cf0c, case 2 -> f6eb14, case 6 -> f71034).
- EMC native refs (heuristic tokenizer, `tools/emc.py` refs over all groups): em092 = em022 except em022's 0:130;
  em022 / em092 refs missing from GU em067_00_cmdtbl: 1:69 1:73 1:74 1:77 4:111 6:40 6:41. GU still has its own
  handlers for 1:69 (f6d380), 1:73 (f6d3a8), 1:74 (f6d3b4), 1:77 (f6d62c), 6:40 (f71414), 6:41 (f71430) (C: table
  entries not default); 4:111 goes to the base (case 4 default). GU's own em067_00_cmdtbl also yields 3:3 3:4 and
  the 7/77 78 200 201 refs, so either the tokenizer misreads them or GU Zamtrios has the same dead references:
  still open, see below.

## Open questions
- GU counterparts of the 4U effect manager calls (0xc08290, 0xc08698, 0xc0aa20) and of uMhEftCtrl000.
- Exhaustive list of GU variant reads through pointer/base registers (partial scan only).
- 74c5d4 (em22-only 0x947258) in GU f6b694.
- Per-action check of em092's cmd table (needs a real EMC interpreter, not the heuristic tokenizer).
