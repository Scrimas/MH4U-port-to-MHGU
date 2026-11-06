/* em007_01_mv_g.c: Monoblos, ported 4U uEm101 handlers, batch G: category 3 (motion 0x101: settle, turn, walk to the
 * target, fall and land). Literal translations (MH4U v1.1), run by em007_01_moves_run. GU's own Diablos has GU
 * versions of some: its fall / land 0xd3dd00 (motions 0x101 0x104 0x110 0x111, the same calls as 4U 0x8d6e04) and its
 * 3/0 0xd3db20; they end through GU slot 248 where 4U calls 0x94dcbc (setTargetMode(1) + action (0, 3), stygian
 * notes/phase2-actions.md). C = confirmed in code, S = strong, G = guess.
 * - 4U 0x922b6c(this, h) = GU 0xbf0f4 (C: the same body: W+0x628 / 0x620 / 0x624 / 412 / 440 / 444 = rec+0x5bc /
 *   0x5b0 / 0x5b4 / 68 / 428 / 432: the record's height clamped to the ground, + h * speed factors in states 1 2 5 6).
 * - 4U 0x9165a4(this, angles, h) = rotateVel(this, angles, flags) + 0x922b6c(this, h) (C, two calls).
 * - h = W+0xab8 in 3/2: Monoblos' code only reads it, the framework's reset 0x91b7f8 stores 0.0 there (0x91d568) and
 *   the other writers are flying monsters' classes (4U Rathian 0x6ed0bc ..): 0.0 for him (S).
 * - 3/1 3/2 3/3 start with `if (this+68 < W+0xab8) this+68 = W+0xab8`: an object field whose GU place is not found,
 *   and GU's versions of these handlers have no such clamp: left out (G; with W+0xab8 = 0.0 it only keeps this+68
 *   from going negative).
 * - 4U 0x93cda8 / 0x93ce98 = GU 0x7cc08 / 0x7cd60 (S: GU's fall handler calls them at the same places).
 * - 4U 0x90e4d8 zeroes velocity W+352..360 and acceleration W+368..376 = GU stopMove (rec+0x10..0x18, 0x20..0x28, S).
 * - controlled test (local index == owner W+0x1da) = GU this+0x7420 (game.h EN_CONTROLLED, S). */
#include "em007_01.h"

typedef int (*groundClamp_t)(void *self, float h);
#define groundClamp  FN(groundClamp_t, 0xbf0f4)     /* [0x922b6c] */
typedef void (*selfOnly_t)(void *self);
#define fallStart    FN(selfOnly_t, 0x7cc08)        /* [0x93cda8] */
#define fallStep     FN(selfOnly_t, 0x7cd60)        /* [0x93ce98] */
#define REC_VEL_Y    (REC_VEL + 4)                  /* [4U W+356] */
#define REC_VEL_Z    (REC_VEL + 8)                  /* [4U W+360] */
#define REC_POS_Y    (REC_POS_X + 4)                /* [4U W+412] */

static inline void end_to_3(void *self) { VCALL0(self, SLOT_ACTION_END_3); }       /* [0x94dcbc] */

static inline float vsqrt(float d)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

/* 4U 0x9165a4 */
static int turn_vel_clamp(void *self, const uint32_t *angles, uint32_t flags, float h)
{
    rotateVel(self, angles, flags);
    return groundClamp(self, h);
}

/* ---- 3/1: the 4U sub-dispatcher 0x8d9688's case 1 (0x8d96e4): motion 0x101, turn to the target (step 128), the end
 * (0, 3) when facing it */
void mbmv_3_1(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 1);
        setMotion(self, 0x101, 6.0f, 0.0f);
    } else if (rec[REC_STEP0] == 1) {
        if (turnToTarget(self, 128, 0)) end_to_3(self);
    }
}

/* ---- 3/2: 4U 0x8d6a74, the climb toward the target: motion 0x101, speed z at least 5 and up speed 10, the timer =
 * distance / speed (on the controlling machine), the velocity turned toward the target each frame with the height
 * clamp; the end (0, 3) at the timer or 1000 above the target slot */
void mbmv_8d6a74(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 1);
        restApply(self, restValue(self));
        setMotion(self, 0x101, 6.0f, 0.0f);
        stopMove(self);
        if (RF(rec, REC_VEL_Z) <= 0.0f) RF(rec, REC_VEL_Z) = 5.0f;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) {
            const float *t = &RF(rec, REC_TARGET), *pos = &RF(rec, REC_POS_X);
            float dx = t[0] - pos[0], dy = t[1] - pos[1], dz = t[2] - pos[2], d = dx * dx;
            d += dy * dy;
            d += dz * dz;
            RF(rec, REC_TIMER) = (float)(int32_t)(vsqrt(d) / RF(rec, REC_VEL_Z));
        }
        RF(rec, REC_VEL_Y) = 10.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    {   /* 4U work+0x1c / 0x20 / 0x24 = (0, angle, 0): cleared at step 0, the angle every frame (a local triple, S) */
        const float *t = &RF(rec, REC_TARGET), *pos = &RF(rec, REC_POS_X);
        uint32_t tri[3] = {0, atan_u16(t[0] - pos[0], t[2] - pos[2]), 0};
        turn_vel_clamp(self, tri, 0, 0.0f);
    }
    if (!timerDown(self, &RF(rec, REC_TIMER), 1.0f) &&
        RF(rec, REC_POS_Y) < RF(rec, REC_TARGET + 4) + 1000.0f) return;
    stopMove(self);
    end_to_3(self);
}

/* ---- 3/3: 4U 0x8d6c80, the walk to the target (motion 0x101 looped, speed 10, timer = 3 x xz distance / speed): turn
 * (step 128), the velocity turned by his own angles with the height clamp; the end (0, 3) at the timer or within 200 */
void mbmv_8d6c80(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    const float *t, *pos;
    float dx, dz, d;
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        restApply(self, restValue(self));
        setMotionLoop(self, 0x101, 6.0f, 0.0f);
        stopMove(self);
        RF(rec, REC_VEL_Z) = 10.0f;
        t = &RF(rec, REC_TARGET);
        pos = &RF(rec, REC_POS_X);
        dx = t[0] - pos[0];
        dz = t[2] - pos[2];
        d = dx * dx;
        d += 0.0f;
        d += dz * dz;
        RF(rec, REC_TIMER) = vsqrt(d) / RF(rec, REC_VEL_Z) * 3.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    turnToTarget(self, 128, 0);
    turn_vel_clamp(self, &RU(rec, REC_ANGLES), 1, restValue(self));
    t = &RF(rec, REC_TARGET);
    pos = &RF(rec, REC_POS_X);
    dx = t[0] - pos[0];
    dz = t[2] - pos[2];
    d = dx * dx;
    d += 0.0f;
    d += dz * dz;
    d = vsqrt(d);
    if (timerDown(self, &RF(rec, REC_TIMER), 1.0f) || !(d > 200.0f)) end_to_3(self);
}

/* ---- 3/4: 4U 0x8d6e04, fall and land: motion 0x101 with the fall start, the fall until the height clamp lands him,
 * then 0x104, 0x110 and 0x111 (target mode 0), the end with the last */
void mbmv_8d6e04(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        restApply(self, restValue(self));
        setMotion(self, 0x101, 6.0f, 0.0f);
        fallStart(self);
        return;
    case 1:
        fallStep(self);
        if (groundClamp(self, restValue(self))) {
            rec[REC_STEP0]++;
            setMotion(self, 0x104, 6.0f, 0.0f);
        }
        return;
    case 2:
        groundClamp(self, restValue(self));
        if (isMotionEnd(self)) {
            rec[REC_STEP0]++;
            setMotion(self, 0x110, 6.0f, 0.0f);
        }
        return;
    case 3:
        groundClamp(self, restValue(self));
        if (isMotionEnd(self)) {
            rec[REC_STEP0]++;
            setTargetMode(self, 0);
            setMotion(self, 0x111, 0.0f, 0.0f);
        }
        return;
    case 4:
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}
