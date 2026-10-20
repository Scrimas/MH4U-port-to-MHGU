#!/usr/bin/env python3
"""tzreport.py : summarize a Ryujinx log of a Tigerstripe Zamtrios test session (the tester only plays and closes).

usage: python3 monsters/tigerstripe_zamtrios/tools/tzreport.py [LOG]   (default: newest log in ~/.config/Ryujinx/Logs)

Reports: crash / errors, the core's lines about the monster (data file, installed, spawn, file IDs), and the
action / motion log of module/em067_01_diag.c: actions seen, the ones GU's class has no handler for (static decode of
uEm067_00's dispatcher 0xf78f98 and its category tables, 2026-10-20), and which variant-1 motions played.
"""
import collections, glob, os, re, sys

LOGS = os.path.expanduser('~/.config/Ryujinx/Logs/*.log')
NOISE = ('TamperMachine', 'FFmpeg', 'AudioRenderer', 'NvdecProcessor')
# uEm067_00 action dispatch (slot 125, 0xf78f98): categories without a class handler go to the base (0xca118);
# for the categories with a jump table, the numbers that have their own case (others = the table's default)
BASE_CATS = {3, 4, 5, 9, 14, 15}
HANDLED = {
    0: {0, 1, 2, 7},
    1: {0, 1, 2, 4, 5, 10, 16, 18, 19, 20, 21, 22, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 49,
        50, 51, 52, 53, 54, 55, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 100, 101, 102, 103},
    6: {0, 1, 2, 3, 4, 5, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23, 24, 32, 34, 36, 37, 38, 39, 40, 41, 42, 43},
    7: {6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 52, 53, 54, 55, 56, 58, 61, 62, 63,
        64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 202, 203},
    13: {8, 9, 10, 11, 12},
}
# motions GU's variant-1 code requests (notes/phase1-variant-map.md section 4): only em092's motion lists have them
VARIANT1_MOTIONS = [0x462, 0x463, 0x464, 0x465, 0x466, 0x467, 0x468, 0x469, 0x46a, 0x46b, 0x46c, 0x46d, 0x46e,
                    0x370, 0x372]


def gu_handles(cat, num):
    if cat in BASE_CATS: return False
    return num in HANDLED[cat] if cat in HANDLED else True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(LOGS), key=os.path.getmtime)
    lines = open(path, errors='replace').read().splitlines()
    print('log:', path)
    crash = [l for l in lines if 'Unhandled exception' in l or 'InvalidAccessHandler' in l]
    print('session end %s | crash: %s' % (lines[-1][:12] if lines else '?', 'YES ' + crash[0][:120] if crash else 'no'))
    errors = collections.Counter(re.sub(r'0x[0-9a-f]+', 'X', l[13:].strip())[:120]
                                 for l in lines if '|E|' in l and not any(n in l for n in NOISE))
    for e, n in errors.most_common(5):
        print('  error x%d: %s' % (n, e))

    core = [(l[:12], l.split('mh4uport: ', 1)[1]) for l in lines if 'mh4uport: ' in l]
    print('\ncore:')
    for ts, m in core:
        if re.search(r'tigerstripe_zamtrios (data|installed|NOT installed|em_create|quest_prep|em_arc|em_record)|'
                     r'quest_prep quest|module_init', m):
            print('  %s %s' % (ts, m))
    files = [m for ts, m in core if m.startswith('tigerstripe_zamtrios file ')]
    miss = [m for m in files if re.search(r'-> 0 lr', m)]
    print('  file IDs served: %d lines, %d returned no resource%s' % (len(files), len(miss),
                                                                    (': ' + '; '.join(miss[:6])) if miss else ''))

    tz = [(l[:12], l.split('tzport: ', 1)[1]) for l in lines if 'tzport: ' in l]
    print('\nem067_01 (%d log lines):' % len(tz))
    for ts, m in tz:
        if 'first dispatch' in m: print('  %s %s' % (ts, m))
    acts = collections.Counter()
    mots = collections.Counter()
    for ts, m in tz:
        a = re.search(r'action (\d+)/(\d+) \(motion ([0-9a-f]+)', m)
        if a:
            acts[int(a.group(1)), int(a.group(2))] += 1; mots[int(a.group(3), 16)] += 1
        b = re.search(r'motion ([0-9a-f]+) \(action', m)
        if b: mots[int(b.group(1), 16)] += 1
    print('  actions: %d starts, %d distinct' % (sum(acts.values()), len(acts)))
    print('  ', ' '.join('%d/%d x%d' % (c, n, k) for (c, n), k in sorted(acts.items())))
    gaps = [(c, n) for c, n in acts if not gu_handles(c, n)]
    print('  reaching no uEm067_00 handler (base / default case): %s' % (
        ' '.join('%d/%d x%d' % (c, n, acts[c, n]) for c, n in sorted(gaps)) or 'none'))
    seen = [m for m in VARIANT1_MOTIONS if m in mots]
    print('  variant-1 motions played: %d of %d (%s); never: %s' % (
        len(seen), len(VARIANT1_MOTIONS), ' '.join('%x' % m for m in seen) or '-',
        ' '.join('%x' % m for m in VARIANT1_MOTIONS if m not in mots) or '-'))
    print('  motions: %d distinct; most frequent: %s' % (len(mots), ', '.join('%x x%d' % kv for kv in mots.most_common(10))))


if __name__ == '__main__':
    main()
