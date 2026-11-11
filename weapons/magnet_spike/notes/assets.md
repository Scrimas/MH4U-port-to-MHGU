# Magnet Spike assets: motions and models (MHF -> MHGU)

C = confirmed on the files, S = inferred. Local inputs (gitignored): dump/mhf/motion/{w13,w13w}.aan,
dump/mhf/player/{m,f}_editpl.* (character-edit body: parts 0 FMOD, 1 FSKL, 2 textures), dump/mhf/weapon/wkNNN/
{0.fmod, 1.fskl, 2.tex} (the 40 Magnet Spike models).

## Inputs

What `tools/msbuild.py` reads from `dump/mhf/` (`tools/doctor.py` checks these, warn-only). They were extracted by hand,
with session scripts kept locally in `dump/scratch/magnet-spike-session/` (`ms_extract.py`, `mhfc.c`/`mhfc.py` = MHF's
ECD decryption and JPK decompression, `mhfarc.py`), so `tools/setup.py` has no step for them. `dump/mhf/SOURCES.txt`
records each file's source and SHA-1.

| File | Source |
|---|---|
| `motion/w13.aan`, `w13w.aan` | an MHF-ZZ PC client, `dat/motion/w13.mot` / `w13w.mot`, JPK-decompressed |
| `weapon/wkNNN/{0.fmod, 1.fskl, 2.tex}` | `dat/extend/wk000.abn` / `wk500.abn` entries: ECD, then a simple archive of JPK parts. The build uses wk400, 404, 407, 414, 415, 595, 606 |
| `player/m_editpl.{0.bin, fskl}` | the character-edit male body (parts 0 FMOD, 1 FSKL) |
| `zz/mhfdat.dec.bin`, `zz/mhfsdt.dec.bin` | `dat/mhfdat.bin` / `mhfsdt.bin` of the ZZ client "Monster Hunter Frontier Z PC [EN-CT4.1]", ECD-decrypted (CRC checked) |
| `ui/mhf_90c_04.png` | `dat/mhf_90c.bin.xbox`, PNG 4 (the HUD's gauge cell and horseshoe) |

Bringing these scripts into the repo would allow a `setup.py mhf` step from a client folder; not done yet.

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
- Frame rate: **motion frames are 1/60 s** (S, strong; 2026-10-29). MHF timers count 30 per second (Magnetise 2400 =
  80 s), so a game tick moves the motion two frames. Evidence:
  - The drawn run loops cover 4.3 m per stride cycle of 41-49 frames (1430 / 1435, foot plants by forward
    kinematics). That is 0.7-0.8 s per cycle at 60 fps, a running cadence; at 30 fps it would be 1.5 s with 2.2 m
    steps, i.e. slow motion.
  - The set-motion routine 0x10a92cd0 halves the step's blend (`blend / 2`) before storing it in a counter.

  The preview plays at 60 fps (Paxlord's plugin used 30). For GU's 30 fps lists, MHF frames, event frames and cancel
  windows divide by 2. To confirm with the first in-game walk.

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

## Weapon motions in MHGU (C, corrected 2026-10-29)
The player LMTs animate the player bones only, and the model arcs (weapon\wNN\%03d) hold no motions. The weapon
motions are separate arcs: arc/weapon/wNN/gMM.arc = weapon\wNN\mot\wgNN_MM (LMT), plus wgNN_sa_MM for Hunter Arts and
L / R lists for two-part weapons. All 14 classes have them, and each model's rPlayerWeaponList record (mGmkMotNo)
picks the set. The Magnet Spike's 163 MHF weapon motions therefore become one GU weapon list (wg05_00) instead of
code that poses the bones (Phase 2).

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

## Effects (MHF side, C unless marked; 2026-11-04)
- **Container**: `dat/effect.bin` = u32 count 20 + (offset, size) pairs; the client keeps it at 0x1ed528bc.
  - Entries 0-17 are texture sub-archives (u32 n, offsets; PNG data).
  - Entry 18 (header +0x94, JKR/JPK) = the effect-set container, unpacked and walked by 0x113d5910:
    - layout: u32 count, u32 type-table offset; (u16 kind, u16 set id) per entry; (u32 offset, u32 size) from u32 3;
    - kind 1 = a set, registered by 0x113d55b0 -> 0x113d4a70(data, size, set id) into the set table 0x1e8d31a8 (0x44-B slots, id at +0x38).
  - Entry 19 (+0x9c) goes to 0x108df7d0 (not read).
- **Sets**: 61 in ZZ, ids 0xbb8-0xbcc, 0xfa0-0xfc6, 0x1004-0x100a, 0x13ee-0x13ef. The player's are 0xfc5 (114504 B) and 0xfc6 (37868 B).
- **Set layout** (0x113d4a70):
  - header 14 x u16: version (> 3; 4 in ZZ), then section counts;
  - record sizes A 0x70, B 0x18, C 0x10, D 0x10, E 0x38, F 0x8c, G u16 list (+ 1), H 0x20, then the rest;
  - 0xfc6 = A 208, B 195, C 261, D 2, E 101.
- **Spawn**:
  - 0x113d61f0 (fastcall, edx = set id; stack: index, position, ...) finds the set and calls 0x113d35a0(set, index, ...);
  - index = an A record (0xfc6 A[0x11]: f32 position (0, -200, 320), 1.047 rad, ..., u16 +0x4c = 38, +0x4e = 4, +0x50 = 3: links into later sections; semantics not decoded);
  - a second request form 0x113d66b0(set, id, k, pos..., flags) -> 0x1146aa50 (a 0x40 task carrying the same set / id).
- **Motion effects**: 0x113d4c50 walks a motion-keyed table of 32-B records (+0xc motion, +0xe frame, +0x12 index, +0x14 set id, +0x16 flags) per action (+0x32c): MHF ties effects to motion frames as data (table source not located).
- **The MS code's posts**: about 60 (scratch inventory ms_effect_calls.txt).
  - Magnetic Shock task 0x1004d810: 0xfc5 0x4d / 0x14 / 0x54 / 0x53, 0xfc6 0x2d-0x34.
  - Triple Strike charge levels (0x10333d0c..): 0xfc6 0xe / 0x11 / 0xf.
  - Attraction / marker / pin (0x10332..0x10336): 0xfc5 0x16, 0x22, 0x30, 0x3a, 0x39, 0x3e, 0x40, 0x45, 0x4f, 0x5e, 0x5d, 0x1a, 0x3, 0x14, 0x15, 0x37, 0x38.
- **Plan** (port, maintainer's request after test 14):
  1. decode the set sections' meaning from the spawn / update / draw code (0x113d35a0 on);
  2. convert the textures (PNG -> GU RGBA8 .tex, as tools/efl4u2gu.py convert_tex);
  3. build GU EFL per MHF effect from GU template units (billboard particle / ribbon / mesh: tools/efl4u2gu.py knows the containers and block layouts), with MHF's colours, sizes, lifetimes, counts and velocities;
  4. post them where MHF does (msfx PEL ids, ms_act posts); they replace the GS stand-ins.
- **Effect runtime** (decoded 2026-11-04 except the F emitters):
  - **Effect** = every A record with A +0x50 == the effect id: the posted "index" is that id, not an A row. 0x113d3fc0 runs the timeline per frame:
    - each matching A spawns at its frame +0x4e: +0x58 particles, flags +0x54 (bit 0 = no particle);
    - particle definition = the E record whose +4 == A +0x4c; params A +0x48 / +0x5c / +0x52;
    - A floats 0x00-0x47 = position / rotation / scale bases and random ranges ("Emitter" below);
    - spawn = 0x113cd960 (plain), 0x113cd4b0, or 0x113cd9c0 (attached variants: unit, joint).
  - **Particle** (C, 0x113cd4b0 spawn, 0x113cda30 update, 0x113ce4d0 draw; tools/mhffx.py decodes all below):
    - a particle is a MESH of the effect model (effect.bin entry 0 part 0 = an FMOD of 446 meshes, part 1 its
      FSKL; textures = entry 1's 13 PNG atlases), drawn with a world matrix = scale x rotation (x the view
      matrix for the billboard flags E +0 bits 0 / 1 / 0x200) at its position. Loader 0x1089e0e0 -> 0x108f88e0:
      8 model packs (table 0x11a458e0: entry pairs 0/1, 2/3, 4/5, 8/9, 12/13, 16/17); pack 0 = the common one.
      Mesh -> material (FMOD dir 9, last u32 = texture index) -> texture (dir 0xa: u32 image index into the PNG
      list, width, height). Meshes are quads (28 of 446 are 4-vertex) or shaped strips / rings, with atlas UVs.
    - E (0x38): +0 flags (above; 4 / 0xc00 / particle flag 0x10 pick the render queue, 0x40 colour override,
      0x80 snap to the ground, 0x400 distance cull); +4 id (= A +0x4c); +6 == 1: the set's own pack; +8 mesh;
      +0xa D group (mesh flipbook; +0 frame, +8 mesh, random pick among frame-0 keys); +0xc life (scaled by the
      A life scale +0x5c when >= 1); B curves: +0xe position offset (in the particle's rotated frame, + the
      effect yaw), +0x10 rotation (degrees, added to the spawn rotation), +0x12 scale (x the spawn scale),
      +0x22 (-> particle +0x78, draw, meaning open), +0x26 (open); +0x16 UV mode (1 scroll u / v by 1 / +0x18,
      1 / +0x1c per tick; 2 u only; 3 v only; 4-6 flipbook of +0x18 cells over +0x1c frames; 7 UV from curve
      +0x18); +0x20 colour curve (C group); +0x24 second D group; +0x15 draw mode; +0x28 f32 alpha parameter.
    - B key (0x18): vec3 +0, i32 frame +0xc, u16 flags +0x10 (first key bit 0 = loop), byte curve id +0x12.
      Linear between keys, the end values outside (0x113ccd90). C key (0x10): i32 frame, u16 flags +4, byte
      group +6, RGBA bytes +8..+0xb (0x113ccaf0 packs A = +0xb, R = +8, G = +9, B = +0xa), linear.
    - Ages count 2 per MHF tick (1/60 s), the effect timeline too (A +0x4e).
  - **Emitter** A (0x70; 0x113d37e0 / 0x113d3bd0 / 0x113d3d80 / 0x113d3f00, C): position = base +0 + U(-1, 1) x
    range +0xc per axis (turned by the effect yaw); rotation (rad) = base +0x18 + U x range +0x24, wrapped to
    [-pi, pi]; scale = base +0x30 + U x range +0x3c (flag 2: one U for the three axes); flags 4 / 8 random mirror
    of x / y; flag 1 = spawn F records (0x8c, second emitter kind, 0x113d0ca0 family, not decoded) instead of E.
    The MHF RNG: r = r x 0xb0 mod 0xff53 (0x1ed5f2a2).
  - **Blend** (C, 0x113ce4d0 -> 0x10b705e0(src, dst) -> state 0x5e = table 0x1185df00[src] | 0x1185df28[dst]):
    E draw byte +0x15: 1 = source alpha / one (additive), 0 and 2 = source alpha / inverse source alpha (2 also sets
    state 0xd = 0x800); factor names S from use (124 sites pass dst 5, 52 dst 1). E flag 4 / 0xc00 only pick the
    draw list (0x113cdf82). The colour key packs D3DCOLOR ARGB with R = +8 (0x113ccaf0): RGBA bytes as stored, as GU's
    (em001_00_500 Rathian fire = 255 110 110). E +0x22 is not a colour scale: a camera-ward offset (0x113cd340,
    unprojected toward the eye, x the curve's z = 100-200 cm).
  - **F emitter** (A flag 1; spawn 0x113d0b60 -> task update 0x113d1950 / 0x113d2700, partly read, S): F +4 id
    (= A +0x4c), +0xc life; three vec3 parameters base + U x range: +0x14 / +0x20, +0x2c / +0x38, +0x44 / +0x50
    (the third is added to particle +0x60.. each tick and clamped at 0: a growth rate; the first two S velocity /
    acceleration, 0x113d2190 / 0x113d1b30 not read); curve +0xe; at its end it posts the child effect +0x7a of
    its set (0x113d35a0), and along its life the effects keyed in a D-like group (0x113cc970 -> 0x113d34f0 /
    0x113d47e0): a moving emitter that drops other effects (sparks with trails). GU: a particle unit with speed
    and child units.
  - **Mesh shapes** (2026-11-05, test 18, C from model0.fmod): the particle meshes are not all flat in x / y. Of
    the 942 converted particles (posted effects + per-motion keys) 538 use x / y-flat meshes, 131 meshes in the XZ
    or YZ plane (93, 121, 42, 401, 335, 334) and 273 3-D ones (arcs, rings, domes: 291, 337, 340, 53, 379, 61, 143,
    329). E flags & 0x203 == 0 (world-oriented): the mesh in the effect frame; otherwise the particle matrix
    (scale x rotation) times the camera matrix (0x113ce4d0). Port: mhffx2gu.model_unit / mhfmodel.py, bake view.
  - **The Magnet Spike's 35 posted effects** (sets 0xfc5 / 0xfc6): 513 particles. 431 have no position curve
    (they stay where they spawn, with the random spread, and only scale, turn, recolour). 52 move on one straight
    segment (2 keys = constant speed). 15 move on two segments (3 keys). 15 are F emitters. 0xfc6 0xf has no A
    record.
  - **Deviation rule (maintainer, 2026-11-04)**: GU particles move by speed / gravity / drag, MHF's by keyed
    paths. Any effect whose motion GU can only approximate (from the 3-key paths on, or anything the converter
    fits with an error above its tolerance) goes on the deviation list with its error; the converter prints that
    list.
- **Conversion** (tools/mhffx2gu.py, run by msbuild; GU format: notes/gu-efl-units.md), 2026-11-04:
  - each MHF particle = one GU Billboard entry cloned from em001_00_500 entry 0 (one particle, once, no motion);
    its MHF mesh baked into a sprite of one atlas (effect\base\ms_mhf_000 TEX + EAN), scale / colour curves from
    MHF's keys, the burst frame as an invisible lead-in (alpha 0, keys shifted), life in the emit block;
  - msbuild packs every converted effect into w05.arc (effect\pl\w05\ms_SSS_EEE[_k], <= 32 entries per file);
  - posts (msfxposts.py, from notes/effect-posts.md): PEL records from POST_BASE 3000, one block per (effect, bone,
    offset) = a record per MHF base-offset group with its entry mask and joint (msmot.BODY_MAP; bone 0 = none);
    ms_act.c fx_posts posts the motion rows (117) at their frames with MHF's Magnetise gate, fx_queue the event
    rows (guard, Impact guard, Triple Strike level 1 / overcharge / early release); GS's Magnetic Shock stand-ins
    are off when the table is on. Not posted yet: the carriers (marker, shot and trail, beams, Magnetise loops),
    the pin's, event 17's hand piece (effect-posts.md "Not posted yet" in msfxposts.py);
  - spawn spread: the MHF base offset = the record's position, the range = GU's box spawn shape (element +0x78
    byte 0 = 1, extents +0x60 / +0x68 / +0x70: 0xa5e450 case 1, C);
  - (2026-11-11) world-oriented 3-D meshes (not flat in x / y) -> GU Model units in effect draw on the mesh as a
    model (mhffx2gu.model_unit, mhfmodel.py); MHF's particle matrix = S, then RotationX / Y / Z (0x113ce4d0 ->
    0x10006ab0 / 0x10006a50 / 0x100069f0, D3DXMatrixMultiply on the right: column Rz Ry Rx, C) of the SUM of the
    post's Euler angles and the A spawn rotation (0x113d3bd0, C), the A position turned by the post's yaw
    (0x113d37e0, C); GU's = S . R(order 0 = the same Rz Ry Rx) . the emitter (gu-efl-units.md "Model transform").
    Equal for a post without rotation (fxplace.py: <= 2 cm, the key times rounded to whole GU frames); with a
    post yaw, MHF's Euler sum differs from GU's product wherever the spawn roll (z) is non-zero (S deviation);
  - the shot's hand piece (msgun.py, 0x1004f7b0, C): v -> bone 18 (origin + R (S v + p)), R = Rz Ry Rx: the part
    offset p is turned by the part's rotation (test 21 drew R S v + p: parts 15-50 cm apart, the barrel 90 deg off);
  - (older, flat meshes) world-oriented MHF meshes -> GU Polygons (type 2, template w04.arc cm121_041 entry 2; layout C 0xa9ff8c:
    rotation x / y / z pairs +0x170, width / height +0x1c0 / +0x1c8 with curves +0x1b0 / +0x1b4); rotation order G;
  - MHF UV animation (modes 2-6) -> baked frames on one looping EAN entry (flags 3, speed = 1 / frames per cell):
    flipbooks exact, scrolls as SCROLL_FRAMES (8) steps per cycle (deviation: choppier than MHF's smooth scroll);
  - 453 GU entries over the 35 effects (one 1024 x 1024 atlas, 28 cells / 106 frames). Not converted yet
    (gen/report.txt lists each): position curves (67 particles), F emitters (15), UV modes 7 / 1 (3 / 1);
  - deviations (until a test says otherwise): GU's billboard size unit is G (half extent in cm assumed); mesh
    overlaps baked with "max"; the GU volume setting may shorten fades.
- **GU side**: GU's generator classes (DTI names at 0x157816d..):
  - Billboard, BillboardStrip, SizeBillboard, LiteBillboard, MassBillboard, Polyline, LitePolyline, Polygon, PolygonStrip, LitePolygon, AxisPolygon, ClothPolygon, Texline, Trail, Line, Model, PrimModel, Point, Custom, Filter, Force, Hit, LensFlare, Light, LightShaft, Adhesion.
  - tools/efl4u2gu.py knows EFL containers / blocks only structurally. No public layout of their fields (searched 2026-11-04). Writing new MHF-shaped effects needs those fields decoded from GU's code (unit factory, the Billboard / Trail generators' parameter reads).
