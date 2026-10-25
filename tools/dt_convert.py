"""dt_convert.py : build MHGU dtbase / dttune for a 4U monster from a GU donor file, by editing the donor's loaded
object inside the emulated game (GU loader -> edit -> GU writer, tools/guemu.py). Run with the scratch venv.

  dt_convert.py validate                 rebuild GU Teostra and Rathian from 4U data with Kushala as donor, diff
  dt_convert.py build EMNNN DONOR OUTDIR [--sensor]    (--sensor: also the RECORDS tables, the 4U sensor)

Only mappings that a vote over the 40 monsters present in both games supports (tools/dt_vote.py, dump/dtmap/)
are applied; everything else stays the donor's. Rules: (object field, 4U file, header word or offset, size rule).
A block the 4U monster does not have is dropped from the donor's (ABSENT), as GU files without it carry it.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
sys.path.insert(0, paths.GU_PY)
import guemu, gu_schema, emdata4u
from romfs import RomFS
from arc import arc_entries, arc_read

WRITER = {'dtbase': 0x531D4, 'dttune': 0x57068}
GU_TYPE = {'dtbase': 0x59D9C3DA, 'dttune': 0x48E8AC29}

# scalars: object offset -> (4U file, header byte offset); votes 30-40 of 40
SCALARS = {
    'dtbase': {0x64: ('emd', 0x0C), 0x68: ('emd', 0x10), 0x6C: ('emd', 0x30), 0x98: ('emd', 0x6C),
               0x9C: ('emd', 0x70), 0xA0: ('emd', 0x14), 0xA4: ('emd', 0x78), 0xA8: ('emd', 0x7C)},
    'dttune': {0x64: ('etd', 0x10), 0xE0: ('etd', 0x8C), 0xE4: ('etd', 0x90), 0xE8: ('etd', 0x94),
               0xEC: ('emd', 0x14), 0xF0: ('etd', 0x9C)},
}
# blocks: object pointer field -> (4U file, header word, size rule, count field, element size)
#   size rule: int = copy that many bytes; 'gap' = up to the next header pointer
BLOCKS = {
    'dtbase': {0x70: ('emd', 13, 32, None, 0),   # 39/40
               0x74: ('emd', 38, 64, None, 0),   # 22/40
               0x84: ('emd', 20, 52, None, 0),   # 34/40
               0x88: ('emd', 21, 52, None, 0),   # 36/40
               0x8C: ('emd', 22, 4, None, 0),    # 39/40
               0xAC: ('emd', 43, 56, 0xC0, 28)}, # 39/40
    'dttune': {0x68: ('etd', 5, 80, None, 0),    # 29/40 exact, 98.6 % bytes: per-PART table, 8 x 10 B {u16 part HP,
                                                 # u8 levels, u8, u8, u8, u16 2nd-level HP / 0xffff, u16 kind}
                                                 # (missed by the vote; was Kushala's part HP / breaks)
               0x7c: ('etd', 10, 16, None, 0),   # 37/40: rows of 4 f32 thresholds; GU size = 16 x header
                                                 # byte +0x0a (rows), donor count kept -> only row 0 is Gogmazios'
               0x70: ('etd', 7, 80, None, 0),    # 17/40 exact, the rest retuned
               0x74: ('etd', 8, 80, None, 0),    # 16/40
               # 0x88 <- etd word 13 (18/40) left out: the writer reads a loop count from this block and 4U's
               # values make it stop early (bisected: output 379 of 1463 bytes)
               0x98: ('etd', 17, 16, None, 0),   # 39/40
               0x9C: ('etd', 18, 12, None, 0),   # 40/40
               0xA0: ('etd', 19, 12, None, 0),   # 39/40
               0xA4: ('etd', 20, 12, None, 0),   # 39/40
               0xAC: ('etd', 22, 12, None, 0),   # 36/40
               0xB8: ('etd', 25, 14, None, 0),   # 32/40 (first 14 bytes of the 4U block)
               0xC8: ('etd', 29, 'gap', 0xFF, 24)},  # 23/40 exact, GU size == 4U gap: the 24-byte part table
}
# record tables (opt-in, build --sensor): object pointer field -> (4U file, header word, 4U record size, count field,
# GU record size); the 4U records end at an s32 0xffff. 0x78 = the sensor ("eye") table GU 0x71144 reads at index
# ai+0x249 (sensor 0xc3144: near radius = auto notice): GU record = the 4U record with two u16 (eye angle offsets, 0 in
# every GU file) after the s32 joint; over the 64 records of the shared monsters joint 63 and range 61 are equal, near /
# angles partly retuned by GU. Not in the vote (record size differs). Opt-in so the files built before stay as they are.
RECORDS = {'dttune': {0x78: ('etd', 9, 28, 0xF9, 32)}}
# blocks dropped when the 4U word is absent (2026-10-25, Dalamadur on Kushala kept Kushala's slope fit, ailments and
# stamina): object pointer field -> (4U file, header word, gate bytes the loader reads = what GU files without the
# block hold). C: each field is null in GU files with exactly these gates (ailments / +0xc8 / +0xcc: em012, em084,
# em087; stamina, +0xa8: 13 monsters; dtbase +0xac: 30; +0x7c: 20), and the word / field pairs are the vote's, plus
# +0x7c = emd word 40 (4U em001 word 40 == GU em001_00 +0x7c: struct {records, u8 shift, 3 f32} and the 44-byte
# joint records; read by 0xc1d88, eased by 0xa8724, turned by the joint callback 0xab1a0). Null-safe readers: the
# slope fit 0xc1d88 / 0xa7ff8, stamina 0xbd260, ailments 0xa235c / 0xa2394 (4U: 0x93fcc4 likewise never builds up).
ABSENT = {
    'dtbase': {0x7C: ('emd', 40, {0xBD: 0}),                                 # slope fit (Dalamadur: corpse neck)
               0xAC: ('emd', 43, {0xC0: 0})},                                # joint points
    'dttune': {0x94: ('etd', 16, {0xF4: 0, 0xFC: 0, 0xFD: 0, 0xFE: 0}),      # stamina (+0xf4 = its second table)
               0x98: ('etd', 17, {0x114: 1}), 0x9C: ('etd', 18, {0x115: 1}),  # ailment buildups
               0xA0: ('etd', 19, {0x116: 1}), 0xA4: ('etd', 20, {0x117: 1}),
               0xA8: ('etd', 21, {0x118: 1}), 0xB0: ('etd', 23, {0x11A: 1}), 0xB4: ('etd', 24, {0x11B: 1}),
               0xBC: ('etd', 26, {0x11D: 1}), 0xC8: ('etd', 29, {0xFF: 0}), 0xCC: ('etd', 30, {0x122: 1})},
}
GATE32 = {0xF4}          # gates that are pointers (4 bytes), the rest are bytes
# 4U bytes over the start of a donor block of the same layout: field -> (4U file, header word, bytes). Rage +0x8c:
# u16 threshold, u16 duration, then multipliers (4U etd word 14 == GU +0x8c[0:56] for Rathian, Teostra, Kushala; GU's
# bytes 56..123 have no 4U counterpart and stay). Read by 0x82cd4 / 0xbcf00 / 0xc05a8.
PREFIX = {'dttune': {0x8C: ('etd', 14, 56)}}
# focus points (c83e4: joint A + offset, joint B + offset, radius; 36-byte records closed by 0xffff), 4U etd word 33:
# both 72-byte GU blocks = records 0 and 1 (Kushala: GU em024_00 +0xd4 == +0xd8 == 4U em031 word 33[0:72]); a monster
# with one record (Dalamadur: head joint 5 / tail 156, B = bone 0, radius 1000) gets it twice
FOCUS = {'dttune': (0xD4, 0xD8)}
FOCUS_WORD, FOCUS_REC = 33, 36


def ptrs_of(u):
    return emdata4u_ptrs(u)


def emdata4u_ptrs(u):
    out = {}
    for w in range(2, 48):
        v = struct.unpack_from('<I', u, 4 * w)[0]
        if 4 * 48 <= v < len(u):
            out[w] = v
    return out


def block_at(u, fk, w):
    """file offset of the block of 4U header word w, None when the monster has none"""
    p = emdata4u_ptrs(u).get(w)
    raw = struct.unpack_from('<I', u, 4 * w)[0]
    if p is None and fk == 'etd' and 0x24 <= raw < len(u):
        p = raw              # etd headers are shorter than 48 words: word 5 (part table) points at 0xa0
    return p


def focus_want(u):
    """the 72 bytes both focus blocks get (4U etd word 33 records 0 and 1), None to keep the donor's"""
    p = block_at(u, 'etd', FOCUS_WORD)
    recs = []
    while p is not None and p + FOCUS_REC <= len(u) and struct.unpack_from('<H', u, p)[0] != 0xffff and len(recs) < 2:
        recs.append(u[p:p + FOCUS_REC]); p += FOCUS_REC
    return recs[0] + recs[-1] if recs else None


def ptr_fields(kind):
    """the object's pointer fields (blocks and tables) the checks compare"""
    return range(0x68, 0xB8, 4) if kind == 'dtbase' else range(0x68, 0xE0, 4)


def convert(kind, donor_bytes, d4, log=None, records=False):
    loader, vt, reset = gu_schema.KINDS[kind]
    applied = []

    def modify_records(uc, st):
        for off, (fk, w, size4, cnt, size) in RECORDS.get(kind, {}).items():
            u = d4[fk]; p = emdata4u_ptrs(u).get(w)
            cur = struct.unpack_from('<I', bytes(uc.mem_read(guemu.OBJ + off, 4)))[0]
            if p is None or not cur:
                applied.append('records +%#x kept (4U word %d %s, donor %s)' % (
                    off, w, 'absent' if p is None else 'ok', 'has it' if cur else 'lacks it'))
                continue
            recs = []
            while p + size4 <= len(u) and struct.unpack_from('<i', u, p)[0] != 0xffff:
                recs.append(u[p:p + 4] + bytes(size - size4) + u[p + 4:p + size4]); p += size4
            new = st['alloc'](max(1, len(recs)) * size)
            uc.mem_write(new, b''.join(recs))
            uc.mem_write(guemu.OBJ + off, struct.pack('<I', new))
            uc.mem_write(guemu.OBJ + cnt, bytes([len(recs)]))
            applied.append('records +%#x <- %s word %d (%d x %d bytes, count +%#x)' % (off, fk, w, len(recs), size, cnt))

    dropped, focused, nulls = set(), set(), {}

    def modify(uc, st):
        obj = guemu.OBJ
        u32 = lambda a: struct.unpack_from('<I', bytes(uc.mem_read(a, 4)))[0]
        size = dict(st['blocks'])
        for off, (fk, h) in SCALARS[kind].items():
            uc.mem_write(obj + off, d4[fk][h:h + 4])
            applied.append('scalar +%#x <- %s+%#x' % (off, fk, h))
        for off, (fk, w, gates) in ABSENT.get(kind, {}).items():
            if block_at(d4[fk], fk, w) is not None or not u32(obj + off):
                continue
            uc.mem_write(obj + off, bytes(4))
            for g, v in gates.items():
                uc.mem_write(obj + g, struct.pack('<I', v) if g in GATE32 else bytes([v]))
            dropped.add(off)
            applied.append('block +%#x dropped (4U word %d absent; gates %s)' % (
                off, w, ' '.join('+%#x=%d' % gv for gv in gates.items())))
        for off, (fk, w, n) in PREFIX.get(kind, {}).items():
            p, cur = block_at(d4[fk], fk, w), u32(obj + off)
            if p is None or not cur or size.get(cur, 0) < n:
                applied.append('block +%#x kept (4U word %d %s)' % (off, w, 'absent' if p is None else 'ok'))
                continue
            uc.mem_write(cur, d4[fk][p:p + n])
            applied.append('block +%#x[0:%d] <- %s word %d (donor bytes %d..%d kept)' % (off, n, fk, w, n,
                                                                                     size[cur] - 1))
        for off in FOCUS.get(kind, ()):
            want, cur = focus_want(d4['etd']), u32(obj + off)
            if want is None or not cur or size.get(cur, 0) != len(want):
                applied.append('block +%#x kept (4U word %d, donor size %d)' % (off, FOCUS_WORD, size.get(cur, 0)))
                continue
            uc.mem_write(cur, want)
            focused.add(off)
            applied.append('block +%#x <- etd word %d records 0 / 1 (joints %d %d / %d %d)' % (
                off, FOCUS_WORD, *struct.unpack_from('<i12xi16xi12xi', want)))
        for off, (fk, w, rule, cnt, esz) in BLOCKS[kind].items():
            if off in dropped:
                continue
            u = d4[fk]; ptrs = emdata4u_ptrs(u)
            raw = struct.unpack_from('<I', u, 4 * w)[0]
            if w not in ptrs and 0x24 <= raw < len(u) and fk == 'etd':
                ptrs[w] = raw        # etd headers are shorter than 48 words: word 5 (part table) points at 0xa0
            cur = struct.unpack_from('<I', bytes(uc.mem_read(obj + off, 4)))[0]
            if w not in ptrs or not cur:
                applied.append('block +%#x kept (4U word %d %s, donor %s)' % (off, w, 'absent' if w not in ptrs else 'ok',
                                                                              'has it' if cur else 'lacks it'))
                continue
            p = ptrs[w]
            if rule == 'gap':
                n = min([q for q in ptrs.values() if q > p] + [len(u)]) - p
            else:
                n = rule
            if cnt is not None:
                n -= n % esz
                uc.mem_write(obj + cnt, bytes([n // esz]))
            new = st['alloc'](n)
            uc.mem_write(new, u[p:p + n])
            uc.mem_write(obj + off, struct.pack('<I', new))
            applied.append('block +%#x <- %s word %d (%d bytes%s)' % (off, fk, w, n,
                                                                      ', count +%#x = %d' % (cnt, n // esz) if cnt is not None else ''))
        if records:
            modify_records(uc, st)
        nulls.update((off, not u32(obj + off)) for off in ptr_fields(kind))
    out, err = guemu.load_modify_write(loader, WRITER[kind], vt, donor_bytes, modify,
                                       alloc=gu_schema.ALLOC, skip={reset})
    check(kind, out, d4, dropped, focused, nulls)
    if log is not None: log.extend(applied)
    return out


def check(kind, out, d4, dropped, focused, nulls):
    """the written file loads back with the edits: dropped blocks null, every other block as present as before the
    writer (a wrong gate shifts the stream), the 4U prefix / focus bytes in place (focus: only the blocks written;
    a donor block of another size is kept, e.g. Tigerstripe's)"""
    loader, vt, reset = gu_schema.KINDS[kind]
    st, err, obj, uc = guemu.run(loader, vt, out, alloc=gu_schema.ALLOC, skip={reset})
    u32 = lambda o: struct.unpack_from('<I', obj, o)[0]
    bad = [] if st['pos'] == len(out) else ['loader read %d of %d bytes (%s)' % (st['pos'], len(out), err)]
    bad += ['+%#x %s after reload' % (o, 'null' if not u32(o) else 'set') for o, was in nulls.items() if was != (not u32(o))]
    bad += ['+%#x not dropped' % o for o in dropped if u32(o)]
    for off, (fk, w, n) in PREFIX.get(kind, {}).items():
        p = block_at(d4[fk], fk, w)
        if p is not None and u32(off) and bytes(uc.mem_read(u32(off), n)) != d4[fk][p:p + n]:
            bad.append('+%#x prefix differs' % off)
    for off in focused:
        want = focus_want(d4['etd'])
        if bytes(uc.mem_read(u32(off), len(want))) != want:
            bad.append('+%#x focus differs' % off)
    if bad:
        raise RuntimeError('%s check: %s' % (kind, '; '.join(bad)))


def gu_file(rom, gu, kind):
    d = rom.read('/nativeNX/arc/enemy/%s.arc' % gu)
    return [arc_read(d, e) for e in arc_entries(d) if e[1] == GU_TYPE[kind]][0]


def validate():
    rom = RomFS(paths.GU_ROMFS)
    for kind in ('dtbase', 'dttune'):
        donor = gu_file(rom, 'em024_00', kind)
        for em4, gu in (('em032', 'em027_00'), ('em001', 'em001_00'), ('em031', 'em024_00')):
            ref = gu_file(rom, gu, kind)
            out = convert(kind, donor, emdata4u.load_4u(em4))
            same = sum(a == b for a, b in zip(out, ref))
            dn = sum(a == b for a, b in zip(donor, ref))
            print('%-7s %s from donor em024_00: size %d vs GU %d, equal bytes %.1f%% (donor alone %.1f%%)' % (
                kind, gu, len(out), len(ref), 100.0 * same / len(ref), 100.0 * dn / len(ref)))


if __name__ == '__main__':
    if sys.argv[1] == 'validate':
        validate()
    elif sys.argv[1] == 'build':
        rom = RomFS(paths.GU_ROMFS)
        d4 = emdata4u.load_4u(sys.argv[2]); os.makedirs(sys.argv[4], exist_ok=True)
        for kind in ('dtbase', 'dttune'):
            log = []
            out = convert(kind, gu_file(rom, sys.argv[3], kind), d4, log, records='--sensor' in sys.argv[5:])
            open(os.path.join(sys.argv[4], kind + '.bin'), 'wb').write(out)
            print(kind, len(out), 'bytes'); [print('   ', l) for l in log]
