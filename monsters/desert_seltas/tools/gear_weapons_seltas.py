"""gear_weapons_seltas.py : the Desert Seltas / Desert Seltas Queen weapons (4U's lines of their materials) as records appended to GU's loaded
weapon tables -> data file sections TBLA / TXTA / KIRX of each entry (gen/[<entry>/]*-weapons.sec, tools/portdata.py; read by module/gear.c).
Tables, 4U records and the rules every monster shares: tools/weapons4u.py; this file: their inputs (as Shrouded Nerscylla's
gear_weapons_em070_01.py). Facts: C = read in code / data, S = strong, G = guess.

  gear_weapons_seltas.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_seltas.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe, 2026-11-09): the 4U weapons made of their materials, along the upgrade table's child IDs (record +16,
weapons4u.UPGRADE_4U): the lines on 4U models made for them (every weapon of the model is made of their materials, no GU arc has the
model), and the single weapons on other models whose upgrade recipe is more than half theirs (D.S.QueenConcentrate counted: a Queen
material GU has). In 4U each line starts as an upgrade of another weapon; here the first one is forged from its own 4U upgrade recipe's
materials, the parent left out (weapons4u first_upgrade, as Stygian's, Black Gravios' and Shrouded Nerscylla's: no GU record touched). One
line per class and entry (weapons4u), so each sits in the entry whose materials it holds most of:
  Desert Seltas
    SnS    Bright Night -> Sainted Dame -> Gartered Rood   (188 189 190, model 101, parent Dual Cross Brand)
    GL     Monsieur Gore+                                  (151, GU's model 80: its parent Monsieur Gore is GU's 47; its child Madame
                                                            Butcher is GU's 48, the Queen's own line goes on from there)
    DB     Crossdrills -> Crossveldts -> Crossenders       (162 163 164, model 93, parent Gyro Wedges)
  Desert Seltas Queen
    Hammer Boulverizer                                     (164, model 105, parent Logicbreaker)
    LBG    Battalion Strafer (4U)                          (111, GU's model 50: its parent Machine Strafer is GU's 34)
    GL     Seltas Fortitude (4U)                           (153, GU's model 84: its parent Madame Butcher is GU's 48)
    Bow    Gold Popillia -> Golden Ray                     (140 141, model 82, parent Absolute Deviance)
GU has its own weapons of those two names (C, 2026-11-11: weapon06MsgData 206 "Battalion Strafer", Machine Strafer's final
form, and weapon09MsgData 290 "Seltas Fortitude", in all five languages GU's names = 4U's): the two lines carry Monoblos'
label " (4U)" after their names in every language (LABEL_4U; the maintainer's choice, PR #17), so the smithy lists no two
entries of one name. The 2026-11-09 name check had missed them.
Left out (listed for review): IG Cannibal Happa (78: half theirs, D.S.Queen Moonlash x2 + Brutal Biter x2; its parent Trim Happa is GU's)
and CB Maximinsect (52: half, 4 of 8 items), and the lines of other monsters with one of their parts (Grand Pincer, Plesioth Pelagis,
Zamtrista Akzar, White Catastrophe, Dragonwood Godblade, Webbonscylla and others).
Data: affinity, defense, slots, rarity, price, bowgun ammo, GL shelling, DB second element = the 4U records'. Raw and element = the 4U
records' on GU's balance (each class's median of GU's final level / 4U over the weapons both games have by name at 4U G rarity,
weapons4u.gu_scale; raw to tens), as Shrouded Nerscylla's (the user: "Skaliere ... Waffen ... wenn nötig auf MHGU Niveau"), a DEVIATION
from 4U, wanted. No status weapon in their lines (water, C).
Sharpness: mKireType is a byte and the table is full (C): entries GU holds take its row. The others keep their 4U row in KIRX (weapons4u
exact; module/gear.c answers GU's sharpness getter 0xf4724 with it), and mKireType holds the GU row nearest the 4U entry (kire_near: the
least sum of absolute differences over GU's own rows), the fallback, a DEVIATION at the bars' end only with a core that lacks that hook.
Stand-ins (records copied, then every 4U field set): GU's own parent weapon where GU has its name (34, 47, 48), else the earlier ports'
per class (SnS 44, Hammer 40, Bow 27: Shrouded Nerscylla's; DB 23: Black Gravios').
Recipe items GU lacks (SUBSTITUTES, G, listed for review): S.Queen Concentrate -> D.S.QueenConcentrate (items_seltas.SUBSTITUTES);
T.Najarala Splasher (Tidal Najarala's, her package) -> Najarala Ampsounder (Tidal's armor swaps the two); D.Mohran Allbrace (GU has no
Dah'ren Mohran) -> Lrg ElderDragon Bone.
Models (C): 4U's numbers. The own models (allocations.toml weapon_models, free in GU) get arcs from tools/weapon4u2gu.py (build.py
weapons); the GU models (50, 80, 84) are GU's own arcs of the same 4U model (GU kept 4U's numbers, C: GU's weapons of that model).
Sounds (C): each 4U arc's own set (sound_set_4u, checked): GU's arc of that number when GU ships it, else the 4U arc's converted.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_seltas, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc, gmd   # noqa: E402

STATUS = {}                              # no status weapon in their lines (C)
SUBSTITUTES = {'S.Queen Concentrate': 'D.S.QueenConcentrate',
               'T.Najarala Splasher': 'Najarala Ampsounder',   # Tidal Najarala's appended item needs her package (Tigerstripe's rule):
                                                               # the GU Najarala part her armor's level rows swap it for (C)
               'D.Mohran Allbrace': 'Lrg ElderDragon Bone'}    # GU has no Dah'ren Mohran: an elder dragon's G part (G)
# per entry: GU NN, GU stand-in ID, 4U parent, 4U IDs (first weapon from its 4U upgrade recipe, then each upgrade of the previous one),
# GU model (True: GU ships the model's arc)
LINES = {
    'desert_seltas': [(1, 44, 67, (188, 189, 190), False),      # Bright Night .. Gartered Rood
                      (9, 47, 150, (151,), True),               # Monsieur Gore+
                      (11, 23, 56, (162, 163, 164), False)],    # Crossdrills .. Crossenders
    'desert_seltas_queen': [(2, 40, 163, (164,), False),        # Boulverizer
                            (6, 34, 110, (111,), True),         # Battalion Strafer
                            (9, 48, 152, (153,), True),         # Seltas Fortitude
                            (10, 27, 51, (140, 141), False)],   # Gold Popillia .. Golden Ray
}
PARENT_NAMES = {(1, 67): 'Dual Cross Brand', (9, 150): 'Monsieur Gore', (11, 56): 'Gyro Wedges', (2, 163): 'Logicbreaker',
                (6, 110): 'Machine Strafer', (9, 152): 'Madame Butcher', (10, 51): 'Absolute Deviance'}
GU_STANDIN_NAMES = {(6, 34): 'Machine Strafer', (9, 47): 'Monsieur Gore', (9, 48): 'Madame Butcher'}   # GU's own parents (C)
OTHER_CHILDREN = {(9, 151): 152}         # 4U children of their weapons that are not in the line: Madame Butcher (GU's 48)
LABEL_4U = {'desert_seltas_queen': {6: ' (4U)', 9: ' (4U)'}}   # entry -> GU class -> label after the line's names (docstring)
BOW = dict(kyoku=None)                   # arc shot: the stand-in's; tame, charges, coatings: the 4U record's
PWL_FIX = []                             # every model's GU motion set has its gNN arc (check_pwl)
GEAR_SRC = os.path.join(ROOT, 'dump/gear_src/weapons/4u/data')
PFX = {0: 'two', 1: 'one', 2: 'ham', 3: 'lan', 4: 'hbg', 6: 'lbg', 7: 'swo', 8: 'axe', 9: 'gun', 10: 'bow',
       11: 'sou', 12: 'hue', 13: 'rod', 14: 'gaxe'}


def arc_4u(nn, model):
    """the 4U weapon arc of a model (the converted dump; LBG arcs are named hue, as the 4U RomFS: C)"""
    for pfx in (PFX[nn],) + (('hue',) if nn == 6 else ()):
        p = os.path.join(GEAR_SRC, 'pl_%s%03d.arc' % (pfx, model))
        if os.path.exists(p): return p
    raise FileNotFoundError((nn, model))


def sound_set_4u(nn, model):
    """the wave set number of the 4U weapon arc of a model (its waves are named <pfx>NNN_k)"""
    ents = arcpack.read(open(arc_4u(nn, model), 'rb').read())[1]
    sets = {re.match(r'[a-z]+(\d+)_', p.split('\\')[-1]).group(1) for p, t, d in ents if '\\wave\\' in p}
    assert len(sets) == 1, (nn, model, sets)
    return int(sets.pop())


def children_4u(exe, nn, i):
    """child weapon IDs of a 4U weapon (upgrade table record +16, 4 x u16)"""
    ctype = weapons4u.CLASS_INFO[nn][3]
    a = weapons4u.u32(exe, weapons4u.UPGRADE_4U + 4 * (ctype - 7)) + 24 * i - EXE_BASE
    return [c for c in struct.unpack_from('<4H', exe, a + 16) if c]


def check_models(R, exe, res):
    """own models: GU's motion set (pl_wNN record at the model number) has its gNN arc and no GU model arc exists at the number; GU models:
    GU's stand-in (the 4U parent's GU record) has that model and GU ships its arc"""
    lres = gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))
    for name, lines in LINES.items():
        for nn, sid, parent, ids4u, gu_model in lines:
            ms = {weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'] for i in ids4u}
            assert len(ms) == 1, (nn, ms)
            m = ms.pop()
            arc = '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, m)
            if gu_model:
                n, base = weapons4u.table(res['table\\weapon%02dBaseData' % nn], weapons4u.base_layout(nn))
                g = gmd(lres['eng\\table\\weapon%02dMsgData_eng' % nn])
                assert g[6 * sid] == GU_STANDIN_NAMES[nn, sid] and base[sid]['mModelID'] == m and arc in R.files, (nn, sid, m)
                continue
            pwl = res['weapon\\w%02d\\pwl\\pl_w%02d' % (nn, nn)]
            assert m < struct.unpack_from('<I', pwl, 4)[0], (nn, m)
            gg = struct.unpack_from('<I', pwl, 8 + 16 * m)[0]
            assert '/nativeNX/arc/weapon/w%02d/g%02d.arc' % (nn, gg) in R.files, (nn, m, gg)
            assert arc not in R.files, (nn, m, 'a GU model arc at our number')


def sound_arcs(R, exe):
    """[(class, model)] whose 4U sound set GU does not ship: build.py step weapons converts them (tools/wsnd4u2gu.py)"""
    out = []
    for name, lines in LINES.items():
        for nn, sid, parent, ids4u, gu_model in lines:
            for m in sorted({weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'] for i in ids4u}):
                s = sound_set_4u(nn, m)
                if '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, s) not in R.files:
                    assert s == m and not gu_model, (nn, m, s)
                    out.append((nn, m))
    return out


def kire_near(exe, res, kire4):
    """{4U sharpness entry: GU row} for the entries GU has no equal row of: the least sum of absolute differences over GU's own rows
    (a port's rows exist only with its package), the lower row on a tie"""
    kn, rows = weapons4u.table(res['table\\kireajiData'], weapons4u.KIRE)
    out = {}
    for i in kire4:
        v = weapons4u.KIRE.dec(exe[weapons4u.KIRE_4U + 14 * i - EXE_BASE:][:14])
        if v in rows: continue                          # kire_reuse: GU's equal row
        out[i] = min(range(kn), key=lambda r: (sum(abs(rows[r][k] - v[k]) for k in v), r))
    return out


def spec(R, name):
    exe = open(EXE, 'rb').read()
    t4 = gear4u.text4u('eng')
    classes, kire = [], []
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    lres = gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))
    for nn, sid, parent, ids4u, gu_model in LINES[name]:
        short, txt, ptab, _ = weapons4u.CLASS_INFO[nn]
        assert t4[txt + 'Name'][parent] == PARENT_NAMES[nn, parent] and ids4u[0] in children_4u(exe, nn, parent), (nn, parent)
        for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; the rest is not theirs
            want = ([b] if b else []) + ([OTHER_CHILDREN[nn, a]] if (nn, a) in OTHER_CHILDREN else [])
            assert sorted(children_4u(exe, nn, a)) == sorted(want), (nn, a, children_4u(exe, nn, a), want)
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        c = dict(nn=nn, standin=sid, ids4u=ids4u, first_upgrade=True)
        c['raw_scale'], c['elem_scale'] = weapons4u.gu_scale(nn, res, lres, t4, exe)
        print('%s: scale %-6s raw x %.3f, element x %.3f' % (name, short, c['raw_scale'], c['elem_scale']))
        m0 = ws[0]['model']
        assert all(w['model'] == m0 for w in ws), (nn, [w['model'] for w in ws])
        s = sound_set_4u(nn, m0)
        if s != m0: c['srqr'] = s                        # 4U's arc holds another weapon's set: GU's arc of that number
        if nn == 10: c['bow'] = BOW
        classes.append(c)
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    mats = [items_seltas.materials(n, R, exe) for n in (name,) + tuple(o for o in LINES if o != name)]
    return dict(name=name, materials=mats, classes=classes, status=STATUS, kire_4u=kire, kire_reuse=True,
                kire_near=kire_near(exe, res, kire), pwl_fix=PWL_FIX, substitutes=SUBSTITUTES)


def label_4u(name, text):
    """weapons4u's MsgData strings of a class (per language: name, description, three times per weapon) with the
    entry's LABEL_4U after every name of that class (Monoblos' label_4u)"""
    table, entry, strs = text
    m = re.fullmatch(r'weapon(\d\d)MsgData', table)
    lab = LABEL_4U.get(name, {}).get(int(m.group(1))) if m else None
    if not lab: return text
    n = len(next(ids for nn, sid, parent, ids, gu in LINES[name] if nn == int(m.group(1))))
    assert all(len(ss) == 6 * n for ss in strs), (table, [len(ss) for ss in strs])
    return table, entry, [[s + lab if i % 2 == 0 else s for i, s in enumerate(ss)] for ss in strs]


def main():
    R = RomFS(gear4u.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    check_models(R, exe, gu_arc(R.read('/nativeNX/loc/arc/resident.arc')))
    show = sys.argv[1:] == ['show']
    have = set(open(weapons4u.OUT_HOOKS).read().split())
    for name in LINES:
        s = spec(R, name)
        exact = []                                       # their kire_near weapons' own 4U rows (KIRX)
        tables, texts, hooks, summary, log, kire = weapons4u.build(s, exact)
        texts = [label_4u(name, t) for t in texts]
        secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'], exact)
        missing = [l for l in hk.splitlines() if not set(l.split()) <= have]
        weapons4u.show(summary, log, kire, tables, hooks, s['status'])
        print('%s: sharpness rows nearest the 4U entries %s' % (name, s['kire_near']))
        for nn, wid, level, row, slash in exact:
            print('%s: own sharpness w%02d %3d Lv%d: 4U %s, GU row %d the fallback' % (name, nn, wid, level, slash, row))
        for short, i, nm, b, r, mats, k in summary:      # elements (weapons4u.show prints statuses only)
            if 'mElement1' in b:
                print('element %-6s %3d %-24s %d:%d + %d:%d' % (short, i, nm, b['mElement1'], r['mElementValue1'] * 10,
                                                               b['mElement2'], r['mElementValue2'] * 10))
            elif 'mElement' in b:
                print('element %-6s %3d %-24s %d:%d' % (short, i, nm, b['mElement'], r['mElementValue'] * 10))
        print('%s: hooks missing from module/gear_hooks.txt: %s' % (name, missing or 'none'))
        if show: continue
        assert not missing, 'module/gear_hooks.txt lacks %s: run tools/weapons4u.write_hooks' % missing
        for sec in secs: print('wrote', portdata.write_section(name, sec, 'weapons'))
    print('sound arcs to convert:', sound_arcs(R, exe))


if __name__ == '__main__':
    main()
