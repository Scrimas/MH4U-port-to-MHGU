"""routes_seltas.py : Desert Seltas' and Desert Seltas Queen's 4U area behaviour on GU's maps -> their GU area files (manifest fields 40 area_link,
41 area_eat, 42 map_info, 43 area_select). Shrouded Nerscylla's routes_em070_01.py generalised to several maps per entry (the readings of the formats
are in its docstring and in Tidal Najarala's routes_em068_01.py; C unless marked).

4U keeps a monster's area behaviour per stage: emd word 14 hop distances per area, word 15 stay areas, word 17 stay timers; EMC `2a CASE stage > 07 CASE
area` blocks = next areas; class slot 66 = the sleep and eating areas per stage (C, 2026-11-09): uEm025 0x788c64 (Seltas and Desert Seltas): stage 1 sleep
9 for em 94 (7 for em 25), stages 17 / 18 sleep 3; eating stage 1 area 8, stages 17 / 18 area 10. uEm026 0x79953c (both queens, no species test):
stages 17 / 18 sleep 5, eat 4. 4U stage 18 (the night Dunes) holds the same emd data as stage 17 (asserted).
Maps (C): 4U stage 17 / 18 = GU map 5, the Dunes; 4U stage 1 = GU map 11, the Ancestral Steppe. GU's Seltas has map 11 records (area_link kinds 3 and 4:
the kind is a bit mask, 0x69e1e4 `tst`, and the class loads masks 1 / 2 / 4 into this+0x7618 / 0x761c / 0x7620 at 0x70abc, so kind 3 serves the plain
and the hunger moves), no map 5; GU's Seltas Queen has neither. A map GU's species lacks gets GU Diablos' map-5 record shapes (em007_00, Monoblos' and
Shrouded Nerscylla's donor), every value from the 4U data. Moves: GU's area_act_tbl entries 61 (Seltas, move types 1 1 1 1) and 58 (Seltas Queen,
3 4 3 4), both group 0: every 4U hop between two areas of theirs has an exit point of group 0 on GU's map (asserted, gu_exits).

What GU's engine reads (Nerscylla's docstring): area_link rows[from][4 + to] = hops; kind 4 = the way to the sleep area (reason 1, weakened); area_eat
= the hunger chance by stamina (no row for a map = never eats there); area_select = the next areas by where the monster came from; map_info block
per map = areas, eating / sleeping area masks, stay timers.
"""
import copy, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, emc, emdata4u, xfs   # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack                      # noqa: E402

N_AREAS = 11
MAP_INFO_HEAD, MAP_INFO_BLOCK = 12, 86
DONOR = ('/nativeNX/arc/enemy/em007_00.arc', 'em007_00')
# entry -> (4U em, GU area_act_tbl index, [(4U stage, GU map, sleep areas, eating areas)])
PLANS = {
    'desert_seltas': ('em094', 61, [(17, 5, [3], [10]), (1, 11, [9], [8])]),
    'desert_seltas_queen': ('em095', 58, [(17, 5, [5], [4])]),
}
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


def routing(scripts, stage):
    """the 4U next-area rules of a stage from the AI table's scripts (reduced to the monster's em): {area: {back area / None: [(weight, area)]}}"""
    best = None
    for gi, g in enumerate(scripts):
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
            if r >= len(d): break                  # the table ends with the stage's last area
            if r: out['dist'][a] = list(struct.unpack_from('<%db' % N_AREAS, d, r))
    p = _stage_list(d, 15).get(stage)
    while p and d[p] != 0xff:
        out['stay'].append(d[p]); p += 1
    p = _stage_list(d, 17).get(stage)
    while p and d[p] != 0xff:
        out['timers'][d[p]] = struct.unpack_from('<3H', d, p + 2); p += 8
    return out


def gu_exits(rom, index, gmap, areas):
    """{area: areas GU's stage lets the monster leave it to}, by the stage's monster points of its group (RPP: 12-B head, 32-B records: +12 u16 flags,
    +18 u16 variant, +26 u8 other area, +28 u32 group mask); index = its GU area_act_tbl entry"""
    _, res = arcpack.read(rom.read('/nativeNX/loc/arc/resident.arc'))
    aat = [d for p, t, d in res if p == 'enemy\\area_act_tbl\\enemy']
    assert len(aat) == 1 and len(aat[0]) == 12 + 137 * 44, 'area_act_tbl layout changed'
    group = aat[0][12 + 44 * index + 36]
    pts = {p: d for p, t, d in arcpack.read(rom.read('/nativeNX/loc/arc/stage/map_com/m%02d.arc' % gmap))[1]}
    out = {}
    for a in areas:
        d = pts['stage\\_point_pos\\map%02d\\m%02da%02d' % (gmap, gmap, a)]
        assert d[:4] == b'RPP\0', a
        recs = []
        for k in range(struct.unpack_from('<I', d, 8)[0]):
            o = 12 + 32 * k
            flags, variant = struct.unpack_from('<H', d, o + 12)[0], struct.unpack_from('<H', d, o + 18)[0]
            if struct.unpack_from('<I', d, o + 28)[0] >> group & 1:
                recs.append((flags, variant, d[o + 26]))
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


def plans(name, scripts, rom, notes=None):
    """[map plan] of an entry: areas, neighbours (hop 1 in its 4U table), links (= those, each with a GU exit, asserted), hops over the links,
    routing, timers, sleep, eat, the GU map. GU's map 5 is the day Dunes: stage 17's data (C: Desert Seltas' stage 18 data has one link more, 3 - 7, which
    GU's map 5 also has an exit for; his own Dunes quests m01030 / m10815 are on stage 17, only the Queen's m10924 is on 18: stage 17 for both, noted)"""
    em, index, maps = PLANS[name]
    out = []
    for stage, gmap, sleep, eat in maps:
        e = emd_stage(em, stage)
        if stage == 17:
            e18 = emd_stage(em, 18)
            if e18 != e and e18['dist'] and notes is not None:
                notes.append('routes: 4U stage 18 (night Dunes) differs from 17 for %s (hop-1 links 17 %s, 18 %s); stage 17 taken' % (
                    em, sorted((a, b) for a in e['dist'] for b, v in enumerate(e['dist'][a]) if v == 1 and a < b),
                    sorted((a, b) for a in e18['dist'] for b, v in enumerate(e18['dist'][a]) if v == 1 and a < b)))
        where, route = routing(scripts, stage)
        if not route and stage == 17:
            where, route = routing(scripts, 18)
        areas = sorted(a for a in e['dist'] if a)
        assert areas, ('no 4U stage data', em, stage)
        assert set(sleep) | set(eat) <= set(areas), ('sleep / eat area not one of its areas', em, stage)
        adj = {a: [b for b, v in enumerate(e['dist'][a]) if v == 1 and b != a] for a in areas}
        exits = gu_exits(rom, index, gmap, areas)
        links = {a: [b for b in adj[a] if b in exits[a]] for a in areas}
        assert links == adj, ('a 4U hop GU\'s stage has no exit for', em, gmap, links, adj)
        assert all(links.values()) and all(set(hops(links, a)) == set(areas) for a in areas), ('its areas are not connected on GU\'s stage', links)
        out.append(dict(stage=stage, map=gmap, areas=areas, adj=adj, links=links, hops={a: hops(links, a) for a in areas}, dist=e['dist'], route=route,
                        timers=e['timers'], where=where, stay=sorted(e['stay']), sleep=sleep, eat=eat))
    return out


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


def _donor(rom, kind):
    _, g = arcpack.read(rom.read(DONOR[0]))
    d = [x for p, t, x in g if p == 'enemy\\%s\\%s' % (kind, DONOR[1])]
    assert len(d) == 1, kind
    return d[0]


def _arr(root):
    arr = root['RouteFindDataResource']['mpArray']
    return arr if isinstance(arr, list) else [arr]


def _with_map(data, rom, kind, m):
    """the parsed GU file and its records of map m: its own, else GU Diablos' map-m records merged in (Stygian's area_files)"""
    assert xfs.build(data, xfs.parse(data)) == data, 'XFS round trip'
    root = xfs.parse(data)
    arr = _arr(root)
    if any(o['mMapNo'] == m for o in arr):
        return root, [o for o in arr if o['mMapNo'] == m], 'its own'
    dn = _donor(rom, kind)
    darr = _arr(xfs.parse(dn))
    mine = [o for o in darr if o['mMapNo'] == m]
    assert mine and {o['_class'] for x in mine for o in xfs.walk(x)} <= {h for h, _ in xfs.defs(data)[1]}
    at = sum(1 for o in arr if o['mMapNo'] < m)
    root['RouteFindDataResource']['mpArray'] = arr[:at] + mine + arr[at:]
    return root, mine, 'GU Diablos\' shapes'


def area_link_file(data, rom, P, notes):
    """per map: hops (none -> 255, self 0) over its links in the records without the weak bit (kind 1 / 2 / 3), kind 4 = its way to its sleep area as GU's
    sparser form (each row names only the areas on that way)"""
    for p in P:
        root, mine, src = _with_map(data, rom, 'area_link', p['map'])
        assert any(o['mKind'] & 4 for o in mine) and any(o['mKind'] & 3 for o in mine), [o['mKind'] for o in mine]
        weak = {a: _path(p['links'], a, p['sleep'][0]) for a in p['areas']}
        for o in mine:
            for r, row in enumerate(o['mAreaSelDataArray']['mpArray']):
                way = {x: i for i, x in enumerate(weak[r])} if o['mKind'] & 4 and r in weak else p['hops'].get(r, {r: 0})
                for c in range(1, 13):
                    row['A%02d' % c] = way.get(c, 255) if r in p['areas'] else (0 if c == r else 255)
        data = xfs.build(data, root)
        notes.append('area_link map %d (%s, kinds %s): its 4U hops over the links %s; the weak way to area %d: %s' % (
            p['map'], src, sorted(o['mKind'] for o in mine), p['links'], p['sleep'][0], weak))
    return data


def area_eat_file(data, rom, P, notes):
    """per map: the species' own eating row (Status 2: hunger chance by stamina, as GU gives its species; 4U keeps none, its rest group is replaced
    by this engine) in the map's record; a map GU's species has keeps its record"""
    for p in P:
        root = xfs.parse(data)
        own = [o['mAreaSelDataArray']['mpArray'] for o in _arr(root) if o['mMapNo'] != p['map']]
        rows = [r for x in own for r in (x if isinstance(x, list) else [x]) if r['Status'] == 2]      # one row: not a list (tools/xfs.py)
        assert rows, 'GU\'s species has no eating row'
        root, mine, src = _with_map(data, rom, 'area_eat', p['map'])
        assert len(mine) == 1, len(mine)
        if src == 'its own':
            notes.append('area_eat map %d: GU\'s record of the species kept' % p['map'])
            continue
        mine[0]['mAreaSelDataArray']['mpArray'] = [copy.deepcopy(rows[0])]
        data = xfs.build(data, root)
        notes.append('area_eat map %d: GU\'s species\' eating row (of %d) in GU Diablos\' record shape' % (p['map'], len(rows)))
    return data


def area_select_file(data, rom, P, notes):
    """per map: rows from its 4U routing (Monoblos' rule), over the links GU's stage has: Status 2 per neighbour it came from, Status 4 = the first step
    toward its sleep area, Status 0 = 4U's 'from nowhere' or default; the map's records replaced"""
    for p in P:
        root, mine_list, src = _with_map(data, rom, 'area_select', p['map'])
        arr = _arr(root)
        mine = {o['mAreaNo']: o for o in mine_list}
        first = mine_list[0]['mAreaSelDataArray']['mpArray']
        e0 = copy.deepcopy(first[0] if isinstance(first, list) else first)
        tpl = mine_list[0]
        adj, links, route, sleep = p['adj'], p['links'], p['route'], p['sleep']

        def conv(a, dests):
            acc = {}
            for w, z in dests:
                q = _path(links, a, z) if z != a else None
                if q and len(q) > 1: acc[q[1]] = acc.get(q[1], 0) + w
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
        for a in p['areas']:
            r, ns, out_of, rows = route.get(a, {}), adj[a], links[a], []
            for b in ns:
                acc = conv(a, r[b] if b in r else (r.get(None) or [(1.0, x) for x in out_of if x != b] or [(1.0, out_of[0])]))
                rows.append(entry(2, b, acc or {x: 1.0 for x in out_of if x != b} or {out_of[0]: 1.0}))
            q = _path(links, a, sleep[0]) if a != sleep[0] else None
            if q and len(q) > 1:
                rows.append(entry(4, 255, {q[1]: 1.0}))
            acc = conv(a, r.get(255) or r.get(None) or [])
            rows.append(entry(0, 255, acc or {x: 1.0 for x in out_of}))
            o = copy.deepcopy(mine.get(a) or tpl)
            o['mAreaNo'] = a
            o['mAreaSelDataArray']['mpArray'] = rows
            out.append(o)
            log[a] = [(x['Status'], x['BackArea'], [(x['Next%dArea' % i], x['Next%dRand' % i]) for i in range(1, 5) if x['Next%dArea' % i] != 255]) for x in rows]
        keep = [o for o in arr if o['mMapNo'] != p['map']]
        at = sum(1 for o in keep if o['mMapNo'] < p['map'])
        root['RouteFindDataResource']['mpArray'] = keep[:at] + out + keep[at:]
        data = xfs.build(data, root)
        notes.append('area_select map %d (%s) from its 4U routing (%s), sleep %s: %s' % (p['map'], src, p['where'], sleep, log))
    return data


def map_info_file(data, rom, P, notes):
    """per map: its block = its areas, eat / sleep (4U class slot 66), prey 0, stay timers = its 4U frames / 60"""
    n = (len(data) - MAP_INFO_HEAD) // MAP_INFO_BLOCK
    assert len(data) == MAP_INFO_HEAD + n * MAP_INFO_BLOCK, len(data)
    for p in P:
        assert n > p['map'], (n, p['map'])
        o = MAP_INFO_HEAD + MAP_INFO_BLOCK * p['map']
        was = struct.unpack_from('<4H', data, o)
        trip = {a: tuple(round(x / 60) for x in t) for a, t in p['timers'].items()}
        b = bytearray(MAP_INFO_BLOCK)
        struct.pack_into('<4H', b, 0, mask(p['areas']), mask(p['eat']), mask(p['sleep']), 0)
        for a, t in trip.items():
            struct.pack_into('<3H', b, 8 + 6 * a, *t)
        data = data[:o] + bytes(b) + data[o + MAP_INFO_BLOCK:]
        notes.append('map_info block %d (GU\'s species: %s): areas %s, eat %s, sleep %s, stay timers its 4U (s) %s' % (
            p['map'], 'none' if not any(was) else 'masks %04x %04x %04x' % was[:3], p['areas'], p['eat'], p['sleep'], trip))
    return data
