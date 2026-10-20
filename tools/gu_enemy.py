"""gu_enemy.py : MHGU 1.4 enemy class survey (static; uses MHGU_Editor/scratch/py helpers).

  gu_enemy.py classes      DTI, size, newInstance, ctor, object vtable of every uEmXXX_YY / uEnemy
  gu_enemy.py slots [N]    uEnemy vtable slots vs overrides in the monster classes (first N slots)
"""
import collections, pickle, re, sys

sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
import asm, vt  # noqa: E402

B = 0x10000000
DTI_CTOR = 0x7aedcc
# monsters derive from uFestaEnemy (ctor 0xc9cf0, vtable 0x1734d44) < uEnemy (abstract, ctor 0xacc8c,
# vtable 0x1734798) < uEnemyBase
UENEMY_CTOR = 0xc9cf0
UENEMY_VT = 0x1734d44


def ins(a):
    return asm.INS.get(a, ('', ''))


def got_at(b):
    """value loaded by `ldr rX, [pc, rX]` (GOT) or computed by `add rX, pc, rX` at b."""
    m, o = ins(b)
    mm = re.match(r'(r\d+), (?:\[pc, (r\d+)\]|pc, (r\d+))$', o)
    if not mm: return None
    r = mm.group(2) or mm.group(3)
    for k in range(1, 14):
        a = b - 4 * k
        m2, o2 = ins(a)
        if m2 == 'ldr' and o2.startswith(r + ', [pc, #'):
            t = (b + 8 + asm.pcrel_value(a)) & 0xFFFFFFFF
            return vt.u(t) - B if mm.group(2) else t
    return None


def next_got(a, n=20, want='ldr'):
    for k in range(n):
        b = a + 4 * k
        m, o = ins(b)
        if (want == 'ldr' and m == 'ldr' and ', [pc, r' in o) or (want == 'add' and m == 'add' and ', pc, r' in o):
            v = got_at(b)
            if v is not None: return b, v
    return None, None


def movw_r3(site):
    for k in range(1, 20):
        m, o = ins(site - 4 * k)
        mm = re.match(r'r3, #(0x[0-9a-f]+|\d+)$', o)
        if m in ('movw', 'mov') and mm: return int(mm.group(1), 0)
    return None


def classes():
    names = pickle.load(open(asm.ROOT + 'dti.pkl', 'rb'))
    out = {}
    calls = asm.callers()
    for site in calls.get(DTI_CTOR, []):
        # name = string loaded into r1 (add r1, pc, r1) just before the call
        name = None
        for k in range(1, 8):
            m, o = ins(site - 4 * k)
            if m == 'add' and o.startswith('r1, pc, r1'):
                t = got_at(site - 4 * k)
                if t is not None:
                    e = asm.MEM.find(b'\0', t); name = asm.MEM[t:e].decode(errors='replace')
                break
        if not name or not re.fullmatch(r'uEm\d{3}_\d{2}|uEnemy|uFestaEnemy|uEnemyBase', name): continue
        size = movw_r3(site)
        _, dvt = next_got(site + 4)
        dvt = dvt + 8 if dvt is not None else None
        newi = vt.u(dvt + 8) - B if dvt else None
        ctor = None
        if newi:
            for k in range(30):
                m, o = ins(newi + 4 * k)
                if m == 'b':
                    ctor = int(o.split()[0], 16); break
        ovt = None
        if ctor:
            for k in range(12):
                m, o = ins(ctor + 4 * k)
                if m == 'bl' and int(o.split()[0], 16) == UENEMY_CTOR:
                    _, v = next_got(ctor + 4 * (k + 1))
                    ovt = v + 8 if v is not None else None
                    break
        out[name] = dict(site=site, size=size, dti_vt=dvt, newinst=newi, ctor=ctor, vt=ovt)
    return out


def vslots(v, n):
    return [vt.u(v + 4 * k) - B for k in range(n)]


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'classes'
    C = classes()
    if cmd == 'classes':
        for k in sorted(C):
            c = C[k]
            print('%-10s size %-7s dti_vt %-9s newInstance %-9s ctor %-9s vt %s' % (
                k, hex(c['size'] or 0), hex(c['dti_vt'] or 0), hex(c['newinst'] or 0), hex(c['ctor'] or 0), hex(c['vt'] or 0)))
    elif cmd == 'slots':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        base = vslots(UENEMY_VT, n)
        ov = collections.Counter(); who = collections.defaultdict(list)
        ems = [k for k in C if k != 'uEnemy' and C[k]['vt']]
        for k in ems:
            for i, (a, b) in enumerate(zip(vslots(C[k]['vt'], n), base)):
                if a != b: ov[i] += 1; who[i].append(k[3:6])
        for i in range(n):
            print('%3d %-9s overridden by %2d/%d %s' % (i, hex(base[i] & 0xFFFFFFFF), ov[i], len(ems), ' '.join(who[i][:12])))
