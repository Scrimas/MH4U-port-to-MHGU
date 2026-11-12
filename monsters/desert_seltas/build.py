"""build.py : rebuild every Desert Seltas package output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/desert_seltas/build.py [STEP ...]      default: every step, in order (--list: the steps)

Package monsters/desert_seltas/ = Desert Seltas and Desert Seltas Queen (allocations.toml entries desert_seltas, desert_seltas_queen). Outputs: romfs/
(converted RomFS = its assets package: the monster arcs em076_01 / em069_01, the quests, the armor and weapon model arcs), tools/<arc>_manifest.json,
gen/[<entry>/]*.sec and the entries' data files (tools/portdata.py).
Inputs: dump/romfs (4U em094 / em095 / em025 / em026 arcs, em_data.arc, quest00 / 01.arc), dump/gear_src (4U armor / weapon arcs) and the GU RomFS /
main of tools/paths.py (the .venv runs the dt step). Work files in dump/converted/em094/ and em095/. One line per step on stdout, the step's own output
in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
ENTRIES = ('desert_seltas', 'desert_seltas_queen')
# Seltas Z 430 / 431 (tools/gear_seltas.py). --opaque-tint (notes/porting-guide.md, armor colour): changes nothing here, every tinted
# (type 3) material of the 20 arcs already selects plain FTransparency, so GU draws the armor colour 0x07 in full (checked 2026-11-09)
ARMOR = (430, 431)
# class, 4U arc prefix, models (tools/gear_weapons_seltas.py): the arcs of the lines on their own 4U models; the LBG and GL lines are on GU's own
# models 50 / 80 / 84 (GU's arcs). No sound arcs: each 4U arc holds a sound set GU ships (checked there)
WEAPONS = (('01', 'one', ('101',)), ('02', 'ham', ('105',)), ('10', 'bow', ('082',)), ('11', 'sou', ('093',)))


def dt():     # dtbase / dttune of 4U em094 / em025 on GU em076_00, em095 / em026 on GU em069_00: the arc step takes their 4U values + GU's retunes of the
    # species where theirs equal the species' (tools/build_seltas_arc.py retuned_on)
    return [py('tools/dt_convert.py', 'build', em, gu, os.path.join(DUMP, 'converted', sub, 'dt_%s' % em), venv=True)
            for sub, gu, ems in (('em094', 'em076_00', ('em094', 'em025')), ('em095', 'em069_00', ('em095', 'em026'))) for em in ems]


def weapons():
    for c, pf, ms in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')


STEPS = [
    ('dt', 'dump/converted/em094/dt_*/ + em095/dt_*/', dt),
    ('arc', 'the two monster arcs (carves, routes) + manifests + FILE', lambda: [py(os.path.join(T, 'build_seltas_arc.py'))]),
    ('name', 'NAME of both (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_seltas.py'))]),
    ('items', 'TBLA + TXTA (materials) + BUI4 of both', lambda: [py(os.path.join(T, 'items_seltas.py'))]),
    ('gear', 'armor records (Seltas Z, the Queen\'s entry)', lambda: [py(os.path.join(T, 'gear_seltas.py'))]),
    ('armor', 'armor model arcs (20)', lambda: armor(ROMFS, ARMOR, '--opaque-tint')),
    ('weapons', 'weapon model arcs (4)', weapons),
    ('gearw', 'weapon table records (7 lines, 12 weapons, both entries)', lambda: [py(os.path.join(T, 'gear_weapons_seltas.py'))]),
    ('notes', "Hunter's Notes entries 132 / 133", lambda: [py(os.path.join(T, 'notes_seltas.py'), flags=('-B',))]),
    ('quest', '1068 11138 11139 11140 11374 11373 (4U m01030 caravan, m10805 m10815 m10818 m10924 m10928 guild)',
     lambda: [py(os.path.join(T, 'build_seltas_quest.py'), flags=('-I', '-B'))]),
    ('pack', 'gen/**/*.sec -> the entries\' data files', lambda: [py('tools/portdata.py', 'pack', n) for n in ENTRIES]),
]

if __name__ == '__main__':
    main('desert_seltas', STEPS)
