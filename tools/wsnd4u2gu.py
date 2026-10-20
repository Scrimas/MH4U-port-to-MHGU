"""wsnd4u2gu.py : MH4U (3DS) weapon sound effects -> MHGU (Switch) weapon sound arcs (arc/weapon/wNN/snd/MMM.arc),
for the Gogmazios weapons. Formats from tools/snd4u2gu.py (imported, not modified); the weapon rules below.

  wsnd4u2gu.py convert NN IN.arc OUT.arc [--model M]  4U weapon arc (data/pl_<pfx>NNN.arc) -> GU snd arc MMM
  wsnd4u2gu.py gogma DIR4U [OUTDIR]                    the 14 Gogma weapons (DIR4U/pl_<pfx>NNN.arc) ->
                                                       OUTDIR/wNN/snd/NNN.arc (default module/romfs/nativeNX/arc/weapon)
  wsnd4u2gu.py check NN OUT.arc [IN.arc]               parse back: waves (bit-identical to IN.arc), bank keys, request
                                                       IDs vs every GU snd arc of the class, request -> bank keys
  wsnd4u2gu.py selftest DIR4U                          rebuild Capcom's 4U -> GU weapon pairs, report byte agreement
  import: wsnd4u2gu.convert(nn, src_bytes, n4, model=None, rom=None) -> (GU arc bytes, log lines)

Facts: C = confirmed in data, S = strong, G = guess. "Pairs" = Capcom's own weapon conversions: every 4U arc
pl_<pfx>NNN.arc with sounds whose number GU also has as wNN/snd/NNN.arc, where GU's model NNN is the 4U model
(MOD bones / bounding box / material names equal) and every GU weapon of model NNN has mSrqrNo NNN: 579 pairs
(GS 56, SnS 26, Ham 59, Lance 47, HBG 30, LBG 39, LS 46, SA 43, GL 48, Bow 43, DB 53, HH 38, IG 26, CB 25).
Numbers below are from `selftest` (578 pairs converted; swo117 refused: a 4U wave with 0 samples).

- weapon record (C): mSrqrNo selects arc/weapon/wNN/snd/%03d.arc; mSrqrNo = mModelID on 1502 of 1606 GU weapons.
  The arc holds only the weapon's own sounds. mat_b.arc / mat_i.arc in snd/ are the class's hit sounds for
  mSndMaterial (two_hit_bone / two_hit_iron, ...); no 4U weapon-record byte predicts mSndMaterial on the pairs.
- arc content (C, entry list path / type / order equal on 554 / 578): the 4U weapon's sound entries in 4U order
  (waves, then per bank: bank + request; bowguns: bank B (body) and bank SF (shots)), renamed, + the class's
  GU-only wave PFMMM_90 right after the last wave; 4U waves no converted bank entry plays are dropped (GS 014 /
  027 / 063 _7). Paths: 4U sound\\se\\pl\\wp\\[bgn\\]PF\\NNN\\wave\\PFNNN_x -> GU sound\\se\\pl\\wp\\PF\\MMM\\wav\\
  PFMMM_x; bank and request share sound\\se\\pl\\wp\\PF\\MMM\\snd_wp_PF[B|SF]MMM (bowguns lose the 4U bgn\\ level).
  The 24 other pairs: 11 GU hammers + 2 bowguns + 2 IGs without the _90 wave (key 90 entry with an empty path),
  4 lances / 2 HBGs with GU-renamed extra keys 7 / 8 (4U 'rall' waves), 2 hammers keeping an unplayed _07, and
  CB 002 whose GU paths say 003.
- GU weapon banks and requests are CLASS TEMPLATES (C): over all GU snd arcs of a class (79..137 each), every
  bank record / trailer, every bank entry byte (except byte 5 = volume on DB's 11 keys and 1-3 keys of GS / Ham /
  Lance / HH / CB, and Lance byte 38 on one key) and every request word except w9/w10 (dB) and SnS / CB w11,
  Ham / DB w12, Lance w2 / w21, SA w21, HBG w8, GL w17, HH w4 / w5, IG w2 is the same for a given (bank kind,
  key / request ID). Where GU varies per weapon, the variation does not come from 4U: in the vote
  over the pairs (selftest), the class's GU majority beats the 4U value (snd4u2gu rules) on every word of every
  class except Lance w2 (WORDS_4U), and on bank byte 5 (DB: majority 390 / 530, 4U 55). So the converter takes
  bank and request from the class majority (class_template) and from 4U only: the waves, the wave behind each
  bank key, and which request IDs exist.
- volumes (C / S): request w9/w10 = the class's GU value. 4U volumes are class norms too; when a 4U weapon is off
  its 4U class norm, its GU conversion is back at the GU class norm (355 of 570 entries) and almost never at
  4U - 2 dB (10 / 570). GU class value = 4U class norm - 2 dB in most classes (snd4u2gu's monster re-level), with
  the bank trailer gain raised: 4U -> GU dB GS -2 -> -1, SnS -1.5 -> -0.5, Ham / LS / DB / HH -2 -> -0.5, Lance /
  GL / Bow -2 -> -1, SA -4 -> -2, IG -2 -> -0.2, CB -3 -> -1.5, bowgun B 0 -> 0, SF -1.5 -> -0.5 (C, class
  constants).
  Capcom's re-encoded waves are within about +-2 dB RMS (median per class) of the 4U waves (S), so 4U waves at
  GU class levels land near Capcom's own level for a converted weapon.
- waves (C): GU's weapon waves are mostly Capcom re-encodes from its masters (other sample counts / rates); the
  857 waves Capcom kept (same DSP data and sample count) are byte-identical to snd4u2gu.gu_wave(madp_parse(4U))
  apart from the 8-byte stamp at 0x10, a build time (u16 2017, u8 month 8, day 2, hour 12, min, sec, 0; varies
  per class; snd4u2gu's constant is kept, G: never read). 4U DSP-ADPCM is copied losslessly at its 4U rate (S: GU
  ships 8000..22050 Hz weapon waves). The _90 wave (tiny, one per class) is the class majority's.
- bank (C, byte-identical on 590 / 647 banks, entries 5146 / 5310, same wave path 5286 / 5310): SBKR v4, the
  class's records ({id, 0x0800 | 2 * count, first, 0}: the 4U category bits 11-14 are dropped, not moved to x
  as for monsters; bowgun SF has 2 groups of 4), entries in the class's key order (4U keys + key 90 last), each
  the class entry for that key with the path of the 4U entry's wave (the class's wave for that key when the 4U
  arc has it); trailer {f32 gain, u32 index} = the class's (byte 1 of the index = 0xcd in GU).
- request (C, entries identical 4655 / 6896: the rest differ in w9/w10 only, but Lance w2 3 / w21 12, IG w2 8,
  Ham w12 5, SA w21 1): SRQR v5, header / string table as snd4u2gu (own bank only: 4U weapons have no common
  bank; 640 / 647 identical), the class's IDs in its order. 4U IDs GU lacks are dropped (HBG / LBG bank B ID 3,
  69 / 69 pairs); GU-only IDs (HH 115, 165-167, 215-219: echo chains on the note keys 15-18, in 106 / 110 GU
  horns) are the class entry: identical in all 38 paired horns except w9/w10 (249 / 342 entries identical).
  Ham IDs 8/9 (key 7) and Lance IDs 7-9 (keys 7/8, w21 = -1) point at keys the bank lacks, as in 127 / 130 GU
  hammers and 122 / 127 GU lances.
"""
import collections, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
import arcpack
import snd4u2gu as S4

T4, TG = S4.T4, S4.TG
PFX = {0: 'two', 1: 'one', 2: 'ham', 3: 'lan', 4: 'hbg', 6: 'lbg', 7: 'swo', 8: 'axe', 9: 'gun', 10: 'bow',
       11: 'sou', 12: 'hue', 13: 'rod', 14: 'gaxe'}
GOGMA = {0: 97, 1: 97, 2: 99, 3: 82, 4: 40, 6: 47, 7: 79, 8: 77, 9: 82, 10: 75, 11: 87, 12: 71, 13: 25, 14: 27}
OUT_DEFAULT = os.path.join(ROOT, 'module/romfs/nativeNX/arc/weapon')
RE4 = re.compile(r'^sound\\se\\pl\\wp\\(?:bgn\\)?([a-z]+)\\(\d{3})\\(?:(wave)\\)?(.+)$')
REG = re.compile(r'^sound\\se\\pl\\wp\\([a-z]+)\\(\d{3})\\(?:(wav)\\)?(.+)$')

# request words taken from the 4U entry (snd4u2gu.req_ent_gu: w9/w10 = 4U dB - 2) instead of the class's GU value,
# per class: only where 4U beats the class template in the vote over the pairs (selftest prints it)
WORDS_4U = {3: (2,)}
BANK_BYTES_4U = ()          # bank entry bytes taken from 4U: none (the class template wins on every byte)


def gu_rom():
    from romfs import RomFS
    return RomFS(S4.GU_ROMFS)


def snd_arcs(rom, nn):
    return sorted(f for f in rom.files if re.match(r'/nativeNX/arc/weapon/w%02d/snd/\d{3}\.arc$' % nn, f))


def kind_of(name):
    """bank / request file name -> kind ('snd_wp_two', 'snd_wp_hbgB', 'snd_wp_hbgSF')."""
    m = re.match(r'^(snd_wp_[a-zA-Z]+)\d{3}$', name)
    assert m, name
    return m.group(1)


def suffix_of(name):
    """wave file name PFNNN_x -> x ('' for the empty path some GU arcs carry on key 90, type 0)."""
    if not name: return ''
    m = re.match(r'^[a-z]+\d{3}_(.+)$', name)
    assert m, name
    return m.group(1)


# ------------------------------------------------------------------ class template (majority over GU arcs)

_TPL = {}


def _maj(c):
    return c.most_common(1)[0][0]


def class_template(nn, rom=None):
    """majority over every GU snd arc of class nn:
    banks[kind] = dict(order=[keys], ent={key: 76 B}, sfx={key: wave suffix}, vary={key: {byte j}}, recs, x, tail)
    reqs[kind] = dict(order=[w0], ent={w0: 33 words}, vary={w0: {word j}}, hdr)
    waves_gu = {suffix: wave bytes} for wave suffixes GU adds (no 4U counterpart: '90'), narcs."""
    if nn in _TPL: return _TPL[nn]
    rom = rom or gu_rom()
    B = collections.defaultdict(lambda: dict(order=collections.Counter(), ent=collections.defaultdict(collections.Counter),
                                             sfx=collections.defaultdict(collections.Counter),
                                             byte=collections.defaultdict(lambda: collections.defaultdict(set)),
                                             recs=collections.Counter(), x=collections.Counter(), tail=collections.Counter()))
    R = collections.defaultdict(lambda: dict(order=collections.Counter(), ent=collections.defaultdict(collections.Counter),
                                             word=collections.defaultdict(lambda: collections.defaultdict(set)),
                                             hdr=collections.Counter()))
    W90 = collections.defaultdict(collections.Counter)
    arcs = snd_arcs(rom, nn)
    for f in arcs:
        for p, t, d in arcpack.read(rom.read(f))[1]:
            m = REG.match(p)
            assert m, p
            name = m.group(4)
            if t == TG['WAVE']:
                if suffix_of(name) == '90': W90['90'][d] += 1
            elif t == TG['BANK']:
                b = S4.bank_parse(d); T = B[kind_of(name)]
                T['order'][tuple(a[72] for _, _, a in b['ents'])] += 1
                T['recs'][tuple(b['recs'])] += 1; T['x'][b['x']] += 1; T['tail'][b['tail_raw']] += 1
                for q, _, a in b['ents']:
                    k = a[72]
                    T['ent'][k][a] += 1; T['sfx'][k][suffix_of(q.split('\\')[-1])] += 1
                    for j in range(76): T['byte'][k][j].add(a[j])
            elif t == TG['REQ']:
                g = S4.reqgu_parse(d); T = R[kind_of(name)]
                T['order'][tuple(w[0] for w in g['ents'])] += 1; T['hdr'][d[0x0C:0x20]] += 1
                for w in g['ents']:
                    T['ent'][w[0]][w] += 1
                    for j in range(33): T['word'][w[0]][j].add(w[j])
    banks = {k: dict(order=list(_maj(T['order'])), ent={key: _maj(c) for key, c in T['ent'].items()},
                     sfx={key: _maj(c) for key, c in T['sfx'].items()},
                     vary={key: {j for j, s in v.items() if len(s) > 1} for key, v in T['byte'].items()},
                     recs=list(_maj(T['recs'])), x=_maj(T['x']), tail=_maj(T['tail'])) for k, T in B.items()}
    reqs = {k: dict(order=list(_maj(T['order'])), ent={w0: list(_maj(c)) for w0, c in T['ent'].items()},
                    vary={w0: {j for j, s in v.items() if len(s) > 1} for w0, v in T['word'].items()},
                    hdr=_maj(T['hdr'])) for k, T in R.items()}
    _TPL[nn] = dict(banks=banks, reqs=reqs, waves_gu={s: _maj(c) for s, c in W90.items()}, narcs=len(arcs))
    return _TPL[nn]


# ------------------------------------------------------------------ builders

def bank_build_w(b4, tb, wave_path, log, have=()):
    """4U SNDB (parsed) -> GU SBKR from the class template tb; wave_path(suffix) -> GU wave path; have = the 4U
    arc's wave suffixes (a key plays the class's wave for it when the 4U arc has that wave, else the 4U one)."""
    k4 = {}
    for p, t, a in b4['ents']:
        assert t == T4['WAVE'], hex(t)
        k4.setdefault(a[12], (p, a))
    ents = []
    for key in tb['order']:
        e = bytearray(tb['ent'][key])
        if key in k4:
            p, a = k4[key]
            c = S4.bank_ent_gu(a)
            for j in BANK_BYTES_4U:
                e[j] = c[j]
            sfx = suffix_of(p.split('\\')[-1])
            if tb['sfx'].get(key) != sfx and tb['sfx'].get(key) in have:
                log.append('  bank key %d: 4U wave _%s -> the class wave _%s' % (key, sfx, tb['sfx'][key]))
                sfx = tb['sfx'][key]
        elif tb['sfx'][key] == '90':
            sfx = '90'
        else:
            log.append('  bank key %d: in every GU arc of the class, not in the 4U bank: dropped' % key)
            continue
        ents.append(wave_path(sfx).encode('ascii') + b'\0' + struct.pack('<I', TG['WAVE']) + bytes(e))
    for key in sorted(set(k4) - set(tb['order'])):
        log.append('  bank key %d: 4U only (no GU entry for it in the class): dropped' % key)
    recs = tb['recs']             # group records {id, 0x0800 | 2 * count, first entry, x}: the class's
    if sum((r[1] & 0x7FF) // 2 for r in recs) != len(ents):
        raise SystemExit('bank: %d entries, the class records %s describe another count' % (len(ents), recs))
    return b''.join([struct.pack('<4s4I', b'SBKR', 4, len(recs), len(ents), tb['x'])] +
                    [struct.pack('<HHII', *r) for r in recs] + ents + [tb['tail']])


def req_build_w(r4, tr, bank_path, log, words_4u=()):
    """4U SREQ (parsed) -> GU SRQR from the class template tr; string table = [bank_path]; words_4u: words
    taken from the 4U entry (WORDS_4U)."""
    by4 = {w[0]: w for w in r4['ents']}
    ents = []; gu_only = []
    for w0 in tr['order']:
        g = list(tr['ent'][w0])
        w = by4.get(w0)
        if w is not None:
            c = struct.unpack('<33I', S4.req_ent_gu(w))
            for j in words_4u: g[j] = c[j]
        else:
            gu_only.append(w0 & 0xFFFF)
        ents.append(struct.pack('<33I', *g))
    drop = sorted(w0 & 0xFFFF for w0 in set(by4) - set(tr['order']))
    if gu_only: log.append('  request IDs only GU has (class entries as is): %s' % gu_only)
    if drop: log.append('  request IDs GU dropped from the class: %s' % drop)
    n = len(ents)
    stab = 0x34 + 132 * n
    blob = bank_path.encode('ascii') + b'\0'
    end = (stab + 4 + len(blob) + 15) // 16 * 16
    hdr = struct.pack('<4s2I', b'SRQR', 5, n) + tr['hdr'] + struct.pack('<5I', stab, end, end, end, end)
    body = hdr + b''.join(ents) + struct.pack('<I', stab + 4) + blob
    return body + bytes(end - len(body))


def convert(nn, src, n4, model=None, rom=None):
    """4U weapon arc bytes (pl_<pfx><n4>.arc) -> (GU snd arc bytes for model `model`, log lines)."""
    pf = PFX[nn]
    model = n4 if model is None else model
    tpl = class_template(nn, rom)
    log = []
    gdir = 'sound\\se\\pl\\wp\\%s\\%03d\\' % (pf, model)
    wave_path = lambda sfx: gdir + 'wav\\%s%03d_%s' % (pf, model, sfx)
    out = []
    s4 = [(p, t, d) for p, t, d in arcpack.read(src)[1] if p.startswith('sound\\')]
    have = {suffix_of(RE4.match(p).group(4)) for p, t, d in s4 if t == T4['WAVE']}
    for p, t, d in s4:
        m = RE4.match(p)
        assert m and m.group(1) == pf, p      # 4U sound number may differ from the model (78 of 579 pairs)
        name = m.group(4)
        if t == T4['WAVE']:
            assert m.group(3), p
            mp = S4.madp_parse(d)
            if not mp['samples']: raise SystemExit('%s: empty 4U wave' % p)
            out.append((wave_path(suffix_of(name)), TG['WAVE'], S4.gu_wave(mp)))
        elif t in (T4['BANK'], T4['REQ']):
            kind = kind_of(name)
            gpath = gdir + kind + '%03d' % model
            if t == T4['BANK']:
                out.append((gpath, TG['BANK'], bank_build_w(S4.bank_parse(d), tpl['banks'][kind], wave_path, log,
                                                            have)))
            else:
                r4 = S4.req4_parse(d)
                assert len(r4['strs']) == 1 and r4['strs'][0].endswith('\\' + name), r4['strs']
                out.append((gpath, TG['REQ'], req_build_w(r4, tpl['reqs'][kind], gpath, log, WORDS_4U.get(nn, ()))))
        else:
            raise SystemExit('unhandled 4U sound entry %s %08x' % (p, t))
    last = max(i for i, (p, t, d) in enumerate(out) if t == TG['WAVE'])
    for sfx, d in sorted(tpl['waves_gu'].items()):
        out.insert(last + 1, (wave_path(sfx), TG['WAVE'], d)); last += 1
        log.append('  wave %s: GU-only class wave (copied from the class majority)' % wave_path(sfx).split('\\')[-1])
    used = {q for p, t, d in out if t == TG['BANK'] for q, _, _ in S4.bank_parse(d)['ents']}
    for p, t, d in out:
        if t == TG['WAVE'] and p not in used: log.append('  wave %s: no bank entry plays it: dropped' % p.split('\\')[-1])
    out = [e for e in out if e[1] != TG['WAVE'] or e[0] in used]
    return arcpack.build(out), log


# ------------------------------------------------------------------ check

def check(nn, path, src=None, rom=None):
    rom = rom or gu_rom()
    tpl = class_template(nn, rom)
    ents = arcpack.read(open(path, 'rb').read())[1]
    ok = True
    waves = {p: d for p, t, d in ents if t == TG['WAVE']}
    for p, t, d in ents:
        assert REG.match(p), p
        if t == TG['WAVE']:
            v, flags, n = struct.unpack_from('<I4sI', d, 0)
            samples, rate = struct.unpack_from('<II', d, 0x60)
            ok &= v == 2 and len(d) >= 0x78 + n and (len(d) - 0x78) % 0x100 == 0 and n == S4.dsp_data_bytes(samples)
    # GU class request-ID sets (every arc), for coverage
    gsets = collections.Counter()
    for f in snd_arcs(rom, nn):
        for p, t, d in arcpack.read(rom.read(f))[1]:
            if t == TG['REQ']:
                gsets[(kind_of(p.split('\\')[-1]), tuple(sorted(w[0] & 0xFFFF for w in S4.reqgu_parse(d)['ents'])))] += 1
    for p, t, d in ents:
        kind = kind_of(p.split('\\')[-1]) if t in (TG['BANK'], TG['REQ']) else None
        if t == TG['BANK']:
            b = S4.bank_parse(d)
            miss = [q for q, tt, _ in b['ents'] if q not in waves or tt != TG['WAVE']]
            nrec = sum((r[1] & 0x7FF) // 2 for r in b['recs'])
            keys = [a[72] for _, _, a in b['ents']]
            print('  bank %-14s %2d entries (record says %d), keys %s, missing waves %s, tail %.3f' % (
                kind, len(b['ents']), nrec, keys, miss, b['tail'][0][0]))
            ok &= not miss and nrec == len(b['ents'])
            bkeys = set(keys)
        elif t == TG['REQ']:
            g = S4.reqgu_parse(d)
            stab, end = struct.unpack_from('<II', d, 0x20)
            ids = sorted(w[0] & 0xFFFF for w in g['ents'])
            ours = set(ids)
            sets = [(s, c) for (k, s), c in gsets.items() if k == kind]
            full = sum(c for s, c in sets if set(s) <= ours)
            union = set().union(*[set(s) for s, c in sets])
            nokey = [w[0] for w in g['ents'] if (w[0] >> 16) & 0xFF not in bkeys | {0xFF}]
            # Capcom ships such IDs too (Ham 8/9 -> key 7 in 127 / 130 GU hammers, Lance 7-9 -> keys 7/8 with no
            # bank, w21 = -1, in 122 / 127): fine when the class template has the ID and lacks the key as well
            tb, tr = tpl['banks'][kind], tpl['reqs'][kind]
            asgu = [w0 & 0xFFFF for w0 in nokey if w0 in tr['ent'] and (w0 >> 16) & 0xFF not in tb['order']]
            badkey = [w0 & 0xFFFF for w0 in nokey if w0 & 0xFFFF not in asgu]
            strs = d[stab + 4:d.index(b'\0', stab + 4)].decode()
            print('  request %-11s %2d IDs %s\n      covers the full ID set of %d / %d GU arcs of the class; GU IDs not '
                  'here: %s (union over the class); IDs with a key not in the bank: %s (as in the GU class: %s); '
                  'string %s' % (kind, len(ids), ids, full, sum(c for s, c in sets), sorted(union - ours), badkey, asgu,
                                 strs))
            ok &= stab == 0x34 + 132 * len(g['ents']) and end == len(d) and not badkey and strs == p
    if src:
        s4 = {RE4.match(p).group(4): d for p, t, d in arcpack.read(open(src, 'rb').read())[1] if t == T4['WAVE']}
        same = 0
        for p, d in waves.items():
            name = p.split('\\')[-1]
            k = [x for x in s4 if suffix_of(x) == suffix_of(name)]
            if not k: continue
            m = S4.madp_parse(s4[k[0]]); n = struct.unpack_from('<I', d, 8)[0]
            same += d[0x78:0x78 + n] == m['data'] and struct.unpack_from('<I', d, 0x60)[0] == m['samples']
        print('  waves: %d, %d bit-identical to the 4U source (+ %d GU-only)' % (len(waves), same, len(waves) - len(s4)))
        ok &= same == len(s4)
    print('OK' if ok else 'PROBLEMS')
    return ok


# ------------------------------------------------------------------ selftest on Capcom's weapon conversions

def pairs(dir4u, rom):
    """579 (nn, n4, 4U arc path, GU snd arc path): see the docstring."""
    import glob
    sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/tools')
    import mod as modlib
    import gear_weapons_em089 as G
    from build_assets import arc as gu_arc
    res = gu_arc(rom.read('/nativeNX/loc/arc/resident.arc'))
    out = []
    for nn, pf in PFX.items():
        rows = G.table(res['table\\weapon%02dBaseData' % nn], G.base_layout(nn))[1]
        srq = collections.defaultdict(set)
        for b in rows: srq[b['mModelID']].add(b['mSrqrNo'])
        for f in sorted(glob.glob(os.path.join(dir4u, 'pl_%s[0-9]*.arc' % pf))):
            m = re.search(r'pl_%s(\d+)\.arc$' % pf, f)
            if not m: continue
            n4 = int(m.group(1))
            gs, gm = '/nativeNX/arc/weapon/w%02d/snd/%03d.arc' % (nn, n4), '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, n4)
            if gs not in rom.files or gm not in rom.files or srq.get(n4) != {n4}: continue
            e4 = arcpack.read(open(f, 'rb').read())[1]
            if not any(p.startswith('sound\\') for p, t, d in e4): continue
            m4 = {p.split('\\')[-1]: d for p, t, d in e4 if t == 0x58A15856}
            mg = {p.split('\\')[-1]: d for p, t, d in arcpack.read(rom.read(gm))[1] if t == 0x58A15856}
            same = False
            for part in set(m4) & set(mg):
                a, b = modlib.parse(m4[part]), modlib.parse(mg[part])
                same |= a['local'] == b['local'] and a['aabb'] == b['aabb'] and a['material_names'] == b['material_names']
            if same: out.append((nn, n4, f, gs))
    return out


def selftest(dir4u):
    rom = gu_rom()
    P = pairs(dir4u, rom)
    C = collections.Counter(); per = collections.defaultdict(collections.Counter)
    wordfail = collections.defaultdict(collections.Counter)
    vote = collections.defaultdict(collections.Counter)       # (class, word) -> template / 4U right where they differ
    odd = []
    for nn, n4, f, gs in P:
        src = open(f, 'rb').read()
        try:
            data, log = convert(nn, src, n4, rom=rom)
        except SystemExit as ex:
            C['convert refused (%s)' % str(ex).split(':')[-1].strip()] += 1; continue
        ours = arcpack.read(data)[1]; cap = arcpack.read(rom.read(gs))[1]
        C['pairs'] += 1
        same_list = [(p, t) for p, t, d in ours] == [(p, t) for p, t, d in cap]
        C['entry list (path, type, order) equal'] += same_list
        if not same_list:
            a, b = [(p, t) for p, t, d in ours], [(p, t) for p, t, d in cap]
            odd.append('%s: ours only %s | GU only %s%s' % (f.split('/')[-1], [p.split('\\')[-1] for p, t in a if (p, t) not in b],
                       [p.split('\\')[-1] for p, t in b if (p, t) not in a], ' | order differs' if set(a) == set(b) else ''))
        tpl = class_template(nn, rom)
        for p, t, d in arcpack.read(src)[1]:          # vote: class template vs 4U word, where they differ
            if t != T4['REQ'] or not p.startswith('sound\\'): continue
            kind = kind_of(p.split('\\')[-1])
            gq = [g for q, tt, g in cap if tt == TG['REQ'] and kind_of(q.split('\\')[-1]) == kind]
            gw = {w[0]: w for w in S4.reqgu_parse(gq[0])['ents']} if gq else {}
            for w in S4.req4_parse(d)['ents']:
                x = gw.get(w[0])
                if x is None: continue
                c, tm = struct.unpack('<33I', S4.req_ent_gu(w)), tpl['reqs'][kind]['ent'][w[0]]
                for j in range(33):
                    if c[j] != tm[j]:
                        vote[(nn, j)]['n'] += 1; vote[(nn, j)]['tpl'] += tm[j] == x[j]; vote[(nn, j)]['4U'] += c[j] == x[j]
        G = {(p, t): d for p, t, d in cap}
        for p, t, d in ours:
            g = G.get((p, t))
            if g is None: C['our entry missing in GU'] += 1; continue
            if t == TG['WAVE']:
                n = struct.unpack_from('<I', g, 8)[0]       # kept = same DSP data and sample count
                kept = d[0x78:0x78 + n] == g[0x78:0x78 + n] and d[0x60:0x64] == g[0x60:0x64]
                C['waves'] += 1; C['waves Capcom kept bit-identical'] += kept
                if kept: C['  of those, byte-identical outside the stamp'] += d[:0x10] + d[0x18:] == g[:0x10] + g[0x18:]
            elif t == TG['BANK']:
                C['banks'] += 1; C['banks byte-identical'] += d == g; per[nn]['bank ok'] += d == g; per[nn]['bank'] += 1
                b, bg = S4.bank_parse(d), S4.bank_parse(g)
                ge = {a[72]: (q, a) for q, _, a in bg['ents']}
                for q, _, a in b['ents']:
                    C['bank entries'] += 1
                    if a[72] not in ge: continue
                    C['bank entries: same wave path'] += q == ge[a[72]][0]
                    C['bank entries: 76 bytes identical'] += a == ge[a[72]][1]
                    if a[5] != ge[a[72]][1][5]: per[nn]['bank byte5 differs'] += 1
            elif t == TG['REQ']:
                C['requests'] += 1; C['requests byte-identical'] += d == g
                r, rg = S4.reqgu_parse(d), S4.reqgu_parse(g)
                gw = {w[0]: w for w in rg['ents']}
                for w in r['ents']:
                    x = gw.get(w[0])
                    C['request entries'] += 1
                    if x is None: continue
                    C['request entries identical'] += w == x
                    per[nn]['req ent'] += 1; per[nn]['req ent ok'] += w == x
                    for j in range(33):
                        if w[j] != x[j]: wordfail[(nn, j)][(w[0] & 0xFFFF)] += 1
                C['request header + string table identical'] += d[:0x34] == g[:0x34] and \
                    d[0x34 + 132 * len(r['ents']):] == g[0x34 + 132 * len(rg['ents']):]
    for k, v in C.items(): print('%6d  %s' % (v, k))
    for o in odd: print('  entry list differs:', o)
    print('vote, request words where the class template and the 4U word (snd4u2gu rules) differ: template right / '
          '4U right / entries (* = taken from 4U, WORDS_4U)')
    for nn in sorted({n for n, j in vote}):
        print('  w%02d %-4s %s' % (nn, PFX[nn], ' '.join('w%d%s %d/%d/%d' % (j, '*' if j in WORDS_4U.get(nn, ()) else '',
              v['tpl'], v['4U'], v['n']) for (n, j), v in sorted(vote.items()) if n == nn)))
    print('per class: banks identical, request entries identical (words that differ: word -> entries)')
    for nn in sorted(per):
        wf = {j: sum(c.values()) for (n, j), c in wordfail.items() if n == nn}
        print('  w%02d %-4s banks %3d / %3d, request entries %4d / %4d %s' % (
            nn, PFX[nn], per[nn]['bank ok'], per[nn]['bank'], per[nn]['req ent ok'], per[nn]['req ent'],
            ' '.join('w%d:%d' % kv for kv in sorted(wf.items()))))
    return C


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else ''
    if cmd == 'convert':
        nn, src, dst = int(a[1]), a[2], a[3]
        n4 = int(re.search(r'(\d{3})\.arc$', src).group(1))
        model = int(a[a.index('--model') + 1]) if '--model' in a else None
        data, log = convert(nn, open(src, 'rb').read(), n4, model)
        open(dst, 'wb').write(data)
        print('\n'.join(log)); print(len(data), 'bytes ->', dst)
    elif cmd == 'gogma':
        dir4u = a[1]; out = a[2] if len(a) > 2 else OUT_DEFAULT
        rom = gu_rom()
        for nn, n in GOGMA.items():
            src = os.path.join(dir4u, 'pl_%s%03d.arc' % (PFX[nn], n))
            data, log = convert(nn, open(src, 'rb').read(), n, rom=rom)
            dst = os.path.join(out, 'w%02d' % nn, 'snd', '%03d.arc' % n)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
            print('w%02d %s%03d -> %s (%d B)' % (nn, PFX[nn], n, dst, len(data)))
            for l in log: print(l)
    elif cmd == 'check':
        sys.exit(0 if check(int(a[1]), a[2], a[3] if len(a) > 3 else None) else 1)
    elif cmd == 'selftest':
        selftest(a[1])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
