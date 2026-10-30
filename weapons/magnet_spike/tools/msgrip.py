"""msgrip.py : which hand holds the Magnet Spike on each frame of an MHF weapon motion.
The weapon motions (w13w) key weapon bones 3-10 in the frame of the HOLDING hand, and MHF passes the weapon between
the hands mid-motion (Finishing Slash: right hand until frame 103, then left) with no flag in the motion files (bones
0-2 carry no channels, no trailing data) and no action event at the switch; MHF's own mechanism is not located yet.
The keys tell anyway: the keyed weapon passes through the holding fist. Fist centres = the body mesh's vertices of
hand bones 14 / 18 relative to their bone (m_editpl: (+8.3, -0.7, 0.6) / (-8.3, -0.7, 0.7) cm, no vertex on the
other side). Rule per frame: keep the current hand (bone 14 at frame 0) unless the other fist lies within GOOD cm of
the keyed weapon's surface and MARGIN cm closer than the current one. Over all 157 body motions with a weapon motion
it finds 14 clean switches (new fist 0.1-1.2 cm), at frames where the other fist is on the weapon too, and the chains
agree (the wind-ups 1406 / 1418 / 1446 end in the right hand, Finishing Slash 1035 starts in it).
Motion conventions as mhf2blend.py: short rotations x 2 pi / 16384, short translations and scales / 16 (cm), float
keys as is (radians, cm), Hermite keys with tangents per frame, local = T(pos) R(Rz Ry Rx) S.
usage: python3 -I msgrip.py W13W.aan WEAPON_DIR BODY_FMOD BODY_FSKL      every weapon motion's holder switches"""
import math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aan, fmod, fskl

ROT = 2 * math.pi / 16384
HANDS = (14, 18)
GOOD, MARGIN = 6.0, 4.0


def value(t, keys, f, chan):
    """AAN channel (key type t, keys) at frame f, in radians / cm / scale"""
    if t in (17, 33): ks = [(k[1], k[0], 0.0, 0.0, True) for k in keys]
    elif t in (18, 34): ks = [(k[1], k[0], k[2], k[3], False) for k in keys]
    else: ks = [(k[2], k[1], k[3], k[4], k[0] == 0x10000) for k in keys]
    if f <= ks[0][0]: v = ks[0][1]
    elif f >= ks[-1][0]: v = ks[-1][1]
    else:
        i = max(j for j in range(len(ks)) if ks[j][0] <= f)
        (f0, v0, _, o0, lin), (f1, v1, i1, _, _) = ks[i], ks[i + 1]
        d = f1 - f0; s = (f - f0) / d
        v = v0 + (v1 - v0) * s if lin else ((2 * s ** 3 - 3 * s ** 2 + 1) * v0 + (s ** 3 - 2 * s ** 2 + s) * d * o0
                                            + (3 * s ** 2 - 2 * s ** 3) * v1 + (s ** 3 - s ** 2) * d * i1)
    return v * (ROT if chan[0] == 'r' else 1 / 16.0) if t < 32 else v


def euler(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


# the model turn (test 1: "the models lay flat" in the smithy viewer, which stands a weapon on its model z axis, GS's
# blade z -80..224, where MHF's Magnet Spike lies along x, -140..140): the GU model (its root's child: fmod2gu
# skeleton(), as the viewer replaces the root joint) and the weapon motions' root carry TURN (x -> z); the hand grip and
# the back's carry record undo it (ms_class.c s_grip, back_record); hit shapes and arcs stay in the hand's frame
TURN = euler((0.0, -math.pi / 2, 0.0))


def pose(bones, tracks, f):
    """FSKL bones, {bone: AAN channels} -> {bone: 4x4} in the skeleton root's frame at frame f (unkeyed = rest)"""
    by = {b['node']: b for b in bones}; out = {}
    def walk(n, parent):
        b = by[n]; pos, rot, sc = list(b['pos']), list(b['rot']), [1.0, 1.0, 1.0]
        for ch, (t, keys) in tracks.get(n, {}).items():
            if keys and ch[0] in 'rts':
                {'r': rot, 't': pos, 's': sc}[ch[0]]['xyz'.index(ch[1])] = value(t, keys, f, ch)
        L = np.eye(4); L[:3, :3] = euler(rot) @ np.diag(sc); L[:3, 3] = pos
        out[n] = parent @ L
        c = b['child']
        while c >= 0: walk(c, out[n]); c = by[c]['sibling']
    for b in bones:
        if b['parent'] < 0: walk(b['node'], np.eye(4))
    return out


def fists(body_fmod, body_fskl):
    """hand bone -> centre of its fist (mean of the vertices it carries) in the bone's own frame, cm"""
    _, bones = fskl.parse(body_fskl); by = {b['node']: b for b in bones}
    def rest(n):
        p = np.zeros(3)
        while n >= 0: p += by[n]['pos']; n = by[n]['parent']
        return p
    m = fmod.parse(body_fmod)[0]; out = {}
    for h in HANDS:
        V = [p for p, ws in zip(m['pos'], m['weights'])
             if ws and (m['bones'][max(ws, key=lambda w: w[1])[0]] if m['bones'] else max(ws, key=lambda w: w[1])[0]) == h]
        out[h] = np.mean(V, 0) - rest(h)
    return out


class Weapon:
    """the weapon model's rest skeleton, vertices (each on its heaviest bone) and triangles"""
    def __init__(self, fmod_bytes, fskl_bytes):
        _, self.bones = fskl.parse(fskl_bytes)
        self.rest_inv = {b: np.linalg.inv(m) for b, m in pose(self.bones, {}, 0).items()}
        P, B, T = [], [], []
        for m in fmod.parse(fmod_bytes):
            base = len(P)
            for p, ws in zip(m['pos'], m['weights']):
                b = max(ws, key=lambda w: w[1])[0]; P.append(p); B.append(m['bones'][b] if m['bones'] else b)
            T += [(base + a, base + b, base + c) for a, b, c, _ in fmod.triangles(m)]
        self.pos, self.bone, self.tris = np.array(P, float), np.array(B), np.array(T)

    def posed(self, tracks, f):
        """vertices posed by a weapon motion at frame f, in the weapon root's frame (= the holding hand's)"""
        W = pose(self.bones, tracks, f); out = np.empty_like(self.pos)
        for b in set(self.bone.tolist()):
            M = W[b] @ self.rest_inv[b]; s = self.bone == b
            out[s] = self.pos[s] @ M[:3, :3].T + M[:3, 3]
        return out


def tri_dist(p, A, B, C):
    """distance from point p to the nearest of the triangles (A, B, C: n x 3), closest-point regions as in Ericson"""
    ab, ac, ap = B - A, C - A, p - A
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp, cp = p - B, p - C
    d3, d4, d5, d6 = (ab * bp).sum(1), (ac * bp).sum(1), (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = va + vb + vc; den[den == 0] = 1e-12
    Q = A + ab * (vb / den)[:, None] + ac * (vc / den)[:, None]
    with np.errstate(divide='ignore', invalid='ignore'):
        e = [((vc <= 0) & (d1 >= 0) & (d3 <= 0), A + ab * (d1 / (d1 - d3))[:, None]),
             ((vb <= 0) & (d2 >= 0) & (d6 <= 0), A + ac * (d2 / (d2 - d6))[:, None]),
             ((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), B + (C - B) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None])]
    for m, q in e: Q[m] = q[m]
    for m, q in (((d1 <= 0) & (d2 <= 0), A), ((d3 >= 0) & (d4 <= d3), B), ((d6 >= 0) & (d5 <= d6), C)): Q[m] = q[m]
    return np.linalg.norm(Q - p, axis=1).min()


def holders(weapon, tracks, frames, fist):
    """holding hand (14 / 18) for frames 0..frames of one weapon motion"""
    h, out = HANDS[0], []
    for f in range(int(frames) + 1):
        P = weapon.posed(tracks, f); A, B, C = P[weapon.tris[:, 0]], P[weapon.tris[:, 1]], P[weapon.tris[:, 2]]
        d = {k: tri_dist(fist[k], A, B, C) for k in HANDS}; o = HANDS[1] if h == HANDS[0] else HANDS[0]
        if d[o] < GOOD and d[o] + MARGIN < d[h]: h = o
        out.append(h)
    return out


def tracks_of(mo, bones):
    """AAN motion -> {bone id: channels} in FSKL order"""
    return {b['node']: mo['bones'][i] for i, b in enumerate(bones) if i < len(mo['bones'])}


if __name__ == '__main__':
    w13w, wdir, body, bskl = sys.argv[1:5]
    weapon = Weapon(open(os.path.join(wdir, '0.fmod'), 'rb').read(), open(os.path.join(wdir, '1.fskl'), 'rb').read())
    fist = fists(open(body, 'rb').read(), open(bskl, 'rb').read())
    print('fist centres (cm, own bone frame):', {h: np.round(c, 1).tolist() for h, c in fist.items()})
    for part, motions in enumerate(aan.parse(open(w13w, 'rb').read())):
        for slot, mo in sorted(motions.items()):
            hs = holders(weapon, tracks_of(mo, weapon.bones), mo['frames'], fist)
            sw = ['f%d->%d' % (f, hs[f]) for f in range(1, len(hs)) if hs[f] != hs[f - 1]]
            if hs[0] != HANDS[0] or sw:
                print('motion %d: starts in %d%s' % (1000 + part * 100 + slot, hs[0], ', ' + ' '.join(sw) if sw else ''))
