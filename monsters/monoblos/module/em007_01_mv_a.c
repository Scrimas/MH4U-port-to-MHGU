/* em007_01_mv_a.c: Monoblos, ported 4U uEm101 handlers, batch A: the horn charge and the stuck horn.
 * Run by em007_01_moves_run (em007_01_moves.c, s_moves rows with the 4U sub-dispatcher's parameters in p[]). Each
 * handler is a literal translation of the 4U function named in its comment (MH4U v1.1, dump/mh4u.asm), in 4U call
 * order with 4U frames, timers and attack indexes (his own records: MB_ATK). GU's own Diablos charge 0xd430a8 is the
 * GU version of the same handler (same steps, motions 0x20f / 0x210, attack parameters, timers and helper calls; GU
 * dropped 4U's cases 4 and 8 and added a Bloodbath speed factor and a stage-19 attack flag), so its field offsets and
 * helper calls are the evidence for the 4U -> GU map (em007_01.h). C = confirmed in code, S = strong, G = guess.
 * - step byte W+0x144 = rec+0x1a1 (C), timer W+468 = rec+0x1bc, target slot W+536 = rec+0x1d0 and position W+408 =
 *   rec+0x40 (C: GU d43574..d435c4 reads them for the same distance), angles W+424 = rec+0x50 (C: GU d432a8).
 * - 4U timerDown 0xb0709c(this, &t) subtracts dt; GU's 0x72128 takes a scale, 1.0 at GU's twin sites (C).
 * - 4U setStopDist 0x92dc88(this, flags, s0) leaves r2 unset; GU's 0x78b88 reads r2 as an extra byte, 0 at GU's twin
 *   sites (C). */
#include "em007_01.h"

static inline float vsqrt(float d)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

/* 4U class 0x8e02c8(this, slot): the horn's wall-hit feedback when the local player is in his area and attack slot
 * `slot` is not flagged. 4U posts 0xbfef9c(mgr *0x105729c, 7, pos); GU's charge makes the same two tests and posts
 * its rumble 0x19148(mgr, 7, 4096, 0, 0) instead (GU d433c4..d43408): GU's form is kept (S). */
static void wall_hit_feedback(void *self, uint32_t slot)
{
    uint8_t *rec = REC(self);
    if (FIELD(uint8_t, self, EN_AREA) != playerArea()) return;
    if (slot >= 2) return;
    if (rec[REC_ATK0_STATE + 184 * slot] & 1) return;      /* GU attack slots are 184 bytes (4U 152) */
    rumble(RUMBLE_MGR, 7, 4096, 0, 0);
}

/* ---- 7/3 7/10 7/24 7/25 7/34: 4U 0x8db41c(kind = r1: 0 / 1 / 4 / 5 / 8). Step 0 sets up the run (motion 0x20f,
 * timer 300 or 180, kinds 3 / 5..7 with an attack from the first frame and a capped motion speed), step 1 runs until
 * the target slot is reached (inRange) or the timer ends: on a wall (0x8d750c) the horn sticks (1/2, kind 8: 6/14),
 * else the brake (motion 0x210, step 2) or kind 1's think / kind 4's 2/13; step 2 ends with the motion. */
void mbmv_8db41c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t kind = p[0];
    uint32_t step = rec[REC_STEP0];
    if (step == 0) {
        int capped = 0, stop = 1;
        rec[REC_STEP0] = 1;
        work[WK_CHARGE] = 1;
        setTargetMode(self, 0);
        RF(rec, REC_TIMER) = 300.0f;
        switch (kind) {                                     /* 4U jump table 0x8db4c8 */
        case 1:
            setMotion(self, 0x20f, 6.0f, 0.0f);
            break;
        case 3:
            setMotion(self, 0x20f, 6.0f, 116.0f);
            attackEx(self, 0, MB_ATK(47), 154);
            break;
        case 4:
            setMotion(self, 0x20f, 10.0f, 10.0f);
            break;
        case 5:
            rootMove(self, 0x418, &RU(rec, REC_ANGLES), ROOT_MOVE_OFFSET);
            setMotion(self, 0x20f, 0.0f, 114.0f);
            attackEx(self, 0, MB_ATK(48), 154);
            capped = 1;
            break;
        case 6:
            setMotion(self, 0x20f, 4.0f, 150.0f);
            attackEx(self, 0, MB_ATK(48), 138);
            capped = 1;
            break;
        case 7:
            setMotion(self, 0x20f, 4.0f, 120.0f);
            attackEx(self, 0, MB_ATK(49), 138);
            capped = 1;
            break;
        default:                                            /* 0, 2, 8.. (0x8db508) */
            setMotion(self, 0x20f, 6.0f, 0.0f);
            if (kind == 8) RF(rec, REC_TIMER) = 180.0f;
            else if (kind == 2) stop = 0;
            break;
        }
        if (capped) {                                       /* 0x8db68c */
            float s = layerSpeed(self), m = 1.4f;
            if (s * 1.4f > 1.7f) m = 1.7f / s;
            setMotionSpeed(self, m);
            setStopDist(self, 0, 0, 0.0f);
        } else if (stop) {
            setStopDist(self, 0, 0, 500.0f);
        }
        {                                                   /* 0x8db54c */
            const float *t = &RF(rec, REC_TARGET), *pos = &RF(rec, REC_POS_X);
            float dx = t[0] - pos[0], dy = t[1] - pos[1], dz = t[2] - pos[2], d = dx * dx;
            d += dy * dy;
            d += dz * dz;
            RF(rec, REC_TGT_DIST) = vsqrt(d);
        }
        return;
    }
    if (step == 2) {
        if (isMotionEnd(self)) end_action(self);
        return;
    }
    if (step != 1) return;
    if (chargeTarget(self, kind == 8 ? 1 : 0)) return;      /* 0x8defb0 acted (3/7) */
    work[WK_CHARGE] = 0;
    uint32_t near = 64;
    int done;
    if (kind == 4) {
        if (motionCheckB(self, 1, 0, 85.0f, 0.0f)) attackEx(self, 0, MB_ATK(14), 136);
    } else if (kind >= 5 && kind <= 7) {
        for (uint32_t i = 0; i < 2; i++) wanderPoint(self, 0, i);
        near = 20;
    }
    if (kind == 8) done = 0;
    else done = inRange(self, 0, near);
    if (!done) done = timerDown(self, &RF(rec, REC_TIMER), 1.0f);
    if (done) {                                             /* 0x8db844 */
        rec[REC_STEP0]++;
        if (kind == 1) {
            rec[REC_STEP0]++;
            thinkRequest(self, 0);
        } else if (kind == 4) {
            mb_state(self)->w488 = 1.0f;
            mb_chain_now(self, 2, 13);
        } else {
            setMotion(self, 0x210, 4.0f, 0.0f);
        }
        return;
    }
    if (kind == 8 && wallCheck(self, 1024, 8192)) {         /* 0x8db8c8 */
        wall_hit_feedback(self, 0);
        attackFlag(self, 0);
        mb_chain(self, 6, 14);
        return;
    }
    if (!motionCheck(self, 1, 0, 90.0f, 0.0f) || kind == 8) return;
    if (wallCheck(self, 128, 4096)) {
        wall_hit_feedback(self, 0);
        attackFlag(self, 0);
        mb_chain(self, 1, 2);
    }
}

/* ---- 2/2: 4U 0x8d7f08, the charge run without a timer (motion 0x20f, stop distance -500): ends on reaching the
 * target slot; from frame 90 a wall sticks the horn (1/2) */
void mbmv_8d7f08(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x20f, 6.0f, 0.0f);
        setStopDist(self, 0, 0, -500.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (inRange(self, 0, 64)) {
        end_action(self);
        return;
    }
    if (motionCheck(self, 1, 0, 90.0f, 0.0f) && wallCheck(self, 128, 4096)) {
        wall_hit_feedback(self, 0);
        attackFlag(self, 0);
        mb_chain(self, 1, 2);
    }
}

/* ---- 2/10: 4U 0x8d8518, the fast charge run (motion 0x20f at speed 1.5, stop distance -400, timer 360): the brake
 * 0x210 on reaching the slot or at the timer, a wall from frame 90 sticks the horn (1/2), else the charge's target
 * check every frame (0x8defb0) */
void mbmv_8d8518(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    (void)p;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        work[WK_CHARGE] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x20f, 6.0f, 0.0f);
        setMotionSpeed(self, 1.5f);
        setStopDist(self, 0, 0, -400.0f);
        RF(rec, REC_TIMER) = 360.0f;
        return;
    case 1:
        if (inRange(self, 0, 64) || timerDown(self, &RF(rec, REC_TIMER), 1.0f)) {
            rec[REC_STEP0]++;
            setMotion(self, 0x210, 4.0f, 0.0f);
        } else if (motionCheck(self, 1, 0, 90.0f, 0.0f) && wallCheck(self, 128, 4096)) {
            wall_hit_feedback(self, 0);
            attackFlag(self, 0);
            mb_chain(self, 1, 2);
            return;
        }
        if (chargeTarget(self, 0)) return;                  /* 0x8d86b8 */
        work[WK_CHARGE] = 0;
        return;
    case 2:
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 7/4 7/21: 4U 0x8db998(kind = r1 0 / 1), the charge run into a horn thrust: motion 0x20f (kind 1 from frame
 * 10), stop distance -500, the target distance; on reaching the slot the thrust 0x213 with attack 16 at frame 50;
 * from frame 90 a wall sticks the horn (1/2) */
void mbmv_8db998(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    switch (rec[REC_STEP0]) {
    case 0: {
        const float *t, *pos;
        float dx, dy, dz, d;
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (kind == 1) setMotion(self, 0x20f, 10.0f, 10.0f);
        else setMotion(self, 0x20f, 6.0f, 0.0f);
        setStopDist(self, 0, 0, -500.0f);
        t = &RF(rec, REC_TARGET);
        pos = &RF(rec, REC_POS_X);
        dx = t[0] - pos[0];
        dy = t[1] - pos[1];
        dz = t[2] - pos[2];
        d = dx * dx;
        d += dy * dy;
        d += dz * dz;
        RF(rec, REC_TGT_DIST) = vsqrt(d);
        return;
    }
    case 1:
        if (inRange(self, 0, 64)) {
            rec[REC_STEP0]++;
            setMotion(self, 0x213, 6.0f, 0.0f);
            return;
        }
        if (motionCheck(self, 1, 0, 90.0f, 0.0f) && wallCheck(self, 128, 4096)) {
            wall_hit_feedback(self, 0);
            attackFlag(self, 0);
            mb_chain(self, 1, 2);
        }
        return;
    case 2:
        if (motionCheckB(self, 0, 0, 50.0f, 0.0f)) attackEx(self, 0, MB_ATK(16), 8);
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 1/2: 4U 0x8d9af8, the stuck horn (motion 0x317, timer 480): attack 40 and an item drop (100 %), then until the
 * timer ends the hunter scan (0x8e0d34) keeps him there, else he pulls out (1/27); at the timer the struggle motion
 * 0x318 with attack 58 at frame 74, end with the motion. Parameters unused. */
void mbmv_8d9af8(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        RF(rec, REC_TIMER) = 480.0f;
        setMotion(self, 0x317, 6.0f, 0.0f);
        return;
    case 1:
        attack(self, 0, MB_ATK(40));
        enemyDrop(self, &RF(rec, REC_POS_X), 100, 0);
        rec[REC_STEP0]++;
        /* fall through: 4U runs the step-2 code in the same frame (0x8d9c0c) */
    case 2:
        if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) {
            rec[REC_STEP0]++;
            setMotion(self, 0x318, 0.0f, 0.0f);
        } else if (stuckScan(self, 0) == 0) {
            mb_chain(self, 1, 27);
        }
        return;
    case 3:
        if (motionCheck(self, 0, 0, 74.0f, 0.0f)) attackEx(self, 0, MB_ATK(58), 193);
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 1/27: 4U sub-dispatcher 0x8ddf24 case 27 (0x8de710): the horn pulled out, motion 0x301, end with it */
void mbmv_1_27(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x301, 2.0f, 0.0f);
    } else if (rec[REC_STEP0] == 1) {
        if (isMotionEnd(self)) end_action(self);
    }
}
