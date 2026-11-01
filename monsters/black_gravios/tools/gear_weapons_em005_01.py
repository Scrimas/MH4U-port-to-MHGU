"""gear_weapons_em005_01.py : the 18 Black Gravios weapons (4U's 6 lines named for him) as records appended to GU's
loaded weapon tables -> data file sections TBLA / TXTA of the black_gravios entry (gen/*-weapons.sec,
tools/portdata.py; read by module/gear.c). Tables, 4U records and the rules every monster shares: tools/weapons4u.py;
this file: Black Gravios' inputs (as Stygian's gear_weapons_em057_01.py). Facts: C = read in code / data, S = strong,
G = guess.

  gear_weapons_em005_01.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em005_01.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe, 2026-11-01): the 4U lines whose recipes are Black Gravios materials, followed along the
upgrade table's child IDs (record +16, weapons4u.UPGRADE_4U): each link single, the last without a child (checked).
4U weapons of other monsters' lines that only add one Black Gravios part are not his (left out). Each line branches
off a GU-shared Gravios weapon in 4U (the parent below, except the DBs: Melting Wail is forged); the user's rule for
Stygian (2026-10-28): standalone lines, no GU weapon record touched. The SnS line starts at Red Demonic Flame: 4U's
Black Doom Flame and Red Divine Flame before it are GU weapon 114's levels (additions only). The first weapon is
forged from its 4U create recipe where 4U has one (DB 73 Melting Wail), else from the materials of its 4U upgrade
recipe (the parent left out). Every later weapon is an upgrade of the previous one, with its 4U upgrade recipe.
Data: raw, element, affinity, defense, slots, rarity, price, sharpness, GL shelling, bowgun ammo = the 4U records'.
Stand-ins (records copied, then every 4U field set): the GU weapon of each line's 4U parent (GU-folded), the DBs GU 23
Flamestorm (fire, rarity 6: no Gravios DB in GU); bowgun recoil / reload / deviation / rapid fire / special ammo from
the stand-in (logged by weapons4u).
Models (C): 4U's numbers (allocations.toml weapon_models, free in GU), arcs tools/weapon4u2gu.py (build.sh weapons).
Sounds (C): each 4U arc's own set (sound_set_4u) except SnS 103 (holds set 009, GU snd/009 = Flame Syphos') and DB
094 (holds 008 = Melting Wail's, converted from sou008).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/black_gravios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em005_01, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'black_gravios'
# 4U status -> GU mElement: Poison (S: GU's Gravios Venom Spear 114 / Graviton Hammer 120 carry 6, their 4U lines 1;
# Dalamadur's Para 2 -> 7, Blast 4 -> 9 follow the same + 5)
STATUS = {1: 6}
SUBSTITUTES = {}
# GU NN, GU stand-in ID, 4U parent (None: forged; checked: its children include the line's first weapon), 4U IDs
# (first weapon, then each upgrade of the previous one), first weapon forged from its 4U upgrade recipe
LINES = [(1, 114, 191, (192, 193), True),            # Red Divine Flame (GU 114 C) -> Red Demonic .. Red Efreet's Flame
         (2, 120, 49, (50, 173, 174), True),         # Graviton Hammer -> Venom Crater .. Glasya-Labolas
         (3, 114, 17, (18, 125, 126), True),         # Gravios Spear -> Black Gravios Spear .. Gravios Fire Lance
         (4, 96, 24, (25, 26, 94), True),            # Gravios Gigahowl -> Gravios Roar .. Gravios Gigacannon
         (9, 102, 28, (29, 140, 141), True),         # White Cannon -> Black Gunlance .. Black Gore Buster
         (11, 23, None, (73, 74, 174, 175), False)]  # (forged) Melting Wail .. Megiddo Breakers
# sound set per model where the 4U arc holds another model's set (C, sound_set_4u): SnS 103 holds 009 (GU's own
# snd/009, Flame Syphos'); DB 094 holds 008 (Melting Wail's, converted with model 8)
SRQR_MODEL = {(1, 103): 9, (11, 94): 8}
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
    exists at our numbers; a borrowed set (SRQR_MODEL) is GU's own or one of ours"""
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    ours = {(nn, weapons4u.weapon_4u(exe, nn, weapons4u.CLASS_INFO[nn][2], i)['model'])
            for nn, sid, parent, ids4u, _ in LINES for i in ids4u}
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
    for nn, sid, parent, ids4u, first_upgrade in LINES:
        ptab = weapons4u.CLASS_INFO[nn][2]
        assert parent is None or ids4u[0] in children_4u(exe, nn, parent), (nn, parent)
        for a, b in zip(ids4u, ids4u[1:] + (None,)):     # the line follows the upgrade table; it ends there
            assert children_4u(exe, nn, a) == ([b] if b else []), (nn, a, children_4u(exe, nn, a))
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        srqr = {SRQR_MODEL.get((nn, w['model']), w['model']) for w in ws}
        for w in ws:                                     # each 4U arc's sound set: its own model's, or SRQR_MODEL's
            assert sound_set_4u(nn, w['model']) == SRQR_MODEL.get((nn, w['model']), w['model']), (nn, w['model'])
        c = dict(nn=nn, standin=sid, ids4u=ids4u, first_upgrade=first_upgrade)
        if len(srqr) == 1 and srqr != {ws[0]['model']}: c['srqr'] = srqr.pop()   # one set for the whole line
        classes.append(c)
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em005_01.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
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
