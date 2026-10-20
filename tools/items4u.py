"""items4u.py : MH4U item records and text -> the data file sections ITEM and BUI (tools/portdata.py; module/items.c).
Shared by the monsters' item tools (monsters/<name>/tools/items_*.py), which list their materials and rewards.

  import items4u
  m = items4u.Materials('gogmazios', items=[(4U id, GU category)], decos=[(4U id, GU id)], other={4U id: GU id},
                        no_gu={4U ids})
  m.gu_item(k)                      GU item ID of 4U item k (None: no GU item)
  m.item_section(exe, text)         ITEM section (text = {lang: text_4u(lang)})
  items4u.breaks(exe, table, ptr, conds, gu_item) / bui_section(breaks)     break rewards -> BUI

GU slots: the unused "DUMMY" items 2977.. (name DUMMY, rarity 1, icon 1, in no recipe / reward / carve table), and
for decorations the unused DUMMY decorations 2889.. (type 3, icon 44, sell 40; decoData ends at 2888, so the
monster's gear tool appends their decoData / decoCreate records). allocations.toml items / decorations give each
monster its range.
4U sources (v1.1):
- item table: 20-byte records at 0xf029e4 in dump/exefs_v11/mem.bin (loaded at 0x100000): type, rarity-1, ?, carry,
  icon, colour, u16 sort, u32 flags, u32 sell, u32 buy. 4U and GU share the icon and colour numbers (1033 of the
  1073 items both games name the same have the same icon; colours match likewise).
- text: core_common.arc msg/itemName_<lang> / itemExp_<lang> (lmd), entry = 4U item id, 5 languages.
Category (GU file +0x1b, meaning not traced) is not in 4U's record: each monster tool picks it from a GU item with
the same icon.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import alloc, arc, portdata

EXE = os.path.join(ROOT, 'dump/exefs_v11/mem.bin')
EXE_BASE, ITEM_TABLE = 0x100000, 0xf029e4
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')     # order of the item text in items.c
DUMMY_ICON, DUMMY_SELL = 1, 0                   # what items.c expects in a DUMMY material slot
DECO_DUMMY_ICON, DECO_DUMMY_SELL = 44, 40       # ... and in a DUMMY decoration slot


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
    """(item names, item descriptions) of one language, indexed by 4U item id"""
    d = open(os.path.join(ROOT, 'dump/romfs/%s/data/core_common.arc' % lang), 'rb').read()
    f = {e[0].split('\\')[-1]: arc.arc_read(d, e) for e in arc.arc_entries(d) if '\\msg\\' in e[0]}
    return lmd(f['itemName_' + lang]), lmd(f['itemExp_' + lang])


def gu_str(s):
    """4U item text as GU stores it (CRLF line breaks); markup tags refused"""
    if '\0' in s: sys.exit('4U text with a markup tag, not handled: %r' % s)
    return s.replace('\n', '\r\n')


_MSG = {}
def msg4u(lang):
    """{file stem: strings} of every core_common msg file of one language (lmd), e.g. ['emName'][4U em]"""
    if lang not in _MSG:
        d = open(os.path.join(ROOT, 'dump/romfs/%s/data/core_common.arc' % lang), 'rb').read()
        f = {e[0].split('\\')[-1]: arc.arc_read(d, e) for e in arc.arc_entries(d) if '\\msg\\' in e[0]}
        _MSG[lang] = {k.rsplit('_', 1)[0]: lmd(v) for k, v in f.items() if k.endswith('_' + lang)}
    return _MSG[lang]


def gu_text(s):
    """4U gear / notes text as GU stores it (CRLF line breaks); markup tags refused"""
    if '\0' in s: sys.exit('4U text with a markup tag: %r' % s)
    return s.replace('\r\n', '\n').replace('\n', '\r\n')


class Materials:
    """A monster's materials in its allocations.toml item range (items = [(4U id, GU category)], in GU id order),
    its decorations ([(4U id, GU id)]), and the other 4U items of its tables (other = {4U id: GU id}; no_gu = 4U ids
    GU has no item for)."""
    def __init__(self, name, items, decos=(), other=None, no_gu=()):
        a = alloc.monster(name)
        self.items, self.decos, self.other, self.no_gu = list(items), list(decos), dict(other or {}), set(no_gu)
        self.gu_first = a['items'][0]
        assert self.gu_first + len(self.items) - 1 == a['items'][1], 'allocations.toml items does not match the list'
        if self.decos:
            assert [g for _, g in self.decos] == list(range(a['decorations'][0], a['decorations'][1] + 1))

    def gu_item(self, k):
        """GU item ID of 4U item k (None: no GU item, no_gu)"""
        for i, (k4, _) in enumerate(self.items):
            if k4 == k: return self.gu_first + i
        return None if k in self.no_gu else self.other[k]

    def every(self):
        """(4U id, GU id, category, 4U record type, DUMMY icon, DUMMY sell) of each material and decoration"""
        return [(k, self.gu_first + i, cat, 0, DUMMY_ICON, DUMMY_SELL) for i, (k, cat) in enumerate(self.items)] + \
               [(k, gu, 0, 3, DECO_DUMMY_ICON, DECO_DUMMY_SELL) for k, gu in self.decos]

    def item_section(self, exe, text, log=print):
        """ITEM: {GU id, rarity, icon, colour, category, DUMMY icon, DUMMY sell, sell, buy}, then name / description
        per language"""
        every = self.every()
        sec = portdata.Section('ITEM')
        sec.u32(len(every))
        for k, gu, cat, kind, d_icon, d_sell in every:
            rare, icon, col, sell, buy = item_4u(exe, k, kind)
            sec.raw(struct.pack('<HBBBBBxIII', gu, rare, icon, col, cat, d_icon, d_sell, sell, buy))
            log('item %d <- 4U %d %s' % (gu, k, text['eng'][0][k]))
        for lang in LANGS:
            names, exps = text[lang]
            for k, *_ in every:
                sec.str(gu_str(names[k]))
                sec.str(gu_str(exps[k]))
        return sec


def breaks(exe, table, ptr, conds, gu_item):
    """4U break reward groups at `table` (checked against the pointer at `ptr`): 6-byte {u16 chance, u16 item, u16
    count}, each group closed by 0xFFFF, one group per GU condition in `conds` -> [(GU cond, [(chance, count, GU
    item)])]"""
    assert struct.unpack_from('<I', exe, ptr - EXE_BASE)[0] == table
    out, a = [], table - EXE_BASE
    for cond in conds:
        ents = []
        while struct.unpack_from('<H', exe, a)[0] != 0xFFFF:
            chance, item, count = struct.unpack_from('<HHH', exe, a)
            ents.append((chance, count, gu_item(item)))
            a += 6
        a += 2
        assert sum(e[0] for e in ents) == 100, ents
        out.append((cond, ents))
    return out


def bui_section(brk):
    """BUI: break rewards, groups (GU condition, entries); each group closed by chance 255"""
    ents = [e for _, es in brk for e in es + [(255, 0, 0)]]
    bui = portdata.Section('BUI ')
    bui.u32(len(brk), len(ents))
    bui.raw(bytes(c for c, _ in brk) + bytes(len(e) for _, e in brk))
    bui.align()
    for chance, count, item in ents:
        bui.raw(struct.pack('<BBH', chance, count, item))
    return bui
