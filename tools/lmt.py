"""lmt.py : copy animations between MT LMT v67 motion lists (MH4U / MHGU, 32-bit; file offsets, relocated by the game
at load). Layout read off 4U em022 / em092 and GU em067_00 (tools/efl4u2gu.py lmt_events reads the same events):

  header      'LMT\\0', u16 version 67, u16 animation count, u32 animation offsets (0 = empty slot)
  animation   0x40 bytes: +0 track table, +4 track count, +8 frames, +0xc loop frame, +0x34 event block (0 = none)
  track       0x24 bytes: u8 buffer type, usage, joint type, bone id, f32 weight, +8 buffer size, +0xc buffer,
              +0x10 f32 reference frame[4], +0x20 bounds (0x20 bytes, 0 = none)
  event block 4 groups x 0x48 bytes: u16 remap[32], u32 count, u32 pointer to count x {u32 bits, u32 frames}

  splice(dst, src, [(src index, dst index)]) -> dst with those animations of src appended (dst slots must be empty)
"""
import struct

ANIM, TRACK, BOUNDS, GROUP, GROUPS = 0x40, 0x24, 0x20, 0x48, 4


def anims(d):
    assert d[:4] == b'LMT\0' and struct.unpack_from('<H', d, 4)[0] == 67, 'not an LMT v67'
    n = struct.unpack_from('<H', d, 6)[0]
    return list(struct.unpack_from('<%dI' % n, d, 8))


def blocks(d, o):
    """an animation's data: [(offset, size)] of its header, track table, buffers, bounds, event block and lists"""
    out = [(o, ANIM)]
    tr, tc = struct.unpack_from('<II', d, o)
    if tc:
        out.append((tr, TRACK * tc))
    for k in range(tc):
        t = tr + TRACK * k
        size, buf = struct.unpack_from('<II', d, t + 8)
        if buf: out.append((buf, size))
        bnd = struct.unpack_from('<I', d, t + 0x20)[0]
        if bnd: out.append((bnd, BOUNDS))
    ev = struct.unpack_from('<I', d, o + 0x34)[0]
    if ev:
        out.append((ev, GROUP * GROUPS))
        for g in range(GROUPS):
            cnt, ptr = struct.unpack_from('<II', d, ev + GROUP * g + 0x40)
            if ptr and cnt: out.append((ptr, 8 * cnt))
    for a, s in out:
        assert 0 < a and a + s <= len(d), 'pointer out of the file'
    return out


def _view(d, o):
    """the animation as offset-free content (for the copy check)"""
    tr, tc = struct.unpack_from('<II', d, o)
    head = bytearray(d[o:o + ANIM]); head[0:4] = bytes(4); head[0x34:0x38] = bytes(4)
    v = [bytes(head)]
    for k in range(tc):
        t = bytearray(d[tr + TRACK * k:tr + TRACK * (k + 1)])
        size, buf = struct.unpack_from('<II', t, 8)
        bnd = struct.unpack_from('<I', t, 0x20)[0]
        t[0xc:0x10] = bytes(4); t[0x20:0x24] = bytes(4)
        v += [bytes(t), d[buf:buf + size] if buf else b'-', d[bnd:bnd + BOUNDS] if bnd else b'-']
    ev = struct.unpack_from('<I', d, o + 0x34)[0]
    if ev:
        for g in range(GROUPS):
            grp = bytearray(d[ev + GROUP * g:ev + GROUP * (g + 1)])
            cnt, ptr = struct.unpack_from('<II', grp, 0x40)
            grp[0x44:0x48] = bytes(4)
            v += [bytes(grp), d[ptr:ptr + 8 * cnt] if ptr else b'-']
    return v


def splice(dst, src, pairs):
    out = bytearray(dst)
    sa, da = anims(src), anims(dst)
    for si, di in pairs:
        assert sa[si] and not da[di], (si, di, 'source empty or target slot used')
        reloc = {}
        for a, s in sorted(set(blocks(src, sa[si]))):
            out += bytes(-len(out) % 16)
            reloc[a] = len(out)
            out += src[a:a + s]
        o = reloc[sa[si]]
        tr, tc = struct.unpack_from('<II', src, sa[si])
        if tc: struct.pack_into('<I', out, o, reloc[tr])
        for k in range(tc):
            t = reloc[tr] + TRACK * k
            buf, bnd = struct.unpack_from('<I', out, t + 0xc)[0], struct.unpack_from('<I', out, t + 0x20)[0]
            if buf: struct.pack_into('<I', out, t + 0xc, reloc[buf])
            if bnd: struct.pack_into('<I', out, t + 0x20, reloc[bnd])
        ev = struct.unpack_from('<I', src, sa[si] + 0x34)[0]
        if ev:
            struct.pack_into('<I', out, o + 0x34, reloc[ev])
            for g in range(GROUPS):
                p = reloc[ev] + GROUP * g + 0x44
                ptr = struct.unpack_from('<I', out, p)[0]
                if ptr and struct.unpack_from('<I', out, p - 4)[0]: struct.pack_into('<I', out, p, reloc[ptr])
        struct.pack_into('<I', out, 8 + 4 * di, o)
    out += bytes(-len(out) % 16)
    res = bytes(out)
    for si, di in pairs:                       # every copied animation reads back the same through its new pointers
        assert _view(res, anims(res)[di]) == _view(src, sa[si]), (si, di)
        blocks(res, anims(res)[di])
    for i, o in enumerate(da):                 # the destination's own animations are untouched
        if o: assert _view(res, o) == _view(dst, o), i
    return res
