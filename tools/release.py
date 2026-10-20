"""release.py : build, check and package an MH4U Port release on the machine that holds the game dumps (a release can
never be built in hosted CI: the converters read ~15 GB of 4U / GU data and the module build reads GU's main).

  release.py build           every monster's build.sh (all steps), then the module, both without test switches
  release.py check           release checks on the current outputs (exit 1 on any failure)
  release.py package [DIR]   check, then zips + manifest.json into DIR (default dump/release/v<core version>)
  release.py all [DIR]       build + package
  release.py publish DIR --repo OWNER/NAME [--yes]
                             create the GitHub release v<core version> with DIR's files (gh CLI); asks first unless
                             --yes. CI (.github/workflows/installer.yml) then attaches the installer apps to it.

Packages (notes/installer.md): core-<v>.zip = exefs/{subsdk1, <build id>.ips} + romfs/nativeNX/mh4uport/<every monster>.bin
(always installed together: gear IDs depend on all of them); <monster>-<v>.zip = that monster's romfs/ (its assets).
Zip paths are relative to the mod folder ('<mods>/contents/<title>/MH4U Port/' for Ryujinx, '<load>/<TITLE>/MH4U Port/'
for the yuzu family); the installer maps them for Atmosphère. manifest.json: format 1, title, mod name, core and
monsters {name, title, version, requires_core, file, sha256, size} and the warnings the installer shows.
"""
import hashlib, json, os, re, struct, subprocess, sys, tomllib, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths, portdata

ROOT = paths.ROOT
TITLE_ID = '0100770008DD8000'
MOD_NAME = 'MH4U Port'
MODULE_OUT = os.path.join(ROOT, 'module', 'out')
WARNINGS = [
    "A monster's armor and weapon models ship with that monster. Before uninstalling a monster, unequip its armor "
    "and weapons.",
    "Online, a player wearing gear of a monster you did not install may crash your game or show nothing: install "
    "the monsters your group uses, in the same versions.",
]


def toml(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def vtuple(v):
    return tuple(int(x) for x in v.split('.'))


def core():
    return toml(os.path.join(ROOT, 'module', 'core.toml'))


def packages():
    return [dict(toml(os.path.join(paths.monster(m['name']), 'package.toml')), alloc=m) for m in alloc.monsters()]


def clean_env():
    env = dict(os.environ)
    for k in ('GOG_DEFINES', 'GOG_MOD_ROOT', 'PORT_ASSETS'):
        env.pop(k, None)
    return env


def build():
    for p in packages():
        print('== build %s' % p['name'], flush=True)
        subprocess.run(['bash', os.path.join(paths.monster(p['name']), 'build.sh')], check=True, env=clean_env())
    print('== build module', flush=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'module', 'build.py')], check=True, env=clean_env())


def build_id():
    ips = [f for f in os.listdir(MODULE_OUT) if f.endswith('.ips')]
    assert len(ips) == 1, ips
    return ips[0]


def check():
    """[problem] of the current outputs (empty = releasable)"""
    bad = ['allocations.toml: ' + e for e in alloc.check()]
    c = core()
    defines = open(os.path.join(MODULE_OUT, 'defines.txt')).read().split() \
        if os.path.exists(os.path.join(MODULE_OUT, 'defines.txt')) else ['(module not built)']
    if defines:
        bad.append('module built with %s: rebuild without test switches (release.py build)' % ' '.join(defines))
    owner = {}
    for p in packages():
        name = p['name']
        if vtuple(p['requires_core']) > vtuple(c['version']):
            bad.append('%s requires core %s, core is %s' % (name, p['requires_core'], c['version']))
        data = os.path.join(paths.gen(name), name + '.bin')
        if not os.path.exists(data):
            bad.append('%s: no data file %s' % (name, data)); continue
        hdr, _ = portdata.read(data)
        if hdr['version'] != portdata.version(name)[1]:
            bad.append('%s: data file version %x != package.toml %s' % (name, hdr['version'], p['version']))
        if os.path.getmtime(data) < os.path.getmtime(os.path.join(paths.monster(name), 'package.toml')):
            bad.append('%s: data file older than package.toml (repack)' % name)
        rf = paths.romfs(name)
        files = [os.path.relpath(os.path.join(d, f), rf) for d, _, fs in os.walk(rf) for f in fs]
        if not files:
            bad.append('%s: empty romfs %s' % (name, rf))
        for rel in files:
            if rel in owner:
                bad.append('RomFS path %s shipped by %s and %s' % (rel, owner[rel], name))
            owner[rel] = name
            m = re.search(r'questData_(\d{7})\.ext$', rel)
            if m:                    # boss record +0x69 = HP row: test builds use rows 0..9 (5 % HP)
                qd = open(os.path.join(rf, rel), 'rb').read()
                qid = int(m.group(1))
                if qid not in p['alloc'].get('quests', []):
                    bad.append('%s: quest %d is not in its allocations' % (name, qid))
                if qd[0x69] < 10:
                    bad.append('%s: quest %d has HP row %d (a test build?)' % (name, qid, qd[0x69]))
    return bad


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def write_zip(path, members):
    """members: [(zip path, source file)] -> deterministic zip (sorted, fixed timestamps)"""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, src in sorted(members):
            zi = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(src, 'rb') as f:
                z.writestr(zi, f.read(), compresslevel=9)


def package(out):
    bad = check()
    if bad:
        sys.exit('not releasable:\n  ' + '\n  '.join(bad))
    os.makedirs(out, exist_ok=True)
    c = core()
    pk = packages()
    members = [('exefs/subsdk1', os.path.join(MODULE_OUT, 'subsdk1')),
               ('exefs/' + build_id(), os.path.join(MODULE_OUT, build_id()))]
    members += [('romfs/nativeNX/mh4uport/%s.bin' % p['name'], os.path.join(paths.gen(p['name']), p['name'] + '.bin'))
                for p in pk]
    entries = []
    core_zip = 'core-%s.zip' % c['version']
    write_zip(os.path.join(out, core_zip), members)
    for p in pk:
        rf = paths.romfs(p['name'])
        mem = [('romfs/' + os.path.relpath(os.path.join(d, f), rf).replace(os.sep, '/'), os.path.join(d, f))
               for d, _, fs in os.walk(rf) for f in fs]
        z = '%s-%s.zip' % (p['name'], p['version'])
        write_zip(os.path.join(out, z), mem)
        entries.append(dict(name=p['name'], title=p['title'], version=p['version'], requires_core=p['requires_core'],
                            file=z, sha256=sha256(os.path.join(out, z)), size=os.path.getsize(os.path.join(out, z))))
    manifest = dict(format=1, title_id=TITLE_ID, mod_name=MOD_NAME,
                    core=dict(version=c['version'], file=core_zip, sha256=sha256(os.path.join(out, core_zip)),
                              size=os.path.getsize(os.path.join(out, core_zip))),
                    monsters=entries, warnings=WARNINGS)
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    for f in sorted(os.listdir(out)):
        print('%10d %s' % (os.path.getsize(os.path.join(out, f)), os.path.join(out, f)))
    return out


def publish(out, repo, yes):
    c = core()
    tag = 'v%s' % c['version']
    files = [os.path.join(out, f) for f in sorted(os.listdir(out))]
    assert any(f.endswith('manifest.json') for f in files), 'no manifest.json in %s' % out
    print('release %s on %s with %d files:' % (tag, repo, len(files)))
    for f in files: print('  ', os.path.basename(f))
    if not yes and input('publish? [y/N] ').strip().lower() != 'y':
        sys.exit('not published')
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--title', 'MH4U Port %s' % tag,
                    '--notes', 'MH4U Port %s: install with the MH4U Port installer (attached by CI).' % tag] + files,
                   check=True)


def main():
    a = sys.argv[1:]
    default_out = os.path.join(ROOT, 'dump', 'release', 'v' + core()['version'])
    if not a or a[0] not in ('build', 'check', 'package', 'all', 'publish'):
        sys.exit(__doc__)
    if a[0] in ('build', 'all'):
        build()
    if a[0] == 'check':
        bad = check()
        print('releasable' if not bad else 'not releasable:\n  ' + '\n  '.join(bad))
        sys.exit(1 if bad else 0)
    if a[0] in ('package', 'all'):
        package(a[1] if len(a) > 1 else default_out)
    if a[0] == 'publish':
        if '--repo' not in a:
            sys.exit('publish needs --repo OWNER/NAME')
        publish(a[1] if len(a) > 1 and not a[1].startswith('--') else default_out, a[a.index('--repo') + 1],
                '--yes' in a)


if __name__ == '__main__':
    main()
