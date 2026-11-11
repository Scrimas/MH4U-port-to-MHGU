"""doctor.py : can this machine build the port? Checks the Python packages, the toolchain, your game inputs (by SHA-256 of
what the tools read: the right game, region and version) and the files tools/setup.py makes. Prints each failure with
the command that fixes it; exit 1 if anything required fails. Run it first, and again after tools/setup.py.

  python3 tools/doctor.py [--quick]        --quick: skip the SHA-256 checks
"""
import glob, hashlib, importlib, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

WINDOWS = os.name == 'nt'
if WINDOWS:
    VENV = r'py -m venv .venv && .venv\Scripts\pip install -r requirements.txt, then .venv\Scripts\activate'
    SETUP = 'python tools/setup.py'
    TOOLS_FIX = (r'MSYS2 UCRT64: pacman -S mingw-w64-ucrt-x86_64-{clang,lld,llvm-tools,ffmpeg,opus}, and '
                 r'C:\msys64\ucrt64\bin on your PATH (CONTRIBUTING.md)')
else:
    VENV = 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, then activate .venv'
    SETUP = 'python3 tools/setup.py'
    TOOLS_FIX = 'install it (Arch: clang lld llvm ffmpeg opus; Debian / Ubuntu: clang lld llvm ffmpeg libopus0)'
# (path, SHA-256 or None = must exist, what it is, the fix). The hashes identify versions; they are not game data.
INPUTS = [
    ('dump/base/*.3ds', None, 'MH4U (EUR) ROM, decrypted', 'dump your cartridge / eShop copy with GodMode9 into dump/base/'),
    ('dump/update/*.cia', None, 'MH4U v1.1 update (EUR), decrypted', 'dump it with GodMode9 into dump/update/'),
    (paths.GU_EXEFS + '/main', 'b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef', 'MHGU v1.4 ExeFS',
     'Ryujinx: right-click MHGU > Manage Title Updates > 1.4.0, then Extract Data > ExeFS into dump/gu_exefs'),
    (paths.GU_ROMFS + '/nativeNX/loc/arc/quest/gq.arc', '5d28425a975459e62630d32685d5e5bc84d4798180e282d3a5110d1a5bafe95a',
     'MHGU v1.4 RomFS', 'Ryujinx: Manage Title Updates > 1.4.0, then Extract Data > RomFS into dump/gu_romfs'),
]
MADE = []      # (path, SHA-256 or None, what, fix): the outputs of tools/setup.py, filled from its STEPS below
# Optional (warn only): what weapons/magnet_spike/tools/msbuild.py reads, MHF-Z files the maintainer extracted by hand
# (dump/mhf/SOURCES.txt). No setup step: the extraction needs MHF clients and local tools that are not in the repo.
MS_FIX = 'only for the Magnet Spike (MS_SLICE): see weapons/magnet_spike/notes/assets.md "Inputs"'
MS_INPUTS = [('dump/mhf/' + p, 'Magnet Spike: ' + w) for p, w in (
    ('motion/w13.aan', 'MHF w13 body motions'), ('motion/w13w.aan', 'MHF w13 weapon motions'),
    ('player/m_editpl.fskl', 'MHF player skeleton'), ('player/m_editpl.0.bin', 'MHF player model'),
    ('zz/mhfdat.dec.bin', 'MHF-Z mhfdat, decoded'), ('zz/mhfsdt.dec.bin', 'MHF-Z mhfsdt, decoded'),
    ('ui/mhf_90c_04.png', 'MHF-Z HUD art'),
    ('weapon/wk[0-9]*/0.fmod', 'MHF weapon models'))]

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
    if WINDOWS:
        check('Python in UTF-8 mode (setup.py, module/build.py; build.py steps set it themselves)', sys.flags.utf8_mode,
              'run `setx PYTHONUTF8 1` once, then open a new terminal', required=False)
    for b, why in (('clang', 'module/build.py'), ('ld.lld', 'module/build.py'), ('llvm-nm', 'module/build.py'),
                   ('llvm-objdump', 'tools/setup.py gu_code'), ('ffmpeg', 'music, tools/snd_bgm.py')):
        check('%s (%s)' % (b, why), shutil.which(b) is not None, TOOLS_FIX)
    if shutil.which('clang'):
        t = subprocess.run(['clang', '--print-targets'], capture_output=True, text=True).stdout
        check('clang can build for ARM (the module targets the Switch)', re.search(r'^\s+arm\s', t, re.M) is not None,
              'use an LLVM build with the ARM target (' + TOOLS_FIX + ')')
    if shutil.which('ffmpeg'):
        v = subprocess.run(['ffmpeg', '-hide_banner', '-version'], capture_output=True, text=True).stdout
        check('ffmpeg built with libsoxr (resampler of tools/snd_bgm.py)', 'enable-libsoxr' in v,
              'use a full ffmpeg build (' + TOOLS_FIX + ')')
    import snd_bgm
    check('libopus (tools/snd_bgm.py encodes the music)', snd_bgm.find_opus() is not None,
          TOOLS_FIX + '; or set OPUS_LIB to the library file')

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
    for p, what in MS_INPUTS:
        check('%s: %s' % (what, p), bool(glob.glob(os.path.join(paths.ROOT, p))), MS_FIX, required=False)
    print('\n%s' % ('all good' if not failed else '%d problem(s)' % failed))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
