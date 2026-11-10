"""test_modsave.py : module/modsave.c against its reference tools/modsave.py, without the game.

Compiles modsave.c with the module's flags (module/build.py CFLAGS), runs ms_split, ms_merge and ms_restore as ARM
code under unicorn on a synthetic slot and on every slot of the GU `system` files given, and checks that:
- C's file equals Python's, byte for byte, and so does the cleaned slot;
- merging C's file back gives the slot as it was (byte for byte, the link record aside), exactly;
- ms_restore puts the slot back as the merge found it;
- a file cut short, a wrong check word and a full journal are refused, the slot untouched.
Also refuses ARMv8 CRC instructions in modsave.c's code. Exit 1 on any failure.

  python3 tools/test_modsave.py [SYSTEM ...]
"""
import os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'module'))
import build  # noqa: E402  (module/build.py: CFLAGS)
import modsave as M  # noqa: E402
from test_save import run, emulator, STACK, RET  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

SLOT, FILE, QTAB, JRN, ASIDE, OUT = 0x20000000, 0x21000000, 0x21100000, 0x21200000, 0x21300000, 0x21400000
JCAP, ACAP = 0x10000, 0x2000


def build_elf(out):
    o = os.path.join(out, 'modsave.o')
    run('clang', *build.CFLAGS, '-I', os.path.join(ROOT, 'module'), '-c', os.path.join(ROOT, 'module', 'modsave.c'),
        '-o', o)
    if 'crc32' in run('llvm-objdump', '-d', o):
        sys.exit('FAIL modsave.c uses ARMv8 CRC instructions')
    elf = os.path.join(out, 'modsave.elf')
    run('ld.lld', '-static', '-e', '0', '--image-base=0x10000', '-o', elf, o)   # fails on any memcpy / memset call
    syms = {}
    for line in run('llvm-nm', elf).splitlines():
        p = line.split()
        if len(p) == 3: syms[p[2]] = int(p[0], 16)
    return open(elf, 'rb').read(), syms


def call(uc, addr, *args):
    """AAPCS: r0-r3, then the stack"""
    sp = STACK - 0x1000
    for i, a in enumerate(args[:4]):
        uc.reg_write((A.UC_ARM_REG_R0, A.UC_ARM_REG_R1, A.UC_ARM_REG_R2, A.UC_ARM_REG_R3)[i], a & 0xFFFFFFFF)
    if args[4:]:
        uc.mem_write(sp, b''.join(struct.pack('<I', a & 0xFFFFFFFF) for a in args[4:]))
    uc.reg_write(A.UC_ARM_REG_SP, sp)
    uc.reg_write(A.UC_ARM_REG_LR, RET)
    uc.emu_start(addr, RET, count=2_000_000_000)
    r = uc.reg_read(A.UC_ARM_REG_R0)
    return r - (1 << 32) if r & 0x80000000 else r


def main(paths):
    with tempfile.TemporaryDirectory() as t:
        img, syms = build_elf(t)
    uc, log = emulator(img)
    for base, size in ((SLOT, 0x120000 + 0x1000), (FILE, 0x10000), (QTAB, 0x10000), (JRN, JCAP), (ASIDE, ACAP),
                       (OUT, 0x1000)):
        uc.mem_map(base, (size + 0xFFF) & ~0xFFF)
    quests = M.quest_bits()
    uc.mem_write(QTAB, b''.join(struct.pack('<II', i, q) for i, q in quests))
    bad = []

    def one(name, slot):
        slot = bytes(slot)
        # Python
        ps = bytearray(slot)
        pf, pleft = M.split(ps, quests, 0xC0FFEE, 7)
        # C: compute only, then clean
        uc.mem_write(SLOT, slot)
        n0 = call(uc, syms['ms_split'], SLOT, QTAB, len(quests), 0xC0FFEE, 7, 0, 0, FILE, M.FILE_SIZE, 0, OUT)
        f0 = bytes(uc.mem_read(FILE, max(n0, 0)))
        if bytes(uc.mem_read(SLOT, M.SLOT_SIZE)) != slot: bad.append('%s: ms_split without clean changed the slot' % name)
        n = call(uc, syms['ms_split'], SLOT, QTAB, len(quests), 0xC0FFEE, 7, 0, 0, FILE, M.FILE_SIZE, 1, OUT)
        cf = bytes(uc.mem_read(FILE, max(n, 0)))
        cs = bytes(uc.mem_read(SLOT, M.SLOT_SIZE))
        if pf is None:
            if n != -1: bad.append('%s: Python refused the split, C returned %d' % (name, n))
            return
        if cf != pf:
            d = next((i for i in range(min(len(cf), len(pf))) if cf[i] != pf[i]), min(len(cf), len(pf)))
            bad.append('%s: C file (%d B) != Python file (%d B), first difference at %d' % (name, len(cf), len(pf), d))
            return
        if f0[:12] != pf[:12] or f0[16:24] != pf[16:24] or f0[32:] != pf[32:]:   # the hash and its check word differ
            bad.append('%s: the compute-only file differs from the cleaning one' % name)
        if cs != bytes(ps):
            d = next(i for i in range(M.SLOT_SIZE) if cs[i] != ps[i])
            bad.append('%s: C cleaned slot != Python cleaned slot at %#x' % (name, d))
            return
        # merge C's file back
        uc.mem_write(FILE, cf)
        r = call(uc, syms['ms_merge'], SLOT, FILE, len(cf), QTAB, len(quests), JRN, JCAP, OUT, ASIDE, ACAP, OUT + 4,
                 OUT + 0x100)
        jlen, alen = struct.unpack('<II', bytes(uc.mem_read(OUT, 8)))
        exact, placed, moved, kept, aside = struct.unpack('<5I', bytes(uc.mem_read(OUT + 0x100, 20)))
        ms = bytes(uc.mem_read(SLOT, M.SLOT_SIZE))
        lk = slice(M.RESERVED, M.RESERVED + M.LINK_N)
        if r != 0: bad.append('%s: ms_merge returned %d' % (name, r)); return
        if ms[:lk.start] + ms[lk.stop:] != slot[:lk.start] + slot[lk.stop:]:
            d = next(i for i in range(M.SLOT_SIZE) if ms[i] != slot[i] and not lk.start <= i < lk.stop)
            bad.append('%s: merge(split) differs at %#x' % (name, d))
        if not exact or aside or kept or moved:
            bad.append('%s: not exact: exact %d placed %d moved %d kept %d aside %d' % (name, exact, placed, moved,
                                                                                        kept, aside))
        call(uc, syms['ms_restore'], SLOT, JRN, jlen)
        if bytes(uc.mem_read(SLOT, M.SLOT_SIZE)) != cs: bad.append('%s: ms_restore did not give the clean slot' % name)
        # refusals: cut short, a wrong check word, a journal too small
        for what, f, jcap in (('cut short', cf[:-3], JCAP), ('check word', cf[:12] + b'\0\0\0\0' + cf[16:], JCAP),
                              ('small journal', cf, 64 if placed > 2 else 0)):
            if not jcap: continue
            uc.mem_write(SLOT, cs)
            uc.mem_write(FILE, f)
            r = call(uc, syms['ms_merge'], SLOT, FILE, len(f), QTAB, len(quests), JRN, jcap, OUT, ASIDE, ACAP,
                     OUT + 4, OUT + 0x100)
            if r == 0: bad.append('%s: %s merged' % (name, what))
            if bytes(uc.mem_read(SLOT, M.SLOT_SIZE)) != cs: bad.append('%s: %s changed the slot' % (name, what))
        print('ok %s: %d bytes, %d placed' % (name, len(cf), placed) if not [b for b in bad if b.startswith(name)]
              else 'FAIL %s' % name)

    one('synthetic', synthetic(quests))
    for p in paths:
        data = open(p, 'rb').read()
        for k, base in M.slots(data):
            one('%s slot %d' % (os.path.basename(p), k + 1), data[base:base + M.SLOT_SIZE])
    for b in bad: print('FAIL ' + b)
    if log: print('\n'.join(log[:20]))
    return 1 if bad else 0


def synthetic(quests):
    """one of each kind (tools/modsave.py test's slot, plus the worn weapon case with no vanilla weapon left)"""
    s = bytearray(M.SLOT_SIZE)
    M.setbits(s, M.BOX, 19 * 5, 12, 2980); M.setbits(s, M.BOX, 19 * 5 + 12, 7, 7)
    M.setbits(s, M.BOX, 19 * 6, 12, 100); M.setbits(s, M.BOX, 19 * 6 + 12, 7, 3)
    struct.pack_into('<HH', s, M.POUCH + 0, 0, 0)
    M.setbits(s, M.POUCH, 19 * 3, 12, 2891); M.setbits(s, M.POUCH, 19 * 3 + 12, 7, 1)
    struct.pack_into('<HH', s, M.LOADOUTS + M.LOADOUT_SZ * 2 + M.LOADOUT_ITEMS + 4 * 3, 2995, 2)
    struct.pack_into('<HH', s, M.EQBOX + M.ENTRY * 0, 7 + 2, 140)                    # an added hammer, worn
    struct.pack_into('<HHH3H', s, M.EQBOX + M.ENTRY * 1, 1, 10, 0, 2890, 300, 0)     # vanilla helm, an added jewel
    struct.pack_into('<HHH', s, M.EQBOX + M.ENTRY * 2, 2 | (3 << 10), 20, 1290)      # vanilla mail, an added look
    struct.pack_into('<HH', s, M.EQBOX + M.ENTRY * 3, 1, 1300)                       # an added helm, worn
    struct.pack_into('<7H', s, M.WORN, 0, 3, 2, M.NONE, M.NONE, M.NONE, M.NONE)
    for o in M.WEAPON_CLASS: s[o] = 2
    s[M.WORN_CACHE + 4:M.WORN_CACHE + 4 + M.ENTRY] = s[M.EQBOX:M.EQBOX + M.ENTRY]
    struct.pack_into('<HH', s, M.CARD_GEAR + 44, 1, 1301)
    struct.pack_into('<7H', s, M.MYSETS + M.MYSET * 4 + 0x30, 0, 3, M.NONE, M.NONE, M.NONE, M.NONE, M.NONE)
    struct.pack_into('<H', s, M.REGISTER[1][0] + 2, 2999)
    M.setbits(s, M.OBTAINED, 2980, 1, 1)
    s[M.RESERVED + 0x27C:M.RESERVED + 0x280] = b'MH4S'
    struct.pack_into('<H', s, M.TALLIES[0][0] + 2 * 106, 12)
    if quests:
        M.setbits(s, M.QUEST_MAPS[0], quests[0][0], 1, 1)
        struct.pack_into('<H', s, M.CARD_HISTORY + M.HISTORY * 2 + 6, quests[0][1])
    return s


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
