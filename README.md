# MH4U Port

⚠️⚠️⚠️ Disclaimer: This project is going to be merged (not anytime soon tho) with another bigger project. 
In the meantime, I will still be working on porting monsters and make releases. ⚠️⚠️⚠️

If you are a contributor, I would accept PR, but understand that as it's going to be merged, there are some monsters that are already done and therefore working on them isn't useful.
If you're interested into porting monsters, here is a (non-exhaustive) list of what monsters are actually useful to be ported:
- Dah'ren Mohran (from MH4U) and Jhen Mohran (from MH3U)
- Dire Miralis (from MH3U


--- 

Brings Monster Hunter 4 Ultimate monsters into Monster Hunter Generations Ultimate (Switch, v1.4), with their quests, armor, weapons and skills. They are added to the game; nothing is replaced.

**Monsters:** Gogmazios, Dalamadur, Shah Dalamadur, and Tigerstripe Zamtrios.

Next up is... hum... I have no idea. Maybe Tidal Najarala or Stygian Zinogre.

## Install

1. Get the zips from [Releases](../../releases).
2. Open the game's mod directory (Ryujinx: right-click MHGU > Open Mods Directory).
3. Extract `core` there, then the monsters you want. They all merge into one `MH4U Port` folder.

Unequip a monster's gear before removing that monster. Online, everyone should have the same monsters installed.

## Build

You need your own MH4U and MHGU dumps; no game data is in this repo. Each monster builds with `monsters/<name>/build.sh`, and `python3 tools/release.py all` makes the release zips.

`notes/porting-guide.md` explains how a port works and is the place to start for a new monster.

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later): you can redistribute and modify this project under version 3 of the License or, at your option, any later version. See [LICENSE](LICENSE). Game data and assets stay their owners' and are not covered.
