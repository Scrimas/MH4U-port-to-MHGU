"""build.py : rebuild the Heaven's Mount map package from the dumps (game data: the outputs are gitignored, never
published).

  python3 maps/heavens_mount/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs: maps/heavens_mount/romfs/ (stage folder m30: area + stage arcs, map_com, area maps, area streams; its Harvest
Tours: tools/tour4u.py, package.toml [[tour]]); work files
in dump/converted/em049/. Inputs: the 4U ROM, dump/m05_unpacked (made when missing), dump/gu_stage and the GU dumps of
tools/paths.py. Required by Stygian Zinogre (monsters/stygian_zinogre/package.toml requires).
One line per step on stdout, the step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MAP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MAP, '..', '..', 'tools'))
from steps import py, main

T = os.path.join(MAP, 'tools')
STEPS = [
    ('stage', 'stage m30 (alias of 24)', lambda: [py(os.path.join(T, 'build_heavens_mount.py'), flags=('-B',))]),
    ('ui', 'its area maps + whole map (after stage)', lambda: [py(os.path.join(T, 'build_heavens_mount_ui.py'),
                                                                  flags=('-I', '-B'))]),
    ('tours', 'Harvest Tours 841 10547 11372 (4U q806 q10515 q10907)',
     lambda: [py('tools/tour4u.py', 'heavens_mount', flags=('-B',))]),
]

if __name__ == '__main__':
    main('heavens_mount', STEPS)
