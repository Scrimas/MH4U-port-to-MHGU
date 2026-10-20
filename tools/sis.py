"""sis.py : MH4U / MHGU stage area info "SIS" v6 (rStageAreaInfo, type 0x065375d5). Same format in both games.

  sis.py dump FILE...            print every record
  sis.py selftest DIR            parse + rewrite every *.sis / *.065375d5 under DIR, compare bytes

Layout (little-endian, packed):
  +00 'SIS\\0'  +04 u32 6  +08 f32 pos[3] (area reference point)  +14 u32 (uninitialised junk)
  then 4 sections {u32 count, count x record}; every record starts with u32 + f32 pos[3]:
    1 points  28 B: +00 f32 point id (ballistae numbered 1.0, 2.0 ... across the stage; 0 elsewhere),
                    +10 u16 kind (camp 0/1/2; 3 ballista, 5 Dragonator, 6 st008 cannon ...), +12 u16 ANGLE (65536 =
                    360 deg: GU 0x5027bc passes it to the st004 ballista as its facing), f32 w, f32 h
    2 exits   28 B: +10 u8 variant, u8 TARGET AREA, u16 junk, f32 radius, f32 height      (trigger zone)
    3 arrivals 20 B: +10 u8 variant, u8 SOURCE AREA (0xff = quest start / cart), u16 angle (4U 0x2efafc returns it
                    with the position)                                                    (player spawn points)
    4 spheres 24 B: +10 u32 0?, f32 radius-like values (GU only in this stage set; m19 has none)
Checked on 194 GU (base RomFS map_com) + 124 4U (m01..m21) files: all parse to the last byte.
"""
import struct, sys, os

SIZES = (28, 28, 20, 24)
NAMES = ('points', 'exits', 'arrivals', 'spheres')


def parse(d):
    assert d[:4] == b'SIS\0' and struct.unpack_from('<I', d, 4)[0] == 6, d[:8]
    s = dict(head=d[8:0x18], sec=[])
    o = 0x18
    for sz in SIZES:
        n = struct.unpack_from('<I', d, o)[0]; o += 4
        s['sec'].append([bytearray(d[o + sz * i:o + sz * (i + 1)]) for i in range(n)])
        o += sz * n
    assert o == len(d), ('trailing', o, len(d))
    return s


def write(s):
    out = bytearray(b'SIS\0' + struct.pack('<I', 6) + s['head'])
    for recs in s['sec']:
        out += struct.pack('<I', len(recs)) + b''.join(bytes(r) for r in recs)
    return bytes(out)


def pos(r):
    return struct.unpack_from('<3f', r, 4)


def remap_areas(s, amap, drop_missing=True):
    """rewrite target (exits) / source (arrivals) area bytes with amap {old: new}; records whose area is not in
    amap (and not 0xff) are dropped when drop_missing, so no exit leads to an area the alias does not have."""
    for k in (1, 2):
        keep = []
        for r in s['sec'][k]:
            a = r[17]
            if a == 0xFF or a in amap:
                if a != 0xFF: r[17] = amap[a]
                keep.append(r)
            elif not drop_missing:
                keep.append(r)
        s['sec'][k] = keep
    return s


def dump(s):
    print(' head pos (%.1f %.1f %.1f)' % struct.unpack_from('<3f', s['head'], 0))
    for nm, recs in zip(NAMES, s['sec']):
        for r in recs:
            x = pos(r)
            if nm == 'points':
                print('  %-8s (%8.1f %7.1f %8.1f) kind %d  w %.0f h %.0f' % (nm, *x, struct.unpack_from('<H', r, 16)[0],
                                                                       *struct.unpack_from('<2f', r, 20)))
            elif nm == 'exits':
                print('  %-8s (%8.1f %7.1f %8.1f) var %d -> area %d  r %.0f h %.0f' % (nm, *x, r[16], r[17],
                                                                                  *struct.unpack_from('<2f', r, 20)))
            elif nm == 'arrivals':
                print('  %-8s (%8.1f %7.1f %8.1f) var %d <- area %s' % (nm, *x, r[16], 'start' if r[17] == 0xFF else r[17]))
            else:
                print('  %-8s (%8.1f %7.1f %8.1f) %s' % (nm, *x, bytes(r[16:]).hex()))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'dump':
        for f in sys.argv[2:]:
            print(f); dump(parse(open(f, 'rb').read()))
    elif cmd == 'selftest':
        n = bad = 0
        for dp, _, fs in os.walk(sys.argv[2]):
            for f in fs:
                if f.endswith('.sis') or f.endswith('.065375d5'):
                    d = open(os.path.join(dp, f), 'rb').read(); n += 1
                    if write(parse(d)) != d: bad += 1; print('MISMATCH', f)
        print('SIS files %d, identical %d' % (n, n - bad))
    else:
        raise SystemExit(__doc__)
