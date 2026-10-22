"""build_speartip.py : Speartip Crag (4U stage 8, m08) for MHGU, as an alias of GU stage 18 (the Sanctuary, 2 areas).

  build_speartip.py [--out DIR]     write (default DIR = monsters/dalamadur/romfs)
                                      DIR/nativeNX/arc/stage/m29d/{m29d,a00,a01}.arc
                                      DIR/nativeNX/loc/arc/stage/map_com/m29.arc
                                      DIR/nativeNX/sound/bgm/map/m29d/wav/m29a00d.opus, m29a01d.opus
                                    report: dump/converted/dalamadur/speartip_report.json

Route (notes/speartip-crag.md section 6, Gogmazios' Battlequarters precedent tools/stage4u2gu.py): our arcs keep the
Sanctuary's INTERNAL paths (stage\\m18d\\..., sound\\...\\m18d\\...), so every file ID GU computes for stage 18 resolves
by path hash to our resources; they ship at new RomFS paths (folder m29 = allocations.toml stage_alias) that the module
asks for while Dalamadur's quests run (module/stage_alias.c). The Sanctuary's own files stay untouched (an addition).
Area numbers are the same in both games (0 camp, 1 arena), so the 4U area info (SIS) ships unchanged.

  area arcs a00 / a01 (GU m18 aNN.arc as the base):
    - main model m18a0Nd <- 4U m08a0Nd (stage4u2gu convert_models / build_mrl / textures)
    - set schedulers: every GU one goes with its props; 4U's take the GU slots -a00..-a04 (file IDs 0xada7 + (stage
      * 13 + area) * 5 + k exist for every slot): camp -a00 rocks + their SE, -a01 lightning, -a02 billboard; arena
      -a00 (cliffs, lightning bolt + flash light), -a01 = 4U -sky. All their tracks exist for the same class in GU's
      corpus (2026-10-21 check). The 4U -col / -e00 / -e02 run the "Effect" controller GU lacks: not shipped (the
      break effects are posted by the module, goal D)
    - filter -f: GU's structure without its props (uBaseModel objects + the MaterialControls aimed at them: the
      Sanctuary's -f draws 5 camp / 11 arena props), 4U light / fog values (stage4u2gu port_filter, as Gogmazios)
    - area SE: 4U m08a0Nd bank, request, waves and sound call (tools/snd_area.py) replace GU's (the camp: added;
      GU asks for the request by file ID 0xcede although the Sanctuary ships none)
  stage arc m29d.arc (GU m18d.arc): KowareObj schedulers m18a01d-k01..k03 <- 4U m08a01d-k00..k02 (mId 1..3 kept: GU's
    action-0 start swaps the same SBC parts 2 * mId - 1 / 2 * mId as 4U; mType 9..11 are no special case in GU's
    KowareObj code: it tests 4, 5, 6, 12, 17, 18, 20 only; no mAt* attack sphere, so not breakable by hits, as 4U;
    Effect controllers dropped), their models; area stream STQR bgm_m18d <- 4U str_m08 streams.
  map_com m29.arc (GU m18.arc): area collision (5 kinds per area; the camp has no shells in 4U -> its main files,
    the m19 camp rule), area info SIS, item pops (4U: no gathering spot in either area; GU's Sanctuary arena has 4),
    stage effect lists m18_000 / m18_100 emptied (the Sanctuary's 3 + 1 ambient effects; 4U m08 ships none),
    whole-map area offsets = 4U m08's (AMAP08_WMAP; the map pictures: build_speartip_ui.py).
    Kept GU: kowareObjData (already 4U's layout {1,1,0,0,200} {1,2,1,0,200} {1,3,2,0,200}), ballista shells (no
    kind-3 point in the 4U area info -> none spawn), nav, area select / patrol.
Deviations / G: 4U collision group flags w2 0x102 (arena lower floor 10, 52 triangles) kept: GU uses bits 0x2 and
0x100 apart, never together; GU's second infinite lights (DEF02 / EM02) and GodRays / ColorCorrect stay GU's.
"""
import argparse, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                          # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths                                         # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack, sbc, sdl, snd_area, snd_bgm          # noqa: E402
import stage4u2gu as s4                              # noqa: E402

U4 = os.path.join(ROOT, 'dump', 'm08_unpacked')      # 4U loc/data/m08*.arc unpacked (done here when missing)
U4_ARCS = ('m08', 'm08a00', 'm08a01')
GUX = os.path.join(ROOT, 'dump', 'gu_stage', 'nativeNX')
STR4U = os.path.join(ROOT, 'dump', 'romfs', 'sound', 'bgm', 'str_map', 'm08')
REPORT = os.path.join(ROOT, 'dump', 'converted', 'dalamadur', 'speartip_report.json')
STAGE, FOLDER = 18, 29                               # allocations.toml dalamadur stage_alias
G = 'm%02d' % STAGE
T_MOD, T_MRL, T_TEX, T_SDL = s4.T_MOD, s4.T_MRL, s4.T_TEX, s4.T_SDL
T_SBC, T_SIS, T_STQR = s4.T_SBC, s4.T_SIS, s4.T_STQR
T_IPS, T_IPL = 0x52776ab1, 0x25fd693f
T_PEL = 0x5a525c16                                   # stage effect placement list (effect\pel\st\m18_000 / _100)
T_WMAP = s4.T_WMAP                                   # whole-map area offsets (map_com stage\m18d\m18d)
MEM4U = os.path.join(ROOT, 'dump', 'exefs_v11', 'mem.bin')     # 4U v1.1, flat from 0x100000
# 4U aMap08 (Speartip stage class, vtable 0xe652f8) +0x10 = 0x656fb4: 0x6c2ac8(obj, W, records, 2) with the literals
# {records, W} here: W = 30000, records 24 B {s32 x, s32 z, ...} = a00 (6800, 5300), a01 (0, -2800). C
AMAP08_WMAP = 0x656fe0
PEL_EMPTY = b'PEL\0' + struct.pack('<4I', 15, 0, 0, 0)   # = GU's own empty lists (m07, m08, m10 ...: 20 of 140)
T_SOUND = (0x79c47b59, 0x15d782fb, 0x1bcc4966, 0x2543b93e)      # GU wave, bank, request, sound call
UBASEMODEL = 0x45a468ee
# GU area -> (4U main model, {GU set-scheduler slot: 4U scheduler})
AREAS = {
    0: ('stage\\m08d\\m08a00d\\m08a00d', {'a00': 'm08a00d-a00', 'a01': 'm08a00d-a01', 'a02': 'm08a00d-a02'}),
    1: ('stage\\m08d\\m08a01d\\m08a01d', {'a00': 'm08a01d-a00', 'a01': 'm08a01d-sky'}),
}
KOBJ = {k: 'stage\\m08d\\m08a01d\\sdl\\m08a01d-k%02d' % (k - 1) for k in (1, 2, 3)}    # GU k0N (mId N) <- 4U
ITEM_POPS = {('stage\\m18d\\m18d', T_IPS): 'stage\\m08d\\m08d', ('stage\\m18d\\m18d_low', T_IPL): 'stage\\m08d\\m08d',
             ('stage\\m18d\\m18d_high', T_IPL): 'stage\\m08d\\m08d_high',
             ('stage\\m18d\\m18d_g', T_IPL): 'stage\\m08d\\m08d_g'}
# area streams: 4U str_m08 (sequence id -> stream: 0 camp, 1 arena; 20 rain not used) -> GU m18 sequence ids
# 0 (camp) and 1 / 0x1f / 0x20 / 0x21 (the Sanctuary's arena stream and its three variants, all -> our arena stream)
STREAMS = ((0, 'm08_a00d', 0), (1, 'm08_a01d', 1))      # (GU stream, 4U wav, 4U sequence id)


def gu_file(rel):
    """a GU base-RomFS file under dump/gu_stage (extracted when missing)"""
    p = os.path.join(GUX, rel)
    if not os.path.exists(p):
        from romfs import RomFS
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(RomFS(paths.GU_ROMFS).read('/nativeNX/' + rel))
    return open(p, 'rb').read()


def unpack_4u():
    """4U arcs -> U4/<arc>/<path>.<type> (the layout of tools/arcpack.py unpack, which stage4u2gu.u4_find reads)"""
    for a in U4_ARCS:
        out = os.path.join(U4, a)
        if os.path.exists(os.path.join(out, '_order.txt')): continue
        ver, ents = arcpack.read(open(os.path.join(ROOT, 'dump', 'romfs', 'loc', 'data', a + '.arc'), 'rb').read())
        order = []
        for path, th, data in ents:
            rel = path.replace('\\', '/') + '.%08x' % th
            os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
            open(os.path.join(out, rel), 'wb').write(data)
            order.append(rel)
        open(os.path.join(out, '_order.txt'), 'w').write(''.join(r + '\n' for r in order))


def u4(path, typ):
    return s4.u4_find(path, typ)


# Speartip's lighting is 4U's alone (test 2026-10-21, user: the arena is far brighter than in 4U): after port_filter
# (the lights / fog both games have take 4U's values), the host's objects that 4U's filter lacks are switched off
# (Draw 0: its second infinite light, an always-on s2 light (4U's lightning flash is the a00 set's), god rays, the
# ambient light, the top / bottom gradient layers) and the screen filters both have take every 4U track (bloom,
# colour correction). Kept GU's: the player lights PL01..03 (4U lights hunters with camera lights of another class),
# StableShadow, StageDataSet.
# EM02-InfiniteLight (GU's second monster light, no 4U counterpart) stays ON: with it off the monster's skin showed
# a cell pattern all over (tests 2026-10-21, from the filter's first build on); back on = skin right, and the user
# prefers the arena this way (test 2026-10-21 evening)
GU_ONLY_OFF = ('DEF02-InfiniteLight', 's2-InfiniteLight', 'GodRaysFilter', 'AmbientLight',
               'MhFilter_top', 'MhFilter_bottom')
SAME_FILTERS = ('BloomFilter', 'ColorCorrectFilter')


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
            if k in gt and gt[k]['kind'] == sdl.KIND_4U_TO_GU[e['kind']]:
                sdl.set_values(g, gt[k], sdl.values(u, e), times=e['times'])
                done.append('%s.%s' % (n, k))
    return sdl.build(g), done


def camcheck_drawmode(ns):
    """GU camera-checked uStageSets carry mDrawMode 13 (stage4u2gu DRAWMODE_CAMCHECK)"""
    for i, n, c, tr in sdl.objects(ns):
        if c == s4.USTAGESET and 'mCameraCheck' in tr and 'mDrawMode' in tr and sdl.values(ns, tr['mCameraCheck'])[0]:
            sdl.set_values(ns, tr['mDrawMode'],
                           [s4.DRAWMODE_CAMCHECK.get(v, v) for v in sdl.values(ns, tr['mDrawMode'])])


def models_textures(models):
    """[(path, mrl, mod, textures)] -> 4U texture paths in first-use order"""
    out = []
    for p, r, m, t in models:
        out += [x for x in t if x not in out]
    return out


def ordered(ents, drop_models, new_textures, new_models, tail):
    """GU entries minus the dropped models and every texture no kept MRL uses, then: kept GU textures, our textures,
    kept GU materials / models, ours (TEX -> MRL -> MOD: a model fetches its MRL by path while loading), the rest of
    the GU entries in their order, then `tail` (schedulers after the models they name)."""
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


def area_sound(k, ents, log):
    """4U m08a0Nd SE (tools/snd_area.py) instead of GU m18a0Nd's: waves, bank, request, call"""
    new = snd_area.convert_area(k, 'a%02d' % k, True, log, u4=U4, s4='m08', sg=G)
    mine = ('sound\\se\\map\\%sd\\%sa%02dd\\' % (G, G, k), 'sound\\call\\map\\%sd\\%sa%02dd' % (G, G, k))
    gone = [e for e in ents if e[1] in T_SOUND and e[0].startswith(mine)]
    assert gone, (k, 'no GU area sound entries')
    return [e for e in ents if e not in gone] + new, '%d GU entries -> %d (4U m08a%02dd)' % (len(gone), len(new), k)


def build_area(k, rep):
    g, a4 = '%sa%02dd' % (G, k), 'm08a%02dd' % k
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/a%02d.arc' % (G, k)))
    main4, sets4 = AREAS[k]
    gmain = 'stage\\%sd\\%s\\%s' % (G, g, g)
    d4 = u4(main4, T_MOD)
    gmod, mats = s4.convert_models([(d4, '')])
    s4.check_model(gmod, [d4])
    gmrl, texs, rows = s4.build_mrl(mats, {0: u4(main4, T_MRL)})
    models = [(gmain, gmrl, gmod, texs)]
    r = rep['a%02d' % k] = dict(model=gmain, source=main4, meshes=len(mats), materials=rows)
    drop = {gmain}
    # every GU set scheduler goes with the props it draws; the 4U ones take the slots
    gsets = [(p, d) for p, t, d in ents if t == T_SDL and re.search(r'-a0\d$', p)]
    for p, d in gsets:
        drop |= set(sdl.resource_paths(sdl.parse(d)))
    ents = [e for e in ents if not (e[1] == T_SDL and re.search(r'-a0\d$', e[0]))]
    tail = []
    r['sets'] = {}
    for slot, n4 in sets4.items():
        ns = sdl.parse(sdl.convert_4u(u4('stage\\m08d\\%s\\sdl\\%s' % (a4, n4), T_SDL), drop_ctrl=s4.sdl_drop_ctrl,
                                      drop_keyless=True))
        camcheck_drawmode(ns)
        props = sdl.resource_paths(ns)
        for p in props:
            pm, pr, pt, prow = s4.convert_prop(p)
            models.append((p, pr, pm, pt))
        tail.append(('stage\\%sd\\%s\\sdl\\%s-%s' % (G, g, g, slot), T_SDL, sdl.build(ns)))
        r['sets'][slot] = dict(source=n4, objects=[n for i, n, c, tr in sdl.objects(ns)], props=props)
    r['dropped_gu_sets'] = [p for p, d in gsets]
    # filter: GU's without its props, 4U light / fog values
    fpath = 'stage\\%sd\\%s\\sdl\\%s-f' % (G, g, g)
    k_f = [i for i, e in enumerate(ents) if e[0] == fpath and e[1] == T_SDL][0]
    fs = sdl.parse(ents[k_f][2])
    props = set(sdl.resource_paths(fs))
    gone = sdl.remove_objects(fs, lambda c, n: c == UBASEMODEL)
    drop |= props - set(sdl.resource_paths(fs))
    f4 = u4('stage\\m08d\\%s\\sdl\\%s-f' % (a4, a4), T_SDL)
    fd, done = s4.port_filter(sdl.build(fs), f4)
    fd, own = filter_4u_only(fd, f4)
    ents[k_f] = (fpath, T_SDL, fd)
    r['filter'] = dict(dropped_objects=gone, ported=done, speartip=own)
    ents, r['sound'] = area_sound(k, ents, r.setdefault('sound_log', []))
    out, ndrop = ordered(ents, drop, models_textures(models), [m for m in models], tail)
    r['dropped_gu'] = dict(models=sorted(drop), textures=ndrop)
    return out


def build_stage_arc(streams, rep):
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/%sd.arc' % (G, G)))
    rows = []; drop = set(); new = {}
    for k, p4 in KOBJ.items():
        gp = 'stage\\%sd\\%sa01d\\sdl\\%sa01d-k%02d' % (G, G, G, k)
        old = sdl.parse([d for p, t, d in ents if p == gp and t == T_SDL][0])
        assert [sdl.values(old, tr['mId'])[0] for i, n, c, tr in sdl.objects(old) if c == 0x3dfe3bc2] == [k], gp
        drop |= set(sdl.resource_paths(old))
        sd = s4.convert_kobj(p4, k, 1, se_area=(1, 1))
        models = []
        for p in sdl.resource_paths(sdl.parse(sd)):
            pm, pr, pt, prow = s4.convert_prop(p)
            models.append((p, pr, pm, pt))
        new[gp] = (sd, models)
        rows.append((gp, p4, 'mId %d' % k, [m[0] for m in models]))
    ents = [(p, t, streams if t == T_STQR else d) for p, t, d in ents]
    models = [m for sd, ms in new.values() for m in ms]
    tail = [(gp, T_SDL, sd) for gp, (sd, ms) in new.items()]
    ents = [e for e in ents if not (e[1] == T_SDL and e[0] in new)]
    out, ndrop = ordered(ents, drop, models_textures(models), models, tail)
    rep['stage_arc'] = dict(kobj=rows, dropped_gu_models=sorted(drop), dropped_gu_textures=ndrop)
    return out


def collision_4u(area, kind):
    """4U m08a0Nd collision of one kind; a missing shell -> the main file of its family (4U camp: no shells)"""
    base = os.path.join(U4, 'm08', 'stage', 'm08d', area, 'collision', area)
    for kk in (kind, kind.replace('-shell', '')):
        p = base + kk + '.%08x' % T_SBC
        if os.path.exists(p):
            return kk, open(p, 'rb').read()
    raise SystemExit('4U collision %s%s missing' % (area, kind))


def wholemap_4u():
    """4U m08 whole map: (W, [(x, z) offset per area]) (AMAP08_WMAP)"""
    m = open(MEM4U, 'rb').read()
    u = lambda a: struct.unpack_from('<I', m, a - 0x100000)[0]
    recs = u(AMAP08_WMAP)
    return u(AMAP08_WMAP + 4), [struct.unpack_from('<2i', m, recs + 24 * a - 0x100000) for a in range(2)]


def wholemap_offsets(d):
    """GU whole-map records (f32, u32 n, n x 20 B {s32 x, s32 z, ...}: stage4u2gu.py "whole-map area offsets") with 4U
    m08's offsets; the module scales the GU whole-map record by GU dims[18] / 4U W (package.toml wholemap_k)"""
    w, offs = wholemap_4u()
    b = bytearray(d)
    assert struct.unpack_from('<I', b, 4)[0] == len(offs) and len(b) == 8 + 20 * len(offs), len(b)
    for a, o in enumerate(offs):
        struct.pack_into('<2i', b, 8 + 20 * a, *o)
    return bytes(b), 'whole-map offsets -> 4U m08 %s (W %d)' % (offs, w)


def build_map_com(rep):
    ver, ents = arcpack.read(gu_file('loc/arc/stage/map_com/%s.arc' % G))
    rows = []; out = []; seen = set()
    for p, t, d in ents:
        name = p.split('\\')[-1]
        if t == T_SBC and re.match(r'%sa0[01]d-a-' % G, name):
            area4, kind = 'm08' + name[3:7], name[7:]
            src, d4 = collision_4u(area4, kind)
            d = sbc.convert_4u(d4)
            s = sbc.parse(d)
            rows.append((p, area4 + src, [x['id'] for x in s['parts']], s['nA'], s['nB'], s['nC']))
        elif t == T_SIS and re.match(r'%sa0[01]d-info' % G, name):
            a4 = 'm08' + name[3:7]
            d = open(os.path.join(U4, 'm08', 'stage', 'm08d', a4, '%s-info.%08x' % (a4, T_SIS)), 'rb').read()
            rows.append((p, 'm08' + name[3:7] + '-info (verbatim: same area numbers)'))
        elif (p, t) in ITEM_POPS:
            src = ITEM_POPS[(p, t)]
            d = u4(src, t)
            rows.append((p, '%s (4U item pops: no gathering spot)' % src))
        elif t == T_PEL and re.match(r'effect\\pel\\st\\%s_[01]00$' % G, p):
            assert d[:16] == PEL_EMPTY[:16], p
            rows.append((p, 'emptied (the Sanctuary\'s %d stage effects; 4U Speartip has no effect list)' %
                         struct.unpack_from('<I', d, 16)[0]))
            d = PEL_EMPTY
        elif t == T_WMAP and p == 'stage\\%sd\\%sd' % (G, G):
            d, what = wholemap_offsets(d)
            rows.append((p, what))
        else:
            out.append((p, t, d))
            continue
        seen.add((p, t))
        out.append((p, t, d))
    assert len(seen) == 10 + 2 + 4 + 2 + 1, sorted(seen)
    rep['map_com'] = rows
    return out


def stq4u_db(path):
    """4U STRQ: {sequence id: (stream index, dB)} (stream table 36 B from 0x18, sequences 100 B after it)"""
    d = open(path, 'rb').read()
    ns, nq = struct.unpack_from('<II', d, 8)
    out = {}
    for o in range(0x18 + 36 * ns, 0x18 + 36 * ns + 100 * nq, 100):
        out[struct.unpack_from('<I', d, o)[0]] = (struct.unpack_from('<I', d, o + 92)[0],
                                                  struct.unpack_from('<f', d, o + 36)[0])
    return out


def build_streams(outroot, rep):
    """4U str_m08 area streams -> GU opus (m29d paths) + the stage STQR (GU m18's sequences, our streams); level =
    4U dB + the median battle-theme delta (tools/snd_bgm.py levels), as for the monster themes"""
    log = []
    med, _ = snd_bgm.levels(log)
    q4 = stq4u_db(os.path.join(STR4U, 'str_m08.stq'))
    ver, ents = arcpack.read(gu_file('arc/stage/%sd/%sd.arc' % (G, G)))
    base = [d for p, t, d in ents if t == T_STQR][0]
    s = snd_bgm.stqr_parse(base)
    assert snd_bgm.stqr_build(s) == base, 'bgm_m18d.stqr does not rebuild byte-identically'
    streams = []; db = {}
    for k, wav, sid in STREAMS:
        assert q4[sid][0] == k, (sid, q4[sid])
        path = 'sound\\bgm\\map\\m%02dd\\wav\\m%02da%02dd' % (FOLDER, FOLDER, k)
        log.append(path)
        opus, ns, ls, le, rms = snd_bgm.convert_track(open(os.path.join(STR4U, 'wav', wav + '.mca'), 'rb').read(), log)
        f = os.path.join(outroot, 'nativeNX', path.replace('\\', '/') + '.opus')
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, 'wb').write(opus)
        streams.append([path, len(opus), ns, 2, snd_bgm.RATE, ls, le, snd_bgm.STREAM_HASH, 0])
        db[k] = q4[sid][1] + med
    s['streams'] = streams
    seqs = []
    for q in s['seqs']:
        q = bytearray(q)
        k = 0 if struct.unpack_from('<I', q, 0)[0] == 0 else 1
        struct.pack_into('<I', q, 92, k)
        struct.pack_into('<f', q, 36, db[k])
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
    ap.add_argument('--out', default=paths.romfs('dalamadur'))
    a = ap.parse_args()
    unpack_4u()
    s4.set_source(U4, 'm08')
    rep = {}
    sdir = os.path.join(a.out, 'nativeNX', 'arc', 'stage', 'm%02dd' % FOLDER)
    os.makedirs(sdir, exist_ok=True)
    for k in AREAS:
        ents = build_area(k, rep)
        open(os.path.join(sdir, 'a%02d.arc' % k), 'wb').write(arcpack.build(ents))
        print('built a%02d.arc: %d entries (%s)' % (k, len(ents), rep['a%02d' % k]['sound']), flush=True)
    stqr = build_streams(a.out, rep)
    ents = build_stage_arc(stqr, rep)
    open(os.path.join(sdir, 'm%02dd.arc' % FOLDER), 'wb').write(arcpack.build(ents))
    print('built m%02dd.arc: %d entries, kobj %s' % (FOLDER, len(ents), [r[:3] for r in rep['stage_arc']['kobj']]))
    mp = os.path.join(a.out, 'nativeNX', 'loc', 'arc', 'stage', 'map_com', 'm%02d.arc' % FOLDER)
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    ents = build_map_com(rep)
    open(mp, 'wb').write(arcpack.build(ents))
    print('built map_com m%02d.arc: %d entries' % (FOLDER, len(ents)))
    for row in rep['map_com']: print('  ', *row)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(rep, open(REPORT, 'w'), indent=1)
    print('report:', os.path.relpath(REPORT, ROOT))


if __name__ == '__main__':
    main()
