"""gear_em057_01.py : Stygian Zinogre's armor (Zinogre U: HR, Zinogre Z: G = 2 series pairs, 20 pieces) as records
appended to GU's loaded tables -> data file sections TBLA / TXTA (gen/*-armor.sec, tools/portdata.py; module/gear.c).
Formats, 4U records and the shared rules: tools/gear4u.py (armors: several pairs). Weapons: gear_weapons_em057_01.py.
Models: build.sh step armor (tools/armor4u2gu.py, the 40 arcs pl_{m,f}_<part>{169,170,438,439} from the 3DS image).
  gear_em057_01.py          write the sections
  gear_em057_01.py show     print them only
4U data (C, notes/phase1-assets.md 4c): per pair the Blademaster piece IDs below (Gunner = ID + 1), rarity 6 (U) / 9
(Z), models 169 / 170 (U) and 438 / 439 (Z) (4U armor record +0 / +2 = male / female model, C: Dalamadur's Rebellion
193 / 194; 4U Zinogre X = 336 = GU Zinogre X; unused in GU, C), recipes = 4U's (every item exists in GU or is ours).
Choices (the rules of Dalamadur's / Gogmazios' armor, user OK 2026-10-21; listed for review):
  - Templates: GU EX Zinogre Helm / Cap (458 / 459, HR rarity 6) for U, Zinogre Helm X / Cap X (920 / 921, rarity 9)
    for Z: max level, limit levels, defense table, sound, look.
  - Defense: 4U defense x the mean GU / 4U ratio of same-tier 4U monster sets GU also has (ANCHORS): HR rarity 6
    Agnaktor (59 / 30 -> 60 / 30) and Regios S (58 / 29 -> 60 / 30); G Zinogre X (90 / 49 -> 120 / 72).
  - Skills by GU tree name (TREE_4U_GU for renamed trees).
  - Level rows: the template's (EX Zinogre 9 levels, Zinogre X 5), its Zinogre materials swapped by role (for
    review): Jasper -> S.Zinogre Umbrage, Skymerald -> S.Zinogre Skymerald (gems), Hyper Zinogre Shell -> S.Zinogre
    Carapace, Hyper Zinogre Cortex -> S.Zinogre Cortex (GU has no Hyper Stygian); the generic Hyper Heavyclaw stays.
    Scraps given back: the template's.
  - Default dye = 4U's colour index (0x26 both series).
  - Recipe items GU lacks (head pieces) -> the substitutes Dalamadur's weapons use (gear_weapons_em090.py, for review):
    Yoldspar Ore -> Fucium Ore (HR ore), Cosmicite Ore -> Meldspar Ore (top regular G ore).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em057_01, portdata           # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402
NAME = 'stygian_zinogre'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, tier, level-row swaps)
PAIRS = [('Zinogre U', [140, 141, 136, 135, 137], (458, 459), (169, 170), 'HR',
          {'Zinogre Jasper': 'S.Zinogre Umbrage', 'Hyper Zinogre Shell': 'S.Zinogre Carapace',
           'Hyper Zinogre Cortex': 'S.Zinogre Cortex'}),
         ('Zinogre Z', [598, 602, 586, 586, 594], (920, 921), (438, 439), 'G',
          {'Zinogre Skymerald': 'S.Zinogre Skymerald', 'Hyper Zinogre Cortex': 'S.Zinogre Cortex'})]
# tier -> ([(4U head ID, GU series)] Blademaster, [...] Gunner)
ANCHORS = {'HR': ([(310, 468), (704, 476)], [(311, 469), (705, 477)]),
           'G': ([(596, 920)], [(597, 921)])}
TREE_4U_GU = {}
DROPPED_TREES = set()
TEMPLATE_WORD = 'Zinogre'
SUBSTITUTES = {'Yoldspar Ore': 'Fucium Ore', 'Cosmicite Ore': 'Meldspar Ore'}


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
    mats = items_em057_01.materials(R, exe)
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
