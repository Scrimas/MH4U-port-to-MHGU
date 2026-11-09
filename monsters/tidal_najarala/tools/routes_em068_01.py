"""routes_em068_01.py : Tidal Najarala's 4U area behaviour on the Frozen Seaway -> her GU area files (manifest fields 40 area_link, 41 area_eat, 42 map_info, 43 area_select).

4U keeps a monster's area behaviour per stage (monsters/monoblos/tools/routes_em007_01.py documents the layout, C): emd word 14 hop distances per area, word 15 stay areas, word 17 stay timers;
EMC `2a CASE stage > 07 CASE area` blocks = next areas; class slot 66 (uEm023 0x76c000) = sleep / eating areas per stage. Her 4U quests are on stage 4, the Frozen Seaway = GU map 14 (Stygian's
quests.md); GU's Najarala has no map 14 (C), so its records are new here: the record shapes come from GU Zamtrios (em067_00, map 14 only, as Stygian's area_files takes another monster's map), the values
from her 4U data where 4U has them. The Arena (GU map 9, her m11016) has one area: GU's Najarala records stay.

What GU's engine reads (C):
  area_link  rows[from][4 + to] = hops (0x69a33c). Which kind by the reason of the move this+0x73f5 (0xb31a0, 0xbdae4): 1 = weakened, to the sleep area (kind 4: 0xb870c), 3 / 4 = hunger (kind 2: 0xb82cc),
             else kind 1. So kind 4 names HER way to HER sleep area: Zamtrios' leads to his area 7, and with it she could never start the move to area 6.
  area_eat   chance of the hunger move by stamina, rows with Status bit 2 (0xb7e90, 0xb8250, one caller). No row for the map = chance 0: she would never go to eat.
  points     stage\\_point_pos\\map14: her move types are 4 / 3 (dive): she surfaces at the next area's flags-0x20 point (0xb3e4c -> 0xb4774, whatever area she left), and travels to the exit point of the
             current area: flags bit 1, `other` = the next area, variant 0, her Group in the mask (0xb3640 -> 0xb38a0). No such point: nothing is written, she travels toward the last exit she knew.
             4U's hop table links areas 2 -> 3, for which GU's stage has no such point, so she does not take that step (gu_links; a DEVIATION, notes/plan.md "Routes"): her 4U share for it goes the way round.
"""
import copy, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, emc, emdata4u, xfs   # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack                      # noqa: E402

EM4U, STAGE_4U, MAP_GU = 'em093', 4, 14
DONOR_INDEX = 57                    # GU Najarala's area_act_tbl entry, which she runs on (allocations.toml donor_index)
SLEEP, EAT = [6], [7]               # 4U uEm023 slot 66 0x76c000 on stage 4: the weakened move 0x93e0ac to area 6, the hunger move 0x942358 to area 7 (C)
N_AREAS = 11
MAP_INFO_HEAD, MAP_INFO_BLOCK = 12, 86
DONOR = ('/nativeNX/arc/enemy/em067_00.arc', 'em067_00')
_L = None


def lens():
    global _L
    if _L is None:
        _L = list(open(paths.GU_MAIN, 'rb').read()[0x1732c8c:0x1732c8c + 167])
    return _L


def tokens(s):
    L, i, out = lens(), 0, []
    while i < len(s):
        op = s[i]
        if op == 0xff:
            out.append((op, '', b'')); i += 1; continue
        if op >= len(L): break
        n = L[op]
        if n < 0x80:
            out.append((op, '', s[i + 1:i + 1 + n])); i += 1 + n; continue
        sub = s[i + 1]
        if sub == 0x00:
            out.append((op, 'IF', s[i + 2:i + 2 + (n & 15)])); i += 2 + (n & 15)
        elif sub == 0x01:
            w = {0x80: 1, 0x90: 2, 0xa0: 3, 0xb0: 4}.get(n & 0xf0, 1)
            out.append((op, 'CASE', s[i + 2:i + 2 + w])); i += 2 + w
        elif sub == 0x02:
            out.append((op, 'ELSE', b'')); i += 2
        elif sub == 0xff:
            out.append((op, 'END', b'')); i += 2
        else: i += 2
    return out


def tree(toks):
    stack, blocks = [[]], []
    for op, kind, args in toks:
        if kind == 'IF':
            b = ['BLOCK', op, args, [('IF', [])]]
            stack[-1].append(b); blocks.append(b); stack.append(b[3][-1][1])
        elif kind in ('CASE', 'ELSE') and blocks:
            stack.pop(); b = blocks[-1]
            b[3].append(('ELSE' if kind == 'ELSE' else 'CASE %d' % int.from_bytes(args, 'little'), []))
            stack.append(b[3][-1][1])
        elif kind == 'END' and blocks:
            blocks.pop(); stack.pop()
        elif kind == '':
            stack[-1].append((op, args))
    return stack[0]


def _stage_blocks(items, stage, path):
    for it in items:
        if it[0] != 'BLOCK': continue
        for lab, sub in it[3]:
            p = path + [(it[1], lab)]
            if it[1] == 0x2a and lab == 'CASE %d' % stage: yield p, sub
            else: yield from _stage_blocks(sub, stage, p)


def _dests(items, w=1.0):
    out = []
    for it in items:
        if it[0] == 'BLOCK':
            cs = [(lab, sub) for lab, sub in it[3] if sub or lab != 'IF']
            if it[1] == 0x4a:
                tot = sum(int(lab.split()[1]) for lab, _ in cs if lab.startswith('CASE')) or 1
                for lab, sub in cs:
                    if lab.startswith('CASE'): out += _dests(sub, w * int(lab.split()[1]) / tot)
            else:
                for lab, sub in cs: out += _dests(sub, w / max(len(cs), 1))
        elif it[0] == 0x03 and len(it[1]) >= 2 and it[1][0] in (1, 2) and it[1][1] < N_AREAS:
            out.append((w, it[1][1]))
    return out


def _by_back(items):
    for it in items:
        if it[0] == 'BLOCK' and it[1] == 0x22:
            res = {}
            for lab, sub in it[3]:
                if lab == 'IF' and not sub: continue
                res.setdefault(None if lab == 'ELSE' else int(lab.split()[1]), []).extend(_dests(sub))
            return res
    return {None: _dests(items)}


def routing(cmd, stage):
    best = None
    for gi, g in enumerate(emc.parse(cmd)[1]):
        for si, s in enumerate(g):
            for path, sub in _stage_blocks(tree(tokens(s)), stage, []):
                areas = {}
                for it in sub:
                    if it[0] == 'BLOCK' and it[1] == 0x07:
                        for lab, items in it[3]:
                            if lab.startswith('CASE'):
                                r = _by_back(items)
                                if any(r.values()): areas[int(lab.split()[1])] = r
                if not areas: continue
                score = (any(o == 0x40 and l == 'ELSE' for o, l in path), not any(o == 0x40 and l != 'ELSE' for o, l in path), len(areas))
                if best is None or score > best[0]:
                    best = (score, 'g%d s%d' % (gi, si), areas)
    return (best[1], best[2]) if best else (None, {})


def _stage_list(d, word):
    p = struct.unpack_from('<I', d, 4 * word)[0]; out = {}
    while p and p + 8 <= len(d) and d[p] != 0xff:
        if d[p + 1:p + 4] != b'\0\0\0': return {}
        out[d[p]] = struct.unpack_from('<I', d, p + 4)[0]; p += 8
    return out


def emd_stage(em, stage):
    d = emdata4u.load_4u(em)['emd']
    out = {'dist': {}, 'stay': [], 'timers': {}}
    o = _stage_list(d, 14).get(stage)
    if o:
        for a in range(N_AREAS):
            r = struct.unpack_from('<I', d, o + 4 * a)[0]
            if r >= len(d): break                  # the table ends with the stage's last area (stage 4: fewer rows than the Dunes')
            if r: out['dist'][a] = list(struct.unpack_from('<%db' % N_AREAS, d, r))
    p = _stage_list(d, 15).get(stage)
    while p and d[p] != 0xff:
        out['stay'].append(d[p]); p += 1
    p = _stage_list(d, 17).get(stage)
    while p and d[p] != 0xff:
        out['timers'][d[p]] = struct.unpack_from('<3H', d, p + 2); p += 8
    return out


def gu_exits(rom, areas):
    """{area: areas GU's stage lets her leave it to}, by the stage's monster points (RPP: 12-B head, 32-B records: +12 u16 flags, +18 u16 variant, +26 u8 other area, +28 u32 group mask); asserts the move
    types and the surfacing point of every area, the docstring's rules"""
    _, res = arcpack.read(rom.read('/nativeNX/loc/arc/resident.arc'))
    aat = [d for p, t, d in res if p == 'enemy\\area_act_tbl\\enemy']
    assert len(aat) == 1 and len(aat[0]) == 12 + 137 * 44, 'area_act_tbl layout changed'
    e = aat[0][12 + 44 * DONOR_INDEX:12 + 44 * (DONOR_INDEX + 1)]
    assert list(e[32:36]) == [4, 3, 4, 3], ('GU Najarala\'s move types changed', list(e[32:36]))
    group = e[36]
    pts = {p: d for p, t, d in arcpack.read(rom.read('/nativeNX/loc/arc/stage/map_com/m%02d.arc' % MAP_GU))[1]}
    out = {}
    for a in areas:
        d = pts['stage\\_point_pos\\map%d\\m%02da%02d' % (MAP_GU, MAP_GU, a)]
        assert d[:4] == b'RPP\0', a
        recs = []
        for k in range(struct.unpack_from('<I', d, 8)[0]):
            o = 12 + 32 * k
            flags, variant = struct.unpack_from('<H', d, o + 12)[0], struct.unpack_from('<H', d, o + 18)[0]
            if struct.unpack_from('<I', d, o + 28)[0] >> group & 1:
                recs.append((flags, variant, d[o + 26]))
        assert any(f & 0x20 for f, _, _ in recs), ('no point to surface at', a)
        out[a] = sorted({x for f, v, x in recs if f & 2 and v == 0})
    return out


def hops(links, a):
    """{area: hops from a} over links"""
    out, fr = {a: 0}, [a]
    while fr:
        nx = []
        for x in fr:
            for y in links.get(x, ()):
                if y not in out:
                    out[y] = out[x] + 1
                    nx.append(y)
        fr = nx
    return out


def plan(cmd, rom):
    """her area plan on the Frozen Seaway: areas, neighbours (hop 1 in her 4U table), links (those GU's stage has an exit for), hops over the links, routing, timers"""
    e = emd_stage(EM4U, STAGE_4U)
    where, route = routing(cmd, STAGE_4U)
    areas = sorted(a for a in e['dist'] if a)
    assert areas, 'no 4U stage-4 data for em093'
    adj = {a: [b for b, v in enumerate(e['dist'][a]) if v == 1 and b != a] for a in areas}
    exits = gu_exits(rom, areas)
    links = {a: [b for b in adj[a] if b in exits[a]] for a in areas}
    assert all(links.values()) and all(set(hops(links, a)) == set(areas) for a in areas), ('her areas are not connected on GU\'s stage', links)
    return dict(areas=areas, adj=adj, links=links, hops={a: hops(links, a) for a in areas}, dist=e['dist'], route=route, timers=e['timers'], where=where, stay=sorted(e['stay']), sleep=SLEEP, eat=EAT)


def _path(adj, a, z):
    prev, fr = {a: None}, [a]
    while fr and z not in prev:
        nx = []
        for x in fr:
            for y in sorted(adj.get(x, ())):
                if y not in prev:
                    prev[y] = x; nx.append(y)
        fr = nx
    if z not in prev: return None
    p = [z]
    while p[-1] != a: p.append(prev[p[-1]])
    return p[::-1]


def mask(areas):
    return sum(1 << a for a in areas)


def _donor(rom, kind, gtype_data):
    _, g = arcpack.read(rom.read(DONOR[0]))
    d = [x for p, t, x in g if p == 'enemy\\%s\\%s' % (kind, DONOR[1])]
    assert len(d) == 1, kind
    return d[0]


def _merge(data, dn, m):
    """GU em068_00's area file with the donor's records of map m (Stygian's area_files)"""
    assert xfs.build(data, xfs.parse(data)) == data, 'XFS round trip'
    root, droot = xfs.parse(data), xfs.parse(dn)
    arr = root['RouteFindDataResource']['mpArray']
    darr = droot['RouteFindDataResource']['mpArray']
    arr = arr if isinstance(arr, list) else [arr]
    darr = darr if isinstance(darr, list) else [darr]
    assert not any(o['mMapNo'] == m for o in arr), ('GU Najarala has map %d now' % m)
    mine = [o for o in darr if o['mMapNo'] == m]
    assert mine and {o['_class'] for x in mine for o in xfs.walk(x)} <= {h for h, _ in xfs.defs(data)[1]}
    at = sum(1 for o in arr if o['mMapNo'] < m)
    root['RouteFindDataResource']['mpArray'] = arr[:at] + mine + arr[at:]
    return root, [o for o in root['RouteFindDataResource']['mpArray'] if o['mMapNo'] == m]


def area_link_file(data, rom, P, notes):
    """map 14's rows, the donor's records with her hops (none -> 255, self 0): kinds 1 and 2 over her links (= her 4U hop table, but for the steps GU's stage has no exit for), kind 4 her way to her sleep
    area as GU's sparser form: each row names only the areas on that way"""
    root, mine = _merge(data, _donor(rom, 'area_link', None), MAP_GU)
    assert sorted(o['mKind'] for o in mine) == [1, 2, 4], [o['mKind'] for o in mine]
    weak = {a: _path(P['links'], a, P['sleep'][0]) for a in P['areas']}
    for o in mine:
        for r, row in enumerate(o['mAreaSelDataArray']['mpArray']):
            way = {x: i for i, x in enumerate(weak[r])} if o['mKind'] == 4 and r in weak else P['hops'].get(r, {r: 0})
            for c in range(1, 13):
                row['A%02d' % c] = way.get(c, 255) if r in P['areas'] else (0 if c == r else 255)
    notes.append('area_link map %d: kinds 1, 2 = her 4U hops over the links %s (4U neighbours %s); kind 4 = her way to area %d: %s' % (MAP_GU, P['links'], P['adj'], P['sleep'][0], weak))
    return xfs.build(data, root)


def area_eat_file(data, rom, P, notes):
    """map 14's record with GU Najarala's own eating row (Status 2, the same on its maps 7 and 13): hunger chance by stamina, as GU gives her species (4U keeps none: its rest group is replaced by this engine)"""
    root, mine = _merge(data, _donor(rom, 'area_eat', None), MAP_GU)
    own = [o['mAreaSelDataArray']['mpArray'] for o in root['RouteFindDataResource']['mpArray'] if o['mMapNo'] != MAP_GU]
    rows = [r for x in own for r in (x if isinstance(x, list) else [x]) if r['Status'] == 2]      # one row: not a list (tools/xfs.py)
    values = lambda r: {k: v for k, v in r.items() if not k.startswith('_')}
    assert len(rows) >= 2 and all(values(r) == values(rows[0]) for r in rows), 'GU Najarala\'s eating rows differ'
    assert len(mine) == 1, len(mine)
    mine[0]['mAreaSelDataArray']['mpArray'] = [copy.deepcopy(rows[0])]
    notes.append('area_eat map %d: GU Najarala\'s eating row' % MAP_GU)
    return xfs.build(data, root)


def area_select_file(data, rom, P, notes):
    """map-14 rows from her 4U routing (Monoblos' rule), over the links GU's stage has: Status 2 per neighbour she came from, Status 4 = first step toward her sleep area, Status 0 = 4U's 'from nowhere' or default"""
    root, mine_list = _merge(data, _donor(rom, 'area_select', None), MAP_GU)
    arr = root['RouteFindDataResource']['mpArray']
    mine = {o['mAreaNo']: o for o in mine_list}
    first = mine_list[0]['mAreaSelDataArray']['mpArray']
    e0 = copy.deepcopy(first[0] if isinstance(first, list) else first)
    tpl = mine_list[0]
    adj, links, route, sleep = P['adj'], P['links'], P['route'], P['sleep']

    def conv(a, dests):
        acc = {}
        for w, z in dests:
            p = _path(links, a, z) if z != a else None
            if p and len(p) > 1: acc[p[1]] = acc.get(p[1], 0) + w
        return acc

    def entry(status, back, acc):
        e = copy.deepcopy(e0)
        ns = sorted(acc, key=lambda x: (-acc[x], x))[:4]
        tot = sum(acc[x] for x in ns) or 1
        share = [int(100 * acc[x] / tot) for x in ns]
        if share: share[0] += 100 - sum(share)
        e.update(Status=status, RouteNo=0, Param=0, BackArea=back)
        for i in range(4):
            e['Next%dArea' % (i + 1)] = ns[i] if i < len(ns) else 255
            e['Next%dRand' % (i + 1)] = share[i] if i < len(ns) else 255
        return e

    log, out = {}, []
    for a in P['areas']:
        r, ns, out_of, rows = route.get(a, {}), adj[a], links[a], []
        for b in ns:
            acc = conv(a, r[b] if b in r else (r.get(None) or [(1.0, x) for x in out_of if x != b] or [(1.0, out_of[0])]))
            rows.append(entry(2, b, acc or {x: 1.0 for x in out_of if x != b} or {out_of[0]: 1.0}))
        p = _path(links, a, sleep[0]) if a != sleep[0] else None
        if p and len(p) > 1:
            rows.append(entry(4, 255, {p[1]: 1.0}))
        acc = conv(a, r.get(255) or r.get(None) or [])
        rows.append(entry(0, 255, acc or {x: 1.0 for x in out_of}))
        o = copy.deepcopy(mine.get(a) or tpl)
        o['mAreaNo'] = a
        o['mAreaSelDataArray']['mpArray'] = rows
        out.append(o)
        log[a] = [(x['Status'], x['BackArea'], [(x['Next%dArea' % i], x['Next%dRand' % i]) for i in range(1, 5) if x['Next%dArea' % i] != 255]) for x in rows]
    keep = [o for o in arr if o['mMapNo'] != MAP_GU]
    at = sum(1 for o in keep if o['mMapNo'] < MAP_GU)
    root['RouteFindDataResource']['mpArray'] = keep[:at] + out + keep[at:]
    notes.append('area_select map %d from her 4U routing (%s), sleep %s: %s' % (MAP_GU, P['where'], sleep, log))
    return xfs.build(data, root)


def map_info_file(data, rom, P, notes):
    """block 14: her areas, eat / sleep (4U uEm023 slot 66), prey 0, stay timers = her 4U frames / 60"""
    n = (len(data) - MAP_INFO_HEAD) // MAP_INFO_BLOCK
    assert len(data) == MAP_INFO_HEAD + n * MAP_INFO_BLOCK and n > MAP_GU, len(data)
    o = MAP_INFO_HEAD + MAP_INFO_BLOCK * MAP_GU
    assert not any(data[o:o + MAP_INFO_BLOCK]), 'GU Najarala has map_info block 14 now'
    trip = {a: tuple(round(x / 60) for x in t) for a, t in P['timers'].items()}
    b = bytearray(MAP_INFO_BLOCK)
    struct.pack_into('<4H', b, 0, mask(P['areas']), mask(P['eat']), mask(P['sleep']), 0)
    for a, t in trip.items():
        struct.pack_into('<3H', b, 8 + 6 * a, *t)
    notes.append('map_info block %d: areas %s, eat %s, sleep %s, stay timers her 4U (s) %s' % (MAP_GU, P['areas'], P['eat'], P['sleep'], trip))
    return data[:o] + bytes(b) + data[o + MAP_INFO_BLOCK:]
