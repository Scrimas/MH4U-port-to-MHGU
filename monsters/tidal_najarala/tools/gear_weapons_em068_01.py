"""gear_weapons_em068_01.py : the Tidal Najarala weapons (4U's 7 lines of her materials) as records appended to GU's loaded weapon tables
-> data file sections TBLA / TXTA / KIRX of the tidal_najarala entry (gen/*-weapons.sec, tools/portdata.py; read by module/gear.c). Tables, 4U
records and the rules every monster shares: tools/weapons4u.py; this file: her inputs (as Monoblos' gear_weapons_em007_01.py). Facts: C =
read in code / data, S = strong, G = guess.

  gear_weapons_em068_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em068_01.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe, 2026-11-06): the 4U weapons with a create recipe of her materials, along the upgrade table's child IDs (record
+16, weapons4u.UPGRADE_4U):
  SnS    Lepis Prism -> Grootslang                      (157 158)
  Lance  Jingana -> Jingana+ -> Caduceus                (147 148 149)
  HBG    Azure Blast -> Azure Buster                    (113 114)
  LS     Hyddra -> Hyddra+ -> Alphard                   (156 157 158)
  SA     Cryoseism -> Illuyanka                         (151 152)
  HH     132 -> 133                                     (names from 4U)
  IG     Medusa -> Medusa+ -> Medusa Mirror             (65 66 67; the IG upgrade table has no child IDs: same model 34, the upgrades' rows
                                                         follow each other, checked in spec())
Each first weapon has a 4U create recipe and is forged from it (no GU record touched, the user's rule for Stygian). Left out as not hers
(one of her parts in another line's upgrade): Violet Pincer, Jajala Blade, Barroth Basher, Gaia Horizon, Weird Wacha Nakha, Monsieur Gore+,
Diviathan Gunlance, Viand Bowfish and others (their lines are not hers).
Data: raw, element, affinity, defense, slots, rarity, price, sharpness, bowgun ammo = the 4U records'.
Stand-ins (records copied, then every 4U field set): as Tigerstripe's and Monoblos' per class: SnS 44, Lance 52, HBG 97 (recoil / reload /
deviation / rapid fire / special ammo kept from it, logged by weapons4u), LS 81, SA 14, HH 43, IG 23.
Kinsect (C): 4U extra 1 = Impact on all three Medusa -> GU mInsectType 12 Mauldrone (insectData_eng 12; GU's own IGs are 1 Culldrone x 42, 12
Mauldrone x 38, 3 special ones).
Recipe items GU lacks (SUBSTITUTES, G, listed for review), the rules of the earlier ports: Desert Seltas Queen -> Seltas Queen, Black Diablos ->
Diablos, Brute Tigrex -> Tigrex, Meaty Piel -> Meaty Hide+, Stygian's items -> Zinogre's.
Models (C): 4U's numbers (allocations.toml weapon_models, free in GU), arcs tools/weapon4u2gu.py (build.py weapons).
Sounds (C): each 4U arc's own set (sound_set_4u, checked).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em068_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'tidal_najarala'
STATUS = {}
SUBSTITUTES = {'D.S.Queen Pectus+': 'S.Queen Pectus+', 'D.S.Queen Cortex': 'S.Queen Cortex',
               'B.Diablos Cortex': 'Diablos Cortex', 'Brutal Biter': 'Tigrex Hardfang', 'S.Zinogre Cortex': 'Zinogre Cortex',
               'S.Zinogre Lash': 'Zinogre Lash', 'Meaty Piel': 'Meaty Hide+', 'B.Tetsucabra Gnawrl': 'Tetsucabra Gnawrl',
               'Earth Dragonsphire': 'Lrg Wyvern Gem', 'Lagombi Auricle': 'Lagombi Ear+',
               'Twisted Stouthorn': 'Diablos Hardhorn'}  # Monoblos' G horn: his appended item needs his package (Tigerstripe's rule)
# GU NN, GU stand-in ID, 4U IDs (first weapon from its create recipe, then each upgrade of the previous one)
LINES = [(1, 44, (157, 158)),                  # Lepis Prism .. Grootslang
         (3, 52, (147, 148, 149)),             # Jingana .. Caduceus
         (4, 97, (113, 114)),                  # Azure Blast .. Azure Buster
         (7, 81, (156, 157, 158)),             # Hyddra .. Alphard
         (8, 14, (151, 152)),                  # Cryoseism .. Illuyanka
         (12, 43, (132, 133)),                 # the Hunting Horn line
         (13, 23, (65, 66, 67))]               # Medusa .. Medusa Mirror
IG_INSECT, IG_INSECT_4U = 12, 1          # Mauldrone (impact; 4U extra 1 = Impact): the docstring's "Kinsect"
# Sharpness: mKireType is a byte and GU's 164 rows + the 88 of the ports before her leave 4 rows (C). 4 of her 9 4U entries get them
# (the ones no GU row comes close to: 91 89 92 86); the table is full now. The other 5 keep their 4U row in KIRX (weapons4u exact,
# module/gear.c answers GU's sharpness getter with it); mKireType holds the nearest GU row as the fallback (sum of the differences
# 10..40 of 450, weapons4u logs them), a DEVIATION at the bars' end only with a core that lacks that hook
KIRE_NEAR = {73: 25, 56: 8, 57: 9, 70: 22, 88: 18}
OTHER_CHILDREN = {}                      # 4U children of her weapons that are not hers (checked in spec())
# the sound set each 4U arc holds (C, checked by sound_set_4u): its line's parent set, and GU ships them all, so no sound arc is
# converted (as Tigerstripe's: mSrqrNo = that set)
SRQR_MODEL = {(1, 102): 58, (3, 88): 39, (4, 45): 23, (7, 85): 44, (8, 81): 40, (12, 76): 40, (13, 34): 20}
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
    exists at our numbers"""
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    ours = {(nn, weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'])
            for nn, sid, ids4u in LINES for i in ids4u}
    for nn, m in sorted(ours):
        pwl = res['weapon\\w%02d\\pwl\\pl_w%02d' % (nn, nn)]
        assert m < struct.unpack_from('<I', pwl, 4)[0], (nn, m)
        g = struct.unpack_from('<I', pwl, 8 + 16 * m)[0]
        assert '/nativeNX/arc/weapon/w%02d/g%02d.arc' % (nn, g) in R.files, (nn, m, g)
        assert '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, m) not in R.files, (nn, m)
    for (nn, m), s in SRQR_MODEL.items():
        assert '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, s) in R.files, (nn, s)


def spec(R):
    exe = open(EXE, 'rb').read()
    classes, kire = [], []
    for nn, sid, ids4u in LINES:
        ptab = weapons4u.CLASS_INFO[nn][2]
        if nn == 13:                                     # 12-B IG upgrade rows: {ID, kinsect level, 2 x {item, count}}, no child IDs
            ig = [struct.unpack_from('<2H', exe, weapons4u.IG_UPGRADE_4U + 12 * i - EXE_BASE) for i in ids4u]
            assert ig[0] == (0, 0) and all(r[0] == i and r[1] for r, i in zip(ig[1:], ids4u[1:])), (nn, ig)
        else:
            for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; the rest is not hers
                want = ([b] if b else []) + ([OTHER_CHILDREN[nn, a]] if (nn, a) in OTHER_CHILDREN else [])
                assert sorted(children_4u(exe, nn, a)) == sorted(want), (nn, a, children_4u(exe, nn, a), want)
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        for w in ws:                                     # each 4U arc's sound set: its own model's
            assert sound_set_4u(nn, w['model']) == SRQR_MODEL.get((nn, w['model']), w['model']), (nn, w['model'])
        classes.append(dict(nn=nn, standin=sid, ids4u=ids4u, srqr=SRQR_MODEL[nn, ws[0]['model']],
                            **({'insect': IG_INSECT, 'insect_4u': IG_INSECT_4U} if nn == 13 else {})))
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em068_01.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
                kire_reuse=True, kire_near=KIRE_NEAR, pwl_fix=PWL_FIX, substitutes=SUBSTITUTES)


def main():
    R = RomFS(gear4u.GU_ROMFS)
    check_pwl(R, open(EXE, 'rb').read())
    s = spec(R)
    exact = []                                           # her KIRE_NEAR weapons' own 4U rows (KIRX)
    tables, texts, hooks, summary, log, kire = weapons4u.build(s, exact)
    secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'], exact)
    have = set(open(weapons4u.OUT_HOOKS).read().split())
    missing = [l for l in hk.splitlines() if not set(l.split()) <= have]
    weapons4u.show(summary, log, kire, tables, hooks, s['status'])
    for nn, wid, level, row, slash in exact:
        print('own sharpness w%02d %3d Lv%d: 4U %s, GU row %d the fallback' % (nn, wid, level, slash, row))
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
