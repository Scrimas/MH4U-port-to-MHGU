"""gear_em089.py : Gogma armor (+ the Arcana skill and jewels) as records appended to GU's loaded tables -> data file
sections TBLA / TXTA / SKIL (gen/*-armor.sec, tools/portdata.py; module/gear.c). See notes/content-plan.md "Armor and
weapons" / "Skills".

  gear_em089.py          write the sections
  gear_em089.py show     print them only

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
  skillTypeData (19 B): u32 tree, u8 kind, 7 x u16 skill at -20 -15 -10 +10 +15 +20 +25 points; names 2 per tree.
  skillData (18 B): u32 skill, 14 per-class bytes; names 2 per skill.
  decoData (resident.arc, 5 B): size, u8 tree, s8 points, u8 tree, s8 points; record k = item 2638 + k (251 in v1.0).
  decoCreate (blacksmith.arc, 16 B): u16 item, u16 rank field, 4 x {u16 item, u8 count}.
4U (v1.1 exe dump/exefs_v11/mem.bin at 0x100000): armor records 40 B via the equipment pointer table 0xf58868
  (entries 33 head, 29 body, 30 arms, 31 waist, 32 legs): +5 rarity - 1, +7 defense, +8 u32 price, +12 5 x s8
  resist, +17 slots, +30 5 x {u8 tree, s8 points}; recipes in notes/content-plan.md (create table 0xf3f000..).
Choices (notes/content-plan.md):
  - IDs: series 1287 (Blademaster) / 1288 (Gunner), tree 206 Arcana, skill 328 Enlightened Blade = the v1.0 table
    counts; module/gear.c appends only when the loaded count is that number (v1.4 item count = v1.0's, 2991).
  - Template: GU Akantor Mask X / Fangs X (series 1054 / 1055, rarity 10, the X tier 4U Gogma belongs to: 4U def
    110 = 4U Akantor Mask X 110, Kaiser Crown X 109): max level, limit levels, defense table, colours, sound, look.
  - Defense: 4U def x mean GU/4U ratio of the X sets present in both games (Blademaster: Kaiser Crown X 128/109,
    Akantor Mask X 134/110 -> 1.196; Gunner: Kaiser Mask X 76/63 = 1.206): 110 -> 132, 64 -> 77.
  - Model: 4U's own numbers, 352 Blademaster / 353 Gunner (4U armor record +0 male / +2 female model = 0x160 /
    0x161). GU keeps 4U model numbers and 352 / 353 are unused gaps in its file list; the arcs come from
    tools/armor4u2gu.py (romfs/nativeNX/arc/player/com/{m,f}/{352,353}/<part>.arc).
  - Cosmicite Ore (4U rarity 8, top regular G ore, no GU item) -> Meldspar Ore (GU's top regular G ore, rarity 8).
  - Levels: the template's level rows (spheres); Akantor materials -> Gogmazios ones (crystal -> Dragonsphire).
  - Arcana (4U tree 140, +10 = Enlightened Blade = Awaken + Element Atk Up + Status Atk Up): new tree / skill, the
    effect is module/gear.c's has-skill hook (Element Atk Up 76, Status Atk +1 79). GU has no Awaken.
  - Arcane Jwl 1 / 2 / 3, True Arcane Jwl 3: 4U's decoration records in the DUMMY decorations 2889.. (items_em089),
    recipes = DECO_RECIPES (port choice, see there).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_EDITOR_TOOLS)
import arc, portdata
import items_em089
from items_em089 import lmd
from build_assets import RomFS, arc as gu_arc, gmd

GU_ROMFS = paths.GU_ROMFS
EXE = os.path.join(ROOT, 'dump/exefs_v11/mem.bin')
EXE_BASE = 0x100000
LANGS = items_em089.LANGS
# GU table classes (main offsets: element alloc / free / ctor / parse, in-memory element size; module/gear.c)
CLS_ARMOR_SERIES = (0xd4768, 0xd47a4, 0xd47d0, 0xd75fc, 140)
CLS_ARMOR_CREATE = (0x4a7f4c, 0x4a7f88, 0x4a7fb4, 0x4a8c68, 48)
CLS_ARMOR_PROCESS = (0x4a94f8, 0x4a9534, 0x4a9560, 0x4aa02c, 44)
CLS_SKILL_TYPE = (0x4cd4e0, 0x4cd51c, 0x4cd548, 0x4cda28, 24)
CLS_SKILL = (0x4cc3fc, 0x4cc438, 0x4cc464, 0x4ccc10, 24)
CLS_DECO = (0x184140, 0x18417c, 0x1841a8, 0x184484, 12)
CLS_DECO_CREATE = (0x4aacd4, 0x4aad10, 0x4aad3c, 0x4ab294, 20)
# Enlightened Blade (4U: Awaken + Element Atk Up + Status Atk Up): GU skill checks answer yes for these (SKIL)
SKILL_GRANTS = (76, 79)                  # Element Atk Up, Status Atk +1 (GU has no Awaken)

SERIES_FIRST, TREE_ID, SKILL_ID = 1287, 206, 328
TEMPLATE = (1054, 1055)                  # GU Akantor Mask X / Fangs X
MODEL = (352, 353)                       # 4U Gogma Blademaster / Gunner models
PARTS_4U = [('Head', 33, 550), ('Body', 29, 554), ('Arm', 30, 538), ('Waist', 31, 538), ('Leg', 32, 546)]
DEF_GU = {110: 132, 64: 77}              # 4U defense -> GU (module docstring)
ARCANA_4U, ENLIGHTENED_4U = 140, 273     # 4U tree / skill ids
GU_TREES = {'Expert': 70, 'Artillery': 90, 'Avarice': 199, 'Sharpener': 34, 'Dead Eye': 66, 'Normal Up': 48,
            'Normal S+': 52, 'Reload Spd': 45}
ELEMENTALITY = 319                       # GU compound skill whose per-class bytes the new skill copies
# 4U armor recipes (create table, notes/content-plan.md appendix): (item name, count) per part
RECIPES = [[('Gogmazios Gasher', 2), ('Gogmazios Battlement', 4), ('Gogmazios Fortress', 2), ('Purecrystal', 2)],
           [('Gogmazios Battlement', 3), ('Wartorn Dragonsphire', 1), ('Heavy Drakesbone Oil', 5), ('Allfire Stone', 3)],
           [('Gogmazios Offenders', 5), ('Gogmazios Fiberwing', 2), ('Gogmazios Fortress', 5), ('Meldspar Ore', 3)],
           [('Gogmazios Fiberwing', 2), ('Gogmazios Fortress', 5), ('Seregios Dissenter', 1), ('Gogmazios Briartail', 1)],
           [('Gogmazios Fortress', 5), ('Gogmazios Battlement', 4), ('Gogmazios Offenders', 5), ('Lrg ElderDragon Bone', 6)]]
SCRAP = 2985                             # Gogmazios Scrap+ (items_em089), given back like the template's scraps
# 4U description index per armor ID (u16 tables, one per part) -> core_common <Part>Exp_<lang>. Found by vote over
# the armor GU took from 4U (GU description = 4U text): 532/564 head pairs agree, the rest differ in wording (C).
EXP_4U = {'Head': 0xef1308, 'Body': 0xeef4f8, 'Arm': 0xeefc90, 'Waist': 0xef0408, 'Leg': 0xef0b80}


def exp_4u(exe, table, k):
    return struct.unpack_from('<H', exe, table - EXE_BASE + 2 * k)[0]
LEVEL_SWAP = {'Great Wyvern Crystal': 'Wartorn Dragonsphire'}   # template level-row materials -> Gogmazios
# Arcane jewels. 4U decoration table 0xf578dc: 8-B records {u16 item, u8 size, u8 tree, s8 points, u8 tree, s8 points,
# u8 0}, record = the item record's u16 at +10, minus 1 (C). 4U has NO recipe for them: they are among the 93
# decorations absent from 4U's decoration recipe table (0xf553e0, 229 x 24 B) and come from weighted reward lists
# (0xf61198.., Blademaster / Gunner variants; the source of those lists is not traced). GU crafts every decoration, so
# PORT CHOICE: recipes in GU's G-rank pattern (Bloodrun Jewel for sizes 1-2, Lazurite Jewel for size 3, + Gogmazios
# materials); rank field = GU's Elemental-tree jewels (Element Jwl 1 / 3, checked).
DECO_4U, DECO_ITEM0, DECO_RANK = 0xf578dc, 2638, 2
DECO_RECIPES = {1838: [('Bloodrun Jewel', 1), ('Gogmazios Battlement', 1), ('Heavy Drakesbone Oil', 1)],
                1839: [('Bloodrun Jewel', 1), ('Gogmazios Fortress', 1), ('Gogmazios Fiberwing', 1)],
                1840: [('Lazurite Jewel', 1), ('Gogmazios Gasher', 1), ('Gogmazios Offenders', 2)],
                1841: [('Lazurite Jewel', 1), ('Wartorn Dragonsphire', 1), ('Gogmazios Briartail', 1)]}


def deco_4u(exe, item):
    """4U decoration record of an item -> size, tree, points, second tree"""
    k = struct.unpack_from('<H', exe, items_em089.ITEM_TABLE - EXE_BASE + 20 * item + 10)[0] - 1
    it, size, t1, p1, t2 = struct.unpack_from('<HBBbB', exe, DECO_4U - EXE_BASE + 8 * k)
    assert it == item, (item, it)
    return size, t1, p1, t2


def gu_item_names(R):
    it = gmd(gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    names = {it[2 * i]: i for i in range(len(it) // 2) if it[2 * i] not in ('DUMMY', '')}
    for i, (k4, _) in enumerate(items_em089.ITEMS):            # our materials (DUMMY in the RomFS)
        names[text4u('eng')['itemName'][k4]] = items_em089.GU_FIRST + i
    return names


from items4u import msg4u as text4u, gu_text as gu_str     # 4U core_common msg files; gear / notes text rule


def armor_4u(exe, ptab_index, k):
    o = struct.unpack_from('<I', exe, 0xf58868 + 4 * ptab_index - EXE_BASE)[0] - EXE_BASE + 40 * k
    r = exe[o:o + 40]
    return dict(rare=r[5] + 1, defense=r[7], price=struct.unpack_from('<I', r, 8)[0],
                res=list(struct.unpack_from('5b', r, 12)), slots=r[17],
                skills=[(r[30 + 2 * j], struct.unpack_from('b', r, 31 + 2 * j)[0]) for j in range(5) if r[30 + 2 * j]])


def c_bytes(b, per=16):
    return ',\n'.join('    ' + ', '.join('0x%02x' % x for x in b[i:i + per]) for i in range(0, len(b), per))


def c_str(s):
    s = gu_str(s)
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'


def main():
    R = RomFS(GU_ROMFS)
    exe = open(EXE, 'rb').read()
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    bs = gu_arc(R.read('/nativeNX/arc/facility/blacksmith.arc'))
    names = gu_item_names(R)
    st4 = text4u('eng')['skillType']
    series = res['table\\armorSeriesData']
    assert struct.unpack_from('<I', series, 4)[0] == SERIES_FIRST
    tables, texts = [], []          # TBLA / TXTA entries (tools/portdata.py)

    # ---- armor series: Blademaster, Gunner
    recs = []
    for g in range(2):
        r = bytearray(series[8 + 127 * TEMPLATE[g]: 8 + 127 * (TEMPLATE[g] + 1)])
        p = [armor_4u(exe, pt, k0 + g) for _, pt, k0 in PARTS_4U]
        assert all(x['rare'] == 10 and x['price'] == 15000 and x['res'] == p[0]['res'] and
                   x['defense'] == p[0]['defense'] for x in p), p
        struct.pack_into('<I', r, 0, SERIES_FIRST + g)
        struct.pack_into('<H', r, 4, SERIES_FIRST + g)               # sort after every GU series (max 1286)
        struct.pack_into('<H', r, 11, MODEL[g])
        r[13:17] = bytes([1, 1, 1 - g, g])
        struct.pack_into('<I', r, 17, p[0]['price'])
        r[21] = r[22] = 0
        struct.pack_into('5b', r, 23, *p[0]['res'])
        r[28:103] = bytes(75)
        for part, x in enumerate(p):
            for j, (tree4, pts) in enumerate(x['skills']):
                name = st4[tree4]
                tree = TREE_ID if tree4 == ARCANA_4U else GU_TREES[name]
                struct.pack_into('<Hb', r, 28 + 15 * part + 3 * j, tree, pts)
        r[103] = p[0]['rare'] - 1
        r[106] = DEF_GU[p[0]['defense']]
        r[108:113] = bytes(x['slots'] for x in p)
        recs.append(bytes(r))
    tables.append(dict(path='table\\armorSeriesData', cls=CLS_ARMOR_SERIES, rec_bytes=127, base=SERIES_FIRST,
                       records=b''.join(recs)))                         # Gogma Blademaster, Gunner

    # ---- names: 10 strings per series (Blademaster then Gunner: 5 names, 5 descriptions), 5 languages
    text = []
    for lang in LANGS:
        t = text4u(lang)
        strs = []
        for g in range(2):
            strs += [t[part + 'Name'][k0 + g] for part, _, k0 in PARTS_4U]
            strs += [t[part + 'Exp'][exp_4u(exe, EXP_4U[part], k0 + g)] for part, _, k0 in PARTS_4U]
        text.append([gu_str(s) for s in strs])
    texts.append(('armorSeriesData', SERIES_FIRST * 10, text))

    # ---- create recipes, one per part
    crt = []
    for part in range(5):
        t = bs['table\\armorCreateA%02d' % part]
        n = struct.unpack_from('<I', t, 4)[0]
        tpl = [t[8 + 42 * i: 50 + 42 * i] for i in range(n) if struct.unpack_from('<H', t, 8 + 42 * i)[0] == TEMPLATE[0]]
        r = bytearray(tpl[0])
        struct.pack_into('<4H', r, 0, SERIES_FIRST, SERIES_FIRST + 1, 0, 0)
        for k in range(4):
            name, cnt = RECIPES[part][k]
            struct.pack_into('<HB', r, 10 + 4 * k, names[name], cnt)   # the flag byte (+13 on the first) stays
        struct.pack_into('<H', r, 30, SCRAP)
        crt.append(bytes(r))
    # the counts GU's tables hold before the append (GU v1.0 RomFS = v1.4 as far as checked)
    cnt = lambda d: struct.unpack_from('<I', d, 4)[0]
    for part in range(5):
        tables.append(dict(path='table\\armorCreateA%02d' % part, cls=CLS_ARMOR_CREATE, rec_bytes=42,
                           base=cnt(bs['table\\armorCreateA%02d' % part]), records=crt[part]))

    # ---- level rows
    t = bs['table\\armorProcessA00']
    n = struct.unpack_from('<I', t, 4)[0]
    it_names = {v: k for k, v in names.items()}
    lv = []
    ours = {TEMPLATE[0]: SERIES_FIRST, TEMPLATE[1]: SERIES_FIRST + 1, 0: 0}
    for i in range(n):                   # one row per level holds the whole set (Blademaster + Gunner IDs)
            r = bytearray(t[8 + 38 * i: 46 + 38 * i])
            ids = struct.unpack_from('<4H', r, 0)
            if TEMPLATE[0] not in ids: continue
            struct.pack_into('<4H', r, 0, *(ours[x] for x in ids))
            for k in range(4):
                item = struct.unpack_from('<H', r, 10 + 3 * k)[0]
                if item and it_names.get(item) in LEVEL_SWAP:
                    struct.pack_into('<H', r, 10 + 3 * k, names[LEVEL_SWAP[it_names[item]]])
                assert not item or 'Akantor' not in it_names.get(item, ''), it_names.get(item)
            lv.append(bytes(r))
    tables.append(dict(path='table\\armorProcessA00', cls=CLS_ARMOR_PROCESS, rec_bytes=38, base=cnt(t),
                       records=b''.join(lv)))

    # ---- Arcana tree + Enlightened Blade
    tt = res['table\\skillTypeData']; ts = res['table\\skillData']
    assert struct.unpack_from('<I', tt, 4)[0] == TREE_ID and struct.unpack_from('<I', ts, 4)[0] == SKILL_ID
    tree = struct.pack('<IB7H', TREE_ID, 0, 0, 0, 0, SKILL_ID, SKILL_ID, SKILL_ID, SKILL_ID)
    skill = struct.pack('<I', SKILL_ID) + ts[8 + 18 * ELEMENTALITY + 4: 8 + 18 * (ELEMENTALITY + 1)]
    tables.append(dict(path='table\\skillTypeData', cls=CLS_SKILL_TYPE, rec_bytes=19, base=TREE_ID, records=tree))
    tables.append(dict(path='table\\skillData', cls=CLS_SKILL, rec_bytes=18, base=SKILL_ID, records=skill))
    t4 = [text4u(lang) for lang in LANGS]     # tree name + description, skill name + description
    texts.append(('skillTypeData', TREE_ID * 2, [[gu_str(t['skillType'][ARCANA_4U]),
                                                  gu_str(t['skillTypeExp'][ARCANA_4U])] for t in t4]))
    texts.append(('skillData', SKILL_ID * 2, [[gu_str(t['skillName'][ENLIGHTENED_4U]),
                                              gu_str(t['skillExp'][ENLIGHTENED_4U])] for t in t4]))
    skil = portdata.Section('SKIL')       # Enlightened Blade answers yes for SKILL_GRANTS (module/gear.c)
    skil.u32(1, SKILL_ID, *(SKILL_GRANTS + (0xFFFFFFFF,) * (3 - len(SKILL_GRANTS))))

    # ---- Arcane jewels (items_em089.DECOS): decoData record k = item 2638 + k, so they append at the table's end
    dd, dc = res['table\\decoData'], bs['table\\decoCreate']
    deco, crt = b'', b''
    for i, (k4, gu) in enumerate(items_em089.DECOS):
        assert gu == DECO_ITEM0 + cnt(dd) + i, (gu, cnt(dd))
        size, tree4, pts, tree4b = deco_4u(exe, k4)
        assert tree4 == ARCANA_4U and not tree4b, (k4, tree4, tree4b)
        deco += struct.pack('<BBbBb', size, TREE_ID, pts, 0, 0)
        crt += struct.pack('<HH', gu, DECO_RANK) + b''.join(struct.pack('<HB', names[n], c) for n, c in DECO_RECIPES[k4])
        crt += bytes(12 - 3 * len(DECO_RECIPES[k4]))
    assert all(struct.unpack_from('<H', dc, 8 + 16 * k + 2)[0] == DECO_RANK for k in range(cnt(dc))
               if struct.unpack_from('<H', dc, 8 + 16 * k)[0] in (names['Element Jwl 1'], names['Element Jwl 3']))
    tables.append(dict(path='table\\decoData', cls=CLS_DECO, rec_bytes=5, base=cnt(dd), records=deco))
    tables.append(dict(path='table\\decoCreate', cls=CLS_DECO_CREATE, rec_bytes=16, base=cnt(dc), records=crt))

    secs = [portdata.tbla(tables), portdata.txta(texts), skil]
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section('gogmazios', s, 'armor'))


if __name__ == '__main__':
    main()
