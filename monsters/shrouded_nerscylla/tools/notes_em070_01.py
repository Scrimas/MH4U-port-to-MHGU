"""notes_em070_01.py : Shrouded Nerscylla in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_em070_01.py          write the sections
  notes_em070_01.py show     print it only

Description = 4U emExp[96]. No tips page: GU Nerscylla's page is GU's own text about Nerscylla.
Record as GU's Nerscylla entry, listed right after it (GU lists every variant next to its base). Threat: Tidal Najarala's and
Tigerstripe's 6 (a 4U subspecies at G rank; 4U's own value not located, G). Her entry 131 is past the save map: module/notes.c shows
it as soon as any of her quests is cleared and writes nothing; the quest here (quests[0]) is only what the unlock table of the record
names.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/shrouded_nerscylla
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

NAME = 'shrouded_nerscylla'
EM4U = 96                                # 4U em number = emName / emExp index
THREAT = 6
GU_INDEX, GU_ID = 126, 0x46              # GU Nerscylla: name entry, em ID


def gu_entry():
    """GU's Hunter's Notes entry of Nerscylla"""
    hits = [k for k in range(notes4u.N) if notes4u.gu_record(k)[:2] == (GU_INDEX, GU_ID)]
    assert len(hits) == 1, hits
    return hits[0]


def main():
    after = gu_entry()
    gu = notes4u.gu_record(after)
    kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
    secs = notes4u.sections(NAME, kind, THREAT, after, alloc.monster(NAME)['quests'][0],
                            desc=lambda t: t['emExp'][EM4U], tips=None, large=large, capturable=capturable,
                            sizes=sizes, check_after=(GU_INDEX, GU_ID))
    notes4u.main(NAME, secs)


if __name__ == '__main__':
    main()
