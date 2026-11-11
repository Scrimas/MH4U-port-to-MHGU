"""gear_weapons_em070_01.py : the Shrouded Nerscylla weapons (4U's 9 lines of her materials) as records appended to GU's loaded weapon tables
-> data file sections TBLA / TXTA / KIRX of the shrouded_nerscylla entry (gen/*-weapons.sec, tools/portdata.py; read by module/gear.c). Tables, 4U
records and the rules every monster shares: tools/weapons4u.py; this file: her inputs (as Tidal Najarala's gear_weapons_em068_01.py). Facts: C =
read in code / data, S = strong, G = guess.

  gear_weapons_em070_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em070_01.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe, 2026-11-06): every 4U weapon whose upgrade recipe is mainly her materials, along the upgrade table's child IDs (record
+16, weapons4u.UPGRADE_4U). In 4U each line starts as an upgrade of a Nerscylla weapon; here the first one is forged from its own 4U upgrade
recipe's materials, the parent left out (weapons4u first_upgrade, as Stygian's and Black Gravios': no GU record touched, the user's rule for Stygian):
  GS     Ebonscylla -> Webbonscylla                     (186 187, parent Scylla Shear)
  SnS    Cold Blood -> Mortal Heart                     (195 196, parent Bloodslaughter)
  Hammer Scylla Maelstrom -> Scylla Maeltasrophe        (155 156, parent Master Musterer+)
  HBG    Nightfall Blaster -> Vampyr Blaster            (92 93, parent Buster Blaster+)
  LS     Gloom -> Dark Matter                           (167 168, parent Bioptimus+)
  GL     Nightfall Cannon -> Nux Cannon                 (172 173, parent Royal Gunbird+)
  Bow    Weblivion -> Wide Weblivion                    (143 144, parent Scylla Webdart)
  IG     Silent Eye -> Silent Eye+ -> Nightmare         (58 59 60; the IG upgrade table has no child IDs: same model 42, the rows follow each other)
  CB     Schwarzschlum -> Schwarzschlum+ -> Chernobog's Scythe (45 46 47, parent Arachnoscale+)
Left out as not hers (one of her parts in another line's upgrade): Dark Din, Plesioth Drencher, Paradise Green, Rinforzato, Klick-Klack,
Schwarzschild and others; IG Spirit Eater -> Reaper's Stroke (56 57, poison: one line per class and monster, weapons4u; listed for review).
Data: affinity, defense, slots, rarity, price, bowgun ammo = the 4U records'. Status 3 = Sleep (GU mElement 8, Gogmazios' spec). Raw and element = the 4U records' on GU's balance (the user: "Skaliere ... Waffen ... wenn nötig auf MHGU Niveau"): GU's G weapons level
on past 4U's values (her 4U 180..260 against GU's rarity-9 final levels of about 310), so each class's median of GU's final level / 4U over the weapons both games have by name at 4U G rarity (weapons4u.gu_scale); raw to tens. A DEVIATION from 4U, wanted, her weapons only (the earlier ports keep 4U's).
Sharpness: mKireType is a byte and the table is full since Tidal Najarala (C): entries GU holds take its row. The others keep their 4U row
in KIRX (weapons4u exact; module/gear.c answers GU's sharpness getter 0xf4724 with it), and mKireType holds the nearest GU row (KIRE_NEAR) as
the fallback, a DEVIATION at the bars' end only with a core that lacks that hook.
Stand-ins (records copied, then every 4U field set): GU's own parent weapon where GU has its name, else the earlier ports' per class.
Kinsect (C): 4U extra of the three IGs -> GU mInsectType as Tidal's (12 Mauldrone for Impact, 1 Culldrone for Cutting).
Recipe items GU lacks (SUBSTITUTES, G, listed for review): Tidal's and Monoblos' rules.
Models (C): 4U's numbers (allocations.toml weapon_models, free in GU), arcs tools/weapon4u2gu.py (build.py weapons).
Sounds (C): each 4U arc's own set (sound_set_4u, checked): GU's arc of that number when GU ships it (SRQR_MODEL), else the 4U arc's converted.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/shrouded_nerscylla
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em070_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'shrouded_nerscylla'
STATUS = {3: 8}                          # 4U Sleep -> GU mElement 8 (Gogmazios' spec, C)
SUBSTITUTES = {'D.S.Queen Moonlash': 'S.Queen Moonlash', 'B.Diablos Chine': 'Diablos Chine', 'B.Gravios Pallium': 'Gravios Pallium',
               'B.Gravios Cortex': 'Gravios Cortex', 'B.Gravios Crown': 'Gravios Crown', 'B.Tigrex Hardclaw': 'Tigrex Hardclaw',
               'R.Basarios Fellwing': 'Basarios Fellwing', 'Cephalos Purpscale': 'Cephalos Shard'}
# GU NN, GU stand-in ID, 4U parent, 4U IDs (first weapon from its 4U upgrade recipe, then each upgrade of the previous one)
LINES = [(0, 9, 185, (186, 187)),              # Ebonscylla .. Webbonscylla
         (1, 44, 194, (195, 196)),             # Cold Blood .. Mortal Heart
         (2, 40, 154, (155, 156)),             # Scylla Maelstrom .. Scylla Maeltasrophe
         (4, 97, 91, (92, 93)),                # Nightfall Blaster .. Vampyr Blaster
         (7, 81, 166, (167, 168)),             # Gloom .. Dark Matter
         (9, 15, 171, (172, 173)),             # Nightfall Cannon .. Nux Cannon
         (10, 27, 142, (143, 144)),            # Weblivion .. Wide Weblivion
         (13, 23, None, (58, 59, 60)),         # Silent Eye .. Nightmare
         (14, 41, 42, (45, 46, 47))]           # Schwarzschlum .. Chernobog's Scythe
PARENT_NAMES = {0: 'Scylla Shear', 1: 'Bloodslaughter', 2: 'Master Musterer+', 4: 'Buster Blaster+', 7: 'Bioptimus+', 9: 'Royal Gunbird+', 10: 'Scylla Webdart', 14: 'Arachnoscale+'}
IG_INSECT = {0: 1, 1: 12}                # 4U extra 0 Cutting -> GU Culldrone, 1 Impact -> Mauldrone (insectData_eng; Tigerstripe's, Tidal's)
# GU rows nearest her 4U entries (tools: sum of absolute differences, GU rows only: a port's rows exist only with its package): mKireType,
# the fallback; her bars are the 4U rows (KIRX)
KIRE_NEAR = {38: 38, 68: 20, 81: 138, 82: 86, 90: 23, 92: 85, 94: 44}
OTHER_CHILDREN = {}                      # 4U children of her weapons that are not hers (checked in spec())
BOW = dict(kyoku=None)                   # arc shot: the stand-in's; tame, charges, coatings: the 4U record's
SRQR_MODEL = {}                          # filled in spec(): the sound set each 4U arc holds where GU ships it
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
    """every model's GU motion set (pl_wNN record at the model number) has its gNN arc, and no GU model arc exists at our numbers"""
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    ours = {(nn, weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'])
            for nn, sid, parent, ids4u in LINES for i in ids4u}
    for nn, m in sorted(ours):
        pwl = res['weapon\\w%02d\\pwl\\pl_w%02d' % (nn, nn)]
        assert m < struct.unpack_from('<I', pwl, 4)[0], (nn, m)
        g = struct.unpack_from('<I', pwl, 8 + 16 * m)[0]
        assert '/nativeNX/arc/weapon/w%02d/g%02d.arc' % (nn, g) in R.files, (nn, m, g)
        assert '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, m) not in R.files, (nn, m)


def sound_arcs(R):
    """[(class, model)] whose 4U sound set GU does not ship: build.py step weapons converts them (tools/wsnd4u2gu.py)"""
    exe = open(EXE, 'rb').read()
    out = []
    for nn, sid, parent, ids4u in LINES:
        for m in sorted({weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'] for i in ids4u}):
            s = sound_set_4u(nn, m)
            if '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, s) not in R.files:
                assert s == m, (nn, m, s)
                out.append((nn, m))
    return out


def spec(R):
    exe = open(EXE, 'rb').read()
    t4 = gear4u.text4u('eng')
    classes, kire = [], []
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    lres = gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))
    for nn, sid, parent, ids4u in LINES:
        short, txt, ptab, _ = weapons4u.CLASS_INFO[nn]
        if nn == 13:                                     # 12-B IG upgrade rows: {ID, kinsect level, 2 x {item, count}}, no child IDs
            ig = [struct.unpack_from('<2H', exe, weapons4u.IG_UPGRADE_4U + 12 * i - EXE_BASE) for i in ids4u]
            assert ig[0] == (0, 0) and all(r[0] == i and r[1] for r, i in zip(ig[1:], ids4u[1:])), (nn, ig)
        else:
            assert t4[txt + 'Name'][parent] == PARENT_NAMES[nn] and ids4u[0] in children_4u(exe, nn, parent), (nn, parent)
            for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; the rest is not hers
                want = ([b] if b else []) + ([OTHER_CHILDREN[nn, a]] if (nn, a) in OTHER_CHILDREN else [])
                assert sorted(children_4u(exe, nn, a)) == sorted(want), (nn, a, children_4u(exe, nn, a), want)
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        c = dict(nn=nn, standin=sid, ids4u=ids4u, first_upgrade=True)
        c['raw_scale'], c['elem_scale'] = weapons4u.gu_scale(nn, res, lres, t4, exe)
        print('scale %-6s raw x %.3f, element x %.3f' % (weapons4u.CLASS_INFO[nn][0], c['raw_scale'], c['elem_scale']))
        m0 = ws[0]['model']
        assert all(w['model'] == m0 for w in ws), (nn, [w['model'] for w in ws])
        s = sound_set_4u(nn, m0)
        if s != m0: c['srqr'] = s                        # 4U's arc holds another weapon's set: GU's arc of that number
        if nn == 10: c['bow'] = BOW
        if nn == 13:
            assert len({w['extra'] for w in ws}) == 1, ws
            c.update(insect=IG_INSECT[ws[0]['extra']], insect_4u=ws[0]['extra'])
        classes.append(c)
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em070_01.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
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
    print('sound arcs to convert:', sound_arcs(R))
    print('hooks missing from module/gear_hooks.txt:', missing or 'none')
    if sys.argv[1:] == ['show']:
        return
    assert not missing, 'module/gear_hooks.txt lacks %s: run tools/weapons4u.write_hooks' % missing
    for sec in secs: print('wrote', portdata.write_section(NAME, sec, 'weapons'))


if __name__ == '__main__':
    main()
