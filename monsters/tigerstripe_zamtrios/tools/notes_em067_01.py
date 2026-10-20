"""notes_em067_01.py : Tigerstripe Zamtrios in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em067_01.py          write the sections
  notes_em067_01.py show     print it only

Description = 4U emExp[92]. No tips page: 4U's HunterNote has no Zamtrios / Tigerstripe tip, and GU Zamtrios' page
(HN_MonsterListMsg 123, "Shave That Ice!") is about the ice armor Tigerstripe lacks.
Record as GU's Zamtrios entry 55 (type 6, capturable, size records shown), listed right after it (GU lists every
variant next to its base). Threat 6: GU's subspecies entries (IDs 0x201 / 0x202) sit at 6 over bases of 4 / 5,
Zamtrios is 4 (S: GU's rule, 4U's own value not located). Unlocked by clearing its first quest.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tigerstripe_zamtrios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'tigerstripe_zamtrios'
EM4U = 92                                # 4U em number = emName / emExp index
ZAMTRIOS = 55                            # GU's Zamtrios entry (name entry 56, em 0x43)
THREAT = 6


def main():
    gu = notes4u.gu_record(ZAMTRIOS)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, ZAMTRIOS, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(56, 0x43))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
