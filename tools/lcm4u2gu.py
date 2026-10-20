"""lcm4u2gu.py : MH4U camera list (rCameraList 'LCM', type 0x39c52040, v4) -> MHGU (v5).

Format (both): 'LCM\\0', u16 version (4U 4, GU 5), u16 1, then 256 u32 record offsets (0 = no camera id), records,
then data (32-byte track headers and key blocks). A 4U record is 0x9c bytes; a GU record is the same record behind
16 zero bytes (0xac). Evidence (static, corpus): every one of the 689 records of the 67 GU monster LCMs has a zero
16-byte prefix; Rathian's shared ids 0/1/2/4/5/8: all non-offset words of the GU record = the 4U record shifted by
16 bytes, the referenced data blocks start byte-identical. Offset fields (file offsets into the data area, 0 = none),
relative to the 4U record: +40, +60, +76, +96, +112, +132, +152 (over the 87 4U LCMs these are the only words that
point past the records; +36 / +72 / +108 / +140 are sizes). Conversion: version 5, records re-laid with the prefix,
the data area copied verbatim and every offset field shifted by the record growth (16 * records).

  lcm4u2gu.py IN.lcm OUT.lcm
"""
import struct, sys

REC4, REC5, PREFIX = 0x9c, 0xac, 16
OFFSET_FIELDS = (40, 60, 76, 96, 112, 132, 152)


def convert(d):
    assert d[:4] == b'LCM\0', 'not an LCM'
    ver = struct.unpack_from('<H', d, 4)[0]
    if ver == 5:
        return bytes(d)
    assert ver == 4, 'LCM version %d' % ver
    offs = list(struct.unpack_from('<256I', d, 8))
    ids = [i for i in range(256) if offs[i]]
    if not ids:
        return d[:4] + struct.pack('<H', 5) + d[6:]
    first = min(offs[i] for i in ids)
    order = sorted(ids, key=lambda i: offs[i])
    rec_end = max(offs[i] for i in ids) + REC4
    for a, b in zip(order, order[1:]):
        assert offs[b] - offs[a] == REC4, 'records not contiguous'
    assert first == 8 + 1024, 'records do not follow the table'
    shift = PREFIX * len(ids)
    out = bytearray(d[:8] + bytes(1024))
    struct.pack_into('<H', out, 4, 5)
    for i in order:
        r = bytearray(d[offs[i]:offs[i] + REC4])
        for f in OFFSET_FIELDS:
            v = struct.unpack_from('<I', r, f)[0]
            if v:
                assert rec_end <= v < len(d), 'offset field +%d = %#x outside the data area' % (f, v)
                struct.pack_into('<I', r, f, v + shift)
        struct.pack_into('<I', out, 8 + 4 * i, len(out))
        out += bytes(PREFIX) + r
    assert len(out) == rec_end + shift
    out += d[rec_end:]
    return bytes(out)


if __name__ == '__main__':
    src = open(sys.argv[1], 'rb').read()
    open(sys.argv[2], 'wb').write(convert(src))
