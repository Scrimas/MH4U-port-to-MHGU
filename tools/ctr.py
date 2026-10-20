"""ctr.py : read decrypted 3DS images (.3ds/.cci, .cia, .cxi) without external tools.

  ctr.py info  IMAGE
  ctr.py exefs IMAGE OUTDIR            (code.bin decompressed, plus exheader.bin)
  ctr.py ls    IMAGE [REGEX]           (RomFS listing)
  ctr.py x     IMAGE REGEX OUTDIR      (RomFS extract, paths kept)
"""
import os, re, struct, sys

MU = 0x200  # media unit


class Reader:
    def __init__(s, path, base=0):
        s.f = open(path, 'rb'); s.base = base
    def __call__(s, off, n):
        s.f.seek(s.base + off); return s.f.read(n)
    def sub(s, off):
        r = Reader.__new__(Reader); r.f = s.f; r.base = s.base + off; return r


def find_ncch(path):
    """NCCH partitions (content index -> Reader) of a CCI, CIA or bare NCCH."""
    rd = Reader(path)
    if rd(0x100, 4) == b'NCSD':
        out = {}
        for i in range(8):
            off, size = struct.unpack('<II', rd(0x120 + 8 * i, 8))
            if size: out[i] = rd.sub(off * MU)
        return out
    if rd(0x100, 4) == b'NCCH':
        return {0: rd}
    hsz, typ, ver, cert, tik, tmd, meta = struct.unpack('<IHHIIII', rd(0, 0x18))
    if hsz == 0x2020:  # CIA
        al = lambda x: (x + 63) & ~63
        coff = al(hsz) + al(cert) + al(tik) + al(tmd)
        toff = al(hsz) + al(cert) + al(tik)
        sigtype = struct.unpack('>I', rd(toff, 4))[0]
        sigsz = {0x10003: 0x23C, 0x10004: 0x13C, 0x10005: 0x7C}[sigtype]
        th = toff + 4 + sigsz
        ncont = struct.unpack('>H', rd(th + 0x9E, 2))[0]
        out = {}
        for i in range(ncont):
            cid, idx, ctype, csize = struct.unpack('>IHHQ', rd(th + 0x9C4 + 0x30 * i, 16))
            if ctype & 1:
                raise SystemExit('CIA content %d is still encrypted' % idx)
            if rd(coff + 0x100, 4) == b'NCCH': out[idx] = rd.sub(coff)
            coff += al(csize)
        return out
    raise SystemExit('unknown image format')


class NCCH:
    def __init__(s, rd):
        s.rd = rd
        h = rd(0, 0x200)
        assert h[0x100:0x104] == b'NCCH'
        s.flags = h[0x188:0x190]
        s.exh_size = struct.unpack_from('<I', h, 0x180)[0]
        s.exefs = struct.unpack_from('<II', h, 0x1A0)
        s.romfs = struct.unpack_from('<II', h, 0x1B0)
        # some decryptors leave the NoCrypto flag clear, so check the data itself
        if s.romfs[1] and rd(s.romfs[0] * MU, 4) != b'IVFC' or \
                s.exefs[1] and rd(s.exefs[0] * MU, 5) != b'.code':
            raise SystemExit('NCCH is encrypted')
        s.product = h[0x150:0x160].rstrip(b'\0').decode()
        s.title = struct.unpack_from('<Q', h, 0x118)[0]

    def exheader(s):
        return s.rd(0x200, 0x800) if s.exh_size else b''

    def exefs_files(s):
        off, size = s.exefs
        if not size: return {}
        hdr = s.rd(off * MU, 0x200)
        out = {}
        for i in range(10):
            name, o, n = struct.unpack_from('<8sII', hdr, 16 * i)
            name = name.rstrip(b'\0').decode()
            if name: out[name] = s.rd(off * MU + 0x200 + o, n)
        return out

    def romfs_reader(s):
        off, size = s.romfs
        if not size: return None
        return RomFS(s.rd.sub(off * MU))


def blz_decompress(c):
    """Backward LZ (code.bin) decompression, as in ctrtool."""
    top_bottom, extra = struct.unpack_from('<II', c, len(c) - 8)
    out = bytearray(len(c) + extra); out[:len(c)] = c
    o = len(out)
    i = len(c) - (top_bottom >> 24)
    stop = len(c) - (top_bottom & 0xFFFFFF)
    while i > stop:
        i -= 1; ctl = c[i]
        for _ in range(8):
            if i <= stop or o <= 0: break
            if ctl & 0x80:
                i -= 2
                seg = c[i] | c[i + 1] << 8
                n = (seg >> 12) + 3; d = (seg & 0xFFF) + 2
                for _ in range(n):
                    v = out[o + d]; o -= 1; out[o] = v
            else:
                i -= 1; o -= 1; out[o] = c[i]
            ctl = (ctl << 1) & 0xFF
    return bytes(out)


class RomFS:
    def __init__(s, rd):
        assert rd(0, 4) == b'IVFC', 'not an IVFC RomFS'
        master = struct.unpack('<I', rd(8, 4))[0]
        lg = struct.unpack('<I', rd(0x4C, 4))[0]
        bs = 1 << lg
        l3 = (0x60 + master + bs - 1) & ~(bs - 1)
        s.rd = rd.sub(l3)
        h = struct.unpack('<10I', s.rd(0, 40))
        (_, _, _, dmo, dms, _, _, fmo, fms, s.data) = h
        s.dm = s.rd(dmo, dms); s.fm = s.rd(fmo, fms)
        s.files = {}
        s._walk(0, '')

    def _walk(s, d, path):
        par, sib, child, fil, hnext, nl = struct.unpack_from('<6I', s.dm, d)
        name = s.dm[d + 24:d + 24 + nl].decode('utf-16le')
        p = path + '/' + name if d else ''
        f = fil
        while f != 0xFFFFFFFF:
            fpar, fsib, off, sz, fh, fnl = struct.unpack_from('<IIQQII', s.fm, f)
            fn = s.fm[f + 32:f + 32 + fnl].decode('utf-16le')
            s.files[p + '/' + fn] = (off, sz)
            f = fsib
        c = child
        while c != 0xFFFFFFFF:
            s._walk(c, p)
            c = struct.unpack_from('<I', s.dm, c + 4)[0]

    def read(s, name):
        off, sz = s.files[name]
        return s.rd(s.data + off, sz)


def main_ncch(path):
    parts = find_ncch(path)
    return NCCH(parts[min(parts)]), parts


if __name__ == '__main__':
    cmd, img = sys.argv[1], sys.argv[2]
    n, parts = main_ncch(img)
    if cmd == 'info':
        print('partitions', sorted(parts), 'product', n.product, 'title %016x' % n.title)
        print('exefs', n.exefs, 'romfs', n.romfs, 'exheader', hex(n.exh_size))
        exh = n.exheader()
        if exh:
            name = exh[:8].rstrip(b'\0').decode()
            text, ro, data = (struct.unpack_from('<III', exh, o) for o in (0x10, 0x20, 0x30))
            print('app', name, 'compressed code' if exh[0xD] & 1 else 'plain code')
            print('text addr %#x size %#x | ro addr %#x size %#x | data addr %#x size %#x | bss %#x'
                  % (text[0], text[2], ro[0], ro[2], data[0], data[2], struct.unpack_from('<I', exh, 0x3C)[0]))
        print('exefs files', {k: len(v) for k, v in n.exefs_files().items()})
    elif cmd == 'exefs':
        out = sys.argv[3]; os.makedirs(out, exist_ok=True)
        exh = n.exheader()
        open(os.path.join(out, 'exheader.bin'), 'wb').write(exh)
        for k, v in n.exefs_files().items():
            if k == '.code' and exh and exh[0xD] & 1: v = blz_decompress(v)
            open(os.path.join(out, 'code.bin' if k == '.code' else k + '.bin'), 'wb').write(v)
            print(k, len(v))
    elif cmd in ('ls', 'x'):
        r = n.romfs_reader()
        pat = re.compile(sys.argv[3] if len(sys.argv) > 3 else '')
        hits = sorted(k for k in r.files if pat.search(k))
        if cmd == 'ls':
            for k in hits: print(r.files[k][1], k)
        else:
            out = sys.argv[4]
            for k in hits:
                p = os.path.join(out, k.lstrip('/')); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(r.read(k))
            print(len(hits), 'files ->', out)
