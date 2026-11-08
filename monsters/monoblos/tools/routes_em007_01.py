"""routes_em007_01.py : Monoblos' 4U area behaviour on the Dunes -> his GU area files (manifest fields 40 area_link,
42 map_info, 43 area_select; the user, 2026-11-05: "where he spawns and where he walks must come from MH4U").

4U keeps a monster's area behaviour per stage (C; the layout the Sunken Hollow work traced, its tools/routes4u.py,
re-implemented here read-only for this one monster):
  emd word 14  {u8 stage, pad, u32 offset} list -> per area a row of 11 s8 hop distances (-1 = never), word 15 = the
               areas it stays in, word 17 = per area {u8 area, pad, u16 x3} stay timers in frames.
  EMC          `2a CASE stage > 07 CASE area` blocks: `03 01 Z` = walk toward Z, by the area it came from (`22`, 0xff =
               none) and weighted (`4a`, the case value = %); the normal mode is the `40 ELSE` branch.
  class code   sleep / eating area: vtable slot 66 (uEm101 0x8e0bd4 = uEm099 0x8d65e0's code): stages 17 / 18 -> the
               weakened move 0x93e0ac to area 5, the hunger move 0x942358 to area 7 (C).
4U em101 on stage 17 (the Dunes by day, his quests m00801 / m01018; m00818's night Dunes 18 -> GU's Dunes too) =
4U em099 Diablos' data byte for byte (C, 2026-11-05). GU em007_00's map-5 records differ (C): its hop table links
1 <-> 2 (4U never walks it), its next-area shares and stay timers are GU's own. GU area semantics (C, the Sunken Hollow
work's section 17): area_select Status 0 = next areas (came from nowhere), 2 = arrived from BackArea, 4 = weakened;
area_link = hop tables per travel kind; map_info = 86-B block per map: u16 areas / eat / sleep / prey bit masks, then
per AREA NUMBER a u16 triple (block +8 + 6 * area) of stay timers in seconds (GU's maps hold 4U's frames / 60, S).
"""
import copy, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, emc, emdata4u, xfs   # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack                      # noqa: E402

EM4U, STAGE_4U, MAP_GU = 'em101', 17, 5
SLEEP, EAT = [5], [7]               # 4U uEm101 slot 66 for stages 17 / 18 (C)
N_AREAS = 11
MAP_INFO_HEAD, MAP_INFO_BLOCK = 12, 86
_L = None


def lens():
    global _L
    if _L is None:
        _L = list(open(paths.GU_MAIN, 'rb').read()[0x1732c8c:0x1732c8c + 167])
    return _L


def tokens(s):
    """(op, kind, args): kind '' (plain), 'IF', 'CASE', 'ELSE', 'END' (GU's instruction lengths = 4U's for these ops)"""
    L, i, out = lens(), 0, []
    while i < len(s):
        op = s[i]
        if op == 0xff: out.append((op, '', b'')); i += 1; continue
        if op >= len(L): break
        n = L[op]
        if n < 0x80:
            out.append((op, '', s[i + 1:i + 1 + n])); i += 1 + n; continue
        sub = s[i + 1]
        if sub == 0x00: out.append((op, 'IF', s[i + 2:i + 2 + (n & 15)])); i += 2 + (n & 15)
        elif sub == 0x01:
            w = {0x80: 1, 0x90: 2, 0xa0: 3, 0xb0: 4}.get(n & 0xf0, 1)
            out.append((op, 'CASE', s[i + 2:i + 2 + w])); i += 2 + w
        elif sub == 0x02: out.append((op, 'ELSE', b'')); i += 2
        elif sub == 0xff: out.append((op, 'END', b'')); i += 2
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
    """(where, {area: {back area (0xff = none, None = any other): [(weight, destination)]}}) of the stage's routing
    script: the one with the most areas, the normal mode (`40 ELSE`) first"""
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
                score = (any(o == 0x40 and l == 'ELSE' for o, l in path),
                         not any(o == 0x40 and l != 'ELSE' for o, l in path), len(areas))
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
    """{'dist': {area: [s8 per target]}, 'stay': [areas], 'timers': {area: (f1, f2, f3) frames}}"""
    d = emdata4u.load_4u(em)['emd']
    out = {'dist': {}, 'stay': [], 'timers': {}}
    o = _stage_list(d, 14).get(stage)
    if o:
        for a in range(N_AREAS):
            r = struct.unpack_from('<I', d, o + 4 * a)[0]
            if r: out['dist'][a] = list(struct.unpack_from('<%db' % N_AREAS, d, r))
    p = _stage_list(d, 15).get(stage)
    while p and d[p] != 0xff: out['stay'].append(d[p]); p += 1
    p = _stage_list(d, 17).get(stage)
    while p and d[p] != 0xff:
        out['timers'][d[p]] = struct.unpack_from('<3H', d, p + 2); p += 8
    return out


def plan(cmd):
    """his area plan on the Dunes: areas, neighbours (hop 1), 4U hop table, routing, timers"""
    e = emd_stage(EM4U, STAGE_4U)
    where, route = routing(cmd, STAGE_4U)
    areas = sorted(a for a in e['dist'] if a)
    adj = {a: [b for b, v in enumerate(e['dist'][a]) if v == 1 and b != a] for a in areas}
    assert sorted(e['stay']) == areas and set(e['timers']) == set(areas), 'his 4U stay areas / timers / hop table differ'
    return dict(areas=areas, adj=adj, dist=e['dist'], route=route, timers=e['timers'], where=where)


def _path(adj, a, z):
    """shortest walk a -> z over his neighbours (BFS, smallest area first)"""
    prev, fr = {a: None}, [a]
    while fr and z not in prev:
        nx = []
        for x in fr:
            for y in sorted(adj.get(x, ())):
                if y not in prev: prev[y] = x; nx.append(y)
        fr = nx
    if z not in prev: return None
    p = [z]
    while p[-1] != a: p.append(prev[p[-1]])
    return p[::-1]


def mask(areas):
    return sum(1 << a for a in areas)


def area_link_file(data, P, notes):
    """map-5 rows of his three travel kinds from his 4U hops: kind 1 (normal) and kind 2 (hunger, to eat area 7) = his 4U hop
    table (-1 -> 255, self 0), kind 4 (weakened, reason 1 0xb870c) = his way to sleep area 5 in GU's sparser form: each row
    names only the areas on that way (index along it).
    0.4.8 (the user's long hunt of 10784, log 2026-11-08 13-52-00, and "Ja, umstellen"): kinds 2 / 4 were GU Diablos' rows
    until 0.4.7, so at 6 % he went 7 -> 3 -> 5, while his 4U hops are 7: 2 / 10, 3: 1 / 4, 5: 4 (C); now 7 -> 10 -> 4 -> 5."""
    root = xfs.parse(data)
    arr = root['RouteFindDataResource']['mpArray']
    arr = arr if isinstance(arr, list) else [arr]
    mine = [o for o in arr if o['mMapNo'] == MAP_GU]
    assert sorted(o['mKind'] for o in mine) == [1, 2, 4], [o['mKind'] for o in mine]
    weak = {a: _path(P['adj'], a, SLEEP[0]) for a in P['areas']}
    assert all(weak.values()), ('an area of his has no way to his sleep area', weak)
    for o in mine:
        rows = o['mAreaSelDataArray']['mpArray']
        for r, row in enumerate(rows):
            for c in range(1, 13):
                if o['mKind'] == 4 and r in weak:
                    way = {x: i for i, x in enumerate(weak[r])}
                    row['A%02d' % c] = way.get(c, 255)
                else:
                    v = P['dist'][r][c] if r in P['dist'] and c < N_AREAS else (0 if c == r else -1)
                    row['A%02d' % c] = 255 if v < 0 else v
    notes.append('area_link map %d: kinds 1, 2 = his 4U hop table (neighbours %s); kind 4 = his way to area %d: %s'
                 % (MAP_GU, P['adj'], SLEEP[0], weak))
    return xfs.build(data, root)


def area_select_file(data, P, notes):
    """map-5 rows from his 4U routing, GU's three kinds (the Sunken Hollow work's select_rows rule): Status 2 per
    neighbour it came from (4U's case for that area, else its default), Status 4 = the first step toward his sleep area
    (4U's weakened move walks there), Status 0 = 4U's 'from nowhere' (0xff) case or its default; a 4U destination =
    the first area of the walk to it; weights = 4U's `4a` shares, at most 4 next areas"""
    root = xfs.parse(data)
    arr = root['RouteFindDataResource']['mpArray']
    arr = arr if isinstance(arr, list) else [arr]
    mine = {o['mAreaNo']: o for o in arr if o['mMapNo'] == MAP_GU}
    assert sorted(mine) == P['areas'], ('GU map-5 select areas', sorted(mine))
    first = mine[P['areas'][0]]['mAreaSelDataArray']['mpArray']
    e0 = copy.deepcopy(first[0] if isinstance(first, list) else first)
    adj, route = P['adj'], P['route']

    def conv(a, dests):
        acc = {}
        for w, z in dests:
            p = _path(adj, a, z) if z != a else None
            if p and len(p) > 1: acc[p[1]] = acc.get(p[1], 0) + w
        return acc

    def entry(status, back, acc):
        e = copy.deepcopy(e0)
        ns = sorted(acc, key=lambda x: (-acc[x], x))[:4]
        tot = sum(acc[x] for x in ns)
        share = [int(100 * acc[x] / tot) for x in ns]
        share[0] += 100 - sum(share)
        e.update(Status=status, RouteNo=0, Param=0, BackArea=back)
        for i in range(4):
            e['Next%dArea' % (i + 1)] = ns[i] if i < len(ns) else 255
            e['Next%dRand' % (i + 1)] = share[i] if i < len(ns) else 255
        return e

    log = {}
    for a in P['areas']:
        r, ns, rows = route.get(a, {}), adj[a], []
        for b in ns:
            acc = conv(a, r[b] if b in r else (r.get(None) or [(1.0, x) for x in ns if x != b] or [(1.0, b)]))
            rows.append(entry(2, b, acc or {x: 1.0 for x in ns if x != b} or {b: 1.0}))
        p = _path(adj, a, SLEEP[0])
        if p and len(p) > 1:
            rows.append(entry(4, 255, {p[1]: 1.0}))
        acc = conv(a, r.get(255) or r.get(None) or [])
        rows.append(entry(0, 255, acc or {x: 1.0 for x in ns}))
        mine[a]['mAreaSelDataArray']['mpArray'] = rows
        log[a] = [(x['Status'], x['BackArea'], [(x['Next%dArea' % i], x['Next%dRand' % i]) for i in range(1, 5)
                                                 if x['Next%dArea' % i] != 255]) for x in rows]
    notes.append('area_select map %d from his 4U routing (%s): %s' % (MAP_GU, P['where'], log))
    return xfs.build(data, root)


def map_info_file(data, P, notes):
    """block 5: his areas, eat 7, sleep 5, prey 0 (GU's Diablos has none), triples = his 4U stay timers / 60"""
    n = (len(data) - MAP_INFO_HEAD) // MAP_INFO_BLOCK
    assert len(data) == MAP_INFO_HEAD + n * MAP_INFO_BLOCK and n > MAP_GU, len(data)
    o = MAP_INFO_HEAD + MAP_INFO_BLOCK * MAP_GU
    gu = data[o:o + MAP_INFO_BLOCK]
    assert struct.unpack_from('<4H', gu, 0) == (mask(P['areas']), mask(EAT), mask(SLEEP), 0), \
        ('GU Diablos map-5 masks differ from his 4U areas / eat / sleep', struct.unpack_from('<4H', gu, 0))
    trip = {a: tuple(round(x / 60) for x in t) for a, t in P['timers'].items()}
    b = bytearray(MAP_INFO_BLOCK)
    struct.pack_into('<4H', b, 0, mask(P['areas']), mask(EAT), mask(SLEEP), 0)
    for a, t in trip.items():
        struct.pack_into('<3H', b, 8 + 6 * a, *t)
    gu_trip = {a: struct.unpack_from('<3H', gu, 8 + 6 * a) for a in P['areas']}
    notes.append('map_info block %d: areas %s, eat %s, sleep %s (= GU Diablos\'), stay timers his 4U (s) %s (GU '
                 'Diablos %s)' % (MAP_GU, P['areas'], EAT, SLEEP, trip, gu_trip))
    return data[:o] + bytes(b) + data[o + MAP_INFO_BLOCK:]
