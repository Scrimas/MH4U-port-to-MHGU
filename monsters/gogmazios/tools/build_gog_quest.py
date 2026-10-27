"""build_gog_quest.py : the Gogmazios quests for MHGU, EXTRA G-rank Hub quests (notes/stage.md, quest section).

  build_gog_quest.py [--source m11014 | m11035] [--bq | --arena | --plain | --siege | --legacy] [--area N]
                     [--pos ANGLE X Y Z] [--out DIR]
  --source: the 4U quest, m11014 "Advanced: Quagmire Quarrel" -> 11491 (default), m11035 "Advanced: Act of Gog" ->
  11492 (SOURCES). Build both after a change to the shared code.
  --bq (= the DEFAULT when no variant flag is given) = Battlequarters alias variant (stage 26, camp start, no siege,
  Gogmazios in alias area 2 at (633.5, 0, 1510.8)); module/stage.c applies the alias by default (-DNO_GOG_STAGE_ALIAS
  turns it off for the Fortress-data variants).
  setEmMain: +0x0C u32 area, +0x10 f32 angle, x, y, z.

Writes (default DIR = monsters/gogmazios/romfs, mirror of the game RomFS):
  nativeNX/loc/arc/quest/q<ID>.arc                      quest arc (setEmMain, emSetList, rem, supp, questPlus,
                                                          questLink, 5+2 GMDs, questData), loaded at quest start;
                                                          v1.4 finds questLink at entry [count-9], questData [count-1]
  nativeNX/loc/quest/questData/questData_<ID>.ext        loose questData (329 B), loaded for the board lists
  nativeNX/loc/quest/questLink/questLink_<ID>.qdl        loose questLink (308 B)
  nativeNX/<lang>/quest/questData/questData_<ID>_<lang>.gmd   text, lang = eng fre ger ita spa
All new files: nothing of the game is replaced. The quest only shows up with the module's two hooks
(quest_group entry + unlock answer, see notes/stage.md).

Sources:
  GU template  q0011413 (G4 Hub Kushala "Steel Yourself": plain hunt, no siege) from the base RomFS
               (MHGU_Editor/scratch/base_romfs.bin), setEmMain position from q0011319 (Fortress, Lao-Shan, area 1).
  4U quests    m11014 (loc/data/quest00.arc, v005): 5-language text, fee 3600z, reward 35400z, sub 11800z, 50 min,
               subquest "Wound Gogmazios's back"; m11035 (quest01.arc): fee 4600z, reward 45900z, sub 15300z, 50 min,
               "Sever Gogmazios's tail", 4U spawn byte 3 = 1 (module/em089_act.c spawn_b3). Same stage, spawn,
               stat rows.
Formats (questData, questLink, GMD, the v1.4 arc layout): tools/quest4u.py. questData +0x1A = 12 as on the Kushala and
Lao G4 quests (G).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import items_em089                  # noqa: E402
import quest4u                      # noqa: E402
from quest4u import (arc_files, text4u, ref, LANGS, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS, T_GMD,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U)
from romfs import RomFS             # noqa: E402

# 4U source quest -> GU quest (G4 Hub; 11491 / 11492 = the first free numbers after 11490, checked: no file, no list
# entry; module/stage.c renames quest_group placeholders 1011009 / 1011003 to them). sub = GU subquest code of the
# 4U subquest: decimal digits, each a break group (1-6, module/em089_break.c: back = part 1 = group 3) or 7 = tail
# sever (GU quests: 1 head, 7 tail, 17 head + sever, ...; the same digits 0x3a6f54 decodes). Was 5 (the chest) until
# test 2026-10-20 10:01 showed the chest break completing it.
import alloc                       # noqa: E402
ALLOC = alloc.monster('gogmazios')  # quests, em_id, standin_id, ui_icon (allocations.toml)
SOURCES = {
    'm11014': dict(arc='quest00.arc', qid=ALLOC['quests'][0], sub=3, rems=('rem_891014', 'rem_892014')),  # Wound
    'm11035': dict(arc='quest01.arc', qid=ALLOC['quests'][1], sub=7, rems=('rem_891035', 'rem_892035')),  # Sever tail
}
EM_ID = ALLOC['em_id']
BOSS_ID, BOSS_EM = ALLOC['standin_id'], 24   # Kushala: the loader-visible stand-in, swapped to EM_ID at spawn (main.c)
GU_ROMFS = paths.GU_ROMFS
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
HRP_PER_Z = 1880 / 35400       # quest 11491's HRP (chosen at its creation) per zenny of reward, kept for quest 11492
TPL, TPL_POS = 11413, 11319
TPL_ARENA = 11469              # G4 Arena quest (stage 9): --arena test map
BQ_AREA, BQ_POS = 2, (0.0, 633.5, 0.0, 1510.8)    # --bq spawn (alias area 2 = 4U m19a03d)
# rewards (tools/quest4u.py rem_4u): one entry per 4U row; the subquest list is row A's in both quests. 4U items ->
# GU: tools/items_em089.py gu_item. GU rem slots: 0 / 1 rows A / B, 2 / 3 rows C / D, 4 the subquest's (MHGU_Editor
# docs/05); row C stays GU's G Hub Accolade XX table (rem_530072, as on every G4 Hub quest), slot 4 = row A's table
# like 4U (and like GU's q0011413). rem_89xxxx: no GU quest uses that range.


def rem_4u(q, row):
    return quest4u.rem_4u(q, row, items_em089.gu_item)


def bq_plus(d):
    """--bq questPlus (rQuestPlus 0x26bec21c, 25 B: f32 1.0, u32 1, then cQuestPlus fields in registration order
    0x37ba10: u8 mIsRail @8, u8 mIsRailStart @9, u16 mRailOpenTime @10, mRailStartTime @12, mRailReuseTime @14 (Rail* =
    stage 9 only, 0x504e64), u8 mIsGekiryu @16, u16 mGekiryuStartTime @17, mGekiryuReuseTime @19 (seconds: GU 0x503c18
    / 0x503fa8 multiply by 60 frames), u16 mFortHpS @21, mFortHpL @23). Dragonator as 4U Battlequarters: usable at once,
    reuse after 600 s (4U 0x6b0ce0: fps * 10 * 60). Needs module/stage_gimmick.c (alias Dragonator without siege)."""
    b = bytearray(d)
    assert len(b) == 25 and b[:8] == bytes.fromhex('0000803f01000000') and not any(b[8:]), b.hex()
    b[16] = 1
    struct.pack_into('<HH', b, 17, 0, 600)
    # fortress HP: 0 = fortress already destroyed on stage 26 -> instant quest fail (in-game test 2026-10-18, also the
    # first questPlus_0000 Fortress test); Lao's siege questPlus_0026 uses 600 / 600
    struct.pack_into('<HH', b, 21, 600, 600)
    return bytes(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--area', type=int, default=None, help='spawn area (default: template q0011319, area 1)')
    ap.add_argument('--pos', type=float, nargs=4, default=None, help='spawn x y z w (setEmMain floats)')
    ap.add_argument('--siege', action='store_true', help='use the Fortress siege questPlus_0026 (Lao) instead of 0000')
    ap.add_argument('--plain', action='store_true',
                    help="diagnostic: keep the template's stage 23, start area and Kushala spawn point (only the "
                         "monster changes); the Fortress quests failed at once after loading, with no monster prep")
    ap.add_argument('--arena', action='store_true',
                    help='test map: the Arena (stage 9), start area / stage fields / first spawn point of the G4 Arena '
                         'quest q0011469; the Fortress (Lao siege data) left Gogmazios on Lao\'s unreachable track')
    ap.add_argument('--bq', action='store_true',
                    help='Battlequarters alias (stage 26 + module/stage.c GOG_STAGE_ALIAS): start in camp, no siege '
                         '(questPlus_0000), Gogmazios in alias area 2 (= 4U arena m19a03d) at 4U m11014\'s spawn')
    ap.add_argument('--hp-table', type=int,
                    help='boss vital (HP) table byte, default the 4U quest\'s (m11014 65 = HP x 2.05, m11035 69 = '
                         'x 2.17); a lower table = shorter tests')
    ap.add_argument('--icon', type=int, default=alloc.board_byte(alloc.ICON_PAGE2),
                    help='board icon byte qd+0xD6. GU 0x3a3178: bytes < 142 = UI index + 1 (24 = Kushala, verified); '
                         '142..186 = hyper icons (remap table + badge at 0x613318: 147 showed Hyper Khezu in test 3). '
                         'module/icons.c: bytes 200.. = our atlas, no badge; default 200 = 4U\'s "?" (4U m11014 / '
                         'm11035 +0xE8 = 0)')
    ap.add_argument('--legacy', action='store_true',
                    help='old default: Fortress stage 26 with Lao\'s q0011319 spawn record (area 1), no alias layout')
    ap.add_argument('--source', choices=sorted(SOURCES), default='m11014',
                    help='4U quest to port: m11014 "Advanced: Quagmire Quarrel" -> 11491 (default), m11035 '
                         '"Advanced: Act of Gog" -> 11492')
    ap.add_argument('--out', default=os.path.join(MON, 'romfs'))
    a = ap.parse_args()
    if not (a.arena or a.plain or a.siege or a.legacy):
        a.bq = True                     # the test variant (notes/stage.md section 10) is the default since session 5
    if a.bq:
        assert not (a.arena or a.plain or a.siege), '--bq excludes --arena / --plain / --siege'
        # 4U m11014 boss record (+0x1200): em 89, area byte 3 (= arena m19a03d -> alias area 2), pos (633.5, 0,
        # 1510.8), rotation 0; the 4U arena floor there is y 0 (collision probe). GU setEmMain +0x0C area,
        # +0x10 f32 (angle, x, y, z) (checked: the Arena / Kushala template positions sit on their stage floors).
        if a.area is None: a.area = BQ_AREA
        if a.pos is None: a.pos = list(BQ_POS)
    src4 = SOURCES[a.source]
    qid = src4['qid']; sid = '%07d' % qid

    R = RomFS(GU_ROMFS)
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL))
    pos = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL_POS))
    q4 = arc_files(open(os.path.join(Q4U_DIR, src4['arc']), 'rb').read())['loc\\quest\\' + a.source][1]
    assert q4[4:8] == b'v005' and struct.unpack_from('<H', q4, 0xC0)[0] == int(a.source[1:]) and q4[0xC4] == 19
    boss4 = q4.find(bytes.fromhex('5900000001000000'))      # 4U boss record: em 89, area byte +9, floats +0x10 / +0x18
    assert boss4 > 0 and q4[boss4 + 9] == 3 and struct.unpack_from('<fxxxxf', q4, boss4 + 0x10) == \
        struct.unpack('<ff', struct.pack('<ff', BQ_POS[1], BQ_POS[3])), 'spawn differs from m11014'

    # --- questData
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % TPL][1])
    assert len(qd) == 329
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x11] = 10                          # every board
    qd[0x12] = 14                          # G4
    arena = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % TPL_ARENA)) if a.arena else None
    if a.arena:
        aq = arena['loc\\quest\\questData\\questData_%07d' % TPL_ARENA][1]
        qd[0x14], qd[0x15], qd[0x1A] = aq[0x14], aq[0x15], aq[0x1A]   # stage 9, start area, stage-type byte
        qd[0x58:0x60] = aq[0x58:0x60]
    elif not a.plain:
        qd[0x14] = 26                      # Fortress (stage alias -> Battlequarters, notes/stage.md)
        qd[0x15] = 0                       # start area: camp, as both Fortress quests
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]   # 50 min (4U)
    qd[0x17] = 3
    qd[0x1A] = 12
    if a.siege:
        # Fortress quests: +0x1A and +0x58..+0x5F as on Lao's q0011319 (the only Fortress Hub quest; the Kushala
        # values 12 / 1,1,..,4,4 made the first Fortress test fail at once, together with the missing siege data)
        lao = pos['loc\\quest\\questData\\questData_%07d' % TPL_POS][1]
        qd[0x1A] = lao[0x1A]
        qd[0x58:0x60] = lao[0x58:0x60]
    qd[0x1F] = 1; struct.pack_into('<HH', qd, 0x20, EM_ID, 1)
    qd[0x24:0x29] = bytes(5)               # no second objective
    # subquest +0x29 {u8 type, u16 target, u16 code}: type 8 = wound / sever (template: 08 18 00 11 00 = Kushala head
    # + sever); target = the real monster ID like the main objective (the stand-in is swapped at spawn)
    qd[0x29] = 8; struct.pack_into('<HH', qd, 0x2A, EM_ID, src4['sub'])
    # money / points: 4U fee +0xA4, reward +0xA8, subquest reward +0xAC (= reward / 3 in both quests); academy =
    # reward x 0.08 (G); GU's sub academy = sub reward / 10 and sub HRP = HRP / 10 (q0011413: 5100 / 510, 1600 / 160)
    fee, reward, sub = struct.unpack_from('<III', q4, 0xA4)
    assert sub * 3 == reward, (fee, reward, sub)
    hrp = int(round(reward * HRP_PER_Z, -1))
    struct.pack_into('<IIIIIIIII', qd, 0x31, fee, 0, reward, sub, int(reward * 0.08), 0, sub // 10, hrp, hrp // 10)
    # boss record = Kushala (0x18), a stand-in kept out of the quest setup's per-monster tables; module/main.c swaps
    # 0x18 -> 0x59 at spawn prep / creation for this quest only (quest ID [[0x188ad90]+0xe0]), as the TEST_SWAP builds
    # did. (The empty monster list of the first tests was the null questLink, see the arc layout below.)
    # stat tables = rows of em_nando_tbl, the 4U quest's (tools/quest4u.py stats_4u): m11014 65 / 109 / 79 (HP 2.05,
    # attack 8.2, defense 0.8), m11035 69 / 115 / 83 (2.17, 10, 0.8). Until 2026-10-20 the builder used 116 / 98 / 98
    # (HP 4.3, attack 6.3, defense 0.75), read from the 4U board icons (+0xE8, 98 = no icon).
    hp, atk, other = quest4u.stats_4u(q4, R)
    if a.hp_table is not None: hp = a.hp_table
    boss = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, 1, hp, atk, other, 1, 100, 0, 3)
    qd[0x64:0x64 + 65] = boss + bytes(52)
    qd[0xD6:0xDB] = bytes([a.icon, 0, 0, 0, 0])    # board icon, default 4U's '?' (module/icons.c)
    for i, lang in enumerate(LANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(T_GMD, '%s_%s' % (sid, lang))
    qd = bytes(qd)

    # --- questLink + resources
    if a.arena:
        setname = 'b_m%02dem%03d_00' % (qd[0x14], BOSS_EM)
        first = [k for k in arena if '\\setEmMain\\b_m09' in k][0]   # the Arena quest's first monster spawn
        se = bytearray(arena[first][1])
    elif a.plain:
        setname = 'b_m%02dem%03d_00' % (qd[0x14], BOSS_EM)
        se = bytearray(tpl['quest\\boss\\setEmMain\\b_m%02dem024_00' % qd[0x14]][1])
    else:
        setname = 'b_m26em%03d_00' % (BOSS_EM if a.bq else 89)
        se = bytearray(pos['quest\\boss\\setEmMain\\b_m26em012_00'][1])
    if a.area is not None: struct.pack_into('<I', se, 0x0C, a.area)
    if a.pos: struct.pack_into('<4f', se, 0x10, *a.pos)
    plus = 'questPlus_0026' if a.siege else 'questPlus_0000'
    plus_src = pos if a.siege else tpl
    plus_data = plus_src['quest\\plus\\' + plus][1]
    if a.bq: plus, plus_data = 'questPlus_%04d' % (qid % 10000), bq_plus(plus_data)   # own name: no cache clash
    res = [('quest\\boss\\setEmMain\\' + setname, T_SET, bytes(se)),
           ('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]),
           ('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1])]
    rems = {name: rem_4u(q4, row) for row, name in zip(REWARD_ROWS_4U, src4['rems'])}
    assert rems[src4['rems'][1]][:8] == tpl['quest\\rem\\rem_230088'][1][:8]     # GU's f32 1.0, u32 1
    sub4 = struct.unpack_from('<I', q4, SUB_ROW_4U)[0]
    assert sub4 == struct.unpack_from('<I', q4, REWARD_ROWS_4U[0])[0], 'the 4U subquest rewards are not row A'
    REM = [src4['rems'][0], src4['rems'][1], 'rem_530072', 'rem_000000', src4['rems'][0]]
    for r in sorted(set(REM)):
        src = pos if ('quest\\rem\\' + r) in pos else tpl
        res.append(('quest\\rem\\' + r, T_REM, rems[r] if r in rems else src['quest\\rem\\' + r][1]))
    res.append(('quest\\supp\\supp_' + sid, T_SUPP, tpl['quest\\supp\\supp_%07d' % TPL][1]))
    res.append(('quest\\plus\\' + plus, T_PLUS, plus_data))
    link = tpl['loc\\quest\\questLink\\questLink_%07d' % TPL][1][:8]
    link += ref(T_SET, setname) + ref(T_SET, 'b_m00em000_00') * 4 + ref(T_ESL, 'z_m00d_000') * 3
    link += b''.join(ref(T_REM, r) for r in REM) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus[-4:])
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    gmds = quest4u.quest_gmds(tpl, TPL, sid, t4)
    quest4u.write(a.out, quest4u.assemble(res, link, gmds, qd, sid))
    print('quest %d: stage %d, %d min, em %#x, "%s"' % (qid, qd[0x14], qd[0x16], EM_ID, t4['eng'][0]))


if __name__ == '__main__':
    main()
