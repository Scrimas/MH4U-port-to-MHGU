"""walk_em090.py : 4U's walk strips as triangles -> data file section WALK of the dalamadur and shah_dalamadur entries,
for the module's copy of 4U's ground query (monsters/dalamadur/module/dala_walk.c walk_step).

4U (C, 0x681e44 -> 0x681c84 -> 0x5a4680; gu-walkable.md 6b): the hunter's ground on the monster is the HIGHEST strip
triangle whose XZ projection holds him, in a vertical segment from y + 50 down to y - 300 (em024 / em083). GU's own
ground (the walk SBC files, tools/walk4u2gu.py) does not step up 35..70 onto an overlapping piece (test 2026-10-22,
tail j141 -> j140), so the module runs 4U's query on these triangles and lifts the hunter.

WALK: u32 n, n x {u16 joint, u16 triangles, u32 offset}, then per piece triangles x 9 f32 (3 bone-local vertices, the
same vertices as the walk SBC files: 4U emd word 10, every joint's strips once, tools/walk4u2gu.py by_joint).
Shah's halves have the same strips (walk4u2gu.SAME; checked here), so both entries carry the same table.

  walk_em090.py          write the sections (then build.sh pack)
  walk_em090.py show     print the pieces only
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import emdata4u as E  # noqa: E402
import portdata  # noqa: E402
import walk4u2gu as W  # noqa: E402

ENTRIES = ('dalamadur', 'shah_dalamadur')


def pieces():
    """[(joint, [9 floats per triangle])]: head em024 joints, then tail em083 joints"""
    sets = {em: W.walk_sets(E.load_4u(em)['emd']) for em in W.EMS}
    for em, src in W.SAME.items():
        assert W.same_sets(sets[em], sets[src]), '%s walk sets differ from %s' % (em, src)
    out = []
    for em in ('em024', 'em083'):
        for j, (strips, _) in W.by_joint(sets[em]).items():
            tris = []
            for S in strips:
                tt, _, _ = W.strip_tris(S)
                tris += [[float(x) for k in t for x in S[k]] for t in tt]
            out.append((j, tris))
    return out


def section(P):
    sec = portdata.Section('WALK')
    sec.u32(len(P))
    off = 4 + 8 * len(P)
    body = b''
    for j, tris in P:
        sec.raw(struct.pack('<HHI', j, len(tris), off + len(body)))
        body += b''.join(struct.pack('<9f', *t) for t in tris)
    sec.raw(body)
    return sec


def main():
    P = pieces()
    for j, tris in P: print('joint %3d: %3d triangles' % (j, len(tris)))
    if sys.argv[1:] == ['show']: return
    sec = section(P)
    for name in ENTRIES: print('wrote', portdata.write_section(name, sec))


if __name__ == '__main__':
    main()
