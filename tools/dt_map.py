"""dt_map.py : learn where every field of a GU enemy-data object (dtbase / dtbparts / dttune) comes from in the
MH4U em_data files (emd / etd), from monsters present in both games. Run with the MHGU_Editor scratch venv.

  dt_map.py KIND        prints, per GU object field / heap block, its 4U source for each training monster and
                        whether they agree

GU objects come from emulating the game's own loader on the GU file (tools/gu_schema.py). A 4U source is
described relative to the 4U header: ('hdr', off) for a scalar at header offset off, ('ptr', w, delta) for data at
delta bytes into the block that header word w points to.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
import gu_schema
from arc import arc_entries, arc_read
from romfs import RomFS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = {'dtbase': 'emd', 'dtbparts': 'emd', 'dttune': 'etd'}
GU_FILE = {'dtbase': 0x59D9C3DA, 'dtbparts': 0x1BBC291E, 'dttune': 0x48E8AC29}
TRAIN = [('em001', 'em001_00'), ('em031', 'em024_00'), ('em032', 'em027_00')]


def shared_pairs():
    """(4U emNNN, GU emNNN_VV) for every monster in both games, matched by English name (40 pairs)."""
    import csv, re
    d = open(os.path.join(ROOT, 'dump/romfs/eng/data/core_common.arc'), 'rb').read()
    b = [arc_read(d, e) for e in arc_entries(d) if e[0] == 'eng\\msg\\emName_eng'][0]
    i = b.find('Rathian'.encode('utf-16le')); start = b.rfind(b'\0\0\0\0', 0, i)
    names = [m.group().decode('utf-16le') for m in re.finditer(rb'(?:[\x20-\x7e\x80-\xff][\x00])+', b[start:])]
    em4 = {}
    for k, nm in enumerate(names): em4.setdefault(nm, 'em%03d' % (k + 1))
    img = open('/home/scrimas/Projects/MHGU_Editor/scratch/mem.bin', 'rb').read()
    pairs = {struct.unpack_from('<II', img, 0x1597EA4 + 8 * i)[1]: struct.unpack_from('<II', img, 0x1597EA4 + 8 * i)[0]
             for i in range(137)}
    out = []
    for row in csv.DictReader(open('/home/scrimas/Projects/MHGU_Editor/data/monster-index.csv')):
        nm, idx = row['monster'], int(row['index']) - 1
        if nm not in em4 or idx not in pairs or pairs[idx] & 0x1000: continue
        if nm.startswith(('Raging', 'Furious', 'Savage', 'Apex')): continue   # variants share the base's GU file
        eid = pairs[idx]
        out.append((em4[nm], 'em%03d_%02d' % (eid & 0xFF, (eid >> 8) & 0xF)))
    return sorted(set(out))
HDR_WORDS = 48


def load_4u():
    f = open(os.path.join(ROOT, 'dump/romfs/data/em_data.arc'), 'rb').read()
    out = {}
    for e in arc_entries(f):
        out[(e[0].split('\\')[1], 'etd' if e[1] == 0x3D8BBBAC else 'emd')] = arc_read(f, e)
    return out


def gu_file(rom, gu, kind):
    d = rom.read('/nativeNX/arc/enemy/%s.arc' % gu)
    return [arc_read(d, e) for e in arc_entries(d) if e[1] == GU_FILE[kind]][0]


def ptr_words(u):
    """header word index -> pointer value, for words that look like offsets into the file."""
    out = {}
    for w in range(2, HDR_WORDS):
        v = struct.unpack_from('<I', u, 4 * w)[0]
        if 4 * HDR_WORDS <= v < len(u) and v % 2 == 0:
            out[w] = v
    return out


def locate(u, needle, ptrs, prefer=None):
    """where does `needle` (bytes) sit in the 4U file, relative to its header pointers."""
    hits, i = [], u.find(needle)
    while i != -1:
        hits.append(i); i = u.find(needle, i + 1)
    if not hits:
        return None
    descs = []
    for h in hits:
        if h + len(needle) <= 4 * HDR_WORDS:
            descs.append(('hdr', h))
            continue
        base = max(((w, p) for w, p in ptrs.items() if p <= h), key=lambda wp: wp[1], default=None)
        if base:
            descs.append(('ptr', base[0], h - base[1]))
    if prefer and prefer in descs:
        return prefer
    return descs[0] if len(descs) == 1 else tuple(descs)


def object_parts(s):
    """scalar runs of the object (contiguous obj fields read from the file) and heap blocks with their owner."""
    runs, cur = [], None
    for fo, n, (reg, off) in sorted((f for f in s['fields'] if f[2][0] == 'obj'), key=lambda f: f[2][1]):
        if cur and off == cur[1]:
            cur[1] = off + n
        else:
            cur = [off, off + n]; runs.append(cur)
    obj = s['mem'][('obj', 0)]
    scalars = [(a, obj[a:b]) for a, b in runs]
    blocks = []
    for i, (p, n) in enumerate(s['blocks']):
        own = s['owner'].get(i)
        blocks.append((i, n, own, s['mem'][('heap', i)][:n]))
    return scalars, blocks


def learn(kind, rom=None, U=None):
    rom = rom or RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
    U = U or load_4u()
    table = {}
    for em4, gu in TRAIN:
        try:
            s = gu_schema.schema(gu_file(rom, gu, kind), kind)
        except IndexError:
            continue
        files = {k: (U[(em4, k)], ptr_words(U[(em4, k)])) for k in ('emd', 'etd')}

        def loc_any(piece):
            out = {}
            for k, (u, ptrs) in files.items():
                l = locate(u, piece, ptrs)
                if l: out[k] = l
            return out or None
        scalars, blocks = object_parts(s)
        for off, b in scalars:
            for k in range(0, len(b), 4):             # per 4-byte slice so short differences stay local
                piece = b[k:k + 4]
                if len(piece) < 4 or piece == b'\0\0\0\0':
                    continue
                table.setdefault(('obj', off + k, len(piece)), {})[em4] = loc_any(piece)
        for i, n, own, data in blocks:
            if own is None:
                continue
            key = ('block', '%s+%#x' % ('obj' if own[0][0] == 'obj' else 'heap', own[1]))
            table.setdefault(key, {})[em4] = (n, loc_any(data) if n >= 4 else None)
    return table


if __name__ == '__main__':
    t = learn(sys.argv[1])
    for k in sorted(t, key=str):
        v = t[k]
        locs = {str(x[1] if k[0] == 'block' else x) for x in v.values()}
        print('%-28s %s %s' % (k, 'AGREE' if len(locs) == 1 and 'None' not in locs else '     ', v))
