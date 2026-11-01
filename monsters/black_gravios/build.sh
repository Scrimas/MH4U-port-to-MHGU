#!/bin/bash
# build.sh : rebuild every Black Gravios output from the dumps (game data: the outputs are gitignored, never published).
#
#   monsters/black_gravios/build.sh [STEP ...]      default: every step, in order
#
# Outputs (monsters/black_gravios/): romfs/ (converted RomFS = its assets package), gen/black_gravios.bin (its data
#   file, packed from the gen/*.sec sections, tools/portdata.py), tools/em005_01_manifest.json.
# Inputs: dump/romfs (4U em040.arc, em041.arc, em_data.arc, quest00 / 01.arc) and the GU RomFS / main of
#   tools/paths.py (its venv runs the dt step). Work files in dump/converted/em041/. One line per step on stdout, the
#   step's own output in $BUILD_LOGS/<step>.log.
set -u
MON=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$MON/../.." && pwd)
LOGS=${BUILD_LOGS:-$ROOT/dump/build_logs/black_gravios}
T=$MON/tools
mkdir -p "$LOGS"
cd "$ROOT" || exit 1

dt() {        # dtbase / dttune of 4U em040 and em041 on GU em005_00 (tools/dt_convert.py, unicorn: the venv)
    local py em
    py=$ROOT/.venv/bin/python; [ -x "$py" ] || py=python3     # needs unicorn (requirements.txt)
    for em in em040 em041; do
        "$py" tools/dt_convert.py build $em em005_00 "$ROOT/dump/converted/em041/dt_$em" || return 1
    done
}
GS=$ROOT/dump/gear_src      # 4U armor / weapon arcs (extracted with tools/ctr.py x) + MRL indexes
armor() {     # Gravios U 185 / 186, Gravios Z 394 / 395 (tools/gear_em005_01.py), m and f
    local s n p
    for s in m f; do for n in 185 186 394 395; do for p in helm arm wst leg body; do
        mkdir -p "$MON/romfs/nativeNX/arc/player/com/$s/$n"
        python3 tools/armor4u2gu.py convert "$GS/armor/4u/data/pl_${s}_$p$n.arc" \
            "$MON/romfs/nativeNX/arc/player/com/$s/$n/$p.arc" "$GS/armor/out/mrl_index.pkl" || return 1
    done; done; done
}
weapons() {   # class:4U arc prefix:models:sound models (tools/gear_weapons_em005_01.py): every model arc of the line,
    local spec nn pf ms ss m   # and the sound set of each model whose 4U arc holds its own set (SnS 103: GU's 009;
    for spec in 01:one:103:- 02:ham:029:029 03:lan:047,100:047,100 04:hbg:007:007 09:gun:027:027 \
                11:sou:008,094:008; do   # DB 094 holds 008's set)
        IFS=: read -r nn pf ms ss <<< "$spec"
        mkdir -p "$MON/romfs/nativeNX/arc/weapon/w$nn/snd"
        for m in ${ms//,/ }; do
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
    dt)           dt ;;                                                     # dump/converted/em041/dt_em04N/
    arc)          python3 "$T/build_em005_01_arc.py" ;;                    # monster arc (carves) + manifest + FILE
    name)         python3 "$T/name_em005_01.py" ;;                         # NAME (4U names, 5 languages)
    items)        python3 "$T/items_em005_01.py" ;;                        # TBLA + TXTA (materials) + BUI2 / BUI4
    gear)         python3 "$T/gear_em005_01.py" ;;                         # armor records (Gravios U, Gravios Z)
    armor)        armor ;;                                                  # armor model arcs (40)
    weapons)      weapons ;;                                                # weapon model + sound arcs
    gearw)        python3 "$T/gear_weapons_em005_01.py" ;;                 # weapon table records (6 lines, 18)
    quest)        python3 -I -B "$T/build_em005_01_quest.py" ;;            # 10780 11430 10781 1025 (4U m10611 m10923
                                                                            # m10601 m00911)
    pack)         python3 tools/portdata.py pack black_gravios ;;          # gen/*.sec -> gen/black_gravios.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
ALL=(dt arc name items gear armor weapons gearw quest pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
