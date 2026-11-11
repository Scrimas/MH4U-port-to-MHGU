"""items_em007_01.py : Monoblos materials and break rewards for module/items.c and module/gear.c -> data file sections
TBLA + TXTA (his 7 items APPENDED after Black Gravios', notes/items-append.md) and BUI2 / BUI4 (tools/portdata.py,
tools/items4u.py).
  items_em007_01.py          write the sections
  items_em007_01.py show     print them only
Materials (C, 2026-11-05: 4U item names and his carve / shiny / break tables): the 4U items named for Monoblos plus his
two horns (Scarlet Finehorn / Stouthorn: his break group 2, no other 4U monster drops them), in 4U ID order -> GU
3041..3047 (allocations.toml monoblos items). White Monoblos' (W.Monoblos Cortex / Chine, Argent Stouthorn) are not
his (White Monoblos is not in this port); 4U 1696 Monoblos Scrap+ is in none of his tables and none of his gear's
recipes: left out. GU category: the most common category of the GU items with the same icon (as Black Gravios').
Break rewards (C, 2026-11-05): 4U lookup items4u.breaks_em of em 101, mapped to GU Diablos' own break record (result.arc
bui_s2 / bui_s4 em 0x7: cond 10 / 20 / 30 hold the item mixes of 4U em099's groups 0 / 2 / 3: body / horn / back, GU's
chances retuned). 4U group 1 (Frenzy crystals) has no GU part and groups 4..7 are White Monoblos' (the em101 table
serves both): left out. High (4U rank 2) -> BUI2, G (rank 3) -> BUI4 (module/items.c: GU file bui_s<rank>).
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

NAME, EM4U = 'monoblos', 101
# 4U IDs (text_4u, C). Order = GU IDs from 3041: never reorder once released (saves keep them).
ITEMS_4U = [1545,   # Monoblos Carapace
            1546,   # Monoblos Cortex
            1547,   # Monoblos Thoracic
            1548,   # Monoblos Chine
            1549,   # Scarlet Finehorn
            1550,   # Scarlet Stouthorn
            1551]   # Monoblos Heart
# the other 4U items of his break, carve and shiny tables -> GU items of the same English name (C, GU itemData_eng)
OTHER_4U_GU = {270: 415,    # Monster Hardbone
               280: 440,    # Wyvern Gem
               825: 2128,   # Wyvern Tear
               826: 2129,   # Large Wyvern Tear
               1540: 1433,  # Diablos Tailcase+
               1541: 1434,  # Blos Medulla
               1610: 441,   # Lrg Wyvern Gem
               1611: 417}   # Monster Slogbone
NO_GU_4U = set()
BREAK_GROUPS = [(0, 10), (2, 20), (3, 30)]     # (4U group, GU cond): body, horn, back (GU Diablos' layout)
RANKS_4U = (2, 3)                              # High, G


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
