"""gear_seltas.py : the Seltas Z armor (4U, 1 series pair, 10 pieces, crafted from Desert Seltas Queen's and Desert Seltas' materials in 4U) as
records appended to GU's loaded tables -> data file sections TBLA / TXTA of the desert_seltas_queen entry (gen/desert_seltas_queen/*-armor.sec,
tools/portdata.py; module/gear.c). Formats, 4U records and the shared rules: tools/gear4u.py. Weapons: gear_weapons_seltas.py. Models: build.py
step armor (tools/armor4u2gu.py, the 20 arcs pl_{m,f}_<part>{430,431}).
  gear_seltas.py          write the sections
  gear_seltas.py show     print them only
4U data (C, 2026-11-09): the pieces whose 4U create recipes are their materials, per part the Blademaster piece ID below (Gunner = ID + 1),
rarity 9, models 430 / 431 (no GU armor arc has them): Helm, Mail, Vambraces, Greaves Z of the Queen's materials, Faulds Z of his. The set
sits in the Queen's entry (most of its materials are hers); the recipes name both entries' materials.
Choices (the rules of Black Gravios', Monoblos', Tidal Najarala's and Shrouded Nerscylla's armor, listed for review):
  - Template: GU Seltas X (914 / 915, G rank, the same species line: 4U's Seltas X is the Seltas Queen's G set): max level, limit levels,
    defense table, sound, look.
  - Defense: 4U defense x the GU / 4U ratio of the template's set: 4U Seltas Helm X / Cap X (ANCHORS: 96 / 52) -> GU Seltas X (122 / 73).
    Scaled on GU's balance, as the user asked ("Skaliere ... Waffen und Rüstungen wenn nötig auf MHGU Niveau").
  - Skills by GU tree name: GU has every tree of the set (C), none dropped.
  - Level rows: the template's 5, the Seltas Queen's own material swapped for hers (LEVEL_SWAP: GU's rows ask Hyper S.Queen Cortex; GU has
    no Hyper Desert Seltas Queen, as Monoblos' Hyper Diablos Cortex and Tidal's Hyper Najarala Cortex); D.S.QueenConcentrate and the armor
    spheres stay.
  - Recipe items GU lacks: SUBSTITUTES: S.Queen Concentrate -> D.S.QueenConcentrate (items_seltas.SUBSTITUTES, GU's own choice for its
    Seltas Queen).
  - Resists: 4U's Faulds Z / Coat Z (his piece) differ from the other four (C: Blademaster fire 0 water 0 against 3 / -1, Gunner 1 / 1
    against 4 / 0). GU's series holds one set for all five parts (+23; its per-part table armorResistData is used by no GU series, C):
    the other four parts' set (gear4u res_majority), a DEVIATION on that piece.
  - Default dye = 4U's colour index.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_seltas, portdata             # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402
NAME = 'desert_seltas_queen'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, level-row swaps)
PAIRS = [('Seltas Z', [536, 540, 524, 524, 532], (914, 915), (430, 431), {'Hyper S.Queen Cortex': 'D.S.Queen Cortex'})]
TREE_4U_GU = {}
DROPPED_TREES = set()
TEMPLATE_WORD = 'S.Queen'                # no level-row material of the normal Seltas Queen may stay ('D.S.Queen ...' splits apart)
SUBSTITUTES = {'S.Queen Concentrate': 'D.S.QueenConcentrate'}


def anchors(t4):
    """([(4U head ID, GU series)], [..]) Blademaster, Gunner: 4U's piece of GU's template name"""
    hit = {n: k for k, n in enumerate(t4['HeadName']) if n in ('Seltas Helm X', 'Seltas Cap X')}
    return [(hit['Seltas Helm X'], 914)], [(hit['Seltas Cap X'], 915)]


def defense_map(exe, series, defs, anch):
    """{4U defense: GU defense} of one pair's Blademaster / Gunner defenses `defs`"""
    out = {}
    for g, d4 in enumerate(defs):
        ratios = [series[8 + 127 * gu + 106] / gear4u.armor_4u(exe, 33, k)['defense'] for k, gu in anch[g]]
        out[d4] = int(d4 * sum(ratios) / len(ratios) + 0.5)
    return out


def armor_specs(R, exe):
    t4 = text4u('eng')
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    series = res['table\\armorSeriesData']
    gst = gmd(gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\skillTypeData_eng'])
    gtree = {gst[i]: i // 2 for i in range(0, len(gst), 2)}
    anch = anchors(t4)

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
        specs.append(dict(template=tpl, model=model, parts=parts, defense=defense_map(exe, series, defs, anch),
                          tree=tree, recipes=recipes, scrap=None, level_swap=swap, template_word=TEMPLATE_WORD,
                          res_majority=True))
    return specs


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    mats = [items_seltas.materials(n, R, exe) for n in ('desert_seltas_queen', 'desert_seltas')]
    specs = armor_specs(R, exe)
    for (pair, *_), s in zip(PAIRS, specs):
        print('%-10s defense %s' % (pair, s['defense']))
    tables, texts = gear4u.armors(NAME, mats, specs, R, exe)
    secs = [portdata.tbla(tables), portdata.txta(texts)]
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section(NAME, s, 'armor'))


if __name__ == '__main__':
    main()
