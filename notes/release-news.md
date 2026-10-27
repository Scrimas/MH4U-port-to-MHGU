# What's new, per release

tools/release.py puts the section of the core version being packaged into the release text ("What's new"). Two
groups, **New** (something added) and **Fixed** (what works now, not what was broken), one short plain line each,
written for players; write the section before `release.py package`.

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
