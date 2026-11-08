"""gear_em007_01.py : Monoblos' armor (4U Mono S: HR, Mono X: G = 2 series pairs, 20 pieces, crafted from Monoblos
materials in 4U) as records appended to GU's loaded tables -> data file sections TBLA / TXTA (gen/*-armor.sec,
tools/portdata.py; module/gear.c). Formats, 4U records and the shared rules: tools/gear4u.py. Weapons:
gear_weapons_em007_01.py. Models: build.py step armor (tools/armor4u2gu.py, the 40 arcs pl_{m,f}_<part>{368..371}).
  gear_em007_01.py          write the sections
  gear_em007_01.py show     print them only
4U data (C, 2026-11-05): the pieces whose 4U create recipes use Monoblos materials, per pair the Blademaster piece IDs
below (Gunner = ID + 1), rarity 5 (S) / 9 (X), models 368 / 369 (S) and 370 / 371 (X) (no GU armor arc has them).
Left out: Monodevil Mail / Vest (White Monoblos materials) and Kirin Horn X / Crest X (Kirin's set, one Scarlet
Stouthorn).
Choices (the rules of Black Gravios' armor, listed for review):
  - Templates: GU Diablos Helm / Cap (738 / 739, HR) for S, Diablos Helm X / Cap X (976 / 977, G) for X: max level,
    limit levels, defense table, sound, look.
  - Defense: 4U defense x the GU / 4U ratio of a plain set of the same tier. G: 4U Diablos X (682 / 683) -> GU Diablos
    X (976 / 977). HR: 4U has no Diablos S set (C: its Diablos heads are 74 / 75 rarity 3, 684 / 685 rarity 8 defense 1,
    682 / 683 X, 688 / 689 Z), so Black Gravios' HR anchor: 4U Gravios S (216 / 217) -> GU Gravios (730 / 731).
  - Skills by GU tree name; 4U FreeElemnt (Awaken) has no GU tree (GU has no hidden elements): dropped, a DEVIATION.
  - Level rows: the templates' (Diablos 9 levels, Diablos X 5), Diablos' own materials swapped for his: Majestic Horn ->
    Scarlet Finehorn (his HR horn), Hyper Diablos Cortex -> Monoblos Cortex (GU has no Hyper Monoblos, as Black
    Gravios' Hyper Gravios Cortex), Diablos Hardhorn -> Scarlet Stouthorn (his G horn).
  - Default dye = 4U's colour index.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em007_01, portdata           # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402
NAME = 'monoblos'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, tier, level-row swaps)
PAIRS = [('Mono S', [668, 672, 656, 656, 664], (738, 739), (368, 369), 'HR', {'Majestic Horn': 'Scarlet Finehorn'}),
         ('Mono X', [670, 674, 658, 658, 666], (976, 977), (370, 371), 'G',
          {'Hyper Diablos Cortex': 'Monoblos Cortex', 'Diablos Hardhorn': 'Scarlet Stouthorn'})]
# tier -> ([(4U head ID, GU series)] Blademaster, [...] Gunner)
ANCHORS = {'HR': ([(216, 730)], [(217, 731)]),
           'G': ([(682, 976)], [(683, 977)])}
TREE_4U_GU = {}
# 4U FreeElemnt (Awaken: hidden weapon elements usable): GU has no hidden elements and no such tree (C: GU skillTypeData
# has no Awaken / FreeElemnt): dropped, a DEVIATION
DROPPED_TREES = {'FreeElemnt'}
TEMPLATE_WORD = 'Diablos'        # no Diablos material may stay in the level rows (after PAIRS' swaps)
SUBSTITUTES = {}


def defense_map(exe, series, tier, defs):
    """{4U defense: GU defense} of one pair's Blademaster / Gunner defenses `defs`"""
    out = {}
    for g, d4 in enumerate(defs):
        ratios = [series[8 + 127 * gu + 106] / gear4u.armor_4u(exe, 33, k)['defense'] for k, gu in ANCHORS[tier][g]]
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
    for pair, parts, tpl, model, tier, swap in PAIRS:
        recipes = []
        for (part, _), k in zip(gear4u.PARTS, parts):
            r = [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k)]
            assert r == [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k + 1)], (pair, part)
            recipes.append([(SUBSTITUTES.get(n, n), c) for n, c in r])
        defs = [gear4u.armor_4u(exe, 33, parts[0] + g)['defense'] for g in range(2)]
        specs.append(dict(template=tpl, model=model, parts=parts, defense=defense_map(exe, series, tier, defs),
                          tree=tree, recipes=recipes, scrap=None, level_swap=swap, template_word=TEMPLATE_WORD))
    return specs


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    mats = items_em007_01.materials(R, exe)
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
