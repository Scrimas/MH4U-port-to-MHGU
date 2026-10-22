"""notes_em090.py : Dalamadur in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format; as Gogmazios' notes_em089.py).

  notes_em090.py          write the sections
  notes_em090.py show     print it only

4U text: description = emExp[24] (C). No tips page: no 4U HunterNote string names Dalamadur (C, scan of the eng
table). Choices (G, as Gogmazios): elder dragon list type, threat 8 (GU's final elders), not capturable, no size
records; listed after Nakarkos (102), so before Gogmazios (whose data file loads first and anchors there too);
unlocked by clearing the entry's first quest. Shah Dalamadur (notes_entry 126): description = emExp[110] (C), the
same choices, listed right after Dalamadur's entry (module/notes.c anchors on any placed entry; Dalamadur's data file
loads first, registry order), unlocked by his first quest (11495, m11030).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

EM4U = {'dalamadur': 24, 'shah_dalamadur': 110}   # 4U em number = emName / emExp index
TYPE_ELDER = 13
THREAT = 8
AFTER = 102                              # Nakarkos' entry (name entry 69, em 0x54)


def main():
    for name in ('dalamadur', 'shah_dalamadur'):
        after = AFTER if name == 'dalamadur' else alloc.monster('dalamadur')['notes_entry']
        secs = notes4u.sections(name, TYPE_ELDER, THREAT, after, alloc.monster(name)['quests'][0],
                                desc=lambda t, em=EM4U[name]: t['emExp'][em], tips=None,
                                check_after=(69, 0x54) if name == 'dalamadur' else None)
        notes4u.main(name, secs)


if __name__ == '__main__':
    main()
