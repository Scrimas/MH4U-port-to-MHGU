"""test_save.py : test module/save.c (the mod's own save store and the per-quest slot leases) without the game.

Compiles module/save.c and module/util.c with the module's flags (module/build.py CFLAGS) together with the harness
tools/test_save.c, links them and runs each test function as ARM code under unicorn (requirements.txt), on a fake
character whose every byte is checked. Then reads the store test_lessee leaves and checks it on its own (header,
FNV-1a check word, the record). Also refuses ARMv8 CRC instructions in save.c's code. Exit 1 on any failure.

  python3 tools/test_save.py
"""
import os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'module'))
import build  # noqa: E402  (module/build.py: CFLAGS)
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_INTR  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

TESTS = ('test_fixed', 'test_lessee', 'test_takeback', 'test_conflict', 'test_two', 'test_foreign', 'test_damaged',
         'test_full', 'test_cap', 'test_nochar', 'test_loaded', 'test_size')
STACK, RET = 0x7F000000, 0x7FFF0000
STORE_OFF = 0x3900


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode or r.stderr.strip():
        sys.exit('FAILED: %s\n%s%s' % (' '.join(a), r.stdout, r.stderr))
    return r.stdout


def build_elf(out):
    with open(os.path.join(out, 'alloc.h'), 'w', encoding='utf-8') as f:
        f.write('#pragma once\n#define PORT_MONSTER_COUNT 10u\n')     # test_save.c port_monsters[]
    objs = []
    for src in (os.path.join(ROOT, 'module', 'save.c'), os.path.join(ROOT, 'module', 'util.c'),
                os.path.join(HERE, 'test_save.c')):
        o = os.path.join(out, os.path.basename(src) + '.o')
        run('clang', *build.CFLAGS, '-I', out, '-I', os.path.join(ROOT, 'module'), '-c', src, '-o', o)
        objs.append(o)
    dis = run('llvm-objdump', '-d', objs[0])
    if 'crc32' in dis:
        sys.exit('FAIL save.c uses ARMv8 CRC instructions')
    elf = os.path.join(out, 'test_save.elf')
    run('ld.lld', '-static', '-e', '0', '--image-base=0x10000', '-o', elf, *objs)
    syms = {}
    for line in run('llvm-nm', elf).splitlines():
        p = line.split()
        if len(p) == 3: syms[p[2]] = int(p[0], 16)
    return open(elf, 'rb').read(), syms


def emulator(img):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
    phoff, phentsize, phnum = struct.unpack_from('<I', img, 0x1C)[0], *struct.unpack_from('<HH', img, 0x2A)
    for i in range(phnum):
        typ, off, vaddr, _, filesz, memsz = struct.unpack_from('<6I', img, phoff + i * phentsize)
        if typ != 1 or not memsz: continue                            # PT_LOAD
        lo, hi = vaddr & ~0xFFF, (vaddr + memsz + 0xFFF) & ~0xFFF
        try:
            uc.mem_map(lo, hi - lo)
        except UcError:                                               # shares a page with the segment before
            for page in range(lo, hi, 0x1000):
                try: uc.mem_map(page, 0x1000)
                except UcError: pass
        uc.mem_write(vaddr, img[off:off + filesz])
    uc.mem_map(STACK - 0x100000, 0x100000)
    uc.mem_map(RET, 0x1000)
    uc.reg_write(A.UC_ARM_REG_C1_C0_2, uc.reg_read(A.UC_ARM_REG_C1_C0_2) | (0xF << 20))   # CPACR: VFP / NEON
    uc.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)
    log = []

    def on_intr(uc, intno, _):
        if intno == 2:                                                # svc #0x27: logf -> OutputDebugString
            p, n = uc.reg_read(A.UC_ARM_REG_R0), uc.reg_read(A.UC_ARM_REG_R1)
            log.append(bytes(uc.mem_read(p, n)).decode('utf-8', 'replace'))
    uc.hook_add(UC_HOOK_INTR, on_intr)
    return uc, log


def call(uc, addr):
    uc.reg_write(A.UC_ARM_REG_SP, STACK - 0x100)
    uc.reg_write(A.UC_ARM_REG_LR, RET)
    uc.emu_start(addr, RET, count=50_000_000)
    return uc.reg_read(A.UC_ARM_REG_R0)


def fnv(h, data):
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def check_store(b):
    """the store test_lessee leaves: one record of the test lessee (em 0x65)"""
    bad = []
    magic, version, n, word, zero = struct.unpack_from('<IHHII', b, 0)
    if (magic, version, n, zero) != (0x5334484D, 1, 1, 0):
        bad.append('header %x %d %d %d' % (magic, version, n, zero))
    if word != fnv(fnv(2166136261, b[4:8]), b[16:16 + 12 * n]):
        bad.append('check word %x' % word)
    rec = struct.unpack_from('<6H', b, 16)
    if rec != (0x65, 4, 1, 1100, 1300, 0):
        bad.append('record %s, expected em 0x65, 4 hunts, 1 capture, smallest 1100, largest 1300' % (rec,))
    if any(b[16 + 12 * n:]):
        bad.append('bytes after the records are not zero')
    return bad


def main():
    with tempfile.TemporaryDirectory() as out:
        img, syms = build_elf(out)
    fails = 0
    for t in TESTS:
        uc, log = emulator(img)
        n = call(uc, syms[t])
        extra = check_store(bytes(uc.mem_read(syms['g_user'] + STORE_OFF, 0x43F8 - STORE_OFF))) \
            if t == 'test_lessee' else []
        for line in log:
            if line.startswith('FAIL'): print('  ' + line)
        for e in extra: print('  FAIL store bytes: ' + e)
        print('%-14s %s' % (t, 'ok' if not n and not extra else '%d failed' % (n + len(extra))))
        fails += n + len(extra)
        if os.environ.get('TEST_SAVE_LOG'):
            print('\n'.join('    ' + l for l in log if not l.startswith('FAIL')))
    print('all ok' if not fails else '%d check(s) failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
