import struct, zlib
def arc_entries(d):
    assert d[:4] == b'ARC\0'
    ver, n = struct.unpack('<HH', d[4:8])
    out = []
    for i in range(n):
        e = d[0xC + i*0x50: 0xC + (i+1)*0x50]
        name = e[:64].split(b'\0')[0].decode()
        th, cs, ds, off = struct.unpack('<4I', e[64:80])
        out.append((name, th, cs, ds & 0x1FFFFFFF, off))
    return out
def arc_read(d, ent):
    name, th, cs, ds, off = ent
    raw = d[off:off+cs]
    return zlib.decompress(raw) if cs != ds or raw[:1] == b'\x78' else raw
