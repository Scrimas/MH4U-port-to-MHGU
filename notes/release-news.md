# What's new, per release

tools/release.py puts the section of the core version being packaged into the release text ("What's new"). Two
groups, **New** (something added) and **Fixed** (what works now, not what was broken), one short plain line each,
written for players; write the section before `release.py package`.

## v1.6.0
**New**
- Dalamadur, Shah Dalamadur and Tigerstripe Zamtrios have their own icons.
- Tigerstripe Zamtrios moved up to G★3, with more health and better rewards.

**Fixed**
- Hunter's Notes size records now show the new monsters and their sizes (they showed rocks).
- Standing on Dalamadur's back above the lake no longer hurts you.
- Running off Dalamadur's back jumps again, so you can reach the walls.
- Dalamadur now moves elsewhere on time: flinching or toppling him no longer resets his countdown.
- Tigerstripe's water beam now inflicts water instead of ice.
