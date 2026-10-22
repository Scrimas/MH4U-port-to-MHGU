"""items_em090.py : Dalamadur / Shah Dalamadur materials and break rewards for module/items.c and module/gear.c ->
data file sections TBLA + TXTA (the 30 items APPENDED past GU's 2991, notes/items-append.md) of the dalamadur entry,
and BUI<rank> of all four entries (tools/portdata.py, tools/items4u.py). Facts: monsters/dalamadur/notes/plan.md
goal F.

  items_em090.py          write the sections
  items_em090.py show     print them only

Materials (C: 4U item names): every 4U item named for Dalamadur / Shah Dalamadur, in 4U ID order -> GU 2991..3020
(allocations.toml dalamadur items). GU category (file +0x1b, meaning not traced): the most common category of the GU
items with the same icon (derived, as Gogmazios' list took the Daora item with the same icon).
Break rewards (C): 4U lookup items4u.breaks_em, 4U group g -> GU cond 10 * (g + 2) (module/dala_break.c: GU group =
4U group + 1); High (4U rank 2) -> BUI2, G (rank 3) -> BUI4 (module/items.c: GU file bui_s<rank>); Shah has G only.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

# 4U IDs (text_4u, C). Order = GU IDs from 2991: never reorder once released (saves keep them).
ITEMS_4U = [677,    # Dalamadur Steel
            678,    # Dalam Tail Scale
            679,    # Dalamadur Gazer
            680,    # Dalamadur Pectus
            681,    # Dalamadur Glaive
            682,    # Dalamadur Talon
            683,    # Dalam Tail Shell
            684,    # Dalamadur Fanblade
            685,    # Vortex Bone
            686,    # Skyblade Gem
            687,    # Shattered Omen
            881,    # Dalamadur Ticket
            951,    # Dalamadur Scrap
            1369,   # Dalamadur Steel+
            1370,   # Dalamadur Glaive+
            1371,   # Dalamadur Pectus+
            1372,   # Dalamadur Ripper
            1373,   # Dalamadur Fanblade+
            1374,   # Dalam Tail Scale+
            1375,   # Dalam Tail Shell+
            1376,   # Skyblade Drgnsphire
            1377,   # S.Dalamadur Steel+
            1378,   # S.Dalamadur Glaive+
            1379,   # S.Dalamadur Gazer
            1380,   # S.Dalamadur Pectus+
            1381,   # S.Dalamadur Ripper
            1382,   # S.Dalam Fanblade+
            1383,   # S.Dalam Tail Scale+
            1384,   # S.Dalam Tail Shell+
            1700]   # Dalamadur Scrap+
# the other 4U items of the break tables and quest reward rows (m10709 rows A / B) -> GU items of the same name
# (GU English itemData names; Gogmazios' items_em089.py OTHER_4U_GU)
OTHER_4U_GU = {281: 442,    # Elder Dragon Blood
               888: 1776,   # Accolade
               271: 418,    # Elder Dragon Bone
               228: 349,    # Hard Armor Sphere
               229: 350,    # Heavy Armor Sphere
               37: 354,     # Shining Charm
               38: 355,     # Timeworn Charm
               958: 342,    # Lazurite Jewel
               758: 357,    # Rustshard
               759: 358,    # Ancient Shard
               # the other 4U quests' rows (m10721, m11030 and the event quests m60131 / m60209 / m60213, 2026-10-21)
               217: 332,    # Novacrystal
               889: 1777,   # Accolade G
               959: 343,    # Adamant Orb
               1608: 419,   # Lrg ElderDragon Bone
               1642: 344,   # Sovereign Orb
               1643: 351,   # Strong Armor Sphere -> King Armor Sphere (Gogmazios' choice)
               1648: 356,   # Enduring Charm
               1720: 2937}  # Conqueror's Seal -> Hero's Seal (GU has no Conqueror's Seal; the recipes' substitute
                            # for Conqueror's Seal G, gear_weapons_em090.py SUBSTITUTES)
# 4U items GU has no item for (dropped from the reward rows, chance to the row's most likely item, quest4u.rem_4u):
# Gold Guild Ticket (m60131), Immenseness Ticket S (event special reward, m60209 / m60213)
NO_GU_4U = {249, 1724}
# break groups: (4U group, GU cond) per entry; (4U em, ranks)
BREAKS = {'dalamadur': (24, [(0, 20), (1, 30), (2, 40), (3, 50)], (2, 3)),
          'shah_dalamadur': (110, [(0, 20), (1, 30), (2, 40), (3, 50)], (3,)),
          'dalamadur_tail': (83, [(0, 20), (1, 30)], (2, 3)),
          'shah_dalamadur_tail': (111, [(0, 20), (1, 30)], (3,))}


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


def materials(R, exe):
    return items4u.Materials('dalamadur', [(k, c) for k, c in categories(R, exe).items()], (), OTHER_4U_GU, NO_GU_4U)


def main():
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    text = {lang: text_4u(lang) for lang in LANGS}
    m = materials(R, exe)
    out = [('dalamadur', s) for s in m.append_sections(exe, text, R)]
    for name, (em, groups, ranks) in BREAKS.items():
        for rank in ranks:
            brk = items4u.breaks_em(exe, em, groups, rank, m.gu_item)
            assert brk and all(i is not None for _, es in brk for _, _, i in es), (name, rank)
            out.append((name, items4u.bui_section(brk, items4u.RANK_4U_GU[rank])))
    if sys.argv[1:] == ['show']:
        for name, s in out: print(name, s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for name, s in out: print('wrote', portdata.write_section(name, s))


if __name__ == '__main__':
    main()
