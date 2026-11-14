"""items_seltas.py : Desert Seltas' and Desert Seltas Queen's materials and break rewards for module/items.c and module/gear.c -> data file
sections TBLA + TXTA (their items APPENDED after Shrouded Nerscylla's, notes/items-append.md) and BUI4 of each entry (tools/portdata.py,
tools/items4u.py).
  items_seltas.py          write the sections
  items_seltas.py show     print them only
Materials (C, 2026-11-09: 4U item names and their carve / shiny / break tables): the 4U items named for them, in 4U ID order -> GU
3055..3057 (Desert Seltas) and 3058..3062 (the Queen; allocations.toml items). 4U 1396 D.S.QueenConcentrate is GU's own item 1032 (GU's
Seltas Queen gives it), so it is not appended. Their other table items exist in GU under the same English name, but 4U 480 S.Queen Concentrate,
which GU lacks: SUBSTITUTES gives D.S.QueenConcentrate in its place, GU's own choice for its Seltas Queen (4U em026's G break group 0 holds S.Queen
Concentrate 7 % next to D.S.QueenConcentrate 4 %, GU's cond 10 holds D.S.QueenConcentrate 6 % and no S.Queen Concentrate, C). GU category: the most
common category of the GU items with the same icon (Black Gravios' rule).
Break rewards (C): 4U lookup items4u.breaks_em at rank 3 only (4U has both at G rank only: their carve and break tables hold nothing else), mapped to
the GU species' own break record (result.arc bui_s4): Seltas 0x4c conds 10 / 20 = 4U em025's groups 0 general / 2 horn (equal items, GU's chances
of a few retuned), Seltas Queen 0x45 conds 10..50 = 4U em026's groups 0 general / 2 maw / 3, 4 claws / 5 tail. 4U group 1 (and the Queen's 1:
Frenzy crystals) has no GU part, as GU's own records have none. 4U em094's break table ends after group 2, em095's after group 5 (the next em's
groups follow: em095's base = em094's + 12, C).
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
import gear4u, items4u, portdata
from items4u import EXE, LANGS, text_4u
from romfs import RomFS

# 4U IDs (text_4u, C). Order = GU IDs from each entry's first: never reorder once released (saves keep them).
ENTRIES = {
    'desert_seltas': dict(
        em4u=94,
        items=[1388,          # D.Seltas Cortex
               1389,          # D.Seltas Razorwing
               1390],         # D.Seltas Hardhorn
        breaks=[(0, 10), (2, 20)]),
    'desert_seltas_queen': dict(
        em4u=95,
        items=[1397,          # D.S.Queen Cortex
               1398,          # D.S.Queen Pectus+
               1399,          # D.S.Queen Maw
               1400,          # D.S.Queen Hardclaw
               1401],         # D.S.Queen Moonlash
        breaks=[(0, 10), (2, 20), (3, 30), (4, 40), (5, 50)]),
}
# the other 4U items of their break, carve and shiny tables and of the gear recipes -> GU items of the same English name (C, GU itemData_eng)
OTHER_4U_GU = {1396: 1032,   # D.S.QueenConcentrate (GU's own)
               822: 2121,    # Queen Substance
               1624: 539,    # Monster Essence
               1604: 455,    # Omniplegia Sac
               470: 1019,    # Seltas Horn+
               1601: 470}    # Flood Sac
SUBSTITUTES = {480: 1032}    # S.Queen Concentrate (no GU item) -> D.S.QueenConcentrate, as GU's Seltas Queen (docstring)
NO_GU_4U = set()
RANKS_4U = (3,)              # G


def categories(R, exe, items):
    """{4U id: GU category} = the most common category among the GU items with the 4U item's icon"""
    d = gear4u.gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))['table\\itemData']
    names = gear4u.gmd(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    by_icon = collections.defaultdict(collections.Counter)
    for i in range(struct.unpack_from('<I', d, 4)[0]):
        r = d[8 + 44 * i:8 + 44 * (i + 1)]
        if r[4] == 0 and names[2 * i] not in ('DUMMY', ''):           # materials (type 0) with a name
            by_icon[r[0x10]][r[0x1b]] += 1
    out = {}
    for k in items:
        icon = items4u.item_4u(exe, k)[1]
        assert by_icon[icon], '4U item %d: no GU material has icon %d' % (k, icon)
        out[k] = by_icon[icon].most_common(1)[0][0]
    return out


def check_other(R):
    """every OTHER_4U_GU pair has the same English name in both games; every SUBSTITUTES key has no GU item of its name"""
    gn = gear4u.gmd(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    n4 = text_4u('eng')[0]
    bad = [(k, n4[k], g, gn[2 * g]) for k, g in OTHER_4U_GU.items() if n4[k] != gn[2 * g]]
    assert not bad, 'OTHER_4U_GU names differ: %s' % bad
    have = set(gn[0::2])
    assert not [k for k in SUBSTITUTES if n4[k] in have], 'a substituted 4U item is in GU now'


def materials(name, R=None, exe=None):
    R = R or RomFS(paths.GU_ROMFS)
    exe = exe or open(EXE, 'rb').read()
    check_other(R)
    e = ENTRIES[name]
    other = dict(OTHER_4U_GU)
    other.update(SUBSTITUTES)
    for o, oe in ENTRIES.items():          # the other entry's materials (shared recipes, mixed break tables)
        if o == name: continue
        first = __import__('alloc').monster(o)['items'][0]
        other.update({k: first + i for i, k in enumerate(oe['items'])})
    return items4u.Materials(name, [(k, c) for k, c in categories(R, exe, e['items']).items()], (), other, NO_GU_4U)


def main():
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    text = {lang: text_4u(lang) for lang in LANGS}
    show = sys.argv[1:] == ['show']
    for name, e in ENTRIES.items():
        m = materials(name, R, exe)
        out = list(m.append_sections(exe, text, R))
        for rank in RANKS_4U:
            brk = items4u.breaks_em(exe, e['em4u'], e['breaks'], rank, m.gu_item)
            assert len(brk) == len(e['breaks']) and all(i is not None for _, es in brk for _, _, i in es), (name, rank)
            out.append(items4u.bui_section(brk, items4u.RANK_4U_GU[rank]))
        for s in out:
            if show: print(name, s.tag, portdata.decode(s.tag, s.bytes()))
            else: print('wrote', portdata.write_section(name, s))


if __name__ == '__main__':
    main()
