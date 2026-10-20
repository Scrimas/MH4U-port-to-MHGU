"""mkelf3ds.py : wrap a decompressed 3DS code.bin into an ELF (text/ro/data at their load
addresses, from exheader.bin) so llvm-objdump can disassemble it.

  mkelf3ds.py EXEFS_DIR OUT.elf
Also writes EXEFS_DIR/mem.bin: a flat image where offset = vaddr - 0x100000.
"""
import struct, sys, os

src, dst = sys.argv[1], sys.argv[2]
code = open(os.path.join(src, 'code.bin'), 'rb').read()
exh = open(os.path.join(src, 'exheader.bin'), 'rb').read()
pg = lambda x: (x + 0xFFF) & ~0xFFF
segs = []
off = 0
for name, o, flags in (('.text', 0x10, 6), ('.rodata', 0x20, 2), ('.data', 0x30, 3)):
    addr, _, size = struct.unpack_from('<III', exh, o)
    segs.append((name, addr, size, off, flags))
    off += pg(size)
base = segs[0][1]
mem = bytearray(segs[2][1] + pg(segs[2][2]) - base)
for name, addr, size, fo, _ in segs:
    mem[addr - base:addr - base + size] = code[fo:fo + size]
open(os.path.join(src, 'mem.bin'), 'wb').write(mem)

shstr = b'\0' + b'\0'.join(n.encode() for n, *_ in segs) + b'\0.shstrtab\0'
DATA = 0x1000
shoff = (DATA + len(mem) + len(shstr) + 7) & ~7
out = bytearray(shoff + 40 * 5)
out[DATA:DATA + len(mem)] = mem
out[DATA + len(mem):DATA + len(mem) + len(shstr)] = shstr
eh = b'\x7fELF\x01\x01\x01' + b'\0' * 9 + struct.pack('<HHIIIIIHHHHHH', 2, 40, 1, base, 52, shoff,
                                                      0x05000000, 52, 32, 1, 40, 5, 4)
ph = struct.pack('<8I', 1, DATA, base, base, len(mem), len(mem), 7, 0x1000)
out[:52] = eh; out[52:84] = ph


def sh(name, typ, flags, addr, off, size):
    return struct.pack('<10I', name, typ, flags, addr, off, size, 0, 0, 4, 0)


shs = [b'\0' * 40]; ni = 1
for n, addr, size, _, flags in segs:
    shs.append(sh(ni, 1, flags, addr, DATA + addr - base, size)); ni += len(n) + 1
shs.append(sh(ni, 3, 0, 0, DATA + len(mem), len(shstr)))
out[shoff:shoff + 200] = b''.join(shs)
open(dst, 'wb').write(out)
for n, addr, size, *_ in segs: print(n, hex(addr), hex(size))
