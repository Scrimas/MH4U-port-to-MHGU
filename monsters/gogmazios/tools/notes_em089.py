"""notes_em089.py : Gogmazios in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(gen/*-notes.sec, tools/portdata.py; module/notes.c).

  notes_em089.py          write the sections
  notes_em089.py show     print it only

GU 1.4 main (tools/gu.py), C unless noted:
  - list 0x162d9f0, 123 x 16 B, reached only through data word 0x183ec4c: +0 u8 monsterName entry (name, 0x55bc4c
    bank 3), +4 u16 em ID (icon via 0x560ca4), +6 type (Elder Dragon 13), +7 threat stars, +8 / +10 u16
    HN_MonsterListMsg strings (description, tips page; 0xffff = none), +12 3 large / 2 small, +13 capturable,
    +14 size records shown.
  - unlock conditions 0x162d1f8, 123 x 8 B {u32 value, u8 kind}: kind 2 = quest `value` cleared (0x523da4, quest-list
    lookup), tested by talk condition 44 and set by talk action 6 (0x245848 / 0x247ae4).
  - display order 0x1631ef4, 123 x u32 entry numbers (0x5b0b48), grouped by type; Elder Dragons last.
  - save: 128-bit map S+0x35b0 (+ NEW copy S+0x35c0), bits 123..127 unused -> entry 123 = Gogmazios.
  Every loop over the list is bounded by an immediate (module/build.py WORD_PATCHES, 123 -> 124); two of them are
  unrolled by two and read one record past the end, so the copy carries a padding record (em 0xffff, type 0xff).
4U sources (core_common lmd, 5 languages): description = emExp[89] (GU's description of a monster both games have is
4U's emExp text, e.g. Kushala); tips page = 4U's Gogmazios tip HunterNote[435] under its title HunterNote[179]
("Tar"), in GU's "title\\r\\n\\r\\nbody" page layout.
Choices: unlocked by clearing quest 11491 (G4 "Quagmire Quarrel"); not capturable, no size records (fixed size, as
4U); threat THREAT (see there); shown after Nakarkos, before Fatalis.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gu, portdata
from gear_em089 import text4u, gu_str, LANGS

LIST, UNLOCK, ORDER, N = 0x162d9f0, 0x162d1f8, 0x1631ef4, 123
EM4U = 89                                # 4U em number = emName / emExp index
import alloc
ALLOC = alloc.monster('gogmazios')
NAME_ENTRY, EM_ID, TYPE_ELDER = ALLOC['name_entry'], ALLOC['em_id'], 13
assert ALLOC['notes_entry'] == N, 'this tool appends the entry right after the GU list (first ported monster only)'
THREAT = 8                               # G: 4U's own value not located; GU gives 8 to the final elders
TEXT_FIRST = 220                         # = the HN_MonsterListMsg string count
QUEST = ALLOC['quests'][0]               # its first quest (11491) unlocks the entry
AFTER = 102                              # Nakarkos' entry: Gogmazios is listed right after it


def main():
    M = bytes(gu.MEM)
    lst = M[LIST:LIST + 16 * N]
    order = list(struct.unpack_from('<%dI' % N, M, ORDER))
    assert sorted(order) == list(range(N)) and struct.unpack_from('<IH', lst, 16 * AFTER) == (69, 0x54)
    # NOTE: list record, unlock record, the entry it is listed after (module/notes.c builds the tables from GU's)
    note = portdata.Section('NOTE')
    note.raw(struct.pack('<IHBBHHBBBB', NAME_ENTRY, EM_ID, TYPE_ELDER, THREAT, TEXT_FIRST, TEXT_FIRST + 1, 3, 0, 0, 0))
    note.raw(struct.pack('<IB3x', QUEST, 2))
    note.u32(AFTER)
    # its two HN_MonsterListMsg strings: description, tips page
    strs = []
    for lang in LANGS:
        t = text4u(lang)
        strs.append([gu_str(t['emExp'][EM4U]), gu_str(t['HunterNote'][179] + '\n\n' + t['HunterNote'][435])])
    secs = [note, portdata.txta([('HN_MonsterListMsg', TEXT_FIRST, strs)])]
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section('gogmazios', s, 'notes'))


if __name__ == '__main__':
    main()
