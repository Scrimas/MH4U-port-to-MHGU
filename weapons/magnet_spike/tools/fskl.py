"""MHF FSKL skeletons (structure after Paxlord's mhfz-blender-plugin parse_fskl): directory header (u32 type,
u32 count, u32 size), a root-index block, then one 268-byte block (type 0x40000001) per bone: u32 node, parent, child,
sibling (-1 = none), then three f32 4-vectors scale, rotation (Euler radians), translation (w = 1 each; parse_fskl
reads two of the w's as "IK weight / blend"), u32 unknown (-1), u32 part (player: 0 = root + legs, bones 0-8;
1 = spine, arms, head, bones 9-20; the two parts of an AAN motion), zero padding. Units: cm.
usage: python3 -I fskl.py FILE.fskl        print the bone tree"""
import struct, sys


def parse(b):
    """-> (root indices, [dict(node, parent, child, sibling, scale, rot, pos, unk, part)])"""
    _, nfiles, _ = struct.unpack_from('<III', b, 0)
    _, nroots, _ = struct.unpack_from('<III', b, 12)
    roots = list(struct.unpack_from('<%dI' % nroots, b, 24))
    o = 24 + 4 * nroots; bones = []
    for _ in range(nfiles - 1):
        _, _, size = struct.unpack_from('<III', b, o)
        v = struct.unpack_from('<4i12f2I', b, o + 12)
        bones.append(dict(node=v[0], parent=v[1], child=v[2], sibling=v[3], scale=v[4:7], rot=v[8:11],
                          pos=v[12:15], unk=v[16], part=v[17]))
        o += size
    return roots, bones


if __name__ == '__main__':
    roots, bones = parse(open(sys.argv[1], 'rb').read())
    by = {bn['node']: bn for bn in bones}
    print('roots', roots, 'bones', len(bones))
    def show(n, depth):
        bn = by[n]
        print('%s%-3d part %2d pos (%8.2f %8.2f %8.2f) rot (%6.3f %6.3f %6.3f) unk %#x' % (
            '  ' * depth, n, bn['part'], *bn['pos'], *bn['rot'], bn['unk']))
        c = bn['child']
        while c >= 0:
            show(c, depth + 1); c = by[c]['sibling']
    for bn in bones:
        if bn['parent'] < 0: show(bn['node'], 0)
