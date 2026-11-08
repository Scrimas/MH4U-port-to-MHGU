"""build_em070_01_quest.py : Shrouded Nerscylla's 4U quests for MHGU, appended to GU's quest list by the core (module/quest.c
quest_group_append; allocations.toml quests + quest_append). Rules as Tidal Najarala's builder (monsters/tidal_najarala/tools/
build_em068_01_quest.py) and Monoblos' (the Dunes).

  build_em070_01_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/shrouded_nerscylla/romfs), per quest: the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write).

Her 4U quests (C, all of quest00 / 01.arc; no DLC extdata on the machine that built this, her event quests are unread), all on stage 18, the night Dunes:
  m01014  caravan ★10, stat rows 45 / 93 / 109, subquest slay 8 Bnahabra
  m10902  hub G2 (star 9), rows 61 / 102 / 82, subquest wound the outer hide
  m10914  hub G2, "Advanced", hunt 2 of her one after the other (second spawn byte +0xC 1), rows 42 / 102 / 56 each, spawn byte +0xF 1 (frenzy), subquest suppress its frenzy twice
  m22003  Arena "Grudge Match" (quest type 1): preset gear, time ranks. NOT PORTED, the user's rule ("alle Missionen außer Arena Quest").
She is G rank only in 4U (C: her carve and break tables hold nothing else), so all of them stay G rank here. No quest of hers holds a real Nerscylla (C), so the stand-in is never mistaken.

Placement: as Tidal's and Monoblos' (the user, 2026-11-05: single player and multiplayer versions, hub HP differs): all three as village ★10 G (single player, tier 5) and as hub quests at G3, GU's rank of its solo Nerscylla
hunt q11332 (C).

Sources (C unless marked):
  GU template  per quest (QUESTS): stars / class bytes, board, start area, flags, +0x1A, money, questPlus, GMD unk word. Hub: q11327 (G3, a plain hunt on the Dunes, so no re-staging). Village: GU has no village ★10 G quest on
               the Dunes: q1012, GU's plain G single hunt, re-staged 2 -> 5, as Monoblos' m01018.
  Small monsters q605 (GU's Dunes set of Apceros and Bnahabra, the list her 4U quests name, on the quest's own stage).
  Stat rows    r = 1 for the single hunts: 4U's Nerscylla at G (m10825: 60 / 100 / 82) stands against her 61 / 102 / 82 in the same steps, so GU's rows at the placement: q1012's 51 / 97 / 85 (every village ★10 G single hunt), q11332's
               Nerscylla 102 / 110 / 96. m10914 hunts two: HP = base x r, r = her 4U HP of a double (row 42, 1.36) over a single (row 61, 1.93) = 0.705, the nearest GU row not below it; attack and other as the base (102 = 102 in 4U, GU's own double
               hunts keep theirs too: q11367).
               Her base HP (dttune, 3900) = GU Nerscylla's, as in 4U.
  Boss record  her = the stand-in Nerscylla (allocations.toml standin_id 0x46), swapped to 0x146 at spawn by module/main.c; aura 0; size from 4U; restore / byte 8 / size table / stamina = the base record's.
  4U quest     text (5 languages), minutes, objectives, spawns (area, point, rotation), reward rows A / B / subquest.
  Subquest     m10902: 4U 0x204 {96, part 4} "outer hide" -> GU type 8 {real ID, code 3}. GU code = break group, GU cond = 10 * (group + 1) (porting guide), GU's "poison spike" is 2 = 4U part 3 (4U's texts: 2 claw, 3 spike, 4 hide), so 4 -> 3 (S).
               m01014: 4U 0x101 {68, 8} -> GU type 1 {Bnahabra 0x101a, 8} (C: q404 "Slay 15 Bnahabra"). m10914: 4U 0x4004 "suppress its frenzy" has no GU state (no frenzy): GU's subquest of its own double Nerscylla hunt instead, type 9 {count 2} "Mount and topple
               monster twice" with GU's text (q927), a DEVIATION.
  Rewards      her own materials (items_em070_01.py, appended IDs), the other 4U items by English name in GU itemData_eng (a 4U item GU lacks is left out, logged). Reward slots 3 / 4 = GU's empty row rem_000000.
  Supply box   village: the 4U quest's (quest4u.supp_4u), one Map at the start (map_only_start, the user 2026-11-05 and again 2026-11-06: "darf es nur eine Map sein"; C: GU's village boxes hold one), its night box's Hot Drinks become Cool Drinks: GU's Dunes is the hot day map (a DEVIATION with the stage, Monoblos' m00818).
               Hub: the template's box and +0x58 delivery groups (4 Maps for 4 players, 4 x supplies, nothing else at the start: C).
  Spawn        the template's boss setEmMain record with 4U's area and floats, 4U 18 -> GU 5 (Monoblos' m00818: GU's Dunes = 4U's, S). +8 = GU's round = 4U's spawn byte +0xC: the second of m10914 comes after the first (GU's q927 the same).
  Frenzy       m10914's spawn byte +0xF 1: the frenzy state GU has no equivalent of (Tigerstripe's rule, the user 2026-10-20): left out, a DEVIATION, logged per quest.
"""
import argparse, os, re, statistics, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/shrouded_nerscylla
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, gear4u, gmd, quest4u   # noqa: E402
sys.path.insert(0, HERE)
import items_em070_01               # noqa: E402
from items4u import EXE, EXE_BASE, text_4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('shrouded_nerscylla')
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x146; Nerscylla 0x46, swapped at spawn
EM_4U = 96
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {18: 5}                  # 4U night Dunes -> GU Dunes (Monoblos' STAGE_GU; GU has no night Dunes)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: her cell (module/icons.c; 4U +0xE8 = 106)
REM_EMPTY = struct.pack('<fI', 1.0, 1) + bytes(176)     # GU's rem_000000 (184 B, no group; C: q10706)
G_TIER = 5                          # GU questData +0x13 rank tier (C: village ★10 G 5, hub G 5)
URGENT = 0x1                        # questData +0x16F bit 0 = an urgent (key) quest (Monoblos' builder)
BNAHABRA = 0x101a                   # GU's small monster ID (C: q404, q11224)
ESL_TPL = 605                       # GU's Dunes small monsters Apceros + Bnahabra (C: 4U's list)
SUB_TEXT_TPL = 927                  # GU's own subquest of its double Nerscylla hunt
# Quests (k = index in allocations.toml quests):
#   num   4U quest
#   tpl   GU template (same placement and kind)
#   base  (GU quest, em)  the GU boss record whose rows, difficulty, size table and stamina she takes
#   sub   ('break', GU code) | ('slay', GU ID, 4U em, count) | ('gu', 5 bytes, GU quest whose subquest text is taken)
#   tpl_stage the template sits on another stage (its stage byte is replaced)
#   supp_tpl  the GU hub quest whose supply box and delivery groups replace the 4U quest's
# Only the quests 4U has, where 4U has them (the user, 2026-11-08: "keine Dorf-Quests, wenn es sie im Original nicht gab";
# Monoblos' copies were the exception, 4U has no multiplayer quest of his): m01014 is a caravan quest -> village, m10902 /
# m10914 are guild quests -> hub. 0.1.11's village copies of m10902 / m10914 (1063 / 1064) and hub copy of m01014 (11369) are gone.
QUESTS = [
    # --- 4U caravan quest: village ★10 G
    dict(k=0, num=1014, tpl=1012, tpl_stage=2, base=(1012, 0x202), sub=('slay', BNAHABRA, 68, 8)),
    # --- 4U guild quests: hub G3
    dict(k=1, num=10902, tpl=11327, base=(11332, 0x46), supp_tpl=11327, sub=('break', 3)),
    dict(k=2, num=10914, tpl=11327, base=(11332, 0x46), supp_tpl=11327, sub=('gu', bytes([9, 0, 0, 2, 0]), SUB_TEXT_TPL)),
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
    """4U boss spawn records of the first list, 0x28 B each closed by em 0xffffffff: [(em, area, (x, y, z, rot), +0xC, +0xF)]"""
    rec = struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    out = []
    while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
        out.append((struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10), q[rec + 0xC], q[rec + 0xF]))
        rec += 0x28
    return out


def quest_data(R, qid):
    return arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % qid))['loc\\quest\\questData\\questData_%07d' % qid][1]


def boss_record(qd, em):
    """the questData boss record (+0x64, 13 B each) of em"""
    recs = [struct.unpack_from('<HBBBBBBBHBB', qd, 0x64 + 13 * k) for k in range(5)]
    return next(r for r in recs if r[0] == em)


def stats_block(q, i):
    """4U boss stat block i (+0x34 + 8 i, one per spawn, in spawn order): (size %, HP, attack, other row)"""
    o = STATS_4U + 8 * i
    return (struct.unpack_from('<H', q, o)[0],) + tuple(q[o + 3:o + 6])


def stat_rows(R, exe, q4, b, count):
    """(HP, attack, other) rows and the trace, b = the GU base record; a quest with `count` of her: HP by 4U's double against its single (docstring)"""
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    rows = [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]
    if count == 1:
        return (b[4], b[5], b[6]), (1.0, rows[b[4]][0], rows[b[4]][0], rows[b[5]][1])
    r4 = lambda row: struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
    single = stats_block(quest_4u(10902), 0)
    r_hp = r4(stats_block(q4, 0)[1])[0] / r4(single[1])[0]
    assert r_hp < 1, r_hp
    target = rows[b[4]][0] * r_hp
    hp = min((abs(rows[k][0] - target), k) for k in range(len(rows)) if rows[k][0] >= target - 1e-3)[1]
    return (hp, b[5], b[6]), (r_hp, target, rows[hp][0], rows[b[5]][1])


def objectives_4u(q):
    """4U main objectives (+0xCB count, {u32 type, u16 target, u16 count} at +0xCC / +0xD4; 1 = hunt) and the subquest record at +0xDC"""
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
    """gu_item(4U id) -> GU id: her own materials (items_em070_01.py, appended IDs), else by English name (the first id of
    the name), None when GU has no such item"""
    names4 = text_4u('eng')[0]
    by_name = {n: ids[0] for n, ids in names.items()}
    ours = {k: ALLOC['items'][0] + i for i, k in enumerate(items_em070_01.ITEMS_4U)}

    def gu_item(k):
        n = names4[k]
        if k in ours: return ours[k]
        if n in by_name: return by_name[n]
        print('reward: 4U %d %s has no GU item (left out)' % (k, n))
        return None
    return gu_item


def map_only_start(supp, map_id, m4):
    """GU supp bytes with one Map at the start, as GU's village boxes (C: q1002, q1012, q1036 hold 1, its hub boxes 4 for
    4 players, and 4U's hub quests m10902 / m10914 hold 4): the box's other start items go to the front of delivery group 1
    (the first slot whose group byte is 1; slots 32.. = group 4 stay), the extra Maps go. As Monoblos' builder, plus the one Map"""
    slots = [list(struct.unpack_from('<HBB', supp, 8 + 4 * s)) for s in range(40)]
    g1 = [s for s in range(32) if slots[s][2]]
    assert len(g1) == 1 and slots[g1[0]][2] == 1, ('box without a single delivery group 1', m4, g1)
    start = [x for x in slots[:g1[0]] if x[0]]
    maps, move = [x for x in start if x[0] == map_id], [x for x in start if x[0] != map_id]
    assert maps, ('no Map in the start box', m4)
    if not move and len(maps) == 1: return supp
    rest = [x for x in slots[g1[0]:32] if x[0]]
    if move:
        rest[0][2] = 0
        rest = move + rest
        rest[0][2] = 1
    new = maps[:1] + rest
    assert len(new) <= 32, (m4, 'box overflow')
    new += [[0, 0, 0]] * (32 - len(new))
    print('%s: start box = one Map (%d extra dropped), %d item(s) moved to delivery 1' % (m4, len(maps) - 1, len(move)))
    return supp[:8] + b''.join(struct.pack('<HBB', *x) for x in new + slots[32:])


def set_name(stage, k, i):
    """setEmMain names, one content per name (asserted over the quests built), none in GU's quests (C, 2026-11-06: GU uses
    b_mNNem070_00..02 only): hers 60 + 2 k + i"""
    assert k < 10 and i < 2, (k, i)
    return 'b_m%02dem070_%02d' % (stage, 60 + 2 * k + i)


def build(R, exe, gu_item, names, out, spec, hp_table=None):
    k, num, tpl_id = spec['k'], spec['num'], spec['tpl']
    qid = ALLOC['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    q4 = quest_4u(num)
    sp = spawns_4u(q4)
    ems = [s[0] for s in sp]
    assert all(e == EM_4U for e in ems) and len(ems) in (1, 2), (m4, ems)
    frenzy = [s[4] for s in sp if s[4]]
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    base_qd = quest_data(R, spec['base'][0])
    objs, sub4 = objectives_4u(q4)
    assert len(objs) == 1 and objs[0][0] == 1 and objs[0][1] == EM_4U and objs[0][2] == len(ems), (m4, objs, ems)

    # --- questData: the template's (rank, board, start area, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == quest4u.QD_SIZE and qd[0x14] == spec.get('tpl_stage', stage), (tpl_id, 'not on the stage')
    qd[0x14] = stage
    assert (qd[0x12], qd[0x13]) == (base_qd[0x12], base_qd[0x13]), ('template and stat base differ in rank', tpl_id)
    assert qd[0x13] == G_TIER, (tpl_id, 'template is not G rank')
    assert not struct.unpack_from('<H', qd, 0x16F)[0] & URGENT, (tpl_id, 'template is an urgent quest')
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # minutes (4U)
    qd[0x1D] = 0
    assert qd[0x1F] == 1, (tpl_id, 'not a hunt')
    qd[0x1F:0x29] = bytes(10)
    struct.pack_into('<BHH', qd, 0x1F, 1, EM_ID, len(ems))
    sub, sub_text = spec['sub'], None
    if sub[0] == 'break':                   # GU code of the 4U part, on her (real ID)
        assert sub4[0] == 0x204 and sub4[1] == EM_4U, (m4, 'the 4U subquest is not her wound', sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, EM_ID, sub[1])
    elif sub[0] == 'slay':                  # GU sub type 1 = hunt N small monsters (Stygian's builder, C)
        assert sub4 == (0x101, sub[2], sub[3]), (m4, 'the 4U subquest is not this small-monster hunt', sub4)
        struct.pack_into('<BHH', qd, 0x29, 1, sub[1], sub[3])
    else:                                   # GU's own subquest with GU's text: the 4U one has no GU state
        assert sub4[0] == 0x4004, (m4, sub4)
        qd[0x29:0x2E] = sub[1]
        sq = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % sub[2]))
        assert quest_data(R, sub[2])[0x29:0x2E] == sub[1], ('GU quest has another subquest', sub[2])
        sub_text = {lang: quest4u.gmd_unpack(sq['%s\\quest\\questData\\questData_%07d_%s' % (lang, sub[2], lang)][1])[1][6].decode('utf-8') for lang in quest4u.LANGS}
    if spec.get('supp_tpl'):                # a GU hub box (4 players) with its delivery groups
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
        ia, ib, supp = names['Hot Drink'][0], names['Cool Drink'][0], bytearray(supp)
        hits = [s for s in range(40) if struct.unpack_from('<H', supp, 8 + 4 * s)[0] == ia]
        for s in hits:
            struct.pack_into('<H', supp, 8 + 4 * s, ib)
        supp = bytes(supp)
        print('%s: supply Hot Drink -> Cool Drink in %d slot(s)' % (m4, len(hits)))

    # boss records: hers = the stand-in, the computed rows
    b = boss_record(base_qd, spec['base'][1])
    (hp, atk, other), trace = stat_rows(R, exe, q4, b, len(ems))
    if hp_table is not None: hp = hp_table
    recs = b''
    for i in range(len(ems)):
        recs += struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, b[3], hp, atk, other, b[7], stats_block(q4, i)[0], b[9], b[10])
    qd[0x64:0x64 + 65] = recs + bytes(65 - len(recs))
    qd[0xD6:0xDB] = bytes([ICON] * len(ems) + [0] * (5 - len(ems)))
    for i, lang in enumerate(quest4u.QLANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))

    # --- questLink + resources
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    res, set_list = [], []
    for i, s in enumerate(sp):              # one setEmMain per boss: the template's first record with 4U's area and floats, +8 = GU's round = 4U's +0xC
        se = bytearray(tpl['quest\\boss\\setEmMain\\' + tnames[0]][1])
        x, y, z, rot = s[2]
        struct.pack_into('<I', se, 8, s[3])
        struct.pack_into('<I4f', se, 0x0C, s[1], rot, x, y, z)
        n = set_name(stage, k, i)
        assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
        res.append(('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)))
        set_list.append(n)
    res.append(('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]))
    set_refs = b''.join(ref(T_SET, n) for n in set_list) + ref(T_SET, 'b_m00em000_00') * (5 - len(set_list))
    # small monsters of the GU quest on the quest's own stage
    esl_src = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % ESL_TPL))
    el = esl_src['loc\\quest\\questLink\\questLink_%07d' % ESL_TPL][1]
    esl_names = [el[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    assert quest_data(R, ESL_TPL)[0x14] == stage, ('esl_tpl on another stage', ESL_TPL)
    esl = esl_names[5:8]
    for nm in sorted(set(esl)):
        res.append(('quest\\zako\\emSetList\\' + nm, T_ESL, esl_src['quest\\zako\\emSetList\\' + nm][1]))
    # rewards: rows A / B from 4U, the subquest row from 4U (row A's file when equal), slots 3 / 4 GU's empty row
    ptr = lambda o: struct.unpack_from('<I', q4, o)[0]
    rows = {'rem_%sa' % m4: REWARD_ROWS_4U[0], 'rem_%sb' % m4: REWARD_ROWS_4U[1]}
    sub_name = 'rem_%sa' % m4
    if ptr(SUB_ROW_4U) and ptr(SUB_ROW_4U) != ptr(REWARD_ROWS_4U[0]):
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
    link = tlink[:8] + set_refs
    link += b''.join(ref(T_ESL, nm) for nm in esl)
    link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    if sub_text:
        for lang, s in sub_text.items():
            t4[lang][6] = s
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    qd = bytes(qd)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, objective %s, sub %s; boss %#x x%d rows %s (r HP %.3f, target %.2f -> %.2f, attack %.2f); spawns %s%s' % (
        qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], qd[0x1F:0x24].hex(' '), qd[0x29:0x2E].hex(' '), BOSS_ID, len(ems), (hp, atk, other), *trace,
        [(s[1], s[3]) for s in sp], '; 4U frenzy state %s DROPPED (deviation)' % frenzy if frenzy else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help='boss vital (HP) table byte instead of the computed one (shorter tests)')
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
