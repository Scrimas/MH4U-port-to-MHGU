Port Dalamadur and Shah Dalamadur from MH4U into MHGU faithfully, in /home/scrimas/Projects/MH4U_MHGU_port (git,
private repo Scrimas/MH4U-port-to-MHGU, branch main). Scope:
- both monsters (Shah Dalamadur may be a variant of the same 4U class or its own em: find out, then port it the way
  4U builds it), faithful in looks, arena, behaviour, music and SFX ("finished" = all of these, an ADDITION to GU,
  never a replacement);
- both armor sets (every piece, Blademaster and Gunner, male and female, every rank 4U has), both weapon lines
  (every weapon 4U has for them, all classes and upgrade paths, with their models and sounds), and their skills
  (new skill trees, decorations if any, and the armor skills the sets give);
- the content around them: materials, carves, break / capture / quest rewards, Hunter's Notes, names in every
  language, map and quest-board icons, their quests on their arena.

Already done in this repo, reuse it: Gogmazios (4U em089, own GU class port: monsters/gogmazios/) and Tigerstripe
Zamtrios (4U em092, run by GU's Zamtrios class as variant 1: monsters/tigerstripe_zamtrios/). Shared tools in tools/
(converters for models, textures, materials, effects, sounds, motions, quests, items, gear, weapons, EMC, XFS, LMT),
the core module in module/, release packaging in tools/release.py.

Read first, in this order:
1. notes/porting-guide.md: sections 0, 1, 4, 5, 5b (lessons from Tigerstripe) and 6 (Dalamadur: what to settle
   first). It points to the topic notes (registry, enemy-class, port, api-map, assets, data, gear-weapons).
2. The memory files (MEMORY.md index): they hold the user's rules for tests, installs, faithful claims, agents.
3. allocations.toml and `python3 tools/alloc.py show` (free IDs: registry index, Notes, save slot, name entries,
   DUMMY items, decorations, file IDs, quests, board slots, BGM IDs).
4. monsters/gogmazios/notes/port-checklist.md only by search (rg by address or topic), never end to end.

How to work (the user's rules, keep them):
- Research -> plan -> review: present a plan per goal and wait for the user's OK before restructuring anything or
  publishing. Ask the user what a 4U feature does before guessing (they know 4U well).
- Edit files only with the Edit tool (Write for new files); read and search with cat / sed -n / rg / rg --files.
  `sudo -A` for sudo. Announce anything longer than about a minute and run it in the background.
- At most ONE helper agent at a time, freshly and narrowly briefed (files it owns, files it must not touch, no
  sub-agents, no installs). Static RE briefs work well: give it the addresses and notes already known.
- Never call something "4U behaviour" before tracing every end condition in 4U code. Mark facts C / S / G.
- Validate every converter on GU's or 4U's own data before trusting it (build-time asserts, byte-identical rebuilds),
  and keep Gogmazios' and Tigerstripe's outputs byte-identical after any change to a shared tool.
- Multiplayer correctness is priority 1: GU applies damage only on the machine controlling the monster
  (enemy+0x7420); every machine runs the attacks against its own copy.
- Tests: install only when the user says so, into ~/.config/Ryujinx/mods
  (`GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install`, then cmp the installed files), uninstall
  after each test. Kill tests use TEST_HP_PCT=5 (or the quest builder's low HP row). The user plays and closes; read
  the Ryujinx log (~/.config/Ryujinx/Logs, a report tool like monsters/*/tools/*report.py) and ask only about
  visuals.
- Commits: no AI attribution (no Co-Authored-By, no session link). Never print or commit anything from ryuroot/
  (emulator keys). Game data and converted assets stay out of git (dump/, monsters/*/romfs, monsters/*/gen).
- Keep one-off scripts and outputs in the session scratchpad and copy them to dump/scratch/dalamadur-session/ before
  the session ends (/tmp is wiped on reboot).

Release: `python3 tools/release.py all` builds and packages core-<v>.zip (module + every monster's data file,
required) and one <monster>-<v>.zip per monster (its assets, optional); every zip extracts into the game's mod
directory. Bump module/core.toml and each package.toml on published changes. No installer apps.

Start with Phase 0 of the guide (identify both monsters' 4U em numbers, class, arena stage, how Shah differs), then
present the plan.
