"""msfxposts.py : where the Magnet Spike posts MHF's converted effects (mhffx2gu.py), from MHF's own post sites
(notes/effect-posts.md: addresses, conditions, bones, offsets; C there unless marked). Library for msbuild.py.

Two kinds of rows:
- MOTION posts: (key, frame, (set, id), bone, offset, gate). key = ('mot', MHF motion[, action filter]) or ('act',
  action) = the action's first motion; frame = motion frame (1/60 s; an MHF task tick t from a motion frame f0 =
  f0 + 2 t). The module (ms_act.c fx_posts) posts the row's PEL records once per motion run when MS_REACHED(frame),
  if the gate holds: 0 always, 1 Magnetise on in the current mode (MHF M), 2 off.
- EVENT posts: name -> [(delay frames, (set, id), bone, offset)], queued by the module at the event (ms_act.c
  fx_queue): 'GUARD' (action 14 with < 2 guard hits), 'GUARD112' (Impact guard 112), 'CHARGED' (Triple Strike level
  1), 'RELEASE' (its second threshold), 'EARLY' (released before level 1).
Bones: MHF hunter bones (0 = floor = the hunter's own frame: no joint; 10 = S upper body; 14 / 18 = the hands) ->
GU joints by msmot.BODY_MAP; MHF HP(x, y, z) = bone 0 + R(yaw) (x, y, z) = joint none + offset; a TASK post keeps
its bone (S: GU's joint-attached record follows it as MHF's re-read matrix does). MHF's single-player view: the
"not O" branches (other hunters' clients) are left out.
Carriers posted by the module (EVENT_POSTS 'MARKER' / 'SHOT' / 'TRAIL'): fc5 0xe / 0xb / 0xa. Not posted yet
(module work): the other carriers that follow the marker / beams / weapon matrix (fc5 0 / 2 / 7 / 0x4d at the marker
/ 0x4e / 0x28, fc6 0x10 / 0x12 / 0x22 / 0x1e, Magnetise fc5 0x55-0x58), the pin's,
event 17's hand piece (no effect id: three model meshes)."""

ANY = 0xffff
SHOCK_HIT = [(0, 0xfc6, 0x2d, (-90, 0, 0)), (0, 0xfc6, 0x2d, (-120, 0, 80)), (1, 0xfc6, 0x2d, (-130, 0, 130)),
             (1, 0xfc5, 0x54, (-30, 140, 250)), (3, 0xfc6, 0x2e, (-120, 0, 170)), (5, 0xfc6, 0x2e, (-90, 0, 250)),
             (6, 0xfc6, 0x2f, (-30, 0, 400)), (8, 0xfc6, 0x30, (40, 0, 550))]          # MS task 0xf (t, ...)
SHOCK_WHIFF = [(0, 0xfc6, 0x32, (-150, 0, 0)), (1, 0xfc6, 0x32, (-180, 0, 70)), (1, 0xfc5, 0x53, (-30, 140, 250)),
               (2, 0xfc6, 0x32, (-170, 0, 140)), (3, 0xfc6, 0x33, (-110, 0, 270)), (5, 0xfc6, 0x34, (-20, 0, 450))]
DOUBLE_SWIPE = [(0, 0xfc6, 0x32, (-40, 0, -120)), (0, 0xfc6, 0x32, (-190, 0, -50)), (1, 0xfc6, 0x32, (-180, 0, 110)),
                (3, 0xfc6, 0x32, (-80, 0, 270)), (4, 0xfc6, 0x33, (150, 0, 260))]   # MS task 0x11, gate O and M


def _task(rows, key, f0, gate=0):
    return [(key, f0 + 2 * t, (s, i), 0, off, gate) for t, s, i, off in rows]


MOTION_POSTS = (
    # Magnetic Shock: hit 159 / 160 (f8 of 1031 / 1032), 162 (1082 from its first update); whiff 95 / 96, 161
    _task(SHOCK_HIT, ('mot', 1031, 159), 8) + _task(SHOCK_HIT, ('mot', 1032, 160), 8) +
    _task(SHOCK_HIT, ('mot', 1082, 162), 0) +
    _task(SHOCK_WHIFF, ('mot', 1031, 95), 8) + _task(SHOCK_WHIFF, ('mot', 1032, 96), 8) +
    _task(SHOCK_WHIFF, ('mot', 1082, 161), 0) +
    _task(DOUBLE_SWIPE, ('mot', 1424), 20, gate=1) + [
    # attraction: MS task 0x12 (Cutting 58 / 61 / 62) / 0x13 (Impact 68 / 71 / 72) from the action start, t1 / t3
    *[(('act', a), 2, (0xfc5, 0x3), 14, (30, 0, -20), 0) for a in (58, 61, 62)],
    *[(('act', a), 6, (0xfc5, 0x4), 14, (30, 0, 150), 0) for a in (58, 61, 62)],
    *[(('act', a), 2, (0xfc5, 0x3), 14, (20, 0, 140), 0) for a in (68, 71, 72)],
    *[(('act', a), 6, (0xfc5, 0x4), 14, (-10, 0, 170), 0) for a in (68, 71, 72)],
    # the approach motions: fc5 5 at f10, fc5 1 at f30 on the hand (60, 0, 60) in 1472, else (0, 0, 170)
    *[(('mot', m), 10, (0xfc5, 0x5), 14, (60, 0, 60) if m == 1472 else (0, 0, 170), 0)
      for m in (1069, 1079, 1414, 1415, 1460, 1472)],
    *[(('mot', m), 30, (0xfc5, 0x1), 14, (60, 0, 60) if m == 1472 else (0, 0, 170), 0)
      for m in (1069, 1079, 1414, 1415, 1460, 1472)],
    # repulsion: MS task 0xb (66) / 0xc (67) from the action start: t2 fc5 1 on the hand, t3 fc5 0x4d ahead / up
    (('act', 66), 4, (0xfc5, 0x1), 14, (60, 0, 60), 0), (('act', 67), 4, (0xfc5, 0x1), 14, (0, 0, 170), 0),
    (('act', 66), 6, (0xfc5, 0x4d), 0, (0, 100, -100), 0), (('act', 67), 6, (0xfc5, 0x4d), 0, (0, 100, -100), 0),
    # Guard Counter success (motion 1034 f32)
    (('mot', 1034), 32, (0xfc5, 0x38), 0, (30, 140, 250), 0), (('mot', 1034), 32, (0xfc5, 0x14), 0, (30, 140, 250), 0),
    # Charged Strike (35, motion 1082)
    (('mot', 1082, 35), 4, (0xfc5, 0x3), 14, (10, 0, 160), 0),
    (('mot', 1082, 35), 10, (0xfc5, 0x3), 0, (120, 160, 30), 1),
    (('mot', 1082, 35), 20, (0xfc5, 0x3), 0, (-10, 230, -30), 1),
    *[(('mot', 1082, 35), f, (0xfc5, 0x15), 14, (10, 0, z), 0) for f, z in ((36, 80), (44, 160), (52, 240))],
    (('mot', 1082, 35), 60, (0xfc5, 0x14), 0, (0, 130, 200), 0),
    (('mot', 1082, 35), 60, (0xfc5, 0x3b), 0, (0, 130, 200), 1),
    (('mot', 1082, 35), 60, (0xfc5, 0x37), 0, (0, 130, 200), 2),
    # Supplex second motion 1062
    (('mot', 1062), 40, (0xfc6, 0x11), 10, (0, 0, 0), 1),
    (('mot', 1062), 68, (0xfc5, 0x3), 14, (70, -50, 130), 1),
    (('mot', 1062), 78, (0xfc5, 0x3), 14, (-30, -40, 130), 1),
    (('mot', 1062), 104, (0xfc5, 0x3a), 0, (0, 100, 300), 1),
    (('mot', 1062), 104, (0xfc5, 0x30), 0, (0, 100, 300), 2),
    # Magnetic Assault (Leap): Cutting 1012, Impact 1013
    (('mot', 1012), 44, (0xfc5, 0x39), 0, (-20, 120, 250), 1),
    (('mot', 1012), 44, (0xfc5, 0x3e), 0, (-20, 120, 50), 2),
    (('mot', 1012), 46, (0xfc5, 0x22), 0, (0, 0, 250), 2),
    (('mot', 1012), 46, (0xfc5, 0x5e), 0, (0, 0, 250), 1),
    (('mot', 1012), 48, (0xfc5, 0x45), 0, (10, 100, 150), 1),
    (('mot', 1013), 44, (0xfc5, 0x3d), 0, (-30, 180, 70), 2),
    (('mot', 1013), 46, (0xfc5, 0x22), 0, (30, 0, 250), 2),
    (('mot', 1013), 46, (0xfc5, 0x5e), 0, (30, 0, 250), 1),
    (('mot', 1013), 48, (0xfc5, 0x45), 0, (20, 100, 200), 1),
    # Magnetic Double Slash 1045
    (('mot', 1045), 62, (0xfc5, 0x4f), 0, (0, 110, 50), 1),
    (('mot', 1045), 62, (0xfc5, 0x40), 0, (0, 140, 70), 2),
    # Finishing Slash lead-ins 1406 / 1418 / 1446
    *[(('mot', m), 6, (0xfc6, 0x11), 10, (0, 0, 0), 1) for m in (1406, 1418, 1446)],
    *[(('mot', m), 20, (0xfc5, 0x3), 0, (70, 80, 0), 1) for m in (1406, 1418, 1446)],
    *[(('mot', m), 30, (0xfc5, 0x3), 0, (-60, 140, 0), 1) for m in (1406, 1418, 1446)],
    # Magnetic Pin slam 1421 (f30; MHF: only within 200 of the ground, S), Pin Finisher 1488
    (('mot', 1421), 30, (0xfc5, 0x1a), 0, (0, 50, 100), 0), (('mot', 1421), 30, (0xfc5, 0x1c), 0, (0, 0, 100), 0),
    (('mot', 1488), 184, (0xfc5, 0x5d), 0, (0, 0, 170), 0),
    # Guard Assault 1410
    (('mot', 1410), 30, (0xfc5, 0x3d), 0, (-30, 160, 90), 1),
    (('mot', 1410), 34, (0xfc5, 0x5e), 0, (0, 0, 300), 2), (('mot', 1410), 34, (0xfc5, 0x30), 0, (0, 120, 300), 2),
    (('mot', 1410), 34, (0xfc5, 0x3a), 0, (0, 120, 300), 1),
])

EVENT_POSTS = {
    'GUARD': [(0, (0xfc5, 0x46), 14, (30, 0, -70)), (0, (0xfc5, 0x47), 14, (40, 0, 100)),
              (8, (0xfc5, 0x15), 14, (30, 0, -100)), (12, (0xfc5, 0x15), 14, (60, 0, 10)),
              (16, (0xfc5, 0x15), 14, (30, 0, 100))],
    'GUARD112': [(0, (0xfc5, 0x16), 0, (0, 120, 100)), (0, (0xfc4, 0x2), 0, (0, 0, 100)),
                 (0, (0xfc5, 0x15), 14, (0, 0, 40)), (12, (0xfc5, 0x15), 14, (0, 0, 100)),
                 (24, (0xfc5, 0x15), 14, (0, 0, 170))],
    'CHARGED': [(0, (0xfc6, 0x11), 10, (0, 0, 0)), (8, (0xfc5, 0x15), 14, (0, 0, 40)),
                (16, (0xfc5, 0x15), 14, (0, 0, 80)), (24, (0xfc5, 0x15), 14, (0, 0, 120))],
    'RELEASE': [(0, (0xfc6, 0xe), 10, (0, 0, 0))],
    'EARLY': [(0, (0xfc6, 0x13), 10, (0, 0, 0))],
    # carriers (ms_act.c fx_at, posted at a world point and moved every tick; not queued): the marker (special #2,
    # 0x101e938a), the shot (special #1, 0x101e9059), its trail points (special #9, 0x101eb0a1)
    'MARKER': [(0, (0xfc5, 0xe), 0, (0, 0, 0))],
    'SHOT': [(0, (0xfc5, 0xb), 0, (0, 0, 0))],
    'TRAIL': [(0, (0xfc5, 0xa), 0, (0, 0, 0))],
}


# MHF's per-motion effect keys (C: mhfdat header u32 0x618 -> per weapon type {i32 count, records*}, Magnet Spike =
# 13; record {u16 motion, u16 count, u32 keys*} sorted by motion, binary-searched by 0x1099b180; key 16 B {u16 frame,
# u16 kind, u16 a, u16 b, u8 c, u8 d, s16 x, y, z}, fired when the motion frame crosses it (0x1099af70) through the
# handlers 0x11a42488[kind] (P, a, b, c, d, x, y, z). Effect kinds, a = set, b = effect id, c = bone (0-20 the
# hunter's, 21+ = weapon bone c - 21 via 0x10999ce0 -> 0x1032bb60), d = follow mode (0x1099a720):
#   2 (0x1099a7f0) at the bone, its matrix copied once: fixed; 3 (0x1099a890) on the bone, re-read: follows;
#   6 (0x1099ad50) Translation(x, y, z) x the bone matrix, copied once: fixed; 7 (0x1099ae30) the offset re-applied to
#   the bone each tick: follows; 4 / 5 (0x1099a970) the bone's position snapped to the ground (0x108cbe30), fixed
#   (5 also tests the ground's presence, 0x108cf000, not a gate). Kinds 0 / 1 = sounds (S: 0x11413d70 / 0x114252b0),
#   8 = the face slots (0x1099af40 -> 0x10886860: blinks), not effects.
# Modes: 'att' = a PEL record on the joint (follows); 'fix' = posted at the joint's world point and rotation at that
# frame (ms_act.c); 'gnd' = at the joint's point on the ground, the hunter's yaw. MHF's d (3 / 4 = position only +
# the hunter's yaw, 5 = no update) is left out: S deviation for those rows (they follow the joint's rotation).
KEY_KINDS = {2: 'fix', 3: 'att', 4: 'gnd', 5: 'gnd', 6: 'fix', 7: 'att'}


def motion_keys(dat, weapon_type=13):
    """mhfdat bytes -> rows (('mot', motion), frame, (set, id), bone, offset, gate 0, mode)"""
    import struct
    t = struct.unpack_from('<I', dat, 0x618)[0]
    n, p = struct.unpack_from('<iI', dat, t + 8 * weapon_type)
    out = []
    for i in range(n):
        mot, k, ptr = struct.unpack_from('<HHI', dat, p + 8 * i)
        for j in range(k):
            f, kind, a, b, c, d, x, y, z = struct.unpack_from('<HHHHBBhhh', dat, ptr + 16 * j)
            if kind in KEY_KINDS:
                off = (x, y, z) if kind in (6, 7) else (0, 0, 0)
                out.append((('mot', mot), f, (a, b), c, off, 0, KEY_KINDS[kind]))
    return out


def effects(dat=None):
    """every (set, id) the rows post (with the per-motion keys when mhfdat is given)"""
    out = {r[2] for r in MOTION_POSTS} | ({r[2] for r in motion_keys(dat)} if dat else set())
    for rows in EVENT_POSTS.values():
        out |= {r[1] for r in rows}
    return sorted(out)
