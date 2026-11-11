"""build.py : rebuild the Speartip Crag map package from the dumps (game data: the outputs are gitignored, never
published).

  python3 maps/speartip_crag/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs: maps/speartip_crag/romfs/ (stage folder m29: area + stage arcs, map_com, area maps, area streams); work files
in dump/converted/dalamadur/. Inputs: the 4U ROM, dump/m08_unpacked (made when missing), dump/gu_stage and the GU dumps
of tools/paths.py. Required by Dalamadur (monsters/dalamadur/package.toml requires).
One line per step on stdout, the step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MAP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MAP, '..', '..', 'tools'))
from steps import py, main

T = os.path.join(MAP, 'tools')
STEPS = [
    ('stage', 'stage m29 (alias of 18)', lambda: [py(os.path.join(T, 'build_speartip.py'))]),
    ('ui', 'its area maps + whole map (after stage)', lambda: [py(os.path.join(T, 'build_speartip_ui.py'))]),
]

if __name__ == '__main__':
    main('speartip_crag', STEPS)
