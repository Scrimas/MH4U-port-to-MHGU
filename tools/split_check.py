"""split_check.py : prove that a build change moved files between packages without changing a byte (maps split from
their monsters, 2026-11), by comparing the current outputs with a packaged release.

  split_check.py [RELEASE_DIR]     RELEASE_DIR: a release made by tools/release.py package (default: the newest
                                   dump/release/v*)

Every file of RELEASE_DIR's zips is looked up in the current outputs:
  core-<v>.zip   exefs/<f> = module/out/<f>; romfs/nativeNX/mhgu_de/<entry>.bin = the entry's gen/<entry>.bin;
                 the icon atlases = module/out/<name>
  other zips     romfs/<path> = the one package (monster or map) whose romfs holds <path> now
One line per zip (identical / differs / missing, and where its files live now), then the current files that no zip of
the release holds (new) and the paths held by two packages. Exit 0 when every file is found once and identical and
nothing is new. Only paths and hashes are printed (no game data).
"""
import glob, hashlib, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths, ui_icons

MOD = 'MHGU Definitive Edition/'
MODULE_OUT = os.path.join(paths.ROOT, 'module', 'out')


def sha(f):
    h = hashlib.sha256()
    for b in iter(lambda: f.read(1 << 20), b''):
        h.update(b)
    return h.hexdigest()


def file_sha(path):
    with open(path, 'rb') as f:
        return sha(f)


def current():
    """{romfs path: [(package, file)]} over every monster package and map package"""
    out = {}
    roots = [(p, paths.romfs(p)) for p in alloc.packages()] + [(m, paths.map_romfs(m)) for m in paths.maps()]
    for name, rf in roots:
        for d, _, fs in os.walk(rf):
            for f in fs:
                full = os.path.join(d, f)
                out.setdefault(os.path.relpath(full, rf).replace(os.sep, '/'), []).append((name, full))
    return out


def core_file(rel):
    """the current file of a core zip member (path below 'MHGU Definitive Edition/')"""
    if rel.startswith('exefs/'):
        return os.path.join(MODULE_OUT, rel[6:])
    m = re.fullmatch(r'romfs/nativeNX/mhgu_de/(.+)', rel)
    if m and m.group(1) in ui_icons.FILES:
        return os.path.join(MODULE_OUT, m.group(1))
    if m and m.group(1).endswith('.bin'):
        e = m.group(1)[:-4]
        return os.path.join(paths.gen(e), e + '.bin')
    return None


def main():
    a = sys.argv[1:]
    rel_dir = a[0] if a else max(glob.glob(os.path.join(paths.DUMP, 'release', 'v*')),
                                 key=lambda p: tuple(int(x) for x in re.findall(r'\d+', os.path.basename(p))))
    cur = current()
    seen, bad = set(), 0
    print('release', rel_dir)
    for zp in sorted(glob.glob(os.path.join(rel_dir, '*.zip'))):
        name = os.path.basename(zp)
        same = diff = miss = 0
        where = {}
        with zipfile.ZipFile(zp) as z:
            for zi in z.infolist():
                if zi.is_dir(): continue
                assert zi.filename.startswith(MOD), (name, zi.filename)
                rel = zi.filename[len(MOD):]
                if name.startswith('core-'):
                    f, owner = core_file(rel), 'core'
                elif rel.startswith('romfs/') and rel[6:] in cur:
                    seen.add(rel[6:])
                    owner, f = cur[rel[6:]][0]
                else:
                    f, owner = None, None
                if not f or not os.path.exists(f):
                    miss += 1
                    print('  missing %s: %s' % (name, rel))
                    continue
                where[owner] = where.get(owner, 0) + 1
                with z.open(zi) as zf:
                    ok = zi.file_size == os.path.getsize(f) and sha(zf) == file_sha(f)
                same += ok; diff += not ok
                if not ok: print('  differs %s: %s (now %s)' % (name, rel, os.path.relpath(f, paths.ROOT)))
        bad += diff + miss
        print('%-32s %4d identical, %d differ, %d missing; now in %s' % (
            name, same, diff, miss, ', '.join('%s %d' % kv for kv in sorted(where.items()))))
    new = sorted(r for r in cur if r not in seen)
    for r in new:
        print('  new (in no zip of the release): %s (%s)' % (r, ', '.join(p for p, _ in cur[r])))
    dup = sorted(r for r, v in cur.items() if len(v) > 1)
    for r in dup:
        print('  in two packages: %s (%s)' % (r, ', '.join(p for p, _ in cur[r])))
    bad += len(new) + len(dup)
    print('same files, same bytes' if not bad else '%d problem(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
