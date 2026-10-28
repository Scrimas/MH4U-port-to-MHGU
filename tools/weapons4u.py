"""weapons4u.py : MH4U weapons -> records appended to GU's loaded weapon tables (data file sections TBLA / TXTA /
PWLF, tools/portdata.py; read by module/gear.c) and module/gear_hooks.txt, shared by the monsters' weapon tools
(monsters/<name>/tools/gear_weapons_*.py, which give the spec). Spec of the tables: notes/gear-weapons.md (sections
1-8; section numbers below refer to it).

  import weapons4u
  tables, texts, hooks, summary, log, kire = weapons4u.build(spec)
  secs, hooks_txt = weapons4u.sections(tables, texts, hooks, spec['pwl_fix'])

spec = dict(name=allocations.toml name, materials=items4u.Materials, classes=[class spec], status={4U status: GU
mElement}, kire_4u=[4U sharpness entries, in append order], pwl_fix=[(path suffix, model, GU value, ours)],
substitutes={4U item name: GU item name}); class spec = dict(nn=GU class, ids4u=(create weapon, then each upgrade of
the previous one), standin=GU weapon ID whose records are copied, recipes=optional expected [{item name: count}],
ammo={4U id: ammo string} (bowguns, optional: default the 4U record's, a given string must equal it),
bow=dict(kyoku, tame, bottles, cshot={4U id: expected charge shots}; each optional: kyoku None / absent = the
stand-in's (not in the 4U record), bottles default the 4U record's coatings, tame / cshot given = checked against the
record), hh=(4U note set, GU fueMusicData) (optional: default the 4U set's own index, the two tables being equal),
insect=GU mInsectType, srqr=sound set (default the model number: the 4U arc's own sounds converted by
tools/wsnd4u2gu.py; a 4U arc holding another weapon's set uses GU's arc of that number), first_upgrade=True (the
first weapon has no 4U create recipe: it is forged from its own 4U upgrade recipe's materials, the parent left out)).

Sources:
  - GU base RomFS tables (loc/arc/resident.arc, arc/facility/blacksmith.arc, <lang>/arc/resident_<lang>.arc).
  - GU 1.4 main (tools/gu.py): every table class's generated loader -> element alloc / free / ctor / parse, in-memory
    element size, hook site load + 0x3c (checked: `mov r0, r8; add sp, sp, #24`, count stored at res+0x64, array at
    res+0x6c, version literal = the file's f32).
  - 4U v1.1 exe (dump/exefs_v11/mem.bin @0x100000): weapon records via the equipment pointer table 0xf58868 (melee
    24 B, bow / bowguns 40 B), sharpness table 0xf581e4 (7 cumulative u16), create recipes 0xf3f000.. (24 B), upgrade
    recipes via the pointer table 0xf56974 (24 B per weapon ID: 4 x {u16 item, u16 count}), IG upgrades 0xf569a8
    (12 B per ID: u16 ID, u16 kinsect level, 2 x {item, count}; ID and level 0 on a G weapon upgraded from an HR
    one: Metalmangler+ 97, Self-possession 100). Names: core_common <Class>Name_<lang>.
  - 4U fields read by vote over the 4U / GU weapons of the same English name (C = the 4U value on (nearly) every
    pair, S = on most, GU retuned the rest): 40-B records +14 defense (C), +15 bow charge levels = mTameDankai (C),
    bow +18 / +19 element, +20 / +21 status (type, s8 value: as melee +12..+15; S), bow +32 u32 coatings (S, bit 1
    Power, 2 Poison, 3 Para, 4 Sleep, 5 C.Range, 6 Paint, 7 Exhaust, 8 Blast; bits 9..15 unknown), bowgun +5
    deviation = GU mBure (C, kept from the stand-in like recoil / reload), +7 ammo record index into the 39-B count
    records AMMO_4U (one per bowgun; code literals 0x282368 / 0x28236c) and +32 40-bit loadable mask (C: decodes
    Gogmazios' kiranico ammo exactly); melee +17 SA / CB phial = GU mBinType (S), GL (level - 1) * 3 + type =
    GU mShootType / mShootLevel + 1 (S), HH note set = an index into NOTES_4U, byte-equal to GU fueMusicData (C;
    identity on most HH pairs). 4U elements +12 1..5 (fire, water, thunder, dragon, ice) = GU mElement 1..5 (C).
    Bow arc shot: not in the 40-B record (searched; G: another table).
Rules (notes section 8; port choices made for Gogmazios, kept for every monster):
  - IDs: a monster's weapons follow GU's and the earlier monsters' (allocations.toml [monster.append.weapons]); each
    line is its own tree: the first weapon from its create recipe, each next one an upgrade of the previous one.
  - One level per weapon (mMaxLv 1, mMaxLvForLimit 0, one LevelData row); a weapon with a child derives at level 1.
  - Every record is a copy of the stand-in's with fields set; the stand-in's final level row for LevelData; a
    stand-in without a create recipe lends the table's first plain one.
  - mModelID = mSrqrNo = the 4U record's model number (GU kept 4U's numbers; arcs from tools/weapon4u2gu.py, sounds
    from tools/wsnd4u2gu.py); mSndMaterial 1; mRare = 4U rarity - 1; mPrice = the 4U price; mPriceChangeLv 0,
    mColorIndex 0, mNamed 0, mSpecialSkill 0, mSortID = after GU's and the earlier monsters'.
  - Element / status (melee and bows): the 4U value (value / 10 in both games), hidden (negative, needs Awaken)
    made visible (GU has no Awaken); statuses through spec status, a weapon with both: refused. DB: mElement1 = the
    record's, mElement2 = its DB2_4U entry's (S: the GU same-name dual DBs keep that order).
  - Sharpness: the monster's 4U entries appended to kireajiData; mKireLevel = 2 x the 4U level.
  - Recipes: the 4U exe's, items by English name in GU itemData_eng (our materials included; spec substitutes for 4U
    items GU lacks); create: mLv 1, mKey[0] 2, no provision, no scraps; process: one level-1 record per weapon,
    all-zero for a create weapon, no provision, no scraps.
  - Bowguns: ammo in section 2's slot order (n -> count n enabled, (n) -> count n disabled), from the 4U record
    (ammo_4u); kept from the stand-in (logged): special ammo, rapid / crouch fire, recoil, reload, deviation, slot 32.
  - Names: A = B = C = the 4U name; descriptions: 4U's (EXP_4U index tables; create and upgrade share one in 4U).
"""
import os, re, struct, sys, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_EDITOR_TOOLS)
import alloc, gu, portdata                          # noqa: E402
from gear4u import text4u, gu_item_names, gu_str, exp_4u, LANGS, GU_ROMFS, EXE, EXE_BASE  # noqa: E402
from build_assets import RomFS, arc as gu_arc, gmd  # noqa: E402

OUT_HOOKS = os.path.join(paths.ROOT, 'module/gear_hooks.txt')
PCREFS = os.path.join(paths.ROOT, 'dump/gu_pcrefs.pkl')

PTAB_4U, KIRE_4U, UPGRADE_4U, IG_UPGRADE_4U = 0xf58868, 0xf581e4, 0xf56974, 0xf569a8
CREATE_4U = (0xf3f000, 0xf55400)
AMMO_4U = {6: 0xfb2bf4, 4: 0xfb4739}     # bowgun ammo count records (39 B: 4U ammo index -> clip size), per class
NOTES_4U = 0xf31da4                      # HH note sets, 50 x 3 colours (= GU table\fueMusicData)
ELEMENT_4U = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}   # 4U element -> GU mElement (fire, water, thunder, dragon, ice)
# DB second element (C: read by 0x2f8a00 / 0x2f8d64, DB only, index = the melee record's +17 via 0x2f81c4): 4 B per
# index {u8 element, s8 value, u8 status, s8 value} (the melee record's types and units); index 0 = none. Indexes 1..30
# are the 28 4U dual-element DBs (Twin Nails 1 blast record + ice 40 here: the GU same-name weapons all have mElement2)
DB2_4U = 0xf588f4
# 4U ammo index -> GU ammo slot (section 2): 0..19 the same (Normal .. Dragon), 20 none (Slicing, G), 21..30 -> 20..29
# (Poison .. Recover), 31 / 32 none (G: Demon / Armor), 33 / 34 -> 30 / 31 (Paint / Tranq; order G, both 2 everywhere)
AMMO_SLOT = dict([(k, k) for k in range(20)] + [(k, k - 1) for k in range(21, 31)] + [(33, 30), (34, 31)])
# bow coating mask bit -> GU mLoadEnableBottle indexes (4U Power = GU Power Lv1 + Lv2, as the Gogmazios / Tigerstripe
# specs; [2] / [3] element coatings: GU only; [11]: set on every GU row)
COATING_4U = {1: (0, 1), 2: (5,), 3: (6,), 4: (7,), 5: (4,), 6: (10,), 7: (8,), 8: (9,)}
SND_MATERIAL = 1
# GU NN -> short name, 4U text class, 4U equipment pointer-table index, 4U create-recipe type
CLASS_INFO = {0: ('GS', 'Lsword', 0, 7), 1: ('SnS', 'Sword', 1, 8), 2: ('Hammer', 'Hammer', 2, 9),
              3: ('Lance', 'Lance', 3, 10), 4: ('HBG', 'Heavy', 19, 12), 6: ('LBG', 'Light', 18, 11),
              7: ('LS', 'Lsword2', 6, 13), 8: ('SA', 'Axe', 7, 14), 9: ('GL', 'Lance2', 8, 15),
              10: ('Bow', 'Bow', 23, 16), 11: ('DB', 'Wsword', 10, 17), 12: ('HH', 'Hammer2', 11, 18),
              13: ('IG', 'Rod', 12, 19), 14: ('CB', 'Gaxe', 13, 20)}
# 4U description index per weapon ID (u16 table per class, GU NN -> address) -> core_common <Class>Exp_<lang>; found
# by vote over the weapons GU took from 4U, as gear4u.EXP_4U (C)
EXP_4U = {0: 0xef1ae2, 1: 0xef1cce, 2: 0xef1ebc, 3: 0xef20aa, 4: 0xef23cc, 6: 0xef225a, 7: 0xef2506, 8: 0xef26cc,
          9: 0xef2858, 10: 0xef2a12, 11: 0xef2bae, 12: 0xef2d78, 13: 0xef2eea, 14: 0xef302a}


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
    s8 = lambda r, k: struct.unpack_from('b', r, k)[0]
    if nn in (4, 6, 10):
        r = exe[u32(exe, PTAB_4U + 4 * ptab) - EXE_BASE + 40 * i:][:40]
        w = dict(model=struct.unpack_from('<H', r, 0)[0], rare=r[4] + 1, price=struct.unpack_from('<I', r, 8)[0],
                 raw=struct.unpack_from('<H', r, 12)[0], slots=r[16], aff=s8(r, 17), defense=r[14],
                 charges=tuple(r[22:26]), elem=0, elem_value=0, status=0, value=0)
        if nn == 10:
            w.update(elem=r[18], elem_value=s8(r, 19), status=r[20], value=s8(r, 21), tame=r[15],
                     coatings=struct.unpack_from('<I', r, 32)[0])
        else:
            w.update(bure=r[5], ammo=exe[AMMO_4U[nn] - EXE_BASE + 39 * r[7]:][:39],
                     loadable=int.from_bytes(r[32:37], 'little'))
        return w
    r = exe[u32(exe, PTAB_4U + 4 * ptab) - EXE_BASE + 24 * i:][:24]
    return dict(model=struct.unpack_from('<H', r, 0)[0], sharp=r[2], kire=r[3], price=struct.unpack_from('<I', r, 4)[0],
                raw=struct.unpack_from('<H', r, 8)[0], defense=r[10], aff=s8(r, 11), elem=r[12], elem_value=s8(r, 13),
                status=r[14], value=s8(r, 15), slots=r[16], extra=r[17], rare=r[19] + 1)


def elem_status(w, status):
    """(GU mElement, value / 10) of a 4U record: its element, else its status (spec status: 4U -> GU), else none"""
    if w['elem'] and w['status']:
        sys.exit('4U weapon with element %d and status %d: not supported' % (w['elem'], w['status']))
    if w['elem']:
        return ELEMENT_4U[w['elem']], abs(w['elem_value'])
    if w['status']:
        return status[w['status']], abs(w['value'])
    return 0, 0


def db_second_4u(exe, w, status):
    """(GU mElement2, value / 10) of a 4U DB record: its +17 indexes DB2_4U (0 = single element); the entry's element,
    else its status (spec status: 4U -> GU), visible as the first one"""
    if not w['extra']:
        return 0, 0
    et, ev, st, sv = struct.unpack_from('<BbBb', exe, DB2_4U + 4 * w['extra'] - EXE_BASE)
    if bool(et) == bool(st):
        sys.exit('4U DB second element %d: element %d and status %d' % (w['extra'], et, st))
    return (ELEMENT_4U[et], abs(ev)) if et else (status[st], abs(sv))


def ammo_4u(w):
    """bowgun ammo string (spec format, GU slots 0..31) of a 4U record + [4U ammo indexes loadable without a GU slot]:
    a loadable ammo = its count; one that is not: (count) on slots 0..14, 0 on 15..31 (as GU zeroes those, S)"""
    out = ['0'] * 32
    for k, s in AMMO_SLOT.items():
        n = w['ammo'][k]
        out[s] = '%d' % n if (w['loadable'] >> k) & 1 else '(%d)' % n if s < 15 and n else '0'
    return ' '.join(out), [k for k in range(39) if k not in AMMO_SLOT and (w['loadable'] >> k) & 1]


def bottles_4u(mask):
    """GU mLoadEnableBottle[12] of a 4U bow coating mask (COATING_4U; [11] = 1)"""
    out = [0] * 11 + [1]
    for bit, slots in COATING_4U.items():
        for s in slots:
            if (mask >> bit) & 1: out[s] = 1
    return tuple(out)


def recipes_4u(exe, t4, ctype, ids4u, nn, first_upgrade=False):
    """[(4U item name, count)] per weapon: create recipe for the first, upgrade recipe for the others;
    first_upgrade: the first weapon has no 4U create recipe (checked) and is forged from the materials of its own 4U
    upgrade recipe (the parent weapon left out: the upgrade table lists only the materials)"""
    name = lambda pairs: [(t4['itemName'][it], c) for it, c in pairs if it]
    out = []
    hits = [a for a in range(CREATE_4U[0], CREATE_4U[1], 24) if struct.unpack_from('<HH', exe, a + 4 - EXE_BASE) ==
            (ctype, ids4u[0])]
    if first_upgrade:
        assert not hits and nn != 13, (ctype, ids4u[0], hits)
        v = struct.unpack_from('<8H', exe, u32(exe, UPGRADE_4U + 4 * (ctype - 7)) + 24 * ids4u[0] - EXE_BASE)
    else:
        assert len(hits) == 1, (ctype, ids4u[0], hits)
        v = struct.unpack_from('<8H', exe, hits[0] + 8 - EXE_BASE)
    out.append(name(zip(v[0::2], v[1::2])))
    for i in ids4u[1:]:
        if nn == 13:
            r = struct.unpack_from('<6H', exe, IG_UPGRADE_4U + 12 * i - EXE_BASE)
            assert r[0] in (i, 0), r                     # 0: a G weapon upgraded from an HR one
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
    free, alloc_, ctor, parse = calls[4][1], calls[6][1], calls[7][1], calls[8][1]
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
    return dict(load=load, alloc=alloc_, free=free, ctor=ctor, parse=parse, size=sz[0], site=load + 0x3c)


def build(spec):
    name, classes, status = spec['name'], spec['classes'], spec['status']
    kire_4u, subst = list(spec['kire_4u']), spec.get('substitutes', {})
    m_alloc = alloc.monster(name)
    prior = alloc.monsters()[:[m['name'] for m in alloc.monsters()].index(name)]
    R = RomFS(GU_ROMFS)
    exe = open(EXE, 'rb').read()
    res = gu_arc(R.read('/nativeNX/loc/arc/resident.arc'))
    bs = gu_arc(R.read('/nativeNX/arc/facility/blacksmith.arc'))
    lres = {lang: gu_arc(R.read('/nativeNX/%s/arc/resident_%s.arc' % (lang, lang))) for lang in LANGS}
    t4 = {lang: text4u(lang) for lang in LANGS}
    it_gu = gmd(lres['eng']['eng\\table\\itemData_eng'])
    our = gu_item_names(R, [spec['materials']])
    misses, tables, texts, hooks, summary, log = [], [], [], [], [], []

    def gu_item(nm):
        if nm in subst:
            log.append('recipe item %s (no GU item) -> %s' % (nm, subst[nm]))
            nm = subst[nm]
        ids = [i for i in range(len(it_gu) // 2) if it_gu[2 * i] == nm] or ([our[nm]] if nm in our else [])
        if len(ids) != 1: misses.append('%s (%d GU matches)' % (nm, len(ids)))
        return ids[0] if len(ids) == 1 else 0

    kd = res['table\\kireajiData']
    kn, _ = table(kd, KIRE)
    kn += alloc.offset(name, 'kireaji')
    assert m_alloc['append'].get('kireaji', 0) == len(kire_4u), 'allocations.toml kireaji != the spec\'s entries'
    def cls(name, version, hook):
        c = gu_class(name, version)
        hooks.append((hook, c['site'], name))
        return c

    for cs in classes:
        nn, ids4u, sid = cs['nn'], cs['ids4u'], cs['standin']
        short, txt, ptab, ctype = CLASS_INFO[nn]
        wkey = 'w%02d' % nn
        assert m_alloc['append']['weapons'].get(wkey) == len(ids4u), 'allocations.toml weapons.%s' % wkey
        off = alloc.offset(name, 'weapons', wkey)                  # rows of the earlier monsters' weapons
        lines = sum(1 for m in prior if m.get('append', {}).get('weapons', {}).get(wkey))   # one create row each
        w4 = [weapon_4u(exe, nn, ptab, i) for i in ids4u]
        rec4 = recipes_4u(exe, t4['eng'], ctype, ids4u, nn, cs.get('first_upgrade', False))
        for k, (r, plan) in enumerate(zip(rec4, cs.get('recipes', ()))):     # optional cross-check
            if dict(r) != plan or len(r) != len(plan):
                sys.exit('%s %d: 4U recipe %s != the spec\'s %s' % (short, ids4u[k], r, plan))
        bl, ll = base_layout(nn), level_layout(nn)
        bd, ld = res['table\\weapon%02dBaseData' % nn], res['table\\weapon%02dLevelData' % nn]
        n, base = table(bd, bl)
        ln, lv = table(ld, ll)
        ids = [n + off + k for k in range(len(ids4u))]
        assert ids[-1] <= 255 and base[sid]['mIndex'] == sid
        sort0 = max(b['mSortID'] for b in base) + off
        rows = [r for r in lv if r['mNo'] == sid]
        bout, lout = [], []
        for k, (i4, w) in enumerate(zip(ids4u, w4)):
            b = dict(base[sid])
            b.update(mIndex=ids[k], mModelID=w['model'], mSrqrNo=cs.get('srqr', w['model']), mSndMaterial=SND_MATERIAL, mMaxLv=1,
                     mMaxLvForLimit=0, mRare=w['rare'] - 1, mPrice=w['price'], mPriceChangeLv=0, mColorIndex=0,
                     mSortID=sort0 + 1 + k, mNamed=0, mSpecialSkill=0)
            for j in range(5):
                b['mDeriveLv[%d]' % j] = b['mDeriveID[%d]' % j] = 0
            if k + 1 < len(ids):
                b['mDeriveLv[0]'], b['mDeriveID[0]'] = 1, ids[k + 1]
            r = dict(rows[-1])
            r.update(mIndex=ln + off + len(lout), mNo=ids[k], mLevel=1, mAttack=w['raw'], mDefense=w['defense'],
                     mAffinity=w['aff'] & 0xff, mSlotCount=w['slots'])
            if nn in (4, 6):
                ammo, no_slot = ammo_4u(w)
                if i4 in cs.get('ammo', {}) and cs['ammo'][i4] != ammo:
                    sys.exit('%s %d: spec ammo %s != the 4U record\'s %s' % (short, i4, cs['ammo'][i4], ammo))
                for s, tok in enumerate(ammo.split()):
                    r['mLoadShellCount[%d]' % s] = int(tok.strip('()'))
                    r['mLoadEnableShell[%d]' % s] = int(tok != '0' and not tok.startswith('('))
                if no_slot:
                    log.append('%s %d %s: loadable 4U ammo without a GU slot (4U index: count) %s: left out' % (
                        short, ids[k], t4['eng'][txt + 'Name'][i4], ['%d: %d' % (a, w['ammo'][a]) for a in no_slot]))
                if w['bure'] != r['mBure']:
                    log.append('%s %d %s: 4U deviation %d, the stand-in\'s mBure %d kept' % (
                        short, ids[k], t4['eng'][txt + 'Name'][i4], w['bure'], r['mBure']))
                fire = 'mDownShot' if nn == 4 else 'mQuickShot'
                log.append('%s %d %s: kept from the stand-in (ID %d Lv%d): mRecoil %d, mReloadSpeed %d, mBure %d, '
                           '%s %s, special ammo (shell, have, count) %s, ammo slot 32 (%d, %d)' % (
                               short, ids[k], t4['eng'][txt + 'Name'][i4], sid, rows[-1]['mLevel'],
                               r['mRecoil'], r['mReloadSpeed'], r['mBure'], fire, [r['%s[%d]' % (fire, j)] for j in range(5)],
                               [(r['mUniqueShell[%d]' % j], r['mUniqueHaveShellCount[%d]' % j],
                                 r['mUniqueShellCount[%d]' % j]) for j in range(5)],
                               r['mLoadShellCount[32]'], r['mLoadEnableShell[32]']))
            elif nn == 10:
                bow = cs['bow']
                b['mElement'], val = elem_status(w, status)
                cshot = tuple(c + 1 for c in w['charges'])      # 4U Rapid n = n - 1, Spread n + 4, Pierce n + 9 -> GU + 1 (S)
                assert i4 not in bow.get('cshot', {}) or cshot == bow['cshot'][i4], (i4, cshot)
                assert bow.get('tame', w['tame']) == w['tame'], (i4, w['tame'])
                r.update(mElementValue=val, mTameDankai=w['tame'])
                if bow.get('kyoku') is None:
                    log.append('%s %d %s: arc shot not in the 4U record: the stand-in\'s mKyoku %d kept' % (
                        short, ids[k], t4['eng'][txt + 'Name'][i4], r['mKyoku']))
                else:
                    r['mKyoku'] = bow['kyoku']
                bottles = bow.get('bottles') or bottles_4u(w['coatings'])
                if w['coatings'] >> 9:
                    log.append('%s %d %s: 4U coating mask %#x: bits from 9 unknown, ignored' % (
                        short, ids[k], t4['eng'][txt + 'Name'][i4], w['coatings']))
                for j in range(4): r['mCShotKind[%d]' % j] = cshot[j]
                for j in range(12): r['mLoadEnableBottle[%d]' % j] = bottles[j]
            else:
                elem, val = elem_status(w, status)               # 4U hidden (negative) -> visible
                r.update(mKireType=kn + kire_4u.index(w['sharp']), mKireLevel=2 * w['kire'])
                if nn == 11:
                    elem2, val2 = db_second_4u(exe, w, status)
                    b.update(mElement1=elem, mElement2=elem2)
                    r.update(mElementValue1=val, mElementValue2=val2)
                else:
                    b['mElement'] = elem
                    r['mElementValue'] = val
                if nn in (8, 14):
                    assert w['extra'] in (0, 1), w               # SA Power / Element phial, CB Impact / Element
                    b['mBinType'], r['mBinElementValue'] = w['extra'], 0     # (types 2.. carry a value: not read)
                elif nn == 9:                                    # 4U (level - 1) * 3 + type (Normal, Long, Wide)
                    b['mShootType'], r['mShootLevel'] = w['extra'] % 3, w['extra'] // 3
                elif nn == 12 and 'hh' in cs:
                    assert w['extra'] == cs['hh'][0], w
                    r['mFueMusicType'] = cs['hh'][1]
                elif nn == 12:
                    fue = res['table\\fueMusicData']
                    assert exe[NOTES_4U - EXE_BASE:][:len(fue) - 8] == fue[8:] and w['extra'] < (len(fue) - 8) // 3
                    r['mFueMusicType'] = w['extra']
                elif nn == 13:
                    assert w['extra'] == 0, w                    # Cutting
                    b['mInsectType'] = cs['insect']
            bout.append(bl.enc(b))
            lout.append(ll.enc(r))
            summary.append((short, ids[k], t4['eng'][txt + 'Name'][i4], b, r, rec4[k], k))
        tables.append(('table\\weapon%02dBaseData' % nn, cls('rWeapon%02dBaseData' % nn, bd[:4], 'gear_w%02d_base' % nn),
                       bl.size, n + off, bout))
        tables.append(('table\\weapon%02dLevelData' % nn, cls('rWeapon%02dLevelData' % nn, ld[:4], 'gear_w%02d_level' % nn),
                       ll.size, ln + off, lout))
        # name index (one per language arc, the same in all) and names (6 strings per weapon)
        mi = {lang: lres[lang]['%s\\table\\weapon%02dMsgData' % (lang, nn)] for lang in LANGS}
        mn, mrecs = table(mi['eng'], MSGIDX)
        assert mn == n and all(table(mi[lang], MSGIDX)[0] == n for lang in LANGS) and mrecs[sid]['mIndex'] == sid
        tables.append(('table\\weapon%02dMsgData' % nn, cls('rWeapon%02dMsgData' % nn, mi['eng'][:4], 'gear_w%02d_msg' % nn),
                       MSGIDX.size, n + off, [MSGIDX.enc(dict(mrecs[sid], mIndex=i)) for i in ids]))
        strs = []
        for lang in LANGS:
            g = lres[lang]['%s\\table\\weapon%02dMsgData_%s' % (lang, nn, lang)]
            ln_ = struct.unpack_from('<I', g, 0x24)[0]
            if g[0x28:0x28 + ln_] != b'weapon%02dMsgData' % nn or len(gmd(g)) != 6 * n:
                sys.exit('weapon%02dMsgData_%s: name %r, %d strings != 6 x %d' % (nn, lang, g[0x28:0x28 + ln_], len(gmd(g)), n))
            strs.append(sum([[t4[lang][txt + 'Name'][i], t4[lang][txt + 'Exp'][exp_4u(exe, EXP_4U[nn], i)]] * 3
                             for i in ids4u], []))
        texts.append(('weapon%02dMsgData' % nn, 6 * (n + off), strs))
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
        tables.append(('table\\weaponCreateW%02d' % nn, None, CREATE.size, cn + lines, [CREATE.enc(c)]))
        tables.append(('table\\weaponProcessW%02d' % nn, None, PROCESS.size, pn + off, pout))
    if misses:
        sys.exit('item names not in GU itemData_eng: %s' % ', '.join(sorted(set(misses))))
    # the create / process classes (one each, 14 files) and kireajiData
    cc = cls('rWeaponCreateData', bs['table\\weaponCreateW00'][:4], 'gear_w_create')
    pc = cls('rWeaponProcessData', bs['table\\weaponProcessW00'][:4], 'gear_w_process')
    for k, t in enumerate(tables):
        if t[1] is None:
            tables[k] = (t[0], cc if 'Create' in t[0] else pc) + t[2:]
    kire = [KIRE.dec(exe[KIRE_4U + 14 * i - EXE_BASE:][:14]) for i in kire_4u]
    assert all(k['mSlash[6]'] <= 450 for k in kire)
    tables.append(('table\\kireajiData', cls('rKireajiData', kd[:4], 'gear_kireaji'), KIRE.size, kn,
                   [KIRE.enc(k) for k in kire]))
    for lang in LANGS:
        for nn in [c['nn'] for c in classes]:                    # every language: the same versions as eng
            assert lres[lang]['%s\\table\\weapon%02dMsgData' % (lang, nn)][:4] == lres['eng']['eng\\table\\weapon%02dMsgData' % nn][:4]
    return tables, texts, hooks, summary, log, kire


def sections(tables, texts, hooks, pwl_fix):
    """TBLA (a resource path is matched as a suffix of the path at res+0x8, so the per-language
    "eng\\table\\weapon00MsgData" is matched by "table\\weapon00MsgData"), TXTA, PWLF; and the hook lines"""
    tbl = []
    for path, c, rb, expect, recs in tables:
        flags = portdata.TBL_KIREAJI if path.endswith('kireajiData') else \
            portdata.TBL_NEEDS_KIREAJI if path.endswith('LevelData') else 0
        tbl.append(dict(path=path, cls=(c['alloc'], c['free'], c['ctor'], c['parse'], c['size']), rec_bytes=rb,
                        base=expect, records=b''.join(recs), flags=flags))
    secs = [portdata.tbla(tbl), portdata.txta([(n, e, [[gu_str(s) for s in ss] for ss in strs]) for n, e, strs in texts])]
    if pwl_fix:
        pwl = portdata.Section('PWLF')
        pwl.u32(len(pwl_fix))
        for path, model, frm, to in pwl_fix:
            pwl.str(path)
            pwl.raw(struct.pack('<HBB', model, frm, to))
        secs.append(pwl)
    return secs, ''.join('%s 0x%X\n' % (h, s) for h, s, _ in hooks)


def write_hooks(hooks_txt):
    """module/gear_hooks.txt = the hooks already listed (another monster's tool) + this tool's new ones; a hook name
    listed with another site is an error"""
    old = open(OUT_HOOKS).read().splitlines() if os.path.exists(OUT_HOOKS) else []
    have = dict(l.split() for l in old if l.strip())
    lines = list(old)
    for l in hooks_txt.splitlines():
        h, s = l.split()
        assert have.get(h, s) == s, ('hook site differs', h, have[h], s)
        if h not in have: lines.append(l); have[h] = s
    open(OUT_HOOKS, 'w').write(''.join(l + '\n' for l in lines))
    return OUT_HOOKS


def show(summary, log, kire, tables, hooks, status):
    for short, i, name, b, r, mats, k in summary:
        elem = r.get('mElementValue', r.get('mElementValue1', 0))
        el = b.get('mElement', b.get('mElement1'))
        sharp = 'kire %d/%d' % (r['mKireType'], r['mKireLevel']) if 'mKireType' in r else '-'
        print('%-6s %3d %-22s raw %d aff %d status %s slots %d %s model %d/%d price %d derive %s  %s %s' % (
            short, i, name, r['mAttack'], struct.unpack('b', bytes([r['mAffinity']]))[0],
            '%d:%d' % (el, elem * 10) if el in status.values() else '-', r['mSlotCount'], sharp,
            b['mModelID'], b['mSrqrNo'], b['mPrice'], '%d@Lv%d' % (b['mDeriveID[0]'], b['mDeriveLv[0]']) if b['mDeriveID[0]'] else '-',
            'create' if k == 0 else 'upgrade', ', '.join('%s %d' % m for m in mats)))
    print('kireaji appended:', [tuple(k.values()) for k in kire])
    for l in log: print('log:', l)
    for path, c, rb, expect, recs in tables:
        print('table %-26s expect %4d n %d (rec %d B, mem %d B)' % (path, expect, len(recs), rb, c['size']))
    for h, s, name in hooks:
        print('hook %-16s 0x%X  %s' % (h, s, name))
