# Contributing

Thanks for helping. Read this file first. `ARCHITECTURE.md` maps the repo, and `notes/porting-guide.md` explains how a
monster port is done.

**No game data ever goes into this repo** (not in commits, issues or PRs): every asset is rebuilt locally from your
own dumps. The project is GPL-3.0-or-later. By contributing, you agree to license your work under the same terms,
and, as the project will later be merged into a larger one, to let your work be relicensed under that project's
license when the merge happens.

## Ways to help

| You want to | You need |
|---|---|
| **Report a bug** | The game and the mod, nothing else. Open an issue (see below). |
| **Fix something** | The full setup below. |
| **Port a new monster** | The full setup, then `notes/porting-guide.md`. Open an issue first, so nobody else starts the same monster. |
| **Work on the installer** | Rust only, no game files: [The installer](#the-installer) below. |

### Report a bug

1. Say which release you run and how you installed it: with the installer (it shows the release at the top, e.g.
   2.0.0) or by hand (`core-x.y.z` and every zip, all from the same release). Then on which emulator or console, and
   solo or online.
2. Give the steps: quest, monster, what you did, and what happened versus what you expected (4U behaviour if you
   know it).
3. Attach the **log** of the session. In Ryujinx: File > Open Logs Folder, then the newest file. A screenshot or
   clip helps with anything visual.

## Requirements

- **Linux or Windows** (macOS is untested). Every build script is Python, so no shell is needed.
- Python 3.11 or newer, plus `clang`, `lld`, `llvm` (llvm-objdump, llvm-nm), `ffmpeg` built with libsoxr, and `opus`.
  - **Linux:** from your package manager. Arch: `clang lld llvm ffmpeg opus`. Debian / Ubuntu: `clang lld llvm ffmpeg
    libopus0`.
  - **Windows:** Python from [python.org](https://www.python.org/downloads/) (tick "Add python.exe to PATH"). The
    other tools come from [MSYS2](https://www.msys2.org): install it, open the **MSYS2 UCRT64** terminal and run
    `pacman -S mingw-w64-ucrt-x86_64-{clang,lld,llvm-tools,ffmpeg,opus}`, then add `C:\msys64\ucrt64\bin` to your
    PATH (Windows search: "Edit the system environment variables" > Environment Variables > Path > New). Run the
    commands below in a normal PowerShell, not in the MSYS2 terminal.
- About **30 GB** of free disk: about 12 GB for the GU RomFS, 3 GB for the 4U ROM, and room for the converted files.
- [Ryujinx](https://ryujinx.app) with your own keys and your own MHGU, to extract the game files and to test.

`python3 tools/doctor.py` (Windows: `python tools/doctor.py`) checks all of this, and prints the fix for anything
missing.

## What to dump, and how

Everything comes from games you own. The tools check versions by SHA-256 (`tools/doctor.py`).

| Put this | Here | How |
|---|---|---|
| MH4U **EUR**, decrypted `.3ds` | `dump/base/` | GodMode9 on your 3DS: dump the cartridge (or the installed eShop title) as a decrypted `.3ds`. |
| MH4U **v1.1 update (EUR)**, decrypted `.cia` | `dump/update/` | GodMode9: build a decrypted CIA of the installed update. |
| MHGU **v1.4 ExeFS** | `dump/gu_exefs/` | Ryujinx: right-click MHGU > Manage Title Updates > **1.4.0**, then right-click > Extract Data > **ExeFS**. |
| MHGU **v1.4 RomFS** | `dump/gu_romfs/` | Ryujinx, with 1.4.0 still selected: right-click > Extract Data > **RomFS** (12 GB). |
| *(optional)* 4U DLC extdata | `dump/extdata_4u/` | Your 3DS extdata. Only the event-quest builders use it. |

Only the EUR 4U is supported: the tools read fixed code addresses of EUR v1.1. Both MHGU extractions must be
**v1.4**, the version the mod targets (`doctor.py` tells you if the update was not applied).

Your keys come from your own Switch (Lockpick_RCM) and live in Ryujinx's `system/` folder. Never copy them into the
repo.

## Quick start

**Linux:**

```sh
git clone https://github.com/Scrimas/MHGU-Definitive-Edition.git && cd MHGU-Definitive-Edition
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
# put your dumps in dump/ (table above), then:
python3 tools/setup.py             # makes the rest of dump/ (a few minutes; safe to re-run)
python3 tools/doctor.py            # every line must be "ok"; each failure prints its fix
python3 monsters/gogmazios/build.py   # one monster (each one has its own build.py), about a minute
python3 module/build.py            # the code module (all monsters) -> module/out/
GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install   # into your Ryujinx mods folder
```

**Windows** (PowerShell):

```powershell
git clone https://github.com/Scrimas/MHGU-Definitive-Edition.git; cd MHGU-Definitive-Edition
py -m venv .venv; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\Activate.ps1         # if refused: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
setx PYTHONUTF8 1                  # once, then open a new PowerShell (the tools read and write UTF-8 text)
# put your dumps in dump\ (table above), then:
python tools\setup.py
python tools\doctor.py
python monsters\gogmazios\build.py
python module\build.py
$env:GOG_MOD_ROOT = "$env:APPDATA\Ryujinx\mods"; python module\build.py install
```

Then start MHGU in Ryujinx and play the monster's quest. To remove the mod, delete the `MHGU Definitive Edition`
folder in `<Ryujinx mods>/contents/0100770008dd8000/` (Linux: `~/.config/Ryujinx/mods`, Windows:
`%APPDATA%\Ryujinx\mods`), and unequip that monster's gear before removing it. `module/build.py install` also removes
`MH4U Port`, the mod's folder before 2.0.0. Without `GOG_MOD_ROOT` it installs into `ryuroot/`, the maintainer's
isolated test setup (`tools/ryutest.sh`, Linux only).

A monster's `build.py` runs its steps in order, one line each, with the step's own output in
`dump/build_logs/<monster>/<step>.log`. `build.py STEP ...` re-runs only those steps; `build.py --list` lists them.
A ported arena is a map package of its own (`maps/<map>/build.py`, same runner): build the map a monster `requires`
(its `package.toml`) too; `module/build.py install` installs the required maps with the monster. A new arena = a new
map package (`notes/porting-guide.md`, Phase 5).

Feature and test switches are C `#ifdef`s: `GOG_DEFINES="NAME1 NAME2" python3 module/build.py` (PowerShell:
`$env:GOG_DEFINES = "NAME1 NAME2"` first). Release builds use none. `python3 tools/release.py all` builds and packages a
full release into `dump/release/` ([Releases](#releases-maintainer) below).

## The installer

`installer/` is the MHGU Definitive Edition Installer (Rust + Slint), the app players use. It needs no game files and
none of the setup above: only [Rust](https://rustup.rs) (stable), and on Linux the fontconfig and xkbcommon
development packages (Debian / Ubuntu: `libfontconfig1-dev libxkbcommon-dev`). `installer/README.md` maps its code;
`notes/installer.md` is its design.

```sh
cargo test --manifest-path installer/Cargo.toml --workspace          # unit tests (synthetic saves, no game data)
cargo build --manifest-path installer/Cargo.toml -p mhgu-de-core --bin mhgu-de-cli
python3 installer/tests/cli_test.py                                 # end to end: a fake release, every place kind
cargo run --manifest-path installer/Cargo.toml -p mhgu-de-installer  # the window, on the real releases
python3 installer/tools/i18n.py                                     # after changing a shown string: the catalogs
```

It reads the mod's releases from MHGU-Definitive-Edition-Packages and its own from this repository;
`MHGU_DE_RELEASES=<folder>` points it at a local release instead (a `releases.json` in the GitHub API's shape, see
`installer/README.md`), to test a release before it is published.

## Workflow

1. Open or pick an **issue** for the change, and say you are on it.
2. Branch from `main`: `wip/<topic>` (e.g. `wip/issue-6-effects`), one topic per branch.
3. Commit messages: `<Monster or area>: <what changed> (issue #N)`, e.g.
   `Stygian Zinogre: play the discharge effect once (issue #8)`. Explain *why* in the body when it is not obvious.
4. Test in-game before asking for review, and say how you tested (quest, solo or online, what you checked).
5. Open a PR to `main`. Keep it reviewable: one topic, no unrelated reformatting.

## Rules

- **No game data in git.** That covers ROMs, RomFS files, converted assets (`monsters/*/romfs/`), generated tables
  (`monsters/*/gen/`) and anything else holding 4U / GU bytes or text. `.gitignore` covers the usual places. Add files
  by explicit path, check `git status` before every commit, and never use `git add -f` on ignored paths.
- **No keys or secrets**, anywhere.
- **IDs are claimed in `allocations.toml`.** Every game-wide ID a port takes (registry index, em number, file IDs, save
  slots, text / icon / Notes entries, quest IDs) lives there; `python3 tools/alloc.py` checks it. Starting a port?
  Open a **draft PR early** that only adds your `allocations.toml` entry, so two ports never take the same IDs. Once a
  monster has shipped, its IDs never change, because saves and quests keep them.
- **Faithful to 4U**: a port is finished when its looks, arena, behaviour, music, SFX, quest ranks, drops and
  gathering match 4U. Stand-ins are known deviations, listed as such.
- Everything is **added** to GU: never replace a GU monster, quest or item.
- Releases are matched sets: core and monster zips from different releases are never mixed.

## Checks

- **Pre-commit hook** (`tools/hooks/pre-commit`, switched on by `tools/setup.py`): runs `tools/check_repo.py`, which
  refuses files in game-data folders, game file types (`.arc`, `.3ds`, `.nsp`, ...), binaries over 256 KB and key
  material. If it refuses a file, unstage it (`git restore --staged <file>`); never bypass it with `--no-verify`.
- **CI** (`.github/workflows/ci.yml`, every PR and push to `main`, no game files needed): the same check on every
  tracked file, `tools/alloc.py` (IDs), every Python file compiles, and every C file of the module compiles
  (`tools/ci_compile.py`; it cannot link, which needs GU's `main`). Run them locally before a PR.
- **Save code**: a change to `module/save.c` (the mod's save store and slot leases) runs `python3 tools/test_save.py`
  too: it runs that file as ARM code under unicorn on a fake character, no game files needed.
- **Save files**: a change to `module/modsave.c`, `installer/core/src/modsave.rs` or `tools/modsave.py` (the mod's own
  save files, notes/mod-save-format.md) runs `python3 tools/test_modsave.py [system ...]` and `python3 tools/modsave.py
  test [system]`: C and Rust against the Python reference, byte for byte, on a synthetic slot and on copies of your
  own saves.
- **Installer CI** (`.github/workflows/installer.yml`, every push and PR touching `installer/`): `cargo fmt --check`,
  the unit tests, the catalogs (`installer/tools/i18n.py --check`) and `installer/tests/cli_test.py`, on Linux and
  Windows.

## Releases (maintainer)

A release has two GitHub releases with the same version: the zips on
[MHGU-Definitive-Edition-Packages](https://github.com/Scrimas/MHGU-Definitive-Edition-Packages) (what the installer
installs, published directly) and the installer on this repository (the page players land on, drafted, published by
hand).

1. Write the release's section in `notes/release-news.md` (`## v<version>`: **New** / **Fixed**, one short line each
   for players).
2. Bump the versions: `module/core.toml` (core), the `package.toml` of each changed package (`requires_core` too when
   it needs the new core), and `installer/Cargo.toml` to the same version (the workflow refuses a tag that does not
   match it). Build the installer once so `installer/Cargo.lock` follows (CI builds `--locked`), and commit all of it.
3. `python3 tools/release.py all`: builds everything without test switches, checks it and packages
   `dump/release/v<version>/` (the zips, `manifest.json`, `NOTES.md` for -Packages, `NOTES-main.md` for this
   repository). Test that folder in game through the installer (`MHGU_DE_RELEASES`, above).
4. Tag `main`: `git tag v<version> && git push origin v<version>`. The Installer workflow builds the .exe and the
   AppImage, starts the .exe on Windows and drafts the release "MHGU Definitive Edition <version>" here.
5. `python3 tools/release.py publish`: publishes the zips on -Packages (marked Latest), then gives this repository's
   draft `NOTES-main.md` as its text (`python3 tools/release.py main-notes` if the draft was not there yet).
6. Check the draft, then publish it: it becomes this repository's Latest release.

Pre-releases: `release.py all --pre N` (version `<core>-pre.N`), published as GitHub pre-releases; the installer
offers them only when its Settings switch is on.

## Using an AI coding assistant

`AGENTS.md` gives AI tools the hard rules and where to start. You are responsible for what you submit: check its
claims against the code, and never paste game data into a chat.
