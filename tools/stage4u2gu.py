"""stage4u2gu.py : MH4U stage assets (Battlequarters, m19) -> MHGU stage assets, first "Fortress alias" build.

  stage4u2gu.py mod IN.mod OUT.mod [IN2.mod ...]   convert (and merge) static 4U stage models into one GU model
  stage4u2gu.py check OUT.mod                      decode a converted GU stage model, compare with the sources
  stage4u2gu.py alias [OUTROOT] [--keep-sets] [--keep-filters] [--keep-gimmicks] [--keep-koware] [--keep-sound]
                                                   [--keep-relation] [--keep-doors] [--keep-cart]
                                                   [--keep-static-doors] [--keep-static-cannons] [--keep-items]
                                                   [--keep-camera] [--keep-gate]
                                                   build the alias stage arcs (default monsters/gogmazios/romfs); the --keep-*
                                                   flags fall back to the Fortress data of one session-5 change
                                                   (bisecting aid if the in-game test fails at area load)

Inputs: 4U arcs unpacked in dump/m19_unpacked/<arc>/ (tools/arcpack.py unpack), GU Fortress arcs in
dump/gu_stage/nativeNX/... (MHGU_Editor scratch/py/romfs.py extract). See notes/stage.md "Converters" + section 11.
`alias` builds: area arcs (4U main models, 4U set schedulers + props, Fortress props dropped, 4U light/fog values in
GU's filter schedulers), m28d.arc (4U breakables in the area-2 slots, Fortress area-1 gates hidden, BGM streams when
dump/converted/bgm_m28.json exists), map_com m28.arc (4U collision + area info, Fortress gimmick shells moved:
Dragonator spears, cart path = 4U loop keys for module/stage_cart.c). Report: dump/stage_alias_report.json.

Static stage models (no bones), 4U MOD 0xE6 -> GU MOD 0xD4:
  4U 0x59DC400B 28 B  f32 pos[3], snorm8 N[4], f32 uv[2], u8 rgba
  4U 0x3F78800C 32 B  same + a second u8 rgba (dropped)
  GU 0x207D603B 24 B  IANonSkinBC (AppShaderPackage.mfx): f32 pos[3] @0, Normal @12 = one packed 32-bit
                      R10G10B10A2 unorm (n = v / 511.5 - 1, checked against face normals of m26a02d: |dot| 0.94),
                      f16 uv[2] @16 (v flipped, as for monsters), u8 rgb VertexColor @20, u8 VertexAlpha @23
  meshes: drawMode kept (same values in both games), skinBoneBegin 0, 1 envelope per mesh (4U stage models carry
  the same 144-byte bone-255 envelopes, copied), index values rebased when meshes are renumbered.
Materials: GU template entries + parameter blocks from Fortress MRLs (lit = FLighting family / unlit =
FConstantColor family, by blend state, raster state and 4U name prefix), texture slots repointed.
Textures: 4U ETC1 -> BC1, ETC1A4 -> BC3 (tools/tex.py), 4U paths kept (no clash with Fortress names).
"""
import os, struct, sys, zlib, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
import mod as modlib
import mrl as mrllib
import mrl_anim, mrl_build
import arcpack
import tex as texlib

U4 = os.path.join(ROOT, 'dump', 'm19_unpacked')
U4_MAIN = 'm19'         # u4_find searches this unpacked arc first (the stage-wide 4U arc)
GUX = os.path.join(ROOT, 'dump', 'gu_stage', 'nativeNX')
GUU = os.path.join(ROOT, 'dump', 'gu_stage', 'unpacked')
CACHE = os.path.join(ROOT, 'dump', 'stage_cache')        # converted textures (slow to encode)

T_MOD, T_MRL, T_TEX = 0x58A15856, 0x2749C8A8, 0x241F5DEB
KEEP = set()            # alias --keep-* fallbacks: 'sets', 'filters', 'gimmicks', 'koware'
FMT_4U = {0x59DC400B: 28, 0x3F78800C: 32, 0x82917009: 24}
GU_FMT, GU_STRIDE = 0x207D603B, 24
NORMAL_W = 3            # top 2 bits of the packed normal: 3 on the GU stage vertices (see check)


# ------------------------------------------------------------------ models

def pack_normal(n):
    n = n.astype(np.float64)
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
    q = np.clip(np.round((n / l + 1.0) * 511.5), 0, 1023).astype(np.uint32)
    return (q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20) | (NORMAL_W << 30)).astype('<u4')


def unpack_normal(w):
    w = w.astype(np.int64)
    return np.stack([(w & 0x3FF), (w >> 10) & 0x3FF, (w >> 20) & 0x3FF], 1) / 511.5 - 1.0


def read_mesh_4u(d, m, x):
    st = x['stride']
    assert FMT_4U.get(x['fmt']) == st, ('4U stage vertex format %#x stride %d not handled' % (x['fmt'], st))
    base = m['offsets']['vb'] + x['streamOff'] + x['vertexStart'] * st
    v = np.frombuffer(d[base:base + x['numVertices'] * st], np.uint8).reshape(-1, st)
    pos = np.frombuffer(v[:, 0:12].tobytes(), '<f4').reshape(-1, 3)
    nrm = v[:, 12:15].view(np.int8).astype(np.float64) / 127.0
    uv = np.frombuffer(v[:, 16:24].tobytes(), '<f4').reshape(-1, 2)
    # 0x82917009 (24 B, 4U Heaven's Mount m05a02d -sky00 / -river): the 28-B layout without the colour -> white
    col = v[:, 24:28].copy() if st >= 28 else np.full((len(v), 4), 255, np.uint8)
    return pos, nrm, uv, col


def encode_mesh_gu(pos, nrm, uv, col):
    n = len(pos)
    out = np.zeros((n, GU_STRIDE), np.uint8)
    out[:, 0:12] = pos.astype('<f4').view(np.uint8).reshape(n, 12)
    out[:, 12:16] = pack_normal(nrm).view(np.uint8).reshape(n, 4)
    uvh = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1).astype('<f2')
    out[:, 16:20] = uvh.view(np.uint8).reshape(n, 4)
    out[:, 20:24] = col
    return out


def hidden_4u(col):
    """a 4U stage mesh whose vertex alpha is 0 everywhere draws nothing in 4U (S: 4U's XfB shaders scale by vertex
    alpha), while GU's templates ignore it: dropped. The only one in m05 / m08 / m19 (C, scan 2026-10-28): m05a03d's
    XfBAW_1__m00_52, 31 vertices, unlit rock00 over a 6700 x 2900 x 6300 span (a flat fogged sheet in area 3, test
    2026-10-28)."""
    return not col[:, 3].any()


def convert_models(sources):
    """sources: [(4U MOD bytes, material-name suffix)] -> (GU MOD bytes, [(new material name, src index, old name)]).
    Several 4U models are merged into one GU model (meshes concatenated, materials renamed per source)."""
    vb = bytearray(); ib = bytearray(); meshes = []; envs = []; mats = []; groups = None
    vcount = 0; icount = 0; edges = 0
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    meta = None
    for si, (d, suffix) in enumerate(sources):
        m = modlib.parse(d)
        assert m['version'] == 0xE6 and m['bones'] == 0, 'static 4U stage models only'
        meta = meta or m['metadata']
        if groups is None:
            groups = d[m['offsets']['groups']:m['offsets']['groups'] + 32 * m['groups']]
            ngroups = m['groups']
        mat_base = len(mats)
        for k, nm in enumerate(m['material_names']):
            new = (nm + suffix)[:127]
            mats.append((new, si, nm))
        src_ib = np.frombuffer(m['ib'], '<u2')
        if len(src_ib) < m['indices']:
            src_ib = np.concatenate([src_ib, np.full(m['indices'] - len(src_ib), src_ib[-1], np.uint16)])
        eo = m['envelopes_off']
        for mi, x in enumerate(m['mesh_list']):
            pos, nrm, uv, col = read_mesh_4u(d, m, x)
            if hidden_4u(col): continue
            lo = np.minimum(lo, pos.min(0)); hi = np.maximum(hi, pos.max(0))
            vb += encode_mesh_gu(pos, nrm, uv, col).tobytes()
            idx = src_ib[x['indexStart']:x['indexStart'] + x['numIndices']].astype(np.int64)
            live = idx != 0xFFFF
            # 4U index values: vertexStart-based (checked: all indices of a mesh lie in [vs, vs + n))
            if live.any():
                lo_i, hi_i = idx[live].min(), idx[live].max()
                assert x['vertexStart'] <= lo_i and hi_i < x['vertexStart'] + x['numVertices'], \
                    ('index range', mi, lo_i, hi_i, x['vertexStart'], x['numVertices'])
            idx[live] += vcount - x['vertexStart']
            assert idx[live].max(initial=0) < 0xFFFF
            new_is = icount
            ib += idx.astype('<u2').tobytes()
            icount += len(idx)
            # GU ends EVERY mesh with one 0xFFFF restart (m26a00d / m26a02d: gap 1 after all meshes, value 0xffff)
            # and its draw reads it: without it the strip ran on into the next mesh's first index = one triangle
            # per mesh stretched to that vertex (test-5 black / distorted triangles, 83 in a00, 56 in a02)
            ib += struct.pack('<H', 0xFFFF); icount += 1
            env = bytearray(d[eo + 144 * mi: eo + 144 * (mi + 1)])
            env[4:16] = b'\0' * 12
            envs.append(bytes(env))
            d0 = x['group'] | ((x['material'] + mat_base) << 12) | (x['lod'] << 24)
            d1 = (1 | (x['shape'] << 1) | (x['sort'] << 2) | (x['alpha'] << 8) | (GU_STRIDE << 16) |
                  (x['prim'] << 24) | (x['binflip'] << 30))
            meshes.append(struct.pack('<HHIIIIIIIIBBHHHI', x['drawMode'], x['numVertices'], d0, d1,
                                      vcount, 0, GU_FMT, new_is, x['numIndices'], 0, 0, 1, len(meshes) + 1,
                                      vcount, vcount + x['numVertices'] - 1, 0))
            vcount += x['numVertices']
        edges += m['edges']
    assert vcount < 0xFFFF, 'too many vertices for 16-bit indices'
    names = b''.join(struct.pack('<128s', n.encode('ascii')) for n, _, _ in mats)
    c = (lo + hi) / 2
    r = float(np.linalg.norm(hi - lo) / 2)
    o_g = 0x84
    o_m = o_g + len(groups)
    o_me = o_m + len(names)
    o_env = o_me + 48 * len(meshes)
    o_vb = o_env + 144 * len(envs)
    o_ib = o_vb + len(vb)
    end = o_ib + len(ib)
    hdr = struct.pack('<4shHHHIII', b'MOD\0', 0xD4, 0, len(meshes), len(mats), vcount, icount, edges)
    hdr += struct.pack('<10I', len(vb), 0, ngroups, 0, o_g, o_m, o_me, o_vb, o_ib, end)
    hdr += struct.pack('<4f8f', c[0], c[1], c[2], r, lo[0], lo[1], lo[2], 0.0, hi[0], hi[1], hi[2], 0.0)
    mid, low, light, bj = meta
    hdr += struct.pack('<3IB3xI', mid, low, light | 0x80000000, bj, len(envs))
    assert len(hdr) == 0x84
    out = hdr + groups + names + b''.join(meshes) + b''.join(envs) + bytes(vb) + bytes(ib)
    assert len(out) == end
    return out + b'\0' * 4, mats


def check_model(dg, sources):
    """decode our GU model and compare positions / normals / uvs / index topology with the 4U sources."""
    mg = modlib.parse(dg)
    worst = dict(pos=0.0, nrm=0.0, uv=0.0); k = 0
    ibg = np.frombuffer(mg['ib'], '<u2')
    for d in sources:
        m = modlib.parse(d)
        ib4 = np.frombuffer(m['ib'], '<u2')
        for x in m['mesh_list']:
            pos, nrm, uv, col = read_mesh_4u(d, m, x)
            if hidden_4u(col): continue
            xg = mg['mesh_list'][k]; k += 1
            b = mg['offsets']['vb'] + xg['vertexStart'] * GU_STRIDE
            v = np.frombuffer(dg[b:b + xg['numVertices'] * GU_STRIDE], np.uint8).reshape(-1, GU_STRIDE)
            p = np.frombuffer(v[:, 0:12].tobytes(), '<f4').reshape(-1, 3)
            n = unpack_normal(np.frombuffer(v[:, 12:16].tobytes(), '<u4'))
            t = np.frombuffer(v[:, 16:20].tobytes(), '<f2').reshape(-1, 2).astype(float)
            nn = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
            worst['pos'] = max(worst['pos'], float(np.abs(p - pos).max()))
            worst['nrm'] = max(worst['nrm'], float(np.abs(n - nn).max()))
            ref = np.stack([uv[:, 0], 1 - uv[:, 1]], 1)
            worst['uv'] = max(worst['uv'], float((np.abs(t - ref) / np.maximum(1, np.abs(ref))).max()))
            a = ib4[x['indexStart']:x['indexStart'] + x['numIndices']].astype(int)
            g = ibg[xg['indexStart']:xg['indexStart'] + xg['numIndices']].astype(int)
            a = np.where(a == 0xFFFF, -1, a - x['vertexStart']); g = np.where(g == 0xFFFF, -1, g - xg['vertexStart'])
            assert (a == g).all(), 'index mismatch mesh %d' % k
    print('meshes %d | max err pos %.3g normal %.3g uv(rel) %.3g | topology identical' %
          (k, worst['pos'], worst['nrm'], worst['uv']))


# ------------------------------------------------------------------ materials

_TPL = None


def gu_templates():
    """[(key, entry words, block, anim, name)] from the Fortress area-2 / area-1 MRLs."""
    global _TPL
    if _TPL is None:
        _TPL = []
        for a, n in (('a02', 'm26a02d'), ('a01', 'm26a01d')):
            base = os.path.join(GUU, a, 'stage', 'm26d', n, n)
            d = open(base + '.2749c8a8', 'rb').read()
            gm = modlib.parse(open(base + '.58a15856', 'rb').read())
            names = {mrllib.name_hash(x): x for x in gm['material_names']}
            # only materials whose meshes are all IANonSkinBC (the shader input layout must match our vertices)
            fmts = {}
            for x in gm['mesh_list']:
                fmts.setdefault(gm['material_names'][x['material']], set()).add(x['fmt'])
            moff = struct.unpack_from('<I', d, 24)[0]
            for i, mt in enumerate(mrllib.read(d)['mats']):
                if fmts.get(names.get(mt['name'])) != {GU_FMT}: continue
                w = list(struct.unpack_from('<15I', d, moff + 60 * i))
                lit = any(p[0] == 'FLighting' for p in mt['params'])
                st = [s for s in mt['states'] if s]
                _TPL.append(dict(blend=st[0], rs=st[2], lit=lit, w=w, block=d[w[13]:w[13] + w[2]],
                                 anim=d[w[14]:w[14] + w[12]] if w[12] else b'', name=names.get(w[1], ''),
                                 src='%s#%d' % (n, i)))
    return _TPL


def pick_template(blend, rs, lit, name4, at=False):
    """Fortress template closest to a 4U material. Every Fortress IANonSkinBC template selects the same UV features
    (FUVTransformPrimary = FUVTransformOffset, ...: checked on all of them), so animated templates qualify too (their
    anim block is replaced). The opaque / blended class decides (w7 top bits = draw pass: GU 0x8c opaque, 0x8d
    alpha-tested, 0x8f / 0x91 blended); the states themselves are set from the 4U material in build_mrl."""
    pre = name4.split('__')[0][:5]           # 'XfB_W' / 'XfBAW'
    best = None
    for t in gu_templates():
        t_at = t['blend'] == 'BSSolid' and bool(t['w'][7] & mrl_build.W7_ALPHATEST)
        s = (4 * ((t['blend'] == 'BSSolid') == (blend == 'BSSolid')) + 2 * (t['lit'] == lit) + 1.5 * (t_at == at) +
             1 * (t['blend'] == blend) + 0.5 * (t['rs'] == rs) + 0.25 * (t['name'][:5] == pre) -
             0.01 * len(t['block']) / 1000)
        if best is None or s > best[0]: best = (s, t)
    return best[1]


GU_STATES = {a for a, _ in mrllib.records(0x22).values()}
W7_KEEP_4U = 0xFFF00                         # w7 bits 8-15 alpha-test ref, 16-19 depth bias (mrl_build.W7_*)


def gu_state(name):
    """4U state record -> GU record name (None = keep the template's). GU has no RSMeshCNBiasN (4U a00 813e69ea,
    a01 kusa00): cull-none wins (the cards and one-sided camp walls vanish from behind otherwise); the 4U depth-bias
    nibble still goes into w7."""
    if name in GU_STATES: return name
    if name.startswith('RSMeshCNBias'): return 'RSMeshCN'
    return None


def build_mrl(mats, mrl4_by_src):
    """mats: [(new name, src index, 4U name)]; mrl4_by_src[src] = 4U MRL bytes.
    Returns (GU MRL bytes, [4U texture paths used], report rows).
    Per material: a Fortress template entry + block (pick_template), tAlbedoMap repointed, then the 4U material's own
    blend / depth / raster states, its w7 alpha test (BSSolid bit 24, ref 128 on the 4U 'XfBAW_1/3' cards: grass,
    leaves, ropes, torch stands) and depth-bias nibble, and its animations converted (mrl_anim.gu_entries: UV scroll /
    flipbook of the torch fire, water, sky and clouds; 4U loop + autoplay flags kept)."""
    textures = []; entries = []; blocks = []; anims = []; rows = []
    parsed = {s: mrllib.read(b) for s, b in mrl4_by_src.items()}
    anims4 = {s: mrl_anim.material_anims(b)[1] for s, b in mrl4_by_src.items()}
    for new, si, old in mats:
        r4 = parsed[si]
        m4 = [x for x in r4['mats'] if x['name'] == mrllib.name_hash(old)]
        assert m4, 'material %s not in its 4U MRL' % old
        m4 = m4[0]
        st = [s for s in m4['states'] if s]
        w4 = m4['words']
        # 4U lit flag = w6 bit 31: clear only on the 14 sky / cloud / distant forest / effect-card materials of m19
        # (every opaque 4U stage material lists tLutShininess, sky included; GU's sky is FConstantColor = unlit)
        lit = bool(w4[6] >> 31)
        at = st[0] == 'BSSolid' and bool(w4[7] & mrl_build.W7_ALPHATEST)
        albedo = [p[2] for p in m4['params'] if p[0] == 'tAlbedoMap']
        tpath = r4['textures'][albedo[0] - 1][1] if albedo and albedo[0] else None
        t = pick_template(st[0], st[2], lit, old, at)
        if tpath and tpath not in textures: textures.append(tpath)
        tidx = textures.index(tpath) + 1 if tpath else 0
        block = bytearray(t['block']); w = list(t['w'])
        cb_words = {}
        for k in range(w[6] & 0xFFF):
            a, val, word = struct.unpack_from('<III', block, 12 * k)
            if a & 0xF == 3:
                slot = mrllib.rec_name(0x22, word)
                struct.pack_into('<I', block, 12 * k + 4, tidx if slot == 'tAlbedoMap' else 0)
            elif a & 0xF == 1:
                cb_words[mrllib.rec_name(0x22, word)] = word
        set_st = []
        for s4 in st[:3]:                    # BS*, DS*, RS* of the 4U material
            g = gu_state(s4)
            if g:
                mrl_build.set_state(w, g); set_st.append(g)
        w[7] = (w[7] & ~W7_KEEP_4U) | (w4[7] & W7_KEEP_4U)
        if t['blend'] == 'BSSolid':          # bit 24 = alpha test only on BSSolid (GU blended templates set it)
            w[7] = (w[7] | mrl_build.W7_ALPHATEST) if at else (w[7] & ~mrl_build.W7_ALPHATEST)
        anim = b''
        e4 = anims4[si].get(m4['name'], [])
        if e4:
            ge = mrl_anim.gu_entries(e4, cb_words)
            for g, e in zip(ge, e4): g['flags'] |= e['flags'] & mrl_anim.FLAG_AUTOPLAY
            anim = mrl_anim.build(ge)
        w[1] = mrllib.name_hash(new)
        entries.append(w); blocks.append(bytes(block)); anims.append(anim)
        rows.append((new, st[0], st[2], 'lit' if lit else 'unlit', t['src'], t['name'], tpath,
                     '/'.join(set_st), 'w7 %08x' % w[7], '%d anims' % len(e4)))
    tex_off = 0x1C
    mat_off = tex_off + 76 * len(textures)
    blk = mat_off + 60 * len(entries)
    for w, b in zip(entries, blocks):
        w[13] = blk; w[12] = w[14] = 0; blk += len(b)
    tail = bytearray()                       # animation blocks after the parameter blocks, 16-byte aligned (as GU)
    for w, a in zip(entries, anims):
        if not a: continue
        tail += b'\0' * (-(blk + len(tail)) % 16)
        w[12], w[14] = len(a), blk + len(tail)
        tail += a
    out_e = [struct.pack('<15I', *w) for w in entries]
    hdr = struct.pack('<4s6I', b'MRL\0', 0x22, len(entries), len(textures), 0xB2D34C60, tex_off, mat_off)
    tt = b''.join(struct.pack('<3I64s', T_TEX, 0, 0, p.encode('ascii')) for p in textures)
    return hdr + tt + b''.join(out_e) + b''.join(blocks) + bytes(tail), textures, rows


# ------------------------------------------------------------------ textures

_TEX4 = None


def tex4_index():
    global _TEX4
    if _TEX4 is None:
        _TEX4 = {}
        for arc in sorted(os.listdir(U4)):
            for dp, _, fs in os.walk(os.path.join(U4, arc)):
                for f in fs:
                    if f.endswith('.241f5deb'):
                        rel = os.path.relpath(os.path.join(dp, f), os.path.join(U4, arc))[:-9].replace('/', '\\')
                        _TEX4.setdefault(rel, os.path.join(dp, f))
    return _TEX4


def convert_texture(path4):
    """4U texture (by arc path) -> GU TEX bytes, cached in dump/stage_cache."""
    os.makedirs(CACHE, exist_ok=True)
    key = os.path.join(CACHE, zlib.crc32(path4.encode()).__format__('08x') + '.tex')
    if os.path.exists(key): return open(key, 'rb').read()
    src = open(tex4_index()[path4], 'rb').read()
    h = texlib.parse(src)
    img = texlib.decode_3ds(h, 0)
    fmt = 'bc3' if h['fmt'] == 0x0C else 'bc1'
    out = texlib.encode_gu(img, fmt)
    open(key, 'wb').write(out)
    return out


# ------------------------------------------------------------------ alias build

def u4(arc, path, typ):
    return open(os.path.join(U4, arc, path.replace('\\', '/') + '.%08x' % typ), 'rb').read()


# GU model path (Fortress name, inside the GU arc) <- 4U models merged into it [(arc, path)]
ALIAS_MODELS = {
    'a00': ('stage\\m26d\\m26a00d\\m26a00d', [('m19a00', 'stage\\m19d\\m19a00d\\m19a00d')]),
    'a01': ('stage\\m26d\\m26a01d\\m26a01d', [('m19a01', 'stage\\m19d\\m19a01d\\m19a01d'),
                                              ('m19a01', 'stage\\m19d\\m19a01d\\m19a01d-sky00')]),
    # c00..c03 are drawn by the converted 4U set scheduler m19a03d-a02 (ALIAS_SETS); sky00 by 4U's filter scheduler
    # m19a03d-f, whose structure is not converted (GU's Fortress "-f" is kept) -> merged here, at mPos 0 as in 4U.
    # c04 (also in 4U's -f) is a camera-checked uStageSet -> FILTER_SETS, not merged.
    'a02': ('stage\\m26d\\m26a02d\\m26a02d', [('m19a03', 'stage\\m19d\\m19a03d\\m19a03d'),
                                              ('m19a03', 'stage\\m19d\\m19a03d\\m19a03d-sky00')]),
}

# GU area set scheduler "-a00" (draws the area's props) <- the 4U scheduler drawing the same area's props, converted
# with tools/sdl.py; its models are converted one by one and shipped under their 4U paths (the scheduler resolves its
# resource references by path among the arc's earlier entries); the Fortress props it drew are dropped.
ALIAS_SETS = {
    'a00': ('stage\\m26d\\m26a00d\\sdl\\m26a00d-a00', 'stage\\m19d\\m19a00d\\sdl\\m19a00d-a00'),
    'a01': ('stage\\m26d\\m26a01d\\sdl\\m26a01d-a00', 'stage\\m19d\\m19a01d\\sdl\\m19a01d-a00'),
    'a02': ('stage\\m26d\\m26a02d\\sdl\\m26a02d-a00', 'stage\\m19d\\m19a03d\\sdl\\m19a03d-a02'),
}
T_SDL = 0x4c0db839
USTAGESET = 0x2516a76b
# uStageSets of the 4U filter scheduler "-f" (GU's "-f" keeps Fortress's structure) -> appended to the area set
# scheduler with all their 4U tracks. Arena c04 (sky cards, cliffs and wall tops above the arena): mCameraCheck 1,
# distance 6000 / cylinder height 1300 around (0, 0, 0) = hidden while the camera is low inside the arena (GU
# 0x51b21c: the camera check fades the set out, 0x51b4d0 = inside test). Merged into the main model (always drawn)
# until test 5: the black triangles in the arena sky.
FILTER_SETS = {'a02': ['c04']}
# GU camera-checked sets / kowareModels all carry mDrawMode 13 (m26a02d-a00 c00, m26a01d-k01..k03, m26a02d-k01/k02);
# 4U's carry 5 (or 1) -> 5 becomes 13 (bit 3 added) on camera-checked uStageSets.
DRAWMODE_CAMCHECK = {5: 13}
# 4U arena KowareObj models that GU cannot run (scheduler m19a03d-a01, KowareObj mType 0 / mId 3, one action Id 0
# frames 0..200: side doors a02 / a03 swing (mRot y +-0.05..), wall a04 sinks 360; the kod table has no free area-2
# slot and nothing in GU sends the action) -> drawn STATIC in their frame-0 pose as extra uStageSet objects of the
# area set scheduler (clones of c00: same draw/camera settings). Their frame-0 rotations are 0, so mPos is exact. The
# 4U collision keeps a04's thin wall parts (z -4710), which now has its model. NOT added: the gate m19a03d-a00/a01
# (scheduler a00, mType 22, frame-0 mRot x -1.134 rad: a uStageSet has no rotation track), the lever (s01 -> model
# s03, mType 24) and s02 (model s04, mType 25): their poses are relative / unclear; the cart s00 stays GU's st006.
# The cannons s03 / s04 (models s05..s10, frame-0 rotation 0, absolute offsets) are added. `--keep-doors` = none.
# arena-4: the doors / wall are now a real GU KowareObj (DOORS_KOWARE below); their static clones only come back with
# `--keep-static-doors` (old arena-2 behaviour, no kobj). Same for the floor cannons (CANNONS_KOWARE) with
# `--keep-static-cannons`.
STATIC_DOORS = [('a02', 'stage\\m19d\\m19a03d\\m19a03d-a02', (-3555.0, 0.0, -1490.0)),
                ('a03', 'stage\\m19d\\m19a03d\\m19a03d-a03', (3510.0, 0.0, -620.0)),
                ('a04', 'stage\\m19d\\m19a03d\\m19a03d-a04', (700.0, 0.0, -4745.0))]
# cannons s03 / s04 (KowareObj mType 23, actions 51..55): frame-0 pose of their 3 parts
STATIC_CANNONS = [('s05', 'stage\\m19d\\m19a03d\\m19a03d-s05', (1975.0, 0.0, 1230.0)),
                  ('s06', 'stage\\m19d\\m19a03d\\m19a03d-s06', (2045.0, 0.0, 1230.0)),
                  ('s07', 'stage\\m19d\\m19a03d\\m19a03d-s07', (2050.0, 0.0, 1230.0)),
                  ('s08', 'stage\\m19d\\m19a03d\\m19a03d-s08', (-1500.0, 0.0, 1230.0)),
                  ('s09', 'stage\\m19d\\m19a03d\\m19a03d-s09', (-1570.0, 0.0, 1230.0)),
                  ('s10', 'stage\\m19d\\m19a03d\\m19a03d-s10', (-1575.0, 0.0, 1230.0))]
STATIC_KOWARE = {'a02': []}
EFFECT_CTRL = 0x5a17f498      # 4U "Effect" / "MhEffect" scheduler controller: no GU scheduler uses this class


def sdl_drop_ctrl(cls, name):
    return cls == EFFECT_CTRL


# GU filter / light scheduler "-f" <- 4U values (structure, GU-only objects (PL player lights, AmbientLight,
# StableShadow, MhFilter_top...) and GU-only tracks stay GU's; only same-class objects and same-name tracks are
# copied). Bloom thresholds / tone tracks are NOT copied (GU's HDR pipeline differs: G).
ALIAS_FILTERS = {'a00': 'stage\\m19d\\m19a00d\\sdl\\m19a00d-f', 'a01': 'stage\\m19d\\m19a01d\\sdl\\m19a01d-f',
                 'a02': 'stage\\m19d\\m19a03d\\sdl\\m19a03d-f'}
FILTER_MAP = [  # (GU object names, 4U object name, tracks)
    (('EM01-InfiniteLight', 'DEF01-InfiniteLight'), 'base01-InfiniteLight', ('mColor', 'mDir', 'mBalance')),
    (('EM03-HemiSphereLight', 'DEF03-HemiSphereLight'), 'base01-HemiSphereLight', ('mColor', 'mDir', 'mRevColor')),
    (('s2-InfiniteLight',), 's2-InfiniteLight', ('Draw', 'mColor', 'mDir', 'mBalance')),
    (('ColorFog',), 'ColorFog', ('Draw', 'mColor', 'mDensity', 'mStart', 'mEnd')),
    (('MhFilter',), 'MhFilter', ('Draw', 'Top Front', 'Top Back', 'Top Near', 'Top Far', 'Btm Front', 'Btm Back',
                                 'Btm Near', 'Btm Far')),
]


def port_filter(gu, u4d):
    import sdl
    g = sdl.parse(gu); u = sdl.parse(u4d)
    go = {n: (c, tr) for i, n, c, tr in sdl.objects(g)}
    uo = {n: (c, tr) for i, n, c, tr in sdl.objects(u)}
    done = []
    for gns, un, tracks in FILTER_MAP:
        gn = [n for n in gns if n in go]
        if not gn or un not in uo: continue
        gc, gt = go[gn[0]]; uc, ut = uo[un]
        assert gc == uc, (gn, un, hex(gc), hex(uc))
        for k in tracks:
            if k in gt and k in ut and gt[k]['kind'] == sdl.KIND_4U_TO_GU[ut[k]['kind']]:
                sdl.set_values(g, gt[k], sdl.values(u, ut[k]), times=ut[k]['times'])
                done.append('%s.%s' % (gn[0], k))
    if 'MhFilter' in uo and sdl.values(u, uo['MhFilter'][1]['Draw']) == [0] and 'MhFilter_top' in go:
        t = go['MhFilter_top'][1]['Draw']                     # 4U draws no gradient filter at all here
        sdl.set_values(g, t, [0] * len(t['times'])); done.append('MhFilter_top.Draw=0')
    return sdl.build(g), done


_U4IDX = None


def set_source(u4dir, main):
    """use another 4U stage (its arcs unpacked in u4dir/<arc>/, main = the stage-wide arc) for u4_find /
    convert_texture (monsters/dalamadur/tools/build_speartip.py: dump/m08_unpacked, 'm08')"""
    global U4, U4_MAIN, _U4IDX, _TEX4
    U4, U4_MAIN, _U4IDX, _TEX4 = u4dir, main, None, None


def u4_find(path, typ):
    """bytes of a 4U resource by arc path + type, searched over the unpacked stage arcs (U4_MAIN first)."""
    global _U4IDX
    if _U4IDX is None:
        _U4IDX = {}
        for arc in [U4_MAIN] + sorted(a for a in os.listdir(U4) if a != U4_MAIN):
            for dp, _, fs in os.walk(os.path.join(U4, arc)):
                for f in fs:
                    if '.' not in f or f.startswith('_'): continue
                    rel, ext = f.rsplit('.', 1)
                    key = (os.path.relpath(os.path.join(dp, rel), os.path.join(U4, arc)).replace('/', '\\'), ext)
                    _U4IDX.setdefault(key, os.path.join(dp, f))
    return open(_U4IDX[(path, '%08x' % typ)], 'rb').read()


def convert_prop(path4):
    """one static 4U model -> (GU MOD, GU MRL, [4U texture paths], material report rows)."""
    d = u4_find(path4, T_MOD)
    gmod, mats = convert_models([(d, '')])
    check_model(gmod, [d])
    gmrl, texs, rows = build_mrl(mats, {0: u4_find(path4, T_MRL)})
    return gmod, gmrl, texs, rows


def mrl_textures(d):
    return [p for th, p in mrllib.read(d)['textures'] if th == T_TEX and p]


def build_area(area, report):
    import sdl
    ver, ents = arcpack.read(open(os.path.join(GUX, 'arc', 'stage', 'm26d', area + '.arc'), 'rb').read())
    if area not in ALIAS_MODELS:
        return ents
    gpath, srcs = ALIAS_MODELS[area]
    if area == 'a02' and 'sets' in KEEP:        # Fortress set scheduler kept -> 4U c00..c03 merged (session-4 build)
        srcs = srcs + [('m19a03', 'stage\\m19d\\m19a03d\\m19a03d-c%02d' % k) for k in range(4)]
    mods = [u4(a, p, T_MOD) for a, p in srcs]
    mrls = {i: u4(a, p, T_MRL) for i, (a, p) in enumerate(srcs)}
    suffixes = ['' if i == 0 else '_%d' % i for i in range(len(srcs))]
    gmod, mats = convert_models(list(zip(mods, suffixes)))
    check_model(gmod, mods)
    gmrl, texs, rows = build_mrl(mats, mrls)
    report[area] = dict(model=gpath, sources=[p for _, p in srcs], meshes=modlib.parse(gmod)['meshes'],
                        materials=rows, textures=texs)
    replaced = {gpath}                          # GU model paths whose MOD + MRL leave the arc
    new_models = [(gpath, gmrl, gmod)]
    new_sdl = None
    if area in ALIAS_SETS and 'sets' not in KEEP:
        gsdl, usdl = ALIAS_SETS[area]
        old = [e for e in ents if e[0] == gsdl and e[1] == T_SDL][0][2]
        replaced |= set(sdl.resource_paths(sdl.parse(old)))          # the Fortress props it drew
        # drop_keyless: camp torch billboards a10-00 / a10-01 carry keyless mScale (+ mAngle): GU never has those
        new_sdl = sdl.convert_4u(u4_find(usdl, T_SDL), drop_ctrl=sdl_drop_ctrl, drop_keyless=True)
        ns = sdl.parse(new_sdl)
        added = []
        if area in FILTER_SETS and 'filters' not in KEEP:
            tpl = [i for i, n, c, tr in sdl.objects(ns) if c == USTAGESET][0]
            fs = sdl.parse(sdl.convert_4u(u4_find(ALIAS_FILTERS[area], T_SDL), drop_ctrl=sdl_drop_ctrl))
            for i, n, c, tr in sdl.objects(fs):
                if c != USTAGESET or n not in FILTER_SETS[area]: continue
                k = sdl.clone_object(ns, tpl, n, sdl.values(fs, tr['mpModel'])[0])
                ktr = [x for x in sdl.objects(ns) if x[0] == k][0][3]
                assert set(ktr) == set(tr), (n, set(ktr) ^ set(tr))
                for name, e in tr.items():
                    if name == 'mpModel': continue
                    assert ktr[name]['kind'] == e['kind'], (n, name)
                    sdl.set_values(ns, ktr[name], sdl.values(fs, e), times=e['times'])
                added.append(n)
            assert added == FILTER_SETS[area], added
        for i, n, c, tr in sdl.objects(ns):
            if c == USTAGESET and 'mCameraCheck' in tr and 'mDrawMode' in tr and sdl.values(ns, tr['mCameraCheck'])[0]:
                sdl.set_values(ns, tr['mDrawMode'], [DRAWMODE_CAMCHECK.get(v, v) for v in sdl.values(ns, tr['mDrawMode'])])
        new_sdl = sdl.build(ns)
        report[area]['filter_sets'] = added
        if area in STATIC_KOWARE and 'doors' not in KEEP:
            ns = sdl.parse(new_sdl)
            tpl = [i for i, n, c, tr in sdl.objects(ns) if c == 0x2516a76b][0]       # a uStageSet (c00)
            statics = (STATIC_KOWARE[area] + (STATIC_DOORS if 'static-doors' in KEEP else [])
                       + (STATIC_CANNONS if 'static-cannons' in KEEP else []))
            for name, model, pos in statics:
                k = sdl.clone_object(ns, tpl, name, model, pos)
                for e in ns['ents'][k + 1:]:            # no camera fade around c00's check point
                    if e['name'] in ('mCameraCheck', 'mCheckCylinderUse') and e['times'] is not None:
                        sdl.set_values(ns, e, [0] * len(e['times']))
            new_sdl = sdl.build(ns)
            report[area]['static_koware'] = [x[0] for x in statics]
        props = sdl.resource_paths(sdl.parse(new_sdl))
        for p in props:
            pm, pr, pt, prow = convert_prop(p)
            new_models.append((p, pr, pm))
            texs += [t for t in pt if t not in texs]
        report[area]['set_scheduler'] = dict(gu=gsdl, source=usdl, props=props,
                                             dropped_fortress_props=sorted(replaced - {gpath}))
    # textures used only by the replaced Fortress MRLs are dropped
    keep = set(); old_tex = set()
    for p, t, d in ents:
        if t == T_MRL:
            (old_tex if p in replaced else keep).update(mrl_textures(d))
    drop = old_tex - keep
    first_tex = min(k for k, e in enumerate(ents) if e[1] == T_TEX)    # GU puts the filter scheduler "-f" first
    out = list(ents[:first_tex]) + [(p, T_TEX, convert_texture(p)) for p in texs]
    for p, t, d in ents[first_tex:]:
        if t == T_TEX and (p in drop or p in texs): continue
        if p in replaced and t in (T_MOD, T_MRL): continue
        if new_sdl is not None and p == gsdl and t == T_SDL: continue
        out.append((p, t, d))
    # TEX -> MRL -> MOD order (a model fetches its MRL by path while loading), the set scheduler after its models
    i = max(k for k, e in enumerate(out) if e[1] == T_TEX) + 1
    ins = []
    for p, r, m in new_models:
        ins += [(p, T_MRL, r), (p, T_MOD, m)]
    if new_sdl is not None:
        ins.append((gsdl, T_SDL, new_sdl))
    out[i:i] = ins
    if area in ALIAS_FILTERS and 'filters' not in KEEP:
        fpath = 'stage\\m26d\\m26%sd\\sdl\\m26%sd-f' % (area, area)
        k = [j for j, e in enumerate(out) if e[0] == fpath and e[1] == T_SDL][0]
        d, done = port_filter(out[k][2], u4_find(ALIAS_FILTERS[area], T_SDL))
        out[k] = (fpath, T_SDL, d)
        report[area]['filter'] = dict(source=ALIAS_FILTERS[area], ported=done)
    report[area]['dropped_fortress_textures'] = len(drop)
    out, snd = area_sound(area, out)
    if snd: report[area]['sound'] = snd
    return out


# Area sound (sound agent, tools/snd_area.py convert -> AREA_SND_JSON, one entry per arc): a00 / a01 lose the Fortress
# area SE (waves 0x79c47b59 under sound\se\map\m26d\m26a0Kd\, bank 0x15d782fb, request 0x1bcc4966, call 0x2543b93e
# sound\call\map\m26d\m26a0Kd) and get the converted 4U m19a00d / m19a01d files under the same paths, in the listed
# order (waves -> bank -> request -> call), at the place of the first removed entry; a02 swaps only the call (GU's a02
# bank + request are Capcom's own conversion of 4U m19a03d and the gimmick code uses their IDs).
AREA_SND_JSON = os.path.join(ROOT, 'dump', 'converted', 'area_snd.json')
T_SND = (0x79c47b59, 0x15d782fb, 0x1bcc4966, 0x2543b93e)


def area_sound(area, ents):
    if not os.path.exists(AREA_SND_JSON) or 'sound' in KEEP:
        return ents, None
    spec = [e for e in json.load(open(AREA_SND_JSON)) if os.path.basename(e['arc']) == area + '.arc']
    if not spec:
        return ents, None
    adds = [(a['path'], int(a['type'], 16), open(os.path.join(ROOT, a['file']), 'rb').read())
            for a in spec[0]['add_in_order']]
    mine = ('sound\\se\\map\\m26d\\m26%sd\\' % area, 'sound\\call\\map\\m26d\\m26%sd' % area)
    if [int(t.split()[0], 16) for t in spec[0]['remove_types']] == [0x2543b93e]:      # call only
        (cp, ct, cd), = adds
        k = [i for i, e in enumerate(ents) if e[0] == cp and e[1] == ct]
        assert len(k) == 1, (area, cp)
        ents = list(ents); ents[k[0]] = (cp, ct, cd)
        return ents, 'call %s replaced (%d B)' % (cp, len(cd))
    drop = [i for i, (p, t, d) in enumerate(ents) if t in T_SND and p.startswith(mine)]
    assert drop, (area, 'no Fortress area sound entries')
    out = [e for i, e in enumerate(ents) if i not in set(drop)]
    at = drop[0]
    out[at:at] = adds
    return out, 'Fortress area SE (%d entries) -> 4U %s (%d entries)' % (len(drop), spec[0].get('source_4u'), len(adds))


# ------------------------------------------------------------------ collision (map_com)

T_SBC = 0x51fc779f
# GU alias area (Fortress name) <- 4U Battlequarters area. Per area GU loads 5 SBC kinds (file-ID bases 0xa229 g00,
# 0xa395 w00, 0xa501 / 0xa66d shells, 0xa7d9 cam). A missing 4U kind: shell <- the main file of the same family
# (m19a00d has no shells), cam -> the Fortress one is kept (m19a00d has none; GU's camp cam is a flat 20000 plane).
ALIAS_COLLISION = {'m26a00d': 'm19a00d', 'm26a01d': 'm19a01d', 'm26a02d': 'm19a03d'}
SBC_KINDS = ('-a-g00', '-a-w00', '-a-g00-shell', '-a-w00-shell', '-a-cam')


def collision_4u(area4, kind):
    base = os.path.join(U4, 'm19', 'stage', 'm19d', area4, 'collision', area4)
    for k in (kind, kind.replace('-shell', '')):
        p = base + k + '.%08x' % T_SBC
        if os.path.exists(p):
            return k, open(p, 'rb').read()
    return None, None


# ------------------------------------------------------------------ area info (SIS, same format in both games)
# 4U topology: camp 0 <-> 1, 0 <-> 3; 1 <-> 2, 1 <-> 3; 2 <-> 3 (arena = 3). The alias has 0, 1, 2 (= 4U 3): 4U area 2
# is dropped, its two passages become a second (variant 1) link a01 <-> a02, the way Fortress links a00 <-> a01
# twice (exit variant v -> arrival variant v in the target area, checked on m26a00d/m26a01d).
ALIAS_SIS = {'m26a00d': 'm19a00d', 'm26a01d': 'm19a01d', 'm26a02d': 'm19a03d'}
SIS_AREA = {0: (0, 0), 1: (1, 0), 3: (2, 0), 2: None}        # 4U area -> (GU area, variant); None = per area below
SIS_VIA_DROPPED = {'m19a01d': (2, 1), 'm19a03d': (1, 1)}      # 4U a01's link to a02 -> arena v1; arena's -> a01 v1
T_SIS = 0x065375d5


def convert_sis(area4):
    import sis
    s = sis.parse(open(os.path.join(U4, 'm19', 'stage', 'm19d', area4, area4 + '-info.%08x' % T_SIS), 'rb').read())
    for k in (1, 2):                      # exits: target area, arrivals: source area (0xff = quest start)
        keep = []
        for r in s['sec'][k]:
            a = r[17]
            if a != 0xFF:
                m = SIS_AREA[a] or SIS_VIA_DROPPED.get(area4)
                if m is None: continue
                r[17], r[16] = m[0], m[1] if r[16] == 0 else r[16]
            keep.append(r)
        s['sec'][k] = keep
    return sis.write(s)


# ------------------------------------------------------------------ whole-map area offsets (map_com stage\m26d\m26d)
# GU (C): whole map (map_com <lang>, cUIOEnlargeMap vtable +0x6c = 0x61bde8): icon = (x + off.x, z + off.z) * 256 * k /
# W + 2 * (rec.f3c, rec.f40) HD px from the texture centre; off = s32 pair at +0 / +4 of the 20-byte records of this
# file (f32, u32 count, records; read through 0x50089c -> 0x4f9040, memory +4 / +8), W = dims[26] = 60000 (0x5058d0),
# k = whole-map record +0x34 / +0x38 (0x61b940; stage 26 = 0x1635b5c: 1.0, f3c / f40 = 0). Checked: Fortress SIS land on
# the Fortress art. 4U (C): m19 stage class setup 0x6596dc -> 0x6c2ac8(W = 40000, records 0xdee2b4, 4 x 24 B {s32 x,
# s32 z, ...}); icons 0xb832ac: u = (x + off.x + W / 2) / W * 128 px of m19d_ID (checked: 4U SIS land on m19d_ID).
# -> offsets = 4U's here; module/stage_alias.c (stage_wholerec) sets k = 60000 / 40000 and tools/mapui4u2gu.py draws the
# 4U picture at 2x, so GU icon = 2 * (4U u - 64). The other record fields (Fortress' gameplay flags) stay.
T_WMAP = 0x6ff78212
WMAP_4U = 0xdee2b4                    # 4U v1.1 whole-map records (24 B), m19 = 4U areas a00..a03
WMAP_AREAS = {0: 0, 1: 1, 2: 3}       # alias area -> 4U area (as ALIAS_SIS)


def wholemap_offsets(d):
    m = open(os.path.join(ROOT, 'dump', 'exefs_v11', 'mem.bin'), 'rb').read()   # flat from 0x100000
    b = bytearray(d)
    n = struct.unpack_from('<I', b, 4)[0]
    assert n == len(WMAP_AREAS) and len(b) == 8 + 20 * n, (n, len(b))
    new = []
    for a, a4 in WMAP_AREAS.items():
        off = struct.unpack_from('<2i', m, WMAP_4U + 24 * a4 - 0x100000)
        struct.pack_into('<2i', b, 8 + 20 * a, *off)
        new.append(off)
    return bytes(b), 'whole-map offsets -> 4U m19 %s' % new


def build_map_com(report):
    import sbc
    ver, ents = arcpack.read(open(os.path.join(GUX, 'loc', 'arc', 'stage', 'map_com', 'm26.arc'), 'rb').read())
    rows = []
    out = []
    for p, t, d in ents:
        if t == T_SBC:
            name = p.split('\\')[-1]
            area = name[:7]
            kind = name[7:]
            if area in ALIAS_COLLISION and kind in SBC_KINDS:
                src, d4 = collision_4u(ALIAS_COLLISION[area], kind)
                if d4 is not None:
                    d = sbc.convert_4u(d4)
                    s = sbc.parse(d)
                    rows.append((p, ALIAS_COLLISION[area] + src, len(s['parts']), s['nA'], s['nB'], s['nC']))
                else:
                    rows.append((p, 'Fortress (kept)'))
        elif t == T_SIS and p.split('\\')[-1][:7] in ALIAS_SIS:
            src = ALIAS_SIS[p.split('\\')[-1][:7]]
            d = convert_sis(src)
            rows.append((p, src + '-info (area numbers remapped)'))
        elif t == T_WMAP and p == 'stage\\m26d\\m26d':
            d, what = wholemap_offsets(d)
            rows.append((p, what))
        elif t == T_CAM and p == CAMP_CAM and 'camera' not in KEEP:
            d, what = convert_camp_cam(d)
            rows.append((p, what))
        elif t == T_IPS and p == 'stage\\m26d\\m26d' and 'items' not in KEEP:
            d, what = convert_ips()
            rows.append((p, what))
        elif t == T_IPL and p in IPL_4U and 'items' not in KEEP:
            d, ids = convert_ipl(IPL_4U[p])
            rows.append((p, '%s (4U items %s -> GU %s)' % (IPL_4U[p], ids, [ITEMS_4U[k] for k in ids])))
        elif (p, t) in GIMMICK_EDITS and 'gimmicks' not in KEEP:
            d, what = GIMMICK_EDITS[(p, t)](d)
            rows.append((p, what))
        elif t == T_REL and p in ALIAS_RELATION and 'relation' not in KEEP:
            area4 = ALIAS_RELATION[p]
            g00 = collision_4u(area4, '-a-g00')[1]
            d, what = relation_for(sbc.convert_4u(g00), d)
            rows.append((p, '%s floors -> %s' % (area4, what)))
        out.append((p, t, d))
    report['collision'] = rows
    return out


# ------------------------------------------------------------------ item pops (map_com IPS / IPL, stage item model)
# rItemPopSet "IPS" v0x2003, same format in both games (GU reader 0x31a4f4, 4U 0x5b9d40): header 0x34 B {magic, ver,
# nAreas, data size, 0, 0, size1, size1, 0, size2, offset3 = size1 + size2, 0, size3}, then three sections, each
# starting with an area table {u32 off, u32 count} (offsets from the section start). Section 1 = gather points (36 B:
# +0 u8 list, +4 pos, +0x10 radius, +0x14 height, +0x18 / +0x1a u16 (4U yaw at +0x1a), +0x1c count, +0x1d
# guaranteed count (GU 0x31b290: then a random stop), +0x1e type, +0x1f icon = mesh group of the stage item model
# (GU 0x3191d8 -> point+0x68 -> 0x31945c; 4U shows group icon - 1, see ITEM_GROUPS), +0x20 flags). Sections 2 / 3 =
# per-area sub-tables {u32 off, u32 n} -> records (GU 0x319adc / 0x319b28, same layout in 4U; empty in the Fortress).
# rItemPopList "IPL" v0x2003: {n1, size1, off2, n2, size2} at 0x10, tables at 0x24 / 0x24 + off2 of {u32 off, u32
# count} -> count x {u8 %, u8 count, u16 item} + 0xff (GU 0x319eb8: list index of a point).
# The alias used to keep the Fortress files (pickups 760 above our ledges / over the abyss): now 4U m19d's, areas
# 4U 0 / 1 / 3 -> GU 0 / 1 / 2 (4U m19a02d has no GU area and no points), items by name (ITEMS_4U).
# Arena piles: 4U places each of its 5 spots twice, a full pile (+0x20 = 0x01 | spot bit 0x04 / 0x08 / 0x10, counts
# 5 / 4) and a small pile (same bits | 0x20, counts 3 / 2, icon + 1) that 4U activates once the first is empty
# (0x5b8c20: bits & 0x60, icon + 1, count +48 == 0). GU has no such chain (its +0x56 bits 2 / 4 are runtime flags,
# 0x319528 / 0x31a944; empty points are deleted and re-created, 0x31b5xx): one GU point per spot with the full
# pile's mesh and the summed counts 8 / 6, flags 0x01 as the Fortress' (deviation: the small-pile stage is not shown).
T_IPS, T_IPL = 0x52776ab1, 0x25fd693f
IPS_4U = 'stage\\m19d\\m19d'
IPS_AREAS = (0, 1, 3)                   # 4U area of GU area 0, 1, 2
IPL_4U = {'stage\\m26d\\m26d_low': 'stage\\m19d\\m19d', 'stage\\m26d\\m26d_high': 'stage\\m19d\\m19d_high',
          'stage\\m26d\\m26d_g': 'stage\\m19d\\m19d_g'}
# 4U item -> GU item (same English name: Ballista Ammo, Cannon Ammo, Stone, Whetstone, EZ Max Potion, EZ Lifepowder,
# First-aid Med+, First-aid Med, EZ Barrel Bomb L, Throwing Knife, Bounce Bomb, Barrel Bomb L)
ITEMS_4U = {780: 1730, 783: 2115, 206: 317, 168: 56, 777: 1724, 1732: 1725, 770: 1717, 769: 1716, 779: 1728,
            55: 64, 81: 91, 79: 89}
# The pile meshes: 4U m19-item (groups 17 / 18 = GU m26d-item's two piles, unused by 4U; 21..30 = full / small pile
# of spot E ballista, E cannon, W ballista, W cannon, N cannon: same bounding box per pair, the small one's vertices
# mostly the full one's) replaces the Fortress model under its GU path, regrouped. The point visual (uShellSt001
# init 0x4915fc, by icon point+0x68): icons 21..28 / 29 / 34 / 35 / 38 / 39 = St001 effects only (21..26 = GU's bug
# points: butterflies, fireflies), 36 = dropped item, 30..33 nothing; icons < 21 and 37 load the item model and draw
# one group (0x491974): icon 1..12 -> group 5, 6, 7, 8, 1, 2, 11, 12, 3, 4, 9, 10, 13..16 -> none, 17..20 -> 17..20,
# 37 -> 21 (0 = no visual). Icons 1 / 2 / 5 / 6 / 11 / 12 are also gather kinds of the point scans 0x31badc / 0x31bc34
# (Palico gathering, G), 37..39 points exist only by a quest flag (0x31a66c), 25 / 26 / 38 are remapped (0x3191d8).
# The five full piles -> groups / icons 17..20 and group 7 (icon 3); the small piles and 4U's own 17 / 18 -> 22..28,
# never drawn (no icon sets a group bit above 21).
ITEM_MODEL = ('stage\\m26d\\m26d-item\\m26d-item', 'stage\\m19d\\m19-item\\m19-item')
ITEM_GROUPS = {17: 22, 18: 23, 21: 17, 22: 24, 23: 18, 24: 25, 25: 19, 26: 26, 27: 20, 28: 27, 29: 7, 30: 28}
GROUP_ICON = {7: 3}                     # GU icon drawing that group, where not icon == group


def ips_sections(d):
    magic, ver, n, size, z0, z1, s1, s1b, z2, s2, o3, z3, s3 = struct.unpack_from('<4s12I', d, 0)
    assert magic == b'IPS\0' and ver == 0x2003 and s1 == s1b and o3 == s1 + s2 and not (z0 | z1 | z2 | z3), d[:0x34]
    assert size == s1 + s2 + s3 == len(d) - 0x34, (size, s1, s2, s3, len(d))
    return n, (d[0x34:0x34 + s1], d[0x34 + s1:0x34 + o3], d[0x34 + o3:0x34 + o3 + s3])


def ips_build(n, secs):
    s1, s2, s3 = secs
    return b'IPS\0' + struct.pack('<12I', 0x2003, n, len(s1) + len(s2) + len(s3), 0, 0, len(s1), len(s1), 0,
                                  len(s2), len(s1) + len(s2), 0, len(s3)) + s1 + s2 + s3


def ips_points(sec, n):
    return [[sec[o + 36 * i:o + 36 * (i + 1)] for i in range(c)]
            for o, c in (struct.unpack_from('<2I', sec, 8 * a) for a in range(n))]


def ips_pack_points(areas):
    tab = bytearray(8 * len(areas)); body = b''
    for a, recs in enumerate(areas):
        struct.pack_into('<2I', tab, 8 * a, 8 * len(areas) + len(body), len(recs))
        body += b''.join(recs)
    return bytes(tab) + body


def ips_nested(sec, n4, order):
    """section 2 / 3 with the area table of `order` (4U areas): each area block (sub-table + records) moves as is,
    its sub-table offsets shifted"""
    tab = [struct.unpack_from('<2I', sec, 8 * a) for a in range(n4)]
    starts = sorted({o for o, c in tab if c} | {len(sec)})
    out = bytearray(8 * len(order)); body = bytearray()
    for g, a in enumerate(order):
        o, c = tab[a]
        new = 8 * len(order) + len(body)
        if c:
            blk = bytearray(sec[o:min(s for s in starts if s > o)])
            for i in range(c):
                struct.pack_into('<I', blk, 8 * i, struct.unpack_from('<I', blk, 8 * i)[0] - o + new)
            body += blk
        struct.pack_into('<2I', out, 8 * g, new, c)
    return bytes(out + body)


def convert_ips():
    d4 = u4_find(IPS_4U, T_IPS)
    n4, (s1, s2, s3) = ips_sections(d4)
    assert ips_build(n4, (ips_pack_points(ips_points(s1, n4)), ips_nested(s2, n4, range(n4)),
                          ips_nested(s3, n4, range(n4)))) == d4, 'IPS round trip'
    pts = ips_points(s1, n4)
    assert not pts[2], 'points in 4U m19a02d'
    areas = []
    for a in IPS_AREAS:
        recs = [bytearray(r) for r in pts[a] if not (a == 3 and r[0x20] & 0x20)]
        if a == 3:
            small = [r for r in pts[a] if r[0x20] & 0x20]
            assert len(small) == len(recs) == 5, (len(small), len(recs))
            for r in recs:
                s, = [s for s in small if s[0x20] == r[0x20] | 0x20 and s[0x1f] == r[0x1f] + 1 and s[0] == r[0]
                      and s[4:0x1c] == r[4:0x1c]]
                r[0x1c] += s[0x1c]; r[0x1d] += s[0x1d]
                g = ITEM_GROUPS[r[0x1f] - 1]
                r[0x1f] = GROUP_ICON.get(g, g)
                r[0x20] = 0x01
        areas.append([bytes(r) for r in recs])
    d = ips_build(len(IPS_AREAS), (ips_pack_points(areas), ips_nested(s2, n4, IPS_AREAS), ips_nested(s3, n4, IPS_AREAS)))
    return d, '%s: points per GU area %s (4U areas %s; arena pile pairs merged, icons -> %s), sections 2 / 3 moved' % (
        IPS_4U, [len(r) for r in areas], list(IPS_AREAS), sorted({r[0x1f] for r in areas[2]}))


def convert_ipl(path4):
    d = bytearray(u4_find(path4, T_IPL))
    assert d[:4] == b'IPL\0' and struct.unpack_from('<2I', d, 4) == (0x2003, len(d) - 0x24), d[:12]
    n1, size1, off2, n2, size2 = struct.unpack_from('<5I', d, 0x10)
    ids = set()
    for base, n in ((0x24, n1), (0x24 + off2, n2)):
        for i in range(n):
            off, cnt = struct.unpack_from('<2I', d, base + 8 * i)
            for k in range(cnt):
                o = base + off + 4 * k + 2
                it = struct.unpack_from('<H', d, o)[0]
                ids.add(it)
                struct.pack_into('<H', d, o, ITEMS_4U[it])
            assert d[base + off + 4 * cnt] == 0xff, (path4, i)
    return bytes(d), sorted(ids)


def regroup_model(dg, gmap):
    """GU MOD (convert_models output): mesh group ids (group list +0, mesh d0 bits 0..11) renamed by gmap, the group
    list kept in id order like the sources"""
    m = modlib.parse(dg)
    d = bytearray(dg)
    og, om = m['offsets']['groups'], m['offsets']['meshes']
    ents = []
    for i in range(m['groups']):
        e = bytearray(d[og + 32 * i:og + 32 * (i + 1)])
        g = struct.unpack_from('<I', e, 0)[0]
        struct.pack_into('<I', e, 0, gmap.get(g, g))
        ents.append(bytes(e))
    d[og:og + 32 * len(ents)] = b''.join(sorted(ents, key=lambda e: struct.unpack_from('<I', e, 0)[0]))
    for i in range(m['meshes']):
        d0 = struct.unpack_from('<I', d, om + 48 * i + 4)[0]
        struct.pack_into('<I', d, om + 48 * i + 4, (d0 & ~0xfff) | gmap.get(d0 & 0xfff, d0 & 0xfff))
    return bytes(d)


# ------------------------------------------------------------------ camp camera (map_com m26a00d-cam)
# 4U rStageCameraData "SCD" v0x13 (m19a00d-cam): header {nZones, nParams, nRails, 0, offZones, offParams, offRails},
# zones 0x44 B {u8 id, u8 type, u8 2, u8 2, u8 nConn, u8 0, u8 param, u8 0, 16 B 0, 4 corners (x, z) (= GU 左上 /
# 右上 / 左下 / 右下 pt, same order), 2 f32 heights, u32 offset of nConn x {u8 zone id, u8 blend frames, u8 flag,
# u8}}, params 0x38 B {vec3 pos, vec3 target 1, vec3 target 2, vec3 target 3, f32 fov, f32 roll}. Capcom's ported
# camps (4U m01 / m03 / m04 / m05 / m11 / m15 -> GU m11 / m13 / m14 / m16 / m09 + m10 / m12) map zone id -> areaNo,
# type -> camType, panType 0, panTarget 2, pos -> panParam.camPos, target -> panParam.target, fov, corners; their
# three targets are equal (0, 170, 0). m19's only target set in every param is the third, (0, 240, 0) -> used.
# GU camera 0x159a4 (record +0x31 camType): 0 = fixed camPos looking at the player + target, 1 = rail, 2 = camPos /
# target as offsets from the player, 3 / 4 = area camera. 0x14a7c keeps the LAST matching record, and m19's catch-all
# zone 6 (x -2948..4243, z -4805..1781, over the supply-box zone 1) is the last 4U zone -> 4U takes the first match ->
# records in reverse order. The Fortress file (record 1 = a fixed camera at y 240, 390 below our camp floor around
# the supply box) is replaced: its default record 0 (camType 3) kept, then 4U's type-0 zones (the supply box). Not
# converted (deviation): zone 2 (id 4, type 1 = rail camera over x -5600..-2976, rail table at offRails), the type-2
# follow zones (GU blends type 2 over 40 frames, 0x15428, and no GU camp uses it: the camera trailed the hunter, test
# of 2026-10-23) and the zone-to-zone blend frames (GU connectArray left empty, as in Capcom's camps): GU's default
# camera and blending there.
T_CAM = 0x6b41a2f9
CAMP_CAM = 'stage\\m26d\\m26a00d\\etc\\m26a00d-cam'
CAMP_CAM_4U = 'stage\\m19d\\m19a00d\\etc\\m19a00d-cam'


def convert_camp_cam(d):
    import copy, xfs
    s = u4_find(CAMP_CAM_4U, T_CAM)
    magic, ver, nz, npar, nrail, z, oz, op, orl = struct.unpack_from('<4s8I', s, 0)
    assert magic == b'SCD\0' and ver == 0x13, (magic, ver)
    root = xfs.parse(d)
    recs = root['mDataArray']['mpArray']
    assert len(recs) == 2 and [r['cmnData.camType'] for r in recs] == [3, 0], [r['cmnData.camType'] for r in recs]
    f32 = lambda v: int.from_bytes(struct.pack('<f', v), 'little')
    v2 = lambda x, y: int.from_bytes(struct.pack('<2f', x, y), 'little')
    v4 = lambda v: int.from_bytes(struct.pack('<4f', v[0], v[1], v[2], 0.0), 'little')
    new, done = [recs[0]], []
    for i in reversed(range(nz)):
        r = s[oz + 0x44 * i:oz + 0x44 * (i + 1)]
        zid, typ, prm = r[0], r[1], r[6]
        if typ != 0:
            continue
        pts = struct.unpack_from('<8f', r, 0x18)
        h = struct.unpack_from('<2f', r, 0x38)
        p = struct.unpack_from('<14f', s, op + 0x38 * prm)
        g = copy.deepcopy(recs[1])
        for k, i2 in zip(('左上 pt', '右上 pt', '左下 pt', '右下 pt'), range(0, 8, 2)):
            g[k] = v2(pts[i2], pts[i2 + 1])
        g['高さ'], g['高さ(下)'] = f32(h[0]), f32(h[1])
        g['cmnData.areaNo'], g['cmnData.camType'], g['cmnData.panType'], g['cmnData.panTarget'] = zid, typ, 0, 2
        g['cmnData.zoomDist'] = g['cmnData.zoomRate'] = 0
        g['panParam.fov'], g['panParam.roll'] = f32(p[12]), f32(p[13])
        g['panParam.camPos'], g['panParam.target'] = v4(p[0:3]), v4(p[9:12])
        g['railParam.railType'] = g['railParam.target'] = g['railParam.keyNum'] = 0
        new.append(g)
        done.append((zid, typ, p[0:3], p[9:12]))
    root['mDataArray']['mpArray'] = new
    return xfs.build(d, root), '%s zones (id, type, pos, target) %s, reversed (GU keeps the last match); rail and ' \
        'follow zones not converted' % (CAMP_CAM_4U, done)


# ------------------------------------------------------------------ Fortress gimmick shells (map_com shell params)
# GU spawns the Fortress gimmicks as shells from code (0x50249c, flags u16[stage] at 0x162bd60; stage 26 = 0x3ec):
#   st003 x4 Dragonator spears: model m26d-gekiryusou (= 4U m19d-gekiryusou), pos = st003 FUP vec[3 + i] (i = 0..3,
#        Fortress: vec 3..6; Castle Schrade 7, Forlorn Citadel 9, stage 10 0..2), (pitch, yaw) degrees = FUP
#        st003_sh00<k> floats 0/1 with k = 1 for stage 26 (0x4a3164 -> shell sub-type byte, set to 1 at 0x5025c4)
#   st004 ballistae: one per SIS point kind 3 (position/angle from the point) -> already 4U's via the SIS conversion
#   st006 rail-cannon cart (models m26d-s00..s03 = 4U m19a03d-s01..s04), one per area 1 / 2, path = scheduler
#        m26d-etc-a00 ("Model" mPos / mAngle, 25 keys over 6000 frames), stop frames = st006 FUP ints
#   st007 gate (m26d-a00/a01 = 4U m19a03d-a00/a01) at st007 FUP vec 0 (-5980, 2050, -16200), area 1 -> outside our
#        area 1 (4U m19a01d spans x, z +-3100 / -2100..3650): left as is (4U's arena gate not reproduced, notes)
#   st008 per SIS point kind 6 (none in 4U's arena info)
# The quest-shell arcs arc/stage/quest/shell/st0NN.arc are never requested (no path string in main), so the map_com
# copies are the only ones loaded; ours (m28.arc) is loaded only for the alias -> Fortress quests are unaffected.
T_FUP = 0x496f8f22


def fup_parse(d):
    assert d[:4] == b'FUP\0' and struct.unpack_from('<I', d, 4)[0] == 2, d[:8]
    ni, nf, nv = struct.unpack_from('<3I', d, 8)
    o = 0x14
    ints = list(struct.unpack_from('<%di' % ni, d, o)); o += 4 * ni
    fl = list(struct.unpack_from('<%df' % nf, d, o)); o += 4 * nf
    vs = [list(struct.unpack_from('<3f', d, o + 12 * i)) for i in range(nv)]; o += 12 * nv
    assert o == len(d), (o, len(d))
    return ints, fl, vs


def fup_write(ints, fl, vs):
    return (b'FUP\0' + struct.pack('<4I', 2, len(ints), len(fl), len(vs)) + struct.pack('<%di' % len(ints), *ints)
            + struct.pack('<%df' % len(fl), *fl) + b''.join(struct.pack('<3f', *v) for v in vs))


# 4U Battlequarters Dragonator (traced, notes/stage.md section 12): the m19 stage class aMap19 (vtable 0xe6556c, setup
# slot 0x6594b4) creates its uStageGimmick objects (ctor 0x33ce00, param {u8 type, u8 sub, u8 area, pos, rot}) through
# 0x6c1cc0 (type 2): two spears at (+-495, 800, 4105), rot (0, pi, 0), area 3 (literals 0x6596c8..0x6596d8); type 2 =
# model index 4 of the m19 gimmick list 0xef5874 (table 0x1032f80 {1, 5, 4, 1}) = m19d-gekiryusou (= GU m26d-gekiryusou,
# same AABB). The other two type-2/3 objects (sub 3 / type 3, pos 0) have no model: pile bunker + controller. Switch =
# SIS point kind 5 at (0, 1765, 3610) (converted SIS). GU st003 takes pos = FUP vec[3 + i] and (pitch, yaw) degrees =
# st003_sh001; GU spawns 4 spears for stage 26 -> module/stage_gimmick.c stops the loop after 2 for the alias (vec 5/6
# keep the Fortress values, unused). The spear motion of GU st003 (8-frame thrust to 1600, back to 1400, hold 180,
# retract) is 4U's uStageGimmick type 2 update 0x33c7c8 (same constants), facing -z = yaw 180 as 4U's rot y = pi.
DRAGONATOR_4U = [(495.0, 800.0, 4105.0), (-495.0, 800.0, 4105.0)]
DRAGONATOR_PITCH_YAW = (0.0, 180.0)
# 4U rail-cannon cart (scheduler m19a03d-s00, KowareObj mType 21): parked at the north station (895, 1700, 4355),
# mRot (0, pi, 0); player levers send it around a 4-station LOOP (north / west (-3097, 950, 590) / south (0, 1700,
# -5210) / east (3535, 950, 840)): each 4U action plays s00 frames [startFrame, startFrame + moveFrame] (notes/stage.md
# section 13). GU st006 = Capcom's port of this cart (same 5 interaction points), but on a linear rail. The path
# scheduler m26d-etc-a00 gets the 4U s00 cart keys verbatim (118 mOffset / mRot keys -> "Model" mPos / mAngle, same
# frame numbers + interpolation bits, frame count = 4U's) and module/stage_cart.c plays the 4U legs on it.
# st006 FUP ints [6] / [7] (area-2 stops, states 10 / 11) -> 0 / 800 = 4U N / W, so without the module driver GU's
# own area-2 logic still runs the 4U N <-> W leg. `--keep-cart`: every key = the 4U start pose (old parked cart).
CART_4U_POS, CART_4U_ANGLE = (895.0, 1700.0, 4355.0), (0.0, 3.14159265, 0.0)
CART_4U_SDL, CART_4U_OBJ = 'stage\\m19d\\m19a03d\\sdl\\m19a03d-s00', 'm19a03d-s00'
CART_AREA2_STOPS = (0, 800)


def edit_st003(d):
    ints, fl, vs = fup_parse(d)
    assert len(vs) == 10 and [round(c) for c in vs[3]] == [380, 1080, -5500], vs[3]
    for i, v in enumerate(DRAGONATOR_4U): vs[3 + i] = list(v)
    return fup_write(ints, fl, vs), 'Dragonator spears vec 3..4 -> 4U aMap19 %s (vec 5/6 unused)' % (DRAGONATOR_4U,)


def edit_st003_sh001(d):
    ints, fl, vs = fup_parse(d)
    assert fl == [0.0, 0.0], fl
    return fup_write(ints, list(DRAGONATOR_PITCH_YAW), vs), 'stage-26 spear (pitch, yaw) -> %s' % (DRAGONATOR_PITCH_YAW,)


def edit_cart_path(d):
    import sdl
    s = sdl.parse(d)
    (i, name, cls, tr), = sdl.objects(s)
    assert name == 'Model' and set(tr) >= {'mPos', 'mAngle'}, (name, list(tr))
    if 'cart' in KEEP:
        for k, v in (('mPos', CART_4U_POS), ('mAngle', CART_4U_ANGLE)):
            sdl.set_values(s, tr[k], [v] * len(tr[k]['times']))
        return sdl.build(s), 'rail-cannon cart path: every key = 4U start %s yaw pi (--keep-cart)' % (CART_4U_POS,)
    u = sdl.parse(u4_find(CART_4U_SDL, T_SDL))
    ut, = [t for _, n, _, t in sdl.objects(u) if n == CART_4U_OBJ]
    times = ut['mOffset']['times']
    assert ut['mRot']['times'] == times and len(times) == 118, len(times)
    for k, k4 in (('mPos', 'mOffset'), ('mAngle', 'mRot')):
        assert tr[k]['kind'] == sdl.KIND_4U_TO_GU[ut[k4]['kind']]
        sdl.set_values(s, tr[k], sdl.values(u, ut[k4]), times=times)
    s['frames'] = max(s['frames'], u['frames'])
    return sdl.build(s), 'rail-cannon cart path <- 4U %s keys (%d, frames %d) for the loop driver' % (
        CART_4U_OBJ, len(times), s['frames'])


def edit_st006(d):
    ints, fl, vs = fup_parse(d)
    assert ints == [0, 800, 1000, 1800, 2000, 3000, 4000, 4800], ints
    if 'cart' in KEEP:
        return d, 'st006 FUP unchanged (--keep-cart)'
    ints[6], ints[7] = CART_AREA2_STOPS
    return fup_write(ints, fl, vs), 'st006 area-2 stops (FUP ints 6 / 7) -> %s = 4U N / W' % (CART_AREA2_STOPS,)


# ------------------------------------------------------------------ monster route finding (relation\m26\m26aNN)
# RouteFindDataResource (XFS type 0x1e329efc, loaded per area by sStage 0x4fded0 into stage+0x3c0+4*area): one entry
# per floor id (collision group w1 byte 3), for each destination floor {u8 RouteAttr, u8 RouteAttrDir, s16 TblCnt,
# u8 FloorID0..7 = floor path} (cRelationData +4/+5/+6/+8, registration 0x4f5cb8). Rules read off all 78 GU tables
# (base RomFS map_com, scratch relcorp/relstat/relbfs): row 0 and column 0 = direct [j] (1, 0); self = [a] (1, 0);
# direct pairs [a, b] carry the transition class by height: 1 walk (shared edge / ramp, GU dy up to +-1784),
# 2 ~500 (IQR 397..777), 4 ~1000 (627..1000), 8 big (1349..2241); 16 / 32 = rarer special jumps; dir 0 up, 1 down;
# longer paths = BFS over the direct pairs with neighbours in ascending order (1095 of 1170 GU entries; the rest are
# unreachable / hand-made), attr/dir = the path's first non-walk hop (472 / 472). Direct pairs as in Capcom's own
# Fortress tables (geometry check of m26a01d/a02d, scratch adj.py): every ledge links to the ground floor 1, and two
# ledges link when they share collision vertices at the same height. The 4U arena (m19a03d) gives: 1-2 (950, 4),
# 1-3 / 1-4 (ramps: shared vertices, 1), 1-5 / 1-7 (1700, 8), 1-6 (950, 4), 2-3, 3-4 (walk). 4U itself has no route
# tables (its AI walks on SIS + collision), so this is GU's convention applied to 4U's floors (G for the AI use).
T_REL = 0x1e329efc
ALIAS_RELATION = {'relation\\m26\\m26a01': 'm19a01d', 'relation\\m26\\m26a02': 'm19a03d'}


def collision_floors(d):
    """GU SBC bytes -> {floor id: (vertices (n, 3), median y)} (floor id = group w1 byte 3)."""
    import sbc
    s = sbc.parse(d)
    V = np.frombuffer(s['verts'], '<f4').reshape(-1, 4)[:, :3]
    G = [struct.unpack_from('<2I', s['groups'], 32 * i)[1] >> 24 for i in range(s['nG'])]
    acc = {}
    for p in s['parts']:
        t0, tn, v0 = p['pairs'][2], p['pairs'][3], p['pairs'][4]
        for k in range(tn):
            o = 32 * (t0 + k)
            vi = struct.unpack_from('<3H', s['tris'], o + 12)
            acc.setdefault(G[struct.unpack_from('<H', s['tris'], o + 18)[0]], []).append(V[[v0 + x for x in vi]])
    return {f: (np.concatenate(L), float(np.median(np.concatenate(L)[:, 1]))) for f, L in acc.items()}


def relation_pairs(fl):
    """direct pairs {(a, b): (attr, dir)} per the Fortress convention above."""
    def shared(a, b):
        A, B = fl[a][0], fl[b][0]
        d = np.abs(A[None, :, :] - B[:, None, :]).max(2)
        return int((d < 2).sum())
    def cls(dy):
        h = abs(dy)
        return 1 if h < 200 else 2 if h < 700 else 4 if h < 1250 else 8
    pairs = {}
    ids = sorted(f for f in fl if f)
    for b in ids:
        if b == 1 or 1 not in fl: continue
        dy = fl[b][1] - fl[1][1]
        attr = 1 if shared(1, b) else cls(dy)
        pairs[(1, b)] = (attr, 0 if dy >= 0 or attr == 1 else 1)
        pairs[(b, 1)] = (attr, 1 if dy > 0 and attr != 1 else 0)
    for a in ids:
        for b in ids:
            if 1 < a < b and abs(fl[a][1] - fl[b][1]) < 200 and shared(a, b):
                pairs[(a, b)] = pairs[(b, a)] = (1, 0)
    return pairs


def relation_table(fl):
    """[(floor, [(attr, dir, path) per destination 0..n-1])] for floors 0..max id."""
    n = max(fl) + 1
    pairs = relation_pairs(fl)
    adj = {a: sorted(b for (x, b) in pairs if x == a) for a in range(n)}
    rows = []
    for a in range(n):
        row = []
        if a == 0:
            rows.append((0, [(1, 0, [j]) for j in range(n)])); continue
        prev = {a: None}; q = [a]
        for x in q:
            for y in adj[x]:
                if y not in prev: prev[y] = x; q.append(y)
        for j in range(n):
            if j == 0 or j == a or j not in prev:
                row.append((1, 0, [j])); continue
            path = [j]
            while path[-1] != a: path.append(prev[path[-1]])
            path = path[::-1]
            hops = [pairs[(path[i], path[i + 1])] for i in range(len(path) - 1)]
            nw = [h for h in hops if h[0] != 1]
            attr, dr = nw[0] if nw else (1, 0)
            row.append((attr, dr, path))
        rows.append((a, row))
    return rows


def relation_xfs(tpl, rows):
    """serialize rows with the Fortress file's class definitions (XFS v0x10.8; object = u16 2*def+1, u16 running id,
    u32 size from the size field on; member = u32 count + values / objects; header +8 = object count)."""
    nd, dsz = struct.unpack_from('<II', tpl, 0x10)
    head = bytearray(tpl[:0x18 + dsz])
    ids = [0]
    def obj(cls, body_fn):
        oid = ids[0]; ids[0] += 1
        body = body_fn()
        return struct.pack('<HHI', 2 * cls + 1, oid, len(body) + 4) + body
    def one(fmt, v):
        return struct.pack('<I' + fmt, 1, v)
    def elem(attr, dr, path):
        assert len(path) <= 8
        fid = path + [0] * (8 - len(path))
        return lambda: one('B', attr) + one('B', dr) + one('h', len(path)) + b''.join(one('B', f) for f in fid)
    def floor(f, row):
        def rel():
            return one('B', 0) + struct.pack('<I', len(row)) + b''.join(obj(3, elem(*e)) for e in row)
        return lambda: one('B', f) + struct.pack('<I', 1) + obj(1, rel)
    def rfd():
        return one('B', 1) + struct.pack('<I', len(rows)) + b''.join(obj(2, floor(f, r)) for f, r in rows)
    body = obj(0, lambda: one('I', 2) + struct.pack('<I', 1) + obj(1, rfd))
    struct.pack_into('<I', head, 8, ids[0])
    return bytes(head) + body


def relation_parse(d):
    """inverse of relation_xfs for the fixed RouteFindDataResource layout -> rows (self-check / reports)."""
    nd, dsz = struct.unpack_from('<II', d, 0x10)
    o = [0x18 + dsz]
    def rd(fmt):
        v = struct.unpack_from(fmt, d, o[0]); o[0] += struct.calcsize(fmt); return v
    def hdr(): rd('<HHI')
    def one(fmt): return rd('<I' + fmt)[1]
    hdr(); assert one('I') == 2; rd('<I'); hdr(); one('B'); n = rd('<I')[0]
    rows = []
    for _ in range(n):
        hdr(); f = one('B'); rd('<I'); hdr(); one('B'); m = rd('<I')[0]; row = []
        for _ in range(m):
            hdr(); a = one('B'); dr = one('B'); c = one('h'); fid = [one('B') for _ in range(8)]
            row.append((a, dr, fid[:c]))
        rows.append((f, row))
    assert o[0] == len(d), (o[0], len(d))
    return rows


def relation_for(gsbc, tpl):
    assert relation_xfs(tpl, relation_parse(tpl)) == tpl            # serializer reproduces Capcom's file
    fl = collision_floors(gsbc)
    rows = relation_table(fl)
    out = relation_xfs(tpl, rows)
    assert relation_parse(out) == rows
    desc = ' '.join('%d-%d:%d/%d' % (a, b, at, dr) for (a, b), (at, dr) in sorted(relation_pairs(fl).items()) if a < b)
    return out, 'floors %s, direct %s' % (sorted(fl), desc)


GIMMICK_EDITS = {
    ('shell\\st\\st003\\st003', T_FUP): edit_st003,
    ('shell\\st\\st003\\st003_sh001', T_FUP): edit_st003_sh001,
    ('stage\\m26d\\m26d-etc\\sdl\\m26d-etc-a00', T_SDL): edit_cart_path,
    ('shell\\st\\st006\\st006', T_FUP): edit_st006,
}


# ------------------------------------------------------------------ stage arc m28d.arc (Fortress m26d.arc copy)
# Breakables (KowareObj schedulers, kod table in map_com: 5 slots, area 1 k01..k03, area 2 k01..k02, vital 100).
# Area 2 slots <- 4U arena breakables m19a03d-k01 / -k02 (3 damage-state models + a06 each, world-space models,
# mType 0 = GU's common type); mId kept at the Fortress slot's value (mId = the collision part a break disables:
# Fortress a02 parts 1 / 3; our arena collision has no such part). 4U k03 (165, 1700, 6315) has no slot (dropped).
# 4U's k schedulers carry no mAt* attack sphere (a GU-only property) -> they cannot be broken (deviation); their
# "Effect" controllers (class unused in GU) and SoundControl (4U SE ids 300-320 of the 4U m19a03d bank, area 3) are
# removed. Area 1 slots (Fortress gates; 4U's area 1 has no breakables): models moved 50000 below and Draw 0.
KOWARE_4U = {'stage\\m26d\\m26a02d\\sdl\\m26a02d-k01': 'stage\\m19d\\m19a03d\\sdl\\m19a03d-k01',
             'stage\\m26d\\m26a02d\\sdl\\m26a02d-k02': 'stage\\m19d\\m19a03d\\sdl\\m19a03d-k02'}
KOWARE_HIDE = ['stage\\m26d\\m26a01d\\sdl\\m26a01d-k0%d' % k for k in (1, 2, 3)]
SOUND_CTRL = 0x10163337
# The a06 smoke billboard of each 4U breakable is a uKowareModel in object category 9; GU's 709 schedulers never put
# a uKowareModel there (always 11) -> dropped (it only shows after a break, which cannot happen here).
KOWARE_MODEL = 0x167df530

# arena-4: 4U side doors a02 / a03 + sinking wall a04 = KowareObj scheduler m19a03d-a01 (mId 3, one action Id 0 =
# frames 0..200: doors swing to +-pi/2, wall sinks 360; SE 309..312). GU runs the same KowareObj class (Capcom's port):
# 0x4fe9c0 creates the schedulers k01..k04 of every area from file ids 0xbbdf + stage*52 + area*4 + k-1; m26a02d-k03
# (0xc131) is in GU's file table but not shipped by the Fortress -> the converted a01 goes there. GU plays action Id 0
# and does 4U's collision swap itself (action-0 start: SBC part 2*mId-1 = 5 off, part 6 on; 0x513e2c = 4U 0x1cd494).
# Edits: the 4U "Effect" controller is dropped (class absent in GU; module/stage_doors.c posts its CreateKowareEft 16
# at frame 2), SoundControl mSdlSeReqArea 3 -> 2 (4U arena area 3 = GU area 2), kowareModel Draw 0 -> 1 (4U's older
# schedulers carry Draw 0 on models that are visible in 4U, e.g. the cart s00..s02; every GU kowareModel has Draw 1).
# The trigger (4U 0x6b70cc: boss HP <= 40 % and > 10 min ELAPSED) is module/stage_doors.c (cmd 0 via 0x514f9c).
# kod table (map_com): + {area 2, mId 3, idx 5, type 0, vital 100} = 4U's type-0 state table entry (3, 3, 0)
# (0x6c55d8; GU 0x5011c0 / 0x501864 keep the "action played" bit idx in mgr+0x280).
DOORS_KOWARE = ('stage\\m26d\\m26a02d\\sdl\\m26a02d-k03', 'stage\\m19d\\m19a03d\\sdl\\m19a03d-a01')
DOORS_KOD = (2, 3, 5, 0, 100)
T_KOD = 0x2dd067f
# Floor cannons s03 / s04 (KowareObj mId 4 / 5, actions 51..55 = barrel 25 / 55 deg and back, SE 304 / 305; their
# Effect controllers post index 0 = nothing). s03 -> m26a02d-k04 (file 0xc132, created by 0x4fe9c0); s04 -> the path
# of file 0xc133 (m26a03d-k01: stage 26 has 3 areas, so 0x4fe9c0 never asks for it) that module/stage_cannon.c
# creates for area 2 itself with 0x500bb4 right after 0x4fe9c0. Same edits as the doors (Effect dropped, Draw 1,
# SE area 3 -> 2). No kod entry (4U's state tables 0x6c55d8 / 0x6c5578 hold no mId 4 / 5).
CANNONS_KOWARE = [('stage\\m26d\\m26a02d\\sdl\\m26a02d-k04', 'stage\\m19d\\m19a03d\\sdl\\m19a03d-s03', 4, 1),
                  ('stage\\m26d\\m26a03d\\sdl\\m26a03d-k01', 'stage\\m19d\\m19a03d\\sdl\\m19a03d-s04', 5, 1)]
# Demolisher gate (4U scheduler m19a03d-a00, KowareObj mType 22 / mId 2: cannon a00 at (0, 2200, -8110), pitch
# -1.134 rad keyed (raise / aim), barrel a01 recoils 300 at frame 156, PartsDisp off 152..400; actions 53 raise
# 0..150, 54 fire 150..400 (quake 9), 55 400..700; SE controller) -> the path of file 0xc134 (m26a03d-k02, next to
# s04's 0xc133), created by module/stage_demolisher.c like s04. Same edits as the cannons, plus its
# ScrollCollisionSbc object (moving collision with 4U's m19a03d-a-w00-a00-shell, not shipped: GU's st007 uses
# m26d-etc's) dropped: the gate stands behind the south wall, out of the hunters' reach (deviation).
# mId 2 -> 6: the breakable m26a02d-k02 (converted 4U k02, KowareObj area 2, mId 2 = its Fortress slot) is created
# first, so area + mId 2 found the breakable (no action 53 / 54: GU's lookup 0x513d3c failed and closed every request,
# test 20:37 / 20:59). Area-2 mIds: k01 1, k02 2, doors 3, s03 4, s04 5 -> the gate 6 (no kod entry, as s03 / s04).
GATE_KOWARE = ('stage\\m26d\\m26a03d\\sdl\\m26a03d-k02', 'stage\\m19d\\m19a03d\\sdl\\m19a03d-a00', 2, 1)
GATE_MID = 6
SCROLL_SBC = 0x24e6fdaf


def convert_kobj(path4, mid, n_se, se_area=(3, 2), drop_cls=(), new_mid=None):
    """4U arena KowareObj scheduler -> GU (Effect controller dropped, kowareModel Draw 1, SE area se_area[0] -> [1]:
    Battlequarters 3 -> 2; n_se = number of SoundControl area tracks; objects of the classes drop_cls removed;
    new_mid: the KowareObj mId written instead of 4U's `mid`)."""
    import sdl
    new = sdl.convert_4u(u4_find(path4, T_SDL), drop_ctrl=lambda c, n: c == EFFECT_CTRL,
                         drop_obj=lambda c, cat, n: c in drop_cls, drop_keyless=True)
    s = sdl.parse(new)
    mids = []
    for i, n, c, tr in sdl.objects(s):
        if c == KOWARE_MODEL and 'Draw' in tr:
            sdl.set_values(s, tr['Draw'], [1] * len(tr['Draw']['times']))
        if c == 0x3dfe3bc2:
            mids = sdl.values(s, tr['mId'])
            if new_mid is not None:
                sdl.set_values(s, tr['mId'], [new_mid] * len(tr['mId']['times']))
    assert mids == [mid], (path4, mids)
    ctrl = None; areas = 0
    for i, e in enumerate(s['ents']):
        if e['kind'] == 3: ctrl = e['x']
        elif e['kind'] in (1, 2, 4): ctrl = None
        elif ctrl == SOUND_CTRL and e['name'] == 'mSdlSeReqArea' and e['times'] is not None:
            assert sdl.values(s, e) == [se_area[0]] * len(e['times'])
            sdl.set_values(s, e, [se_area[1]] * len(e['times'])); areas += 1
    assert areas == n_se, (path4, areas)
    return sdl.build(s)


def convert_doors():
    return convert_kobj(DOORS_KOWARE[1], 3, 3)


def edit_kod(d):
    ver, n = struct.unpack_from('<fI', d, 0)
    rows = [struct.unpack_from('<4BH', d, 8 + 6 * i) for i in range(n)]
    assert len(d) == 8 + 6 * n and DOORS_KOD[:2] not in [r[:2] for r in rows], rows
    assert DOORS_KOD[2] not in [r[2] for r in rows if r[3] == 0]
    if 'static-doors' in KEEP:
        return d, 'kod unchanged (--keep-static-doors)'
    rows.append(DOORS_KOD)
    return (struct.pack('<fI', ver, len(rows)) + b''.join(struct.pack('<4BH', *r) for r in rows),
            'kod + %s (doors KowareObj, 4U type-0 state entry)' % (DOORS_KOD,))


GIMMICK_EDITS[('table\\stage\\kowareObjData\\m26d', T_KOD)] = edit_kod


def hide_koware(d):
    import sdl
    s = sdl.parse(d)
    for i, name, cls, tr in sdl.objects(s):
        if cls == 0x167df530:                       # uKowareModel
            if 'mOffset' in tr:
                sdl.set_values(s, tr['mOffset'], [(x, y - 50000.0, z) for x, y, z, w in sdl.values(s, tr['mOffset'])])
            if 'Draw' in tr:
                sdl.set_values(s, tr['Draw'], [0] * len(tr['Draw']['times']))
        if cls == 0x3dfe3bc2 and 'mAtRadius' in tr:  # uKowareObj: no attack sphere
            sdl.set_values(s, tr['mAtRadius'], [0.0] * len(tr['mAtRadius']['times']))
    return sdl.build(s)


def build_stage_arc(report):
    import sdl
    ver, ents = arcpack.read(open(os.path.join(GUX, 'arc', 'stage', 'm26d', 'm26d.arc'), 'rb').read())
    byp = {(p, t): d for p, t, d in ents}
    rows = []
    replaced = set(); inserts = {}
    for gsdl, usdl in (KOWARE_4U.items() if 'koware' not in KEEP else ()):
        gs = sdl.parse(byp[(gsdl, T_SDL)])
        replaced |= set(sdl.resource_paths(gs))
        mid = [sdl.values(gs, tr['mId'])[0] for i, n, c, tr in sdl.objects(gs) if c == 0x3dfe3bc2][0]
        new = sdl.convert_4u(u4_find(usdl, T_SDL), drop_ctrl=lambda c, n: c in (EFFECT_CTRL, SOUND_CTRL),
                             drop_obj=lambda c, cat, n: c == KOWARE_MODEL and cat == 9, drop_keyless=True)
        ns = sdl.parse(new)
        for i, n, c, tr in sdl.objects(ns):
            if c == 0x3dfe3bc2: sdl.set_values(ns, tr['mId'], [mid] * len(tr['mId']['times']))
        new = sdl.build(ns)
        models = []
        for p in sdl.resource_paths(ns):
            pm, pr, pt, prow = convert_prop(p)
            models.append((p, pr, pm, pt))
        inserts[gsdl] = (new, models)
        rows.append((gsdl, usdl, 'mId %d' % mid, [m[0] for m in models]))
    extra = []                                  # new kobj schedulers: [(GU path, GU sdl, models)]
    news = []
    if 'static-doors' not in KEEP:
        news.append((DOORS_KOWARE[0], DOORS_KOWARE[1], convert_doors(), 'mId 3 (doors / wall KowareObj, new slot)'))
    if 'static-cannons' not in KEEP:
        for gpath, upath, mid, nse in CANNONS_KOWARE:
            news.append((gpath, upath, convert_kobj(upath, mid, nse), 'mId %d (floor cannon KowareObj)' % mid))
    if 'gate' not in KEEP:
        gpath, upath, mid, nse = GATE_KOWARE
        news.append((gpath, upath, convert_kobj(upath, mid, nse, drop_cls=(SCROLL_SBC,), new_mid=GATE_MID),
                     'mId %d -> %d (Demolisher gate KowareObj, ScrollCollisionSbc dropped)' % (mid, GATE_MID)))
    for gpath, upath, new, what in news:
        models = []
        for p in sdl.resource_paths(sdl.parse(new)):
            pm, pr, pt, prow = convert_prop(p)
            models.append((p, pr, pm, pt))
        extra.append((gpath, new, models))
        rows.append((gpath, upath, what, [m[0] for m in models]))
    doors = extra or None
    item = None
    if 'items' not in KEEP:                     # the 4U pile meshes under the Fortress item-model path (ITEM_MODEL)
        pm, pr, pt, prow = convert_prop(ITEM_MODEL[1])
        item = (regroup_model(pm, ITEM_GROUPS), pr, pt)
        replaced.add(ITEM_MODEL[0])
        rows.append((ITEM_MODEL[0], ITEM_MODEL[1], 'groups %s' % ITEM_GROUPS, pt))
    keep = set(); old_tex = set()
    for p, t, d in ents:
        if t == T_MRL: (old_tex if p in replaced else keep).update(mrl_textures(d))
    drop = old_tex - keep
    out = []; done_tex = set()
    for p, t, d in ents:
        if t == T_TEX and p in drop: continue
        if item and p == ITEM_MODEL[0] and t == T_MRL:
            mm, mr, mt = item
            for tp in mt:
                if tp not in done_tex: out.append((tp, T_TEX, convert_texture(tp))); done_tex.add(tp)
            out += [(p, T_MRL, mr), (p, T_MOD, mm)]
            continue
        if p in replaced and t in (T_MOD, T_MRL): continue
        if t == T_SDL and p in inserts:
            new, models = inserts[p]
            for mp, mr, mm, mt in models:
                for tp in mt:
                    if tp not in done_tex: out.append((tp, T_TEX, convert_texture(tp))); done_tex.add(tp)
            for mp, mr, mm, mt in models:
                if (mp, T_MOD) not in {(e[0], e[1]) for e in out}: out += [(mp, T_MRL, mr), (mp, T_MOD, mm)]
            out.append((p, T_SDL, new))
        else:
            if t == T_SDL and p in KOWARE_HIDE and 'koware' not in KEEP:
                d = hide_koware(d); rows.append((p, 'hidden (models -50000, Draw 0, mAtRadius 0)'))
            if t == T_STQR:
                d, what = bgm_stqr(d); rows.append((p, what))
            out.append((p, t, d))
        if doors and t == T_SDL and p == 'stage\\m26d\\m26a02d\\sdl\\m26a02d-k02':
            for gpath, new, models in doors:    # models (TEX -> MRL -> MOD) before the scheduler that names them
                have = {(e[0], e[1]) for e in out}
                for mp, mr, mm, mt in models:
                    for tp in mt:
                        if (tp, T_TEX) not in have and tp not in done_tex:
                            out.append((tp, T_TEX, convert_texture(tp))); done_tex.add(tp)
                have = {(e[0], e[1]) for e in out}
                for mp, mr, mm, mt in models:
                    if (mp, T_MOD) not in have: out += [(mp, T_MRL, mr), (mp, T_MOD, mm)]
                out.append((gpath, T_SDL, new))
            doors = None
    assert doors is None, 'k02 scheduler not found for the kobj inserts'
    report['stage_arc'] = rows
    return out


# ------------------------------------------------------------------ area streams (BGM) hookup
# rSoundStreamRequest "STQR" `sound\bgm\map\m26d\bgm_m26d` (in m28d.arc): u32 'STQR', u32 8, u32 nStreams (4 =
# areas 0..3), u32 nSequences, 16 zero, u32 stream table offset (0x38), u32 sequence table offset, ...; stream entry
# 36 B {u32 path offset, u32 file size, u32 samples, u32 channels, u32 rate, u32 loopStart, u32 loopEnd, u32
# 0x15542770, u32 0}; paths `sound\bgm\map\m26d\wav\m26a0Nd` = loose nativeNX/sound/bgm/map/m26d/wav/*.opus.
# The sound agent's converted 4U streams are picked up from BGM_JSON when it exists:
#   [{"stream": 0..3, "samples": n, "channels": c, "rate": r, "loop_start": a, "loop_end": b}, ...] with the opus at
#   monsters/gogmazios/romfs/nativeNX/sound/bgm/map/m28d/wav/m28a0<stream>d.opus; listed streams get the m28d path
#   (same string length), the others keep the Fortress stream.
T_STQR = 0x167dbbff
BGM_JSON = os.path.join(ROOT, 'dump', 'converted', 'bgm_m28.json')
BGM_DIR = os.path.join(paths.romfs('gogmazios'), 'nativeNX', 'sound', 'bgm', 'map', 'm28d', 'wav')


BGM_STQR = os.path.join(ROOT, 'dump', 'converted', 'bgm_m28d.stqr')   # sound agent's full replacement (preferred):
# streams 0..2 = m28d/wav/m28a0{0,1,2}d, 3 = Fortress m26a03d, 4 = m28cmpd (4U stage jingle bgm_map_19, sequence 0x32)


def bgm_stqr(d):
    if os.path.exists(BGM_STQR) and 'sound' not in KEEP:
        r = open(BGM_STQR, 'rb').read()
        assert r[:4] == b'STQR' and struct.unpack_from('<I', r, 4)[0] == 8, r[:8]
        return r, 'replaced by %s (%d streams)' % (os.path.relpath(BGM_STQR, ROOT), struct.unpack_from('<I', r, 8)[0])
    if not os.path.exists(BGM_JSON):
        return d, 'Fortress streams kept (no %s yet)' % os.path.relpath(BGM_JSON, ROOT)
    b = bytearray(d)
    assert b[:4] == b'STQR' and struct.unpack_from('<I', b, 4)[0] == 8, b[:8]
    n = struct.unpack_from('<I', b, 8)[0]
    tab = struct.unpack_from('<I', b, 0x20)[0]
    done = []
    for s in json.load(open(BGM_JSON)):
        k = s['stream']; assert 0 <= k < n, k
        e = tab + 36 * k
        po = struct.unpack_from('<I', b, e)[0]
        old = b[po:b.index(b'\0', po)].decode('ascii')
        new = old.replace('m26d', 'm28d').replace('m26a', 'm28a')
        assert len(new) == len(old) and new.endswith('m28a%02dd' % k), (old, new)
        opus = os.path.join(BGM_DIR, 'm28a%02dd.opus' % k)
        b[po:po + len(new)] = new.encode('ascii')
        struct.pack_into('<7I', b, e, po, os.path.getsize(opus), s['samples'], s['channels'], s['rate'],
                         s['loop_start'], s['loop_end'])
        done.append(new)
    return bytes(b), 'streams -> %s' % done


def alias(outroot):
    report = {}
    sdir = os.path.join(outroot, 'nativeNX', 'arc', 'stage', 'm28d')
    os.makedirs(sdir, exist_ok=True)
    for area in ('a00', 'a01', 'a02', 'a03'):
        ents = build_area(area, report)
        open(os.path.join(sdir, area + '.arc'), 'wb').write(arcpack.build(ents))
        print('built', area, len(ents), 'entries', flush=True)
    # stage-wide arc: Fortress copy with the breakables replaced / hidden. map_com: Fortress copy with the area
    # collision + area info converted from 4U m19 and the gimmick shell params edited (cameras, nav, gimmick
    # collision m26d-etc stay Fortress's)
    dp = os.path.join(outroot, 'nativeNX', 'arc', 'stage', 'm28d', 'm28d.arc')
    ents = build_stage_arc(report)
    open(dp, 'wb').write(arcpack.build(ents))
    for r in report['stage_arc']: print('  stage arc', *r)
    print('built arc/stage/m28d/m28d.arc', len(ents), 'entries')
    dp = os.path.join(outroot, 'nativeNX', 'loc', 'arc', 'stage', 'map_com', 'm28.arc')
    os.makedirs(os.path.dirname(dp), exist_ok=True)
    ents = build_map_com(report)
    open(dp, 'wb').write(arcpack.build(ents))
    for r in report['collision']: print('  collision', *r)
    print('built loc/arc/stage/map_com/m28.arc', len(ents), 'entries')
    json.dump(report, open(os.path.join(ROOT, 'dump', 'stage_alias_report.json'), 'w'), indent=1)
    print('report: dump/stage_alias_report.json')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'mod':
        srcs = [open(p, 'rb').read() for p in [sys.argv[2]] + sys.argv[4:]]
        out, mats = convert_models([(d, '' if i == 0 else '_%d' % i) for i, d in enumerate(srcs)])
        open(sys.argv[3], 'wb').write(out)
        check_model(out, srcs)
    elif cmd == 'alias':
        args = [a for a in sys.argv[2:] if not a.startswith('--keep-')]
        KEEP.update(a[7:] for a in sys.argv[2:] if a.startswith('--keep-'))
        assert KEEP <= {'sets', 'filters', 'gimmicks', 'koware', 'sound', 'relation', 'doors', 'cart',
                        'static-doors', 'static-cannons', 'items', 'camera', 'gate'}, KEEP
        alias(args[0] if args else paths.romfs('gogmazios'))
    else:
        raise SystemExit(__doc__)
