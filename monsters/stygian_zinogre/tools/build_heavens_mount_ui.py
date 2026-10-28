"""build_heavens_mount_ui.py : the in-quest maps of Heaven's Mount (4U m05) on the Ruined Pinnacle alias (stage 24 ->
folder m30), after build_heavens_mount.py (it reads our map_com m30.arc).

  build_heavens_mount_ui.py [--out DIR] [--preview DIR]
      write DIR/nativeNX/<lang>/arc/stage/mapUI/m30d/aNN_ui_<lang>.arc (area maps 0..9, kind 49) and
      DIR/nativeNX/<lang>/arc/stage/map_com/m30_<lang>.arc (whole map, kind 55) for eng fre ger ita spa
      (default DIR = monsters/stygian_zinogre/romfs); --preview: the composed pictures as PNG

Same route as Speartip Crag / Battlequarters (tools/mapui4u2gu.py helpers; transforms in module/stage_alias.c):
  area maps: 4U lyt\\quest\\m05\\m05aNN_ID, left 128 x 128 (pane ui285aNN_map1 UV (0, 0)-(0.5, 1)); exit labels from
    OUR area info (= 4U m05's): the 4U digit glyph of the target area (atlas rect of pane ui285aNN_<target>[_n]) or the
    camp icon (4U cmn_icon cell, mapui4u2gu.camp_icon) 13 4U px outside each exit (G, as Battlequarters / Speartip:
    4U places its label panes at run time; no arrows).
    - areas 0..3: the GU record takes the 4U record (package.toml [stage] maprec, checked here against 4U's table
      0xeebe0c + 0x18 * 5), picture at 2x into HD_m24aNNdn (BC3 256 x 256): GU px = 2 * (4U px - 64).
    - areas 4..8: the core's maprec holds 4 areas (module/port.h map_k[4], stage_alias.c s_maprec[4], build.py
      asserts <= 4), so these keep GU's own m24 records (table 0x1774dec[24 * 14 + area]) and the 4U picture is
      resampled to them (nearest): GU texture px p -> world (p - 128 - 2 * off) / (k * 128 / 10000) -> 4U px. Scale
      vs 2x: a04 0.78, a05 0.94, a06 1.23 (a 4U picture edge may leave the 256 frame), a07 0.78, a08 0.75 (G: the
      look; icons land right by construction).
    GUI m24aNNdn: the Ruined Pinnacle's exit highlights (Tex_areaNN) and animated players (Anim_area*) off-screen
    (no 4U counterpart placed: a DEVIATION, the 4U picture carries the labels).
  area 9 (no 4U area): GU's a09_ui_<lang>.arc unchanged.
  whole map: 4U m05d_ID 128 x 128 (pane ui255_map UV (0, 0)-(1, 1)), 4U icon transform (0xb832ac: u = (x + off +
    W / 2) / W * 128, W 60000) = GU's with k = dims[24] / W = 60000 / 60000 = 1.0 (package.toml wholemap_k); checked:
    every SIS point of the 9 areas lands on the art. 2x into HD_map_24dn (BC3). GUI map24dn: highlights area01..08 =
    4U ui255_area01..08 (pos read as minus the frame pixel, size 44 * scale * 2, Speartip's rule, G), area09 off-screen.
"""
import argparse, os, re, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths                                         # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack, sis, tex, tomllib                    # noqa: E402
import mapui4u2gu as mu                              # noqa: E402

GUX = os.path.join(ROOT, 'dump', 'gu_stage', 'nativeNX')
LANGS = mu.LANGS
STAGE4U, G, FOLDER, N4, NGU = 5, 'm24', 30, 9, 10
STAGE = 24
MAPREC_CORE = 4                          # areas the core's maprec covers (module/port.h)
GU_MAPTAB = 0x1774dec                    # GU per-area map records: 14 pointers per stage (stage_alias.c)
WMAP_W4U, WMAP_WGU = 60000, 60000        # 4U m05 W (build_heavens_mount.py AMAP05_WMAP), GU dims[24] (0x5058d0 +0xc0)
LABEL_DIST = mu.LABEL_DIST
OFFSCREEN = mu.OFFSCREEN
T_GUI = mu.TYPE_GUI


def mem4u():
    return open(mu.MEM4U, 'rb').read()


def rec4u():
    m = mem4u()
    p = struct.unpack_from('<I', m, mu.MAPTAB4U + 0x18 * STAGE4U + 0xc - 0x100000)[0]
    return {a: struct.unpack_from('<fhh', m, p + 8 * a - 0x100000) for a in range(N4)}


def recgu():
    m = open(paths.GU_MAIN, 'rb').read()
    out = {}
    for a in range(NGU):
        p = struct.unpack_from('<I', m, GU_MAPTAB + 4 * (14 * STAGE + a))[0]
        out[a] = (struct.unpack_from('<f', m, p + 0x2c)[0],) + struct.unpack_from('<2h', m, p + 0x30)
    return out


def arc4u(name):
    return {p: d for p, _, d in arcpack.read(open(os.path.join(mu.SRC4U, name), 'rb').read())[1]}


def pane4u(lyt, name):
    """4U lyt pane record (0x6c B): +0xc pos x, y, +0x18 size w, h, +0x20 scale x, y, +0x28 UV u, v, du, dv"""
    no = lyt.index(name.encode() + b'\0')
    r = next(o for o in range(0, no, 4) if struct.unpack_from('<I', lyt, o + 4)[0] == no and
             struct.unpack_from('<I', lyt, o + 8)[0] == 0x6c)
    return struct.unpack_from('<2f', lyt, r + 0xc), struct.unpack_from('<4f', lyt, r + 0x18), \
        struct.unpack_from('<4f', lyt, r + 0x28)


def mapcom():
    return {(p, t): d for p, t, d in arcpack.read(open(os.path.join(paths.romfs('stygian_zinogre'), 'nativeNX', 'loc',
                                                                    'arc', 'stage', 'map_com', 'm%02d.arc' % FOLDER),
                                                       'rb').read())[1]}


def sis_points(area, mc):
    """our area info (4U m05's): {section: [(x, z, area byte, y)]}"""
    s = sis.parse(mc[('stage\\%sd\\%sa%02dd\\%sa%02dd-info' % (G, G, area, G, area), 0x065375d5)])
    out = {}
    for k, name in ((0, 'points'), (1, 'exits'), (2, 'arrivals')):
        out[name] = [struct.unpack_from('<f', r, 4) + struct.unpack_from('<f', r, 12) + (r[17],) +
                     struct.unpack_from('<f', r, 8) for r in s['sec'][k]]
    return out


def gu_arc(rel):
    p = os.path.join(GUX, rel)
    if not os.path.exists(p):
        from romfs import RomFS
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(RomFS(paths.GU_ROMFS).read('/nativeNX/' + rel))
    return open(p, 'rb').read()


def glyph(area, target, atlas, lyt):
    """the 4U label of an exit to `target`: its digit (pane ui285aNN_<target>[_n] rect on the 256 x 128 atlas), the
    camp icon for 0"""
    if target == 0:
        return mu.camp_icon()
    names = sorted(set(re.findall(rb'(ui285a%02d_%d(?:_\d)?)\0' % (area, target), lyt)))
    if not names:
        return None
    (_, _), (_, _, _, _), (u, v, du, dv) = pane4u(lyt, names[0].decode())
    x0, y0, w, h = int(round(u * 256)), int(round(abs(v) * 128)), int(round(du * 256)), int(round(dv * 128))
    return atlas[y0:y0 + h, x0:x0 + w]


def compose_area(area, rec, mc, log):
    """4U area picture (128 px) with the exit labels"""
    f = arc4u('m05a%02d_map.arc' % area)
    atlas = tex.decode(f['lyt\\quest\\m05\\m05a%02d_ID' % area])
    lyt = f['eng\\lyt\\quest\\m05\\ui285a%02d' % area]
    img = atlas[:128, :128].copy()
    ys, xs = np.nonzero(img[:, :, 3] > 0)
    cx, cy = xs.mean(), ys.mean()
    k = rec[0] * 128 / 20000
    placed = []
    for x, z, dst, y in sis_points(area, mc)['exits']:
        g = glyph(area, dst, atlas, lyt)
        if g is None:
            log.append('a%02d: no 4U label for the exit to %d' % (area, dst)); continue
        u, v = rec[1] + 64 + x * k, rec[2] + 64 + z * k
        d = np.array([u - cx, v - cy]); d /= max(np.linalg.norm(d), 1e-6)
        h, w = g.shape[:2]
        lx = min(max(u + d[0] * LABEL_DIST, w / 2 + 1), 127 - w / 2)
        ly = min(max(v + d[1] * LABEL_DIST, h / 2 + 1), 127 - h / 2)
        x0, y0 = int(round(lx - w / 2)), int(round(ly - h / 2))
        reg = img[y0:y0 + h, x0:x0 + w]
        m = g[:, :, 3:4].astype(np.float32) / 255
        reg[:] = (g * m + reg * (1 - m)).astype(np.uint8)
        reg[:, :, 3] = np.maximum(reg[:, :, 3], g[:, :, 3])
        placed.append((round(x0 + w / 2, 1), round(y0 + h / 2, 1), dst))
    return img, placed


def to_gu(img, rec4, recg):
    """the 128-px 4U picture resampled onto the GU 256-px texture of GU record recg (nearest)"""
    kg = recg[0] * 128 / 10000
    k4 = rec4[0] * 128 / 20000
    p = np.arange(256) + 0.5
    wx = (p - 128 - 2 * recg[1]) / kg
    wz = (p - 128 - 2 * recg[2]) / kg
    u = np.floor(rec4[1] + 64 + wx * k4).astype(int)
    v = np.floor(rec4[2] + 64 + wz * k4).astype(int)
    out = np.zeros((256, 256, 4), np.uint8)
    okx, oky = (u >= 0) & (u < 128), (v >= 0) & (v < 128)
    out[np.ix_(oky, okx)] = img[np.ix_(v[oky], u[okx])]
    return out, k4 / (kg / 2)


def wholemap_check(img, mc):
    d = mc[('stage\\%sd\\%sd' % (G, G), 0x6ff78212)]
    offs = [struct.unpack_from('<2i', d, 8 + 20 * a) for a in range(N4)]
    pts = []
    for area in range(N4):
        for sec, lst in sis_points(area, mc).items():
            for x, z, _, y in lst:
                u = (x + offs[area][0] + WMAP_W4U / 2) / WMAP_W4U * 128
                v = (z + offs[area][1] + WMAP_W4U / 2) / WMAP_W4U * 128
                iu, iv = int(u), int(v)
                on = 0 <= iu < 128 and 0 <= iv < 128 and img[max(iv - 2, 0):iv + 3, max(iu - 2, 0):iu + 3, 3].any()
                pts.append((round(u, 1), round(v, 1), area, sec, bool(on)))
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=paths.romfs('stygian_zinogre'))
    ap.add_argument('--preview')
    a = ap.parse_args()
    st = tomllib.load(open(os.path.join(MON, 'package.toml'), 'rb'))['stage']
    r4, rg = rec4u(), recgu()
    assert len(st['maprec']) == MAPREC_CORE
    for area in range(MAPREC_CORE):
        got = (round(r4[area][0], 4), r4[area][1], r4[area][2])
        assert got == tuple(st['maprec'][area]), ('4U record differs from package.toml maprec', area, got)
    assert abs(st['wholemap_k'] - WMAP_WGU / WMAP_W4U) < 1e-6, st['wholemap_k']
    mc = mapcom()
    log = []
    # --- area maps
    for area in range(NGU):
        if area >= N4:
            for lang in LANGS:
                rel = '%s/arc/stage/mapUI/%sd/a%02d_ui_%s.arc' % (lang, G, area, lang)
                dst = os.path.join(a.out, 'nativeNX', lang, 'arc', 'stage', 'mapUI', 'm%02dd' % FOLDER,
                                   'a%02d_ui_%s.arc' % (area, lang))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(gu_arc(rel))
            print('area %d: GU a%02d_ui unchanged (no 4U area)' % (area, area))
            continue
        pic, labels = compose_area(area, r4[area], mc, log)
        if area < MAPREC_CORE:
            img, how = pic.repeat(2, 0).repeat(2, 1), '4U record %s, 2x' % (r4[area],)
        else:
            img, sc = to_gu(pic, r4[area], rg[area])
            how = 'GU record %s, 4U picture resampled (x%.2f of 2x)' % (tuple(round(v, 3) for v in rg[area]), 1 / sc)
        print('area %d: %s, labels %s' % (area, how, labels))
        if a.preview:
            from PIL import Image
            Image.fromarray(img).save(os.path.join(a.preview, 'm%02da%02d_map.png' % (FOLDER, area)))
        tex_img = tex.encode_gu(img, 'bc3', mips=1)
        for lang in LANGS:
            ents = arcpack.read(gu_arc('%s/arc/stage/mapUI/%sd/a%02d_ui_%s.arc' % (lang, G, area, lang)))[1]
            out = []
            for p, t, d in ents:
                base = p.split('\\')[-1]
                if base == 'HD_%sa%02ddn_BM_NOMIP' % (G, area):
                    assert len(d) == len(tex_img); d = tex_img
                elif base == '%sa%02ddn' % (G, area) and t == T_GUI:
                    _, items = mu.gui_items(d)
                    e = {k: (OFFSCREEN, -OFFSCREEN) for k in items
                         if (k.startswith(('Tex_area', 'AnimP_', 'Anim_area')) and 'PosX' in items[k])}
                    if e: d = mu.gui_set_pos(d, e)
                out.append((p, t, d))
            dst = os.path.join(a.out, 'nativeNX', lang, 'arc', 'stage', 'mapUI', 'm%02dd' % FOLDER,
                               'a%02d_ui_%s.arc' % (area, lang))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(arcpack.build(out))
    for line in log: print('  ', line)
    # --- whole map
    f = arc4u('m05_map.arc')
    src = tex.decode(f['lyt\\quest\\m05\\m05d_ID'])
    lyt = f['eng\\lyt\\quest\\m05\\ui255']
    (_, _), (_, _, _, _), uv = pane4u(lyt, 'ui255_map')
    assert uv == (0.0, 0.0, 1.0, 1.0) and src.shape[:2] == (128, 128), (uv, src.shape)
    img = src.copy()
    pts = wholemap_check(img, mc)
    print('whole map: SIS points on the art %d / %d %s' % (sum(p[4] for p in pts), len(pts),
                                                           [p for p in pts if not p[4]]))
    # 4U m05's section-0 points include far-off ones (a6 (-124, 40): outside the 128 frame) and one a06 exit sits
    # next to the art's edge; every arrival must land and >= 90 % overall, else the offsets are wrong
    assert all(p[4] for p in pts if p[3] == 'arrivals') and sum(p[4] for p in pts) >= 0.9 * len(pts), \
        'SIS points off the 4U whole-map art: offsets wrong'
    hl, size = {}, {}
    for area in range(1, N4):
        (px, py), (w, h, sx, sy), _ = pane4u(lyt, 'ui255_area%02d' % area)
        hl['area%02d' % area] = {'PosX': 2 * (-px - 64), 'PosY': 2 * (-py - 64)}
        size['area%02d' % area] = {'Size': (2 * w * sx, 2 * h * sy, 0.0, 0.0)}
    hl['area%02d' % N4] = {'PosX': OFFSCREEN, 'PosY': -OFFSCREEN}
    print('whole map highlights', {k: (round(v['PosX']), round(v['PosY'])) for k, v in hl.items()})
    img2 = img.repeat(2, 0).repeat(2, 1)
    if a.preview:
        from PIL import Image, ImageDraw
        im = Image.new('RGBA', (512, 512), (40, 40, 90, 255))
        im.alpha_composite(Image.fromarray(img2).resize((512, 512), Image.NEAREST))
        dr = ImageDraw.Draw(im)
        for u, v, ar, sec, on in pts:
            dr.ellipse((4 * u - 3, 4 * v - 3, 4 * u + 3, 4 * v + 3), outline='red', width=2)
        im.save(os.path.join(a.preview, 'm%02d_wholemap.png' % FOLDER))
    tex_img = None
    for lang in LANGS:
        ents = arcpack.read(gu_arc('%s/arc/stage/map_com/%s_%s.arc' % (lang, G, lang)))[1]
        out = []
        for p, t, d in ents:
            base = p.split('\\')[-1]
            if base == 'HD_map_%sdn_BM_NOMIP' % G[1:]:
                tex_img = tex_img or tex.encode_gu(img2, 'bc3', mips=1)
                assert len(tex_img) == len(d); d = tex_img
            elif base == 'map%sdn' % G[1:] and t == T_GUI:
                d = mu.gui_set_vec(mu.gui_set_floats(d, hl), size)
            out.append((p, t, d))
        dst = os.path.join(a.out, 'nativeNX', lang, 'arc', 'stage', 'map_com', 'm%02d_%s.arc' % (FOLDER, lang))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(arcpack.build(out))
    print('wrote <lang>/arc/stage/mapUI/m%02dd/aNN_ui_<lang>.arc and map_com/m%02d_<lang>.arc for %s' % (
        FOLDER, FOLDER, ' '.join(LANGS)))


if __name__ == '__main__':
    main()
