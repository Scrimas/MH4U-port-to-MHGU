"""steps.py : the step runner of every monsters/<name>/build.py (Linux and Windows, no shell needed).

A package's build.py lists its steps in order, (name, comment, function); each function returns the commands of that
step, made with py() / armor() / weapon() below. The runner then works as the old build.sh did:

  python3 monsters/<name>/build.py [STEP ...]     default: every step, in order
  python3 monsters/<name>/build.py --list         the steps, one "name<TAB>comment" line each (install.sh reads it)

One line per step on stdout; the step's own output goes to $BUILD_LOGS/<step>.log (default dump/build_logs/<name>/).
A step stops at its first failing command; the next steps still run; the exit code is 1 when any step failed.

Every command runs from the repo root with this Python (the activated .venv) in UTF-8 mode (-X utf8: Windows would
otherwise read and write text files in its ANSI code page; a no-op on a UTF-8 Linux).
"""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.path.join(ROOT, 'dump')
GS = os.path.join(DUMP, 'gear_src')          # 4U armor / weapon arcs (tools/ctr.py x) + the MRL template indexes
VENV_PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe') if os.name == 'nt' else \
    os.path.join(ROOT, '.venv', 'bin', 'python')


def py(script, *args, flags=(), timeout=None, venv=False):
    """one Python command: script (repo-relative or absolute) + args; flags such as '-I' / '-B'; venv: the repo's
    .venv Python even when build.py runs under another one (the dt steps need unicorn, requirements.txt)"""
    exe = VENV_PY if venv and os.path.exists(VENV_PY) else sys.executable
    return [exe, '-X', 'utf8', *flags, script, *[str(a) for a in args]], timeout


def armor(romfs, series, *flags):
    """armor model arcs: 4U pl_{m,f}_<part><n>.arc -> romfs/nativeNX/arc/player/com/<s>/<n>/<part>.arc
    (flags: tools/armor4u2gu.py convert options, e.g. '--opaque-tint')"""
    for s in 'mf':
        for n in series:
            for p in ('helm', 'arm', 'wst', 'leg', 'body'):
                out = os.path.join(romfs, 'nativeNX', 'arc', 'player', 'com', s, str(n))
                os.makedirs(out, exist_ok=True)
                yield py('tools/armor4u2gu.py', 'convert', os.path.join(GS, 'armor', '4u', 'data', 'pl_%s_%s%s.arc' % (s, p, n)),
                         os.path.join(out, p + '.arc'), os.path.join(GS, 'armor', 'out', 'mrl_index.pkl'), *flags)


def weapon(romfs, cls, arc, model, *flags):
    """one weapon model arc: 4U pl_<arc>.arc -> romfs/nativeNX/arc/weapon/w<cls>/<model>.arc"""
    out = os.path.join(romfs, 'nativeNX', 'arc', 'weapon', 'w%02d' % cls)
    os.makedirs(out, exist_ok=True)
    return py('tools/weapon4u2gu.py', 'convert', cls, os.path.join(GS, 'weapons', '4u', 'data', 'pl_%s.arc' % arc),
              os.path.join(out, '%s.arc' % model), os.path.join(GS, 'weapons', 'out', 'wpn_mrl_index.pkl'), *flags)


def weapon_sound(romfs, cls, arc, model):
    """one weapon sound arc: 4U pl_<arc>.arc -> romfs/nativeNX/arc/weapon/w<cls>/snd/<model>.arc"""
    out = os.path.join(romfs, 'nativeNX', 'arc', 'weapon', 'w%02d' % cls, 'snd')
    os.makedirs(out, exist_ok=True)
    return py('tools/wsnd4u2gu.py', 'convert', cls, os.path.join(GS, 'weapons', '4u', 'data', 'pl_%s.arc' % arc),
              os.path.join(out, '%s.arc' % model))


def run_step(fn, log):
    with open(log, 'w', encoding='utf-8') as f:
        for argv, timeout in fn():
            f.write('$ %s\n' % ' '.join(argv)); f.flush()
            try:
                r = subprocess.run(argv, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                f.write('timed out after %ds\n' % timeout)
                return False
            if r.returncode:
                return False
    return True


def main(name, steps):
    """steps: [(name, comment, function returning the step's commands)], in build order"""
    by = {s: (c, fn) for s, c, fn in steps}
    args = sys.argv[1:]
    if args == ['--list']:
        for s, c, _ in steps: print('%s\t%s' % (s, c))
        return
    bad = [a for a in args if a not in by]
    if bad:
        sys.exit('unknown step(s) %s; steps: %s' % (' '.join(bad), ' '.join(s for s, _, _ in steps)))
    todo = args or [s for s, _, _ in steps]
    logs = os.environ.get('BUILD_LOGS') or os.path.join(DUMP, 'build_logs', name)
    os.makedirs(logs, exist_ok=True)
    fails = 0; t0 = time.time()
    for k, s in enumerate(todo, 1):
        t = time.time(); log = os.path.join(logs, s + '.log')
        try:
            good = run_step(by[s][1], log)
        except Exception as e:           # a step's own setup (paths, folders) failed
            with open(log, 'a', encoding='utf-8') as f: f.write('%s: %s\n' % (type(e).__name__, e))
            good = False
        fails += not good
        print('[%2d/%d] %-12s %s in %ds' % (k, len(todo), s, 'ok' if good else 'FAILED (see %s)' % log, time.time() - t),
              flush=True)
    print('done: %d step(s) failed, %ds' % (fails, time.time() - t0))
    sys.exit(1 if fails else 0)
