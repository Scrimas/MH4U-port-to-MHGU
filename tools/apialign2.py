"""apialign2.py : 4U->GU framework API map pooled over every monster present in both games.

Pairs (4U class, GU class) by monster name; code blocks: GU = [class min, next class min) (contiguous per class),
4U = [previous class's last override end, this class's last override end) (action code precedes overrides).
Same algorithm as apialign.py (anchor-based function pairing + LCS call alignment, iterated), votes pooled.

  apialign2.py      -> dump/apimap2.pkl {'map': {4U: GU}, 'votes': {4U: (GU, best, total)}}; prints em089 callees
"""
import bisect, collections, os, pickle, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apialign as al  # noqa: E402
import apimap as am  # noqa: E402
import a4u  # noqa: E402

PAIRS = [('uEm001', 'uEm001_00'), ('uEm036', 'uEm003_00'), ('uEm007', 'uEm008_00'), ('uEm009', 'uEm009_00'),
         ('uEm034', 'uEm011_00'), ('uEm016', 'uEm014_00'), ('uEm030', 'uEm018_00'), ('uEm019', 'uEm023_00'),
         ('uEm031', 'uEm024_00'), ('uEm103', 'uEm025_00'), ('uEm032', 'uEm027_00'), ('uEm011', 'uEm032_00'),
         ('uEm033', 'uEm033_00'), ('uEm116', 'uEm038_00'), ('uEm042', 'uEm043_00'), ('uEm048', 'uEm057_00'),
         ('uEm047', 'uEm061_00'), ('uEm044', 'uEm063_00'), ('uEm020', 'uEm065_00'), ('uEm021', 'uEm066_00'),
         ('uEm022', 'uEm067_00'), ('uEm023', 'uEm068_00'), ('uEm026', 'uEm069_00'), ('uEm028', 'uEm071_00'),
         ('uEm025', 'uEm076_00'), ('uEm088', 'uEm077_00'), ('uEm038', 'uEm004_00'), ('uEm099', 'uEm007_00'),
         ('uEm077', 'uEm013_00'), ('uEm017', 'uEm021_00'), ('uEm027', 'uEm070_00'), ('uEm105', 'uEm017_00')]


def blocks_4u():
    N = a4u.by_name()
    P = [a4u.u(0xe6b058 + 4 * k) for k in range(95)]
    ends = {}
    for n, d in N.items():
        if not (n.startswith('uEm') and n[3:].isdigit()): continue
        v = a4u.vtables(d)
        if not v: continue
        E = [a4u.u(v[0] + 4 * k) for k in range(95)]
        ov = [e for e, p in zip(E, P) if e != p and e and 0x6d0000 <= e < 0x920000]
        if ov: ends[n] = max(ov)
    srt = sorted(ends.items(), key=lambda kv: kv[1])
    out = {}
    for i, (n, hi) in enumerate(srt):
        lo = srt[i - 1][1] + 4 if i else 0x6dd000
        st = al.starts4(hi, hi + 0x4000)
        out[n] = (lo, st[1] if len(st) > 1 else hi + 0x400)
    return out


def blocks_gu():
    rng, _ = pickle.load(open(am.DUMP + 'gu_classes.pkl', 'rb'))
    srt = sorted(rng.items(), key=lambda kv: kv[1][0])
    out = {}
    for i, (n, (lo, hi)) in enumerate(srt):
        out[n] = (lo, srt[i + 1][1][0] if i + 1 < len(srt) else hi + 0x400)
    return out


def main():
    b4, bg = blocks_4u(), blocks_gu()
    data = []
    for n4, ng in PAIRS:
        if n4 not in b4 or ng not in bg:
            print('skip', n4, ng); continue
        data.append((n4, ng, al.seqs4(*b4[n4]), al.seqsG(*bg[ng])))
    print(len(data), 'monster pairs')
    M = dict(al.SEED)
    for rnd in range(6):
        votes = collections.Counter(); npairs = 0
        for n4, ng, s4, sg in data:
            for f, g, sc in al.pair_functions(s4, sg, M):
                npairs += 1
                a = al.lcs_align(s4[f], sg[g], M)
                votes.update(al.votes_from(s4[f], sg[g], a, M))
        by4 = collections.defaultdict(collections.Counter)
        for (a, b), n in votes.items(): by4[a][b] += n
        added = 0
        taken = set(M.values())
        for a, c in sorted(by4.items(), key=lambda kv: -max(kv[1].values())):
            (b, n), tot = c.most_common(1)[0], sum(c.values())
            if a not in M and b not in taken and n >= 4 and n / tot >= 0.6:
                M[a] = b; taken.add(b); added += 1
        print('round %d: %d function pairs, +%d, total %d' % (rnd, npairs, added, len(M)))
        if not added: break
    final = {a: (M.get(a, c.most_common(1)[0][0]), c.most_common(1)[0][1], sum(c.values())) for a, c in by4.items()}
    for a, b in M.items(): final.setdefault(a, (b, 99, 99))
    pickle.dump({'map': M, 'votes': final}, open(am.DUMP + 'apimap2.pkl', 'wb'))
    ext = pickle.load(open(am.DUMP + 'em089/ext_callees_v2.pkl', 'rb'))
    for t, cnt in ext.most_common(140):
        if not (0x100000 <= t < 0xdec784): continue
        if t in final:
            b, n, tot = final[t]
            print('%x em089:%-4d -> GU %x  %s %d/%d' % (t, cnt, b, 'MAP ' if t in M else 'cand', n, tot))
        else:
            print('%x em089:%-4d -> ?' % (t, cnt))


if __name__ == '__main__':
    main()
