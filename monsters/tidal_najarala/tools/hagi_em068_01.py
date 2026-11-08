"""hagi_em068_01.py : Tidal Najarala carve tables from 4U for the em068_01 arc (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4_em068_01, tools/build_em068_01_arc.py). Format and 4U tables: tools/hagi4u.py.

  hagi_em068_01.py       print the tables

4U em 93 is G rank only (low and high null, C, 2026-11-06): carve point 0 = body, one shiny drop set; no tail table (Najarala's
points 1 / 2 read the tables of other monsters, C). Layout = GU em068_00's own s4 (body = table 0, shiny set 1 at header byte 14). s4 =
G, s0..s3 = GU's filler (as Tigerstripe's: she has no quest below G); items via tools/items_em068_01.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import hagi4u, items_em068_01
from hagi4u import KIND_BYTE

EM_4U = 93


def files():
    """{manifest field: data} for fields 46..50 (hagi s0..s4)"""
    exe = hagi4u.exe()
    gu_item = items_em068_01.materials().gu_item
    recs = {'body': hagi4u.carve_record_4u(exe, EM_4U, 0), 'shiny': hagi4u.shiny_record_4u(exe, EM_4U)}
    t = {}
    for kind, rec in recs.items():
        low, high, g, _ = hagi4u.record_4u(exe, rec)
        assert low == 0 and high == 0 and g, kind
        t[kind] = [(n, c, gu_item(item)) for n, c, item in hagi4u.table_4u(exe, g)]
    filler = hagi4u.filler()
    out = {46: filler, 47: filler, 48: filler, 49: filler}
    out[50] = hagi4u.hagi([t['body'], t['shiny']], {KIND_BYTE['shiny']: 1})
    return out


if __name__ == '__main__':
    hagi4u.show(files())
