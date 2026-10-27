"""build_em067_01_quest.py : the Tigerstripe Zamtrios quest for MHGU, EXTRA G3 Hub quest 11493 = 4U m10821 "Grand
Finals Confrontation" (4U data: notes/content-data.md section 4). Rank: G3, a deviation (user 2026-10-27: 4U's G1 sits
below GU's own Zamtrios, G2, and Hyper Zamtrios, G3), so the rank values are GU's G3 ones (Sources). 4U m10830 "Advanced: Tiger-sharq" is not ported:
its Tigerstripe spawns frenzied (spawn record +0xF = 1, subquest "Suppress its Frenzy (2x)"), and GU has no frenzied
monsters (user, 2026-10-20: drop it unless importing the frenzy is easy; it is 4U's whole frenzy system).

  build_em067_01_quest.py [--hp-table N] [--out DIR]

Writes (default DIR = monsters/tigerstripe_zamtrios/romfs): the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write). All new files; the quest shows up through the module's quest_group hook
(allocations.toml quest_slots).

Sources:
  GU template  q0011327 (G3 Hub Dunes, stage 5, one hunt): questData fields (stars 13), money (fee 1400z, reward
               13500z, sub 4200z, academy / HRP), supply box, questPlus, slot 2 / 3 rewards (GU's G3 Hub coin
               tables), GMD unk word. Its monster and small monsters are dropped.
  GU rows      q0011330 (G3 Hub, Hyper Zamtrios alone, GU's only G3 Zamtrios hunt): stat rows 102 / 108 / 96 (HP x3.6,
               attack x7.9, defense x0.75), without the Hyper aura. 4U's were 60 / 100 / 82 (HP x1.9, G1).
  4U quest     m10821 (loc/data/quest01.arc, v005): 5-language text, 50 min, subquest "Wound T.Zamtrios's dorsal
               fin", spawn (area 4, (-996, 57, 2142)), reward rows A / B (row A = the subquest's). Not used: its G1
               money (fee 1100z, reward 11100z) and stat rows.
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
TPL = 11327                       # G3 Hub Dunes, one hunt
ROWS_GU = 11330                   # GU's G3 Zamtrios hunt (Hyper): the stat rows
STAGE = 5                         # GU Dunes = 4U Dunes (stage 17), user's choice
# GU subquest code: decimal digits, each a break group (GU Zamtrios quests: 1 head, 2 top fin, 14 head + tail);
# 4U's dorsal fin = 4U break group 3 = GU group 2 (tools/items_em067_01.py)
SUB_CODE = 2
REMS = ('rem_921821', 'rem_922821')          # rows A / B (4U em 92, row, quest 10821): no GU quest uses the names
SETNAME = 'b_m%02dem067_00' % STAGE          # no GU quest has Zamtrios on the Dunes (name unused, checked)
ICON = alloc.board_byte(ALLOC['ui_icon'])   # board icon: Tigerstripe's cell (module/icons.c; 4U m10821 +0xE8 = 102 = icon 101 + 1,
                                             # its second icon 84 is a label cell, not a monster)


def spawn_4u(q):
    """4U boss spawn record ([+0x28] -> list of record pointers): (em, area, (x, y, z, w))"""
    rec = struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    return struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help="boss vital (HP) table byte, default GU's G3 Zamtrios hunt's (102 = "
                                                 'HP x 3.6); a lower table = shorter tests')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    a = ap.parse_args()
    sid = '%07d' % QID

    R = RomFS(paths.GU_ROMFS)
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL))
    q4 = arc_files(open(os.path.join(Q4U_DIR, ARC_4U), 'rb').read())['loc\\quest\\' + SRC_4U][1]
    assert q4[4:8] == b'v005' and struct.unpack_from('<H', q4, 0xC0)[0] == int(SRC_4U[1:]) and q4[0xC4] == STAGE_4U
    em4, area4, pos4 = spawn_4u(q4)
    assert em4 == EM_4U and q4[spawn_rec_flag(q4)] == 0, 'not a plain Tigerstripe spawn'

    # --- questData: the template's (G3 = stars 13, Hub, Dunes, start area, +0x1A, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % TPL][1])
    assert len(qd) == 329 and qd[0x12] == 13 and qd[0x14] == STAGE and qd[0x11] == 10
    struct.pack_into('<I', qd, 0x0C, QID)
    # clear rule +0x1d (C): quest+0xe8 = [1, 2, 3][+0x1d] (table 0x162a75a, init 0x3abe54); the clear check 0x3a027c
    # (per frame while state 2) clears on rule 1 when objective 0 is done (flags & 0x60 == 0x20), rule 2 needs
    # objectives 0 AND 1. One hunt = 0, as this template (tests 2026-10-21 with a two-hunt template: the kill
    # completed objective 0, the quest waited for the dropped objective 1).
    assert qd[0x1D] == 0
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # 50 min (4U)
    qd[0x1F] = 1; struct.pack_into('<HH', qd, 0x20, EM_ID, 1)
    qd[0x24:0x29] = bytes(5)                               # no second objective (the template's Monoblos)
    # subquest {u8 type, u16 target, u16 code}: type 8 = wound / sever; target = the real ID like the objective
    qd[0x29] = 8; struct.pack_into('<HH', qd, 0x2A, EM_ID, SUB_CODE)
    # money / points (+0x31: fee, 0, reward, sub reward, academy, 0, sub academy, HRP, sub HRP): the template's (G3)
    # boss record {u16 id, subtype, aura, restore, HP / attack / other rows, byte 8, u16 size %, size table, stamina}:
    # the stand-in Zamtrios, GU's G3 Zamtrios rows (ROWS_GU) with aura 0; byte 8 = 2, size table 5 and stamina 3 as
    # GU's own G Zamtrios hunts (11207 / 11227 / 11304 / 11330; byte 8's meaning not traced); size 100 % (4U)
    hp, atk, other = gu_rows(R)
    if a.hp_table is not None: hp = a.hp_table
    assert struct.unpack_from('<H', q4, quest4u.STATS_4U)[0] == 100
    boss = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, 1, hp, atk, other, 2, 100, 5, 3)
    qd[0x64:0x64 + 65] = boss + bytes(52)
    qd[0xD6:0xDB] = bytes([ICON, 0, 0, 0, 0])
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))
    qd = bytes(qd)

    # --- questLink + resources: setEmMain = the template's record with 4U's area and position (no rotation in 4U)
    se = bytearray(tpl['quest\\boss\\setEmMain\\b_m%02dem044_00' % STAGE][1])
    struct.pack_into('<I4f', se, 0x0C, area4, 0.0, *pos4[:3])
    res = [('quest\\boss\\setEmMain\\' + SETNAME, T_SET, bytes(se)),
           ('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]),
           ('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1])]
    # rewards: rows A / B from 4U (items: tools/items_em067_01.py), slots 2 / 3 the template's (G3 Hub coins),
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


def gu_rows(R):
    """(HP, attack, other) stat rows of GU's G3 Zamtrios hunt ROWS_GU: its boss record (questData +0x64) is the Hyper
    Zamtrios (id 0x43, aura byte 1)"""
    qd = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % ROWS_GU))['loc\\quest\\questData\\questData_%07d' % ROWS_GU][1]
    em, _, aura = struct.unpack_from('<HBB', qd, 0x64)
    assert qd[0x12] == 13 and em == 0x43 and aura == 1, (qd[0x12], em, aura)
    return tuple(qd[0x64 + 5:0x64 + 8])


def spawn_rec_flag(q):
    """offset of the 4U spawn record's byte +0xF (1 = frenzied in m10830)"""
    return struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0] + 0xF


if __name__ == '__main__':
    main()
