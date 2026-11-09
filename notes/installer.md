# MHGU Definitive Edition Installer and the release packages

The MHGU Definitive Edition Installer (`installer/`, Rust + Slint Fluent like MHGU_Editor) installs the mod from the
GitHub releases of [MHGU-Definitive-Edition-Packages](https://github.com/Scrimas/MHGU-Definitive-Edition-Packages):
the ticked monsters with the maps they need, into several places at once, updated to the newest release, removed
again, with the saves of those places migrated and cleaned. Decisions are the maintainer's (2026-11-09); code map in
`installer/README.md`.

## Releases (tools/release.py)

- A release is one matched set (tag `v<core version>`): `core-<v>.zip` (module + every monster's data file, always
  installed), `<monster>-<v>.zip`, `map-<map>-<v>.zip`, `icons-<release>.zip` (one 72 x 72 PNG per monster, the 4U icon
  at 2x: release asset only, never in git), `manifest.json` and NOTES.md as its text. Every zip extracts into one
  `MHGU Definitive Edition` folder, so extracting by hand keeps working.
- `manifest.json` schema 1 (`installer/core/src/manifest.rs`): the release, `prerelease`, `installer_min`, every
  package (name, kind core / monster / map, title, subtitle, version, requires, zip, size, sha256, every file with
  size and sha256; a monster's entries and icon, a map's folder), `migrations` (migrations.toml), `cleaning` (per
  monster package: its item ranges, armor series and weapons), `warnings`. A newer schema asks for a newer installer.
- Pre-releases: `release.py package --pre N` = `<core>-pre.N`, published as a GitHub pre-release; the installer offers
  them only when its Settings switch is on (with a warning). A release is published marked Latest.
- Two repositories (2.0.0, the maintainer's choice: the list of monster releases would bury the installer):
  `release.py publish` puts the mod's releases on **MHGU-Definitive-Edition-Packages** (zips only, a README); the
  code repository **MHGU-Definitive-Edition** holds the installer's own releases (tag `v<installer version>` with its
  .exe, AppImage and checksums, drafted by .github/workflows/installer.yml, Latest once published), so its release
  page leads new players to the installer. Its older `v1.x` releases are the mod's from before the split (MH4U Port):
  the installer tells its own by their files. One release-list call per repository and start (no `releases/latest`).
  Each release: the tag `v<version>` on main drafts the installer's release (the maintainer publishes it),
  `release.py publish` publishes the zips on -Packages with NOTES.md, then gives the draft NOTES-main.md (What's
  new, monsters and quests, install, tips) as its whole text and the title "MHGU Definitive Edition <version>"
  (`release.py main-notes` when the draft comes later).
- Releases before 2.0.0 have no manifest: the installer installs 2.0.0 and later (no rollback, so nothing is lost).

## Packages

- **core** always comes along. **monsters** are what the player ticks. **maps** (`maps/<map>/`, core 2.0.0): a
  ported arena, required by the monsters fought there (`requires` in their package.toml); later, shared utility
  packages work the same way. A required package comes with the first monster that needs it and leaves with the last.
  The core counts a monster whose map's stage arc is missing as not installed (module/port.c port_installed).
- A place on an older release has everything it keeps moved to the newest release (a package whose version and files
  are unchanged is not downloaded again). A package whose files went missing is repaired.

## Install places (installer/core/src/places.rs)

| Place | Found at | Mod folder |
|---|---|---|
| Ryujinx | `<config>/Ryujinx` (Linux ~/.config, Windows %APPDATA%), its Flatpaks; a portable one as a picked folder | `mods/contents/0100770008dd8000/MHGU Definitive Edition` |
| yuzu family (yuzu, suyu, sudachi, citron, eden, torzu) | `<data>/<name>` (Linux ~/.local/share, Windows %APPDATA%), Flatpaks `~/.var/app/*/data/<name>` | `<load>/0100770008DD8000/MHGU Definitive Edition` (load = qt-config.ini's when not the default, else `<data>/load`) |
| MHGU PC Recomp (untested) | a picked folder holding `mhgurecomp(.exe)` | `mods/MHGU Definitive Edition` ($MHGU_MODS_DIR when set) |
| Atmosphère SD card | mounted cards holding `atmosphere/` | `atmosphere/contents/0100770008DD8000/{exefs,romfs}`, the IPS in `atmosphere/exefs_patches/MHGU Definitive Edition/` |
| Folder | a picked folder | `<folder>/MHGU Definitive Edition` |

The recomp facts come from DeepWiki's summary of morerokk/MHGURecomp (`runtime/mods.c`: a new mod folder loads
enabled unless mods/load_order.txt marks it `# off:`): strong, not confirmed; the port has never run there.

- **Install record** `mhgu-de-install.json` (in the mod folder; SD card: `contents/<title>/`): the release, each
  package's version and files with sha256. A mod folder without one was extracted by hand (or by install.sh): it is
  replaced (removed, installed fresh) after the review says so; on an SD card only our paths are removed.
- **The name before 2.0.0**: a v1.x release extracted by hand left a `MH4U Port` folder beside ours (SD card:
  `romfs/nativeNX/mh4uport` and `exefs_patches/MH4U Port`; its exefs files have our names and are replaced). The
  emulator would load both, so it counts as a hand install and is removed after the install worked, or by a removal
  (places.rs `legacy`); the review says so.
- **Install**: zips downloaded into the cache and checked (size, sha256); every extracted file checked against the
  manifest, a zip member it does not list refused (no path can leave the mod folder). Mod-folder places: the new
  `MHGU Definitive Edition` is built beside the old one (unchanged packages hard-linked or copied) and swapped in by
  rename, so a place is never half installed. SD cards: our old files deleted, the new ones written, the record last;
  other mods in `contents/<title>` stay.

## Saves (installer/core/src/saves.rs)

- Found per place: Ryujinx `bis/user/save/<id>/0/system`, the yuzu family's
  `nand/user/save/0000000000000000/<user>/0100770008DD8000/system`, the recomp's save folder (`SaveLocation` of
  mhgurecomp.ini, else %APPDATA%\MHGURecomp\save / ~/.local/share/MHGURecomp/save), on an SD card the newest JKSV /
  Checkpoint backup of MHGU, migrated into a NEW backup folder beside it (restored with JKSV by the player). Every
  character of every save found is handled; the game must be closed (running emulators are checked).
- Parser: MHGU_Editor's save container, item stores, equipment box and all-copies write, vendored in
  `installer/vendor/mhgu-save` (`installer/tools/vendor_save.py`; no local edits; the editor's GU tables are not taken).
- **Migrations** (only when a shipped ID really has to move; shipped IDs never move): steps in `migrations.toml` (item,
  decoration, armor series, weapon remaps), copied into the manifest; applied to the box, pouch, loadouts, items
  obtained (GU's map and the core's bits of IDs 3008..), the equipment box (pieces, decorations, layered looks) and the
  My Sets' decoration copies. Quest and save-slot remaps are not done by installer 2.0: a step with them blocks the
  migration. `release.py check` refuses a release whose allocations moved a shipped ID since the last tag without a
  step of this release.
- **Migration level**: the MH4S store's version-2 header word at +12 (notes/save-store.md), the last step applied to
  the character. Core 2.0.0 reads version 1 and 2 and turns version 1 into 2 at load. A store that is neither (another
  tool's data, a newer format) makes the save one that cannot be migrated.
- **A save that cannot be migrated** (unreadable, another tool's data, migrated by a newer release, a step this
  installer cannot apply): the first Install shows a warning that can only be closed; going through the review again
  installs without that save, which stays as it is.
- **Cleaning on removal** (the review's choice, when a save holds gear of a monster that leaves; the monsters' data
  files stay installed with the core, only their models leave): Unequip only (preselected: worn pieces taken off, a
  worn weapon swapped for another of the box since a hunter always holds one, My Sets entries cleared; nothing
  deleted) / Remove the worn pieces (data loss) / Remove all their items, decorations and gear (data loss) / leave the
  saves. Layered looks of their armor go back to the own look in every mode.
- **Backups**: before any write, every copy of the save (Ryujinx `0/` `1/`, `system` and `system_backup`) is copied
  into `<data>/mhgu-de-installer/save-backups/<save>-<hash>/<time>-<release>/` (not beside the save: there it would
  sit inside the emulator's save file system). Never deleted by the installer.

## The window and the rest

- Design "B2 compact": 1066 x 600 logical px, install places with what each holds and the action on the left, the
  release's monsters with their maps nested on the right; a review dialog lists every change per place, the saves, the
  cleaning choice and the warnings: the gear warning on removal, online (once: the group needs the same release and
  monsters), pre-releases, the release's own warnings, an emulator running.
- Self-update: the newest installer release of MHGU-Definitive-Edition with its `SHA256SUMS-<v>`, checked at start
  (Settings switch), downloaded beside the running file and swapped in (Windows: the old .exe renamed aside, deleted
  at the next start; Linux: $APPIMAGE replaced), then restarted. Checksums catch a broken download, not a forged
  release.
- Settings and the download cache: `<config>/mhgu-de-installer/settings.json`, `<cache>/mhgu-de-installer/<release>/`;
  after each install only the installed release's zips stay (they serve another place later), older releases'
  folders are deleted.
- Languages: MHGU_Editor's set (en, fr, de, es, it, zh_TW, zh_CN), gettext catalogs in `installer/gui/lang/`
  (`installer/tools/i18n.py`); English now, the other catalogs empty.
- Tests: core unit tests (synthetic saves: zeros with valid slot pointers, no game data), `installer/tests/cli_test.py`
  (a fake release of dummy files into every kind of place), CI on Linux and Windows; the Windows .exe is started on
  the runner and draws its window (MHGU_DE_SNAPSHOT). Windows is tested by CI only.

## Not yet verified

- An emulator that does not ignore the record file in the mod folder (it would then move beside the folder).
- Newer Ryujinx keeps a per-mod on / off state: a freshly added folder must load without Manage Mods.
- MHGU PC Recomp, Atmosphère on hardware (subsdk1 + exefs_patches IPS), Eden (not on the maintainer's machine).
- The .exe is not code-signed: SmartScreen warns (More info -> Run anyway), as for the editor.
