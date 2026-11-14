"""setup.py : make dump/ (everything the converters and module/build.py read) from your own MH4U and MHGU dumps.
Safe to re-run: a step whose outputs all exist is skipped. Check the result with tools/doctor.py.

  python3 tools/setup.py [--force] [STEP ...]        default: every step, in order; --force redoes the steps

Your inputs (never commit them):
  dump/base/*.3ds      MH4U (EUR), decrypted (GodMode9 on your 3DS: cartridge or eShop title -> decrypted .3ds)
  dump/update/*.cia    MH4U v1.1 update (EUR), decrypted (GodMode9)
  dump/gu_exefs/       MHGU v1.4 ExeFS: in Ryujinx, right-click MHGU > Manage Title Updates > 1.4.0, then
                       right-click > Extract Data > ExeFS into this folder
  dump/gu_romfs/       MHGU v1.4 RomFS: right-click > Extract Data > RomFS (12 GB), update 1.4.0 still selected
  dump/extdata_4u/     optional, 4U DLC quests: your 3DS extdata (tools/extdata4u.py)
Every other dump/ file a build needs is either made here or extracted by the tool that needs it.
"""
import json, os, pickle, shutil, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths, nso  # noqa: E402
from steps import VENV_PY  # noqa: E402   (.venv/bin/python, Windows: .venv\Scripts\python.exe)

D = paths.DUMP
ROOT = paths.ROOT
WEAPON_PREFIXES = ('axe', 'bow', 'gaxe', 'gun', 'ham', 'hbg', 'hue', 'lan', 'lbg', 'one', 'rod', 'sou', 'swo', 'two', 'w')
GU_STAGE_UNPACKED = [('a%02d' % i, 'arc/stage/m26d/a%02d.arc' % i) for i in range(4)] + [
    ('m26d', 'arc/stage/m26d/m26d.arc'), ('m26', 'loc/arc/stage/map_com/m26.arc'), ('m18_a00', 'arc/stage/m18d/a00.arc'),
    ('m18_a01', 'arc/stage/m18d/a01.arc'), ('m18_m18d', 'arc/stage/m18d/m18d.arc'),
    ('m18_map_com', 'loc/arc/stage/map_com/m18.arc')]
M19_ARCS = ('m19',) + tuple('m19a%02d' % a for a in range(4))      # Battlequarters (4U stage arcs)


def run(*a, **kw):
    subprocess.run([str(x) for x in a], check=True, **kw)


def tool(name, *a, py=sys.executable):
    run(py, '-B', os.path.join(HERE, name), *a)


def objdump(elf, out, *flags, cwd):
    with open(out, 'w') as f:
        run('llvm-objdump', '-d', '--no-show-raw-insn', *flags, elf, stdout=f, cwd=cwd)


def s_4u_exefs():
    out = os.path.join(D, 'exefs_v11')
    tool('ctr.py', 'exefs', paths.UPDATE_4U, out)
    shutil.copyfile(os.path.join(out, 'code.bin'), os.path.join(out, 'mem.bin'))   # code.bin is already flat (0x100000)


def s_4u_romfs():
    tool('ctr.py', 'x', paths.ROM_4U, '.', os.path.join(D, 'romfs'))


def s_4u_asm():
    tool('mkelf3ds.py', os.path.join(D, 'exefs_v11'), os.path.join(D, 'mh4u_v11.elf'))
    objdump('dump/mh4u_v11.elf', os.path.join(D, 'mh4u.asm'), '--triple=armv6k-none-eabi', '--mattr=+vfp2', cwd=ROOT)


def s_4u_m19():
    """4U Battlequarters arcs -> dump/m19_unpacked/<arc>/<path>.<type hash> (+ _order.txt), the tools/arcpack.py
    layout read by stage4u2gu, snd_area and efl4u2gu (m05 / m08 are unpacked by the tools that need them)"""
    for a in M19_ARCS:
        unpack(os.path.join(D, 'romfs', 'loc', 'data', a + '.arc'), os.path.join(D, 'm19_unpacked', a))


def unpack(arc, out):
    """arc -> out/<path>.<type hash> + out/_order.txt (tools/arcpack.py unpack layout)"""
    import arcpack
    ver, ents = arcpack.read(open(arc, 'rb').read())
    order = []
    for path, th, data in ents:
        rel = path.replace('\\', '/') + '.%08x' % th
        os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
        open(os.path.join(out, rel), 'wb').write(data)
        order.append(rel)
    open(os.path.join(out, '_order.txt'), 'w').write(''.join(r + '\n' for r in order))


def s_gu_stage():
    """dump/gu_stage/: the GU stage files listed in tools/gu_stage_files.txt (Fortress m26 = the template of the
    ported arenas, m18 ...) and GU_STAGE_UNPACKED of them unpacked into dump/gu_stage/unpacked/"""
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    r, g = RomFS(paths.GU_ROMFS), os.path.join(D, 'gu_stage')
    for p in open(os.path.join(HERE, 'gu_stage_files.txt')).read().split('\n'):
        if not p or p.startswith('#'): continue
        os.makedirs(os.path.dirname(os.path.join(g, p)), exist_ok=True)
        open(os.path.join(g, p), 'wb').write(r.read('/' + p))
    for d, arc in GU_STAGE_UNPACKED:
        unpack(os.path.join(g, 'nativeNX', arc), os.path.join(g, 'unpacked', d))


def s_gear():
    g = os.path.join(D, 'gear_src')
    tool('ctr.py', 'x', paths.ROM_4U, r'^/data/pl_[mf]_(arm|body|helm|leg|wst)\d+\.arc$',
         os.path.join(g, 'armor', '4u'))
    tool('ctr.py', 'x', paths.ROM_4U, r'^/data/pl_(%s)\d+\.arc$' % '|'.join(WEAPON_PREFIXES), os.path.join(g, 'weapons', '4u'))
    for d in ('armor', 'weapons'): os.makedirs(os.path.join(g, d, 'out'), exist_ok=True)
    tool('armor4u2gu.py', 'index', os.path.join(g, 'armor', '4u'), os.path.join(g, 'armor', 'out', 'mrl_index.pkl'))
    tool('weapon4u2gu.py', 'index', os.path.join(g, 'weapons', '4u', 'data'),
         os.path.join(g, 'weapons', 'out', 'wpn_mrl_index.pkl'))


def gu_main_nso():
    for d in (paths.GU_EXEFS, os.path.join(paths.GU_EXEFS, 'exefs')):
        if os.path.isfile(os.path.join(d, 'main')): return os.path.join(d, 'main')
    sys.exit('no MHGU ExeFS in %s: Ryujinx, right-click MHGU > Extract Data > ExeFS' % paths.GU_EXEFS)


def s_gu_code():
    """GU main (NSO) -> mem.bin (flat: text|ro|data at their memory offsets), main32.elf (ARM32 ELF of it, as
    MHGU_Editor's mkelf32.py), main.asm (its disassembly, read by tools/gulib/asm.py)"""
    img, segs, _ = nso.flat(open(gu_main_nso(), 'rb').read())
    out = paths.GU_CODE
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'mem.bin'), 'wb').write(img)
    names = ('.text', '.rodata', '.data')
    shstr = b'\0' + b'\0'.join(n.encode() for n in names) + b'\0.shstrtab\0'
    DATA = 0x1000
    shoff = (DATA + len(img) + len(shstr) + 7) & ~7
    elf = bytearray(shoff + 40 * 5)
    elf[DATA:DATA + len(img)] = img
    elf[DATA + len(img):DATA + len(img) + len(shstr)] = shstr
    elf[:52] = b'\x7fELF\x01\x01\x01' + b'\0' * 9 + struct.pack('<HHIIIIIHHHHHH', 2, 40, 1, 0, 52, shoff, 0x05000000,
                                                                  52, 32, 1, 40, 5, 4)
    elf[52:84] = struct.pack('<8I', 1, DATA, 0, 0, len(img), len(img), 7, 0x1000)
    sh = [b'\0' * 40]; ni = 1
    for n, (mo, sz, _) in zip(names, segs):
        sh.append(struct.pack('<10I', ni, 1, {'.text': 6, '.rodata': 2, '.data': 3}[n], mo, DATA + mo, sz, 0, 0, 4, 0))
        ni += len(n) + 1
    sh.append(struct.pack('<10I', ni, 3, 0, 0, DATA + len(img), len(shstr), 0, 0, 4, 0))
    elf[shoff:shoff + 200] = b''.join(sh)
    open(os.path.join(out, 'main32.elf'), 'wb').write(elf)
    objdump('main32.elf', os.path.join(out, 'main.asm'), '--triple=armv7', cwd=out)


def s_gu_reloc():
    """gu_main/img_reloc.pkl (image, {stub address: imported symbol}) for tools/gulib/vt.py and asm.starts(): mem.bin
    loaded at 0x10000000 (bss included) with the dynamic relocations applied (R_ARM_RELATIVE, ABS32, GLOB_DAT,
    JUMP_SLOT); an imported symbol points at a stub address from 0x0e000000 up, 8 bytes apart"""
    m = open(paths.GU_MAIN, 'rb').read()
    B, END, STUB = 0x10000000, 0x2147000, 0x0E000000   # END: bss end 0x2146788, page-rounded
    u32 = lambda b, a: struct.unpack_from('<I', b, a)[0]
    mod0 = u32(m, 4)
    dyn, tags = mod0 + struct.unpack_from('<i', m, mod0 + 4)[0], {}
    while u32(m, dyn): tags[u32(m, dyn)] = u32(m, dyn + 4); dyn += 8
    img, stubs, by_name = bytearray(END), {}, {}
    img[:len(m)] = m

    def sym(i):
        n, v, _, _, _, shn = struct.unpack_from('<IIIBBH', m, tags[6] + 16 * i)
        return m[tags[5] + n:m.index(b'\0', tags[5] + n)].decode(), v, shn
    for tab, size in ((tags[17], tags[18]), (tags[23], tags[2])):   # DT_REL / DT_RELSZ, DT_JMPREL / DT_PLTRELSZ
        for i in range(0, size, 8):
            off, info = struct.unpack_from('<II', m, tab + i)
            t = info & 0xFF
            if t == 23:   # R_ARM_RELATIVE: base + the addend in place
                struct.pack_into('<I', img, off, (u32(img, off) + B) & 0xFFFFFFFF)
            elif t in (2, 21, 22):   # R_ARM_ABS32 (addend in place), GLOB_DAT, JUMP_SLOT
                name, v, shn = sym(info >> 8)
                if shn: tgt = B + v
                else:
                    if name not in by_name: by_name[name] = STUB + 8 * len(stubs); stubs[by_name[name]] = name
                    tgt = by_name[name]
                struct.pack_into('<I', img, off, ((u32(img, off) if t == 2 else 0) + tgt) & 0xFFFFFFFF)
    pickle.dump((bytes(img), stubs), open(os.path.join(paths.GU_CODE, 'img_reloc.pkl'), 'wb'))


def s_gu_plt():
    """dump/gu_plt.json {PLT stub address: imported symbol} for tools/guemu.py: each ARM PLT stub (add ip, pc / add
    ip, ip / ldr pc, [ip, #n]!) jumps through a GOT slot whose R_ARM_JUMP_SLOT relocation names the symbol"""
    m = open(paths.GU_MAIN, 'rb').read()
    u32 = lambda a: struct.unpack_from('<I', m, a)[0]
    mod0 = u32(4)
    dyn, tags = mod0 + struct.unpack_from('<i', m, mod0 + 4)[0], {}
    while u32(dyn): tags[u32(dyn)] = u32(dyn + 4); dyn += 8
    sym, strt, rel, relsz = tags[6], tags[5], tags[23], tags[2]
    name = lambda i: m[strt + u32(sym + 16 * i):m.index(b'\0', strt + u32(sym + 16 * i))].decode()
    got = {u32(r): name(u32(r + 4) >> 8) for r in range(rel, rel + relsz, 8) if u32(r + 4) & 0xFF == 22}
    plt = {}
    for a in range(0, len(m) - 12, 4):
        w0, w1, w2 = u32(a), u32(a + 4), u32(a + 8)
        if w0 & 0xFFFFFF00 == 0xE28FC600 and w1 & 0xFFFFFF00 == 0xE28CCA00 and w2 & 0xFFFFF000 == 0xE5BCF000:
            slot = a + 8 + ((w0 & 0xFF) << 20) + ((w1 & 0xFF) << 12) + (w2 & 0xFFF)
            if slot in got: plt['%#x' % a] = got[slot]
    json.dump(plt, open(os.path.join(D, 'gu_plt.json'), 'w'))


def s_gu_pcrefs():
    sys.path.insert(0, paths.GU_PY)
    import gu
    pickle.dump(gu.all_pcrefs(), open(os.path.join(D, 'gu_pcrefs.pkl'), 'wb'))


def s_gu_shader():
    sys.path.insert(0, paths.GU_PY)
    from romfs import RomFS
    os.makedirs(os.path.join(D, 'gu'), exist_ok=True)
    open(os.path.join(D, 'gu', 'AppShaderPackage.mfx'), 'wb').write(
        RomFS(paths.GU_ROMFS).read('/nativeNX/system/app_shader/AppShaderPackage.mfx'))


def s_dt_em089():
    """Gogmazios' dtbase / dttune on GU Kushala em024_00 (tools/dt_convert.py: GU loaders emulated with unicorn)"""
    tool('dt_convert.py', 'build', 'em089', 'em024_00', os.path.join(D, 'converted', 'em089'),
         py=VENV_PY if os.path.exists(VENV_PY) else sys.executable)


# (name, [(output, SHA-256 or None, what)], function): tools/doctor.py checks these outputs too
STEPS = [
    ('4u_exefs', [('dump/exefs_v11/code.bin', '4ffd2ebb8c7d212a8a33cd222ccc85e8e337db9ee1ea1467189899e485017722',
                   'MH4U v1.1 (EUR) code'), ('dump/exefs_v11/mem.bin', None, 'MH4U v1.1 code, flat')], s_4u_exefs),
    ('4u_romfs', [('dump/romfs/data/em_data.arc', None, 'MH4U RomFS')], s_4u_romfs),
    ('4u_asm', [('dump/mh4u_v11.elf', None, 'MH4U code ELF'), ('dump/mh4u.asm', None, 'MH4U disassembly')], s_4u_asm),
    ('4u_m19', [('dump/m19_unpacked/%s/_order.txt' % a, None, '4U stage arc %s, unpacked' % a) for a in M19_ARCS],
     s_4u_m19),
    ('gu_code', [('dump/gu_main/mem.bin', '24c208c395c65727b21b5fa91af8381396e70cf421b0fcfee0345d8743298110',
                  'MHGU v1.4 main, flat'), ('dump/gu_main/main32.elf', None, 'MHGU main ELF'),
                 ('dump/gu_main/main.asm', None, 'MHGU main disassembly')], s_gu_code),
    ('gu_reloc', [('dump/gu_main/img_reloc.pkl', None, 'MHGU main, relocated')], s_gu_reloc),
    ('gu_plt', [('dump/gu_plt.json', None, 'MHGU PLT symbols')], s_gu_plt),
    ('gu_pcrefs', [('dump/gu_pcrefs.pkl', None, 'MHGU pc-relative references')], s_gu_pcrefs),
    ('gu_shader', [('dump/gu/AppShaderPackage.mfx', None, 'MHGU shader package')], s_gu_shader),
    ('gu_stage', [('dump/gu_stage/unpacked/%s/_order.txt' % d, None, 'GU stage arc %s, unpacked' % d)
                  for d, _ in GU_STAGE_UNPACKED], s_gu_stage),
    ('gear', [('dump/gear_src/armor/out/mrl_index.pkl', None, 'armor material index'),
              ('dump/gear_src/weapons/out/wpn_mrl_index.pkl', None, 'weapon material index')], s_gear),
    ('dt_em089', [('dump/converted/em089/dtbase.bin', None, 'Gogmazios dtbase'),
                  ('dump/converted/em089/dttune.bin', None, 'Gogmazios dttune')], s_dt_em089),
]


def hooks():
    """switch on tools/hooks/pre-commit (refuses game data and keys: tools/check_repo.py), once per clone"""
    git = lambda *a: subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True)
    if git('rev-parse', '--git-dir').returncode == 0 and git('config', 'core.hooksPath').stdout.strip() != 'tools/hooks':
        git('config', 'core.hooksPath', 'tools/hooks'); print('pre-commit hook on (tools/hooks/pre-commit)')


def main():
    hooks()
    force = '--force' in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith('--')]
    bad = [w for w in want if w not in [s[0] for s in STEPS]]
    if bad: sys.exit('unknown step(s) %s; steps: %s' % (bad, ' '.join(s[0] for s in STEPS)))
    for name, outs, fn in STEPS:
        if want and name not in want: continue
        if not force and all(os.path.exists(os.path.join(ROOT, p)) for p, _, _ in outs):
            print('[%s] up to date' % name); continue
        print('[%s] ...' % name, flush=True)
        fn()
    print('done: now run python3 tools/doctor.py')


if __name__ == '__main__':
    main()
