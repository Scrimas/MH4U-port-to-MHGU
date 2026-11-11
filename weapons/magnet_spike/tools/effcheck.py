"""effcheck.py : replay GU's effect-load and Model-unit conditions on a built arc (no in-game test needed).

  effcheck.py ARC                 every EFL of the arc (a built file, or relative to the GU romfs)
  effcheck.py ARC SUBSTRING       only the EFLs whose path contains it (e.g. '\\ms_')

check(entries) takes [(path, type, bytes)] in arc order (msbuild runs it on the w05.arc it writes) and returns the
problem lines. Conditions (notes/gu-efl-units.md "Unit block, Model (type 5)"; C = traced in code):
- Model unit +0x50 path: empty -> record flag 0x2000; no rModel of that path -> flag 0x10 (0xb5bbec case 5, C). The
  MOD and its same-path MRL (rModel post-load 0xb49854) must come before the EFL in the arc (S: GU resolves names
  while the arc loads, as msbuild's PEL order).
- MOD version 0xd4 (rModel load 0xb490cc, C); every MOD material name in the MRL, else the default material
  (0xb49854, C), which fails the effect-draw ready check 0xa94b48 (class id compare, 0xb91ef0, C; S that the default
  is not the effect class) -> the whole effect build fails (0x9bda64, C). Effect-draw units: material class =
  EFFECT_MAT_CLASS (S: every GU effect-model material in w00 / w04 has it, incl. those GU draws in that mode).
- MRL textures in the arc before the MRL (S).
- Frame (unit +0x100 bits 12-21, range bits 22-31; skipped with the frame curve +0x44): some mesh of the model in that
  group (0xb49090, C) and, for scene-model units (unit +0x1a bit 0), frame < mesh count (0xa94c10 shows mesh bit j
  for j < count only when j == frame, C). Tests 18-20: frame 1 on one-mesh models = nothing drawn.
- Move kind 5 needs its position curve (move +0x70 != 0): 0xa59ce4 returns 0, the build fails (C).
- Effect-mode units (unit +0x1a bit 0 clear): blend index (unit byte 3) one of EFFECT_BLENDS (S: what GU uses).
- UV layer 0 (unit +0x134 lo16, a 0x40-B value block read by 0xa99f40 / 0xa6b824 / 0xa6bc0c, C): inside the EFL; its
  u / v curve offsets (+0x30 / +0x34, from the unit) zero or a curve header inside the EFL; no extra layers (+0x136,
  +0x138 bits 24-27: 0 in all 4708 GU effect-mode units of the player arcs, not decoded beyond 0xa99f40); damping
  (+0x20) finite. A bad offset reads garbage speeds or curves (no bounds check in the code)."""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, mod as modlib, mrl as mrllib
sys.path.append(paths.GU_PY)
from arc import arc_entries, arc_read

T_EFL, T_MOD, T_MRL, T_TEX = 0x6D5AE854, 0x58A15856, 0x2749c8a8, 0x241f5deb
EFFECT_MAT_CLASS = 0x5fb0ebe4
EFFECT_BLENDS = (0, 1, 5, 6)   # unit byte 3 of the 10731 GU effect-mode Model units (S: 0xb007fc state table)


def _cstr(d, o, n):
    return d[o:o + n].split(b'\0')[0].decode('ascii', 'replace')


def check(entries, only=None):
    """-> (problem lines, counts)"""
    pos = {(p, t): k for k, (p, t, _) in enumerate(entries)}
    data = {(p, t): d for p, t, d in entries}
    bad, n_units, n_efl = [], 0, 0
    models = {}
    def model(mp):
        if mp not in models:
            mod, mrl = data.get((mp, T_MOD)), data.get((mp, T_MRL))
            m = modlib.parse(mod) if mod else None
            r = mrllib.read(mrl) if mrl else None
            models[mp] = (m, r)
        return models[mp]
    for k, (p, t, d) in enumerate(entries):
        if t != T_EFL or (only and only not in p): continue
        n_efl += 1
        n = struct.unpack_from('<H', d, 0x10)[0]
        for i in range(n):
            w = struct.unpack_from('<4I', d, 0x30 + 16 * i)
            if w[3] & 0xf == 5 and w[3] >> 8 and not struct.unpack_from('<I', d, (w[3] >> 8) + 0x30 + 0x70)[0]:
                bad.append('%s e%d: move kind 5 without its position curve (+0x70 = 0): 0xa59ce4 fails' % (p, i))
            if w[1] & 0xff != 5 or not w[1] >> 8: continue
            n_units += 1
            u = (w[1] >> 8) + 0x30
            mp = _cstr(d, u + 0x50, 0x40)
            tag = '%s e%d (%s)' % (p, i, mp or 'no model')
            if not mp:
                bad.append('%s: empty model path (record flag 0x2000)' % tag); continue
            km, kr = pos.get((mp, T_MOD)), pos.get((mp, T_MRL))
            if km is None or km > k:
                bad.append('%s: MOD %s' % (tag, 'missing (record flag 0x10)' if km is None else 'after the EFL'))
                continue
            if kr is None or kr > km:
                bad.append('%s: MRL %s' % (tag, 'missing (default materials)' if kr is None else 'after the MOD'))
            m, r = model(mp)
            if m['version'] != 0xD4:
                bad.append('%s: MOD version %#x' % (tag, m['version']))
            scene = d[u + 0x1a] & 1
            if not scene and d[u + 3] not in EFFECT_BLENDS:
                bad.append('%s: blend index %d (GU effect-mode Model units use %s)' % (tag, d[u + 3], EFFECT_BLENDS))
            if r:
                mats = {mm['name']: mm for mm in r['mats']}
                for nm in m['material_names']:
                    mm = mats.get(mrllib.name_hash(nm))
                    if mm is None:
                        bad.append('%s: material %s not in the MRL (default material)' % (tag, nm))
                    elif not scene and mm['cls'] != EFFECT_MAT_CLASS:
                        bad.append('%s: material %s class %08x (ready check 0xa94b48)' % (tag, nm, mm['cls']))
                for tt, tp in r['textures']:
                    if tt == T_TEX and pos.get((tp, T_TEX), kr + 1) > kr:
                        bad.append('%s: texture %s %s' % (tag, tp, 'missing' if (tp, T_TEX) not in pos else 'after the MRL'))
            vb, x136 = struct.unpack_from('<HH', d, u + 0x134)
            if vb:
                if u + vb + 0x40 > len(d):
                    bad.append('%s: UV value block +0x134 = %#x past the EFL end' % (tag, vb))
                else:
                    c_u, c_v = struct.unpack_from('<II', d, u + vb + 0x30)
                    for nm, co in (('u', c_u), ('v', c_v)):
                        if co and (u + co + 4 > len(d) or not struct.unpack_from('<I', d, u + co)[0] & 0xff):
                            bad.append('%s: UV %s curve offset %#x invalid' % (tag, nm, co))
                    damp = struct.unpack_from('<f', d, u + vb + 0x20)[0]
                    if not (damp == damp and abs(damp) < 1e3):
                        bad.append('%s: UV damping %r' % (tag, damp))
            if x136 or (struct.unpack_from('<I', d, u + 0x138)[0] >> 24) & 0xf:
                bad.append('%s: extra UV layers (+0x136 %#x / +0x138 bits 24-27) not decoded' % (tag, x136))
            if struct.unpack_from('<H', d, u + 0x44)[0]: continue
            f = struct.unpack_from('<I', d, u + 0x100)[0]
            groups = {x['group'] for x in m['mesh_list']}
            for fr in range((f >> 12) & 0x3ff, ((f >> 12) & 0x3ff) + (f >> 22) + 1):
                if fr not in groups:
                    bad.append('%s: frame %d names no mesh group (has %s)' % (tag, fr, sorted(groups)))
                elif scene and fr >= len(m['mesh_list']):
                    bad.append('%s: scene-model frame %d >= %d meshes: nothing shown' % (tag, fr, len(m['mesh_list'])))
    return bad, (n_efl, n_units)


def main():
    a = sys.argv[1]
    if os.path.exists(a):
        d = open(a, 'rb').read()
    else:
        from romfs import RomFS
        d = RomFS(paths.GU_ROMFS).read('/nativeNX/arc/' + a)
    ents = [(e[0], e[1], arc_read(d, e)) for e in arc_entries(d)]
    bad, (ne, nu) = check(ents, sys.argv[2] if len(sys.argv) > 2 else None)
    for l in bad: print(l)
    print('effcheck: %d EFLs, %d Model units, %d problems' % (ne, nu, len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
