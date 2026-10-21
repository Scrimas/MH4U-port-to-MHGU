"""snd_bgm.py : MH4U Gogmazios battle BGM (and the Battlequarters streams) -> MHGU Opus streams + battle STQR.

  snd_bgm.py all [--keep]        extract, decode, encode, level, write the opus files + the extended bgm_bt.stqr
                                 into monsters/gogmazios/romfs/nativeNX/sound/bgm/... (work files: dump/converted/bgm/)
  snd_bgm.py check FILE.opus     parse a GU (Capcom) opus stream, decode it, print levels
  snd_bgm.py stqr                only rebuild bgm_bt.stqr from the already written opus files

Sources: 4U ROM dump/base/*.3ds (tools/ctr.py): /sound/bgm/battle/wav/bgm_em089.mca (phase 1), bgm_em089_2.mca
(phase 2), bgm_bat.stq (4U sequences: em089 = id 32 at 0.0 dB, em089_2 = id 33 at -0.9 dB); Battlequarters
/sound/bgm/stage/wav/bgm_map_19.mca (stage theme of bgm_st_19.stq) and /sound/bgm/str_map/m19/wav/m19_a0Nd.mca
(area streams of str_m19.stq). GU: base RomFS sound/bgm/battle/bgm_bt.stqr + its opus files.

4U .mca = MADP v5 stereo: u32 samples @0x0c, rate @0x10 (32728), loop start/end @0x14/0x18, data size @0x20,
  seconds f32 @0x24, seek entries @0x28 (20 B each from 0x30), data offset @0x2c; per channel 0x30 bytes
  {s16 coef[16], gain, ps, hist1, hist2, loop ps, loop hist1, loop hist2, pad} after the seek table; DSP-ADPCM data
  interleaved per 0x100 bytes (checked: the seek table's per-channel ps bytes match frame headers only for 0x100).
GU .opus (Capcom wrapper, all 512 GU files share the constants): u32 samples, channels, loop start, loop end,
  0xf8 (= 8 + packet bytes), marker count, 0, offset of the Nintendo Opus header, 0x02c17700, 4, 8-byte date,
  markers {u32 0x7f, u32 sample} (optional: Ostgaloa01 has none), then the Nintendo header {0x80000001, 0x18,
  u8 0, u8 channels, u16 240, u32 48000, u32 0x20, 0, 0, u32 pre-skip 120} and the data chunk {0x80000004, size}
  of packets {u32 BE size, u32 BE encoder final range, payload}. GU: CELT-only 20 ms stereo 48 kHz CBR 240 B
  (96 kb/s, TOC 0xfc, pre-skip 120 = libopus RESTRICTED_LOWDELAY lookahead) -> encoded the same way here with the
  system libopus (ctypes), after soxr resampling 32728 -> 48000 Hz (ffmpeg).
GU STQR v8: header {magic, 8, streams, sequences, 16 zero bytes, stream table, sequence table, 4 x string table},
  streams 36 B {name offset, file size, samples, channels, rate, loop start, loop end, 0x15542770, 0},
  sequences 140 B {u32 request id, ..., f32 dB @+36, ..., u32 stream index @+92, ...}, names. The battle file is
  rebuilt byte-identical, then 2 streams + 2 sequences are APPENDED (ids EM089_BGM_ID1/2; no GU entry changes).
"""
import ctypes, ctypes.util, math, os, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)

ROM_4U = os.path.join(ROOT, 'dump/base/Monster Hunter 4 Ultimate (EUR) Decrypted.3ds')
GU_ROMFS = paths.GU_ROMFS
WORK = os.path.join(ROOT, 'dump/converted/bgm')
GOG_ROMFS = paths.romfs('gogmazios')
OUT = os.path.join(GOG_ROMFS, 'nativeNX/sound/bgm')
GU_BT = '/nativeNX/sound/bgm/battle/bgm_bt.stqr'

import alloc
EM089_BGM_ID1, EM089_BGM_ID2 = alloc.monster('gogmazios')['bgm_ids']   # phase 1 / 2 (4U ids 32 / 33): allocations.toml
TRACKS = [   # (4U file, GU stream path, 4U dB from bgm_bat.stq, id)
    ('sound/bgm/battle/wav/bgm_em089.mca', 'sound\\bgm\\battle\\wav\\bgm_em089_Gogmazios1', 0.0, EM089_BGM_ID1),
    ('sound/bgm/battle/wav/bgm_em089_2.mca', 'sound\\bgm\\battle\\wav\\bgm_em089_Gogmazios2', -0.9, EM089_BGM_ID2),
]
STAGE = [   # Battlequarters area streams (4U str_m19) -> alias m28d stream slots (tools/stage4u2gu.py bgm_stqr reads
    # dump/converted/bgm_m28.json): GU area 0 <- 4U a00 (camp), 1 <- a01, 2 <- a03 (arena); (4U file, GU path, slot)
    ('sound/bgm/str_map/m19/wav/m19_a00d.mca', 'sound\\bgm\\map\\m28d\\wav\\m28a00d', 0),
    ('sound/bgm/str_map/m19/wav/m19_a01d.mca', 'sound\\bgm\\map\\m28d\\wav\\m28a01d', 1),
    ('sound/bgm/str_map/m19/wav/m19_a03d.mca', 'sound\\bgm\\map\\m28d\\wav\\m28a02d', 2),
    # 4U stage jingle of bgm_st_19 (request 10, -2.7 dB, non-looping) = GU's camp jingle mNNcmpd (map STQR request
    # 0x32, non-looping 20-30 s, same category 1); the Fortress has none -> added as stream 4 of the m28d STQR
    ('sound/bgm/stage/wav/bgm_map_19.mca', 'sound\\bgm\\map\\m28d\\wav\\m28cmpd', None),
]
STAGE_JINGLE_DB_4U = -2.7
GU_M26D = '/nativeNX/sound/bgm/map/m26d/bgm_m26d.stqr'     # = the copy in m28d.arc (type 0x167dbbff)
GU_CMP_TEMPLATE = ('/nativeNX/sound/bgm/map/m09d/bgm_m09d.stqr', 0x32)   # a GU camp-jingle sequence
M28D_STQR = os.path.join(ROOT, 'dump/converted/bgm_m28d.stqr')
EM089_STQR = os.path.join(ROOT, 'dump/converted/bgm_em089.stqr')    # arc entry sound\bgm\battle\bgm_em089
EM089_STQR_PATH = 'sound\\bgm\\battle\\bgm_em089'
T_STQR = 0x167DBBFF
BGM_M28_JSON = os.path.join(ROOT, 'dump/converted/bgm_m28.json')
# loudness anchors: the same monster's theme in both games (4U bgm_bat.stq stream, GU bgm_bt.stqr stream)
ANCHORS = [('bgm_em031', 'bgm_em024_Daola'), ('bgm_em032', 'bgm_em027_Teo'), ('bgm_em033', 'bgm_em033_Akantor'),
           ('bgm_em028', 'bgm_em071_Gore'), ('bgm_em029', 'bgm_em072_Shagal'), ('bgm_em088', 'bgm_em077_Sellegios')]

GU_OPUS_DATE = bytes.fromhex('e10708020b393300')
GU_OPUS_C20, GU_OPUS_C24 = 0x02C17700, 4
STREAM_HASH = 0x15542770
RATE, FRAME, PACKET, PRESKIP = 48000, 960, 240, 120


# ------------------------------------------------------------------ 4U MCA (stereo MADP)

def mca_parse(d):
    assert d[:4] == b'MADP' and struct.unpack_from('<I', d, 4)[0] == 5
    ch = d[8]
    ns, rate, ls, le, x1c, dsz = struct.unpack_from('<6I', d, 0x0C)
    nseek, doff = struct.unpack_from('<II', d, 0x28)
    cb = 0x30 + 20 * nseek
    coefs = [struct.unpack_from('<16h', d, cb + 0x30 * c) for c in range(ch)]
    assert cb + 0x30 * ch <= doff
    return dict(ch=ch, ns=ns, rate=rate, ls=ls, le=le, coefs=coefs, data=d[doff:doff + dsz], loop=le > ls)


def mca_decode(m, inter=0x100):
    """-> bytes s16le interleaved."""
    import array
    ch, ns, data = m['ch'], m['ns'], m['data']
    chans = []
    for c in range(ch):
        coefs = m['coefs'][c]
        nfr = (ns + 13) // 14
        buf = bytearray()
        per = inter // 8
        for f0 in range(0, nfr, per):
            o = ((f0 * 8) // inter * ch + c) * inter
            buf += data[o:o + inter]
        out = array.array('h', bytes(2 * ns)); h1 = h2 = 0; k = 0
        for f in range(nfr):
            ps = buf[8 * f]; sc = 1 << (ps & 15); c1 = coefs[2 * (ps >> 4)]; c2 = coefs[2 * (ps >> 4) + 1]
            for i in range(14):
                if k == ns: break
                b = buf[8 * f + 1 + (i >> 1)]
                n = (b >> 4) if not i & 1 else (b & 15)
                if n >= 8: n -= 16
                s = (((n * sc) << 11) + 1024 + c1 * h1 + c2 * h2) >> 11
                s = -32768 if s < -32768 else 32767 if s > 32767 else s
                out[k] = s; k += 1; h2 = h1; h1 = s
        chans.append(out)
    inter_pcm = array.array('h', bytes(2 * ns * ch))
    for c in range(ch): inter_pcm[c::ch] = chans[c]
    return inter_pcm.tobytes()


def resample(pcm, rate_in, ch=2):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 's16le', '-ar', str(rate_in), '-ac',
                        str(ch), '-i', 'pipe:0', '-af', 'aresample=%d:resampler=soxr:precision=28' % RATE,
                        '-f', 's16le', '-ac', str(ch), 'pipe:1'], input=pcm, capture_output=True, check=True)
    return r.stdout


# ------------------------------------------------------------------ libopus (system library, ctypes)

_lib = None


def lib():
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL(ctypes.util.find_library('opus'))
        _lib.opus_encoder_create.restype = ctypes.c_void_p
        _lib.opus_decoder_create.restype = ctypes.c_void_p
        _lib.opus_encode.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        _lib.opus_decode.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                     ctypes.c_int]
    return _lib


OPUS_APPLICATION_RESTRICTED_LOWDELAY = 2051
SET_BITRATE, SET_VBR, SET_COMPLEXITY, SET_SIGNAL, GET_LOOKAHEAD, GET_FINAL_RANGE = 4002, 4006, 4010, 4024, 4027, 4031
SET_FORCE_CHANNELS = 4022     # GU packets are all stereo (TOC 0xfc): no mono fallback on quiet frames
SET_BANDWIDTH, BANDWIDTH_FULLBAND = 4008, 1105   # and fullband (quiet passages otherwise drop to SWB, TOC 0xdc)
SIGNAL_MUSIC = 3002


def opus_encode(pcm48, ch=2):
    """s16le interleaved 48 kHz -> [(packet, final range)], lookahead."""
    L = lib(); err = ctypes.c_int()
    enc = L.opus_encoder_create(RATE, ch, OPUS_APPLICATION_RESTRICTED_LOWDELAY, ctypes.byref(err))
    assert err.value == 0, err.value
    e = ctypes.c_void_p(enc)
    for req, v in ((SET_BITRATE, PACKET * 8 * RATE // FRAME), (SET_VBR, 0), (SET_COMPLEXITY, 10),
                   (SET_SIGNAL, SIGNAL_MUSIC), (SET_FORCE_CHANNELS, ch), (SET_BANDWIDTH, BANDWIDTH_FULLBAND)):
        assert L.opus_encoder_ctl(e, req, ctypes.c_int(v)) == 0, req
    la = ctypes.c_int(); L.opus_encoder_ctl(e, GET_LOOKAHEAD, ctypes.byref(la))
    step = FRAME * ch * 2
    n = (len(pcm48) + step - 1) // step
    pcm48 = pcm48 + bytes(n * step - len(pcm48))
    out = []; buf = ctypes.create_string_buffer(1500); rng = ctypes.c_uint32()
    for i in range(n):
        k = L.opus_encode(e, pcm48[i * step:(i + 1) * step], FRAME, buf, 1500)
        assert k > 0, k
        L.opus_encoder_ctl(e, GET_FINAL_RANGE, ctypes.byref(rng))
        out.append((buf.raw[:k], rng.value))
    L.opus_encoder_destroy(e)
    return out, la.value


def opus_decode(packets, ch=2):
    L = lib(); err = ctypes.c_int()
    dec = ctypes.c_void_p(L.opus_decoder_create(RATE, ch, ctypes.byref(err)))
    assert err.value == 0
    pcm = ctypes.create_string_buffer(5760 * ch * 2); out = bytearray()
    for p in packets:
        k = L.opus_decode(dec, p, len(p), pcm, 5760, 0)
        assert k > 0, k
        out += pcm.raw[:k * ch * 2]
    L.opus_decoder_destroy(dec)
    return bytes(out)


# ------------------------------------------------------------------ GU (Capcom) opus container

def gu_opus_build(packets, ns, ls, le, ch=2):
    nx = 0x30
    hdr = struct.pack('<10I', ns, ch, ls, le, 8 + PACKET, 0, 0, nx, GU_OPUS_C20, GU_OPUS_C24) + GU_OPUS_DATE
    nxh = struct.pack('<IIBBHIIIII', 0x80000001, 0x18, 0, ch, PACKET, RATE, 0x20, 0, 0, PRESKIP)
    body = b''.join(struct.pack('>II', len(p), r) + p for p, r in packets)
    return hdr + nxh + struct.pack('<II', 0x80000004, len(body)) + body


def gu_opus_parse(d):
    ns, ch, ls, le, f10, nm, f18, nxoff, f20, f24 = struct.unpack_from('<10I', d, 0)
    t, hs, ver, nch, fsz, rate, doff, a, b, pre = struct.unpack_from('<IIBBHIIIII', d, nxoff)
    assert t == 0x80000001 and rate == RATE
    dt, dsz = struct.unpack_from('<II', d, nxoff + doff)
    assert dt == 0x80000004
    p = nxoff + doff + 8; pk = []
    while p < nxoff + doff + 8 + dsz:
        sz, rng = struct.unpack_from('>II', d, p); pk.append(d[p + 8:p + 8 + sz]); p += 8 + sz
    return dict(ns=ns, ch=ch, ls=ls, le=le, f10=f10, markers=nm, nxoff=nxoff, f20=f20, f24=f24, fsz=fsz,
                preskip=pre, packets=pk)


def rms_db(pcm):
    import array
    a = array.array('h', pcm)
    s = sum(x * x for x in a[::7]) / max(1, len(a[::7]))
    return 10 * math.log10(max(s, 1e-9) / 32768.0 ** 2)


# ------------------------------------------------------------------ STQR

def stqr_parse(d):
    mag, ver, ns, nq = struct.unpack_from('<4s3I', d, 0)
    assert mag == b'STQR' and ver == 8
    so, qo, s1, s2, s3, s4 = struct.unpack_from('<6I', d, 0x20)
    assert s1 == s2 == s3 == s4 and (qo + 140 * nq + 15) // 16 * 16 == s1, 'unexpected layout'
    streams = []
    for i in range(ns):
        w = list(struct.unpack_from('<9I', d, so + 36 * i))
        name = d[w[0]:d.index(b'\0', w[0])].decode('ascii')
        streams.append([name] + w[1:])
    seqs = [d[qo + 140 * i:qo + 140 * (i + 1)] for i in range(nq)]
    return dict(head=d[0x10:0x20], streams=streams, seqs=seqs, end=len(d))


def stqr_build(s):
    ns, nq = len(s['streams']), len(s['seqs'])
    so = 0x38; qo = so + 36 * ns; st = (qo + 140 * nq + 15) // 16 * 16     # names 16-aligned (all GU STQRs)
    names = b''; offs = []
    for st_ in s['streams']:
        offs.append(st + len(names)); names += st_[0].encode('ascii') + b'\0'
    out = struct.pack('<4s3I', b'STQR', 8, ns, nq) + s['head'] + struct.pack('<6I', so, qo, st, st, st, st)
    for o, st_ in zip(offs, s['streams']):
        out += struct.pack('<9I', o, *st_[1:])
    out += b''.join(s['seqs'])
    return out + bytes(st - len(out)) + names


# ------------------------------------------------------------------ pipeline

def extract(paths):
    """4U ROM files -> WORK/4u/<path> (tools/ctr.py)."""
    want = [p for p in paths if not os.path.exists(os.path.join(WORK, '4u', p))]
    if want:
        pat = '^/(' + '|'.join(p.replace('.', '\\.') for p in want) + ')$'
        subprocess.run([sys.executable, os.path.join(HERE, 'ctr.py'), 'x', ROM_4U, pat, os.path.join(WORK, '4u')],
                       check=True, capture_output=True)
    return {p: open(os.path.join(WORK, '4u', p), 'rb').read() for p in paths}


def convert_track(mca, log):
    m = mca_parse(mca)
    pcm = mca_decode(m)
    pcm48 = resample(pcm, m['rate'], m['ch'])
    k = RATE / m['rate']
    ns = min(len(pcm48) // (2 * m['ch']), int(round(m['ns'] * k)))
    ls, le = (int(round(m['ls'] * k)), int(round(m['le'] * k))) if m['loop'] else (0xFFFFFFFF, 0xFFFFFFFF)
    # pad so the last real sample survives the decoder's 120-sample pre-skip (packets = ceil((ns + 120) / 960))
    need = ((ns + PRESKIP + FRAME - 1) // FRAME) * FRAME
    pcm48 = pcm48[:ns * 2 * m['ch']] + bytes((need - ns) * 2 * m['ch'])
    pk, la = opus_encode(pcm48, m['ch'])
    assert la == PRESKIP and all(len(p) == PACKET and p[0] == 0xFC for p, _ in pk), (la, set(len(p) for p, _ in pk))
    dec = opus_decode([p for p, _ in pk], m['ch'])[PRESKIP * 2 * m['ch']:][:ns * 2 * m['ch']]
    src = pcm48[:ns * 2 * m['ch']]
    import array
    a, b = array.array('h', src), array.array('h', dec)
    num = sum(x * x for x in a[::11]); den = sum((x - y) ** 2 for x, y in zip(a[::11], b[::11])) or 1
    log.append('  %d Hz %.1f s -> %d samples @48k, loop %s-%s, %d packets, SNR %.1f dB, rms %.1f dBFS' % (
        m['rate'], m['ns'] / m['rate'], ns, ls, le, len(pk), 10 * math.log10(num / den), rms_db(src)))
    return gu_opus_build(pk, ns, ls, le, m['ch']), ns, ls, le, rms_db(src)


def levels(log):
    """median of (GU dB + GU rms) - (4U dB + 4U rms) over the anchor themes."""
    from romfs import RomFS
    rom = RomFS(GU_ROMFS)
    bt = stqr_parse(rom.read(GU_BT))
    gdb = {}
    for q in bt['seqs']:
        si = struct.unpack_from('<I', q, 92)[0]
        if si < len(bt['streams']):
            gdb.setdefault(bt['streams'][si][0].split('\\')[-1], struct.unpack_from('<f', q, 36)[0])
    bat = extract(['sound/bgm/battle/bgm_bat.stq'])['sound/bgm/battle/bgm_bat.stq']
    ns4, nq4 = struct.unpack_from('<II', bat, 8)
    names4 = [bat[w:bat.index(b'\0', w)].decode().split('\\')[-1] for w in
              (struct.unpack_from('<I', bat, 0x18 + 36 * i)[0] for i in range(ns4))]
    db4 = {}
    for i in range(nq4):
        q = bat[0x3C0 + 100 * i:0x3C0 + 100 * (i + 1)]
        si = struct.unpack_from('<I', q, 92)[0]
        if si < ns4: db4.setdefault(names4[si], struct.unpack_from('<f', q, 36)[0])
    mcas = extract(['sound/bgm/battle/wav/%s.mca' % a for a, _ in ANCHORS])
    deltas = []
    for a, g in ANCHORS:
        r4 = rms_db(mca_decode(mca_parse(mcas['sound/bgm/battle/wav/%s.mca' % a])))
        go = gu_opus_parse(rom.read('/nativeNX/sound/bgm/battle/wav/%s.opus' % g))
        rg = rms_db(opus_decode(go['packets']))
        d = (gdb[g] + rg) - (db4[a] + r4)
        deltas.append(d)
        log.append('  anchor %-10s 4U %+.1f dB rms %.1f | GU %-22s %+.1f dB rms %.1f | delta %+.2f' % (
            a, db4[a], r4, g, gdb[g], rg, d))
    deltas.sort()
    med = deltas[len(deltas) // 2] if len(deltas) % 2 else (deltas[len(deltas) // 2 - 1] + deltas[len(deltas) // 2]) / 2
    log.append('  median delta %+.2f dB' % med)
    return med, db4


def build_em089_stqr(new_streams, log):
    """em089's own battle STQR `sound\\bgm\\battle\\bgm_em089` (packed into the em089 arc; module/em089_bgm.c points
    the GU lookups of ids 0x900 / 0x901 at it). TEST 2 FINDING: GU loads `sound\\bgm\\battle\\bgm_bt` from
    nativeNX/loc/arc/quest.arc, never the loose bgm_bt.stqr, so the appended copy was ignored and 0x900 did not
    resolve. Header = GU bgm_bt's, streams = ours only (index 0, 1), sequences = GU Kushala's template with our
    id / dB / stream index. Only the GU loader reads a sequence's stream index (+0x5c, at load 0xb6ced8); playback
    uses the pre-resolved stream pointer at +0x88, so the entries work when returned for the GU battle STQR."""
    return build_battle_stqr(new_streams, log, EM089_STQR, 'em089')


def build_battle_stqr(new_streams, log, out_path, label):
    """a monster's own battle STQR (build_em089_stqr): streams [(path, size, samples, loop start, loop end, sequence
    id, dB)] -> out_path; returns the bytes."""
    from romfs import RomFS
    base = RomFS(GU_ROMFS).read(GU_BT)
    s = stqr_parse(base)
    assert stqr_build(s) == base, 'bgm_bt.stqr does not rebuild byte-identically'
    ids = {struct.unpack_from('<I', q, 0)[0] for q in s['seqs']}
    tpl = [q for q in s['seqs'] if struct.unpack_from('<I', q, 0)[0] == 24][0]      # Kushala (em024) theme
    s['streams'], s['seqs'] = [], []
    for path, size, ns, ls, le, rid, db in new_streams:
        assert rid not in ids
        s['streams'].append([path, size, ns, 2, RATE, ls, le, STREAM_HASH, 0])
        q = bytearray(tpl)
        struct.pack_into('<I', q, 0, rid)
        struct.pack_into('<f', q, 36, db)
        struct.pack_into('<I', q, 92, len(s['streams']) - 1)
        s['seqs'].append(bytes(q))
        log.append('  %s stqr: stream %d %s, sequence id 0x%x, %.2f dB' % (label, len(s['streams']) - 1, path, rid,
                                                                             db))
    out = stqr_build(s)
    chk = stqr_parse(out)
    assert len(chk['streams']) == len(new_streams) == len(chk['seqs'])
    open(out_path, 'wb').write(out)
    log.append('  -> %s' % out_path)
    return out


def build_stqr(new_streams, log):
    """(superseded by build_em089_stqr: GU never reads the loose bgm_bt.stqr) extended bgm_bt.stqr bytes."""
    from romfs import RomFS
    base = RomFS(GU_ROMFS).read(GU_BT)
    s = stqr_parse(base)
    assert stqr_build(s) == base, 'bgm_bt.stqr does not rebuild byte-identically'
    ids = {struct.unpack_from('<I', q, 0)[0] for q in s['seqs']}
    tpl = [q for q in s['seqs'] if struct.unpack_from('<I', q, 0)[0] == 24][0]      # Kushala (em024) theme
    for path, size, ns, ls, le, rid, db in new_streams:
        assert rid not in ids
        s['streams'].append([path, size, ns, 2, RATE, ls, le, STREAM_HASH, 0])
        q = bytearray(tpl)
        struct.pack_into('<I', q, 0, rid)
        struct.pack_into('<f', q, 36, db)
        struct.pack_into('<I', q, 92, len(s['streams']) - 1)
        s['seqs'].append(bytes(q))
        log.append('  stqr: stream %d %s, sequence id 0x%x, %.2f dB' % (len(s['streams']) - 1, path, rid, db))
    out = stqr_build(s)
    chk = stqr_parse(out)
    assert chk['seqs'][:63] == stqr_parse(base)['seqs'] and len(chk['streams']) == 61 + len(new_streams)
    return out


def build_m28d_stqr(m28, jingle, med, log):
    """alias map STQR: GU m26d's, streams in bgm_m28.json -> ours (m28d paths), + stream 4 m28cmpd with a camp-jingle
    sequence (id 0x32, template GU m09d's). jingle = (path, size, ns). Every other byte = GU m26d's."""
    from romfs import RomFS
    rom = RomFS(GU_ROMFS)
    base = rom.read(GU_M26D)
    s = stqr_parse(base)
    assert stqr_build(s) == base, 'bgm_m26d.stqr does not rebuild byte-identically'
    for e in m28:
        st = s['streams'][e['stream']]
        new = st[0].replace('m26d', 'm28d').replace('m26a', 'm28a')
        opus = os.path.join(OUT, 'map/m28d/wav/%s.opus' % new.split('\\')[-1])
        s['streams'][e['stream']] = [new, os.path.getsize(opus), e['samples'], e['channels'], e['rate'],
                                     e['loop_start'], e['loop_end'], STREAM_HASH, 0]
    ids = {struct.unpack_from('<I', q, 0)[0] for q in s['seqs']}
    t = stqr_parse(rom.read(GU_CMP_TEMPLATE[0]))
    tpl = [q for q in t['seqs'] if struct.unpack_from('<I', q, 0)[0] == GU_CMP_TEMPLATE[1]][0]
    assert GU_CMP_TEMPLATE[1] not in ids
    path, size, ns = jingle
    s['streams'].append([path, size, ns, 2, RATE, 0xFFFFFFFF, 0xFFFFFFFF, STREAM_HASH, 0])
    q = bytearray(tpl)
    struct.pack_into('<f', q, 36, STAGE_JINGLE_DB_4U + med)
    struct.pack_into('<I', q, 92, len(s['streams']) - 1)
    s['seqs'].append(bytes(q))
    out = stqr_build(s)
    open(M28D_STQR, 'wb').write(out)
    log.append('  m28d STQR: streams %s + stream %d %s (request 0x32, %.2f dB) -> %s' % (
        [e['stream'] for e in m28], len(s['streams']) - 1, path, STAGE_JINGLE_DB_4U + med, M28D_STQR))


def write(path, data):
    p = os.path.join(GOG_ROMFS, 'nativeNX', path.replace('\\', '/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)
    return p


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    log = []
    if cmd == 'check':
        g = gu_opus_parse(open(sys.argv[2], 'rb').read())
        pcm = opus_decode(g['packets'], g['ch'])
        print({k: v for k, v in g.items() if k != 'packets'}, len(g['packets']), 'packets, rms %.1f dBFS' % rms_db(pcm))
        return
    if cmd in ('all',):
        os.makedirs(WORK, exist_ok=True)
        med, db4 = levels(log)
        srcs = extract([t[0] for t in TRACKS] + [t[0] for t in STAGE])
        new = []
        for src, path, db_4u, rid in TRACKS:
            log.append(path)
            opus, ns, ls, le, r = convert_track(srcs[src], log)
            write(path + '.opus', opus)
            # GU level = 4U level + median anchor delta; our rms equals the 4U master's (same PCM)
            db = db_4u + med if '--keep' not in sys.argv else db_4u
            new.append((path + '', len(opus), ns, ls, le, rid, db))
        m28 = []
        for src, path, slot in STAGE:
            log.append(path)
            opus, ns, ls, le, r = convert_track(srcs[src], log)
            write(path + '.opus', opus)
            if slot is not None:
                m28.append(dict(stream=slot, samples=ns, channels=2, rate=RATE, loop_start=ls, loop_end=le,
                                source=src))
            else:
                jingle = (path, len(opus), ns)
        import json
        json.dump(m28, open(BGM_M28_JSON, 'w'), indent=1)
        log.append('  -> %s (%d streams)' % (BGM_M28_JSON, len(m28)))
        build_m28d_stqr(m28, jingle, med, log)
        open(os.path.join(WORK, 'battle_streams.txt'), 'w').write(repr(new))
        build_em089_stqr(new, log)
    elif cmd == 'stqr':
        new = eval(open(os.path.join(WORK, 'battle_streams.txt')).read())
        build_em089_stqr(new, log)
    for l in log: print(l)


if __name__ == '__main__':
    main()
