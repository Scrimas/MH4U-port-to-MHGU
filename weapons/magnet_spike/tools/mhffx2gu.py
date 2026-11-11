"""mhffx2gu.py : MHF effects (mhffx.py) -> GU effect files (EFL + sprite atlas TEX + EAN), for msbuild.py.
Formats: notes/assets.md "## Effects" (MHF) and notes/gu-efl-units.md (GU). C / S / G marks as there.

What a converted particle is (one GU entry per MHF particle; the MHF count of a burst = that many entries):
- a world-oriented 3-D mesh (not flat in x / y: nonflat) -> a GU Model unit on the mesh as an effect model
  (mhfmodel.py, Builder.model_unit; test 18: 404 / 942 particles use such meshes and their sprites were empty);
- else the MHF mesh baked into a sprite (camera-facing ones after their spawn rotation x / y and relative scale,
  bake view); its triangles are rasterised with their
  atlas texture x vertex colour into a square cell centred on the mesh origin (the particle position), so a GU
  Billboard of that cell covers what MHF's billboarded mesh covers (shaped meshes too: 13-84-vertex glows, rays);
- unit = cParticleGeneratorBillboard (type 0) from GU's em001_00_500 entry 0 (one particle, once: emit type 0x11,
  0xa5a900, C; no motion: move kind 0, S), its element / emit / move blocks as they are, the emit block's hold B =
  the MHF life (fade-in A / fade-out C 0: 0xaed0d0, C);
- the MHF burst frame D: the particle spawns with the effect and stays invisible (alpha 0) until D, every key shifted
  by D (GU's start wait comes from the poster, not the unit: 0xa5abc4 case 0, C);
- scale curve (unit +0x3a, 0xa6a2d0, C): key = (base - range) x curve x R, random range 2 range x curve x R (MHF
  scale = (base + U range) x curve, U in [-1, 1); GU = value + r range, r in [0, 1) per particle, C); R = the
  sprite's half size in GU size units = cm / (cell texels / 2) (test 16: cm drew 16-64x too big; factor G);
- colour curve (unit +0x42, C): the MHF C keys (RGBA bytes, linear, C both); no C group -> the E record's flags
  only (white). Blend: MHF E draw byte +0x15 (0x113ce4d0 -> 0x10b705e0(src 4, dst 1 / 5) -> state 0x5e via the
  factor tables 0x1185df00 / 0x1185df28, C; factor names S: 4 = source alpha, 1 = one, 5 = inverse source alpha):
  1 -> additive = BSBlendAddAlpha (0); 0 / 2 -> alpha blend = BSBlendBlendAlpha (1) (test 17: all additive washed to
  white). E flag 4 only picks the render queue (0x113cdf82, C);
- roll (unit +0x170 value / range, rad, C): MHF spawn rotation z +- range -> (z - range, 2 range).
- spawn position: the base = the group's PEL record offset (one record per MHF base, posted together); the range =
  GU's box shape (element()).
- world-oriented MHF meshes (E flags & 0x203 == 0) -> cParticleGeneratorPolygon (type 2, POLY_TEMPLATE): spawn
  rotation x / y / z, width / height = the sprite with the scale curve.
- UV animation (modes 2-6): baked frames on one looping EAN entry (uv_frames).
- motion: MHF position curves (E +0xe) and F emitters (A flag 1: physics particles, their mean path simulated by
  f_path: velocity, gravity, drag curve, growth) -> GU move kind 5 (keyed offsets over the particle age, linear, the
  end values outside; notes/gu-efl-move.md, C on both sides); F's velocity spread = a random path turn (S); the
  ground (bounces, child effects) left out (S).
Model units: MHF's UV scroll (modes 1-3) = GU's UV layer 0 (uv_block, C both sides).
Not converted yet (each reported by particles()): UV modes 1 / 7 on sprites, mesh flipbooks, rotation curves, sets' own packs,
colour flags 0x40."""
import io, math, os, struct, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import mhffx, fmod

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'dump', 'mhf', 'effect')
TEMPLATE = ('enemy/em001_00.arc', 'effect\\em\\em001\\em001_00_500', 0)
POLY_TEMPLATE = ('player/quest/w04.arc', 'effect\\cm\\cm121_041', 2)   # one-shot static Polygon (type 2)
POLY_SIZE = 0x1f0           # Polygon unit head + tail (0xa9ff8c, C): rotation x / y / z (value, range) +0x170..,
                            # angular speeds +0x188.., curves +0x1a8 / rot +0x1ac / width +0x1b0 / height +0x1b4,
                            # width +0x1c0 / +0x1c4, height +0x1c8 / +0x1cc, rates +0x1d0 / +0x1d8
T_EFL, T_TEX, T_EAN = 0x6D5AE854, 0x241F5DEB, 0x4E397417
EFL_DIR = 'effect\\pl\\w05'               # GU's EFL names carry no 'efl' folder (w00.arc: effect\\pl\\w00\\w00_000)
ATLAS = 'effect\\base\\ms_mhf_000'          # EAN path; the texture = ATLAS + TEX_SUFFIX (GU's effect textures)
TEX_SUFFIX = '_HQ_NOMIP'
# BC3, not RGBA8 (test 19: the 1024 x 2048 RGBA8 atlas = 8 MB, w05.arc 27 MB unpacked against GU's largest weapon
# arc w13 at 18.7 MB / largest file 1.2 MB: no effect drew at all, old ones included; S, the class heap not traced)
TEX_FMT = 'bc3'
CELL_MIN, CELL_MAX, ATLAS_W = 32, 128, 1024   # one 1024 x 1024 RGBA8 atlas (4 MB) for every effect
CELL_MAX_ANIM, SCROLL_FRAMES = 64, 8     # animated sprites: smaller cells; a UV scroll cycle in this many frames
ADD_BLEND, ALPHA_BLEND = 0, 1
# GU's simplest one-shot Model unit (type 5, emit 17, move 0, no curves / UV layers / animation block, 0x140 B; w04
# cm123_041 entry 0, size 1): the 3-D world-oriented MHF meshes (Builder.model_unit). Model unit fields (init
# 0xa9958c, C): +0x28 size (x the scale), +0x42 colour curve, +0x48 colours, +0x50 model path, +0x90 scale x / y / z
# (value, range) and +0xa8 rates (0xa6b59c; with the curve +0x132 the scale = the curve's three (value, range)
# keys, flag 0x800000), +0xd0 rotation (value, range) x / y / z and +0xe8 angular speeds (0xa6adac, curve +0x130),
# +0x134 a value block (0xa6b824, only when non-zero), +0x136 / +0x138 UV layers (count = +0x13b & 0xf, 0x30 B each:
# scroll values / speeds, 0xa99f40) and an animation block (+0x138 lo16, 0xa99a38); 0 = none.
MODEL_TEMPLATE = ('player/quest/w04.arc', 'effect\\cm\\cm123_041', 0)
MODEL_SIZE = 0x140
# Model unit +0x100 bits 12-21 = the mesh 'frame' a particle shows, + rand % (bits 22-31 + 1) (or the frame curve
# +0x44), 0xa99a38 -> particle +0x108; particle +0x100 = the index of the first mesh whose group (MOD mesh d0 & 0xfff)
# equals it (0xb49090, 0 when none). Effect draw (0xa956d8): that mesh. Scene-model mode (unit +0x1a bit 0, as this
# template: 0xa949f8 sets draw mode 0x37, 0xa94c10 makes one GU model unit per particle) shows mesh bit j (j < mesh
# count) only when j == the frame (C; S that the bits are the meshes' display mask). cm123_041 entry 0 picks frame 1
# of cm100_910 (5 meshes, groups 1 / 0 / 2 / 3 / 4); ours have one mesh in group 0 -> frame 0 (frame 1 hid every
# Model unit, tests 18-20: test 21 static follow-up), drawn in effect mode (model_effect_mode)
MODEL_FRAME = 0x100
# TEST-22 DIAGNOSTIC SPLIT (one-build A/B on the Model draw mode; phase3.md "Test 22"). Test 20 (scene mode, frame 1)
# showed the attraction / repulsion / Guard Counter effects' billboards; test 21 (effect mode, frame 0) showed none of
# them, while the Model-only plain-attack smoke (fae 0xb / 0xc / 0xd) and the gun did show. These effects keep the
# template's SCENE mode (model_effect_mode not applied: 0xa94b48's material test skipped, gen +0xed bit 2; draw mode
# 0x37, one GU model unit per particle, mesh j shown when j == the frame: frame 0 = our one mesh, S) with frame 0;
# every other MHF Model unit (RB moves, per-motion keys, finisher, Magnetise, shot, marker, the gun) stays in EFFECT
# mode. fxwatch prints "scene N" per effect. Drop the table (all effect mode, or all scene) after test 22.
SCENE_TEST22 = {
    (0xfc5, 0x1): 'attraction f30 / repulsion t2 (mixed)', (0xfc5, 0x5): 'attraction f10 (Model only)',
    (0xfc5, 0x7): 'attraction marker f10 (mixed)', (0xfc5, 0x2): 'attraction beam (Model only)',
    (0xfc5, 0x4d): 'repulsion t3 / marker (mixed)', (0xfc5, 0x4e): 'repulsion carrier (Model only)',
    (0xfc5, 0x38): 'Guard Counter success f32 (mixed)',
}


def model_frame(u, group=0):
    """unit +0x100: show the mesh of `group`, no random frame range (MODEL_FRAME)"""
    w = struct.unpack_from('<I', u, MODEL_FRAME)[0]
    struct.pack_into('<I', u, MODEL_FRAME, (w & 0xfff) | (group & 0x3ff) << 12)


def model_effect_mode(u):
    """the template's scene-model unit -> GU's effect draw (as efl4u2gu's models and 10795 / 11359 GU Model units;
    notes/gu-efl-units.md "Unit block, Model"): +0x1a bit 0 clear (0xa949f8: draw mode 5, materials checked by
    0xa94b48, the unit's blend byte used); +8 = 0 and +0x10c = 0, the effect-mode majority, where the template held
    scene-mode values (+0x10c bits 20-23 = 1 -> 0xc90094 / 0xc90380 arguments, +0x10e bit 4 -> gen +0x44 bit 3: 15 /
    1 of 10731 GU effect-mode units, G meaning; +8 -> gen +0xa0 and 0xc90094, 0 in 3308 / 3327 weapon-arc units)"""
    u[0x1a] &= 0xfe
    struct.pack_into('<I', u, 8, 0)
    struct.pack_into('<I', u, 0x10c, 0)
# Model UV scroll (GU side C, notes/gu-efl-units.md "Model UV layers"): unit +0x134 lo16 = offset (from the unit) of
# a 0x40-B value block = UV layer 0: f32 (value, range) pairs u +0x00, v +0x08, du +0x10, dv +0x18 (per GU frame),
# damping +0x20 (du *= it each frame; 1 = constant speed), +0x30 / +0x34 curve offsets for u / v (0 = none), +0x38 /
# +0x3c the curves' "add to the previous value" flags. Init 0xa99f40 -> 0xa6b824 (value + r x range), update 0xa9ada0
# -> 0xa6bc0c (u += du, wrapped by 2 when beyond +-2), draw 0xa956d8 -> 0xcaf17c (slot 0 = EAN offset + layer 0,
# wrapped to (-1, 1)) -> 0xc90b50, which writes slot 0 into the material's CBMaterial fUVTransform translation (+0x2c /
# +0x3c; efx_blend's FUVTransformPrimary = FUVTransformOffset, FUVAlbedoMap = FUVPrimary). GU's own effect-mode Model
# units: 2206 / 4708 in the player arcs carry such a block (du / dv 0.005-0.1, damping 0.6-1.0).
# MHF side (C, 0x113d0690, per MHF tick, ages count 2 per tick): E +0x16 mode 1 = u and v, 2 = u, 3 = v; the offset
# += 1 / (E +0x18 (u) or +0x1c (v)) / ls, ls = the particle's life scale (A +0x5c, 1 below 0.01), wrapped to [0, 1];
# the draw adds it to the mesh UVs (S: 0x113ce040 puts it in the texture matrix's translation row). GU per frame =
# half of it; v negated (GU v = 1 - MHF v, mhfmodel.mesh_part); the start offset = -D x speed, so the scroll's phase at
# MHF's spawn frame D (the particle exists in GU from frame 0, invisible until D) is MHF's 0.
UV_BLOCK = 0x134


def uv_scroll(e, ls):
    """MHF UV scroll (modes 1-3) -> (du, dv) per GU frame in GU's UV orientation, or None"""
    m = e['uv_mode']
    if m not in (1, 2, 3): return None
    sp = lambda n: (1.0 / n / ls / 2.0) if n else 0.0
    du = sp(e['uv_u']) if m in (1, 2) else 0.0
    dv = -sp(e['uv_v']) if m in (1, 3) else 0.0
    return (du, dv) if (du or dv) else None


def uv_block(e, ls, D):
    """the unit's UV value block (layer 0) for an MHF UV scroll, or None (UV_BLOCK)"""
    s = uv_scroll(e, ls)
    if not s: return None
    du, dv = s
    u0, v0 = math.fmod(-D * du, 1.0), math.fmod(-D * dv, 1.0)
    return struct.pack('<9f', u0, 0.0, v0, 0.0, du, 0.0, dv, 0.0, 1.0) + bytes(0x40 - 36)


FLAT = 0.05                  # a mesh is flat when its z extent <= 5 % of its x / y extent


def nonflat(src, mi, _c={}):
    """mhffx's sprites need a mesh flat in its x / y plane (z = 0); 404 / 942 test-18 particles were not (XZ / YZ
    planes, rings, arcs, domes)"""
    k = (id(src), mi)
    if k not in _c:
        P = np.array(src.meshes[mi]['pos'], float)
        e = P.max(0) - P.min(0) if len(P) else np.zeros(3)
        _c[k] = bool(e[2] > FLAT * max(e[0], e[1], 1e-6))
    return _c[k]


# ------------------------------------------------------------------------------------------------ MHF side

class Source:
    def __init__(self, src=SRC):
        self.sets = mhffx.container(open(os.path.join(src, 'sets.bin'), 'rb').read())
        fm = open(os.path.join(src, 'model0.fmod'), 'rb').read()
        self.meshes = fmod.parse(fm)
        self.colours = _vertex_colours(fm)
        self.mat_tex, self.tex_img = _materials(fm)
        eb = open(os.path.join(src, 'effect.bin.dec'), 'rb').read()
        o, n = struct.unpack_from('<II', eb, 4 + 8 * 1)      # entry 1 = pack 0's PNG list (0x1089e0e0 table, C)
        e = eb[o:o + n]
        from PIL import Image
        self.images = []
        for j in range(struct.unpack_from('<I', e, 0)[0]):
            a, s = struct.unpack_from('<II', e, 4 + 8 * j)
            self.images.append(np.asarray(Image.open(io.BytesIO(e[a:a + s])).convert('RGBA')))

    def set(self, sid):
        return mhffx.Set(self.sets[sid])


def _dirs(b):
    t, n, size = struct.unpack_from('<III', b, 0)
    o, out = 12, {}
    for _ in range(n):
        dt, dn, ds = struct.unpack_from('<III', b, o)
        out[dt] = (o, dn, ds)
        o += ds
    return out


def _materials(b):
    """material -> texture (dir 9: last u32), texture -> image index into the PNG list (dir 0xa: u32 +0)"""
    d = _dirs(b)
    def recs(dt):
        o, dn, ds = d[dt]; c = o + 12; out = []
        for _ in range(dn):
            t, n, sz = struct.unpack_from('<III', b, c); out.append(b[c + 12:c + sz]); c += sz
        return out
    mats = [struct.unpack_from('<I', m, len(m) - 4)[0] if len(m) == 260 else None for m in recs(9)]
    return mats, [struct.unpack_from('<I', t, 0)[0] for t in recs(0xa)]


def _vertex_colours(b):
    """per mesh: (n, 4) float RGBA 0..255 (block 0xB0000, 4 f32 per vertex)"""
    out = []
    o, dn, ds = _dirs(b)[2]
    c = o + 12
    for _ in range(dn):
        mt, mn, ms = struct.unpack_from('<III', b, c); p = c + 12; col = None
        for _ in range(mn):
            bt, bn, bs = struct.unpack_from('<III', b, p)
            if bt == 0xB0000:
                col = np.frombuffer(b[p + 12:p + 12 + 16 * bn], '<f4').reshape(bn, 4)
            p += bs
        out.append(col)
        c += ms
    return out


def bake(src, mi, du=0.0, dv=0.0, cap=CELL_MAX, view=None):
    """mesh mi (its UVs + (du, dv): MHF's UV animation offset) -> (RGBA cell (S, S, 4) uint8, half size R in cm);
    the cell centre = the mesh origin, +y up. view = (rx, ry, sy, sz): a camera-facing particle's spawn rotation x /
    y and its scale y / z relative to x, applied before the front view (MHF 0x113ce4d0: scale x rotation, then the
    camera matrix, C; the z roll stays the unit's roll, the x scale its size; test 18: XZ / YZ / 3-D meshes seen
    front-on without them baked to empty or sliver cells)"""
    m = src.meshes[mi]
    P = np.array(m['pos'], float)
    if view:
        rx, ry, sy, sz = view
        P = P * (1.0, sy, sz)
        P = np.array([_rot(v, (rx, ry, 0.0)) for v in P]) if len(P) else P
    UV = np.array([(u + du, 1.0 - v + dv) for u, v in m['uv']], float)   # fmod.py flips v; images top-down
    tris = fmod.triangles(m)
    img = src.images[src.tex_img[src.mat_tex[m['material_list'][0]]]].astype(np.float32)
    H, W = img.shape[:2]
    col = src.colours[mi] if src.colours[mi] is not None else np.full((len(P), 4), 255.0)
    R = float(np.abs(P[:, :2]).max()) or 1.0
    # texel density of the source: texels per cm along the mesh's edges
    dens = []
    for a, b, c, _ in tris[:64]:
        g = np.linalg.norm(P[b, :2] - P[a, :2])
        t = np.linalg.norm((UV[b] - UV[a]) * (W, H))
        if g > 1e-3: dens.append(t / g)
    S = int(2 ** round(math.log2(max(CELL_MIN, min(cap, 2 * R * (np.median(dens) if dens else 1.0))))))
    out = np.zeros((S, S, 4), np.float32)
    ys, xs = np.mgrid[0:S, 0:S]
    px = (xs + 0.5) / S * 2 * R - R
    py = R - (ys + 0.5) / S * 2 * R
    for a, b, c, _ in tris:
        A, B, C = P[a, :2], P[b, :2], P[c, :2]
        den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
        if abs(den) < 1e-9: continue
        l1 = ((B[1] - C[1]) * (px - C[0]) + (C[0] - B[0]) * (py - C[1])) / den
        l2 = ((C[1] - A[1]) * (px - C[0]) + (A[0] - C[0]) * (py - C[1])) / den
        l3 = 1 - l1 - l2
        ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not ins.any(): continue
        u = (l1 * UV[a, 0] + l2 * UV[b, 0] + l3 * UV[c, 0])[ins]
        v = (l1 * UV[a, 1] + l2 * UV[b, 1] + l3 * UV[c, 1])[ins]
        k = (l1[ins, None] * col[a] + l2[ins, None] * col[b] + l3[ins, None] * col[c]) / 255.0
        tx = np.clip((u % 1.0) * W - 0.5, 0, W - 1); ty = np.clip((v % 1.0) * H - 0.5, 0, H - 1)
        x0, y0 = np.floor(tx).astype(int), np.floor(ty).astype(int)
        x1, y1 = np.minimum(x0 + 1, W - 1), np.minimum(y0 + 1, H - 1)
        fx, fy = (tx - x0)[:, None], (ty - y0)[:, None]
        s = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) +
             img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)
        # overlapping triangles: MHF draws them all with the particle's blend; "over" keeps the strongest
        out[ins] = np.maximum(out[ins], s * k)
    return np.clip(out, 0, 255).astype(np.uint8), R


def uv_frames(e, ls):
    """MHF UV animation (0x113d0690, C) -> ([(du, dv)] per baked frame, GU frames per baked frame) or None.
    Ages count 1/60 s (= GU effect frames), 2 per MHF tick; the offsets add to the mesh UVs (wrapping sampler).
    4: flipbook of N = +0x18 cells on an isqrt(N) square grid over L = +0x1c x ls age units, frame k at
    (k % C, k // C) / C, L // N units each, looping; 5 / 6: a strip along u / v; 2 / 3: u / v scroll by
    1 / (+0x18 or +0x1c) / ls per tick, baked as SCROLL_FRAMES frames over one cycle (S: GU shows it as a flipbook)."""
    m = e['uv_mode']
    if m in (4, 5, 6):
        N = max(1, e['uv_u']); L = max(1, int(e['uv_v'] * ls)); C = max(1, math.isqrt(N))
        step = max(1, L // N)
        if m == 4: fr = [((k % C) / C, (k // C) / C) for k in range(N)]
        elif m == 5: fr = [(k / N, 0.0) for k in range(N)]
        else: fr = [(0.0, k / N) for k in range(N)]
        return fr, float(step)
    if m in (2, 3):
        n = e['uv_u'] if m == 2 else e['uv_v']
        if not n: return None
        rate = 1.0 / n / ls                       # UV per tick
        T = 2.0 / abs(rate)                       # age units per cycle
        K = int(max(2, min(SCROLL_FRAMES, round(T))))
        sg = 1.0 if rate > 0 else -1.0
        fr = [((sg * k / K, 0.0) if m == 2 else (0.0, sg * k / K)) for k in range(K)]
        return fr, T / K
    return None


# ------------------------------------------------------------------------------------------------ plan

def particles(st, eid, life_min=mhffx.LIFE_MIN):
    """the MHF effect -> [(A, E, converted?, reasons)]; an F emitter's records come as E-like dicts with 'F' set
    (from_f); position curves (E) and F paths become GU kind-5 move paths (move_block)"""
    out = []
    for a in st.effect(eid):
        ls = a['p5c'] if a['p5c'] >= life_min else 1.0
        if a['flags'] & 1:
            fs = st.femitters(a['part'])
            if not fs: out.append((a, None, False, ['F emitter without F records']))
            for f in fs:
                e = from_f(f)
                why = []
                if e['uv_mode'] and not uv_frames(e, ls): why.append('UV mode %d' % e['uv_mode'])
                if e['mesh_anim']: why.append('mesh flipbook')
                out.append((a, e, not why, why))
            continue
        for e in st.particles(a['part']):
            why = []
            if e['uv_mode'] and not uv_frames(e, ls): why.append('UV mode %d' % e['uv_mode'])
            if e['mesh_anim']: why.append('mesh flipbook')
            if e['pack'] == 1: why.append("set's own pack")
            if len(st.curve(e['c_rot'])) > 1: why.append('rotation curve')
            out.append((a, e, not why, why))
    return out


def from_f(f):
    """an F record as the E fields the unit builder reads (no scale / position / rotation curves: the path and the
    growth are simulated, f_path)"""
    return dict(flags=f['flags'], id=f['id'], pack=0, mesh=f['mesh'], mesh_anim=f['mesh_anim'], life=f['life'],
                c_pos=0, c_rot=0, c_scl=0, draw=f['draw'], uv_mode=f['uv_mode'], uv_u=f['uv_u'], uv_v=f['uv_v'],
                c_col=f['c_col'], F=f)


def _rot(v, r):
    """R = Rz Ry Rx (MHF's Euler order, notes/assets.md, S for effects) applied to v"""
    x, y, z = v; cx, sx = math.cos(r[0]), math.sin(r[0]); cy, sy = math.cos(r[1]), math.sin(r[1])
    cz, sz = math.cos(r[2]), math.sin(r[2])
    y, z = cx * y - sx * z, sx * y + cx * z
    x, z = cy * x + sy * z, -sy * x + cy * z
    x, y = cz * x - sz * y, sz * x + cz * y
    return (x, y, z)


def f_path(st, a, f):
    """simulate an F particle's mean path (U = 0; 0x113d2190 / 0x113d2700 order: pos += v, vy -= g, v x= the velocity
    curve at the age; scale += growth, growth x= its curve; one update per MHF tick, age += 2) in the effect's frame
    -> ([(age, pos)], [(age, scale x)]); the ground (bounces, children) is left out (S deviation)"""
    p, v = [0.0, 0.0, 0.0], list(f['vel'])
    sc, gr = a['scl'][0], f['grow'][0]
    path, scl = [(0, tuple(p))], [(0, sc)]
    life = max(2, f['life'])
    for age in range(0, life, 2):
        for k in range(3): p[k] += v[k]
        v[1] -= f['grav']
        if f['c_vel']:
            m = st.curve_at(f['c_vel'], age)
            v = [v[k] * m[k] for k in range(3)]
        sc = max(0.0, sc + gr)
        if f['c_grow']: gr *= st.curve_at(f['c_grow'], age)[0]
        path.append((age + 2, tuple(p))); scl.append((age + 2, sc))
    return path, scl


def _thin(keys, n=24):
    """at most n keys, the ends kept"""
    if len(keys) <= n: return keys
    step = (len(keys) - 1) / (n - 1)
    return [keys[int(round(i * step))] for i in range(n)]


def move_block(keys, rot=((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)), order=0):
    """[(GU age, (x, y, z))] -> GU move kind 5 block (w3 type 0x05; notes/gu-efl-move.md, C): 0x80 B (+0x04 Euler
    order << 12 | axis 4 << 8, +0x10.. path rotation (value, range) per axis, +0x50.. path scale 1, +0x70 the curve
    offset), then the curve {count | 2 << 8; keys {u32 age, x, 0, y, 0, z, 0}}: linear, the end values outside, so
    pos(age) = E (spawn + Rp curve(age)) as MHF's offset curve"""
    b = bytearray(0x80)
    struct.pack_into('<II', b, 0, 0, order << 12 | 4 << 8)
    for k in range(3): struct.pack_into('<ff', b, 0x10 + 8 * k, *rot[k])
    struct.pack_into('<8f', b, 0x50, 1, 0, 1, 0, 1, 0, 1, 0)
    struct.pack_into('<I', b, 0x70, 0x80)
    c = struct.pack('<I', len(keys) | 2 << 8) + b''.join(
        struct.pack('<I6f', t, x, 0.0, y, 0.0, z, 0.0) for t, (x, y, z) in keys)
    blk = bytes(b) + c
    return blk + b'\0' * (-len(blk) % 16)


# ------------------------------------------------------------------------------------------------ GU side

def _f(x): return struct.pack('<f', x)


def curve(keys, flags=0):
    """GU curve table: u32 count | 2 << 8 | flags << 24, keys {u32 time, w1, w2} (0xaf7958 / 0xaf938c, C)"""
    return struct.pack('<I', len(keys) | 2 << 8 | flags << 24) + b''.join(
        struct.pack('<I', t) + w1 + w2 for t, w1, w2 in keys)


def rgba(c):
    return bytes(c)


class Builder:
    def __init__(self, src, gu_read, rom=None):
        """gu_read(arc, path) -> bytes of a GU file (the EFL template); rom (RomFS) for the models' MRLs"""
        self.src = src
        self.mtpl = _template(gu_read, MODEL_TEMPLATE)
        assert self.mtpl[1][0] == 5 and self.mtpl[2][0] == 17 and len(self.mtpl[1][1]) >= MODEL_SIZE, 'model template'
        import mhfmodel
        self.models = mhfmodel.Models(src, rom)
        self.poly = _template(gu_read, POLY_TEMPLATE)
        assert self.poly[1][0] == 2 and len(self.poly[1][1]) >= POLY_SIZE, 'polygon template'
        d = gu_read(TEMPLATE[0], TEMPLATE[1])
        self.tpl_head = d[:0x30]
        n, n2 = struct.unpack_from('<HH', d, 0x10)
        ents = [struct.unpack_from('<4I', d, 0x30 + 16 * i) for i in range(n)]
        tail = struct.unpack_from('<%dI' % n2, d, 0x30 + 16 * n)
        starts = sorted({(w >> 8) + 0x30 for e in ents for w in e if w >> 8} | {t + 0x30 for t in tail})
        size = {o: (starts[i + 1] if i + 1 < len(starts) else len(d)) - o for i, o in enumerate(starts)}
        e = ents[TEMPLATE[2]]
        self.tpl = [(w & 0xff, d[(w >> 8) + 0x30:(w >> 8) + 0x30 + size[(w >> 8) + 0x30]]) for w in e]
        self.tpl_tail = [d[t + 0x30:t + 0x30 + 0x70] for t in tail]
        assert self.tpl[1][0] == 0 and len(self.tpl[1][1]) >= 0x1a0, 'template unit is not a Billboard'
        self.cells = {}          # mesh -> (index, cell rgba, R)
        self.report = []

    def cell(self, mi, frames=((0.0, 0.0),), view=None):
        """-> (EAN entry index, [frame images], R): one entry per (mesh, UV frames, view)"""
        key = (mi, tuple(frames), view)
        if key not in self.cells:
            cap = CELL_MAX if len(frames) == 1 else CELL_MAX_ANIM
            imgs = [bake(self.src, mi, du, dv, cap, view) for du, dv in frames]
            self.cells[key] = (len(self.cells), [i for i, _ in imgs], imgs[0][1])
        return self.cells[key]

    def motion(self, st, a, e, tm, sb):
        """-> (scale keys [(MHF frame, (x, y, z) factors, _)], GU move (5, block) or None): F paths, position curves"""
        F = e.get('F')
        mv = None
        if F:                                   # F: the simulated growth as the scale curve, the path as kind 5
            path, sc = f_path(st, a, F)
            sk = [(f, (v / sb if sb else 0.0,) * 3, 0) for f, v in _thin(sc)]
            vn = math.sqrt(sum(x * x for x in F['vel']))
            spread = ((0.0, 0.0),) * 3
            if vn > 1e-3:                       # MHF's velocity range as a random path turn (S)
                ax = math.atan2(abs(F['vel_r'][1]) * 1.024, vn); ay = math.atan2(abs(F['vel_r'][0]) * 1.024, vn)
                spread = ((-ax, 2 * ax), (-ay, 2 * ay), (0.0, 0.0))
            mv = (5, move_block([(tm(f), q) for f, q in _thin(path)], spread))
        else:
            sk = st.curve(e['c_scl']) or [(0, (1.0, 1.0, 1.0), 0)]
            pk = st.curve(e['c_pos'])
            if pk and any(any(abs(x) > 1e-3 for x in v) for _, v, _ in pk):
                # MHF's offset in the particle's spawn-rotated frame: the base rotation applied here, its random
                # range as the path's (order 0 = X, Y, Z, S); one GU key per MHF key (exact, C)
                r0 = a['rot']; rr = a['rot_r']
                mv = (5, move_block([(tm(f), _rot(v, r0)) for f, v, _ in pk],
                                    tuple((-rr[k], 2 * rr[k]) for k in range(3))))
        return sk, mv

    def unit(self, a, e):
        st = self.cur_set
        ls = a['p5c'] if a['p5c'] >= mhffx.LIFE_MIN else 1.0
        world = not e['flags'] & 0x203
        if world and nonflat(self.src, e['mesh']):
            return self.model_unit(st, a, e, ls)
        anim = uv_frames(e, ls) if e['uv_mode'] else None
        view = None
        if not world:                           # camera-facing: the spawn rotation x / y and relative scale baked
            sb0 = a['scl'][0] or 1.0
            v = (round(a['rot'][0], 2), round(a['rot'][1], 2), round(a['scl'][1] / sb0, 2), round(a['scl'][2] / sb0, 2))
            if v != (0.0, 0.0, 1.0, 1.0) and (v[:3] != (0.0, 0.0, 1.0) or nonflat(self.src, e['mesh'])):
                view = v
        idx, imgs, R = self.cell(e['mesh'], anim[0] if anim else ((0.0, 0.0),), view)
        img = imgs[0]
        # GU sizes count the sprite's texels (0xa7e768 builds the quad from the EAN frame's w / h; GU's own hunter
        # billboards: size 0.2-1.25 on 256-px frames; test 16: cm sizes drew 16-64x too big): size 1 = one cm per
        # texel from the pivot (G: the exact factor is not traced), so the MHF half size R cm = R / (S / 2)
        R = R / (img.shape[0] / 2.0)
        D = a['frame']
        life = int(round(e['life'] * ls))
        tm = lambda f: D + int(round(f * ls))
        u = bytearray(self.tpl[1][1][:0x1a0])
        u[3] = ADD_BLEND if e['draw'] == 1 else ALPHA_BLEND      # MHF draw byte (docstring, C)
        struct.pack_into('<f', u, 0x1c, 1.0)
        sb, sr = a['scl'][0], a['scl_r'][0]
        struct.pack_into('<4f', u, 0x28, (sb - sr) * R, 2 * sr * R, 0.0, 0.0)
        tail = b''
        # scale curve
        sk, mv = self.motion(st, a, e, tm, sb)
        F = e.get('F')
        keys = [(tm(f), _f((sb - sr) * v[0] * R), _f(2 * sr * v[0] * R)) for f, v, _ in sk]
        if D: keys = [(0, keys[0][1], keys[0][2])] + keys
        off_s = 0x1a0 + len(tail); tail += curve(keys)
        # colour curve (alpha 0 before D)
        ck = st.colours(e['c_col'])
        cols = [(tm(f), bytes.fromhex(c)) for f, c, _ in ck] or [(tm(0), b'\xff\xff\xff\xff')]
        keys = [(t, c, c) for t, c in cols]
        if D:
            z = cols[0][1][:3] + b'\0'
            keys = [(0, z, z), (max(D - 1, 0), z, z)] + keys
        off_c = 0x1a0 + len(tail); tail += curve(keys)
        struct.pack_into('<HHHHHHHH', u, 0x38, 0, off_s, 0, 0, 0, off_c, 0, 0)    # +0x40 byte 0 = 0: one colour
        struct.pack_into('<4s4s', u, 0x48, cols[0][1], cols[0][1])
        # UV animation (0xa69d00 / 0xa6a004, C): flags 1 = animate, 2 = loop (GU's own: 0x3 with speed 0.1, S)
        struct.pack_into('<IIff', u, 0x50, idx << 16 | (3 if anim else 0), 0, 1.0 / anim[1] if anim else 0.0, 0.0)
        S = img.shape[0]
        struct.pack_into('<II', u, 0x60, S // 2, S // 2)
        u[0x70:0x130] = (ATLAS + TEX_SUFFIX).encode().ljust(0xc0, b'\0')
        u[0x130:0x170] = ATLAS.encode().ljust(0x40, b'\0')
        rz, rr = a['rot'][2], a['rot_r'][2]
        w, wr = (F['ang'][2] / 2, F['ang_r'][2] / 2) if F else (0.0, 0.0)   # rad per tick -> per frame
        struct.pack_into('<8f', u, 0x170, rz - rr, 2 * rr, w - wr, 2 * wr, 1.0, 0.0, 0.0, 0.0)
        struct.pack_into('<fII', u, 0x190, 1.0, 0, 0)
        emit = bytearray(self.tpl[2][1])
        struct.pack_into('<III', emit, 0, 0, D + life, 0)
        if not e['flags'] & 0x203:
            # world-oriented MHF mesh (no view matrix in 0x113ce4d0) -> a GU Polygon: the same head (colour,
            # texture, EAN, curves), the MHF spawn rotation on x / y / z (rad, value - range, 2 range; order G),
            # width = height = the sprite size with the scale curve (half extent assumed, as the Billboard: G)
            q = bytearray(self.poly[1][1][:POLY_SIZE])         # Polygon's own head flags; ours copied in:
            for a0, a1 in ((3, 4), (0x1c, 0x20), (0x28, 0x68), (0x70, 0x170)):   # blend, size / curves / colours /
                q[a0:a1] = u[a0:a1]                            # UV / pivot, texture + EAN paths
            rot = [(a['rot'][k] - a['rot_r'][k], 2 * a['rot_r'][k]) for k in range(3)]
            struct.pack_into('<6f6f', q, 0x170, *[x for r in rot for x in r], *([0.0] * 6))
            shift = POLY_SIZE - 0x1a0                          # our curves move behind the Polygon block
            for o in (0x3a, 0x42):
                v = struct.unpack_from('<H', q, o)[0]
                if v: struct.pack_into('<H', q, o, v + shift)
            # width / height: the sprite's half size in texels, the size curve (+0x3a) scaling it as the
            # Billboard's (G: GU's Polygon template cm121_041 = 100 x size 4 on a 64-px pivot); no width curves
            struct.pack_into('<IIII', q, 0x1a8, 0, 0, 0, 0)
            h = img.shape[0] / 2.0
            struct.pack_into('<8f', q, 0x1c0, h, 0.0, h, 0.0, 0.0, 0.0, 0.0, 0.0)
            return (2, bytes(q) + tail), bytes(emit), mv
        return (0, bytes(u) + tail), bytes(emit), mv

    def model_unit(self, st, a, e, ls):
        """a world-oriented 3-D MHF mesh -> a GU Model unit on the mesh as a model (mhfmodel): MHF's local transform
        scale x rotation (0x113ce4d0, C) = the unit's scale x / y / z (base - range, 2 range) x the scale curve
        and rotation x / y / z (value - range, 2 range, rad; GU order 0 = MHF's Rz Ry Rx, C); colour curve, life,
        motion and blend (unit byte 3 -> particle +0x18 bits 5-12 -> 0xb007fc in the draw 0xc90b50, C) as the
        Billboard's; MHF's UV scroll (modes 1-3, 132 / 266 units) as GU's UV layer 0 (uv_block, C both sides)"""
        D = a['frame']
        life = int(round(e['life'] * ls))
        tm = lambda f: D + int(round(f * ls))
        u = bytearray(self.mtpl[1][1][:MODEL_SIZE])
        u[3] = ADD_BLEND if e['draw'] == 1 else ALPHA_BLEND
        struct.pack_into('<f', u, 0x1c, 1.0)
        struct.pack_into('<4f', u, 0x28, 1.0, 0.0, 0.0, 0.0)
        sb = a['scl'][0]
        sk, mv = self.motion(st, a, e, tm, sb)
        F = e.get('F')
        base, rng = a['scl'], a['scl_r']
        keys = [(tm(f), tuple(x for k in range(3) for x in ((base[k] - rng[k]) * v[k], 2 * rng[k] * v[k])))
                for f, v, _ in sk]
        if D: keys = [(0, keys[0][1])] + keys
        tail = b''
        off_s = MODEL_SIZE + len(tail)
        tail += struct.pack('<I', len(keys) | 2 << 8) + b''.join(struct.pack('<I6f', t, *v) for t, v in keys)
        ck = st.colours(e['c_col'])
        cols = [(tm(f), bytes.fromhex(c)) for f, c, _ in ck] or [(tm(0), b'\xff\xff\xff\xff')]
        ckeys = [(t, c, c) for t, c in cols]
        if D:
            z = cols[0][1][:3] + b'\0'
            ckeys = [(0, z, z), (max(D - 1, 0), z, z)] + ckeys
        off_c = MODEL_SIZE + len(tail); tail += curve(ckeys)
        struct.pack_into('<HHHHHHHH', u, 0x38, 0, 0, 0, 0, 0, off_c, 0, 0)
        struct.pack_into('<4s4s', u, 0x48, cols[0][1], cols[0][1])
        u[0x50:0x90] = self.models.mesh(e['mesh']).encode().ljust(0x40, b'\0')
        model_frame(u)
        if getattr(self, 'cur_eff', None) in SCENE_TEST22:
            self.n_scene = getattr(self, 'n_scene', 0) + 1
        else:
            model_effect_mode(u)
        struct.pack_into('<6f', u, 0x90, *[x for k in range(3) for x in (base[k] - rng[k], 2 * rng[k])])
        struct.pack_into('<6f', u, 0xa8, *([0.0] * 6))
        r, rr = a['rot'], a['rot_r']
        struct.pack_into('<6f', u, 0xd0, *[x for k in range(3) for x in (r[k] - rr[k], 2 * rr[k])])
        w, wr = (F['ang'][2] / 2, F['ang_r'][2] / 2) if F else (0.0, 0.0)
        struct.pack_into('<6f', u, 0xe8, 0.0, 0.0, 0.0, 0.0, w - wr, 2 * wr)
        blk = uv_block(e, ls, D)
        off_uv = 0
        if blk:
            off_uv = MODEL_SIZE + len(tail); tail += blk
            self.n_uv = getattr(self, 'n_uv', 0) + 1
        struct.pack_into('<HHHHI', u, 0x130, 0, off_s, off_uv, 0, 0)
        emit = bytearray(self.tpl[2][1])
        struct.pack_into('<III', emit, 0, 0, D + life, 0)
        self.n_models = getattr(self, 'n_models', 0) + 1
        return (5, bytes(u) + tail), bytes(emit), mv

    def element(self, a):
        """the template element; an MHF position range -> GU's box spawn shape (element +0x78 byte 0 = 1 ->
        0xa5e450 case 1: offset = (2r - 1) x (+0x60, +0x68, +0x70) per axis, C), MHF U spans +-1.024 x range"""
        el = bytearray(self.tpl[0][1])
        r = a['pos_r']
        if any(r):
            for k, o in enumerate((0x60, 0x68, 0x70)):
                struct.pack_into('<ff', el, o, abs(r[k]) * 1.024, 0.0)
            el[0x78] = 1
        return (self.tpl[0][0], bytes(el))

    def efl(self, sid, eid):
        """one MHF effect -> ([(EFL path, EFL bytes)], groups [(EFL path, element mask, base position)], entries,
        [(E id, reasons)] not converted). A group = the entries of one MHF base position (turned by the effect yaw
        in MHF, 0x113d37e0, C), posted as one PEL record with that offset; at most 32 entries per EFL (the record's
        element mask)"""
        st = self.cur_set = self.src.set(sid)
        self.cur_eff = (sid, eid)
        by_pos, skipped = {}, []
        for a, e, ok, why in particles(st, eid):
            if not ok:
                skipped.append((e['id'] if e else a['part'], why)); continue
            key = tuple(round(x, 2) for x in a['pos'])
            for _ in range(max(1, a['count'])):
                u, em, mv = self.unit(a, e)
                by_pos.setdefault(key, []).append([self.element(a), u, (self.tpl[2][0], em), mv or self.tpl[3]])
        files, groups, cur, n = [], [], [], 0
        def flush():
            if cur:
                path = efl_name(sid, eid) + ('_%d' % len(files) if files else '')
                files.append((path, write_efl(self.tpl_head, [x for _, x in cur], self.tpl_tail)))
                masks = {}
                for i, (pos, _) in enumerate(cur): masks[pos] = masks.get(pos, 0) | 1 << i
                groups.extend((path, m, pos) for pos, m in masks.items())
        for pos, es in by_pos.items():
            for x in es:
                if len(cur) == 32: flush(); cur.clear()
                cur.append((pos, x)); n += 1
        flush()
        return files, groups, n, skipped

    def atlas(self):
        """-> (RGBA atlas image, EAN bytes): shelf-packed frames (largest first), one EAN entry per cell (index =
        cell index) with its frames (EAN layout: notes/gu-efl-units.md, efl4u2gu.py)"""
        cells = sorted(self.cells.values(), key=lambda c: c[0])
        order = sorted(((img.shape[0], c, f) for c, (idx, imgs, R) in enumerate(cells) for f, img in enumerate(imgs)),
                       key=lambda t: -t[0])
        x = y = row = 0; place = {}
        for S, c, f in order:
            if x + S > ATLAS_W: x, y, row = 0, y + row, 0
            place[(c, f)] = (x, y, S); x += S; row = max(row, S)
        H = max(32, 1 << (y + row - 1).bit_length())
        A = np.zeros((H, ATLAS_W, 4), np.uint8)
        for (c, f), (x, y, S) in place.items():
            A[y:y + S, x:x + S] = cells[c][1][f]
        n = len(cells)
        ents, frames = b'', b''
        off = 32 * n
        for c, (idx, imgs, R) in enumerate(cells):
            x0, y0, S = place[(c, 0)]
            ents += struct.pack('<IIIIIIII', off + len(frames), len(imgs), S // 2, S // 2, x0, y0, 1 | 1 << 16,
                                S | S << 16)
            for f in range(len(imgs)):
                x, y, S = place[(c, f)]
                frames += struct.pack('<II4f', x | y << 16, S | S << 16, x / ATLAS_W, y / H, (x + S) / ATLAS_W,
                                      (y + S) / H)
        body = ents + frames
        ean = b'EAN\0' + struct.pack('<III', 0x20120224, len(body), n | 1 << 24) + body
        return A, ean


def _template(gu_read, t):
    """(arc, EFL path, entry) -> the entry's 4 (type, block bytes)"""
    d = gu_read(t[0], t[1])
    n, n2 = struct.unpack_from('<HH', d, 0x10)
    ents = [struct.unpack_from('<4I', d, 0x30 + 16 * i) for i in range(n)]
    tail = struct.unpack_from('<%dI' % n2, d, 0x30 + 16 * n)
    starts = sorted({(w >> 8) + 0x30 for e in ents for w in e if w >> 8} | {x + 0x30 for x in tail})
    size = {o: (starts[i + 1] if i + 1 < len(starts) else len(d)) - o for i, o in enumerate(starts)}
    return [(w & 0xff, d[(w >> 8) + 0x30:(w >> 8) + 0x30 + size[(w >> 8) + 0x30]]) for w in ents[t[2]]]


def write_efl(head, ents, tail_recs):
    """EFL container (efl4u2gu.efl_parse layout): header 0x30, n x 16-B entries of 4 block words
    ((offset - 0x30) << 8 | type), n2 u32 tail offsets, then the blocks (16-aligned, as every GU EFL)"""
    n, n2 = len(ents), len(tail_recs)
    p = 0x30 + 16 * n + 4 * n2
    p = (p + 15) & ~15
    blob = bytearray(); words = []; tails = []
    def put(b):
        nonlocal blob
        o = p + len(blob)
        blob += b + b'\0' * (-len(b) % 16)
        return o
    shared = {}
    for e in ents:
        w = []
        for t, b in e:
            key = (t, b)
            if key not in shared: shared[key] = put(b)
            w.append((shared[key] - 0x30) << 8 | t)
        words.append(w)
    for r in tail_recs: tails.append(put(r) - 0x30)
    total = p + len(blob)
    h = bytearray(head)
    struct.pack_into('<I', h, 8, total - 0x30)
    struct.pack_into('<HH', h, 0x10, n, n2)
    out = bytes(h) + b''.join(struct.pack('<4I', *w) for w in words) + struct.pack('<%dI' % n2, *tails)
    out += b'\0' * (p - len(out))
    return out + bytes(blob)


def efl_name(sid, eid):
    return '%s\\ms_%03x_%03x' % (EFL_DIR, sid & 0xfff, eid)

# The effects the MHF Magnet Spike code posts (0x113d61f0 / 0x113d66b0 call sites, notes/assets.md): (set, effect)
MS_EFFECTS = [(0xfc5, e) for e in (0x1, 0x3, 0x4, 0x14, 0x15, 0x16, 0x1a, 0x22, 0x30, 0x37, 0x38, 0x39, 0x3a, 0x3d,
                                   0x3e, 0x40, 0x45, 0x46, 0x47, 0x4d, 0x4f, 0x53, 0x54, 0x5d, 0x5e)] + \
             [(0xfc6, e) for e in (0xe, 0xf, 0x11, 0x2d, 0x2e, 0x2f, 0x30, 0x32, 0x33, 0x34)]


def build_all(gu_read, effects=MS_EFFECTS, src=SRC, rom=None):
    """-> (arc entries [(path, type, bytes)], {(set, effect): [(EFL path, element mask, position)]}, report);
    rom (RomFS) for the 3-D meshes' MRLs (mhfmodel)"""
    import tex
    b = Builder(Source(src), gu_read, rom)
    ents, made, rep = [], {}, []
    for sid, eid in effects:
        files, groups, n, skipped = b.efl(sid, eid)
        ents += [(path, T_EFL, d) for path, d in files]
        made[(sid, eid)] = groups
        rep.append('mhf effect %#x %#x: %d GU entries%s' % (sid, eid, n, ''.join(
            '; not converted: E %d (%s)' % (k, ', '.join(w)) for k, w in skipped)))
    if b.cells:
        A, ean = b.atlas()
        # the atlas first: an arc's resources resolve the paths they name while they load (GU's arcs hold every
        # texture / EAN before the EFLs naming it, every EFL before its PEL: msbuild puts these before the PEL)
        ents = [(ATLAS + TEX_SUFFIX, T_TEX, tex.encode_gu(A, TEX_FMT, mips=1)), (ATLAS, T_EAN, ean)] + ents
        rep.append('mhf effect atlas %dx%d, %d sprites' % (A.shape[1], A.shape[0], len(b.cells)))
    if b.models.mods:                          # the 3-D meshes' textures / MRLs / MODs before the EFLs naming them
        k = next(i for i, (p, t, d) in enumerate(ents) if t == T_EFL)
        ents[k:k] = b.models.entries()
        rep.append('mhf effect models: %d meshes, %d textures, %d Model units (%d with MHF\'s UV scroll as GU UV layer '
                   '0, unit +0x134)' % (len(b.models.mods), len(b.models.tex), getattr(b, 'n_models', 0),
                                        getattr(b, 'n_uv', 0)))
        rep.append('mhf effect models, test-22 draw-mode split: %d Model units in SCENE mode (%s), the rest in effect '
                   'mode' % (getattr(b, 'n_scene', 0), ', '.join('%#x %#x = %s' % (s, e, w)
                                                                 for (s, e), w in sorted(SCENE_TEST22.items()))))
    return ents, made, rep
