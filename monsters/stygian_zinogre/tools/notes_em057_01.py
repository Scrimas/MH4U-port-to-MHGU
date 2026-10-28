"""notes_em057_01.py : Stygian Zinogre in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em057_01.py          write the sections

Description = 4U emExp[49] (C). No tips page: no 4U HunterNote string names Stygian Zinogre or Zinogre (C, scan of
the eng table). Record as GU's Zinogre entry 93 (type 12, capturable, size records shown), listed right after it, so
before Thunderlord Zinogre (94) (GU lists every variant next to its base). Threat 6: GU's subspecies entries sit at 6
over bases of 4 / 5 (Tigerstripe's rule; Zinogre is 5, Thunderlord 6) (S: 4U's own value not located). Unlocked by
clearing his first quest (allocations.toml quests[0] = 10775, 4U m10603).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'stygian_zinogre'
EM4U = 49                                # 4U em number = emName / emExp index
ZINOGRE = 93                             # GU's Zinogre entry (name entry 44, em 0x39)
THREAT = 6


def main():
    gu = notes4u.gu_record(ZINOGRE)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, ZINOGRE, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(44, 0x39))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
