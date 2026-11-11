"""lmt.py : copy animations between MT LMT v67 motion lists (MH4U / MHGU, 32-bit; file offsets, relocated by the game
at load). Layout read off 4U em022 / em092 and GU em067_00 (tools/efl4u2gu.py lmt_events reads the same events):

  header      'LMT\\0', u16 version 67, u16 animation count, u32 animation offsets (0 = empty slot)
  animation   0x40 bytes: +0 track table, +4 track count, +8 frames, +0xc loop frame, +0x34 event block (0 = none)
  track       0x24 bytes: u8 buffer type, usage, joint type, bone id, f32 weight, +8 buffer size, +0xc buffer,
              +0x10 f32 reference frame[4], +0x20 bounds (0x20 bytes, 0 = none)
  event block 4 groups x 0x48 bytes: u16 remap[32], u32 count, u32 pointer to count x {u32 bits, u32 frames}

  splice(dst, src, [(src index, dst index)]) -> dst with those animations of src appended (dst slots must be empty)
  with_tracks(dst, src, [(src index, dst index)]) -> dst rebuilt, those animations with src's tracks and dst's event block
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


def _track_keys(d, o):
    """an animation's tracks as (usage, joint type, bone)"""
    tr, tc = struct.unpack_from('<II', d, o)
    return [d[tr + TRACK * k + 1:tr + TRACK * k + 4] for k in range(tc)]


def with_tracks(dst, src, pairs):
    """dst rebuilt from its parts: the animations of pairs [(src index, dst index)] take src's tracks (table, buffers, bounds), everything else stays dst's, event blocks too.
    Nothing of the replaced tracks is left behind. The same motion in two forms: frames, loop and track keys must be equal (asserted). For a monster whose motions the other game
    stores finer, Capcom's conversion of the same animation (Tidal Najarala: 4U 7-bit quaternions, GU 11-bit)."""
    sa, da = anims(src), anims(dst)
    use = {}
    for si, di in pairs:
        assert sa[si] and da[di], (si, di, 'empty slot')
        assert src[sa[si] + 8:sa[si] + 16] == dst[da[di] + 8:da[di] + 16], (si, di, 'frames or loop differ')
        assert _track_keys(src, sa[si]) == _track_keys(dst, da[di]), (si, di, 'track keys differ')
        use[di] = si
    out = bytearray(dst[:8 + 4 * len(da)])

    def put(data):
        out.extend(bytes(-len(out) % 16))
        at = len(out)
        out.extend(data)
        return at

    for i, o in enumerate(da):
        if not o: continue
        tab, so = (src, sa[use[i]]) if i in use else (dst, o)
        a = put(dst[o:o + ANIM])
        struct.pack_into('<I', out, 8 + 4 * i, a)
        tr, tc = struct.unpack_from('<II', tab, so)
        if tc:
            t0 = put(tab[tr:tr + TRACK * tc])
            struct.pack_into('<I', out, a, t0)
            for k in range(tc):
                t = t0 + TRACK * k
                size, buf = struct.unpack_from('<II', out, t + 8)
                bnd = struct.unpack_from('<I', out, t + 0x20)[0]
                if buf: struct.pack_into('<I', out, t + 0xc, put(tab[buf:buf + size]))
                if bnd: struct.pack_into('<I', out, t + 0x20, put(tab[bnd:bnd + BOUNDS]))
        ev = struct.unpack_from('<I', dst, o + 0x34)[0]
        if ev:
            e0 = put(dst[ev:ev + GROUP * GROUPS])
            struct.pack_into('<I', out, a + 0x34, e0)
            for g in range(GROUPS):
                cnt, ptr = struct.unpack_from('<II', dst, ev + GROUP * g + 0x40)
                if ptr and cnt: struct.pack_into('<I', out, e0 + GROUP * g + 0x44, put(dst[ptr:ptr + 8 * cnt]))
    out.extend(bytes(-len(out) % 16))
    res = bytes(out)
    ra = anims(res)
    tracks = lambda v, n: v[1:1 + 3 * n]        # _view: header, 3 entries per track, then the event groups
    for i, o in enumerate(da):                  # every animation reads back through its new pointers
        if not o: continue
        blocks(res, ra[i])
        vr, vd = _view(res, ra[i]), _view(dst, o)
        n = struct.unpack_from('<I', dst, o + 4)[0]
        assert vr[0] == vd[0] and vr[1 + 3 * n:] == vd[1 + 3 * n:], (i, 'header or events changed')
        want = _view(src, sa[use[i]]) if i in use else vd
        assert tracks(vr, n) == tracks(want, n), (i, 'tracks')
    return res
