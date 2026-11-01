"""build_em005_01_arc.py : build nativeNX/arc/enemy/em005_01.arc (Black Gravios = GU Gravios variant 1, ID 0x105) + its
data file section FILE.

  build_em005_01_arc.py      build, verify, then write (paths in monsters/black_gravios/):
      romfs/nativeNX/arc/enemy/em005_01.arc
      tools/em005_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em057_04): the variant's own files under enemy\\em005\\em005_01\\..., the files it shares
with variant 0 under em005_00's paths and file IDs. GU's class uEm004_00 runs it (variant byte 1, notes/plan.md).
4U runs Black Gravios on Gravios' class and files (C, 2026-10-31): em041.arc ships em040's motions, camera, AI, sound
call (em038) and effects byte for byte as em040.arc does; em041's attackdata, hitsize and bodydata equal em040's. Only
its models and tuning are its own. So:
  own, converted from MH4U em041.arc:
      mod\\em005_01 (+ _tail) MOD + MRL    tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py)
      mod\\em005_01_NN_BM (+A)             albedo (BC3) + GU specular map from its alpha (4U has no normal maps)
      mod\\em005_01 XFS                    GU em005_00's parts states for em041's mesh groups
      dt_tune\\em005_01_dttune             GU em005_00's with 4U em041's values where 4U em040 and em041 differ
                                           (GU's own AI distance ranges kept: em040's and em041's are equal)
      hagi\\hagi_s0..s4_em005_01           carves: 4U High tables in s2, G in s4, GU's filler in s0 / s1 / s3
                                           (tools/hagi_em005_01.py)
  shared, GU em005_00 (original paths + file IDs): motions, camera, command table, sound, effects (PEL / PSL), shells,
      attack / hit / body / cambody data, dtbase, dtbparts, dou mou ka, area data (maps 7 8 12 13 24: the Volcanic
      Hollow of its quests is map 12).
Known deviations (later steps, notes/plan.md): em041's own effects (MEF em041_1, EFLs em041_002 / em041_101, effect
model ef_em041) are not in yet, GU Gravios' effects play; the 4U emd word-32
colour table (em041's darker part colours) has no known GU field.
Inputs besides the arcs: dump/converted/em041/dt_em040/ and dt_em041/ (build.sh step dt: tools/dt_convert.py, donor
em005_00).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/black_gravios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, emdata4u, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, tex

NAME = 'black_gravios'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em041.arc')
SRC_4U_GRAVIOS = os.path.join(ROOT, 'dump/romfs/data/em040.arc')
GU_ARC = '/nativeNX/arc/enemy/em005_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em005_01.arc')
OUT_JSON = os.path.join(HERE, 'em005_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, XFS=0x7CD0E77E)
P4 = 'enemy\\em041\\'            # 4U Black Gravios' own paths
P0 = 'enemy\\em005\\em005_00\\'  # GU variant 0
P = 'enemy\\em005\\em005_01\\'   # ours
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 1, 3, 33, 46, 47, 48, 49, 50]
DT_DIR = os.path.join(ROOT, 'dump/converted/em041')           # build.sh step dt
MODELS = (('em041', 'em005_01', 0), ('em041_tail', 'em005_01_tail', 1))    # 4U name, ours, manifest field
# Material type (MRL w6 bits 21-28) = the 'mNN' of the 4U name: GU em005_00's materials carry the same names as 4U
# em041's (body m00 -> 0, add m01 -> 1, eye m02 -> 2, damage / wing m50 -> 50, tail m00 -> 0; C, 2026-10-31).
MTYPE = {}
# 4U group 50 (both em040 and em041) is not in GU's model, so no GU state names it: hidden in the base state, as GU
# Gravios never shows it. em041 has no group 19 (em040 and GU em005_00 do): its GU states drop it.
HIDDEN_GROUPS = (50,)
# dttune AI distance ranges (tools/dt_convert.py RANGES): 4U etd word 10 rows (16 B, closed by an all -1 row) and
# word 11 offsets (12 B per row, zeros when absent), written by the conversion in that order (dttune())
RANGE_WORDS = (10, 11)
# 4U etd blocks em041 changes that dt_convert does not convert: word -> offset of its 12-byte block in GU em005_00's
# dttune (C, 2026-11-01: its first 6 bytes = 4U em040's, the last 6 GU-retuned; checked by unconverted_blocks)
UNCONV_AT = {24: 0x358}


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def model(S, rom, src_name, dst_name, gu_tex, notes):
    """one em041 MOD + MRL (+ the textures it is the first to use) -> [(path, type, data)], the parsed 4U MOD.
    Templates as tigerstripe_zamtrios/tools/build_em067_01_arc.py: blended -> 'add', emissive (4U CBMaterialStd
    emission > 0, diffuse 0) -> 'unlit', else the lit 'solid'; a lit 4U 'E0' material with a tExtendMap (em041_03_BM,
    the sphere-map lighting texture GU em005_00 also binds as tSphereMap) -> 'solid_sphere'. MRL before MOD, as in GU's
    arcs: a model fetches its materials by path while it loads."""
    src = P4 + 'mod\\' + src_name
    d4 = S[(src, T['MOD'])]
    m4, r4 = modlib.parse(d4), mrl.read(S[(src, T['MRL'])])
    out, tex_paths, tex_index, mats = [], [], {}, []

    def gu_path(src_tex, spec):
        """GU path of a 4U texture, converted on first use: albedo -> BC3 + its '+A' specular map (the BM alpha, the
        4U specular mask, in R, G, B; alpha 255); other maps -> BC3 as they are"""
        if src_tex not in gu_tex:
            t = tex.decode(S[(src_tex, T['TEX'])])
            path = P + 'mod\\em005_01_' + src_tex.split('em041_')[-1]
            out.append((path, T['TEX'], tex.encode_gu(t, 'bc3')))
            if spec:
                s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
                out.append((path + '+A', T['TEX'], tex.encode_gu(s, 'bc3')))
            gu_tex[src_tex] = path
        return gu_tex[src_tex]

    def slot(path):
        if path not in tex_index:
            tex_paths.append(path); tex_index[path] = len(tex_paths)
        return tex_index[path]

    for mname in m4['material_names']:
        mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
        assert len(mm) == 1, (src_name, mname)
        mm = mm[0]
        states = [s for s in mm['states'] if s]
        albedo = r4['textures'][[v for n, t, v in mm['params'] if n == 'tAlbedoMap'][0] - 1][1]
        a = gu_path(albedo, True)
        slots = {'tAlbedoMap': slot(a), 'tSpecularMap': slot(a + '+A')}
        std = struct.unpack_from('<8f', mm['block'], 0x60)       # emission rgba, diffuse rgba
        key = 'add' if 'BSAddAlpha' in states or 'BSBlendAlpha' in states else \
              'unlit' if max(std[0:3]) > 0 and max(std[4:7]) == 0 else 'solid'
        ext = [v for n, t, v in mm['params'] if n == 'tExtendMap' and v]
        consts = {}
        if key == 'solid' and ext:
            key = 'solid_sphere'
            slots['tSphereMap'] = slot(gu_path(r4['textures'][ext[0] - 1][1], False))
            # 4U CBMaterialStd albedo / diffuse / emission (mrl_anim.static_constants), specular a neutral 0.5, as
            # Tigerstripe's solid_sphere materials (its diffuse alpha is 0 on these opaque 4U materials: not taken)
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            consts = {k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], 1.0).items()
                      if k in (('$Globals', 'fAlbedoColor'), ('CBMaterial', 'fDiffuseColor'), ('$Globals', 'fEmissionColor'))}
            consts[('$Globals', 'fSpecularColor')] = (0.5, 0.5, 0.5)
        extra = dict(mtype=MTYPE.get(mname, int(re.search(r'_m(\d\d)_', mname).group(1))),
                     bias=(mm['words'][7] >> 16) & 0xF)
        mats.append((mname, key, slots, [s for s in states if s.startswith('RS')], consts, extra))
        notes.append('%s material %s: template %s, type %d, %s' % (
            dst_name, mname, key, extra['mtype'], {s: tex_paths[v - 1].split('\\')[-1] for s, v in slots.items()}))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(P + 'mod\\' + dst_name, T['MRL'], mrl_bytes), (P + 'mod\\' + dst_name, T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(gu_xfs, groups, notes):
    """GU em005_00's parts states (rMonsterPartsManager XFS) for em041's mesh groups. 4U em041's visibility rows are
    em040's (their emd files differ only in the word-32 colour table, C), and GU's states name the same group numbers
    (GU's model = em040's groups minus 50)."""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    unnamed = sorted(set(groups) - {g for st in states for g, _ in st} - set(HIDDEN_GROUPS))
    assert not unnamed, 'em041 groups without a GU state: %s' % unnamed
    kept[0] += [(g, 0) for g in HIDDEN_GROUPS if g in groups]
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted({g for st in states for g, _ in st} - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in em041): %s, hidden at spawn: %s' % (
        len(kept), dropped, list(HIDDEN_GROUPS)))
    return bytes(head) + data


def shared_4u(S, notes):
    """assert what lets every non-model file stay GU Gravios': em041.arc's em040 / em038 files equal em040.arc's, and
    the 4U attack / hit / body data of em040 and em041 are equal"""
    _, s40 = arcpack.read(open(SRC_4U_GRAVIOS, 'rb').read())
    g40 = {(p, t): d for p, t, d in s40}
    shared = [(k, d) for k, d in S.items() if 'em040' in k[0] or 'em038' in k[0]]
    assert shared and all(g40.get(k) == d for k, d in shared), 'em041.arc no longer ships em040.arc\'s files'
    own = sorted({p for p, t in S if 'em041' in p})
    d40, d41 = emdata4u.load_4u('em040'), emdata4u.load_4u('em041')
    for name, conv in (('attackdata', lambda d: emdata4u.attackdata(d['etd'])),
                       ('hitsize', lambda d: emdata4u.hitsize(d['etd'])),
                       ('bodydata', lambda d: emdata4u.bodydata(d['emd'], 8))):
        assert conv(d40) == conv(d41), name + ' of em040 and em041 differ: convert it too'
    notes.append('4U em041.arc: %d files = em040.arc\'s (motions, camera, AI, sound call, effects), own: %s; '
                 'attackdata / hitsize / bodydata = em040\'s' % (len(shared), own))


def range_rows(em):
    """4U AI distance range rows of em (etd word 10 up to its all -1 row) + its word 11 offsets (None when absent)"""
    import dt_convert
    u = emdata4u.load_4u(em)['etd']
    p, q = (dt_convert.block_at(u, 'etd', w) for w in RANGE_WORDS)
    rows = []
    while struct.unpack_from('<4f', u, p) != (-1.0,) * 4:
        rows.append(u[p:p + 16]); p += 16
    return b''.join(rows), (u[q:q + 12 * len(rows)] if q is not None else None)


def dttune(gu, notes):
    """GU em005_00's dttune with 4U em041's values where tools/dt_convert.py gives em040 != em041 (C, 2026-11-01).
    The conversions write the 4U range rows + offsets (RANGE_WORDS) at R; before R they line up with GU's file: GU's is
    the em040 conversion at 50 of the 51 differing bytes (the 51st, +0x0f = 17, is the record count GU shares with
    em041's layout). GU keeps its own ranges there (not 4U's rows; em040's and em041's are equal, so they do not tell
    Black Gravios apart), and after them GU's file ends with the em041 conversion's tail (its 17-record block)."""
    c40 = open(os.path.join(DT_DIR, 'dt_em040', 'dttune.bin'), 'rb').read()
    c41 = open(os.path.join(DT_DIR, 'dt_em041', 'dttune.bin'), 'rb').read()
    (rows, offs), r41 = range_rows('em040'), range_rows('em041')
    assert (rows, offs) == r41, '4U range rows of em040 and em041 differ: port them too'
    R = c41.find(rows)
    assert R > 0 and c40.find(rows) == R, 'range rows not at the same offset in both conversions'
    tail = c41[R + len(rows) + 12 * (len(rows) // 16):]
    assert gu.endswith(tail), 'GU dttune does not end with the em041 conversion past the ranges'
    delta = [i for i in range(R) if c40[i] != c41[i]]
    assert all(gu[i] in (c40[i], c41[i]) for i in delta), 'GU dttune holds neither 4U value at a differing byte'
    retuned = [i for i in range(R) if gu[i] != c41[i] and c40[i] == c41[i]]
    out = bytearray(gu)
    for i in delta: out[i] = c41[i]
    notes.append('dttune: GU em005_00 + %d bytes of 4U em040 -> em041 differences before the ranges at +%#x (%d were '
                 'em040\'s in GU); GU\'s own ranges (+%#x..+%#x) and bytes %s kept; tail = em041 conversion (%d bytes)'
                 % (len(delta), R, sum(gu[i] == c40[i] != c41[i] for i in delta), R, len(gu) - len(tail),
                    [hex(i) for i in retuned], len(tail)))
    unconverted_blocks(out, notes)
    return bytes(out)


def unconverted_blocks(out, notes):
    """4U etd blocks where em041 differs from em040 that tools/dt_convert.py does not convert (it only gates them,
    ABSENT): word 24 (dttune +0xb4, 12 B: u16 150 + 5 pairs of u8, falling per pair; role G: the durations of a
    repeated condition such as a trap or flash). GU em005_00 holds it at UNCONV_AT[24] in 4U's layout (C: its first 6
    bytes = 4U em040's, the last 6 GU-retuned). Rule as dttune(): a byte GU kept from em040 takes em041's value, a
    GU-retuned byte is scaled by em041 / em040 (rounded)."""
    d40, d41 = emdata4u.load_4u('em040')['etd'], emdata4u.load_4u('em041')['etd']
    for w, at in UNCONV_AT.items():
        p = struct.unpack_from('<I', d40, 4 * w)[0]
        assert p == struct.unpack_from('<I', d41, 4 * w)[0]
        a, b, n = d40[p:p + 12], d41[p:p + 12], 12
        g = out[at:at + n]
        assert g[:2] == a[:2] == b[:2], ('etd word %d header' % w, g.hex(), a.hex())
        new = bytearray(g)
        for i in range(2, n):
            new[i] = b[i] if g[i] == a[i] else int(g[i] * b[i] / a[i] + 0.5)
        out[at:at + n] = new
        notes.append('dttune +%#x (4U etd word %d, not converted by dt_convert): %d bytes set to em041\'s, %d scaled '
                     'from GU\'s retune' % (at, w, sum(g[i] == a[i] != b[i] for i in range(2, n)),
                                            sum(g[i] != a[i] for i in range(2, n))))


def main():
    img = open(paths.GU_MAIN, 'rb').read()
    rom = RomFS(paths.GU_ROMFS)
    _, src = arcpack.read(open(SRC_4U, 'rb').read())
    S = {(p, t): d for p, t, d in src}
    _, gents = arcpack.read(rom.read(GU_ARC))
    notes = []
    ghash = {(phash(p), t): (p, t) for p, t, _ in gents}
    gman = manifest_of(img, ALLOC['donor_index'])
    G = {(p, t): d for p, t, d in gents}
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em005_00's file of manifest field k
    shared_4u(S, notes)

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    m4 = None
    for src_name, dst_name, field in MODELS:
        files, m = model(S, rom, src_name, dst_name, gu_tex, notes)
        ents += files
        own[field] = (P + 'mod\\' + dst_name, T['MOD'])
        m4 = m4 or m
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em005_01', T['XFS'], parts_xfs(gfile(3), groups, notes)))
    own[3] = (P + 'mod\\em005_01', T['XFS'])
    typ = ghash[fileid_entry(img, gman[33])][1]
    ents.append(('enemy\\dt_tune\\em005_01_dttune', typ, dttune(gfile(33), notes)))
    own[33] = ('enemy\\dt_tune\\em005_01_dttune', typ)
    sys.path.insert(0, HERE)
    import hagi_em005_01                 # carves: 4U High tables in s2, G in s4, GU's filler in s0 / s1 / s3
    for k, data in hagi_em005_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em005_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    notes.append('carves: 4U em041 High / G tables in hagi s2 / s4 (tools/hagi_em005_01.py)')

    # ---- the shared GU em005_00 files: everything but what ours replace and em005_00's model (MOD, MRL, textures)
    replaced = {ghash[fileid_entry(img, gman[k])] for k in own if gman[k] != -1}
    drop = replaced | {(p, t) for p, t, _ in gents if p.startswith(P0 + 'mod\\')}
    while True:                                  # a file a kept one names by path stays
        kept = [(p, t, d) for p, t, d in gents if (p, t) not in drop]
        named = {(p, t) for p, t in drop if any(p.encode('ascii') in kd for _, _, kd in kept)}
        if not named: break
        for p, t in sorted(named):
            notes.append('kept %s although replaced: named by %s' % (p, [kp for kp, _, kd in kept
                                                                         if p.encode('ascii') in kd][:4]))
        drop -= named
    ents += kept
    notes.append('shared from em005_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em005_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U em041)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em005_00, its file ID)'

    # ---- verify before writing anything
    arc = arcpack.build(ents)
    ver, back = arcpack.read(arc)
    assert ver == 0x11 and len(back) == len(ents)
    assert len({(p, t) for p, t, _ in back}) == len(back), 'duplicate entries'
    present = {(phash(p), t) for p, t, _ in back}
    for fid, p, t in new_files:
        assert (phash(p), t) in present, p
    for k in range(51):
        if manifest[k] != -1 and manifest[k] < FILE_ID_BASE:
            assert fileid_entry(img, manifest[k]) in present, (k, hex(manifest[k]))
    for p, t, d in back:
        if p.startswith(P) and t == T['MOD']: modlib.parse(d)
        if p.startswith(P) and t == T['TEX']: tex.decode(d)

    # ---- write
    os.makedirs(os.path.dirname(OUT_ARC), exist_ok=True)
    open(OUT_ARC, 'wb').write(arc)
    fields = []
    for k in range(51):
        fid = manifest[k]
        if fid == -1:
            fields.append(dict(field=k, file_id=-1)); continue
        p, t = new_files[fid - FILE_ID_BASE][1:] if fid >= FILE_ID_BASE else ghash[fileid_entry(img, fid)]
        fields.append(dict(field=k, file_id='0x%x' % fid, path=p, type='0x%08x' % t, source=src_of[k]))
    json.dump(dict(monster='em005_01 (Black Gravios)', id='0x%x' % ALLOC['em_id'],
                   registry_index=ALLOC['registry_index'], file_id_base='0x%x' % FILE_ID_BASE,
                   file_count=len(new_files), manifest=fields,
                   files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p))
                          for f, p, t in new_files], notes=notes), open(OUT_JSON, 'w'), indent=1)
    # FILE section: the registry manifest of its index and the (path hash, type) of each of our file IDs
    sec = portdata.Section('FILE')
    sec.u32(FILE_ID_BASE, len(new_files), *[x & 0xFFFFFFFF for x in manifest])
    for fid, p, t in new_files:
        sec.u32(phash(p), t)
    print('wrote', portdata.write_section(NAME, sec))
    print('arc: %d entries, %.1f MB -> %s' % (len(ents), len(arc) / 1e6, OUT_ARC))
    print('own file IDs 0x%x..0x%x (%d)' % (FILE_ID_BASE, FILE_ID_BASE + len(new_files) - 1, len(new_files)))
    for n in notes: print(' ', n)


if __name__ == '__main__':
    main()
