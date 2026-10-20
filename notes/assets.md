# Asset formats: MH4U (3DS) -> MHGU (Switch), for Gogmazios (em089)

Status 2026-10-17. Tools in `tools/` (pure Python + numpy/Pillow, no installs). Nothing here has been loaded
in game yet: every check below is a file-level round trip or decode comparison.

## Summary

| Type (hash) | 4U | GU | Port status |
|---|---|---|---|
| ARC container | v0x13 | v0x11 | **done** `arcpack.py` (repack of GU arcs gives identical entry contents) |
| rTexture `241f5deb` | v0xA5, ETC1/ETC1A4, 3DS 8x8 tiles | v0xA0, BC1/3/4/5 + RGBA8, Tegra block-linear | **done** `tex.py` |
| rModel `58a15856` | MOD 0xE6 | MOD 0xD4 | **prototype** `mod4u2gu.py` (all 4 em089 models convert + verify) |
| rMotionList `76820d81` | LMT 67 | LMT 67 | **copy as is** (same layout; GU codecs are a superset) |
| EMC cmd table `3aabba02` | ver 0x20120804, 23 groups | same version, 21 groups | drop 4U's 2 trailing (empty) groups; record semantics = code side |
| rMaterial `2749c8a8` | MRL 0x20, shader pkg MFX v52 | MRL 0x22, MFX v53 | **done** (template-based) `mrl_build.py` |
| camera list `39c52040` | LCM v4 | LCM v5 | small, to check |
| effects `6d5ae854` EFL / `4e397417` EAN / `148b6f89` MEF | 0x30111104 / 0x20100924 | 0x20120306 / 0x20120224 | different versions: re-author with GU effects |
| sound `67195a2e` MADP, `14b5c8e6` SNDB, `2618de3f` SREQ, `6e171a6e` MSS | 3DS ADPCM banks | GU uses other types (`79c47b59`, `15d782fb`, ...) | replace (decode MADP, re-encode) or borrow GU sounds |
| cloth/chain `535d969f` CTC | v0x16 | not in sampled GU arcs | to check |
| BGM | `/sound/bgm/battle/wav/bgm_em089*.mca` | - | separate |

The base RomFS also has a New 3DS texture copy `/snake/data/em089_.arc` (361 KB), not examined.

## ARC

Both: `'ARC\0'`, u16 version, u16 count, u32 0, count x 0x50 entries
`{char path[64], u32 type hash, u32 compressed size, u32 decompressed size | flags << 29, u32 offset}`, then zlib.
- GU (0x11): flags = 2 on every entry, every entry zlib, data starts at the header size rounded up to **0x8000**
  (zero padding; em001_00: 0xAB9C -> 0x10000), entries contiguous in table order.
  GU's zlib streams are not reproduced byte for byte by Python's zlib (any level); contents are what matter.
- 4U (0x13): flags 1 (5 on a few), data right after the header.
- `arcpack.py selftest`: em001_00 (549 entries) and em088_00 (743) repack -> identical contents, same data start.
  em089 (128 entries) unpack -> GU container -> identical contents.

## TEX

Header (both): `'TEX\0'`, tier0 = version:8 | unk:6 | unk:14 | type:4, tier1 = mips:6 | width:13 | height:13,
u8 faces, u8 format, u16 depth (layout as RevilLib `TEXx9D`).
- 4U (0xA5): then mips x u32 offsets (absolute), data. Formats (mhff wiki): 0x0B ETC1 (8 B/block),
  0x0C ETC1A4 (8 B 4-bit alpha + 8 B ETC1), 0x03 RGBA8 (ABGR), 0x04 RGB565, ... 3DS tiling: 8x8 tiles row by row,
  2x2 blocks in Z order inside; each ETC1 block a little-endian u64; alpha nibble index = x*4 + y.
  em089: body 1024x512 ETC1A4 6 mips, parts 256x256 ETC1A4, effects ETC1/ETC1A4 NOMIP.
- GU (0xA0): then u32 data size, mips x u32 offsets (relative), data. Header fields seen on all 7928 enemy
  textures: unk = 0 / 2, type 2, faces 1, depth 1. Formats: 0x13 BC1, 0x17 BC3 (BM), 0x19 BC4 (BM+A),
  0x1F BC5 (NM), 0x07 RGBA8 (cm textures). Data: Tegra X1 block linear per mip, 64 B x 8 row GOBs,
  block height = min(16, pow2(ceil(h_blocks/8))) GOBs, halved per mip while the mip height <= half a block.
- `tex.py selftest` over **all 137 GU enemy arcs: 7928 textures, deswizzle -> swizzle -> header rebuild
  byte-identical** (mip offsets/sizes match the computed layout, incl. non-square and 1-mip ones).
  Visual check: GU em001_00_BM mip 0 and mip 4, 4U em089_01_BM decode correctly.
- Encoder: BC1 (principal-axis endpoints), BC3/BC4/BC5 (min/max alpha); em089_01_BM 4U -> GU BC3 = 33.2 dB PSNR
  against the decoded ETC1A4 source, BC5 normal map 50.1 dB. Full mip chain (box filter).
- Orientation: texel order is the same in both games (no image flip); the model UVs are flipped instead (see MOD).

## MOD

Spec from RevilLib `src/mtf_mod` (GU = `LoadMODXDxLEx32<MODTraitsXD3PS4>`, 4U = `LoadMODXE5`) + checks on files:
- common: `'MOD\0'`, s16 version, u16 bones, meshes, materials, u32 vertices, indices, edges.
- 4U header 0x40 (+metadata, bones at 0x80): vbSize, textures 0, groups, **skins**, offsets bones/groups/
  materials/meshes/vb/ib. GU header 0x84: vbSize, textures 0, groups, offsets ..., dataEnd; metadata adds
  u32 envelope count; GU sets bit 31 of lightGroup.
- bones: 24 B records, local matrices, "inverse bind" matrices, 256 B remap: **same layout and, for Rathian,
  same values in both games** (only remap differs: GU reordered bone IDs; keep 4U's with 4U's LMT).
- **Positions are normalised in both games.** The per-bone matrix holds the dequantisation (scale = cube side,
  e.g. 1815.593 for Rathian = 2086.945 for em089; translation = AABB min - bone position). 4U stores f32 in
  [0,1]; GU stores u16 = p * 32767. The cube side can exceed the AABB (em001, em032); em007/em088 use
  the max extent. Boneless (rigid) models store float model-space positions in both games.
- 4U vertex formats used by em089: `0x01B36016` / `0xF606F017` (36 B: f32 pos, snorm8 N, f32 uv, b0 b1 w0 w1,
  snorm8 T, b2 b3 w2 w3, palette-local bones), `0xD6784014` (28 B, 2 weights, no tangent; the spear),
  `0x82917009` (24 B rigid; the severed tail). Skin palette per mesh = byte +0x29.
- GU uses MT "PC" formats, global bone indices, no palettes, plus extra edge/shadow meshes
  (`0x0CB68015`, `0xDB7DA014`, drawMode 32). Conversion targets: `0x14D40022` P3s_W1s_N4c_T4c_B4c_U2h_W2h
  (28 B; GU uses it on Rathian with drawMode 58560) and `0x5E7F2030` P3f_N4c_T4c_U2h_U2h for rigid models.
  Weights: unorm16 w0 + f16 w1, w2, w3 implied.
- **UV: v_GU = 1 - v_4U** (Rathian eye material: 4U v 0.90-0.99, GU v 0.005-0.05; matches the MH4U viewer's flip_v).
- Envelopes (GU, 144 B): one per bone a mesh uses: {u32 bone, sphere, AABB, OBB matrix + extents} in model space.
- `mod4u2gu.py` results (decode output, compare with the 4U source):

| model | meshes | envelopes | pos error | weights | uv | ib / bones / matrices / remap |
|---|---|---|---|---|---|---|
| em089 | 58 | 399 | 1.5e-5 (half a step) | 2e-4 | 1e-3 | identical |
| em089_tail (rigid) | 2 | 2 | 0 | - | 2e-4 | identical |
| em089_gekiryusou | 7 | 7 | 1.5e-5 | 0 | 2e-4 | identical |
| em001 (control) | 29 | 184 | 1.5e-5 | 1e-4 | 2e-4 | identical |

  4U em001's index buffer ends 2 bytes before its declared count: padded with the last index.
- Not done: edge/shadow meshes (the monster may cast no shadow / no outline until generated), GU's per-format
  vertex streams (we use one stream, allowed by the format), drawMode/flags only copied from GU's values.

## LMT

Both v67, 32-bit layout (RevilLib LMT66-68): animation 64 B {tracks, numTracks, numFrames, loopFrame,
end-frame additive pos/rot, flags, events, floats}; track 36 B {compression, type, boneType, boneID, weight,
bufferSize, buffer, reference[4], extremes}. 4U em001 and GU em001_00 lists: same slot counts, animations,
frame counts and track lists; GU re-encodes many rotation tracks with codecs 14/15 but still contains 4U-style
codec 6/7 tracks. em089_0..3 parse cleanly (114 animations, 0 bad pointers). So the 4U lists should load as is.

## EMC

Same magic/version. Header `{'EMC\0', u32 0x20120804, u32 groupCount, u32 0}` + groups {u32 count, u32 offset,
u32, u32}. 4U has 23 groups, GU 21; 4U's groups 21-22 are empty in em001 and em089, and the per-group
record sizes match (64, 72, 32, 192, 48 ...). Converting = drop the 2 empty groups, shift offsets by -0x20.
Record contents (action IDs, conditions) are monster logic: they only make sense with ported code.

## MRL

`mrl.py` reads both (4U v0x20 with LtShaderPackage.lfx MFX v52; GU v0x22 with AppShaderPackage.mfx v53,
extracted to dump/gu/). 4U materials: LUT shading (tAlbedoMap, tLutShininess/tLutFresnel, BS*/DS*/RS* states,
IABGBase); GU materials: feature records (FAlbedo, FBump, FSpecular..., tNormalMap/tAlbedoMap/tSpecularMap,
IASkinTBNLA*wt). Only 292 of 795 4U record names exist in GU. Plan: build em089's MRL from a GU monster MRL
template per blend state (BSSolid / BSAddAlpha / BSBlendAlpha), keyed by the 4U material name hashes
(crc32(name) ^ ~0 from the MOD), pointing at the converted textures.

## em089_00.arc build (tools/build_em089_arc.py, 2026-10-17)

Output: `module/romfs/nativeNX/arc/enemy/em089_00.arc` (840 entries, 17.8 MB, GU v0x11), `tools/em089_manifest.json`,
`module/em089_files.inc`. The Rathian test copy is kept in `module/romfs-rathian/` (identical to GU em001_00.arc).
The script verifies before writing: every new file ID's (path hash, type) and every kept donor ID is in the arc,
converted MODs/TEXs parse back, no duplicate entries.

Converted (internal paths `enemy\em089\em089_00\...`): models em089_00 / _tail / _gekiryusou + one MRL each, textures
_01.._05_BM (BC3) and _04_NM (BC5 from the 4U normal map's R, G), motion lists _0.._3 (4U LMT unchanged), and the
4U command table as `enemy\cmd_tbl\em089_00_cmdtbl_4u` (GU group count 21, offsets kept; not in the manifest unless
`--cmdtbl gog`).

Materials (`tools/mrl_build.py`): GU template entry + parameter block copied, name hash and texture indices
rewritten. Templates: `solid` em004_00 mat 0 (albedo + specular), `solid_nm` em001_00 mat 0 (+ normal),
`add` em037_00 mat 3 (BSAddAlpha). Matched by name hash (4U MRL order differs from MOD order): body, eye, wing,
gekiryusou, tail -> solid; the 5 liquid materials -> solid_nm; `XfB__m06_add` -> add. Not carried: 4U tExtendMap
(05_BM, packed but unused), CBRadialBlur, LUT shading. BM alpha is a specular mask in both games (GU Rathian BM
alpha mean 49), so the BM is also the tSpecularMap.

Placeholders, donor **Kushala em024_00** (elder dragon, 49 bones, 4 motion lists, closest size and skeleton IDs):
- renamed em024 -> em089 with new file IDs: field 3 model-parts XFS, 11 camera, 26 attackdata, 28 hitsize,
  30 bodydata, 31 cambodydata, 32 dtbase, 33 dttune, 34 dtbparts, 35 actiontune, 37 cmdtbl, 40-44 area/map,
  46-50 hagi.
- original paths + Kushala's own file IDs (they reference each other by path): 12 sound call, 13 sound bank,
  14-15 pts, 16-17 pel, 18-21 psl (Kushala's motion-synced effects: timings will not match Gogmazios' motions),
  25 shell arc, 45 option motion (Rathian's em001_00_option, as Kushala's manifest has it).
- the rest of Kushala's arc is packed unchanged (802 entries: effects, sounds, shell data, Kushala's textures),
  minus its body/tail MOD+MRL and motion lists.

File IDs: 0x10700..0x1071c (29): manifest files + extras 4U cmdtbl 0x1071b, gekiryusou model 0x1071c.

**Update (later 2026-10-17): fields 3, 26, 28, 30, 31, 32, 33 now hold Gogmazios' own converted 4U data; only
34 dtbparts (and 11, 35, 40-50) stay Kushala's. Details, checks and the HUD icon/name: notes/data.md.**

Mismatches against Gogmazios (item 4):
- Skeleton: Gogmazios 52 bone IDs, Kushala 49. Kushala bodydata uses 4 IDs Gogmazios lacks; remapped to the
  nearest bone in normalised bind position: 130 -> 200, 144 -> 143, 240 -> 0, 241 -> 0 (cambodydata: 130 -> 200).
  hitsize / attackdata / effects may also name bone IDs (formats not decoded) -> not remapped.
- Mesh groups: Gogmazios 36 (0, 2-9, 11-19, 22, 25-35, 100-105) vs Kushala 11 (0-8, 100, 101). The XFS
  (field 3, probably part visibility) and dtbparts / dttune (part HP, breaks) describe Kushala's parts; Gogmazios'
  own parts rows are in the 4U `emd` (em_data.arc, 38 rows, parts 2-35 and 101-105, conds 1/6/7/11): converting
  them needs the GU XFS / DTP formats decoded.
- Edge/shadow meshes NOT generated: GU edge meshes (0x0CB68015) are per-face duplicated vertices with face normals
  and an undecoded normal.w; producing them blind risks broken shadows, so the model ships without them.

### Fix 2026-10-17: model loaded but nothing drawn
- Cause: every converted mesh had drawMode **0xE4C0**. In GU that value only marks special proxy meshes (Rathian's
  6 hidden eye meshes, the second of each tail's two meshes, Kushala's break-state body pieces); drawn meshes use
  **0xEFFF** (all 3 compared models). 4U encodes the same split: 0xEDD7 / 0xECD3 drawn, 0xEEDA / 0xE6C8 proxies.
  `mod4u2gu.gu_drawmode()` now maps them: em089 body 48 drawn + 10 proxies (eye-material meshes in groups
  100-104, a spear piece), tail 1 + 1, spear 5 + 2.
- Also aligned with GU: mesh weight field 3 or 4 on 0x14D40022 (we wrote 1-4), 0 on rigid 0x5E7F2030 (we wrote 1).
- The MRL was NOT broken: `mrl.read()` had a wrong entry-size heuristic for v0x22 (took the next entry's block
  size word as an offset -> "esize 39"). Fixed: 60-byte entries, param block = (w13, w2), GU descriptor count =
  first constant-buffer offset / 12. `tools/mrl_check.py` compares each built material with its template: all 12
  materials identical except name hash, offsets and texture indices (in range).
- Material IA state is not tied to the vertex format: real GU meshes in 0x14D40022 use IASkinTBNLA2wt,
  IASkinTB2wt and IASwing2HighPrecision materials; 0x5E7F2030 tails use TBNLA2wt (Rathian) or TB2wt (Kushala).
- Field-3 XFS = parts visibility (`mPartsVisibleGroupList`, `mPartsVisibleInfo`: group IDs + visible flags per
  part state). Still Kushala's; it names groups 0-8, 100, 101.
- Diagnostic arc `module/romfs-kushala-model/...`: identical except fields 0/1 hold Kushala's original GU body/tail
  MOD + MRL under our paths (`build_em089_arc.py --kushala-model`).
- Entry order (coordinator's in-game finding): the game's arcs store TEX -> MRL -> MOD; a model fetches its MRL by
  path while loading, so anything referenced by path must come before its user. build_em089_arc.py keeps that.

### Fix 2026-10-17: spikes when animated (clean at rest)
- Cause: the first weight of 0x14D40022 ("W1s") is **SNORM16** (w0 = raw / 32767); mod4u2gu wrote it as UNORM16
  (raw = w * 65535), so the game read w0 = 0.5 as -1.0 and derived w3 = 1 - w0 - w1 - w2 = 2.0. The shader
  derives w3, so weights always sum to 1: at rest every bone has the same skin matrix and the mesh looks right,
  any bone motion pulls vertices out into spikes.
- Evidence on real GU vertices (em001/em024/em004/em071, all 0x14D40022 meshes): reading w0 as snorm16 gives an
  implied w3 that is never negative (min 0.000); reading it as unorm16 gives w3 >= 0.2 always and w3 == w0 on 92 %
  of vertices (the doubling artefact). Bone indices are global joint indices (max < bone count) and every bone a
  mesh uses (w > 0.01) is in that mesh's envelope list.
- Not the cause, checked: 4U skin palettes hold joint indices (max 51 of 52); LMT tracks address bone IDs (up to
  205), all present in our remap; GU Rathian keeps 4U's bone IDs and its LMT track IDs, it only reordered the joint
  array and its remap follows (remap[ID] lands on the same bind position in both games), so 4U MOD order + 4U remap
  + 4U LMT is consistent. Track 255 (root) is handled the same in both.
- Positions are written as s16 too (P3s = snorm16, values 0..32767).

### Fix 2026-10-17: model scale
- GU dtbase f32 @0x15 = per-monster model scale; it equals 4U `emd` (em_data.arc, type 0x0a0e48d4) f32 @0xC on
  40 of 41 monsters present in both games (the miss: Raging Brachydios matched to Brachydios' GU file). Values:
  Kushala/Teostra/Chameleos 0.8, Rathian 1.0, Akantor 1.5, Kirin 2.3, **Gogmazios 2.5**.
- Our dtbase = Kushala's with only bytes 0x15-0x18 replaced by Gogmazios' 2.5 (read from the 4U emd).
- Crown sizes / size records come from resident `em_size_scale_data` (mTrueSize, crown scales) by monster index;
  index 137 has no entry there (not touched).

## Sources

- RevilLib (MT Framework formats, MOD/TEX/LMT/ARC): https://github.com/PredatorCZ/RevilLib
- mhff wiki, MH4U rTexture/rModel/rMaterial/rArchive: https://github.com/svanheulen/mhff/wiki
- MH4U Monster Viewer (4U pipeline notes: flip_v, ETC1A4, LMT v67): https://github.com/ArmoredRaven17/mh4u-monster-viewer
- MHGU Blender importer (MHGU MOD): https://github.com/DemonDrugd/MHGU-blenderImporter
- MT Framework Mobile Blender script (3DS MOD): https://github.com/xZombieAlix/MT-Framework-Mobile---Blender-Model-Script
- Noesis 3DS TEX plugin: https://github.com/Zheneq/Noesis-Plugins/blob/master/fmt_mtframework_3ds_tex.py
- pyswizzle (Switch swizzle reference): https://github.com/Aclios/pyswizzle
- SoupTextures (MHGU TEX tool): https://gamebanana.com/tools/19801
- MHGU model import/export guide: https://gamebanana.com/tools/19384
