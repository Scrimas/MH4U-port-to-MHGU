"""efldump.py : print the decoded fields of MHGU EFL (rEffectList 0x20120306) entries by name.

  efldump.py FILE.efl [ENTRY ...]              a loose EFL (e.g. an arcpack unpack <path>.6d5ae854)
  efldump.py ARC EFLPATH [ENTRY ...]           an EFL inside a GU arc (ARC relative to the GU romfs or absolute;
                                               EFLPATH with backslashes, e.g. effect\\cm\\cm090_000)
  --raw   also print every non-zero unknown word

Layout and evidence: weapons/magnet_spike/notes/gu-efl-units.md (C = code, S = corpus, G = guess).
An EFL entry = 4 block words ((offset - 0x30) << 8 | type byte):
  w0 element block (0xc0), w1 unit block (class by type byte, factory 0x9bdc68), w2 emit block (16 / 32 B),
  w3 move block (low nibble = kind, bit 4 = 'Lite' class variant).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

UNIT_CLASS = {0: 'Billboard', 1: 'Polyline', 2: 'Polygon', 3: 'Texline', 4: 'Line', 5: 'Model', 6: 'PrimModel',
              7: 'LensFlare', 8: 'MassBillboard', 9: 'Filter', 10: 'Light', 11: 'Hit', 12: 'Polyline',
              13: 'Texline', 14: 'Line', 15: 'PolygonStrip', 16: 'Custom', 17: 'ClothPolygon', 18: 'Adhesion',
              19: 'BillboardStrip', 20: 'SizeBillboard', 21: 'LightShaft', 22: 'Point', 23: 'AxisPolygon',
              24: 'Force', 25: 'Node', 26: 'Trail'}
LITE = {0: 'LiteBillboard', 1: 'LitePolyline', 2: 'LitePolygon', 25: 'NodeInfinite'}

# (offset, format, name); format: I u32, H u16, h s16, B u8, f f32, x hex u32, c colour (bytes R G B A),
# 'r' f32 pair (value, random range), 's<n>' string of n bytes
ELEMENT = [(0x00, 'x', 'w0 (G: element id / flags)'), (0x04, 'x', 'w1'), (0x08, 'x', 'flags (bit 27 GU only)'),
           (0x0c, 'x', 'w3 (byte 3 = 1)'), (0x10, 'x', 'joint/ref [8] (-1 = none, S)'),
           (0x30, 'x', 'w0x30 (const 0x66; bits 0-3 / 4-7 -> generator +0xe8, C 0xa59268)'),
           (0x40, 'r', 'time scale / speed + random (C -> gen +0xf8)'),
           (0x48, 'I', 'w0x48 (1..)'), (0x4c, 'I', 'w0x4c'), (0x50, 'I', 'w0x50 (1)'), (0x54, 'x', 'w0x54'),
           (0x60, 'r', 'pair 0x60 (G)'), (0x68, 'r', 'pair 0x68 (G)'), (0x70, 'r', 'pair 0x70 (G)'),
           (0x78, 'x', 'bytes 0 / 1 / 3 -> generator +0xe4 / +0xe8 (C 0xa59268)'),
           (0x80, 'r', 'pair 0x80 (G)'), (0x88, 'r', 'scale x + random (C -> gen +0x160)'),
           (0x90, 'r', 'scale y + random (C -> gen +0x164)'), (0x98, 'r', 'scale z + random (C -> gen +0x168)'),
           (0xa0, 'H', 'u16 -> generator +0xe4 lo16 (C)'), (0xa2, 'H', 'transform mode (bits 0-3, C 0xaec900)'),
           (0xb0, 'f', 'f32 (non-zero -> gen +0x194 bit 24)'), (0xb4, 'x', 'u16 random seed flag / hi16'),
           (0xbe, 'H', 'offset of transform sub-block (C 0xaec900)')]
EMIT = [(0x00, 'x', 'u16 pair: wait / interval (S, G)'), (0x04, 'x', 'u16 pair: count (lo) / hi (S, G)'),
        (0x08, 'x', 'u16 pair: emitter life frames (S, G)'), (0x0c, 'I', 'loop flag (S, G)')]
MOVE2 = [(0x00, 'x', 'flags (bit 4 -> gen +0xdc bit 25, C)'),
         (0x04, 'x', 'mode word (bits 8-11 / 12-15 -> gen +0xec nibbles, C)'),
         (0x10, 'r', 'direction angle X + range (rad, S)'), (0x18, 'r', 'direction angle Y + range (rad, S)'),
         (0x20, 'r', 'direction angle Z + range (rad, S)'), (0x28, 'r', 'speed + range (S)'),
         (0x30, 'r', 'pair 0x30 (accel / gravity?, G)'), (0x40, 'r', 'velocity damping per frame + range (S)'),
         (0x48, 'I', 'w0x48 (G)')]
UNIT = [(0x00, 'x', 'byte0 kind, byte1 -> 0xafccc8, byte3 blend index (C)'),
        (0x04, 'x', 'flags (-> gen +0x90, C 0xaec900; bit 14 S)'), (0x08, 'x', '-> gen +0xa0 (C)'),
        (0x0c, 'x', 'w0x0c (s32, S)'), (0x10, 'f', 'f32 0x10 (S)'),
        (0x14, 'x', 'bytes 2 / 3 GU only (S)'),
        (0x18, 'x', 'bits 0-3 colour mode, 4-7 draw variant, 16 / 17 / 18 / 19 flags (C)'),
        (0x1c, 'f', 'f32 0x1c (0.9..1, G: per-frame factor)'), (0x20, 'f', 'f32 0x20 (-> gen +0x188, C)'),
        (0x28, 'r', 'size + random (S, G)'), (0x30, 'r', 'size growth + random (S, G)'),
        (0x38, 'H', 'curve offset 0x38'), (0x3a, 'H', 'curve offset 0x3a'), (0x3c, 'H', 'curve offset 0x3c'),
        (0x3e, 'H', 'curve offset 0x3e (C slot 23)'), (0x40, 'B', 'colour random mode (C 0xa6be40)'),
        (0x41, 'B', 'UV anim curve mode (bit 0, C 0xa69d00)'),
        (0x42, 'H', 'colour/alpha curve offset (C)'), (0x44, 'H', 'UV anim frame curve offset (C)'),
        (0x46, 'H', 'curve offset 0x46'), (0x48, 'c', 'colour A (C)'), (0x4c, 'c', 'colour B (C)'),
        (0x50, 'x', 'UV flags lo16 (0x10 / 0x400 / 0x800 random flips, C), byte 2 EAN entry, byte 3 its random'),
        (0x54, 'x', 'UV start frame lo16 + random hi16 (C)'), (0x58, 'f', 'UV anim speed (C)'),
        (0x5c, 'f', 'UV anim frame clamp (C)'), (0x60, 'I', 'pivot x (S)'), (0x64, 'I', 'pivot y (S)'),
        (0x6c, 'f', 'f32 0x6c (const 5, S)'), (0x70, 's192', 'texture path'), (0x130, 's64', 'EAN path'),
        (0x170, 'r', 'rotation + random (rad, C slot 23)'), (0x178, 'r', 'angular speed + random (rad / frame, C)'),
        (0x180, 'r', 'pair 0x180 (S)'), (0x190, 'f', 'angular speed damping (C 0xa7de94)'),
        (0x194, 'I', 'random sign of angular speed (C slot 23)'), (0x198, 'I', 'rotation curve offset (C)')]


def load(argv):
    a = argv[0]
    if a.endswith('.arc') and len(argv) > 1:
        import arcpack
        p = a
        if not os.path.exists(p):
            import paths
            p = os.path.join(paths.GU_ROMFS, a.lstrip('/'))
        for name, th, d in arcpack.read(open(p, 'rb').read())[1]:
            if th == 0x6D5AE854 and name.lower() == argv[1].lower():
                return d, argv[2:]
        sys.exit('no EFL %s in %s' % (argv[1], p))
    return open(a, 'rb').read(), argv[1:]


def blocks(d):
    magic, ver, size, fps, n, n2 = struct.unpack_from('<4sIIfHH', d, 0)
    assert magic == b'EFL\0', magic
    starts = {len(d)}
    ents = [struct.unpack_from('<4I', d, 0x30 + 16 * i) for i in range(n)]
    for t in struct.unpack_from('<%dI' % n2, d, 0x30 + 16 * n):
        if t:
            starts.add(t + 0x30)
    for e in ents:
        for w in e:
            if w >> 8:
                starts.add((w >> 8) + 0x30)
    st = sorted(starts)
    size_of = {st[i]: st[i + 1] - st[i] for i in range(len(st) - 1)}
    return dict(ver=ver, fps=fps, n=n, n2=n2, ents=ents, size=size_of)


def fmt(b, o, f):
    if o + 4 > len(b) and f not in ('H', 'h', 'B'):
        return '-'
    if f == 'x':
        return '%08x' % struct.unpack_from('<I', b, o)[0]
    if f == 'I':
        return str(struct.unpack_from('<i', b, o)[0])
    if f in ('H', 'h', 'B'):
        return str(struct.unpack_from('<' + f, b, o)[0])
    if f == 'f':
        return '%.6g' % struct.unpack_from('<f', b, o)[0]
    if f == 'r':
        v, r = struct.unpack_from('<2f', b, o)
        return '%.6g + rand * %.6g' % (v, r)
    if f == 'c':
        return 'RGBA %d %d %d %d' % tuple(b[o:o + 4])
    if f.startswith('s'):
        return repr(b[o:o + int(f[1:])].split(b'\0')[0].decode('ascii', 'replace'))
    raise ValueError(f)


def show(title, b, table, raw):
    print('  %s (%#x B)' % (title, len(b)))
    seen = set()
    for o, f, name in table:
        print('    +%03x %-34s %s' % (o, name, fmt(b, o, f)))
        n = int(f[1:]) if f.startswith('s') else 8 if f == 'r' else 2 if f in 'Hh' else 1 if f == 'B' else 4
        seen.update(range(o, o + n))
    if raw:
        for o in range(0, len(b) - 3, 4):
            if o not in seen and struct.unpack_from('<I', b, o)[0]:
                print('    +%03x (unknown)                         %08x' % (o, struct.unpack_from('<I', b, o)[0]))


def curves(b):
    """curve tables {u32 count | 2 << 8 | prop << 24, count x {u32 frame, u32 a, u32 b}} at the unit's offsets."""
    offs = sorted({struct.unpack_from('<H', b, o)[0] for o in range(0x38, 0x48, 2)} - {0})
    for a in offs:
        if a + 4 > len(b):
            continue
        h = struct.unpack_from('<I', b, a)[0]
        k = h & 0xFF
        keys = [struct.unpack_from('<3I', b, a + 4 + 12 * i) for i in range(k) if a + 16 + 12 * i <= len(b)]
        print('    curve @+%03x prop %#x mode %d keys %d: %s' % (a, h >> 24, (h >> 8) & 0xFF, k,
              ' '.join('[%d %08x %08x]' % kk for kk in keys)))


def main(argv):
    raw = '--raw' in argv
    argv = [a for a in argv if a != '--raw']
    if not argv:
        sys.exit(__doc__)
    d, rest = load(argv)
    E = blocks(d)
    print('EFL ver %#x fps %g entries %d tail %d' % (E['ver'], E['fps'], E['n'], E['n2']))
    want = [int(x, 0) for x in rest] or range(E['n'])
    for i in want:
        e = E['ents'][i]
        blk = []
        for w in e:
            o = (w >> 8) + 0x30 if w >> 8 else None
            blk.append((w & 0xFF, d[o:o + E['size'][o]] if o else b''))
        ut = blk[1][0]
        lite = blk[3][0] & 0xF0 != 0
        cls = (LITE.get(ut) if lite else None) or UNIT_CLASS.get(ut, '?')
        print('entry %d: element type %d, unit type %d = cParticleGenerator%s, emit type %#x, move type %#x'
              % (i, blk[0][0], ut, cls, blk[2][0], blk[3][0]))
        if blk[0][1]:
            show('element', blk[0][1], ELEMENT, raw)
        if blk[2][1]:
            show('emit', blk[2][1], EMIT, raw)
        if blk[3][1]:
            show('move kind %d' % (blk[3][0] & 0xF), blk[3][1], MOVE2 if blk[3][0] & 0xF == 2 else [], raw)
        if blk[1][1]:
            show('unit', blk[1][1], UNIT if ut in (0, 19, 20) else UNIT[:12], raw)
            curves(blk[1][1])


if __name__ == '__main__':
    main(sys.argv[1:])
