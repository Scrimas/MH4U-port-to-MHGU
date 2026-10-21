"""bgm_dalamadur.py : Dalamadur's theme (4U stage music of Speartip Crag) -> GU Opus streams + its own battle STQR.

  bgm_dalamadur.py      write monsters/dalamadur/romfs/nativeNX/sound/bgm/battle/wav/bgm_em090_Dalamadur1 / 2.opus
                        and dump/converted/dalamadur/bgm_em090.stqr (packed into em090_00 / em090_01 as
                        sound\\bgm\\battle\\bgm_em090 by build_dalamadur_arc.py)

4U (notes/speartip-crag.md, C): sound\\bgm\\stage\\bgm_st_08.stq sequence 11 -> wav\\bgm_em024.mca (-0.3 dB, phase 1),
sequence 12 -> bgm_em024_2.mca (-0.5 dB, phase 2: from the first arena break). Both Dalamadur and Shah use them (the
4U selector 0x30e16c gives em 24 and 110 the same stage theme). GU level = 4U level + the median delta of the
battle-theme anchors (tools/snd_bgm.py levels), as for Gogmazios. Conversion: tools/snd_bgm.py convert_track.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import alloc, snd_bgm

SRC = os.path.join(ROOT, 'dump/romfs/sound/bgm/stage/wav')         # extracted 4U files (speartip-crag.md)
STQR = os.path.join(ROOT, 'dump/converted/dalamadur/bgm_em090.stqr')
PLANNED_IDS = (0x902, 0x903)     # allocations.toml bgm_ids once the entry exists (Phase 3)
TRACKS = [   # (4U file, GU stream path, 4U dB from bgm_st_08.stq)
    ('bgm_em024.mca', 'sound\\bgm\\battle\\wav\\bgm_em090_Dalamadur1', -0.3),
    ('bgm_em024_2.mca', 'sound\\bgm\\battle\\wav\\bgm_em090_Dalamadur2', -0.5),
]


def main():
    try:
        ids = tuple(alloc.monster('dalamadur')['bgm_ids'])
    except KeyError:
        ids = PLANNED_IDS
    log = []
    med, _ = snd_bgm.levels(log)
    new = []
    for (src, path, db_4u), rid in zip(TRACKS, ids):
        log.append(path)
        opus, ns, ls, le, _ = snd_bgm.convert_track(open(os.path.join(SRC, src), 'rb').read(), log)
        out = os.path.join(MON, 'romfs/nativeNX', path.replace('\\', '/') + '.opus')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(opus)
        new.append((path, len(opus), ns, ls, le, rid, db_4u + med))
    os.makedirs(os.path.dirname(STQR), exist_ok=True)
    snd_bgm.build_battle_stqr(new, log, STQR, 'em090')
    for l in log: print(l)


if __name__ == '__main__':
    main()
