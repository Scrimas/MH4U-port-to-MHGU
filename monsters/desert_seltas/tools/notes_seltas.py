"""notes_seltas.py : Desert Seltas and Desert Seltas Queen in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA of each entry
(gen/[<entry>/]*-notes.sec; tools/notes4u.py for the tables and the format).

  notes_seltas.py          write the sections
  notes_seltas.py show     print them only

Description = 4U emExp[94] / [95]. No tips page: GU's Seltas / Seltas Queen pages are GU's own texts about the normal ones.
Records as GU's Seltas / Seltas Queen entries, each listed right after its species (GU lists every variant next to its base). Threat: 6, the earlier
ports' value for a 4U subspecies at G rank (4U's own value not located, G). Their entries 132 / 133 are past the save map: module/notes.c shows each
as soon as any of its quests is cleared (Desert Seltas' also when one of the Queen's is: guest_in) and writes nothing; the quest here (quests[0]) is
only what the unlock table of the record names.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, notes4u

THREAT = 6
# entry: (4U em number = emName / emExp index, GU species' name entry = registry index, GU em ID)
ENTRIES = {'desert_seltas': (94, 61, 0x4c), 'desert_seltas_queen': (95, 58, 0x45)}


def gu_entry(index, gid):
    """GU's Hunter's Notes entry of the species"""
    hits = [k for k in range(notes4u.N) if notes4u.gu_record(k)[:2] == (index, gid)]
    assert len(hits) == 1, hits
    return hits[0]


def main():
    for name, (em4u, index, gid) in ENTRIES.items():
        after = gu_entry(index, gid)
        gu = notes4u.gu_record(after)
        kind, large, capturable, sizes = gu[2], gu[6], gu[7], gu[8]
        secs = notes4u.sections(name, kind, THREAT, after, alloc.monster(name)['quests'][0],
                                desc=lambda t, em4u=em4u: t['emExp'][em4u], tips=None, large=large, capturable=capturable,
                                sizes=sizes, check_after=(index, gid))
        notes4u.main(name, secs)


if __name__ == '__main__':
    main()
