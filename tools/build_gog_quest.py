"""build_gog_quest.py : the Gogmazios quests for MHGU, EXTRA G-rank Hub quests (notes/stage.md, quest section).

  build_gog_quest.py [--source m11014 | m11035] [--bq | --arena | --plain | --siege | --legacy] [--area N]
                     [--pos ANGLE X Y Z] [--out DIR]
  --source: the 4U quest, m11014 "Advanced: Quagmire Quarrel" -> 11491 (default), m11035 "Advanced: Act of Gog" ->
  11492 (SOURCES). Build both after a change to the shared code.
  --bq (= the DEFAULT when no variant flag is given) = Battlequarters alias variant (stage 26, camp start, no siege,
  Gogmazios in alias area 2 at (633.5, 0, 1510.8)); needs module/stage.c built with -DGOG_STAGE_ALIAS.
  setEmMain: +0x0C u32 area, +0x10 f32 angle, x, y, z.

Writes (default DIR = module/romfs, mirror of the game RomFS):
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

questData (329 B, little endian; MHXX rQuestData layout, mhff wiki):
  +0x00 'KC' header (u32 0x434b0000, u32 1, u32 0)  +0x0C u32 quest id
  +0x10 type  +0x11 board (10 = every board)  +0x12 stars (14 = G4)  +0x13 rank tier  +0x14 stage  +0x15 start area
  +0x16 minutes  +0x17 carts  +0x1A BGM/flags (12 on the Kushala and Lao G4 quests, G)  +0x1F objective type (1 hunt)
  +0x20 u16 target  +0x22 u16 count  +0x24 objective 2  +0x29 subquest (type, u16 target, u16 code: SOURCES)
  +0x31 fee  +0x39 reward  +0x3D sub reward  +0x41 academy pts (reward x 0.08 in G)  +0x49 sub academy  +0x4D HRP
  +0x51 sub HRP  +0x58 supply deliveries  +0x64 5 x 13 B boss {u16 em id, u8 subtype, u8 aura, u8 restore count,
  u8 vital/attack/other table, u8 difficulty, u16 size %, u8 size table, u8 stamina}  +0xA5 small monster tables
  +0xD6 5 icons  +0xDF 5 x {u32 GMD type 0x242bb29a, char[16] "<ID>_<lang>"}  +0x147 u16 flags (bit 7 = no rotation)
questLink (308 B): 'KC' header, 13 x {u32 type, char[16] name}: 5 setEmMain, 3 emSetList, 5 rem, supp, questPlus.
GMD (v0x10302): 'GMD\\0', u32 version, u32 lang 0, u32 unk (copied from the template), u64 0, u32 strings,
  u32 labels 0, u32 string bytes, u32 name length, name\\0, UTF-8 strings. 7 strings: title, client, description,
  other monsters, main objective, failure, subquest.
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
import arcpack                      # noqa: E402
import items_em089                  # noqa: E402
from romfs import RomFS             # noqa: E402

# 4U source quest -> GU quest (G4 Hub; 11491 / 11492 = the first free numbers after 11490, checked: no file, no list
# entry; module/stage.c renames quest_group placeholders 1011009 / 1011003 to them). sub = GU subquest code of the
# 4U subquest: decimal digits, each a break group (1-6, module/em089_break.c: back = part 1 = group 3) or 7 = tail
# sever (GU quests: 1 head, 7 tail, 17 head + sever, ...; the same digits 0x3a6f54 decodes). Was 5 (the chest) until
# test 2026-10-20 10:01 showed the chest break completing it.
SOURCES = {
    'm11014': dict(arc='quest00.arc', qid=11491, sub=3, rems=('rem_891014', 'rem_892014')),  # Wound Gogmazios's back
    'm11035': dict(arc='quest01.arc', qid=11492, sub=7, rems=('rem_891035', 'rem_892035')),  # Sever Gogmazios's tail
}
EM_ID = 0x59
BOSS_ID, BOSS_EM = 0x18, 24    # Kushala: the loader-visible stand-in, swapped to EM_ID at spawn (module/main.c)
GU_ROMFS = '/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin'
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
HRP_PER_Z = 1880 / 35400       # quest 11491's HRP (chosen at its creation) per zenny of reward, kept for quest 11492
TPL, TPL_POS = 11413, 11319
TPL_ARENA = 11469              # G4 Arena quest (stage 9): --arena test map
BQ_AREA, BQ_POS = 2, (0.0, 633.5, 0.0, 1510.8)    # --bq spawn (alias area 2 = 4U m19a03d)
LANGS = ['eng', 'fre', 'ger', 'ita', 'spa']
FILLER_LANGS = ['jpn', 'kor']      # arc padding only (v1.4 positional questLink lookup, see main())
LANG4U = {'eng': 0, 'fre': 1, 'spa': 2, 'ger': 3, 'ita': 4}    # order of m11014's language tables (pointer at +0xBC)
T_SET, T_ESL, T_REM, T_SUPP, T_PLUS, T_LINK, T_GMD, T_QD = (
    0x2553701d, 0x32ca92f8, 0x5b3c302d, 0x54539aee, 0x26bec21c, 0x00e0bb1c, 0x242bb29a, 0x1bbfd18e)
# rewards: 4U quest header +0x1C row A, +0x20 row B, +0x24 subquest -> list {u32 0x8000, u32 table} closed by 0xFFFF
# (one entry each; the subquest list is row A's in both quests), table = 6-byte {u16 chance, u16 item, u16 count}
# closed by 0xFFFF. 4U items -> GU: tools/items_em089.py gu_item. GU rem slots: 0 / 1 rows A / B, 2 / 3 rows C / D,
# 4 the subquest's (MHGU_Editor docs/05); row C stays GU's G Hub Accolade XX table (rem_530072, as on every G4 Hub
# quest), slot 4 = row A's table like 4U (and like GU's q0011413). rem_89xxxx: no GU quest uses that range.
REWARD_ROWS_4U = (0x1C, 0x20)
SUB_ROW_4U = 0x24


def arc_files(data):
    return {p: (t, d) for p, t, d in arcpack.read(data)[1]}


def text4u(q):
    """m11014's 5 language blocks -> {lang: [title, objective, failure, description, other, client, subquest]}"""
    out = {}
    langs = struct.unpack_from('<I', q, 0xBC)[0]          # -> 5 language tables (0xFBC in m11014)
    for lang, k in LANG4U.items():
        tab = struct.unpack_from('<I', q, langs + 4 * k)[0]
        strs = []
        for i in range(7):
            o = struct.unpack_from('<I', q, tab + 4 * i)[0]
            assert o < len(q) and not o & 1, (lang, i, o)
            e = o
            while q[e:e + 2] != b'\0\0':
                e += 2
                assert e < len(q), (lang, i)
            strs.append(q[o:e].decode('utf-16-le').replace('\n', '\r\n'))
        out[lang] = strs
    return out


def rem_4u(q, row):
    """one 4U reward row (quest header offset) -> GU rem, 184 B: f32 1.0, u32 1, 8 x {u8 condition, u8 entries}
    groups, then each group's {u16 item, u8 count, u8 chance} entries closed by {0, 0, 0xFF}. A 4U row is one group;
    condition 1 = the plain groups of GU's rows A / B (q0011413 rem_130240 adds a condition-4 group, rem_230088 not).
    A 4U item with no GU item is left out and its chance goes to the row's most likely item (the row stays 100 %)."""
    lst = struct.unpack_from('<I', q, row)[0]
    flags, off = struct.unpack_from('<II', q, lst)
    assert flags == 0x8000 and struct.unpack_from('<H', q, lst + 8)[0] == 0xFFFF, 'unexpected 4U reward list'
    ents, lost = [], 0
    while struct.unpack_from('<H', q, off)[0] != 0xFFFF:
        chance, item, count = struct.unpack_from('<HHH', q, off)
        gu = items_em089.gu_item(item)
        if gu is None:
            lost += chance
            print('reward row %#x: 4U item %d has no GU item, its %d %% goes to the most likely item' % (row, item, chance))
        else:
            ents.append([gu, count, chance])
        off += 6
    max(ents, key=lambda e: e[2])[2] += lost
    assert sum(e[2] for e in ents) == 100 and len(ents) <= 40, ents
    body = b''.join(struct.pack('<HBB', *e) for e in ents)
    d = struct.pack('<fI', 1.0, 1) + bytes([1, len(ents)]) + bytes(14) + body + struct.pack('<HBB', 0, 0, 0xFF)
    return d + bytes(184 - len(d))


def gmd(name, strings, unk):
    body = b''.join(s.encode('utf-8') + b'\0' for s in strings)
    n = name.encode('ascii')
    return (b'GMD\0' + struct.pack('<IIIQIIII', 0x10302, 0, unk, 0, len(strings), 0, len(body), len(n))
            + n + b'\0' + body)


def gmd_unpack(d):
    cnt, _, size, nl = struct.unpack_from('<IIII', d, 0x18)
    return d[0x28:0x28 + nl].decode(), d[0x29 + nl:].split(b'\0')[:cnt], struct.unpack_from('<I', d, 0xC)[0]


def ref(t, name):
    n = name.encode('ascii'); assert len(n) < 16, name
    return struct.pack('<I16s', t, n)


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
    ap.add_argument('--hp-table', type=int, default=116,
                    help='boss vital (HP) table byte, default 116 (GU em_nando_tbl row with HP 4.3 = 4U m11014 row 98\'s '
                         'HP; GU row 98 has 3.4); a lower table = shorter tests')
    ap.add_argument('--icon', type=int, default=192,
                    help='board icon byte qd+0xD6. GU 0x3a3178: bytes < 142 = UI index + 1 (24 = Kushala, verified); '
                         '142..186 = hyper icons (remap table + badge at 0x613318: 147 showed Hyper Khezu in test 3). '
                         'The user\'s HD UI v4 cheat (0x3a3188 / 0x613318 cave) adds bytes > 186 = UI index + 46, no '
                         'badge: default 192 = UI 146 (Gogmazios "?", tools/ui_icon_hdui.py). Without that cheat 192 '
                         'shows no icon')
    ap.add_argument('--legacy', action='store_true',
                    help='old default: Fortress stage 26 with Lao\'s q0011319 spawn record (area 1), no alias layout')
    ap.add_argument('--source', choices=sorted(SOURCES), default='m11014',
                    help='4U quest to port: m11014 "Advanced: Quagmire Quarrel" -> 11491 (default), m11035 '
                         '"Advanced: Act of Gog" -> 11492')
    ap.add_argument('--out', default=os.path.join(ROOT, 'module', 'romfs'))
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
    # stat tables = rows of em_nando_tbl (GU loc resident.arc, 4U copy at 0xf3a330, same 32-B rows {HP, attack,
    # defense, ...}): 4U m11014 / m11035 use row 98 for all three (HP 4.3, attack 6.3, defense 0.75); GU's row 98
    # has the same attack / defense but HP 3.4 -> HP byte = GU row 116 (HP 4.3), attack and other = row 98
    boss = struct.pack('<HBBBBBBBHBB', BOSS_ID, 0, 0, 1, a.hp_table, 98, 98, 1, 100, 0, 3)
    qd[0x64:0x64 + 65] = boss + bytes(52)
    qd[0xD6:0xDB] = bytes([a.icon, 0, 0, 0, 0])    # board icon, default Kushala's 24 (= UI index 23 + 1, G)
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

    # --- text
    t4 = text4u(q4)
    gmds = {}
    for lang in LANGS:
        title, obj, fail, desc, other, client, sub = t4[lang]
        unk = gmd_unpack(tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, TPL, lang)][1])[2]
        gmds[lang] = gmd('questData_' + sid, [title, client, desc, other, obj, fail, sub], unk)

    # self-check: the GMD writer reproduces the template byte for byte
    for lang in LANGS:
        d = tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, TPL, lang)][1]
        name, strs, unk = gmd_unpack(d)
        assert gmd(name, [s.decode('utf-8') for s in strs], unk) == d, lang

    ents = res + [('loc\\quest\\questLink\\questLink_' + sid, T_LINK, link)]
    ents += [('%s\\quest\\questData\\questData_%s_%s' % (l, sid, l), T_GMD, gmds[l]) for l in LANGS]
    # v1.4 positional layout: the quest start reads questData = arc entry [count-1] (0x3ba6dc) and questLink =
    # entry [count-9] (0x3ba840, path must contain "Link"; v1.0 used [count-7]). The v1.0 template arcs have only
    # 7 entries from questLink to questData, so 2 inert GMDs (English text, language folders the game never asks
    # for) fill the gap; without them questLink is null and 0x3ade34 skips the whole quest setup.
    ents += [('%s\\quest\\questData\\questData_%s_%s' % (l, sid, l), T_GMD, gmds['eng']) for l in FILLER_LANGS]
    ents += [('loc\\quest\\questData\\questData_' + sid, T_QD, qd)]
    assert len(ents) >= 9 and ents[-9][1] == T_LINK and 'Link' in ents[-9][0] and ents[-1][1] == T_QD
    arc = arcpack.build(ents)
    assert arc_files(arc) == {p: (t, d) for p, t, d in ents}

    out = os.path.join(a.out, 'nativeNX')
    files = {'loc/arc/quest/q%s.arc' % sid: arc,
             'loc/quest/questData/questData_%s.ext' % sid: qd,
             'loc/quest/questLink/questLink_%s.qdl' % sid: link}
    files.update({'%s/quest/questData/questData_%s_%s.gmd' % (l, sid, l): gmds[l] for l in LANGS})
    for rel, data in files.items():
        p = os.path.join(out, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        print('%6d %s' % (len(data), p))
    print('quest %d: stage %d, %d min, em %#x, "%s"' % (qid, qd[0x14], qd[0x16], EM_ID, t4['eng'][0]))


if __name__ == '__main__':
    main()
