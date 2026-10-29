# MHGU weapon class anatomy (what Magnet Spike has to provide)

Read off MHGU 1.4 (base RomFS + main), Charge Blade (class 14) as the reference. C = confirmed, S = inferred.

## Code (C unless marked)
- One player class per weapon class: `uPlayerQuest00..14` (+15, probably the Prowler), all derived from
  `uPlayerQuest` (386 vtable slots; the weapon classes' vtables are ~556 slots). Vtables: 00 0x1749a88,
  01 0x174a354, 02 0x174ac20, 03 0x174b4f0, 04 0x174bdc4, 06 0x174c694, 07 0x174cf64, 08 0x174d838,
  09 0x174e110, 10 0x174e9e0, 11 0x174f2b4, 12 0x174fb80, 13 0x1750450, 14 0x1750d20, 15 0x17515ec.
- Factory 0x275a68: `ldrb r0,[r8,#0x4d4]` (weapon class 0..15), 16-case jump table, `new` + ctor per class
  (00: size 13120, new 0x2b33b4, ctor 0x2b33f0). **Class 5 is an unused slot**: the natural home for Magnet Spike.
- About 400 `ldrb [..,#0x4d4]` sites read the class (rough count): every one needs a decision for class 5.

## Files per class (CB: arc/player/quest/w14*.arc)
| file | type | CB content |
|---|---|---|
| `w14.arc` player\param\pl_w14 | 0x496f8f22, magic `FUP`, v2 | weapon parameters (132 B) |
| player\hit\pl_we14_hitdata | 0x4e2ef008, magic `HDP` | 80 hit entries (4496 B): the attacks' damage data (S) |
| player\hit\pl_we14_hitsize | 0x5653c1b0, magic `HTS` | 12 hit shapes |
| player\pma\w14\w14_000..002 | 0x18a9225c | small tables, {f32 6.0, count, count x (u32, f32 frame, u32 id)} (meaning S: per-motion attach / timing) |
| player\mot\w14\w14 | 0x76820d81, LMT v67 | 256 motion slots (the moveset) |
| player\mot\w14\w14_sa | LMT v67 | 152 slots (Hunter Arts) |
| sound\pts\pl\w14_000 / _800, sound\call\pl\pl_wp14 | | sounds |
| effect\pl\w14\*, effect\base\* | | effects |
| `w14_m.arc` player\cmd\w14\sa\plcmd_w14_saNNNN_lvMM | 0x5139901d (XFS) | Hunter Art commands, 3 levels each |
| player\cam\w14\* | 0x4c0db839 / 0x30991f46 | cameras |
| `w14_m0..m5.arc` player\cmd\{com,w14}\plcmd_* | 0x5139901d (XFS) | the per-style command set (m0..m5 = the six styles, S) |

Command file (`tools/xfs.py` parses it): one XFS object {mQuality, act_st, act_no, act_param, cmd_type,
cmd_param0..3}; the file name repeats act_st and act_no (`plcmd_w14_0x0010_027a` = act_st 0x10, act_no 27).
act_st 0x0001 = common actions (`plcmd_com_*`), 0x0010 = weapon actions, high bit 0x8000 seen with both (S: a flag).
cmd_type / cmd_param = the input and its condition (meaning still to read from the code).

## How a class runs an action (Charge Blade, GU 1.4 main; dump/gu/decomp/cb.c = the class's 76 functions)
- The class's own code is one block (CB 0x11d3efc..0x11e0660). Of its ~556 vtable slots, 218 are the same in every
  class and 67 are CB-only. **Slot 201** (CB 0x11d5c50, 28.9 KB) is the action function: a switch on the action
  number u16 player +0x250a (281 CB cases); unknown numbers go to the base handler (vtable +0x2f4, `FUN_00282f7c`).
- Steps: byte player +5 (bits 8..15 of word +4). Step 0 of an action: step++, `FUN_00282fd8(p, flags, a, b)`
  (action flags at +0x2510 / +0x2514, vtable +0x300), vtable +0x84c, then start a motion with `FUN_002a8d10(p, desc)`.
  Later steps poll `FUN_00950bcc(p + 0x4b0)` (motion ended = state byte bit 2) and frames: `FUN_00280e4c(frame, p)`
  (frame reached), `FUN_00280c1c(frame, p)` (frame window); current frame float at +0x4f4.
- **Motion descriptor** (24 B, PC-relative tables in the class code): u32 motion (0xffff = none, e.g. 0x13f1), u32
  blend (+ flag bits 30 / 31 = other start modes), u32 start frame, u32 counter step (+0xfec), u32 -> {u16 command
  table id, i16 frame offset} for `FUN_002e9b7c`, u32 -> {u16 hit-data index, u32 type} for `FUN_002b7240` = arm
  attack slot 0 (attack slots at +0x3020, 0xb8 B each, vtable +0x7c8). Which frames the attack is live on is not in
  the descriptor (S: LMT v67 event bits, as with monsters).
- Change action: `FUN_002b6e94` -> vtable +0x68c (category, action, ...). Flag helpers `FUN_00283238` /
  `FUN_0028321c` set / clear +0x2510 / +0x2514. `FUN_002ad23c` counts up +0x3268 (to 30).
  - vtable +0x68c = 0x2b6f68 (every class): ends a weapon action into the common neutral actions. Kind 1 ->
    set action (1, 0x18), else (1, 0) (S: sheathed / drawn neutral), through 0x2831e0(p, act_st, act_no, x). The base
    handler for unknown action numbers (+0x2f4 = 0x2b6e5c) calls it with kind 0. 0x283060(p, st, no) = "is the
    current action (st, no)" (act_st u16 +0x2506, act_no u16 +0x250a).
  - **Drawn idle, walk, turn, draw and sheathe are common actions** (act_st 1) that ask class slots for their command
    tables (and S: motions). GS's slots 392 / 398 / 404-408 / 412-416 (12-70 B each) only pick table ids, e.g. slot
    392 (+0x620) = 0x2e9b7c(p, 2000, x) = the class list's table 0, which holds the drawn-idle commands.

## Command system (C, 2026-10-29; Phase 2 research f)
GU's cancels are data, as in MHF. Per style, each class ships a command table list and the commands it names:
- `player\cmd\wNN\plcmd_wNN_<style>` (type 0x4b4c2bd3, XFS cPlCmdTblList {mQuality, TblList -> array of cPlCmdTbl
  {Command -> array of cPlCmd {Active u8 +4, CmdBase = resource ref to an rPlBaseCmd file +8, PreFrame +0xc,
  StartFrame +0x10, EndFrame +0x14 (floats)}}}). GS Guild: 47 tables (`cls5/cmdtbl.py` parses them). Common
  list: player\cmd\com\plcmd_com_<style> in com_mN.arc.
- `plcmd_{com,wNN}_0xSSSS_NNNx` (type 0x5139901d, rPlBaseCmd; fields +0x60 mQuality, +0x64 u16 act_st, +0x66 u16
  act_no, +0x68 u16 act_param, +0x6a u16 cmd_type, +0x6c..+0x78 u32 cmd_param0..3; getter 0x2731b4). The arc of a
  class's style (wNN_mK.arc) carries the table list and every command it names, common ones included.
- Table ids: **2000 + k = table k of the class list, 1000 + k = table k of the common list**, 0 / 9999 = none.
  `0x2e9b7c(p, id, frame)` sets the table (player +0x24a8, id +0x24ac) and clears the per-command "buffered" flags
  (+0x24b0, 0x30 B); `0x2e9c50(p, id, frame, keep)` with keep = 1 keeps them (CB uses it between steps). A motion
  descriptor names its table, so each attack names its own cancel table.
- Each frame the command step 0x2e9d54 (from the player update 0x29b8e8) walks the current table: per command
  (0x26d42c = command + frames as i16), PreFrame < 999 = buffering allowed from that frame (999 = press inside the
  window only), StartFrame / EndFrame = transition window (>= 999 = the motion's end, EndFrame 0 = S: no end); the
  input test 0x2ecefc; then a switch on cmd_param3 & 0xfff (0 = plain) and set action (act_st, act_no). cmd_type
  bit 0x8000 = S: an automatic / conditional command, 0x4000 = another flag.
- Input tests (0x2ecefc, by cmd_type & 0xfff): 6 = common input id param0 pressed (bit of player +0x1414, test
  0x285e2c), 8 = class input id param0 (bit of +0x1424, test 0x285e78), 7 / 0xc = stick tilted + 6 / 8, 9 = 8 + stick
  direction param2 (0x27f728: 0x10000.. = forward / back / left / right sectors), 0x12 = 8 + stick neutral, 4 / 5 =
  stick tilted / pushed far, 0x13 / 0x14 / 0x16 / 0x17 = class slots +0x630 / +0x234 / +0x62c.
- Input layer (local player, every frame): 0x27c97c -> slot 138 (+0x228) = 0x2a79cc copies the pad (global +0x6b9c
  held, +0x6ba0, +0x6ba4) into the player: **+0x13f4 held, +0x13f8 pressed this frame (+0x13fa previous)**, +0x140e
  stick angle, +0x1412 stick magnitude (classes 0x27e608: > 0x31 / 0x59 / 0x6d). The common ids (+0x1414) come from
  0x27ca28 / 0x27db78; **slot 139 (+0x22c) is the class's own translator** (GS 0x1160058, CB 0x11d42b0) that sets
  the class ids (+0x1424, setter 0x285e54) from the virtual buttons and the press combos at +0x1444 (built by
  0x27ca28 with a short simultaneity window: bit 2 = X alone, 4 = A alone, 0x40 = X + A).
  - Virtual pad bits (S, strong; from GS / common use): 0x20 = X (GS overhead / charge on hold), 0x100 = A, 0x10 = B
    (common evade: ids 0xd / 0xe -> common actions 2 / 3), 0x80 = Y (sheathe / item), 0x1000 = R (guard; an option
    aliases 0x2000 or 0x4000 to it). **ZR and Minus not identified yet** (first test logs the raw word).
  - GS ids: X alone -> 0x12 / 0xc / 0x1d, A alone -> 2 / 9 / 0x1a / 0x1d, X + A -> 1 / 8, held X -> 5 / 0x11 (+ 3 /
    0x10 after a fresh press), held A -> 0x16 (+ 0x1e), R -> 0x17.
- Inputs: the per-style `plcmd` files bind an action (act_st 0x1 common / 0x10 weapon, act_no) to an input id, and
  the command tables give the frame windows (section "Command system" below).
- **Hit data** `pl_weNN_hitdata` (HDP: u32 version 0x20160209, u32 count, then 56-B entries = 28 i16).
  - Entry 0 is a dummy.
  - i16[4] = motion value (GS 48 / 65 / 80 / 100 for draw and charge levels; CB 15..42), repeated at i16[26].
  - i16[6] = flags (1 = cut, 3, 0x2001 ...).
  - Floats 1.0 at +44 / +48.
  - i16[2] / [3] are still unknown: GS 34 / 10, Hammer 22..52 / 6..10 (S: KO and exhaust).
  - i16[19..21] are packed bytes.

  Arming (0x2b7240 -> 0x2b72d4): attack slot = player + 0x3020 + slot * 0xb8, entry by index (0x2a8a50), plus the
  HTS resource (0x2a8a70). i16[0] is the frame the attack goes live, counted from the motion (the motion's current
  frame +0x4f4 subtracted). So GS charge levels go live at 96 / 200 / 240, and arming late shortens the window.
  The byte at +0x20 is passed as the hit-shape set (0 in the entries read).
- **Hit shapes** `pl_weNN_hitsize`: 'HTS', u32 version, u32 count (CB 12, GS 7), then count x {u32 shape count,
  u32 offset}; shapes are 0x30 B (layout to read: joint, radius, ends).
- For Magnet Spike, the interpreter can arm at MHF's ATTACK event frame with start 0, or arm at the step start with
  start = frame / 2. The HDP and HTS come from mhfsdt (MV, type, KO, shape sets on weapon bones 5 / 7). Still to
  find: the active duration, and whether GU shapes can name weapon-model joints.

## Class 5 in GU (Phase 2 research, 2026-10-29; C unless marked)
- Box equipment type = class + 7, so class 5 = type 12. The type -> class switch at 0x3c1830 (`sub r0,r0,#7`,
  `cmp r0,#14`, store at 0x3c1924) skips the store for type 12. The class byte sits at +0x4d4 of the hunter's
  equipment info; the player object points to that struct at +0x13c4.
- Factory 0x275a68, kind 0 (quest): one object per class. Sizes: GS 0x3340, SnS 0x3340, Hammer 0x3330, Lance 0x3340,
  HBG 0x3350, LBG 0x3360, LS 0x3350, SA 0x3360, GL 0x3380, Bow 0x3340, DB 0x3380, HH 0x3350, IG 0x3360, CB 0x3360,
  Prowler 0x3400. Class 5 returns 0 (no player). Kind 1 (lobby) builds one generic class (0x28bc94, 0x2740 B) for
  every weapon except the Prowler; kind 5 another (0x2750 B). Every kind continues at 0x275bc8 (r7 = the kind,
  stored at +0x13c8 at 0x275bf0; r8 = the equipment info, r10 = the object): a hook there must test the kind, since
  quest-class code reads fields past a generic object's end (test 1: slot 80 0x29ccdc checks +0x32a4..+0x3300).
  GU has no per-class lobby arcs (arc/player/lobby holds com.arc and make.arc only).
- A class constructor: base ctor 0x2990bc(this, 0) (fills 0x3328 B), the class vtable, its own fields from +0x3328,
  then 0x2b290c(this, X) (X stored at +0x3320). After the constructor the factory calls 0x26fd90, 0x288248 (the 7
  sub-objects; the weapon objects, 0x1420 B at +0x2388 / +0x238c, built when 0x277830(class, part) != 0x19),
  0x27acd8 and 0x276478 (equipment setup).
- Resource setup 0x29a498 is called from each class's own slot function. It loads motion banks by file ID through
  0x957400(this, res, bank): the common banks from 0x3de, bank 5 = class + 0x3ef (player\mot\wNN\wNN), bank 7 =
  class + 0x407 (wNN_sa). It also loads params 1 and class + 2 (player\param\pl_wNN), and cameras class + 0x863 /
  0x87b. GU's file-ID table (0x15a0ce0, {path hash, type}) already holds the class-5 names: the hashes match
  player\mot\w05\w05, w05_sa, player\param\pl_w05, player\hit\pl_we05_hitdata / _hitsize. Our arcs only have to
  carry those files.
- Weapon setup 0x288d10 (per weapon part, from the factory's sub-objects): file IDs from one-time .bss tables,
  each "+ number" unless the entry is the "no file" value (0, read-only 0x15a0cd8):
  - model: 0x286ac0 table[class * 2 + part] + model number (the ID before each class's first model: GS 20414, SnS
    20614, ..., HBG 21614, LBG 22814);
  - weapon motions: 0x286c2c (wgNN_00, + the pwl mGmkMotNo) and 0x286e28 (wgNN_sa_00);
  - pwl: 0x287024 table[class] + the display type -> weapon\wNN\pwl\pl_wNN_gMM (16 per class, player\com\com.arc),
    attached to the weapon by 0x3072f8.

  All four leave class 5 at "no file" while GU's file table still names MH3's class-5 files at the gaps (mbg001 =
  21815, wg05_00 = 0x4b0, wg05_sa_00 = 0x653; no pl_w05 files): build.py ms_patches fills them (pwl: GS's range).
  A pl_wNN_gMM file holds per-body-slot records {slot, 4 words, -1 = default} (168 B for GS's 8 slots).
- Weapon sync 0x308b3c (per frame): a bank-5 body motion in slot S plays slot S of weapon list 0 (wgNN_00, layer 0)
  and of list 1 (wgNN_sa_00, layer 1) when the list has it (bank 7: lists 2 / 3), synced to the body; with none,
  index 1 (drawn). Any other motion: index 0 when sheathed, 1 when drawn (SA / CB: their mode's 0x14). The weapon's
  current motion is weapon +0x4b4 (layer 0) / +0x5f4 (layer 1), list << 8 | slot.
- Command lists (0x29b514, after every equipment load): common list = file 21 + style (player\cmd\com\plcmd_com_
  <style>, com_mN.arc), class list = file 27 + class * 6 + style (player\cmd\wNN\plcmd_wNN_<style>, wNN_mN.arc),
  stored at player +0x24ec / +0x24f0; GU's style names: guild, old, airhike, bushi, kizuna, tatsujin (style =
  vt+0x168). Set-table 0x2e9b7c: id < 2000 indexes the common list (id - 1000), else the class list (id - 2000); the
  table goes to +0x24a8, its id to +0x24ac. A missing list leaves every table of it empty.
  A list resolves its CmdBase references (to rPlBaseCmd files) while it loads: GU's style arcs hold the command
  files first and the list last. A reference to a command not loaded yet stays null, and the command step's reader
  0x26d42c skips it (no error). Style indexes: 4 = kizuna (Alchemy), 5 = tatsujin (Valor).
- Inputs: GU's R (the weapon button) is 0x65f93c(): 0x40, or 0x800 with the other R option (byte +0x446e of a
  settings object); GS's translator tests it against the held buttons.
- Path formats (0x1556f9e..), all taking class 5 as w05:
  - player: player\quest\w%02d, w%02d_m, w%02d_m%d, player\lobby\w%02d;
  - shells: shell\pl\w%02d;
  - weapon: weapon\w%02d\%03d (model), weapon\w%02d\g%02d (weapon motions), weapon\w%02d\snd\%03d,
    weapon\w%02d\snd\mat%s.

  Arcs are requested by kind through 0x27b34c(this, slot, kind, class, x) -> 0x1529a8.
- **Class 5 is a leftover bowgun slot** (S: MH3's Medium Bowgun, between HBG 4 and LBG 6). GU still tests "gunner" as
  `class - 4 < 3`, so class 5 takes the gunner path there. Sites:
  - the gunner helper 0x27c7ec, which has many callers;
  - 0x144880, 0x1449b4, 0x144ad8;
  - resource setup 0x29a498 (gunner stance 0x2f / 2);
  - the functions 0x6ece8c, 0x6fcabc, 0x70361c and the sites 0x6ed880, 0x70b734 (S: UI code);
  - switches that send class 5 to the bowgun cases: 0x18015c (= 4 / 6 / 10) and 0x665ad8 (= 4 / 6);
  - 0x2e5810, a switch(class - 4) where class 5 has its own case (to read).

  Ranges over classes 4..10 still to read: 0x1722c0, 0x28ab24, 0x58a16c, 0x58ef9c.

  Elsewhere class 5 gets the default case of the 26 class switches and sits outside every class bit set (for
  example melee = {0-3, 7-9, 11-14}). So until patched it counts as neither melee nor gunner.
- Audit of the 400 class-byte reads (scratch script, decompiled functions):
  - 256 compare with one class (class 5 = "another class": fine unless the else branch matters);
  - 25 class bit sets;
  - 26 switches;
  - 28 tables indexed by class (class 5's entry still to check);
  - about 60 to read by hand.
- **GU has weapon motions** (correction of Phase 1): arc/weapon/wNN/gMM.arc = weapon\wNN\mot\wgNN_MM, plus wgNN_sa_MM
  for Hunter Arts and L / R pairs for two-part weapons. Every class has them, and each model's pwl mGmkMotNo picks the
  set (notes/gear-weapons.md in the repo root). The weapon objects at +0x2388 / +0x238c play them.
- Weapon motion sync: 0x308b3c runs every frame from the weapon object's update 0x3077f0.
  - Player motion id = bank * 1000 + index. For a bank-5 motion (the class list), the weapon plays motion `index` on
    layer 0 and `0x100 | index` on layer 1, provided its list has them (0x953b10 tests, 0x954640 plays).
  - Otherwise it falls back to motion 1 / 0x101 (SA and CB choose by their mode).
  - So wg05_00 must use the body list's indexes: the same pairing as MHF's w13w (part P slot S = body motion P S).
- Weapon attach (C, test 1 runs 5-6): 0x3078b8 (weapon, hunter, type) runs each frame from the weapon update 0x3077f0
  (hunter = weapon +0x30), before the motion sync. The type is weapon +0x13d0 (ctor default 25), the weapon's part
  type, not the class: class 5's part type is patched to the Great Sword's 0, so GU attaches it as a Great Sword
  (the class byte is hunter +0x13c4 -> +0x4d4).
  - State: 0x308834 -> 0x288738 = the first active body-motion event (0x2824a8: u16 ids at hunter +0x14ec, mask
    +0x14dc): event 0x17 -> state 0xb, 0x14 -> 10, 0x13 -> 9, 7 -> 8, 6 -> 7, 5 -> 6, 4 -> 5, 1 -> 0, 2 -> 2, 3 -> 1,
    0x10 / 0x11, 0x16 -> 0x12, 0x1d -> 0x13, 0x1e -> 3, none -> 0x14. A hunter kind other than 0 (quest) always
    gets 2. GS's events: drawn idle / walk 3, draw (slot 2) 2 to frame 14 then 1, sheathe (slot 3) 1 then 2 from 36.
    Types 2, 5 and 13 skip it: state 4.
  - Joint (0x3084c4 -> weapon +0x13cc): states 1 / 3 / 5 / 7 / 9 / 0xb / 0xe -> 8 (+x hand), 0 / 6 / 8 / 10 / 0x13
    -> 12 (-x hand), 4 -> 11, 0x14 -> 2, 2 -> the class's pwl table [display type +0x13f8] (+0x20 of a 0x30-B
    record). Scale +0x60..+0x68: 1.0 on the fixed joints; else by class byte (1 / 11: 1.0, 3 / 6 / 8: 0.9, 14: 0.8 /
    0.7, others 0.8, so a sheathed GS is 0.8).
  - Record (0x308334 per type and state): {f32 position[3], pad, f32 rotation[3] degrees}, applied when the
    pointer changes (+0x1408): position -> +0x40, rotation x pi/180 -> 0x8a7dc4 (quaternion +0x50). The Great
    Sword's (.bss, filled by its static init 0x30afa4): state 0 (-11, -2, 10) no turn; 1 (10, 0, 58) 180 deg about
    z; 3 (10, -2, 8) 180 deg about z; 0x12 (-47, 51, -24) (89, -4, 41) deg; 0x13 = state 0's.
  - Then the weapon's vtable +0x48 (weapon, hunter, joint) attaches it; the previous joint goes to +0x13c8, the state
    to +0x13d4 (the motion sync reads it: state 2 / 0x12 = the sheathed pose for non-bank-5 motions).
  - Class 5 (ms_class.c ms_attach, on the hunter's class byte): joint 8 with no offset (msbuild bakes the bone-18
    frames into the root track), otherwise GU's Great Sword path. Checked offline (scratch FK on GU's armor MOD
    binds, LMT quaternions as stored): our drawn idle puts joint 8 at bone 14's place and orientation (1 cm, identity),
    and GS's own idle keeps its other hand along joint 8's +z as MHF's does.
- Second-mode motions: GU's common actions pick them only for SA / CB by class byte (drawn idle 0x2de664: class 8 ->
  slot 215 ? 5020 : 5001; walk 0x2e5c60: 5024 / 5004). Class 5 remaps them in the unit setter 0x53a164 (ms_setmotion).
- Motion frame fields of a unit (C): +0x4f0 blend length, +0x4f4 blend countdown (0x53a0d8 = "blending"),
  +0x4fc frame, +0x504 end, +0x508 loop start, +0x50c speed. Each tick 0x27b9c8 copies +0x4fc to +0x14d0 and
  stores this tick's advance (speed x +0x1c) at +0x14d4; 0x280e4c(p, frame) = "reached" on their sum (wrapped on a
  loop, false while blending), 0x280c1c the window check.
- Button role masks 0x65f808..0x65facc: each returns one virtual bit for a role, and the control option +0x446e
  swaps roles between 0x40 / 0x100 / 0x200 / 0x400 / 0x800 (R = 0x65f93c: 0x40, or 0x800); +0x446d swaps 1 / 8,
  +0x446f 0x100000.. / 1.. (S: D-pad).

## Equipment side: box type 12 (Phase 2 research, 2026-10-29; C unless marked)
Nothing rejects type 12; it only has no data. Spot-checked on mem.bin: the type -> class table, the gunner table,
the two patch words, the pl_w05 hash and the 0x13c208 jump table.
- **Equip sets class 5 by itself.**
  - 0x26e964 (equip) stores class = table 0x159fdcc[type] (u32 entries; [12] = 5) at +0x4d4 (0x26ea74..0x26ea7c).
  - 0x26e600 copies it with the hunter info.
  - The player save keeps it raw.
  - 0x2875c0 builds weapon\w05\<model> from it.
- **sEquip** (global 0x1856b18) holds per-type resources:
  - BaseData +0x50.., LevelData +0x88.., MsgData +0xc0..: 14 words each, types 7-11 and 13-21, no slot for 12;
  - kireaji +0xfc;
  - pwl +0x184 + 4 * class.

  Loader 0x13cc80 uses fixed file IDs (base 0xdde4.., level 0xddf2..), with none for class 5. The pwl IDs 0xde20..
  include 0xde25 = weapon\w05\pwl\pl_w05 (hash 0x821bd974), a file GU does not ship.
- **Getters return 0 for type 12:**
  - base 0x13c208(sEquip, type, id): jump table entry 0x13c264 -> 0x13c32c, about 50 callers;
  - level 0x13ed08;
  - msg index 0x13f14c;
  - "names loaded" 0x13f830 (mask 0xfff7df, bit 11 clear).

  The 4 name slots of the base vtable then fall back to NULL.
  - The pwl getters 0x13f554 / 0x13f594 / 0x13f5d4 / 0x13f614 index by class, and class 5 gives 0.
  - Sharpness is the same for every class (melee level-vtable slots read kireaji through 0x13f290).
- **Without a base record, equipping recurses forever.** 0x26ec84 refuses the entry (no record) and 0x26e964 falls
  back to a dummy of the same type with ID 0, which is refused the same way. Record ID 0 must therefore exist.
- **Records:**
  - base = GS layout: 40 B in memory, GS vtable 0x173791c with 90 slots; ctor 0xf5630, parser 0xf6268 (33-B file
    record), u16 +0x26 = first level row. Its slot +0x18 (getType, constant array 0x15a0028) never returns 12, so
    class 5 needs its own vtable copy with getType = 12.
  - level = GS rows: ctor 0xf6f80, parser 0xf74c8, vtable 0x1737c24, type-free.
  - names: either own vtable slots +0x3c/+0x40/+0xbc/+0xc0 reading the GS weapon GMD (global 0x1856b20,
    0xb84114(gmd, 6 * mIndex + k), strings appended by the TXTA path), or hooks on 0x13f830 / 0x13f14c.
- **Minimal set:**
  - entry hooks on 0x13c208 and 0x13ed08 (type 12 -> our tables);
  - names;
  - pwl for class 5: hooks on the 4 pwl getters, or a resident pl_w05 (S: load timing);
  - word patch 0x1628064 `2` -> `1`: the type-7 indexed gunner table, read only by 0x26ee8c, which strips
    blademaster-only armor;
  - word patch 0x145b94 `movw r2,#0x7fdf` -> `#0x7fff`: blademaster / gunner for the item box, 0x15a06b0[5] = 0.
- **Cosmetic or later:**
  - the equipment icon (0x162e7e8 and smithy 0x1650018, low byte = type 12, now 63 = the LBG icon);
  - per-type stat 0x159fe34[12] = 0 (S: a skill-raised stat);
  - sQuest 0x526f70 counts type 12 as LBG;
  - the smithy, armory, Hunter's Notes, arena and quest-result lists leave 12 out.
- **Risks:**
  - Saves are not validated, so type-12 entries and class 5 persist. Without the mod, equipping one recurses (S:
    stack overflow) and a saved class 5 reaches the player factory (S: crash). Test on a backed-up save.
  - Multiplayer peers copy the class byte raw (S: everyone needs the mod).
  - Equipping in the house may request player\lobby\w05 (S).

## Decisions (user, 2026-10-29, end of Phase 1)
- Styles: **Guild only for now** (MHF's Magnet Spike has one moveset); other styles are not excluded for later.
- Hunter Arts: **the 10 shared arts only** (`plcmd_com_sa0000..0009` in com_m.arc); no Magnet Spike arts.

## Porting consequence (Phase 2 design input)
MHF drives Magnet Spike from data (step scripts, cancel windows, frame events, mhfsdt attacks); GU classes hard-code
the same things in a per-action switch. The faithful and smallest route is a new class (slot 5) whose action function
is a small interpreter of the MHF action records (converted 1:1: steps -> motion descriptors, cancels -> plcmd + frame
windows, events -> attack / effect / state calls), with MHF's motion values in a generated HDP.
The weapon model needs its placement too. Its bones are animated by a GU weapon motion list (weapon\w05\mot\wg05_00,
converted from the MHF weapon motions). Its root sits on the holding hand, GU bone 8 or 12 (MHF 14 / 18), switched
per frame from `tools/msgrip.py`'s table (assets.md, "Weapon grip"). Done in Phase 2: msmot bakes the bone-18 frames
into the root track (in bone 14's frame), and the class attaches the weapon to joint 8 ("Weapon attach" above).
