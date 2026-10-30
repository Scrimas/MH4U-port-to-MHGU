"""ms_icon_hdui.py : the Magnet Spike's equipment icon in the user's "HD UI v4" resident_eng.arc (local mod file, never
shipped; test 1: "the icon is still the Great Sword's in the forge, the bowgun's in the item box").

GU draws an equipment icon by icon id from HD_cmn_icon_GSM_NOMIP (1024 x 2048 RGBA8): 64-pixel cells, 10 per row,
id n = cell (n % 10, n // 10) (C: GS 55, LS 56, SnS 57, DB 58, Hammer 59 sit there). Box type -> icon id: three u8
tables (0x162e7dc, 0x164ff08, 0x165000c), type 12 = 63 (the bowguns'); build.py ms_patches sets ICON_ID there. Cell
ICON_ID is empty in GU's atlas (C). The art = MHF-Z's Magnet Spike type icon (UI bank dat/mhf_90c.bin.xbox, PNG 6:
32-pixel white silhouettes; cell (0, 10): the Cutting blade and the Impact pillar), 2x nearest. Only that entry's
data changes (new zlib stream appended, its size / offset words updated), as monsters/gogmazios/tools/ui_icon_hdui.py
does for micon01; it patches the arc as it is now, so it keeps Gogmazios' patch (re-running that tool, which starts
from its own backup, drops this one: run this again after it).
  ms_icon_hdui.py [ARC]      patch (default: the Ryujinx mods copy); the original is kept as ARC.pre-magnet-spike
  ms_icon_hdui.py restore    copy the backup back
"""
import os, shutil, struct, sys, zlib
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import tex                                                      # noqa: E402

ARC = os.path.expanduser('~/.config/Ryujinx/mods/contents/0100770008dd8000/HD UI v4/romfs/nativeNX/eng/arc/'
                         'resident_eng.arc')
ENTRY = 'eng\\GUI\\99_texture\\HD_cmn_icon_GSM_NOMIP'
CELL, COLS = 64, 10
ICON_ID = 121                                                   # build.py MS_ICON_ID
MHF_ICONS = os.path.join(ROOT, 'dump', 'mhf', 'ui', 'mhf_90c_06.png')
MHF_CELL = (0, 320, 32, 352)


def main():
    arc = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != 'restore' else ARC
    bak = arc + '.pre-magnet-spike'
    if 'restore' in sys.argv:
        shutil.copyfile(bak, arc)
        print('restored', arc)
        return
    if not os.path.exists(bak):
        shutil.copyfile(arc, bak)
    d = bytearray(open(arc, 'rb').read())
    assert d[:4] == b'ARC\0'
    n = struct.unpack_from('<H', d, 6)[0]
    idx = [i for i in range(n) if d[12 + 80 * i:12 + 80 * i + 64].split(b'\0')[0].decode() == ENTRY]
    assert len(idx) == 1, 'no %s in %s' % (ENTRY, arc)
    o = 12 + 80 * idx[0]
    t, cs, ds, off = struct.unpack_from('<4I', d, o + 64)
    t_old = zlib.decompress(bytes(d[off:off + cs]))
    assert len(t_old) == ds & 0x1FFFFFFF
    h = tex.parse(t_old)
    assert tex.FMT_GU.get(h['fmt']) == 'rgba8' and h['mips'] == 1, 'unexpected atlas format %r' % h
    old = np.array(tex.decode(t_old), np.uint8)
    x, y = (ICON_ID % COLS) * CELL, (ICON_ID // COLS) * CELL
    icon = np.array(Image.open(MHF_ICONS).convert('RGBA').crop(MHF_CELL).resize((CELL, CELL), Image.NEAREST))
    img = old.copy()
    img[y:y + CELL, x:x + CELL] = icon
    t_new = tex.encode_gu(img, 'rgba8', mips=1)
    back = np.array(tex.decode(t_new), np.uint8)
    keep = old.copy(); keep[y:y + CELL, x:x + CELL] = back[y:y + CELL, x:x + CELL]
    assert (keep == back).all(), 'pixels outside the cell changed'
    z = zlib.compress(t_new, 9)
    new_off = len(d) + (-len(d) % 16)
    d += b'\0' * (new_off - len(d)) + z
    struct.pack_into('<II', d, o + 68, len(z), (ds & ~0x1FFFFFFF) | len(t_new))
    struct.pack_into('<I', d, o + 76, new_off)
    open(arc, 'wb').write(d)
    print('%s: %s cell %d (%d, %d) = MHF Magnet Spike icon, entry %d -> offset %d, %d B (backup %s)' %
          (arc, ENTRY.split('\\')[-1], ICON_ID, x, y, idx[0], new_off, len(z), bak))


if __name__ == '__main__':
    main()
