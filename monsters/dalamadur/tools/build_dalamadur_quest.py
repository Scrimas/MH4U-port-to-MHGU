"""build_dalamadur_quest.py : Dalamadur's and Shah Dalamadur's 4U quests for MHGU (notes/plan.md 6. Quests), each from
its own 4U file: the ROM's (loc/data/quest01.arc) and the user's DLC extdata (tools/extdata4u.py: event quests).
Stage 18 = GU's Sanctuary, which loads Speartip Crag (folder m29, build_speartip.py) while the quest runs
(allocations.toml stage_alias, module/stage_alias.c). Ranks as 4U (faithful, user 2026-10-21): 4U 7 -> GU Hub HR 7
(ID 107NN, template q0010764), 4U G3 -> GU Hub G4 (ID 114NN, template q0011425; as Gogmazios' G3 quests).

  build_dalamadur_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/dalamadur/romfs), per quest: the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write). The quests show up through the module's quest_group hook (allocations.toml
quests / quest_slots: entry dalamadur quests[0..3], shah_dalamadur quests[0..1], in QUESTS order).

Sources (C): rank bytes (questData 0x12 star, 0x13 class, 0x1A, 0x2E-0x30), board, supply box, questPlus, the
generic reward rows of slots 3 / 4 and the GMD unk word: the GU template's; text (5 languages), fee / reward /
subquest reward, minutes, boss stat rows, reward rows A / B / subquest: the 4U quest's; academy points and HRP: the
4U reward x the template's ratio (rounded to 10), subquest ones / 10 as GU's.
  4U quests  m10709 Advanced: Speartip Menace (7)   fee 2200 / 21000 / sub 7000, stats 37/72/76, sub: wound head
             m10721 Advanced: Here to Eternity (7)  fee 2600 / 25200 / 8400, stats 43/102/77, no subquest
             m60131 Pillar of Strength (event 7)    fee 2600 / 25200 / 8400, stats 40/105/82, sub: wound back
             m60209 The Speartip's King (event 10)  fee 3000 / 29400 / 9800, stats 65/107/79, sub: wound legs
             m11030 Advanced: Eternal Emperor (10)  fee 3600 / 35400 / 11800, stats 65/109/79, sub: wound back (Shah)
             m60213 The Crimson Shah (event 10)     fee 3000 / 29400 / 9800, stats 67/111/79, sub: sever tail (Shah)
  All: 50 min, two bosses in area 1 at the arena origin with no rotation (head, tail), objective: slay the head.
Subquest {type 8, u16 target em, u16 code} (GU 0x3a6f54, as build_gog_quest.py): code digits = break groups of the
target (module/dala_break.c: head 1, chest 2, back 3, claws 4 = both legs, 4U group 0x83) or 7 = tail sever (the
tail half's cut, module/dala_parts.c tail_sever: reward flag 7 on the tail instance).
Bosses (GU precedent: Ahtal-Ka quests 11432 / 1011030 list [0x58, 0x57], objective 0x58): [head stand-in, tail
stand-in] (allocations.toml standin_id, swapped at spawn by module/main.c), objective the head's real em ID. Both at
4U's point, the arena origin (0, 0, 0) with rotation 0: every Dalamadur motion moves bone 0 only (class-study.md), so
the two halves form one body around their common origin, coiled round the spire k02. The setEmMain record is
Amatsu's (b_m18em058_00, area 1, in both templates) with 4U's floats (setEmMain floats = rotation, x, y, z).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, extdata4u, hagi4u, quest4u   # noqa: E402
import items_em090                  # noqa: E402  (this package's tools/)
from quest4u import (arc_files, text4u, ref, LANGS, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U)
from romfs import RomFS             # noqa: E402

HR, G = 10764, 11425              # GU templates: Amatsu HR 7 / G4 on the Sanctuary, every board, start area 0
ARC_4U, STAGE_4U = 'quest01.arc', 8
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE = 18                        # the Sanctuary = Speartip Crag's alias stage (allocations.toml stage_alias)
TPL_SET = 'b_m18em058_00'         # Amatsu's spawn record (area 1); its floats become 4U's
# entry (owner of the quest ID), 4U source ('rom' = ARC_4U, 'ext' = the DLC extdata), 4U number, star / template,
# 4U bosses, subquest (target entry, GU code) or None
QUESTS = [('dalamadur', 'rom', 10709, HR, (24, 83), ('dalamadur', 1)),               # wound the head
          ('dalamadur', 'rom', 10721, HR, (24, 83), None),
          ('dalamadur', 'ext', 60131, HR, (24, 83), ('dalamadur', 3)),               # wound the back
          ('dalamadur', 'ext', 60209, G, (24, 83), ('dalamadur', 4)),                # wound the legs (both claws)
          ('shah_dalamadur', 'rom', 11030, G, (110, 111), ('shah_dalamadur', 3)),    # wound the back
          ('shah_dalamadur', 'ext', 60213, G, (110, 111), ('shah_dalamadur_tail', 7))]   # sever the tail
STAR_4U = {HR: 7, G: 10}          # 4U quest star byte +0xC2 of each kind


def spawns_4u(q):
    """4U boss spawn records, 0x28 B each from [+0x28] -> first record, closed by em 0xffffffff:
    [(em, area, (x, y, z, rotation))]"""
    out, rec = [], struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
        out.append((struct.unpack_from('<I', q, rec)[0], q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10)))
        rec += 0x28
    return out


def quest_ids():
    """{(entry, 4U number): GU quest ID}: each entry's quests in QUESTS order (allocations.toml)"""
    out, k = {}, {}
    for entry, src, num, tpl, ems, sub in QUESTS:
        out[(entry, num)] = alloc.monster(entry)['quests'][k.get(entry, 0)]
        k[entry] = k.get(entry, 0) + 1
    return out


def build(R, out, entry, src, num, tpl_id, ems, subq, qid, hp_table=None):
    head, tail = alloc.monster(entry), next(m for m in alloc.monsters() if m.get('companion_of') == entry)
    sid, m4 = '%07d' % qid, 'm%05d' % num
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    q4 = (arc_files(open(os.path.join(Q4U_DIR, ARC_4U), 'rb').read())['loc\\quest\\' + m4][1] if src == 'rom'
          else extdata4u.quest(num))
    assert q4[4:8] == b'v005' and struct.unpack_from('<H', q4, 0xC0)[0] == num and q4[0xC4] == STAGE_4U, m4
    assert q4[0xC2] == STAR_4U[tpl_id], (m4, q4[0xC2])
    sp = spawns_4u(q4)
    assert [s[0] for s in sp] == list(ems) and all(s[1] == 1 and s[2] == (0, 0, 0, 0) for s in sp), (m4, sp)

    # --- questData: the template's (rank bytes, board, start area 0, flags), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == 329 and qd[0x14] == STAGE and qd[0x11] == 10 and qd[0x1D] == 0   # clear rule: objective 0
    t_fee, _, t_reward, t_sub, t_acad, _, t_subacad, t_hrp, t_subhrp = struct.unpack_from('<9I', qd, 0x31)
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # 50 min (4U)
    qd[0x1F] = 1; struct.pack_into('<HH', qd, 0x20, head['em_id'], 1)
    qd[0x24:0x29] = bytes(5)
    fee, reward, sub = struct.unpack_from('<III', q4, 0xA4)
    if subq:                                               # {u8 type 8 = wound / sever, u16 target em, u16 code}
        qd[0x29] = 8; struct.pack_into('<HH', qd, 0x2A, alloc.monster(subq[0])['em_id'], subq[1])
    else:
        qd[0x29:0x2E] = bytes(5); sub = 0
    r10 = lambda v: int(round(v, -1))
    acad, hrp = r10(reward * t_acad / t_reward), r10(reward * t_hrp / t_reward)
    struct.pack_into('<9I', qd, 0x31, fee, 0, reward, sub, acad, 0, sub // 10, hrp, hrp // 10 if sub else 0)
    # boss records {u16 id, subtype, aura, restore, HP / attack / other rows, byte 8, u16 size %, size table,
    # stamina}: the stand-ins, the 4U quest's stat rows (both bosses share them in 4U), the template's other bytes
    hp, atk, other = quest4u.stats_4u(q4, R)
    if hp_table is not None: hp = hp_table
    t = struct.unpack_from('<HBBBBBBBHBB', qd, 0x64)
    boss = lambda em: struct.pack('<HBBBBBBBHBB', em, t[1], t[2], t[3], hp, atk, other, t[7], 100, t[9], t[10])
    qd[0x64:0x64 + 65] = boss(head['standin_id']) + boss(tail['standin_id']) + bytes(39)
    qd[0xD6:0xDB] = bytes([head['donor_index'] + 1, 0, 0, 0, 0])   # board icon: the donor's until the icons
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))
    qd = bytes(qd)

    # --- questLink + resources: setEmMain = Amatsu's record (area 1) with 4U's rotation and point for both halves
    assert head['stage_alias'][0] == STAGE
    v = head['em_id'] >> 8
    setnames = ('b_m%02dem090_%02d' % (STAGE, v), 'b_m%02dem091_%02d' % (STAGE, v))   # no GU quest uses em090 / 91
    se = bytearray(tpl['quest\\boss\\setEmMain\\' + TPL_SET][1])
    assert struct.unpack_from('<I', se, 0x0C)[0] == sp[0][1] == 1
    struct.pack_into('<4f', se, 0x10, *(sp[0][2][3:] + sp[0][2][:3]))   # 4U (x, y, z, rotation) -> (rotation, x, y, z)
    res = [('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)) for n in setnames]
    res += [('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]),
            ('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1])]
    tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
    # 15 refs: 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
    # rows A / B / subquest from 4U (a subquest row equal to row A is row A's file); slots 3 / 4 the template's
    gu_item = items_em090.materials(R, hagi4u.exe()).gu_item
    ptr = lambda o: struct.unpack_from('<I', q4, o)[0]
    rows = {'rem_%sa' % m4: REWARD_ROWS_4U[0], 'rem_%sb' % m4: REWARD_ROWS_4U[1]}
    sub_name = 'rem_%sa' % m4
    if subq and ptr(SUB_ROW_4U) and ptr(SUB_ROW_4U) != ptr(REWARD_ROWS_4U[0]):
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
    link = tlink[:8] + b''.join(ref(T_SET, n) for n in setnames) + ref(T_SET, 'b_m00em000_00') * 3
    link += ref(T_ESL, 'z_m00d_000') * 3
    link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d = 4U %s (%s): star %d class %d, %d min, bosses %#x / %#x (stand-ins %#x / %#x), rows %d/%d/%d, '
          'fee %d reward %d sub %d (%s), "%s"' % (
              qid, m4, src, qd[0x12], qd[0x13], qd[0x16], head['em_id'], tail['em_id'], head['standin_id'],
              tail['standin_id'], hp, atk, other, fee, reward, sub, subq, t4['eng'][0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hp-table', type=int, help="boss vital (HP) table byte, default each 4U quest's; a lower "
                                                 'table = shorter tests')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    ap.add_argument('--only', type=int, help='build only this GU quest ID')
    a = ap.parse_args()
    R = RomFS(paths.GU_ROMFS)
    ids = quest_ids()
    for entry, src, num, tpl_id, ems, sub in QUESTS:
        if a.only in (None, ids[(entry, num)]):
            build(R, a.out, entry, src, num, tpl_id, ems, sub, ids[(entry, num)], a.hp_table)


if __name__ == '__main__':
    main()
