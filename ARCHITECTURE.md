# Architecture

MHGU Definitive Edition (MH4U Port before 2.0.0) adds Monster Hunter 4 Ultimate monsters (with their quests, armor,
weapons and skills) to Monster Hunter Generations Ultimate (Switch, v1.4). Everything is **added**; no GU monster,
quest or item is replaced.
Ported so far: Gogmazios, Dalamadur / Shah Dalamadur, Tigerstripe Zamtrios, Stygian Zinogre, Black Gravios, Monoblos,
Tidal Najarala, Shrouded Nerscylla. In progress: the Magnet Spike weapon class from MHF-ZZ.

**No game data is in git.** Every asset and every table holding 4U text or records is rebuilt locally from your own
4U / GU dumps by the converters in `tools/` and `monsters/<name>/tools/`.

New contributor? Start with `CONTRIBUTING.md` (setup, quick start, workflow), then this file, then
`notes/porting-guide.md` before porting a monster.

## How it runs in the game

A release is one mod folder, `MHGU Definitive Edition/`, loaded by the emulator (Ryujinx) or Atmosphere:

| Path in the mod | Built from | Role |
|---|---|---|
| `exefs/subsdk1` | `module/` (C) + each monster's `module/` | Code injected into GU: hooks and the ported monster classes |
| `exefs/<build id>.ips` | `module/build.py` | Patch to GU's `main` that branches into the hooks (trampolines) |
| `romfs/nativeNX/mhgu_de/<name>.bin` | `monsters/<name>/gen/` (`tools/portdata.py`) | Per-monster data file read by the code at run time |
| `romfs/nativeNX/...` (arcs, textures, sounds) | `monsters/<name>/romfs/`, `maps/<map>/romfs/` | Converted 4U assets (layeredFS) |

Release = `core-<v>.zip` (exefs + data files) + one optional zip per monster (its assets) + one per map (a ported
arena, `map-<map>-<v>.zip`, needed by the monsters that `require` it), all merged into the same folder, with a
`manifest.json` and `icons-<v>.zip` for the installer (notes/installer.md). A release's zips are one matched set:
never mix versions.

## Repository layout

### Tracked

```
allocations.toml      Single source of every game-wide ID a port takes (registry index, em number, file IDs,
                      save slots, name / icon / Hunter's Notes entries, quest IDs, appended table records).
                      IDs only ever grow (saves and quests keep them). Checked by tools/alloc.py,
                      emitted as module/out/alloc.h for the C side.
module/               Core C module (the shared engine of the port):
  main.c crt0.S link.ld   entry point, startup, link layout of subsdk1
  port.c port.h           monster registry: relocated GU registry tables, class registration
  quest.c                 quest lists / quest data hooks
  gear.c gear_hooks.txt   armor, weapons, skills
  items.c                 items appended to GU's tables
  bgm.c icons.c notes.c   music, UI icons, Hunter's Notes
  save.c                  the mod's save store and per-quest leases of the save slots (notes/save-store.md)
  stage_alias.c           maps 4U stages onto GU stage slots
  game.h util.c util.h    GU structures and helpers
  core.toml               core version and build config
  build.py                builds subsdk1 + IPS; `build.py install` installs into the Ryujinx mod folder
tools/                ~60 Python scripts (shared by every port):
  formats             arc.py arcpack.py tex.py lmt.py (animation) mod.py (model) mrl*.py (materials)
                      sbc.py (collision) xfs.py (GU area data) emc.py (enemy AI bytecode)
                      sdl.py (scheduler) nso.py ctr.py (reads decrypted 3DS images)
  4U -> GU            mod4u2gu stage4u2gu snd4u2gu wsnd4u2gu efl4u2gu (effects) lcm4u2gu (cameras) walk4u2gu
                      armor4u2gu weapon4u2gu mapui4u2gu (each *4u2gu.py converts one asset kind)
                      sis.py (stage area info) mrl_build mrl_check mrl_anim (GU material lists from templates)
  sound               snd_bgm.py (BGM -> Opus + STQR) snd_area.py (area sounds)
  4U data readers     quest4u items4u weapons4u gear4u emdata4u notes4u extdata4u (DLC quests)
                      hagi4u (carve tables -> GU carve files) hsum4u (summarise a 4U action handler)
  enemy data          dt_convert dt_map dt_vote fieldmap: build GU dtbase / dtbparts / dttune from 4U records
  GU study            gu.py gu_enemy.py gu_schema.py guemu.py (runs GU loaders under unicorn) arctypes.py
  binaries            mkelf3ds.py (4U code.bin -> ELF) stage0.gdb (gdb script)
  UI                  ui_icons.py (icon atlas page, see module/icons.c)
  code mapping        apimap*.py apialign*.py slotmap.py dis4u.py disp4u.py a4u.py: match 4U functions and
                      vtable slots to GU's, resolve 4U action dispatchers
  ids / packing       alloc.py portdata.py paths.py (every input / output path, overridable by environment)
  setup               setup.py (makes dump/ from your own dumps, step by step), doctor.py (checks the machine,
                      inputs and outputs), gu_stage_files.txt (the GU stage files setup.py copies),
                      steps.py (the step runner of every monsters/<name>/build.py: Linux and Windows, no shell)
  gulib/              GU readers vendored from MHGU_Editor: romfs (Ryujinx folder or image), arc, gmd, asm
                      (index of GU main's disassembly), vt, build_assets subset, monster-index.csv; tools put it
                      first on sys.path (paths.GU_PY), so its arc.py shadows tools/arc.py there
  pipeline            release.py (build, check, package, publish), ryutest.sh (isolated Ryujinx test run;
                      maintainer's machine: Hyprland, fixed NSP path)
monsters/<name>/      One port each: gogmazios, dalamadur, stygian_zinogre, tigerstripe_zamtrios
  build.py              rebuilds every output of this monster from the dumps, step by step (tools/steps.py)
  tools/                monster-specific generators (arc build, quests, gear, action tables)
  module/               the monster's C code (class, actions, shells, effects, stage gimmicks),
                        compiled into subsdk1 with the core
  notes/                study notes, behaviour notes, port checklist, release notes
maps/<map>/           One ported arena each: battlequarters (m28), speartip_crag (m29), heavens_mount (m30)
  package.toml          kind "map", version, folder (= the monsters' stage_alias), [stage] (compiled into the core)
  build.py, tools/      its alias stage arcs, map UI, map_com, area streams (tools/steps.py)
  notes/                links to the study notes (kept with the port that made the arena)
weapons/magnet_spike/ WIP: MHF-ZZ weapon class on GU's weapon class slot 5 (tools/, gen/, romfs/)
requirements.txt      Python packages (one .venv for every tool)
migrations.toml       save migration steps for the installer (empty: shipped IDs never move)
installer/            MHGU Definitive Edition Installer (Rust + Slint): core/ (releases, places, planner, install,
                      saves), gui/, vendor/mhgu-save (MHGU_Editor's save parser), tests/, packaging/
                      (notes/installer.md)
notes/                Project docs: porting-guide (start here), port, api-map, data, enemy-class,
                      registry, gear-weapons, items-append, assets, installer, release-news
.github/workflows/    ci.yml (checks without game data), installer.yml (installer tests; builds and a draft
                      release on v* tags). A mod release cannot be built in CI: it needs ~15 GB of dumps
```

### Local only (gitignored)

```
dump/                 Game dumps and everything derived from them (detailed below)
monsters/*/romfs*/    Converted assets of each monster (its assets package; romfs-<donor>/ = alternative or
                      experimental builds)
monsters/*/gen/       Generated tables holding 4U text / records -> packed into <name>.bin
maps/*/romfs/         Converted assets of each map package
ryuroot/              Isolated Ryujinx data dir used by tools/ryutest.sh (keys, mods, test save)
module/out/           Build output (subsdk1, IPS, alloc.h)
installer/target|dist Rust build output
install.sh            Maintainer's personal install dashboard (+ .install.state)
.venv/                Python venv (requirements.txt)
.claude/              AI assistant session data
```

Other root files: `README.md` (users), `LICENSE` (GPL-3.0-or-later), `opencode.jsonc` (AI assistant config),
`.vscode/` (editor settings).

### dump/ in detail

Everything a converter or study tool reads or writes. Paths are fixed (`tools/paths.py: DUMP`). You provide the raw
inputs; `tools/setup.py` makes the rest a build needs (marked [setup]); the converters extract what else they need
when it is missing; the code-study files are the maintainer's and only matter when porting a new monster.

```
Raw inputs (from your own consoles / games)
  base/                 MH4U (EUR) decrypted .3ds ROM          (read by tools/ctr.py)
  update/               MH4U v1.1 update, decrypted .cia
  extdata_4u/           optional: 4U DLC / event quest extdata (decrypted by tools/extdata4u.py)
  gu_exefs/             MHGU v1.4 ExeFS (Ryujinx Extract Data, update 1.4 selected): main, main.npdm, rtld, sdk
  gu_romfs/             MHGU v1.4 RomFS (Ryujinx Extract Data, update 1.4 selected): nativeNX/... (12 GB)

Made by tools/setup.py (also needed by a build)
  exefs_v11/            4U v1.1 code.bin, exheader.bin, mem.bin (flat from 0x100000)   [setup 4u_exefs]
  romfs/                4U RomFS (data, sound, per-language text...)        [setup 4u_romfs]
  mh4u_v11.elf mh4u.asm(.idx)  4U code as ELF, disassembly (+ dis4u.py index)   [setup 4u_asm]
  m19_unpacked/         4U Battlequarters arcs unpacked (arcpack layout)       [setup 4u_m19]
  gu_main/              GU main: mem.bin (flat), main32.elf, main.asm, asm caches; dti.pkl (maintainer's, optional:
                        the gu_class donor check of module/build.py)          [setup gu_code]
  gu_plt.json gu_pcrefs.pkl  GU PLT symbols (guemu.py), pc-relative refs (weapons4u.py)  [setup gu_plt, gu_pcrefs]
  gu/AppShaderPackage.mfx    GU shader package (material records)              [setup gu_shader]
  gu_stage/             GU stage files (tools/gu_stage_files.txt) + unpacked arcs   [setup gu_stage]
  gear_src/{armor,weapons}/4u + out/*.pkl   4U gear arcs + material template indexes   [setup gear]
  converted/em089/      Gogmazios dtbase / dttune (dt_convert.py, unicorn)     [setup dt_em089]

Maintainer's extra GU study files (not needed to build)
  gu/                   other MHGU pieces: player/ and resident/ arcs, rtld, sample EMC
  gu_quest/ gu_quest14/ GU quest files used as templates / references
  mhf/                  MHF-ZZ data for Magnet Spike: motions, player models, weapon/action tables (json/txt)
  gear_src/ (rest)      armor / weapon conversion work (4uall, gu, png, scripts...)

Code study (reverse engineering)
  mh4u_ghidra/          headless Ghidra project of 4U (functions.tsv, fstarts.txt)
  gu/ghidra/ gu/decomp/ headless Ghidra project of MHGU main + decompiled C output
  mhf/ghidra/ mhf/decomp/  same for the MHF game DLL
  apimap*.pkl apimap_match.txt apimap_table.md apialign*.txt monster_fn_pairs.pkl
                        4U -> GU function maps (tools/apimap*.py, apialign*.py)
  gu_classes.pkl gu_pcrefs.pkl gu_plt.json gu_emnum_uses.txt dti.pkl
                        GU class survey, cross refs, PLT, em number uses, 4U DTI registry
  fieldmap_cooc.pkl em089_ext.pkl dtmap/
                        4U -> GU enemy record / enemy data field maps (fieldmap.py, dt_map.py, dt_vote.py)
  em089/                Gogmazios class study: actions, motions, effects, EMC refs, external callees
  em001_cmd_4u.emc      reference 4U AI bytecode (Rathian)

Intermediate data
  converted/            converter work files (area sounds, BGM streams, per-monster dtbase/dttune...)
  m05_unpacked/ m08_unpacked/ m19_unpacked/  unpacked 4U stage arcs (m19 = Battlequarters)
  q4u_m19/              4U quest files on the Battlequarters
  stage_cache/          converted stage textures, cached by tools/stage4u2gu.py (slow to encode)
  stage_alias_report.json   output of the stage alias check (module/stage_alias.c)

Logs and outputs
  build_logs/<monster>/ one log per build.py step
  install_logs/         one log per install.sh run (rebuilt steps, switches, targets)
  release/v<x.y.z>/     packaged release zips, manifest.json, NOTES.md (-Packages), NOTES-main.md (this repository's
                        release) (tools/release.py); release_build.log
  scratch/              per-session working notes and throwaway scripts
```

### Outside the repo

Nothing: the build needs no other checkout. The GU helpers that used to come from MHGU_Editor (the maintainer's
save editor, github.com/Scrimas/MHGU-Save-editor) are vendored in `tools/gulib/`, and every GU input is made in
`dump/` from your own Ryujinx extractions. Each GU path can be overridden with an environment variable
(`GU_EXEFS`, `GU_ROMFS`, `GU_CODE`; `tools/paths.py`). `tools/dt_convert.py` and `tools/guemu.py` emulate GU loaders
with unicorn, from `.venv` (`requirements.txt`).

The maintainer's code-study files (Ghidra projects, function maps, `dti.pkl`, ...) were made with private scripts and
stay local; `notes/` records what came out of them.

## Build flow

```
your 4U / GU dumps (dump/)
  -> python3 tools/setup.py        derived inputs in dump/ (once; tools/doctor.py checks everything)
  -> python3 monsters/<name>/build.py   converters write monsters/<name>/romfs/ and gen/
  -> python3 maps/<map>/build.py        the arenas' converters write maps/<map>/romfs/
  -> python3 module/build.py       core + every monster's module/ -> subsdk1 + IPS (reads allocations.toml)
  -> python3 tools/release.py all  build + checks + zips into dump/release/v<core version>/
  -> python3 tools/release.py publish   the zips on MHGU-Definitive-Edition-Packages, the text of this repository's
                                   installer release (drafted by .github/workflows/installer.yml on the v<version> tag)
```

Feature and test switches are C `#ifdef`s, enabled with `GOG_DEFINES="NAME1 NAME2" python3 module/build.py`;
release builds use none of the test switches.

## How a monster port works (short)

1. **Identify**: find the 4U class, its em number, files and quests; reserve IDs in `allocations.toml`.
2. **Assets**: convert models, textures, animations, collision, effects, sounds into GU arcs.
3. **Register**: add the class to the relocated registry (`module/port.c`), name, icon, save slot (a new monster:
   `save = "lease"`, `module/save.c`).
4. **Behaviour**: reimplement the 4U AI / actions / shells in C under `monsters/<name>/module/`, mapping 4U engine
   calls to GU's (`tools/apimap*`).
5. **Content**: quests (at the rank matching 4U), arena / stage, music, items, armor, weapons, skills, Hunter's
   Notes, drops, gathering.
6. **Test** in Ryujinx (`GOG_MOD_ROOT=~/.config/Ryujinx/mods python3 module/build.py install`), read the logs,
   iterate.

A port is finished only when it is faithful to 4U in looks, arena, behaviour, music, SFX, quest ranks, drops and
gathering; stand-ins count as deviations. Details, pitfalls and per-monster lessons: `notes/porting-guide.md`.

## Rules worth knowing

- Never commit game data or anything derived from it (see `.gitignore`).
- IDs in `allocations.toml` never move once a monster has shipped.
- Multiplayer: every player needs the same monsters installed.
- Unequip a monster's gear before uninstalling that monster.
