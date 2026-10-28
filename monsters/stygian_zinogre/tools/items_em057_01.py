"""items_em057_01.py : Stygian Zinogre materials and break rewards for module/items.c and module/gear.c -> data file
sections TBLA + TXTA (its 15 items APPENDED after Dalamadur's, notes/items-append.md) and BUI2 / BUI4
(tools/portdata.py, tools/items4u.py). Facts: notes/phase1-assets.md 4b.
  items_em057_01.py          write the sections
  items_em057_01.py show     print them only
Materials (C: 4U item names): every 4U item named for Stygian Zinogre, in 4U ID order -> GU 3021..3035
(allocations.toml stygian_zinogre items). GU category (file +0x1b, meaning not traced): the most common category of
the GU items with the same icon (as Dalamadur's items_em090.py).
Break rewards (C): 4U lookup items4u.breaks_em (Stygian's groups follow Zinogre em048's layout: 0 body, 1 frenzy,
2 horn, 3 claws, 4 back), mapped to GU Zinogre's own break record (result.arc bui_s2 / bui_s4 em 0x39: cond 10 body,
20 horn, 30 back, 40 claws: the same item mixes as 4U em048's groups 0 / 2 / 4 / 3, GU's chances retuned). 4U group 1
(Frenzy crystals, given when the hunter overcomes its frenzy) has no GU part: left out, as Tigerstripe's. High (4U
rank 2) -> BUI2, G (rank 3) -> BUI4 (module/items.c: GU file bui_s<rank>).
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

NAME, EM4U = 'stygian_zinogre', 49
# 4U IDs (text_4u, C). Order = GU IDs from 3021: never reorder once released (saves keep them).
ITEMS_4U = [534,    # S.Zinogre Carapace
            535,    # S.Zinogre Horn+
            536,    # S.Zinogre Claw+
            537,    # S.Zinogre Tail
            538,    # S.Zin Drakeshell
            539,    # Dracophage Bug
            540,    # S.Zinogre Dragonhair
            541,    # S.Zinogre Umbrage
            1507,   # S.Zin Dragonlocks
            1508,   # S.Zinogre Cortex
            1509,   # S.Zinogre Hardhorn
            1510,   # S.Zinogre Hardclaw
            1511,   # S.Zinogre Drakehold
            1512,   # S.Zinogre Lash
            1513]   # S.Zinogre Skymerald
# the other 4U items of its carve and shiny tables -> GU items of the same English name (C, GU itemData_eng)
OTHER_4U_GU = {825: 2128,   # Wyvern Tear
               826: 2129,   # Large Wyvern Tear
               # the reward rows A / B / subquest of its 4U quests m10603 m10607 m10608 m10612 m10616 m10925 m10930
               # m11010 m00907 m01029 (2026-10-28; m60205 is extdata, not read yet), same English name (C). No
               # same-name GU item, to decide with their quests: 480 S.Queen Concentrate (m10607; GU has S.Queen
               # Extract / D.S.QueenConcentrate), 510 511 513 Azure Rathalos (m10607), 578..581 Brute Tigrex (m10608),
               # 1643 Strong Armor Sphere (m10930)
               # Brute Tigrex is not in GU: m10608 names Tigrex in its place (build_em057_01_quest.py PARTNER_GU, a
               # DEVIATION), so its reward rows give the matching Tigrex materials (GU id = itemData_eng index / 2)
               # the DLC event m60205 (extdata), same English name (C): 1723 Immenseness Ticket has none (NO_GU_4U)
               1297: 699,   # Rubbery Finehide
               1298: 704,   # Gypceros Hardhead
               1599: 453,   # Deadly Poison Sac
               1611: 417,   # Monster Slogbone
               1638: 333,   # Purecrystal
               1648: 356,   # Enduring Charm
               # Azure Rathalos is not in GU: m10607 names Rathalos in its place (PARTNER_GU, a DEVIATION), so its
               # reward rows give the matching Rathalos materials (GU itemData_eng index / 2)
               510: 1203,   # A.Rathalos Scale+ -> Rathalos Scale+
               511: 1206,   # A.Rathalos Carapace -> Rathalos Carapace
               512: 1211,   # A.Rathalos Tail -> Rathalos Tail
               513: 1209,   # A.Rathalos Wing -> Rathalos Wing
               578: 1376,   # B.Tigrex Scale+ -> Tigrex Scale+
               579: 1379,   # B.Tigrex Carapace -> Tigrex Carapace
               580: 1384,   # B.Tigrex Claw+ -> Tigrex Claw+
               581: 1387,   # B.Tigrex Fang+ -> Tigrex Fang+
               38: 355,     # Timeworn Charm
               86: 99,      # Bone Husk
               226: 347,    # Armor Sphere+
               227: 348,    # Adv Armor Sphere
               228: 349,    # Hard Armor Sphere
               229: 350,    # Heavy Armor Sphere
               259: 394,    # Fulgurbug
               269: 414,    # Monster Keenbone
               270: 415,    # Monster Hardbone
               277: 432,    # Wyvern Fang
               278: 433,    # Wyvern Claw
               280: 440,    # Wyvern Gem
               292: 461,    # Inferno Sac
               298: 469,    # Torrent Sac
               351: 616,    # Ioprey Fang
               353: 618,    # Ioprey Scale+
               355: 621,    # Ioprey Hide+
               464: 538,    # Monster Broth
               472: 1021,   # S.Queen Carapace
               474: 1023,   # S.Queen Hardpectus
               476: 1025,   # S.Queen Sharpclaw
               477: 1027,   # S.Queen Jaw
               478: 1029,   # S.Queen Crescent
               509: 1214,   # Rathalos Ruby
               519: 1235,   # Rath Medulla
               522: 1239,   # Zinogre Carapace
               524: 1242,   # Zinogre Electrofur
               528: 1248,   # Zinogre Claw+
               531: 1253,   # Zinogre Shocker+
               532: 1255,   # Zinogre Plate
               533: 1256,   # Zinogre Jasper
               553: 1090,   # Brach Gem
               576: 1389,   # Tigrex Scalp
               759: 358,    # Ancient Shard
               887: 1774,   # Commendation G
               957: 341,    # Bloodrun Jewel
               958: 342,    # Lazurite Jewel
               959: 343,    # Adamant Orb
               1410: 1441,  # Gore Magala Shard
               1413: 1451,  # Gore Magala Shredder
               1417: 1463,  # Chaos Scale
               1418: 1461,  # Diametrical Horn
               1419: 1448,  # Antinomic Wing
               1420: 1455,  # Contrary Scale
               1480: 1072,  # Brach Cortex
               1481: 1075,  # Fine Brach Ebonshell
               1482: 1078,  # Brach Crown
               1485: 1091,  # Brach Pallium
               1486: 1081,  # Glowing Slime
               1514: 1404,  # Seregios Slavescale
               1516: 1407,  # Seregios Airblade
               1518: 1410,  # Seregios Carver
               1524: 1418,  # Seregios Scraper
               1526: 1420,  # Seregios Dissenter
               1611: 417,   # Monster Slogbone
               1616: 421,   # Avian Stoutbone
               1648: 356}   # Enduring Charm
NO_GU_4U = {1723,      # Immenseness Ticket (m60205's event ticket: GU has no item; its chance goes to the row's most
                       # likely item, tools/quest4u.py rem_4u)
            480,       # S.Queen Concentrate (m10607): no same-name GU item (GU: S.Queen Extract / D.S.QueenConcentrate)
            1643}      # Strong Armor Sphere (m10930): GU has none (its spheres: Armor Sphere .. True Armor Sphere)
BREAK_GROUPS = [(0, 10), (2, 20), (3, 40), (4, 30)]     # (4U group, GU cond)
RANKS_4U = (2, 3)                                        # High, G


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


def materials(R=None, exe=None):
    R = R or RomFS(paths.GU_ROMFS)
    exe = exe or open(EXE, 'rb').read()
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
