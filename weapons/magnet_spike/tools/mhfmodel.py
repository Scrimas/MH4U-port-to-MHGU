"""mhfmodel.py : MHF effect meshes (model0.fmod) as GU effect models (rigid MOD + MRL + texture), for mhffx2gu.py (the
3-D world-oriented particles) and msgun.py (the shot's hand piece).

GU side (C unless marked):
- MOD: the rigid effect format of GU's weapon-effect models (w00.arc effect\\base\\cm010_000 and 20 others):
  version 0xD4, one material, vertex format 0x207D603B, stride 24 (f32 position, 10:10:10:2 normal, f16 uv,
  u8 RGBA), triangle runs with a 0xFFFF after every mesh (efl4u2gu.convert_effect_mod), metadata (1000, 3000, 1, 0).
- Vertex colour: Capcom's weapon-effect MODs store RGB 0x7f grey on every vertex (w00: 7f7f7f on 13 / 15 files,
  6d / 5b / 54 on the others) and the per-vertex opacity in A (edge fades: A 0 on the rims). Their neutral is 0x7f
  (S: the effect shader doubles it); MHF's vertex colours are 0..255 with 255 neutral -> RGB / 2, A kept.
  (msgun test 18 wrote (0, 0, 0, 255), efl4u2gu's rule for a different material: the gun did not show.)
- UV: fmod.py flips v (MHF's GL-style origin); GU samples top-down as mhffx2gu.bake does -> (u, 1 - v).
  (msgun test 18 wrote the flipped v: the wrong half of the atlas.)
- Texture: BC3 (GU effect textures; test 19 RGBA8 overflowed the class arc, mhffx2gu TEX_FMT).
- MRL: em024 cm101_000 material 0 = efl4u2gu's efx_blend (BSBlendAlpha, tAlbedoMap), the one its converted effect
  models drew with in the monster ports; test 19 / 20 used w00 cm010_000's (the material of 328 / 429 GU
  effect-model materials) and no model showed (S). Every GU effect material is BSBlendAlpha; the unit's blend byte
  picks add / blend (C: 0xa9958c -> particle +0x18 -> 0xb007fc in the draw 0xc90b50, after the material's state).
  Its features (notes/gu-efl-units.md "Model look"): FUVTransformOffset (the unit's UV layer 0 lands in fUVTransform,
  C), FDiffuseVertexColorMD (the vertex colour; x2 of the 0x7f neutral S / G), FEmissionConstantEflEmu (the unit
  colour -> fDiffuseColor, C), DSZTestWrite, RSMeshCN (S: depth write, no cull)."""
import os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), 'tools')
if ROOT_TOOLS not in sys.path: sys.path.append(ROOT_TOOLS)
import fmod

EFX_GU, STRIDE = 0x207D603B, 24
T_TEX, T_MRL, T_MOD = 0x241f5deb, 0x2749c8a8, 0x58a15856
MAT = 'XfBAW_0__m00_'                                  # the material name of cm010_000's MOD
MAT_TEMPLATE = ('/nativeNX/arc/enemy/em024_00.arc', 'effect\\base\\cm101_000', 0)   # efl4u2gu's efx_blend: the
# material its converted effect models drew with in the monster ports (test 20: w00 cm010_000's showed nothing, S)
NEUTRAL = 127.0


def _mrl_templates():
    import mrl_build
    mrl_build.TEMPLATES['efx_ms'] = MAT_TEMPLATE
    return mrl_build


def mesh_part(src, mi, P=None, N=None):
    """MHF mesh mi -> (P (n, 3) cm, N (n, 3), UV (n, 2) GU, COL (n, 4) uint8, triangles); P / N override the
    positions / normals (msgun's transformed parts)"""
    m = src.meshes[mi]
    P = np.array(m['pos'], float) if P is None else np.asarray(P, float)
    N = np.array(m['normal'], float) if N is None else np.asarray(N, float)
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    UV = np.array([(u, 1.0 - v) for u, v in m['uv']], float)
    c = src.colours[mi]
    if c is None:
        col = np.tile([NEUTRAL, NEUTRAL, NEUTRAL, 255.0], (len(P), 1))
    else:
        col = np.concatenate([np.asarray(c, float)[:, :3] * (NEUTRAL / 255.0), np.asarray(c, float)[:, 3:4]], 1)
    col = np.clip(np.round(col), 0, 255).astype(np.uint8)
    return P, N, UV, col, [(a, b, c_) for a, b, c_, _ in fmod.triangles(m)]


def image_of(src, mi):
    """the source image index of mesh mi's first material"""
    m = src.meshes[mi]
    return src.tex_img[src.mat_tex[m['material_list'][0]]]


def merged(parts):
    """[(P, N, UV, COL, triangles)] -> one part (the triangles renumbered)"""
    tris, base = [], 0
    for P, _, _, _, t in parts:
        tris += [(a + base, b + base, c + base) for a, b, c in t]; base += len(P)
    return tuple(np.concatenate([p[k] for p in parts]) for k in range(4)) + (tris,)


def mod_bytes(parts):
    """[(P, N, UV, COL, triangles)] -> GU MOD bytes: the parts as one rigid mesh in group 0, material 0 (MAT). One
    mesh: a GU Model unit shows only the mesh its frame names (mhffx2gu.MODEL_FRAME, C)"""
    import mod4u2gu
    parts = [merged(parts)] if len(parts) > 1 else parts
    vb, ib, recs, envs, allp, ntri = bytearray(), bytearray(), [], [], [], 0
    for P, N, UV, COL, tris in parts:
        n = len(P)
        q = np.clip(np.round((N + 1.0) * 0.5 * 1023), 0, 1023).astype(np.uint32)
        nw = q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20) | (3 << 30)
        out = np.zeros((n, STRIDE), np.uint8)
        out[:, 0:12] = P.astype('<f4').view(np.uint8).reshape(n, 12)
        out[:, 12:16] = nw.astype('<u4').view(np.uint8).reshape(n, 4)
        out[:, 16:20] = UV.astype('<f2').view(np.uint8).reshape(n, 4)
        out[:, 20:24] = COL
        vstart = len(vb) // STRIDE
        vb += out.tobytes()
        ntri += len(tris)
        idx = []
        for a, b, c in tris: idx += [vstart + a, vstart + b, vstart + c, 0xFFFF]
        if idx: idx.pop()
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
    hdr += struct.pack('<4f4f4f', *centre, radius, *lo, 0.0, *hi, 0.0)
    hdr += struct.pack('<3IB3xI', 1000, 3000, 1, 0, len(envs))     # cm010_000's metadata
    assert len(hdr) == 0x84
    out = hdr + groups + mats + b''.join(recs) + b''.join(envs) + bytes(vb) + bytes(ib)
    assert len(out) == end
    return out + b'\0' * 4


class Models:
    """one GU model per MHF mesh (or per named part list), one texture per MHF source image; entries() in load order
    (textures, then each model's MRL and MOD: GU resolves names while loading)"""
    def __init__(self, src, rom, prefix='effect\\base\\ms_m'):
        self.src, self.rom, self.prefix = src, rom, prefix
        self.tex = {}         # image index -> texture path
        self.mods = {}        # key -> (path, MRL bytes, MOD bytes)

    def texture(self, img):
        if img not in self.tex:
            self.tex[img] = '%stex%02d_HQ_NOMIP' % (self.prefix, img)
        return self.tex[img]

    def model(self, key, parts, img, path=None):
        """key -> model path; parts as mod_bytes, img = the source image index they sample"""
        if key not in self.mods:
            mrl_build = _mrl_templates()
            path = path or '%s%03d' % (self.prefix, len(self.mods))
            t = self.texture(img)
            mrl = mrl_build.build(self.rom, [(MAT, 'efx_ms', {'tAlbedoMap': 1})], [t])
            self.mods[key] = (path, mrl, mod_bytes(parts))
        return self.mods[key][0]

    def mesh(self, mi):
        """MHF mesh mi as it is (cm, its own frame) -> model path"""
        return self.model(('mesh', mi), [mesh_part(self.src, mi)], image_of(self.src, mi))

    def entries(self):
        import tex
        out = [(p, T_TEX, tex.encode_gu(np.ascontiguousarray(self.src.images[i]), 'bc3', mips=1))
               for i, p in sorted(self.tex.items())]
        for path, mrl, mod in self.mods.values():
            out += [(path, T_MRL, mrl), (path, T_MOD, mod)]
        return out
