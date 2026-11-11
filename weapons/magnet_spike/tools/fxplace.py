"""fxplace.py : where the converted MHF effect models land in GU, against where MHF draws them (offline, no game run).

  python3 weapons/magnet_spike/tools/fxplace.py [--arc W05.ARC] [--png] [--yaw DEG]

Two sides, each from its own data and its own decoded math (C = traced in code; notes/gu-efl-units.md "Model
transform", notes/assets.md "Effects"):
- MHF (expected): the effect particle (0x113ce4d0, C): world = position + R S v, S = spawn scale x the scale curve,
  R = Rz Ry Rx (D3DXMatrixMultiply by RotationX, then Y, then Z, row vectors) of the SUM of the post's Euler rotation
  and the A spawn rotation (0x113d3bd0, C), position = A position turned by the post's yaw (0x113d37e0, C) + the
  position curve turned by the particle rotation (mhffx docstring, S). Means of the random ranges (U = 0).
  The hand piece (0x1004f7b0, C): v -> bone 18 (origin + R (S v + p)), msgun.py docstring.
- GU (predicted, from OUR BUILT bytes: the EFL unit / element / move blocks, the MOD vertices, the PEL record):
  world = E (pos + R_o S v) (column form of 0xa6d3b4 / 0xa956d8: row v . S . R_o . G100, translation = the particle
  position), S = unit +0x90 (value + range / 2, or the +0x132 curve at the age) x size +0x28, R_o = 0x321694 order
  unit +0x100 bits 0-3 (0: Rz Ry Rx), G100 = the emitter rows x element +0x40 (0xa5a0c4), E = PEL record T R x the
  joint (0x9bea1c / 0x9c0020 / 0x27c40c), pos = the move kind 5 curve (kind 0: the emitter point).
The post frame is the same on both sides except the rotation: MHF adds the post's Euler angles to the particle's,
GU multiplies the emitter's matrix; --yaw shows that difference for a post with that hunter yaw (0 = none).

Per Model unit: centroid offset (cm), max vertex distance (cm), scale ratio GU / MHF (rms radius), orientation error
(deg, Kabsch); --png renders front / side / top views (MHF blue, GU orange, hunter joints as dots) into gen/fxplace/.
The numeric part needs numpy only; --png needs PIL."""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEAPON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(WEAPON))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, mod as modlib
sys.path.append(paths.GU_PY)
from arc import arc_entries, arc_read
import mhffx, mhffx2gu, msgun

ARC = os.path.join(WEAPON, 'romfs', 'nativeNX', 'arc', 'player', 'quest', 'w05.arc')
OUT = os.path.join(WEAPON, 'gen', 'fxplace')
T_EFL, T_MOD = 0x6D5AE854, 0x58A15856
PEL_PATH = 'effect\\pel\\pl\\w05_000'
TOL_CM, TOL_DEG = 1.0, 1.0          # residual tolerance of the fix (cm / degrees)


# ------------------------------------------------------------------------------------------------ rotations

def _rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def _ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def _rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def gu_euler(r, order):
    """GU 0x321694 (row-vector matrices, C for orders 0 and 4) as a column matrix: order 0 = v . Rx . Ry . Rz -> Rz Ry Rx;
    4 = v . Rz . Rx . Ry -> Ry Rx Rz"""
    x, y, z = r
    if order == 0: return _rz(z) @ _ry(y) @ _rx(x)
    if order == 4: return _ry(y) @ _rx(x) @ _rz(z)
    raise ValueError('GU Euler order %d not decoded' % order)


def mhf_euler(r):
    """MHF particle / hand-piece rotation (0x10006ab0 / 0x10006a50 / 0x100069f0 after the scaling, C): Rz Ry Rx"""
    return _rz(r[2]) @ _ry(r[1]) @ _rx(r[0])


# ------------------------------------------------------------------------------------------------ GU side

class Built:
    """the built class arc: {(path, type): bytes}"""
    def __init__(self, path=ARC):
        d = open(path, 'rb').read()
        self.e = {(e[0], e[1]): arc_read(d, e) for e in arc_entries(d)}

    def efls(self):
        return sorted(p for p, t in self.e if t == T_EFL and '\\ms_' in p)

    def vertices(self, path):
        """MOD positions (one rigid mesh, f32 xyz at +0 of a 24-B vertex: mhfmodel.mod_bytes, C for GU's format)"""
        m = modlib.parse(self.e[(path, T_MOD)])
        V = np.frombuffer(m['vb'], np.uint8).reshape(-1, m['mesh_list'][0]['stride'])[:, :12]
        return V.copy().view('<f4').reshape(-1, 3).astype(float)

    def pel(self):
        """PEL list-1 records (msfx.pel_add layout): path -> [(pos, rot deg, scale, joint)]"""
        d = next((b for (p, t), b in self.e.items() if p == PEL_PATH and b[:4] == b'PEL\0'), None)
        out = {}
        if d is None: return out
        i = 8
        for li in range(3):
            n = struct.unpack_from('<I', d, i)[0]; i += 4
            for _ in range(n):
                L = d[i]; path = d[i + 1:i + 1 + L].decode('ascii', 'replace'); st = i + 1 + L + 2
                if li == 1:
                    out.setdefault(path, []).append((struct.unpack_from('<3f', d, st), struct.unpack_from('<3f', d, st + 0x10),
                                                     struct.unpack_from('<3f', d, st + 0x20), struct.unpack_from('<H', d, st + 0x32)[0]))
                i = st + 160
        return out


def entry(efl, i):
    w = struct.unpack_from('<4I', efl, 0x30 + 16 * i)
    return [(x & 0xff, (x >> 8) + 0x30) for x in w]


def _curve3(b, o, age):
    """unit / move vec3 curve (u32 count | 2 << 8, keys {u32 age, x, rx, y, ry, z, rz}): linear, clamped, the range's
    mean (r = 0.5) (0xafb2bc, C linear; gu-efl-move.md)"""
    n = struct.unpack_from('<I', b, o)[0] & 0xff
    ks = [struct.unpack_from('<I6f', b, o + 4 + 28 * k) for k in range(n)]
    val = lambda k: np.array([k[1] + 0.5 * k[2], k[3] + 0.5 * k[4], k[5] + 0.5 * k[6]])
    if age <= ks[0][0]: return val(ks[0])
    for k0, k1 in zip(ks, ks[1:]):
        if age <= k1[0]:
            t = (age - k0[0]) / (k1[0] - k0[0]) if k1[0] > k0[0] else 1.0
            return val(k0) * (1 - t) + val(k1) * t
    return val(ks[-1])


def gu_model(built, efl, i, age):
    """a built Model entry at particle age -> (model path, column matrix 3x3 R S, position in the post frame)"""
    (te, eo), (tu, uo), _, (tm, mo) = entry(efl, i)
    assert tu == 5
    u = lambda o, f='<f': struct.unpack_from(f, efl, uo + o)[0]
    path = efl[uo + 0x50:uo + 0x90].split(b'\0')[0].decode()
    sc = u(0x132, '<H')
    S = (_curve3(efl, uo + sc, age) if sc else
         np.array([u(0x90 + 8 * k) + 0.5 * u(0x94 + 8 * k) for k in range(3)])) * u(0x28)
    rot = np.array([u(0xd0 + 8 * k) + 0.5 * u(0xd4 + 8 * k) + age * (u(0xe8 + 8 * k) + 0.5 * u(0xec + 8 * k))
                    for k in range(3)])
    el = struct.unpack_from('<2f', efl, eo + 0x40)
    g = el[0] + 0.5 * el[1]                                           # gen +0xf8 x the emitter rows (0xa5a0c4)
    R = gu_euler(rot, u(0x100, '<I') & 0xf) @ np.diag(S) * g
    pos = np.zeros(3)
    if tm & 0xf == 5:                                                 # kind 5: pos = E (spawn + curve(age)) (C)
        pos = _curve3(efl, mo + struct.unpack_from('<I', efl, mo + 0x70)[0], age)
    return path, R, pos


# ------------------------------------------------------------------------------------------------ MHF side

def mhf_model(src, st, a, e, f, ls, yaw=0.0):
    """MHF particle at key time f -> (mesh index, column 3x3 R S, position) in the post frame (post rotation (0, yaw,
    0)); means of the ranges"""
    sk = st.curve_at(e['c_scl'], f) if e['c_scl'] else (1.0, 1.0, 1.0)
    S = np.array(a['scl']) * np.array(sk)
    rot = np.array(a['rot']) + (0.0, yaw, 0.0)                        # the Euler sum (0x113d3bd0, C)
    R = mhf_euler(rot)
    pos = _ry(yaw) @ np.array(a['pos'])                               # turned by the post's yaw (0x113d37e0, C)
    if e['c_pos'] and st.curve(e['c_pos']):
        pos = pos + mhffx2gu._rot(st.curve_at(e['c_pos'], f), tuple(rot))
    return e['mesh'], R @ np.diag(S), pos


def model_units(src, built):
    """every built Model entry with its MHF particle, in mhffx2gu.Builder.efl's order -> [(EFL path, entry, sid, eid,
    a, e)]"""
    out = []
    for path in built.efls():
        if '_gun' in path: continue
        base = path.split('\\')[-1].split('_')
        if base[0] != 'ms' or len(base) < 3: continue
        sid, eid = int(base[1], 16), int(base[2], 16)
        out.append((sid, eid))
    rows = []
    for sid, eid in sorted(set(out)):
        st = src.set(sid)
        by_pos = {}
        for a, e, ok, why in mhffx2gu.particles(st, eid):
            if not ok: continue
            for _ in range(max(1, a['count'])):
                by_pos.setdefault(tuple(round(x, 2) for x in a['pos']), []).append((a, e))
        seq = [x for v in by_pos.values() for x in v]
        name = mhffx2gu.efl_name(sid, eid)
        for k in range(0, len(seq), 32):
            p = name + ('_%d' % (k // 32) if k else '')
            efl = built.e.get((p, T_EFL))
            if efl is None: continue
            for i, (a, e) in enumerate(seq[k:k + 32]):
                if entry(efl, i)[1][0] == 5: rows.append((p, i, sid, eid, st, a, e))
    return rows


# ------------------------------------------------------------------------------------------------ metrics

def metrics(G, M):
    """(centroid offset, max vertex distance, scale ratio, orientation error deg) between matching vertex sets"""
    cg, cm = G.mean(0), M.mean(0)
    A, B = G - cg, M - cm
    rg, rm = math.sqrt((A ** 2).sum(1).mean()), math.sqrt((B ** 2).sum(1).mean())
    U, _, Vt = np.linalg.svd(B.T @ A)
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    Q = U @ D @ Vt
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Q) - 1) / 2))))
    return (float(np.linalg.norm(cg - cm)), float(np.linalg.norm(G - M, axis=1).max()),
            rg / rm if rm > 1e-9 else float('nan'), ang)


def units_table(src, built, yaw=0.0):
    """-> rows (EFL, entry, sid, eid, E id, mesh, metrics, (G, M, tris))"""
    out, verts = [], {}
    for p, i, sid, eid, st, a, e in model_units(src, built):
        if e.get('F'): continue                  # F paths: the converter's own simulation on both sides
        ls = a['p5c'] if a['p5c'] >= mhffx.LIFE_MIN else 1.0
        D = a['frame']
        age = D + int(round(0.5 * e['life'] * ls))   # mid-life, GU particle age; MHF key time = (age - D) / ls
        f = (age - D) / ls
        efl = built.e[(p, T_EFL)]
        path, Rg, pg = gu_model(built, efl, i, age)
        if path not in verts: verts[path] = built.vertices(path)
        V = verts[path]
        mi, Rm, pm = mhf_model(src, st, a, e, f, ls, yaw)
        Vm = np.array(src.meshes[mi]['pos'], float)
        rec = np.array(a['pos'])                 # the PEL record's offset = the group's MHF base (msbuild)
        G = (_ry(yaw) @ (rec + pg + (Rg @ V.T).T).T).T if yaw else rec + pg + (Rg @ V.T).T
        M = pm + (Rm @ Vm.T).T
        out.append((p, i, sid, eid, e['id'], mi, metrics(G, M), (G, M)))
    return out


# ------------------------------------------------------------------------------------------------ follow modes

def follow_check(src, built, psi=math.radians(30.0), tilt=(math.radians(40.0), math.radians(25.0))):
    """the per-motion keys with follow mode d 3 / 4 (msfxposts.key_mode 'fixyaw' / 'fixyaw90'): MHF turns the
    effect by (0, the hunter's yaw [+ 90 deg], 0) at the key (0x1146b370, C); the port before test 22 used the
    joint's full rotation ('fix'), now that yaw. Test frame: hunter yaw psi, the joint turned against it by Rx(tilt
    0) Rz(tilt 1). -> [(effect, mode, EFL, entry, max vertex distance before, after)] (cm, post frame; the joint
    point cancels)"""
    import msfxposts
    dat = open(os.path.join(ROOT, 'dump', 'mhf', 'zz', 'mhfdat.dec.bin'), 'rb').read()
    modes = {}
    for key, f, eff, bone, off, gate, mode in msfxposts.motion_keys(dat):
        if mode in ('fixyaw', 'fixyaw90'): modes.setdefault(eff, set()).add(mode)
    out = []
    base = {(r[0], r[1]): r for r in units_table(src, built, 0.0) if (r[2], r[3]) in modes}
    for mode in ('fixyaw', 'fixyaw90'):
        y = psi + (math.pi / 2 if mode == 'fixyaw90' else 0.0)
        Rj = _ry(y) @ _rx(tilt[0]) @ _rz(tilt[1])        # the joint's full rotation (the 'fix' post)
        for r in units_table(src, built, y):
            if mode not in modes.get((r[2], r[3]), ()): continue
            G_after, M = r[7]
            G0 = base[(r[0], r[1])][7][0]
            G_before = (Rj @ G0.T).T
            out.append(((r[2], r[3]), mode, r[0], r[1], float(np.linalg.norm(G_before - M, axis=1).max()),
                        float(np.linalg.norm(G_after - M, axis=1).max())))
    return out


# ------------------------------------------------------------------------------------------------ the hand piece

def shot_pose(frame=msgun.FRAME):
    """MHF body bones at the shot (action 82's motion, the post frame) -> {bone: 4x4} in the hunter's root frame"""
    import aan, fskl, msact, msmot
    MHF = os.path.join(ROOT, 'dump', 'mhf')
    acts = msact.actions(open(os.path.join(MHF, 'zz', 'mhfdat.dec.bin'), 'rb').read())
    mot = [m for k, m, *_ in acts[msgun.ACTIONS[0]]['steps'] if k in (3, 4, 5)][0]
    w13 = aan.parse(open(os.path.join(MHF, 'motion', 'w13.aan'), 'rb').read())
    _, bb = fskl.parse(open(os.path.join(MHF, 'player', 'm_editpl.fskl'), 'rb').read())
    return mot, msmot.body_world(w13, bb, mot)(frame)


def hand_piece(src, built, W):
    """-> (MHF expected (n, 3), GU predicted from the built MOD / unit / PEL (n, 3), triangles) in the hunter frame"""
    import fmod
    B = W[msgun.BONE]
    Mv, tris, base = [], [], 0
    for mi, (pos, scl, rot) in zip(msgun.MESHES, msgun.PARTS):
        R = mhf_euler(rot)
        v = np.array(src.meshes[mi]['pos'], float)
        Mv.append((v * (msgun.K * np.array(scl)) + msgun.K * np.array(pos)) @ R.T)   # 0x1004f7b0 (C)
        tris += [(x + base, y + base, z + base) for x, y, z, _ in fmod.triangles(src.meshes[mi])]; base += len(v)
    M = np.concatenate(Mv) + msgun.ORIGIN
    M = (B[:3, :3] @ M.T).T + B[:3, 3]
    efl = built.e[(msgun.EFL, T_EFL)]
    path, Rg, pg = gu_model(built, efl, 0, msgun.LIFE // 2)
    V = built.vertices(path)
    rec = built.pel().get(msgun.EFL, [((0, 0, 0), (0, 0, 0), (1, 1, 1), 0xffff)])[0]
    Rr = gu_euler(np.radians(rec[1]), 0) * rec[2][0]                  # PEL rotation (deg) x scale, R = Rz Ry Rx (S)
    G = np.array(rec[0]) + pg + (Rr @ (Rg @ V.T)).T                   # the record T R in the joint frame (0x9bea1c)
    G = (B[:3, :3] @ G.T).T + B[:3, 3]                                # joint 12 = MHF bone 18 (same frames, S)
    return M, G, tris, rec


# ------------------------------------------------------------------------------------------------ pictures

VIEWS = (('front', 0, 1, 1), ('side', 2, 1, 1), ('top', 0, 2, -1))   # (name, horizontal axis, vertical axis, sign)


def render(path, sets, joints=None, px=360, title=''):
    """orthographic front (x, y) / side (z, y) / top (x, z) views of point sets [(V, tris, rgba)] -> PNG"""
    from PIL import Image, ImageDraw
    allp = np.concatenate([V for V, _, _ in sets] + ([np.array(list(joints.values()))] if joints else []))
    lo, hi = allp.min(0), allp.max(0)
    span = float((hi - lo).max()) * 1.1 + 1.0
    mid = (lo + hi) / 2
    img = Image.new('RGBA', (px * 3, px + 20), (255, 255, 255, 255))
    for k, (name, h, v, sg) in enumerate(VIEWS):
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(layer)
        X = lambda P: (k * px + px / 2 + (P[..., h] - mid[h]) / span * px,
                       20 + px / 2 - sg * (P[..., v] - mid[v]) / span * px)
        for V, tris, col in sets:
            x, y = X(V)
            for a, b, c in tris:
                dr.polygon([(x[a], y[a]), (x[b], y[b]), (x[c], y[c])], fill=col)
        if joints:
            for bn, q in joints.items():
                x, y = X(np.array(q)); dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 0, 255))
        img = Image.alpha_composite(img, layer)
        ImageDraw.Draw(img).text((k * px + 4, 2), '%s %s' % (title, name), fill=(0, 0, 0, 255))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert('RGB').save(path)


def render_cam(path, sets, joints, eye=(70.0, 190.0, -260.0), at=(-20.0, 110.0, 120.0), px=600, title=''):
    """a perspective view from behind the hunter's right shoulder (as GU's aim camera, S) -> PNG; painter's order"""
    from PIL import Image, ImageDraw
    eye, at = np.array(eye), np.array(at)
    f = (at - eye) / np.linalg.norm(at - eye); r = np.cross((0, 1, 0), f); r /= np.linalg.norm(r); u = np.cross(f, r)
    def X(P):
        q = (np.asarray(P) - eye) @ np.c_[r, u, f]
        return px / 2 + q[..., 0] / q[..., 2] * px * 0.9, px / 2 - q[..., 1] / q[..., 2] * px * 0.9, q[..., 2]
    img = Image.new('RGBA', (px, px), (255, 255, 255, 255))
    for V, tris, col in sets:
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(layer)
        x, y, z = X(V)
        for a, b, c in sorted(tris, key=lambda t: -(z[t[0]] + z[t[1]] + z[t[2]])):
            dr.polygon([(x[a], y[a]), (x[b], y[b]), (x[c], y[c])], fill=col)
        img = Image.alpha_composite(img, layer)
    dr = ImageDraw.Draw(img)
    for bn, q in joints.items():
        x, y, _ = X(np.array(q)); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(0, 0, 0, 255)); dr.text((x + 5, y), str(bn), fill=(0, 0, 0, 255))
    dr.text((4, 4), title, fill=(0, 0, 0, 255))
    img.convert('RGB').save(path)


BLUE, ORANGE = (40, 90, 220, 110), (240, 130, 20, 110)


def main(argv):
    arc = argv[argv.index('--arc') + 1] if '--arc' in argv else ARC
    yaw = math.radians(float(argv[argv.index('--yaw') + 1])) if '--yaw' in argv else 0.0
    png = '--png' in argv
    global OUT
    if '--out' in argv: OUT = argv[argv.index('--out') + 1]
    src, built = mhffx2gu.Source(), Built(arc)
    mot, W = shot_pose()
    M, G, tris, rec = hand_piece(src, built, W)
    m = metrics(G, M)
    print('hand piece (motion %d f%d, bone %d / joint %d, PEL offset %s): centroid %.1f cm, max %.1f cm, scale %.3f, '
          'orientation %.1f deg' % (mot, msgun.FRAME, msgun.BONE, rec[3], tuple(round(x, 1) for x in rec[0]), *m))
    print('  MHF centroid %s, GU centroid %s, MHF bone 18 at %s (hunter frame, cm)' % (
        M.mean(0).round(1), G.mean(0).round(1), W[18][:3, 3].round(1)))
    rows = units_table(src, built, yaw)
    rows.sort(key=lambda r: -r[6][1])
    print('Model units: %d (yaw %.0f deg); worst by max vertex distance:' % (len(rows), math.degrees(yaw)))
    print('  %-26s %3s %5s %4s %4s %9s %9s %7s %8s' % ('EFL', 'e', 'set', 'eff', 'mesh', 'centroid', 'max', 'scale',
                                                   'orient'))
    for p, i, sid, eid, eidn, mi, (c, mx, s, o), _ in rows[:10]:
        print('  %-26s %3d %5x %4x %4d %9.2f %9.2f %7.3f %8.2f' % (p.split('\\')[-1], i, sid, eid, mi, c, mx, s, o))
    if rows:
        ms = np.array([r[6] for r in rows])
        bad = sum(1 for r in rows if r[6][1] > TOL_CM or r[6][3] > TOL_DEG)
        print('  summary: max vertex distance median %.2f / max %.2f cm, orientation max %.2f deg, scale %.3f-%.3f; '
              '%d / %d over %.0f cm / %.0f deg' % (np.median(ms[:, 1]), ms[:, 1].max(), ms[:, 3].max(),
                                                    np.nanmin(ms[:, 2]), np.nanmax(ms[:, 2]), bad, len(rows), TOL_CM,
                                                    TOL_DEG))
    fc = follow_check(src, built)
    if fc:
        effs = sorted({'%x:%x' % e for e, *_ in fc})
        bef, aft = np.array([x[4] for x in fc]), np.array([x[5] for x in fc])
        print('follow mode d 3 / 4 keys (%s; hunter yaw 30 deg, joint turned Rx 40 Rz 25 against it): %d Model units, '
              'max vertex distance before (joint rotation) median %.1f / max %.1f cm, after (hunter yaw) median %.1f / '
              'max %.1f cm' % (', '.join(effs), len(fc), np.median(bef), bef.max(), np.median(aft), aft.max()))
    if png:
        J = {b: W[b][:3, 3] for b in (0, 2, 9, 10, 12, 13, 14, 16, 17, 18, 20)}
        render(os.path.join(OUT, 'hand_piece.png'), [(M, tris, BLUE), (G, tris, ORANGE)], J,
               title='hand piece (MHF blue, GU orange)')
        render_cam(os.path.join(OUT, 'hand_piece_aimcam.png'), [(M, tris, BLUE), (G, tris, ORANGE)], J,
                   title='hand piece from behind the right shoulder (MHF blue, GU orange; bone numbers MHF)')
        hand = {b: W[b][:3, 3] for b in (16, 17, 18)}
        render(os.path.join(OUT, 'hand_piece_close.png'), [(M, tris, BLUE), (G, tris, ORANGE)], hand,
               title='hand piece, forearm')
        import fmod
        for p, i, sid, eid, eidn, mi, mt, (Gu, Mh) in rows[:10]:
            t = [(a, b, c) for a, b, c, _ in fmod.triangles(src.meshes[mi])]
            render(os.path.join(OUT, '%s_e%02d.png' % (p.split('\\')[-1], i)), [(Mh, t, BLUE), (Gu, t, ORANGE)],
                   {'post': (0.0, 0.0, 0.0)}, title='%x:%x E %d mesh %d' % (sid, eid, eidn, mi))
        print('PNGs in %s' % OUT)
    return rows


if __name__ == '__main__':
    main(sys.argv[1:])
