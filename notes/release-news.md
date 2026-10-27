# What's new, per release

tools/release.py puts the section of the core version being packaged into the release text ("What's new"). Two
groups, **New** (something added) and **Fixed** (something that was wrong), one short plain line each, written for
players; write the section before `release.py package`.

## v1.6.0
**New**
- Dalamadur, Shah Dalamadur and Tigerstripe Zamtrios have their own icons.
- Tigerstripe Zamtrios moved up to G★3, with more health and better rewards.

**Fixed**
- Hunter's Notes size records showed rocks for the new monsters.
- Standing on Dalamadur's back above the lake hurt you.
- Running off Dalamadur's back didn't jump, so you couldn't reach the walls.
- Dalamadur's countdown to move elsewhere restarted every time he flinched.
- Tigerstripe's water beam inflicted ice.
