"""gear_weapons_em007_01.py : the 14 Monoblos weapons (4U's 5 lines of his materials) as records appended to GU's
loaded weapon tables -> data file sections TBLA / TXTA of the monoblos entry (gen/*-weapons.sec, tools/portdata.py;
read by module/gear.c). Tables, 4U records and the rules every monster shares: tools/weapons4u.py; this file:
Monoblos' inputs (as Black Gravios' gear_weapons_em005_01.py). Facts: C = read in code / data, S = strong, G = guess.

  gear_weapons_em007_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em007_01.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe, 2026-11-05): the 4U weapons whose recipes are Monoblos materials, along the upgrade table's
child IDs (record +16, weapons4u.UPGRADE_4U). Each first weapon has a 4U create recipe and is forged from it (no GU
record touched, the user's rule for Stygian). A line ends where 4U goes on with a weapon that is not his (OTHER_CHILDREN,
checked: its recipe holds White Monoblos or Diablos materials, or another monster's), and branches into others' lines
are left out the same way:
  GS     Executioner -> Executioner+                (164 165; 4U goes on to 166 Enforcer's Axe: White Monoblos)
  SnS    Crimson Club -> Crimson Club+ -> Monoblos Club     (179 180 181; then 182 Studded Club = GU 115, Diablos')
  Lance  Crimson Lance -> .. -> Crimson Monoblos   (130..133)
  HBG    Monodevilcaster -> Monodevilcaster+         (117 118; then 119 Monodevilblaster: White Monoblos)
  LS     Crimson Scythe -> Crimson Scythe+ -> Monoblos Scythe (127 128 129)
Left out as not his (one Monoblos part in another line): Daimyo's Warbow II, Great Purple Emperor II, Shell Intoner+,
Enduring Surrender, Chum Scarecrows; White Monoblos' (Bamboo Dragonsbane, Ceramic Blos Lance, White Mantis, ...).
GU has its own GS named "Executioner" (41, the bone line, model 159): his GS line carries the label " (4U)" after its
4U names in every language (LABEL_4U; the maintainer's choice, PR #17), so the smithy lists no two entries of one name.
Data: raw, element, affinity, defense, slots, rarity, price, sharpness, bowgun ammo = the 4U records'.
Stand-ins (records copied, then every 4U field set): GU Diablos' weapon of each class where GU has one (C: their recipes
are Diablos materials): GS 124 Quarrel Hornsword, SnS 115 Studded Club, Lance 115 Diablos Lance, HBG 97 Dual Threat
(recoil / reload / deviation / rapid fire / special ammo kept from it, logged by weapons4u); LS: GU has no Diablos LS,
81 Centenarian Dagger (fire, rarity 6, as Black Gravios' DB stand-in rule).
Recipe items GU lacks (SUBSTITUTES, G, listed for review): B.Tigrex Hardclaw -> Tigrex Hardclaw (GU has no Brute
Tigrex: the Tigerstripe / Black Gravios rule), Brutal Horn+ (4U: Rajang's carves / breaks) -> Rajang Horn+ (GU's
Rajang horn of the same rank).
Models (C): 4U's numbers (allocations.toml weapon_models, free in GU), arcs tools/weapon4u2gu.py (build.py weapons).
Sounds (C): each 4U arc's own set (sound_set_4u, checked).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em007_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'monoblos'
STATUS = {}                              # no status weapon in his lines (fire or raw)
SUBSTITUTES = {'B.Tigrex Hardclaw': 'Tigrex Hardclaw', 'Brutal Horn+': 'Rajang Horn+'}
# GU NN, GU stand-in ID, 4U IDs (first weapon from its create recipe, then each upgrade of the previous one)
LINES = [(0, 124, (164, 165)),                 # Executioner .. Executioner+
         (1, 115, (179, 180, 181)),            # Crimson Club .. Monoblos Club
         (3, 115, (130, 131, 132, 133)),       # Crimson Lance .. Crimson Monoblos
         (4, 97, (117, 118)),                  # Monodevilcaster .. Monodevilcaster+
         (7, 81, (127, 128, 129))]             # Crimson Scythe .. Monoblos Scythe
# 4U children of his weapons that are not his (checked in spec(): every other child is the line's next weapon)
OTHER_CHILDREN = {(0, 164): 167,    # Cera Cigil (Diablos / Black Diablos materials)
                  (0, 165): 166,    # Enforcer's Axe (White Monoblos materials)
                  (1, 179): 185,    # Rajang Club
                  (1, 181): 182,    # Studded Club (Diablos materials; GU's own SnS 115)
                  (3, 131): 134,    # Ceramic Blos Lance (White Monoblos materials)
                  (4, 118): 119,    # Monodevilblaster (White Monoblos materials)
                  (7, 127): 130}    # White Mantis (White Monoblos materials)
LABEL_4U = {0: ' (4U)'}                  # GU class -> label after the line's names (GU GS 41 is "Executioner" too)
SRQR_MODEL = {}                          # every 4U arc holds its own model's sound set (checked)
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
        assert '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, m) not in R.files, (nn, m)
    for (nn, m), s in SRQR_MODEL.items():
        assert (nn, s) in ours or '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, s) in R.files, (nn, s)


def spec(R):
    exe = open(EXE, 'rb').read()
    classes, kire = [], []
    for nn, sid, ids4u in LINES:
        ptab = weapons4u.CLASS_INFO[nn][2]
        for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; the rest is not his
            want = ([b] if b else []) + ([OTHER_CHILDREN[nn, a]] if (nn, a) in OTHER_CHILDREN else [])
            assert sorted(children_4u(exe, nn, a)) == sorted(want), (nn, a, children_4u(exe, nn, a), want)
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        for w in ws:                                     # each 4U arc's sound set: its own model's
            assert sound_set_4u(nn, w['model']) == SRQR_MODEL.get((nn, w['model']), w['model']), (nn, w['model'])
        classes.append(dict(nn=nn, standin=sid, ids4u=ids4u))
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em007_01.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
                pwl_fix=PWL_FIX, substitutes=SUBSTITUTES)


def label_4u(text):
    """weapons4u's MsgData strings of a class (per language: name, description, three times per weapon) with LABEL_4U
    after every name of that class"""
    table, entry, strs = text
    m = re.fullmatch(r'weapon(\d\d)MsgData', table)
    lab = LABEL_4U.get(int(m.group(1))) if m else None
    if not lab: return text
    n = len(next(ids for nn, sid, ids in LINES if nn == int(m.group(1))))
    assert all(len(ss) == 6 * n for ss in strs), (table, [len(ss) for ss in strs])
    return table, entry, [[s + lab if i % 2 == 0 else s for i, s in enumerate(ss)] for ss in strs]


def main():
    R = RomFS(gear4u.GU_ROMFS)
    check_pwl(R, open(EXE, 'rb').read())
    s = spec(R)
    tables, texts, hooks, summary, log, kire = weapons4u.build(s)
    texts = [label_4u(t) for t in texts]
    secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'])
    have = set(open(weapons4u.OUT_HOOKS, encoding='utf-8').read().split())
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
