# MH4U Port Installer

The app players use to install the mod: it reads the repository's GitHub releases (`manifest.json` + the zips that
`tools/release.py` makes), installs the ticked monsters with the maps they need into Ryujinx, the yuzu family, MHGU PC
Recomp (untested), an Atmosphère SD card or any folder, updates them to the newest release, removes them, and updates
itself from its own `installer-v*` releases. Rust + Slint (Fluent), like MHGU_Editor.

| Path | What |
|---|---|
| `core/` | everything without a window: `manifest.rs` (schema 1), `source.rs` (GitHub or a local folder), `places.rs`, `record.rs` (`mh4uport-install.json`), `plan.rs`, `apply.rs` (download, check, extract, swap), `selfupdate.rs`, `settings.rs`; `src/bin/cli.rs` = `mh4uport-cli` |
| `gui/` | the window: `ui/app.slint`, `src/main.rs`, `src/i18n.rs`, `lang/` (gettext catalogs) |
| `tools/i18n.py` | keeps `gui/lang/` in step with the strings (`@tr` in .slint, `tr` / `trf` / `trn` in Rust) |
| `tests/cli_test.py` | end to end: a fake release of dummy files installed into every kind of place by `mh4uport-cli` |
| `packaging/build.py` | the release files: `.exe` (mingw-w64), `.AppImage` (zig, glibc 2.28), `SHA256SUMS-<v>` |

```sh
cargo test --manifest-path installer/Cargo.toml --workspace
cargo build --manifest-path installer/Cargo.toml -p mh4uport-core --bin mh4uport-cli && python3 installer/tests/cli_test.py
cargo run --manifest-path installer/Cargo.toml -p mh4uport-installer
```

Environment variables (tests, offline use): `MH4UPORT_RELEASES=<folder>` (a `releases.json` in the GitHub API's shape,
download URLs relative to it), `MH4UPORT_CACHE`, `MH4UPORT_CONFIG`, `MH4UPORT_SNAPSHOT=<png>` (draw the window into a
file and quit; `MH4UPORT_SNAPSHOT_OPEN=review|settings|about` opens that dialog first).

Releases: bump `version` in `installer/Cargo.toml`, push the tag `installer-v<version>`: `.github/workflows/installer.yml`
builds, tests the .exe on Windows and drafts the release (never marked Latest: the repository's Latest stays on the
mod's release).
