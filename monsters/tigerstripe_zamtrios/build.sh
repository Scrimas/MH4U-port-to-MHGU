#!/bin/bash
# build.sh : rebuild every Tigerstripe Zamtrios output from the dumps (game data: the outputs are gitignored, never
# published).
#
#   monsters/tigerstripe_zamtrios/build.sh [STEP ...]      default: every step, in order
#
# Outputs (monsters/tigerstripe_zamtrios/): romfs/ (converted RomFS = its assets package), gen/tigerstripe_zamtrios.bin
#   (its data file, packed from the gen/*.sec sections, tools/portdata.py), tools/em067_01_manifest.json.
# Inputs: dump/romfs (4U em092.arc, em_data.arc), dump/base (4U ROM: core effect arcs, Dunes stage arcs),
#   dump/m19_unpacked/m19a03 (reference area-colour file) and the GU scratch dir of tools/paths.py (its venv runs the
#   dt step). Work files in dump/converted/em092/. One line per step on stdout, the step's own output in
#   $BUILD_LOGS/<step>.log.
set -u
MON=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$MON/../.." && pwd)
LOGS=${BUILD_LOGS:-$ROOT/dump/build_logs/tigerstripe_zamtrios}
T=$MON/tools
mkdir -p "$LOGS"
cd "$ROOT" || exit 1

dt() {        # dtbase / dttune of 4U em022 and em092 on GU em067_00 (tools/dt_convert.py, unicorn: the GU venv)
    local py em
    py=$(python3 -I -c "import sys; sys.path.insert(0, 'tools'); import paths; print(paths.GU_SCRATCH)")/venv/bin/python
    for em in em022 em092; do
        "$py" tools/dt_convert.py build $em em067_00 "$ROOT/dump/converted/em092/dt_$em" || return 1
    done
}
step() {      # name: command line of one step
    case $1 in
    dt)           dt ;;                                                     # dump/converted/em092/dt_em0NN/
    arc)          python3 "$T/build_em067_01_arc.py" ;;                    # monster arc + manifest + FILE section
    name)         python3 "$T/name_em067_01.py" ;;                         # NAME (4U names, 5 languages)
    notes)        python3 "$T/notes_em067_01.py" ;;                        # Hunter's Notes entry 124
    pack)         python3 tools/portdata.py pack tigerstripe_zamtrios ;;   # gen/*.sec -> gen/tigerstripe_zamtrios.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
ALL=(dt arc name notes pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
