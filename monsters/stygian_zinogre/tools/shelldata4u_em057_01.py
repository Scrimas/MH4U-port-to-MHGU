"""shelldata4u_em057_01.py : the 4U static-init data of Stygian Zinogre's shells (notes/b5-shells.md step 1). Read-only:
it only prints (module/em057_01_shelldata.h is written by hand from its output).

MH4U v1.1 keeps these vectors at 0 in its image; static initializers fill them. This tool runs those initializers
under unicorn (the MHGU_Editor scratch venv) and prints what they leave:
  4U 0xd27970 (relative init_array entry): uEm048's statics
    - the 72-B orb records {off, A, B: float[4]; f0..f5} of 0xfebc18 0xfebd38 0xfebe58 0xfebf78 0xfec098 (record
      selector 0x856900): the init writes off / A / B, f0..f5 are .data
    - the 24-B pillar frame tables {float frame, u32, float x, y, z, u32} of 0xfeba98 (1/6.. loop 0x8470a4),
      0xfebb28 / 0xfebbb8 (2/40, 0x84555c / 0x845578): the init writes x / y / z, a row with frame < 0 ends a table
  4U 0xd1daf0 (relative init_array entry): the MT math constants, vector block 0x10e6378.. (16 B each); the orb's arc
    axis = the vector at 0x10e63a8 (uShell046 0xc89508 copies x, y, z to shell +0x2e8); the effect request ctor
    0xc0ca90 copies 0x10e6378 (position, rotation) and 0x10e6388 (scale) as its defaults
  GU 0xf06104 (absolute init_array entry): the static init of uEm057_00's unit, which fills GU's copy of 0xfeba98 at
    bss 0x2132a50 (32-B rows {float frame, 3 words, float x, y, z, word}; GU's 1/6.. loop 0xef4494 reads the frames):
    the cross-check of step 1.
Stubs: 4U 0x5bfabc (MtDTI ctor: links the class DTI into the DTI tree, writes nothing the tables use) returns at once;
GU SDK imports (dump/gu_plt.json): memclr / memset / memcpy done, the rest return r0. Reads of data / bss by an init
are listed (a dependence on another initializer would show there).

  /home/scrimas/Projects/MHGU_Editor/scratch/venv/bin/python -I -B monsters/stygian_zinogre/tools/shelldata4u_em057_01.py
      [--check]      --check: also compare module/em057_01_shelldata.h (its tables, addresses, axis) with the run
"""
import json, os, re, struct, sys
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC, \
    UC_ARM_REG_SP, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths  # noqa: E402

B4 = 0x100000                                  # 4U mem.bin is flat from here
STACK, RET = 0x20000000, 0x30000000            # outside both images
INIT_4U = [(0xd27970, 'uEm048 statics'), (0xd1daf0, 'MT math constants')]
DTI_CTOR_4U = 0x5bfabc
ORB_TABLES = [(0xfebc18, 4, 'HR, kind 0 (rank < 5)'), (0xfebd38, 4, 'HR, kind 1 (rank < 5)'),
              (0xfebe58, 4, 'G, kind 0 (rank >= 5)'), (0xfebf78, 4, 'G, kind 1 (rank >= 5)'),
              (0xfec098, 10, 'G, kind 2 = vt77 (rank >= 5)')]
FRAME_TABLES = [(0xfeba98, '1/6.. charge stance (0x8470a4)'), (0xfebb28, '2/40 step 1 (0x84555c)'),
                (0xfebbb8, '2/40 step 2 (0x845578)')]
MT_BLOCK = (0x10e6378, 9)                      # 0x10e6378..0x10e6407
AXIS = 0x10e63a8
GU_INIT, GU_ROWS = 0xf06104, 0x2132a50
GU_IMG_END = 0x2147000                         # tools/guemu.py
GU_PCREFS = [(0xef44b4, 0xef45d0, '1/6.. loop row base'), (0xef4498, 0xef45cc, '1/6.. loop first frame'),
             (0xf065c4, 0xf07118, 'static init 0xf06104 table base')]


def f32(b, o):
    return struct.unpack_from('<f', b, o)[0]


def fmt(v):
    return '%.9g' % v


def init_array_4u(mem, fn):
    """the relative init_array (entry + its address = function) holding fn -> (start, count, index)"""
    n = len(mem) // 4
    w = struct.unpack('<%dI' % n, mem[:n * 4])
    hits = [i for i in range(n) if (w[i] + B4 + 4 * i) & 0xFFFFFFFF == fn]
    assert len(hits) == 1, (hex(fn), hits)
    text = lambda i: 0 <= i < n and B4 <= (w[i] + B4 + 4 * i) & 0xFFFFFFFF < 0xDED000
    lo = hi = hits[0]
    while text(lo - 1): lo -= 1
    while text(hi + 1): hi += 1
    return B4 + 4 * lo, hi - lo + 1, hits[0] - lo


def new_uc():
    """an ARM unicorn with the VFP on (CPACR cp10 / cp11 full access, FPEXC.EN): both inits use VFP stores"""
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.reg_write(UC_ARM_REG_C1_C0_2, uc.reg_read(UC_ARM_REG_C1_C0_2) | (0xF << 20))
    uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
    return uc


def run(uc, fn, stubs, log):
    """call fn() with every stub address returning at once; -> error text or None"""
    def on_stub(uc_, addr, size, _):
        log.append('stub %s (lr 0x%x)' % (stubs[addr], uc_.reg_read(UC_ARM_REG_LR)))
        uc_.reg_write(UC_ARM_REG_PC, uc_.reg_read(UC_ARM_REG_LR))
    hs = [uc.hook_add(UC_HOOK_CODE, on_stub, begin=a, end=a) for a in stubs]
    uc.reg_write(UC_ARM_REG_SP, STACK + 0xF0000)
    uc.reg_write(UC_ARM_REG_LR, RET)
    err = None
    try:
        uc.emu_start(fn, RET, count=50_000_000)
    except UcError as e:
        err = '%s at pc=0x%x lr=0x%x' % (e, uc.reg_read(UC_ARM_REG_PC), uc.reg_read(UC_ARM_REG_LR))
    for h in hs: uc.hook_del(h)
    return err


def emulate_4u():
    """run the two 4U inits in init_array order -> (memory after, image, notes)"""
    mem = open(os.path.join(paths.DUMP, 'exefs_v11', 'mem.bin'), 'rb').read()
    exh = open(os.path.join(paths.DUMP, 'exefs_v11', 'exheader.bin'), 'rb').read()
    data_addr, _, data_size = struct.unpack_from('<III', exh, 0x30)
    bss_end = data_addr + data_size + struct.unpack_from('<I', exh, 0x3C)[0]
    end = (bss_end + 0xFFF) & ~0xFFF
    assert B4 + len(mem) <= end
    notes = ['4U image 0x%x..0x%x (mem.bin), data 0x%x+0x%x, bss to 0x%x' % (B4, B4 + len(mem), data_addr, data_size,
                                                                          bss_end)]
    order = []
    for fn, what in INIT_4U:
        start, count, idx = init_array_4u(mem, fn)
        order.append((idx, fn, what))
        notes.append('C: 4U 0x%x (%s) = init_array entry %d of %d (relative array at 0x%x)' % (fn, what, idx, count,
                                                                                            start))
    uc = new_uc()
    uc.mem_map(B4, end - B4)
    uc.mem_write(B4, mem)
    uc.mem_map(STACK, 0x100000)
    uc.mem_map(RET, 0x1000)
    for _, fn, what in sorted(order):
        log, reads, writes = [], set(), set()
        hr = uc.hook_add(UC_HOOK_MEM_READ, lambda u, k, a, s, v, _: reads.update(range(a, a + s)),
                         begin=data_addr, end=end - 1)
        hw = uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, k, a, s, v, _: writes.update(range(a, a + s)),
                         begin=B4, end=end - 1)
        err = run(uc, fn, {DTI_CTOR_4U: 'MtDTI ctor 0x5bfabc'} if fn == 0xd27970 else {}, log)
        uc.hook_del(hr); uc.hook_del(hw)
        assert err is None, '4U 0x%x: %s' % (fn, err)
        notes.append('run 4U 0x%x: returned; %d bytes written; %s; data / bss reads: %s' % (
            fn, len(writes), ', '.join(log) or 'no stub hit', spans(reads) or 'none'))
        notes.append('  writes in the tables / MT block: %s' % spans(
            {a for a in writes if 0xFEBA00 <= a < 0xFEC400 or 0x10E6300 <= a < 0x10E6480}))
    return bytes(uc.mem_read(B4, end - B4)), mem, notes


def spans(addrs):
    out, run_ = [], None
    for a in sorted(addrs):
        if run_ and a == run_[1]: run_[1] = a + 1
        else:
            if run_: out.append(run_)
            run_ = [a, a + 1]
    if run_: out.append(run_)
    return ' '.join('0x%x..0x%x' % (a, b - 1) for a, b in out)


def emulate_gu():
    """GU's static init 0xf06104 (its unit's tables, among them the copy of 4U 0xfeba98) -> (memory, notes)"""
    mem = open(paths.GU_MAIN, 'rb').read()
    u32 = lambda a: struct.unpack_from('<I', mem, a)[0]
    notes = []
    for b, lit, what in GU_PCREFS:          # `ldr rY, [pc, #imm]` ... `add rD, pc, rY` at b
        assert u32(b) & 0x0FFF0FF0 == 0x008F0000, hex(b)
        notes.append('C: GU 0x%x: add pc -> 0x%x (literal 0x%x; %s)' % (b, (b + 8 + u32(lit)) & 0xFFFFFFFF, lit, what))
    assert (0xef44b4 + 8 + u32(0xef45d0)) & 0xFFFFFFFF == GU_ROWS == (0xf065c4 + 8 + u32(0xf07118)) & 0xFFFFFFFF
    n = len(mem) // 4
    w = struct.unpack('<%dI' % n, mem[:n * 4])
    ia = [4 * i for i in range(n) if w[i] == GU_INIT]
    notes.append('C: GU init_array slot(s) holding 0x%x: %s' % (GU_INIT, ' '.join('0x%x' % a for a in ia)))
    assert len(ia) == 1
    plt = {int(k, 16): v for k, v in json.load(open(os.path.join(paths.DUMP, 'gu_plt.json'))).items()}
    uc = new_uc()
    uc.mem_map(0, GU_IMG_END)
    uc.mem_write(0, mem[:GU_IMG_END].ljust(GU_IMG_END, b'\0'))
    uc.mem_map(STACK, 0x100000)
    uc.mem_map(RET, 0x1000)
    calls = []

    def on_plt(uc_, addr, size, _):
        if addr not in plt: return
        name = plt[addr]
        r0, r1, r2 = (uc_.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if name.startswith('__aeabi_memclr'): uc_.mem_write(r0, bytes(r1))
        elif name.startswith('__aeabi_memset'): uc_.mem_write(r0, bytes([r2 & 0xFF]) * r1)
        elif name == 'memset': uc_.mem_write(r0, bytes([r1 & 0xFF]) * r2)
        elif name in ('memcpy', 'memmove') or name.startswith(('__aeabi_memcpy', '__aeabi_memmove')):
            uc_.mem_write(r0, bytes(uc_.mem_read(r1, r2)))
        calls.append(name)
        uc_.reg_write(UC_ARM_REG_PC, uc_.reg_read(UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE, on_plt, begin=min(plt), end=max(plt))
    err = run(uc, GU_INIT, {}, [])
    assert err is None, 'GU 0x%x: %s' % (GU_INIT, err)
    notes.append('run GU 0x%x: returned; SDK imports called: %s' % (GU_INIT, sorted(set(calls))))
    return bytes(uc.mem_read(0, GU_IMG_END)), notes


HEADER = os.path.join(os.path.dirname(HERE), 'module', 'em057_01_shelldata.h')
H_ORB = [('sz_orb_hr0', 'SZ_4U_ORB_HR0'), ('sz_orb_hr1', 'SZ_4U_ORB_HR1'), ('sz_orb_g0', 'SZ_4U_ORB_G0'),
         ('sz_orb_g1', 'SZ_4U_ORB_G1'), ('sz_orb_g2', 'SZ_4U_ORB_G2')]                   # ORB_TABLES order
H_ROWS = [('sz_pillar_stance', 'SZ_4U_PILLAR_STANCE'), ('sz_pillar_walk1', 'SZ_4U_PILLAR_WALK1'),
          ('sz_pillar_walk2', 'SZ_4U_PILLAR_WALK2')]                                     # FRAME_TABLES order


def check_header(m4, rows4):
    """the header's tables / #defines against the run -> list of differences"""
    src = re.sub(r'/\*.*?\*/', '', open(HEADER).read(), flags=re.S)
    defs = {k: int(v, 0) for k, v in re.findall(r'#define (SZ_\w+)\s+(0x[0-9a-f]+|\d+)u\b', src)}
    tabs = {k: (int(n), [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', body)])
            for k, n, body in re.findall(r'static const \w+ (\w+)\[(\d+)\] = \{(.*?)\};', src, flags=re.S)}
    bad = []
    for (name, d), (a, cnt, _) in zip(H_ORB, ORB_TABLES):
        n, vals = tabs[name]
        if defs.get(d) != a or n != cnt or struct.pack('<%df' % len(vals), *vals) != m4[a - B4:a - B4 + 72 * cnt]:
            bad.append('%s / %s != 4U 0x%x' % (name, d, a))
    for (name, d), (a, _) in zip(H_ROWS, FRAME_TABLES):
        n, vals = tabs[name]
        packed = b''.join(struct.pack('<fIfffI', v[0], int(v[1]), v[2], v[3], v[4], int(v[5]))
                          for v in zip(*[iter(vals)] * 6))
        if defs.get(d) != a or n != len(rows4[a]) or len(vals) != 6 * n or packed != m4[a - B4:a - B4 + 24 * n]:
            bad.append('%s / %s != 4U 0x%x' % (name, d, a))
    n, vals = tabs['sz_orb_arc_axis']
    if defs.get('SZ_4U_ORB_ARC_AXIS') != AXIS or struct.pack('<4f', *vals) != m4[AXIS - B4:AXIS - B4 + 16]:
        bad.append('sz_orb_arc_axis != 4U 0x%x' % AXIS)
    if defs.get('SZ_GU_PILLAR_STANCE') != GU_ROWS or defs.get('SZ_GU_PILLAR_STRIDE') != 32:
        bad.append('SZ_GU_PILLAR_STANCE / _STRIDE != GU 0x%x / 32' % GU_ROWS)
    return bad


def frame_rows(m, base, a, stride, offs):
    """rows of a frame table up to and including the first with frame < 0"""
    rows = []
    while True:
        rows.append(tuple(f32(m, a - base + o) for o in offs) + (a,))
        if rows[-1][0] < 0 or len(rows) > 16: return rows
        a += stride


def main():
    m4, img4, notes = emulate_4u()
    for n in notes: print(n)
    print('\n== orb records (72 B: off, A, B = float[4] x, y, z, w from the init; f0..f5 = .data) ==')
    for a, cnt, what in ORB_TABLES:
        print('4U 0x%x  %s, %d records' % (a, what, cnt))
        for i in range(cnt):
            o = a + 72 * i - B4
            v = struct.unpack_from('<18f', m4, o)
            same = img4[o + 48:o + 72] == m4[o + 48:o + 72]
            print('  [%d] 0x%x off (%s)  A (%s)  B (%s)  f0..f5 %s%s' % (
                i, a + 72 * i, ', '.join(fmt(x) for x in v[0:4]), ', '.join(fmt(x) for x in v[4:8]),
                ', '.join(fmt(x) for x in v[8:12]), ' '.join(fmt(x) for x in v[12:18]),
                '' if same else '  (f0..f5 CHANGED by the init)'))
    print('\n== pillar frame tables (24 B: frame, u32 +4, x, y, z, u32 +20; ends at frame < 0) ==')
    rows4 = {}
    for a, what in FRAME_TABLES:
        rows4[a] = frame_rows(m4, B4, a, 24, (0, 8, 12, 16))
        print('4U 0x%x  %s, %d rows (terminator included)' % (a, what, len(rows4[a])))
        for r in rows4[a]:
            o = r[-1] - B4
            print('  0x%x frame %s  x %s  y %s  z %s  (+4 0x%x, +20 0x%x)' % (
                r[-1], fmt(r[0]), fmt(r[1]), fmt(r[2]), fmt(r[3]), struct.unpack_from('<I', m4, o + 4)[0],
                struct.unpack_from('<I', m4, o + 20)[0]))
    print('\n== MT vector constants (0xd1daf0) ==')
    base, cnt = MT_BLOCK
    for i in range(cnt):
        a = base + 16 * i
        print('  0x%x (%s)%s' % (a, ', '.join(fmt(f32(m4, a - B4 + 4 * k)) for k in range(4)),
                                 '   <- orb arc axis (0xc89508)' if a == AXIS else
                                 '   <- effect request default position / rotation (0xc0ca90)' if a == 0x10e6378 else
                                 '   <- effect request default scale (0xc0ca90)' if a == 0x10e6388 else ''))
    print('\n== GU copy of 4U 0xfeba98 ==')
    mg, gnotes = emulate_gu()
    for n in gnotes: print(n)
    rg = frame_rows(mg, 0, GU_ROWS, 32, (0, 16, 20, 24))
    ok = len(rg) == len(rows4[0xfeba98])
    for r, r4 in zip(rg, rows4[0xfeba98]):
        same = r[:4] == r4[:4]
        ok &= same
        print('  GU 0x%x frame %s  x %s  y %s  z %s  words %s  | 4U %s' % (
            r[-1], fmt(r[0]), fmt(r[1]), fmt(r[2]), fmt(r[3]),
            ' '.join('%x' % x for x in struct.unpack_from('<8I', mg, r[-1])), 'same' if same else 'DIFFERS'))
    print('C: GU 0x%x rows %s 4U 0xfeba98 (frame, x, y, z), %d rows each' % (GU_ROWS, '==' if ok else '!=', len(rg)))
    if '--check' in sys.argv:
        bad = check_header(m4, rows4)
        print('\n== %s ==\n%s' % (HEADER, '\n'.join('MISMATCH ' + b for b in bad) or
                                  'matches the run: 5 orb tables, 3 frame tables, axis, GU table address'))
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
