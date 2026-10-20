"""weapon4u2gu.py : convert an MH4U weapon model arc (data/pl_<pfx>NNN.arc) into an MHGU weapon arc
(nativeNX/arc/weapon/wNN/MMM.arc) -- prototype (2026-10-20, Gogma weapons). Built on tools/armor4u2gu.py.

  weapon4u2gu.py index DIR4U OUT.pkl        material template index from Capcom's own weapon conversions: every
                                            4U DIR4U/pl_<pfx>NNN.arc whose MOD part GU also has (same class and
                                            number, same bones / bounding box / material names)
  weapon4u2gu.py convert NN IN.arc OUT.arc IDX.pkl [--model M]
  weapon4u2gu.py check OUT.arc              parse every entry back (armor4u2gu.check + MOD/MRL material cover)

Rules, each checked on the 4U -> GU weapon pairs Capcom made (GU keeps 4U weapon model numbers: GS 56/62 same-number
pairs are the same model, Ham 59/64, Lance 94/106 parts, HBG 30/32, LBG 43/44, LS 76/92, SA 44/48, GL 88/102,
Bow 86/96, DB 106/114, HH 38/46, IG 29/33, CB 52/60; SnS only 26/116):
- arc content: 4U = MODs + MRLs + own BM + common env textures + the weapon's sounds (sound\\se\\pl\\wp\\...);
  GU = the same models/materials + BM+A, sounds live in arc/weapon/wNN/snd/%03d.arc (mSrqrNo). In 310/310 paired
  arcs the only GU-only entries are BM+A textures (and a few env textures): no GU-added parts (LS saya exists in
  83/123 GU arcs but was never added to a converted 4U LS).
- paths: 4U weapon\\<pfx>\\<pfx>NNN\\x -> GU weapon\\wNN\\<pfx>NNN\\x (env textures keep weapon\\common\\...).
- MOD: tools/mod4u2gu.convert (per-material envelope counts equal Capcom's on 310/310 paired weapon MODs). GU
  weapons mostly use other vertex formats, but 0x14D40022 occurs on GU weapon meshes too (9 meshes, IASkinTB2wt
  like all GU weapon/armor materials). 4U 0x7BA7401B (32 B) = 0xD6784014 + RGBA8 vertex colour (glow meshes;
  Gogma: ken079, sou_l087, sou_r087, one mesh each) -> GU 0xCBF6C01A (24 B, one bone + colour) exactly as Capcom's
  17 paired meshes (mod4u2gu COLOUR_GU notes, vcolour=True), in its own stream (normalize_4u keep_colour).
- edge meshes (mod4u2gu edges=True, 2026-10-20): the armor rule holds on Capcom's weapon pairs (598 same-model
  MODs whose GU normal meshes follow the 4U mesh order; mod4u2gu EDGE_FMT notes): which meshes get one 2229 /
  2257, quad triangles 131135 equal / 863 only ours / 1194 only Capcom's, record (drawMode & 0x1020, group /
  material / lod / alpha / weights, data1 bits) 1259 / 1259, numbering 598 / 598, table order 559 / 598.
  Capcom's edge vertex format follows the normal mesh's weight count (1 -> 0xB0983013, 2 -> 0xDB7DA014,
  3 -> 0x0CB68015: 11 / 11, incl. the 6 GU weapon 0x14D40022 meshes), so our 0x14D40022 meshes get 0x0CB68015
  edges as on armor. Vertex-colour (0xCBF6C01A) meshes get none (Capcom: 131 / 132).
- drawMode (vote over the same pairs, drawmodes()): 4U 0xECD3 -> GU 0xEFFF 250 / 0xECF3 154 / 0xEEFB 18; the GU
  material decides: states BSAddAlpha + DSZTest + RSMesh -> 0xECF3 on 153 / 153 meshes (153 of the 156 0xECF3
  meshes); every other visible mesh 0xEFFF (mod4u2gu.gu_drawmode). 0xEEFB (27 meshes, mixed states) has no rule.
- textures, MRL: as armor4u2gu (BM -> BC3 + BM+A as BC4, env textures = GU's own copies, GU material from the
  identical 4U parameter block). Weapons add material animations (glow/scroll, 4U w12 = 104/124/144/224/244/580):
  the index key includes the 4U animation block, and the GU template's own animation block (Capcom's conversion,
  e.g. 4U 124 -> GU 204 B, 580 -> 808 B) is copied with it. GU material type = 4U type >> 2 (as armor; weapons:
  1/3 -> 0, 9/11 -> 2, 21 -> 5, 120..123 -> 30).
"""
import collections, glob, hashlib, os, pickle, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import armor4u2gu as A
import arcpack, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, tex

T_TEX, T_MRL, T_MOD = A.T_TEX, A.T_MRL, A.T_MOD
PFX = {0: 'two', 1: 'one', 2: 'ham', 3: 'lan', 4: 'hbg', 6: 'lbg', 7: 'swo', 8: 'axe', 9: 'gun', 10: 'bow',
       11: 'sou', 12: 'hue', 13: 'rod', 14: 'gaxe'}
rom = A.rom


def gu_arc_path(nn, n):
    return '/nativeNX/arc/weapon/w%02d/%03d.arc' % (nn, n)


def entries(d):
    return arcpack.read(d)[1]


# ---------------------------------------------------------------- 4U MOD normalisation (before mod4u2gu)

def normalize_4u(d, keep_colour=True):
    """4U MOD with mixed vertex streams (a 0x7BA7401B 32-B mesh = 0xD6784014 + RGBA8 colour, ken079 /
    sou_l,r087; either kind may sit in a stream at streamOff != 0) -> the 0xD6784014 meshes in one 28-B stream in
    mesh order, index values rebased (4U indices are absolute within a stream). keep_colour: each 0x7BA7401B mesh
    keeps its 32-B vertices, appended after that stream as its own block (vertexStart 0, streamOff = block offset,
    indices local), for mod4u2gu.convert(vcolour=True) -> GU 0xCBF6C01A; else cut to 28 B (colour dropped).
    A 0x43FB3015 mesh (32 B = 0xD6784014 + tangent) next to 0xD6784014 ones (sou_l,r095: own stream at streamOff 0)
    is cut to its 28-B 0xD6784014 part the same way (tangent dropped, as on the other meshes).
    Unchanged if already uniform."""
    m = modlib.parse(d)
    ms = m['mesh_list']
    if all(x['fmt'] == 0xD6784014 and x['streamOff'] == 0 for x in ms) or \
            all(x['fmt'] == 0x43FB3015 and x['streamOff'] == 0 for x in ms) or \
            not all(x['fmt'] in (0xD6784014, 0x7BA7401B, 0x43FB3015) for x in ms):
        return d
    vb = bytearray(); ib = bytearray(m['ib']); recs = [None] * len(ms)
    colour = [j for j, x in enumerate(ms) if keep_colour and x['fmt'] == 0x7BA7401B]
    for j in [j for j in range(len(ms)) if j not in colour] + colour:
        x = ms[j]
        st = x['stride']
        base = m['offsets']['vb'] + x['streamOff'] + x['vertexStart'] * st
        v = np.frombuffer(d[base:base + x['numVertices'] * st], np.uint8).reshape(-1, st)
        r = bytearray(x['raw'])
        if j in colour:
            delta = -x['vertexStart']
            struct.pack_into('<II', r, 12, 0, len(vb))
            vb += v.tobytes()
        else:
            nvs = len(vb) // 28
            delta = nvs - x['vertexStart']
            vb += np.ascontiguousarray(v[:, :28]).tobytes()
            d1 = struct.unpack_from('<I', r, 8)[0]
            struct.pack_into('<I', r, 8, (d1 & ~(0xFF << 16)) | (28 << 16))
            struct.pack_into('<III', r, 12, nvs, 0, 0xD6784014)
        for k in range(x['indexStart'], min(x['indexStart'] + x['numIndices'], len(ib) // 2)):
            i = struct.unpack_from('<H', ib, 2 * k)[0]
            if i != 0xFFFF: struct.pack_into('<H', ib, 2 * k, i + delta)
        recs[j] = r
    o = m['offsets']
    out = bytearray(d[:o['vb']]) + vb
    out += b'\0' * (-len(out) % 4)
    ib_off = len(out)
    out += ib + d[o['ib'] + len(m['ib']):]
    out[o['meshes']:o['meshes'] + 48 * len(ms)] = b''.join(recs)
    struct.pack_into('<I', out, 0x0C, sum(x['numVertices'] for x in ms))   # vertex count
    struct.pack_into('<I', out, 0x18, len(vb))                  # vbSize
    struct.pack_into('<I', out, 0x3C, ib_off)                   # ibOff
    return bytes(out)


# ---------------------------------------------------------------- MRL template index

def anim4(d, m):
    w = m['words']
    return d[w[14]:w[14] + w[12]] if w[12] else b''


def key4(d, m):
    zb, fl = A.blk4(m)
    k = hashlib.md5(zb + struct.pack('<10I', *m['words'][3:13])).hexdigest()
    return k, hashlib.md5(k.encode() + anim4(d, m)).hexdigest(), fl


def index(dir4u, out):
    r = rom()
    idx = []
    for nn, pf in PFX.items():
        for f in sorted(glob.glob(os.path.join(dir4u, 'pl_%s[0-9]*.arc' % pf))):
            mm = re.search(r'pl_%s(\d+)\.arc$' % pf, f)
            if not mm: continue
            gp = gu_arc_path(nn, int(mm.group(1)))
            if gp not in r.files: continue
            e4 = entries(open(f, 'rb').read())
            eg = entries(r.read(gp))
            mod4 = {p.split('\\')[-1]: d for p, th, d in e4 if th == T_MOD}
            modg = {p.split('\\')[-1]: d for p, th, d in eg if th == T_MOD}
            mrl4 = {p.split('\\')[-1]: d for p, th, d in e4 if th == T_MRL}
            mrlg = {p.split('\\')[-1]: (p, d) for p, th, d in eg if th == T_MRL}
            for part in mod4:
                if part not in modg or part not in mrl4 or part not in mrlg: continue
                a, b = modlib.parse(mod4[part]), modlib.parse(modg[part])
                if not (a['local'] == b['local'] and a['aabb'] == b['aabb'] and a['material_names'] == b['material_names']):
                    continue
                d4, (gpath, dg) = mrl4[part], mrlg[part]
                rg = mrl.read(dg)
                gby = {m['name']: (i, m) for i, m in enumerate(rg['mats'])}
                for m in mrl.read(d4)['mats']:
                    if m['name'] not in gby: continue
                    gi, g = gby[m['name']]
                    k, ka, fl = key4(d4, m)
                    gz = bytearray(g['block'])
                    for q in range(g['words'][6] & 0xFFF):
                        if struct.unpack_from('<I', gz, 12 * q)[0] & 0xF == 3: struct.pack_into('<I', gz, 12 * q + 4, 0)
                    idx.append(dict(key=k, keya=ka, sig=A.sig4(m), anim=m['words'][12], floats=fl, gu=(gp, gpath, gi),
                                    ganim=g['words'][12],
                                    gblock=hashlib.md5(bytes(gz) + struct.pack('<5I', *g['words'][3:8]) + g['anim']).hexdigest()))
    pickle.dump(idx, open(out, 'wb'))
    print(len(idx), 'material pairs ->', out)


def pick_template(idx, d, m):
    k, ka, fl = key4(d, m)
    for field, val, how in (('keya', ka, 'exact+anim'), ('key', k, 'exact')):
        ex = [e for e in idx if e[field] == val]
        if ex:
            best = collections.Counter(e['gblock'] for e in ex).most_common(1)[0][0]
            return [e for e in ex if e['gblock'] == best][0], '%s (%d)' % (how, len(ex))
    s, an = A.sig4(m), m['words'][12]
    for how, cond in (('nearest, same anim size', lambda e: e['sig'] == s and e['anim'] == an),
                      ('nearest', lambda e: e['sig'] == s and (e['ganim'] > 0) == (an > 0)),
                      ('nearest, any anim', lambda e: e['sig'] == s)):
        cand = [e for e in idx if cond(e) and len(e['floats']) == len(fl)]
        if cand: break
    if not cand:
        plain = (tuple('RSMesh' if x.startswith('RSMeshBias') else x for x in s[0]),) + s[1:]
        cand = [e for e in idx if e['sig'] == plain and len(e['floats']) == len(fl)]
        how = 'nearest, RS state from 4U'
    # no pair with these exact states (extra 4U states such as TMaterialOutline / DMP_pointSprite2_1 / SSPoint, or a
    # DS state): same blend state + texture slots + type, then same blend state + type; DS and RS taken from 4U
    st = lambda sig, k: [x for x in sig[0] if x.startswith(k)][:1]
    for lvl, core in (('BS/DS/slots/type', lambda g: (st(g, 'BS'), st(g, 'DS'), g[1], g[2])),
                      ('BS/slots/type', lambda g: (st(g, 'BS'), g[1], g[2])),
                      ('BS/type', lambda g: (st(g, 'BS'), g[2]))):
        if cand: break
        same = [e for e in idx if core(e['sig']) == core(s)]
        same = [e for e in same if (e['ganim'] > 0) == (an > 0)] or same    # keep the 4U animation if possible
        cand = [e for e in same if len(e['floats']) == len(fl)] or same
        how = 'relaxed %s, DS+RS states from 4U' % lvl
    if not cand: raise SystemExit('no GU template with signature %s' % (s,))
    if len({len(e['floats']) for e in cand}) > 1 or len(cand[0]['floats']) != len(fl):
        cand = [e for e in cand if len(e['floats']) == len(cand[0]['floats'])]
        n = min(len(fl), len(cand[0]['floats']))
        dist = [float(np.abs(np.nan_to_num(e['floats'][:n] - fl[:n])).sum()) for e in cand]
        i = int(np.argmin(dist))
        return cand[i], '%s (L1 %.3f over %d, constant block sizes differ)' % (how, dist[i], len(cand))
    dist = [float(np.abs(np.nan_to_num(e['floats'] - fl)).sum()) for e in cand]
    i = int(np.argmin(dist))
    return cand[i], '%s (L1 %.3f over %d)' % (how, dist[i], len(cand))


# templates with an animation block: mrl_build.load_template refuses them, so serve them here (block only; the
# GU animation block is passed to mrl_build.build as extra['anim'])
_load_template = mrl_build.load_template
_ANIMATED = {}


def _load_template_w(romfs, key):
    if key not in _ANIMATED: return _load_template(romfs, key)
    w, block, anim = _ANIMATED[key]
    return list(w), block


mrl_build.load_template = _load_template_w


def gu_material(t):
    """(words, block, anim bytes, texture table) of a GU template material."""
    gp, mp, gi = t['gu']
    ents = entries(rom().read(gp))
    d = [x for p, th, x in ents if th == T_MRL and p == mp][0]
    r = mrl.read(d)
    g = r['mats'][gi]
    w = list(g['words']); w[12] = 0
    return w, g['block'], g['anim'], r


# ---------------------------------------------------------------- conversion

_common = {}


def gu_common(paths):
    """GU's own copies of weapon\\common textures, searched in the GU weapon arcs."""
    want = set(paths) - set(_common)
    if want:
        r = rom()
        for k in sorted(r.files):
            if not want - set(_common): break
            if '/arc/weapon/w' not in k or not re.search(r'/\d{3}\.arc$', k): continue
            for p, th, d in entries(r.read(k)):
                if th == T_TEX and p in want and p not in _common: _common[p] = d
    return {p: _common[p] for p in paths if p in _common}


def convert(nn, src, idx, model=None, log=print):
    pf = PFX[nn]
    n4 = int(re.search(r'pl_%s(\d+)\.arc$' % pf, src).group(1))
    model = n4 if model is None else model
    old = '%03d' % n4; new = '%03d' % model

    def gpath(p):
        if p.startswith('weapon\\common\\'): return p
        assert p.startswith('weapon\\%s\\%s%s\\' % (pf, pf, old)), p
        q = 'weapon\\w%02d\\%s%s\\' % (nn, pf, new) + p.split('\\')[-1].replace(old, new)
        return q

    e4 = [(p, th, d) for p, th, d in entries(open(src, 'rb').read()) if not p.startswith('sound\\')]
    tex4 = {p: d for p, th, d in e4 if th == T_TEX}
    mods = [(p, d) for p, th, d in e4 if th == T_MOD]
    mrls = {p: d for p, th, d in e4 if th == T_MRL}
    other = [(p, th) for p, th, d in e4 if th not in (T_TEX, T_MOD, T_MRL)]
    if other: raise SystemExit('unhandled 4U entries %s' % other)
    own = [p for p in tex4 if '\\common\\' not in p]
    gtex = []
    for p in own:
        img = tex.decode(tex4[p])
        gtex.append((gpath(p), tex.encode_gu(img, 'bc3')))
        a = img[..., 3:4].repeat(4, -1)
        gtex.append((gpath(p) + '+A', tex.encode_gu(np.ascontiguousarray(a), 'bc4')))
    common = sorted({p for d in mrls.values() for th, p in mrl.read(d)['textures'] if th and '\\common\\' in p})
    gc = gu_common(common)
    for p in common:
        if p in gc:
            gtex.append((p, gc[p]))
        else:          # GU dropped this env texture: ship the 4U one (BC3, same path; no GU file to collide with)
            gtex.append((p, tex.encode_gu(tex.decode(tex4[p]), 'bc3')))
            log('  %s: not in GU, converted from 4U' % p)
    allpaths = [p for p, _ in gtex]
    out = [(p, T_TEX, d) for p, d in gtex]
    for mp, md in mods:
        d4 = mrls[mp]
        r4 = mrl.read(d4)
        names = {zlib.crc32(x.encode()) ^ 0xFFFFFFFF: x for x in modlib.parse(md)['material_names']}
        real = [(th, p) for th, p in r4['textures'] if th]
        tpath = []
        for th, p in real:
            tpath.append(gpath(p))
            if gpath(p) + '+A' in allpaths: tpath.append(gpath(p) + '+A')
        ti = lambda p: tpath.index(p) + 1
        mats = []
        for m in r4['mats']:
            if m['name'] not in names:
                log('  material %08x: not used by the MOD, dropped' % m['name']); continue
            t, how = pick_template(idx, d4, m)
            key = 'wpn_%s_%s_%d' % (t['gu'][0].split('/')[-2], t['gu'][0].split('/')[-1][:3], t['gu'][2])
            key += '_' + t['gu'][1].split('\\')[-1]
            mrl_build.TEMPLATES[key] = t['gu'][:2] + (t['gu'][2],)
            gw, gblock, ganim, gm = gu_material(t)
            if ganim: _ANIMATED[key] = (gw, gblock, ganim)
            bad = [p for p in m['params'] if p[1] == 3 and p[2] > len(r4['textures'])]
            if bad: log('  material %08x: params %s are no texture slots (index past the %d textures), ignored'
                        % (m['name'], [(p[0], p[2]) for p in bad], len(r4['textures'])))
            p4 = {p[0]: r4['textures'][p[2] - 1][1] for p in m['params']
                  if p[1] == 3 and 0 < p[2] <= len(r4['textures']) and r4['textures'][p[2] - 1][0]}
            alb = gpath(p4['tAlbedoMap'])
            gs ={p[0]: p[2] for p in gm['mats'][t['gu'][2]]['params'] if p[1] == 3}
            spec_plusA = 'tSpecularMap' in gs and gm['textures'][gs['tSpecularMap'] - 1][1].endswith('+A')
            slots = {'tAlbedoMap': ti(alb), 'tSpecularMap': ti(alb + '+A') if spec_plusA and alb + '+A' in tpath else ti(alb)}
            if 'tSphereMap' in gs:
                if 'tExtendMap' not in p4: raise SystemExit('template %s has a sphere map, 4U material none' % key)
                slots['tSphereMap'] = ti(gpath(p4['tExtendMap']))
            rest = set(gs) - set(slots)
            if rest: log('  warning: template slots %s set to the albedo' % sorted(rest))
            mtype = ((m['words'][6] >> 21) & 0xFF) >> 2
            extra, states = {'mtype': mtype}, ()
            rs = [x for x in m['states'] if x and x.startswith('RSMeshBias')]
            if 'RS state from 4U' in how:
                states, extra['bias'] = (rs[0],), int(rs[0][len('RSMeshBias'):])
            if 'DS+RS states from 4U' in how:
                ds = [x for x in m['states'] if x and x.startswith('DS')]
                r4s = [x for x in m['states'] if x and x.startswith('RSMesh') and not x.startswith('RSMeshC')]
                states = tuple(ds[:1] + r4s[:1])
                extra['bias'] = int(r4s[0][len('RSMeshBias'):]) if r4s and r4s[0].startswith('RSMeshBias') else 0
            an = ''
            if ganim:
                extra['anim'] = ganim
                kinds = {tr['kind'] & 0xF for e in mrl_anim.parse(ganim) for tr in e['tracks']}
                an = ' +GU anim %d B (kinds %s)' % (len(ganim), sorted(kinds))
                if 3 in kinds: log('  warning: copied animation swaps textures (kind 3): template texture indices')
            elif m['words'][12]:
                an = ' (4U anim %d B dropped: no animated template)' % m['words'][12]
            mats.append((names[m['name']], key, slots, states, {}, extra))
            log('  %-40s <- %s %s mat %d [%s] type %d%s' % (names[m['name']], t['gu'][0].split('weapon/')[1],
                t['gu'][1].split('\\')[-1], t['gu'][2], how, mtype, an))
        out.append((gpath(mp), T_MRL, mrl_build.build(rom(), mats, tpath)))
        md2 = normalize_4u(md)
        if md2 is not md:
            log('  %s: mixed vertex streams normalised, %d 0x7BA7401B mesh(es) -> 0xCBF6C01A (colour kept)' % (
                mp, sum(x['fmt'] == mod4u2gu.COLOUR_4U for x in modlib.parse(md)['mesh_list'])))
        gmod = mod4u2gu.convert(md2, vcolour=True, edges=True)
        gmod, changed = drawmodes(gmod, out[-1][2])
        for name in changed: log('  %s: drawMode 0xECF3 (BSAddAlpha + DSZTest + RSMesh material)' % name)
        out.append((gpath(mp), T_MOD, gmod))
    return arcpack.build(out)


# GU drawMode of a visible weapon mesh from its material's GU states (docstring, vote over Capcom's weapon pairs)
ADD_STATES, ADD_DRAWMODE = ('BSAddAlpha', 'DSZTest', 'RSMesh'), 0xECF3


def drawmodes(dmod, dmrl):
    """converted GU MOD + its GU MRL -> (MOD with 0xECF3 on the visible normal meshes whose material has exactly
    the BS / DS / RS states ADD_STATES, [material names changed]). Edge meshes keep drawMode & 0x1020 (= 0x20 for
    0xEFFF and 0xECF3 alike); proxies (0xE4C0) and vertex-colour meshes (already 0xECF3) are left."""
    m = modlib.parse(dmod)
    states = {x['name']: [s for s in x['states'] if s and s[:2] in ('BS', 'DS', 'RS')] for x in mrl.read(dmrl)['mats']}
    out = bytearray(dmod); changed = []
    for i, x in enumerate(m['mesh_list']):
        if x['fmt'] == mod4u2gu.EDGE_FMT or x['drawMode'] != mod4u2gu.GU_DRAW_VISIBLE: continue
        name = m['material_names'][x['material']]
        if sorted(states.get(zlib.crc32(name.encode()) ^ 0xFFFFFFFF, ())) == sorted(ADD_STATES):
            struct.pack_into('<H', out, m['offsets']['meshes'] + 48 * i, ADD_DRAWMODE)
            changed.append(name)
    return bytes(out), changed


def check(path):
    ok = A.check(path)
    ents = entries(open(path, 'rb').read())
    mrls = {p: mrl.read(d) for p, th, d in ents if th == T_MRL}
    for p, th, d in ents:
        if th != T_MOD: continue
        m = modlib.parse(d)
        hs = {zlib.crc32(x.encode()) ^ 0xFFFFFFFF for x in m['material_names']}
        have = {x['name'] for x in mrls.get(p, {'mats': []})['mats']}
        miss = hs - have
        bad = [x for x in m['mesh_list'] if x['fmt'] not in (mod4u2gu.GU_FMT, mod4u2gu.COLOUR_GU, mod4u2gu.EDGE_FMT)
               or x['material'] >= m['materials']]
        dms = collections.Counter('%04x' % x['drawMode'] for x in m['mesh_list'])
        print('  %-44s MOD materials %d, without MRL material %d, odd meshes %d, edge meshes %d, drawModes %s, '
              'bones %s' % (p, len(hs), len(miss), len(bad), sum(x['fmt'] == mod4u2gu.EDGE_FMT for x in m['mesh_list']),
                            dict(sorted(dms.items())), [b['index'] for b in m['bone_list']]))
        ok &= not miss and not bad
    print('OK' if ok else 'PROBLEMS')
    return ok


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'index':
        index(sys.argv[2], sys.argv[3])
    elif cmd == 'convert':
        a = sys.argv[2:]
        mdl = int(a[a.index('--model') + 1]) if '--model' in a else None
        data = convert(int(a[0]), a[1], pickle.load(open(a[3], 'rb')), model=mdl)
        open(a[2], 'wb').write(data)
        print(len(data), 'bytes ->', a[2])
    elif cmd == 'check':
        sys.exit(0 if check(sys.argv[2]) else 1)
