"""dt_convert.py : build MHGU dtbase / dttune for a 4U monster from a GU donor file, by editing the donor's loaded
object inside the emulated game (GU loader -> edit -> GU writer, tools/guemu.py). Run with the scratch venv.

  dt_convert.py validate                 rebuild GU Teostra and Rathian from 4U data with Kushala as donor, diff
  dt_convert.py build EMNNN DONOR OUTDIR

Only mappings that a vote over the 40 monsters present in both games supports (tools/dt_vote.py, dump/dtmap/)
are applied; everything else stays the donor's. Rules: (object field, 4U file, header word or offset, size rule).
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
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


def ptrs_of(u):
    return emdata4u_ptrs(u)


def emdata4u_ptrs(u):
    out = {}
    for w in range(2, 48):
        v = struct.unpack_from('<I', u, 4 * w)[0]
        if 4 * 48 <= v < len(u):
            out[w] = v
    return out


def convert(kind, donor_bytes, d4, log=None):
    loader, vt, reset = gu_schema.KINDS[kind]
    applied = []

    def modify(uc, st):
        obj = guemu.OBJ
        for off, (fk, h) in SCALARS[kind].items():
            uc.mem_write(obj + off, d4[fk][h:h + 4])
            applied.append('scalar +%#x <- %s+%#x' % (off, fk, h))
        for off, (fk, w, rule, cnt, esz) in BLOCKS[kind].items():
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
    out, err = guemu.load_modify_write(loader, WRITER[kind], vt, donor_bytes, modify,
                                       alloc=gu_schema.ALLOC, skip={reset})
    if log is not None: log.extend(applied)
    return out


def gu_file(rom, gu, kind):
    d = rom.read('/nativeNX/arc/enemy/%s.arc' % gu)
    return [arc_read(d, e) for e in arc_entries(d) if e[1] == GU_TYPE[kind]][0]


def validate():
    rom = RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
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
        rom = RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
        d4 = emdata4u.load_4u(sys.argv[2]); os.makedirs(sys.argv[4], exist_ok=True)
        for kind in ('dtbase', 'dttune'):
            log = []
            out = convert(kind, gu_file(rom, sys.argv[3], kind), d4, log)
            open(os.path.join(sys.argv[4], kind + '.bin'), 'wb').write(out)
            print(kind, len(out), 'bytes'); [print('   ', l) for l in log]
