"""fieldmap.py : map MH4U enemy-record offsets (W = [this+0xe28]) to MHGU ones (rec = [this+0x1428]).

Per function, a small register tracker follows `this` (r0 at entry) and the record pointer:
  4U: rec = ldr [this+0xe28] or ldr [this+0x8d88] (em089 keeps a copy there); adds chain offsets.
  GU: rec = ldr [this+0x1428] (often `movw rX,#0x1428; ldr rd,[r0,rX]`), work = [this+0xcac0] = rec+96;
      register-offset accesses `[rn, rX]` with rX = movw constant.
Accesses through rec give (kind, offset), kind = b(yte)/h(alf)/w(ord)/f(loat), s = signed.
Offsets are paired across the mapped function pairs of dump/apimap2.pkl (+ the paired Rathian functions):
score = co-occurrence / occurrences, ties broken by count.

  fieldmap.py uses4 LO HI          record fields used by a 4U range (em089: 8b661c 8ca1f0)
  fieldmap.py map OFF[,OFF..]       GU candidates for 4U record offsets (hex), e.g. 1ca,1cb,144
  fieldmap.py em089                 candidates for every byte/half/word field em089 uses
"""
import bisect, collections, os, pickle, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a4u, dis4u  # noqa: E402
import apimap as am  # noqa: E402
import apialign as al  # noqa: E402

asm = am.asm
KIND = {'ldrb': 'b', 'strb': 'b', 'ldrsb': 'sb', 'ldrh': 'h', 'strh': 'h', 'ldrsh': 'sh', 'ldr': 'w', 'str': 'w',
        'vldr': 'f', 'vstr': 'f', 'ldrd': 'd', 'strd': 'd'}
MEMOP = re.compile(r'^(r\d+|s\d+|d\d+|lr|r12)(?:, (r\d+))?, \[(r\d+|sp)(?:, (#-?0x[0-9a-f]+|#-?\d+|r\d+))?\](!?)$')


def _imm(s): return int(s.lstrip('#'), 0)


REC4, RECG = 0xe30, 0x1440   # the record is embedded: 4U W = this+0xe30, GU rec = this+0x1440 (CONFIRMED, ctors)


def track(ins_at, start, n, rec_this_offs, work_this_off=None, work_delta=0, rec_base=None):
    """returns Counter of (kind, rec_offset); this-relative accesses beyond rec_base count as record fields."""
    R = {'r0': ('T', 0)}
    K = {}  # register -> constant
    out = collections.Counter()
    for k in range(n):
        a = start + 4 * k
        m, o = ins_at(a)
        if m in ('?', ''): break
        base_m = re.sub(r'(eq|ne|lt|gt|le|ge|hi|lo|hs|ls|mi|pl|cc|cs)$', '', m) if m not in KIND else m
        if base_m in ('bl', 'blx'):
            for r in ('r0', 'r1', 'r2', 'r3', 'r12'): R.pop(r, None); K.pop(r, None)
            continue
        if base_m in ('pop',) and 'pc' in o: break
        if base_m == 'bx' and o == 'lr': break
        mm = MEMOP.match(o)
        if base_m in KIND and mm:
            rd, rd2, rn, off, wb = mm.groups()
            if off is None: d = 0
            elif off.startswith('#'): d = _imm(off)
            else: d = K.get(off)
            src = R.get(rn)
            if d is not None and src:
                kind, val = src[0], src[1] + d
                if kind == 'W':
                    out[(KIND[base_m], val)] += 1
                    if base_m.startswith('ldr') and base_m != 'ldrd': R.pop(rd, None); K.pop(rd, None)
                    if wb: R[rn] = ('W', val)
                    continue
                if kind == 'T' and base_m == 'ldr':
                    if val in rec_this_offs: R[rd] = ('W', 0); K.pop(rd, None); continue
                    if work_this_off is not None and val == work_this_off: R[rd] = ('W', work_delta); continue
                if kind == 'T' and rec_base is not None and val >= rec_base and val not in rec_this_offs \
                        and val != work_this_off:
                    out[(KIND[base_m], val - rec_base)] += 1
                    if base_m.startswith('ldr') and base_m != 'ldrd': R.pop(rd, None); K.pop(rd, None)
                    continue
            if base_m.startswith('ldr') or base_m.startswith('vldr'):
                R.pop(rd, None); K.pop(rd, None)
            continue
        ops = [x.strip() for x in o.split(',')]
        if not ops: continue
        rd = ops[0]
        if base_m in ('movw', 'mov') and len(ops) == 2 and ops[1].startswith('#'):
            K[rd] = _imm(ops[1]); R.pop(rd, None); continue
        if base_m == 'mov' and len(ops) == 2 and ops[1] in R:
            R[rd] = R[ops[1]]; continue
        if base_m in ('add', 'sub') and len(ops) == 3 and ops[1] in R and (ops[2].startswith('#') or ops[2] in K):
            v = _imm(ops[2]) if ops[2].startswith('#') else K[ops[2]]
            if base_m == 'sub': v = -v
            R[rd] = (R[ops[1]][0], R[ops[1]][1] + v); K.pop(rd, None); continue
        if re.match(r'r\d+$|lr$|r12$', rd) and base_m not in ('cmp', 'cmn', 'tst', 'teq', 'push', 'vcmp', 'vcmpe') \
                and not base_m.startswith('v') and not base_m.startswith('str'):
            R.pop(rd, None); K.pop(rd, None)
    return out


def ins4(a): return dis4u.INS(a)


def insG(a): return asm.INS.get(a, ('?', ''))


def fields4(f, n=None):
    n = n or 800
    return track(ins4, f, n, (0xe28, 0x8d88), rec_base=REC4)


def fieldsG(f, n=None):
    n = n or 800
    return track(insG, f, n, (0x1428,), work_this_off=0xcac0, work_delta=96, rec_base=RECG)


def fn_len4(f):
    st = al.starts4(f + 4, f + 0x3000)
    return ((st[0] - f) // 4) if st else 400


def fn_lenG(f):
    st = al.startsG(f + 4, f + 0x3000)
    return ((st[0] - f) // 4) if st else 400


def monster_pairs():
    """paired monster functions (4U, GU) of the 31 monsters in both games (apialign2 pairing, final map)."""
    cache = am.DUMP + 'monster_fn_pairs.pkl'
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    import apialign2 as a2
    M = pickle.load(open(am.DUMP + 'apimap2.pkl', 'rb'))['map']
    b4, bg = a2.blocks_4u(), a2.blocks_gu()
    out = []
    for n4, ng in a2.PAIRS:
        if n4 not in b4 or ng not in bg: continue
        s4, sg = al.seqs4(*b4[n4]), al.seqsG(*bg[ng])
        out += [(f, g) for f, g, sc in al.pair_functions(s4, sg, M)]
    pickle.dump(out, open(cache, 'wb'))
    return out


def pairs():
    d = pickle.load(open(am.DUMP + 'apimap2.pkl', 'rb'))
    base = [(a, b) for a, b in d['map'].items() if 0x100000 <= a < 0xdec784 and 0 < b < 0x13f1dec]
    return base + monster_pairs()


def build_cooc():
    P = pairs()
    occ4 = collections.Counter(); co = collections.defaultdict(collections.Counter)
    occG = collections.Counter()
    for a, b in P:
        x = fields4(a, fn_len4(a)); y = fieldsG(b, fn_lenG(b))
        occG.update(set(y))
        for k4 in set(x):
            occ4[k4] += 1
            for kg in set(y):
                if kg[0].lstrip('s') == k4[0].lstrip('s'): co[k4][kg] += 1
    return occ4, (co, occG), len(P)


def candidates(occ4, cog, key, top=3, npairs=1):
    co, occG = cog
    if key not in co: return []
    n = occ4[key]
    # two views: raw ratio P(G | 4U) (right for frequent fields) and lift P(G | 4U) / P(G) (right for rare ones)
    by_ratio = sorted(co[key].items(), key=lambda kv: -kv[1])[:2]
    by_lift = sorted(co[key].items(),
                     key=lambda kv: -((kv[1] / n) / (occG[kv[0]] / npairs)) * min(kv[1], 8) if kv[1] >= 2 else 0)
    res = by_ratio + [kv for kv in by_lift if kv not in by_ratio][:top - 1]
    return [(kg, v, n) for kg, v in res]


def main():
    cmd = sys.argv[1]
    if cmd == 'uses4':
        lo, hi = (int(x, 16) for x in sys.argv[2:4])
        tot = collections.Counter()
        for f in al.starts4(lo, hi): tot.update(fields4(f, fn_len4(f)))
        for (k, o), n in sorted(tot.items(), key=lambda kv: kv[0][1]): print('%-2s %#06x %d' % (k, o, n))
        return
    cache = am.DUMP + 'fieldmap_cooc.pkl'
    if os.path.exists(cache): occ4, co, npairs = pickle.load(open(cache, 'rb'))
    else:
        occ4, co, npairs = build_cooc(); pickle.dump((occ4, co, npairs), open(cache, 'wb'))
    if cmd == 'map':
        for s in sys.argv[2].split(','):
            o = int(s, 16)
            for k in ('b', 'sb', 'h', 'sh', 'w', 'f'):
                c = candidates(occ4, co, (k, o), npairs=npairs)
                if c: print('4U %-2s %#06x (in %d pairs) -> %s' % (k, o, occ4[(k, o)], '  '.join(
                    '%s %#06x %d' % (kg[0], kg[1], v) for kg, v, n in c)))
    elif cmd == 'em089':
        tot = collections.Counter()
        for f in al.starts4(0x8b661c, 0x8ca1f0): tot.update(fields4(f, fn_len4(f)))
        for (k, o), cnt in sorted(tot.items(), key=lambda kv: -kv[1]):
            c = candidates(occ4, co, (k, o), npairs=npairs)
            print('%-2s %#06x em089 uses %-3d base pairs %-3d -> %s' % (k, o, cnt, occ4.get((k, o), 0), '  '.join(
                '%s %#06x %d' % (kg[0], kg[1], v) for kg, v, n in c) or '-'))


if __name__ == '__main__':
    main()
