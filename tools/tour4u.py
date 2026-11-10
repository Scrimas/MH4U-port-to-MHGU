"""tour4u.py : a map's Harvest Tours from MH4U's (maps/<map>/package.toml [[tour]], allocations.toml [[map]] quests).

  python3 tools/tour4u.py MAP [--out DIR] [--only ID]      default DIR = maps/MAP/romfs

Writes per quest the quest arc, loose questData / questLink and the 7 GMDs (tools/quest4u.py assemble / write), as the
monsters' quest builders do. A tour is GU's own tour of the same board and rank (`template`: its questData, rewards,
supply box, questPlus, board icons, GMD words) on the map's stage alias (package.toml gu_stage; module/stage_alias.c
loads the map while it runs), with 4U's (`from_4u`):
  - minutes (4U +0xB4) and text (5 languages; chT / chS from lang/zh_*.toml [quests], keyed by the board's quest);
  - the intruders, in GU's own intruder system (QD_INTRUDE: GU rolls them, online as in its own quests). GU's tours
    have one, in boss slot 2 with its setEmMain record {f32 1.0, u32 1, u32 0, u32 area, f32 rotation, x, y, z} (C:
    q821 / q10502 / q11343). 4U's list (header +0x30, 0x2C-byte records {u32 weight, u32 em, u32 n, u8, u8 area, ..,
    f32 x, y, z @0x14, u16 angle @0x24} closed by weight 0xffff, C) holds every possible intruder with its weight: the
    entries of weight > 0 go to slots 2, 3, 4 with their weights, 4U's chance and timing (intrude_4u) to GU's fields.
    Each boss record is the template's slot 2 (its rows: GU's intruder stats at that rank) naming the 4U intruder's GU
    monster (same English name; 4U em043 = Savage Deviljho, S: 4U's caravan quest m01004 "Devil at Heaven's Gate"
    spawns it); the spot is 4U's area, x / y / z, and its 16-bit angle in degrees (GU's tours: -129, -100, S). 4U also
    rolls a second intruder among the entries left (NEWSAVE_MAPREWORK.md C6b); whether GU's roll does is to check (G);
  - the small monsters: 4U's per-area lists (the template's sets sit on GU terrain), species by English name, the
    ones GU lacks left out (logged);
  - the subquest (4U +0xDC; m806 / m10907 "Hunt a Congalala", type 1 {em, count}, C): GU type 1 {target, count} (its
    hunt objective's type, S) with 4U's subquest reward row (+0x24) in GU items of the same English name; GU's tour
    templates have none, so the subquest's money and points stay the template's 0 (G: a deviation if 4U pays some).
The main reward row stays the template's rem_210013: GU's own version of 4U's tour row A (the same Mystery Bone,
Worm, Raw Meat and Whetstone, GU's Jellies for 4U's nectars, C: 4U m806 / m10515 / m10907 row A against it).
Entries with weight 0 are left out: 4U never spawns them (C: its roll 0x69e0cc can't pick a weight of 0; the
maintainer, 2026-11-10: keep them dropped, NEWSAVE_MAPREWORK.md D7).
setEmMain / emSetList names are global (one content per name, as GU's): b_m<stage>em<GU em>_9<k> / z_m<stage>d_95<k>
for tour k of the map, which no GU file and no monster builder uses (asserted against the RomFS).
"""
import argparse, csv, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths, quest4u                        # noqa: E402
sys.path.insert(0, paths.GU_PY)
sys.path.insert(0, os.path.join(paths.ROOT, 'monsters', 'stygian_zinogre', 'tools'))
from romfs import RomFS                             # noqa: E402
from quest4u import arc_files, ref, T_SET, T_ESL, T_REM, T_SUPP, T_PLUS   # noqa: E402
from items4u import msg4u                           # noqa: E402
# the 4U quest readers of the reference quest builder (4U ROM / DLC quests, small-monster lists, GU emSetList)
from build_em057_01_quest import quest_4u, zako_4u, esl_gu, objectives_4u   # noqa: E402
import gear4u                                       # noqa: E402
from items4u import text_4u                         # noqa: E402

INTRUDERS_4U = 0x30
# GU's intruder fields (questData, S: MHGen's rQuestData names, svanheulen/mhxqe mhgen_editor.js, matched on GU's own
# quests: every quest with intruders has them, weights summing to 100 over its occupied slots 2..4; GU's tours: 100 %,
# minute 0, 100 %, slot 2 at 100): +0xCC chance (%), +0xCD first minute, +0xCE first check's chance (%), +0xCF..+0xD1
# limits of slots 2..4 (0 on tours; G: meaning), +0xD2..+0xD4 weights of slots 2..4
QD_INTRUDE = 0xCC
INTRUDER_SLOTS = (2, 3, 4)
NAME_4U = {43: 'Savage Deviljho'}                   # 4U emName names the variant like its base (both "Deviljho")


def gu_ems(R):
    """{English name: GU em ID} of GU's registry (index -> ID pairs, tools/gulib/monster-index.csv names)"""
    img = open(paths.GU_MAIN, 'rb').read()
    pairs = {struct.unpack_from('<II', img, alloc.GU_PAIRS + 8 * i)[1]: struct.unpack_from('<II', img,
             alloc.GU_PAIRS + 8 * i)[0] for i in range(alloc.GU_COUNT)}
    out = {}
    for row in csv.DictReader(open(os.path.join(paths.GU_PY, 'monster-index.csv'), encoding='utf-8')):
        idx = int(row['index']) - 1
        if idx in pairs: out.setdefault(row['monster'], pairs[idx])
    return out


def intruders_4u(q):
    """[(weight, em, area, (x, y, z), angle)] of a 4U tour"""
    o, out = struct.unpack_from('<I', q, INTRUDERS_4U)[0], []
    while o and struct.unpack_from('<I', q, o)[0] != 0xffff:
        w, em, _ = struct.unpack_from('<III', q, o)
        out.append((w, em, q[o + 13], struct.unpack_from('<3f', q, o + 0x14), struct.unpack_from('<H', q, o + 0x24)[0]))
        o += 0x2C
    assert sum(w for w, *_ in out) == 100, out
    return out


def intrude_4u(q):
    """(chance %, first minute, first check's chance %) of a 4U quest's intruders (C, 4U v1.1: 0x69b504 / 0x69c664
    roll rand % 100 < quest + [quest] + 0x18; 0x6a6d2c checks from minute quest +0x80 at chance quest +0x82, a miss
    retries 3 minutes later at +10 %; Felyne Gamechanger, food skill 52, makes it 100 % / 100 %)"""
    sub = struct.unpack_from('<I', q, 0)[0]
    chance, = struct.unpack_from('<I', q, sub + 0x18)
    minute, start = struct.unpack_from('<HH', q, 0x80)
    assert chance <= 100 and start <= 100 and minute < 256, (chance, minute, start)
    return chance, minute, start


def degrees(angle):
    """a 4U 16-bit angle -> degrees in (-180, 180]"""
    d = angle * 360.0 / 65536.0
    return d - 360.0 if d > 180.0 else d


def build_map(name, out, only=None):
    R = RomFS(paths.GU_ROMFS)
    pk = paths.package_toml(name)
    stage = pk['gu_stage']
    em_gu, names4u = gu_ems(R), msg4u('eng')['emName']
    items_gu, items4u_eng = gear4u.gu_item_names(R, []), text_4u('eng')[0]
    gu_item = lambda k: items_gu.get(items4u_eng[k])   # None: no GU item of that name (quest4u.rem_4u drops it)
    gu_files = set(R.files)
    built, sets = [], {}                    # setEmMain name -> content: one content per name (GU's rule)
    for k, t in enumerate(pk.get('tour', [])):
        q4 = quest_4u(t['from_4u'])
        intr = intruders_4u(q4)
        outcomes = [e for e in intr if e[0] > 0]
        assert 1 <= len(outcomes) <= len(INTRUDER_SLOTS), (name, t['quest'], 'GU has 3 intruder slots', intr)
        qid = t['quest']
        tpl_id = t['template']
        tpl = arc_files(R.read('/nativeNX/loc/arc/quest/q%07d.arc' % tpl_id))
        tqd = tpl['loc\\quest\\questData\\questData_%07d' % tpl_id][1]
        assert len(tqd) == quest4u.QD_SIZE and tqd[0x10] == 3 and tqd[0x1F] == 7, (tpl_id, 'not a GU Harvest Tour')
        assert (tpl_id < 10000) == (qid < 10000), (tpl_id, qid, 'template on another board')
        assert tqd[QD_INTRUDE:QD_INTRUDE + 10] == bytes([100, 0, 100, 0, 0, 0, 100, 0, 0, 0]), (
            tpl_id, 'GU tour template intruder fields', tqd[QD_INTRUDE:QD_INTRUDE + 10].hex())
        tlink = tpl['loc\\quest\\questLink\\questLink_%07d' % tpl_id][1]
        tnames = [tlink[8 + 20 * i + 4:8 + 20 * (i + 1)].split(b'\0')[0].decode() for i in range(15)]
        bslot = [i for i in range(5) if struct.unpack_from('<H', tqd, 0x64 + 13 * i)[0]]
        assert bslot == [2] and tnames[2] != 'b_m00em000_00', (tpl_id, 'one intruder in boss slot 2', bslot)
        tset = tpl['quest\\boss\\setEmMain\\' + tnames[2]][1]
        assert len(tset) == 32 and struct.unpack_from('<fII', tset, 0) == (1.0, 1, 0), tpl_id
        # the 4U small monsters, by species name (the template's GU-terrain sets are not used)
        zak, gone = [], set()
        for r in zako_4u(q4):
            nm = names4u[r[0]]
            if nm in em_gu and em_gu[nm] & 0x1000: zak.append((em_gu[nm],) + r[1:])
            else: gone.add(nm)
        esl_name = 'z_m%02dd_%03d' % (stage, 950 + k)
        assert not any(p.endswith('/' + esl_name + '.esl') or esl_name in p for p in gu_files), esl_name
        sub4 = objectives_4u(q4)[1]
        rems = {r: tpl['quest\\rem\\' + r][1] for r in set(tnames[8:13])}
        rem = list(tnames[8:13])
        if sub4[0] == 1:                   # hunt {4U em, count}
            sub_nm = NAME_4U.get(sub4[1], names4u[sub4[1]])
            assert sub_nm in em_gu, (qid, 'subquest target %s' % sub_nm)
            sub = struct.pack('<BHH', 1, em_gu[sub_nm], sub4[2])
            rem[4] = 'rem_%07ds' % qid
            rems[rem[4]] = quest4u.rem_4u(q4, quest4u.SUB_ROW_4U, gu_item)
        else:
            assert sub4 == (0, 0, 0), (qid, 'a 4U subquest kind not handled', sub4)
            sub, sub_nm = bytes(5), None
        t4 = quest4u.text4u(q4)
        if only not in (None, qid): continue
        sid = '%07d' % qid
        qd = bytearray(tqd)
        struct.pack_into('<I', qd, 0x0C, qid)
        qd[0x14] = stage
        qd[0x16] = struct.unpack_from('<I', q4, 0xB4)[0]          # minutes (4U)
        assert qd[0x29:0x2E] == bytes(5), (tpl_id, 'a template with a subquest')
        qd[0x29:0x2E] = sub
        chance, minute, start = intrude_4u(q4)
        qd[QD_INTRUDE:QD_INTRUDE + 10] = bytes([chance, minute, start, 0, 0, 0] +
                                               [e[0] for e in outcomes] + [0] * (3 - len(outcomes)) + [0])
        for i, lang in enumerate(quest4u.QLANGS):
            qd[0xDF + 20 * i:0xDF + 20 * (i + 1)] = ref(quest4u.T_GMD, '%s_%s' % (sid, lang))
        trec = tqd[0x64 + 13 * 2:0x64 + 13 * 3]
        slot_set, res, shown = {}, [], []
        for slot, (w, em4, area, pos, ang) in zip(INTRUDER_SLOTS, outcomes):
            nm = NAME_4U.get(em4, names4u[em4])
            assert nm in em_gu and not em_gu[nm] & 0x1000, (qid, '4U intruder %d %s: no GU large monster' % (em4, nm))
            gid = em_gu[nm]
            rec = bytearray(trec)                                     # the template's rows, this monster
            struct.pack_into('<H', rec, 0, gid)
            qd[0x64 + 13 * slot:0x64 + 13 * (slot + 1)] = rec
            se = bytearray(tset)
            struct.pack_into('<I4f', se, 0x0C, area, degrees(ang), *pos)
            set_name = 'b_m%02dem%03d_%02d' % (stage, gid & 0xff, 90 + k)
            assert not any(set_name in p for p in gu_files), set_name
            assert sets.setdefault(set_name, bytes(se)) == bytes(se), ('setEmMain %s differs between quests' % set_name)
            if set_name not in slot_set.values():
                res.append(('quest\\boss\\setEmMain\\' + set_name, T_SET, bytes(se)))
            slot_set[slot] = set_name
            shown.append('%s (4U em%d) GU %#x weight %d, area %d at %s angle %.1f' % (
                nm, em4, gid, w, area, tuple(round(v) for v in pos), degrees(ang)))
        res.append(('quest\\boss\\setEmMain\\b_m00em000_00', T_SET, tpl['quest\\boss\\setEmMain\\b_m00em000_00'][1]))
        esl = [esl_name if zak else 'z_m00d_000', 'z_m00d_000', 'z_m00d_000']
        if zak: res.append(('quest\\zako\\emSetList\\' + esl_name, T_ESL, esl_gu(zak)))
        res.append(('quest\\zako\\emSetList\\z_m00d_000', T_ESL, tpl['quest\\zako\\emSetList\\z_m00d_000'][1]))
        for r in sorted(set(rem)):
            res.append(('quest\\rem\\' + r, T_REM, rems[r]))
        res.append(('quest\\supp\\supp_' + sid, T_SUPP, tpl['quest\\supp\\supp_%07d' % tpl_id][1]))
        res.append(('quest\\plus\\questPlus_' + tnames[14], T_PLUS, tpl['quest\\plus\\questPlus_' + tnames[14]][1]))
        link = tlink[:8] + b''.join(ref(T_SET, slot_set.get(i, 'b_m00em000_00')) for i in range(5))
        link += b''.join(ref(T_ESL, n) for n in esl)
        link += b''.join(ref(T_REM, r) for r in rem) + ref(T_SUPP, 'supp_' + sid) + ref(T_PLUS, tnames[14])
        assert len(link) == 308
        gmds = quest4u.quest_gmds(tpl, tpl_id, sid, t4)
        quest4u.write(out, quest4u.assemble(res, link, gmds, bytes(qd), sid))
        built.append(qid)
        print('tour %d = 4U q%d (tpl q%d): star %d class %d stage %d, %d min; intruders %d %%, from minute %d at %d %%: '
              '%s; rows %s; subquest %s; %d small monsters%s; "%s"' % (
                  qid, t['from_4u'], tpl_id, qd[0x12], qd[0x13], stage, qd[0x16], chance, minute, start,
                  '; '.join(shown), tuple(trec[5:8]),
                  'hunt %d %s (row %s)' % (sub4[2], sub_nm, rem[4]) if sub_nm else 'none',
                  len(zak), ' (4U species GU lacks, left out: %s)' % sorted(gone) if gone else '', t4['eng'][0]))
        left = [(w, names4u[e]) for w, e, *_ in intr if not w]
        if left: print('tour %d: 4U entries with weight 0 left out (D7): %s' % (t['quest'], left))
    return built


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('map')
    ap.add_argument('--out')
    ap.add_argument('--only', type=int, help='build only this quest ID')
    a = ap.parse_args()
    ids = build_map(a.map, a.out or paths.map_romfs(a.map), a.only)
    print('%d tour quest(s) built: %s' % (len(ids), ids))


if __name__ == '__main__':
    main()
