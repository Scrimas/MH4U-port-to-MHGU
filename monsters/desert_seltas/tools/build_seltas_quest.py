"""build_seltas_quest.py : Desert Seltas' and Desert Seltas Queen's 4U quests for MHGU, appended to GU's quest list by the core
(module/quest.c quest_group_append; allocations.toml quests + quest_append). Built as Shrouded Nerscylla's builder
(monsters/shrouded_nerscylla/tools/build_em070_01_quest.py), plus partners, an intruder, rounds and the 4U small monsters.

  build_seltas_quest.py [--hp-table N] [--out DIR] [--only ID]

Writes (default DIR = monsters/desert_seltas/romfs), per quest: the quest arc, loose questData / questLink and the 5 GMDs
(tools/quest4u.py assemble / write).

Their 4U quests (C, all of quest00 / 01.arc; their event quests are left out, the user 2026-11-09):
  m01030  caravan 10 star (G), the Dunes (17): hunt a Desert Seltas; subquest break his horn
  m10805  guild G1, the Ancestral Steppe (1): hunt a Desert Seltas; a Rajang intrudes (+0x30: 100 %, stat block 2)
  m10815  guild G1, the Dunes: slay 30 Bnahabra, subquest slay 8 Konchu; a Desert Seltas intrudes (100 %, stat block 2)
  m10818  guild G1, the Ancestral Steppe: hunt a Seltas and a Desert Seltas (he comes second: spawn byte +0xC 1); subquest
          deliver 1 Queen Substance
  m10924  guild G2, the night Dunes (18): hunt a Desert Seltas Queen, her Desert Seltas with her (spawn count 99: he comes
          back); subquest wound her tail
  m10928  guild G2, the Dunes, "hunt all" (+0xA0 8): a Cephadrome (list 0), then (list 1) the Queen and her Desert Seltas
          (count 99); objective text "Hunt a <X> and a Desert Seltas Queen", subquest suppress the Queen's frenzy. 4U's text
          names a Shrouded Nerscylla for X in all 5 languages, its file spawns a Cephadrome (em 105): the text here names the
          Cephadrome (the monster that comes)
  Not ported: m10812 (Purple Gypceros on the Sunken Hollow, Desert Seltas its 50 % intruder): GU has neither.
Placement (the user's rules, 2026-11-08): caravan -> village (1068, 10 star G), guild -> hub, ranks by the README rule: 4U's G1
Desert Seltas sits with 4U's G1 Seltas and GU's Seltas hunt q11103 is G1 -> hub G1; 4U's G2 Queen sits with 4U's G2 Seltas Queen
and GU's lowest G Seltas Queen quest q11305 is G3 -> hub G3. No quest waits for a GU monster's own quest (the user 2026-11-09:
G rank quests).

Sources (C unless marked):
  Template (tpl) GU quest of the same board and rank, the same kind, board 10 (every board): stars, rank, category, start area,
                 flags, money, questPlus, GMD unk word, small-monster rows (+0xA5..+0xA7). Village q1012 (G single hunt,
                 re-staged 2 -> 5, as Shrouded Nerscylla's); hub G1 q11109 (a Steppe hunt with intruders), q11114 (GU's G1
                 slay-small-monsters quest, re-staged 24 -> 5), q11127 (a Steppe hunt of two, the second in round 1); hub G3
                 q11305 (GU's Seltas Queen hunt with her Seltas, re-staged 101 -> 5), q11306 (a hunt of two monsters, rule 1,
                 re-staged 2 -> 5).
  Boss slots     GU: 0 / 1 the main bosses, 2..4 more bosses or intruders (GU's intruders sit there, q11124 / q11217 in slot
                 2; GU's hunt-all quests fill 2 / 3 with +0xCC zero, q11363). 4U's intruder is its stat block 2: slot 2 here.
  Intruder       +0xCC..+0xD3 and +0x16F bit 3 of GU's G1 hunt with one intruder in slot 2, q11124 (64 00 64 00 00 00 64 00, as
                 GU's other G quests with one: q11101..q11126, q11217; bit 3 is set on exactly the 417 GU quests with +0xCC
                 set). Which of those bytes is a chance is not traced (G); 4U's chance is 100 % in both quests. The +0xA8 spawn
                 condition (q11114 / q11217: after 10 small monsters) is cleared: 4U's intruder list holds a chance and a spawn
                 record only.
  Rows (HP / attack / other) GU's own record of the species at the placement (DS: Seltas', the Queen: Seltas Queen's) with
                 its restore count, difficulty, size table and stamina; size % from 4U (4U 0 -> 100, G: 4U's 0 not traced);
                 subtype and aura 0:
                   1068    q1012's boss (51 / 97 / 85, every village 10 star G single hunt)
                   11138   DS = q11103's first Seltas (59 / 85 / 84); Rajang = GU's G1 intruder Rajang, q11108 (71 / 94 / 86)
                   11139   DS as 11138, HP by his 4U row here over m10805's (Shrouded Nerscylla's double-hunt rule)
                   11140   Seltas and DS = GU's own G1 double Seltas hunt q11103, its two records in spawn order
                   11374   q11305's Queen (71 / 92 / 86) and her Seltas (81 / 94 / 86, restore 5: GU's form of 4U's count 99)
                   11373   Cephadrome = GU's G3 multi-monster Cephadrome q11360 (49 / 93 / 86); Queen and DS as 11374, HP by
                           their 4U rows here over m10924's
  Partners       the real Seltas (11140), Rajang and Cephadrome are GU's own monsters. Desert Seltas is named by his stand-in
                 (allocations.toml standin_id 0x4c; in 11140, where a real Seltas is, standin_alt 0x45), the Queen by 0x45,
                 swapped at spawn by module/main.c (in the Queen's quests DS through guest_in).
  Objectives     hunts: the real IDs (two targets: rule 1, both). 4U's hunt all (m10928): every boss but the one with count 99
                 (4U's objective text names those two). m10815: GU type 1 on Bnahabra 0x101a (C: q307 "slay 20").
  Subquest       4U 0x204 {em, part} -> GU type 8 {real ID, code}: DS horn = GU Seltas code 1 (q703 "Break the Seltas's
                 horn"), the Queen's tail = code 4 (q902 "Wound Seltas Queen's tail"). 4U 0x101 {Konchu} -> GU type 1 on Konchu
                 0x102d (C: q313); 4U 2 {item} -> GU type 5. m10928's "suppress the frenzy" has no GU state (no frenzy): the
                 Queen's tail subquest of m10924 with m10924's 4U text, a DEVIATION. Sub money (+0x3D reward, +0x49 academy,
                 +0x51 HRP): the template's, or (sub_money) a GU quest's of this rank with this kind of subquest where the
                 template's subquest is another kind (11139: q11105 "slay 8", 2400; 11373: q11305, the Queen's tail). Without
                 a subquest 0 (as GU's own quests without one). The village quest keeps its 4U subquest with the template's 0
                 sub money (GU's village G quests have none, C; as Shrouded Nerscylla's and Tidal Najarala's village quests).
  Rounds         setEmMain +8 = the rank of (4U list, spawn byte +0xC): m10818's DS after the Seltas, m10928's Queen and DS
                 after the Cephadrome (S: 4U's reader of +0xC is not traced). The intruder: round 0 (q11124).
  Small monsters 4U's first set (+0x2C) per area as a GU emSetList (esl_4u, format below); species GU lacks (Delex) are left
                 out, logged. 4U's sets 1 / 2 are not used (what switches them is not traced on either side, G; only m10815's
                 set 1 differs). m10815 needs its Bnahabra and Konchu: GU's Dunes sets hold few (C: q605).
  Supply box     village: the 4U quest's (quest4u.supp_4u) with one Map at the start (map_only_start), Hot Drinks -> Cool
                 Drinks on GU's Dunes. Hub: a GU hub box of the same stars, objective type and map (supp_tpl, else the
                 template's) with its delivery groups (+0x58): 4 Maps for 4 players, Cool Drinks on the Dunes (q11111 G1,
                 q11327 / q11352 G3).
  Rewards        their own materials (items_seltas.py, appended IDs), the other 4U items as items_seltas OTHER_4U_GU /
                 SUBSTITUTES, else by English name in GU itemData_eng; a 4U item GU lacks is left out, logged. Reward slots
                 3 / 4 = GU's empty row rem_000000.
  Frenzy         spawn byte +0xF 1 (m10818, m10928): GU has no frenzy (the user: left out), logged per quest.
  Night Dunes    m10924 (4U 18) -> GU's Dunes (5): GU has no night Dunes, a DEVIATION with the stage (Shrouded Nerscylla's).
GU emSetList (C over 3608 records of 136 GU quest sets): 'esl\\0', u32 2, 14 u32 block offsets (block k = area k + 1, 0 = none),
a block 'ESD\\0', u32 0x20151214, u16 n, then n records of 0x24 B {u16 em, u8 count, 0xcd, u8 link, u8 area, u8 a, u8 b, 0, 0,
0xcd, 0xcd, f32 x, y, z, u32 0, u16 angle, u16 0, u32 0}. 4U record (0x28 B, lists per area closed by em 0xffffffff): u32 em,
u32 count, u8 link, u8 area, u8 a, u8 b, f32 x, y, z @0x10, u16 angle @0x20. Fields 1:1 (S: these quests' values lie in GU's
value sets, a 1 / 5, b 0..2, link 0..10 / 255; link 20 only on Delex, left out); 4U count 255 -> GU 99.
"""
import argparse, csv, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
import alloc, arcpack, gear4u, gmd, quest4u   # noqa: E402
sys.path.insert(0, HERE)
import items_seltas                 # noqa: E402
from items4u import EXE, EXE_BASE, msg4u, text_4u   # noqa: E402
from quest4u import (arc_files, text4u, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS,  # noqa: E402
                     REWARD_ROWS_4U, SUB_ROW_4U, STATS_4U, NANDO_4U)
from romfs import RomFS             # noqa: E402

DS, DSQ = alloc.monster('desert_seltas'), alloc.monster('desert_seltas_queen')
ALT, ALT_QUEST = DS['standin_alt']  # 0x45 names Desert Seltas in 11140 (a real Seltas is in it)
Q4U_DIR = os.path.join(ROOT, 'dump/romfs/loc/data')
STAGE_GU = {17: 5, 18: 5, 1: 11}    # 4U Dunes (day, night) -> GU Dunes; 4U Ancestral Steppe -> GU's
# 4U em -> (GU ID the boss record names, GU ID at spawn): theirs are stand-ins, swapped by the core
GU_OF = {94: (DS['standin_id'], DS['em_id']), 95: (DSQ['standin_id'], DSQ['em_id']), 25: (0x4c, 0x4c), 105: (0x11, 0x11),
         112: (0x17, 0x17)}
NAME_4U = {94: 'Desert Seltas', 95: 'Desert Seltas Queen', 25: 'Seltas', 105: 'Cephadrome', 112: 'Rajang'}   # asserted: emName
ICON = {94: alloc.board_byte(DS['ui_icon']), 95: alloc.board_byte(DSQ['ui_icon'])}   # their cells (module/icons.c)
ICON_GU = {0x4c: 703, 0x11: 11111}  # GU quests whose first boss is that monster: its board icon (C)
ICON_SMALL = {0x101a: 307}          # GU quest whose first objective slays that small monster: its board icon (C)
SMALL_CHECK = {68: (0x101a, 307), 73: (0x102d, 313)}   # 4U Bnahabra / Konchu -> GU, a GU quest slaying it (C)
INTRUDER_ICON = 106                 # GU's board icon of an intruder (C: q11124 / q11217 [.., 106])
INTRUDER_DONOR = 11124              # GU's G1 hunt with one intruder in slot 2
INTRUDER_SLOT = 2
INTRUDER_FLAG = 0x8                 # questData +0x16F bit 3: set exactly with +0xCC (C)
URGENT = 0x1                        # questData +0x16F bit 0 = an urgent (key) quest (Monoblos' builder)
COMPANION = 99                      # 4U spawn count of a boss that comes back (the Queen's Desert Seltas, C: m10924 / m10928)
REM_EMPTY = struct.pack('<fI', 1.0, 1) + bytes(176)     # GU's rem_000000 (184 B, no group; C: q10706)
# Quests: owner entry and k = index in its allocations.toml quests; num = 4U quest; tpl = GU template (tpl_stage: its stage
# when re-staged); supp_tpl = the GU hub quest whose box replaces the template's; rows = per boss in spawn order, the intruder
# last: (GU quest, GU ID[, nth record of it]) whose record gives rows / restore / difficulty / size table / stamina; ratio = per
# boss index: (4U quest, its stat block) whose 4U HP row the HP is scaled against (none: GU's rows as they are); sub =
# ('break', 4U em, GU code) | ('deliver', 4U item) | ('slay', 4U small em) | ('like', 4U quest, 4U em, GU code): that quest's
# 4U subquest and text instead of one GU has no state for; sub_money = the GU quest whose sub money fields are taken
QUESTS = [
    dict(owner='desert_seltas', k=0, num=1030, tpl=1012, tpl_stage=2, rows=[(1012, 0x202)], sub=('break', 94, 1)),
    dict(owner='desert_seltas', k=1, num=10805, tpl=11109, rows=[(11103, 0x4c), (11108, 0x17)]),
    dict(owner='desert_seltas', k=2, num=10815, tpl=11114, tpl_stage=24, supp_tpl=11111, rows=[(11103, 0x4c)],
         ratio={0: (10805, 0)}, sub=('slay', 73), sub_money=11105),
    dict(owner='desert_seltas', k=3, num=10818, tpl=11127, rows=[(11103, 0x4c, 0), (11103, 0x4c, 1)], sub=('deliver', 822)),
    dict(owner='desert_seltas_queen', k=0, num=10924, tpl=11305, tpl_stage=101, supp_tpl=11327,
         rows=[(11305, 0x45), (11305, 0x4c)], sub=('break', 95, 4)),
    dict(owner='desert_seltas_queen', k=1, num=10928, tpl=11306, tpl_stage=2, supp_tpl=11352,
         rows=[(11360, 0x11), (11305, 0x45), (11305, 0x4c)], ratio={1: (10924, 0), 2: (10924, 1)}, sub=('like', 10924, 95, 4),
         sub_money=11305),
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
    """4U boss spawns of every list of the table at +0x28 (u32 list pointers, up to 4; the "hunt all" quests put later waves
    in list 1), records 0x28 B closed by em 0xffffffff: [(em, count, area, (x, y, z, rot), list, +0xC, +0xF)]"""
    tbl = struct.unpack_from('<I', q, 0x28)[0]
    out = []
    for li in range(4):
        rec = struct.unpack_from('<I', q, tbl + 4 * li)[0]
        if not rec or rec + 4 > len(q): continue
        while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF:
            em, count = struct.unpack_from('<II', q, rec)
            out.append((em, count, q[rec + 9], struct.unpack_from('<4f', q, rec + 0x10), li, q[rec + 0xC], q[rec + 0xF]))
            rec += 0x28
    return out


def rounds(sp):
    """GU mRoundNo per spawn (setEmMain +8): the rank of (list, +0xC) (docstring: Rounds)"""
    order = sorted({(s[4], s[5]) for s in sp})
    return [order.index((s[4], s[5])) for s in sp]


def intruder_4u(q):
    """(chance %, 4U em, area, (x, y, z, rot)) of the 4U intruder list, or None (no list, an empty one or chance 0). +0x30
    -> entries {u32 chance %, spawn record 0x28 B} closed by chance 0xffff + em 0xffffffff (C: m10805 / m10815 hold one
    entry, the quests without an intruder start with the end mark)"""
    o = struct.unpack_from('<I', q, 0x30)[0]
    if not o or struct.unpack_from('<I', q, o + 4)[0] == 0xFFFFFFFF or not struct.unpack_from('<I', q, o)[0]:
        return None
    r = o + 4
    assert struct.unpack_from('<II', q, r + 0x28) == (0xFFFF, 0xFFFFFFFF), 'more than one 4U intruder'
    return struct.unpack_from('<I', q, o)[0], struct.unpack_from('<I', q, r)[0], q[r + 9], struct.unpack_from('<4f', q, r + 0x10)


def stats_block(q, i):
    """4U boss stat block i (+0x34 + 8 i): (size %, HP row, attack row, other row); the spawns in order, the intruder's is
    block 2 (C: m10805 / m10815)"""
    o = STATS_4U + 8 * i
    return (struct.unpack_from('<H', q, o)[0],) + tuple(q[o + 3:o + 6])


def objectives_4u(q):
    """4U main objectives (+0xCB count, {u32 type, u16 target, u16 count} at +0xCC / +0xD4; 1 = hunt, 0x101 = slay a small
    monster) and the subquest record at +0xDC"""
    n = q[0xCB]
    return [struct.unpack_from('<IHH', q, 0xCC + 8 * i) for i in range(n)], struct.unpack_from('<IHH', q, 0xDC)


def quest_data(R, qid):
    return arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % qid))['loc\\quest\\questData\\questData_%07d' % qid][1]


def boss_records(qd):
    return [struct.unpack_from('<HBBBBBBBHBB', qd, 0x64 + 13 * k) for k in range(5)]


def gu_record(R, qid, gid, nth=0):
    """the nth boss record of GU ID gid in GU quest qid"""
    recs = [r for r in boss_records(quest_data(R, qid)) if r[0] == gid]
    assert len(recs) > nth, (qid, hex(gid))
    return recs[nth]


def link_names(f, qid):
    tl = f['loc\\quest\\questLink\\questLink_%07d' % qid][1]
    return tl, [tl[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]


def gu_names(R):
    """{GU English item name: [ids]} (GU id = itemData_eng index / 2; supply box lookup by name, quest4u.supp_4u)"""
    gu = gmd.gmd_strings(gear4u.gu_arc(R.read('/nativeNX/eng/arc/resident_eng.arc'))['eng\\table\\itemData_eng'])
    out = {}
    for i in range(0, len(gu), 2):
        out.setdefault(gu[i], []).append(i // 2)
    return out


def gu_items(names):
    """gu_item(4U id) -> GU id: their materials (appended IDs) and items_seltas' OTHER_4U_GU / SUBSTITUTES, else by English
    name (the first id of the name), None when GU has no such item"""
    names4 = text_4u('eng')[0]
    by_name = {n: ids[0] for n, ids in names.items()}
    ours = {}
    for name, e in items_seltas.ENTRIES.items():
        first = alloc.monster(name)['items'][0]
        ours.update({k: first + i for i, k in enumerate(e['items'])})
    ours.update(items_seltas.OTHER_4U_GU)
    ours.update(items_seltas.SUBSTITUTES)

    def gu_item(k):
        if k in ours: return ours[k]
        n = names4[k]
        if n in by_name: return by_name[n]
        print('reward: 4U %d %s has no GU item (left out)' % (k, n))
        return None
    return gu_item


def small_gu():
    """{4U small monster em: GU ID} by English name: 4U emName = GU's monster list (tools/gulib/monster-index.csv, registry
    index = list index - 1), GU ID from the registry pairs; checked against GU quests slaying Bnahabra / Konchu"""
    img = open(paths.GU_MAIN, 'rb').read()
    pairs = {i: e for e, i in (struct.unpack_from('<II', img, alloc.GU_PAIRS + 8 * k) for k in range(alloc.GU_COUNT))}
    gu = {}
    for row in csv.reader(open(os.path.join(paths.GU_PY, 'monster-index.csv'), encoding='utf-8')):
        if row and row[0].isdigit() and row[2] == 'small': gu[row[1]] = pairs[int(row[0]) - 1]
    n4 = msg4u('eng')['emName']
    zmap = {e: gu[n] for e, n in enumerate(n4) if n in gu}
    for e, (gid, _) in SMALL_CHECK.items():
        assert zmap.get(e) == gid, (e, hex(zmap.get(e, 0)), hex(gid))
    return zmap


def esl_4u(q4, zmap):
    """GU emSetList from the 4U quest's first small-monster set (+0x2C; docstring: GU emSetList) -> (bytes, records, the 4U
    species left out)"""
    tbl = struct.unpack_from('<I', q4, struct.unpack_from('<I', q4, 0x2C)[0])[0]
    names4 = msg4u('eng')['emName']
    blocks, out, i = {}, [], 0
    while tbl and struct.unpack_from('<I', q4, tbl + 4 * i)[0]:
        rec = struct.unpack_from('<I', q4, tbl + 4 * i)[0]
        while struct.unpack_from('<I', q4, rec)[0] != 0xFFFFFFFF:
            em, n = struct.unpack_from('<II', q4, rec)
            link, area, a, b = q4[rec + 8:rec + 12]
            pos = struct.unpack_from('<3f', q4, rec + 0x10)
            ang = struct.unpack_from('<H', q4, rec + 0x20)[0]
            if em in zmap:
                assert 1 <= area <= 14 and a in (1, 5) and b <= 2 and (link <= 11 or link == 255), (em, area, a, b, link)
                assert n == 255 or n <= 16, (em, n)
                blocks.setdefault(area, []).append((zmap[em], 99 if n == 255 else n, link, a, b, pos, ang))
            else:
                out.append(names4[em])
            rec += 0x28
        i += 1
    head, body = bytearray(b'esl\0' + struct.pack('<I', 2) + bytes(56)), bytearray()
    for area in sorted(blocks):
        struct.pack_into('<I', head, 8 + 4 * (area - 1), 64 + len(body))
        body += b'ESD\0' + struct.pack('<IH', 0x20151214, len(blocks[area]))
        for em, n, link, a, b, pos, ang in blocks[area]:
            body += struct.pack('<HBBBBBBBBBB3fIHHI', em, n, 0xcd, link, area, a, b, 0, 0, 0xcd, 0xcd, *pos, 0, ang, 0, 0)
    return bytes(head + body), sum(len(v) for v in blocks.values()), sorted(set(out))


def nando_gu(R):
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    return [struct.unpack_from('<8f', gu, 16 + 32 * k) for k in range((len(gu) - 16) // 32)]


def hp_4u(exe, row):
    return struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)[0]


def hp_row(rows, base_row, r):
    """GU em_nando_tbl row whose HP column is nearest base * r and not below it (Shrouded Nerscylla's double hunt rule)"""
    target = rows[base_row][0] * r
    return min((abs(rows[k][0] - target), k) for k in range(len(rows)) if rows[k][0] >= target - 1e-3)[1]


def map_only_start(supp, map_id, m4):
    """GU supp bytes with one Map at the start, as GU's village boxes (Shrouded Nerscylla's builder): the box's other start
    items go to the front of delivery group 1, the extra Maps go"""
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


def set_name(stage, gid, owner, k, slot):
    """setEmMain names, one content per name (asserted over the quests built): b_mSSemNNN_VV with VV = 60 + 4 k + slot
    (Desert Seltas' quests) or 80 + 4 k + slot (the Queen's); GU's own names stay below 60 (C: Shrouded Nerscylla's 60..
    are on em070 only)"""
    assert k < 5 and slot < 4, (k, slot)
    return 'b_m%02dem%03d_%02d' % (stage, gid & 0xff, (60 if owner == 'desert_seltas' else 80) + 4 * k + slot)


def gu_icon(R, gid):
    """GU's board icon of monster gid: the icon of a GU quest whose first boss it is (ICON_GU)"""
    q = ICON_GU[gid]
    d = quest_data(R, q)
    assert struct.unpack_from('<H', d, 0x64)[0] == gid and d[0xD6], (hex(gid), 'icon quest', q)
    return d[0xD6]


def build(R, exe, nando, gu_item, names, zmap, out, spec, hp_table=None):
    owner, k, num, tpl_id = spec['owner'], spec['k'], spec['num'], spec['tpl']
    qid = alloc.monster(owner)['quests'][k]
    sid, m4 = '%07d' % qid, 'm%05d' % num
    village = qid < 10000
    q4 = quest_4u(num)
    sp = spawns_4u(q4)
    bosses = [dict(em=s[0], count=s[1], area=s[2], pos=s[3], round=r, frenzy=s[6], block=i, slot=i)
              for i, (s, r) in enumerate(zip(sp, rounds(sp)))]
    intr = intruder_4u(q4)
    if intr:
        assert len(bosses) < INTRUDER_SLOT, (m4, 'an intruder after more than two bosses')
        bosses.append(dict(em=intr[1], count=1, area=intr[2], pos=intr[3], round=0, frenzy=0, block=INTRUDER_SLOT,
                           slot=INTRUDER_SLOT))
    assert all(b['em'] in GU_OF for b in bosses) and len(bosses) == len(spec['rows']), (m4, [b['em'] for b in bosses])
    for b in bosses:
        assert msg4u('eng')['emName'][b['em']] == NAME_4U[b['em']], (m4, b['em'])
        assert b['count'] in (1, COMPANION), (m4, b)
    stage = STAGE_GU[q4[0xC4]]
    tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
    objs, sub4 = objectives_4u(q4)

    # --- questData: the template's (rank, board, start area, flags, money), then 4U's values
    qd = bytearray(tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1])
    assert len(qd) == quest4u.QD_SIZE and qd[0x14] == spec.get('tpl_stage', stage), (tpl_id, 'not on the stage')
    assert qd[0x11] == 10 and qd[0x13] == 5 and (tpl_id < 10000) == village, (tpl_id, 'board / rank / board family')
    assert not struct.unpack_from('<H', qd, 0x16F)[0] & URGENT, (tpl_id, 'template is an urgent quest')
    assert not any(qd[0xAD:0xCC]), (tpl_id, 'template with more spawn settings than the +0xA8 condition')
    qd[0x14] = stage
    struct.pack_into('<I', qd, 0x0C, qid)
    qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]       # minutes (4U)
    qd[0xA8:0xAD] = bytes(5)                                # GU's spawn condition (docstring: Intruder)
    # objectives: hunt (1), slay a small monster (0x101), 4U's hunt all (+0xA0 8)
    if objs[0][0] == 0x101:
        assert len(objs) == 1 and objs[0][1] in zmap, (m4, objs)
        kind, targets = 'slay', [(1, zmap[objs[0][1]], objs[0][2])]
    elif q4[0xA0] == 8:
        kind, targets = 'hunt all', [(1, GU_OF[b['em']][1], 1) for b in bosses if b['count'] != COMPANION]
        assert len(objs) == 1 and objs[0][0] == 1 and objs[0][1] in [b['em'] for b in bosses if b['count'] != COMPANION], \
            (m4, objs)
    else:
        assert all(t == 1 for t, _, _ in objs), (m4, objs)
        kind, targets = 'hunt', [(1, GU_OF[e][1], n) for t, e, n in objs]
    assert 1 <= len(targets) <= 2, (m4, targets)
    qd[0x1D] = len(targets) - 1                             # two targets: rule 1, both (GU's two-target hunts, q11111)
    qd[0x1F:0x29] = bytes(10)
    for i, t in enumerate(targets):
        struct.pack_into('<BHH', qd, 0x1F + 5 * i, *t)
    # subquest
    sub, sub_text = spec.get('sub'), None
    if not sub:
        assert not sub4[0], (m4, 'a 4U subquest without a spec', sub4)
        qd[0x29:0x2E] = bytes(5)
        for o in (0x3D, 0x49, 0x51):                        # sub reward, sub academy points, sub HRP
            struct.pack_into('<I', qd, o, 0)
    elif sub[0] == 'break':
        assert sub4[0] == 0x204 and sub4[1] == sub[1], (m4, 'the 4U subquest is not this wound', sub4)
        struct.pack_into('<BHH', qd, 0x29, 8, GU_OF[sub[1]][1], sub[2])
    elif sub[0] == 'deliver':
        assert sub4[0] == 2 and sub4[1] == sub[1], (m4, 'the 4U subquest is not this delivery', sub4)
        item = gu_item(sub[1])
        assert item is not None, (m4, '4U item %d has no GU item' % sub[1])
        struct.pack_into('<BHH', qd, 0x29, 5, item, sub4[2])
    elif sub[0] == 'slay':
        assert sub4[0] == 0x101 and sub4[1] == sub[1], (m4, 'the 4U subquest is not this small-monster hunt', sub4)
        struct.pack_into('<BHH', qd, 0x29, 1, zmap[sub[1]], sub4[2])
    else:                                                   # 'like': another 4U quest's subquest and text
        assert sub[0] == 'like' and sub4[0] == 0x4004, (m4, 'not the frenzy subquest', sub4)
        oq = quest_4u(sub[1])
        o_sub = objectives_4u(oq)[1]
        assert o_sub[0] == 0x204 and o_sub[1] == sub[2], (sub, o_sub)
        struct.pack_into('<BHH', qd, 0x29, 8, GU_OF[sub[2]][1], sub[3])
        sub_text = {lang: strs[6] for lang, strs in text4u(oq).items()}
    if spec.get('sub_money'):              # the sub money of a GU quest of this rank with this kind of subquest
        mq = quest_data(R, spec['sub_money'])
        assert (mq[0x12], mq[0x13], mq[0x29]) == (qd[0x12], qd[0x13], qd[0x29]), ('sub_money of another rank / kind', mq[0x29])
        for o in (0x3D, 0x49, 0x51):
            qd[o:o + 4] = mq[o:o + 4]
    if village:
        assert not struct.unpack_from('<I', qd, 0x3D)[0] and not spec.get('supp_tpl'), (m4, 'village template with sub money')
        supp, groups = quest4u.supp_4u(q4, text_4u('eng')[0], names)
        qd[0x58:0x60] = groups or bytes(8)
        supp = map_only_start(supp, names['Map'][0], m4)
        ia, ib, supp = names['Hot Drink'][0], names['Cool Drink'][0], bytearray(supp)
        hits = [s for s in range(40) if struct.unpack_from('<H', supp, 8 + 4 * s)[0] == ia] if stage == 5 else []
        for s in hits:
            struct.pack_into('<H', supp, 8 + 4 * s, ib)
        supp = bytes(supp)
        box = 'the 4U box, one Map at the start%s' % (', %d Hot Drink slot(s) -> Cool Drink' % len(hits) if hits else '')
    else:                                                   # a GU hub box (4 players) with its delivery groups
        st_id = spec.get('supp_tpl', tpl_id)
        st = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % st_id))
        supp = st['quest\\supp\\' + link_names(st, st_id)[1][13]][1]
        sq = st['loc\\quest\\questData\\questData_%07d' % st_id][1]
        assert (sq[0x12], sq[0x13], sq[0x1F], sq[0x14]) == (qd[0x12], qd[0x13], qd[0x1F], stage), (
            'supp_tpl of another rank / objective type / map', st_id)
        qd[0x58:0x60] = sq[0x58:0x60]
        box = 'GU q%d' % st_id

    # --- boss records: GU's own record of the species (rows, restore, difficulty, size table, stamina), 4U's size
    recs, info = [bytes(13)] * 5, []
    for i, b in enumerate(bosses):
        named = ALT if (b['em'] == 94 and qid == ALT_QUEST) else GU_OF[b['em']][0]
        row = spec['rows'][i]
        base = gu_record(R, row[0], row[1], row[2] if len(row) > 2 else 0)
        assert base[1] == 0 and base[2] == 0, (row, 'GU base record with a subtype / aura')
        assert (b['count'] == COMPANION) == (base[3] > 1), (m4, b['em'], 'restore count against the 4U count', base)
        hp, note = base[4], ''
        if i in spec.get('ratio', {}):
            rq, ri = spec['ratio'][i]
            r = hp_4u(exe, stats_block(q4, b['block'])[1]) / hp_4u(exe, stats_block(quest_4u(rq), ri)[1])
            hp = hp_row(nando, base[4], r)
            note = ' (HP row %d x %.3f, against 4U m%05d)' % (base[4], r, rq)
        if hp_table is not None and b['em'] in (94, 95): hp = hp_table
        size = stats_block(q4, b['block'])[0] or 100
        recs[b['slot']] = struct.pack('<HBBBBBBBHBB', named, 0, 0, base[3], hp, base[5], base[6], base[7], size, base[9],
                                      base[10])
        info.append('slot %d %#x %d/%d/%d restore %d size %d round %d%s' % (
            b['slot'], named, hp, base[5], base[6], base[3], size, b['round'], note))
    qd[0x64:0x64 + 65] = b''.join(recs)
    flags = struct.unpack_from('<H', qd, 0x16F)[0]
    if intr:
        dq = quest_data(R, INTRUDER_DONOR)
        drec = boss_records(dq)
        assert [s for s in range(5) if drec[s][0]] == [0, INTRUDER_SLOT] and struct.unpack_from('<H', dq, 0x16F)[0] & INTRUDER_FLAG
        assert (dq[0x12], dq[0x13]) == (11, qd[0x13]), ('intruder donor of another rank', INTRUDER_DONOR)
        qd[0xCC:0xD4] = dq[0xCC:0xD4]
        flags |= INTRUDER_FLAG
    else:
        qd[0xCC:0xD4] = bytes(8)
        flags &= ~INTRUDER_FLAG
    struct.pack_into('<H', qd, 0x16F, flags)
    icons = []
    if kind == 'slay':                     # the small monster's icon first (q11217: [Ioprey 82, 106])
        d = quest_data(R, ICON_SMALL[targets[0][1]])
        assert struct.unpack_from('<BH', d, 0x1F) == (1, targets[0][1]) and d[0xD6], 'small-monster icon quest'
        icons.append(d[0xD6])
    for b in bosses:
        if intr and b['slot'] == INTRUDER_SLOT: icons.append(INTRUDER_ICON)
        else: icons.append(ICON[b['em']] if b['em'] in ICON else gu_icon(R, GU_OF[b['em']][1]))
    qd[0xD6:0xDB] = bytes((icons + [0] * 5)[:5])
    for i, lang in enumerate(quest4u.QLANGS):
        qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))

    # --- questLink + resources: 15 refs = 5 setEmMain, 3 emSetList, 5 rem (A, B, slot 3, slot 4, subquest), supp, questPlus
    tlink, tnames = link_names(tpl, tpl_id)
    assert tnames[0] != 'b_m00em000_00', tpl_id
    base_set = tpl['quest\\boss\\setEmMain\\' + tnames[0]][1]
    res, setrefs = [], ['b_m00em000_00'] * 5
    for b in bosses:                       # the template's first setEmMain (C: GU's records differ only in round / area /
        se = bytearray(base_set)           # rotation / position), 4U's area and floats, the round
        x, y, z, rot = b['pos']
        struct.pack_into('<I', se, 8, b['round'])
        struct.pack_into('<I4f', se, 0x0C, b['area'], rot, x, y, z)
        named = ALT if (b['em'] == 94 and qid == ALT_QUEST) else GU_OF[b['em']][0]
        n = set_name(stage, named, owner, k, b['slot'])
        assert _SETS.setdefault(n, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % n)
        res.append(('quest\\boss\\setEmMain\\' + n, T_SET, bytes(se)))
        setrefs[b['slot']] = n
    res.append(('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]))
    # small monsters: 4U's first set
    esl_data, nzak, zak_out = esl_4u(q4, zmap)
    esl = ['z_m%02dd_%d' % (stage, qid), 'z_m00d_000', 'z_m00d_000']
    res.append(('quest\\zako\\emSetList\\' + esl[0], T_ESL, esl_data))
    res.append(('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1]))
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
    link = tlink[:8] + b''.join(ref(T_SET, n) for n in setrefs) + b''.join(ref(T_ESL, n) for n in esl)
    link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, plus)
    assert len(link) == 308

    # --- text (4U, 5 languages) + arc layout + files (tools/quest4u.py)
    t4 = text4u(q4)
    if num == 10928:                       # 4U's text names a Shrouded Nerscylla (em 96), its file spawns the Cephadrome (105)
        for lang, strs in t4.items():
            nm = msg4u(lang)['emName']
            old = nm[96]
            if lang == 'ger':              # accusative after "einen": the adjective's -er -> -en (4U m00715 "einen Cephadrome")
                old = re.sub(r'er\b', 'en', old, count=1)
            hits = [i for i, s in enumerate(strs) if old in s]
            assert hits == [1] and nm[105] not in strs[1], (lang, 'objective text', hits)
            strs[1] = strs[1].replace(old, nm[105])
    if sub_text:
        for lang, s in sub_text.items():
            t4[lang][6] = s
    gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
    qd = bytes(qd)
    quest4u.write(out, quest4u.assemble(res, link, gmds, qd, sid))
    frenzy = [hex(GU_OF[b['em']][1]) for b in bosses if b['frenzy']]
    print('quest %d = 4U %s (tpl q%d): star %d class %d stage %d, %d min, %s %s rule %d, sub %s; bosses %s; spawns %s; '
          'icons %s; box %s; small monsters %d%s%s%s; "%s"' % (
              qid, m4, tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], kind, qd[0x1F:0x29].hex(' '), qd[0x1D],
              qd[0x29:0x2E].hex(' '), info, [(b['slot'], b['area']) for b in bosses], list(qd[0xD6:0xDB]), box, nzak,
              ' (left out: %s)' % ', '.join(zak_out) if zak_out else '',
              '; intruder %#x at 4U %d %%, GU q%d\'s +0xCC %s' % (GU_OF[intr[1]][1], intr[0], INTRUDER_DONOR,
                                                                   qd[0xCC:0xD4].hex(' ')) if intr else '',
              '; 4U frenzy of %s DROPPED (deviation)' % ', '.join(frenzy) if frenzy else '', t4['eng'][0]))


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
    zmap = small_gu()
    for e, (gid, q) in SMALL_CHECK.items():
        d = quest_data(R, q)
        assert gid in (struct.unpack_from('<H', d, 0x20)[0], struct.unpack_from('<H', d, 0x2A)[0]), (e, q)
    nando = nando_gu(R)
    for spec in QUESTS:
        if a.only in (None, alloc.monster(spec['owner'])['quests'][spec['k']]):
            build(R, exe, nando, gu_item, names, zmap, a.out, spec, a.hp_table)


if __name__ == '__main__':
    main()
