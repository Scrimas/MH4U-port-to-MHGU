"""armor4u2gu.py : convert an MH4U player armor arc (pl_{m,f}_<part><N>.arc) into an MHGU armor arc
(nativeNX/arc/player/com/{m,f}/<N>/<part>.arc) -- prototype (2026-10-20, Gogma armor = 4U models 352 / 353).

  armor4u2gu.py index DIR4U OUT.pkl         material template index from Capcom's own conversions: every 4U armor
                                            arc DIR4U/data/pl_[mf]_*.arc that GU also has (same model number)
  armor4u2gu.py convert IN.arc OUT.arc IDX.pkl [--no-ctc] [--xfs-from N] [--no-edges]
  armor4u2gu.py check OUT.arc               parse every entry back (MOD index runs / vertex ranges, MRL texture
                                            references, TEX decode)

Rules, each checked on the 4U -> GU pairs Capcom made (GU keeps 4U model numbers: 1799 of 1898 male pairs have
identical bones / bounding box / material names):
- skeleton: player bone IDs 0-19 have the same parents and local matrices in both games; IDs 20+ are per-armor
  (cloth) bones driven by the CTC. MODs carry only the bones they use; nothing to remap.
- MOD: tools/mod4u2gu.convert(edges=True) (bones, matrices, remap equal; per-material envelope counts equal
  Capcom's on 1795/1795 paired MODs). GU's extra edge meshes (drawMode 0x20, 0 under an 0xE4C0 proxy; format
  0x0CB68015) are built as Capcom built them for converted 4U armor (mod4u2gu EDGE_FMT notes): one per mesh with
  hard (normal-split) edges, degenerate quads along them + corner fills; on all 2936 same-model pairs the same
  meshes get one (9260 / 9296) and 98.8 % of Capcom's quad triangles are reproduced. Mesh numbers / table order
  then follow Capcom's. --no-edges gives the previous output.
- own textures: 4U BM (ETC1A4 128x128, 4 mips) -> GU BC3 with the full mip chain; BM+A = the BM alpha as BC4
  (Capcom: BM+A == BM alpha, corr 0.997). Common textures (env_pNNN_BM, m_/f_skin_BM) = GU's own copies
  (one GU dropped: the 4U arc's copy as BC3, same path).
- MRL: per 4U material, the GU material Capcom made from the identical 4U parameter block (texture indices
  ignored; 2456 of 2604 4U keys give exactly one GU block), else from the nearest 4U block with the same states,
  texture-slot set and material type. GU material type (w6 bits 21-28) = 4U type >> 2 (sym 3, skin 2, else 0).
  Texture slots: tAlbedoMap = 4U albedo, tSphereMap = 4U tExtendMap, tSpecularMap = albedo or its BM+A, as in
  the template.
- CTC v0x16: header 0x40 copied, each 0x48-byte chain record gets 8 bytes (0xcd) at +0x10, node records copied
  (201 of 225 pairs equal, GU's 0xcdcdcdcd words = never-written padding; the other 24 differ in content).
- XFS (helm only, every GU helm arc has one, 4U has none): 0x66c89ed2 v0x10, InfoType 0, mQuality 2,
  mAutoDelete 0, mpArray of 32 {u16 mDispFlag0, u16 mDispFlag1} = one per hairstyle (GU m/f_hair000-029, 4U
  000-027; hair mesh groups are the same in both games); mDispFlag0 bit g = hair group g shown (bits 10-15, no
  such groups, always set). Capcom's tables for converted 4U helms vary per helm and per hairstyle (683 same-model
  helms, 296 distinct over styles 0-27) and no 4U source was found: not in the 40-B head record (no byte or u16
  predicts them), no model- or record-indexed u8 / bit table in the v1.1 exe separates hide-all from show-all
  helms, not geometric (helm coverage of each hair group predicts the bit at 71 % vs 66 % for "always hidden").
  So copied from a GU helm (placeholder, --xfs-from, default 354).
- arc order TEX -> MRL -> MOD -> CTC -> XFS (a model fetches its MRL / textures by path while loading).
"""
import collections, glob, hashlib, os, pickle, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, mod as modlib, mod4u2gu, mrl, mrl_build, tex

GU_ROMFS = paths.GU_ROMFS
T_TEX, T_MRL, T_MOD, T_CTC, T_XFS = 0x241f5deb, 0x2749c8a8, 0x58a15856, 0x535d969f, 0x66c89ed2
ARC_RE = re.compile(r'pl_([mf])_(helm|body|arm|wst|leg)(\d+)\.arc$')
_rom = None


def rom():
    global _rom
    if _rom is None:
        from romfs import RomFS
        _rom = RomFS(GU_ROMFS)
    return _rom


def gu_arc_path(sex, part, n):
    return '/nativeNX/arc/player/com/%s/%03d/%s.arc' % (sex, n, part)


def entries(d):
    return arcpack.read(d)[1]


# ---------------------------------------------------------------- MRL template index

def blk4(m):
    """4U material: (parameter block with texture indices zeroed, constant floats after the descriptors)."""
    b = bytearray(m['block'])
    k = 0
    while 12 * k + 12 <= len(b):
        a, v, w = struct.unpack_from('<III', b, 12 * k)
        k += 1
        if a == 0 and v == 0 and w == 0: break
        if a & 0xF == 3: struct.pack_into('<I', b, 12 * k - 8, 0)
    data = bytes(b[12 * k:])
    return bytes(b), np.frombuffer(data[:len(data) // 4 * 4], '<f4').astype(np.float64)


def sig4(m):
    """(states, used texture slots, material type) of a 4U material."""
    slots = tuple(sorted(p[0] for p in m['params'] if p[1] == 3 and p[2]))
    return tuple(s for s in m['states'] if s), slots, ((m['words'][6] >> 21) & 0xFF) >> 2


def index(dir4u, out):
    r = rom()
    idx = []
    for f in sorted(glob.glob(os.path.join(dir4u, 'data', 'pl_*.arc'))):
        mm = ARC_RE.search(f)
        if not mm: continue
        gp = gu_arc_path(mm.group(1), mm.group(2), int(mm.group(3)))
        if gp not in r.files: continue
        e4 = {th: d for p, th, d in entries(open(f, 'rb').read())}
        eg = {th: (p, d) for p, th, d in entries(r.read(gp))}
        if T_MRL not in e4 or T_MRL not in eg: continue
        rg = mrl.read(eg[T_MRL][1])
        gby = {m['name']: (i, m) for i, m in enumerate(rg['mats'])}
        for m in mrl.read(e4[T_MRL])['mats']:
            if m['name'] not in gby: continue
            gi, g = gby[m['name']]
            if g['words'][12]: continue                       # template must have no animation block
            zb, fl = blk4(m)
            gz = bytearray(g['block'])
            for k in range(g['words'][6] & 0xFFF):
                if struct.unpack_from('<I', gz, 12 * k)[0] & 0xF == 3: struct.pack_into('<I', gz, 12 * k + 4, 0)
            idx.append(dict(key=hashlib.md5(zb + struct.pack('<10I', *m['words'][3:13])).hexdigest(),
                            sig=sig4(m), floats=fl, gu=(gp, eg[T_MRL][0], gi),
                            gblock=hashlib.md5(bytes(gz) + struct.pack('<5I', *g['words'][3:8])).hexdigest()))
    pickle.dump(idx, open(out, 'wb'))
    print(len(idx), 'material pairs ->', out)


def pick_template(idx, m):
    zb, fl = blk4(m)
    key = hashlib.md5(zb + struct.pack('<10I', *m['words'][3:13])).hexdigest()
    exact = [e for e in idx if e['key'] == key]
    if exact:                                                 # majority GU block among Capcom's conversions
        best = collections.Counter(e['gblock'] for e in exact).most_common(1)[0][0]
        return [e for e in exact if e['gblock'] == best][0], 'exact (%d)' % len(exact)
    s = sig4(m)
    cand = [e for e in idx if e['sig'] == s and len(e['floats']) == len(fl)]
    how = 'nearest'
    if not cand:     # e.g. RSMeshBias5 + sphere map: no pair has it -> template with RSMesh, 4U RS state set later
        plain = (tuple('RSMesh' if x.startswith('RSMeshBias') else x for x in s[0]),) + s[1:]
        cand = [e for e in idx if e['sig'] == plain and len(e['floats']) == len(fl)]
        how = 'nearest, RS state from 4U'
    # no pair with these exact states (e.g. 4U Zamtrios Z f_helm436: BSBlendAlpha + DSZTestWrite + IABGBase): same
    # blend state + texture slots + type, then same blend state + type; DS and RS taken from 4U (as weapon4u2gu.py)
    st = lambda sig, k: [x for x in sig[0] if x.startswith(k)][:1]
    for lvl, core in (('BS/DS/slots/type', lambda g: (st(g, 'BS'), st(g, 'DS'), g[1], g[2])),
                      ('BS/slots/type', lambda g: (st(g, 'BS'), g[1], g[2])),
                      ('BS/type', lambda g: (st(g, 'BS'), g[2]))):
        if cand: break
        same = [e for e in idx if core(e['sig']) == core(s)]
        cand = [e for e in same if len(e['floats']) == len(fl)] or same
        how = 'relaxed %s, DS+RS states from 4U' % lvl
    if not cand: raise SystemExit('no GU template with signature %s' % (s,))
    if len({len(e['floats']) for e in cand}) > 1 or len(cand[0]['floats']) != len(fl):
        cand = [e for e in cand if len(e['floats']) == len(cand[0]['floats'])]
        n = min(len(fl), len(cand[0]['floats']))
        d = [float(np.abs(np.nan_to_num(e['floats'][:n] - fl[:n])).sum()) for e in cand]
        i = int(np.argmin(d))
        return cand[i], '%s (L1 %.3f over %d, constant block sizes differ)' % (how, d[i], len(cand))
    d = [float(np.abs(np.nan_to_num(e['floats'] - fl)).sum()) for e in cand]
    i = int(np.argmin(d))
    return cand[i], '%s (L1 %.3f over %d)' % (how, d[i], len(cand))


# ---------------------------------------------------------------- conversion

def gu_common(paths):
    """GU's own copies of common textures (player\\mod\\common\\...), searched in the GU armor arcs."""
    r = rom(); out = {}
    want = set(paths)
    for k in sorted(r.files):
        if not want - set(out): break
        if '/arc/player/com/' not in k or not k.endswith('.arc'): continue
        for p, th, d in entries(r.read(k)):
            if th == T_TEX and p in want and p not in out: out[p] = d
    return out


def ctc4u2gu(a):
    assert a[:4] == b'CTC\0' and struct.unpack_from('<I', a, 4)[0] == 0x16
    nch = struct.unpack_from('<I', a, 0x10)[0]
    out = bytearray(a[:0x40]); p = 0x40
    for _ in range(nch):
        ch = bytearray(a[p:p + 0x48]); p += 0x48
        ch[0x10:0x10] = b'\xcd' * 8
        out += ch
    return bytes(out + a[p:])


def convert(src, idx, ctc=True, xfs_from=354, edges=True, log=print):
    mm = ARC_RE.search(src)
    sex, part, n = mm.group(1), mm.group(2), int(mm.group(3))
    e4 = entries(open(src, 'rb').read())
    by = {th: (p, d) for p, th, d in e4 if th != T_TEX}
    tex4 = {p: d for p, th, d in e4 if th == T_TEX}
    mod_path, mod4 = by[T_MOD]
    r4 = mrl.read(by[T_MRL][1])
    names = {zlib.crc32(x.encode()) ^ 0xFFFFFFFF: x for x in modlib.parse(mod4)['material_names']}
    # textures: own BM -> BC3 (+ BM+A as BC4), common ones from GU
    own = [p for p in tex4 if '\\common\\' not in p]
    gtex = []                                                 # [(path, data)] in output order
    for p in own:
        img = tex.decode(tex4[p])
        gtex.append((p, tex.encode_gu(img, 'bc3')))
        a = img[..., 3:4].repeat(4, -1)
        gtex.append((p + '+A', tex.encode_gu(np.ascontiguousarray(a), 'bc4')))
    common = [p for th, p in r4['textures'] if th and '\\common\\' in p]
    gc = gu_common(common)
    for p in common:
        if p in gc:
            gtex.append((p, gc[p]))
        else:          # GU dropped this env texture: ship the 4U one (BC3, same path), as tools/weapon4u2gu.py
            if p not in tex4: raise SystemExit('GU has no %s and the 4U arc does not carry it' % p)
            gtex.append((p, tex.encode_gu(tex.decode(tex4[p]), 'bc3')))
            log('  %s: not in GU, converted from 4U' % p)
    tpath = [p for p, _ in gtex]
    ti = lambda p: tpath.index(p) + 1
    mats = []
    for m in r4['mats']:
        if m['name'] not in names:
            log('  material %08x: not used by the MOD, dropped' % m['name']); continue
        t, how = pick_template(idx, m)
        key = 'arm_%s_%d' % (t['gu'][0].split('/')[-2] + t['gu'][0].split('/')[-1], t['gu'][2])
        mrl_build.TEMPLATES[key] = t['gu']
        p4 = {p[0]: r4['textures'][p[2] - 1][1] for p in m['params'] if p[1] == 3 and p[2]}
        alb = p4.get('tAlbedoMap')
        # template: does its tSpecularMap use the albedo itself or the albedo's BM+A?
        gd = rom().read(t['gu'][0])
        gm = mrl.read([d for p, th, d in entries(gd) if th == T_MRL][0])
        gmat = gm['mats'][t['gu'][2]]
        gs = {p[0]: p[2] for p in gmat['params'] if p[1] == 3}
        spec_plusA = 'tSpecularMap' in gs and gm['textures'][gs['tSpecularMap'] - 1][1].endswith('+A')
        if alb is None:      # no 4U texture at all (3 materials in 5395 4U armor arcs, C): every slot null, as
            # Capcom's only converted case, GU m/008/leg skin material (tAlbedoMap / tSpecularMap 0)
            slots = dict({s: 0 for s in gs}, tAlbedoMap=0)
            log('  %s: no 4U albedo, null texture slots (as GU m/008/leg)' % names[m['name']])
        else:
            slots = {'tAlbedoMap': ti(alb),
                     'tSpecularMap': ti(alb + '+A') if spec_plusA and alb + '+A' in tpath else ti(alb)}
        if 'tSphereMap' in gs and alb is not None:
            if 'tExtendMap' not in p4: raise SystemExit('template %s has a sphere map, 4U material none' % key)
            slots['tSphereMap'] = ti(p4['tExtendMap'])
        other = set(gs) - set(slots)
        if other: log('  warning: template slots %s set to the albedo' % sorted(other))
        mtype = ((m['words'][6] >> 21) & 0xFF) >> 2
        extra, states = {'mtype': mtype}, ()
        rs = [x for x in m['states'] if x and x.startswith('RSMeshBias')]
        if 'RS state from 4U' in how:     # GU w7 bits 16-19 = N of RSMeshBiasN (mrl_build W7_BIAS_SHIFT)
            states, extra['bias'] = (rs[0],), int(rs[0][len('RSMeshBias'):])
        if 'DS+RS states from 4U' in how:
            ds = [x for x in m['states'] if x and x.startswith('DS')]
            r4s = [x for x in m['states'] if x and x.startswith('RSMesh') and not x.startswith('RSMeshC')]
            states = tuple(ds[:1] + r4s[:1])
            extra['bias'] = int(r4s[0][len('RSMeshBias'):]) if r4s and r4s[0].startswith('RSMeshBias') else 0
        mats.append((names[m['name']], key, slots, states, {}, extra))
        log('  %-34s <- %s %s mat %d  [%s] type %d' % (names[m['name']], t['gu'][0].split('com/')[1], t['gu'][1].split('\\')[-1],
                                                     t['gu'][2], how, mtype))
    mrl_out = mrl_build.build(rom(), mats, tpath)
    out = [(p, T_TEX, d) for p, d in gtex]
    out.append((by[T_MRL][0], T_MRL, mrl_out))
    out.append((mod_path, T_MOD, mod4u2gu.convert(mod4, edges=edges)))
    if T_CTC in by and ctc:
        out.append((by[T_CTC][0], T_CTC, ctc4u2gu(by[T_CTC][1])))
    if part == 'helm':
        gx = [d for p, th, d in entries(rom().read(gu_arc_path(sex, part, xfs_from))) if th == T_XFS][0]
        out.append((mod_path, T_XFS, gx))
        log('  XFS copied from GU %s/%03d/helm (placeholder)' % (sex, xfs_from))
    return arcpack.build(out)


def check(path):
    ents = entries(open(path, 'rb').read())
    paths = {(p, th) for p, th, d in ents}
    ok = True
    for p, th, d in ents:
        if th == T_TEX:
            h = tex.parse(d); img = tex.decode(d)
            info = 'fmt %#x %dx%d mips %d unk1 %d' % (h['fmt'], h['width'], h['height'], h['mips'], h['unk1'])
        elif th == T_MRL:
            r = mrl.read(d)
            miss = [t for th2, t in r['textures'] if th2 and (t, T_TEX) not in paths]
            bad = [(hex(m['name']), q) for m in r['mats'] for q in m['params']    # 0 = no texture (GU m/008/leg)
                   if q[1] == 3 and not 0 <= q[2] <= len(r['textures'])]
            info = 'v%#x %d materials, %d textures, missing in arc %s, bad indices %s' % (r['version'], len(r['mats']), len(r['textures']), miss, bad)
            ok &= not miss and not bad
        elif th == T_MOD:
            m = modlib.parse(d)
            nib = len(m['ib']) // 2
            ib = struct.unpack('<%dH' % nib, m['ib'])
            bad = []                     # index run inside the buffer, followed by 0xFFFF, vertices inside the VB
            for k, x in enumerate(m['mesh_list']):
                run = [i for i in ib[x['indexStart']:x['indexStart'] + x['numIndices']] if i != 0xFFFF]
                lo, hi = (x['vertexStart'], x['vertexStart'] + x['numVertices']) if x['streamOff'] == 0 else (0, x['numVertices'])
                if (x['indexStart'] + x['numIndices'] >= nib or ib[x['indexStart'] + x['numIndices']] != 0xFFFF or
                        not run or min(run) < lo or max(run) >= hi or
                        x['streamOff'] + hi * x['stride'] > m['vbSize']):
                    bad.append(k)
            ne = sum(1 for x in m['mesh_list'] if x['fmt'] == mod4u2gu.EDGE_FMT)
            info = 'v%#x bones %d meshes %d (edge %d) materials %d envelopes %d, bad index runs %s' % (
                m['version'], m['bones'], m['meshes'], ne, m['materials'], m['envCount'], bad)
            ok &= not bad
        else:
            info = '%r v%#x %d B' % (d[:4], struct.unpack_from('<H', d, 4)[0], len(d))
        print('  %-44s %08x %s' % (p, th, info))
    print('OK' if ok else 'PROBLEMS')
    return ok


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'index':
        index(sys.argv[2], sys.argv[3])
    elif cmd == 'convert':
        a = sys.argv[2:]
        xf = int(a[a.index('--xfs-from') + 1]) if '--xfs-from' in a else 354
        data = convert(a[0], pickle.load(open(a[2], 'rb')), ctc='--no-ctc' not in a, xfs_from=xf,
                       edges='--no-edges' not in a)
        open(a[1], 'wb').write(data)
        print(len(data), 'bytes ->', a[1])
    elif cmd == 'check':
        sys.exit(0 if check(sys.argv[2]) else 1)
