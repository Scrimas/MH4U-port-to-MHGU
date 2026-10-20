"""mod.py : MT Framework rModel (MOD) reader for MH4U (3DS, version 0xE6) and MHGU (Switch, version 0xD4).

  mod.py info FILE.mod            header, bones, groups, materials, meshes (vertex formats, strides)

Layout (both, little-endian), from RevilLib (github.com/PredatorCZ/RevilLib, src/mtf_mod) + checked on files:
  common  'MOD\\0', s16 version, u16 bones, u16 meshes, u16 materials, u32 vertices, u32 indices, u32 edges
  4U E6   u32 vbSize, u32 textures(0), u32 groups, u32 skins, u32 bonesOff, groupsOff, materialsOff,
          meshesOff, vbOff, ibOff                                              (header 0x40)
  GU D4   u32 vbSize, u32 textures(0), u32 groups, u32 bonesOff, groupsOff, materialsOff, meshesOff,
          vbOff, ibOff, dataEnd                                                (header 0x40)
  then    sphere (4f), AABB (2 x 4f), metadata: u32 middleDist, lowDist, lightGroup, u8 boundaryJoint
          (+3 pad), GU adds u32 envelopeCount
  bones   n x 24 B {u8 index, parent, mirror, pad, f32 furthestVertex, f32 parentDistance, f32 pos[3]},
          n x 64 B local matrix, n x 64 B inverse bind matrix, 256 B remap (bone id -> index)
          4U only: skins x 28 B {u32 count, u8 bones[24]}  (per-mesh skin palette, mesh.skinBoneBegin indexes it)
  groups  n x 32 B {u32 index, pad[12], f32 sphere[4]}
  materials n x 128 B names (crc32(name)^~0 = MRL material name hash)
  meshes  n x 48 B: u16 drawMode, u16 vertexCount, u32 data0 (group:12, material:12, lod:8),
          u32 data1 (visible:1, shape:1, sort:1, weights:5, alpha:8, stride:8, primType:6, binormalFlip:1, bridge:1),
          u32 vertexStart, u32 vertexStreamOffset, u32 vertexFormat (input layout hash), u32 indexStart,
          u32 indexCount, u32 indexValueOffset, u8 skinBoneBegin, u8 envelopes, u16 meshIndex,
          u16 minVertex, u16 maxVertex, u32 boundaryInfo
  envelopes 4U: u32 count + n x 144 B; GU: metadata.envelopeCount x 144 B
  vertex buffer, u16 index buffer (triangle strips, 0xFFFF restart)
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def vertex_format_names():
    """input layout hash -> name, from the shader packages (IA* records hashed like MT class names)."""
    return {}


def parse(d):
    magic, ver, nb, nm, nmat, nv, ni, ne = struct.unpack_from('<4shHHHIII', d, 0)
    assert magic == b'MOD\0', magic
    ver &= 0xFFFF
    m = dict(version=ver, bones=nb, meshes=nm, materials=nmat, vertices=nv, indices=ni, edges=ne)
    if ver == 0xE6:
        (m['vbSize'], m['textures'], m['groups'], m['skins'], ob, og, omat, omesh, ovb, oib) = \
            struct.unpack_from('<10I', d, 0x18)
        o = 0x40
    elif ver == 0xD4:
        (m['vbSize'], m['textures'], m['groups'], ob, og, omat, omesh, ovb, oib, m['dataEnd']) = \
            struct.unpack_from('<10I', d, 0x18)
        m['skins'] = 0
        o = 0x40
    else:
        raise SystemExit('unsupported MOD version %#x' % ver)
    m['sphere'] = struct.unpack_from('<4f', d, o)
    m['aabb'] = struct.unpack_from('<8f', d, o + 16)
    md = struct.unpack_from('<3IB', d, o + 48)
    m['metadata'] = md
    if ver == 0xD4:
        m['envCount'] = struct.unpack_from('<I', d, o + 64)[0]
    m['offsets'] = dict(bones=ob, groups=og, materials=omat, meshes=omesh, vb=ovb, ib=oib)
    # bones
    bones = []
    for i in range(nb):
        idx, par, mir, _, fur, pdist, x, y, z = struct.unpack_from('<4B5f', d, ob + 24 * i)
        bones.append(dict(index=idx, parent=par, mirror=mir, furthest=fur, pdist=pdist, pos=(x, y, z)))
    m['bone_list'] = bones
    p = ob + 24 * nb
    m['local'] = [struct.unpack_from('<16f', d, p + 64 * i) for i in range(nb)]; p += 64 * nb
    m['invbind'] = [struct.unpack_from('<16f', d, p + 64 * i) for i in range(nb)]; p += 64 * nb
    m['remap'] = d[p:p + 256] if nb else b''; p += 256 if nb else 0
    m['skin_list'] = []
    for i in range(m['skins']):
        cnt = struct.unpack_from('<I', d, p)[0]
        m['skin_list'].append(list(d[p + 4:p + 4 + cnt])); p += 28
    m['group_list'] = [struct.unpack_from('<I12x4f', d, og + 32 * i) for i in range(m['groups'])]
    m['material_names'] = [d[omat + 128 * i: omat + 128 * (i + 1)].split(b'\0')[0].decode('ascii', 'replace')
                           for i in range(nmat)]
    meshes = []
    for i in range(nm):
        f = struct.unpack_from('<HHIIIIIIIIBBHHHI', d, omesh + 48 * i)
        d0, d1 = f[2], f[3]
        meshes.append(dict(drawMode=f[0], numVertices=f[1], group=d0 & 0xFFF, material=(d0 >> 12) & 0xFFF,
                           lod=d0 >> 24, visible=d1 & 1, shape=(d1 >> 1) & 1, sort=(d1 >> 2) & 1,
                           weights=(d1 >> 3) & 31, alpha=(d1 >> 8) & 0xFF, stride=(d1 >> 16) & 0xFF,
                           prim=(d1 >> 24) & 0x3F, binflip=(d1 >> 30) & 1, bridge=d1 >> 31,
                           vertexStart=f[4], streamOff=f[5], fmt=f[6], indexStart=f[7], numIndices=f[8],
                           indexValueOffset=f[9], skinBoneBegin=f[10], envelopes=f[11], meshIndex=f[12],
                           minV=f[13], maxV=f[14], boundary=f[15], raw=d[omesh + 48 * i: omesh + 48 * (i + 1)]))
    m['mesh_list'] = meshes
    p = omesh + 48 * nm
    if ver == 0xE6:
        m['envCount'] = struct.unpack_from('<I', d, p)[0]; p += 4
    m['envelopes_off'] = p
    m['vb'] = d[ovb:ovb + m['vbSize']]
    m['ib'] = d[oib:oib + 2 * ni]
    return m


if __name__ == '__main__':
    import collections
    d = open(sys.argv[2], 'rb').read()
    m = parse(d)
    print({k: v for k, v in m.items() if not isinstance(v, (list, bytes, dict))})
    print('offsets', {k: hex(v) for k, v in m['offsets'].items()}, 'metadata', m['metadata'], 'envelopes', m['envCount'])
    print('bones', len(m['bone_list']), 'first', m['bone_list'][:3])
    print('skins', len(m['skin_list']), m['skin_list'][:3])
    print('materials', m['material_names'])
    c = collections.Counter((hex(x['fmt']), x['stride'], x['weights']) for x in m['mesh_list'])
    print('vertex formats (fmt, stride, weights):', dict(c))
    for x in m['mesh_list'][:6]:
        print({k: v for k, v in x.items() if k != 'raw'})
