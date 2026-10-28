/* em057_01_mv_a.c: Stygian Zinogre, ported 4U uEm048 handlers, batch A (turns, backstep, 7/4 7/5, 7/14 7/15).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case. Each handler is a literal translation of the 4U function
 * named in its comment (MH4U v1.1, dump/mh4u.asm), in 4U call order with 4U frame / timer / angle values; em==49
 * branches take the Stygian side (phase1-variant-map.md). Verdicts and parameters: notes/phase2-actions.md 2.
 * C = confirmed in code, S = strong, G = guess.
 *
 * 4U -> GU (C unless marked; "site" = GU's look-alike handler does the same call at the same place):
 * - step bytes W+0x144 / 0x145 = rec+0x1a1 / 0x1a2; velocity W+352 = rec+0x10, position W+408 = rec+0x40, yaw
 *   W+0x1ac = rec+0x54, target slot W+536 = rec+0x1d0 (sites ef7108 efa240), vec4 W+392 = rec+0x30 and motion
 *   speed multiplier W+0x410 = rec+0x398 (sites ef7588 efa38c f003f8), dt this+20 = this+28.
 * - work = [this+0x8d88] = [this+0xcac0], same offsets: +0x18 angle to the target, +0x1c signed turn, +0x20 xz
 *   distance, +0x30 backstep yaw rate (sites ef7108 ef7588 efa240).
 * - layer-0 motion speed this+668 = getter 0xb09bc (this+0x50c); helpers below with their 4U addresses.
 * - 4U setActionNext 0x94ef9c = GU 0x76984 (same body: category-11 guard, controller test, else the pending action
 *   this+0x73e5..7 for the network). chain() calls it plainly, as GU's own uEm057_00 chains (ef4d58, efaf7c, and
 *   f0031c through slot 244 = b 0x76984); the Gogmazios busy() block belongs to its own think override.
 * - vt+0x164 (end of action) = slot 247.
 * None of these handlers posts a sound, shell or effect in 4U (C: no 0x2fcc50 / 0x662904 / 0x6639a0 call). */
#include "em057_01.h"

/* tail shared by 0x845fe8 / 0x8499bc: vel.y = 0, velocity turned by ang (0xaad5b0), pos += vel * dt */
static void move_turned(void *self, uint32_t ang)
{
    uint8_t *rec = REC(self);
    float *v = &RF(rec, REC_VEL), *pos = &RF(rec, REC_POS_X), dt = FIELD(float, self, EN_DT);
    v[1] = 0.0f;
    rot_y(v, ang);
    pos[0] += v[0] * dt;
    pos[1] += v[1] * dt;
    pos[2] += v[2] * dt;
}

/* 4U step 0 of 0x845fe8 / 0x8499bc: angle to the target slot into work+0x18, motion by side, the turn into
 * work+0x1c (side 1: (angle - yaw) | 0xffff0000, i.e. turned the negative way; side 0: (angle - yaw) & 0xffff) */
static void turn_start(void *self, uint32_t side, uint32_t mot0, uint32_t mot1, float blend, float start)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    const float *pos = &RF(rec, REC_POS_X), *t = &RF(rec, REC_TARGET);
    uint32_t a = atan_u16(t[0] - pos[0], t[2] - pos[2]), d;
    RU(work, WK_ANG) = a;
    d = a - RU(rec, REC_YAW);
    if (side) {
        setMotion(self, mot1, blend, start);
        RU(work, WK_TURN) = d | 0xffff0000u;
    } else {
        setMotion(self, mot0, blend, start);
        RU(work, WK_TURN) = d & 0xffff;
    }
}

/* ---- 2/47-52 2/61-70: 4U 0x845fe8(side, next, mode): turn toward the target slot (motion 0x204 / 0x205) with a
 * backward slide, then 7/next at the motion end. mode 1 (2/63-70) = blend 10 / start 14, window 16-40. */
void szmv_845fe8(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = p[0], next = p[1], mode = p[2];
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        RF(work, WK_DIST) = dist_xz(&RF(rec, REC_POS_X), &RF(rec, REC_TARGET));
        if (mode == 1) turn_start(self, side, 0x204, 0x205, 10.0f, 14.0f);
        else turn_start(self, side, 0x204, 0x205, 4.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        stopMove(self);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    stopMove(self);
    float a = mode == 1 ? 16.0f : 10.0f, k = mode == 1 ? -12.5f : -10.0f;
    spinWindow(self, RU(work, WK_TURN), a, 40.0f);
    if (motionCheck(self, 3, 0, a, 40.0f)) {
        float v = motionSpeed(self) * k;
        RF(rec, REC_VEL + 8) = v * sizeFactor(self);
    }
    move_turned(self, RU(work, WK_ANG));
    if (isMotionEnd(self)) chain(self, 7, next);
}

/* ---- 2/72 2/73 2/75-77 2/79 2/80: 4U 0x84383c(move, cat, num, [sp] mode), from the 0x843d58 case stubs with
 * (1, 7, n, 0): backstep (motion 0x1c); move != 0: slide back with a yaw drift in the window 0 .. speed + 8; turn
 * to the target in 50-60; speed 0.8 from frame 60; then cat/num at frame 60 (7/31 32 34 61), 70 (7/200) or 80
 * (others); cat 0 ends at the motion end instead. */
void szmv_84383c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t move = p[0], cat = p[1], num = p[2], mode = p[3];
    float out = 0.0f;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (mode == 1) setMotion(self, 0x1c, 10.0f, 20.0f);
        else setMotion(self, 0x1c, 2.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.0f : 0.9f);
        stopMove(self);
        if (!move) return;
        RU(work, WK_ANG) = RU(rec, REC_YAW);
        float v = motionSpeed(self) * 26.5f;
        RF(rec, REC_VEL) = v * sizeFactor(self);
        RF(work, WK_RATE) = motionSpeed(self) * 3.5f;
        RF(rec, REC_V30) = RF(rec, REC_VEL);
        RF(rec, REC_V30 + 4) = RF(rec, REC_VEL + 4);
        RF(rec, REC_V30 + 8) = RF(rec, REC_VEL + 8);
        RF(rec, REC_V30 + 12) = 0.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (move && motionCheck(self, 9, &out, 0.0f, motionSpeed(self) + 8.0f)) {
        float dt = FIELD(float, self, EN_DT);
        uint32_t d = (uint32_t)(int32_t)(0.5f + RF(work, WK_RATE) * dt * (out * 65536.0f) * 0.0027777778f) & 0xffff;
        RU(rec, REC_YAW) = RU(rec, REC_YAW) - d;
        float v[4] = { RF(rec, REC_V30), RF(rec, REC_V30 + 4), RF(rec, REC_V30 + 8), 0.0f };
        rot_y(v, RU(work, WK_ANG));
        RF(rec, REC_VEL) = v[0] * out;
        RF(rec, REC_VEL + 4) = v[1] * out;
        RF(rec, REC_VEL + 8) = v[2] * out;
        const uint32_t ang[3] = { 0, RU(work, WK_ANG), 0 };
        rotateVel(self, ang, 1);
    }
    if (motionCheck(self, 9, &out, 50.0f, 60.0f))
        turnToTarget(self, (uint32_t)(int32_t)(0.5f + RF(rec, REC_MSPEED) * 4.0f * (out * 65536.0f) * 0.0027777778f)
                     & 0xffff, 0);
    if (motionCheck(self, 0, 0, 60.0f, 60.0f)) setMotionSpeed(self, 0.8f);
    if (cat == 0) {
        if (isMotionEnd(self)) end_action(self);
        return;
    }
    float f = 80.0f;
    if (cat == 7) {
        if (num == 31 || num == 32 || num == 34 || num == 61) f = 60.0f;
        else if (num == 200) f = 70.0f;
    }
    if (motionCheck(self, 1, 0, f, 0.0f)) chain(self, cat, num);
}

/* ---- 7/4 7/5: 4U 0x8499bc(side): turn toward the target slot (motion 0x20a / 0x20b, blend 4) in the window 18-40,
 * turn to the target from frame 42, backward slide in 18-42; at the motion end 7/20 if the motion is 0x20b, else
 * 7/21 (GU efa240 = the same with setActionW(2, 4) + think instead). r2 (7) is unused. */
void szmv_8499bc(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        turn_start(self, p[0], 0x20a, 0x20b, 4.0f, 0.0f);
        stopMove(self);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    spinWindow(self, RU(work, WK_TURN), 18.0f, 40.0f);
    if (motionCheck(self, 2, 0, 18.0f, 0.0f)) pin13a0(self);
    if (motionCheck(self, 1, 0, 42.0f, 0.0f))
        turnToTarget(self, (uint32_t)(int32_t)(0.5f + RF(rec, REC_MSPEED) * 182.04445f) & 0xffff, 0);
    stopMove(self);
    if (motionCheck(self, 3, 0, 18.0f, 42.0f)) {
        stopMove(self);
        float v = motionSpeed(self) * -23.75f;
        RF(rec, REC_VEL + 8) = v * sizeFactor(self);
    }
    move_turned(self, RU(work, WK_ANG));
    if (isMotionEnd(self)) chain(self, 7, curMotion(self) == 0x20b ? 20 : 21);
}

/* ---- 7/14: 4U 0x84a234: motion 0x1d (blend 4); turn to the target in the window 0-32 (out fraction x 1.5 deg);
 * when not blending: forward speed 28 (3.4 from frame 42) along the yaw; then 7/15. r1 r2 (14, 7) are unused. */
void szmv_84a234(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    float out = 0.0f;
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x1d, 4.0f, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 9, &out, 0.0f, 32.0f))
        turnToTarget(self, (uint32_t)(int32_t)(0.5f + out * 1.5f * 65536.0f * 0.0027777778f) & 0xffff, 0);
    stopMove(self);
    if (!blendActive(self)) {
        int late = motionCheck(self, 2, 0, 42.0f, 0.0f);
        float v = motionSpeed(self) * (late ? 3.4f : 28.0f), dt;
        RF(rec, REC_VEL + 8) = v * sizeFactor(self);
        rot_y(&RF(rec, REC_VEL), RU(rec, REC_YAW));
        RF(rec, REC_VEL + 4) = 0.0f;
        dt = FIELD(float, self, EN_DT);
        RF(rec, REC_POS_X) += RF(rec, REC_VEL) * dt;
        RF(rec, REC_POS_X + 4) += 0.0f * dt;                /* 4U adds its 0.0 constant x dt, not vel.y */
        RF(rec, REC_POS_X + 8) += RF(rec, REC_VEL + 8) * dt;
    }
    if (isMotionEnd(self)) chain(self, 7, 15);
}

/* ---- 7/15: 4U 0x84a444: motion 0x203, attack slot 0 index 55 (Stygian; 4U 0x84a4f8: em 48 / 114 -> 34), speed
 * 1.2 charged / 1.0; turn to the target every frame (speed x 1.5 deg); then 7/16. r1 r2 (15, 7) are unused. */
void szmv_84a444(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x203, 0.0f, 0.0f);
        attack(self, 0, 55);
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    turnToTarget(self, (uint32_t)(int32_t)(0.5f + RF(rec, REC_MSPEED) * 1.5f * 182.04445f) & 0xffff, 0);
    if (isMotionEnd(self)) chain(self, 7, 16);
}
