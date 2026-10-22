"""portdata.py : a monster's data file nativeNX/mh4uport/<name>.bin, read by the core module (module/port.c).

  portdata.py pack NAME          monsters/NAME/gen/*.sec (one per section, written by the monster's tools through
                                 write_section) + monsters/NAME/package.toml -> monsters/NAME/gen/NAME.bin
  portdata.py dump FILE.bin      print every section (checks)

Every registered monster's data file always ships (allocations.toml order = append order, so gear IDs never move);
whether a monster is installed is decided by its assets (module/port.c). Format 1, little endian, 4-aligned:
  header 32 B   char magic[4] "MH4P", u16 format, u16 sections, char name[16] (cut to 16 bytes, no NUL then: the
                core compares those 16 bytes and em_id), u32 version (major << 16 | minor << 8 | patch, package.toml),
                u32 em_id
  directory     sections x {char tag[4], u32 offset, u32 size} (offsets from the file start)
  sections      strings are NUL-terminated UTF-8 inside the section, referenced by u32 offsets from the section start
Sections (written by the monster tools, consumed by module/*.c):
  FILE  u32 first_id, u32 count, s32 manifest[51], {u32 path hash, u32 type hash}[count]          (file_id, registry)
  ITEM  u32 n, n x {u16 id, u8 rarity, icon, colour, category, dummy_icon, 0, u32 dummy_sell, sell, buy},
        u32 text[5][n][2] (name, description per language)                                            (items.c)
  BUI   u32 groups, u32 entries, u8 cond[groups], u8 count[groups] (4-aligned), {u8 chance, count, u16 item}[entries]
  BUIr  the same for GU rank file r = '1' Low, '2' High, '4' G (quest\bui\bui_s<r>): preferred over BUI     (items.c)
  TBLA  u32 n, n x {u32 path suffix, u32 flags, u32 alloc, free, ctor, parse, u16 mem size, u16 file record size,
        u32 base, u32 count, u32 records}: records appended to a GU table when it holds exactly `base`   (gear.c)
  TXTA  u32 n, n x {u32 GMD name, u32 base, u32 count, u32 strings}: u32 strings[5][count] appended (gear.c)
  NOTE  u8 list record[16], u8 unlock record[8], u32 after (entry it is listed after)               (notes.c)
  NAME  u32 monsterName entry, u32 name[5]                                                           (items.c)
  SKIL  u32 n, n x {u32 skill, u32 grants[3]}: having `skill` also answers yes for the granted GU skills (gear.c)
  PWLF  u32 n, n x {u32 path suffix, u16 model, u8 from, u8 to}: weapon motion-set fixes             (gear.c)
  GPTS  u32 n, n x {u8 GU rank, u8 list, u16 0, u32 offset}, lists {u8 weight, u8 qty, u16 item} closed by weight
        0xff: a monster's runtime gather-point item lists (monsters/dalamadur/module/dala_gather.c)
  WALK  u32 n, n x {u16 joint, u16 triangles, u32 offset}, triangles x 9 f32 bone-local vertices: 4U walk strips
        for the module's copy of 4U's ground query (monsters/dalamadur/module/dala_walk.c, tools/walk_em090.py)
TBLA flags: 1 = the sharpness table, 2 = needs that monster's sharpness rows (skipped when they were refused).
"""
import json, os, struct, sys, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths

MAGIC, FORMAT = b'MH4P', 1
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')       # text order in every section (items.c language index)
TBL_KIREAJI, TBL_NEEDS_KIREAJI = 1, 2


class Section:
    """fixed part + strings: s.u32(v), s.raw(b), s.str(text) (u32 offset of a pooled string), s.bytes()"""
    def __init__(self, tag):
        assert len(tag) == 4
        self.tag, self.body, self.refs, self.pool = tag, bytearray(), [], {}

    def raw(self, b):
        self.body += b

    def u32(self, *v):
        self.body += struct.pack('<%dI' % len(v), *[x & 0xFFFFFFFF for x in v])

    def align(self):
        self.body += bytes(-len(self.body) % 4)

    def str(self, s):
        self.refs.append((len(self.body), s))
        self.body += bytes(4)

    def bytes(self):
        self.align()
        out, pool, offs = bytearray(self.body), bytearray(), {}
        for pos, s in self.refs:
            if s not in offs:
                offs[s] = len(out) + len(pool)
                pool += s.encode('utf-8') + b'\0'
            struct.pack_into('<I', out, pos, offs[s])
        out += pool
        return bytes(out + bytes(-len(out) % 4))


def tbla(tables):
    """TBLA from [dict(path, cls=(alloc, free, ctor, parse, mem size), rec_bytes, base, records, flags=0)]"""
    s = Section('TBLA')
    off = 4 + 40 * len(tables)
    s.u32(len(tables))
    for t in tables:
        assert len(t['records']) % t['rec_bytes'] == 0, t['path']
        a, f, c, p, ms = t['cls']
        s.str(t['path'])
        s.u32(t.get('flags', 0), a, f, c, p)
        s.raw(struct.pack('<HH', ms, t['rec_bytes']))
        s.u32(t['base'], len(t['records']) // t['rec_bytes'], off)
        off += (len(t['records']) + 3) // 4 * 4
    for t in tables:
        s.raw(t['records'])
        s.align()
    return s


def txta(texts):
    """TXTA from [(GMD name, base, strings[5][n])]"""
    s = Section('TXTA')
    off = 4 + 16 * len(texts)
    s.u32(len(texts))
    for name, base, strs in texts:
        assert len(strs) == len(LANGS) and len({len(x) for x in strs}) == 1, name
        s.str(name)
        s.u32(base, len(strs[0]), off)
        off += 4 * len(LANGS) * len(strs[0])
    for _, _, strs in texts:
        for lang in strs:
            for x in lang: s.str(x)
    return s


def sec_dir(name):
    """where an entry's section files live: monsters/<name>/gen, or gen/<entry> in a package of several entries"""
    return paths.gen(name) if paths.package(name) == name else os.path.join(paths.gen(name), name)


def write_section(name, sec, part=None):
    """<sec_dir>/<TAG>[-part].sec (several files may carry the same tag: the module reads them all)"""
    d = sec_dir(name)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, sec.tag.strip() + ('-' + part if part else '') + '.sec')
    open(p, 'wb').write(sec.tag.encode() + sec.bytes())
    return p


def version(name):
    with open(os.path.join(paths.monster(name), 'package.toml'), 'rb') as f:
        v = tomllib.load(f)['version']
    major, minor, patch = (int(x) for x in v.split('.'))
    return v, major << 16 | minor << 8 | patch


def pack(name):
    import alloc
    m = alloc.monster(name)
    d = sec_dir(name)
    secs = []
    for f in sorted(os.listdir(d)):
        if f.endswith('.sec'):
            b = open(os.path.join(d, f), 'rb').read()
            secs.append((b[:4], b[4:]))
    vs, v = version(name)
    head = MAGIC + struct.pack('<HH16sII', FORMAT, len(secs), name.encode(), v, m['em_id'])
    off = len(head) + 12 * len(secs)
    dir_, body = b'', b''
    for tag, b in secs:
        dir_ += tag + struct.pack('<II', off + len(body), len(b))
        body += b
    out = os.path.join(paths.gen(name), name + '.bin')
    open(out, 'wb').write(head + dir_ + body)
    print('wrote %s: version %s, %d sections (%s), %d bytes' % (out, vs, len(secs),
                                                                ' '.join(t.decode() for t, _ in secs),
                                                                len(head + dir_ + body)))
    return out


# ---- reader (checks, tools/datacheck) ----
def cstr(b, off):
    return b[off:b.index(b'\0', off)].decode('utf-8')


def read(path):
    d = open(path, 'rb').read()
    assert d[:4] == MAGIC, 'not a port data file'
    fmt, n, nm, ver, em = struct.unpack_from('<HH16sII', d, 4)
    secs = []
    for k in range(n):
        tag = d[32 + 12 * k:36 + 12 * k].decode()
        o, s = struct.unpack_from('<II', d, 36 + 12 * k)
        secs.append((tag, d[o:o + s]))
    return dict(format=fmt, name=nm.rstrip(b'\0').decode(), version=ver, em_id=em), secs


def decode(tag, b):
    u = lambda o, n=1: struct.unpack_from('<%dI' % n, b, o)
    if tag == 'FILE':
        first, count = u(0, 2)
        man = list(struct.unpack_from('<51i', b, 8))
        files = [u(212 + 8 * k, 2) for k in range(count)]
        return dict(first=first, manifest=man, files=files)
    if tag == 'ITEM':
        n = u(0)[0]
        recs = [struct.unpack_from('<HBBBBBxIII', b, 4 + 20 * k) for k in range(n)]
        t = 4 + 20 * n
        text = [[[cstr(b, u(t + 4 * (2 * (len(recs) * l + i) + j))[0]) for j in range(2)] for i in range(n)]
                for l in range(len(LANGS))]
        return dict(items=recs, text=text)
    if tag[:3] == 'BUI':
        g, e = u(0, 2)
        cond, cnt = list(b[8:8 + g]), list(b[8 + g:8 + 2 * g])
        o = 8 + (2 * g + 3) // 4 * 4
        return dict(cond=cond, count=cnt, entries=[struct.unpack_from('<BBH', b, o + 4 * k) for k in range(e)])
    if tag == 'TBLA':
        n, out = u(0)[0], []
        for k in range(n):
            p, fl, a, f, c, pa = u(4 + 40 * k, 6)
            ms, rb = struct.unpack_from('<HH', b, 28 + 40 * k)
            base, cnt, rec = u(32 + 40 * k, 3)
            out.append(dict(path=cstr(b, p), flags=fl, cls=[a, f, c, pa, ms], rec_bytes=rb, base=base, count=cnt,
                            records=b[rec:rec + rb * cnt].hex()))
        return out
    if tag == 'TXTA':
        n, out = u(0)[0], []
        for k in range(n):
            nm, base, cnt, so = u(4 + 16 * k, 4)
            out.append(dict(gmd=cstr(b, nm), base=base,
                            text=[[cstr(b, u(so + 4 * (cnt * l + i))[0]) for i in range(cnt)] for l in range(len(LANGS))]))
        return out
    if tag == 'NOTE':
        return dict(list=b[:16].hex(), unlock=b[16:24].hex(), after=u(24)[0])
    if tag == 'NAME':
        return dict(entry=u(0)[0], name=[cstr(b, u(4 + 4 * l)[0]) for l in range(len(LANGS))])
    if tag == 'SKIL':
        return [u(4 + 16 * k, 4) for k in range(u(0)[0])]
    if tag == 'PWLF':
        return [(cstr(b, u(4 + 8 * k)[0]),) + struct.unpack_from('<HBB', b, 8 + 8 * k) for k in range(u(0)[0])]
    return b.hex()


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['pack']:
        pack(a[1])
    elif a[:1] == ['dump']:
        h, secs = read(a[1])
        print(json.dumps(h))
        for t, b in secs:
            print(t, json.dumps(decode(t, b), ensure_ascii=False)[:2000])
    else:
        print(__doc__)
        sys.exit(2)
