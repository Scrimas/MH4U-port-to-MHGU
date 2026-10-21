"""build_dalamadur_quest.py : Dalamadur's first quest for MHGU, EXTRA quest 11494 = 4U m10709 "Speartip Menace"
(notes/phase0.md, Quests). Goal D test form: GU's Sanctuary (stage 18) stands in for Speartip Crag until the arena
port (goal E), and the reward rows are GU's generic ones until the items exist (goal F).

  build_dalamadur_quest.py [--hp-table N] [--out DIR]

Writes (default DIR = monsters/dalamadur/romfs): the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write). The quest shows up through the module's quest_group hook (allocations.toml
quest_slots).

Sources:
  GU template  q0011425 (G4 Sanctuary, Amatsu, every board): questData fields, supply box, questPlus, the generic
               reward rows rem_530008 / rem_530034 (its slots 3 / 4), GMD unk word. Its subquest is dropped.
  4U quest     m10709 (loc/data/quest01.arc, v005): 5-language text, fee 2200z, reward 21000z, 50 min, two bosses
               in area 1, both at the arena origin with no rotation: em024 (head) and em083 (tail), stat rows 37 / 72 /
               76 for both. Objective: hunt em024. Its subquest "Wound the Dalamadur's head" (7000z) is left out until
               the part breaks exist (goal D).
Bosses (GU precedent: Ahtal-Ka quests 11432 / 1011030 list [0x58, 0x57], objective 0x58): [head stand-in, tail
stand-in] (allocations.toml standin_id, swapped at spawn by module/main.c), objective the head's real em ID. Both at
one point, as in 4U: every Dalamadur motion moves bone 0 only (class-study.md), so the two halves form one body
around their common origin. Test spawn: Amatsu's point in the Sanctuary's area 1 (b_m18em058_00).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, quest4u               # noqa: E402
from quest4u import arc_files, text4u, ref, LANGS, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS   # noqa: E402
from romfs import RomFS             # noqa: E402

HEAD, TAIL = alloc.monster('dalamadur'), alloc.monster('dalamadur_tail')
QID = HEAD['quests'][0]
SRC_4U, ARC_4U, STAGE_4U, EMS_4U = 'm10709', 'quest01.arc', 8, (24, 83)
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
TPL = 11425
STAGE = 18                        # the Sanctuary until Speartip Crag (goal E)
TPL_SET = 'b_m18em058_00'         # Amatsu's spawn in area 1: rotation -110, (2250, 30, 522)
SETNAMES = ('b_m%02dem090_00' % STAGE, 'b_m%02dem091_00' % STAGE)    # no GU quest uses these names (no em090 / 91)
ICON = HEAD['donor_index'] + 1    # board icon: Kushala's until the icons (goal F)


def spawns_4u(q):
    """4U boss spawn records, 0x28 B each from [+0x28] -> first record, closed by em 0xffffffff:
    [(em, area, (x, y, z, rotation))]"""
    out, rec = [], struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
        out.append((struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10)))
        rec += 0x28
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help="boss vital (HP) table byte, default the 4U quest's (37); a lower "
                                                 'table = shorter tests')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    a = ap.parse_args()
    sid = '%07d' % QID

    R = RomFS(paths.GU_ROMFS)
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL))
    q4 = arc_files(open(os.path.join(Q4U_DIR, ARC_4U), 'rb').read())['loc\\quest\\' + SRC_4U][1]
    assert q4[4:8] == b'v005' and struct.unpack_from('<H', q4, 0xC0)[0] == int(SRC_4U[1:]) and q4[0xC4] == STAGE_4U
    sp = spawns_4u(q4)
    assert [s[0] for s in sp] == list(EMS_4U) and all(s[1] == 1 and s[2] == (0, 0, 0, 0) for s in sp), sp

    # --- questData: the template's (G4, every board, start area 0, +0x1A, flags), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % TPL][1])
    assert len(qd) == 329 and qd[0x14] == STAGE and qd[0x11] == 10 and qd[0x1D] == 0   # clear rule: objective 0
    tpl_reward, tpl_hrp = struct.unpack_from('<I', qd, 0x39)[0], struct.unpack_from('<I', qd, 0x4D)[0]
    struct.pack_into('<I', qd, 0x0C, QID)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # 50 min (4U)
    qd[0x1F] = 1; struct.pack_into('<HH', qd, 0x20, HEAD['em_id'], 1)
    qd[0x24:0x29] = bytes(5)
    qd[0x29:0x2E] = bytes(5)                               # no subquest yet (4U: wound the head, goal D breaks)
    fee, reward, sub = struct.unpack_from('<III', q4, 0xA4)
    hrp = int(round(reward * tpl_hrp / tpl_reward, -1))
    struct.pack_into('<IIIIIIIII', qd, 0x31, fee, 0, reward, 0, int(reward * 0.08), 0, 0, hrp, 0)
    # boss records {u16 id, subtype, aura, restore, HP / attack / other rows, byte 8, u16 size %, size table,
    # stamina}: the stand-ins, the 4U quest's stat rows (both bosses share them in 4U), the template's other bytes
    hp, atk, other = quest4u.stats_4u(q4, R)
    if a.hp_table is not None: hp = a.hp_table
    t = struct.unpack_from('<HBBBBBBBHBB', qd, 0x64)
    boss = lambda em: struct.pack('<HBBBBBBBHBB', em, t[1], t[2], t[3], hp, atk, other, t[7], 100, t[9], t[10])
    qd[0x64:0x64 + 65] = boss(HEAD['standin_id']) + boss(TAIL['standin_id']) + bytes(39)
    qd[0xD6:0xDB] = bytes([ICON, 0, 0, 0, 0])
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))
    qd = bytes(qd)

    # --- questLink + resources: setEmMain = Amatsu's record (area 1, its point), 4U's rotation (0) for both halves
    se = bytearray(tpl['quest\\boss\\setEmMain\\' + TPL_SET][1])
    assert struct.unpack_from('<I', se, 0x0C)[0] == 1
    struct.pack_into('<f', se, 0x10, 0.0)
    res = [('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)) for n in SETNAMES]
    res += [('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]),
            ('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1])]
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % TPL][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    REM = [tnames[10], tnames[11], tnames[10], tnames[11], tnames[10]]    # generic rows until the items (goal F)
    for r in sorted(set(REM)):
        res.append(('quest\\rem\\' + r, T_REM, tpl['quest\\rem\\' + r][1]))
    res.append(('quest\\supp\\supp_' + sid, T_SUPP, tpl['quest\\supp\\supp_%07d' % TPL][1]))
    plus = tnames[14]
    res.append(('quest\\plus\\questPlus_' + plus, T_PLUS, tpl['quest\\plus\\questPlus_' + plus][1]))
    link = tlink[:8] + b''.join(ref(T_SET, n) for n in SETNAMES) + ref(T_SET, 'b_m00em000_00') * 3
    link += ref(T_ESL, 'z_m00d_000') * 3
    link += b''.join(ref(T_REM, r) for r in REM) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, TPL, sid, t4)
    quest4u.write(a.out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d: stage %d, %d min, bosses %#x / %#x (stand-ins %#x / %#x), rows %d/%d/%d, "%s"' % (
        QID, qd[0x14], qd[0x16], HEAD['em_id'], TAIL['em_id'], HEAD['standin_id'], TAIL['standin_id'], hp, atk,
        other, t4['eng'][0]))


if __name__ == '__main__':
    main()
