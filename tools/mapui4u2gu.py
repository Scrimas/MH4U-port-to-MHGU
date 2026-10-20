"""mapui4u2gu.py : in-quest area maps (mapUI, kind 49) of the Battlequarters alias (stage 26 -> m28) from MH4U m19.

  mapui4u2gu.py            write monsters/gogmazios/romfs/nativeNX/<lang>/arc/stage/mapUI/m28d/a0N_ui_<lang>.arc
                           (eng fre ger ita spa)
                           and the whole map <lang>/arc/stage/map_com/m28_<lang>.arc (kind 55, see wholemap())
  mapui4u2gu.py preview    also save the composed maps as PNG into the dir given by $UI_PREVIEW
  mapui4u2gu.py gui FILE   dump the instances / position params of a GU map GUI (0x22948394)

World -> map transform (notes/port-checklist.md "Arena 4", Map UI bullet):
  GU (C): cUIOEnlargeMap (DTI 0x184000c, vtable 0x17754f4) setup 0x61c318 takes the per-area record
    rec = table[stage][area] (table 0x1774dec, 14 pointers per stage; 2nd table 0x177540c when 0x55df28 < 3), keeps it at
    this+0x15c, scale this+0x70 = rec.f32[+0x2c] * 128 / 10000 (0x61c5e0..0x61c5f8); the icon update 0x619bf8 calls
    vtable+0x6c = 0x61cacc: map = (x * scale + 2 * rec.s16[+0x30], z * scale + 2 * rec.s16[+0x32]) in HD pixels from
    the centre of the 256x256 map texture. Records 0x34 B: +0..+0x10 GUI file IDs per language (loader 0x61c288),
    +0x1c/+0x24/+0x28 GUI object ids, +0x2c f32, +0x30/+0x32 s16. Stage 26: 0x16382ac/0x16382e0/0x1638314.
  4U (C): 0x5a5f14(area, f32 *scale, s16 off[2]) reads table 0xeebe0c + 0x18 * stage, +0xc -> 8-byte records
    {f32 scale, s16 x, s16 y} per area (area index = 0x69dbf0(area) = the area except on stage 13); icons 0xb82e38:
    u = off.x + (x * scale + 20000 * 0.5) / 20000 * 128 (same for v with z) in pixels of the 128x128 map picture
    (layout pane map1 = atlas UV (0,0)-(0.5,1), 1:1). m19 = 0xeebfd4 -> records 0xeebb10.
  => GU (map / 2 + 64) == 4U (u, v) when the GU record holds the 4U scale and offsets and the GU texture is the 4U
     picture at 2x: no re-fit needed. module/stage.c (stage_maprec) swaps the record while the alias runs.

Image: 4U atlas lyt\\quest\\m19\\m19aNN_ID left 128x128 at 2x (nearest). Exit labels: 4U glyphs (digits of the atlas
top row, rects from ui299aNN; camp = 4U cmn_icon cell of pane uiNNN_camp) next to every exit of OUR converted SIS
(map_com m28.arc, target = alias area number). Deviation: 4U's own label / arrow panes (ui299 l_area, suji, l_yaji)
are placed by runtime layout logic not decoded -> labels here sit 13 4U px outside each exit, no arrows.
GUI: the Fortress GUIs (same internal paths -> same file IDs) with: Tex_areaNN highlight overlays (a00) moved onto our
labels, unused ones and the fort HP icon players (AnimP_fort*) moved off-screen, HD_gmk_m26 (Fortress gimmick icons
Tex_k*) blanked. Values from code / data, nothing by eye except the label distance.
"""
import os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, sis, tex

GU_ROMFS = paths.GU_ROMFS
MEM4U = os.path.join(ROOT, 'dump/exefs_v11/mem.bin')       # 4U v1.1, flat from 0x100000
SRC4U = os.path.join(ROOT, 'dump/romfs/eng/data')
GOG_ROMFS = paths.romfs('gogmazios')
MAPCOM = os.path.join(GOG_ROMFS, 'nativeNX/loc/arc/stage/map_com/m28.arc')   # stage4u2gu.py alias output
OUT = os.environ.get('UI_OUT', os.path.join(GOG_ROMFS, 'nativeNX'))
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')
AREAS = ((0, 0), (1, 1), (2, 3))        # alias area -> 4U m19 area (stage4u2gu.py alias: 0 -> 0, 1 -> 1, 3 -> 2)
STAGE4U = 19
MAPTAB4U = 0xeebe0c                     # 0x5a5f40 literal: 0x18-byte entries per 4U stage, +0xc = record array
# keep in sync with module/stage.c MAPREC (checked by main())
MAPREC = {0: (1.8, 17, 11), 1: (2.0, 0, -8), 2: (1.1, 0, -1)}
GLYPH = {1: (128, 0, 8, 16), 2: (136, 0, 12, 16), 3: (148, 0, 12, 16)}   # ui299a00_1 / ui299a01_2 / ui299a00_3 UVs
CAMP = (192, 127, 16, 16)               # ui299a01_camp UV (0.75, 0.248, 0.0625, 0.03125) on 4U cmn_icon 256x512
# big area number baked into the atlas: 4U a03 shows '3', the alias calls the arena area 2 -> 4U a02's big '2'
# (4U area, seed box of the white digit pixels, source atlas area, its seed box); a01's '1' already matches
BIGNUM = {3: (2, (95, 0, 128, 40), (10, 88, 40, 118))}
LABEL_DIST = 13                         # G: 4U px from the exit point outward (label centre)
OFFSCREEN = 4000.0                      # GUI px: right of / above the HUD map
TYPE_TEX, TYPE_GUI = 0x241f5deb, 0x22948394


def u32(d, o): return struct.unpack_from('<I', d, o)[0]


# ---------------------------------------------------------------- 4U data

def rec4u():
    m = open(MEM4U, 'rb').read()
    p = u32(m, MAPTAB4U + 0x18 * STAGE4U + 0xc - 0x100000)
    return {a: struct.unpack_from('<fhh', m, p + 8 * a - 0x100000) for a in range(4)}


def arc4u(name):
    return {p: d for p, _, d in arcpack.read(open(os.path.join(SRC4U, name), 'rb').read())[1]}


def atlas4u(a4):
    return tex.decode(arc4u('m19a%02d_map.arc' % a4)['lyt\\quest\\m19\\m19a%02d_ID' % a4])


def camp_icon():
    t = arc4u('core_common.arc')['eng\\lyt\\common\\texture\\cmn_icon_GSM_NOMIP']
    x, y, w, h = CAMP
    return tex.decode(t)[y:y + h, x:x + w]


def exits(area):
    """our converted SIS (alias numbering): [(x, z, target area)] of section 2 (exits)."""
    for n, t, d in arcpack.read(open(MAPCOM, 'rb').read())[1]:
        if n == 'stage\\m26d\\m26a%02dd\\m26a%02dd-info' % (area, area):
            out = []
            for r in sis.parse(d)['sec'][1]:
                x, y, z = struct.unpack_from('<3f', r, 4)
                out.append((x, z, r[17]))
            return out
    raise SystemExit('no SIS for area %d in %s (run stage4u2gu.py alias first)' % (area, MAPCOM))


# ---------------------------------------------------------------- composition (4U pixels, 128x128 frame)

def glyph_blob(img, seed_box):
    """bounding box of the opaque 8-connected blob holding the white pixels in seed_box (big area digit + outline)."""
    x0, y0, x1, y1 = seed_box
    sub = img[y0:y1, x0:x1]
    ys, xs = np.nonzero((sub[:, :, 3] > 0) & (sub[:, :, :3].min(2) > 200))
    todo = [(y + y0, x + x0) for y, x in zip(ys, xs)]
    seen = set(todo)
    while todo:
        y, x = todo.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q not in seen and 0 <= q[0] < 128 and 0 <= q[1] < 128 and img[q][3] > 0:
                    seen.add(q); todo.append(q)
    yy, xx = zip(*seen)
    assert max(xx) - min(xx) < 24 and max(yy) - min(yy) < 24, 'digit blob touches the map piece'
    return min(xx), min(yy), max(xx) + 1, max(yy) + 1


def compose(area, a4, rec):
    atlas = atlas4u(a4)
    img = atlas[:128, :128].copy()
    if a4 in BIGNUM:                    # the atlas' own area number (4U numbering) -> the alias number's glyph
        src4, box, srcbox = BIGNUM[a4]
        x0, y0, x1, y1 = glyph_blob(img, box)
        img[y0:y1, x0:x1] = 0
        s = atlas4u(src4)[:128, :128]
        sx0, sy0, sx1, sy1 = glyph_blob(s, srcbox)
        cx, cy = (x0 + x1) // 2 - (sx1 - sx0) // 2, (y0 + y1) // 2 - (sy1 - sy0) // 2
        img[cy:cy + sy1 - sy0, cx:cx + sx1 - sx0] = s[sy0:sy1, sx0:sx1]
    alpha = img[:, :, 3] > 0
    ys, xs = np.nonzero(alpha)
    cx, cy = xs.mean(), ys.mean()
    scale, ox, oy = rec
    k = scale * 128 / 20000
    labels = []
    for x, z, dst in exits(area):
        u, v = ox + 64 + x * k, oy + 64 + z * k
        iu, iv = int(round(u)), int(round(v))
        ring = alpha[max(iv - 6, 0):iv + 7, max(iu - 6, 0):iu + 7]
        if ring.size and ring.all():
            continue                    # interior point (a02's under-floor exit (0, -3250, 0)): no label
        d = np.array([u - cx, v - cy]); d /= max(np.linalg.norm(d), 1e-6)
        glyph = camp_icon() if dst == 0 else atlas[GLYPH[dst][1]:GLYPH[dst][1] + 16,
                                                   GLYPH[dst][0]:GLYPH[dst][0] + GLYPH[dst][2]]
        labels.append([u + d[0] * LABEL_DIST, v + d[1] * LABEL_DIST, glyph, dst])
    for _ in range(50):                 # push overlapping labels apart (axis of least overlap)
        moved = False
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                a, b = labels[i], labels[j]
                wx = (a[2].shape[1] + b[2].shape[1]) / 2 + 1 - abs(a[0] - b[0])
                wy = (a[2].shape[0] + b[2].shape[0]) / 2 + 1 - abs(a[1] - b[1])
                if wx > 0 and wy > 0:
                    ax = 0 if wx < wy else 1
                    s = 1 if a[ax] >= b[ax] else -1
                    a[ax] += s * min(wx, wy) / 2; b[ax] -= s * min(wx, wy) / 2
                    moved = True
        if not moved: break
    out = []
    for lx, ly, g, dst in labels:
        h, w = g.shape[:2]
        lx = min(max(lx, w / 2 + 1), 127 - w / 2); ly = min(max(ly, h / 2 + 1), 127 - h / 2)
        x0, y0 = int(round(lx - w / 2)), int(round(ly - h / 2))
        reg = img[y0:y0 + h, x0:x0 + w]
        m = g[:, :, 3:4].astype(np.float32) / 255
        reg[:] = (g * m + reg * (1 - m)).astype(np.uint8)
        reg[:, :, 3] = np.maximum(reg[:, :, 3], g[:, :, 3])
        out.append((x0 + w / 2, y0 + h / 2, dst))
    return img.repeat(2, 0).repeat(2, 1), out


# ---------------------------------------------------------------- GU GUI (0x22948394, header 72 x u32)
# H[12] instances @H[43] (36 B: +0x10 name, +0x18 first param), H[17] objects @H[47] (36 B: +0x14 name, +0x1c first
# param), H[14] params @H[45] (20 B: +4 type, +0xc name, +0x10 value; type 2 = f32 at H[68] + value), strings @H[65].

def gui_items(d):
    H = struct.unpack_from('<72I', d, 0)
    S = H[65]
    name = lambda o: d[S + o:d.index(b'\0', S + o)].decode('latin1')
    items = [(name(u32(d, H[43] + 36 * i + 0x10)), u32(d, H[43] + 36 * i + 0x18)) for i in range(H[12])]
    items += [(name(u32(d, H[47] + 36 * i + 0x14)), u32(d, H[47] + 36 * i + 0x1c)) for i in range(H[17])]
    starts = sorted(set(s for _, s in items)) + [H[14]]
    out = {}
    for n, s in items:
        e = starts[starts.index(s) + 1]
        out[n] = {name(u32(d, H[45] + 20 * i + 0xc)): (i, u32(d, H[45] + 20 * i + 4), u32(d, H[45] + 20 * i + 0x10))
                  for i in range(s, e)}
    return H, out


def gui_set_floats(d, edits):
    """edits {instance: {param: value}} (f32 params): new values appended to the float pool, the params repointed."""
    H, items = gui_items(d)
    vals = [v for ps in edits.values() for v in ps.values()]
    pool = struct.pack('<%df' % len(vals), *vals)
    pool += b'\0' * (-len(pool) % 16)
    end = H[69]                         # float pool ends where the vector pool starts
    d = bytearray(d[:end] + pool + d[end:])
    k = 0
    for inst, ps in edits.items():
        for pn in ps:
            i, t, _ = items[inst][pn]
            assert t == 2, (inst, pn, t)
            struct.pack_into('<I', d, H[45] + 20 * i + 0x10, end - H[68] + 4 * k)
            k += 1
    for j in [2] + list(range(38, 71)):  # file size + section offsets behind the insertion point (vectors, strings)
        if H[j] >= end: struct.pack_into('<I', d, 4 * j, H[j] + len(pool))
    assert u32(d, 8) == len(d)
    return bytes(d)


def gui_set_pos(d, edits):
    """edits {instance: (x, y)}: PosX / PosY (gui_set_floats)."""
    return gui_set_floats(d, {inst: {'PosX': x, 'PosY': y} for inst, (x, y) in edits.items()})


def gui_set_vec(d, edits):
    """edits {instance: {param: 4 floats}} (vector params, type 4): overwritten in place in the vector pool @H[69];
    each edited vector must be used by that one param only."""
    H, items = gui_items(d)
    users = {}
    for ps in items.values():
        for i, t, v in ps.values():
            if t == 4: users[v] = users.get(v, 0) + 1
    d = bytearray(d)
    for inst, ps in edits.items():
        for pn, vec in ps.items():
            i, t, v = items[inst][pn]
            assert t == 4 and users[v] == 1, (inst, pn, t, users.get(v))
            struct.pack_into('<4f', d, H[69] + v, *vec)
    return bytes(d)


def gui_dump(path):
    d = open(path, 'rb').read()
    H, items = gui_items(d)
    for n, ps in items.items():
        pos = ['%s=%g' % (p, struct.unpack_from('<f', d, H[68] + ps[p][2])[0]) for p in ('PosX', 'PosY') if p in ps]
        print('%-14s %s' % (n, ' '.join(pos)))


# ---------------------------------------------------------------- whole map (map_com <lang>, kind 55)
# Transform (C, tools/stage4u2gu.py "whole-map area offsets"): GU icon = (x + off) * 256 * k / 60000 HD px from the
# texture centre (0x61bde8, dims[26] 0x5058d0), 4U u = (x + off + 20000) / 40000 * 128 px of m19d_ID (0xb832ac, W from
# 0x6596dc). Offsets = 4U's (m28.arc, stage4u2gu.py alias) and k = 60000 / 40000 (module/stage.c stage_wholerec) ->
# GU icon = 2 * (u - 64): texture = m19d_ID at 2x, no fit. GUI map26dn: the Fortress area highlights area01 / area02
# take 4U's ui269_area01 / ui269_area03 panes (alias areas 1 / 2), the fort HP icon players go off-screen.
WMAP_W4U, WMAP_WGU = 40000, 60000       # 4U 0x6596dc (W passed to 0x6c2ac8), GU dims[26] (0x5058d0)
WMAP_K = WMAP_WGU / WMAP_W4U            # keep in sync with module/stage.c WHOLEREC_K
WMAP_PANES = {1: 1, 2: 3}               # alias area -> 4U ui269_areaNN (GU GUI instance areaNN = alias area)
# area labels baked into m19d_ID (4U numbering), as on the area maps: the arena's '3' -> the '2' glyph, the '2' of 4U a02
# (area dropped by the alias, its piece stays as a passage) erased. Seed boxes of the white digit pixels (4U px).
WMAP_DIGIT3, WMAP_DIGIT2 = (44, 8, 60, 26), (44, 100, 62, 122)


def ui269_panes():
    """4U whole-map highlight panes ui269_areaNN -> {N: (u, v, w, h)} in px of the 128x128 picture. Pane record (lyt
    0x15302ef4, 0x6c B): +4 name offset, +0xc f32 pos x, y, +0x18 f32 size w, h, +0x20 f32 scale x, y (C, values).
    Frame (G): pos = minus the picture pixel; checked: (75, 70) / (35, 110) / (33, 25) sit on the 4U SIS points of
    a01 / a02 / a03 mapped by the 0xb832ac transform."""
    d = arc4u('m19_map.arc')['eng\\lyt\\quest\\m19\\ui269']
    out = {}
    for n in (1, 2, 3):
        no = d.index(b'ui269_area%02d\0' % n)
        r = next(o for o in range(0, no, 4) if u32(d, o + 4) == no and u32(d, o + 8) == 0x6c)
        x, y = struct.unpack_from('<2f', d, r + 0xc)
        w, h, sx, sy = struct.unpack_from('<4f', d, r + 0x18)
        out[n] = (-x, -y, w * sx, h * sy)
    return out


def wholemap_image():
    img = tex.decode(arc4u('m19_map.arc')['lyt\\quest\\m19\\m19d_ID']).copy()
    x0, y0, x1, y1 = glyph_blob(img, WMAP_DIGIT2)
    two = img[y0:y1, x0:x1].copy()
    img[y0:y1, x0:x1] = 0
    x0, y0, x1, y1 = glyph_blob(img, WMAP_DIGIT3)
    img[y0:y1, x0:x1] = 0
    h, w = two.shape[:2]
    cx, cy = (x0 + x1) // 2 - w // 2, (y0 + y1) // 2 - h // 2
    m = two[:, :, 3] > 0
    img[cy:cy + h, cx:cx + w][m] = two[m]
    return img


def bc1_punch(img):
    """(h, w, 4) uint8 with binary alpha -> BC1 blocks (n, 8): tex.bc1_encode (4-colour) where opaque, 3-colour blocks
    (c0 <= c1) with index 3 = transparent where any pixel is (tex.bc1_encode has no punch-through mode)."""
    b = tex.to_blocks(img)
    n = len(b)
    tr = b[..., 3].reshape(n, 16) < 128
    fill = b.reshape(n, 16, 4).copy()
    for i in np.nonzero(tr.any(1) & ~tr.all(1))[0]:     # endpoints from the opaque pixels only
        fill[i, tr[i]] = fill[i, ~tr[i]][0]
    out = tex.bc1_encode(fill.reshape(n, 4, 4, 4))
    for i in np.nonzero(tr.any(1))[0]:
        lo, hi = sorted(struct.unpack('<HH', out[i, :4].tobytes()))
        p0, p1 = tex._unpack565(np.array([lo, hi]))
        pal = np.stack([p0, p1, (p0 + p1) // 2])
        idx = ((fill[i, :, None, :3].astype(np.int32) - pal[None]) ** 2).sum(-1).argmin(1)
        idx[tr[i]] = 3
        out[i] = list(struct.pack('<HHI', lo, hi, sum(int(k) << (2 * j) for j, k in enumerate(idx))))
    return out


def encode_bc1_punch(img, like):
    """GU TEX (1 mip, BC1) of img with the header fields of `like` (the Fortress texture it replaces)."""
    hd = tex.parse(like)
    H, W = img.shape[:2]
    (w, h, bpp, bh, off, size), = tex.gu_layout(W, H, 1, 'bc1')
    data = tex.swizzle(bc1_punch(img).reshape(h, w, bpp), bpp, bh)
    out = tex.gu_header(W, H, 1, tex.GU_FMT['bc1'], [off], len(data), unk1=hd['unk1']) + data
    assert len(out) == len(like) and (hd['width'], hd['height'], hd['fmt'], hd['mips']) == (W, H, 0x13, 1)
    dec = tex.decode(out)
    assert ((dec[:, :, 3] > 0) == (img[:, :, 3] > 0)).all(), 'BC1 alpha differs'
    return out


def wholemap_check(img2x):
    """our converted SIS points (m28.arc, alias areas) through the GU transform with the m28.arc offsets and k:
    -> [(u, v, area, on art)] in px of the 2x texture."""
    offs, out = None, []
    for n, t, d in arcpack.read(open(MAPCOM, 'rb').read())[1]:
        if t == 0x6ff78212 and n == 'stage\\m26d\\m26d':
            offs = [struct.unpack_from('<2i', d, 8 + 20 * a) for a in range(3)]
    for area in range(3):
        for x, z, _ in exits(area):
            u = 128 + (x + offs[area][0]) * 256 * WMAP_K / WMAP_WGU
            v = 128 + (z + offs[area][1]) * 256 * WMAP_K / WMAP_WGU
            iu, iv = int(u), int(v)
            on = 0 <= iu < 256 and 0 <= iv < 256 and img2x[max(iv - 3, 0):iv + 4, max(iu - 3, 0):iu + 4, 3].any()
            out.append((u, v, area, bool(on)))
    return out


def wholemap(preview=None):
    from romfs import RomFS
    rf = RomFS(GU_ROMFS)
    img = wholemap_image().repeat(2, 0).repeat(2, 1)
    pts = wholemap_check(img)
    print('whole map: SIS exits on the art %d / %d %s' % (
        sum(p[3] for p in pts), len(pts), [(round(u), round(v), a) for u, v, a, on in pts if not on]))
    assert all(p[3] for p in pts), 'SIS exit off the 4U whole-map art: offsets / k wrong'
    panes = ui269_panes()
    fl = {'AnimP_fort1': {'PosX': OFFSCREEN, 'PosY': -OFFSCREEN}, 'AnimP_fort2': {'PosX': OFFSCREEN, 'PosY': -OFFSCREEN}}
    vec = {}
    for area, n4 in WMAP_PANES.items():        # GUI px from the texture centre = 2 * (4U px - 64), size 2x, no rotation
        u, v, w, h = panes[n4]
        fl['area%02d' % area] = {'PosX': 2 * (u - 64), 'PosY': 2 * (v - 64), 'Rotation': 0.0}
        vec['area%02d' % area] = {'Size': (2 * w, 2 * h, 0.0, 0.0)}
    print('whole map: highlights', {k: (round(e['PosX'], 1), round(e['PosY'], 1), vec[k]['Size'][:2])
                                    for k, e in fl.items() if k in vec})
    if preview:
        from PIL import Image, ImageDraw
        im = Image.new('RGBA', (512, 512), (40, 40, 90, 255))
        im.alpha_composite(Image.fromarray(img).resize((512, 512), Image.NEAREST))
        dr = ImageDraw.Draw(im)
        for u, v, a, on in pts:
            dr.ellipse((2 * u - 3, 2 * v - 3, 2 * u + 3, 2 * v + 3), outline='red', width=2)
        for k, e in vec.items():
            x, y, (w, h) = 2 * (128 + fl[k]['PosX']), 2 * (128 + fl[k]['PosY']), e['Size'][:2]
            dr.ellipse((x - w, y - h, x + w, y + h), outline='yellow', width=1)
        im.save(os.path.join(preview, 'm28_wholemap.png'))
    tex_img = None
    for lang in LANGS:
        _, ents = arcpack.read(rf.read('/nativeNX/%s/arc/stage/map_com/m26_%s.arc' % (lang, lang)))
        out = []
        for p, t, d in ents:
            base = p.split('\\')[-1]
            if base == 'HD_map_26dn_BM_NOMIP':
                tex_img = tex_img or encode_bc1_punch(img, d)
                assert len(tex_img) == len(d); d = tex_img
            elif base == 'map26dn' and t == TYPE_GUI:
                d = gui_set_vec(gui_set_floats(d, fl), vec)
            out.append((p, t, d))
        dst_path = os.path.join(OUT, lang, 'arc/stage/map_com/m28_%s.arc' % lang)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        open(dst_path, 'wb').write(arcpack.build(out))
    print('wrote', os.path.join(OUT, '<lang>/arc/stage/map_com/m28_<lang>.arc'), 'for', ' '.join(LANGS))


# ---------------------------------------------------------------- build

def blank_like(t):
    h = tex.parse(t)
    img = np.zeros((h['height'], h['width'], 4), np.uint8)
    out = tex.encode_gu(img, tex.FMT_GU[h['fmt']], mips=h['mips'])
    assert len(out) == len(t)
    return out


def main(preview=None):
    r4 = rec4u()
    for alias, a4 in AREAS:
        got = (round(r4[a4][0], 4), r4[a4][1], r4[a4][2])
        assert got == MAPREC[alias], ('4U record differs from MAPREC / stage.c', alias, got)
    from romfs import RomFS
    rf = RomFS(GU_ROMFS)
    for alias, a4 in AREAS:
        img, labels = compose(alias, a4, MAPREC[alias])
        print('area %d (4U a%02d): record scale %g off %s, labels %s' % (
            alias, a4, MAPREC[alias][0], MAPREC[alias][1:], [(round(x, 1), round(y, 1), t) for x, y, t in labels]))
        tex_img = tex.encode_gu(img, 'bc3', mips=1)
        # GUI px from the texture centre (0x61cacc frame): 2 * (4U px - 64)
        lab = {t: (2 * (x - 64), 2 * (y - 64)) for x, y, t in labels}
        edits = {'AnimP_fort1': (OFFSCREEN, -OFFSCREEN), 'AnimP_fort2': (OFFSCREEN, -OFFSCREEN)}
        if preview:
            from PIL import Image
            Image.fromarray(img).save(os.path.join(preview, 'm28a%02d_map.png' % alias))
        for lang in LANGS:
            src = '/nativeNX/%s/arc/stage/mapUI/m26d/a%02d_ui_%s.arc' % (lang, alias, lang)
            _, ents = arcpack.read(rf.read(src))
            out = []
            for p, t, d in ents:
                base = p.split('\\')[-1]
                if base == 'HD_m26a%02ddn_BM_NOMIP' % alias:
                    assert len(d) == len(tex_img); d = tex_img
                elif base == 'HD_gmk_m26_BM_NOMIP':
                    d = blank_like(d)
                elif base == 'm26a%02ddn' % alias and t == TYPE_GUI:
                    _, items = gui_items(d)
                    e = dict(edits)
                    for inst in items:
                        if inst.startswith('Tex_area') and inst != 'Tex_area':   # a00 exit highlights: Tex_areaNN[a]
                            dst = int(inst[8:10])
                            e[inst] = lab[dst] if (dst in lab and not inst.endswith('a')) else (OFFSCREEN, -OFFSCREEN)
                    d = gui_set_pos(d, {k: v for k, v in e.items() if k in items})
                out.append((p, t, d))
            dst_path = os.path.join(OUT, lang, 'arc/stage/mapUI/m28d/a%02d_ui_%s.arc' % (alias, lang))
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            open(dst_path, 'wb').write(arcpack.build(out))
    print('wrote', os.path.join(OUT, '<lang>/arc/stage/mapUI/m28d/a0N_ui_<lang>.arc'), 'for', ' '.join(LANGS))
    wholemap(preview)


if __name__ == '__main__':
    if sys.argv[1:2] == ['gui']:
        gui_dump(sys.argv[2])
    elif sys.argv[1:2] == ['preview']:
        main(os.environ['UI_PREVIEW'])
    else:
        main()
