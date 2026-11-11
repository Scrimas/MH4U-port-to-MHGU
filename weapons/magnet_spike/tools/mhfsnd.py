"""mhfsnd.py : Monster Hunter Frontier ZZ sound banks (.snd, 'MOMO') -> lists and WAVs (notes/sounds.md).

  python3 -I mhfsnd.py list FILE.snd [...]          header, programs / tones, samples, waves, the request table
  python3 -I mhfsnd.py dump FILE.snd OUTDIR         one WAV per wave (wNN.wav) and per request (rNNN.wav, the wave the
                                                    request resolves to); OUTDIR outside git (scratch, dump/ or gen/)
  python3 -I mhfsnd.py ms OUTDIR [MODEL ...]        the Magnet Spike's banks: dat/sound/we13.snd (weapon-type bank) +
                                                    the models' wkNNN.snd (dump/mhf/weapon, default the 6 forgeable
                                                    + the test model: 400 404 407 414 415 595 606) -> list + WAVs
  import: parse(bytes) -> bank dict; pcm(bank) -> int16 numpy array of the whole BD; wave(bank, i) -> int16 array;
          resolve(bank, request index) -> dict (program, note, tone, sample, wave, volume, pan, ...)

Game audio: never into git. The client is read-only (MHF_CLIENT, default ~/Videos/Monster Hunter Frontier Online).

Format (C = read in mhfo-hd.dll, D = confirmed in the data of every bank listed by `ms`, G = guess):
- MOMO (D): 'MOMO', u32 3, u32 hd_off (0x40), u32 hd_packed, u32 bd_off (0x200 / ..), u32 bd_size, u32 tbl_off,
  u32 tbl_packed, zeros to 0x40. HD and table are JPK (JKR\\x1a type 3) packed; the BD is raw.
  C: 0x114dd5c0 unpacks the HD (size = JKR +0xc) and copies bd_size bytes from bd_off; 0x114dcc30 / 0x114dcd00 unpack
  the table into the bank slot (0x1e3cbd68[slot]) and the HD (0x1e3c9920[slot], compared with 'Head').
- BD (D): ONE Ogg Vorbis stream (48000 Hz mono in every MS bank) holding all waves back to back; the client imports
  ogg.dll. Waves = Vagi records: {u32 start (bytes of 16-bit PCM = 2 x sample index), u32 samples, u32 a, u32 b,
  u16 c, u16 rate}; consecutive waves are 1441 samples apart (D, padding), a / b / c = 0 in the MS banks (G: loop).
- HD (C: merge 0x114dd750): 'Head' {u32 0x20, u32 2, u32 hd size, u32 original PS2 BD size, u32 prog, u32 smpl,
  u32 vagi chunk offsets}; each chunk {magic, u32 size, u32 max index, u32 0 | -1}.
  Prog: u32 offsets[max + 1] (-1 = no program), programs {u8 tones, u8 0xff, u8 vol, u8 pan, u32 (0, -1)} + tones
  14 B {u8, u8 0xff, u8 lo note, u8 hi note, u16, u16, u8 vol, u8 pan, u16, u16 sample}. Smpl 12 B {u8 x4 (ADSR, G),
  u8 0xff, u8 note, u8 vol, u8 pan, u16, u16 wave}. Vagi 20 B as above. Program numbers are global: the merge keeps
  a component's program k on k (a clash aborts), renumbers samples and waves, adds the BD offsets.
- Request table 'dbsT' (C: 0x114dc9c0 / 0x114dcf90 / 0x114dd030): {'dbsT', u32 0x10, u32 bytes, u32 count} + count x
  32 B: u32 kind, u8 0x29, u8, u8 program, u8 note, u8 a, u8 b, u8 c, u8 0xff, u8 vol (+0x0a, rewritten by
  0x114dced0), u8 pan (+0x0b), u16, u32, u16 d, u16 0xffff, u16 random pitch range (+0x18, C), u16 random volume
  range (+0x1a, C), u16, u16 (+0x1e == 1: 0x114dd030 skips the front / back flag, C).
"""
import os, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MHF_CLIENT = os.environ.get('MHF_CLIENT', os.path.expanduser('~/Videos/Monster Hunter Frontier Online'))
MHF_WEAPON = os.path.join(ROOT, 'dump', 'mhf', 'weapon')
MS_MODELS = (400, 404, 407, 414, 415, 595, 606)        # msbuild MODELS (the forgeable six + the test weapon)
WAVE_GAP = 1441


# ------------------------------------------------------------------ JPK (JKR type 3 / 4)

def jpk(b):
    assert b[:4] == b'JKR\x1a', b[:4]
    typ = struct.unpack_from('<H', b, 6)[0]
    start, osz = struct.unpack_from('<II', b, 8)
    assert typ in (3, 4), typ
    out = bytearray(osz); o = 0; st = [0, 0]
    if typ == 3:
        pp = [start]

        def rb():
            v = b[pp[0]]; pp[0] += 1; return v
    else:
        tl = struct.unpack_from('<h', b, start)[0]; to = start + 2; h = [to + tl * 4 - 0x3fc, 0, 0]

        def rb():
            d = tl
            while d >= 0x100:
                h[1] -= 1
                if h[1] < 0: h[1] = 7; h[2] = b[h[0]]; h[0] += 1
                d = struct.unpack_from('<h', b, (d * 2 - 0x200 + ((h[2] >> h[1]) & 1)) * 2 + to)[0]
            return d & 0xff

    def bit():
        st[0] -= 1
        if st[0] < 0: st[0] = 7; st[1] = rb()
        return (st[1] >> st[0]) & 1

    def cpy(off, ln):
        nonlocal o
        for _ in range(ln + 3):
            if o >= osz: return
            out[o] = out[o - off - 1]; o += 1
    while o < osz:
        if not bit(): out[o] = rb(); o += 1; continue
        if not bit():
            ln = (bit() << 1) | bit(); cpy(rb(), ln); continue
        hi = rb(); lo = rb()
        ln = (hi & 0xe0) >> 5; off = ((hi & 0x1f) << 8) | lo
        if ln: cpy(off, ln - 1); continue
        if not bit():
            ln = (bit() << 3) | (bit() << 2) | (bit() << 1) | bit(); cpy(off, ln + 7); continue
        t = rb()
        if t == 0xff:
            for _ in range(off + 0x1b): out[o] = rb(); o += 1
            continue
        cpy(off, t + 0x17)
    return bytes(out)


# ------------------------------------------------------------------ bank

def _chunk(hd, off, magic):
    m, size, mx, x = struct.unpack_from('<4sIIi', hd, off)
    assert m == magic, (m, magic)
    return size, mx, x


def parse(b):
    """MOMO bytes -> dict(header, programs {k: dict(vol, pan, tones)}, smpl [..], vagi [..], table [..], bd)"""
    magic, ver, hd_off, hd_n, bd_off, bd_n, tb_off, tb_n = struct.unpack_from('<4s7I', b, 0)
    assert magic == b'MOMO' and ver == 3, (magic, ver)
    hd = jpk(b[hd_off:hd_off + hd_n])
    tb = jpk(b[tb_off:tb_off + tb_n]) if tb_n else b''
    m, hsz, two, hdsize, bd_ps2, po, so, vo = struct.unpack_from('<4s7I', hd, 0)
    assert m == b'Head', m
    _, mx, _ = _chunk(hd, po, b'Prog')
    progs = {}
    for k, o in enumerate(struct.unpack_from('<%di' % (mx + 1), hd, po + 16)):
        if o == -1: continue
        p = po + o
        n, _, vol, pan = struct.unpack_from('<4B', hd, p)
        tones = []
        for t in range(n):
            r = struct.unpack_from('<BBBBHHBBHH', hd, p + 8 + 14 * t)
            tones.append(dict(lo=r[2], hi=r[3], u4=r[4], u6=r[5], vol=r[6], pan=r[7], u10=r[8], smpl=r[9], b0=r[0]))
        progs[k] = dict(vol=vol, pan=pan, tones=tones)
    _, mx, _ = _chunk(hd, so, b'Smpl')
    smpl = []
    for i in range(mx + 1):
        r = struct.unpack_from('<4sBBBBHH', hd, so + 16 + 12 * i)
        smpl.append(dict(adsr=r[0].hex(), note=r[2], vol=r[3], pan=r[4], u8=r[5], vagi=r[6]))
    _, mx, _ = _chunk(hd, vo, b'Vagi')
    vagi = []
    for i in range(mx + 1):
        off, n, a, c, d, rate = struct.unpack_from('<IIIIHH', hd, vo + 16 + 20 * i)
        vagi.append(dict(start=off // 2, samples=n, a=a, b=c, c=d, rate=rate, odd=off & 1))
    table = []
    if tb:
        m, h, nb, cnt = struct.unpack_from('<4sIII', tb, 0)
        assert m == b'dbsT', m
        for i in range(cnt):
            r = struct.unpack_from('<IBBBBBBBBBBHIHHHHHH', tb, 16 + 32 * i)
            table.append(dict(kind=r[0], b4=r[1], b5=r[2], prog=r[3], note=r[4], a=r[5], b=r[6], c=r[7], vol=r[9],
                              pan=r[10], u12=r[11], u14=r[12], d=r[13], u1a=r[14], rpitch=r[15], rvol=r[16],
                              u1e=r[17], u20=r[18]))
    return dict(header=(hd_off, hd_n, bd_off, bd_n, tb_off, tb_n), bd_ps2=bd_ps2, programs=progs, smpl=smpl,
                vagi=vagi, table=table, bd=b[bd_off:bd_off + bd_n])


def vorbis_info(bd):
    """(channels, rate) from the Vorbis identification header of the BD's first Ogg page"""
    assert bd[:4] == b'OggS', bd[:4]
    ns = bd[26]
    p = 27 + ns
    assert bd[p:p + 7] == b'\x01vorbis', bd[p:p + 7]
    return bd[p + 11], struct.unpack_from('<I', bd, p + 12)[0]


def pcm(bank):
    """the whole BD as int16 samples (ffmpeg decodes the Ogg Vorbis stream; no resampling)"""
    import numpy as np
    ch, rate = vorbis_info(bank['bd'])
    r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'ogg', '-i', 'pipe:0', '-f', 's16le', '-acodec', 'pcm_s16le',
                        '-ac', str(ch), '-ar', str(rate), 'pipe:1'], input=bank['bd'], capture_output=True)
    if r.returncode:
        raise RuntimeError('ffmpeg failed: ' + r.stderr.decode(errors='replace'))
    a = np.frombuffer(r.stdout, dtype='<i2')
    return a.reshape(-1, ch) if ch > 1 else a


def wave(bank, i, whole=None):
    v = bank['vagi'][i]
    whole = pcm(bank) if whole is None else whole
    return whole[v['start']:v['start'] + v['samples']]


def tone_of(bank, prog, note):
    p = bank['programs'].get(prog)
    if not p: return None
    for k, t in enumerate(p['tones']):
        if t['lo'] <= note <= t['hi']: return k, t
    return None


def resolve(bank, i, extra=()):
    """request i -> dict(prog, note, tone, smpl, vagi (wave index in its own bank), bank (0 = this one, 1.. = extra
    banks: the components the game merges with it), semitones = note - sample note)"""
    e = bank['table'][i]
    out = dict(e, tone=None, smpl=None, vagi=None, owner=None)
    for k, b in enumerate((bank,) + tuple(extra)):
        t = tone_of(b, e['prog'], e['note'])
        if t:
            s = b['smpl'][t[1]['smpl']]
            out.update(tone=t[0], smpl=t[1]['smpl'], vagi=s['vagi'], owner=k, semitones=e['note'] - s['note'],
                       tvol=t[1]['vol'], svol=s['vol'])
            break
    return out


def write_wav(path, a, rate):
    import numpy as np
    a = np.ascontiguousarray(a, dtype='<i2')
    ch = a.shape[1] if a.ndim == 2 else 1
    raw = a.tobytes()
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + len(raw)) + b'WAVEfmt ' +
                struct.pack('<IHHIIHH', 16, 1, ch, rate, rate * 2 * ch, 2 * ch, 16) + b'data' +
                struct.pack('<I', len(raw)) + raw)


# ------------------------------------------------------------------ commands

def listing(name, bank, whole=None):
    import numpy as np
    ch, rate = vorbis_info(bank['bd'])
    L = ['%s: HD %d B packed, BD %d B (Ogg Vorbis %d ch %d Hz), table %d requests; PS2 BD was %d B' % (
        name, bank['header'][1], bank['header'][3], ch, rate, len(bank['table']), bank['bd_ps2'])]
    for k, p in sorted(bank['programs'].items()):
        L.append('  program %d: vol %d pan %d, %d tones: %s' % (k, p['vol'], p['pan'], len(p['tones']), ' '.join(
            '%d-%d>s%d(v%d)' % (t['lo'], t['hi'], t['smpl'], t['vol']) for t in p['tones'])))
    if whole is not None:
        L.append('  BD decoded: %d samples (%.2f s)' % (len(whole), len(whole) / rate))
    for i, v in enumerate(bank['vagi']):
        s = '  wave %2d: start %7d, %6d samples (%.3f s) %d Hz a %d b %d c %d' % (
            i, v['start'], v['samples'], v['samples'] / max(v['rate'], 1), v['rate'], v['a'], v['b'], v['c'])
        if whole is not None:
            w = whole[v['start']:v['start'] + v['samples']].astype(np.float64)
            gap = whole[max(0, v['start'] - WAVE_GAP):v['start']].astype(np.float64)
            s += ', peak %5.1f dBFS, rms %5.1f dBFS, gap before peak %5.1f dBFS' % (
                _db(np.abs(w).max() if len(w) else 0), _db(np.sqrt((w ** 2).mean()) if len(w) else 0),
                _db(np.abs(gap).max() if len(gap) else 0))
        L.append(s)
    for i, e in enumerate(bank['table']):
        r = resolve(bank, i)
        L.append('  request %3d: kind %d prog %d note %d vol %3d pan %3d a %d b %d c %d d %d rpitch %d rvol %d '
                 'u1e %d -> %s' % (i, e['kind'], e['prog'], e['note'], e['vol'], e['pan'], e['a'], e['b'], e['c'],
                                    e['d'], e['rpitch'], e['rvol'], e['u1e'],
                                    'tone %d smpl %d wave %d (%+d st)' % (r['tone'], r['smpl'], r['vagi'],
                                                                          r['semitones'])
                                    if r['tone'] is not None else 'not in this bank'))
    return L


def _db(x):
    import math
    return 20 * math.log10(x / 32768.0) if x > 0 else -999.0


def dump(name, bank, out):
    os.makedirs(out, exist_ok=True)
    whole = pcm(bank)
    _, rate = vorbis_info(bank['bd'])
    for i in range(len(bank['vagi'])):
        write_wav(os.path.join(out, '%s_w%02d.wav' % (name, i)), wave(bank, i, whole), bank['vagi'][i]['rate'] or rate)
    n = 0
    for i in range(len(bank['table'])):
        r = resolve(bank, i)
        if r['vagi'] is None: continue
        write_wav(os.path.join(out, '%s_r%03d.wav' % (name, i)), wave(bank, r['vagi'], whole), rate)
        n += 1
    return whole, n


def ms_banks(models=MS_MODELS):
    out = [('we13', os.path.join(MHF_CLIENT, 'dat', 'sound', 'we13.snd'))]
    for m in models:
        p = os.path.join(MHF_WEAPON, 'wk%03d' % m, 'wk%03d.snd' % m)
        if os.path.exists(p): out.append(('wk%03d' % m, p))
        else: print('wk%03d: no .snd' % m)
    return out


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    if a[0] == 'list':
        for p in a[1:]:
            b = parse(open(p, 'rb').read())
            print('\n'.join(listing(os.path.basename(p), b, pcm(b))))
    elif a[0] == 'dump':
        b = parse(open(a[1], 'rb').read())
        name = os.path.splitext(os.path.basename(a[1]))[0]
        whole, n = dump(name, b, a[2])
        print('%s: %d waves, %d request WAVs -> %s' % (name, len(b['vagi']), n, a[2]))
    elif a[0] == 'ms':
        out = a[1]
        models = [int(x) for x in a[2:]] or MS_MODELS
        os.makedirs(out, exist_ok=True)
        L = []
        for name, p in ms_banks(models):
            b = parse(open(p, 'rb').read())
            whole, n = dump(name, b, os.path.join(out, name))
            L += listing(name, b, whole)
        open(os.path.join(out, 'list.txt'), 'w').write('\n'.join(L) + '\n')
        print('\n'.join(L))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
