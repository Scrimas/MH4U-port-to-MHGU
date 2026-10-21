"""paths.py : where the inputs live and where a monster's outputs go (one place for every tool).

Inputs outside this repo (override with the environment for another machine / CI):
  GU_SCRATCH   MHGU_Editor scratch dir: main.asm, mem.bin (GU 1.4 main, flat), base_romfs.bin, py/ helpers
  GU_EDITOR    MHGU_Editor checkout (tools/ helpers, data/monster-index.csv)
Repo layout: tools/ + module/ + notes/ = shared core; monsters/<package>/{module,tools,notes} = one package,
monsters/<package>/{gen,romfs} = its generated tables and converted RomFS (gitignored: game data). A package holds one
allocations.toml entry, or several (their `package` key, e.g. Dalamadur, Shah Dalamadur and their tail halves): the
functions below take an entry name and resolve its package; gen/ keeps one data file per entry.
"""
import os, tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
DUMP = os.path.join(ROOT, 'dump')

GU_EDITOR = os.environ.get('GU_EDITOR', '/home/scrimas/Projects/MHGU_Editor')
GU_SCRATCH = os.environ.get('GU_SCRATCH', os.path.join(GU_EDITOR, 'scratch'))
GU_PY = os.path.join(GU_SCRATCH, 'py')               # romfs.py, asm.py, arc.py ... (MHGU_Editor)
GU_EDITOR_TOOLS = os.path.join(GU_EDITOR, 'tools')
GU_ROMFS = os.path.join(GU_SCRATCH, 'base_romfs.bin')
GU_MAIN = os.path.join(GU_SCRATCH, 'mem.bin')        # MHGU 1.4 main, flat


_PACKAGES = None


def package(name):
    """the package folder name of an allocations.toml entry (its `package` key, default the entry name); a name that
    is no entry is taken as a package name"""
    global _PACKAGES
    if _PACKAGES is None:
        with open(os.path.join(ROOT, 'allocations.toml'), 'rb') as f:
            _PACKAGES = {m['name']: m.get('package', m['name']) for m in tomllib.load(f).get('monster', [])}
    return _PACKAGES.get(name, name)


def monster(name):
    """monsters/<package of name>"""
    return os.path.join(ROOT, 'monsters', package(name))


def romfs(name):
    """monsters/<package>/romfs: mirror of the game RomFS (nativeNX/...), shared by the package's entries"""
    return os.path.join(monster(name), 'romfs')


def gen(name):
    """monsters/<package>/gen: generated tables and the entries' data files <name>.bin"""
    return os.path.join(monster(name), 'gen')
