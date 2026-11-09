"""release.py : build, check and package an MHGU Definitive Edition release on the machine that holds the game dumps (a
release can never be built in hosted CI: the converters read ~15 GB of 4U / GU data and the module build reads GU's
main).

  release.py build           every monster's build.py (all steps), then the module, both without test switches
  release.py check           release checks on the current outputs (exit 1 on any failure)
  release.py package [DIR] [--pre N]
                             check, then the zips, icons-<release>.zip, manifest.json, NOTES.md and NOTES-main.md
                             into DIR (default dump/release/v<release>); --pre N: pre-release <core version>-pre.N
  release.py all [DIR] [--pre N]   build + package
  release.py publish DIR [--repo OWNER/NAME] [--yes] [--draft]
                             create the GitHub release v<release> on PACKAGES_REPO (default; manifest.json: a
                             pre-release is published as one, a release is marked Latest) with DIR's assets and NOTES.md
                             as its text (gh CLI); asks first unless --yes. REPO's own releases are the installer's
                             (.github/workflows/installer.yml): a release of the mod is refused there. Then main-notes.
  release.py main-notes [DIR]
                             REPO's draft v<installer version> (drafted by the workflow on the tag) gets NOTES-main.md
                             as its text, above GitHub's generated notes; a published release is left alone

Packages: core-<v>.zip = MHGU Definitive Edition/exefs/{subsdk1, <build id>.ips} + MHGU Definitive
Edition/romfs/nativeNX/mhgu_de/<every monster>.bin (always installed together: gear IDs depend on all of them) + the
icon atlases micon_sd/hd.tex and hudicon_sd/hd.tex; <monster>-<v>.zip = MHGU Definitive Edition/romfs/... (that
monster's assets, optional); map-<map>-<v>.zip = a map package's RomFS (maps/<map>: a ported arena, installed with the
monsters that require it). Every zip extracts into the game's mod directory ('<mods>/contents/<title>/' for Ryujinx,
'<load>/<TITLE>/' for the yuzu family) and they merge into the one 'MHGU Definitive Edition' folder. NOTES.md (the
release text on PACKAGES_REPO): What's new (notes/release-news.md, one section per core version: write it before
packaging), then how to install: the installer, or by hand (the maps each monster needs). NOTES-main.md (the text of
REPO's release, the page players land on): what the mod is, What's new, the monsters and their quests (read from the
quest files), how to install (the installer's files, or the zips on PACKAGES_REPO), online play and removals.
manifest.json (schema 1) is what the MHGU Definitive Edition Installer reads (installer/core/src/manifest.rs,
notes/installer.md): the release, every package with its zip, size, sha256, requires and every file (path below 'MHGU
Definitive Edition/', size, sha256), the save migrations and cleaning data (empty until the installer migrates saves)
and extra warnings. The releases before 2.0.0 (MH4U Port v1.x, on REPO) have none: the installer supports 2.0.0 and
later.
"""
import hashlib, io, json, os, re, struct, subprocess, sys, tomllib, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths, portdata, ui_icons

ROOT = paths.ROOT
TITLE_ID = '0100770008DD8000'
MOD_NAME = 'MHGU Definitive Edition'
MANIFEST_SCHEMA = 1        # bump on a change an older installer would misread (installer/core/src/manifest.rs)
INSTALLER_MIN = '2.0.0'    # oldest installer that installs this release (it asks for its own update otherwise)
LEGACY_NAME = 'MH4U Port'  # the mod's folder before 2.0.0 (installer/core/src/places.rs LEGACY_FOLDER)
REPO = 'Scrimas/MHGU-Definitive-Edition'                    # the code and the installer's releases
PACKAGES_REPO = 'Scrimas/MHGU-Definitive-Edition-Packages'  # the mod's releases (installer/core/src/lib.rs)
MODULE_OUT = os.path.join(ROOT, 'module', 'out')


def toml(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def vtuple(v):
    return tuple(int(x) for x in v.split('.'))


def core():
    return toml(os.path.join(ROOT, 'module', 'core.toml'))


def packages():
    """one dict per package: its package.toml + romfs = its RomFS folder + entries = its allocations.toml entries (one
    data file each) + alloc = the first entry; monster packages in registry order, then the map packages
    (maps/<name>: no entries, alloc None)"""
    out = []
    for p in alloc.packages():
        ents = [m for m in alloc.monsters() if alloc.package(m) == p]
        out.append(dict(toml(os.path.join(paths.monster(p), 'package.toml')), entries=ents, alloc=ents[0],
                        romfs=paths.romfs(p)))
    for mp in paths.maps():
        out.append(dict(toml(os.path.join(paths.map_dir(mp), 'package.toml')), entries=[], alloc=None,
                        romfs=paths.map_romfs(mp)))
    return out


def zip_name(p):
    """<monster>-<v>.zip, map-<map>-<v>.zip"""
    return ('map-%s-%s.zip' if p.get('kind') == 'map' else '%s-%s.zip') % (p['name'], p['version'])


def clean_env():
    env = dict(os.environ)
    for k in ('GOG_DEFINES', 'GOG_MOD_ROOT', 'PORT_ASSETS'):
        env.pop(k, None)
    return env


def build():
    for p in packages():
        print('== build %s' % p['name'], flush=True)
        subprocess.run([sys.executable, os.path.join(paths.package_dir(p['name']), 'build.py')], check=True,
                       env=clean_env())
    print('== build module', flush=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'module', 'build.py')], check=True, env=clean_env())


def build_id():
    ips = [f for f in os.listdir(MODULE_OUT) if f.endswith('.ips')]
    assert len(ips) == 1, ips
    return ips[0]


def check():
    """[problem] of the current outputs (empty = releasable)"""
    bad = ['allocations.toml: ' + e for e in alloc.check()] + moved_ids()
    steps = migrations(core()['version'])
    if [s['step'] for s in steps] != list(range(1, len(steps) + 1)):
        bad.append('migrations.toml: steps are numbered 1, 2, 3... in order (%s)' % [s['step'] for s in steps])
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
        rf = p['romfs']
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


def release_id(pre=None):
    """the release (= tag without 'v'): the core version, '<core>-pre.N' for a pre-release"""
    return core()['version'] + ('-pre.%d' % pre if pre else '')


def zip_files(path):
    """[{path below 'MHGU Definitive Edition/', size, sha256}] of a written zip, in zip order"""
    out = []
    with zipfile.ZipFile(path) as z:
        for zi in z.infolist():
            if zi.is_dir(): continue
            assert zi.filename.startswith(MOD_NAME + '/'), zi.filename
            with z.open(zi) as f:
                h = hashlib.sha256()
                for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
            out.append(dict(path=zi.filename[len(MOD_NAME) + 1:], size=zi.file_size, sha256=h.hexdigest()))
    return out


def write_icons(path):
    """icons-<release>.zip: <package>.png per monster package (tools/ui_icons.py package_icons), deterministic"""
    from PIL import Image
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
        for name, img in sorted(ui_icons.package_icons().items()):
            b = io.BytesIO()
            Image.fromarray(img, 'RGBA').save(b, 'PNG', optimize=True)
            zi = zipfile.ZipInfo(name + '.png', date_time=(2026, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            z.writestr(zi, b.getvalue())
    with zipfile.ZipFile(path) as z:
        return sorted(n[:-4] for n in z.namelist())


MIGRATIONS = os.path.join(ROOT, 'migrations.toml')
ID_KEYS = alloc.RANGES + alloc.LISTS + alloc.SCALARS + alloc.ORDERED + ('em_id', 'stage_alias', 'append', 'package')


def migrations(rel):
    """the migration steps released up to `rel` (migrations.toml), as the manifest lists them"""
    steps = toml(MIGRATIONS).get('step', []) if os.path.exists(MIGRATIONS) else []
    out = []
    for s in sorted(steps, key=lambda s: s['step']):
        if vtuple(s['release'].split('-')[0]) <= vtuple(rel.split('-')[0]):
            out.append({k: s.get(k, []) if k not in ('step', 'release') else s[k]
                        for k in ('step', 'release', 'items', 'decorations', 'armor', 'weapons', 'quests', 'save_slots')})
    return out


def cleaning(p):
    """what a monster package owns in a save (the installer's cleaning on removal): its items and decorations (item ID
    ranges, allocations.toml), its armor series and weapons (class, ID) as its data files append them (TBLA records
    appended to table\\armorSeriesData and table\\weaponNNBaseData from their `base`)"""
    items, armor, weapons = [], [], []
    for m in p['entries']:
        items += [list(m[k]) for k in ('items', 'decorations') if k in m]
        _, secs = portdata.read(os.path.join(paths.gen(m['name']), m['name'] + '.bin'))
        for tag, b in secs:
            if tag != 'TBLA':
                continue
            for t in portdata.decode(tag, b):
                ids = list(range(t['base'], t['base'] + t['count']))
                w = re.fullmatch(r'table\\weapon(\d\d)BaseData', t['path'])
                if t['path'] == 'table\\armorSeriesData':
                    armor += ids
                elif w:
                    weapons += [[int(w.group(1)), i] for i in ids]
    return dict(items=items, armor=sorted(set(armor)), weapons=weapons)


def last_tag():
    """the newest release tag v<major.minor.patch> before this one (None without git or tags)"""
    r = subprocess.run(['git', '-C', ROOT, 'tag', '--list', 'v*'], capture_output=True, text=True)
    tags = [t for t in r.stdout.split() if re.fullmatch(r'v\d+\.\d+\.\d+', t) and t != 'v' + core()['version']]
    return max(tags, key=lambda t: vtuple(t[1:])) if r.returncode == 0 and tags else None


def moved_ids():
    """[problem]: an ID shipped in the last release tag that allocations.toml moved, without a migration step of this
    release (migrations.toml)"""
    tag = last_tag()
    if not tag:
        return []
    r = subprocess.run(['git', '-C', ROOT, 'show', '%s:allocations.toml' % tag], capture_output=True, text=True)
    if r.returncode:
        return []
    old = {m['name']: m for m in tomllib.loads(r.stdout).get('monster', [])}
    now = {m['name']: m for m in alloc.monsters()}
    names = [m['name'] for m in tomllib.loads(r.stdout).get('monster', [])]
    bad = []
    if [n for n in now if n in old] != names:
        bad.append('allocations.toml: the entries shipped in %s changed order or left (registry order)' % tag)
    for n, o in old.items():
        for k in ID_KEYS:
            if n in now and o.get(k) != now[n].get(k):
                bad.append('allocations.toml: %s %s changed since %s (%s -> %s)' % (n, k, tag, o.get(k), now[n].get(k)))
    steps = [s for s in migrations(core()['version']) if s['release'] == core()['version']]
    if bad and steps:
        print('allocations moved shipped IDs since %s, with migration step(s) %s: check that they cover:\n  %s' % (
            tag, [s['step'] for s in steps], '\n  '.join(bad)))
        return []
    return [b + ' (shipped IDs never move: a migration step in migrations.toml if it must)' for b in bad]


def manifest(rel, pre, c, pk, out, icons):
    """manifest.json of the release in out (the zips written): what the installer reads"""
    def pkg(name, kind, title, version, zname, **more):
        z = os.path.join(out, zname)
        return dict(name=name, kind=kind, title=title, version=version, zip=zname, size=os.path.getsize(z),
                    sha256=sha256(z), **more, files=zip_files(z))
    ps = [pkg('core', 'core', 'Core', c['version'], 'core-%s.zip' % c['version'], subtitle='Needed by every monster',
              requires=[])]
    for p in pk:
        more = dict(subtitle=p.get('subtitle', ''), requires=p.get('requires', []), requires_core=p['requires_core'])
        if p.get('kind') == 'map':
            more['folder'] = p['folder']
        else:
            more['entries'] = [m['name'] for m in p['entries']]
            if p['name'] in icons: more['icon'] = p['name'] + '.png'
        ps.append(pkg(p['name'], p.get('kind', 'monster'), p['title'], p['version'], zip_name(p), **more))
    return dict(schema=MANIFEST_SCHEMA, release=rel, prerelease=bool(pre), installer_min=INSTALLER_MIN,
                title_id=TITLE_ID, mod_folder=MOD_NAME, icons='icons-%s.zip' % rel, packages=ps,
                migrations=migrations(rel), cleaning={p['name']: cleaning(p) for p in pk if p.get('kind') != 'map'},
                warnings=c.get('warnings', []))


def package(out, pre=None):
    bad = check()
    if bad:
        sys.exit('not releasable:\n  ' + '\n  '.join(bad))
    os.makedirs(out, exist_ok=True)
    c = core()
    pk = packages()
    rel = release_id(pre)
    members = [('exefs/subsdk1', os.path.join(MODULE_OUT, 'subsdk1')),
               ('exefs/' + build_id(), os.path.join(MODULE_OUT, build_id()))]
    members += [('romfs/nativeNX/mhgu_de/%s.bin' % m['name'], os.path.join(paths.gen(m['name']), m['name'] + '.bin'))
                for p in pk for m in p['entries']]
    members += [('romfs/nativeNX/mhgu_de/' + name, os.path.join(MODULE_OUT, name)) for name in ui_icons.FILES]
    core_zip = 'core-%s.zip' % c['version']
    write_zip(os.path.join(out, core_zip), [(MOD_NAME + '/' + a, s) for a, s in members])
    for p in pk:
        rf = p['romfs']
        mem = [(MOD_NAME + '/romfs/' + os.path.relpath(os.path.join(d, f), rf).replace(os.sep, '/'), os.path.join(d, f))
               for d, _, fs in os.walk(rf) for f in fs]
        write_zip(os.path.join(out, zip_name(p)), mem)
    icons = write_icons(os.path.join(out, 'icons-%s.zip' % rel))
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest(rel, pre, c, pk, out, icons), f, indent=1, ensure_ascii=False)
        f.write('\n')
    with open(os.path.join(out, 'NOTES.md'), 'w', encoding='utf-8') as f:
        f.write(notes(c, pk, pre))
    with open(os.path.join(out, 'NOTES-main.md'), 'w', encoding='utf-8') as f:
        f.write(notes_main(c, pk, rel, pre))
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
    """[(monster title, rank, quest title)] of a package's shipped quests: board from the ID (below 10000 = Village,
    GU's numbering; questData +0x11 is a quest type, not the board: GU uses 0..10 on both), rank from questData +0x12
    stars (Hub: 1..7 = Low / High Rank, 11.. = G1..; Village: the star count), title = the English GMD's first
    string"""
    sys.path.insert(0, paths.GU_PY)
    import gmd
    rf, out = p['romfs'], []
    for m in p['entries']:
        for q in m.get('quests', []):
            qd = open(os.path.join(rf, 'nativeNX/loc/quest/questData/questData_%07d.ext' % q), 'rb').read()
            star = qd[0x12]
            if q < 10000:
                board, rank = 'Village', '★%d' % star
            else:
                board = 'Hub'
                rank = 'G★%d' % (star - 10) if star > 10 else '%s ★%d' % ('High Rank' if star >= 4 else 'Low Rank', star)
            title = gmd.gmd_strings(open(os.path.join(rf, 'nativeNX/eng/quest/questData/questData_%07d_eng.gmd' % q),
                                         'rb').read())[0]
            out.append((m.get('title', p['title']), '%s %s' % (board, rank), title))
    return out


def notes(c, pk, pre=None):
    """release text: What's new (notes/release-news.md), then how to install: the installer, or by hand"""
    v = c['version']
    by = {p['name']: p for p in pk}
    assert all(r in by for p in pk for r in p.get('requires', [])), 'requires a package that is not in the release'
    need = ', '.join('`%s` for %s' % (zip_name(mp), ', '.join(p['title'] for p in pk if mp['name'] in p.get('requires', [])))
                     for mp in pk if mp.get('kind') == 'map')
    lines = (['> **Pre-release**: a test build that may contain bugs; use it at your own discretion (the installer '
              'offers it only when pre-releases are switched on in its Settings).', ''] if pre else []) + \
            ["## What's new"] + '\n'.join(news(v)).strip().split('\n')
    lines += ['', '## Install',
              '**With the installer** (Windows, Linux): download the [MHGU Definitive Edition Installer]'
              '(https://github.com/%s/releases/latest) and run it. Tick where to install (Ryujinx, the yuzu '
              'family, an SD card...) and the monsters you want: it downloads them with the maps they need, and '
              'updates or removes them later.' % REPO, '',
              '**By hand**:',
              '1. Download the zips you want from this release only (never mix zips from different releases).',
              '2. Open the mod folder: Ryujinx: right-click MHGU > Open Mods Directory. yuzu / Eden and others: '
              'right-click MHGU > Open Mod Data Location.',
              '3. Extract **core** (always), then the monsters you want and the maps they need (%s). They all merge '
              'into one `%s` folder.' % (need, MOD_NAME),
              '4. To update: delete `%s` (and `%s`, its name before 2.0.0), then extract the new zips.'
              % (MOD_NAME, LEGACY_NAME)]
    return '\n'.join(lines) + '\n'


def installer_version():
    return toml(os.path.join(ROOT, 'installer', 'Cargo.toml'))['workspace']['package']['version']


def notes_main(c, pk, rel, pre=None):
    """the text of REPO's release (the installer's: the page players land on): what the mod is, What's new, the
    monsters and their quests, how to install (the installer's files, or this release's zips by hand), the tips"""
    v, f = c['version'], 'MHGU-Definitive-Edition-Installer-%s-x86_64' % installer_version()
    lines = (['> **Pre-release**: a test build that may contain bugs; use it at your own discretion.', '']
             if pre else []) + \
            ['MH4U monsters in MHGU (Switch 1.4): the monsters, their arenas, music, quests and gear.', '',
             "## What's new"] + '\n'.join(news(v)).strip().split('\n') + ['', '## Monsters and quests',
             'On the Hub quest board (Village: on the village board):']
    for p in pk:
        qs = quests(p)
        for t in dict.fromkeys(t for t, _, _ in qs):
            mine = [(r.replace('Hub ', ''), q) for tt, r, q in qs if tt == t]
            lines.append('- **%s**: %s' % (t, ' · '.join('%s: %s' % (r, ', '.join('*%s*' % q for rr, q in mine if rr == r))
                                                          for r in dict.fromkeys(r for r, _ in mine))))
    lines += ['', '## Install',
              '**With the installer**: download `%s.exe` (Windows 10 / 11) or `%s.AppImage` (Linux: make it '
              'executable) below and run it. Tick where to install (Ryujinx, the yuzu family, an SD card...) and the '
              'monsters you want: it downloads them with the maps they need, and updates or removes them later.'
              % (f, f), '',
              '**By hand**: the zips of this release are on [MHGU-Definitive-Edition-Packages v%s]'
              '(https://github.com/%s/releases/tag/v%s): follow the instructions there.' % (rel, PACKAGES_REPO, rel), '',
              '- **Online**: everyone needs the same release and the same monsters.',
              '- **Removing a monster**: unequip its armor and weapons first (their models leave with it).']
    return '\n'.join(lines) + '\n'


MAIN_MARK = "<!-- release.py: NOTES-main.md above, GitHub's notes below -->"


def main_notes(out):
    """REPO's draft v<installer version> gets NOTES-main.md as its text, above the notes GitHub generated (kept); a
    published release is left alone"""
    tag, body = 'v' + installer_version(), os.path.join(out, 'NOTES-main.md')
    assert os.path.exists(body), 'package %s first' % out
    r = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO, '--json', 'isDraft,body'], capture_output=True,
                       text=True)
    if r.returncode:
        print('no release %s on %s yet (.github/workflows/installer.yml drafts it on the tag): run release.py '
              'main-notes %s once it is there' % (tag, REPO, out))
        return
    d = json.loads(r.stdout)
    if not d['isDraft']:
        print('%s on %s is published: its text is left alone' % (tag, REPO))
        return
    generated = d['body'].split(MAIN_MARK, 1)[-1].strip()
    text = open(body, encoding='utf-8').read().rstrip() + '\n\n' + MAIN_MARK + '\n\n' + generated + '\n'
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', REPO, '--notes-file', '-'], input=text, text=True,
                   check=True)
    print("%s on %s (draft): NOTES-main.md above GitHub's notes" % (tag, REPO))


def publish(out, repo, yes, draft):
    body, mf = os.path.join(out, 'NOTES.md'), os.path.join(out, 'manifest.json')
    assert os.path.exists(body) and os.path.exists(mf), 'package %s first' % out
    if repo.lower() == REPO.lower():
        sys.exit("%s's releases are the installer's: the mod's go to %s" % (REPO, PACKAGES_REPO))
    m = json.load(open(mf, encoding='utf-8'))
    tag, pre = 'v%s' % m['release'], m['prerelease']
    files = [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.endswith('.zip')] + [mf]
    assert any(os.path.basename(f).startswith('core-') for f in files), 'package %s first' % out
    print('%s%s %s on %s with %d files:' % ('draft ' if draft else '', 'pre-release' if pre else 'release', tag, repo,
                                          len(files)))
    for f in files: print('  ', os.path.basename(f))
    if not yes and input('publish? [y/N] ').strip().lower() != 'y':
        sys.exit('not published')
    # a pre-release never takes the Latest badge (the installer installs the Latest release, pre-releases on request)
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--title', 'MHGU Definitive Edition %s' % tag,
                    '--notes-file', body] + (['--prerelease'] if pre else ['--latest']) + (['--draft'] if draft else [])
                   + files, check=True)
    main_notes(out)


def main():
    a = sys.argv[1:]
    pre = None
    if '--pre' in a:
        i = a.index('--pre')
        pre = int(a[i + 1]); assert pre > 0, '--pre N: N from 1'
        del a[i:i + 2]
    default_out = os.path.join(ROOT, 'dump', 'release', 'v' + release_id(pre))
    if not a or a[0] not in ('build', 'check', 'package', 'all', 'publish', 'main-notes'):
        sys.exit(__doc__)
    if a[0] in ('build', 'all'):
        build()
    if a[0] == 'check':
        bad = check()
        print('releasable' if not bad else 'not releasable:\n  ' + '\n  '.join(bad))
        sys.exit(1 if bad else 0)
    if a[0] in ('package', 'all'):
        package(a[1] if len(a) > 1 else default_out, pre)
    if a[0] == 'publish':
        repo = a[a.index('--repo') + 1] if '--repo' in a else PACKAGES_REPO
        publish(a[1] if len(a) > 1 and not a[1].startswith('--') else default_out, repo, '--yes' in a, '--draft' in a)
    if a[0] == 'main-notes':
        main_notes(a[1] if len(a) > 1 else default_out)


if __name__ == '__main__':
    main()
