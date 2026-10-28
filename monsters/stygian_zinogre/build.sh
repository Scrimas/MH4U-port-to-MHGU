#!/bin/bash
# build.sh : rebuild every Stygian Zinogre output from the dumps (game data: the outputs are gitignored, never
# published).
#
#   monsters/stygian_zinogre/build.sh [STEP ...]      default: every step, in order
#
# Outputs (monsters/stygian_zinogre/): romfs/ (converted RomFS = its assets package: the monster arc, the weapon model
#   and sound arcs, the Heaven's Mount stage alias m30 (steps stage + stageui; the stage step extracts 4U m05 from
#   dump/base into dump/romfs and dump/m05_unpacked when missing)), gen/stygian_zinogre.bin (its data file, packed from the gen/*.sec sections, tools/portdata.py),
#   tools/em057_01_manifest.json.
# Inputs: dump/romfs (4U em049.arc, em_data.arc), dump/gear_src (4U weapon arcs + MRL index), dump/base (4U ROM: core
#   effect arcs, Arena stage arcs), dump/m19_unpacked/m19a03 (reference area-colour file) and the GU scratch dir of tools/paths.py (its venv runs the
#   dt step). Work files in dump/converted/em049/. One line per step on stdout, the step's own output in
#   $BUILD_LOGS/<step>.log.
set -u
MON=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$MON/../.." && pwd)
LOGS=${BUILD_LOGS:-$ROOT/dump/build_logs/stygian_zinogre}
T=$MON/tools
mkdir -p "$LOGS"
cd "$ROOT" || exit 1

dt() {        # dtbase / dttune of 4U em048 and em049 on GU em057_00 (tools/dt_convert.py, unicorn: the GU venv)
    local py em
    py=$(python3 -I -c "import sys; sys.path.insert(0, 'tools'); import paths; print(paths.GU_SCRATCH)")/venv/bin/python
    for em in em048 em049; do
        "$py" tools/dt_convert.py build $em em057_00 "$ROOT/dump/converted/em049/dt_$em" || return 1
    done
}
GS=$ROOT/dump/gear_src      # 4U armor / weapon arcs (extracted with tools/ctr.py x) + MRL indexes
armor() {     # Zinogre U 169 / 170, Zinogre Z 438 / 439 (tools/gear_em057_01.py), m and f
    local s n p
    for s in m f; do for n in 169 170 438 439; do for p in helm arm wst leg body; do
        mkdir -p "$MON/romfs/nativeNX/arc/player/com/$s/$n"
        python3 tools/armor4u2gu.py convert "$GS/armor/4u/data/pl_${s}_$p$n.arc" \
            "$MON/romfs/nativeNX/arc/player/com/$s/$n/$p.arc" "$GS/armor/out/mrl_index.pkl" || return 1
    done; done; done
}
weapons() {   # class:4U arc prefix:models:sound models (tools/gear_weapons_em057_01.py): every model arc of the line,
    local spec nn pf ms ss m   # and the sound set of each model whose 4U arc holds its own set (the HBG's: GU's 019)
    for spec in 00:two:038:038 01:one:042:042 02:ham:046:046 03:lan:054:054 04:hbg:046:- 06:lbg:030:030 \
                07:swo:036,082:036,082 08:axe:038:038 09:gun:026:026 10:bow:034,081:034,081 11:sou:040:040 \
                12:hue:028:028; do
        IFS=: read -r nn pf ms ss <<< "$spec"
        mkdir -p "$MON/romfs/nativeNX/arc/weapon/w$nn/snd"
        for m in ${ms//,/ }; do   # lan054 / lbg030 need the converter's sphere-map fallback (notes/weapons.md 4.)
            python3 tools/weapon4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$pf$m.arc" \
                "$MON/romfs/nativeNX/arc/weapon/w$nn/$m.arc" "$GS/weapons/out/wpn_mrl_index.pkl" --alpha-test-4u --anim-4u \
                --shield-bone0 || return 1
        done
        [ "$ss" = - ] && continue
        for m in ${ss//,/ }; do
            python3 tools/wsnd4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$pf$m.arc" \
                "$MON/romfs/nativeNX/arc/weapon/w$nn/snd/$m.arc" || return 1
        done
    done
}
step() {      # name: command line of one step
    case $1 in
    dt)           dt ;;                                                     # dump/converted/em049/dt_em0NN/
    stage)        python3 -B "$T/build_heavens_mount.py" ;;                # Heaven's Mount: stage m30 (alias of 24)
    stageui)      python3 -I -B "$T/build_heavens_mount_ui.py" ;;          # its area maps + whole map (after stage)
    arc)          python3 "$T/build_em057_01_arc.py" ;;                    # monster arc + manifest + FILE section
    name)         python3 "$T/name_em057_01.py" ;;                         # NAME (4U names, 5 languages)
    items)        python3 "$T/items_em057_01.py" ;;                        # TBLA + TXTA (materials) + BUI2 / BUI4
    gear)         python3 "$T/gear_em057_01.py" ;;                         # armor records (Zinogre U, Zinogre Z)
    weapons)      weapons ;;                                                # weapon model + sound arcs
    gearw)        python3 "$T/gear_weapons_em057_01.py" ;;                 # weapon table records (12 Brimstren lines)
    armor)        armor ;;                                                  # armor model arcs (40)
    quest)        python3 -I -B "$T/build_em057_01_quest.py" ;;            # his quests (QUESTS: all 11)
    notes)        python3 -B "$T/notes_em057_01.py" ;;                     # Hunter's Notes entry 127
    stagename)    python3 -B "$T/stage_name_em057_01.py" ;;                # board name of Heaven's Mount (TXTA)
    pack)         python3 tools/portdata.py pack stygian_zinogre ;;        # gen/*.sec -> gen/stygian_zinogre.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
ALL=(dt stage stageui arc quest name notes stagename items gear armor weapons gearw pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
