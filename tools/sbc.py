"""sbc.py : MH4U / MHGU stage collision "SBC" (type 0x51fc779f) reader, MHGU writer, 4U -> GU converter.

  sbc.py info FILE                 dump header / parts / BVH / grids (either game)
  sbc.py selftest DIR              parse + rewrite every GU *.sbc / *.51fc779f under DIR, compare byte for byte
  sbc.py conv IN_4U OUT_GU         convert one 4U collision file to GU

Layout (both games little-endian, NO alignment: every block follows the previous one byte for byte).
nP = parts (one uniform grid each), nG = attribute groups, nA = polygons, nB = triangles, nC = vertices.

  header         4U 0x48 / GU 0x54
    +00 'SBC\\xff'  +04 u32 class hash (4U 0x77cf8df8, GU 0x781aca20)  +08 u32 0  +0C u32 2
    +10 u16 nP  +12 u16 nG  +14 u32 nA  +18 u32 nB  +1C u32 nC
    4U: +20 8 zero, +28 bbox (min vec4, max vec4)
    GU: +20 16 zero, +30 bbox, +50 u32 runtime size = 112 * BVH nodes + sum over grids (8 * nx * nz + 2 * listLen)
  part record    4U 0x48: bbox(32), u32 0, 2 x u32 runtime pointers (garbage), 3 x (u32 start, u32 count) for
                 (polygons, triangles, vertices), u32 id
                 GU 0x50: bbox(32), 3 x u32 0, the 3 (start, count) pairs, u32 id, 2 x u32 0
                 record 0 = the first part (start 0); triangle/vertex/polygon indices are LOCAL to the part.
  polygon AABB   nA x 28: f32 min[3], u32 local polygon index, f32 max[3]  (polygon box inflated by 2 on each axis)
  BVHC           'BVHC', u32 hash 0x77b17b24, u32 1, u32 0, bbox(32), u32 nNodes, 12 zero, nNodes x 112-byte
                 4-wide nodes over the PARTS: u8 mask x4 (same byte 4 times; high nibble bit i = slot i is a leaf
                 = part idx[i], low nibble bit i = slot i is an inner node idx[i], neither = empty),
                 u16 idx[4], u32 pad (4U: garbage, GU: 0), f32 slot boxes SoA minx[4] miny[4] minz[4] maxx[4]..
  triangle       nB x 32: f32 normal[3], u16 v[3] (local vertex indices), u16 group, u32 0, u8[4] edge/flag bytes,
                 u32 0
  vertex         nC x 16: f32 x, y, z, 0
  group          nG x 32: u32 attribute word (wall/floor/material bits), u32 4U 0x20000 / GU 0, u32 1,
                 3 x u32 0 / runtime pointers
  polygon        nA x 10: u16 tri0, u16 tri1 (0xffff = single triangle), u8[4] quad vertex order
                 (ff x4 for a triangle), u16 group
  grco (per part) 'grco', u32 hash 0x77c09c94, bbox(32), u16 nx, u16 nz, u8 1, u8 1,
                 nx*nz x (u32 count, u32 offset) z-major, u32 listLen, listLen x u16 local polygon indices
                 (lists stored x-major); nx = max(1, floor(extent_x / cell)), cell = 300 / 600 / 900 per file.
Block order:
  4U: header, parts, polygons, triangles, vertices, groups, grco x nP, polygon AABBs, BVHC
  GU: header, parts, polygon AABBs, BVHC, triangles, vertices, groups, polygons, grco x nP
"""
import struct, sys, os

T_SBC = 0x51fc779f
HASH_4U, HASH_GU = 0x77cf8df8, 0x781aca20


def _bvhc(d, o):
    assert d[o:o + 4] == b'BVHC', ('BVHC expected', hex(o))
    nn = struct.unpack_from('<I', d, o + 48)[0]
    end = o + 64 + 112 * nn
    return dict(raw=bytes(d[o:end]), nodes=nn), end


def _grco(d, o):
    assert d[o:o + 4] == b'grco', ('grco expected', hex(o))
    nx, nz = struct.unpack_from('<HH', d, o + 40)
    o2 = o + 46 + 8 * nx * nz
    n = struct.unpack_from('<I', d, o2)[0]
    end = o2 + 4 + 2 * n
    return dict(raw=bytes(d[o:end]), nx=nx, nz=nz, n=n), end


def parse(d):
    magic, h = struct.unpack_from('<4sI', d, 0)
    assert magic == b'SBC\xff', magic
    nP, nG, nA, nB, nC = struct.unpack_from('<HHIII', d, 0x10)
    s = dict(nG=nG, nA=nA, nB=nB, nC=nC, parts=[], grids=[])
    if h == HASH_GU:
        s['ver'] = 'gu'
        s['bbox'] = d[0x30:0x50]
        s['gridmem'] = struct.unpack_from('<I', d, 0x50)[0]
        o = 0x54
        for p in range(nP):
            r = d[o:o + 0x50]
            s['parts'].append(dict(bbox=r[:32], pairs=struct.unpack_from('<6I', r, 44),
                                   id=struct.unpack_from('<I', r, 68)[0], pad=r[32:44] + r[72:80]))
            o += 0x50
        s['aabb'] = d[o:o + 28 * nA]; o += 28 * nA
        s['bvh'], o = _bvhc(d, o)
        s['tris'] = d[o:o + 32 * nB]; o += 32 * nB
        s['verts'] = d[o:o + 16 * nC]; o += 16 * nC
        s['groups'] = d[o:o + 32 * nG]; o += 32 * nG
        s['polys'] = d[o:o + 10 * nA]; o += 10 * nA
        for p in range(nP):
            g, o = _grco(d, o); s['grids'].append(g)
    elif h == HASH_4U:
        s['ver'] = '4u'
        s['bbox'] = d[0x28:0x48]
        o = 0x48
        for p in range(nP):
            r = d[o:o + 0x48]
            s['parts'].append(dict(bbox=r[:32], pairs=struct.unpack_from('<6I', r, 44),
                                   id=struct.unpack_from('<I', r, 68)[0], pad=r[32:44]))
            o += 0x48
        s['polys'] = d[o:o + 10 * nA]; o += 10 * nA
        s['tris'] = d[o:o + 32 * nB]; o += 32 * nB
        s['verts'] = d[o:o + 16 * nC]; o += 16 * nC
        s['groups'] = d[o:o + 32 * nG]; o += 32 * nG
        aabb = []
        if d[o:o + 4] == b'BVHC':       # 4U m05a01d-a-cam (the only such file seen): two BVHs (7 nodes, then 1) and
            s['bvh'], o = _bvhc(d, o)   # no grid / polygon AABBs; the first is taken as the BVH (G), convert_4u
            s['bvh2'], o = _bvhc(d, o)  # rebuilds the AABBs and gives each part a 1 x 1 grid
            s['nogrid'] = True
        else:
            for p in s['parts']:            # 4U: each grid is followed by its part's polygon AABBs
                g, o = _grco(d, o); s['grids'].append(g)
                n = p['pairs'][1]
                aabb.append(d[o:o + 28 * n]); o += 28 * n
            s['aabb'] = b''.join(aabb)
            s['bvh'], o = _bvhc(d, o)
    else:
        raise ValueError('unknown SBC class hash %#x' % h)
    assert o == len(d), ('trailing bytes', o, len(d))
    return s


def grid_mem(s):
    return 112 * s['bvh']['nodes'] + sum(8 * g['nx'] * g['nz'] + 2 * g['n'] for g in s['grids'])


def write_gu(s):
    nP = len(s['parts'])
    out = bytearray(struct.pack('<4sIIIHHIII', b'SBC\xff', HASH_GU, 0, 2, nP, s['nG'], s['nA'], s['nB'], s['nC']))
    out += b'\0' * 16 + s['bbox'] + struct.pack('<I', grid_mem(s))
    for p in s['parts']:
        out += p['bbox'] + b'\0' * 12 + struct.pack('<6II', *p['pairs'], p['id']) + b'\0' * 8
    out += s['aabb'] + s['bvh']['raw'] + s['tris'] + s['verts'] + s['groups'] + s['polys']
    for g in s['grids']:
        out += g['raw']
    return bytes(out)


# ------------------------------------------------------------------ acceleration-structure builders
# Reproduce the game tools' derived data from geometry (checked byte for byte on both corpora, `sbc.py rebuild`).

def poly_vertices(s, part, k):
    """global vertex indices of local polygon k of part."""
    a0, an, b0, bn, c0, cn = part['pairs']
    t0, t1 = struct.unpack_from('<HH', s['polys'], 10 * (a0 + k))
    vs = []
    for t in (t0, t1):
        if t != 0xFFFF:
            vs += [c0 + v for v in struct.unpack_from('<3H', s['tris'], 32 * (b0 + t) + 12)]
    return vs


def build_aabbs(s):
    """polygon AABBs: vertex min/max, widened by 1 on each axis (by 2 on an axis where the polygon is flat)."""
    import numpy as np
    V = np.frombuffer(s['verts'], '<f4').reshape(-1, 4)[:, :3]
    out = bytearray()
    one = np.float32(1)
    for p in s['parts']:
        for k in range(p['pairs'][1]):
            P = V[poly_vertices(s, p, k)]
            mn = P.min(0); mx = P.max(0)
            flat = mn == mx
            mn = np.where(flat, mn - one, mn) - one
            mx = np.where(flat, mx + one, mx) + one
            out += struct.pack('<3fI3f', *mn.tolist(), k, *mx.tolist())
    return bytes(out)


def grid_dims(bbox, cell):
    mn = struct.unpack_from('<3f', bbox, 0); mx = struct.unpack_from('<3f', bbox, 16)
    return max(1, int((mx[0] - mn[0]) // cell)), max(1, int((mx[2] - mn[2]) // cell))


def build_grid(s, pi, nx, nz):
    """uniform XZ grid over the part bbox: a cell lists every polygon whose AABB touches it (closed intervals)."""
    import numpy as np
    p = s['parts'][pi]
    a0, an = p['pairs'][0], p['pairs'][1]
    ab = np.frombuffer(s['aabb'], np.dtype([('mn', '<f4', 3), ('i', '<u4'), ('mx', '<f4', 3)]))[a0:a0 + an]
    mn = np.frombuffer(p['bbox'][0:12], '<f4'); mx = np.frombuffer(p['bbox'][16:28], '<f4')
    cx = np.float32((mx[0] - mn[0]) / np.float32(nx)); cz = np.float32((mx[2] - mn[2]) / np.float32(nz))
    lists = {}
    for ix in range(nx):
        x0 = np.float32(mn[0] + np.float32(ix) * cx); x1 = np.float32(x0 + cx)
        sx = (ab['mn'][:, 0] <= x1) & (ab['mx'][:, 0] >= x0)
        for iz in range(nz):
            z0 = np.float32(mn[2] + np.float32(iz) * cz); z1 = np.float32(z0 + cz)
            lists[(ix, iz)] = np.nonzero(sx & (ab['mn'][:, 2] <= z1) & (ab['mx'][:, 2] >= z0))[0]
    offs = {}; flat = []
    for ix in range(nx):                       # lists stored x-major
        for iz in range(nz):
            offs[(ix, iz)] = len(flat); flat += lists[(ix, iz)].tolist()
    out = bytearray(b'grco' + struct.pack('<I', 0x77c09c94) + p['bbox'] + struct.pack('<HHBB', nx, nz, 1, 1))
    for iz in range(nz):                       # table z-major
        for ix in range(nx):
            out += struct.pack('<II', len(lists[(ix, iz)]), offs[(ix, iz)])
    out += struct.pack('<I', len(flat)) + struct.pack('<%dH' % len(flat), *flat)
    return dict(raw=bytes(out), nx=nx, nz=nz, n=len(flat))


def rebuild_check(root):
    """rebuild AABBs + grids of every SBC under root (either game, grid dims taken from the file), compare bytes."""
    import collections
    c = collections.Counter()
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if not (f.endswith('.sbc') or f.endswith('.51fc779f')): continue
            try: s = parse(open(os.path.join(dp, f), 'rb').read())
            except (AssertionError, ValueError): c['unparsed'] += 1; continue
            c['aabb ok' if build_aabbs(s) == s['aabb'] else 'aabb diff'] += 1
            for pi, g in enumerate(s['grids']):
                c['grid ok' if build_grid(s, pi, g['nx'], g['nz'])['raw'] == g['raw'] else 'grid diff'] += 1
    print(root, dict(c))


# ------------------------------------------------------------------ 4U -> GU

def _zero_bvh_pad(raw):
    b = bytearray(raw)
    nn = struct.unpack_from('<I', b, 48)[0]
    for i in range(nn):
        struct.pack_into('<I', b, 64 + 112 * i + 12, 0)
    return bytes(b)


# Group words (the attribute vocabulary is shared: every 4U value of w0, w2, triangle and polygon bytes also occurs
# in GU files; w1 low byte 0x21 is the only 4U value GU never uses -> 0x23, the value GU's Fortress camp (modelled on
# the 4U Battlequarters camp, where 4U has 0x21) uses. G.)
W1_B0_MAP = {0x21: 0x23}
GU_GROUP_W6 = 0x02ac8b30          # constant left-over pointer in all 6472 GU group records (4U: real pointers)


def _groups_gu(g):
    b = bytearray(g)
    for i in range(len(b) // 32):
        w = list(struct.unpack_from('<8I', b, 32 * i))
        w[1] = (w[1] & ~0xFF) | W1_B0_MAP.get(w[1] & 0xFF, w[1] & 0xFF)
        w[5], w[6], w[7] = 0, GU_GROUP_W6, 0
        struct.pack_into('<8I', b, 32 * i, *w)
    return bytes(b)


def convert_4u(d, rebuild=True):
    """4U SBC bytes -> GU SBC bytes. Geometry, attributes, part ids and BVH topology kept; polygon AABBs and grids
    rebuilt with the game tools' rules (identical to the 4U ones: asserted)."""
    s = parse(d)
    assert s['ver'] == '4u'
    s = dict(s)
    s['bvh'] = dict(s['bvh'], raw=_zero_bvh_pad(s['bvh']['raw']))
    s['groups'] = _groups_gu(s['groups'])
    if s.get('nogrid'):                 # the grid-less 4U variant (parse): AABBs by the game tools' rule, 1 x 1 grids
        s['aabb'] = build_aabbs(s)
        s['grids'] = [build_grid(s, pi, 1, 1) for pi in range(len(s['parts']))]
    elif rebuild:
        assert build_aabbs(s) == s['aabb'], 'polygon AABB rebuild differs from 4U'
        for pi, g in enumerate(s['grids']):
            assert build_grid(s, pi, g['nx'], g['nz'])['raw'] == g['raw'], 'grid rebuild differs from 4U'
    out = write_gu(s)
    t = parse(out)
    for k in ('tris', 'verts', 'polys', 'aabb'):
        assert t[k] == s[k]
    return out


# ------------------------------------------------------------------ CLI

def info(s):
    print('%s parts %d groups %d polys %d tris %d verts %d bvh nodes %d' % (
        s['ver'], len(s['parts']), s['nG'], s['nA'], s['nB'], s['nC'], s['bvh']['nodes']))
    print(' bbox', ['%.1f' % x for x in struct.unpack('<8f', s['bbox'])])
    for p, g in zip(s['parts'], s['grids']):
        print(' part id %d pairs %s grid %dx%d list %d' % (p['id'], p['pairs'], g['nx'], g['nz'], g['n']))


def selftest(root):
    n = bad = 0
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if not (f.endswith('.sbc') or f.endswith('.51fc779f')): continue
            d = open(os.path.join(dp, f), 'rb').read()
            s = parse(d)
            if s['ver'] != 'gu': continue
            n += 1
            w = write_gu(s)
            if w != d:
                bad += 1
                k = next(i for i in range(min(len(w), len(d))) if w[i] != d[i]) if len(w) == len(d) else -1
                print('MISMATCH', f, len(d), len(w), 'first diff', k)
    print('GU files %d, byte-identical %d' % (n, n - bad))
    return bad == 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'info':
        info(parse(open(sys.argv[2], 'rb').read()))
    elif cmd == 'selftest':
        sys.exit(0 if selftest(sys.argv[2]) else 1)
    elif cmd == 'conv':
        open(sys.argv[3], 'wb').write(convert_4u(open(sys.argv[2], 'rb').read()))
    else:
        raise SystemExit(__doc__)
