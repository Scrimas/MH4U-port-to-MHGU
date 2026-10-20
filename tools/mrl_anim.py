"""mrl_anim.py : MRL material animation blocks (entry w12 = size, w14 = offset), MH4U (v0x20) and MHGU (v0x22).

  mrl_anim.py dump FILE.mrl          every material's animations, tracks and keys

GU runtime (C = code read, MHGU 1.4 main): material object = monster this+0xf8[i], i < this+0xfc (0x890adc);
type = (obj+0x18 >> 22) & 0xff, copied from MRL entry w6 bits 21-28 at load (0xb45f74) = the 'mNN' of the
material name (em049 types 51-56, 4U em089 m01..m05 tar, m06 lights, m50 wing; 4U keeps it in the same bits of
its own object, slot 39 0x8b9e28); obj+0x74 = animation set (+0x10 -> {count, entry*[count]});
find 0xb0bb0c(set, const char *name) -> index or -1 (crc of the name = the entry name hash);
play 0xb0cab0(obj, slot 0..3, index): obj+0x50+8*slot = index (0xffff = off), obj+0x54+8*slot = frame (f32) = 0;
current 0xb0ffb8(obj, slot) = (s16) obj+0x50+8*slot. Per-frame evaluation 0xb0ffc4 -> 0xb0ea4c (all 4 slots).
At load every slot is 0xffff, then entries with flags bit 1 fill slots 0.. in order (0xb0cbe0).

Layout (same in both games, decoded on 4U em089.mrl and GU em049_00 / em080_00):
  block   u32 count, u32 entry offset[count]                       (offsets from the block start)
  entry   u32 frames, u32 flags, u32 cb list offset, u32 name hash (crc32(name) ^ ~0, e.g. 'Solid'),
          u32 track offset[ntracks]                     (ntracks = (cb list offset - entry - 16) / 4)
          flags: u16 low = (ntracks << 2) | loop bit (S), u16 high = cb list size in bytes
  cb list u32 constant-buffer state words used by the tracks (count = (flags >> 16) / 4)
  track   u32 cb state word, u8 kind, u8 nkeys, u16 0, u32 variable word, nkeys x {u32 frame, f32 v[n]}
          variable word = (cb record << 22) | (float offset << 12) | (cols - 1) << 10 | (rows - 1) << 8 | 1
          kind & 0xF: 0 = 1 float, 1 = 4 floats (colour), 6 = 5 floats (UV transform: offset u, v, scale u, v,
          rotation) -> n, 3 = texture index (GU em013_01); kind >> 4: 1 or 2 (interpolation?, GU uses both)
          loop bit: 4U Solid/Liquid/Gas 0x11, transitions 0x10, Small/Large 5, SmalltoLarge 4; GU 8/9
"""
import struct, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mrl

KIND_FLOATS = {0: 1, 1: 4, 3: 1, 6: 5}      # 3 = texture swap (u32 texture index; cb word = texture slot)


def parse(blk):
    n = struct.unpack_from('<I', blk, 0)[0]
    offs = struct.unpack_from('<%dI' % n, blk, 4)
    out = []
    for o in offs:
        frames, flags, cbl, nh = struct.unpack_from('<4I', blk, o)
        nt = (cbl - o - 16) // 4
        toffs = struct.unpack_from('<%dI' % nt, blk, o + 16)
        cbs = list(struct.unpack_from('<%dI' % ((flags >> 16) // 4), blk, cbl))
        tracks = []
        for t in toffs:
            cbw, kind, nk, pad, var = struct.unpack_from('<IBBHI', blk, t)
            nf = KIND_FLOATS[kind & 0xF]
            fmt = '<II' if kind & 0xF == 3 else '<I%df' % nf
            keys = [struct.unpack_from(fmt, blk, t + 12 + k * 4 * (1 + nf)) for k in range(nk)]
            tracks.append(dict(cb=cbw, kind=kind, pad=pad, var=var, keys=keys,
                               size=12 + nk * 4 * (1 + nf), off=t))
        out.append(dict(off=o, frames=frames, flags=flags, name=nh, cbs=cbs, tracks=tracks))
    return out


def var_name(ver, cbw, var):
    """(cb name, variable name) of a track."""
    cb = mrl.rec_name(ver, cbw)
    fo = (var >> 12) & 0xFF
    lay = mrl.cb_layout(ver, cb) if cb else {}
    names = [k for k, (o, r, c) in lay.items() if o == fo and k[:1] in 'fbi']
    return cb, names[0] if names else 'f%d' % fo


NAMES = ['Solid', 'Liquid', 'Gas', 'Sol_to_Liq', 'Liq_to_Sol', 'Liq_to_Gas', 'Gas_to_Liq', 'Sol_to_Gas',
         'Gas_to_Sol', 'Small', 'SmalltoLarge', 'LargetoSmall', 'Large']
NAMES += ['Light_%s' % s for s in ('On', 'Off', 'OnToOff', 'OffToOn', 'Loop', 'Start', 'End')]
# em089's lights material (type 6): the 4U name table at 0xff6fb4 (slot 39 looks them up in this order)
LIGHT_NAMES = ['Light_Gas_Bress', 'Light_Gas_Bress_End', 'Light_Wing_Attack_back', 'Light_Wing_Attack',
               'Light_Wing_Attack_gekiryusou', 'Light_Wing_Attack_houdai', 'Light_Tail_Attack01', 'Light_Tail_Attack02']
NAMES += LIGHT_NAMES
HASHNAME = {mrl.name_hash(s): s for s in NAMES}


def material_anims(d):
    """{material name hash: [entries]} of an MRL file (4U entry w12 = size, w14 = offset, as in GU)."""
    ver = struct.unpack_from('<I', d, 4)[0]
    nmat = struct.unpack_from('<I', d, 8)[0]
    moff = struct.unpack_from('<I', d, 24)[0]
    out = {}
    for i in range(nmat):
        w = struct.unpack_from('<15I', d, moff + 60 * i)
        if w[12]:
            out[w[1]] = parse(d[w[14]:w[14] + w[12]])
    return ver, out


def first_frame(entry, ver):
    """{(cb name, variable name): values of the first key} of one animation entry."""
    return {var_name(ver, t['cb'], t['var']): t['keys'][0][1:] for t in entry['tracks']}


# ---- 4U -> GU conversion
# 4U tracks target the LUT-shading CBMaterialStd; GU's equivalents live in $Globals / CBMaterial (names from both
# packages). Specular: 4U .w is the gloss amount (Solid 0.1 matte, Liquid 0.8 wet, Gas 1.0), GU has no such term,
# so the GU colour is rgb * w. Emission (lights material only): -> $Globals.fEmissionColor, 4-float kind 0x11 as
# GU's own fEmissionColor tracks (76 in the enemy MRLs, var = float3 at f48).
# Diffuse (tar-look agent, 2026-10-18): 4U fMaterialStdDiffuse = (diffuse rgb, material ALPHA w). Capcom's own 3DS ->
# GU conversions write it as a 4-float track on CBMaterial.fDiffuseColor (kind 0x11, var = float3 at f0) PLUS a
# 1-float track on CBMaterial.fTransparency (f3, kind 0x10) with the same keys as w (GU em025_00 mats 2-5,
# em079_04 mats 0/2/4: w 0 -> 0.221 -> 0.69 -> 1 in 30 frames in both tracks); with FTransparencyAlpha the GU
# alpha is albedo.a * fTransparency, alpha-tested against the MRL entry's w7 reference (mrl_build). `alpha`
# scales w: em089's tar also multiplies the 4U per-vertex alpha (N.w), which GU's vertex format lacks, so
# tools/mod4u2gu.py splits the tar meshes into vertex-alpha classes and each class material gets w * class.
# UV transform: the v offset changes sign (GU UV v = 1 - 4U v, tools/mod4u2gu.py). Capcom's own conversions do
# the same: 4U em032 mat 42b876fc v 0 -> +1 / 150 f = GU em027_00 mat 42b876fc v 0 -> -1; 4U em032 30869c45
# (1 -> -4) = GU (-1 -> +4); u is kept (4U em011 6eae2464 u 0 -> 0.15 -> 0.5 = GU em032_00), and every GU key
# has v = -0.0 where 4U has 0.0. Until 2026-10-18 the tar scrolled upward in GU (v copied unchanged).
# map: 4U (cb, var) -> [((GU cb, GU var), f(values, alpha) -> values, kind & 0xF override or None = 4U kind)]
TRACK_MAP = {
    ('CBMaterial', 'fUVTransform'): [(('CBMaterial', 'fUVTransform'),
                                      lambda v, a: (v[0], -v[1]) + tuple(v[2:]), None)],
    ('CBMaterialStd', 'fMaterialStdAlbedoColor'): [(('$Globals', 'fAlbedoColor'), lambda v, a: v, None)],
    ('CBMaterialStd', 'fMaterialStdSpecular'): [(('$Globals', 'fSpecularColor'),
                                                 lambda v, a: (v[0] * v[3], v[1] * v[3], v[2] * v[3], v[3]), None)],
    ('CBMaterialStd', 'fMaterialStdDiffuse'): [(('CBMaterial', 'fDiffuseColor'),
                                                lambda v, a: (v[0], v[1], v[2], v[3] * a), None),
                                               (('CBMaterial', 'fTransparency'), lambda v, a: (v[3] * a,), 0)],
    ('CBMaterialStd', 'fMaterialStdEmission'): [(('$Globals', 'fEmissionColor'), lambda v, a: v, None)],
}


def animated_targets(entries4):
    """set of (GU cb, GU var) that the converted tracks of these 4U entries write."""
    out = set()
    for e in entries4:
        for t in e['tracks']:
            out |= {g for g, _, _ in TRACK_MAP.get(var_name(0x20, t['cb'], t['var']), ())}
    return out


def static_constants(std_block, alpha=1.0):
    """{(GU cb, GU var): values} of a 4U material's own CBMaterialStd constants (bytes of the buffer) for the
    mapped variables (emission, diffuse + alpha, specular, albedo), cut to the GU variable's size."""
    import struct as _s
    out = {}
    for var, (fo, rows, cols) in mrl.cb_layout(0x20, 'CBMaterialStd').items():
        if ('CBMaterialStd', var) not in TRACK_MAP: continue
        vals = _s.unpack_from('<%df' % (rows * cols), std_block, 4 * fo)
        for (gcb, gvar), v in map_values('CBMaterialStd', var, vals, alpha):
            gfo, grows, gcols = mrl.cb_layout(0x22, gcb)[gvar]
            out[(gcb, gvar)] = v[:grows * gcols]
    return out
FLAG_LOOP, FLAG_AUTOPLAY = 1, 2   # GU 0xb0cbe0: entries with bit 1 are put in the 4 play slots at load (S: bit 0)


def gu_var_word(cbname, var, cb_word):
    fo, rows, cols = mrl.cb_layout(0x22, cbname)[var]
    return ((cb_word & 0xFFF) << 22) | (fo << 12) | ((cols - 1) << 10) | ((rows - 1) << 8) | 1


def map_values(cb, var, values, alpha=1.0):
    """4U (cb, var, values) -> [((GU cb, GU var), values)] ([] when the track has no GU equivalent)."""
    return [(g, tuple(f(values, alpha))) for g, f, _ in TRACK_MAP.get((cb, var), ())]


def solid_constants(entry, alpha=1.0):
    """{(GU cb, GU var): values cut to the variable's size} of a 4U entry's first frame (UV keys are (u, v, su, sv,
    rot), not the matrix: skipped), to bake the steady state the material starts in into the GU constants."""
    out = {}
    for (cb, var), vals in first_frame(entry, 0x20).items():
        for (gcb, gvar), v in map_values(cb, var, vals, alpha):
            if gvar == 'fUVTransform': continue
            fo, rows, cols = mrl.cb_layout(0x22, gcb)[gvar]
            out[(gcb, gvar)] = v[:rows * cols]
    return out


def gu_entries(entries4, cb_words, autoplay=(), alpha=1.0):
    """4U entries -> GU entries (same order, names, frames, keys). cb_words = {GU cb name: the material's state word
    of that constant buffer (its descriptor word)}; autoplay = names given the autoplay flag; alpha = scale of the
    4U diffuse w (material alpha), see TRACK_MAP."""
    out = []
    for e in entries4:
        tracks = []
        for t in e['tracks']:
            cb, var = var_name(0x20, t['cb'], t['var'])
            for k, ((gcb, gvar), f, kind) in enumerate(TRACK_MAP.get((cb, var), ())):
                keys = [(key[0],) + map_values(cb, var, key[1:], alpha)[k][1] for key in t['keys']]
                tracks.append(dict(cb=cb_words[gcb], kind=t['kind'] if kind is None else (t['kind'] & 0xF0) | kind,
                                   var=gu_var_word(gcb, gvar, cb_words[gcb]), keys=keys))
        flags = (len(tracks) << 2) | (e['flags'] & FLAG_LOOP) | \
            (FLAG_AUTOPLAY if HASHNAME.get(e['name']) in autoplay else 0)
        out.append(dict(name=e['name'], frames=e['frames'], flags=flags, tracks=tracks))
    return out


def build(entries):
    """GU material animation block (layout above) from [{name, frames, flags (low 16 bits), tracks}]."""
    head = 4 + 4 * len(entries)
    body = bytearray()
    offs = []
    for e in entries:
        o = head + len(body)
        offs.append(o)
        cbs = []
        for t in e['tracks']:
            if t['cb'] not in cbs: cbs.append(t['cb'])
        nt = len(e['tracks'])
        cbl = o + 16 + 4 * nt
        t_off = cbl + 4 * len(cbs)
        toffs, tdata = [], bytearray()
        for t in e['tracks']:
            toffs.append(t_off + len(tdata))
            tdata += struct.pack('<IBBHI', t['cb'], t['kind'], len(t['keys']), 0, t['var'])
            for k in t['keys']:
                tdata += struct.pack('<I%df' % (len(k) - 1), *k)
        body += struct.pack('<4I', e['frames'], ((4 * len(cbs)) << 16) | (e['flags'] & 0xFFFF), cbl, e['name'])
        body += struct.pack('<%dI' % nt, *toffs) + struct.pack('<%dI' % len(cbs), *cbs) + tdata
    return struct.pack('<I%dI' % len(entries), len(entries), *offs) + bytes(body)


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        d = open(sys.argv[2], 'rb').read()
        ver, A = material_anims(d)
        for mh, entries in A.items():
            print('material %08x: %d animations' % (mh, len(entries)))
            for e in entries:
                print('  %-14s frames %4d flags %08x cbs %s' % (HASHNAME.get(e['name'], '%08x' % e['name']),
                      e['frames'], e['flags'], [mrl.rec_name(ver, c) for c in e['cbs']]))
                for t in e['tracks']:
                    cb, var = var_name(ver, t['cb'], t['var'])
                    print('      %s.%s kind %02x var %08x keys %s' % (cb, var, t['kind'], t['var'],
                          [(k[0],) + tuple(round(x, 3) for x in k[1:]) for k in t['keys']]))
