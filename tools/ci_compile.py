"""ci_compile.py : compile every C file of the module (core + each monster's module/) the way module/build.py does,
without GU's files: no hooks, tables or link (those need dump/gu_main/mem.bin), and the tables generated from GU's
RomFS (board places, the save's quest list) left empty. For CI and quick checks; exit 1 on the first compile error.

  python3 tools/ci_compile.py
"""
import glob, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'module'))
import build  # noqa: E402  (module/build.py: flags, sources, generated C)

with tempfile.TemporaryDirectory() as out:
    errs = build.alloc.check()
    if errs: sys.exit('allocations.toml:\n  ' + '\n  '.join(errs))
    open(os.path.join(out, 'alloc.h'), 'w').write(build.alloc.header())
    open(os.path.join(out, 'port_monsters.c'), 'w').write(build.monsters_c(stub=True))
    open(os.path.join(out, 'modsave_quests.h'), 'w').write(build.modsave_quests_h(stub=True))
    open(os.path.join(out, 'gear_hooks.inc'), 'w').write(
        ''.join('GEAR_HOOK(%s)\n' % l.split()[0] for l in open(build._GEAR_HOOKS) if l.strip()))
    mods = [os.path.join(build.paths.monster(p), 'module') for p in build.alloc.packages()]
    incs = ['-I', out, '-I', build.HERE] + [a for d in mods for a in ('-I', d)]
    srcs = sorted(glob.glob(os.path.join(build.HERE, '*.c'))) + [os.path.join(out, 'port_monsters.c')]
    for d in mods: srcs += sorted(glob.glob(os.path.join(d, '*.c')))
    for path in srcs:
        r = subprocess.run(['clang', *build.CFLAGS, *build.EXTRA_DEFINES, *incs, '-c', path, '-o', os.devnull],
                           capture_output=True, text=True)
        if r.returncode: sys.exit('%s\n%s' % (os.path.relpath(path, ROOT), r.stderr))
    print('%d C files compile' % len(srcs))
