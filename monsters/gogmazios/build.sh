#!/bin/bash
# build.sh : rebuild every Gogmazios output from the dumps (game data: the outputs are gitignored, never published).
#
#   monsters/gogmazios/build.sh [STEP ...]      default: every step, in order
#
# Outputs (monsters/gogmazios/): romfs/ (converted RomFS = its assets package), gen/gogmazios.bin (its data file,
#   packed from the gen/*.sec sections, tools/portdata.py), module/em089_slot75.inc, tools/em089_manifest.json;
#   module/gear_hooks.txt (core); work files in dump/converted/.
# Inputs: dump/ (4U ROM dump/base/*.3ds, extracted dump/romfs + dump/exefs_v11, dump/m19_unpacked, dump/gu_stage,
#   dump/converted/em089/{dtbase,dttune}.bin from tools/dt_convert.py in the unicorn venv), dump/gear_src/ (4U armor
#   and weapon arcs + the MRL template indexes of tools/armor4u2gu.py / weapon4u2gu.py `index`), and the GU scratch
#   dir of tools/paths.py. One line per step on stdout, the step's own output in $BUILD_LOGS/<step>.log.
set -u
MON=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$MON/../.." && pwd)
LOGS=${BUILD_LOGS:-$ROOT/dump/build_logs/gogmazios}
GS=$ROOT/dump/gear_src
T=$MON/tools
mkdir -p "$LOGS"
cd "$ROOT" || exit 1

armor() {
    local s n p
    for s in m f; do for n in 352 353; do for p in helm arm wst leg body; do
        mkdir -p "$MON/romfs/nativeNX/arc/player/com/$s/$n"
        python3 tools/armor4u2gu.py convert "$GS/armor/4u/data/pl_${s}_$p$n.arc" \
            "$MON/romfs/nativeNX/arc/player/com/$s/$n/$p.arc" "$GS/armor/out/mrl_index.pkl" || return 1
    done; done; done
}
weapons() {   # class:4U arc name (model = its last 3 digits)
    local spec nn arc num
    for spec in 00:two097 01:one097 02:ham099 03:lan082 04:hbg040 06:lbg047 07:swo079 08:axe077 09:gun082 \
                10:bow075 11:sou087 12:hue071 13:rod025 14:gaxe027; do
        nn=${spec%%:*}; arc=${spec##*:}; num=${arc: -3}
        mkdir -p "$MON/romfs/nativeNX/arc/weapon/w$nn"
        python3 tools/weapon4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$arc.arc" \
            "$MON/romfs/nativeNX/arc/weapon/w$nn/$num.arc" "$GS/weapons/out/wpn_mrl_index.pkl" || return 1
    done
}
step() {      # name: command line of one step
    case $1 in
    snd_bgm)      python3 tools/snd_bgm.py all ;;                         # BGM opus + STQRs (dump/converted)
    snd_area)     python3 tools/snd_area.py convert ;;                    # arena area sounds (dump/converted)
    arc)          python3 "$T/build_em089_arc.py" --cmdtbl gog ;;         # monster arc + manifest + FILE section
    stage)        timeout 1800 python3 -I tools/stage4u2gu.py alias ;;    # Battlequarters alias arcs (m28)
    mapui)        timeout 1200 python3 -I tools/mapui4u2gu.py ;;          # area + whole maps (reads stage's m28.arc)
    ui)           python3 -I "$T/ui_em089.py" ;;                          # name (icon: tools/ui_icons.py)
    quest1)       python3 "$T/build_gog_quest.py" ;;                      # 11491 (4U m11014)
    quest2)       python3 "$T/build_gog_quest.py" --source m11035 ;;      # 11492
    slot75)       python3 "$T/em089_slot75_gen.py" ;;
    items)        python3 "$T/items_em089.py" ;;
    gear)         python3 "$T/gear_em089.py" ;;
    gear_weapons) python3 "$T/gear_weapons_em089.py" ;;
    notes)        python3 "$T/notes_em089.py" ;;
    armor)        armor ;;
    weapons)      weapons ;;
    wsnd)         python3 tools/wsnd4u2gu.py gogma "$GS/weapons/4u/data" ;;
    pack)         python3 tools/portdata.py pack gogmazios ;;              # gen/*.sec -> gen/gogmazios.bin
    *)            echo "unknown step $1"; return 2 ;;
    esac
}
ALL=(snd_bgm snd_area arc stage mapui ui quest1 quest2 slot75 items gear gear_weapons notes armor weapons wsnd pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
