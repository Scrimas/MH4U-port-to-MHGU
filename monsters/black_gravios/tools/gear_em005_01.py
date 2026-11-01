"""gear_em005_01.py : Black Gravios' armor (4U Gravios U: HR, Gravios Z: G = 2 series pairs, 20 pieces; in 4U both are
crafted from Black Gravios materials) as records appended to GU's loaded tables -> data file sections TBLA / TXTA
(gen/*-armor.sec, tools/portdata.py; module/gear.c). Formats, 4U records and the shared rules: tools/gear4u.py.
Weapons: gear_weapons_em005_01.py. Models: build.sh step armor (tools/armor4u2gu.py, the 40 arcs
pl_{m,f}_<part>{185,186,394,395} from the 3DS image).
  gear_em005_01.py          write the sections
  gear_em005_01.py show     print them only
4U data (C, 2026-11-01): the pieces whose 4U create recipes use Black Gravios materials: per pair the Blademaster
piece IDs below (Gunner = ID + 1), rarity 6 (U) / 9 (Z), models 185 / 186 (U) and 394 / 395 (Z) (unused in GU: its
Gravios / Gravios X are 183 / 184 and 392 / 393), recipes = 4U's (every item exists in GU or is ours).
Choices (the rules of Stygian's armor, listed for review):
  - Templates: GU Gravios Helm / Cap (730 / 731, HR rarity 6) for U, Gravios Helm X / Cap X (922 / 923, rarity 9)
    for Z: max level, limit levels, defense table, sound, look.
  - Defense: 4U defense x the GU / 4U ratio of the plain Gravios set of the same tier (ANCHORS: 4U Gravios S 57 / 29
    -> GU Gravios 58 / 29, 4U Gravios X 96 / 52 -> GU Gravios X 120 / 72).
  - Skills by GU tree name (TREE_4U_GU for renamed trees); 4U Flame Aura has no GU tree: dropped (DROPPED_TREES).
  - Level rows: the template's (Gravios 9 levels, Gravios X 5); Z: Hyper Gravios Cortex -> B.Gravios Cortex (GU has
    no Hyper Black Gravios), Gravios Pallium -> B.Gravios Pallium; Gravios Medulla stays (4U's own recipes use it).
  - Default dye = 4U's colour index.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/black_gravios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em005_01, portdata           # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402
NAME = 'black_gravios'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, tier, level-row swaps)
PAIRS = [('Gravios U', [218, 219, 214, 213, 215], (730, 731), (185, 186), 'HR', {}),
         ('Gravios Z', [614, 618, 602, 602, 610], (922, 923), (394, 395), 'G',
          {'Hyper Gravios Cortex': 'B.Gravios Cortex', 'Gravios Pallium': 'B.Gravios Pallium'})]
# tier -> ([(4U head ID, GU series)] Blademaster, [...] Gunner)
ANCHORS = {'HR': ([(216, 730)], [(217, 731)]),
           'G': ([(612, 922)], [(613, 923)])}
TREE_4U_GU = {}
# 4U Flame Aura (skill: "monsters react as if you are carrying a Torch", C: 4U skillExp 256): GU has no torches and no
# such tree (GU's same-name sets with it, Agnaktor and Lava X, were reworked without it): dropped, a DEVIATION
DROPPED_TREES = {'Flame Aura'}
# no word check: Black Gravios shares Gravios' Medulla in 4U (his own armor recipes use it, C), so the templates' level
# rows keep it; their other Gravios materials are swapped (PAIRS level-row swaps)
TEMPLATE_WORD = None
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
    mats = items_em005_01.materials(R, exe)
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
