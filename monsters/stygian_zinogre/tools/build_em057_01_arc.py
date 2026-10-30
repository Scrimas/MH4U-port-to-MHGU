"""build_em057_01_arc.py : build nativeNX/arc/enemy/em057_01.arc (Stygian Zinogre = GU Zinogre variant 1, ID 0x139)
+ its data file section FILE.

  build_em057_01_arc.py      build, verify, then write (paths in monsters/stygian_zinogre/):
      romfs/nativeNX/arc/enemy/em057_01.arc
      tools/em057_01_manifest.json         (51 manifest fields, file IDs, sources)
      gen/FILE.sec                         (data file section FILE: manifest + file table, tools/portdata.py)

Layout = GU's own variant arcs (em057_04, Thunderlord): the variant's own files under enemy\\em057\\em057_01\\..., the
files it shares with variant 0 under em057_00's paths and file IDs. GU's class uEm057_00 runs it (variant byte 1,
notes/phase1-variant-map.md). The source facts are in notes/phase1-assets.md.
  own, converted from MH4U em049.arc (4U runs Stygian on Zinogre's class and files: em048's motions, camera, AI):
      mod\\em057_01 (+ _tail) MOD + MRL    tools/mod4u2gu.py; MRL from GU templates (tools/mrl_build.py), 4U material
                                           animations converted (tools/mrl_anim.py), as gogmazios/build_em089_arc.py
      mod\\em057_01_NN_BM (+A), _NN_NM_*   albedo (BC3) + GU specular map from its alpha; normal maps (BC5)
      mod\\em057_01 XFS                    GU em057_00's parts states for em049's mesh groups
      mot\\em057_01_0 / _2 / _3            4U em048's motion lists (LMT 67, unchanged: GU re-encoded every Zinogre
                                           animation) + GU's own 2:42 (GU class code may request it)
      mot\\em057_01_cam                    4U e048_cam (tools/lcm4u2gu.py; GU's own differs)
      effects                              tools/efl4u2gu.py effect_set: MEF em048_0 (shared by both 4U arcs) + em049_1's
                                           records (Stygian's own ids 3000..3041, which the shared motions name next
                                           to Zinogre's 2000..2041), em049's EFL family + the nine em048 EFLs
                                           em049.arc ships, one PSL per motion list; PEL list 2 = GU em057_00u's +
                                           our code posts 3200..3299 (SHELL_FX)
      shell\\em\\em057_01_shell01\\...      shell family: GU em057_00_shell01 renamed, HDS / HTS for Stygian's shells
                                           (shell_family(); def file ID SHELL_FILE_ID, no manifest field)
      sound call / waves / bank / request  tools/snd4u2gu.py monster_entries (4U call em048 + bank snd_em049)
      cam_body_data\\em057_01_cambodydata  4U em049's (a copy of its bodydata: 28 records; em048 has 16)
      dt_tune\\em057_01_dttune             GU em057_00's + the bytes where tools/dt_convert.py gives em049 != em048
      hit_data\\em057_01_attackdata        4U em049's + GU's two extra records (GU retuned 16 shared records)
      hagi\\hagi_s0..s4_em057_01           carves: 4U High tables in s2, G in s4, GU's filler in s0 / s1 / s3
                                           (tools/hagi_em057_01.py)
      cmd_tbl\\em057_01_cmdtbl             4U em048_cmd for em 49 in GU's language (cmdtbl(): op-0x46 em switches
                                           reduced to their em-49 bodies, GU's area-move scripts, GU's extra entries)
      area_link / area_eat / map_info /    GU em057_00's (maps 1 4 6 14 23 24) + GU Brachydios' (em063_00) map 12
      area_select / area_patrol \\em057_01  records (Volcanic Hollow, his 4U quests' stage 15: area_files())
  shared, GU em057_00 (original paths + file IDs): sound triggers (PTS), PEL c, GU's shell families (rows 247 / 248,
      which GU's class preloads for variant 1 too: notes/b5-shells.md 2a), hitsize, bodydata,
      dtbase, dtbparts (4U em048 and em049 give the same data: notes/phase1-assets.md 4), dou mou ka.
Inputs besides the arcs: dump/converted/em049/dt_em048/ and dt_em049/ (build.sh step dt: tools/dt_convert.py in the
MHGU_Editor venv, donor em057_00) and the 4U ROM (core effect arcs, Arena area colour).
"""
import json, os, re, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, arcpack, ctr, efl4u2gu, emc, emdata4u, lcm4u2gu, lmt, mod as modlib, mod4u2gu, mrl, mrl_anim, \
    mrl_build, portdata, snd4u2gu, tex, xfs

NAME = 'stygian_zinogre'
ALLOC = alloc.monster(NAME)
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']      # IDs served by the module (allocations.toml)
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em049.arc')
GU_ARC = '/nativeNX/arc/enemy/em057_00.arc'
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em057_01.arc')
OUT_JSON = os.path.join(HERE, 'em057_01_manifest.json')
FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02,
         LCM=0x39C52040)
P4 = 'enemy\\em049\\'            # 4U Stygian's own paths
P48 = 'enemy\\em048\\'           # 4U Zinogre's paths (em049.arc ships its motions, camera and AI under them)
P0 = 'enemy\\em057\\em057_00\\'  # GU variant 0
P = 'enemy\\em057\\em057_01\\'   # ours
BANKS = (0, 2, 3)                # motion lists of em048 and em057_00: manifest field 4 + bank
GU_ONLY_MOTIONS = {2: [(42, 42)]}   # bank: [(GU index, our index)]: GU's animation in a slot 4U leaves empty
# manifest fields with our own file: IDs are given in this order (append only: IDs never move once shipped)
OWN_ORDER = [0, 1, 3, 4, 6, 7, 11, 37, 17, 18, 20, 21, 12, 13, 31, 33, 25, 15, 46, 47, 48, 49, 50, 26, 40, 41, 42, 43,
             44]                # 40..44 moved after 26 before any of them shipped (2026-10-28): 26 keeps its ID
DT_DIR = os.path.join(ROOT, 'dump/converted/em049')           # build.sh step dt
PEL_U = 'effect\\pel\\em\\em057_01u'
PSL = 'effect\\psl\\enemy\\em057\\em057_01\\mot\\em057_01_%d'
MODELS = (('em049', 'em057_01', 0), ('em049_tail', 'em057_01_tail', 1))    # 4U name, ours, manifest field
# Material type (MRL w6 bits 21-28) = the 'mNN' of the 4U name, except where GU's own Zinogre gives the same role
# another number: GU em057_00 names its body 'XfB_N__E_m00_body' (type 0) and its effect 'XfB__I0__m03_effect' (type 3),
# 4U em048 / em049 the reverse (body m03, effect m00). GU's class addresses materials by type (C, 2026-10-28: its init
# 0xeeed64 keeps type 52 and type 3 for the material charge glow of slot 132, which em057_01_fix.c skips for Stygian:
# 4U has none), so the roles follow GU. Lights keep 4U's 1 / 2 (GU has one light, type 2 = 4U's light_01 m02); head 4
# has no GU counterpart.
MTYPE = {'XfB_N__E_m03_body': 0, 'XfBAN__IW_0__m00_effect_': 3}
# 4U groups 50 (eye), 51, 52 (light_01): 4U rows show them only under condition 10 / state bit 128 (the same rows as
# Zinogre em048; G: frenzy, as Tigerstripe's group 50); GU's Zinogre model has none, so no GU state names them: hidden
# in the base state, as GU Zinogre never shows them.
HIDDEN_GROUPS = (50, 51, 52)

# ---- Stygian's shells: data side (notes/b5-shells.md 2b.4 / 2b.5 / 3; the shell classes come in later module steps).
# C = read in 4U / GU code or data, S = strong, G = guess.
# Family (C): GU em057_00_shell01 (def with 14 kinds of ef / snd / hit / sh params, HDS, HTS: 59 files, def last) under
# our path, by same-length renames only: the family path and the def's PEL path (GU's em057_00u -> PEL_U). Its PTS
# (sound\pts\em\em057_00u) and sound request (sound\se\em\em057_00\snd_em057_00) stay GU's, in the arc (GU's own
# shell defs name them too). Our shells post sounds through the owner's request (ours; GU's has no 224) and effects
# through PEL_U list 2 (SHELL_FX), as em089 / Dalamadur. The def has no manifest field: its file ID is an extra after
# the fields' (EXTRA_ORDER, as build_dalamadur_arc.py), = SHELL_FILE_ID (asserted). Appended after GU's kept files, so
# every file it names comes first.
SHELL_SRC = 'shell\\em\\em057_00_shell01\\em057_00_01'
SHELL_DST = 'shell\\em\\em057_01_shell01\\em057_01_01'
PEL_GU = 'effect\\pel\\em\\em057_00u'
T_HDS, T_HTS, T_SHELL = 0x4EB68CEE, 0x5653C1B0, 0x4AA69872
SHELL_FILE_ID = 0x108db          # the def (module: Stygian's shell request) = FILE_ID_BASE + the 27 own fields
# Area data (C: tools/xfs.py layout; manifest fields 40 area_link, 41 area_eat, 42 map_info, 43 area_select, 44
# area_patrol). GU em057_00's cover maps 1 4 6 14 23 24 (patrol: 4), so on the Volcanic Hollow (GU map 12: 4U m10616
# m00907 m10925, stage 15) Zinogre's would give no next area. 4U keeps no area data in the monster arcs (S, as em092),
# so map 12 comes from GU Brachydios em063_00 (maps 6 8 12; a large ground brawler of the Hollow, Stygian's partner in
# m10925; GU's q1003 is its Hollow hunt): its map-12 records are appended to Zinogre's in map order (XFS files) and its
# map-12 block replaces Zinogre's empty one (map_info: 12-B header + 28 x 86-B blocks, block = map). The Arena (map 9)
# is one area: no data, as GU's. Heaven's Mount comes with its stage port.
AREA_FIELDS = {40: 'area_link', 41: 'area_eat', 42: 'map_info', 43: 'area_select', 44: 'area_patrol'}
AREA_DONOR = ('/nativeNX/arc/enemy/em063_00.arc', 'em063_00', 12)
MAP_INFO_HEAD, MAP_INFO_BLOCK = 12, 86
# Heaven's Mount (his quests m10607 m10930 m11010) runs on GU map 24 = the alias of the Ruined Pinnacle with 4U m05's
# geometry and area numbers (tools/build_heavens_mount.py). Zinogre's own map-24 records describe the Ruined
# Pinnacle's area graph, so area_link (hop distances, kinds 1 / 2 / 4) and area_select (next areas) of map 24 are
# rebuilt from the 4U area graph: the exits of the 4U area info (SIS section 1, target byte +17) between areas 1..8
# (the camp is never a target, as GU's rows 0). No GU monster roams this graph, and 4U keeps no route data of its own
# (its AI walks on SIS + collision, S), so: area_select = every 4U neighbour with an equal share (Status 0 only;
# GU's Status 4 "weakened" rows have no 4U source, G), area_link kinds 1 / 2 / 4 = the BFS hop count (G for kind 4,
# whose GU rows are a sparser subgraph); GU area 9 (no 4U area) keeps a self-only row. area_eat and the map_info block
# stay Zinogre's (per-map stamina / stay values, not area-graph data).
AREA_ALIAS = (24, os.path.join(ROOT, 'dump/romfs/loc/data/m05.arc'), 'm05', 9)   # GU map, 4U stage arc, 4U areas
# Heaven's Mount area 4 (the vine climb) is out of the monsters' graph: no 4U monster goes there (user, 2026-10-28; test
# 2026-10-28: with it, he jumped from 6 into 4 and looped there), so it is no Next area and keeps a self-only row
HUNTER_ONLY = {4}


def alias_graph():
    """4U Heaven's Mount area graph {area: sorted neighbours} (areas 1..), from the SIS exits of m05.arc (C)"""
    sys.path.insert(0, paths.GU_PY)
    import sis
    _, ents = arcpack.read(open(AREA_ALIAS[1], 'rb').read())
    E = {p: d for p, t, d in ents if t == 0x065375d5}
    s4 = AREA_ALIAS[2]
    g = {}
    for a in range(AREA_ALIAS[3]):
        recs = sis.parse(E['stage\\%sd\\%sa%02dd\\%sa%02dd-info' % (s4, s4, a, s4, a)])['sec'][1]
        g[a] = sorted({r[17] for r in recs} - {a})
    # some 4U exits are one-way for hunters (drops, e.g. 4 -> 3): monsters leave by flying / climbing, so the graph is
    # made two-way (S)
    for a in list(g):
        for b in g[a]:
            if a not in g[b]: g[b] = sorted(g[b] + [a])
    return {a: [b for b in ns if b and b not in HUNTER_ONLY] for a, ns in g.items() if a and a not in HUNTER_ONLY}


def alias_routes(kind, data, notes):
    """area_link / area_select with their map-AREA_ALIAS[0] records rebuilt from alias_graph()"""
    import copy
    m = AREA_ALIAS[0]
    g = alias_graph()
    dist = {}
    for a in g:                                   # BFS hop counts over areas 1..8
        d, fr = {a: 0}, [a]
        while fr:
            nx = []
            for x in fr:
                for y in g[x]:
                    if y not in d: d[y] = d[x] + 1; nx.append(y)
            fr = nx
        dist[a] = d
    root = xfs.parse(data)
    arr = root['RouteFindDataResource']['mpArray']
    arr = arr if isinstance(arr, list) else [arr]
    mine = [o for o in arr if o['mMapNo'] == m]
    if kind == 'area_link':
        assert {o['mKind'] for o in mine} == {1, 2, 4}, [o['mKind'] for o in mine]
        for o in mine:
            rows = o['mAreaSelDataArray']['mpArray']
            for r, row in enumerate(rows):
                for c in range(1, 13):
                    row['A%02d' % c] = (dist[r].get(c, 255) if r in dist else (0 if c == r else 255))
        new = arr
        what = 'kinds 1 / 2 / 4 = 4U hop counts'
    else:
        tpl = copy.deepcopy(mine[0])
        e0 = tpl['mAreaSelDataArray']['mpArray']
        e0 = copy.deepcopy(e0[0] if isinstance(e0, list) else e0)
        recs = []
        for a, ns in sorted(g.items()):
            r = copy.deepcopy(tpl)
            r['mAreaNo'] = a
            e = copy.deepcopy(e0)
            ns = ns[:4]
            share = [100 // len(ns) + (1 if i < 100 % len(ns) else 0) for i in range(len(ns))]
            e.update(Status=0, RouteNo=0, Param=0, BackArea=255)
            for i in range(4):
                e['Next%dArea' % (i + 1)] = ns[i] if i < len(ns) else 255
                e['Next%dRand' % (i + 1)] = share[i] if i < len(ns) else 255
            r['mAreaSelDataArray']['mpArray'] = e
            recs.append(r)
        at = arr.index(mine[0])
        new = [o for o in arr[:at] if o['mMapNo'] != m] + recs + [o for o in arr[at:] if o['mMapNo'] != m]
        what = 'areas %s' % {a: ns[:4] for a, ns in sorted(g.items())}
    root['RouteFindDataResource']['mpArray'] = new
    out = xfs.build(data, root)
    assert xfs.build(out, xfs.parse(out)) == out
    notes.append('area data %s map %d: %d Ruined Pinnacle record(s) -> 4U Heaven\'s Mount graph (%s)' % (
        kind, m, len(mine), what))
    return out
EXTRA_ORDER = ['shell01']        # own files without a manifest field, IDs after the fields' (append only)
CODE_4U = os.path.join(ROOT, 'dump/exefs_v11/code.bin')     # MH4U v1.1 code, loaded at 0x100000
CODE_4U_BASE = 0x100000
# 4U shell attack data (C): (40-B records, volume pointer table): record byte 0x19 = volume -> 40-B hitsize records up
# to 0xFFFF; read by 0x9ab120(shell, records, volumes, record, a, b) in each init.
U044 = (0x10300d0, 0x10300c8)    # uShell044 init 0xc87f84, record = subtype: 1 Zinogre pillar, 3 Stygian pillar
U003 = (0x101f230, 0x101efbc)    # uShell003 (dala_shell003.c), record = subtype: 129 / 235 Zinogre, 135 / 236 Stygian
U046 = (0x10307e0, 0x10307d8)    # uShell046 init 0xc89280, record = subtype 0..4 (all five identical): the orbs
GU_HDS_1C = set(range(6, 11)) | {254}   # 4U byte 0x1c values GU never uses -> 6 (build_dalamadur_arc.py; GU's
                                        # uShell003 twins hold 6 where 4U has 0x1c, asserted)
# HDS entries in the module's order, byte 0x19 = the HTS group of the same index:
#   0 pillar  4U uShell044 record 3 = GU entry 0 (= 4U record 1 by the em089 rule, byte for byte) + 4U's record 1 -> 3
#             delta (+0x0c, +0x10)
#   1 blast   4U uShell003 135 = GU entry 1 (= 4U 129 by the rule except GU's +0x2c = 2, rule 0) + 4U's 129 -> 135
#             delta (+0x0c; +0x19 = our group 1)
#   2 blast   4U uShell003 236 = GU entry 2 (= 4U 235, the same) + 4U's 235 -> 236 delta (+0x0c; +0x19 = group 2)
#   3 orb     4U uShell046 record 0 by the em089 rule (no GU twin; GU's shell18 entry is a retuned uShell044 0, design
#             2a; 4U's records 0..4 = uShell044 record 2 byte for byte)
# HTS groups (GU record = 4U record + 8 zero bytes with +0x0a = 0x0848, and +4 = 1 on GU's bone-1001 group): 0 = GU g0
# as is (4U uShell044 volume 1, bone 1001 r200), 1 = GU g1 with r180 (uShell003 volume 110, bone 255), 2 = GU g1 as is
# (volume 153 = GU g1's volume 106, bone 255 r200), 3 = GU g0 with r130 (uShell046 volume 0, bone 1001).
SHELL_HDS_NAMES = ('pillar (uShell044 3)', 'blast (uShell003 135)', 'blast (uShell003 236)', 'orb (uShell046 0-4)')
# Code-posted effects (PEL list 2 after GU em057_00u's 27 records: efl4u2gu effect_set extra2), from the 4U requests
# (C; request ctor 0xc0ca90 defaults: mask -1, scale = MT 0x10e6388 (1, 1, 1), position / rotation 0, joint +0x60 255,
# none of these posts changes the scale). EFL = 4U group 58 list (EFL_GROUPS_4U, asserted), mask -> k (mask = 1 << k,
# -1 = all), joint = request +0x60 (255 -> -1), follow = posted on a moving object (efl4u2gu PEL_TAIL_PREV), else
# placed once: the joint -1 ones are world posts with no target (em057_01_efx.c sz_efx_world gives position and
# rotation) and take GU's world code-post tail (efl4u2gu PEL_TAIL_WORLD, asserted = GU em001_00u record 31's; test 5
# drew them away from the point with PEL_TAIL, which needs a target). id = 3200 + file
# number, + 50 for a file's element-1 variant, + 25 for its element-2 variant (files 0..24); the block SHELL_FX_IDS is
# asserted free in PEL_U before these. The aura rows are posted by em057_01_efx.c in place of GU's Zinogre records
# (GU 30 / 31 / 32 = em057_00_000 joint 2 masks 2 / 4 / 1, 1120 / 1121 = em057_00_011 joint 2: Capcom's conversion of
# 4U em048's (57, 0) / (57, 11) aura, the same joint and masks).
EFL_GROUPS_4U = 0xef895c         # 4U EFL table: group -> list of path pointers (group 58 = 0xef6fbc, elements 9..28)
SHELL_FX_IDS = range(3200, 3300)
SHELL_FX = [   # (id, 4U group, element, k, joint, follow, 4U post)
    (3202, 58, 11, -1, 2, True, 'charge change 0x856fec (0xc088d8 on the monster): W+0x1ca != 11, joint 2'),
    (3205, 58, 14, -1, 1, True, 'charge change 0x856fec: W+0x1ca == 11, joint 1'),
    (3203, 58, 12, 0, -1, False, 'vt77 ground hit 0x85849c (0xc08628 at the point): uncharged, mask 1'),
    (3253, 58, 12, 1, -1, False, 'vt77 ground hit 0x85849c: charged, mask r5 = 2 (0x857f40; S: no other r5 write '
                                 'seen on the path)'),
    (3215, 58, 20, 0, -1, True, 'uShell046 flight 0xc89250 (0xc08698 on the shell +0x5c): mask 1 (0x10308a8)'),
    (3217, 58, 22, 0, -1, False, 'uShell046 impact 0xc89c70 / 0xc8a1c0 (0xc08628 at the hit point): mask r10 = 1'),
    (3267, 58, 22, 1, -1, False, 'uShell046 age end 0xc897d4 / 0xc89d10 (at the shell position): mask r7 = 2'),
    (3219, 58, 24, -1, -1, False, 'uShell044 sub 3 burst 0x9aa504 (0xc08628 at the shell position, window start)'),
    (3220, 58, 25, -1, -1, False, 'uShell044 sub 3 gather 0xc88188 (0xc08698 on the shell, 0x1030260): a shell '
                                  'that does not move (S), placed once (as Dalamadur 2950)'),
    (3222, 58, 27, -1, -1, False, 'uShell003 135 / 236 blast 0xc55854 (0xc08628 at the shell; 0x101dfcc mask -1, '
                                  'scale table 0x1021a08 = 1.0)'),
    (3200, 58, 9, 0, 2, True, 'aura controller 0x322f18 (0xc08698 on the monster, joint +0x60 = 2): charged '
                              '(0x90f90c), mask 1'),
    (3250, 58, 9, 1, 2, True, 'aura controller 0x322f18: slot-51 query 1 answers 1, mask 2'),
    (3225, 58, 9, 2, 2, True, 'aura controller 0x322f18: slot-51 query 1 answers 2, mask 4'),
    (3211, 58, 17, -1, 2, True, 'aura controller 0x322f18: enraged (rageOn 0x954e48), mask left at the ctor\'s -1'),
]
# the 4U request ids of the shells' and effect posts' sounds (notes/b5-shells.md 1): asserted in our converted request,
# own bank (word 21 = 0): 205 vt77 hit, 210 / 213 charge change, 215 / 216 / 224 orb, 217 / 218 pillar, 226 blast
SHELL_SOUNDS = (205, 210, 213, 215, 216, 217, 218, 224, 226)


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, struct.unpack_from('<I', img, FILES_TABLE + 4 * index)[0]))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)


def textures(S, r4, slots, out, gu_tex, spec_type=1):
    """the GU texture paths of one 4U material's albedo / normal maps (converted on first use into `out`):
    albedo -> BC3 + its '+A' specular map in R, G, B (alpha 255), normal map -> BC5 (as Gogmazios' em089_04_NM).
    The '+A' map is the 4U specular mask: the BM alpha for 4U CBMaterialStd iMaterialStdSpecularMaskType 1 (as
    build_em089_arc.py: Gogmazios' materials are type 1), the normal map's alpha for type 2 (C, data: every type-2
    material here (body, head, fur, tails) has a BM alpha that is 255 but for the fur's cut-out, while the left half of
    its NM_MIRROR, exactly the BM's size, holds a 16-level mask whose edges follow the BM's (correlation 0.79 / 0.68,
    against 0.1 for the right half or the whole map); 4U em049 means 28..36 / 255, the fur area 18: nearly matte).
    Until 2026-10-28 type 2 took the BM alpha too, a near-full mask: the fur shone cream in GU (user: "the fur looks
    like regular Zinogre's"). spec_type 0 (no specular: the eye, the effect) takes whatever the texture already has."""
    paths_of = {}
    nm = slots.get('tNormalMap') if spec_type == 2 else None
    nm_src = r4['textures'][nm - 1][1] if nm else None
    for slot, v in slots.items():
        if not v: continue
        src = r4['textures'][v - 1][1]
        name = src.split('\\')[-1]
        if src not in gu_tex:
            t = tex.decode(S[(src, T['TEX'])])
            path = P + 'mod\\em057_01_' + name.split('em049_')[-1]
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
    """one em049 MOD + MRL (+ the textures it is the first to use) -> [(path, type, data)], the parsed 4U MOD.
    Templates as build_em089_arc.py: blended -> 'add', normal-mapped -> 'solid_nm', emissive (4U CBMaterialStd
    emission > 0, diffuse 0) -> 'unlit', else 'solid'; alpha-tested (MRL w7 bit 24 on BSSolid) -> 'solid_at' / 'tar'
    (with a normal map). Every 4U material animation is converted (constants = the 4U material's own for the
    variables its tracks drive); none autoplays: 4U picks them from code (names unknown hashes: notes/phase1-assets.md).
    MRL before MOD, as in GU's arcs: a model fetches its materials by path while it loads."""
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
        key = 'add' if 'BSAddAlpha' in states or 'BSBlendAlpha' in states else \
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
        mats.append((mname, key, slots, [s for s in states if s.startswith('RS')], consts, extra))
        notes.append('%s material %s: template %s, type %d, %s, 4U specular mask type %d%s' % (
            dst_name, mname, key, extra['mtype'], sorted(p.split('\\')[-1] for p in gp.values()), spec_type,
            ', %d 4U animations' % len(ents4) if ents4 else ''))
    mod_bytes = mod4u2gu.convert(d4)
    mrl_bytes = mrl_build.build(rom, mats, tex_paths)
    assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
    out += [(P + 'mod\\' + dst_name, T['MRL'], mrl_bytes), (P + 'mod\\' + dst_name, T['MOD'], mod_bytes)]
    return out, m4


def parts_xfs(gu_xfs, groups, notes):
    """GU em057_00's parts states (rMonsterPartsManager XFS) for em049's mesh groups. 4U em049's visibility rows are
    em048's (C), and GU's states name the same group numbers (GU's model = em048's groups minus 50..52)."""
    r, states = emdata4u.parse_xfs_states(gu_xfs)
    data, nobj = emdata4u.xfs_states(states)
    assert data == gu_xfs[r:], 'XFS round trip differs: emdata4u.xfs_states no longer matches GU files'
    kept = [[(g, v) for g, v in st if g in groups] for st in states]
    unnamed = sorted(set(groups) - {g for st in states for g, _ in st} - set(HIDDEN_GROUPS))
    assert not unnamed, 'em049 groups without a GU state: %s' % unnamed
    kept[0] += [(g, 0) for g in HIDDEN_GROUPS if g in groups]
    data, nobj = emdata4u.xfs_states(kept)
    head = bytearray(gu_xfs[:r])
    struct.pack_into('<I', head, 8, nobj)
    dropped = sorted({g for st in states for g, _ in st} - set(groups))
    notes.append('parts states: %d (GU layout), groups dropped (not in em049): %s, hidden at spawn: %s' % (
        len(kept), dropped, list(HIDDEN_GROUPS)))
    return bytes(head) + data


def motion_bank(S, gu_banks, b, notes):
    """4U em048's motion list b, plus GU's animations in the slots 4U leaves empty (GU_ONLY_MOTIONS)"""
    d = S[(P48 + 'mot\\em048_%d' % b, T['LMT'])]
    if b not in GU_ONLY_MOTIONS:
        return d
    out = lmt.splice(d, gu_banks[b], GU_ONLY_MOTIONS[b])
    notes.append('motions bank %d: 4U em048 + GU em057_00 %s' % (b, [g for g, _ in GU_ONLY_MOTIONS[b]]))
    return out


def arena_soil(notes):
    """RGBA area colour for the effects: the 4U Arena's (stage 11, m11a01: four of Stygian's 4U quests) area_color_soil
    (same 455-byte SDL layout as the Battlequarters' m19a03d-col whose soil efl4u2gu documents, colour at +0xd0). GU
    has no area tint: one colour is baked in."""
    m19 = os.path.join(ROOT, 'dump/m19_unpacked/m19a03/stage/m19d/m19a03d/sdl/m19a03d-col.4c0db839')
    ref = open(m19, 'rb').read()
    n, _ = ctr.main_ncch(efl4u2gu.ROM_4U)
    _, ents = arcpack.read(n.romfs_reader().read('/loc/data/m11a01.arc'))
    d = [d for p, t, d in ents if p == 'stage\\m11d\\m11a01d\\sdl\\m11a01d-col'][0]
    assert len(d) == len(ref) and re.findall(rb'[ -~]{4,}', d) == re.findall(rb'[ -~]{4,}', ref), 'm11a01d-col layout'
    soil = bytes(round(255 * x) for x in struct.unpack_from('<4f', d, 0xd0))
    notes.append('effect area colour: 4U Arena m11a01 soil %s' % (tuple(soil),))
    return soil


def efl_4u(code, grp, elem):
    """the EFL path 4U posts for (group, element): table EFL_GROUPS_4U -> the group's list of path pointers"""
    u32 = lambda a: struct.unpack_from('<I', code, a - CODE_4U_BASE)[0]
    p = u32(u32(EFL_GROUPS_4U + 4 * grp) + 4 * elem) - CODE_4U_BASE
    return code[p:code.index(b'\0', p)].decode('ascii')


def gu_world_tail():
    """bytes 0x34.. of GU em001_00u's list-2 record 31, a joint -1 world code post (efl4u2gu PEL_TAIL_WORLD's source)"""
    arc = efl4u2gu.gu_rom().read('/nativeNX/arc/enemy/em001_00.arc')
    pel = [d for p, t, d in arcpack.read(arc)[1] if t == efl4u2gu.T['PEL'] and p.endswith('em001_00u')][0]
    body, i = efl4u2gu.pel_lists(pel)[2][1], 0
    while i < len(body):
        st = body[i + 3 + body[i]:i + 3 + body[i] + 160]
        if struct.unpack_from('<H', st, 0x30)[0] == 31:
            return st[0x34:]
        i += 3 + body[i] + 160


def gu_local_tail(gu_pel_u):
    """bytes 0x34.. of GU em057_00u's list-1 record 560 (Capcom's em048_004 joint 2, 4U flags 0x225: efl4u2gu
    PEL_TAIL_LOCAL's source), its mask word +0x48 zeroed"""
    body, i = efl4u2gu.pel_lists(gu_pel_u)[1][1], 0
    while i < len(body):
        st = bytearray(body[i + 3 + body[i]:i + 3 + body[i] + 160])
        if struct.unpack_from('<H', st, 0x30)[0] == 560:
            st[0x48:0x4c] = bytes(4)
            return bytes(st[0x34:])
        i += 3 + body[i] + 160


def pel_ids(body):
    """the record ids of a PEL list's bytes (record = u8 path length, path, 2 bytes, 160 bytes; id u16 at +0x30)"""
    ids, i = [], 0
    while i < len(body):
        n = body[i]
        ids.append(struct.unpack_from('<H', body, i + 3 + n + 0x30)[0])
        i += 3 + n + 160
    assert i == len(body), 'PEL list layout'
    return ids


def effects(S, gu_pel_u, code, notes):
    """em049's effects (tools/efl4u2gu.py effect_set) -> [(path, type, data)]. MEF em048_0 (shared by em048.arc and
    em049.arc: common qe families + group 48 = Zinogre's EFLs; em049.arc ships the nine its records name, em048_004 006
    008 014 018 021 030 031 102 (C, 2026-10-28: dropped until then), not group 114's em114_100 / 101, as in 4U) +
    em049_1's records as extra records (group 49 = em049's EFLs). PEL list 2 = GU em057_00u's (GU's class posts its
    Zinogre ids; em057_01_efx.c swaps Stygian's in) + Stygian's code posts SHELL_FX (extra2, ids in SHELL_FX_IDS:
    asserted free before, each once after)."""
    groups = {48: 'effect\\efl\\em\\em048\\em048_%03d', 49: 'effect\\efl\\em\\em049\\em049_%03d'}
    groups.update({g: 'effect\\efl\\qe\\qe%03d\\qe%03d_%%03d' % (g, g) for g in (0, 6, 8, 13)})
    own = efl4u2gu.mef_records(S[('effect\\mef\\em\\em049_1', efl4u2gu.T['MEF'])])
    assert all(r['grp'] == 49 for r in own), 'em049_1 names another EFL group'
    list2 = efl4u2gu.pel_lists(gu_pel_u)[2]
    assert gu_world_tail() == efl4u2gu.PEL_TAIL_WORLD, "GU's world code-post tail (em001_00u record 31) changed"
    assert gu_local_tail(gu_pel_u) == efl4u2gu.PEL_TAIL_LOCAL, "Capcom's local joint tail (em057_00u record 560)"
    extra2 = []
    for rid, grp, elem, k, joint, follow, _ in SHELL_FX:
        path = efl_4u(code, grp, elem)
        assert path.startswith('effect\\efl\\em\\em049\\em049_') and rid in SHELL_FX_IDS, (rid, path)
        f = int(path[-3:])                                             # the id scheme: 3200 + file (+ 50 / + 25)
        assert f < 25 and rid - 3200 == f + {1: 50, 2: 25}.get(k, 0), (rid, path, k)
        extra2.append((path, dict(id=rid, joint=joint, k=k, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0),
                                  scl=(1.0, 1.0, 1.0), follow=follow, world=joint == -1 and not follow)))
    spec = dict(arc=SRC_4U, stage_unpacked=[], mef='effect\\mef\\em\\em048_0', em_efl='effect\\efl\\em\\em049\\',
                groups=groups, extra=[(groups[49] % r['file'], r) for r in own],
                lmts=[(P48 + 'mot\\em048_%d' % b, PSL % b) for b in BANKS], pel=PEL_U, soil=arena_soil(notes),
                list2=list2, extra2=extra2, hide_grey_models='chunks')   # issue #6 white debris (efl4u2gu.CHUNK_MODELS)
    log = []
    out = efl4u2gu.effect_set(spec, log)
    lists = efl4u2gu.pel_lists(out[(PEL_U, efl4u2gu.T['PEL'])])
    ours = [r['id'] for _, r in extra2]
    before = pel_ids(lists[0][1]) + pel_ids(lists[1][1]) + pel_ids(list2[1])
    assert len(ours) == len(set(ours)) and not set(before) & set(SHELL_FX_IDS), 'PEL id block 3200..3299 not free'
    assert pel_ids(lists[2][1]) == pel_ids(list2[1]) + ours, 'PEL list 2 = GU em057_00u list 2 + SHELL_FX'
    notes.append('effects: %d entries (tools/efl4u2gu.py effect_set; em049_1 ids %d..%d as extra records)' % (
        len(out), min(r['id'] for r in own), max(r['id'] for r in own)))
    notes += ['  ' + l for l in log if not l.startswith('EFL ')]
    notes += ['  code post %d: %s k %d joint %d %s; 4U %s' % (r['id'], p.split('\\')[-1], r['k'], r['joint'],
                                                              'follows' if r['follow'] else 'world post (no target)'
                                                              if r['world'] else 'placed once', src)
              for (p, r), src in zip(extra2, [x[-1] for x in SHELL_FX])]
    return [(p, t, d) for (p, t), d in out.items()]


def sound(rom, notes):
    """em049's sound call (4U em048's file), waves, bank snd_em049 and request (tools/snd4u2gu.py monster_entries) ->
    ([(path, type, data)], {field: (path, type)}). Common-bank requests from GU em057_00 (same numbers in every GU
    monster) plus the ones GU's Zinogre adds (its class may post them)."""
    spec = dict(name='em049', src=SRC_4U, p4_wave='sound\\se\\em\\em048\\wave\\', pg_wave='sound\\se\\em\\em057_01\\wav\\',
                p4_bank='sound\\se\\em\\em048\\snd_em049', pg_bank='sound\\se\\em\\em057_01\\snd_em057_01',
                p4_call='sound\\call\\em\\em048', pg_call='sound\\call\\em\\em057_01', donor_arc=GU_ARC,
                donor_name='GU em057_00', donor_extra=True)
    log = []
    out = snd4u2gu.monster_entries(spec, rom=rom, log=log)
    snd4u2gu.verify(out, spec)
    req = [d for p, t, d in out if (p, t) == (spec['pg_bank'], snd4u2gu.TG['REQ'])]
    assert len(req) == 1
    bank = {e[0] & 0xFFFF: e[21] for e in snd4u2gu.reqgu_parse(req[0])['ents']}
    assert all(bank.get(i) == 0 for i in SHELL_SOUNDS), 'shell sounds missing from our request (own bank): %s' % [
        i for i in SHELL_SOUNDS if bank.get(i) != 0]
    notes += log
    notes.append('sound request: the shell / effect post ids %s are own-bank entries' % (SHELL_SOUNDS,))
    return out, {12: (spec['pg_call'], snd4u2gu.TG['CALL']), 13: (spec['pg_bank'], snd4u2gu.TG['REQ'])}


def rec_4u(code, shell, i):
    """4U attack record i (40 B) of a shell's (records, volumes)"""
    o = shell[0] + 40 * i - CODE_4U_BASE
    return code[o:o + 40]


def vol_4u(code, shell, v):
    """the single 40-B hitsize record of a shell's volume v (asserted single: the next record is the 0xFFFF end)"""
    p = struct.unpack_from('<I', code, shell[1] + 4 * v - CODE_4U_BASE)[0] - CODE_4U_BASE
    assert struct.unpack_from('<H', code, p + 40)[0] == 0xFFFF, (hex(shell[1]), v)
    return code[p:p + 40]


def hds_rule(r4, group):
    """the em089 rule (build_em089_arc.py / build_dalamadur_arc.py shell_hds): 4U 40-B record -> GU 56-B HDS entry:
    0x00..0x23 copied, byte 0x12 bits 0-1 kept and its level (bits 2+) to +0x2c, 0x1c by GU_HDS_1C, +0x28 f32 1.0,
    0x19 = the HTS group"""
    assert not any(r4[0x24:0x28]), r4.hex()
    r = bytearray(56)
    r[0:0x24] = r4[0:0x24]
    r[0x12] = r4[0x12] & 3
    r[0x1c] = r4[0x1c] if r4[0x1c] in GU_HDS_1C else 6
    struct.pack_into('<f', r, 0x28, 1.0)
    r[0x2c] = r4[0x12] >> 2
    r[0x19] = group
    return bytes(r)


def hts_rule(v4, gu_rec):
    """4U 40-B hitsize record -> GU 48-B HTS record: + 8 zero bytes, +0x0a = GU's (0x0848 in all GU shell HTS)"""
    assert not any(v4[0x0a:0x0c]), v4.hex()
    r = bytearray(48)
    r[0:40] = v4
    r[0x0a:0x0c] = gu_rec[0x0a:0x0c]
    return bytes(r)


def diff(a, b):
    return [i for i in range(len(a)) if a[i] != b[i]]


def shell_hds(code, gu):
    """our HDS (SHELL_HDS_NAMES order) from GU em057_00_shell01's (3 entries) and the 4U records, with the asserts of
    notes/b5-shells.md 3 (GU's entries = rule / twin; the 4U Zinogre -> Stygian deltas)"""
    assert gu[:4] == b'HDS\0' and struct.unpack_from('<I', gu, 8)[0] == 3 and len(gu) == 16 + 3 * 56
    g = [gu[16 + 56 * i:72 + 56 * i] for i in range(3)]
    z1, s3 = rec_4u(code, U044, 1), rec_4u(code, U044, 3)
    z129, s135, z235, s236 = (rec_4u(code, U003, i) for i in (129, 135, 235, 236))
    orb = [rec_4u(code, U046, i) for i in range(5)]
    assert (z1[0x19], s3[0x19], z129[0x19], s135[0x19], z235[0x19], s236[0x19], orb[0][0x19]) == \
        (1, 1, 106, 110, 152, 153, 0), '4U volume indices changed'
    assert g[0] == hds_rule(z1, 0), 'GU HDS 0 != em089 rule of 4U uShell044 record 1'
    for e, z, grp in ((g[1], z129, 1), (g[2], z235, 2)):
        r = bytearray(hds_rule(z, grp))
        assert r[0x2c] == 0 and z[0x1c] == 0x1c and r[0x1c] == 6, z.hex()
        r[0x2c] = 2                                      # GU's level where the rule gives 0 (Capcom's retune)
        assert e == bytes(r), 'GU HDS entry != em089 rule of its 4U uShell003 twin + level 2'
    assert diff(z1, s3) == [0x0c, 0x10] and diff(z129, s135) == diff(z235, s236) == [0x0c, 0x19], \
        'Zinogre -> Stygian 4U deltas changed'
    assert all(r == orb[0] for r in orb), '4U uShell046 records 0..4 differ'
    out = []
    e = bytearray(g[0]); e[0x0c] = s3[0x0c]; e[0x10] = s3[0x10]
    assert bytes(e) == hds_rule(s3, 0)                   # GU entry 0 + delta = the rule of record 3
    out.append(bytes(e))
    for base, s, grp in ((g[1], s135, 1), (g[2], s236, 2)):
        e = bytearray(base); e[0x0c] = s[0x0c]
        assert e[0x19] == grp                            # our group for the twin's volume = GU's group index
        out.append(bytes(e))
    out.append(hds_rule(orb[0], 3))
    return struct.pack('<4sIII', b'HDS\0', struct.unpack_from('<I', gu, 4)[0], len(out), 0) + b''.join(out), out


def shell_hts(code, gu):
    """our HTS (groups = HDS entries, one record each) from GU em057_00_shell01's three groups, with the asserts"""
    assert gu[:4] == b'HTS\0' and struct.unpack_from('<I', gu, 8)[0] == 3 and len(gu) == 16 + 24 + 3 * 48
    tab = [struct.unpack_from('<II', gu, 16 + 8 * k) for k in range(3)]
    assert all(c == 1 for c, _ in tab), tab
    g = [gu[o:o + 48] for _, o in tab]
    v1 = vol_4u(code, U044, 1)
    v106, v110, v152, v153 = (vol_4u(code, U003, v) for v in (106, 110, 152, 153))
    v0 = vol_4u(code, U046, 0)
    assert diff(hts_rule(v1, g[0]), g[0]) == [4] and g[0][4] == 1, 'GU HTS g0 != 4U uShell044 volume 1 (+4 = 1)'
    assert hts_rule(v106, g[1]) == g[1] and hts_rule(v152, g[2]) == g[2], 'GU HTS g1 / g2 != 4U volumes 106 / 152'
    radius = lambda r, v: bytes(r[:0x0c]) + bytes(v[0x0c:0x10]) + bytes(r[0x10:])
    out = [g[0], radius(g[1], v110), g[1], radius(g[0], v0)]
    assert out[1] == hts_rule(v110, g[1]) and out[2] == hts_rule(v153, g[1]), '4U volumes 110 / 153 = GU g1 + radius'
    assert diff(hts_rule(v0, g[0]), out[3]) == [4], '4U uShell046 volume 0 = GU g0 + radius (+4 = 1 kept)'
    n = len(out)
    head = bytearray(gu[:16])
    struct.pack_into('<I', head, 8, n)
    table = b''.join(struct.pack('<II', 1, 16 + 8 * n + 48 * k) for k in range(n))
    return bytes(head) + table + b''.join(out), out


def shell_family(gents, code, notes):
    """[(path, type, data)] of Stygian's shell family in GU's order (def last): GU em057_00_shell01 renamed, our
    HDS / HTS"""
    assert len(SHELL_SRC) == len(SHELL_DST) and len(PEL_GU) == len(PEL_U)
    out = []
    for p, t, d in gents:
        if not p.startswith(SHELL_SRC): continue
        if t == T_SHELL:
            assert d.count(SHELL_SRC.encode()) == 58 and d.count(PEL_GU.encode()) == 1    # 14 x 4 params + HDS + HTS
            d = d.replace(SHELL_SRC.encode(), SHELL_DST.encode()).replace(PEL_GU.encode(), PEL_U.encode())
            assert b'em057_00_shell01' not in d and b'em057_00u' in d    # the PTS stays GU's
        elif t == T_HDS:
            d, hds = shell_hds(code, d)
        elif t == T_HTS:
            d, hts = shell_hts(code, d)
        else:
            assert b'em057' not in d and b'shell\\' not in d, p          # params name no file
        out.append((SHELL_DST + p[len(SHELL_SRC):], t, d))
    assert len(out) == 59 and out[-1][:2] == (SHELL_DST, T_SHELL) and sum(t == T_SHELL for _, t, _ in out) == 1
    notes.append('shell family %s: %d files from GU %s (def file ID 0x%x, PEL %s); HDS %d entries, HTS %d groups:' % (
        SHELL_DST, len(out), SHELL_SRC, SHELL_FILE_ID, PEL_U, len(hds), len(hts)))
    for k, name in enumerate(SHELL_HDS_NAMES):
        e, h = hds[k], hts[k]
        notes.append('  HDS %d %s: window %d+%d power %d type 0x%x +0x0c 0x%x +0x10 0x%x level %d -> HTS %d: bone %d '
                     'r%g' % (k, name, *struct.unpack_from('<hHHB', e, 0)[0:2], struct.unpack_from('<H', e, 4)[0],
                              e[6], struct.unpack_from('<I', e, 0x0c)[0], e[0x10], e[0x2c], e[0x19],
                              struct.unpack_from('<H', h, 0)[0], struct.unpack_from('<f', h, 0x0c)[0]))
    return out


def cambodydata(model_bones, notes):
    """4U em049's camera body data (emd word 9, a copy of its bodydata), converted (tools/emdata4u.py)"""
    emd = emdata4u.load_4u('em049')['emd']
    b = emdata4u.bodydata(emd, 9)
    assert b == emdata4u.bodydata(emd, 8), 'em049 cambodydata is no longer its bodydata: recheck phase1-assets.md 4'
    n = struct.unpack_from('<I', b, 8)[0]
    # bone 255: GU's own em057_00 bodydata has a record on it too (255, 0xFFFF)
    bad = {struct.unpack_from('<H', b, 16 + 44 * k + o)[0] for k in range(n) for o in (0, 2)} - model_bones - {0xFF, 0xFFFF}
    assert not bad, 'cambodydata names bones missing from the model: %s' % sorted(bad)
    notes.append('cambodydata: 4U em049 (%d records; GU em057_00 = retuned em048, 19)' % n)
    return b


# AI table (notes/plan.md B6). 4U em048_cmd serves em 48, 49 and 114: their differences are EMC op 0x46 blocks, a
# switch on the em number (4U 0x951ff0; GU has no op 0x46, its handler 0x8470c skips the token, so every case body
# would run in turn: Dalamadur's lesson). Our table serves Stygian only, so each 0x46 block is reduced to its em-49
# body (case 49, else the else body): Stygian's own selectors g0 s12 / s13 / s14 and g8 s0 keep their case-49 bodies.
# GU's language for area moves replaces 4U's in the scripts that carry it (GU g0 s0 = 4U g0 s0 for em 49 with the
# engine op 0x9e where 4U called its area script s88, C), and GU's extra entries are appended: its class picks group-1
# scripts by number (area_act_tbl, Tigerstripe's lesson). Instruction lengths: GU's table main 0x1732c8c (byte < 0x80
# = argument count; 0x8n..0xBn block ops: 00 opens with n args, 01 = case with a 1..4-byte value, 02 else, ff end).
EMC_LEN_TABLE, EMC_LEN_COUNT = 0x1732c8c, 167
EMC_GU_AREA = {(0, 0), (0, 1), (0, 2), (20, 0), (1, 59), (1, 62), (1, 63), (1, 88)}   # (group, script): GU's version
EMC_4U_ONLY_OPS = {0x03, 0x06, 0x36, 0x4d, 0x2a}    # 4U area ops (no-ops in GU) and stage switches (4U stage ids)


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


def emc_em_only(s, em, lens):
    """the script with every op-0x46 block reduced to em's body (its case, else the else body)"""
    out, frames = bytearray(), []                   # per open 0x46 block: [taking, taken]
    for t in emc_tokens(s, lens):
        if t[0] == 0x46:
            if t[1] == 0x00: frames.append([False, False])
            elif t[1] == 0x01: frames[-1][0] = t[2] == em and not frames[-1][1]; frames[-1][1] |= frames[-1][0]
            elif t[1] == 0x02: frames[-1][0] = not frames[-1][1]; frames[-1][1] = True
            else: frames.pop()
            continue
        if all(f[0] for f in frames): out += t
    assert not frames, 'unbalanced op-0x46 block'
    return bytes(out)


# 4U's rest test (notes/plan.md B7). 4U op 0x80 = if ((s8) W+0x53a) [0x953500: 0x93731c], op 0x91 = if (W+0x7e80 & 32)
# [0x953ef8: 0x936418(this, 32)], both with an else (C). GU's 0x80 (0xc9b58) never takes its body (no test: skip to
# the else) and GU's 0x91 (0x852bc) is a switch on the em number (this+0xb5f4) whose body, with no case, never runs (C).
# 4U g0 s3 is `80 00 R 80 02 91 00 R 91 02 91 ff 80 ff` with R twice (the same bytes) = if (W+0x53a || bit 32) R: it
# becomes `80 00 R 80 02 80 ff` (GU's own g0 s3 form), and the op-0x80 hook in module/em057_01_ai.c answers
# (W+0x53a || rec+0x5e08 & 32) for Stygian. Without that hook both forms skip R, as the table did before.
def emc_rest_merge(s, lens):
    """4U g0 s3's op-0x80 block with its op-0x91 else -> one op-0x80 block (see above); other scripts unchanged"""
    t = emc_tokens(s, lens)
    ops = [x[:2] for x in t]
    if b'\x91\x00' not in ops: return s
    a, e, o = ops.index(b'\x80\x00'), ops.index(b'\x80\x02'), ops.index(b'\x91\x00')
    e2, z2, z = ops.index(b'\x91\x02'), ops.index(b'\x91\xff'), ops.index(b'\x80\xff')
    assert ops.count(b'\x80\x00') == ops.count(b'\x91\x00') == 1 and a < e == o - 1 and e2 == z2 - 1 == z - 2 \
        and t[a + 1:e] == t[o + 1:e2], 'op-0x91 block not in its 4U g0 s3 form'
    return b''.join(t[:e + 1] + [b'\x80\xff'] + t[z + 1:])


def cmdtbl(d4, gu, img, notes):
    """4U em048_cmd for em 49 in GU's language (see above) -> EMC bytes"""
    lens = img[EMC_LEN_TABLE:EMC_LEN_TABLE + EMC_LEN_COUNT]
    ver, u4 = emc.parse(d4)
    _, g = emc.parse(gu)
    assert len(u4) == 23 and len(g) == 21 and not u4[22], 'EMC group layout changed'
    assert [emc_em_only(s, 49, lens) for s in u4[21]] == [b'\xff'], "4U group 21 (em 114's) is not empty for em 49"
    out, kept, called = [], 0, set()
    for gi in range(21):
        scripts = []
        for k, s in enumerate(u4[gi]):
            if (gi, k) in EMC_GU_AREA:
                scripts.append(g[gi][k]); continue
            s = emc_rest_merge(emc_em_only(s, 49, lens), lens)
            assert not {t[0] for t in emc_tokens(s, lens)} & EMC_4U_ONLY_OPS, ('4U-only op left', gi, k)
            scripts.append(s); kept += 1
        extra = g[gi][len(u4[gi]):]
        for s in extra:
            called |= {t[1] for t in emc_tokens(s, lens) if t[0] == 0x14}
        out.append(scripts + list(extra))
    heads = [t[:2] for sc in out for s in sc for t in emc_tokens(s, lens)]
    assert heads.count(b'\x80\x00') == 1 and not any(h[0] == 0x91 for h in heads), \
        'op-0x80 / 0x91 blocks changed: module/em057_01_ai.c answers the one op-0x80 block (g0 s3)'
    differs = sorted(c for c in called if c < len(u4[1]) and out[1][c] != g[1][c])
    notes.append('AI table: 4U em048_cmd for em 49 (%d scripts, op-0x46 blocks reduced), GU area scripts %s, GU extra '
                 'entries appended (groups %s); GU extras call 4U-differing scripts %s' % (
                     kept, sorted(EMC_GU_AREA), [(gi, len(u4[gi]), len(g[gi])) for gi in range(21)
                                                 if len(g[gi]) > len(u4[gi])], differs))
    return emc.build(out, ver)


def attackdata(gu, notes):
    """4U em049's attackdata (tools/emdata4u.py; = em048's, asserted) with GU em057_00's byte 28 (GU-only, the
    converter writes 6), then GU's records 75 / 76 (its own additions: GU code may still post them). GU retuned 16
    shared records (1, 17, 18, 21, 34..44, 70, 71, 74, Zinogre's uncharged attacks that 4U Stygian also uses); Stygian
    keeps 4U's. Its own indices 48..73 are unchanged in GU (notes/phase1-assets.md)."""
    st = emdata4u.attackdata(emdata4u.load_4u('em049')['etd'])
    assert st == emdata4u.attackdata(emdata4u.load_4u('em048')['etd'])
    n4, ng = struct.unpack_from('<I', st, 8)[0], struct.unpack_from('<I', gu, 8)[0]
    assert (st[:8], st[12:16]) == (gu[:8], gu[12:16]) and ng == n4 + 2, 'GU attackdata layout changed'
    assert len(st) == 16 + 32 * n4 and len(gu) == 16 + 32 * ng
    out = bytearray(gu[:16]) + st[16:] + gu[16 + 32 * n4:]
    for k in range(n4):
        out[16 + 32 * k + 28] = gu[16 + 32 * k + 28]
    diff = [k for k in range(ng) if out[16 + 32 * k:48 + 32 * k] != gu[16 + 32 * k:48 + 32 * k]]
    notes.append('attackdata: 4U em049 (%d records) + GU records %d / %d, GU byte 28; differs from GU in records %s'
                 % (n4, n4, n4 + 1, diff))
    return bytes(out)


def dttune(gu, notes):
    """GU em057_00's dttune + the bytes where tools/dt_convert.py (donor em057_00) gives em049 != em048: Stygian's 4U
    differences on GU's own Zinogre tuning (GU's retuned bytes and these never overlap: asserted)."""
    c48 = open(os.path.join(DT_DIR, 'dt_em048', 'dttune.bin'), 'rb').read()
    c49 = open(os.path.join(DT_DIR, 'dt_em049', 'dttune.bin'), 'rb').read()
    assert len(c48) == len(c49) == len(gu)
    delta = [i for i in range(len(gu)) if c48[i] != c49[i]]
    retuned = {i for i in range(len(gu)) if c48[i] != gu[i]}
    assert not retuned & set(delta), 'GU retuned bytes Stygian changes: %s' % sorted(retuned & set(delta))
    out = bytearray(gu)
    for i in delta: out[i] = c49[i]
    notes.append('dttune: GU em057_00 + %d bytes of 4U em048 -> em049 differences (GU retuned %d other bytes)' % (
        len(delta), len(retuned)))
    return bytes(out)


def area_files(rom, gfile, gtype, notes):
    """{field: (our path, type, data)}: GU em057_00's area files + the donor's map-12 records (AREA_DONOR)"""
    _, dents = arcpack.read(rom.read(AREA_DONOR[0]))
    m = AREA_DONOR[2]
    out = {}
    for k, kind in AREA_FIELDS.items():
        dsrc = [d for p, t, d in dents if p == 'enemy\\%s\\%s' % (kind, AREA_DONOR[1]) and t == gtype[k]]
        assert len(dsrc) == 1, (k, kind)
        z, dn = gfile(k), dsrc[0]
        if kind == 'map_info':
            n = (len(z) - MAP_INFO_HEAD) // MAP_INFO_BLOCK
            assert len(z) == len(dn) == MAP_INFO_HEAD + n * MAP_INFO_BLOCK and z[:MAP_INFO_HEAD] == dn[:MAP_INFO_HEAD]
            o = MAP_INFO_HEAD + m * MAP_INFO_BLOCK
            assert not any(z[o:o + MAP_INFO_BLOCK]) and any(dn[o:o + MAP_INFO_BLOCK]), 'map_info block %d' % m
            data = z[:o] + dn[o:o + MAP_INFO_BLOCK] + z[o + MAP_INFO_BLOCK:]
            added = 1
        else:
            assert xfs.build(z, xfs.parse(z)) == z, ('XFS round trip', kind)
            root, droot = xfs.parse(z), xfs.parse(dn)
            arr = root['RouteFindDataResource']['mpArray']
            darr = droot['RouteFindDataResource']['mpArray']
            arr = arr if isinstance(arr, list) else [arr]
            darr = darr if isinstance(darr, list) else [darr]
            assert all('mMapNo' in o for o in arr + darr) and not any(o['mMapNo'] == m for o in arr), kind
            mine = [o for o in darr if o['mMapNo'] == m]
            assert {o['_class'] for x in mine for o in xfs.walk(x)} <= {h for h, _ in xfs.defs(z)[1]}, kind
            at = sum(1 for o in arr if o['mMapNo'] < m)
            root['RouteFindDataResource']['mpArray'] = arr[:at] + mine + arr[at:]
            data = xfs.build(z, root)
            back = [o for o in xfs.walk(xfs.parse(data)) if 'mMapNo' in o]
            assert xfs.build(data, xfs.parse(data)) == data and back == arr[:at] + mine + arr[at:], ('merge', kind)
            added = len(mine)
            if kind in ('area_link', 'area_select'):
                data = alias_routes(kind, data, notes)
        out[k] = ('enemy\\%s\\em057_01' % kind, gtype[k], data)
        notes.append('area data %s: GU em057_00 + %s map %d (%d record%s)' % (kind, AREA_DONOR[1], m, added,
                                                                          '' if added == 1 else 's'))
    return out


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
    gfile = lambda k: G[ghash[fileid_entry(img, gman[k])]]          # GU em057_00's file of manifest field k

    # ---- our own files
    own, ents, gu_tex = {}, [], {}
    m4 = None
    for src_name, dst_name, field in MODELS:
        files, m = model(S, rom, src_name, dst_name, gu_tex, notes)
        ents += files
        own[field] = (P + 'mod\\' + dst_name, T['MOD'])
        m4 = m4 or m
    groups = sorted({x['group'] for x in m4['mesh_list']})
    ents.append((P + 'mod\\em057_01', T['XFS'], parts_xfs(gfile(3), groups, notes)))
    own[3] = (P + 'mod\\em057_01', T['XFS'])
    gu_banks = {b: gfile(4 + b) for b in BANKS}
    for b in BANKS:
        ents.append((P + 'mot\\em057_01_%d' % b, T['LMT'], motion_bank(S, gu_banks, b, notes)))
        own[4 + b] = (P + 'mot\\em057_01_%d' % b, T['LMT'])
    ents.append((P + 'mot\\em057_01_cam', T['LCM'], lcm4u2gu.convert(S[(P48 + 'mot\\e048_cam', T['LCM'])])))
    own[11] = (P + 'mot\\em057_01_cam', T['LCM'])
    gu_cmd = [d for p, t, d in gents if p.startswith('enemy\\cmd_tbl\\em057_00') and t == T['EMC']]
    assert len(gu_cmd) == 1
    ents.append(('enemy\\cmd_tbl\\em057_01_cmdtbl', T['EMC'], cmdtbl(S[(P48 + 'data\\em048_cmd', T['EMC'])], gu_cmd[0],
                                                                     img, notes)))
    own[37] = ('enemy\\cmd_tbl\\em057_01_cmdtbl', T['EMC'])
    code = open(CODE_4U, 'rb').read()
    ents += effects(S, gfile(17), code, notes)
    own[17] = (PEL_U, efl4u2gu.T['PEL'])
    for b in BANKS:
        own[18 + b] = (PSL % b, efl4u2gu.T['PSL'])
    files, fields = sound(rom, notes)
    ents += files
    own.update(fields)
    model_bones = {i for i in range(256) if m4['remap'][i] != 255}     # converted MOD keeps 4U's bone IDs
    assert {fx[4] for fx in SHELL_FX if fx[4] >= 0} <= model_bones, 'SHELL_FX joints missing from the model'
    for k, path, data in ((26, 'enemy\\hit_data\\em057_01_attackdata', attackdata(gfile(26), notes)),
                          (31, 'enemy\\cam_body_data\\em057_01_cambodydata', cambodydata(model_bones, notes)),
                          (33, 'enemy\\dt_tune\\em057_01_dttune', dttune(gfile(33), notes))):
        typ = ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    sys.path.insert(0, HERE)
    import hagi_em057_01                 # carves: 4U High tables in s2, G in s4, GU's filler in s0 / s1 / s3
    for k, data in hagi_em057_01.files().items():
        path, typ = 'enemy\\hagi\\hagi_s%d_em057_01' % (k - 46), ghash[fileid_entry(img, gman[k])][1]
        ents.append((path, typ, data))
        own[k] = (path, typ)
    for k, (path, typ, data) in area_files(rom, gfile, {k: ghash[fileid_entry(img, gman[k])][1]
                                                        for k in AREA_FIELDS}, notes).items():
        ents.append((path, typ, data))
        own[k] = (path, typ)

    family = shell_family(gents, code, notes)     # our shell family (appended after the kept files: SHELL_SRC)
    extras = {'shell01': (SHELL_DST, T_SHELL)}

    # ---- the shared GU em057_00 files: everything but what ours replace and em057_00's model (MOD, MRL, textures)
    replaced = {ghash[fileid_entry(img, gman[k])] for k in own if gman[k] != -1}
    drop = replaced | {(p, t) for p, t, _ in gents if p.startswith(P0 + 'mod\\')}
    while True:                                  # a file a kept one (or our family) names by path stays
        kept = [(p, t, d) for p, t, d in gents if (p, t) not in drop]
        named = {(p, t) for p, t in drop if any(p.encode('ascii') in kd for _, _, kd in kept + family)}
        if not named: break
        for p, t in sorted(named):
            notes.append('kept %s although replaced: named by %s' % (p, [kp for kp, _, kd in kept + family
                                                                         if p.encode('ascii') in kd][:4]))
        drop -= named
    ents += kept
    notes.append('shared from em057_00: %d files kept, %d dropped (replaced or its model)' % (len(kept), len(drop)))
    ents += family

    # ---- manifest: own fields -> our IDs (field order: IDs only ever grow), the rest = em057_00's IDs
    new_files, manifest, src_of = [], list(gman), {}
    assert set(own) <= set(OWN_ORDER), 'add new own fields at the end of OWN_ORDER: %s' % (set(own) - set(OWN_ORDER))
    for k in [k for k in OWN_ORDER if k in own]:
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + own[k])
        manifest[k] = fid
        src_of[k] = 'converted (4U em049)'
    for k in range(51):
        if k not in own and manifest[k] != -1: src_of[k] = 'shared (GU em057_00, its file ID)'
    assert set(extras) <= set(EXTRA_ORDER), 'add new extra files at the end of EXTRA_ORDER: %s' % (
        set(extras) - set(EXTRA_ORDER))
    extra_ids = {}
    for name in [n for n in EXTRA_ORDER if n in extras]:     # own files without a field: IDs after the fields'
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid,) + extras[name])
        extra_ids[name] = fid
    assert extra_ids['shell01'] == SHELL_FILE_ID, 'shell family def at 0x%x, the module expects 0x%x' % (
        extra_ids['shell01'], SHELL_FILE_ID)

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
    json.dump(dict(monster='em057_01 (Stygian Zinogre)', id='0x%x' % ALLOC['em_id'],
                   registry_index=ALLOC['registry_index'], file_id_base='0x%x' % FILE_ID_BASE,
                   file_count=len(new_files), manifest=fields,
                   files=[dict(file_id='0x%x' % f, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p))
                          for f, p, t in new_files], extras={n: '0x%x' % f for n, f in extra_ids.items()},
                   notes=notes), open(OUT_JSON, 'w'), indent=1)
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
