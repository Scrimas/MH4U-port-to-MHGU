"""walk4u2gu.py : MH4U walk-on-monster strips (emd word 10) -> MHGU ground SBC files ("g"), one per (em, joint).

  walk4u2gu.py convert [OUTDIR]   OUTDIR/<em>_b<joint>.sbc + index.json (default dump/converted/dalamadur/walk)
  walk4u2gu.py selftest [OUTDIR]  GU em084_00 / em087_00 SBC: round trip + rebuild from geometry; then our outputs
  walk4u2gu.py dump [EM ...]      4U sets / strips, triangles, facing

4U input (class-study.md "Walking on the body"; C unless marked):
  emd header word 10 -> u32 set pointers closed by 0; set = 12-byte strips {u32 joint id, u32 n, u32 -> n x f32[3]
  joint-local vertices} closed by 0xffffffff.
  - joint id = model joint id: 0xb05478 maps it through the remap table [W+0x228] (255 -> joint 0).
  - triangle strip: the query 0x681c84 takes n - 2 triangles (v[i], v[i+1], v[i+2]) per strip, each vertex moved
    to world by the joint matrix (0x924148), and flips a hit normal with y < 0 -> two-sided, winding unused.
  - data (S, checked by `dump`): read with the alternating strip winding, every strip of em024 / em083 is
    consistent (adjacent normals agree) and its right-hand normal points at the joint origin on every triangle:
    inward. We orient each strip so the stored normal points away from the joint (the walked, outer side).
    "Up" is a world-space property of the pose; in joint space the outer normals point anywhere (em024 bind pose:
    head joint up, body joints from up to down), so no up-facing filter is possible here.
GU output (layout: sbc.py; model: GU's em084_00 / em087_00 g files, see selftest):
  - 1 part (id 0), 1 BVH node (leaf slot 0, the part box in all 4 slots); header = part = BVH box = vertex
    min / max (w 0; a flat axis widened by 1); polygon AABBs and grid (cell 300) from sbc.py's builders; vertices
    welded by exact position.
  - 1 polygon per triangle (tri1 0xffff, quad bytes ff), as GU's monster g files (em084 / em087: 1 quad in 478).
  - triangle normal = normalize((v1 - v0) x (v2 - v0)) (all 621629 GU triangles), group 0, both u32 0.
  - edge bytes +24..+26 (edge k = v[k] -> v[k+1 mod 3]), byte 27 = 0: 0 = open, several neighbours, neighbour
    in another group or folded back; else by dz = height of the neighbour's far vertex over this triangle's plane:
    4 concave (dz >= 5), 1 coplanar (|dz| < 0.01), 2 otherwise (S: calibrated on the GU corpus; 1 vs 2 on
    coplanar edges follows the source mesh's polygons, not geometry).
  - group words (GROUP): em084_00_g00 group 0 (Nakarkos' body ground, 16 of its 27 triangles) except the attribute
    index w1 >> 24, see ATTR.
"""
import json, os, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emdata4u as E  # noqa: E402
import paths  # noqa: E402
import sbc  # noqa: E402

OUT = os.path.join(paths.DUMP, 'converted/dalamadur/walk')
EMS = ('em024', 'em083', 'em110', 'em111')
SAME = {'em110': 'em024', 'em111': 'em083'}      # Shah halves: reuse the files when their walk sets are identical
CELL = 300                                        # grid cell of every GU monster SBC (nx = floor(extent / 300))
BVH_HASH = 0x77b17b24

# Ground attribute index (group w1 >> 24). GU: stage files use 0..0x1c / 0x32, monster g files 0x33..0x3e, one per
# piece (em012 0x33, em087 0x34..0x3c / 0x3e, em084 0x3d). Generic code keeps 18 monster slots 0x33..0x44 (0x5253e4,
# table 0x162c162: slot -> id 40116 + 100 k) and special-cases used values (0x5b19c: 0x33..0x35 -> owner em012 /
# em087; masks at 0xf35d34, 0x453cd0, em084 0x1069680). 0x3f..0x44 are free: one each for head and tail. G
ATTR = {'em024': 0x3f, 'em083': 0x40}
# (w0, w1 low bits, w2, w3, w4): em084_00_g00 group 0. w0 0x0200004c = em084 / em012 (creature bodies; em087's
# machine pieces 0x4d / 0x7d / 0x3c), w1 low byte 7, w2 0x40000000 = every monster g group (no stage file) | 0x40000
# (em084 bulk, most em087 pieces), w3 5, w4 0xffff (all monster g groups). w5..w7: 0, sbc.GU_GROUP_W6, 0. G
GROUP = (0x0200004c, 0x00000007, 0x40040000, 0x00000005, 0x0000ffff)


# ------------------------------------------------------------------ 4U strips

def walk_sets(emd):
    """emd word 10 -> [set] = [(joint id, float32 (n, 3) vertices)]"""
    u = lambda o: struct.unpack_from('<I', emd, o)[0]
    p, out = E.hw(emd, 10), []
    while u(p):
        o, st = u(p), []
        while u(o) != 0xFFFFFFFF:
            j, n, vp = struct.unpack_from('<3I', emd, o)
            st.append((j, np.frombuffer(emd, '<f4', 3 * n, vp).reshape(n, 3)))
            o += 12
        out.append(st); p += 4
    return out


def same_sets(a, b):
    return len(a) == len(b) and all(len(x) == len(y) and all(j == k and V.tobytes() == W.tobytes()
                                                             for (j, V), (k, W) in zip(x, y)) for x, y in zip(a, b))


def by_joint(sets):
    """{joint: (strips, [set indices])}; every set holding a joint must hold the same strips for it"""
    out = {}
    for si, st in enumerate(sets):
        cur = {}
        for j, V in st:
            cur.setdefault(j, []).append(V)
        for j, L in cur.items():
            if j not in out:
                out[j] = (L, [si]); continue
            assert len(out[j][0]) == len(L) and all(a.tobytes() == b.tobytes() for a, b in zip(out[j][0], L)), \
                'joint %d: set %d holds other strips than set %d' % (j, si, out[j][1][0])
            out[j][1].append(si)
    return dict(sorted(out.items()))


def normal(a, b, c):
    x = np.cross(b.astype(float) - a, c.astype(float) - a)
    return x / np.linalg.norm(x)


def strip_tris(V):
    """triangle strip -> (vertex triples, flipped, facing): alternating winding (i, i+1, i+2) / (i+1, i, i+2), the
    whole strip reversed when its normals point at the joint origin; facing = signs of dot(normal, centroid)"""
    T = [(i, i + 1, i + 2) if i % 2 == 0 else (i + 1, i, i + 2) for i in range(len(V) - 2)]
    side = [float(np.dot(normal(*V[list(t)]), V[list(t)].mean(0))) for t in T]
    flip = sum(side) < 0
    if flip:
        T = [(b, a, c) for a, b, c in T]; side = [-x for x in side]
    return T, flip, side


# ------------------------------------------------------------------ GU SBC

def bvh_one(bbox):
    """BVHC with one node: leaf slot 0 = part 0 (mask byte 0x10 x 4, idx 0), the part box in all 4 SoA slots"""
    mn = struct.unpack_from('<3f', bbox, 0); mx = struct.unpack_from('<3f', bbox, 16)
    node = b'\x10' * 4 + struct.pack('<4HI', 0, 0, 0, 0, 0) + struct.pack('<24f', *[c for c in mn + mx for _ in range(4)])
    return dict(raw=b'BVHC' + struct.pack('<3I', BVH_HASH, 1, 0) + bbox + struct.pack('<I12x', 1) + node, nodes=1)


def edge_bytes(V, T, N, G):
    """edge flags per triangle (4 bytes), rule in the module docstring"""
    ed = {}
    for t, tri in enumerate(T):
        for k in range(3):
            ed.setdefault(frozenset((tri[k], tri[(k + 1) % 3])), []).append(t)
    out = []
    for t, tri in enumerate(T):
        f = [0, 0, 0, 0]
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            nb = [x for x in ed[frozenset((a, b))] if x != t]
            if len(nb) != 1 or G[nb[0]] != G[t] or np.dot(N[t], N[nb[0]]) < -0.999:
                continue
            far = next(x for x in T[nb[0]] if x != a and x != b)
            dz = float(np.dot(V[far].astype(float) - V[a], N[t]))
            f[k] = 4 if dz >= 5 else 1 if abs(dz) < 0.01 else 2
        out.append(bytes(f))
    return out


def build(V, T, G, groups, N=None, flags=None, polys=None):
    """one-part GU SBC bytes from float32 vertices (n, 3), triangles (local vertex triples), per-triangle group, group
    records (32 B each); normals / edge bytes / polygons computed unless given (selftest passes GU's own)"""
    V = np.asarray(V, '<f4')
    if N is None:
        N = np.array([normal(*V[list(t)]) for t in T])
    if flags is None:
        flags = edge_bytes(V, T, N, G)
    if polys is None:
        polys = b''.join(struct.pack('<HH4BH', t, 0xFFFF, 255, 255, 255, 255, G[t]) for t in range(len(T)))
    tris = b''.join(struct.pack('<3f3HHI', *np.float32(N[t]).tolist(), *T[t], G[t], 0) + flags[t] + bytes(4)
                    for t in range(len(T)))
    verts = b''.join(struct.pack('<4f', *v.tolist(), 0.0) for v in V)
    mn, mx = V.min(0), V.max(0)
    flat = mn == mx                                 # a flat axis is widened by 1 (em087 g00 / g02)
    mn, mx = np.where(flat, mn - np.float32(1), mn), np.where(flat, mx + np.float32(1), mx)
    bbox = struct.pack('<8f', *mn.tolist(), 0.0, *mx.tolist(), 0.0)
    nA = len(polys) // 10
    s = dict(ver='gu', nG=len(groups) // 32, nA=nA, nB=len(T), nC=len(V), bbox=bbox, tris=tris, verts=verts,
             groups=groups, polys=polys, bvh=bvh_one(bbox),
             parts=[dict(bbox=bbox, pairs=(0, nA, 0, len(T), 0, len(V)), id=0)])
    s['aabb'] = sbc.build_aabbs(s)
    s['grids'] = [sbc.build_grid(s, 0, *sbc.grid_dims(bbox, CELL))]
    return sbc.write_gu(s)


def group_record(em):
    w0, w1, w2, w3, w4 = GROUP
    return struct.pack('<8I', w0, ATTR[em] << 24 | w1, w2, w3, w4, 0, sbc.GU_GROUP_W6, 0)


def convert_joint(em, strips):
    """strips of one joint -> (SBC bytes, info)"""
    key, V, T, flips = {}, [], [], 0
    for S in strips:
        tt, flip, _ = strip_tris(S)
        flips += flip
        ids = []
        for v in S:
            k = v.tobytes()
            if k not in key:
                key[k] = len(V); V.append(v)
            ids.append(key[k])
        T += [tuple(ids[i] for i in t) for t in tt]
    V = np.array(V, '<f4')
    d = build(V, T, [0] * len(T), group_record(em))
    return d, dict(triangles=len(T), vertices=len(V), strips=len(strips), flipped=flips,
                   bbox=[V.min(0).tolist(), V.max(0).tolist()])


def convert(out=OUT):
    os.makedirs(out, exist_ok=True)
    sets = {em: walk_sets(E.load_4u(em)['emd']) for em in EMS}
    index = []
    for em in EMS:
        src = SAME.get(em)
        if src and not same_sets(sets[em], sets[src]):
            raise SystemExit('%s walk sets differ from %s: add an ATTR entry and convert it on its own' % (em, src))
        for j, (strips, sl) in by_joint(sets[src or em]).items():
            name = '%s_b%03d.sbc' % (src or em, j)
            d, info = convert_joint(src or em, strips)
            if not src:
                open(os.path.join(out, name), 'wb').write(d)
            index.append(dict(em=em, bone=j, file=name, triangles=info['triangles'], bbox=info['bbox'], sets=sl,
                              strips=info['strips'], vertices=info['vertices'], **({'same_as': src} if src else {})))
            print('%s joint %3d sets %s strips %2d (reversed %2d) tris %3d verts %3d %s%s' % (
                em, j, sl, info['strips'], info['flipped'], info['triangles'], info['vertices'], name,
                ' (= %s)' % src if src else ''))
    json.dump(index, open(os.path.join(out, 'index.json'), 'w'), indent=1)
    print('wrote', out)


# ------------------------------------------------------------------ selftest

def gu_monster_sbc(ems=('em084_00', 'em087_00')):
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    from arc import arc_entries, arc_read
    rom = RomFS(paths.GU_ROMFS)
    for em in ems:
        d = rom.read('/nativeNX/arc/enemy/%s.arc' % em)
        for e in arc_entries(d):
            if e[1] == sbc.T_SBC:
                yield e[0].split('\\')[-1], arc_read(d, e)


def check_gu():
    """GU's own files: (1) parse + write_gu byte-identical, (2) build() from their geometry, groups, polygons,
    normals and edge bytes byte-identical (box, BVH, AABBs, grid, header), (3) our normal / edge rules vs theirs"""
    n = rt = rb = 0; nerr = 0.0; agree = {}
    for name, d in gu_monster_sbc():
        s = sbc.parse(d); n += 1
        rt += sbc.write_gu(s) == d
        V = np.frombuffer(s['verts'], '<f4').reshape(-1, 4)[:, :3]
        T = [struct.unpack_from('<3H', s['tris'], 32 * t + 12) for t in range(s['nB'])]
        G = [struct.unpack_from('<H', s['tris'], 32 * t + 18)[0] for t in range(s['nB'])]
        N = np.array([struct.unpack_from('<3f', s['tris'], 32 * t) for t in range(s['nB'])])
        F = [s['tris'][32 * t + 24:32 * t + 28] for t in range(s['nB'])]
        ok = len(s['parts']) == 1 and build(V, T, G, s['groups'], N, F, s['polys']) == d
        rb += ok
        if not ok:
            print('  rebuild differs:', name)
        nerr = max(nerr, max(np.abs(normal(*V[list(t)]) - N[i]).max() for i, t in enumerate(T)))
        kind = name.split('_')[-1][0]
        a = agree.setdefault(kind, [0, 0])
        for x, y in zip(edge_bytes(V, T, N, G), F):
            a[0] += sum(p == q for p, q in zip(x[:3], y[:3])); a[1] += 3
    print('GU em084_00 + em087_00: %d SBC, round trip byte-identical %d, rebuilt from geometry byte-identical %d'
          % (n, rt, rb))
    print('  normal rule max |diff| %.2g; edge byte rule agrees on %s edges' % (
        nerr, ', '.join('%s files %d / %d' % (k, *v) for k, v in sorted(agree.items()))))
    return rt == n and rb == n


def check_ours(out=OUT):
    """our files parse back; per joint: triangle count = sum(n - 2), box = 4U vertex min / max, vertices = the 4U
    vertices, triangles = the 4U strip triangles (as vertex sets), stored normals point away from the joint"""
    good = True
    try:
        idx = json.load(open(os.path.join(out, 'index.json')))
    except OSError:
        idx = None
    for em in EMS:
        sets = walk_sets(E.load_4u(em)['emd'])
        src = SAME.get(em)
        if src:
            same = same_sets(sets, walk_sets(E.load_4u(src)['emd']))
            print('%s walk sets identical to %s: %s' % (em, src, same)); good &= same
            continue
        for j, (strips, sl) in by_joint(sets).items():
            d, _ = convert_joint(em, strips)
            f = os.path.join(out, '%s_b%03d.sbc' % (em, j))
            disk = open(f, 'rb').read() == d if os.path.exists(f) else None
            s = sbc.parse(d)
            V = np.frombuffer(s['verts'], '<f4').reshape(-1, 4)[:, :3]
            P = np.vstack(strips)
            T = [struct.unpack_from('<3H', s['tris'], 32 * t + 12) for t in range(s['nB'])]
            N = np.array([struct.unpack_from('<3f', s['tris'], 32 * t) for t in range(s['nB'])])
            want = sorted(sorted(S[i + k].tobytes() for k in range(3)) for S in strips for i in range(len(S) - 2))
            have = sorted(sorted(V[v].tobytes() for v in t) for t in T)
            box = struct.unpack('<8f', s['bbox'])
            okbox = box[:3] == tuple(P.min(0).tolist()) and box[4:7] == tuple(P.max(0).tolist())
            outw = min(float(np.dot(N[i], V[list(t)].mean(0))) for i, t in enumerate(T))
            ok = (s['nB'] == sum(len(S) - 2 for S in strips) and okbox and want == have and outw > 0
                  and {v.tobytes() for v in V} == {v.tobytes() for v in P} and disk is not False)
            if idx is not None:
                e = next((x for x in idx if x['em'] == em and x['bone'] == j), None)
                ok &= e is not None and e['triangles'] == s['nB']
            good &= ok
            fl = np.frombuffer(b''.join(s['tris'][32 * t + 24:32 * t + 27] for t in range(s['nB'])), 'u1')
            print('%s joint %3d: %s tris %3d verts %3d parts %d groups %d grid %dx%d  box (%.0f %.0f %.0f)..(%.0f %.0f '
                  '%.0f) = 4U %s, triangles = 4U %s, outward min %.0f, edge bytes %s, file %s' % (
                      em, j, 'OK  ' if ok else 'FAIL', s['nB'], s['nC'], len(s['parts']), s['nG'], s['grids'][0]['nx'],
                      s['grids'][0]['nz'], *box[:3], *box[4:7], okbox, want == have, outw,
                      {int(a): int(c) for a, c in zip(*np.unique(fl, return_counts=True))}, {True: 'same', False: 'DIFFERS',
                                                                      None: 'not written'}[disk]))
    return good


def selftest(out=OUT):
    a = check_gu()
    b = check_ours(out)
    print('selftest', 'OK' if a and b else 'FAILED')
    return a and b


def dump(ems):
    for em in ems:
        sets = walk_sets(E.load_4u(em)['emd'])
        print(em, 'sets', [len(s) for s in sets])
        for si, st in enumerate(sets):
            for k, (j, V) in enumerate(st):
                T, flip, side = strip_tris(V)
                N = [normal(*V[list(t)]) for t in T]
                cons = min([float(np.dot(a, b)) for a, b in zip(N, N[1:])] or [1.0])
                print('  set %d strip %2d joint %3d n %d tris %d  adjacent normal dot min %.2f  4U winding %s  facing %s'
                      % (si, k, j, len(V), len(T), cons, 'inward (reversed)' if flip else 'outward',
                         ''.join('+' if x > 0 else '-' for x in side)))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'convert':
        convert(sys.argv[2] if len(sys.argv) > 2 else OUT)
    elif cmd == 'selftest':
        sys.exit(0 if selftest(sys.argv[2] if len(sys.argv) > 2 else OUT) else 1)
    elif cmd == 'dump':
        dump(sys.argv[2:] or EMS)
    else:
        raise SystemExit(__doc__)
