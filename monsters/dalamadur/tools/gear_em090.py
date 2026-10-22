"""gear_em090.py : Dalamadur's armor (Rebellion / Riot: HR, EX, X, Z = 4 series pairs, 40 pieces) as records appended
to GU's loaded tables -> data file sections TBLA / TXTA (gen/*-armor.sec, tools/portdata.py; module/gear.c).
Formats, 4U records and the shared rules: tools/gear4u.py (armors: several pairs). Weapons: to come (plan.md goal F).

  gear_em090.py          write the sections
  gear_em090.py show     print them only

4U data (C, dump/scratch/dalamadur-session/armor_skills.py, phase0.md): per pair the Blademaster piece IDs below
(Gunner = ID + 1), rarity 7 (HR, EX) / 10 (X, Z), models 193 / 194, 298 / 299, 348 / 349, 452 / 453 (male = female;
unused in GU, arcs from tools/armor4u2gu.py, build.sh armor), recipes = 4U's (every item exists in GU or is ours).
Choices (the rules of Gogmazios' / Tigerstripe's armor, user OK 2026-10-21; listed for review):
  - Templates: GU Akantor Mask / Fangs (590 / 591, HR rarity 7) for HR and EX, Akantor Mask X / Fangs X (1054 /
    1055, rarity 10) for X and Z (Gogmazios' template): max level, limit levels, defense table, sound, look.
  - Defense: 4U defense x the mean GU / 4U ratio of the same-tier 4U sets GU also has (ANCHORS; X = Gogmazios'
    anchors, so 4U 110 / 64 give the same GU 132 / 77 as Gogma X). GU weakened the EX sets (4U EX Kaiser / EX
    Kushala 81 -> GU 70 / 76), so EX Rebellion (4U 81) lands BELOW plain Rebellion (4U 69): to review.
  - Skills by GU tree name; 4U PunishDraw = GU 'Punish Draw' (41, +10 = Punishing Draw, C); FreeElemnt (Awaken)
    has no GU tree: dropped (as Tigerstripe), so Rebellion Z keeps Status Res 10, Edgemaster 3 / SteadyHand 3,
    Expert -15, PunishDraw / Rapid Fire 10.
  - Level rows: the template's; Akantor Gem -> Skyblade Gem (HR), Great Wyvern Crystal -> Skyblade Drgnsphire (G,
    as Gogmazios' Dragonsphire). Scraps given back: Dalamadur Scrap (HR, EX) / Scrap+ (X, Z) for the template's.
  - Default dye = 4U's colour index (0x20 HR / EX, 0x41 X, 0x0f Z).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em090, portdata              # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402

NAME = 'dalamadur'
# (pair, 4U Blademaster IDs head / body / arms / waist / legs, GU template pair, model pair, tier, 4U scrap, swaps)
PAIRS = [('Rebellion', [286, 287, 286, 281, 283], (590, 591), (193, 194), 'HR', 951, {'Akantor Gem': 'Skyblade Gem'}),
         ('EX Rebellion', [424, 428, 412, 412, 420], (590, 591), (298, 299), 'EX', 951, {'Akantor Gem': 'Skyblade Gem'}),
         ('Rebellion X', [654, 658, 642, 642, 650], (1054, 1055), (348, 349), 'X', 1700,
          {'Great Wyvern Crystal': 'Skyblade Drgnsphire'}),
         ('Rebellion Z', [658, 662, 646, 646, 654], (1054, 1055), (452, 453), 'X', 1700,
          {'Great Wyvern Crystal': 'Skyblade Drgnsphire'})]
# tier -> ([(4U head ID, GU series)] Blademaster, [...] Gunner): 4U HR Akantor Mask / Ukanlos Mask / Kaiser Crown /
# Kushala Glare = GU Akantor Mask / Ukanlos Mask / Kaiser Crown S / Kushala Glare S (GU renamed its HR versions);
# EX Kaiser / EX Kushala; X = Gogmazios' (gear_em089.py: Kaiser Crown X, Akantor Mask X / Kaiser Mask X)
ANCHORS = {'HR': ([(132, 590), (338, 594), (280, 570), (240, 560)], [(133, 591), (339, 595), (281, 571), (241, 561)]),
           'EX': ([(144, 572), (242, 562)], [(145, 573), (243, 563)]),
           'X': ([(634, 1002), (636, 1054)], [(635, 1003)])}
TREE_4U_GU = {'PunishDraw': 'Punish Draw'}
DROPPED_TREES = {'FreeElemnt'}
TEMPLATE_WORD = 'Akantor'


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
    for pair, parts, tpl, model, tier, scrap4, swap in PAIRS:
        recipes = []
        for (part, _), k in zip(gear4u.PARTS, parts):
            r = [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k)]
            assert r == [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(exe, part, k + 1)], (pair, part)
            assert len(r) == 4, (pair, part, r)
            recipes.append(r)
        defs = [gear4u.armor_4u(exe, 33, parts[0] + g)['defense'] for g in range(2)]
        specs.append(dict(template=tpl, model=model, parts=parts, defense=defense_map(exe, series, tier, defs),
                          tree=tree, recipes=recipes, scrap=mats.gu_item(scrap4), level_swap=swap,
                          template_word=TEMPLATE_WORD))
    return specs


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    mats = items_em090.materials(R, exe)
    specs = armor_specs(R, exe, mats)
    for (pair, *_), s in zip(PAIRS, specs):
        print('%-13s defense %s' % (pair, s['defense']))
    tables, texts = gear4u.armors(NAME, [mats], specs, R, exe)
    secs = [portdata.tbla(tables), portdata.txta(texts)]
    if sys.argv[1:] == ['show']:
        for s in secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        return
    for s in secs: print('wrote', portdata.write_section(NAME, s, 'armor'))


if __name__ == '__main__':
    main()
