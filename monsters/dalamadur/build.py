"""build.py : rebuild every Dalamadur output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/dalamadur/build.py [STEP ...]      default: every step, in order (--list: the steps)

Package monsters/dalamadur/ = Dalamadur, Shah Dalamadur and their tail halves (allocations.toml entries dalamadur,
shah_dalamadur, dalamadur_tail, shah_dalamadur_tail). Outputs: romfs/ (converted RomFS = its assets package: the four
monster arcs em090_00 / em090_01 / em091_00 / em091_01, the theme's opus streams, the armor and weapon model
arcs, the weapons' sound arcs; Speartip Crag is the map package maps/speartip_crag), tools/<arc>_manifest.json, gen/<entry>/*.sec (data file
sections, once the entries are allocated).
Inputs: dump/romfs (4U em024 / em083 / em110 / em111 arcs, em_data.arc, m08*.arc, the stage BGM and str_m08
  streams), dump/base (4U ROM: core effect arcs), dump/m19_unpacked/m19a03 (reference area-colour file) and the GU
  scratch dir of tools/paths.py (the .venv runs the dt step; GU m18 files are extracted from its RomFS into
  dump/gu_stage). Work files in dump/converted/dalamadur/, dump/m08_unpacked/. One line per step on stdout, the
  step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import DUMP, py, armor, weapon, weapon_sound, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
ENTRIES = ('dalamadur', 'shah_dalamadur', 'dalamadur_tail', 'shah_dalamadur_tail')
# Rebellion / Riot HR 193 / 194, EX 298 / 299, X 348 / 349, Z 452 / 453 (tools/gear_em090.py)
ARMOR = (193, 194, 298, 299, 348, 349, 452, 453)
# class, 4U arc prefix, HR model, G model (tools/gear_weapons_em090.py): both model arcs, and the line's sound set
# (held by both 4U arcs: the HR model's number = mSrqrNo) from the HR arc
WEAPONS = (('00', 'two', '057', '104'), ('01', 'one', '055', '105'), ('02', 'ham', '059', '107'),
           ('03', 'lan', '036', '091'), ('04', 'hbg', '024', '047'), ('06', 'lbg', '045', '056'),
           ('07', 'swo', '042', '087'), ('08', 'axe', '043', '085'), ('09', 'gun', '049', '090'),
           ('10', 'bow', '025', '084'), ('11', 'sou', '041', '096'), ('12', 'hue', '035', '078'),
           ('13', 'rod', '006', '040'), ('14', 'gaxe', '018', '035'))


def dt():     # dtbase / dttune of the four halves on GU Kushala em024_00 (tools/dt_convert.py, needs unicorn: the .venv)
    return [py('tools/dt_convert.py', 'build', em, 'em024_00', os.path.join(DUMP, 'converted', 'dalamadur', 'dt_' + em),
               '--sensor', venv=True) for em in ('em024', 'em083', 'em110', 'em111')]


def weapons():
    for c, pf, a, b in WEAPONS:
        for m in (a, b):
            yield weapon(ROMFS, int(c), pf + m, m, '--alpha-test-4u', '--anim-4u', '--shield-bone0')
        yield weapon_sound(ROMFS, int(c), pf + a, a)


STEPS = [
    ('dt', 'dump/converted/dalamadur/dt_em0NN/', dt),
    ('bgm', 'theme opus + dump/converted/dalamadur STQR', lambda: [py(os.path.join(T, 'bgm_dalamadur.py'))]),
    ('walk', 'walk collision SBC (dump/converted/dalamadur/walk)', lambda: [py('tools/walk4u2gu.py', 'convert')]),
    ('arc', 'the four monster arcs + manifests', lambda: [py(os.path.join(T, 'build_dalamadur_arc.py'))]),
    ('quest', 'the 6 quests (QUESTS; extdata ones)', lambda: [py(os.path.join(T, 'build_dalamadur_quest.py'))]),
    ('name', 'NAME of both heads (4U names, 5 languages)', lambda: [py(os.path.join(T, 'name_em090.py'))]),
    ('notes', "Hunter's Notes entry 125", lambda: [py(os.path.join(T, 'notes_em090.py'))]),
    ('items', 'appended materials + BUI<rank> per entry', lambda: [py(os.path.join(T, 'items_em090.py'))]),
    ('gather', 'GPTS: meteor scale / head point lists', lambda: [py(os.path.join(T, 'gather_em090.py'))]),
    ('walksec', 'WALK: 4U walk triangles (dala_walk.c)', lambda: [py(os.path.join(T, 'walk_em090.py'))]),
    ('gear', 'armor table records (4 series pairs)', lambda: [py(os.path.join(T, 'gear_em090.py'))]),
    ('armor', 'armor model arcs', lambda: armor(ROMFS, ARMOR)),
    ('weapons', 'weapon model + sound arcs', weapons),
    ('gearw', 'weapon table records (14 lines)', lambda: [py(os.path.join(T, 'gear_weapons_em090.py'))]),
    ('pack', 'sections (portdata.py sec_dir) -> gen/<entry>.bin', lambda: [py('tools/portdata.py', 'pack', e) for e in ENTRIES]),
]

if __name__ == '__main__':
    main('dalamadur', STEPS)
