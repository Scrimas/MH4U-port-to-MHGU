"""items_heavens_mount.py : the GU item of every 4U item in Heaven's Mount's gathering lists (4U m05d IPL: Low, High, G),
used by build_heavens_mount.py (gu_ipl) to convert the lists. No item is added: a 4U item GU lacks takes the closest GU
item, as the earlier ports did (the maintainer, 2026-11-10: "do as Gogmazios and Dalamadur, closest MHGU item").

  items_heavens_mount.py show     print the map: each 4U item of the three lists -> its GU item

- The same English name in GU (C, GU itemData_eng).
- The earlier ports' substitutes (monsters/dalamadur/tools/gear_weapons_em090.py SUBSTITUTES, gather_em090.py;
  monsters/gogmazios/tools/items_em089.py): Yoldspar Ore -> Fucium Ore, Cosmicite Ore -> Meldspar Ore, Strong Armor
  Sphere -> King Armor Sphere.
- Gossamite Ore has no GU item: dropped, its weight added to the list's most likely item (the maintainer, 2026-10-21,
  Dalamadur's meteor scales; build_heavens_mount.py gu_ipl).
- The 6 other 4U-only items -> the GU item of the same kind, icon and colour (4U and GU share both numberings,
  tools/items4u.py), nearest rarity and price (C: 4U v1.1 item table, GU itemData):
    Stam Nectar: Dragon (kinsect feed, r3, stamina colour 7) -> Heavy Jelly (GU kinsect feed, r4, colour 7)
    Nectar: Dragon+ (r4, dragon colour 5)                    -> Dragon Ambrosia (r4, colour 5)
    Stam Nectar: Dragon+ (r5, colour 7)                      -> Heavy Jelly+ (r5, colour 7)
    Glueglopper (a cricket, r4, colour 8, sell 120)          -> Blossom Cricket (r4, colour 8, sell 180)
    Killer Beetle (r4, colour 2, sell 200)                   -> Shiny Beetle (r4, colour 2, sell 200)
    Mistentoe (an account item: a plant, r3, carry 10,
               sell 100)                                     -> Water Lily Root (GU's account plant: r3, carry 10,
                                                                sell 80)
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.dirname(HERE)                         # maps/heavens_mount
ROOT = os.path.dirname(os.path.dirname(MAP))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u                                       # noqa: E402
from items4u import text_4u                         # noqa: E402
from romfs import RomFS                             # noqa: E402

# 4U name -> GU name (GU has no item of the 4U name)
SUBSTITUTES = {'Yoldspar Ore': 'Fucium Ore', 'Cosmicite Ore': 'Meldspar Ore',
               'Strong Armor Sphere': 'King Armor Sphere',
               'Stam Nectar: Dragon': 'Heavy Jelly', 'Nectar: Dragon+': 'Dragon Ambrosia',
               'Stam Nectar: Dragon+': 'Heavy Jelly+', 'Glueglopper': 'Blossom Cricket',
               'Killer Beetle': 'Shiny Beetle', 'Mistentoe': 'Water Lily Root'}
DROPPED = {214}                                      # Gossamite Ore: no GU item


def item_map(R=None):
    """gu_item(4U id) -> GU item ID, or None for a dropped item (DROPPED); KeyError for a 4U item with no GU item"""
    R = R or RomFS(paths.GU_ROMFS)
    names4u = text_4u('eng')[0]
    by_name = gear4u.gu_item_names(R, [])
    bad = [g for g in SUBSTITUTES.values() if g not in by_name]
    assert not bad, 'substitutes with no GU item of that name: %s' % bad

    def gu_item(k):
        if k in DROPPED: return None
        nm = SUBSTITUTES.get(names4u[k], names4u[k])
        if nm not in by_name: raise KeyError('4U item %d %s: no GU item named %s' % (k, names4u[k], nm))
        return by_name[nm]
    return gu_item


def main():
    import build_heavens_mount as B
    B.s4.set_source(B.U4, 'm05')
    gu_item, names4u = item_map(), text_4u('eng')[0]
    for path in ('stage\\m05d\\m05d', 'stage\\m05d\\m05d_high', 'stage\\m05d\\m05d_g'):
        _, secs = B.ipl_sections(B.u4(path, B.T_IPL))
        ks = sorted({k for lists in secs for ents in lists for _, _, k in ents})
        print(path)
        for k in ks:
            g = gu_item(k)
            if g is None or SUBSTITUTES.get(names4u[k]):
                print('  4U %4d %-22s -> %s' % (k, names4u[k], 'dropped' if g is None else 'GU %d %s' % (
                    g, SUBSTITUTES[names4u[k]])))
        print('  (%d items, the others by the same name)' % len(ks))


if __name__ == '__main__':
    if sys.argv[1:] == ['show']: main()
    else: sys.exit(__doc__)
