"""hagi_em090.py : Dalamadur / Shah Dalamadur carve tables from 4U for the four arcs (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4, tools/hagi4u.py: s1 Low, s2 High, s4 G; a rank without 4U tables = GU's filler).

  hagi_em090.py       print the tables of every entry

4U (C, hagi4u.carve_record_4u / shiny_record_4u; plan.md goal F): head em024 / em110 carve point 0 = the body; tail
em083 / em111 point 0 = the tail half's body, point 1 = the severed tail (GU kind 'tail' of the half that is cut);
shiny drop set 0 when 4U has one (0x930bdc gives set 0 to every em but 17/18/22/44/50/66/67/89). Items through
items_em090 (the appended materials) and its OTHER_4U_GU.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core tools
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import hagi4u, items_em090
from hagi4u import KIND_BYTE, FILLER_4U
from romfs import RomFS

# entry -> (4U em, carve points by GU kind: None = the body table, 'tail' = the severed tail)
ENTRIES = {'dalamadur': (24, {None: 0}), 'shah_dalamadur': (110, {None: 0}),
           'dalamadur_tail': (83, {None: 0, 'tail': 1}), 'shah_dalamadur_tail': (111, {None: 0, 'tail': 1})}
RANK_FIELD = {1: 47, 2: 48, 3: 50}                  # 4U rank column (low, high, G) -> manifest field (s1, s2, s4)


def tables_of(exe, rec, gu_item):
    """4U record -> {4U rank: [(count, chance, GU item)]} for the ranks that have a table"""
    out = {}
    for rank, a in zip((1, 2, 3), hagi4u.record_4u(exe, rec)[:3]):
        if not hagi4u.EXE_BASE <= a < hagi4u.EXE_BASE + len(exe): continue   # none (or not a table: em 24's
        # shiny base reads past the shiny records)
        t = hagi4u.table_4u(exe, a)
        if not t or t == [(1, 100, FILLER_4U)]: continue
        out[rank] = [(n, c, gu_item(item)) for n, c, item in t]
        assert all(i is not None for _, _, i in out[rank]), (hex(rec), rank, t)
    return out


def files(name, exe=None, gu_item=None):
    """{manifest field: data} for fields 46..50 of the entry's arc"""
    exe = exe or hagi4u.exe()
    if gu_item is None:
        gu_item = items_em090.materials(RomFS(paths.GU_ROMFS), exe).gu_item
    em, points = ENTRIES[name]
    kinds = {k: tables_of(exe, hagi4u.carve_record_4u(exe, em, p), gu_item) for k, p in points.items()}
    kinds['shiny'] = tables_of(exe, hagi4u.shiny_record_4u(exe, em, 0), gu_item)
    filler = hagi4u.filler()
    out = {f: filler for f in range(46, 51)}
    for rank, field in RANK_FIELD.items():
        if rank not in kinds[None]: continue
        tables, index = [kinds[None][rank]], {}
        for k in ('tail', 'shiny'):
            if rank in kinds.get(k, {}):
                index[KIND_BYTE[k]] = len(tables)
                tables.append(kinds[k][rank])
        out[field] = hagi4u.hagi(tables, index)
    return out


if __name__ == '__main__':
    exe = hagi4u.exe()
    gi = items_em090.materials(RomFS(paths.GU_ROMFS), exe).gu_item
    for name in ENTRIES:
        print(name)
        hagi4u.show(files(name, exe, gi))
