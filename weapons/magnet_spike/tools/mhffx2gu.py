"""mhffx2gu.py : MHF effects (mhffx.py) -> GU effect files (EFL + sprite atlas TEX + EAN), for msbuild.py.
Formats: notes/assets.md "## Effects" (MHF) and notes/gu-efl-units.md (GU). C / S / G marks as there.

What a converted particle is (one GU entry per MHF particle; the MHF count of a burst = that many entries):
- the MHF mesh baked into a sprite: every MHF particle mesh is flat (z = 0); its triangles are rasterised with their
  atlas texture x vertex colour into a square cell centred on the mesh origin (the particle position), so a GU
  Billboard of that cell covers what MHF's billboarded mesh covers (shaped meshes too: 13-84-vertex glows, rays);
- unit = cParticleGeneratorBillboard (type 0) from GU's em001_00_500 entry 0 (one particle, once: emit type 0x11,
  0xa5a900, C; no motion: move kind 0, S), its element / emit / move blocks as they are, the emit block's hold B =
  the MHF life (fade-in A / fade-out C 0: 0xaed0d0, C);
- the MHF burst frame D: the particle spawns with the effect and stays invisible (alpha 0) until D, every key shifted
  by D (GU's start wait comes from the poster, not the unit: 0xa5abc4 case 0, C);
- scale curve (unit +0x3a, 0xa6a2d0, C): key = (base - range) x curve x R, random range 2 range x curve x R (MHF
  scale = (base + U range) x curve, U in [-1, 1); GU = value + r range, r in [0, 1) per particle, C); R = the
  sprite's half size (cm): GU's billboard size unit is G (half extent assumed; test: compare with MHF footage);
- colour curve (unit +0x42, C): the MHF C keys (RGBA bytes, linear, C both); no C group -> the E record's flags
  only (white). Blend: MHF E flag 4 (render queue, S additive) -> BSBlendAddAlpha (0), else BSBlendBlendAlpha (1);
- roll (unit +0x170 value / range, rad, C): MHF spawn rotation z +- range -> (z - range, 2 range).
- spawn position: the base = the group's PEL record offset (one record per MHF base, posted together); the range =
  GU's box shape (element()).
Not converted yet (each reported by particles()): position curves (motion), non-billboard meshes (E flags & 0x203
== 0: world-oriented, need a Polygon / Model unit), UV modes 1-7, mesh flipbooks, rotation curves, F emitters, sets'
own packs (E +6 == 1), colour flags 0x40."""
import io, math, os, struct, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import mhffx, fmod

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'dump', 'mhf', 'effect')
TEMPLATE = ('enemy/em001_00.arc', 'effect\\em\\em001\\em001_00_500', 0)
T_EFL, T_TEX, T_EAN = 0x6D5AE854, 0x241F5DEB, 0x4E397417
EFL_DIR = 'effect\\pl\\w05'               # GU's EFL names carry no 'efl' folder (w00.arc: effect\\pl\\w00\\w00_000)
ATLAS = 'effect\\base\\ms_mhf_000'          # EAN path; the texture = ATLAS + TEX_SUFFIX (GU's effect textures)
TEX_SUFFIX = '_HQ_NOMIP'
CELL_MIN, CELL_MAX, ATLAS_W = 32, 256, 1024
ADD_BLEND, ALPHA_BLEND = 0, 1


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


def bake(src, mi):
    """mesh mi -> (RGBA cell (S, S, 4) uint8, half size R in cm); the cell centre = the mesh origin, +y up"""
    m = src.meshes[mi]
    P = np.array(m['pos'], float)
    UV = np.array([(u, 1.0 - v) for u, v in m['uv']], float)      # fmod.py flips v; images are top-down (D3D)
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
    S = int(2 ** round(math.log2(max(CELL_MIN, min(CELL_MAX, 2 * R * (np.median(dens) if dens else 1.0))))))
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


# ------------------------------------------------------------------------------------------------ plan

def particles(st, eid, life_min=mhffx.LIFE_MIN):
    """the MHF effect -> [(A, E, converted?, reasons)]"""
    out = []
    for a in st.effect(eid):
        if a['flags'] & 1:
            out.append((a, None, False, ['F emitter']))
            continue
        for e in st.particles(a['part']):
            why = []
            k = st.curve(e['c_pos'])
            if len(k) > 1 and any(v != k[0][1] for _, v, _ in k): why.append('position curve (%d keys)' % len(k))
            if not e['flags'] & 0x203: why.append('world-oriented mesh')
            if e['uv_mode']: why.append('UV mode %d' % e['uv_mode'])
            if e['mesh_anim']: why.append('mesh flipbook')
            if e['pack'] == 1: why.append("set's own pack")
            if len(st.curve(e['c_rot'])) > 1: why.append('rotation curve')
            out.append((a, e, not why, why))
    return out


# ------------------------------------------------------------------------------------------------ GU side

def _f(x): return struct.pack('<f', x)


def curve(keys, flags=0):
    """GU curve table: u32 count | 2 << 8 | flags << 24, keys {u32 time, w1, w2} (0xaf7958 / 0xaf938c, C)"""
    return struct.pack('<I', len(keys) | 2 << 8 | flags << 24) + b''.join(
        struct.pack('<I', t) + w1 + w2 for t, w1, w2 in keys)


def rgba(c):
    return bytes(c)


class Builder:
    def __init__(self, src, gu_read):
        """gu_read(arc, path) -> bytes of a GU file (the EFL template)"""
        self.src = src
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

    def cell(self, mi):
        if mi not in self.cells:
            img, R = bake(self.src, mi)
            self.cells[mi] = (len(self.cells), img, R)
        return self.cells[mi]

    def unit(self, a, e):
        idx, img, R = self.cell(e['mesh'])
        st = self.cur_set
        ls = a['p5c'] if a['p5c'] >= mhffx.LIFE_MIN else 1.0
        D = a['frame']
        life = int(round(e['life'] * ls))
        tm = lambda f: D + int(round(f * ls))
        u = bytearray(self.tpl[1][1][:0x1a0])
        u[3] = ADD_BLEND if e['flags'] & 4 else ALPHA_BLEND
        struct.pack_into('<f', u, 0x1c, 1.0)
        sb, sr = a['scl'][0], a['scl_r'][0]
        struct.pack_into('<4f', u, 0x28, (sb - sr) * R, 2 * sr * R, 0.0, 0.0)
        tail = b''
        # scale curve
        sk = st.curve(e['c_scl']) or [(0, (1.0, 1.0, 1.0), 0)]
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
        struct.pack_into('<IIff', u, 0x50, idx << 16, 0, 0.0, 0.0)
        S = img.shape[0]
        struct.pack_into('<II', u, 0x60, S // 2, S // 2)
        u[0x70:0x130] = (ATLAS + TEX_SUFFIX).encode().ljust(0xc0, b'\0')
        u[0x130:0x170] = ATLAS.encode().ljust(0x40, b'\0')
        rz, rr = a['rot'][2], a['rot_r'][2]
        struct.pack_into('<8f', u, 0x170, rz - rr, 2 * rr, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        struct.pack_into('<fII', u, 0x190, 1.0, 0, 0)
        emit = bytearray(self.tpl[2][1])
        struct.pack_into('<III', emit, 0, 0, D + life, 0)
        return bytes(u) + tail, bytes(emit)

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
        by_pos, skipped = {}, []
        for a, e, ok, why in particles(st, eid):
            if not ok:
                skipped.append((e['id'] if e else a['part'], why)); continue
            key = tuple(round(x, 2) for x in a['pos'])
            for _ in range(max(1, a['count'])):
                u, em = self.unit(a, e)
                by_pos.setdefault(key, []).append([self.element(a), (0, u), (self.tpl[2][0], em), self.tpl[3]])
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
        """-> (RGBA atlas image, EAN bytes): shelf-packed cells, one EAN entry per cell (index = cell index)"""
        cells = sorted(self.cells.values())
        x = y = row = 0; place = []
        for idx, img, R in cells:
            S = img.shape[0]
            if x + S > ATLAS_W: x, y, row = 0, y + row, 0
            place.append((x, y, S)); x += S; row = max(row, S)
        H = max(32, 1 << (y + row - 1).bit_length())
        A = np.zeros((H, ATLAS_W, 4), np.uint8)
        for (x, y, S), (idx, img, R) in zip(place, cells):
            A[y:y + S, x:x + S] = img
        n = len(place)
        ents, frames = b'', b''
        base = 32 * n
        for k, (x, y, S) in enumerate(place):
            ents += struct.pack('<IIIIIIII', base + 24 * k, 1, S // 2, S // 2, x, y, 1 | 1 << 16, S | S << 16)
            frames += struct.pack('<II4f', x | y << 16, S | S << 16, x / ATLAS_W, y / H, (x + S) / ATLAS_W,
                                  (y + S) / H)
        body = ents + frames
        ean = b'EAN\0' + struct.pack('<III', 0x20120224, len(body), n | 1 << 24) + body
        return A, ean


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


def build_all(gu_read, effects=MS_EFFECTS, src=SRC):
    """-> (arc entries [(path, type, bytes)], {(set, effect): [(EFL path, element mask, position)]}, report)"""
    import tex
    b = Builder(Source(src), gu_read)
    ents, made, rep = [], {}, []
    for sid, eid in effects:
        files, groups, n, skipped = b.efl(sid, eid)
        ents += [(path, T_EFL, d) for path, d in files]
        made[(sid, eid)] = groups
        rep.append('mhf effect %#x %#x: %d GU entries%s' % (sid, eid, n, ''.join(
            '; not converted: E %d (%s)' % (k, ', '.join(w)) for k, w in skipped)))
    if b.cells:
        A, ean = b.atlas()
        ents += [(ATLAS + TEX_SUFFIX, T_TEX, tex.encode_gu(A, 'rgba8', mips=1)), (ATLAS, T_EAN, ean)]
        rep.append('mhf effect atlas %dx%d, %d sprites' % (A.shape[1], A.shape[0], len(b.cells)))
    return ents, made, rep
