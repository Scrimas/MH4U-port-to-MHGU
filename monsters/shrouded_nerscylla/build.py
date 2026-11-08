"""build.py : rebuild every Shrouded Nerscylla output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/shrouded_nerscylla/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/shrouded_nerscylla/): romfs/ (converted RomFS = its assets package), gen/shrouded_nerscylla.bin (its data file, packed
  from the gen/*.sec sections, tools/portdata.py), tools/em070_01_manifest.json.
Inputs: dump/romfs (4U em096.arc, em027.arc, em_data.arc, quest00 / 01.arc) and the GU RomFS / main of tools/paths.py (the .venv
  runs the dt step). Work files in dump/converted/em096/. One line per step on stdout, the step's own output in
  $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# Nerscylla Z 434 / 435 (tools/gear_em070_01.py)
ARMOR = (434, 435)
# class, 4U arc prefix, models (tools/gear_weapons_em070_01.py): every model arc of the line. No sound arcs: each 4U arc holds a
# sound set GU ships (checked there)
WEAPONS = (('00', 'two', ('106',)), ('01', 'one', ('106',)), ('02', 'ham', ('108',)), ('04', 'hbg', ('049',)), ('07', 'swo', ('090',)),
           ('09', 'gun', ('092',)), ('10', 'bow', ('085',)), ('13', 'rod', ('042',)), ('14', 'gaxe', ('036',)))


def dt():     # dtbase / dttune of 4U em096 and em027 on GU em070_00: the arc step takes GU's file + 4U's differences between
    # them (Tigerstripe's rule: GU's retunes of 4U Nerscylla and her differences do not overlap, asserted there)
    return [py('tools/dt_convert.py', 'build', em, 'em070_00', os.path.join(DUMP, 'converted', 'em096', 'dt_%s' % em), venv=True)
            for em in ('em096', 'em027')]


def weapons():
    for c, pf, ms in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')


STEPS = [
    ('dt', 'dump/converted/em096/dt_em096/ + dt_em027/', dt),
    ('arc', 'monster arc (carves) + manifest + FILE', lambda: [py(os.path.join(T, 'build_em070_01_arc.py'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em070_01.py'))]),
    ('items', 'TBLA + TXTA (materials) + BUI4', lambda: [py(os.path.join(T, 'items_em070_01.py'))]),
    ('gear', 'armor records (Nerscylla Z)', lambda: [py(os.path.join(T, 'gear_em070_01.py'))]),
    ('armor', 'armor model arcs (20)', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model arcs', weapons),
    ('gearw', 'weapon table records (9 lines, 20)', lambda: [py(os.path.join(T, 'gear_weapons_em070_01.py'))]),
    ('notes', "Hunter's Notes entry 131", lambda: [py(os.path.join(T, 'notes_em070_01.py'), flags=('-B',))]),
    ('quest', '1062 11370 11371 (4U m01014 caravan, m10902 m10914 guild)',
     lambda: [py(os.path.join(T, 'build_em070_01_quest.py'), flags=('-I', '-B'))]),
    ('pack', 'gen/*.sec -> gen/shrouded_nerscylla.bin', lambda: [py('tools/portdata.py', 'pack', 'shrouded_nerscylla')]),
]

if __name__ == '__main__':
    main('shrouded_nerscylla', STEPS)
