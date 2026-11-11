"""mshud.py: the Magnet Spike's HUD gauge look (test 1: "the in-game HUD is the Charge Blade's").

Class 5 drives the Charge Blade's gauge widget (build.py word 0x665b34; ms_class.c ms_hud: 5 phials = the magnet
gauge's bars, colour = the mode). Its .gui (eng\\GUI\\01_quest\\hud\\hud14_chargeAx, quest_eng.arc) draws the vials
and the shield from HD_hud00. This writes a copy of HD_hud00 with MHF's Magnet Spike HUD art (MHF-Z's UI bank
dat/mhf_90c.bin.xbox, PNG 4, kept as dump/mhf/ui/mhf_90c_04.png) painted over them: the full vial = a gauge cell
(MHF's cell frame, white inside: GU tints it), the empty vial = MHF's dark cell, the shield = MHF's horseshoe; the
module points the gauge .gui's HD_hud00 entry at it while a Magnet Spike hunter owns the widget. The base is the HD UI
mod's HD_hud00 when installed (the user's), else GU's.

  mshud.py [OUT.tex]      default: weapons/magnet_spike/romfs/nativeNX/mh4uport/ms_hud00.tex
  mshud.py reticle [DIR]  MHF's aim reticle on GU's scope HUD (build_reticle): DIR/ms_reticle{0,1,2}.tex, default
                          weapons/magnet_spike/romfs/nativeNX/mh4uport; prints the static check
"""
import os, struct, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEAPON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(WEAPON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import weapons4u as W, tex                                      # noqa: E402

HDUI_QUEST = os.path.expanduser('~/.config/Ryujinx/mods/contents/0100770008dd8000/HD UI v4/romfs/nativeNX/eng/arc/'
                                'quest_eng.arc')
TEX_PATH = 'eng\\GUI\\99_texture\\HD_hud00_BM_NOMIP'
MHF_ART = os.path.join(ROOT, 'dump', 'mhf', 'ui', 'mhf_90c_04.png')
OUT = os.path.join(WEAPON, 'romfs', 'nativeNX', 'mh4uport', 'ms_hud00.tex')

# CB's pieces in HD_hud00 (2048 x 2048): a pixel inside each; the piece = its 8-connected opaque pixels (alpha > 16)
CB = {'vial_full': (1071, 771), 'vial_empty': (1168, 771), 'shield_fill': (961, 1023), 'shield_frame': (1088, 1000)}
# MHF's pieces in mhf_90c_04 (256 x 512): one gauge cell with its black frame, the grey horseshoe
MHF_CELL = (127, 281, 151, 298)
MHF_HORSESHOE = (221, 308, 255, 341)


def bbox(img, seed, limit=160):
    """bounding box (x0, y0, x1, y1) of the opaque piece holding pixel seed, searched within limit pixels of it"""
    sx, sy = seed
    a = img[..., 3] > 16
    if not a[sy, sx]: raise SystemExit('no CB piece at %r' % (seed,))
    seen, todo = {(sx, sy)}, [(sx, sy)]
    while todo:
        x, y = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q in seen or abs(q[0] - sx) > limit or abs(q[1] - sy) > limit or not a[q[1], q[0]]: continue
                seen.add(q); todo.append(q)
    xs, ys = [p[0] for p in seen], [p[1] for p in seen]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def paste_fit(img, box, art, fill_width=True):
    """clear box, then art scaled to the box's width (or to fit it), centred, nearest-neighbour (pixel art)"""
    x0, y0, x1, y1 = box
    img[y0:y1, x0:x1] = 0
    bw, bh = x1 - x0, y1 - y0
    k = bw / art.width if fill_width else min(bw / art.width, bh / art.height)
    w, h = max(1, round(art.width * k)), max(1, min(bh, round(art.height * k)))
    a = np.array(art.resize((w, h), Image.NEAREST))
    ox, oy = x0 + (bw - w) // 2, y0 + (bh - h) // 2
    img[oy:oy + h, ox:ox + w] = a


def build(out=OUT):
    if os.path.exists(HDUI_QUEST):
        src, arc = 'HD UI v4', W.gu_arc(open(HDUI_QUEST, 'rb').read())
    else:
        src, arc = 'GU', W.gu_arc(W.RomFS(W.GU_ROMFS).read('/nativeNX/eng/arc/quest_eng.arc'))
    base = tex.decode(arc[TEX_PATH])
    img = np.array(base, np.uint8).copy()
    k = img.shape[1] / 2048                                         # GU's own HD_hud00 is 512 px, HD UI's 2048 (4x)
    boxes = {n: bbox(img, (round(x * k), round(y * k)), round(160 * k)) for n, (x, y) in CB.items()}
    full, empty = boxes['vial_full'], boxes['vial_empty']        # one cell height for both (the empty vial's open
    boxes['vial_empty'] = (empty[0], full[1], empty[2], full[3])   # neck makes its piece shorter)
    mhf = Image.open(MHF_ART).convert('RGBA')
    cell = mhf.crop(MHF_CELL)
    lit = np.array(cell)
    inner = (lit[..., 3] > 128) & (lit[..., :3].max(-1) > 24)        # the cell's dark inside (not its black frame)
    lit[inner] = (255, 255, 255, 255)
    paste_fit(img, boxes['vial_full'], Image.fromarray(lit))
    paste_fit(img, boxes['vial_empty'], cell)
    paste_fit(img, boxes['shield_fill'], mhf.crop(MHF_HORSESHOE), fill_width=False)
    x0, y0, x1, y1 = boxes['shield_frame']
    img[y0:y1, x0:x1] = 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(tex.encode_gu(img, 'bc3', mips=1))
    return '%s: %dx%d from %s HD_hud00; CB pieces %s' % (os.path.relpath(out, ROOT), img.shape[1], img.shape[0], src,
                                                         {k: tuple(int(v) for v in b) for k, b in boxes.items()})


# ---------------------------------------------------------------------------------------------------------- reticle
# MHF's aim reticle (notes/mechanics.md "MHF's reticle", C): 0x10339700 draws sprite 0xb6 of HUD context 4 (bank =
# dat/mhf_90c.bin entry 20, sprite table at +0x1c) at the screen centre, scale min(height / 720, 1). Its three frames
# are one cell (u 1, v 323, 46 x 46, origin -23 -23) of texture index 0 = texture ID 0x0b14 = mhf_90c entry 4 (the
# loader 0x1096ce81's table 0x11881658: entry 4 -> 0x0b14), i.e. dump/mhf/ui/mhf_90c_04.png, tinted by the cell's
# ARGB colour (0x113ecc60 multiplies it in): frame 0 repel possible 0xff0b99ff blue, 1 attract possible 0xffc62900
# red, 2 neither 0xffffffff white.
MHF_RETICLE = (1, 323, 47, 369)
MHF_RETICLE_RGB = ((0x0b, 0x99, 0xff), (0xc6, 0x29, 0x00), (0xff, 0xff, 0xff))
RETICLE_DIR = os.path.join(WEAPON, 'romfs', 'nativeNX', 'mh4uport')
RETICLE_NAME = 'ms_reticle%d.tex'                     # the module's res_get("mh4uport\\ms_reticleN")
SCOPE_GUI = 'eng\\GUI\\01_quest\\hud\\hud6_scope'
HUD01_PATH = 'eng\\GUI\\99_texture\\HD_hud01_BM_NOMIP'
DTI_TEXTURE, DTI_TEXTURESET = 0x1b6313a3, 0x4f7228fc  # cGUIObjTexture / cGUIObjTextureSet (CRC of the DTI names)


def scope_users(g):
    """hud6_scope (GUI v0x22715, header 72 x u32 H) -> (hud01 entry id, {user: [(u0, v0, u1, v1), ...]}) in the .gui's
    texel units (its entry says 256 x 512) for every instance that samples HD_hud01. Layout (C): instances 36 B at
    H[43] (count H[12]; +0x10 name, +0x14 DTI hash, +0x18 first param, +0x20 TextureSet block offset into H[70]),
    params 20 B at H[45] (+4 type, +0xc name, +0x10 value: type 7 Texture = int at H[68] + value = the entry id, type 4
    = 4 floats at H[69] + value), texture entries 64 B at H[58] (count H[28]; +0 id, +0x2c path), strings H[65].
    cGUIObjTexture draws mTextureRect; a cGUIObjTextureSet block = (count, first vertex, count rects) and draws quad r
    from the .gui's vertex buffer (file +0x120, H[36] bytes of 24-byte vertices x y z colour u v; the loader 0xb7f988
    copies it to the rGUI's buffer +0x80, the set's draw 0xa515f8 strips count * 6 - 2 vertices from its first) at
    vertices first + 6r .. + 3"""
    H = struct.unpack_from('<72I', g, 0)
    u32 = lambda o: struct.unpack_from('<I', g, o)[0]
    name = lambda o: g[H[65] + o:g.index(b'\0', H[65] + o)].decode('latin1')
    ent = {u32(H[58] + 64 * i): name(u32(H[58] + 64 * i + 0x2c)) for i in range(H[28])}
    hud01 = [i for i, p in ent.items() if p == HUD01_PATH]
    assert len(hud01) == 1, ent
    starts = sorted({u32(H[43] + 36 * i + 0x18) for i in range(H[12])} | {u32(H[47] + 36 * i + 0x1c)
                                                                          for i in range(H[17])} | {H[14]})
    vo, nv = u32(0x120), H[36] // H[71]
    vert = [struct.unpack_from('<3fI2f', g, vo + H[71] * i) for i in range(nv)]
    def samples_hud01(k):
        w = struct.unpack_from('<5I', g, H[45] + 20 * k)
        return name(w[3]) == 'Texture' and w[1] == 7 and struct.unpack_from('<i', g, H[68] + w[4])[0] == hud01[0]
    every = {k for k in range(H[14]) if samples_hud01(k)}  # every Texture param naming hud01 (instances, objects)
    seen, users = set(), {}
    for i in range(H[12]):
        b = H[43] + 36 * i
        first, kind = u32(b + 0x18), u32(b + 0x14)
        if kind not in (DTI_TEXTURE, DTI_TEXTURESET): continue    # roots / nulls / colour adjusts own no texture
        last = next(s for s in starts if s > first)
        ps = {}
        for k in range(first, last):
            w = struct.unpack_from('<5I', g, H[45] + 20 * k)
            ps[name(w[3])] = (w[1] & 0xff, w[4])
            if samples_hud01(k): seen.add(k)
        if ps.get('Texture', (0,))[0] != 7 or struct.unpack_from('<i', g, H[68] + ps['Texture'][1])[0] != hud01[0]:
            continue
        key = 'I%d %s' % (i, name(u32(b + 0x10)))
        if kind == DTI_TEXTURE:
            r = struct.unpack_from('<4f', g, H[69] + ps['mTextureRect'][1])
            users[key] = [(min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))]
        elif kind == DTI_TEXTURESET:
            o = H[70] + u32(b + 0x20)
            cnt, v0 = struct.unpack_from('<II', g, o)
            assert v0 + 6 * cnt - 2 <= nv, key
            rects = []
            for r in range(cnt):
                q = vert[v0 + 6 * r:v0 + 6 * r + 4]
                rects.append((min(v[4] for v in q), min(v[5] for v in q), max(v[4] for v in q), max(v[5] for v in q)))
            users[key] = rects
            users[key + ' quads'] = [vert[v0 + 6 * r:v0 + 6 * r + 4] for r in range(cnt)]
    if seen != every: raise SystemExit('hud6_scope: hud01 Texture params outside the decoded users: %r' % (every - seen))
    return hud01[0], users


def reticle_quarter(k):
    """MHF's cell -> its top-left quarter at k texels per HUD unit, 23k x 23k RGBA (the HUD square x, y in [-23, 0]).
    MHF's art is mirror-symmetric about its column 22 and between its rows 22 / 23 (3 pixels differ by <= 21 / 255),
    so the four mirrored TextureSet quadrants rebuild it; the port centres column 22 on x = 0 (MHF's origin -23 puts
    it 0.5 px left of the centre: deviation, half a HUD unit)"""
    cell = np.array(Image.open(MHF_ART).convert('RGBA').crop(MHF_RETICLE))
    assert cell.shape[:2] == (46, 46)
    n = 23 * k
    t = (np.arange(n) + 0.5) / k - 23.0
    col = np.floor(t + 22.5).astype(int)
    row = np.floor(t + 23.0).astype(int)
    out = np.zeros((n, n, 4), np.uint8)
    ok_c, ok_r = col >= 0, row >= 0
    out[np.ix_(ok_r, ok_c)] = cell[np.ix_(row[ok_r], col[ok_c])]
    return out


def build_reticle(out_dir=RETICLE_DIR):
    """three copies of the live HD_hud01 (the HD UI mod's when installed, else GU's): TextureSet TexS_scope's four
    quadrants (UV (0, 32)-(240, 272), mirrored about the screen centre = texel (240, 272); the only centred geometry
    of element 0, the tree GU's scope widget shows for class 5) carry MHF's reticle quarter in its centre corner in
    frame N's colour; everything else is empty: the copies are bound only while the local class-5 hunter aims, so
    GU's arrows, bars, ring, zoom gauge and crosshairs (every other user of the entry) vanish then, as in MHF. The
    reticle corner stays 1 texel away from every other user's rect (none of them samples it). Returns the report;
    exits on a failed check"""
    if os.path.exists(HDUI_QUEST):
        src, arc = 'HD UI v4', W.gu_arc(open(HDUI_QUEST, 'rb').read())
    else:
        src, arc = 'GU', W.gu_arc(W.RomFS(W.GU_ROMFS).read('/nativeNX/eng/arc/quest_eng.arc'))
    g = arc[SCOPE_GUI]
    hid, users = scope_users(g)
    base = np.array(tex.decode(arc[HUD01_PATH]), np.uint8)
    Hh, Ww = base.shape[:2]
    ents = struct.unpack_from('<I', g, 4 * 58)[0]
    e = next(ents + 64 * i for i in range(struct.unpack_from('<I', g, 4 * 28)[0])
             if struct.unpack_from('<I', g, ents + 64 * i)[0] == hid)
    gw, gh = struct.unpack_from('<HH', g, e + 0xc)
    k = Ww // gw
    if k * gw != Ww or k * gh != Hh: raise SystemExit('reticle: HD_hud01 %dx%d is no multiple of the .gui\'s %dx%d'
                                                       % (Ww, Hh, gw, gh))
    scope = users.pop('I1 TexS_scope quads')
    rects = users.pop('I1 TexS_scope')
    quads = rects[:4]
    if any(q != (0.0, 32.0, 240.0, 272.0) for q in quads) or [(v[0], v[1]) for v in scope[0]] != \
            [(-240.0, -240.0), (0.0, -240.0), (-240.0, 0.0), (0.0, 0.0)]:
        raise SystemExit('reticle: TexS_scope quadrants are not the decoded (0, 32)-(240, 272): %r' % quads)
    others = {n: rs for n, rs in users.items() if not n.endswith(' quads')}
    others['I1 TexS_scope bars'] = rects[4:]
    keep = np.zeros((Hh, Ww), bool)                   # every other user's texels, 1 texel around them
    for rs in others.values():
        for u0, v0, u1, v1 in rs:
            keep[max(0, int(np.floor(v0 * k)) - 1):int(np.ceil(v1 * k)) + 1,
                 max(0, int(np.floor(u0 * k)) - 1):int(np.ceil(u1 * k)) + 1] = True
    q0 = (0 * k, 32 * k, 240 * k, 272 * k)
    region = np.zeros((Hh, Ww), bool)
    region[q0[1]:q0[3] + 1, q0[0]:q0[2] + 1] = True    # the quadrant's UV + the 1-texel edge padding
    quarter = reticle_quarter(k)
    n = quarter.shape[0]
    cx, cy = 240 * k, 272 * k                         # the texel corner drawn at the screen centre
    pad = np.zeros((n + 1, n + 1, 4), np.uint8)       # one texel past the corner (u 240 / v 272) for the bilinear
    pad[:n, :n] = quarter                             # edge: the mirror of the last texel is itself
    pad[n, :n] = quarter[n - 1]
    pad[:n, n] = quarter[:, n - 1]
    pad[n, n] = quarter[n - 1, n - 1]
    paint = np.zeros((Hh, Ww), bool)
    paint[cy - n:cy + 1, cx - n:cx + 1] = True
    if (paint & keep).any(): raise SystemExit('reticle: the painted corner touches another user of hud01')
    if cy + 1 > Hh or cx + 1 > Ww: raise SystemExit('reticle: the painted corner is outside the atlas')
    if (paint & ~region).any(): raise SystemExit('reticle: the painted corner leaves TexS_scope\'s quadrant')
    os.makedirs(out_dir, exist_ok=True)
    outs = []
    for f, rgb in enumerate(MHF_RETICLE_RGB):
        img = np.zeros_like(base)                     # every other hud01 user blanked: the copy is bound only
        art = pad.astype(np.float32)                  # while the local class-5 hunter aims (MHF: the reticle alone)
        art[..., :3] *= np.array(rgb, np.float32) / 255.0
        img[cy - n:cy + 1, cx - n:cx + 1] = np.round(art).astype(np.uint8)
        used = (img != 0).any(-1)
        if (used & ~paint).any(): raise SystemExit('reticle %d: texels outside the reticle corner are not empty' % f)
        if (used & keep).any(): raise SystemExit('reticle %d: another user of hud01 would sample the reticle' % f)
        sim = render_quadrants(img, scope, k, k)
        want = mhf_square(k, rgb)
        err = np.abs(sim.astype(int) - want.astype(int))[..., 3].max()
        if err > 32: raise SystemExit('reticle %d: the quadrants do not rebuild MHF\'s reticle (alpha err %d)' % (f, err))
        path = os.path.join(out_dir, RETICLE_NAME % f)
        with open(path, 'wb') as fh:
            fh.write(tex.encode_gu(img, 'bc3', mips=1))
        outs.append('%s %d KB' % (os.path.basename(path), os.path.getsize(path) // 1024))
    return ('%s: %dx%d (HD_hud01\'s size, %s; entry id %d, .gui %dx%d, x%d); MHF cell %r -> 46 x 46 HUD units at the '
            'centre (TexS_scope corner texel (%d, %d)); blanked (GU art gone while aiming): TexS_scope ring + bars, %s; '
            'kept GU: none on this entry (TexS_align = hud00, Txt_No = custom_pnl2: other entries, not swapped)' % (
                ', '.join(outs), Ww, Hh, src, hid, gw, gh, k, MHF_RETICLE, cx, cy,
                ', '.join(sorted(n.split(' ', 1)[1] + '(' + n.split(' ', 1)[0] + ')' for n in others
                                 if n != 'I1 TexS_scope bars'))))


def render_quadrants(img, quads, k, px, half=30):
    """the four TexS_scope quads drawn (nearest) from img (k texels per .gui texel) over the HUD square
    [-half, half)^2 at px pixels per HUD unit"""
    n = 2 * half * px
    t = (np.arange(n) + 0.5) / px - half
    X, Y = np.meshgrid(t, t)
    out = np.zeros((n, n, 4), np.uint8)
    for q in quads[:4]:
        (x0, y0), (x1, _), (_, y2) = (q[0][0], q[0][1]), (q[1][0], q[1][1]), (q[2][0], q[2][1])
        u0, v0, u1, v2 = q[0][4], q[0][5], q[1][4], q[2][5]
        m = (np.minimum(x0, x1) <= X) & (X < np.maximum(x0, x1)) & (np.minimum(y0, y2) <= Y) & (Y < np.maximum(y0, y2))
        U = u0 + (X - x0) / (x1 - x0) * (u1 - u0)
        V = v0 + (Y - y0) / (y2 - y0) * (v2 - v0)
        ui = np.clip(np.floor(U * k).astype(int), 0, img.shape[1] - 1)
        vi = np.clip(np.floor(V * k).astype(int), 0, img.shape[0] - 1)
        out[m] = img[vi[m], ui[m]]
    return out


def mhf_square(k, rgb, half=30):
    """MHF's reticle as the port shows it (column 22 centred) over the same square"""
    cell = np.array(Image.open(MHF_ART).convert('RGBA').crop(MHF_RETICLE)).astype(np.float32)
    cell[..., :3] *= np.array(rgb, np.float32) / 255.0
    n = 2 * half * k
    t = (np.arange(n) + 0.5) / k
    col = np.floor(t - half + 22.5).astype(int)
    row = np.floor(t - half + 23.0).astype(int)
    out = np.zeros((n, n, 4), np.uint8)
    okc, okr = (col >= 0) & (col < 46), (row >= 0) & (row < 46)
    out[np.ix_(okr, okc)] = np.round(cell[np.ix_(row[okr], col[okc])]).astype(np.uint8)
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['reticle']:
        print(build_reticle(*sys.argv[2:3]))
    else:
        print(build(*sys.argv[1:2]))
