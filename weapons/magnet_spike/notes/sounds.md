# Magnet Spike sounds: MHF side, GU side, conversion (step S1, 2026-11-11; static, nothing built)

C = confirmed in code / data, S = strong, G = guess. MHF addresses are mhfo-hd.dll (ZZ), GU addresses main32.elf
(1.4). Tool: `tools/mhfsnd.py` (MHF banks -> lists / WAVs; WAVs only outside git). No game audio in the repo.

## 1. MHF: how a sound is played (C unless marked)

- **Bank slots.** 16 slots, per slot a request table (0x1e3cbd68[slot], the bank's 'dbsT') and an HD (0x1e3c9920[slot]).
  Loaders: 0x114dcc30 (one MOMO -> slot ESI) and 0x114dcd00 / 0x114dd750 (several MOMOs merged into one HD: a
  component's program k stays program k, a clash aborts; samples / waves renumbered, BD offsets added).
  - slot 11 + k = the **weapon-type bank** `dat/sound/we%02d.snd` (0x10b46540 from 0x10b47d70) for the k-th
    distinct weapon type among the hunters (list 0x1dc0b228, max 4; 0x10b431c0 maps a type to its slot; 9 = a
    lobby case). Magnet Spike = type 13 -> **we13.snd** (220 KB).
  - slot 2 + hunter index (P+0xc) = the **per-hunter bank** (0x1089ad40 -> 0x114dcdd0): the weapon model's
    `sound\w%c%03d.snd` (0x108e05e0: letter = id / 1000 + 'e', so Magnet Spike models wkNNN; from the extend
    archive, dump/mhf/weapon/wkNNN/wkNNN.snd) or `o_we%04d.snd`, merged with a common bank chosen by 0x10b42ad0
    (table 0x11879468: common00 / common01 / commonCH / lobby ...). S: in quests commonCH (program 7; common00 /
    01 use program 0 and would clash with the model's program 0).
  - slots 0, 1, 3, 6, 7, 8: system / stage / ground banks (footsteps: slot 7, 0x1091e5d0).
- **Play.** 0x114dd030(ecx = request, edx = position, slot, ?, category, flag): 3-D. The category row
  (DAT_1e77dcc4+0x548, 20 B: f32 near, f32 far, u16 curve index x2, s32 request offset, ...) gives a distance
  attenuation by a 17-point curve, pan / front-back flags from the listener; the request index gets the row's offset
  added (runtime table, G: 0 for category 1). 0x114dcf90 / 0x114dc9e0 = the 2-D play: random pitch +- entry +0x18
  and random volume +- entry +0x1a. 0x10b42ef0 (4431 callers) = 2-D wrapper.
- **Wrappers used by hunter code:**
  - 0x10b43370(P = eax, request = arg, position = edi, category = esi): the **weapon-type bank** (slot 11 + k of
    P's weapon type), only for the local hunter (P+0x7f8 == the local id). Every Magnet Spike call passes category 1.
    (effect-posts.md / phase3.md call 0x10b43370 a "rumble preset": wrong, it is this sound call.)
  - 0x10b43770(P = esi, request = eax, position, category): the **per-hunter bank** (slot 2 + P+0xc).
  - 0x1091e1b0: system bank (slot 1) at a motion frame.
- **Motion keys kind 0 / 1 are not sounds.** Kind 1 (0x1099a7b0 -> 0x114252b0) starts a particle task (update
  0x11422270: DAT_119f3840[a] particles with random spread, no sound call; C), kind 0 (0x1099a790 -> 0x11413d70)
  another effect task. The 446 Magnet Spike kind-1 keys (a 0 / 3 / 4 / 20 on bones 5 / 8, a 7 / 8 / 10 / 12 / 15 on
  no bone) are dust / particles (S: bones 5 / 8 = the feet). effect-posts.md's "0 / 1 = sounds (S)" is wrong.
- The frame events (handler table 0x11926b40) start no sound except event 26 (below).

## 2. MHF: the Magnet Spike's sounds

### Code-played, weapon-type bank we13.snd (C: call site, request; wave = mhfsnd resolve)
All at category 1, 3-D at the given point, local hunter only. Wave lengths at 48 kHz.

| request | where (MHF) | event | wave (s) |
|---|---|---|---|
| 6 | 0x10338ba2, event 26 handler 0x10338b00 (action 34, P+0x15 == 1) | Triple Strike charge starts (with the charge aura fc6:12) | w1 (1.30) |
| 7 | 0x10333da0 (0x103339d0, action 34) | Triple Strike charge level 0 -> 1 (with fc6:11, MS task kind 4) | w2 (1.68) |
| 13 | 0x10336430 (0x103362e0, after a motion effect key fc5 3 / 4 / 0x46 / 0x47 on bone 14 or 18, unless MS flag 0x40000) | attraction / guard task posts (fc5:3 = the attraction, 0x46 / 0x47 guard) | w15 (1.00) |
| 14 | 0x103343ca (motion 1034 f32) | Guard Counter success (with fc5:14) | w13 (1.63) |
| 5 | 0x10335276 (motion 1034, same tick as 14, S) and MS task 0x1004d810 (0x1004e758 / 0x1004ee80) | Guard Counter; Magnetic Shock / whiff tasks (kinds 0xf / 0x10, t0) | w10 (1.30) |
| 23 | 0x10335276 (motion 1082 f60, Charged Strike, with fc5:14) and 0x1004e74b / 0x1004ee73 | Charged Strike hit; Magnetic Shock tasks (with 5) | w14 (2.00) |
| 17 | 0x10334f8c (1012 f48), 0x1033527c (1013 f48), 0x10336094 (1410 f34) | Magnetic Assault (Leap) Cutting / Impact landing, Guard Assault (with fc5:45 / 0x3a) | w29 (1.70) |
| 26 | 0x103359ad (motion 1488 f114) | Pin Finisher, first beat | w22 (3.03) |
| 27 | 0x10335a69 (motion 1488 f184, with fc5:5d) | Pin Finisher, final blow | w23 (2.40) |
| 36 | 0x1032ee71 (0x1032e4b0, group 0 action 0 while 0x10033670 says so) | not identified (G: a mode / state change) | w21 (1.49) |
| 12 | 0x1004ddda (MS task kind 0xa, guard with < 2 guard hits) | guarded hit | w12 (1.47) |
| 24 | 0x101bc14f / 0x101bdb12 (pin code 0x101bc000..) | pin (S: pin start / hold) | w24 (2.63) |
| 9 | 0x101e9013 (0x101e8de0) | special (S: shot / marker) | w3 (0.70) |
| 18, 19 | 0x101e9e3f / 0x101e9d05 (special #3 update 0x101e9b70), 19 also 0x101eb4f8 | pin special | w27 (1.41), w25 (2.20) |

we13 holds 37 requests (programs 3 and 4, 31 waves, 46.5 s): request 0 (no tone) and 16 (program 0, volume 0) are
dummies; requests 29-35 (program 3, three volume steps each, random pitch 1000 / 3000) and the rest have no caller
found in the Magnet Spike code (S: shared hunter code may use them, e.g. draw / sheathe: not traced).

### Weapon-model banks wkNNN.snd (per-hunter bank) (D unless marked)
- Each has ONE program (0): requests 0-15 = notes 60-75 -> 6-8 real waves (wave 0 of the 16-tone banks is a
  91-sample silent dummy, tones 60 / 69 / 72-75 point at it). Requests 16-31 (program 0, notes 76-91) and 32-47
  (program 1) have no tone in the model bank (C for the HD content; S: a class template, silent).
- Requests 0-15: volume 100 (0 for request 0), random pitch 4000 (+0x18, units G), a 11 b 30 c 1 d 4.
- The used models: wk400 (test weapon), 414, 415, 595, 606 (16 tones, 8 waves, 9.0-12.4 s), wk404 / wk407
  (12 tones, 6 waves, 4.4 s; **the two files are byte-identical**).
- **Who plays them for the Magnet Spike: not found.** No call of 0x10b43770 (or 0x114dd030 with slot 2 + k) in the MS
  code range 0x1032ae00..0x1033e000; the callers found are shared hunter code (0x1091ebe0, 0x109d80c0.., 0x10a4ccb0..,
  0x1099b8d0 = per-motion hard-coded shared actions). Candidates still open: the attack object (event 3 -> 0x101e78e0
  -> 0x101e7980 / 0x101e7a20 / 0x111d4e20 / 0x111d60c0) for swing / hit sounds (mhfsdt attack words [14] = 0x201 /
  0x501 and [17] = 0x606 per attack kind: G), and draw / sheathe.
- Totals over we13 + the 7 models: **77 distinct waves, 101.8 s** at 48 kHz.

### Playback parameters (dbsT, HD)
Gain chain request vol x tone vol x sample vol x program vol (0-127 each; e.g. we13 request 7 = 127 / 95 / 127 / 115;
law G: linear / 127). Random pitch +0x18 (C that it is a +- range; unit G), random volume +0x1a (0 in every MS
request). No looping wave (Vagi a / b / c = 0 in every MS bank, D). Stops: not traced (G: one-shots, no stop call
found next to the MS call sites).

## 3. MHF formats (D; tools/mhfsnd.py docstring has the byte layout)
MOMO v3 container: JPK-packed HD ('Head' / 'Prog' / 'Smpl' / 'Vagi', PS2-HD-like), JPK-packed request table
'dbsT' (32-B entries: program, note, volume, pan, random pitch / volume ranges) and a raw BD that is **one Ogg
Vorbis stream, mono 48000 Hz**, all waves back to back 1441 samples apart (Vagi: start = PCM byte offset, length in
samples). The masters are band-limited: no energy above 16 kHz in any MS wave (D), peaks normalised to 0 dBFS.
Note == sample note in every MS tone (played at the native rate: no transposition). Decoding = ffmpeg (Vorbis).

## 4. GU side
- **Player request slots** (C, 0x27b928, the player's sound object at P + 0x447 * 4): slot 0 = file 0x92b, slot 1 =
  file 0x92c + class (iVar4 == 1 branch), slots 2 / 3 / 4 = resolver 0x4ea0dc(class, equipment, k = 1 / 2 / 0),
  installed with 0x4d5e30(obj, resource, slot) after the getter 0x152960(file ID, type); slots 5-8 from the
  armour, slot 9+ others. The resolver's class jump table (0x4ea380) has "no file" for class 5 -> hook
  `ms_snd_file` (ms_class.c) asks as class 0, so slot 2 = GS's snd_wp_two001 (k 1, by mSrqrNo), slot 4 =
  snd_wp_two_bcom (k 0, by mSndMaterial), slot 3 = k 2 (S: GS's Hunter Arts bank; msbuild leaves two_arts out).
  Logs: `weapon sound request k 1 / 2 / 0 (lr 4ea010)` once per load (test logs 10-21).
- **Motion sequence** sound\call\pl\pl_wp05 (MSS v 0x20131015, msfx.py): records 5000 + motion slot, events at
  frames, op 0x66 = weapon sound {a: 1 -> slot 2, 0 -> slot 4; request id; joint; position mode; random; alt
  request}. PTS sound\pts\pl\w05_000 / _800 = effect-tied sounds (GS's flash sound plays with the flashes).
- **Files** (C, GU RomFS): arc/weapon/wNN/snd/NNN.arc = the model's waves + SBKR v4 + SRQR v5 (GS 001: 7 waves at
  8-16 kHz, 11 requests, 66.5 KB); snd/mat_b.arc / mat_i.arc = the class's common bank (GS: 25 waves, most at
  **48000 Hz**, requests 0..289, 684 KB). Over GU's 1581 weapon snd arcs: 12844 waves, 8000-24000 Hz (one 48000),
  longest 3.66 s, none looping, arcs up to 195 KB. Codec: rSoundSourceADPCM v2 = mono Nintendo DSP-ADPCM
  (tools/snd4u2gu.py has the header, the bank / request layouts and the decoder; wsnd4u2gu.py the class-template
  rules). Opus is for streams (BGM) only.
- **Hit sounds** (C from wsnd4u2gu): the mat_b / mat_i bank by the weapon record's mSndMaterial (bone / iron), its
  hit requests (two_hit_bone, two_hit_sp, ...); which request per hit kind: not traced here.
- **Limits:** Sound heap 20 MiB (gu-efl-units.md); keep w05.arc under ~20 MB unpacked.
- **No DSP-ADPCM encoder in the repo** (snd4u2gu / wsnd4u2gu copy 4U's DSP data bit for bit; snd_bgm encodes Opus).

## 5. Conversion round trip (scratch, stepS/roundtrip.py; 2026-11-11)
MHF wave (mhfsnd) -> new numpy DSP-ADPCM encoder (8 coefficient pairs by weighted k-means over per-frame 2nd-order
predictors, then per frame an exhaustive search over 8 pairs x 13 shifts with the decoder's exact arithmetic) ->
snd4u2gu.gu_wave (GU v2 header) -> snd4u2gu.gu_wave_parse + dsp_decode -> compare. Sample counts equal in every case.

| sound | rate | GU wave | codec SNR | peak error |
|---|---|---|---|---|
| wk404 w03 (0.46 s, whoosh-like, trigger unknown) | 48000 | 12.9 KB | 33.6 dB | 1638 (-26 dBFS) |
| same | 32000 | 8.6 KB | 28.7 dB | 3564 (-19 dBFS) |
| we13 request 13 (attraction keys, 1.00 s) | 48000 | 27.8 KB | 28.7 dB | 3191 (-20 dBFS) |
| same | 32000 | 18.6 KB | 24.4 dB | 3264 (-20 dBFS) |
| we13 request 26 (Pin Finisher f114, 3.03 s) | 48000 | 83.6 KB | 35.9 dB | 1795 (-25 dBFS) |
| same | 32000 | 55.7 KB | 31.8 dB | 2911 (-21 dBFS) |

Encoder check: re-encoding Capcom's own GU waves (decoded two_whoosh_b / two_flash / two_layer_whoosh_fast) gives
47.7 / 36.5 / 46.6 dB, so the encoder is usable but not optimal; a port of the reference coefficient search
(DSPADPCM / VGAudio style) should gain a few dB. 48 kHz keeps the most (sizes ~27.5 KB/s); 32 kHz loses nothing in
band (no content above 16 kHz) but costs ~4-5 dB SNR at the same 4.57 bits per sample.

## 6. Build plan (next step, not executed)
1. Encoder: move roundtrip.dsp_encode into a shared tool (tools/dspadpcm.py, core: the maintainer's call), with a
   selftest on Capcom waves (re-encode SNR) and on snd4u2gu.dsp_decode bit-exactness.
2. Weapon-type bank -> GU class common bank: arc/weapon/w05/snd/mat_b.arc (and mat_i.arc, same content) = the 29
   real we13 waves (~1.27 MB at 48 kHz), SBKR + SRQR built from GS's bcom as the class template (wsnd4u2gu rules),
   request ids = MHF's we13 request numbers + a fixed base (no clash with GU's 0..289), volumes from MHF's gain chain.
3. Model banks: arc/weapon/w05/snd/00N.arc per forged model (msbuild MODELS 1-7): the wkNNN waves (6-8, 120-340 KB
   at 48 kHz each; wk404 = wk407 share one arc content), SBKR + SRQR from GS's 001 template, request = MHF request
   0-15. Total all banks ~2.9 MB at 48 kHz (~1.9 MB at 32 kHz).
4. Module: ms_snd_file returns OUR file IDs for class 5 (new IDs in allocations.toml, the file-ID table extended as
   the monster ports do) instead of GS's: a GS hunter in the same session would otherwise share the paths.
5. ms_act.c: at each MHF call site of section 2 (same action / motion / frame / step), post the request on slot 4
   at the hunter point (GU's sound-at-position / on-object calls, porting-guide table); event 26 / charge level as
   the module already tracks them; request 13 next to the module's fc5 3 / 0x46 / 0x47 posts on joints 14 / 18.
6. pl_wp05: drop the GS stand-in whooshes only once the MHF model-bank trigger is traced (open item 1); until then
   keep them or leave swings silent (the maintainer's call).
7. Deviations that stay: GU's 3-D attenuation / pan instead of MHF's category curve; MHF's random pitch (+0x18)
   unless a GU request word does the same (to check in SRQR); GU's voice limits.
8. In-game checks (Xbox letters, the port's map in phase3.md "inputs": Y = tri, B = circle, A = special, X = evade,
   RB = R1, RB + RT = Guard Counter, RT = aim): Triple Strike in Impact (B, B, hold B): charge-start sound, then the
   level-up sound with the cue; Guard Counter (RB + RT into a monster attack): its sound at the counter; a guarded
   hit; Magnetic Assault (leap) and Guard Assault: the landing sound; mark a monster (RT + A), then RT + Y 14-40 m
   away: the pull sound with the attraction effect; Pin Finisher: two beats; Magnetic Shock: its sound. The log
   shows the request posts (one line per post, to add); the tester only reports what plays. Then a second hunter
   with a Great Sword (two local Ryujinx over LDN) to confirm GS keeps its own sounds.

## 7. Open questions
1. What plays the weapon-model bank requests 0-15 for the Magnet Spike (swing, hit, draw / sheathe)? Next:
   0x101e7980 / 0x101e7a20 / 0x111d4e20 / 0x111d60c0 (attack object) and the shared draw / sheathe code.
2. The category table (DAT_1e77dcc4+0x548) contents: runtime data; its file is not identified (request offset and
   near / far for category 1).
3. Units of the random pitch (+0x18: 1000 / 3000 / 4000) and the volume law.
4. Request 36's event (0x1032e4b0, group 0 action 0); the shared-code callers of we13 requests 0-4, 8, 10, 11,
   15, 20-22, 25, 28-35.
5. GU: which SRQR words carry random pitch / priority, and GU's request id per hit kind in the bcom bank.

## Decisions (the maintainer, 2026-11-11)
- Sample rate: 48 kHz (MHF's own).
- One sound bank per weapon model, as MHF (byte-identical models share one); the weapon-type bank we13 is shared.
- The branch takes main first (merge, no rebase) so the sound file IDs come from the current allocations.toml.
- Not decided here: the encoder's place (plan: tools/dspadpcm.py, shared) and the swings until the model-bank
  triggers are traced (plan: the GS stand-in whooshes stay until then, listed as a deviation).
- Found by this study, to fix with the sound build: the module shakes the camera (MS_SHAKE) where MHF's event calls
  0x10b43370, which plays a weapon-type-bank request, not a rumble preset.
