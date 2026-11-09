"""gear_em068_01.py : Tidal Najarala's armor (4U Najarala Z, 1 series pair, 10 pieces, crafted from her materials in 4U) as records
appended to GU's loaded tables -> data file sections TBLA / TXTA (gen/*-armor.sec, tools/portdata.py; module/gear.c). Formats, 4U
records and the shared rules: tools/gear4u.py. Weapons: gear_weapons_em068_01.py. Models: build.py step armor (tools/armor4u2gu.py,
the 20 arcs pl_{m,f}_<part>{432,433}).
  gear_em068_01.py          write the sections
  gear_em068_01.py show     print them only
4U data (C, 2026-11-06): the pieces whose 4U create recipes are her materials, per part the Blademaster piece ID below (Gunner = ID +
1), rarity 8, models 432 / 433 (no GU armor arc has them). Left out: Lagiacrus X (Lagiacrus' set in 4U: her materials are only part of
its recipes, GU's own Lagiacrus X stays GU's).
Choices (the rules of Black Gravios' and Monoblos' armor, listed for review):
  - Template: GU Najarala Helm X / Cap X (867 / 868, G rank, the same species): max level, limit levels, defense table, sound, look.
  - Defense: 4U defense x the GU / 4U ratio of the same species' G set: 4U Najarala X (530 / 531: 86 / 46) -> GU Najarala X (867 / 868: 112
    / 67). So 4U Z 88 / 47 -> 115 / 68. Scaled on GU's balance, as the user asked ("skaliere ... die Werte der Rüstung").
  - Skills by GU tree name; a 4U tree GU lacks is dropped (DROPPED_TREES), a DEVIATION.
  - Level rows: the template's, Najarala's own materials swapped for hers (LEVEL_SWAP).
  - Recipe items GU lacks: SUBSTITUTES (G, listed for review), Tigerstripe's rules: Rhenoplos Bone -> Large Herbivore Bone.
  - Default dye = 4U's colour index.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em068_01, portdata           # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402
NAME = 'tidal_najarala'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, level-row swaps)
PAIRS = [('Najarala Z', [532, 536, 520, 520, 528], (867, 868), (432, 433),
          {'Najarala Cortex': 'T.Najarala Cortex', 'Najarala Piel': 'T.Najarala Piel',
           'Najarala Ampsounder': 'T.Najarala Splasher', 'Hyper Najarala Cortex': 'T.Najarala Cortex'})]
ANCHORS = ([(530, 867)], [(531, 868)])   # (4U head ID, GU series), Blademaster, Gunner
TREE_4U_GU = {'PunishDraw': 'Punish Draw'}
DROPPED_TREES = {'FreeElemnt'}           # as Tigerstripe's and Monoblos': GU has no hidden elements
TEMPLATE_WORD = None                     # hers contain the word too: tools/gear4u.py checks the swaps' sources below
SUBSTITUTES = {'Rhenoplos Bone': 'Large Herbivore Bone'}


def defense_map(exe, series, defs):
    """{4U defense: GU defense} of one pair's Blademaster / Gunner defenses `defs`"""
    out = {}
    for g, d4 in enumerate(defs):
        ratios = [series[8 + 127 * gu + 106] / gear4u.armor_4u(exe, 33, k)['defense'] for k, gu in ANCHORS[g]]
        out[d4] = int(d4 * sum(ratios) / len(ratios) + 0.5)
    return out


def armor_specs(R, exe, mats):
    t4 = text4u('eng')
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    series = res['table\\armorSeriesData']
    gst = gmd(gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\skillTypeData_eng'])
    gtree = {gst[i]: i // 2 for i in range(0, len(gst), 2)}

    def tree(tree4, name):
        if name in DROPPED_TREES: return None
        return gtree[TREE_4U_GU.get(name, name)]
    specs = []
    for pair, parts, tpl, model, swap in PAIRS:
        recipes = []
        for (part, _), k in zip(gear4u.PARTS, parts):
            r = [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k)]
            assert r == [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k + 1)], (pair, part)
            recipes.append([(SUBSTITUTES.get(n, n), c) for n, c in r])
        defs = [gear4u.armor_4u(exe, 33, parts[0] + g)['defense'] for g in range(2)]
        specs.append(dict(template=tpl, model=model, parts=parts, defense=defense_map(exe, series, defs),
                          tree=tree, recipes=recipes, scrap=None, level_swap=swap, template_word=TEMPLATE_WORD))
    return specs


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    mats = items_em068_01.materials(R, exe)
    specs = armor_specs(R, exe, mats)
    for (pair, *_), s in zip(PAIRS, specs):
        print('%-10s defense %s' % (pair, s['defense']))
    tables, texts = gear4u.armors(NAME, [mats], specs, R, exe)
    secs = [portdata.tbla(tables), portdata.txta(texts)]
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section(NAME, s, 'armor'))


if __name__ == '__main__':
    main()
