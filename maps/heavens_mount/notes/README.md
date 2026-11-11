# Heaven's Mount (map package)

4U m05 as an alias of GU stage 24 (the Ruined Pinnacle), stage folder m30. Built by `maps/heavens_mount/build.py`
(`tools/build_heavens_mount.py`, then `tools/build_heavens_mount_ui.py`). Required by Stygian Zinogre.

Its study stays with the port that made it: `monsters/stygian_zinogre/notes/heavens-mount.md`.

## Gathering (1.0.1)

The gather points are 4U m05's, verbatim. Up to 1.0.0 their item lists (rItemPopList, Low / High / G) were 4U's
verbatim too, so GU read 4U item IDs as its own and every quest on the map gave the wrong items. Since 1.0.1
`tools/build_heavens_mount.py` (`gu_ipl`) rewrites each list with GU item IDs (`tools/items_heavens_mount.py`;
`python3 maps/heavens_mount/tools/items_heavens_mount.py show` prints the map):
- 4U items GU has under the same English name keep it;
- the earlier ports' substitutes: Yoldspar Ore -> Fucium Ore, Cosmicite Ore -> Meldspar Ore, Strong Armor Sphere ->
  King Armor Sphere;
- Gossamite Ore is dropped, its weight added to the list's most likely item (as Dalamadur's meteor scales);
- no item is added (the maintainer, 2026-11-10): the 6 other 4U-only items take the closest GU item (same kind, icon
  and colour, nearest rarity and price): Stam Nectar: Dragon -> Heavy Jelly, Nectar: Dragon+ -> Dragon Ambrosia, Stam
  Nectar: Dragon+ -> Heavy Jelly+, Glueglopper -> Blossom Cricket, Killer Beetle -> Shiny Beetle, Mistentoe (an
  account item) -> Water Lily Root (GU's account plant).
Each list keeps 4U's entries, counts and weights otherwise (every list sums to 100, checked). Its board name (TXTA)
is in Stygian Zinogre's data file (`monsters/stygian_zinogre/tools/stage_name_em057_01.py`), so it stays with him.
