"""sdl.py : MH4U (v0x15) / MHGU (v0x16) scheduler "SDL" (rScheduler, type 0x4c0db839): reader, writer, 4U -> GU.

  sdl.py dump FILE...              print objects / tracks / keys (either game)
  sdl.py selftest DIR [DIR4U]      parse + re-layout every *.4c0db839 under DIR (GU) / DIR4U (4U), compare bytes
  sdl.py conv IN_4U OUT_GU         convert one 4U scheduler to GU

Layout (little-endian; offsets are absolute file offsets):
  +00 'SDL\\0'  +04 u16 version (4U 0x15, GU 0x16)  +06 u16 entry count n  +08 u32 0xe2316427  +0C u32 frame count
  +10 u32 0  +14 u32 string-table offset
  +18 n entries: 4U 24 B {u32 t, u32 parent, u32 name, u32 x, u32 timeOff, u32 valOff}
                 GU 32 B {u32 t, u32 parent, u32 name, u32 x, u32 e1, u32 e2, u32 timeOff, u32 valOff}
      t = kind (byte 0) | property type (byte 1) << 8 | key count << 16; name = offset into the string table.
      kind 1 root, 2 object (x = class hash, e.g. uStageSet 0x2516a76b), 3 controller (x = class hash,
      sSoundControl 0x10163337), 4 section root, 5 array / array element (x = element index); others are tracks.
  data: per track with keys, in entry order: key times (u32 each: frame | interpolation << 24) at the running
      offset, then the values at the next 16-byte boundary; the next block starts at the next 4-byte boundary.
  strings: names, then resource references {u32 resource type hash, path\\0} (resource-track values point here).
Track kinds (same value encodings in both games, renumbered: GU inserted kinds 7 and 10):
  4U  6 int   7 vec4  8 f32  9 bool(1 B)  0xa classref (entry index)  0xb resource  0xc u32  0xd event  0xe curve(64 B)
  GU  6       8       9      0xb          0xc                         0xd          0xe      0xf        0x10
Checked: every GU (709) and 4U (703) stage scheduler of the base RomFS re-lays out byte for byte (selftest).
"""
import struct, sys, os

T_SDL = 0x4c0db839
HASH = 0xe2316427
KIND_4U_TO_GU = {6: 6, 7: 8, 8: 9, 9: 0xb, 0xa: 0xc, 0xb: 0xd, 0xc: 0xe, 0xd: 0xf, 0xe: 0x10}
VSIZE = {0x15: {6: 4, 7: 16, 8: 4, 9: 1, 0xa: 4, 0xb: 4, 0xc: 4, 0xd: 4, 0xe: 64},
         0x16: {6: 4, 8: 16, 9: 4, 0xb: 1, 0xc: 4, 0xd: 4, 0xe: 4, 0xf: 4, 0x10: 64}}
RES_KIND = {0x15: 0xb, 0x16: 0xd}
VEC_KIND = {0x15: 7, 0x16: 8}
F32_KIND = {0x15: 8, 0x16: 9}
BOOL_KIND = {0x15: 9, 0x16: 0xb}
CREF_KIND = {0x15: 0xa, 0x16: 0xc}


def cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('latin1')


def parse(d):
    assert d[:4] == b'SDL\0', d[:4]
    ver, n, h, frames, z, stro = struct.unpack_from('<HHIIII', d, 4)
    assert ver in (0x15, 0x16) and h == HASH and z == 0, (ver, hex(h), z)
    es = 24 if ver == 0x15 else 32
    ents = []
    for i in range(n):
        o = 0x18 + es * i
        if ver == 0x15:
            t, p, nm, x, to, vo = struct.unpack_from('<6I', d, o); e1 = e2 = 0
        else:
            t, p, nm, x, e1, e2, to, vo = struct.unpack_from('<8I', d, o)
        kind, nk = t & 0xff, t >> 16
        e = dict(kind=kind, ptype=(t >> 8) & 0xff, nk=nk, parent=p, name=cstr(d, stro + nm), name_off=nm, x=x,
                 e1=e1, e2=e2, to=to, vo=vo, times=None, values=None)
        if kind in VSIZE[ver] and nk:
            e['times'] = list(struct.unpack_from('<%dI' % nk, d, to))
            e['values'] = d[vo:vo + nk * VSIZE[ver][kind]]
        ents.append(e)
    return dict(ver=ver, frames=frames, ents=ents, strings=d[stro:])


def build(s):
    """re-serialize (data re-laid out with the game tools' rule, see module doc)."""
    ver = s['ver']; es = 24 if ver == 0x15 else 32
    n = len(s['ents'])
    off = 0x18 + es * n
    data = bytearray()
    lay = []
    for e in s['ents']:
        if e['times'] is None:
            lay.append((0, 0)); continue
        to = off + len(data)
        data += struct.pack('<%dI' % len(e['times']), *e['times'])
        while (off + len(data)) % 16: data += b'\0'
        vo = off + len(data)
        data += e['values']
        while (off + len(data)) % 4: data += b'\0'
        lay.append((to, vo))
    stro = off + len(data)
    out = bytearray(b'SDL\0' + struct.pack('<HHIIII', ver, n, HASH, s['frames'], 0, stro))
    for e, (to, vo) in zip(s['ents'], lay):
        t = e['kind'] | e['ptype'] << 8 | (len(e['times']) if e['times'] is not None else e['nk']) << 16
        if ver == 0x15:
            out += struct.pack('<6I', t, e['parent'], e['name_off'], e['x'], to, vo)
        else:
            out += struct.pack('<8I', t, e['parent'], e['name_off'], e['x'], e['e1'], e['e2'], to, vo)
    return bytes(out + data + s['strings'])


# ------------------------------------------------------------------ values

def values(s, e):
    """decoded key values of a track (vec4 tuples, floats, bools, ints; resource tracks -> path strings)."""
    if e['values'] is None: return None
    ver, k, v = s['ver'], e['kind'], e['values']
    nk = len(e['times'])
    if k == VEC_KIND[ver]: return [struct.unpack_from('<4f', v, 16 * i) for i in range(nk)]
    if k == F32_KIND[ver]: return list(struct.unpack_from('<%df' % nk, v))
    if k == BOOL_KIND[ver]: return list(v[:nk])
    if VSIZE[ver][k] == 4:
        w = list(struct.unpack_from('<%dI' % nk, v))
        if k == RES_KIND[ver]: return [cstr(s['strings'], o + 4) if o else '' for o in w]
        return w
    return [v[64 * i:64 * (i + 1)] for i in range(nk)]


def set_values(s, e, vals, times=None):
    """replace a track's keys (vec4 / f32 / int tracks)."""
    ver, k = s['ver'], e['kind']
    if times is not None: e['times'] = list(times)
    nk = len(e['times']); assert len(vals) == nk, (len(vals), nk)
    if k == VEC_KIND[ver]: e['values'] = b''.join(struct.pack('<4f', *(tuple(x) + (0.0,) * (4 - len(x)))) for x in vals)
    elif k == F32_KIND[ver]: e['values'] = struct.pack('<%df' % nk, *vals)
    elif k == BOOL_KIND[ver]: e['values'] = bytes(vals)
    else: e['values'] = struct.pack('<%dI' % nk, *vals)


def objects(s):
    """[(object entry index, name, class hash, {track name: entry})] for kind-2 objects (tracks parented to them,
    including array elements' tracks under the object's arrays)."""
    out = []; owner = {}
    for i, e in enumerate(s['ents']):
        if e['kind'] == 2:
            owner[i] = i; out.append((i, e['name'], e['x'], {}))
        elif e['kind'] in (1, 3, 4):
            owner[i] = None
        else:
            o = owner.get(e['parent']); owner[i] = o
            if o is not None and e['times'] is not None:
                [x for x in out if x[0] == o][0][3].setdefault(e['name'], e)
    return out


def add_string(s, raw):
    """append raw bytes to the string table, return their offset."""
    o = len(s['strings']); s['strings'] = s['strings'] + raw
    return o


def clone_object(s, src, name, model=None, pos=None):
    """append a copy of kind-2 object entry `src` and its direct tracks at the end of the entry list (valid for
    schedulers whose entries are objects only, e.g. the area set schedulers): new name, optional resource track
    'mpModel' -> model path (MOD type 0x58a15856) and vec track 'mPos' -> pos (all keys). Returns the new index."""
    ents = s['ents']
    new = len(ents)
    o = dict(ents[src]); o['name'] = name; o['name_off'] = add_string(s, name.encode('ascii') + b'\0')
    ents.append(o)
    for e in list(ents[src + 1:new]):
        if e['parent'] != src or e['kind'] in (1, 2, 3, 4, 5): continue
        t = dict(e); t['parent'] = new
        if t['times'] is not None: t['times'] = list(t['times'])
        if model is not None and t['name'] == 'mpModel':
            ref = add_string(s, struct.pack('<I', 0x58a15856) + model.encode('ascii') + b'\0')
            t['values'] = struct.pack('<%dI' % len(t['times']), *[ref] * len(t['times']))
        if pos is not None and t['name'] == 'mPos':
            set_values(s, t, [tuple(pos)] * len(t['times']))
        ents.append(t)
    return new


def remove_objects(s, pred):
    """drop the kind-2 objects with pred(class_hash, name) True, with their tracks and arrays, from a parsed scheduler
    (either version); an object whose classref track names a dropped object goes too (GU MaterialControl mpTarget ->
    its model). Track / array parents and classref values are renumbered. Returns the dropped object names."""
    ents, cref = s['ents'], CREF_KIND[s['ver']]
    owner = {}
    for i, e in enumerate(ents):
        if e['kind'] == 2: owner[i] = i
        elif e['kind'] in (1, 3, 4): owner[i] = None
        else: owner[i] = owner.get(e['parent'])
    drop = {i for i, e in enumerate(ents) if e['kind'] == 2 and pred(e['x'], e['name'])}
    while True:
        more = {owner[i] for i, e in enumerate(ents) if e['kind'] == cref and e['values'] is not None and
                owner[i] is not None and owner[i] not in drop and
                set(struct.unpack_from('<%dI' % len(e['times']), e['values'])) & drop}
        if not more: break
        drop |= more
    keep = [i not in drop and owner[i] not in drop for i in range(len(ents))]
    new_idx = {i: j for j, i in enumerate(i for i, k in enumerate(keep) if k)}
    out = []
    for i, e in enumerate(ents):
        if not keep[i]: continue
        e = dict(e)
        if e['kind'] not in (1, 2, 3, 4): e['parent'] = new_idx[e['parent']]
        if e['kind'] == cref and e['values'] is not None:
            w = struct.unpack_from('<%dI' % len(e['times']), e['values'])
            e['values'] = struct.pack('<%dI' % len(w), *[new_idx[v] if v else 0 for v in w])
        out.append(e)
    s['ents'] = out
    return [ents[i]['name'] for i in sorted(drop)]


def resource_paths(s):
    return sorted({v for e in s['ents'] if e['kind'] == RES_KIND[s['ver']] and e['values'] is not None
                   for v in values(s, e) if v})


# ------------------------------------------------------------------ 4U -> GU

def convert_4u(d, drop=None, drop_ctrl=None, drop_obj=None, drop_keyless=False):
    """4U scheduler bytes -> GU scheduler bytes: entries widened (e1 = e2 = 0, as in 703 of 709 GU files), track
    kinds renumbered, data re-laid out; values, names, resource references unchanged.
    drop(class_hash, track_name) -> True removes that track (properties the GU class does not have);
    drop_ctrl(class_hash, name) -> True removes a kind-3 controller section (kind-4 root + controller + its tracks),
    e.g. 4U "Effect"/"MhEffect" 0x5a17f498, a class no GU scheduler uses.
    drop_obj(class_hash, category, name) -> True removes an object with its tracks; classrefs to it become 0.
    drop_keyless=True removes value tracks with 0 keys (time / value offsets 0): 4U m19a00d-a00 has keyless mScale x2
    / mAngle x1 on billboarded uStageSets; no GU uStageSet (0x2516a76b) has a keyless track in any GU stage scheduler
    (GU leaves such tracks out: the property keeps its class default, scale 1 / angle 0, as 4U's keyless tracks mean).
    Parent fields: objects (kind 2) carry a category number (9, 10, 11, 16, 17 ...), not an index -> kept; tracks and
    arrays point at entry indices -> renumbered, like classref values, when entries are removed."""
    s = parse(d)
    assert s['ver'] == 0x15
    ents0 = s['ents']
    owner_cls = {}
    keep = []
    for i, e in enumerate(ents0):
        if e['kind'] == 2: owner_cls[i] = e['x']
        elif e['kind'] in (1, 3, 4): owner_cls[i] = e['x'] if e['kind'] == 3 else None
        else: owner_cls[i] = owner_cls.get(e['parent'])
        is_track = e['kind'] not in (1, 2, 3, 4, 5)
        k = not (drop and is_track and drop(owner_cls[i], e['name']))
        if drop_keyless and e['kind'] in VSIZE[0x15] and e['nk'] == 0: k = False
        if e['kind'] == 3 and drop_ctrl and drop_ctrl(e['x'], e['name']): k = False
        if e['kind'] == 2 and drop_obj and drop_obj(e['x'], e['parent'], e['name']): k = False
        if e['kind'] not in (1, 2, 3, 4) and not keep[e['parent']]: k = False      # child of a removed entry
        keep.append(k)
    dropped_obj = {i for i, e in enumerate(ents0) if e['kind'] == 2 and not keep[i]}
    for i, e in enumerate(ents0):          # a section root left without its controller goes too
        if e['kind'] == 4 and not (i + 1 < len(ents0) and ents0[i + 1]['kind'] == 3 and keep[i + 1]):
            keep[i] = False
    new_idx = {}; j = 0
    for i, k in enumerate(keep):
        if k: new_idx[i] = j; j += 1
    ents = []
    for i, e in enumerate(ents0):
        if not keep[i]: continue
        e = dict(e)
        if e['kind'] in KIND_4U_TO_GU: e['kind'] = KIND_4U_TO_GU[e['kind']]
        if e['kind'] not in (1, 2, 3, 4): e['parent'] = new_idx[e['parent']]
        if e['kind'] == CREF_KIND[0x16] and e['values'] is not None:
            w = struct.unpack_from('<%dI' % len(e['times']), e['values'])
            assert all(v == 0 or v in new_idx or v in dropped_obj for v in w), ('classref to a dropped entry',
                                                                              e['name'], w)
            e['values'] = struct.pack('<%dI' % len(w), *[new_idx.get(v, 0) if v else 0 for v in w])
        ents.append(e)
    return build(dict(ver=0x16, frames=s['frames'], ents=ents, strings=s['strings']))


# ------------------------------------------------------------------ CLI

def dump(path):
    d = open(path, 'rb').read(); s = parse(d)
    print('%s: version %#x, %d entries, %d frames' % (path, s['ver'], len(s['ents']), s['frames']))
    for i, e in enumerate(s['ents']):
        if e['kind'] in (1, 2, 3, 4, 5):
            print('  [%d] kind %d parent %d %s %08x' % (i, e['kind'], e['parent'], e['name'], e['x']))
        else:
            v = values(s, e)
            print('    [%d] %s (kind %#x type %#x) %s' % (
                i, e['name'], e['kind'], e['ptype'],
                None if v is None else list(zip(['%d:%d' % (t >> 24, t & 0xffffff) for t in e['times']], v))))


def selftest(root):
    n = bad = 0
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if not (f.endswith('.4c0db839') or f.endswith('.sdl')): continue
            d = open(os.path.join(dp, f), 'rb').read(); n += 1
            if build(parse(d)) != d: bad += 1; print('MISMATCH', os.path.join(dp, f))
    print('%s: SDL files %d, byte-identical %d' % (root, n, n - bad))
    return bad == 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'dump':
        for p in sys.argv[2:]: dump(p)
    elif cmd == 'selftest':
        ok = all([selftest(r) for r in sys.argv[2:]])
        sys.exit(0 if ok else 1)
    elif cmd == 'conv':
        open(sys.argv[3], 'wb').write(convert_4u(open(sys.argv[2], 'rb').read()))
    else:
        raise SystemExit(__doc__)
