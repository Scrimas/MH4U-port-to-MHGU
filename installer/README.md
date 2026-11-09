# MHGU Definitive Edition Installer

The app players use to install the mod: it reads the GitHub releases of MHGU-Definitive-Edition-Packages
(`manifest.json` + the zips that `tools/release.py` makes), installs the ticked monsters with the maps they need into
Ryujinx, the yuzu family, MHGU PC Recomp (untested), an Atmosphère SD card or any folder, updates them to the newest
release, removes them (the `MH4U Port` folder of the releases before 2.0.0 too), and updates itself from its own
releases on MHGU-Definitive-Edition. Rust + Slint (Fluent), like MHGU_Editor.

| Path | What |
|---|---|
| `core/` | everything without a window: `manifest.rs` (schema 1), `source.rs` (GitHub or a local folder), `places.rs`, `record.rs` (`mhgu-de-install.json`), `plan.rs`, `apply.rs` (download, check, extract, swap), `selfupdate.rs`, `settings.rs`; `src/bin/cli.rs` = `mhgu-de-cli` |
| `gui/` | the window: `ui/app.slint`, `src/main.rs`, `src/i18n.rs`, `src/desktop.rs` (the menu entry / Start Menu shortcut), `lang/` (gettext catalogs) |
| `tools/i18n.py` | keeps `gui/lang/` in step with the strings (`@tr` in .slint, `tr` / `trf` / `trn` in Rust) |
| `tests/cli_test.py` | end to end: a fake release of dummy files installed into every kind of place by `mhgu-de-cli` |
| `packaging/build.py` | the release files: `.exe` (mingw-w64), `.AppImage` (zig, glibc 2.28), `SHA256SUMS-<v>` |

```sh
cargo test --manifest-path installer/Cargo.toml --workspace
cargo build --manifest-path installer/Cargo.toml -p mhgu-de-core --bin mhgu-de-cli && python3 installer/tests/cli_test.py
cargo run --manifest-path installer/Cargo.toml -p mhgu-de-installer
```

Environment variables (tests, offline use): `MHGU_DE_RELEASES=<folder>` (the mod's releases: a `releases.json` in the
GitHub API's shape, download URLs relative to it), `MHGU_DE_INSTALLER_RELEASES=<folder>` (the installer's, the same
way), `MHGU_DE_CACHE`, `MHGU_DE_CONFIG`, `MHGU_DE_SNAPSHOT=<png>` (draw the window into a file and quit;
`MHGU_DE_SNAPSHOT_OPEN=review|settings|about` opens that dialog first).

Releases: every release of the mod has one of the installer with the same version (CONTRIBUTING.md, Releases):
`version` in `installer/Cargo.toml` = the release's, then the tag `v<version>`: `.github/workflows/installer.yml`
builds, tests the .exe on Windows and drafts "MHGU Definitive Edition <version>" on this repository;
`tools/release.py publish` puts the zips on MHGU-Definitive-Edition-Packages and gives the draft its text
(NOTES-main.md); the maintainer publishes the draft (it becomes Latest).
