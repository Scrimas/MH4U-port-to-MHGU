"""snd_area.py : 4U Battlequarters (m19) area sound -> the Fortress-alias area arcs (m28d a00 / a01 / a02).

  snd_area.py convert     write dump/converted/area_snd/<area>/<arc path>.<type> + dump/converted/area_snd.json
  snd_area.py survey      field statistics of every 4U / GU area sound call (SES) in the RomFS dumps

Per alias area (GU area k <- 4U area, as the arena build maps them: 0 <- m19a00d, 1 <- m19a01d, 2 <- m19a03d):
  - area 0 / 1: the 4U area bank (SNDB -> SBKR), request (SREQ -> SRQR) and waves (MADP -> GU ADPCM, bit-exact) via
    tools/snd4u2gu.py, plus the area sound call (SES), all under the Fortress paths the stage loader asks for
    (sound\\se\\map\\m26d\\m26a0Kd\\snd_m26a0Kd, sound\\call\\map\\m26d\\m26a0Kd, waves ...\\m26a0Kd\\wav\\<4U name>).
    They REPLACE the Fortress area bank / request / call / waves in a0K.arc.
  - area 2 (arena): only the call is replaced. GU's Fortress a02 bank + request ARE Capcom's conversion of 4U
    m19a03d (same request IDs 40..61, 304..336, same parameters up to GU tuning; only the big-cannon IDs 300-303,
    316, 319, 321-323, 333-335 dropped, GU Fortress gimmick IDs added), so they stay (the GU gimmick code uses them).
    The 4U arena call has no SE emitter at all (one reverb zone), so GU's 13 Fortress ambience emitters (creaks,
    draft, underpass wind) go away.
Request volumes are kept as 4U's (--keep-volume): Capcom's a02 conversion does not show the monsters' -2 dB rule.

SES (area sound call; 4U type 0x68cd2933 v 0x20120623, GU 0x2543b93e v 0x20160706), from 596 4U and 1205 GU
records (all base-RomFS area arcs of both games): 'SES\\0', u32 version, u32 n, u32 0, then n x {u32 index, u32
offset} at 0x10, records:
  4U {u32 lo16 index | hi16 request id, u8 shape (1 points, 2 polyline), u8 points, u8 type (1 SE emitter, 3 reverb
      zone, 4 EQ zone), u8 flag, f32 radius, u16 near, u16 far, u32 runtime (0x18b45c), u32 0, char path[64],
      vec4 point[points]}
  GU the same with one word inserted after the radius: u32 (u16 0, u16 x), x = 0 in 517 of 650 type-1 point records
      (5000..13000 otherwise; no 4U counterpart) -> written 0; the runtime word holds GU junk (0x84...) -> 0.
  Type-1 paths name the area bank; type 3/4 name the stage reverb / EQ file (4U snd_M19d 'REV\\0' v2 presets;
  GU snd_m26d 'REVR' / 'EQUR', different layouts) -> NOT converted: type-3/4 records are dropped (deviation).
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import snd4u2gu

U4 = os.path.join(ROOT, 'dump', 'm19_unpacked')
OUT = os.path.join(ROOT, 'dump', 'converted', 'area_snd')
OUT_JSON = os.path.join(ROOT, 'dump', 'converted', 'area_snd.json')
T_SES4, T_SESG = 0x68CD2933, 0x2543B93E
SES_V4, SES_GU = 0x20120623, 0x20160706
AREAS = [(0, 'a00', True), (1, 'a01', True), (2, 'a03', False)]     # (GU area, 4U area, replace bank + request)


def ses_parse(d, gu):
    mag, ver, n = struct.unpack_from('<4sII', d, 0)
    assert mag == b'SES\0' and ver == (SES_GU if gu else SES_V4), (mag, hex(ver))
    tab = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(n)]
    nh = 7 if gu else 6
    recs = []
    for idx, off in tab:
        w = list(struct.unpack_from('<%dI' % nh, d, off))
        shape, npt, typ, flag = struct.pack('<I', w[1])
        path = d[off + 4 * nh:off + 4 * nh + 64].split(b'\0')[0].decode('ascii')
        pts = [struct.unpack_from('<4f', d, off + 4 * nh + 64 + 16 * i) for i in range(npt)]
        recs.append(dict(index=idx, w=w, shape=shape, npt=npt, type=typ, flag=flag, path=path, pts=pts))
    return recs


def ses_build_gu(recs):
    n = len(recs)
    body = b''; offs = []
    base = 0x10 + 8 * n
    for r in recs:
        offs.append(base + len(body))
        w = r['w']
        hdr = struct.pack('<7I', w[0], w[1], w[2], 0, w[3], 0, 0)
        body += hdr + r['path'].encode('ascii').ljust(64, b'\0') + b''.join(struct.pack('<4f', *p) for p in r['pts'])
    out = struct.pack('<4sIII', b'SES\0', SES_GU, n, 0) + b''.join(struct.pack('<II', r['index'], o)
                                                                       for r, o in zip(recs, offs)) + body
    return out


def convert_area(k, a4, full, log, u4=U4, s4='m19', sg='m26'):
    """4U area a4 of stage s4 (arcs unpacked in u4/<s4><a4>/) -> GU area k of the stage folder sg (the GU paths the
    stage loader asks for); full = also the bank, request and waves. Returns [(path, type, bytes)]."""
    src = os.path.join(u4, s4 + a4)
    gdir = 'sound\\se\\map\\%sd\\%sa%02dd\\' % (sg, sg, k)
    gbank = gdir + 'snd_%sa%02dd' % (sg, k)
    gcall = 'sound\\call\\map\\%sd\\%sa%02dd' % (sg, sg, k)
    files = []
    ses = open(os.path.join(src, 'sound/call/map/%s/%s_%sd.%08x' % (s4, s4, a4, T_SES4)), 'rb').read()
    recs = ses_parse(ses, False)
    keep = []
    for r in recs:
        if r['type'] != 1:
            log.append('  %s call record %d: type %d (%s id %d) dropped (stage reverb/EQ zone)' % (
                a4, r['index'], r['type'], r['path'].split('\\')[-1], r['w'][0] >> 16))
            continue
        r['path'] = gbank
        keep.append(r)
    for i, r in enumerate(keep):        # renumber (index / lo16 = record number in both games)
        r['index'] = i; r['w'][0] = (r['w'][0] & 0xFFFF0000) | i
    if full:
        b4p = os.path.join(src, 'sound/se/map/%s/%s%sd/snd_%s%sd' % (s4, s4, a4, s4, a4))
        b4 = snd4u2gu.bank_parse(open(b4p + '.%08x' % snd4u2gu.T4['BANK'], 'rb').read())
        p4 = 'sound\\se\\map\\%s\\%s%sd\\wave\\' % (s4, s4, a4)
        rename = lambda p: gdir + 'wav\\' + p[len(p4):] if p.startswith(p4) else (_ for _ in ()).throw(
            AssertionError(p))
        used = []
        for p, _, _ in b4['ents']:
            if p not in used: used.append(p)
        for p in used:
            d = open(os.path.join(src, p.replace('\\', '/') + '.%08x' % snd4u2gu.T4['WAVE']), 'rb').read()
            files.append((rename(p), snd4u2gu.TG['WAVE'], snd4u2gu.gu_wave(snd4u2gu.madp_parse(d))))
        files.append((gbank, snd4u2gu.TG['BANK'], snd4u2gu.bank_build(b4, rename)))
        r4 = snd4u2gu.req4_parse(open(b4p + '.%08x' % snd4u2gu.T4['REQ'], 'rb').read())
        assert r4['strs'] == ['sound\\se\\map\\%s\\%s%sd\\snd_%s%sd' % (s4, s4, a4, s4, a4)], r4['strs']
        req, _ = snd4u2gu.req_build(r4, {}, [gbank], keep_volume=True)
        files.append((gbank, snd4u2gu.TG['REQ'], req))
        ids = {w[0] & 0xFFFF for w in r4['ents']}
        miss = sorted({r['w'][0] >> 16 for r in keep} - ids)
        assert not miss, ('call names requests the request lacks', miss)
        log.append('  %s -> a%02d: %d waves, bank %d entries, request %d entries, call %d emitters (of %d)' % (
            a4, k, len(used), len(b4['ents']), len(r4['ents']), len(keep), len(recs)))
    else:
        log.append('  %s -> a%02d: call only (%d emitters of %d records; GU bank/request kept)' % (
            a4, k, len(keep), len(recs)))
    files.append((gcall, T_SESG, ses_build_gu(keep)))
    for r in ses_parse(files[-1][2], True):     # self-check
        assert r['type'] == 1 and r['path'] == gbank
    return files


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'convert'
    if cmd != 'convert':
        print(__doc__); return
    log = []; manifest = []
    for k, a4, full in AREAS:
        files = convert_area(k, a4, full, log)
        for p, t, d in files:
            fn = os.path.join(OUT, 'a%02d' % k, p.replace('\\', '/') + '.%08x' % t)
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            open(fn, 'wb').write(d)
        manifest.append(dict(
            arc='monsters/gogmazios/romfs/nativeNX/arc/stage/m28d/a%02d.arc' % k, source_4u='m19%sd' % a4,
            remove_types=(['0x79c47b59 (paths sound\\se\\map\\m26d\\m26a%02dd\\...)' % k, '0x15d782fb', '0x1bcc4966']
                          if full else []) + ['0x2543b93e'],
            add_in_order=[dict(path=p, type='0x%08x' % t, file=os.path.relpath(
                os.path.join(OUT, 'a%02d' % k, p.replace('\\', '/') + '.%08x' % t), ROOT)) for p, t, _ in files]))
    json.dump(manifest, open(OUT_JSON, 'w'), indent=1)
    for l in log: print(l)
    print('->', OUT_JSON)


if __name__ == '__main__':
    main()
