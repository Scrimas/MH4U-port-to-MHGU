"""paths.py : where the inputs live and where a monster's outputs go (one place for every tool).

GU inputs, made from your own MHGU v1.4 by tools/setup.py (each one overridable with the environment variable of the
same name):
  GU_EXEFS     dump/gu_exefs: Ryujinx, right-click MHGU > Extract Data > ExeFS (main, main.npdm, rtld, sdk, subsdk0)
  GU_ROMFS     dump/gu_romfs: Ryujinx, Extract Data > RomFS (update 1.4 selected), or a RomFS image file
  GU_CODE      dump/gu_main: made by `tools/setup.py gu_code` from GU_EXEFS: mem.bin (main, flat), main32.elf, main.asm
GU_PY = tools/gulib: the GU readers (romfs, arc, gmd, asm ...), vendored from MHGU_Editor.
Repo layout: tools/ + module/ + notes/ = shared core; monsters/<package>/{module,tools,notes} = one package,
monsters/<package>/{gen,romfs} = its generated tables and converted RomFS (gitignored: game data). A package holds one
allocations.toml entry, or several (their `package` key, e.g. Dalamadur, Shah Dalamadur and their tail halves): the
functions below take an entry name and resolve its package; gen/ keeps one data file per entry.
maps/<map>/{package.toml,build.py,tools,notes} = a map package (a ported arena: stage arcs, map UI, map_com, stage
BGM), required by the monsters whose package.toml lists it in `requires`; maps/<map>/romfs = its converted RomFS
(gitignored). A map has no allocations.toml entry: its stage folder is the stage_alias of the monsters requiring it.
"""
import glob, os, tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
DUMP = os.path.join(ROOT, 'dump')
ROM_4U = (sorted(glob.glob(os.path.join(DUMP, 'base', '*.3ds'))) or [os.path.join(DUMP, 'base', 'MH4U.3ds')])[0]
UPDATE_4U = (sorted(glob.glob(os.path.join(DUMP, 'update', '*.cia'))) or [os.path.join(DUMP, 'update', 'v1.1.cia')])[0]

GU_EXEFS = os.environ.get('GU_EXEFS', os.path.join(DUMP, 'gu_exefs'))
GU_ROMFS = os.environ.get('GU_ROMFS', os.path.join(DUMP, 'gu_romfs'))
GU_CODE = os.environ.get('GU_CODE', os.path.join(DUMP, 'gu_main'))
GU_PY = os.path.join(TOOLS, 'gulib')                 # romfs.py, asm.py, arc.py ... (put first on sys.path)
GU_MAIN = os.path.join(GU_CODE, 'mem.bin')           # MHGU 1.4 main, flat


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


MAPS = os.path.join(ROOT, 'maps')


def maps():
    """map package names (maps/<name>/package.toml), sorted"""
    return sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(MAPS, '*', 'package.toml')))


def map_dir(name):
    """maps/<name>"""
    return os.path.join(MAPS, name)


def map_romfs(name):
    """maps/<name>/romfs: the map's converted RomFS (nativeNX/...)"""
    return os.path.join(map_dir(name), 'romfs')


def package_dir(name):
    """the folder of any package: maps/<name> for a map, else monsters/<package of name>"""
    return map_dir(name) if os.path.exists(os.path.join(map_dir(name), 'package.toml')) else monster(name)


def package_toml(name):
    """the package.toml of any package: a map, or the package of a monster entry (KeyError: no such package)"""
    p = os.path.join(package_dir(name), 'package.toml')
    if not os.path.exists(p): raise KeyError('no package %r (maps/<name> or monsters/<name>)' % name)
    with open(p, 'rb') as f:
        return tomllib.load(f)


def requires(name):
    """every package that package `name` needs besides the core (its `requires`, theirs first), without itself"""
    out = []
    for r in package_toml(name).get('requires', []):
        for x in requires(r) + [r]:
            if x not in out: out.append(x)
    return out
