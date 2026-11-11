#!/usr/bin/env bash
# Decompile functions of an analysed headless Ghidra project into OUT (C text; Ghidra's log in OUT.log).
# usage: decomp.sh PROJECT_DIR PROJECT_NAME PROGRAM OUT ADDR...
#   e.g. decomp.sh dump/mhf/ghidra mhfo mhfo-hd.dll /abs/path/ms.c 0x1032d850 0x1032c4e0
# Launcher: $GHIDRA_HEADLESS if set, else ghidra-analyzeHeadless on PATH (the NixOS ghidra package), else a classic
# install's /opt/ghidra/support/analyzeHeadless.
D=$(cd "$(dirname "$0")" && pwd)
P=$1 N=$2 F=$3 O=$(realpath -m "$4"); shift 4
H=${GHIDRA_HEADLESS:-$(command -v ghidra-analyzeHeadless || echo /opt/ghidra/support/analyzeHeadless)}
[ -x "$H" ] || { echo "decomp.sh: no Ghidra headless launcher ($H); set GHIDRA_HEADLESS" >&2; exit 127; }
GHIDRA_HEADLESS_MAXMEM=${GHIDRA_HEADLESS_MAXMEM:-3G} "$H" "$P" "$N" \
    -process "$F" -noanalysis -readOnly -scriptPath "$D" -postScript Decomp.java "$O" "$@" > "$O.log" 2>&1
st=$?
[ $st -ne 0 ] && tail -20 "$O.log"
exit $st
