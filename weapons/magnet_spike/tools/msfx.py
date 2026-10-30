"""msfx.py : the Magnet Spike's swing arcs and swing sounds as GU data (stand-ins: MHF's own effects and sounds are in
Frontier's formats, not converted; notes/phase3.md "Effects and sounds"). Library for msbuild.py.

Arcs (C unless marked): GU draws a swing as a ring mesh posted once per swing, no blade ribbon: the class PSL (kind 2)
posts a record of the class PEL's list 1, an EFL Model unit on effect\\base\\cm010_000 (GS's arcs, w00_000 units 0-3).
The ring lies in its y-z plane; texture v runs with theta = atan2(y, z) (v = (theta - 125 deg) / 360) and only v
0.56-1 is visible: a crescent from a sharp head at theta -26 deg back to a faded tail at 125 deg (GS's near-identity
record 2 = an overhead slash in front of the hunter), so the swing turns about the ring's +x. Every attack gets a
record of its own: the circle fitted to its blade tip (the hit capsule end farthest from the hand, on a weapon bone)
over the live frames (+ LEAD before) in the hunter's frame (MHF bone 1 = GU's unit) at the post (mid-window); +x on
the swing axis, the head on the tip at the post, scale = tip radius / the band's outer radius (MHF's swings: radius
1.4-4.5 m, sweeps 70-480 deg). GU's effect rotation 0x8a7dc4 case 0 = R = Rz Ry Rx (as MHF; S: PEL posts use
case 0).

Sounds: GU's per-motion sound sequence sound\\call\\pl\\pl_wp05 (rFestaSoundSequence, the copy of GS's pl_wp00):
records keyed by motion id 5000 + slot, events at motion frames, op 0x66 = a weapon sound of SRQR slot 2 (a = 1) or 4
(a = 0: GS's snd_wp_two_bcom). GS's records stay on the slots GS's own motions fill (GU_COPY, COMMON); ours get one
event per attack 2 frames before the hit: GS's whoosh_b (65) on the holding hand + its layered whoosh (fast 90 in
Cutting, slow 94 in Impact) on joint 2, as GS's slash 5110."""
import math, struct
import numpy as np
import msgrip, msmot

HEAD = math.radians(-26.0)    # the crescent's head on the ring (theta = atan2(y, z))
RING_R = 109.0                # outer radius of the ring's visible band (cm; texture u 0.6)
GS_REACH = 200.0              # GU's look: GS's crescents (scale 1, band out to RING_R) trail a blade reaching 260 cm
                              # (its capsules): a swing of tip radius r = scale r / GS_REACH (test 1: r / RING_R
                              # was "quite big compared to the weapon"; test 2: r / 260 "slightly too small", the
                              # user asked for in between: 200)
ARC_BASE = 1000               # PEL ids of the Magnet Spike's arcs (GS's list-1 ids end at 517)
ARC_TEMPLATE = 2              # GS's record copied (unit mask 4: its overhead slash's arc)
SHOCK_EFX = 1100              # PEL ids of the Magnetic Shock 5 x 3 spots (msbuild SHOCK; MHF effects 0x2e-0x30: S)
SHOCK_TEMPLATE = 105          # GS's charged slash ground impact (cm001_004, posted with its arc 0 at slot 106 f44)
# looks with no MHF counterpart converted (S): GS's charge flashes copied under ids its PTS does not tie a sound to.
# Code posts (vt+0x39c) read PEL list 2 (GS's: 500-517, its code-posted charge glows; list 1 = the PSL's): test 4,
# every code post asked list-1 ids and showed nothing (the marker's returned 0); CODE_EFX go to lists 1 and 2
MARKER_EFX = (1200, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.5, 9)          # the marker, posted at its point (ms_act.c)
AURA_EFX = (1201, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.6, 11, 8)        # Magnetise on: on the weapon hand (joint 8)
FLASH_EFX = {'CHARGED': (1300, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, 7, 8),     # Triple Strike charged (GS flash 7)
             'GUARD': (1301, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, 9, 8),       # guarded hit (flash 9)
             'MAGNETISE': (1302, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, 11, 8)}  # Magnetise on (flash 11)
LEAD = 4                      # frames before the hit the swing path starts
SND_LEAD = 2
WHOOSH_B, WHOOSH_FAST, WHOOSH_SLOW = 65, 90, 94


def frames_of(w13, mot):
    return int(msmot.body_chans(w13, mot)[0]['frames']) + 1


def euler_xyz(R):
    """R = Rz Ry Rx -> (x, y, z) in degrees"""
    y = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    return tuple(math.degrees(a) for a in (math.atan2(R[2, 1], R[2, 2]), y, math.atan2(R[1, 0], R[0, 0])))


def fit(P):
    """points -> (centre, axis right-handed with the motion, radius, swept degrees)"""
    m = P.mean(0)
    _, _, Vt = np.linalg.svd(P - m)
    e1, e2 = Vt[0], Vt[1]
    q = np.c_[(P - m) @ e1, (P - m) @ e2]
    D, E, F = np.linalg.lstsq(np.c_[q, np.ones(len(q))], -(q ** 2).sum(1), rcond=None)[0]
    cx, cy = -D / 2, -E / 2
    r = math.sqrt(max(cx * cx + cy * cy - F, 0.0))
    a = np.unwrap(np.arctan2(q[:, 1] - cy, q[:, 0] - cx))
    axis = np.cross(e1, e2) * (1.0 if a[-1] >= a[0] else -1.0)
    return m + cx * e1 + cy * e2, axis, r, abs(math.degrees(a[-1] - a[0]))


def arc(sw, wdata, holders):
    """one attack (msbuild.build_hits swings) -> dict(post, pos, rot, scl, sweep) or None (no swing: thrusts,
    blasts, hits not on the weapon)"""
    w13w, wbones, weapon, w13, bbones = wdata
    if not sw['tip']: return None
    mot, f0, bone, pt = sw['mot'], sw['frame'], sw['tip'][0], np.append(sw['tip'][1], 1.0)
    part, s = (mot - 1000) // 100, (mot - 1000) % 100
    mo = w13w[part].get(s)
    if not mo: return None
    n = frames_of(w13, mot)
    tr, body, hs = msgrip.tracks_of(mo, weapon.bones), msmot.body_world(w13, bbones, mot), holders.get(mot)
    fa, fb = max(0, f0 - LEAD), min(n - 2, f0 + max(sw['dur'], 1))
    Wp = [body(f)[hs[min(f, len(hs) - 1)] if hs else 14] @ msgrip.pose(weapon.bones, tr, f)[bone] @ pt
          for f in range(fa, fb + 1)]
    if len(Wp) < 3: return None
    # posted at the swing's fastest frame from the arming on (test 5: "even the crescent seems delayed": the
    # window's middle moved 7-12 frames later when test 3 doubled the live time)
    steps = range(max(f0 - fa, 1), len(Wp))
    if not steps: return None                       # armed on the motion's last frames: no swing left
    post = fa + max(steps, key=lambda i: np.linalg.norm((Wp[i] - Wp[i - 1])[:3]))
    U = np.linalg.inv(body(post)[1])
    P = [(U @ q)[:3] for q in Wp]
    c, axis, r, sweep = fit(np.array(P))
    if not 40.0 <= r <= 500.0 or sweep < 35.0: return None
    h = P[post - fa] - c                                # the head on the blade at the post: the arc trails it
    h = h - axis * (h @ axis)
    h /= np.linalg.norm(h)
    hl = np.array([0.0, math.sin(HEAD), math.cos(HEAD)])
    xl = np.array([1.0, 0.0, 0.0])
    R = np.c_[axis, h, np.cross(axis, h)] @ np.c_[xl, hl, np.cross(xl, hl)].T
    return dict(post=post, pos=tuple(c), rot=euler_xyz(R), scl=r / GS_REACH, sweep=sweep, r=r)


def pel_add(d, recs, code=()):
    """the class PEL (v15, lists 0 / 1 / 2) + list-1 records [(id, pos, rot, scale[, template id[, joint]])] copied
    from GS's list-1 record template (default ARC_TEMPLATE); `code` records (code posts) go to lists 1 and 2"""
    assert d[:4] == b'PEL\0' and struct.unpack_from('<I', d, 4)[0] == 15
    lists, i, tmpls = [], 8, {}
    for li in range(3):
        n = struct.unpack_from('<I', d, i)[0]
        i += 4
        start = i
        for _ in range(n):
            L = d[i]
            rec = d[i:i + 1 + L + 2 + 160]
            if li == 1: tmpls[struct.unpack_from('<H', rec, 1 + L + 2 + 0x30)[0]] = rec
            i += len(rec)
        lists.append([n, d[start:i]])
    assert i == len(d)
    for k, (rid, pos, rot, scl, *t) in enumerate(list(recs) + list(code)):
        tmpl = tmpls[t[0] if t else ARC_TEMPLATE]
        r = bytearray(tmpl)
        st = 1 + tmpl[0] + 2
        struct.pack_into('<3f', r, st + 0x00, *pos)
        struct.pack_into('<3f', r, st + 0x10, *rot)
        struct.pack_into('<3f', r, st + 0x20, scl, scl, scl)
        struct.pack_into('<H', r, st + 0x30, rid)
        if len(t) > 1: struct.pack_into('<H', r, st + 0x32, t[1] & 0xffff)      # joint
        for li in (1, 2) if k >= len(recs) else (1,):
            lists[li][0] += 1
            lists[li][1] += bytes(r)
    return b'PEL\0' + struct.pack('<I', 15) + b''.join(struct.pack('<I', n) + b for n, b in lists)


def psl_add(d, posts):
    """the class PSL (v2) + an entry per slot: posts = {slot: (frames, [(frame, PEL list-1 id)])}, each a 1-frame run
    of kind 2 (GS's arcs: 106 / 107)"""
    assert d[:4] == b'PSL\0'
    n = struct.unpack_from('<H', d, 6)[0]
    out = bytearray(d)
    for slot, (frames, ps) in sorted(posts.items()):
        ps = sorted(ps)[:32]
        while len(out) % 16: out += b'\0'
        ent_at = len(out)
        data_at = ent_at + 16
        ids = [rid for _, rid in ps] + [0] * (32 - len(ps))
        kinds = [2] * len(ps) + [0] * (32 - len(ps))
        data = struct.pack('<I32H32I32I', (1 << len(ps)) - 1, *ids, *kinds, *([0] * 32))
        runs, f = [], 0
        for F in sorted({F for F, _ in ps}):
            if F > f: runs.append((0, F - f))
            runs.append((sum(1 << k for k, (G, _) in enumerate(ps) if G == F), 1))
            f = F + 1
        if f < frames - 1: runs.append((0, frames - 1 - f))
        ev_at = data_at + len(data) + 8
        out += struct.pack('<IHBBII', frames, 0, 32, 0, data_at, 0) + data + struct.pack('<II', len(runs), ev_at)
        out += b''.join(struct.pack('<II', b, k) for b, k in runs)
        assert slot < n
        struct.pack_into('<I', out, 8 + 4 * slot, ent_at)
    return bytes(out)


def _whoosh(req, joint, posmode):
    """op 0x66 (weapon sound, a = 0: SRQR slot 4), tags u16 a, u16 req, s16 joint, u16 posmode, u8 random, u8
    threshold, u16 alt req, u8 range (GS's)"""
    tags = (3, 3, 6, 3, 1, 2, 3, 2)
    return bytes([0x66, 1, len(tags), 0]) + struct.pack('<8I', *tags) + struct.pack('<HHhHBBHB', 0, req, joint,
                                                                                    posmode, 0, 0, 0, 0)


def _record(mid, frames, events):
    """events: {frame: [command bytes]} -> one MSS record (offsets relative to the record / the block)"""
    blocks = []
    for f in sorted(events):
        cmds = events[f]
        head = 4 + 4 * len(cmds)
        offs, o = [], head
        for c in cmds:
            offs.append(o)
            o += len(c)
        blocks.append((f, struct.pack('<HH', f, len(cmds)) + struct.pack('<%dI' % len(cmds), *offs) + b''.join(cmds)))
    init_at = 0x10 + 8 * len(blocks)
    body, o = bytearray(), init_at + 4
    pairs = []
    for f, b in blocks:
        pairs.append((f, o))
        body += b
        o += len(b)
    return (struct.pack('<IHHiI', mid, len(blocks), max(frames - 1, 0), -1, init_at) +
            b''.join(struct.pack('<II', f, o) for f, o in pairs) + struct.pack('<HH', 0xffff, 0) + bytes(body))


def mss_rebuild(d, drop, sounds):
    """GS's pl_wp00 copy: records of motion ids in drop removed, ours added: sounds = {motion id: (frames, {frame:
    [command bytes]})}; records sorted by id (the lookup scans linearly, max 512)"""
    assert d[:4] == b'MSS\0'
    n = struct.unpack_from('<H', d, 8)[0]
    base = 0x10 + 2 * 512
    idx = [struct.unpack_from('<II', d, base + 8 * i) for i in range(n)]
    recs = {}
    for k, (mid, off) in enumerate(idx):
        end = idx[k + 1][1] if k + 1 < n else len(d)
        if mid not in drop: recs[mid] = d[off:end]
    for mid, (frames, evs) in sounds.items():
        recs[mid] = _record(mid, frames, evs)
    assert len(recs) <= 512
    head = bytearray(d[:base])
    struct.pack_into('<H', head, 8, len(recs))
    table, body, o = bytearray(), bytearray(), base + 8 * len(recs)
    for mid in sorted(recs):
        table += struct.pack('<II', mid, o + len(body))
        body += recs[mid]
        while len(body) % 4: body += b'\0'
    return bytes(head + table + body)


def build(swings, wdata, holders, own, gu_copy, common, report):
    """-> (PEL records [(id, pos, rot, scale)], PSL posts {slot: (frames, [(frame, id)])}, MSS drop set, MSS sounds)"""
    w13 = wdata[3]
    recs, posts, sounds, seen = [], {}, {}, set()
    for sw in swings:
        key = (sw['mot'], sw['frame'])
        if key in seen or sw['mot'] not in own: continue
        seen.add(key)
        slot, frames = own[sw['mot']], frames_of(w13, sw['mot'])
        a = arc(sw, wdata, holders)
        if a:
            rid = ARC_BASE + len(recs)
            recs.append((rid, a['pos'], a['rot'], a['scl']))
            posts.setdefault(slot, (frames, []))[1].append((a['post'], rid))
            report.append('arc %d: slot %3d (MHF %d) f%d post f%d, r %.0f cm, sweep %.0f deg, pos %s rot %s' % (
                rid, slot, sw['mot'], sw['frame'], a['post'], a['r'], a['sweep'],
                '(%.0f %.0f %.0f)' % a['pos'], '(%.0f %.0f %.0f)' % a['rot']))
        if sw['special'] and not a: continue                     # blasts / shots: no whoosh
        hs = holders.get(sw['mot'])
        f = max(0, sw['frame'] - SND_LEAD)
        joint = 12 if hs and hs[min(f, len(hs) - 1)] == 18 else 8
        evs = sounds.setdefault(5000 + slot, (frames, {}))[1]
        evs.setdefault(f, []).extend([_whoosh(WHOOSH_B, joint, 2),
                                      _whoosh(WHOOSH_FAST if sw['cut'] else WHOOSH_SLOW, 2, 3)])
    drop = {5000 + s for s in own.values()} - {5000 + s for s in list(gu_copy) + list(common)}
    report.append('arcs: %d records on %d slots; swing sounds on %d slots' % (len(recs), len(posts), len(sounds)))
    return recs, posts, drop, sounds
