"""hagi_em057_01.py : Stygian Zinogre carve tables from 4U for the em057_01 arc (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4_em057_01, tools/build_em057_01_arc.py). Format and 4U tables: tools/hagi4u.py; 4U data:
notes/phase1-assets.md 4b.

  hagi_em057_01.py       print the tables

4U em 49 is High and G rank (low null): carve point 0 = body (3 carves), point 1 = tail, one shiny drop set (0x930bdc:
set 0; 4U's "set 1" records are the next monster's). Layout = GU em057_00's own s2 / s4: body = table 0, tail set 1 at
header byte 8, shiny set 1 at byte 14. GU's Zinogre also has a kind-4 ("dropped") table at byte 20 (Fulgurbug 82 %),
GU's own addition with no 4U counterpart: none here (ff, as most GU monsters). s2 = High, s4 = G, s0 / s1 / s3 = GU's
filler; items via tools/items_em057_01.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import hagi4u, items_em057_01
from hagi4u import KIND_BYTE

EM_4U = 49


def files():
    """{manifest field: data} for fields 46..50 (hagi s0..s4)"""
    exe = hagi4u.exe()
    gu_item = items_em057_01.materials().gu_item
    recs = {'body': hagi4u.carve_record_4u(exe, EM_4U, 0), 'tail': hagi4u.carve_record_4u(exe, EM_4U, 1),
            'shiny': hagi4u.shiny_record_4u(exe, EM_4U)}
    t = {}
    for kind, rec in recs.items():
        low, high, g, _ = hagi4u.record_4u(exe, rec)
        assert low == 0 and high and g, kind
        for rank, p in (('high', high), ('g', g)):
            t[kind, rank] = [(n, c, gu_item(item)) for n, c, item in hagi4u.table_4u(exe, p)]
    filler = hagi4u.filler()
    out = {46: filler, 47: filler, 49: filler}
    for field, rank in ((48, 'high'), (50, 'g')):
        out[field] = hagi4u.hagi([t['body', rank], t['tail', rank], t['shiny', rank]],
                                 {KIND_BYTE['tail']: 1, KIND_BYTE['shiny']: 2})
    return out


if __name__ == '__main__':
    hagi4u.show(files())
