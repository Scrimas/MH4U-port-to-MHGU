"""emdata4u.py : convert MH4U per-monster data (em_data.arc: `emd` 0x0a0e48d4 + `etd` 0x3d8bbbac) into MHGU's
enemy data files. Layouts were read from GU's own loaders (tools/guemu.py) and checked on monsters present in both
games (selftest: rebuild GU Rathian em001_00 and Kushala em024_00 from their 4U data and diff).

  emdata4u.py selftest
  emdata4u.py build EMNNN OUTDIR      write the converted files for one 4U monster

Whole-file formats (GU loads the file into memory and fixes pointers in place, so they are 4U images + header):
  bodydata / cambodydata (BDD 0x20110219): 4U emd header word 8 / 9 -> 44-byte records until bone == 0xFFFF.
      GU: {'BDD\\0', ver, count, 0} + records (+2 bone B = 0xFFFF unless shape 2, last u16 = 0) + terminator
      {FFFF FFFF, 0...}. bodydata = the HURT volumes (bone, shape, hitzone/part indexes; GU Rathian/Kushala).
  attackdata (HDE 0x20160121): 4U etd header word 28 -> 40-byte records up to word 29. GU record = 4U[0:32] with
      byte 18 -> b18 & 3, byte 31 = b18 >> 2 (moved knockback bits), byte 28 = 6 (0xFE on the all-zero record 0).
  hitsize (HTS 0x20131015): 4U etd header word 27 -> one pointer per group, up to word 28; a group is 40-byte
      records closed by a record whose u16 0 is 0xFFFF. GU: header, (count, offset) per group, records of 48 bytes
      (4U record + 8 zero bytes), then one empty group (count 0, offset = end), as in GU's own files.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arc import arc_entries, arc_read

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EM_DATA = os.path.join(ROOT, 'dump/romfs/data/em_data.arc')
T_EMD, T_ETD = 0x0A0E48D4, 0x3D8BBBAC


def load_4u(em):
    f = open(EM_DATA, 'rb').read()
    out = {}
    for e in arc_entries(f):
        if e[0] == 'enemy\\%s\\data\\%s' % (em, em):
            out['emd' if e[1] == T_EMD else 'etd'] = arc_read(f, e)
    return out


def hw(b, i):
    return struct.unpack_from('<I', b, 4 * i)[0]

# ---------------------------------------------------------------- bodydata

def bodydata(emd, word):
    p = hw(emd, word)
    recs = []
    while struct.unpack_from('<H', emd, p)[0] != 0xFFFF:
        r = bytearray(emd[p:p + 44])
        # record: u16 bone A, u16 bone B, u16 shape (0 sphere, 1 capsule off1-off2 on A, 2 capsule A+off1 ->
        # B+off2), u16 x5 (hitzone/part/flags), f32 radius, off1[3], off2[3]. GU writes "no bone B" as 0xFFFF
        # but keeps B on shape 2 (checked on the shared monsters); forcing 0xFFFF there collapsed em089's
        # 26 two-bone capsules (wings, neck, tail)
        if struct.unpack_from('<H', r, 4)[0] != 2:
            struct.pack_into('<H', r, 2, 0xFFFF)
        struct.pack_into('<H', r, 42, 0)
        recs.append(bytes(r)); p += 44
    term = struct.pack('<HH', 0xFFFF, 0xFFFF) + bytes(40)
    return struct.pack('<4sIII', b'BDD\0', 0x20110219, len(recs), 0) + b''.join(recs) + term

# ---------------------------------------------------------------- attackdata

def attackdata(etd):
    a, b = hw(etd, 28), hw(etd, 29)
    recs = []
    for k in range((b - a) // 40):
        r4 = etd[a + 40 * k:a + 40 * k + 40]
        r = bytearray(r4[:32])
        if not any(r4):
            r[28] = 0xFE
        else:
            r[18] = r4[18] & 3
            r[31] = r4[18] >> 2
            r[28] = 6
        recs.append(bytes(r))
    return struct.pack('<4sIII', b'HDE\0', 0x20160121, len(recs), 0) + b''.join(recs)

# ---------------------------------------------------------------- hitsize

def hitsize(etd):
    a, b = hw(etd, 27), hw(etd, 28)
    groups = []
    for i in range((b - a) // 4):
        p = hw(etd, 0) and struct.unpack_from('<I', etd, a + 4 * i)[0]
        recs = []
        while p and struct.unpack_from('<H', etd, p)[0] != 0xFFFF:
            recs.append(etd[p:p + 40] + bytes(8)); p += 40
        groups.append(recs)
    groups.append([])
    n = len(groups)
    off = 16 + 8 * n
    table, data = b'', b''
    for recs in groups:
        table += struct.pack('<II', len(recs), off + len(data))
        data += b''.join(recs)
    return struct.pack('<4sIII', b'HTS\0', 0x20131015, n, 0) + table + data


# ---------------------------------------------------------------- parts visibility (XFS, rMonsterPartsManager)

def part_rows(emd):
    """4U visibility rows (emd header +0x88): (group, cond, mode, param, threshold) until group == -1.
    mode 0: hidden while the condition holds; mode 1: hidden while it does not (every row counts)."""
    o = struct.unpack_from('<I', emd, 0x88)[0]; out = []
    while True:
        g, c, m, p, t = struct.unpack_from('<iHHII', emd, o)
        if g == -1: return out
        out.append((g, c, m, p, t)); o += 16


def spawn_visible(rows, groups):
    """visibility at spawn (no break, no sever, no state bit): hidden if any mode-1 row names the group."""
    hidden = {g for g, c, m, p, t in rows if m == 1}
    return {g: (g not in hidden) for g in groups}


def xfs_states(states):
    """XFS data for rMonsterPartsManager: states = [[(group, visible), ...], ...]. Returns (bytes, object count).
    Object = u16 class, u16 index, u32 size (size counts itself + the content); classes as in GU's files:
    1 root {mQuality=2, mPartsVisibleGroupList}, 3 array {mAutoDelete=0, mpArray}, 5 cPartsVisibleGroup
    {mPartsVisibleInfo array}, 7 cPartsVisibleInfo {group u32, visible u8}."""
    idx = [0]

    def obj(cls, content):
        i = idx[0]; idx[0] += 1
        return (cls, i, content)

    def ser(o):
        cls, i, content = o
        body = b''.join(ser(c) if isinstance(c, tuple) else c for c in content)
        return struct.pack('<HHI', cls, i, 4 + len(body)) + body
    root = obj(1, [])
    arr = obj(3, [])
    elems = []
    for st in states:
        grp = obj(5, [])
        inner = obj(3, [])
        infos = [obj(7, [struct.pack('<II', 1, g), struct.pack('<IB', 1, 1 if v else 0)]) for g, v in st]
        inner[2].extend([struct.pack('<IBI', 1, 0, len(infos))] + infos)
        grp[2].extend([struct.pack('<I', 1), inner])
        elems.append(grp)
    arr[2].extend([struct.pack('<IBI', 1, 0, len(elems))] + elems)
    root[2].extend([struct.pack('<II', 1, 2), struct.pack('<I', 1), arr])
    return ser(root), idx[0]


def parse_xfs_states(x):
    """inverse of xfs_states on a GU file (root located by its size field)."""
    for r in range(0x100, len(x) - 8):
        if struct.unpack_from('<HHI', x, r) == (1, 0, len(x) - r - 4):
            break
    out, i = [], r
    while i < len(x) - 8:
        cls, idx, size = struct.unpack_from('<HHI', x, i)
        if cls == 5:
            out.append([]); i += 8; continue
        if cls == 7:
            g = struct.unpack_from('<I', x, i + 12)[0]; v = x[i + 20]
            out[-1].append((g, v)); i += 8 + size - 4; continue
        i += 8 if cls in (1, 3) else 1
        if cls == 3: i += 9 if x[i] == 1 else 0
    return r, out


SPAWN_STATE_WORD = 0x7C      # em089 4U state word at spawn (tar state bits; agent D, em089 4U code)


def row_visible(rows, g, word=SPAWN_STATE_WORD, broken=(), severed=()):
    """4U visibility of group g: hidden if any of its rows hides it. Conditions: 7 = state word & param,
    6 = break record param broken, 1 = sever param done, 11 = unknown (taken as false)."""
    for gg, c, m, p, t in rows:
        if gg != g: continue
        holds = {7: bool(word & p), 6: p in broken, 1: p in severed}.get(c, False)
        if holds if m == 0 else not holds:
            return False
    return True


def partsvis(emd, donor_xfs, model_groups, word=SPAWN_STATE_WORD):
    """Gogmazios-style visibility states in the donor's state layout (Kushala: 0 base, 1/6 eyelid, 2-4 / 7-9
    break pairs intact / broken, 5 / 10 tail intact / severed, 11 empty), filled from the 4U rows by role.
    Every value is the group's full 4U evaluation (all its rows) at the spawn state word, intact and unsevered,
    except the one break / sever the state stands for."""
    rows = part_rows(emd)
    groups = sorted(set(model_groups) | {g for g, *_ in rows})
    breaks = {}                                       # break record -> groups
    for g, c, m, p, t in rows:
        if c == 6 and g not in breaks.get(p, []): breaks.setdefault(p, []).append(g)
    sever = sorted({g for g, c, m, p, t in rows if c == 1 and p == 1})      # tail
    slots = sorted(breaks)[:3]
    in_slot = {g for p in slots for g in breaks[p]} | set(sever)
    vis = lambda g, **kw: row_visible(rows, g, word, **kw)
    base = [(g, vis(g)) for g in groups if g not in in_slot]
    intact = [[(g, vis(g)) for g in breaks[p]] for p in slots]
    broken = [[(g, vis(g, broken={p})) for g in breaks[p]] for p in slots]
    while len(intact) < 3: intact.append([]); broken.append([])
    states = [base, []] + intact + [[(g, vis(g)) for g in sever], []] + broken + \
             [[(g, vis(g, severed={1})) for g in sever], []]
    r, _ = parse_xfs_states(donor_xfs)
    data, nobj = xfs_states(states)
    head = bytearray(donor_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    return bytes(head) + data, states


CONVERTERS = {
    'bodydata': lambda d: bodydata(d['emd'], 8),
    'cambodydata': lambda d: bodydata(d['emd'], 9),
    'attackdata': lambda d: attackdata(d['etd']),
    'hitsize': lambda d: hitsize(d['etd']),
}


def selftest():
    sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
    from romfs import RomFS
    rom = RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
    for em4, gu in (('em001', 'em001_00'), ('em031', 'em024_00'), ('em011', 'em011_00'), ('em032', 'em027_00')):
        d4 = load_4u(em4)
        arc = rom.read('/nativeNX/arc/enemy/%s.arc' % gu)
        G = {e[0].split('\\')[-1]: arc_read(arc, e) for e in arc_entries(arc)}
        for kind, conv in CONVERTERS.items():
            ref = G.get('%s_%s' % (gu, kind))
            if ref is None: continue
            out = conv(d4)
            same = sum(x == y for x, y in zip(out, ref))
            print('%s %-12s ours %5d GU %5d bytes  header-equal %s  equal bytes %5.1f%%' % (
                gu, kind, len(out), len(ref), out[:12] == ref[:12], 100.0 * same / max(len(ref), 1)))


if __name__ == '__main__':
    if sys.argv[1] == 'selftest':
        selftest()
    elif sys.argv[1] == 'build':
        d4 = load_4u(sys.argv[2]); os.makedirs(sys.argv[3], exist_ok=True)
        for kind, conv in CONVERTERS.items():
            open(os.path.join(sys.argv[3], kind + '.bin'), 'wb').write(conv(d4))
