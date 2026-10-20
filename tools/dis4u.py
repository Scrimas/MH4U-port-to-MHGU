"""dis4u.py : fast lookups in dump/mh4u.asm (MH4U v1.1 disassembly).

  dis4u.py ADDR [N]          print N lines (default 60) from ADDR
  dis4u.py -f ADDR           print the function containing ADDR (push .. matching pop/bx lr, heuristic)
Library: lines(addr, n), func_bounds(addr), INS(addr) -> (mnemonic, operands)
"""
import array, bisect, mmap, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../dump/'
ASM = ROOT + 'mh4u.asm'
IDX = ROOT + 'mh4u.asm.idx'
_f = open(ASM, 'rb')
_mm = mmap.mmap(_f.fileno(), 0, access=mmap.ACCESS_READ)
LINE = re.compile(rb'^ +([0-9a-f]+):\s+(\S+)\s*(.*)$')


def _build():
    addrs = array.array('I'); offs = array.array('Q')
    pos = 0
    for line in iter(_mm.readline, b''):
        m = LINE.match(line)
        if m:
            addrs.append(int(m.group(1), 16)); offs.append(pos)
        pos += len(line)
    with open(IDX, 'wb') as f:
        f.write(len(addrs).to_bytes(8, 'little')); addrs.tofile(f); offs.tofile(f)
    return addrs, offs


def _load():
    if not os.path.exists(IDX) or os.path.getmtime(IDX) < os.path.getmtime(ASM):
        return _build()
    with open(IDX, 'rb') as f:
        n = int.from_bytes(f.read(8), 'little')
        addrs = array.array('I'); addrs.fromfile(f, n)
        offs = array.array('Q'); offs.fromfile(f, n)
    return addrs, offs


ADDRS, OFFS = _load()


def _line_at(i):
    _mm.seek(OFFS[i]); return _mm.readline().decode('latin-1').rstrip('\n')


def INS(a):
    i = bisect.bisect_left(ADDRS, a)
    if i >= len(ADDRS) or ADDRS[i] != a: return ('?', '')
    m = LINE.match(_line_at(i).encode('latin-1'))
    return (m.group(2).decode(), m.group(3).decode().split(' @')[0].split(' <')[0].strip()) if m else ('?', '')


def lines(a, n=60):
    i = bisect.bisect_left(ADDRS, a)
    out = []
    for k in range(i, min(i + n, len(ADDRS))):
        l = _line_at(k)
        out.append(re.sub(r' <\.text\+0x[0-9a-f]+>', '', l))
    return out


def func_bounds(a, maxn=6000):
    """start = nearest preceding push {..lr} / str lr,[sp,#-4]!; end = first pop {..pc}/ldr pc,[sp],#4/bx lr
    after which the next instruction is a new function start (heuristic)."""
    i = bisect.bisect_left(ADDRS, a)
    s = i
    while s > 0:
        mn, op = INS(ADDRS[s])
        if (mn.startswith('push') and 'lr' in op) or (mn == 'str' and op.startswith('lr, [sp, #-')):
            break
        s -= 1
    return ADDRS[s]


if __name__ == '__main__':
    if sys.argv[1] == '-f':
        a = int(sys.argv[2], 16); st = func_bounds(a)
        print('\n'.join(lines(st, int(sys.argv[3]) if len(sys.argv) > 3 else 200)))
    else:
        print('\n'.join(lines(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 60)))
