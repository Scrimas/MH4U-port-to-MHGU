"""MHF attack (hit) data: dat/mhfsdt.bin after ECD + JPK decode (mhfo-hd.dll loader 0x10afcd10, lookup by attack-object
kind 0x10afcfd0, record fetch 0x10afd0c0 / 0x10afd0f0, copy into the attack object 0x11323160).

Root: 28 B entries sorted by (kind, sub), ended by kind -1:
  u16 sub, u16 kind, u16 count, u16 sets, u32 attacks, u32 extra, u32 shapes, u32 p14, u32 p18   (offsets from the file start)
  attacks  count x 40 B, indexed by attack id (the param of the weapon's "attack" frame event; MS event 3 -> kind 0x78):
           i16 [2] motion value, [7] damage type (0x20a cut, 0x10a impact), [8] shape set, [16] KO (8.8 fixed point),
           rest unread ([1], [3], [5], [14], [17])
  extra    count x 16 B (0x10afd0f0; all zero for Magnet Spike)
  shapes   sets x 8 u32 -> lists of 40 B hit shapes ended by -1 (u16 kind, u16 bone, u32, u32, 7 x f32); the 8 = per-weapon
           variant (melee record byte +0x1c, 0x10899270)
The attack object then adds the Magnetise bonus to the motion value (0x1033c5d0: x (100 + param 61) / 100).
Magnet Spike: kind 0x78 = its attacks (46), kind 0x79 = its special attacks (14, e.g. the Pin Finisher's 600).
usage: python3 -I sdt.py MHFSDT.dec.bin                 list the kinds
       python3 -I sdt.py MHFSDT.dec.bin KIND [shapes]   one kind's attacks (and its shape sets)"""
import struct, sys


def entries(d):
    out = []; o = 0
    while struct.unpack_from('<h', d, o + 2)[0] != -1:
        sub, kind, count, sets, pa, pe, ps, p14, p18 = struct.unpack_from('<HHHH5I', d, o)
        out.append(dict(sub=sub, kind=kind, count=count, sets=sets, attacks=pa, extra=pe, shapes=ps))
        o += 28
    return out


def attacks(d, e):
    out = []
    for i in range(e['count']):
        r = struct.unpack_from('<20h', d, e['attacks'] + 40 * i)
        out.append(dict(id=i, mv=r[2], type=r[7] & 0xffff, shape=r[8], ko=(r[16] & 0xffff) / 256, raw=r))
    return out


def shape_sets(d, e):
    """-> [set][variant] = [(kind, bone, u32, u32, 7 floats)]"""
    out = []
    for s in range(e['sets']):
        var = []
        for v in range(8):
            p = struct.unpack_from('<I', d, e['shapes'] + 32 * s + 4 * v)[0]; lst = []
            while p and struct.unpack_from('<h', d, p)[0] != -1:
                lst.append(struct.unpack_from('<HHII7f', d, p)); p += 40
            var.append(lst)
        out.append(var)
    return out


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    es = entries(d)
    if len(sys.argv) == 2:
        for e in es: print('kind %#05x sub %d: %3d attacks, %2d shape sets' % (e['kind'], e['sub'], e['count'], e['sets']))
        sys.exit()
    e = next(x for x in es if x['kind'] == int(sys.argv[2], 0))
    for a in attacks(d, e):
        print('%2d  MV %4d  KO %5.1f  %-6s shape %d   raw %s' % (
            a['id'], a['mv'], a['ko'], {0x20a: 'cut', 0x10a: 'impact'}.get(a['type'], hex(a['type'])), a['shape'],
            ' '.join(str(x) for x in a['raw'])))
    if 'shapes' in sys.argv[3:]:
        for s, var in enumerate(shape_sets(d, e)):
            same = all(v == var[0] for v in var)
            for v, lst in enumerate(var[:1] if same else var):
                print('set %d variant %s:' % (s, 'all' if same else v))
                for sh in lst: print('   kind %d bone %d %#x %d  %s' % (sh[:4] + (' '.join('%.1f' % f for f in sh[4:]),)))
