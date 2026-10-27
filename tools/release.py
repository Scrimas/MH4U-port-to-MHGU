"""release.py : build, check and package an MH4U Port release on the machine that holds the game dumps (a release can
never be built in hosted CI: the converters read ~15 GB of 4U / GU data and the module build reads GU's main).

  release.py build           every monster's build.sh (all steps), then the module, both without test switches
  release.py check           release checks on the current outputs (exit 1 on any failure)
  release.py package [DIR]   check, then the zips + NOTES.md into DIR (default dump/release/v<core version>)
  release.py all [DIR]       build + package
  release.py publish DIR --repo OWNER/NAME [--yes] [--draft]
                             create the GitHub release v<core version> with DIR's zips and NOTES.md as its text (gh
                             CLI); asks first unless --yes. No installer apps (user, 2026-10-21): users extract the zips.

Packages: core-<v>.zip = MH4U Port/exefs/{subsdk1, <build id>.ips} + MH4U Port/romfs/nativeNX/mh4uport/<every
monster>.bin (always installed together: gear IDs depend on all of them) + the icon atlases micon_sd/hd.tex; <monster>-<v>.zip = MH4U Port/romfs/... (that
monster's assets, optional). Every zip extracts into the game's mod directory ('<mods>/contents/<title>/' for Ryujinx,
'<load>/<TITLE>/' for the yuzu family) and they merge into the one 'MH4U Port' folder. NOTES.md (the release text):
what the mod is, What's new (notes/release-news.md, one section per core version: write it before packaging), the
monsters and their quests (read from the quest files), install / update / online play, files with sha256, warnings.
"""
import hashlib, os, re, struct, subprocess, sys, tomllib, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths, portdata, ui_icons

ROOT = paths.ROOT
TITLE_ID = '0100770008DD8000'
MOD_NAME = 'MH4U Port'
MODULE_OUT = os.path.join(ROOT, 'module', 'out')


def toml(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def vtuple(v):
    return tuple(int(x) for x in v.split('.'))


def core():
    return toml(os.path.join(ROOT, 'module', 'core.toml'))


def packages():
    """one dict per package: its package.toml + entries = its allocations.toml entries (one data file each) + alloc =
    the first entry"""
    out = []
    for p in alloc.packages():
        ents = [m for m in alloc.monsters() if alloc.package(m) == p]
        out.append(dict(toml(os.path.join(paths.monster(p), 'package.toml')), entries=ents, alloc=ents[0]))
    return out


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
        for e in (m['name'] for m in p['entries']):
            data = os.path.join(paths.gen(e), e + '.bin')
            if not os.path.exists(data):
                bad.append('%s: no data file %s' % (e, data)); continue
            hdr, _ = portdata.read(data)
            if hdr['version'] != portdata.version(e)[1]:
                bad.append('%s: data file version %x != package.toml %s' % (e, hdr['version'], p['version']))
            if os.path.getmtime(data) < os.path.getmtime(os.path.join(paths.monster(e), 'package.toml')):
                bad.append('%s: data file older than package.toml (repack)' % e)
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
                if qid not in [q for m in p['entries'] for q in m.get('quests', [])]:
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
    members += [('romfs/nativeNX/mh4uport/%s.bin' % m['name'], os.path.join(paths.gen(m['name']), m['name'] + '.bin'))
                for p in pk for m in p['entries']]
    members += [('romfs/nativeNX/mh4uport/' + name, os.path.join(MODULE_OUT, name)) for name, _, _ in ui_icons.ATLASES]
    core_zip = 'core-%s.zip' % c['version']
    write_zip(os.path.join(out, core_zip), [(MOD_NAME + '/' + a, s) for a, s in members])
    for p in pk:
        rf = paths.romfs(p['name'])
        mem = [(MOD_NAME + '/romfs/' + os.path.relpath(os.path.join(d, f), rf).replace(os.sep, '/'), os.path.join(d, f))
               for d, _, fs in os.walk(rf) for f in fs]
        write_zip(os.path.join(out, '%s-%s.zip' % (p['name'], p['version'])), mem)
    with open(os.path.join(out, 'NOTES.md'), 'w') as f:
        f.write(notes(c, pk, out))
    for f in sorted(os.listdir(out)):
        print('%10d %s' % (os.path.getsize(os.path.join(out, f)), os.path.join(out, f)))
    return out


NEWS = os.path.join(ROOT, 'notes', 'release-news.md')   # "## v<core version>" sections: this release's What's new


def news(version):
    """the What's new section of notes/release-news.md for this core version (its lines up to the next '## v')"""
    text = open(NEWS).read().split('\n')
    head = '## v' + version
    assert head in text, '%s has no section %s' % (NEWS, head)
    i = text.index(head) + 1
    j = next((k for k in range(i, len(text)) if text[k].startswith('## v')), len(text))
    return [l for l in text[i:j]]


def quests(p):
    """[(monster title, rank, quest title)] of a package's shipped quests: rank from questData (+0x11 board 10 = Hub,
    +0x12 stars: 1..7 = Hub Low / High Rank, 11.. = G1..), title = the English GMD's first string"""
    sys.path.insert(0, paths.GU_PY)
    import gmd
    rf, out = paths.romfs(p['name']), []
    for m in p['entries']:
        for q in m.get('quests', []):
            qd = open(os.path.join(rf, 'nativeNX/loc/quest/questData/questData_%07d.ext' % q), 'rb').read()
            star = qd[0x12]
            rank = 'G★%d' % (star - 10) if star > 10 else '%s ★%d' % ('High Rank' if star >= 4 else 'Low Rank', star)
            board = 'Hub' if qd[0x11] == 10 else 'board %d' % qd[0x11]
            title = gmd.gmd_strings(open(os.path.join(rf, 'nativeNX/eng/quest/questData/questData_%07d_eng.gmd' % q),
                                         'rb').read())[0]
            out.append((m.get('title', p['title']), '%s %s' % (board, rank), title))
    return out


def notes(c, pk, out):
    """release text: what the mod is, What's new (notes/release-news.md), the monsters and their quests, install /
    update / online play, the files with their sha256, the warnings"""
    v = c['version']
    lines = ['MH4U monsters in MHGU (Switch 1.4): the monsters, their arenas, music, quests and gear. '
             'Take every zip from this one release.', '',
             "## What's new"] + '\n'.join(news(v)).strip().split('\n') + ['', '## Monsters']
    for p in pk:
        qs = quests(p)
        for t in dict.fromkeys(t for t, _, _ in qs):
            ranks = list(dict.fromkeys(r.replace('Hub ', '') for tt, r, _ in qs if tt == t))
            lines.append('- **%s**: %s' % (t, ', '.join(ranks)))
    lines += ['', '## Install',
              '1. Open the mod folder: Ryujinx: right-click MHGU > Open Mods Directory. yuzu / Eden and others: '
              'right-click MHGU > Open Mod Data Location.',
              '2. Extract **core** (always), then the monsters you want. They all merge into one `%s` folder.' % MOD_NAME,
              '3. To update: delete `%s`, then extract the new zips.' % MOD_NAME, '',
              '- **Online**: everyone needs the same release and the same monsters.',
              '- **Removing a monster**: unequip its armor and weapons first (their models leave with it).', '',
              '<details><summary>Files (sha256)</summary>', '',
              '- core-%s.zip `%s`' % (v, sha256(os.path.join(out, 'core-%s.zip' % v)))]
    for p in pk:
        z = '%s-%s.zip' % (p['name'], p['version'])
        lines.append('- %s `%s`' % (z, sha256(os.path.join(out, z))))
    lines += ['', '</details>']
    return '\n'.join(lines) + '\n'


def publish(out, repo, yes, draft):
    c = core()
    tag = 'v%s' % c['version']
    files = [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.endswith('.zip')]
    body = os.path.join(out, 'NOTES.md')
    assert os.path.exists(body) and any(os.path.basename(f).startswith('core-') for f in files), 'package %s first' % out
    print('%srelease %s on %s with %d files:' % ('draft ' if draft else '', tag, repo, len(files)))
    for f in files: print('  ', os.path.basename(f))
    if not yes and input('publish? [y/N] ').strip().lower() != 'y':
        sys.exit('not published')
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--title', 'MH4U Port %s' % tag,
                    '--notes-file', body] + (['--draft'] if draft else []) + files, check=True)


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
                '--yes' in a, '--draft' in a)


if __name__ == '__main__':
    main()
