# GU EFL effect entries and units (for authoring particle effects)

Static study, 2026-11-04 (MHGU 1.4 main, Ghidra project dump/gu/ghidra; corpus = the 1648 unique EFLs of the GU
romfs nativeNX/arc, version 0x20120306, all with fps 60). Marks: **C** confirmed by code (function + logic),
**S** strong (corpus statistics), **G** guess. 4U uses the same container (efl4u2gu.py), so this mostly holds there too.
Reader: `weapons/magnet_spike/tools/efldump.py` (prints these fields by name; `--raw` adds the unknown words).

## Container (recap, C + S, see tools/efl4u2gu.py)
Header 0x30 B (`EFL\0`, u32 version, u32 size - 0x30, f32 fps, u16 n entries, u16 n2), then n x 16-B entries,
then n2 u32 tail offsets, then the blocks. Offsets are from file +0x30. Blocks can be shared between entries.

## One entry = 4 blocks (C: 0xaec864 / 0xa58fa8)
Each entry word = `(block offset - 0x30) << 8 | type byte`; resource +0x68 = entry table.

| word | generator field | block | type byte |
|---|---|---|---|
| w0 | gen +0x30 (0xaec864) | **element** block, always 0xc0 B (S) | 0..44: copied to gen +0x1e (C); an index, not a class |
| w1 | gen +0x34 (0xa58fa8) | **unit** block (class specific, 0x1a0+ B for Billboard) | class, gen +0x40 byte 0 (C) |
| w2 | gen +0x38 | **emit** block, 16 B (0x20 B when type high nibble is 5) (S) | 0x11 / 0x12 / 0x21 / 0x22 / 0x51 / 0x52; bits 4-7 -> gen +0x40 bits 12-15 (C) = fade mode used at particle init/update (0xa7d870, 0xa7de94: mask 0xaa vs 0x154 picks alpha vs colour scaling by life) |
| w3 | gen +0x3c | **move** block (kind = low nibble: 0 16 B, 1 / 2 0x50 B, 5 / 8 0xc0 B, 6 0x80 B) (S) | low nibble -> gen +0x40 bits 16-19 and 20-23 (C); **bit 4 set = 'Lite' class** (factory, C) |

Also per entry (C, 0xaec864): gen +0x28 = resource +0x70 + index * 0x44 (runtime record; its +0x14 = the loaded EAN /
texture-anim resource: zero -> no UV animation, 0xa69d00); gen +0x14 = index << 16 | count.

## Unit type -> class (C: GU factory 0x9bdc68, called by the unit build 0x9bda64)
All generator objects are 0x1d0 B (0x250 for type 0x19). `L` = class when w3 type bit 4 is set.

| type | class | type | class |
|---|---|---|---|
| 0 | Billboard (L LiteBillboard) | 0xd | Texline |
| 1 | Polyline when L (LitePolyline), else same as 0xc | 0xe | Line |
| 2 | Polygon (L LitePolygon) | 0xf | PolygonStrip |
| 3 | Texline | 0x10 | Custom |
| 4 | Line | 0x11 | ClothPolygon |
| 5 | Model | 0x12 | Adhesion |
| 6 | PrimModel | 0x13 | BillboardStrip |
| 7 | LensFlare | 0x14 | SizeBillboard |
| 8 | MassBillboard | 0x15 | LightShaft |
| 9 | Filter | 0x16 | Point |
| 0xa | Light | 0x17 | AxisPolygon |
| 0xb | Hit | 0x18 | Force |
| 0xc | Polyline (0x1790c84) | 0x19 | node class (DTI 0x2123d5c; L cParticleNodeInfinite) |
| | | 0x1a | Trail |

Type 1 without the Lite bit is created as type 0xc = cParticleGeneratorPolyline (C).
Vtables (slot 0 address; DTI GOT 0x1843968..): cEffectUnitGenerator 0x179007c, cParticleGenerator 0x17900fc,
Billboard 0x179017c, LiteBillboard 0x17902c0, Model 0x17907fc, Polygon 0x17908fc, Polyline 0x1790c84,
Filter 0x17903fc, BillboardStrip 0x17901e8, SizeBillboard 0x1790254. 25 virtual slots.
Billboard overrides: 6 0xa7b114 (bind entry 0xa58fa8, then allocate the particle pool: 0xb0-B particles, C),
8 0xa7b140 (setup from the unit), 15 0xa7b370 (create), 16 0xa7b42c (frame update; Strip / Size sub-blocks at
unit +0x19c / +0x1b0), 17 0xa7b560 (translate all particles), 21 0xa7b580 (vertex build / draw, switch on gen
+0x46), 23 0xa7d870 (**particle init**), 24 0xa7dd74 (**per-frame particle loop**, 0xa7de94 per particle;
dead particles freed by 0xa5b224). Base: slot 8 0xa59268 (shared setup), slot 16 0xa5a0c4 (matrices).

Random numbers (C): every random draw is `table[++gen->counter & 0xfff]`, a 4096-entry float table; the
fields below combine as `value + r * range`. The colour code scales r by 256 (0xa6be40), so r is in [0, 1) (S:
rotation -pi + r * 2pi covers the full circle in 1848 / 2096 Billboard units). Integer ranges use
`lo + rand_u32 % (range + 1)`.

## Element block (w0, 0xc0 B, shared by every generator class)
| off | type | meaning | ev |
|---|---|---|---|
| +0x00..+0x0c | u32 | ids / flags; +0x08 bit 27 = GU-only flag (0x08000000 in 1258 / 1634), copied to gen +0x8c (0xaec900) | C / S |
| +0x10..+0x2c | s32 x 8 | joint / attach references, -1 = none (1578 / 1634 all -1) | S, G |
| +0x30 | u32 | always 0x66 (S); bits 0-3 -> gen +0xe8 bits 12-15, bits 4-7 -> bits 8-11 (0xa59268) | C |
| +0x40, +0x44 | f32 x 2 | value + random -> gen +0xf8 (1.0 in 1573 / 1634; time scale / frame speed) | C, G meaning |
| +0x48 / +0x4c / +0x50 / +0x54 | u32 | small ints (1-4) | S |
| +0x60/64, +0x68/6c, +0x70/74 | f32 pairs | value + range, frame-like magnitudes (30, 50, 100) | S, G (wait / life / interval) |
| +0x78 | u32 | byte 0 -> gen +0xe4 bits 16-23, byte 1 -> gen +0xe4 bits 24-31, byte 3 -> gen +0xe8 byte 0; bit 16 -> gen +0x194 bit 25 | C |
| +0x80, +0x84 | f32 pair | value + range (0..1) | S |
| +0x88/8c, +0x90/94, +0x98/9c | f32 pairs | value + random -> gen +0x160 / +0x164 / +0x168 (1.0 in all 1634: element scale x/y/z) | C, G meaning |
| +0xa0 | u16 | -> gen +0xe4 low 16 | C |
| +0xa2 | u16 | bits 0-3: transform mode (-> gen +0x50 bits 24-27) when +0xbe != 0 | C |
| +0xb0 | f32 | != 0 -> gen +0x194 bit 24 | C |
| +0xb4 | u16 / u16 | lo != 0: random draw -> gen +0x1a8, gen +0x10 bit 9; hi != 0: gen +0x10 bit 10 | C |
| +0xbe | u16 | offset (from the element block) of a transform sub-block: floats [0..2] -> gen +0x60, [4..6] -> gen +0x70, [8], [9] -> gen +0x80 / +0x84 | C (0xaec900) |

## Emit block (w2, 16 B) — S / G only
Four u32, observed as small integers or u16 pairs: +0 (0 / 5 / 10), +4 (often a u16 pair, e.g. lo 0 hi 15),
+8 (10 / 20 / 30), +0xc 0 or 1 (152 / 1586). G: wait / interval, count (+ random), emitter life, loop. The reader
was not traced (next step: callers reading gen +0x38). (Superseded: the emit block = particle life, C, "Main-agent
decode" below.)

## Move block, kind 2 (w3, 0x50 B) — the most common (8980 of 15086 entries)
Corrected and extended (C) by gu-efl-move.md ("Corrections to gu-efl-units.md"; +0x48, +0x50..+0x6c below are wrong).
| off | type | meaning | ev |
|---|---|---|---|
| +0x00 | u32 | flags; byte 0 bit 4 -> gen +0xdc bit 25 (0xa59268); 0x01000000 in 2390 / 3123 | C / S |
| +0x04 | u32 | bits 8-11 -> gen +0xec bits 4-7, bits 12-15 -> gen +0xec bits 0-3 (0x4200 / 0x4400 / 0x4500 = mode) | C, G meaning (spawn shape / direction mode) |
| +0x10/14, +0x18/1c, +0x20/24 | f32 pairs | angle + range in radians (-pi..pi, ranges up to 2pi) | S (emission direction X / Y / Z) |
| +0x28, +0x2c | f32 pair | 10 / 5 / 20 + range 2 / 4 | S, G initial speed |
| +0x30, +0x34 | f32 pair | 0.1 / 0.2 (-20..5) + range | S, G acceleration / gravity |
| +0x40, +0x44 | f32 pair | 1.0 / 0.98 / 0.95 + range | S, G velocity damping per frame |
| +0x48 | u32 | 0 / 4 / 8 / 5 | S |
| +0x50..+0x6c (0xc0-B kinds) | f32 pairs | value + random -> light object gen +0x1b8 +0x10..+0x1c (colour * intensity) | C (0xa59268) |

## Unit block, Billboard (type 0), 0x1a0 B + appended curve tables
Common head (all generator units, C 0xaec900): +0 byte 0 -> gen +0x44 byte 0, byte 1 -> 0xafccc8 -> gen +0x45,
byte 3 = blend index (BSBlend table, efl4u2gu.py); +4 -> gen +0x90 (flags; bits 18 / 20 / 21 / 22 select
gen +0xec bits 7 / 11 / 12, 0xa59268); +8 -> gen +0xa0; +0x18 bits 0-3 colour mode -> gen +0x40 bits 24-27,
bit 17 -> gen +0x40 bit 31, bit 18 -> gen +0x194 bit 28, bits 4-7 != 0 -> draw variant gen +0x46 = 0x17 / 0x2f
(else 0x19) (0xa7b140); +0x1a bit 0 -> gen +0xec bit 10; +0x1b -> gen +0x52.

| off | type | meaning | ev |
|---|---|---|---|
| +0x0c | s32 | -100 / -200 / -50 typical | S (G: draw priority / z bias) |
| +0x10 | f32 | 0 / -100 / -500 / -1e4 | S |
| +0x14 | u32 | byte 2 = 20 / 10 / 60 | S |
| +0x18 | u32 | flags (above); 0x00080000 = bit 19 on almost every GU Billboard | C / S |
| +0x1c | f32 | 0.5..1.15 (1.0, 0.98, 0.95) | S, G per-frame size / alpha factor |
| +0x20 | f32 | -> gen +0x188 -> particle +0x58 and +0x50 / +0x54 = int(value * k) (0xa6a2a4); 1 / 2 / 4 / 10 | C, G meaning |
| +0x28, +0x2c | f32 pair | 0.75 / 1.25 / 2.5 + range (0..2.5) | S, G particle size + random |
| +0x30, +0x34 | f32 pair | 0.05 / 0.075 (-1.25..3.75) + range | S, G size change per frame |
| +0x38..+0x46 | u16 x 8 | offsets (from the unit) of appended curve tables, 0 = none: +0x42 = colour / alpha curve (C: slot 23 / 0xa7de94 `unit +0x40 >> 16`), +0x44 = UV-animation frame curve (C 0xa69d00), +0x3e = table for gen +0xcc (C slot 23); +0x38 / +0x3a / +0x3c / +0x46 G (size, other tracks) | C / G |
| +0x40 | u8 | **colour random mode** (Billboard copies it to gen +0x194, 0xa7b140): bits 0-3 != 0 -> lerp colour A..B by r (bit 4: one r per channel), else bit 5 -> pick A or B at random, else A (0xa6be40) | C |
| +0x41 | u8 | bit 0: UV frame curve gives an offset added to the start frame instead of an absolute frame (0xa69d00) | C |
| +0x48, +0x4c | RGBA8 | colour A / B (gen +0x170 / +0x174, gen +0x180 = &A for the GU PEL recolour) | C |
| +0x50 | u32 | lo16 UV flags: bit 4 / 10 / 11 = randomly set particle flip bits 2 / 8 / 9; bits 8 / 9 / 12 = draw state (0xa7c210); byte 2 = EAN entry index, byte 3 = its random range (index + rand % (b3 + 1)) | C |
| +0x54 | u16 / u16 | UV start frame + random range (frame + rand % (hi + 1)) | C (0xa69d00) |
| +0x58 | f32 | UV animation speed (frames per frame) | C |
| +0x5c | f32 | UV frame clamp when a frame curve is used | C |
| +0x60, +0x64 | u32 | pivot x / y in texels (= EAN pivot; 256 / 64 / 128) | S |
| +0x6c | f32 | 5.0 in all 2096 | S |
| +0x70 | char[0xc0] | texture path (`effect\base\...`, no extension; tex type 0x241F5DEB) | S |
| +0x130 | char[0x40] | EAN path (`effect\base\...`) | S (C notes: EAN = UV atlas) |
| +0x170, +0x174 | f32 pair | initial rotation (rad) + random range (-pi + r * 2pi typical) -> particle +0x74 / +0x84 | C (0xa7d870) |
| +0x178, +0x17c | f32 pair | angular speed (rad / frame) + range -> particle +0xa4 (non-zero sets particle flag 8 / 1) | C |
| +0x180, +0x184 | f32 pair | 1.0 + range | S |
| +0x190 | f32 | angular speed damping: each frame rot += w; w *= +0x190 (bit 13 of the particle flags also multiplies a per-particle factor) | C (0xa7de94) |
| +0x194 | u32 | 1 = random sign for the angular speed | C (0xa7d870, G for the exact op: a conditional vneg) |
| +0x198 | u32 | offset of a rotation curve; when set, rotation = curve(particle time) instead of the constant (0xa7de94 / 0xa7d870) | C |
| +0x19c / +0x1b0 | u32 | (BillboardStrip / SizeBillboard only) offsets of their extra track blocks (0xa7b42c) | C |

Curve tables (C for the colour use, S for the layout, efl4u2gu.unit_curve_props): `u32 count | 2 << 8 | prop << 24`
(prop 0 colour, 1 alpha, 0x40 scale), then `count` keys of 12 B `{u32 frame, u32 a, u32 b}`. The evaluator
0xaed74c (time) + 0xaf938c (colour) / 0xaf7958 (float) takes the particle; key word 0 < 0 (bit 31) marks a
looping / non-life track (`-1 < *curve` sets particle flag 0x20000 / 0x80000). Time base (frames vs life fraction)
and interpolation: not traced (G: linear, frames). (Superseded: byte 3 is a flags byte with the time source, C,
"Main-agent decode" "Curve header"; the interpolation table 0xaf7a80 is still unread.)

## Particle (0xb0 B, list at gen +0xb0, next +4) — runtime, for reading the code
+0x20 / +0x30 position (current / previous), +0x50 / +0x54 / +0x58 from unit +0x20, +0x60 motion state (0xa6a004),
+0x70 / +0x80 rotation pair (double-buffered by particle +0xf bit 0), +0x90 / +0x94 colour, +0x98 base colour,
+0xa4 angular speed, +0xa8 second rate (adds to +0x78, death when < 0), +0xa0 motion record.

## Open
Updated 2026-11-11 (the 2026-11-04 list, with what the later sections settled):
- Emit block: decoded ("Main-agent decode": particle life, emission types 1 / 2); open: the burst interval / end
  readers 0xa5c464 / 0xa5c7dc.
- Particle life, age and motion: decoded ("Main-agent decode"; motion kinds 0-11 in gu-efl-move.md, C); open: the
  spawn shapes of move +0x04 beyond the box shape (0xa5e450 case 1).
- Size: decoded ("Main-agent decode" "Size", 0xa6a2d0 / 0xa6a434).
- Curves: time source and keys decoded ("Curve header"); open: the interpolation jump table 0xaf7a80.
- Billboard orientation modes (gen +0x46 0x17 / 0x19 / 0x2f from unit +0x18 bits 4-7) in the draw 0xa7b580.
- Polyline (types 1 / 0xc, vtable 0x1790c84: init 0xab76d8, loop 0xab7f2c) not decoded beyond the shared head.
- Model: type 5, its transform, look (UV layers incl. the extra ones, colour, material), blend, limits and record
  masks decoded below; open: the mesh mask +0x110 read side (S), the blend on the scene-model path (G), the shader
  math behind the material features (vertex colour x2?, lighting, depth write: G), the name of DTI 0x21293e8 (the
  effect material class the ready check wants, effect-posts.md "Open").

## Unit block, Model (type 5) (static, 2026-11-11; C unless marked)
Vtable 0x17907fc: slot 6 0xa9499c bind (0xa58fa8, then 0x120-B particles, + 0x20 x (unit +0x138 bits 24-27 + 1) when
unit +0x134 lo16 != 0), 8 0xa949f8 setup, 15 0xa94b48 ready check, 17 0xa94bd8 translate, 19 0xa94bf8, 20 0xa94c10
scene-model update, 21 0xa956d8 draw, 23 0xa9958c particle init, 24 0xa9a154 loop (0xa9a280 per particle).

**Resource resolution.** rEffectList (vtable 0x1793aa4) load 0xb5c5cc ('EFL', version 0x20120306) -> 0xb5c770: n
0x44-B records at resource +0x70 -> 0xb5c878 per entry: 0xb5b97c clears the record, 0xb5bab0 element +0xb8 / +0xba
/ +0xbc (offsets of path strings, flags 0x20 / 0x200 / 0x400 when unresolved), 0xb5c288 move block, 0xb5bbec unit
block by type. Type 5: unit +0x50 (char[0x40]) -> sResource (0x2126a64) vt+0x30(rModel DTI 0x21251c8, path, 1) ->
record +0x18; empty path -> record +0 |= 0x2000, not found -> |= 0x10; unit +0x138 lo16 = offset of an EAN path ->
rEffectAnim -> record +0x14 (0x1000 / 8). The lookup is by path + type (no arc named in the code; S that it finds
what the loaded arcs hold, as GS's cm010_000 in its own class arc). rModel (vtable 0x1792f34): load 0xb490cc takes
MOD version 0xd4 only; +0x84 material count, +0x218 material names (0x80 B), +0x74 / +0x78 meshes (0x30 B) / count.
Post-load (slot 10, 0xb49854): the rMaterial (DTI 0x21250f8) of the model's own path -> +0x210; per material name
MRL vt+0x40(name) -> +0x214[i]; missing MRL or name -> a default material (global 0x2126afc +0x4304c).

**Ready check 0xa94b48.** Skipped when unit +0x1a bit 0 is set (gen +0xec bit 10, 0xa59268). Else every material of
record +0x18 (rModel vt+0x40 0xb48d70 = +0x214[i]) must pass sEffect (0x2126554, vtable 0x179510c) vt+0x6c =
0xb91ef0: material DTI id (+0x1c) == DTI 0x21293e8's (unnamed in dti.pkl; S: the class 0x5fb0ebe4 that every GU
effect-model material carries). Then the shared 0xa59ce4: move kind 5 needs move +0x70 (else 0). A failure makes
0x9bda64 set effect +0xf0 bit 0x2000000: no generator of the effect runs. A null record +0x18 is dereferenced
(G: a crash rather than a quiet fail).

**Setup 0xa949f8.** Draw mode gen +0x46: unit +0x1a bit 0 -> 0x37 (scene model); else 5, or 0x1e when 0xa5b880 holds
(unit +2 bit 0). Unit +0x100 bits 0-3 -> gen +0xe8 bits 16-19, bits 4-7 -> bits 24-27 (!= 6 sets gen +0xdc bit 30);
+0x10e bit 4 -> gen +0x44 bit 3; +0x11c -> gen +0x1ac; +0x40 / +0x48 / +0x4c colour mode and colours as Billboard.

**Particle init 0xa9958c.** Frame (0xa99a38): unit +0x100 bits 12-21 + rand % (bits 22-31 + 1), or the frame curve at
unit +0x44 -> particle +0x108; particle +0x100 = 0xb49090(model, frame) = index of the first mesh whose group
(MOD mesh d0 & 0xfff) equals the frame, 0 when none. Colour: curve unit +0x42 (0xaed74c / 0xaf938c; header >= 0 ->
particle flag 0x20000, re-evaluated every frame by 0xa9a280) else colours A / B (0xa6be40), alpha or colour scaled by
the emit fade (gen +0x40 bits 12-15, masks 0xaa / 0x154). Scale 0xa6b59c: unit +0x90 (value, range) x 3, +0xa8
rates, or the curve +0x132 (keys 28 B: u32 time, 3 x (value, range); particle flag 0x800000). Rotation 0xa6adac:
unit +0xd0, +0xe8, curve +0x130. Unit +0x10c bits 20-23 -> particle +0x100 bits 12-15, bit 31 -> flag 0x8000 (scale
rates x unit +0xc0..+0xc8 per frame); +0x114 -> particle +0xf8; +0x134 lo16 -> UV layers (0xa99f40, "Model look").

**Draw.** Effect mode (gen +0x46 5 / 0x1e; 0xa956d8 returns for any other value): per particle 0xa9af40 ->
0xc90094(context, record +0x18, the owner position, unit +8, (unit +0x10c >> 20) & 0xf, owner +0x208 + unit +0x120)
and 0xc90380(particle +0xf8, ..., particle +0x100 & 0xff, ...) (S: draws that one mesh). Scene-model mode (0x37):
0xa94c10 gives each particle a GU model unit (0xa955b0: 0x500 B via 0xc6b66c / 0xc6b6a8, moved by 0xc08100, vt+0x58
= record +0x18) with the particle's matrix, alpha (+0x158), material colour (vt+0x2c) and mesh mask +0x110: for j <
the mesh count, bit j = (j == particle +0x108) (C; S that +0x110 is the meshes' display mask). The unit blend byte is
not read on this path (G).

**Blend (C, 2026-11-11).** Particle init 0xa9958c: particle +0x18 = (unit +0 u32 >> 19) & 0x1fe0 = unit byte 3 << 5.
The effect draw 0xa956d8 (mode 5) -> 0xc90380 -> 0xc90b50(rModel instance, draw context, ..., stack: colour, particle
+0x50, particle +0x18, particle +0xc bits 16-23, UV block): after the material set 0x87a048 (0xc91114) it calls the
model helper 0xb007fc(context, particle +0x18) at 0xc928ec: index = (word & 0xffff) >> 5 (> 0x22 -> 1) into the
blend-state table (0 BSBlendAddAlpha, 1 BSBlendBlendAlpha, 5 / 6 reverse-subtract: efl4u2gu, C) -> context +0x118, dirty
bit context +0x10c bit 13. So the unit's byte 3 sets the blend over the material's own (BSBlendAlpha in every GU
effect material: 4708 / 4708 effect-mode units of the player arcs, byte 3 = 0 on 24 of them). Ghidra stops 0xc90b50
at 0xc9127c (the noreturn memcpy thunk 0x13efe30); the rest is read in dump/gu_main/main.asm (0xc90b50-0xc929xx).

**Fields only the effect path reads** (template cm123_041 e0 -> GU weapon-arc effect-mode units / efl4u2gu em089-090):
| field | use | e0 | GU effect | efl4u2gu |
|---|---|---|---|---|
| +2 bit 0 | 0xa5b880: draw mode 0x1e instead of 5 (C) | 0 | 0 | 0 (4 x 1) |
| +3 | blend index (S, above) | 1 | 1 / 6 / 0 | 1 / 0 / 5 / 6 |
| +8 | gen +0xa0 -> 0xa9af40 block; 0xc90094 argument (C; G meaning) | 1 | 0 (3308 / 3327) | 0 / 1 |
| +0x10c bits 20-23 | 0xc90094 argument, particle +0x100 bits 12-15 -> 0xc90380 (C; G meaning) | 1 | 0 | 0 |
| +0x10e bit 4 | gen +0x44 bit 3 (0xa949f8, C) | 1 | 0 | 0 |
| +0x100 bits 8-11, +0x10c bit 28, +0x110 | draw sub-modes / offset x gen +0xfc (0xa956d8, C; G) | 0, 0, 0 | 0, 0, 0 mostly | same |
| +0x3c, +0x120..+0x12c, +0x13c | 0xa9af40 block, sort key, UV transform (C) | GU's common values | same | same |
The MHF units (mhffx2gu.model_effect_mode, 2026-11-11) clear +0x1a bit 0 and set +8 = 0, +0x10c = 0; blend = MHF's;
MHF's UV scroll = UV layer 0 (+0x134, mhffx2gu.uv_block).

**Nothing drawn when** (C unless marked): model path empty / unresolved; MRL or a material name missing, or an
effect-mode material of another class (ready check, the whole effect fails); move kind 5 without +0x70; scene mode
with frame >= mesh count (tests 18-20: frame 1 from cm123_041 entry 0 on our one-mesh models); alpha 0 from colour
A / the curve / the fade; scale 0. Effect mode with a frame that names no group draws mesh 0 (S).
GU corpus (11359 Model units): 564 scene mode, 10795 effect mode; cm123_041's scene-mode entries pick frames 1 / 2 /
4 of cm100_910 (5 meshes, groups 1 / 0 / 2 / 3 / 4). Check: `python3 weapons/magnet_spike/tools/effcheck.py ARC`
replays these conditions (0 problems on GU's w00 / w04 / w13 and on efl4u2gu's em089_00 / em090_00 / em091_00).

## Model transform, effect draw (static, 2026-11-11; C unless marked)
Row vectors throughout (MT: v' = v . M, translation in row 3; 0x1ebe8 = A . B, C). Per particle (0xa956d8 mode 5 /
0x1e -> 0xa6d3b4 -> 0xc90380 / 0xc90b50, which copies the matrix to the draw constants as is):
**world = v . S . R . G100**, translation row replaced by the particle position (particle +0x20).
- S = diag(particle +0xd0 x particle +0x40): unit +0x90 scale (value + r range, or the +0x132 curve) x size (+0x28, G
  for the +0x40 source).
- R = 0x321694(particle +0x60 rotation, order gen +0xe8 bits 16-19 = unit +0x100 bits 0-3; default 4 from 0xa59268).
  Radians. Order 0 = v . Rx . Ry . Rz = column Rz Ry Rx (MHF's particle order, below); order 4 = v . Rz . Rx . Ry =
  column Ry Rx Rz; 1-3, 5 decoded in 0x321694 too (not needed). Every MHF Model unit and the gun use order 0 (+0x100
  = 0x60). Rotation init 0xa6adac: +0xd0 (value + r range) -> particle +0x60 / +0x70, speeds +0xe8 -> +0xa0; gen
  +0x52 bit 3 (unit +0x1b) adds a random y, gen +0xec bit 11 (unit +4 bit 21) adds 0xa6a950's, gen +0xc1 bit 6
  mirrors y / z (all clear in ours).
- Unit +4 bit 18 (gen +0xec bit 13) swaps to R . S; gen +0x50 bit 17 (unit +0x1b bit 1) aligns to the emitter's motion
  instead; particle flag 0x80 with gen +0xe8 bits 24-27 != 6 (unit +0x100 bits 4-7) takes a billboard axis (switch
  in 0xa6d3b4): ours have +0x100 bits 4-7 = 6 and +4 = +0x1b = 0, so none applies.
- **G100** (gen +0x100, 0xa5a0c4 each frame) = the emitter's rotation rows (gen +0x18 matrix) x effect +0x1a0..+0x1a8 x
  effect +0x1b0 x gen +0xf8 (element +0x40, value + r range) x the slot scale (+0xe0..); identity rows when gen +0xec
  bit 12 (unit +4 bit 20 / 21). The translation row of G100 is dropped.
- Particle position (move kind 0, 0xa64a04): the emitter matrix x the spawn offset; kind 5: E (spawn + Rp curve(age))
  (gu-efl-move.md).
- **The emitter matrix** (effect slot 0x130 B, effect +0x1f4; 0x9be664 init, 0x9bea1c per frame) = slot local
  (rotation from the slot quaternion +0x90 or Euler, translation +0x80 = the PEL record offset) . J, with J = the
  owner's joint matrix: effect vt +0xec = 0x9c0020 -> owner vt +0x54; the hunter's = 0x27c40c: joint record +0x10
  of `owner +0x494 + 0xa0 x ids[joint]` (owner +0x498), the owner's own matrix (+0xb0) for joint 0xffff. Mode = slot
  +0x10c bits 16-19 (from the record): 3 = no owner, 2 = owner position with the local rotation, else the product
  (rows normalised, their lengths kept as the slot scale). Hence a PEL post on joint j with offset o draws
  v . S . R . (rows of T(o) R_rec J) at the particle position: **the model in the joint's frame, offset o in that
  frame**, as MHF's bone-attached draw (S: that joint record +0x10 is the world matrix, as ms_act.c fx_fixed uses it).
- Not traced: draw-time paths for mode 5 beyond the matrix (0xaef728, 0xbae520); colour, UV and blend: "Model look".
Check: `python3 weapons/magnet_spike/tools/fxplace.py` replays this on the built arc against MHF's math.

## Model look: UV layers, colour, material (static, 2026-11-11; C unless marked)
**UV layers.** Unit +0x134 lo16 = offset (from the unit) of a 0x40-B value block, UV layer 0: f32 (value, range)
pairs u +0x00, v +0x08, du +0x10, dv +0x18; +0x20 damping; +0x24..+0x2f 0 (all GU units); +0x30 / +0x34 offsets of u / v
curves (0 = none; header bits 27-29 == 3 set particle flag 0x10 = no sub-frame blend, 0xa6b824); +0x38 / +0x3c
"curve adds to the previous value" flags. +0x136 = offset of extra layers (0x30 B each, count unit +0x13b & 0xf when
+0x138 bits 24-27 != 0; +0x138 bits 24-25 / 26-27 -> particle +0x100 bits 8-9 / 10-11).
- Bind 0xa9499c: particle + 0x20 x (n extra + 1) bytes when +0x134 lo16 != 0; gen +0xd4 = their offset.
- Init 0xa99f40 -> 0xa6b824: layer {u, v (two buffers each, particle +0xf bit 0), du, dv, flags, damping} = value
  + r x range; du != 0 -> particle +0x10 flag 0x800, dv -> 0x1000 (curves: 0x20000000 / 0x40000000).
- Update 0xa9a280 -> 0xa9ada0 -> 0xa6bc0c, every frame: u(new) = u(old) + du, du *= damping (curve: u = curve(age)
  [+ u(old)]); both buffers beyond +-2 -> -+2. Extra layers alike (flags in their +0x18).
- Draw 0xa956d8 mode 5: particle +0xcc == 0 and particle +0xfc lo16 == 0 -> no UV block (slot count 0); else
  0xcaf17c(sub-frame, particle, block, EAN record +0x14) fills up to 4 slots (u, v) + count at +0x20: slot 0 = the EAN
  frame offset (none: 0) + layer 0 blended by the sub-frame, wrapped to (-1, 1); slots 1.. the extra layers.
- 0xc90b50 (0xc914dc): slot 0 -> CBMaterial +0x2c / +0x3c, slot 1 -> +0x4c / +0x5c, slot 2 -> +0x6c / +0x7c = the
  translations of fUVTransform / 2 / 3 (2 x 4 rows at floats 8 / 16 / 24; mfx layout, mrl.cb_layout). efx_blend selects
  FUVTransformPrimary = FUVTransformOffset and FUVAlbedoMap = FUVPrimary (S: by name, the albedo UV + that offset).
- GU's own (player arcs): 2206 / 4708 effect-mode Model units carry a value block (du / dv 0.005..0.1 per frame,
  damping 0.6..1.0; curves in 44); none uses +0x136 / +0x138 layers. Converted: mhffx2gu.uv_block (MHF modes 1-3).
**Colour.** Particle colour +0xf0 / +0xf4 (RGBA u32, byte 0 = R; double-buffered, blended by gen +0x9c / 256), alpha x
the draw's alpha argument >> 8; alpha 0 = not drawn. 0xc90b50: alpha / 255 -> 0x886bb4 (context +0x17c, a per-draw
constant; S: multiplies the output alpha). The material's FEmission feature (0xb0ffd4 = its feature word) ==
FEmissionConstantEflEmu: CBMaterial fDiffuseColor (floats 0..2) = RGB / 255 x particle +0x50 / 256 when particle +0x1c &
0x3200001 == 0, else RGB / 255 and a second constant (context +0x1704) = particle +0x50 / 256 (0xc913a8..0xc914d8);
fTransparency (float 3) stays the material's 1.0. Particle +0x50 = int(unit +0x20 x 256) (0xa6a2a4): unit +0x20 is an
intensity (GU effect-mode units: 2.0 in 2691, 1.0 in 1588, 4.0 in 429 of 4708; ours 1.0).
**Material** (efx_blend = em024 cm101_000, class 0x5fb0ebe4; feature words = (jamcrc(variant) & 0xfffff) << 12 |
record, mrl_build.state_word, names from AppShaderPackage.mfx): FDiffuse = FDiffuseVertexColorMD, FEmission =
FEmissionConstantEflEmu, FTransparency = FTransparencyAlpha, FAlbedo = FAlbedoMap (tAlbedoMap), FUVTransformPrimary =
FUVTransformOffset, FLighting / FBRDF / FBump / FReflect / FShininess / FOcclusion / FDistortion / FVertexDisplacement
= the feature's own (default) name, FSpecular = FSpecularMap (no map), FFresnel = FFresnelSchlick; states BSBlendAlpha
(replaced per unit, above), DSZTestWrite, RSMeshCN. S (names only, the shader code is not read): unlit EFL emulation
(texture x vertex colour x fDiffuseColor as emission), depth test and write on, no back-face cull. Every GU
effect-mode model material has DSZTestWrite (4708 / 4708) and RSMeshCN in 4453. G: whether "MD" doubles the vertex
colour (Capcom's 0x7f neutral, mhfmodel.NEUTRAL): GU's 7f-vertex models come with unit +0x20 = 1.0 (948) as often as
2.0 (1264), so the corpus does not settle it.
Check: `python3 weapons/magnet_spike/tools/fxlook.py` renders MHF's and GU's draw of the built units side by side.

## Limits and budgets (static, 2026-11-11; C unless marked)
What an effect consumes from the post to the draw, and what happens at a limit. Tool: `python3
weapons/magnet_spike/tools/fxbudget.py [--log TEST.log]` (corpus distributions, ours placed in them, peak per action);
effcheck.py fails a build whose EFL is above GU's own maximum in entries, particle slots or work block.
| piece | size / count | from | at the limit |
|---|---|---|---|
| proxy uMHProofEffect (the post handle) | 0x350 B; live count in the global MAIN 0x1850a50 (ctor 0x41f10 +1, dtor 0x4201c -1) | 0x41cf4 -> its DTI's allocator | **144** (0x41558, called by the post 0x40978 before the proxy exists): post category (extra +8) 2 / 3 end one live proxy from the manager's buckets (+0x74.. bit masks, slots +0x770; vt +0x40) and go on; any other category is refused, handle 0. The module posts with extra 0 = category 0 |
| effect object | 0x500 B (0x4260c -> 0x43b70) | its DTI's allocator | null: no effect (G: not followed further) |
| generator | 0x1d0 B per kept entry (0x250 node); one per entry the record keeps (below) | the class's operator new (0xa7b084, 0xa9490c, ...: `0x7aa47c(DTI)` vt +0x20) | null -> effect +0xf0 0x2000000, whole effect (0x9bdc68); init vt +0x18 failing -> 0x4000000 |
| work block | slots x 0x130 + the generators' gen +0x20 (+ 0x60 + table 0x1671700[res +0x7c bits 4-7] with effect +0x1d0) | uEffect's DTI allocator (0x9be320) | null -> 0x2000000, whole effect |
| slot map | n2 x 4 B (EFL header n2) | 0xb91f44 | null -> 0x4000000 |
| slot extra | 0x20 / 0x30 / 0x50 B per slot by element fields (0xaeb230) | a DTI allocator | null -> 0x2000000 (0x9be664) |
| scene-mode model unit | 0x500 B per live particle (0xa955b0 -> 0xc6b66c), registered in sUnit (0xc08100) | its DTI allocator | null: that particle not shown (0xa955b0 returns 0) |
| draw | 0xaef728 copies the unit's 0x30-B draw block (unit +0x3e) and skips the draw when its byte 0 bit 1 is set and a global +0x158 is 0; 0xbae520 picks the draw context (+0x2c + 4 x layer) and sets its layer / priority | - | no count, no per-frame list cap found on these paths |
**Allocators.** An MT class allocates from `table[(DTI +0x18 >> 23) & 0x3f]` (0x7aa47c, table MAIN 0x18a62e8). The index
comes from a name map built at boot (0x15004c: 303 calls of 0x7aa394(name, index); 0x7aa588 walks each DTI's
parents to the first mapped name): cParticleManager (parent of every cParticleGenerator*) and uBaseEffect (parent
of uEffect, uProofEffect, uMHProofEffect) -> 21, cUnit -> 15. 0x151ccc creates the heaps: 15 'Unit' 120 MiB, 16
Area 1 MiB, 3 Array/String 16 MiB, 4 Collision 4 MiB, 18 Physics 14 MiB, 13 Resource 500 MiB, 17 Sound 20 MiB, NVN
texture / buffer / shader 848 / 200 / 100 MiB, and aliases 8 / 0x14 / **0x15** / 0x16 to the Unit heap. So every
effect piece above comes from the one 120 MiB Unit heap that every unit of the game shares: **no per-class
generator pool exists**, and a failure needs that heap full (G: its fill in a quest is not known statically).
**Work block per generator** (0xa5b658, from the class bind = vtable slot 6): gen +0x20 = N x (round16(particle) +
round16(extra) + move size) + round16(N x emit size), N = element +0xc lo16 (gen +0xd0, 0xa58fa8; x 5 / 16 or x 9 / 16
when element +8 bit 2 is clear and gen +0x50 >> 28 is 1 / 0 with element +0x48 counts >= 2 / 4: G which applies).
Particle bytes (bind arguments): Billboard / LiteBillboard / SizeBillboard 176, Model 288 (+ 0x20 x UV layers),
Polygon 256, Polyline 208, BillboardStrip 192, Line 128, Texline 160, PrimModel 336, Trail 208 (fxbudget.PSIZE).
Move size by kind (u16 table 0x1671700) 64 / 112 / 96 / 144 / 112 / 144 / 128 / 64 / 160 for kinds 0-8; emit size (u32
table 0x1671730, index emit high nibble ^ 8) 16 for the GU types 1 / 2 / 5.
**Record mask (C, 2026-11-11).** Entry i of an EFL is built by a post only when element +0 & mask0 != 0 and element
+4 & mask1 != 0 (0x9be8c4 = effect vt +0xdc, asked per entry by 0x9bdc68; also its runtime record +4 must share no
bit with effect +0x116 | a global +0x228, G meaning). The chain: the PEL list record in memory = the file record's
160-B body at +0x20 (id body +0x30 = record +0x50, the field 0x3267d0 matches); the proxy start step 0x329908 copies
it field by field with 0x31cc6c -> 0x31c3a8 into proxy +0x80 (field 2: body +0x30 -> +0x40; **field 0x12: body +0x48
-> +0x58, field 0x13: body +0x4c -> +0x5c**), i.e. proxy +0xd8 / +0xdc; 0x32aa44 (proxy vt +0x80) loads them (its
record pointer = proxy +0x50) and calls 0x9bd5a0, which stores them at effect +0x1c8 / +0x1cc = mask0 / mask1. An
effect keeping no entry builds no generator: 0x9bdc68 returns 0, +0xf0 |= 0x1000000 (not 0x2000000), nothing runs.
GU's pattern (weapon-arc PELs, all lists, 1391 records naming an EFL of their arc): masks of one bit 1251, several
bits 54, all ones 86; element +0 one bit in 4745 / 5695 entries (two bits 948), several entries share a bit in 378 /
433 EFLs: **a bit = a group of entries, one record per group**. Tolerated by GU: entries no record of the arc keeps
(91 EFLs: posted by code with other masks), overlapping masks (22), one record keeping nothing. efl4u2gu (monster
ports) copies 4U's element blocks (its group bits) and writes mask = 1 << k from 4U's post data (efl4u2gu.py,
`mask = 1 << r['k']`): the same pattern, not our defect; em089-091 hold 5 records that keep nothing
(m19a03_002 mask 4; qe013_003 mask -1 on element +0 = 0 entries; em024_020 mask 2: not followed, G whether they
matter). **Ours until 2026-11-11:** every MHF entry had the template's element +0 = 1 and the records entry-index
bits (1 << i): 169 records built their whole EFL at the first group's offset, 319 built nothing. Now
(mhffx2gu.Builder.efl, GROUP_BITS): element +0 = 1 << group index in its EFL, the group's record mask = that bit
(msgun: bit 0, mask 1); more than 32 groups in one EFL stops the build. effcheck.check_masks fails a build whose
record keeps no entry, keeps more than one group, or leaves an entry no posted record keeps (0 on GU's w00 / w04 /
w13 and em089 for their own records: the rule runs on `\ms_` EFLs only).

**Corpus (fxbudget.py, 1650 unique GU EFLs; max = GU's maximum):** entries per EFL p50 6 / p99 49 / max 122 (weapon
arcs max 72); Model units p50 5 / max 112 (weapon arcs 51); particle slots per entry (element +0xc) p90 80 / max 1000;
sum per EFL max 3010; UV layers per Model unit max 2; work block per EFL p50 5.8 KB / p99 88 KB / max 341 KB (weapon
arcs 194 KB). efl4u2gu's in-game em089-091 reach 84 entries, 56 Model units, 341 KB. GU's busiest weapon motion
(PSL slot): w08 slot 190, 4 records, 86 generators, 223 KB; w01 slot 130, 32 records, 200 generators, 92 KB.
**Ours (w05.arc, 86 ms_* EFLs):** entries max 32, Model units max 20 (ms_fc5_038), particle slots 1 per entry (sum
max 32), UV layers <= 1, work block max 11.7 KB (ms_fc5_03b, above 76 % of GU's EFLs): **under GU's maximum on every
axis**. The draw mode does not enter the bind, the work block or the slot init (0xa9499c / 0xa58fa8 / 0x9be320 /
0xaeb230 read no +0x1a bit): tests 20 (scene) and 21 (effect) built the same sizes (the 2026-11-05 build, test-20
state: 345 KB over all EFLs; now 350 KB, the difference = the UV layers added after test 21). Scene mode adds one
0x500-B model unit per live particle (<= 20 per effect here). Peak alive in test 21 (fxbudget --log): 10 proxies,
55 generators, 22 KB (action 107); 20 Model generators (Guard Counter, 57); against 144 proxies and the 120 MiB heap.
So no capacity explains the test-21 loss (C for the mechanism, S for the heap state). Records after the mask fix
(above): 82 keep their whole (one-group) EFL, 406 one group of several, 0 none (before: 169 all, 319 none); the
peak table keeps its numbers (the first record had built every entry) without the 4-6 empty proxies per action.
fxplace (records placed by the mask): before 80 / 253 Model units over 1 cm, max 565.7 cm (fc5:3a; fc5:4f / 38 / 39
about 450 cm); after 19 / 253, max 1.97 cm (the pre-existing MHF-sum residuals).

## Main-agent decode (2026-11-04, C unless marked)
- **Emit block = particle life** (0xaed0d0, called per new particle by 0xa5ca24 for emit-type high nibble 1 / 2):
  three u32 = (u16 frames, u16 random range) each: +0 fade-in A, +4 hold B (or a curve at the block +
  (word3 lo16 >> 1)), +8 fade-out C; word 3 lo16 is kept. Per particle frames = value + rand % (range + 1).
  Life = A + B + C frames; the generator fades alpha (high nibble masks 0xaa) or colour (0x154) by the phase
  (x 256 at 0xa7d870 / 0xa7de94). The effect-volume setting (owner +0x11a & 0xf: 0 -> / 4, 1 -> / 2, 2 -> as
  is) shortens A and C. Corpus: cm300_012 (0, 20 +- 5, 0) vs its colour curve ending at 25; em072_00_012
  (0, 60, 0) vs 60; em033_00_002 (0, 10, 40) vs 51 (S).
- **Emission** (generator update 0xa5a48c, state byte gen +0x47): emit type low nibble 1 -> 0xa5a900 = ONE
  particle, once, then the generator finishes (vt +0x2c); 2 -> 0xa5abc4 = bursts: count = element +0x48
  (u16 + random) or the curve at element +0xb4 (lo16), repeats from element +0x4c (u16 + random) -> gen
  +0x1aa, interval / end via 0xa5c464 / 0xa5c7dc (not read). The start wait of both (gen +0xe0 hi16) =
  owner +0x1fc (f32) x (gen +0x18) +0x11c: set by the posting effect, not by the unit.
- **Particle age** = particle +0x14, +1 per update (move kind 2 step 0xa631fc); curves read it by default.
- **Curve header** (0xaf7958 / 0xaed74c): u32 = count (byte 0) | 2 << 8 | flags << 24; byte 3 & 7 = time
  source (0 particle age, 1 generator time gen +0x88, 2 / 3 owner +0x10c, 4 a global); bit 30 = wrap (loop);
  bits 27-29 = interpolation (jump table at 0xaf7a80, not read). Keys {u32 time, f32 value, f32 random
  range}: value + range x the particle's random draw. So the old "prop 0 colour / 1 alpha / 0x40 scale"
  reading was the flags byte; the curve's role comes from the slot that points to it (+0x3a scale, +0x42
  colour, +0x44 UV frame, +0x198 rotation).
- **Size** (0xa6a2d0 / 0xa6a434): no scale curve (unit +0x38 hi16 = +0x3a == 0): size = +0x28 + r x +0x2c,
  rate = +0x30 + r x +0x34 (non-zero: particle flag 0x100), each frame size += rate, rate x= unit +0x1c;
  with the curve: size = curve(age) (particle flag 0x100000).
- **UV / time state** (0xa69d00 -> particle +0x60): flags = unit +0x50 lo16 (random flips), EAN entry = +0x50
  byte 2 + rand % (byte 3 + 1), start frame = +0x54 lo16 + rand % (hi16 + 1) (or the frame curve +0x44),
  speed +0x58; 0xa6a004 steps it; with flag 8 the particle dies at the animation end.
- **Spawn transform** (element +0xbe sub-block, 0xaec900): floats [0..2] -> gen +0x60 (offset), [4..6] -> +0x70.

## Template
Simplest GU Billboard found (1 entry, unit 0x1a0 B, no curves, move kind 2): `/nativeNX/arc/enemy/em021_00.arc`,
`effect\em\em021\em021_00_007`, entry 0 (same shape: em063_00 `effect\em\em063\em063_00_010`, em065_00
`effect\em\em065\em065_00_004`). `python3 weapons/magnet_spike/tools/efldump.py /nativeNX/arc/enemy/em021_00.arc
'effect\em\em021\em021_00_007'`.
