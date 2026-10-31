"""check_repo.py : refuse game data and keys in git. Run by the pre-commit hook (tools/hooks/pre-commit, switched on by
tools/setup.py) and by CI; exit 1 with the reason for each refused file.

  python3 tools/check_repo.py --staged        the files staged for the next commit (pre-commit hook)
  python3 tools/check_repo.py --since REF     the files changed from REF to HEAD (CI: a PR or a push)
  python3 tools/check_repo.py --all           every tracked file
"""
import fnmatch, os, re, subprocess, sys

DATA_PATHS = ['dump/*', 'ryuroot/*', 'save-backup-*', 'monsters/*/romfs*/*', 'monsters/*/gen/*', 'weapons/*/romfs*/*',
              'weapons/*/gen/*']
GAME_EXT = {'.3ds', '.cci', '.cxi', '.cia', '.nsp', '.xci', '.nca', '.nso', '.arc', '.lmt', '.mod', '.tex', '.mrl',
            '.gmd', '.lmd', '.sbc', '.efl', '.lcm', '.emc', '.stq', '.stqr', '.mca', '.bcwav', '.opus', '.ext', '.qdl',
            '.gfd', '.gui', '.sav', '.keys'}
MAX_BINARY = 256 * 1024
KEY = re.compile(rb'(header_key|titlekek_[0-9a-f]{2}|master_key_[0-9a-f]{2}|key_area_key_\w+|package2_key_[0-9a-f]{2})'
                 rb'\s*=\s*[0-9a-fA-F]{32}')


def git(*a, raw=False):
    r = subprocess.run(['git', *a], capture_output=True, check=True)
    return r.stdout if raw else r.stdout.decode()


def problems(path, data):
    if any(fnmatch.fnmatch(path, p) for p in DATA_PATHS): yield 'in a game-data folder (see .gitignore)'
    if os.path.splitext(path)[1].lower() in GAME_EXT: yield 'game file type %s' % os.path.splitext(path)[1]
    if b'\0' in data[:8192] and len(data) > MAX_BINARY: yield 'binary file over %d KB' % (MAX_BINARY // 1024)
    if KEY.search(data): yield 'contains console key material'


def main():
    mode = sys.argv[1:2]
    if mode == ['--staged']:
        files = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split('\0')
        read = lambda p: git('show', ':' + p, raw=True)
    elif mode == ['--since'] and len(sys.argv) == 3:
        files = git('diff', '--name-only', '--diff-filter=ACMR', '-z', sys.argv[2], 'HEAD').split('\0')
        read = lambda p: git('show', 'HEAD:' + p, raw=True)
    elif mode == ['--all']:
        files = git('ls-files', '-z').split('\0')
        read = lambda p: git('show', 'HEAD:' + p, raw=True)
    else:
        sys.exit(__doc__)
    bad = 0
    for p in filter(None, files):
        for why in problems(p, read(p)):
            print('REFUSED %s: %s' % (p, why)); bad += 1
    if bad:
        sys.exit('%d problem(s): no game data or keys in git (CONTRIBUTING.md, Rules). Unstage with git restore '
                 '--staged <file>.' % bad)
    print('check_repo: %d file(s) ok' % len([f for f in files if f]))


if __name__ == '__main__':
    main()
