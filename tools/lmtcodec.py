"""lmtcodec.py : decode / encode the bone-track buffers of MT LMT v67 motion lists (MHGU Switch, 32-bit; the container
is tools/lmt.py). C = confirmed (GU 1.4 main code and/or every track of GU's lists), S = inferred.

  lmtcodec.py check [ARC|FILE.lmt ...]   decode + re-encode every track, compare the bytes (default: GU's player
                                         lists w00, w00_sa, w14, w14_sa, co_0/1/2/6 from paths.GU_ROMFS; an ARC is a
                                         RomFS path like /nativeNX/arc/player/lobby/com.arc, all its LMTs)
Library: decode(type, buffer, ref, bounds) -> [(frame, value)], encode(type, keys, ref, bounds, loop) ->
(buffer, reference, bounds), sample(keys, frame), hemi(quaternion keys), tracks(lmt bytes) -> (anim, frames, loop,
track dict). New tracks: 6 for rotations (GU's main player codec, 1/4096), 4 for positions (16 bit), 1 / 2 constants.

Track 0x24 B: u8 type, u8 usage, u8 joint type, u8 bone id (255 = root), f32 weight, u32 buffer size, u32 buffer,
f32 reference[4], u32 bounds -> 0x20 B {f32 scale[4], f32 base[4]} (0 = none).

Codecs (C): GU 1.4 main (main32.elf, Ghidra dump/gu) table 0x179110c, 16 x {u32 key size, frame getter, evaluator}
(evaluators 0xafea98-0xaffb78, sampler 0xafe6d4). Bit layouts as RevilLib's LMT66-68; the quantisation is GU's:
  type key  little-endian key, f = frames to the next key; bit:width   value
   1    0   no buffer (constant vec3)                                    reference xyz
   2    0   no buffer (constant quaternion)                              reference xyzw
   3   16   f32 x, y, z, u32 f                                           as stored
   4    8   u16 x, y, z, u16 f                                           base + scale * (u - 8) / (2^n - 16), n = 16
   5    4   u8 x, y, z, u8 f                                             bounded, n = 8
   6    8   x 42:14, y 28:14, z 14:14, w 0:14 (two's complement), f 56:8   s / 4096, no bounds
   7    4   x 21:7, y 14:7, z 7:7, w 0:7, f 28:4                         bounded, n = 7
   8   12   f32 x, y, z, one key per frame                               as stored
   9   16   f32 x, y, z, w, one key per frame                            as stored
  11-13 4   x | y | z 0:14, w 14:14, f 28:4; the other two = base        bounded, n = 14
  14    6   x 0:11, y 11:5+16:6, z 22:10+32:1, w 33:11, f 44:4           bounded, n = 11 (a+b: high bits first)
  15    5   x 0:8+8:1, y 9:7+16:2, z 18:6+24:3, w 27:5+32:4, f 36:4      bounded, n = 9
Types 0 and 10: empty table entries. In GU's data (C): player lists use 1 2 4 5 6 7 11 12 14 15; 13 occurs elsewhere
(ev, npc); 3, 8 and 9 occur nowhere in 4322 ev / npc / otomo / weapon arcs (decodable by the game, S as output).

Semantics (C): key 0 is frame 0, key i+1 = key i + f_i, the last key has f = 0 (the sampler walks until f = 0, then
holds that key; types 8 / 9 have no end mark, S: avoid). Every GU track: sum f = motion frames - 1 (the motion plays
frames 0 .. frames - 1). The sampler lerps vec3 keys; quaternion keys are dequantised, nlerped (dot-product sign
check) and normalised. Bounded keys hold u in [8, 2^n - 8]: GU's tool maps the source [min, max] onto it (scale =
max - min, base = min; scale 1e-5 for a constant component; unused 4th vec3 component scale 1e-5, base 0; types
11-13 store the range of their two dropped components, of which the game reads the base). GU's bounds are not always
recoverable from the keys ("derived" in check; S: the source range lies outside the kept keys, or GU's float floor
left a key a step short). Reference: constant types = the value (the sampler returns it); keyed types: not read by
the sampler, GU stores the source pose at frame max(loop, 0) (quaternions within 1e-3, vec3 within 0.15 cm).

Binding (C, 0x95123c / 0x952c7c): before a motion binds, every joint's channels are cleared (no track, weight 0);
usage 0 / 1 / 2 = the joint's rotation / translation / scale channel (bone id through the model's remap, unmapped ids
skipped), 3 / 4 = the motion's root rotation / translation (any bone id; GU uses 255). The weight goes into the
channel, the joint type into the joint's mode (unless 2). A joint without a track keeps its bind transform (S).
Track order is free (bound by bone id); GU's usual: 255/4, 0/0, 0/1, 1-4, 9-12, 5-8, 17-19, 14-16 (bone/usage).
Values (C, player lists + the pl001 skeleton): rotations are full local values, Hamilton xyzw, world = parent *
local (GU's bind rotations are all identity, so absolute = delta from bind; co_0 idle: head 152 cm, hands 86 cm,
ankles 10 cm, the conjugate convention lifts the hands over the head); translations in cm, bone 0's = hip height
above the root (bind offset 0); the root track = root position, not per-frame deltas. Animation header (C, 522 of
527 motions): +0x10 = root(last) - root(loop) if looping, else root(last); +0x20 identity; flags 0x00800000.
Player tracks: joint type 0, weight 1.0; rotations of bones 0-12, 14-19, bone 0 translation, root translation (21);
co_0 adds a root rotation in 2 motions and bones 13 / 20 / 21 in one (which lacks bone 0's rotation).
"""
import math, os, struct, sys
from lmt import anims, TRACK, BOUNDS

KEY = {1: 0, 2: 0, 3: 16, 4: 8, 5: 4, 6: 8, 7: 4, 8: 12, 9: 16, 11: 4, 12: 4, 13: 4, 14: 6, 15: 5}
QUAT = {2, 6, 7, 9, 11, 12, 13, 14, 15}
BITS = {4: 16, 5: 8, 7: 7, 11: 14, 12: 14, 13: 14, 14: 11, 15: 9}                          # bounded types
COMPS = {4: (0, 1, 2), 5: (0, 1, 2), 7: (0, 1, 2, 3), 11: (0, 3), 12: (1, 3), 13: (2, 3), 14: (0, 1, 2, 3),
         15: (0, 1, 2, 3)}                                                                  # stored components
FIELDS = {4: ([[(0, 16)], [(16, 16)], [(32, 16)]], (48, 16)),                               # [(bit, width)] per comp
          5: ([[(0, 8)], [(8, 8)], [(16, 8)]], (24, 8)),                                    # (high part first),
          6: ([[(42, 14)], [(28, 14)], [(14, 14)], [(0, 14)]], (56, 8)),                    # then the frame field
          7: ([[(21, 7)], [(14, 7)], [(7, 7)], [(0, 7)]], (28, 4)),
          11: ([[(0, 14)], [(14, 14)]], (28, 4)),
          14: ([[(0, 11)], [(11, 5), (16, 6)], [(22, 10), (32, 1)], [(33, 11)]], (44, 4)),
          15: ([[(0, 8), (8, 1)], [(9, 7), (16, 2)], [(18, 6), (24, 3)], [(27, 5), (32, 4)]], (36, 4))}
FIELDS[12] = FIELDS[13] = FIELDS[11]
FMAX = {3: 2 ** 32 - 1, 8: 1, 9: 1, **{t: (1 << FIELDS[t][1][1]) - 1 for t in FIELDS}}    # longest key (frames)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


E5 = f32(1e-5)


def _unpack(ty, k):
    q = int.from_bytes(k, 'little')
    comps, (fp, fn) = FIELDS[ty]
    out = []
    for parts in comps:
        v = 0
        for p, n in parts: v = v << n | q >> p & (1 << n) - 1
        out.append(v)
    return q >> fp & (1 << fn) - 1, out


def _pack(ty, f, ints):
    comps, (fp, fn) = FIELDS[ty]
    assert 0 <= f < 1 << fn, (ty, f)
    q = f << fp
    for parts, v in zip(comps, ints):
        for p, n in reversed(parts): q |= (v & (1 << n) - 1) << p; v >>= n
    return q.to_bytes(KEY[ty], 'little')


def _bounds(b):
    return None if b is None else struct.unpack('<8f', b) if isinstance(b, (bytes, bytearray)) else tuple(b)


def decode(ty, buf, ref=None, bounds=None):
    """-> [(frame, value)], value (x, y, z) or quaternion (x, y, z, w) as stored (not normalised); ref = the track's
    reference (types 1, 2), bounds = its 0x20-byte block or 8 floats (bounded types)"""
    if ty in (1, 2):
        return [(0, tuple(ref[:3] if ty == 1 else ref[:4]))]
    ks = KEY[ty]
    assert ks and len(buf) % ks == 0, (ty, len(buf))
    bd = _bounds(bounds)
    out, frame = [], 0
    for i in range(0, len(buf), ks):
        k = buf[i:i + ks]
        if ty in (3, 8, 9):
            v = struct.unpack_from('<4f' if ty == 9 else '<3f', k)
            f = struct.unpack_from('<I', k, 12)[0] if ty == 3 else 1
        elif ty == 6:
            f, u = _unpack(ty, k)
            v = tuple((x - 0x4000 if x & 0x2000 else x) / 4096 for x in u)
        else:
            f, u = _unpack(ty, k)
            den, v = (1 << BITS[ty]) - 16, list(bd[4:])
            for c, x in zip(COMPS[ty], u): v[c] = bd[4 + c] + bd[c] * (x - 8) / den
            v = tuple(v[:3] if ty in (4, 5) else v)
        out.append((frame, tuple(v)))
        frame += f
    return out


def sample(keys, frame):
    """the game's value at a (fractional) frame: lerp (vec3) / nlerp + normalise (quaternion), ends held"""
    i = 0
    while i + 1 < len(keys) and keys[i + 1][0] <= frame: i += 1
    v = keys[i][1]
    if i + 1 < len(keys) and frame > keys[i][0]:
        (fa, a), (fb, b) = keys[i], keys[i + 1]
        if len(a) == 4 and sum(x * y for x, y in zip(a, b)) < 0: b = [-x for x in b]
        t = (frame - fa) / (fb - fa)
        v = [x + (y - x) * t for x, y in zip(a, b)]
    if len(v) == 4:
        n = math.sqrt(sum(x * x for x in v)); v = [x / n for x in v]
    return tuple(v)


def hemi(keys):
    """quaternion keys made sign-continuous, w >= 0 first (as GU's player lists): tighter bounds for types 7, 11-15"""
    out = []
    for f, v in keys:
        p = out[-1][1] if out else (0, 0, 0, 1)
        out.append((f, tuple(v) if sum(x * y for x, y in zip(v, p)) >= 0 else tuple(-x for x in v)))
    return out


def encode(ty, keys, ref=None, bounds=None, loop=-1):
    """keys [(frame, value)]: integer frames rising from 0 (the last = motion frames - 1), value (x, y, z) or a unit
    quaternion (x, y, z, w) -> (buffer bytes, reference (4 floats), bounds bytes or None). Keys longer than the type's
    frame field are split with sampled keys (types 8 / 9: one per frame); signs are kept (run hemi() first for a
    bounded quaternion type). ref / bounds default to GU's rules (pose at frame max(loop, 0); per-component min and
    range); pass a GU track's own to reproduce it byte for byte."""
    n = 4 if ty in QUAT else 3
    keys = [(int(f), tuple(float(x) for x in v[:n])) for f, v in keys]
    assert keys and keys[0][0] == 0 and all(a[0] < b[0] for a, b in zip(keys, keys[1:])), 'frames must rise from 0'
    assert all(len(v) == n for f, v in keys), 'type %d takes %d components' % (ty, n)
    if ty in (1, 2):
        assert all(v == keys[0][1] for f, v in keys), 'constant type, changing values'
        return b'', tuple(ref) if ref is not None else keys[0][1] + (1.0,) * (4 - n), None
    full = []
    for (fa, a), (fb, b) in zip(keys, keys[1:] + [keys[-1]]):
        full.append((fa, a))
        full += [(g, sample(keys, g)) for g in range(fa + FMAX[ty], fb, FMAX[ty])]
    keys = full
    if ref is None:
        ref = sample(keys, max(loop, 0)) + (1.0,) * (4 - n)
    if ty in BITS:
        if bounds is None:
            sc, ba = [E5] * 4, [0.0] * 4
            for c in range(n):
                lo, hi = min(v[c] for f, v in keys), max(v[c] for f, v in keys)
                ba[c] = f32(lo)
                if c not in COMPS[ty]:
                    assert hi - lo < 1e-3, 'type %d drops component %d, which changes' % (ty, c)
                    sc[c] = f32(hi - lo)
                else:
                    sc[c] = f32(max(hi - ba[c], E5))
            bounds = struct.pack('<8f', *sc, *ba)
        elif not isinstance(bounds, (bytes, bytearray)):
            bounds = struct.pack('<8f', *bounds)
        bd = struct.unpack('<8f', bounds)
        den, top = (1 << BITS[ty]) - 16, (1 << BITS[ty]) - 8
    else:
        bounds = None
    out = bytearray()
    for i, (f, v) in enumerate(keys):
        d = keys[i + 1][0] - f if i + 1 < len(keys) else 0
        if ty == 3: out += struct.pack('<3fI', *v, d)
        elif ty in (8, 9): out += struct.pack('<%df' % n, *v)
        elif ty == 6: out += _pack(6, d, [max(-8192, min(8191, math.floor(x * 4096 + 0.5))) for x in v])
        else: out += _pack(ty, d, [max(8, min(top, math.floor((v[c] - bd[4 + c]) / bd[c] * den + 8.5)))
                                   for c in COMPS[ty]])
    return bytes(out), tuple(ref), bounds


def tracks(d):
    """(animation index, frames, loop frame, track dict) for every track of an LMT v67"""
    for ai, o in enumerate(anims(d)):
        if not o: continue
        tr, tc, nf, lf = struct.unpack_from('<IIIi', d, o)
        for k in range(tc):
            p = tr + TRACK * k
            ty, us, jt, bone, w, size, buf = struct.unpack_from('<4BfII', d, p)
            bnd = struct.unpack_from('<I', d, p + 0x20)[0]
            yield ai, nf, lf, dict(index=k, type=ty, usage=us, joint=jt, bone=bone, weight=w,
                                   buf=d[buf:buf + size] if buf else b'', ref=struct.unpack_from('<4f', d, p + 0x10),
                                   bounds=d[bnd:bnd + BOUNDS] if bnd else None)


def _lists(args):
    """{name: LMT bytes} from RomFS arcs / local files"""
    from arc import arc_entries, arc_read
    out, rom = {}, None
    for a in args or ['/nativeNX/arc/player/quest/%s.arc' % n for n in ('w00', 'w14', 'com')]:
        if not a.startswith('/nativeNX/'):
            out[os.path.basename(a)] = open(a, 'rb').read(); continue
        if rom is None:
            import paths
            sys.path.append(paths.GU_PY)
            from romfs import RomFS
            rom = RomFS(paths.GU_ROMFS)
        d = rom.read(a)
        for e in arc_entries(d):
            if e[1] == 0x76820d81: out[e[0].split('\\')[-1]] = arc_read(d, e)
    return out


def synthetic():
    """every keyed type on made-up keys with long gaps (types 3, 8, 9 have no GU data): decode(encode(keys)) holds the
    source keys and the split ones within half a step (float types: float32)"""
    vec = [(0, (0.0, 90.0, 0.0)), (7, (3.5, 92.0, -1.0)), (40, (10.0, 85.0, 30.0)), (300, (12.0, 85.0, 400.0))]
    ax = {11: (1, 0, 0), 12: (0, 1, 0), 13: (0, 0, 1)}
    for ty in sorted(KEY):
        if not KEY[ty]: continue
        if ty in QUAT:
            a = ax.get(ty, tuple(x / math.sqrt(14) for x in (1, 2, 3)))
            src = hemi([(f, tuple(x * math.sin(0.04 * f) for x in a) + (math.cos(0.04 * f),)) for f in (0, 7, 40, 300)])
        else:
            src = vec
        buf, ref, bnd = encode(ty, src)
        back = decode(ty, buf, ref, bnd)
        bd = _bounds(bnd)
        gaps = [g - f for (f, v), (g, w) in zip(back, back[1:])]
        assert {f for f, v in src} <= {f for f, v in back} and max(gaps) <= FMAX[ty], (ty, 'frames')
        for f, v in back:                                  # source keys and split keys = sample(src, f)
            for c, (x, y) in enumerate(zip(v, sample(src, f))):
                tol = (bd[c] / ((1 << BITS[ty]) - 16) / 2 if ty in BITS else 1 / 8192 if ty == 6 else 0) + 1e-6 * abs(y)
                assert abs(x - y) <= tol + 1e-12, (ty, f, c, x, y, tol)
    print('synthetic keys, every keyed type (gap split, types 3 / 8 / 9): ok')


def check(args):
    """decode -> re-encode every track: with the track's own bounds / reference (must give identical bytes) and with
    the encoder's own rules (counted); quaternion norms, frame sums, reference vs the pose at max(loop, 0)"""
    st, bad = {}, []
    for name, d in _lists(args).items():
        for ai, nf, lf, t in tracks(d):
            ty, b0, r0 = t['type'], t['bounds'], t['ref']
            s = st.setdefault(ty, dict(tracks=0, keys=0, exact=0, bounds=0, ref=0, buf=0, all=0, norm=0.0,
                                       refdev=0.0, redec=0.0, lists=set()))
            s['tracks'] += 1; s['lists'].add(name)
            keys = decode(ty, t['buf'], r0, b0)
            s['keys'] += len(keys)
            where = (name, ai, t['index'], ty)
            if ty not in (1, 2) and keys[-1][0] != nf - 1: bad.append(where + ('frames', keys[-1][0], nf))
            if ty in QUAT:
                s['norm'] = max(s['norm'], max(abs(math.sqrt(sum(x * x for x in v)) - 1) for f, v in keys))
            # 1. pinned: GU's own reference and bounds -> the buffer must come back byte for byte
            buf, ref, bnd = encode(ty, keys, r0, b0, lf)
            if buf == t['buf'] and bnd == b0 and struct.pack('<4f', *ref) == struct.pack('<4f', *r0):
                s['exact'] += 1
            else:
                bad.append(where + ('pinned round trip differs',))
            # 2. derived: the encoder's own bounds / reference
            buf, ref, bnd = encode(ty, keys, loop=lf)
            okb, okr, okd = bnd == b0, struct.pack('<4f', *ref) == struct.pack('<4f', *r0), buf == t['buf']
            s['bounds'] += okb; s['ref'] += okr; s['buf'] += okd; s['all'] += okb and okr and okd
            back = decode(ty, buf, ref, bnd)
            if [f for f, v in back] != [f for f, v in keys]: bad.append(where + ('derived frames differ',))
            bd = _bounds(bnd)
            for (f, v), (g, w) in zip(keys, back):         # re-decoded error in quantisation steps (<= 0.5), less
                for c in range(len(v)):                    # one float32 ulp of the value (the bounds are float32)
                    step = bd[c] / ((1 << BITS[ty]) - 16) if ty in BITS else 1 / 4096 if ty == 6 else 0
                    e = max(0.0, abs(v[c] - w[c]) - abs(v[c]) * 2 ** -23)
                    s['redec'] = max(s['redec'], e / step if step else e)
            # reference vs the pose at max(loop, 0) (sign-free for quaternions)
            p = sample(keys, max(lf, 0))
            if len(p) == 4 and sum(x * y for x, y in zip(p, r0)) < 0: p = [-x for x in p]
            s['refdev'] = max(s['refdev'], max(abs(x - y) for x, y in zip(p, r0)))
    print('type tracks    keys  pinned exact | derived: bounds    ref buffer    all | max|norm-1| redecode ref-pose',
          ' lists')
    for ty, s in sorted(st.items()):
        print('%4d %6d %7d %13d | %15d %6d %6d %6d | %11s %8.3f %8.2g  %s' % (
            ty, s['tracks'], s['keys'], s['exact'], s['bounds'], s['ref'], s['buf'], s['all'],
            '%.2e' % s['norm'] if ty in QUAT else '-', s['redec'], s['refdev'],
            ','.join(sorted(s['lists'])[:8]) + (' +%d' % (len(s['lists']) - 8) if len(s['lists']) > 8 else '')))
    print("(pinned = with the track's own reference and bounds; derived = the encoder's rules; redecode = largest "
          'error of decode(encode(keys)) in quantisation steps; ref-pose = largest |reference - pose at max(loop, 0)|)')
    tot = sum(s['tracks'] for s in st.values())
    print('tracks', tot, 'pinned byte-exact', sum(s['exact'] for s in st.values()), 'problems', len(bad))
    for b in bad[:20]: print('  ', b)
    assert not bad, 'round trip failed'
    assert all(s['norm'] < 0.05 for t, s in st.items() if t in QUAT), 'quaternion norm off'
    assert all(s['redec'] <= 0.5 + 1e-6 for s in st.values()), 'derived encode off by more than half a step'
    return st


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        synthetic()
        check(sys.argv[2:])
    else:
        print(__doc__)
