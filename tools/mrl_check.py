"""mrl_check.py : compare every material of a built MRL with its GU template, structure field by field.

  mrl_check.py BUILT.mrl      (materials matched to templates by their class/state words)

Checks per material: entry size 60, identical entry words except w1 (name hash), w13/w14 (offsets) and w12
(animation size, 0 in our templates); identical parameter block except the texture descriptors' values;
same descriptor count, names and types; texture indices within the texture table.
"""
import struct, sys
sys.path.insert(0, '/home/scrimas/Projects/MHGU_Editor/scratch/py')
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from romfs import RomFS
import mrl, mrl_build, mrl_anim


def template_records(rom):
    out = {}
    for key in mrl_build.TEMPLATES:
        w, block = mrl_build.load_template(rom, key)
        out[key] = (w, block)
    return out


def changed_constants(m, block, tblock):
    """set of 'cb.var' whose floats differ between block and tblock; None in the set = a difference outside
    every named variable."""
    cbs = {}
    for name, t, v in m['params']:
        if t == 1: cbs[name] = v
    named = {}
    for cb, off in cbs.items():
        for var, (fo, rows, cols) in mrl.cb_layout(0x22, cb).items():
            if not var.startswith(('f', 'b', 'i')) or fo > 0x400: continue
            for k in range(rows * cols):
                named.setdefault(off + 4 * (fo + k), '%s.%s' % (cb, var))
    out = set()
    start = 12 * len(m['params'])
    for o in range(start, min(len(block), len(tblock)), 4):
        if block[o:o + 4] != tblock[o:o + 4]:
            out.add(named.get(o))
    return out


def check(d, rom):
    r = mrl.read(d)
    T = template_records(rom)
    ok = True
    for m in r['mats']:
        w = m['words']
        # w5 = RS state (replaced by the 4U raster state on purpose, mrl_build.set_state)
        # w6 bits 21-28 = material type (mrl_build 'mtype'), compared without them
        TM = ~(0xFF << 21) & 0xFFFFFFFF
        # w7 bits 8-19 = alpha-test reference + depth-bias nibble (mrl_build 'alpha_ref' / 'bias'), compared without
        R7 = ~(0xFFF << 8) & 0xFFFFFFFF
        same = lambda tw: tw[0] == w[0] and [tw[i] for i in (3, 4, 8, 9, 10, 11)] == \
            [w[i] for i in (3, 4, 8, 9, 10, 11)] and tw[6] & TM == w[6] & TM and tw[7] & R7 == w[7] & R7
        # templates with identical words (solid / unlit differ only in constants): the closest constants win
        cands = [k for k, (tw, _) in T.items() if same(tw)]
        key = min(cands, key=lambda k: len(changed_constants(m, m['block'], T[k][1]))) if cands else None
        if key is None:
            print('  %08x: no template with the same class/states' % w[1]); ok = False; continue
        tw, tblock = T[key]
        tm = mrl.read(struct.pack('<4s6I', b'MRL\0', 0x22, 1, 0, 0, 0x1C, 0x1C) +
                      struct.pack('<15I', *(tw[:13] + [0x58, 0])) + tblock)['mats'][0]
        diff_words = [i for i in range(15) if i not in (1, 5, 6, 7, 12, 13, 14) and w[i] != tw[i]]
        if w[7] & R7 != tw[7] & R7: diff_words.append(7)
        a_ref, bias = (w[7] >> 8) & 0xFF, (w[7] >> 16) & 0xF
        rs = mrl.rec_name(0x22, w[5]) or ''
        bias_ok = bias == (int(rs[10:]) if rs.startswith('RSMeshBias') else bias if rs == 'RSMeshCN' else 0)
        anim = 'none'
        if w[12]:
            try:
                ents = mrl_anim.parse(d[w[14]:w[14] + w[12]])
                desc = set()       # tracks must name one of the material's constant-buffer descriptor words
                for k in range(w[6] & 0xFFF):
                    a, v, wd = struct.unpack_from('<III', m['block'], 12 * k)
                    if a & 0xF == 1: desc.add(wd)
                bad = [t for e in ents for t in e['tracks'] if t['cb'] not in desc]
                anim = '%d entries%s' % (len(ents), ' BAD-CB' if bad else '')
                if bad: ok = False
            except Exception as ex:
                anim = 'PARSE ERROR %s' % ex; ok = False
        rs_ok = (mrl.rec_name(0x22, w[5]) or '').startswith('RSMesh')
        names = [(n, t) for n, t, _ in m['params']] == [(n, t) for n, t, _ in tm['params']]
        tex_ok = all(1 <= v <= len(r['textures']) for n, t, v in m['params'] if t == 3)
        nontex_same = [(n, t, v) for n, t, v in m['params'] if t != 3] == [(n, t, v) for n, t, v in tm['params'] if t != 3]
        # constants: allowed to differ only inside named variables (mrl_build.set_constant), reported by name
        changed = changed_constants(m, m['block'], tblock)
        good = (not diff_words and rs_ok and names and tex_ok and nontex_same and len(m['block']) == len(tblock)
                and None not in changed)
        ok &= good
        print('  %08x template %-8s type %d descriptors %d/%d words-differ %s %s w7 alpha-test %d ref %d bias %d%s '
              'names %s textures %s other-params %s constants-changed %s anim %s -> %s' % (
                  w[1], key, (w[6] >> 21) & 0xFF, len(m['params']), len(tm['params']), diff_words, rs,
                  (w[7] >> 24) & 1, a_ref, bias, '' if bias_ok else ' (!= RS state, template value)', names,
                  [(n, v) for n, t, v in m['params'] if t == 3], nontex_same, sorted(changed, key=str), anim,
                  'OK' if good else 'MISMATCH'))
    return ok


if __name__ == '__main__':
    rom = RomFS('/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin')
    sys.exit(0 if check(open(sys.argv[1], 'rb').read(), rom) else 1)
