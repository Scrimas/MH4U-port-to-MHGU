"""build_em068_01_quest.py : Tidal Najarala's 4U quests for MHGU, appended to GU's quest list by the core (module/quest.c
quest_group_append; allocations.toml quests + quest_append). Rules as Monoblos' builder (monsters/monoblos/tools/
build_em007_01_quest.py) for the single hunts, Stygian Zinogre's (monsters/stygian_zinogre/tools/build_em057_01_quest.py)
for the quest with partners.

  build_em068_01_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/tidal_najarala/romfs), per quest: the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write).

Her 4U quests (C, all of quest00 / 01.arc; no DLC extdata on the machine that built this, her event quests are unread):
  m10822  hub G1 (star 8), Frozen Seaway, Tidal, stat rows 60 / 100 / 82, size 100
  m11022  hub G3 (star 10), Frozen Seaway, Apex Tidal (em 120, spawn byte +0xF 9), 73 / 109 / 87, size 130, "Advanced:"
  m11016  hub G3 (star 10), Arena, "hunt all": Zinogre + Tidal, then Tigrex + Gravios, all 37 / 104 / 82
  m22002  Arena "Grudge Match" (quest type 1): preset gear, time ranks. NOT PORTED, as Stygian's m21003 and Black Gravios'
          m21006 (Stygian's notes/quests.md 1): notes/plan.md "Quests".
She is G rank only in 4U (C: her carve and break tables hold nothing else), so all of them stay G rank here.

Placement: as Monoblos' (the user, 2026-11-05: single player and multiplayer versions, hub HP differs): m10822 and m11022 as
village ★10 G (single player, tier 5) and as hub quests, m11016 as a hub quest. Hub ranks: m10822 -> G3, GU's rank of its solo
Najarala hunt q11339 (C); m11022 -> G4 (one above: "Advanced" in 4U's top rank); m11016 -> G4, where GU's own version of the
same four-monster quest sits (q11480, C: Arena, hunt all, Zinogre + Najarala, then Tigrex + Gravios).

Sources (C unless marked):
  GU template  per quest (QUESTS): stars / class bytes, board, start area, flags, +0x1A, money, questPlus, GMD unk word. Hub:
               q11330 (G3) / q11433 (G4), plain hunts on the Frozen Seaway, so no re-staging; q11480 for m11016. Village: GU
               has no village ★10 G quest on the Frozen Seaway (the stage's village quests are tier 3: q804 q901 q1021): q1012,
               GU's plain G single hunt, re-staged 2 -> 14, with the small monsters of q1021 (village ★10, stage 14), as
               Monoblos' m01018.
  Stat rows    m10822: r = 1 (her 4U rows equal 4U Najarala's m10831 at the same rank), so GU's rows at the placement: q1012's
               51 / 97 / 85 (every village ★10 G single hunt), q11339's Najarala 102 / 108 / 96. m11016: GU's own Najarala
               record in q11480 (65 / 109 / 96; 4U gives all four monsters one row, GU its own rows: both kept as GU's).
               m11022: 4U has no Najarala at G3 to divide by, and its rows mean "Apex": r (S) = its rows over the median of
               4U's other plain single hub hunts at star 10 (adv_ratio: HP 2.29 / 2.05 = 1.117, attack 8.2 / 7.9 = 1.038, the
               ten Apex hunts of that star all hold 2.29-2.35 / 7.6-8.2), so that the quest stays stronger than the plain
               ones without its Apex state (a DEVIATION, below). Base q1012's rows, q11433's (G4: 107 / 108 / 97). Target =
               base x r, the nearest GU row not below it. The other row is the base's.
               Her base HP (dttune, +500 on GU Najarala's as in 4U) comes on top in all of them.
  Boss record  Tidal = the stand-in Najarala (allocations.toml standin_id 0x44), swapped to 0x144 at spawn by module/main.c;
               aura 0; size from 4U; restore / byte 8 / size table / stamina = the base record's.
  4U quest     text (5 languages), minutes, objectives, spawns (area, point, rotation), reward rows A / B / subquest.
  Subquest     4U 0x204 {em, part 2} "head" / {em, part 5} "tail" (C: the quests' own texts) -> GU type 8 {real ID, code}: GU
               Najarala's codes 1 head (q813 q10229), 3 back (q10511), 4 tail (q410 q11215), 13 head + back, 14 head + tail
               (C: GU's subquest texts). m11016 has none (4U), so none here (GU's q11480 has its own: left out).
  Rewards      her own materials (items_em068_01.py, appended IDs), the other 4U items by English name in GU itemData_eng (a 4U
               item GU lacks is left out, logged). Reward slots 3 / 4 = GU's empty row rem_000000.
  Supply box   village: the 4U quest's (quest4u.supp_4u), one Map at the start (map_only_start, the user 2026-11-05 and 2026-11-07;
               C: all 343 GU village quests hold 0 or 1, all 548 hub quests 0 or 4, and her 4U quests, hub quests, hold 4). Hub:
               the template's box and +0x58 delivery groups (4 Maps, 4 x supplies, Hot Drinks on the Frozen Seaway: C).
  Spawn        the template's boss setEmMain record with 4U's area and floats (4U 4 -> GU 14 is 4U's geometry, S, Stygian's
               notes/quests.md 2). m11016: GU's own four records of q11480, unchanged (GU's version of this quest; 4U 11 -> GU 9
               has no geometry check, and two of 4U's points differ from GU's). Small monsters: the template's or esl_tpl's.
  Apex         em 120 in m11022 is her Apex form (4U W+0x7e80 bit 32, 4U 0x91 AI branch): GU has no Apex state, so it runs as
               the normal Tidal (a DEVIATION, as the frenzy states of the earlier ports): logged per quest.
"""
import argparse, os, re, statistics, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, gear4u, gmd, quest4u   # noqa: E402
sys.path.insert(0, HERE)
import items_em068_01               # noqa: E402
from items4u import EXE, EXE_BASE, text_4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('tidal_najarala')
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x144; Najarala 0x44, swapped at spawn
EM_4U = (93, 120)                   # Tidal, Apex Tidal (one class, C)
PARTNER_GU = {48: 0x39, 11: 0x20, 40: 0x5}     # m11016: Zinogre, Tigrex, Gravios (C: 4U em numbers against q11480's records)
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {4: 14, 11: 9}           # 4U Frozen Seaway / Arena -> GU stage (Stygian's notes/quests.md 2)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: her cell (module/icons.c; 4U +0xE8 = 103)
REM_EMPTY = struct.pack('<fI', 1.0, 1) + bytes(176)     # GU's rem_000000 (184 B, no group; C: q10706)
G_TIER = 5                          # GU questData +0x13 rank tier (C: village ★10 G 5, hub G 5)
URGENT = 0x1                        # questData +0x16F bit 0 = an urgent (key) quest (Monoblos' builder)
# Quests (k = index in allocations.toml quests):
#   num   4U quest
#   tpl   GU template (same placement and kind)
#   base  (GU quest, em)  the GU boss record whose rows, difficulty, size table and stamina she takes
#   sub   GU code of the 4U subquest's part (None: the 4U quest has none)
#   advanced  her rows = base x adv_ratio (m11022)
#   tpl_stage the template sits on another stage (its stage byte is replaced); esl_tpl = the GU quest whose small
#             monster sets are used instead of the template's (one on the quest's own stage)
#   supp_tpl  the GU hub quest whose supply box and delivery groups replace the 4U quest's
#   gu_bosses the template is GU's version of the quest: its boss records and setEmMain files stay (Najarala = stand-in)
# Only the quests 4U has, where 4U has them (the user, 2026-11-08): all three are guild quests -> hub only. 0.2.7's village
# copies of m10822 / m11022 (1060 / 1061) are gone; Monoblos' village / hub pairs were the exception (4U has no multiplayer quest of his).
QUESTS = [
    # --- 4U guild quests: hub G3 / G4
    dict(k=0, num=10822, tpl=11330, base=(11339, 0x44), supp_tpl=11330, sub=1),
    dict(k=1, num=11022, tpl=11433, base=(11433, 0x2a), supp_tpl=11433, sub=4, advanced=True),
    # m11016 (Arena, 11497 until 0.2.8) is out: no Arena quests (the user, 2026-11-08). Its row was
    # dict(num=11016, tpl=11480, base=(11480, 0x44), supp_tpl=11480, sub=None, gu_bosses=True); gu_bosses / PARTNER_GU serve only it.
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
    """4U boss spawn records of every list of the table at +0x28 (u32 list pointers, up to 4, 0 = none), 0x28 B each closed
    by em 0xffffffff, in list order: [(em, area, (x, y, z, rot), +0xF)]"""
    tbl = struct.unpack_from('<I', q, 0x28)[0]
    out = []
    for i in range(4):
        if tbl + 4 * i + 4 > len(q): break
        rec = struct.unpack_from('<I', q, tbl + 4 * i)[0]
        if not rec or rec + 4 > len(q): continue
        while rec + 4 <= len(q) and struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
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
    """4U boss stat block i (+0x34 + 8 i, one per spawn, in spawn order): (size %, HP, attack, other row)"""
    o = STATS_4U + 8 * i
    return (struct.unpack_from('<H', q, o)[0],) + tuple(q[o + 3:o + 6])


def adv_ratio(exe, q4):
    """(r HP, r attack): the Advanced quest's 4U rows over the median of 4U's plain single hub hunts of its star (hub quest
    type 3, IDs 10000.., one boss, spawn byte +0xF 0)"""
    r4 = lambda row: struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
    star, hp, atk = q4[0xC2], [], []
    for arc in ('quest00.arc', 'quest01.arc'):
        for name, v in arc_files(open(os.path.join(Q4U_DIR, arc), 'rb').read()).items():
            q = v[1]
            if not re.search(r'm1\d{4}$', name) or q[4:8] != b'v005' or q[0xA0] != 3 or q[0xC2] != star: continue
            sp = spawns_4u(q)
            if len(sp) == 1 and not sp[0][3]:
                s = stats_block(q, 0)
                hp.append(r4(s[1])[0])
                atk.append(r4(s[2])[1])
    assert hp, 'no plain hunts at star %d' % star
    s = stats_block(q4, 0)
    return r4(s[1])[0] / statistics.median(hp), r4(s[2])[1] / statistics.median(atk), len(hp)


def stat_rows(R, exe, q4, b, advanced):
    """(HP, attack, other) rows and the trace (r HP, r attack, target HP, target attack, rows' values), b = the GU base record"""
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    rows = [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]
    if not advanced:
        return (b[4], b[5], b[6]), (1.0, 1.0, rows[b[4]][0], rows[b[5]][1], rows[b[4]][0], rows[b[5]][1])
    r_hp, r_atk, n = adv_ratio(exe, q4)
    print('adv_ratio: %d plain hunts at the star: r HP %.3f, r attack %.3f' % (n, r_hp, r_atk))
    assert r_hp >= 1 and r_atk >= 1, (r_hp, r_atk)

    def pick(col, base_row, r):
        base = rows[base_row][col]      # 1e-3: the table's 8.2 is the target 7.9 x 8.2 / 7.9, not below it
        return min((abs(rows[k][col] - base * r), k) for k in range(len(rows)) if rows[k][col] >= base * r - 1e-3)[1], base * r
    hp, t_hp = pick(0, b[4], r_hp)
    atk, t_atk = pick(1, b[5], r_atk)
    return (hp, atk, b[6]), (r_hp, r_atk, t_hp, t_atk, rows[hp][0], rows[atk][1])


def objectives_4u(q):
    """4U main objectives (+0xCB count, {u32 type, u16 target, u16 count} at +0xCC / +0xD4; 1 = hunt) and the subquest record
    at +0xDC (0x204 = wound / sever {em, 4U part code})"""
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
    """gu_item(4U id) -> GU id: her own materials (items_em068_01.py, appended IDs), else by English name (the first id of
    the name), None when GU has no such item"""
    names4 = text_4u('eng')[0]
    by_name = {n: ids[0] for n, ids in names.items()}
    ours = {k: ALLOC['items'][0] + i for i, k in enumerate(items_em068_01.ITEMS_4U)}

    def gu_item(k):
        n = names4[k]
        if k in ours: return ours[k]
        if n in by_name: return by_name[n]
        print('reward: 4U %d %s has no GU item (left out)' % (k, n))
        return None
    return gu_item


def map_only_start(supp, map_id, m4):
    """GU supp bytes with one Map at the start, as GU's village boxes (docstring: Supply box): the box's other start items go
    to the front of delivery group 1 (the first slot whose group byte is 1; slots 32.. = group 4 stay), the extra Maps go. As
    Monoblos' builder, plus the one Map (Shrouded Nerscylla's the same)"""
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


def set_name(stage, k):
    """setEmMain names, one content per name (asserted over the quests built), none in GU's quests (C, 2026-11-06: GU uses
    b_mNNem068_00 only): hers 60 + k"""
    assert k < 10, k
    return 'b_m%02dem068_%02d' % (stage, 60 + k)


def build(R, exe, gu_item, names, out, spec, hp_table=None):
    k, num, tpl_id = spec['k'], spec['num'], spec['tpl']
    qid = ALLOC['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    q4 = quest_4u(num)
    sp = spawns_4u(q4)
    ems = [s[0] for s in sp]
    me = [i for i, e in enumerate(ems) if e in EM_4U]
    assert len(me) == 1 and all(e in EM_4U or e in PARTNER_GU for e in ems), (m4, ems)
    me = me[0]
    apex = [s[3] for s in sp if s[0] in EM_4U and (s[0] == 120 or s[3])]
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    base_qd = quest_data(R, spec['base'][0])
    objs, sub4 = objectives_4u(q4)

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
    if spec.get('gu_bosses'):               # GU type 3 = all large monsters (4U's text; q11480 itself), target / count 0
        assert qd[0x1F] == 3, (tpl_id, 'not a hunt-all quest')
        qd[0x1F:0x29] = bytes(10)
        qd[0x1F] = 3
        assert set(e for _, e, _ in objs) <= set(ems), (m4, objs, ems)
    else:
        assert qd[0x1F] == 1, (tpl_id, 'not a hunt')
        assert len(objs) == 1 and objs[0][0] == 1 and objs[0][1] in EM_4U and objs[0][2] == 1, (m4, objs)
        qd[0x1F:0x29] = bytes(10)
        struct.pack_into('<BHH', qd, 0x1F, 1, EM_ID, 1)
    if spec['sub'] is not None:             # GU code of the 4U part, on her (real ID)
        assert sub4[0] == 0x204 and sub4[1] in EM_4U, (m4, 'the 4U subquest is not her wound / sever', sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, EM_ID, spec['sub'])
    else:
        assert not sub4[0], (m4, 'the 4U quest has a subquest', sub4)
        qd[0x29:0x2E] = bytes(5)
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

    # boss records: hers = the stand-in. gu_bosses: GU's own four, in 4U's spawn order (checked); else the computed rows
    b = boss_record(base_qd, spec['base'][1])
    (hp, atk, other), trace = stat_rows(R, exe, q4, b, spec.get('advanced', False))
    if hp_table is not None: hp = hp_table
    size = stats_block(q4, me)[0]
    if spec.get('gu_bosses'):
        recs = [struct.unpack_from('<HBBBBBBBHBB', qd, 0x64 + 13 * i) for i in range(5)]
        gids = [r[0] for r in recs if r[0]]
        want = [BOSS_ID if e in EM_4U else PARTNER_GU[e] for e in ems]
        assert gids == want, (m4, 'GU\'s bosses are not 4U\'s, in order', gids, want)
        assert all(stats_block(q4, i)[0] == recs[i][8] for i in range(len(ems))), (m4, 'sizes differ from GU\'s')
        if hp_table is not None:
            r = recs[me]
            struct.pack_into('<HBBBBBBBHBB', qd, 0x64 + 13 * me, r[0], r[1], r[2], r[3], hp, r[5], r[6], r[7], r[8], r[9], r[10])
        icons = bytearray(qd[0xD6:0xDB])
        assert icons[me] and all(icons[:len(ems)]), (tpl_id, 'board icons', icons)
        icons[me] = ICON                 # her cell; the partners' are GU's own (4U's order)
        qd[0xD6:0xDB] = bytes(icons)
    else:
        recs = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, b[3], hp, atk, other, b[7], size, b[9], b[10])
        qd[0x64:0x64 + 65] = recs + bytes(65 - len(recs))
        qd[0xD6:0xDB] = bytes([ICON, 0, 0, 0, 0])
    for i, lang in enumerate(quest4u.QLANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))

    # --- questLink + resources
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    res = []
    if spec.get('gu_bosses'):            # GU's records and names, unchanged
        for n in sorted(set(tnames[:5])):
            res.append(('quest\\boss\\setEmMain\\' + n, T_SET, tpl['quest\\boss\\setEmMain\\' + n][1]))
        set_refs = b''.join(ref(T_SET, n) for n in tnames[:5])
    else:                                # one setEmMain: the template's first record with 4U's area and floats
        se = bytearray(tpl['quest\\boss\\setEmMain\\' + tnames[0]][1])
        x, y, z, rot = sp[me][2]
        struct.pack_into('<I4f', se, 0x0C, sp[me][1], rot, x, y, z)
        n = set_name(stage, k)
        assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
        res += [('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)),
                ('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1])]
        set_refs = ref(T_SET, n) + ref(T_SET, 'b_m00em000_00') * 4
    esl_src, esl_names = tpl, tnames
    if spec.get('esl_tpl'):              # small monsters of a GU quest on the quest's own stage
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
    if spec['sub'] is not None and ptr(SUB_ROW_4U) and ptr(SUB_ROW_4U) != ptr(REWARD_ROWS_4U[0]):
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
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    qd = bytes(qd)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, objective %s, sub %s; boss %#x rows %s size %d '
          '(r HP %.3f atk %.3f, target %.2f / %.2f -> %.2f / %.2f); spawns %s%s' % (
              qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], qd[0x1F:0x24].hex(' '), qd[0x29:0x2E].hex(' '), BOSS_ID,
              (hp, atk, other) if not spec.get('gu_bosses') else tuple(boss_record(qd, BOSS_ID)[4:7]), size, *trace,
              [s[1] for s in sp], '; 4U Apex state (em 120, +0xF %s) DROPPED (deviation)' % apex if apex else ''))


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
