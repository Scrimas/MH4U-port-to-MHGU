"""react_seltas.py : the Desert Seltas Queen's 4U reactions (category 10) for module/seltas_react.c.

  react_seltas.py list        every case: 4U em-95 table vs 4U em-26 table (and GU's variant-0 table where it is a plain play)
  react_seltas.py c           the C tables + case list (stdout; module/seltas_react.c holds a reviewed copy)

4U (v1.1, read 2026-11-09, C): the Queen's dispatcher 0x7957c4 sends category 10 to 0x79463c, which tests the species
(W+0x1c0 == 26 -> the normal Queen's switch at 0x7946a4, else em 95's at 0x794660). Every case tail-calls the reaction
player 0x9197c0(this, table, flag), some after the hit direction 0x938620 or [W+0x8d88]+4; numbers without a case go
to 0x791504 (both species). GU 0xf9be10 keeps the normal Queen's switch and returns at once for any variant
(`ldrb [this+0xb5f5]; cmp #0; popne`), so a Desert Queen in GU never ends a reaction: the 2026-11-09 test log shows
her in 10/7 with her last attack's motion until her death (69 s and 53 s).
Tables: 8-byte ops {u32 op, u32 arg}; ops 0 / 1 / 2 / 0x35 point at a 24-byte motion descriptor (+0 u16 motion, +4 s32
blend, +8 s32 start frame, +0xc flags, +0x10 u16, +0x12 u8 movement type, +0x13 u8, +0x14 movement data), GU's has
floats at +4 / +8 (monsters/gogmazios/module/em089_react.c, C). Movement data: type 1 = 2 floats, types 2 / 3 / 7 / 8 = 6.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths   # noqa: E402

MEM4 = open(os.path.join(paths.DUMP, 'exefs_v11', 'mem.bin'), 'rb').read()
BASE4 = 0x100000
MEMG = open(os.path.join(paths.GU_CODE, 'mem.bin'), 'rb').read()

MOTION_OPS = (0x00, 0x01, 0x02, 0x35)
MV_FLOATS = {0: 0, 1: 2, 2: 6, 3: 6, 7: 6, 8: 6}
# movement data in 4U .bss, written by a static initializer at boot: {address: raw words} (C: 0xd26260..0xd2627c stores
# s0 = 0.0 (0xd262a8, set at 0xd26194 and not changed after), s1 = 0x40a33333 (0xd262d4) at +4 and 0xbdcccccd (0xd262d8)
# at +16, s0 elsewhere)
BSS_MV = {0x10b6820: (0x00000000, 0x40a33333, 0x00000000, 0x00000000, 0xbdcccccd, 0x00000000)}

# 4U em-95 cases (0x794660..; literal pool 0x794f10..0x794fe4). 'dir' = by the hit direction 0x938620 (GU 0x9e994):
# {direction: table}, '*' for the rest; 'male' = by [W+0x8d88]+4 == 1 (GU [this+0xcac0]+4, the case GU keeps for 155).
EM95 = {
    7: ('dir', {6: 0xfde1c4, '*': 0xfde1a4}, 0),
    8: 0xfde3b4, 83: 0xfde3b4, 181: 0xfde3b4, 225: 0xfde3b4,          # flag 1 (below)
    20: ('dir', {2: 0xfde2cc, 3: 0xfde2cc, 4: 0xfde1fc, 5: 0xfde1fc, '*': 0xfde1c4}, 0),
    27: 0xfde564, 29: 0xfde494, 30: 0xfde4a4, 31: 0xfde474, 32: 0xfde50c,
    37: 0xfde41c, 150: 0xfde41c,                                       # flag 1
    42: 0xfde544, 112: 0xfde544, 43: 0xfde534, 68: 0xfde4cc, 69: 0xfde4cc,
    82: 0xfde5e4, 180: 0xfde5e4,
    96: 0xfde5f4, 103: 0xfde5f4, 97: 0xfde604, 98: 0xfde614, 104: 0xfde614, 99: 0xfde634, 100: 0xfde644,
    101: 0xfde624, 102: 0xfde624, 105: 0xfde654, 110: 0xfde68c,
    135: 0xfde1a4, 148: 0xfde1a4,
    155: ('male', {1: 0xfde274, '*': 0xfde234}, 0),
    161: 0xfde6b4, 167: 0xfde6fc, 169: 0xfde72c, 197: 0xfde72c, 171: 0xfde74c, 173: 0xfde74c,
    187: 0xfde75c, 188: 0xfde794, 189: 0xfde7bc, 190: 0xfde7ec, 210: 0xfde5a4, 217: 0xfde1fc,
}
FLAG1 = {8, 83, 181, 225, 37, 150}
# the normal Queen's (em 26, 0x7946a4..) for comparison
EM26 = {
    7: ('dir', {6: 0xfde1b4, '*': 0xfde194}, 0),
    8: 0xfde2f4, 83: 0xfde2f4, 181: 0xfde2f4, 225: 0xfde2f4,
    20: ('dir', {2: 0xfde2a4, 3: 0xfde2a4, 4: 0xfde1d4, 5: 0xfde1d4, '*': 0xfde1b4}, 0),
    27: 0xfde554, 29: 0xfde484, 30: 0xfde4a4, 31: 0xfde474, 32: 0xfde4e4,
    37: 0xfde35c, 150: 0xfde35c,
    42: 0xfde544, 112: 0xfde544, 43: 0xfde534, 68: 0xfde4b4, 69: 0xfde4b4,
    82: 0xfde5d4, 180: 0xfde5d4,
    96: 0xfde5f4, 103: 0xfde5f4, 97: 0xfde604, 98: 0xfde614, 104: 0xfde614, 99: 0xfde634, 100: 0xfde644,
    101: 0xfde624, 102: 0xfde624, 105: 0xfde654, 110: 0xfde664,
    148: 0xfde194,
    155: ('male', {1: 0xfde244, '*': 0xfde224}, 0),
    161: 0xfde6b4, 167: 0xfde6cc, 169: 0xfde72c, 197: 0xfde72c, 171: 0xfde73c, 173: 0xfde73c,
    187: 0xfde75c, 188: 0xfde784, 189: 0xfde7a4, 190: 0xfde7d4, 210: 0xfde574, 217: 0xfde1d4,
}


def u32(a): return struct.unpack_from('<I', MEM4, a - BASE4)[0]
def s32(a): return struct.unpack_from('<i', MEM4, a - BASE4)[0]
def u16(a): return struct.unpack_from('<H', MEM4, a - BASE4)[0]
def u8(a): return MEM4[a - BASE4]
def f32(a): return struct.unpack_from('<f', MEM4, a - BASE4)[0]


def table(a):
    """[(op, arg)] up to and with op 0xff"""
    out = []
    for k in range(64):
        op, arg = u32(a + 8 * k), u32(a + 8 * k + 4)
        out.append((op, arg))
        if op == 0xff: return out
    raise SystemExit('table %x: no end' % a)


def desc(a):
    """4U motion descriptor -> dict (blend / start as numbers)"""
    d = dict(motion=u16(a), pad=u16(a + 2), blend=s32(a + 4), start=s32(a + 8), flags=u32(a + 12), kind=u16(a + 16),
             move=u8(a + 18), b13=u8(a + 19), mv=u32(a + 20))
    if d['move'] not in MV_FLOATS: raise SystemExit('descriptor %x: movement type %d' % (a, d['move']))
    n = MV_FLOATS[d['move']]
    if d['mv'] and d['mv'] - BASE4 + 4 * n > len(MEM4):          # .bss: filled by a static initializer (BSS_MV)
        if d['mv'] not in BSS_MV: raise SystemExit('descriptor %x: movement data %x in .bss, not in BSS_MV' % (a, d['mv']))
        d['mvdata'] = list(BSS_MV[d['mv']])
    else:
        d['mvdata'] = [u32(d['mv'] + 4 * i) for i in range(n)] if d['mv'] else []
    return d


def fl(w):
    return struct.unpack('<f', struct.pack('<I', w))[0]


def show(a):
    s = []
    for op, arg in table(a):
        if op in MOTION_OPS:
            d = desc(arg)
            s.append('op%x(m%03x b%d s%d f%x k%d mv%d%s)' % (op, d['motion'], d['blend'], d['start'], d['flags'], d['kind'], d['move'],
                                                         ' ' + '/'.join('%g' % fl(x) for x in d['mvdata']) if d['mvdata'] else ''))
        elif op == 0xff:
            s.append('end')
        else:
            s.append('op%x(%x)' % (op, arg))
    return ' '.join(s)


def tables_of(spec):
    if isinstance(spec, int): return {'': spec}
    return {str(k): v for k, v in spec[1].items()}


def main_list():
    for n in sorted(EM95):
        a95, a26 = tables_of(EM95[n]), (tables_of(EM26[n]) if n in EM26 else {})
        for key in a95:
            t95 = a95[key]
            t26 = a26.get(key) or a26.get('*') or a26.get('')
            same = t26 == t95
            print('%3d%s flag %d  4U em95 %x: %s' % (n, (' [%s]' % key) if key else '', 1 if n in FLAG1 else 0, t95, show(t95)))
            if not same and t26:
                print('            em26 %x: %s' % (t26, show(t26)))
            elif same:
                print('            (em26: the same table)')


def gu32(a): return struct.unpack_from('<I', MEMG, a)[0]
def guf(a): return struct.unpack_from('<f', MEMG, a)[0]


def gu_show(a):
    """GU table (main offset) in show()'s form: descriptors with float blend / start"""
    s = []
    for k in range(64):
        op, arg = gu32(a + 8 * k), gu32(a + 8 * k + 4)
        if op in MOTION_OPS:
            mv, move = gu32(arg + 20), MEMG[arg + 18]
            n = MV_FLOATS.get(move, 0)
            if mv and mv + 4 * n > len(MEMG): data = 'bss:%x' % mv
            else: data = '/'.join('%g' % guf(mv + 4 * i) for i in range(n)) if mv else ''
            s.append('op%x(m%03x b%g s%g f%x k%d mv%d%s)' % (op, struct.unpack_from('<H', MEMG, arg)[0], guf(arg + 4), guf(arg + 8),
                                                         gu32(arg + 12), struct.unpack_from('<H', MEMG, arg + 16)[0], move,
                                                         ' ' + data if data else ''))
        elif op == 0xff:
            s.append('end'); break
        else:
            s.append('op%x(%x)' % (op, arg))
    return ' '.join(s)


# GU's variant-0 (normal Queen) tables: 0xf9be10's jump table (0xf9be4c, numbers 7..210), each case `ldr / add r0, pc /
# add r1, r0, #off` then the shared tail to 0xa134c (C, 2026-11-09). 7 / 20 pick by 0x9e994, 155 by [this+0xcac0]+4.
GU_V0 = {8: 0x17e8ec0, 27: 0x17e8bb0, 29: 0x17e8b60, 30: 0x17e8b70, 31: 0x17e8b40, 32: 0x17e8d78, 37: 0x17e8e60,
         42: 0x17e8b30, 43: 0x17e8b50, 68: 0x17e8be0, 69: 0x17e8be0, 82: 0x17e8bc0, 83: 0x17e8ec0, 96: 0x17e8ac0,
         97: 0x17e8ad0, 98: 0x17e8ae0, 99: 0x17e8af0, 100: 0x17e8b00, 101: 0x17e8b10, 102: 0x17e8b10, 103: 0x17e8ac0,
         104: 0x17e8ae0, 105: 0x17e8b20, 110: 0x17e8d50, 112: 0x17e8b30, 148: 0x17e8aa0, 150: 0x17e8e60, 161: 0x17e8c00,
         167: 0x17e8dd0, 169: 0x17e8b80, 171: 0x17e8b90, 173: 0x17e8b90, 180: 0x17e8bc0, 181: 0x17e8ec0, 187: 0x17e8da0,
         188: 0x17e8bd0, 189: 0x17e8c18, 190: 0x17e8c30, 197: 0x17e8b80, 210: 0x17e8e30}


def main_gu():
    for n, g in sorted(GU_V0.items()):
        t26 = tables_of(EM26[n]).get('') if n in EM26 else None
        a, b = gu_show(g), show(t26) if t26 else '-'
        print('%3d GU %x: %s' % (n, g, a))
        print('    4U em26 %s: %s%s' % ('%x' % t26 if t26 else '-', b, '   [same]' if a.replace('b2 ', 'b2 ') == b else ''))


def c_name(a): return 'T_%x' % a


# ops whose arg points at data, besides the motion ops: 0x2e {u32 id, float, u32} (4U 0x93457c / GU 0xaa418 camera
# event, em089_react.c), 0xe {u32}; 0xfe takes a pointer in some tables (99..105), all of them shared below
PTR_OPS = {0x2e: 3, 0x0e: 1}


def shared():
    """numbers whose 4U em-95 table is the normal Queen's: {n: GU's normal-Queen table}"""
    out = {}
    for n, s95 in EM95.items():
        if isinstance(s95, int) and EM26.get(n) == s95:
            assert n in GU_V0, n
            out[n] = GU_V0[n]
    return out


def main_c():
    sh = shared()
    own = {n: s for n, s in EM95.items() if n not in sh}
    used = sorted({t for spec in own.values() for t in tables_of(spec).values()})
    descs, mvs, ptrs, out = {}, {}, {}, []
    for t in used:
        for op, arg in table(t):
            if op in MOTION_OPS: descs[arg] = desc(arg)
            elif op in PTR_OPS: ptrs[arg] = [u32(arg + 4 * i) for i in range(PTR_OPS[op])]
            elif op == 0xfe and arg: raise SystemExit('table %x: op 0xfe with data %x' % (t, arg))
    for a, d in sorted(descs.items()):
        if d['mv'] and d['mv'] not in mvs:
            mvs[d['mv']] = d['mvdata']
    out.append('/* ---- tables (monsters/desert_seltas/tools/react_seltas.py c; names = 4U addresses) ---- */')
    for a, v in sorted(mvs.items()):
        out.append('static const uint32_t MV_%x[%d] = {%s};   /* %s */' % (a, len(v), ', '.join('0x%08x' % x for x in v),
                                                                          ' '.join('%g' % fl(x) for x in v)))
    for a, v in sorted(ptrs.items()):
        out.append('static const uint32_t E_%x[%d] = {%s};' % (a, len(v), ', '.join('0x%08x' % x for x in v)))
    for a, d in sorted(descs.items()):
        out.append('static const rx_desc D_%x = {0x%03x, %d, %d.0f, %d.0f, 0x%x, %d, %d, %d, %s};' % (
            a, d['motion'], d['pad'], d['blend'], d['start'], d['flags'], d['kind'], d['move'], d['b13'],
            ('MV_%x' % d['mv']) if d['mv'] else '0'))
    for t in used:
        ops = []
        for op, arg in table(t):
            if op in MOTION_OPS: ops.append('{0x%x, &D_%x}' % (op, arg))
            elif op in PTR_OPS: ops.append('{0x%x, E_%x}' % (op, arg))
            else: ops.append('{0x%x, I(0x%x)}' % (op, arg))
        out.append('static const rx_op %s[] = {%s};' % (c_name(t), ', '.join(ops)))
    out.append('')
    out.append('/* ---- the switch (4U 0x794660..; numbers 4U shares with the normal Queen play GU\'s normal-Queen table) ---- */')
    cases = {}
    for n in sorted(EM95):
        if n in sh:
            cases.setdefault(('gu', sh[n], 0), []).append(n)
        elif isinstance(EM95[n], int):
            cases.setdefault(('t', EM95[n], 1 if n in FLAG1 else 0), []).append(n)
        else:
            cases.setdefault(('c', n), []).append(n)
    for key, ns in sorted(cases.items(), key=lambda x: x[1][0]):
        lab = ' '.join('case %d:' % n for n in ns)
        if key[0] == 'gu':
            out.append('    %s t = GU_T(0x%x); break;   /* 4U: the normal Queen\'s table */' % (lab, key[1]))
        elif key[0] == 't':
            out.append('    %s t = %s;%s break;' % (lab, c_name(key[1]), ' flag = 1;' if key[2] else ''))
        else:
            kind, sub, _ = EM95[key[1]]
            rest = c_name(sub['*'])
            if kind == 'dir':
                conds = {}
                for d, tt in sub.items():
                    if d != '*': conds.setdefault(tt, []).append(d)
                expr = rest
                for tt, ds in sorted(conds.items(), reverse=True):
                    expr = '(%s) ? %s : %s' % (' || '.join('d == %d' % d for d in ds), c_name(tt), expr)
                out.append('    %s { uint32_t d = hitDir(self); t = %s; } break;' % (lab, expr))
            else:
                out.append('    %s t = MALE_BYTE(self) == 1 ? %s : %s; break;' % (lab, c_name(sub[1]), rest))
    print('\n'.join(out))


if __name__ == '__main__':
    {'list': main_list, 'c': main_c, 'gu': main_gu}[sys.argv[1] if len(sys.argv) > 1 else 'list']()
