# Magnet Spike notes: where to start

Port of MHF-ZZ's Magnet Spike to MHGU's class 5 (branch magnet-spike, switch MS_SLICE). Marks in every note: C =
traced in code / data, S = strong inference, G = guess. Start with phase3.md "Status" and "Deviations".

## Notes
- phase3.md: current state (Status, Weapons and smithy, Deviations: reference), then one section per test 1-22
  (history: what was believed and changed at each test; "superseded" pointers where a cause was later disproved).
  "## Test 22" is the next checklist.
- mechanics.md: MHF's mechanics traced in mhfo-hd.dll and how the module ports each (reference): time and units,
  frame events, i-frames, inputs, gauge, guard, charge, marker / attraction / repulsion, aim view and reticle, pin.
- behaviour.md: MHF's moveset as players know it (guide / chart, G) and how MHF runs it from data (C; reference).
- phase2.md: the Phase 2 vertical slice (class-5 plumbing, run 1-7 history) and the GS code class 5 still uses.
- gu-weapon-class.md: GU's weapon-class anatomy (code, files, commands, hit data, class 5, equipment type 12;
  reference, with a few Phase 1 guesses marked superseded).
- assets.md: MHF inputs in dump/mhf, motions, skeletons, weapon grip, models, MHF's effect format and the effect
  conversion (reference; "Conversion" opens with the current state).
- effect-posts.md: where and when MHF posts each effect, its per-motion keys and follow modes, GU's post handle and
  effect build (reference).
- gu-efl-units.md: GU EFL entries and units (element, emit, move, Billboard, Model: transform, look, blend, limits,
  record masks; reference). gu-efl-move.md: GU's move block and the MHF-path -> kind-5 recipe (reference).

## Tools (weapons/magnet_spike/tools)
- msbuild.py: builds everything (romfs/ + gen/ms_data.inc, gitignored; gen/report.txt) from dump/mhf and the GU romfs;
  `msbuild.py report` prints the plan only; MS_MHF_FX=0 leaves MHF's effects out. Library modules: msact, msmot,
  mshit, msfx, msfxposts, mhffx / mhffx2gu, mhfmodel, msgun, mshud, msgrip, fmod2gu, aan, sdt.
- effcheck.py ARC [SUBSTR]: replays GU's effect-load / Model-unit / record-mask conditions (msbuild stops on a problem).
- fxplace.py [--arc A] [--yaw DEG]: where the effect models land in GU against MHF's math.
- fxlook.py [--effect fc5:38]: MHF's look against GU's draw, contact sheets in gen/fxplace/look/.
- fxbudget.py [--log LOG]: GU's effect capacities, our EFLs placed in GU's corpus, a test log's peak load.
- efldump.py ARC EFLPATH [ENTRY]: GU EFL fields by name (`--raw` adds the unknown words).
- ms_icon_hdui.py: paints the Magnet Spike icon into the maintainer's HD UI atlas.
- ghidra/decomp.sh PROJECT_DIR NAME PROGRAM OUT ADDR...: decompile by address from a headless Ghidra project
  (ghidra-analyzeHeadless on PATH, else /opt/ghidra, or $GHIDRA_HEADLESS); Decomp / Xrefs / ExportFuncs / MakeFuncs
  .java are its scripts.

## Build and verify
- `python3 weapons/magnet_spike/tools/msbuild.py` (runs effcheck on w05.arc), then
  `GOG_DEFINES=MS_SLICE python3 module/build.py`; install with the maintainer's install.sh (MS_SLICE on).
- Offline checks after a build: effcheck.py on the built w05.arc, fxplace.py, fxlook.py, fxbudget.py.
- Environment: `python3 tools/doctor.py` (the Magnet Spike inputs are its "Magnet Spike:" lines).

## Test logs
The maintainer plays and closes the game; the module writes `msport:` lines into the Ryujinx log. Copies:
dump/mhf/test_logs/ (ms_testN_Ryujinx_*.log up to test 17, testN.log since 18). Each test section in phase3.md names
its log and the lines to read.
