"""mhffx.py : MHF effect sets (dat/effect.bin entry 18), decoded from the ZZ client (mhfo-hd.dll); see
notes/assets.md "## Effects". C = read in the client's code, S = data only.

Container: u32 count, u32 type-table offset; (u32 offset, u32 size) pairs from u32 3; type table = (u16 kind,
u16 set id) per entry (kind 1 = an effect set, registered by 0x113d4a70).
Set = 14 x u16 header (version 4, counts of A, B, C, D, E, F, ...), then the sections back to back:
  A 0x70  emitter: one spawn burst of an effect (0x113d3fc0, C)
  B 0x18  vec3 curve key  (0x113ccd90, C)
  C 0x10  colour key      (0x113ccaf0, C)
  D 0x10  mesh-animation key (0x113cca10 / 0x113cc8e0, C)
  E 0x38  particle definition (0x113cd4b0 spawn, 0x113cda30 update, 0x113ce4d0 draw, C)
  F 0x8c  second emitter kind (A flag bit 0), not decoded
Timing: the effect and particle ages count 2 per MHF tick (1/60 s units); key frames, A +0x4e and E life use them.

usage: python3 -I mhffx.py SETS.bin list                     sets and section counts
       python3 -I mhffx.py SETS.bin effect SET EFFECT        an effect's emitters, particles and curves (hex ids)"""
import struct, sys, math

SIZES = dict(A=0x70, B=0x18, C=0x10, D=0x10, E=0x38, F=0x8c)
RAND = 1 / 512.0      # (rng & 0x3ff) - 0x200, x DAT_119b5f6c: uniform in [-1, 1)


def container(c):
    cnt, tt = struct.unpack_from('<II', c, 0)
    out = {}
    for i in range(1, cnt):
        kind, sid = struct.unpack_from('<HH', c, tt + 4 * i)
        off, size = struct.unpack_from('<II', c, 12 + 8 * (i - 1))
        if kind == 1:
            out[sid] = c[off:off + size]
    return out


class Set:
    def __init__(self, s):
        self.raw = s
        self.hdr = struct.unpack_from('<14H', s, 0)
        p = 0x1c
        self.sec = {}
        for k, name in enumerate('ABCDEF'):
            n = self.hdr[1 + k]
            self.sec[name] = [s[p + i * SIZES[name]: p + (i + 1) * SIZES[name]] for i in range(n)]
            p += n * SIZES[name]

    # --- records -----------------------------------------------------------------------------------------------
    @staticmethod
    def emitter(r):
        """A record (0x113d3fc0 / 0x113d37e0 / 0x113d3bd0 / 0x113d3d80 / 0x113d3f00, C):
        position = base +0x00 + U(-1,1) x range +0x0c (per axis), turned by the effect's yaw, + the effect origin;
        rotation (rad) = base +0x18 + U x range +0x24, wrapped to [-pi, pi]; scale = base +0x30 + U x range +0x3c
        (flag 2: one U for all axes); flags 4 / 8: random mirror of x / y; spawns at effect frame +0x4e, count +0x58,
        particle id +0x4c (every E with E +4 == it), effect id +0x50; +0x48 / +0x5c / +0x52 passed to the particle
        (+0x5c = life scale: key frames and life x it when >= 1, S)."""
        f = struct.unpack_from('<18f', r, 0)
        return dict(pos=f[0:3], pos_r=f[3:6], rot=f[6:9], rot_r=f[9:12], scl=f[12:15], scl_r=f[15:18],
                    p48=struct.unpack_from('<f', r, 0x48)[0], part=struct.unpack_from('<H', r, 0x4c)[0],
                    frame=struct.unpack_from('<H', r, 0x4e)[0], effect=struct.unpack_from('<H', r, 0x50)[0],
                    p52=struct.unpack_from('<h', r, 0x52)[0], flags=struct.unpack_from('<I', r, 0x54)[0],
                    count=struct.unpack_from('<h', r, 0x58)[0], p5c=struct.unpack_from('<f', r, 0x5c)[0],
                    rest=r[0x60:].hex())

    @staticmethod
    def particle(r):
        """E record (0x113cd4b0 / 0x113cdd70 / 0x113cecf0 / 0x113cf6b0 / 0x113cffa0 / 0x113d05f0 / 0x113d0690, C):
        +0 flags (bits 0 / 1 / 0x200 billboard modes = view-matrix multiplies, 4 / 0xc00 render queue, 0x20 draw
        variant, 0x40 colour override, 0x80 snap to ground, 0x400 distance cull); +4 id; +6 == 1: mesh from the
        set's own pack; +8 mesh (index into the effect model, effect.bin entry 0) unless the D group +0xa animates
        it; +0xc life; curves (B ids): +0xe position offset (in the particle's rotated frame), +0x10 rotation
        (degrees, added to the spawn rotation), +0x12 scale (x the spawn scale), +0x22 -> particle +0x78 (draw,
        S colour scale), +0x26 -> particle +0x104 (?); +0x16 UV mode (1 scroll u / v by 1 / +0x18, 1 / +0x1c per
        tick, 2 u only, 3 v only, 4-6 flipbook: +0x18 cells, +0x1c frames, 7 UV from curve +0x18); +0x20 colour
        curve (C group, RGBA); +0x24 second D group; +0x15 draw mode; +0x28 f32 (draw: != 1.0 -> alpha param)."""
        h = struct.unpack_from('<IHHHHHHHH', r, 0)
        return dict(flags=h[0], id=h[1], pack=h[2], mesh=h[3], mesh_anim=h[4], life=h[5], c_pos=h[6], c_rot=h[7],
                    c_scl=h[8], b14=r[0x14], draw=r[0x15], uv_mode=r[0x16], b17=r[0x17],
                    uv_u=struct.unpack_from('<i', r, 0x18)[0], uv_v=struct.unpack_from('<i', r, 0x1c)[0],
                    c_col=struct.unpack_from('<H', r, 0x20)[0], c_22=struct.unpack_from('<H', r, 0x22)[0],
                    anim2=struct.unpack_from('<H', r, 0x24)[0], c_26=struct.unpack_from('<H', r, 0x26)[0],
                    f28=struct.unpack_from('<f', r, 0x28)[0], rest=r[0x2c:].hex())

    def curve(self, cid):
        """B keys of curve cid (byte +0x12), in record order: (frame +0xc, vec3 +0, flags +0x10 (bit 0 of the first
        key = loop)); linear between keys, the first / last value outside them (0x113ccd90, C)."""
        if cid == 0:
            return []
        return [(struct.unpack_from('<i', r, 0xc)[0], struct.unpack_from('<3f', r, 0),
                 struct.unpack_from('<H', r, 0x10)[0]) for r in self.sec['B'] if r[0x12] == cid]

    def colours(self, gid):
        """C keys of group gid (byte +6): (frame +0, RGBA bytes +8.. in the order R = +0xa, G = +9, B = +8? (S),
        flags +4 (bit 0 = loop))"""
        if gid == 0:
            return []
        return [(struct.unpack_from('<i', r, 0)[0], r[8:12].hex(), struct.unpack_from('<H', r, 4)[0])
                for r in self.sec['C'] if r[6] == gid]

    def mesh_keys(self, gid):
        """D keys of group gid (u16 +6): (frame +0, mesh +8)"""
        if gid == 0:
            return []
        return [(struct.unpack_from('<i', r, 0)[0], struct.unpack_from('<i', r, 8)[0])
                for r in self.sec['D'] if struct.unpack_from('<H', r, 6)[0] == gid]

    def effect(self, eid):
        return [self.emitter(r) for r in self.sec['A'] if struct.unpack_from('<H', r, 0x50)[0] == eid]

    def particles(self, pid):
        return [self.particle(r) for r in self.sec['E'] if struct.unpack_from('<H', r, 4)[0] == pid]


def _v(v):
    return '(%s)' % ', '.join('%g' % round(x, 3) for x in v)


def show_effect(st, eid):
    for a in st.effect(eid):
        print('A frame %d x%d part %d flags %#x pos %s +-%s rot %s +-%s scl %s +-%s p48 %g p52 %d p5c %g' % (
            a['frame'], a['count'], a['part'], a['flags'], _v(a['pos']), _v(a['pos_r']), _v(a['rot']),
            _v(a['rot_r']), _v(a['scl']), _v(a['scl_r']), a['p48'], a['p52'], a['p5c']))
        if a['flags'] & 1:
            print('   (F emitter, not decoded)')
            continue
        for e in st.particles(a['part']):
            print('   E id %d flags %#x mesh %d anim %d life %d draw %d uv %d (%d, %d) f28 %g pack %d b14 %d' % (
                e['id'], e['flags'], e['mesh'], e['mesh_anim'], e['life'], e['draw'], e['uv_mode'], e['uv_u'],
                e['uv_v'], e['f28'], e['pack'], e['b14']))
            for name, cid in (('pos', e['c_pos']), ('rot', e['c_rot']), ('scl', e['c_scl']), ('c22', e['c_22']),
                              ('c26', e['c_26'])):
                k = st.curve(cid)
                if k:
                    print('      %s #%d: %s' % (name, cid, ' '.join('%d:%s' % (f, _v(v)) for f, v, _ in k)))
            if e['c_col']:
                print('      col #%d: %s' % (e['c_col'], ' '.join('%d:%s' % (f, c) for f, c, _ in
                                                                  st.colours(e['c_col']))))
            for name, g in (('mesh', e['mesh_anim']), ('anim2', e['anim2'])):
                if g:
                    print('      %s anim #%d: %s' % (name, g, st.mesh_keys(g)))


if __name__ == '__main__':
    sets = container(open(sys.argv[1], 'rb').read())
    if sys.argv[2] == 'list':
        for sid, s in sorted(sets.items()):
            print('%#x' % sid, len(s), Set(s).hdr[1:7])
    elif sys.argv[2] == 'effect':
        show_effect(Set(sets[int(sys.argv[3], 16)]), int(sys.argv[4], 16))
