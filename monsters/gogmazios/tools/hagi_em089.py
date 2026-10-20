"""hagi_em089.py : Gogmazios carve tables from 4U for the em089 arc (manifest fields 46-50 =
enemy\\hagi\\hagi_s0..s4_em089_00, tools/build_em089_arc.py). See notes/content-plan.md "Rewards".

  hagi_em089.py       print the tables

GU format (346 B, MHGU_Editor tools/monster_carves.py; rHagi load 0x39ad9c checks the magic and copies the rest):
  +0  03 01 12 14, u16 (above the used entries in every GU file; 16 in GU's filler files), then 20 index bytes:
      +6 / +7 body table of sets 2 / 3 (set 1 = table 0), +8 + 3k + j table of kind k set j (k 0 tail, 1 broken part,
      2 shiny drop, 3 other, 4 dropped / mined); ff = none
  +26 80 x {u16 count << 8 | chance %, u16 item}, each table closed by ffff 0000, the rest ffff 0000.
  s1 Low, s2 High, s4 G rank; a rank the monster is not in holds GU's filler (one First-aid Med 1716 at 100 %).
4U v1.1 (dump/exefs_v11/mem.bin, loaded at 0x100000): body, tail and shiny arrays of 16-byte per-monster records
{low, high, G, filler} (array bases not traced; column meaning inferred from em089's); em089's records at
0x1002f70 / 0x1003340 / 0x10038b0 point to G tables in GU's own entry format. Low / high are null (G-only monster),
the filler column is 4U's First-aid Med (769) or null.
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
import items_em089

EXE = os.path.join(ROOT, 'dump/exefs_v11/mem.bin')
EXE_BASE = 0x100000
RECORDS_4U = {'body': 0x1002f70, 'tail': 0x1003340, 'shiny': 0x10038b0}
SHINY_SET0_4U = 0x10038a8                                # u32 -> 4U shiny set 0, G (One-shot Binder)
KIND_BYTE = {'tail': 8 + 3 * 0, 'shiny': 8 + 3 * 2}      # set 1 of GU kinds 0 / 2 (+1: set 2)
FILLER = 1716                                            # GU First-aid Med
SIZE, ENTRIES, SPARE = 346, 80, 14                        # u16 = used entries + 14, as GU's filler (2 + 14)


def table_4u(exe, a):
    out = []
    while True:
        x, item = struct.unpack_from('<HH', exe, a - EXE_BASE)
        if x == 0xFFFF: return out
        out.append((x >> 8, x & 0xFF, item))
        a += 4


def hagi(tables, index):
    """tables: list of [(count, chance, GU item)]; index: {header byte: table number}"""
    ents = []
    starts = []
    for t in tables:
        assert sum(c for _, c, _ in t) == 100, t
        starts.append(len(ents))
        ents += [struct.pack('<HH', n << 8 | c, item) for n, c, item in t] + [struct.pack('<HH', 0xFFFF, 0)]
    assert len(ents) <= ENTRIES
    head = bytearray(b'\x03\x01\x12\x14' + struct.pack('<H', len(ents) + SPARE) + b'\xff' * 20)
    for byte, t in index.items(): head[byte] = starts[t]
    d = bytes(head) + b''.join(ents) + struct.pack('<HH', 0xFFFF, 0) * (ENTRIES - len(ents))
    assert len(d) == SIZE
    return d


def files():
    """{manifest field: data} for fields 46..50 (hagi s0..s4)"""
    exe = open(EXE, 'rb').read()
    g = {}
    for kind, rec in RECORDS_4U.items():
        low, high, gp, filler = struct.unpack_from('<4I', exe, rec - EXE_BASE)
        assert low == 0 and high == 0 and (not filler or table_4u(exe, filler) == [(1, 100, 769)]), kind  # First-aid Med
        g[kind] = [(n, c, items_em089.gu_item(item)) for n, c, item in table_4u(exe, gp)]
    binder = [(n, c, items_em089.gu_item(item))
              for n, c, item in table_4u(exe, struct.unpack_from('<I', exe, SHINY_SET0_4U - EXE_BASE)[0])]
    filler = hagi([[(1, 100, FILLER)]], {})
    s4 = hagi([g['body'], g['tail'], g['shiny'], binder],
              {KIND_BYTE['tail']: 1, KIND_BYTE['shiny']: 3, KIND_BYTE['shiny'] + 1: 2})
    return {46: filler, 47: filler, 48: filler, 49: filler, 50: s4}


if __name__ == '__main__':
    for k, d in files().items():
        v = struct.unpack_from('<%dH' % (2 * ENTRIES), d, 26)
        print('field %d: u16 %d, index %s' % (k, struct.unpack_from('<H', d, 4)[0], d[6:26].hex(' ')))
        print('   ', [(x >> 8, x & 0xFF, it) for x, it in zip(v[0::2], v[1::2]) if x != 0xFFFF])
