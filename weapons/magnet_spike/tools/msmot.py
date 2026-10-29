"""msmot.py : MHF Magnet Spike motions -> MHGU motion lists (LMT v67): the body list player\\mot\\w05\\w05 (GU player
skeleton) and the weapon list weapon\\w05\\mot\\wg05_00 (the converted model's 11 bones), paired by slot as GU's weapon
sync pairs them (0x308b3c: a bank-5 player motion plays the same slot of the weapon list).

Sources: w13.aan (body: even part = MHF bones 0-8, odd part = 9-20, same slot) and w13w.aan (weapon: part P slot S
= body motion P S), both read with aan.py; values and FK as msgrip.py (rotations Euler Rz Ry Rx, absolute local;
MHF rest rotations are all zero, as GU's binds; cm; +z forward, y up in both games).
Body (C on the files, notes/assets.md "Skeletons"):
  MHF bone 1 (root motion) -> GU root track 255 (usage 4 translation, rebased to start at 0; usage 3 rotation when
  bone 1 turns), MHF bone 2 (hips) -> GU bone 0 rotation + translation (height above the root), the rest rotation
  only, by BODY_MAP. GU's track order and codecs (tools/lmtcodec.py): rotations type 6, translations type 4,
  constants types 1 / 2.
Weapon: every bone gets rotation and translation tracks (rest values where MHF leaves a channel unkeyed: the GU
  model's binds hold the FSKL rest, and GU's evaluation of a missing track is not traced), scale tracks where MHF
  keys a scale away from 1. MHF keys the weapon in the frame of the HOLDING hand (bone 14 = GU 8, or 18 = GU 12,
  msgrip.holders); GU attaches it to one joint, so on bone-18 frames the weapon root (bone 0) is keyed with
  inverse(W14) x W18 from the body motion's own pose: the hand switch is baked into the data.
Frames: MHF and GU motion frames are both 1/60 s (notes/assets.md "Frame rate"): frame f -> frame f.
Animation header as GU's: +0x10 = root(last) - root(loop) (looping) or root(last), +0x20 identity, flags 0x00800000,
an event block of 4 groups (here empty, or a GU template's events rescaled).

Library: body(parts, mid) / weapon(wparts, wbones, mid, holders, body pose) -> anim dict; lmt_bytes({slot: anim});
anim_from_gu(lmt, slot) copies a GU animation as is."""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import aan, msgrip, lmt, lmtcodec

# MHF body bone -> GU bone (hips and up; MHF 0 = floor, 1 = root motion -> GU 255)
BODY_MAP = {2: 0, 9: 1, 10: 2, 19: 3, 20: 4, 11: 5, 12: 6, 13: 7, 14: 8, 15: 9, 16: 10, 17: 11, 18: 12,
            3: 14, 4: 15, 5: 16, 6: 17, 7: 18, 8: 19}
GU_ORDER = [0, 1, 2, 3, 4, 9, 10, 11, 12, 5, 6, 7, 8, 17, 18, 19, 14, 15, 16]   # GU's track order after 255, bone 0 pos
ROT_EPS = 0.0006          # nlerp error kept below ~0.07 deg (type 6 steps are 1/4096)
POS_EPS = 0.05            # cm
FLAGS = 0x00800000


def quat(m):
    """3x3 rotation -> unit quaternion (x, y, z, w)"""
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = ((m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = (0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s)
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = ((m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s)
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = ((m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s)
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def channel(chans, ch, f, rest):
    """one MHF channel at frame f (radians / cm / scale), rest value when unkeyed"""
    if ch in chans and chans[ch][1]:
        t, keys = chans[ch]
        return msgrip.value(t, keys, f, ch)
    return rest


def reduce(keys, err):
    """keep the keys the game's interpolation (lerp / nlerp) cannot rebuild within err; keys = [(frame, value)]"""
    if len(keys) <= 2: return keys
    out, a = [keys[0]], 0
    for b in range(2, len(keys)):
        fa, va = keys[a]; fb, vb = keys[b]
        ok = True
        for k in range(a + 1, b):
            s = (keys[k][0] - fa) / (fb - fa)
            v = [x + (y - x) * s for x, y in zip(va, vb)]
            if len(v) == 4:
                n = math.sqrt(sum(c * c for c in v)); v = [c / n for c in v]
            if max(abs(x - y) for x, y in zip(v, keys[k][1])) > err:
                ok = False; break
        if not ok:
            out.append(keys[b - 1]); a = b - 1
    out.append(keys[-1])
    return out


def hemi(seq):
    """quaternion samples sign-continuous"""
    out = [seq[0]]
    for q in seq[1:]:
        if sum(x * y for x, y in zip(q, out[-1])) < 0: q = tuple(-c for c in q)
        out.append(q)
    return out


def rot_track(bone, usage, samples):
    """samples [quaternion per frame] -> track dict (type 2 constant or type 6)"""
    samples = hemi(samples)
    if max(max(abs(a - b) for a, b in zip(q, samples[0])) for q in samples) < 1e-5:
        buf, ref, bnd = lmtcodec.encode(2, [(0, samples[0])])
        return dict(type=2, usage=usage, bone=bone, buf=buf, ref=ref, bounds=bnd)
    keys = reduce(list(enumerate(samples)), ROT_EPS)
    buf, ref, bnd = lmtcodec.encode(6, keys)
    return dict(type=6, usage=usage, bone=bone, buf=buf, ref=ref, bounds=bnd)


def vec_track(bone, usage, samples, loop=-1):
    """samples [vec3 per frame] -> track dict (type 1 constant or type 4)"""
    if max(max(abs(a - b) for a, b in zip(v, samples[0])) for v in samples) < 1e-3:
        buf, ref, bnd = lmtcodec.encode(1, [(0, samples[0])])
        return dict(type=1, usage=usage, bone=bone, buf=buf, ref=ref, bounds=bnd)
    keys = reduce(list(enumerate(samples)), POS_EPS)
    buf, ref, bnd = lmtcodec.encode(4, keys, loop=loop)
    return dict(type=4, usage=usage, bone=bone, buf=buf, ref=ref, bounds=bnd)


def local_rot(chans, f):
    r = [channel(chans, 'r' + a, f, 0.0) for a in 'xyz']
    return msgrip.euler(r)


def body_chans(parts, mid):
    """MHF body motion id -> (motion of the lower part, {MHF bone: channels} for bones 0-20)"""
    part, slot = (mid - 1000) // 100, (mid - 1000) % 100
    lo, up = parts[part][slot], parts[part + 1].get(slot)
    chans = {i: c for i, c in enumerate(lo['bones'])}
    if up:
        chans.update({9 + i: c for i, c in enumerate(up['bones'])})
    return lo, chans


def body(parts, mid, events=None):
    """MHF body motion -> GU animation dict (frames, loop, tracks, end)"""
    mo, chans = body_chans(parts, mid)
    n = int(mo['frames']) + 1
    loop = int(mo['loop_start']) if mo['loop'] else -1
    tracks = []
    root = [np.array([channel(chans[1], 't' + a, f, 0.0) for a in 'xyz']) for f in range(n)]
    root = [tuple(p - root[0]) for p in root]
    tracks.append(vec_track(255, 4, root, loop))
    rr = [quat(local_rot(chans[1], f)) for f in range(n)]
    if max(abs(q[3]) for q in rr) < 0.99999 or min(abs(q[3]) for q in rr) < 0.99999:
        tracks.append(rot_track(255, 3, rr))
    for gb in GU_ORDER:
        mb = next(k for k, v in BODY_MAP.items() if v == gb)
        tracks.append(rot_track(gb, 0, [quat(local_rot(chans.get(mb, {}), f)) for f in range(n)]))
        if gb == 0:
            hips = [tuple(channel(chans[2], 't' + a, f, 0.0) for a in 'xyz') for f in range(n)]
            tracks.append(vec_track(0, 1, hips, loop))
    end = tuple(np.subtract(root[-1], root[loop]) if loop >= 0 else root[-1])
    return dict(frames=n, loop=loop, tracks=tracks, end=end, events=events)


def body_world(parts, bones, mid):
    """frame -> {MHF bone: 4x4 world (root frame)} for the hand switch"""
    _, chans = body_chans(parts, mid)
    return lambda f: msgrip.pose(bones, chans, f)


def weapon(wparts, wbones, mid, holders=None, world=None, frames=None):
    """MHF weapon motion (paired with body motion mid) -> GU weapon animation dict; holders = msgrip.holders list,
    world = body_world(...) for the bone-18 frames"""
    part, slot = (mid - 1000) // 100, (mid - 1000) % 100
    mo = wparts[part].get(slot)
    n = frames or (int(mo['frames']) + 1 if mo else 1)
    chans = {b['node']: (mo['bones'][i] if mo and i < len(mo['bones']) else {}) for i, b in enumerate(wbones)}
    tracks = []
    for b in wbones:
        node = b['node']
        R, T, S = [], [], []
        for f in range(n):
            ch = chans[node]
            rot = msgrip.euler([channel(ch, 'r' + a, f, b['rot']['xyz'.index(a)]) for a in 'xyz'])
            pos = np.array([channel(ch, 't' + a, f, b['pos']['xyz'.index(a)]) for a in 'xyz'])
            sc = [channel(ch, 's' + a, f, 1.0) for a in 'xyz']
            if node == 0 and holders and world and holders[min(f, len(holders) - 1)] == 18:
                W = world(f)
                M = np.linalg.inv(W[14]) @ W[18]
                L = np.eye(4); L[:3, :3] = rot; L[:3, 3] = pos
                L = M @ L
                rot, pos = L[:3, :3], L[:3, 3]
            R.append(quat(rot)); T.append(tuple(pos)); S.append(tuple(sc))
        tracks.append(rot_track(node, 0, R))
        tracks.append(vec_track(node, 1, T))
        if max(max(abs(c - 1.0) for c in s) for s in S) > 1e-4:
            tracks.append(vec_track(node, 2, S))
    loop = int(mo['loop_start']) if mo and mo['loop'] else -1
    return dict(frames=n, loop=loop, tracks=tracks, end=(0.0, 0.0, 0.0), events=None)


def weapon_pose(wparts, wbones, mid, frame=0):
    """a still weapon pose: every bone as weapon motion mid keys it at `frame`, the root (bone 0) at its rest (the
    joint GU attaches the weapon to places it); constant tracks over 2 frames"""
    part, slot = (mid - 1000) // 100, (mid - 1000) % 100
    mo = wparts[part][slot]
    chans = {b['node']: (mo['bones'][i] if i < len(mo['bones']) else {}) for i, b in enumerate(wbones)}
    tracks = []
    for b in wbones:
        node = b['node']
        ch = {} if node == 0 else chans[node]
        rot = msgrip.euler([channel(ch, 'r' + a, frame, b['rot']['xyz'.index(a)]) for a in 'xyz'])
        pos = tuple(channel(ch, 't' + a, frame, b['pos']['xyz'.index(a)]) for a in 'xyz')
        sc = tuple(channel(ch, 's' + a, frame, 1.0) for a in 'xyz')
        tracks.append(rot_track(node, 0, [quat(rot)] * 2))
        tracks.append(vec_track(node, 1, [pos] * 2))
        if max(abs(c - 1.0) for c in sc) > 1e-4:
            tracks.append(vec_track(node, 2, [sc] * 2))
    return dict(frames=2, loop=-1, tracks=tracks, end=(0.0, 0.0, 0.0), events=None)


def empty_events(frames):
    """4 groups, no event: remap zero, one run of `frames` frames with no bit set"""
    return [([0] * 32, [(0, frames)]) for _ in range(4)]


def gu_events(d, o):
    """a GU animation's event groups [(remap[32], [(bits, frames)])]"""
    ev = struct.unpack_from('<I', d, o + 0x34)[0]
    out = []
    for g in range(4):
        remap = list(struct.unpack_from('<32H', d, ev + 0x48 * g))
        cnt, ptr = struct.unpack_from('<II', d, ev + 0x48 * g + 0x40)
        out.append((remap, [struct.unpack_from('<II', d, ptr + 8 * k) for k in range(cnt)]))
    return out


def rescale_events(groups, frames):
    """event runs stretched to another frame count (each run keeps its share; the total stays `frames`)"""
    out = []
    for remap, runs in groups:
        tot = sum(r[1] for r in runs) or 1
        acc, new = 0, []
        for i, (bits, n) in enumerate(runs):
            end = frames if i == len(runs) - 1 else round((acc + n) * frames / tot)
            beg = round(acc * frames / tot)
            if end > beg: new.append((bits, end - beg))
            acc += n
        out.append((remap, new or [(0, frames)]))
    return out


def lmt_bytes(slots, count=256):
    """{slot: anim dict | ('gu', lmt bytes, slot)} -> LMT v67 bytes (file offsets, 16-B aligned blocks)"""
    head = bytearray(b'LMT\0' + struct.pack('<HH', 67, count) + bytes(4 * count))
    body_ = bytearray()
    base = (len(head) + 15) & ~15

    def put(b, align=16):
        body_.extend(bytes(-(base + len(body_)) % align))
        o = base + len(body_); body_.extend(b); return o
    for s in sorted(slots):
        a = slots[s]
        if isinstance(a, tuple):                     # a GU animation copied as is (lmt.splice relocates it)
            continue
        tracks = a['tracks']
        bufs = [put(t['buf']) if t['buf'] else 0 for t in tracks]
        bnds = [put(t['bounds']) if t['bounds'] else 0 for t in tracks]
        tt = bytearray()
        for t, bo, bd in zip(tracks, bufs, bnds):
            tt += struct.pack('<4BfII4fI', t['type'], t['usage'], 0, t['bone'], 1.0, len(t['buf']), bo,
                              *t['ref'], bd)
        tro = put(bytes(tt))
        groups = a['events'] or empty_events(a['frames'])
        runs = [put(b''.join(struct.pack('<II', *r) for r in g[1]), 8) for g in groups]
        evb = b''.join(struct.pack('<32HII', *g[0], len(g[1]), ro) for g, ro in zip(groups, runs))
        evo = put(evb)
        hdr = struct.pack('<IIIi4f4fII8x', tro, len(tracks), a['frames'], a['loop'], *a['end'], 0.0,
                          0.0, 0.0, 0.0, 1.0, FLAGS, evo)
        assert len(hdr) == 0x40
        struct.pack_into('<I', head, 8 + 4 * s, put(hdr))
    out = bytes(head) + bytes(base - len(head)) + bytes(body_)
    gu = {s: a for s, a in slots.items() if isinstance(a, tuple)}
    for s, (_, src, ss) in sorted(gu.items()):
        out = lmt.splice(out, src, [(ss, s)])
    return out


def check(d):
    """every animation decodes; keyed tracks span frames - 1"""
    for ai, nf, lf, t in lmtcodec.tracks(d):
        keys = lmtcodec.decode(t['type'], t['buf'], t['ref'], t['bounds'])
        if t['type'] not in (1, 2):
            assert keys[-1][0] == nf - 1, (ai, t['bone'], keys[-1][0], nf)
    return True


if __name__ == '__main__':
    import fskl
    w13 = aan.parse(open(sys.argv[1], 'rb').read())
    _, bones = fskl.parse(open(sys.argv[2], 'rb').read())
    for mid in [int(x) for x in sys.argv[3:]]:
        a = body(w13, mid)
        print(mid, 'frames', a['frames'], 'loop', a['loop'], 'tracks', len(a['tracks']),
              'bytes', sum(len(t['buf']) for t in a['tracks']), 'end', np.round(a['end'], 1).tolist())
