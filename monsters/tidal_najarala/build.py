"""build.py : rebuild every Tidal Najarala output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/tidal_najarala/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/tidal_najarala/): romfs/ (converted RomFS = its assets package), gen/tidal_najarala.bin (its data file, packed
  from the gen/*.sec sections, tools/portdata.py), tools/em068_01_manifest.json.
Inputs: dump/romfs (4U em093.arc, em_data.arc, quest00 / 01.arc) and the GU RomFS / main of tools/paths.py (the .venv
  runs the dt step). Work files in dump/converted/em093/. One line per step on stdout, the step's own output in
  $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# Najarala Z 432 / 433 (tools/gear_em068_01.py)
ARMOR = (432, 433)
# class, 4U arc prefix, models (tools/gear_weapons_em068_01.py): every model arc of the line. No sound arcs: each 4U arc holds a
# sound set GU ships (checked there)
WEAPONS = (('01', 'one', ('102',)), ('03', 'lan', ('088',)), ('04', 'hbg', ('045',)), ('07', 'swo', ('085',)),
           ('08', 'axe', ('081',)), ('12', 'hue', ('076',)), ('13', 'rod', ('034',)))


def dt():     # dtbase / dttune of 4U em093 and em023 on GU em068_00: the arc step takes GU's file + 4U's differences between
    # them (Tigerstripe's rule: GU's retunes of 4U Najarala and her differences do not overlap, asserted there)
    return [py('tools/dt_convert.py', 'build', em, 'em068_00', os.path.join(DUMP, 'converted', 'em093', 'dt_%s' % em), venv=True)
            for em in ('em093', 'em023')]


def weapons():
    for c, pf, ms in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')


STEPS = [
    ('dt', 'dump/converted/em093/dt_em093/ + dt_em023/', dt),
    ('arc', 'monster arc (carves) + manifest + FILE', lambda: [py(os.path.join(T, 'build_em068_01_arc.py'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em068_01.py'))]),
    ('items', 'TBLA + TXTA (materials) + BUI4', lambda: [py(os.path.join(T, 'items_em068_01.py'))]),
    ('gear', 'armor records (Najarala Z)', lambda: [py(os.path.join(T, 'gear_em068_01.py'))]),
    ('armor', 'armor model arcs (20)', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model + sound arcs', weapons),
    ('gearw', 'weapon table records (7 lines, 17)', lambda: [py(os.path.join(T, 'gear_weapons_em068_01.py'))]),
    ('notes', "Hunter's Notes entry 130", lambda: [py(os.path.join(T, 'notes_em068_01.py'), flags=('-B',))]),
    ('quest', '11368 11453 (4U guild m10822 m11022)',
     lambda: [py(os.path.join(T, 'build_em068_01_quest.py'), flags=('-I', '-B'))]),
    ('pack', 'gen/*.sec -> gen/tidal_najarala.bin', lambda: [py('tools/portdata.py', 'pack', 'tidal_najarala')]),
]

if __name__ == '__main__':
    main('tidal_najarala', STEPS)
