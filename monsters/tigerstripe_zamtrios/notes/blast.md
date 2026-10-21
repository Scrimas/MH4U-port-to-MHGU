# Tigerstripe Zamtrios: 7/70 deflate blast = 4U uShell016 subtypes 38 / 49 (static, 2026-10-21)

Tags: C = confirmed in code / data, S = strong, G = guess. 4U = MH4U v1.1 (dump/mh4u.asm, code.bin at 0x100000).
Scratch scripts: /tmp/claude-1000/-home-scrimas-Projects-MH4U-MHGU-port/aa473438-013b-4411-b8ca-5d2f95908e85/scratchpad/blast/.
Shell field names follow monsters/gogmazios/module/em089_shell016.c: P = +0x100 (far point), Q = +0x120 (start).

Short version: 38 and 49 run the **same code**. They differ only in data: Dunes 38 = volume r208 + effect scale
(0.8, 0.8, 1.0); other stages 49 = r260 + scale 1.0. The capsule goes from the mouth (joint 131 + M (0, -60, 0)) to
4000 ahead, in **world** axes: Ry(yaw) Rx(pitch), not the joint matrix. It is re-placed at the joint every frame and
lives 21 frames, with a hit window of frames 7..21. It has no map test, ground post or camera shake. Effect:
em092_001 element 1 at the capsule start, then em092_200 when the shell ends. Both EFLs are already in our arc but
have no PEL record. Sounds: 201 at spawn, 205 + 210 along the capsule.

## 1. Shell code

### 1a. Post (7/70, 0x750144..0x7501f4) (C)
- Clamp: `d = u16(a - this+0x8d20)`. If d < 0x8000, d = min(d, 0xe39) (+20 deg, pitch down). Else d = max(d, 0xf555)
  (-15 deg, up).
- Event: `+0` joint 131, `+8` offset (0, -60, 0), `+0x1a` d, `+0x1c` 0.
- 0x6620c4 args: length s0 4000, u16 0xffff (no attack override: init skips +0x19c), `+0x14` vector pointer 0
  (+0x280 = zero vector).
- Subtype: 38 if byte W+0x14b == 17, else 49.

### 1b. Ctor 0xc6f900 (C)
38 and 49 take the default path c6fa10:
- `+0x290` x = d + W+0x1a8 (owner x angle, u32 add)
- `+0x294` y = 0 + W+0x1ac (owner yaw)
- `+0x298` = 0
- `+0x2a0` u16 = owner motion (0x90f994), `+0x2a4` joint, `+0x270` offset, `+0x29c` length

So **both owner angles are added**, the same as em089's default (add_x = add_y = 1).

### 1c. Init 0xc69ddc (C)
- Common part:
  - +0xf1 = 1
  - P and Q zeroed
  - life +0x13c = table 0x102bbbc[sub] = **21.0** for both
  - +0x2b8 = 0, +0x2bc = 0
- Case 38 (0xc6a58c): `0xc07ecc(*0x10572a4, kind 8, area +0x130, shell, offset 0 (zero vector), scale (0.8, 0.8,
  1.0), -1)`.
- Case 49 (0xc6a5cc): the same with kind 9, scale (1, 1, 1). See section 2.
- Attack: `0x9ab120(shell, 0x102b3d0, 0x102b370, 0x102bad8[sub] = 33 / 39, 31, 2)`. This is em089's arm call
  `arm(self, 0, hds, -1, 31, 2, ...)`.
- +0x2b0 sound timer = 600.0.
- Sound case 0xc6abe8 (shared with 13 / 40 / 46-49): `0x304c34(*0xfccd6c, 201, owner, 3, area, -2)`. This is a one-shot
  type-8 SE at the position of **owner joint id 3** (0xb054ac; falls back to the owner position W+0x198).
- Then +0xf4 = 0, +0x2b4 = 0, and a tail call to per-frame slot 23. So the first placement and the first 205 / 210
  happen inside init.

### 1d. Per frame 0xc6ac64, case 0xc6be68 (38 and 49 share it) (C)
1. Owner gone (0x917620): end.
2. +0x1c0 = 100.0. It is the z of a vector at +0x1b8, read by the unit / model code (0x6cee58). G: bounds. em089 does
   not port it either.
3. J = jointPos(131) (0x93093c). M = joint matrix (0x930894).
4. **Q** = J + M (off.x, off.y, off.z + V), where V = volume record +0x18 = 0 for volumes 19 and 21.
5. **P** = J + I Ry(+0x294) Rx(+0x290) (off.x, off.y, off.z + V + length):
   - I = 0x10e6448 = the identity matrix. It is the shared identity: 185 references, and the matrix inverse
     (0xd99ea8) returns it for a zero determinant (S).
   - So the far point is in **world axes**, built from the frozen spawn yaw and pitch. Only J follows the head.
   - The rotation helpers are rotX 0xaad560 then rotY 0xaad5b0, the same as em089. Positive x = pitch down.
6. +0x10c = +0x12c = 0. Branch to the common tail 0xc6e8d4 (r8 stays 0, so life always counts down):
   - sound function 0xc6e9b4 (1e)
   - life -= owner motion step (0x94460c, clamped at 0)
   - **end** (+0xf1 = 2) when owner motion != +0x2a0 (7/70's motion 0x455) or life <= 0
   - angles from d = P - Q: +0x110 = atan2(-dy, |d.xz|), +0x114 = atan2(dx, dz), +0x118 = 0
7. There is **no** map segment test, ground post, camera shake, booms, or life <= 10 end effect.
8. Shell base move 0x9aae2c, after the state slot: rotation from +0x110..+0x118 (0x6d4708), then +0x40 = P. The
   shell unit's transform is (P, segment angles).

### 1e. Sound 0xc6e9b4, case 0xc6ee98 (shared with 13 / 40) (C)
- +0x2b0 += shell dt (0x9a95c0).
- pt = the point of segment P -> Q nearest the listener (0xaf79a4 object +0xe30 + 16, 0xbdf918 / 0x1dfddc). This is
  the same as em089's s016_sound.
- If timer >= 30.0: timer = 0, then start **205** and **210** at pt (0x312484 = GU 0x4efb98, em089_snd_pos).
- Else: move 205 and 210 to pt (0x301074 = GU 0x4eff24, em089_snd_move).
- The timer starts at 600, so both start on the init's per-frame call. They never restart within life 21.

em092 request (S; rule: key k = entry k-1 of the bank group, as em089's rid 203 = oil_flow follows):

| rid | group / key | sound |
|---|---|---|
| 201 | 20 / 1 | em092_se_shell_start |
| 205 | 20 / 3 | em092_se_shell_loop |
| 210 | 20 / 7 | em092_se_ice_Crush |

All three are in em092's 4U request, which tools/snd4u2gu converts in full (rids kept).

GU has no mapping for 0x304c34. Use em089_snd_pos(owner, 201, jointPos(owner, 3), area) (S).

### 1f. End slot 24 0xc6f588 (C)
Only the base end (0x9ab16c). The 205 / 210 sounds are not stopped.

### 1g. Compared with em089_shell016.c (what must change to add 38 / 49)
| item | em089 | 38 / 49 |
|---|---|---|
| joint | 3 (hard-coded) | **131** |
| length | 10000 | **4000** |
| offset | (0, 0, 0) / (0, -50, 130) | **(0, -60, 0)** |
| x angle | fixed per subtype (k_sub.xang) | **per post**: clamp(a - x_prev) from the site, + owner x |
| far point | J + M Rx(x)(off + len) (joint axes; 53: + Ry in joint axes, flattened) | **J + Ry(yaw) Rx(x)(off + len) in world axes**, no flattening; new placement mode |
| re-placed | 36 / 53 once, others every frame | every frame |
| life / records | table | **21 / 33, 39** (new HDS + HTS, section 4) |
| extras | 41 / 51 / 52 / 54-56 map tests, ground posts, booms, shakes, end effects | **none** (like em089's 36 / 37 / 53 path) |
| effect | uEffect002 (0xc0b470) 48 / 50 / 53 / 54 | **uEffect015** (0xc07ecc) em092_001 k1 + end em092_200 (section 2) |
| sounds | per frame 209 or 201 (+ 202 repeat) | **201 at init (joint 3)**, then per frame 205 + 210, start once and move |
| end, angles, owner step, +0x1c0 | | identical (+0x1c0 not ported in either) |

The post API needs joint, offset, length and x angle per call (em089_shell016_post takes only subtype and offset).

## 2. Effects

### 2a. The uEffect015 class (C)
- 0xc07ecc is effect-manager event 15 (0xc0765c -> 0xc079c8).
- Class **uEffect015**: DTI 0x10b5c9c, 232 B, vtable 0xe5c124.
- Functions: ctor 0x1c538c, init slot 18 0x1c4da0, per frame slot 19 0x1c4fd0, ending slot 20 0x1c4b84.

### 2b. Which EFL (C)
- Kind -> u16 {group, file} at 0xfd16ac. Kinds 7 / 8 / 9 = 0x0144, so group 68 (the em092 list of the flat EFL table
  0xef895c), index 1 = **effect\efl\em\em092\em092_001**.
- Kind table 0xfd16d0 (20 B per kind): kinds 7 / 8 / 9 have flags 0x16 and element mask 1 / **2** / **2**. So 38 / 49
  play only element group 1 (PEL k = 1).
- For comparison, ZM 13 / 47 use kind 1 = 0x0121 = em022_001, mask 1.

### 2c. Placement (C, except where tagged)
- Init attaches the effect to the shell: (eff vt+0x48)(eff, shell, -1).
- Flag 4 set: 0x1c4d48 sets the effect's local offset (eff+0x160) = zero - (0, 0, |P - Q|).
  - The shell's origin is P, with its z axis along Q -> P, so **the effect sits at Q (the mouth), pointing along the
    blast**, and follows the shell every frame.
  - The offset is set once at init (flag 32 clear), so it is a fixed length.
- Scale (transform +0x60) = (0.8, 0.8, 1.0) for 38, (1, 1, 1) for 49. The parent is the shell (scale 1), not the
  monster.
- Colour: none. Neither EFL has a colour block, so there is no area tint.

### 2d. End (C, except where tagged)
Once the shell is no longer in state 1 / 2, slot 19 runs these steps in order:
1. 0xc4800c(eff, 0): stop emitting.
2. Effect state 2.
3. 0xc470dc(eff): release.
4. For kinds 7 / 8 / 9: `0xc0a614(mgr, 49, area, eff, ...)` = event 2 = **uEffect002 id 49**.
   - Its table entry 0x1b3364[49] = 0x1644 = group 68 file 22 = **effect\efl\em\em092\em092_200**.
   - All elements (mask -1), offset and rotation 0, scale 1, event +0x40 = 3.0 (G: duration).
   - It is attached to the released effect (init case 0x1b3590), so it plays at the shell's last Q and direction.

### 2e. In our arc
- Both EFLs are in 4U em092.arc's own family. effect_set converts every file under `effect\efl\em\em092\`.
- C (checked in the built em067_01.arc): em092_001, em092_200 and their dependencies are in it (ef_em092 MOD + MRL,
  em092_001_BM_NOMIP, qe001_BM_NOMIP, cm000_GSM_HQ_NOMIP).
- **No MEF record names group 92 file 1 or 200**: these effects are only posted from code, so the PEL has no record
  for them. They need `extra` records in effects() (today `extra=[]`).
- Caveat: effects() passes `list2` = GU's list 2. So extra records land in list 1 only, while em089_efx_post reads
  list 2. Append them to list 2 as well (the ball_fx_list2 path), with ids clear of GU's (0, 1, 10, 11, 30, 31, 60,
  and the class's >= 1000).
- Records:
  - em092_001, joint -1, k 1, scale (0.8, 0.8, 1.0) (38)
  - the same with scale 1.0 (49)
  - em092_200, k -1, scale 1.0 (end)
- Posting: em089's beam style. Post a world record at Q with the segment's pitch / yaw, move it every frame
  (em089_efx_shell016_move pattern), and use PEL_TAIL, not pel_follows. The net 4U placement is Q, not the shell
  origin.
- The model-scale caveat in efl4u2gu (records posted through the monster) applies here too (S).

### 2f. Bonus: TS 40 / 48 (shells.md 5c.1, C)
- Kind 7 = em092_001 element mask 1 (k 0), with scale (0.3, 0.3, 0.5) for 40 and (0.3, 0.3, 0.25) for 48.
- The same em092_200 post plays at their end.
- GU's sp_02 ef params (30 / 31) have no em092_200.

## 3. this+0x8d20 and W+0x14b

### 3a. this+0x8d20
- Writers (C): this+0x8d20 / 0x8d24 / 0x8d28 = W+0x1a8 / 0x1ac / 0x1b0, the owner angle triple:
  - 0x955e74, enemy vtable slot 10 0x955e5c (runs after the move)
  - 0x94ce54, end of move slot 9 0x94cd6c (one branch)
- Meaning: the angles as of the last move end, i.e. the drawn / previous-frame angles.
- Other uses: uEm022 0x74a8f0 reads it with this+0x40 (model position) to place a post. The shell at 0xc5574c copies it
  into its own angles.
- Effect in 7/70 (S): final pitch = clamp(a - x_prev) + x_now. The clamp is relative to the body pitch; the result is
  a world pitch, consistent with the world-axes far point.
- GU: the snapshot copy was not found (GU slot 9 0xc9eb8 -> 0xad7b4 has no obvious copy). Use rec+0x50 (REC_ANGLES x)
  for both terms: `xang = (clamp16(a - x) + x) & 0xffff`, and yaw = rec+0x54. The error is one frame of pitch change;
  7/70 step 1 only turns the yaw (S).

### 3b. W+0x14b
- C: byte copy of [stage / quest manager]+0xc8c, written at enemy setup (0x91bad8, 0x94e81c). The same manager's
  +0xc90 is the area copied into W+0x14c.
- uShell016's own subtype-3 case tests the same +0xc8c (== 9).
- 17 = 4U Dunes (content-data.md quest +0xC4).
- No night id (S): the 4U ROM has only `m17d` Dunes data, no `m17n`. m18 is a different stage (grass textures).
- GU: `[[MAIN+0x188ca48]+0x48] == 5` -> 38, else 49. Whether GU uses another id for Dunes at night was not checked (G).

## 4. GU hit data (hds_entry rules)
- byte 0x1c = **6**: em089 shell_hds turns 4U 0 into 6 for its uShell016 records, and GU's own sp_02 entry 0 also has
  6.
- byte 0x12: 4U 0x14 -> 0, and +0x2c = 5.
- byte 0x19 = the HTS group the caller assigns.

| record | 4U address | 4U 40 B |
|---|---|---|
| 33 (38) | 0x102b8f8 | `07000e00500002000000003c11000000000014000000000000130200000000000000000000000000` |
| 39 (49) | 0x102b9e8 | `07000e00500002000000003c11000000000014000000000000150200000000000000000000000000` |

Both records:
- window 7 + 14 (frames 7..21), power 80, type 2, u16 +8 = 0
- +0x0b 0x3c, +0x0c 0x11 (the TS flag of record 38), level 5
- volume 19 / 21

GU HDS (56 B; byte 0x19 still holds the 4U volume, to be remapped):
- 33: `07000e00500002000000003c110000000000000000000000001302000600000000000000000000000000803f050000000000000000000000`
- 39: `07000e00500002000000003c110000000000000000000000001502000600000000000000000000000000803f050000000000000000000000`

HTS groups: one capsule each, bone 1001, shape 1. GU record = 4U 40 B + 8 zero bytes, with +0x0a = 0x0848 (em089's
rule).
- vol 19 (0x102b230), **r 208**: `e90300000100000000004808000050430000000000000000000000000000000000000000000000000000000000000000`
- vol 21 (0x102b2d0), **r 260**: `e90300000100000000004808000082430000000000000000000000000000000000000000000000000000000000000000`

Both have +0x18 (the z shift added to the offset) = 0. The capsule is the segment Q -> P: GU this+0x1000 -> this+0x40,
as in em089. Put the entries in the family our class loads; GU's sp_02 uses entry 0 and groups 0 / 1, so append.

## 5. Multiplayer
Nothing in 38 / 49 is controller-only (C):
- No W+0x1d9 test in the post, ctor, init, per-frame, sound or uEffect015 paths. There is no RNG.
- Inputs:
  - the target slot rec+0x1d0 (synced in the action message, S)
  - the stage id (global)
  - the owner's joint and angles (position sync)
- The listener-nearest sound point is local (cosmetic).
- Post on every machine from the handler, as em089 does. Each machine tests its own hunters against the capsule.
