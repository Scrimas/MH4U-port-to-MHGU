# What's new, per release

tools/release.py puts the section of the core version being packaged into the release text ("What's new"). Two
groups, **New** (something added) and **Fixed** (what works now, not what was broken), one short plain line each,
written for players; write the section before `release.py package`.

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
