"""hagi_em089.py : Gogmazios carve tables from 4U for the em089 arc (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4_em089_00, tools/build_em089_arc.py). See notes/content-plan.md "Rewards"; format and 4U
records: tools/hagi4u.py.

  hagi_em089.py       print the tables

em089's records at 0x1002f70 / 0x1003340 / 0x10038b0 (body / tail / shiny) point to G tables; low / high are null
(G-only monster), the filler column is 4U's First-aid Med (769) or null.
Shiny drops (C, the item drop 0x911f58): u32 table pointer [0x1002a5c + 4 * (base + 4 * set + rank)], base =
u16 [0x1003ddc + 2 * W+0x1c0] (em 89: 912), rank 1..3 (G = 3), set = 0x930bdc (em 89: 1 when work+0xed == 1, else 0).
Set 1's G table is the shiny record above (0x10038b8 -> 0x10026f2); set 0's (0x10038a8 -> 0x10026ea) is One-shot
Binder 100 % (Kiranico's "Shiny Drops (Ballista)"). The tail break clears work+0xed before its drop (0x8c67f8: One-shot
Binder), the rare tar-drip splash sets it before its drop (0xc908b0: the shiny table).
-> s4 = 4U's G body / tail tables and the shiny tables of sets 0 / 1 in GU's shiny sets 1 / 2 (header bytes 14 / 15,
chosen by GU's enemy vtable slot 149 = em089_drop_set); items via tools/items_em089.py; s0..s3 = GU's filler.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import hagi4u, items_em089
from hagi4u import EXE_BASE, KIND_BYTE

RECORDS_4U = {'body': 0x1002f70, 'tail': 0x1003340, 'shiny': 0x10038b0}
SHINY_SET0_4U = 0x10038a8                                # u32 -> 4U shiny set 0, G (One-shot Binder)


def files():
    """{manifest field: data} for fields 46..50 (hagi s0..s4)"""
    exe = hagi4u.exe()
    g = {}
    for kind, rec in RECORDS_4U.items():
        low, high, gp, filler = hagi4u.record_4u(exe, rec)
        assert low == 0 and high == 0 and (not filler or hagi4u.table_4u(exe, filler) == [(1, 100, hagi4u.FILLER_4U)]), \
            kind
        g[kind] = [(n, c, items_em089.gu_item(item)) for n, c, item in hagi4u.table_4u(exe, gp)]
    binder = [(n, c, items_em089.gu_item(item))
              for n, c, item in hagi4u.table_4u(exe, struct.unpack_from('<I', exe, SHINY_SET0_4U - EXE_BASE)[0])]
    filler = hagi4u.filler()
    s4 = hagi4u.hagi([g['body'], g['tail'], g['shiny'], binder],
                     {KIND_BYTE['tail']: 1, KIND_BYTE['shiny']: 3, KIND_BYTE['shiny'] + 1: 2})
    return {46: filler, 47: filler, 48: filler, 49: filler, 50: s4}


if __name__ == '__main__':
    hagi4u.show(files())
