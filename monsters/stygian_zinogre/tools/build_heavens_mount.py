"""build_heavens_mount.py : Heaven's Mount (4U stage 5, m05) for MHGU, as an alias of GU stage 24 (the Ruined
Pinnacle, 10 areas) for Stygian Zinogre's three Heaven's Mount quests (notes/heavens-mount.md).

  build_heavens_mount.py [--out DIR]   write (default DIR = monsters/stygian_zinogre/romfs)
                                         DIR/nativeNX/arc/stage/m30d/{m30d,a00..a09}.arc
                                         DIR/nativeNX/loc/arc/stage/map_com/m30.arc
                                         DIR/nativeNX/sound/bgm/map/m30d/wav/m30aNNd.opus (4U str_m05 streams)
                                       report: dump/converted/em049/heavens_mount_report.json

Route = Speartip Crag's (monsters/dalamadur/tools/build_speartip.py) and the Battlequarters' (tools/stage4u2gu.py): our
arcs keep the Ruined Pinnacle's INTERNAL paths (stage\\m24d\\..., sound\\...\\m24d\\...), so every file ID GU computes
for stage 24 resolves by path hash to our resources; they ship at new RomFS paths (folder m30 = allocations.toml
stage_alias) that the core asks for while Stygian's quests run (module/stage_alias.c). The Ruined Pinnacle's own files
stay untouched. 4U m05 has 9 areas (4U area-count table 0xe087b4: stage 5 -> 9, C), GU has no 9-area stage (GU table
0x162bbe8: 2 / 10..13 only); stage 24 has 10 (C). 4U area N = GU area N for N = 0..8 (so the 4U area info SIS ships
unchanged), GU area 9 is left over: no 4U SIS exit leads there (S: unreachable), its files stay GU's.

  area arcs a00..a08 (GU m24 aNN.arc as the base):
    - main model m24aNNd <- 4U m05aNNd (stage4u2gu convert_models / build_mrl / textures)
    - set schedulers: every GU one goes with its props; 4U's take the GU slots -a00..-a04 (AREAS: the 4U area sets
      and -sky; a08 fills all 5). The 4U -col / -e0N schedulers run the "Effect" controller GU lacks: not shipped.
    - filter -f: GU's structure without its props (uBaseModels + Grass2 + MhBillboard objects placed on GU terrain),
      4U light / fog values (stage4u2gu port_filter), then 4U's lights only (filter_4u_only, Speartip's rule; GU's
      EM02 monster light stays on: memory "stage lighting"); the 4U source is the area's weather filter -f01 where it
      has one (areas 1, 5..8: port_weather, its weather cycle and storm flash), else -f
    - area SE: 4U m05aNNd bank, request, waves and call (tools/snd_area.py) replace GU's
  a09.arc: GU m24 a09.arc unchanged (the left-over area; shipped so a request for it still finds a file).
  stage arc m30d.arc (GU m24d.arc): KowareObj schedulers: the Ruined Pinnacle's 5 (a03 k01, a04 k01 / k02, a07 k01 /
    k02) dropped with their models; 4U m05a06d-k01..k04 (hit-breakable rocks, mId 1..4, mType 13 / 14 / 15 / 0) ->
    m24a06d-k01..k04; 4U m05a08d-k00 (mId 8, 12 actions, the -s00 model with ScrollCollisionSbc) -> m24a08d-k01, its
    collision files at their 4U paths in this arc (GU's KowareObj creator 0x4fe9c0 asks for k01..k04 of every area by
    file ID 0xbbdf + stage * 52 + area * 4 + k - 1). Area stream STQR bgm_m24d <- 4U str_m05 streams (sequence = area).
  map_com m30.arc (GU m24.arc): area collision (5 kinds x 9 areas; a missing 4U shell -> its main file, the m19 camp
    rule), area info SIS (4U verbatim), item pops (4U m05d), stage effect lists m24_000 / m24_100 emptied (GU's own
    empty form), whole-map offsets = 4U m05's (aMap05 0x656778 literals: W 60000, 9 records), kowareObjData = 4U
    stage-5 state table A (0x6c55d8 -> [0xfcf4c4][5]: (6, 1, 0) (6, 2, 1) (6, 3, 2) (6, 4, 3)), monster navigation:
    relation\\m24\\m24aNN regenerated from the 4U floors (stage4u2gu relation_for), point_pos / way_point of areas
    0..8 = GU's own empty forms (m24a00's), area_patrol\\_map24 emptied (GU patrol points sit on GU terrain); the
    per-area camera XFS etc\\m24aNNd-cam of areas 0..8 removed (GU rail cameras of GU terrain; the Sanctuary / 4U
    m08 ship none).
Kept GU: area 9's files, the stage SE (snd_m24d), pec_m24d, snd_fs_ase24, setItemData, stage shells, area_select\\_map24
(empty in GU). Deviations / G: see notes/heavens-mount.md.
"""
import argparse, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                          # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths                                         # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack, sbc, sdl, snd_area, snd_bgm, xfs     # noqa: E402
import stage4u2gu as s4                              # noqa: E402

A4 = 5                                               # 4U stage
N4 = 9                                               # 4U areas (0xe087b4[5])
U4 = os.path.join(ROOT, 'dump', 'm05_unpacked')      # 4U loc/data/m05*.arc unpacked (done here when missing)
U4_ARCS = ('m05',) + tuple('m05a%02d' % a for a in range(N4))
ROM4U = os.path.join(ROOT, 'dump', 'base', 'Monster Hunter 4 Ultimate (EUR) Decrypted.3ds')
GUX = os.path.join(ROOT, 'dump', 'gu_stage', 'nativeNX')
STR4U = os.path.join(ROOT, 'dump', 'romfs', 'sound', 'bgm', 'str_map', 'm05')
REPORT = os.path.join(ROOT, 'dump', 'converted', 'em049', 'heavens_mount_report.json')
STAGE, FOLDER = 24, 30                               # allocations.toml stygian_zinogre stage_alias
NGU = 10                                             # GU 0x162bbe8[24]
G = 'm%02d' % STAGE
T_MOD, T_MRL, T_TEX, T_SDL = s4.T_MOD, s4.T_MRL, s4.T_TEX, s4.T_SDL
T_SBC, T_SIS, T_STQR = s4.T_SBC, s4.T_SIS, s4.T_STQR
T_IPS, T_IPL = 0x52776ab1, 0x25fd693f
T_PEL = 0x5a525c16
T_WMAP = s4.T_WMAP
T_KOD = 0x2dd067f
T_REL = s4.T_REL
T_PP, T_WP = 0x450a16e3, 0x5f36b659                  # stage\_point_pos\mapNN\mNNaNN, stage\_way_point\...
T_PATROL = 0x0947f3c8
T_CAMX = 0x6b41a2f9                                  # stage\mNNd\mNNaNNd\etc\mNNaNNd-cam (camera XFS)
MEM4U = os.path.join(ROOT, 'dump', 'exefs_v11', 'mem.bin')     # 4U v1.1, flat from 0x100000
# 4U stage-5 map class: its +0x10 function calls 0x6c2ac8(obj, W, records, 9) at 0x656778 (the only caller with 9
# records) with the literals {records, W} at 0x65679c: W = 60000, 24-B records {s32 x, s32 z, ...}. C (values),
# S (that the class is stage 5's: the only 9-area class; build_heavens_mount_ui.py checks every SIS point lands on the
# 4U whole-map art). GU dims[24] = 60000 (0x5058d0 table +0xc0) -> whole-map k 1.0.
AMAP05_WMAP = 0x65679c
KOD_4U = 0xfcf4c4                                    # 4U state table A: u32 per stage -> {area, mId, bit} until 255
KOD_VITAL = 100                                      # G: 4U keeps no vital (mLevel 1); GU's kod use 50 / 100 / 200
PEL_EMPTY = b'PEL\0' + struct.pack('<4I', 15, 0, 0, 0)
T_SOUND = (0x79c47b59, 0x15d782fb, 0x1bcc4966, 0x2543b93e)      # GU wave, bank, request, sound call
UBASEMODEL, GRASS2, BILLBOARD = 0x45a468ee, 0x54646bac, 0x75bb7ae3
SCROLL_SBC = 0x24e6fdaf
SOUND_CTRL = 0x10163337
KOWARE_OBJ = 0x3dfe3bc2
# GU area -> (4U main model, {GU set-scheduler slot: 4U scheduler}); the 4U sets of each area arc (-col / -e0N / -f01
# are not sets: see the docstring)
AREAS = {}
for _a in range(N4):
    _sets = {0: ['a01', 'a02', 'a03', 'sky'], 4: ['a00', 'sky'], 8: ['a00', 'a01', 'a02', 'a03', 'sky']}.get(
        _a, ['a01', 'sky'])
    AREAS[_a] = ('stage\\m05d\\m05a%02dd\\m05a%02dd' % (_a, _a),
                 {'a%02d' % k: 'm05a%02dd-%s' % (_a, n) for k, n in enumerate(_sets)})
# KowareObj: GU slot path -> (4U scheduler, mId, area)
KOBJ = {'stage\\%sd\\%sa06d\\sdl\\%sa06d-k%02d' % (G, G, G, k): ('stage\\m05d\\m05a06d\\sdl\\m05a06d-k%02d' % k, k, 6)
        for k in (1, 2, 3, 4)}
KOBJ['stage\\%sd\\%sa08d\\sdl\\%sa08d-k01' % (G, G, G)] = ('stage\\m05d\\m05a08d\\sdl\\m05a08d-k00', 8, 8)
# The camp model m05a00d carries two alternative mesh groups with matching wall-collision parts: group / w00 part 1 =
# a boulder on the path to the exit (rock01 x 839..2464, z 456..1704; SIS exit to area 1 at (4400, 1500)), group /
# part 2 = a rock, cloth and cards at the back (x -2733..-1180, z -2576..-984). 4U's stage-5 area loader 0x656598
# (its set list 0xecca14: m05a00d-a01..a03, so the m05 class, C) ends with `if area == 0: 0x6c2f34(stage, 0, 1, 0)`
# on every camp load, no other condition: 0x6c2f34(stage, area, n, on) sets model group bit n (stage+0x64 ..+0x108)
# and collision part n to `on`, part n + 1 to !on -> group 1 hidden, part 1 off, part 2 on (C). Both were left on
# (issue 7: camp exit blocked). Group 1's meshes are left out, part 1 dropped from the camp collision (sbc.drop_parts).
HIDDEN_GROUPS = {0: {1}}                             # 4U area -> mesh groups the 4U code always hides
HIDDEN_PARTS = {0: {1}}                              # 4U area -> collision part ids it always switches off
ITEM_POPS = {('stage\\%sd\\%sd' % (G, G), T_IPS): 'stage\\m05d\\m05d',
             ('stage\\%sd\\%sd_low' % (G, G), T_IPL): 'stage\\m05d\\m05d',
             ('stage\\%sd\\%sd_high' % (G, G), T_IPL): 'stage\\m05d\\m05d_high',
             ('stage\\%sd\\%sd_g' % (G, G), T_IPL): 'stage\\m05d\\m05d_g'}
# Speartip's lighting rule (memory "stage lighting"): after port_filter, GU-only light objects that 4U's filter lacks
# are switched off (Draw 0), the screen filters both games have take every 4U track; EM02-InfiniteLight stays on;
# PL01..03 / StableShadow / StageDataSet stay GU's. AmbientLight stays ON (issue 7: with it off every surface out of
# direct light was pure black, here and on Speartip Crag): it is GU's ambient term (mGroup 5, mMode 3, the system
# DefaultCube_CM env cube, no host-terrain data), not an extra light; 4U's ambient comes from its hemisphere light
# MhFilter (GU's main height / distance gradient, pale grey, lens flare on) is off where 4U's filter has none (areas 2
# and 7; issue 7: it washed area 2's distant forest cards into pale slabs). Where 4U has one, it takes every 4U
# track (SAME_FILTERS), its blend state too: 4U m05 uses mBreandState 0 (a GU value: 6 GU MhFilter + 65 MhFilter_top
# filters), GU's 15 under 4U's alpha-0.5 cyan colours tinted areas 0 / 2..4 (issue 7, test 2026-10-29: "too much cyan")
# s2-InfiniteLight carries 4U's s2 (port_filter) and is off where 4U has none (areas 3, 5, 6): stage4u2gu STAGE_LIGHTS
# Bloom mThrethold stays GU's (0.9 on every GU stage sampled; 4U's 0.5 in GU's renderer blew the floors out white,
# issue 7, G)
GU_ONLY_OFF = ('DEF02-InfiniteLight', 's2-InfiniteLight', 'GodRaysFilter', 'MhFilter_top', 'MhFilter_bottom',
               'MhFilter')
SAME_FILTERS = ('BloomFilter', 'ColorCorrectFilter', 'MhFilter')
GU_TRACKS = ('mThrethold',)


def gu_file(rel):
    """a GU base-RomFS file under dump/gu_stage (extracted when missing)"""
    p = os.path.join(GUX, rel)
    if not os.path.exists(p):
        from romfs import RomFS
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(RomFS(paths.GU_ROMFS).read('/nativeNX/' + rel))
    return open(p, 'rb').read()


def unpack_4u():
    """4U arcs -> U4/<arc>/<path>.<type> (tools/arcpack.py unpack layout, read by stage4u2gu.u4_find); the arcs come
    from dump/romfs/loc/data (extracted from the 4U ROM with tools/ctr.py x when missing)"""
    src = os.path.join(ROOT, 'dump', 'romfs', 'loc', 'data')
    if not all(os.path.exists(os.path.join(src, a + '.arc')) for a in U4_ARCS):
        import subprocess
        subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'ctr.py'), 'x', ROM4U,
                        r'^/(loc/data/m05|sound/bgm/str_map/m05/)', os.path.join(ROOT, 'dump', 'romfs')], check=True)
    for a in U4_ARCS:
        out = os.path.join(U4, a)
        if os.path.exists(os.path.join(out, '_order.txt')): continue
        ver, ents = arcpack.read(open(os.path.join(src, a + '.arc'), 'rb').read())
        order = []
        for path, th, data in ents:
            rel = path.replace('\\', '/') + '.%08x' % th
            os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
            open(os.path.join(out, rel), 'wb').write(data)
            order.append(rel)
        open(os.path.join(out, '_order.txt'), 'w').write(''.join(r + '\n' for r in order))


def u4(path, typ):
    return s4.u4_find(path, typ)


def u4_has(path, typ):
    try:
        u4(path, typ)
        return True
    except KeyError:
        return False


def filter_4u_only(gd, u4d):
    g, u = sdl.parse(gd), sdl.parse(u4d)
    go = {n: (c, tr) for i, n, c, tr in sdl.objects(g)}
    uo = {n: (c, tr) for i, n, c, tr in sdl.objects(u)}
    done = []
    for n in GU_ONLY_OFF:
        if n in go and n not in uo and 'Draw' in go[n][1]:
            t = go[n][1]['Draw']
            sdl.set_values(g, t, [0] * len(t['times']))
            done.append('%s.Draw=0' % n)
    for n in SAME_FILTERS:
        if n not in go or n not in uo: continue
        (gc, gt), (uc, ut) = go[n], uo[n]
        assert gc == uc, (n, hex(gc), hex(uc))
        for k, e in ut.items():
            if k in gt and k not in GU_TRACKS and gt[k]['kind'] == sdl.KIND_4U_TO_GU[e['kind']]:
                sdl.set_values(g, gt[k], sdl.values(u, e), times=e['times'])
                done.append('%s.%s' % (n, k))
    return sdl.build(g), done


# 4U areas 1, 5..8 ship a second filter -f01 = the area's weather cycle (1000 frames; StageDataSet Weather-state1 0..100
# clear = -f's values, change 100..300, state2 300..400 storm: light 1.5 -> 1.0, gradient filter on, fog / bloom /
# colour keys, colour corrector 3 (type 6) on at 200..300 = the flash; back 400..600) (C, values). GU runs the same
# system: its m24 areas 1, 2, 5..8 carry StageDataSet Weather-* keys over a 600-frame -f (C, scan of GU's stage
# filters: 15 stages). So the GU -f takes -f01 where 4U has one: the shared light / fog / gradient / bloom tracks with
# their 4U keys (port_filter, filter_4u_only), then here the scheduler length, the Weather-* keys, the gradient filter's
# state / position keys and every 4U colour corrector (GU's area 1 has 2, 4U's 4: GU's last element cloned).
WEATHER_TRACKS = ('mBreandState', 'mTopPos', 'mBottomPos')


def array_elements(s, obj, name):
    """[(element entry index, {track name: entry})] of array `name` under object entry `obj`"""
    ents = s['ents']
    return [(i, {t['name']: t for t in ents if t['parent'] == i and t['kind'] not in (1, 2, 3, 4, 5)})
            for i, e in enumerate(ents) if e['kind'] == 5 and e['parent'] == obj and e['name'] == name]


def clone_element(s, elem):
    """insert a copy of array element entry `elem` (with its tracks) right after its last track; later track / array
    parents and classref values renumbered (as sdl.remove_objects)"""
    ents, cref = s['ents'], sdl.CREF_KIND[s['ver']]
    tracks = [i for i, e in enumerate(ents) if e['parent'] == elem and e['kind'] not in (1, 2, 3, 4, 5)]
    at = (tracks[-1] if tracks else elem) + 1
    k = 1 + len(tracks)
    for e in ents:
        if e['kind'] not in (1, 2, 3, 4) and e['parent'] >= at: e['parent'] += k
        if e['kind'] == cref and e['values'] is not None:
            w = struct.unpack_from('<%dI' % len(e['times']), e['values'])
            e['values'] = struct.pack('<%dI' % len(w), *[v + k if v >= at else v for v in w])
    new = [dict(ents[elem])] + [dict(ents[i], parent=at) for i in tracks]
    for t in new[1:]:
        t['times'] = list(t['times']) if t['times'] is not None else None
    s['ents'] = ents[:at] + new + ents[at:]


def port_weather(gd, u4d):
    g, u = sdl.parse(gd), sdl.parse(u4d)
    done = ['frames %d -> %d' % (g['frames'], u['frames'])]
    g['frames'] = u['frames']

    def copy(gt, ut, keys, what):
        for k in keys:
            if k in gt and k in ut and gt[k]['kind'] == sdl.KIND_4U_TO_GU[ut[k]['kind']]:
                sdl.set_values(g, gt[k], sdl.values(u, ut[k]), times=ut[k]['times'])
                done.append('%s.%s' % (what, k))
    go = {n: (i, tr) for i, n, c, tr in sdl.objects(g)}
    uo = {n: (i, tr) for i, n, c, tr in sdl.objects(u)}
    ut = uo['StageDataSet'][1]
    assert any(k.startswith('Weather-') for k in go['StageDataSet'][1]), 'GU area without weather keys'
    copy(go['StageDataSet'][1], ut, [k for k in ut if k.startswith('Weather-')], 'StageDataSet')
    if 'MhFilter' in go and 'MhFilter' in uo:
        copy(go['MhFilter'][1], uo['MhFilter'][1], WEATHER_TRACKS, 'MhFilter')
    if 'ColorCorrectFilter' not in go or 'ColorCorrectFilter' not in uo:
        return sdl.build(g), done
    gi, ui = go['ColorCorrectFilter'][0], uo['ColorCorrectFilter'][0]
    ue = array_elements(u, ui, 'mCorrector')
    while len(array_elements(g, gi, 'mCorrector')) < len(ue):
        clone_element(g, array_elements(g, gi, 'mCorrector')[-1][0])
        done.append('ColorCorrectFilter.mCorrector cloned')
    for (_, gt), (_, utr) in zip(array_elements(g, gi, 'mCorrector'), ue):
        copy(gt, utr, list(utr), 'mCorrector')
    return sdl.build(g), done


def camcheck_drawmode(ns):
    for i, n, c, tr in sdl.objects(ns):
        if c == s4.USTAGESET and 'mCameraCheck' in tr and 'mDrawMode' in tr and sdl.values(ns, tr['mCameraCheck'])[0]:
            sdl.set_values(ns, tr['mDrawMode'],
                           [s4.DRAWMODE_CAMCHECK.get(v, v) for v in sdl.values(ns, tr['mDrawMode'])])


def models_textures(models):
    out = []
    for p, r, m, t in models:
        out += [x for x in t if x not in out]
    return out


def ordered(ents, drop_models, new_textures, new_models, tail):
    """build_speartip.ordered: GU entries minus the dropped models and every texture no kept MRL uses, then kept GU
    textures, ours, kept GU materials / models, ours (TEX -> MRL -> MOD), the rest of GU's, then `tail`"""
    kept = [e for e in ents if not (e[1] in (T_MOD, T_MRL) and e[0] in drop_models)]
    used = set()
    for p, t, d in kept:
        if t == T_MRL: used.update(s4.mrl_textures(d))
    tex = [e for e in kept if e[1] == T_TEX and e[0] in used and e[0] not in new_textures]
    out = tex + [(p, T_TEX, s4.convert_texture(p)) for p in new_textures]
    out += [e for e in kept if e[1] in (T_MRL, T_MOD)]
    for p, r, m, t in new_models:
        out += [(p, T_MRL, r), (p, T_MOD, m)]
    out += [e for e in kept if e[1] not in (T_TEX, T_MRL, T_MOD)]
    return out + tail, len([e for e in ents if e[1] == T_TEX]) - len(tex)


def props_of(ns, rep):
    """models of a converted scheduler -> [(path, mrl, mod, textures)]; collision resources -> [(path, SBC)]
    (converted at their 4U paths); anything else is reported (no model, no collision: G)"""
    models, cols = [], []
    for p in sdl.resource_paths(ns):
        if '\\collision\\' in p and u4_has(p, T_SBC):
            cols.append((p, T_SBC, sbc.convert_4u(u4(p, T_SBC))))
        elif u4_has(p, T_MOD):
            pm, pr, pt, prow = s4.convert_prop(p, solid_alpha=True)
            models.append((p, pr, pm, pt))
        else:
            rep.setdefault('unresolved_resources', []).append(p)
    return models, cols


def area_sound(k, ents, log):
    new = snd_area.convert_area(k, 'a%02d' % k, True, log, u4=U4, s4='m05', sg=G)
    mine = ('sound\\se\\map\\%sd\\%sa%02dd\\' % (G, G, k), 'sound\\call\\map\\%sd\\%sa%02dd' % (G, G, k))
    gone = [e for e in ents if e[1] in T_SOUND and e[0].startswith(mine)]
    return [e for e in ents if e not in gone] + new, '%d GU entries -> %d (4U m05a%02dd)' % (len(gone), len(new), k)


def build_area(k, rep):
    g, a4 = '%sa%02dd' % (G, k), 'm05a%02dd' % k
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/a%02d.arc' % (G, k)))
    main4, sets4 = AREAS[k]
    gmain = 'stage\\%sd\\%s\\%s' % (G, g, g)
    d4, mrl4 = u4(main4, T_MOD), u4(main4, T_MRL)
    hide = HIDDEN_GROUPS.get(k, set())
    gmod, mats = s4.convert_models([(d4, '')], drop_groups=hide, solid_alpha=s4.alpha_tested_4u(mrl4))
    s4.check_model(gmod, [d4], drop_groups=hide)
    gmrl, texs, rows = s4.build_mrl(mats, {0: mrl4})
    models = [(gmain, gmrl, gmod, texs)]
    r = rep['a%02d' % k] = dict(model=gmain, source=main4, meshes=len(mats), materials=len(rows))
    drop = {gmain}
    gsets = [(p, d) for p, t, d in ents if t == T_SDL and re.search(r'-a0\d$', p)]
    for p, d in gsets:
        drop |= set(sdl.resource_paths(sdl.parse(d)))
    ents = [e for e in ents if not (e[1] == T_SDL and re.search(r'-a0\d$', e[0]))]
    tail = []
    r['sets'] = {}
    for slot, n4 in sets4.items():
        ns = sdl.parse(sdl.convert_4u(u4('stage\\m05d\\%s\\sdl\\%s' % (a4, n4), T_SDL), drop_ctrl=s4.sdl_drop_ctrl,
                                      drop_keyless=True))
        camcheck_drawmode(ns)
        ms, cols = props_of(ns, r)
        assert not cols, (n4, 'a set scheduler with collision', cols)
        models += ms
        tail.append(('stage\\%sd\\%s\\sdl\\%s-%s' % (G, g, g, slot), T_SDL, sdl.build(ns)))
        r['sets'][slot] = dict(source=n4, objects=len(sdl.objects(ns)), props=[m[0] for m in ms])
    r['dropped_gu_sets'] = [p for p, d in gsets]
    fpath = 'stage\\%sd\\%s\\sdl\\%s-f' % (G, g, g)
    k_f = [i for i, e in enumerate(ents) if e[0] == fpath and e[1] == T_SDL][0]
    fs = sdl.parse(ents[k_f][2])
    props = set(sdl.resource_paths(fs))
    gone = sdl.remove_objects(fs, lambda c, n: c in (UBASEMODEL, GRASS2, BILLBOARD))
    drop |= props - set(sdl.resource_paths(fs))
    f01 = 'stage\\m05d\\%s\\sdl\\%s-f01' % (a4, a4)
    weather = u4_has(f01, T_SDL)
    f4 = u4(f01 if weather else 'stage\\m05d\\%s\\sdl\\%s-f' % (a4, a4), T_SDL)
    fd, done = s4.port_filter(sdl.build(fs), f4)
    fd, own = filter_4u_only(fd, f4)
    wx = []
    if weather: fd, wx = port_weather(fd, f4)
    ents[k_f] = (fpath, T_SDL, fd)
    r['filter'] = dict(dropped_objects=gone, ported=len(done), lights_4u_only=own, source='-f01' if weather else '-f',
                       weather=wx)
    ents, r['sound'] = area_sound(k, ents, r.setdefault('sound_log', []))
    out, ndrop = ordered(ents, drop, models_textures(models), models, tail)
    r['dropped_gu'] = dict(models=len(drop), textures=ndrop)
    return out


def se_tracks(d):
    """SoundControl mSdlSeReqArea tracks of a converted scheduler: [(entry index, values)]"""
    s = sdl.parse(d)
    out, ctrl = [], None
    for i, e in enumerate(s['ents']):
        if e['kind'] == 3: ctrl = e['x']
        elif e['kind'] in (1, 2, 4): ctrl = None
        elif ctrl == SOUND_CTRL and e['name'] == 'mSdlSeReqArea' and e['times'] is not None:
            out.append((i, sdl.values(s, e)))
    return out


def build_stage_arc(streams, rep):
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/%sd.arc' % (G, G)))
    rows = []; drop = set()
    gu_k = [(p, d) for p, t, d in ents if t == T_SDL and re.search(r'-k0\d$', p)]
    for p, d in gu_k:
        drop |= set(sdl.resource_paths(sdl.parse(d)))
    ents = [e for e in ents if not (e[1] == T_SDL and re.search(r'-k0\d$', e[0]))]
    models, tail, cols = [], [], []
    for gp, (p4, mid, area) in KOBJ.items():
        # SoundControl area tracks: 4U area = GU area here (same numbering), so the count only feeds the assert
        n_se = len(se_tracks(sdl.convert_4u(u4(p4, T_SDL), drop_ctrl=lambda c, n: c == s4.EFFECT_CTRL,
                                            drop_keyless=True)))
        sd = s4.convert_kobj(p4, mid, n_se, se_area=(area, area))
        ns = sdl.parse(sd)
        ms, cs = props_of(ns, rep)
        models += ms
        cols += [c for c in cs if c[0] not in [x[0] for x in cols]]
        tail.append((gp, T_SDL, sd))
        objs = [(n, hex(c)) for i, n, c, tr in sdl.objects(ns)]
        rows.append((gp, p4, 'mId %d' % mid, [m[0] for m in ms], [c[0] for c in cs], objs))
    ents = [(p, t, streams if t == T_STQR else d) for p, t, d in ents]
    out, ndrop = ordered(ents, drop, models_textures(models), models, cols + tail)
    rep['stage_arc'] = dict(kobj=rows, dropped_gu_kobj=[p for p, d in gu_k], dropped_gu_models=sorted(drop),
                            dropped_gu_textures=ndrop)
    return out


def collision_4u(area, kind):
    """4U m05aNNd collision of one kind; a missing shell -> the main file of its family"""
    for kk in (kind, kind.replace('-shell', '')):
        p = 'stage\\m05d\\%s\\collision\\%s-a-%s' % (area, area, kk)
        if u4_has(p, T_SBC):
            return kk, u4(p, T_SBC)
    raise SystemExit('4U collision %s %s missing' % (area, kind))


# SIS exit record +00 (u32 / f32 "type"): 0 on every 4U m05 exit but the camp's (m05a00d -> 1: 1.0, the only nonzero
# value in the 38 exits of 4U m05 / m08 / m19, C). GU uses 1.0 on 14 of 478 exits (m01a08d / a09d, m12a01d / a08d,
# m13a03d, m11a09d, m06a10d), each one on a climbable wall (floor groups w0 0x7d / 0x5d, w2 0x10 inside the zone, C):
# S, GU = an exit taken while climbing. The camp has no climbable surface near its zone (4400, 0, 1500) r 3000 and the
# hunter walked into it without a transition (issue 7, user 2026-10-29), so a 1.0 exit is written as a walking exit
# (0). What 4U's 1.0 means is not traced (G).
def exits_walkable(d):
    import sis
    s = sis.parse(d); n = 0
    for r in s['sec'][1]:
        if struct.unpack_from('<f', r, 0)[0] == 1.0:
            struct.pack_into('<f', r, 0, 0.0); n += 1
    return sis.write(s), '; %d climb-type exit(s) -> walking' % n if n else ''


def wholemap_4u():
    m = open(MEM4U, 'rb').read()
    u = lambda a: struct.unpack_from('<I', m, a - 0x100000)[0]
    recs = u(AMAP05_WMAP)
    return u(AMAP05_WMAP + 4), [struct.unpack_from('<2i', m, recs + 24 * a - 0x100000) for a in range(N4)]


def wholemap_offsets(d):
    """GU whole-map records (f32, u32 n, n x 20 B {s32 x, s32 z, ...}) with 4U m05's offsets for areas 0..8 (area 9
    keeps GU's: no 4U area)"""
    w, offs = wholemap_4u()
    b = bytearray(d)
    assert struct.unpack_from('<I', b, 4)[0] == NGU and len(b) == 8 + 20 * NGU, len(b)
    for a, o in enumerate(offs):
        struct.pack_into('<2i', b, 8 + 20 * a, *o)
    return bytes(b), 'whole-map offsets -> 4U m05 %s (W %d)' % (offs, w)


def kod_4u():
    m = open(MEM4U, 'rb').read()
    p = struct.unpack_from('<I', m, KOD_4U + 4 * A4 - 0x100000)[0]
    out = []
    while m[p - 0x100000] != 255:
        out.append(tuple(m[p - 0x100000:p - 0x100000 + 3])); p += 3
    return out


def build_kod(d):
    ver, n = struct.unpack_from('<fI', d, 0)
    old = [struct.unpack_from('<4BH', d, 8 + 6 * i) for i in range(n)]
    rows = [(a, mid, bit, 0, KOD_VITAL) for a, mid, bit in kod_4u()]
    assert rows and all(r[0] == 6 for r in rows), rows
    return struct.pack('<fI', ver, len(rows)) + b''.join(struct.pack('<4BH', *r) for r in rows), (old, rows)


def empty_xfs_array(d):
    root = xfs.parse(d)
    arr = root['RouteFindDataResource']['mpArray']
    n = len(arr) if isinstance(arr, list) else 1
    root['RouteFindDataResource']['mpArray'] = []
    out = xfs.build(d, root)
    assert xfs.parse(out)['RouteFindDataResource']['mpArray'] == []
    return out, n


# Monster entry / exit points (stage\_point_pos\map24\m24aNN; GU header 'RPP\0', u32 version, u32 count, then 32-B
# records: +0 f32 x y z, +12 u16 flags, +18 u16 variant, +20 f32 radius, +24 s16 angle (deg), +26 u8 other area,
# +28 u32 group mask. C from GU m24's files and the readers (point object +0x10 pos, +0x20 angle, +0x22 area, +0x24
# radius, +0x28 flags, +0x2e variant, +0x30 mask). Move type 2 (Zinogre, area_act_tbl entry 44: [2, 2, 6, 5], group 0):
#   exit 0xb3640: the current area's point with flags bit 1 (2), area = next, variant = the asked one (0 = the edge the
#     route follower 0x97130 walks to, 2 = the far point of the exit script; 0x8f460);
#   entry 0xb3e4c: the next area's point with flags bit 0 (1), area = the area left, variant 0 (the far point he comes
#     in from; variant 2 = the edge, as GU's pairs).
# No point found leaves the position as it was (no write): with empty files he entered area 7 at his area-6
# coordinates (test 2026-10-28, icon off the map). So per 4U neighbour (the alias graph of build_em057_01_arc.py): far =
# the 4U SIS exit centre toward it, edge = the 4U SIS arrival from it (hunters'; 4U keeps no monster points, S), as
# GU's 4-record pattern; radius 500 and mask 0xffffffff (every group) as GU's commonest values. One more record per area
# = GU's flags-0x34 form (types 0 / 1 / 5 / 6 / 8: flyers' fixed point, no area): the arrival nearest the arrivals'
# centroid. Areas 0 / 9: the empty form.
PP_HEAD = b'RPP\0' + struct.pack('<I', 0x0133776f)


def area_graph():
    """4U Heaven's Mount area graph {area: sorted neighbours} over areas 1..8, made two-way (as alias_graph)"""
    import sis
    g = {}
    for a in range(N4):
        recs = sis.parse(u4('stage\\m05d\\m05a%02dd\\m05a%02dd-info' % (a, a), T_SIS))['sec'][1]
        g[a] = sorted({r[17] for r in recs} - {a})
    for a in list(g):
        for b in g[a]:
            if a not in g[b]: g[b] = sorted(g[b] + [a])
    return {a: [b for b in ns if b] for a, ns in g.items() if a}


def point_pos_4u(a, graph):
    """point_pos of area a (1..8) -> (file, what)"""
    import sis
    s = sis.parse(u4('stage\\m05d\\m05a%02dd\\m05a%02dd-info' % (a, a), T_SIS))['sec']
    exits, arrs = {}, {}
    for r in sorted(s[1], key=lambda r: r[16]):
        exits.setdefault(r[17], struct.unpack_from('<3f', r, 4))
    for r in sorted(s[2], key=lambda r: r[16]):
        arrs.setdefault(r[17], (struct.unpack_from('<3f', r, 4), struct.unpack_from('<H', r, 18)[0]))
    deg = lambda u: (u * 360 + 32768) // 65536 % 360

    def rec(pos, flags, var, ang, other):
        return struct.pack('<3fHHHHfhBBI', *pos, flags, 0, 0, var, 500.0, (ang + 180) % 360 - 180, other, 0,
                           0xffffffff)
    recs, what = [], []
    for b in graph[a]:
        edge, face = arrs[b] if b in arrs else (exits[b], None)
        far = exits.get(b, edge)
        if face is None:   # no 4U arrival from b: face from the exit toward the area (atan2 on x / z, GU yaw sense)
            import math
            face = int(math.atan2(edge[0] - far[0], edge[2] - far[2]) / math.pi * 32768) & 0xffff
        ang = deg(face)
        recs += [rec(far, 1, 0, ang, b), rec(edge, 1, 2, ang, b), rec(edge, 2, 0, ang + 180, b),
                 rec(far, 2, 2, ang + 180, b)]
        what.append('%d%s%s' % (b, '' if b in arrs else ' (no arrival)', '' if b in exits else ' (no exit)'))
    pts = [p for p, _ in arrs.values()]
    c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
    p, u = min(arrs.values(), key=lambda pu: sum((pu[0][k] - c[k]) ** 2 for k in range(3)))
    recs.append(struct.pack('<3fHHHHfhBBI', *p, 0x34, 0, 0, 2, 500.0, (deg(u) + 180) % 360 - 180, 0, 0, 0xffffffff))
    return (PP_HEAD + struct.pack('<I', len(recs)) + b''.join(recs),
            'point_pos: %d 4U points, entry / exit for areas %s + one fixed point' % (len(recs), ', '.join(what)))


def build_map_com(rep):
    ver, ents = arcpack.read(gu_file('loc/arc/stage/map_com/%s.arc' % G))
    E = {(p, t): d for p, t, d in ents}
    empty_pp = E[('stage\\_point_pos\\map%d\\%sa00' % (STAGE, G), T_PP)]
    empty_wp = E[('stage\\_way_point\\map%d\\%sa00' % (STAGE, G), T_WP)]
    assert len(empty_pp) == 12 and len(empty_wp) == 153, (len(empty_pp), len(empty_wp))
    graph = area_graph()
    g00 = {}
    rows = []; out = []; seen = set(); dropped = []
    area_rx = '|'.join('%02d' % a for a in range(N4))
    for p, t, d in ents:
        name = p.split('\\')[-1]
        m = re.match(r'%sa(%s)d-a-(.*)$' % (G, area_rx), name)
        if t == T_SBC and m:
            a4 = 'm05a%sd' % m.group(1)
            src, d4 = collision_4u(a4, m.group(2))
            d = sbc.drop_parts(sbc.convert_4u(d4), HIDDEN_PARTS.get(int(m.group(1)), set()))
            s = sbc.parse(d)
            if m.group(2) == 'g00': g00[int(m.group(1))] = d
            rows.append((p, a4 + '-a-' + src, len(s['parts']), s['nA'], s['nB'], s['nC']))
        elif t == T_SIS and re.match(r'%sa(%s)d-info$' % (G, area_rx), name):
            a = name[4:6]
            d, walk = exits_walkable(u4('stage\\m05d\\m05a%sd\\m05a%sd-info' % (a, a), T_SIS))
            rows.append((p, 'm05a%sd-info (verbatim: same area numbers%s)' % (a, walk)))
        elif (p, t) in ITEM_POPS:
            d = u4(ITEM_POPS[(p, t)], t)
            rows.append((p, ITEM_POPS[(p, t)] + ' (4U item pops)'))
        elif t == T_PEL and re.match(r'effect\\pel\\st\\%s_[01]00$' % G, p):
            assert d[:16] == PEL_EMPTY[:16], p
            rows.append((p, 'emptied (%d Ruined Pinnacle stage effects; 4U m05 has no effect list)' %
                         struct.unpack_from('<I', d, 16)[0]))
            d = PEL_EMPTY
        elif t == T_WMAP and p == 'stage\\%sd\\%sd' % (G, G):
            d, what = wholemap_offsets(d)
            rows.append((p, what))
        elif t == T_KOD:
            d, (old, new) = build_kod(d)
            rows.append((p, 'kod %s -> 4U stage-5 table A %s' % (old, new)))
        elif t == T_PP and re.match(r'%sa(%s)$' % (G, area_rx), name):
            a = int(name[-2:])
            if a in graph:
                assert d[:8] == PP_HEAD, p
                d, what = point_pos_4u(a, graph)
                rows.append((p, what))
            else:
                rows.append((p, 'point_pos %d B -> GU empty form' % len(d)))
                d = empty_pp
        elif t == T_WP and re.match(r'%sa(%s)$' % (G, area_rx), name):
            rows.append((p, 'way_point %d B -> GU empty form' % len(d)))
            d = empty_wp
        elif t == T_PATROL:
            d, n = empty_xfs_array(d)
            rows.append((p, 'area_patrol: %d GU patrol records removed' % n))
        elif t == T_CAMX and re.match(r'%sa(%s)d-cam$' % (G, area_rx), name):
            dropped.append(p)
            continue
        elif t == T_REL:
            continue                                  # regenerated below
        else:
            out.append((p, t, d))
            continue
        seen.add((p, t))
        out.append((p, t, d))
    # relation tables: GU ships m24a01..a08; regenerated from the 4U floors with GU's convention (stage4u2gu
    # relation_for), template = GU's own table of the same area
    rel = []
    for p, t, d in ents:
        if t != T_REL: continue
        a = int(p[-2:])
        if a in g00:
            d, what = s4.relation_for(g00[a], d)
            rel.append((p, 'm05a%02dd floors: %s' % (a, what)))
        out.append((p, t, d))
    rep['map_com'] = rows + rel
    rep['map_com_dropped'] = dropped
    assert len([r for r in rows if r[0].endswith(('-g00', '-w00', '-g00-shell', '-w00-shell', '-cam'))]) == 5 * N4
    assert len(rel) == N4 - 1, rel
    return out


def stq4u(path):
    """4U STRQ: streams [wav names by order], {sequence id: (stream index, dB)}"""
    d = open(path, 'rb').read()
    ns, nq = struct.unpack_from('<II', d, 8)
    out = {}
    for o in range(0x18 + 36 * ns, 0x18 + 36 * ns + 100 * nq, 100):
        out[struct.unpack_from('<I', d, o)[0]] = (struct.unpack_from('<I', d, o + 92)[0],
                                                  struct.unpack_from('<f', d, o + 36)[0])
    return ns, out


def build_streams(outroot, rep):
    """4U str_m05 area streams -> GU opus (m30d paths) + the stage STQR (GU m24's sequences: id = area; ours point at
    the 4U stream of the same 4U sequence id). 4U: 8 streams = a00d a01d a02d a03d a05d a06d a07d + rain (stream 7,
    sequence 20, unused); areas 4 / 8 reuse a03d / a01d (C, str_m05.stq). GU sequences 9 / 10 (no 4U area) -> the
    a01d stream (G: never played); 0x32 (m24cmpd, one-shot) keeps GU's own stream. Level = 4U dB + the median
    battle-theme delta (tools/snd_bgm.py levels), as Speartip's"""
    log = []
    med, _ = snd_bgm.levels(log)
    ns4, q4 = stq4u(os.path.join(STR4U, 'str_m05.stq'))
    wavs = sorted(f[:-4] for f in os.listdir(os.path.join(STR4U, 'wav')) if f.endswith('.mca'))
    assert wavs == ['m05_a%02dd' % a for a in (0, 1, 2, 3, 5, 6, 7)] and ns4 == 8, (wavs, ns4)
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/%sd.arc' % (G, G)))
    base = [d for p, t, d in ents if t == T_STQR][0]
    s = snd_bgm.stqr_parse(base)
    assert snd_bgm.stqr_build(s) == base, 'bgm_m24d.stqr does not rebuild byte-identically'
    gstreams = s['streams']
    cmp_i = [i for i, x in enumerate(gstreams) if x[0].endswith('m24cmpd')]
    assert len(cmp_i) == 1, gstreams
    streams = []; idx4 = {}
    for si, wav in enumerate(wavs):
        path = 'sound\\bgm\\map\\m%02dd\\wav\\m%02d%sd' % (FOLDER, FOLDER, wav[3:-1])
        log.append(path)
        opus, n, ls, le, rms = snd_bgm.convert_track(open(os.path.join(STR4U, 'wav', wav + '.mca'), 'rb').read(), log)
        f = os.path.join(outroot, 'nativeNX', path.replace('\\', '/') + '.opus')
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, 'wb').write(opus)
        streams.append([path, len(opus), n, 2, snd_bgm.RATE, ls, le, snd_bgm.STREAM_HASH, 0])
        idx4[si] = si
    streams.append(gstreams[cmp_i[0]])
    cmp_new = len(streams) - 1
    s['streams'] = streams
    seqs = []
    for q in s['seqs']:
        q = bytearray(q)
        sid = struct.unpack_from('<I', q, 0)[0]
        if sid == 0x32:
            struct.pack_into('<I', q, 92, cmp_new)
        else:
            k4, db = q4[sid] if sid in q4 and sid < N4 else q4[1]
            struct.pack_into('<I', q, 92, idx4[k4])
            struct.pack_into('<f', q, 36, db + med)
        seqs.append(bytes(q))
    s['seqs'] = seqs
    out = snd_bgm.stqr_build(s)
    chk = snd_bgm.stqr_parse(out)
    assert [x[0] for x in chk['streams']] == [x[0] for x in streams]
    rep['streams'] = dict(log=log, sequences=[(hex(struct.unpack_from('<I', q, 0)[0]),
                                               struct.unpack_from('<I', q, 92)[0],
                                               round(struct.unpack_from('<f', q, 36)[0], 2)) for q in seqs])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=paths.romfs('stygian_zinogre'))
    a = ap.parse_args()
    unpack_4u()
    s4.set_source(U4, 'm05')
    s4.VCOL_FLOOR = 0.15                             # issue 7: surfaces with 4U vertex RGB 0 were pure black
    s4.STAGE_LIGHTS = True                           # issue 7: 4U's hemisphere light -> GU AmbientLight
    rep = {}
    sdir = os.path.join(a.out, 'nativeNX', 'arc', 'stage', 'm%02dd' % FOLDER)
    os.makedirs(sdir, exist_ok=True)
    for k in AREAS:
        ents = build_area(k, rep)
        open(os.path.join(sdir, 'a%02d.arc' % k), 'wb').write(arcpack.build(ents))
        r = rep['a%02d' % k]
        print('built a%02d.arc: %d entries (%s); sets %s; unresolved %s' % (
            k, len(ents), r['sound'], {s: v['source'] for s, v in r['sets'].items()}, r.get('unresolved_resources')),
            flush=True)
    for k in range(N4, NGU):
        open(os.path.join(sdir, 'a%02d.arc' % k), 'wb').write(gu_file('arc/stage/%sd/a%02d.arc' % (G, k)))
        print('a%02d.arc: GU m24 a%02d.arc unchanged (no 4U area)' % (k, k))
    stqr = build_streams(a.out, rep)
    ents = build_stage_arc(stqr, rep)
    open(os.path.join(sdir, 'm%02dd.arc' % FOLDER), 'wb').write(arcpack.build(ents))
    print('built m%02dd.arc: %d entries, kobj %s, dropped GU kobj %s' % (
        FOLDER, len(ents), [r[:5] for r in rep['stage_arc']['kobj']], rep['stage_arc']['dropped_gu_kobj']))
    print('stream sequences (id, stream, dB):', rep['streams']['sequences'])
    mp = os.path.join(a.out, 'nativeNX', 'loc', 'arc', 'stage', 'map_com', 'm%02d.arc' % FOLDER)
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    ents = build_map_com(rep)
    open(mp, 'wb').write(arcpack.build(ents))
    print('built map_com m%02d.arc: %d entries (dropped GU cameras %s)' % (FOLDER, len(ents), rep['map_com_dropped']))
    for row in rep['map_com']: print('  ', *row)
    if rep.get('unresolved_resources'): print('UNRESOLVED kobj resources:', rep['unresolved_resources'])
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(rep, open(REPORT, 'w'), indent=1, default=str)
    print('report:', os.path.relpath(REPORT, ROOT))


if __name__ == '__main__':
    main()
