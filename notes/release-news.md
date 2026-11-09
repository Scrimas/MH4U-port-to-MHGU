# What's new, per release

tools/release.py puts the section of the core version being packaged into the release text ("What's new"). Two
groups, **New** (something added) and **Fixed** (what works now, not what was broken), one short plain line each,
written for players; write the section before `release.py package`.

## v1.10.0
**New**
- The MH4U Port Installer (Windows, Linux): it downloads the monsters you tick into Ryujinx, the yuzu family or an SD
  card, with the maps they need, and updates or removes them.
- The ported arenas are downloads of their own: Battlequarters (Gogmazios), Speartip Crag (Dalamadur) and Heaven's
  Mount (Stygian Zinogre). A monster whose arena is missing stays off instead of loading a missing stage.

**Fixed**
- Sorting the item box works when it holds items from a newer release of the mod: they stay at the end of the box.

## v1.9.0
**New**
- Monoblos, ported by @Rukasu1609, with his MH4U AI and attacks, 6 quests from MH4U (High and G rank, village and
  hub), his Mono S / Mono X armor, 14 weapons in 5 lines and a Hunter's Notes page.
- Black Gravios now has his Hunter's Notes page.
- Ported monsters that MHGU has no record slot for keep their own hunt and capture counts and crown sizes in your save.

**Fixed**
- Ported weapons and armor are listed in the smithy among MHGU's gear of the same rarity.

## v1.8.0
**New**
- Black Gravios, ported by @Rukasu1609, with his 8 quests from MH4U, his Gravios U / Gravios Z armor and 6 weapon
  lines. He has no Hunter's Notes page yet.
- The mod can now be built on Windows as well as Linux.

**Fixed**
- The mod no longer stops the Damage Numbers plugin (Forge) from showing its numbers.
- Gogmazios' tar now shows MH4U's tar icon on the HUD instead of MHGU's web icon.
- Gogmazios no longer skips his second phase when a flinch interrupts his rage roar.
- Dalamadur's fallen meteor scales now show, so you can mine Shattered Omen from them during the fight.

## v1.7.3
**Fixed**
- The mod now works together with the Key Quest Markers plugin (Forge).
- Gogmazios fights a hunter on the side walls as in MH4U: he stands up and uses his tar body shake, his sweeping
  downward laser and his wing scrape, instead of repeating bites and wing slams at the wall.
- Gogmazios' quests now have their full MH4U supply box (First-aid Med+, Rations, Cleansers, ammo and more), with
  Quagmire Quarrel and Act of Gog each getting their own.
- Gogmazios closes his eyes when he dies.
- Stygian Zinogre howls on his charged roar and leaves no charged aura behind when he changes area.
- Stygian Zinogre's quests give only their MH4U rewards (no MHGU tickets or Valstrax materials), and their texts
  name the monsters you actually meet.
- Stygian Zinogre's body marks glow brighter, as in MH4U.
- Stygian Zinogre and Tigerstripe Zamtrios now get a kill cam when the hunt ends.

## v1.7.2
**New**
- Building the mod yourself and contributing are now much easier: one setup script prepares everything from your
  own game dumps, and CONTRIBUTING.md on GitHub walks you through it (what to dump, how to build and test, how to
  report bugs or port a monster).

**Fixed**
- Every ported quest now uses the quest format of MHGU 1.4, the game version the mod is made for. With the game set
  to Chinese, these quests show their English text.
- Gogmazios no longer carries behaviour settings inherited from Kushala Daora (the MHGU monster his data is built
  on) where MH4U has none of its own.

## v1.7.1
**Fixed**
- Gogmazios' tar now covers you in black tar, as in MH4U, instead of white spider web.
- Gogmazios' arm slams no longer throw white "snow" debris.
- Dalamadur's fire breath charges at his mouth again (it showed in the wrong place).
- Stygian Zinogre's horns, spikes and tail now show breaks and the tail cut, and he no longer starts the hunt in his charged state.
- Stygian Zinogre's discharge effect plays once instead of looping every few seconds.
- Heaven's Mount and Speartip Crag: the camp rock is gone, the camp exits work, and vines and lighting look as in MH4U.
- Grey rock chunks from Gogmazios', Dalamadur's and Stygian Zinogre's attacks are no longer shown (they rendered white in MHGU).

## v1.7.0
**New**
- Stygian Zinogre, with his 11 quests from MH4U (Hub High Rank, G★4, Village ★10 and the event quest A Song of
  Extremes), his Zinogre U / Zinogre Z armor, 37 weapons in 12 Brimstren lines and his Hunter's Notes entry.
- Heaven's Mount, his MH4U arena, with its weather, music and breakable rocks (used by his Heaven's Mount quests).

**Fixed**
- Effects attached to a monster's body (roars and similar) now move with it, as in MH4U, for every ported monster.

## v1.6.1
**Fixed**
- The game now launches on yuzu and Eden (it hung on the loading screen). Thanks to a developer of the MH4U HD
  project for the fix.

## v1.6.0
**New**
- Dalamadur, Shah Dalamadur and Tigerstripe Zamtrios have their own icons.
- Tigerstripe Zamtrios moved up to G★3, with more health and better rewards.

**Fixed**
- Hunter's Notes size records now show the new monsters' icons and their sizes (they showed rocks and wrong values).
- Standing on Dalamadur's back above the lake no longer hurts you.
- Running off Dalamadur's back triggers the jump animation, so you can climb onto the nearby wall.
- Dalamadur now moves elsewhere on time: flinching or toppling him no longer resets his countdown.
- Tigerstripe's water beam now inflicts water (it inflicted iceblight, which was wrong).
