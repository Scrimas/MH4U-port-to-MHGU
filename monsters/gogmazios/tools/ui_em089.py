"""ui_em089.py : HUD icon + name of Gogmazios (registry index 137) as RomFS additions. See notes/data.md.

  ui_em089.py            write monsters/gogmazios/romfs/nativeNX/<lang>/GUI/... for eng fre ger ita spa
  ui_em089.py preview    also save the patched atlases as PNG into the scratch dir given by $UI_PREVIEW

Icon: reg_icon[137] (module/build.py ICON_EM089) = UI index 141. The icon setter 0x56ef50 picks atlas
index / 98 (HD_cmn_micon00 / 01, table 0x1635228) and 0x560918 kind 3 computes the cell: local = index % 98,
column = local % 7, row = local / 7, 36 units (= 72 HD pixels) per cell. 141 -> micon01 cell 43 (row 6, col 1),
empty in every language. Only the BC3 blocks of that cell are re-encoded; every other block is copied.
Source: MH4U eng core_common.arc `cmn_micon_BM_MQ_NOMIP` cell (row 0, col 8), 36x36 pixel art -> 2x nearest
(GU's HD icons are the same 36-unit pixel art at 2x).

Name: monsterName_<lang>.gmd entry k = registry index k (0x55bc4c(mgr, 3, k)); entry 137 starts a second list
(Rathian), so index 137 cannot use it. Entry 105 'dummy1' (index 105 = unused code 0x1064) becomes 'Gogmazios'
and the module hook name_index (0x55bda4, id -> name index) maps 137 -> 105.
GMD v0x010302: strings are the last <u32 @0x20> bytes, NUL-separated, no offset table -> only that size changes.
Base: the v1.0 RomFS (MHGU_Editor scratch); v1.4's copies could not be read (no NCA keys here).
"""
import os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import arcpack, tex

GU_ROMFS = paths.GU_ROMFS
SRC_4U = os.path.join(ROOT, 'dump/romfs/eng/data/core_common.arc')
OUT = os.environ.get('UI_OUT', os.path.join(MON, 'romfs/nativeNX'))   # UI_OUT: dry run elsewhere
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')
import alloc
ALLOC = alloc.monster('gogmazios')
ICON_UI_INDEX = ALLOC['ui_icon']         # allocations.toml (141, 143-145 = the user's HD UI v4 cheat: Alatreon /
                                         # Fatalis icons)
NAME_ENTRY, NAME = ALLOC['name_entry'], 'Gogmazios'   # allocations.toml (main.c EM089_NAME_ENTRY)
SRC_CELL = (0, 0)                        # 4U atlas (row, col), 36-pixel cells: 4U has NO Gogmazios icon, its quests
                                         # use icon 0 = '?' (m11014 / m11035 u16 +0xE8 = 0; Kushala's m01002 = 33).
                                         # (0, 8) was a by-eye guess (another monster), replaced 2026-10-19
CELL = 72


def gu_icon_cell(index):
    local = index % 98
    return index // 98, (local % 7) * CELL, (local // 7) * CELL      # atlas, x, y (HD pixels)


def icon_4u():
    _, e = arcpack.read(open(SRC_4U, 'rb').read())
    t = [d for p, _, d in e if p.endswith('cmn_micon_BM_MQ_NOMIP')][0]
    img = tex.decode(t)
    r, c = SRC_CELL
    cell = img[r * 36:r * 36 + 36, c * 36:c * 36 + 36]
    return cell.repeat(2, 0).repeat(2, 1)


def patch_atlas(t, x, y, icon):
    """replace the BC3 blocks under icon (x, y multiples of 4) in a 1-mip GU texture; returns (bytes, image)."""
    h = tex.parse(t)
    assert tex.FMT_GU[h['fmt']] == 'bc3' and h['mips'] == 1 and x % 4 == 0 and y % 4 == 0
    w, hh, bpp, bh, off, size = tex.gu_layout(h['width'], h['height'], 1, 'bc3')[0]
    el = tex.deswizzle(h['data'][off:off + size], w, hh, bpp, bh).copy()
    before = tex.decode(t)[y:y + icon.shape[0], x:x + icon.shape[1]]
    assert (before[..., 3] == 0).all() or (before[..., :3] >= 250).all(), 'target cell is not empty'
    enc = tex.bc_encode(icon, 'bc3').reshape(icon.shape[0] // 4, icon.shape[1] // 4, bpp)
    el[y // 4:y // 4 + enc.shape[0], x // 4:x // 4 + enc.shape[1]] = enc
    data = tex.swizzle(el, bpp, bh)
    start = len(t) - len(h['data'])
    out = t[:start] + data + t[start + len(data):]
    assert len(out) == len(t)
    return out, tex.decode(out)


def gmd_set(d, k, text):
    assert d[:4] == b'GMD\0' and struct.unpack_from('<I', d, 4)[0] == 0x00010302
    ss = struct.unpack_from('<I', d, 0x20)[0]
    sc = struct.unpack_from('<I', d, 0x18)[0]
    body = d[len(d) - ss:]
    parts = body.split(b'\0')
    assert len(parts) == sc + 1 and parts[-1] == b'', 'unexpected string section'
    parts[k] = text.encode('utf-8')
    nb = b'\0'.join(parts)
    out = bytearray(d[:len(d) - ss] + nb)
    struct.pack_into('<I', out, 0x20, len(nb))
    return bytes(out)


def main():
    rom = RomFS(GU_ROMFS)
    icon = icon_4u()
    atlas, x, y = gu_icon_cell(ICON_UI_INDEX)
    preview = os.environ.get('UI_PREVIEW') if 'preview' in sys.argv else None
    sys.path.insert(0, paths.GU_PY)
    import gmd
    for lang in LANGS:
        rel = '%s/GUI/99_texture/HD_cmn_micon%02d_BM_MQ_NOMIP.tex' % (lang, atlas)
        t = rom.read('/nativeNX/' + rel)
        new, img = patch_atlas(t, x, y, icon)
        old = tex.decode(t)
        mask = np.ones(old.shape[:2], bool); mask[y:y + CELL, x:x + CELL] = False
        assert (old[mask] == img[mask]).all(), 'pixels outside the cell changed'
        os.makedirs(os.path.dirname(os.path.join(OUT, rel)), exist_ok=True)
        open(os.path.join(OUT, rel), 'wb').write(new)
        if preview: tex.save_png(img, os.path.join(preview, 'micon%02d_%s.png' % (atlas, lang)))

        rel = '%s/GUI/06_msg/monsterName_%s.gmd' % (lang, lang)
        d = rom.read('/nativeNX/' + rel)
        s0 = gmd.gmd_strings(d)
        assert s0[NAME_ENTRY] == 'dummy1', (lang, s0[NAME_ENTRY])
        nd = gmd_set(d, NAME_ENTRY, NAME)
        s1 = gmd.gmd_strings(nd)
        assert s1[NAME_ENTRY] == NAME and all(a == b for i, (a, b) in enumerate(zip(s0, s1)) if i != NAME_ENTRY)
        os.makedirs(os.path.dirname(os.path.join(OUT, rel)), exist_ok=True)
        open(os.path.join(OUT, rel), 'wb').write(nd)
        print('%s: icon -> micon%02d (%d, %d), name entry %d = %r' % (lang, atlas, x, y, NAME_ENTRY, NAME))


if __name__ == '__main__':
    main()
