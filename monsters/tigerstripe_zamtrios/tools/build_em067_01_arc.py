"""build_em067_01_arc.py : build nativeNX/arc/enemy/em067_01.arc (Tigerstripe Zamtrios = GU Zamtrios variant 1,
ID 0x143) + its data file section FILE.

  build_em067_01_arc.py      build, verify, then write (paths in monsters/tigerstripe_zamtrios/):
      romfs/nativeNX/arc/enemy/em067_01.arc
      tools/em067_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em001_02.arc): the variant's own files under enemy\\em067\\em067_01\\..., the files it
shares with variant 0 under em067_00's paths and file IDs, so the arc works alone and shares those resources with an
em067_00 in the same quest. GU's class uEm067_00 runs it (variant byte 1, notes/phase1-variant-map.md).
  own, converted from MH4U em092.arc:
      mod\\em067_01 MOD + MRL       tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py)
      mod\\em067_01_NN_BM (+A)      albedo textures (BC3) + GU specular maps made from their alpha
      mod\\em067_01 XFS             GU em067_00's 33 parts states, kept for em092's mesh groups
      mot\\em067_01_0/2/3/4         4U motion lists (LMT 67, unchanged): GU's variant-1 code asks for em092's motions
      mot\\em067_01_cam             4U camera list (tools/lcm4u2gu.py)
      cmd_tbl\\em067_01_cmdtbl      4U command table + GU's extra selector / area-move scripts (cmdtbl())
      effects                       tools/efl4u2gu.py effect_set: em092's EFLs (+ the qe families its MEF names) under
                                    their 4U paths, PEL u list 1 from its MEF (the 4U ids its motions' PSLs name), list
                                    2 = GU em067_00u's (GU's class posts GU ids), PSL per motion list from its LMTs;
                                    area colour = the Dunes' (its 4U quests' stage 17)
      body_data\\em067_01_bodydata   GU em067_00's minus the 2 records 4U em092 drops from em022's (bones 142, 131)
      dt_tune\\em067_01_dttune       GU em067_00's + the bytes where tools/dt_convert.py gives em092 != em022
      sound call / waves / bank / request   tools/snd4u2gu.py monster_entries (see sound())
      hagi\\hagi_s0..s4_em067_01    carves: 4U G body / shiny tables in s4, GU's filler in s0..s3 (tools/hagi_em067_01.py)
  shared, GU em067_00 (original paths + file IDs): sound triggers (PTS c / u), PEL c, shell arc, attack data, hitsize,
      cambodydata, dtbase, dtbparts, area data: 4U em022 and em092 convert to the same attack / hit / cambody / dtbase
      data (checked 2026-10-20), so GU's own tuning of them stays.
Inputs besides the arcs: dump/converted/em092/dt_em022/ and dt_em092/ (build.sh step dt: tools/dt_convert.py in the
MHGU_Editor venv, donor em067_00) and the 4U ROM (core effect arcs, Dunes area colours).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tigerstripe_zamtrios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, ctr, efl4u2gu, emc, emdata4u, lcm4u2gu, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, \
    mrl_build, portdata, snd4u2gu, tex

NAME = 'tigerstripe_zamtrios'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em092.arc')
GU_ARC = '/nativeNX/arc/enemy/em067_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em067_01.arc')
OUT_JSON = os.path.join(HERE, 'em067_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02,
         LCM=0x39C52040)
P4 = 'enemy\\em092\\'            # 4U source paths
P0 = 'enemy\\em067\\em067_00\\'  # GU variant 0
P = 'enemy\\em067\\em067_01\\'   # ours
BANKS = (0, 2, 3, 4)             # motion lists of em092 and em067_00 (neither has list 1): manifest field 4 + bank
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 3, 4, 6, 7, 8, 11, 37, 17, 18, 20, 21, 22, 30, 33, 12, 13, 46, 47, 48, 49, 50, 26, 40, 41, 42, 43, 44]
DT_DIR = os.path.join(ROOT, 'dump/converted/em092')           # build.sh step dt
PEL_U = 'effect\\pel\\em\\em067_01u'
PSL = 'effect\\psl\\enemy\\em067\\em067_01\\mot\\em067_01_%d'
BODYDATA_DROP = {12: 142, 13: 131}  # em022 / GU bodydata record -> its bone A: the records em092 does not have
# Material type (MRL w6 bits 21-28) = the 'mNN' of the 4U name, except the fat body: GU renamed Zamtrios'
# 'XfB__E0__m00_fatbig' (4U em022 and em092) to 'XfB__E0__m01_fatbig' (em067_00 MRL w6 type 1; its other types
# follow the names: body 0, eye 2), so GU's class may address it by type 1 (S: not traced in the code).
MTYPE = {'XfB__E0__m00_fatbig': 1}
# 4U group 50 (eye + m03_virs material; 4U row: shown only while condition 10 holds) is not in GU's model, so no GU
# state names it: hidden in the base state, as GU Zamtrios never shows it.
HIDDEN_GROUPS = (50,)


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def model(S, rom, notes):
    """em092 MOD + MRL + textures -> [(path, type, data)], the parsed 4U MOD. MRL before MOD, as in GU's arcs: a model
    fetches its materials by path while it loads (a MOD packed first loads without them: em089 test 2026-10-17)."""
    src = P4 + 'mod\\em092'
    d4 = S[(src, T['MOD'])]
    m4, r4 = modlib.parse(d4), mrl.read(S[(src, T['MRL'])])
    out, gu_tex, tex_paths, tex_index, mats = [], {}, [], {}, []
    for mname in m4['material_names']:
        mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
        assert len(mm) == 1, mname
        mm = mm[0]
        states = [s for s in mm['states'] if s]
        albedo = [v for n, t, v in mm['params'] if n == 'tAlbedoMap'][0]
        src_tex = r4['textures'][albedo - 1][1]
        if src_tex not in gu_tex:
            # GU specular map '<BM>+A' = the BM alpha (4U specular mask) in R, G, B, alpha 255 (build_em089_arc.py)
            t = tex.decode(S[(src_tex, T['TEX'])])
            s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
            path = P + 'mod\\em067_01_' + src_tex.split('em092_')[-1]
            out += [(path, T['TEX'], tex.encode_gu(t, 'bc3')), (path + '+A', T['TEX'], tex.encode_gu(s, 'bc3'))]
            gu_tex[src_tex] = path
        slots = {}
        for slot, gp in (('tAlbedoMap', gu_tex[src_tex]), ('tSpecularMap', gu_tex[src_tex] + '+A')):
            if gp not in tex_index:
                tex_paths.append(gp); tex_index[gp] = len(tex_paths)
            slots[slot] = tex_index[gp]
        # template as em089's: blended -> 'add', emissive (4U CBMaterialStd emission > 0, diffuse 0) -> 'unlit',
        # else the lit 'solid' (em092 has no normal map). A lit 4U 'E0' material with a tExtendMap (body em092_05,
        # fat body em092_07: sphere-map lighting textures) -> 'solid_sphere' with it as tSphereMap, as Capcom's
        # converted 4U monsters (mrl_build notes); test 2026-10-21: the plain 'solid' left the puffed belly black.
        std = struct.unpack_from('<8f', mm['block'], 0x60)
        key = 'add' if 'BSAddAlpha' in states or 'BSBlendAlpha' in states else \
              'unlit' if max(std[0:3]) > 0 and max(std[4:7]) == 0 else 'solid'
        ext = [v for n, t, v in mm['params'] if n == 'tExtendMap' and v]
        consts = {}
        if key == 'solid' and ext:
            key = 'solid_sphere'
            ext_tex = r4['textures'][ext[0] - 1][1]
            if ext_tex not in gu_tex:
                path = P + 'mod\\em067_01_' + ext_tex.split('em092_')[-1]
                out.append((path, T['TEX'], tex.encode_gu(tex.decode(S[(ext_tex, T['TEX'])]), 'bc3')))
                gu_tex[ext_tex] = path
            if gu_tex[ext_tex] not in tex_index:
                tex_paths.append(gu_tex[ext_tex]); tex_index[gu_tex[ext_tex]] = len(tex_paths)
            slots['tSphereMap'] = tex_index[gu_tex[ext_tex]]
            # 4U CBMaterialStd albedo / diffuse / emission (mrl_anim.static_constants); not its diffuse alpha (0 on
            # these opaque 4U materials, GU fTransparency would hide them), specular a neutral 0.5 (4U 1.0, em019's
            # template 0.7 / 0.3 / 0.3)
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            consts = {k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], 1.0).items()
                      if k in (('$Globals', 'fAlbedoColor'), ('CBMaterial', 'fDiffuseColor'), ('$Globals', 'fEmissionColor'))}
            consts[('$Globals', 'fSpecularColor')] = (0.5, 0.5, 0.5)
        mtype = MTYPE.get(mname, int(re.search(r'_m(\d\d)_', mname).group(1)))
        extra = dict(mtype=mtype, bias=(mm['words'][7] >> 16) & 0xF)
        mats.append((mname, key, slots, [s for s in states if s.startswith('RS')], consts, extra))
        notes.append('material %s: template %s, type %d, %s%s' % (mname, key, mtype, src_tex.split('\\')[-1],
                                                                ', sphere %s' % ext_tex.split('\\')[-1] if ext and key == 'solid_sphere' else ''))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(P + 'mod\\em067_01', T['MRL'], mrl_bytes), (P + 'mod\\em067_01', T['MOD'], mod_bytes)]
    return out, m4


# Paralysis balls (notes/shells.md): GU's uShellEm067_sp_13 / sp_01 run Tigerstripe's balls and their impact residue
# (module em067_01_shells.c posts them for variant 1). Their families ship inside the monster arc under GU's paths,
# so ours carry Tigerstripe's data: HDS entries from 4U's records (the conversion of gogmazios/tools/build_em089_arc.py
# shell_hds, checked here on GU's own Zamtrios entries, which are 4U Zamtrios' records converted), the defs' effect
# list = em067_01u, and in em067_01u's code-post list GU's ball effects point at em092's.
HDS_T, HTS_T, SHELL_DEF_T = 0x4EB68CEE, 0x5653C1B0, 0x4AA69872
S012_REC_4U = 0x1028904 + 84    # 4U uShell012 attack records (40 B): Zamtrios 7..10, Tigerstripe 29..32
S003_REC_4U = 0x101efbc + 628   # 4U uShell003 (impact residue): Zamtrios 63 / 71 / 72, Tigerstripe 169 / 171 / 172
BALLS = ('shell\\em\\em067_00_shell13\\em067_00_13', ((0, 7, 29), (1, 8, 30), (2, 9, 31), (3, 10, 32)), 8)
RESIDUE = ('shell\\em\\em067_00_shell01\\em067_00_01', ((5, 63, 169), (6, 71, 171), (7, 72, 172)), 0xfe)
RESIDUE_RADIUS = {5: 200.0, 6: 200.0, 7: 300.0}      # 4U volumes of 169 / 171 / 172 (GU Zamtrios: 125 / 125 / 200)
BALL_FX = {'effect\\em\\em067\\em067_00_012': 'effect\\efl\\em\\em092\\em092_012',     # flight
           'effect\\em\\em067\\em067_00_014': 'effect\\efl\\em\\em092\\em092_013'}     # impact
# 7/70's sand / air blast (notes/blast.md): 4U uShell016 38 (Dunes) / 49, our class module em067_01_shell016.c on GU's
# breath family sp_02 (shell table row 291 = file 0x8a76), whose HDS / HTS get two more entries / groups: 4U records
# 33 / 39 (uShell016 records 0x102b370 + 96, byte 0x1c 6 as GU's own entry 0 = record 12, checked) and capsule
# volumes 19 / 21 (0x102b230 / 0x102b2d0: bone 1001, r208 / r260). The module arms HDS entries 1 / 2.
BREATH = 'shell\\em\\em067_00_shell02\\em067_00_02'
BREATH_FILE_ID = 0x8a76
S016_REC_4U = 0x102b370 + 96
BLAST = ((38, 33, 0x102b230, 208.0), (49, 39, 0x102b2d0, 260.0))     # subtype, record, volume, radius
BLAST_HDS0 = 1                                                         # entry of 38 (49 = + 1): em067_01_shell016.c
# code-posted effects (PEL list 2, efl4u2gu extra2): em092_001 element 1 at the mouth along the blast (4U uEffect015
# kinds 8 / 9, scale (0.8, 0.8, 1.0) / 1.0), em092_200 at the shell's end (uEffect002 49, all elements)
BLAST_FX = [('effect\\efl\\em\\em092\\em092_001', dict(id=4238, joint=-1, k=1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                      scl=(0.8, 0.8, 1.0))),
            ('effect\\efl\\em\\em092\\em092_001', dict(id=4249, joint=-1, k=1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                      scl=(1.0, 1.0, 1.0))),
            ('effect\\efl\\em\\em092\\em092_200', dict(id=4300, joint=-1, k=-1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                      scl=(1.0, 1.0, 1.0)))]


def hts_add(d, groups):
    """HTS with `groups` (lists of 48-B records) appended (before a closing empty group, as emdata4u writes for monster
    hitsize; GU's shell HTS have none) -> (data, first new index)"""
    n = struct.unpack_from('<I', d, 8)[0]
    tab = [struct.unpack_from('<II', d, 16 + 8 * g) for g in range(n)]
    recs = [d[off:off + 48 * cnt] for cnt, off in tab]
    assert 16 + 8 * n + sum(len(r) for r in recs) == len(d), 'HTS layout'
    first = n - 1 if tab[-1] == (0, len(d)) else n
    recs[first:first] = [b''.join(g) for g in groups]
    head = bytearray(d[:16])
    struct.pack_into('<I', head, 8, len(recs))
    table, data, base = b'', b'', 16 + 8 * len(recs)
    for r in recs:
        table += struct.pack('<II', len(r) // 48, base + len(data))
        data += r
    return bytes(head) + table + data, first


def hds_entry(exe, a, b1c):
    """a 4U 40-B attack record -> a GU 56-B HDS entry (build_em089_arc.shell_hds rules; byte 0x19 set by the caller)"""
    r4 = exe[a - 0x100000:a - 0x100000 + 40]
    r = bytearray(56)
    r[0:0x24] = r4[0:0x24]
    r[0x12] = r4[0x12] & 3
    r[0x1c] = b1c
    struct.pack_into('<f', r, 0x28, 1.0)
    r[0x2c] = r4[0x12] >> 2
    return r


def shell_data(ents, notes):
    """the kept GU entries with Tigerstripe's ball / residue hit data and effect list"""
    exe = open(os.path.join(ROOT, 'dump/exefs_v11/code.bin'), 'rb').read()     # MH4U v1.1 code, at 0x100000
    out, blast_hds = [], [None]
    for p, t, d in ents:
        for path, rows, b1c in (BALLS, RESIDUE):
            if (p, t) != (path + '_hitdata', HDS_T): continue
            d = bytearray(d)
            for k, zm, ts in rows:
                o = 16 + 56 * k
                gu = hds_entry(exe, S012_REC_4U + 40 * zm if b1c == 8 else S003_REC_4U + 40 * zm, b1c)
                gu[0x19] = d[o + 0x19]
                assert bytes(gu) == bytes(d[o:o + 56]), (path, k, 'GU entry is not 4U record %d converted' % zm)
                new = hds_entry(exe, S012_REC_4U + 40 * ts if b1c == 8 else S003_REC_4U + 40 * ts, b1c)
                new[0x19] = d[o + 0x19]
                d[o:o + 56] = new
            notes.append('shell %s: HDS entries %s = 4U records %s' % (path.split('\\')[-1], [r[0] for r in rows],
                                                                     [r[2] for r in rows]))
            d = bytes(d)
        if (p, t) == (RESIDUE[0] + '_hitsize', HTS_T):     # residue volumes: the group of each entry, 4U radius
            d = bytearray(d)
            hds = [e for e in ents if e[:2] == (RESIDUE[0] + '_hitdata', HDS_T)][0][2]
            for k, rad in RESIDUE_RADIUS.items():
                g = hds[16 + 56 * k + 0x19]
                off = struct.unpack_from('<I', d, 16 + 8 * g + 4)[0]
                struct.pack_into('<f', d, off + 0x0c, rad)
            d = bytes(d)
        if (p, t) == (BREATH + '_hitsize', HTS_T):           # 7/70 blast volumes, then the blast HDS entries
            vols = []
            for sub, rec, vol, rad in BLAST:
                r = bytearray(exe[vol - 0x100000:vol - 0x100000 + 40]) + bytearray(8)
                assert struct.unpack_from('<Hf', r, 0)[0] == 1001 and struct.unpack_from('<f', r, 0x0c)[0] == rad, sub
                struct.pack_into('<H', r, 0x0a, 0x0848)            # GU's value in every HTS record (build_em089_arc)
                vols.append([bytes(r)])
            d, g0 = hts_add(d, vols)
            hds = [e for e in ents if e[:2] == (BREATH + '_hitdata', HDS_T)][0][2]
            n = struct.unpack_from('<I', hds, 8)[0]
            assert n == BLAST_HDS0 and len(hds) == 16 + 56 * n
            gu = hds_entry(exe, S016_REC_4U + 40 * 12, 6)
            gu[0x19] = hds[16 + 0x19]
            gu[2:4] = hds[18:20]                                   # GU's +2 (9999) on its breath entry
            assert bytes(gu) == hds[16:72], 'GU breath entry is not 4U record 12 converted'
            new = bytearray(hds)
            struct.pack_into('<I', new, 8, n + len(BLAST))
            for i, (sub, rec, vol, rad) in enumerate(BLAST):
                e = hds_entry(exe, S016_REC_4U + 40 * rec, 6)
                e[0x19] = g0 + i
                new += e
            blast_hds[0] = bytes(new)
            notes.append('shell em067_00_02: HDS entries %s = 4U uShell016 records %s, HTS groups %s (r %s)' % (
                list(range(n, n + len(BLAST))), [b[1] for b in BLAST], list(range(g0, g0 + len(BLAST))),
                [b[3] for b in BLAST]))
        if t == SHELL_DEF_T and p.startswith('shell\\em\\em067_00_shell'):
            assert d.count(b'effect\\pel\\em\\em067_00u') == 1, p
            d = d.replace(b'effect\\pel\\em\\em067_00u', PEL_U.encode())
        out.append((p, t, d))
    assert blast_hds[0], 'breath family not found'
    return [(p, t, blast_hds[0] if (p, t) == (BREATH + '_hitdata', HDS_T) else d) for p, t, d in out]


def ball_fx_list2(list2):
    """GU PEL list 2 (count, record bytes) with the ball flight / impact records on em092's EFLs (state kept)"""
    n, body = list2
    out, i = b'', 0
    for _ in range(n):
        L = body[i]
        path = body[i + 1:i + 1 + L].decode('ascii')
        rest = body[i + 1 + L:i + 1 + L + 2 + 160]
        new = BALL_FX.get(path, path).encode('ascii')
        out += bytes([len(new)]) + new + rest
        i += 1 + L + 2 + 160
    assert i == len(body)
    return n, out


def parts_xfs(gu_xfs, groups, notes):
    """GU em067_00's parts states (rMonsterPartsManager XFS) for em092's mesh groups. 4U em092's visibility rows are
    a subset of em022's, identical for every group they share, so the GU states mean the same for those groups."""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    unnamed = sorted(set(groups) - {g for st in states for g, _ in st} - set(HIDDEN_GROUPS))
    assert not unnamed, 'em092 groups without a GU state: %s' % unnamed
    kept[0] += [(g, 0) for g in HIDDEN_GROUPS if g in groups]
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted({g for st in states for g, _ in st} - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in em092): %s, hidden at spawn: %s' % (
        len(kept), dropped, list(HIDDEN_GROUPS)))
    return bytes(head) + data


def dunes_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Dunes hunting areas' area_color_soil
    (stage\\m17d\\m17aNNd\\sdl\\m17aNNd-col, areas 1..11; same 455-byte SDL layout as the Battlequarters' m19a03d-col
    whose soil efl4u2gu documents, colour at +0xd0). GU has no area tint: one colour is baked in."""
    m19 = os.path.join(ROOT, 'dump/m19_unpacked/m19a03/stage/m19d/m19a03d/sdl/m19a03d-col.4c0db839')
    ref = open(m19, 'rb').read()
    names = re.findall(rb'[ -~]{4,}', ref)
    n, _ = ctr.main_ncch(efl4u2gu.ROM_4U)
    fs = n.romfs_reader()
    cols = []
    for a in range(1, 12):
        _, ents = arcpack.read(fs.read('/loc/data/m17a%02d.arc' % a))
        d = [d for p, t, d in ents if p == 'stage\\m17d\\m17a%02dd\\sdl\\m17a%02dd-col' % (a, a)][0]
        assert len(d) == len(ref) and re.findall(rb'[ -~]{4,}', d) == names, 'm17a%02dd-col layout' % a
        cols.append([round(255 * x) for x in struct.unpack_from('<4f', d, 0xd0)])
    soil = bytes(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(4))
    notes.append('effect area colour: Dunes soil median %s (areas 1..11: %s)' % (tuple(soil), cols))
    return soil


def effects(gu_pel_u, notes):
    """em092's effects (tools/efl4u2gu.py effect_set) -> [(path, type, data)]. MEF groups: 92 = its own EFL family,
    others = the 4U common qe families (qe000 / 006 / 008 / 013 exist in the core arcs)."""
    groups = {92: 'effect\\efl\\em\\em092\\em092_%03d'}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 6, 8, 13)})
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef='effect\\mef\\em\\em092_0', em_efl='effect\\efl\\em\\em092\\',
                groups=groups, extra=[], lmts=[(P4 + 'mot\\em092_%d' % b, PSL % b) for b in BANKS], pel=PEL_U,
                soil=dunes_soil(notes), list2=ball_fx_list2(efl4u2gu.pel_lists(gu_pel_u)[2]), extra2=BLAST_FX)
    log = []
    out = efl4u2gu.effect_set(spec, log)
    for p in set(BALL_FX.values()):
        assert (p, efl4u2gu.T['EFL']) in out, 'ball effect not shipped: ' + p
    notes.append('PEL list 2: GU ball effects -> %s' % sorted(set(BALL_FX.values())))
    notes.append('effects: %d entries (tools/efl4u2gu.py effect_set)' % len(out))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return [(p, t, d) for (p, t), d in out.items()]


def sound(rom, notes):
    """em092's sound call, waves, bank and request (tools/snd4u2gu.py monster_entries) -> ([(path, type, data)],
    {field: (path, type)}). Common-bank requests from GU em067_00 (same numbers in every GU monster), plus the ones GU's
    Zamtrios adds (800-827, 9999: its class may post them). GU's own-bank additions 212 / 220 / 221 / 230 have no
    em092 wave group: not ported (silent if GU's code posts them). Request numbers otherwise line up: em092 holds all
    of em022's (GU's code posts em022 numbers) + 6 of its own."""
    spec = dict(name='em092', src=SRC_4U, p4_wave='sound\\se\\em\\em092\\wave\\', pg_wave='sound\\se\\em\\em067_01\\wav\\',
                p4_bank='sound\\se\\em\\em092\\snd_em092', pg_bank='sound\\se\\em\\em067_01\\snd_em067_01',
                p4_call='sound\\call\\em\\em092', pg_call='sound\\call\\em\\em067_01', donor_arc=GU_ARC,
                donor_name='GU em067_00', donor_extra=True)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    notes += log
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def bodydata(gu, notes):
    """GU em067_00's bodydata minus the records em092 lacks (4U em022 -> em092 drops exactly those, the others are
    identical in 4U; GU retuned values in the shared ones, which stay)."""
    d22 = emdata4u.bodydata(emdata4u.load_4u('em022')['emd'], 8)
    d92 = emdata4u.bodydata(emdata4u.load_4u('em092')['emd'], 8)
    rec = lambda b: [b[16 + 44 * k:60 + 44 * k] for k in range(struct.unpack_from('<I', b, 8)[0])]
    r22, r92, rg = rec(d22), rec(d92), rec(gu)
    assert len(rg) == len(r22) and [r for k, r in enumerate(r22) if k not in BODYDATA_DROP] == r92
    for k, bone in BODYDATA_DROP.items():
        assert struct.unpack_from('<H', rg[k], 0)[0] == bone == struct.unpack_from('<H', r22[k], 0)[0], k
    keep = [r for k, r in enumerate(rg) if k not in BODYDATA_DROP]
    head = bytearray(gu[:16])
    struct.pack_into('<I', head, 8, len(keep))
    tail = gu[16 + 44 * len(rg):]
    notes.append('bodydata: GU em067_00 minus records %s (bones %s)' % (sorted(BODYDATA_DROP),
                                                                        sorted(BODYDATA_DROP.values())))
    return bytes(head) + b''.join(keep) + tail


def cmdtbl(d4, gu, notes):
    """4U em092's command table + the entries GU em067_00's table has beyond it (group 0 selector 29, group 1 scripts
    180..199). GU's class code picks group-1 scripts by number outside the table's own selectors: the area moves of
    resident enemy\\area_act_tbl (Zamtrios' entry: 180..187, picked through 0xb4e58 -> 0x69c1c8, read at 0x82a04
    without a range check). 4U had native actions there, so em092's table stops at 179 and an area move read past it
    (null script pointer: crash in the EMC decoder 0x50ce0, test 2026-10-21 08:20). Every script the appended ones
    call (14 nn) is the same in both tables (asserted), so they run as in GU."""
    ts = emc.parse(emc.to_gu(d4))[1]
    g = emc.parse(gu)[1]
    assert len(ts) == len(g)
    added, todo = [], []
    for k in range(len(g)):
        assert len(ts[k]) <= len(g[k]), k
        added += [(k, i) for i in range(len(ts[k]), len(g[k]))]
        ts[k] = ts[k] + g[k][len(ts[k]):]
    for k, i in added:
        for c in emc.refs(g[k][i])[1]:
            assert c >= len(emc.parse(emc.to_gu(d4))[1][1]) or g[1][c] == ts[1][c], (k, i, 'calls a script em092 changes', c)
    notes.append('cmdtbl: 4U em092 + GU em067_00 entries %s (all their calls are scripts identical in both)' %
                 ['g%d s%d' % a for a in added])
    return emc.build(ts)


# GU leaves an area with Zamtrios' dive (6/1 0x415 submerge, 6/3 0x416 travel, 6/2 0x417 emerge: shared code, no
# variant test, as in 4U), but em092's bank 4 lacks indices 21..23 (phase1-variant-map.md 4), so 6/1 had no motion and
# every area move failed (test 2026-10-21 08:52: 1/51 -> 6/1 -> 6/3 -> 7/13 loop). The user recalls 4U Tigerstripe
# diving into the ground to leave: em022's three motions go into em092's empty slots (same skeleton by bone ID). They
# carry em022's event data; our PSL / sound call come from em092's lists, so the dive plays without effects / sounds.
EM022_ARC = os.path.join(ROOT, 'dump/romfs/data/em022.arc')
DIVE = {4: [(21, 21), (22, 22), (23, 23)]}       # bank: [(em022 index, em092 index)]


def motion_bank(S, b, notes):
    d = S[(P4 + 'mot\\em092_%d' % b, T['LMT'])]
    if b not in DIVE:
        return d
    _, z = arcpack.read(open(EM022_ARC, 'rb').read())
    src = [x for p, t, x in z if (p, t) == ('enemy\\em022\\mot\\em022_%d' % b, T['LMT'])][0]
    out = lmt.splice(d, src, DIVE[b])
    notes.append('motions bank %d: em092 + em022 dive %s (0x415..0x417)' % (b, [i for i, _ in DIVE[b]]))
    return out


# Area changes: the five per-monster area files (manifest fields 40 area_link, 41 area_eat, 42 map_info, 43
# area_select, 44 area_patrol) are keyed by map (XFS records mMapNo; map_info = 86-byte blocks per map). GU Zamtrios'
# cover map 14 only (its other stages are single-area arenas), so on the Dunes (map 5) Tigerstripe had no next area
# and never left. 4U keeps no area data in the monster arcs (em022 / em092 have none), so ours are GU Diablos'
# (em007_00: a large ground monster of the Dunes, map 5 areas 1-5, 7, 10 incl. the spawn area 4; no patrol data,
# as every GU Dunes route of it).
AREA_DONOR = ('/nativeNX/arc/enemy/em007_00.arc', 'em007_00')
AREA_FIELDS = {40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select', 44: 'area_patrol'}


def area_files(rom, gtype, notes):
    """{field: (our path, type, GU em007_00's data)}"""
    _, g = arcpack.read(rom.read(AREA_DONOR[0]))
    out = {}
    for k, kind in AREA_FIELDS.items():
        src = [(p, t, d) for p, t, d in g if p == 'enemy\\%s\\%s' % (kind, AREA_DONOR[1])]
        assert len(src) == 1 and src[0][1] == gtype[k], (k, kind)
        out[k] = ('enemy\\%s\\em067_01' % kind, src[0][1], src[0][2])
    notes.append('area data (fields 40-44): GU %s (map 5 / 22 routes; GU em067_00 covers map 14 only)' %
                 AREA_DONOR[1])
    return out


def attackdata(gu, notes):
    """4U em092's attackdata (tools/emdata4u.py) with GU em067_00's byte 28 (GU-only, the converter writes 6). 4U em092
    and em022 share one table (asserted), so this is GU's table except where GU retuned 4U fields for its Zamtrios:
    flags bytes 12-13 of records 23, 24, 31, 32, 33 (4U 01 08, GU 81 02: bit 7 of byte 12 is the bit Zamtrios' ice
    balls carry in the shell hit data and Tigerstripe's paralysis balls lack)."""
    ts = emdata4u.attackdata(emdata4u.load_4u('em092')['etd'])
    assert ts == emdata4u.attackdata(emdata4u.load_4u('em022')['etd'])
    n = struct.unpack_from('<I', gu, 8)[0]
    assert ts[:16] == gu[:16] and len(ts) == len(gu) == 16 + 32 * n
    out = bytearray(ts)
    for k in range(n):
        out[16 + 32 * k + 28] = gu[16 + 32 * k + 28]
    diff = sorted({(i - 16) // 32 for i in range(16, len(gu)) if out[i] != gu[i]})
    assert all(out[16 + 32 * k:16 + 32 * k + 32][:12] + out[16 + 32 * k + 14:16 + 32 * k + 32] ==
               gu[16 + 32 * k:16 + 32 * k + 12] + gu[16 + 32 * k + 14:16 + 32 * k + 32] for k in diff), 'more than flags'
    notes.append('attackdata: 4U em092 (= em022) with GU byte 28; differs from GU in the flags of records %s' % diff)
    return bytes(out)


def dttune(gu, notes):
    """GU em067_00's dttune + the bytes where tools/dt_convert.py (donor em067_00) gives em092 != em022: Tigerstripe's
    4U differences on GU's own Zamtrios tuning (GU's retuned bytes and these never overlap: asserted)."""
    c22 = open(os.path.join(DT_DIR, 'dt_em022', 'dttune.bin'), 'rb').read()
    c92 = open(os.path.join(DT_DIR, 'dt_em092', 'dttune.bin'), 'rb').read()
    assert len(c22) == len(c92) == len(gu)
    delta = [i for i in range(len(gu)) if c22[i] != c92[i]]
    retuned = {i for i in range(len(gu)) if c22[i] != gu[i]}
    assert not retuned & set(delta), 'GU retuned bytes Tigerstripe changes: %s' % sorted(retuned & set(delta))
    out = bytearray(gu)
    for i in delta: out[i] = c92[i]
    notes.append('dttune: GU em067_00 + %d bytes of 4U em022 -> em092 differences (GU retuned %d other bytes)' % (
        len(delta), len(retuned)))
    return bytes(out)


def main():
    img = open(paths.GU_MAIN, 'rb').read()
    rom = RomFS(paths.GU_ROMFS)
    _, src = arcpack.read(open(SRC_4U, 'rb').read())
    S = {(p, t): d for p, t, d in src}
    _, gents = arcpack.read(rom.read(GU_ARC))
    notes = []
    gents = shell_data(gents, notes)
    ghash = {(phash(p), t): (p, t) for p, t, _ in gents}
    assert ghash[fileid_entry(img, BREATH_FILE_ID)] == (BREATH, SHELL_DEF_T), 'em067_01_shell016.c loads file 0x8a76'
    gman = manifest_of(img, ALLOC['donor_index'])

    # ---- our own files
    own, ents = {}, []
    files, m4 = model(S, rom, notes)
    ents += files
    own[0] = (P + 'mod\\em067_01', T['MOD'])
    gu_xfs = [d for p, t, d in gents if (p, t) == (P0 + 'mod\\em067_00', T['XFS'])][0]
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em067_01', T['XFS'], parts_xfs(gu_xfs, groups, notes)))
    own[3] = (P + 'mod\\em067_01', T['XFS'])
    for b in BANKS:
        ents.append((P + 'mot\\em067_01_%d' % b, T['LMT'], motion_bank(S, b, notes)))
        own[4 + b] = (P + 'mot\\em067_01_%d' % b, T['LMT'])
    ents.append((P + 'mot\\em067_01_cam', T['LCM'], lcm4u2gu.convert(S[(P4 + 'mot\\e092_cam', T['LCM'])])))
    own[11] = (P + 'mot\\em067_01_cam', T['LCM'])
    gu_cmd = [d for p, t, d in gents if p.startswith('enemy\\cmd_tbl\\em067_00') and t == T['EMC']]
    assert len(gu_cmd) == 1
    ents.append(('enemy\\cmd_tbl\\em067_01_cmdtbl', T['EMC'], cmdtbl(S[(P4 + 'data\\em092_cmd', T['EMC'])], gu_cmd[0],
                                                                     notes)))
    own[37] = ('enemy\\cmd_tbl\\em067_01_cmdtbl', T['EMC'])
    G = {(p, t): d for p, t, d in gents}
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em067_00's file of manifest field k
    efx = effects(gfile(17), notes)
    ents += efx
    own[17] = (PEL_U, efl4u2gu.T['PEL'])
    for b in BANKS:
        own[18 + b] = (PSL % b, efl4u2gu.T['PSL'])
    files, fields = sound(rom, notes)
    ents += files
    own.update(fields)
    for k, path, conv in ((26, 'enemy\\hit_data\\em067_01_attackdata', attackdata),
                          (30, 'enemy\\body_data\\em067_01_bodydata', bodydata),
                          (33, 'enemy\\dt_tune\\em067_01_dttune', dttune)):
        typ = ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, conv(gfile(k), notes)))
        own[k] = (path, typ)
    import hagi_em067_01                 # carves: 4U G body / shiny tables in s4, GU's filler in s0..s3
    for k, data in hagi_em067_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em067_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    for k, (path, typ, data) in area_files(rom, {k: ghash[fileid_entry(img, gman[k])][1] for k in AREA_FIELDS},
                                           notes).items():
        ents.append((path, typ, data))
        own[k] = (path, typ)

    # ---- the shared GU em067_00 files: everything but what ours replace and em067_00's model (MOD, MRL, textures)
    replaced = {ghash[fileid_entry(img, gman[k])] for k in own if gman[k] != -1}
    drop = replaced | {(p, t) for p, t, _ in gents if p.startswith(P0 + 'mod\\')}
    while True:                                  # a file a kept one names by path stays (e.g. em067_00u: GU shells)
        kept = [(p, t, d) for p, t, d in gents if (p, t) not in drop]
        named = {(p, t) for p, t in drop if any(p.encode('ascii') in kd for _, _, kd in kept)}
        if not named: break
        for p, t in sorted(named):
            notes.append('kept %s although replaced: named by %s' % (p, [kp for kp, _, kd in kept
                                                                         if p.encode('ascii') in kd][:4]))
        drop -= named
    ents += kept
    notes.append('shared from em067_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em067_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'GU %s (area data)' % AREA_DONOR[1] if k in AREA_FIELDS else 'converted (4U em092)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em067_00, its file ID)'

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
    json.dump(dict(monster='em067_01 (Tigerstripe Zamtrios)', id='0x%x' % ALLOC['em_id'],
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
