"""gather_em090.py : the item lists of Dalamadur's runtime gather points -> data file section GPTS of the dalamadur
and shah_dalamadur entries (module: monsters/dalamadur/module/dala_gather.c; facts: notes/plan.md section 6, "Meteor
scale research" / "Mining helper").

  gather_em090.py          write the sections
  gather_em090.py show     print them only

4U (C): a point's list = [0x1002a5c + 4 * (u16 0x1003ed4[em] + 4 * record byte 12 + rank)], {u8 weight, u8 qty, u16
item} closed by weight 0xff (0x9357ec); list 0 = the meteor scale (uShell038, record 0x102fab4), list 1 = the head's
on-body point (record 0xfdc924); em 24 (dalamadur: High and G) and 110 (shah_dalamadur: G only; its High lists are
empty). GU reads the same format (0x31b37c: weighted by the sum of the weights). 4U rank 2 / 3 -> GU rank 2 / 4
(items4u.RANK_4U_GU, the quest rank byte module/items.c reads).
Items: the 4U -> GU mapping of items_em090.py (materials, OTHER_4U_GU), then GU items by name with the ore
substitutes of gear_weapons_em090.py (Yoldspar Ore -> Fucium Ore, Cosmicite Ore -> Meldspar Ore). Gossamite Ore has no
GU item: dropped, its weight added to the list's most likely item (user 2026-10-21: Shattered Omen).
GPTS: u32 n, n x {u8 GU rank, u8 list, u16 0, u32 offset}, then each list {u8 weight, u8 qty, u16 GU item} closed by
{0xff, 0xff, 0}.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, items_em090, portdata      # noqa: E402
from gear_weapons_em090 import SUBSTITUTES          # noqa: E402
from items4u import EXE, EXE_BASE, text_4u          # noqa: E402
from romfs import RomFS                             # noqa: E402

LISTS_4U, LIST_BASE_4U = 0x1002a5c, 0x1003ed4
ENTRIES = {'dalamadur': 24, 'shah_dalamadur': 110}  # head entry -> 4U em
LISTS = (0, 1)                                      # record byte 12: meteor scale, head on-body point
RANKS = (2, 3)                                      # 4U High, G
DROPPED = {214}                                     # Gossamite Ore: no GU item (user 2026-10-21)


def list_4u(exe, em, b12, rank):
    """[(weight, qty, 4U item)] of em's list b12 at 4U rank, [] if none"""
    u16 = lambda a: struct.unpack_from('<H', exe, a - EXE_BASE)[0]
    a = struct.unpack_from('<I', exe, LISTS_4U + 4 * (u16(LIST_BASE_4U + 2 * em) + 4 * b12 + rank) - EXE_BASE)[0]
    out = []
    while a and exe[a - EXE_BASE] != 0xff:
        out.append(struct.unpack_from('<BBH', exe, a - EXE_BASE))
        a += 4
    return out


def gu_list(ents, gu_item, log):
    """4U entries -> GU entries: dropped items' weight to the most likely kept item (first of the highest)"""
    keep = [e for e in ents if e[2] not in DROPPED]
    extra = sum(w for w, _, k in ents if k in DROPPED)
    assert keep and sum(w for w, _, _ in ents) == 100, ents
    top = max(range(len(keep)), key=lambda i: (keep[i][0], -i))
    out = [(w + (extra if i == top else 0), q, gu_item(k)) for i, (w, q, k) in enumerate(keep)]
    if extra: log('  dropped %s, weight %d to %d' % ([k for _, _, k in ents if k in DROPPED], extra, out[top][2]))
    return out


def main():
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    mats = items_em090.materials(R, exe)
    names4u = text_4u('eng')[0]
    by_name = gear4u.gu_item_names(R, [mats])

    def gu_item(k):
        if k in mats.other or any(k4 == k for k4, _ in mats.items): return mats.gu_item(k)
        nm = SUBSTITUTES.get(names4u[k], names4u[k])
        assert nm in by_name, '4U item %d %s: no GU item named %s' % (k, names4u[k], nm)
        return by_name[nm]

    out = []
    for name, em in ENTRIES.items():
        heads, body = [], bytearray()
        lists = [(items4u.RANK_4U_GU[r], b12, list_4u(exe, em, b12, r)) for r in RANKS for b12 in LISTS]
        lists = [x for x in lists if x[2]]
        off = 4 + 8 * len(lists)
        for gu_rank, b12, ents in lists:
            print('%s em %d list %d GU rank %d: 4U %s' % (name, em, b12, gu_rank,
                                                          [(w, q, names4u[k]) for w, q, k in ents]))
            g = gu_list(ents, gu_item, print)
            print('  -> GU %s' % g)
            heads.append(struct.pack('<BBHI', gu_rank, b12, 0, off + len(body)))
            body += b''.join(struct.pack('<BBH', *e) for e in g) + struct.pack('<BBH', 0xff, 0xff, 0)
        sec = portdata.Section('GPTS')
        sec.u32(len(lists))
        sec.raw(b''.join(heads) + bytes(body))
        out.append((name, sec))
    if sys.argv[1:] == ['show']:
        for name, s in out: print(name, s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for name, s in out: print('wrote', portdata.write_section(name, s))


if __name__ == '__main__':
    main()
