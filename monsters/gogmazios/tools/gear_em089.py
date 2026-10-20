"""gear_em089.py : Gogma armor (+ the Arcana skill and jewels) as records appended to GU's loaded tables -> data file
sections TBLA / TXTA / SKIL (gen/*-armor.sec, tools/portdata.py; module/gear.c). See notes/content-plan.md "Armor and
weapons" / "Skills". Armor: tools/gear4u.py (formats, 4U records, rules); the Arcana tree, skill and jewels here.

  gear_em089.py          write the sections
  gear_em089.py show     print them only

GU tables (besides gear4u's; MHGU_Editor docs/07 + this tool's checks):
  skillTypeData (19 B): u32 tree, u8 kind, 7 x u16 skill at -20 -15 -10 +10 +15 +20 +25 points; names 2 per tree.
  skillData (18 B): u32 skill, 14 per-class bytes; names 2 per skill.
  decoData (resident.arc, 5 B): size, u8 tree, s8 points, u8 tree, s8 points; record k = item 2638 + k (251 in v1.0).
  decoCreate (blacksmith.arc, 16 B): u16 item, u16 rank field, 4 x {u16 item, u8 count}.
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
import gear4u, portdata
import items_em089
from gear4u import EXE, EXE_BASE, LANGS, RomFS, gu_arc, text4u, gu_str, cnt

# GU table classes (main offsets: element alloc / free / ctor / parse, in-memory element size; module/gear.c)
CLS_SKILL_TYPE = (0x4cd4e0, 0x4cd51c, 0x4cd548, 0x4cda28, 24)
CLS_SKILL = (0x4cc3fc, 0x4cc438, 0x4cc464, 0x4ccc10, 24)
CLS_DECO = (0x184140, 0x18417c, 0x1841a8, 0x184484, 12)
CLS_DECO_CREATE = (0x4aacd4, 0x4aad10, 0x4aad3c, 0x4ab294, 20)
# Enlightened Blade (4U: Awaken + Element Atk Up + Status Atk Up): GU skill checks answer yes for these (SKIL)
SKILL_GRANTS = (76, 79)                  # Element Atk Up, Status Atk +1 (GU has no Awaken)

SERIES_FIRST, TREE_ID, SKILL_ID = 1287, 206, 328
ARCANA_4U, ENLIGHTENED_4U = 140, 273     # 4U tree / skill ids
GU_TREES = {'Expert': 70, 'Artillery': 90, 'Avarice': 199, 'Sharpener': 34, 'Dead Eye': 66, 'Normal Up': 48,
            'Normal S+': 52, 'Reload Spd': 45}
ELEMENTALITY = 319                       # GU compound skill whose per-class bytes the new skill copies
ARMOR = dict(
    name='gogmazios', materials=[items_em089.MATERIALS],
    template=(1054, 1055),               # GU Akantor Mask X / Fangs X
    model=(352, 353),                    # 4U Gogma Blademaster / Gunner models
    parts=[550, 554, 538, 538, 546],     # 4U Blademaster IDs: head, body, arms, waist, legs
    defense={110: 132, 64: 77},          # 4U defense -> GU (module docstring)
    tree=lambda tree4, name: TREE_ID if tree4 == ARCANA_4U else GU_TREES[name],
    # 4U armor recipes (create table, notes/content-plan.md appendix): (item name, count) per part
    recipes=[[('Gogmazios Gasher', 2), ('Gogmazios Battlement', 4), ('Gogmazios Fortress', 2), ('Purecrystal', 2)],
             [('Gogmazios Battlement', 3), ('Wartorn Dragonsphire', 1), ('Heavy Drakesbone Oil', 5), ('Allfire Stone', 3)],
             [('Gogmazios Offenders', 5), ('Gogmazios Fiberwing', 2), ('Gogmazios Fortress', 5), ('Meldspar Ore', 3)],
             [('Gogmazios Fiberwing', 2), ('Gogmazios Fortress', 5), ('Seregios Dissenter', 1), ('Gogmazios Briartail', 1)],
             [('Gogmazios Fortress', 5), ('Gogmazios Battlement', 4), ('Gogmazios Offenders', 5), ('Lrg ElderDragon Bone', 6)]],
    scrap=2985,                          # Gogmazios Scrap+ (items_em089), given back like the template's scraps
    level_swap={'Great Wyvern Crystal': 'Wartorn Dragonsphire'},   # template level-row materials -> Gogmazios
    template_word='Akantor',
    colour='template')                   # Akantor X's dye 0x0a (tested look, 2026-10-20); 4U Gogma's is 0x29
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


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    bs = gu_arc(R.read('/nativeNX/arc/facility/blacksmith.arc'))
    names = gear4u.gu_item_names(R, ARMOR['materials'])
    tables, texts = gear4u.armor(ARMOR, R, exe)       # TBLA / TXTA entries (tools/portdata.py)
    assert tables[0]['base'] == SERIES_FIRST

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
