"""build_em005_01_quest.py : Black Gravios' 4U quests for MHGU, appended to GU's quest list by the core
(module/quest.c quest_group_append; allocations.toml quests + quest_append). Placement as Stygian Zinogre's (user
2026-10-28 there): 4U Hub HR6 -> GU Hub HR7, 4U Hub G2 -> GU Hub G4. Built (user 2026-10-31 / 11-01): 4U m10611
and m10923.

  build_em005_01_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/black_gravios/romfs), per quest: the quest arc, loose questData / questLink and the
5 GMDs (tools/quest4u.py assemble / write).

Sources (C unless marked), the rules of monsters/stygian_zinogre/tools/build_em057_01_quest.py:
  GU template  per quest (QUESTS): a GU quest at the placement (stars / class bytes, board, start area, flags, +0x1A,
               money, questPlus, GMD unk word) on the same stage with the same kind.
               m10611 (two hunts, Volcanic Hollow): q10707, GU's HR7 Hub two-hunt on stage 12.
  Stat rows    r = the 4U Black Gravios row's em_nando_tbl value over the 4U Gravios row of the same quest (HP column
               0, attack column 1; m10611 has both), target = GU's HR7 Hub Gravios (q10767) x r, the nearest GU row
               never below that quest's own; the Gravios next to him takes q10767's own record (Stygian's m10612
               rule). G: GU's two-hunt quests use lower rows than its single hunts (q10707: 30 / 65); to review in a test.
  Boss record  Black Gravios = the alternative stand-in Basarios (allocations.toml standin_alt: the quest has a real
               Gravios, which keeps its ID), swapped to 0x105 at spawn by module/main.c; aura 0.
  4U quest     text (5 languages), minutes, objectives, spawns (area, point, rotation), reward rows A / B / subquest,
               subquest kind.
  Subquest     {u8 type 8 = wound / sever, u16 target em, u16 code}: 4U 0x204 {em 41, part 7} = sever the tail -> GU
               code 7 (tail sever, notes/porting-guide.md "Quests").
  Rewards      Black Gravios' own materials (items_em005_01.py, appended IDs), the other 4U items by English name in
               GU itemData_eng. Reward slots 3 / 4 = GU's empty row rem_000000 (Stygian's issue #8 fix).
  Supply box   the 4U quest's (quest4u.supp_4u, Gogmazios' issue #11 fix).
  Spawn        the template's boss setEmMain record with 4U's area and floats (setEmMain floats = rotation, x, y, z;
               4U spawn floats = x, y, z, rotation). GU's Volcanic Hollow is 4U's geometry (S, as Stygian's).
               Small monsters: the template's sets.
4U spawn byte +0xF (m10611: Gravios 2, Black Gravios 3; 4U's frenzy / special states, GU has none): left out, a
DEVIATION, logged.
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/black_gravios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, gear4u, gmd, quest4u   # noqa: E402
sys.path.insert(0, HERE)
import items_em005_01               # noqa: E402
from items4u import EXE, EXE_BASE, text_4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('black_gravios')
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x105; Gravios 0x5, swapped at spawn
ALT_ID = ALLOC['standin_alt'][0]                         # Basarios 0x4: names him where a real Gravios fights too
EM_4U = 41
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {15: 12, 3: 13}          # 4U Volcanic Hollow / Primal Forest -> GU stage (S: Stygian's vote over GU quest
                                    # texts, monsters/stygian_zinogre/notes/phase1-assets.md; GU em005_00's area data
                                    # covers maps 7 8 12 13 24)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: Black Gravios' cell (module/icons.c; 4U +0xE8 = 43)
PARTNER_GU = {40: 0x5}              # 4U Gravios -> GU Gravios
ICON_QUEST = {0x5: 10671}           # a GU quest with it first (its board icon)
REM_EMPTY = struct.pack('<fI', 1.0, 1) + bytes(176)     # GU's rem_000000 (184 B, no group; C: q10706)
# Quests (k = index in allocations.toml quests):
#   num   4U quest            tpl   GU template (same rank, stage and kind)
#   grav  index of the 4U Gravios stat block the ratio divides by (same quest), or
#   ref   (4U quest, stat block): a Gravios in another quest of the same 4U stars (a single hunt has none), or of
#         other stars where 4U has none (ref_stars = the reason, logged)
#   base  (GU quest, em)      the GU boss record the ratio multiplies; partners take its own record of their GU ID
#   sub   ('break', GU target, GU code) or ('deliver',): GU type 5 {GU item, count} of the 4U delivery subquest
#   alt   the quest names Black Gravios by ALT_ID (a real Gravios is in it)
# m10601 Ore D'oeuvre (4U Hub HR6 urgent, stage 3, single hunt): GU Hub HR7 as m10611, as a regular quest (an appended
# quest gates no rank: 4U's urgent mark is not kept, a DEVIATION); template q10739 (GU HR7, stage 13, one hunt target);
# 4U has no HR6 single Gravios: ratio over m10524 (HR5 single Gravios, 37 / 58 / 55 vs 39 / 66 / 56, G); base q10767.
# Subquest 4U {em 41, part 3} "Wound the back" -> GU code 2 (S: 4U break group 3 -> GU group 2 = cond 30, as the chest)
# m00911 Advanced: Whale of a Hammer (4U caravan ★9, stage 15, two Black Gravios, spawn +0xF 1 = frenzy, dropped):
# GU village ★10 as Stygian's caravan quests; template and base q1035 (GU village ★10 "hunt 2 Gravios" on stage 12);
# ratio over m00903 (caravan ★9 Gravios: 23 / 56 / 103, equal to his). Subquest: deliver 2 Coal (GU 2084).
# m10923 Hollow Promise (4U Hub G2, stage 15, single hunt, C): placed on GU Hub G4 as Stygian's G quests
# (notes/quests.md there); template q11443 (GU G4 single hunt on stage 12, the one Stygian's single G quests use);
# ratio over 4U m10904 (G2 Gravios single hunt on stage 15: rows 61 / 102 / 82 vs Black Gravios' 61 / 104 / 82);
# base GU q11438 (G4 Gravios single hunt). Subquest: 4U 0x204 {em 41, part 4} "Wound the chest" -> GU code 3 (S: GU
# Gravios' break group 3 = cond 40, the item mix of 4U break group 4, items_em005_01.py; GU code k = group k as its
# head code 1 = cond 20, q919 / q11309)
QUESTS = [
    dict(k=0, num=10611, tpl=10707, grav=0, base=(10767, 0x5), sub=('break', EM_ID, 7), alt=True),
    dict(k=1, num=10923, tpl=11443, ref=(10904, 0), base=(11438, 0x5), sub=('break', EM_ID, 3)),
    dict(k=2, num=10601, tpl=10739, ref=(10524, 0), ref_stars='4U has no HR6 single Gravios', base=(10767, 0x5),
         sub=('break', EM_ID, 2)),
    dict(k=3, num=911, tpl=1035, ref=(903, 1), base=(1035, 0x5), sub=('deliver',)),
]
_SETS = {}           # setEmMain name -> data over every quest built: one content per name, as GU's


def quest_4u(num):
    """a 4U quest by number (loc/data/quest00.arc / quest01.arc)"""
    for arc in ('quest00.arc', 'quest01.arc'):
        f = arc_files(open(os.path.join(Q4U_DIR, arc), 'rb').read())
        if 'loc\\quest\\m%05d' % num in f:
            q = f['loc\\quest\\m%05d' % num][1]
            assert q[4:8] == b'v005' and struct.unpack_from('<H', q, 0xC0)[0] == num, num
            return q
    raise KeyError('4U quest m%05d' % num)


def spawns_4u(q):
    """4U boss spawn records of the first list, 0x28 B each closed by em 0xffffffff: [(em, area, (x, y, z, rot), +0xF)]"""
    rec = struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    out = []
    while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
        out.append((struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10),
                    q[rec + 0xF]))
        rec += 0x28
    return out


def quest_data(R, qid):
    return arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % qid))['loc\\quest\\questData\\questData_%07d' % qid][1]


def boss_record(qd, em):
    """the questData boss record (+0x64, 13 B each) of em"""
    recs = [struct.unpack_from('<HBBBBBBBHBB', qd, 0x64 + 13 * k) for k in range(5)]
    return next(r for r in recs if r[0] == em)


def stats_block(q, i):
    """4U boss stat block i (+0x34 + 8 i, one per first-list spawn, in spawn order): (size %, HP, attack, other row)"""
    o = STATS_4U + 8 * i
    return (struct.unpack_from('<H', q, o)[0],) + tuple(q[o + 3:o + 6])


def stat_rows(R, exe, s, z, b):
    """(HP, attack, other) rows and the trace (r HP, r attack, target HP, target attack, rows' values): s / z = the 4U
    Black Gravios / Gravios stat blocks, b = the GU base boss record"""
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    rows = [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]
    r4 = lambda row: struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
    r_hp, r_atk = r4(s[1])[0] / r4(z[1])[0], r4(s[2])[1] / r4(z[2])[1]

    def pick(col, base_row, r):
        base = rows[base_row][col]
        return min((abs(rows[k][col] - base * r), k) for k in range(len(rows)) if rows[k][col] >= base)[1], base * r
    hp, t_hp = pick(0, b[4], r_hp)
    atk, t_atk = pick(1, b[5], r_atk)
    return (hp, atk, b[6]), (r_hp, r_atk, t_hp, t_atk, rows[hp][0], rows[atk][1])


def objectives_4u(q):
    """4U main objectives (+0xCB count, {u32 type, u16 target, u16 count} at +0xCC / +0xD4; 1 = hunt, 0x81 = capture)
    and the subquest record at +0xDC (0x204 = wound / sever {em, 4U part code}, 2 = deliver {4U item, count})"""
    n = q[0xCB]
    return [struct.unpack_from('<IHH', q, 0xCC + 8 * i) for i in range(n)], struct.unpack_from('<IHH', q, 0xDC)


def gu_names(R):
    """{GU English item name: [ids]} (GU id = itemData_eng index / 2; supply box lookup by name, quest4u.supp_4u)"""
    gu = gmd.gmd_strings(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    out = {}
    for i in range(0, len(gu), 2):
        out.setdefault(gu[i], []).append(i // 2)
    return out


def gu_items(names):
    """gu_item(4U id) -> GU id: Black Gravios' own materials (items_em005_01.py, appended IDs), else by English name
    (the first id of the name)"""
    names4 = text_4u('eng')[0]
    by_name = {n: ids[0] for n, ids in names.items()}
    ours = {k: ALLOC['items'][0] + i for i, k in enumerate(items_em005_01.ITEMS_4U)}

    def gu_item(k):
        n = names4[k]
        if k in ours: return ours[k]
        if n in by_name: return by_name[n]
        print('reward: 4U %d %s has no GU item' % (k, n))
        return None
    return gu_item


def gu_id(em4, spec):
    """GU ID a 4U boss is named by in the quest's boss records (Black Gravios: a stand-in)"""
    if em4 == EM_4U: return ALT_ID if spec.get('alt') else BOSS_ID
    return PARTNER_GU[em4]


def partner_icon(R, gid):
    qd = quest_data(R, ICON_QUEST[gid])
    assert struct.unpack_from('<H', qd, 0x64)[0] == gid and qd[0xD6], (gid, 'icon quest')
    return qd[0xD6]


def set_name(stage, em4, k, j=0):
    """setEmMain names, one content per name (asserted over the quests built), none in GU's quests (C, 2026-10-31: GU
    uses b_mNNem005_00..02 only): Black Gravios' 60 + k, a partner's 80 + k; the j-th of the same em in a quest + 10 j"""
    assert k < 10 and j < 2, (k, j)
    if em4 == EM_4U: return 'b_m%02dem005_%02d' % (stage, 60 + 10 * j + k)
    return 'b_m%02dem%03d_%02d' % (stage, PARTNER_GU[em4] & 0xff, 80 + 10 * j + k)


def build(R, exe, gu_item, names, out, spec, hp_table=None):
    k, num, tpl_id = spec['k'], spec['num'], spec['tpl']
    qid = ALLOC['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    q4 = quest_4u(num)
    sp = spawns_4u(q4)
    ems = [s[0] for s in sp]
    assert ems.count(EM_4U) >= 1 and all(e == EM_4U or e in PARTNER_GU for e in ems), (m4, ems)
    me = ems.index(EM_4U)
    assert all(stats_block(q4, i) == stats_block(q4, me) for i, e in enumerate(ems) if e == EM_4U), \
        (m4, 'Black Gravios spawns with different stats')
    frenzy = [(e, s[3]) for e, s in zip(ems, sp) if s[3]]
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    base_qd = quest_data(R, spec['base'][0])
    objs, sub4 = objectives_4u(q4)
    assert 1 <= len(objs) <= 2 and all(t in (1, 0x81) for t, _, n in objs), (m4, objs)
    assert sorted(e for _, e, n in objs for _ in range(n)) == sorted(ems), \
        (m4, 'objectives are not the spawned bosses', objs, ems)

    # --- questData: the template's (rank, board, start area, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == quest4u.QD_SIZE and qd[0x14] == stage and qd[0x1F] in (1, 2, 3), \
        (tpl_id, 'not a hunt / capture on the stage')
    assert (qd[0x12], qd[0x13]) == (base_qd[0x12], base_qd[0x13]), ('template and stat base differ in rank', tpl_id)
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # minutes (4U)
    # objectives: 4U's, targets = the real IDs; two targets = clear rule 1 (+0x1D: objectives 0 AND 1)
    qd[0x1D] = len(objs) - 1
    qd[0x1F:0x29] = bytes(10)
    for i, (t, e, n) in enumerate(objs):
        target = EM_ID if e == EM_4U else PARTNER_GU[e]
        struct.pack_into('<BHH', qd, 0x1F + 5 * i, 2 if t == 0x81 else 1, target, n)
    sub = spec.get('sub')
    if sub and sub[0] == 'break':          # GU code of the 4U part, on the 4U subquest's monster (real ID)
        assert sub4[0] == 0x204, (m4, 'the 4U subquest is not a wound / sever', sub4)
        assert sub[1] == (EM_ID if sub4[1] == EM_4U else PARTNER_GU[sub4[1]]), (m4, sub, sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, sub[1], sub[2])
    elif sub and sub[0] == 'deliver':      # GU type 5 {u16 GU item, u16 count} (C: q102 "Deliver 2 Fossilized Bones")
        assert sub4[0] == 2 and gu_item(sub4[1]) is not None, (m4, 'the 4U subquest is not a delivery', sub4)
        struct.pack_into('<BHH', qd, 0x29, 5, gu_item(sub4[1]), sub4[2])
    else:
        qd[0x29:0x2E] = bytes(5)
    # supply box from the 4U quest (quest4u.supp_4u, as Gogmazios', issue #11); a later delivery sets its group bytes
    supp, supp_later = quest4u.supp_4u(q4, text_4u('eng')[0], names)
    if supp_later:
        qd[0x58:0x60] = quest4u.SUPP_QD

    # boss records in 4U's spawn order: Black Gravios = the stand-in with the computed rows; partners = the base
    # quest's record of their GU ID
    b = boss_record(base_qd, spec['base'][1])
    if 'ref' in spec:                      # a Gravios of the same 4U stars (+0xC2) in another quest
        qr = quest_4u(spec['ref'][0])
        assert spawns_4u(qr)[spec['ref'][1]][0] == 40, ('ratio reference is not a Gravios', spec['ref'])
        assert qr[0xC2] == q4[0xC2] or spec.get('ref_stars'), ('ratio reference of other 4U stars', spec['ref'])
        if qr[0xC2] != q4[0xC2]:
            print('%s: ratio over m%05d (4U %d stars, his %d): %s (G)' % (m4, spec['ref'][0], qr[0xC2], q4[0xC2],
                                                                        spec['ref_stars']))
        grav = stats_block(qr, spec['ref'][1])
    else:
        grav = stats_block(q4, spec['grav'])
    (hp, atk, other), trace = stat_rows(R, exe, stats_block(q4, me), grav, b)
    if hp_table is not None: hp = hp_table
    recs, info = b'', []
    for i, e in enumerate(ems):
        size = stats_block(q4, i)[0]
        gid = gu_id(e, spec)
        r = (hp, atk, other, b) if e == EM_4U else (lambda pb: (pb[4], pb[5], pb[6], pb))(
            boss_record(base_qd, PARTNER_GU[e]))
        if hp_table is not None: r = (hp_table,) + r[1:]
        recs += struct.pack('<HBBBBBBBHBB', gid, 0, 0, r[3][3], r[0], r[1], r[2], r[3][7], size, r[3][9], r[3][10])
        info.append('%#x rows %d/%d/%d size %d' % (gid, r[0], r[1], r[2], size))
    qd[0x64:0x64 + 65] = recs + bytes(65 - len(recs))
    icons = [ICON if e == EM_4U else partner_icon(R, PARTNER_GU[e]) for e in ems]
    qd[0xD6:0xDB] = bytes(icons + [0] * (5 - len(icons)))
    for i, lang in enumerate(quest4u.QLANGS):
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
        n = set_name(stage, e, k, ems[:i].count(e))
        assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
        res.append(('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)))
        setnames.append(n)
    res.append(('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]))
    esl = tnames[5:8]
    for n in sorted(set(esl)):
        res.append(('quest\\zako\\emSetList\\' + n, T_ESL, tpl['quest\\zako\\emSetList\\' + n][1]))
    # rewards: rows A / B from 4U, the subquest row from 4U (row A's file when equal), slots 3 / 4 GU's empty row
    # rem_000000 (as Stygian's, issue #8: a template's condition-3 rows are its own quest's extras, none in 4U)
    ptr = lambda o: struct.unpack_from('<I', q4, o)[0]
    rows = {'rem_%sa' % m4: REWARD_ROWS_4U[0], 'rem_%sb' % m4: REWARD_ROWS_4U[1]}
    sub_name = 'rem_%sa' % m4
    if sub and ptr(SUB_ROW_4U) and ptr(SUB_ROW_4U) != ptr(REWARD_ROWS_4U[0]):
        sub_name = 'rem_%ss' % m4
        rows[sub_name] = SUB_ROW_4U
    rems = {name: quest4u.rem_4u(q4, row, gu_item) for name, row in rows.items()}
    assert not set(rems) & set(tnames), 'reward row names taken by the template'
    rems['rem_000000'] = REM_EMPTY
    assert tpl.get('quest\\rem\\rem_000000', (0, REM_EMPTY))[1] == REM_EMPTY, "GU's rem_000000 is not the empty row"
    rem = ['rem_%sa' % m4, 'rem_%sb' % m4, 'rem_000000', 'rem_000000', sub_name]
    for r in sorted(set(rem)):
        res.append(('quest\\rem\\' + r, T_REM, rems[r]))
    res.append(('quest\\supp\\supp_' + sid, T_SUPP, supp))
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
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, objectives %s, sub %s; bosses %s (Black '
          'Gravios r HP %.3f atk %.3f, target %.2f / %.2f -> %.2f / %.2f); spawns %s%s; "%s"' % (
              qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], qd[0x1F:0x29].hex(' '), qd[0x29:0x2E].hex(' '),
              info, *trace, [(s[1], tuple(round(v) for v in s[2])) for s in sp],
              '; 4U spawn byte +0xF %s DROPPED (deviation)' % frenzy if frenzy else '', t4['eng'][0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help='boss vital (HP) table byte instead of the computed one (shorter '
                                                 'tests)')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    ap.add_argument('--only', type=int, help='build only this GU quest ID')
    a = ap.parse_args()
    R = RomFS(paths.GU_ROMFS)
    exe = open(EXE, 'rb').read()
    names = gu_names(R)
    gu_item = gu_items(names)
    for spec in QUESTS:
        if a.only in (None, ALLOC['quests'][spec['k']]):
            build(R, exe, gu_item, names, a.out, spec, a.hp_table)


if __name__ == '__main__':
    main()
