# Magnet Spike: behaviour reference (MHF-Z)

The port target. Sources, best first:
1. MHF-Z code: `mhfo-hd.dll` of the final ZZ client (build 2019-09-02), analysed with Ghidra
   (`dump/mhf/ghidra`, gitignored). Code facts carry their address.
2. Fist's MHF guide, "ZZ Content > Magnet Spikes" and "Magnet Spike Moves & Motions"
   (https://fist-mirror.github.io/guide/futuresection.html, read 2026-10-29). Its move flowchart is Capcom's official
   manual chart, titled "Magnet Spike Moves (Extreme Style)".
3. Game data: `dat/motion/w13.mot` (body motions), `w13w.mot` (weapon motions), `mhfdat.bin` (weapon records).

Status (2026-10-29): moveset decoded from the game data (actions, inputs, cancel windows, frame events, attack values)
and matched to the guide's moves (C sections). C = confirmed in code or data, G = guide only. Decoded dump:
`python3 -I tools/msact.py dump/mhf/zz/mhfdat.dec.bin dump/mhf/zz/mhfsdt.dec.bin [ACTION...]`
(dump/mhf/ms_actions.txt).

## Basics (G)
- Two modes, **Cutting** (cut damage, fast attacks and evasions like Dual Swords) and **Impact** (impact damage, slow
  heavy single hits, quick swipes, a fast charge). Either mode can be drawn into or switched to from idle at any
  time; no gauge needed. Any horizontal of one mode can switch into a horizontal of the other (Transform Attack).
- No phial, no length. Attack multiplier (bloat) 5.4.
- **Aiming mode** (L2 in the flowchart, either mode): shoot a **Magnetic Marker** on a monster, then **attract** to it
  (red marker, proper distance) or **repel** from it (blue, too close); too far = white, no action. Attraction tracks
  the monster on a linear path and can be cancelled into an evade or a falling attack.
- **Magnetise**: each mode charges by use; when its icon turns red the weapon can be magnetised: all attacks x1.1
  (like a power phial) and extra hits on some attacks, for 80 s. Afterwards a short lockout with no charge gain.
  The two modes charge independently and can hold the red charge indefinitely.
- **Gauge** (bars): spent by evasions, attract / repel and starting the Magnetic Pin, one bar per action; refills
  over time and by hitting the monster.
- **Magnetic Pin**: builds up like a status. When ready the monster shows a moving magnetism aura. Started from
  Magnetic Double Slash (Cutting) or Magnetic Double Swipe (Impact): leap, slam the weapon down, pin the monster and
  start a QTE (mash the shown direction / buttons). A good QTE turns the monster icon red and allows the **Pin
  Finisher** (MV 600) on the marker's spot; it knocks the monster over and extends the pin. On a tail it deals cut
  damage but only down to 1 HP, so any following cutting hit severs it.

## Moves and motion values (G, guide's table; Impact values in brackets = KO)
※ = has invulnerability frames.

| Cutting mode | MV | Impact mode | MV (KO) |
|---|---|---|---|
| Unsheathe Vertical | 61 | Horizontal 1 | 44 (30) |
| Vertical 1 | 43 | Horizontal 2 | 53 (30) |
| Upslash | 35 | Overhead Horizontal | 100 (45) |
| Vertical 2 | 46 | Down Swipe | 46 (25) |
| Horizontal 1 | 56 | Triple Strike 1 | 51 (10) |
| Horizontal 2 | 46 | Triple Strike 2 | 58 (20) |
| Horizontal 3 | 64 | Triple Strike 3 | 130 (50) |
| Finishing Slash | 120 | Charged Strike | 338 (190) |
| Finishing Slash (Magnetised) | 120, 10x3 | Charged Strike (C.UP+1) | 363 (190) |
| Guard Counter | 30 | Charged Strike (C.UP+2) | 373 (190) |
| Guard Counter (Success) | 30, 80 | Supplex | 96, 121 (50, 65) |
| Magnetic Double Slash ※ | 44, 54 | Guard Assault ※ | 73, 90 (35, 45) |
| Magnetic Evade into Upslash | 55 | Magnetic Double Swipe ※ | 42, 52 (30, 35) |
| Retreat Slash ※ | 20, 20 | Magnetic Shock (Whiff) | 75 (30) |
| Magnetic Assault (Leap) ※ | 80 | Magnetic Shock (Iframed) | 125, 5x3 (60, 5x3) |
| Falling Downslash ※ | 200 | Magnetic Assault (Leap) ※ | 40, 50 (35, 35) |
| Magnetic Pin | 1 | Falling Swings ※ | 25, 80, 120 (20, 35, 75) |
| Magnetic Pin Finisher | 600 | Magnetic Pin | 1 |
| | | Magnetic Pin Finisher | 600 |

## Move flow (G, Capcom's chart; PlayStation-style MHF buttons; "17if" = 17 invulnerable frames)
Cutting mode
- Vertical 1 (triangle) -> Upslash -> Vertical 2; Horizontal 1 (circle) -> Horizontal 2 -> Horizontal 3; the two
  chains cross between Vertical 1 / Upslash and Horizontal 1 / Horizontal 2. Vertical 2, Horizontal 3 and Guard
  Counter lead into Finishing Slash.
- Guard Counter (R1; guard frames over the whole animation).
- Magnetic Evasion (R1 + square, 17if), Retreat Slash (cross, 17if), Magnetic Assault (R1 + circle, 17if), Magnetic
  Double Slash (triangle, 17if) -> Magnetic Pin (R1 + circle + triangle).
- Magnetic Field (L2 aiming): Magnetic Marker (L2 + circle), Magnetic Attraction (17if) -> Falling Slash (triangle
  while falling) or Approach Cancel (cross while falling); Magnetic Repulsion (L2 + cross, 24if).
- Magnetise (R1 + SELECT). Switch (SELECT, from idle); Transform Attack (SELECT, from a horizontal, into the other
  mode's matching horizontal: H1 <-> H1, H2 <-> H2, H3 <-> Overhead Horizontal).

Impact mode
- Horizontal 1 (circle / stick+circle) -> Horizontal 2 -> Overhead Horizontal (triangle, stick+) -> Supplex;
  Downswipe; Triple Strike 1 -> 2 -> 3 (circle); Charged Strike (timed release).
- Just Guard (R2, 19if from guard) -> Guard Assault (triangle, 17if).
- Magnetic Double Swipe (17if), Magnetic Assault (R1 + circle or triangle, 17if), Magnetic Evasion, Magnetic Force
  (17if) -> Supplex.
- Magnetic Pin -> Pin Finisher (R2); Unsheathed Running (double-tap a direction); Recovery (cross).
- Magnetic Field as in Cutting mode, with Falling Swipe instead of Falling Slash.

The chart misses some combos (guide): Magnetic Assault (Leap) in Cutting mode -> Upslash -> Vertical 2 gives an
early Finishing Slash.

## How MHF runs Magnet Spike (C, mhfo-hd.dll + mhfdat.bin; addresses = the 2019-09-02 ZZ dll)
Player struct (0x1050 B, array at 0x1dc6c000): +3 weapon type (13 = MS; 1 / 5 bowguns, 11 Tonfa, 12 Switch
Axe F), +5 action step, +0xc player index, +0x14 action number, +0x15 action group, +0x16 / +0x17 previous action /
group, +0x31c / +0x31e motion start frame (lower / upper body), +0x324 / +0x326 blend, +0x32c / +0x32e motion ID
(upper = lower + 100), +0x62f motion bank slot. Per-player extension 0x9d0 B at 0x1e2a32f0 + index * 0x9d0; MS
part at +0x1c0 (0x1e2a34b0), current mode byte at MS +0x64 (0 = Cutting, 1 = Impact).
- Motion ID = bank * 1000 + part * 100 + slot (bank 0 = shared plcom, 1 = the weapon bank; part = the even AAN part,
  its upper-body twin is part + 1): decoder 0x108fdc80, set-motion 0x10a92cd0 (id in ax, both layers).
- Action dispatch 0x10a5b440, by group: 0 0x109fdb40, 1 = weapon actions 0x109ff060 (actions 0xf0..0xf4 shared,
  else the weapon executor), 2 0x10a46e80, 3 0x10a50af0, 4 0x10a55080, 5 0x10a596d0, 6 0x10a5a810, 7 0x10a48090;
  then per weapon (MS: 0x1032d730).
- Weapon descriptor table 0x118806b8 + type * 40, 10 callbacks, the executor last (0x118806dc + type * 40). MS:
  0x1032d0a0, 0x1032d110, 0x1032d210, stub, 0x1032d2d0, stubs, executor **0x1032fa80**. The executor runs the shared
  engine with MS callbacks: 0x10a67790 (with 0x10337c50), 0x1032b820 + 0x103339d0 (per-action extras, e.g. charge
  levels and their sounds), 0x10a68510 (frame events -> 0x103396d0 -> 45 handlers at table 0x11926b40),
  0x10a68110 (commands: 0x10336830 = 14 MS queries at 0x11926c5c, 0x10337530, 0x10337c50; 25 input checks at
  0x11926bf8), 0x10331350, then 0x1032c480 (mode = the current action's mode).
- MS support code: 0x1032ae00..0x1033e000 (268 functions; mode test 0x1032c4e0 has 42 callers across the game).
- An NPC hunter with a Magnet Spike (NPC kind 0x2b, update 0x10ac5ba0 -> 0x10ad2830) has its own simpler copy of
  the moves at 0x10ad0000..0x10ae2000, with literal motion IDs: not the player's code.

**The moveset is data** (`tools/msact.py` has every layout): mhfdat header u32 0x614 -> per weapon type {count,
records}; MS = 165 actions (0..164), each {steps, cancels, events}:
- **steps** (12 B; engine 0x10a67790): play a motion once / until a frame / hold, or jump to another action. Motion =
  bank * 1000 + part * 100 + slot (bank 1 = w13.mot). 131 distinct MS motions are used.
- **cancels** (40 B; engine 0x10a68110): priority, condition, input, an input-buffer window, the next action and a
  transition window. A pressed input is kept while its buffer window is open; the action changes inside the
  transition window; a higher priority overrides a kept lower one. Next actions >= 165 (202, 203, 207, 208) are shared
  actions (roll, charge release...).
- **events** (12 B; engine 0x10a68510 -> MS handlers 0x11926b40): at step start / at a frame, event id + param. Event 3
  = **attack** (param = attack id in mhfsdt kind 0x78), 4 / 42-44 = special attacks (mhfsdt kind 0x79: 43 and 44
  fire #8 = the Pin Finisher), 11 / 45 = stamina / gauge costs, 13 = move speed, 14 / 39 = turn to stick / target,
  1 / 21 = guard and armor flags, 12 = camera shake, 22-38 = MS state (magnet charge per mode, flags).
- Time spec (cancel windows and events): step, kind (step start / never / frame), frame, loop count.

**Inputs** (25 checks at 0x11926bf8; MHF key config categories 13-14 "Magnet Spike 1/2", e.g. command 0xdf =
"Attack R-up | triangle"): 0 roll, 1 stick, 2 tri, 3 circle, 4 tri+circle, 5 transform (SELECT), 6 stick+circle,
7-11 R1 + tri / circle / tri+circle / special-A (cross) / SELECT, 13 guard counter (R2), 14 / 15 circle held /
released, 16 R1, 17 R1 + evade (cross), 19 / 23 / 24 while aiming (L2 held): circle / cross / tri, 20 always,
21 tri released, 22 stick+tri (12, 18 never). Every input also has a right-stick alternative ("R-up" = tri...).
Priority order 0x11a868d8. **Conditions** (14 at 0x11926c5c): always, gauge >= 1..5 bars (1 bar = param 19 = 2000),
attract / repel possible (marker distance), fall height, MS flags, mode.

**Mode lists and tuning**: mhfdat header u32 0xb90 -> MS block (0xdc1a20): Cutting actions (81), Impact (81), either
(39); (action, 1) pairs (28); 60 / 30 degree turn limits per action (65536 = 360 deg); flag lists; parameter table
(+0x14: u16 values; e.g. 19 = gauge bar 2000, 61 = Magnetise damage bonus %).

**Attack values: `dat/mhfsdt.bin`** (`tools/sdt.py`; loader 0x10afcd10, lookup by attack-object kind 0x10afcfd0).
Kind 0x78 = the 46 MS attacks (40 B: motion value, damage type cut 0x20a / impact 0x10a, KO in 8.8 fixed point, hit
shape set), kind 0x79 = 14 MS special attacks (marker shot, Pin Finisher 600, magnetised extra hits 10 and 5).
Hit shapes: 9 sets of capsules / spheres on the weapon's horseshoe bones 5 and 7 (Cutting) or around the body
(Impact), 8 variants per set chosen by the weapon model. Magnetise adds (100 + param 61)% to the motion value when
the attack spawns (0x1033c5d0).

## Moves in the data (C; action numbers, motion values from mhfsdt, inputs from the idle table 0x1032d2d0)
From drawn idle each input has a Cutting and an Impact action; chains are cancels (the dump has the frame windows).
Variants of a move (same attack, a different lead-in motion depending on the previous move) are listed together.

| Move | Cutting actions (MV) | Impact actions (MV / KO) |
|---|---|---|
| tri from idle | 0 Vertical 1 (43) | 18 Down Swipe (46/25) |
| tri+circle from idle | 2 Upslash (35) | 26 Supplex (96/50, 121/65) |
| circle from idle | 6 Horizontal 1 (56) | 32 Triple Strike 1 (51/10) |
| stick+circle | 6 Horizontal 1 | 23 Horizontal 1 (44/30) |
| chain | V1 -tri-> 3 Upslash -tri-> 4 Vertical 2 -tri+circle-> 152 Finishing Slash (120); H1 -circle-> 9 Horizontal 2 (46) -circle-> 10 Horizontal 3 (64) -tri+circle-> 155 Finishing Slash | H1 -circle-> 25 Horizontal 2 (53/30) -tri+circle-> 28 Overhead Horizontal (100/45) -tri+circle-> 30 Supplex; TS1 -circle-> 33 TS2 (58/20) -circle-> 34 charge (hold) -release (shared action 208, S)-> 36 TS3 (130/50) or 35 Charged Strike (338/190) |
| variants | V1: 1, 13, 15, 17, 78, 80, 127, 140; Upslash: 3, 16, 48, 81, 128, 141, 153; V2: 4, 5, 129; H1: 7, 8, 49, 83, 109, 122-125, 142; H3: 126; Finishing: 152, 154, 155 | Down Swipe: 20-22, 52, 85, 132, 133, 143, 150; H1: 24, 79, 86, 130, 131, 145, 149; H2: 27; Overhead: 29, 54; Supplex: 30, 31, 37, 43, 144; TS1: 87, 139, 147, 148, 151 |
| R1+tri | 11 / 135 Magnetic Double Slash (44, 54) | 39 / 146 Magnetic Double Swipe (42/30, 52/35) |
| R1+tri+circle | 12 / 51 / 136 Magnetic Assault (Leap) (80) | 38 / 53 / 138 Magnetic Assault (Leap) (40/35, 50/35) |
| R1+tri+circle after the double slash / swipe | 97 Magnetic Pin (1) | 94 Magnetic Pin (1) |
| pin sequence (code-driven) | 98-105: pin, QTE loops, 105 Pin Finisher (special 600 at frame 184) | 156, 157 (Pin Finisher) |
| R1+cross (special A) | 106 Retreat Slash (20, 20) | 158 (name open; spawns special #11) -> tri / circle 161 / 162 Magnetic Shock (75/30; 125/60 when it went through an attack) |
| R1+evade, R1+circle | 107 / 108 Magnetic Evasion -tri-> 110 / 111 Evade Upslash (55) | 116 / 117 Magnetic Evasion -> 95 / 96 Magnetic Shock (75/30) or 159 / 160 (125/60 + 5 x 3) |
| R2 | 14 Guard Counter (30); success variants 57, 76, 77 -tri+circle-> 154 Finishing Slash | 112 guard -> 113 -> 114 / 115 Guard Assault (73/35, 90/45) |
| aiming (L2) + circle | 82 Magnetic Marker (special #1 = the shot) | 84 Magnetic Marker |
| aiming + tri (red marker) | 58 Magnetic Attraction -tri-> 59 Falling Downslash (200); cross -> 63 approach cancel | 68 Magnetic Attraction -tri-> 73 Falling Swings (25/20, 80/35) + 74 (120/75); 69 cancel |
| aiming + cross (blue marker) | 66 Magnetic Repulsion | 67 Magnetic Repulsion |
| SELECT from idle | 90 switch to Impact | 91 switch to Cutting |
| SELECT from a horizontal (Transform Attack) | from H1 / H2 / H3: 120 / 121 / 89 = Impact H1 / H2 / Overhead | from H1 / H2 / Overhead: 118 / 119 / 88 = Cutting H1 / H2 / H3 |
| R1+SELECT | 163 Magnetise | 164 Magnetise |
| stick / unsheathed move | 40, 41 | 44, 45 |
| sheathed (0x1032d110 / 0x1032d210) | tri: shared draw action (group 0 action 4); moving tri: 78 (Vertical 1, 43) | tri+circle: 79 (Horizontal 1); R1+tri+circle: 112 (guard) |

Columns = the mode the input is pressed in (the number is the action it starts).
Every guide motion value (and Impact KO) is in mhfsdt, except the guide's Unsheathe Vertical 61: in the data the
draw attack is the shared draw then Vertical 1 (43). Unused or code-spawned attacks: #3 (38), #20 (50), #42-45.
The guide's Charged Strike C.UP values (363, 373) are not in the data (the skill adds them).

## Motion banks (C, from the files)
`w13.mot` (JPK -> AAN, `tools/aan.py`): 3 groups, each a pair of parts (part A: 9 bones, root + lower body with
translation; part B: 12 bones, upper body, rotation only = the 21-bone MHF player skeleton) sharing slot numbers.
Group 0: 79 motions (slots 1..83), group 1: 4 (slots 1, 2, 21, 23), group 2: 74 (slots 1..98); 157 in all.
Motion ID 1000 + part * 100 + slot (e.g. 1049 = group 0 slot 49). `w13w.mot` holds the 11-bone weapon's motions.
Value conventions, the skeleton map to MHGU and the Blender preview: notes/assets.md.
