"""vt.py : which class vtable(s) hold a function; class name from RTTI typeinfo (vtable[-1])."""
import pickle, struct, sys, re
import asm
IMG, _ = pickle.load(open(asm.ROOT + 'img_reloc.pkl', 'rb'))
B = 0x10000000
TEXT_END = 0x13f1dec
u = lambda a: struct.unpack_from('<I', IMG, a)[0]

def tiname(ti):
    """typeinfo: [vptr][name ptr]"""
    try:
        n = u(ti + 4) - B
        if 0 <= n < len(asm.MEM):
            e = asm.MEM.index(b'\0', n)
            s = asm.MEM[n:e]
            if 2 < len(s) < 200 and all(32 < c < 127 for c in s): return s.decode()
    except Exception: pass
    return None

def holders(fn):
    pat = struct.pack('<I', B + fn)
    out = []
    i = IMG.find(pat)
    while i != -1:
        if i % 4 == 0 and i >= TEXT_END:
            # walk back to the vtable head: offset-to-top (0 / small neg) then typeinfo pointer
            j = i - 4; name = None; idx = 0
            while j > i - 4 * 600:
                v = u(j)
                if not (B <= v < B + TEXT_END):
                    # j holds typeinfo?  j-4 holds offset-to-top
                    name = tiname(v - B) if B <= v < B + len(IMG) else None
                    break
                j -= 4; idx += 1
            out.append((i, idx, name))
        i = IMG.find(pat, i + 1)
    return out

if __name__ == '__main__':
    for a in sys.argv[1:]:
        f = int(a, 16)
        print(a, [(hex(i), idx, n) for i, idx, n in holders(f)])
