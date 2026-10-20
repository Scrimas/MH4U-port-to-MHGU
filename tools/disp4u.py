"""disp4u.py : resolve MH4U enemy action dispatchers by tiny emulation.

The dispatchers are compare trees / jump tables on bytes of the enemy work struct ([this+0xe28]).
run(entry, fields) executes from `entry` with this = OBJ, [OBJ+0xe28] = WORK and WORK bytes from
`fields` ({offset: value}), until it branches (b/bl, or ldr pc) to a function start; returns
(target, r1) or None (bx lr / pop pc = no action).

  disp4u.py ENTRY FIELD_OFF [fixed_off=val ...]   sweep FIELD_OFF over 0..255
"""
import re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a4u, dis4u

OBJ, WORK = 0x10000000, 0x20000000


def is_func_start(a):
    w = a4u.u(a)
    return (w & 0xFFFF4000) == 0xE92D4000 or w == 0xE52DE004


COND = {'eq', 'ne', 'cs', 'hs', 'cc', 'lo', 'mi', 'pl', 'vs', 'vc', 'hi', 'ls', 'ge', 'lt', 'gt', 'le', 'al'}


def split_cond(mn, base):
    if mn == base: return 'al'
    if mn.startswith(base) and mn[len(base):] in COND: return mn[len(base):]
    return None


def cond_ok(c, f):
    N, Z, C, V = f
    return {'al': True, 'eq': Z, 'ne': not Z, 'cs': C, 'hs': C, 'cc': not C, 'lo': not C, 'mi': N, 'pl': not N,
            'vs': V, 'vc': not V, 'hi': C and not Z, 'ls': (not C) or Z, 'ge': N == V, 'lt': N != V,
            'gt': (not Z) and N == V, 'le': Z or N != V}[c]


def imm(s):
    return int(s.lstrip('#'), 0)


def run(entry, fields, maxsteps=400):
    R = [0] * 16
    R[0] = OBJ
    F = (False, False, False, False)
    mem = lambda a, n: (WORK if a == OBJ + 0xe28 else 0) if n == 4 else (fields.get(a - WORK, 0) if WORK <= a < WORK + 0x10000 else 0)
    pc = entry
    for _ in range(maxsteps):
        mn, op = dis4u.INS(pc)
        if mn == '?': return ('?', pc)
        args = [x.strip() for x in re.split(r',(?![^\[]*\])', op)]
        nxt = pc + 4
        def rv(x):
            x = x.strip()
            if x.startswith('#'): return imm(x) & 0xFFFFFFFF
            if x == 'pc': return pc + 8
            if x == 'lr': return R[14]
            if x == 'sp': return R[13]
            return R[int(x[1:])]
        def rn(x): return {'sp': 13, 'lr': 14, 'pc': 15}.get(x, None) if x in ('sp', 'lr', 'pc') else int(x[1:])
        if mn.startswith('v') or mn.startswith('str'):
            # FP ops do not steer dispatch; stores into the work struct are kept
            m = re.match(r'(r\d+), \[(r\d+), #(0x[0-9a-f]+|\d+)\]$', op)
            if mn.startswith('str') and m and WORK <= rv(m.group(2)) < WORK + 0x10000:
                fields[rv(m.group(2)) + int(m.group(3), 0) - WORK] = R[int(m.group(1)[1:])] & 0xFF
            pc = nxt; continue
        c = None
        for base in ('ldrb', 'ldrh', 'ldr', 'cmp', 'cmn', 'subs', 'sub', 'adds', 'add', 'mov', 'bx', 'bl', 'b', 'pop', 'push', 'nop', 'tst', 'and', 'lsl', 'uxtb'):
            c = split_cond(mn, base)
            if c: break
        if c is None:
            return ('unk', pc, mn, op)
        if not cond_ok(c, F):
            pc = nxt; continue
        if base in ('push', 'nop'):
            pass
        elif base == 'pop':
            if 'pc' in op: return None
        elif base in ('ldr', 'ldrb', 'ldrh'):
            m = re.match(r'(\w+), \[(\w+)(?:, (#-?0x[0-9a-f]+|#-?\d+|r\d+(?:, lsl #\d+)?))?\](!?)$', op)
            if not m: return ('unk', pc, mn, op)
            rd, base_r, off = m.group(1), m.group(2), m.group(3)
            addr = rv(base_r)
            if off:
                if off.startswith('#'): addr += imm(off)
                else:
                    mm = re.match(r'(r\d+)(?:, lsl #(\d+))?', off)
                    addr += rv(mm.group(1)) << int(mm.group(2) or 0)
            if base_r == 'pc':
                val = a4u.u(addr)
            else:
                val = mem(addr, 1 if base == 'ldrb' else 4)
            if rd == 'pc':
                if is_func_start(val): return (val, R[1])
                pc = val; continue
            R[rn(rd)] = val & 0xFFFFFFFF
        elif base in ('cmp', 'cmn', 'tst'):
            a = rv(args[0]); b = rv(args[1])
            if base == 'tst':
                r = a & b; F = (bool(r >> 31), r == 0, F[2], F[3])
            else:
                if base == 'cmn': b = (-b) & 0xFFFFFFFF
                r = (a - b) & 0xFFFFFFFF
                sa, sb, sr = a >> 31, b >> 31, r >> 31
                F = (bool(sr), r == 0, a >= b, (sa != sb) and (sr != sa))
        elif base in ('sub', 'subs', 'add', 'adds', 'and', 'lsl'):
            a = rv(args[1]); b = rv(args[2]) if len(args) > 2 else 0
            r = {'sub': a - b, 'subs': a - b, 'add': a + b, 'adds': a + b, 'and': a & b, 'lsl': a << b}[base] & 0xFFFFFFFF
            if base in ('subs',):
                sa, sb, sr = a >> 31, b >> 31, r >> 31
                F = (bool(sr), r == 0, a >= b, (sa != sb) and (sr != sa))
            R[rn(args[0])] = r
        elif base == 'uxtb':
            R[rn(args[0])] = rv(args[1]) & 0xFF
        elif base == 'mov':
            R[rn(args[0])] = rv(args[1])
        elif base == 'bx':
            if args[0] == 'lr': return None
            return ('bx', args[0])
        elif base in ('b', 'bl'):
            t = int(re.match(r'0x([0-9a-f]+)', op).group(1), 16)
            if base == 'bl' or is_func_start(t) or t < entry - 0x40 or t > entry + 0x2000:
                return (t, R[1])
            pc = t; continue
        pc = nxt
    return ('loop', pc)


if __name__ == '__main__':
    entry = int(sys.argv[1], 16); off = int(sys.argv[2], 16)
    fixed = {int(k, 16): int(v, 0) for k, v in (a.split('=') for a in sys.argv[3:])}
    for v in range(256):
        r = run(entry, {**fixed, off: v})
        if r: print(v, r if isinstance(r[0], str) else ('%x' % r[0], 'r1=%d' % r[1]))
