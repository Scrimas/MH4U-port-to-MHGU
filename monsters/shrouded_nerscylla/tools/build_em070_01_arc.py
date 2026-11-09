"""build_em070_01_arc.py : build nativeNX/arc/enemy/em070_01.arc (Shrouded Nerscylla = GU Nerscylla variant 1, ID 0x146) + its data file
section FILE.

  build_em070_01_arc.py      build, verify, then write (paths in monsters/shrouded_nerscylla/):
      romfs/nativeNX/arc/enemy/em070_01.arc
      tools/em070_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em001_02.arc): the variant's own files under enemy\\em070\\em070_01\\..., the files it shares with
variant 0 under em070_00's paths and file IDs. GU's class uEm070_00 runs it (variant byte 1, notes/plan.md: GU dropped 4U's tests of her, so what
differs is here as data or in module/em070_01.c).
  own, converted from MH4U em096.arc:
      mod\\em070_01 MOD + MRL        tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py)
      mod\\em070_01_NN_BM (+A)       albedo textures (BC3) + GU specular maps made from their alpha
      mod\\em070_01 XFS              GU em070_00's parts states, kept for em096's mesh groups
      mot\\em070_01_0/2/3/4          her 4U motion lists (LMT 67) with GU's finer tracks where GU has the motion (motion_bank), slots she lacks filled from GU's
      cmd_tbl\\em070_01_cmdtbl       4U em027_cmd for em 96 in GU's language (cmdtbl())
      effects                        tools/efl4u2gu.py effect_set: her EFLs (+ the qe families her MEF names) under their 4U paths, PEL u
                                     list 1 from em096_0, list 2 = GU em070_00u's with the shell effects on hers, a PSL per motion list;
                                     area colour = the Dunes' (her 4U quests' night Dunes on GU's Dunes); GU's common effects where her motions are GU's
      sound call / waves / bank / request   tools/snd4u2gu.py monster_entries
      dt_tune\\em070_01_dttune       GU em070_00's + the bytes where tools/dt_convert.py gives em096 != em027 (Tigerstripe's rule: GU's retunes
                                     of 4U Nerscylla and her differences do not overlap, asserted): HP, hitzones, parts on GU's balance
      hagi\\hagi_s0..s4_em070_01     carves: 4U G body / shiny tables in s4, GU's filler in s0..s3 (tools/hagi_em070_01.py)
      area_link / area_eat / map_info / area_select   GU em070_00's + map 5 (the Dunes, not a GU Nerscylla map) from her 4U data
                                     and GU's stage (tools/routes_em070_01.py)
  her data in GU's shell families (under GU's paths, as Tigerstripe's and Tidal Najarala's; no quest has both monsters, C): the families' defs name her PEL, shell01's
      G rank record is 4U uShell003's 216 (shell_data).
  shared, GU em070_00 (original paths + file IDs): camera (4U's is one file for em 27 / 96), sound triggers (PTS), PEL c, attack data, hitsize,
      bodydata, cambodydata, dtbase, dtbparts, area_patrol, doumouka: 4U em027 and em096 convert to the same attack / hit / body / dtbase data (C), so
      GU's own tuning of them stays.
Inputs besides the arcs: dump/converted/em096/dt_em027/ and dt_em096/ (build.py step dt) and the 4U ROM (core effect arcs, area colours).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/shrouded_nerscylla
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, ctr, efl4u2gu, emc, emdata4u, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, mrl_build, portdata, snd4u2gu, tex

NAME = 'shrouded_nerscylla'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em096.arc')
GU_ARC = '/nativeNX/arc/enemy/em070_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em070_01.arc')
OUT_JSON = os.path.join(HERE, 'em070_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02)
P4 = 'enemy\\em096\\'            # 4U paths
P0 = 'enemy\\em070\\em070_00\\'  # GU variant 0
P = 'enemy\\em070\\em070_01\\'   # ours
BANKS = (0, 2, 3, 4)             # her motion lists: manifest field 4 + bank (GU's too)
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 3, 4, 6, 7, 8, 37, 17, 18, 20, 21, 22, 12, 13, 33, 46, 47, 48, 49, 50, 40, 42, 43, 41]
DT_DIR = os.path.join(ROOT, 'dump/converted/em096')           # build.py step dt
PEL_U = 'effect\\pel\\em\\em070_01u'
PEL_GU = 'effect\\pel\\em\\em070_00u'
PSL = 'effect\\psl\\enemy\\em070\\em070_01\\mot\\em070_01_%d'
MEF = 'effect\\mef\\em\\em096_0'
GU_RS = {a for _, (a, _) in mrl.records(0x22).items() if a and a.startswith('RS')}     # GU's rasterizer states


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
            path = P + 'mod\\em070_01_' + name.split('em096_')[-1]
            s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
            out += [(path, T['TEX'], tex.encode_gu(t, 'bc3')), (path + '+A', T['TEX'], tex.encode_gu(s, 'bc3'))]
            gu_tex[src] = path
        paths_of[slot] = gu_tex[src]
        if slot == 'tAlbedoMap':
            paths_of['tSpecularMap'] = gu_tex[src] + '+A'
    return paths_of


def model(S, rom, gu_tex, notes):
    """em096 MOD + MRL (+ textures) -> [(path, type, data)], the parsed 4U MOD. Templates (Monoblos' rules + Tigerstripe's sphere map): additive ->
    'add', 4U BSBlendAlpha -> 'blend' with the material's own constants, emissive -> 'unlit', a lit E0 material with a tExtendMap -> 'solid_sphere',
    alpha-tested -> 'solid_at', else 'solid'. Every 4U material animation is converted. MRL before MOD, as in GU's arcs. Her skin's 4U normal map has no place in the
    'blend' template: left out (a DEVIATION, notes/plan.md)."""
    src = P4 + 'mod\\em096'
    d4, d4m = S[(src, T['MOD'])], S[(src, T['MRL'])]
    m4, r4 = modlib.parse(d4), mrl.read(d4m)
    anims4 = mrl_anim.material_anims(d4m)[1]
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
                path = P + 'mod\\em070_01_' + ext_tex.split('em096_')[-1]
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
        notes.append('material %s: template %s, type %d, %s%s%s, 4U params %s' % (
            mname, key, extra['mtype'], sorted(p.split('\\')[-1] for p in gp.values()), ', %d 4U animations' % len(ents4) if ents4 else '',
            ', 4U states %s -> %s' % (rs, rs_gu[:1]) if rs != rs_gu[:1] else '', [n for n, t, v in mm['params'] if n.startswith('t') and v]))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(P + 'mod\\em070_01', T['MRL'], mrl_bytes), (P + 'mod\\em070_01', T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(gu_xfs, groups, notes):
    """GU em070_00's parts states (rMonsterPartsManager XFS) for em096's mesh groups. Her group 50 (2 additive meshes, em 27's too in 4U): GU's states keep it, state 4 hides it, and
    GU's slot 132 (no variant test, C: 0xf9ee88) applies state 4 every frame, so it stays hidden as on GU's Nerscylla, whose model has none"""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    unnamed = sorted(set(groups) - {g for st in states for g, _ in st})
    assert not unnamed, 'em096 groups without a GU state: %s' % unnamed
    assert kept[4] == [(50, 0)], ('GU state 4 no longer hides group 50', kept[4])
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted({g for st in states for g, _ in st} - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in em096): %s' % (len(kept), dropped))
    return bytes(head) + data


def skeleton_check(gu_mod, our_mod, notes):
    """GU's class and the shared camera / data drive our model: the same bone ids, parents and bind positions (C)"""
    def by_id(m):
        bl = m['bone_list']
        return {b['index']: (bl[b['parent']]['index'] if b['parent'] != 255 else None, b['pos']) for b in bl}
    g, o = by_id(modlib.parse(gu_mod)), by_id(modlib.parse(our_mod))
    assert set(g) == set(o) and all(g[k][0] == o[k][0] for k in g), 'em096 skeleton differs from GU em070_00\'s'
    far = max((max(abs(a - b) for a, b in zip(g[k][1], o[k][1])), k) for k in g)
    notes.append('skeleton: %d bones equal to GU em070_00\'s; largest bind position difference %.1f (bone %d)' % (len(o), *far))


def motion_bank(S, gfile, b, notes):
    """her 4U list b, the motions she shares with GU's list in GU's form, with the slots only GU's list has (GU's class may ask for them: GU's code for them has no variant test). Her
    banks are 4U em027's animations track for track (C, 2026-11-06: only slots 30, 31, 33, 34 of her bank 4 are not in em027's, and GU's bank 4 holds them), and GU em070_00 holds the same animations
    on the same skeleton (skeleton_check) stored finer. So GU's tracks, the user's rule ("Wenn es in MHGU schon Animationen geben sollte ... kannst du aus MHGU nehmen"), and her 4U event blocks stay:
    sound and effect timing, her PSLs come from them (spec lmts reads S)."""
    d = S[(P4 + 'mot\\em096_%d' % b, T['LMT'])]
    gu = gfile(4 + b)
    ga, oa = lmt.anims(gu), lmt.anims(d)
    frames = lambda x, o: struct.unpack_from('<I', x, o + 8)[0]
    swap = [(i, i) for i, o in enumerate(oa) if o and i < len(ga) and ga[i]]
    for i, _ in swap:
        assert frames(d, oa[i]) == frames(gu, ga[i]), ('bank slot frames differ', b, i)
    size4 = len(d)
    d = lmt.with_tracks(d, gu, swap)
    notes.append('motions bank %d: GU\'s tracks in %d slots, her event blocks kept; %d slots stay 4U\'s; file %d B -> %d B' % (b, len(swap), sum(1 for o in oa if o) - len(swap), size4, len(d)))
    fill = [(i, i) for i, o in enumerate(ga) if o and i < len(oa) and not oa[i]]
    past = [i for i, o in enumerate(ga) if o and i >= len(oa)]
    if past:                                       # GU's slots past her table
        notes.append('motions bank %d: GU slots %s lie past her table of %d' % (b, past, len(oa)))
    if not fill: return d
    out = lmt.splice(d, gu, fill)
    notes.append('motions bank %d: her 4U list + GU\'s animations in the slots she lacks %s' % (b, [i for i, _ in fill]))
    return out


# ---- AI table (notes/plan.md "AI table"). 4U em027_cmd serves em 27 and 96: their differences are EMC op 0x46 blocks, a switch on the em number (g0 s2 s3 s6, g1 s106). Our table serves her only, so each
# block is reduced to her body. GU's table has no such switch (it dropped her). GU's language replaces 4U's where the engine needs it: EMC_GU = the area move g0 s0, patrol g0 s1, next areas g0 s12 (GU ops 0x94 0x95, area_select),
# g0 s17 and g1 s83 s84 (GU's stage numbers; on stage 5 the same default as 4U's), g20 s0. Group 16 = GU's (empty; 4U's rest group, which GU never selects, Black Gravios' check). 4U's op 0x87 (W+0x53a, frenzy, G: GU has no
# frenzy state) keeps its else body. 4U stage cases in kept scripts (g1 s44 s80 s81 s82 s94) get GU's numbers: 4U Dunes 17 / 18 -> GU 5 (STAGE_CASE). GU's extra entries are appended: g0 s24, g1 s107.. (GU's class picks group-1 scripts by
# number, area_act_tbl 107..114).
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_GU = {(0, 0), (0, 1), (0, 12), (0, 17), (1, 83), (1, 84), (20, 0)}
EMC_GU_GROUPS = (16,)
EMC_4U_ONLY = {0x03, 0x05, 0x40, 0x46, 0x49, 0x4a, 0x7e, 0x8a, 0x8b, 0x8c, 0x8d, 0x87}
STAGE_CASE = {2: 0xFF, 3: 13, 17: 5, 18: 5}        # 4U stage -> GU stage in a kept `2a 01 NN` case (4U Sunken Hollow: not a GU stage, so no case holds)
OP_FRENZY = 0x87


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


def cmdtbl(d4, gu, img, notes):
    """4U em027_cmd for em 96 in GU's language (see above) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[21] and not u4[22], 'EMC group layout changed'
    ops = lambda s: {t[0] for t in emc_tokens(s, lens)}
    assert not any(ops(x) & {0x92} for gr in g for x in gr), 'GU has a variant switch now'
    out, own, same, frenzy = [], [], [], []
    for gi in range(21):
        if gi in EMC_GU_GROUPS:
            out.append(list(g[gi])); continue
        scripts = []
        for k, s in enumerate(u4[gi]):
            gv = g[gi][k] if k < len(g[gi]) else None
            if (gi, k) in EMC_GU:
                scripts.append(gv); continue
            mine = emc_em_only(s, 96, lens)
            if OP_FRENZY in ops(mine):
                frenzy.append((gi, k))
                mine = emc_else_only(mine, lens, OP_FRENZY)
            mine = stage_cases(mine, lens)
            assert not ops(mine) & EMC_4U_ONLY, ('4U op left', gi, k, sorted(ops(mine) & EMC_4U_ONLY))
            (same if mine == gv else own).append((gi, k))
            scripts.append(mine)
        assert len(scripts) <= len(g[gi]), gi
        out.append(scripts + list(g[gi][len(scripts):]))
    assert [len(x) for x in out] == [len(x) for x in g], 'our table must carry every GU entry number'
    notes.append('AI table: 4U em027_cmd for em 96; GU\'s %s; GU\'s group %s; GU extra entries appended (%s); %d scripts equal to GU\'s, her own bodies in %s; frenzy branches cut in %s' % (
        sorted(EMC_GU), list(EMC_GU_GROUPS), ['g%d s%d..s%d' % (gi, len(u4[gi]), len(g[gi]) - 1) for gi in range(21) if len(g[gi]) > len(u4[gi])], len(same), own, frenzy))
    return emc.build(out, ver)


# ---- shells (notes/plan.md "Shells"). GU's families = 4U's shells (C): shell00 kinds 0..14, 15..17, 18..35 = 4U uShell001 subtypes by rank: her subtypes (93 95 120 ...) differ from Nerscylla's (11 13 119 ...) only in their effect group
# (72 instead of 38, the same element numbers), so GU's kinds and sh files are hers too. Family shell13 = 4U uShell012 60 / 61, the same. Family shell01 = 4U uShell003, the web bursts they leave: her 165 / 166 / 167 / 214 equal Nerscylla's 34 / 37 / 25 / 213 but her
# G rank 216, whose byte +6 is 56 against 215's 61 (C). So only that byte is data here, and PEL list 2 names her effects.
FAM00, FAM01 = 'shell\\em\\em070_00_shell00\\em070_00_00', 'shell\\em\\em070_00_shell01\\em070_00_01'
HDS_T, SHELL_DEF_T = 0x4EB68CEE, 0x4AA69872
U003_REC = 0x101f230                           # 4U attack records, 40 B
REC_G_NERSCYLLA, REC_G_HERS = 215, 216
# PEL list 2 by record id: GU's shell and class effects -> hers. GU's em070_00_NNN = 4U em027_NNN (C: same sizes and structure on 000 002 006 018 021 022 023; GU's file of 4U (38, 4) (38, 5) (uShell001 16) is 004 / 005, of (38, 9) (uShell003) 010), and 4U em096_NNN is her
# version of em027_NNN (group 72 = group 38 element for element to 039). The shot's impact: 4U uShell001 G rank (72, 41) = em096_202, which GU's single id 1 stands for (lower ranks em096_001: she has no quest there).
BS = chr(92)
EFL96 = 'effect' + BS + 'efl' + BS + 'em' + BS + 'em096' + BS + 'em096_%03d'
SHELL_FX = {0: 0, 1: 202, 2: 10, 30: 20, 31: 21, 32: 25, 33: 25, 34: 22, 90: 4, 91: 5, 100: 4, 101: 5, 1120: 18, 1121: 18}
# colourless 4U solid effect meshes: vertex RGB 127 = 1.0 (efl4u2gu convert_effect_mod); white drew them at 2x
SOLID_FILL = (127, 127, 127, 255)


def code_4u():
    return open(os.path.join(ROOT, 'dump/exefs_v11/code.bin'), 'rb').read(), 0x100000


def shell_data(gents, notes):
    """the kept GU entries with her data: her PEL in every family's def, her G rank burst"""
    code, base = code_4u()
    rec = lambda k: code[U003_REC + 40 * k - base:U003_REC + 40 * k + 40 - base]
    a, b = rec(REC_G_NERSCYLLA), rec(REC_G_HERS)
    assert [i for i in range(40) if a[i] != b[i]] == [6] and (a[6], b[6]) == (61, 56), 'uShell003 215 / 216 changed'
    out, defs = [], 0
    for p, t, d in gents:
        if p == FAM01 + '_hitdata' and t == HDS_T:
            assert d[16 + 56 * 2 + 6] == a[6] and d[16 + 6] == 0x38 and d[16 + 56 + 6] == 0x3d, 'GU shell01 HDS changed'
            d = bytearray(d)
            d[16 + 56 * 2 + 6] = b[6]
            d = bytes(d)
            notes.append('shell01 HDS entry 2: byte +6 %d -> %d (4U uShell003 record %d, hers at G rank)' % (a[6], b[6], REC_G_HERS))
        elif t == SHELL_DEF_T and p.startswith('shell\\em\\em070_00_shell'):
            assert d.count(PEL_GU.encode()) == 1, p
            d = d.replace(PEL_GU.encode(), PEL_U.encode())
            defs += 1
        out.append((p, t, d))
    assert defs == 4, defs
    notes.append('shell families: %d defs name her PEL' % defs)
    return out


def shell_list2(list2):
    """GU PEL list 2 (count, record bytes) with the shell effects on hers (state bytes kept, as Tigerstripe's): by record id, as ids 1 and 2 share GU's file. A file 4U has no twin for (GU's em070_00_500) or GU's common ones stay"""
    n, body = list2
    out, i, hit = b'', 0, set()
    for _ in range(n):
        L = body[i]
        path = body[i + 1:i + 1 + L].decode('ascii')
        rest = body[i + 1 + L:i + 1 + L + 2 + 160]
        rid = struct.unpack_from('<H', rest, 2 + 0x30)[0]
        new = EFL96 % SHELL_FX[rid] if rid in SHELL_FX else None
        if new: hit.add(rid)
        new = (new or path).encode('ascii')
        out += bytes([len(new)]) + new + rest
        i += 1 + L + 2 + 160
    assert i == len(body) and hit == set(SHELL_FX), ('PEL list 2 lacks', set(SHELL_FX) - hit)
    return n, out


def dunes_soil(notes):
    """RGBA area colour for the effects: the per-channel median of the 4U Dunes hunting areas' area_color_soil, Tigerstripe's and Monoblos' rule. Her 4U quests are on the night Dunes (stage 18); GU has only the
    day map, so its colour, as Monoblos' m00818"""
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


# The user's rule (2026-11-06): where an animation is the same as GU's, GU's effects, as with the roar. Her banks and GU's have equal frames in every shared slot (motion_bank), so GU's slots fit. GU's common effects (PEL c, kind 3, its cm* files: air, dust,
# spray) go into her entry and replace her 4U common effects (kind 4, qe*: 4U's dust) there. Her own em096_* effects stay, they are what makes her Shrouded; GU's Nerscylla-only slots (em070_*) do not come. Where GU's motion has no common effect, hers stay as they are. A DEVIATION from 4U, wanted.
#
# 0.1.2 (the user's test of 0.1.1, log 2026-11-07 20-15-35: "beim Laufen fliegen Äste und Blätter weg, obwohl sie in der Wüste ist", and nothing at the dig-in):
# - GU_FOREST: GU Nerscylla's own debris cm200_067 (records 150 / 151: 8 model units cm200_101, colour ff3a4f41 dark green, element ground word 0x20; C, files) sat in her walk 0/6 and in 2/25 2/26 4/8 4/9
#   4/12. GU's Nerscylla lives in forests; GU's Diablos, the Dunes' own, has no such record (his walk: cm202_001 / 002, sand dust). Her PEL c posts draw every set (em070_01_fx.c), so the leaves drew on the
#   sand. Not taken: where GU's motion then has no common effect left, hers stay (4U's dust; 0/6 keeps em096_040, sand-coloured).
# - KEEP_4U: her dig-in 0x421 (bank 4 slot 33): 4U posts qe006_010 (record 504, ground flag) at frames 47, 76, 106 (C: em096_4 events); GU's slot has only cm202_006 (250) at frames 29..31, which the
#   user did not see. Her 504 stays next to GU's 250 (placed on her ground by em070_01_fx.c). A DEVIATION from the rule above, the user's wish.
# 0.1.3 (the user's test of 0.1.2, log 2026-11-08 08-38-41: the dig-in sand is seen but "wirkt weiß"; Monoblos' sand, GU Diablos' own, looks right to them; asked, the user: "Ja, Diablos-Sand"):
# - KEEP_4U empty: 504 leaves the dig-in again. DIABLOS_DIG: GU Diablos' burrow sand, PEL u list 1 record 370 = em007_00_000 (joint -1; GU em007_00 bank 0 slots 23 / 24, motions 0x17 / 0x18, frame 26 and
#   1 / 48 / 94; C, PSL; Monoblos plays these motions in his 6/208), posted at her 4U frames 47, 76, 106 of 0x421 (4U's timing, em096_4 events). burrow_trail copies the record and its files; module/em070_01_fx.c
#   leaves its request as GU's Diablos posts it (no ground set named). A DEVIATION, wanted.
GU_FOREST = {'cm200_067'}
# 0.1.6 (the user, 2026-11-08: "beim eingraben, die Sandspur wenn unter der Erde sowie das auftauchen nur Umgebungseffekte vom Diablos ... Entferne also die MH4U Effekte für die aufgezählten Bewegungen,
#   die anderen Effekte der Umgebung so lassen"): in her dig-in 0x421 (bank 4 slot 33) and her burst 0x422 (slot 34) only GU Diablos' ground effects. DIABLOS_DROP takes out the others there:
#   GU Nerscylla's cm202_006 (PEL c 250, kind 3) in both, 4U's ground dust em096_200 (502 at frame 0, 503 at 86, kind 4) in the burst. Her own em096_008 / em096_036 at the burst's frame 41 stay:
#   purple / dark red (C, colours ff6794 / 9700d1 / 200711 ...), her miasma, not the ground. DIABLOS_POSTS: the dig-in keeps 370 (em007_00_000, Diablos' 0x17 / 0x18); the burst gets Diablos'
#   eruption em007_00_004 (GU em007_00c list 1 records 21, joint -1, mask 1, and 22, joint 0, mask 2: his burrowed attack 0x214 = bank 2 slot 20 posts them at frames 56 and 109, C, PSL) as her
#   records 1402 / 1403 at her 4U frames 41 (her break-out: 4U's burst posts) and 86 (4U's ground dust 503). A DEVIATION, wanted.
# 0.1.8 (the user's test of 0.1.7, log 2026-11-08 12-53-43, screenshot): Diablos' trail is seen now, but "Beim eingraben sowie die Sandspur wenn sie unter der Erde ist und bei auftauchen sollen doch
#   die Effekte aus mh4u genommen werden ... die von diablos passen nicht zu ihr", and the odd glitter on the ground at the discovery (circled) goes. So 0x421 and 0x422 play 4U's effects again: 504
#   (qe006_010) at 47 / 76 / 106 (KEEP_4U) and the burst's 502 / 503 (em096_200) with her miasma; GU Nerscylla's cm202_006 (250) stays out of both (a GU effect, never seen). Diablos' 370 / 1402 /
#   1403 are gone. 4U plays nothing while she travels (C, "Effects" in notes/plan.md): Diablos' trail 1400 / 1401 stays until the user decides.
#   The glitter: her discovery motion 0x3e (bank 0 slot 62; the log: script 5/0, action 2/0 motion 0x3e, only there) is GU's with GU Nerscylla's common cm202_021 (PEL c 31, frame 2) and cm202_020
#   (30, frame 51); her PEL c posts name no ground set, so every ground's elements draw at once (sand, water, snow: S, the look). GU_DROP takes them out there.
KEEP_4U = {(4, 33): {504}}
# 0.1.10 (the user on 0.1.9, log 2026-11-08 13-17-24: the 4U dust at the dig-in shows "irgendwie gelb"): 4U's Intensity 1 baked as x2 into the soil-multiplied grey turns qe006_010 into (255, 230, 162)
#   and em096_200 into (252, 198, 140) (C, dustcol); GU lights it brighter still. At 1x they come out (147, 115, 82) / (126, 99, 70), the brown of GU's own Dunes dust (cm202_002's sand elements
#   ff5f7f9f = (159, 127, 95), C). So the dig-in and burst dust stay 1x: a DEVIATION from 4U's brightness, for the colour the user expects. Her other effects keep the bake.
# 0.1.14 (the maintainer's test of 0.1.13, PR #23, 2026-11-09: "When she dives underground or is toppled, some efx is broken and appear as near-pure white"): two causes (C, her 4U EFLs).
#   (1) Rock chunks: the dig-in dust qe006_010 (504; motions 0x409, 0x40c, 0x421) draws one grey model unit (e4e4e6) of the shared chunk model qe000_001, the burst em096_200 (502 / 503;
#   0x422) five (999999 .. bfbfbf) of cm000_000 / qe001_000. GU washes these grey chunk models out to near white (issue #6, tools/efl4u2gu.py HIDE_GREY_MODELS notes), so they are hidden
#   as on Black Gravios, Dalamadur and Stygian Zinogre (spec hide_grey_models 'chunks', efl4u2gu.CHUNK_MODELS): a DEVIATION from 4U, which draws them. The dust itself stays. The rule also
#   hides the chunk units of em096_102, em096_201, qe000_000 and qe000_001 (4U code posts 1031 / 1032, 1012, 1004).
#   (2) Her 4U fall dust qe006_001 (500 / 501) still had the x2 bake that made the dig-in dust white before 0.1.10. It is left only where GU's motion has no common effect of its own: 501 in
#   0x304, one of her bank-3 reaction motions (the others play GU's common dust). Now 1x as well, the brown of the dig-in and burst dust.
DUST_1X = ('qe006_010', 'em096_200', 'qe006_001')
DIABLOS_POSTS = {}
GU_DROP = {(4, 33): {(3, 250)}, (4, 34): {(3, 250)}, (0, 61): {(3, 30), (3, 31)}, (0, 62): {(3, 30), (3, 31)},
           (0, 6): {(4, 50)}, (0, 8): {(4, 50)}}
# 0.1.11 (the user on 0.1.10, screenshot: the glitter on the sand is still there, far from her, while she has not seen the hunter yet; it vanishes when walked to and cannot be gathered): her own 4U
#   turn dust em096_040 (record 50, ground flag, motions 6 and 8 = her turns, posted every frame 7.. / 20.., world posts on her ground, C: logs 12-53-43 and 13-17-24 show it at every turn
#   before and at the discovery) is the one ground effect of hers left there, cream (255, 230, 162) / (255, 255, 186) after the x2 bake: bright points on the sand (S, no 0.1.10 log yet). The user,
#   asked to remove the glitter: out of both turns. A DEVIATION from 4U (no ground dust when she turns).
# 0.1.10: her discovery has two motions (the log 13-17-24: script 5/0 played 0x3d, 12-53-43 played 0x3e); both hold the same GU commons, 0.1.8 took them only out of 0x3e
DIABLOS_DROP = GU_DROP          # diablos_dig's name since 0.1.6


def gu_common_effects(psl, gu_psl, her_u, gu_c, bank, notes):
    out = bytearray(psl)
    done = 0
    skipped = []
    for i in range(min(struct.unpack_from('<H', gu_psl, 6)[0], struct.unpack_from('<H', psl, 6)[0])):    # GU's slots past her table: motion_bank
        g = psl_entry(gu_psl, i)
        if not g: continue
        gf, gmask, gids, gkinds, gper = g
        add = [k for k in range(32) if gmask >> k & 1 and gkinds[k] == 3 and gu_c.get(gids[k], '').startswith('cm')]
        skipped += [(i, gids[k]) for k in add if gu_c[gids[k]] in GU_FOREST]
        add = [k for k in add if gu_c[gids[k]] not in GU_FOREST]
        if not add: continue
        e = psl_entry(out, i)
        f, mask, ids, kinds, per = e if e else (gf, 0, [0] * 32, [0] * 32, [0] * (gf - 1))
        assert f == gf, ('her motion and GU\'s differ in frames', bank, i, f, gf)
        for k in range(32):
            if mask >> k & 1 and kinds[k] == 4 and not her_u.get(ids[k], 'em096').startswith('em096') and ids[k] not in KEEP_4U.get((bank, i), ()):
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
    notes.append('effects bank %d: GU\'s common effects in %d motions; GU\'s forest debris not taken (slot, id): %s' % (bank, done, skipped))
    return bytes(out)


def diablos_dig(psl, bank, notes):
    """DIABLOS_DROP out of / DIABLOS_POSTS (kind 4 = PEL u list 1, at her 4U frames) into her PSL of bank `bank`"""
    out = bytearray(psl)
    for (b, i) in sorted(set(DIABLOS_POSTS) | set(DIABLOS_DROP)):
        if b != bank: continue
        f, mask, ids, kinds, per = psl_entry(out, i)
        dropped = []
        for k in range(32):
            if mask >> k & 1 and (kinds[k], ids[k]) in DIABLOS_DROP.get((b, i), ()):
                dropped.append((kinds[k], ids[k]))
                mask &= ~(1 << k)
                ids[k], kinds[k] = 0, 0
                per = [v & ~(1 << k) for v in per]
        assert set(dropped) == set(DIABLOS_DROP.get((b, i), ())), ('not in the slot', bank, i, DIABLOS_DROP.get((b, i)), dropped)
        for rid, frames in DIABLOS_POSTS.get((b, i), ()):
            assert rid not in [ids[k] for k in range(32) if mask >> k & 1], ('the slot has the record already', bank, i, rid)
            assert all(0 <= x < f - 1 for x in frames), ('a frame past the motion', bank, i)
            k = next(k for k in range(32) if not mask >> k & 1)
            ids[k], kinds[k] = rid, 4
            mask |= 1 << k
            per = [v | ((x in frames) << k) for x, v in enumerate(per)]
        psl_put(out, i, f, mask, ids, kinds, per)
        notes.append("effects bank %d slot %d: out %s, GU Diablos' %s" % (bank, i, sorted(dropped), list(DIABLOS_POSTS.get((b, i), ()))))
    return bytes(out)

def psl_ids(psl):
    """{(kind, id): [slots]} of a PSL"""
    out = {}
    for i in range(struct.unpack_from('<H', psl, 6)[0]):
        e = psl_entry(psl, i)
        if not e: continue
        for k in range(32):
            if e[1] >> k & 1: out.setdefault((e[3][k], e[2][k]), []).append(i)
    return out


# Her 4U effects on the ground (Tidal Najarala's way, her notes: 4U 0x391b50 copies the MEF flags into the effect; ground flag (bit 1): x, z = the joint + the record offset, y = her ground). GU's records have no such tail, so these
# become world records and module/em070_01_fx.c (hook on the PSL post) names the point: the joint's x, z at the post (joint -1: her own), her ground y (rec+0x5b4). A DEVIATION: the point does not ride the joint over the effect's life (it
# hardly matters: em096_040 plays on motions 6 and 8, turns on the spot; the others are one-frame posts). Slot mode 1: 4U ends the effect when the event range ends; in GU that is end mode 1 (+0x3a, Dalamadur's pel_slot_end has the code reading).
def ground_rows():
    """k_ground of module/em070_01_fx.c: (id, joint, offset z)"""
    src = open(os.path.join(MON, 'module', 'em070_01_fx.c'), encoding='utf-8').read()
    body = src[src.index('k_ground[] = {'):]
    return [tuple(int(x) for x in m) for m in re.findall(r'\{\s*(\d+),\s*(-?\d+),\s*(-?\d+)\s*\}', body[:body.index('};')])]


def pel_ground_records(pel, S, notes):
    mef = efl4u2gu.mef_records(S[(MEF, efl4u2gu.T['MEF'])])
    ground = [r for r in mef if r['flags'] & efl4u2gu.MEF_GROUND and r['id'] != 1008]      # 1008: a code post of 4U, no motion names it
    assert all(r['pos'][:2] == (0.0, 0.0) and r['pos'][2] == round(r['pos'][2]) for r in ground), 'a ground record the table cannot hold'
    assert ground_rows() == [(r['id'], r['joint'], round(r['pos'][2])) for r in ground], 'k_ground (module/em070_01_fx.c) differs from her MEF records'
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
    notes.append('effects: %d records on her ground %s (world posts, module/em070_01_fx.c), %d records end with their event range' % (len(placed), sorted(placed), ends))
    res = pel[:8]
    for k, (cnt, b) in enumerate(lists):
        res += struct.pack('<I', cnt) + (bytes(out) if k == 1 else b)
    return res


# GU's ground trail while she travels under the ground (the user, 2026-11-07, after the first test: "wenn sie sich unter der Erde bewegt, entstehen Effekte ... wenn es in MHGU Effekte fürs Buddeln wie bei Monoblos gibt, nimm diese"). module/em070_01.c starts it through GU's 0xa4a58(this, 2),
# common effect 2 = element 1400 of list 2 of her PEL u (table 0x159fa1c, C). GU's Nerscylla has no such element: 4U and GU play nothing in her travel (motion 1 has no events, 4U 0x915da0 and GU 0xfa6b74 post nothing, C), so this is the look of GU's Diablos, a DEVIATION, wanted.
TRAIL_ARC = '/nativeNX/arc/enemy/em007_00.arc'
TRAIL_PEL = 'effect\\pel\\em\\em007_00u'
TRAIL_ID = 1400
TRAIL_WORLD_ID = 1401           # 0.1.5: 1400 with the tail that places once; module/em070_01.c posts it at her point and moves it every frame (its trail_watch has the reading)
COPY_RECS = ()   # (GU em007_00 PEL u / c, list, his id, her id). 0.1.9: none (the user: under the ground "gar nichts, wie 4U"); 0.1.1..0.1.8 the trail 1400 (+ 1401), 0.1.3..0.1.7 also 370 / 1402 / 1403
TRAIL_PEL_C = 'effect\\pel\\em\\em007_00c'


def world_copy(rec, rid):
    """a PEL record (u8 length, path, 2 bytes, 160 bytes) as record `rid` that places once: the bytes where efl4u2gu's follow tail (PEL_TAIL_PREV) and world tail (PEL_TAIL_WORLD) differ
    take the world tail's, but the end mode +0x3a (0.1.5 took the world tail's 0 too: the log, 11-42-26... 12-13-57, posted it again every 4 frames, it ended on its own; Diablos' 1 keeps his
    alive for its 3600 frames, S); GU Diablos' 1400 must hold the follow tail's there (asserted), its other bytes stay his"""
    at = 1 + rec[0] + 2
    st = bytearray(rec[at:at + 160])
    diff = [k for k in range(len(efl4u2gu.PEL_TAIL_PREV)) if efl4u2gu.PEL_TAIL_PREV[k] != efl4u2gu.PEL_TAIL_WORLD[k] and k != 0x3a - 0x34]   # 0.1.6: +0x3a (end mode) stays his
    assert all(st[0x34 + k] == efl4u2gu.PEL_TAIL_PREV[k] for k in diff), ('the record does not hold the follow tail', [(k, st[0x34 + k]) for k in diff])
    for k in diff:
        st[0x34 + k] = efl4u2gu.PEL_TAIL_WORLD[k]
    struct.pack_into('<H', st, 0x30, rid)
    return rec[:at] + bytes(st)


def burrow_trail(rom, ents, notes):
    """ents with GU Diablos' records COPY_RECS added to her PEL u (a PEL c record keeps its list, takes her id), the world copy TRAIL_WORLD_ID of the trail, and the files they name (those her arc lacks)"""
    _, dia = arcpack.read(rom.read(TRAIL_ARC))
    T_PEL = efl4u2gu.T['PEL']
    src = {'u': efl4u2gu.pel_lists(next(d for p, t, d in dia if p == TRAIL_PEL and t == T_PEL)),
           'c': efl4u2gu.pel_lists(next(d for p, t, d in dia if p == TRAIL_PEL_C and t == T_PEL))}
    at = next(k for k, e in enumerate(ents) if e[0] == PEL_U and e[1] == T_PEL)
    pel = ents[at][2]
    lists = efl4u2gu.pel_lists(pel)

    def has(li, rid):
        i = 0
        for _ in range(lists[li][0]):
            if struct.unpack_from('<H', lists[li][1], i + 1 + lists[li][1][i] + 2 + 0x30)[0] == rid: return True
            i += 1 + lists[li][1][i] + 2 + 160
        return False

    recs = {}
    for pk, li, rid, her in COPY_RECS:
        n, body = src[pk][li]
        i, rec = 0, None
        for _ in range(n):
            size = 1 + body[i] + 2 + 160
            if struct.unpack_from('<H', body, i + 1 + body[i] + 2 + 0x30)[0] == rid: rec = body[i:i + size]
            i += size
        assert rec, ('GU Diablos has no such record', pk, li, rid)
        assert not has(li, her), ('her PEL u has the record already', li, her)
        if her != rid:
            at_st = 1 + rec[0] + 2
            rec = rec[:at_st + 0x30] + struct.pack('<H', her) + rec[at_st + 0x32:]
        recs.setdefault(li, []).append(rec)
        if (pk, li, rid) == ('u', 2, TRAIL_ID):
            assert not has(li, TRAIL_WORLD_ID), 'her PEL u has the world trail id already'
            recs[li].append(world_copy(rec, TRAIL_WORLD_ID))
    res = pel[:8]
    for k, (cnt, b) in enumerate(lists):
        res += struct.pack('<I', cnt + len(recs.get(k, ()))) + b + b''.join(recs.get(k, ()))
    out = list(ents)
    out[at] = (ents[at][0], ents[at][1], res)
    have = {(p, t): d for p, t, d in ents}
    by = {}
    for p, t, d in dia:
        by.setdefault(p, []).append((p, t, d))
    todo, seen, added = [r[1:1 + r[0]].decode('ascii') for rs in recs.values() for r in rs], set(), 0
    while todo:
        p = todo.pop()
        if p in seen: continue
        seen.add(p)
        assert p in by, ('a file of the record is not in GU em007_00', p)
        for e in by[p]:
            todo += [m.decode('ascii') for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', e[2])]
            if (e[0], e[1]) in have:
                assert have[(e[0], e[1])] == e[2], ('another file of that name in her arc', e[0])
    # 0.1.7: in GU Diablos' arc order, which loads every file before the effects that name it. 0.1.1..0.1.6 added them in walk order, an EFL before its own textures
    # (em007_00_005 at 167, its cm090_015 at 168; em007_00_004 at 159, its cm090_014 at 160): a file finds what the arc has loaded (Tidal's snow lesson), so the trail
    # and the eruption drew nothing in any test, while 370's elements (mask 0x40) name only files that came first and were seen (the user, 2026-11-08).
    for e in dia:
        if e[0] in seen and (e[0], e[1]) not in have:
            out.append(e)
            added += 1
    pos = {(e[0], e[1]): i for i, e in enumerate(out)}
    for e in out:
        for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', e[2]):
            for t in [k for k in pos if k[0] == m.decode('ascii')]:
                assert pos[t] < pos[(e[0], e[1])] or e[0] not in seen, ('a file after the effect that names it', e[0], t[0])
    notes.append("effects: GU Diablos' records %s in her PEL u (GU em007_00) + %d (%d placed once), %d files added: %s" % (COPY_RECS, TRAIL_WORLD_ID, TRAIL_ID, added, sorted(seen)))
    return out


def effects(S, gu_pel_u, gu_pel_c, gu_psls, notes):
    """her effects (tools/efl4u2gu.py effect_set) -> [(path, type, data)]. hide_grey_models 'chunks' since 0.1.14: GU draws the grey rock-chunk models of her dig-in and burst near white (DUST_1X
    notes). Effects of 4U's ground flag: the list of what remains after GU's common effects is logged, notes/plan.md "Ground"."""
    groups = {96: EFL96}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 3, 6, 8, 13)})
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef=MEF, em_efl='effect\\efl\\em\\em096\\', groups=groups, extra=[],
                lmts=[(P4 + 'mot\\em096_%d' % b, PSL % b) for b in BANKS], pel=PEL_U, soil=dunes_soil(notes),
                list2=shell_list2(efl4u2gu.pel_lists(gu_pel_u)[2]), solid_fill=SOLID_FILL, intensity=True, intensity_skip=DUST_1X,
                hide_grey_models='chunks')
    log = []
    out = efl4u2gu.effect_set(spec, log)
    out[(PEL_U, efl4u2gu.T['PEL'])] = pel_ground_records(out[(PEL_U, efl4u2gu.T['PEL'])], S, notes)
    her_u, gu_c = pel_names(out[(PEL_U, efl4u2gu.T['PEL'])], 1), {}
    for li in (1, 2):
        gu_c.update(pel_names(gu_pel_c, li))
    for b, gu_psl in gu_psls.items():
        k = (PSL % b, efl4u2gu.T['PSL'])
        out[k] = diablos_dig(gu_common_effects(out[k], gu_psl, her_u, gu_c, b, notes), b, notes)
    mef = efl4u2gu.mef_records(S[(MEF, efl4u2gu.T['MEF'])])
    ground = {r['id'] for r in mef if r['flags'] & efl4u2gu.MEF_GROUND}
    for b in BANKS:
        left = {i: v for (kind, i), v in psl_ids(out[(PSL % b, efl4u2gu.T['PSL'])]).items() if kind == 4 and i in ground}
        notes.append('effects bank %d: 4U ground-flag records left in her motions: %s' % (b, left))
    for rid in SHELL_FX:
        assert (EFL96 % SHELL_FX[rid], efl4u2gu.T['EFL']) in out, 'shell effect not shipped: %d' % rid
    notes.append('effects: %d entries (tools/efl4u2gu.py effect_set)' % len(out))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    return [(p, t, d) for (p, t), d in out.items()]


def sound(rom, notes):
    """her sound call (4U em027's file), waves, bank snd_em096 and request (tools/snd4u2gu.py monster_entries) -> ([(path, type, data)], {field: (path, type)}). Common-bank requests
    from GU em070_00, plus the ones GU's Nerscylla adds (its class may post them)."""
    spec = dict(name='em096', src=SRC_4U, p4_wave='sound\\se\\em\\em096\\wave\\', pg_wave='sound\\se\\em\\em070_01\\wav\\',
                p4_bank='sound\\se\\em\\em096\\snd_em096', pg_bank='sound\\se\\em\\em070_01\\snd_em070_01',
                p4_call='sound\\call\\em\\em027', pg_call='sound\\call\\em\\em070_01', donor_arc=GU_ARC,
                donor_name='GU em070_00', donor_extra=True)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    notes += log
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def dttune(gu, notes):
    """GU em070_00's dttune + the bytes where tools/dt_convert.py (donor em070_00) gives em096 != em027: her 4U differences on GU's own Nerscylla tuning (GU's retuned bytes and these
    never overlap: asserted). So her hitzones are 4U's, whose Nerscylla values GU kept (C: GU changed 7 other bytes only)."""
    c23 = open(os.path.join(DT_DIR, 'dt_em027', 'dttune.bin'), 'rb').read()
    c93 = open(os.path.join(DT_DIR, 'dt_em096', 'dttune.bin'), 'rb').read()
    assert len(c23) == len(c93) == len(gu)
    delta = [i for i in range(len(gu)) if c23[i] != c93[i]]
    retuned = {i for i in range(len(gu)) if c23[i] != gu[i]}
    assert not retuned & set(delta), 'GU retuned bytes she changes: %s' % sorted(retuned & set(delta))
    out = bytearray(gu)
    for i in delta: out[i] = c93[i]
    notes.append('dttune: GU em070_00 + %d bytes of 4U em027 -> em096 differences at %#x..%#x (GU retuned %d other bytes); base HP %d (Nerscylla %d)' % (
        len(delta), delta[0], delta[-1], len(retuned), struct.unpack_from('<H', out, 0x38)[0], struct.unpack_from('<H', gu, 0x38)[0]))
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
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em070_00's file of manifest field k

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    files, m4 = model(S, rom, gu_tex, notes)
    ents += files
    own[0] = (P + 'mod\\em070_01', T['MOD'])
    skeleton_check(gfile(0), [d for p, t, d in files if t == T['MOD']][0], notes)
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em070_01', T['XFS'], parts_xfs(gfile(3), groups, notes)))
    own[3] = (P + 'mod\\em070_01', T['XFS'])
    for b in BANKS:
        ents.append((P + 'mot\\em070_01_%d' % b, T['LMT'], motion_bank(S, gfile, b, notes)))
        own[4 + b] = (P + 'mot\\em070_01_%d' % b, T['LMT'])
    gu_cmd = [d for p, t, d in gents if p == 'enemy\\cmd_tbl\\em070_00_cmdtbl' and t == T['EMC']]
    assert len(gu_cmd) == 1 and fileid_entry(img, gman[37]) == (phash('enemy\\cmd_tbl\\em070_00_cmdtbl'), T['EMC'])
    ents.append(('enemy\\cmd_tbl\\em070_01_cmdtbl', T['EMC'], cmdtbl(S[('enemy\\em027\\data\\em027_cmd', T['EMC'])], gu_cmd[0], img, notes)))
    own[37] = ('enemy\\cmd_tbl\\em070_01_cmdtbl', T['EMC'])
    gu_pel_c = [d for p, t, d in gents if t == efl4u2gu.T['PEL'] and p == 'effect\\pel\\em\\em070_00c']
    assert len(gu_pel_c) == 1, 'GU em070_00c'
    ents += effects(S, gfile(17), gu_pel_c[0], {b: gfile(18 + b) for b in BANKS}, notes)
    own[17] = (PEL_U, efl4u2gu.T['PEL'])
    for b in BANKS:
        own[18 + b] = (PSL % b, efl4u2gu.T['PSL'])
    files, fields = sound(rom, notes)
    ents += files
    own.update(fields)
    typ = ghash[fileid_entry(img, gman[33])][1]
    ents.append(('enemy\\dt_tune\\em070_01_dttune', typ, dttune(gfile(33), notes)))
    own[33] = ('enemy\\dt_tune\\em070_01_dttune', typ)
    dtb = lambda n: open(os.path.join(DT_DIR, n, 'dtbase.bin'), 'rb').read()
    assert dtb('dt_em096') == dtb('dt_em027'), 'dtbase of 4U em096 differs from em027\'s: own it'
    a, b = emdata4u.load_4u('em027'), emdata4u.load_4u('em096')
    assert emdata4u.attackdata(a['etd']) == emdata4u.attackdata(b['etd']) and emdata4u.hitsize(a['etd']) == emdata4u.hitsize(b['etd']) and \
        emdata4u.bodydata(a['emd'], 8) == emdata4u.bodydata(b['emd'], 8) and emdata4u.bodydata(a['emd'], 9) == emdata4u.bodydata(b['emd'], 9), 'her attack / hit / body data differ from em027\'s: own them'
    sys.path.insert(0, HERE)
    import hagi_em070_01                 # carves: 4U G body / shiny tables in s4, GU's filler in s0..s3
    for k, data in hagi_em070_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em070_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    import routes_em070_01 as routes     # her 4U area behaviour on the Dunes
    plan = routes.plan(S[('enemy\\em027\\data\\em027_cmd', T['EMC'])], rom)
    for k, kind in {40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select'}.items():
        typ = ghash[fileid_entry(img, gman[k])][1]
        build_file = {'area_link': routes.area_link_file, 'area_eat': routes.area_eat_file, 'map_info': routes.map_info_file, 'area_select': routes.area_select_file}[kind]
        ents.append(('enemy\\%s\\em070_01' % kind, typ, build_file(gfile(k), rom, plan, notes)))
        own[k] = ('enemy\\%s\\em070_01' % kind, typ)

    # ---- the shared GU em070_00 files: everything but what ours replace and em070_00's model (MOD, MRL, textures)
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
    notes.append('shared from em070_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))
    ents = burrow_trail(rom, ents, notes)
    # a record finds what the arc has loaded: PEL u names the shared GU files of its list 2 (em070_00_500, cm202_*), and GU's arc has them before its PEL u
    at = next(i for i, e in enumerate(ents) if e[0] == PEL_U and e[1] == efl4u2gu.T['PEL'])
    want, todo, by = set(), [p.decode('ascii') for p in re.findall(rb'effect\\[A-Za-z0-9_\\]+', dict(((e[0], e[1]), e[2]) for e in ents)[(PEL_U, efl4u2gu.T['PEL'])])], {}
    for e in ents: by.setdefault(e[0], []).append(e)
    while todo:
        p = todo.pop()
        if p in want or p not in by: continue
        want.add(p)
        for _, _, d in by[p]:
            todo += [m.decode('ascii') for m in re.findall(rb'effect\\[A-Za-z0-9_\\]+', d)]
    moved = [e for e in ents[at + 1:] if e[0] in want]
    ents = ents[:at] + moved + ents[at:at + 1] + [e for e in ents[at + 1:] if e[0] not in want]
    notes.append('effects: %d files moved before her PEL u' % len(moved))

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em070_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U em096)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em070_00, its file ID)'

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
    json.dump(dict(monster='em070_01 (Shrouded Nerscylla)', id='0x%x' % ALLOC['em_id'], registry_index=ALLOC['registry_index'],
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
