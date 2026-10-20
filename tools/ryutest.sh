#!/usr/bin/env bash
# ryutest.sh : run MHGU headless (no window) in an isolated Ryujinx data dir (ryuroot/) for automated checks.
#   ryutest.sh run [--nomod]     build + install the module into ryuroot, run headless with the GDB stub on :55555
#                                (foreground: start it with run_in_background; no window is ever created)
#   ryutest.sh stop              kill that Ryujinx (by exe path + root dir)
#   ryutest.sh log               path of the current log
# The user's ~/.config/Ryujinx (config, mods, saves) is never touched; ryuroot/bis/user is a copy. Exception: the gui
# run writes its Ryujinx log to ~/.config/Ryujinx/Logs (the newest file there during the run).
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
R=$ROOT/ryuroot
GAME=${GAME:-"$HOME/Switch Games/Monster Hunter Generations Ultimate  [0100770008dd8000][v0].nsp"}

ryu_pids() {   # only Ryujinx processes running on our root dir (the gui launch's /proc/PID/exe is unreadable: cmdline)
    for p in /proc/[0-9]*; do
        c=$(tr '\0' ' ' 2>/dev/null < "$p/cmdline")
        case "$c" in ryujinx\ *|/usr/lib/ryujinx/Ryujinx\ *) ;; *) continue;; esac
        case "$c" in *"--root-data-dir $R "*) echo "${p#/proc/}";; esac
    done
}
ryu_windows() { hyprctl clients -j | python3 -I -c "import json,sys; print(' '.join(c['workspace']['name'] for c in json.load(sys.stdin) if 'yujinx' in (c['class']+c['title']).lower()))"; }

stop() {
    for p in $(ryu_pids); do kill "$p"; done; sleep 3
    for p in $(ryu_pids); do kill -9 "$p"; done; sleep 1
    echo "stopped: $(ryu_pids | wc -l) test Ryujinx left, windows [$(ryu_windows)]"
}

run() {   # foreground: launch via the Bash tool with run_in_background
    [ -n "$(ryu_pids)" ] && { echo "test Ryujinx already running"; exit 1; }
    case " $* " in *" --nomod "*) rm -rf "$R/mods/contents/0100770008dd8000/Gogmazios Port";;
        *) python3 -I "$ROOT/module/build.py" install || exit 1;; esac
    mkdir -p "$R/run"
    SDL_VIDEO_DRIVER=offscreen SDL_AUDIO_DRIVER=pulseaudio exec ryujinx --no-gui --root-data-dir "$R" --enable-gdb-stub \
        --ignore-controller-applet --skip-user-profiles-manager --system-language BritishEnglish --system-region Europe \
        "$GAME" > "$R/run/stdout.log" 2>&1 < /dev/null
}

gui() {   # windowed run on hidden workspace 10 (headless mode aborts ~1.5 s in); killed if it lands elsewhere
    [ -n "$(ryu_pids)" ] && { echo "test Ryujinx already running"; exit 1; }
    case " $* " in *" --nomod "*) rm -rf "$R/mods/contents/0100770008dd8000/Gogmazios Port";;
        *) python3 -I "$ROOT/module/build.py" install || exit 1;; esac
    hyprctl eval "hl.exec_cmd([[env AVALONIA_GLOBAL_SCALE_FACTOR=1.5 SDL_AUDIO_DRIVER=pulseaudio ryujinx --root-data-dir $R \"$GAME\"]], { workspace = '10 silent', no_initial_focus = true })" >/dev/null
    for i in $(seq 1 40); do
        sleep 0.25
        local ws; ws=$(ryu_windows)
        case "$ws" in ""|10|"10 10") ;; *) echo "window appeared on [$ws] -> killed"; stop; exit 1;; esac
    done
    echo "pids: $(ryu_pids | tr '\n' ' ') windows: [$(ryu_windows)]"
}

case ${1:-} in
    gui) shift; gui "$@";;
    run) shift; run "$@";;
    stop) stop;;
    log) echo "$R/run/stdout.log";;
    *) echo "usage: $0 run [--nomod] | stop | log"; exit 2;;
esac
