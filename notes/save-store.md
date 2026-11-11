# The mod's save store and per-quest slot leases (module/save.c)

**Bits under a key** (Shrouded Nerscylla, 2026-11-06): a record whose first field is a key 0xf001.. instead of an em ID (no em ID is that high) holds 80 bits in its 5 other fields
(save.c save_bits_get / save_bits_set, same seal). module/gear.c keeps there the armor "listed" bits past GU's 576 records per part, one key per part: GU's arrays are never touched. Nothing else
reads these records: every reader looks a record up by em ID, the `loaded:` / `saving:` log lines print the key like an em ID, and a core without this code leaves them alone.

2026-11-04, for issue #16 (Monoblos): every save slot is taken, and a monster without one crashes the game at quest
end (maintainer). This is the smaller step of the save concept: new monsters borrow a slot for their quest, and their
numbers go to a store of the mod's own inside the character's save data. The monsters shipped up to v1.8.0 keep their
slots: for them, and for every existing save, nothing changes. Not done here: an own save file, a save without
ported items and gear (see the end). Hunter's Notes entries past save bit 127 need no store: they have no bit, their
state is computed from the monster's cleared quests (module/notes.c, since Monoblos 0.4.4).

C = confirmed in code or data, S = strong, G = guess. GU = MHGU 1.4 main offsets.

## What GU does

**Save tallies** (sUserInfo = [0x1897f78], the loaded character; T = sUserInfo + 0x72c), C:
- `u16 hunts[137]` at T, `u16 captures[137]` at T + 0x112 (cleared by 0x521b9c, 548 bytes).
- Size records: a vector at T + 0x224 {data, count}, resized to 137 by 0x521b9c -> 0x527d78(T + 0x224, 137); each
  8-byte entry points to `u16 {smallest, largest}`.

**Writers**, one caller each: the quest-end writer 0x38d990, which walks the 137 indexes in the order of the table
0x162a250 and, for an index with a hunt or a capture in the quest (C):

| call | does |
|---|---|
| 0x38dcdc(this, index, n) | hunt-count milestones; skips indexes 105..111 and 133 (mask 0x1000007f) |
| 0x50bdc(index) | index -> ID (index 105..111 -> 0x1064..0x106a) |
| 0x526d94(T, id, n) | hunts += n, at most 9999 |
| 0x526e00(T, id, n) | captures += n, at most 9999 |
| 0x1c95a4(.., id) | hunted-at-rank bits; IDs > 88 skipped |
| 0x55ff98(mgr, id, 0) | size ID (merges some variants; other IDs unchanged) |
| 0x526f48(T, size id, 1 / 0) | the current largest / smallest, for the result screen |
| 0x526eb0(T, size id, size) | 1 = new largest (stored < size) |
| 0x526ef8(T, size id, size) | 1 = new smallest ((u16)(stored - 1) >= size; 0 = none yet) |

New records go to a list of the result object (+0x190, 10-byte entries {size ID, old largest, size, old smallest, 0})
and to 0x1636a8 (the result's top-3 highlights): both transient (S).

**Readers by ID** (index from 0x50b64): 0x523104 hunts + captures (9 callers, the Hunter's Notes page 0x560058),
0x526dd4 hunts (14 callers: 0x560418, 0x3ec018, 0x3efb30, 0x3f7500), 0x526e44 captures (9 callers: 0x560238, the Notes
page's "captured"), all with `cmp r0, #136; bhi -> 0`. **0x526f48 has no bound** (8 callers: the writer, the Notes
page 0x5b20b0, 0x161ac8, 0x3f3624, 0x3f3824): an index past 136 reads past the 137-entry vector. 0x526e74 (by index,
5 callers in the Notes list) bounds at 136. C

**The quest's tally**: the quest object [0x188ad90] + 0x110 + index * 8 = {u16 largest, smallest, hunts, captures},
written by the tally 0x3a75c8 (hunts / captures at 0x3a7618, sizes at 0x3a78fc, no bound), read by 0x3a3930 (one
caller, 0x2626c4) and the writer. C

**Character save / load**: 0x51d0a0 / 0x51dbb4 (callers 0x3e7634 / 0x3e77ec) write / read +32 (1024 bytes), the bulk
0x51d12c / 0x51dc40, the hunts, captures and size records. C

**The reserved block** sUserInfo + 0x3684..+0x43f7 (0xd74 bytes): written raw by 0x51daa8 (in 0x51d12c) and read raw
by 0x51e5c0 (in 0x51dc40); zeroed with +0x3682 (0xd76 bytes) by the initialisers 0x51c91c and 0x51cbe4 (C). No other
GU code uses it (S): every function that loads sUserInfo (625) was searched for offsets inside the block; the hits
were halves of movw / movt pairs (offsets 0x1xxxx of other objects), allocation sizes (0x3d8b10), masks and
multipliers, and other objects (0x55f238 writes +0x36cc.. of [mgr+0x45e8], 0x6e314c +0x3900 of a UI object). The
register flow was not followed through every function, hence S. The core already keeps the items-obtained bits of
IDs 3008.. at +0x3700..+0x38ff (module/items.c), the save link record at +0x3684..+0x3693 (core 3.0.0,
notes/mod-save-format.md), and module/notes.c reads +0x36fc, in the unused part between them, as a word that is
always zero.

## What the core does

**allocations.toml**: a monster with `save_index` (the 7 dummy slots, every monster up to v1.8.0) keeps it. A new
monster takes `save = "lease"` instead (tools/alloc.py: no save_index; name entry and Notes as before).

**Leases** (save.c save_slot_tally, from main.c stats_add): a lessee's first tally in a quest borrows a slot: its
slot of the last quest if still free, else 109, 111, 110, 108, 107, 106, 105 (109 first: the tails' shared slot has
no icon, size data or name entry of its own). A slot is free when no other lessee holds it in this quest, the quest
has counted nothing in it, and it is not the fixed slot of a monster of this quest. A ported monster only spawns in
its own quests (main.c standin_swap), so a lessee never meets the owner of its slot; if an owner is still counted in
its slot while a lessee holds it in the same quest, the lessee's quest entry moves to another free slot first. A
fixed-slot monster's tally takes its slot back. A character load ends every lease. Seven ported monsters killed in one
quest would leave no free slot: the eighth is counted in slot 109 with another (logged), never past index 136.

**While a slot is leased** it shows the lessee in the quest result: name (main.c name_index_c: the slot's index ->
the lessee's name entry), icon (reg_icon[slot] = the lessee's), size and crowns (the slot's em_size_scale_data
element, main.c size_slot_dress; the as-built values come back with the owner) and break rewards (items.c
bui_record_c: the slot ID -> the lessee's record).

**Writes**: the hooks on 0x526d94, 0x526e00, 0x526eb0 and 0x526ef8 work on the lessee's store record for a leased
slot ID, with GU's rules (cap 9999, (u16) wrap, 0 = no size) and GU's return values, and return without running GU's
function: **the owner's GU record of a leased slot is never written**. Any other ID runs GU's function unchanged.

**Reads**: 0x523104, 0x526dd4, 0x526e44, 0x526f48 and 0x3a3930: a lessee's em ID (and 0x526f48 a leased slot ID) is
answered from the store; a fixed-slot monster's em ID reads its slot. The last part also changes two things for the
monsters up to v1.8.0: the Notes page's "captured" (0x526e44 answered 0 for an index past 136) and its size records
(0x526f48 read past the vector) now show the slot's numbers. To check in game.

**A record's crown and cm**: 0x67310(mgr, id, size, out {u8 crown, f32 cm at +4}), 10 callers (the Notes page, among others),
searches em_size_scale_data for the ID's registry index. A ported index has no element, so nothing was written and the Notes
page showed 0 next to the record it had read (user's test 2026-11-06: 98 and 114 in the store, 0 and 0 on Monoblos' page). The
hook save.c size_lookup_c asks under the slot's ID for a fixed slot's monster, whose element is its own (main.c size_data), and
answers a lessee itself with GU's rules on its package.toml [size]: for every size 0..400, crown and cm equal GU's function bit
for bit (GU's code emulated with an element of the same numbers; a scratch check, C).

**The store** (sUserInfo + 0x3900..+0x43f7, 2808 bytes, 232 records):

| offset | size | |
|---|---|---|
| 0 | 4 | magic "MH4S" |
| 4 | 2 | version 2 (core 2.0.0; version 1 up to core 1.9.0: read, and turned into version 2 at load) |
| 6 | 2 | records |
| 8 | 4 | FNV-1a 32 of bytes 4..7, (version 2) bytes 12..15, and the records |
| 12 | 4 | version 2: the migration level, the last save-migration step the installer applied to this character (installer/core/src/saves.rs; the core never changes it); version 1: 0 |
| 16 | 12 each | {u16 em ID, hunts, captures, smallest, largest, flags 0} |

The rest stays zero. An all-zero block is an empty store; the first lessee record writes the header. A block that is
neither empty nor a valid store (another tool's data, a damaged store, a newer version) is never written: the
lessees' numbers are then not recorded (logged), the hooks still keep GU's slot records untouched. FNV-1a instead of
a CRC: a bit-by-bit CRC loop could be compiled into ARMv8 CRC32 instructions (tools/test_save.py refuses them).

**Logs** (Ryujinx guest log): `store sUserInfo+3900 ...: empty / valid, N record(s) / NOT a store`, `X leases save
slot 109 (id 1068) for quest N`, `save slot 109 (id 1068) shows X`, `X +1 hunt(s) -> store N (slot 1068
untouched)`, `X size N: largest record new / kept`, and at every character load and save the 7 slots' hunts and
captures plus the store's records (`loaded:` / `saving:`).

## Effects on saves

| Case | Effect |
|---|---|
| A save of v1.8.0 or older, the 6 shipped monsters | Nothing changes: they count in their slots as before; the store stays all zero until a lessee is hunted (tools/test_save.py test_fixed: no byte of the character changes) |
| A lessee hunted (Monoblos, or the TEST_LEASE build) | Its numbers go to the store; GU's records of the slots are not written |
| Back to v1.8.0 | v1.8.0 never reads +0x3900..: the store stays as it is; the 6 monsters' numbers are where v1.8.0 expects them |
| Mod removed | GU copies the reserved block raw: the store stays in the save, unused, and is back with the mod |
| New character | GU zeroes the block: an empty store |
| Another character | The store is part of each character's data |
| Save editor | Keeps the block if it copies it (G); if it zeroes it, only lessees' numbers are lost |
| Online | Each player's own save, as before |

## Tests

- `python3 tools/test_save.py`: save.c with the module's flags under unicorn (ARM), 13 tests on a fake character with
  the real IDs of v1.8.0 and two test lessees: fixed slots write no byte; a lessee's quest (lease, dressing, writes
  and reads with GU's rules); an owner taking its slot back; the same-quest conflict; two lessees in one quest; data
  that is not a store, a damaged store, a newer version and a full store (never written); the 9999 cap; no
  character; a character load; a record's crown and cm; bits under a key. Every test of the store checks every byte of the character
  outside it.
- In game (Ryujinx, solo): a real hunt of Monoblos, quest 10784, 2026-11-05: `monoblos leases save slot 109 (id 1068)`,
  `monoblos +1 hunt(s) -> store 1 (slot 1068 untouched)`, `monoblos size 114: largest record new`, the `saving:` lines show
  slots 105..111 unchanged (109: 0 hunts) and `store em 107: hunts 1, captures 0, smallest 114, largest 114`; after a restart
  on 2026-11-06: `store ...: valid, 1 record(s)` with the same numbers. A second real hunt of 10784 on 2026-11-06:
  `monoblos +1 hunt(s) -> store 2 (slot 1068 untouched)`, `monoblos size 98: smallest record new`, `saving: store em 107: hunts
  2, captures 0, smallest 98, largest 114`. With the size_lookup hook, Monoblos' Notes page shows his size records (the user, on
  screen, 2026-11-06; the hook writes no log line).
- In game, to do: a capture through the store; the 6 monsters' quest result (name, icon, crowns) and Hunter's Notes counts and
  sizes; the TEST_LEASE build (`GOG_DEFINES="TEST_LEASE=7"`: Black Gravios acts as a lessee).

## Not in this step

- monsterName entries: 'dummy5' (entry 109) is the last free dummy name; more need an append to monsterName and a check
  of how GU reads that GMD's second list (entries 137..267).
- An own save file next to GU's save (the definitive fix, every platform to test) and a save without ported items or
  gear (removing the mod safely).
