"""tex.py : MT Framework rTexture (TEX) for MH4U (3DS, version 0xA5/0xA6) and MHGU (Switch, version 0xA0).

  tex.py info FILE.tex
  tex.py topng FILE.tex OUT.png [mip]       decode (4U: ETC1/ETC1A4/RGBA..., GU: BC1/3/4/5/RGBA8) to PNG
  tex.py togu IN.tex|IN.png OUT.tex [--fmt bc3|bc1|bc4|bc5|rgba8] [--mips N]
                                           encode an MHGU texture (Tegra X1 block-linear, full mip chain)
  tex.py selftest                          round-trip every texture of a GU monster arc (container + swizzle)

Header (both): 'TEX\\0', tier0 (version:8, unk:6, unk:14, type:4), tier1 (mips:6, width:13, height:13),
u8 faces, u8 format, u16 depth.  4U: then mips x u32 offsets, data (3DS 8x8 tiles).
GU: then u32 data size, mips x u32 offsets, data (block-linear, each mip with its own block height).
"""
import struct, sys
import numpy as np

# ---------------------------------------------------------------- header

FMT_GU = {0x13: 'bc1', 0x14: 'bc1', 0x17: 'bc3', 0x19: 'bc4', 0x1F: 'bc5', 0x07: 'rgba8'}
GU_FMT = {'bc1': 0x13, 'bc3': 0x17, 'bc4': 0x19, 'bc5': 0x1F, 'rgba8': 0x07}
BLOCK_BYTES = {'bc1': 8, 'bc4': 8, 'bc3': 16, 'bc5': 16}


def parse(t):
    magic, t0, t1, faces, fmt, depth = struct.unpack_from('<4sIIBBH', t, 0)
    assert magic == b'TEX\0', magic
    h = dict(version=t0 & 0xFF, unk0=(t0 >> 8) & 0x3F, unk1=(t0 >> 14) & 0x3FFF, type=t0 >> 28,
             mips=t1 & 0x3F, width=(t1 >> 6) & 0x1FFF, height=t1 >> 19, faces=faces, fmt=fmt, depth=depth,
             tier0=t0)
    if h['type'] == 6: raise SystemExit('cube maps not supported')
    if h['version'] == 0xA0:
        size = struct.unpack_from('<I', t, 16)[0]
        h['offsets'] = list(struct.unpack_from('<%dI' % h['mips'], t, 20))
        start = 20 + 4 * h['mips']
        h['data'] = t[start:start + size]
    elif h['version'] in (0xA5, 0xA6):
        h['offsets'] = list(struct.unpack_from('<%dI' % h['mips'], t, 16))
        start = 16 + 4 * h['mips']
        h['data'] = t[start:]
        h['offsets'] = [o - start for o in h['offsets']] if h['offsets'][0] == start else h['offsets']
    else:
        raise SystemExit('unsupported TEX version %#x' % h['version'])
    return h


def gu_header(width, height, mips, fmt, offsets, size, unk1=2):
    t0 = 0xA0 | (unk1 << 14) | (2 << 28)
    t1 = mips | (width << 6) | (height << 19)
    return struct.pack('<4sIIBBH', b'TEX\0', t0, t1, 1, fmt, 1) + struct.pack('<I', size) + \
        struct.pack('<%dI' % mips, *offsets)

# ---------------------------------------------------------------- 3DS (ETC1 / ETC1A4 / raw), 8x8 tiles

ETC_MOD = np.array([[2, 8, -2, -8], [5, 17, -5, -17], [9, 29, -9, -29], [13, 42, -13, -42],
                    [18, 60, -18, -60], [24, 80, -24, -80], [33, 106, -33, -106], [47, 183, -47, -183]],
                   dtype=np.int32)


def etc1_blocks(words):
    """words: (n,) uint64 (3DS stores each ETC1 block little-endian) -> (n,4,4,3) uint8, [block][y][x]."""
    w = words.astype(np.uint64)
    hi = (w >> np.uint64(32)).astype(np.uint32)
    lo = (w & np.uint64(0xFFFFFFFF)).astype(np.uint32)
    diff = (hi >> 1) & 1
    flip = hi & 1
    cw1 = (hi >> 5) & 7
    cw2 = (hi >> 2) & 7

    def ch(shift):
        a = (hi >> (shift + 4)) & 0xF            # individual mode: 4-bit pairs
        b = (hi >> shift) & 0xF
        base5 = (hi >> (shift + 3)) & 0x1F         # differential: 5-bit base + 3-bit signed delta
        d = ((hi >> shift) & 7).astype(np.int32)
        d = np.where(d >= 4, d - 8, d)
        b5 = base5.astype(np.int32) + d
        c1 = np.where(diff == 1, (base5 << 3) | (base5 >> 2), (a << 4) | a).astype(np.int32)
        c2 = np.where(diff == 1, (b5 << 3) | (b5 >> 2), (b << 4) | b).astype(np.int32)
        return c1, c2

    r1, r2 = ch(24); g1, g2 = ch(16); b1, b2 = ch(8)
    base1 = np.stack([r1, g1, b1], -1)  # (n,3)
    base2 = np.stack([r2, g2, b2], -1)
    out = np.zeros((len(w), 4, 4, 3), np.uint8)
    for x in range(4):
        for y in range(4):
            i = x * 4 + y
            idx = (((lo >> (i + 16)) & 1) << 1 | ((lo >> i) & 1)).astype(np.int64)
            second = np.where(flip == 1, y >= 2, x >= 2)
            cw = np.where(second, cw2, cw1).astype(np.int64)
            base = np.where(second[:, None], base2, base1)
            m = ETC_MOD[cw, idx]
            out[:, y, x] = np.clip(base + m[:, None], 0, 255)
    return out


def untile_3ds(blocks4, width, height):
    """blocks4: (n,4,4,C) in 3DS order (8x8 tiles row by row, 2x2 blocks Z-order) -> (h,w,C)."""
    C = blocks4.shape[-1]
    tw, th = width // 8, height // 8
    b = blocks4.reshape(th, tw, 2, 2, 4, 4, C)          # tile row, tile col, by, bx, y, x
    img = b.transpose(0, 2, 4, 1, 3, 5, 6).reshape(height, width, C)
    return img


def decode_3ds(h, mip=0):
    w, hgt = max(8, h['width'] >> mip), max(8, h['height'] >> mip)
    d = h['data'][h['offsets'][mip]:]
    fmt = h['fmt']
    if fmt in (0x0B, 0x0C):
        n = (w // 4) * (hgt // 4)
        if fmt == 0x0B:
            words = np.frombuffer(d, '<u8', n)
            rgb = etc1_blocks(words)
            a = np.full(rgb.shape[:3] + (1,), 255, np.uint8)
        else:
            pairs = np.frombuffer(d, '<u8', 2 * n).reshape(n, 2)
            rgb = etc1_blocks(pairs[:, 1])
            aw = pairs[:, 0]
            a = np.zeros((n, 4, 4, 1), np.uint8)
            for x in range(4):
                for y in range(4):
                    v = ((aw >> np.uint64(4 * (x * 4 + y))) & np.uint64(0xF)).astype(np.uint8)
                    a[:, y, x, 0] = v * 17
        return untile_3ds(np.concatenate([rgb, a], -1), w, hgt)
    # uncompressed 3DS formats: 8x8 tiles with Morton order inside
    bpp = {0x01: 2, 0x02: 2, 0x03: 4, 0x04: 2, 0x05: 1, 0x07: 2, 0x10: 1, 0x11: 3}[fmt]
    raw = np.frombuffer(d, np.uint8, w * hgt * bpp).reshape(-1, 64, bpp)
    morton = np.zeros(64, np.int64)
    for i in range(64):
        x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
        y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
        morton[i] = y * 8 + x
    lin = np.zeros_like(raw); lin[:, morton] = raw
    tiles = lin.reshape(hgt // 8, w // 8, 8, 8, bpp).transpose(0, 2, 1, 3, 4).reshape(hgt, w, bpp)
    if fmt == 0x03:   # ABGR in memory -> RGBA
        return tiles[..., ::-1].copy()
    if fmt == 0x11:
        return np.concatenate([tiles[..., ::-1], np.full((hgt, w, 1), 255, np.uint8)], -1)
    if fmt in (0x05, 0x10):
        g = tiles[..., 0]; return np.stack([g, g, g, np.full_like(g, 255)], -1)
    if fmt == 0x07:
        return np.stack([tiles[..., 1]] * 3 + [tiles[..., 0]], -1)
    v = tiles[..., 0].astype(np.uint16) | (tiles[..., 1].astype(np.uint16) << 8)
    if fmt == 0x04:
        r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
        return np.stack([r * 255 // 31, g * 255 // 63, b * 255 // 31, np.full_like(v, 255)], -1).astype(np.uint8)
    if fmt == 0x01:
        return np.stack([((v >> s) & 15) * 17 for s in (12, 8, 4, 0)], -1).astype(np.uint8)
    if fmt == 0x02:
        r = (v >> 11) & 31; g = (v >> 6) & 31; b = (v >> 1) & 31; a = v & 1
        return np.stack([r * 255 // 31, g * 255 // 31, b * 255 // 31, a * 255], -1).astype(np.uint8)
    raise SystemExit('3DS format %#x not supported' % fmt)

# ---------------------------------------------------------------- Tegra X1 block linear

def div_up(a, b): return (a + b - 1) // b


def pow2_up(v):
    p = 1
    while p < v: p <<= 1
    return p


def block_height_log2(height_blocks):
    bh = min(16, pow2_up(div_up(height_blocks, 8)))
    return bh.bit_length() - 1


def mip_block_height(base_log2, h_blocks):
    """block height (in GOBs) used for one mip: shrink while the mip is shorter than half a block."""
    log2 = base_log2
    while log2 > 0 and h_blocks <= (8 << log2) // 2:
        log2 -= 1
    return 1 << log2


def bl_size(w, h, bpp, bh):
    return div_up(w * bpp, 64) * 64 * div_up(h, 8 * bh) * 8 * bh


def bl_offsets(w, h, bpp, bh):
    """byte offset of every (x, y) element (w x h, bpp bytes each) in a block-linear surface: (h, w)."""
    x = np.arange(w)[None, :] * bpp
    y = np.arange(h)[:, None]
    gobs_w = div_up(w * bpp, 64)
    gob = ((y // (8 * bh)) * gobs_w * bh * 512 + (x // 64) * bh * 512 + ((y % (8 * bh)) // 8) * 512)
    return gob + ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16)


def gu_layout(width, height, mips, fmt_name):
    """[(w_el, h_el, bpp, bh, offset, size)] per mip for an MHGU texture."""
    if fmt_name == 'rgba8':
        bpp, ew, eh = 4, width, height
    else:
        bpp, ew, eh = BLOCK_BYTES[fmt_name], div_up(width, 4), div_up(height, 4)
    base = block_height_log2(eh)
    out, off = [], 0
    for m in range(mips):
        if fmt_name == 'rgba8':
            w, h = max(1, width >> m), max(1, height >> m)
        else:
            w, h = div_up(max(1, width >> m), 4), div_up(max(1, height >> m), 4)
        bh = mip_block_height(base, h)
        size = bl_size(w, h, bpp, bh)
        out.append((w, h, bpp, bh, off, size))
        off += size
    return out


def deswizzle(data, w, h, bpp, bh):
    offs = bl_offsets(w, h, bpp, bh)
    buf = np.frombuffer(data, np.uint8)
    idx = offs[..., None] + np.arange(bpp)
    return buf[idx]                         # (h, w, bpp)


def swizzle(elems, bpp, bh):
    h, w = elems.shape[:2]
    out = np.zeros(bl_size(w, h, bpp, bh), np.uint8)
    offs = bl_offsets(w, h, bpp, bh)
    out[offs[..., None] + np.arange(bpp)] = elems
    return out.tobytes()

# ---------------------------------------------------------------- BCn

def _rgb565(c):
    return ((c[..., 0].astype(np.uint16) >> 3) << 11) | ((c[..., 1].astype(np.uint16) >> 2) << 5) | (c[..., 2].astype(np.uint16) >> 3)


def _unpack565(v):
    v = v.astype(np.int32)
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1)


def bc1_decode(blk, punchthrough=True):
    """blk: (n, 8) uint8 -> (n,4,4,4)"""
    c0 = blk[:, 0].astype(np.uint16) | blk[:, 1].astype(np.uint16) << 8
    c1 = blk[:, 2].astype(np.uint16) | blk[:, 3].astype(np.uint16) << 8
    p0, p1 = _unpack565(c0), _unpack565(c1)
    four = (c0 > c1) | (not punchthrough)
    p2 = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four[:, None], (p0 + 2 * p1) // 3, 0)
    pal = np.stack([p0, p1, p2, p3], 1)                              # (n,4,3)
    alpha = np.stack([np.full(len(blk), 255)] * 3 + [np.where(four, 255, 0)], 1)
    bits = blk[:, 4:8].copy().view('<u4')[:, 0]
    out = np.zeros((len(blk), 4, 4, 4), np.uint8)
    for i in range(16):
        k = ((bits >> (2 * i)) & 3).astype(np.int64)
        out[:, i // 4, i % 4, :3] = pal[np.arange(len(blk)), k]
        out[:, i // 4, i % 4, 3] = alpha[np.arange(len(blk)), k]
    return out


def bc4_decode(blk):
    """blk: (n, 8) -> (n,4,4) uint8"""
    a0 = blk[:, 0].astype(np.int32); a1 = blk[:, 1].astype(np.int32)
    pal = np.zeros((len(blk), 8), np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    gt = a0 > a1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(gt, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(gt, pal[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    pal[:, 6] = np.where(gt, pal[:, 6], 0); pal[:, 7] = np.where(gt, pal[:, 7], 255)
    bits = np.zeros(len(blk), np.uint64)
    for k in range(6): bits |= blk[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    out = np.zeros((len(blk), 4, 4), np.uint8)
    for i in range(16):
        k = ((bits >> np.uint64(3 * i)) & np.uint64(7)).astype(np.int64)
        out[:, i // 4, i % 4] = pal[np.arange(len(blk)), k]
    return out


def bc1_encode(px, alpha_cut=None):
    """px: (n,4,4,3/4) uint8 -> (n,8). Bounding-box endpoints along the luminance-weighted axis, 4-colour mode."""
    n = len(px)
    p = px[..., :3].reshape(n, 16, 3).astype(np.int32)
    mean = p.mean(1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', p - mean, p - mean)
    axis = np.ones((n, 3))
    for _ in range(8):  # power iteration for the principal axis
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-9)
    proj = np.einsum('nki,ni->nk', p - mean, axis)
    lo = (mean[:, 0] + axis * proj.min(1, keepdims=True)).clip(0, 255)
    hi = (mean[:, 0] + axis * proj.max(1, keepdims=True)).clip(0, 255)
    c0 = _rgb565(hi.astype(np.uint8)); c1 = _rgb565(lo.astype(np.uint8))
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = _unpack565(c0), _unpack565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3], 1)   # (n,4,3)
    d = ((p[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)          # (n,16,4)
    idx = d.argmin(-1).astype(np.uint32)
    eq = c0 == c1
    idx[eq] = 0
    bits = np.zeros(n, np.uint32)
    for i in range(16): bits |= idx[:, i] << np.uint32(2 * i)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0] = c0 & 0xFF; out[:, 1] = c0 >> 8; out[:, 2] = c1 & 0xFF; out[:, 3] = c1 >> 8
    out[:, 4:8] = bits.view(np.uint8).reshape(n, 4)
    return out


def bc4_encode(ch):
    """ch: (n,4,4) uint8 -> (n,8), 8-value mode with min/max endpoints."""
    n = len(ch)
    v = ch.reshape(n, 16).astype(np.int32)
    a0 = v.max(1); a1 = v.min(1)
    pal = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)], 1)
    idx = np.abs(v[:, :, None] - pal[:, None, :]).argmin(-1).astype(np.uint64)
    flat = a0 == a1
    idx[flat] = 0
    bits = np.zeros(n, np.uint64)
    for i in range(16): bits |= idx[:, i] << np.uint64(3 * i)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0] = a0; out[:, 1] = a1
    for k in range(6): out[:, 2 + k] = ((bits >> np.uint64(8 * k)) & np.uint64(0xFF)).astype(np.uint8)
    return out


def to_blocks(img):
    """(h,w,C) -> (hb*wb,4,4,C), padding to multiples of 4 by edge replication."""
    h, w = img.shape[:2]
    H, Wd = div_up(h, 4) * 4, div_up(w, 4) * 4
    if (H, Wd) != (h, w):
        img = np.pad(img, ((0, H - h), (0, Wd - w), (0, 0)), mode='edge')
    return img.reshape(H // 4, 4, Wd // 4, 4, -1).transpose(0, 2, 1, 3, 4).reshape(-1, 4, 4, img.shape[2])


def from_blocks(b, hb, wb):
    C = b.shape[-1]
    return b.reshape(hb, wb, 4, 4, C).transpose(0, 2, 1, 3, 4).reshape(hb * 4, wb * 4, C)


def bc_encode(img, fmt):
    b = to_blocks(img)
    if fmt == 'bc1': return bc1_encode(b)
    if fmt == 'bc3': return np.concatenate([bc4_encode(b[..., 3]), bc1_encode(b)], 1)
    if fmt == 'bc4': return bc4_encode(b[..., 0])
    if fmt == 'bc5': return np.concatenate([bc4_encode(b[..., 0]), bc4_encode(b[..., 1])], 1)
    raise ValueError(fmt)


def bc_decode(blk, fmt):
    if fmt == 'bc1': return bc1_decode(blk)
    if fmt == 'bc3':
        c = bc1_decode(blk[:, 8:], punchthrough=False); c[..., 3] = bc4_decode(blk[:, :8]); return c
    if fmt == 'bc4':
        g = bc4_decode(blk); return np.stack([g, g, g, np.full_like(g, 255)], -1)
    if fmt == 'bc5':
        r = bc4_decode(blk[:, :8]); g = bc4_decode(blk[:, 8:])
        return np.stack([r, g, np.zeros_like(r), np.full_like(r, 255)], -1)
    raise ValueError(fmt)

# ---------------------------------------------------------------- GU decode / encode

def decode_gu(h, mip=0):
    fmt = FMT_GU.get(h['fmt'])
    if fmt is None: raise SystemExit('GU format %#x not supported' % h['fmt'])
    lay = gu_layout(h['width'], h['height'], h['mips'], fmt)
    w, hh, bpp, bh, off, size = lay[mip]
    assert off == h['offsets'][mip], ('layout mismatch', mip, off, h['offsets'][mip])
    el = deswizzle(h['data'][off:off + size], w, hh, bpp, bh)
    W, H = max(1, h['width'] >> mip), max(1, h['height'] >> mip)
    if fmt == 'rgba8':
        return el[:H, :W]
    img = from_blocks(bc_decode(el.reshape(-1, bpp), fmt), hh, w)
    return img[:H, :W]


def mip_chain(img, mips):
    out = [img]
    for _ in range(1, mips):
        a = out[-1].astype(np.float32)
        h, w = a.shape[:2]
        if h > 1: a = (a[0:h - h % 2:2] + a[1:h - h % 2 + 1:2][:a[0:h - h % 2:2].shape[0]]) / 2
        if w > 1: a = (a[:, 0:w - w % 2:2] + a[:, 1:w - w % 2 + 1:2][:, :a[:, 0:w - w % 2:2].shape[1]]) / 2
        out.append(np.round(a).astype(np.uint8))
    return out


def full_mips(w, h):
    return max(w, h).bit_length()


def encode_gu(img, fmt='bc3', mips=None):
    """img (h,w,4) uint8 -> MHGU TEX bytes."""
    H, W = img.shape[:2]
    mips = mips or full_mips(W, H)
    lay = gu_layout(W, H, mips, fmt)
    data = bytearray()
    for (w, h, bpp, bh, off, size), m in zip(lay, mip_chain(img, mips)):
        assert len(data) == off
        if fmt == 'rgba8':
            el = m.reshape(h, w, 4)
        else:
            el = bc_encode(m, fmt).reshape(h, w, bpp)
        data += swizzle(el, bpp, bh)
    return gu_header(W, H, mips, GU_FMT[fmt], [l[4] for l in lay], len(data)) + bytes(data)


def reencode_gu_container(t):
    """GU TEX -> deswizzle every mip -> swizzle again -> rebuild header. Must equal the input."""
    h = parse(t)
    fmt = FMT_GU[h['fmt']]
    lay = gu_layout(h['width'], h['height'], h['mips'], fmt)
    data = bytearray()
    for w, hh, bpp, bh, off, size in lay:
        el = deswizzle(h['data'][off:off + size], w, hh, bpp, bh)
        data += swizzle(el, bpp, bh)
    return gu_header(h['width'], h['height'], h['mips'], h['fmt'], [l[4] for l in lay], len(data),
                     unk1=h['unk1']) + bytes(data)


def decode(t, mip=0):
    h = parse(t)
    return decode_gu(h, mip) if h['version'] == 0xA0 else decode_3ds(h, mip)


def save_png(img, path):
    from PIL import Image
    Image.fromarray(np.ascontiguousarray(img), 'RGBA' if img.shape[2] == 4 else 'RGB').save(path)


def selftest(arcpath='/nativeNX/arc/enemy/em001_00.arc'):
    import paths
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    from arc import arc_entries, arc_read
    r = RomFS(paths.GU_ROMFS)
    d = r.read(arcpath)
    ok = bad = skip = 0
    for e in arc_entries(d):
        if e[1] != 0x241F5DEB: continue
        t = arc_read(d, e)
        h = parse(t)
        if h['fmt'] not in FMT_GU or h['type'] == 6: skip += 1; continue
        if reencode_gu_container(t) == t: ok += 1
        else: bad += 1; print('MISMATCH', e[0], hex(h['fmt']), h['width'], h['height'], h['mips'])
    print(arcpath, 'round-trip ok', ok, 'mismatch', bad, 'skipped', skip)
    return bad == 0


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'selftest':
        good = all(selftest(p) for p in (sys.argv[2:] or ['/nativeNX/arc/enemy/em001_00.arc']))
        sys.exit(0 if good else 1)
    t = open(sys.argv[2], 'rb').read() if not sys.argv[2].endswith('.png') else None
    if cmd == 'info':
        h = parse(t); h.pop('data'); print(h)
    elif cmd == 'topng':
        save_png(decode(t, int(sys.argv[4]) if len(sys.argv) > 4 else 0), sys.argv[3])
    elif cmd == 'togu':
        fmt = sys.argv[sys.argv.index('--fmt') + 1] if '--fmt' in sys.argv else 'bc3'
        mips = int(sys.argv[sys.argv.index('--mips') + 1]) if '--mips' in sys.argv else None
        if t is None:
            from PIL import Image
            img = np.array(Image.open(sys.argv[2]).convert('RGBA'))
        else:
            img = decode(t)
        open(sys.argv[3], 'wb').write(encode_gu(img, fmt, mips))
