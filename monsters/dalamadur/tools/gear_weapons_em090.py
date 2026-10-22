"""gear_weapons_em090.py : the 71 Dalamadur / Shah Dalamadur weapons (one line in each of the 14 classes) as records
appended to GU's loaded weapon tables -> data file sections TBLA / TXTA / PWLF of the dalamadur entry
(gen/dalamadur/*-weapons.sec, tools/portdata.py; read by module/gear.c). Tables, 4U records and the rules every
monster shares: tools/weapons4u.py; this file: Dalamadur's inputs. Facts: C = read in code / data, S = strong, G = guess.

  gear_weapons_em090.py          write the sections (and check module/gear_hooks.txt holds the weapon class hooks)
  gear_weapons_em090.py show     print the per-weapon summary, the tables and the hooks; write nothing

Lines (C, 4U v1.1 exe): from each create weapon (notes/phase0.md "Content") along the upgrade table's child IDs
(record +16, weapons4u.UPGRADE_4U): create (HR) -> HR upgrade -> G "<Name> the <X>" -> Dalamadur X (Shah materials)
-> its upgrade (Dalamadur G materials + Skyblade Drgnsphire / Elder Dragon Gem); each link single, the last without a
child. The IG upgrade table has no child IDs: its line (S) = 32 -> 33 -> 34 -> 100 Self-possession (the only other
model-6 IG, rarity 9, Dalam Tail Shell recipe; its IG upgrade entry has ID / kinsect level 0 like Metalmangler+ 97, a
G weapon from an HR one) -> 101 -> 102 (Dalamadur-named). The two-model split (HR / G line one model, the Dalamadur X
pair another) is the 4U records' (C).
Choices (G unless noted; Tigerstripe / Gogmazios rules):
  - Statuses (C): Para (4U 2 -> GU 7) on GS / SnS / Lance / LS / DB / HH / CB, Blast (4U 4 -> GU 9) on Hammer / SA /
    GL / IG / Bow; no element anywhere. Hidden (Awaken) values made visible (all but SA and IG: GU has no Awaken).
  - Stand-ins: Gogmazios' (GU's Akantor / Demonlord weapons: only the recipe templates come from them on melee) except
    HBG Demonic Cannon 73 (4U deviation 0; Akantor Cannon has mBure 1), LBG Demonlord Blaster 58 (mBure 6 = 4U's).
    Kept from them (logged): bowgun recoil / reload / rapid or crouch fire / special ammo / slot 32, the bow arc shot
    (not in the 4U record; Akantor Bow's).
  - Class data from the 4U records (weapons4u.py notes): bowgun ammo and loadable flags, bow charges (Spread 2-3 /
    Spread 2-4 / Pierce 4-5 / Rapid 5), 4 charge levels, coatings Poison / Para / Sleep / C.Range / Paint / Exhaust
    (+ an unknown bit 10), defense; SA Element phial (4U 1), GL Wide shelling Lv3 / 4 / 4 / 5 / 5, HH note set 44 =
    GU fueMusicData 44 (colours 2 / 5 / 8), IG Cutting -> Culldrone (GU kinsect 1), CB Impact.
  - Models: 4U's (allocations.toml weapon_models, all free in GU); arcs tools/weapon4u2gu.py (build.sh weapons).
    Motion sets (GU pl_wNN at those numbers = 4U's; PWL_FIX): six classes point at gNN arcs GU lacks -> the set of the
    GU models with the same bone counts (S).
  - Sounds: each line's two 4U arcs hold the HR model's set (C), GU ships none of them -> mSrqrNo = the HR model,
    converted by tools/wsnd4u2gu.py (build.sh weapons), one snd arc per class. Hammer 059: 4U bank key 7 (wave _07)
    has no entry in GU's hammer class: dropped by the converter (its `check` reports that wave as missing).
  - Recipe items GU lacks -> SUBSTITUTES (for review).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, gear4u, items_em090, portdata, weapons4u   # noqa: E402
from gear4u import EXE, EXE_BASE, RomFS, gu_arc       # noqa: E402

NAME = 'dalamadur'
STATUS = {2: 7, 4: 9}                    # 4U status -> GU mElement: Para, Blast
# recipe items GU lacks (G, for review): Black Gravios -> Gravios (as Tigerstripe's B.Diablos / B.Tigrex), ores by tier
# and description (GU itemData +5: Meldspar 7 = G like 4U Cosmicite, Fucium 5 = HR like 4U Yoldspar), the 4U honour
# seal -> GU's (Hero's Seal: "a true symbol of the art of hunting")
SUBSTITUTES = {'B.Gravios Cortex': 'Gravios Cortex', 'B.Gravios Crown': 'Gravios Crown', 'Cosmicite Ore': 'Meldspar Ore',
               'Yoldspar Ore': 'Fucium Ore', "Conqueror's Seal G": "Hero's Seal"}
# GU NN, GU stand-in ID, 4U IDs (create weapon first, then each upgrade of the previous one)
LINES = [(0, 71, (104, 105, 212, 213, 214)),         # Swordscale Shard .. Dreaming Dalamadur
         (1, 63, (103, 104, 217, 218, 219)),         # Eviscerator & Scutum .. Bescaled Dalamadur
         (2, 18, (109, 110, 211, 212, 213)),         # Helixbone Slab .. Agonized Dalamadur
         (3, 48, (87, 88, 188, 189, 190)),           # Shellslab Prong .. Generous Dalamadur
         (4, 73, (54, 55, 130, 131, 132)),           # Caudalbone Crook .. Militant Dalamadur
         (6, 58, (153, 154, 155, 156, 157)),         # Penetrating Gaze .. Buoyant Dalamadur
         (7, 68, (80, 81, 186, 187, 188)),           # Tailblade Parallel .. Clouded Dalamadur
         (8, 56, (77, 78, 170, 171, 172)),           # Keenscale Phalanx .. Praying Dalamadur
         (9, 60, (93, 94, 191, 192, 193)),           # Illstarred Gunlance .. Unchained Dalamadur
         (10, 56, (80, 81, 173, 174, 175)),          # Cradlecrush Embrace .. Enraged Dalamadur
         (11, 63, (101, 102, 198, 199, 200)),        # Blackspine Bundles .. Amber Dalamadur
         (12, 60, (75, 76, 154, 155, 156)),          # Veilglare Hymn .. Bloodied Dalamadur
         (13, 43, (32, 33, 34, 100, 101, 102)),      # Direspike Display .. Bounding Dalamadur
         (14, 41, (86, 87, 88, 89, 90))]             # Bebladed Implement .. Patient Dalamadur
IG_INSECT = 1                            # Culldrone (cutting; 4U extra 0 = Cutting)
BOW = dict(kyoku=None)                   # arc shot: the stand-in's; tame, charges, coatings: the 4U record's
# motion sets (rPlayerWeaponList mGmkMotNo, weapons4u.sections PWLF): GU's record at the model number, whose gNN arc GU
# lacks -> the set of the GU models (with an arc) whose MOD parts have the same bone counts: SnS 1-bone sword + shield
# 10 / 10 at 0, Hammer 5 bones 25 / 31 at 0, LS 19 / 19 at 0, GL 3 + 1 bones 61 / 81 at 0, Bow 76 / 78 at 20, HH 18 / 18
# at 0 (4U's gimmick animation of those sets is lost: no GU arc). (path suffix, model, GU value, ours)
PWL_FIX = [('pl_w01', 55, 3, 0), ('pl_w01', 105, 3, 0), ('pl_w02', 59, 9, 0), ('pl_w02', 107, 9, 0),
           ('pl_w07', 42, 3, 0), ('pl_w07', 87, 3, 0), ('pl_w09', 49, 13, 0), ('pl_w09', 90, 13, 0),
           ('pl_w10', 25, 3, 20), ('pl_w10', 84, 3, 20), ('pl_w12', 35, 6, 0), ('pl_w12', 78, 6, 0)]
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
    """child weapon IDs of a 4U weapon (upgrade table record +16, 4 x u16; none for the IG)"""
    ctype = weapons4u.CLASS_INFO[nn][3]
    a = weapons4u.u32(exe, weapons4u.UPGRADE_4U + 4 * (ctype - 7)) + 24 * i - EXE_BASE
    return [c for c in struct.unpack_from('<4H', exe, a + 16) if c]


def check_pwl(R):
    """GU's motion set at each fixed model is PWL_FIX's 'from', its arc missing, the 'to' arc present"""
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    garc = lambda nn, g: '/nativeNX/arc/weapon/w%02d/g%02d.arc' % (nn, g) in R.files
    for path, model, frm, to in PWL_FIX:
        nn = int(path[-2:])
        pwl = res['weapon\\w%02d\\pwl\\%s' % (nn, path)]
        assert struct.unpack_from('<I', pwl, 8 + 16 * model)[0] == frm and not garc(nn, frm) and garc(nn, to), path
    fixed = {(int(p[-2:]), m) for p, m, _, _ in PWL_FIX}
    for nn, sid, ids4u in LINES:                     # every other model: its GU motion set has an arc
        pwl = res['weapon\\w%02d\\pwl\\pl_w%02d' % (nn, nn)]
        for m in {weapons4u.weapon_4u(open(EXE, 'rb').read(), nn, weapons4u.CLASS_INFO[nn][2], i)['model'] for i in ids4u}:
            assert (nn, m) in fixed or garc(nn, struct.unpack_from('<I', pwl, 8 + 16 * m)[0]), (nn, m)


def spec(R):
    exe = open(EXE, 'rb').read()
    classes, kire = [], []
    for nn, sid, ids4u in LINES:
        ptab = weapons4u.CLASS_INFO[nn][2]
        if nn != 13:                                 # the line follows the upgrade table; it ends there
            for a, b in zip(ids4u, ids4u[1:] + (None,)):
                assert children_4u(exe, nn, a) == ([b] if b else []), (nn, a, children_4u(exe, nn, a))
        ws = [weapons4u.weapon_4u(exe, nn, ptab, i) for i in ids4u]
        hr = ws[0]['model']
        assert all(sound_set_4u(nn, w['model']) == hr for w in ws), nn     # both arcs hold the HR model's set
        c = dict(nn=nn, standin=sid, ids4u=ids4u, srqr=hr)
        c.update({10: dict(bow=BOW), 13: dict(insect=IG_INSECT)}.get(nn, {}))
        classes.append(c)
        for w in ws:
            if 'sharp' in w and w['sharp'] not in kire: kire.append(w['sharp'])
    return dict(name=NAME, materials=items_em090.materials(R, exe), classes=classes, status=STATUS, kire_4u=kire,
                pwl_fix=PWL_FIX, substitutes=SUBSTITUTES)


def main():
    R = RomFS(gear4u.GU_ROMFS)
    check_pwl(R)
    s = spec(R)
    tables, texts, hooks, summary, log, kire = weapons4u.build(s)
    secs, hk = weapons4u.sections(tables, texts, hooks, s['pwl_fix'])
    have = set(open(weapons4u.OUT_HOOKS).read().split())
    missing = [l for l in hk.splitlines() if not set(l.split()) <= have]
    weapons4u.show(summary, log, kire, tables, hooks, s['status'])
    print('hooks missing from module/gear_hooks.txt:', missing or 'none')
    if sys.argv[1:] == ['show']:
        return
    assert not missing, 'module/gear_hooks.txt lacks %s: run tools/weapons4u.write_hooks' % missing
    for sec in secs: print('wrote', portdata.write_section(NAME, sec, 'weapons'))


if __name__ == '__main__':
    main()
