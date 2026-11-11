"""build.py : rebuild every Black Gravios output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/black_gravios/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/black_gravios/): romfs/ (converted RomFS = its assets package), gen/black_gravios.bin (its data
  file, packed from the gen/*.sec sections, tools/portdata.py), tools/em005_01_manifest.json.
Inputs: dump/romfs (4U em040.arc, em041.arc, em_data.arc, quest00 / 01.arc) and the GU RomFS / main of
  tools/paths.py (the .venv runs the dt step). Work files in dump/converted/em041/. One line per step on stdout, the
  step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, weapon_sound, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# Gravios U 185 / 186, Gravios Z 394 / 395 (tools/gear_em005_01.py)
ARMOR = (185, 186, 394, 395)
# class, 4U arc prefix, models, sound models (tools/gear_weapons_em005_01.py): every model arc of the line, and the
# sound set of each model whose 4U arc holds its own set (SnS 103: GU's 009; DB 094 holds 008's set)
WEAPONS = (('01', 'one', ('103',), ()), ('02', 'ham', ('029',), ('029',)), ('03', 'lan', ('047', '100'), ('047', '100')),
           ('04', 'hbg', ('007',), ('007',)), ('09', 'gun', ('027',), ('027',)), ('11', 'sou', ('008', '094'), ('008',)))


def dt():     # dtbase / dttune of 4U em040 and em041 on GU em005_00 (tools/dt_convert.py, needs unicorn: the .venv)
    return [py('tools/dt_convert.py', 'build', em, 'em005_00', os.path.join(DUMP, 'converted', 'em041', 'dt_' + em),
               venv=True) for em in ('em040', 'em041')]


def weapons():
    for c, pf, ms, ss in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')
        for m in ss:
            yield weapon_sound(ROMFS, int(c), pf + m, m)


STEPS = [
    ('dt', 'dump/converted/em041/dt_em04N/', dt),
    ('arc', 'monster arc (carves) + manifest + FILE', lambda: [py(os.path.join(T, 'build_em005_01_arc.py'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em005_01.py'))]),
    ('items', 'TBLA + TXTA (materials) + BUI2 / BUI4', lambda: [py(os.path.join(T, 'items_em005_01.py'))]),
    ('gear', 'armor records (Gravios U, Gravios Z)', lambda: [py(os.path.join(T, 'gear_em005_01.py'))]),
    ('armor', 'armor model arcs (40)', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model + sound arcs', weapons),
    ('gearw', 'weapon table records (6 lines, 18)', lambda: [py(os.path.join(T, 'gear_weapons_em005_01.py'))]),
    ('notes', "Hunter's Notes entry 128", lambda: [py(os.path.join(T, 'notes_em005_01.py'), flags=('-B',))]),
    ('quest', '10780 11430 10781 1025 1056 10782 10783 11451 (4U m10611 m10923 m10601 m00911 m00902 m10606 m10615 '
              'm10927)', lambda: [py(os.path.join(T, 'build_em005_01_quest.py'), flags=('-I', '-B'))]),
    ('pack', 'gen/*.sec -> gen/black_gravios.bin', lambda: [py('tools/portdata.py', 'pack', 'black_gravios')]),
]

if __name__ == '__main__':
    main('black_gravios', STEPS)
