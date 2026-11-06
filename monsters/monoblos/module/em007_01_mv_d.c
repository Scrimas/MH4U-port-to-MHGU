/* em007_01_mv_d.c: Monoblos, ported 4U uEm101 handlers, batch D: walking, running and approaching (category 2).
 * Literal translations of the 4U functions named below (MH4U v1.1), run by em007_01_moves_run. They share the
 * charge's field map (em007_01_mv_a.c): work+1 = GU work+0 (WK_CHARGE), timer W+468 = rec+0x1bc, distance W+568 =
 * rec+0x1f0, the class helper 0x8defb0 = GU 0xd3c7bc (chargeTarget), layer-0 motion speed this+668 = GU 0xb09bc.
 * C = confirmed in code, S = strong, G = guess. */
#include "em007_01.h"

typedef float (*speedGet_t)(void *self);
#define motionSpeed  FN(speedGet_t, 0xb09bc)    /* [this+668] */
typedef int (*selfInt_t)(void *self);
#define slowState    FN(selfInt_t, 0x816d0)     /* [0x92e998] */

static inline float vsqrt(float d)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

/* W+568 = distance to target slot 0 (4U 0x8db54c's code, here inline in 0x8d81d0) */
static void target_dist(uint8_t *rec)
{
    const float *t = &RF(rec, REC_TARGET), *pos = &RF(rec, REC_POS_X);
    float dx = t[0] - pos[0], dy = t[1] - pos[1], dz = t[2] - pos[2], d = dx * dx;
    d += dy * dy;
    d += dz * dz;
    RF(rec, REC_TGT_DIST) = vsqrt(d);
}

/* the shared end test of the kind with a timer: target slot reached, timer out, or a hunter ahead (findTargetEx
 * range 4096, -1 = none) */
static int reached_or_timed(void *self, uint8_t *rec)
{
    if (inRange(self, 0, 64)) return 1;
    if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) return 1;
    return findTargetEx(self, 0, -1, 4096, 4) != -1;
}

/* 4U turn records (s32 blend / start -> GU floats, game.h seq_rec): 0xe0e090 = turn window 0..90, angle 0x4000,
 * straight angle 0x0e39, motions 0x0d / 0x09 / 0x0a; 0xe0e0d0 = window 2..20, angle 0x4000, straight angle 0x1555,
 * motions 0x0d / 0x0b / 0x0c */
static const seq_rec s_seq_e0e090 = {0.0f, 90.0f, 0.0f, 0x0e394000u,
                                     {{0x0d, 4.0f, 4.0f, 0}, {0x09, 10.0f, 0.0f, 0}, {0x0a, 10.0f, 0.0f, 0}}};
static const seq_rec s_seq_e0e0d0 = {2.0f, 20.0f, 0.0f, 0x15554000u,
                                     {{0x0d, 4.0f, 0.0f, 0}, {0x0b, 4.0f, 0.0f, 0}, {0x0c, 4.0f, 0.0f, 0}}};

/* ---- 2/3 2/5 2/17 2/24: the 4U sub-dispatcher 0x8dda24's inline turns (cases 3 / 5 / 17 / 24 at 0x8ddad4 /
 * 0x8ddb38 / 0x8ddc90 / 0x8ddd10): a turn sequence (2/3 and 2/24: record 0xe0e090, flags 1; 2/5 and 2/17: record
 * 0xe0e0d0, flags 0), the end when it is done; 2/24 first sets sleepFlagA every frame */
void mbmv_2_turn(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t big = p[0], flags = p[1];
    const seq_rec *seq = big ? &s_seq_e0e090 : &s_seq_e0e0d0;
    if (p[2]) sleepFlagA(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        seqStart1(self, seq, 0, flags, 0);
    } else if (rec[REC_STEP0] == 1) {
        if (seqPoll1(self, seq)) end_action(self);
    }
}

/* ---- 2/12 2/14 2/18: 4U 0x8d89d0(kind = r1 0..2), the stalk: motion 7 at speed 0.76 following the target (0x8da42c's
 * target rule into the slot every frame, the distance to the slot before the update into W+568), turning at
 * W+488 + 215 (kind 2: + 350) per frame, W+488 growing by 20 (kind 2: 50) at each motion end (kind 0: fixed); the end
 * under 700 or at the timer 300. W+488 has no GU field found (GU's motion-7 handler 0xd3eb74 is other code): it lives
 * in mb_state, as the charge's store before 2/13 */
void mbmv_8d89d0(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0];
    float t[3];
    struct mb_state *st = mb_state(self);
    mb_target_pos(self, t);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 7, 4.0f, 0.0f);
        setStopDist(self, 0, 0, 0.0f);
        RF(rec, REC_TIMER) = 300.0f;
        st->w488 = 0.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    setMotionSpeed(self, 0.76f);
    target_dist(rec);
    {
        float *slot = &RF(rec, REC_TARGET);
        slot[0] = t[0];
        slot[1] = t[1];
        slot[2] = t[2];
        slot[3] = 0.0f;
    }
    if (kind == 1) {
        turnToTarget(self, (uint32_t)(st->w488 + 215.0f) & 0xffff, 0);
        if (isMotionEnd(self)) st->w488 = st->w488 + 20.0f;
    } else if (kind == 2) {
        turnToTarget(self, (uint32_t)(st->w488 + 350.0f) & 0xffff, 0);
        if (isMotionEnd(self)) st->w488 = st->w488 + 50.0f;
    } else {
        turnToTarget(self, (uint32_t)(st->w488 + 215.0f) & 0xffff, 0);
    }
    inRange(self, 0, 0);                                    /* 4U calls it, result unused */
    if (RF(rec, REC_TGT_DIST) < 700.0f || timerDown(self, &RF(rec, REC_TIMER), 1.0f)) {
        rec[REC_STEP0]++;
        end_action(self);
    }
}

/* ---- 2/0 2/21 2/25 2/26: 4U 0x8d7d8c(kind = r1 0..3), the walk (motion 5): stop distance -500 (kind 3: -200; kind
 * 1 with a 600 timer), the charge's target check, end on reaching the slot (kind 1 also on the timer or a hunter
 * ahead) */
void mbmv_8d7d8c(void *self, const uint8_t *p)
{
    uint8_t *rec, *work = WORK(self);
    uint32_t kind = p[0];
    if (kind == 2) sleepFlagA(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        work[WK_CHARGE] = 1;
        setTargetMode(self, 0);
        setMotion(self, 5, 6.0f, 0.0f);
        if (kind == 3) {
            setStopDist(self, 0, 0, -200.0f);
            return;
        }
        setStopDist(self, 0, 0, -500.0f);
        if (kind == 1) RF(rec, REC_TIMER) = 600.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (kind != 1 && chargeTarget(self, 0)) return;
    work[WK_CHARGE] = 0;
    if (kind == 1 ? reached_or_timed(self, rec) : inRange(self, 0, 64)) end_action(self);
}

/* ---- 2/6 2/22: 4U 0x8d81d0(kind = r1 0 / 1), the run (motion 6): kind 0 stop distance 500 and the target distance,
 * kind 1 stop distance -300 with a 600 timer; ends as the walk */
void mbmv_8d81d0(void *self, const uint8_t *p)
{
    uint8_t *rec, *work = WORK(self);
    uint32_t kind = p[0];
    if (kind == 1) {
        sleepFlagA(self);
        sleepFlagB(self);
    }
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        work[WK_CHARGE] = 1;
        setTargetMode(self, 0);
        setMotion(self, 6, 10.0f, 0.0f);
        if (kind == 1) {
            setStopDist(self, 0, 0, -300.0f);
            RF(rec, REC_TIMER) = 600.0f;
            return;
        }
        setStopDist(self, 0, 0, 500.0f);
        target_dist(rec);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (kind != 1 && chargeTarget(self, 0)) return;
    work[WK_CHARGE] = 0;
    if (kind == 1 ? reached_or_timed(self, rec) : inRange(self, 0, 64)) end_action(self);
}

/* ---- 2/19 2/20 2/23: 4U 0x8d93c4(kind = r1 0..2), the approach (motion 7, speed 0.8 when slowed): stop distance 350
 * (kinds 1 / 2: -900; kind 2 with a 300 timer over the motion speed), then motion 8 and the end with it */
void mbmv_8d93c4(void *self, const uint8_t *p)
{
    uint8_t *rec, *work = WORK(self);
    uint32_t kind = p[0];
    int done;
    if (kind == 2) {
        sleepFlagA(self);
        sleepFlagB(self);
    }
    rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 7, 4.0f, 0.0f);
        if (slowState(self)) setMotionSpeed(self, 0.8f);
        if (kind == 1) {
            setStopDist(self, 0, 0, -900.0f);
        } else if (kind == 2) {
            setStopDist(self, 0, 0, -900.0f);
            RF(rec, REC_TIMER) = 300.0f;
            if (motionSpeed(self) != 0.0f) RF(rec, REC_TIMER) = RF(rec, REC_TIMER) / motionSpeed(self);
        } else {
            setStopDist(self, 0, 0, 350.0f);
        }
        return;
    case 1:
        if (kind != 2 && chargeTarget(self, 0)) return;
        work[WK_CHARGE] = 0;
        done = kind == 2 ? reached_or_timed(self, rec) : inRange(self, 0, 64);
        if (!done) return;
        rec[REC_STEP0]++;
        setMotion(self, 8, 4.0f, 0.0f);
        if (slowState(self)) setMotionSpeed(self, 0.8f);
        return;
    case 2:
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}
