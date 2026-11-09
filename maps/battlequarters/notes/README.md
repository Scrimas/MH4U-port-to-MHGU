# Battlequarters (map package)

4U m19 as an alias of GU stage 26 (the Fortress), stage folder m28. Built by `maps/battlequarters/build.py` with the
shared converters `tools/stage4u2gu.py` (alias arcs), `tools/mapui4u2gu.py` (area and whole maps), `tools/snd_bgm.py
stage` and `tools/snd_area.py` (area streams and sounds). Required by Gogmazios.

Its study and test history stay with the port that made it: `monsters/gogmazios/notes/stage.md` (and the "Arena"
sections of `monsters/gogmazios/notes/port-checklist.md`). Its gimmicks (doors, cannons, Dragonator, cart, Demolisher)
are core code: `monsters/gogmazios/module/stage*.c`, `module/stage_alias.c`.
