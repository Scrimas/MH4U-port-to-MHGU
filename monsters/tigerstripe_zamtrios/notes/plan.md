# Tigerstripe Zamtrios port: plan (approved 2026-10-20)

Source: MH4U em092 (class uEm022, shared with Zamtrios em022). Target: GU Zamtrios class uEm067_00, **variant 1**
(GU ID 0x143, arc `nativeNX/arc/enemy/em067_01.arc`). Arena: GU Dunes (stage 5) = 4U Dunes day (stage 17), user's
decision. Phase 1 study: [phase1-variant-map.md](phase1-variant-map.md). Process: notes/porting-guide.md.

## IDs (proposed in Phase 0b, written to allocations.toml in Phase 2)
| what | value | note |
|---|---|---|
| GU ID | 0x143 | em 67, variant 1 (GU ships only em067_00) |
| registry index | 138 | after Gogmazios 137 |
| save slot / name entry | 106 / 106 | `dummy2` |
| Notes entry | 124 | |
| quests | 11493 | 4U m10821 "Grand Finals Confrontation" (free: no file, no list entry). m10830 "Advanced: Tiger-sharq" dropped (frenzied spawn: GU has no frenzy; user 2026-10-20) |
| quest board slots | Phase 4 | DUMMY placeholders (group 127), chosen as for Gogmazios (notes/stage.md section 8) |
| materials | 2986..2990 | 4U 1357..1361: T.Zamtrios Shard, Piel, Grandfin, Sawtooth+, Tailbrand |
| file IDs | own range after Gogmazios' | |

## Phase 2: register the monster and build its arc (no behaviour code)
1. allocations.toml entry (IDs above).
2. build.py support for a monster without its own class (`package.toml` names GU's uEm067_00): its registry entry
   reuses GU's class, its module only holds hooks gated on `variant == 1`. Gogmazios' build output stays
   byte-identical.
3. Arc `em067_01.arc` from 4U em092 with the existing converters: models, textures, materials (GU em067_00's as
   templates), motions and EMC copied as is, effects, sounds, shell data; body / hit / stat data converted as for
   Gogmazios, differences from GU's own Zamtrios values reported before choosing.
4. Check whether GU's quest loader accepts 0x143 directly; if not, the same stand-in swap as Gogmazios.
5. Headless boot test: spawn, variant-1 motions, no crash.

### Phase 2 status (2026-10-20)
- Done, static checks only (no in-game run yet: the user is playing, nothing installed):
  - registry: allocations.toml entry; build.py `gu_class` (registry DTI = the donor's, checked against
    MHGU_Editor dti.pkl: index 56 = uEm067_00), optional ui_icon (donor's), no class registration; Notes bound
    0x55FF3C = count - count % 2 (odd counts now fine); data-file header name compared on its 16 bytes (port.c);
    TEST_SWAP_PORT (test swap to any ported monster).
  - arc (tools/build_em067_01_arc.py, build.sh steps dt / arc / pack): own model / textures / materials, XFS
    (GU states filtered), 4U motions, camera, EMC, effects (tools/efl4u2gu.py effect_set), sound
    (tools/snd4u2gu.py monster_entries), bodydata (GU - 2 records), dttune (GU + 42 bytes of 4U deltas); 15 + 2 own
    file IDs 0x10740..0x10750; the rest shared from em067_00 under its paths / IDs.
  - Gogmazios outputs byte-identical after the converter refactors (arc, manifest, FILE section).
  - diagnostics: module em067_01_diag.c (hook 0xf78f98, "tzport:" action / motion log), tools/tzreport.py.
- Next: boot + spawn test (TEST_SWAP TEST_SWAP_PORT=1, any Zamtrios quest) once the user allows installs; it also
  answers step 4 (spawn through quest_prep / em_create with 0x143).
- Open items found while building (for Phase 3 / tests):
  - LMT events of 19 em092 motions name MEF id 1100, which em092's MEF lacks (4U's resolution not traced).
  - em092_200 EFL is in no MEF record (4U code posts it): Phase 3.
  - 4U tExtendMap (body / fat body) has no slot in the GU templates: dropped (look check).
  - group 50 (eye + m03_virs) shown by 4U under condition 10 (not traced), hidden here as in GU.
  - 4U material animations (2 x 15 frames on body and fat body) not ported: GU's class asks for none.
  - fat body material type 1 (GU's rename) is a guess (S).
  - GU's own-bank requests 212 / 220 / 221 / 230 have no em092 wave group: silent if GU's code posts them.
  - qe006 / qe013 effects ship under the same 4U paths in Gogmazios' arc (Battlequarters soil) and here (Dunes
    soil): in a quest with both, the first arc loaded wins.

### First in-game test (when the user allows installs)
- Build with GOG_DEFINES="TEST_SWAP TEST_SWAP_PORT=1" and play a quest on GU's Dunes (stage 5): every large
  monster becomes Tigerstripe. A Dunes quest also answers the area-data risk below.
- Read the log with monsters/tigerstripe_zamtrios/tools/tzreport.py (actions reaching no GU handler, variant-1
  motions, file IDs); ask the user only about looks (model, tExtendMap, eye group 50, colours, effects' sand tint).
- Area data risk (G): GU uses Zamtrios only on stages 9, 14 and 20 (questData scan 2026-10-20); its area_link /
  area_select / area_patrol / map_info (XFS / MTD, shared from em067_00) may not cover stage 5. Stage arcs carry
  their own enemy\area_patrol\_mapNN / area_select\_mapNN (Gogmazios notes/stage.md), maybe a fallback. If
  Tigerstripe never changes area on the Dunes: borrow stage-5 data from a GU Dunes monster.

## Phase 3: behaviour gaps (only where GU's variant-1 code differs from 4U)
1. Exact walk of em092's EMC (not the heuristic tokenizer): which gap actions are reachable.
2. Shells: uShell012 subtypes 40..43 (+ the 2100 range rule), uShell016 subtypes 40 / 48.
3. Gate the CAT2/7 tremor (GU f6e5c8) to variant 0.
4. The reachable missing actions (7/77, 7/78, 7/200, 7/201, category-3 ledge chain) and effects (effect-manager
   id 8, uMhEftCtrl000 (13, 68), 0xc0aa20 skip).
5. Multiplayer: hooks only adjust GU's own code paths; damage stays on the controlling machine; check each shell.

### Phase 3 status
- 3.3 done (static): module em067_01_gaps.c, hook 0x48c4f0 skips the 2/7 tremor post (return to 0xf6e5cc) for
  variant 1, as 4U. The rest waits for the first test's action log (which gap actions the EMC really reaches).

## Phase 4: content
1. Move the Gogmazios content tools (items, gear, Notes, quests) into shared tools with per-monster inputs;
   Gogmazios' data file stays byte-identical.
2. Tigerstripe: 5 materials, carves / rewards, armor (S or Z: from 4U's recipe tables), 17 weapons in 8 classes,
   jewels if any use its materials, Notes entry, name, icon, 2 G1 quests on Dunes (day).
3. Music: GU's Zamtrios theme expected to apply through its em-type check (confirm 4U uses the same theme);
   sounds from em092.

### Phase 4 status
- Shared tools (Gogmazios outputs byte-identical: every gen/*.sec, gear_hooks.txt, 16 quest files): tools/items4u.py
  (materials, break rewards, 4U text readers msg4u / gu_text), tools/notes4u.py (Notes entry, text base from
  [monster.append] notes_text), tools/quest4u.py (4U quest text / rewards, GMD writer, v1.4 arc layout).
- Tigerstripe: NAME (4U emName[92], 5 languages), Notes entry 124 (4U emExp[92], no tips page, type 6, threat 6,
  after Zamtrios, unlocked by 11493); allocations: quests 11493 / 11494, board slots 1011048 / 1011049 (not in the
  event download catalog), stand-in 0x43.
- Finding for Gogmazios (not changed): its slots 1011009 / 1011003 are in the event download catalog 0x1595e98, so a
  save holding those downloaded events may clash with the renamed entries (to verify, user's call).
- 4U content data: notes/content-data.md (helper, 2026-10-20).
- Quest stat rows (C, also fixed Gogmazios' quests): 4U +0x34 = {u16 size, u8, HP, attack, other, u8, u8} (spawn copy
  0x68aa30 -> work +0x414..+0x416; HP 0x934084, attack 0x922d48, defense 0x922d78); +0xE8 = board icons.
- Done (static): items_em067_01.py (ITEM: 5 materials, 4U prices, GU Zamtrios categories; BUI: 4U groups 0/2/3/4/5
  -> GU conds 10/20/30/40/50, 4U group 1 = frenzy crystals left out), hagi_em067_01.py (own carve files s0..s4 in
  the arc, IDs 0x10751..0x10755: 4U body table, 4U shiny table in both GU shiny sets), build_em067_01_quest.py
  (11493: template q0011111 G1 Dunes; 4U spawn area 4 (-996, 57, 2142) = GU m05a04d floor y 57.2; rows 60/100/82
  = GU rows with the same values; subquest code 2 = top fin; rows A / B from 4U, row B's 0x8003 list as condition
  1; slots 2 / 3 the template's G1 coin tables; board icon = Zamtrios').
- Open: no small monsters (4U spawns Bnahabra and Hermitaur, the text names them; GU has no Hermitaur); boss byte 8
  = 2 and size table 5 copied from GU's G Zamtrios hunts (meaning not traced); capture rewards not looked at.
- Gear (user choices 2026-10-20; tools/gear_em067_01.py on the new shared tools/gear4u.py + tools/weapons4u.py,
  Gogmazios' gear sections and gear_hooks.txt byte-identical after the move):
  - armor Zamtrios Z (series 1289 / 1290, template GU Zamtrios X 851 / 852): defense 86 / 46 scaled like Zamtrios X
    -> 104 / 62; FreeElemnt (no GU tree) dropped; Meaty Piel -> Meaty Hide+; level-row Hyper Zamtrios Piel ->
    T.Zamtrios Piel; template scraps (Heavy Zamtrios Scrap) kept; models 436 / 437 (tools/armor4u2gu.py).
  - 19 weapons (Kiranico's 17 + Carnelian Lance -> Crystalis), own lines (create, then upgrades); Paralysis (Lance's
    hidden 4U value made visible); bows from kiranico's page data (Blast arc shot, Spread/Rapid charges, coatings
    Power / Poison / Para / Paint); IG Culldrone; recipe substitutes: Rhenoplos Bone -> Large Herbivore Bone,
    B.Diablos Cortex -> Diablos Cortex, D.S.Queen Pectus+ -> S.Queen Pectus+, Blackcurl Stouthorn -> Diablos
    Hardhorn, B.Tigrex Hardfang -> Tigrex Hardfang, Dire Blastheart -> Tigrex Mantle; 13 4U sharpness bars appended.
  - sounds: each 4U weapon arc holds its line's parent set (Lance 90: lan049), GU ships them all: mSrqrNo = that set
    (44 / 55 / 49 / 35 / 43 / 30 / 38 / 21 / 12), no sound arc written (GU's unused snd/090.arc left alone).
  - motion sets (pl_wNN at the 9 model numbers) all point at existing gNN arcs: no PWLF fix (skeleton fit: smithy test).
  - converters extended (Gogmazios' arcs byte-identical): armor4u2gu ships 4U env textures GU dropped (env_p052 /
    env_p076) and has the weapon converter's relaxed template match; weapon4u2gu ignores MRL params whose texture
    index is past the list (a float misread as a slot); mod4u2gu reads 4U vertex format 0x43FB3015 (2 weights +
    tangent, 32 B; 600 4U weapon arcs use it).
- Not ported: the four other-line weapons whose recipes use a TS material (SA Vermilion Bloodaxe, HH Crabby Castanet,
  Parahazard Call+, event Hunter Master): their lines are not in GU.
- Music (C, static): 4U has no battle theme for em 22 or em 92 (ROM sound/bgm/battle: no bgm_em022 / em092), so
  4U plays the area's battle music; GU's theme selector 0x4e60d4 sends em 67 to its default branch (stage theme,
  jump-table entry 55 = 0x4e63c4) as well: Tigerstripe on the Dunes plays the Dunes battle theme in both games.
- Next: the board / HUD icon (needs the user's HD UI files: with an install), then the first in-game test.

### First in-game tests (2026-10-21, user)
- OK: spawn through the stand-in, own files served (incl. carves), carves, break rewards, gear in the smithy
  (models), Notes entry; Gogmazios quests on the Battlequarters again after the alias became the default.
- Fixed: armor dye = 4U record +19 (gold 0x36; the Zamtrios X template's icy 0x0b made it silver; Gogma -> 4U's
  0x29, user); body / fat body = 4U E0 materials with their sphere maps (GU em019 E0 template; the puffed belly was
  black); quest clear rule +0x1d = 0 (one hunt): the two-hunt template's 1 made the clear check wait for objective
  1 too; the kill did complete objective 0 (9/143 -> 29). A first guess (quest type 1) changed nothing: reverted.
- Open: quest 11493 is built with HP row 0 (5 %) for the check: rebuild at full HP (row 60) after the user's kill;
  remove the tally diagnostics (module/main.c stats_add / stats_exit) before a release; paralysis-ball shells
  (notes/shells.md, helper research); board icon (later, with the installer).

## Phase 5: tests (user sessions)
Quest spawn, kill (TEST_HP_PCT=5), gear check, then the two-instance multiplayer test.
