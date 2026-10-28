# Stygian Zinogre phase 2: reachable 4U actions, port verdicts (static RE, 2026-10-28)

Builds on `phase1-variant-map.md` (addresses, em==49 sites, case maps). 4U = MH4U v1.1, class uEm048, dispatcher slot 44
0x855a60, remap slot 46 0x856a44, action W+0x1ca / +0x1cb, em byte W+0x1c0. GU = MHGU 1.4, uEm057_00, dispatcher slot 125
0xf03620, remap slot 127 0xeef31c. Action notation cat/num; "4U params" = (r1, r2, r3, [sp]) passed by the dispatcher.
Confidence: **C** confirmed in code / data, **S** strong, **G** guess; "not verified" = check incomplete.

Scratch scripts (not in the repo, all print to stdout): /tmp/claude-1000/-home-scrimas-Projects-MH4U-MHGU-port/f1f458ee-797d-4e55-beaf-a811c32a8ba2/scratchpad/p2/
- `emu2.py` path-exploring abstract interpreter for both classes (concrete params / em / variant / cat / num, literal and
  .text+.rodata reads, stack spills, output-parameter invalidation, NZCV-set splitting, VFP literals); every call that
  leaves the class is an event with r0..r3 / s0 / s1 / [sp]. `emu.py` = first 4U-only version (same reach result).
- `reach.py` fixed point of the reachable set (em048_cmd refs + chains + slot-46 remap); `check.py` cross-check of every
  setActionNext site inside walked handlers; `calls.py` / `wrap.py` setAction wrappers and class call sites.
- `cmp.py` / `verdict.py` per-action signatures 4U vs GU (motions + start args, attack slot / index, chained actions,
  motionCheck / atFrame frames, shells / effects / sounds, float literals, named framework calls).
- `gp.py` GU-PARAMS search (GU handler run with a parameter grid / the 4U params); `portinfo.py` PORT handler extents,
  callees, posts; `final.py` the verdict table below and the counts.

## 0. Answer

**Reachable set: 208 actions (C within the emulator model, section 1).** 116 em048_cmd tokens (112 named + the 4
artifacts 0/70 0/109 5/8 6/2) + 92 not in the script: 86 reached through handler chains, 6 only through the slot-46
remap (2/64 2/66 2/68 2/70 7/4 7/208). Identical for em 48 and em 49: **no em==49-dependent chain** (C: same set, same
chain sites). No cat-10/11 reaction chains into cat 1/2/7 (C, section 1.4).

| verdict | actions | meaning |
|---|---|---|
| KEEP | 89 | GU same-number case runs the same handler logic with the same parameters (motions + start args, attacks, follow-ups, frame tests equal) |
| GU-PARAMS = | 11 | GU kept the handler; GU handler + suitable params reproduces 4U (params given) |
| GU-PARAMS != | 20 | GU kept the handler but not this parameter set; with 4U's params it is NOT equivalent (what is missing given) |
| PORT-chain | 16 | GU same-number handler identical except the follow-up (GU 2/4 = wait + think) |
| PORT | 55 | no GU case or a restructured family: port the 4U handler |
| n/a | 17 | no 4U handler (0/n>=4, 5/x, 6/x, 7/135 136 255): 4U returns, GU ends at once; nothing to port |

**The main GU restructuring (C, 30+ handlers):** GU kept most 4U attack handlers but replaced the 4U code-level
follow-ups (setActionNext(7, n) / (1, n) / (2, n)) with **setActionW(2, 4) + thinkRequest(0)** (0x752ec / 0x82510, e.g.
efa4b0 / efa4c4 in 7/4, f00fa4 in 7/33, efc0e0 in 7/51). GU 2/4 (ef7990 case @ef7cd8, C) =
setTargetMode(0), timer rec+0x1bc = 120.0, count down with timerDown, then setActionW(2, 4) + thinkRequest: an idle wait
while GU's own AI script picks the next move. 4U's em048_cmd relies on the code chains (7/4 -> 7/20 / 7/21, 7/205 ->
7/206 -> 7/207, 7/14 -> 7/15 -> 7/16, ...), so running it on GU handlers would drop every combo follow-up. PORT-chain
rows can be served either by the 4U handler or by GU's handler with its 2/4 request replaced by the 4U target (the 4U
condition of each follow-up is at the listed 4U site).

**4U handlers behind the PORT, PORT-chain and GU-PARAMS != rows (4U function, words listed incl. literal pools /
instructions reached by the reachable actions, C):**
| 4U handler | actions | size | GU base worth reusing |
|---|---|---|---|
| 0x845fe8..0x8462d0 | 2/47-52 2/61-70 (turn, then follow-up 7/r2) | 186 / 175 | ef7108 (same turn motions 0x204 / 0x205, follow-up 2/4) |
| 0x84383c..0x843c3c (+ 843d58 case stubs) | 2/72 2/73 2/75-77 2/79 2/80 (motion 0x1c, G: backstep; stub passes (1, 7, n, 0)) | 256 / 225 | ef7588 (equal except follow-up) |
| 0x848310..0x848bf4 | 7/2 3 6 7 16 68 69 188 189 | 569 / 405 | none (efeedc 1/4) |
| 0x8499bc..0x849c8c | 7/4 7/5 (chain) | 180 / 170 | efa240 |
| 0x84a234..0x84a444 | 7/14 (chain) | 132 / 122 | f00108 (GU 7/246) |
| 0x84a444..0x84a59c | 7/15 (chain) | 86 / 72 | f0035c (GU 7/247) |
| 0x84a59c..0x84ab60 | 7/205 7/209 (chain) | 369 / 317 | effc00 |
| 0x84ab60..0x84b184 | 7/51-53 (chain), 7/202 | 393 / 326 | efbe1c |
| 0x84b548..0x84bad8 | 7/35 36 67 (chain), 7/54 7/200 | 356 / 307 | efcfe8 |
| 0x84bad8..0x84bdc4 | 7/192-197 7/204 (follow-up = params) | 187 / 156 | efeb30 |
| 0x84d488..0x84d8b8 | 7/203 7/206 (chain) | 268 / 223 | efc6cc |
| 0x84dd44..0x84e328 | 7/113 7/115 | 377 / 328 | efb5f0 (shell loop 66..246 with GU's own kind; no frame-94 sound, no 100..260 sound loop) |
| 0x853704..0x854088 | 7/160-175 | 609 / 562 | none (GU reused the numbers) |
| 0x854088..0x8545d8 | 7/176 7/177 | 340 / 279 | none (eff878 1/4) |
| 0x84f50c..0x84f744 | 7/186 7/187 | 142 / 133 | none |
| 0x84f744..0x84fbe4 | 7/190 7/191 | 296 / 255 | f00684 3/4 (no window 80-100) |
| 0x84fbe4..0x84ff7c | 7/215 7/216 | 230 / 215 | none |
| 0x84ff7c..0x850714 | 7/217 | 486 / 424 | efd9ac (GU 7/166-169: same motions / attacks / frames) |
| 0x850714..0x850d0c | 7/218 | 382 / 344 | efd9ac |
| 0x852780..0x852bd0 | 7/220 (entered at 0x8527ec from cat-7 sub-dispatcher 0x851494) | 276 / 254 | none |
| 0x847274..0x8474d4 | 1/39 1/42 1/43 (r1 3-5 branches) | 152 / 135 | ef45e0 (r1 0-2) |
| 0x847a40..0x847bdc / 0x847bdc..0x847d58 | 1/40 / 1/41 (r1 = 1 chain 1/40 -> 1/41 -> 1/42) | 103 / 84, 95 / 69 | ef4c74 / ef4fd4 |
| 0x842b44..0x842da8 | 13/3 (chain 13/4) | 153 / 144 | f02f24 (chains 13/5) |
Shared class helpers they call: 0x856d6c..0x856e60 (61 words; distance / approach to target slot; GU counterpart
efc550, S: same 4-float signature, target slot rec+464, sqrt), 0x8565cc..0x856680 (45 words; 4 x sndJoint, GU posts no
sound, S drop), 0x855c38..0x855fe4 (235 words, 67 reached, from 0x84bad8; GU efeb30 calls efa7e0, G counterpart),
0x852d74..0x852ec0 (83 words, 39 reached, from 0x842b44). Orb helpers 0x84f0e4 / 0x85629c / 0x8562f0 (uShell046) are the
phase-1 Stygian orb sites, needed whatever handler serves the orb actions.

**GU-PARAMS equivalence calls (gp.py, exact-param runs):**
| 4U action | GU handler + params | equivalent? |
|---|---|---|
| 7/21 (84a59c 1,0) | effc00(2,0) = GU 7/20 | yes (C: 4U r1 only selects 7/4 vs 7/5 when r2 = 2) |
| 7/31 (84a59c 0,3) | effc00(1,0) (GU 7/209's params) | yes (C: start blend 14 / frame 60 both) |
| 7/40 (84bad8 255,255) | efeb30(0,0) | yes (C) |
| 7/62 7/63 (84c280) and 7/32 33 34 61 66 87 (same number = f00c6c) | **efa930 with the 4U params** (r1, r2, r3, [sp] same meaning) | yes except the shell post (S: 7/32 7/61 one extra GU atFrame(4) in the emulator); GU f00c6c is a restructured copy (no frames 16 / 78, no windows 0-20 / 28-38, follow-ups 2/4) |
| 1/39 1/42 1/43 (847274 r1 3-5) | ef45e0(3..5) | **no**: GU tests r1 == 2 only; r1 3-5 take the r1 = 0 path (no sleepFlagA + 0x93c6c8, no r1 = 5 effect path 0x390f9c / 0x939c00, no r1 = 3 end branch) (C) |
| 1/40 (847a40 r1 1) / 1/41 (847bdc r1 1) | ef4c74 / ef4fd4(76) | no: fixed chain 1/36 / 1/37 (4U 1/41 / 1/42) (C) |
| 2/75-77 (843d58 -> 84383c(1,7,n,0)) | ef7588(1,1,0) | follow-up only (2/4 vs 7/31 / 7/32 / 7/61) (C) |
| 7/54 7/200 (84b548) | efcfe8(0,3) / (0,0) | no: no follow-up 7/53, no window mc 9 0-20 (C) |
| 7/115 (84dd44 r1 3) | efb5f0(0) | no: GU's shell loop posts its own kind, not uShell044 3; no sounds at 94 / 100..260 step 20 (C, corrected by port batch E2) |
| 7/202 (84ab60 r1 3) | efbe1c | no: r1 = 3 start (0x216 blend 16 / frame 24) and window mc 9 100-110 missing (C) |
| 7/192-197 (84bad8 cat,num) | efeb30 | follow-up only: GU params (1,1) / (0,1) give 2/4 (C) |
| 7/14 / 7/15 | GU 7/246 f00108 / 7/247 f0035c | follow-up only (none vs 7/15 / 7/16) (C) |

**Remap (slot 46) must be ported too (C):** 4U 0x856a44 runs from setAction 0x90efac on the controlling machine for
every mode except 3 (setActionNext mode 5 included) and remaps 2/63<->64, 65<->66, 67<->68, 69<->70 and 7/4<->5,
7/207<->208 by 0x91e130(this, 0), 7/186 -> 215 and 7/187 -> 216 when 0x69ae70() >= 5. GU 0xeef31c starts with
7/207<->208 (by 0xc7ef8(this, 0), C) and GU-only 7/249-254 -> 162 / 163 (variant 0, rank >= 5, C); the rest of the
function is behind `variant == 4` (G: Thunderlord entries, not read). No 2/63-70, 7/4<->5 or 7/186 / 187 entry (C for the
part read).

**Unmapped 4U helpers the ports need** (section 4): 0x91e130 (target side, GU 0xc7ef8 S), 0x69ae70 (rank, GU 0x3a8d68 S),
0x90f90c (charged?, GU 0x81790 S), 0xaad5b0 / 0xaad40c / 0xaacda4 (vector math, reimplement), 0x2bad24 / 0xd076b0
(7/190 191 217 218 220 orb / shell geometry, G), plus small ones listed there.

## 1. Reachable set

### 1.1 Method (C for the code facts, S for completeness)
- em048_cmd from `dump/romfs/data/em049.arc` (`enemy\em048\data\em048_cmd`, 0x3AABBA02), all groups, `emc.refs`: 116 native
  tokens = the brief's list + 0/70 0/109 5/8 6/2 (C). Suspect reads (G): 10/111 (`6f 00 0a 6f 01 01` = condition 0x6f
  id 10, case 1 in g0.s0), 0/9, 0/255, 5/2 also sit inside condition blocks; all are no-ops in both games anyway.
- Per action: emu2 walk of slot 44 from 0x855a60 with W+0x1ca / +0x1cb / +0x1c0 set, recursing into class callees
  (depth 6), plus vt47 0x857060 (r1 = cat, r2 = num), vt40 0x846738, vt39 0x846598. Chains = calls to setActionNext
  0x94ef9c (r1 = cat, r2 = num; on the host it calls 0x90efac mode 5, else stores W+0x1cf / +0x1d0 / +0x1d1), setActionW
  0x935ac8, setAction 0x90efac. Class calls that reach 0x90efac within 2 levels (C, `calls.py sa`): 0x94ef9c (155
  sites, all in action handlers), 0x94dcbc (3: setTargetMode(1) + setAction(0, 3) mode 2, in cat-0 / cat-3 handlers),
  0x9197c0 (44: reaction tables, section 1.4), 0x91f744 (vt36 13/0, section 1.3; and 0x841268, no caller), 0x94cd6c (vt9;
  and 0x841158, no caller). No direct store to W+0x1ca / +0x1cb (C).
- Every chain argument resolved to constants (0 unresolved); follow-ups passed as parameters resolved through the
  emulator: 2/47-70 r2 -> 7/r2 at 0x846134; 0x84bad8 (r1, r2) -> (cat, num) at 0x84bd38; 0x84b184 (r2, r3) at 0x84b51c;
  0x84383c (r2, r3) at 0x843bf8 (C).
- `check.py`: the 62 setActionNext sites that no reachable action hits belong either to handlers no reachable action
  runs (0x842694 3/10-11, 0x8474d4 1/14, 0x848bf4 7/8-13 70 71 81 82 118 119 130 131, 0x849c8c 7/10 11, 0x84e328 7/99,
  0x850d0c 7/219, 0x8545d8 7/178-181) or to parameter values of unreachable actions (0x846ec4 r1 = 3 -> 1/30 = 1/17;
  0x848310 r2 = 2 with r3 1-3 -> 7/169-171 173-175 = 7/79 80 116 117 128 129, its r2 = 1 with r3 1-3 sites (7/161-163
  165-167) are used by no 4U case (dead); 0x84a59c r2 = 2 -> 7/4 / 7/5 = 7/100; 0x84b548 r1 = 2 -> 7/198 =
  7/37; 0x84b184 = 7/23-30 ...), checked by emulating every case of these handlers (C). 0x859a88 (3/0, 3/1) has no
  caller in uEm048 (S: another class).
- Bugs found and fixed during the work (affect only float arguments / shells, re-checked): conditional VFP mnemonics
  (`vldreq`), stack output parameters (0x2bad24 writes sp+0x18), d-register copies. Reach result unchanged (C).
- Limits: unknown memory is unknown (paths are explored both ways, so chains can be over-approximated, never missed
  unless a target comes from memory, which did not happen); emulator joins states after 12 per pc (S).

### 1.2 The set (208)
Script tokens (116): 0/0 0/9 0/11 0/20 0/21 0/29 0/70 0/78 0/87 0/109 0/111 0/255 1/0-4 1/6 1/9 1/15 1/16 1/18 1/19 1/22
1/23 1/26 1/27 1/34 1/35 1/38-40 1/43 2/0 2/1 2/3 2/10 2/15 2/19 2/21 2/22 2/26 2/32 2/33 2/35 2/36 2/38-40 2/45-52 2/61
2/62 2/72 2/73 2/75-77 2/79 2/80 2/82 3/1 3/4 3/6 3/7 3/9 5/2 5/8 6/2 7/0 7/1 7/14 7/22 7/33-36 7/40 7/51 7/54 7/62 7/63
7/65-67 7/85-87 7/89 7/91 7/109 7/113 7/115 7/192-197 7/204 7/205 7/209 7/211 7/212 7/255 10/0 10/2 10/111 12/0 13/1.

Reached only by chains / remap (92), with the 4U site (C):
| action | from |
|---|---|
| 1/12 | 7/65@84c23c |
| 1/20 / 1/21 | 9/2@852c70 / 9/1@852cf0 |
| 1/28 | 1/15 1/29 @84704c |
| 1/29 | 1/16 1/32 1/33 @847068 |
| 1/32 / 1/33 | 7/36@84ba78 / 7/33@84cc64 |
| 1/36 1/37 / 1/41 1/42 | 1/35@847bbc, 1/36@847d34 / 1/40@847adc, 1/41@847c5c |
| 2/63 65 67 69 71 | 7/194 195 196 197 193 @84bd38 |
| 2/64 66 68 70 | remap of 2/63 65 67 69 |
| 3/0 3/2 3/3 | 2/15 19 21 35 45 46 82 via 0x8555c8 (@855678 / 85572c / 8556c8: height step 650 / 1200 / 2200) |
| 3/5 | 3/4@842018 |
| 7/2 3 6 7 68 69 188 189 | 2/47-52 2/61 2/62 and 2/63-70 @846134 |
| 7/4 / 7/5 | remap(7/5) / 7/203@84d8a0 |
| 7/15 / 7/16 | 7/14@84a40c / 7/15@84a4c8 |
| 7/20 7/21 | 7/4 7/5 @849b8c / 849c58 |
| 7/31 7/32 7/52 7/61 7/200 7/201 | 2/75 76 79 77 72 73 @843bf8 |
| 7/53 | 7/35 36 54 200 @84b9dc |
| 7/112 / 7/126 | 7/67@84b9f8 / 7/51-53@84b168 |
| 7/135 7/136 | 7/171 7/175 @853b90 / 853b74 (frame 80, r2 >= 2 && r3 == 3), 7/218@850bcc / 850bb0 |
| 7/160-175 | 7/217 @8504b0..8506b0; also 7/6 -> 160 @848750, 7/7 -> 164, 7/68 -> 168, 7/69 -> 172 |
| 7/176 7/177 | 7/168@853c1c, 7/172@853c38, 7/218@850bf4 / 850c10 |
| 7/186 7/187 | 7/16 7/189 @848950 / 7/188@8487c0 |
| 7/190 7/191 | 7/186@84f710 / 7/187@84f6f4 |
| 7/198 | 7/192@84bd38, 7/34@84cc98 |
| 7/202 | 7/168 170 171 172 174 175 @853bf8, 7/218@850a0c |
| 7/203 7/206 7/207 7/208 7/210 | 7/204@84bd38, 7/205@84aaf0, 7/206@84d864, remap(7/207), 7/209@84ab2c |
| 7/215 7/216 | 7/176@854128 / 7/177@8540fc, 7/217@850640 / 850590, remap(7/186 / 7/187) |
| 7/217 | 7/2 3 6 7 68 69 188 189 @848a2c |
| 7/218 | 7/160-175 @853d90 |
| 7/220 | 7/215 7/216 @84fe90 |
| 8/0 / 9/0 / 9/1 9/2 | 7/65@84c094 / 8/0@855380 / 9/0@846538 846554 |
| 13/2-13/6 | 13/1@84e8a0 -> 13/2@84e9c4 -> 13/3@842be8 -> 13/4@842e2c -> 13/5@84ead0 |
- G-rank gates (C): 0x848310 -> 7/217 and 0x853704 -> 7/218 only when 0x69ae70() >= 5 and (W+0x1d2 % 100) >= 50 (the
  action serial as a 50 % roll), plus [sp] != 1 for 0x848310 only (0x848384; corrected by port batch C 2026-10-28:
  0x853704 tests no [sp]); 0x854088 (7/176 177) -> 7/215 / 7/216 when 0x69ae70() >= 5 and the roll > 50 (`bls`);
  remap 7/186 / 7/187 -> 215 / 216 when 0x69ae70() >= 5. So 7/217 7/218
  7/135 7/136 7/161-163 165-167 169-171 173-175 are G-rank only (7/160 164 168 172 also come from 0x848310 at any rank).
- **7/135 / 7/136 have no 4U handler** (cat-7 sub-dispatcher 0x851494 default 0x851868 returns) (C): the 4U chains
  7/171 / 7/175 / 7/218 -> 7/135 / 7/136 lead to a no-op action (G: unused move left in the code; what 4U does then
  depends on the framework, not traced).
- work+0x115..0x117 = the lead-in's (side, r2, r3) (C): 0x8489c8 stores 0x848310's (read by 7/217), 0x853d24 stores
  0x853704's (7/218), 0x84fbe4 stores (side, 0, 0) (7/220). 4U's callers pass 0x848310 only (r2, r3) = (0,0) (1,0)
  (2,0) (1,5) (port batch D), so 7/217 ends or chains 7/160 164 168 172 215 216. With r2 != 0, 7/217 tests no motion
  end, only frame 62 (C: 0x850238); 7/218 does (r2 == 1: motion end; r2 >= 2: motion end or frame 62).
- 2/10 also chained from 13/2 13/3 13/4 8/0 9/0; 1/4 from 1/3 1/6 1/15 1/16 1/20 1/28 1/29 1/32 1/33 2/21 2/40; 7/0 7/1
  from 7/169 7/173 7/218 (all script actions too).

### 1.3 Engine-started actions (outside the script / chains)
- 13/0: uEm048 vt36 0x858fd4 (event hook, r1 = event): r1 == 22 -> 0x91f744 = setAction(13, 0, mode 1) (C). 4U 0x842a08
  motion 2 = GU 13/0 f02bd0 motion 2: KEEP (C signature).
- Base 0x94cd6c (vt9 0x858fc8 tail call) reaches setAction through 0x91b7f8 with table-driven arguments: shared framework
  code, not class-specific (S, not traced).

### 1.4 Cat 10 / 11 reactions (C)
Class 0x854ad0 (cat 10) and the dispatcher's cat 11 path only pass reaction tables to the base runner 0x9197c0 (44 call
sites: 10/7 89 114 20 31 29 30 27 42 43 68 69 37 110 112 96-102 175 32 210 82 135 180 155 157 187 188 161 189 190 169
197 171 167 217 8 83 150 181 225 and 11/0-255); other cat-10 numbers end through vt+0x164. The runner sets actions only
through end helpers: 0x94e654 -> 0/9, 0x955a10 -> 0/8, 0x9559a8 -> 0/6, 0x911ad0 -> 0/7, 0x94dcbc -> 0/3, 0x939020 /
0x9189b4 -> 12/255 (C within 2 call levels of 0x9197c0; S beyond). **No reaction chains into cat 1 / 2 / 7.** Script
10/0 10/2 10/111: 4U default (vt+0x164 end at once) = GU base 0x76144 (vt+0x3dc end at once): KEEP (C).

## 2. Verdict per action (grouped by 4U handler)
4U params -> GU same-number case (GU params; END = 0xca10c / 0xca118). Signatures compared 4U em 48 vs GU variant 0 (logic)
and em 49 vs variant 1 (variant sites, phase 1). KEEP rows: motions with start args, attack slots / indexes, follow-ups
and every motionCheck / atFrame frame equal (C, emulator) unless a note says otherwise.

| 4U handler | actions (4U params -> GU case) | verdict | note | Stygian sites (phase 1) |
|---|---|---|---|---|
| 842fa0 | 0/0 -> ef3a70(72) | KEEP | | |
| 842fa0 | 0/9 0/11 0/20 0/21 0/29 0/70 0/78 0/87 0/109 0/111 0/255 -> END | n/a | 4U case default returns, GU ends (both: no behaviour; cat 0 n >= 4 are idle states the framework also uses, e.g. 0/6-0/9 set by the reaction runner) | |
| 852ec0 | 1/0 1/2 1/12 1/19 1/22 1/23 1/27 -> ef4fd4(76) | KEEP | | |
| 846a60 | 1/1 -> ef3c10 | KEEP | | |
| 846bac | 1/3 (0) 1/20 (1) -> ef3d28(0 / 1) | KEEP | charge helper 0x8588b8 windows inlined in GU | |
| 846d58 | 1/4 (0) 1/21 (1) -> ef3f28(0 / 1) | KEEP | GU adds effect-handle releases (this+0xcb08..0xcb10 -> 0x32a400) at frames 20 / 80 and attackEx(1, -1) resets | 846dc4 846e5c idx 51 / 54 (B DIFFERENT; GU v1 arms 25 also uncharged) |
| 846ec4 | 1/6 (0,0) 1/15 (1,0) 1/16 (2,0) 1/28 (0,1) 1/29 (1,1) 1/32 (2,3) 1/33 (2,4) -> ef4280(same) | KEEP | | 847098 uShell044 3 (A DIFFERENT), charge gain 8570a8 (D MATCHED) |
| 847274 | 1/9 (0) 1/34 (1) 1/37 (2) 1/38 (0) -> ef45e0(same) | KEEP | | |
| 847274 | 1/39 (3) 1/42 (4) 1/43 (5) -> END | GU-PARAMS != | ef45e0 keeps r1 0-2 (see section 0) | |
| 847680 | 1/18 -> ef4874 | KEEP | GU adds a timerDown | |
| 8477c4 | 1/26 -> ef4990 | KEEP | | |
| 847a40 | 1/35 (0) -> ef4c74 | KEEP | | |
| 847a40 | 1/40 (1) -> END | GU-PARAMS != | ef4c74: no r1, chain 1/36 | |
| 847bdc | 1/36 (0) -> ef4fd4(76) | KEEP | GU merged it into the generic handler | |
| 847bdc | 1/41 (1) -> END | GU-PARAMS != | ef4fd4 path exists for 1/36 only (chain 1/37) | |
| 843d58 | 2/0 -> ef7990(80); 2/1 -> ef5674(0); 2/3 -> ef58c4(0); 2/22 -> ef6604; 2/82 -> ef5f24(1,0) | KEEP | 2/82 inline case = same signature as 2/15 (attack 42 + 3/x selector) | |
| 843d58 | 2/10 -> ef7588(0,0,0); 2/71 -> ef7588(1,0,1) | KEEP | motion 0x1c: GU blend 10, start frame computed (4U 2 / 0 and 10 / 20) (S) | |
| 843d58 -> 84383c | 2/72 (1,7,200,0) -> ef7588(1,2,0); 2/73 (1,7,201,0) -> ef7588(1,3,0) | PORT-chain | GU follow-up 2/4 (+ blend 10) | |
| 843d58 -> 84383c | 2/75 (1,7,31,0) 2/76 (1,7,32,0) 2/77 (1,7,61,0) -> END | GU-PARAMS != | ef7588(1,1,0) equal except follow-up | |
| 843d58 -> 84383c | 2/79 (1,7,52,0) -> ef7108(0,0,1); 2/80 (1,7,34,0) -> ef7108(1,0,1) | PORT | GU numbers reused by a turn (ef7108); ef7588 equal except follow-up | |
| 844c8c | 2/15 (1,0) 2/35 (1,2) 2/45 (3,2) -> ef5f24(same) | KEEP | 3/x selector 0x8555c8 = GU ef5da4 (same 650 / 1200 / 2200 thresholds, C) | |
| 844fec | 2/19 (1,0) -> ef6178(1,0) | KEEP | | |
| 84516c | 2/21 (0) -> ef62e4(0) | KEEP | | 845190 8453b4 (A MATCHED) |
| 84516c | 2/40 (1) -> ef62e4(1) | KEEP | 4U posts uShell044(3) from frame tables 0xfebb28 / 0xfebbb8 for BOTH species (r1 == 1, no em test, C); GU none (GU-wide, like sounds) | 845190 8453b4 (A MATCHED) |
| 845668 | 2/26 -> ef677c | KEEP | | |
| 845edc | 2/32 (0) 2/33 (2) 2/36 (1) -> ef6fb8(same) | KEEP | | |
| 843264 | 2/38 (1,0) 2/39 (1,1) -> ef59ec(same) | KEEP | | 84328c 8432f4 (A MATCHED) |
| 8435fc | 2/46 (1) -> ef5bdc(1) | KEEP | | 843720 idx 60 (B DIFFERENT) |
| 845fe8 | 2/47 (0,2,0) 2/48 (1,3,0) 2/49 (0,6,0) 2/50 (1,7,0) 2/51 (0,68,0) 2/52 (1,69,0) 2/61 (0,188,0) 2/62 (1,189,0) 2/63-70 (same r2, r3 = 1) -> END | PORT | turn (motion 0x204 / 0x205, window 10-40 or blend 10 / start 14 and 16-40 for r3 = 1), follow-up 7/r2; GU look-alike ef7108 follows with 2/4 | |
| 8413f4 | 3/0 (0) 3/1 (1) -> ef8178(0 / 1) | KEEP | numeric constants differ (4U 15.5 30 35 68 481 543 593, GU 48 50) (S: retuned) | |
| 8418ac 841afc 841d84 8421cc | 3/2 -> ef855c(92); 3/3 -> ef87d0(96); 3/4 -> ef8a24(1); 3/7 -> ef8f94(108) | KEEP | numeric constants differ (S) | |
| 842054 | 3/5 (5) 3/6 (6) -> ef8e08(60); 3/9 (9) -> ef8e08(116); 12/0 (0) -> ef8e08(0) | KEEP | 4U -30 / -4.7 vs GU 5000 constants (S) | |
| (none) | 5/2 5/8 6/2 -> END | n/a | categories 5 / 6 empty in both | |
| 847d58 | 7/0 (0,0) 7/1 (1,0) 7/207 (0,1) 7/208 (1,1) -> ef9918(same) | KEEP | | 847e74 8480d4 idx 59 (B DIFFERENT) |
| 848310 | 7/2 (0,0,0,0) 7/3 (1,0,0,0) 7/6 (0,1,0,0) 7/7 (1,1,0,0) 7/16 (1,1,5,1) 7/68 (0,2,0,0) 7/69 (1,2,0,0) 7/188 (0,1,5,0) 7/189 (1,1,5,0) -> END | PORT | r2 == 0: no follow-up; else follow-up by r1 / r2 / r3 (jump tables 0x848708 0x84872c 0x8486d0 0x84884c) | 8484e8 848574 idx 55 / 56 (B MISSING) |
| 8499bc | 7/4 (0) 7/5 (1) -> efa240(0 / 1) | PORT-chain | GU 2/4 instead of 7/20 / 7/21 | |
| 84a234 | 7/14 -> END | GU-PARAMS != | moved to GU 7/246 f00108, no follow-up 7/15 | |
| 84a444 | 7/15 -> END | GU-PARAMS != | moved to GU 7/247 f0035c, no follow-up 7/16 | 84a4f8 idx 55 (B MISSING) |
| 84a59c | 7/20 (0,0) -> effc00(2,0); 7/86 (0,1) -> effc00(0,0) | KEEP | GU re-encoded params: r1 = start (0: blend 4 / frame 0, 1: 14 / 60, 2: 4 / 46), r2 = follow-up mode | |
| 84a59c | 7/21 (1,0) -> END; 7/31 (0,3) -> END | GU-PARAMS = | effc00(2,0) / effc00(1,0) | |
| 84a59c | 7/205 (0,4) -> effc00(0,1); 7/209 (0,5) -> effc00(1,0) | PORT-chain | 4U follow-ups 7/206 / 7/210 at frame 68; GU 2/4 / none (GU 7/209 = 4U 7/31 start) | |
| 84ab60 | 7/22 (0) 7/112 (1) 7/201 (2) -> efbe1c(0,0 / 1,0 / 2,0) | KEEP | GU adds a rest-state hook (atFrame(table) -> restApply(0), motionCheck(1) -> 0xc0410) | 84b0d4 idx 50 (B DIFFERENT) |
| 84ab60 | 7/51 (4) 7/52 (5) 7/53 (6) -> efbe1c(0,1 / 2,1 / 1,1) | PORT-chain | GU 2/4 instead of 7/126 (7/51 also lacks window mc 9 100-110) | 84b0d4 |
| 84ab60 | 7/202 (3) -> END | GU-PARAMS != | see section 0 | 84b0d4 |
| 84c280 | 7/32 (1,0,2,0) 7/33 (0,0,3,0) 7/34 (0,0,4,0) 7/61 (1,2,2,1) 7/66 (0,0,0,0) 7/87 (1,0,0,0) -> f00c6c | GU-PARAMS = | use efa930 with the 4U params (f00c6c restructured) | 84c6a0 84cd50 uShell046 orbs (C DIFFERENT) |
| 84c280 | 7/62 (0,2,0,1) 7/63 (1,2,0,1) -> END | GU-PARAMS = | efa930 with the 4U params | 84c6a0 84cd50 |
| 84c280 | 7/211 (0,0,0,5) 7/212 (1,0,0,5) -> efa930(same) | KEEP | orb shell via GU request (Zinogre) | 84c6a0 84cd50 |
| 84b548 | 7/35 (0,0,0) 7/36 (1,0,0) 7/67 (0,0,1) -> efcfe8(0,0 / 0,1 / 0,3) | PORT-chain | 4U follow-ups 7/53, 1/32 + 7/53, 7/112; GU none / 2/4; 4U window mc 9 0-20 missing; blend 2 vs 10 | 84b770 idx 60 (B DIFFERENT) |
| 84b548 | 7/54 (0,0,2) 7/200 (0,1,0) -> END | GU-PARAMS != | see section 0 | 84b770 |
| 84bad8 | 7/40 (255,255) -> END | GU-PARAMS = | efeb30(0,0) | |
| 84bad8 | 7/192 (7,198) 7/193 (2,71) 7/194 (2,63) 7/195 (2,65) 7/196 (2,67) 7/197 (2,69) -> END | GU-PARAMS != | follow-up only | |
| 84bad8 | 7/204 (7,203) -> efeb30(1,1) | PORT-chain | GU 2/4 instead of 7/203 | |
| 84bff8 | 7/65 -> efa510(1276) | KEEP | | |
| 84d488 | 7/85 (0,0) 7/198 (1,0) 7/210 (2,0) -> efc6cc(same) | KEEP | 7/210: GU blend 10 / frame 38 as 4U (C: literals efcc38 / efcc3c; corrected by port batch E1) | 8468c4 (A MATCHED) |
| 84d488 | 7/203 (1,1) 7/206 (2,2) -> efc6cc(1,2 / 2,1) | PORT-chain | GU 2/4 instead of 7/5 / 7/207 | 8468c4 |
| 84daa4 | 7/89 -> efb364(1328) | KEEP | | 84dc44 idx 69 (B DIFFERENT) |
| 84b184 | 7/91 (1,255,255) -> efcc48(1) | KEEP | 255 = no follow-up | |
| 84f138 | 7/109 (0) -> efbb04(0) | KEEP | | 84f24c idx 66 (B DIFFERENT) |
| 84dd44 | 7/113 (1) -> efb5f0(0) | PORT | GU keeps the shell loop 66..246 (efb884 -> 0x3faf28, its own kind, index bounded at 11, C) but lacks the sounds at 94 / 100..260 step 20; ported (em057_01_mv_f.c), so GU's stand-in shell is gone until B5 | 84e2b0 idx 53, 84dfc8 uShell044 3 (B / C DIFFERENT) |
| 84dd44 | 7/115 (3) -> END | GU-PARAMS != | same gap | 84e2b0 84dfc8 |
| 84f2cc | 7/126 (1) -> efbc58(1) | KEEP | | 84f38c idx 52 (B DIFFERENT) |
| 851494 | 7/135 7/136 7/255 -> END | n/a | no 4U case (0x851868 returns) | |
| 852780 (@8527ec) | 7/220 -> END | PORT | | 852a88 852b38 idx 73 / 72, 852904 uShell010 236, effect c094e8 |
| 853704 | 7/160-163 (0,1,0-3) 7/164-167 (1,1,0-3) 7/168-171 (0,2,0-3) 7/172-175 (1,2,0-3) -> GU 7/160-165 170 171 efd5e0, 7/166-169 efd9ac, 7/172-175 END | PORT | GU reused the numbers for other moves | 8539b0 853a04 idx 57 / 58 (B MISSING) |
| 854088 | 7/176 (0,0) 7/177 (1,0) -> END | PORT | | 854410 8544ec idx 61 / 62 (B MISSING) |
| 84f50c | 7/186 (0) 7/187 (1) -> END | PORT | | |
| 84f744 | 7/190 (0) 7/191 (1) -> END | PORT | look-alike f00684 (7/251 252) lacks window mc 3 80-100 | 84fa4c / 84fb00 idx 48 / 49, 84f8a0 uShell010 135 (MISSING) |
| 84fbe4 | 7/215 (0) 7/216 (1) -> END | PORT | | |
| 84ff7c | 7/217 -> efe384(0,1) | PORT | GU 7/217 = other move; efd9ac matches except follow-up / shell | 85028c 850340 idx 73 / 72, 850100 uShell010 236 |
| 850714 | 7/218 -> efe384(1,1) | PORT | same | 850aa8 850b00, 850898 |
| 855298 | 8/0 -> f01c18(0) | KEEP | | |
| 8462d0 | 9/0 -> f01f18(132) | KEEP | | |
| 852bd0 | 9/1 9/2 -> f02164(132) | KEEP | 4U atFrame result unused (dead call) | |
| 854ad0 | 10/0 10/2 10/111 -> base 0x76144 | KEEP | both end at once | |
| 84e7d0 | 13/1 -> f02ce4; 13/2 -> f02e3c; 13/5 -> f03344; 13/6 -> f03428(172) | KEEP | | |
| 842b44 | 13/3 (3) -> f02f24 | PORT-chain | GU 13/5 (skips 13/4) or 2/10 | |
| 842da8 | 13/4 (4) -> f0316c | KEEP | | |
- Numeric-literal deltas inside KEEP handlers (S, not traced; most are GU framework changes: sinf / cosf instead of the 4U
  angle tables, effect handles, charge-timer inlining): 1/3 1/6 1/15 1/16 1/20 1/28 1/29 1/32 1/33 (4U charge helper
  0x8588b8 constants), 2/15 19 21 35 45 46 82 (GU loads 650 / 1200 / 2200 as floats, 4U as int bit patterns, same
  values), 7/20 7/86 (4U -9.03 -8 -1 25 68 120.5 only), 7/22 7/112 7/201, 7/85 7/198 7/210, 8/0 (4U 180), 9/0 (4U -600,
  0.005), 13/4 (4U 500), cat 3 (above). Values: `python3 -B cmp.py` prints them per action.
- Sounds: every 4U sndJoint / sndPos call (207 209 204 219 220 225) has no GU class counterpart (phase 1: GU class posts
  no sound) (C).

## 3. PORT handlers: callees and posts (portinfo.py, em 49 walk of the reachable actions)
| 4U handler | unmapped external callees (calls) | motions | attacks (em 49) | shells / effects / sounds |
|---|---|---|---|---|
| 0x845fe8 | 90f90c 9175a8(2) 923fc8(2) aacda4 aad5b0 | 0x204 0x205 | - | - |
| 0x84383c | 90f90c 923fc8 aad5b0 | 0x1c | - | - |
| 0x848310 (+ 8565cc, 856d6c) | 69ae70 90f90c(3) 955478 aacda4 aad5b0 | 0x201 0x202 0x23a 0x23b 0x23e 0x23f | (0,4) (0,7) (0,55) (0,56) | sndJoint 209 225 |
| 0x8499bc | 9175a8 923fc8 aad5b0 b05184 | 0x20a 0x20b | - | - |
| 0x84a234 | 91ad14 923fc8(2) aad5b0 | 0x1d | - | - |
| 0x84a444 | 90f90c | 0x203 | (0,55) | - |
| 0x84a59c | 90f90c(3) 92e998 942258 94461c | 0x208 0x209 0x20c 0x20d | (0,9) | - |
| 0x84ab60 (+ 856d6c) | 90f90c(3) 942258 aacda4(2) | 0x215-0x218 | (0,50) | - |
| 0x84b548 | 90f90c(4) 9175a8(3) 92e998 | 0x219 0x21b 0x21c | (0,11) (0,60) | - |
| 0x84bad8 (+ 855c38) | 69ae70 90f90c 923fc8(2) aacda4 aad5b0 | 0x21d | (0,17) (1,18) | - |
| 0x84d488 (+ 856d6c) | 955478(2) aacda4 aad5b0 | 0x21e | (0,24) | - |
| 0x84dd44 | 10ed68 930894 aad5b0 be9a0c | 0x14 0x18 | (0,53) | uShell044 3; sndJoint 207 219, sndPos 220 |
| 0x853704 (+ 8565cc, 856d6c) | 69ae70 90f90c(3) 9175a8(2) 91e130(2) 955478 aacda4 aad5b0 | 0x201 0x202 0x228 0x229 0x23a 0x23b 0x23e 0x23f | (0,22) (0,23) (0,57) (0,58) | sndJoint 209 225 |
| 0x854088 (+ 8565cc, 856d6c) | 69ae70 90f90c(4) 9175a8 91e130 955478 aacda4 aad5b0 | 0x201 0x202 0x228 0x229 | (0,22) (0,23) (0,61) (0,62) | sndJoint 209 225 |
| 0x84f50c | - | 0x22b 0x22c | - | sndJoint 209 225 |
| 0x84f744 (+ 856d6c) | 2bad24 69ae70 90f90c(2) 955478 aacda4 aad40c aad5b0(2) d076b0 | 0x201 0x202 | (0,48) (0,49) | uShell010 135, effect 0xc094e8 |
| 0x84fbe4 (+ 856d6c) | 9175a8 91e130 aacda4 aad5b0 | 0x228 0x229 0x23a 0x23b 0x23e 0x23f | - | - |
| 0x84ff7c (+ 8565cc, 856d6c) | 2bad24 69ae70 955478 aacda4 aad40c aad5b0(2) d076b0 | 0x23c 0x23d | (0,72) (0,73) | uShell010 236, effect 0xc094e8, sndJoint 209 225 |
| 0x850714 (+ 856d6c) | same as 0x84ff7c | 0x23c 0x23d | (0,72) (0,73) | uShell010 236, effect 0xc094e8 |
| 0x852780 (+ 856d6c) | 2bad24 69ae70 955478 aacda4 aad40c aad5b0(2) d076b0 | 0x23c 0x23d | (0,70) (0,71) (0,72) (0,73) | uShell010 235 / 236, effect 0xc094e8 |
| 0x847274 | 2fd110 2fff1c 390f9c(2) 939c00 94c980 | 0x314 | (0,19) | effects 0xc0819c 0xc0ca90 (mapped names only) |
| 0x847a40 / 0x847bdc | 310104 92213c / 2fd110 2fff1c 390f9c | 0xf / 0x305 | - | effect 0xc0ca90 |
| 0x842b44 (+ 852d74) | 92e334 930124 936ac0 94bd6c 955478 | 0xd 0x219 | - | - |
Mapped calls used by all of them (module/game.h, notes/api-map.md): setMotion, setMotionSpeed, setTargetMode, stopMove,
turnToTarget, motionCheck, atFrame, isMotionEnd, curMotion, attackEx, attackFlag, setActionNext, rotateVel, accelVel,
restApply, inRange, setStopDist, timerDown, camShakeJoint, sleepFlagA / B, jointPos (0x93093c), atan2 (C).
Stygian indices / shells inside these handlers: phase-1 groups B / C (the table in section 2 lists them per action).

## 4. Unmapped 4U helpers (candidates)
| 4U | what (C from the 4U body unless marked) | GU candidate |
|---|---|---|
| 0x90f90c | charged / state query, gates charged attack indexes and speeds | 0x81790 (S: dump/apimap2.pkl 99 votes; GU 1/4 ef3fc4 uses it at the same place) |
| 0x69ae70(mgr) | quest rank / stage value (>= 5 = G rank tests) | 0x3a8d68 (S: apimap2 99; GU remap eef3a4 `>= 5`) |
| 0x91e130(this, slot) | side of target slot W+536+16*slot vs position W+408 (remap, 0x853704 0x854088 0x84fbe4) | 0xc7ef8 (S: same role in both remaps, 7/207 <-> 208) |
| 0x9175a8(ang, a, b) | yaw += ang over motion window a..b | 0x76e8c (C, tigerstripe missing-actions.md) |
| 0x955478 | called when motionCheck(3, ...) hits | 0x7b5f8 (C, tigerstripe notes) |
| 0x923fc8 | size factor | 0xbecf0 (C, gogmazios port-checklist) |
| 0xaacda4(a, b) | sqrt(dx^2 + dz^2) | inline / 0x13efddc (S, apimap2) |
| 0xaad5b0 / 0xaad40c | rotY vector rotation / vector normalise (vsqrt) | none: reimplement (tigerstripe blast.md uses rotX / rotY) |
| 0xb05184 0x92e998 0x942258 0x94461c 0x91ad14 0x930894 0xbe9a0c | small framework helpers | 0xc0644 0x816d0 0xbf178 0xb0eb0 0xb0a8c (blend > 0, game.h) 0xc1660 0x16b920 (S: apimap2 99 votes, not re-checked) |
| 0x2bad24 | large query (412-byte frame, output struct at sp+24 read back): ground / ray test (G) | not found |
| 0xd076b0 | vector / matrix math (G) | not found |
| 0x10ed68 | memcpy (ldm / stm loop) | libc |
| 0x390f9c 0x2fd110 0x2fff1c | effect / sound-side helpers (0x2fa04c checks) (G) | not found (GU has no class sounds) |
| 0x939c00(this, f) | W+0x7e80 \|= f, W+0x7e81 &= ~f | not found |
| 0x92213c(this, v) | W+0x7a1a = 1, W+0x7a18 = v | not found |
| 0x94c980 | em byte + global (+0xad50) compare with 0x55f5 / 0x55f6 (quest / area check) (G) | not found |
| 0x310104 | this+0x1839 = 1 unless player index matches (net flag) (G) | not found |
| 0x92e334 0x930124 0x936ac0 0x94bd6c | 13/3 path (G) | 0x936ac0 -> 0xc43bc (W, 1 vote) |
| class 0x856d6c / 0x8565cc / 0x855c38 / 0x852d74 | approach / sounds / 84bad8 helper / 13/3 helper | efc550 (S) / none (sounds) / efa7e0 (G) / not found |

## 5. Unresolved / caveats
- 7/135 / 7/136: chained by 4U code but no 4U handler; how the 4U framework recovers was not traced (G-rank only).
- Suspect script tokens (10/111 0/9 0/255 5/2) would need the EMC interpreter to settle; no effect on the port.
- KEEP is behavioural (emulator signatures), not instruction-for-instruction; numeric deltas listed in section 2 are
  not traced (S). Variant-1 data problems (indexes, orbs, effects) remain the phase-1 sites.
- Sub-tables of the reaction tables and the base 0x94cd6c path (vt9) not followed past 2 call levels.
- GU-PARAMS = for the orb family relies on efa930 having the 4U parameter meaning (C on 10 parameter sets, S overall);
  7/32 / 7/61 show one extra GU atFrame(4) in the emulator (probably an emulator join artefact, not verified).
