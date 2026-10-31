# AGENTS.md

Instructions for AI coding assistants working in this repo (Claude Code, Codex, opencode, Cursor, ...).

## Read first
1. `CONTRIBUTING.md`: setup, inputs, workflow, rules.
2. `ARCHITECTURE.md`: what lives where, how the mod runs in the game, the build flow.
3. `notes/porting-guide.md`: how a monster port is done, with lessons from each port. Read it before touching a
   port. Its "ground rules" are the maintainer's working rules.
4. The monster's own `monsters/<name>/notes/` before changing that monster.

## Hard rules
- **Never commit, paste or print game data**: ROM / RomFS bytes, converted assets, `monsters/*/gen/`, 4U / GU text
  tables, anything under `dump/`. Add files by explicit path; never `git add -A`, `git add .` or `git add -f`.
- **Never read, print or commit keys or credentials** (`prod.keys`, `title.keys`, anything in Ryujinx `system/`,
  `ryuroot/`, `*.env`).
- **IDs in `allocations.toml` never move** once shipped; new IDs only grow. Run `python3 tools/alloc.py` after editing
  it.
- **Faithful to 4U**: don't call a behaviour "4U" without tracing it in 4U code (`dump/mh4u.asm`, `tools/dis4u.py`).
  Mark findings as confirmed, strong or guess.
- **Additions only**: never replace a GU monster, quest or item.
- Don't silently change shipped output: `python3 tools/release.py` and byte comparisons against the last release
  show what a change does.

## Working
- Environment: `source .venv/bin/activate`, then `python3 tools/doctor.py` must be all "ok". GU inputs come from
  `tools/paths.py` (`GU_EXEFS`, `GU_ROMFS`, `GU_CODE`), and the GU readers are in `tools/gulib/`.
- Build one monster: `monsters/<name>/build.sh [STEP ...]`, then the module: `python3 module/build.py`. Step logs go to
  `dump/build_logs/<name>/`.
- In-game tests need a human. Ask the tester to play and close, then read the Ryujinx log yourself (Gogmazios:
  `monsters/gogmazios/tools/gogreport.py`). Ask only about what a log can't show (visuals, sound).
- Commit messages: `<Monster or area>: <what changed> (issue #N)`. No AI attribution trailers.
