"""cli_test.py : the installer end to end, without a window and without game data: a fake release (dummy files, zips
made as tools/release.py makes them, a manifest of schema 1) installed by mh4uport-cli into every kind of place.

  python3 installer/tests/cli_test.py [CLI]      CLI default: installer/target/debug/mh4uport-cli(.exe)

Checks: the files land where each place wants them (Ryujinx, the yuzu family, the recomp, an SD card, a folder), maps
come and go with their monsters, a hand-extracted install is replaced only when asked, an update to a newer release,
a pre-release only when asked, a save migrated by a release's step (backed up, every copy), the gear of a removed
monster taken off, a save that cannot be migrated stopping the install, the removal leaves other mods alone. The saves
are synthetic (zeros with valid slot pointers). Exit 1 at the first failure.
"""
import hashlib, json, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = '.exe' if os.name == 'nt' else ''
CLI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'target', 'debug', 'mh4uport-cli' + EXE)
TID = '0100770008DD8000'
MOD = 'MH4U Port'

PACKAGES = [   # name, kind, requires, files
    ('core', 'core', [], ['exefs/subsdk1', 'exefs/FB08F1D2.ips', 'romfs/nativeNX/mh4uport/alpha.bin',
                          'romfs/nativeNX/mh4uport/beta.bin']),
    ('alpha', 'monster', ['arena'], ['romfs/nativeNX/arc/enemy/em100_00.arc', 'romfs/nativeNX/loc/quest/q1.ext']),
    ('beta', 'monster', ['arena'], ['romfs/nativeNX/arc/enemy/em101_00.arc']),
    ('gamma', 'monster', [], ['romfs/nativeNX/arc/enemy/em102_00.arc']),
    ('arena', 'map', [], ['romfs/nativeNX/arc/stage/m28d/m28d.arc', 'romfs/nativeNX/eng/arc/stage/map_com/m28_eng.arc']),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


# a synthetic save (MHGU_Editor docs/11-save-map.md offsets): slot 1 in use, character base SLOT1
SAVE_SIZE, SLOT1 = 5_159_100, 0x18CC9C
ITEM_BOX, EQ_BOX, WORN, STORE = 0x278, 0x62EE, 0x23B39, 0x533A


def blank_save():
    b = bytearray(SAVE_SIZE)
    for k, base in enumerate((0x18CC9C, 0x2AC560, 0x3CBE24)):
        struct.pack_into('<I', b, 0x34 + 4 * k, base - 0x24)
    b[0x28] = 1
    return b


def set_bits(b, at, pos, width, v):
    for k in range(width):
        o, m = at + (pos + k) // 8, 1 << ((pos + k) % 8)
        b[o] = b[o] | m if v >> k & 1 else b[o] & ~m


def get_bits(b, at, pos, width):
    return sum(((b[at + (pos + k) // 8] >> ((pos + k) % 8)) & 1) << k for k in range(width))


def write_save(d, b):
    for c in ('0', '1'):
        os.makedirs(os.path.join(d, c), exist_ok=True)
        for f in ('system', 'system_backup'):
            open(os.path.join(d, c, f), 'wb').write(b)


def make_release(root, tag, version, pre=False, change=(), migrations=(), cleaning=None):
    """a release folder root/<tag>/ with the zips + manifest.json; `change`: packages whose files differ"""
    d = os.path.join(root, tag)
    os.makedirs(d)
    pkgs, assets = [], []
    for name, kind, req, files in PACKAGES:
        pv = version if name in change or kind == 'core' else '1.0.0'
        zname = ('map-%s-%s.zip' if kind == 'map' else '%s-%s.zip') % (name, pv)
        entries = []
        with zipfile.ZipFile(os.path.join(d, zname), 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(files):
                data = ('%s %s %s' % (name, pv, f)).encode()
                zi = zipfile.ZipInfo('%s/%s' % (MOD, f), date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, data)
                entries.append(dict(path=f, size=len(data), sha256=sha(data)))
        zb = open(os.path.join(d, zname), 'rb').read()
        p = dict(name=name, kind=kind, title=name.title(), subtitle='', version=pv, requires=req, zip=zname,
                 size=len(zb), sha256=sha(zb), files=entries)
        if kind == 'map': p['folder'] = 28
        pkgs.append(p)
    m = dict(schema=1, release=version, prerelease=pre, installer_min='1.0.0', title_id=TID, mod_folder=MOD,
             packages=pkgs, migrations=list(migrations), cleaning=cleaning or {}, warnings=[])
    json.dump(m, open(os.path.join(d, 'manifest.json'), 'w'), indent=1)
    for f in sorted(os.listdir(d)):
        assets.append(dict(name=f, browser_download_url='%s/%s' % (tag, f), size=os.path.getsize(os.path.join(d, f))))
    return dict(tag_name=tag, prerelease=pre, draft=False, html_url='', published_at='2026-11-09T00:00:00Z', assets=assets)


def publish(root, rels):
    json.dump(rels, open(os.path.join(root, 'releases.json'), 'w'))


def cli(*args, ok=(0,)):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode not in ok:
        sys.exit('FAILED: mh4uport-cli %s -> %d\n%s%s' % (' '.join(args), r.returncode, r.stdout, r.stderr))
    return r


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what, flush=True)
    if not cond:
        sys.exit(1)


def read(p):
    return open(p, encoding='utf-8').read() if os.path.isfile(p) else None


def main():
    tmp = tempfile.mkdtemp(prefix='mh4u-cli-')
    try:
        rel = os.path.join(tmp, 'releases')
        os.makedirs(rel)
        os.environ['MH4UPORT_RELEASES'] = rel
        os.environ['MH4UPORT_CACHE'] = os.path.join(tmp, 'cache')
        os.environ.pop('MHGU_MODS_DIR', None)
        v110 = make_release(rel, 'v1.10.0', '1.10.0')
        publish(rel, [v110])
        # the places
        ryu, eden, sd, recomp, folder = (os.path.join(tmp, n) for n in ('Ryujinx', 'eden-test', 'sd', 'recomp', 'folder'))
        for d in (ryu, eden, os.path.join(sd, 'atmosphere'), recomp, folder):
            os.makedirs(d)
        open(os.path.join(recomp, 'mhgurecomp' + EXE), 'w').close()
        other = os.path.join(sd, 'atmosphere/contents', TID, 'romfs/other_mod/file.bin')
        os.makedirs(os.path.dirname(other))
        open(other, 'w').write('theirs')
        mods = {
            'ryujinx': os.path.join(ryu, 'mods/contents', TID.lower(), MOD),
            'yuzu': os.path.join(eden, 'load', TID, MOD),
            'recomp': os.path.join(recomp, 'mods', MOD),
            'folder': os.path.join(folder, MOD),
        }
        roots = dict(ryujinx=ryu, yuzu=eden, recomp=recomp, folder=folder, sdcard=sd)
        places = [a for k, r in roots.items() for a in ('--place', '%s:%s' % (k, r))]

        r = cli('releases')
        check(r.stdout.startswith('v1.10.0\t'), 'the release list')
        r = cli('install', *places, '--monsters', 'alpha', ok=(1,))
        check('add --yes' in r.stderr and 'arena add 1.0.0 (for Alpha)' in r.stdout, 'a plan without --yes changes nothing')
        check(not os.path.exists(mods['folder']), '... nothing installed')
        cli('install', *places, '--monsters', 'alpha', '--yes')
        for k, d in mods.items():
            check(read(os.path.join(d, 'romfs/nativeNX/arc/stage/m28d/m28d.arc')) == 'arena 1.0.0 romfs/nativeNX/arc/stage/m28d/m28d.arc'
                  and os.path.isfile(os.path.join(d, 'exefs/subsdk1')) and os.path.isfile(os.path.join(d, 'mh4uport-install.json')),
                  '%s: core, alpha and its map, the record' % k)
        a = os.path.join(sd, 'atmosphere')
        check(os.path.isfile(os.path.join(a, 'exefs_patches', MOD, 'FB08F1D2.ips'))
              and os.path.isfile(os.path.join(a, 'contents', TID, 'exefs/subsdk1'))
              and os.path.isfile(os.path.join(a, 'contents', TID, 'romfs/nativeNX/arc/enemy/em100_00.arc'))
              and os.path.isfile(os.path.join(a, 'contents', TID, 'mh4uport-install.json')), 'sdcard: Atmosphère folders')
        r = cli('install', *places, '--monsters', 'alpha')
        check(r.stdout.count('up to date') == 5, 'installed again: up to date everywhere')
        # beta shares the map; alpha leaves, the map stays; then gamma alone, the map leaves
        cli('install', *places, '--monsters', 'beta', '--yes')
        check(os.path.isfile(os.path.join(mods['ryujinx'], 'romfs/nativeNX/arc/stage/m28d/m28d.arc'))
              and not os.path.exists(os.path.join(mods['ryujinx'], 'romfs/nativeNX/arc/enemy/em100_00.arc')), 'a shared map stays with beta')
        cli('install', *places, '--monsters', 'gamma', '--yes')
        check(not os.path.exists(os.path.join(mods['yuzu'], 'romfs/nativeNX/arc/stage'))
              and not os.path.exists(os.path.join(a, 'contents', TID, 'romfs/nativeNX/arc/stage')), 'the map leaves with its last monster')
        # a newer release: core and gamma change, the rest moves along
        v111 = make_release(rel, 'v1.11.0', '1.11.0', change=('gamma',))
        pre = make_release(rel, 'v1.12.0-pre.1', '1.12.0-pre.1', pre=True)
        publish(rel, [v110, v111, pre])
        r = cli('install', *places, ok=(1,))
        check('gamma update 1.0.0 -> 1.11.0' in r.stdout and 'core update 1.10.0 -> 1.11.0' in r.stdout, 'an update plan (pre-release left out)')
        cli('install', *places, '--yes')
        check(read(os.path.join(mods['recomp'], 'romfs/nativeNX/arc/enemy/em102_00.arc')) == 'gamma 1.11.0 romfs/nativeNX/arc/enemy/em102_00.arc', 'updated')
        r = cli('install', '--place', 'folder:' + folder, '--pre', ok=(1,))
        check('core update 1.11.0 -> 1.12.0-pre.1' in r.stdout, 'the pre-release only with --pre')
        # a hand-extracted install
        hand = os.path.join(tmp, 'hand')
        os.makedirs(os.path.join(hand, MOD, 'romfs/old'))
        open(os.path.join(hand, MOD, 'romfs/old/leftover.arc'), 'w').write('x')
        cli('install', '--place', 'folder:' + hand, '--monsters', 'gamma', '--yes', ok=(3,))
        check(os.path.isfile(os.path.join(hand, MOD, 'romfs/old/leftover.arc')), 'a hand install is kept without --replace')
        cli('install', '--place', 'folder:' + hand, '--monsters', 'gamma', '--yes', '--replace')
        check(not os.path.exists(os.path.join(hand, MOD, 'romfs/old')) and os.path.isfile(os.path.join(hand, MOD, 'mh4uport-install.json')),
              'replaced with --replace')
        # a damaged download is refused
        z = os.path.join(rel, 'v1.11.0', 'beta-1.0.0.zip')
        open(z, 'ab').write(b'tampered')
        shutil.rmtree(os.environ['MH4UPORT_CACHE'])
        r = cli('install', '--place', 'folder:' + folder, '--monsters', 'gamma,beta', '--yes', ok=(1,))
        check('checksum' in r.stderr and not os.path.exists(os.path.join(mods['folder'], 'romfs/nativeNX/arc/enemy/em101_00.arc')),
              'a download that does not match the manifest is refused')
        # saves: a release with a migration step, then the gear of a monster that leaves
        sd_ = os.path.join(ryu, 'bis/user/save/0000000000000002')
        b = blank_save()
        set_bits(b, SLOT1 + ITEM_BOX, 0, 12, 2977); set_bits(b, SLOT1 + ITEM_BOX, 12, 7, 4)
        struct.pack_into('<HH', b, SLOT1 + EQ_BOX, 1, 1287)               # entry 0: alpha's head (armor series 1287)
        struct.pack_into('<HH', b, SLOT1 + EQ_BOX + 36, 7 + 5, 7)        # entry 1: a GU weapon, class 5
        struct.pack_into('<7H', b, SLOT1 + WORN, 1, 0, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF)
        write_save(sd_, bytes(b))
        clean = {'alpha': dict(items=[[2977, 2985]], armor=[1287], weapons=[])}
        step1 = dict(step=1, release='1.14.0', items=[[2977, 3050]], decorations=[], armor=[], weapons=[], quests=[], save_slots=[])
        v114 = make_release(rel, 'v1.14.0', '1.14.0', migrations=[step1], cleaning=clean)
        publish(rel, [v110, v111, pre, v114])
        ry = ('--place', 'ryujinx:' + ryu)
        os.environ['MH4UPORT_BACKUPS'] = os.path.join(tmp, 'backups')
        r = cli('install', *ry, '--monsters', 'alpha', '--yes')
        check('save Ryujinx' not in r.stderr and 'migrate [(1, [1])]' in r.stdout, 'a save to migrate is listed')
        for c in ('0/system', '0/system_backup', '1/system', '1/system_backup'):
            s2 = open(os.path.join(sd_, c), 'rb').read()
            check(get_bits(s2, SLOT1 + ITEM_BOX, 0, 12) == 3050 and struct.unpack_from('<HHHHI', s2, SLOT1 + STORE + 4)[0] == 2
                  and struct.unpack_from('<I', s2, SLOT1 + STORE + 12)[0] == 1, 'migrated: item 2977 -> 3050, store v2 level 1 (%s)' % c)
        backups = [os.path.join(dp, f) for dp, _, fs in os.walk(os.environ['MH4UPORT_BACKUPS']) for f in fs]
        check(len(backups) == 4 and all(get_bits(open(f, 'rb').read(), SLOT1 + ITEM_BOX, 0, 12) == 2977 for f in backups),
              'the four copies backed up before the write')
        r = cli('install', *ry, '--monsters', 'alpha', ok=(0, 1))
        check('migrate' not in r.stdout, 'migrated once')
        r = cli('install', *ry, '--monsters', 'gamma', '--yes')
        s2 = open(os.path.join(sd_, '0/system'), 'rb').read()
        check(struct.unpack_from('<2H', s2, SLOT1 + WORN) == (1, 0xFFFF) and struct.unpack_from('<H', s2, SLOT1 + EQ_BOX + 2)[0] == 1287,
              'alpha leaves: its head taken off, kept in the box (unequip)')
        # a save holding another tool's data where the store is: the install stops unless --anyway
        b = bytearray(open(os.path.join(sd_, '0/system'), 'rb').read())
        b[SLOT1 + STORE + 8] ^= 0xFF                                     # the check word: not a store any more
        write_save(sd_, bytes(b))
        step2 = dict(step1, step=2, release='1.15.0', items=[[3050, 3051]])
        v115 = make_release(rel, 'v1.15.0', '1.15.0', migrations=[step1, step2], cleaning=clean)
        publish(rel, [v110, v111, pre, v114, v115])
        r = cli('install', *ry, '--monsters', 'gamma', '--yes', ok=(4,))
        check('cannot be migrated' in r.stdout, 'a save that cannot be migrated stops the install')
        cli('install', *ry, '--monsters', 'gamma', '--yes', '--anyway')
        check(open(os.path.join(sd_, '0/system'), 'rb').read() == bytes(b), '--anyway installs and leaves that save alone')
        # removal
        cli('remove', *places, '--yes', '--anyway')
        check(all(not os.path.exists(d) for d in mods.values()), 'removed from every mod folder')
        left = sorted(os.path.relpath(os.path.join(dp, f), a).replace(os.sep, '/') for dp, _, fs in os.walk(a) for f in fs)
        check(left == ['contents/%s/romfs/other_mod/file.bin' % TID], 'sdcard: only the other mod is left')
        print('all ok')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
