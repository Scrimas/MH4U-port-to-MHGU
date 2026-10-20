"""quest4u.py : MH4U quest data -> MHGU quest files, shared by the monsters' quest builders
(monsters/<name>/tools/build_*_quest.py). Formats (layouts checked on GU's own quests; Gogmazios' notes/stage.md):

questData (329 B, little endian; MHXX rQuestData layout, mhff wiki):
  +0x00 'KC' header (u32 0x434b0000, u32 1, u32 0)  +0x0C u32 quest id
  +0x10 type  +0x11 board (10 = every board)  +0x12 stars (14 = G4)  +0x13 rank tier  +0x14 stage  +0x15 start area
  +0x16 minutes  +0x17 carts  +0x1A BGM/flags  +0x1F objective type (1 hunt)
  +0x20 u16 target  +0x22 u16 count  +0x24 objective 2  +0x29 subquest (type, u16 target, u16 code)
  +0x31 fee  +0x39 reward  +0x3D sub reward  +0x41 academy pts (reward x 0.08 in G)  +0x49 sub academy  +0x4D HRP
  +0x51 sub HRP  +0x58 supply deliveries  +0x64 5 x 13 B boss {u16 em id, u8 subtype, u8 aura, u8 restore count,
  u8 vital/attack/other table, u8 difficulty, u16 size %, u8 size table, u8 stamina}  +0xA5 small monster tables
  +0xD6 5 icons  +0xDF 5 x {u32 GMD type 0x242bb29a, char[16] "<ID>_<lang>"}  +0x147 u16 flags (bit 7 = no rotation)
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
FILLER_LANGS = ['jpn', 'kor']      # arc padding only (v1.4 positional questLink lookup, see assemble())
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


def quest_gmds(tpl, tpl_id, sid, t4):
    """questData_<sid>_<lang> GMDs from the 4U text (text4u), the template's unk word; checks first that the GMD writer
    reproduces the template's files byte for byte"""
    for lang in LANGS:
        d = tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, tpl_id, lang)][1]
        name, strs, unk = gmd_unpack(d)
        assert gmd(name, [s.decode('utf-8') for s in strs], unk) == d, lang
    gmds = {}
    for lang in LANGS:
        title, obj, fail, desc, other, client, sub = t4[lang]
        unk = gmd_unpack(tpl['%s\\quest\\questData\\questData_%07d_%s' % (lang, tpl_id, lang)][1])[2]
        gmds[lang] = gmd('questData_' + sid, [title, client, desc, other, obj, fail, sub], unk)
    return gmds


def assemble(res, link, gmds, qd, sid):
    """quest arc + loose files -> {RomFS path under nativeNX: bytes}. res = [(path, type, data)] of the resources
    questLink names. v1.4 positional layout: questData = arc entry [count-1] (0x3ba6dc), questLink = [count-9]
    (0x3ba840, path must contain "Link"; v1.0 used [count-7]); a v1.0 template has 7 entries from questLink to
    questData, so 2 inert GMDs (English text, language folders the game never asks for) fill the gap: without them
    questLink is null and 0x3ade34 skips the whole quest setup."""
    ents = res + [('loc\\quest\\questLink\\questLink_' + sid, T_LINK, link)]
    ents += [('%s\\quest\\questData\\questData_%s_%s' % (l, sid, l), T_GMD, gmds[l]) for l in LANGS]
    ents += [('%s\\quest\\questData\\questData_%s_%s' % (l, sid, l), T_GMD, gmds['eng']) for l in FILLER_LANGS]
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
