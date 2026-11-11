"""fxlook.py : what the converted MHF effect models LOOK like in GU, against MHF's draw (offline, no game run).

  python3 weapons/magnet_spike/tools/fxlook.py [--arc W05.ARC] [--effect fc5:38 ...] [--all] [--frames N]
                                               [--no-uv] [--vc1x] [--out DIR]

Software rasteriser (numpy + PIL), one contact sheet per effect in gen/fxplace/look/ (gitignored): rows = effect
frames (GU frames = MHF age units, 1/60 s), columns = MHF / GU from a 3/4 view and from above, over a mid-grey
background. Prints per effect the mean absolute difference |MHF - GU| of the pictures (0..255) and, unless --no-uv,
the same with GU's UV layer ignored (what the build before the UV layer drew), so the UV conversion shows as a number.

Each side from its own data and decoded math (C = traced in code; notes/gu-efl-units.md, notes/assets.md "Effects"):
- MHF (expected): the E particle mesh (model0.fmod), placed as fxplace.mhf_model (0x113ce4d0, C); colour = texture x
  vertex colour x the C-key colour (RGBA bytes, linear, 0x113ccaf0, C); UV + the scroll offset of 0x113d0690 (modes
  1-3: 1 / (E +0x18 | +0x1c) / ls per MHF tick = 2 age units, wrapped to [0, 1], C; added to the mesh UVs, S);
  blend E +0x15: 1 additive (src a, one), 0 / 2 alpha (src a, 1 - src a) (0x10b705e0, C).
- GU (predicted, from OUR BUILT bytes): the entry's Model unit, the MOD (f32 position, f16 UV, u8 RGBA), its MRL's
  texture (BC3 decoded), placed as fxplace.gu_model (C); colour = texture x vertex colour x 2 (the 0x7f neutral of
  FDiffuseVertexColorMD, S; --vc1x draws it 1x) x the unit colour curve +0x42 (keys {frame, RGBA, RGBA}, linear: G)
  x unit +0x20 (0xc90b50: CBMaterial fDiffuseColor = RGB / 255 x particle +0x50 / 256, C); UV + layer 0 (unit +0x134
  value block: u0 + du x age with the damping, wrapped to (-1, 1): 0xa99f40 / 0xa6bc0c / 0xcaf17c, C; the material's
  fUVTransform translation, C); blend = unit byte 3 (0xb007fc in 0xc90b50, C): 0 BSBlendAddAlpha, 1 BSBlendBlendAlpha,
  5 / 6 reverse-subtract (efl4u2gu, C); visible from frame 0 to the emit block's life (0xaed0d0, C).
Both: painter's order (back to front per triangle), no depth test, no cull (efx_blend: RSMeshCN, DSZTestWrite: S that
GU's depth write only matters between particles), no lighting (FEmissionConstantEflEmu: S), no fog, no tone map."""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEAPON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(WEAPON))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fxplace, mhffx2gu, mhfmodel, fmod
import mod as modlib, mrl as mrllib, tex as texlib

OUT = os.path.join(WEAPON, 'gen', 'fxplace', 'look')
T_EFL, T_MOD, T_MRL, T_TEX = 0x6D5AE854, 0x58A15856, 0x2749c8a8, 0x241f5deb
CELL = 256
BG = 0.5
VIEWS = (('3/4', math.radians(35.0), math.radians(25.0)), ('top', 0.0, math.radians(89.0)))
VC_GU = 255.0 / 127.0          # GU's effect vertex colour neutral 0x7f (S); --vc1x: 1.0


# ------------------------------------------------------------------------------------------------ raster

def basis(yaw, pitch):
    """orthographic camera looking at the post frame from yaw (about y, from the front = -z) and pitch (down)"""
    f = np.array([-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    r = np.cross((0.0, 1.0, 0.0), f); r /= np.linalg.norm(r)
    return r, np.cross(f, r), f


def sample(img, uv):
    """bilinear, wrapping; uv (n, 2) with v top-down -> (n, 4) float 0..1"""
    H, W = img.shape[:2]
    x = np.mod(uv[:, 0], 1.0) * W - 0.5; y = np.mod(uv[:, 1], 1.0) * H - 0.5
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    x0 %= W; y0 %= H; x1 = (x0 + 1) % W; y1 = (y0 + 1) % H
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) +
            img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def draw(layers, view, box, px=CELL):
    """layers [(P (n, 3), UV (n, 2), COL (n, 4) 0..1 incl. the particle colour, tris, image float 0..1, blend)] ->
    (px, px, 3) float; blend 'add' / 'alpha' / 'sub'"""
    r, u, f = view
    lo, span = box
    out = np.full((px, px, 3), BG)
    items = []
    for li, (P, UV, COL, tris, img, blend) in enumerate(layers):
        q = np.c_[P @ r, P @ u, P @ f]
        sx = (q[:, 0] - lo[0]) / span * px; sy = px - (q[:, 1] - lo[1]) / span * px
        for t in tris:
            items.append((-(q[t[0], 2] + q[t[1], 2] + q[t[2], 2]), li, t, sx, sy))
    items.sort(key=lambda x: x[0])
    for _, li, (a, b, c), sx, sy in items:
        P, UV, COL, tris, img, blend = layers[li]
        xs, ys = np.array([sx[a], sx[b], sx[c]]), np.array([sy[a], sy[b], sy[c]])
        x0, x1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, px)
        y0, y1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, px)
        if x0 >= x1 or y0 >= y1: continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-9: continue
        gy, gx = np.mgrid[y0:y1, x0:x1]
        gx = gx + 0.5; gy = gy + 0.5
        l1 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
        l2 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any(): continue
        w = np.c_[l1[m], l2[m], l3[m]]
        uv = w @ UV[[a, b, c]]
        s = sample(img, uv) * (w @ COL[[a, b, c]])
        rgb, al = np.clip(s[:, :3], 0, None), np.clip(s[:, 3:4], 0, 1)
        Y, X = gy[m].astype(int), gx[m].astype(int)
        dst = out[Y, X]
        if blend == 'add': dst = dst + rgb * al
        elif blend == 'sub': dst = dst - rgb * al
        else: dst = rgb * al + dst * (1 - al)
        out[Y, X] = dst
    return np.clip(out, 0, 1)


# ------------------------------------------------------------------------------------------------ MHF side

def _lerp_keys(keys, f):
    """[(frame, value array)] linear, end values outside"""
    if not keys: return None
    if f <= keys[0][0]: return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0) if f1 > f0 else 1.0
            return v0 + (v1 - v0) * t
    return keys[-1][1]


class MHF:
    def __init__(self, src):
        self.src = src; self.img = {}

    def image(self, mi):
        k = mhfmodel.image_of(self.src, mi)
        if k not in self.img: self.img[k] = self.src.images[k].astype(np.float32) / 255.0
        return self.img[k]

    def layer(self, st, a, e, t):
        """the particle at effect time t (age units) -> raster layer or None"""
        ls = a['p5c'] if a['p5c'] >= mhffx2gu.mhffx.LIFE_MIN else 1.0
        D = a['frame']
        if not (D <= t < D + e['life'] * ls): return None
        f = (t - D) / ls
        mi, RS, pos = fxplace.mhf_model(self.src, st, a, e, f, ls)
        m = self.src.meshes[mi]
        P = pos + np.array(m['pos'], float) @ RS.T
        uv = np.array(m['uv'], float)
        ticks = (t - D) // 2
        if e['uv_mode'] in (1, 2) and e['uv_u']: uv[:, 0] += math.fmod(ticks / e['uv_u'] / ls, 1.0)
        if e['uv_mode'] in (1, 3) and e['uv_v']: uv[:, 1] += math.fmod(ticks / e['uv_v'] / ls, 1.0)
        UV = np.c_[uv[:, 0], 1.0 - uv[:, 1]]                      # images top-down (fmod.py flips v)
        vc = self.src.colours[mi]
        vc = np.full((len(P), 4), 1.0) if vc is None else np.asarray(vc, float) / 255.0
        keys = [(k, np.frombuffer(bytes.fromhex(c), np.uint8).astype(float) / 255.0)
                for k, c, _ in st.colours(e['c_col'])]
        kc = _lerp_keys(keys, f)
        COL = vc * (kc if kc is not None else 1.0)
        tris = [(x, y, z) for x, y, z, _ in fmod.triangles(m)]
        return P, UV, COL, tris, self.image(mi), 'add' if e['draw'] == 1 else 'alpha'


# ------------------------------------------------------------------------------------------------ GU side

BLENDS = {0: 'add', 1: 'alpha', 5: 'sub', 6: 'sub'}


class GU:
    def __init__(self, built, uv=True, vc=VC_GU):
        self.b, self.uv, self.vc = built, uv, vc
        self.mods, self.tex = {}, {}

    def model(self, path):
        if path not in self.mods:
            m = modlib.parse(self.b.e[(path, T_MOD)])
            st = m['mesh_list'][0]['stride']
            V = np.frombuffer(m['vb'], np.uint8).reshape(-1, st)
            P = V[:, 0:12].copy().view('<f4').reshape(-1, 3).astype(float)
            UV = V[:, 16:20].copy().view('<f2').reshape(-1, 2).astype(float)
            COL = V[:, 20:24].astype(float) / 255.0
            ib = np.frombuffer(m['ib'], '<u2')
            tris = []
            for me in m['mesh_list']:
                run = []
                for x in list(ib[me['indexStart']:me['indexStart'] + me['numIndices']]) + [0xFFFF]:
                    if x == 0xFFFF:
                        tris += [tuple(run[k:k + 3]) for k in range(len(run) - 2)]; run = []
                    else: run.append(int(x))
            r = mrllib.read(self.b.e[(path, T_MRL)])
            tp = [p for t, p in r['textures'] if t == T_TEX][0]
            if tp not in self.tex:
                self.tex[tp] = texlib.decode(self.b.e[(tp, T_TEX)]).astype(np.float32) / 255.0
            self.mods[path] = (P, UV, COL, tris, self.tex[tp])
        return self.mods[path]

    def layer(self, efl, i, t, rec=(0.0, 0.0, 0.0)):
        """entry i at effect time t, rec = its PEL record's offset (the group's MHF base, msbuild; fxplace) ->
        raster layer or None"""
        _, (tu, uo), (_, emo), _ = fxplace.entry(efl, i)
        g = lambda o, f='<f': struct.unpack_from(f, efl, uo + o)[0]
        life = sum(x & 0xffff for x in struct.unpack_from('<3I', efl, emo))   # fade-in + hold + fade-out (0xaed0d0)
        if t >= life: return None
        path, RS, pos = fxplace.gu_model(self.b, efl, i, t)
        P0, UV0, COL0, tris, img = self.model(path)
        P = np.asarray(rec, float) + pos + P0 @ RS.T
        UV = UV0.copy()
        vb = g(0x134, '<H')
        if self.uv and vb:
            u0, ur, v0, vr, du, dur, dv, dvr, damp = struct.unpack_from('<9f', efl, uo + vb)
            du, dv = du + 0.5 * dur, dv + 0.5 * dvr
            k = t if abs(damp - 1.0) < 1e-6 else (1 - damp ** t) / (1 - damp)
            UV += (math.fmod(u0 + 0.5 * ur + du * k, 1.0), math.fmod(v0 + 0.5 * vr + dv * k, 1.0))
        co = g(0x42, '<H')
        kc = None
        if co:
            n = struct.unpack_from('<I', efl, uo + co)[0] & 0xff
            keys = []
            for j in range(n):
                fr, ca, cb = struct.unpack_from('<I4s4s', efl, uo + co + 4 + 12 * j)
                keys.append((fr, (np.frombuffer(ca, np.uint8).astype(float) + np.frombuffer(cb, np.uint8)) / 510.0))
            kc = _lerp_keys(keys, t)
        if kc is None: kc = np.frombuffer(efl[uo + 0x48:uo + 0x4c], np.uint8).astype(float) / 255.0
        kc = kc * (g(0x20), g(0x20), g(0x20), 1.0)
        vc = COL0 * (self.vc, self.vc, self.vc, 1.0)
        return P, UV, vc * kc, tris, img, BLENDS.get(efl[uo + 3], 'alpha')


# ------------------------------------------------------------------------------------------------ sheets

def effect_rows(src, built):
    """{(sid, eid): [(EFL path, entry, st, a, e)]} of every built Model unit with its MHF particle (the GU side is
    placed at the group's PEL record offset = the MHF base, as fxplace; a post's own offset is common to both sides)"""
    out = {}
    for p, i, sid, eid, st, a, e in fxplace.model_units(src, built):
        if e.get('F'): continue
        out.setdefault((sid, eid), []).append((p, i, st, a, e))
    return out


def sheet(key, rows, mhf, gu, gu_nouv, nframes, out_dir):
    """render one effect -> (PNG path, mean |MHF - GU|, mean |MHF - GU without the UV layer| or None)"""
    from PIL import Image, ImageDraw
    sid, eid = key
    end = max(a['frame'] + a_life(a, e) for _, _, st, a, e in rows)
    beg = min(a['frame'] for _, _, st, a, e in rows)
    ts = sorted({int(round(beg + (end - beg) * (k + 0.5) / nframes)) for k in range(nframes)})
    sides = []
    for t in ts:
        M = [l for l in (mhf.layer(st, a, e, t) for _, _, st, a, e in rows) if l]
        G = [l for l in (gu.layer(built_efl(gu, p), i, t, a['pos']) for p, i, st, a, e in rows) if l]
        N = [l for l in (gu_nouv.layer(built_efl(gu, p), i, t, a['pos']) for p, i, st, a, e in rows) if l] \
            if gu_nouv else []
        sides.append((t, M, G, N))
    allp = [l[0] for _, M, G, _ in sides for l in M + G]
    if not allp: return None, 0.0, None
    allp = np.concatenate(allp)
    views = [basis(y, p) for _, y, p in VIEWS]
    boxes = []
    for v in views:
        q = np.c_[allp @ v[0], allp @ v[1]]
        lo, hi = q.min(0), q.max(0)
        span = float((hi - lo).max()) * 1.08 + 1.0
        boxes.append(((lo + hi) / 2 - span / 2, span))
    W = CELL * 2 * len(views); H = (CELL + 16) * len(ts) + 20
    img = Image.new('RGB', (W, H), (40, 40, 40)); dr = ImageDraw.Draw(img)
    blends = sorted({('add' if e['draw'] == 1 else 'alpha') for *_, e in rows})
    uvm = sorted({e['uv_mode'] for *_, e in rows})
    dr.text((4, 4), 'MHF %x:%x  %d Model units  MHF blend %s, UV modes %s  |  columns: MHF, GU (%s) per view; '
            'span %s cm' % (sid, eid, len(rows), '/'.join(blends), uvm, 'vertex colour x%.2f' % gu.vc,
                            ' / '.join('%.0f' % b[1] for b in boxes)), fill=(255, 255, 255))
    diffs, diffs_n = [], []
    for r, (t, M, G, N) in enumerate(sides):
        y = 20 + r * (CELL + 16)
        for k, (v, box) in enumerate(zip(views, boxes)):
            a_ = draw(M, v, box); b_ = draw(G, v, box)
            diffs.append(np.abs(a_ - b_).mean() * 255)
            if gu_nouv: diffs_n.append(np.abs(a_ - draw(N, v, box)).mean() * 255)
            for c, pic in enumerate((a_, b_)):
                x = (2 * k + c) * CELL
                img.paste(Image.fromarray((pic * 255).astype(np.uint8)), (x, y + 16))
                lay = M if c == 0 else G
                shown = sum(1 for l in lay if l[2][:, 3].max() > 0)          # alpha > 0 (GU's lead-in keys: 0)
                dr.text((x + 4, y + 2), '%s %s  f%d  (%d particles)' % ('MHF' if c == 0 else 'GU', VIEWS[k][0], t,
                                                                       shown), fill=(255, 255, 255))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'ms_%03x_%03x.png' % (sid & 0xfff, eid))
    img.save(path)
    return path, float(np.mean(diffs)), (float(np.mean(diffs_n)) if diffs_n else None)


def a_life(a, e):
    ls = a['p5c'] if a['p5c'] >= mhffx2gu.mhffx.LIFE_MIN else 1.0
    return e['life'] * ls


def built_efl(gu, path):
    return gu.b.e[(path, T_EFL)]


def main(argv):
    arc = argv[argv.index('--arc') + 1] if '--arc' in argv else fxplace.ARC
    out = argv[argv.index('--out') + 1] if '--out' in argv else OUT
    nf = int(argv[argv.index('--frames') + 1]) if '--frames' in argv else 5
    want = [tuple(int(x, 16) for x in argv[k + 1].split(':')) for k, a in enumerate(argv) if a == '--effect']
    vc = 1.0 if '--vc1x' in argv else VC_GU
    src, built = mhffx2gu.Source(), fxplace.Built(arc)
    rows = effect_rows(src, built)
    if want: keys = [k for k in want if k in rows]
    elif '--all' in argv: keys = sorted(rows)
    else:   # default: the effects with UV-scrolled Model units, most first (the swing arcs), up to 8
        sc = {k: sum(1 for *_, e in v if e['uv_mode'] in (1, 2, 3)) for k, v in rows.items()}
        keys = sorted((k for k in rows if sc[k]), key=lambda k: -sc[k])[:8]
    mhf, gu = MHF(src), GU(built, vc=vc)
    gu_n = None if '--no-uv' in argv else GU(built, uv=False, vc=vc)
    if '--no-uv' in argv: gu = GU(built, uv=False, vc=vc)
    print('effect     units  UV  mean |MHF - GU| (0..255)%s  sheet' % ('' if gu_n is None else '  without the UV layer'))
    for k in keys:
        path, d, dn = sheet(k, rows[k], mhf, gu, gu_n, nf, out)
        nuv = sum(1 for *_, e in rows[k] if e['uv_mode'] in (1, 2, 3))
        print('%3x:%-4x %7d %4d %10.2f %s  %s' % (k[0], k[1], len(rows[k]), nuv, d,
                                                 '' if dn is None else '%25.2f' % dn, path or '(nothing drawn)'))


if __name__ == '__main__':
    main(sys.argv[1:])
