# Gogmazios Port: release notes (draft, 2026-10-20)

## Multiplayer
- **Every player in the room needs the mod, the same version.** The quest (G4 Hub, quest 11491) and the monster
  (em 0x59) only exist with it. A player without the mod cannot see or load the quest. Joining a modded player's
  quest without it is not supported and may crash or hang that player's game.
- Mixed versions can desync: the monster's behaviour code and the per-monster network bytes must match.
- FPS patches (60 / 120) do not need to match between players, as in the vanilla game: the mod's timing follows
  the game's frame delta. (To confirm in the mixed-FPS test.)
- How it works: the machine that controls the monster (normally the room host) runs its AI. The other players'
  games replay its actions with the same target hunter, and all arena gimmicks follow the players' own actions.
- Tested: (fill in after the PC + Steam Deck test: LDN / RyuLDN, Ryujinx version, what was checked).
- Known limits: (fill in from the test; candidates: cart and doors have no host authority, so a dropped player
  action can leave one machine's cart at another station).

## Quests
- G4 Hub: "Advanced: Quagmire Quarrel" (4U m11014, quest 11491) and "Advanced: Act of Gog" (4U m11035, quest 11492),
  with 4U's fees, rewards, subquests and reward tables. They take two unused placeholder entries of the quest list
  (in memory only), so they need no save change. 4U's Conqueror's Seal G (Act of Gog, 3 %) has no MHGU item and is
  left out.

## Save data
- Gogmazios' hunts, captures and size are recorded in the save's unused monster slot 106 (game's "dummy1",
  registry index 105, monster code 0x1064). No game screen lists that slot: the Guild Card monster log and the
  large-monster total have fixed lists and do not show Gogmazios. Save editors show the slot as dummy1 / slot 106.
  Nothing else in the save changes format.
- Without the mod the slot is ignored by the game (a vanilla game never writes or shows it).

## Items
- The 8 Gogmazios materials and Gogmazios Scrap+ use GU's unused "DUMMY" items 2977-2985. Without the mod they
  show as "DUMMY" in the item box (they stay in the save). The mod patches the item table in memory, so it works
  with UI mods that replace resident.arc / resident_<lang>.arc.
