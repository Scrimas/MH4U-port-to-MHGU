"""items_em089.py : Gogmazios materials and break rewards for module/items.c -> data file sections ITEM, BUI
(gen/ITEM.sec, gen/BUI.sec; tools/portdata.py). See notes/content-plan.md "Rewards".

  items_em089.py          write the sections
  items_em089.py show     print them only

GU slots: the unused "DUMMY" items 2977.. (name DUMMY, rarity 1, icon 1, in no recipe / reward / carve table), and
for the Arcane jewels the unused DUMMY decorations 2889.. (type 3, icon 44, sell 40; decoData ends at 2888, so
tools/gear_em089.py appends their decoData / decoCreate records).
4U sources (v1.1):
- item table: 20-byte records at 0xf029e4 in dump/exefs_v11/mem.bin (loaded at 0x100000): type, rarity-1, ?, carry,
  icon, colour, u16 sort, u32 flags, u32 sell, u32 buy. 4U and GU share the icon and colour numbers (1033 of the
  1073 items both games name the same have the same icon; colours match likewise).
- text: core_common.arc msg/itemName_<lang> / itemExp_<lang> (lmd), entry = 4U item id, 5 languages.
Category (GU file +0x1b, meaning not traced) is not in 4U's record: copied from the Daora G item with the same icon
(scale 2, shell 3, claw 4, horn 5, wing 4, tail 5, gem 9, scrap 1; Elder Dragon Blood 0 for the oil).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import arc, portdata

EXE = os.path.join(ROOT, 'dump/exefs_v11/mem.bin')
EXE_BASE, ITEM_TABLE = 0x100000, 0xf029e4
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')     # order of em089_item_text in items.c
import alloc
ALLOC = alloc.monster('gogmazios')
GU_FIRST = ALLOC['items'][0]                    # allocations.toml items = [first, last]
# (4U id, GU category)
ITEMS = [(1528, 2),   # Battlement (scale)
         (1529, 3),   # Fortress (shell)
         (1530, 5),   # Gasher (horn-like blade)
         (1531, 4),   # Offenders (claws)
         (1532, 4),   # Fiberwing
         (1533, 5),   # Briartail
         (1534, 9),   # Wartorn Dragonsphire (gem)
         (1535, 0),   # Heavy Drakesbone Oil (fluid)
         (1713, 1)]   # Gogmazios Scrap+ (Palico)
DUMMY_ICON, DUMMY_SELL = 1, 0            # what items.c expects in a DUMMY material slot
# Arcane jewels: (4U id, GU id); category 0 and the DUMMY decoration's icon / sell checked by items.c
DECOS = [(1838, 2889), (1839, 2890), (1840, 2891), (1841, 2892)]
assert GU_FIRST + len(ITEMS) - 1 == ALLOC['items'][1], 'allocations.toml items does not match ITEMS'
assert [g for _, g in DECOS] == list(range(ALLOC['decorations'][0], ALLOC['decorations'][1] + 1))
DECO_DUMMY_ICON, DECO_DUMMY_SELL = 44, 40
# the other 4U items of Gogmazios' carve and reward tables -> GU items of the same name, except Strong Armor Sphere
# (4U rarity 8), which GU lacks: King Armor Sphere (GU rarity 8)
OTHER_4U_GU = {1608: 419,     # Lrg ElderDragon Bone
               281: 442,      # Elder Dragon Blood
               229: 350,      # Heavy Armor Sphere
               1643: 351,     # Strong Armor Sphere -> King Armor Sphere
               38: 355,       # Timeworn Charm
               1648: 356,     # Enduring Charm
               959: 343,      # Adamant Orb
               1642: 344,     # Sovereign Orb
               830: 2133,     # Old Dragon Treasure
               782: 1731}     # One-shot Binder (shiny drop set 0, tools/hagi_em089.py)
NO_GU_4U = {1721}             # Conqueror's Seal G (m11035 row B, 3 %): a 4U-only material, GU has no seal
# break rewards (module/items.c bui_record): 4U G tables at 0xf37a8e (pointer at 0xf3946c), 6-byte {u16 chance,
# u16 item, u16 count} closed by 0xFFFF, in the order Head, Wing, Breast, Back (kiranico.com/en/mh4u monster page
# data, same items and chances). GU condition = table 0x162a736 [10, 20, .., 60][break group]; em089_break.c groups:
# head (part 0) 1, wings 2, back (part 1) 3, tail tip 4 (no 4U reward), chest (part 7) 5. Part names = Kiranico's
# stagger list order (part 1 back, part 7 chest; test 2026-10-20 10:01: the chest break completed "Wound back").
BREAKS_4U, BREAKS_4U_PTR = 0xf37a8e, 0xf3946c
BREAK_CONDS = [20, 30, 60, 40]


def breaks_4u(exe):
    """[(GU cond, [(chance, count, GU item)])]"""
    assert struct.unpack_from('<I', exe, BREAKS_4U_PTR - EXE_BASE)[0] == BREAKS_4U
    out, a = [], BREAKS_4U - EXE_BASE
    for cond in BREAK_CONDS:
        ents = []
        while struct.unpack_from('<H', exe, a)[0] != 0xFFFF:
            chance, item, count = struct.unpack_from('<HHH', exe, a)
            ents.append((chance, count, gu_item(item)))
            a += 6
        a += 2
        assert sum(e[0] for e in ents) == 100, ents
        out.append((cond, ents))
    return out


def gu_item(k):
    """GU item ID of 4U item k (None: no GU item, NO_GU_4U)"""
    for i, (k4, _) in enumerate(ITEMS):
        if k4 == k: return GU_FIRST + i
    return None if k in NO_GU_4U else OTHER_4U_GU[k]


def lmd(d):
    """4U lmd message file: header <4sHH7I>; idx n x (u32 hash, u16 first op, u16); ops 16 B (kind 1 = string,
    22 = end); string table 12 B (u32 offset, u32 chars, u32) UTF-16LE."""
    _, _, _, n, n_ops, n_str, o_idx, o_ops, o_str, _ = struct.unpack_from('<4sHH7I', d, 0)
    strs = []
    for k in range(n_str):
        off, chars, _ = struct.unpack_from('<3I', d, o_str + 12 * k)
        strs.append(d[off:off + 2 * chars].decode('utf-16le').rstrip('\0'))
    out = []
    for k in range(n):
        _, j, _ = struct.unpack_from('<IHH', d, o_idx + 8 * k)
        s = ''
        while j < n_ops:
            kind, val = struct.unpack_from('<2I', d, o_ops + 16 * j)
            if kind == 22: break
            s += strs[val] if kind == 1 else '\0<tag %d>' % kind     # tags: refused in gu_str

            j += 1
        out.append(s)
    return out


def item_4u(exe, k, kind=0):
    t, rare, _, carry, icon, col, _, _, sell, buy = struct.unpack_from('<6BHIII', exe, ITEM_TABLE - EXE_BASE + 20 * k)
    assert t == kind and carry == 99, 'unexpected 4U record %d' % k
    return rare + 1, icon, col, sell, buy


def text_4u(lang):
    d = open(os.path.join(ROOT, 'dump/romfs/%s/data/core_common.arc' % lang), 'rb').read()
    f = {e[0].split('\\')[-1]: arc.arc_read(d, e) for e in arc.arc_entries(d) if '\\msg\\' in e[0]}
    return lmd(f['itemName_' + lang]), lmd(f['itemExp_' + lang])


def gu_str(s):
    """4U item text as GU stores it (CRLF line breaks); markup tags refused"""
    if '\0' in s: sys.exit('4U text with a markup tag, not handled: %r' % s)
    return s.replace('\n', '\r\n')


def main():
    exe = open(EXE, 'rb').read()
    text = {lang: text_4u(lang) for lang in LANGS}
    every = [(k, GU_FIRST + i, cat, 0, DUMMY_ICON, DUMMY_SELL) for i, (k, cat) in enumerate(ITEMS)] + \
            [(k, gu, 0, 3, DECO_DUMMY_ICON, DECO_DUMMY_SELL) for k, gu in DECOS]
    # ITEM: {GU id, rarity, icon, colour, category, DUMMY icon, DUMMY sell, sell, buy}, then name / description
    sec = portdata.Section('ITEM')
    sec.u32(len(every))
    for k, gu, cat, kind, d_icon, d_sell in every:
        rare, icon, col, sell, buy = item_4u(exe, k, kind)
        sec.raw(struct.pack('<HBBBBBxIII', gu, rare, icon, col, cat, d_icon, d_sell, sell, buy))
        print('item %d <- 4U %d %s' % (gu, k, text['eng'][0][k]))
    for lang in LANGS:
        names, exps = text[lang]
        for k, *_ in every:
            sec.str(gu_str(names[k]))
            sec.str(gu_str(exps[k]))
    # BUI: break rewards, groups (GU condition, entries) of the 4U tables Head, Wing, Breast, Back; each group
    # closed by chance 255
    brk = breaks_4u(exe)
    ents = [e for _, es in brk for e in es + [(255, 0, 0)]]
    bui = portdata.Section('BUI ')
    bui.u32(len(brk), len(ents))
    bui.raw(bytes(c for c, _ in brk) + bytes(len(e) for _, e in brk))
    bui.align()
    for chance, count, item in ents:
        bui.raw(struct.pack('<BBH', chance, count, item))
    if sys.argv[1:] == ['show']:
        for s in (sec, bui): print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in (sec, bui): print('wrote', portdata.write_section('gogmazios', s))


if __name__ == '__main__':
    main()
