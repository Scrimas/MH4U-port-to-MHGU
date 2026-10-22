"""build_dalamadur_arc.py : build the four Dalamadur arcs + their file manifests and data file sections FILE.

  build_dalamadur_arc.py            build all four, verify, then write (paths in monsters/dalamadur/):
      romfs/nativeNX/arc/enemy/em090_00.arc   Dalamadur (head half, 4U em024)
      romfs/nativeNX/arc/enemy/em090_01.arc   Shah Dalamadur (head half, 4U em110)
      romfs/nativeNX/arc/enemy/em091_00.arc   Dalamadur's tail half (4U em083)
      romfs/nativeNX/arc/enemy/em091_01.arc   Shah Dalamadur's tail half (4U em111)
      tools/<arc>_manifest.json               51 manifest fields, file IDs, sources
      gen/<entry>/FILE.sec                    manifest + file table (tools/portdata.py), only once allocations.toml
                                              holds the entry (until then the planned IDs below, and no section)

Layout (notes/phase0.md, class-study.md): 4U ships one model for both halves (each half shows its own mesh groups) and
the tail arc em083 is a subset of em024's files (same for em111 / em110). Here, as GU's variant arcs do (em067_01):
an arc carries its own files under its own paths, plus the files it shares with another entry under THAT entry's
paths and file IDs, so every arc works alone and shares the resources when both are loaded.
  head (em090_00 / em090_01), converted from 4U em024 / em110:
      mod\\emNNN_0V (+ _tail: the boneless severed-tail piece, manifest 1) MOD + MRL, textures (+ GU specular maps)
      mot\\emNNN_0V_0 / 2 / 3       4U motion lists (LMT 67, unchanged; Shah's 0 / 3 = Dalamadur's, shared)
      mot\\emNNN_0V_cam             4U camera list (tools/lcm4u2gu.py)
      cmd_tbl\\em090_00_cmdtbl      4U em024_cmd (Shah's em110_cmd is identical: shared)
      XFS parts visibility          spawn state of the half (4U rows + the class spawn masks), every state the same:
                                    the class evaluates the 4U rows at runtime (class-study.md "Model groups")
      attackdata, hitsize, bodydata, cambodydata (tools/emdata4u.py), dtbase / dttune (tools/dt_convert.py, donor
      Kushala em024_00, dump/converted/dalamadur/dt_emNNN)
      effects (tools/efl4u2gu.py effect_set: EFLs under their 4U paths, PEL u = MEF _0 (motion) + MEF _1 (code
      posts, ids 2000+), PSL per motion list), area colour of the Speartip Crag arena
      sound call / waves / bank / request (tools/snd4u2gu.py monster_entries)
  tail (em091_00 / em091_01), from 4U em083 / em111: own cmd table (em083_cmd == em111_cmd: shared), XFS, attackdata,
      hitsize, bodydata, cambodydata, dtbase / dttune; model, motions, camera, effects and sound = its head's.
  donor (Kushala em024_00, as Gogmazios'): renamed placeholders under em090_00 paths, shared by all four (dtbparts,
      actiontune, area_link / eat / select / patrol, map_info, hagi s0..s4 until the content step converts the carves),
      and its effect / sound / shell chain under its original paths and file IDs (pts c / u, pel c, shell arc, option
      motion; they name each other by path).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import hagi_em090, items_em090                     # this package's carve / item tools (tools/)
import alloc, arcpack, efl4u2gu, emc, emdata4u, hagi4u, lcm4u2gu, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, \
    portdata, snd4u2gu, tex

T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02,
         LCM=0x39C52040, MEF=0x148B6F89, BDD=0x1AC7B52D, DTB=0x59D9C3DA)
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
DONOR, DONOR_INDEX = 'em024_00', 23                 # Kushala Daora (G: as Gogmazios; revisit with the registry entry)
DT_DIR = os.path.join(ROOT, 'dump/converted/dalamadur')   # dt_<em>/{dtbase,dttune}.bin (tools/dt_convert.py)
BANKS = (0, 2, 3)                # 4U motion lists em024_0 / 2 / 3: manifest field 4 + bank, PSL field 18 + bank
P4M = 'enemy\\em024\\'           # 4U model / motion paths (em083 carries em024's), Shah: enemy\\em110\\
# 4U raster states GU's shader package lacks: cull-none + depth bias 8 -> GU cull-none (the bias nibble still goes
# into MRL w7, mrl_build extra 'bias')
RS_MAP = {'RSMeshCNBias8': 'RSMeshCN'}
# 4U 'E1' bodies with an extend map (iMaterialStdSpecularColorType 1, sphere_lit): Capcom's own conversion of that
# preset, GU Kushala em024_00_tail mat 0 'XfB__E_m00_body' (4U Kushala em031's body has the same CBMaterialStd ints
# as Dalamadur's, C): tAlbedo = tSpecular = the BM, tSphereMap = the 4U extend texture, no normal map, no animation
# block, IASkinTB2wt. Dalamadur only (registered here, not in tools/mrl_build.py). User 2026-10-22: restore the sheen.
mrl_build.TEMPLATES['solid_e1'] = ('/nativeNX/arc/enemy/em024_00.arc', 'enemy\\em024\\em024_00\\mod\\em024_00_tail', 0)
# 4U spawn group masks (class-study.md): groups each half hides at spawn (head 0x76d5a0, tail 0x89fe4c)
HIDE = {'head': {1, 16, 17, 18, 19, 20, 21, 22, 25, 106, 107, 108},
        'tail': {0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 23, 24} | set(range(30, 46)) | set(range(100, 106))}
# entries (allocations.toml names); planned file-ID ranges until the registry entries exist (Phase 3)
HALVES = [
    dict(entry='dalamadur', em4='em024', gu='em090_00', role='head', title='Dalamadur', ids=(0x10780, 0x107ff)),
    dict(entry='shah_dalamadur', em4='em110', gu='em090_01', role='head', title='Shah Dalamadur', ids=(0x10800, 0x1087f),
         share='em090_00'),
    dict(entry='dalamadur_tail', em4='em083', gu='em091_00', role='tail', title='Dalamadur (tail half)',
         ids=(0x10880, 0x1089f), head='em090_00'),
    dict(entry='shah_dalamadur_tail', em4='em111', gu='em091_01', role='tail', title='Shah Dalamadur (tail half)',
         ids=(0x108a0, 0x108bf), head='em090_01', share='em091_00'),
]
FIELD_KIND = {0: 'model', 1: 'model (tail)', 3: 'model data (XFS)', 4: 'motion 0', 6: 'motion 2', 7: 'motion 3',
              11: 'camera', 12: 'sound call', 13: 'sound bank', 14: 'pts c', 15: 'pts u', 16: 'pel c', 17: 'pel u',
              18: 'psl 0', 20: 'psl 2', 21: 'psl 3', 25: 'shell arc', 26: 'attackdata', 28: 'hitsize', 30: 'bodydata',
              31: 'cambodydata', 32: 'dtbase', 33: 'dttune', 34: 'dtbparts', 35: 'actiontune', 37: 'cmdtbl',
              40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select', 44: 'area_patrol',
              45: 'option motion', 46: 'hagi s0', 47: 'hagi s1', 48: 'hagi s2', 49: 'hagi s3', 50: 'hagi s4'}
RENAMED = [34, 35, 40, 41, 42, 43, 44]                          # donor placeholders, own IDs (em090_00 paths)
HAGI = [46, 47, 48, 49, 50]      # carves s0..s4 per half (tools/hagi_em090.py); em090_00 had them as placeholders, the
                                 # other halves number them after their extras (every earlier file ID stays)
KEPT = [14, 15, 16, 25, 45]                                      # donor files, donor IDs
# own fields in ID order per role (IDs never move once shipped: append new fields at the end)
OWN_ORDER = {'head': [0, 1, 3, 4, 6, 7, 11, 37, 12, 13, 17, 18, 20, 21, 26, 28, 30, 31, 32, 33] + RENAMED,
             'tail': [3, 37, 26, 28, 30, 31, 32, 33]}
# own files without a manifest field, IDs right after the fields' (append only); the module finds them by file ID
EXTRA_ORDER = ['bgm_stqr', 'walk_b001', 'walk_b002', 'walk_b003', 'walk_b004', 'walk_b005', 'walk_b140', 'walk_b141',
               'walk_b142', 'shell00']
BGM_STQR = 'sound\\bgm\\battle\\bgm_em090'        # Dalamadur's own battle STQR (tools/bgm_dalamadur.py)
# walk collision (tools/walk4u2gu.py): one GU ground SBC per 4U joint ID of the half's walk sets, bone-local; Shah's
# sets are byte-identical (index same_as), so its arcs carry Dalamadur's files. The class registers / moves / enables
# them (class-study.md "Walking on the body"; gu-walkable.md).
WALK_DIR = os.path.join(ROOT, 'dump/converted/dalamadur/walk')
WALK = {'em090_00': ('em024', (1, 2, 3, 4, 5)), 'em091_00': ('em083', (140, 141, 142))}
T_SBC = 0x51FC779F
# Dalamadur's shell family (module dala_shell.h): shell\em\em090_00_shell00\em090_00_00 = a copy of Kushala's family
# 00 (XFS def with 26 entries of ef / snd / hit / sh params, ShellCmnParam FUP, HDS, HTS: 108 files) as Gogmazios'
# build_em089_arc.py shell_family: only the def names the other files (same-length path rename); its effect / sound
# list paths stay Kushala's em024_00u (the classes post their effects through the monster's PEL, dala_efx.c). HDS /
# HTS from the 4U inline records of the shells Dalamadur posts (C, module dala_shell*.c / dala_meteor.c). The def's
# file ID = em090_00's extra 'shell00' = module DALA_SHELL_FILE (asserted); all four arcs carry the family.
CODE_4U = os.path.join(ROOT, 'dump/exefs_v11/code.bin')     # MH4U v1.1 code, loaded at 0x100000
CODE_4U_BASE = 0x100000
SHELL_SRC = 'shell\\em\\em024_00_shell00\\em024_00_00'
SHELL_DST = 'shell\\em\\em090_00_shell00\\em090_00_00'
T_HDS, T_HTS, T_SHELL = 0x4EB68CEE, 0x5653C1B0, 0x4AA69872
SHELL_FILE_ID = 0x107a6          # module dala_shell.h DALA_SHELL_FILE
BGM_STQR_FILE_ID = 0x107a0       # module dala_bgm.c DALA_FILE_BGM_STQR
# HDS entries in the module's order (dala_shell.h DALA_HDS_*): (4U records, volume table, record, records that must
# be byte-identical and fold onto this entry). 4U readers: 0x9ab120(shell, records, volumes, record, a, b).
SHELL_HDS = [
    (0x102dff0, 0x102dfe0, 0, ()), (0x102dff0, 0x102dfe0, 1, ()), (0x102dff0, 0x102dfe0, 2, ()),
    (0x102dff0, 0x102dfe0, 3, ()), (0x102dff0, 0x102dfe0, 4, ()), (0x102dff0, 0x102dfe0, 5, ()),  # uShell029 0..5
    (0x1019f30, 0x1019e50, 64, (82,)), (0x1019f30, 0x1019e50, 62, (81,)),     # uShell001 kinds 24 / 89, 25 / 88
    (0x101f230, 0x101efbc, 112, (159,)), (0x101f230, 0x101efbc, 113, (160,)),  # uShell003: record = subtype
    (0x101f230, 0x101efbc, 114, (161,)), (0x101f230, 0x101efbc, 126, (162,)),
    (0x102b3d0, 0x102b370, 14, (34,)), (0x102b3d0, 0x102b370, 18, (35,)),     # uShell016 21 / 39 (+ frame 380)
    (0x1025bc8, 0x1025b58, 4, ()),                                            # uShell005 subtype 4 (tail 7.0)
]
# HDS byte 0x1c (attack slot +0x55 in GU 0x168f50 / +0x4d in 4U 0xb701b4): 0 in monster records, 29 in the uShell003
# records, 1 in uShell005's; GU's own HDS only hold 6..10 / 254 (Gogmazios' survey). Meaning not traced: values GU
# never uses become 6 (Kushala's, the commonest) (G).
GU_HDS_1C = set(range(6, 11)) | {254}


def code4u():
    return open(CODE_4U, 'rb').read()


def shell_volumes(code):
    """HTS groups: every distinct (volume table, index) of SHELL_HDS in first-use order -> {key: group}, [key]."""
    order = []
    for rec_base, vol_base, idx, _ in SHELL_HDS:
        o = rec_base + 40 * idx - CODE_4U_BASE
        key = (vol_base, code[o + 0x19])
        if key not in order: order.append(key)
    return {k: i for i, k in enumerate(order)}, order


def shell_hds(code, template):
    """HDS (56-B entries) from the 4U 40-B records, converted as build_em089_arc.py shell_hds (same reader offsets in
    GU 0x168e98 / 4U 0xb700f8, C there): byte 0x12 bits 0-1 kept, its level (bits 2+) to +0x2c; +0x28 f32 1.0; byte
    0x19 = the HTS group; byte 0x1c see GU_HDS_1C."""
    assert template[:4] == b'HDS\0'
    group, _ = shell_volumes(code)
    recs = []
    for rec_base, vol_base, idx, same in SHELL_HDS:
        o = rec_base + 40 * idx - CODE_4U_BASE
        r4 = code[o:o + 40]
        for s in same:
            q = rec_base + 40 * s - CODE_4U_BASE
            assert code[q:q + 40] == r4, 'record %d of 0x%x is not record %d' % (s, rec_base, idx)
        assert not any(r4[0x24:0x28]), r4.hex()
        r = bytearray(56)
        r[0:0x24] = r4[0:0x24]
        r[0x12] = r4[0x12] & 3
        r[0x1c] = r4[0x1c] if r4[0x1c] in GU_HDS_1C else 6
        struct.pack_into('<f', r, 0x28, 1.0)
        r[0x2c] = r4[0x12] >> 2
        r[0x19] = group[(vol_base, r4[0x19])]
        recs.append(bytes(r))
    ver = struct.unpack_from('<I', template, 4)[0]
    return struct.pack('<4sIII', b'HDS\0', ver, len(recs), 0) + b''.join(recs)


def shell_hts(code, template):
    """HTS: one group per 4U volume (40-B records until 0xFFFF; GU record = 4U + 8 zero bytes, +0x0a = Kushala's
    0x0848 as in all GU shell HTS records, 4U 0 there), Kushala's header."""
    assert template[:4] == b'HTS\0'
    off = struct.unpack_from('<I', template, 0x14)[0]
    rec0 = template[off:off + 48]
    _, order = shell_volumes(code)
    groups = []
    for vol_base, v in order:
        p = struct.unpack_from('<I', code, vol_base + 4 * v - CODE_4U_BASE)[0] - CODE_4U_BASE
        recs = []
        while struct.unpack_from('<H', code, p)[0] != 0xFFFF:
            r4 = code[p:p + 40]
            assert not any(r4[0x0a:0x0c]), r4.hex()
            r = bytearray(48)
            r[0:40] = r4
            r[0x0a:0x0c] = rec0[0x0a:0x0c]
            recs.append(bytes(r))
            p += 40
        assert recs, (hex(vol_base), v)
        groups.append(recs)
    n = len(groups)
    head = bytearray(template[:16])
    struct.pack_into('<I', head, 8, n)
    data_off, table, data = 16 + 8 * n, b'', b''
    for recs in groups:
        table += struct.pack('<II', len(recs), data_off + len(data))
        data += b''.join(recs)
    return bytes(head) + table + data, order


def shell_family(dents):
    """[(path, type, data)] of Dalamadur's family in the donor's order, + a note."""
    code = code4u()
    out, vols = [], None
    for p, t, d in dents:
        if not p.startswith(SHELL_SRC): continue
        np_ = SHELL_DST + p[len(SHELL_SRC):]
        if t == T_SHELL:
            n = d.count(SHELL_SRC.encode())
            d = d.replace(SHELL_SRC.encode(), SHELL_DST.encode())
            assert n == 107 and b'em024_00_shell00' not in d, n      # 26 x 4 params + cmn + HDS + HTS
        elif t == T_HDS:
            d = shell_hds(code, d)
        elif t == T_HTS:
            d, vols = shell_hts(code, d)
        out.append((np_, t, d))
    assert sum(t == T_SHELL for _, t, _ in out) == 1 and len(out) == 108 and vols, len(out)
    return out, 'shell family %s: %d files from %s; HDS %d entries, HTS %d groups (4U volumes %s)' % (
        SHELL_DST, len(out), SHELL_SRC, len(SHELL_HDS), len(vols), ', '.join('0x%x[%d]' % k for k in vols))


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def src_arc(em4):
    _, src = arcpack.read(open(os.path.join(ROOT, 'dump/romfs/data/%s.arc' % em4), 'rb').read())
    return {(p, t): d for p, t, d in src}


def spec_type(mm, cbs):
    """CBMaterialStd iMaterialStdSpecularColorType of a 4U material (None without CBMaterialStd)"""
    if 'CBMaterialStd' not in cbs:
        return None
    fo = mrl.cb_layout(0x20, 'CBMaterialStd')['iMaterialStdSpecularColorType'][0]
    return struct.unpack_from('<i', mm['block'], cbs['CBMaterialStd'] + 4 * fo)[0]


def sphere_lit(mm, cbs):
    """True for a 4U lit material whose tExtendMap is its sphere-map LIGHTING: CBMaterialStd
    iMaterialStdSpecularColorType 2 (Tigerstripe em092's 'XfB__E0__' body / fat body, GU template 'solid_sphere').
    Type 1 is the 'E1' setup (Gogmazios em089's 'XfBA_E1__m00_body', Dalamadur's body1 / body2, 4U Kushala em031's
    body: the other five sphere / reflection ints equal, C): Gogmazios ships it as plain 'solid' and looks right.
    Dalamadur's body1 / body2 on 'solid_sphere' (test 2026-10-21, 7.png: the tail belly = mesh 25 body2, the neck
    belly = mesh 49 body1) lost their albedo in shadow: flat dark plates, grey gaps, white stars at the junctions,
    i.e. the sphere reflection weighted where the 4U specular mask (BM alpha) is LOW (S: GU shader not read), while
    the 'solid' meshes on the same textures (body4_nm / body5_nm) looked right. That test ran with GU's monster light
    EM02 switched off (the real cause of the dark skin, build_speartip.py); type 1 now takes 'solid_e1' (Capcom's
    Kushala conversion of the same preset), not the type-2 template."""
    return spec_type(mm, cbs) == 2


def model(S, rom, em4, p, gu, notes):
    """4U MOD + MRL + textures of em024 / em110 (and its _tail piece) -> [(path, type, data)], the parsed main MOD.
    Templates as em089 / em067_01 (mrl_build TEMPLATES): blended -> 'add'; constant-colour (CBMaterialConstant,
    IAFilter2: eye, inner mouth) -> 'unlit'; lit with a sphere-lighting extend map (sphere_lit) -> 'solid_sphere' (none
    on em024 / em110); alpha-tested -> 'solid_at'; else 'solid'. MRL before MOD, as in GU's arcs (a MOD packed first
    loads without materials)."""
    out, gu_tex = [], {}

    def tex_path(src_tex, spec):                       # 4U texture -> GU path (+ its GU specular map)
        if src_tex not in gu_tex:
            t = tex.decode(S[(src_tex, T['TEX'])])
            path = p + 'mod\\%s_%s' % (gu, src_tex.split(em4 + '_')[-1])
            out.append((path, T['TEX'], tex.encode_gu(t, 'bc3')))
            if spec:   # GU specular map '<BM>+A' = the BM alpha (4U specular mask) in R, G, B (build_em089_arc.py)
                s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
                out.append((path + '+A', T['TEX'], tex.encode_gu(s, 'bc3')))
            gu_tex[src_tex] = path
        return gu_tex[src_tex]
    main = None
    for src_name, dst in ((em4, gu), (em4 + '_tail', gu + '_tail')):
        src = P4M.replace('em024', em4) + 'mod\\' + src_name
        d4 = S[(src, T['MOD'])]
        m4, raw = modlib.parse(d4), S[(src, T['MRL'])]
        r4, anims4 = mrl.read(raw), mrl_anim.material_anims(raw)[1]
        tex_paths, tex_index, mats = [], {}, []

        def slot(gp):
            if gp not in tex_index:
                tex_paths.append(gp); tex_index[gp] = len(tex_paths)
            return tex_index[gp]
        for mname in m4['material_names']:
            mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
            assert len(mm) == 1, mname
            mm = mm[0]
            states = [s for s in mm['states'] if s]
            texv = {n: v for n, t, v in mm['params'] if n.startswith('t') and isinstance(v, int) and v}
            cbs = {n: v for n, t, v in mm['params'] if t == 1}
            albedo = r4['textures'][texv['tAlbedoMap'] - 1][1]
            # specular map = the BM itself, as Capcom's GU Kushala (em024_00 body: the same 4U CBMaterialStd sphere /
            # specular ints as Dalamadur's body, the same dark albedo, C). The '+A' mask (BM alpha as white, Gogmazios'
            # rule) lit the plate rims far above the near-black albedo: dark plates, bright lines and 4-point stars
            # over the whole body (tests 2026-10-21, screenshots 7 / 9)
            slots = {'tAlbedoMap': slot(tex_path(albedo, False)), 'tSpecularMap': slot(tex_path(albedo, False))}
            ext = r4['textures'][texv['tExtendMap'] - 1][1] if 'tExtendMap' in texv else None
            alpha_test = 'BSSolid' in states and mm['words'][7] & mrl_build.W7_ALPHATEST
            consts, extra = {}, dict(bias=(mm['words'][7] >> 16) & 0xF)
            if 'BSAddAlpha' in states or 'BSBlendAlpha' in states:
                key = 'add'
            elif 'CBMaterialConstant' in cbs:
                key = 'unlit'
            elif alpha_test:
                key = 'solid_at'
                extra['alpha_ref'] = (mm['words'][7] >> 8) & 0xFF
            elif ext and sphere_lit(mm, cbs):
                key = 'solid_sphere'
                slots['tSphereMap'] = slot(tex_path(ext, False))
            elif ext and spec_type(mm, cbs) == 1:    # body1 / body2: the 4U sheen (MRL TEMPLATES 'solid_e1' above)
                key = 'solid_e1'
                slots['tSphereMap'] = slot(tex_path(ext, False))
            else:
                key = 'solid'
            if 'CBMaterialStd' in cbs and key == 'solid_e1':
                # 4U albedo / diffuse / emission; specular and reflection stay Capcom's Kushala values
                consts = {k: v for k, v in mrl_anim.static_constants(mm['block'][cbs['CBMaterialStd']:], 1.0).items()
                          if k in (('$Globals', 'fAlbedoColor'), ('CBMaterial', 'fDiffuseColor'),
                                   ('$Globals', 'fEmissionColor'))}
            elif 'CBMaterialStd' in cbs and key in ('solid', 'solid_sphere', 'solid_at'):
                # 4U albedo / diffuse / emission (mrl_anim.static_constants), specular 0.5 as em067_01's sphere
                # materials (4U diffuse alpha 1.0 here, so fTransparency stays the template's)
                consts = {k: v for k, v in mrl_anim.static_constants(mm['block'][cbs['CBMaterialStd']:], 1.0).items()
                          if k in (('$Globals', 'fAlbedoColor'), ('CBMaterial', 'fDiffuseColor'),
                                   ('$Globals', 'fEmissionColor'))}
                if key == 'solid_sphere':   # the template's em019 value is a red tint (0.7, 0.3, 0.3); 4U is grey
                    consts[('$Globals', 'fSpecularColor')] = (0.5, 0.5, 0.5)
                elif key in ('solid', 'solid_at'):   # 4U em024 / em110: no environment map (bMaterialStdEnvMap 0)
                    # on any material, so no cube reflection (the em030 template's 0.1); body1 / body2's extend-map
                    # reflection is 'solid_e1''s sphere map (2026-10-22). The lit plate rims of the tail's
                    # underside (test 2026-10-21) were body2 = mesh 25 on 'solid_sphere', not this cube term.
                    consts[('CBMaterial', 'fReflectiveColor')] = (0.0, 0.0, 0.0)
            mt = re.search(r'_m(\d\d)_', mname)
            if mt: extra['mtype'] = int(mt.group(1))
            ents4 = anims4.get(mm['name'], [])
            if ents4:   # 4U material animations (rage glow, eye): converted, none autoplays; the class plays them
                try:
                    extra['anim'] = mrl_anim.build(mrl_anim.gu_entries(ents4, mrl_build.cb_words(rom, key),
                                                                       autoplay=(), alpha=1.0))
                    anote = ', %d animations' % len(ents4)
                except Exception as e:      # noqa: BLE001 (reported, the material stays static)
                    anote = ', %d animations NOT converted (%s)' % (len(ents4), e)
            else:
                anote = ''
            rs = [RS_MAP.get(s, s) for s in states if s.startswith('RS')]
            mats.append((mname, key, slots, rs, consts, extra))
            notes.append('%s material %s: template %s%s%s%s' % (dst, mname, key, ', sphere %s' % ext.split('\\')[-1]
                                                                if key in ('solid_sphere', 'solid_e1') else '', anote,
                                                                ', raster %s' % rs if rs != [s for s in states if
                                                                                            s.startswith('RS')] else ''))
        mod_bytes = mod4u2gu.convert(d4)
        mrl_bytes = mrl_build.build(rom, mats, tex_paths)
        assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
        out += [(p + 'mod\\' + dst, T['MRL'], mrl_bytes), (p + 'mod\\' + dst, T['MOD'], mod_bytes)]
        if main is None: main = m4
    return out, main


def visibility_xfs(emd, donor_xfs, groups, role, notes, gu):
    """XFS parts states: every one of the donor's states = the half's spawn visibility (4U rows at spawn: no break,
    rage, sever or Shah state, emdata4u.row_visible with state word 0) minus the groups its class hides at spawn."""
    rows = emdata4u.part_rows(emd)
    vis = [(g, g not in HIDE[role] and emdata4u.row_visible(rows, g, word=0)) for g in groups]
    r, states = emdata4u.parse_xfs_states(donor_xfs)
    data, nobj = emdata4u.xfs_states([vis] * len(states))
    head = bytearray(donor_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    notes.append('%s XFS: %d states, visible at spawn %s' % (gu, len(states), [g for g, v in vis if v]))
    return bytes(head) + data


def hts_bones(b):
    """HTS groups from +0x10 {u32 count, u32 offset}, 48-B records {u16 bone A, u16 bone B, u16 shape (2 = capsule)}"""
    for g in range(struct.unpack_from('<I', b, 8)[0]):
        c, o = struct.unpack_from('<II', b, 16 + 8 * g)
        for k in range(c):
            a, bb, shape = struct.unpack_from('<HHH', b, o + 48 * k)
            yield a
            if shape == 2: yield bb


def data_files(em4, p, gu, mod4, notes):
    """4U emd / etd of one half -> {field: (path, type, data)}: attackdata, hitsize, bodydata, cambodydata, dtbase /
    dttune (dt_convert on the donor). Every bone they name exists in the model (4U bone IDs = model IDs)."""
    d4 = emdata4u.load_4u(em4)
    ids = {i for i in range(256) if mod4['remap'][i] != 255}
    out = {26: ('enemy\\hit_data\\%s_attackdata' % gu, 0x70BB64BA, emdata4u.attackdata(d4['etd'])),
           28: ('enemy\\hit_data\\%s_hitsize' % gu, 0x5653C1B0, emdata4u.hitsize(d4['etd'])),
           30: ('enemy\\body_data\\%s_bodydata' % gu, T['BDD'], emdata4u.bodydata(d4['emd'], 8)),
           31: ('enemy\\cam_body_data\\%s_cambodydata' % gu, T['BDD'], emdata4u.bodydata(d4['emd'], 9))}
    bad = sorted({b for b in hts_bones(out[28][2])} - ids - {255})
    assert not bad, '%s hitsize names bones missing from the model: %s' % (em4, bad)
    for k in (30, 31):
        b = out[k][2]
        n = struct.unpack_from('<I', b, 8)[0]
        bad = {struct.unpack_from('<H', b, 16 + 44 * i + o)[0] for i in range(n) for o in (0, 2)} - ids - {0xFFFF}
        assert not bad, '%s %s names bones missing from the model: %s' % (em4, FIELD_KIND[k], sorted(bad))
    for k, kind, typ in ((32, 'dtbase', T['DTB']), (33, 'dttune', 0x48E8AC29)):
        pre = os.path.join(DT_DIR, 'dt_%s' % em4, '%s.bin' % kind)
        assert os.path.exists(pre), 'run tools/dt_convert.py build %s %s %s first (build.sh step dt)' % (
            em4, DONOR, os.path.dirname(pre))
        out[k] = ('enemy\\%s\\%s_%s' % ('dt_base' if k == 32 else 'dt_tune', gu, kind), typ, open(pre, 'rb').read())
    notes.append('%s data: %d attacks, %d hitsize groups, bodydata %d / cambodydata %d records (4U %s)' % (
        gu, struct.unpack_from('<I', out[26][2], 8)[0],          # HDE header: count at +8 (emdata4u.attackdata)
        struct.unpack_from('<I', out[28][2], 8)[0], struct.unpack_from('<I', out[30][2], 8)[0],
        struct.unpack_from('<I', out[31][2], 8)[0], em4))
    return out


def area_soil(notes):
    """RGBA area colour for the effects: the Speartip Crag arena's area_color_soil (4U stage\\m08d\\m08a01d\\sdl\\
    m08a01d-col, same SDL layout as the Battlequarters' m19a03d-col whose soil efl4u2gu documents, colour +0xd0)."""
    ref = open(os.path.join(ROOT, 'dump/m19_unpacked/m19a03/stage/m19d/m19a03d/sdl/m19a03d-col.4c0db839'), 'rb').read()
    _, ents = arcpack.read(open(os.path.join(ROOT, 'dump/romfs/loc/data/m08a01.arc'), 'rb').read())
    d = [d for p, t, d in ents if p == 'stage\\m08d\\m08a01d\\sdl\\m08a01d-col']
    assert len(d) == 1 and len(d[0]) == len(ref) and re.findall(rb'[ -~]{4,}', d[0]) == re.findall(rb'[ -~]{4,}', ref), \
        'm08a01d-col layout'
    soil = bytes(round(255 * x) for x in struct.unpack_from('<4f', d[0], 0xd0))
    notes.append('effect area colour: Speartip Crag arena soil %s' % (tuple(soil),))
    return soil


EM_COND = 70        # head condition id answered by em090_cond (dala_cond_em): the em number, 24 or 110
EMC_LEN = {0x00: 3, 0x01: 5, 0x14: 2, 0x20: 2}                                   # plain ops: op + args
EMC_BLOCK = {0x02: 2, 0x0a: 2, 0x11: 3, 0x1c: 2, 0x46: 2, 0x6a: 2, 0x6f: 3}     # block ops: length of `op 00 ..`


def emc_em_switch(cmd):
    """GU has no op 0x46 (4U 0x951ff0: switch on the em number W+0x1c0); GU's handler 0x8470c skips the token, so
    every case body of a 0x46 block runs in turn (the head root g0 s0 called the Shah and the rank selector on every
    pass). Rewrite each one as the same block on op 0x6f (monster condition, GU slot 133) with EM_COND: `46 00` ->
    `6f 00 70`, `46 01 v` -> `6f 01 v`, `46 02` -> `6f 02`, `46 ff` -> `6f ff`. Lengths are GU's (main 0x1732c8c); an
    op outside the Dalamadur set raises KeyError. The tail table has no 0x46."""
    ver, groups = emc.parse(cmd)
    out = []
    for g in groups:
        ng = []
        for s in g:
            b, i = bytearray(), 0
            while i < len(s):
                op = s[i]
                if op == 0xff:
                    b += s[i:]
                    break
                n = EMC_LEN[op] if op in EMC_LEN else EMC_BLOCK[op] if s[i + 1] == 0 else 3 if s[i + 1] == 1 else 2
                if op == 0x46:
                    b += bytes([0x6f, 0, EM_COND]) if s[i + 1] == 0 else bytes([0x6f]) + s[i + 1:i + n]
                else:
                    b += s[i:i + n]
                i += n
            ng.append(bytes(b))
        out.append(ng)
    return emc.build(out, ver)


def pel_slot_end(pel, ids):
    """PEL v15 -> (PEL, sorted ids changed): end mode +0x3a = 1 on the list-1 records (the PSL posts, slot kind 4)
    whose id is in `ids` (4U MEF slot mode 1). List 2 (code posts) keeps the tail's mode: without a PSL controller an
    end-mode-1 effect is never stopped (below).
    4U (C): MEF byte 1 = slot mode. cMhMotionEffect create 0x391b50: 0 = one-shot, never tracked; 1 = one of 4 tracked
    slots (id +0x4c, effect +0x74, active +0x70, mode +0x5c). Every frame 0x39170c clears the active flags, 0x391a18
    sets them again for the events whose bit is on, 0x390b40 kills (0xc470dc) a mode-1 effect whose flag stayed 0:
    a mode-1 effect lives exactly as long as its event range (or its motion).
    GU (C): the PSL player 0x31d218 / 0x31d530 gives each posted effect +0x194 = &controller+0xc4[slot] (0x31d1d4) and
    pulses bits there: 2 on the run's falling edge (slot 8 0x31d200), 4 on a motion change, 8 when the frame goes
    back (wrap); a frozen motion (same motion and frame) returns early. The effect (0x329668) latches 2 / 4 / 8 into
    +0x198 / +0x199 / +0x19a; 0x329dbc on record +0x3a (effect +0xca): end mode 0 stops on +0x199 / +0x19a only and
    ends when the effect ends; end mode 1 stops on +0x198 / +0x199, and a finished effect goes to state 3, which the
    state switch 0x3296ec runs like state 0 (S: replayed until the stop; 4U re-creates only under 0x391a18's test).
    Our tail PEL_TAIL has end mode 0 for every MEF record: a mode-1 effect outlived its range until the motion
    changed, and the death motion 0x33d, frozen on its last frame (dala_react.c), never changes: em024_012 element 1
    of record 253 (frames 35-72, joint 6 + (0, 600, 500)) burned on forever where it was placed (test 2026-10-21).
    Capcom's GU monsters (72 enemy arcs, PSL runs vs their PEL record, S): runs > 5 frames have end mode 1 in 2130 of
    2213, 1-frame runs end mode 0 in 6795 of 6859; Dalamadur's slot-mode-1 records are its multi-frame runs."""
    lists = efl4u2gu.pel_lists(pel)
    (n0, b0), (n1, b1), (n2, b2) = lists

    def join(body1):
        return pel[:8] + struct.pack('<I', n0) + b0 + struct.pack('<I', n1) + body1 + struct.pack('<I', n2) + b2

    assert join(b1) == pel
    b1, i, hit = bytearray(b1), 0, []
    for _ in range(n1):
        i += 1 + b1[i] + 2                          # u8 path length, path, 2 bytes, then the 160-B record
        rid = struct.unpack_from('<H', b1, i + 0x30)[0]
        if rid in ids:
            b1[i + 0x3a] = 1
            hit.append(rid)
        i += 160
    assert i == len(b1)
    return join(bytes(b1)), sorted(hit)


def effects(em4, gu, soil, notes):
    """4U effects of em024 / em110 (tools/efl4u2gu.py effect_set). MEF _0 (motion effects, ids < 2000) = PEL list 1;
    MEF _1 (ids 2000+; no class code posts them, the motions' LMT events do: 4U 0x391a18) joins as extra records.
    MEF groups: the em's own EFL family, qe 6 / 13. MEF slot mode 1 -> PEL end mode 1 (pel_slot_end)."""
    S = efl4u2gu.sources(os.path.join(ROOT, 'dump/romfs/data/%s.arc' % em4), [])
    num = int(em4[2:])
    groups = {num: 'effect\\efl\\em\\%s\\%s_%%03d' % (em4, em4)}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (6, 13)})
    extra = []
    for r in efl4u2gu.mef_records(S[('effect\\mef\\em\\%s_1' % em4, T['MEF'])]):
        fam = groups.get(r['grp'])
        if fam and (fam % r['file'], efl4u2gu.T['EFL']) in S:
            extra.append((fam % r['file'], r))
        else:
            notes.append('%s MEF _1 id %d: group %d file %d has no 4U EFL -> no PEL record' % (gu, r['id'], r['grp'],
                                                                                              r['file']))
    n_mef = len(extra)
    # the class's own code posts (no MEF record in 4U: module dala_efx.c has the 4U sources; ids = its DALA_EFX_*).
    # Attached in 4U (joint / shell) -> the tail that follows its target (follow); world-position posts (shell
    # impacts) place once. Both PELs hold every record (the tails post their head's PEL); 2910 / 2911 = the 0xc48378
    # colour of em 83 / em 111; group 35 / 81 elements 0 / 1 / 4 / 5 / 6 / 7 = the em's _000 / _001 / _005 / _006 /
    # _007 / _009 (C). 2950 is attached in 4U too, but to a shell that never moves: placed once on it (as the blasts).
    cm, qe, em = 'effect\\efl\\cm\\cm000\\cm000_002', 'effect\\efl\\qe\\qe013\\qe013_002', groups[num]
    zero = (0.0, 0.0, 0.0)
    for rid, path, joint, pos, scl, k, col, follow in (
            (2800, cm, 200, (3850.0, -945.0, -805.0), 8.0, 2, None, True),
            (2801, cm, 5, (0.0, 500.0, 1000.0), 8.0, 2, None, True),
            (2802, cm, 142, (970.0, -110.0, 865.0), 8.0, 2, None, True),
            (2900, em % 3, -1, zero, 1.0, -1, None, True),                 # meteor
            (2910, qe, 157, (0.0, 0.0, -950.0), 4.5, -1, (120, 85, 80, 255), True),
            (2911, qe, 157, (0.0, 0.0, -950.0), 4.5, -1, (143, 76, 58, 255), True),
            (2920, em % 0, -1, zero, 3.5, -1, None, True),                 # uShell001 fireball body
            (2921, em % 1, -1, zero, 1.0, 1, None, False),                 # its wall hit, kinds 24 / 88
            (2922, em % 1, -1, zero, 1.2, 1, None, False),                 # wall hit, kinds 25 / 89
            (2923, em % 1, -1, zero, 1.2, 0, None, False),                 # ground hit, kinds 25 / 89
            (2930, em % 5, -1, zero, 1.2, -1, None, False),                # uShell003 blasts 113 / 126 / 160 / 162
            (2931, em % 1, -1, zero, 1.5, 0, None, False),                 # uShell003 burn 112 / 159
            (2940, em % 9, -1, zero, (13.0, 13.0, 12.0), -1, None, False),  # uShell016 beam: z = 12000 / 1000,
            # x / y = curve 0xfd1514 of uEffect015 records 2 / 6 = constant 13 (C); world post moved every frame
            # (dala_efx_post_beam); following, it was not drawn (as Gogmazios' laser)
            (2950, em % 6, -1, zero, 1.0, -1, None, False),                # uShell038 meteor scale (still shell)
            (2951, em % 7, -1, zero, 1.0, -1, None, False),                # uShell038 end, at the point
            (2960, em % 16, 4, (0.0, -500.0, 1100.0), 1.0, 3, None, True),      # heat aura zone 0 (uMhEftCtrl004)
            (2961, em % 16, 101, (500.0, 1300.0, -700.0), 1.0, 4, None, True),   # heat aura zone 1
            # Shah's crimson zones (dala_shah.c): uEffect003 subtypes 4 / 5 / 6 = group 81 elements 23 / 26 / 27 =
            # _200 / _203 / _204, mask 1 while armed; the expiry post 0x775f2c: the same files, mask 2. Authored in
            # world space, posted at position 0 (placed once). em024 has no _2xx: em090_00u gets placeholders
            # (_003), never posted (dala_shah.c returns at once for Dalamadur).
            (2970, em % (200 if num == 110 else 3), -1, zero, 1.0, 0, None, False),
            (2971, em % (203 if num == 110 else 3), -1, zero, 1.0, 0, None, False),
            (2972, em % (204 if num == 110 else 3), -1, zero, 1.0, 0, None, False),
            (2973, em % (200 if num == 110 else 3), -1, zero, 1.0, 1, None, False),
            (2974, em % (203 if num == 110 else 3), -1, zero, 1.0, 1, None, False),
            (2975, em % (204 if num == 110 else 3), -1, zero, 1.0, 1, None, False)):
        extra.append((path, dict(id=rid, joint=joint, k=k, pos=pos, rot=zero,
                                 scl=scl if isinstance(scl, tuple) else (scl, scl, scl), follow=follow,
                                 colour=bytes(col) if col else None)))
    pel = 'effect\\pel\\em\\%su' % gu
    psl = 'effect\\psl\\enemy\\%s\\%s\\mot\\%s_%%d' % (gu[:5], gu, gu)
    spec = dict(arc=os.path.join(ROOT, 'dump/romfs/data/%s.arc' % em4), stage_unpacked=[],
                mef='effect\\mef\\em\\%s_0' % em4, em_efl='effect\\efl\\em\\%s\\' % em4, groups=groups, extra=extra,
                lmts=[(P4M.replace('em024', em4) + 'mot\\%s_%d' % (em4, b), psl % b) for b in BANKS], pel=pel,
                soil=soil, list2=None)
    log = []
    out = efl4u2gu.effect_set(spec, log)
    notes.append('%s effects: %d entries (tools/efl4u2gu.py effect_set), %d code-post records from MEF _1 + %d of '
                 'the class (dala_efx.c)' % (gu, len(out), n_mef, len(extra) - n_mef))
    notes.extend('  ' + l for l in log if not l.startswith('EFL '))
    # LMT events name MEF _0 and _1 ids alike (4U 0x391a18: id - 2000 < 7000 -> MEF _1), so both lists' slot modes
    mef = efl4u2gu.mef_records(S[(spec['mef'], T['MEF'])]) + [r for _, r in extra[:n_mef]]
    assert all(r['slot'] in (0, 1) for r in mef), 'MEF slot mode 2 (repeat interval): not mapped'
    out[(pel, efl4u2gu.T['PEL'])], ids = pel_slot_end(out[(pel, efl4u2gu.T['PEL'])],
                                                      {r['id'] for r in mef if r['slot'] == 1})
    notes.append('%s PEL list 1: end mode 1 on the %d records of MEF slot mode 1 (stop at the event range end, as 4U): '
                 '%s' % (gu, len(ids), ' '.join(map(str, ids))))
    fields = {17: (pel, efl4u2gu.T['PEL'])}
    fields.update({18 + b: (psl % b, efl4u2gu.T['PSL']) for b in BANKS})
    return [(p, t, d) for (p, t), d in out.items()], fields


def sound(rom, em4, gu, notes):
    """4U sound call, waves, bank, request of em024 / em110 (tools/snd4u2gu.py monster_entries). The tail halves use
    their head's (4U em083 / em111 carry em024's / em110's sound files). Shah's call list sits at sound\\call\\em\\
    em024 in 4U em110.arc."""
    S = src_arc(em4)
    call = [p for (p, t) in S if p.startswith('sound\\call\\em\\') and t == 0x6E171A6E]
    assert len(call) == 1, call
    spec = dict(name=em4, src=os.path.join(ROOT, 'dump/romfs/data/%s.arc' % em4),
                p4_wave='sound\\se\\em\\%s\\wave\\' % em4, pg_wave='sound\\se\\em\\%s\\wav\\' % gu,
                p4_bank='sound\\se\\em\\%s\\snd_%s' % (em4, em4), pg_bank='sound\\se\\em\\%s\\snd_%s' % (gu, gu),
                p4_call=call[0], pg_call='sound\\call\\em\\%s' % gu, donor_arc='/nativeNX/arc/enemy/%s.arc' % DONOR,
                donor_name='GU Kushala', donor_extra=False)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    notes.extend(log)
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def main():
    img = open(paths.GU_MAIN, 'rb').read()
    rom = RomFS(paths.GU_ROMFS)
    _, dents = arcpack.read(rom.read('/nativeNX/arc/enemy/%s.arc' % DONOR))
    D = {(p, t): d for p, t, d in dents}
    dhash = {(phash(p), t): (p, t) for p, t, _ in dents}
    dman = manifest_of(img, DONOR_INDEX)
    dfield = {k: (fid,) + dhash[fileid_entry(img, fid)] for k, fid in enumerate(dman) if fid != -1}
    reg = {m['name']: m for m in alloc.monsters()}
    notes = {h['gu']: [] for h in HALVES}
    soil = area_soil(notes['em090_00'])
    files = {}            # gu -> {field: (path, type)} of the fields it owns
    extras = {}           # gu -> {name: (path, type)} of its files without a field (IDs after the fields', EXTRA_ORDER)
    data = {}             # (path, type) -> bytes, every file any arc carries
    own_extra = {}        # gu -> [(path, type, data)] files it ships that no field names
    shell_keys = []       # (path, type) of the shell family (every arc: the tails and Shah post shells too)
    exe4 = hagi4u.exe()
    gu_item = items_em090.materials(rom, exe4).gu_item
    for h in HALVES:
        gu, em4, role, nt = h['gu'], h['em4'], h['role'], notes[h['gu']]
        p = 'enemy\\%s\\%s\\' % (gu[:5], gu)
        S = src_arc(em4)
        hg = hagi_em090.files(h['entry'], exe4, gu_item)     # carves per rank: fields 46-50
        own, ext = {}, []
        for k in HAGI:
            _, path, typ = dfield[k]
            own[k] = (path.replace('em024_00', gu), typ); ext.append(own[k] + (hg[k],))
            assert own[k][0] != path, path
        nt.append('carves: tools/hagi_em090.py (fields 46-50, %s)' % h['entry'])
        if role == 'head':
            ents, mod4 = model(S, rom, em4, p, gu, nt)
            ext += ents
            own[0], own[1] = (p + 'mod\\' + gu, T['MOD']), (p + 'mod\\' + gu + '_tail', T['MOD'])
            share = h.get('share')
            for b in BANKS:
                d = S[(P4M.replace('em024', em4) + 'mot\\%s_%d' % (em4, b), T['LMT'])]
                if share and d == data.get(files[share][4 + b]):
                    nt.append('motion list %d = %s\'s (shared)' % (b, share)); continue
                own[4 + b] = (p + 'mot\\%s_%d' % (gu, b), T['LMT']); ext.append(own[4 + b] + (d,))
            cam = [k for k in S if k[1] == T['LCM']]
            assert len(cam) == 1, cam
            own[11] = (p + 'mot\\%s_cam' % gu, T['LCM']); ext.append(own[11] + (lcm4u2gu.convert(S[cam[0]]),))
            cmd = emc_em_switch(emc.to_gu(S[(P4M.replace('em024', em4) + 'data\\%s_cmd' % em4, T['EMC'])]))
            if share and cmd == data.get(files[share][37]):
                nt.append('command table = %s\'s (shared)' % share)
            else:
                own[37] = ('enemy\\cmd_tbl\\%s_cmdtbl' % gu, T['EMC']); ext.append(own[37] + (cmd,))
            fx, fxf = effects(em4, gu, soil, nt)
            ext += fx; own.update(fxf)
            snd, sndf = sound(rom, em4, gu, nt)
            ext += snd; own.update(sndf)
        else:
            mod4 = modlib.parse(S[(P4M + 'mod\\em024', T['MOD'])] if em4 == 'em083' else
                                S[('enemy\\em110\\mod\\em110', T['MOD'])])
            cmd = emc.to_gu(S[('enemy\\%s\\data\\%s_cmd' % (em4, em4), T['EMC'])])
            share = h.get('share')
            if share and cmd == data.get(files[share][37]):
                nt.append('command table = %s\'s (shared)' % share)
            else:
                own[37] = ('enemy\\cmd_tbl\\%s_cmdtbl' % gu, T['EMC']); ext.append(own[37] + (cmd,))
        groups = sorted({x['group'] for x in mod4['mesh_list']})
        own[3] = (p + 'mod\\' + gu, T['XFS'])
        ext.append(own[3] + (visibility_xfs(emdata4u.load_4u(em4)['emd'], D[dfield[3][1:]], groups, role, nt, gu),))
        for k, (path, typ, d) in data_files(em4, p, gu, mod4, nt).items():
            own[k] = (path, typ); ext.append((path, typ, d))
        if gu == 'em090_00':        # files no manifest field names, own IDs after the fields' (module code finds them)
            stqr = os.path.join(DT_DIR, 'bgm_em090.stqr')        # tools/bgm_dalamadur.py: the theme, both phases
            if os.path.exists(stqr):
                extras.setdefault(gu, {})['bgm_stqr'] = (BGM_STQR, 0x167DBBFF)
                ext.append((BGM_STQR, 0x167DBBFF, open(stqr, 'rb').read()))
            else:
                nt.append('no %s yet (tools/bgm_dalamadur.py): no theme' % stqr)
        if gu in WALK:
            src_em, bones = WALK[gu]
            for b in bones:
                f = os.path.join(WALK_DIR, '%s_b%03d.sbc' % (src_em, b))
                if not os.path.exists(f):
                    nt.append('no %s yet (tools/walk4u2gu.py convert): body not walkable' % f); break
                key = ('collision\\%s_g%03d' % (gu, b), T_SBC)
                extras.setdefault(gu, {})['walk_b%03d' % b] = key
                ext.append(key + (open(f, 'rb').read(),))
            else:
                nt.append('walk collision: %d files (4U %s joints %s)' % (len(bones), src_em, list(bones)))
        if gu == 'em090_00':        # donor placeholders, renamed once, shared by the four
            for k in RENAMED:
                if k not in dfield: continue
                _, path, typ = dfield[k]
                new = path.replace('em024_00', 'em090_00')
                assert new != path, path
                own[k] = (new, typ); ext.append((new, typ, D[(path, typ)]))
                nt.append('field %d: placeholder %s (donor %s, renamed)' % (k, path, DONOR))
        if gu == 'em090_00':        # Dalamadur's shell family (module dala_shell.h): the four arcs carry it
            fam, fam_note = shell_family(dents)
            extras.setdefault(gu, {})['shell00'] = (SHELL_DST, T_SHELL)
            ext += fam
            shell_keys[:] = [(fp, ft) for fp, ft, _ in fam]
            nt.append(fam_note)
        for path, typ, d in ext:
            assert data.get((path, typ), d) == d, 'two different files at %s' % path
            data[(path, typ)] = d
        files[gu] = own
        own_extra[gu] = ext

    # ---- manifests: own fields, then the shared ones (head / share / em090_00), then the donor's kept files
    arcs, man_json, extra_json = {}, {}, {}
    for h in HALVES:
        gu, role, nt = h['gu'], h['role'], notes[h['gu']]
        a = reg.get(h['entry'])
        base, last = tuple(a['file_ids']) if a else h['ids']
        if not a: nt.append('not in allocations.toml yet: planned file IDs 0x%x..0x%x, no FILE section' % (base, last))
        own, manifest, src_of, new_files = files[gu], [-1] * 51, {}, []
        late = [] if gu == 'em090_00' else HAGI        # numbered after the extras (see HAGI)
        for k in [k for k in OWN_ORDER[role] if k in own] + sorted(set(own) - set(OWN_ORDER[role]) - set(late)):
            fid = base + len(new_files)
            assert fid <= last, 'file IDs past the range: widen file_ids'
            new_files.append((fid,) + own[k]); manifest[k] = fid; src_of[k] = 'own'
        ex = extras.get(gu, {})
        assert set(ex) <= set(EXTRA_ORDER), 'add new extra files at the end of EXTRA_ORDER: %s' % (set(ex) - set(EXTRA_ORDER))
        extra_ids = {}
        for name in [n for n in EXTRA_ORDER if n in ex]:
            fid = base + len(new_files)
            assert fid <= last, 'file IDs past the range: widen file_ids'
            new_files.append((fid,) + ex[name]); extra_ids[name] = fid
        for k in late:
            fid = base + len(new_files)
            assert fid <= last, 'file IDs past the range: widen file_ids'
            new_files.append((fid,) + own[k]); manifest[k] = fid; src_of[k] = 'own'
        man_json[gu] = (manifest, new_files, src_of)
        extra_json[gu] = extra_ids
        if 'bgm_stqr' in extra_ids:  # module dala_bgm.c DALA_FILE_BGM_STQR (the core's BGM hooks load it by this ID)
            assert extra_ids['bgm_stqr'] == BGM_STQR_FILE_ID, 'bgm stqr at 0x%x, module expects 0x%x' % (
                extra_ids['bgm_stqr'], BGM_STQR_FILE_ID)
        if 'shell00' in extra_ids:   # module dala_shell.h DALA_SHELL_FILE loads the family by this ID
            assert extra_ids['shell00'] == SHELL_FILE_ID, 'shell family def at 0x%x, module expects 0x%x' % (
                extra_ids['shell00'], SHELL_FILE_ID)
    for h in HALVES:              # shared fields take the owner's IDs (owners come first in HALVES): a tail's own kind
        gu = h['gu']              # of field (AI, data) from the other tail, the rest from its head (Shah's tail: Shah's
        manifest, new_files, src_of = man_json[gu]   # model, not em091_00's), then em090_00
        for k in range(51):
            if manifest[k] != -1 or k in KEPT: continue
            order = (h.get('share'), h.get('head')) if h['role'] == 'tail' and k in OWN_ORDER['tail'] else \
                    (h.get('head'), h.get('share'))
            for owner in [x for x in order + ('em090_00',) if x and x != gu]:
                if man_json[owner][0][k] != -1:
                    manifest[k] = man_json[owner][0][k]; src_of[k] = 'shared (%s, its file ID)' % owner
                    break
        for k in KEPT:
            if k in dfield:
                manifest[k] = dfield[k][0]; src_of[k] = 'donor %s (original path + file ID)' % DONOR
    byid = {fid: (p, t) for gu in man_json for fid, p, t in man_json[gu][1]}
    # the donor's files for every field we fill ourselves, and its model / motions / camera / XFS
    drop = {(dfield[k][1], dfield[k][2]) for k in dfield if k not in KEPT}
    drop |= {(p, t) for p, t, _ in dents if p.startswith('enemy\\em024\\em024_00\\')}
    donor_chain = [(p, t, d) for p, t, d in dents if (p, t) not in drop]
    for h in HALVES:
        gu, nt = h['gu'], notes[h['gu']]
        manifest, new_files, src_of = man_json[gu]
        need = []                 # files of the fields this arc names, then the files it owns that no field names
        for k in range(51):
            fid = manifest[k]
            if fid == -1 or k in KEPT: continue
            need.append(byid[fid])
        need += [(p, t) for p, t, _ in own_extra[gu]]
        need += shell_keys        # the shell family (em090_00's file ID; dala_shell.h)
        if h.get('share'):        # Shah: the same theme and walk collision as Dalamadur (4U data identical)
            need += list(extras.get(h['share'], {}).values())
        if h['role'] == 'tail':   # the head's textures, materials, effect and sound files ride along (no field names
            need += [(p, t) for p, t, _ in own_extra[h['head']]]     # them; its data files come too, unused)
        seen, ents = set(), []
        for key in need:
            if key in seen: continue
            seen.add(key); ents.append(key + (data[key],))
        # a file must follow every file it names by path (notes/assets.md "Entry order"): a model fetches its MRL
        # while loading and an MRL its textures, so TEX -> MRL -> MOD -> the rest (test 2026-10-21: model first =
        # no materials, nothing drawn, collision present). Sounds the same way, as GU's own arcs store them (C: em024_00,
        # em001_00, em071_00): waves -> bank -> request (test 2026-10-21: request first = no monster sound at all)
        rank = {T['TEX']: 0, T['MRL']: 1, T['MOD']: 2, snd4u2gu.TG['WAVE']: 4, snd4u2gu.TG['BANK']: 5,
                snd4u2gu.TG['REQ']: 6}
        ents.sort(key=lambda e: rank.get(e[1], 3))
        have = {(p, t) for p, t, _ in ents}
        ents += [(p, t, d) for p, t, d in donor_chain if (p, t) not in have]
        arcs[gu] = ents
        nt.append('arc: %d own / shared files + %d donor chain files' % (len(have), len(ents) - len(have)))

    # ---- verify before writing anything
    built = {}
    for h in HALVES:
        gu = h['gu']
        manifest = man_json[gu][0]
        arc = arcpack.build(arcs[gu])
        ver, back = arcpack.read(arc)
        assert ver == 0x11 and len(back) == len(arcs[gu])
        assert len({(p, t) for p, t, _ in back}) == len(back), 'duplicate entries in %s' % gu
        present = {(phash(p), t) for p, t, _ in back}
        for k in range(51):
            fid = manifest[k]
            if fid == -1: continue
            ht = (phash(byid[fid][0]), byid[fid][1]) if fid in byid else fileid_entry(img, fid)
            assert ht in present, '%s field %d (0x%x) not in its arc' % (gu, k, fid)
        for p, t, d in back:
            if t == T['MOD'] and p.startswith('enemy\\em09'): modlib.parse(d)
            if t == T['TEX'] and p.startswith('enemy\\em09'): tex.decode(d)
        built[gu] = arc

    # ---- write
    for h in HALVES:
        gu, nt = h['gu'], notes[h['gu']]
        manifest, new_files, src_of = man_json[gu]
        out = os.path.join(MON, 'romfs/nativeNX/arc/enemy/%s.arc' % gu)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(built[gu])
        fields = []
        for k in range(51):
            fid = manifest[k]
            if fid == -1:
                fields.append(dict(field=k, kind=FIELD_KIND.get(k, ''), file_id=-1)); continue
            p, t = byid[fid] if fid in byid else dhash[fileid_entry(img, fid)]
            fields.append(dict(field=k, kind=FIELD_KIND.get(k, ''), file_id='0x%x' % fid, path=p, type='0x%08x' % t,
                               source=src_of.get(k, '')))
        a = reg.get(h['entry'])
        json.dump(dict(monster='%s (%s)' % (gu, h['title']), entry=h['entry'], donor=DONOR,
                       file_id_base='0x%x' % (a['file_ids'][0] if a else h['ids'][0]), file_count=len(new_files),
                       manifest=fields, extra={k: '0x%x' % v for k, v in extra_json[gu].items()}, files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t,
                                                    path_hash='0x%08x' % phash(p)) for f, p, t in new_files],
                       notes=nt), open(os.path.join(HERE, '%s_manifest.json' % gu), 'w'), indent=1)
        if a:   # FILE section: the registry manifest of its index and the (path hash, type) of each own file ID
            sec = portdata.Section('FILE')
            sec.u32(a['file_ids'][0], len(new_files), *[x & 0xFFFFFFFF for x in manifest])
            for fid, p, t in new_files:
                sec.u32(phash(p), t)
            print('wrote', portdata.write_section(h['entry'], sec))
        print('%s: %d entries, %.1f MB -> %s; own file IDs %d' % (gu, len(arcs[gu]), len(built[gu]) / 1e6, out,
                                                                  len(new_files)))
        for n in nt: print('  ', n)


if __name__ == '__main__':
    main()
