"""MHF FMOD models (block layout after Paxlord's mhfz-blender-plugin src/file_parsers.py; standalone, no bpy).
File = root header {u32 type 1, u32 count, u32 size} then `count` directories {u32 type, u32 count, u32 size}:
type 2 = meshes (count mesh directories), 9 = materials, 0xA = textures, 0x20000 = skipped. A mesh directory (type 4)
holds blocks: 5 = triangle strips (sub-blocks of u32 strips: u32 length & 0xfffffff, then indices), 0x50000 material
list, 0x60000 per-strip material index, 0x70000 positions (3 f32), 0x80000 normals, 0xA0000 UVs (2 f32, v flipped
here as Paxlord does), 0xB0000 colours, 0xC0000 weights (per vertex: u32 n, n x {u32 bone list index, f32 percent}),
0x100000 bone list (mesh-local index -> skeleton bone id), 0x120000 tangents. Units: cm, Y up.
usage: python3 -I fmod.py FILE.fmod        mesh summary"""
import struct, sys


def _hdr(b, o):
    return struct.unpack_from('<III', b, o)


def _mesh(b, o):
    t, n, size = _hdr(b, o)
    m = dict(strips=[], material_list=[], material_index=[], pos=[], normal=[], uv=[], weights=[], bones=[])
    c = o + 12
    for _ in range(n):
        bt, bn, bs = _hdr(b, c); p = c + 12
        if bt == 5:
            for _ in range(bn):
                st, sn, ss = _hdr(b, p); p += 12
                for _ in range(sn):
                    k = struct.unpack_from('<I', b, p)[0] & 0xFFFFFFF; p += 4
                    m['strips'].append(list(struct.unpack_from('<%dI' % k, b, p))); p += 4 * k
        elif bt == 0x50000: m['material_list'] = list(struct.unpack_from('<%dI' % bn, b, p))
        elif bt == 0x60000: m['material_index'] = list(struct.unpack_from('<%dI' % bn, b, p))
        elif bt == 0x70000: m['pos'] = [struct.unpack_from('<3f', b, p + 12 * i) for i in range(bn)]
        elif bt == 0x80000: m['normal'] = [struct.unpack_from('<3f', b, p + 12 * i) for i in range(bn)]
        elif bt == 0xA0000:
            m['uv'] = [(u, 1.0 - v) for u, v in (struct.unpack_from('<2f', b, p + 8 * i) for i in range(bn))]
        elif bt == 0xC0000:
            for _ in range(bn):
                k = struct.unpack_from('<I', b, p)[0]; p += 4
                m['weights'].append([struct.unpack_from('<If', b, p + 8 * j) for j in range(k)]); p += 8 * k
        elif bt == 0x100000: m['bones'] = list(struct.unpack_from('<%dI' % bn, b, p))
        c += bs
    return m


def triangles(m):
    """strips -> [(a, b, c, global material)] with alternating winding (degenerate triangles dropped)"""
    out = []
    for si, s in enumerate(m['strips']):
        mat = m['material_list'][m['material_index'][si]] if m['material_index'] and m['material_list'] else 0
        for i in range(2, len(s)):
            a, b2, c = s[i - 2], s[i - 1], s[i]
            if a == b2 or b2 == c or a == c: continue
            out.append((a, b2, c, mat) if i % 2 == 0 else (a, c, b2, mat))
    return out


def parse(b):
    """-> list of meshes (dicts above; weights hold mesh-local bone indices, map them through m['bones'])"""
    t, n, size = _hdr(b, 0)
    meshes = []; o = 12
    for _ in range(n):
        dt, dn, ds = _hdr(b, o)
        if dt == 2:
            c = o + 12
            for _ in range(dn):
                meshes.append(_mesh(b, c)); c += _hdr(b, c)[2]
        o += ds
    return meshes


if __name__ == '__main__':
    for i, m in enumerate(parse(open(sys.argv[1], 'rb').read())):
        print('mesh %d: %d vertices, %d triangles, %d weighted, bones %s' % (
            i, len(m['pos']), len(triangles(m)), len(m['weights']), m['bones']))
