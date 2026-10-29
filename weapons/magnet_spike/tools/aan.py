"""MHF AAN motion packages (dat/motion/*.mot after JPK decode). Layout after Paxlord's mhfz-blender-plugin
(src/file_parsers.py parse_aan_package): header = (motion count, offset table) per part; parts come in pairs (lower
body + root, upper body) that share slot numbers; motion = u32 flags, u32 bone count, u32 size, u32 loop,
f32 loop start, then per bone u32 flags, u32 channel count, u32 size and its channels; channel = u32 header (bits
0-8 channel, 16-23 key type), u32 key count, u32 size, keys.
Short keys are (value, frame, tangent in, tangent out); the value units are not settled yet (rotation looks like
65536 = one turn).
usage: python3 -I aan.py FILE.aan          list each motion: group, slot, frames, loop, bones per part"""
import struct, sys, collections

KEY = {17: '<hh', 18: '<hhhh', 19: '<ihhhh', 33: '<ff', 34: '<ffff', 35: '<iffff'}
CHAN = {0x1: 'sx', 0x2: 'sy', 0x4: 'sz', 0x8: 'rx', 0x10: 'ry', 0x20: 'rz', 0x40: 'tx', 0x80: 'ty', 0x100: 'tz'}


def motion(b, o):
    """-> dict(loop, loop_start, frames, bones=[{chan: (key type, [keys])}])"""
    _, nb, _, loop, ls = struct.unpack_from('<IIIIf', b, o)
    cur = o + 20; bones = []; frames = 0
    for _ in range(nb):
        _, nc, size = struct.unpack_from('<III', b, cur)
        c = cur + 12; chans = {}
        for _ in range(nc):
            h, nk, cs = struct.unpack_from('<III', b, c)
            t = (h >> 16) & 0xff; f = KEY[t]; n = struct.calcsize(f)
            keys = [struct.unpack_from(f, b, c + 12 + i * n) for i in range(nk)]
            chans[CHAN.get(h & 0x1ff, hex(h & 0x1ff))] = (t, keys)
            if keys and t in (17, 18): frames = max(frames, keys[-1][1])
            c += cs
        bones.append(chans); cur += size
    return dict(loop=loop, loop_start=ls, frames=frames, bones=bones)


def parse(b):
    """-> list of parts, each {slot: motion}"""
    first = struct.unpack_from('<II', b, 0)[1]
    parts = []
    for i in range(first // 8):
        n, o = struct.unpack_from('<II', b, 8 * i)
        p = {}
        if n and n != 0xffffffff and o:
            for s, mo in enumerate(struct.unpack_from('<%dI' % n, b, o)):
                if mo != 0xffffffff: p[s] = motion(b, mo)
        parts.append(p)
    return parts


if __name__ == '__main__':
    parts = parse(open(sys.argv[1], 'rb').read())
    types = collections.Counter(t for p in parts for m in p.values() for bn in m['bones'] for t, _ in bn.values())
    print('parts', [len(p) for p in parts], 'key types', dict(types))
    for g in range(0, len(parts) - 1, 2):
        lo, up = parts[g], parts[g + 1]
        for s in sorted(set(lo) | set(up)):
            a, u = lo.get(s), up.get(s)
            m = a or u
            print('group %d slot %3d  frames %4d  loop %d from %5.1f  bones %s+%s' % (
                g // 2, s, max(x['frames'] for x in (a, u) if x), m['loop'], m['loop_start'],
                len(a['bones']) if a else '-', len(u['bones']) if u else '-'))
