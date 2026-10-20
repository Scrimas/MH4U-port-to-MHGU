"""a4u.py : static helpers for the MH4U v1.1 code (dump/exefs_v11/mem.bin, flat from 0x100000).

DTI registry: every MtDTI is built by a static init that calls 0x5bfabc(r0 = DTI (bss),
r1 = name, r2 = parent DTI, r3 = object size).  dtis() returns {dti: (name, parent, size)}.
"""
import os, pickle, re, struct

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../dump/'
M = open(ROOT + 'exefs_v11/mem.bin', 'rb').read()
B = 0x100000
TEXT_END = B + 0xcec784
DTI_CTOR = 0x5bfabc
W = struct.unpack_from('<%dI' % (len(M) // 4), M, 0)


def u(a):
    return W[(a - B) >> 2]


def cstr(a, n=80):
    if not B <= a < B + len(M): return None
    s = M[a - B:a - B + n].split(b'\0')[0]
    try: return s.decode()
    except UnicodeDecodeError: return None


def rot(imm12):
    r = (imm12 >> 8) * 2; v = imm12 & 0xFF
    return ((v >> r) | (v << (32 - r))) & 0xFFFFFFFF if r else v


def bl_target(a):
    w = u(a)
    if (w & 0x0F000000) != 0x0B000000: return None
    off = w & 0xFFFFFF
    if off & 0x800000: off -= 0x1000000
    return a + 8 + 4 * off


def reg_value(a, reg, back=16):
    """constant loaded into reg before address a (ldr =lit, add rX,pc,#, mov #)."""
    for b in range(a - 4, a - 4 * back, -4):
        w = u(b)
        if (w >> 28) != 0xE: continue
        rd = (w >> 12) & 15
        if rd != reg: continue
        if (w & 0x0F7F0000) == 0x051F0000:  # ldr rd, [pc, #+-imm]
            imm = w & 0xFFF
            return u(b + 8 + (imm if w & (1 << 23) else -imm))
        if (w & 0x0FEF0000) == 0x028F0000:  # add rd, pc, #imm
            return (b + 8 + rot(w & 0xFFF)) & 0xFFFFFFFF
        if (w & 0x0FEF0000) == 0x03A00000:  # mov rd, #imm
            return rot(w & 0xFFF)
        return None  # other write to rd
    return None


def _build_dtis():
    out = {}
    for i in range((TEXT_END - B) // 4):
        a = B + 4 * i
        if (W[i] & 0x0F000000) != 0x0B000000 or bl_target(a) != DTI_CTOR: continue
        d, n, p, s = (reg_value(a, r) for r in (0, 1, 2, 3))
        name = cstr(n) if n else None
        if d and name: out[d] = (name, p, s)
    return out


def dtis():
    cache = ROOT + 'dti.pkl'
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    r = _build_dtis(); pickle.dump(r, open(cache, 'wb')); return r


def by_name():
    return {v[0]: k for k, v in dtis().items()}


def chain(d):
    D = dtis(); out = []
    while d in D:
        out.append(D[d][0]); d = D[d][1]
    return out


_REFS = None


def refs(val):
    """addresses of aligned words equal to val (index built on first use)."""
    global _REFS
    if _REFS is None:
        _REFS = {}
        for i, w in enumerate(W):
            if B <= w < B + len(M) + 0x200000:
                _REFS.setdefault(w, []).append(B + 4 * i)
    return _REFS.get(val, [])


def getdti_funcs(dti):
    """functions `ldr r0, =dti; bx lr`."""
    out = []
    for L in refs(dti):
        for ins in range(L - 64, L, 4):
            w = u(ins)
            if (w & 0xFFFFF000) == 0xE59F0000 and ins + 8 + (w & 0xFFF) == L and u(ins + 4) == 0xE12FFF1E:
                out.append(ins)
    return out


GETDTI_SLOT = 5


def vtables(dti):
    return [r - 4 * GETDTI_SLOT for g in getdti_funcs(dti) for r in refs(g)]


def vtable_entries(vt):
    out = []; a = vt
    while B <= u(a) < TEXT_END:
        out.append(u(a)); a += 4
    return out
