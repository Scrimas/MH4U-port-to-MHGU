"""build.py : rebuild the Battlequarters map package from the dumps (game data: the outputs are gitignored, never
published).

  python3 maps/battlequarters/build.py [STEP ...]      default: every step, in order (--list: the steps)

Outputs: maps/battlequarters/romfs/ (stage folder m28: area + stage arcs, map_com, area maps, area streams); work files
in dump/converted/. Inputs: the 4U ROM (dump/base/*.3ds) and extracted dump/romfs + dump/exefs_v11, dump/m19_unpacked,
dump/gu_stage and the GU dumps of tools/paths.py. Required by Gogmazios (monsters/gogmazios/package.toml requires).
One line per step on stdout, the step's own output in $BUILD_LOGS/<step>.log (tools/steps.py).
"""
import os, sys
MAP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MAP, '..', '..', 'tools'))
from steps import py, main

STEPS = [
    ('snd_bgm', 'area streams + camp jingle, m28d STQR', lambda: [py('tools/snd_bgm.py', 'stage')]),
    ('snd_area', 'arena area sounds (dump/converted)', lambda: [py('tools/snd_area.py', 'convert')]),
    ('stage', 'alias arcs (m28)', lambda: [py('tools/stage4u2gu.py', 'alias', flags=('-I',), timeout=1800)]),
    ('mapui', "area + whole maps (reads stage's m28.arc)", lambda: [py('tools/mapui4u2gu.py', flags=('-I',), timeout=1200)]),
]

if __name__ == '__main__':
    main('battlequarters', STEPS)
