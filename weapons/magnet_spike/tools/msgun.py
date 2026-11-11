"""msgun.py : the shot's hand piece (MHF event 17, notes/effect-posts.md "Notes") as a GU effect model, for msbuild.py.

MHF (C unless marked): at f6 of actions 82 / 84 event 17 starts MS task kind 0 (0x10338670 -> 0x1004d700) on bone
18 (the -x hand) for 16 ticks (the event's parameter). Every tick it takes bone 18's matrix with the origin moved to
bone 18 + M18 (-4, -4, 2) and draws three meshes of the effect model pack (0x13, 0x74, 0x97 = our model0.fmod meshes
19, 116, 151) through the draw list 0x1ecde5e0 (callback 0x1004f7b0), each with 9 constants from 0x1004d4b0, the
first six (position, scale) x 0.95 (C). The draw callback 0x1004f7b0 (C, disassembled): the position p is turned by the
part's own rotation (0x10006830 / 0x10006880 / 0x1000d320: x, then y, then z, right-handed) and then by the bone
(D3DXVec3TransformNormal), added to the origin; the mesh matrix = Scaling(s) x RotX x RotY x RotZ (0x10004f80, row
vectors) x the bone matrix (task data +0x58 = 0x12 != 0), translation = that point. In column form, in the bone-18
frame: v -> R (S v + p), R = Rz Ry Rx. (Test 21 built R S v + p: the parts 15-50 cm apart, the barrel turned 90 deg.)
Drawn white with the default blend (0x114067e0 mode 1).

GU: one rigid effect model (mhfmodel: MOD, its effect material, the pack's PNG 1 = the meshes' only image; the
three parts baked into the bone-18 frame, merged into one mesh: a Model unit shows one mesh, mhffx2gu.MODEL_FRAME)
and one EFL entry = GU's one-shot Model unit
(mhffx2gu.MODEL_TEMPLATE, copied whole), life 32 frames, no motion, no spin, scale 1, white. The MHF hand bone 18
frame = GU joint 12's (as every other effect on a hand: msbuild.fx_post_tables, S). Test 18 (not seen): the unit was
em001_00_500 entry 1 cut at 0x140, its +0x134 value-block offset (0x170) left pointing past the cut; the vertex
colour (0, 0, 0, 255) where Capcom's weapon-effect models use 7f grey; the UVs unflipped (mhfmodel docstring)."""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import mhffx2gu

MESHES = (19, 116, 151)
PARTS = (((0.0, -10.0, 8.5), (0.9, 0.9, 0.9), (-1.920, 0.0, 1.571)),
         ((-13.0, -18.0, 0.0), (0.3, 0.8, 0.3), (0.785, 1.571, -0.785)),
         ((-13.0, 0.0, -35.0), (2.5, 2.5, 2.0), (0.0, 1.571, 0.0)))
K = 0.95                     # 0x1004d4b0 scales position and scale (C)
ORIGIN = (-4.0, -4.0, 2.0)   # bone 18 + M18 (-4, -4, 2): the PEL record's offset
BONE, FRAME, LIFE = 18, 6, 32
ACTIONS = (82, 84)
MODEL = 'effect\\base\\ms_gun_000'
EFL = mhffx2gu.EFL_DIR + '\\ms_gun'
KEY = ('gun', 0)             # the effect key of msbuild.fx_post_tables' rows


POSTS = [(('act', a), FRAME, KEY, BONE, ORIGIN, 0, 'att') for a in ACTIONS]


def euler(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def parts(src):
    """the three meshes, each R(rot) (S(K scale) v + K pos), in the bone-18 frame (mhfmodel parts; 0x1004f7b0, C)"""
    import mhfmodel
    out = []
    for mi, (pos, scl, rot) in zip(MESHES, PARTS):
        m = src.meshes[mi]
        R = euler(rot)
        P = (np.array(m['pos'], float) * (K * np.array(scl)) + K * np.array(pos)) @ R.T
        N = (np.array(m['normal'], float) / np.array(scl)) @ R.T
        out.append(mhfmodel.mesh_part(src, mi, P, N))
    return out


def build_efl(gu_read):
    """GU's one-shot Model unit (mhffx2gu.MODEL_TEMPLATE, whole: no dangling offsets) on our model: scale 1, no
    spin / growth / curves, white, MHF's alpha blend, 32 frames"""
    t = mhffx2gu.MODEL_TEMPLATE
    # the EFL head and group tails from em001_00_500 (as mhffx2gu's files): cm123_041's 14 tails hold offsets into
    # its own blocks (test 20: copied, they pointed past our file)
    tt = mhffx2gu.TEMPLATE
    d = gu_read(tt[0], tt[1])
    head = d[:0x30]
    n, n2 = struct.unpack_from('<HH', d, 0x10)
    tail = struct.unpack_from('<%dI' % n2, d, 0x30 + 16 * n)
    (te, el), (tu, u), (tm, em), (tv, mv) = mhffx2gu._template(gu_read, t)
    assert tu == 5 and tm == 17, 'template entry is not a one-shot Model'
    el = mhffx2gu.group_element((te, el), 1)[1]                 # group bit 0 = its one record's mask (build)
    u = bytearray(u[:mhffx2gu.MODEL_SIZE])
    u[3] = mhffx2gu.ALPHA_BLEND                                 # MHF's default blend (alpha)
    struct.pack_into('<f', u, 0x1c, 1.0)
    struct.pack_into('<4f', u, 0x28, 1.0, 0.0, 0.0, 0.0)        # size 1, no growth
    struct.pack_into('<HHHHHHHH', u, 0x38, 0, 0, 0, 0, 0, 0, 0, 0)   # no size / colour / UV curves
    u[0x48:0x50] = b'\xff' * 8                                  # white
    u[0x50:0x90] = MODEL.encode().ljust(0x40, b'\0')
    mhffx2gu.model_frame(u)                                     # the model's one mesh (group 0)
    mhffx2gu.model_effect_mode(u)                               # GU's effect draw (the blend byte)
    struct.pack_into('<6f', u, 0x90, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0)   # scale x / y / z
    struct.pack_into('<6f', u, 0xa8, *([0.0] * 6))                   # scale rates
    struct.pack_into('<6f', u, 0xd0, *([0.0] * 6))                   # rotation
    struct.pack_into('<6f', u, 0xe8, *([0.0] * 6))                   # angular speed
    struct.pack_into('<HHHHI', u, 0x130, 0, 0, 0, 0, 0)              # no curves, value block, UV layers, animation
    em = bytearray(em)
    struct.pack_into('<III', em, 0, 0, LIFE, 0)                      # fade-in 0, hold 32, fade-out 0
    tails = [d[x + 0x30:x + 0x30 + 0x70] for x in tail]
    return mhffx2gu.write_efl(head, [[(te, el), (tu, bytes(u)), (tm, bytes(em)), (tv, mv)]], tails)


def build(gu_read, rom):
    """-> (arc entries [(path, type, bytes)] in load order, {KEY: groups}, report)"""
    import mhfmodel
    src = mhffx2gu.Source()
    img = mhfmodel.image_of(src, MESHES[0])
    assert all(mhfmodel.image_of(src, mi) == img for mi in MESHES), 'the hand piece uses one atlas'
    ms = mhfmodel.Models(src, rom, prefix='effect\\base\\ms_gun_')
    ms.model('gun', parts(src), img, path=MODEL)
    ents = ms.entries() + [(EFL, mhffx2gu.T_EFL, build_efl(gu_read))]
    mod = ms.mods['gun'][2]
    return ents, {KEY: [(EFL, 1, (0.0, 0.0, 0.0))]}, ['hand piece: %s (%d B MOD, 3 parts in one mesh), %s' % (MODEL, len(mod), EFL)]
