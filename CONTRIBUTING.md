# Contributing

Thanks for helping. Read this file first. `ARCHITECTURE.md` maps the repo, and `notes/porting-guide.md` explains how a
monster port is done.

**No game data ever goes into this repo** (not in commits, issues or PRs): every asset is rebuilt locally from your
own dumps. The project is GPL-3.0-or-later. By contributing, you agree to license your work under the same terms.

## Ways to help

| You want to | You need |
|---|---|
| **Report a bug** | The game and the mod, nothing else. Open an issue (see below). |
| **Fix something** | The full setup below. |
| **Port a new monster** | The full setup, then `notes/porting-guide.md`. Open an issue first, so nobody else starts the same monster. |

### Report a bug

1. Say which release you run (`core-x.y.z` and every monster zip, all from the same release), on which emulator or
   console, and solo or online.
2. Give the steps: quest, monster, what you did, and what happened versus what you expected (4U behaviour if you
   know it).
3. Attach the **log** of the session. In Ryujinx: File > Open Logs Folder, then the newest file. A screenshot or
   clip helps with anything visual.

## Requirements

- **Linux** (Windows: use WSL2; macOS is untested). Python 3.11 or newer, `clang`, `lld`, `llvm` (llvm-objdump),
  `ffmpeg` built with libsoxr, `opus`. On Arch: `clang lld llvm ffmpeg opus`.
- About **30 GB** of free disk: about 12 GB for the GU RomFS, 3 GB for the 4U ROM, and room for the converted files.
- [Ryujinx](https://ryujinx.app) with your own keys and your own MHGU, to extract the game files and to test.

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

```sh
git clone https://github.com/Scrimas/MH4U-port-to-MHGU.git && cd MH4U-port-to-MHGU
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
# put your dumps in dump/ (table above), then:
python3 tools/setup.py             # makes the rest of dump/ (a few minutes; safe to re-run)
python3 tools/doctor.py            # every line must be "ok"; each failure prints its fix
monsters/gogmazios/build.sh        # one monster (each one has its own build.sh), about a minute
python3 module/build.py            # the code module (all monsters) -> module/out/
GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install   # into your Ryujinx mods folder
```

Then start MHGU in Ryujinx and play the monster's quest. To remove the mod, delete
`~/.config/Ryujinx/mods/contents/0100770008dd8000/MH4U Port`, and unequip that monster's gear before removing it.
`python3 module/build.py install` without `GOG_MOD_ROOT` installs into `ryuroot/`, the maintainer's isolated test
setup (`tools/ryutest.sh`).

Feature and test switches are C `#ifdef`s: `GOG_DEFINES="NAME1 NAME2" python3 module/build.py`. Release builds use
none. `python3 tools/release.py all` builds and packages a full release into `dump/release/`.

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

## Using an AI coding assistant

`AGENTS.md` gives AI tools the hard rules and where to start. You are responsible for what you submit: check its
claims against the code, and never paste game data into a chat.
