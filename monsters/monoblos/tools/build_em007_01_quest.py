"""build_em007_01_quest.py : Monoblos' 4U quests for MHGU, appended to GU's quest list by the core
(module/quest.c quest_group_append; allocations.toml quests + quest_append). Placement as Black Gravios' caravan quests
(monsters/black_gravios/tools/build_em005_01_quest.py, Stygian Zinogre's rule there): 4U caravan -> GU village ★10.
Ranks (the user, 2026-11-05: "ranks that make sense in GU's single player, High and G rank; then multiplayer quests
for both; hub HP differs"): each quest keeps its 4U rank (C: m00801 / m00818 reward his High materials Carapace /
Thoracic, m01018 his G ones Cortex / Chine; his carves / breaks are High and G only): single player = village ★10
High (tier 3) / G (tier 5, GU has 16 village ★10 G quests, C); multiplayer = the same three as hub quests on GU
Diablos' hub ranks, HR7 and G4 (C: q10768 / q11448, GU's only hub Diablos hunts besides multi-monster ones).

  build_em007_01_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/monoblos/romfs), per quest: the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write).

Sources (C unless marked), the rules of Black Gravios' builder:
  GU template  per quest (QUESTS): a GU quest of the same placement and kind (stars / class bytes, board, start area,
               flags, +0x1A, money, questPlus, GMD unk word), a Diablos one where GU has it. GU has no village ★10
               single Diablos hunt on the Dunes (C, 2026-11-05: q1002 is on stage 22, q1036 = capture on stage 5): the
               hunts take q1002 re-staged to the Dunes with q1036's small monsters (Black Gravios' m10606 rule,
               tpl_stage / esl_tpl). Village ★10 G: q1012, GU's plain G single hunt (type 0, as q1002; q1009 / q1011 /
               q1045 carry type 1 and +0x1E 25), re-staged. Hub: q10728 (a plain HR7 hunt on the Dunes: GU's HR7
               Diablos hunt q10768 is HR7's urgent quest, see URGENT; 0.4.2 used it and the hub showed his quest as
               an emergency quest, user 2026-11-05), q10706 (HR7 capture, stage 12, as Stygian's 10779), q11448 (G4
               Diablos hunt, stage 22). Every Dunes quest of these uses the same small monster set z_m05d_059 (C).
  Stat rows    r = his 4U em_nando_tbl row value over 4U Diablos' at the same tier and kind (HP column 0, attack
               column 1): the only such pair is caravan ★10 G (RATIO: m01018 vs m01025, HP 1.00, attack 0.967, C); 4U
               has no High Rank Diablos quest, so the High quests take the same r (G). Base = GU's rows at the
               placement: every village ★10 single hunt has 37 / 66 / 19 (HR) or 51 / 97 / 85 (G), the hub ones
               GU's Diablos quests q10768 (HR7 49 / 82 / 84) and q11448 (G4 107 / 108 / 97): GU's hub rows are its
               multiplayer values (HP x1.57 / x3.85 against x1.21 / x1.63 in the village, C). Target = base x r, the
               nearest GU row not below it. (Until 0.4.1 the ★8 quests divided by m01025, a G quest: HP x0.73, attack
               x0.45 at village HR, under GU's own Diablos there.)
  Boss record  Monoblos = the stand-in Diablos (allocations.toml standin_id 0x7), swapped to 0x107 at spawn by
               module/main.c; aura 0.
  4U quest     text (5 languages), minutes, objectives, spawns (area, point, rotation), reward rows A / B / subquest.
  Subquest     4U 0x204 {em 101, part 2} = "horn" (C: m00801 / m01018 texts) -> GU code 1 (C: GU q1002 / q11406 /
               q1011024 "horn" = code 1; 4U Diablos m10926 part 2 = "horn" too); m00818: deliver (GU type 5).
  Rewards      Monoblos' own materials (items_em007_01.py, appended IDs), the other 4U items by English name in GU
               itemData_eng (a 4U item GU lacks is left out, logged). Reward slots 3 / 4 = GU's empty row rem_000000.
  Supply box   the 4U quest's (quest4u.supp_4u: the supplies as delivery group 1 a few minutes in, the restock as
               group 4), with only the Map at the start as GU's HR / G boxes (map_only_start; C: q1002 / q1036 / q1012
               and every hub box start with Maps only; the user, 2026-11-05: "at the start GU gives only the map").
               Hub quests (supp_tpl): the box and questData +0x58 delivery groups of a GU hub quest of the same rank
               and kind, as 4U's boxes are for one player (user 2026-11-05: "4 maps in the
               multiplayer box"; C: every GU hub box starts with 4 Maps, group 1 holds 4 x meds / rations / drinks):
               GU's Diablos HR7 hunt q10768 and G4 hunt q11448 (EZ Sonic Bombs, as his 4U boxes), the HR7 capture
               template q10706 (tranquilizers).
  Spawn        the template's boss setEmMain record with 4U's area and floats. GU's Dunes = 4U's Dunes (S, the porting
               guide's 4U 17 -> GU 5); 4U's night Dunes (stage 18, m00818) -> GU's Dunes: GU has no night Dunes (a
               DEVIATION). Small monsters: the template's sets (or esl_tpl's).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, gear4u, gmd, quest4u   # noqa: E402
sys.path.insert(0, HERE)
import items_em007_01               # noqa: E402
from items4u import EXE, EXE_BASE, msg4u, text_4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('monoblos')
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x107; Diablos 0x7, swapped at spawn
EM_4U, EM_4U_REF = 101, 99                               # Monoblos; Diablos (the stat ratio's reference)
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {17: 5, 18: 5}           # 4U Dunes (day / night) -> GU Dunes (porting guide; GU has no night Dunes)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: Monoblos' cell (module/icons.c; 4U +0xE8 = 111)
REM_EMPTY = struct.pack('<fI', 1.0, 1) + bytes(176)     # GU's rem_000000 (184 B, no group; C: q10706)
RATIO = ((1018, 0), (1025, 0))      # (4U quest, stat block): Monoblos, Diablos at the same tier and kind (see above)
TIER = {'high': 3, 'g': 5}          # GU questData +0x13 rank tier (C: village ★10 3 / 5, hub HR7 3, G4 5)
URGENT = 0x1                        # questData +0x16F bit 0 = an urgent (key) quest (C: 28 GU quests, one per star:
                                    # village 206 303 402 501 .. 1005, hub 10216 10307 .. 10768, G 11204 11319 11401)
# Quests (k = index in allocations.toml quests):
#   num   4U quest            rank  its 4U rank (checked against the template's tier)
#   tpl   GU template (same placement and kind)
#   base  (GU quest, em)      the GU boss record the ratio multiplies (its rows, difficulty, size table, stamina)
#   sub   ('break', GU target, GU code) or ('deliver',)
#   tpl_stage the template sits on another stage (its stage byte is replaced); esl_tpl = the GU quest whose small
#             monster sets are used instead of the template's (one on the quest's own stage)
#   supp_tpl  the GU hub quest whose supply box and delivery groups replace the 4U quest's (see above)
QUESTS = [
    # --- single player: village ★10
    # m00801 (caravan ★8 HR, Dunes, hunt): q1002 re-staged 22 -> 5, q1036's small monsters; base q1002's Diablos
    dict(k=0, num=801, rank='high', tpl=1002, tpl_stage=22, esl_tpl=1036, base=(1002, 0x7),
         sub=('break', EM_ID, 1)),
    # m00818 (caravan ★8 HR, night Dunes, capture, deliver 4U item 791): capture q1036 (stage 5), base its Diablos;
    # its night box's Hot Drinks become Cool Drinks: GU's Dunes is the hot day map (DEVIATION with the stage)
    dict(k=1, num=818, rank='high', tpl=1036, base=(1036, 0x7), sub=('deliver',),
         supp_swap={'Hot Drink': 'Cool Drink'}),
    # m01018 (caravan ★10 G, Dunes, hunt): q1012 re-staged 2 -> 5, q1036's small monsters; base its boss (51 / 97 /
    # 85: GU has no single village G Diablos hunt; q1030's Diablos is one of three in the Arena)
    dict(k=2, num=1018, rank='g', tpl=1012, tpl_stage=2, esl_tpl=1036, base=(1012, 0x202), sub=('break', EM_ID, 1)),
    # --- multiplayer: hub
    # m00801 -> HR7 hunt q10728 (Dunes, a plain hunt), base q10768's Diablos (GU's HR7 urgent quest: its rows and box)
    dict(k=3, num=801, rank='high', tpl=10728, base=(10768, 0x7), supp_tpl=10768, sub=('break', EM_ID, 1)),
    # m00818 -> HR7 capture: q10706 re-staged 12 -> 5, q10768's small monsters; base q10768's Diablos
    dict(k=4, num=818, rank='high', tpl=10706, tpl_stage=12, esl_tpl=10768, base=(10768, 0x7), supp_tpl=10706,
         sub=('deliver',)),
    # m01018 -> G4 hunt: q11448 re-staged 22 -> 5, q11464's small monsters; base q11448's Diablos
    dict(k=5, num=1018, rank='g', tpl=11448, tpl_stage=22, esl_tpl=11464, base=(11448, 0x7), supp_tpl=11448,
         sub=('break', EM_ID, 1)),
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
    Monoblos / Diablos stat blocks, b = the GU base boss record"""
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    rows = [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]
    r4 = lambda row: struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
    r_hp, r_atk = r4(s[1])[0] / r4(z[1])[0], r4(s[2])[1] / r4(z[2])[1]

    def pick(col, base_row, r):
        """the GU row nearest base x r, never below it (r <= 1 here: his 4U attack is 0.967 of Diablos'; Black
        Gravios' rule kept rows >= the base's: his quests were never weaker than the base)"""
        base = rows[base_row][col]
        return min((abs(rows[k][col] - base * r), k) for k in range(len(rows)) if rows[k][col] >= base * r)[1], base * r
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
    """gu_item(4U id) -> GU id: Monoblos' own materials (items_em007_01.py, appended IDs), else by English name (the
    first id of the name), None when GU has no such item"""
    names4 = text_4u('eng')[0]
    by_name = {n: ids[0] for n, ids in names.items()}
    ours = {k: ALLOC['items'][0] + i for i, k in enumerate(items_em007_01.ITEMS_4U)}

    def gu_item(k):
        n = names4[k]
        if k in ours: return ours[k]
        if n in by_name: return by_name[n]
        print('reward: 4U %d %s has no GU item (left out)' % (k, n))
        return None
    return gu_item


def map_only_start(supp, map_id, m4):
    """GU supp bytes with only the Map(s) at the start: the box's other start items go to the front of delivery group 1
    (the first slot whose group byte is 1; slots 32.. = group 4 stay)"""
    slots = [list(struct.unpack_from('<HBB', supp, 8 + 4 * s)) for s in range(40)]
    g1 = [s for s in range(32) if slots[s][2]]
    assert len(g1) == 1 and slots[g1[0]][2] == 1, ('box without a single delivery group 1', m4, g1)
    start = [x for x in slots[:g1[0]] if x[0]]
    keep, move = [x for x in start if x[0] == map_id], [x for x in start if x[0] != map_id]
    assert keep, ('no Map in the start box', m4)
    if not move: return supp
    rest = [x for x in slots[g1[0]:32] if x[0]]
    rest[0][2] = 0
    group1 = move + rest
    group1[0][2] = 1
    new = keep + group1
    assert len(new) <= 32, (m4, 'box overflow')
    new += [[0, 0, 0]] * (32 - len(new))
    print('%s: start box = Map only, %s moved to delivery 1' % (m4, [x[:2] for x in move]))
    return supp[:8] + b''.join(struct.pack('<HBB', *x) for x in new + slots[32:])


def set_name(stage, k):
    """setEmMain names, one content per name (asserted over the quests built), none in GU's quests (C, 2026-11-05: GU
    uses b_mNNem007_00..02 only): Monoblos' 60 + k"""
    assert k < 10, k
    return 'b_m%02dem007_%02d' % (stage, 60 + k)


def build(R, exe, gu_item, names, out, spec, hp_table=None):
    k, num, tpl_id = spec['k'], spec['num'], spec['tpl']
    qid = ALLOC['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    q4 = quest_4u(num)
    sp = spawns_4u(q4)
    ems = [s[0] for s in sp]
    assert ems == [EM_4U], (m4, 'not a single Monoblos', ems)
    frenzy = [(e, s[3]) for e, s in zip(ems, sp) if s[3]]
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    base_qd = quest_data(R, spec['base'][0])
    objs, sub4 = objectives_4u(q4)
    assert len(objs) == 1 and objs[0][0] in (1, 0x81) and objs[0][1:] == (EM_4U, 1), (m4, objs)

    # --- questData: the template's (rank, board, start area, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == quest4u.QD_SIZE and qd[0x14] == spec.get('tpl_stage', stage) and qd[0x1F] in (1, 2), \
        (tpl_id, 'not a hunt / capture on the stage')
    want_kind = 2 if objs[0][0] == 0x81 else 1
    assert qd[0x1F] == want_kind, (tpl_id, 'template is not the 4U quest\'s kind')
    qd[0x14] = stage
    assert (qd[0x12], qd[0x13]) == (base_qd[0x12], base_qd[0x13]), ('template and stat base differ in rank', tpl_id)
    assert qd[0x13] == TIER[spec['rank']], (tpl_id, 'template tier is not his 4U rank', spec['rank'])
    assert not struct.unpack_from('<H', qd, 0x16F)[0] & URGENT, (tpl_id, 'template is an urgent quest')
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # minutes (4U)
    qd[0x1D] = 0
    qd[0x1F:0x29] = bytes(10)
    struct.pack_into('<BHH', qd, 0x1F, want_kind, EM_ID, 1)
    sub = spec.get('sub')
    if sub and sub[0] == 'break':          # GU code of the 4U part, on Monoblos (real ID)
        assert sub4[0] == 0x204 and sub4[1] == EM_4U, (m4, 'the 4U subquest is not his wound / sever', sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, sub[1], sub[2])
    elif sub and sub[0] == 'deliver':      # GU type 5 {u16 GU item, u16 count} (C: q102 "Deliver 2 Fossilized Bones")
        assert sub4[0] == 2 and gu_item(sub4[1]) is not None, (m4, 'the 4U subquest is not a delivery', sub4)
        struct.pack_into('<BHH', qd, 0x29, 5, gu_item(sub4[1]), sub4[2])
    else:
        qd[0x29:0x2E] = bytes(5)
    if spec.get('supp_tpl'):             # a GU hub box (4 players) with its delivery groups
        st = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % spec['supp_tpl']))
        sl = st['loc\\quest\\questLink\\questLink_%07d' % spec['supp_tpl']][1]
        supp = st['quest\\supp\\' + sl[8 + 20 * 13 + 4:8 + 20 * 14].split(b'\0')[0].decode()][1]
        sq = quest_data(R, spec['supp_tpl'])
        assert (sq[0x12], sq[0x13], sq[0x1F]) == (qd[0x12], qd[0x13], qd[0x1F]), ('supp_tpl of another rank / kind',
                                                                                  spec['supp_tpl'])
        qd[0x58:0x60] = sq[0x58:0x60]
    else:
        supp, supp_later = quest4u.supp_4u(q4, text_4u('eng')[0], names)
        if supp_later:
            qd[0x58:0x60] = supp_later   # the delivery groups (quest4u.supp_4u)
        supp = map_only_start(supp, names['Map'][0], m4)
    for a, b in spec.get('supp_swap', {}).items():
        ia, ib, supp = names[a][0], names[b][0], bytearray(supp)
        hits = [s for s in range(40) if struct.unpack_from('<H', supp, 8 + 4 * s)[0] == ia]
        assert hits, ('supp_swap: no %s in the box' % a, m4)
        for s in hits:
            struct.pack_into('<H', supp, 8 + 4 * s, ib)
        supp = bytes(supp)
        print('%s: supply %s -> %s in %d slot(s)' % (m4, a, b, len(hits)))

    # boss record: Monoblos = the stand-in with the computed rows
    b = boss_record(base_qd, spec['base'][1])
    (qm, im), (qz, iz) = RATIO
    qm4, qz4 = quest_4u(qm), quest_4u(qz)
    assert spawns_4u(qm4)[im][0] == EM_4U and spawns_4u(qz4)[iz][0] == EM_4U_REF, \
        ('RATIO is not Monoblos / Diablos', RATIO)
    assert qm4[0xC2] == qz4[0xC2], ('RATIO quests of other 4U stars', RATIO)
    (hp, atk, other), trace = stat_rows(R, exe, stats_block(qm4, im), stats_block(qz4, iz), b)
    if hp_table is not None: hp = hp_table
    size = stats_block(q4, 0)[0]
    recs = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, b[3], hp, atk, other, b[7], size, b[9], b[10])
    qd[0x64:0x64 + 65] = recs + bytes(65 - len(recs))
    qd[0xD6:0xDB] = bytes([ICON, 0, 0, 0, 0])
    for i, lang in enumerate(quest4u.QLANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))

    # --- questLink + resources: one setEmMain (the template's first record with 4U's area and floats); small monsters
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    se0 = tpl['quest\\boss\\setEmMain\\' + tnames[0]][1]
    se = bytearray(se0)
    x, y, z, rot = sp[0][2]
    struct.pack_into('<I4f', se, 0x0C, sp[0][1], rot, x, y, z)
    n = set_name(stage, k)
    assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
    res = [('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)),
           ('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1])]
    esl_src, esl_names = tpl, tnames
    if spec.get('esl_tpl'):                # small monsters of a GU quest on the quest's own stage
        esl_src = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % spec['esl_tpl']))
        el = esl_src['loc\\quest\\questLink\\questLink_%07d' % spec['esl_tpl']][1]
        esl_names = [el[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
        assert quest_data(R, spec['esl_tpl'])[0x14] == stage, ('esl_tpl on another stage', spec['esl_tpl'])
    esl = esl_names[5:8]
    for nm in sorted(set(esl)):
        res.append(('quest\\zako\\emSetList\\' + nm, T_ESL, esl_src['quest\\zako\\emSetList\\' + nm][1]))
    # rewards: rows A / B from 4U, the subquest row from 4U (row A's file when equal), slots 3 / 4 GU's empty row
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
    link = tlink[:8] + ref(T_SET, n) + ref(T_SET, 'b_m00em000_00') * 4
    link += b''.join(ref(T_ESL, nm) for nm in esl)
    link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    qd = bytes(qd)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, objective %s, sub %s; boss %#x rows %d/%d/%d '
          'size %d (r HP %.3f atk %.3f, target %.2f / %.2f -> %.2f / %.2f); spawn area %d%s' % (
              qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], qd[0x1F:0x24].hex(' '), qd[0x29:0x2E].hex(' '),
              BOSS_ID, hp, atk, other, size, *trace, sp[0][1],
              '; 4U spawn byte +0xF %s DROPPED (deviation)' % frenzy if frenzy else ''))


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
