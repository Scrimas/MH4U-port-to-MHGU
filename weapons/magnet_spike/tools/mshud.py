"""mshud.py: the Magnet Spike's HUD gauge look (test 1: "the in-game HUD is the Charge Blade's").

Class 5 drives the Charge Blade's gauge widget (build.py word 0x665b34; ms_class.c ms_hud: 5 phials = the magnet
gauge's bars, colour = the mode). Its .gui (eng\\GUI\\01_quest\\hud\\hud14_chargeAx, quest_eng.arc) draws the vials
and the shield from HD_hud00. This writes a copy of HD_hud00 with MHF's Magnet Spike HUD art (MHF-Z's UI bank
dat/mhf_90c.bin.xbox, PNG 4, kept as dump/mhf/ui/mhf_90c_04.png) painted over them: the full vial = a gauge cell
(MHF's cell frame, white inside: GU tints it), the empty vial = MHF's dark cell, the shield = MHF's horseshoe; the
module points the gauge .gui's HD_hud00 entry at it while a Magnet Spike hunter owns the widget. The base is the HD UI
mod's HD_hud00 when installed (the user's), else GU's.

  mshud.py [OUT.tex]      default: weapons/magnet_spike/romfs/nativeNX/mh4uport/ms_hud00.tex
"""
import os, sys
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
    boxes = {k: bbox(img, v) for k, v in CB.items()}
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


if __name__ == '__main__':
    print(build(*sys.argv[1:2]))
