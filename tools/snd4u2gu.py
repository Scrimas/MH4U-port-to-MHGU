"""snd4u2gu.py : MH4U (3DS) monster sound effects -> MHGU (Switch) formats: Gogmazios (em089) here, any monster through
monster_entries(spec) (monsters/tigerstripe_zamtrios/tools/build_em067_01_arc.py).

  snd4u2gu.py convert [--keep-volume] [OUTDIR]   convert em089's 4U sound call / bank / request / waves; write them
                                                 as OUTDIR/<arc path>.<type hash> (default dump/converted/em089/snd)
  snd4u2gu.py wav OUTDIR                         decode every em089 wave (4U MADP and the converted GU wave) to WAV
  snd4u2gu.py selftest                           check the rules on Capcom's own 4U -> GU conversions (monster pairs)
  import: snd4u2gu.em089_entries(keep_volume=False) -> [(arc path, type hash, data)] in GU arc order

Formats (4U type -> GU type), derived by aligning 4U monsters with the GU files Capcom converted from them
(4U em031 Kushala -> GU em024_00, em028 -> em071_00, em032 -> em027_00, em029 -> em072_00, em088 -> em077_00,
43 pairs for the request statistics) and from the GU loaders (SRQR 0xb67a0c, MSS 0x4d9c7c):

- wave: 4U MADP 0x67195a2e (v5) -> GU 0x79c47b59 (rSoundSourceADPCM, v2). BOTH are mono Nintendo DSP-ADPCM
  (8-byte frames, 16 coefficients), so the sample data is copied bit for bit (lossless, 4U sample rates kept:
  GU plays 8000..22000 Hz waves too).
    4U : 'MADP', u32 5, u8[4] 01 00 00 01, u32 samples, u32 rate, u32 loop flag, u32 loop start, u32 0x60,
         u32 data size (padded 0x100), f32 seconds, u32 0, u32 0x60, s16 coef[16] @0x30, u16 gain, ps, hist1,
         hist2 @0x50, junk to 0x60, data @0x60.
    GU : u32 2, u8[4] 01 00 00 01, u32 exact data bytes, f32 seconds, 8 constant bytes (e1 07 08 02 0c 02 0e 00,
         in every GU wave), s16 coef[16] @0x18, zeros to 0x60, u32 samples, u32 rate, u32 0, u32 0, u32 samples-1,
         u32 0, data @0x78 padded with zeros to a multiple of 0x100.
- bank: 4U SNDB 0x14b5c8e6 (v11) -> GU SBKR 0x15d782fb (v4). Header {magic, ver, nrec, nent, u32 3|4} + nrec
  12-byte group records {u16 id, u16 flags, u32 first entry, u32 x} + nent entries {path\\0, u32 type, 76 bytes}.
    record: 4U flags = 0x8000 | category << 11 | 2*count; GU flags = 0x0800 | 2*count, x = category << 24 | 4U x.
    entry : GU = 4U[0:2] + 00 + 4U[3:12] + 4U[16:75] + 4U[12:16] + 00 (the 4-byte key {lo, hi, root, 0} moved to
            the end; byte 2 = 8 in every 4U entry, 0 in every GU entry), type 0x67195a2e -> 0x79c47b59, wave
            path sound\\se\\em\\em089\\wave\\X -> sound\\se\\em\\em089_00\\wav\\X (GU layout).
- request: 4U SREQ 0x2618de3f (v8, 92-byte entries) -> GU SRQR 0x1bcc4966 (v5, 132-byte entries).
    words 0..21 copied, except (GU's own conversions, 5428 matched entries):
      w5 (per-monster category id, a global table): Kushala's 4U -> GU values, else the majority over all pairs
      w8 &= 0xffff (4U sets bit 16 on every entry), w17 &= 0xffff0000 (4U 0xa000 / 0xa500 low half cleared),
      w18 0x16 -> 0x3b, w9/w10 (dB) - 2.0 (Capcom's dominant GU re-level of 4U requests; --keep-volume skips it)
    4U w22 (runtime pointer slot / build value) dropped; GU words 22..32 = 0, 0, -96.0f, -1, 100, 0, 0, 0, 0, -1, 0
    (identical in every GU entry; 22 = bank pointer slot, 31/32 = section-C index / pointer, filled at load).
    w21 = bank index into the string table: 0 = own bank, 1 = common bank. 4U's common bank is
    sound\\se\\common\\snd_common, GU's sound\\se\\com\\snd_com_qst (in the arc via the donor): every common-bank entry
    is taken verbatim from GU Kushala's request (same IDs 311..345 in all monsters), else converted.
    header (0x34): magic, 5, n, 0, 0, 0, 0, 0x0291df77 (constant in GU), string table offset, end x4.
- sound call: 4U MSS 0x6e171a6e (v 0x20120123) -> GU 0x10ebe843 (v 0x20131015, checked by GU 0x4d9cbc). Same
  layout (u16 motion table[512] @0x10, (key, offset) pairs @0x410, records keyed bank * 1000 + motion, events
  {u16 frame, u16 n, offsets, commands 0x163 (request id, joint, flags) / 0x15e}); 1277 records of the pairs are
  byte-identical between the games: only the version changes.
"""
import os, re, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack

GU_ROMFS = paths.GU_ROMFS
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em089.arc')
DONOR_ARC = '/nativeNX/arc/enemy/em024_00.arc'          # GU Kushala (common-bank request entries)
DEFAULT_OUT = os.path.join(ROOT, 'dump/converted/em089/snd')

T4 = dict(WAVE=0x67195A2E, BANK=0x14B5C8E6, REQ=0x2618DE3F, CALL=0x6E171A6E)
TG = dict(WAVE=0x79C47B59, BANK=0x15D782FB, REQ=0x1BCC4966, CALL=0x10EBE843)

P4_WAVE = 'sound\\se\\em\\em089\\wave\\'
PG_WAVE = 'sound\\se\\em\\em089_00\\wav\\'
P4_BANK = 'sound\\se\\em\\em089\\snd_em089'
PG_BANK = 'sound\\se\\em\\em089_00\\snd_em089_00'          # bank and request share the path (GU layout)
P4_COMMON = 'sound\\se\\common\\snd_common'
PG_COMMON = 'sound\\se\\com\\snd_com_qst'
P4_CALL = 'sound\\call\\em\\em089'
PG_CALL = 'sound\\call\\em\\em089'

GU_WAVE_STAMP = bytes.fromhex('e10708020c020e00')
SRQR_HASH = 0x0291DF77
MSS_V4, MSS_GU = 0x20120123, 0x20131015

# request w5 (category): GU Kushala em024_00 vs 4U Kushala em031 first, then the majority over the 43 pairs
W5_KUSHALA = {0x12C: 0x13B, 0x12D: 0x13C, 0x13B: 0x14F, 0x13C: 0x150, 0x150: 0x163}
W5_GLOBAL = {0x128: 0x137, 0x12E: 0x13D, 0x12F: 0x143, 0x130: 0x144, 0x137: 0x14B, 0x138: 0x14C, 0x141: 0x150,
             0x123: 0x132, 0x50: 0x63}      # values not listed are kept (0x100, 0x132, 0x164, 0x16e, 0x17d: identity)
W18_MAP = {0x16: 0x3B}
DB_SHIFT = -2.0
GU_TAIL = struct.pack('<11I', 0, 0, 0xC2C00000, 0xFFFFFFFF, 100, 0, 0, 0, 0, 0xFFFFFFFF, 0)


# ------------------------------------------------------------------ DSP-ADPCM (both games)

def dsp_data_bytes(samples):
    full, rem = divmod(samples, 14)
    return full * 8 + ((1 + (rem + 1) // 2) if rem else 0)


def dsp_decode(data, coefs, samples):
    """mono Nintendo DSP-ADPCM -> list of int16 (history starts at 0, as both games' headers say)."""
    out = []; h1 = h2 = 0
    for f in range(0, (samples + 13) // 14):
        ps = data[8 * f]; scale = 1 << (ps & 0xF); c1, c2 = coefs[2 * (ps >> 4)], coefs[2 * (ps >> 4) + 1]
        for i in range(14):
            if len(out) == samples: break
            b = data[8 * f + 1 + i // 2]
            n = (b >> 4) if i % 2 == 0 else (b & 0xF)
            if n >= 8: n -= 16
            s = ((n * scale) << 11) + 1024 + c1 * h1 + c2 * h2
            s >>= 11
            s = -32768 if s < -32768 else 32767 if s > 32767 else s
            out.append(s); h2, h1 = h1, s
    return out


def madp_parse(d):
    assert d[:4] == b'MADP' and struct.unpack_from('<I', d, 4)[0] == 5, d[:8]
    ch = d[8]
    samples, rate, loop, lstart, doff, dsize = struct.unpack_from('<6I', d, 0x0C)
    secs = struct.unpack_from('<f', d, 0x24)[0]
    assert doff == 0x60 and ch == 1 and loop == 0, (doff, ch, loop)
    coefs = struct.unpack_from('<16h', d, 0x30)
    n = dsp_data_bytes(samples)
    assert n <= dsize and 0x60 + dsize <= len(d), (n, dsize, len(d))
    return dict(samples=samples, rate=rate, secs=secs, coefs=coefs, data=d[0x60:0x60 + n], flags=d[8:12])


def gu_wave(m):
    """MADP fields -> GU rSoundSourceADPCM v2 bytes (data copied bit for bit)."""
    n = len(m['data'])
    hdr = bytearray(0x78)
    struct.pack_into('<I', hdr, 0, 2)
    hdr[4:8] = m['flags']
    struct.pack_into('<If', hdr, 8, n, m['samples'] / m['rate'])
    hdr[0x10:0x18] = GU_WAVE_STAMP
    struct.pack_into('<16h', hdr, 0x18, *m['coefs'])
    struct.pack_into('<6I', hdr, 0x60, m['samples'], m['rate'], 0, 0, m['samples'] - 1, 0)
    pad = (n + 0xFF) // 0x100 * 0x100
    return bytes(hdr) + m['data'] + bytes(pad - n)


def gu_wave_parse(d):
    v, flags, n, secs = struct.unpack_from('<I4sIf', d, 0)
    assert v == 2 and d[0x10:0x18] == GU_WAVE_STAMP, (v, d[0x10:0x18])
    samples, rate = struct.unpack_from('<II', d, 0x60)
    return dict(samples=samples, rate=rate, secs=secs, coefs=struct.unpack_from('<16h', d, 0x18),
                data=d[0x78:0x78 + n], flags=flags)


# ------------------------------------------------------------------ bank

def bank_parse(d):
    magic, ver, nrec, nent, x = struct.unpack_from('<4s4I', d, 0)
    recs = [struct.unpack_from('<HHII', d, 0x14 + 12 * i) for i in range(nrec)]
    p = 0x14 + 12 * nrec; ents = []
    for _ in range(nent):
        e = d.index(b'\0', p)
        path = d[p:e].decode('ascii'); typ = struct.unpack_from('<I', d, e + 1)[0]
        ents.append((path, typ, d[e + 5:e + 5 + 76])); p = e + 5 + 76
    # trailer: x records {f32 value, u32 index} (index 0..x-1; GU leaves junk in byte 2 of the index word)
    tail = [struct.unpack_from('<fI', d, p + 8 * i) for i in range(x)]
    assert p + 8 * x == len(d), (p, x, len(d))
    return dict(magic=magic, ver=ver, x=x, recs=recs, ents=ents, tail=tail, tail_raw=d[p:])


def bank_rec_gu(r):
    gid, f, start, x = r
    assert not (x >> 24), hex(x)
    if not f & 0x8000:      # stage banks: groups without bit 15 (4U m19a03d 0x10 / 0x0 / 0x2c) keep their flags in GU
        return (gid, f, start, x)       # (Capcom's GU m26a02d, converted from it: 0x22 / 0x0 / 0x1c, x 9 / 0 / 0)
    return (gid, 0x0800 | (f & 0x7FF), start, (((f >> 11) & 0xF) << 24) | x)


def bank_ent_gu(a):
    # byte 2: 4U 8 (10 on a few) -> GU 0 (5726 of 5750 matched entries; em089: 8 everywhere)
    assert len(a) == 76 and a[2] in (8, 10) and a[75] == 0, a.hex()
    return a[0:2] + b'\0' + a[3:12] + a[16:75] + a[12:16] + b'\0'


def bank_build(b4, rename):
    assert b4['magic'] == b'SNDB' and b4['ver'] == 11
    out = [struct.pack('<4s4I', b'SBKR', 4, len(b4['recs']), len(b4['ents']), b4['x'])]
    out += [struct.pack('<HHII', *bank_rec_gu(r)) for r in b4['recs']]
    for path, typ, a in b4['ents']:
        assert typ == T4['WAVE'], hex(typ)
        out.append(rename(path).encode('ascii') + b'\0' + struct.pack('<I', TG['WAVE']) + bank_ent_gu(a))
    assert [i & 0xFF for _, i in b4['tail']] == list(range(b4['x']))     # byte 1 = junk in both games
    out.append(b4['tail_raw'])          # {f32, u32 index} x nx: same layout in GU (values are 4U's)
    return b''.join(out)


# ------------------------------------------------------------------ request

def req4_parse(d):
    magic, ver, n, soff = struct.unpack_from('<4s3I', d, 0)
    assert magic == b'SREQ' and ver == 8 and soff == 0x10 + 92 * n, (magic, ver, soff)
    ents = [struct.unpack_from('<23I', d, 0x10 + 92 * i) for i in range(n)]
    strs = []
    o = soff
    while o + 4 <= len(d):
        so = struct.unpack_from('<I', d, o)[0]
        if not soff < so < len(d): break
        strs.append(d[so:d.index(b'\0', so)].decode('ascii')); o += 4
    return dict(ents=ents, strs=strs)


def reqgu_parse(d):
    magic, ver, n = struct.unpack_from('<4s2I', d, 0)
    assert magic == b'SRQR' and ver == 5
    return dict(ents=[struct.unpack_from('<33I', d, 0x34 + 132 * i) for i in range(n)], hdr=d[:0x34])


def f2u(f): return struct.unpack('<I', struct.pack('<f', f))[0]
def u2f(u): return struct.unpack('<f', struct.pack('<I', u))[0]


def req_ent_gu(w, keep_volume=False):
    g = list(w[:22])
    g[5] = W5_KUSHALA.get(w[5], W5_GLOBAL.get(w[5], w[5]))
    g[8] = w[8] & 0xFFFF
    g[17] = w[17] & 0xFFFF0000
    g[18] = W18_MAP.get(w[18], w[18])
    if not keep_volume:
        for j in (9, 10):
            v = u2f(w[j])
            if v > -96.0: g[j] = f2u(v + DB_SHIFT)
    return struct.pack('<22I', *g) + GU_TAIL


def req_build(r4, common_gu, strs, keep_volume=False, extra=()):
    """r4: parsed 4U SREQ; common_gu: {id: 132-byte GU entry} (donor's common-bank entries); extra: 132-byte GU
    entries appended after the converted ones."""
    ents = []; stats = dict(common_donor=0, common_converted=0)
    for w in r4['ents']:
        rid = w[0] & 0xFFFF
        if w[21] == 1 and rid in common_gu:
            ents.append(common_gu[rid]); stats['common_donor'] += 1; continue
        if w[21] == 1:
            stats['common_converted'] += 1
        e = req_ent_gu(w, keep_volume)
        if w[21] == 1 and (w[4] & 0xFFFF) == 0x0A:      # GU common-bank entries carry 0x14 here (all pairs)
            e = e[:16] + struct.pack('<I', (w[4] & 0xFFFF0000) | 0x14) + e[20:]
        ents.append(e)
    ents += list(extra)
    n = len(ents)
    stab = 0x34 + 132 * n
    blob = b''.join(s.encode('ascii') + b'\0' for s in strs)
    offs = []; o = stab + 4 * len(strs)
    for s in strs:
        offs.append(o); o += len(s) + 1
    end = (stab + 4 * len(strs) + len(blob) + 15) // 16 * 16
    hdr = struct.pack('<4s7I5I', b'SRQR', 5, n, 0, 0, 0, 0, SRQR_HASH, stab, end, end, end, end)
    body = hdr + b''.join(ents) + struct.pack('<%dI' % len(strs), *offs) + blob
    return body + bytes(end - len(body)), stats


# ------------------------------------------------------------------ sound call

def call_build(d):
    magic, ver = struct.unpack_from('<4sI', d, 0)
    assert magic == b'MSS\0' and ver == MSS_V4, (magic, hex(ver))
    return d[:4] + struct.pack('<I', MSS_GU) + d[8:]


# ------------------------------------------------------------------ em089

def _gu_romfs():
    from romfs import RomFS
    return RomFS(GU_ROMFS)


def donor_common_entries(rom=None, donor_arc=DONOR_ARC):
    """{request number: 132-byte entry} of a GU monster's common-bank (bank 1) requests, in file order"""
    rom = rom or _gu_romfs()
    _, dents = arcpack.read(rom.read(donor_arc))
    req = [d for p, t, d in dents if t == TG['REQ']]
    assert len(req) == 1
    g = reqgu_parse(req[0])
    out = {}
    for k, w in enumerate(g['ents']):
        if w[21] == 1:
            out[w[0] & 0xFFFF] = req[0][0x34 + 132 * k:0x34 + 132 * (k + 1)]
    return out


def em089_spec():
    """Gogmazios' sound (tools/build_em089_arc.py) for monster_entries"""
    return dict(name='em089', src=SRC_4U, p4_wave=P4_WAVE, pg_wave=PG_WAVE, p4_bank=P4_BANK, pg_bank=PG_BANK,
                p4_call=P4_CALL, pg_call=PG_CALL, donor_arc=DONOR_ARC, donor_name='GU Kushala', donor_extra=False)


def em089_entries(keep_volume=False, rom=None, log=None):
    """GU arc entries for em089's sound, in GU arc order: call, waves, bank, request."""
    return monster_entries(em089_spec(), keep_volume, rom, log)


def monster_entries(spec, keep_volume=False, rom=None, log=None):
    """GU arc entries for a 4U monster's sound, in GU arc order: call, waves, bank, request. spec: name (log), src (its
    4U arc), p4_wave / p4_bank / p4_call (4U paths), pg_wave / pg_bank / pg_call (GU paths), donor_arc (GU monster
    arc whose common-bank requests replace 4U's: same numbers in every GU monster), donor_name (log), donor_extra
    (also append the donor's common-bank requests whose numbers the 4U request lacks: its GU class may post them)."""
    P4_WAVE, PG_WAVE, P4_BANK, PG_BANK = spec['p4_wave'], spec['pg_wave'], spec['p4_bank'], spec['pg_bank']
    _, src = arcpack.read(open(spec['src'], 'rb').read())
    S = {(p, t): d for p, t, d in src}
    rename = lambda p: PG_WAVE + p[len(P4_WAVE):] if p.startswith(P4_WAVE) else (_ for _ in ()).throw(
        AssertionError('wave outside %s: %s' % (spec['name'], p)))
    b4 = bank_parse(S[(P4_BANK, T4['BANK'])])
    out = [(spec['pg_call'], TG['CALL'], call_build(S[(spec['p4_call'], T4['CALL'])]))]
    used = []
    for path, typ, _ in b4['ents']:
        if path not in used: used.append(path)
    waves = {p for p, t, _ in src if t == T4['WAVE']}
    assert set(used) <= waves, set(used) - waves
    for path in sorted(waves, key=lambda p: (p not in used, used.index(p) if p in used else 0, p)):
        out.append((rename(path), TG['WAVE'], gu_wave(madp_parse(S[(path, T4['WAVE'])]))))
    out.append((PG_BANK, TG['BANK'], bank_build(b4, rename)))
    r4 = req4_parse(S[(P4_BANK, T4['REQ'])])
    # 4U requests name their own bank and the common one; Dalamadur's (em024 / em110) only its own (no entry uses bank 1)
    assert r4['strs'] in ([P4_BANK, P4_COMMON], [P4_BANK]), r4['strs']
    assert len(r4['strs']) == 2 or all(w[21] == 0 for w in r4['ents']), 'common-bank entries without the common bank'
    common = donor_common_entries(rom, spec['donor_arc'])
    have = {w[0] & 0xFFFF for w in r4['ents']}
    extra = [e for k, e in common.items() if k not in have] if spec['donor_extra'] else []
    req, stats = req_build(r4, common, [PG_BANK, PG_COMMON], keep_volume, extra)
    out.append((PG_BANK, TG['REQ'], req))
    if log is not None:
        log.append('%s sound: %d waves (%d used by the bank), bank %d groups / %d entries, request %d entries '
                   '(%d common-bank entries from %s, %d converted%s), sound call %d B' % (
                       spec['name'], len(waves), len(used), len(b4['recs']), len(b4['ents']), len(r4['ents']),
                       stats['common_donor'], spec['donor_name'], stats['common_converted'],
                       ', + %d more of its common-bank requests' % len(extra) if extra else '', len(out[0][2])))
    return out


def verify(entries, spec=None):
    """re-parse everything we produced; waves decode identically to the 4U source."""
    spec = spec or em089_spec()
    P4_WAVE, PG_WAVE = spec['p4_wave'], spec['pg_wave']
    _, src = arcpack.read(open(spec['src'], 'rb').read())
    S = {(p, t): d for p, t, d in src}
    for p, t, d in entries:
        if t == TG['WAVE']:
            g = gu_wave_parse(d); m = madp_parse(S[(P4_WAVE + p[len(PG_WAVE):], T4['WAVE'])])
            assert g['data'] == m['data'] and g['coefs'] == m['coefs'] and g['samples'] == m['samples'], p
            assert len(d) - 0x78 >= len(g['data']) and (len(d) - 0x78) % 0x100 == 0
        elif t == TG['BANK']:
            b = bank_parse(d); assert b['magic'] == b'SBKR' and b['ver'] == 4
            names = {q for q, tt, _ in entries if tt == TG['WAVE']}
            assert all(q in names and tt == TG['WAVE'] for q, tt, _ in b['ents'])
        elif t == TG['REQ']:
            g = reqgu_parse(d)
            stab, end = struct.unpack_from('<II', d, 0x20)
            assert stab == 0x34 + 132 * len(g['ents']) and end == len(d)
        elif t == TG['CALL']:
            assert struct.unpack_from('<I', d, 4)[0] == MSS_GU
    return True


# ------------------------------------------------------------------ selftest on Capcom's conversions

PAIRS = [('em031', 'em024_00'), ('em028', 'em071_00'), ('em032', 'em027_00'), ('em029', 'em072_00'),
         ('em088', 'em077_00')]


def selftest():
    rom = _gu_romfs()
    tot = dict(rec=0, rec_ok=0, ent=0, ent_ok=0, req=0, req_ok=0)
    for a4, g in PAIRS:
        _, s4 = arcpack.read(open(os.path.join(ROOT, 'dump/romfs/data/%s.arc' % a4), 'rb').read())
        _, sg = arcpack.read(rom.read('/nativeNX/arc/enemy/%s.arc' % g))
        b4 = bank_parse([d for p, t, d in s4 if t == T4['BANK'] and a4 in p][0])
        bg = bank_parse([d for p, t, d in sg if t == TG['BANK'] and g in p][0])
        rg = {r[0]: r for r in bg['recs']}
        for r in b4['recs']:
            if r[0] in rg and rg[r[0]][2] == r[2] and (rg[r[0]][1] & 0x7FF) == (r[1] & 0x7FF):
                tot['rec'] += 1; tot['rec_ok'] += bank_rec_gu(r)[:3] == rg[r[0]][:3] and \
                    (bank_rec_gu(r)[3] >> 24) == (rg[r[0]][3] >> 24)
        key = lambda p: re.sub(r'^em\d+_', '', p.split('\\')[-1].lower()).replace('vf_', 'se_')
        gi = {}
        for p, t, e in bg['ents']: gi.setdefault((key(p), e[71]), e)
        for p, t, a in b4['ents']:
            e = gi.get((key(p), a[12]))
            if e is None: continue
            c = bank_ent_gu(a)
            tot['ent'] += 1
            # byte 5 (volume) and 32 are re-tuned per monster by Capcom: structure = every other byte
            tot['ent_ok'] += all(c[j] == e[j] for j in range(76) if j not in (5, 32))
        r4 = req4_parse([d for p, t, d in s4 if t == T4['REQ'] and a4 in p][0])
        rq = reqgu_parse([d for p, t, d in sg if t == TG['REQ'] and g in p][0])
        ig = {w[0]: w for w in rq['ents']}
        for w in r4['ents']:
            wg = ig.get(w[0])
            if not wg or wg[4] != w[4] or wg[21] != w[21]: continue
            c = struct.unpack('<33I', req_ent_gu(w, keep_volume=True))
            tot['req'] += 1
            tot['req_ok'] += all(c[j] == wg[j] for j in range(33) if j not in (5, 6, 7, 9, 10, 11, 14, 15, 20, 3, 18))
        c4 = [d for p, t, d in s4 if t == T4['CALL']][0]
        assert call_build(c4)[8:0x10] == c4[8:0x10]
    print('bank records  %d / %d' % (tot['rec_ok'], tot['rec']))
    print('bank entries  %d / %d (all bytes except the per-monster volume/distance bytes 5, 32)' % (
        tot['ent_ok'], tot['ent']))
    print('request ents  %d / %d (structural words; tuned words 3,5,6,7,9-11,14,15,18,20 excluded)' % (
        tot['req_ok'], tot['req']))


def write_wav(path, pcm, rate):
    import array
    a = array.array('h', pcm)
    raw = a.tobytes()
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + len(raw)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate,
                rate * 2, 2, 16) + b'data' + struct.pack('<I', len(raw)) + raw)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'convert'
    if cmd == 'convert':
        keep = '--keep-volume' in sys.argv
        args = [a for a in sys.argv[2:] if not a.startswith('--')]
        out = args[0] if args else DEFAULT_OUT
        log = []
        ents = em089_entries(keep, log=log)
        verify(ents)
        os.makedirs(out, exist_ok=True)
        order = []
        for p, t, d in ents:
            fn = os.path.join(out, p.replace('\\', '/') + '.%08x' % t)
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            open(fn, 'wb').write(d); order.append('%s.%08x' % (p.replace('\\', '/'), t))
        open(os.path.join(out, '_order.txt'), 'w').write('\n'.join(order) + '\n')
        for l in log: print(l)
        print('%d files -> %s (verified)' % (len(ents), out))
    elif cmd == 'wav':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for p, t, d in em089_entries():
            if t != TG['WAVE']: continue
            g = gu_wave_parse(d)
            write_wav(os.path.join(out, p.split('\\')[-1] + '.wav'), dsp_decode(g['data'], g['coefs'], g['samples']),
                      g['rate'])
        print('wavs ->', out)
    elif cmd == 'selftest':
        selftest()
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
