"""notes_em089.py : Gogmazios in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em089.py          write the sections
  notes_em089.py show     print it only

4U text: description = emExp[89]; tips page = 4U's Gogmazios tip HunterNote[435] under its title HunterNote[179]
("Tar").
Choices: unlocked by clearing quest 11491 (G4 "Quagmire Quarrel"); not capturable, no size records (fixed size, as
4U); threat THREAT (see there); shown after Nakarkos, before Fatalis.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

EM4U = 89                                # 4U em number = emName / emExp index
TYPE_ELDER = 13
THREAT = 8                               # G: 4U's own value not located; GU gives 8 to the final elders
AFTER = 102                              # Nakarkos' entry (name entry 69, em 0x54): Gogmazios is listed right after it


def main():
    secs = notes4u.sections('gogmazios', TYPE_ELDER, THREAT, AFTER, alloc.monster('gogmazios')['quests'][0],
                            desc=lambda t: t['emExp'][EM4U],
                            tips=lambda t: t['HunterNote'][179] + '\n\n' + t['HunterNote'][435],
                            check_after=(69, 0x54))
    notes4u.main('gogmazios', secs)


if __name__ == '__main__':
    main()
