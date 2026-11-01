"""build.py : rebuild every Tigerstripe Zamtrios output from the dumps (game data: the outputs are gitignored, never
published).

  python3 monsters/tigerstripe_zamtrios/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/tigerstripe_zamtrios/): romfs/ (converted RomFS = its assets package), gen/tigerstripe_zamtrios.bin
  (its data file, packed from the gen/*.sec sections, tools/portdata.py), tools/em067_01_manifest.json.
Inputs: dump/romfs (4U em092.arc, em_data.arc), dump/base (4U ROM: core effect arcs, Dunes stage arcs),
  dump/m19_unpacked/m19a03 (reference area-colour file) and the GU scratch dir of tools/paths.py (the .venv runs the
  dt step). Work files in dump/converted/em092/. One line per step on stdout, the step's own output in
  $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# class, 4U arc name (model = its last 3 digits); sounds = GU's sets (tools/gear_em067_01.py SRQR)
WEAPONS = (('01', 'one104'), ('02', 'ham106'), ('03', 'lan090'), ('08', 'axe084'), ('09', 'gun089'), ('10', 'bow083'),
           ('11', 'sou095'), ('13', 'rod038'), ('14', 'gaxe034'))


def dt():     # dtbase / dttune of 4U em022 and em092 on GU em067_00 (tools/dt_convert.py, needs unicorn: the .venv)
    return [py('tools/dt_convert.py', 'build', em, 'em067_00', os.path.join(DUMP, 'converted', 'em092', 'dt_' + em),
               venv=True) for em in ('em022', 'em092')]


STEPS = [
    ('dt', 'dump/converted/em092/dt_em0NN/', dt),
    ('arc', 'monster arc + manifest + FILE section', lambda: [py(os.path.join(T, 'build_em067_01_arc.py'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em067_01.py'))]),
    ('notes', "Hunter's Notes entry 124", lambda: [py(os.path.join(T, 'notes_em067_01.py'))]),
    ('items', 'ITEM (materials) + BUI (break rewards)', lambda: [py(os.path.join(T, 'items_em067_01.py'))]),
    ('quest', '11493 (4U m10821)', lambda: [py(os.path.join(T, 'build_em067_01_quest.py'))]),
    ('gear', 'armor + weapon table records', lambda: [py(os.path.join(T, 'gear_em067_01.py'))]),
    ('armor', 'armor model arcs (Zamtrios Z 436 / 437)', lambda: armor(ROMFS, (436, 437))),
    ('weapons', 'weapon model arcs', lambda: [weapon(ROMFS, int(c), a, a[-3:]) for c, a in WEAPONS]),
    ('pack', 'gen/*.sec -> gen/tigerstripe_zamtrios.bin', lambda: [py('tools/portdata.py', 'pack', 'tigerstripe_zamtrios')]),
]

if __name__ == '__main__':
    main('tigerstripe_zamtrios', STEPS)
