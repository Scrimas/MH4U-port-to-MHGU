"""paths.py : where the inputs live and where a monster's outputs go (one place for every tool).

Inputs outside this repo (override with the environment for another machine / CI):
  GU_SCRATCH   MHGU_Editor scratch dir: main.asm, mem.bin (GU 1.4 main, flat), base_romfs.bin, py/ helpers
  GU_EDITOR    MHGU_Editor checkout (tools/ helpers, data/monster-index.csv)
Repo layout: tools/ + module/ + notes/ = shared core; monsters/<name>/{module,tools,notes} = one monster,
monsters/<name>/{gen,romfs} = its generated tables and converted RomFS (gitignored: game data).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
DUMP = os.path.join(ROOT, 'dump')

GU_EDITOR = os.environ.get('GU_EDITOR', '/home/scrimas/Projects/MHGU_Editor')
GU_SCRATCH = os.environ.get('GU_SCRATCH', os.path.join(GU_EDITOR, 'scratch'))
GU_PY = os.path.join(GU_SCRATCH, 'py')               # romfs.py, asm.py, arc.py ... (MHGU_Editor)
GU_EDITOR_TOOLS = os.path.join(GU_EDITOR, 'tools')
GU_ROMFS = os.path.join(GU_SCRATCH, 'base_romfs.bin')
GU_MAIN = os.path.join(GU_SCRATCH, 'mem.bin')        # MHGU 1.4 main, flat


def monster(name):
    """monsters/<name>"""
    return os.path.join(ROOT, 'monsters', name)


def romfs(name):
    """monsters/<name>/romfs: mirror of the game RomFS (nativeNX/...)"""
    return os.path.join(monster(name), 'romfs')


def gen(name):
    """monsters/<name>/gen: generated tables included by the module build"""
    return os.path.join(monster(name), 'gen')
