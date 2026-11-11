"""fxbudget.py : what an effect costs GU when it is posted, built and drawn, measured on GU's own EFLs and on ours.

  fxbudget.py                      corpus distributions (GU romfs, cached), our ms_* EFLs placed in them, offenders
  fxbudget.py --log LOG            + the peak load of a test log's posts (msport: mhf effect / carrier lines)
  fxbudget.py --arc NAME=ARC ...   + extra arcs as their own group (e.g. efl4u2gu's em089_00.arc)
  fxbudget.py --ours ARC           our arc (default: the built w05.arc)
  fxbudget.py --rescan             rebuild the corpus cache (dump/mhf/fxbudget_corpus.pkl, ~1-2 min)

Capacities (GU 1.4 main; notes/gu-efl-units.md "Limits and budgets"; C = traced in code):
- proxies (uMHProofEffect, 0x350 B): at most PROXY_CAP alive, counted by the ctor 0x41f10 / dtor 0x4201c in the
  global at MAIN 0x1850a50; the post 0x40978 asks 0x41558 first: at the cap a post of category 2 / 3 ends one live
  proxy from the manager's buckets and goes on, any other category (ours: extra 0 -> category 0) is refused (handle 0).
- every other piece (effect 0x500 B, generators 0x1d0 B, the work block, slot extras, scene-mode model units 0x500 B
  per particle) is a plain allocation from its class's MtAllocator: allocator index 21 (0x15004c's name map:
  cParticleManager, uBaseEffect, ...; parents walked by 0x7aa588) = the 'Unit' heap, UNIT_HEAP bytes (0x151ccc),
  shared with every unit of the game. No per-class generator pool, no per-frame draw cap (0xaef728 copies the unit's
  0x30-B draw block, 0xbae520 picks the draw context and layer). A null allocation fails the whole effect
  (0x9bdc68 / 0x9be320 / 0x9be664 -> effect +0xf0 0x2000000).
- work block (0x9be320) = slots x 0x130 + the sum of the generators' gen +0x20; gen +0x20 (0xa5b658) = N x (particle
  + extra + MOVE_SZ[move kind]) + round16(N x EMIT_SZ[emit high nibble ^ 8]), N = element +0xc lo16 (0xa58fa8;
  N x 5 / 16 or x 9 / 16 under element +8 bit 2 clear and gen +0x50 >> 28 = 0 / 1: not applied here, an upper
  bound), particle / extra = the class's bind (vtable slot 6) arguments (PSIZE; Model extra = 0x20 x UV layers).
- entries built per post (rec_stats): those whose element +0 shares a bit with the record's mask (0x9be8c4, C; S
  that the mask is the PEL record +0x48); none kept -> no generator, effect +0xf0 0x1000000."""
import collections, glob, os, pickle, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths  # noqa: E402
sys.path.append(paths.GU_PY)
from arc import arc_entries, arc_read  # noqa: E402

T_EFL, T_PEL = 0x6D5AE854, 0x5ac2b4e3   # rEffectList; T_PEL only used through the path (effect\pel\...)
OURS = os.path.join(ROOT, 'weapons', 'magnet_spike', 'romfs', 'nativeNX', 'arc', 'player', 'quest', 'w05.arc')
CACHE = os.path.join(ROOT, 'dump', 'mhf', 'fxbudget_corpus.pkl')
PEL_PATH = 'effect\\pel\\pl\\w05_000'

PROXY_CAP = 144                          # 0x41558: cmp count, #144 (C)
UNIT_HEAP = 0x7800000                    # 0x151ccc: allocator 15 'Unit', 120 MiB; index 21 (effects) -> it (C)
SLOT = 0x130                             # effect emitter slot (0x9be320 / 0x9be664, C)
# particle bytes per generator class (bind = vtable slot 6 -> 0xa5b658(gen, size, extra), C; key = unit type, 'L'
# = the Lite class when move-type bit 4 is set): Billboard 0xa7b114, Model 0xa9499c, Polygon 0xa9c520, ...
PSIZE = {0: 176, '0L': 176, '1L': 208, 1: 208, 2: 256, '2L': 256, 3: 160, 4: 128, 5: 288, 6: 336, 7: 192, 8: 144,
         9: 176, 10: 176, 11: 128, 12: 208, 13: 160, 14: 128, 15: 288, 16: 144, 17: 256, 18: 256, 19: 192, 20: 176,
         21: 224, 22: 112, 23: 304, 24: 112, 26: 208}
MOVE_SZ = (64, 112, 96, 144, 112, 144, 128, 64, 160)      # u16 table MAIN 0x1671700 (0xa5b658, gen +0x42 & 0xf)
EMIT_SZ = (48, 4, 4, 4, 4, 4, 4, 4, 4, 16, 16, 16, 16, 16, 16, 48)   # u32 table 0x1671730 (0xaed0b0)
CLASS = {0: 'Billboard', 1: 'Polyline', 2: 'Polygon', 3: 'Texline', 4: 'Line', 5: 'Model', 6: 'PrimModel',
         7: 'LensFlare', 8: 'MassBillboard', 9: 'Filter', 10: 'Light', 11: 'Hit', 12: 'Polyline', 13: 'Texline',
         14: 'Line', 15: 'PolygonStrip', 16: 'Custom', 17: 'ClothPolygon', 18: 'Adhesion', 19: 'BillboardStrip',
         20: 'SizeBillboard', 21: 'LightShaft', 22: 'Point', 23: 'AxisPolygon', 24: 'Force', 25: 'Node', 26: 'Trail'}
LIFE_KEYS = ('entries', 'gens', 'models', 'maxN', 'sumN', 'uv', 'work')

# GU's own maxima over the 1650 unique EFLs of the romfs (fxbudget.py --rescan, 2026-11-11); effcheck.py fails a
# build whose MHF EFL is above one of them on an axis whose cost is traced (BUDGET_AXES)
GU_MAX = {'entries': 122, 'maxN': 1000, 'sumN': 3010, 'work': 340928, 'models': 112, 'uv': 2}
BUDGET_AXES = ('entries', 'sumN', 'work')


def r16(x):
    return (x + 15) & ~15


def efl_stats(b):
    """one EFL -> dict (entries, n2, gens by class, Model units, UV layers, N per entry, work-block bytes, life)"""
    n, n2 = struct.unpack_from('<HH', b, 0x10)
    cls = collections.Counter()
    work, sumN, maxN, models, uv, life = 0, 0, 0, 0, 0, 0
    el0, per = [], []
    for i in range(n):
        w = struct.unpack_from('<4I', b, 0x30 + 16 * i)
        t, lite = w[1] & 0xff, bool(w[3] & 0x10)
        cls[CLASS.get(t, t) if not (lite and t in (0, 1, 2)) else 'Lite' + CLASS[t]] += 1
        e = (w[0] >> 8) + 0x30
        N = struct.unpack_from('<H', b, e + 0xc)[0] if w[0] >> 8 else 0
        el0.append(struct.unpack_from('<I', b, e)[0] if w[0] >> 8 else 0)
        psz = PSIZE.get(('%dL' % t) if lite and t in (0, 1, 2) else t, 0)
        extra = 0
        if t == 5 and w[1] >> 8:
            u = (w[1] >> 8) + 0x30
            models += 1
            if struct.unpack_from('<H', b, u + 0x134)[0]:
                k = (struct.unpack_from('<I', b, u + 0x138)[0] >> 24) & 0xf
                extra = 32 + 32 * k
                uv = max(uv, 1 + k)
        kind = w[3] & 0xf
        size = (r16(extra) + r16(psz)) * N + (MOVE_SZ[kind] if kind < 9 else 0) * N + r16(EMIT_SZ[((w[2] >> 4) & 0xf) ^ 8] * N)
        work += size
        per.append((el0[-1], int(t == 5), size))
        sumN += N; maxN = max(maxN, N)
        if w[2] >> 8:                              # emit block: three (u16 frames, u16 range) = particle life (0xaed0d0)
            m = (w[2] >> 8) + 0x30
            fr = struct.unpack_from('<6H', b, m)
            life = max(life, sum(fr[0::2]) + sum(fr[1::2]))
    work += SLOT * min(n2, n) if n else 0
    return {'entries': n, 'n2': n2, 'gens': n, 'cls': dict(cls), 'models': models, 'maxN': maxN, 'sumN': sumN,
            'uv': uv, 'work': work, 'life': life, 'per': per}


def rec_stats(s, mask):
    """one PEL record's effect: the entries the effect keeps (0x9be8c4, C: element +0 & effect +0x1c8 and element +4
    & effect +0x1cc, set by 0x32aa44 -> 0x9bd5a0 from the proxy's record copy; S that +0x1c8 = the PEL record's
    +0x48 mask: GU's 865 weapon-arc records each keep 1..n entries by element +0 bits) -> (gens, Model gens, work)"""
    k = [x for x in s['per'] if x[0] & mask]
    return len(k), sum(x[1] for x in k), (sum(x[2] for x in k) + SLOT * min(s['n2'], len(k))) if k else 0


def arc_efls(d, want=None):
    out = {}
    for e in arc_entries(d):
        if e[1] != T_EFL or (want and not want(e[0])): continue
        b = arc_read(d, e)
        if b[:4] == b'EFL\0': out[e[0]] = efl_stats(b)
    return out


def scan_corpus():
    """-> {'all': {path: stats}, 'weapon': {path: stats}, 'psl': [(arc, slot, ids, gens, work)]}"""
    root = os.path.join(paths.GU_ROMFS, 'nativeNX', 'arc')
    allp, weap, psl = {}, {}, []
    for a in sorted(glob.glob(os.path.join(root, '**', '*.arc'), recursive=True)):
        try:
            d = open(a, 'rb').read(); ents = arc_entries(d)
        except Exception:
            continue
        isw = re.search(r'player[\\/]quest[\\/]w\d\d\.arc$', a)
        local = {}
        for e in ents:
            if e[1] != T_EFL or (e[0] in allp and not isw): continue
            try:
                b = arc_read(d, e)
            except Exception:
                continue
            if b[:4] != b'EFL\0': continue
            s = allp.get(e[0]) or efl_stats(b)
            allp[e[0]] = s; local[e[0]] = s
            if isw: weap[e[0]] = s
        if isw:
            pel = next((arc_read(d, e) for e in ents if e[0].startswith('effect\\pel\\pl\\w') and e[0].endswith('_000')), None)
            pss = next((arc_read(d, e) for e in ents if re.match(r'effect\\psl\\player\\mot\\w\d\d\\w\d\d$', e[0])), None)
            try:
                recs = pel_records(pel) if pel else None
            except (IndexError, struct.error):
                recs = None                     # w10 / w14 / wbc: records of another length (not read)
            if recs and pss:
                for slot, ids in psl_posts(pss):
                    st = [local.get(recs.get(i, ('',))[0]) for i in ids]
                    st = [s for s in st if s]
                    psl.append((os.path.basename(a), slot, len(ids), sum(s['gens'] for s in st), sum(s['work'] for s in st)))
    return {'all': allp, 'weapon': weap, 'psl': psl}


def pel_records(d, lists=(1,)):
    """PEL v15 -> {id: (EFL path, joint, element mask +0x48[, +0x4c with lists given])} of the given lists (record
    layout: msfx.pel_add; the masks reach effect +0x1c8 / +0x1cc, notes/gu-efl-units.md "Record mask")"""
    out, i = {}, 8
    for li in range(3):
        n = struct.unpack_from('<I', d, i)[0]; i += 4
        for _ in range(n):
            L = d[i]; path = d[i + 1:i + 1 + L].decode('ascii', 'replace'); st = i + 1 + L + 2
            rid, joint = struct.unpack_from('<HH', d, st + 0x30)
            m0, m1 = struct.unpack_from('<II', d, st + 0x48)
            if li in lists: out[rid] = (path, joint, m0) if lists == (1,) else (path, joint, m0, m1)
            i = st + 160
    return out


def psl_posts(d):
    """PSL v2 -> [(slot, [PEL list-1 ids posted by the slot's motion])] (layout: msfx.psl_add)"""
    n = struct.unpack_from('<H', d, 6)[0]
    out = []
    for s in range(n):
        o = struct.unpack_from('<I', d, 8 + 4 * s)[0]
        if not o or o + 16 > len(d): continue
        da = struct.unpack_from('<I', d, o + 8)[0]
        if not da or da + 4 + 64 > len(d): continue
        mask = struct.unpack_from('<I', d, da)[0]
        ids = struct.unpack_from('<32H', d, da + 4)
        out.append((s, [ids[k] for k in range(32) if mask >> k & 1]))
    return out


def corpus(rescan=False):
    if not rescan and os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    c = scan_corpus()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(c, open(CACHE, 'wb'))
    return c


def dist(vals):
    v = sorted(vals)
    if not v: return 'n 0'
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    return 'n %d  p50 %s  p90 %s  p99 %s  max %s' % (len(v), q(.5), q(.9), q(.99), v[-1])


def ours(arc=OURS):
    d = open(arc, 'rb').read()
    efl = arc_efls(d, lambda p: '\\ms_' in p)
    pel = next((arc_read(d, e) for e in arc_entries(d) if e[0] == PEL_PATH), None)
    return efl, (pel_records(pel) if pel else {})


def budget_problems(efls, gu_max=None):
    """our EFL stats -> lines for every EFL above GU's own maximum on a traced axis (effcheck rule)"""
    gm = gu_max or GU_MAX
    out = []
    for p, s in sorted(efls.items()):
        for k in BUDGET_AXES:
            if gm.get(k) and s[k] > gm[k]:
                out.append('%s: %s %d > GU maximum %d (fxbudget.py)' % (p, k, s[k], gm[k]))
    return out


LOG_POST = re.compile(r'^(\d+):(\d+):(\d+)\.(\d+) .*msport: mhf effect (\d+) x(\d+) at motion \d+ f\d+ \(action (\d+)')
LOG_CARR = re.compile(r'^(\d+):(\d+):(\d+)\.(\d+) .*msport: mhf carrier (\d+) \((\d+) rows(?:, PEL (\d+))?')


def peak(log, efls, recs):
    """posts of a test log -> per action run: proxies, generators by class, particle-buffer bytes alive at the peak
    (an effect counted for its EFL's longest particle life + 10 frames; carriers re-posted by the module: their rows)"""
    ev = []
    for l in open(log, errors='replace'):
        m = LOG_POST.match(l)
        if m:
            h, mi, s, ms, pid, n, act = map(int, m.groups())
            ev.append(((h * 60 + mi) * 60 + s + ms / 1000.0, act, [pid + k for k in range(n)]))
            continue
    alive = []
    best = collections.defaultdict(lambda: (0, None))
    for t, act, ids in ev:
        for pid in ids:
            path, _, mask = recs.get(pid, ('', 0, 0))
            s = efls.get(path)
            if not s: continue
            g, m, w = rec_stats(s, mask)
            alive.append((t + (s['life'] + 10) / 60.0, act, pid, g, m, w))
        alive = [x for x in alive if x[0] > t]
        cur = (len(alive), sum(x[3] for x in alive), sum(x[4] for x in alive), sum(x[5] for x in alive),
               sum(1 for x in alive if not x[3]))
        if cur[3] > best[act][0]:
            best[act] = (cur[3], (t, cur, sorted({x[2] for x in alive})))
    return best


def main():
    a = sys.argv[1:]
    rescan = '--rescan' in a
    log = a[a.index('--log') + 1] if '--log' in a else None
    arc = a[a.index('--ours') + 1] if '--ours' in a else OURS
    extra = [x.split('=', 1) for i, x in enumerate(a) if i and a[i - 1] == '--arc']
    c = corpus(rescan)
    groups = [('GU all', c['all']), ('GU weapon arcs', c['weapon'])]
    for name, p in extra:
        groups.append((name, arc_efls(open(p, 'rb').read())))
    mine, recs = ours(arc)
    groups.append(('ours', mine))
    print('capacities (C): proxies alive <= %d (0x41558; ours refused at the cap), Unit heap %d MiB shared '
          '(0x151ccc, allocator 21), no per-class pools / draw caps' % (PROXY_CAP, UNIT_HEAP >> 20))
    for k in LIFE_KEYS:
        print('\n%s per EFL' % k)
        for name, g in groups:
            print('  %-16s %s' % (name, dist([s[k] for s in g.values()])))
    cls = collections.Counter()
    for s in c['all'].values():
        for k, v in s['cls'].items(): cls[k] = max(cls[k], v)
    print('\nGU max generators per class in one EFL:', ', '.join('%s %d' % kv for kv in cls.most_common()))
    gm = {k: max(s[k] for s in c['all'].values()) for k in GU_MAX}
    print('GU maxima:', gm)
    print('\nours above GU\'s maximum (any axis):')
    for p, s in sorted(mine.items()):
        over = ['%s %d (GU max %d, x%.1f)' % (k, s[k], gm[k], s[k] / gm[k]) for k in gm if gm[k] and s[k] > gm[k]]
        if over: print('  %s: %s' % (p, '; '.join(over)))
    top = sorted(mine.items(), key=lambda kv: -kv[1]['work'])[:12]
    allw = sorted(s['work'] for s in c['all'].values())
    print('\nours, largest work blocks (bytes; rank among GU\'s %d EFLs):' % len(allw))
    import bisect
    for p, s in top:
        print('  %-34s entries %2d models %2d maxN %3d sumN %4d work %7d  above %.1f %% of GU' % (
            p, s['entries'], s['models'], s['maxN'], s['sumN'], s['work'], 100.0 * bisect.bisect(allw, s['work']) / len(allw)))
    kept = collections.Counter()
    for pid, (p, j, m) in recs.items():
        if p in mine:
            g = rec_stats(mine[p], m)[0]
            kept['none' if not g else 'all' if g == mine[p]['entries'] else 'part'] += 1
    print('\nour PEL records by the entries their mask keeps (GU weapon arcs: 714 part, 151 all, 0 none): %s'
          % ', '.join('%s %d' % kv for kv in sorted(kept.items())))
    ps = sorted(c['psl'], key=lambda x: -x[4])[:5]
    print('\nGU weapon motions posting the most (arc, slot, records, generators, work bytes):')
    for x in ps: print('  %s slot %d: %d records, %d generators, %d B' % x)
    if log:
        print('\npeak per action (log %s): proxies (of them building nothing), generators, Model generators, work '
              'bytes alive' % os.path.basename(log))
        for act, (w, (t, cur, ids)) in sorted(peak(log, mine, recs).items(), key=lambda kv: -kv[1][0])[:12]:
            print('  action %3d: %3d proxies (%d empty), %4d gens, %3d Model, %7d B  (PEL %s)' % ((act, cur[0], cur[4]) + cur[1:4] + (
                ' '.join(map(str, ids[:12])) + (' ...' if len(ids) > 12 else ''),)))


if __name__ == '__main__':
    main()
