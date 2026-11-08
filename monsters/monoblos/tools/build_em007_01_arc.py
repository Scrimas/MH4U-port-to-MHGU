"""build_em007_01_arc.py : build nativeNX/arc/enemy/em007_01.arc (Monoblos = GU Diablos variant 1, ID 0x107) + its data
file section FILE.

  build_em007_01_arc.py      build, verify, then write (paths in monsters/monoblos/):
      romfs/nativeNX/arc/enemy/em007_01.arc
      tools/em007_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em007_04, Bloodbath Diablos): the variant's own files under enemy\\em007\\em007_01\\...,
the files it shares with variant 0 under em007_00's paths and file IDs. GU's class uEm007_00 runs it (variant byte 1,
notes/plan.md), with his 4U AI table and his handlers ported in C (module/em007_01_*.c, notes/actions.md).
  own, converted from MH4U em101.arc:
      mod\\em007_01 (+ _tail) MOD + MRL    tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py), 4U material
                                           animations converted (tools/mrl_anim.py), as stygian_zinogre's
      mod\\em007_01_NN_BM (+A), _NN_NM_*   albedo (BC3) + GU specular map; normal maps (BC5)
      mod\\em007_01 XFS                    his parts states from his 4U visibility rows, GU em007_00's layout (PART_STATES)
      mot\\em007_01_0                      GU em007_00_0 with slots 4 / 14 = 4U em101_4's 4 / 14: his roar and idle
                                           (C: Monoblos' bank 0 has no 4 / 14, his code asks for 0x404 / 0x40e, the
                                           same frame counts as Diablos' 0x004 / 0x00e; GU's code asks for 0x004 / 0x00e)
      mot\\em007_01_4                      4U em101_4 (LMT 67, unchanged) in manifest field 8, which GU's Diablos leaves
                                           empty although its class asks for 0x418 0x419 0x41a 0x425 (C)
      cmd_tbl\\em007_01_cmdtbl             his 4U em101_cmd in GU's language (cmdtbl())
      hit_data\\em007_01_attackdata / _hitsize   his 4U records in GU's second attack table (fields 27 / 29: his index i
                                           -> 1000 + i), with GU's retunes of the equal Diablos records (gu_retunes)
      body_data\\ / cam_body_data\\em007_01_*   his 4U hurt and camera volumes (fields 30 / 31)
      effect\\pel\\em\\em007_01u + effect\\psl\\...\\em007_01_4   GU's PEL u + his 4U records, a bank-4 PSL, his converted EFLs
      dt_tune\\em007_01_dttune             tools/dt_convert.py of 4U em101 on GU em007_00: his 4U values and distance rows
                                           (400, 1000, 2500, 5000) on GU's balance (dttune_gu, dttune_ai)
      hagi\\hagi_s0..s4_em007_01           carves (tools/hagi_em007_01.py)
      area_link / map_info / area_select   his 4U routes on the Dunes (tools/routes_em007_01.py)
  shared, GU em007_00 (original paths + file IDs): motion banks 1..3, camera, sounds, PEL c, PSL banks 0..3, shells, GU's
      attack table for GU's handlers (fields 26 / 28), dtbase (4U em099 and em101 convert to GU's bytes, C), dtbparts, dou
      mou ka, area_eat, area_patrol.
Inputs besides the arcs: dump/converted/em101/dt_*/ (build.py step dt).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/monoblos
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, emc, emdata4u, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, tex

NAME = 'monoblos'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em101.arc')
GU_ARC = '/nativeNX/arc/enemy/em007_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em007_01.arc')
OUT_JSON = os.path.join(HERE, 'em007_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E)
P4 = 'enemy\\em101\\'            # 4U Monoblos' own paths
P0 = 'enemy\\em007\\em007_00\\'  # GU variant 0
P = 'enemy\\em007\\em007_01\\'   # ours
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 1, 3, 4, 8, 33, 40, 42, 43, 46, 47, 48, 49, 50, 37, 27, 29, 17, 22, 30, 31]
AREA_FIELDS = {40: 'area_link', 42: 'map_info', 43: 'area_select'}     # his 4U routes (routes_em007_01.py)
DT_DIR = os.path.join(ROOT, 'dump/converted/em101')            # build.py step dt
MODELS = (('em101', 'em007_01', 0), ('em101_tail', 'em007_01_tail', 1))    # 4U name, ours, manifest field
MTYPE = {}                       # material type = the 'mNN' of the 4U name (checked against GU em007_00's in the notes)
# His mesh groups by his 4U visibility rows (emd +0x88, C: tools/emdata4u.py part_rows; 4U evaluator 0x948378, conditions in
# monsters/dalamadur/notes/class-study.md). They are NOT GU Diablos' numbers: his eye is 2 (Diablos' 5), his horn 102 -> 3 at
# rank 2 (Diablos has two steps, 102 -> 2 and 103 -> 3), 103 is his back with no broken piece (5 has no mesh).
PART_ROWS = [(102, 6, 0, 6, 2), (3, 6, 1, 6, 2),            # horn, broken at part 6 rank 2 -> its stump
             (1, 0, 1, 0, 0),                               # eyelid: shown only while the eyes are closed (cond 0)
             (101, 1, 0, 1, 0), (4, 1, 1, 1, 0),            # tail, severed -> its stump
             (103, 6, 0, 0, 1), (5, 6, 1, 0, 1),            # back, gone at part 0 rank 1 (no mesh 5 in his model)
             (2, 10, 0, 0, 0), (2, 11, 0, 0, 0),            # amber eye: hidden under cond 10 and when dead (cond 11)
             (50, 10, 1, 0, 0), (50, 11, 0, 0, 0),          # red eye: ONLY under cond 10 (4U W+0x53a, the frenzy look; S)
             (51, 10, 1, 0, 0), (51, 11, 0, 0, 0)]          # pink veins around the eye: the same rows as the red eye
# GU's own Diablos model has no 50 / 51 (4U em099 has the same rows on them): GU dropped the frenzy look. Who reads the
# states (11, GU's count), C: 0 / 1 / 2 = GU's 0x6f5a4 every frame through the numbers GU's class gives variants other than
# 4 at slot 118 (0xd35130: closed 1, open 2, other -1; slot 114 returns 0, so state 0 is never read for him); his closed eye hides
# group 2 as GU's closed eye hides Diablos' 5. 1 / 2 and 5..10 = module em007_01_mat.c every frame, because GU's slot 132 0xd39fc8
# only runs for variants 0 and 4 and 0x6f5a4 sits behind a flag of the enemy manager: until 0.4.6 the breaks never switched and
# no state named his eye, so all were drawn at once.
PART_STATES = [[(0, 1), (100, 1), (6, 1), (50, 0), (51, 0)],
               [(1, 1), (2, 0), (50, 0), (51, 0)],          # 1 eyes closed
               [(1, 0), (2, 1), (50, 0), (51, 0)],          # 2 eyes open
               [], [],                                      # 3 / 4: Diablos' first horn step, he has none
               [(3, 0), (102, 1)], [(3, 1), (102, 0)],      # 5 / 6 horn intact / broken
               [(103, 1)], [(103, 0)],                      # 7 / 8 back intact / broken
               [(4, 0), (101, 1)], [(4, 1), (101, 0)]]      # 9 / 10 tail intact / severed
OWN_BANK0 = (4, 14)              # GU bank-0 slots that take 4U em101_4's animation of the same index (his versions)
BANK4_FIELD = 8                  # manifest field of motion list 4 (fields 4..8 = lists 0..4: GU em005_00 fills 8)
GU_RS = {a for _, (a, _) in mrl.records(0x22).items() if a and a.startswith('RS')}     # GU's rasterizer states


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def textures(S, r4, slots, out, gu_tex, spec_type=1):
    """the GU texture paths of one 4U material's albedo / normal maps (converted on first use into `out`), the rules of
    stygian_zinogre/tools/build_em057_01_arc.py textures(): albedo -> BC3 + its '+A' specular map in R, G, B (alpha
    255; the 4U specular mask = the BM alpha for iMaterialStdSpecularMaskType 1, the normal map's left half alpha for
    type 2), normal map -> BC5."""
    paths_of = {}
    nm = slots.get('tNormalMap') if spec_type == 2 else None
    nm_src = r4['textures'][nm - 1][1] if nm else None
    for slot, v in slots.items():
        if not v: continue
        src = r4['textures'][v - 1][1]
        name = src.split('\\')[-1]
        if src not in gu_tex:
            t = tex.decode(S[(src, T['TEX'])])
            path = P + 'mod\\em007_01_' + name.split('em101_')[-1]
            if slot == 'tAlbedoMap':
                m = t[..., 3]
                if nm_src:
                    n = tex.decode(S[(nm_src, T['TEX'])])
                    assert n.shape[0] == t.shape[0] and n.shape[1] == 2 * t.shape[1], (src, nm_src, n.shape, t.shape)
                    m = n[:, :t.shape[1], 3]
                s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = m; s[..., 3] = 255
                out += [(path, T['TEX'], tex.encode_gu(t, 'bc3')), (path + '+A', T['TEX'], tex.encode_gu(s, 'bc3'))]
                gu_tex[('spec', src)] = nm_src
            else:
                out.append((path, T['TEX'], tex.encode_gu(t, 'bc5')))
            gu_tex[src] = path
        elif slot == 'tAlbedoMap' and spec_type:
            assert gu_tex[('spec', src)] == nm_src, 'materials sharing %s want other specular masks' % src
        paths_of[slot] = gu_tex[src]
        if slot == 'tAlbedoMap':
            paths_of['tSpecularMap'] = gu_tex[src] + '+A'
    return paths_of


def model(S, rom, src_name, dst_name, gu_tex, notes):
    """one em101 MOD + MRL (+ the textures it is the first to use) -> [(path, type, data)], the parsed 4U MOD.
    Templates as stygian_zinogre's model(): additive -> 'add', normal-mapped -> 'solid_nm', emissive (4U CBMaterialStd
    emission > 0, diffuse 0) -> 'unlit', else 'solid'; alpha-tested (MRL w7 bit 24 on BSSolid) -> 'solid_at' / 'tar'.
    4U BSBlendAlpha -> 'blend' with the 4U material's own emission, diffuse and specular; one with animations starts in
    the first frame of its first one, the resting state 4U's class plays at spawn (his rage veins: alpha 0, module
    em007_01_mat.c). Until 0.4.5 both went through 'add' with alpha 1. Every 4U material animation is converted. MRL
    before MOD, as in GU's arcs."""
    d4 = S[(P4 + 'mod\\' + src_name, T['MOD'])]
    d4m = S[(P4 + 'mod\\' + src_name, T['MRL'])]
    m4, r4 = modlib.parse(d4), mrl.read(d4m)
    anims4 = mrl_anim.material_anims(d4m)[1]
    out, tex_paths, tex_index, mats = [], [], {}, []
    for mname in m4['material_names']:
        mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
        assert len(mm) == 1, (src_name, mname)
        mm = mm[0]
        states = [s for s in mm['states'] if s]
        std = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd']
        spec_at = mrl.cb_layout(0x20, 'CBMaterialStd')['iMaterialStdSpecularMaskType'][0]
        spec_type = struct.unpack_from('<I', mm['block'], std[0] + 4 * spec_at)[0] if std else 1
        assert spec_type in (0, 1, 2), (mname, spec_type)
        gp = textures(S, r4, {n: v for n, _, v in mm['params'] if n in ('tAlbedoMap', 'tNormalMap')}, out, gu_tex,
                      spec_type)
        slots = {}
        for slot, path in gp.items():
            if path not in tex_index:
                tex_paths.append(path); tex_index[path] = len(tex_paths)
            slots[slot] = tex_index[path]
        std = struct.unpack_from('<8f', mm['block'], 0x60)       # emission rgba, diffuse rgba
        emissive = max(std[0:3]) > 0 and max(std[4:7]) == 0
        key = 'blend' if 'BSBlendAlpha' in states else 'add' if 'BSAddAlpha' in states else \
              ('solid_nm' if 'tNormalMap' in slots else 'unlit' if emissive else 'solid')
        alpha_test = 'BSSolid' in states and mm['words'][7] & mrl_build.W7_ALPHATEST
        if alpha_test:
            key = 'solid_at' if 'tNormalMap' not in slots else 'tar'
        w7 = mm['words'][7]
        extra = dict(mtype=MTYPE.get(mname, int(re.search(r'_m(\d\d)_', mname).group(1))), bias=(w7 >> 16) & 0xF)
        if alpha_test:
            extra['alpha_ref'] = (w7 >> 8) & 0xFF
        consts = {}
        ents4 = anims4.get(mm['name'], [])
        if ents4:
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            anim_vars = mrl_anim.animated_targets(ents4)
            consts.update({k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], 1.0).items()
                           if k in anim_vars})
            extra['anim'] = mrl_anim.build(mrl_anim.gu_entries(ents4, mrl_build.cb_words(rom, key)))
        if key == 'blend':
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            consts.update(mrl_anim.static_constants(mm['block'][std_off:], 1.0))
            if ents4:
                consts.update(mrl_anim.solid_constants(ents4[0]))
        # the 4U material's rasterizer state: the first one GU's shader package has (C: 'XfBA1__m02_angry' lists
        # RSMeshBias5 and RSMeshCNBias8; GU has no RSMeshCNBias* record, so its depth bias 5 stays, culling GU's)
        rs = [s for s in states if s.startswith('RS')]
        rs_gu = [s for s in rs if s in GU_RS]
        mats.append((mname, key, slots, rs_gu[:1], consts, extra))
        notes.append('%s material %s: template %s, type %d, %s, 4U specular mask type %d%s%s' % (
            dst_name, mname, key, extra['mtype'], sorted(p.split('\\')[-1] for p in gp.values()), spec_type,
            ', %d 4U animations' % len(ents4) if ents4 else '',
            ', 4U states %s -> %s' % (rs, rs_gu[:1]) if rs != rs_gu[:1] else ''))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(P + 'mod\\' + dst_name, T['MRL'], mrl_bytes), (P + 'mod\\' + dst_name, T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(gu_xfs, emd, groups, notes):
    """his parts states (rMonsterPartsManager XFS) from his 4U rows, in GU em007_00's file layout: see PART_STATES"""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    assert emdata4u.part_rows(emd) == PART_ROWS, '4U em101 visibility rows changed: review PART_STATES'
    assert len(PART_STATES) == len(states), 'GU em007_00 has another number of parts states'
    named = {g for st in PART_STATES for g, _ in st}
    assert named == set(groups), ('groups without a state / states without a mesh', sorted(named ^ set(groups)))
    data, nobj = emdata4u.xfs_states(PART_STATES)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    notes.append('parts states: %d (GU layout), from his 4U rows; groups %s' % (len(PART_STATES), sorted(named)))
    return bytes(head) + data


def skeleton_check(gu_mod, our_mod, notes):
    """GU em007_00's motions drive our model: the same bone ids with the same parent ids (motion tracks name bones by
    id). The file order differs (C: 4U em101 lists the chains 6..9 / 61 60 and 15..18 / 80 81 before 10..13 / 71 70 and
    19..22 / 90 91, 4U em099 and GU em007_00 the other way round), so bones are compared by id."""
    def by_id(m):
        bl = m['bone_list']
        return {b['index']: (bl[b['parent']]['index'] if b['parent'] != 255 else None, b['pos']) for b in bl}
    g, o = by_id(modlib.parse(gu_mod)), by_id(modlib.parse(our_mod))
    assert set(g) == set(o), 'em101 bone ids differ from GU em007_00\'s'
    assert all(g[k][0] == o[k][0] for k in g), 'em101 bone hierarchy differs from GU em007_00\'s'
    far = max((max(abs(a - b) for a, b in zip(g[k][1], o[k][1])), k) for k in g)
    notes.append('skeleton: %d bones, ids and parent ids equal to GU em007_00\'s (file order differs); largest bind '
                 'position difference %.1f (bone %d)' % (len(o), *far))


def bank0(gu0, own4, notes):
    """GU em007_00_0 with slots OWN_BANK0 = 4U em101_4's animations of the same index (frame counts asserted equal)"""
    ga, oa = lmt.anims(gu0), lmt.anims(own4)
    frames = lambda d, o: struct.unpack_from('<I', d, o + 8)[0]
    d = bytearray(gu0)
    for s in OWN_BANK0:
        assert ga[s] and oa[s] and frames(gu0, ga[s]) == frames(own4, oa[s]), ('bank-0 slot', s)
        struct.pack_into('<I', d, 8 + 4 * s, 0)
    out = lmt.splice(bytes(d), own4, [(s, s) for s in OWN_BANK0])
    notes.append('motions bank 0: GU em007_00_0 with slots %s = 4U em101_4 %s (frames %s)' % (
        list(OWN_BANK0), list(OWN_BANK0), [frames(own4, oa[s]) for s in OWN_BANK0]))
    return out


# GU's retunes of 4U Diablos in the dttune (C, 2026-11-05: GU em007_00's file vs tools/dt_convert.py of 4U em099 on
# it with GU's ranges differ at exactly these 10 bytes): quantities (offset: struct format) and part-table codes (the
# 24-byte records of 4U etd word 29 at +0x3ac, records 0..2: 4U Diablos (4, 0), GU (22, 2), 4U Monoblos (4, 4)).
RETUNE_QTY = {0x38: '<H',        # base HP: GU 4500, 4U Diablos 4300, 4U Monoblos 4000
              0x370: '<H',       # GU 100, 4U Diablos 120, 4U Monoblos 50 (role G)
              0x5ec: '<f'}       # GU 680.0, 4U Diablos 780.0, 4U Monoblos 600.0 (role G)
RETUNE_CODE = (0x3ac, 0x3c4, 0x3dc)


def dttune_gu(gu, c99, c101, notes):
    """his dttune on GU's balance (the user, 2026-11-05: "adapted to MHGU so it is fair"): 4U em101's conversion, and
    where GU retuned 4U Diablos (Black Gravios' rule, unconverted_blocks there): a quantity = his 4U value x GU / 4U
    Diablos; a code (the part table's type / sub byte pairs) = GU's (G: GU's recoding of the same 4U record type; his
    4U sub byte 4 where Diablos has 0 is not kept, a DEVIATION to check)"""
    assert len(gu) == len(c99) == len(c101), 'dttune sizes differ: convert both with --keep-ranges'
    retuned = {i for i in range(len(gu)) if gu[i] != c99[i]}
    covered, out = set(), bytearray(c101)
    for o, f in RETUNE_QTY.items():
        n = struct.calcsize(f)
        covered |= set(range(o, o + n))
        g, d, m = (struct.unpack_from(f, x, o)[0] for x in (gu, c99, c101))
        v = m * g / d
        struct.pack_into(f, out, o, int(v + 0.5) if f != '<f' else v)
        notes.append('dttune +%#x: his 4U %s x GU %s / 4U Diablos %s = %s' % (o, m, g, d, struct.unpack_from(f, out, o)[0]))
    for o in RETUNE_CODE:
        covered |= {o, o + 1}
        notes.append('dttune +%#x part record (type, sub): GU %s (4U Diablos %s, his 4U %s)' % (
            o, tuple(gu[o:o + 2]), tuple(c99[o:o + 2]), tuple(c101[o:o + 2])))
        out[o:o + 2] = gu[o:o + 2]
    assert retuned <= covered, 'GU retunes not covered by the rule: %s' % sorted(hex(i) for i in retuned - covered)
    notes.append('dttune: 4U em101 + GU\'s retunes (%d bytes) on GU\'s balance; %d of %d bytes differ from GU\'s' % (
        len(retuned), sum(a != b for a, b in zip(out, gu)), len(out)))
    return bytes(out)


def dttune_ai(out_keep, c101_keep, c101_ai, notes):
    """the dttune above with his 4U AI distance rows (his AI table's distance checks name his rows, 0.4.0): 4U em101's
    conversion without --keep-ranges (one row, (400, 1000, 2500, 5000), C) differs from the --keep-ranges one only in
    the range block (GU em007_00's three rows) and the header size field; the retuned fields sit before or after that
    block, so each moves by the size difference (asserted by its bytes in both conversions)"""
    pre = next(i for i in range(0x10, min(len(c101_keep), len(c101_ai))) if c101_keep[i] != c101_ai[i])
    suf = next(i for i in range(1, min(len(c101_keep), len(c101_ai))) if c101_keep[-i] != c101_ai[-i]) - 1
    shift = len(c101_ai) - len(c101_keep)
    assert c101_keep[0x0c:pre] == c101_ai[0x0c:pre], 'dttune conversions differ before the range block'
    out = bytearray(c101_ai)
    spans = [(o, struct.calcsize(f)) for o, f in RETUNE_QTY.items()] + [(o, 2) for o in RETUNE_CODE]
    for o, n in spans:
        if o + n <= pre: o2 = o
        elif o >= len(c101_keep) - suf: o2 = o + shift
        else: raise AssertionError('retuned field +%#x inside the range block' % o)
        assert c101_ai[o2:o2 + n] == c101_keep[o:o + n]
        out[o2:o2 + n] = out_keep[o:o + n]
    notes.append('dttune: his 4U AI distance rows (range block %#x..%#x of %d bytes, his conversion %+d bytes); the '
                 'retuned fields moved with it' % (pre, len(c101_keep) - suf, len(c101_keep), shift))
    return bytes(out)


# ---- his 4U AI table (0.4.0, notes/actions.md). GU's interpreter reads 4U tables (Black Gravios' and Stygian's
# findings): area moves are GU engine ops (0x94 set up, 0x95 start, 0x9e advance; patrol 0x96 / 0x97 / 0x4e), and GU's
# class picks group-1 scripts by number only through area_act_tbl (C: every synthesized `14 nn` script, this+0xba34, is
# built from 0xb4e58's entry; no uEm007_00 code writes the think fields). His em101_cmd has its own layout (group 0 28
# scripts, group 1 65; GU's Diablos table 27 / 141), so:
# - groups 0..20 = his (op-0x46 blocks reduced to his case 101; 4U case 102 = White Monoblos);
# - g0 s0: 4U's area-move step `14 0c` (his 4U g1 s12) -> GU's `9e 00 00`, the rest his, natives too (0.4.7: 0.4.0..
#   0.4.6 left its two, 6/8 when he lies burrowed and 1/35 under op 0x68, as raw GU numbers, so GU Diablos' handlers ran
#   them: 6/8 = GU's base rest 0xd37270, 1/35 = Diablos' dig-in 0xd3c3c8, C); g0 s8 (his area move: s0's `3f` branch) =
#   GU's g0 s1; g0 s1 (his patrol: s0's default) = GU's g0 s2; g20 s0 = GU's (ops 0xa0 / 0xa1); group 7 = GU's (none in
#   4U); group 16 = GU's (empty: 4U's rest group, which GU never selects, Black Gravios' check);
# - group 1 = his 65 scripts, then GU's numbers 65..140 empty (`a6 ff`, GU's own empty form) except the scripts
#   area_act_tbl names for the donor (Diablos: 121..127, read from resident.arc), which are GU's, with every script
#   they call imported as GU's copy (appended at 141..);
# - his natives -> GU's dispatch: KEEP (engine actions, the same in both games), TWINS (GU's same-category action whose
#   handler plays the same motions with the same side parameter; interim: GU Diablos' handler, his 4U handler is not
#   ported yet), every other action (c, n) -> (c, PORT_BASE + n), which GU's dispatchers never handle (cat 1 0..35,
#   2 0..200, 3 0..9, 6 0..50, 7 0..200, C) and module/em007_01_moves.c runs as his ported 4U handler.
# GU's scripts run for variant 1 as their op-0x92 else bodies (GU's variant switch, cases 0 and 4 only): imported so.
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_TYPE = 0x3AABBA02
PORT_BASE = 208
KEEP = {(0, 255), (11, 38)}              # GU 0/255 = END (0xca10c), 11/38 = base 0xa134c = 4U base 0x9197c0 (C)
# 4U action: GU action (the handler pairs of scratch twins.py: equal motion sets, 0x404 / 0x40e = GU 0x004 / 0x00e;
# same side parameter r1); APPROX = his r1 = 1 variant on GU's only one
TWINS = {(0, 2): (0, 2), (1, 25): (1, 3), (3, 0): (3, 3), (3, 7): (3, 7), (6, 14): (6, 26)}
# GU actions in the scripts imported from GU (area_act_tbl 121..127 with their calls, g0 s1 / s8, g7, g20) that become
# his: GU 2/3 (GU Diablos' turn = 4U Diablos' 2/3, 0x8d1594 case 3: record 0xe0e034) -> his 2/3, so every turn of his,
# unaware ones in GU's wander script g1 s122 included, runs one handler (module/em007_01_moves.c). His 4U 2/3 (uEm101
# slot 44 0x8df448 -> 0x8dda24 case 3) takes record 0xe0e090 (motions 9 / a, 90 deg in 90 frames; C, GU em007_00_0 slots
# 9..d = 4U em101_0 9..d by per-track keyframe bounds); the port plays the quick record 0xe0e0d0 (motions b / c, 90 deg in
# 18 frames) for 2/3 and 2/24: a DEVIATION from 4U's code, confirmed by the maintainer after viewing 4U footage
# (2026-11-08): unaware, engaged and enraged he makes the same quick turn, enraged only faster by his rage speed
GU_TO_HIS = {(2, 3): (2, 3 + PORT_BASE)}
APPROX = set()                           # his attack twins (7/0 5 6 7 9 18 20 22) are ported: GU's attack with Diablos'
# records
EMC_4U_ONLY = {0x03, 0x06, 0x07, 0x22, 0x2a, 0x36, 0x40, 0x41, 0x46, 0x49, 0x4a, 0x4d, 0x63, 0x8b, 0x91}
AAT_PATH = 'enemy\\area_act_tbl\\enemy'
MOVES_C = os.path.join(MON, 'module', 'em007_01_moves.c')


def emc_tokens(s, lens):
    """a script's instructions, by GU's length table (an op past the table = the end, 0xff)"""
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
    """the script with every switch block of `op` (4U 0x46 = em number, GU 0x92 = variant) reduced to em's body (its
    case, else the else body)"""
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


def action_of(k):
    """his 4U action -> the action his table starts in GU (see above)"""
    if k in KEEP: return k
    if k in TWINS: return TWINS[k]
    assert k[0] in (1, 2, 3, 6, 7) and k[1] + PORT_BASE < 256, ('no GU number for 4U action', k)
    return k[0], k[1] + PORT_BASE


def moves_c_rows():
    """the (category, 4U number) rows of module/em007_01_moves.c's s_moves (`MV(c, n, ...)`)"""
    src = open(MOVES_C, encoding='utf-8').read()
    return {(int(c), int(n)) for c, n in re.findall(r'^\s*MV\((\d+),\s*(\d+),', src, re.M)}


def aat_scripts(rom, index):
    """the group-1 scripts resident area_act_tbl names for registry index `index` (44-byte entries after a 12-byte
    header, script per kind at +0..+31, 0 = none)"""
    _, ents = arcpack.read(rom.read('/nativeNX/loc/arc/resident.arc'))
    d = [x for p, t, x in ents if p == AAT_PATH]
    assert len(d) == 1 and len(d[0]) == 12 + 137 * 44, 'area_act_tbl layout changed'
    e = d[0][12 + 44 * index:12 + 44 * index + 44]
    return sorted({b for b in e[:32] if b})


def cmdtbl(d4, gu, img, aat, notes):
    """4U em101_cmd in GU's language (see above) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[21] and not u4[22], 'EMC group layout changed'
    m = [[emc_em_only(s, 101, lens) for s in gr] for gr in u4[:21]]
    gv = [[emc_em_only(s, 1, lens, 0x92) for s in gr] for gr in g]
    ops = lambda s: {t[0] for t in emc_tokens(s, lens)}
    n1 = len(m[1])
    assert [len(x) for x in m[2:]] == [len(x) if gi not in (7, 16) else {7: 0, 16: 1}[gi] for gi, x in
                                       enumerate(g[2:], 2)], 'his group sizes differ from GU\'s beyond groups 7 / 16'
    # group 1: his scripts; GU's area_act_tbl scripts and everything they call as GU's copies
    g1 = list(m[1]) + [b'\xa6\xff'] * (len(g[1]) - n1)
    placed = {}

    def gu_script(k):
        """our number of GU's group-1 script k (imported with its calls)"""
        if k in placed: return placed[k]
        placed[k] = k if k >= n1 else len(g1)
        if k < n1: g1.append(None)
        g1[placed[k]] = imported(gv[1][k])
        return placed[k]

    gu_turns = []

    def imported(s):
        out = []
        for t in emc_tokens(s, lens):
            if t[0] == 0x14:
                out.append(bytes([0x14, gu_script(t[1])]))
            elif t[0] == 0x00 and len(t) == 3 and (t[1], t[2]) in GU_TO_HIS:
                out.append(bytes([0x00, *GU_TO_HIS[(t[1], t[2])]]))
                gu_turns.append((t[1], t[2]))
            else:
                out.append(t)
        return b''.join(out)

    assert aat and all(n1 <= k < len(g[1]) for k in aat), ('area_act_tbl scripts inside his range', aat)
    for k in aat: gu_script(k)
    groups = [None, g1]
    # group 0
    g0 = list(m[0])
    t0 = emc_tokens(g0[0], lens)
    assert t0[:3] == [b'\x61\x00', b'\x14\x0c', b'\x61\x02'] and b'\x3f\x00\x20\x08' in g0[0] and b'\x20\x01' in g0[0]
    assert emc_tokens(gv[0][0], lens)[:3] == [b'\x61\x00', b'\x9e\x00\x00', b'\x61\x02']
    g0[0] = b''.join([t0[0], b'\x9e\x00\x00'] + t0[2:])
    assert gv[0][1] == b'\x94\x00\x00\x95\x00\x00\xff' and {0x96, 0x97} <= ops(gv[0][2])
    assert ops(m[0][8]) & EMC_4U_ONLY and ops(m[0][1]) & EMC_4U_ONLY, 'his g0 s1 / s8 are not his area scripts'
    g0[8], g0[1] = imported(gv[0][1]), imported(gv[0][2])
    groups[0] = g0
    for gi in range(2, 21):
        if gi in (7, 20): groups.append([imported(s) for s in gv[gi]])
        elif gi == 16: groups.append([])
        else: groups.append(list(m[gi]))
    gu_made = {(0, 1), (0, 8)} | {(7, k) for k in range(len(gv[7]))} | {(20, 0)}     # g0 s0 is his but one token
    gu_made |= {(1, k) for k in placed.values()}
    # what his own scripts reach (roots: group 0 and groups 2..20; 0x14 calls into group 1, 0x20 gotos in group 0)
    reach, todo = set(), [(0, k) for k in range(len(g0))] + [(gi, k) for gi in range(2, 21) for k in
                                                             range(len(groups[gi]))]
    while todo:
        gi, k = todo.pop()
        if (gi, k) in reach: continue
        reach.add((gi, k))
        for t in emc_tokens(groups[gi][k], lens):
            if t[0] == 0x14 and (gi, k) not in gu_made: todo.append((1, t[1]))
            if t[0] == 0x20 and gi == 0: todo.append((0, t[1]))
    his = sorted((gi, k) for gi in range(21) for k in range(len(groups[gi])) if (gi, k) not in gu_made)
    left = {(gi, k): sorted(ops(groups[gi][k]) & EMC_4U_ONLY) for gi, k in his if (gi, k) in reach}
    assert not any(left.values()), ('4U-only op in a script his table reaches', {k: v for k, v in left.items() if v})
    # natives: his scripts -> GU's dispatch
    used = set()
    for gi, k in his:
        out = []
        for t in emc_tokens(groups[gi][k], lens):
            if t[0] == 0 and len(t) == 3:
                used.add((t[1], t[2]))
                t = bytes([0]) + bytes(action_of((t[1], t[2])))
            out.append(t)
        groups[gi][k] = b''.join(out)
    ported = sorted(k for k in used if k not in KEEP and k not in TWINS)
    rows = moves_c_rows()
    notes.append('AI table: 4U em101_cmd (case 101), GU\'s g0 s0 area step / s1 patrol / s8 area move, g7, g20 s0, '
                 'empty g16; group 1 = his %d + GU %d..%d empty but area_act_tbl %s (+ calls imported at %s)' % (
                     n1, n1, len(g[1]) - 1, aat, sorted(v for v in placed.values() if v >= len(g[1]))))
    assert gu_turns, 'no GU 2/3 in the imported scripts: GU_TO_HIS has nothing to do'
    notes.append('AI table: GU actions in the imported GU scripts that run his 4U handler: %s' % ' '.join(
        '%d/%d->%d/%d x%d' % (k + GU_TO_HIS[k] + (gu_turns.count(k),)) for k in sorted(set(gu_turns))))
    notes.append('AI table: his scripts no script reaches (picked by 4U code; nothing in GU picks them): %s' % [
        'g%d s%d' % x for x in his if x not in reach])
    twins = ' '.join('%d/%d->%d/%d' % (k + TWINS[k]) for k in sorted(used & set(TWINS)))
    notes.append('AI table natives: keep %s; twins %s (approximate: %s); ported as (c, %d + n): %s' % (
        sorted(k for k in used if k in KEEP), twins, sorted(APPROX & used), PORT_BASE,
        ' '.join('%d/%d' % k for k in ported)))
    missing = [k for k in ported if k not in rows]
    notes.append('AI table: ported actions without a C handler yet (module/em007_01_moves.c ends them at once, '
                 'logged): %s' % (' '.join('%d/%d' % k for k in missing) or 'none'))
    stray = sorted(rows & (KEEP | set(TWINS)))
    assert not stray, ('C rows for actions the table gives to GU', stray)
    return emc.build(groups, ver)


def moves_c_twins():
    """the TW(c, n, gc, gn) rows of module/em007_01_moves.c (its copy of TWINS for his handlers' chains)"""
    src = open(MOVES_C, encoding='utf-8').read()
    return {(int(a), int(b)): (int(c), int(d)) for a, b, c, d in
            re.findall(r'TW\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', src.split('s_twins[][4] = {')[1].split('};')[0])}


# His 4U attack records (0.4.0): GU's attackEx looks an index >= 1000 up in a second table, record 0x70ffc from
# this+0x75d8 and hitsize 0x7105c from this+0x75e0, filled by manifest fields 27 / 29 (attackdata / hitsize types in all
# 18 GU monsters that use them; GU's Diablos leaves both empty, C). His handlers attack with 1000 + his 4U index
# (module/em007_01.h MB_ATK_BASE, checked here); an attack record's byte 25 names its hitsize group (C: 0x7de00 reads
# it next to 0x7105c's table), so his records and groups go there unchanged (tools/emdata4u.py, byte 28 = 6 as every
# converted 4U record), and GU's own pair (fields 26 / 28) keeps serving GU's Diablos handlers.
ATK2_FIELD, HTS2_FIELD = 27, 29
MODULE_H = os.path.join(MON, 'module', 'em007_01.h')
# GU's retunes of 4U Diablos' attack records on his (0.4.3; the user, 2026-11-05: "check his HP / attack values"):
# GU em007_00's attackdata = 4U em099's converted but 15 records (C): power byte 4 of 9 (55 -> 80, 55 -> 70, 40 -> 55,
# 55 -> 65, 60 -> 70 twice with byte 6 3 -> 2, 40 -> 55, 60 -> 80, 55 -> 60), byte 30 0 -> 5 of 5, one hitsize group.
# The rule of his body values (dttune_gu): his 4U value where GU kept Diablos', GU's change where his 4U record equals
# the Diablos one but for TWIN_FREE (his own hitsize groups, GU's code byte, the knockback bits): the same attack.
TWIN_FREE = (25, 28, 31)


def gu_retunes(atk, gu_atk, notes):
    """his converted attackdata with GU's changes of the 4U Diablos records he shares (see above)"""
    recs = lambda d: [bytearray(d[16 + 32 * k:48 + 32 * k]) for k in range(struct.unpack_from('<I', d, 8)[0])]
    D, G, M = recs(emdata4u.attackdata(emdata4u.load_4u('em099')['etd'])), recs(gu_atk), recs(atk)
    assert len(D) == len(G), 'GU em007_00 attackdata no longer 4U em099\'s length'
    key = lambda r: bytes(b for o, b in enumerate(r) if o not in TWIN_FREE)
    done, set_to = [], {}
    for k, (d, g) in enumerate(zip(D, G)):
        diff = [o for o in range(32) if o != 28 and d[o] != g[o]]
        if not diff or 25 in diff: continue          # a hitsize group change concerns Diablos' own groups
        for i, m in enumerate(M):
            if not any(m[:28]) or key(m) != key(d): continue
            for o in diff:
                assert set_to.setdefault((i, o), g[o]) == g[o], ('two retunes of one record differ', i, o)
                m[o] = g[o]
            done.append('M%d<-D%d %s' % (i, k, ' '.join('+%d %d->%d' % (o, d[o], g[o]) for o in diff)))
    notes.append('attack data: GU\'s retunes of 4U Diablos records on his equal ones (but bytes %s): %s' % (
        TWIN_FREE, ', '.join(done)))
    out = bytearray(atk)
    for i, m in enumerate(M):
        out[16 + 32 * i:48 + 32 * i] = m
    return bytes(out)


def attack_files(gu_atk, notes):
    """{field: (path, data)}: his 4U em101 attackdata / hitsize for GU's second attack table, GU's Diablos retunes
    applied to the records he shares with 4U Diablos (gu_retunes)"""
    etd = emdata4u.load_4u('em101')['etd']
    atk, hts = gu_retunes(emdata4u.attackdata(etd), gu_atk, notes), emdata4u.hitsize(etd, off2_gu=True)
    n, ng = struct.unpack_from('<I', atk, 8)[0], struct.unpack_from('<I', hts, 8)[0]
    assert re.search(r'#define MB_ATK_BASE 1000\b', open(MODULE_H, encoding='utf-8').read()), 'MB_ATK_BASE != 1000'
    b25 = {atk[16 + 32 * k + 25] for k in range(n) if any(atk[16 + 32 * k:48 + 32 * k])}
    assert max(b25) < ng, ('attack record names a hitsize group past his table', max(b25), ng)
    notes.append('attack data: his 4U em101 attackdata (%d records) / hitsize (%d groups) in fields %d / %d (GU\'s '
                 'second table: his index i -> 1000 + i)' % (n, ng, ATK2_FIELD, HTS2_FIELD))
    return {ATK2_FIELD: ('enemy\\hit_data\\em007_01_attackdata', atk),
            HTS2_FIELD: ('enemy\\hit_data\\em007_01_hitsize', hts)}


# ---- his effects (0.4.1). 4U em101.arc carries his own MEF em101_0 (66 records: his EFL family em101_* = MEF group
# 101, and the 4U common qe000 / 006 / 008 / 013 families) and his EFLs; his motions name MEF ids in their LMT event
# group 2. GU's em007_00 has PSLs for banks 0..3 only (field 22 empty, as GU's Diablos has no bank 4). Black Gravios'
# rule (the user, 2026-11-02): a move GU's Diablos has keeps GU's look, his own moves get 4U's effects. So banks 0..3
# keep GU's PSLs (his banks 0..3 are Diablos' animations), and bank 4 (his own motions, field 8 = 4U em101_4) gets a
# PSL from his em101_4 events (tools/efl4u2gu.py effect_set, slot kind 4 = PEL u list 1). PEL u = GU em007_00u's list
# 1 (20 records, GU's PSLs name them) + his 66 MEF records (ids 0..35 500..523 1000..1032, none of GU's: asserted),
# list 2 = GU's (GU's class posts its ids). Sounds need nothing: GU's em007 sound call keeps 4U em099's bank-4 records
# (keys 4000 + 0x00 0x01 0x04 0x0e 0x11 0x14 0x15 0x18 0x19 0x1a 0x1e 0x1f 0x21 0x22 0x24 0x25), which 4U shared
# between Diablos and Monoblos (his arc loads sound\\call\\em\\em099, C).
# Burrow trail (the user, 2026-11-05: GU's Diablos effect, not 4U's): no code-posted 4U EFL any more (em101_019 the
# mound, em101_020 the dust, 0.4.1..0.4.3): his burrow handlers post GU's common trail, id 2 (module/em007_01_mv_h.c).
PEL_U = 'effect\\pel\\em\\em007_01u'
PSL4 = 'effect\\psl\\enemy\\em007\\em007_01\\mot\\em007_01_4'
MEF_4U = 'effect\\mef\\em\\em101_0'
EFX_GROUPS = {101: 'effect\\efl\\em\\em101\\em101_%03d'}
EFX_GROUPS.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 6, 8, 13)})


def dunes_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Dunes hunting areas' area_color_soil (his
    three 4U quests are on the Dunes; tigerstripe_zamtrios' build_em067_01_arc.py dunes_soil, the same rule)"""
    import ctr, efl4u2gu
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


def pel_ids(body):
    """record ids of a PEL list body (u8 path length, path, 2 bytes, 160 bytes: id at +0x30)"""
    ids, i = [], 0
    while i < len(body):
        L = body[i]
        ids.append(struct.unpack_from('<H', body, i + 1 + L + 2 + 0x30)[0])
        i += 1 + L + 2 + 160
    assert i == len(body), 'PEL list layout'
    return ids


# His roar (bank-4 motion 4 = 0x404: 1/21 1/34 2/7) starts 4U's radial blur at the head at frame 112 (0xc0819c: a new
# uMhRadialBlurFilter, 200 B, area-gated, C; GU has no spawn helper for it, dalamadur dala_efx.c), not an EFL. GU's
# Diablos plays its roar air in that animation instead (PEL c id 90 = cm202_050 on joint 3, the only slot of GU's
# bank-0 motion 4, the same animation as his 0x404, tools: bank0). As Black Gravios' roars (the user chose GU's look
# there): GU's air slot with GU's frames goes into his bank-4 motion-4 entry, next to his own 4U slots. DEVIATION.
ROAR_MOTIONS4 = (4,)


def psl_entry(psl, i):
    """(frames, slot mask, ids[32], kinds[32], per-frame bits) of PSL entry i, or None (black_gravios' layout:
    entry {u32 frames, u16 0, u8 32, u8 0, u32 data, u32 0}; data {u32 mask, u16 id[32], u32 kind[32], u32 0[32], u32
    runs, u32 run offset}; runs {u32 bits, u32 frames})"""
    o = struct.unpack_from('<I', psl, 8 + 4 * i)[0] if i < struct.unpack_from('<H', psl, 6)[0] else 0
    if not o: return None
    frames, _, _, _, da, _ = struct.unpack_from('<IHBBII', psl, o)
    mask = struct.unpack_from('<I', psl, da)[0]
    ids = list(struct.unpack_from('<32H', psl, da + 4))
    kinds = list(struct.unpack_from('<32I', psl, da + 68))
    assert not any(struct.unpack_from('<32I', psl, da + 196)), ('PSL entry rest', i)       # psl_put writes zeros there
    nr, ra = struct.unpack_from('<II', psl, da + 0x144)
    per = [b for k in range(nr) for b, f in [struct.unpack_from('<II', psl, ra + 8 * k)] for _ in range(f)]
    return frames, mask, ids, kinds, per


def psl_put(out, i, frames, mask, ids, kinds, per):
    """entry i of the PSL bytearray out -> a new data block appended at the end (black_gravios' psl_put)"""
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


def roar_air(psl4, gu_psl0, notes):
    """his bank-4 PSL with GU's roar air slot (PEL c id 90, kind 3) of GU's bank-0 motion 4 in ROAR_MOTIONS4"""
    out = bytearray(psl4)
    gf, gmask, gids, gkinds, gper = psl_entry(gu_psl0, 4)
    air = [k for k in range(32) if gmask >> k & 1 and (gids[k], gkinds[k]) == (90, 3)]
    assert len(air) == 1, 'GU\'s roar (bank 0 motion 4) has no single air slot'
    for m in ROAR_MOTIONS4:
        assert m < struct.unpack_from('<H', out, 6)[0], ('bank-4 PSL ends before motion', m)
        e = psl_entry(out, m)
        if e: f, mask, ids, kinds, per = e
        else: f, mask, ids, kinds, per = gf, 0, [0] * 32, [0] * 32, [0] * (gf - 1)
        assert f == gf, ('his roar and GU\'s differ in frames', f, gf)
        k = next(k for k in range(32) if not mask >> k & 1)
        mine = [(ids[j], kinds[j]) for j in range(32) if mask >> j & 1]
        ids[k], kinds[k] = 90, 3
        per = [b | ((gper[x] >> air[0] & 1) << k) for x, b in enumerate(per)]
        psl_put(out, m, f, mask | 1 << k, ids, kinds, per)
        on = [x for x, b in enumerate(gper) if b >> air[0] & 1]
        notes.append('roar: bank-4 motion %d: his 4U slots %s + GU\'s air (cm202_050, PEL c 90) in slot %d, frames '
                     '%d..%d' % (m, mine, k, min(on), max(on)))
    return bytes(out)


def effects(gu_pel_u, gu_psl0, notes):
    """his effects -> ([(path, type, data)], {field: (path, type)}): see above"""
    import efl4u2gu
    T4 = efl4u2gu.T
    gu_lists = efl4u2gu.pel_lists(gu_pel_u)
    assert gu_lists[0][0] == 0, 'GU em007_00u list 0 not empty'
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef=MEF_4U, em_efl='effect\\efl\\em\\em101\\', groups=EFX_GROUPS,
                extra=[], lmts=[(P4 + 'mot\\em101_4', PSL4)], pel=PEL_U, soil=dunes_soil(notes), list2=gu_lists[2])
    log = []
    out = efl4u2gu.effect_set(spec, log)
    mine_lists = efl4u2gu.pel_lists(out.pop((PEL_U, T4['PEL'])))
    mine, list2 = mine_lists[1], mine_lists[2]
    gu1 = pel_ids(gu_lists[1][1])
    assert not set(pel_ids(mine[1])) & set(gu1), 'PEL list-1 ids collide with GU\'s'
    assert list2 == gu_lists[2], 'PEL list 2 = GU\'s'
    pel = b'PEL\0' + struct.pack('<I', 15) + struct.pack('<I', 0) + \
        struct.pack('<I', gu_lists[1][0] + mine[0]) + gu_lists[1][1] + mine[1] + \
        struct.pack('<I', list2[0]) + list2[1]
    lists = efl4u2gu.pel_lists(pel)
    assert pel_ids(lists[1][1]) == gu1 + pel_ids(mine[1]) and lists[2] == list2, 'merged PEL u layout'
    assert (PSL4, T4['PSL']) in out, 'no bank-4 PSL'
    out[(PSL4, T4['PSL'])] = roar_air(out[(PSL4, T4['PSL'])], gu_psl0, notes)
    ents = [(p, t, d) for (p, t), d in out.items()] + [(PEL_U, T4['PEL'], pel)]
    notes.append('effects: PEL u = GU em007_00u (list 1: %d, list 2: %d) + his 4U em101_0 records (%d); PSL bank 4 '
                 'from 4U em101_4; banks 0..3 GU\'s; %d converted 4U files' % (
                     gu_lists[1][0], gu_lists[2][0], mine[0], len(out) - 1))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return ents, {17: (PEL_U, T4['PEL']), 22: (PSL4, T4['PSL'])}


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
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em007_00's file of manifest field k

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    m4 = None
    for src_name, dst_name, field in MODELS:
        files, m = model(S, rom, src_name, dst_name, gu_tex, notes)
        ents += files
        own[field] = (P + 'mod\\' + dst_name, T['MOD'])
        m4 = m4 or m
        if field == 0:
            skeleton_check(gfile(0), [d for p, t, d in files if t == T['MOD']][0], notes)
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em007_01', T['XFS'], parts_xfs(gfile(3), emdata4u.load_4u('em101')['emd'], groups, notes)))
    own[3] = (P + 'mod\\em007_01', T['XFS'])
    own4 = S[(P4 + 'mot\\em101_4', T['LMT'])]
    ents.append((P + 'mot\\em007_01_0', T['LMT'], bank0(gfile(4), own4, notes)))
    own[4] = (P + 'mot\\em007_01_0', T['LMT'])
    assert gman[BANK4_FIELD] == -1, 'GU em007_00 has a motion list 4 now'
    ents.append((P + 'mot\\em007_01_4', T['LMT'], own4))
    own[BANK4_FIELD] = (P + 'mot\\em007_01_4', T['LMT'])
    notes.append('motions bank 4: 4U em101_4 (%d animations) in field %d' % (sum(1 for o in lmt.anims(own4) if o),
                                                                            BANK4_FIELD))
    typ = ghash[fileid_entry(img, gman[33])][1]
    conv = lambda d: open(os.path.join(DT_DIR, d, 'dttune.bin'), 'rb').read()
    dtt = dttune_gu(gfile(33), conv('dt_em099_gu_ranges'), conv('dt_em101_gu_ranges'), notes)
    dtt = dttune_ai(dtt, conv('dt_em101_gu_ranges'), conv('dt_em101'), notes)
    ents.append(('enemy\\dt_tune\\em007_01_dttune', typ, dtt))
    own[33] = ('enemy\\dt_tune\\em007_01_dttune', typ)
    gu_cmd = [d for p, t, d in gents if p == 'enemy\\cmd_tbl\\em007_00_cmdtbl' and t == EMC_TYPE]
    assert len(gu_cmd) == 1 and fileid_entry(img, gman[37]) == (phash('enemy\\cmd_tbl\\em007_00_cmdtbl'), EMC_TYPE)
    aat = aat_scripts(rom, ALLOC['donor_index'])
    ents.append(('enemy\\cmd_tbl\\em007_01_cmdtbl', EMC_TYPE,
                 cmdtbl(S[(P4 + 'data\\em101_cmd', EMC_TYPE)], gu_cmd[0], img, aat, notes)))
    own[37] = ('enemy\\cmd_tbl\\em007_01_cmdtbl', EMC_TYPE)
    assert moves_c_twins() == TWINS, 'module/em007_01_moves.c TW rows differ from TWINS'
    assert gman[ATK2_FIELD] == gman[HTS2_FIELD] == -1, 'GU em007_00 uses the second attack table now'
    for k, (path, data) in attack_files(gfile(ATK2_FIELD - 1), notes).items():
        typ = ghash[fileid_entry(img, gman[k - 1])][1]          # the type of fields 26 / 28 (same in every GU monster)
        ents.append((path, typ, data))
        own[k] = (path, typ)
    # his hurt and camera volumes (0.4.5; 0.1.0..0.4.4 shared GU Diablos': two side horns and a neck volume on a monster
    # with one centre horn and a frill): 4U em101 emd words 8 / 9. Same bones (skeleton_check), parts and hitzone rows as
    # his dttune (4U em101), and his volumes carry the flag sonic bombs need (asserted)
    emd = emdata4u.load_4u('em101')['emd']
    for k, word, path in ((30, 8, 'enemy\\body_data\\em007_01_bodydata'),
                          (31, 9, 'enemy\\cam_body_data\\em007_01_cambodydata')):
        typ = ghash[fileid_entry(img, gman[k])][1]
        data = emdata4u.bodydata(emd, word)
        ents.append((path, typ, data))
        own[k] = (path, typ)
        if k == 30:
            n = struct.unpack_from('<I', data, 8)[0]
            recs = [struct.unpack_from('<8H', data, 16 + 44 * i) for i in range(n)]
            bones = {b['index'] for b in modlib.parse([d for p, t, d in ents if t == T['MOD']][0])['bone_list']}
            assert {r[0] for r in recs} <= bones | {255}, 'a hurt volume names a bone his model lacks'
            assert sum(1 for r in recs if r[5] & 4) >= 8, 'sonic bombs need hurt volumes with flag 4'
            notes.append('hurt volumes: his 4U em101 bodydata, %d records (GU Diablos: %d)' % (
                n, struct.unpack_from('<I', gfile(30), 8)[0]))
    assert gman[22] == -1, 'GU em007_00 has a bank-4 PSL now'
    files, fields = effects(gfile(17), gfile(18), notes)
    ents += files
    own.update(fields)
    dtb = open(os.path.join(DT_DIR, 'dt_em101_gu_ranges', 'dtbase.bin'), 'rb').read()
    assert dtb == gfile(32), 'dtbase of 4U em101 differs from GU em007_00\'s: own it'
    sys.path.insert(0, HERE)
    import routes_em007_01 as routes     # his 4U area behaviour on the Dunes
    plan = routes.plan(S[(P4 + 'data\\em101_cmd', 0x3AABBA02)])
    for k, kind in AREA_FIELDS.items():
        typ = ghash[fileid_entry(img, gman[k])][1]
        build_file = {'area_link': routes.area_link_file, 'map_info': routes.map_info_file,
                      'area_select': routes.area_select_file}[kind]
        ents.append(('enemy\\%s\\em007_01' % kind, typ, build_file(gfile(k), plan, notes)))
        own[k] = ('enemy\\%s\\em007_01' % kind, typ)
    import hagi_em007_01                 # carves: 4U High tables in s2, G in s4, GU's filler in s0 / s1 / s3
    for k, data in hagi_em007_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em007_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    notes.append('carves: 4U em101 High / G tables in hagi s2 / s4 (tools/hagi_em007_01.py)')

    # ---- the shared GU em007_00 files: everything but what ours replace and em007_00's model (MOD, MRL, textures)
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
    notes.append('shared from em007_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em007_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U em101)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em007_00, its file ID)'

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
        if p.startswith(P) and t == T['LMT']:
            for o in lmt.anims(d):
                if o: lmt.blocks(d, o)

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
    json.dump(dict(monster='em007_01 (Monoblos)', id='0x%x' % ALLOC['em_id'],
                   registry_index=ALLOC['registry_index'], file_id_base='0x%x' % FILE_ID_BASE,
                   file_count=len(new_files), manifest=fields,
                   files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p))
                          for f, p, t in new_files], notes=notes),
              open(OUT_JSON, 'w', encoding='utf-8', newline='\n'), indent=1)    # LF on every OS (.gitattributes)
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
