"""gear_weapons_em089.py : the 28 Gogmazios weapons as records appended to GU's loaded weapon tables
-> data file sections TBLA / TXTA / PWLF (gen/*-weapons.sec, tools/portdata.py; read by module/gear.c) and
module/gear_hooks.txt (load-exit hooks). Spec: notes/gear-weapons.md (sections 1-8; section numbers below refer to it);
tables, 4U records and the rules every monster shares: tools/weapons4u.py. This file: Gogmazios' inputs.

  gear_weapons_em089.py          write the sections and the hook list
  gear_weapons_em089.py show     print the per-weapon summary, the tables and the hooks; write nothing

Choices (notes section 8 unless noted):
  - IG line Messenger's Mark -> Luminary's Mark -> Limbo Lacrimosa (83 -> 84 -> 85).
  - Stand-ins = GU's Akantor weapons (sound sets reused, records copied).
  - mRare 9, mPrice = the 4U price (the brief's 80000 / 130000, IG 60000 / 120000 / 130000: checked), Sleep
    (mElement 8) at the 4U value / 10; the IG's hidden 4U sleep made visible.
  - Sharpness: 4U entries 88 / 100 / 89 appended to kireajiData as 164 / 165 / 166, mKireLevel = 2 x 4U level (12).
  - Recipes checked against notes/content-plan.md "Appendix" (+ IG upgrades).
  - Bowguns: ammo per kiranico (notes section 7); bow coatings Power Lv1/2, Sleep, Blast (+ [10], [11]).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import items_em089, portdata, weapons4u             # noqa: E402

SLEEP = 8                                # GU mElement sleep (4U status 3)
KIRE_4U_IDX = (88, 100, 89)              # 4U sharpness entries used by the Gogma weapons -> GU 164, 165, 166
# notes/content-plan.md "Appendix" (+ section 7's IG upgrades): create recipe, upgrade recipe(s), by item name
O, F, G, B, W, T = ('Gogmazios Offenders', 'Gogmazios Fortress', 'Gogmazios Gasher', 'Gogmazios Battlement',
                    'Gogmazios Fiberwing', 'Gogmazios Briartail')
OIL, DS, GEM, BONE = 'Heavy Drakesbone Oil', 'Wartorn Dragonsphire', 'Lrg Elder Dragon Gem', 'Lrg ElderDragon Bone'
RECIPES = {'GS': [{B: 5, F: 5, G: 2, OIL: 2}, {F: 8, O: 2, GEM: 1, DS: 1}],
           'SnS': [{G: 3, F: 5, T: 2, OIL: 3}, {O: 4, W: 2, GEM: 1, DS: 1}],
           'Hammer': [{B: 7, F: 4, OIL: 3, BONE: 5}, {G: 4, F: 5, GEM: 1, DS: 1}],
           'Lance': [{G: 2, O: 4, W: 2, OIL: 2}, {G: 2, F: 4, GEM: 1, DS: 1}],
           'LS': [{O: 4, W: 3, T: 2, OIL: 3}, {G: 4, F: 3, 'Gravios Pallium': 1, DS: 1}],
           'SA': [{B: 5, F: 5, G: 3, T: 2}, {G: 5, W: 3, GEM: 1, DS: 1}],
           'GL': [{F: 8, B: 4, W: 2, OIL: 4}, {O: 4, W: 2, BONE: 5, DS: 1}],
           'DB': [{O: 4, T: 1, F: 4, BONE: 8}, {OIL: 4, G: 3, GEM: 1, DS: 1}],
           'HH': [{B: 4, F: 4, O: 2, OIL: 1}, {W: 4, G: 2, GEM: 1, DS: 1}],
           'IG': [{F: 3, OIL: 4, DS: 1}, {G: 2, O: 2}, {T: 2, DS: 1}],
           'CB': [{G: 2, F: 8, O: 2, OIL: 3}, {F: 12, O: 3, GEM: 1, DS: 1}],
           'LBG': [{F: 8, O: 4, W: 5, DS: 1}],
           'HBG': [{F: 6, W: 4, OIL: 4, DS: 1}],
           'Bow': [{F: 8, W: 3, OIL: 2, G: 4}, {O: 5, T: 2, GEM: 1, DS: 1}]}
# bowgun ammo (kiranico, notes section 7) in GU slot order (section 2): Normal 1-3, Pierce 1-3, Pellet 1-3, Crag 1-3,
# Clust 1-3, Flaming, Water, Thunder, Freeze, Dragon, Poison 1-2, Para 1-2, Sleep 1-2, Exhaust 1-2, Recover 1-2,
# Paint, Tranq; "(n)" = listed but not loadable (count n, enable 0); slot 32 (unknown) is the stand-in's
AMMO = {165: '6 (10) (10) (4) 6 8 6 8 8 (2) 2 2 (2) (2) 2 0 0 0 0 0 0 0 2 0 3 3 3 3 2 2 2 2',   # Bethorned Dystopia
        141: '4 (10) (10) 4 8 6 (4) 7 7 (3) (3) 3 (2) 2 2 0 0 0 0 0 0 0 2 0 3 3 3 3 2 2 2 2'}   # Trembling Lordship
# bow (section 8): arc shot Blast, 3 charge levels (+ the 4th with Load Up, G), coatings Power Lv1/2, Sleep, Blast,
# and the two set on every GU row ([10], [11])
BOW = dict(kyoku=2, tame=3, bottles=(1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1),
           cshot={183: (9, 4, 9, 4), 184: (9, 4, 10, 5)})        # section 8 (Spread4 Rapid4 Spread4/5 Rapid4/5)
HH = (3, 2)                              # 4U note set purple/red/blue -> GU fueMusicData 2 = (2, 3, 4)
IG_INSECT = 1                            # Culldrone (cutting; 4U extra 0 = Cutting)
PRICES = {(13, 0): 60000, (13, 1): 120000}   # brief: IG 60000 / 120000 / 130000, else 80000 / 130000
# GU NN, GU stand-in ID, 4U IDs (create weapon first, then each upgrade of the previous one)
LINES = [(0, 71, (222, 223)),            # Akantor Broadsword
         (1, 63, (227, 228)),            # Akantor Duo
         (2, 18, (221, 222)),            # Demonlord Hammer
         (3, 48, (198, 199)),            # Demonlord Spear
         (4, 55, (141,)),                # Akantor Cannon
         (6, 58, (165,)),                # Demonlord Blaster
         (7, 68, (199, 200)),            # Akantor Katana
         (8, 56, (180, 181)),            # Akantor Switch Axe
         (9, 60, (201, 202)),            # Akantor Gunlance
         (10, 56, (183, 184)),           # Akantor Bow
         (11, 63, (208, 209)),           # Akantor Blades
         (12, 60, (164, 165)),           # Akantor Horn
         (13, 43, (130, 131, 132)),      # Demonlord Cudgel
         (14, 41, (98, 99))]             # Akantor C. Blade
# rPlayerWeaponList (weapon\wNN\pwl\pl_wNN) motion sets (mGmkMotNo, record of the model number + 4): every Gogma
# model number already has a record carrying 4U's value except two (tools/weapon4u2gu.py report): HBG 40 GU 1 (g01
# serves only GU model 22, another skeleton) -> 4U 0 = g00, used by 69 HBGs with hbg040's bones; SA 77 GU 8 (no
# g08.arc) -> 20, the set of all 20 GU axes with axe077's 4-bone skeleton. (path suffix, model, GU value, ours)
PWL_FIX = [('pl_w04', 40, 1, 0), ('pl_w08', 77, 8, 20)]


def spec():
    classes = []
    for nn, sid, ids4u in LINES:
        c = dict(nn=nn, standin=sid, ids4u=ids4u, recipes=RECIPES[weapons4u.CLASS_INFO[nn][0]])
        c.update({4: dict(ammo=AMMO), 6: dict(ammo=AMMO), 10: dict(bow=BOW), 12: dict(hh=HH),
                  13: dict(insect=IG_INSECT)}.get(nn, {}))
        classes.append(c)
    return dict(name='gogmazios', materials=items_em089.MATERIALS, classes=classes, status={3: SLEEP},
                kire_4u=KIRE_4U_IDX, pwl_fix=PWL_FIX)


def check(summary):
    """the Gogmazios brief's values (rarity 10, prices, sleep, sharpness level 6)"""
    for short, i, name, b, r, mats, k in summary:
        nn = [n for n, info in weapons4u.CLASS_INFO.items() if info[0] == short][0]
        assert b['mRare'] == 9 and r['mDefense'] == 0, (short, i)
        assert b['mPrice'] == PRICES.get((nn, k), 80000 if k == 0 else 130000), (short, i, b['mPrice'])
        if 'mKireLevel' in r:
            assert r['mKireLevel'] == 12 and b.get('mElement', b.get('mElement1')) == SLEEP, (short, i)


def main():
    s = spec()
    tables, texts, hooks, summary, log, kire = weapons4u.build(s)
    check(summary)
    secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'])
    weapons4u.show(summary, log, kire, tables, hooks, s['status'])
    if sys.argv[1:] == ['show']:
        return
    for sec in secs: print('wrote', portdata.write_section('gogmazios', sec, 'weapons'))
    print('wrote', weapons4u.write_hooks(hk))


if __name__ == '__main__':
    main()
