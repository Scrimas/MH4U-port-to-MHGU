#!/bin/bash
# build.sh : rebuild every Dalamadur output from the dumps (game data: the outputs are gitignored, never published).
#
#   monsters/dalamadur/build.sh [STEP ...]      default: every step, in order
#
# Package monsters/dalamadur/ = Dalamadur, Shah Dalamadur and their tail halves (allocations.toml entries dalamadur,
# shah_dalamadur, dalamadur_tail, shah_dalamadur_tail). Outputs: romfs/ (converted RomFS = its assets package: the four
# monster arcs em090_00 / em090_01 / em091_00 / em091_01, the theme's opus streams, Speartip Crag = stage folder m29,
# the armor and weapon model arcs, the weapons' sound arcs),
# tools/<arc>_manifest.json, gen/<entry>/*.sec (data file sections, once the entries are allocated).
# Inputs: dump/romfs (4U em024 / em083 / em110 / em111 arcs, em_data.arc, m08*.arc, the stage BGM and str_m08
#   streams), dump/base (4U ROM: core effect arcs), dump/m19_unpacked/m19a03 (reference area-colour file) and the GU
#   scratch dir of tools/paths.py (its venv runs the dt step; GU m18 files are extracted from its RomFS into
#   dump/gu_stage). Work files in dump/converted/dalamadur/, dump/m08_unpacked/. One line per step on stdout, the
#   step's own output in $BUILD_LOGS/<step>.log.
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
        "$py" tools/dt_convert.py build $em em024_00 "$ROOT/dump/converted/dalamadur/dt_$em" --sensor || return 1
    done
}
GS=$ROOT/dump/gear_src      # 4U armor / weapon arcs (extracted with tools/ctr.py x) + MRL indexes
armor() {     # Rebellion / Riot HR 193 / 194, EX 298 / 299, X 348 / 349, Z 452 / 453 (tools/gear_em090.py), m and f
    local s n p
    for s in m f; do for n in 193 194 298 299 348 349 452 453; do for p in helm arm wst leg body; do
        mkdir -p "$MON/romfs/nativeNX/arc/player/com/$s/$n"
        python3 tools/armor4u2gu.py convert "$GS/armor/4u/data/pl_${s}_$p$n.arc" \
            "$MON/romfs/nativeNX/arc/player/com/$s/$n/$p.arc" "$GS/armor/out/mrl_index.pkl" || return 1
    done; done; done
}
weapons() {   # class:4U arc prefix:HR model:G model (tools/gear_weapons_em090.py): both model arcs, and the line's
    local spec nn pf a b m   # sound set (held by both 4U arcs: the HR model's number = mSrqrNo) from the HR arc
    for spec in 00:two:057:104 01:one:055:105 02:ham:059:107 03:lan:036:091 04:hbg:024:047 06:lbg:045:056 \
                07:swo:042:087 08:axe:043:085 09:gun:049:090 10:bow:025:084 11:sou:041:096 12:hue:035:078 \
                13:rod:006:040 14:gaxe:018:035; do
        IFS=: read -r nn pf a b <<< "$spec"
        mkdir -p "$MON/romfs/nativeNX/arc/weapon/w$nn/snd"
        for m in $a $b; do
            python3 tools/weapon4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$pf$m.arc" \
                "$MON/romfs/nativeNX/arc/weapon/w$nn/$m.arc" "$GS/weapons/out/wpn_mrl_index.pkl" --alpha-test-4u --anim-4u \
                --shield-bone0 || return 1
        done
        python3 tools/wsnd4u2gu.py convert $((10#$nn)) "$GS/weapons/4u/data/pl_$pf$a.arc" \
            "$MON/romfs/nativeNX/arc/weapon/w$nn/snd/$a.arc" || return 1
    done
}
step() {      # name: command line of one step
    case $1 in
    dt)           dt ;;                                                     # dump/converted/dalamadur/dt_em0NN/
    bgm)          python3 "$T/bgm_dalamadur.py" ;;                          # theme opus + dump/converted/dalamadur STQR
    walk)         python3 tools/walk4u2gu.py convert ;;                     # walk collision SBC (dump/converted/dalamadur/walk)
    arc)          python3 "$T/build_dalamadur_arc.py" ;;                    # the four monster arcs + manifests
    speartip)     python3 "$T/build_speartip.py" ;;                         # Speartip Crag: stage m29 (alias of 18)
    ui)           python3 "$T/build_speartip_ui.py" ;;                      # its area maps + whole map (after speartip)
    quest)        python3 "$T/build_dalamadur_quest.py" ;;                  # the 6 quests (QUESTS; extdata ones)
    name)         python3 "$T/name_em090.py" ;;                             # NAME of both heads (4U names, 5 languages)
    notes)        python3 "$T/notes_em090.py" ;;                            # Hunter's Notes entry 125
    items)        python3 "$T/items_em090.py" ;;                            # appended materials + BUI<rank> per entry
    gather)       python3 "$T/gather_em090.py" ;;                           # GPTS: meteor scale / head point lists
    walksec)      python3 "$T/walk_em090.py" ;;                             # WALK: 4U walk triangles (dala_walk.c)
    gear)         python3 "$T/gear_em090.py" ;;                             # armor table records (4 series pairs)
    armor)        armor ;;                                                  # armor model arcs
    weapons)      weapons ;;                                                # weapon model + sound arcs
    gearw)        python3 "$T/gear_weapons_em090.py" ;;                     # weapon table records (14 lines)
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
ALL=(dt bgm walk arc speartip ui quest name notes items gather walksec gear armor weapons gearw pack)
STEPS=("$@"); [ $# -eq 0 ] && STEPS=("${ALL[@]}")
k=0; fails=0; t0=$(date +%s)
for s in "${STEPS[@]}"; do
    k=$((k + 1)); t=$(date +%s)
    if step "$s" > "$LOGS/$s.log" 2>&1; then r=ok; else r="FAILED (see $LOGS/$s.log)"; fails=$((fails + 1)); fi
    printf '[%2d/%d] %-12s %s in %ds\n' $k ${#STEPS[@]} "$s" "$r" $(( $(date +%s) - t ))
done
printf 'done: %d step(s) failed, %ds\n' $fails $(( $(date +%s) - t0 ))
[ $fails -eq 0 ]
