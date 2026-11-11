"""build.py : rebuild every Monoblos output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/monoblos/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/monoblos/): romfs/ (converted RomFS = its assets package), gen/monoblos.bin (its data file, packed
  from the gen/*.sec sections, tools/portdata.py), tools/em007_01_manifest.json.
Inputs: dump/romfs (4U em101.arc, em_data.arc, quest00 / 01.arc) and the GU RomFS / main of tools/paths.py (the .venv
  runs the dt step). Work files in dump/converted/em101/. One line per step on stdout, the step's own output in
  $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, weapon_sound, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# Mono S 368 / 369, Mono X 370 / 371 (tools/gear_em007_01.py)
ARMOR = (368, 369, 370, 371)
# class, 4U arc prefix, models, sound models (tools/gear_weapons_em007_01.py): every model arc of the line, and the
# sound set of each model (each 4U arc holds its own model's set, checked there)
WEAPONS = (('00', 'two', ('114',), ('114',)), ('01', 'one', ('115',), ('115',)), ('03', 'lan', ('097',), ('097',)),
           ('04', 'hbg', ('062',), ('062',)), ('07', 'swo', ('097',), ('097',)))


def dt():     # dtbase / dttune of 4U em101 and em099 on GU em007_00, GU's AI distance ranges kept: em099's shows GU's
    # retunes of 4U Diablos, which the arc step carries over to his values (GU's balance); then em101 with his own 4U
    # distance rows, which his AI table's distance checks name (the arc step moves the retunes into it)
    return [py('tools/dt_convert.py', 'build', em, 'em007_00',
               os.path.join(DUMP, 'converted', 'em101', 'dt_%s_gu_ranges' % em), '--keep-ranges', venv=True)
            for em in ('em101', 'em099')] + \
           [py('tools/dt_convert.py', 'build', 'em101', 'em007_00', os.path.join(DUMP, 'converted', 'em101', 'dt_em101'),
               venv=True)]


def weapons():
    for c, pf, ms, ss in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')
        for m in ss:
            yield weapon_sound(ROMFS, int(c), pf + m, m)


STEPS = [
    ('dt', 'dump/converted/em101/dt_em101_gu_ranges/ + dt_em099_gu_ranges/ + dt_em101/', dt),
    ('arc', 'monster arc (carves) + manifest + FILE', lambda: [py(os.path.join(T, 'build_em007_01_arc.py'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em007_01.py'))]),
    ('items', 'TBLA + TXTA (materials) + BUI2 / BUI4', lambda: [py(os.path.join(T, 'items_em007_01.py'))]),
    ('gear', 'armor records (Mono S, Mono X)', lambda: [py(os.path.join(T, 'gear_em007_01.py'))]),
    ('armor', 'armor model arcs (40)', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model + sound arcs', weapons),
    ('gearw', 'weapon table records (5 lines, 14)', lambda: [py(os.path.join(T, 'gear_weapons_em007_01.py'))]),
    ('notes', "Hunter's Notes entry 129", lambda: [py(os.path.join(T, 'notes_em007_01.py'), flags=('-B',))]),
    ('quest', '1057 1058 1059 10784 10785 11452 (4U m00801 m00818 m01018)',
     lambda: [py(os.path.join(T, 'build_em007_01_quest.py'), flags=('-I', '-B'))]),
    ('pack', 'gen/*.sec -> gen/monoblos.bin', lambda: [py('tools/portdata.py', 'pack', 'monoblos')]),
]

if __name__ == '__main__':
    main('monoblos', STEPS)
