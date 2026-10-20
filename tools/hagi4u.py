"""hagi4u.py : MH4U carve tables -> GU carve files (enemy\\hagi\\hagi_s0..s4_<em>, monster arc manifest fields 46-50),
shared by the monsters' carve tools (monsters/<name>/tools/hagi_*.py).

GU format (346 B, MHGU_Editor tools/monster_carves.py; rHagi load 0x39ad9c checks the magic and copies the rest):
  +0  03 01 12 14, u16 (above the used entries in every GU file; 16 in GU's filler files), then 20 index bytes:
      +6 / +7 body table of sets 2 / 3 (set 1 = table 0), +8 + 3k + j table of kind k set j (k 0 tail, 1 broken part,
      2 shiny drop, 3 other, 4 dropped / mined); ff = none
  +26 80 x {u16 count << 8 | chance %, u16 item}, each table closed by ffff 0000, the rest ffff 0000.
  s1 Low, s2 High, s4 G rank; a rank the monster is not in holds GU's filler (one First-aid Med 1716 at 100 %).
4U v1.1 (dump/exefs_v11/mem.bin, loaded at 0x100000): body, tail and shiny arrays of 16-byte per-monster records
{low, high, G, filler} pointing at tables in GU's own entry format (filler column = 4U's First-aid Med 769 or null).
These records are slots of one pointer table (0x926044, 0x911f58): u32 [TABLES_4U + 4 * idx], idx = base + rank
(1 low, 2 high, 3 G; the "filler" column is the next base's rank 0). Carve point c of monster em: 16-B records
from u32 [CARVE_POINTS_4U + 4 * em], u16 +0 = base (carve_record_4u); shiny drop set s: base = u16 [SHINY_4U + 2 * em]
+ 4 * s (shiny_record_4u).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from items4u import EXE, EXE_BASE

KIND_BYTE = {'tail': 8 + 3 * 0, 'broken': 8 + 3 * 1, 'shiny': 8 + 3 * 2}   # set 1 of a GU kind (+1: set 2)
FILLER = 1716                                            # GU First-aid Med
FILLER_4U = 769                                          # 4U First-aid Med
SIZE, ENTRIES, SPARE = 346, 80, 14                       # u16 = used entries + 14, as GU's filler (2 + 14)
TABLES_4U, CARVE_POINTS_4U, SHINY_4U = 0x1002a5c, 0x1003bec, 0x1003ddc


def table_4u(exe, a):
    """4U carve table at address a -> [(count, chance %, 4U item)]"""
    out = []
    while True:
        x, item = struct.unpack_from('<HH', exe, a - EXE_BASE)
        if x == 0xFFFF: return out
        out.append((x >> 8, x & 0xFF, item))
        a += 4


def record_4u(exe, rec):
    """a 16-byte per-monster record -> (low, high, G, filler) table addresses (0 = none)"""
    return struct.unpack_from('<4I', exe, rec - EXE_BASE)


def carve_record_4u(exe, em, point=0):
    """address of the record_4u record of 4U monster em's carve point `point`"""
    pts = struct.unpack_from('<I', exe, CARVE_POINTS_4U + 4 * em - EXE_BASE)[0]
    base = struct.unpack_from('<H', exe, pts + 16 * point - EXE_BASE)[0]
    return TABLES_4U + 4 * (base + 1)


def shiny_record_4u(exe, em, set_=0):
    """address of the record_4u record of 4U monster em's shiny drop set `set_`"""
    return TABLES_4U + 4 * (struct.unpack_from('<H', exe, SHINY_4U + 2 * em - EXE_BASE)[0] + 4 * set_ + 1)


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


def filler():
    """GU's carve file for a rank the monster is not in"""
    return hagi([[(1, 100, FILLER)]], {})


def show(files):
    for k, d in files.items():
        v = struct.unpack_from('<%dH' % (2 * ENTRIES), d, 26)
        print('field %d: u16 %d, index %s' % (k, struct.unpack_from('<H', d, 4)[0], d[6:26].hex(' ')))
        print('   ', [(x >> 8, x & 0xFF, it) for x, it in zip(v[0::2], v[1::2]) if x != 0xFFFF])


def exe():
    return open(EXE, 'rb').read()
