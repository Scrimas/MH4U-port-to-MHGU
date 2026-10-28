"""gear_weapons_em057_01.py : the 37 Stygian Zinogre weapons (4U's 12 "Brimstren" lines) as records appended to GU's
loaded weapon tables -> data file sections TBLA / TXTA of the stygian_zinogre entry (gen/*-weapons.sec,
tools/portdata.py; read by module/gear.c). Tables, 4U records and the rules every monster shares: tools/weapons4u.py;
this file: Stygian Zinogre's inputs. Facts: C = read in code / data, S = strong, G = guess.
Scope and study: monsters/stygian_zinogre/notes/weapons.md.

  gear_weapons_em057_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em057_01.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe): the 4U weapons whose recipes use Stygian materials ("Brimstren X" HR rarity 6 -> "X+" G ->
"Stygian <vice / virtue>"; LS / Bow end in a "Charonian" weapon with its own model), followed along the upgrade table's
child IDs (record +16, weapons4u.UPGRADE_4U): each link single, the last without a child (checked). In 4U each line
branches off a Zinogre weapon (the parent below); the user's choice (2026-10-28): standalone lines, no GU weapon record
touched. The first weapon is forged: its 4U create recipe where 4U has one (Bow 41 Drakegaze, HH 25 Drakesong), else
the materials of its 4U upgrade recipe (the parent weapon left out; weapons4u class spec first_upgrade). Every later
weapon is an upgrade of the previous one, with its 4U upgrade recipe.
Data (C unless noted; weapons4u reads it all from the 4U records):
  - Elements: dragon on every class but the DBs; the DBs thunder (record) + dragon (second element: the record's +17
    = 3 / 18 / 19 indexes the 4U DB second-element table weapons4u.DB2_4U = dragon 28 / 32 / 36). No status, nothing
    hidden. Raw, affinity, defense, slots, rarity, price: the 4U records'.
  - Sharpness: the lines' 4U entries appended to kireajiData; mKireLevel = 2 x the 4U level.
  - GL: 4U extra 7 / 10 / 10 = Long Lv3 / Lv4 / Lv4. HH: 4U note set 6 = GU fueMusicData 6 (the tables are equal).
    SA: Power phial (4U 0).
  - Bowguns: ammo and loadable flags from the 4U records; 4U loadable ammo without a GU slot (Slicing, Demon / Armor
    and the HBG's indexes 37 / 38) left out (logged).
  - Bow: 4 charges (4U +22, GU = 4U + 1: Pierce 2 / Rapid 3 / Rapid 4 / Spread 4 .. Charonian Pierce 2 / Rapid 3 /
    Rapid 5 / Spread 5), 3 charge levels, coatings Power / Poison / C.Range / Paint (4U mask 0x66).
Stand-ins (records copied, then every 4U field set): the GU Zinogre weapon of each class (the 4U lines' own parents,
  GU-folded): melee and the bow lend only fields 4U has no value for; kept from them (G, logged):
  - Bow arc shot: not in the 4U record -> Usurper's Rumble's (GU's form of 4U Distant Thunder, model 4: the Brimstren
    bow's 4U parent line) mKyoku.
  - Bowguns: recoil, reload, deviation (4U +5 = 0 on all six records), rapid / crouch fire, special ammo, slot 32 from
    the GU parent's final level row (HBG Loyal Thunder 101 = Orcus Quarcus, LBG Usurper's Crime 18 = Oppressor's
    Rift).
Models (C): 4U's numbers (allocations.toml weapon_models, free in GU), arcs tools/weapon4u2gu.py (build.sh weapons).
  Motion sets: GU's pl_wNN record at each model number points at a gNN arc GU has (checked): no PWLF fix. lan054 /
  lbg030 need a sphere-map fallback the converter lacks (notes/weapons.md section 4, Open 1).
Sounds (C): every 4U arc holds its own model's set (checked) -> mSrqrNo = mModelID, converted by tools/wsnd4u2gu.py
  (build.sh weapons), except the HBG: 4U hbg046 holds set 19 = Oppressor's Wedge's (4U model 19 = GU Loyal Thunder's
  model 19), so mSrqrNo 19 = GU's own snd/019.arc (no conversion).
Recipe items GU lacks -> SUBSTITUTES (for review): one, in Brimstren Drakesong+'s upgrade.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em057_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'stygian_zinogre'
STATUS = {}                              # no 4U status on any Stygian weapon (checked by weapons4u.elem_status)
# recipe items GU lacks (G, for review): GU has no Ivory Lagiacrus -> the base species' item of the same part and rank
# (as Dalamadur's B.Gravios -> Gravios): I.Lagi D-Shocker (4U 1780, G shell) -> Deathly Shocker (4U 1778 = GU 879)
SUBSTITUTES = {'I.Lagi D-Shocker': 'Deathly Shocker'}
# GU NN, GU stand-in ID (the GU Zinogre weapon of the class), 4U parent (checked: its children include the line's
# first weapon), 4U IDs (first weapon, then each upgrade of the previous one), first weapon forged from its 4U upgrade
# recipe (no 4U create recipe)
LINES = [(0, 9, 28, (29, 155, 156), True),           # Usurper's Storm; Despot's Blackstorm -> Drakepride .. Acedia
         (1, 19, 27, (28, 159, 160), True),          # Usurper's Firebolt; Despot's Crookbolt -> Drakescale .. Luxuria
         (2, 47, 25, (26, 159, 160), True),          # Usurper's Thunder; Despot's Crackle -> Drakemaw .. Industria
         (3, 42, 53, (56, 161, 162), True),          # Usurper's Coming; Despot's Cacophony -> Draketail .. Ira
         (4, 101, 95, (97, 98), True),               # Loyal Thunder; Oppressor's Wedge -> Drakemouth, Humilitas
         (6, 18, 17, (18, 19, 103, 104), True),      # Usurper's Crime; Despot's Wildfire -> Drakekiss .. Invidia
         (7, 28, 41, (43, 152, 153), True),          # Usurper's Boltslicer; Usurper Boltslicer+ -> Drakebone .. Charonian
         (8, 25, 25, (26, 124, 125), True),          # Usurper's Downpour; Despot's Cloudburst -> Drakefang .. Vanagloria
         (9, 36, 54, (56, 165, 166), True),          # Usurper's Roar; Usurper's Roar+ -> Drakeblood .. Avaritia
         (10, 3, 39, (41, 42, 132, 133), False),     # Usurper's Rumble; Distant Thunder II -> Drakegaze .. Charonian
         (11, 20, 63, (65, 169, 170), True),         # Usurper's Fulgur; Despot's Blitz -> Drakeclaws .. Superbia
         (12, 43, 23, (25, 111, 112), False)]        # Usurper's Growl; Usurper's Growl+ -> Drakesong .. Tristitia
SRQR = {4: 19}                           # 4U hbg046 holds Oppressor's Wedge's set 19 = GU snd/019.arc (Loyal Thunder)
BOW = dict(kyoku=None)                   # arc shot: the stand-in's; tame, charges, coatings: the 4U record's
PWL_FIX = []                             # every model's GU motion set has its gNN arc (check_pwl)
GEAR_SRC = os.path.join(ROOT, 'dump/gear_src/weapons/4u/data')
PFX = {0: 'two', 1: 'one', 2: 'ham', 3: 'lan', 4: 'hbg', 6: 'lbg', 7: 'swo', 8: 'axe', 9: 'gun', 10: 'bow',
       11: 'sou', 12: 'hue', 13: 'rod', 14: 'gaxe'}


def sound_set_4u(nn, model):
    """the wave set number of the 4U weapon arc of a model (its waves are named <pfx>NNN_k)"""
    ents = arcpack.read(open(os.path.join(GEAR_SRC, 'pl_%s%03d.arc' % (PFX[nn], model)), 'rb').read())[1]
    sets = {re.match(r'[a-z]+(\d+)_', p.split('\\')[-1]).group(1) for p, t, d in ents if '\\wave\\' in p}
    assert len(sets) == 1, (nn, model, sets)
    return int(sets.pop())


def children_4u(exe, nn, i):
    """child weapon IDs of a 4U weapon (upgrade table record +16, 4 x u16)"""
    ctype = weapons4u.CLASS_INFO[nn][3]
    a = weapons4u.u32(exe, weapons4u.UPGRADE_4U + 4 * (ctype - 7)) + 24 * i - EXE_BASE
    return [c for c in struct.unpack_from('<4H', exe, a + 16) if c]


def check_pwl(R, exe):
    """every model's GU motion set (pl_wNN record at the model number) has its gNN arc, and no GU model arc / snd arc
    exists at our numbers (the HBG's snd 019 is GU's own)"""
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    for nn, sid, parent, ids4u, _ in LINES:
        pwl = res['weapon\\w%02d\\pwl\\pl_w%02d' % (nn, nn)]
        for m in {weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'] for i in ids4u}:
            assert m < struct.unpack_from('<I', pwl, 4)[0], (nn, m)
            g = struct.unpack_from('<I', pwl, 8 + 16 * m)[0]
            assert '/nativeNX/arc/weapon/w%02d/g%02d.arc' % (nn, g) in R.files, (nn, m, g)
            assert '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, m) not in R.files, (nn, m)
            assert '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, m) not in R.files, (nn, m)
    for nn, s in SRQR.items():
        assert '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, s) in R.files, (nn, s)


def spec(R):
    exe = open(EXE, 'rb').read()
    classes, kire = [], []
    for nn, sid, parent, ids4u, first_upgrade in LINES:
        ptab = weapons4u.CLASS_INFO[nn][2]
        assert ids4u[0] in children_4u(exe, nn, parent), (nn, parent)
        for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; it ends there
            assert children_4u(exe, nn, a) == ([b] if b else []), (nn, a, children_4u(exe, nn, a))
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        for w in ws:                                     # each 4U arc's sound set: its own model's, or SRQR's
            assert sound_set_4u(nn, w['model']) == SRQR.get(nn, w['model']), (nn, w['model'])
        c = dict(nn=nn, standin=sid, ids4u=ids4u, first_upgrade=first_upgrade)
        if nn in SRQR: c['srqr'] = SRQR[nn]
        c.update({10: dict(bow=BOW)}.get(nn, {}))
        classes.append(c)
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em057_01.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
                pwl_fix=PWL_FIX, substitutes=SUBSTITUTES)


def main():
    R = RomFS(gear4u.GU_ROMFS)
    check_pwl(R, open(EXE, 'rb').read())
    s = spec(R)
    tables, texts, hooks, summary, log, kire = weapons4u.build(s)
    secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'])
    have = set(open(weapons4u.OUT_HOOKS).read().split())
    missing = [l for l in hk.splitlines() if not set(l.split()) <= have]
    weapons4u.show(summary, log, kire, tables, hooks, s['status'])
    for short, i, name, b, r, mats, k in summary:        # elements (weapons4u.show prints statuses only)
        if 'mElement1' in b:
            print('element %-6s %3d %-24s %d:%d + %d:%d' % (short, i, name, b['mElement1'], r['mElementValue1'] * 10,
                                                           b['mElement2'], r['mElementValue2'] * 10))
        elif 'mElement' in b:
            print('element %-6s %3d %-24s %d:%d' % (short, i, name, b['mElement'], r['mElementValue'] * 10))
    print('hooks missing from module/gear_hooks.txt:', missing or 'none')
    if sys.argv[1:] == ['show']:
        return
    assert not missing, 'module/gear_hooks.txt lacks %s: run tools/weapons4u.write_hooks' % missing
    for sec in secs: print('wrote', portdata.write_section(NAME, sec, 'weapons'))


if __name__ == '__main__':
    main()
