"""asm.py : (vendored from MHGU_Editor scratch/py, GPL-3.0-or-later) index of main.asm (addr -> (mnemonic, operands)), call graph, function starts."""
import re, pickle, os, collections, struct
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ (append: never shadow the caller's imports)
import paths  # noqa: E402
ROOT = paths.GU_CODE + '/'   # tools/setup.py gu_code: mem.bin, main.asm, caches
CACHE = ROOT + 'asmidx.pkl'
LINE = re.compile(r'^ +([0-9a-f]+):\s+\t?(\S+)\s*(.*)$')
MEM = open(ROOT + 'mem.bin', 'rb').read()
u32 = lambda a: struct.unpack_from('<I', MEM, a)[0]


def build():
    ins = {}
    for l in open(ROOT + 'main.asm', errors='replace'):
        m = LINE.match(l)
        if not m: continue
        a = int(m.group(1), 16)
        if a >= 0x13f1dec: continue
        ins[a] = (m.group(2), m.group(3).split(' @')[0].strip())
    return ins

if os.path.exists(CACHE):
    INS = pickle.load(open(CACHE, 'rb'))
else:
    INS = build(); pickle.dump(INS, open(CACHE, 'wb'))

BL = re.compile(r'^(bl|blx|b)(eq|ne|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le)?$')
def target(a):
    m, o = INS.get(a, ('', ''))
    if BL.match(m):
        t = o.split()[0]
        if t.startswith('0x'): return int(t, 16)
    return None

_calls = None
def callers():
    global _calls
    if _calls is None:
        p = ROOT + 'callers.pkl'
        if os.path.exists(p): _calls = pickle.load(open(p, 'rb'))
        else:
            _calls = collections.defaultdict(list)
            for a, (m, o) in INS.items():
                if m in ('bl', 'blx') or m.startswith('bl') and len(m) == 4:
                    t = target(a)
                    if t is not None: _calls[t].append(a)
            _calls = dict(_calls); pickle.dump(_calls, open(p, 'wb'))
    return _calls

_starts = None
def starts():
    """sorted function starts: call targets + code pointers stored in data (vtables, tables)."""
    global _starts
    if _starts is None:
        p = ROOT + 'fstarts.pkl'
        if os.path.exists(p): _starts = pickle.load(open(p, 'rb'))
        else:
            IMG, _ = pickle.load(open(ROOT + 'img_reloc.pkl', 'rb'))
            s = set(callers())
            for i in range(0x13f1dec, len(IMG) - 3, 4):
                v = struct.unpack_from('<I', IMG, i)[0] - 0x10000000
                if 0 <= v < 0x13f1dec and v % 4 == 0 and INS.get(v, ('',))[0] in ('push', 'mov', 'ldr', 'b', 'sub', 'add', 'cmp', 'vpush', 'str', 'movw', 'bx', 'ldrb', 'ldrh'):
                    s.add(v)
            _starts = sorted(s); pickle.dump(_starts, open(p, 'wb'))
    return _starts

def func_start(a):
    """nearest known function start at or before a (call target / code pointer), else push."""
    import bisect
    st = starts()
    i = bisect.bisect_right(st, a) - 1
    if i >= 0 and a - st[i] < 0x4000: return st[i]
    return func_start_push(a)

def func_start_push(a):
    """walk back to the nearest push {.., lr} / previous function end."""
    b = a
    while b > 0:
        m, o = INS.get(b, ('', ''))
        if m == 'push' and 'lr' in o: return b
        if b != a and (m == 'bx' and o == 'lr' or m == 'pop' and 'pc' in o): return b + 4
        b -= 4
    return 0

def dis(a, n=40):
    out = []
    for i in range(n):
        m, o = INS.get(a + 4 * i, ('?', ''))
        out.append('%8x  %-8s %s' % (a + 4 * i, m, o))
    return '\n'.join(out)

def func(a, maxn=3000):
    """instructions of the function starting at a, until a return followed by a push."""
    out = []; b = a
    for _ in range(maxn):
        m, o = INS.get(b, ('?', ''))
        out.append((b, m, o))
        if b != a and m == 'push' and 'lr' in o and out[-2][1] in ('bx', 'pop', 'b'): out.pop(); break
        b += 4
    return out

def pcrel_value(a):
    """value of `ldr rX,[pc,#imm]` at a, and the following add rX,pc,rX / ldr rX,[pc,rX] resolution."""
    m, o = INS[a]
    mm = re.search(r'\[pc, #(-?0x[0-9a-f]+|-?\d+)\]', o)
    if not mm: return None
    lit = a + 8 + int(mm.group(1), 0)
    return u32(lit)
