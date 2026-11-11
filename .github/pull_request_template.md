## What and why

<!-- One topic per PR. Link the issue: "Closes #N". -->

## How it was tested

<!-- Quest, solo or online, what you checked in-game. For output changes: what differs from the last release and why. -->

## Checklist

- [ ] No game data or keys (`python3 tools/check_repo.py --all` passes; the pre-commit hook is on)
- [ ] New IDs claimed in `allocations.toml`, shipped IDs unchanged (`python3 tools/alloc.py`)
- [ ] `python3 tools/ci_compile.py` passes
- [ ] Tested in-game (or explained why not)
- [ ] Notes / docs updated (`monsters/<name>/notes/`, `ARCHITECTURE.md`, `CONTRIBUTING.md` if the setup changed)
