"""arcpack.py : build MHGU-style ARC archives (version 0x11).

  arcpack.py unpack IN.arc OUTDIR          entries -> OUTDIR/<path>.<typehash>  (works for 4U v0x13 and GU v0x11)
  arcpack.py pack INDIR OUT.arc            files named <path>.<typehash> (as unpack writes them), sorted order kept
                                           from INDIR/_order.txt when present
  arcpack.py selftest [GU arc path]        repack a GU arc and check every entry decompresses identically

Container (both games): 'ARC\\0', u16 version, u16 count, u32 0, then count x 0x50 entries
  {char path[64] (backslashes, no extension), u32 type hash, u32 compressed size,
   u32 decompressed size | flags << 29, u32 offset}, then the zlib streams.
GU (0x11): flags = 2 on every entry, all entries zlib-compressed, data starts at the header size rounded up
           to 0x8000 (zero padding), entries stored contiguously in table order.
4U (0x13): flags = 1 (5 on a few), data right after the header (aligned to 0x20); not needed for output.
"""
import os, struct, sys, zlib

GU_VERSION = 0x11
GU_FLAGS = 2
HEADER_ALIGN = 0x8000


def read(d):
    magic, ver, n = struct.unpack_from('<4sHH', d, 0)
    assert magic == b'ARC\0', magic
    out = []
    for i in range(n):
        name, th, cs, ds, off = struct.unpack_from('<64s4I', d, 0xC + 0x50 * i)
        raw = d[off:off + cs]
        size = ds & 0x1FFFFFFF
        data = zlib.decompress(raw) if (cs != size or raw[:1] == b'\x78') else raw
        assert len(data) == size, (name, len(data), size)
        out.append((name.split(b'\0')[0].decode('ascii'), th, data))
    return ver, out


def build(entries, level=9):
    """entries: [(path, type_hash, data)] -> GU arc bytes."""
    n = len(entries)
    hdr = 0xC + 0x50 * n
    start = (hdr + HEADER_ALIGN - 1) // HEADER_ALIGN * HEADER_ALIGN
    table = bytearray(); blobs = bytearray(); off = start
    for path, th, data in entries:
        name = path.encode('ascii')
        assert len(name) < 64, path
        z = zlib.compress(data, level)
        table += struct.pack('<64s4I', name, th, len(z), len(data) | (GU_FLAGS << 29), off)
        blobs += z; off += len(z)
    out = struct.pack('<4sHHI', b'ARC\0', GU_VERSION, n, 0) + table
    return bytes(out) + b'\0' * (start - len(out)) + bytes(blobs)


def selftest(path='/nativeNX/arc/enemy/em001_00.arc'):
    import paths
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    d = RomFS(paths.GU_ROMFS).read(path)
    ver, ents = read(d)
    new = build(ents)
    ver2, ents2 = read(new)
    same = ents == ents2
    first = struct.unpack_from('<I', new, 0xC + 0x4C)[0]
    orig_first = struct.unpack_from('<I', d, 0xC + 0x4C)[0]
    print(path, 'entries', len(ents), 'identical contents', same, 'data start %#x (original %#x)' % (first, orig_first),
          'size %d (original %d)' % (len(new), len(d)))
    return same and first == orig_first


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'selftest':
        sys.exit(0 if selftest(*sys.argv[2:3]) else 1)
    elif cmd == 'unpack':
        ver, ents = read(open(sys.argv[2], 'rb').read())
        out = sys.argv[3]
        with open(os.path.join(out, '_order.txt') if os.makedirs(out, exist_ok=True) is None else '', 'w') as order:
            for path, th, data in ents:
                p = os.path.join(out, path.replace('\\', '/') + '.%08x' % th)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(data)
                order.write('%s.%08x\n' % (path.replace('\\', '/'), th))
        print('version %#x, %d entries -> %s' % (ver, len(ents), out))
    elif cmd == 'pack':
        root = sys.argv[2]
        op = os.path.join(root, '_order.txt')
        if os.path.exists(op):
            files = [l.strip() for l in open(op) if l.strip()]
        else:
            files = sorted(os.path.relpath(os.path.join(dp, f), root) for dp, _, fs in os.walk(root) for f in fs
                           if f != '_order.txt')
        ents = []
        for rel in files:
            base, th = rel.rsplit('.', 1)
            ents.append((base.replace('/', '\\'), int(th, 16), open(os.path.join(root, rel), 'rb').read()))
        open(sys.argv[3], 'wb').write(build(ents))
        print(len(ents), 'entries ->', sys.argv[3])
