"""quest4u.py : MH4U quest data -> MHGU quest files, shared by the monsters' quest builders
(monsters/<name>/tools/build_*_quest.py). Formats (layouts checked on GU's own quests; Gogmazios' notes/stage.md):

questData (v1.4: 369 B, little endian; MHXX rQuestData layout, mhff wiki; v1.0 had 329 B, without the chT / chS refs):
  +0x00 'KC' header (u32 0x434b0000, u32 1, u32 0)  +0x0C u32 quest id
  +0x10 type  +0x11 board (10 = every board)  +0x12 stars (14 = G4)  +0x13 rank tier  +0x14 stage  +0x15 start area
  +0x16 minutes  +0x17 carts  +0x1A BGM/flags  +0x1F objective type (1 hunt)
  +0x20 u16 target  +0x22 u16 count  +0x24 objective 2  +0x29 subquest (type, u16 target, u16 code)
  +0x31 fee  +0x39 reward  +0x3D sub reward  +0x41 academy pts (reward x 0.08 in G)  +0x49 sub academy  +0x4D HRP
  +0x51 sub HRP  +0x58 supply deliveries  +0x64 5 x 13 B boss {u16 em id, u8 subtype, u8 aura, u8 restore count,
  u8 vital/attack/other table, u8 difficulty, u16 size %, u8 size table, u8 stamina}  +0xA5 small monster tables
  +0xD6 5 icons  +0xDF 7 x {u32 GMD type 0x242bb29a, char[16] "<ID>_<lang>"} (QLANGS order)
  +0x16F u16 flags (bit 7 = no rotation; +0x147 in v1.0)
questLink (308 B): 'KC' header, 13 x {u32 type, char[16] name}: 5 setEmMain, 3 emSetList, 5 rem, supp, questPlus.
GMD (v0x10302): 'GMD\\0', u32 version, u32 lang 0, u32 unk (copied from the template), u64 0, u32 strings,
  u32 labels 0, u32 string bytes, u32 name length, name\\0, UTF-8 strings. 7 strings: title, client, description,
  other monsters, main objective, failure, subquest.
Quest arc (loc/arc/quest/q<ID>.arc): v1.4 finds questLink at entry [count-9] and questData at [count-1] (0x3ba840 /
  0x3ba6dc; v1.0 used [count-7]): v1.0-layout templates get 2 inert filler GMDs (assemble()).
4U quest (loc/data/questNN.arc loc\\quest\\mNNNNN, 'v005'): 5 language tables (pointer +0xBC: eng fre spa ger ita),
  7 strings each; reward rows: header +0x1C row A, +0x20 row B, +0x24 subquest -> list {u32 0x8000, u32 table}
  closed by 0xFFFF, table = 6-byte {u16 chance, u16 item, u16 count} closed by 0xFFFF; fee / reward / sub reward
  +0xA4 / +0xA8 / +0xAC, minutes +0xB4, quest number +0xC0, stage +0xC4; boss stats +0x34 (stats_4u); +0xE8 5 x u16
  board icons (98 = none), not stat rows.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack

LANGS = ['eng', 'fre', 'ger', 'ita', 'spa']
QLANGS = LANGS + ['chT', 'chS']     # quest text languages of v1.4 (questData refs + arc GMDs); 4U has no Chinese:
                                    # lang/zh_TW.toml / zh_CN.toml [quests] (tools/translate.py), else English
QD_SIZE = 369                      # v1.4 questData (the templates come from the v1.4 RomFS)
LANG4U = {'eng': 0, 'fre': 1, 'spa': 2, 'ger': 3, 'ita': 4}    # order of a 4U quest's language tables (+0xBC)
T_SET, T_ESL, T_REM, T_SUPP, T_PLUS, T_LINK, T_GMD, T_QD = (
    0x2553701d, 0x32ca92f8, 0x5b3c302d, 0x54539aee, 0x26bec21c, 0x00e0bb1c, 0x242bb29a, 0x1bbfd18e)
REWARD_ROWS_4U = (0x1C, 0x20)
SUB_ROW_4U = 0x24
STATS_4U = 0x34
NANDO_4U = 0xf3a330                # 4U em_nando_tbl, 32-B rows {HP, attack, other: defense + 5 status} (f32)


def arc_files(data):
    return {p: (t, d) for p, t, d in arcpack.read(data)[1]}


def stats_4u(q, R):
    """a 4U quest's boss stat rows (HP, attack, other) for the GU boss record, R = GU RomFS. 4U +0x34 = {u16 size %,
    u8, u8 HP, u8 attack, u8 other, u8, u8}; the spawn copies the three rows in this order to monster work +0x414..
    +0x416 (0x68aa30), read by the HP setup 0x934084 (column 0), attack 0x922d48 (column 1), defense 0x922d78 and the
    status code 0x91ca94 (columns 2..7). GU's em_nando_tbl (resident.arc, 16-B header) holds most of 4U's rows under
    the same numbers but not all (row 98: HP 4.3 in 4U, 3.4 in GU): checked here column by column."""
    from items4u import EXE, EXE_BASE
    rows = tuple(q[STATS_4U + 3:STATS_4U + 6])
    exe = open(EXE, 'rb').read()
    gu = {p: d for p, t, d in arcpack.read(R.read('/nativeNX/loc/arc/resident.arc'))[1]}['enemy\\resident\\em_nando_tbl']
    for row, cols in zip(rows, ((0,), (1,), range(2, 8))):
        r4 = struct.unpack_from('<8f', exe, NANDO_4U - EXE_BASE + 32 * row)
        rg = struct.unpack_from('<8f', gu, 16 + 32 * row)
        assert all(r4[c] == rg[c] for c in cols), ('GU row differs from 4U', row, r4, rg)
    return rows


def text4u(q):
    """a 4U quest's 5 language blocks -> {lang: [title, objective, failure, description, other, client, subquest]}"""
    out = {}
    langs = struct.unpack_from('<I', q, 0xBC)[0]          # -> 5 language tables
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


def rem_4u(q, row, gu_item):
    """one 4U reward row (quest header offset) -> GU rem, 184 B: f32 1.0, u32 1, 8 x {u8 condition, u8 entries}
    groups, then each group's {u16 item, u8 count, u8 chance} entries closed by {0, 0, 0xFF}. A 4U row is one group;
    condition 1 = the plain groups of GU's rows A / B (q0011413 rem_130240 adds a condition-4 group, rem_230088 not).
    gu_item(4U id) -> GU id or None: a 4U item with no GU item is left out and its chance goes to the row's most likely
    item (the row stays 100 %). 4U list flags: 0x8000, or 0x8003 on 130 of the 4U row-B lists (gathering items, ores,
    spheres; meaning not traced) -> condition 1 too: GU's hunts put that kind of row B under condition 1 (G Zamtrios
    11207: spheres, charms, jewels); GU's condition-2 rows B are on its other quest types."""
    lst = struct.unpack_from('<I', q, row)[0]
    flags, off = struct.unpack_from('<II', q, lst)
    assert flags in (0x8000, 0x8003) and struct.unpack_from('<H', q, lst + 8)[0] == 0xFFFF, 'unexpected 4U reward list'
    ents, lost = [], 0
    while struct.unpack_from('<H', q, off)[0] != 0xFFFF:
        chance, item, count = struct.unpack_from('<HHH', q, off)
        gu = gu_item(item)
        if gu is None:
            lost += chance
            print('reward row %#x: 4U item %d has no GU item, its %d %% goes to the most likely item' % (row, item, chance))
        else:
            ents.append([gu, count, chance])
        off += 6
    max(ents, key=lambda e: e[2])[2] += lost
    # a 4U row above 100 % (event m60213 row A: 102): read as rolled out of 100 down the list (G: 4U's roll not
    # traced), so what lies past 100 is cut, entries past it are unreachable and left out
    over, kept = sum(e[2] for e in ents) - 100, []
    if over > 0:
        print('reward row %#x: 4U chances total %d %%, the last %d %% cut (rolled out of 100, G)' % (row, 100 + over,
                                                                                                    over))
        for e in ents:
            e[2] = min(e[2], 100 - sum(k[2] for k in kept))
            if e[2]: kept.append(e)
        ents = kept
    assert sum(e[2] for e in ents) == 100 and len(ents) <= 40, ents
    body = b''.join(struct.pack('<HBB', *e) for e in ents)
    d = struct.pack('<fI', 1.0, 1) + bytes([1, len(ents)]) + bytes(14) + body + struct.pack('<HBB', 0, 0, 0xFF)
    return d + bytes(184 - len(d))


# Supply box (issue #11). 4U quest header +0x08 -> list of 8-byte {u8 kind, u8 slots, u16, u32 table} closed by kind
# 0xff; a table = {u16 item, u16 count} slots (0 = empty): 32 for the box, 8 for the delivery. Gogmazios m11014 / m11035 (C, data): kind 0 -> the box (Map,
# First-aid Med+, Ration, Cleanser, ...: the reporter's 4U box), kinds 1..3 -> one second table (7 / 8 items, the
# later delivery; its trigger is not traced, G). GU supp (168 B): f32 1.0, u32 1, 40 x {u16 item, u8 count, u8 group};
# a nonzero group byte starts a delivery group, the slots before it are the box at start; questData +0x58..+0x5f
# hold the groups' conditions (S, survey of the 1854 v1.4 quests: 869 have no group, 468 `01 01 00 00 00 00 04 04` with
# group 1 at slot 4 (4 Maps at start = q0011413, the old template: "only Maps") and group 4 at slot 32, 219
# `00 00 00 00 00 00 04 04` with only group 4 at slot 32). Here (C, 2026-11-01: 4U HR / G quests of Black Gravios,
# kind 0 = Maps / Torches / Cool Drinks, kind 1 = the supplies, kind 3 = the restock, the
# layout of GU's own HR / G boxes, e.g. q11107: Maps at start, group 1 at slot 4, group 4 at slot 32): 4U kind 0 = the
# box at start, kind 1 right after it as group 1 (the first delivery), kind 3 from slot 32 as group 4, questData +0x58
# = SUPP_QD_1 with a group 1, else SUPP_QD. Until 2026-11-01 kinds 0 and 1 were both in the box at start (user: "you
# get every item at once"); Gogmazios' boxes (kind 1 empty) are unchanged.
SUPP_QD = bytes([0, 0, 0, 0, 0, 0, 4, 4])
SUPP_QD_1 = bytes([1, 1, 0, 0, 0, 0, 4, 4])
SUPP_GU_NAME = {'Power Coating': 'Power Coating Lv1',      # GU splits coatings into Lv1 / Lv2; GU's own boxes use Lv1
                'Water S': 'Water S Lv1'}                  # 4U's one Water S level (Black Gravios m10923): GU's Lv1


def supp_4u(q, names4u, gu_ids, log=print):
    """4U quest -> (GU supp bytes, questData +0x58..+0x5f for its delivery groups or None: none). names4u = 4U item
    names (items4u.text_4u), gu_ids = {GU name: [ids]} (the first id wins: e.g. Normal S Lv2 0x65 as GU's boxes, not
    0x85). A 4U item GU lacks (4U Torch) is left out."""
    # entry byte +1 = the table's slot count (S, Black Gravios' 4U quests 2026-11-01: kinds 0 / 1 / 2 / 3 = 12 / 20 /
    # 0 / 8 or 8 / 24 / 0 / 8 slots, kinds 0 + 1 = 32 = the box; Gogmazios' 32 / 0 / 0 / 8, kinds 1..3 on one table):
    # the box = kind 0's slots then kind 1's, the delivery = kind 3's (kind 2 has none in every quest read)
    lst, ents = struct.unpack_from('<I', q, 8)[0], {}
    while q[lst] != 0xFF:
        ents[q[lst]] = (q[lst + 1], struct.unpack_from('<I', q, lst + 4)[0])
        lst += 8
    assert set(ents) <= {0, 1, 2, 3} and 0 in ents and ents[0][0] + ents.get(1, (0,))[0] <= 32 and \
        ents.get(2, (0,))[0] == 0 and ents.get(3, (0,))[0] <= 8, 'unexpected 4U supply list %s' % ents

    def table(t, slots):
        out = []
        for i in range(slots):
            item, n = struct.unpack_from('<HH', q, t + 4 * i)
            if not item: continue
            name = names4u[item]
            ids = gu_ids.get(SUPP_GU_NAME.get(name, name))
            if not ids:
                log('supply: 4U item %d %s has no GU item, left out' % (item, name)); continue
            out.append((ids[0], n))
        return out
    box = table(ents[0][1], ents[0][0])
    first = table(ents[1][1], ents[1][0]) if 1 in ents else []    # the first delivery (group 1)
    later = table(ents[3][1], ents[3][0]) if 3 in ents else []    # 8 slots: m11035's runs into the list at +0x80
    assert len(box) + len(first) <= 32 and len(later) <= 8 and all(n < 256 for _, n in box + first + later)
    slots = [(i, n, 0) for i, n in box] + [(i, n, 1 if k == 0 else 0) for k, (i, n) in enumerate(first)]
    slots += [(0, 0, 0)] * (32 - len(slots))
    slots += [(i, n, 4 if k == 0 else 0) for k, (i, n) in enumerate(later)] + [(0, 0, 0)] * (8 - len(later))
    groups = (SUPP_QD_1 if later else SUPP_QD_1[:6] + bytes(2)) if first else SUPP_QD if later else None
    return struct.pack('<fI', 1.0, 1) + b''.join(struct.pack('<HBB', *s) for s in slots), groups


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


def quest_gmds(tpl, tpl_id, sid, t4):
    """questData_<sid>_<lang> GMDs from the 4U text (text4u), the template's unk word; checks first that the GMD writer
    reproduces the template's files byte for byte"""
    for lang in QLANGS:
        d = tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, tpl_id, lang)][1]
        name, strs, unk = gmd_unpack(d)
        assert gmd(name, [s.decode('utf-8') for s in strs], unk) == d, lang
    import translate
    gmds, missing = {}, []
    for lang in QLANGS:
        title, obj, fail, desc, other, client, sub = t4[lang if lang in LANGS else 'eng']
        strs = [title, client, desc, other, obj, fail, sub]       # translate.QUEST_FIELDS order
        if lang not in LANGS:
            strs = [translate.game_text(lang, 'quests', '%d.%s' % (int(sid), f), s, missing) if s else s
                    for f, s in zip(translate.QUEST_FIELDS, strs)]
        unk = gmd_unpack(tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, tpl_id, lang)][1])[2]
        gmds[lang] = gmd('questData_' + sid, strs, unk)
    if missing: print('quest %s: %d strings without a translation (English shown; tools/translate.py check)' % (sid, len(missing)))
    return gmds


def assemble(res, link, gmds, qd, sid):
    """quest arc + loose files -> {RomFS path under nativeNX: bytes}. res = [(path, type, data)] of the resources
    questLink names. v1.4 positional layout: questData = arc entry [count-1] (0x3ba6dc), questLink = [count-9]
    (0x3ba840, path must contain "Link"; v1.0 used [count-7]): questLink, the 7 QLANGS GMDs, questData, as GU's own
    v1.4 quests (without the 9 entries questLink is null and 0x3ade34 skips the whole quest setup). Loose GMDs: the 5
    LANGS only (v1.4 has no loose chT / chS quest text)."""
    ents = res + [('loc\\quest\\questLink\\questLink_' + sid, T_LINK, link)]
    ents += [('%s\\quest\\questData\\questData_%s_%s' % (l, sid, l), T_GMD, gmds[l]) for l in QLANGS]
    assert len(qd) == QD_SIZE
    ents += [('loc\\quest\\questData\\questData_' + sid, T_QD, qd)]
    assert len(ents) >= 9 and ents[-9][1] == T_LINK and 'Link' in ents[-9][0] and ents[-1][1] == T_QD
    arc = arcpack.build(ents)
    assert arc_files(arc) == {p: (t, d) for p, t, d in ents}
    files = {'loc/arc/quest/q%s.arc' % sid: arc,
             'loc/quest/questData/questData_%s.ext' % sid: qd,
             'loc/quest/questLink/questLink_%s.qdl' % sid: link}
    files.update({'%s/quest/questData/questData_%s_%s.gmd' % (l, sid, l): gmds[l] for l in LANGS})
    return files


def write(out_romfs, files):
    """files of assemble() -> <out_romfs>/nativeNX/..."""
    out = os.path.join(out_romfs, 'nativeNX')
    for rel, data in files.items():
        p = os.path.join(out, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        print('%6d %s' % (len(data), p))
