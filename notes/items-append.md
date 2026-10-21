# Appending items past GU's 2991 (core, 2026-10-21)

Why: the DUMMY materials 2977..2990 are used up (Gogmazios, Tigerstripe Zamtrios) and Dalamadur needs ~30 items.
User choice (2026-10-21): every new item is APPENDED from 2991 upward (not GU's other DUMMY slots). GU = MHGU 1.4
main offsets. C = read in code / data, S = strong, G = guess. Script: dump/scratch/dalamadur-session/sites.py.

## The table
- rItemData (table\itemData, loc/arc/resident.arc): f32 21.3, u32 2991, 44-B file records, 56-B memory records. It
  is a standard generated table class (C: gu_class('rItemData', 0x41aa6666) -> load 0x192340, alloc 0x1848f8,
  free 0x184934, ctor 0x184960, parse 0x185694, element 0x38, exit 0x19237c), so module/gear.c tbl_append grows it
  from a TBLA block like the gear tables. The exit 0x19237c is already items.c's hook: it appends first, then
  applies the DUMMY patches.
- Text: itemData_<lang> GMD (name 2k, description 2k + 1): TXTA append (gear.c gmd_append).
- No other table in resident / resident_<lang> / blacksmith / facility arcs has 2991 entries (S: scan of 54 arcs).

## Code that knows the count: 44 `movw rX, #0xbad / #0xbae / #0xbaf` sites (no literal-pool copies, C)
| class | sites | action |
|---|---|---|
| bound (`id - 1 <= 2989`, or a loop over all IDs) | 0x1943d8 (obtained set), 0x19440c (obtained clear), 0x6f3df8, 0x6f90f4, 0x6fa504, 0x6fa7ec, 0x6fba28, 0x6fcebc, 0x6fcf98, 0x6fcfb0, 0x6fd020, 0x6fd0e0 (#0xbae: `id - 1 < 2990`), 0x6fd19c, 0x7054e8, 0x709438, 0x7094ec, 0x7094f4, 0x72f2b0, 0x72f890, 0x72fa24, 0x72fbf4, 0x744394 (loop 0x744370 over every ID: category-49 items obtained), 0x78d9e4 (`r1 - 81 <= 2989`, r1 = item + 80) | raise by the appended count |
| per-item buffer | 0x199ae4 item box sort/merge (S): u32[2991] on its stack at sp+8 (frame 708 + 11264, memset 0x2ebc at 0x199b78, loop end 0x199c08; only sp+4 and sp+8 used, one prologue / epilogue): grow the frame (`sub` / `add sp, #708`), the memset size and the loop end. 0x3839bc: heap byte buffer of 2991 (alloc size 0x383f38, count stored at +0x168 by 0x383fd8, reuse check 0x383f14 / 0x383f78 #0xbae, 0x383f88, memset 0x383f9c) | resize together |
| keep | 0x19a504, 0x19a578, 0x19e0c0, 0x19e198 (0x3df1b8(stream, 2991) = the bit width of the saved IDs, 12 bits while IDs < 4096, S); 0x198838 (MHX save import: 1949 old IDs mapped by 0x6aa9b8, 0xbaf = no match, S); 0x385288, 0x3887c8, 0x388868, 0x388908, 0x3889a8, 0x389dd4, 0x38a040, 0x38a094, 0x38a344 (static u16 item lists terminated by 0xbaf, C) | sentinels: never change |
- Other `0x2ebc` hits (0x7008f0, 0x701210, 0x701ed8, 0x70b380, 0x70b4b8, 0x8622c8, 0x863280, 0x86ba34..bc) are struct
  field offsets next to 0x2eb8 / 0x2ec4 (S).

## Save (MHGU_Editor docs/11-save-map.md, C)
- Items obtained: sItem +0x9c, 94 x u32 = bits 0..3007; the Combination List order follows at +0x214. Setter
  0x1943d4 / clear 0x194408 (both bound to 1..2990), test 0x19443c (no bound). IDs 2991..3007 fit the map; IDs from
  3008 go to the extension below through hooks on all three.
- Extension: sUserInfo (global 0x1897f78) +0x3684..+0x43f8 is reserved: zeroed by the initialiser 0x51cb08, copied
  by the saver / loader, read by nothing else (D in the editor's map). Our bits for IDs 3008.. live at its start.
- Item box slots store 12-bit IDs (<= 4095); the pouch and lists store u16.
- Without the mod a save holding appended IDs meets unknown items (behaviour not checked: release-note warning).

## Implementation (core, 2026-10-21; nothing changes while no monster appends items)
- allocations.toml: a monster appends `[monster.append] items = n`; its `items` range must be [2991 + the earlier
  monsters' appended count, + n - 1] (tools/alloc.py checks). alloc.h: PORT_ITEM_COUNT = 2991 + all appended.
- Records: the monster's TBLA block for `table\itemData` (class tuple from gu_class above, 44-B file records,
  base = 2991 + earlier appends); items.c item_data_loaded_c runs gear_tables_loaded on the item table before the
  DUMMY patches. Texts: TXTA `itemData` (2 strings per item, base 2 x that count).
- module/build.py item_patches(): every bound site + the 0x3839bc buffer + the 0x199ae4 loop end raised by n, the
  0x199ae4 memset by 4n, its frame (`sub` / `add sp, #708`) by the smallest 8-aligned encodable grow >= 4n (n = 30:
  708 -> 828); each original word asserted. Hooks obtained_set / _clear / _test (REPLACE) at 0x1943d4 / 0x194408 /
  0x19443c (items.c): IDs < 3008 GU's map, IDs from 3008 sUserInfo +0x3700 (512 B = IDs 3008..7103).
- Checked: simulated n = 30 gives 31 patch words; the real build (n = 0) installs no item hook or patch.
