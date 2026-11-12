"""build_seltas_arc.py : build nativeNX/arc/enemy/em076_01.arc (Desert Seltas = GU Seltas variant 1, ID 0x14c) and em069_01.arc (Desert Seltas Queen =
GU Seltas Queen variant 1, ID 0x145), each with its data file section FILE.

  build_seltas_arc.py [ENTRY ...]      build, verify, then write (paths in monsters/desert_seltas/; default both entries):
      romfs/nativeNX/arc/enemy/<ours>.arc
      tools/<ours>_manifest.json          (51 manifest fields, file IDs, sources)
      gen/[<entry>/]FILE.sec              (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em001_02.arc): the variant's own files under enemy\\emNNN\\emNNN_01\\..., the files it shares with variant 0 under
emNNN_00's paths and file IDs (Shrouded Nerscylla's builder, monsters/shrouded_nerscylla/tools/build_em070_01_arc.py, is the template; the readings it
names hold here unless written otherwise). GU's classes run them as variant 1 and keep 4U's tests of em 94 / 95 as variant tests (notes/plan.md).
  own, converted from MH4U em094.arc / em095.arc:
      mod\\<ours> MOD + MRL         tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py)
      mod\\<ours>_NN_BM (+A)        albedo textures (BC3) + GU specular maps made from their alpha
      mod\\<ours> XFS               GU's parts states for their mesh groups; 4U group 50 (their frenzy look: the Queen's 'XfB__m02_virus', shown by
                                     4U's part rows only in state 10) hidden in the base states GU's slot 132 applies every frame (C: Seltas 0xfc95e8
                                     state 0 / 8, Queen 0xf8d71c / 0xf8d728 states 0 and 8), as Tidal Najarala's
      mot\\<ours>_N                 their 4U motion lists (LMT 67) with GU's finer tracks where GU has the motion (motion_bank), slots they lack filled
                                     from GU's; their own slots (Desert Seltas bank 3 slot 80, bank 4 slots 81, 90..94; the Queen's 86 more) stay 4U's
      cmd_tbl\\<ours>_cmdtbl        4U em025_cmd for em 94 / em095_cmd for em 95 in GU's language (cmdtbl()): GU's tables keep their 4U bodies as op-0x92
                                     variant-1 blocks (C: equal in every such script), GU's variant-1 body where the engine needs GU's language; 4U
                                     scripts past GU's count of a group appended (the Queen's g14 s0, in 4U em095_cmd only: GU's class asks for group
                                     14 where 4U's does, GU f8c7c0 = 4U 0x798418, C)
      effects                        tools/efl4u2gu.py effect_set: their EFLs (+ the qe families their MEF names) under their 4U paths, PEL u list 1
                                     from the MEF, list 2 = GU's (the GU class posts its ids: shell and code effects stay GU's, a DEVIATION where 4U's
                                     differ: notes/plan.md "Effects"), a PSL per motion list; GU's common effects where their motions are GU's (the
                                     user's rule), and there GU's dust instead of their own 4U sand (the rule on environment effects);
                                     4U ground-flag records as world records on their ground (module/seltas_fx.c); grey rock chunks hidden
                                     (hide_grey_models 'chunks', issue #6), 4U's common dust and their own sand at 1x (DUST_1X, own_sand())
      sound call / waves / bank / request   tools/snd4u2gu.py monster_entries
      dt_tune\\<ours>_dttune        their 4U values (tools/dt_convert.py on GU's file) + GU's retunes of the species where their 4U bytes equal the
                                     species' (dttune())
      data files                     Desert Seltas: dtbase (3 bytes of his own), bodydata (21 records: his body is another shape); the Queen:
                                     attackdata (GU's 70 records: GU moved her 4U attacks 69 / 70 to its 47 / 51, C: GU 47 / 51 = 4U 69 / 70 up to
                                     GU's retune bytes 28 / 31, GU 69 is empty, and GU's handlers post 47 / 51 where 4U's post 69 / 70 for her; 4U's
                                     70 / 71 past GU's count would be posted by nothing), hitsize (her 4U groups, GU's where hers
                                     equal the Queen's), bodydata (GU's + her 4U records)
      hagi\\hagi_s0..s4_<ours>      carves: 4U G body / shiny tables in s4, GU's filler in s0..s3 (tools/hagi_seltas.py)
      area_link / area_eat / map_info / area_select   GU's + their 4U maps (tools/routes_seltas.py)
      shell\\<ours>_shellNN\\...     their own 4U shots: copies of GU's families 0x13b / 0x139 (his) and 0x127 (hers) on their own PEL and hit
                                     data, at the end of the arc, file IDs after the manifest's (tools/shots_seltas.py; module/seltas_shots.c
                                     swaps them in for their posts only)
  shared, GU emNNN_00 (original paths + file IDs): camera, sound triggers (PTS), PEL c, cambodydata, dtbparts, action tune, area_patrol, the shell
      families (their defs name GU's PEL u, which stays in the arc for them; Desert Seltas meets a normal Seltas in 4U m10818, so no file under a GU
      path may differ from GU's).
Inputs besides the arcs: dump/converted/em094/dt_em094 / dt_em025 and dump/converted/em095/dt_em095 / dt_em026 (build.py step dt) and the 4U ROM
(core effect arcs, area colours).
"""
import difflib, json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, ctr, efl4u2gu, emc, emdata4u, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, snd4u2gu, tex

FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02)
GU_RS = {a for _, (a, _) in mrl.records(0x22).items() if a and a.startswith('RS')}     # GU's rasterizer states
BS = chr(92)
HIDDEN_GROUPS = (50,)
# 4U's common dust at 1x (Shrouded Nerscylla's DUST_1X: 4U's Intensity 1 baked x2 draws it white-yellow in GU); their own sand too (own_sand(),
# since 0.1.4; every soil-coloured file since 0.1.8); their other own effects keep the bake
DUST_1X = tuple('qe006_%03d' % k for k in range(64))
# Her shot (0.1.13; the user on 0.1.12: "die Königin schießt ab und zu so 3 riesen Geschosse ab, die sind zu hell belichtet"): her 7/9 7/15 7/34 7/79
# post three of GU's shell 0x127 on our copy (tools/shots_seltas.py: flight em095_020, hit em095_021; her ground splash em095_021 too). Their
# particle units carry 4U's Intensity 1 (C: em095_020 units ff708c87 / ffb5fff0, em095_021 ff609e90 / ff7fb299), and x2 clamps them to nearly
# white (b5fff0 -> ffffff); his flight em094_201 has no such unit (his shots look right to the user). At 1x like the dust: a DEVIATION from 4U's
# brightness, for GU's look (the dust's lesson: 4U's x2 draws too bright in GU).
SHOT_1X = ('em095_020', 'em095_021')
SOLID_FILL = (127, 127, 127, 255)       # colourless 4U solid effect meshes: vertex RGB 127 = 1.0
# Her underside glow 'XfB__m03_add' (0.1.17; the user on 0.1.16: "am Schwanz der Königin wirken die Texturen an der Unterseite des Schwanzes komisch"):
# a 4U constant-colour additive overlay (CBMaterialConstant, RSMeshBias10; mesh 29, g14: 112 vertices on the underside of her thorax and abdomen, 90 of
# them on body vertices). 4U em095's material = 4U em026's (the Seltas Queen) byte for byte, its 4 animations too, and Capcom's GU em069_00 draws it
# unlit with the constant's alpha: 'Normal' (alpha 0 = off), 'Angry_Start' / 'Angry_Repeat' / 'Angry_End' (C: the names are GU strings, the keys 4U's
# 1:1 on $Globals.fConstantColor, mrl_anim.CONSTANT_MAP). On 'add' it was lit, its alpha the albedo's, and its 4 entries had lost every track (no
# mapping), so it never went off. Template: GU em076_00 mat 3 'XfB__m02_add', whose words and parameter block equal em069_00's m03_add except the
# material type (C), without an animation block (mrl_build.load_template refuses one); the type (m03) comes from the name as for every material.
ADD_CONST = ('/nativeNX/arc/enemy/em076_00.arc', 'enemy\\em076\\em076_00\\mod\\em076_00', 3)
mrl_build.TEMPLATES.setdefault('add_const', ADD_CONST)
assert mrl_build.TEMPLATES['add_const'] == ADD_CONST
# ---- AI tables. GU's language replaces 4U's where the engine needs it (C, 2026-11-09, both tables against GU's by script):
#   g0 s0 (GU's area advance op 0x9e), g0 s1 (patrol: GU ops 0x4e 0x96 0x97, 4U's 0x8a 0x8b), g0 s6 (area move: GU 0x94 0x95, 4U 0x03 0x40 0x49 0x4a),
#   g20 s0 (GU 0xa0 0xa1), g4 s0 (GU ends it with the native 0/255 in both species' tables); Desert Seltas also g1 s29 (4U ops 0x05 0x49 0x8c) and g1 s34
#   (0x8d). GU's extra entries are appended (GU's class picks group-1 scripts by number). Every other script is their 4U body: GU's own retunes of the
#   species (g1 s46, g1 s81, g12 s0, g13 s0, the Queen's g2 / g18 calls of 1/26 GU took out ...) do not come, his own AI is 4U's.
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_4U_ONLY = {0x03, 0x05, 0x40, 0x46, 0x49, 0x4a, 0x7e, 0x8a, 0x8b, 0x8c, 0x8d, 0x87}
# 4U stage -> GU stage in a kept `2a 01 NN` case: Anc. Steppe 1 -> 11, Primal Forest 3 -> 13, Frozen Seaway 4 -> 14, Arena 11 -> 9, Volcanic Hollow 15
# -> 12, Dunes 17 / 18 -> 5; Sunken Hollow 2, Heaven's Mount 5 and 13 (a stage of lookups in both classes' slot 66, S: Everwood) have none here
STAGE_CASE = {1: 11, 2: 0xFF, 3: 13, 4: 14, 5: 0xFF, 11: 9, 13: 0xFF, 15: 12, 17: 5, 18: 5}
OP_FRENZY = 0x87

ENTRIES = {
    'desert_seltas': dict(
        title='Desert Seltas', em4u='em094', parent='em025', em=94, gu='em076_00', ours='em076_01', num='076',
        banks=(0, 1, 2, 3, 4), mod4u='enemy\\em094\\mod\\em094', mot4u='enemy\\em094\\mot\\em094_%d',
        cmd='enemy\\em025\\data\\em025_cmd', emc_gu={(0, 0), (0, 1), (0, 6), (20, 0), (4, 0), (1, 29), (1, 34)},
        mef='effect\\mef\\em\\em094_0', efl='effect\\efl\\em\\em094\\em094_%03d', efl_dir='effect\\efl\\em\\em094\\',
        sound=dict(name='em094', p4_wave='sound\\se\\em\\em094\\wave\\', p4_bank='sound\\se\\em\\em094\\snd_em094', p4_call='sound\\call\\em\\em025'),
        base_states=(0, 8),
        # file IDs are given in this order (append only: IDs never move once shipped)
        own_order=[0, 3, 4, 5, 6, 7, 8, 37, 17, 18, 19, 20, 21, 22, 12, 13, 33, 32, 30, 46, 47, 48, 49, 50, 40, 42, 43, 41],
        dt='em094'),
    'desert_seltas_queen': dict(
        title='Desert Seltas Queen', em4u='em095', parent='em026', em=95, gu='em069_00', ours='em069_01', num='069',
        banks=(0, 3, 4), mod4u='enemy\\em095\\mod\\em095', mot4u='enemy\\em095\\mot\\em095_%d',
        cmd='enemy\\em095\\data\\em095_cmd', emc_gu={(0, 0), (0, 1), (0, 6), (20, 0), (4, 0)},
        mef='effect\\mef\\em\\em095_0', efl='effect\\efl\\em\\em095\\em095_%03d', efl_dir='effect\\efl\\em\\em095\\',
        sound=dict(name='em095', p4_wave='sound\\se\\em\\em095\\wave\\', p4_bank='sound\\se\\em\\em095\\snd_em095', p4_call='sound\\call\\em\\em095'),
        base_states=(0, 8),
        own_order=[0, 3, 4, 7, 8, 37, 17, 18, 21, 22, 12, 13, 33, 26, 28, 30, 46, 47, 48, 49, 50, 40, 42, 43, 41],
        dt='em095'),
}


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


class E:
    """one entry's paths and allocations"""
    def __init__(s, name):
        s.name, s.c = name, ENTRIES[name]
        c = s.c
        s.alloc = alloc.monster(name)
        s.fid_base, s.fid_last = s.alloc['file_ids']
        s.src4u = os.path.join(ROOT, 'dump/romfs/data/%s.arc' % c['em4u'])
        s.gu_arc = '/nativeNX/arc/enemy/%s.arc' % c['gu']
        s.out_arc = os.path.join(MON, 'romfs/nativeNX/arc/enemy/%s.arc' % c['ours'])
        s.out_json = os.path.join(HERE, '%s_manifest.json' % c['ours'])
        s.P0 = 'enemy\\em%s\\%s\\' % (c['num'], c['gu'])
        s.P = 'enemy\\em%s\\%s\\' % (c['num'], c['ours'])
        s.pel_u = 'effect\\pel\\em\\%su' % c['ours']
        s.pel_gu = 'effect\\pel\\em\\%su' % c['gu']
        s.psl = 'effect\\psl\\enemy\\em%s\\%s\\mot\\%s_%%d' % (c['num'], c['ours'], c['ours'])
        s.dt_dir = os.path.join(ROOT, 'dump/converted', c['dt'])


def textures(e, S, r4, slots, out, gu_tex):
    """the GU texture paths of one 4U material's albedo: BC3 + its '+A' specular map (the BM alpha in R, G, B, alpha 255; 4U specular mask)"""
    paths_of = {}
    for slot, v in slots.items():
        if not v: continue
        src = r4['textures'][v - 1][1]
        name = src.split('\\')[-1]
        if src not in gu_tex:
            t = tex.decode(S[(src, T['TEX'])])
            path = e.P + 'mod\\%s_' % e.c['ours'] + name.split(e.c['em4u'] + '_')[-1]
            sp = np.empty_like(t); sp[..., 0] = sp[..., 1] = sp[..., 2] = t[..., 3]; sp[..., 3] = 255
            out += [(path, T['TEX'], tex.encode_gu(t, 'bc3')), (path + '+A', T['TEX'], tex.encode_gu(sp, 'bc3'))]
            gu_tex[src] = path
        paths_of[slot] = gu_tex[src]
        if slot == 'tAlbedoMap':
            paths_of['tSpecularMap'] = gu_tex[src] + '+A'
    return paths_of


def model(e, S, rom, gu_tex, notes):
    """the 4U MOD + MRL (+ textures) -> [(path, type, data)], the parsed 4U MOD. Templates (Shrouded Nerscylla's rules): additive -> 'add', 4U
    BSBlendAlpha -> 'blend' with the material's own constants, emissive -> 'unlit', a lit E0 material with a tExtendMap -> 'solid_sphere', alpha-tested
    -> 'solid_at', else 'solid'; an additive one whose animations drive the 4U constant colour (her underside glow) -> 'add_const' (Capcom's own,
    ADD_CONST above). Every 4U material animation is converted. MRL before MOD, as in GU's arcs."""
    src = e.c['mod4u']
    d4, d4m = S[(src, T['MOD'])], S[(src, T['MRL'])]
    m4, r4 = modlib.parse(d4), mrl.read(d4m)
    anims4 = mrl_anim.material_anims(d4m)[1]
    out, tex_paths, tex_index, mats = [], [], {}, []
    for mname in m4['material_names']:
        mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
        assert len(mm) == 1, mname
        mm = mm[0]
        states = [s for s in mm['states'] if s]
        gp = textures(e, S, r4, {n: v for n, _, v in mm['params'] if n == 'tAlbedoMap'}, out, gu_tex)
        slots = {}
        for slot, path in gp.items():
            if path not in tex_index:
                tex_paths.append(path); tex_index[path] = len(tex_paths)
            slots[slot] = tex_index[path]
        std = struct.unpack_from('<8f', mm['block'], 0x60)
        emissive = max(std[0:3]) > 0 and max(std[4:7]) == 0
        key = 'blend' if 'BSBlendAlpha' in states else 'add' if 'BSAddAlpha' in states else 'unlit' if emissive else 'solid'
        alpha_test = 'BSSolid' in states and mm['words'][7] & mrl_build.W7_ALPHATEST
        if alpha_test: key = 'solid_at'
        w7 = mm['words'][7]
        extra = dict(mtype=int(re.search(r'_m(\d\d)_', mname).group(1)), bias=(w7 >> 16) & 0xF)
        if alpha_test: extra['alpha_ref'] = (w7 >> 8) & 0xFF
        consts = {}
        ext = [v for n, t, v in mm['params'] if n == 'tExtendMap' and v]
        if key == 'solid' and ext:
            key = 'solid_sphere'
            ext_tex = r4['textures'][ext[0] - 1][1]
            if ext_tex not in gu_tex:
                path = e.P + 'mod\\%s_' % e.c['ours'] + ext_tex.split(e.c['em4u'] + '_')[-1]
                out.append((path, T['TEX'], tex.encode_gu(tex.decode(S[(ext_tex, T['TEX'])]), 'bc3')))
                gu_tex[ext_tex] = path
            if gu_tex[ext_tex] not in tex_index:
                tex_paths.append(gu_tex[ext_tex]); tex_index[gu_tex[ext_tex]] = len(tex_paths)
            slots['tSphereMap'] = tex_index[gu_tex[ext_tex]]
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            consts = {k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], 1.0).items()
                      if k in (('$Globals', 'fAlbedoColor'), ('CBMaterial', 'fDiffuseColor'), ('$Globals', 'fEmissionColor'))}
            consts[('$Globals', 'fSpecularColor')] = (0.5, 0.5, 0.5)
        ents4 = anims4.get(mm['name'], [])
        const = key == 'add' and any(mrl_anim.var_name(0x20, t['cb'], t['var'])[0] == 'CBMaterialConstant' for x in ents4 for t in x['tracks'])
        if const:
            key = 'add_const'              # her underside glow (ADD_CONST above)
        if ents4:
            std = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd']
            if std:                        # a constant-colour material (CBMaterialConstant: the Queen's additive ones) has no Std block to start from
                anim_vars = mrl_anim.animated_targets(ents4)
                consts.update({k: v for k, v in mrl_anim.static_constants(mm['block'][std[0]:], 1.0).items() if k in anim_vars})
            extra['anim'] = mrl_anim.build(mrl_anim.gu_entries(ents4, mrl_build.cb_words(rom, key),
                                                               extra=mrl_anim.CONSTANT_MAP if const else None))
        if key == 'blend':
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            consts.update(mrl_anim.static_constants(mm['block'][std_off:], 1.0))
            if ents4:
                consts.update(mrl_anim.solid_constants(ents4[0]))
        rs = [s for s in states if s.startswith('RS')]
        rs_gu = [s for s in rs if s in GU_RS]
        mats.append((mname, key, slots, rs_gu[:1], consts, extra))
        notes.append('material %s: template %s, type %d, %s%s%s' % (
            mname, key, extra['mtype'], sorted(p.split('\\')[-1] for p in gp.values()), ', %d 4U animations' % len(ents4) if ents4 else '',
            ', 4U states %s -> %s' % (rs, rs_gu[:1]) if rs != rs_gu[:1] else ''))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(e.P + 'mod\\' + e.c['ours'], T['MRL'], mrl_bytes), (e.P + 'mod\\' + e.c['ours'], T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(e, gu_xfs, groups, notes):
    """GU's parts states (rMonsterPartsManager XFS) for the 4U model's mesh groups; HIDDEN_GROUPS (no GU state names them) hidden in the base states"""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    named = {g for st in states for g, _ in st}
    unnamed = sorted(set(groups) - named - set(HIDDEN_GROUPS))
    assert not unnamed, '%s groups without a GU state: %s' % (e.c['em4u'], unnamed)
    assert not set(HIDDEN_GROUPS) & named, 'GU names a hidden group now'
    assert (0, 1) in kept[e.c['base_states'][0]], 'not a base state'
    for k in e.c['base_states']:
        kept[k] += [(g, 0) for g in HIDDEN_GROUPS if g in groups]
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted(named - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in %s): %s, hidden in base states %s: %s' % (
        len(kept), e.c['em4u'], dropped, list(e.c['base_states']), [g for g in HIDDEN_GROUPS if g in groups]))
    return bytes(head) + data


def skeleton_check(e, gu_mod, our_mod, notes):
    """GU's class and the shared camera / data drive our model: the same bone ids, parents and bind positions (C)"""
    def by_id(m):
        bl = m['bone_list']
        return {b['index']: (bl[b['parent']]['index'] if b['parent'] != 255 else None, b['pos']) for b in bl}
    g, o = by_id(modlib.parse(gu_mod)), by_id(modlib.parse(our_mod))
    assert set(g) == set(o) and all(g[k][0] == o[k][0] for k in g), '%s skeleton differs from GU %s\'s' % (e.c['em4u'], e.c['gu'])
    far = max((max(abs(a - b) for a, b in zip(g[k][1], o[k][1])), k) for k in g)
    notes.append('skeleton: %d bones equal to GU %s\'s; largest bind position difference %.1f (bone %d)' % (len(o), e.c['gu'], *far))


def motion_bank(e, S, gfile, b, notes):
    """the 4U list b, the motions shared with GU's list in GU's form (GU's tracks, the 4U event blocks kept: sound and effect timing, the PSLs come
    from them), with the slots only GU's list has (GU's class may ask for them)"""
    d = S[(e.c['mot4u'] % b, T['LMT'])]
    gu = gfile(4 + b)
    ga, oa = lmt.anims(gu), lmt.anims(d)
    frames = lambda x, o: struct.unpack_from('<I', x, o + 8)[0]
    both = [i for i, o in enumerate(oa) if o and i < len(ga) and ga[i]]
    for i in both:
        assert frames(d, oa[i]) == frames(gu, ga[i]), ('bank slot frames differ', b, i)
    # a slot whose GU animation has other tracks than the 4U one (GU reworked it; Desert Seltas bank 3 slot 32) keeps the 4U tracks
    swap = [(i, i) for i in both if lmt._track_keys(d, oa[i]) == lmt._track_keys(gu, ga[i])]
    size4 = len(d)
    d = lmt.with_tracks(d, gu, swap)
    notes.append('motions bank %d: GU\'s tracks in %d slots, the 4U event blocks kept; GU\'s tracks differ, 4U\'s kept in %s; %d slots only the 4U list has (%s); '
                 'file %d B -> %d B' % (b, len(swap), sorted(set(both) - {i for i, _ in swap}), sum(1 for o in oa if o) - len(both),
                                        [i for i, o in enumerate(oa) if o and not (i < len(ga) and ga[i])], size4, len(d)))
    fill = [(i, i) for i, o in enumerate(ga) if o and i < len(oa) and not oa[i]]
    past = [i for i, o in enumerate(ga) if o and i >= len(oa)]
    if past:
        notes.append('motions bank %d: GU slots %s lie past the 4U table of %d' % (b, past, len(oa)))
    if not fill: return d
    out = lmt.splice(d, gu, fill)
    notes.append('motions bank %d: the 4U list + GU\'s animations in the slots it lacks %s' % (b, [i for i, _ in fill]))
    return out


def emc_tokens(s, lens):
    out, i = [], 0
    while i < len(s):
        op = s[i]
        if op >= len(lens):
            out.append(s[i:]); break
        v = lens[op]
        n = 1 + v if v < 0x80 else 2 + (v & 0xf) if s[i + 1] == 0 else 2 + (v >> 4) - 7 if s[i + 1] == 1 else 2
        out.append(s[i:i + n]); i += n
    assert b''.join(out) == s, 'EMC script does not tokenize'
    return out


def emc_em_only(s, em, lens, op=0x46):
    out, frames = bytearray(), []
    for t in emc_tokens(s, lens):
        if t[0] == op:
            if t[1] == 0x00: frames.append([False, False])
            elif t[1] == 0x01: frames[-1][0] = t[2] == em and not frames[-1][1]; frames[-1][1] |= frames[-1][0]
            elif t[1] == 0x02: frames[-1][0] = not frames[-1][1]; frames[-1][1] = True
            else: frames.pop()
            continue
        if all(f[0] for f in frames): out += t
    assert not frames, 'unbalanced switch block'
    return bytes(out)


def emc_else_only(s, lens, op):
    """a script with its `op` blocks (IF t / ELSE f / END) reduced to the else body: the state op asks for does not exist here"""
    out, frames = bytearray(), []
    for t in emc_tokens(s, lens):
        if t[0] == op:
            if t[1] == 0x00: frames.append(False)
            elif t[1] == 0x02: frames[-1] = True
            elif t[1] == 0xff: frames.pop()
            else: raise AssertionError(('a case in a frenzy block', t.hex()))
            continue
        if all(frames): out += t
    assert not frames, 'unbalanced frenzy block'
    return bytes(out)


def stage_cases(s, lens):
    """4U `2a 01 NN` stage cases of a kept script -> GU's numbers"""
    out = []
    for t in emc_tokens(s, lens):
        if t[0] == 0x2a and t[1] == 1:
            assert t[2] in STAGE_CASE, ('4U stage case without a GU number', t.hex())
            t = bytes([0x2a, 1, STAGE_CASE[t[2]]])
        out.append(t)
    return b''.join(out)


def reduced_4u(d4, em, img):
    """the 4U table's groups with the op-0x46 blocks reduced to em (routes_seltas.routing reads it)"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    return [[emc_em_only(s, em, lens) for s in g] for g in emc.parse(d4)[1]]


def cmdtbl(e, d4, gu, img, notes):
    """the 4U table for em in GU's language (see EMC_4U_ONLY's comment) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[21] and not u4[22], 'EMC group layout changed'
    ops = lambda s: {t[0] for t in emc_tokens(s, lens)}
    out, own, same, gu_taken, frenzy, dropped = [], [], [], [], [], []
    for gi in range(21):
        scripts = []
        for k in range(len(g[gi])):
            gv = emc_em_only(g[gi][k], 1, lens, 0x92)       # GU's variant-1 body
            if (gi, k) in e.c['emc_gu'] or k >= len(u4[gi]):
                scripts.append(gv)
                if k < len(u4[gi]): gu_taken.append((gi, k))
                continue
            mine = emc_em_only(u4[gi][k], e.c['em'], lens)
            if OP_FRENZY in ops(mine):
                frenzy.append((gi, k))
                mine = emc_else_only(mine, lens, OP_FRENZY)
            mine = stage_cases(mine, lens)
            # an op of that list GU's own script holds too is GU's language there (the Queen's g18 s3 keeps 0x8c in both games)
            assert not ops(mine) & EMC_4U_ONLY - ops(gv), ('4U op left', e.name, gi, k, sorted(ops(mine) & EMC_4U_ONLY - ops(gv)))
            if any(t[0] == 0x92 for t in emc_tokens(g[gi][k], lens)):
                (same if mine == gv else own).append((gi, k))
            scripts.append(mine)
        for k in range(len(g[gi]), len(u4[gi])):        # 4U scripts past GU's count (the Queen's g14 s0): appended, 4U's body
            mine = emc_em_only(u4[gi][k], e.c['em'], lens)
            if OP_FRENZY in ops(mine):
                frenzy.append((gi, k))
                mine = emc_else_only(mine, lens, OP_FRENZY)
            mine = stage_cases(mine, lens)
            assert not ops(mine) & EMC_4U_ONLY, ('4U op left', e.name, gi, k, sorted(ops(mine) & EMC_4U_ONLY))
            scripts.append(mine)
            dropped.append((gi, k))
        out.append(scripts)
    assert [len(x) for x in out] == [max(len(x), len(y)) for x, y in zip(g, u4[:21])], 'our table must carry every GU entry number'
    notes.append('AI table: 4U %s for em %d; GU\'s variant-1 body in %s; GU extra entries appended (%s); GU\'s op-0x92 scripts whose variant-1 body equals '
                 'the 4U one %s, differs %s; frenzy branches cut in %s; 4U scripts past GU\'s count appended %s' % (
                     e.c['cmd'].split('\\')[-1], e.c['em'], sorted(gu_taken), ['g%d s%d..s%d' % (gi, len(u4[gi]), len(g[gi]) - 1) for gi in range(21)
                                                                              if len(g[gi]) > len(u4[gi])], same, own, frenzy, dropped))
    return emc.build(out, ver)


def dunes_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Dunes hunting areas' area_color_soil (Tigerstripe's, Monoblos' and Shrouded
    Nerscylla's rule). Most of their quests are on the Dunes (Desert Seltas' m10805 / m10818 on the Ancestral Steppe take the same colour, a DEVIATION:
    GU bakes one colour per file)"""
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
    notes.append('effect area colour: Dunes soil median %s (%d areas)' % (tuple(soil), len(cols)))
    return soil


def psl_entry(psl, i):
    """(frames, slot mask, ids[32], kinds[32], per-frame bits) of PSL entry i, or None (Monoblos' psl_entry)"""
    o = struct.unpack_from('<I', psl, 8 + 4 * i)[0] if i < struct.unpack_from('<H', psl, 6)[0] else 0
    if not o: return None
    frames, _, _, _, da, _ = struct.unpack_from('<IHBBII', psl, o)
    mask = struct.unpack_from('<I', psl, da)[0]
    ids = list(struct.unpack_from('<32H', psl, da + 4))
    kinds = list(struct.unpack_from('<32I', psl, da + 68))
    nr, ra = struct.unpack_from('<II', psl, da + 0x144)
    per = [b for k in range(nr) for b, f in [struct.unpack_from('<II', psl, ra + 8 * k)] for _ in range(f)]
    return frames, mask, ids, kinds, per


def psl_put(out, i, frames, mask, ids, kinds, per):
    """entry i of the PSL bytearray out -> a new data block appended at the end (Monoblos' psl_put)"""
    assert len(per) == frames - 1, ('PSL runs', i)
    o = struct.unpack_from('<I', out, 8 + 4 * i)[0]
    runs = []
    for b in per:
        if runs and runs[-1][0] == b: runs[-1][1] += 1
        else: runs.append([b, 1])
    while len(out) % 16: out.append(0)
    data_at = len(out)
    out += struct.pack('<I32H32I32I', mask, *ids, *kinds, *([0] * 32))
    out += struct.pack('<II', len(runs), data_at + 0x144 + 8)
    out += b''.join(struct.pack('<II', b, f) for b, f in runs)
    if o:
        struct.pack_into('<II', out, o + 8, data_at, 0)
    else:
        while len(out) % 16: out.append(0)
        struct.pack_into('<I', out, 8 + 4 * i, len(out))
        out += struct.pack('<IHBBII', frames, 0, 32, 0, data_at, 0)


def pel_names(pel, li):
    """record id -> EFL file name of a PEL list"""
    n, body = efl4u2gu.pel_lists(pel)[li]
    out, i = {}, 0
    for _ in range(n):
        L = body[i]
        out[struct.unpack_from('<H', body, i + 3 + L + 0x30)[0]] = body[i + 1:i + 1 + L].decode('ascii').split('\\')[-1]
        i += 1 + L + 2 + 160
    return out


def gu_common_effects(e, psl, gu_psl, her_u, gu_c, bank, ground, notes):
    """the user's rule (2026-11-06): where an animation is the same as GU's, GU's effects, as with the roar. Their banks and GU's have equal frames in
    every shared slot (motion_bank), so GU's slots fit. GU's common effects (PEL c, kind 3, its cm* files: air, dust, spray) go into their entry and
    replace their 4U common effects (kind 4, qe*: 4U's dust) there; their own em094_* / em095_* effects stay, but for their sand on the ground (MEF
    ground flag, ids `ground`) where GU's motion has its own dust (cm202_*): the user's rule on environment effects (2026-11-08: sand and dust are GU's
    where GU has a fitting one; 0.1.3 test: the Queen's 4U sand every 15 frames of her walk next to GU's steps). Where GU's motion has no common
    effect, theirs stay as they are. GU's commons of other grounds: none of GU's Seltas' or Seltas Queen's PEL c files is a forest debris (cm200_067,
    Shrouded Nerscylla's lesson; C, their lists: cm202_* dust / air, cm200_* splashes, cm104_000)"""
    out = bytearray(psl)
    done, sand = 0, {}
    for i in range(min(struct.unpack_from('<H', gu_psl, 6)[0], struct.unpack_from('<H', psl, 6)[0])):
        g = psl_entry(gu_psl, i)
        if not g: continue
        gf, gmask, gids, gkinds, gper = g
        add = [k for k in range(32) if gmask >> k & 1 and gkinds[k] == 3 and gu_c.get(gids[k], '').startswith('cm')]
        assert not [k for k in add if gu_c[gids[k]] == 'cm200_067'], 'GU\'s forest debris in a motion'
        if not add: continue
        gu_dust = any(gu_c[gids[k]].startswith('cm202_') for k in add)
        en = psl_entry(out, i)
        f, mask, ids, kinds, per = en if en else (gf, 0, [0] * 32, [0] * 32, [0] * (gf - 1))
        assert f == gf, ('the 4U motion and GU\'s differ in frames', bank, i, f, gf)
        own = e.c['em4u']
        for k in range(32):
            if not (mask >> k & 1 and kinds[k] == 4): continue
            if her_u.get(ids[k], own).startswith(own) and not (gu_dust and ids[k] in ground): continue
            if her_u.get(ids[k], own).startswith(own): sand.setdefault(i, []).append(ids[k])
            mask &= ~(1 << k)
            ids[k], kinds[k] = 0, 0
            per = [b & ~(1 << k) for b in per]
        for a in add:
            k = next(k for k in range(32) if not mask >> k & 1)
            ids[k], kinds[k] = gids[a], gkinds[a]
            mask |= 1 << k
            per = [b | ((gper[x] >> a & 1) << k) for x, b in enumerate(per)]
        psl_put(out, i, f, mask, ids, kinds, per)
        done += 1
    notes.append('effects bank %d: GU\'s common effects in %d motions; their own 4U sand left out for GU\'s dust in %s' % (
        bank, done, {'%x' % ((bank << 8) | i): v for i, v in sorted(sand.items())}))
    return bytes(out)


def psl_ids(psl):
    """{(kind, id): [slots]} of a PSL"""
    out = {}
    for i in range(struct.unpack_from('<H', psl, 6)[0]):
        en = psl_entry(psl, i)
        if not en: continue
        for k in range(32):
            if en[1] >> k & 1: out.setdefault((en[3][k], en[2][k]), []).append(i)
    return out


def ground_rows(e):
    """the k_ground table of module/seltas_fx.c for this entry: (id, joint, offset x, offset z)"""
    src = open(os.path.join(MON, 'module', 'seltas_fx.c'), encoding='utf-8').read()
    tag = 'k_ground_%s[] = {' % e.c['ours']
    body = src[src.index(tag):]
    return [tuple(int(x) for x in m) for m in re.findall(r'\{\s*(\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\}', body[:body.index('};')])]


def pel_ground_records(e, pel, S, notes):
    """their 4U effects on the ground (Tidal Najarala's way: 4U 0x391b50 copies the MEF flags into the effect; ground flag bit 1: x, z = the joint + the
    record offset, y = the ground): GU's records have no such tail, so these become world records and module/seltas_fx.c (hook on the PSL post) names
    the point and the ground set. Slot mode 1: 4U ends the effect when the event range ends; in GU that is end mode 1 (+0x3a)"""
    mef = efl4u2gu.mef_records(S[(e.c['mef'], efl4u2gu.T['MEF'])])
    ground = [r for r in mef if r['flags'] & efl4u2gu.MEF_GROUND]
    assert all(r['pos'][1] == 0.0 and r['pos'][0] == round(r['pos'][0]) and r['pos'][2] == round(r['pos'][2]) for r in ground), 'a ground record the table cannot hold'
    want = [(r['id'], r['joint'], round(r['pos'][0]), round(r['pos'][2])) for r in ground]
    assert ground_rows(e) == want, ('k_ground_%s (module/seltas_fx.c) differs from the MEF records' % e.c['ours'], want)
    by = {r['id']: r for r in mef}
    lists = efl4u2gu.pel_lists(pel)
    n, body = lists[1]
    out, i, placed, ends = bytearray(), 0, set(), 0
    for _ in range(n):
        L = body[i]
        path, two, st = body[i + 1:i + 1 + L], body[i + 1 + L:i + 3 + L], bytearray(body[i + 3 + L:i + 3 + L + 160])
        i += 3 + L + 160
        r = by.get(struct.unpack_from('<H', st, 0x30)[0])
        if r and r in ground:
            msk = bytes(st[0x48:0x4c])
            st[0x34:160] = efl4u2gu.PEL_TAIL_WORLD
            st[0x48:0x4c] = msk
            for o, v in efl4u2gu.PEL_COLOUR_OFF: st[o] = v
            placed.add(r['id'])
        if r and r['slot'] == 1:
            st[0x3a] = 1
            ends += 1
        out += bytes([len(path)]) + path + two + bytes(st)
    assert i == len(body), 'PEL list 1'
    assert placed == {r['id'] for r in ground}, 'a ground record has no PEL record'
    notes.append('effects: %d records on the ground %s (world posts, module/seltas_fx.c), %d records end with their event range' % (len(placed), sorted(placed), ends))
    res = pel[:8]
    for k, (cnt, b) in enumerate(lists):
        res += struct.pack('<I', cnt) + (bytes(out) if k == 1 else b)
    return res


def soil_units(d):
    """(units 4U multiplies by the area (soil) colour, other units with an Intensity level) of a 4U EFL: an area colour block (header +0x2c
    word 0 bit 4, +0xc byte 2 = 0) multiplies its mode-0 / mode-5 units, else only mode-5 units take it (tools/efl4u2gu.py convert_efl)"""
    b = efl4u2gu.efl_colour_block(d)
    block = bool(b and b[0] & 0x10 and not (b[3] >> 16) & 0xFF)
    soil, other = 0, 0
    for o, _, k in efl4u2gu.efl_parse(d)['blocks']:
        if not (k and k[0] == 1) or k[1] not in (0, 1, 2):
            continue
        w = struct.unpack_from('<I', d, o + 0x18)[0]
        mode = w & efl4u2gu.UNIT_COLOUR_MODE
        if mode == efl4u2gu.UNIT_AREA_MODE or (block and mode == 0):
            soil += 1
        elif w & efl4u2gu.UNIT_INTENSITY:
            other += 1
    return soil, other


def own_sand(e, S, groups):
    """their own 4U sand and dust: every own EFL whose units 4U multiplies by the area (soil) colour (soil_units), the ones their MEF ground-flag
    records name and the others. Drawn at 1x like 4U's common dust (DUST_1X): 4U's Intensity 1 baked x2 into the soil-multiplied grey made them
    bright yellow-white in GU (the user on 0.1.3, 2026-11-09: "grell gelb schon fast weiß"), e.g. the Queen's em095_000 unit 11: (178, 178, 178) x
    the Dunes soil x 2 = (255, 230, 162), at 1x (147, 115, 81), the brown of GU's own Dunes dust (cm202_002's sand (159, 127, 95), Shrouded
    Nerscylla's lesson). Up to 0.1.7 only the ground-flag ones: the user on 0.1.4 (2026-11-10, "grell gelb" when the Queen pulls him out of the
    ground) saw her em095_028 / 029 (her call 7/72, motion 0x465) at (255, 231, 163); his em094_006 / 007 and her em095_023 were x2 as well.
    Each such file holds soil units only (asserted), so no other unit loses its Intensity."""
    mef = efl4u2gu.mef_records(S[(e.c['mef'], efl4u2gu.T['MEF'])])
    ground = {(groups[r['grp']] % r['file']).split(BS)[-1] for r in mef if r['flags'] & efl4u2gu.MEF_GROUND and r['grp'] == e.c['em']}
    out = set()
    for (p, t), d in S.items():
        if t != efl4u2gu.T['EFL'] or not p.startswith(e.c['efl_dir']):
            continue
        soil, other = soil_units(d)
        if soil:
            assert not other, ('an own EFL with soil units and other units at an Intensity: 1x would dim the others', p)
            out.add(p.split(BS)[-1])
    assert ground <= out, ('a ground-flag file without soil units', ground - out)
    return tuple(sorted(out))


def effects(e, S, gu_pel_u, gu_pel_c, gu_psls, soil, notes):
    """their effects (tools/efl4u2gu.py effect_set) -> [(path, type, data)]"""
    groups = {e.c['em']: e.c['efl']}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 3, 6, 8, 13)})
    sand = own_sand(e, S, groups)
    notes.append('effects: their own sand at 1x %s' % (sand,))
    spec = dict(arc=e.src4u, stage_unpacked=[], mef=e.c['mef'], em_efl=e.c['efl_dir'], groups=groups, extra=[],
                lmts=[(e.c['mot4u'] % b, e.psl % b) for b in e.c['banks']], pel=e.pel_u, soil=soil,
                list2=efl4u2gu.pel_lists(gu_pel_u)[2], solid_fill=SOLID_FILL, intensity=True, intensity_skip=DUST_1X + sand + SHOT_1X,
                hide_grey_models='chunks')
    log = []
    out = efl4u2gu.effect_set(spec, log)
    # Their own rock model (0.1.16; the user on 0.1.15: at one of her moves "Steine am Boden, komplett schwarz"): their
    # ground EFLs (the soil-coloured ones, own_sand) also draw grey rock units with their own effect model ef_em09N,
    # which the shared rule (hide_grey_models 'chunks': CHUNK_MODELS only) does not name; GU draws them black. The same
    # rule as the project's (issue #6: grey 4U rock-chunk model units dropped, "gone entirely") on those files with
    # their model: C, the units of em095_000 / 011 / 012 / 013 / 014 (her steps and slides, 7/61 7/63's 0x493 0x448
    # 0x494); his files hold none. A DEVIATION from 4U as issue #6's.
    model = 'ef_' + e.c['efl_dir'].rstrip(BS).split(BS)[-1]
    for name in sand:
        k = (e.c['efl_dir'] + name, efl4u2gu.T['EFL'])
        if k in out and k in S:
            hid = []
            out[k] = efl4u2gu.hide_grey_models(out[k], S[k], hid, {model})
            notes += ['  own rock model %s in %s: %s' % (model, name, h) for h in hid]
    out[(e.pel_u, efl4u2gu.T['PEL'])] = pel_ground_records(e, out[(e.pel_u, efl4u2gu.T['PEL'])], S, notes)
    her_u, gu_c = pel_names(out[(e.pel_u, efl4u2gu.T['PEL'])], 1), {}
    for li in (1, 2):
        gu_c.update(pel_names(gu_pel_c, li))
    mef = efl4u2gu.mef_records(S[(e.c['mef'], efl4u2gu.T['MEF'])])
    ground = {r['id'] for r in mef if r['flags'] & efl4u2gu.MEF_GROUND}
    for b, gu_psl in gu_psls.items():
        k = (e.psl % b, efl4u2gu.T['PSL'])
        out[k] = gu_common_effects(e, out[k], gu_psl, her_u, gu_c, b, ground, notes)
    for b in e.c['banks']:
        left = {i: v for (kind, i), v in psl_ids(out[(e.psl % b, efl4u2gu.T['PSL'])]).items() if kind == 4 and i in ground}
        notes.append('effects bank %d: 4U ground-flag records left in its motions: %s' % (b, left))
    notes.append('effects: %d entries (tools/efl4u2gu.py effect_set)' % len(out))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return [(p, t, d) for (p, t), d in out.items()]


def sound(e, rom, notes):
    """the sound call, waves, bank and request (tools/snd4u2gu.py monster_entries) -> ([(path, type, data)], {field: (path, type)}). Common-bank requests
    from GU's species, plus the ones GU's species adds (its class may post them)."""
    o = e.c['ours']
    spec = dict(e.c['sound'], src=e.src4u, pg_wave='sound\\se\\em\\%s\\wav\\' % o, pg_bank='sound\\se\\em\\%s\\snd_%s' % (o, o),
                pg_call='sound\\call\\em\\%s' % o, donor_arc=e.gu_arc, donor_name='GU ' + e.c['gu'], donor_extra=True)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    notes += log
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def retuned_on(gu, par, sub):
    """sub (the subspecies' 4U values on GU's layout) + GU's retunes of the species (gu vs par, the species' 4U values on the same layout) at the bytes
    where sub equals par (aligned: the layouts can differ in length); -> (bytes, retunes taken, retunes left out because sub has its own bytes there)"""
    assert len(gu) == len(par), 'GU\'s file and the species\' conversion differ in length'
    ret = {i for i in range(len(gu)) if gu[i] != par[i]}
    out = bytearray(sub)
    taken, left = 0, 0
    sm = difflib.SequenceMatcher(None, par, sub, autojunk=False)
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag != 'equal': continue
        for i in range(a0, a1):
            if i in ret:
                out[b0 + i - a0] = gu[i]
                taken += 1
    left = len(ret) - taken
    return bytes(out), taken, left


def dttune(e, gu, notes):
    """their 4U values (tools/dt_convert.py on GU's file) + GU's retunes of the species where theirs equal the species' (retuned_on): their hitzones, HP
    and parts are 4U's, GU's balance of the rest stays"""
    par = open(os.path.join(e.dt_dir, 'dt_%s' % e.c['parent'], 'dttune.bin'), 'rb').read()
    sub = open(os.path.join(e.dt_dir, 'dt_%s' % e.c['em4u'], 'dttune.bin'), 'rb').read()
    out, taken, left = retuned_on(gu, par, sub)
    notes.append('dttune: %s on GU %s\'s layout (%d B, GU %d B) + %d of GU\'s %d retuned bytes (%d left out: its own bytes there); base HP %d (GU\'s species %d)' % (
        e.c['em4u'], e.c['gu'], len(out), len(gu), taken, taken + left, left, struct.unpack_from('<H', out, 0x38)[0], struct.unpack_from('<H', gu, 0x38)[0]))
    return out


def dtbase(e, gu, notes):
    par = open(os.path.join(e.dt_dir, 'dt_%s' % e.c['parent'], 'dtbase.bin'), 'rb').read()
    sub = open(os.path.join(e.dt_dir, 'dt_%s' % e.c['em4u'], 'dtbase.bin'), 'rb').read()
    out, taken, left = retuned_on(gu, par, sub)
    notes.append('dtbase: %s on GU\'s layout, %d bytes its own, %d of GU\'s retunes kept, %d left out' % (
        e.c['em4u'], sum(1 for i in range(len(out)) if out[i] != gu[i]), taken, left))
    return out


def records(d, size, first=16):
    n = struct.unpack_from('<I', d, 8)[0]
    return [d[first + size * i:first + size * (i + 1)] for i in range(n)]


def bodydata(e, gu, notes):
    """the hurt / push volumes: their 4U records (tools/emdata4u.py) with GU's retunes of the species' records that theirs equal byte for byte"""
    a, b = emdata4u.load_4u(e.c['parent']), emdata4u.load_4u(e.c['em4u'])
    pa, su = emdata4u.bodydata(a['emd'], 8), emdata4u.bodydata(b['emd'], 8)
    rp, rs, rg = records(pa, 44), records(su, 44), records(gu, 44)
    assert len(rp) == len(rg), 'GU\'s bodydata and the species\' 4U one differ in count'
    out, taken, mine = list(rs), [], []
    for i, (p, g) in enumerate(zip(rp, rg)):
        if p == g: continue
        hits = [j for j, s in enumerate(rs) if s == p]
        if len(hits) == 1:
            out[hits[0]] = g; taken.append((i, hits[0]))
        else:
            mine.append(i)
    data = su[:16] + b''.join(out) + su[16 + 44 * len(rs):]
    notes.append('bodydata: %s\'s %d records (the species %d); GU\'s retunes of the species\' records %s taken (species -> ours), left out (its own '
                 'record there) %s' % (e.c['em4u'], len(rs), len(rp), taken, mine))
    return data


ATK_MOVED = {69: 47, 70: 51}            # her 4U attack index -> GU's record holding it (docstring: data files; GU's own posts for her)


def attackdata(e, gu, notes):
    """GU's records (its retunes of the species, with her 4U attacks moved: ATK_MOVED), checked against 4U up to GU's retune bytes"""
    a, b = emdata4u.load_4u(e.c['parent']), emdata4u.load_4u(e.c['em4u'])
    pa, su = emdata4u.attackdata(a['etd']), emdata4u.attackdata(b['etd'])
    assert pa == su, 'its 4U attack records differ from the species\': own them'
    rg, rs = records(gu, 32), records(su, 32)
    assert len(rs) >= len(rg), 'GU has more attack records than 4U'
    for i4, ig in ATK_MOVED.items():                    # GU's record = 4U's but for GU's retune bytes 28 / 31
        assert all(rg[ig][k] == rs[i4][k] for k in range(32) if k not in (28, 31)), ('GU record %d is not 4U %d' % (ig, i4))
    data = struct.pack('<4sIII', b'HDE\0', struct.unpack_from('<I', gu, 4)[0], len(rg), 0) + b''.join(rg)
    notes.append('attackdata: GU %s\'s %d records (her 4U %s in GU\'s %s; 4U\'s %s unused)' % (
        e.c['gu'], len(rg), sorted(ATK_MOVED), [ATK_MOVED[k] for k in sorted(ATK_MOVED)], list(range(len(rg), len(rs)))))
    return data


def hts_groups(h):
    n = struct.unpack_from('<I', h, 8)[0]
    out = []
    for k in range(n):
        c, o = struct.unpack_from('<II', h, 16 + 8 * k)
        out.append([h[o + 48 * i:o + 48 * (i + 1)] for i in range(c)])
    return out


def hitsize(e, gu, notes):
    """the attack volumes: its 4U groups (far end at GU's place, off2_gu, as every new port), GU's group where hers equals the species' 4U group"""
    a, b = emdata4u.load_4u(e.c['parent']), emdata4u.load_4u(e.c['em4u'])
    gp, gs, gg = hts_groups(emdata4u.hitsize(a['etd'], True)), hts_groups(emdata4u.hitsize(b['etd'], True)), hts_groups(gu)
    assert len(gp) == len(gg), 'GU\'s hitsize and the species\' 4U one differ in groups'
    out, gu_taken, mine = [], [], []
    for k, recs in enumerate(gs):
        if k < len(gp) and recs == gp[k]:
            out.append(gg[k]); gu_taken.append(k) if gg[k] != gp[k] else None
        else:
            out.append(recs); mine.append(k)
    n = len(out)
    off = 16 + 8 * n
    table, data = b'', b''
    for recs in out:
        table += struct.pack('<II', len(recs), off + len(data))
        data += b''.join(recs)
    notes.append('hitsize: %d groups (the species %d); GU\'s retuned groups taken %s, its own 4U groups %s' % (n, len(gp), gu_taken, mine))
    return struct.pack('<4sIII', b'HTS\0', struct.unpack_from('<I', gu, 4)[0], n, 0) + table + data


def build(name):
    e = E(name)
    c = e.c
    img = open(paths.GU_MAIN, 'rb').read()
    rom = RomFS(paths.GU_ROMFS)
    _, src = arcpack.read(open(e.src4u, 'rb').read())
    S = {(p, t): d for p, t, d in src}
    _, gents = arcpack.read(rom.read(e.gu_arc))
    notes = []
    ghash = {(phash(p), t): (p, t) for p, t, _ in gents}
    gman = manifest_of(img, e.alloc['donor_index'])
    G = {(p, t): d for p, t, d in gents}
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU's file of manifest field k
    gtype = lambda k: ghash[fileid_entry(img, gman[k])][1]

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    files, m4 = model(e, S, rom, gu_tex, notes)
    ents += files
    own[0] = (e.P + 'mod\\' + c['ours'], T['MOD'])
    skeleton_check(e, gfile(0), [d for p, t, d in files if t == T['MOD']][0], notes)
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((e.P + 'mod\\' + c['ours'], T['XFS'], parts_xfs(e, gfile(3), groups, notes)))
    own[3] = (e.P + 'mod\\' + c['ours'], T['XFS'])
    for b in c['banks']:
        ents.append((e.P + 'mot\\%s_%d' % (c['ours'], b), T['LMT'], motion_bank(e, S, gfile, b, notes)))
        own[4 + b] = (e.P + 'mot\\%s_%d' % (c['ours'], b), T['LMT'])
    gu_cmd = gfile(37)
    d4cmd = S[(c['cmd'], T['EMC'])]
    ents.append(('enemy\\cmd_tbl\\%s_cmdtbl' % c['ours'], T['EMC'], cmdtbl(e, d4cmd, gu_cmd, img, notes)))
    own[37] = ('enemy\\cmd_tbl\\%s_cmdtbl' % c['ours'], T['EMC'])
    ents += effects(e, S, gfile(17), gfile(16), {b: gfile(18 + b) for b in c['banks']}, dunes_soil(notes), notes)
    own[17] = (e.pel_u, efl4u2gu.T['PEL'])
    for b in c['banks']:
        own[18 + b] = (e.psl % b, efl4u2gu.T['PSL'])
    files, fields = sound(e, rom, notes)
    ents += files
    own.update(fields)
    ents.append(('enemy\\dt_tune\\%s_dttune' % c['ours'], gtype(33), dttune(e, gfile(33), notes)))
    own[33] = ('enemy\\dt_tune\\%s_dttune' % c['ours'], gtype(33))
    if 32 in c['own_order']:
        ents.append(('enemy\\dt_base\\%s_dtbase' % c['ours'], gtype(32), dtbase(e, gfile(32), notes)))
        own[32] = ('enemy\\dt_base\\%s_dtbase' % c['ours'], gtype(32))
    else:
        par = open(os.path.join(e.dt_dir, 'dt_%s' % c['parent'], 'dtbase.bin'), 'rb').read()
        assert open(os.path.join(e.dt_dir, 'dt_%s' % c['em4u'], 'dtbase.bin'), 'rb').read() == par, 'its dtbase differs from the species\': own it'
    a, b4 = emdata4u.load_4u(c['parent']), emdata4u.load_4u(c['em4u'])
    if 30 in c['own_order']:
        ents.append(('enemy\\body_data\\%s_bodydata' % c['ours'], gtype(30), bodydata(e, gfile(30), notes)))
        own[30] = ('enemy\\body_data\\%s_bodydata' % c['ours'], gtype(30))
    if 26 in c['own_order']:
        ents.append(('enemy\\hit_data\\%s_attackdata' % c['ours'], gtype(26), attackdata(e, gfile(26), notes)))
        own[26] = ('enemy\\hit_data\\%s_attackdata' % c['ours'], gtype(26))
    else:
        assert emdata4u.attackdata(a['etd']) == emdata4u.attackdata(b4['etd']), 'its attack data differs from the species\': own it'
    if 28 in c['own_order']:
        ents.append(('enemy\\hit_data\\%s_hitsize' % c['ours'], gtype(28), hitsize(e, gfile(28), notes)))
        own[28] = ('enemy\\hit_data\\%s_hitsize' % c['ours'], gtype(28))
    else:
        assert emdata4u.hitsize(a['etd'], True) == emdata4u.hitsize(b4['etd'], True), 'its hit sizes differ from the species\': own them'
    assert emdata4u.bodydata(a['emd'], 9) == emdata4u.bodydata(b4['emd'], 9), 'its camera body data differs from the species\': own it'
    sys.path.insert(0, HERE)
    import hagi_seltas                   # carves: 4U G body / shiny tables in s4, GU's filler in s0..s3
    for k, data in hagi_seltas.files(name).items():
        path = 'enemy\\hagi\\hagi_s%d_%s' % (k - 46, c['ours'])
        ents.append((path, gtype(k), data))
        own[k] = (path, gtype(k))
    import routes_seltas as routes       # their 4U area behaviour on GU's maps
    P = routes.plans(name, reduced_4u(d4cmd, c['em'], img), rom, notes)
    for k, kind in {40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select'}.items():
        build_file = {'area_link': routes.area_link_file, 'area_eat': routes.area_eat_file, 'map_info': routes.map_info_file,
                      'area_select': routes.area_select_file}[kind]
        ents.append(('enemy\\%s\\%s' % (kind, c['ours']), gtype(k), build_file(gfile(k), rom, P, notes)))
        own[k] = ('enemy\\%s\\%s' % (kind, c['ours']), gtype(k))

    # ---- the shared GU files: everything but what ours replace and GU's model (MOD, MRL, textures)
    replaced = {ghash[fileid_entry(img, gman[k])] for k in own if gman[k] != -1}
    drop = replaced | {(p, t) for p, t, _ in gents if p.startswith(e.P0 + 'mod\\')}
    while True:                                  # a file a kept one names by path stays
        kept = [(p, t, d) for p, t, d in gents if (p, t) not in drop]
        named = {(p, t) for p, t in drop if any(p.encode('ascii') in kd for _, _, kd in kept)}
        if not named: break
        for p, t in sorted(named):
            notes.append('kept %s although replaced: named by %s' % (p, [kp for kp, _, kd in kept if p.encode('ascii') in kd][:4]))
        drop -= named
    ents += kept
    notes.append('shared from %s: %d files kept, %d dropped (replaced or its model)' % (c['gu'], len(kept), len(drop)))
    # a record finds what the arc has loaded: our PEL u names the shared GU files of its list 2, and GU's arc has them before its PEL u
    at = next(i for i, x in enumerate(ents) if x[0] == e.pel_u and x[1] == efl4u2gu.T['PEL'])
    want, todo, by = set(), [p.decode('ascii') for p in re.findall(rb'effect\\[A-Za-z0-9_\\]+', dict(((x[0], x[1]), x[2]) for x in ents)[(e.pel_u, efl4u2gu.T['PEL'])])], {}
    for x in ents: by.setdefault(x[0], []).append(x)
    while todo:
        p = todo.pop()
        if p in want or p not in by: continue
        want.add(p)
        for _, _, d in by[p]:
            todo += [m.decode('ascii') for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', d)]
    moved = [x for x in ents[at + 1:] if x[0] in want]
    ents = ents[:at] + moved + ents[at:at + 1] + [x for x in ents[at + 1:] if x[0] not in want]
    notes.append('effects: %d files moved before its PEL u' % len(moved))
    # their own 4U shots: copies of GU's shell families under our paths, at the end (after every file they name);
    # module/seltas_shots.c finds the defs by the file IDs after the manifest's (tools/shots_seltas.py)
    import shots_seltas
    n_own = len([k for k in c['own_order'] if k in own])
    shot_ents, shot_extra = shots_seltas.files(name, G, e.fid_base + n_own, notes)
    ents += shot_ents
    # no file under a GU path may differ from GU's (Desert Seltas meets a normal Seltas in 4U m10818; the Queen's arc likewise)
    for p, t, d in ents:
        if (p, t) in G:
            assert G[(p, t)] == d, ('a file under GU\'s path differs from GU\'s', p)

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = GU's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(c['own_order']), 'add new own fields at the end of own_order: %s' % (set(own) - set(c['own_order']))
    for k in [k for k in c['own_order'] if k in own]:
        fid = e.fid_base + len(new_files)
        assert fid <= e.fid_last, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U %s)' % c['em4u']
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU %s, its file ID)' % c['gu']
    for p, t in shot_extra:                      # files outside the manifest (their shot families' defs): IDs after it
        fid = e.fid_base + len(new_files)
        assert fid <= e.fid_last, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid, p, t))

    # ---- verify before writing anything
    arc = arcpack.build(ents)
    ver, back = arcpack.read(arc)
    assert ver == 0x11 and len(back) == len(ents)
    assert len({(p, t) for p, t, _ in back}) == len(back), 'duplicate entries'
    present = {(phash(p), t) for p, t, _ in back}
    for fid, p, t in new_files:
        assert (phash(p), t) in present, p
    for k in range(51):
        if manifest[k] != -1 and manifest[k] < e.fid_base:
            assert fileid_entry(img, manifest[k]) in present, (k, hex(manifest[k]))
    for p, t, d in back:
        if p.startswith(e.P) and t == T['MOD']: modlib.parse(d)
        if p.startswith(e.P) and t == T['TEX']: tex.decode(d)
        if p.startswith(e.P) and t == T['LMT']:
            for o in lmt.anims(d):
                if o: lmt.blocks(d, o)
    # every file before the effect that names it (Shrouded Nerscylla 0.1.7's lesson), but where GU's own arc has the same order (its resident files)
    pos = {(x[0], x[1]): i for i, x in enumerate(back)}
    gpos = {(p, t): i for i, (p, t, _) in enumerate(gents)}
    for x in back:
        if not x[0].startswith('effect'): continue
        for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', x[2]):
            for k in [k for k in pos if k[0] == m.decode('ascii') and k[0] != x[0]]:
                if k in gpos and (x[0], x[1]) in gpos and gpos[k] > gpos[(x[0], x[1])]: continue
                assert pos[k] < pos[(x[0], x[1])], ('a file after the effect that names it', x[0], k[0])

    # ---- write
    os.makedirs(os.path.dirname(e.out_arc), exist_ok=True)
    open(e.out_arc, 'wb').write(arc)
    fields = []
    for k in range(51):
        fid = manifest[k]
        if fid == -1:
            fields.append(dict(field=k, file_id=-1)); continue
        p, t = new_files[fid - e.fid_base][1:] if fid >= e.fid_base else ghash[fileid_entry(img, fid)]
        fields.append(dict(field=k, file_id='0x%x' % fid, path=p, type='0x%08x' % t, source=src_of[k]))
    json.dump(dict(monster='%s (%s)' % (c['ours'], c['title']), id='0x%x' % e.alloc['em_id'], registry_index=e.alloc['registry_index'],
                   file_id_base='0x%x' % e.fid_base, file_count=len(new_files), manifest=fields,
                   files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p)) for f, p, t in new_files], notes=notes),
              open(e.out_json, 'w', encoding='utf-8', newline='\n'), indent=1)    # LF on every OS (.gitattributes)
    # FILE section: the registry manifest of its index and the (path hash, type) of each of our file IDs
    sec = portdata.Section('FILE')
    sec.u32(e.fid_base, len(new_files), *[x & 0xFFFFFFFF for x in manifest])
    for fid, p, t in new_files:
        sec.u32(phash(p), t)
    print('wrote', portdata.write_section(name, sec))
    print('%s arc: %d entries, %.1f MB -> %s' % (name, len(ents), len(arc) / 1e6, e.out_arc))
    print('own file IDs 0x%x..0x%x (%d)' % (e.fid_base, e.fid_base + len(new_files) - 1, len(new_files)))
    for n in notes: print(' ', n)


def main():
    for name in (sys.argv[1:] or list(ENTRIES)):
        build(name)


if __name__ == '__main__':
    main()
