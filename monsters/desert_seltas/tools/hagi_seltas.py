"""hagi_seltas.py : Desert Seltas' and Desert Seltas Queen's carve tables from 4U for their arcs (manifest fields 46-50 = enemy\\hagi\\hagi_s0..s4_<ours>,
tools/build_seltas_arc.py). Format and 4U tables: tools/hagi4u.py.

  hagi_seltas.py       print the tables

4U em 94 and em 95 are G rank only (low and high null, C, 2026-11-09): carve point 0 = body, shiny set 0 (each em's next point / set is the next
em's own: their records sit one after the other). Layout = GU's own s4 of their species (body = table 0, shiny at header byte 14, C: GU
em076_00 / em069_00 s4); s4 = G, s0..s3 = GU's filler (as Tigerstripe's, Tidal Najarala's and Shrouded Nerscylla's: they have no quest below G);
items via tools/items_seltas.py (the Queen's S.Queen Concentrate -> D.S.QueenConcentrate, its SUBSTITUTES).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import hagi4u, items_seltas
from hagi4u import KIND_BYTE


def files(name):
    """{manifest field: data} for fields 46..50 (hagi s0..s4) of entry `name`"""
    exe = hagi4u.exe()
    em = items_seltas.ENTRIES[name]['em4u']
    gu_item = items_seltas.materials(name).gu_item
    recs = {'body': hagi4u.carve_record_4u(exe, em, 0), 'shiny': hagi4u.shiny_record_4u(exe, em)}
    t = {}
    for kind, rec in recs.items():
        low, high, g, _ = hagi4u.record_4u(exe, rec)
        assert low == 0 and high == 0 and g, (name, kind)
        t[kind] = [(n, c, gu_item(item)) for n, c, item in hagi4u.table_4u(exe, g)]
        assert all(i is not None for _, _, i in t[kind]), (name, kind, t[kind])
    filler = hagi4u.filler()
    out = {46: filler, 47: filler, 48: filler, 49: filler}
    out[50] = hagi4u.hagi([t['body'], t['shiny']], {KIND_BYTE['shiny']: 1})
    return out


if __name__ == '__main__':
    for n in items_seltas.ENTRIES:
        print('==', n)
        hagi4u.show(files(n))
