"""items_em067_01.py : Tigerstripe Zamtrios materials and break rewards for module/items.c -> data file sections ITEM,
BUI (gen/ITEM.sec, gen/BUI.sec; tools/portdata.py, tools/items4u.py). 4U data: notes/content-data.md.

  items_em067_01.py          write the sections
  items_em067_01.py show     print them only

Materials in the DUMMY items 2986..2990 (allocations.toml). Category (GU file +0x1b, meaning not traced): copied from
GU's Zamtrios item of the same name (Shard 944, Piel 942, Grandfin 946, Sawtooth+ 948, Tailbrand 950; icon 13 is
both Grandfin's and Tailbrand's, so the name decides). 4U's prices are kept (GU retuned plain Zamtrios').
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tigerstripe_zamtrios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import items4u, portdata
from items4u import EXE, LANGS, text_4u

# (4U id, GU category)
ITEMS = [(1357, 3),   # T.Zamtrios Shard
         (1358, 2),   # T.Zamtrios Piel
         (1359, 4),   # T.Zamtrios Grandfin
         (1360, 4),   # T.Zamtrios Sawtooth+
         (1361, 5)]   # T.Zamtrios Tailbrand
# the other 4U items of Tigerstripe's carve, break and reward tables -> GU items of the same name (checked by name)
OTHER_4U_GU = {1604: 455,     # Omniplegia Sac
               824: 2123,     # Large Toad Tear (shiny drop)
               1607: 927,     # Paddock Cream
               1613: 426,     # Massive Bone
               1635: 330,     # Eltalite Ore
               216: 329,      # Carbalite Ore
               276: 427,      # Dragonbone Relic
               185: 280,      # Hot Pepper
               958: 342,      # Lazurite Jewel
               228: 349,      # Hard Armor Sphere
               229: 350,      # Heavy Armor Sphere
               37: 354,       # Shining Charm
               38: 355}       # Timeworn Charm
NO_GU_4U = {135, 147}         # Stam Nectar: Water, Power+ Nectar: Fire (m10821 row B): GU has no nectars
MATERIALS = items4u.Materials('tigerstripe_zamtrios', ITEMS, (), OTHER_4U_GU, NO_GU_4U)
GU_FIRST = MATERIALS.gu_first
gu_item = MATERIALS.gu_item
# break rewards (module/items.c bui_record): 4U G tables from 0xf37ba0 (pointer [0xf386c0 + 4 * (928 + 4 * group +
# 3)], em 92 base 928), groups 0..5. GU condition = 10 * (GU break group + 1); GU em067's own break record holds the
# same kind of table at conds 10 / 20 / 30 / 40 / 50 as 4U groups 0 / 2 / 3 / 4 / 5 (head Sawtooth+, top fin
# Grandfin, tail Tailbrand; m10821's "dorsal fin" subquest = 4U group 3). 4U group 1 (Frenzy crystals, given when
# the hunter overcomes its frenzy) has no GU part: left out.
BREAKS_4U, BREAKS_4U_PTR = 0xf37ba0, 0xf3954c
BREAK_CONDS = [10, None, 20, 30, 40, 50]


def breaks_4u(exe):
    """[(GU cond, [(chance, count, GU item)])]"""
    return items4u.breaks(exe, BREAKS_4U, BREAKS_4U_PTR, BREAK_CONDS, gu_item)


def main():
    exe = open(EXE, 'rb').read()
    text = {lang: text_4u(lang) for lang in LANGS}
    sec = MATERIALS.item_section(exe, text)
    bui = items4u.bui_section(breaks_4u(exe))
    if sys.argv[1:] == ['show']:
        for s in (sec, bui): print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in (sec, bui): print('wrote', portdata.write_section('tigerstripe_zamtrios', s))


if __name__ == '__main__':
    main()
