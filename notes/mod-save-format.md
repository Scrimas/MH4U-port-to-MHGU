# The mod's save files (core 3.0.0)

Everything the mod adds to a character lives in a file of its own, `mhgu_de_<slot>.bin` (slot 1..3), next to GU's
`system` and `system_backup` in the game's save. GU's files then hold vanilla data only, so removing the mod, an
older core or a save editor can never meet an added ID there. The reference is `tools/modsave.py`; the module
(module/modsave.c) and the installer (installer/core/src/modsave.rs) follow it byte for byte, and
`tools/test_modsave.py` compares all three.

C = confirmed in code or data, S = strong, G = guess. Offsets are relative to a character's base in GU's file
(MHGU_Editor docs/11-save-map.md: the character's bytes, 0x11F8C4 of them, start at 0x24 + u32 [0x34 + 4 x slot]).

## What is added

GU v1.4's own table counts decide, whatever packages are installed (a monster removed by hand leaves its things
behind, and they are added too):

| Kind | Added |
|---|---|
| Item | ID 2977 and up (2977..2990 the DUMMY materials, 2991.. appended), 2889..2899 (DUMMY decorations) |
| Armor (box entry types 1..5, layered looks) | ID 1287 and up (armorSeriesData) |
| Weapon (box types 7..21 = class 0..14) | ID at or past GU's count of the class: 137 129 132 127 109 0 110 127 110 115 108 126 112 83 81 |
| Quest | the renamed GU slots (allocations.toml `quest_slots`, at their quest_group index) and the appended block from index 1509 |
| Smithy and other bit maps | bits at or past GU's count (table below) |

## Where the split looks

| Offset | What | Record | GU's slot gets |
|---|---|---|---|
| 0x278, 0x27BF | item box (2300) and pouch (32), 19-bit stacks | item | the stack emptied |
| 0x17CF | 24 item loadouts, 32 x {u16 ID, u16 count} at +42 | item (store 2, index 32 k + j) | the entry zeroed |
| 0x62EE | equipment box, 2000 x 36 B | gear (an added piece) / bytes (a vanilla piece with added jewels or look) | zeroed / the piece without them (jewels kept packed, own look) |
| 0x23B39 | worn gear, 7 box indexes | bytes | an added armor piece: none (0xFFFF); an added weapon: a vanilla weapon of the box, same class first, else a starter weapon (class 1, ID 1) in the first entry that was empty |
| 0x240, 0x23B47 | the current weapon class (slot header, player record) | bytes | the replacement weapon's class |
| 0x10C + 44 k + 4 | the slot header's copies of the worn pieces (the slot select, C: MHGU_Editor) | bytes | the replacement's entry, zero, or the piece without its added jewels |
| 0x208C8 | My Sets, 40 x 0x88: box indexes at +0x30, jewel copies at +0x3E | bytes | an added piece's index none, its jewel copies zero; added jewels out |
| 0xC7211 | the own Guild Card's equipment snapshot, 7 x 44 B (shown to other players) | bytes | an added piece zeroed; added jewels and looks out |
| 0xC7AD5 | the card's quest history, 10 x 160 B (+0x06 quest ID) | bytes | a record of one of the mod's quests zeroed (G: GU shows an all-zero record as empty; T3 checks it) |
| 0x11D05A, 0x11D05E | the Item Register touch panels, 2 + 4 u16 item IDs | bytes | zero |
| 0x227A7 + 420 k + 4 | the Melding Pot orders' talismans, 3 x 36 B | bytes | without added jewels |
| 0x5EA6, 0x5FB8, 0x60CA | hunts, captures (u16) and sizes (2 x u16) of GU's dummy entries 105..111 (the six oldest monsters' numbers, D2) | region | zero |
| 0x50BE + 16 | the reserved block (3444 B, copied raw by GU, never read by it, C: notes/save-store.md): the MH4S store, the extra items-obtained bits | region (runs of non-zero bytes) | zero |
| 0x2C77, 0x2D77, 0x2E77 | quests cleared, seen, failed (0x100 B each, bit = list index) | quests (by quest ID) | the bits cleared |
| bit maps below | | bits (runs) | cleared |

| Bit map | Offset | Added from bit |
|---|---|---|
| items obtained | 0x22497 (3008 bits) | 2977 |
| Smithy armor listed, part p | 0x3907 + 576 p (2304 bits) | 4 x armorCreate count: 2252, 2216, 2152, 2068, 2192 |
| Smithy armor NEW, part p | 0x3907 + 576 p + 288 | the larger of 1287 and the listed bound (gear.c reads it by armor ID, MHGU_Editor names it by record: no vanilla mark is ever touched) |
| Smithy weapon listed, type t | 0x36AF + 40 t (160 bits) | weaponCreate count: 95 82 84 86 84 0 98 82 81 80 90 86 75 66 63 |
| Smithy weapon NEW, type t | 0x36AF + 40 t + 20 | the weapon count of the class |
| Smithy weapons by ID, type t | 0x45DF + 128 t (1024 bits) | the weapon count of the class |
| Smithy armor by ID | 0x4D5F (5248 bits) | 1287 |
| Smithy decorations listed / NEW | 0x31A7 / 0x31CB (288 bits) | 275 |
| Hunter's Notes large monsters / NEW | 0x32B7 / 0x32C7 (128 bits) | 123 |
| Meownster hunts per rank | 0x11CFD4 + 12 k (96 bits) | 89 |

Not split (other players' data, or nothing of the mod can be there today): stored Guild Cards and the inbox (0x2C6BD,
0xC9BA5) and Hunters for Hire (0x11B693), which come from other players; the Palico box (no added Palico gear yet);
the card's weapon-usage and per-class counters (no class-5 column); the shared blocks outside the slots.

## The file

Little-endian, created once at 32 KiB (`FILE_SIZE`) and never grown; only the bytes in use are written.

| Offset | Size | |
|---|---|---|
| 0 | 4 | "MHDE" |
| 4 | 2 | format version 1 |
| 6 | 2 | flags, 0 |
| 8 | 4 | bytes used, header included |
| 12 | 4 | FNV-1a 32 of bytes 0..11 and 16..used (no CRC: see notes/save-store.md) |
| 16 | 4 | link ID |
| 20 | 4 | generation, + 1 at each write |
| 24 | 4 | FNV-1a 32 of GU's slot as the split left it (all 0x11F8C4 bytes) |
| 28 | 4 | 0 |
| 32 | | records: {u8 kind, u8 flags, u16 payload length, payload} |

| Kind | Payload |
|---|---|
| 1 item | u8 store (0 box, 1 pouch, 2 loadout), u16 index, u16 item ID, u8 count |
| 2 gear | u16 box index, the 36-B entry |
| 3 bytes | u32 offset, u16 n, the n original bytes, the n bytes GU's slot got |
| 4 region | u32 offset, u16 n, the n original bytes (GU's slot got zeros) |
| 5 bits | u32 offset, u16 first bit, u16 count: that run was all set (GU's slot got it clear) |
| 6 quests | u8 map (0 cleared, 1 seen, 2 failed), u16 n, n x u32 quest ID |
| 7 aside | a whole record (kind, flags, length, payload) the last merge found no place for |

A kind this core doesn't know is kept and written back (as aside). Records are written in this order, and the budget
cuts the list there: worn gear and its fallout (the starter weapon, the weapon class), the slot header's copies, the
card's equipment, the history, the Item Register, the Melding Pot, the tallies, My Sets, the reserved block, the bit
maps, quests, gear, then items. A record past the budget is not written and
its thing stays in GU's slot (logged): every record's change is independent of the others, and the worn gear comes
first, so a piece left in the box by the budget is just not worn.

## The link record

GU's slot keeps 16 bytes of the reserved block (sUserInfo +0x3684, file 0x50BE, D3): "MHDL", u32 link ID, u32
generation, u8 state, 3 x 0. State 1 = split (the file holds the rest), 2 = full (the last save could not write the
file: GU's slot holds everything, the file is stale and never merged on top).

## The merge

One algorithm for every case. Gear first, so that references follow a piece that had to move:

| Record | Goes back when | Otherwise |
|---|---|---|
| gear | its entry is empty, or already holds it | the first empty entry (the worn gear and My Sets follow it); else aside |
| bytes | GU's slot still holds the bytes it got (or already the original) | left as GU has it (the player changed it without the mod) |
| region | GU's slot is zero there (or already holds it) | left as GU has it |
| bits, quests | always (set) | a quest not in this release's list: aside |
| item | its slot is empty, or already holds it | the first empty slot of its store (a loadout entry: aside); else aside |

The exact case (GU's slot unchanged since the split: its hash matches) places every record where it was:
`merge(split(x)) == x` byte for byte, tools/modsave.py test. A restored save that still holds added things (D11)
merges the same way: what is already there counts once.

## In the module (core 3.0.0)

- GU packs a character into its slot of the image (0x3e0ea4): the slot is marked. The image stays complete.
- GU's write (0x877c20, on the save thread, once `savedata` is mounted, 0x877c58): for a marked slot, the split is
  computed; its file is written when its content changed; then the slot is cleaned in place and its link record says
  "split". If the file can't be written whole, the slot stays complete and its link record says "full". GU then
  writes `system` (and next `system_backup`) and commits: the file is in the same commit.
- GU's read of `system` or `system_backup` (0x8778cc; GU writes both from the same buffer and reads the backup when
  `system` is damaged): each slot's file is read into a cache, which mirrors the file from then on (a write updates
  it).
- GU parses a slot (0x3e0db8): the file is merged into the slot's bytes first, and put back as read afterwards (a
  journal of the overwritten bytes), so a later write of that buffer is still clean.
- A slot whose file could not be read, checked (a damaged file, or one of a newer format) or merged this session
  never gets its file overwritten: every save until the game closes leaves slot and file as they are.
- The first split of a character from before 3.0.0 (no link, no file) first copies GU's `system` as it is on disk to
  `system_premigration`, once (D10; an existing copy is kept). GU imports no free-space call, so the copy is tried:
  where the save's size is enforced (a Switch) creating it is expected to fail (G), and the split goes on without it.

## In the installer (2.1.0)

The release's manifest carries the quest list (schema 2 `save_format`, the core's list). Each character is read as
the game sees it (its file merged in when the game would merge it: linked and "split", or beside a restored backup
that still holds added things); migration steps and the cleaning of a monster that leaves work on that view. A
character the installer changed, or whose GU bytes still hold the mod's things (a save from before 3.0.0, a "full"
one, a restored backup), is written split, the file padded to `FILE_SIZE` (the game writes into it and never grows
it), into every copy's folder, before GU's files; every copy of both is in the backup first. A character with
nothing to do keeps both files as they are. A file that is damaged or of a newer format blocks its save (never
overwritten). notes/installer.md "Saves".

## Tools

`python3 tools/test_modsave.py [SYSTEM ...]` runs the three implementations on a synthetic slot and on the saves given
(the installer's through `mhgu-de-cli modsave`, built with cargo). `python3 tools/modsave.py check SYSTEM` lists the
added things a GU file still holds; `unpack FILE` prints a mod file
as text and `pack TEXT OUT` turns that text back into a file; `split` and `merge` work on copies.
