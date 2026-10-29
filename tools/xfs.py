"""xfs.py : reader for MT XFS v0x10 data files (MHGU; e.g. the per-monster area files area_link / area_eat /
area_select / area_patrol, manifest fields 40..44). Layout read off GU em067_00 / em007_00 (2026-10-21, Tigerstripe's
area-data fix; every area file of the 94 GU monster arcs parses to its exact end):

  0x00 'XFS\\0', u16 0x10, u16 minor, u32 object count, u32 0, u32 class count, u32 definition size
  0x18 class table: class count x u32 offset (from 0x18) -> class {u32 DTI hash, u32 field count,
       fields of 0x28 bytes {u32 name offset (from 0x18), u8 type, u8 attribute, u16 size, ...}}
  0x18 + definition size: the root object; object = {u16 tag (class << 1 | 1, 0 = null), u16 serial (depth-first
       object number), u32 size (4 + body bytes)}, then per field u32 count and count values: types 1 (class) /
       2 (class ref) = nested objects, 128 (resource) = u8 kind (0 = none, GU uses 2) + class name + path (C
       strings; the value is (class name, path, kind) or None), others = size-byte LE ints (GU stage cameras
       m26a00d-cam: checked byte-exact; player command tables plcmd_wNN_<style>: 2026-10-29)

  defs(d) -> (object count, [(hash, [(name, type, attribute, size)])], data offset)
  parse(d) -> root object: {'_class': hash, field: value} (a field with count != 1 holds a list)
  walk(obj) -> every nested object, depth first (records with a field, e.g. mMapNo: [o for o in walk(r) if 'mMapNo' in o])
  build(d, root) -> XFS bytes of root (parse() layout) with the header and class table of d
"""
import struct


def defs(d):
    assert d[:4] == b'XFS\0' and struct.unpack_from('<H', d, 4)[0] == 0x10, 'not an XFS v0x10'
    nobj, _, ncls, dsize = struct.unpack_from('<IIII', d, 8)
    cls = []
    for o in struct.unpack_from('<%dI' % ncls, d, 0x18):
        b = 0x18 + o
        h, nf = struct.unpack_from('<II', d, b)
        fields = []
        for i in range(nf):
            no, ty, at, sz = struct.unpack_from('<IBBH', d, b + 8 + 0x28 * i)
            fields.append((d[0x18 + no:d.index(b'\0', 0x18 + no)].decode(), ty, at, sz))
        cls.append((h, fields))
    return nobj, cls, 0x18 + dsize


def parse(d):
    _, cls, data = defs(d)

    def obj(p):
        tag = struct.unpack_from('<H', d, p)[0]
        if tag == 0:
            return p + 8, None
        h, fields = cls[tag >> 1]
        rec, q = {'_class': h}, p + 8
        for name, ty, at, sz in fields:
            n = struct.unpack_from('<I', d, q)[0]
            q += 4
            vals = []
            for _ in range(n):
                if ty in (1, 2):
                    q, v = obj(q)
                elif ty == 128:
                    v, q = None, q + 1
                    if d[q - 1]:
                        e = d.index(b'\0', q)
                        f = d.index(b'\0', e + 1)
                        v, q = (d[q:e].decode(), d[e + 1:f].decode(), d[q - 1]), f + 1
                else:
                    v = int.from_bytes(d[q:q + sz], 'little')
                    q += sz
                vals.append(v)
            rec[name] = vals[0] if n == 1 else vals
        return q, rec

    end, root = obj(data)
    assert end == len(d), 'XFS data does not end where the file does'
    return root


def walk(o):
    if isinstance(o, dict):
        yield o
        for k, v in o.items():
            if k != '_class':
                yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def build(d, root):
    _, cls, data = defs(d)
    index = {h: i for i, (h, _) in enumerate(cls)}
    out = bytearray()
    serial = [0]

    def obj(o):
        if o is None:
            out.extend(b'\0' * 8)
            return
        ci = index[o['_class']]
        start = len(out)
        out.extend(struct.pack('<HHI', ci << 1 | 1, serial[0], 0))
        serial[0] += 1
        for name, ty, at, sz in cls[ci][1]:
            vals = o[name] if isinstance(o[name], list) else [o[name]]
            out.extend(struct.pack('<I', len(vals)))
            for v in vals:
                if ty in (1, 2):
                    obj(v)
                elif ty == 128:
                    out.extend(b'\0' if v is None else bytes([v[2]]) + v[0].encode() + b'\0' + v[1].encode() + b'\0')
                else:
                    out.extend(int(v).to_bytes(sz, 'little'))
        struct.pack_into('<I', out, start + 4, len(out) - start - 4)

    obj(root)
    head = bytearray(d[:data])
    struct.pack_into('<I', head, 8, serial[0])
    return bytes(head + out)
