"""notes_em007_01.py : Monoblos in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em007_01.py          write the sections
  notes_em007_01.py show     print it only

Description = 4U emExp[101]. No tips page: 4U's HunterNote has no string naming Monoblos (C), and GU Diablos' page is
GU's own text about Diablos.
Record as GU's Diablos entry 112 (type 11, capturable, size records shown), listed right after it (GU lists every
variant next to its base). Threat 5 = GU's Diablos (Black Diablos is 6; S: a sibling species of Diablos' tier, 4U's own
value not located). His entry 129 is past the save map: module/notes.c shows it as soon as any of his quests is cleared
and writes nothing; the quest here (quests[0]) is only what the unlock table of the record names.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'monoblos'
EM4U = 101                               # 4U em number = emName / emExp index
DIABLOS = 112                            # GU's Diablos entry (name entry 114, em 0x7)
THREAT = 5


def main():
    gu = notes4u.gu_record(DIABLOS)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, DIABLOS, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(114, 0x7))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
