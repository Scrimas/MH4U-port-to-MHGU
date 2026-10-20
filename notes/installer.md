# Installer and packages: requirements (goal 3 / goal 4)

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
