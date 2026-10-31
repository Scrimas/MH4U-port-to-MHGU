"""build_assets.py : the RomFS / arc / gmd readers of MHGU_Editor tools/build_assets.py (GPL-3.0-or-later), vendored
for tools/gear4u.py, weapons4u.py and wsnd4u2gu.py. RomFS is romfs.py's (reads a Ryujinx RomFS folder too)."""
import struct, zlib
from romfs import RomFS  # noqa: F401


def arc(d):
    """{entry name (backslash path, no extension): bytes}"""
    assert d[:4] == b'ARC\0'
    n = struct.unpack_from('<H', d, 6)[0]; out = {}
    for i in range(n):
        e = d[0xC + i * 0x50:0xC + (i + 1) * 0x50]
        name = e[:64].split(b'\0')[0].decode()
        _, cs, ds, off = struct.unpack_from('<4I', e, 64)
        raw = d[off:off + cs]
        out[name] = zlib.decompress(raw) if (cs != ds & 0x1FFFFFFF or raw[:1] == b'\x78') else raw
    return out


def gmd(d):
    assert d[:4] == b'GMD\0'
    sc, ss = struct.unpack_from('<I', d, 0x18)[0], struct.unpack_from('<I', d, 0x20)[0]
    return [x.decode('utf-8', 'replace') for x in d[len(d) - ss:].split(b'\0')[:sc]]
