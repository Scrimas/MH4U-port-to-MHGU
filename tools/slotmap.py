"""slotmap.py : match MH4U uEnemy vtable slots to MHGU uFestaEnemy slots.

Features per function (both binaries are 32-bit ARM, same code lineage): instruction count, call count,
small immediates, float literals, struct offsets. Rathian is em001 in both games, so uEm001 (4U) vs
uEm001_00 (GU) implementations of the same virtual should look alike; base implementations too.

  slotmap.py base        4U uEnemy base slots next to their best GU uFestaEnemy base match
  slotmap.py em001       4U uEm001 overrides vs GU uEm001_00 overrides (best matches)
"""
import bisect, re, struct, sys

sys.path.insert(0, '/home/scrimas/Projects/MH4U_MHGU_port/tools')
import a4u, gu_enemy as g  # noqa: E402

GA = g.asm
LINE = re.compile(r'^ +([0-9a-f]+):\s+\t?(\S+)\s*(.*)$')


def load_4u():
    ins = {}
    for l in open('/home/scrimas/Projects/MH4U_MHGU_port/dump/mh4u.asm', errors='replace'):
        m = LINE.match(l)
        if m: ins[int(m.group(1), 16)] = (m.group(2), m.group(3).split(' @')[0].strip())
    return ins


I4 = None


def func_end(INS, f, maxn=3000):
    """end = last `pop {..pc}` / `bx lr` / `ldr pc` before the next push{..lr} that is not reached by a local branch."""
    last = f; branch_max = f
    for k in range(maxn):
        a = f + 4 * k
        m, o = INS.get(a, ('', ''))
        if k and m == 'push' and 'lr' in o and a > branch_max: break
        mm = re.match(r'(0x[0-9a-f]+)', o)
        if m.startswith('b') and m not in ('bl', 'blx', 'bic', 'bics', 'bfi', 'bfc') and mm:
            t = int(mm.group(1), 16)
            if f <= t < f + 4 * maxn: branch_max = max(branch_max, t)
        if (m.startswith('pop') and 'pc' in o) or (m.startswith('bx') and o == 'lr') or o.startswith('pc,'):
            last = a
            if a >= branch_max: return a + 4
        if m == 'b' and mm and not (f <= int(mm.group(1), 16) < a + 0x400) and a >= branch_max:
            return a + 4   # tail call
    return last + 4


def features(INS, f, u32):
    end = func_end(INS, f)
    n = (end - f) // 4
    calls = imms = 0
    ims, offs, flts = set(), set(), set()
    for a in range(f, end, 4):
        m, o = INS.get(a, ('', ''))
        if m in ('bl', 'blx'): calls += 1
        for x in re.findall(r'#(-?0x[0-9a-f]+|-?\d+)', o):
            v = int(x, 0)
            if m.startswith(('cmp', 'mov', 'movw')) and -1000 < v < 5000: ims.add(v)
            if m.startswith(('ldr', 'str', 'add', 'movw')) and 0x40 <= v < 0x10000: offs.add(v)
        mm = re.match(r's\d+, \[pc, #(-?0x[0-9a-f]+|-?\d+)\]', o)
        if m == 'vldr' and mm:
            try:
                w = u32((a + 8 + int(mm.group(1), 0)) & ~3)
                flts.add(round(struct.unpack('<f', struct.pack('<I', w))[0], 4))
            except Exception: pass
    return dict(n=n, calls=calls, ims=ims, offs=offs, flts=flts)


def sim(x, y):
    def j(a, b): return len(a & b) / len(a | b) if a | b else 1.0
    size = min(x['n'], y['n']) / max(x['n'], y['n'], 1)
    callr = min(x['calls'], y['calls']) / max(x['calls'], y['calls'], 1)
    return 0.3 * size + 0.15 * callr + 0.25 * j(x['ims'], y['ims']) + 0.3 * j(x['flts'], y['flts'])


def gu_u32(a):
    return GA.u32(a)


def main():
    global I4
    I4 = load_4u()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'em001'
    P4 = [a4u.u(0xe6b058 + 4 * k) for k in range(95)]
    PG = g.vslots(g.UENEMY_VT, 286)
    if cmd == 'em001':
        N = a4u.by_name()
        E4 = [a4u.u(a4u.vtables(N['uEm001'])[0] + 4 * k) for k in range(95)]
        C = g.classes()
        EG = g.vslots(C['uEm001_00']['vt'], 286)
        o4 = [(k, E4[k]) for k in range(95) if E4[k] != P4[k] and E4[k]]
        og = [(k, EG[k]) for k in range(286) if EG[k] != PG[k] and GA.INS.get(EG[k], ('', ''))[0] != 'b']
        fg = {k: features(GA.INS, f, gu_u32) for k, f in og}
        for k, f in o4:
            x = features(I4, f, a4u.u)
            best = sorted(((sim(x, fg[t]), t) for t, _ in og), reverse=True)[:3]
            print('4U slot %2d %x n=%-4d calls=%-3d flt=%-3d -> %s' % (
                k, f, x['n'], x['calls'], len(x['flts']),
                '  '.join('GU %d (%.2f, n=%d)' % (t, s, fg[t]['n']) for s, t in best)))
    elif cmd == 'base':
        fg = {k: features(GA.INS, PG[k], gu_u32) for k in range(286)}
        for k in range(95):
            x = features(I4, P4[k], a4u.u)
            best = sorted(((sim(x, fg[t]), t) for t in range(286)), reverse=True)[:3]
            print('4U base %2d %x n=%-4d -> %s' % (k, P4[k], x['n'],
                  '  '.join('GU %d (%.2f, n=%d)' % (t, s, fg[t]['n']) for s, t in best)))


if __name__ == '__main__':
    main()
