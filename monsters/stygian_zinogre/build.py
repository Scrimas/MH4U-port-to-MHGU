"""build.py : rebuild every Stygian Zinogre output from the dumps (game data: the outputs are gitignored, never
published).

  python3 monsters/stygian_zinogre/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/stygian_zinogre/): romfs/ (converted RomFS = its assets package: the monster arc, the weapon model
  and sound arcs, the Heaven's Mount stage alias m30 (steps stage + stageui; the stage step extracts 4U m05 from
  dump/base into dump/romfs and dump/m05_unpacked when missing)), gen/stygian_zinogre.bin (its data file, packed from
  the gen/*.sec sections, tools/portdata.py), tools/em057_01_manifest.json.
Inputs: dump/romfs (4U em049.arc, em_data.arc), dump/gear_src (4U weapon arcs + MRL index), dump/base (4U ROM: core
  effect arcs, Arena stage arcs), dump/m19_unpacked/m19a03 (reference area-colour file) and the GU scratch dir of
  tools/paths.py (the .venv runs the dt step). Work files in dump/converted/em049/. One line per step on stdout, the
  step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, weapon_sound, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
# Zinogre U 169 / 170, Zinogre Z 438 / 439 (tools/gear_em057_01.py)
ARMOR = (169, 170, 438, 439)
# class, 4U arc prefix, models, sound models (tools/gear_weapons_em057_01.py): every model arc of the line, and the
# sound set of each model whose 4U arc holds its own set (the HBG's: GU's 019). lan054 / lbg030 need the converter's
# sphere-map fallback (notes/weapons.md 4.)
WEAPONS = (('00', 'two', ('038',), ('038',)), ('01', 'one', ('042',), ('042',)), ('02', 'ham', ('046',), ('046',)),
           ('03', 'lan', ('054',), ('054',)), ('04', 'hbg', ('046',), ()), ('06', 'lbg', ('030',), ('030',)),
           ('07', 'swo', ('036', '082'), ('036', '082')), ('08', 'axe', ('038',), ('038',)),
           ('09', 'gun', ('026',), ('026',)), ('10', 'bow', ('034', '081'), ('034', '081')),
           ('11', 'sou', ('040',), ('040',)), ('12', 'hue', ('028',), ('028',)))


def dt():     # dtbase / dttune of 4U em048 and em049 on GU em057_00 (tools/dt_convert.py, needs unicorn: the .venv)
    return [py('tools/dt_convert.py', 'build', em, 'em057_00', os.path.join(DUMP, 'converted', 'em049', 'dt_' + em),
               venv=True) for em in ('em048', 'em049')]


def weapons():
    for c, pf, ms, ss in WEAPONS:
        for m in ms:
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')
        for m in ss:
            yield weapon_sound(ROMFS, int(c), pf + m, m)


STEPS = [
    ('dt', 'dump/converted/em049/dt_em0NN/', dt),
    ('stage', "Heaven's Mount: stage m30 (alias of 24)", lambda: [py(os.path.join(T, 'build_heavens_mount.py'), flags=('-B',))]),
    ('stageui', 'its area maps + whole map (after stage)', lambda: [py(os.path.join(T, 'build_heavens_mount_ui.py'), flags=('-I', '-B'))]),
    ('arc', 'monster arc + manifest + FILE section', lambda: [py(os.path.join(T, 'build_em057_01_arc.py'))]),
    ('quest', 'his quests (QUESTS: all 11)', lambda: [py(os.path.join(T, 'build_em057_01_quest.py'), flags=('-I', '-B'))]),
    ('name', 'NAME (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em057_01.py'))]),
    ('notes', "Hunter's Notes entry 127", lambda: [py(os.path.join(T, 'notes_em057_01.py'), flags=('-B',))]),
    ('stagename', "board name of Heaven's Mount (TXTA)", lambda: [py(os.path.join(T, 'stage_name_em057_01.py'), flags=('-B',))]),
    ('items', 'TBLA + TXTA (materials) + BUI2 / BUI4', lambda: [py(os.path.join(T, 'items_em057_01.py'))]),
    ('gear', 'armor records (Zinogre U, Zinogre Z)', lambda: [py(os.path.join(T, 'gear_em057_01.py'))]),
    ('armor', 'armor model arcs (40)', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model + sound arcs', weapons),
    ('gearw', 'weapon table records (12 Brimstren lines)', lambda: [py(os.path.join(T, 'gear_weapons_em057_01.py'))]),
    ('pack', 'gen/*.sec -> gen/stygian_zinogre.bin', lambda: [py('tools/portdata.py', 'pack', 'stygian_zinogre')]),
]

if __name__ == '__main__':
    main('stygian_zinogre', STEPS)
