"""mrl.py : MT Framework material lists (rMaterial, .mrl) for MH4U (v0x20, shader package MFX v52
romfs/system/ltshader/LtShaderPackage.lfx) and MHGU (v0x22, MFX v53 nativeNX/system/app_shader/AppShaderPackage.mfx).

  mrl.py dump FILE.mrl          materials with state/parameter record names and texture slots

Layout (both versions):
  'MRL\\0', u32 version, u32 materialCount, u32 textureCount, u32 shaderPackageHash, u32 texOff, u32 matOff
  texture entry: u32 type hash (0x241f5deb rTexture, 0 = reserved), u32, u32, char path[64]   (76 bytes)
  material entry: +0 class hash, +4 name hash (crc32(name) ^ ~0), +8 parameter-list size, +0xC.. state words,
                  parameter-list offset (4U: entry +0x34, 60-byte entries; GU: see GU_MAT below)
  word = (tag << 12) | record (1-based index into the shader package record table)
  parameter: 12 bytes [u32 (record << 20) | ..., u32 value, u32 word], value of a texture slot = 1-based texture index
"""
import os, struct, sys, zlib

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../dump/'
PKG = {0x20: (ROOT + 'romfs/system/ltshader/LtShaderPackage.lfx', 0x20, 0x2C),
       0x22: (ROOT + 'gu/AppShaderPackage.mfx', 0x10, 0x18)}
_REC = {}


def records(ver):
    if ver not in _REC:
        path, stroff_at, offs_at = PKG[ver]
        l = open(path, 'rb').read()
        n = struct.unpack_from('<I', l, 0xC)[0]
        STR = struct.unpack_from('<I', l, stroff_at)[0]
        cstr = lambda o: l[o:l.find(b'\0', o)].decode('latin1')
        rec = {}
        for i in range(n - 1):
            o = struct.unpack_from('<I', l, offs_at + 4 * i)[0]
            w = struct.unpack_from('<6I', l, o)
            try: rec[w[3] >> 16] = (cstr(STR + w[0]), cstr(STR + w[1]))
            except Exception: pass
        _REC[ver] = rec
    return _REC[ver]


def rec_name(ver, word):
    r = records(ver).get(word & 0xFFF)
    return r[0] if r else None


def name_hash(name):
    return zlib.crc32(name.encode('ascii')) ^ 0xFFFFFFFF


_CB = {}


def cb_layout(ver, cbname):
    """{variable: (float offset, rows, cols)} of a constant-buffer record of the shader package.
    Record = 6 words {name, type, ...}; GU: u16 count at +24, variables from +40; 4U: u16 count at +22, from +36.
    Variable (28 B): {name, type, class (cols = bits 4-7, rows = bits 8-11), 0, (float offset << 8) | .., ...}.
    Checked: GU CBMaterial fDiffuseColor f0 float3, fTransparency f3, fUVTransform f8 2x4; $Globals
    fAlphaClipThreshold f0, fAlbedoColor f1, fSpecularColor f44; 4U CBMaterialStd fMaterialStdAlbedoColor f20."""
    if (ver, cbname) in _CB:
        return _CB[(ver, cbname)]
    path, stroff_at, offs_at = PKG[ver]
    l = open(path, 'rb').read()
    n = struct.unpack_from('<I', l, 0xC)[0]
    STR = struct.unpack_from('<I', l, stroff_at)[0]
    cstr = lambda o: l[o:l.find(b'\0', o)].decode('latin1')
    cnt_at, var_at = (24, 40) if ver == 0x22 else (22, 36)
    out = None
    for i in range(n - 1):
        o = struct.unpack_from('<I', l, offs_at + 4 * i)[0]
        try:
            if cstr(STR + struct.unpack_from('<I', l, o)[0]) != cbname: continue
        except Exception:
            continue
        out = {}
        for k in range(struct.unpack_from('<H', l, o + cnt_at)[0]):
            v = struct.unpack_from('<7I', l, o + var_at + 28 * k)
            out[cstr(STR + v[0])] = ((v[4] >> 8) & 0xFFFF, (v[2] >> 8) & 0xF, (v[2] >> 4) & 0xF)
        break
    assert out, 'no constant buffer %s' % cbname
    _CB[(ver, cbname)] = out
    return out


def read(d):
    magic, ver, nmat, ntex, pkg, toff, moff = struct.unpack_from('<4sIIIIII', d, 0)
    assert magic == b'MRL\0', magic
    textures = []
    for i in range(ntex):
        e = d[toff + 76 * i: toff + 76 * (i + 1)]
        th = struct.unpack_from('<I', e, 0)[0]
        textures.append((th, e[12:76].split(b'\0')[0].decode('ascii', 'replace')))
    # material entries are 60 bytes in both versions: w2 parameter block size, w13 its offset; GU also has
    # w12 animation block size / w14 offset. 4U ends the descriptor list with an all-zero one; in GU the count
    # is the constant-buffer offset (smallest value of a type-1 descriptor) / 12.
    esize = 60
    mats = []
    for m in range(nmat):
        w = struct.unpack_from('<15I', d, moff + esize * m)
        pl, ps = w[13], w[2]
        block = d[pl:pl + ps]
        states = [rec_name(ver, x) for x in w[3:13]] if ver == 0x20 else [rec_name(ver, x) for x in w[3:8]]
        count = len(block) // 12
        if ver != 0x20:
            # walk until the first constant buffer starts
            k = 0; first_cb = len(block)
            while 12 * k + 12 <= min(first_cb, len(block)):
                a, val, _ = struct.unpack_from('<III', block, 12 * k)
                if a & 0xF == 1: first_cb = min(first_cb, val)
                k += 1
            count = min(k, first_cb // 12)
        params = []
        for k in range(count):
            a, val, word = struct.unpack_from('<III', block, 12 * k)
            if ver == 0x20 and a == 0 and val == 0 and word == 0: break
            params.append((rec_name(ver, word) or hex(word), a & 0xF, val))
        mats.append(dict(cls=w[0], name=w[1], words=w, states=states, params=params, block=block,
                         anim=d[w[14]:w[14] + w[12]] if ver != 0x20 and w[12] else b''))
    return dict(version=ver, pkg=pkg, textures=textures, mats=mats, esize=esize)


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        d = open(sys.argv[2], 'rb').read()
        r = read(d)
        print('version %#x pkg %08x textures %d materials %d entry %d bytes' % (r['version'], r['pkg'], len(r['textures']),
              len(r['mats']), r['esize']))
        for i, (th, p) in enumerate(r['textures']): print('  tex %2d %08x %s' % (i + 1, th, p))
        for m in r['mats']:
            print('  mat cls %08x name %08x states %s' % (m['cls'], m['name'], [s for s in m['states'] if s]))
            for p in m['params']: print('      ', p)
