"""build.py : rebuild every Gogmazios output from the dumps (game data: the outputs are gitignored, never published).

  python3 monsters/gogmazios/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs (monsters/gogmazios/): romfs/ (converted RomFS = its assets package), gen/gogmazios.bin (its data file,
  packed from the gen/*.sec sections, tools/portdata.py), module/em089_slot75.inc, tools/em089_manifest.json;
  module/gear_hooks.txt (core); work files in dump/converted/.
Inputs: dump/ (4U ROM dump/base/*.3ds, extracted dump/romfs + dump/exefs_v11, dump/m19_unpacked, dump/gu_stage,
  dump/converted/em089/{dtbase,dttune}.bin from tools/dt_convert.py in the unicorn venv), dump/gear_src/ (4U armor
  and weapon arcs + the MRL template indexes of tools/armor4u2gu.py / weapon4u2gu.py `index`), and the GU scratch
  dir of tools/paths.py. One line per step on stdout, the step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MON = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MON, '..', '..', 'tools'))
from steps import GS, py, armor, weapon, main

T = os.path.join(MON, 'tools')
ROMFS = os.path.join(MON, 'romfs')
WEAPONS = (('00', 'two097'), ('01', 'one097'), ('02', 'ham099'), ('03', 'lan082'), ('04', 'hbg040'), ('06', 'lbg047'),
           ('07', 'swo079'), ('08', 'axe077'), ('09', 'gun082'), ('10', 'bow075'), ('11', 'sou087'), ('12', 'hue071'),
           ('13', 'rod025'), ('14', 'gaxe027'))   # class, 4U arc name (model = its last 3 digits)

STEPS = [
    ('snd_bgm', 'BGM opus + STQRs (dump/converted)', lambda: [py('tools/snd_bgm.py', 'all')]),
    ('snd_area', 'arena area sounds (dump/converted)', lambda: [py('tools/snd_area.py', 'convert')]),
    ('arc', 'monster arc + manifest + FILE section', lambda: [py(os.path.join(T, 'build_em089_arc.py'), '--cmdtbl', 'gog')]),
    ('stage', 'Battlequarters alias arcs (m28)', lambda: [py('tools/stage4u2gu.py', 'alias', flags=('-I',), timeout=1800)]),
    ('mapui', "area + whole maps (reads stage's m28.arc)", lambda: [py('tools/mapui4u2gu.py', flags=('-I',), timeout=1200)]),
    ('ui', 'name (icon: tools/ui_icons.py)', lambda: [py(os.path.join(T, 'ui_em089.py'), flags=('-I',))]),
    ('quest1', '11491 (4U m11014)', lambda: [py(os.path.join(T, 'build_gog_quest.py'))]),
    ('quest2', '11492', lambda: [py(os.path.join(T, 'build_gog_quest.py'), '--source', 'm11035')]),
    ('slot75', 'slot 75 include', lambda: [py(os.path.join(T, 'em089_slot75_gen.py'))]),
    ('items', 'appended items', lambda: [py(os.path.join(T, 'items_em089.py'))]),
    ('gear', 'armor table records', lambda: [py(os.path.join(T, 'gear_em089.py'))]),
    ('gear_weapons', 'weapon table records', lambda: [py(os.path.join(T, 'gear_weapons_em089.py'))]),
    ('notes', "Hunter's Notes entry", lambda: [py(os.path.join(T, 'notes_em089.py'))]),
    ('armor', 'armor model arcs (352 / 353)', lambda: armor(ROMFS, (352, 353))),
    ('weapons', 'weapon model arcs', lambda: [weapon(ROMFS, int(c), a, a[-3:]) for c, a in WEAPONS]),
    ('wsnd', 'weapon sound arcs', lambda: [py('tools/wsnd4u2gu.py', 'gogma', os.path.join(GS, 'weapons', '4u', 'data'))]),
    ('pack', 'gen/*.sec -> gen/gogmazios.bin', lambda: [py('tools/portdata.py', 'pack', 'gogmazios')]),
]

if __name__ == '__main__':
    main('gogmazios', STEPS)
