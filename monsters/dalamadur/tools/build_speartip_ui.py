"""build_speartip_ui.py : the in-quest maps of Speartip Crag (4U m08) on the Sanctuary alias (stage 18 -> folder m29).

  build_speartip_ui.py [--out DIR] [--preview DIR]
      write DIR/nativeNX/<lang>/arc/stage/mapUI/m29d/a0N_ui_<lang>.arc (area maps, kind 49) and
      DIR/nativeNX/<lang>/arc/stage/map_com/m29_<lang>.arc (whole map, kind 55) for eng fre ger ita spa
      (default DIR = monsters/dalamadur/romfs); --preview: the composed pictures as PNG

Same route as Battlequarters (tools/mapui4u2gu.py, whose GUI / texture helpers this uses; transforms in
module/stage_alias.c): the GU map record of an area holds the 4U record (package.toml [stage] maprec, checked here
against 4U's table) and the GU picture is the 4U one at 2x, so GU map px = 2 * (4U px - 64) from the texture centre.
  area maps: 4U lyt\\quest\\m08\\m08a0N_ID, left 128x128 (pane map1 UV (0,0)-(0.5,1)) at 2x into HD_m18a0Ndn (BC3,
    256x256); exit labels from OUR area info (build_speartip.py m29.arc, 4U m08's): the camp's exit to area 1 gets
    the atlas '1' (rect of pane ui288a00_1) 13 4U px outside it (G, as Battlequarters: 4U places its label panes at
    run time); the arena's only exit is the under-floor fall volume (interior: no label; its big '1' is baked in).
    GUI m18a00dn: the exit highlight Tex_area01 onto the '1'. m18a01dn: the Sanctuary's breakable icons (AnimP_k01..03,
    HD_gmk_m18) off-screen / blank: 4U draws its own breakables (ui288a01 koware01..03, atlas right half) as overlays
    that go with the breaks (goal D: pane UVs in notes/speartip-crag.md section 7).
  whole map: 4U m08d_ID, pane ui258_map shows its top-left 58x64 px, centred in the 128 px frame of the 4U icon
    transform (0xb832ac: u = (x + off + W / 2) / W * 128, W 30000; checked: every SIS point of both areas lands on
    the art); 2x into HD_map_18dn (BC3). GUI map18dn: the arena highlight area01 = 4U ui258_area01 (pos read as minus
    the frame pixel, as ui269 for m19: G), size 44 * scale * 2. The area offsets are build_speartip.py's (m29.arc).
"""
import argparse, os, struct, sys
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
STAGE4U, G, FOLDER = 8, 'm18', 29
MAPTAB4U = mu.MAPTAB4U
GLYPH1 = (128, 0, 8, 16)                 # ui288a00_1 UV (0.5, 0, 0.031, 0.125) on the 256x128 atlas
LABEL_DIST = mu.LABEL_DIST
OFFSCREEN = mu.OFFSCREEN
WMAP_W4U, WMAP_WGU = 30000, 40000        # 4U aMap08 W (build_speartip.py AMAP08_WMAP), GU dims[18] (0x5058d0)
WMAP_PANE = (0, 0, 58, 64)               # ui258_map UV (0, 0, 0.453, 0.5) on m08d_ID 128x128
T_GUI = mu.TYPE_GUI


def mem4u():
    return open(mu.MEM4U, 'rb').read()


def rec4u():
    m = mem4u()
    p = struct.unpack_from('<I', m, MAPTAB4U + 0x18 * STAGE4U + 0xc - 0x100000)[0]
    return {a: struct.unpack_from('<fhh', m, p + 8 * a - 0x100000) for a in range(2)}


def arc4u(name):
    return {p: d for p, _, d in arcpack.read(open(os.path.join(mu.SRC4U, name), 'rb').read())[1]}


def pane4u(arc, lyt, name):
    """4U lyt pane record (0x6c B): +0xc pos x, y, +0x18 size w, h, +0x20 scale x, y, +0x28 UV u, v, du, dv"""
    d = arc4u(arc)[lyt]
    no = d.index(name.encode() + b'\0')
    r = next(o for o in range(0, no, 4) if struct.unpack_from('<I', d, o + 4)[0] == no and
             struct.unpack_from('<I', d, o + 8)[0] == 0x6c)
    return struct.unpack_from('<2f', d, r + 0xc), struct.unpack_from('<4f', d, r + 0x18), \
        struct.unpack_from('<4f', d, r + 0x28)


def mapcom():
    """our map_com m29.arc {(path, type): bytes} (item pops and whole-map offsets share stage\\m18d\\m18d)"""
    return {(p, t): d for p, t, d in arcpack.read(open(os.path.join(paths.romfs('dalamadur'), 'nativeNX', 'loc', 'arc',
                                                                    'stage', 'map_com', 'm%02d.arc' % FOLDER),
                                                       'rb').read())[1]}


PASSAGE_Y = -1000.0                      # exits below are fall volumes (the arena's (0, -3350, 0) r 10000), no passage


def sis_points(area, mc):
    """our area info (4U m08's): {section: [(x, z, area byte, y)]} for points / exits / arrivals"""
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
    return arcpack.read(open(p, 'rb').read())[1]


def compose_area(area, rec, mc):
    """4U area picture (128 px) with the exit labels -> (2x RGBA, [(label u, v, target)])"""
    atlas = tex.decode(arc4u('m08a%02d_map.arc' % area)['lyt\\quest\\m08\\m08a%02d_ID' % area])
    img = atlas[:128, :128].copy()
    alpha = img[:, :, 3] > 0
    ys, xs = np.nonzero(alpha)
    cx, cy = xs.mean(), ys.mean()
    k = rec[0] * 128 / 20000
    labels = []
    for x, z, dst, y in sis_points(area, mc)['exits']:
        if y < PASSAGE_Y: continue       # the arena's under-floor fall volume back to camp: no passage, no label
        u, v = rec[1] + 64 + x * k, rec[2] + 64 + z * k
        assert dst == 1, ('Speartip passages lead to area 1 (the camp exit)', area, dst)
        d = np.array([u - cx, v - cy]); d /= max(np.linalg.norm(d), 1e-6)
        x0, y0, w, h = GLYPH1
        labels.append((u + d[0] * LABEL_DIST, v + d[1] * LABEL_DIST, atlas[y0:y0 + h, x0:x0 + w], dst))
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


def wholemap_image():
    """4U m08d_ID's pane picture centred in the 128 px frame"""
    src = tex.decode(arc4u('m08_map.arc')['lyt\\quest\\m08\\m08d_ID'])
    x0, y0, w, h = WMAP_PANE
    img = np.zeros((128, 128, 4), np.uint8)
    ox, oy = (128 - w) // 2, (128 - h) // 2
    img[oy:oy + h, ox:ox + w] = src[y0:y0 + h, x0:x0 + w]
    return img, (ox, oy)


def wholemap_check(img, mc):
    """every SIS point of both areas through the 4U whole-map transform (our m29.arc offsets) -> on the art?"""
    d = mc[('stage\\%sd\\%sd' % (G, G), 0x6ff78212)]
    offs = [struct.unpack_from('<2i', d, 8 + 20 * a) for a in range(2)]
    assert offs == [(6800, 5300), (0, -2800)], ('m29.arc whole-map offsets are not 4U m08\'s', offs)
    pts = []
    for area in range(2):
        for sec, lst in sis_points(area, mc).items():
            for x, z, _, y in lst:
                u = (x + offs[area][0] + WMAP_W4U / 2) / WMAP_W4U * 128
                v = (z + offs[area][1] + WMAP_W4U / 2) / WMAP_W4U * 128
                if sec == 'exits' and y < PASSAGE_Y: continue    # the under-floor fall volume
                iu, iv = int(u), int(v)
                on = 0 <= iu < 128 and 0 <= iv < 128 and img[max(iv - 2, 0):iv + 3, max(iu - 2, 0):iu + 3, 3].any()
                pts.append((round(u, 1), round(v, 1), area, sec, bool(on)))
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=paths.romfs('dalamadur'))
    ap.add_argument('--preview')
    a = ap.parse_args()
    st = tomllib.load(open(os.path.join(MON, 'package.toml'), 'rb'))['stage']
    r4 = rec4u()
    for area in range(2):
        got = (round(r4[area][0], 4), r4[area][1], r4[area][2])
        assert got == tuple(st['maprec'][area]), ('4U record differs from package.toml maprec', area, got)
    assert abs(st['wholemap_k'] - WMAP_WGU / WMAP_W4U) < 1e-6, st['wholemap_k']
    mc = mapcom()
    # --- area maps
    for area in range(2):
        img, labels = compose_area(area, r4[area], mc)
        print('area %d: record %s, labels %s' % (area, r4[area], [(round(x, 1), round(y, 1), t) for x, y, t in labels]))
        if a.preview:
            from PIL import Image
            Image.fromarray(img).save(os.path.join(a.preview, 'm29a%02d_map.png' % area))
        tex_img = tex.encode_gu(img, 'bc3', mips=1)
        lab = {t: (2 * (x - 64), 2 * (y - 64)) for x, y, t in labels}
        for lang in LANGS:
            ents = gu_arc('%s/arc/stage/mapUI/%sd/a%02d_ui_%s.arc' % (lang, G, area, lang))
            out = []
            for p, t, d in ents:
                base = p.split('\\')[-1]
                if base == 'HD_%sa%02ddn_BM_NOMIP' % (G, area):
                    assert len(d) == len(tex_img); d = tex_img
                elif base == 'HD_gmk_%s_BM_NOMIP' % G:
                    d = mu.blank_like(d)
                elif base == '%sa%02ddn' % (G, area) and t == T_GUI:
                    _, items = mu.gui_items(d)
                    e = {k: (OFFSCREEN, -OFFSCREEN) for k in items if k.startswith('AnimP_k')}
                    if area == 0:
                        e['Tex_area01'] = lab[1]
                    d = mu.gui_set_pos(d, e)
                out.append((p, t, d))
            dst = os.path.join(a.out, 'nativeNX', lang, 'arc', 'stage', 'mapUI', 'm%02dd' % FOLDER,
                               'a%02d_ui_%s.arc' % (area, lang))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(arcpack.build(out))
    # --- whole map
    img, (ox, oy) = wholemap_image()
    pts = wholemap_check(img, mc)
    print('whole map: picture at (%d, %d) of the frame; SIS points on the art %d / %d %s' % (
        ox, oy, sum(p[4] for p in pts), len(pts), [p for p in pts if not p[4]]))
    assert all(p[4] for p in pts), 'SIS point off the 4U whole-map art: frame / offsets wrong'
    (px, py), (w, h, sx, sy), uv = pane4u('m08_map.arc', 'eng\\lyt\\quest\\m08\\ui258', 'ui258_area01')
    hl = {'area01': {'PosX': 2 * (-px - 64), 'PosY': 2 * (-py - 64), 'Rotation': 0.0}}
    size = {'area01': {'Size': (2 * w * sx, 2 * h * sy, 0.0, 0.0)}}
    print('whole map: arena highlight', hl, size)
    img2 = img.repeat(2, 0).repeat(2, 1)
    if a.preview:
        from PIL import Image, ImageDraw
        im = Image.new('RGBA', (512, 512), (40, 40, 90, 255))
        im.alpha_composite(Image.fromarray(img2).resize((512, 512), Image.NEAREST))
        dr = ImageDraw.Draw(im)
        for u, v, ar, sec, on in pts:
            dr.ellipse((4 * u - 3, 4 * v - 3, 4 * u + 3, 4 * v + 3), outline='red' if ar else 'cyan', width=2)
        x, y = 2 * (128 + hl['area01']['PosX']), 2 * (128 + hl['area01']['PosY'])
        sw, sh = size['area01']['Size'][:2]
        dr.ellipse((x - sw, y - sh, x + sw, y + sh), outline='yellow', width=1)
        im.save(os.path.join(a.preview, 'm29_wholemap.png'))
    tex_img = None
    for lang in LANGS:
        ents = gu_arc('%s/arc/stage/map_com/%s_%s.arc' % (lang, G, lang))
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
    print('wrote <lang>/arc/stage/mapUI/m%02dd/a0N_ui_<lang>.arc and map_com/m%02d_<lang>.arc for %s' % (
        FOLDER, FOLDER, ' '.join(LANGS)))


if __name__ == '__main__':
    main()
