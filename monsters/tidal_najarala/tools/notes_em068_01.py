"""notes_em068_01.py : Tidal Najarala in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em068_01.py          write the sections
  notes_em068_01.py show     print it only

Description = 4U emExp[93]. No tips page: GU Najarala's page is GU's own text about Najarala.
Record as GU's Najarala entry, listed right after it (GU lists every variant next to its base). Threat: Tigerstripe's 6 (a 4U
subspecies at G rank; 4U's own value not located, G). Her entry 130 is past the save map: module/notes.c shows it as soon as any
of her quests is cleared and writes nothing; the quest here (quests[0]) is only what the unlock table of the record names.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'tidal_najarala'
EM4U = 93                                # 4U em number = emName / emExp index
THREAT = 6
NAJARALA = 68                            # GU's Najarala entry (name entry 57, em 0x44, type 9, threat 4)


def main():
    gu = notes4u.gu_record(NAJARALA)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, NAJARALA, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(57, 0x44))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
