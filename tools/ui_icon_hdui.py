"""ui_icon_hdui.py : put em089's icon into the user's "HD UI v4" resident_eng.arc (local mod file, never shipped).

  ui_icon_hdui.py [ARC]      patch (default: the Ryujinx mods copy); the original is kept as ARC.pre-gogmazios
  ui_icon_hdui.py restore    copy the backup back

GU loads HD_cmn_micon00/01 from nativeNX/eng/arc/resident_eng.arc, so tools/ui_em089.py's loose atlases are never
read. HD UI v4 replaces that arc: micon01 = 1024x1024 BC3, 144-pixel cells (4x the 36-unit grid), cells 141 / 143-145
hold its Alatreon / Fatalis icons and 146.. are empty. Only the BC3 blocks of cell ICON_UI_INDEX change (the 4U icon,
4x nearest); the new zlib stream is appended at the end of the file and only that entry's size / offset words change,
so every other entry stays byte-identical (the arc's own header quirks, e.g. the stray bit 24 in HD_load00's size
field, are left alone).
"""
import os, shutil, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui_em089, tex

ARC = os.path.expanduser('~/.config/Ryujinx/mods/contents/0100770008dd8000/HD UI v4/romfs/nativeNX/eng/arc/'
                         'resident_eng.arc')
ENTRY = 'eng\\GUI\\99_texture\\HD_cmn_micon01_BM_MQ_NOMIP'
CELL = 144


def main():
    arc = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != 'restore' else ARC
    bak = arc + '.pre-gogmazios'
    if 'restore' in sys.argv:
        shutil.copyfile(bak, arc)
        print('restored', arc)
        return
    if not os.path.exists(bak):
        shutil.copyfile(arc, bak)
    d = bytearray(open(bak, 'rb').read())
    assert d[:4] == b'ARC\0'
    n = struct.unpack_from('<H', d, 6)[0]
    idx = [i for i in range(n) if d[12 + 80 * i:12 + 80 * i + 64].split(b'\0')[0].decode() == ENTRY]
    assert len(idx) == 1, 'no %s in %s' % (ENTRY, arc)
    o = 12 + 80 * idx[0]
    t, cs, ds, off = struct.unpack_from('<4I', d, o + 64)
    t_old = zlib.decompress(bytes(d[off:off + cs]))
    assert len(t_old) == ds & 0x1FFFFFFF
    atlas, _, _ = ui_em089.gu_icon_cell(ui_em089.ICON_UI_INDEX)
    assert atlas == 1, 'icon index %d is not in micon01' % ui_em089.ICON_UI_INDEX
    local = ui_em089.ICON_UI_INDEX % 98
    x, y = (local % 7) * CELL, (local // 7) * CELL
    icon = ui_em089.icon_4u().repeat(2, 0).repeat(2, 1)          # 72 (2x) -> 144 (4x)
    t_new, img = ui_em089.patch_atlas(t_old, x, y, icon)
    old = tex.decode(t_old)
    mask = (slice(y, y + CELL), slice(x, x + CELL))
    keep = old.copy(); keep[mask] = img[mask]
    assert (keep == img).all(), 'pixels outside the cell changed'
    z = zlib.compress(t_new, 9)
    new_off = len(d) + (-len(d) % 16)
    d += b'\0' * (new_off - len(d)) + z
    struct.pack_into('<II', d, o + 68, len(z), ds)
    struct.pack_into('<I', d, o + 76, new_off)
    open(arc, 'wb').write(d)
    print('%s: %s cell %d (%d, %d) patched, entry %d -> offset %d, %d B (backup %s)' %
          (arc, ENTRY.split('\\')[-1], ui_em089.ICON_UI_INDEX, x, y, idx[0], new_off, len(z), bak))


if __name__ == '__main__':
    main()
