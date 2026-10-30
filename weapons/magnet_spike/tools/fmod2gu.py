"""fmod2gu.py : convert an MHF weapon model (FMOD + FSKL + PNG texture, e.g. dump/mhf/weapon/wk400) into an MHGU MOD
(version 0xD4) and pack it into a GU weapon arc -- the Phase 1 pipeline proof.

  fmod2gu.py mod WKDIR OUT.mod MATERIAL          the MOD alone (one mesh per FMOD mesh, material named MATERIAL)
  fmod2gu.py arc WKDIR TEMPLATE.arc OUT.arc      a test arc: the template GU weapon arc (one MOD) with its MOD and
                                                 albedo (BM) / alpha (BM+A) textures replaced; its MRL is kept, so
                                                 the MOD's material takes the template's first material name

MOD layout as tools/mod.py; conventions read off GU weapon / armor MODs and checked on the MHF data:
- bones: the FSKL tree in node order (index = node id); record {u8 id, u8 parent index, u8 mirror (own index), pad,
  f32 furthest skinned vertex, f32 |local position|, f32 local position[3]}; local matrices row-vector style
  (rotation rows = R^T, translation in the 4th row), R = Rz Ry Rx of the FSKL Euler angles (standard right-handed:
  arm bone 5's local +Z turned by its -40 deg rest rotation points along its vertices, 1168 / 1168 MHF triangles
  and GU's strips both have cross(b - a, c - a) along the normals); inverse bind = S(cube) T(AABB min) W^-1, the
  position dequantisation folded in as in every GU MOD.
- vertices: GU 0x14D40022 (28 B, 3 weights) via tools/mod4u2gu.encode_gu_vertices; positions in the unit cube of the
  AABB; FMOD weights are percent of skeleton bones (no bone list on Magnet Spike models).
- indices: each triangle its own strip, 0xFFFF between, one 0xFFFF after the mesh (as mod4u2gu's alpha splits).
- envelopes: mod4u2gu.envelopes_for; one group (0); metadata (1000, 3000, light group | 0x80000000, 0) as GU weapons.
Not done here (later phases): GU edge meshes, group-100 proxy meshes, a proper MRL, the GU weapon attach offset."""
import math, os, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'tools'))
import fmod, fskl
import mod4u2gu, arcpack, tex
from msgrip import TURN

T_TEX, T_MRL, T_MOD = 0x241f5deb, 0x2749c8a8, 0x58a15856
GU_FMT, STRIDE = 0x14D40022, 28


def euler(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def skeleton(bones):
    """-> nodes in order, parent index list, local (column-vector) 4x4s, world 4x4s; the roots carry msgrip.TURN"""
    by = {b['node']: b for b in bones}
    order = sorted(by)
    assert order == list(range(len(order))), 'FSKL node ids must be 0..n-1'
    local, world = {}, {}
    turn = np.eye(4); turn[:3, :3] = TURN
    def walk(n):
        b = by[n]; L = np.eye(4); L[:3, :3] = euler(b['rot']); L[:3, 3] = b['pos']
        if b['parent'] < 0: L = turn @ L
        local[n] = L; world[n] = (world[b['parent']] if b['parent'] >= 0 else np.eye(4)) @ L
        c = b['child']
        while c >= 0: walk(c); c = by[c]['sibling']
    for b in bones:
        if b['parent'] < 0: walk(b['node'])
    return order, [by[n]['parent'] for n in order], local, world, by


def build_mod(fm, fs, material):
    meshes = fmod.parse(fm); _, bones = fskl.parse(fs)
    order, parents, local, world, by = skeleton(bones)
    nb = len(order)
    allpos = np.concatenate([np.array(m['pos'], float) for m in meshes]) @ TURN.T
    lo, hi = allpos.min(0), allpos.max(0); cube = float((hi - lo).max())
    vb = bytearray(); ib = bytearray(); recs = []; envs = []; ntri = 0; furthest = np.zeros(nb)
    for mi, m in enumerate(meshes):
        P = np.array(m['pos'], float) @ TURN.T; n = len(P)
        N = np.clip(np.round(np.array(m['normal'], float) @ TURN.T * 127), -127, 127).astype(np.int8)
        N = np.concatenate([N, np.full((n, 1), 127, np.int8)], 1)
        UV = np.array(m['uv'], float) if m['uv'] else np.zeros((n, 2))
        gb = np.zeros((n, 4), np.int64); w = np.zeros((n, 4))
        for i, ws in enumerate(m['weights']):
            ws = sorted(ws, key=lambda t: -t[1])[:4]
            for k, (b, pc) in enumerate(ws):
                gb[i, k] = m['bones'][b] if m['bones'] else b; w[i, k] = pc / 100.0
        for i in range(n):
            for k in range(4):
                if w[i, k] > 0:
                    furthest[gb[i, k]] = max(furthest[gb[i, k]], np.linalg.norm(P[i] - world[gb[i, k]][:3, 3]))
        tan = np.zeros((n, 4), np.int8); tan[:, 0] = 127; tan[:, 3] = 127
        enc, nw = mod4u2gu.encode_gu_vertices((P - lo) / cube, N, UV, gb, w, tan)
        vstart = len(vb) // STRIDE
        vb += enc.tobytes()
        tris = fmod.triangles(m); ntri += len(tris)
        idx = []
        for a, b, c, _ in tris: idx += [vstart + a, vstart + b, vstart + c, 0xFFFF]
        idx.pop()
        istart = len(ib) // 2
        ib += struct.pack('<%dH' % len(idx), *idx) + b'\xff\xff'
        e = mod4u2gu.envelopes_for(P, gb, w); envs += e
        d0 = 0 | (0 << 12) | (0xFF << 24)
        d1 = 1 | (max(3, nw) << 3) | (STRIDE << 16) | (4 << 24)
        recs.append(struct.pack('<HHIIIIIIIIBBHHHI', 0xEFFF, n, d0, d1, vstart, 0, GU_FMT, istart, len(idx), 0, 0,
                                len(e), mi + 1, vstart, vstart + n - 1, 0))
    # bones: records, local matrices, inverse binds, remap
    q = np.eye(4); q[0, 0] = q[1, 1] = q[2, 2] = cube; q[:3, 3] = lo   # normalised -> model (column-vector)
    brec = b''; bloc = b''; binv = b''; remap = bytearray(b'\xff' * 256)
    for i, nid in enumerate(order):
        b = by[nid]; p = parents[i]
        brec += struct.pack('<4B5f', nid, 255 if p < 0 else order.index(p), i, 0, float(furthest[nid]),
                            float(np.linalg.norm(b['pos'])), *[float(v) for v in local[nid][:3, 3]])
        bloc += struct.pack('<16f', *local[nid].T.flatten())             # row-vector storage = transpose
        binv += struct.pack('<16f', *(np.linalg.inv(world[nid]) @ q).T.flatten())
        remap[nid] = i
    bones_blk = brec + bloc + binv + bytes(remap)
    centre = (lo + hi) / 2; radius = float(np.linalg.norm(allpos - centre, axis=1).max())
    groups = struct.pack('<I12x4f', 0, *centre, radius)
    mats = material.encode('ascii').ljust(128, b'\0')
    o_b = 0x84; o_g = o_b + len(bones_blk); o_m = o_g + len(groups); o_me = o_m + len(mats)
    o_env = o_me + 48 * len(recs); o_vb = o_env + 144 * len(envs); o_ib = o_vb + len(vb); end = o_ib + len(ib)
    hdr = struct.pack('<4shHHHIII', b'MOD\0', 0xD4, nb, len(recs), 1, len(vb) // STRIDE, len(ib) // 2, ntri)
    hdr += struct.pack('<10I', len(vb), 0, 1, o_b, o_g, o_m, o_me, o_vb, o_ib, end)
    hdr += struct.pack('<4f8f', *centre, radius, *lo, 0.0, *hi, 0.0)
    hdr += struct.pack('<3IB3xI', 1000, 3000, 0x80000001, 0, len(envs))
    assert len(hdr) == 0x84
    out = hdr + bones_blk + groups + mats + b''.join(recs) + b''.join(envs) + bytes(vb) + bytes(ib)
    assert len(out) == end
    return out + b'\0' * 4


def png_of(tex_file):
    """MHF model texture block: u32 1, u32 12, u32 size, then the PNG"""
    b = open(tex_file, 'rb').read()
    n, off, size = struct.unpack_from('<III', b, 0)
    assert b[off:off + 4] == b'\x89PNG', 'not a PNG texture block'
    return b[off:off + size]


def gu_textures(png_bytes):
    """PNG -> (BC3 albedo TEX, BC4 TEX of the alpha = GU's BM+A, as armor4u2gu builds it) through tools/tex.py"""
    from PIL import Image
    import io
    img = np.array(Image.open(io.BytesIO(png_bytes)).convert('RGBA'))
    a = img[:, :, 3:4]
    return tex.encode_gu(img, 'bc3'), tex.encode_gu(np.concatenate([a, a, a, np.full_like(a, 255)], 2), 'bc4')


def build_arc(wkdir, template, out):
    ver, ents = arcpack.read(open(template, 'rb').read())
    mods = [e for e in ents if e[1] == T_MOD]
    assert len(mods) == 1, 'template arc must hold one MOD'
    mod_path = mods[0][0]
    import mod as modlib
    material = modlib.parse(mods[0][2])['material_names'][0]
    gm = build_mod(open(os.path.join(wkdir, '0.fmod'), 'rb').read(), open(os.path.join(wkdir, '1.fskl'), 'rb').read(),
                   material)
    bm, bma = gu_textures(png_of(os.path.join(wkdir, '2.tex')))
    new = []
    for path, th, data in ents:
        if th == T_MOD: data = gm
        elif th == T_TEX and path == mod_path + '_BM': data = bm
        elif th == T_TEX and path == mod_path + '_BM+A': data = bma
        new.append((path, th, data))
    open(out, 'wb').write(arcpack.build(new))
    return mod_path, material, len(gm)


if __name__ == '__main__':
    if sys.argv[1] == 'mod':
        wk, out, mat = sys.argv[2:5]
        open(out, 'wb').write(build_mod(open(os.path.join(wk, '0.fmod'), 'rb').read(),
                                        open(os.path.join(wk, '1.fskl'), 'rb').read(), mat))
    elif sys.argv[1] == 'arc':
        print(build_arc(*sys.argv[2:5]))
