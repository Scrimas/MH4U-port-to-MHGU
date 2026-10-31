"""doctor.py : can this machine build the port? Checks the Python packages, the toolchain, your game inputs (by SHA-256 of
what the tools read: the right game, region and version) and the files tools/setup.py makes. Prints each failure with
the command that fixes it; exit 1 if anything required fails. Run it first, and again after tools/setup.py.

  python3 tools/doctor.py [--quick]        --quick: skip the SHA-256 checks
"""
import ctypes.util, glob, hashlib, importlib, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

VENV = 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, then activate .venv'
SETUP = 'python3 tools/setup.py'
# (path, SHA-256 or None = must exist, what it is, the fix). The hashes identify versions; they are not game data.
INPUTS = [
    ('dump/base/*.3ds', None, 'MH4U (EUR) ROM, decrypted', 'dump your cartridge / eShop copy with GodMode9 into dump/base/'),
    ('dump/update/*.cia', None, 'MH4U v1.1 update (EUR), decrypted', 'dump it with GodMode9 into dump/update/'),
    (paths.GU_EXEFS + '/main', None, 'MHGU v1.4 ExeFS',
     'Ryujinx: right-click MHGU > Extract Data > ExeFS, into dump/gu_exefs (update 1.4 installed)'),
    (paths.GU_ROMFS, None, 'MHGU v1.4 RomFS', 'Ryujinx: right-click MHGU > Extract Data > RomFS, into dump/gu_romfs'),
]
MADE = []      # (path, SHA-256 or None, what, fix): the outputs of tools/setup.py, filled from its STEPS below

failed = 0


def check(name, good, fix='', required=True):
    global failed
    print('%s %s' % ('ok  ' if good else 'FAIL' if required else 'warn', name))
    if not good:
        if fix: print('       -> ' + fix)
        failed += required


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def main():
    quick = '--quick' in sys.argv
    check('Python >= 3.11 (%s)' % sys.version.split()[0], sys.version_info >= (3, 11), 'install Python 3.11 or newer')
    for m in ('numpy', 'PIL', 'cryptography', 'unicorn'):
        try:
            importlib.import_module(m); good = True
        except ImportError:
            good = False
        check('python module ' + m, good, VENV)
    for b, why in (('clang', 'module/build.py'), ('ld.lld', 'module/build.py'), ('llvm-objdump', 'tools/setup.py gu'),
                   ('ffmpeg', 'music, tools/snd_bgm.py')):
        check('%s (%s)' % (b, why), shutil.which(b) is not None, 'install it (Arch: clang lld llvm ffmpeg)')
    if shutil.which('ffmpeg'):
        v = subprocess.run(['ffmpeg', '-hide_banner', '-version'], capture_output=True, text=True).stdout
        check('ffmpeg built with libsoxr (resampler of tools/snd_bgm.py)', 'enable-libsoxr' in v, 'use a full ffmpeg build')
    check('libopus (tools/snd_bgm.py encodes the music)', ctypes.util.find_library('opus') is not None, 'install opus')

    import setup
    made = [(os.path.join(paths.ROOT, p), h, what, '%s %s' % (SETUP, step)) for step, outs, _ in setup.STEPS
            for p, h, what in outs]
    for p, h, what, fix in [(os.path.join(paths.ROOT, p), h, w, f) for p, h, w, f in INPUTS] + made:
        hits = sorted(glob.glob(p))
        good = bool(hits)
        if good and h and not quick:
            good = sha(hits[0]) == h
            what += '' if good else ' (SHA-256 differs: another version or region?)'
        check('%s: %s' % (what, os.path.relpath(p, paths.ROOT)), good, fix)
    print('\n%s' % ('all good' if not failed else '%d problem(s)' % failed))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
