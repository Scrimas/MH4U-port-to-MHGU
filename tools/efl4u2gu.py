"""efl4u2gu.py : MH4U effect data -> MHGU: Gogmazios (em089) here, any monster through effect_set(spec).

  efl4u2gu.py build [OUTDIR]     convert the em089 effect set; write OUTDIR/<path>.<typehash> + OUTDIR/_report.txt
                                 (default OUTDIR = the scratch dir given by $EFX_OUT, else dump/converted/em089_efx)
  efl4u2gu.py check FILE.efl     structural check of a GU (or 4U) EFL
  efl4u2gu.py report             conversion report only (no files)
Library (tools/build_em089_arc.py): entries() -> [(path, type hash, bytes)] in arc load order, PEL_U, PSL[4];
other monsters: effect_set(spec, log) (monsters/tigerstripe_zamtrios/tools/build_em067_01_arc.py).

What is converted (all formats were compared on both games' code and on corpora, see notes/port-checklist.md
"## Effects (effects agent)"):
  EFL  rEffectList 0x30111104 -> 0x20120306. Same container in both games (header, 16-byte entries of 4 block
       words ((offset - 0x30) << 8 | type), n2 0x70-byte tail records); every block keeps its size and layout except
       unit type 9 (cParticleGeneratorFilter, 0xc0 -> 0xe0, re-laid out: 4U words 26/27 -> GU 36/37, colour 28-31 ->
       32-35, GU-only words 24-31 from GU's constant defaults). The file is re-serialised block by block, so a size
       change moves every later block (shared blocks stay shared). Resource paths are kept: every converted
       resource is packed under its 4U path (no GU arc uses the effect\\efl / effect\\base\\{em,cm,qe} 4U names).
       Unit +0x18 (unit_4u_to_gu, evidence at UNIT_INTENSITY): bits 12-15 (4U 'Intensity') cleared, GU-only bit 19
       set on unit types 0 / 1 / 2 (Capcom's rule). GU-only fields that stay 0: +0x18 bits 4-11 / 17, +0x14 bytes
       2 / 3, element header +8 bit 27.
  EAN  rEffectAnim 0x20100924 -> 0x20120224, layout identical; byte +0xf (GU flag, 1 in every GU file, stored as
       bit 24 of the frame count) left 0 = the 4U meaning.
  TEX  4U ETC1 / ETC1A4 NOMIP -> GU RGBA8 1 mip (what GU effect textures use), lossless after the ETC decode.
  MOD  effect models via mod4u2gu (rigid -> 0x5E7F2030); MRL from GU's effect material cm101_000 (BSBlendAlpha,
       DSZTestWrite, RSMeshCN) with the 4U BS/DS/RS states; GU's IA state is not tied to the vertex format.
  PEL  em089 effect definitions (rProofEffectList v15, the GU counterpart of 4U's MEF rMhMotionEffect): one record
       per 4U MEF record in list 1 (motion sequences) and list 2 (code posts, 0x6ff74(this, 2, id, req)). Mapped:
       EFL path (group 89/6/13 -> em089/qe006/qe013, file), id, joint, element mask (1 << k, k < 0 -> all), pos,
       rot (degrees), scale. Other bytes = the most common GU monster PEL u list-1 tail (PEL_TAIL), with GU's
       colour override switched off (PEL_COLOUR_OFF), except on the records whose 4U effect colour is multiplied
       in code (pel_colour: EFL +0x2c block -> 4U area colour or 0xc48378 code colour) = GU override mode 2.
       NOT mapped: MEF b0, slot mode, flag bits other than 0x200, repeat interval (4U cMhMotionEffect behaviour;
       in GU the PSL run lengths carry the active time).
  PSL  rProofEffectMotSequenceList v2 x 4 (one per motion list), from the 4U LMT animation event group 2 (MEF id
       remap[32] + run-length {bits, frames} events): same encoding in GU; slot kind 4 = PEL u list 1.
"""
import os, struct, sys, zlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
sys.path.insert(0, paths.GU_PY)
import arcpack, tex, mod as modlib, mod4u2gu, mrl, mrl_build, ctr

ROM_4U = os.path.join(ROOT, 'dump/base/Monster Hunter 4 Ultimate (EUR) Decrypted.3ds')
SRC_EM089 = os.path.join(ROOT, 'dump/romfs/data/em089.arc')
CORE_ARCS = ['/eng/data/core_quest.arc', '/eng/data/core_common.arc']
STAGE_UNPACKED = ['m19a03', 'm19']   # Battlequarters arena effects (effect\efl\st\m19a03), lowest priority
GU_ROMFS = paths.GU_ROMFS

T = dict(EFL=0x6D5AE854, EAN=0x4E397417, TEX=0x241F5DEB, MOD=0x58A15856, MRL=0x2749C8A8, MEF=0x148B6F89,
         LMT=0x76820D81, PEL=0x5A525C16, PSL=0x254309C9)
GU_EFL_VER, GU_EAN_VER = 0x20120306, 0x20120224
PEL_U = 'effect\\pel\\em\\em089_00u'
PSL = ['effect\\psl\\enemy\\em089\\em089_00\\mot\\em089_00_%d' % i for i in range(4)]
MEF_PATH = 'effect\\mef\\em\\em089_0'
LMT_PATH = 'enemy\\em089\\mot\\em089_%d'
# MEF group -> EFL family (C: 4U 0x390c70 resolves (list kind, group, file); em089 uses 89 / qe 6, 13)
GROUP_EFL = {89: 'effect\\efl\\em\\em089\\em089_%03d', 6: 'effect\\efl\\qe\\qe006\\qe006_%03d',
             13: 'effect\\efl\\qe\\qe013\\qe013_%03d'}
# GU PEL record bytes 0x34..0xa0, element mask (0x48..0x4b) overwritten per record. 2026-10-19: the most common
# exact tail of the GU MONSTER PEL u list-1 records (177 of 2648 over the em0NN_00 arcs, top for joint-attached and
# for joint -1 records alike; it is also the tail of Capcom's converted 4U footsteps, e.g. GU em071 / em072 ids 12 /
# 13 on joints 63 / 73 = 4U MEF flags 0x2a6). The previous tail (84 of 2648, from a corpus with non-monster PELs)
# differs at +0x36 / +0x38 / +0x3a / +0x52 / +0x53 / +0x5c / +0x64 / +0x70 / +0x73 / +0x86; test 4 showed a puddle
# glued under the monster (em089 footsteps 42 / 43 fire in nearly every idle / walk motion).
PEL_TAIL = bytes.fromhex(
    '010001040100000003000600000000000000000000000000ffffffff00000101000000000000614401000000000000ff'
    '070000000000003f0000000001030001000000ff0000803f0000803f000000000000010000000000ffffffffffffffff'
    'ffffffffffffffff0000803f')
assert len(PEL_TAIL) == 160 - 0x34
# GU PEL colour override (C: loader 0x323264 reads the 160-B struct to record object +0x20; the effect keeps it at
# effect +0x90). 0x327cb8 / 0x32b4f4 recolour the effect's units only when +0x70 == 1, with the colour from 0x3214f0:
# +0x56 -> table A[u16 +0x64], else +0x73 -> global table B[u16 +0x64] entry u16 +0x66, else RGBA +0x60; mode +0x71
# (3 = RGB lerp to that colour, alpha kept), factor f32 +0x68 (0.5). The monster-majority tail above has it ON
# (+0x70 1, +0x73 1, +0x64 7: table 7, = 1131 of 1432 GU cm202 ground-dust list-1 records) -> every em089 effect was
# lerped halfway to that table colour (test 5: roar, puddle explosions, steps, tail break came out white). 4U has no
# such override (MEF records carry no colour; over 60 matched 4U/GU records no MEF flag bit predicts +0x70), so it
# is OFF for every record = the previous tail's bytes. 2026-10-19: these bytes only; the rest of PEL_TAIL stays.
# (Test 6: the effects stay white with the whole test-4 tail too, and test 4 already had white tail smoke: the tail
# is not what makes them white.)
PEL_COLOUR_OFF = ((0x70, 0), (0x73, 0), (0x64, 0), (0x65, 0))
# 4U effect colour multiply (2026-10-19, white-effects helper). The white smoke / dust units are light grey in the
# EFL (em089_031 steps ff8b8b8b / ffa2a2a2 / ffcccccc, model ff2f2f2f; em089_032 roar dust a5 / a4 / 46; qe013_002
# tail smoke ff / 9b / af / ad); 4U darkens them at run time:
#  - EFL header +0x2c = offset (from +0x30) of a 16-B block (C: 4U loader 0x23d6ac res+0x90 = header +0x2c, res+0x68 =
#    data). The effect's slot 26 0xafa89c: block word 0 bit 4 -> effect +0x228 |= 1 (colour on), and block +0xc
#    byte 2 == 0 -> |= 2 (area colour). em089_021 / 023 / 031 / 032, qe006_000..041: (0x10, 1, 0, 0) = area colour;
#    em089_050, qe013_002: (0x10, 1, 0, 0x10000) = code colour.
#  - Unit colour hook = slot 60 0xc474c0 (only this effect class overrides it; base 0xafc570 = bx lr): unit colour
#    mode (generator +0x3c bits 24-27 = unit +0x18 bits 0-3, setup 0x39f984; 5 on the dust units of em089_022 / 024 /
#    030 / 051, qe016_003: see UNIT_AREA_MODE) 0 + effect
#    +0x228 bit 0 -> bit 1 ? area colour 0xc0813c(sEffect, effect +0x239)
#    : effect +0x24c == 1 ? code colour +0x25c (setter 0xc48378) : unchanged; mode 5 -> area colour. Combine 0xc48274
#    = per-channel unit * colour / 255 (RGBA) = a MULTIPLY (alpha kept for alpha 255).
#  - effect +0x239 = 0xc09908(owner) ground state (0 normal, 1 / 5 water, 2 lava, 3 poison, 4 vines) -> sEffect
#    +0x1df0 area_color_soil (property registration 0xc08bd4), +0x1df4 water, +0x1e04 yogan, +0x1dfc poison, +0x1df8
#    tuta: set by the stage MhEffect scheduler; m19a03d-col / -f / -f02 / -f03 all give soil (0.5373, 0.4588,
#    0.3569, 1) = (137, 117, 91, 255).
#  - Code colours on qe013_002 (em089 code, 0xc088d8 group 1 file 138): tail break 0x8c6918 (37, 46, 49, 255) =
#    PEL 3300; spear break 0x8c89c4 (42, 29, 25, 255) and 0x8a2818 (120, 85, 80 / 143, 76, 58) are not ported.
# GU: 0x327cb8 (uMHProofEffect slot 52, run after the unit build 0x9bda64) walks the effect's units (+0x1f0, next
# +0xc); for cParticleGenerator units it combines the source colours (+0x180 / +0x184) with the 0x3214f0 colour
# (+0x56 / +0x73 off -> RGBA +0x60, byte order = the EFL colour word's) by mode +0x71: 0 = RGBA lerp (+0x68),
# 1 = 0x9b67e4 (replace, or lerp by the EFL block's u16 +0xc when its bit 4 is set: a 4U block gives factor 0),
# 2 = per-channel a * b >> 8 (254 -> 255) = 4U's multiply, 3 = RGB lerp (alpha kept). -> mode 2 with the 4U colour.
# The area colour is fixed to the Battlequarters soil (em089's only stage; 4U's other ground states not mapped).
PEL_COLOUR_ON, PEL_COLOUR_MODE, PEL_COLOUR_RGBA = 0x70, 0x71, 0x60
PEL_COLOUR_MUL = 2
M19A03_AREA_SOIL = bytes((137, 117, 91, 255))
CODE_COLOUR = {3300: bytes((37, 46, 49, 255))}     # record id -> 4U 0xc48378 colour of its poster
# The previous tail (until 2026-10-19), kept for effects that must move with a unit. Transform mode (C: 0x32a548, the
# record merged into the request at effect +0x80): +0x36 4 -> 0, 1 -> 2, 0 -> (+0x38 == 1 ? 1 : 0), 2 / 3 -> 3 / 4;
# +0x3a = end mode (0x329dbc). PEL_TAIL (+0x36 1, mode 2) stays where it was posted: fixes the owner-posted step
# puddle (test 4: glued under him with mode 0) but the blob drips 3000 / 3001 posted on their shell stopped falling
# (test 5). G (from those two tests, the mode consumer is not traced): mode 0 follows the target / joint.
PEL_TAIL_PREV = bytes.fromhex(
    '010000040000010003000600000000000000000000000000ffffffff00000000000000000000614400000000000000ff'
    '000000000000003f0000000000030000000000ff0000803f0000803f000000000000000000000000ffffffffffffffff'
    'ffffffffffffffff0000803f')
assert len(PEL_TAIL_PREV) == len(PEL_TAIL)


def pel_follows(rid):
    """records posted on a moving unit (3000 / 3001 blob, 5100 + sub uShell051 ground shell: em089_efx_post_on):
    previous tail (all-previous bytes = their test-4 state, when they moved correctly; its colour bytes are already
    off). Not the 4200 / 4300 + sub uShell016 beams: with the previous tail the laser was gone (test 4) and the tar beam
    not drawn (test 6); with PEL_TAIL it shot out of the mouth (test 5)."""
    return rid in (3000, 3001) or 5100 <= rid < 5200
# GU Filter (unit type 9) words 24..31: constant in every GU sample (cm202_050, em013/027/033 ...)
# (2026-10-19, filter helper, C + S) Same in all 29 GU type-9 units of the romfs (eflcorp.pkl); the 7 Capcom
# conversions (4U em023_010 / 016, em028_016, em116_011, d0502_004 -> GU em068_00_009 / 011, em071 / em072, em038_00_008,
# em027_00_010) equal filter_4u_to_gu(4U unit) byte for byte. Class in both games = a screen-space radial blur
# request, no geometry: 4U draw 0x415bc0 -> 0x4156c0 -> 0xaf3610 -> 0xaf3450 (creates uMultiBlurFilter, DTI name at
# 0xd4a570, line 0x64608c); GU draw (vtable 0x17903fc slot 20) 0xa855f4 switches on unit +0x40 byte 0 (0 here) ->
# 0xa85684 -> 0xb92024 -> 0xb92098 on sEffect +0x278, whose type 0 (set at 0xb8fd90) -> uMultiBlurFilter (0xc63ca4).
# GU w24 byte 1 = samples, byte 2 = centre mode (0 / 3 screen centre = w36 / 37 + w28..31, else the particle's world
# position = 4U w24 byte 2 == 1, 0x4157bc), w26 / w27 -> request / per-particle params; colour = w32..35 (particle init
# 0xcafed4). 4U hard-codes 0.045 / 3 / alpha * 0.5 in the draw (0x415aa4, 0x4158f4, 0x415b0c) instead.
FILTER_GU_W24_31 = (0x04041000, 0, 0x3F800000, 0xBDCCCCCD, 0x3F000000, 0x3F800000, 0x3F000000, 0x3F800000)
# GU effect material template (BSBlendAlpha effect, no animation block): Kushala's arc cm101_000 mat 0
mrl_build.TEMPLATES.setdefault('efx_blend', ('/nativeNX/arc/enemy/em024_00.arc', 'effect\\base\\cm101_000', 0))


def phash(p):
    return zlib.crc32(p.encode('ascii')) ^ 0xFFFFFFFF

# ------------------------------------------------------------------ sources


_SRC = {}


def sources(arc=SRC_EM089, stage_unpacked=STAGE_UNPACKED):
    """(path, type) -> bytes over a 4U monster arc (default em089.arc), the 4U core arcs (common effects) and the
    unpacked 4U stage arcs given (lowest priority). Cached per argument set."""
    key = (arc, tuple(stage_unpacked))
    if key not in _SRC:
        S = _SRC[key] = {}
        arcs = [open(arc, 'rb').read()]
        n, _ = ctr.main_ncch(ROM_4U)
        fs = n.romfs_reader()
        arcs += [fs.read(a) for a in CORE_ARCS]
        for a in arcs:
            for p, t, d in arcpack.read(a)[1]:
                S.setdefault((p, t), d)
        for st in stage_unpacked:             # 4U stage arcs unpacked as <path>.<type hash> (arcpack unpack)
            base = os.path.join(ROOT, 'dump', 'm19_unpacked', st)
            for dp, _, fs in os.walk(base):
                for f in fs:
                    stem, _, ext = f.rpartition('.')
                    if len(ext) != 8 or any(c not in '0123456789abcdefABCDEF' for c in ext):
                        continue                 # unpack listings / notes, not arc entries
                    rel =os.path.relpath(os.path.join(dp, stem), base).replace('/', '\\')
                    S.setdefault((rel, int(ext, 16)), open(os.path.join(dp, f), 'rb').read())
    return _SRC[key]

# ------------------------------------------------------------------ EFL


def efl_parse(d):
    magic, ver, size, fps, n, n2 = struct.unpack_from('<4sIIfHH', d, 0)
    assert magic == b'EFL\0', magic
    ents = [list(struct.unpack_from('<4I', d, 0x30 + 16 * i)) for i in range(n)]
    tail_at = 0x30 + 16 * n
    tail = list(struct.unpack_from('<%dI' % n2, d, tail_at))
    starts = set()
    kind = {}
    for e in ents:
        for k, w in enumerate(e):
            if w >> 8:
                o = (w >> 8) + 0x30
                starts.add(o); kind.setdefault(o, (k, w & 0xFF))
    for t in tail:
        if t:
            starts.add(t + 0x30); kind.setdefault(t + 0x30, ('tail', 0))
    end = size + 0x30
    assert end == len(d), (hex(end), hex(len(d)))
    st = sorted(starts)
    first = st[0]
    assert first >= tail_at + 4 * n2, (hex(first), hex(tail_at))
    blocks = [(o, (st[i + 1] if i + 1 < len(st) else end) - o, kind.get(o)) for i, o in enumerate(st)]
    return dict(ver=ver, n=n, n2=n2, ents=ents, tail=tail, first=first, blocks=blocks)


def filter_4u_to_gu(b):
    """unit type 9 (Filter): 4U 0xc0 -> GU 0xe0 (word map from 4U/GU sample comparison, see module doc)."""
    w = list(struct.unpack('<48I', b[:0xc0]))
    assert w[24] == 0x10000, 'unexpected 4U filter word 24 %#x' % w[24]
    g = w[:24] + list(FILTER_GU_W24_31) + w[28:32] + w[26:28] + [0] * 18
    assert len(g) == 56
    return struct.pack('<56I', *g)


# Unit word +0x18 (2026-10-19, helper2; corpora = every EFL of the 4U ROM (13525 units) and of the GU romfs outside
# quest / sound arcs (13754 units); Capcom conversions = the 31 GU files with a 4U original of the same unit layout at
# >= 97 % unit-byte identity (4U em027 -> GU em070, em077 -> em013, qe008 -> cm200 ...), 59 units):
#  bits 12-15 = 4U 'Intensity' (C: 4U property list of the particle draw state (0x2547e0: 'Blend state' getter
#    0xcd8b7c = bits 5-15, 'Intensity' 0xcd8b10 = bits 26-29); 0x2e8864 copies unit +0x18 bits 12-15 to state bits
#    26-29, the draw 0x35c440 uses it as the index of one of 9 combiner set-ups (3DS fixed function)). 4U 0 / 1 / 2
#    (4079 / 8152 / 1294). GU has no such field: set in 0 of 13754 GU units, dropped in 21 / 21 converted units;
#    no GU effect read of these bits was found (GU builds its state from unit +0 byte 3 and +0x50 bits 8/9/12 at
#    0xa7c210). Not a darkening blend: em089's black smoke units have Intensity 0, the orange fire ones 1 / 2; the
#    blend index (unit +0 byte 3) is kept by Capcom (57 / 58 converted units identical). -> cleared.
#    (2026-10-19, blend-6 helper, C: the combiner index is base + Intensity (r9 = state bits 26-29, 0x35bf68) and the
#    set-up table 0xe352a0 = scale 0 / 1 / 2 per index, written to the combiner's scale field (0x35bb48) = PICA RGB
#    scale 1x / 2x / 4x (I: PICA encoding). So GU draws Intensity 1 / 2 units at 1/2 / 1/4 of 4U's brightness.)
#  Blend index (unit +0 byte 3) needs no mapping (C): 4U draw 0x35c4e8 / model helper 0x64284c -> shader handle table
#    0xe39f34 (copied by 0x229f68), GU particle draw 0xb95038 / model helper 0xb007fc -> table 0x16a23f8 (copied by
#    0xc7a3cc): indices 0..15 name the same blend states (0 BSBlendAddAlpha, 1 BSBlendBlendAlpha, 5 BSBlendRevSubAlpha,
#    6 BSBlendRevSubBlendAlpha ...; GU inserts BSBlendNoBlend at 16), and the records of those names are byte-identical
#    in 4U LtShaderPackage.lfx and GU AppShaderPackage.mfx (6 = src*a reverse-subtracted from dst*(1-a): darkens only).
#  bit 19 (GU only): set on every GU Billboard / Polyline / Polygon (types 0 / 1 / 2) whose blend index is not 14 and
#    whose unit +4 bit 14 is clear (2801 / 2801; the 259 without it are exactly those two GU-only cases, which 4U
#    never uses), added by Capcom to 12 / 12 converted type 0 / 1 units; never set in 4U. Meaning not traced (G).
#  Unchanged: +0x50 byte 2 (index * 32 into a per-element table: 4U 0x402e64 = GU 0xa7c1ac, same code; Capcom's
#    zeros come with its GU EAN / texture swaps), GU-only bits 4-11 / 17 (artist values), type 5 bit 16 (kept 8 / 8).
#    (2026-10-19, tar-white helper, C: the table is the unit's EAN (path at unit +0x130), a UV ATLAS, not a colour /
#    alpha track: GU rEffectAnim load 0xce461c copies file +0x10.. to +0x6c (count | (byte +0xf != 0) << 24 -> +0x68);
#    entry = {data off, frame count (hi 16 = loop flags), pivot x / y (= unit +0x60 / +0x64 in 8575 / 8965 4U and
#    2917 / 3060 GU units), x, y, cols | rows << 16, cell w | h << 16}, frame = 24 B {x | y << 16, w | h << 16, u0 v0
#    u1 v1}; GU's frame step (e.g. 0xa7c9f4) reads entry +0 / frame +0..7. Same layout in both games' EANs (GU's
#    multi-entry cm099_000 / em019_00_004 decode alike; Capcom kept index 1 / 2 into em019_00_004 for em107 -> em019).
#    No runtime reader of the +0x68 bit 24 found (only the saver 0xce47b8 writes it back) -> EAN byte +0xf kept 0.)
UNIT_INTENSITY = 0xF000
UNIT_GU_B19 = 1 << 19
# 4U unit colour mode 5 (unit +0x18 bits 0-3 -> generator +0x3c bits 24-27, setup 0x39f984): the colour hook 0xc474c0
# multiplies the AREA colour (0xc0813c) into the unit colours whatever the EFL header block says (0xc474f0 cmp 5 ->
# 0xc478dc(.., 1) -> 0xc48274 = per channel trunc(a * (1/255) * (b * (1/255)) * 255), float32, generator +0x168 / +0x16c
# from the colours at +0x178, +0x170 / +0x174 from +0x17c only when non-null); modes 1-4 / 6+ keep them (0xc476c4 ->
# return), mode 0 follows the header block (pel_colour). 404 of 519 4U mode-5 units are pure grey (dust tinted at run
# time); GU authors its 29 mode-5 units already coloured (1 grey) and no GU reader tints them (test 11: em089_022 /
# 024 / 030 tail-sweep / slam dust white). -> baked into words 18 / 19 with the Battlequarters soil (the only area),
# when the file has no header block; with an area block the PEL multiply already covers every unit.
UNIT_COLOUR_MODE, UNIT_AREA_MODE = 0xF, 5


def unit_curve_props(blk):
    """properties of the curve tables appended to a unit (offset = unit +0x40 hi16; header count | 2 << 8 | prop << 24,
    0 = colour, 1 = alpha, 0x40 = scale)."""
    a = struct.unpack_from('<I', blk, 0x40)[0] >> 16
    props = []
    while a and a + 4 <= len(blk):
        h = struct.unpack_from('<I', blk, a)[0]
        if not h & 0xFF or (h >> 8) & 0xFF != 2:
            break
        props.append(h >> 24)
        a += 4 + 12 * (h & 0xFF)
    return props


def area_multiply(word, rgba):
    """4U 0xc48274 on one colour word (bytes R, G, B, A) and an RGBA colour, float32 as the 3DS VFP."""
    import numpy as np
    a = np.frombuffer(struct.pack('<I', word), np.uint8).astype(np.float32)
    b = np.frombuffer(bytes(rgba), np.uint8).astype(np.float32)
    k = np.float32(1.0 / 255.0)
    c = (a * k) * (b * k) * np.float32(255.0)
    return struct.unpack('<I', c.astype(np.uint32).astype(np.uint8).tobytes())[0]


def unit_4u_to_gu(blk, utype, area=None):
    """area: the colour baked into mode-5 units (None = left to the PEL multiply, 'code' = code-coloured file)."""
    w = struct.unpack_from('<I', blk, 0x18)[0] & ~UNIT_INTENSITY
    if utype in (0, 1, 2):
        w |= UNIT_GU_B19
    out = bytearray(blk)
    struct.pack_into('<I', out, 0x18, w)
    if utype != 9 and w & UNIT_COLOUR_MODE == UNIT_AREA_MODE and area:
        assert area != 'code', 'mode-5 unit in a code-coloured EFL (area colour per unit: not mapped)'
        for o in (0x48, 0x4c):
            struct.pack_into('<I', out, o, area_multiply(struct.unpack_from('<I', blk, o)[0], area))
        # colour curve (prop 0): keys {u32 frame, colour, colour}, the pair layout of words 18 / 19. 4U multiplies the
        # current curve colour (+0x17c path) each frame; per channel that commutes with the key interpolation, so
        # every key colour gets it (S; first seen on em092_010, 2026-10-20). Alpha curves (prop 1) need nothing: the
        # area colours' alpha is 255.
        a = struct.unpack_from('<I', blk, 0x40)[0] >> 16
        while a and a + 4 <= len(blk):
            h = struct.unpack_from('<I', blk, a)[0]
            if not h & 0xFF or (h >> 8) & 0xFF != 2:
                break
            if h >> 24 == 0:
                for i in range(h & 0xFF):
                    for o in (a + 8 + 12 * i, a + 12 + 12 * i):
                        struct.pack_into('<I', out, o, area_multiply(struct.unpack_from('<I', blk, o)[0], area))
            a += 4 + 12 * (h & 0xFF)
    return bytes(out)


def convert_efl(d, log=None, soil=M19A03_AREA_SOIL):
    """soil = RGBA of the area colour 4U multiplies in (the stage's area_color_soil; default the Battlequarters')"""
    p = efl_parse(d)
    out_blocks, newoff = [], {}
    pos = p['first']
    b = efl_colour_block(d)
    area = (soil if not b or not b[0] & 0x10 else None if not (b[3] >> 16) & 0xFF else 'code')
    for o, size, k in p['blocks']:
        blk = d[o:o + size]
        if k and k[0] == 1:
            blk = unit_4u_to_gu(blk, k[1], area)
        if k == (1, 9):
            assert size == 0xC0, size
            blk = filter_4u_to_gu(blk)
            if log is not None: log.append('unit type 9 (Filter) at %#x re-laid out 0xc0 -> 0xe0' % o)
        newoff[o] = pos
        out_blocks.append(blk)
        pos += len(blk)
    hdr = bytearray(d[:p['first']])
    struct.pack_into('<I', hdr, 4, GU_EFL_VER)
    struct.pack_into('<I', hdr, 8, pos - 0x30)
    for i, e in enumerate(p['ents']):
        for k, w in enumerate(e):
            if w >> 8:
                o = (w >> 8) + 0x30
                struct.pack_into('<I', hdr, 0x30 + 16 * i + 4 * k, ((newoff[o] - 0x30) << 8) | (w & 0xFF))
    tail_at = 0x30 + 16 * p['n']
    for i, t in enumerate(p['tail']):
        if t:
            struct.pack_into('<I', hdr, tail_at + 4 * i, newoff[t + 0x30] - 0x30)
    out = bytes(hdr) + b''.join(out_blocks)
    assert len(out) == pos
    return out


def check_efl(d):
    """structure check: re-parse, every block word inside the file, unit sizes plausible."""
    p = efl_parse(d)
    sizes = {o: (s, k) for o, s, k in p['blocks']}
    bad = []
    for i, e in enumerate(p['ents']):
        for k, w in enumerate(e):
            if w >> 8 and (w >> 8) + 0x30 not in sizes:
                bad.append((i, k, hex(w)))
    if p['ver'] == GU_EFL_VER:
        for o, (s, k) in sizes.items():
            if k == (1, 9) and s < 0xE0: bad.append(('filter size', hex(o), hex(s)))
    return p, bad


def efl_paths(d):
    """resource paths named inside the blocks (NUL-terminated 'effect\\...' strings)."""
    out, i = [], d.find(b'effect\\')
    while i != -1:
        e = d.index(b'\0', i)
        out.append(d[i:e].decode('ascii'))
        i = d.find(b'effect\\', e)
    return out

# ------------------------------------------------------------------ EAN / TEX / MOD+MRL


def convert_ean(d):
    assert d[:4] == b'EAN\0' and struct.unpack_from('<I', d, 4)[0] == 0x20100924
    return d[:4] + struct.pack('<I', GU_EAN_VER) + d[8:]


def convert_tex(d):
    return tex.encode_gu(tex.decode(d), 'rgba8', mips=1)


_ROM = None


def gu_rom():
    global _ROM
    if _ROM is None:
        from romfs import RomFS
        _ROM = RomFS(GU_ROMFS)
    return _ROM


EFX_4U = {0x82917009: 24, 0x59DC400B: 28}   # 4U rigid effect formats: f32 pos, snorm8 N, f32 uv [, u8 RGBA]
EFX_GU, EFX_GU_STRIDE = 0x207D603B, 24      # GU effect format (S: 12k GU effect meshes): f32 pos, 10:10:10:2 N,
                                            # f16 uv, u8 RGBA (sample normals decode to unit length, e.g. (0,0,-1))


def convert_effect_mod(d):
    """boneless 4U effect MOD (0xE6) -> GU MOD (0xD4), every mesh in GU's effect vertex format 0x207D603B
    (4U vertex colour kept, (0, 0, 0, 255) for the colourless 0x82917009 meshes; uv v -> 1 - v as mod4u2gu)."""
    import numpy as np
    m = modlib.parse(d)
    assert m['version'] == 0xE6 and m['bones'] == 0, 'effect models are boneless'
    ib = bytearray(m['ib'])
    if len(ib) < 2 * m['indices']:
        ib += ib[-2:] * ((2 * m['indices'] - len(ib)) // 2)
    vb = bytearray(); meshes = []; envs = []; ib_out = bytearray()
    for x in m['mesh_list']:
        st = EFX_4U.get(x['fmt'])
        assert st == x['stride'], '4U effect vertex format %#x stride %d' % (x['fmt'], x['stride'])
        base = m['offsets']['vb'] + x['streamOff'] + x['vertexStart'] * st
        v = np.frombuffer(d[base:base + x['numVertices'] * st], np.uint8).reshape(-1, st)
        n = len(v)
        pos = np.frombuffer(v[:, 0:12].tobytes(), '<f4').reshape(-1, 3)
        nrm = v[:, 12:15].view(np.int8).astype(np.float64) / 127.0
        uv = np.frombuffer(v[:, 16:24].tobytes(), '<f4').reshape(-1, 2)
        # colourless 4U mesh -> RGB 0, alpha 255 = Capcom's own conversion (4U ef_em077 group 3, 88 vertices,
        # 0x82917009 -> GU em013_00_000 group 3, 88 vertices, constant (0, 0, 0, 255)); no GU effect mesh has a
        # constant white colour (0 of 274 in 60 enemy arcs, 22 constant (0, 0, 0, 255)). The GU effect material
        # (FDiffuseVertexColorMD) doubles the vertex colour: the old white fill drew these meshes at 2x = saturated
        # white (test 10: ef_em089 heap disc em089_015 u1, explosion smoke)
        col = v[:, 24:28] if st == 28 else np.tile(np.array([0, 0, 0, 255], np.uint8), (n, 1))
        q = np.clip(np.round((nrm + 1.0) * 0.5 * 1023), 0, 1023).astype(np.uint32)
        nw = q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20) | (3 << 30)
        out = np.zeros((n, EFX_GU_STRIDE), np.uint8)
        out[:, 0:12] = pos.astype('<f4').view(np.uint8).reshape(n, 12)
        out[:, 12:16] = nw.astype('<u4').view(np.uint8).reshape(n, 4)
        out[:, 16:20] = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1).astype('<f2').view(np.uint8).reshape(n, 4)
        out[:, 20:24] = col
        new_start = len(vb) // EFX_GU_STRIDE
        vb += out.tobytes()
        # indices are absolute vertex numbers: rebase onto the new vertex start (0xFFFF = strip restart). GU index
        # buffer: every mesh's run followed by one 0xFFFF (all GU monster / stage / effect models: gap 1, value
        # 0xffff; GU's draw reads it, without it a triangle joins the next mesh's first vertex) -> copied out per mesh.
        run = []
        for k in range(x['indexStart'], x['indexStart'] + x['numIndices']):
            i = struct.unpack_from('<H', ib, 2 * k)[0]
            if i != 0xFFFF:
                i = i - x['vertexStart'] + new_start
                assert 0 <= i < 0xFFFF, i
            run.append(i)
        istart = len(ib_out) // 2
        ib_out += struct.pack('<%dH' % len(run), *run) + b'\xff\xff'
        e = mod4u2gu.envelopes_for(pos.astype(np.float64), None, None)
        envs += e
        d1 = (1 | (x['shape'] << 1) | (x['sort'] << 2) | (x['alpha'] << 8) | (EFX_GU_STRIDE << 16) |
              (x['prim'] << 24) | (x['binflip'] << 30))
        d0 = x['group'] | (x['material'] << 12) | (x['lod'] << 24)
        meshes.append(struct.pack('<HHIIIIIIIIBBHHHI', mod4u2gu.gu_drawmode(x['drawMode']), n, d0, d1, new_start, 0,
                                  EFX_GU, istart, x['numIndices'], 0, 0, len(e), x['meshIndex'],
                                  new_start, new_start + n - 1, 0))
    ib = bytes(ib_out)
    groups = d[m['offsets']['groups']:m['offsets']['groups'] + 32 * m['groups']]
    mo = m['offsets']['materials']
    mats = d[mo:mo + 128 * m['materials']]
    o_g = 0x84
    o_m = o_g + len(groups)
    o_me = o_m + len(mats)
    o_env = o_me + 48 * len(meshes)
    o_vb = o_env + 144 * len(envs)
    o_ib = o_vb + len(vb)
    end = o_ib + len(ib)
    hdr = struct.pack('<4shHHHIII', b'MOD\0', 0xD4, 0, len(meshes), m['materials'], len(vb) // EFX_GU_STRIDE,
                      len(ib) // 2, m['edges'])
    hdr += struct.pack('<10I', len(vb), 0, m['groups'], 0, o_g, o_m, o_me, o_vb, o_ib, end)
    hdr += struct.pack('<4f8f', *m['sphere'], *m['aabb'])
    mid, low, light, bj = m['metadata']
    hdr += struct.pack('<3IB3xI', mid, low, light | 0x80000000, bj, len(envs))
    assert len(hdr) == 0x84
    return hdr + groups + mats + b''.join(meshes) + b''.join(envs) + bytes(vb) + ib + b'\0' * 4


def convert_model(path, mod4, mrl4):
    """effect MOD + MRL -> GU. Materials: GU effect template, 4U blend/depth/raster states, 4U textures."""
    gmod = convert_effect_mod(mod4)
    r4 = mrl.read(mrl4)
    # 4U texture table: (type, path), type 0 = reserved slot (LUT samplers); keep the real textures, renumber
    tex_paths, newidx = [], {}
    for i, (ty, p) in enumerate(r4['textures']):
        if ty == T['TEX']:
            tex_paths.append(p); newidx[i + 1] = len(tex_paths)
    by_hash = {mm['name']: mm for mm in r4['mats']}
    mats = []
    for name in modlib.parse(gmod)['material_names']:
        mm = by_hash.get(mrl_build.name_hash(name))
        assert mm, '%s: no 4U material for %s' % (path, name)
        alb = [v for n, t, v in mm['params'] if n == 'tAlbedoMap']
        states = [s for s in mm['states'] if s and s[:2] in ('BS', 'DS', 'RS')]
        mats.append((name, 'efx_blend', {'tAlbedoMap': newidx.get(alb[0], 1) if alb else 1, 'tSpecularMap': 0},
                     states))
    gmrl = mrl_build.build(gu_rom(), mats, tex_paths)
    return gmod, gmrl, tex_paths

# ------------------------------------------------------------------ MEF -> PEL, LMT events -> PSL


def mef_records(d):
    assert d[:4] == b'MEF\0'
    n = struct.unpack_from('<I', d, 8)[0]
    out = []
    for i in range(n):
        r = d[12 + 72 * i:12 + 72 * i + 72]
        b0, slot, b2, lkind = r[0], r[1], r[2], r[3]
        rid, grp, fil, joint = struct.unpack_from('<HHHh', r, 4)
        flags, k, iv = struct.unpack_from('<Iif', r, 12)
        pos = struct.unpack_from('<3f', r, 0x18)
        rot = struct.unpack_from('<3f', r, 0x28)
        scl = struct.unpack_from('<3f', r, 0x38)
        out.append(dict(b0=b0, slot=slot, kind=lkind, id=rid, grp=grp, file=fil, joint=joint, flags=flags, k=k,
                        interval=iv, pos=pos, rot=rot, scl=scl))
    return out


def efl_colour_block(d):
    """4U EFL header +0x2c block (4 words) or None (see M19A03_AREA_SOIL)."""
    o = struct.unpack_from('<I', d, 0x2c)[0]
    return struct.unpack_from('<4I', d, o + 0x30) if o else None


def pel_colour(path, rid, S=None, soil=M19A03_AREA_SOIL):
    """RGBA 4U multiplies into the units of record `rid` (EFL `path`), None = 4U keeps the unit colours."""
    b = efl_colour_block((S or sources())[(path, T['EFL'])])
    if not b or not b[0] & 0x10:
        return None
    if not (b[3] >> 16) & 0xFF:
        return soil
    return CODE_COLOUR.get(rid)


def pel_record(path, r, S=None, soil=M19A03_AREA_SOIL):
    st = bytearray(160)
    struct.pack_into('<4f', st, 0x00, *r['pos'], 0.0)
    struct.pack_into('<4f', st, 0x10, *r['rot'], 0.0)
    struct.pack_into('<4f', st, 0x20, *r['scl'], 0.0)
    struct.pack_into('<HH', st, 0x30, r['id'], r['joint'] & 0xFFFF)
    st[0x34:] = PEL_TAIL_PREV if pel_follows(r['id']) else PEL_TAIL
    for o, v in PEL_COLOUR_OFF:
        st[o] = v
    col = pel_colour(path, r['id'], S, soil)
    if col:
        st[PEL_COLOUR_RGBA:PEL_COLOUR_RGBA + 4] = col
        st[PEL_COLOUR_ON], st[PEL_COLOUR_MODE] = 1, PEL_COLOUR_MUL
    mask = (1 << r['k']) if 0 <= r['k'] < 32 else 0xFFFFFFFF
    struct.pack_into('<I', st, 0x48, mask)
    p = path.encode('ascii')
    return bytes([len(p)]) + p + b'\x01\x00' + bytes(st)


def build_pel(recs, S=None, soil=M19A03_AREA_SOIL, list2=None):
    """recs: [(efl path, mef record)] -> PEL v15: list 0 empty, list 1 = all records (motion sequences, PSL kind 4),
    list 2 (code posts) = all records too, or list2 = (count, record bytes) of another PEL (pel_lists)."""
    body = b''.join(pel_record(p, r, S, soil) for p, r in recs)
    n2, body2 = list2 if list2 is not None else (len(recs), body)
    return b'PEL\0' + struct.pack('<II', 15, 0) + struct.pack('<I', len(recs)) + body + \
        struct.pack('<I', n2) + body2


def pel_lists(d):
    """a PEL v15's three lists as (count, record bytes); record = u8 path length, path, 2 bytes, 160 bytes"""
    assert d[:4] == b'PEL\0' and struct.unpack_from('<I', d, 4)[0] == 15
    out, i = [], 8
    for _ in range(3):
        n = struct.unpack_from('<I', d, i)[0]
        i += 4
        start = i
        for _ in range(n):
            i += 1 + d[i] + 2 + 160
        out.append((n, d[start:i]))
    assert i == len(d), 'PEL size'
    return out


def lmt_events(d):
    """[(anim index, frames, remap[32], [(bits, frames)])] of event group 2, None for empty animations."""
    n = struct.unpack_from('<H', d, 6)[0]
    offs = struct.unpack_from('<%dI' % n, d, 8)
    out = []
    for i, o in enumerate(offs):
        if not o:
            out.append(None); continue
        frames = struct.unpack_from('<I', d, o + 8)[0]
        ev = struct.unpack_from('<I', d, o + 0x34)[0]
        if not ev:
            out.append((i, frames, None, [])); continue
        b = ev + 0x48 * 2
        remap = struct.unpack_from('<32H', d, b)
        cnt, ptr = struct.unpack_from('<II', d, b + 0x40)
        evs = [struct.unpack_from('<II', d, ptr + 8 * k) for k in range(cnt)] if ptr else []
        out.append((i, frames, remap, evs))
    return out


def build_psl(lmt, known_ids, log=None):
    """one PSL per motion list: entry per animation with group-2 effect slots whose MEF id has a PEL record."""
    anims = lmt_events(lmt)
    n = len(anims)
    entries = []
    for a in anims:
        if not a or not a[2]:
            entries.append(None); continue
        i, frames, remap, evs = a
        mask = 0
        ids = [0] * 32
        for k, r in enumerate(remap):
            if r and r in known_ids:
                mask |= 1 << k; ids[k] = r
            elif r and log is not None:
                log.append('PSL anim %d slot %d: MEF id %d has no PEL record (not in the MEF)' % (i, k, r))
        if not mask or not evs:
            entries.append(None); continue
        # run lengths: 4U totals = frames (114/114 em089 motions), GU PSLs total frames - 1 (every Kushala motion)
        evs = [list(x) for x in evs]
        if sum(f for b, f in evs) == frames:
            evs[-1][1] -= 1
            if evs[-1][1] <= 0: evs.pop()
        kinds = [4 if mask >> k & 1 else 0 for k in range(32)]
        data = struct.pack('<I32H32I32I', mask, *ids, *kinds, *([0] * 32))
        assert len(data) == 0x144
        entries.append((frames, data, evs))
    hdr_len = 8 + 4 * n
    pos = (hdr_len + 15) & ~15
    offs, blob = [], bytearray()
    for e in entries:
        if not e:
            offs.append(0); continue
        frames, data, evs = e
        ent_at = pos + len(blob)
        data_at = ent_at + 16
        ev_at = data_at + len(data) + 8
        blob += struct.pack('<IHBBII', frames, 0, 32, 0, data_at, 0)
        blob += data + struct.pack('<II', len(evs), ev_at)
        blob += b''.join(struct.pack('<II', b, f) for b, f in evs)
        while len(blob) % 16: blob += b'\0'
        offs.append(ent_at)
    head = b'PSL\0' + struct.pack('<HH', 2, n) + struct.pack('<%dI' % n, *offs)
    return head + b'\0' * (pos - len(head)) + bytes(blob)

# ------------------------------------------------------------------ the em089 set

# Code-posted effects (module/em089_efx.c), PEL list-2 records with ids above the 4U MEF range (max 1021).
EM089_EFL = 'effect\\efl\\em\\em089\\em089_%03d'
A16 = 360.0 / 65536.0                   # u16 angle -> degrees


def _rec(rid, fil, joint=-1, k=-1, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), scl=1.0):
    return (EM089_EFL % fil, dict(id=rid, joint=joint, k=k, pos=pos, rot=rot, scl=(scl, scl, scl)))


def extra_records():
    """[(efl path, record)] of the effects em089's code posts (4U sources in brackets).
    3000 / 3001: uShell050 tar blob attached effect [per-kind table 0x1031694: (65, 2) kinds 0, 1, 6-9 = em089_003,
      (65, 14) kinds 2-5 = em089_016; mask -1, scale table +1008 = 1.0], on the shell (joint -1).
    4200 + sub / 4300 + sub: uShell016 uEffect002 [init 0xc69ddc -> 0xc0b470 mode 1; end 0xc6cbd8 / 0xc6dd90 /
      0xc6e8d0 mode 2 at life <= 10]: ids 48 / 50 -> em089_005, 53 / 54 -> em089_012 (table 0xfd0b94); per frame
      [0x1b5ba0] at the shell's start point (joint 3 + M * offset) along the capsule, scale 2.5 (transform +0x60),
      id 50 pitch +35, id 54 +40 u16 units; mode = EFL element mask (0xafd76c) -> k 0 / 1. World records: the
      position and rotation come from em089_efx.c at the post and every frame (GU live update as 0x10ab3d8).
    5701 / 5702 / 5704: uEffect002 57 [0xc0bd38, update 0x1b6520] = em089_050 on joint 1, modes 1 / 2 / 4.
    5100 + sub: uShell051 ground shell effect [0xc904d0 -> 0xc08628: table 0x1031b54 {group, file, mask}, scale table
      0x1032020] at the shell position (posted at a world position)."""
    out = [_rec(3000, 3), _rec(3001, 16)]
    # 3100: 4U 0x954e5c ground impact (2/35 landing): 0xc08628 group 1 file 64 = qe006_000 (dust), mask -1, material
    # variant byte (0xc094e8) not representable; effect scale = s0 * kind factor (kind 1: 0.8 * 0.8) baked in.
    # 3200 (roar blur, make_roar_blur) NOT emitted: the EFL Filter unit's strength words are an RGBA colour + alpha
    # (Capcom values (1,1,1,1), (0.924,0.871,0.849,1), (1,1,1,0.15)...), em089_011's (0.844 x4) is a beam screen effect;
    # no calibration to 4U's code blur (peak 0.035) exists, and a wrong full-screen filter is very visible.
    out.append(('effect\\efl\\qe\\qe006\\qe006_000', dict(id=3100, joint=-1, k=-1, pos=(0.0, 0.0, 0.0),
                                                       rot=(0.0, 0.0, 0.0), scl=(0.64, 0.64, 0.64))))
    # 3300: 4U slot 64 0x8c67c0, tail first break: 0xc088d8 group 1 file 138 (flat table 0xef895c) = qe013_002 on
    # joint 143, offset (0, 30, -100), scale 2, mask -1; its colour (37, 46, 49, 255) set by 0xc48378 = CODE_COLOUR.
    out.append(('effect\\efl\\qe\\qe013\\qe013_002', dict(id=3300, joint=143, k=-1, pos=(0.0, 30.0, -100.0),
                                                       rot=(0.0, 0.0, 0.0), scl=(2.0, 2.0, 2.0))))
    # 4U places every uShell016 effect from the shell's capsule (0x1b5ba0), so all are world records (joint -1); the
    # old joint-3 records 4000 / 4100 + sub (x angle in the joint frame) disagreed with the capsule in test 3.
    # Scale 1.0, not 4U's 2.5 (transform +0x60): these are posted through the monster, whose attach model already
    # carries its 2.5 model scale (test 4: the beams vanished and the owner-referenced ground effects came out ~2.5x
    # too big; module/em089_efx.c logs the resulting transform scale to confirm).
    s016 = {36: 5, 37: 5, 41: 12, 51: 12, 52: 12, 53: 5, 54: 12, 55: 12, 56: 12}
    for sub, fil in sorted(s016.items()):
        out.append(_rec(4200 + sub, fil, -1, 0, scl=1.0))
        if sub in (41, 51, 52, 54, 55, 56):                # end effect: 51 -> id 54, others id 53
            out.append(_rec(4300 + sub, 12, -1, 1, scl=1.0))
    for mode, k in ((1, 0), (2, 1), (4, 2)):
        out.append(_rec(5700 + mode, 50, 1, k))
    s051 = {1: (2, 1.0), 3: (15, 1.0), 6: (8, 1.0), 9: (15, 0.5), 10: (15, 0.5), 11: (15, 0.5), 12: (15, 0.5),
            13: (13, 1.0), 14: (15, 0.7), 15: (13, 1.0), 16: (2, 1.0), 17: (8, 1.0), 19: (8, 1.2), 20: (8, 1.5)}
    for sub, (fil, scl) in sorted(s051.items()):
        out.append(_rec(5100 + sub, fil, -1, -1, scl=scl))
    # the uShell051 end posts (0xc906d8): 4 / 5 / 8 / 18 = table 0x1031b54 {65, element 12 = em089_014, mask 1 / 2 /
    # 2 / 2} -> k 0 / 1 (mask = 1 << k), scale table 0x1032020 1.0 / 1.3 / 1.0 / 1.0
    for sub, (fil, k, scl) in sorted({4: (14, 0, 1.0), 5: (14, 1, 1.3), 8: (14, 1, 1.0), 18: (14, 1, 1.0)}.items()):
        out.append(_rec(5100 + sub, fil, -1, k, scl=scl))
    # 6200 + k: the fallen Dragonator spear (4U cut object 1 + its controller 0xc2e96c, module/em089_pile.c): group 65
    # file 24 = em089_024, element mask 1 << k (1 landing, 2 charge, 4 explosion, 8 collapse, 16 wobble peak), posted
    # at world positions / on the spear object by the module
    for k in range(5):
        out.append(_rec(6200 + k, 24, -1, k))
    out += stage_records()
    return out


# 4U sEffect scheduler event CreateKowareEft (handler 0xc0afa8): index 1..17 -> table 0xe06378 {u16 group, u16 file}
# of the flat EFL table 0xef895c; mask = 1 << KowareEftGroup (+0x1ca), material = KowareEftJimenType (+0x1cc, desc
# +0x18, not representable), position KowareEftPos (+0x1d0), scale KowareEftScale (+0x1e0), area KowareEftAreaNo
# (+0x1c8, played only in the player's area). Battlequarters schedulers m19a03d-e01..e10 use indices 2, 11, 12, 16.
KOWARE_EFL = {2: 'effect\\efl\\qe\\qe016\\qe016_003', 11: 'effect\\efl\\st\\m19a03\\m19a03_000'}
KOWARE_EFL.update({12 + i: 'effect\\efl\\st\\m19a03\\m19a03_%03d' % n for i, n in enumerate((1, 2, 3, 4, 8, 9))})
M19A03_EFL = 'effect\\efl\\st\\m19a03\\m19a03_%03d'


ROAR_BLUR = 'effect\\efl\\em\\em089\\em089_roarblur'   # port-made (no 4U file): see make_roar_blur
ROAR_BLUR_FRAMES = 148    # 4U 0x3e3b14 ramp at 30 fps: 0 -> 0.035 (+0.005/f, 7 f), -> 0.025 (-0.0002/f, 50 f),
                          # -> 0 (-0.0015/f, 16.7 f) = 74 frames = 148 frames at the EFL's 60 fps


def make_roar_blur(S):
    """4U-format EFL with one radial-blur Filter entry for the roar (4U 0xc0819c creates a uMhRadialBlurFilter in
    code; GU blurs through EFL Filter units). Built from em089's own 4U Filter entry (em089_011 entry 5: element
    header, Filter unit, its two param blocks, tail record), offset zeroed (the 4U blur centres on joint 3, = the
    PEL record joint) and the tail word 1 (40 in em089_011) set to the 4U ramp length. The Filter strength words
    (0.844) are em089_011's: the GU filter constants are uploaded to the shader as a block (0x8b9094), so 4U's
    0.035 peak has no traced GU counterpart, and the ramp shape is not reproduced (constant strength)."""
    d = S[('effect\\efl\\em\\em089\\em089_011', T['EFL'])]
    p = efl_parse(d)
    ent = p['ents'][5]
    bl = {o: s for o, s, _ in p['blocks']}
    hdr = bytearray(d[:0x30])
    struct.pack_into('<HH', hdr, 0x10, 1, 1)
    first = (0x30 + 16 + 4 + 15) & ~15
    blob, words, pos = bytearray(), [], first
    for w in ent:
        if not w >> 8:
            words.append(w); continue
        o = (w >> 8) + 0x30
        words.append(((pos - 0x30) << 8) | (w & 0xFF))
        blob += d[o:o + bl[o]]
        pos += bl[o]
    t_off = p['tail'][5] + 0x30
    tail = bytearray(d[t_off:t_off + bl[t_off]])
    w0 = struct.unpack_from('<I', tail, 0)[0]
    struct.pack_into('<I', tail, 0, w0 & ~0xFF)                    # entry index 5 -> 0
    struct.pack_into('<I', tail, 4, ROAR_BLUR_FRAMES)
    assert struct.unpack_from('<3f', tail, 32) == (0.0, -50.0, 130.0)
    struct.pack_into('<3f', tail, 32, 0.0, 0.0, 0.0)               # em089_011's beam offset (0, -50, 130) -> 0
    tail_rel = pos - 0x30
    blob += tail
    pos += len(tail)
    out = bytearray(hdr) + struct.pack('<4I', *words) + struct.pack('<I', tail_rel)
    out += b'\0' * (first - len(out)) + blob
    struct.pack_into('<I', out, 8, len(out) - 0x30)
    efl_parse(bytes(out))
    return bytes(out)


def stage_records():
    """6000 + 4 * index + group: KowareEft index (2, 11..17) with element mask 1 << group (groups 0..2), scale 1;
    6100 + n: m19a03_NNN (all 14 arena EFLs), mask -1 (the ones outside the KowareEft table are played by 4U
    gimmick code the alias does not run)."""
    def rec(path, rid, k):
        return (path, dict(id=rid, joint=-1, k=k, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), scl=(1.0, 1.0, 1.0)))
    out = [rec(p, 6000 + 4 * i + g, g) for i, p in sorted(KOWARE_EFL.items()) for g in range(3)]
    out += [rec(M19A03_EFL % n, 6100 + n, -1) for n in range(14)]
    return out


def em089_spec():
    """Gogmazios' effect set (tools/build_em089_arc.py) for effect_set"""
    return dict(arc=SRC_EM089, stage_unpacked=STAGE_UNPACKED, mef=MEF_PATH, em_efl='effect\\efl\\em\\em089\\',
                groups=GROUP_EFL, extra=extra_records(), lmts=[(LMT_PATH % i, PSL[i]) for i in range(4)], pel=PEL_U,
                soil=M19A03_AREA_SOIL, list2=None)


def em089_set(log):
    return effect_set(em089_spec(), log)


def effect_set(spec, log):
    """A 4U monster's effects in GU form: {(path, type): bytes} in arc load order (textures, animations, effect
    models, EFLs, PEL u, PSLs). spec: arc (its 4U arc), stage_unpacked (unpacked 4U stage arcs, lowest priority),
    mef (its MEF path), em_efl (its EFL family prefix: every file in it is converted), groups {MEF group: EFL path
    pattern}, extra [(EFL path, record)] (records for code posts), lmts [(4U LMT path, GU PSL path)] (one PSL per motion
    list), pel (the GU PEL u path), soil (RGBA of the stage's area colour that 4U multiplies in), list2 (None = PEL
    list 2 holds our records too, or (count, record bytes) of a GU PEL's list 2: the GU class posts its own ids)."""
    S = sources(spec['arc'], spec['stage_unpacked'])
    mef = mef_records(S[(spec['mef'], T['MEF'])])
    efls = {p for (p, t) in S if t == T['EFL'] and p.startswith(spec['em_efl'])}
    pel_recs = []
    for r in mef:
        fam = spec['groups'].get(r['grp'])
        path = fam % r['file'] if fam else None
        if not path or (path, T['EFL']) not in S:
            log.append('MEF id %d: group %d file %d has no 4U EFL -> no PEL record' % (r['id'], r['grp'], r['file']))
            continue
        efls.add(path)
        pel_recs.append((path, r))
    for path, r in spec['extra']:
        assert (path, T['EFL']) in S and r['id'] not in {q['id'] for _, q in pel_recs}, (path, r['id'])
        efls.add(path)
        pel_recs.append((path, r))
    out = collections.OrderedDict()           # (path, type) -> bytes, filled per kind, emitted in load order
    conv = {'TEX': {}, 'EAN': {}, 'MRL': {}, 'MOD': {}, 'EFL': {}}
    need = set()
    for p in sorted(efls):
        d4 = S[(p, T['EFL'])]
        l = []
        conv['EFL'][p] = convert_efl(d4, l, spec['soil'])
        _, bad = check_efl(conv['EFL'][p])
        assert not bad, (p, bad)
        log.append('EFL %s: %d entries, %d B -> %d B%s' % (p, efl_parse(d4)['n'], len(d4), len(conv['EFL'][p]),
                   ('; ' + '; '.join(l)) if l else ''))
        need |= set(efl_paths(d4))
    for p in sorted(need):
        found = [t for (q, t) in S if q == p]
        if not found:
            log.append('MISSING resource %s (named by an EFL)' % p); continue
        for t in found:
            if t == T['TEX']: conv['TEX'][p] = convert_tex(S[(p, t)])
            elif t == T['EAN']: conv['EAN'][p] = convert_ean(S[(p, t)])
            elif t == T['MOD']:
                mrl4 = S.get((p, T['MRL']))
                try:
                    gmod, gmrl, mtex = convert_model(p, S[(p, t)], mrl4)
                except (Exception, SystemExit) as e:
                    log.append('MODEL %s NOT converted: %s' % (p, e)); continue
                conv['MOD'][p], conv['MRL'][p] = gmod, gmrl
                for tp in mtex:
                    if tp not in conv['TEX'] and (tp, T['TEX']) in S:
                        conv['TEX'][tp] = convert_tex(S[(tp, T['TEX'])])
                    elif (tp, T['TEX']) not in S:
                        log.append('MISSING texture %s (material of %s)' % (tp, p))
                log.append('MODEL %s: %d materials' % (p, len(modlib.parse(gmod)['material_names'])))
    for kind in ('TEX', 'EAN', 'MRL', 'MOD', 'EFL'):
        for p in sorted(conv[kind]):
            out[(p, T[kind])] = conv[kind][p]
    out[(spec['pel'], T['PEL'])] = build_pel(pel_recs, S, spec['soil'], spec['list2'])
    known = {r['id'] for _, r in pel_recs}
    for lmt, psl in spec['lmts']:
        out[(psl, T['PSL'])] = build_psl(S[(lmt, T['LMT'])], known, log)
    lists = 'x 2 lists' if spec['list2'] is None else '(list 1) + %d GU records (list 2)' % spec['list2'][0]
    log.append('PEL %s: %d records %s; PSL x%d from LMT event group 2' % (spec['pel'], len(pel_recs), lists,
                                                                        len(spec['lmts'])))
    return out


def entries(log=None):
    log = [] if log is None else log
    return [(p, t, d) for (p, t), d in em089_set(log).items()]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'report'
    if cmd == 'check':
        p, bad = check_efl(open(sys.argv[2], 'rb').read())
        print('ver %#x entries %d tail %d blocks %d bad %s' % (p['ver'], p['n'], p['n2'], len(p['blocks']), bad))
        return
    log = []
    ents = entries(log)
    for l in log: print(l)
    kinds = collections.Counter(t for _, t, _ in ents)
    print('entries %d: %s, %.1f KB' % (len(ents), {k: kinds[v] for k, v in T.items() if kinds[v]},
                                        sum(len(d) for _, _, d in ents) / 1024))
    if cmd == 'build':
        out = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('EFX_OUT', os.path.join(ROOT, 'dump/converted/em089_efx'))
        for p, t, d in ents:
            fn = os.path.join(out, p.replace('\\', '/') + '.%08x' % t)
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            open(fn, 'wb').write(d)
        open(os.path.join(out, '_report.txt'), 'w').write('\n'.join(log) + '\n')
        print('written to', out)


if __name__ == '__main__':
    main()
