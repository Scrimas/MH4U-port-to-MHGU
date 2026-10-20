"""notes4u.py : a ported monster in the Hunter's Notes large-monster list -> data file sections NOTE + TXTA
(tools/portdata.py; module/notes.c). Used by the monsters' notes tools (monsters/<name>/tools/notes_*.py).

GU 1.4 main (tools/gu.py), C unless noted:
  - list 0x162d9f0, 123 x 16 B, reached only through data word 0x183ec4c: +0 u8 monsterName entry (name, 0x55bc4c
    bank 3), +4 u16 em ID (icon via 0x560ca4), +6 type (Elder Dragon 13), +7 threat stars, +8 / +10 u16
    HN_MonsterListMsg strings (description, tips page; 0xffff = none), +12 3 large / 2 small, +13 capturable,
    +14 size records shown.
  - unlock conditions 0x162d1f8, 123 x 8 B {u32 value, u8 kind}: kind 2 = quest `value` cleared (0x523da4, quest-list
    lookup), tested by talk condition 44 and set by talk action 6 (0x245848 / 0x247ae4).
  - display order 0x1631ef4, 123 x u32 entry numbers (0x5b0b48), grouped by type; Elder Dragons last.
  - save: 128-bit map S+0x35b0 (+ NEW copy S+0x35c0), bits 123..127 unused -> entries 123.. = the ported monsters
    (allocations.toml notes_entry, registry order).
  Every loop over the list is bounded by an immediate (module/build.py WORD_PATCHES); two of them are unrolled by two
  and read one record past the end, so the copy carries a padding record (em 0xffff, type 0xff).
Text: the monster's HN_MonsterListMsg strings (description, tips page if any; allocations.toml [monster.append]
notes_text = their count) appended after GU's 220 and those of the monsters before it (TXTA: module/gear.c appends
them only while the loaded file holds exactly that base).
4U sources: description = emExp[4U em] (GU's description of a monster both games have is 4U's emExp text, e.g.
Kushala); tips page = 4U HunterNote strings in GU's "title\\r\\n\\r\\nbody" page layout.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, gu, portdata
from items4u import LANGS, msg4u, gu_text

LIST, UNLOCK, ORDER, N = 0x162d9f0, 0x162d1f8, 0x1631ef4, 123
GU_TEXT = 220                            # HN_MonsterListMsg strings in GU
UNLOCK_QUEST = 2                         # unlock kind: quest cleared


def gu_record(entry):
    """GU's list record of entry k: (name entry, em ID, type, threat, text 1, text 2, large, capturable, sizes, pad)"""
    return struct.unpack_from('<IHBBHHBBBB', bytes(gu.MEM), LIST + 16 * entry)


def sections(name, kind, threat, after, quest, desc, tips=None, large=3, capturable=0, sizes=0, check_after=None):
    """[NOTE, TXTA] of monster `name`: list type `kind`, `threat` stars, listed after GU entry `after` (check_after =
    its expected (name entry, em ID)), unlocked by clearing `quest`; desc / tips(msg4u dict) -> 4U text, tips None =
    no tips page (0xffff)."""
    a = alloc.monster(name)
    M = bytes(gu.MEM)
    order = list(struct.unpack_from('<%dI' % N, M, ORDER))
    assert sorted(order) == list(range(N))
    if check_after: assert gu_record(after)[:2] == check_after, gu_record(after)
    n_text = 1 + (tips is not None)
    assert a.get('append', {}).get('notes_text') == n_text, 'allocations.toml [monster.append] notes_text = %d' % n_text
    t0 = GU_TEXT + alloc.offset(name, 'notes_text')
    # NOTE: list record, unlock record, the entry it is listed after (module/notes.c builds the tables from GU's)
    note = portdata.Section('NOTE')
    note.raw(struct.pack('<IHBBHHBBBB', a['name_entry'], a['em_id'], kind, threat, t0,
                         t0 + 1 if tips is not None else 0xFFFF, large, capturable, sizes, 0))
    note.raw(struct.pack('<IB3x', quest, UNLOCK_QUEST))
    note.u32(after)
    strs = [[gu_text(desc(msg4u(lang)))] + ([gu_text(tips(msg4u(lang)))] if tips is not None else [])
            for lang in LANGS]
    return [note, portdata.txta([('HN_MonsterListMsg', t0, strs)])]


def main(name, secs):
    """write (or with `show`, print) the sections"""
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section(name, s, 'notes'))
