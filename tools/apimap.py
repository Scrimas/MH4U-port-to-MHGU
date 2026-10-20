"""apimap.py : map MH4U enemy-framework functions to MHGU ones through Rathian (em001 in both games).

Signal: a framework helper is called from Rathian's code with constant arguments (motion ids, attack indexes,
modes...). The same Rathian action calls the matching MHGU helper with the same constants. For every external
callee of a code range we collect the multiset of (r1, r2) constants at its call sites, then score 4U->GU pairs.

  apimap.py sig4 LO HI          callee signatures of a 4U range
  apimap.py match [N]           best GU match for the N most-called em089 callees (default 60)
Ranges: 4U em001 0x6dd000-0x6efee8, GU em001_00 0xcefe00-0xd0cb00, 4U em089 0x8b661c-0x8ca1f0.
"""
import collections, os, pickle, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
sys.path.insert(0, paths.GU_PY)
import a4u  # noqa: E402
import asm  # noqa: E402  (MHGU main.asm index)

R4_EM001 = (0x6dd000, 0x6efee8)
RG_EM001 = (0xcefe00, 0xd0cb00)
R4_EM089 = (0x8b661c, 0x8ca1f0)
DUMP = os.path.dirname(os.path.abspath(__file__)) + '/../dump/'


def branch4(a):
    w = a4u.u(a)
    if (w >> 28) == 0xF or (w & 0x0E000000) != 0x0A000000: return None
    off = w & 0xFFFFFF
    if off & 0x800000: off -= 0x1000000
    return a + 8 + 4 * off


def sig4(lo, hi):
    out = collections.defaultdict(list)
    for a in range(lo, hi, 4):
        t = branch4(a)
        if t is None or lo <= t < hi: continue
        out[t].append((a4u.reg_value(a, 1), a4u.reg_value(a, 2)))
    return out


def gu_const(a, reg, back=12):
    for k in range(1, back):
        m, o = asm.INS.get(a - 4 * k, ('', ''))
        if not o.startswith(reg + ','): continue
        mm = re.match(r'r\d+, #(-?0x[0-9a-f]+|-?\d+)$', o)
        if m in ('mov', 'movw') and mm: return int(mm.group(1), 0) & 0xFFFFFFFF
        if m == 'mvn' and mm: return (~int(mm.group(1), 0)) & 0xFFFFFFFF
        if m in ('cmp', 'cmn', 'tst', 'str', 'strb', 'strh'): continue
        return None
    return None


def gu_target(a):
    m, o = asm.INS.get(a, ('', ''))
    if m not in ('bl', 'b', 'blx') and not re.match(r'b(eq|ne|lt|gt|le|ge|hi|lo|hs|ls|mi|pl)$', m): return None
    mm = re.match(r'(0x[0-9a-f]+)', o)
    return int(mm.group(1), 16) if mm else None


def sigG(lo, hi):
    out = collections.defaultdict(list)
    for a in range(lo, hi, 4):
        t = gu_target(a)
        if t is None or lo <= t < hi: continue
        out[t].append((gu_const(a, 'r1'), gu_const(a, 'r2')))
    return out


def score(x, y):
    """x, y: lists of (r1, r2). Jaccard on constant r1 values (weighted) + call-count ratio."""
    cx = collections.Counter(v for v, _ in x if v is not None)
    cy = collections.Counter(v for v, _ in y if v is not None)
    inter = sum((cx & cy).values()); union = sum((cx | cy).values())
    jac = inter / union if union else 0.0
    cnt = min(len(x), len(y)) / max(len(x), len(y))
    return 0.7 * jac + 0.3 * cnt, inter


def main():
    cmd = sys.argv[1]
    if cmd == 'sig4':
        lo, hi = (int(x, 16) for x in sys.argv[2:4])
        for t, v in sorted(sig4(lo, hi).items(), key=lambda kv: -len(kv[1])):
            print('%x %d %s' % (t, len(v), collections.Counter(r for r, _ in v).most_common(8)))
        return
    if cmd == 'match':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        s4 = sig4(*R4_EM001); sg = sigG(*RG_EM001)
        ext = pickle.load(open(DUMP + 'em089/ext_callees_v2.pkl', 'rb'))
        res = {}
        for t, cnt in ext.most_common(n):
            x = s4.get(t)
            if not x:
                print('%x em089:%-4d  (not called by 4U em001)' % (t, cnt)); continue
            best = sorted(((score(x, y), g) for g, y in sg.items()), key=lambda r: -r[0][0])[:3]
            res[t] = best
            print('%x em089:%-4d em001:%-4d -> %s' % (t, cnt, len(x), '  '.join(
                'GU %x (%.2f, %d common, n=%d)' % (g, s[0], s[1], len(sg[g])) for s, g in best)))
        pickle.dump(res, open(DUMP + 'apimap_em001.pkl', 'wb'))


if __name__ == '__main__':
    main()
