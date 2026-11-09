"""items_em068_01.py : Tidal Najarala materials and break rewards for module/items.c and module/gear.c -> data file sections
TBLA + TXTA (her 3 items APPENDED after Monoblos', notes/items-append.md) and BUI4 (tools/portdata.py, tools/items4u.py).
  items_em068_01.py          write the sections
  items_em068_01.py show     print them only
Materials (C, 2026-11-06: 4U item names and her carve / shiny / break tables): the 3 4U items named for her, in 4U ID order -> GU
3048..3050 (allocations.toml tidal_najarala items). Her other table items exist in GU under the same English name. GU category:
the most common category of the GU items with the same icon (as Black Gravios').
Break rewards (C): 4U lookup items4u.breaks_em of em 93, rank 3 only (4U has her at G rank only: her carve and break tables hold
nothing else), mapped to GU Najarala's own break record (result.arc bui_s4 em 0x44: conds 10 / 20 / 30 / 40 / 50 hold the mixes of 4U
em023's groups 0 / 2 / 3 / 4 / 5, as Tigerstripe's). 4U group 1 (Frenzy crystals) has no GU part; groups 6 / 7 belong to the next
monster of 4U's table: left out.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

NAME, EM4U = 'tidal_najarala', 93
# 4U IDs (text_4u, C). Order = GU IDs from 3048: never reorder once released (saves keep them).
ITEMS_4U = [1366,   # T.Najarala Piel
            1367,   # T.Najarala Cortex
            1368]   # T.Najarala Splasher
# the other 4U items of her break, carve and shiny tables -> GU items of the same English name (C, GU itemData_eng)
OTHER_4U_GU = {826: 2129,   # Large Wyvern Tear
               1364: 966,   # Heart-stopping Beak
               1601: 470,   # Flood Sac
               1610: 441,   # Lrg Wyvern Gem
               1611: 417}   # Monster Slogbone
NO_GU_4U = set()
BREAK_GROUPS = [(0, 10), (2, 20), (3, 30), (4, 40), (5, 50)]     # (4U group, GU cond): GU Najarala's layout
RANKS_4U = (3,)                                                  # G


def categories(R, exe):
    """{4U id: GU category} = the most common category among the GU items with the 4U item's icon"""
    d = gear4u.gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))['table\\itemData']
    names = gear4u.gmd(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    by_icon = collections.defaultdict(collections.Counter)
    for i in range(struct.unpack_from('<I', d, 4)[0]):
        r = d[8 + 44 * i:8 + 44 * (i + 1)]
        if r[4] == 0 and names[2 * i] not in ('DUMMY', ''):           # materials (type 0) with a name
            by_icon[r[0x10]][r[0x1b]] += 1
    out = {}
    for k in ITEMS_4U:
        icon = items4u.item_4u(exe, k)[1]
        assert by_icon[icon], '4U item %d: no GU material has icon %d' % (k, icon)
        out[k] = by_icon[icon].most_common(1)[0][0]
    return out


def check_other(R):
    """every OTHER_4U_GU pair has the same English name in both games"""
    gn = gear4u.gmd(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    n4 = text_4u('eng')[0]
    bad = [(k, n4[k], g, gn[2 * g]) for k, g in OTHER_4U_GU.items() if n4[k] != gn[2 * g]]
    assert not bad, 'OTHER_4U_GU names differ: %s' % bad


def materials(R=None, exe=None):
    R = R or RomFS(paths.GU_ROMFS)
    exe = exe or open(EXE, 'rb').read()
    check_other(R)
    return items4u.Materials(NAME, [(k, c) for k, c in categories(R, exe).items()], (), OTHER_4U_GU, NO_GU_4U)


def main():
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    text = {lang: text_4u(lang) for lang in LANGS}
    m = materials(R, exe)
    out = list(m.append_sections(exe, text, R))
    for rank in RANKS_4U:
        brk = items4u.breaks_em(exe, EM4U, BREAK_GROUPS, rank, m.gu_item)
        assert len(brk) == len(BREAK_GROUPS) and all(i is not None for _, es in brk for _, _, i in es), rank
        out.append(items4u.bui_section(brk, items4u.RANK_4U_GU[rank]))
    if sys.argv[1:] == ['show']:
        for s in out: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in out: print('wrote', portdata.write_section(NAME, s))


if __name__ == '__main__':
    main()
