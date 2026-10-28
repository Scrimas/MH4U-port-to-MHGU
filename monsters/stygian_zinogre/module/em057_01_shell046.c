/* em057_01_shell046.c: Stygian Zinogre's dragon orbs, a literal translation of 4U uShell046 (DTI 0x10bc210, 0x338 B,
 * vtable 0xe6e6ac) on this port's GU uShellEnemy framework (em057_01_shell.h); posted by em057_01_posts.c (the orb
 * volleys). notes/b5-shells.md 1a and 8g. C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * 4U (C unless marked):
 * - post 0x6629bc(mgr, owner, sub, &off, [sp] &A, &B, &origin, &angles, u16 grp; s0-s5 = f0..f5) -> message 46 {+0
 *   sub, +2 grp, +4 f0 f1 f2, +0x10 f3 f4 f5, +0x20 off, +0x30 A, +0x40 B, +0x50 origin, +0x60 angles, +0x6c owner}
 *   -> ctor 0xc8a754: position +0x100 = origin + R off, A +0x278 = origin + R A, B +0x288 = origin + R B, with R =
 *   Ry(angles[1]) Rx(angles[0]) Rz(angles[2]) (turn_zxy); path +0x2b0 = capsule end +0x120 = position, angles +0x110 =
 *   0; f0 +0x298 (speed to A), f1 +0x29c (speed to B), f2 +0x2a0 (age limit), f3 +0x2e0 (arc), |f4| +0x2f8 (wobble
 *   radius), f5 +0x2fc (wobble speed) and +0x300 (the wobble velocity starts at (f5, 0, 0)); the leg time / timer,
 *   drawn position, axis and wobble offset start at 0. Subtypes 2 / 3 / 4 of an em-49 owner take a target: kind
 *   W+0x278 in {0, 1} -> t = 0x92c960(owner, W+0x27a, W+0x27c), kept when 0x91f8bc(owner, t, 0); then +0x324 = t and
 *   +0x328 = t's position with the y rule (y <= 0: y + 150; 0 < y <= 150: 150; else as is); no target -> +0x320 =
 *   255.
 * - init 0xc89184: subtype < 5 and an owner, else done; the flight effect (58, 20) = em049_015, mask 1 (table
 *   0x10308a8) ON the shell (0xc08698, request +0x5c = shell), handle +0x274 (a failed post sets state 2, the init
 *   then sets 1 anyway, 0xc892a4); arm 0x9ab120(records 0x10307e0, volumes 0x10307d8, sub, 23, 2); grp != 0xffff ->
 *   the slot's group; sound timer +0x270 = 0; state 1, then the first per-frame (tail call 0xc892c4).
 * - per frame 0xc892f0: owner gone / leaving (0x917620) -> slot off, state 3; slot inactive or age +316 >= 18000 ->
 *   state 2; flight effect dead -> state 2; sound 215 on the shell when the timer +0x270 runs out (0x9aad4c), timer 22;
 *   then by subtype (0 / 1: 0xc89430, 2 / 4: 0xc89cb8, 3: 0xc8977c): age >= f2 -> em049_017 mask 2 at the position
 *   (0xc08628), state 2 (orb_expire); else the phase +0xf2:
 *     0: phase 1, a leg to A at f0 (0xc8a1fc: velocity = unit(A - position) * f0, leg time T = |A - position| / f0,
 *        timer 0), then as 1;
 *     1: timer >= T -> phase 2 (subtype 4 first stops and waits 30 more frames, 0xc89d74), else timer += dt;
 *     2: subtype 2: B = the target's position now (y rule) when still valid; subtype 4: B = +0x328 when it has a
 *        target; subtype 3: B = the target's position now (y rule) when still valid, then B += unit(B - owner
 *        position) * 600 (always); subtypes 0 / 1: B as posted; then phase 3: path = drawn = previous drawn =
 *        position, a leg to B at f1, the arc axis (1, 0, 0) (MT constant 0x10e63a8) turned by the leg's pitch then
 *        yaw, sound 224 on the shell, then as 3;
 *     3: timer >= T -> phase 4 with velocity = (drawn - previous drawn) / dt, else timer += dt;
 *     4: straight on.
 *   Then the move 0xc8a4ec: capsule end = position, path += velocity * dt; phase 3: drawn = path + axis * f3 sin(pi
 *   timer / T); else drawn = path; subtypes 0 / 1 in phases 3 / 4 wobble (0xc8a334), phases 0-2 zero the wobble
 *   offset; position = drawn + Ry(+0x114) Rx(+0x110) Rz(+0x118) wobble offset. Then a zero-length capsule (each axis
 *   within 0.01) lowers the capsule end by 1; angles +0x110 / +0x114 = the step's pitch / yaw; the slot's window
 *   length +448 = 100 every frame (so the attack never runs out: the design's "99-frame life" was wrong); collision
 *   0xc8a288: the slot's hit byte +0x16e != 255 -> at the position, else the map segment position -> capsule end
 *   (0x2b96e4, mask 48, flags 0x9aad8c): an impact = em049_017 mask 1 at the point (0xc08628) + sound 216 there
 *   (0x312484), state 2; else age += dt.
 * - wobble 0xc8a334: when u16 [*0xfb6b7c + 0x22] < 4096 the wobble velocity is re-aimed: (0, f5) turned by its old
 *   angle atan2(-x, y) plus (v & 8192) - 4096 (the same u16 read again: below 4096 its bit 13 is clear, so always
 *   -4096 = -22.5 deg); offset += velocity * dt; past the radius: offset back on the radius, velocity = -f5 along it.
 *   The u16's writers are state copies (0xc27830 / 0xc2789c, 0xc1d8fc) and a save / restore around 0x2f4c5c (G: its
 *   meaning); the port draws the 1-in-16 chance from a per-orb LCG seeded with the action serial and the orb's index
 *   (the same on every machine; a deviation in timing only).
 * - kill 0xc8a750 = the base kill 0x9ab16c (state 3, slot off): the flight effect is not released there, it is
 *   attached to the shell (S: it ends with it).
 * GU (C unless marked): the target = GU 0xc2eb4(owner, rec+0x232, rec+0x234) (twin of 0x92c960: the same 255 / mask
 * 10 / index rules and uPlayer class test); 4U's 0x91f8bc(owner, t, 0) as GU translated it inline in its own target
 * code (0xc29a4..0xc29c8, the twin of 4U 0x92cfac..0x92cfe8): present (0x49240(pl+0x1051) == 0, in place of 4U
 * 0x6832c8(mgr, [t+0xe30]+0x33)) and in the owner's area (pl+0x1054 == owner+0x1054); 4U's state-8 test (+0x371) has
 * no counterpart there and is left out (S); the hunter's position pl+0x40 (= 4U [t+0xe30]+0x10, GU 0xc29cc). Map
 * segment 0x1838fc and its flags 0x4a2a8c (= 4U 0x2b96e4 / 0x9aad8c, dala_meteor.c). The window length = slot +0x60,
 * the hit byte = slot +6 (em057_01_shell.h). The flight effect: record 3215 posted on the shell (em057_01_efx.c
 * sz_efx_on: GU shells' own request style, attach model + position + unit + area); the expiry / impact effects 3267 /
 * 3217 as world posts; none of em049_015 / 017's elements has a ground variant (C). The flight effect is finished at
 * the kill (S above). 4U's init tail call is left to GU's first unit update (the shell's dt is set there, S): the orb
 * starts one update later at most.
 * Multiplayer: no net test in the class or its posts (C); every machine runs the volley handler and posts its own
 * orbs; the target comes from the synced target slot, its position is read locally (on the target's own machine the
 * orb flies at him, where his hits count). */
#include "em057_01_shell.h"
#include "em057_01_shelldata.h"

typedef void *(*tgtHunter_t)(void *self, uint32_t sub, uint32_t param);
#define tgtHunter    FN(tgtHunter_t, 0xc2eb4)   /* [0x92c960] */
typedef int (*plAbsent_t)(uint32_t index);
#define plAbsent     FN(plAbsent_t, 0x49240)    /* [0x6832c8(mgr, index)] */
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment   FN(map_segment_t, 0x1838fc) /* [0x2b96e4] */
typedef uint32_t (*shell_flags_t)(void *self);
#define colFlags     FN(shell_flags_t, 0x4a2a8c) /* [0x9aad8c] */
#define COL_MGR      (*(void **)MAIN(0x21270e0))
#define PL_INDEX     0x1051     /* u8 player index [4U [t+0xe30]+0x33] */
#define PL_AREA      0x1054     /* u8 area [4U [t+0xe30]+9] */
#define PL_POS       0x40       /* float[3] position [4U [t+0xe30]+0x10] */

#define O_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [4U +0xfd] */
#define O_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define O_PHASE   (SIZE_uShellEnemy + 0x02)   /* u8 [+0xf2] */
#define O_ARMED   (SIZE_uShellEnemy + 0x03)
#define O_TKIND   (SIZE_uShellEnemy + 0x04)   /* u8 target slot kind, 255 = none [+0x320] */
#define O_TINDEX  (SIZE_uShellEnemy + 0x05)   /* u8 the target's player index (logs) */
#define O_GROUP   (SIZE_uShellEnemy + 0x06)   /* u16 hit group [+0x26c] */
#define O_SERIAL  (SIZE_uShellEnemy + 0x08)
#define O_TARGET  (SIZE_uShellEnemy + 0x0c)   /* void * the target hunter [+0x324] */
#define O_RAND    (SIZE_uShellEnemy + 0x10)   /* u32 wobble LCG */
#define O_AGE     (SIZE_uShellEnemy + 0x14)   /* float [+316] */
#define O_SNDT    (SIZE_uShellEnemy + 0x18)   /* float sound-215 timer [+0x270] */
#define O_EFX     (SIZE_uShellEnemy + 0x1c)   /* void * flight effect [+0x274] */
#define O_F       (SIZE_uShellEnemy + 0x20)   /* float[3] f0 f1 f2 [+0x298] */
#define O_T       (SIZE_uShellEnemy + 0x2c)   /* float leg time [+0x2a4] */
#define O_TT      (SIZE_uShellEnemy + 0x30)   /* float leg timer [+0x2a8] */
#define O_ARC     (SIZE_uShellEnemy + 0x34)   /* float f3 [+0x2e0] */
#define O_WRAD    (SIZE_uShellEnemy + 0x38)   /* float |f4| [+0x2f8] */
#define O_WSPD    (SIZE_uShellEnemy + 0x3c)   /* float f5 [+0x2fc] */
#define O_POS     (SIZE_uShellEnemy + 0x40)   /* float[3] spawn position [+0x100 at the ctor] */
#define O_VEL     (SIZE_uShellEnemy + 0x4c)   /* float[3] [+0x140] */
#define O_A       (SIZE_uShellEnemy + 0x58)   /* float[3] [+0x278] */
#define O_B       (SIZE_uShellEnemy + 0x64)   /* float[3] [+0x288] */
#define O_PATH    (SIZE_uShellEnemy + 0x70)   /* float[3] [+0x2b0] */
#define O_DRAWN   (SIZE_uShellEnemy + 0x7c)   /* float[3] [+0x2c0] */
#define O_DPREV   (SIZE_uShellEnemy + 0x88)   /* float[3] [+0x2d0] */
#define O_AXIS    (SIZE_uShellEnemy + 0x94)   /* float[3] [+0x2e8] */
#define O_WVEL    (SIZE_uShellEnemy + 0xa0)   /* float[3] [+0x300] */
#define O_WOFS    (SIZE_uShellEnemy + 0xac)   /* float[3] [+0x310] */
#define O_TPOS    (SIZE_uShellEnemy + 0xb8)   /* float[3] the target's position at the post [+0x328] */
#define O_SIZE    (SIZE_uShellEnemy + 0xc4)
#define O_AGE_CAP 18000.0f                    /* 0xc89348 */
#define O_SND_GAP 22.0f                       /* 0xc893e4 */
#define O_WINDOW  100.0f                      /* the slot's window length every frame (0xc89748) */
#define O_HOVER   30.0f                       /* subtype 4's wait at A (0xc89d84) */
#define O_PUSH    600.0f                      /* subtype 3's B past the target (0xc89938) */
#define O_YMIN    150.0f                      /* the y rule (0xc8ac6c) */
#define O_LINES   160u

#define V(self, off) (&FIELD(float, self, off))

static szcls_t s_orb;
static uint32_t s_orb_serial, s_orb_lines;

static int orb_line(void)
{
    if (s_orb_lines >= O_LINES) return 0;
    s_orb_lines++;
    return 1;
}

static void sincos_u16(uint32_t a, float *s, float *c)
{
    float r = (float)(a & 0xffff) * 0x1.921fb6p-14f;
    *s = sinf_gu(r);
    *c = cosf_gu(r);
}

/* v turned by az about z, then ax about x, then ay about y (ctor 0xc8a7dc.., move 0xc8a5a4.., 4U table sin / cos) */
static void turn_zxy(float *out, const float *v, uint32_t ax, uint32_t ay, uint32_t az)
{
    float s, c, x, y, z, t;
    sincos_u16(az, &s, &c);
    x = c * v[0] - s * v[1];
    y = s * v[0] + c * v[1];
    z = v[2];
    sincos_u16(ax, &s, &c);
    t = c * y - s * z;
    z = s * y + c * z;
    y = t;
    sincos_u16(ay, &s, &c);
    t = c * x + s * z;
    z = c * z - s * x;
    x = t;
    out[0] = x;
    out[1] = y;
    out[2] = z;
}

static float vsqrt(float d)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

static void copy3(float *d, const float *s) { d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; }

/* the y rule of a target position (ctor 0xc8ac14, re-aims 0xc898a8 / 0xc8a02c) */
static float y_rule(float y)
{
    if (y > O_YMIN) return y;
    return y > 0.0f ? O_YMIN : y + O_YMIN;
}

/* 4U 0x91f8bc(owner, t, 0) as GU translated it (header) */
static int hunter_valid(void *owner, void *pl)
{
    return pl && owner && !plAbsent(FIELD(uint8_t, pl, PL_INDEX)) &&
           FIELD(uint8_t, pl, PL_AREA) == FIELD(uint8_t, owner, EN_AREA);
}

/* 0xc8a1fc: a leg from the position to p at speed v; returns the leg time */
static float orb_leg(void *self, const float *p, float v)
{
    const float *pos = V(self, SH_POS);
    float d[3] = {p[0] - pos[0], p[1] - pos[1], p[2] - pos[2]}, len, t, *vel = V(self, O_VEL);
    len = vsqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    t = len / v;
    if (len >= 0x1p-23f)                                     /* 0xc8a238: bits >= 0x34000000 */
        for (int i = 0; i < 3; i++) d[i] *= 1.0f / len;
    for (int i = 0; i < 3; i++) vel[i] = d[i] * v;
    return t;
}

/* 0x9aad4c: 1 when the timer is or reaches 0 (then 0) */
static int timer_out(void *self, float *t)
{
    if (*t > 0.0f) {
        *t -= FIELD(float, self, SH_DT);
        if (*t > 0.0f) return 0;
    }
    *t = 0.0f;
    return 1;
}

static void orb_end(void *self, const char *why)
{
    if (orb_line())
        logf("szport: orb %u end at age %d: %s", FIELD(uint32_t, self, O_SERIAL), (int32_t)FIELD(float, self, O_AGE),
             why);
    FIELD(uint8_t, self, O_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 16 = 4U slot 24 (the base kill); the flight effect ends with the shell it is attached to in 4U (S) */
static void orb_kill(void *self)
{
    void *h = FIELD(void *, self, O_EFX);
    uShell_kill(self);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, O_EFX) = 0;
}

/* phase 2 -> 3 (0xc8949c.., 0xc89974.., 0xc89df8..): the leg to B */
static void orb_leg_b(void *self, void *owner)
{
    float *pos = V(self, SH_POS), *vel = V(self, O_VEL), *axis = V(self, O_AXIS);
    uint32_t pitch, yaw;
    FIELD(uint8_t, self, O_PHASE) = 3;
    copy3(V(self, O_PATH), pos);
    copy3(V(self, O_DRAWN), pos);
    copy3(V(self, O_DPREV), pos);
    FIELD(float, self, O_T) = orb_leg(self, V(self, O_B), V(self, O_F)[1]);
    FIELD(float, self, O_TT) = 0.0f;
    axis[0] = sz_orb_arc_axis[0];
    axis[1] = sz_orb_arc_axis[1];
    axis[2] = sz_orb_arc_axis[2];
    pitch = atan_u16(-vel[1], vsqrt(vel[0] * vel[0] + vel[2] * vel[2]));
    yaw = atan_u16(vel[0], vel[2]);
    turn_zxy(axis, axis, pitch, yaw, 0);
    sz_snd_obj(owner, 224, self);
    if (orb_line()) {
        const float *b = V(self, O_B);
        logf("szport: orb %u leg to B %d %d %d at age %d (leg time %d)", FIELD(uint32_t, self, O_SERIAL),
             (int32_t)b[0], (int32_t)b[1], (int32_t)b[2], (int32_t)FIELD(float, self, O_AGE),
             (int32_t)FIELD(float, self, O_T));
    }
}

/* the end of a leg's timer: phase 3 -> 4 (0xc89604.., 0xc89adc.., 0xc89f64..), else timer += dt */
static void orb_leg_tick(void *self)
{
    float *t = V(self, O_T), *tt = V(self, O_TT);
    if (*tt < *t) {
        *tt += FIELD(float, self, SH_DT);
        return;
    }
    if (FIELD(uint8_t, self, O_PHASE) != 3) {
        FIELD(uint8_t, self, O_PHASE) = 2;
        return;
    }
    FIELD(uint8_t, self, O_PHASE) = 4;
    *t = *tt = 0.0f;
    for (int i = 0; i < 3; i++)
        V(self, O_VEL)[i] = (V(self, O_DRAWN)[i] - V(self, O_DPREV)[i]) * (1.0f / FIELD(float, self, SH_DT));
}

/* 0xc8a334 */
static void orb_wobble(void *self)
{
    float *wv = V(self, O_WVEL), *wo = V(self, O_WOFS), r = FIELD(float, self, O_WRAD), sp = FIELD(float, self, O_WSPD);
    uint32_t x = FIELD(uint32_t, self, O_RAND) * 1103515245u + 12345u;
    FIELD(uint32_t, self, O_RAND) = x;
    if ((x >> 16 & 0xffff) < 4096) {                       /* u16 [*0xfb6b7c + 0x22] < 4096 (G: its source) */
        uint32_t a = atan_u16(-wv[0], wv[1]) - 4096u;      /* the side: always -4096 (header) */
        float s, c;
        sincos_u16(a, &s, &c);
        wv[0] = -s * sp;                                    /* (0, f5) turned by a */
        wv[1] = c * sp;
        wv[2] = 0.0f;
    }
    for (int i = 0; i < 3; i++) wo[i] += wv[i] * FIELD(float, self, SH_DT);
    if (wo[0] * wo[0] + wo[1] * wo[1] + wo[2] * wo[2] > r * r) {
        float k = 1.0f / vsqrt(wo[0] * wo[0] + wo[1] * wo[1] + wo[2] * wo[2]);
        for (int i = 0; i < 3; i++) {
            wo[i] *= k;
            wv[i] = -wo[i] * sp;
            wo[i] *= r;
        }
    }
}

/* 0xc8a4ec */
static void orb_move(void *self)
{
    float *pos = V(self, SH_POS), *path = V(self, O_PATH), *drawn = V(self, O_DRAWN), *wo = V(self, O_WOFS), w[3];
    uint32_t phase = FIELD(uint8_t, self, O_PHASE), sub = FIELD(uint8_t, self, O_SUB);
    const uint32_t *ang = &FIELD(uint32_t, self, SH_ANGLES);
    copy3(V(self, SH_POS2), pos);
    for (int i = 0; i < 3; i++) path[i] += V(self, O_VEL)[i] * FIELD(float, self, SH_DT);
    if (phase == 3) {
        float s;
        copy3(V(self, O_DPREV), drawn);
        copy3(drawn, path);
        s = sinf_gu(FIELD(float, self, O_TT) * 3.14159274f / FIELD(float, self, O_T)) * FIELD(float, self, O_ARC);
        for (int i = 0; i < 3; i++) drawn[i] += V(self, O_AXIS)[i] * s;
    } else
        copy3(drawn, path);
    if (phase == 3 || phase == 4) {
        if (sub < 2) orb_wobble(self);
    } else
        wo[0] = wo[1] = wo[2] = 0.0f;
    turn_zxy(w, wo, ang[0], ang[1], ang[2]);
    for (int i = 0; i < 3; i++) pos[i] = drawn[i] + w[i];
}

static void orb_point_fx(void *self, void *owner, uint32_t id, const float *p, const char *what, uint32_t r)
{
    void *h = sz_efx_world(owner, id, p, 0, 0);
    if (orb_line())
        logf("szport: orb %u %s (%x) at %d %d %d age %d: efx %x", FIELD(uint32_t, self, O_SERIAL), what, r,
             (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], (int32_t)FIELD(float, self, O_AGE), (uint32_t)h);
}

/* age >= f2 (0xc89790, 0xc89ccc): em049_017 mask 2 at the position */
static int orb_expire(void *self, void *owner)
{
    if (FIELD(float, self, O_AGE) < V(self, O_F)[2]) return 0;
    orb_point_fx(self, owner, SZ_EFX_EXPIRE, V(self, SH_POS), "expired", 0);
    orb_end(self, "age limit");
    return 1;
}

/* the common tail after the phase step (0xc89694, 0xc89b48, 0xc8a07c) */
static void orb_tail(void *self, void *owner)
{
    float *pos = V(self, SH_POS), *cap = V(self, SH_POS2), d[3], out[4] = {0, 0, 0, 0};
    uint32_t r = 255, hit = 0;
    orb_move(self);
    for (int i = 0; i < 3; i++) d[i] = pos[i] - cap[i];
    if ((d[0] < 0 ? -d[0] : d[0]) <= 0.01f && (d[1] < 0 ? -d[1] : d[1]) <= 0.01f &&
        (d[2] < 0 ? -d[2] : d[2]) <= 0.01f)
        cap[1] -= 1.0f;
    FIELD(uint32_t, self, SH_ANGLES) = atan_u16(-d[1], vsqrt(d[0] * d[0] + d[2] * d[2]));
    FIELD(uint32_t, self, SH_ANGLES + 4) = atan_u16(d[0], d[2]);
    FIELD(float, self, SH_ATK0 + ATK_TIME) = O_WINDOW;
    if (FIELD(uint8_t, self, SH_ATK0 + ATK_HIT) != 255) {   /* 0xc8a288 */
        copy3(out, pos);
        hit = 2;
    } else {
        void *col = COL_MGR;
        r = col ? mapSegment(col, pos, cap, FIELD(uint8_t, self, SH_AREA), out, 0, 48, colFlags(self)) : 0;
        if (r) hit = 1;
    }
    if (hit) {
        orb_point_fx(self, owner, SZ_EFX_IMPACT, out, hit == 2 ? "impact: attack connected" : "impact: map", r);
        sz_snd_at(owner, 216, out, FIELD(uint8_t, self, SH_AREA));
        orb_end(self, "impact");
        return;
    }
    FIELD(float, self, O_AGE) += FIELD(float, self, SH_DT);
}

/* the target's position now with the y rule, when it is still valid (0xc89840.., 0xc89fc4..) */
static int orb_reaim(void *self, void *owner)
{
    void *pl = FIELD(void *, self, O_TARGET);
    float *b = V(self, O_B);
    uint32_t k = FIELD(uint8_t, self, O_TKIND);
    if (!pl || k > 1 || !hunter_valid(owner, pl)) return 0;
    copy3(b, V(pl, PL_POS));
    b[1] = y_rule(b[1]);
    return 1;
}

static void orb_frame(void *self)
{
    void *owner = FIELD(void *, FIELD(uint8_t *, self, SH_PARAM), 0xc), *h = FIELD(void *, self, O_EFX);
    uint32_t sub = FIELD(uint8_t, self, O_SUB), phase = FIELD(uint8_t, self, O_PHASE);
    if (!FIELD(uint8_t, self, SH_ATK0 + ATK_ACTIVE) || FIELD(float, self, O_AGE) >= O_AGE_CAP) {
        orb_end(self, FIELD(uint8_t, self, O_ARMED) ? "attack slot inactive" : "not armed");
        return;
    }
    if (h && !sz_efx_alive(h)) {
        FIELD(void *, self, O_EFX) = 0;
        orb_end(self, "flight effect gone");
        return;
    }
    if (timer_out(self, V(self, O_SNDT))) {
        sz_snd_obj(owner, 215, self);
        FIELD(float, self, O_SNDT) = O_SND_GAP;
    }
    if (orb_expire(self, owner)) return;
    switch (phase) {
    case 0:
        FIELD(uint8_t, self, O_PHASE) = 1;
        FIELD(float, self, O_T) = orb_leg(self, V(self, O_A), V(self, O_F)[0]);
        FIELD(float, self, O_TT) = 0.0f;
        /* fall through: the timer test of phase 1 */
    case 1:
        if (sub == 4 && FIELD(float, self, O_TT) >= FIELD(float, self, O_T)) {   /* 0xc89d74: stop, 30 frames */
            float *v = V(self, O_VEL);
            v[0] = v[1] = v[2] = 0.0f;
            if (FIELD(float, self, O_TT) < FIELD(float, self, O_T) + O_HOVER) {
                FIELD(float, self, O_TT) += FIELD(float, self, SH_DT);
                break;
            }
            FIELD(uint8_t, self, O_PHASE) = 2;
            break;
        }
        orb_leg_tick(self);
        break;
    case 2:
        if (sub == 2) orb_reaim(self, owner);
        else if (sub == 4) {
            if (FIELD(void *, self, O_TARGET)) copy3(V(self, O_B), V(self, O_TPOS));
        } else if (sub == 3) {
            float *b = V(self, O_B), d[3], len;
            const float *o = &RF(REC(owner), REC_POS_X);
            orb_reaim(self, owner);
            for (int i = 0; i < 3; i++) d[i] = b[i] - o[i];
            len = vsqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
            if (len >= 0x1p-23f)
                for (int i = 0; i < 3; i++) d[i] *= 1.0f / len;
            for (int i = 0; i < 3; i++) b[i] += d[i] * O_PUSH;
        }
        orb_leg_b(self, owner);
        orb_leg_tick(self);
        break;
    case 3:
        orb_leg_tick(self);
        break;
    default:
        break;
    }
    orb_tail(self, owner);
}

/* slot 79: base set-up, then 4U init 0xc89184 */
static int orb_setup(void *self, void *param)
{
    void *owner;
    uint32_t sub = FIELD(uint8_t, self, O_SUB);
    if (uShellEnemy_setup(self, param) != 1) return 0;
    owner = FIELD(void *, param, 0xc);
    copy3(V(self, SH_POS), V(self, O_POS));
    copy3(V(self, SH_POS2), V(self, O_POS));
    for (int i = 0; i < 3; i++) FIELD(uint32_t, self, SH_ANGLES + 4 * i) = 0;
    FIELD(void *, self, O_EFX) = sz_efx_on(owner, SZ_EFX_FLIGHT, self);
    FIELD(uint8_t, self, O_ARMED) = (uint8_t)sz_shell_arm(self, SZ_HDS_ORB, 23, 2, FIELD(uint16_t, self, O_GROUP));
    FIELD(float, self, O_SNDT) = 0.0f;
    FIELD(uint8_t, self, O_STATE) = 1;                     /* 0xc892a4, also after a failed effect post */
    if (orb_line()) {
        const float *p = V(self, O_POS), *a = V(self, O_A), *b = V(self, O_B);
        logf("szport: orb %u sub %u at %d %d %d A %d %d %d B %d %d %d f %d %d %d target %d (kind %u) hit %u efx %x",
             FIELD(uint32_t, self, O_SERIAL), sub, (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], (int32_t)a[0],
             (int32_t)a[1], (int32_t)a[2], (int32_t)b[0], (int32_t)b[1], (int32_t)b[2],
             (int32_t)(V(self, O_F)[0] * 100.0f), (int32_t)(V(self, O_F)[1] * 100.0f), (int32_t)V(self, O_F)[2],
             FIELD(void *, self, O_TARGET) ? (int32_t)FIELD(uint8_t, self, O_TINDEX) : -1,
             FIELD(uint8_t, self, O_TKIND), FIELD(uint8_t, self, O_ARMED), (uint32_t)FIELD(void *, self, O_EFX));
    }
    return 1;
}

/* slot 9 = 4U slot 23 */
static void orb_move_slot(void *self)
{
    uShell_move(self);
    if (sz_shell_live(self) && FIELD(uint8_t, self, O_STATE) == 1) orb_frame(self);
}

static void *orb_new(MtDTI *dti) { (void)dti; return sz_cls_new(&s_orb); }
static MtDTI *orb_dti(void *self) { (void)self; return &s_orb.dti; }
static void orb_delete(void *self)
{
    void *h = FIELD(void *, self, O_EFX);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, O_EFX) = 0;
    sz_cls_free(&s_orb, self);
}

/* 4U 0x6629bc + ctor 0xc8a754 (em057_01.h); rec = the 72-B record, origin / angles = the volley's, seed = the
 * wobble LCG's seed */
void sz_shell046(void *owner, uint32_t sub, const void *record, const float *origin, const uint32_t *angles,
                 uint32_t grp, uint32_t seed, uint32_t site)
{
    const sz_orb_rec *r = record;
    void *param, *shell;
    float pos[3];
    if (sub >= 5 || !owner || !r) {
        if (orb_line()) logf("szport: orb subtype %u dropped (4U %x)", sub, site);
        return;
    }
    if (!s_orb.registered)
        sz_cls_register(&s_orb, "uShellEm057_01Orb", O_SIZE, orb_new, orb_delete, orb_dti, orb_move_slot, orb_setup,
                        orb_kill);
    turn_zxy(pos, r->off, angles[0], angles[1], angles[2]);
    for (int i = 0; i < 3; i++) pos[i] += origin[i];
    param = sz_shell_param(owner, 0, pos, grp, "orb");
    if (!param) return;
    shell = sz_cls_new(&s_orb);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return;
    }
    FIELD(uint8_t, shell, O_SUB) = (uint8_t)sub;
    FIELD(uint16_t, shell, O_GROUP) = (uint16_t)grp;
    copy3(V(shell, O_POS), pos);
    copy3(V(shell, O_PATH), pos);
    turn_zxy(V(shell, O_A), r->a, angles[0], angles[1], angles[2]);
    turn_zxy(V(shell, O_B), r->b, angles[0], angles[1], angles[2]);
    for (int i = 0; i < 3; i++) {
        V(shell, O_A)[i] += origin[i];
        V(shell, O_B)[i] += origin[i];
        V(shell, O_F)[i] = r->f[i];
    }
    FIELD(float, shell, O_ARC) = r->f[3];
    FIELD(float, shell, O_WRAD) = r->f[4] < 0.0f ? -r->f[4] : r->f[4];
    FIELD(float, shell, O_WSPD) = r->f[5];
    V(shell, O_WVEL)[0] = r->f[5];                          /* +0x300 = f5 */
    FIELD(uint32_t, shell, O_RAND) = seed;
    if (sub >= 2) {                                          /* 0xc8ab40..: the target */
        const uint8_t *k = REC(owner) + REC_TGT_KIND;
        void *pl = k[0] <= 1 ? tgtHunter(owner, k[2], k[4]) : 0;
        FIELD(uint8_t, shell, O_TKIND) = k[0];
        if (pl && hunter_valid(owner, pl)) {
            FIELD(void *, shell, O_TARGET) = pl;
            FIELD(uint8_t, shell, O_TINDEX) = FIELD(uint8_t, pl, PL_INDEX);
            copy3(V(shell, O_TPOS), V(pl, PL_POS));
            V(shell, O_TPOS)[1] = y_rule(V(shell, O_TPOS)[1]);
        } else
            FIELD(uint8_t, shell, O_TKIND) = 255;
    }
    FIELD(uint32_t, shell, O_SERIAL) = ++s_orb_serial;
    sz_shell_start(shell, param, "orb");
}
