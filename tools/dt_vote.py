"""dt_vote.py : majority vote, over every monster present in both games, of which 4U header pointer each GU
dtbase / dtbparts / dttune heap block is copied from (exact byte matches only), and which 4U header offset each
GU object scalar equals. Run with the MHGU_Editor scratch venv.

  dt_vote.py KIND [--json OUT]
"""
import collections, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dt_map, gu_schema
from romfs import RomFS


def vote(kind):
    rom = RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
    U = dt_map.load_4u()
    blocks = collections.defaultdict(collections.Counter)
    sizes = collections.defaultdict(list)
    scal = collections.defaultdict(collections.Counter)
    seen = 0
    for em4, gu in dt_map.shared_pairs():
        try:
            data = dt_map.gu_file(rom, gu, kind)
        except (IndexError, KeyError):
            continue
        s = gu_schema.schema(data, kind)
        if s['read'] != s['size'] or (em4, 'emd') not in U:
            continue
        seen += 1
        files = {k: (U[(em4, k)], dt_map.ptr_words(U[(em4, k)])) for k in ('emd', 'etd')}
        scalars, blk = dt_map.object_parts(s)
        for i, n, own, b in blk:
            if not own or own[0][0] != 'obj' or n < 4:
                continue
            for fk, (u, ptrs) in files.items():
                for w, p in ptrs.items():
                    if u[p:p + n] == b:
                        blocks[own[1]][(fk, w)] += 1
                        nxt = min([q for q in ptrs.values() if q > p] + [len(u)])
                        sizes[(own[1], fk, w)].append((n, nxt - p))
        for off, b in scalars:
            for k in range(0, len(b) - 3, 4):
                v = b[k:k + 4]
                for fk, (u, _) in files.items():
                    for h in range(0, 4 * dt_map.HDR_WORDS, 4):
                        if u[h:h + 4] == v:
                            scal[off + k][(fk, h)] += 1
    return seen, blocks, sizes, scal


if __name__ == '__main__':
    kind = sys.argv[1]
    seen, blocks, sizes, scal = vote(kind)
    out = {'monsters': seen, 'blocks': {}, 'scalars': {}}
    print(kind, 'monsters used:', seen)
    for off in sorted(blocks):
        (fk, w), n = blocks[off].most_common(1)[0]
        sz = collections.Counter(sizes[(off, fk, w)])
        print('  block obj+%#x <- %s word %d (%d/%d exact)  (GU size, 4U gap): %s' % (off, fk, w, n, seen, dict(sz)))
        out['blocks']['%#x' % off] = dict(file=fk, word=w, support=n, sizes=[list(k) for k in sz])
    for off in sorted(scal):
        (fk, h), n = scal[off].most_common(1)[0]
        if n >= max(3, seen // 2):
            print('  scalar obj+%#x == %s +%#x (%d/%d)' % (off, fk, h, n, seen))
            out['scalars']['%#x' % off] = dict(file=fk, off=h, support=n)
    if '--json' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
