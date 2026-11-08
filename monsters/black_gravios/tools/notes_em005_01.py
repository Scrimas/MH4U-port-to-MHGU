"""notes_em005_01.py : Black Gravios in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em005_01.py          write the sections
  notes_em005_01.py show     print it only

Description = 4U emExp[41]. No tips page: 4U's HunterNote and HunterNoteEQ have no string naming Gravios (C), and GU
Gravios' page is GU's own text about Gravios.
Record as GU's Gravios entry 117 (type 11, capturable, size records shown), listed right after it (GU lists every
variant next to its base). Threat 6: GU's subspecies entries (IDs 0x201, 0x202, 0x401, 0x402, 0x407) sit at 6 over bases
of 4 / 5, Gravios is 5 (S: GU's rule, 4U's own value not located). His entry 128 is past the save map: module/notes.c
shows it as soon as any of his quests is cleared and writes nothing; the quest here (quests[0]) is only what the unlock
table of the record names.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/black_gravios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'black_gravios'
EM4U = 41                                # 4U em number = emName / emExp index
GRAVIOS = 117                            # GU's Gravios entry (name entry 113, em 0x5)
THREAT = 6


def main():
    gu = notes4u.gu_record(GRAVIOS)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, GRAVIOS, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(113, 0x5))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
