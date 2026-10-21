#!/bin/bash
# build.sh : rebuild every Dalamadur output from the dumps (game data: the outputs are gitignored, never published).
#
#   monsters/dalamadur/build.sh [STEP ...]      default: every step, in order
#
# Package monsters/dalamadur/ = Dalamadur, Shah Dalamadur and their tail halves (allocations.toml entries dalamadur,
# shah_dalamadur, dalamadur_tail, shah_dalamadur_tail). Outputs: romfs/ (converted RomFS = its assets package: the four
# monster arcs em090_00 / em090_01 / em091_00 / em091_01 and the theme's opus streams), tools/<arc>_manifest.json,
# gen/<entry>/*.sec (data file sections, once the entries are allocated).
# Inputs: dump/romfs (4U em024 / em083 / em110 / em111 arcs, em_data.arc, m08a01.arc, the stage BGM), dump/base (4U
#   ROM: core effect arcs), dump/m19_unpacked/m19a03 (reference area-colour file) and the GU scratch dir of
#   tools/paths.py (its venv runs the dt step). Work files in dump/converted/dalamadur/. One line per step on stdout,
#   the step's own output in $BUILD_LOGS/<step>.log.
set -u
MON=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$MON/../.." && pwd)
LOGS=${BUILD_LOGS:-$ROOT/dump/build_logs/dalamadur}
T=$MON/tools
mkdir -p "$LOGS"
cd "$ROOT" || exit 1

dt() {        # dtbase / dttune of the four halves on GU Kushala em024_00 (tools/dt_convert.py, unicorn: the GU venv)
    local py em
    py=$(python3 -I -c "import sys; sys.path.insert(0, 'tools'); import paths; print(paths.GU_SCRATCH)")/venv/bin/python
    for em in em024 em083 em110 em111; do
        "$py" tools/dt_convert.py build $em em024_00 "$ROOT/dump/converted/dalamadur/dt_$em" || return 1
    done
}
step() {      # name: command line of one step
    case $1 in
    dt)           dt ;;                                                     # dump/converted/dalamadur/dt_em0NN/
    bgm)          python3 "$T/bgm_dalamadur.py" ;;                          # theme opus + dump/converted/dalamadur STQR
    walk)         python3 tools/walk4u2gu.py convert ;;                     # walk collision SBC (dump/converted/dalamadur/walk)
    arc)          python3 "$T/build_dalamadur_arc.py" ;;                    # the four monster arcs + manifests
    quest)        python3 "$T/build_dalamadur_quest.py" ;;                  # quest 11494 (4U m10709)
    pack)         pack ;;                                 # sections (portdata.py sec_dir) -> gen/<entry>.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
pack() {      # one data file per entry (tools/portdata.py)
    local e
    for e in dalamadur shah_dalamadur dalamadur_tail shah_dalamadur_tail; do
        python3 tools/portdata.py pack $e || return 1
    done
}
ALL=(dt bgm walk arc quest pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
