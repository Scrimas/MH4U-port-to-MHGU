"""build_em067_01_quest.py : the Tigerstripe Zamtrios quest for MHGU, EXTRA G1 Hub quest 11493 = 4U m10821 "Grand
Finals Confrontation" (4U data: notes/content-data.md section 4). 4U m10830 "Advanced: Tiger-sharq" is not ported:
its Tigerstripe spawns frenzied (spawn record +0xF = 1, subquest "Suppress its Frenzy (2x)"), and GU has no frenzied
monsters (user, 2026-10-20: drop it unless importing the frenzy is easy; it is 4U's whole frenzy system).

  build_em067_01_quest.py [--hp-table N] [--out DIR]

Writes (default DIR = monsters/tigerstripe_zamtrios/romfs): the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write). All new files; the quest shows up through the module's quest_group hook
(allocations.toml quest_slots).

Sources:
  GU template  q0011111 (G1 Hub Dunes, stage 5, every board, Diablos + Monoblos): questData fields, supply box,
               questPlus, slot 2 / 3 rewards (GU's G1 Hub coin tables), GMD unk word. Its second monster, second
               objective and small monsters are dropped.
  4U quest     m10821 (loc/data/quest01.arc, v005): 5-language text, fee 1100z, reward 11100z, sub 3700z, 50 min,
               subquest "Wound T.Zamtrios's dorsal fin", spawn (area 4, (-996, 57, 2142)), stat rows 60 / 100 / 82,
               reward rows A / B (row A = the subquest's).
Spawn: GU's Dunes area 4 (m05a04d) is 4U's geometry: its floor under (-996, 2142) is at y 57.2 (4U y 57).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tigerstripe_zamtrios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, items_em067_01, quest4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, LANGS, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U)
from romfs import RomFS             # noqa: E402

ALLOC = alloc.monster('tigerstripe_zamtrios')
QID = ALLOC['quests'][0]
EM_ID, BOSS_ID = ALLOC['em_id'], ALLOC['standin_id']   # 0x143; Zamtrios 0x43, swapped to 0x143 at spawn (main.c)
SRC_4U, ARC_4U, STAGE_4U, EM_4U = 'm10821', 'quest01.arc', 17, 92
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
TPL = 11111
STAGE = 5                         # GU Dunes = 4U Dunes (stage 17), user's choice
# GU subquest code: decimal digits, each a break group (GU Zamtrios quests: 1 head, 2 top fin, 14 head + tail);
# 4U's dorsal fin = 4U break group 3 = GU group 2 (tools/items_em067_01.py)
SUB_CODE = 2
REMS = ('rem_921821', 'rem_922821')          # rows A / B (4U em 92, row, quest 10821): no GU quest uses the names
SETNAME = 'b_m%02dem067_00' % STAGE          # no GU quest has Zamtrios on the Dunes (name unused, checked)
ICON = ALLOC['donor_index'] + 1              # board icon: GU's Zamtrios (UI index 56 + 1, as q0011207's 57)


def spawn_4u(q):
    """4U boss spawn record ([+0x28] -> list of record pointers): (em, area, (x, y, z, w))"""
    rec = struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    return struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help="boss vital (HP) table byte, default the 4U quest's (60 = HP x 1.9); "
                                                 'a lower table = shorter tests')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    a = ap.parse_args()
    sid = '%07d' % QID

    R = RomFS(paths.GU_ROMFS)
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL))
    q4 = arc_files(open(os.path.join(Q4U_DIR, ARC_4U), 'rb').read())['loc\\quest\\' + SRC_4U][1]
    assert q4[4:8] == b'v005' and struct.unpack_from('<H', q4, 0xC0)[0] == int(SRC_4U[1:]) and q4[0xC4] == STAGE_4U
    em4, area4, pos4 = spawn_4u(q4)
    assert em4 == EM_4U and q4[spawn_rec_flag(q4)] == 0, 'not a plain Tigerstripe spawn'

    # --- questData: the template's (G1 = stars 11, every board, Dunes, start area, +0x1A, flags), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % TPL][1])
    assert len(qd) == 329 and qd[0x12] == 11 and qd[0x14] == STAGE and qd[0x11] == 10
    tpl_reward, tpl_hrp = struct.unpack_from('<I', qd, 0x39)[0], struct.unpack_from('<I', qd, 0x4D)[0]
    struct.pack_into('<I', qd, 0x0C, QID)
    # quest type 1 (single large-monster hunt, as Gogmazios' quests and 196 GU one-boss hunts; the template's 0): the
    # objective init 0x3abea4 gives a type-1 hunt flag 0x100, which ends the quest when the kill completes it; type 0
    # ends through the boss records, whose ID is the stand-in, not 0x143 (test 2026-10-21: kill counted, no clear)
    qd[0x10] = 1
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # 50 min (4U)
    qd[0x1F] = 1; struct.pack_into('<HH', qd, 0x20, EM_ID, 1)
    qd[0x24:0x29] = bytes(5)                               # no second objective (the template's Monoblos)
    # subquest {u8 type, u16 target, u16 code}: type 8 = wound / sever; target = the real ID like the objective
    qd[0x29] = 8; struct.pack_into('<HH', qd, 0x2A, EM_ID, SUB_CODE)
    # money / points: 4U fee, reward, sub reward (= reward / 3); academy = reward x 0.08 (G), sub academy = sub / 10,
    # HRP = reward x the template's HRP per zenny (700 / 12600), sub HRP = HRP / 10 (as the template)
    fee, reward, sub = struct.unpack_from('<III', q4, 0xA4)
    assert sub * 3 == reward, (fee, reward, sub)
    hrp = int(round(reward * tpl_hrp / tpl_reward, -1))
    struct.pack_into('<IIIIIIIII', qd, 0x31, fee, 0, reward, sub, int(reward * 0.08), 0, sub // 10, hrp, hrp // 10)
    # boss record {u16 id, subtype, aura, restore, HP / attack / other rows, byte 8, u16 size %, size table, stamina}:
    # the stand-in Zamtrios, the 4U quest's stat rows (tools/quest4u.py stats_4u); byte 8 = 2, size table 5 and
    # stamina 3 as GU's own G Zamtrios hunts (11207 / 11227 / 11304; byte 8's meaning not traced); size 100 % (4U)
    hp, atk, other = quest4u.stats_4u(q4, R)
    if a.hp_table is not None: hp = a.hp_table
    assert struct.unpack_from('<H', q4, quest4u.STATS_4U)[0] == 100
    boss = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, 1, hp, atk, other, 2, 100, 5, 3)
    qd[0x64:0x64 + 65] = boss + bytes(52)
    qd[0xD6:0xDB] = bytes([ICON, 0, 0, 0, 0])
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))
    qd = bytes(qd)

    # --- questLink + resources: setEmMain = the template's record with 4U's area and position (no rotation in 4U)
    se = bytearray(tpl['quest\\boss\\setEmMain\\b_m%02dem017_00' % STAGE][1])
    struct.pack_into('<I4f', se, 0x0C, area4, 0.0, *pos4[:3])
    res = [('quest\\boss\\setEmMain\\' + SETNAME, T_SET, bytes(se)),
           ('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]),
           ('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1])]
    # rewards: rows A / B from 4U (items: tools/items_em067_01.py), slots 2 / 3 the template's (G1 Hub coins),
    # slot 4 (subquest) = row A's table, as in 4U (its subquest list is row A's)
    rems = {name: quest4u.rem_4u(q4, row, items_em067_01.gu_item) for row, name in zip(REWARD_ROWS_4U, REMS)}
    assert struct.unpack_from('<I', q4, SUB_ROW_4U)[0] == struct.unpack_from('<I', q4, REWARD_ROWS_4U[0])[0], \
        'the 4U subquest rewards are not row A'
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % TPL][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem, supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    REM = [REMS[0], REMS[1], tnames[10], tnames[11], REMS[0]]
    for r in sorted(set(REM)):
        res.append(('quest\\rem\\' + r, T_REM, rems[r] if r in rems else tpl['quest\\rem\\' + r][1]))
    res.append(('quest\\supp\\supp_' + sid, T_SUPP, tpl['quest\\supp\\supp_%07d' % TPL][1]))
    plus = tnames[14]
    res.append(('quest\\plus\\questPlus_' + plus, T_PLUS, tpl['quest\\plus\\questPlus_' + plus][1]))
    link = tlink[:8] + ref(T_SET, SETNAME) + ref(T_SET, 'b_m00em000_00') * 4 + ref(T_ESL, 'z_m00d_000') * 3
    link += b''.join(ref(T_REM, r) for r in REM) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, TPL, sid, t4)
    quest4u.write(a.out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d: stage %d, %d min, em %#x (stand-in %#x), rows %d/%d/%d, spawn area %d %s, "%s"' % (
        QID, qd[0x14], qd[0x16], EM_ID, BOSS_ID, hp, atk, other, area4, pos4[:3], t4['eng'][0]))


def spawn_rec_flag(q):
    """offset of the 4U spawn record's byte +0xF (1 = frenzied in m10830)"""
    return struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0] + 0xF


if __name__ == '__main__':
    main()
