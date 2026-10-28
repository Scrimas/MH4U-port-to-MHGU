"""build_em057_01_quest.py : Stygian Zinogre's 4U quests for MHGU (notes/quests.md), appended to GU's quest list by the
core (module/quest.c quest_group_append; allocations.toml quests + quest_append). Placement (user 2026-10-28): 4U
Hub HR6 -> GU Hub HR7, caravan -> Village 10*, Hub G2 / G3 and the event -> GU Hub G4.

  build_em057_01_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/stygian_zinogre/romfs), per quest: the quest arc, loose questData / questLink and the
5 GMDs (tools/quest4u.py assemble / write).

Sources (C unless marked):
  GU template  per quest (QUESTS): a GU quest at the placement (stars / class bytes, board, start area, flags, +0x1A,
               money, supply box, questPlus, reward slots 3 / 4, GMD unk word) on the same stage with the same kind
               (single hunt). Its money is kept: the rank moved (Tigerstripe's rule; 4U's money is lower, S).
  Stat rows    (user 2026-10-28, notes/quests.md 3b) r = the 4U Stygian quest's em_nando_tbl value over the 4U Zinogre
               quest's at the comparable tier (HP column 0, attack column 1), target = GU's Zinogre quest at the
               placement x r, the nearest GU em_nando_tbl row never below that quest's own row; the other row is
               the GU quest's. GU's HR7 Hub single Zinogre (q10735) is a Hyper quest (aura byte +3 = 1): its rows
               are the base, our boss has no aura (Stygian has no Hyper state).
  Boss record  the stand-in Zinogre (allocations.toml standin_id, swapped to 0x139 at spawn by module/main.c), rows
               above, aura 0, size % from 4U, restore / byte 8 / size table / stamina = the GU Zinogre quest's.
  4U quest     text (5 languages), minutes, spawn (area, point, rotation), reward rows A / B / subquest
               (tools/items_em057_01.py materials), subquest kind.
  Subquest     {u8 type 8 = wound / sever, u16 target em, u16 code}: GU Zinogre break groups read from GU's own
               subquest texts (q905 1 = head, q10735 12 = head & back, q11478 13 = head & front legs, q10609 7 =
               tail sever).
  Spawn        the template's boss setEmMain record with 4U's area and floats (setEmMain floats = rotation, x, y, z;
               4U spawn floats = x, y, z, rotation, build_dalamadur_quest.py). GU's Frozen Seaway / Volcanic Hollow
               are 4U's geometry (S, as Tigerstripe's Dunes). Small monsters: the template's sets (GU's fauna of
               that stage; 4U's own lists are not ported, S).

Quests built (QUESTS; notes/quests.md 5): m10603 m10608 m10612 m10616 m10925 m60205 (extdata) m00907 m01029, and the
three Heaven's Mount quests m10607 m10930 m11010 on the stage alias (GU stage 24 = 4U m05 geometry, folder m30:
tools/build_heavens_mount.py, notes/heavens-mount.md). Opt-in keys for those (the other quests' outputs are
unchanged): waves (bosses from every 4U spawn list, in list order; GU spawns them in record order, at most two at
once, S), hunt_all (GU objective type 3 "hunt all large monsters", rule 0, as GU's q10742 / q11488), tpl_stage (the
template sits on another stage: its stage byte is replaced), ('slay', 4U em, count) subquests (GU type 1 small-monster
hunt, ZAKO_GU), zako (the small monsters come from the 4U quest's own per-area lists, ZAKO_GU species only, instead
of the template's GU-terrain sets).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, extdata4u, items_em057_01, quest4u   # noqa: E402
from items4u import EXE, EXE_BASE   # noqa: E402
from quest4u import (arc_files, text4u, ref, LANGS, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('stygian_zinogre')
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x139; Zinogre 0x39, swapped at spawn
EM_4U, ZINOGRE_GU = 49, 0x39
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {4: 14, 15: 12, 11: 9,  # 4U Frozen Seaway / Volcanic Hollow / Arena -> GU stage (notes/quests.md 2)
            5: 24}                  # Heaven's Mount -> the alias of GU stage 24 (allocations.toml stage_alias)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: Stygian's cell (module/icons.c; 4U +0xE8 = 50, its art)
ALT_ID = 0x439       # allocations.toml standin_alt: Thunderlord Zinogre (GU em057_04, the same class) names Stygian in
                     # the quests where a real Zinogre fights next to him (module/main.c standin_swap)
# the other 4U bosses of his quests -> GU ID (C: 4U em numbers of the spawn lists; GU IDs from GU's own quests)
PARTNER_GU = {48: 0x39,     # Zinogre
              12: 0x20,     # Brute Tigrex: not in GU -> Tigrex (a DEVIATION, notes/quests.md 5)
              44: 0x3f,     # Brachydios
              88: 0x4d,     # Seregios
              9: 0x9,       # Gypceros
              4: 0x2,       # Azure Rathalos: not in GU -> Rathalos (a DEVIATION, notes/heavens-mount.md)
              26: 0x45,     # Seltas Queen
              25: 0x4c,     # Seltas
              97: 0x47}     # Gore Magala
# 4U small monsters -> GU ID (C: GU quests naming them as objectives, q10230 "Ioprey Hunting" 0x100b); the others of
# the 4U lists (Kelbi, Conga, Remobra, Felyne, Melynx, Bnahabra) are left out (no GU ID read: a DEVIATION)
ZAKO_GU = {60: 0x100b}      # Ioprey
# GU break groups (subquest code digits, C from GU's subquest texts): Zinogre 1 head, 2 back, 3 front legs, 7 tail;
# Tigrex 7 tail (q914 / q10602). 4U's own codes differ (m10603 2 head, m10616 3 front leg, m00907 4 back, 7 tail).
# Quests (k = index in allocations.toml quests; notes/quests.md 3b / 3c):
#   num   4U quest           tpl   GU template (same rank, stage and kind; two-hunt ones are made two-hunt here)
#   zin   (4U quest, boss)   the 4U Zinogre stat block the ratio divides by (None: r = 1, notes/quests.md 3b)
#   base  (GU quest, em)     the GU boss record the ratio multiplies (stat base); partners take the base quest's own
#                            record of their GU ID when it has one, else Stygian's rows (4U gives them his rows)
#   sub   ('break', em, code) / ('deliver', 4U item, count)
#   alt   the quest names Stygian by ALT_ID (a real Zinogre is in it)
QUESTS = [
    dict(k=0, num=10603, tpl=10724, zin=(10520, 0), base=(10735, 0x39), sub=('break', 0x39, 1)),
    dict(k=2, num=10608, tpl=10774, zin=(10612, 0), base=(10708, 0x39), sub=('break', 0x20, 7)),
    dict(k=3, num=10612, tpl=10774, zin=(10612, 0), base=(10708, 0x39), sub=('break', 0x39, 7), alt=True),
    dict(k=4, num=10616, tpl=10706, zin=(10528, 0), base=(10735, 0x39), sub=('break', 0x39, 3)),
    dict(k=5, num=10925, tpl=11463, zin=(10915, None), base=(11488, 0x39), sub=('break', 0x39, 7)),
    dict(k=9, num=907, tpl=1003, zin=None, base=(1003, 0x3f), sub=('break', 0x39, 2)),
    dict(k=10, num=1029, tpl=1021, zin=(903, None), base=(1049, 0x39), sub=('deliver', 826, 1)),
    dict(k=8, num=60205, tpl=11468, zin=(10915, None), base=(11488, 0x39)),     # DLC event (extdata), no subquest
    # Heaven's Mount (alias of GU stage 24, notes/heavens-mount.md). m10607: 4U "hunt all large monsters" over three
    # waves (Stygian a6; Azure Rathalos a8; Seltas Queen a6 + Seltas a3): no HR7 Hub quest on stage 24 (C), so the
    # template is GU's HR7 Hub hunt-all with Zinogre (q10742, Misty Peaks night 104), re-staged
    dict(k=1, num=10607, tpl=10742, tpl_stage=104, zin=(10612, 0), base=(10720, 0x39), sub=('deliver', 826, 1),
         waves=True, hunt_all=True, zako=True),
    dict(k=6, num=10930, tpl=11472, zin=(10903, 0), base=(11478, 0x39), sub=('slay', 60, 8), zako=True),
    # m11010: 4U head of Gore Magala (code 2) -> GU group 1 "feelers" (GU's head break, C: q602 text)
    dict(k=7, num=11010, tpl=11473, zin=(11016, None), base=(11488, 0x39), sub=('break', 0x47, 1), waves=True,
         zako=True),
]
_SETS = {}           # setEmMain name -> data over every quest built: one content per name, as GU's (C: 488 names)


def quest_4u(num):
    """a 4U quest by number: the ROM's (loc/data/quest00.arc / quest01.arc), else the user's DLC extdata (event
    quests, tools/extdata4u.py)"""
    for arc in ('quest00.arc', 'quest01.arc'):
        f = arc_files(open(os.path.join(Q4U_DIR, arc), 'rb').read())
        if 'loc\\quest\\m%05d' % num in f:
            q = f['loc\\quest\\m%05d' % num][1]
            assert q[4:8] == b'v005' and struct.unpack_from('<H', q, 0xC0)[0] == num, num
            return q
    q = extdata4u.quest(num)
    assert q[4:8] == b'v005' and struct.unpack_from('<H', q, 0xC0)[0] == num, num
    return q


def spawns_4u(q, waves=False):
    """4U boss spawn records of the first list, 0x28 B each closed by em 0xffffffff: [(em, area, (x, y, z, rot), +0xF)];
    waves: every list of the table at +0x28 (u32 list pointers, up to 4, 0 = none; C: m10607's three waves, m11010's
    two), in list order"""
    tbl = struct.unpack_from('<I', q, 0x28)[0]
    lists = [struct.unpack_from('<I', q, tbl + 4 * i)[0] for i in range(4 if waves else 1)]
    out = []
    for rec in lists:
        if not rec or rec + 4 > len(q): continue
        while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
            out.append((struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10),
                        q[rec + 0xF]))
            rec += 0x28
    return out


def zako_4u(q):
    """4U small-monster lists of the first set (+0x2C -> set pointers -> per-area list pointers until 0; records 0x28 B
    {u32 em, u32 n, u8 link, u8 area, .., f32 x, y, z @0x10, u16 angle @0x20} closed by em 0xffffffff, C: m10930's
    Kelbi / Conga / Remobra / Ioprey / Felyne / Melynx / Bnahabra lists of areas 1..8):
    [(em, n, link, area, (x, y, z), angle)]"""
    sets = struct.unpack_from('<I', q, 0x2C)[0]
    tbl = struct.unpack_from('<I', q, sets)[0]
    out, i = [], 0
    while tbl and struct.unpack_from('<I', q, tbl + 4 * i)[0]:
        rec = struct.unpack_from('<I', q, tbl + 4 * i)[0]
        while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
            em, n = struct.unpack_from('<II', q, rec)
            out.append((em, n, q[rec + 8], q[rec + 9], struct.unpack_from('<3f', q, rec + 0x10),
                        struct.unpack_from('<H', q, rec + 0x20)[0]))
            rec += 0x28
        i += 1
    return out


def esl_gu(recs):
    """GU emSetList (C: GU's z_m07d_033 / z_m24d_024 layouts): 'esl\\0', u32 2, 14 u32 block offsets, blocks 'ESD\\0' u32
    0x20151214, u16 n, n x 0x24 B {u16 em, u8 area, 0xcd, u8 link (0xff = none), u8 block number, 1, 0, 0, 0, 0xcd, 0xcd,
    f32 x, y, z, u32 0, u16 angle, u16 0, u32 0}. One block per 4U area list; a 4U record = one GU record (G: 4U's
    count n, 3..5 for Ioprey, has no GU field: GU respawns small monsters itself, S)"""
    blocks = {}
    for em, n, link, area, pos, ang in recs:
        blocks.setdefault(area, []).append((em, link, pos, ang))
    assert len(blocks) <= 14
    head, body = bytearray(b'esl\0' + struct.pack('<I', 2) + bytes(56)), bytearray()
    for b, area in enumerate(sorted(blocks)):
        struct.pack_into('<I', head, 8 + 4 * b, 64 + len(body))
        body += b'ESD\0' + struct.pack('<IH', 0x20151214, len(blocks[area]))
        for em, link, pos, ang in blocks[area]:
            body += struct.pack('<HBBBBBBBBBB3fIHHI', em, area, 0xcd, b + 1 if link != 255 else 0xff, b + 1, 1, 0, 0,
                                0, 0xcd, 0xcd, *pos, 0, ang, 0, 0)
    return bytes(head + body)


def quest_data(R, qid):
    return arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % qid))['loc\\quest\\questData\\questData_%07d' % qid][1]


def boss_record(qd, em):
    """the questData boss record (+0x64, 13 B each) of em"""
    recs = [struct.unpack_from('<HBBBBBBBHBB', qd, 0x64 + 13 * k) for k in range(5)]
    return next(r for r in recs if r[0] == em)


def stats_block(q, i):
    """4U boss stat block i (+0x34 + 8 i, one per first-list spawn, in spawn order: S, m10612's Zinogre / Stygian
    rows match notes/quests.md 3b): (size %, HP row, attack row, other row)"""
    o = STATS_4U + 8 * i
    return (struct.unpack_from('<H', q, o)[0],) + tuple(q[o + 3:o + 6])


def stat_rows(R, exe, s, z, b):
    """(HP, attack, other) rows and the trace (r HP, r attack, target HP, target attack) per notes/quests.md 3b:
    s / z = the 4U Stygian / Zinogre stat blocks (None = r 1.0), b = the GU base boss record"""
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    rows = [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]
    r4 = lambda row: struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
    r_hp, r_atk = (r4(s[1])[0] / r4(z[1])[0], r4(s[2])[1] / r4(z[2])[1]) if z else (1.0, 1.0)

    def pick(col, base_row, r):
        base = rows[base_row][col]
        return min((abs(rows[k][col] - base * r), k) for k in range(len(rows)) if rows[k][col] >= base)[1], base * r
    hp, t_hp = pick(0, b[4], r_hp)
    atk, t_atk = pick(1, b[5], r_atk)
    return (hp, atk, b[6]), (r_hp, r_atk, t_hp, t_atk, rows[hp][0], rows[atk][1])


def objectives_4u(q):
    """4U main objectives (+0xCB count, records {u32 type, u16 target, u16 count} at +0xCC / +0xD4; type 1 = hunt,
    0x81 = capture: m10616 "Capture a Stygian Zinogre") and the subquest record at +0xDC (type 0x204 = wound / sever
    {em, 4U part code}, 2 = deliver {4U item, count}) (C: read on his 11 quests against their texts)"""
    n = q[0xCB]
    objs = [struct.unpack_from('<IHH', q, 0xCC + 8 * i) for i in range(n)]
    return objs, struct.unpack_from('<IHH', q, 0xDC)


def gu_id(em4, spec):
    """GU ID a 4U boss is named by in the quest's boss records (Stygian: the stand-in)"""
    if em4 == EM_4U: return ALT_ID if spec.get('alt') else BOSS_ID
    return PARTNER_GU[em4]


ICON_QUEST = {0x39: 10735, 0x20: 10724, 0x3f: 1003, 0x4d: 10706, 0x9: 514,   # GU quests with it first (C)
              0x2: 917, 0x45: 10605, 0x4c: 703, 0x47: 10604}


def partner_icon(R, gid):
    qd = quest_data(R, ICON_QUEST[gid])
    assert struct.unpack_from('<H', qd, 0x64)[0] == gid and qd[0xD6], (gid, 'icon quest')
    return qd[0xD6]


def set_name(stage, em4, k):
    """setEmMain names, one content per name as GU's (asserted over the quests built): Stygian's carries 60 + k as its
    variant (quest k 0 keeps its first name 'b_m14em057_01'), a partner's 80 + k (no GU quest uses those names)"""
    if em4 == EM_4U: return 'b_m%02dem057_%02d' % (stage, 1 if k == 0 else 60 + k)
    return 'b_m%02dem%03d_%02d' % (stage, PARTNER_GU[em4] & 0xff, 80 + k)


def build(R, exe, gu_item, out, spec, hp_table=None):
    k, num, tpl_id = spec['k'], spec['num'], spec['tpl']
    qid = ALLOC['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    q4 = quest_4u(num)
    sp = spawns_4u(q4, spec.get('waves', False))
    ems = [s[0] for s in sp]
    assert ems.count(EM_4U) == 1 and all(e == EM_4U or e in PARTNER_GU for e in ems), (m4, ems)
    me = ems.index(EM_4U)
    # 4U spawn byte +0xF (C, survey of the 4U ROM quests): 9 on the Apex monsters, 1 / 2 on "Advanced:" quests
    # (m10830's frenzied Tigerstripe = 1, m10522 "Frenzied Foe" = 2): the frenzy virus states, which GU lacks (the
    # user dropped 4U's frenzy for Tigerstripe, 2026-10-20): left out, a DEVIATION, logged per quest.
    frenzy = [(e, s[3]) for e, s in zip(ems, sp) if s[3]]
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    base_qd = quest_data(R, spec['base'][0])
    objs, sub4 = objectives_4u(q4)
    assert 1 <= len(objs) <= 2 and all(t in (1, 0x81) for t, _, n in objs), (m4, objs)
    if spec.get('hunt_all'):    # 4U "Hunt all large monsters" names the last wave's bosses (m10607: Seltas Queen, Seltas)
        assert set(e for _, e, _ in objs) <= set(ems) and len(ems) > len(objs), (m4, objs, ems)
    else:
        assert sorted(e for _, e, _ in objs) == sorted(ems), (m4, 'objectives are not the spawned bosses', objs, ems)

    # --- questData: the template's (rank, board, start area, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == 329 and qd[0x14] == spec.get('tpl_stage', stage) and qd[0x1F] in (1, 2, 3), \
        (tpl_id, 'not a hunt / capture on the stage')
    qd[0x14] = stage
    assert (qd[0x12], qd[0x13]) == (base_qd[0x12], base_qd[0x13]), ('template and stat base differ in rank', tpl_id)
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # minutes (4U)
    # objectives: 4U's, targets = the real IDs (as Tigerstripe's); capture = GU type 2 (q918 "Taming of the Zinogre");
    # two targets = clear rule 1 (+0x1D: objectives 0 AND 1, Tigerstripe's trace; GU's two-hunt quests, e.g. q10774)
    qd[0x1D] = len(objs) - 1
    qd[0x1F:0x29] = bytes(10)
    if spec.get('hunt_all'):    # GU type 3 = all large monsters, target / count 0, rule 0 (q10742 / q11488, C)
        qd[0x1D] = 0
        qd[0x1F] = 3
    else:
        for i, (t, e, n) in enumerate(objs):
            target = EM_ID if e == EM_4U else PARTNER_GU[e]
            struct.pack_into('<BHH', qd, 0x1F + 5 * i, 2 if t == 0x81 else 1, target, n)
    sub = spec.get('sub')
    if sub and sub[0] == 'break':          # GU code of the 4U part, on the 4U subquest's monster (real ID)
        assert sub4[0] == 0x204, (m4, 'the 4U subquest is not a wound / sever', sub4)
        target = EM_ID if sub4[1] == EM_4U else PARTNER_GU[sub4[1]]
        assert target == (EM_ID if sub[1] == 0x39 and sub4[1] == EM_4U else sub[1]), (m4, sub, sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, target, sub[2])
    elif sub and sub[0] == 'deliver':
        assert sub4 == (2, sub[1], sub[2]), (m4, 'the 4U subquest is not this delivery', sub4)
        item = gu_item(sub[1])
        assert item is not None, (m4, '4U item %d has no GU item' % sub[1])
        struct.pack_into('<BHH', qd, 0x29, 5, item, sub[2])
    elif sub and sub[0] == 'slay':         # GU sub type 1 = hunt N small monsters (q705 {1, 0x100f, 8}, C)
        assert sub4 == (0x101, sub[1], sub[2]), (m4, 'the 4U subquest is not this small-monster hunt', sub4)
        struct.pack_into('<BHH', qd, 0x29, 1, ZAKO_GU[sub[1]], sub[2])
    else:
        qd[0x29:0x2E] = bytes(5)

    # boss records in 4U's spawn order: Stygian = the stand-in with the computed rows; partners = the base quest's
    # record of their GU ID if it has one, else Stygian's rows (4U gives them his: m10608 / m10925 / m01029)
    b = boss_record(base_qd, spec['base'][1])
    s4 = stats_block(q4, me)
    z4 = None
    if spec.get('zin'):
        zq = quest_4u(spec['zin'][0])
        zi = spec['zin'][1] if spec['zin'][1] is not None else \
            [s[0] for s in spawns_4u(zq, spec.get('waves', False))].index(48)
        z4 = stats_block(zq, zi)
    (hp, atk, other), trace = stat_rows(R, exe, s4, z4, b)
    if hp_table is not None: hp = hp_table
    base_ids = [struct.unpack_from('<H', base_qd, 0x64 + 13 * i)[0] for i in range(5)]
    recs, info = b'', []
    for i, e in enumerate(ems):
        size = stats_block(q4, i)[0]
        gid = gu_id(e, spec)
        if e == EM_4U:
            r = (hp, atk, other, b)
        elif PARTNER_GU[e] in base_ids:
            pb = boss_record(base_qd, PARTNER_GU[e])
            r = (pb[4], pb[5], pb[6], pb)
        else:
            r = (hp, atk, other, b)
        recs += struct.pack('<HBBBBBBBHBB', gid, 0, 0, r[3][3], r[0], r[1], r[2], r[3][7], size, r[3][9], r[3][10])
        info.append('%#x rows %d/%d/%d size %d' % (gid, r[0], r[1], r[2], size))
    qd[0x64:0x64 + 65] = recs + bytes(65 - len(recs))
    # board icons in 4U's order (4U +0xE8 lists Stygian 50 first in every quest of his): his cell, a partner's =
    # the first icon of a GU quest whose first boss it is (ICON_QUEST)
    icons = [ICON if e == EM_4U else partner_icon(R, PARTNER_GU[e]) for e in ems]
    qd[0xD6:0xDB] = bytes(icons + [0] * (5 - len(icons)))
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))

    # --- questLink + resources: one setEmMain per boss (the template's first record with 4U's area and floats);
    # the template's small-monster sets
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    se0 = tpl['quest\\boss\\setEmMain\\' + tnames[0]][1]
    res, setnames = [], []
    for i, e in enumerate(ems):
        se = bytearray(se0)
        x, y, z, rot = sp[i][2]
        struct.pack_into('<I4f', se, 0x0C, sp[i][1], rot, x, y, z)
        n = set_name(stage, e, k)
        assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
        res.append(('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)))
        setnames.append(n)
    res.append(('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]))
    esl = tnames[5:8]
    if spec.get('zako'):     # 4U's own small-monster lists (the template's sets sit on GU terrain), ZAKO_GU species
        zak = [(ZAKO_GU[r[0]],) + r[1:] for r in zako_4u(q4) if r[0] in ZAKO_GU]
        esl = ['z_m%02dd_%03d' % (stage, 900 + k) if zak else 'z_m00d_000', 'z_m00d_000', 'z_m00d_000']
        if zak:
            res.append(('quest\\zako\\emSetList\\' + esl[0], T_ESL, esl_gu(zak)))
        res.append(('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1]))
        info_zako = '; small monsters (4U lists, %d of %d records kept: %s)' % (
            len(zak), len(zako_4u(q4)), sorted({(hex(r[0]), r[3]) for r in zak}))
    else:
        info_zako = ''
        for n in sorted(set(tnames[5:8])):
            res.append(('quest\\zako\\emSetList\\' + n, T_ESL, tpl['quest\\zako\\emSetList\\' + n][1]))
    # rewards: rows A / B from 4U, slots 3 / 4 the template's, the subquest row from 4U (row A's file when equal)
    ptr = lambda o: struct.unpack_from('<I', q4, o)[0]
    rows = {'rem_%sa' % m4: REWARD_ROWS_4U[0], 'rem_%sb' % m4: REWARD_ROWS_4U[1]}
    sub_name = 'rem_%sa' % m4
    if sub and ptr(SUB_ROW_4U) and ptr(SUB_ROW_4U) != ptr(REWARD_ROWS_4U[0]):
        sub_name = 'rem_%ss' % m4
        rows[sub_name] = SUB_ROW_4U
    rems = {name: quest4u.rem_4u(q4, row, gu_item) for name, row in rows.items()}
    assert not set(rems) & set(tnames), 'reward row names taken by the template'
    rem = ['rem_%sa' % m4, 'rem_%sb' % m4, tnames[10], tnames[11], sub_name]
    for r in sorted(set(rem)):
        res.append(('quest\\rem\\' + r, T_REM, rems[r] if r in rems else tpl['quest\\rem\\' + r][1]))
    res.append(('quest\\supp\\supp_' + sid, T_SUPP, tpl['quest\\supp\\supp_%07d' % tpl_id][1]))
    plus = tnames[14]
    res.append(('quest\\plus\\questPlus_' + plus, T_PLUS, tpl['quest\\plus\\questPlus_' + plus][1]))
    link = tlink[:8] + b''.join(ref(T_SET, n) for n in setnames) + ref(T_SET, 'b_m00em000_00') * (5 - len(setnames))
    link += b''.join(ref(T_ESL, n) for n in esl)
    link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    qd = bytes(qd)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, objectives %s, sub %s; bosses %s (Stygian r HP '
          '%.3f atk %.3f, target %.2f / %.2f -> %.2f / %.2f); spawns %s%s; "%s"' % (
              qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], qd[0x1F:0x29].hex(' '), qd[0x29:0x2E].hex(' '),
              info, *trace, [(s[1], tuple(round(v) for v in s[2])) for s in sp],
              ('; 4U frenzy state %s DROPPED (deviation)' % frenzy if frenzy else '') + info_zako, t4['eng'][0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help='boss vital (HP) table byte instead of the computed one (shorter '
                                                 'tests)')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    ap.add_argument('--only', type=int, help='build only this GU quest ID')
    a = ap.parse_args()
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    gu_item = items_em057_01.materials(R, exe).gu_item
    for spec in QUESTS:
        if a.only in (None, ALLOC['quests'][spec['k']]):
            build(R, exe, gu_item, a.out, spec, a.hp_table)


if __name__ == '__main__':
    main()
