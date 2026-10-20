"""gu.py : MHGU 1.4 main static helpers on top of MHGU_Editor/scratch/py (asm.py index of main.asm).

pcref(b): address computed by the pc-relative instruction at b, with the literal it uses:
  `add rD, pc, rY`  -> (b+8+lit, 'addr', lit_addr)
  `ldr rD, [pc, rY]` -> (word at b+8+lit = GOT/data slot value, 'got', lit_addr)  (slot address returned too)
where rY was loaded by `ldr rY, [pc, #imm]` within the previous instructions.
"""
import re, struct, sys
import paths
sys.path.insert(0, paths.GU_PY)
import asm  # noqa: E402

INS = asm.INS
MEM = asm.MEM
u32 = asm.u32


def lit_of(b, reg, back=12):
    """address of the literal loaded into reg by `ldr reg, [pc, #imm]` before b."""
    for k in range(1, back):
        a = b - 4 * k
        m, o = INS.get(a, ('', ''))
        if m == 'ldr' and o.startswith(reg + ', [pc, #'):
            mm = re.search(r'\[pc, #(-?0x[0-9a-f]+|-?\d+)\]', o)
            return a + 8 + int(mm.group(1), 0)
        # stop if reg is overwritten by something else
        if o.split(',')[0].strip() == reg and m not in ('cmp', 'cmn', 'tst', 'str', 'strb', 'strh', 'push'):
            return None
    return None


def pcref(b):
    m, o = INS.get(b, ('', ''))
    mm = re.match(r'(r\d+), pc, (r\d+)$', o)
    if m == 'add' and mm:
        L = lit_of(b, mm.group(2))
        if L is None: return None
        return ((b + 8 + u32(L)) & 0xFFFFFFFF, 'addr', L, None)
    mm = re.match(r'(r\d+), \[pc, (r\d+)\]$', o)
    if m == 'ldr' and mm:
        L = lit_of(b, mm.group(2))
        if L is None: return None
        slot = (b + 8 + u32(L)) & 0xFFFFFFFF
        if 0 <= slot < len(MEM) - 4:
            return (u32(slot), 'got', L, slot)
    return None


def all_pcrefs(lo=0, hi=0x13f1dec):
    out = {}
    for b in INS:
        if lo <= b < hi:
            r = pcref(b)
            if r: out[b] = r
    return out


def dis(a, n=20):
    return ['%x: %s %s' % (a + 4 * k, *INS.get(a + 4 * k, ('?', ''))) for k in range(n)]
