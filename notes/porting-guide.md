# Porting an MH4U monster into MHGU: guide for a new session

Written 2026-10-19 from the Gogmazios (4U em089) port; content side (Phase 5b) added 2026-10-20. Example target:
Dalamadur, but everything here applies to any 4U-only monster. GU = MHGU 1.4 main offsets (runtime = 0x704000 + offset); 4U = MH4U v1.1 (EUR) code.bin addresses.
Mark every fact you write down as C (confirmed in code or data), S (strong) or G (guess).

## Repository layout (since 2026-10-20)
| path | what |
|---|---|
| `allocations.toml` | every game-wide ID a monster takes (em ID, registry index, file IDs, save slot, name / Notes entries, quests and board slots, DUMMY items, BGM IDs, stage folder, gear models, appended record counts) + the free pools; `python3 tools/alloc.py [show]` checks it |
| `module/` | core module: hook framework (build.py), `port.c` (monsters, data files, installed check, file IDs), `quest.c`, `items.c`, `gear.c`, `notes.c`, `main.c` (shared hooks) |
| `tools/` | core converters and helpers; `paths.py` (GU scratch / MHGU_Editor locations, overridable), `portdata.py` (data file writer / reader), `alloc.py` |
| `notes/` | core notes (this guide, registry, enemy-class, port, api-map, assets, data, gear-weapons, installer) |
| `monsters/<name>/` | one monster: `module/` (its C code, compiled into the core module), `tools/`, `notes/`, `package.toml` (version, C prefix), `build.sh` (every generator, in order) |
| `monsters/<name>/gen/`, `romfs/` | gitignored game data: its data file `<name>.bin` (+ the `.sec` sections) and its converted RomFS (= its assets) |

Gogmazios files named below as `tools/*_em089.py`, `tools/build_gog_quest.py`, `tools/gogreport.py`,
`module/em089*.c`, `module/stage*.c` or `notes/{port-checklist,stage,content-plan,em089-behaviour}.md` now live in
`monsters/gogmazios/{tools,module,notes}/` under the same names. Older notes keep the old paths.

How a monster plugs in (module/port.h): its tools write its data file (tables + text, never compiled into the core);
every registered monster's data file always installs, so appended gear IDs never move; the monster is INSTALLED when
its assets are present (its monster arc), which turns on its quests, spawning and quest-time hooks. The core hooks
loop over the monsters; a hook site used by one monster only (e.g. Gogmazios' stage gimmicks) keeps its handler in
that monster's module code.

## 0. Read first
1. This guide.
2. `monsters/gogmazios/notes/port-checklist.md`: the full Gogmazios log, more than 3000 lines. Do not read it end to
   end; `rg` it by 4U / GU address or topic. Warning: some `[ ]` / `[~]` lines went stale when later work landed.
   Check the code before trusting a "stubbed" or "not ported" line.
3. Topic notes:
   - `notes/registry.md`: the per-index tables a new monster index needs.
   - `notes/enemy-class.md`: the class chain, the DTI and ctor pattern, and vtable slots.
   - `notes/port.md`: how GU runs actions and how actions end.
   - `notes/api-map.md`: the 4U -> GU function and record mapping.
   - `notes/assets.md`: file formats.
   - `notes/data.md`: the data fields of the monster arc.
   - `monsters/gogmazios/notes/stage.md`: the arena and stage alias, plus the quest.
   - `monsters/gogmazios/notes/content-plan.md`: save slot, rewards, gear, skills, Hunter's Notes, quests (the content
     side, Phase 5b).
   - `notes/gear-weapons.md`: the weapon table formats and the choices behind gear_weapons_em089.py.
   - `notes/installer.md`: package layout and the warnings the installer must show.
4. The user's rules (section 1) and the memory files listed in MEMORY.md.

## 1. Ground rules (the user's, keep them)
- Edit files only with the Edit tool (Write for new files). Never use sed -i, Python or heredoc edits: every change
  must be visible as a diff. Read and search with shell tools (cat, sed -n, rg, rg --files).
- Use `sudo -A`. Never `cargo build --release` locally. Run long jobs in the background; announce anything over
  about 1 minute.
- No AI attribution in commits or docs. Never expose secrets.
- Ported game assets stay local (Ryujinx mods folder). They never go into a public repo.
- Install only when the user says so. Uninstall after each test. Keep test windows off the user's workspaces.
  Low test burden: the user plays and closes, you read the log, and you ask only about visuals.
- "Finished" = faithful to 4U in looks, arena, behaviour, music and SFX. The port is an ADDITION to GU, never a
  replacement.
- At most ONE helper agent at a time, freshly and narrowly briefed (a big-context spawn burns usage). Give it the
  files it owns and the files it must not touch, and forbid sub-agents and installs.
- Never call something "4U behaviour" before tracing every end condition in 4U code (memory
  feedback-faithful-claims). Never justify a choice with an unverified rationale: the user checks.

## 2. Inputs and environment
| what | where |
|---|---|
| 4U ROM | `dump/base/*.3ds`; `tools/ctr.py ls/x` extracts RomFS paths; listing in `dump/base_list.txt` |
| 4U extracted | `dump/romfs/<lang>/data`, monster arcs `/data/emNNN.arc`, data `/data/em_data.arc` (emd + etd) |
| 4U code | `dump/exefs_v11/mem.bin` (flat from 0x100000), disassembly `dump/mh4u.asm`; `tools/dis4u.py ADDR [N]`, `-f ADDR` (its function-start heuristic is sometimes wrong: walk back to the `push {.., lr}`) |
| GU code | `/home/scrimas/Projects/MHGU_Editor/scratch/main.asm` (rg `^ +ADDR:`), `mem.bin`, `py/asm.py` (asm.u32, asm.INS); `tools/gu.py` (pc-relative resolver) |
| GU RomFS | `/home/scrimas/Projects/MHGU_Editor/scratch/base_romfs.bin` (read through the helper scripts) |
| pairings | `dump/monster_fn_pairs.pkl` (1075 4U -> GU function pairs, 4U 0x6dd000..0x911b38), `dump/apimap.pkl`, `dump/apimap2.pkl` |
| emulation | `tools/guemu.py` (runs a GU loader under unicorn; use the MHGU_Editor scratch venv) |
| Ryujinx | title 0100770008dd8000, mods `~/.config/Ryujinx/mods/contents/0100770008dd8000/<mod name>`, logs `~/.config/Ryujinx/Logs` |
| headless runs | `tools/ryutest.sh run` (isolated `ryuroot/`, GDB stub on :55555; never touches the user's config) |

Ground truth for every format and every mapping: the monsters that exist in BOTH games (Capcom converted them, e.g.
4U em031 Kushala -> GU em024_00, em001 Rathian -> em001_00). Learn each rule from those pairs, by vote over all
pairs where possible (tools/dt_vote.py, dt_map.py, snd4u2gu.py selftest), then apply it to the new monster.

## 3. What a port consists of
1. **Monster arc** `nativeNX/arc/enemy/emNNN_00.arc` plus its 0xCC-byte file manifest (51 fields: models, MRL,
   LMT x4, XFS, EMC, attack / hit / body data, dtbase / dttune / dtbparts, effects PEL / PSL, sound call / bank /
   request, LCM, ...). File IDs are served by the `file_id` hook (module/port.c) from the monster's range
   (allocations.toml file_ids) and its data file section FILE (manifest + file table). Builder:
   `monsters/gogmazios/tools/build_em089_arc.py` (writes the arc, `em089_manifest.json` and gen/FILE.sec).
2. **Module** (subsdk1, `module/` + every `monsters/<name>/module/`, `python3 module/build.py [install]`): the class
   (DTI + a copy of uFestaEnemy's 286-slot vtable with overrides), the registry relocation (one entry per
   allocations.toml monster), hooks, and every behaviour / shell / effect / sound port. AArch32. Hooks displace two
   instructions into a trampoline; these must not be pc-relative or branches (build.py checks). The trampoline saves
   r0-r5, r12, lr at regs[0..7] and the caller's stack args start at regs[8]; a handler can rewrite them. A handler
   returning nonzero replaces the function (REPLACE_HOOKS).
3. **RomFS additions** = the monster's assets (`monsters/<name>/romfs/...`): BGM (tools/snd_bgm.py), quest arc
   (build_gog_quest.py), the stage alias arcs if the 4U arena is ported (tools/stage4u2gu.py), the map UI
   (tools/mapui4u2gu.py), and the gear models (tools/armor4u2gu.py, tools/weapon4u2gu.py). Never a copy of a GU
   file: another monster would ship the same path (build.py install refuses it); patch the loaded resource instead
   (the monster name is a NAME section applied to the loaded monsterName GMD).
4. **Content** (Phase 5b): the monster's save slot, materials, carves / rewards, armor, weapons, skill and
   decorations, Hunter's Notes entry and quests. The tools write them into the data file
   (`nativeNX/mh4uport/<name>.bin`, tools/portdata.py: sections ITEM, BUI, TBLA, TXTA, NOTE, NAME, SKIL, PWLF, FILE);
   the core patches the loaded tables (module/items.c, gear.c, notes.c), never ships resident arcs: UI mods
   replace resident.arc / resident_<lang>.arc (the
   user's HD UI v4 does), and shipping blacksmith.arc from the v1.0 RomFS could undo update changes.

## 4. Pipeline, in order
### Phase 0: identify (do not guess)
- The 4U em number. For Dalamadur it is NOT recorded anywhere in this repo yet. Find it from 4U data: the boss id of
  its 4U quests (quest arcs, see how `dump/q4u_m19/` was found in notes/port-checklist.md "Demolisher") or the 4U
  monster-name table. 4U em numbers do not match GU ones (4U em031 Kushala = GU em024).
- Check that GU really lacks the monster (GU large ems are 001..088; our Gogmazios is em 0x59 = 89, index 137).
- Pick a GU donor with a close skeleton / behaviour. It gives the dtbase / dttune base object, material
  templates, the shell classes to imitate and a test fallback. Gogmazios used Kushala (em024_00).
- Identify the 4U arena and whether GU has an equivalent. Gogmazios needed the Battlequarters (4U m19) as a new
  stage: done as an alias of GU stage 26 (Fortress) redirected to m28 paths while the quest runs (notes/stage.md).

### Phase 1: static study of the 4U class
- DTI and vtable: `tools/a4u.py` (dtis(), by_name(), vtables()). The action dispatch is 4U vt slot 44, which
  switches on work bytes +0x1ca (category) and +0x1cb (number). `tools/em089_actions.py` resolves the handler and
  the motions of every (category, number); adapt LO / HI / VT to the new class.
- The vtable slots the class overrides: `tools/slotmap.py em001` / `base` matches 4U slots to GU slots by features.
- AI: the EMC (`tools/emc.py`) holds the selectors and scripts; same format in both games. Native actions are
  `00 cat num`.
- Framework callees: `tools/apimap.py` / `apialign.py` map 4U helpers to GU through Rathian. Record fields:
  `tools/fieldmap.py`. Results so far: notes/api-map.md and module/game.h (each define notes its 4U address).

### Phase 2: assets -> arc
| asset | tool | notes |
|---|---|---|
| models MOD 0xE6 -> 0xD4 | tools/mod4u2gu.py | bones / remap / groups unchanged, vertices re-encoded; keeps 4U bone IDs, so 4U data needs no bone remap |
| textures | tools/tex.py | ETC1 -> BC1/3/4/5, Tegra block-linear |
| materials MRL 0x20 -> 0x22 | tools/mrl_build.py, mrl_anim.py | GU TEMPLATE materials (shader package differs); material animations converted separately |
| motions LMT 67 | copy as is | same layout. Root track = bone 0xff usage 4; end-frame vectors at anim +0x10 |
| EMC | copy, drop 4U's 2 trailing empty groups | |
| camera list LCM v4 -> v5 | tools/lcm4u2gu.py | 16-byte record prefix |
| emd / etd -> bodydata, hitsize, attackdata, XFS, dtbase, dttune | tools/emdata4u.py, dt_convert.py (unicorn venv) | voted mappings only; dtbparts stayed the donor's (break records installed at runtime) |
| effects EFL / EAN / MEF -> GU EFL + PEL / PSL | tools/efl4u2gu.py | PEL records in extra_records(); PSL from LMT event group 2 |
| sounds MADP / SNDB / SREQ -> GU types | tools/snd4u2gu.py | rules from Capcom's own monster pairs (selftest) |
| BGM | tools/snd_bgm.py | MCA -> Opus + own STQR in the monster arc, hook bgm_stqr |
- The arc builder's rules: only one agent rebuilds the arc at a time (`ARC LOCK:` line in the monster's checklist),
  and its file table (FILE section) may only GAIN entries (keep existing file IDs stable, inside its file_ids range).
- Check the model scale (Gogmazios 2.5, dtbase +0x15). Joint matrices include it.

### Phase 3: register the class
- Add the monster to allocations.toml (next registry index, its pools' next free values; `tools/alloc.py` checks)
  and give it `monsters/<name>/package.toml` with `code` = its C prefix (`<code>_register_class`, `g_<code>_dti`).
  build.py then grows every registry copy (REG_TABLES, one entry per monster, sentinel pair after the last,
  reg_u16 read at [index + 1], reg_mapicon by em NUMBER for a new number), patches the id <-> index bounds
  (`cmp #137` -> 137 + monsters, WORD_PATCHES 0x50B94 / 0x50C10) and the Notes bounds, and generates the descriptor
  table (out/port_monsters.c, module/port.h). Choose a free GU em number (> 89) or a free variant of a GU em,
  never the 4U number.
- The shared hooks already serve every monster from its descriptor: em_create / quest_prep (stand-in swap while its
  quest runs), em_arc_request (arc preload), em_record (donor record), file_id, name_index, stats_add / stats_hunted /
  save_hunts, quest board / unlock / clear, break rewards, items, gear, Notes. Monster-specific hook sites (BGM,
  stage alias) stay in the monster's code; a second user of the same site turns its handler into a core dispatcher.
- Class: `monsters/gogmazios/module/em089.c` is the template. ctor = uFestaEnemy ctor + our vtable + EN_WORK = record + 96; own fields
  after SIZE_uFestaEnemy. Overridden slots (game.h names): 125 ACTION (= 4U slot 44 dispatch), 119 STATE_FRAME
  (4U slot 40), 129 ACTION_START (4U 47), 127 ACTION_REMAP, 130 MOTION_FRAME, 132 PARTS_FRAME (4U 50), 133 AI_COND
  (4U 51, AI opcode 0x6f conditions), 118 SPAWN_SETUP, 253 THINK_BLOCKED, 168 (4U 75). 4U slot 64 (on-break)
  corresponds to GU slot 214, but em089 does not override it: breaks are polled in slot 132 (em089_break.c).
- The Gogmazios code is em089-specific (file names, EM089_ID checks inside shared hooks). For a second monster,
  copy into emNNN_*.c and make the shared hooks (file_id, set_target, set_action, ...) dispatch by em ID.

### Phase 4: behaviour (the bulk)
- One C handler per 4U handler, translated literally in 4U call order, 4U frame and timer values unchanged (the GU
  helpers apply the speed scaling). See notes/port.md for the framework: begin(), step bytes rec+0x1a1..0x1a3 (4U
  W+0x144..), chain() for setActionNext, and the end slots 247 / 249 (4U `vcall vt+0x164`). **A handler that never
  ends its action freezes the AI.**
- Mapped essentials (more in game.h / api-map.md):
  | 4U | GU | what |
  |---|---|---|
  | this+0xe28 (W) | this+0x1428 (rec) | work record; work struct = rec + 96 |
  | W+352 / W+368 | rec+0x10 / +0x20 | velocity / acceleration |
  | W+408 | rec+0x40 | position (y +0x44; ground y rec+0x5b4 ~ 4U W+0x624) |
  | W+424 / W+0x1ac | rec+0x50 / +0x54 | angle triple / yaw (u16 in u32) |
  | W+0x1c8 / +0x1c9 | rec+0x1ba / +0x1bb | state class / mode |
  | this+20 | this+28 | time scale (EN_DT) |
  | this+576 + k (layer 0) | this+0x4b0 + k | same inner layout: +68 blend left, +72 weight, +80 frame, +92 speed |
  | 0x94e350 / 0x9190c4 | 0xaff40 / 0xafda4 | setMotion / setMotionEx |
  | 0x91ab1c | 0xb0a24 | motionCheck(kind, out frac, s0, s1) |
  | 0xb05df4 / 0x90f994 | 0xb0a84 / 0xb0a00 | isMotionEnd / curMotion |
  | 0x91ab28 | 0xc0e78 | turnStep |
  | 0x91150c / 0x9165cc | 0x7cab8 / 0x7a8dc | rotateVel / accelVel |
  | 0x911cb4 | 0xbe5d4 | speedFactor (size scale) |
  | 0x92e9d4 | 0xbca40 | rest pair: y += value * scale, state class -> 1 (takeoff!) |
  | 0x9167ec | 0xbc8b0 | setTargetMode |
  | 0x9399c0 | 0x8282c(this, 1) | post-action think list |
  | 0x93334c | 0x7dc2c | attackEx (arm an attack slot; slots at rec + 0x998 + 184 * slot) |
  | 0x2fcc50 / 0x304d3c / 0x312484 / 0x301074 | 0x4efd74 / 0x4efe58 / 0x4efb98 / 0x4eff24 | sound at joint / on object / at position / move a playing sound |
  | 0x911f58 | 0xac0ec | item drop |
  | 0xbfe98c | 0x49eac | camera shake |
  | 0x91df20 | 0x712a4 | species row; 4U row +0x48 (emd word 20, map-hit sphere: 4 offsets + radius +48) = the block GU 0x712a4 returns directly ([dtbase+0x84]) |
- Shells: 4U posts uShellNNN objects through 0x660e88 (type = class). Port each as a GU uShellEnemy subclass
  (examples: module/em089_shell*.c for uShell050 tar blobs, 051 ground splashes, 016 beams, 005 tremor). Port
  their lifetimes completely: a shell's attack object (+0x168) clears byte +5 (= shell +0x16d) when the attack
  window (start + length of the attackdata record) runs out, and several 4U shells die on that.
- Effects: GU PEL records posted through em089_efx.c. A live effect that follows something needs GU's per-frame
  setters 0x32a45c(eff, pos, 0) and 0x8a7dc4(*(eff + 0x150), rot in RADIANS); request rotation is in degrees.
- Quest stats: use the monster's OWN 4U quest rows (em_nando_tbl, GU file 0xde1a, 141 x 32 B {HP, attack, defense,
  status x5}; the 4U copy is at 0xf3a330). Pick the GU row whose values equal the 4U row's.
- Logs: `logf("gogport: ...")` with a per-site budget. Every port-only guess gets a log line, so a test answers it.

### Phase 5: quest, arena, UI
- Quest: tools/build_gog_quest.py (G-rank Hub extra quest 11491 via the quest_group_fix / quest_unlocked hooks).
  Copy it for a new quest ID and boss.
- Arena: if GU lacks it, follow notes/stage.md (alias build, collision, SIS, gimmicks, lighting: the 4U unlit
  flag is MRL w6 bit 31, GU lighting comes from the template feature). Stage-specific engine tables matter
  (e.g. 4U arena point tables are per stage: 0x689f7c uses the em's emd +0x40 table except on stage 13).
- Map UI: tools/mapui4u2gu.py (area maps + whole map, transforms in its docstring).

### Phase 5b: content (save, items, gear, Notes, quests)
Order that worked: save slot -> materials -> carves / rewards -> second quest + subquests -> armor data on a GU
stand-in model -> weapon data -> descriptions / decorations / Notes -> gear models. Each step builds clean and is
testable alone (the user checks the smithy or one quest).
- **Save slot.** The save arrays (hunts, captures, sizes) hold registry indexes 0..136 only and every accessor
  bounds-checks, so a new index is silently not counted. Use an unused registry slot (dummy1..7 = indexes 105..111,
  ids 0x1064..0x106a; Gogmazios = 105). Remap at the right place: the quest-end tally 0x3a75c8 compares the
  monster ID with the hunt objective, so remap only the INDEX after `bl 0x50b64` (hook 0x3a75fc), never the ID at the
  entry (test 10:24: kill tallied, quest never completed). Readers: stats_hunted 0x3a3930, save_hunts 0x523104
  (Notes page, 8 more callers). Size records 0x526f48 index a pointer table without a bound: keep them off.
- **Items.** Free item IDs: the "DUMMY" materials 2977..2990 and DUMMY decorations 2889..2899 (type 3). Appending
  past 2990 needs ~24 code patches. items_em089.py -> section ITEM -> items.c patches the loaded rItemData
  (0x19237c) and the itemData_<lang> GMD strings (0xb83c48, every rGUIMessage load passes there: the TXTA text
  appends and the monster name hang off it too). 4U and GU share icon and colour numbers; 4U item record +10 of a
  decoration = decoration index + 1.
- **Table appends.** module/gear.c tbl_append: every GU table class shares one generated loader;
  gear_weapons_em089.gu_class(name, f32 version) finds its load exit (load + 0x3c), element alloc / free / ctor /
  parse and in-memory size, checked instruction by instruction. The tools write each appended block as a TBLA entry
  (path suffix, class, record size, records, `base` = the count the table must hold before it); the core runs the
  GAME's parser on the file-format records and refuses when the count differs (another mod, or a missing earlier
  block). Blocks go in allocations.toml order, so a later monster's base = GU's count + the counts of the monsters
  before it ([monster.append]; IDs never move once released). gmd_append does the same for strings (TXTA). Convert
  hex carefully when copying gu_class output (a decimal -> hex slip put one hook 0x40 off; the build caught it:
  "branch ... targets ... inside the patch"). A new table class needs its load-exit hook in build.py HOOKS or
  module/gear_hooks.txt.
- **Carves and drops.** tools/hagi_em089.py -> hagi s4 (G rank; s0..s3 GU filler). GU picks the shiny table set by
  enemy vtable slot 149 (0xac0ec -> hagi byte 14 + set); 4U picks it in common code 0x930bdc by em number. Port
  per-monster drop sets as a slot-149 override (em089_drop_set). Break rewards: hook 0x3a3874 answers the monster's
  own bui record (conditions = table 0x162a736 by break group).
- **Quests.** tools/build_gog_quest.py --source <4U quest> (fee, rewards, HRP, subquest = GU type 8, digit = break
  group or 7 tail sever); board slots by renaming DUMMY quest_group entries (allocations.toml quest_slots,
  module/quest.c, only while the monster is installed); 4U spawn byte 3 sits where GU keeps the Hyper flag: keep
  GU's 0 and return 4U's value from code.
- **Armor / weapons.** tools/gear_em089.py (armor series 127 B + create / level rows + skill tree / skill +
  Arcane decorations) and tools/gear_weapons_em089.py (14 classes: Base / Level / Msg / Create / Process,
  sharpness, bowgun ammo, bow coatings; one load-exit hook per table class, module/gear_hooks.txt; a weapon
  model's motion-set fix is a PWLF entry, a compound skill a SKIL entry). A smithy entry
  is listed once its first recipe material (flag byte 2) is owned (GU rule, test 10:39). Models keep their 4U
  numbers (GU did the same, and 4U-only numbers are free). Weapon motion sets (rPlayerWeaponList mGmkMotNo) may need
  a fix per model (gear_pwl 0x272910). Skills with no GU equivalent: new tree / skill records plus a has-skill hook
  (0xe0da0) that answers yes for the GU skills it combines.
- **Descriptions.** 4U gear descriptions are not indexed by ID: u16 index tables per part / class in the 4U exe
  (EXP_4U in both gear tools). Find such tables by vote over the gear GU took from 4U (GU text = 4U text).
- **Decorations.** decoData record k = item 2638 + k (getter 0x194230 accepts up to 2899, bound = loaded count);
  decoCreate rows bit-mapped in the save (288 bits, 275 used). Many 4U G decorations (Arcane, Honed, Cutting...)
  are reward-only in 4U: check the 4U recipe table (0xf553e0) before porting a recipe, and say so when a recipe is a
  port choice.
- **Hunter's Notes.** module/notes.c + notes_em089.py (section NOTE: list record, unlock record, anchor entry; texts
  as a TXTA append of HN_MonsterListMsg): three 123-entry tables (list 0x162d9f0 via data word 0x183ec4c, unlock
  conditions 0x162d1f8, display order 0x1631ef4) copied from GU's at module_init with one entry per monster
  (notes_entry = 123 + registry position), 7 loop bounds patched (build.py WORD_PATCHES; two loops are unrolled by
  two and read one record past the end: a padding record follows; an odd total needs the unrolled 0x55FF3C
  re-checked, build.py asserts), save bits 123..127 free (5 monsters at most). Texts: description = 4U emExp[em
  number], tips page = 4U HunterNote tip under its title.
- **Gear models.** tools/armor4u2gu.py (player bones 0-19 identical in both games, 20+ = cloth bones driven by the
  CTC; MRL templates from Capcom's own 4U -> GU pairs) and tools/weapon4u2gu.py (same pipeline + material
  animations). Converted arcs go to monsters/<name>/romfs/nativeNX/arc/player/com/{m,f}/<model>/ and
  arc/weapon/wNN/ (its assets: notes/installer.md has the warning about gear without its monster).
  GU adds edge meshes (zero-area quads on hard edges, format 0x0CB68015) that 4U lacks: mod4u2gu
  convert(edges=True), same rule for armor and weapons (none on vertex-colour glow meshes). 4U glow meshes with
  vertex colour (0x7BA7401B) become GU 0xCBF6C01A (vcolour=True). Weapon drawMode 0xECD3 -> 0xECF3 when the GU
  material is exactly BSAddAlpha + DSZTest + RSMesh, else 0xEFFF (weapon4u2gu drawmodes()).
  The helm XFS (hair shown per hairstyle) has no derivable rule: copy a GU helm's and check hair in game.
- **Weapon sounds.** tools/wsnd4u2gu.py `gogma <4U pl_*.arc dir>` -> arc/weapon/wNN/snd/<model>.arc, then mSrqrNo =
  mModelID in the weapon record. GU banks / requests are class templates: only the waves, key -> wave and the
  request IDs come from 4U. mSndMaterial (bone / iron hit set) has no 4U source. `check` / `selftest` verify.

### Phase 6: test loop
0. Rebuild the monster's data and assets from the dumps: `monsters/<name>/build.sh` (every generator in order, then
   `tools/portdata.py pack`; one line per step).
1. Build both variants and check for 0 warnings:
   `python3 module/build.py`, and with defines, e.g. `GOG_DEFINES="GOG_STAGE_ALIAS TEST_HP_PCT=55 TEST_RAGE=60"`.
2. Install only on the user's go:
   `GOG_DEFINES=... GOG_MOD_ROOT=$HOME/.config/Ryujinx/mods python3 module/build.py install` (exefs + every data
   file + the assets of PORT_ASSETS = comma-separated names, default all, `none` = none) into the mod folder
   "MH4U Port".
3. The user plays and closes. Read the log with `python3 monsters/gogmazios/tools/gogreport.py` (extend it for the
   new monster's lines; core lines start with `mh4uport:`) and ask only about visuals.
4. Uninstall: `rm -rf ~/.config/Ryujinx/mods/contents/0100770008dd8000/"MH4U Port"`.
Automated smoke runs without the user: tools/ryutest.sh. `build.py install` without GOG_MOD_ROOT installs into the
isolated ryuroot/; `ryutest.sh gui` boots it windowed on hidden workspace 10 (headless `run` aborts ~1.5 s in) and
its log (written to ~/.config/Ryujinx/Logs) shows the boot-time table patches (items, armor / skill / weapon /
decoration tables, Notes redirect) without a user test; the blacksmith and Notes-text loads come later (village).
Stop it with `ryutest.sh stop` (matches the cmdline: the gui process's /proc exe link is unreadable).

## 5. Lessons that cost time on Gogmazios
- **Trace every end condition before calling a report "4U behaviour".** The "permanent puddle" was a missing
  attack-window kill (shell +0x16d), not 4U data. The user checked a 4U video.
- **Heights:** the rest pair raises y before the hover motion (root track y 720 x scale 2.5 = 1800). A monster
  "stuck at 1800" was a correct takeoff.
- **Scale:** GU joint matrices include the model scale. A 10000-long 4U capsule is 25000 at scale 2.5 in both
  games.
- **Live effects** must be moved every frame by the port; posting once on a joint is not the same.
- **Stale notes:** the checklist kept "stubbed" lines after the code was wired. Grep the code first.
- **Corpus scope:** take format defaults from the matching GU population. The PEL record tail first came from the
  majority over all GU PELs (stages, weapons...). Gogmazios' footstep effects then stuck under him. The GU MONSTER
  majority tail (177 of 2648 records) is the right default, but not byte for byte: it switches on GU's colour
  override (+0x70 / +0x73 / +0x64 = 1 / 1 / 7, ground-dust colour; blamed for the white effects, which stayed
  white after it was switched off: see the EFL draw-field item) and places effects once
  (+0x36 1), so effects posted on a moving unit stopped following it. efl4u2gu.py: PEL_COLOUR_OFF, pel_follows().
  Check what each default byte does (checklist "White effects after the PEL_TAIL change").
- **Effect reference model:** a pos-only post through the monster uses the monster's attach model as reference: its
  2.5 scale and its height leak into the effect. GU shells post their own effects with the shell as target (flags 3)
  and keep the shell alive until the effect is dead (em089_shell.c pattern).
- **Reactions are separate:** 4U monsters can have their own category-10/11 (flinch, break, sever, trap) handlers in
  vt44. Port them with the actions, not as a placeholder.
- **Mesh index runs:** GU ends every mesh's indices with one 0xFFFF and its draw reads it. Without it each mesh
  gained one triangle stretched to the next mesh's first vertex: the stage's "black / distorted triangles" survived
  three wrong fixes (keyless tracks, lit flags, torch glow). Compare converted files with GU's own byte layout,
  not only with the source data (check_model compared against 4U and passed).
- **Hooks:** check the two displaced instructions and that nothing branches to the second one.
- **Registry:** every per-index table without a bounds check must hold the new entry, or the game reads garbage
  (Kushala's icon and duplicate entries were early symptoms).
- **Stage UI / gimmicks** use per-stage tables and offsets. When the alias swaps the art, swap the records too.
- Status-effect, damage and HP questions: the formulas matched in both games; differences came from the data rows
  and from hits not connecting.
- **"Written, never read" flags:** a monster's own code may not read a work byte that COMMON 4U code does. em089
  work+0xed was skipped as unread; the shared item drop (0x930bdc) reads it to choose the One-shot Binder table.
  Search the whole 4U exe for readers before dropping a write.
- **Death needs the GU end:** a GU death table ends with op 7 then 0xff; without op 7 the reaction never hands the
  monster to 12/255 and the quest never ends (tests 10:01 / 10:13).
- **Version of the data:** the 4U EUR v1.1 update ships only text archives (core_*.arc), identical in every string
  used here, and no monster data: the base RomFS etd is v1.1's. Kiranico sometimes shows another version's numbers
  (HP 18000 vs 17500).
- **Smithy visibility:** a new armor / weapon is listed only once its first recipe material is owned; "missing in
  the smithy" is usually that, not a broken table.
- **Monster gimmicks hide in generic classes:** 4U's cut-object update has `cmp W+0x1c0, #89` branches that turn
  Gogmazios' fallen Dragonator spear into a pile bunker (kind-36 record, stage timeline, player-owned hit); GU's
  port of the class dropped them, and an earlier stage survey called the pile "unreachable" because it never
  looked there. Grep generic 4U classes (cut objects, uStageGimmick, shells) for the monster's em ID before
  calling a feature unreachable, and ask the user what the thing does in 4U.
- **Online damage:** GU sends no damage packets. Every machine runs every attack against its own monster copy, but
  only the controlling machine (enemy+0x7420) applies HP / break / sever (0x97ddc) and ships them in the action
  message. So a gimmick hit must exist on the controller: spawn it on every machine from the replayed press (one
  per press), never only where isLocal(presser); triggers that need a sever poll the synced count on every machine.
- **Cut objects:** manifest field 1 = cut slot 0 (type 1, tail), field 2 = slot 1 (type 2); slot 2 never exists.
  spawnCutPart sets the type's detached bit and reward flag (7 / 6); a reward 4U does not give is suppressed by
  pre-setting the flag bit (0x9d458 skips a set flag). A 4U-specific behaviour is ported by giving that one object
  a copied vtable with its own move (slot 10), as module/em089_pile.c does.

## 6. Dalamadur: things to settle first (all open, verify each)
- Its 4U em number, class DTI / vtable, action table size, and whether it uses shells / effects shared with other
  4U monsters (a shell class ported for Gogmazios may be reusable if the 4U class is the same uShellNNN).
- Its arena (not in GU): which 4U stage, its gimmicks, whether the fight has phases tied to the stage. Budget for
  a stage alias like the Battlequarters one.
- Size: a very large monster means many bones, hitzones and break parts, possibly special camera code (4U LCM ids
  and the camera-event path 0x93457c -> GU 0xaa418, see em089_act.c) and special collision. Check its emd / etd
  layouts against emdata4u.py before building data.
- Registry and content for a second monster: one allocations.toml entry (index 138, Notes entry 124, save slot 106 /
  id 0x1065, name entry 106, the next DUMMY items 2986.. and decorations 2893.., its own file ID range, BGM IDs,
  UI icon cell) and its package.toml; the core needs no edit for those (Phase 3). Still open per monster: its quest
  IDs and DUMMY quest_group slots (only 11491 / 11492 and slots 1011009 / 1011003 are checked free: check more and
  extend the pools), and its gear tools: the Gogmazios ones compute IDs as the v1.0 counts, a second monster's must
  start at GU's count + alloc.offset(name, table) (allocations.toml [monster.append], frozen once released).
- Its own folder monsters/<name>/ with a build.sh like Gogmazios'.
