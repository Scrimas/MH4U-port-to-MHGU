/* em057_01_mv_f.c: Stygian Zinogre, ported 4U uEm048 handlers, batch F (the GU-PARAMS != rows of four 4U handlers GU
 * kept only in part: the roar 1/39 1/42 1/43, the lie-down wait 1/40, the stand-up 1/41, the charge-up 7/113 7/115).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case (GU 1/39 1/40 1/41 1/42 1/43 7/115: no case, end at once; GU
 * 7/113 = efb5f0(0): 4U's frame table with GU shell requests through efb884, but no ring rows, no sound and attack
 * index 32 for variant 1). Each handler is a literal translation of the whole 4U function named in its comment (every
 * value of its r1; MH4U v1.1, dump/mh4u.asm), in 4U call order with 4U frame / timer / angle values; em==49 branches
 * take the Stygian side (only 0x84dd44 tests the em byte: 0x84dfc8 uShell044 subtype 3 (em 48 / 114: 1), 0x84e2b0
 * attack index 53 (em 48 / 114: 32); phase1-variant-map.md 1B / 1C). Verdicts: notes/phase2-actions.md 2.
 * C = confirmed in code, S = strong, G = guess.
 * Parameters (C, case.py 4u 49 and the 4U stubs): cat-1 dispatcher 0x852ec0, table 0x852ee8: 1/39 1/42 1/43 ->
 * 0x853690 0x8536cc 0x8536e0 = 0x847274(r1 = 3 / 4 / 5); 1/40 -> 0x8536a4 = 0x847a40(1); 1/41 -> 0x8536b8 =
 * 0x847bdc(1); r2 = 1 (the category), unused. KEEP, not registered: 1/9 1/38 (0x85367c) 1/34 (0x85362c) 1/37
 * (0x853668) = 0x847274(0 / 1 / 2) on GU ef45e0, 1/35 (0x853640) = 0x847a40(0) on GU ef4c74, 1/36 (0x853654) =
 * 0x847bdc(0) on GU ef4fd4(76). Cat-7 sub-dispatcher 0x851494, table 0x8514ac: 7/113 7/115 -> 0x852088 / 0x8520a0 =
 * 0x84dd44(1 / 3), r2 = 7 unused; 7/94 7/114 = r1 0 / 2 (0x851efc / 0x852094), unreachable (phase2 1.2). No handler
 * reads r2, r3 or [sp]; none tests the controller byte W+0x1d9 (C).
 *
 * 4U -> GU, beyond the batch A-E lists ("site" = GU's look-alike handler does the same call at the same place: ef45e0
 * for 0x847274, ef4c74 for 0x847a40, ef4fd4's 1/36 case ef5540 for 0x847bdc, efb5f0 for 0x84dd44):
 * - 0x922cd8 / 0x93c6c8 = sleepFlagA / sleepFlagB (C: sites ef45f8 ef4600, ef4c7c ef4c84, ef5540 ef5548).
 * - this+0xca8 |= 32 -> EN_MOVECLASS 5 (C: site ef4610, GU r1 0 / 2 as 4U r1 0 / 2-5); |= 16 -> 4 (C: site efb600).
 * - 0x93457c(this, 14, 255, 0.0) = GU 0xaa418(self, 14, 255, 0, 0.0) (C: site ef468c; same body: on the machine whose
 *   player index matches, the index into 4U W+0x78e6 / GU self+0x7582, then net message 4 with (4U W+0x7eb8 / GU
 *   self+0x75f8, 14, 255, 0, s0); GU's r3 == 1 would send message 20 instead).
 * - 0x9399c0 (= 0x945e60(this, 1), the post-action think list) = GU 0x82d8c(self, 0x1644, 0) (C: site ef4704; 0x82d8c
 *   ignores r1 and calls GU 0x8282c(self, 1) = 0x945e60(this, 1) (C: em089_act.c thinkListAfter) unless self+0xba44
 *   bit 1 is set, a GU-only test that comes with the site's call).
 * - 0x92213c(this, v) = GU 0xbd650(self, v) (C: site ef4d18; same body: 4U W+0x7a1a = 1, u16 W+0x7a18 = v / GU
 *   rec+0x5d02 = 1, u16 rec+0x5d00 = v); 0xb0709c(&W+468) = timerDown(&rec+0x1bc, 1.0) (C: site ef4d2c), timer 300
 *   (C: site ef4d08).
 * - 0x930894(this, j, m) = joint matrix GU 0xc1660 (C: em089 / tigerstripe / dalamadur ports, rows of 16 bytes).
 * - 0xbe9a0c(*0xfb6fb8) = GU 0x16b920(*(main+0x1857830)) (C: site efb664 / efb66c, GOT slot 0x1838d9c; u16 serial
 *   + 1, 0 after 59999), stored at work+0x28 (C: site efb67c; work = 4U [this+0x8d88] / GU [this+0xcac0], batch B).
 * - 0x10ed68 = memcpy (C) of the 384-byte ring table 0xe0d144 (4 rows of 12 (distance, angle in degrees)) to the stack,
 *   and an ldm / stm copy of the frame table 0xe0d114: static tables here. The frame table = GU 0x16a636c (C: same 12
 *   floats); its index W+0x145 = rec+0x1a2 (C: site efb734). 4U does not bound it: after the 12th post it reads the
 *   stack word after the table (the offset vector's x, stale); GU bounds it at 11 (efb738) and so does this port.
 * - this+0x8d20 (u32[3]) = 4U's copy of the angle triple W+424..432 (C: 0x955e74, 0x94ce6c) -> rec+0x50 (REC_ANGLES),
 *   its yaw this+0x8d24 -> REC_YAW (S: GU keeps no such copy; the live angles are used).
 * - frames / motions (C, sites): 0x847274 motion 0x314 blend 4 ef465c, speed 0.7 ef4668, atFrame 66 ef469c, attackEx
 *   (0, 19, 5) ef46dc (variant 1: 19), end ef4708; 0x847a40 motion 0xf blend 4 ef4cd8, chain 1/36 ef4d58; 0x847bdc
 *   motion 0x305 blend 8 ef5594, chain 1/37 at the motion end ef560c; 0x84dd44 motion 0x14 blend 4 efb65c, speed 0.6
 *   efb688, atFrame 2 22 42 62 82 efb6dc..efb72c (GU: results unused), table frames efb78c, 60 -> 0.75 efb7c0, 278 ->
 *   motion 0x18 blend 6 efb80c, speed 0.9 efb818, attackEx(0, 53 (GU v1: 32), 1024) efb850, 122 -> 0.75 efb694, end
 *   efb6cc.
 * Posts: 0x662904 = sz_shell044 (em057_01_shell.c: the uShell044 subtype-3 pillar at the 12 ring points of 0x84dd44,
 * 4U call 0x84dff4); B5 stub, logged, 4 lines per 4U site: 0xc0819c = sz_effect_c0819c (0x847274's frame-66 post at
 * joint 4; not pure: area-gated alloc and event 20). 0xc0ca90 is pure: it constructs a 0x60-byte effect descriptor on the stack (vtable 0xe7f900, ids -1, two
 * vectors copied from 4U globals), which 0x847274 / 0x847bdc retag (vtable 0xe7f918, +0x59 = 1, +0x5a = 0, +92 = 0,
 * +96 = 255) and no handler reads again (C), so its literal translation is no code.
 * Sounds: 0x2fcc50 (207 and 219 at joint 2) = sz_snd (batch B). No GU site for the others (GU's class posts no sound,
 * C), so 0x312484 sndPos (220) plays through GU 0x4efb98 (sz_snd_at, as the shells) and the rest are logged stubs:
 * 0x390f9c (the unit's sound-event component this+0xc78), 0x2fd110
 * 0x2fff1c 0x310104 (sound manager *0xfccd6c = SND_MGR) and the store W+0x790d (a byte the sound manager reads, e.g.
 * 0x306b04; GU's 1/35 drops 4U's store of 2). Unmapped framework calls of 1/43 (no GU site: ef45e0 has no r1 = 5 path),
 * logged stubs with no effect: 0x939c00(this, 32) and 0x94c980(this). */
#include "em057_01.h"

/* GU callees and fields used only here */
typedef void (*netEvent4_t)(void *self, uint32_t a, uint32_t b, uint32_t mode, float f);
#define netEvent4   FN(netEvent4_t, 0xaa418)    /* [0x93457c(this, a, b, s0)] */
typedef void (*thinkAfter_t)(void *self, uint32_t unused, uint32_t force);
#define thinkAfter  FN(thinkAfter_t, 0x82d8c)   /* [0x9399c0] */
typedef void (*reqState_t)(void *self, uint32_t v);
#define reqState    FN(reqState_t, 0xbd650)     /* [0x92213c(this, v)] */
typedef void (*jointMtx_t)(void *self, uint32_t joint, float *out16);
#define jointMtx    FN(jointMtx_t, 0xc1660)     /* [0x930894] */
typedef uint32_t (*nextSerial_t)(void *mgr);
#define nextSerial  FN(nextSerial_t, 0x16b920)  /* [0xbe9a0c] */
#define SERIAL_MGR  (*(void **)MAIN(0x1857830)) /* its argument [*0xfb6fb8] (GU efb664: GOT slot 0x1838d9c) */
#define WK_SERIAL   0x28    /* u32 serial taken at the charge-up's start [4U work+0x28] */

#define STUB_SITES  24

/* stub sites: a 4U site logs its first 4 calls (as em057_01_mv_d.c); noinline: clang unrolls the loop at each of the
 * 18 call sites otherwise (+15 KB) */
__attribute__((noinline)) static int stub_line(uint32_t site)
{
    static uint32_t s_site[STUB_SITES];
    static uint8_t s_lines[STUB_SITES];
    uint32_t i = 0;
    while (i < STUB_SITES && s_site[i] && s_site[i] != site) i++;
    if (i == STUB_SITES || s_lines[i] >= 4) return 0;
    s_site[i] = site;
    s_lines[i]++;
    return 1;
}

/* ---- B5 stub: 4U 0xc0819c(r0 = *0x10572a4, unused; area, pos): when area equals the current area (*0xfb6b7c
 * +0xc90), a 200-byte object (0x3e3d18 / 0x3e3cbc) with pos at +0x58 (w 0.0) and area at +0xc4, posted as event 20
 * through 0x64608c(*0x10572f8, 20, obj, 0, 0) (C: 4U body; not pure). area = EN_AREA [4U W+0x14c]; pos = float[4],
 * joint 4 with w 0. site = the 4U call. Runs on every machine. Posts nothing yet: B5 replaces the body. */
void sz_effect_c0819c(void *self, uint32_t area, const float *pos, uint32_t site)
{
    (void)self;
    if (!stub_line(site)) return;
    logf("szport: B5 stub c0819c area %u pos %d %d %d (4U %x)", area, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
         site);
}

/* ---- 4U sndPos 0x312484(mgr *0xfccd6c, id, owner, pos, [sp] area, [sp+4] m2) = GU 0x4efb98 (C: dala_meteor.c,
 * notes/porting-guide.md; the orbs and blasts play through it, em057_01_efx.c sz_snd_at, which passes m2 = -2, the
 * only value 4U's sites pass here). id = 4U request id (our request keeps 4U's numbers), pos = float[4] world point,
 * area = EN_AREA. site = the 4U call (logged). */
void sz_snd_312484(void *self, uint32_t id, const float *pos, uint32_t area, int32_t m2, uint32_t site)
{
    sz_snd_at(self, id, pos, area);
    if (stub_line(site))
        logf("szport: snd 312484 %u pos %d %d %d area %u m2 %d (4U %x)", id, (int32_t)pos[0], (int32_t)pos[1],
             (int32_t)pos[2], area, m2, site);
}

/* ---- stub: 4U 0x390f9c(this+0xc78, id, arg): the unit's sound-event component (owner +4, kind +0x12): gated on the
 * owner's area against the current area, it handles ids 1000..1032 (lookup 0x398f70; for some ids a sound 0x2fff1c
 * with id 204) (S: body; G: what each id plays). No GU site. site = the 4U call. */
void sz_snd_390f9c(void *self, uint32_t id, int32_t arg, uint32_t site)
{
    (void)self;
    if (!stub_line(site)) return;
    logf("szport: snd stub 390f9c id %x arg %d (4U %x, no GU site)", id, arg, site);
}

/* stub: 4U 0x2fd110(mgr *0xfccd6c, owner, mode): when the owner's area passes 0x2fa04c and the manager's state byte is
 * 2, mode 0 -> a manager change with 231, mode 1 -> 0xbe26c4(mgr, 20, -2) and owner W+0x7af2 = 1 (C: body; G: music) */
static void sz_snd_2fd110(void *self, uint32_t mode, uint32_t site)
{
    (void)self;
    if (stub_line(site)) logf("szport: snd stub 2fd110 mode %u (4U %x, no GU site)", mode, site);
}

/* stub: 4U 0x2fff1c(mgr *0xfccd6c, id, owner, joint, [sp] area): if mgr+0xa0 is set and the area passes 0x2fa04c,
 * 0x31218c(mgr, 3, mgr+0xa0, id, owner, joint): a request from the manager's bank +0xa0 at the joint (C: body) */
static void sz_snd_2fff1c(void *self, uint32_t id, uint32_t joint, uint32_t area, uint32_t site)
{
    (void)self;
    if (stub_line(site)) logf("szport: snd stub 2fff1c %u joint %u area %u (4U %x, no GU site)", id, joint, area, site);
}

/* stub: 4U 0x310104(mgr *0xfccd6c, owner): mgr+0x1839 = 1 when the owner's area is not the current area (C: body) */
static void sz_snd_310104(void *self, uint32_t site)
{
    (void)self;
    if (stub_line(site)) logf("szport: snd stub 310104 (4U %x, no GU site)", site);
}

/* stub: 4U W+0x790d = v (u8 the sound manager reads, e.g. 0x306b04 tests 9 (C); GU's 1/35 ef4c74 drops 4U's store of
 * 2: no GU field) */
static void sz_snd_w790d(void *self, uint32_t v, uint32_t site)
{
    (void)self;
    if (stub_line(site)) logf("szport: snd stub W+0x790d = %u (4U %x, no GU field)", v, site);
}

/* 4U 0x939c00 / 0x94c980: sz_unmapped_939c00 / sz_unmapped_94c980 moved to em057_01_start.c (batch S: 4U vt47's 1/41
 * case calls them too; still no GU site, logged no-ops; declared in em057_01.h) */

/* ---- 1/39 1/42 1/43: 4U 0x847274(r1) (r1 0-2: the KEEP rows 1/9 1/38, 1/34, 1/37 on GU ef45e0; r2 unused): roar.
 * r1 2-5: sleepFlagA / B; r1 0 / 2-5: move class 5. Motion 0x314 blend 4, speed 0.7; r1 1: net message 4 (14, 255).
 * At frame 66 attack slot 0 index 19 with param 5, then r1 5: the sound event 0x404, 0x939c00(32), 0x94c980 and the
 * sound 432 at joint 2; else the effect at joint 4 and, for r1 3, the sound event 0x402 and 0x2fd110(0). At the
 * motion end the think list (r1 2-5) and the end of the action. */
void szmv_847274(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0];
    float pos[4] = { 0.0f, 0.0f, 0.0f, 0.0f };
    if (r1 == 2 || r1 == 3 || r1 == 4 || r1 == 5) {
        sleepFlagA(self);
        sleepFlagB(self);
        FIELD(uint8_t, self, EN_MOVECLASS) = 5;             /* 4U this+0xca8 |= 32 */
    } else if (r1 == 0) {
        FIELD(uint8_t, self, EN_MOVECLASS) = 5;
    }
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x314, 4.0f, 0.0f);
        setMotionSpeed(self, 0.7f);
        if (r1 == 1) netEvent4(self, 14, 255, 0, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (atFrame(self, 66.0f)) {
        attackEx(self, 0, 19, 5);
        if (r1 == 5) {
            sz_snd_390f9c(self, 0x404, -1, 0x8473f8);
            sz_unmapped_939c00(self, 32, 0x847404);
            sz_unmapped_94c980(self, 0x847410);
            sz_snd_2fff1c(self, 432, 2, FIELD(uint8_t, self, EN_AREA), 0x847430);
        } else {
            jointPos(self, 4, pos);
            sz_effect_c0819c(self, FIELD(uint8_t, self, EN_AREA), pos, 0x84737c);
            if (r1 == 3) {
                sz_snd_390f9c(self, 0x402, -1, 0x84744c);
                sz_snd_2fd110(self, 0, 0x84745c);
            }
        }
    }
    if (!isMotionEnd(self)) return;
    if (r1 == 2 || r1 == 3 || r1 == 4 || r1 == 5) thinkAfter(self, 0x1644, 0);
    end_action(self);
}

/* ---- 1/40: 4U 0x847a40(r1) (r1 0: the KEEP row 1/35 on GU ef4c74; r2 unused): lying wait. Every frame sleepFlagA /
 * B. Motion 0xf blend 4; at its end the action timer 300 and the sound state (r1 0: W+0x790d = 2; r1 1: 7, then
 * 0x310104); then every frame 0xbd650(2) and the timer; when it has run out: 1/36 (r1 0) / 1/41. */
void szmv_847a40(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0];
    sleepFlagA(self);
    sleepFlagB(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0xf, 4.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        RF(rec, REC_TIMER) = 300.0f;
        if (r1 == 0) {
            sz_snd_w790d(self, 2, 0x847ba0);
        } else if (r1 == 1) {
            sz_snd_w790d(self, 7, 0x847b70);
            sz_snd_310104(self, 0x847b80);
        }
        return;
    case 2:
        reqState(self, 2);
        timerDown(self, &RF(rec, REC_TIMER), 1.0f);
        if (!(RF(rec, REC_TIMER) <= 0.0f)) return;          /* 4U: vcmpe timer, 0.0; bhi (also when unordered) */
        chain(self, 1, r1 == 0 ? 36 : 41);
        return;
    default:
        return;
    }
}

/* ---- 1/41: 4U 0x847bdc(r1) (r1 0: the KEEP row 1/36 on GU ef4fd4(76); r2 unused): stand-up. Every frame
 * sleepFlagA / B. Motion 0x305 blend 8 with the sound events (r1 0: 0x3f8, 0x3fb, 0x2fd110(0); r1 1: 0x403,
 * 0x2fd110(1), the sound 432 at joint 2); at its end 1/37 (r1 0) / 1/42. */
void szmv_847bdc(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0];
    sleepFlagA(self);
    sleepFlagB(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x305, 8.0f, 0.0f);
        if (r1 == 0) {
            sz_snd_390f9c(self, 0x3f8, -1, 0x847cfc);
            sz_snd_390f9c(self, 0x3fb, -1, 0x847d0c);
            sz_snd_2fd110(self, 0, 0x847d1c);
        } else if (r1 == 1) {
            sz_snd_390f9c(self, 0x403, -1, 0x847cb4);
            sz_snd_2fd110(self, 1, 0x847cc4);
            sz_snd_2fff1c(self, 432, 2, FIELD(uint8_t, self, EN_AREA), 0x847ce4);
        }
        return;
    }
    if (rec[REC_STEP0] != 1 || !isMotionEnd(self)) return;
    chain(self, 1, r1 == 0 ? 37 : 42);
}

/* 4U 0xe0d114: the frames of the 12 ring posts (= GU 0x16a636c) */
static const float k_ring_frame[12] = {66.0f, 106.0f, 136.0f, 156.0f, 176.0f, 186.0f,
                                       196.0f, 206.0f, 216.0f, 226.0f, 236.0f, 246.0f};
/* 4U 0xe0d144: per r1, 12 ring points (distance, angle in degrees from the yaw) */
static const float k_ring[4][12][2] = {
    {{1300, 50}, {1200, 150}, {500, 300}, {800, 80}, {1000, 10}, {900, 270}, {500, 220}, {1000, 225}, {800, 340},
     {1100, 180}, {900, 20}, {1000, 120}},
    {{1300, 350}, {600, 40}, {1000, 260}, {500, 180}, {800, 190}, {950, 245}, {1000, 315}, {900, 30}, {500, 270},
     {500, 90}, {1200, 130}, {1200, 150}},
    {{1000, 325}, {800, 30}, {1100, 340}, {1500, 0}, {1300, 70}, {1400, 315}, {700, 0}, {750, 90}, {1250, 10},
     {600, 270}, {1000, 320}, {800, 45}},
    {{1300, 135}, {900, 170}, {1500, 30}, {1300, 275}, {1400, 55}, {1000, 225}, {1200, 325}, {950, 180}, {800, 290},
     {1450, 190}, {1300, 0}, {1200, 85}},
};

/* ---- 7/113 7/115: 4U 0x84dd44(r1) (r1 = ring row 1 / 3; rows 0 / 2 = 7/94 / 7/114, unreachable; r2 unused):
 * charge-up. Every frame move class 4. Motion 0x14 blend 4, speed 0.6, a new serial in work+0x28; sound 207 at joint 2
 * at frames 2 22 42 62 82; at the 12 frames of k_ring_frame the uShell044 (Stygian subtype 3) at the next ring point
 * (distance turned by yaw + angle); sound 219 at joint 2 at frame 94; sound 220 at joint 1's point (0, -90, 60) at
 * frames 100-260 every 20; speed 0.75 at frame 60; at frame 278 motion 0x18 blend 6, speed 0.9, attack slot 0 index 53
 * (em 48 / 114: 32) with param 1024; then speed 0.75 at frame 122 and the end of the action at the motion end. */
void szmv_84dd44(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0];
    FIELD(uint8_t, self, EN_MOVECLASS) = 4;                 /* 4U this+0xca8 |= 16 */
    switch (rec[REC_STEP0]) {
    case 0: {
        void *mgr = SERIAL_MGR;
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        setMotion(self, 0x14, 4.0f, 0.0f);
        if (mgr) RU(WORK(self), WK_SERIAL) = nextSerial(mgr);   /* no manager: GU efb66c would fault */
        setMotionSpeed(self, 0.6f);
        return;
    }
    case 1: {
        uint32_t k = rec[REC_STEP1];
        if (atFrame(self, 2.0f) || atFrame(self, 22.0f) || atFrame(self, 42.0f) || atFrame(self, 62.0f) ||
            atFrame(self, 82.0f))
            sz_snd(self, 207, 2, 0x84df2c);
        if (k < 12 && atFrame(self, k_ring_frame[k])) {     /* 4U: no bound (GU efb738: k <= 11) */
            float ofs[4] = { 0.0f, 0.0f, k_ring[r1][k][0], 0.0f };
            rot_y(ofs, RU(rec, REC_YAW) + u16_of(0.5f + k_ring[r1][k][1] * 182.04445f));
            sz_shell044(self, 3, ofs, &RU(rec, REC_ANGLES), 0xffff, 0, 0.0f, 0x84dff4);
            rec[REC_STEP1]++;
        }
        if (atFrame(self, 94.0f)) sz_snd(self, 219, 2, 0x84e03c);
        if (atFrame(self, 100.0f) || atFrame(self, 120.0f) || atFrame(self, 140.0f) || atFrame(self, 160.0f) ||
            atFrame(self, 180.0f) || atFrame(self, 200.0f) || atFrame(self, 220.0f) || atFrame(self, 240.0f) ||
            atFrame(self, 260.0f)) {
            float m[16], pos[4];
            jointMtx(self, 1, m);
            float x = m[0] * 0.0f, y = m[1] * 0.0f, z = m[2] * 0.0f;
            x += m[4] * -90.0f;
            y += m[5] * -90.0f;
            z += m[6] * -90.0f;
            x += m[8] * 60.0f;
            y += m[9] * 60.0f;
            z += m[10] * 60.0f;
            pos[0] = m[12] + x;
            pos[1] = m[13] + y;
            pos[2] = m[14] + z;
            pos[3] = 0.0f;
            sz_snd_312484(self, 220, pos, FIELD(uint8_t, self, EN_AREA), -2, 0x84e238);
        }
        if (atFrame(self, 60.0f)) setMotionSpeed(self, 0.75f);
        if (!atFrame(self, 278.0f)) return;
        rec[REC_STEP0]++;
        setMotion(self, 0x18, 6.0f, 0.0f);
        setMotionSpeed(self, 0.9f);
        attackEx(self, 0, 53, 1024);
        return;
    }
    case 2:
        if (atFrame(self, 122.0f)) setMotionSpeed(self, 0.75f);
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}
