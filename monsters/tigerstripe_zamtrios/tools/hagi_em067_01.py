"""hagi_em067_01.py : Tigerstripe Zamtrios carve tables from 4U for the em067_01 arc (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4_em067_01, tools/build_em067_01_arc.py). Format and 4U tables: tools/hagi4u.py; 4U data:
notes/content-data.md section 2.

  hagi_em067_01.py       print the tables

4U em 92 is G rank only (low / high null): one carve point (base 336, 3 carves, no part: the body; no tail carve, as
em 22 and GU em067_00) and one shiny drop set (0x930bdc returns set 0 for every em outside its special cases).
GU em067_00's s4: body = table 0, shiny sets 1 / 2 at header bytes 14 / 15 (set 2 = Zamtrios' ice-armour drop, Ice
Crystal 75 %), chosen by GU's class. Here both sets hold 4U's shiny table, so whichever set GU's variant-1 code picks
drops 4U's items. s0..s3 = GU's filler; items via tools/items_em067_01.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import hagi4u, items_em067_01
from hagi4u import KIND_BYTE

EM_4U = 92


def files():
    """{manifest field: data} for fields 46..50 (hagi s0..s4)"""
    exe = hagi4u.exe()
    g = {}
    for kind, rec in (('body', hagi4u.carve_record_4u(exe, EM_4U)), ('shiny', hagi4u.shiny_record_4u(exe, EM_4U))):
        low, high, gp, _ = hagi4u.record_4u(exe, rec)
        assert low == 0 and high == 0 and gp, kind
        g[kind] = [(n, c, items_em067_01.gu_item(item)) for n, c, item in hagi4u.table_4u(exe, gp)]
    filler = hagi4u.filler()
    s4 = hagi4u.hagi([g['body'], g['shiny']], {KIND_BYTE['shiny']: 1, KIND_BYTE['shiny'] + 1: 1})
    return {46: filler, 47: filler, 48: filler, 49: filler, 50: s4}


if __name__ == '__main__':
    hagi4u.show(files())
