"""hsum4u.py : summarise a MH4U action handler for porting: calls with constant r1-r3 and float s0/s1
arguments (resolved from `vldr sN, [pc]` / `vmov.f32 sN, #imm`), step-byte tests, vtable calls.

  hsum4u.py ADDR [ADDR ...]
Names come from the 4U side of notes/api-map.md.
"""
import re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a4u, dis4u

NAMES = {0x94e350: 'setMotion', 0x9190c4: 'setMotionEx', 0x94f440: 'setMotionLoop', 0x91ab1c: 'motionCheck',
         0xb05df4: 'isMotionEnd', 0x9167ec: 'setTargetMode', 0x914dfc: 'attack', 0x933144: 'attackEx',
         0x9162f8: 'setAttackId', 0x91b3f4: 'stopMove', 0x916260: 'resetMove', 0xb0709c: 'timerDown',
         0x94ef9c: 'setActionW', 0x935ac8: 'setActionW2', 0x90efac: 'setAction', 0x91150c: 'rotateToward',
         0x910c6c: 'setMotionTurn', 0x568c8c: 'atan2', 0x90f994: 'curMotion', 0x8b8e28: 'em089_frameEvent',
         0x93093c: 'targetPos', 0xc0819c: 'spawnNetObj', 0x90f934: 'attackFlag', 0x911cb4: 'speedFactor'}


def flt(a):
    return struct.unpack('<f', struct.pack('<I', a4u.u(a)))[0]


def summarize(f, maxn=700):
    lines = dis4u.lines(f, maxn)
    S = {}; R = {}
    out = []
    for i, l in enumerate(lines):
        m = re.match(r'\s+([0-9a-f]+):\s+(\S+)\s*(.*)$', l)
        if not m: continue
        a, mn, op = int(m.group(1), 16), m.group(2), m.group(3).split(' @')[0].strip()
        if i > 0 and mn == 'push' and 'lr' in op: break
        mm = re.match(r'(s\d+), \[pc, #(-?0x[0-9a-f]+|-?\d+)\]', op)
        if mn.startswith('vldr') and mm: S[mm.group(1)] = '%g' % flt((a + 8 + int(mm.group(2), 0)) & ~3)
        mm = re.match(r'(s\d+), #(\S+)$', op)
        if mn.startswith('vmov') and mm: S[mm.group(1)] = mm.group(2)
        mm = re.match(r'(s\d+), (s\d+)$', op)
        if mn.startswith('vmov') and mm and mm.group(2) in S: S[mm.group(1)] = S[mm.group(2)]
        mm = re.match(r'(r\d), #(-?0x[0-9a-f]+|-?\d+)$', op)
        if mn in ('mov', 'movw') and mm: R[mm.group(1)] = int(mm.group(2), 0)
        mm = re.match(r'(r\d), (r\d)$', op)
        if mn == 'mov' and mm: R[mm.group(1)] = R.get(mm.group(2))
        if re.search(r'#0x144\]', op) or re.search(r'#0x1c9\]', op):
            out.append('%x  %s %s' % (a, mn, op))
        if mn in ('bl', 'b') or (mn == 'blx'):
            t = re.match(r'(0x[0-9a-f]+)', op)
            t = int(t.group(1), 16) if t else None
            if mn == 'b' and t and f <= t < f + 4 * maxn: continue
            nm = NAMES.get(t, '%x' % t if t else op)
            args = ' '.join('%s=%s' % (r, R.get(r)) for r in ('r1', 'r2', 'r3') if R.get(r) is not None)
            fl = ' '.join('%s=%s' % (s, S.get(s)) for s in ('s0', 's1') if s in S)
            out.append('%x  %s %s(%s | %s)' % (a, mn, nm, args, fl))
            for r in ('r0', 'r1', 'r2', 'r3', 'r12'): R.pop(r, None)
        mm = re.match(r'(r\d), \[r0, #(0x1[56][0-9a-f])\]', op)
        if mn == 'ldr' and mm: out.append('%x  vcall vt+%s' % (a, mm.group(2)))
    return out


if __name__ == '__main__':
    for x in sys.argv[1:]:
        f = int(x, 16)
        print('===== %x' % f)
        print('\n'.join(summarize(f)))
