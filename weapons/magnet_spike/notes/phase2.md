# Phase 2: vertical slice on class 5

Goal: one Magnet Spike (wk400 model), held as GU's real class 5 (box type 12), playable in a quest on the moves
below. All the technical layers get proven here before Phase 3 brings in the full moveset.

## Decisions (user, 2026-10-29)
- Route: the real class 5 from the start (no Great Sword stand-in). The class-5 plumbing (equipment type 12, class
  object, files, class-byte sites) is part of this phase; Phase 4 keeps the menus / category polish.
- Moves: the slice below, Guild style.
- Sounds and effects: wanted, but deferred to a later phase.
- Work happens on branch magnet-spike, in the main checkout.

## Slice (MHF action numbers; buttons: GU on Switch -> the user's Xbox pad, positional Ryujinx mapping)
| Mode | Move | MHF input -> action | Xbox |
|---|---|---|---|
| Cutting | Vertical 1 -> Upslash -> Vertical 2 | tri: 0 -> 3 -> 4 | Y, Y, Y |
| | -> Finishing Slash | tri+circle: 152 | Y+B |
| | Upslash from idle | tri+circle: 2 | Y+B |
| | Horizontal 1 -> 2 -> 3 | circle: 6 -> 9 -> 10 | B, B, B |
| | -> Finishing Slash | tri+circle: 155 | Y+B |
| | crossings (MHF data) | V1 / Upslash -circle-> H1 (122 / 8), H1 -tri-> V1 (17), H2 -tri-> Upslash (13), H3 -tri-> V2 (5), V2 -circle-> H3 (126) | |
| | Guard Counter | R2: 14 | RT (proposal) |
| | Switch to Impact (idle) | SELECT: 90 | Back (proposal) |
| Impact | Down Swipe | tri: 18 | Y |
| | Triple Strike 1 -> 2 -> charge | circle: 32 -> 33 -> 34 (hold) | B, B, hold B |
| | -> Triple Strike 3 / Charged Strike | release: 208 -> 36 / 35 (timed) | release B |
| | Supplex | tri+circle: 26 | Y+B |
| | Switch to Cutting (idle) | SELECT: 91 | Back (proposal) |
| both | draw; drawing attacks (by the weapon's mode) | sheathed tri = draw; Cutting: moving tri = 78 (Vertical 1); Impact: tri+circle = 79 (Horizontal 1) | Y; moving Y; Y+B |
| | roll, walk, sheathe | cross 202, stick 40/41 and 44/45, GU's own sheathe | A, left stick, X |

Input map: MHF tri -> GU X (Xbox Y), circle -> A (B), cross -> B (A), R1 -> R (RB), R2 -> ZR (RT), SELECT -> minus
(Back), L2 aiming -> Phase 3. ZR / minus = GU's virtual bits 0x800 / 0x200 (confirmed in test 1 run 6: Guard Counter
and the mode switches ran from the user's RT / Back).
Cancels to actions outside the slice (R1 combos, aiming, Impact guard 112) are ignored until Phase 3.

## Work and status (2026-10-29)
2.1 Research: done (gu-weapon-class.md "Command system", "Class 5 in GU", "Equipment side", "Hit data").
- Commands: GU's cancels are data (per-style command tables with Pre / Start / End frames, 2000 + k = the class's
  table k), MHF's map onto them 1:1 (per step; later steps keep the buffered presses). Inputs: class translator
  slot 139 sets class ids from GU's virtual buttons and press combos.
- Frames: GU motion frames are 1/60 s like MHF's (GU's run 384 cm / 43 frames = 5.4 m/s, MHF's 4.3 m / 41-49
  frames at 60 fps; the command windows and the monster clock agree): MHF frame numbers carry over 1:1.
- Common actions (drawn idle, walk, rolls, draw, sheathe) are GU's, playing fixed bank-5 slots; slot 215 "second
  mode" picks the second-mode slots (20 idle, 24 walk ...). Class 5's model ids are MH3's `mbgNNN`.
- Hits: GU shapes sit on player joints only (8 / 12 / 255): MHF's blade shapes are posed into the holding hand.
- Leftover bowgun traits of class 5, all patched (build.py ms_patches): factory case, weapon part, gunner helper and
  8 gunner sites, two 0x47 masks, two class switches, 2 + 6 per-class tables (class 0's melee values).

2.2 Tools: done. `tools/lmtcodec.py` (LMT track codecs, byte-exact on all 11071 GU player tracks), `tools/xfs.py`
(resource fields), `msmot.py` (motions), `mshit.py` (HDP / HTS), `msbuild.py` (everything: romfs/ + gen/, both
gitignored; `gen/report.txt` lists the slot plan, hits and tables).

2.3 Module: done, MS_SLICE builds only (weapons/magnet_spike/module: ms_class.c, ms_act.c; build.py hooks and
patches; install.sh switch "Magnet Spike / MS_SLICE"). The test build adds Magnet Spike ID 1 to the item box.

2.4 User tests: next, on the main Ryujinx and the real save (user's choice; backup
dump/save_backups/2026-10-29_before_magnet_spike; install.sh keeps MS_SLICE on, since a build without it crashes on a
save that holds a Magnet Spike). Test 1 = model, draw, moves, chains, hits (log); the log also prints every held-button
change (to identify the Minus / ZR bits) and every motion slot a class-5 hunter asks for (to check the common slots).
- Test 1, run 1 (2026-10-29): crash when equipping the Magnet Spike in the village (0x29ccdc, slot 80, read 0x10000).
  Cause: the factory hook (0x275bc8, common to every factory kind) gave the quest vtable to the village's generic
  class (kind 1, 0x2740 B), whose slot 80 then checked fields past the object's end (+0x32a4..). Fixed: kind 0
  (quest) only. The save was not written (both slots = the backup's hashes).
- Test 1, run 2: no weapon model (village and quest), and after the moving draw attack (78) nothing worked (move,
  sheathe, attacks). Causes: (1) GU's weapon setup resolves the model, the weapon motions and the pwl through
  per-class file-ID tables that leave class 5 at "no file" (gu-weapon-class.md "Weapon setup"): patched to MH3's
  class-5 IDs; (2) the return to neutral 0x2b6e94 takes 7 arguments and the module passed 4, so the set-action flags
  were stack garbage: now GS's (p, 0, 4, 0, 0, 0, 0). The log also showed GU's +0x1444 press combos only before their
  simultaneity window closes (0x40001 = X pending): GS's translator reads the same bits, kept.
- Test 1, run 3: the model shows. Sheathed it hung in its bind pose (screenshot: parts spread); the drawn weapon did
  not match the motions (to look at, with the state trace); still stuck after the draw. Causes: (1) GU loads the
  class command list as file 27 + class * 6 + style (0x29b514) and names the styles guild / old / airhike / bushi /
  kizuna / tatsujin; msbuild used English names for 1-5, and the user plays Alchemy (5), so class 5 had no command
  tables after the draw; (2) GU's weapon sync plays weapon index 0 for every sheathed motion and wg05_00 had none;
  (3) vt+0x168 (the sheathed-command picker's "state") is the style, so every draw was the moving draw attack. Fixed:
  GU's style names (every style gets the Guild moveset until styles are decided), index 0 = the Cutting form (S),
  moving = a locomotion action (act_st 2). (The user played Valor, not Alchemy: GU's style 5 is Valor.)
- Test 1, run 4 (Guild and Valor): sheathed form better. The new state trace showed the draw attack and the drawn
  idle running right (motion 5001, weapon motion 1, table 2000) but no command ever fired from a class table:
  GU resolves a command list's CmdBase references while the list loads and msbuild put the list first in its arc,
  so every reference stayed null (the command step skips those). Fixed: the list last, as in GU's arcs; the trace
  now counts each table's unresolved commands. Inputs: GU's R is 0x65f93c (0x40, or 0x800 with the other R option):
  the test mode switch uses it (0x1000 never showed in any log).
- Test 1, run 5: Vertical 1 -> Upslash chained (commands fire, 0 unresolved), then stuck in Upslash; in every
  motion the weapon sat away from the hands (screenshot: blade in the ground). Causes: (1) MS_FRAME read +0x4f4,
  GU's blend countdown (0x53a0d8 / 0x53a0f8), not the frame: no frame event fired (Vertical 1's attack at 40) and
  Upslash's "until frame 14" step never ended (its windows closed at the end of the 15-frame motion). The frame is
  +0x4fc; steps and events now use GU's own check 0x280e4c. (2) Read as "GU hard-codes class 5 to attach state 4"
  (wrong, see run 6): hook on 0x3078b8, the weapon in hand on joint 8 with no offset. (3) Slots 2 / 3 are GU's draw /
  sheathe (GS's events), not MHF 1004 / 1001 (walk / idle): GS's motions until MHF's are found. RT / Back gave
  0x800 / 0x200 in the button log (now Guard Counter / mode switch, S until the moves confirm them).
- Test 1, run 6: every slice chain runs and ends (Vertical 1 -> Upslash -> Vertical 2 -> Finishing Slash, the
  horizontals, Guard Counter on RT, the mode switches on Back, Down Swipe), the attacks arm at MHF's frames. Still
  wrong: the weapon upside down and off the hands (screenshot), and always the Cutting form. Causes: (1) the attach
  hook never ran: 0x3078b8's third argument is the weapon's part type (class 5 = GS's 0), so GU attached the Magnet
  Spike as a Great Sword, with GS's grip (10, 0, 58) cm and 180 deg about z; the hook now tests the hunter's class
  byte. The offline FK check confirmed joint 8 = bone 14 (place and orientation), so no offset is right. (2) GU's
  common idle / walk name their second-mode slots only for SA / CB: after the switch to Impact the hunter went back
  to the Cutting idle 5001 (and its weapon motion); the unit setter now maps 5001 / 5004 to 5020 / 5024 in Impact.
- Test 1, run 7 (log 22-34-47): the user confirmed the model ("Done, all good to go"): the weapon in hand on joint 8,
  the Impact idle / walk with the Impact form (5020 / weapon 0x14), every slice chain of both modes (0 -> 3 -> 4,
  1, 6 -> 9 -> 10, 14, 18, 32 -> 33 -> 34 -> 36, 90 / 91), no crash, the save unchanged (all 4 hashes OK).

Done when every slice move plays at MHF's timing and looks like the preview, the weapon transforms and changes
hands, hits deal MHF's motion values, and a full quest runs without a crash.
**PHASE 2 DONE 2026-10-29** (run 7). The stand-ins below carry over to Phase 3 (notes/phase3.md).

## Great Sword code still used by class 5 (must be empty or justified before Phase 2 is done)
- Object layout and constructor: GS's (0x3340 B, base ctor 0x2990bc, GS fields 0x3328.. unused); +0x3320 = GS's
  3DS module name "roPlayerQuest00.cro" (inert on Switch, S).
- Slot 82 (resource setup): GS's function = common setup 0x29a498 + manager group 35 (0x48c388; each class has its
  own group, meaning S).
- Slot 443: GS's function (in states 9 / 10 / 11, at GS frames, common actions 0x172-0x174; meaning S).
- Weapon attach off the hand (sheathed, the draw's first and the sheathe's last frames, the village): GU's Great
  Sword path (ms_attach passes class 0: GS's pwl carry joint and record, 0.8 scale).
- Body motion slots 2 / 3 (draw / sheathe) and the GU_COPY slots: GS's motions with GS's events.
Everything else GS overrides is a Magnet Spike function or the common default (ms_class.c s_defaults).

## Other stand-ins and test values (Phase 2; each has a later fix)
- pl_w05 (class parameters) = GS's values; GU's common code reads some by index.
- pwl (display / carry types) = GS model 1's, and class 5's pwl files are GS's pl_w00_gNN (its file-ID base points
  there; GU has no pl_w05 files): the sheathed placement is GS-like until MHF's is read.
- Camera lists (w05_m.arc) = GS's.
- Effects and sounds (w05.arc) = GS's lists and files under the class-5 names; weapon sound arcs
  arc/weapon/w05/snd/001, mat_b, mat_i = GS's (sounds / effects phase).
- Common motion slots without an MHF equivalent found yet: GU's shared motions (GS's copies), the draw / sheathe
  (2 / 3, GS's: MHF's are not in w13's part 0, S a shared bank); MHF guesses for 5-7, 14-16, 32 / 33, 80 / 81: the
  motion log checks them. During GS's draw / sheathe the weapon shows the drawn idle's form (no weapon motion).
- Hit data: KO / exhaust and the other fields from a GU template entry (GS cut / Hammer impact); i16[4] capped at
  250 (Charged Strike 338 kept in i16[26]).
- Weapon record: Great Sword 1's level row (sharpness), raw 200 (MHF stats -> GU scale is Phase 5).
- Styles: every style's command list is the Guild set (the user decided Guild only; other styles later).
- Sheathed weapon form: the Cutting form (the drawn idle's first frame; MHF keys no sheathed weapon motion, S), on
  the Great Sword's carry placement.
- Icon: GU's own type-12 icon, a bowgun (the leftover MH3 bowgun slot); MHF's Magnet Spike icon is Phase 4
  (own category). The name shows blank until then (no type-12 text getter).
- Impact mode: only the drawn idle / walk play Impact motions (5020 / 5024); GU's other common actions (turns,
  rolls, ...) keep the Cutting slots in Impact until Phase 3 maps their second-mode pairs.
- Not run yet: MHF events guard, armor, speed, turns, shake (logged once each).
