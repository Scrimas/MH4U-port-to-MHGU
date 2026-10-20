# Installer and packages: requirements (goal 3 / goal 4)

## Built (2026-10-21, user decisions: packages on the GitHub repo's releases; standalone Linux AppImage + Windows exe)
- `tools/release.py` (machine with the dumps; hosted CI cannot build: ~15 GB of 4U / GU data, and the module build
  reads GU's main): `build` (every monster's build.sh + the module, no test switches), `check` (allocations, versions,
  requires_core vs module/core.toml, RomFS overlaps, quest HP rows >= 10, module defines.txt empty), `package`
  (core-<v>.zip, <monster>-<v>.zip, manifest.json; deterministic zips), `publish` (gh release v<core>, asks first).
- `installer/` (Rust, Slint 1.18.1 as MHGU_Editor; packaging/build.sh = MHGU_Editor's pipeline): finds Ryujinx
  (+ Flatpak), the yuzu family (yuzu, suyu, sudachi, citron, eden), EmuDeck storage folders and Atmosphère SD cards,
  or a typed folder; reads the latest release of MH4UPORT_REPO (GitHub API), installs core + ticked monsters, checks
  size + sha256, keeps mh4uport-install.json (update / remove per monster, uninstall all), asks twice before removing
  a monster (gear warning), shows the manifest's warnings. CLI mode for tests / scripts (src/main.rs docstring).
- `.github/workflows/installer.yml`: on v* tags, builds both apps, runs installer/tests/cli_test.py on Linux and on
  Windows (the shipped .exe), attaches them to the release.
- Not yet verified: a real GitHub release (no remote yet), the Windows exe's window, Atmosphère on hardware
  (subsdk1 + exefs_patches IPS untested on a Switch).

Collected before the installer exists; each line is a requirement the user set or a consequence of a design choice.

## Package layout (decided 2026-10-20)
- Core package: exefs (subsdk1 + IPS) and EVERY registered monster's data file `romfs/nativeNX/mh4uport/<name>.bin`
  (tables + text, no models / sounds / quests). Always installed together, so gear IDs never move
  (allocations.toml order = append order; module/port.c refuses to append after a missing or mismatched block).
- One package per monster: its assets (monster arc, quests, BGM, arena, map UI, gear models, weapon sounds). A monster
  counts as installed when its monster arc is present (module/port.c); its quests and spawn hooks stay off otherwise.
- Versions: monsters/<name>/package.toml (version, requires_core); the data file header carries the version too.
  The installer keeps an install record (versions, file list, sha256) in the mod folder to update / uninstall.

## Warnings the installer must show (user, 2026-10-20)
- **Gear models ship with their monster.** A monster's armor and weapon models (e.g. Gogma armor models 352 / 353,
  the 14 Gogma weapon models) are in its own package, while its gear records are always installed. Untested what GU
  does when a model file is missing (crash or nothing drawn). Show a warning:
  - before uninstalling a monster: unequip and stop using its armor / weapons first;
  - in the install screen: online, a player wearing gear of a monster you did not install may crash your game or
    show nothing; install the monsters your group uses.
  Possible later fix (not decided): ship the gear models in the always-installed layer, or a module fallback to a
  GU model when the model file is missing.
