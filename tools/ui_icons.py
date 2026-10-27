"""ui_icons.py : the ported monsters' icon atlas, a third page after GU's HD_cmn_micon00 / 01 (module/icons.c).

  ui_icons.py OUT_DIR     write micon_sd.tex and micon_hd.tex into OUT_DIR (module/build.py does)

GU's icon setter 0x56ef50 only knows UI indexes 0..195 (micon00 / 01); index 196 + k is cell k of this atlas, shown by
the module's hook on that setter. The atlas has the size and cell grid of the micon01 the game loaded, because the
sprite keeps micon01's .gui texture entry (its UVs): micon_sd = GU's 512x512 (72-pixel cells), micon_hd = the "HD UI
v4" mod's 1024x1024 (144-pixel cells). Cell k: column k % 7, row k // 7 (0x560918 kind 3, as micon01).

Cells: 0 = 4U's "?" (quest boards of 4U quests whose icon is 0), then every allocations.toml entry with a ui_icon
(196 + k): 4U eng core_common.arc `cmn_micon_BM_MQ_NOMIP`, 36-pixel art at its icon_4u index (indexes 0..97 = the left
block, 7 columns; 98.. = the right block, 7 columns from x 256), nearest-neighbour scaled.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths
sys.path.insert(0, paths.GU_PY)
import arcpack, tex

SRC_4U = os.path.join(paths.ROOT, 'dump/romfs/eng/data/core_common.arc')
ATLASES = (('micon_sd.tex', 512, 72), ('micon_hd.tex', 1024, 144))   # module/icons.c s_atlas
CELLS = 49                       # rows 0..6 (7 * 72 = 504 pixels of 512)


def cells():
    """{cell: 4U icon index}: cell 0 = '?', then the monsters' (ui_icon - ICON_PAGE2)"""
    out = {0: 0}
    for m in alloc.monsters():
        if 'ui_icon' not in m: continue
        k = m['ui_icon'] - alloc.ICON_PAGE2
        assert 0 < k < CELLS and k not in out, (m['name'], m['ui_icon'])
        out[k] = m['icon_4u']
    return out


def icon_4u(img, i):
    """4U index i: 0..97 = the left half's 7 x 14 grid from x 0, 98.. = the right half's from x 256 (its gutter columns
    are 291 / 292, 363 / 364, ...; 252 cut the cells 4 pixels left: user 2026-10-27, Tigerstripe off-centre)"""
    x0, c, r = (0, i % 7, i // 7) if i < 98 else (256, (i - 98) % 7, (i - 98) // 7)
    return img[r * 36:r * 36 + 36, x0 + c * 36:x0 + c * 36 + 36]


def build(out_dir):
    _, e = arcpack.read(open(SRC_4U, 'rb').read())
    src = tex.decode([d for p, _, d in e if p.endswith('cmn_micon_BM_MQ_NOMIP')][0])
    want = cells()
    for name, size, cell in ATLASES:
        img = np.zeros((size, size, 4), np.uint8)
        for k, i in want.items():
            x, y = (k % 7) * cell, (k // 7) * cell
            img[y:y + cell, x:x + cell] = icon_4u(src, i).repeat(cell // 36, 0).repeat(cell // 36, 1)
        with open(os.path.join(out_dir, name), 'wb') as f:
            f.write(tex.encode_gu(img, 'bc3', mips=1))
    return [name for name, _, _ in ATLASES]


if __name__ == '__main__':
    print('wrote', build(sys.argv[1]))
