"""items_em070_01.py : Shrouded Nerscylla materials and break rewards for module/items.c and module/gear.c -> data file sections
TBLA + TXTA (her 4 items APPENDED after Tidal Najarala's, notes/items-append.md) and BUI4 (tools/portdata.py, tools/items4u.py).
  items_em070_01.py          write the sections
  items_em070_01.py show     print them only
Materials (C, 2026-11-06: 4U item names and her carve / shiny / break tables): the 4 4U items named for her, in 4U ID order -> GU
3051..3054 (allocations.toml shrouded_nerscylla items). Her other table items exist in GU under the same English name. GU category:
the most common category of the GU items with the same icon (as Black Gravios').
Break rewards (C): 4U lookup items4u.breaks_em of em 96, rank 3 only (4U has her at G rank only: her carve and break tables hold
nothing else), mapped to GU Nerscylla's own break record (result.arc bui_s4 em 0x46: conds 10 / 20 / 30 / 40 = GU break groups 0..3,
cond = 10 * (group + 1), hold the mixes of 4U em027's groups 0 general / 2 claw / 3 poison spike / 4 hide: the 4U subquest texts name parts 2
claw, 3 spike, 4 hide, and GU's "poison spike" subquest is digit 2, so 4U group 3 = GU group 2). 4U groups 1 and 6 (Frenzy crystals) have no GU
part; groups 5 and 7 (her worn skin's Gore Magala parts) have no cond in GU's record: left out, as GU's Nerscylla has them.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/shrouded_nerscylla
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

NAME, EM4U = 'shrouded_nerscylla', 96
# 4U IDs (text_4u, C). Order = GU IDs from 3051: never reorder once released (saves keep them).
ITEMS_4U = [1406,   # S.Nerscylla Cortex
            1407,   # S.Nerscylla Scishorn
            1408,   # S.Nerscylla Hardclaw
            1409]   # S.Nerscylla Surspike
# the other 4U items of her break, carve and shiny tables -> GU items of the same English name (C, GU itemData_eng)
OTHER_4U_GU = {1604: 455,    # Omniplegia Sac
               822: 2121,    # Queen Substance
               1624: 539,    # Monster Essence
               1457: 1111}   # Pearl Glosshide
NO_GU_4U = set()
BREAK_GROUPS = [(0, 10), (2, 20), (3, 30), (4, 40)]              # (4U group, GU cond): GU Nerscylla's layout
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
