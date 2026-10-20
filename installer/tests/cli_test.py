"""cli_test.py INSTALLER : end-to-end test of the installer's command line on a fake release (dummy files, no game data;
the layout tools/release.py writes), for CI on Linux and Windows. Exit 1 on the first failure.

Checks: install of one monster (core + its files + the install record), install all, a monster dropped (its files
removed, empty folders pruned), uninstall everything, a damaged package refused (sha256), and the Atmosphère layout
(contents/<title>/{exefs,romfs} + exefs_patches/<mod>/<build id>.ips).
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile

TITLE = '0100770008DD8000'
MOD = 'MH4U Port'


def make_release(d):
    os.makedirs(d)
    def pkg(name, files, version='1.0.0'):
        z = '%s-%s.zip' % (name, version)
        with zipfile.ZipFile(os.path.join(d, z), 'w', zipfile.ZIP_DEFLATED) as f:
            for path, data in files.items():
                f.writestr(path, data)
        raw = open(os.path.join(d, z), 'rb').read()
        return dict(name=name, title=name.title(), version=version, requires_core='1.0.0', file=z,
                    sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
    core = pkg('core', {'exefs/subsdk1': b'module', 'exefs/ABCDEF.ips': b'IPS32EEOF',
                        'romfs/nativeNX/mh4uport/a.bin': b'A', 'romfs/nativeNX/mh4uport/b.bin': b'B'})
    a = pkg('a', {'romfs/nativeNX/arc/enemy/a.arc': b'a' * 1000, 'romfs/nativeNX/loc/quest/qa.ext': b'qa'})
    b = pkg('b', {'romfs/nativeNX/arc/enemy/b.arc': b'b' * 1000, 'romfs/nativeNX/arc/weapon/w01/104.arc': b'w'})
    json.dump(dict(format=1, title_id=TITLE, mod_name=MOD, core=core, monsters=[a, b], warnings=['test warning']),
              open(os.path.join(d, 'manifest.json'), 'w'))


def files(root):
    return sorted(os.path.relpath(os.path.join(p, f), root).replace(os.sep, '/')
                  for p, _, fs in os.walk(root) for f in fs)


def main():
    exe = os.path.abspath(sys.argv[1])
    tmp = tempfile.mkdtemp()
    rel = os.path.join(tmp, 'release')
    make_release(rel)
    env = dict(os.environ, XDG_CACHE_HOME=os.path.join(tmp, 'cache'), LOCALAPPDATA=os.path.join(tmp, 'cache'))

    def run(*a, ok=True):
        r = subprocess.run([exe, *a, '--source', rel], env=env, capture_output=True, text=True, timeout=120)
        if (r.returncode == 0) != ok:
            sys.exit('FAIL %s: exit %d\n%s%s' % (' '.join(a), r.returncode, r.stdout, r.stderr))
        return r

    def expect(root, want, what):
        got = files(root) if os.path.isdir(root) else []
        if got != sorted(want):
            sys.exit('FAIL %s:\n  got  %s\n  want %s' % (what, got, sorted(want)))
        print('ok', what)

    mods = os.path.join(tmp, 'ryujinx', 'mods', 'contents', TITLE.lower())
    os.makedirs(mods)
    core = ['%s/exefs/subsdk1' % MOD, '%s/exefs/ABCDEF.ips' % MOD, '%s/romfs/nativeNX/mh4uport/a.bin' % MOD,
            '%s/romfs/nativeNX/mh4uport/b.bin' % MOD, '%s/mh4uport-install.json' % MOD]
    fa = ['%s/romfs/nativeNX/arc/enemy/a.arc' % MOD, '%s/romfs/nativeNX/loc/quest/qa.ext' % MOD]
    fb = ['%s/romfs/nativeNX/arc/enemy/b.arc' % MOD, '%s/romfs/nativeNX/arc/weapon/w01/104.arc' % MOD]
    run('--target', mods, '--install', 'a')
    expect(mods, core + fa, 'install one monster')
    rec = json.load(open(os.path.join(mods, MOD, 'mh4uport-install.json')))
    assert rec['core']['version'] == '1.0.0' and list(rec['monsters']) == ['a'], rec
    run('--target', mods, '--install', 'all')
    expect(mods, core + fa + fb, 'install all')
    run('--target', mods, '--install', 'b')
    expect(mods, core + fb, 'drop a monster')
    if os.path.isdir(os.path.join(mods, MOD, 'romfs', 'nativeNX', 'loc')):
        sys.exit('FAIL drop a monster: empty folders left')
    run('--target', mods, '--uninstall-all')
    expect(mods, [], 'uninstall everything')

    sd = os.path.join(tmp, 'sd')
    os.makedirs(os.path.join(sd, 'atmosphere'))
    run('--target', sd, '--install', 'all')
    c = 'atmosphere/contents/%s/' % TITLE
    expect(sd, [c + 'exefs/subsdk1', 'atmosphere/exefs_patches/%s/ABCDEF.ips' % MOD, c + 'romfs/nativeNX/mh4uport/a.bin',
                c + 'romfs/nativeNX/mh4uport/b.bin', c + 'mh4uport-install.json', c + 'romfs/nativeNX/arc/enemy/a.arc',
                c + 'romfs/nativeNX/loc/quest/qa.ext', c + 'romfs/nativeNX/arc/enemy/b.arc',
                c + 'romfs/nativeNX/arc/weapon/w01/104.arc'], 'Atmosphere layout')

    m = json.load(open(os.path.join(rel, 'manifest.json')))      # a damaged package must be refused
    m['monsters'][0]['sha256'] = '0' * 64
    json.dump(m, open(os.path.join(rel, 'manifest.json'), 'w'))
    shutil.rmtree(os.path.join(tmp, 'cache'), ignore_errors=True)
    other = os.path.join(tmp, 'other')
    os.makedirs(other)
    run('--target', other, '--install', 'a', ok=False)
    print('ok damaged package refused')
    shutil.rmtree(tmp, ignore_errors=True)
    print('all installer tests passed')


if __name__ == '__main__':
    main()
