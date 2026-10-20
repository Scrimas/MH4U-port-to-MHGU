"""build_em089_arc.py : build nativeNX/arc/enemy/em089_00.arc (Gogmazios) + its file manifest for the module.

  build_em089_arc.py --kushala-model    diagnostic: same arc, same paths/file IDs, but fields 0/1 (body, tail)
                                        hold Kushala's ORIGINAL GU MOD + MRL -> romfs-kushala-model/...
  build_em089_arc.py [--cmdtbl gog]     build, verify, then write (paths in monsters/gogmazios/):
      romfs/nativeNX/arc/enemy/em089_00.arc          (the Rathian test copy is kept in romfs-rathian/)
      tools/em089_manifest.json                      (51 manifest fields, file IDs, hashes)
      gen/FILE.sec                                   (data file section FILE: manifest + file table, tools/portdata.py)

Contents of the arc:
  converted from MH4U em089.arc (tools/mod4u2gu.py, tex.py, mrl_build.py):
      enemy\\em089\\em089_00\\mod\\em089_00 / _tail / _gekiryusou   rModel + rMaterial (GU template shaders)
      enemy\\em089\\em089_00\\mod\\em089_00_0N_BM / _04_NM           textures (BC3, BC5)
      enemy\\em089\\em089_00\\mot\\em089_00_0..3                      motion lists (4U LMT 67, unchanged)
      enemy\\cmd_tbl\\em089_00_cmdtbl_4u                             4U command table, GU group count
  placeholders from the donor (Kushala, em024_00), renamed em024 -> em089 so they get their own file IDs:
      model-parts XFS, camera list, attack/hit/body/cambody data, dtbase/dttune/dtbparts, actiontune, cmdtbl,
      area_link/eat/select/patrol, map_info, hagi s0..s4  (bodydata bone IDs remapped onto Gogmazios bones)
  the donor's effect / sound / shell chain under its ORIGINAL paths (they reference each other by path), with the
  donor's own file IDs in the manifest: sound call, snd, pts, pel, psl, shell arc, option motion.
  Gogmazios' shell family shell\\em\\em089_00_shell00\\ (copy of the donor's family 00, HDS/HTS from 4U uShell050;
  def = EM089_FILE_SHELL00, not in the manifest: module/em089_shell.c loads it by file ID).
"""
import json, os, re, shutil, struct, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/gogmazios
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import arcpack, mod as modlib, mod4u2gu, tex, mrl, mrl_build, mrl_anim, emdata4u, portdata
import lcm4u2gu                   # 4U camera list (LCM v4) -> GU v5 (behaviour agent, field 11)

GU_ROMFS = paths.GU_ROMFS
MAIN_IMG = paths.GU_MAIN
SRC_4U = os.path.join(ROOT, 'dump/romfs/data/em089.arc')
OUT_ARC = os.path.join(MON, 'romfs/nativeNX/arc/enemy/em089_00.arc')
OUT_ARC_KUSHALA = os.path.join(MON, 'romfs-kushala-model/nativeNX/arc/enemy/em089_00.arc')
RATHIAN_COPY = os.path.join(MON, 'romfs-rathian/nativeNX/arc/enemy/em089_00.arc')
OUT_JSON = os.path.join(HERE, 'em089_manifest.json')

FILES_TABLE = 0x1732A68          # registry index -> manifest (51 x s32 file IDs)
FILEID_TABLE = 0x15A0CE0         # file ID -> (path hash, type hash), 8 B, entry = ID
import alloc
ALLOC = alloc.monster('gogmazios')
FILE_ID_BASE, FILE_ID_LAST = ALLOC['file_ids']   # IDs served by the module (allocations.toml; the game's end at 0x106D0)
DONOR, DONOR_INDEX = 'em024_00', ALLOC['donor_index']   # Kushala Daora: elder dragon, 49 bones, 4 motion lists

T = dict(MOD=0x58A15856, MRL=0x2749C8A8, TEX=0x241F5DEB, LMT=0x76820D81, XFS=0x7CD0E77E, EMC=0x3AABBA02,
         BDD=0x1AC7B52D, DTB=0x59D9C3DA, EMD=0x0A0E48D4)
EM_DATA_4U = os.path.join(ROOT, 'dump/romfs/data/em_data.arc')
DTB_SCALE, EMD_SCALE = 0x15, 0x0C      # model scale: GU dtbase f32 offset, 4U emd f32 offset
# tar meshes (4U materials *_liquid_*) are pushed this far (model units, cube side 2087 = 32767 position steps,
# so 2.0 = 31 steps) along their normals: they are coplanar copies of body triangles that 4U separates only with
# RSMeshBias5..12; with exactly equal depths GU draws whichever comes first if the bias is not honoured.
# 2.0: in game only the head tar and the tail tip showed (groups 6/9/11/14/22 visible per the spawn log), so
# 20.0 made the arm tar appear (depth confirmed; head/arms/tail-tip match the 4U spawn state per the tar state
# machine); 8.0 = a smaller lift that should still clear the body (2.0 did not on the arms).
TAR_LIFT = 8.0
P = 'enemy\\em089\\em089_00\\'
FIELD_KIND = {0: 'model', 1: 'model (tail)', 2: 'model (alt)', 3: 'model data (XFS)', 4: 'motion 0', 5: 'motion 1',
              6: 'motion 2', 7: 'motion 3', 8: 'motion 4', 11: 'camera', 12: 'sound call', 13: 'sound bank',
              14: 'pts c', 15: 'pts u', 16: 'pel c', 17: 'pel u', 18: 'psl 0', 19: 'psl 1', 20: 'psl 2',
              21: 'psl 3', 22: 'psl 4', 25: 'shell arc', 26: 'attackdata', 28: 'hitsize', 30: 'bodydata',
              31: 'cambodydata', 32: 'dtbase', 33: 'dttune', 34: 'dtbparts', 35: 'actiontune', 37: 'cmdtbl',
              38: 'doumouka', 39: 'doumouka G', 40: 'area_link', 41: 'area_eat', 42: 'map_info',
              43: 'area_select', 44: 'area_patrol', 45: 'option motion', 46: 'hagi s0', 47: 'hagi s1',
              48: 'hagi s2', 49: 'hagi s3', 50: 'hagi s4'}
RENAMED = [3, 11, 26, 28, 30, 31, 32, 33, 34, 35, 37, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50]   # donor, own IDs
KEPT = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 25, 45]                                      # donor IDs


def phash(path):
    return zlib.crc32(path.encode('ascii')) ^ 0xFFFFFFFF


def u32(img, a):
    return struct.unpack_from('<I', img, a)[0]


def manifest_of(img, index):
    return list(struct.unpack_from('<51i', img, u32(img, FILES_TABLE + 4 * index)))


def fileid_entry(img, fid):
    return struct.unpack_from('<II', img, FILEID_TABLE + 8 * fid)

# ------------------------------------------------------------------ conversions

def world_positions(m):
    """bind-pose position per bone index (row-vector matrices, translation in the last row)."""
    W = []
    for i, b in enumerate(m['bone_list']):
        L = np.array(m['local'][i]).reshape(4, 4)
        W.append(L @ W[b['parent']] if b['parent'] != 255 else L)
    return np.array([w[3, :3] for w in W])


def bone_id_map(donor_mod, gog_mod):
    """donor bone IDs Gogmazios lacks -> the Gogmazios bone ID nearest in normalised bind position."""
    def norm(m):
        p = world_positions(m)
        mn, mx = np.array(m['aabb'][:3]), np.array(m['aabb'][4:7])
        return (p - (mn + mx) / 2) / (mx - mn).max()
    pd, pg = norm(donor_mod), norm(gog_mod)
    ids_d = {i: donor_mod['remap'][i] for i in range(256) if donor_mod['remap'][i] != 255}   # id -> index
    ids_g = {i: gog_mod['remap'][i] for i in range(256) if gog_mod['remap'][i] != 255}
    out = {}
    for bid, bi in ids_d.items():
        if bid in ids_g: continue
        best = min(ids_g, key=lambda g: np.linalg.norm(pg[ids_g[g]] - pd[bi]))
        out[bid] = best
    return out


def remap_bdd(b, idmap):
    """BDD (body data): u32 count at +8, 44-byte records from +0x10 starting with u16 bone A, u16 bone B."""
    assert b[:4] == b'BDD\0'
    b = bytearray(b); n = struct.unpack_from('<I', b, 8)[0]; changed = []
    for k in range(n):
        for o in (0, 2):
            v = struct.unpack_from('<H', b, 0x10 + 44 * k + o)[0]
            if v in idmap:
                struct.pack_into('<H', b, 0x10 + 44 * k + o, idmap[v]); changed.append((k, v, idmap[v]))
    return bytes(b), changed


# 4U em089 hitsize names bone 13, which em089.mod does not have (4U tolerates it, GU's joint lookup may not).
# Records 3->13 (r 200) and 4->13 (r 100) are head capsules: 13 -> 201, the head-tip bone on the 3-4-201 axis
# (bind z 680 / 710 / 815). GUESS: no 4U/GU model holds bone 13 next to this chain.
HTS_BONE_FIX = {13: 201}


def hts_bones(b):
    """HTS (hitsize): (u32 count, u32 offset) per group from +0x10, 48-byte records {u16 bone A, u16 bone B,
    u16 shape (2 = capsule A-B, 0/1 = sphere on A), ...}. Yields (record offset, field offset, bone)."""
    assert b[:4] == b'HTS\0'
    for g in range(struct.unpack_from('<I', b, 8)[0]):
        c, o = struct.unpack_from('<II', b, 16 + 8 * g)
        for k in range(c):
            r = o + 48 * k
            a, bb, shape = struct.unpack_from('<HHH', b, r)
            yield r, 0, a
            if shape == 2: yield r, 2, bb


def remap_hts(b, idmap, valid):
    b = bytearray(b); changed = []
    for r, o, v in list(hts_bones(bytes(b))):
        if v in idmap:
            struct.pack_into('<H', b, r + o, idmap[v]); changed.append((v, idmap[v]))
    bad = sorted({v for _, _, v in hts_bones(bytes(b)) if v not in valid and v != 255})
    assert not bad, 'hitsize names bones missing from the model: %s' % bad
    return bytes(b), sorted(set(changed))


# ------------------------------------------------------------------ em089 shell family (tar blobs, uShell050)
# Gogmazios' own projectile family = a copy of Kushala's shell\em\em024_00_shell00 (XFS 0x4aa69872 shell def with
# 26 entries of ef/snd/hit/sh params, ShellCmnParam FUP, HDS, HTS) under shell\em\em089_00_shell00\em089_00_00.
# Only the def names the other files (same-length path rename); its effect/sound lists stay Kushala's
# (effect\pel\em\em024_00u, sound\pts\em\em024_00u, kept in the arc). HDS / HTS come from 4U uShell050's inline data.
CODE_4U = os.path.join(ROOT, 'dump/exefs_v11/code.bin')     # MH4U v1.1 code, loaded at 0x100000
CODE_4U_BASE = 0x100000
SHELL_REC_4U = 0x1031990        # 4U uShell050 attack records, 40 B (0x9ab120 -> 0x9a9624 -> 0xb700f8 reads them)
SHELL_VOL_4U = 0x1031690        # 4U volume table: record byte 0x19 indexes it -> 40-B hitsize records, 0xFFFF end
# 4U uShell016 (breath / beam attack shells, module/em089_shell016.c): records at 0x102b370 + 96, volume table at
# 0x102b370 (0x9ab120(shell, base + 96, base, index, 31, 2) in its init 0xc69ddc). em089's subtypes use records
# 31, 32, 36, 40, 41, 42 -> HDS entries 4..9; their volumes (byte 0x19 = 18 / 20 / 22: capsules on bone 1001, radius
# 330 / 70 / 30) -> HTS groups 1..3 (byte 0x19 remapped).
S016_BASE_4U = 0x102b370
S016_RECS = (31, 32, 36, 40, 41, 42)
S016_VOLS = (18, 20, 22)
# 4U uShell051 (generic ground shell, module/em089_shell051.c): init 0xc8fda4 arms 0x9ab120(shell, base + 52, base,
# record = subtype, ...) with base 0x1031ca4. Subtypes posted by em089's shells: 1 (= 16), 3, 6 (= 17 / 19 / 20),
# 9-15 -> HDS entries 10..19; volumes 1 / 2 / 3 / 6 / 9 / 10 (spheres on bone 255, radius 220 / 250 / 214 / 260 /
# 105 / 175) -> HTS groups 4..9.
S051_BASE_4U = 0x1031ca4
S051_RECS = (1, 3, 6, 9, 10, 11, 12, 13, 14, 15)
S051_VOLS = (1, 2, 3, 6, 9, 10)
# 4U uShell005 (quake / tremor shell of 0x954e5c, module/em089_shell005.c): init 0xc59698 arms 0x9ab120(shell,
# base + 112, base, record = subtype, ...) with base 0x1025b58. em089 (2/35) posts subtype 1 -> HDS entry 20 (power 0,
# attack type 6, window 14 + 10, byte 0x1c = 1 kept); volume 0 (sphere on bone 255, radius 600) -> HTS group 10.
S005_BASE_4U = 0x1025b58
S005_RECS = (1,)
S005_VOLS = (0,)
# uShell051 end posts (end function 0xc906d8 -> 0x6635e8): subtypes 4 (after 2 / 13 / 15), 5 (after 3), 8 (after 7 /
# 9-12), 18 (after 14) -> HDS entries 21..24 (appended after uShell005's entry 20, so every older index stays): power
# 100 / 80 / 80 / 80, attack type 3, windows 0 + 88 / 20 / 15 / 20; volumes 4 / 5 / 8 / 11 (spheres on bone 255,
# radius 300 / 562.5 / 500 / 560) -> HTS groups 11..14.
S051E_RECS = (4, 5, 8, 18)
S051E_VOLS = (4, 5, 8, 11)
# 4U uShell022 kind 10 (the fallen-spear pile bunker hit, module/em089_pile.c): init 0xc753c0 arms 0x9ab120(shell,
# 0x102c7b8, 0x102c784, kind 10, 2, 8) -> HDS entry 25 (= the arena Dragonator record: power 255 window 0 + 180,
# attack type 0x20); volume 0 = 0x102cb18 (sphere on bone 1001, radius 500) -> HTS group 15.
S022_REC_4U = 0x102c7b8
S022_VOL_4U = 0x102c784
S022_PILE = 10
SHELL_SRC = 'shell\\em\\em024_00_shell00\\em024_00_00'
SHELL_DST = 'shell\\em\\em089_00_shell00\\em089_00_00'
HDS, HTS_T, SHELL_XFS = 0x4EB68CEE, 0x5653C1B0, 0x4AA69872


def shell_hds(code, template):
    """HDS (56-B entries) from the 4 4U records. Field map checked in both readers: GU 0x168e98 and 4U 0xb700f8 read
    bytes 0x00..0x23 at the same offsets (s16 0/2, u16 power 4, u8 type 6, u16 8, u8 a/b, u32 c/10/14, u8 18 (0x19
    = volume index, read by 0x4a2790 / 0x9a9624), u16 1a, u8 1c, s8 1d, u8 1e/1f/20/21/22/23). Differences:
      - byte 0x12: 4U packs a level in bits 2+; GU keeps only bits 0-1 there and reads the level from +0x2c
        (slot+0x9e, table 0x173ec24 {0,5,15,25,40,50,100,200}), as GU HDE moved it to byte 31 (emdata4u.attackdata;
        195+44 of the aligned 4U/GU attack records agree).
      - byte 0x1c: 0 in every 4U record (also etd attackdata), 6..10/254 in GU (6 = commonest, Kushala's) -> 6.
      - 0x24..0x37 are GU-only: +0x28 f32 = 1.0 (all 1237 GU HDS entries), +0x26/+0x2e/+0x30 read only for owner
        types 0/2 (monsters are 1), 0 in GU data."""
    assert template[:4] == b'HDS\0'
    recs = []
    srcs = [(SHELL_REC_4U + 40 * i, None) for i in range(4)]
    srcs += [(S016_BASE_4U + 96 + 40 * i, S016_VOLS) for i in S016_RECS]     # entries 4..9 (uShell016)
    srcs += [(S051_BASE_4U + 52 + 40 * i, S051_VOLS) for i in S051_RECS]     # entries 10..19 (uShell051)
    srcs += [(S005_BASE_4U + 112 + 40 * i, S005_VOLS) for i in S005_RECS]    # entry 20 (uShell005 quake)
    srcs += [(S051_BASE_4U + 52 + 40 * i, S051E_VOLS) for i in S051E_RECS]   # entries 21..24 (uShell051 end posts)
    group0 = {S016_VOLS: 1, S051_VOLS: 1 + len(S016_VOLS),                    # first HTS group of each set
              S005_VOLS: 1 + len(S016_VOLS) + len(S051_VOLS),
              S051E_VOLS: 1 + len(S016_VOLS) + len(S051_VOLS) + len(S005_VOLS)}
    for a, vols in srcs:
        o = a - CODE_4U_BASE
        r4 = code[o:o + 40]
        assert (r4[0x1c] == 0 or vols is S005_VOLS) and not any(r4[0x24:0x28]), r4.hex()
        assert (r4[0x19] == 0) if vols is None else (r4[0x19] in vols), r4.hex()
        r = bytearray(56)
        r[0:0x24] = r4[0:0x24]
        r[0x12] = r4[0x12] & 3
        r[0x1c] = r4[0x1c] or 6       # uShell005 records carry a real 4U value (1): kept
        struct.pack_into('<f', r, 0x28, 1.0)
        r[0x2c] = r4[0x12] >> 2
        if vols is not None:
            r[0x19] = group0[vols] + vols.index(r4[0x19])             # HTS group (see shell_hts)
        recs.append(bytes(r))
    # entry 25: uShell022 kind 10 (pile); byte 0x1c is 0xff in 4U -> 8, GU's own st003 Dragonator entries' value
    o = S022_REC_4U + 40 * S022_PILE - CODE_4U_BASE
    r4 = code[o:o + 40]
    assert r4[0x19] == 0 and r4[0x1c] == 0xff and r4[6] == 0x20 and not any(r4[0x24:0x28]), r4.hex()
    r = bytearray(56)
    r[0:0x24] = r4[0:0x24]
    r[0x12] = r4[0x12] & 3
    r[0x1c] = 8
    struct.pack_into('<f', r, 0x28, 1.0)
    r[0x2c] = r4[0x12] >> 2
    r[0x19] = 1 + len(S016_VOLS) + len(S051_VOLS) + len(S005_VOLS) + len(S051E_VOLS)   # HTS group 15
    recs.append(bytes(r))
    ver = struct.unpack_from('<I', template, 4)[0]
    return struct.pack('<4sIII', b'HDS\0', ver, len(recs), 0) + b''.join(recs)


def shell_hts(code, template):
    """HTS = Kushala's family-00 file (1 group, 1 sphere on bone 1001 = the shell itself) with the 4U radius.
    4U record (volume table entry 0, the only one the 4 records use) = GU 48-B record minus 8 tail bytes, the same
    layout emdata4u.hitsize converts: bone 1001, shape 0, f32 radius +0x0c. GU +0x0a holds 0x0848 in all 1044 GU
    shell HTS records (4U: 0) and is kept."""
    p = struct.unpack_from('<I', code, SHELL_VOL_4U - CODE_4U_BASE)[0]
    v4 = code[p - CODE_4U_BASE:p - CODE_4U_BASE + 42]
    assert struct.unpack_from('<HHH', v4, 0) == (1001, 0, 0) and struct.unpack_from('<H', v4, 40)[0] == 0xFFFF
    assert template[:4] == b'HTS\0' and struct.unpack_from('<III', template, 8) == (1, 0, 1)
    off = struct.unpack_from('<I', template, 0x14)[0]
    t = bytearray(template)
    assert bytes(t[off:off + 10]) == v4[:10] and not any(t[off + 16:off + 48]) and not any(v4[16:40])
    t[off + 12:off + 16] = v4[12:16]
    # groups 1..3: the uShell016 capsules (4U volume table S016_BASE_4U[18 / 20 / 22] -> one 40-B record each,
    # bone 1001, shape 1, radius +0x0c; GU record = 4U + 8 zero bytes, +0x0a = 0x0848 as in group 0).
    # File layout: 16-B header (count at +8), count x (records, offset), then 48-B records.
    assert len(t) == off + 48
    rec0 = bytes(t[off:off + 48])
    groups = [rec0]
    # groups 4..9: the uShell051 spheres (bone 255 = the shell, shape 0), same conversion
    for base, v, bone in ([(S016_BASE_4U, v, 1001) for v in S016_VOLS] + [(S051_BASE_4U, v, 255) for v in S051_VOLS]
                          + [(S005_BASE_4U, v, 255) for v in S005_VOLS]
                          + [(S051_BASE_4U, v, 255) for v in S051E_VOLS]     # groups 11..14: uShell051 end posts
                          + [(S022_VOL_4U, 0, 1001)]):                       # group 15: uShell022 kind 10 (pile)
        p = struct.unpack_from('<I', code, base + 4 * v - CODE_4U_BASE)[0]
        r4 = code[p - CODE_4U_BASE:p - CODE_4U_BASE + 42]
        assert struct.unpack_from('<HH', r4, 0) == (bone, 0) and struct.unpack_from('<H', r4, 40)[0] == 0xFFFF, r4.hex()
        assert not any(r4[16:40]), r4.hex()
        r = bytearray(48)
        r[0:40] = r4[0:40]
        r[0x0a:0x0c] = rec0[0x0a:0x0c]
        groups.append(bytes(r))
    n = len(groups)
    head = bytearray(t[:16])
    struct.pack_into('<I', head, 8, n)
    table_end = 16 + 8 * n
    table = b''.join(struct.pack('<II', 1, table_end + 48 * i) for i in range(n))
    t = bytes(head) + table + b''.join(groups)
    return t, struct.unpack_from('<f', v4, 12)[0], struct.unpack_from('<f', template, off + 12)[0]


def shell_family(dents):
    """[(path, type, data)] of em089's family in the donor's order (def last), + a note."""
    code = open(CODE_4U, 'rb').read()
    out = []
    for p, t, d in dents:
        if not p.startswith(SHELL_SRC): continue
        np_ = SHELL_DST + p[len(SHELL_SRC):]
        if t == SHELL_XFS:
            n = d.count(SHELL_SRC.encode())
            d = d.replace(SHELL_SRC.encode(), SHELL_DST.encode())
            assert n == 107 and b'em024_00_shell00' not in d, n      # 26 x 4 params + cmn + HDS + HTS
        elif t == HDS:
            d = shell_hds(code, d)
        elif t == HTS_T:
            d, r4, rgu = shell_hts(code, d)
        out.append((np_, t, d))
    assert sum(t == SHELL_XFS for _, t, _ in out) == 1 and len(out) == 108, len(out)
    return out, 'shell family %s: %d files from %s; HDS from 4U 0x%x, HTS radius %.1f (4U) instead of %.1f' % (
        SHELL_DST, len(out), SHELL_SRC, SHELL_REC_4U, r4, rgu)


def emc_to_gu(b):
    """4U EMC has 23 groups, GU 21; 4U's last two are empty. Keep every offset: rows 21-22 become padding."""
    magic, ver, ng, _ = struct.unpack_from('<4sIII', b, 0)
    assert magic == b'EMC\0' and ver == 0x20120804 and ng == 23
    for g in (21, 22):
        assert struct.unpack_from('<I', b, 16 + 16 * g)[0] == 0, 'group %d not empty' % g
    b = bytearray(b)
    struct.pack_into('<I', b, 8, 21)
    b[16 + 16 * 21:16 + 16 * 23] = bytes(32)
    return bytes(b)


def main():
    use_gog_emc = '--cmdtbl' in sys.argv and sys.argv[sys.argv.index('--cmdtbl') + 1] == 'gog'
    kushala_model = '--kushala-model' in sys.argv
    img = open(MAIN_IMG, 'rb').read()
    rom = RomFS(GU_ROMFS)
    _, src = arcpack.read(open(SRC_4U, 'rb').read())
    S = {(p, t): d for p, t, d in src}
    donor_arc = '/nativeNX/arc/enemy/%s.arc' % DONOR
    _, dents = arcpack.read(rom.read(donor_arc))
    D = {(p, t): d for p, t, d in dents}
    dhash = {(phash(p), t): (p, t) for p, t, _ in dents}
    dman = manifest_of(img, DONOR_INDEX)
    dfield = {}
    for k, fid in enumerate(dman):
        if fid != -1:
            dfield[k] = (fid,) + dhash[fileid_entry(img, fid)]
    entries = []              # (path, type, data)
    notes = []

    # ---- textures
    TEXMAP = {'em089_01_BM': ('01_BM', 'bc3'), 'em089_02_BM': ('02_BM', 'bc3'), 'em089_03_BM': ('03_BM', 'bc3'),
              'em089_04_BM': ('04_BM', 'bc3'), 'em089_05_BM': ('05_BM', 'bc3'), 'em089_04_NM': ('04_NM', 'bc5')}
    gu_tex = {}
    for name, (suffix, fmt) in TEXMAP.items():
        t = tex.decode(S[('enemy\\em089\\mod\\' + name, T['TEX'])])
        path = P + 'mod\\em089_00_' + suffix
        entries.append((path, T['TEX'], tex.encode_gu(t, fmt)))
        gu_tex[name] = path
        if name.endswith('_BM'):
            # GU specular map '<BM>+A' = the BM alpha (4U specular mask) in R, G, B, alpha 255 (GU em001_00_BM+A
            # mean 50 = em001_00_BM alpha mean; em004 NM_MIRROR+A the same layout). Using the BM itself as
            # tSpecularMap made the specular/env reflection follow the albedo colour: grey, washed-out body.
            s = np.empty_like(t); s[..., 0] = s[..., 1] = s[..., 2] = t[..., 3]; s[..., 3] = 255
            entries.append((path + '+A', T['TEX'], tex.encode_gu(s, fmt)))
            gu_tex[name + '+A'] = path + '+A'

    # ---- models + materials
    models = {'em089': 'em089_00', 'em089_tail': 'em089_00_tail', 'em089_gekiryusou': 'em089_00_gekiryusou'}
    gog_mod = modlib.parse(S[('enemy\\em089\\mod\\em089', T['MOD'])])
    for src_name, dst_name in models.items():
        d4 = S[('enemy\\em089\\mod\\' + src_name, T['MOD'])]
        m4 = modlib.parse(d4)
        r4 = mrl.read(S[('enemy\\em089\\mod\\' + src_name, T['MRL'])])
        anims4 = mrl_anim.material_anims(S[('enemy\\em089\\mod\\' + src_name, T['MRL'])])[1]
        tex_paths, tex_index = [], {}
        mats = []
        # tar (4U *_liquid_*): alpha-tested, per-vertex alpha -> split into vertex-alpha class materials
        # (tar-look agent 2026-10-18; mod4u2gu.VALPHA_CLASSES / split_names, mrl_anim.TRACK_MAP diffuse)
        tar_names = [n for n in m4['material_names'] if '_liquid_' in n]
        for gname, mname, valpha in mod4u2gu.split_names(m4['material_names'], set(tar_names)):
            mm = [x for x in r4['mats'] if x['name'] == mrl_build.name_hash(mname)]
            assert mm, (src_name, mname)
            mm = mm[0]
            states = [s for s in mm['states'] if s]
            slots = {n: v for n, _, v in mm['params'] if n in ('tAlbedoMap', 'tNormalMap')}
            gslots = {}
            for slot, v in slots.items():
                if v == 0: continue
                src_tex = r4['textures'][v - 1][1].split('\\')[-1]
                for sl, gp in ((slot, gu_tex[src_tex]),) + \
                        ((('tSpecularMap', gu_tex[src_tex + '+A']),) if slot == 'tAlbedoMap' else ()):
                    if gp not in tex_index:
                        tex_paths.append(gp); tex_index[gp] = len(tex_paths)
                    gslots[sl] = tex_index[gp]
            # lit vs unlit from the 4U CBMaterialStd: emissive (emission > 0, diffuse 0) = eye -> 'unlit'
            std = struct.unpack_from('<8f', mm['block'], 0x60)       # emission rgba, diffuse rgba
            emissive = max(std[0:3]) > 0 and max(std[4:7]) == 0
            key = 'add' if 'BSAddAlpha' in states or 'BSBlendAlpha' in states else \
                  ('solid_nm' if 'tNormalMap' in gslots else 'unlit' if emissive else 'solid')
            # alpha-tested in 4U (MRL w7 bit 24 on a BSSolid material: tar ref 75, wing ref 40; mrl_build W7_*)
            alpha_test = 'BSSolid' in states and mm['words'][7] & mrl_build.W7_ALPHATEST
            if valpha is not None:
                key = 'tar'
            elif alpha_test:
                key = 'solid_at' if 'tNormalMap' not in gslots else 'tar'
            # 4U raster states (tar: RSMeshBias5/10/12, body RSMeshBias2) -> mrl_build.state_word (D's request)
            # Tar agent: (1) the 4U 'Solid' animation's first frame baked into the GU constants (mapping
            # mrl_anim.TRACK_MAP: albedo tint -> fAlbedoColor, specular rgb * gloss -> fSpecularColor); (2) the
            # tar materials' 4U animation blocks converted to GU's (same names and order: Sol_to_Liq.. Gas), Solid
            # flagged autoplay so it runs without code; (3) material type = the name's 'mNN' (GU w6 bits 21-28:
            # tar m01..m05 = types 1..5 that module/em089_tar.c looks for, as 4U slot 39 does).
            # Tar-look agent: (4) the 4U diffuse rgba (w = material alpha) mapped too (fDiffuseColor + fTransparency,
            # w scaled by the vertex-alpha class), template 'tar' (alpha-tested GU overlay), w7 alpha reference and
            # depth-bias nibble = the 4U entry's w7 (tar: ref 75, bias 5/10/12). Solid's w is 0 -> tar hidden.
            # (5) every 4U-animated material (tar, wing type 50 Small..Large, lights type 6 Light_*) gets its blocks
            # converted; constants = the 4U material's own CBMaterialStd (only the variables its tracks drive, so the
            # stopped state matches 4U; the rest stays the template's), then the spawn entry's first
            # frame (tar 'Solid', wing 'Small' = 4U slot 39 [0x8ba04c]), which also autoplays; the lights start
            # stopped (slot 39 plays index -1). (6) w7 depth-bias nibble = the 4U w7 for every material (= its RS
            # state, as in all GU MRLs), alpha reference for the alpha-tested ones.
            consts, extra = {}, {}
            mt = re.search(r'_m(\d\d)_', mname)
            if mt: extra['mtype'] = int(mt.group(1))
            ents4 = anims4.get(mm['name'], [])
            alpha = 1.0 if valpha is None else valpha
            w7 = mm['words'][7]
            extra['bias'] = (w7 >> 16) & 0xF
            if alpha_test:
                extra['alpha_ref'] = (w7 >> 8) & 0xFF
            if ents4:
                std_off = [v for n, t, v in mm['params'] if t == 1 and n == 'CBMaterialStd'][0]
                anim_vars = mrl_anim.animated_targets(ents4)      # only the variables the tracks drive
                consts.update({k: v for k, v in mrl_anim.static_constants(mm['block'][std_off:], alpha).items()
                               if k in anim_vars})
                spawn = [e for e in ents4 if mrl_anim.HASHNAME.get(e['name']) in ('Solid', 'Small')]
                if spawn:
                    consts.update(mrl_anim.solid_constants(spawn[0], alpha))
                extra['anim'] = mrl_anim.build(mrl_anim.gu_entries(ents4, mrl_build.cb_words(rom, key),
                                                                   autoplay=('Solid', 'Small'), alpha=alpha))
            mats.append((gname, key, gslots, [s for s in states if s.startswith('RS')], consts, extra))
        # tar meshes lifted along their normals (mod4u2gu.convert push): 4U relies on the depth bias alone
        push = {n: TAR_LIFT for n in tar_names}
        mod_bytes = mod4u2gu.convert(d4, push, valpha=tar_names)
        mrl_bytes = mrl_build.build(rom, mats, tex_paths)
        assert [m[0] for m in mats] == modlib.parse(mod_bytes)['material_names'], 'MOD / MRL material lists differ'
        if kushala_model and dst_name in ('em089_00', 'em089_00_tail'):
            kp = 'enemy\\em024\\em024_00\\mod\\' + dst_name.replace('em089', 'em024')
            mod_bytes, mrl_bytes = D[(kp, T['MOD'])], D[(kp, T['MRL'])]
            notes.append('%s: DIAGNOSTIC, holds Kushala\'s original %s MOD + MRL' % (dst_name, kp))
        # MRL before MOD, as in the game's arcs: a model fetches its materials by path while it loads, and a
        # model packed before its MRL loads without materials and is never drawn (in-game test 2026-10-17)
        entries.append((P + 'mod\\' + dst_name, T['MRL'], mrl_bytes))
        entries.append((P + 'mod\\' + dst_name, T['MOD'], mod_bytes))
        notes.append('%s: %d materials -> templates %s' % (dst_name, len(mats), [m[1] for m in mats]))

    # ---- motion lists
    for i in range(4):
        entries.append((P + 'mot\\em089_00_%d' % i, T['LMT'], S[('enemy\\em089\\mot\\em089_%d' % i, T['LMT'])]))

    # ---- 4U command table in GU group layout (not in the manifest unless --cmdtbl gog)
    gog_emc_path = 'enemy\\cmd_tbl\\em089_00_cmdtbl_4u'
    entries.append((gog_emc_path, T['EMC'], emc_to_gu(S[('enemy\\em089\\data\\em089_cmd', T['EMC'])])))

    # ---- donor placeholders, renamed
    _, emdata = arcpack.read(open(EM_DATA_4U, 'rb').read())
    emd = [d for p, t, d in emdata if p == 'enemy\\em089\\data\\em089' and t == T['EMD']][0]
    gog_scale = struct.unpack_from('<f', emd, EMD_SCALE)[0]
    donor_mod = modlib.parse(D[('enemy\\em024\\em024_00\\mod\\em024_00', T['MOD'])])
    idmap = bone_id_map(donor_mod, gog_mod)
    # Gogmazios' own data, converted from its 4U em_data (emd/etd); dtbase/dttune come from
    # tools/dt_convert.py (needs the unicorn venv), precomputed into dump/converted/em089/
    d4 = emdata4u.load_4u('em089')
    donor_xfs = D[dfield[3][1:]]
    gog_ids = {i for i in range(256) if gog_mod['remap'][i] != 255}   # converted MOD keeps 4U's bone IDs
    for kind, w in (('bodydata', 8), ('cambodydata', 9)):
        b = emdata4u.bodydata(d4['emd'], w)
        n = struct.unpack_from('<I', b, 8)[0]
        bad = {struct.unpack_from('<H', b, 16 + 44 * k + o)[0] for k in range(n) for o in (0, 2)} - gog_ids - {0xFFFF}
        assert not bad, '%s names bones missing from the model: %s' % (kind, sorted(bad))
    converted = {
        26: (emdata4u.attackdata(d4['etd']), 'attackdata from 4U etd word 28 (61 attacks, 4U attack IDs)'),
        28: (remap_hts(emdata4u.hitsize(d4['etd']), HTS_BONE_FIX, gog_ids)[0],
             'hitsize from 4U etd word 27 (4U bone IDs = model IDs; 13 -> 201)'),
        30: (emdata4u.bodydata(d4['emd'], 8), 'bodydata from 4U emd word 8 (own skeleton bone IDs)'),
        31: (emdata4u.bodydata(d4['emd'], 9), 'cambodydata from 4U emd word 9'),
        3: (emdata4u.partsvis(d4['emd'], donor_xfs, [x['group'] for x in gog_mod['mesh_list']])[0],
            'parts visibility: 4U rows in the donor\'s 12-state layout'),
        11: (lcm4u2gu.convert(S[('enemy\\em089\\mot\\e089_cam', 0x39C52040)]),
             'camera list from 4U e089_cam (LCM v4 -> v5, tools/lcm4u2gu.py; ids = 4U ids of the camera events)'),
    }
    for k, kind in ((32, 'dtbase'), (33, 'dttune')):
        pre = os.path.join(ROOT, 'dump/converted/em089/%s.bin' % kind)
        if os.path.exists(pre):
            converted[k] = (open(pre, 'rb').read(), '%s: donor object + Gogmazios 4U fields/blocks (dt_convert)' % kind)
    import hagi_em089                    # carves: 4U G body / tail / shiny tables in s4, GU's filler in s0..s3
    for k, data in hagi_em089.files().items():
        converted[k] = (data, '%s from 4U (tools/hagi_em089.py)' % FIELD_KIND[k])
    converted_fields = {}
    renamed_path = {}
    for k in RENAMED:
        if k not in dfield: continue
        fid, path, typ = dfield[k]
        data = D[(path, typ)]
        if typ == T['BDD'] and k not in converted:   # donor placeholder only (fields 30/31 are converted now)
            data, changed = remap_bdd(data, idmap)
            notes.append('field %d %s: bone IDs remapped %s' % (k, path.split('\\')[-1],
                         sorted({(a, b) for _, a, b in changed})))
        if typ == T['DTB']:
            # model scale: GU dtbase f32 @0x15 == 4U emd f32 @0xC (equal on 40 of 41 shared monsters; Kushala
            # 0.8, Kirin 2.3); Gogmazios' own value replaces the donor's, nothing else in the file changes
            data = bytearray(data)
            old = struct.unpack_from('<f', data, DTB_SCALE)[0]
            struct.pack_into('<f', data, DTB_SCALE, gog_scale)
            data = bytes(data)
            notes.append('field %d %s: model scale %.3g (donor) -> %.3g (4U emd)' % (k, path.split('\\')[-1], old,
                                                                                  gog_scale))
        if k in converted:                   # Gogmazios' own data replaces the donor's (tools/emdata4u.py etc.)
            data, how = converted[k]
            converted_fields[k] = how
            notes.append('field %d: CONVERTED %s' % (k, how))
        new = path.replace('em024', 'em089')
        renamed_path[k] = (new, typ)
        entries.append((new, typ, data))

    # ---- donor effect / sound / shell chain, original paths (everything not replaced above)
    drop = {(dfield[k][1], dfield[k][2]) for k in RENAMED if k in dfield}
    drop |= {(p, t) for p, t, _ in dents if p.startswith('enemy\\em024\\em024_00\\mod\\em024_00')
             and t in (T['MOD'], T['MRL'])}
    drop |= {(dfield[k][1], dfield[k][2]) for k in (4, 5, 6, 7, 8) if k in dfield}
    have = {(p, t) for p, t, _ in entries}
    kept = 0
    for p, t, d in dents:
        if (p, t) in drop or (p, t) in have: continue
        entries.append((p, t, d)); kept += 1

    # ---- Gogmazios' own shell family (tar blobs; module/em089_shell.c EM089_SHELL_FILE = its def's file ID)
    shell_entries, shell_note = shell_family(dents)
    entries += shell_entries
    notes.append(shell_note)

    # ---- Gogmazios' own sound (tools/snd4u2gu.py: 4U sound call / waves / bank / request -> GU, sound agent);
    # --donor-sound keeps Kushala's (manifest 12 / 13 = donor IDs) for bisecting. The donor's sound files stay in
    # the arc either way (its common bank snd_com_qst + waves are the request's bank 1).
    use_gog_sound = '--donor-sound' not in sys.argv
    if use_gog_sound:
        import snd4u2gu
        snd_log = []
        snd_entries = snd4u2gu.em089_entries(rom=rom, log=snd_log)
        snd4u2gu.verify(snd_entries)
        have = {(p, t) for p, t, _ in entries}
        assert not any((p, t) in have for p, t, _ in snd_entries), 'sound paths clash with the donor'
        entries += snd_entries
        notes += snd_log
    # em089's battle themes: own STQR sound\bgm\battle\bgm_em089 (tools/snd_bgm.py; GU loads bgm_bt from
    # loc/arc/quest.arc, so the themes ride in this arc and module/em089_bgm.c redirects ids 0x900 / 0x901 to it)
    bgm_stqr = os.path.join(ROOT, 'dump/converted/bgm_em089.stqr')
    BGM_STQR_PATH, T_STQR = 'sound\\bgm\\battle\\bgm_em089', 0x167DBBFF
    use_bgm = os.path.exists(bgm_stqr) and '--no-bgm' not in sys.argv
    if use_bgm:
        entries.append((BGM_STQR_PATH, T_STQR, open(bgm_stqr, 'rb').read()))
        notes.append('battle BGM STQR %s (%d B)' % (BGM_STQR_PATH, os.path.getsize(bgm_stqr)))

    # ---- Gogmazios' own effects (tools/efl4u2gu.py, effects agent): 4U EFL/EAN/TEX/effect models under their 4U
    # paths, PEL u from the 4U MEF, PSL x4 from the 4U LMT motion events. --donor-efx keeps Kushala's (manifest
    # 17..21 = donor IDs) for bisecting; the donor's effect files stay in the arc either way (its PEL c = GU common
    # effects, its shell family's pel list).
    use_gog_efx = '--donor-efx' not in sys.argv
    if use_gog_efx:
        import efl4u2gu
        efx_log = []
        efx_entries = efl4u2gu.entries(efx_log)
        have = {(p, t) for p, t, _ in entries}
        assert not any((p, t) in have for p, t, _ in efx_entries), 'effect paths clash'
        entries += efx_entries
        notes.append('effects: %d entries (tools/efl4u2gu.py); %d log lines' % (len(efx_entries), len(efx_log)))

    # ---- manifest + file IDs
    new_files = []                       # (fid, path, type)
    def new_id(path, typ):
        for fid, p, t in new_files:
            if (p, t) == (path, typ): return fid
        fid = FILE_ID_BASE + len(new_files)
        assert fid <= FILE_ID_LAST, 'file IDs past the allocations.toml range: widen file_ids'
        new_files.append((fid, path, typ)); return fid
    manifest = [-1] * 51
    src_of = {}
    manifest[0] = new_id(P + 'mod\\em089_00', T['MOD']); src_of[0] = 'converted'
    manifest[1] = new_id(P + 'mod\\em089_00_tail', T['MOD']); src_of[1] = 'converted'
    for i in range(4):
        manifest[4 + i] = new_id(P + 'mot\\em089_00_%d' % i, T['LMT']); src_of[4 + i] = 'converted'
    for k, (path, typ) in renamed_path.items():
        manifest[k] = new_id(path, typ)
        src_of[k] = ('converted: ' + converted_fields[k]) if k in converted_fields else 'placeholder (%s, renamed)' % DONOR
    if use_gog_emc:
        manifest[37] = new_id(gog_emc_path, T['EMC']); src_of[37] = 'converted (4U command table)'
    for k in KEPT:
        if k in dfield:
            manifest[k] = dfield[k][0]; src_of[k] = 'placeholder (%s, original path + file ID)' % DONOR
    # same IDs with or without --cmdtbl gog: the 4U command table always takes the first extra ID (0x1071b)
    extra = {'cmdtbl_4u': new_id(gog_emc_path, T['EMC'])}
    extra['gekiryusou_model'] = new_id(P + 'mod\\em089_00_gekiryusou', T['MOD'])
    # field 2 = GU cut slot 1 (setup 0xb9fb4: type 2 when set) = 4U cut object 1, the falling Dragonator spear
    manifest[2] = extra['gekiryusou_model']; src_of[2] = 'converted (4U cut object 1: Dragonator spear)'
    extra['shell00'] = new_id(SHELL_DST, SHELL_XFS)     # appended after the existing IDs (0x1071d)
    if use_gog_sound:                                    # appended after shell00: 0x1071e call, 0x1071f request
        manifest[12] = new_id(snd4u2gu.PG_CALL, snd4u2gu.TG['CALL'])
        manifest[13] = new_id(snd4u2gu.PG_BANK, snd4u2gu.TG['REQ'])
        src_of[12] = 'converted (4U sound call, tools/snd4u2gu.py)'
        src_of[13] = 'converted (4U request + bank + waves, tools/snd4u2gu.py)'
    if use_gog_efx:                                      # appended after the sound IDs: PEL u, PSL 0..3
        manifest[17] = new_id(efl4u2gu.PEL_U, efl4u2gu.T['PEL'])
        src_of[17] = 'converted (4U MEF -> PEL u, tools/efl4u2gu.py)'
        for i in range(4):
            manifest[18 + i] = new_id(efl4u2gu.PSL[i], efl4u2gu.T['PSL'])
            src_of[18 + i] = 'converted (4U LMT %d motion events -> PSL, tools/efl4u2gu.py)' % i
    if use_bgm:                                          # appended after every other ID (module/em089_bgm.c)
        extra['bgm_stqr'] = new_id(BGM_STQR_PATH, T_STQR)

    # ---- verify before writing anything
    arc = arcpack.build(entries)
    ver, back = arcpack.read(arc)
    assert ver == 0x11 and len(back) == len(entries)
    present = {(phash(p), t) for p, t, _ in back}
    for fid, path, typ in new_files:
        assert (phash(path), typ) in present, path
    for k in KEPT:
        if manifest[k] != -1 and manifest[k] < FILE_ID_BASE:     # (12 / 13 are our own IDs with our sound)
            assert fileid_entry(img, manifest[k]) in present, (k, hex(manifest[k]))
    for p, t, d in back:
        if t == T['MOD'] and p.startswith(P): modlib.parse(d)
        if t == T['TEX'] and p.startswith(P): tex.decode(d)
    assert len({(p, t) for p, t, _ in back}) == len(back), 'duplicate entries'

    # ---- write
    if kushala_model:            # diagnostic arc only: same paths and file IDs, so the .inc/.json stay valid
        os.makedirs(os.path.dirname(OUT_ARC_KUSHALA), exist_ok=True)
        open(OUT_ARC_KUSHALA, 'wb').write(arc)
        print('DIAGNOSTIC arc: %d entries, %.1f MB -> %s' % (len(entries), len(arc) / 1e6, OUT_ARC_KUSHALA))
        for n in notes: print(' ', n)
        return
    os.makedirs(os.path.dirname(RATHIAN_COPY), exist_ok=True)
    if os.path.exists(OUT_ARC) and not os.path.exists(RATHIAN_COPY):
        shutil.copy2(OUT_ARC, RATHIAN_COPY)
    os.makedirs(os.path.dirname(OUT_ARC), exist_ok=True)
    open(OUT_ARC, 'wb').write(arc)

    fields = []
    for k in range(51):
        fid = manifest[k]
        if fid == -1:
            fields.append(dict(field=k, kind=FIELD_KIND.get(k, ''), file_id=-1)); continue
        if fid >= FILE_ID_BASE:
            _, path, typ = new_files[fid - FILE_ID_BASE]
        else:
            path, typ = dhash[fileid_entry(img, fid)]
        fields.append(dict(field=k, kind=FIELD_KIND.get(k, ''), file_id='0x%x' % fid, path=path,
                           type='0x%08x' % typ, path_hash='0x%08x' % phash(path), source=src_of[k]))
    js = dict(monster='em089_00 (Gogmazios)', id='0x59', registry_index=137, donor=DONOR,
              file_id_base='0x%x' % FILE_ID_BASE, file_count=len(new_files), manifest=fields,
              files=[dict(file_id='0x%x' % fid, path=p, type='0x%08x' % t, path_hash='0x%08x' % phash(p))
                     for fid, p, t in new_files],
              extra={k: '0x%x' % v for k, v in extra.items()},
              bone_id_remap={str(a): b for a, b in sorted(idmap.items())}, notes=notes)
    json.dump(js, open(OUT_JSON, 'w'), indent=1)

    # FILE section: the registry manifest of its index (51 file IDs, -1 = none, 0xCC bytes like the game's) and the
    # (path hash = ~crc32(path), type hash) of each file ID from FILE_ID_BASE (module file_id hook). The C code names
    # a few IDs itself (em089_bgm.c BGM STQR, em089_shell.c shell family): IDs only ever grow, so they stay valid.
    assert extra['shell00'] == 0x1071d and extra.get('bgm_stqr') == 0x10725, extra
    sec = portdata.Section('FILE')
    sec.u32(FILE_ID_BASE, len(new_files), *manifest)
    for fid, p, t in new_files:
        sec.u32(phash(p), t)
    print('wrote', portdata.write_section('gogmazios', sec))

    print('arc: %d entries, %.1f MB -> %s' % (len(entries), len(arc) / 1e6, OUT_ARC))
    print('new file IDs 0x%x..0x%x (%d); donor kept entries %d' % (FILE_ID_BASE, FILE_ID_BASE + len(new_files) - 1,
          len(new_files), kept))
    for n in notes: print(' ', n)
    print('bone ID remap (donor -> Gogmazios), used only on remaining donor BDD placeholders (none now):', idmap)


if __name__ == '__main__':
    main()
