"""gear_weapons_em089.py : the 28 Gogmazios weapons as records appended to GU's loaded weapon tables
-> gen/gear_weapons_em089.inc (tables + names, read by module/gear.c) and module/gear_hooks.txt (load-exit hooks).
Spec: notes/gear-weapons.md (sections 1-8; section numbers below refer to it).

  gear_weapons_em089.py          write both files
  gear_weapons_em089.py show     print the per-weapon summary, the tables and the hooks; write nothing

Sources:
  - GU base RomFS tables (loc/arc/resident.arc, arc/facility/blacksmith.arc, <lang>/arc/resident_<lang>.arc).
  - GU 1.4 main (tools/gu.py): every table class's generated loader -> element alloc / free / ctor / parse, in-memory
    element size, hook site load + 0x3c (checked: `mov r0, r8; add sp, sp, #24`, count stored at res+0x64, array at
    res+0x6c, version literal = the file's f32).
  - 4U v1.1 exe (dump/exefs_v11/mem.bin @0x100000): weapon records via the equipment pointer table 0xf58868 (melee
    24 B, bow / bowguns 40 B), sharpness table 0xf581e4 (7 cumulative u16), create recipes 0xf3f000.. (24 B), upgrade
    recipes via the pointer table 0xf56974 (24 B per weapon ID: 4 x {u16 item, u16 count}), IG upgrades 0xf569a8
    (12 B per ID: u16 ID, u16 kinsect level, 2 x {item, count}). Names: core_common <Class>Name_<lang>.
  - kiranico 4U pages (notes section 7): bowgun ammo, bow coatings (not in the decoded part of the 4U record).
Choices (notes section 8 unless noted):
  - IDs = the v1.0 BaseData counts; IG line Messenger's Mark -> Luminary's Mark -> Limbo Lacrimosa (83 -> 84 -> 85).
  - One level per weapon (mMaxLv 1, mMaxLvForLimit 0, one LevelData row); a weapon with a child derives at level 1.
  - Every record is a copy of the stand-in's (GU weapon whose sound set is reused) with fields set; the
    stand-in's final level row for LevelData; a stand-in without a create recipe lends the table's first plain one.
  - mModelID = the 4U record's model number: GU kept 4U weapon model numbers and all 14 Gogma ones are free; the
    arcs come from tools/weapon4u2gu.py (romfs/nativeNX/arc/weapon/wNN/<model>.arc), pwl fixes in gear.c.
  - mSrqrNo = mModelID (as for ~95 % of GU weapons): the 4U sounds converted by tools/wsnd4u2gu.py into
    wNN/snd/<model>.arc. mSndMaterial (GU-only bone/iron hit set; 4U's hit sounds are class-wide) is a port choice.
  - mRare 9, mPrice = the 4U price, mPriceChangeLv 0, mSndMaterial 1, mColorIndex 0, mNamed 0, mSpecialSkill 0,
    mSortID = class max + 1.., Sleep (mElement 8) at the 4U value / 10; the IG's hidden 4U sleep made visible.
  - Sharpness: 4U entries 88 / 100 / 89 appended to kireajiData as 164 / 165 / 166, mKireLevel = 2 x 4U level (12).
  - Recipes: the 4U exe's, checked against notes/content-plan.md "Appendix" (+ IG upgrades), items mapped by English
    name to GU itemData_eng (our materials 2977.. included); create: mLv 1, mKey[0] 2, no provision, no scraps;
    process: one level-1 record per weapon, all-zero for a create weapon, no provision, no scraps.
  - Bowguns: ammo per kiranico in section 2's slot order (n -> count n enabled, (n) -> count n disabled); kept from
    the stand-in (maps unresolved, logged): special ammo, rapid / crouch fire, recoil, reload, deviation, slot 32.
  - Names: A = B = C = the 4U name; descriptions: 4U's (EXP_4U index tables; create and upgrade share one in 4U).
"""
import os, re, struct, sys, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
from gear_em089 import text4u, gu_item_names, c_bytes, c_str, exp_4u, LANGS, GU_ROMFS, EXE, EXE_BASE  # noqa: E402
from build_assets import RomFS, arc as gu_arc, gmd  # noqa: E402
import gu  # noqa: E402

OUT_INC = os.path.join(MON, 'gen/gear_weapons_em089.inc')
OUT_HOOKS = os.path.join(ROOT, 'module/gear_hooks.txt')
PCREFS = os.path.join(ROOT, 'dump/gu_pcrefs.pkl')

PTAB_4U, KIRE_4U, UPGRADE_4U, IG_UPGRADE_4U = 0xf58868, 0xf581e4, 0xf56974, 0xf569a8
CREATE_4U = (0xf3f000, 0xf55400)
KIRE_4U_IDX = (88, 100, 89)              # 4U sharpness entries used by the Gogma weapons -> GU 164, 165, 166
RARE, SLEEP = 9, 8                       # GU mRare (0-based), mElement sleep
# GU NN, short, 4U text class, 4U equipment pointer-table index, 4U create-recipe type, GU stand-in ID, 4U IDs
# (create weapon first, then each upgrade of the previous one)
CLASSES = [(0, 'GS', 'Lsword', 0, 7, 71, (222, 223)),          # Akantor Broadsword
           (1, 'SnS', 'Sword', 1, 8, 63, (227, 228)),          # Akantor Duo
           (2, 'Hammer', 'Hammer', 2, 9, 18, (221, 222)),      # Demonlord Hammer
           (3, 'Lance', 'Lance', 3, 10, 48, (198, 199)),       # Demonlord Spear
           (4, 'HBG', 'Heavy', 19, 12, 55, (141,)),            # Akantor Cannon
           (6, 'LBG', 'Light', 18, 11, 58, (165,)),            # Demonlord Blaster
           (7, 'LS', 'Lsword2', 6, 13, 68, (199, 200)),        # Akantor Katana
           (8, 'SA', 'Axe', 7, 14, 56, (180, 181)),            # Akantor Switch Axe
           (9, 'GL', 'Lance2', 8, 15, 60, (201, 202)),         # Akantor Gunlance
           (10, 'Bow', 'Bow', 23, 16, 56, (183, 184)),         # Akantor Bow
           (11, 'DB', 'Wsword', 10, 17, 63, (208, 209)),       # Akantor Blades
           (12, 'HH', 'Hammer2', 11, 18, 60, (164, 165)),      # Akantor Horn
           (13, 'IG', 'Rod', 12, 19, 43, (130, 131, 132)),     # Demonlord Cudgel
           (14, 'CB', 'Gaxe', 13, 20, 41, (98, 99))]           # Akantor C. Blade
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
BOW_KYOKU, BOW_TAME = 2, 3
BOW_BOTTLES = (1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1)
BOW_CSHOT = {183: (9, 4, 9, 4), 184: (9, 4, 10, 5)}       # section 8 (Spread4 Rapid4 Spread4/5 Rapid4/5)
HH_NOTES_4U, HH_FUE = 3, 2               # 4U note set purple/red/blue -> GU fueMusicData 2 = (2, 3, 4)
IG_INSECT = 1                            # Culldrone (cutting; 4U extra 0 = Cutting)
# 4U description index per weapon ID (u16 table per class, GU NN -> address) -> core_common <Class>Exp_<lang>; found
# by vote over the weapons GU took from 4U, as gear_em089.EXP_4U (C)
EXP_4U = {0: 0xef1ae2, 1: 0xef1cce, 2: 0xef1ebc, 3: 0xef20aa, 4: 0xef23cc, 6: 0xef225a, 7: 0xef2506, 8: 0xef26cc,
          9: 0xef2858, 10: 0xef2a12, 11: 0xef2bae, 12: 0xef2d78, 13: 0xef2eea, 14: 0xef302a}
PRICES = {(13, 0): 60000, (13, 1): 120000}   # brief: IG 60000 / 120000 / 130000, else 80000 / 130000


class Layout:
    """file record layout (notes sections 1-6), (property, struct code) in file order"""
    def __init__(s, fields):
        s.names = [n for n, _ in fields]
        s.fmt = '<' + ''.join(f for _, f in fields)
        s.size = struct.calcsize(s.fmt)

    def dec(s, b):
        return dict(zip(s.names, struct.unpack(s.fmt, b)))

    def enc(s, d):
        assert set(d) == set(s.names), set(d) ^ set(s.names)
        return struct.pack(s.fmt, *(d[n] for n in s.names))


def base_layout(nn):
    L = [('mIndex', 'I'), ('mModelID', 'H'), ('mSrqrNo', 'H'), ('mSndMaterial', 'B'), ('mMaxLv', 'B'),
         ('mMaxLvForLimit', 'B'), ('mRare', 'B'), ('mPrice', 'I'), ('mPriceChangeLv', 'B')]
    if nn == 11:
        L += [('mElement1', 'B'), ('mElement2', 'B')]
    elif nn not in (4, 6):
        L += [('mElement', 'B')]
        L += {8: [('mBinType', 'B')], 14: [('mBinType', 'B')], 9: [('mShootType', 'B')],
              13: [('mInsectType', 'B')]}.get(nn, [])
    L += [('mColorIndex', 'B'), ('mSortID', 'H'), ('mNamed', 'B'), ('mSpecialSkill', 'B')]
    for k in range(5):
        L += [('mDeriveLv[%d]' % k, 'B'), ('mDeriveID[%d]' % k, 'B')]
    return Layout(L)


def level_layout(nn):
    L = [('mIndex', 'I'), ('mNo', 'B'), ('mLevel', 'B')]
    if nn in (4, 6):
        L += [('mAttack', 'H'), ('mDefense', 'B'), ('mAffinity', 'B'), ('mSlotCount', 'B'), ('mBure', 'B'),
              ('mReloadSpeed', 'B'), ('mRecoil', 'B')]
        L += [('%s[%d]' % ('mDownShot' if nn == 4 else 'mQuickShot', k), 'B') for k in range(5)]
        for k in range(5):
            L += [('mUniqueShell[%d]' % k, 'B'), ('mUniqueHaveShellCount[%d]' % k, 'B'), ('mUniqueShellCount[%d]' % k, 'B')]
        for k in range(33):
            L += [('mLoadShellCount[%d]' % k, 'B'), ('mLoadEnableShell[%d]' % k, 'B')]
    elif nn == 10:
        L += [('mAttack', 'H'), ('mDefense', 'B'), ('mAffinity', 'B'), ('mElementValue', 'H'), ('mSlotCount', 'B'),
              ('mKyoku', 'B'), ('mTameDankai', 'B')]
        L += [('mCShotKind[%d]' % k, 'B') for k in range(4)] + [('mLoadEnableBottle[%d]' % k, 'B') for k in range(12)]
    else:
        L += [('mKireType', 'B'), ('mKireLevel', 'B'), ('mAttack', 'H'), ('mDefense', 'B'), ('mAffinity', 'B')]
        L += [('mElementValue1', 'H'), ('mElementValue2', 'H')] if nn == 11 else [('mElementValue', 'H')]
        L += {8: [('mBinElementValue', 'H')], 14: [('mBinElementValue', 'H')], 9: [('mShootLevel', 'B')],
              12: [('mFueMusicType', 'B')]}.get(nn, [])
        L += [('mSlotCount', 'B')]
    return Layout(L)


CREATE = Layout([('mLv', 'H'), ('mNo', 'H'), ('mDispFlag', 'H')] +
                sum([[('mItem[%d]' % k, 'H'), ('mNum[%d]' % k, 'B'), ('mKey[%d]' % k, 'B')] for k in range(4)], []) +
                [('mCategory', 'H'), ('mRank', 'H')] +
                sum([[('mPiece[%d]' % k, 'H'), ('mPieceNum[%d]' % k, 'H')] for k in range(3)], []))
PROCESS = Layout([('mNo', 'H'), ('mLv', 'H')] + sum([[('mItem[%d]' % k, 'H'), ('mNum[%d]' % k, 'B')] for k in range(4)], []) +
                 [('mCategory', 'H'), ('mRank', 'H')] +
                 sum([[('mPiece[%d]' % k, 'H'), ('mPieceNum[%d]' % k, 'H')] for k in range(3)], []))
MSGIDX = Layout([('mIndex', 'I')])
KIRE = Layout([('mSlash[%d]' % k, 'H') for k in range(7)])


def table(data, lay):
    n = struct.unpack_from('<I', data, 4)[0]
    if len(data) != 8 + n * lay.size:
        sys.exit('table size %d != 8 + %d x %d' % (len(data), n, lay.size))
    return n, [lay.dec(data[8 + lay.size * i: 8 + lay.size * (i + 1)]) for i in range(n)]


# ---- 4U
def u32(exe, a):
    return struct.unpack_from('<I', exe, a - EXE_BASE)[0]


def weapon_4u(exe, nn, ptab, i):
    if nn in (4, 6, 10):
        r = exe[u32(exe, PTAB_4U + 4 * ptab) - EXE_BASE + 40 * i:][:40]
        return dict(model=struct.unpack_from('<H', r, 0)[0], rare=r[4] + 1, price=struct.unpack_from('<I', r, 8)[0],
                    raw=struct.unpack_from('<H', r, 12)[0], slots=r[16], aff=struct.unpack_from('b', r, 17)[0],
                    defense=0, charges=tuple(r[22:26]))
    r = exe[u32(exe, PTAB_4U + 4 * ptab) - EXE_BASE + 24 * i:][:24]
    w = dict(model=struct.unpack_from('<H', r, 0)[0], sharp=r[2], kire=r[3], price=struct.unpack_from('<I', r, 4)[0],
             raw=struct.unpack_from('<H', r, 8)[0], defense=r[10], aff=struct.unpack_from('b', r, 11)[0],
             elem=r[12], status=r[14], value=struct.unpack_from('b', r, 15)[0], slots=r[16], extra=r[17], rare=r[19] + 1)
    assert w['elem'] == 0 and w['status'] == 3 and w['sharp'] in KIRE_4U_IDX and w['kire'] == 6, w   # 3 = sleep
    return w


def recipes_4u(exe, t4, ctype, ids4u, nn):
    """[(4U item name, count)] per weapon: create recipe for the first, upgrade recipe for the others"""
    name = lambda pairs: [(t4['itemName'][it], c) for it, c in pairs if it]
    out = []
    hits = [a for a in range(CREATE_4U[0], CREATE_4U[1], 24) if struct.unpack_from('<HH', exe, a + 4 - EXE_BASE) ==
            (ctype, ids4u[0])]
    assert len(hits) == 1, (ctype, ids4u[0], hits)
    v = struct.unpack_from('<8H', exe, hits[0] + 8 - EXE_BASE)
    out.append(name(zip(v[0::2], v[1::2])))
    for i in ids4u[1:]:
        if nn == 13:
            r = struct.unpack_from('<6H', exe, IG_UPGRADE_4U + 12 * i - EXE_BASE)
            assert r[0] == i, r
            out.append(name(zip(r[2::2], r[3::2])))
        else:
            v = struct.unpack_from('<8H', exe, u32(exe, UPGRADE_4U + 4 * (ctype - 7)) + 24 * i - EXE_BASE)
            out.append(name(zip(v[0::2], v[1::2])))
    return out


# ---- GU main: table classes
_P = None
def gu_class(name, version):
    """resource class -> load, element alloc / free / ctor / parse, in-memory element size, hook site (load + 0x3c);
    the generated loader is checked instruction by instruction (exits on any mismatch)"""
    global _P
    if _P is None:
        _P = {}
        for b, r in pickle.load(open(PCREFS, 'rb')).items():
            _P.setdefault(r[0], []).append(b)
    M = bytes(gu.MEM)
    s = M.find(name.encode() + b'\0')
    while s > 0 and M[s - 1] != 0:
        s = M.find(name.encode() + b'\0', s + 1)
    site = min(_P.get(s, [0]))
    if not site: sys.exit('%s: class name not referenced' % name)
    gots = lambda a, n: [(a + 4 * k, gu.pcref(a + 4 * k)[0]) for k in range(n)
                         if gu.pcref(a + 4 * k) and gu.pcref(a + 4 * k)[1] == 'got']
    g = gots(site - 0x10, 16)
    dti = [v for b, v in g if b < site][-1]
    newi = gu.u32([v for b, v in g if b > site][0] + 16)
    cvt = [v for b, v in gots(newi, 40) if v != dti][0]
    load = gu.u32(cvt + 8 + 11 * 4)
    ins = [gu.INS.get(load + 4 * k, ('?', '')) for k in range(120)]
    end = next(k for k in range(1, 120) if ins[k][0] == 'push')
    ins = ins[:end]
    err = lambda m: sys.exit('%s load %x: %s' % (name, load, m))
    if ins[15] != ('mov', 'r0, r8') or ins[16] != ('add', 'sp, sp, #24'):
        err('exit site %x is %s / %s' % (load + 0x3c, ins[15], ins[16]))
    ver = []                             # the f32 compared with the file's version: a pc literal or an immediate
    for k, (m, o) in enumerate(ins[:12]):
        lit = re.match(r's2, \[pc, #(\d+)\]$', o) if m == 'vldr' else None
        imm = re.match(r's2, #(\S+)$', o) if m == 'vmov.f32' else None
        if lit: ver.append(M[load + 4 * k + 8 + int(lit.group(1)):][:4])
        if imm: ver.append(struct.pack('<f', float(imm.group(1))))
    if ver != [version]:
        err('version %s is not the file\'s %s' % ([v.hex() for v in ver], version.hex()))
    calls = [(k, int(o.split()[0], 16)) for k, (m, o) in enumerate(ins) if m == 'bl']
    fixed = {0: 0x8260d4, 1: 0x8269f4, 2: 0x826130, 5: 0x8263f8}     # reader ctor, read f32, reader dtor, read u32
    if len(calls) != 9 or any(calls[i][1] != v for i, v in fixed.items()):
        err('call pattern %s' % [hex(c) for _, c in calls])
    free, alloc, ctor, parse = calls[4][1], calls[6][1], calls[7][1], calls[8][1]
    k_cnt, k_alloc = calls[5][0], calls[6][0]
    m_cnt = re.match(r'(r\d+), r0$', ins[k_cnt + 1][1]) if ins[k_cnt + 1][0] == 'mov' else None
    after = ins[k_alloc + 1:k_alloc + 5]     # header size store and array = base + 8, in either order
    m_size = [re.match(r'(r\d+), \[r0\]$', o) for m, o in after if m == 'str' and re.match(r'r\d+, \[r0\]$', o)]
    m_arr = [re.match(r'(r\d+), r0, #8$', o) for m, o in after if m == 'add' and re.match(r'r\d+, r0, #8$', o)]
    if not (m_cnt and len(m_size) == 1 and len(m_arr) == 1):
        err('count / size / array registers not found')
    m_size, m_arr = m_size[0], m_arr[0]
    sz = [int(re.match(r'r\d+, #(\d+)$', o).group(1)) for m, o in ins[k_cnt:k_alloc]
          if m == 'mov' and re.match(r'%s, #(\d+)$' % m_size.group(1), o)]
    stores = {(o.split(',')[0], o.split('#')[1].rstrip(']')) for m, o in ins if m == 'str' and '[r4, #' in o}
    if len(sz) != 1 or (m_arr.group(1), '0x6c') not in stores or (m_cnt.group(1), '0x64') not in stores:
        err('size %s / stores %s' % (sz, sorted(stores)))
    return dict(load=load, alloc=alloc, free=free, ctor=ctor, parse=parse, size=sz[0], site=load + 0x3c)


def build():
    R = RomFS(GU_ROMFS)
    exe = open(EXE, 'rb').read()
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    bs = gu_arc(R.read('/nativeNX/arc/facility/blacksmith.arc'))
    lres = {lang: gu_arc(R.read('/nativeNX/%s/arc/resident_%s.arc' % (lang, lang))) for lang in LANGS}
    t4 = {lang: text4u(lang) for lang in LANGS}
    it_gu = gmd(lres['eng']['eng\\table\\itemData_eng'])
    our = gu_item_names(R)
    misses, tables, texts, hooks, summary, log = [], [], [], [], [], []

    def gu_item(nm):
        ids = [i for i in range(len(it_gu) // 2) if it_gu[2 * i] == nm] or ([our[nm]] if nm in our else [])
        if len(ids) != 1: misses.append('%s (%d GU matches)' % (nm, len(ids)))
        return ids[0] if len(ids) == 1 else 0

    kd = res['table\\kireajiData']
    kn, _ = table(kd, KIRE)
    def cls(name, version, hook):
        c = gu_class(name, version)
        hooks.append((hook, c['site'], name))
        return c

    for nn, short, txt, ptab, ctype, sid, ids4u in CLASSES:
        w4 = [weapon_4u(exe, nn, ptab, i) for i in ids4u]
        rec4 = recipes_4u(exe, t4['eng'], ctype, ids4u, nn)
        for k, (r, plan) in enumerate(zip(rec4, RECIPES[short])):
            if dict(r) != plan or len(r) != len(plan):
                sys.exit('%s %d: 4U recipe %s != content-plan %s' % (short, ids4u[k], r, plan))
        bl, ll = base_layout(nn), level_layout(nn)
        bd, ld = res['table\\weapon%02dBaseData' % nn], res['table\\weapon%02dLevelData' % nn]
        n, base = table(bd, bl)
        ln, lv = table(ld, ll)
        ids = [n + k for k in range(len(ids4u))]
        assert ids[-1] <= 255 and base[sid]['mIndex'] == sid
        sort0 = max(b['mSortID'] for b in base)
        rows = [r for r in lv if r['mNo'] == sid]
        bout, lout = [], []
        for k, (i4, w) in enumerate(zip(ids4u, w4)):
            assert w['rare'] == 10 and w['defense'] == 0, w
            price = PRICES.get((nn, k), 80000 if k == 0 else 130000)
            assert w['price'] == price, (short, i4, w['price'])
            b = dict(base[sid])
            b.update(mIndex=ids[k], mModelID=w['model'], mSrqrNo=w['model'], mSndMaterial=1, mMaxLv=1, mMaxLvForLimit=0,
                     mRare=RARE, mPrice=price, mPriceChangeLv=0, mColorIndex=0, mSortID=sort0 + 1 + k, mNamed=0,
                     mSpecialSkill=0)
            for j in range(5):
                b['mDeriveLv[%d]' % j] = b['mDeriveID[%d]' % j] = 0
            if k + 1 < len(ids):
                b['mDeriveLv[0]'], b['mDeriveID[0]'] = 1, ids[k + 1]
            r = dict(rows[-1])
            r.update(mIndex=ln + len(lout), mNo=ids[k], mLevel=1, mAttack=w['raw'], mDefense=0, mAffinity=w['aff'] & 0xff,
                     mSlotCount=w['slots'])
            if nn in (4, 6):
                for s, tok in enumerate(AMMO[i4].split()):
                    r['mLoadShellCount[%d]' % s] = int(tok.strip('()'))
                    r['mLoadEnableShell[%d]' % s] = int(tok != '0' and not tok.startswith('('))
                fire = 'mDownShot' if nn == 4 else 'mQuickShot'
                log.append('%s %d %s: kept from the stand-in (ID %d Lv%d): mRecoil %d, mReloadSpeed %d, mBure %d, '
                           '%s %s, special ammo (shell, have, count) %s, ammo slot 32 (%d, %d)' % (
                               short, ids[k], t4['eng'][txt + 'Name'][i4], sid, rows[-1]['mLevel'],
                               r['mRecoil'], r['mReloadSpeed'], r['mBure'], fire, [r['%s[%d]' % (fire, j)] for j in range(5)],
                               [(r['mUniqueShell[%d]' % j], r['mUniqueHaveShellCount[%d]' % j],
                                 r['mUniqueShellCount[%d]' % j]) for j in range(5)],
                               r['mLoadShellCount[32]'], r['mLoadEnableShell[32]']))
            elif nn == 10:
                b['mElement'] = 0
                cshot = tuple(c + 1 for c in w['charges'])      # 4U Rapid n = n - 1, Spread n = n + 4 -> GU + 1 (G)
                assert cshot == BOW_CSHOT[i4], (i4, cshot)
                r.update(mElementValue=0, mKyoku=BOW_KYOKU, mTameDankai=BOW_TAME)
                for j in range(4): r['mCShotKind[%d]' % j] = cshot[j]
                for j in range(12): r['mLoadEnableBottle[%d]' % j] = BOW_BOTTLES[j]
            else:
                val = abs(w['value'])                            # IG: 4U hidden (negative) -> visible
                r.update(mKireType=kn + KIRE_4U_IDX.index(w['sharp']), mKireLevel=2 * w['kire'])
                if nn == 11:
                    b.update(mElement1=SLEEP, mElement2=0)
                    r.update(mElementValue1=val, mElementValue2=0)
                else:
                    b['mElement'] = SLEEP
                    r['mElementValue'] = val
                if nn in (8, 14):
                    assert w['extra'] == 0, w                    # Power phial / Impact
                    b['mBinType'], r['mBinElementValue'] = 0, 0
                elif nn == 9:
                    assert w['extra'] % 3 == 0, w                # 4U (level - 1) * 3 + type, type 0 Normal
                    b['mShootType'], r['mShootLevel'] = 0, w['extra'] // 3
                elif nn == 12:
                    assert w['extra'] == HH_NOTES_4U, w
                    r['mFueMusicType'] = HH_FUE
                elif nn == 13:
                    assert w['extra'] == 0, w                    # Cutting
                    b['mInsectType'] = IG_INSECT
            bout.append(bl.enc(b))
            lout.append(ll.enc(r))
            name = t4['eng'][txt + 'Name'][i4]
            summary.append((short, ids[k], name, b, r, rec4[k], k))
        tables.append(('table\\weapon%02dBaseData' % nn, cls('rWeapon%02dBaseData' % nn, bd[:4], 'gear_w%02d_base' % nn),
                       bl.size, n, bout))
        tables.append(('table\\weapon%02dLevelData' % nn, cls('rWeapon%02dLevelData' % nn, ld[:4], 'gear_w%02d_level' % nn),
                       ll.size, ln, lout))
        # name index (one per language arc, the same in all) and names (6 strings per weapon)
        mi = {lang: lres[lang]['%s\\table\\weapon%02dMsgData' % (lang, nn)] for lang in LANGS}
        mn, mrecs = table(mi['eng'], MSGIDX)
        assert mn == n and all(table(mi[lang], MSGIDX)[0] == n for lang in LANGS) and mrecs[sid]['mIndex'] == sid
        tables.append(('table\\weapon%02dMsgData' % nn, cls('rWeapon%02dMsgData' % nn, mi['eng'][:4], 'gear_w%02d_msg' % nn),
                       MSGIDX.size, n, [MSGIDX.enc(dict(mrecs[sid], mIndex=i)) for i in ids]))
        strs = []
        for lang in LANGS:
            g = lres[lang]['%s\\table\\weapon%02dMsgData_%s' % (lang, nn, lang)]
            ln_ = struct.unpack_from('<I', g, 0x24)[0]
            if g[0x28:0x28 + ln_] != b'weapon%02dMsgData' % nn or len(gmd(g)) != 6 * n:
                sys.exit('weapon%02dMsgData_%s: name %r, %d strings != 6 x %d' % (nn, lang, g[0x28:0x28 + ln_], len(gmd(g)), n))
            strs.append(sum([[t4[lang][txt + 'Name'][i], t4[lang][txt + 'Exp'][exp_4u(exe, EXP_4U[nn], i)]] * 3
                             for i in ids4u], []))
        texts.append(('weapon%02dMsgData' % nn, 6 * n, strs))
        # recipes: create (first weapon), process (one level-1 record per weapon)
        cd, pd = bs['table\\weaponCreateW%02d' % nn], bs['table\\weaponProcessW%02d' % nn]
        cn, crt = table(cd, CREATE)
        pn, prc = table(pd, PROCESS)
        tpl = [c for c in crt if c['mNo'] == sid] or [c for c in crt if c['mLv'] == 1 and c['mDispFlag'] == 0 and
                                                       c['mKey[0]'] == 2]
        if not any(c['mNo'] == sid for c in crt):
            log.append('%s: stand-in %d has no create recipe; template = the recipe of weapon %d' % (short, sid, tpl[0]['mNo']))
        c = dict(tpl[0], mLv=1, mNo=ids[0], mDispFlag=0, mCategory=0, mRank=0)
        for j in range(4):
            nm, cnt = rec4[0][j] if j < len(rec4[0]) else (None, 0)
            c.update({'mItem[%d]' % j: gu_item(nm) if nm else 0, 'mNum[%d]' % j: cnt, 'mKey[%d]' % j: 2 if j == 0 else 0})
        for j in range(3):
            c['mPiece[%d]' % j] = c['mPieceNum[%d]' % j] = 0
        ptpl = [p for p in prc if p['mNo'] == sid and p['mLv'] == 1]
        assert len(ptpl) == 1
        pout = []
        for k in range(len(ids)):
            p = dict(ptpl[0], mNo=ids[k], mLv=1, mCategory=0, mRank=0)
            mats = rec4[k] if k else []
            for j in range(4):
                nm, cnt = mats[j] if j < len(mats) else (None, 0)
                p.update({'mItem[%d]' % j: gu_item(nm) if nm else 0, 'mNum[%d]' % j: cnt})
            for j in range(3):
                p['mPiece[%d]' % j] = p['mPieceNum[%d]' % j] = 0
            pout.append(PROCESS.enc(p))
        tables.append(('table\\weaponCreateW%02d' % nn, None, CREATE.size, cn, [CREATE.enc(c)]))
        tables.append(('table\\weaponProcessW%02d' % nn, None, PROCESS.size, pn, pout))
    if misses:
        sys.exit('item names not in GU itemData_eng: %s' % ', '.join(sorted(set(misses))))
    # the create / process classes (one each, 14 files) and kireajiData
    cc = cls('rWeaponCreateData', bs['table\\weaponCreateW00'][:4], 'gear_w_create')
    pc = cls('rWeaponProcessData', bs['table\\weaponProcessW00'][:4], 'gear_w_process')
    for k, t in enumerate(tables):
        if t[1] is None:
            tables[k] = (t[0], cc if 'Create' in t[0] else pc) + t[2:]
    kire = [KIRE.dec(exe[KIRE_4U + 14 * i - EXE_BASE:][:14]) for i in KIRE_4U_IDX]
    assert all(k['mSlash[6]'] == 450 for k in kire)
    tables.append(('table\\kireajiData', cls('rKireajiData', kd[:4], 'gear_kireaji'), KIRE.size, kn,
                   [KIRE.enc(k) for k in kire]))
    for lang in LANGS:
        for nn in [c[0] for c in CLASSES]:                       # every language: the same versions as eng
            assert lres[lang]['%s\\table\\weapon%02dMsgData' % (lang, nn)][:4] == lres['eng']['eng\\table\\weapon%02dMsgData' % nn][:4]
    return tables, texts, hooks, summary, log, kire


def render(tables, texts, hooks):
    out = ['/* generated by tools/gear_weapons_em089.py: do not edit */',
           '/* one entry per table to extend: resource path (matched as a suffix of the resource path at res+0x8, so a',
           ' * per-language table like "eng\\table\\weapon00MsgData" is matched by "table\\weapon00MsgData"), element class',
           ' * alloc / free / ctor / parse (main offsets), in-memory element size, file record size, expected v1.0 count,',
           ' * records to append, the records (file format) */']
    ents = []
    for k, (path, c, rb, expect, recs) in enumerate(tables):
        data = b''.join(recs)
        assert len(data) == rb * len(recs)
        out.append('static const uint8_t gw_r%d[] = {   /* %s: %d x %d B */\n%s\n};' % (k, path, len(recs), rb, c_bytes(data)))
        ents.append('    {"%s", 0x%x, 0x%x, 0x%x, 0x%x, %d, %d, %d, %d, gw_r%d},' % (
            path.replace('\\', '\\\\'), c['alloc'], c['free'], c['ctor'], c['parse'], c['size'], rb, expect, len(recs), k))
    out.append('static const struct gear_tbl gear_weapon_tables[] = {\n%s\n};' % '\n'.join(ents))
    out.append('#define GEAR_WEAPON_TABLES (sizeof gear_weapon_tables / sizeof gear_weapon_tables[0])')
    out.append('/* names: GMD internal name (e.g. "weapon00MsgData"), expected string count, strings to append, per language\n'
               ' * eng fre ger ita spa */')
    ents = []
    for k, (name, expect, strs) in enumerate(texts):
        body = '\n'.join('    { /* %s */\n%s\n    },' % (lang, ',\n'.join('        ' + c_str(s) for s in ss))
                         for lang, ss in zip(LANGS, strs))
        out.append('static const char *const gw_t%d[%d][%d] = {\n%s\n};' % (k, len(LANGS), len(strs[0]), body))
        ents.append('    {"%s", %d, %d, {%s}},' % (name, expect, len(strs[0]), ', '.join('gw_t%d[%d]' % (k, j) for j in range(len(LANGS)))))
    out.append('static const struct gear_text gear_weapon_text[] = {\n%s\n};' % '\n'.join(ents))
    out.append('#define GEAR_WEAPON_TEXTS (sizeof gear_weapon_text / sizeof gear_weapon_text[0])')
    out.append('/* load-exit hooks, one per distinct table class (load + 0x3c) */')
    out += ['GEAR_HOOK(%s)' % h for h, _, _ in hooks]
    return '\n'.join(out) + '\n', ''.join('%s 0x%X\n' % (h, s) for h, s, _ in hooks)


def show(summary, log, kire, tables, hooks):
    for short, i, name, b, r, mats, k in summary:
        elem = r.get('mElementValue', r.get('mElementValue1', 0))
        sharp = 'kire %d/%d' % (r['mKireType'], r['mKireLevel']) if 'mKireType' in r else '-'
        print('%-6s %3d %-22s raw %d aff %d sleep %s slots %d %s model %d/%d price %d derive %s  %s %s' % (
            short, i, name, r['mAttack'], struct.unpack('b', bytes([r['mAffinity']]))[0],
            elem * 10 if b.get('mElement', b.get('mElement1')) == SLEEP else '-', r['mSlotCount'], sharp,
            b['mModelID'], b['mSrqrNo'], b['mPrice'], '%d@Lv%d' % (b['mDeriveID[0]'], b['mDeriveLv[0]']) if b['mDeriveID[0]'] else '-',
            'create' if k == 0 else 'upgrade', ', '.join('%s %d' % m for m in mats)))
    print('kireaji appended:', [tuple(k.values()) for k in kire])
    for l in log: print('log:', l)
    for path, c, rb, expect, recs in tables:
        print('table %-26s expect %4d n %d (rec %d B, mem %d B)' % (path, expect, len(recs), rb, c['size']))
    for h, s, name in hooks:
        print('hook %-16s 0x%X  %s' % (h, s, name))


def main():
    tables, texts, hooks, summary, log, kire = build()
    inc, hk = render(tables, texts, hooks)
    show(summary, log, kire, tables, hooks)
    if sys.argv[1:] == ['show']:
        return
    open(OUT_INC, 'w', encoding='utf-8').write(inc)
    open(OUT_HOOKS, 'w').write(hk)
    print('wrote', OUT_INC, OUT_HOOKS)


if __name__ == '__main__':
    main()
