# Magnet Spike assets: motions and models (MHF -> MHGU)

C = confirmed on the files, S = inferred. Local inputs (gitignored): dump/mhf/motion/{w13,w13w}.aan,
dump/mhf/player/{m,f}_editpl.* (character-edit body: parts 0 FMOD, 1 FSKL, 2 textures), dump/mhf/weapon/wkNNN/
{0.fmod, 1.fskl, 2.tex} (the 40 Magnet Spike models).

## Motions (C)
- `w13.mot` (AAN, `tools/aan.py`): 3 groups = part pairs; even part = bones 0-8 (root + legs), odd = 9-20 (spine,
  arms, head). Motion ID 1000 + part * 100 + slot. `w13w.mot`: the weapon's own motions, part P slot S = the body
  motion of part P slot S (parts 0 / 2 / 4 hold 81 / 4 / 75 motions; part 1 holds 3 more).
- Values (Paxlord's plugin, matched by the preview): short rotation x 2 pi / 16384 (16384 = one turn), Euler,
  absolute local values (not deltas from the rest pose); short translation / 16 = cm; Hermite keys (value, frame,
  tangent in, tangent out), tangents per frame. Bone 2 (hips) keys its absolute height (~88 cm) above the root;
  bone 1 carries the root motion (Vertical 1 moves 88 cm forward). The skeleton's rest origin is the hips.
- Euler order / sign: R = Rz Ry Rx, standard right-handed (checked on the weapon: arm bone 5's local +Z turned by
  its -40 deg rest rotation points along its 252 vertices).
- Frame rate: the preview plays at 30 fps (Paxlord's choice). MHF timers count 30 per second (Magnetise 2400 =
  80 s); whether motion frames advance 1 or 2 per tick (the per-layer speed at player +0x1e0 + 0x50 n) is still
  open (S: 30).

## Skeletons (C)
MHF player (FSKL, 21 bones) and MHGU player (bone ids 0-19 + root track 255 in GU's LMTs) are the same skeleton,
offset for offset (cm), except the spine (14.4 vs 15.4) and the head (12.3 vs 12.8):

| MHF | GU | bone |
|---|---|---|
| 0, 1 | 255 | root (floor; root motion) |
| 2 | 0 | hips (parent of the legs) |
| 9, 10 | 1, 2 | spine base, spine |
| 19, 20 | 3, 4 | neck, head |
| 11, 12, 13, 14 | 5, 6, 7, 8 | +x arm: clavicle, upper arm, forearm, hand |
| 15, 16, 17, 18 | 9, 10, 11, 12 | -x arm (18 = the hand holding the weapon) |
| 3, 4, 5 | 14, 15, 16 | +x leg: thigh, knee, foot |
| 6, 7, 8 | 17, 18, 19 | -x leg |

GU's common motions also key bones 13, 20, 21 (not used by weapon classes' motion lists). GU armor models carry
only the bones they use (body 19 of them); the full set comes from all five parts.

## Weapon motions in MHGU (C)
No MHGU weapon arc (w00-w14) and no player class arc holds weapon motions: the player LMTs animate the player bones
only. Magnet Spike's horseshoe opens and closes in 163 MHF weapon motions, so the class will have to pose the weapon
model's bones itself from the MHF weapon keys (Phase 2 design).

## Preview (Phase 1 check)
`blender -b --factory-startup -P tools/mhf2blend.py -- OUT.blend BODY.fmod BODY.fskl WKDIR w13.aan w13w.aan
MOTION=NAME...` builds the MHF player (body, face, hair) holding a Magnet Spike, all motions on one timeline with a
marker per motion (dump/mhf/preview/ms_preview.blend: 17 motions, wk400). `--render DIR` writes PNG frames.

## Models: `tools/fmod2gu.py` (Phase 1 pipeline proof)
FMOD (`tools/fmod.py`; strips, positions, normals, UVs, percent weights of skeleton bones) + FSKL -> GU MOD 0xD4:
the 11 FSKL bones with local matrices and inverse binds (cube quantisation folded in, as in GU's own models),
vertices in 0x14D40022, one strip per triangle, envelopes from mod4u2gu. The PNG texture (MHF `2.tex` = small header
+ PNG) -> GU BC3 albedo + BC4 alpha (`tools/tex.py`). `fmod2gu.py arc WKDIR TEMPLATE.arc OUT.arc` puts the MOD
and textures into a GU weapon arc in place of its own (template MRL kept): wk400 in Great Sword 001's arc parses
back clean (`armor4u2gu.check`). Still to do for real weapons: edge and proxy meshes, the MRL (materials from
MHF's), the attach offset on GU's weapon bone, all 40 models.
