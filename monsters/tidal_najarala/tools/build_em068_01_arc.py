"""build_em068_01_arc.py : build nativeNX/arc/enemy/em068_01.arc (Tidal Najarala = GU Najarala variant 1, ID 0x144) + its data file
section FILE.

  build_em068_01_arc.py      build, verify, then write (paths in monsters/tidal_najarala/):
      romfs/nativeNX/arc/enemy/em068_01.arc
      tools/em068_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em001_02.arc): the variant's own files under enemy\\em068\\em068_01\\..., the files it shares with
variant 0 under em068_00's paths and file IDs. GU's class uEm068_00 runs it (variant byte 1, notes/plan.md: GU kept 4U's tests of her as
variant tests in its handlers).
  own, converted from MH4U em093.arc:
      mod\\em068_01 MOD + MRL        tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py)
      mod\\em068_01_NN_BM (+A)       albedo textures (BC3) + GU specular maps made from their alpha
      mod\\em068_01 XFS              GU em068_00's parts states, kept for em093's mesh groups
      mot\\em068_01_0/2/3/4          her 4U motion lists (LMT 67, unchanged; bank 4 = her two own animations 0x402 / 0x403, which GU's
                                     handler asks for), slots she lacks filled from GU's (FILL: GU's class may ask for them)
      cmd_tbl\\em068_01_cmdtbl       4U em023_cmd for em 93 in GU's language (cmdtbl())
      effects                        tools/efl4u2gu.py effect_set: her EFLs (+ the qe families her MEF names) under their 4U paths, PEL u
                                     list 1 from em093_0 + em093_1, list 2 = GU em068_00u's with the shell effects on hers, a PSL per
                                     motion list; area colour = the Frozen Seaway's (her 4U quests' stage 4)
      sound call / waves / bank / request   tools/snd4u2gu.py monster_entries
      dt_tune\\em068_01_dttune       GU em068_00's + the bytes where tools/dt_convert.py gives em093 != em023 (Tigerstripe's rule: GU's retunes
                                     of 4U Najarala and her differences do not overlap, asserted): HP, hitzones, parts on GU's balance
      hagi\\hagi_s0..s4_em068_01     carves: 4U G body / shiny tables in s4, GU's filler in s0..s3 (tools/hagi_em068_01.py)
      area_link / area_eat / map_info / area_select   GU em068_00's + map 14 (the Frozen Seaway, not a GU Najarala map) from her 4U data
                                     and GU's stage (tools/routes_em068_01.py)
  her data in GU's shell families (under GU's paths, as Tigerstripe's; no quest has both monsters, C): em068_00_shell36 = the scales, 4U
      uShell015, with her launches as more kinds (shell_data), her hit record and effects; em068_00_shell01 = the blasts, her 4U uShell003 record.
  shared, GU em068_00 (original paths + file IDs): camera (4U's is one file for em 23 / 93), sound triggers (PTS), PEL c, attack data, hitsize,
      bodydata, cambodydata, dtbase, dtbparts, area_patrol (GU's Najarala and Zinogre have none on their maps, C): 4U em023 and em093 convert to the same attack / hit / body /
      dtbase data (C), so GU's own tuning of them stays.
Inputs besides the arcs: dump/converted/em093/dt_em023/ and dt_em093/ (build.py step dt) and the 4U ROM (core effect arcs, area colours).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, ctr, efl4u2gu, emc, emdata4u, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, snd4u2gu, tex

NAME = 'tidal_najarala'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em093.arc')
GU_ARC = '/nativeNX/arc/enemy/em068_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em068_01.arc')
OUT_JSON = os.path.join(HERE, 'em068_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02)
P4 = 'enemy\\em093\\'            # 4U paths
P0 = 'enemy\\em068\\em068_00\\'  # GU variant 0
P = 'enemy\\em068\\em068_01\\'   # ours
BANKS = (0, 2, 3, 4)             # her motion lists: manifest field 4 + bank (GU's has 0, 2, 3)
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 3, 4, 6, 7, 8, 37, 17, 18, 20, 21, 22, 12, 13, 33, 46, 47, 48, 49, 50, 40, 42, 43, 41]
DT_DIR = os.path.join(ROOT, 'dump/converted/em093')           # build.py step dt
PEL_U = 'effect\\pel\\em\\em068_01u'
PEL_GU = 'effect\\pel\\em\\em068_00u'
PSL = 'effect\\psl\\enemy\\em068\\em068_01\\mot\\em068_01_%d'
MEFS = ('effect\\mef\\em\\em093_0', 'effect\\mef\\em\\em093_1')
# 4U group 50 (material 'XfBA1__m02_Virs': her frenzy veins, 4U shows them only under the frenzy virus) is not in GU's model, so no GU state
# names it: hidden in the base state, as Tigerstripe's group 50.
HIDDEN_GROUPS = (50,)
BASE_STATES = (0, 15)            # GU's slot 132 applies one of them every frame, with no variant test (C: 0xf89c74, 15 under a condition, else 0): hidden in both
GU_RS ={a for _, (a, _) in mrl.records(0x22).items() if a and a.startswith('RS')}     # GU's rasterizer states


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def textures(S, r4, slots, out, gu_tex):
    """the GU texture paths of one 4U material's albedo: BC3 + its '+A' specular map (the BM alpha in R, G, B, alpha 255; 4U specular mask)"""
    paths_of = {}
    for slot, v in slots.items():
        if not v: continue
        src = r4['textures'][v - 1][1]
        name = src.split('\\')[-1]
        if src not in gu_tex:
            t = tex.decode(S[(src, T['TEX'])])
            path = P + 'mod\\em068_01_' + name.split('em093_')[-1]
            s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
            out += [(path, T['TEX'], tex.encode_gu(t, 'bc3')), (path + '+A', T['TEX'], tex.encode_gu(s, 'bc3'))]
            gu_tex[src] = path
        paths_of[slot] = gu_tex[src]
        if slot == 'tAlbedoMap':
            paths_of['tSpecularMap'] = gu_tex[src] + '+A'
    return paths_of


def model(S, rom, gu_tex, notes):
    """em093 MOD + MRL (+ textures) -> [(path, type, data)], the parsed 4U MOD. Templates (Monoblos' rules + Tigerstripe's sphere map): additive ->
    'add', 4U BSBlendAlpha -> 'blend' with the material's own constants, emissive -> 'unlit', a lit E0 material with a tExtendMap -> 'solid_sphere',
    alpha-tested -> 'solid_at', else 'solid'. Every 4U material animation is converted. MRL before MOD, as in GU's arcs."""
    src = P4 + 'mod\\em093'
    d4, d4m = S[(src, T['MOD'])], S[(src, T['MRL'])]
    m4, r4 = modlib.parse(d4), mrl.read(d4m)
    anims4 = mrl_anim.material_anims(d4m, struct.pack('<I', 15))[1]     # the file stops before its last key's frame: 15, as every other key
    out, tex_paths, tex_index, mats = [], [], {}, []
    for mname in m4['material_names']:
        mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
        assert len(mm) == 1, mname
        mm = mm[0]
        states = [s for s in mm['states'] if s]
        gp = textures(S, r4, {n: v for n, _, v in mm['params'] if n == 'tAlbedoMap'}, out, gu_tex)
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
                path = P + 'mod\\em068_01_' + ext_tex.split('em093_')[-1]
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
        if ents4:
            std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
            anim_vars = mrl_anim.animated_targets(ents4)
            consts.update({k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], 1.0).items() if k in anim_vars})
            extra['anim'] = mrl_anim.build(mrl_anim.gu_entries(ents4, mrl_build.cb_words(rom, key)))
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
    out += [(P + 'mod\\em068_01', T['MRL'], mrl_bytes), (P + 'mod\\em068_01', T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(gu_xfs, groups, notes):
    """GU em068_00's parts states (rMonsterPartsManager XFS) for em093's mesh groups"""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    unnamed = sorted(set(groups) - {g for st in states for g, _ in st} - set(HIDDEN_GROUPS))
    assert not unnamed, 'em093 groups without a GU state: %s' % unnamed
    for k in BASE_STATES:
        assert (0, 1) in kept[k], ('not a base state', k)
        kept[k] += [(g, 0) for g in HIDDEN_GROUPS if g in groups]
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted({g for st in states for g, _ in st} - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in em093): %s, hidden at spawn: %s' % (len(kept), dropped, list(HIDDEN_GROUPS)))
    return bytes(head) + data


def skeleton_check(gu_mod, our_mod, notes):
    """GU's class and the shared camera / data drive our model: the same bone ids, parents and bind positions (C)"""
    def by_id(m):
        bl = m['bone_list']
        return {b['index']: (bl[b['parent']]['index'] if b['parent'] != 255 else None, b['pos']) for b in bl}
    g, o = by_id(modlib.parse(gu_mod)), by_id(modlib.parse(our_mod))
    assert set(g) == set(o) and all(g[k][0] == o[k][0] for k in g), 'em093 skeleton differs from GU em068_00\'s'
    far = max((max(abs(a - b) for a, b in zip(g[k][1], o[k][1])), k) for k in g)
    notes.append('skeleton: %d bones equal to GU em068_00\'s; largest bind position difference %.1f (bone %d)' % (len(o), *far))


def motion_bank(S, gfile, b, notes):
    """her 4U list b, the motions she shares with GU's list in GU's form, with the slots only GU's list has (GU's class may ask for them: GU's code for them has no variant test
    everywhere). Her banks 0, 2, 3 are 4U em023's animations track for track (C, 2026-11-06: only her list 4 is her own), and GU em068_00 holds the same animations on the same
    skeleton (skeleton_check) stored finer: rotation 11 / 9 bits against 4U's 7, bone 0 position 16 against 8. So GU's tracks, the user's rule ("Wenn es in MHGU schon Animationen
    geben sollte ... kannst du aus MHGU nehmen"), and her 4U event blocks stay: sound and effect timing, her PSLs come from them (spec lmts reads S). The user's test of 0.2.1 showed
    hitches on her body that the log could not place on the game's frame time (notes/plan.md)."""
    d = S[(P4 + 'mot\\em093_%d' % b, T['LMT'])]
    if b == 4: return d
    gu = gfile(4 + b)
    ga, oa = lmt.anims(gu), lmt.anims(d)
    assert len(ga) >= len(oa), ('bank longer than GU\'s', b)
    frames = lambda x, o: struct.unpack_from('<I', x, o + 8)[0]
    for i, o in enumerate(oa):
        if o and ga[i]: assert frames(d, o) == frames(gu, ga[i]), ('bank slot frames differ', b, i)
    swap = [(i, i) for i, o in enumerate(oa) if o and ga[i]]
    size4 = len(d)
    d = lmt.with_tracks(d, gu, swap)
    notes.append('motions bank %d: GU\'s tracks in %d slots, her event blocks kept; %d slots stay 4U\'s; file %d B -> %d B' % (b, len(swap), sum(1 for o in oa if o) - len(swap), size4, len(d)))
    fill = [(i, i) for i, o in enumerate(ga) if o and i < len(oa) and not oa[i]]
    past = [i for i, o in enumerate(ga) if o and i >= len(oa)]
    if past:                                       # 4U's em 23 motions past her table: only Najarala's own paths ask for them (C: motion ffff else)
        notes.append('motions bank %d: GU slots %s lie past her table of %d: left out' % (b, past, len(oa)))
    if not fill: return d
    out = lmt.splice(d, gu, fill)
    notes.append('motions bank %d: her 4U list + GU\'s animations in the slots she lacks %s' % (b, [i for i, _ in fill]))
    return out


# ---- AI table (notes/plan.md "AI table"). 4U em023_cmd serves em 23, 93 and (group 21) em 120: their differences are EMC op 0x46 blocks, a switch on
# the em number; GU's table kept those blocks as its op 0x92 (variant switch; asserted: GU's variant-1 bodies = 4U's case-93 bodies). Our table serves her
# only, so each block is reduced to her body. GU's language replaces 4U's where the engine needs it: EMC_GU = the area move g0 s0 / s9, patrol g0 s1, g1 s16 / s48 /
# s72 (GU's stage numbers and rest), g20 s0; group 16 = GU's (4U's rest group, which GU never selects, Black Gravios' check; 1/23 .. 1/27, GU has no handler, sit
# only in it and in 4U's group 21); g0 s14 / s15 = GU's, which are 4U's without the op-0x91 block (4U: if W+0x7e80 & 32 = the Apex state, C: her else body); g0 s18:
# 4U's with its stage case in GU's number (4U 4 -> GU 14). GU's extra entries are appended: g1 s83.. (GU's class picks group-1 scripts by number, area_act_tbl 83..90).
# g0 s2 / s6 / g12 s0 / g13 s0 keep her 4U bodies (GU's Najarala retunes and its extra selector, a deviation only from GU).
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_GU = {(0, 0), (0, 1), (0, 9), (0, 14), (0, 15), (1, 16), (1, 48), (1, 72), (20, 0)}
EMC_GU_GROUPS = (16,)
EMC_4U_ONLY = {0x03, 0x06, 0x07, 0x22, 0x2a, 0x36, 0x40, 0x41, 0x46, 0x49, 0x4a, 0x4d, 0x63, 0x8b, 0x91}
STAGE_CASE = {4: 14}             # 4U Frozen Seaway -> GU stage in a kept `2a 01 NN` case


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


def stage_cases(s, lens):
    """4U `2a 01 NN` stage cases of a kept script -> GU's numbers"""
    out = []
    for t in emc_tokens(s, lens):
        if t[0] == 0x2a and t[1] == 1:
            assert t[2] in STAGE_CASE, ('4U stage case without a GU number', t.hex())
            t = bytes([0x2a, 1, STAGE_CASE[t[2]]])
        out.append(t)
    return b''.join(out)


def cmdtbl(d4, gu, img, notes):
    """4U em023_cmd for em 93 in GU's language (see above) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[22], 'EMC group layout changed'
    ops = lambda s: {t[0] for t in emc_tokens(s, lens)}
    out, own, same = [], [], []
    for gi in range(21):
        if gi in EMC_GU_GROUPS:
            out.append([emc_em_only(x, 1, lens, 0x92) for x in g[gi]]); continue
        scripts = []
        for k, s in enumerate(u4[gi]):
            gv = emc_em_only(g[gi][k], 1, lens, 0x92) if k < len(g[gi]) else None
            if (gi, k) in EMC_GU:
                scripts.append(gv); continue
            mine = emc_em_only(s, 93, lens)
            if any(t[0] == 0x92 for t in emc_tokens(g[gi][k], lens)):
                if mine == gv: same.append((gi, k))
                else: own.append((gi, k))
            if (gi, k) == (0, 18):
                mine = stage_cases(mine, lens)
            assert not ops(mine) & (EMC_4U_ONLY - {0x07, 0x2a, 0x36, 0x40, 0x4d, 0x06, 0x22, 0x63, 0x41, 0x4a, 0x03, 0x49, 0x8b}), ('switch op left', gi, k)
            scripts.append(mine)
        assert len(scripts) <= len(g[gi]), gi
        out.append(scripts + [emc_em_only(x, 1, lens, 0x92) for x in g[gi][len(scripts):]])
    gu_v1 = [[emc_em_only(x, 1, lens, 0x92) for x in gr] for gr in g]
    stray = {(gi, k): sorted(ops(s) & EMC_4U_ONLY) for gi, gr in enumerate(out) for k, s in enumerate(gr)
             if ops(s) & EMC_4U_ONLY and s != gu_v1[gi][k] and (gi, k) != (0, 18)}
    assert not stray, ('4U area op in a script GU does not have that way', stray)
    # scripts GU's taken / appended ones call stay GU's where GU has its own
    loose = sorted({t[1] for gi, k in sorted(EMC_GU) + [(1, k) for k in range(len(u4[1]), len(g[1]))] for t in emc_tokens(gu_v1[gi][k], lens)
                    if t[0] == 0x14 and out[1][t[1]] != gu_v1[1][t[1]]})
    assert [len(x) for x in out] == [len(x) for x in g], 'our table must carry every GU entry number'
    notes.append('AI table: 4U em023_cmd for em 93; GU\'s %s; GU\'s group %s; g0 s18 with GU stage numbers; GU extra entries appended (%s); scripts with her '
                 'own bodies: GU\'s variant-1 body equal in %s, different in %s; GU scripts calling her differing scripts: %s' % (
                     sorted(EMC_GU), list(EMC_GU_GROUPS), ['g%d s%d..s%d' % (gi, len(u4[gi]), len(g[gi]) - 1) for gi in range(21) if len(g[gi]) > len(u4[gi])],
                     same, own, loose))
    return emc.build(out, ver)


# ---- shells (notes/plan.md "Shells"). GU's uShellEm068_sp_36 (id 0x126) = 4U uShell015, data-driven: per kind a ShellInfo in the family's def (ef / snd / hit / sh
# files). Its sh file: ints (2, 3, pair index, mode -1 ballistic), floats yaw (degrees), speed, offset, velocity, acceleration. GU's kinds 0..8 = 4U's kinds 0..8 (the
# same launch numbers, C), GU's 9 / 10 = 4U's 19 / 20, Najarala's aimed scales. Her 4U kinds are other launches:
#   kind  4U launch (kind, param)   offset  her action
#   9/10  (9, 0) / (10, 0)          OFF1 / OFF2  7/3 (GU's f7d634 cases 4, 5: data only)
#   11/12 (9, 2) / (10, 2)          OFF1 / OFF2  7/60 (module em068_01.c)
#   13/14 (9, 3) / (10, 3)          OFF1 / OFF2  7/61
#   15/16 (13, 0) / (14, 0)         default      7/57 (start hook)
#   17/18 (15, 0) / (16, 0)         default      7/59
#   19/20 (9, 0) / (10, 0)          OFF3         7/25
# (9, 0) / (10, 0) at the default offset = GU's kinds 0 / 1 (7/45, 7/47), 4U's 11 / 12 = GU's 2 / 3 (7/53, 7/55) (C: the 4U init values).
FAM36, FAM01 = 'shell\\em\\em068_00_shell36\\em068_00_36', 'shell\\em\\em068_00_shell01\\em068_00_01'
HDS_T, HTS_T, SHELL_DEF_T = 0x4EB68CEE, 0x5653C1B0, 0x4AA69872
OFF1, OFF2, OFF3 = (407.6, 226.0, 638.9), (-179.0, 429.0, 1211.0), (-289.4, 213.8, 596.6)    # 4U 0x763af0 0x763b04 0x7652dc
DEG = lambda a: (a - 0x10000 if a >= 0x8000 else a) * 360.0 / 65536.0
KINDS = {9: (OFF1, (0.0, -8.0, 43.5), -0.1, 728, 0), 10: (OFF2, (0.0, -8.0, 42.5), -0.1, 0x16c1, 1),
         11: (OFF1, (35.0, -8.0, 30.0), -0.08, 0xb8e5, 0), 12: (OFF2, (20.0, -12.0, 10.0), -0.15, 0xf8e5, 1),
         13: (OFF1, (55.0, -3.0, 25.0), -0.08, 0xc001, 0), 14: (OFF2, (35.0, -9.0, 15.0), -0.1, 0xe71d, 1),
         15: (None, (30.0, -8.0, 20.0), -0.1, 49152, 0), 16: (None, (30.0, -8.0, 20.0), -0.1, 0, 1),
         17: (None, (0.0, -8.0, 53.0), -0.005, 728, 0), 18: (None, (0.0, -8.0, 53.0), -0.005, 0xeef, 1),
         19: (OFF3, (0.0, -8.0, 43.5), -0.1, 728, 0), 20: (OFF3, (0.0, -8.0, 42.5), -0.1, 0x16c1, 1)}
N_KINDS = 21
U015_REC, U003_REC = 0x102a9c0, 0x101f230      # 4U attack records, 40 B: uShell015 0 / 5, uShell003 64 / 157
U003_VOL = 0x101efbc
# Her water jet (module/em068_01_jet.c, notes/plan.md "The water jet"): 4U uShell012 subtypes 52 / 53 (record table 0x10290b0: 36, its volume byte 16), which GU has no
# class for. HDS entry 3 and HTS group 3 of family shell01 (GU's 3 entries stay): HDS_JET in the module. Effects (table 0x1027488 / 0x10278d8: (69, 12) and (69, 13), mask
# -1) are code posts in PEL list 2: EFX_JET_* in the module.
U012_VOL, U012_REC = 0x1028904, 0x1028904 + 84
JET_RECORD, JET_VOLUME, JET_HDS = 36, 16, 3
GU_HDS_1C = 6                                  # the rule of the earlier ports for 4U's byte 0x1c = 0 (stygian build_em057_01_arc.py hds_rule)
JET_FX = ((3300, 'em093_019', True), (3301, 'em093_020', False))   # (id, EFL, follows its unit)
EFL_TABLE_4U = 0xef895c
# PEL list 2 by path: GU's shell effects -> hers. 4U table 0x102a938, {u8 group, u8 element} by +0x2f4 state, 8 per species (C): Najarala 0 flight em023_000, 2 planted em023_001, 4 rattle
# em023_014, 6 blast em023_002, 7 gone em023_004; Tidal 0 em093_030, 2 em093_031, 4 and 6 none, 7 em093_004. GU's 000 / 001 / 004 are Najarala's flight / planted / gone. GU's 012 / 002
# (rattle, blast) cannot come up for her alone (no action of hers sends the signal, em068_01.c): the gone effect, not a scale model. Until 0.2.1 004 stood on em093_031: a scale that was
# hit or ran out drew a new whole scale ("they do not really break", test 2026-11-06).
SHELL_FX = {'em068_00_000': 'effect\\efl\\em\\em093\\em093_030', 'em068_00_001': 'effect\\efl\\em\\em093\\em093_031',
            'em068_00_004': 'effect\\efl\\em\\em093\\em093_004', 'em068_00_012': 'effect\\efl\\em\\em093\\em093_004',
            'em068_00_002': 'effect\\efl\\em\\em093\\em093_004'}
# her scale model: Capcom's conversion of its 4U sibling, em023_tuning (24 vertices, the same material) -> em068_00_001: GU's material with her texture. mrl_build template key:
SCALE_MODEL, SCALE_TEMPLATE = 'effect\\base\\em\\em093\\em093_tuning', 'efx_em068_scale'
mrl_build.TEMPLATES.setdefault(SCALE_TEMPLATE, (GU_ARC, 'effect\\base\\em068_00_001', 0))
# colourless 4U solid effect meshes: vertex RGB 127 = 1.0 (efl4u2gu convert_effect_mod); white drew them at 2x
SOLID_FILL = (127, 127, 127, 255)
# the family's rank table (FUP em068_00_36, floats from +24): hits low rank, hits G rank, flight, life, end time, rattle delay low, rattle delay G. 4U 0xc681bc: +0x2ac = 1, 2 only for em 23
# at G rank (0xc681d8): GU's table is Najarala's
FAM_HITS_G = 28
# each kind's ef file = {list, id}: flight, 2nd flight, planted, gone, (none), rattle, gone (C: f8bce4 reads them by index 0 1 3 2 4 5 6). GU posts both flight records with masks 1 and 2. In 4U
# mask 2 comes only with W+0x53a or the Apex bit (0xc68b90: +0x2f0, 0x76145c; S: W+0x53a = frenzy, which GU does not have): her em093_030 mask 2 drew over the plain scale ("glow blue"). No 2nd flight post for her.
EF_ID0, EF_STEP = 533 - 5 * 24, 24
EF_IDS = (0, 3, 2, 1, -1, 30, 2)


def code_4u():
    return open(os.path.join(ROOT, 'dump/exefs_v11/code.bin'), 'rb').read(), 0x100000


def hds_entry(r4, b1c, group):
    """a 4U 40-B attack record -> a GU 56-B HDS entry (tools: gogmazios shell_hds, tigerstripe hds_entry)"""
    r = bytearray(56)
    r[0:0x24] = r4[0:0x24]
    r[0x12] = r4[0x12] & 3
    r[0x1c] = b1c
    struct.pack_into('<f', r, 0x28, 1.0)
    r[0x2c] = r4[0x12] >> 2
    r[0x19] = group
    return bytes(r)


def extend_def(d, n_old, n_new):
    """the family def (XFS rShellInfo: ShellInfoList = N objects {ShellScale, EffectParam, SoundParam, HitParam, ShellParam}, each naming kind files by path) with n_new kinds:
    new objects are copies of kind 0's with their names and serials; the header's object count and the sizes of the root and list objects grow"""
    nobj = struct.unpack_from('<I', d, 8)[0]
    dsize = struct.unpack_from('<I', d, 0x14)[0]
    root = 0x18 + dsize
    tag, ser, rsize = struct.unpack_from('<HHI', d, root)
    assert ser == 0 and nobj == n_old + 2
    p = root + 8
    cnt = struct.unpack_from('<I', d, p)[0]; assert cnt == 1          # mQuality
    p += 4 + 4
    cnt = struct.unpack_from('<I', d, p)[0]; assert cnt == 1          # ShellInfoList
    p += 4
    list_at = p
    ltag, lser, lsize = struct.unpack_from('<HHI', d, p)
    assert lser == 1
    p += 8
    assert struct.unpack_from('<I', d, p)[0] == 1                      # mAutoDelete
    p += 5
    arr_at = p
    assert struct.unpack_from('<I', d, p)[0] == n_old
    p += 4
    objs = []
    q = p
    for k in range(n_old):
        t, s, z = struct.unpack_from('<HHI', d, q)
        assert s == 2 + k
        objs.append(d[q:q + 4 + z + 0])
        q += 4 + z
    # object = u16 tag, u16 serial, u32 size (4 + body bytes): the size counts from itself
    tail = d[q:]
    new = list(objs)
    for k in range(n_old, n_new):
        o = bytearray(objs[0])
        o = o.replace(b'_ef000', b'_ef%03d' % k).replace(b'_snd000', b'_snd%03d' % k).replace(b'_hit000', b'_hit%03d' % k).replace(b'_sh000', b'_sh%03d' % k)
        assert len(o) == len(objs[0])
        struct.pack_into('<H', o, 2, 2 + k)
        new.append(bytes(o))
    body = b''.join(new)
    grow = len(body) - sum(len(o) for o in objs)
    out = bytearray(d[:p]) + body + tail
    struct.pack_into('<I', out, 8, nobj + n_new - n_old)
    struct.pack_into('<I', out, arr_at, n_new)
    struct.pack_into('<I', out, list_at + 4, lsize + grow)
    struct.pack_into('<I', out, root + 4, rsize + grow)
    assert len(out) == len(d) + grow
    return bytes(out)


def sh_file(tpl, spec):
    """GU's sh FUP of a ballistic kind with her launch (offset None = GU's default)"""
    off, vel, acc, yaw, pair = spec
    d = bytearray(tpl)
    assert len(d) == 72 and struct.unpack_from('<i', d, 24)[0] == -1, 'GU sh000 no longer a ballistic kind'
    struct.pack_into('<I', d, 20, pair)                 # ints (2, 3, pair, -1) at +12, then floats
    struct.pack_into('<f', d, 28, DEG(yaw))
    if off: struct.pack_into('<3f', d, 36, *off)
    struct.pack_into('<3f', d, 48, *vel)
    struct.pack_into('<3f', d, 60, 0.0, acc, 0.0)
    return bytes(d)


def ef_file(d):
    """a kind's ef file without the 2nd flight post (EF_IDS): 0x4a1e50 skips an id below 0"""
    assert len(d) == 561 and tuple(struct.unpack_from('<i', d, EF_ID0 + EF_STEP * k)[0] for k in range(7)) == EF_IDS, 'GU ef file changed'
    d = bytearray(d)
    struct.pack_into('<i', d, EF_ID0 + EF_STEP, -1)
    return bytes(d)


def shell_data(gents, notes):
    """the kept GU entries with her scale / blast data"""
    code, base = code_4u()
    rec = lambda a, k: code[a + 40 * k - base:a + 40 * k + 40 - base]
    out = []
    F = {p: (t, d) for p, t, d in gents if p.startswith(FAM36) or p.startswith(FAM01)}
    # the 4U launches of GU's kinds 0..8 equal GU's sh files where the build can tell: the two the table reuses
    s0 = F[FAM36 + '_sh000'][1]
    assert struct.unpack_from('<3f', s0, 12 + 4 * 9) == (0.0, -8.0, 43.5) and abs(struct.unpack_from('<f', s0, 12 + 4 * 4)[0] - 4.0) < 0.01, 'GU sh000 is not 4U kind 0 / 9'
    for p, t, d in gents:
        if p == FAM36 + '_hitdata' and t == HDS_T:
            g0 = bytearray(d[16:72])
            assert hds_entry(rec(U015_REC, 0), g0[0x1c], g0[0x19]) == bytes(g0), 'GU scale entry 0 is not 4U uShell015 record 0 converted'
            d = bytearray(d)
            d[16:72] = hds_entry(rec(U015_REC, 5), g0[0x1c], g0[0x19])
            d = bytes(d)
            notes.append('shell36 HDS entry 0 = 4U uShell015 record 5 (hers; Najarala 0)')
        elif p == FAM01 + '_hitdata' and t == HDS_T:
            g2 = bytearray(d[16 + 56 * 2:16 + 56 * 3])
            r64 = rec(U003_REC, 64)
            e = hds_entry(r64, g2[0x1c], g2[0x19])
            diff = [i for i in range(56) if e[i] != g2[i]]
            notes.append('shell01 HDS entry 2: GU vs 4U uShell003 64 differ at %s' % diff)
            new = bytearray(hds_entry(rec(U003_REC, 157), g2[0x1c], g2[0x19]))
            for i in diff: new[i] = g2[i]          # GU's retune of the shared bytes stays
            new[0x0c:0x10] = rec(U003_REC, 157)[0x0c:0x10]
            d = bytearray(d)
            d[16 + 56 * 2:16 + 56 * 3] = new
            notes.append('shell01 HDS entry 2 = 4U uShell003 record 157 (her blast, water flags %s)' % new[0x0c:0x10].hex())
            jet = rec(U012_REC, JET_RECORD)
            assert jet[0x19] == JET_VOLUME and not any(jet[0x24:0x28]) and struct.unpack_from('<I', d, 8)[0] == JET_HDS and len(d) == 16 + 56 * JET_HDS, 'uShell012 record / GU family changed'
            d += hds_entry(jet, GU_HDS_1C, JET_HDS)
            struct.pack_into('<I', d, 8, JET_HDS + 1)
            d = bytes(d)
            notes.append('shell01 HDS entry %d = 4U uShell012 record %d (her water jet): power %d, type %d' % (JET_HDS, JET_RECORD, struct.unpack_from('<H', jet, 4)[0], jet[6]))
        elif p == FAM01 + '_hitsize' and t == HTS_T:
            off = struct.unpack_from('<I', d, 16 + 8 * 2 + 4)[0]
            d = bytearray(d)
            struct.pack_into('<f', d, off + 0x0c, 350.0)      # 4U volume 146 (GU's Najarala blast 450, 4U's 600)
            # group 3 = the jet's volume 16, by the rule of the earlier ports (4U 40 B + 8 zero bytes, +0x0a = GU's; its far end is 0, so no far-end question, notes/data.md)
            n = struct.unpack_from('<I', d, 8)[0]
            tab = [struct.unpack_from('<II', d, 16 + 8 * k) for k in range(n)]
            assert n == JET_HDS and all(c == 1 for c, _ in tab) and len(d) == 16 + 8 * n + 48 * n, 'GU shell01 HTS changed'
            recs = [bytes(d[o:o + 48]) for _, o in tab]
            vp = struct.unpack_from('<I', code, U012_VOL + 4 * JET_VOLUME - base)[0] - base
            v4 = code[vp:vp + 40]
            assert struct.unpack_from('<H', code, vp + 40)[0] == 0xFFFF and not any(v4[0x0a:0x0c]) and not any(v4[0x1c:0x28]), 'uShell012 volume 16 changed'
            vg = bytearray(48)
            vg[0:40] = v4
            vg[0x0a:0x0c] = recs[0][0x0a:0x0c]
            recs.append(bytes(vg))
            head = bytearray(d[:16])
            struct.pack_into('<I', head, 8, n + 1)
            d = bytes(head) + b''.join(struct.pack('<II', 1, 16 + 8 * (n + 1) + 48 * k) for k in range(n + 1)) + b''.join(recs)
            notes.append('shell01 HTS group %d = 4U uShell012 volume %d: bone %d radius %g' % (JET_HDS, JET_VOLUME, struct.unpack_from('<H', v4, 0)[0], struct.unpack_from('<f', v4, 0x0c)[0]))
        elif t == SHELL_DEF_T and p.startswith('shell\\em\\em068_00_shell'):
            assert d.count(PEL_GU.encode()) == 1, p
            d = d.replace(PEL_GU.encode(), PEL_U.encode())
            if p == FAM36:
                d = extend_def(d, 11, N_KINDS)
        elif p == FAM36 and t != SHELL_DEF_T:
            assert struct.unpack_from('<f', d, FAM_HITS_G - 4)[0] == 1.0 and struct.unpack_from('<f', d, FAM_HITS_G)[0] == 2.0, 'GU rank table changed'
            d = bytearray(d)
            struct.pack_into('<f', d, FAM_HITS_G, 1.0)
            d = bytes(d)
            notes.append('shell36: 1 hit at G rank too (4U: 2 only for em 23)')
        elif p.startswith(FAM36 + '_ef'):
            d = ef_file(d)
        out.append((p, t, d))
    # the new kinds' files: kind 0's ef / snd / hit, her sh; GU's 9 / 10 become her 7/3 launches. They go before the def: a def names its files by path and finds only what the arc has loaded
    # by then (test 2026-11-06: appended at the end of the arc, kinds 11.. had no effect, hit data or offset: invisible scales at her feet, "efx 0 0" in the log)
    new = []
    for k in range(11, N_KINDS):
        for what in ('ef', 'snd', 'hit'):
            t, d = F[FAM36 + '_%s000' % what]
            new.append((FAM36 + '_%s%03d' % (what, k), t, ef_file(d) if what == 'ef' else d))
        new.append((FAM36 + '_sh%03d' % k, F[FAM36 + '_sh000'][0], sh_file(s0, KINDS[k])))
    at = [i for i, (p, t, d) in enumerate(out) if p == FAM36 + '_hitdata'][0]
    assert at < [i for i, (p, t, d) in enumerate(out) if p == FAM36 and t == SHELL_DEF_T][0], 'family def before its files'
    out[at:at] = new
    for k in (9, 10):
        out = [(p, t, sh_file(s0, KINDS[k]) if p == FAM36 + '_sh%03d' % k else d) for p, t, d in out]
        for what in ('ef', 'snd', 'hit'):
            t0, d0 = F[FAM36 + '_%s000' % what]
            out = [(p, t, (ef_file(d0) if what == 'ef' else d0) if p == FAM36 + '_%s%03d' % (what, k) else d) for p, t, d in out]
    notes.append('shell36: %d kinds (GU 11): 9..20 = her launches %s' % (N_KINDS, sorted(KINDS)))
    return out


def shell_list2(list2):
    """GU PEL list 2 (count, record bytes) with the shell effects on hers (state bytes kept, as Tigerstripe's)"""
    n, body = list2
    out, i, hit = b'', 0, set()
    for _ in range(n):
        L = body[i]
        path = body[i + 1:i + 1 + L].decode('ascii')
        rest = body[i + 1 + L:i + 1 + L + 2 + 160]
        new = SHELL_FX.get(path.split('\\')[-1])
        if new: hit.add(path.split('\\')[-1])
        new = (new or path).encode('ascii')
        out += bytes([len(new)]) + new + rest
        i += 1 + L + 2 + 160
    assert i == len(body) and hit == set(SHELL_FX), ('PEL list 2 lacks', set(SHELL_FX) - hit)
    return n, out


def seaway_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Frozen Seaway (stage 4) areas' area_color_soil (layout as the Battlequarters' m19a03d-col, colour at
    +0xd0), Tigerstripe's dunes_soil rule. GU has no area tint: one colour is baked in."""
    m19 = os.path.join(ROOT, 'dump/m19_unpacked/m19a03/stage/m19d/m19a03d/sdl/m19a03d-col.4c0db839')
    ref = open(m19, 'rb').read()
    names = re.findall(rb'[ -~]{4,}', ref)
    n, _ = ctr.main_ncch(efl4u2gu.ROM_4U)
    fs = n.romfs_reader()
    cols = []
    for a in range(1, 13):
        try:
            _, ents = arcpack.read(fs.read('/loc/data/m04a%02d.arc' % a))
        except Exception:
            continue
        d = [d for p, t, d in ents if p == 'stage\\m04d\\m04a%02dd\\sdl\\m04a%02dd-col' % (a, a)]
        if not d: continue
        assert len(d[0]) == len(ref) and re.findall(rb'[ -~]{4,}', d[0]) == names, 'm04a%02dd-col layout' % a
        cols.append([round(255 * x) for x in struct.unpack_from('<4f', d[0], 0xd0)])
    assert cols, 'no 4U stage-4 area colours'
    soil = bytes(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(4))
    notes.append('effect area colour: Frozen Seaway soil median %s (%d areas)' % (tuple(soil), len(cols)))
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


# The user's rule (2026-11-06): where an animation is the same as GU's, GU's effects, as with the roar. Her banks and GU's have equal frames in every shared slot (motion_bank), so
# GU's slots fit. GU's common effects (PEL c, kind 3, its cm* files: air, dust, spray) go into her entry and replace her 4U common effects (kind 4, qe*: 4U's dust) there. Her own
# em093_* effects stay, they are what makes her Tidal; GU's Najarala-only slots (em068_*, em077_*) do not come. Where GU's motion has no common effect, hers stay as they are. 4U's
# roar blur (0xc0819c, code) has no EFL: GU's air effect stands for it. A DEVIATION from 4U, wanted.
def gu_common_effects(psl, gu_psl, her_u, gu_c, bank, notes):
    out = bytearray(psl)
    done = 0
    for i in range(min(struct.unpack_from('<H', gu_psl, 6)[0], struct.unpack_from('<H', psl, 6)[0])):    # GU's slots past her table: motion_bank
        g = psl_entry(gu_psl, i)
        if not g: continue
        gf, gmask, gids, gkinds, gper = g
        add = [k for k in range(32) if gmask >> k & 1 and gkinds[k] == 3 and gu_c.get(gids[k], '').startswith('cm')]
        if not add: continue
        e = psl_entry(out, i)
        f, mask, ids, kinds, per = e if e else (gf, 0, [0] * 32, [0] * 32, [0] * (gf - 1))
        assert f == gf, ('her motion and GU\'s differ in frames', bank, i, f, gf)
        for k in range(32):
            if mask >> k & 1 and kinds[k] == 4 and not her_u.get(ids[k], 'em093').startswith('em093'):
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
    notes.append('effects bank %d: GU\'s common effects in %d motions' % (bank, done))
    return bytes(out)


# Her snow dust (em093_003 on 21 records, nearly every move; user's test 2026-11-06: "die fehlen noch"). 4U (C): the motion post 0x391b50 copies the MEF flags into the effect; ground flag
# (bit 1 -> +0x274 bit 0): every frame x, z = the joint + the record offset turned by her angles, y = her ground (0xc4838c.., 0xc49a84: W+0x624). GU's records have no such tail, and
# PEL_TAIL places them at the joint: inside her body, at its height. So these records become world records and module/em068_01_fx.c (hook on the PSL post) names the point: the joint's x, z
# at the post, her ground y (rec+0x5b4). A DEVIATION: the point does not ride the joint over the effect's short life. It also scales by her size (MEF bit 5, 4U 0xc47f98) and picks the
# ground set. Slot mode 1 (0x391f00..): 4U ends the effect when the event range ends; in GU that is end mode 1 (+0x3a, Dalamadur's pel_slot_end has the code reading).
#
# Her snow itself is GU's since 0.2.3 (the user, 2026-11-06, after seeing 4U's on the ground: positions good, "schauen ob du in MHGU Effekte findest ... damit es besser aussieht; es gibt ja
# einige Monster in MHGU, die in dem Gebiet kämpfen"). GU's monsters on the Frozen Seaway (stage 14: em 67 3 83 42 61 66 34 43 32 57 24 86) step and slide with the common cm202_001 / 002 / 020 /
# 021; each of those holds a set of elements per ground, and ground word 0x100 is the white one: a soft cloud, snow clods, a smear on the ground (C: files; Capcom bakes 0x100 into 71 cm202 records
# of em 38 42 61 66 67 83 86, such as Zamtrios' steps on joints 80, 90). cm202_002 is in her arc already and has the same elements as cm202_001, the steps' file; 0x100000 is GU's usual mask for it,
# which draws the whole set. So her records of 4U's em093_003 with the ground flag play GU's cm202_002: GU's record 3 of em068_00c (with GU's stage tint, table 7) as a world record, her points and
# 4U's scales. 4U's em093_003 stays on the two records without the ground flag. A DEVIATION, wanted. The set: k_ground's last column, module/em068_01_fx.c.
SNOW_EFL, SNOW_GU_ID, SNOW_MASK = 'effect\\cm\\cm202_002', 3, 0x100000


# 0.2.7 (the user's test of 0.2.6, log 2026-11-08 11-04-37, screenshot): "wenn sie sich bewegt kommt manchmal vereinzelt wie eine Staubwolke hoch ... sieht gelb orange aus", her ice splinters "top, so
# lassen". The log: record 2016 (4U's common dust qe006_001, joint 13, motion 0x2b frame 40) posts with set 3, 4U's soil set; her other ground records of 4U's common dust family qe006 (2000 2002 2006
# 2011 2013 2014 2017) are the same kind. They play GU's snow now too, as em093_003 since 0.2.3. Her own em093_007 (2008 / 2009, the ice splinters) stays 4U's.
def is_snow_record(r):
    return (r['grp'] == 93 and r['file'] == 3) or r['grp'] == 6


def ground_rows():
    """k_ground of module/em068_01_fx.c: (id, joint, x, z, snow)"""
    src = open(os.path.join(ROOT, 'monsters', 'tidal_najarala', 'module', 'em068_01_fx.c'), encoding='utf-8').read()
    body = src[src.index('k_ground[] = {'):]
    return [tuple(int(x) for x in m) for m in re.findall(r'\{\s*(\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(\d+)\s*\}', body[:body.index('};')])]


def gu_pel_record(pel, li, rid):
    """(path bytes, 2 bytes, 160 bytes) of a GU PEL record"""
    n, body = efl4u2gu.pel_lists(pel)[li]
    i = 0
    for _ in range(n):
        L = body[i]
        st = body[i + 3 + L:i + 3 + L + 160]
        if struct.unpack_from('<H', st, 0x30)[0] == rid:
            return body[i + 1:i + 1 + L], body[i + 1 + L:i + 3 + L], st
        i += 3 + L + 160
    raise KeyError(rid)


def pel_ground_records(pel, S, gu_pel_c, notes):
    mef = efl4u2gu.mef_records(S[(MEFS[0], efl4u2gu.T['MEF'])]) + efl4u2gu.mef_records(S[(MEFS[1], efl4u2gu.T['MEF'])])
    ground = [r for r in mef if r['flags'] & efl4u2gu.MEF_GROUND and r['joint'] >= 0]
    assert all(r['pos'][1] == 0.0 and r['pos'][0] == round(r['pos'][0]) and r['pos'][2] == round(r['pos'][2]) for r in ground), 'a ground record the table cannot hold'
    assert ground_rows() == [(r['id'], r['joint'], round(r['pos'][0]), round(r['pos'][2]), int(is_snow_record(r))) for r in ground], 'k_ground (module/em068_01_fx.c) differs from her MEF records'
    by = {r['id']: r for r in mef}
    snow_path, snow_two, snow_st = gu_pel_record(gu_pel_c, 1, SNOW_GU_ID)
    assert snow_path.decode('ascii') == SNOW_EFL and snow_st[0x3e] == 6 and snow_st[0x70] == 1, 'GU\'s snow record'
    lists = efl4u2gu.pel_lists(pel)
    n, body = lists[1]
    out, i, placed, ends, snow = bytearray(), 0, set(), 0, 0
    for _ in range(n):
        L = body[i]
        path, two, st = body[i + 1:i + 1 + L], body[i + 1 + L:i + 3 + L], bytearray(body[i + 3 + L:i + 3 + L + 160])
        i += 3 + L + 160
        r = by.get(struct.unpack_from('<H', st, 0x30)[0])
        on_ground = r and r['flags'] & efl4u2gu.MEF_GROUND and r['joint'] >= 0
        if on_ground and is_snow_record(r):
            head = bytearray(snow_st)
            struct.pack_into('<12f', head, 0, *([0.0] * 8), *r['scl'], 0.0)        # the module names the point (offset included), rotation none, 4U's scale
            head[0x30:0x34] = st[0x30:0x34]                                        # id, joint
            head[0x36], head[0x38], head[0x39], head[0x3a] = 3, 2, 1, 0            # PEL_TAIL_WORLD's: mode 3, a point; one shot as GU's dust
            struct.pack_into('<I', head, 0x48, SNOW_MASK)
            path, two, st = snow_path, snow_two, head
            placed.add(r['id'])
            snow += 1
        else:
            if on_ground:
                mask = bytes(st[0x48:0x4c])
                st[0x34:160] = efl4u2gu.PEL_TAIL_WORLD
                st[0x48:0x4c] = mask
                for o, v in efl4u2gu.PEL_COLOUR_OFF: st[o] = v
                placed.add(r['id'])
            if r and r['slot'] == 1:
                st[0x3a] = 1
                ends += 1
        out += bytes([len(path)]) + path + two + bytes(st)
    assert i == len(body), 'PEL list 1'
    assert placed == {r['id'] for r in ground}, 'a ground record has no PEL record'
    notes.append('effects: %d records on her ground (world posts, module/em068_01_fx.c), %d of them GU\'s snow %s, %d records end with their event range' % (len(placed), snow, SNOW_EFL, ends))
    res = pel[:8]
    for k, (cnt, b) in enumerate(lists):
        res += struct.pack('<I', cnt) + (bytes(out) if k == 1 else b)
    return res


def snow_first(ents, notes):
    """GU's snow effect and all it names, in GU's order, before her PEL u: a record finds what the arc has loaded (the lesson of her shell def, S for a PEL). Moving a file up harms nothing: whoever
    named it later still finds it."""
    paths_of = {}
    for e in ents: paths_of.setdefault(e[0], []).append(e)
    want, todo = set(), [SNOW_EFL]
    while todo:
        p = todo.pop()
        if p in want or p not in paths_of: continue
        want.add(p)
        for _, _, d in paths_of[p]:
            todo += [m.decode('ascii') for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', d)]
    at = next(i for i, e in enumerate(ents) if e[0] == PEL_U and e[1] == efl4u2gu.T['PEL'])
    moved = [e for e in ents[at:] if e[0] in want]
    assert any(e[0] == SNOW_EFL for e in moved), 'GU\'s snow effect is not in the arc'
    res = ents[:at] + moved + [e for e in ents[at:] if e[0] not in want]
    assert len(res) == len(ents)
    notes.append('effects: %s and %d more files moved before her PEL u' % (SNOW_EFL, len(moved) - 1))
    return res


def effects(S, gu_pel_u, gu_pel_c, gu_psls, notes):
    """her effects (tools/efl4u2gu.py effect_set) -> [(path, type, data)]. em093_0 + em093_1 (extra records). MEF group 120 (em120_100 / 101: Apex Tidal's) is not in her arc: not hers.
    hide_grey_models stays off: the chunk models that came out white on Dalamadur and Stygian are snow on her stage (soil-baked, SOLID_FILL fixes the 2x) and 4U draws them."""
    groups = {93: 'effect\\efl\\em\\em093\\em093_%03d'}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 6, 8, 13)})
    own = efl4u2gu.mef_records(S[(MEFS[1], efl4u2gu.T['MEF'])])
    code, base = code_4u()
    extra2 = []
    for (rid, name, follow), elem in zip(JET_FX, (12, 13)):
        p4 = struct.unpack_from('<I', code, struct.unpack_from('<I', code, EFL_TABLE_4U + 4 * 69 - base)[0] + 4 * elem - base)[0] - base
        path = code[p4:code.index(b'\0', p4)].decode('ascii')
        assert path == 'effect\\efl\\em\\em093\\' + name, (path, name)
        extra2.append((path, dict(id=rid, joint=-1, k=-1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), scl=(1.0, 1.0, 1.0), follow=follow, world=not follow, once=False)))
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef=MEFS[0], em_efl='effect\\efl\\em\\em093\\', groups=groups,
                extra=[(groups[r['grp']] % r['file'], r) for r in own],
                lmts=[(P4 + 'mot\\em093_%d' % b, PSL % b) for b in BANKS], pel=PEL_U, soil=seaway_soil(notes),
                list2=shell_list2(efl4u2gu.pel_lists(gu_pel_u)[2]), extra2=extra2, solid_fill=SOLID_FILL, intensity=True,
                solid_templates={SCALE_MODEL: SCALE_TEMPLATE})
    log = []
    out = efl4u2gu.effect_set(spec, log)
    out[(PEL_U, efl4u2gu.T['PEL'])] = pel_ground_records(out[(PEL_U, efl4u2gu.T['PEL'])], S, gu_pel_c, notes)
    her_u, gu_c = pel_names(out[(PEL_U, efl4u2gu.T['PEL'])], 1), {}
    for li in (1, 2):
        gu_c.update(pel_names(gu_pel_c, li))
    assert not {rid for rid, _, _ in JET_FX} & set(pel_names(gu_pel_u, 2)), 'PEL ids of the jet taken'
    for b, gu_psl in gu_psls.items():
        k = (PSL % b, efl4u2gu.T['PSL'])
        out[k] = gu_common_effects(out[k], gu_psl, her_u, gu_c, b, notes)
    for p in set(SHELL_FX.values()):
        assert (p, efl4u2gu.T['EFL']) in out, 'shell effect not shipped: ' + p
    notes.append('effects: %d entries (tools/efl4u2gu.py effect_set); jet records %s' % (len(out), [r for r, _, _ in JET_FX]))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return [(p, t, d) for (p, t), d in out.items()]


def sound(rom, notes):
    """her sound call (4U em023's file), waves, bank snd_em093 and request (tools/snd4u2gu.py monster_entries) -> ([(path, type, data)], {field: (path, type)}). Common-bank requests
    from GU em068_00, plus the ones GU's Najarala adds (its class may post them)."""
    spec = dict(name='em093', src=SRC_4U, p4_wave='sound\\se\\em\\em093\\wave\\', pg_wave='sound\\se\\em\\em068_01\\wav\\',
                p4_bank='sound\\se\\em\\em093\\snd_em093', pg_bank='sound\\se\\em\\em068_01\\snd_em068_01',
                p4_call='sound\\call\\em\\em023', pg_call='sound\\call\\em\\em068_01', donor_arc=GU_ARC,
                donor_name='GU em068_00', donor_extra=True)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    notes += log
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def dttune(gu, notes):
    """GU em068_00's dttune + the bytes where tools/dt_convert.py (donor em068_00) gives em093 != em023: her 4U differences on GU's own Najarala tuning (GU's retuned bytes and these
    never overlap: asserted). So her HP and hitzones are 4U's, whose Najarala values GU kept (C: GU changed 19 other bytes only)."""
    c23 = open(os.path.join(DT_DIR, 'dt_em023', 'dttune.bin'), 'rb').read()
    c93 = open(os.path.join(DT_DIR, 'dt_em093', 'dttune.bin'), 'rb').read()
    assert len(c23) == len(c93) == len(gu)
    delta = [i for i in range(len(gu)) if c23[i] != c93[i]]
    retuned = {i for i in range(len(gu)) if c23[i] != gu[i]}
    assert not retuned & set(delta), 'GU retuned bytes she changes: %s' % sorted(retuned & set(delta))
    out = bytearray(gu)
    for i in delta: out[i] = c93[i]
    notes.append('dttune: GU em068_00 + %d bytes of 4U em023 -> em093 differences (GU retuned %d other bytes); base HP %d (Najarala %d)' % (
        len(delta), len(retuned), struct.unpack_from('<H', out, 0x38)[0], struct.unpack_from('<H', gu, 0x38)[0]))
    return bytes(out)


def main():
    img = open(paths.GU_MAIN, 'rb').read()
    rom = RomFS(paths.GU_ROMFS)
    _, src = arcpack.read(open(SRC_4U, 'rb').read())
    S = {(p, t): d for p, t, d in src}
    _, gents0 = arcpack.read(rom.read(GU_ARC))
    notes = []
    gents = shell_data(gents0, notes)
    ghash = {(phash(p), t): (p, t) for p, t, _ in gents}
    gman = manifest_of(img, ALLOC['donor_index'])
    G = {(p, t): d for p, t, d in gents}
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em068_00's file of manifest field k

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    files, m4 = model(S, rom, gu_tex, notes)
    ents += files
    own[0] = (P + 'mod\\em068_01', T['MOD'])
    skeleton_check(gfile(0), [d for p, t, d in files if t == T['MOD']][0], notes)
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em068_01', T['XFS'], parts_xfs(gfile(3), groups, notes)))
    own[3] = (P + 'mod\\em068_01', T['XFS'])
    for b in BANKS:
        ents.append((P + 'mot\\em068_01_%d' % b, T['LMT'], motion_bank(S, gfile, b, notes)))
        own[4 + b] = (P + 'mot\\em068_01_%d' % b, T['LMT'])
    gu_cmd = [d for p, t, d in gents if p == 'enemy\\cmd_tbl\\em068_00_cmdtbl' and t == T['EMC']]
    assert len(gu_cmd) == 1 and fileid_entry(img, gman[37]) == (phash('enemy\\cmd_tbl\\em068_00_cmdtbl'), T['EMC'])
    ents.append(('enemy\\cmd_tbl\\em068_01_cmdtbl', T['EMC'], cmdtbl(S[('enemy\\em023\\data\\em023_cmd', T['EMC'])], gu_cmd[0], img, notes)))
    own[37] = ('enemy\\cmd_tbl\\em068_01_cmdtbl', T['EMC'])
    gu_pel_c = [d for p, t, d in gents if t == efl4u2gu.T['PEL'] and p == 'effect\\pel\\em\\em068_00c']
    assert len(gu_pel_c) == 1, 'GU em068_00c'
    ents += effects(S, gfile(17), gu_pel_c[0], {b: gfile(18 + b) for b in (0, 2, 3)}, notes)
    own[17] = (PEL_U, efl4u2gu.T['PEL'])
    for b in BANKS:
        own[18 + b] = (PSL % b, efl4u2gu.T['PSL'])
    files, fields = sound(rom, notes)
    ents += files
    own.update(fields)
    typ = ghash[fileid_entry(img, gman[33])][1]
    ents.append(('enemy\\dt_tune\\em068_01_dttune', typ, dttune(gfile(33), notes)))
    own[33] = ('enemy\\dt_tune\\em068_01_dttune', typ)
    dtb = lambda n: open(os.path.join(DT_DIR, n, 'dtbase.bin'), 'rb').read()
    assert dtb('dt_em093') == dtb('dt_em023'), 'dtbase of 4U em093 differs from em023\'s: own it'
    sys.path.insert(0, HERE)
    import hagi_em068_01                 # carves: 4U G body / shiny tables in s4, GU's filler in s0..s3
    for k, data in hagi_em068_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em068_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    import routes_em068_01 as routes     # her 4U area behaviour on the Frozen Seaway
    plan = routes.plan(S[('enemy\\em023\\data\\em023_cmd', T['EMC'])], rom)
    for k, kind in {40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select'}.items():
        typ = ghash[fileid_entry(img, gman[k])][1]
        build_file = {'area_link': routes.area_link_file, 'area_eat': routes.area_eat_file, 'map_info': routes.map_info_file, 'area_select': routes.area_select_file}[kind]
        ents.append(('enemy\\%s\\em068_01' % kind, typ, build_file(gfile(k), rom, plan, notes)))
        own[k] = ('enemy\\%s\\em068_01' % kind, typ)

    # ---- the shared GU em068_00 files: everything but what ours replace and em068_00's model (MOD, MRL, textures)
    replaced = {ghash[fileid_entry(img, gman[k])] for k in own if gman[k] != -1}
    drop = replaced | {(p, t) for p, t, _ in gents if p.startswith(P0 + 'mod\\')}
    while True:                                  # a file a kept one names by path stays
        kept = [(p, t, d) for p, t, d in gents if (p, t) not in drop]
        named = {(p, t) for p, t in drop if any(p.encode('ascii') in kd for _, _, kd in kept)}
        if not named: break
        for p, t in sorted(named):
            notes.append('kept %s although replaced: named by %s' % (p, [kp for kp, _, kd in kept if p.encode('ascii') in kd][:4]))
        drop -= named
    ents += kept
    ents = snow_first(ents, notes)
    notes.append('shared from em068_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em068_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U em093)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em068_00, its file ID)'

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
    json.dump(dict(monster='em068_01 (Tidal Najarala)', id='0x%x' % ALLOC['em_id'], registry_index=ALLOC['registry_index'],
                   file_id_base='0x%x' % FILE_ID_BASE, file_count=len(new_files), manifest=fields,
                   files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p)) for f, p, t in new_files], notes=notes),
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
