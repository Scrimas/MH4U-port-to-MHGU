"""apialign.py : extend the 4U->GU API map by aligning the call sequences of paired Rathian functions.

1. Rathian functions (4U em001 / GU em001_00) are paired by their "anchor tokens": (mapped callee, r1 constant)
   for calls to already-mapped helpers (setMotion with motion ids, frame polls, attack enables...).
2. For each pair, the external call sequences are aligned (LCS; equal = mapped pair, or same r1 constant);
   unknown callees aligned together vote for a mapping. Iterate a few rounds.

  apialign.py            prints the map with votes -> dump/apimap.pkl {4U: (GU, votes, total)}
"""
import bisect, collections, os, pickle, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apimap as am  # noqa: E402
import a4u  # noqa: E402

asm = am.asm
SEED = {0x94e350: 0xaff40, 0x9190c4: 0xafda4, 0x91ab1c: 0xb0a24, 0xb06b9c: 0x727d0, 0xb05df4: 0xb0a84,
        0x914dfc: 0x7df94, 0x933144: 0x7dc2c, 0x9167ec: 0xbc8b0}


def starts4(lo, hi):
    s = set()
    for a in range(lo, hi, 4):
        w = a4u.u(a)
        if (w & 0xFFFF4000) == 0xE92D4000 or w == 0xE52DE004: s.add(a)
    return sorted(s)


def startsG(lo, hi):
    s = set()
    for a in range(lo, hi, 4):
        m, o = asm.INS.get(a, ('', ''))
        if m == 'push' and 'lr' in o: s.add(a)
        if m == 'str' and o.startswith('lr, [sp, #-'): s.add(a)
    return sorted(s)


def seqs4(lo, hi):
    st = starts4(lo, hi); out = collections.defaultdict(list)
    for a in range(lo, hi, 4):
        t = am.branch4(a)
        if t is None or lo <= t < hi: continue
        i = bisect.bisect_right(st, a) - 1
        if i < 0: continue
        out[st[i]].append((t, a4u.reg_value(a, 1)))
    return out


def seqsG(lo, hi):
    st = startsG(lo, hi); out = collections.defaultdict(list)
    for a in range(lo, hi, 4):
        t = am.gu_target(a)
        if t is None or lo <= t < hi: continue
        i = bisect.bisect_right(st, a) - 1
        if i < 0: continue
        out[st[i]].append((t, am.gu_const(a, 'r1')))
    return out


def anchors(seq, M, side):
    if side == 4: return collections.Counter((M[t], r) for t, r in seq if t in M and r is not None)
    known = set(M.values())
    return collections.Counter((t, r) for t, r in seq if t in known and r is not None)


def pair_functions(S4, SG, M):
    A4 = {f: anchors(s, M, 4) for f, s in S4.items()}
    AG = {f: anchors(s, M, 'g') for f, s in SG.items()}
    pairs = []
    for f, a in A4.items():
        if sum(a.values()) < 2: continue
        best = None
        for g, b in AG.items():
            inter = sum((a & b).values())
            if inter < 2: continue
            sc = inter / sum((a | b).values())
            if not best or sc > best[0]: best = (sc, g)
        if best and best[0] >= 0.5: pairs.append((f, best[1], best[0]))
    return pairs


def lcs_align(x, y, M):
    n, m = len(x), len(y)
    eq = lambda a, b: (a[0] in M and M[a[0]] == b[0]) or (a[1] is not None and a[1] == b[1] and a[1] > 2)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            D[i][j] = D[i + 1][j + 1] + 1 if eq(x[i], y[j]) else max(D[i + 1][j], D[i][j + 1])
    i = j = 0; out = []
    while i < n and j < m:
        if eq(x[i], y[j]): out.append((i, j)); i += 1; j += 1
        elif D[i + 1][j] >= D[i][j + 1]: i += 1
        else: j += 1
    return out


def votes_from(x, y, al, M):
    """matched anchors plus the unmatched calls sandwiched between consecutive anchors when the gaps
    have the same length (positional match)."""
    v = collections.Counter()
    pts = [(-1, -1)] + al + [(len(x), len(y))]
    for (i0, j0), (i1, j1) in zip(pts, pts[1:]):
        gi, gj = list(range(i0 + 1, i1)), list(range(j0 + 1, j1))
        if gi and len(gi) == len(gj):
            for a, b in zip(gi, gj):
                if x[a][0] not in M: v[(x[a][0], y[b][0])] += 1
    for i, j in al:
        if x[i][0] not in M: v[(x[i][0], y[j][0])] += 2
    return v


def main():
    S4 = am.sig4  # noqa
    s4 = seqs4(*am.R4_EM001); sg = seqsG(*am.RG_EM001)
    M = dict(SEED); votes = collections.Counter()
    for rnd in range(4):
        pairs = pair_functions(s4, sg, M)
        votes = collections.Counter()
        for f, g, sc in pairs:
            al = lcs_align(s4[f], sg[g], M)
            votes.update(votes_from(s4[f], sg[g], al, M))
        by4 = collections.defaultdict(collections.Counter)
        for (a, b), n in votes.items(): by4[a][b] += n
        added = 0
        for a, c in by4.items():
            (b, n), tot = c.most_common(1)[0], sum(c.values())
            if n >= 3 and n / tot >= 0.6 and a not in M and b not in M.values():
                M[a] = b; added += 1
        print('round %d: %d function pairs, +%d mappings, total %d' % (rnd, len(pairs), added, len(M)))
        if not added: break
    final = {}
    for a, c in by4.items():
        (b, n), tot = c.most_common(1)[0], sum(c.values())
        final[a] = (M.get(a, b), n, tot)
    for a, b in M.items(): final.setdefault(a, (b, 99, 99))
    pickle.dump({'map': M, 'votes': final}, open(am.DUMP + 'apimap.pkl', 'wb'))
    ext = pickle.load(open(am.DUMP + 'em089/ext_callees_v2.pkl', 'rb'))
    for t, cnt in ext.most_common(130):
        if t in final:
            b, n, tot = final[t]
            print('%x em089:%-4d -> GU %x  %s votes %d/%d' % (t, cnt, b, 'MAP ' if t in M else 'cand', n, tot))
        else:
            print('%x em089:%-4d -> ?' % (t, cnt))


if __name__ == '__main__':
    main()
