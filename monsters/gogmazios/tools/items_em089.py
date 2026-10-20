"""items_em089.py : Gogmazios materials and break rewards for module/items.c -> data file sections ITEM, BUI
(gen/ITEM.sec, gen/BUI.sec; tools/portdata.py, tools/items4u.py). See notes/content-plan.md "Rewards".

  items_em089.py          write the sections
  items_em089.py show     print them only

Materials in the DUMMY items 2977.., the Arcane jewels in the DUMMY decorations 2889.. (tools/items4u.py).
Category (GU file +0x1b, meaning not traced): copied from the Daora G item with the same icon (scale 2, shell 3,
claw 4, horn 5, wing 4, tail 5, gem 9, scrap 1; Elder Dragon Blood 0 for the oil).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import items4u, portdata
from items4u import EXE, EXE_BASE, ITEM_TABLE, LANGS, lmd, item_4u, text_4u, gu_str     # noqa: F401 (users import them)

# (4U id, GU category)
ITEMS = [(1528, 2),   # Battlement (scale)
         (1529, 3),   # Fortress (shell)
         (1530, 5),   # Gasher (horn-like blade)
         (1531, 4),   # Offenders (claws)
         (1532, 4),   # Fiberwing
         (1533, 5),   # Briartail
         (1534, 9),   # Wartorn Dragonsphire (gem)
         (1535, 0),   # Heavy Drakesbone Oil (fluid)
         (1713, 1)]   # Gogmazios Scrap+ (Palico)
# Arcane jewels: (4U id, GU id); category 0 and the DUMMY decoration's icon / sell checked by items.c
DECOS = [(1838, 2889), (1839, 2890), (1840, 2891), (1841, 2892)]
# the other 4U items of Gogmazios' carve and reward tables -> GU items of the same name, except Strong Armor Sphere
# (4U rarity 8), which GU lacks: King Armor Sphere (GU rarity 8)
OTHER_4U_GU = {1608: 419,     # Lrg ElderDragon Bone
               281: 442,      # Elder Dragon Blood
               229: 350,      # Heavy Armor Sphere
               1643: 351,     # Strong Armor Sphere -> King Armor Sphere
               38: 355,       # Timeworn Charm
               1648: 356,     # Enduring Charm
               959: 343,      # Adamant Orb
               1642: 344,     # Sovereign Orb
               830: 2133,     # Old Dragon Treasure
               782: 1731}     # One-shot Binder (shiny drop set 0, tools/hagi_em089.py)
NO_GU_4U = {1721}             # Conqueror's Seal G (m11035 row B, 3 %): a 4U-only material, GU has no seal
MATERIALS = items4u.Materials('gogmazios', ITEMS, DECOS, OTHER_4U_GU, NO_GU_4U)
GU_FIRST = MATERIALS.gu_first
gu_item = MATERIALS.gu_item
# break rewards (module/items.c bui_record): 4U G tables at 0xf37a8e (pointer at 0xf3946c), 6-byte {u16 chance,
# u16 item, u16 count} closed by 0xFFFF, in the order Head, Wing, Breast, Back (kiranico.com/en/mh4u monster page
# data, same items and chances). GU condition = table 0x162a736 [10, 20, .., 60][break group]; em089_break.c groups:
# head (part 0) 1, wings 2, back (part 1) 3, tail tip 4 (no 4U reward), chest (part 7) 5. Part names = Kiranico's
# stagger list order (part 1 back, part 7 chest; test 2026-10-20 10:01: the chest break completed "Wound back").
BREAKS_4U, BREAKS_4U_PTR = 0xf37a8e, 0xf3946c
BREAK_CONDS = [20, 30, 60, 40]


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
    for s in (sec, bui): print('wrote', portdata.write_section('gogmazios', s))


if __name__ == '__main__':
    main()
