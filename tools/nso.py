"""nso.py : Switch NSO reader/writer (no external deps).

  nso.py info NSO
  nso.py unpack NSO OUT.bin          flat image (text|ro|data at their memory offsets, bss not included)
  nso.py elf2nso IN.elf OUT.nso      uncompressed NSO from a linked ELF (PT_LOAD segments R-X, R--, RW-)
"""
import hashlib, struct, sys


def lz4_block(src, size):
    out = bytearray(); i = 0
    while i < len(src):
        tok = src[i]; i += 1
        n = tok >> 4
        if n == 15:
            while True:
                b = src[i]; i += 1; n += b
                if b != 255: break
        out += src[i:i + n]; i += n
        if i >= len(src): break
        off = src[i] | src[i + 1] << 8; i += 2
        m = tok & 15
        if m == 15:
            while True:
                b = src[i]; i += 1; m += b
                if b != 255: break
        m += 4
        s = len(out) - off
        for k in range(m): out.append(out[s + k])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def parse(d):
    assert d[:4] == b'NSO0'
    flags = struct.unpack_from('<I', d, 0xC)[0]
    segs = []
    fsz = struct.unpack_from('<3I', d, 0x60)
    for i in range(3):
        fo, mo, sz, extra = struct.unpack_from('<4I', d, 0x10 + 0x10 * i)
        raw = d[fo:fo + fsz[i]]
        data = lz4_block(raw, sz) if flags >> i & 1 else raw[:sz]
        segs.append((mo, sz, data))
    bss = struct.unpack_from('<I', d, 0x3C)[0]
    return flags, segs, bss, d[0x40:0x60]


def flat(d):
    flags, segs, bss, bid = parse(d)
    end = segs[2][0] + segs[2][1]
    img = bytearray(end)
    for mo, sz, data in segs: img[mo:mo + sz] = data
    return bytes(img), segs, bss


def elf2nso(elf):
    assert elf[:4] == b'\x7fELF' and elf[4] == 1, 'need ELF32'
    phoff, = struct.unpack_from('<I', elf, 0x1C)
    phentsize, phnum = struct.unpack_from('<HH', elf, 0x2A)
    loads = []
    for i in range(phnum):
        p_type, off, vaddr, paddr, filesz, memsz, flags, align = struct.unpack_from('<8I', elf, phoff + i * phentsize)
        if p_type == 1: loads.append((vaddr, off, filesz, memsz, flags))
    loads.sort()
    assert len(loads) == 3 and [l[4] & 7 for l in loads] == [5, 4, 6], 'need R-X, R--, RW- PT_LOADs: %r' % loads
    hdr = bytearray(0x100)
    hdr[:4] = b'NSO0'
    body = bytearray(); offs = []
    segdata = []
    for vaddr, off, filesz, memsz, _ in loads:
        assert vaddr % 0x1000 == 0
        segdata.append(elf[off:off + filesz])
    bss = loads[2][3] - loads[2][2]
    pos = 0x100
    for i, (l, data) in enumerate(zip(loads, segdata)):
        struct.pack_into('<4I', hdr, 0x10 + 0x10 * i, pos, l[0], len(data), 0 if i < 2 else bss)
        struct.pack_into('<I', hdr, 0x60 + 4 * i, len(data))
        hdr[0xA0 + 0x20 * i:0xC0 + 0x20 * i] = hashlib.sha256(data).digest()
        body += data; pos += len(data)
    # module name offset/size left 0 (fields 0x1C / 0x2C); build id = hash of the image
    hdr[0x40:0x60] = hashlib.sha256(bytes(body)).digest()
    return bytes(hdr + body)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'info':
        d = open(sys.argv[2], 'rb').read()
        flags, segs, bss, bid = parse(d)
        print('flags', hex(flags), 'build id', bid.hex())
        for (mo, sz, _), n in zip(segs, ('text', 'ro', 'data')): print(n, hex(mo), hex(sz))
        print('bss', hex(bss), 'image end', hex(segs[2][0] + segs[2][1] + bss))
    elif cmd == 'unpack':
        img, segs, bss = flat(open(sys.argv[2], 'rb').read())
        open(sys.argv[3], 'wb').write(img)
    elif cmd == 'elf2nso':
        open(sys.argv[3], 'wb').write(elf2nso(open(sys.argv[2], 'rb').read()))
