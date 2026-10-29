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
| 11, 12, 13, 14 | 5, 6, 7, 8 | +x arm: clavicle, upper arm, forearm, hand (14 = the hand holding the weapon) |
| 15, 16, 17, 18 | 9, 10, 11, 12 | -x arm |
| 3, 4, 5 | 14, 15, 16 | +x leg: thigh, knee, foot |
| 6, 7, 8 | 17, 18, 19 | -x leg |

GU's common motions also key bones 13, 20, 21 (not used by weapon classes' motion lists). GU armor models carry
only the bones they use (body 19 of them); the full set comes from all five parts.

## Weapon grip (C on the motion data; MHF's attach code not located yet)
The weapon's bones 0-2 are never keyed; the weapon motions key bones 3-10 below them (bone 3, the core block, is
keyed in the frame of the hand holding the weapon). That is mostly player bone 14 (+x hand, GU bone 8): the other hand
slides along bone 14's local +z in both modes (in bone 14's frame bone 18 sits at (-1, -3, 78) cm in Cutting idle,
31-78 cm along +z through Vertical 1, (-6, -1, 34) in Impact idle), never along an axis of bone 18. Over the 157 body
motions with a weapon motion, the off hand is within 8 cm of the weapon surface (median over the motion) in 106 with
bone 14 and in 9 with bone 18; the rest are one-handed moments (runs, leaps, throws) either way.
**MHF passes the weapon between the hands mid-motion**, and the keys follow the holding hand. The fists (body mesh,
vertices of bones 14 / 18) sit at (+8.3, -0.7, 0.6) / (-8.3, -0.7, 0.7) cm in their bone's frame, and the keyed bar
crosses the weapon root's frame through one of them: at x = +8 (bone 14) or x = -6.8 (bone 18); Finishing Slash
(1035) at -6.8 up to frame 102, then +8.1. `tools/msgrip.py` gives the holding hand per frame (keep it unless the
other fist is within 6 cm of the keyed weapon and 4 cm closer): 17 motions spend frames in bone 18 (1035 frames
0-102, 1043 frames 11-139, ...; the wind-ups 1406 / 1418 / 1446 that precede 1035 in actions 152 / 155 / 154 end in
it), and every clean switch (new fist 0.1-1.2 cm) comes while the other fist is on the weapon too, i.e. a hand-over.
No flag for it in the motion files (bones 0-2 carry no channels, no data after the tracks) nor in the action events:
MHF's switch mechanism is still to find (Phase 2 can run on msgrip's table meanwhile).
The Euler order holds on these grips: with R = Rz Ry Rx the free palm meets the bar within 5 cm on 34 % of 2232
sampled frames (median 6.5 cm), against 2-10 % (median 18-35 cm) for the five other orders.
Shapes in the hand frame (wk400):
- Cutting: rods 9 + 10 in one straight 2.8 m bar along +z, the "string" both hands hold; the blades (5 / 7, +-70 deg
  off bone 4, 60 cm out) bow out to one side like the limbs of a bow.
- Impact: the rods folded parallel into a 1.4 m double shaft along +z (the grip), the blades parallel (the
  horseshoe) from 0.55 to 2.65 m, bone 4 keyed 250 cm out (the head block at 2.2-2.5 m).
Guard Counter (1034) lets the right hand go for the counter swing (29-34 cm off the weapon at frames 30-45, back by
frame 60): MHF's animation, the keys keep the weapon in the left fist. Not read yet (Phase 2): the sheathed placement.

## Weapon motions in MHGU (C)
No MHGU weapon arc (w00-w14) and no player class arc holds weapon motions: the player LMTs animate the player bones
only. Magnet Spike's horseshoe opens and closes in 163 MHF weapon motions, so the class will have to pose the weapon
model's bones itself from the MHF weapon keys (Phase 2 design).

## Preview (Phase 1 check)
`blender -b --factory-startup -P tools/mhf2blend.py -- OUT.blend BODY.fmod BODY.fskl WKDIR w13.aan w13w.aan
MOTION=NAME...` builds the MHF player (body, face, hair) holding a Magnet Spike, all motions on one timeline with a
marker per motion (dump/mhf/preview/ms_preview.blend: 17 motions, wk400). `--render DIR` writes PNG frames.
The weapon follows msgrip's holding hand; the motions chain their root motion as in game (each starts where the last
one ended, the camera follows), and the 20 frames between two motions keep the last pose for 6, then blend into the
next along the shortest arc: preview filler, not MHF transitions (those are the steps' blend frames).

## Models: `tools/fmod2gu.py` (Phase 1 pipeline proof)
FMOD (`tools/fmod.py`; strips, positions, normals, UVs, percent weights of skeleton bones) + FSKL -> GU MOD 0xD4:
the 11 FSKL bones with local matrices and inverse binds (cube quantisation folded in, as in GU's own models),
vertices in 0x14D40022, one strip per triangle, envelopes from mod4u2gu. The PNG texture (MHF `2.tex` = small header
+ PNG) -> GU BC3 albedo + BC4 alpha (`tools/tex.py`). `fmod2gu.py arc WKDIR TEMPLATE.arc OUT.arc` puts the MOD
and textures into a GU weapon arc in place of its own (template MRL kept): wk400 in Great Sword 001's arc parses
back clean (`armor4u2gu.check`). Still to do for real weapons: edge and proxy meshes, the MRL (materials from
MHF's), the attach offset on GU's weapon bone, all 40 models.
