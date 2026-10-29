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
  blend (+ flag bits 30 / 31 = other start modes), u32 start frame, u32 counter step (+0xfec), u32 -> {u16 timeline id
  (< 2000 / >= 2000 = two pma tables), i16} for `FUN_002e9b7c`, u32 -> {u16 hit-data index, u32 type} for
  `FUN_002b7240` = arm attack slot 0 (attack slots at +0x3020, 0xb8 B each, vtable +0x7c8). Which frames the attack
  is live on is not in the descriptor (S: LMT v67 event bits, as with monsters).
- Change action: `FUN_002b6e94` -> vtable +0x68c (category, action, ...). Flag helpers `FUN_00283238` /
  `FUN_0028321c` set / clear +0x2510 / +0x2514. `FUN_002ad23c` counts up +0x3268 (to 30).
- Inputs: the per-style `plcmd` files bind an action (act_st 0x1 common / 0x10 weapon, act_no) to an input
  (cmd_type 6 press, 7 hold, 0x8000 = flag; cmd_param0 = button id). The class code decides when a transition is
  allowed (frame checks above); the command object hangs at +0x263c (S).
- **Hit data** `pl_we14_hitdata` (HDP, u32 version 0x20160209, u32 count 80, then 56 B entries): i16 [2] = motion value
  (CB 14..42), repeated at [24]; [26] = 2 x MV (S: KO or exhaust).

## Decisions (user, 2026-10-29, end of Phase 1)
- Styles: **Guild only for now** (MHF's Magnet Spike has one moveset); other styles are not excluded for later.
- Hunter Arts: **the 10 shared arts only** (`plcmd_com_sa0000..0009` in com_m.arc); no Magnet Spike arts.

## Porting consequence (Phase 2 design input)
MHF drives Magnet Spike from data (step scripts, cancel windows, frame events, mhfsdt attacks); GU classes hard-code
the same things in a per-action switch. The faithful and smallest route is a new class (slot 5) whose action function
is a small interpreter of the MHF action records (converted 1:1: steps -> motion descriptors, cancels -> plcmd + frame
windows, events -> attack / effect / state calls), with MHF's motion values in a generated HDP.
