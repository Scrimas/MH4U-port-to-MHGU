"""mod4u2gu.py : convert an MH4U rModel (MOD 0xE6) into an MHGU rModel (MOD 0xD4) -- prototype.

  mod4u2gu.py IN.mod OUT.mod        convert
  mod4u2gu.py check IN.mod OUT.mod  decode both and compare positions / weights / bones / UVs

What carries over unchanged: bones (records, local matrices, the "inverse bind" matrices that also hold the
position dequantisation: scale = cube side, translation = AABB min - bone position), remap table, groups,
material names, bounding sphere/box, index buffer (triangle strips, absolute indices), mesh order.
What changes:
  - vertices: 4U 36 B {f32 pos[3] normalised to [0,1], snorm8 N[4], f32 uv[2], u8 b0,b1, unorm8 w0,w1,
    snorm8 T[4], u8 b2,b3, unorm8 w2,w3} with palette-local bones (4U skin palettes, mesh byte +0x29)
    -> GU 0x14D40022 28 B "P3s_W1s_N4c_T4c_B4c_U2h_W2h": s16 pos[3] = round(p*32767), snorm16 w0, snorm8 N[4],
    snorm8 T[4], u8 b[4] (global bone indices), f16 uv[2] (v flipped: 1 - v), f16 w1,w2 (w3 = 1 - sum)
  - 4U skin palettes dropped; GU envelopes generated (one per bone a mesh uses: sphere, AABB, axis-aligned OBB)
  - header 0x84 B: XDx32 layout + metadata envelope count; lightGroup bit 31 set as in GU files
  - optional (convert push= / valpha=): tar meshes lifted along their normals; per-vertex alpha (4U N.w, no GU
    equivalent) turned into one mesh + material per alpha class (VALPHA_CLASSES, split_names)
  - optional (convert edges=True, used for armor and weapons): GU edge meshes (drawMode 0x20 / 0, format
    0x0CB68015) = degenerate quads along hard (normal-split) edges + corner fills, built as Capcom did (see
    EDGE_FMT notes). Off by default: the monster ships without them.
  - optional (convert vcolour=True, used for weapons): 4U 0x7BA7401B vertex-colour meshes -> GU 0xCBF6C01A
    (one bone + RGBA8 colour) in their own stream, as Capcom did (see COLOUR_GU notes); without it they are refused.
"""
import struct, sys
import numpy as np

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import mod as modlib

GU_FMT = 0x14D40022
GU_STRIDE = 28
# drawMode: GU draws its normal meshes with 0xEFFF; 0xE4C0 marks special proxy meshes (Rathian's hidden eye
# meshes, the second tail mesh, Kushala's break-state pieces). 4U uses 0xEDD7 / 0xECD3 for drawn meshes and
# 0xEEDA / 0xE6C8 for the same kind of proxies (eye material, groups 100+, the duplicate tail).
GU_DRAW_VISIBLE, GU_DRAW_PROXY = 0xEFFF, 0xE4C0
PROXY_4U = (0xEEDA, 0xE6C8)


def gu_drawmode(dm4):
    return GU_DRAW_PROXY if dm4 in PROXY_4U else GU_DRAW_VISIBLE


RIGID_4U = 0x82917009       # 24 B: f32 pos[3] (model space), snorm8 N[4], f32 uv[2]
RIGID_GU = 0x5E7F2030       # 28 B "P3f_N4c_T4c_U2h_U2h"
RIGID_STRIDE = 28

# vertex-colour meshes (looks helper, 2026-10-20; weapon glow meshes, e.g. 4U ken079 / sou_l,r087). Rules from the
# 17 4U 0x7BA7401B meshes of same-model weapon pairs (scratchpad looks/w2.py), all 17/17:
#   4U 0x7BA7401B 32 B = 0xD6784014 (f32 pos[3], snorm8 N[4], f32 uv[2], u8 b0 b1, unorm8 w0 w1) + RGBA8 colour;
#   w1 = 0 on every vertex (one bone) -> GU 0xCBF6C01A 24 B "1-weight + colour": s16 pos[3], u8 global bone of b0,
#   u8 0, N4c = the 4U normal bytes (w included), T4c = constant (0x49, 0x49, 0x49, 0x7F), f16 uv (u, 1 - v),
#   RGBA8 = the 4U colour bytes. Record: weights 1, stride 24, data1 alpha/shape/sort/binflip as 4U (0), own
#   stream, envelopes from its vertices (1 bone -> 1, Capcom: 16 of 17), drawMode 4U 0xECD3 -> 0xECF3.
#   Capcom quantises positions with floor(p * 32767); here round(), like every other mesh of the converter, so
#   the glow stays coplanar with the meshes it overlays.
COLOUR_4U = 0x7BA7401B
COLOUR_GU, COLOUR_STRIDE = 0xCBF6C01A, 24
COLOUR_DM = {0xECD3: 0xECF3}


def encode_gu_colour(d, m, x):
    """4U 0x7BA7401B mesh -> (GU 0xCBF6C01A vertex rows, normalised positions, global bones (n, 1), weights)."""
    st = x['stride']
    assert st == 32, st
    base = m['offsets']['vb'] + x['streamOff'] + x['vertexStart'] * st
    v = np.frombuffer(d[base:base + x['numVertices'] * st], np.uint8).reshape(-1, st)
    n = len(v)
    if (v[:, 27] != 0).any():
        raise SystemExit('0x7BA7401B mesh with a second bone weight: no 1-weight GU format')
    pos = np.frombuffer(v[:, 0:12].tobytes(), '<f4').reshape(-1, 3)
    uv = np.frombuffer(v[:, 16:24].tobytes(), '<f4').reshape(-1, 2)
    pal = m['skin_list'][x['envelopes']] if m['skin_list'] else list(range(256))
    pal = np.array(pal + [0] * (256 - len(pal)))
    gb0 = pal[v[:, 24].astype(np.int64)]
    out = np.zeros((n, COLOUR_STRIDE), np.uint8)
    out[:, 0:6] = np.clip(np.round(pos * 32767), 0, 32767).astype('<i2').view(np.uint8).reshape(n, 6)
    out[:, 6] = gb0
    out[:, 8:12] = v[:, 12:16]
    out[:, 12:16] = (0x49, 0x49, 0x49, 0x7F)
    out[:, 16:20] = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1).astype('<f2').view(np.uint8).reshape(n, 4)
    out[:, 20:24] = v[:, 28:32]
    return out, pos, gb0[:, None], np.ones((n, 1))


def read_4u_vertices(d, m, x):
    st = x['stride']
    base = m['offsets']['vb'] + x['streamOff'] + x['vertexStart'] * st
    v = np.frombuffer(d[base:base + x['numVertices'] * st], np.uint8).reshape(-1, st)
    pos = np.frombuffer(v[:, 0:12].tobytes(), '<f4').reshape(-1, 3)
    nrm = v[:, 12:16].view(np.int8)
    uv = np.frombuffer(v[:, 16:24].tobytes(), '<f4').reshape(-1, 2)
    if x['fmt'] in (0xF606F017, 0x01B36016) and st == 36:      # 4 weights + tangent
        b = np.concatenate([v[:, 24:26], v[:, 32:34]], 1).astype(np.int64)
        w = np.concatenate([v[:, 26:28], v[:, 34:36]], 1).astype(np.float64) / 255.0
        tan = v[:, 28:32].view(np.int8)
    elif x['fmt'] == 0xD6784014 and st == 28:                  # 2 weights, no tangent
        b = np.concatenate([v[:, 24:26], np.zeros((len(v), 2), np.uint8)], 1).astype(np.int64)
        w = np.concatenate([v[:, 26:28], np.zeros((len(v), 2), np.uint8)], 1).astype(np.float64) / 255.0
        tan = np.zeros((len(v), 4), np.int8)
    elif x['fmt'] == 0x43FB3015 and st == 32:                  # 2 weights + tangent: the 36-B layout minus b2 b3 w2 w3
        b = np.concatenate([v[:, 24:26], np.zeros((len(v), 2), np.uint8)], 1).astype(np.int64)
        w = np.concatenate([v[:, 26:28], np.zeros((len(v), 2), np.uint8)], 1).astype(np.float64) / 255.0
        tan = v[:, 28:32].view(np.int8)
    elif x['fmt'] == RIGID_4U and st == 24:
        return pos, nrm, uv, None, None, np.zeros((len(v), 4), np.int8)
    else:
        raise SystemExit('4U vertex format %#x (stride %d) not handled' % (x['fmt'], st))
    pal = m['skin_list'][x['envelopes']] if m['skin_list'] else list(range(256))
    pal = np.array(pal + [0] * (256 - len(pal)))
    gb = pal[b]
    gb[w == 0] = 0
    return pos, nrm, uv, gb, w, tan


def encode_gu_vertices(pos, nrm, uv, gb, w, tan):
    n = len(pos)
    order = np.argsort(-w, axis=1, kind='stable')
    w = np.take_along_axis(w, order, 1); gb = np.take_along_axis(gb, order, 1)
    s = w.sum(1, keepdims=True); s[s == 0] = 1; w = w / s
    out = np.zeros((n, GU_STRIDE), np.uint8)
    q = np.clip(np.round(pos * 32767), 0, 32767).astype('<i2')     # P3s: snorm16, positions are in [0, 1]
    out[:, 0:6] = q.view(np.uint8).reshape(n, 6)
    # W1s is SNORM16 (w0 = raw / 32767): on real GU vertices this reading gives an implied w3 = 1 - w0 - w1 - w2
    # that is never negative; reading it as UNORM16 (as the first version did) halves w0.
    w0 = np.clip(np.round(w[:, 0] * 32767), 0, 32767).astype('<i2')
    out[:, 6:8] = w0.view(np.uint8).reshape(n, 2)
    nn = nrm.copy(); nn[:, 3] = 127
    out[:, 8:12] = nn.view(np.uint8)
    out[:, 12:16] = tan.view(np.uint8)
    out[:, 16:20] = gb.astype(np.uint8)
    uvh = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1).astype('<f2')
    out[:, 20:24] = uvh.view(np.uint8).reshape(n, 4)
    wh = w[:, 1:3].astype('<f2')
    out[:, 24:28] = wh.view(np.uint8).reshape(n, 4)
    nweights = int((w > 1.0 / 512).sum(1).max()) if n else 1
    return out, nweights


def encode_gu_rigid(pos, nrm, uv, tan):
    n = len(pos)
    out = np.zeros((n, RIGID_STRIDE), np.uint8)
    out[:, 0:12] = pos.astype('<f4').view(np.uint8).reshape(n, 12)
    nn = nrm.copy(); nn[:, 3] = 127
    out[:, 12:16] = nn.view(np.uint8)
    out[:, 16:20] = tan.view(np.uint8)
    uvh = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1).astype('<f2').view(np.uint8).reshape(n, 4)
    out[:, 20:24] = uvh
    out[:, 24:28] = uvh
    return out


def envelopes_for(pos_model, gb, w):
    if gb is None:      # rigid: one envelope on "bone" 0 covering the mesh
        gb = np.zeros((len(pos_model), 1), np.int64); w = np.ones((len(pos_model), 1))
    out = []
    used = sorted(set(gb[w > 0].tolist()))
    for bone in used:
        sel = (gb == bone) & (w > 0)
        p = pos_model[sel.any(1)]
        lo, hi = p.min(0), p.max(0)
        c = (lo + hi) / 2
        r = float(np.linalg.norm(p - c, axis=1).max())
        half = (hi - lo) / 2
        obb = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, c[0], c[1], c[2], 1]
        out.append(struct.pack('<I12x4f8f16f4f', bone, c[0], c[1], c[2], r, lo[0], lo[1], lo[2], 0.0,
                               hi[0], hi[1], hi[2], 0.0, *obb, half[0], half[1], half[2], 0.0))
    return out


def push_out(pos, nrm, dist):
    """move vertices `dist` (in normalised position units) along their normals."""
    n = nrm[:, :3].astype(np.float64)
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
    return pos + n / ln * dist


# ---- per-vertex alpha (tar-look agent, 2026-10-18)
# 4U em089's tar materials have CBMaterialStd bMaterialStdVertexAlpha = 1 and their vertices carry an alpha in the
# normal's 4th byte (0 / 63 / 95 / 127 -> /127; every other em089 mesh has 127). 4U draws a tar texel iff
# BM.a * vertex alpha * diffuse.w > alpha ref 75/255 (tools/mrl_anim.py TRACK_MAP, mrl_build W7_*). GU's
# 0x14D40022 vertices have no vertex alpha (N.w = 127 on every GU mesh), so each split material's triangles are
# grouped by the mean vertex alpha of their 3 corners into VALPHA_CLASSES, one mesh + one material per class,
# and the class value multiplies the material's w (mrl_anim.gu_entries alpha). Triangles below the first class
# are dropped: 4U never draws them in Liquid (needs BM.a > 0.294 / (0.85 * a) > 1 for a < 0.346).
# (lo, hi, class alpha, name suffix): 4U tar vertex alphas cluster at 0.5 (head, tail, back) and 0.75 (arms, chest)
VALPHA_CLASSES = ((0.375, 0.625, 0.5, '_va50'), (0.625, 9.0, 0.75, '_va75'))


def split_names(names, valpha):
    """GU material list for a 4U list when the materials in `valpha` are split by vertex alpha:
    [(GU name, 4U name, class alpha or None)], each split material replaced in place by its classes."""
    out = []
    for n in names:
        if n in valpha:
            out += [(n + sfx, n, a) for lo, hi, a, sfx in VALPHA_CLASSES]
        else:
            out.append((n, n, None))
    return out


def strip_triangles(ib, start, count):
    """triangles (absolute vertex indices, all with the winding of a strip's first triangle) of a triangle strip
    with 0xFFFF restarts; degenerate triangles skipped."""
    idx = struct.unpack_from('<%dH' % count, ib, 2 * start)
    out, strip = [], []
    for v in idx + (0xFFFF,):
        if v != 0xFFFF:
            strip.append(v); continue
        for i in range(len(strip) - 2):
            a, b, c = strip[i:i + 3]
            if a == b or b == c or a == c: continue
            out.append((a, b, c) if i % 2 == 0 else (b, a, c))
        strip = []
    return out


# ---- edge meshes (looks helper, 2026-10-20). Every GU armor mesh with a hard edge (normals split along it) is
# preceded by an "edge" mesh that fills the cracks along those edges: degenerate quads whose two sides carry the
# two faces' vertex normals (zero area at rest; they open up when vertices are pushed along their normals).
# Rules, from Capcom's 4U -> GU armor conversions (scratchpad looks/c2.py, c3.py, v1.py = edge_geometry run on the
# 4U meshes of all 2936 same-model pairs with GU mesh order = 4U order, compared with Capcom's edge meshes):
#  - hard edge = position edge shared by exactly 2 triangles with opposite directions whose vertex normals differ
#    at one end at least. A mesh gets an edge mesh iff it has one: 9260 of 9296 meshes agree. Quad triangles:
#    985108 equal, 9591 only ours, 11511 only Capcom's (~1 %: Capcom's adjacency comes from its source meshes; most
#    misses are 3-4-face edges it still paired), none with the other winding.
#  - quad for face F (edge a->b) and face B (edge b->a): triangles (aF, aB, bF), (aB, bB, bF), i.e. wound like
#    both neighbours; an end with equal normals collapses the quad into one triangle (aF, aB, b) / (a, bB, bF).
#  - corner fill: a position with k >= 3 distinct normals gets k - 2 triangles (c3.py, 400 GU MODs: 3302 of 3576
#    k=3 positions, 1318 of 1472 k=4), each wound to face along its normals' sum (k=3: 29090 of 29322 Capcom
#    triangles). For k >= 4 Capcom's choice of triangles is not reproduced (no simple fan / strip order fits);
#    here a fan over the ring of corner vertices.
#  - vertex 0x0CB68015 (20 B): s16 pos[3], u16 0, u8 bones[4], u8 weights[4] (sum 255), u32 normal 10:10:10:2
#    (component = round((c + 1) / 2 * 1023), w = 3); skin = the source vertex's (60512 of 60934 vertices).
#  - record: drawMode = normal drawMode & 0x1020 (0xEFFF -> 0x20, 0xE4C0 -> 0, 0xFFFF -> 0x1020: 6847 / 6847),
#    group / material / lod / weights / alpha = the normal mesh's (6847 / 6847), data1 shape 0 sort 0 binflip 1
#    bridge 1, stride 20, own stream (vertexStart 0, streamOff = byte offset, indices from 0), own envelopes
#    (bones its vertices use, boxes from its vertices).
#  - meshIndex: 4U meshes in 4U meshIndex order, each normal mesh takes the next number and its edge mesh the one
#    after (2936 / 2936); table sorted by (material, edge meshes first, meshIndex) (3326 / 3528).
# Weapons (wsnd helper, 2026-10-20; scratchpad wsnd/e2b.py, 598 same-model 4U -> GU weapon MOD pairs): same rule.
# Has an edge mesh 2229 / 2257 meshes, quad triangles 131135 equal / 863 only ours / 1194 only Capcom's, corner
# triangles 11011 / 3854 / 3836, record fields 1259 / 1259, numbering 598 / 598, table order 559 / 598. Capcom's
# edge vertex format follows the normal mesh's weight count: 1 -> 0xB0983013 (12 B), 2 -> 0xDB7DA014 (16 B),
# 3 -> 0x0CB68015 (11 / 11), and in 272 of 1259 edge meshes it shares one stream between them (vertexStart != 0,
# indices absolute in the stream); here each keeps its own stream, as Capcom's armor. Vertex-colour meshes get no
# edge mesh (Capcom: 131 / 132).
EDGE_FMT, EDGE_STRIDE = 0x0CB68015, 20


def pack_n10(nrm):
    """normals (n, >= 3) -> u32 10:10:10:2 as on Capcom's edge vertices."""
    n = np.asarray(nrm)[:, :3].astype(np.float64)
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
    c = np.clip(np.round((n / ln + 1) * 0.5 * 1023), 0, 1023).astype(np.uint32)
    return c[:, 0] | (c[:, 1] << 10) | (c[:, 2] << 20) | np.uint32(3 << 30)


def edge_vertices(enc, src, nrm):
    """0x0CB68015 edge vertices from the encoded GU normal-mesh vertices `enc` (GU_FMT rows) of the source vertices
    `src` and their 4U normals: same s16 position and bones, weights as u8 summing to 255 (rounding remainder on
    the largest = first), normal packed 10:10:10:2."""
    v = enc[src]
    n = len(v)
    out = np.zeros((n, EDGE_STRIDE), np.uint8)
    out[:, 0:6] = v[:, 0:6]
    out[:, 8:12] = v[:, 16:20]
    w0 = v[:, 6:8].copy().view('<i2').reshape(n).astype(np.float64) / 32767
    wh = v[:, 24:28].copy().view('<f2').reshape(n, 2).astype(np.float64)
    W = np.stack([w0, wh[:, 0], wh[:, 1], np.clip(1 - w0 - wh.sum(1), 0, 1)], 1)
    wq = np.clip(np.round(W * 255), 0, 255).astype(np.int64)
    wq[:, 0] += 255 - wq.sum(1)
    out[:, 12:16] = wq.astype(np.uint8)
    out[:, 16:20] = pack_n10(nrm[src]).astype('<u4').view(np.uint8).reshape(n, 4)
    return out


def edge_geometry(q, nkey, tris):
    """edge (crack-fill) mesh of one mesh. q: (n, 3) quantised positions, nkey: per-vertex normal as a tuple of
    numbers (equality = same normal; also orients the corner triangles), tris: [(i, j, k)] local vertex indices
    with the drawn winding.
    -> (src, strips): src[e] = source vertex of edge vertex e, strips = [[edge vertex indices]] (each one strip);
    None when the mesh has no hard edge."""
    P = [tuple(r) for r in np.asarray(q).tolist()]
    pe = {}
    for t in tris:
        if len({P[i] for i in t}) < 3: continue
        for u, v in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            pe.setdefault(frozenset((P[u], P[v])), []).append((u, v))
    vid, src = {}, []

    def V(i):
        k = (P[i], nkey[i])
        if k not in vid: vid[k] = len(src); src.append(i)
        return vid[k]
    strips, corner = [], {}
    for l in pe.values():
        if len(l) != 2: continue
        (a, b), (b2, a2) = l                  # face F runs a -> b, face B must run b -> a
        if P[b2] != P[b]: continue
        da, db = nkey[a] != nkey[a2], nkey[b] != nkey[b2]
        if not (da or db): continue
        aF, bF, aB, bB = V(a), V(b), V(a2), V(b2)
        strips.append([aF, aB, bF, bB] if da and db else [aF, aB, bF] if da else [aF, bB, bF])
        if da: corner.setdefault(P[a], []).append((aB, aF))      # reversed quad edges at the corner
        if db: corner.setdefault(P[b], []).append((bF, bB))
    for es in corner.values():
        nodes = list(dict.fromkeys(x for e in es for x in e))
        if len(nodes) < 3: continue
        nxt = {}
        for s, t in es: nxt.setdefault(s, t)
        pred = {t for s, t in es}
        ring, seen = [], set()
        for s0 in [s for s, t in es if s not in pred] + nodes:  # open chains first, then closed rings
            x = s0
            while x is not None and x not in seen:
                seen.add(x); ring.append(x); x = nxt.get(x)
        for i in range(1, len(ring) - 1):
            t = [ring[0], ring[i], ring[i + 1]]
            n0, n1, n2 = (np.asarray(nkey[src[j]], np.float64) for j in t)
            n0, n1, n2 = (x / (np.linalg.norm(x) or 1) for x in (n0, n1, n2))
            if np.cross(n1 - n0, n2 - n0) @ (n0 + n1 + n2) < 0: t = [t[0], t[2], t[1]]
            strips.append(t)
    return (src, strips) if strips else None


def valpha_classes(tris, alpha, base):
    """[triangles of class k] for k in VALPHA_CLASSES; alpha = per-vertex alpha of the mesh, base = its first
    vertex index."""
    out = [[] for _ in VALPHA_CLASSES]
    for t in tris:
        a = sum(alpha[i - base] for i in t) / 3.0
        for k, (lo, hi, _, _) in enumerate(VALPHA_CLASSES):
            if lo <= a < hi: out[k].append(t)
    return out


def convert(d, push=None, valpha=(), edges=False, vcolour=False, rebind=None):
    """rebind: a global bone id that takes every skinned vertex's whole weight (weapon4u2gu --shield-bone0: only when
    every bone the vertices use has that bone's bind, so the rest shape is unchanged).
    vcolour: convert 4U 0x7BA7401B vertex-colour meshes to GU 0xCBF6C01A (COLOUR_GU notes above) in their own
    stream after the normal vertices; their 4U indices must be local to the mesh (weapon4u2gu.normalize_4u).
    Without it such meshes are refused (read_4u_vertices).
    edges: also build GU's edge (crack-fill) meshes as Capcom did for converted armor and weapons (EDGE_FMT notes
    above): one per mesh with a hard edge, each in its own vertex stream after the normal vertices and its index
    run after the normal runs; mesh numbers and table order then follow Capcom's; header vertices / edges (=
    triangle count) include them. Off by default (monster: unchanged output).
    push: {material name: model units} moves those materials' vertices outward along their normals. em089's
    tar meshes are coplanar copies of body triangles (60-97 %) that 4U lifts only with a raster depth bias
    (RSMeshBias5..12); GU's own overlay meshes are offset in the geometry instead, so the converter can bake a
    small lift that does not depend on the depth bias.
    valpha: material names split by per-vertex alpha (see VALPHA_CLASSES); the GU material list is then
    split_names(material names, valpha), and each split mesh becomes one mesh per non-empty class (same vertices,
    new index lists appended to the index buffer as one strip per triangle)."""
    m = modlib.parse(d)
    assert m['version'] == 0xE6
    rigid = m['bones'] == 0
    L = m['invbind'][0][0] if not rigid else 1.0     # cube side (same on every bone)
    mn = np.array(m['aabb'][:3]) if not rigid else np.zeros(3)
    stride = RIGID_STRIDE if rigid else GU_STRIDE
    push = {m['material_names'].index(k): v for k, v in (push or {}).items() if k in m['material_names']}
    gnames = split_names(m['material_names'], set(valpha))
    gindex = {}                                      # 4U material index -> [GU material index per class]
    for gi, (gn, src, a) in enumerate(gnames):
        gindex.setdefault(m['material_names'].index(src), []).append(gi)
    ib = m['ib']
    if len(ib) < 2 * m['indices']:      # some 4U files end before their declared index count
        ib += ib[-2:] * ((2 * m['indices'] - len(ib)) // 2)
    ib = bytearray(ib)
    next_mesh_index = max([x['meshIndex'] for x in m['mesh_list']] + [0]) + 1
    # GU index buffer: every mesh's run followed by one 0xFFFF (all GU monster / stage / effect models: gap 1, value
    # 0xffff; GU's draw reads it). 4U runs are contiguous, so they are copied out one by one, each + 0xFFFF.
    ib_out = bytearray()
    assert not (edges and valpha), 'edge meshes and vertex-alpha splits are not combined'
    vb = bytearray()
    recs = []           # [mesh record fields, envelopes, GU material index, 4U mesh]
    pend = []           # edge meshes to build: (normal record index, edge_geometry result, inputs)
    pend_col = []       # vertex-colour meshes: (record index, GU vertex rows), placed after the normal vertices
    for x in m['mesh_list']:
        if vcolour and x['fmt'] == COLOUR_4U:
            enc, pos, gb, w = encode_gu_colour(d, m, x)
            e = envelopes_for(mn + pos * L, gb, w)
            gis = gindex[x['material']]
            assert len(gis) == 1, 'vertex-colour mesh with a split material'
            d0 = x['group'] | (gis[0] << 12) | (x['lod'] << 24)
            d1 = (1 | (x['shape'] << 1) | (x['sort'] << 2) | (1 << 3) | (x['alpha'] << 8) | (COLOUR_STRIDE << 16) |
                  (x['prim'] << 24) | (x['binflip'] << 30))
            istart = len(ib_out) // 2      # 4U indices of this mesh are local (weapon4u2gu.normalize_4u)
            ib_out += bytes(ib[2 * x['indexStart']:2 * (x['indexStart'] + x['numIndices'])]) + b'\xff\xff'
            recs.append(([COLOUR_DM.get(x['drawMode'], gu_drawmode(x['drawMode'])), x['numVertices'], d0, d1, 0, 0,
                          COLOUR_GU, istart, x['numIndices'], 0, 0, len(e), x['meshIndex'], 0, x['numVertices'] - 1, 0],
                         e, gis[0], x))
            pend_col.append((len(recs) - 1, enc))
            continue
        pos, nrm, uv, gb, w, tan = read_4u_vertices(d, m, x)
        if rebind is not None and gb is not None:
            gb = np.full_like(gb, rebind)
            w = np.zeros_like(w); w[:, 0] = 1
        if x['material'] in push:
            pos = push_out(pos, nrm, push[x['material']] / L)
        assert len(vb) == x['vertexStart'] * stride, 'meshes must be stored in vertex order'
        if rigid:
            enc, nweights, fmt = encode_gu_rigid(pos, nrm, uv, tan), 0, RIGID_GU     # GU rigid meshes: 0
        else:
            (enc, nweights), fmt = encode_gu_vertices(pos, nrm, uv, gb, w, tan), GU_FMT
            nweights = max(3, nweights)          # GU 0x14D40022 meshes only use 3 or 4
        vb += enc.tobytes()
        e = envelopes_for(mn + pos * L, gb, w)
        if edges and not rigid:          # hard edges on the positions as written (s16)
            q = enc[:, 0:6].copy().view('<i2').reshape(-1, 3)
            tris = [tuple(i - x['vertexStart'] for i in t) for t in strip_triangles(ib, x['indexStart'], x['numIndices'])]
            g = edge_geometry(q, [tuple(r) for r in nrm[:, :3].tolist()],
                              [t for t in tris if all(0 <= i < len(q) for i in t)])
            if g: pend.append((len(recs), g, enc, nrm, mn + pos * L, gb, w))
        # data1 alpha byte (RevilLib 'AlphaType'): 4U's tar meshes use 1 (2 for the head pieces g15 / g34), the body
        # 0 / 2. 2026-10-17 the tar meshes were set to 0 together with the depth lift and the template change (tar
        # became visible; the lift was the cause: arms appeared at TAR_LIFT 20). GU reads the byte only into the
        # draw-list SORT KEY (C, 0x893978..0x893a94: key = pass | (byte [| depth << 12]) << 5, mesh+8 = data1), so
        # it orders draws and changes no shading: the 4U value is kept for every mesh again (2026-10-18).
        alpha = x['alpha']
        d1 = (1 | (x['shape'] << 1) | (x['sort'] << 2) | (min(4, nweights) << 3) | (alpha << 8) |
              (stride << 16) | (x['prim'] << 24) | (x['binflip'] << 30))
        gis = gindex[x['material']]
        if len(gis) == 1:
            pieces = [(gis[0], x['indexStart'], x['numIndices'], x['meshIndex'])]
        else:                            # split by vertex alpha: one strip per triangle, restart-separated
            va = nrm[:, 3].astype(np.float64) / 127.0
            pieces = []
            for gi, tris in zip(gis, valpha_classes(strip_triangles(ib, x['indexStart'], x['numIndices']), va,
                                                    x['vertexStart'])):
                if not tris: continue
                idx = []
                for t in tris: idx += list(t) + [0xFFFF]
                idx.pop()
                start = len(ib) // 2
                ib += struct.pack('<%dH' % len(idx), *idx)
                mi = x['meshIndex'] if not pieces else next_mesh_index
                if pieces: next_mesh_index += 1
                pieces.append((gi, start, len(idx), mi))
        for gi, istart, icount, mi in pieces:
            run = bytes(ib[2 * istart:2 * (istart + icount)])
            istart = len(ib_out) // 2
            ib_out += run + b'\xff\xff'
            d0 = x['group'] | (gi << 12) | (x['lod'] << 24)
            recs.append(([gu_drawmode(x['drawMode']), x['numVertices'], d0, d1, x['vertexStart'], 0,
                          fmt, istart, icount, 0, 0, len(e), mi,
                          x['vertexStart'], x['vertexStart'] + x['numVertices'] - 1, 0], e, gi, x))
    for ri, enc in pend_col:
        recs[ri][0][5] = len(vb)               # own stream: vertexStart 0, streamOff = byte offset
        vb += enc.tobytes()
    n_normal, n_edge_v, n_edge_t = len(recs), 0, 0
    for ri, (src, strips), enc, nrm, pm, gb, w in pend:
        f, _, gi, x = recs[ri]
        s = np.asarray(src)
        so = len(vb)
        vb += edge_vertices(enc, s, nrm).tobytes()
        idx = []
        for t in strips: idx += t + [0xFFFF]
        idx.pop()
        istart = len(ib_out) // 2
        ib_out += struct.pack('<%dH' % len(idx), *idx) + b'\xff\xff'
        e = envelopes_for(pm[s], gb[s], w[s])
        d1 = 1 | (((f[3] >> 3) & 31) << 3) | (x['alpha'] << 8) | (EDGE_STRIDE << 16) | (x['prim'] << 24) | (3 << 30)
        recs.append(([f[0] & 0x1020, len(s), f[2], d1, 0, so, EDGE_FMT, istart, len(idx), 0, 0, len(e), 0,
                      0, len(s) - 1, 0], e, gi, x))
        n_edge_v += len(s); n_edge_t += sum(len(t) - 2 for t in strips)
    if edges:       # numbers: 4U meshIndex order, each normal mesh then its edge mesh; table (material, edge first, n)
        edge_of = {id(r[3]): r for r in recs[n_normal:]}
        cnt = 1
        for r in sorted(recs[:n_normal], key=lambda r: r[3]['meshIndex']):
            r[0][12] = cnt; cnt += 1
            if id(r[3]) in edge_of:
                edge_of[id(r[3])][0][12] = cnt; cnt += 1
        recs.sort(key=lambda r: (r[2], 0 if r[0][6] == EDGE_FMT else 1, r[0][12]))
    meshes = [struct.pack('<HHIIIIIIIIBBHHHI', *r[0]) for r in recs]
    envs = [b for r in recs for b in r[1]]
    n_indices = len(ib_out) // 2
    ib = bytes(ib_out)
    nb = m['bones']
    ob = m['offsets']['bones']
    bones = d[ob:ob + 24 * nb + 128 * nb + (256 if nb else 0)]
    groups = d[m['offsets']['groups']:m['offsets']['groups'] + 32 * m['groups']]
    mo = m['offsets']['materials']
    mats = b''.join(d[mo + 128 * m['material_names'].index(src):mo + 128 * m['material_names'].index(src) + 128]
                    if a is None else gn.encode('ascii').ljust(128, b'\0') for gn, src, a in gnames)
    o_b = 0x84
    o_g = o_b + len(bones)
    o_m = o_g + len(groups)
    o_me = o_m + len(mats)
    o_env = o_me + 48 * len(meshes)
    o_vb = o_env + 144 * len(envs)
    o_ib = o_vb + len(vb)
    end = o_ib + len(ib)
    hdr = struct.pack('<4shHHHIII', b'MOD\0', 0xD4, nb, len(meshes), len(gnames), m['vertices'] + n_edge_v, n_indices,
                      m['edges'] + n_edge_t)
    hdr += struct.pack('<10I', len(vb), 0, m['groups'], o_b if nb else 0, o_g, o_m, o_me, o_vb, o_ib, end)
    hdr += struct.pack('<4f8f', *m['sphere'], *m['aabb'])
    mid, low, light, bj = m['metadata']
    hdr += struct.pack('<3IB3xI', mid, low, light | 0x80000000, bj, len(envs))
    assert len(hdr) == 0x84, len(hdr)
    out = hdr + bones + groups + mats + b''.join(meshes) + b''.join(envs) + bytes(vb) + ib
    assert len(out) == end
    return out + b'\0' * 4


def check(d4, dg):
    m4 = modlib.parse(d4); mg = modlib.parse(dg)
    worst = dict(pos=0.0, w=0.0, uv=0.0)
    first_g = {}                         # vertex-alpha split meshes share their source mesh's vertices
    for xg in mg['mesh_list']:
        if xg['fmt'] not in (EDGE_FMT, COLOUR_GU): first_g.setdefault(xg['vertexStart'], xg)
    for x4 in m4['mesh_list']:
        if x4['fmt'] == COLOUR_4U: continue      # own stream (encode_gu_colour), not compared here
        xg = first_g[x4['vertexStart']]
        pos, nrm, uv, gb, w, tan = read_4u_vertices(d4, m4, x4)
        if gb is None:
            base = mg['offsets']['vb'] + xg['vertexStart'] * RIGID_STRIDE
            v = np.frombuffer(dg[base:base + xg['numVertices'] * RIGID_STRIDE], np.uint8).reshape(-1, RIGID_STRIDE)
            p = np.frombuffer(v[:, :12].tobytes(), '<f4').reshape(-1, 3)
            worst['pos'] = max(worst['pos'], float(np.abs(p - pos).max()))
            uvg = np.frombuffer(v[:, 20:24].tobytes(), '<f2').reshape(-1, 2).astype(float)
            worst['uv'] = max(worst['uv'], float(np.abs(uvg - np.stack([uv[:, 0], 1 - uv[:, 1]], 1)).max()))
            continue
        base = mg['offsets']['vb'] + xg['streamOff'] + xg['vertexStart'] * GU_STRIDE
        v = np.frombuffer(dg[base:base + xg['numVertices'] * GU_STRIDE], np.uint8).reshape(-1, GU_STRIDE)
        p = np.frombuffer(v[:, :6].tobytes(), '<u2').reshape(-1, 3) / 32767
        worst['pos'] = max(worst['pos'], float(np.abs(p - pos).max()))
        w0 = np.frombuffer(v[:, 6:8].tobytes(), '<i2') / 32767
        wh = np.frombuffer(v[:, 24:28].tobytes(), '<f2').reshape(-1, 2).astype(float)
        W = np.stack([w0, wh[:, 0], wh[:, 1], 1 - w0 - wh.sum(1)], 1)
        B = v[:, 16:20].astype(int)
        # compare per-bone weight sums
        for i in range(len(v)):
            a = {}; b_ = {}
            for k in range(4):
                a[gb[i, k]] = a.get(gb[i, k], 0) + w[i, k] / max(w[i].sum(), 1e-9)
                b_[B[i, k]] = b_.get(B[i, k], 0) + W[i, k]
            for key in set(a) | set(b_):
                worst['w'] = max(worst['w'], abs(a.get(key, 0) - b_.get(key, 0)))
        uvg = np.frombuffer(v[:, 20:24].tobytes(), '<f2').reshape(-1, 2).astype(float)
        worst['uv'] = max(worst['uv'], float(np.abs(uvg - np.stack([uv[:, 0], 1 - uv[:, 1]], 1)).max()))
    same_ib = mg['ib'][:len(m4['ib'])] == m4['ib']
    same_bones = (m4['bone_list'] == mg['bone_list'] and m4['invbind'] == mg['invbind'] and m4['remap'] == mg['remap'])
    print('meshes', len(mg['mesh_list']), 'envelopes', mg['envCount'], '=', sum(x['envelopes'] for x in mg['mesh_list']),
          '| max err pos %.2e (1 step = %.2e) weights %.4f uv %.4f' % (worst['pos'], 1 / 32767, worst['w'], worst['uv']),
          '| index buffer identical', same_ib, '| bones/matrices/remap identical', same_bones)


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(open(sys.argv[2], 'rb').read(), open(sys.argv[3], 'rb').read())
    else:
        open(sys.argv[2], 'wb').write(convert(open(sys.argv[1], 'rb').read()))
