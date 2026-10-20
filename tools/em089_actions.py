"""em089_actions.py : MH4U uEm089 action table (category, number) -> handler, plus motions each handler sets.

Dispatch: vt44 (0x8c3ac0) switches on work byte +0x1ca (category) and sub-dispatchers on +0x1cb (number);
resolved with disp4u.run(). Motions = constant r1 passed to the setMotion helpers inside the handler.
"""
import bisect, collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a4u, disp4u

LO, HI = 0x8b6600, 0x8cc724
VT = 0xe6a2b4
SET_MOTION = {0x94e350: 'setMotion', 0x9190c4: 'setMotionEx', 0x910c6c: 'setMotionTurn?',
              0x94ef9c: 'motion94ef9c', 0x94f440: 'motion94f440', 0x9200a4: 'motion9200a4'}
MOTIONS = set(map(int, open(os.path.join(os.path.dirname(__file__), '../dump/em089/motions.txt')).read().split()))


def is_push(a):
    w = a4u.u(a); return (w & 0xFFFF4000) == 0xE92D4000 or w == 0xE52DE004


vt = {a4u.u(VT + 4 * k): k for k in range(95)}
STARTS = sorted(set(a for a in range(LO, HI, 4) if is_push(a)) | set(v for v in vt if LO <= v < HI))


def extent(f):
    i = bisect.bisect_right(STARTS, f)
    return f, (STARTS[i] if i < len(STARTS) else HI)


def branch_target(a):
    w = a4u.u(a)
    if (w >> 28) == 0xF or (w & 0x0E000000) != 0x0A000000: return None
    off = w & 0xFFFFFF
    if off & 0x800000: off -= 0x1000000
    return a + 8 + 4 * off


def motions_in(f, seen=None, depth=2):
    """constant motion ids set by f (and by em089-local callees, depth-limited)."""
    seen = seen if seen is not None else set()
    if f in seen: return []
    seen.add(f)
    s, e = extent(f)
    out = []
    for a in range(s, e, 4):
        t = branch_target(a)
        if t is None: continue
        if t in SET_MOTION:
            v = a4u.reg_value(a, 1)
            out.append((SET_MOTION[t], v))
        elif LO <= t < HI and depth > 0 and t in STARTS and t != f:
            out += motions_in(t, seen, depth - 1)
    return out


def action_table():
    top = {}
    for cat in range(14):
        for num in range(256):
            r = disp4u.run(0x8c3ac0, {0x1ca: cat, 0x1cb: num, 0x144: 1})
            if r and isinstance(r[0], int):
                top[(cat, num)] = r
    # categories whose handler is itself a dispatcher on 1cb: resolve one level deeper
    out = {}
    for (cat, num), (t, r1) in top.items():
        if t in (0x8b6f2c, 0x8bac40, 0x8bd4b0, 0x8c2640, 0x8c2784, 0x8c0f94):
            r = disp4u.run(t, {0x1ca: cat, 0x1cb: num, 0x144: 1})
            if r and isinstance(r[0], int): out[(cat, num)] = (t, r[0], r[1])
            else: out[(cat, num)] = (t, None, None)
        else:
            out[(cat, num)] = (None, t, r1)
    return out


if __name__ == '__main__':
    tab = action_table()
    print('cat num  dispatcher handler  r1   motions')
    for (cat, num), (disp, h, r1) in sorted(tab.items()):
        if h is None: continue
        if not (LO <= h < HI):
            print('%3d %3d  %s  -> base %x' % (cat, num, '%x' % disp if disp else '-', h)); continue
        mot = motions_in(h)
        ms = sorted(set(v for k, v in mot if v is not None))
        flag = '' if all(m in MOTIONS for m in ms) else ' (!non-LMT)'
        r1s = r1 if r1 is not None and r1 < 1000 else '-'
        print('%3d %3d  %-8s %x  %-4s %s%s' % (cat, num, '%x' % disp if disp else '-', h, r1s,
                                              ' '.join(str(m) for m in ms), flag))
