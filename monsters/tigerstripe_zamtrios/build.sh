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
GS=$ROOT/dump/gear_src      # 4U armor / weapon arcs (armor 436 / 437 extracted with tools/ctr.py x) + MRL indexes
armor() {     # Zamtrios Z, Blademaster 436 / Gunner 437, male and female
    local s n p
    for s in m f; do for n in 436 437; do for p in helm arm wst leg body; do
        mkdir -p "$MON/romfs/nativeNX/arc/player/com/$s/$n"
        python3 tools/armor4u2gu.py convert "$GS/armor/4u/data/pl_${s}_$p$n.arc" \
            "$MON/romfs/nativeNX/arc/player/com/$s/$n/$p.arc" "$GS/armor/out/mrl_index.pkl" || return 1
    done; done; done
}
weapons() {   # class:4U arc name (model = its last 3 digits); sounds = GU's sets (tools/gear_em067_01.py SRQR)
    local spec nn arc num
    for spec in 01:one104 02:ham106 03:lan090 08:axe084 09:gun089 10:bow083 11:sou095 13:rod038 14:gaxe034; do
        nn=${spec%%:*}; arc=${spec##*:}; num=${arc: -3}
        mkdir -p "$MON/romfs/nativeNX/arc/weapon/w$nn"
        python3 tools/weapon4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$arc.arc" \
            "$MON/romfs/nativeNX/arc/weapon/w$nn/$num.arc" "$GS/weapons/out/wpn_mrl_index.pkl" || return 1
    done
}
step() {      # name: command line of one step
    case $1 in
    dt)           dt ;;                                                     # dump/converted/em092/dt_em0NN/
    arc)          python3 "$T/build_em067_01_arc.py" ;;                    # monster arc + manifest + FILE section
    name)         python3 "$T/name_em067_01.py" ;;                         # NAME (4U names, 5 languages)
    notes)        python3 "$T/notes_em067_01.py" ;;                        # Hunter's Notes entry 124
    items)        python3 "$T/items_em067_01.py" ;;                        # ITEM (materials) + BUI (break rewards)
    quest)        python3 "$T/build_em067_01_quest.py" ;;                  # 11493 (4U m10821)
    gear)         python3 "$T/gear_em067_01.py" ;;                         # armor + weapon table records
    armor)        armor ;;                                                  # armor model arcs
    weapons)      weapons ;;                                                # weapon model arcs
    pack)         python3 tools/portdata.py pack tigerstripe_zamtrios ;;   # gen/*.sec -> gen/tigerstripe_zamtrios.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
ALL=(dt arc name notes items quest gear armor weapons pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
