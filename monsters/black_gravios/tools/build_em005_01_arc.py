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
      cmd_tbl\\em005_01_cmdtbl             4U em040_cmd for em 41 in GU's language (cmdtbl(): op-0x46 em switches
                                           reduced to their em-41 bodies, GU's area-move scripts, GU's extra entries)
      effect\\pel\\em\\em005_01u, PSL      GU em005_00u + 4U em041_1's records; GU's PSLs, 4U's slots only in the
      ...\\em005_01_0.._4                  motions GU gives no effect; his EFLs / effect model converted (effects())
  shared, GU em005_00 (original paths + file IDs): motions, camera, sound, PEL c, PSLs 0 / 1 / 3, shells,
      attack / hit / body / cambody data, dtbase, dtbparts, dou mou ka, area data (maps 7 8 12 13 24: the Volcanic
      Hollow of its quests is map 12).
Known deviations (notes/plan.md): the 4U emd word-32 colour table (em041's darker part colours) has no known GU field;
4U's rest script (EMC group 16) and the shots of g1 s59 are not in; GU's versions of the shared Gravios effects play.
Inputs besides the arcs: dump/converted/em041/dt_em040/ and dt_em041/ (build.py step dt: tools/dt_convert.py, donor
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
import alloc, arcpack, emc, emdata4u, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, tex

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
P40 = 'enemy\\em040\\'           # 4U Gravios' files em041.arc ships
P0 = 'enemy\\em005\\em005_00\\'  # GU variant 0
P = 'enemy\\em005\\em005_01\\'   # ours
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 1, 3, 33, 46, 47, 48, 49, 50, 37, 17, 20, 22, 18, 19, 21]
DT_DIR = os.path.join(ROOT, 'dump/converted/em041')           # build.py step dt
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


# AI table (notes/plan.md "His AI"). 4U em040_cmd (em041.arc ships it) serves em 38, 39, 40, 41 and 115: their
# differences are EMC op 0x46 blocks, a switch on the em number. GU's interpreter has no op 0x46 (handler 0x8470c skips
# the token, so every case body would run in turn), and GU em005_00's table is GU's rewrite of em040_cmd: 4U's 0x46
# became GU's op 0x91 (switch on the em number this+0xb5f4) with case 4 (Basarios) and the else only, so the case-41
# bodies (Black Gravios' own selectors in g0 s2, 7/71 in g1 s39 s70, 7/79 in g1 s65..s73) are gone, and GU emptied the
# scripts its Gravios does not use (`a6 ff`, op 0xa6 = no-op: g0 s20 = his G-rank selector, g1 s35 s39 s42 s44 s45
# s59..s61 s70 s71). Our table serves variant 1 only, so every 0x46 block is reduced to its case-41 body (else the else
# body), as Stygian's (build_em057_01_arc.py). GU's language replaces 4U's where the engine needs it (EMC_GU: the area
# move g0 s0 / s4 and patrol g0 s1 (4U ops 0x03 0x06 0x36 0x4d are no-ops in GU, area moves are GU's engine ops 0x94
# 0x95 0x9e), g20 s0), GU's extra entries are appended (g0 s22, g1 s74..s94: GU's class picks group-1 scripts 74..82
# by number, area_act_tbl entry 113), and group 16 (4U's rest script, g16 s0: 1/38 and 1/41, which GU's dispatcher
# ends at once (0xca10c); GU's table has no group-16 entry) stays GU's (empty). Every native action of the table
# reaches the GU handler of 4U's handler with 4U's parameters (C, dispatcher emulation 2026-11-01, plan.md).
# Instruction lengths: GU's table main 0x1732c8c (byte < 0x80 = argument count; 0x8n..0xBn block ops: 00 opens with n
# args, 01 = case with a 1..4-byte value, 02 else, ff end).
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_GU = {(0, 0), (0, 1), (0, 4), (20, 0)}           # (group, script): GU's version
EMC_GU_GROUPS = (16,)                                 # whole group GU's
EMC_4U_AREA_OPS = {0x03, 0x06, 0x22, 0x2a, 0x35, 0x36, 0x40, 0x41, 0x49, 0x4a, 0x4d, 0x63, 0x8b}   # 4U area / patrol


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
    """the script with every em-switch block (4U op 0x46, GU op 0x91) reduced to em's body (its case, else the else)"""
    out, frames = bytearray(), []                   # per open block: [taking, taken]
    for t in emc_tokens(s, lens):
        if t[0] == op:
            if t[1] == 0x00: frames.append([False, False])
            elif t[1] == 0x01: frames[-1][0] = t[2] == em and not frames[-1][1]; frames[-1][1] |= frames[-1][0]
            elif t[1] == 0x02: frames[-1][0] = not frames[-1][1]; frames[-1][1] = True
            else: frames.pop()
            continue
        if all(f[0] for f in frames): out += t
    assert not frames, 'unbalanced em-switch block'
    return bytes(out)


def cmdtbl(d4, gu, img, notes):
    """4U em040_cmd for em 41 in GU's language (see above) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[22], 'EMC group layout changed'
    assert [emc_em_only(s, 41, lens) for s in u4[21]] == [b'\xff'], "4U group 21 (em 115's) is not empty for em 41"
    ops = lambda s: {t[0] for t in emc_tokens(s, lens)}
    out, own, gu_taken = [], [], []
    for gi in range(21):
        if gi in EMC_GU_GROUPS:
            out.append(list(g[gi])); continue
        scripts = []
        for k, s in enumerate(u4[gi]):
            if (gi, k) in EMC_GU:
                scripts.append(g[gi][k]); gu_taken.append((gi, k)); continue
            s = emc_em_only(s, 41, lens)
            assert not ops(s) & {0x46, 0x91}, ('4U em switch / rest op left', gi, k)
            assert not ops(s) & EMC_4U_AREA_OPS or s == g[gi][k], ('4U area op in a script GU changed', gi, k)
            if s != emc_em_only(u4[gi][k], 40, lens): own.append((gi, k))
            scripts.append(s)
        assert len(scripts) <= len(g[gi]), gi
        out.append(scripts + list(g[gi][len(scripts):]))
    # the scripts GU's taken / appended group-1 ones call (em 5 bodies of GU's own em switches) must be GU's too; GU's
    # appended selector g0 s22 (reached only through GU's g0 s2, which ours does not have) may call 4U versions
    added = [(gi, k) for gi in range(21) if gi not in EMC_GU_GROUPS for k in range(len(u4[gi]), len(g[gi]))]
    loose = set()
    for gi, k in gu_taken + added:
        for t in emc_tokens(emc_em_only(g[gi][k], 5, lens, 0x91), lens):
            if t[0] == 0x14 and out[1][t[1]] != g[1][t[1]]:
                assert gi == 0 and (gi, k) in added, ('GU script calls a 4U script that differs', gi, k, t[1])
                loose.add(t[1])
    assert [len(x) for x in out] == [len(x) for x in g], 'our table must carry every GU entry number'
    notes.append('AI table: 4U em040_cmd for em 41 (op-0x46 blocks reduced; em 41 differs from em 40 in %s), GU\'s '
                 'versions of %s, GU\'s group %s, GU extra entries appended (%s)' % (
                     ['g%d s%d' % a for a in own], ['g%d s%d' % a for a in sorted(gu_taken)], list(EMC_GU_GROUPS),
                     ['g%d s%d..s%d' % (gi, len(u4[gi]), len(g[gi]) - 1) for gi in range(21)
                      if gi not in EMC_GU_GROUPS and len(g[gi]) > len(u4[gi])]))
    notes.append('AI table: GU\'s appended selector g0 s22 calls our 4U versions of g1 %s' % sorted(loose))
    return emc.build(out, ver)


# Effects (notes/plan.md "His own AI and effects"). 4U em041.arc loads em040's MEF em040_0 (Gravios' records, ids
# 0..1032, on em040's EFLs and the qe families) and its own em041_1 (28 records, ids 2004..2062, on em040_002 013 200
# 201 and em041_002); the shared em040 motions name both sets in their event group 2 (in em040.arc the 20xx ids have
# no record, so only Black Gravios plays them, C). Every em041_1 record carries a condition bit (MEF byte 0;
# module/em005_01_fx.c gates them, its table asserted here). GU em005_00 renumbered Gravios' motion effects onto GU's
# own EFLs (PSL kind 3 = PEL c list 1, kind 4 = PEL u list 1). User decision 2026-11-02 (after testing 0.4.2, which
# played 4U's records in every motion: "beams and gas look odd"): a move GU's Gravios has looks as GU's Gravios does,
# 4U's effects only on his own moves. So every motion GU gives an effect keeps GU's PSL entry, and only the motions GU
# leaves without one and 4U's events give an em041_1 record (bank 2 motions 19 21 33 50: 7/79's 562 among them) play
# 4U's slots at 4U's frames (psl_4u); PEL u list 1 = GU em005_00u's + em041_1's records, PEL list 2 (GU's class posts)
# GU's. The EFLs are converted under their 4U paths (no GU arc uses them) with the Volcanic Hollow area colour (5 of
# his 8 quests); grey rock chunks hidden as Stygian's (issue #6, efl4u2gu CHUNK_MODELS).
PEL_U = 'effect\\pel\\em\\em005_01u'
PSL = 'effect\\psl\\enemy\\em005\\em005_01\\mot\\em005_01_%d'
MEF_4U = 'effect\\mef\\em\\em040_0'
MEF_OWN = 'effect\\mef\\em\\em041_1'
EFX_GROUPS = {40: 'effect\\efl\\em\\em040\\em040_%03d', 41: 'effect\\efl\\em\\em041\\em041_%03d'}
EFX_GROUPS.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 6, 8, 13)})
EFX_BANKS = (0, 1, 2, 3, 4)     # motion lists: manifest fields 4 + bank (GU's motions), PSL fields 18 + bank (ours)
EFX_KIND = 4                    # PSL slot kind of PEL u list 1
# code-posted effects (PEL list 2 after GU's records): the spit's request 8 = em040_020 mask 1 on the monster
# (0x809ae0, joint 255; module/em005_01_spit.c) and the 7/57 / 7/71 laser's two uEffect002 41 = em041_101 masks 1 /
# 2, scale 1.0 (uShell016 33 / 35 init 0xc6a378; world records placed by module/em005_01_laser.c). 4040 / 4041 (the
# spit's uShell016 effects em024_009 / em040_100, 0.4.5) are gone: GU gives that shell its own effect.
CODE_FX = [('effect\\efl\\em\\em040\\em040_020', dict(id=4042, joint=-1, k=0, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                     scl=(1.0, 1.0, 1.0))),
           ('effect\\efl\\em\\em041\\em041_101', dict(id=4043, joint=-1, k=0, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                     scl=(1.0, 1.0, 1.0))),
           ('effect\\efl\\em\\em041\\em041_101', dict(id=4044, joint=-1, k=1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                     scl=(1.0, 1.0, 1.0))),
           # the beam's heat burst (0x808410 at frame 120: request 6 = (50, 6) = em040_013, mask 1 << 0, or 1 << 8 with
           # state bit 4; module/em005_01_beam.c): before 0.4.7 the burst's hit came with no look (test 2026-11-03)
           ('effect\\efl\\em\\em040\\em040_013', dict(id=4045, joint=-1, k=0, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                     scl=(1.0, 1.0, 1.0))),
           ('effect\\efl\\em\\em040\\em040_013', dict(id=4046, joint=-1, k=8, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                                     scl=(1.0, 1.0, 1.0)))]
# the roars (bank 0 motions 104 = 1/17 and 4): GU's air effect on the head for 4U's length (roar_head)
ROAR_MOTIONS = (4, 104)
ROAR_ID = 3900                  # PEL u list 1
ROAR_JOINT = 3                  # 4U's qe013 joint (em040_0 ids 16 / 17)


def volcano_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Volcanic Hollow hunting areas'
    area_color_soil (stage\\m15d\\m15aNNd\\sdl\\m15aNNd-col, areas 1..10; layout as the Battlequarters' m19a03d-col,
    colour at +0xd0), as Tigerstripe's dunes_soil. GU has no area tint: one colour is baked in."""
    import ctr, efl4u2gu
    m19 = os.path.join(ROOT, 'dump/m19_unpacked/m19a03/stage/m19d/m19a03d/sdl/m19a03d-col.4c0db839')
    ref = open(m19, 'rb').read()
    names = re.findall(rb'[ -~]{4,}', ref)
    n, _ = ctr.main_ncch(efl4u2gu.ROM_4U)
    fs = n.romfs_reader()
    cols = []
    for a in range(1, 11):
        _, ents = arcpack.read(fs.read('/loc/data/m15a%02d.arc' % a))
        d = [d for p, t, d in ents if p == 'stage\\m15d\\m15a%02dd\\sdl\\m15a%02dd-col' % (a, a)][0]
        assert len(d) == len(ref) and re.findall(rb'[ -~]{4,}', d) == names, 'm15a%02dd-col layout' % a
        cols.append([round(255 * x) for x in struct.unpack_from('<4f', d, 0xd0)])
    soil = bytes(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(4))
    notes.append('effect area colour: Volcanic Hollow soil median %s (areas 1..10: %s)' % (tuple(soil), cols))
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


def psl_4u(gu, lmt4, lmt_gu, known, bank):
    """GU's PSL with 4U's slots in every motion GU gives no effect slot, whose 4U events name a record in `known` and
    whose GU frame count is 4U's: that entry's data becomes the 4U slots (kind EFX_KIND, 4U slot numbers) and 4U's runs
    (efl4u2gu build_psl's rules: GU's runs total frames - 1); every other entry stays GU's. GU's file stays as it is:
    a replaced entry gets a new data block (and a new 16-byte entry where GU has none) appended at the end, its offsets patched (GU layout:
    'PSL\\0', u16 2, u16 n, n entry offsets; entry {u32 frames, u16 0, u8 32, u8 0, u32 data, u32 0..3 (meaning G; 0 in
    efl4u2gu's PSLs and ours)}; data {u32 slot mask, u16 id[32], u32 kind[32], u32 0[32], u32 runs, u32 run offset};
    runs {u32 event bits, u32 frames}). -> (bytes, replaced, retimed by GU (kept), with GU's effects (kept))"""
    import efl4u2gu
    out = bytearray(gu)
    assert out[:4] == b'PSL\0' and struct.unpack_from('<H', out, 4)[0] == 2
    n = struct.unpack_from('<H', out, 6)[0]
    ev4, evg = efl4u2gu.lmt_events(lmt4), efl4u2gu.lmt_events(lmt_gu)
    assert n <= len(evg), ('PSL / motion list sizes', bank)         # GU's bank 0: 120 motions, PSL 105
    replaced, retimed, shared = [], [], []
    for e in ev4:
        if not e or not e[2]: continue
        i, frames4, remap, evs4 = e
        mine = [(k, r) for k, r in enumerate(remap) if r and r in known]     # 0 = an empty slot (em040_0 has an id 0)
        if not mine: continue
        g = struct.unpack_from('<I', gu, 8 + 4 * i)[0] if i < n else 0
        if g and struct.unpack_from('<I', gu, struct.unpack_from('<I', gu, g + 8)[0])[0]:
            shared.append(i); continue           # GU's Gravios plays effects in it: GU's stay
        frames = evg[i][1] if evg[i] else None
        if frames != frames4 or i >= n:          # GU retimed it, or GU's PSL ends before it (bank 3: 123 motions, 122)
            retimed.append(i); continue
        o = struct.unpack_from('<I', out, 8 + 4 * i)[0]
        if o:
            assert struct.unpack_from('<IHBB', out, o) == (frames, 0, 32, 0), ('PSL entry', bank, i)
        mask, ids, kinds = 0, [0] * 32, [0] * 32
        for k, r in mine:
            mask |= 1 << k; ids[k] = r; kinds[k] = EFX_KIND
        per = [b & mask for b, f in evs4 for _ in range(f)][:frames - 1]          # GU's runs end one frame earlier
        assert len(per) == frames - 1, ('4U runs', bank, i)
        psl_put(out, i, frames, mask, ids, kinds, per)
        replaced.append(i)
    return bytes(out), replaced, retimed, shared


def psl_put(out, i, frames, mask, ids, kinds, per):
    """entry i of the PSL bytearray out -> a new data block (slot mask, ids, kinds, per-frame bits `per`, frames - 1
    of them) appended at the end; a new 16-byte entry where the file has none (psl_4u's layout)"""
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


def roar_record(gu_pel_c):
    """the roars of bank 0 get GU's own air effect on the head for 4U's length (PR #12 point 3; user 2026-11-02: GU's
    look, not 4U's). GU em005_00 plays its roar air (PEL c id 90 = cm202_050, a screen blur) on no joint for 18 / 20
    frames; 4U pulses qe013_004 on joint 3 (the head) through the roar (em040_0 id 17). GU's own monsters that put it
    on the head (Tigrex em007_00 and others: joint 3 / 4, up to 200 frames) use the same record with the joint set
    (em007_00's id 90 = em005_00's but +0x32 = 3, C). -> GU's record with joint ROAR_JOINT as PEL u list-1 id ROAR_ID"""
    import efl4u2gu
    body = efl4u2gu.pel_lists(gu_pel_c)[1][1]
    rec, i = None, 0
    while i < len(body):
        L = body[i]
        if struct.unpack_from('<H', body, i + 1 + L + 2 + 0x30)[0] == 90:
            assert body[i + 1:i + 1 + L] == b'effect\\cm\\cm202_050', 'GU em005_00c id 90 is not the roar air'
            rec = bytearray(body[i:i + 1 + L + 2 + 160])
            struct.pack_into('<Hh', rec, 1 + L + 2 + 0x30, ROAR_ID, ROAR_JOINT)
        i += 1 + L + 2 + 160
    assert rec, 'GU em005_00c has no id 90'
    return bytes(rec)


def roar_head(psl, lmt4, notes):
    """bank 0 PSL: in ROAR_MOTIONS GU's air slot (PEL c id 90) becomes roar_record, on from GU's first frame of its
    air to 4U's last id-17 pulse; GU's other slots of the motion stay as they are"""
    import efl4u2gu
    ev4 = {e[0]: e for e in efl4u2gu.lmt_events(lmt4) if e}
    out = bytearray(psl)
    for m in ROAR_MOTIONS:
        o = struct.unpack_from('<I', out, 8 + 4 * m)[0]
        frames, _, _, _, da, _ = struct.unpack_from('<IHBBII', out, o)
        mask = struct.unpack_from('<I', out, da)[0]
        ids = list(struct.unpack_from('<32H', out, da + 4))
        kinds = list(struct.unpack_from('<32I', out, da + 68))
        assert not any(struct.unpack_from('<32I', out, da + 196)), ('GU roar entry rest', m)
        nr, ra = struct.unpack_from('<II', out, da + 0x144)
        per = [b for k in range(nr) for b, f in [struct.unpack_from('<II', out, ra + 8 * k)] for _ in range(f)]
        air = [k for k in range(32) if mask >> k & 1 and (ids[k], kinds[k]) == (90, 3)]
        assert len(air) == 1, ('GU roar slot', m)
        k = air[0]
        start = min(x for x, b in enumerate(per) if b >> k & 1)
        gu_end = max(x for x, b in enumerate(per) if b >> k & 1)
        _, frames4, remap, evs4 = ev4[m]
        assert frames4 == frames and 17 in remap, ('4U roar', m)
        k17 = remap.index(17)
        per4 = [b for b, f in evs4 for _ in range(f)]
        end = max(x for x, b in enumerate(per4) if b >> k17 & 1)
        ids[k], kinds[k] = ROAR_ID, EFX_KIND
        per = [(b & ~(1 << k)) | (int(start <= x <= end) << k) for x, b in enumerate(per)]
        psl_put(out, m, frames, mask, ids, kinds, per)
        notes.append('roar: bank 0 motion %d slot %d: GU\'s air (cm202_050) on joint %d, frames %d..%d (GU: no joint, '
                     '%d..%d)' % (m, k, ROAR_JOINT, start, end, start, gu_end))
    return bytes(out)


def effects(S, gfile, notes):
    """his effects -> ([(path, type, data)], {field: (path, type)}): see above"""
    import efl4u2gu
    T4 = efl4u2gu.T
    gravios = efl4u2gu.mef_records(S[(MEF_4U, T4['MEF'])])
    own = efl4u2gu.mef_records(S[(MEF_OWN, T4['MEF'])])
    assert {r['grp'] for r in own} <= {40, 41}, 'em041_1 names another EFL group'
    # the 4U condition bits (MEF byte 0, 4U 0x391a7c): module/em005_01_fx.c gates the posts by its table
    fx_c = open(os.path.join(MON, 'module', 'em005_01_fx.c')).read()
    table = re.search(r's_b0\[\] = \{(.*?)\};', fx_c, re.S).group(1)
    assert [tuple(map(int, t)) for t in re.findall(r'\{(\d+), (\d+)\}', table)] == \
        [(r['id'], r['b0']) for r in gravios + own if r['b0']], 'module/em005_01_fx.c s_b0 differs from the MEFs'
    gu_lists = efl4u2gu.pel_lists(gfile(17))
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef=MEF_4U, em_efl='effect\\efl\\em\\em041\\', groups=EFX_GROUPS,
                extra=[(EFX_GROUPS[r['grp']] % r['file'], r) for r in own], lmts=[], pel=PEL_U,
                soil=volcano_soil(notes), list2=gu_lists[2], hide_grey_models='chunks', extra2=CODE_FX)
    gu2 = set(pel_ids(gu_lists[2][1]))
    assert not {r['id'] for _, r in CODE_FX} & gu2, 'CODE_FX ids collide with GU\'s list 2'
    log = []
    out = efl4u2gu.effect_set(spec, log)
    for p, _ in CODE_FX:
        assert (p, T4['EFL']) in out, 'code-posted effect not shipped: ' + p
    mine_lists = efl4u2gu.pel_lists(out.pop((PEL_U, T4['PEL'])))
    mine, list2 = mine_lists[1], mine_lists[2]
    known = set(pel_ids(mine[1]))
    assert ROAR_ID not in known
    mine = (mine[0] + 1, mine[1] + roar_record(gfile(16)))
    gu1 = pel_ids(gu_lists[1][1])
    assert known and not known & set(gu1), 'PEL list-1 ids collide with GU\'s'       # list 2 is looked up apart
    assert gu_lists[0][0] == 0, 'GU em005_00u list 0 not empty'
    assert list2[0] == gu_lists[2][0] + len(CODE_FX) and list2[1].startswith(gu_lists[2][1]), 'PEL list 2 = GU + ours'
    pel = b'PEL\0' + struct.pack('<I', 15) + struct.pack('<I', 0) + \
        struct.pack('<I', gu_lists[1][0] + mine[0]) + gu_lists[1][1] + mine[1] + \
        struct.pack('<I', list2[0]) + list2[1]
    lists = efl4u2gu.pel_lists(pel)
    assert pel_ids(lists[1][1]) == gu1 + pel_ids(mine[1]) and lists[2] == list2, 'merged PEL u layout'
    ents = [(p, t, d) for (p, t), d in out.items()] + [(PEL_U, T4['PEL'], pel)]
    fields = {17: (PEL_U, T4['PEL'])}
    taken = 0
    for b in EFX_BANKS:
        psl, rep, ret, shared = psl_4u(gfile(18 + b), S[(P40 + 'mot\\em040_%d' % b, T4['LMT'])], gfile(4 + b), known, b)
        if b == 0:
            psl = roar_head(psl, S[(P40 + 'mot\\em040_0', T4['LMT'])], notes)
        taken += len(rep)                        # a bank without any stays our file (= GU's bytes): file IDs keep
        ents.append((PSL % b, T4['PSL'], psl))   # their order
        fields[18 + b] = (PSL % b, T4['PSL'])
        notes.append('PSL bank %d: 4U slots in motions %s (GU gives them no effect); GU\'s kept (GU\'s effects) %s; '
                     'retimed by GU %s' % (b, rep, shared, ret))
    assert taken, 'no motion takes 4U effects'
    notes.append('effects: PEL u = GU em005_00u (list 1: %d, list 2: %d) + 4U em041_1 records (%d) + code records %s '
                 '(list 2); %d converted 4U files' % (gu_lists[1][0], gu_lists[2][0], len(known),
                                                     [r['id'] for _, r in CODE_FX], len(out)))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return ents, fields


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
    typ = ghash[fileid_entry(img, gman[37])][1]
    ents.append(('enemy\\cmd_tbl\\em005_01_cmdtbl', typ, cmdtbl(S[(P40 + 'data\\em040_cmd', typ)], gfile(37), img,
                                                                 notes)))
    own[37] = ('enemy\\cmd_tbl\\em005_01_cmdtbl', typ)
    files, fields = effects(S, gfile, notes)
    ents += files
    own.update(fields)
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
