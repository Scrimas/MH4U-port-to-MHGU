"""emdata4u.py : convert MH4U per-monster data (em_data.arc: `emd` 0x0a0e48d4 + `etd` 0x3d8bbbac) into MHGU's
enemy data files. Layouts were read from GU's own loaders (tools/guemu.py) and checked on monsters present in both
games (selftest: rebuild GU Rathian em001_00 and Kushala em024_00 from their 4U data and diff).

  emdata4u.py selftest
  emdata4u.py build EMNNN OUTDIR      write the converted files for one 4U monster

Whole-file formats (GU loads the file into memory and fixes pointers in place, so they are 4U images + header):
  bodydata / cambodydata (BDD 0x20110219): 4U emd header word 8 / 9 -> 44-byte records until bone == 0xFFFF.
      GU: {'BDD\\0', ver, count, 0} + the 4U records unchanged (bone B 0 on shapes 0 / 1 as GU's em027_00; off2.z
      at +40 is a float in both games) + terminator {FFFF FFFF, 0...}. bodydata = the hurt AND push volumes (bone,
      shape, hitzone/part indexes; GU Rathian/Kushala; Dalamadur's gu-walkable.md 6b).
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
        # B+off2), u16 x5 (hitzone/part/flags), f32 radius, off1[3], off2[3]. Bone B: GU's own files mostly
        # write 0xFFFF on shapes 0 / 1 where 4U has 0 (em001 / em024 / em084 / em087 / em012), em027_00 keeps
        # 4U's 0 and loads (C, data); kept as 4U since 2026-10-25 (Dalamadur 1.0.0 and Gogmazios 1.1.1 ship it;
        # this wrote 0xFFFF on shapes 0 / 1 before). Shape 2 keeps B in both games: forcing 0xFFFF there
        # collapsed em089's 26 two-bone capsules (wings, neck, tail). Bytes 40..43 are off2.z in both games (GU
        # Rathian em001_00 record 4 keeps 4U's (0, 10, -215), C); they were zeroed here until 2026-10-25 (the high
        # half of the float): every capsule's far end fell to z ~0 (Dalamadur's head volumes shrank to the head
        # joint, user: "can't hit the head, can walk through it"; Gogmazios: 24 of 53 records, fixed in 1.1.1)
        recs.append(bytes(r)); p += 44
    term = struct.pack('<HH', 0xFFFF, 0xFFFF) + bytes(40)
    return struct.pack('<4sIII', b'BDD\0', 0x20110219, len(recs), 0) + b''.join(recs) + term

# ---------------------------------------------------------------- attackdata

def attackdata(etd):
    a, b = hw(etd, 28), hw(etd, 29)
    if not b:     # word 29 absent (Dalamadur em024 / em083: 70 / 24 records): the table runs to the next block named
        # by the header (40 words, blocks from 0xa0; words 35+ hold floats / counts, not offsets)
        b = min(v for v in (hw(etd, i) for i in range(29, 40)) if a < v < len(etd))
        assert (b - a) % 40 == 0, 'attack table %#x..%#x is not whole 40-byte records' % (a, b)
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

def hitsize(etd, off2_gu=False):
    """off2_gu: GU's records are 48 B with the far end of a capsule at +32 (4U: 40 B, at +28), C: 4U vs GU records equal
    with it moved, Teostra 83 of 83 (50 as copied), Kushala 58 of 60 (35), Diablos 53 of 55 (20), Rathian 35 of 38 (8).
    As copied, GU reads (y, z, 0) for that end, and the capsule points the wrong way. False keeps the bytes the shipped
    monsters were built with: a change of their attack volumes, not to be made silently."""
    a, b = hw(etd, 27), hw(etd, 28)
    groups = []
    for i in range((b - a) // 4):
        p = hw(etd, 0) and struct.unpack_from('<I', etd, a + 4 * i)[0]
        recs = []
        while p and struct.unpack_from('<H', etd, p)[0] != 0xFFFF:
            r = etd[p:p + 40]
            recs.append(r[:28] + bytes(4) + r[28:] + bytes(4) if off2_gu else r + bytes(8)); p += 40
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
    """inverse of xfs_states on a GU file (root located by its size field), reading the objects in the exact layout
    xfs_states writes (a byte scan for class numbers misread size fields holding 05, e.g. GU em005_00's 0x5e0)."""
    for r in range(0x100, len(x) - 8):
        if struct.unpack_from('<HHI', x, r) == (1, 0, len(x) - r - 4):
            break

    def array(i):
        """array object at i -> (element count, offset of its first element)"""
        cls, _, _ = struct.unpack_from('<HHI', x, i)
        one, auto, n = struct.unpack_from('<IBI', x, i + 8)
        assert cls == 3 and (one, auto) == (1, 0), ('XFS array', hex(i))
        return n, i + 17
    assert struct.unpack_from('<III', x, r + 8) == (1, 2, 1), 'XFS root'
    out = []
    n, i = array(r + 20)
    for _ in range(n):
        cls, _, size = struct.unpack_from('<HHI', x, i)
        assert cls == 5 and struct.unpack_from('<I', x, i + 8)[0] == 1, ('XFS group', hex(i))
        m, j = array(i + 12)
        st = []
        for _ in range(m):
            c7, _, s7 = struct.unpack_from('<HHI', x, j)
            assert c7 == 7 and s7 == 17, ('XFS info', hex(j))
            st.append((struct.unpack_from('<I', x, j + 12)[0], x[j + 20]))
            j += 4 + s7
        out.append(st)
        i += 4 + size
    assert i == len(x), 'XFS parts states: trailing bytes'
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


def partsvis(emd, donor_xfs, model_groups, word=SPAWN_STATE_WORD, eyelid=()):
    """Gogmazios-style visibility states in the donor's state layout (Kushala: 0 base, 1/6 eyelid, 2-4 / 7-9
    break pairs intact / broken, 5 / 10 tail intact / severed, 11 empty), filled from the 4U rows by role.
    Every value is the group's full 4U evaluation (all its rows) at the spawn state word, intact and unsevered,
    except the one break / sever the state stands for.
    eyelid: the monster's eyelid groups -> state 1 hidden (open) / state 6 shown (closed), as GU em024_00's group 1
    (4U em031 / em001 eyelid group 1 = cond 0 mode 1; em089's eyelid group 12 = cond 11 mode 1, issue #11). Without
    them states 1 / 6 stay empty and the eyes never close (dead Gogmazios)."""
    rows = part_rows(emd)
    groups = sorted(set(model_groups) | {g for g, *_ in rows})
    eyelid = sorted(eyelid)
    assert set(eyelid) <= set(groups), 'eyelid group not in the model'
    breaks = {}                                       # break record -> groups
    for g, c, m, p, t in rows:
        if c == 6 and g not in breaks.get(p, []): breaks.setdefault(p, []).append(g)
    sever = sorted({g for g, c, m, p, t in rows if c == 1 and p == 1})      # tail
    slots = sorted(breaks)[:3]
    in_slot = {g for p in slots for g in breaks[p]} | set(sever) | set(eyelid)
    vis = lambda g, **kw: row_visible(rows, g, word, **kw)
    base = [(g, vis(g)) for g in groups if g not in in_slot]
    intact = [[(g, vis(g)) for g in breaks[p]] for p in slots]
    broken = [[(g, vis(g, broken={p})) for g in breaks[p]] for p in slots]
    while len(intact) < 3: intact.append([]); broken.append([])
    states = [base, [(g, False) for g in eyelid]] + intact + [[(g, vis(g)) for g in sever]] + \
             [[(g, True) for g in eyelid]] + broken + [[(g, vis(g, severed={1})) for g in sever], []]
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
    import paths
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    rom = RomFS(paths.GU_ROMFS)
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
