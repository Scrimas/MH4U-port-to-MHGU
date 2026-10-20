"""gear_em067_01.py : Tigerstripe Zamtrios armor (Zamtrios Z) and its 19 weapons as records appended to GU's loaded
tables -> data file sections TBLA / TXTA (gen/*-armor.sec, gen/*-weapons.sec, tools/portdata.py; module/gear.c).
Formats, 4U records and the shared rules: tools/gear4u.py (armor), tools/weapons4u.py (weapons); 4U data:
notes/content-data.md sections 5 / 6.

  gear_em067_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_em067_01.py show     print them only

Armor (choices, user 2026-10-20):
  - 4U "Zamtrios Z" (G rank, the only series made from Tigerstripe materials), Blademaster head / body / arms / waist
    / legs 528 / 532 / 516 / 516 / 524 (Gunner + 1). GU has Zamtrios and Zamtrios X only.
  - Template GU Zamtrios Helm X / Cap X (851 / 852, rarity 8 like 4U's set): max level, limit levels, defense table,
    sound, scraps given (Heavy Zamtrios Scrap); level rows' Hyper Zamtrios Piel -> T.Zamtrios Piel. Default dye =
    4U's colour 0x36 (gold ff 91 41; the template's icy 0x0b made it silver, test 2026-10-21).
  - Defense: 4U 86 / 46 x GU / 4U Zamtrios X (102 / 84, 61 / 45) -> 104 / 62.
  - Skills by name (Stam Recov, Rec Speed, Tremor Res, Bleeding); 4U FreeElemnt (Awaken, 5 points on the set, no
    skill at 5) has no GU tree: left out.
  - Recipes: 4U's; Meaty Piel (4U Zamite G hide, no GU item) -> Meaty Hide+ (GU's Zamite hide).
  - Model: 4U 436 / 437 (unused in GU; arcs from tools/armor4u2gu.py).
Weapons (choices, user 2026-10-20): the 17 Kiranico lists + the Lance line its 4U tables tie to Tigerstripe
  (Carnelian Lance -> Crystalis). Each line is its own tree (4U's first weapons upgrade from 4U G-rank Zamtrios
  weapons GU lacks): first weapon from its create recipe, then the upgrades. Paralysis (4U status 2 -> GU mElement
  7); the Lance's hidden 4U paralysis made visible (GU has no Awaken). Stand-ins: GU's Zamtrios-line weapons (Sharfin
  Sword, Meaty Press, Omnivicious, Notched Tyrant, Deepbuster, Ice Cold Alighter, Cool Cleavers); IG Deep Blue
  Glaive, CB Akantor C. Blade (GU has no Zamtrios IG / CB line). Bows (kiranico page data, 2026-10-20): no element,
  arc shot Blast, charges Spread / Spread / Rapid / Rapid (levels from the 4U record), coatings Power, Poison, Para,
  Paint. IG: Cutting kinsect (GU Culldrone). Recipe items GU lacks -> same-monster GU items (SUBSTITUTES).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tigerstripe_zamtrios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import gear4u, items_em067_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, RomFS, gu_arc, gmd, text4u   # noqa: E402

NAME = 'tigerstripe_zamtrios'
PARA = 7                                 # GU mElement paralysis (4U status 2)
TEMPLATE = (851, 852)                    # GU Zamtrios Helm X / Cap X
TEMPLATE_DEF = (102, 61)
DROPPED_TREES = {'FreeElemnt'}
ARMOR_SUBST = {'Meaty Piel': 'Meaty Hide+'}
SUBSTITUTES = {'Rhenoplos Bone': 'Large Herbivore Bone', 'B.Diablos Cortex': 'Diablos Cortex',
               'D.S.Queen Pectus+': 'S.Queen Pectus+', 'Blackcurl Stouthorn': 'Diablos Hardhorn',
               'B.Tigrex Hardfang': 'Tigrex Hardfang', 'Dire Blastheart': 'Tigrex Mantle'}
# GU NN, GU stand-in ID, 4U IDs (create weapon first, then each upgrade of the previous one)
LINES = [(1, 44, (175, 176)),            # Agate Saw -> Zamtrista Saw
         (2, 40, (177, 178)),            # Puffer Smash -> Pufferpounder
         (3, 52, (167, 168)),            # Carnelian Lance -> Crystalis
         (8, 14, (130, 131)),            # Allagi Tigermaw -> Zamtreacherous Maw
         (9, 15, (144, 145)),            # Tetrozonata -> Velenofragola
         (10, 27, (122, 123)),           # Quartzlight -> Crystal Lode
         (11, 12, (151, 152)),           # Sandgnashers -> Psammophages
         (13, 23, (72, 73, 74)),         # Sand Fauchard -> Sand Fauchard+ -> Iorovellir
         (14, 41, (63, 64))]             # The Haboob -> Desert Rose
# bow (kiranico): arc shot Blast (2), 3 charge levels (+ the 4th with Load Up, as Gogmazios'), coatings Power Lv1 /
# Lv2, Poison, Para, Paint + [11] (set on every GU row); charge shots (GU kind = 4U + 1): Quartzlight Spread3 Spread4
# Rapid4 Rapid4, Crystal Lode Spread4 Spread5 Rapid4 Rapid5
BOW = dict(kyoku=2, tame=3, bottles=(1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1), cshot={122: (8, 9, 4, 4), 123: (9, 10, 4, 5)})
IG_INSECT = 1                            # Culldrone (cutting; 4U extra 0 = Cutting)
# sound sets: each 4U arc (dump/gear_src/weapons/4u/data/pl_<pfx><model>.arc) holds its line's parent set, not its
# own (Lance 90: lan049_1..6), and GU ships each of those sets (wNN/snd/NNN.arc, the 4U waves + the class's _90
# wave), so mSrqrNo = that set and no sound arc is written (GU's snd/090.arc is another lance set: not replaced)
SRQR = {1: 44, 2: 55, 3: 49, 8: 35, 9: 43, 10: 30, 11: 38, 13: 21, 14: 12}
GEAR_SRC = os.path.join(ROOT, 'dump/gear_src/weapons/4u/data')


def sound_set_4u(nn, model):
    """the wave set number of the 4U weapon arc of a model (its waves are named <pfx>NNN_k)"""
    import arcpack, re
    pfx = {1: 'one', 2: 'ham', 3: 'lan', 8: 'axe', 9: 'gun', 10: 'bow', 11: 'sou', 13: 'rod', 14: 'gaxe'}[nn]
    ents = arcpack.read(open(os.path.join(GEAR_SRC, 'pl_%s%03d.arc' % (pfx, model)), 'rb').read())[1]
    sets = {re.match(r'[a-z]+(\d+)_', p.split('\\')[-1]).group(1) for p, t, d in ents if '\\wave\\' in p}
    assert len(sets) == 1, (nn, model, sets)
    return int(sets.pop())


def armor_spec(R):
    t4 = text4u('eng')
    gst = gmd(gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\skillTypeData_eng'])
    gtree = {gst[i]: i // 2 for i in range(0, len(gst), 2)}
    def tree(tree4, name):
        if name in DROPPED_TREES: return None
        return gtree[name]
    parts = [528, 532, 516, 516, 524]
    recipes = []
    for (part, _), k in zip(gear4u.PARTS, parts):
        r = [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(open(EXE, 'rb').read(), part, k)]
        assert r == [(t4['itemName'][it], c) for it, c in gear4u.armor_recipe_4u(open(EXE, 'rb').read(), part, k + 1)]
        recipes.append([(ARMOR_SUBST.get(n, n), c) for n, c in r])
    return dict(name=NAME, materials=[items_em067_01.MATERIALS], template=TEMPLATE, model=(436, 437), parts=parts,
                defense={86: round(86 * TEMPLATE_DEF[0] / 84), 46: round(46 * TEMPLATE_DEF[1] / 45)}, tree=tree,
                recipes=recipes, scrap=None, level_swap={'Hyper Zamtrios Piel': 'T.Zamtrios Piel'},
                template_word='Zamtrios')


def weapon_spec():
    exe = open(EXE, 'rb').read()
    classes, kire = [], []
    for nn, sid, ids4u in LINES:
        c = dict(nn=nn, standin=sid, ids4u=ids4u, srqr=SRQR[nn])
        c.update({10: dict(bow=BOW), 13: dict(insect=IG_INSECT)}.get(nn, {}))
        model = weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], ids4u[0])['model']
        assert sound_set_4u(nn, model) == SRQR[nn], (nn, model)
        classes.append(c)
        if nn != 10:
            for i in ids4u:
                w = weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)
                assert w['status'] == 2, (nn, i, w)         # every Tigerstripe melee weapon: paralysis
                if w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em067_01.MATERIALS, classes=classes, status={2: PARA}, kire_4u=kire,
                pwl_fix=[], substitutes=SUBSTITUTES)


def main():
    R = RomFS(gear4u.GU_ROMFS)
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    for g in range(2):
        assert res['table\\armorSeriesData'][8 + 127 * TEMPLATE[g] + 106] == TEMPLATE_DEF[g]
    tables, texts = gear4u.armor(armor_spec(R), R)
    armor_secs = [portdata.tbla(tables), portdata.txta(texts)]
    ws = weapon_spec()
    wt, wtexts, hooks, summary, log, kire = weapons4u.build(ws)
    weapon_secs, hk = weapons4u.sections(wt, wtexts, hooks, ws['pwl_fix'])
    have = set(open(weapons4u.OUT_HOOKS).read().split())
    missing = [l for l in hk.splitlines() if not set(l.split()) <= have]
    if sys.argv[1:] == ['show']:
        for s in armor_secs: print(s.tag, portdata.decode(s.tag, s.bytes()))
        weapons4u.show(summary, log, kire, wt, hooks, ws['status'])
        print('hooks missing from module/gear_hooks.txt:', missing or 'none')
        return
    assert not missing, 'module/gear_hooks.txt lacks %s: run tools/weapons4u.write_hooks' % missing
    for s in armor_secs: print('wrote', portdata.write_section(NAME, s, 'armor'))
    for s in weapon_secs: print('wrote', portdata.write_section(NAME, s, 'weapons'))


if __name__ == '__main__':
    main()
