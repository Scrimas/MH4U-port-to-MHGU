"""mrl_build.py : build MHGU material lists (MRL v0x22) from GU template materials.

A GU material entry is 60 bytes:
  w0 class hash, w1 name hash (crc32(name) ^ ~0, = the MOD material name), w2 parameter block size,
  w3..w5 state words ((hash20 << 12) | record: BS*, DS*, RS*), w6 (low 12 bits = descriptor count), w7 flags,
  w8..w11 0, w12 animation block size, w13 parameter block offset, w14 animation block offset.
  w6 bits 21-28 = material type (the 'mNN' of the material name; see tools/mrl_anim.py "GU runtime").
The parameter block is position independent: count x 12-byte descriptors {a, value, word} then constant data.
Descriptor type = a & 0xF: 3 = texture (value = 1-based texture table index), 1 = constant buffer (value = offset
inside the block), 2 = sampler, 0 = feature select. We copy a template's entry + block and rewrite the name hash
and the texture indices (by descriptor name: tAlbedoMap, tNormalMap, tSpecularMap, ...).
"""
import struct, sys, zlib

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import paths
sys.path.insert(1, paths.GU_PY)      # after this dir, as before
import mrl
from arc import arc_entries, arc_read

GU_PKG = 0xB2D34C60          # AppShaderPackage.mfx hash, as in every GU MRL
TEX_TYPE = 0x241F5DEB

# name -> (GU arc, MRL path inside it, material index); all three have no animation block
TEMPLATES = {
    # Rathian's BODY material (mat 2: FTransparency, w6 0x200dc020, w7 0x8c800000, the most common GU
    # normal-mapped body setup). Until 2026-10-17 this was mat 0 = Rathian's WING (FTransparencyAlpha alpha-test
    # variant, wing flags w6 0x264dc020 / w7 0x8d901400), a poor fit for em089's opaque tar overlays.
    'solid_nm': ('/nativeNX/arc/enemy/em001_00.arc', 'enemy\\em001\\em001_00\\mod\\em001_00', 2),  # tNormal, tAlbedo, tSpecular
    # lit body without normal map (em030_00 mat 0: emission 0, diffuse 0.9, specular 0.5, FAlbedoMapColorOnly,
    # tSpecularMap = its BM+A). Until 2026-10-17 'solid' was em004_00 mat 0, which is an UNLIT material
    # (fEmissionColor 1, fDiffuseColor 0, fSpecularColor 0): the em089 body rendered flat/washed out and fogged.
    'solid':    ('/nativeNX/arc/enemy/em030_00.arc', 'enemy\\em030\\em030_00\\mod\\em030_00', 0),  # tAlbedo, tSpecular
    # 4U 'XfB__E0__' materials (lit by their tExtendMap sphere texture): Capcom's own conversion of that preset,
    # em019_00 mat 0 'XfB__E0__m00_body' (tAlbedo, tSpecular, tSphereMap = the 4U extend texture, IASkinTB2wt; 25 GU
    # enemy materials share the setup). Tigerstripe's body / fat body (test 2026-10-21: without it the puffed belly
    # rendered black on its shadow side).
    'solid_sphere': ('/nativeNX/arc/enemy/em019_00.arc', 'enemy\\em019\\em019_00\\mod\\em019_00', 0),
    # unlit/emissive (4U emission 1, diffuse 0: em089's eye material)
    'unlit':    ('/nativeNX/arc/enemy/em004_00.arc', 'enemy\\em004\\em004_00\\mod\\em004_00', 0),  # tAlbedo, tSpecular
    'add':      ('/nativeNX/arc/enemy/em037_00.arc', 'enemy\\em037\\em037_00\\mod\\em037_00', 3),  # BSAddAlpha: tAlbedo, tSpecular
    # em089's tar (4U 'XfBAN__EW_1__m0N_liquid_*': alpha-tested overlay, w7 alpha test ref 75; tar-look agent
    # 2026-10-18). GU em082_04 mat 4 'XfBAN__EW_1__m52_far' = the same Capcom 'XfBAN__EW_1' overlay preset: BSSolid,
    # FTransparencyAlpha (alpha = albedo.a * fTransparency, alpha test), FAlbedoMap (alpha used), FBumpNormalMap,
    # IASkinTBNLA2wt, no 5th state; every other feature equals 'solid_nm' (em001 mat 2). w7 0x8d912f00.
    'tar':      ('/nativeNX/arc/enemy/em082_04.arc', 'enemy\\em082\\em082_04\\mod\\em082_04', 4),  # tNormal, tAlbedo, tSpecular
    # alpha-tested lit material without normal map (em089's wing: 4U w7 alpha test ref 40, Small / Large w anims).
    # GU em058_00 mat 5 'XfBAN__E0__m52_face_d': BSSolid, FTransparencyAlpha, FAlbedoMap, IASkinTB2wt, no 5th
    # state; features and descriptors otherwise identical to 'solid' (em030 mat 0). w7 0x8d900000.
    'solid_at': ('/nativeNX/arc/enemy/em058_00.arc', 'enemy\\em058\\em058_00\\mod\\em058_00', 5),  # tAlbedo, tSpecular
}

# MRL entry w7 (same layout in 4U and GU, checked on every GU enemy MRL): bits 8-15 = alpha-test reference (0..255),
# bits 16-19 = depth bias N of the RSMeshBiasN state (GU: B12 -> 12 on 72/72, B10 29/29, ...), bit 24 = alpha
# test on BSSolid materials (GU 0x8d.. BSSolid + FTransparencyAlpha, 0x8c.. opaque; 4U tar / wing 0x85.., body
# 0x84..); blended materials use other top bits (GU 0x91.., 4U add 0x88..), kept from the template.
W7_REF_SHIFT, W7_BIAS_SHIFT, W7_ALPHATEST = 8, 16, 1 << 24


def name_hash(name):
    return zlib.crc32(name.encode('ascii')) ^ 0xFFFFFFFF


def load_template(romfs, key):
    arc_path, mrl_path, idx = TEMPLATES[key]
    d = romfs.read(arc_path)
    b = [arc_read(d, e) for e in arc_entries(d) if e[1] == 0x2749C8A8 and e[0] == mrl_path][0]
    moff = struct.unpack_from('<I', b, 24)[0]
    w = list(struct.unpack_from('<15I', b, moff + 60 * idx))
    assert w[12] == 0, 'template has an animation block'
    return w, b[w[13]:w[13] + w[2]]


def texture_slots(block, count):
    """[(descriptor offset, slot name)] for the texture descriptors."""
    out = []
    for k in range(count):
        a, v, word = struct.unpack_from('<III', block, 12 * k)
        if a & 0xF == 3:
            out.append((12 * k, mrl.rec_name(0x22, word)))
    return out


def state_word(name):
    """GU state word for a shader-package record name: (~crc32(name) & 0xFFFFF) << 12 | record number
    (checked on BSSolid 0x62b2d186, DSZTestWrite 0xb81391b9, RSMesh 0x108cf1c2, RSMeshBias4 0x6d6841c6)."""
    rec = [k for k, (a, _) in mrl.records(0x22).items() if a == name]
    assert rec, 'no GU shader record %s' % name
    return ((name_hash(name) & 0xFFFFF) << 12) | rec[0]


def set_state(w, name):
    """replace the template's state word of the same kind (BS*, DS*, RS*: first two letters) by `name`."""
    for i in range(3, 8):
        cur = mrl.rec_name(0x22, w[i])
        if cur and cur[:2] == name[:2]:
            w[i] = state_word(name)
            return
    raise SystemExit('template has no %s* state' % name[:2])


def cb_words(romfs, key):
    """{constant buffer name: descriptor word} of a template (animation tracks name their buffer by this word)."""
    w, block = load_template(romfs, key)
    out = {}
    for k in range(w[6] & 0xFFF):
        a, v, word = struct.unpack_from('<III', block, 12 * k)
        if a & 0xF == 1: out[mrl.rec_name(0x22, word)] = word
    return out


def set_constant(w, block, cbname, var, values):
    """overwrite constant `var` of buffer `cbname` ('$Globals', 'CBMaterial') in a material parameter block."""
    cb_off = None
    for k in range(w[6] & 0xFFF):
        a, v, word = struct.unpack_from('<III', block, 12 * k)
        if a & 0xF == 1 and mrl.rec_name(0x22, word) == cbname:
            cb_off = v
    assert cb_off is not None, 'material has no %s' % cbname
    fo, rows, cols = mrl.cb_layout(0x22, cbname)[var]
    assert len(values) == rows * cols, (var, rows, cols)
    struct.pack_into('<%df' % len(values), block, cb_off + 4 * fo, *values)


def build(romfs, materials, textures):
    """materials: [(name, template key, {slot: 1-based texture index}[, [state names][, {(cb, var): values}]])];
    slots not given take tAlbedoMap's index. Optional state names (e.g. the 4U material's 'RSMeshBias10') replace
    the template's state of the same kind: em089's tar materials are coplanar overlays of the body that 4U lifts
    with RSMeshBias5..12 (body RSMeshBias2); with the templates' RSMesh they z-fight and lose to the body.
    Optional constants overwrite template constants by name (see set_constant), e.g. a 4U material animation's
    first frame baked in. Optional 6th element {'anim': GU animation block bytes (mrl_anim.build), 'mtype':
    material type (the 'mNN' of the 4U name, w6 bits 21-28), 'alpha_ref': w7 alpha-test reference 0..255, 'bias':
    w7 depth-bias nibble (W7_* above)}. textures: [path] (no extension). Returns MRL bytes."""
    tex_off = 0x1C
    mat_off = tex_off + 76 * len(textures)
    blk_off = mat_off + 60 * len(materials)
    tex_tab = b''.join(struct.pack('<3I64s', TEX_TYPE, 0, 0, p.encode('ascii')) for p in textures)
    words, blocks, anims = [], [], []
    for mat in materials:
        name, key, slots = mat[:3]
        extra = mat[5] if len(mat) > 5 else {}
        w, block = load_template(romfs, key)
        for st in (mat[3] if len(mat) > 3 else ()):
            set_state(w, st)
        block = bytearray(block)
        for (cbname, var), values in (mat[4] if len(mat) > 4 else {}).items():
            set_constant(w, block, cbname, var, values)
        for off, slot in texture_slots(block, w[6] & 0xFFF):
            idx = slots.get(slot, slots['tAlbedoMap'])
            struct.pack_into('<I', block, off + 4, idx)
        if 'mtype' in extra:      # material type = w6 bits 21-28 (GU loader 0xb45f74 -> material object +0x18)
            w[6] = (w[6] & ~(0xFF << 21)) | ((extra['mtype'] & 0xFF) << 21)
        if 'alpha_ref' in extra:  # w7 alpha-test reference (template must be alpha-tested: w7 bit 24)
            assert w[7] & W7_ALPHATEST, '%s: template %s is not alpha-tested' % (name, key)
            w[7] = (w[7] & ~(0xFF << W7_REF_SHIFT)) | ((extra['alpha_ref'] & 0xFF) << W7_REF_SHIFT)
        if 'bias' in extra:       # w7 depth-bias nibble, = N of the RSMeshBiasN state given above
            w[7] = (w[7] & ~(0xF << W7_BIAS_SHIFT)) | ((extra['bias'] & 0xF) << W7_BIAS_SHIFT)
        w[1] = name_hash(name)
        w[13] = blk_off + sum(len(b) for b in blocks)
        w[12] = w[14] = 0
        words.append(w)
        blocks.append(bytes(block))
        anims.append(extra.get('anim', b''))
    # animation blocks (tools/mrl_anim.build) after the parameter blocks, 16-byte aligned (GU em049_00 layout)
    pos = blk_off + sum(len(b) for b in blocks)
    tail = bytearray()
    for w, a in zip(words, anims):
        if not a: continue
        pad = -(pos + len(tail)) % 16
        tail += b'\0' * pad
        w[12], w[14] = len(a), pos + len(tail)
        tail += a
    hdr = struct.pack('<4s6I', b'MRL\0', 0x22, len(materials), len(textures), GU_PKG, tex_off, mat_off)
    return hdr + tex_tab + b''.join(struct.pack('<15I', *w) for w in words) + b''.join(blocks) + bytes(tail)
