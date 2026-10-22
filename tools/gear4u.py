"""gear4u.py : MH4U armor -> records appended to GU's loaded armor tables (data file sections TBLA / TXTA,
tools/portdata.py; module/gear.c), shared by the monsters' gear tools (monsters/<name>/tools/gear_*.py, which give the
spec); also the 4U text / item helpers the weapon tool (tools/weapons4u.py) uses.

  import gear4u
  tables, texts = gear4u.armor(spec)

spec = dict(name=allocations.toml name, materials=[items4u.Materials], template=(GU Blademaster, Gunner series),
model=(Blademaster, Gunner model), parts=[4U Blademaster ID of head, body, arms, waist, legs] (Gunner = ID + 1),
defense={4U defense: GU defense}, tree=f(4U tree ID, 4U tree name) -> GU tree (None: dropped),
recipes=[[(item name, count)] x 4] per part, scrap=GU item given back (None: the template's), level_swap={template
level-row material: ours}, template_word=a word no level-row material may keep (the template monster's name)).

GU tables (file formats, MHGU_Editor docs/07 + this tool's checks; every new record starts from a GU record):
  armorSeriesData (resident.arc, 127 B): +0 u32 ID, +4 u16 sort, +6 5 x enabled part, +11 u16 model, +13 male,
    female, Blademaster, Gunner, +17 u32 price, +21 unique resist flag / ID, +23 5 x s8 resist F W T I D,
    +28 5 parts x 5 x {u16 skill tree, s8 points}, +103 rarity - 1, +104 max level, +105 levels past the limit,
    +106 defense, +107 defense-growth table, +108 5 x slots, +113.. colours / sound types (14 B).
  armorSeriesData_<lang> GMD: 10 strings per series = 5 part names, then 5 descriptions (4U's, via EXP_4U).
  armorCreateA00..A04 (blacksmith.arc, 42 B, one per part): +0 4 x u16 armor ID, +8 u16, +10 4 x {u16 item, u8 count,
    u8 flag}, +26 provision {u16 group, u8 value}, +30 scraps given {u16 item, u8 count}.
  armorProcessA00 (38 B, one per level past 1): +0 4 x u16 armor ID, +8 u16 level, +10 4 x {u16 item, u8 count},
    +22 provision, +26 scraps.
4U (v1.1 exe dump/exefs_v11/mem.bin at 0x100000): armor records 40 B via the equipment pointer table 0xf58868
  (entries 33 head, 29 body, 30 arms, 31 waist, 32 legs): +5 rarity - 1, +7 defense, +8 u32 price, +12 5 x s8
  resist, +17 slots, +30 5 x {u8 tree, s8 points}; create recipes in the table 0xf3f000.. (types 5 head, 1 body,
  2 arms, 3 waist, 4 legs).
Rules (port choices made for Gogmazios, kept for every monster):
  - IDs: a monster's series pair (Blademaster, Gunner) follows GU's and the earlier monsters' (allocations.toml
    [monster.append] armor_series / armor_create / armor_process); sort = ID.
  - Template: a GU pair of the same tier: max level, limit levels, defense table, colours, sound, look.
  - Defense: 4U defense x the GU / 4U ratio of the matching GU set (the monster's choice, spec defense).
  - Model: 4U's own numbers (GU keeps 4U model numbers; arcs from tools/armor4u2gu.py).
  - Colour (C, 2026-10-21): 4U armor record +19 = an index into GU's table\\equipBaseColorData (125 RGB, resident.arc),
    and GU's series record keeps it as the default dye of both colour slots (+116, +119): Zamtrios 0x2b, Zamtrios X
    0x0b, Akantor X 0x0a, Kirin 0x29, Tigrex 0x16 equal in both games. 4U armor textures are grey metal tinted by
    it (Zamtrios Z 0x36 = ff 91 41 gold; the template's 0x0b turned it icy silver, test 2026-10-21), so the default
    is 4U's index (spec colour='template' keeps the template's).
  - Levels: the template's level rows (spheres), its monster materials swapped for ours.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_EDITOR_TOOLS)
import alloc                                        # noqa: E402
from items4u import EXE, EXE_BASE, LANGS, msg4u as text4u, gu_text as gu_str   # noqa: E402,F401 (users import them)
from build_assets import RomFS, arc as gu_arc, gmd  # noqa: E402

GU_ROMFS = paths.GU_ROMFS
# GU table classes (main offsets: element alloc / free / ctor / parse, in-memory element size; module/gear.c)
CLS_ARMOR_SERIES = (0xd4768, 0xd47a4, 0xd47d0, 0xd75fc, 140)
CLS_ARMOR_CREATE = (0x4a7f4c, 0x4a7f88, 0x4a7fb4, 0x4a8c68, 48)
CLS_ARMOR_PROCESS = (0x4a94f8, 0x4a9534, 0x4a9560, 0x4aa02c, 44)
PARTS = [('Head', 33), ('Body', 29), ('Arm', 30), ('Waist', 31), ('Leg', 32)]    # 4U text part, pointer-table entry
# 4U description index per armor ID (u16 tables, one per part) -> core_common <Part>Exp_<lang>. Found by vote over
# the armor GU took from 4U (GU description = 4U text): 532/564 head pairs agree, the rest differ in wording (C).
EXP_4U = {'Head': 0xef1308, 'Body': 0xeef4f8, 'Arm': 0xeefc90, 'Waist': 0xef0408, 'Leg': 0xef0b80}


def exp_4u(exe, table, k):
    return struct.unpack_from('<H', exe, table - EXE_BASE + 2 * k)[0]


def gu_item_names(R, materials):
    """GU item name -> ID (DUMMY slots left out), plus our materials (items4u.Materials list) by their 4U names"""
    it = gmd(gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    names = {it[2 * i]: i for i in range(len(it) // 2) if it[2 * i] not in ('DUMMY', '')}
    for m in materials:
        for i, (k4, _) in enumerate(m.items):            # DUMMY in the RomFS
            names[text4u('eng')['itemName'][k4]] = m.gu_first + i
    return names


def armor_4u(exe, ptab_index, k):
    o = struct.unpack_from('<I', exe, 0xf58868 + 4 * ptab_index - EXE_BASE)[0] - EXE_BASE + 40 * k
    r = exe[o:o + 40]
    return dict(rare=r[5] + 1, defense=r[7], price=struct.unpack_from('<I', r, 8)[0],
                res=list(struct.unpack_from('5b', r, 12)), slots=r[17], colour=r[19],
                skills=[(r[30 + 2 * j], struct.unpack_from('b', r, 31 + 2 * j)[0]) for j in range(5) if r[30 + 2 * j]])


def cnt(d):
    return struct.unpack_from('<I', d, 4)[0]


CREATE_4U = (0xf3f000, 0xf55400)         # 4U create recipes, 24 B: +4 u16 type, +6 u16 ID, +8 4 x {u16 item, u16 count}
CREATE_TYPE_4U = {'Head': 5, 'Body': 1, 'Arm': 2, 'Waist': 3, 'Leg': 4}


def armor_recipe_4u(exe, part, k):
    """4U create recipe of armor piece k of a part -> [(4U item, count)]"""
    hits = [a for a in range(CREATE_4U[0], CREATE_4U[1], 24)
            if struct.unpack_from('<HH', exe, a + 4 - EXE_BASE) == (CREATE_TYPE_4U[part], k)]
    assert len(hits) == 1, (part, k, hits)
    v = struct.unpack_from('<8H', exe, hits[0] + 8 - EXE_BASE)
    return [(it, c) for it, c in zip(v[0::2], v[1::2]) if it]


def armor(spec, R=None, exe=None):
    """[TBLA table dicts] and [TXTA entries] of the monster's armor series pair, create recipes and level rows"""
    return armors(spec['name'], spec['materials'], [spec], R, exe)


def armors(name, materials, specs, R=None, exe=None):
    """the same for several series pairs: specs = [the per-pair keys of armor's spec (template, model, parts,
    defense, tree, recipes, scrap, level_swap, template_word, colour)], IDs in list order (pair s = first + 2 s);
    one TBLA block per table (allocations.toml armor_series = 2 x pairs, armor_create = pairs)"""
    a = alloc.monster(name)['append']
    R = R or RomFS(GU_ROMFS)
    exe = exe or open(EXE, 'rb').read()
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    bs = gu_arc(R.read('/nativeNX/arc/facility/blacksmith.arc'))
    names = gu_item_names(R, materials)
    st4 = text4u('eng')['skillType']
    series = res['table\\armorSeriesData']
    first = cnt(series) + alloc.offset(name, 'armor_series')
    assert a.get('armor_series') == 2 * len(specs) and a.get('armor_create') == len(specs), \
        'allocations.toml armor_series / armor_create'
    tables, texts = [], []

    # ---- armor series: Blademaster, Gunner per pair
    recs = []
    for s, g in [(s, g) for s in range(len(specs)) for g in range(2)]:
        spec, f = specs[s], first + 2 * s
        tpl_ids = spec['template']
        r = bytearray(series[8 + 127 * tpl_ids[g]: 8 + 127 * (tpl_ids[g] + 1)])
        p = [armor_4u(exe, pt, k0 + g) for (_, pt), k0 in zip(PARTS, spec['parts'])]
        assert all(x['rare'] == p[0]['rare'] and x['price'] == p[0]['price'] and x['res'] == p[0]['res'] and
                   x['defense'] == p[0]['defense'] and x['colour'] == p[0]['colour'] for x in p), p
        struct.pack_into('<I', r, 0, f + g)
        struct.pack_into('<H', r, 4, f + g)                          # sort after every GU series
        struct.pack_into('<H', r, 11, spec['model'][g])
        r[13:17] = bytes([1, 1, 1 - g, g])
        struct.pack_into('<I', r, 17, p[0]['price'])
        r[21] = r[22] = 0
        struct.pack_into('5b', r, 23, *p[0]['res'])
        r[28:103] = bytes(75)
        for part, x in enumerate(p):
            kept = [(spec['tree'](tree4, st4[tree4]), pts) for tree4, pts in x['skills']]
            for j, (tree, pts) in enumerate([s for s in kept if s[0] is not None]):
                struct.pack_into('<Hb', r, 28 + 15 * part + 3 * j, tree, pts)
        r[103] = p[0]['rare'] - 1
        r[106] = spec['defense'][p[0]['defense']]
        if spec.get('colour', '4u') == '4u':        # default dye of both colour slots = 4U's tint (COLOUR notes)
            r[116] = r[119] = p[0]['colour']
        r[108:113] = bytes(x['slots'] for x in p)
        recs.append(bytes(r))
    tables.append(dict(path='table\\armorSeriesData', cls=CLS_ARMOR_SERIES, rec_bytes=127, base=first,
                       records=b''.join(recs)))                         # Blademaster, Gunner per pair

    # ---- names: 10 strings per series (Blademaster then Gunner: 5 names, 5 descriptions), 5 languages
    text = []
    for lang in LANGS:
        t = text4u(lang)
        strs = []
        for spec in specs:
            for g in range(2):
                strs += [t[part + 'Name'][k0 + g] for (part, _), k0 in zip(PARTS, spec['parts'])]
                strs += [t[part + 'Exp'][exp_4u(exe, EXP_4U[part], k0 + g)]
                         for (part, _), k0 in zip(PARTS, spec['parts'])]
        text.append([gu_str(s) for s in strs])
    texts.append(('armorSeriesData', first * 10, text))

    # ---- create recipes, one per part and pair
    off = alloc.offset(name, 'armor_create')
    for part in range(5):
        t = bs['table\\armorCreateA%02d' % part]
        n = cnt(t)
        recs = []
        for s, spec in enumerate(specs):
            tpl_ids, f = spec['template'], first + 2 * s
            tpl = [t[8 + 42 * i: 50 + 42 * i] for i in range(n)
                   if struct.unpack_from('<H', t, 8 + 42 * i)[0] == tpl_ids[0]]
            r = bytearray(tpl[0])
            struct.pack_into('<4H', r, 0, f, f + 1, 0, 0)
            for k in range(4):
                nm, c = spec['recipes'][part][k]
                struct.pack_into('<HB', r, 10 + 4 * k, names[nm], c)       # the flag byte (+13 on the first) stays
            if spec.get('scrap') is not None:
                struct.pack_into('<H', r, 30, spec['scrap'])
            recs.append(bytes(r))
        tables.append(dict(path='table\\armorCreateA%02d' % part, cls=CLS_ARMOR_CREATE, rec_bytes=42, base=n + off,
                           records=b''.join(recs)))

    # ---- level rows
    t = bs['table\\armorProcessA00']
    n = cnt(t)
    it_names = {v: k for k, v in names.items()}
    lv = []
    for s, i in [(s, i) for s in range(len(specs)) for i in range(n)]:
            spec, f = specs[s], first + 2 * s   # one row per level holds the whole set (Blademaster + Gunner IDs)
            tpl_ids, swap = spec['template'], spec.get('level_swap', {})
            ours = {tpl_ids[0]: f, tpl_ids[1]: f + 1, 0: 0}
            r = bytearray(t[8 + 38 * i: 46 + 38 * i])
            ids = struct.unpack_from('<4H', r, 0)
            if tpl_ids[0] not in ids: continue
            struct.pack_into('<4H', r, 0, *(ours[x] for x in ids))
            for k in range(4):
                item = struct.unpack_from('<H', r, 10 + 3 * k)[0]
                if item and it_names.get(item) in swap:
                    struct.pack_into('<H', r, 10 + 3 * k, names[swap[it_names[item]]])
                final = it_names.get(struct.unpack_from('<H', r, 10 + 3 * k)[0], '')
                assert spec['template_word'] not in final.split(), final      # no template-monster material left
            lv.append(bytes(r))
    assert a.get('armor_process') == len(lv), 'allocations.toml armor_process != %d level rows' % len(lv)
    tables.append(dict(path='table\\armorProcessA00', cls=CLS_ARMOR_PROCESS, rec_bytes=38,
                       base=n + alloc.offset(name, 'armor_process'), records=b''.join(lv)))
    return tables, texts
