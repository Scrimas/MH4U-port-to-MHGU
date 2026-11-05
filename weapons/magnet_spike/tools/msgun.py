"""msgun.py : the shot's hand piece (MHF event 17, notes/effect-posts.md "Notes") as a GU effect model, for msbuild.py.

MHF (C unless marked): at f6 of actions 82 / 84 event 17 starts MS task kind 0 (0x10338670 -> 0x1004d700) on bone
18 (the -x hand) for 16 ticks (the event's parameter). Every tick it takes bone 18's matrix with the origin moved to
bone 18 + M18 (-4, -4, 2) and draws three meshes of the effect model pack (0x13, 0x74, 0x97 = our model0.fmod meshes
19, 116, 151) through the draw list 0x1ecde5e0 (callback 0x1004f7b0), each with 9 constants from 0x1004d4b0, the
first six (position, scale) x 0.95; read as position / scale / rotation (S), local = T R(Rz Ry Rx) S as MHF's motions.
Drawn white with the default blend (0x114067e0 mode 1).

GU: one rigid effect MOD (format 0x207D603B as tools/efl4u2gu.convert_effect_mod writes, the three parts baked into
the bone-18 frame), its texture (the pack's PNG 1, the meshes' only atlas) and an MRL on GU's blended effect material
(efx_blend, em024's cm101_000); one EFL entry = GU's one-shot Model unit (type 5, em001_00_500 entry 1: one
particle, once = emit type 17), life 32 frames, no motion, no spin, unit scale 1. The Model unit's fields used (GU
init 0xa9958c, C): +0x50 the model path; +0x90 / +0x98 / +0xa0 scale (value, range) x / y / z and +0xa8.. their
rates (0xa6b59c -> particle +0xd0 / +0x110); +0xd0.. rotation (value, range) and +0xe8.. angular speeds (0xa6adac);
+0x42 the colour curve (0 = the +0x48 colours). The MHF hand bone 18 frame = GU joint 12's (as every other effect on
a hand: msbuild.fx_post_tables, S). Vertex colour (0, 0, 0, 255) = Capcom's own conversion of colourless blended
effect meshes (efl4u2gu, C there), the unit colour white."""
import io, math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import fmod, mhffx2gu

MESHES = (19, 116, 151)
PARTS = (((0.0, -10.0, 8.5), (0.9, 0.9, 0.9), (-1.920, 0.0, 1.571)),
         ((-13.0, -18.0, 0.0), (0.3, 0.8, 0.3), (0.785, 1.571, -0.785)),
         ((-13.0, 0.0, -35.0), (2.5, 2.5, 2.0), (0.0, 1.571, 0.0)))
K = 0.95                     # 0x1004d4b0 scales position and scale (C)
ORIGIN = (-4.0, -4.0, 2.0)   # bone 18 + M18 (-4, -4, 2): the PEL record's offset
BONE, FRAME, LIFE = 18, 6, 32
ACTIONS = (82, 84)
MODEL = 'effect\\base\\ms_gun_000'
TEXTURE = MODEL + '_HQ_NOMIP'
EFL = mhffx2gu.EFL_DIR + '\\ms_gun'
KEY = ('gun', 0)             # the effect key of msbuild.fx_post_tables' rows
MAT = 'XfBAW_0__m00_'        # GU's effect material name (cm010_000)
UNIT_TEMPLATE = ('enemy/em001_00.arc', 'effect\\em\\em001\\em001_00_500', 1)
T_TEX, T_MRL, T_MOD = 0x241f5deb, 0x2749c8a8, 0x58a15856
EFX_GU, STRIDE = 0x207D603B, 24
POSTS = [(('act', a), FRAME, KEY, BONE, ORIGIN, 0, 'att') for a in ACTIONS]


def euler(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def build_mod(src):
    """-> GU MOD bytes: the three meshes, each T(K pos) R(rot) S(K scale), one material, rigid"""
    import mod4u2gu
    vb, ib, recs, envs, allp, ntri = bytearray(), bytearray(), [], [], [], 0
    for mi, (pos, scl, rot) in zip(MESHES, PARTS):
        m = src.meshes[mi]
        R = euler(rot)
        P = (np.array(m['pos'], float) * (K * np.array(scl))) @ R.T + K * np.array(pos)
        N = np.array(m['normal'], float) / np.array(scl)
        N = N @ R.T
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        UV = np.array(m['uv'], float)
        n = len(P)
        q = np.clip(np.round((N + 1.0) * 0.5 * 1023), 0, 1023).astype(np.uint32)
        nw = q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20) | (3 << 30)
        out = np.zeros((n, STRIDE), np.uint8)
        out[:, 0:12] = P.astype('<f4').view(np.uint8).reshape(n, 12)
        out[:, 12:16] = nw.astype('<u4').view(np.uint8).reshape(n, 4)
        out[:, 16:20] = UV.astype('<f2').view(np.uint8).reshape(n, 4)
        out[:, 20:24] = (0, 0, 0, 255)
        vstart = len(vb) // STRIDE
        vb += out.tobytes()
        tris = fmod.triangles(m); ntri += len(tris)
        idx = []
        for a, b, c, _ in tris: idx += [vstart + a, vstart + b, vstart + c, 0xFFFF]
        idx.pop()
        istart = len(ib) // 2
        ib += struct.pack('<%dH' % len(idx), *idx) + b'\xff\xff'
        e = mod4u2gu.envelopes_for(P, None, None); envs += e
        d0 = 0 | (0 << 12) | (0xFF << 24)                       # group 0, material 0, lod 255 (cm010_000)
        d1 = 1 | (1 << 8) | (STRIDE << 16) | (4 << 24)          # visible, alpha, stride, strips (cm010_000)
        recs.append(struct.pack('<HHIIIIIIIIBBHHHI', 0xE4C1, n, d0, d1, vstart, 0, EFX_GU, istart, len(idx), 0, 0,
                                len(e), len(recs) + 1, vstart, vstart + n - 1, 0))
        allp.append(P)
    allp = np.concatenate(allp)
    lo, hi = allp.min(0), allp.max(0)
    centre = (lo + hi) / 2; radius = float(np.linalg.norm(allp - centre, axis=1).max())
    groups = struct.pack('<I12x4f', 0, *centre, radius)
    mats = MAT.encode('ascii').ljust(128, b'\0')
    o_g = 0x84; o_m = o_g + len(groups); o_me = o_m + len(mats)
    o_env = o_me + 48 * len(recs); o_vb = o_env + 144 * len(envs); o_ib = o_vb + len(vb); end = o_ib + len(ib)
    hdr = struct.pack('<4shHHHIII', b'MOD\0', 0xD4, 0, len(recs), 1, len(vb) // STRIDE, len(ib) // 2, ntri)
    hdr += struct.pack('<10I', len(vb), 0, 1, 0, o_g, o_m, o_me, o_vb, o_ib, end)
    hdr += struct.pack('<4f8f', *centre, radius, *lo, 0.0, *hi, 0.0)
    hdr += struct.pack('<3IB3xI', 1000, 3000, 1, 0, len(envs))     # cm010_000's metadata
    assert len(hdr) == 0x84
    out = hdr + groups + mats + b''.join(recs) + b''.join(envs) + bytes(vb) + bytes(ib)
    assert len(out) == end
    return out + b'\0' * 4


def build_efl(gu_read):
    """the Model entry of em001_00_500 entry 1 with our model, scale 1, no spin / growth, white, 32 frames"""
    d = gu_read(UNIT_TEMPLATE[0], UNIT_TEMPLATE[1])
    head = d[:0x30]
    n, n2 = struct.unpack_from('<HH', d, 0x10)
    tail = struct.unpack_from('<%dI' % n2, d, 0x30 + 16 * n)
    ent = mhffx2gu._template(gu_read, UNIT_TEMPLATE)
    (te, el), (tu, u), (tm, em), (tv, mv) = ent
    assert tu == 5 and tm == 17, 'template entry is not a one-shot Model'
    u = bytearray(u[:0x140])                                    # the head + model block, the colour curve dropped
    u[3] = mhffx2gu.ALPHA_BLEND                                 # MHF's default blend (alpha)
    struct.pack_into('<f', u, 0x1c, 1.0)                        # size rate decay
    struct.pack_into('<4f', u, 0x28, 1.0, 0.0, 0.0, 0.0)        # size 1, no growth
    struct.pack_into('<HHHHHHHH', u, 0x38, 0, 0, 0, 0, 0, 0, 0, 0)   # no scale / colour curves
    u[0x48:0x50] = b'\xff' * 8                                   # white
    u[0x50:0x90] = MODEL.encode().ljust(0x40, b'\0')
    struct.pack_into('<6f', u, 0x90, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0)   # scale x / y / z
    struct.pack_into('<6f', u, 0xa8, *([0.0] * 6))                   # scale rates
    struct.pack_into('<3f', u, 0xc0, 1.0, 1.0, 1.0)
    struct.pack_into('<6f', u, 0xd0, *([0.0] * 6))                   # rotation
    struct.pack_into('<6f', u, 0xe8, *([0.0] * 6))                   # angular speed
    struct.pack_into('<HH', u, 0x130, 0, 0)                          # no rotation / scale curves
    em = bytearray(em)
    struct.pack_into('<III', em, 0, 0, LIFE, 0)                      # fade-in 0, hold 32, fade-out 0
    tails = [d[t + 0x30:t + 0x30 + 0x70] for t in tail]
    return mhffx2gu.write_efl(head, [[(te, el), (tu, bytes(u)), (tm, bytes(em)), (tv, mv)]], tails)


def build(gu_read, rom):
    """-> (arc entries [(path, type, bytes)] in load order, {KEY: groups}, report)"""
    sys.path.insert(0, os.path.join(mhffx2gu.ROOT, 'tools'))
    import tex, mrl_build, efl4u2gu        # efl4u2gu registers the efx_blend template
    src = mhffx2gu.Source()
    img = src.images[src.tex_img[src.mat_tex[src.meshes[MESHES[0]]['material_list'][0]]]]
    for mi in MESHES[1:]:
        assert src.tex_img[src.mat_tex[src.meshes[mi]['material_list'][0]]] == src.tex_img[
            src.mat_tex[src.meshes[MESHES[0]]['material_list'][0]]], 'the hand piece uses one atlas'
    mod = build_mod(src)
    mrl = mrl_build.build(rom, [(MAT, 'efx_blend', {'tAlbedoMap': 1})], [TEXTURE])
    ents = [(TEXTURE, T_TEX, tex.encode_gu(np.ascontiguousarray(img), 'rgba8', mips=1)),
            (MODEL, T_MRL, mrl), (MODEL, T_MOD, mod), (EFL, mhffx2gu.T_EFL, build_efl(gu_read))]
    return ents, {KEY: [(EFL, 1, (0.0, 0.0, 0.0))]}, ['hand piece: %s (%d B MOD, 3 meshes), %s' % (MODEL, len(mod), EFL)]
