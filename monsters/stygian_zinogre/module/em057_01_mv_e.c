/* em057_01_mv_e.c: Stygian Zinogre, ported 4U uEm048 handlers, batch E (PORT-chain: the leap 7/205 7/209, the lunge
 * 7/192-197 7/204, the hop back 7/203 7/206, the rest walk 13/3).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case (GU 7/205 = effc00(0, 1) and 7/209 = effc00(1, 0): follow-up 2/4
 * / none, 7/209 also starts at blend 14 / frame 60; 7/192-197 no case, end at once; 7/204 = efeb30(1, 1): 2/4 and no
 * setMotion for variant != 4; 7/203 = efc6cc(1, 2), 7/206 = efc6cc(2, 1): 2/4; 13/3 = f02f24: 13/5 or 2/10). Each
 * handler is a literal translation of the 4U function named in its comment (MH4U v1.1, dump/mh4u.asm), in 4U call order
 * with 4U frame / timer / angle values. None of them tests the em byte (C: no W+0x1c0 read in the four handlers nor in
 * the reached paths of 0x855c38 / 0x852d74), so there is no em==49 branch. Verdicts and parameters:
 * notes/phase2-actions.md 2. C = confirmed in code, S = strong, G = guess.
 * Parameters (C, 4U stubs of the cat-7 sub-dispatcher 0x851494, table 0x8514ac, and case.py 4u 49): 7/192-197 ->
 * 0x8525ec..0x85263c = 0x84bad8(cat, num) = (7, 198) (2, 71) (2, 63) (2, 65) (2, 67) (2, 69); 7/204 -> 0x85269c =
 * 0x84bad8(7, 203); 7/203 -> 0x85268c = 0x84d488(1, 1); 7/206 -> 0x8526bc = 0x84d488(2, 2); 7/205 / 7/209 -> 0x8526ac /
 * 0x8526ec = 0x84a59c(0, 4) / (0, 5); 13/3 -> 0x84ea40 (inside the cat-13 handler 0x84e7d0) = 0x842b44 with r1 = 3,
 * which it never reads. No handler reads [sp] (their [sp] is their own out float / vector).
 *
 * 4U -> GU, beyond the batch A-D lists ("site" = GU's look-alike handler does the same call at the same place: effc00
 * for 0x84a59c, efeb30 for 0x84bad8, efa7e0 for 0x855c38, efc6cc for 0x84d488, f02f24 for 0x842b44):
 * - 0x94461c(this, joint, ang) = GU 0xb0eb0(self, joint, ang, scale) (C: site effd98, same joint 0x263 and u16 yaw;
 *   same body: the joint's position at the layer-0 frame +76 minus at +80 (4U 0x936960: this+652 / 656 = GU this+0x4fc /
 *   0x500), turned by ang, times the size factor (4U W+440 * W+444 = GU 0xbe5d4), added to the position). scale is
 *   GU-only (a per-axis factor): all 68 GU callers pass main+0x191e860 (GOT slot 0x1839bdc, bss; GU 0xad204 copies it as
 *   a scale with w = 1.0), so {1, 1, 1} (S; logged once at the first use).
 * - work+0x44..0x4c = the angle triple rec+0x50..0x58 at the jump (C: site f000c0..f000c8, same offsets).
 * - class 0x855c38 = lunge_855c38 below (GU efa7e0, C: site efee14 with the same 8 arguments 40 58 dist 0 600 0 160; same
 *   body except GU's vmin clamp for 4U's integer-bit compare with 1.0f, and the float association).
 * - 0x84bad8: setMotion efec50, attackEx efec8c (0, 17, 8) / efecc0 (1, 18, 24), questRank efec20 (< 4: x 3, else x 5),
 *   the frame-30 distance / angle efed58..efeddc (inline sqrt / atan2), follow-up window mc 1 80 efee34 (C).
 * - 0x84d488: setMotion efc8ac, attack 0x7df94 efc8f0 (0, 24), stopMove tail efc910, approach tails efca04 (/ 20, / 30)
 *   and efc7f8 (-1200 -2000..500 / 16), turnToTarget efca34 with the offset 32000 (efca28), mc 0 40 -> 0.95 efc764 (C).
 * - 0x84a59c: restApply(254) effd34, sleepFlagB effd3c effd7c, the jump velocity (-9.0322, 0, 120.5111) f00084 f00094 +
 *   rotateVel f000a4, mc 1 18 effdb0, the fall (accel y -1, vel y -8, z 25) effde8..effe04 + accelVel effe18, landCheck
 *   (298) effe24, slowState 0x20d / 0x209 effe58, atFrame 26 -> attackFlag effecc, attackEx(0, 9, 3) f00040 (C).
 * - 0x842b44: 0x922cd8 = sleepFlagA (site f02f54); W+0x3e4 = rec+0x36c (C: site f02f68, both = 1 every frame); 0x936ac0
 *   = GU 0xc43bc (C: site f02fd8 with the same arguments (this, &pos, &u16 angle, 336.0); same body shape: angle to the
 *   target slot into *angle, the +-90 degree test on angle - yaw, size factor x distance); 0x92d0d4(this, pos, 0) = GU
 *   0xc46c8(self, pos, 0) (C: site f02ffc; S: apimap2 99 votes; game.h wanderPoint, here given a position);
 *   0x911c44 / 0x92f720 = seqStart1 / seqPoll1 (C: game.h, sites f0301c f030a4); the 4U turn table 0xe0d06c = GU
 *   0x16a639c (C: same 64 bytes, GU blend / start as floats), kept as k_seq_e0d06c; 0x916260 = resetVel (site f03024);
 *   this+668 = motionSpeed (site f03034); 0xb0709c(&W+468) = timerDown(&timer, 1.0) (site f030f8); W+0x1d9 ==
 *   1 -> EN_CONTROLLED == 1 (GU f03114 tests != 0).
 * - class 0x852d74(this, 0) (G, logged): 4U's reached path is obj = 0x930124(this, 0, 0, 1) (the object with id W+0x1c4,
 *   in this area, not in category 12, category 11 only as 11/8 / 11/9 and 14 only as 14/1); obj ? 0x92e334(obj) (obj in
 *   11/8, 11/9 or 14/1) : 0x94bd6c(this, &pos) (a type-6, state-5 map object listed for this em in this area). GU has no
 *   counterpart of these three (none in apimap / apimap2 / monster_fn_pairs); f02f24 calls GU 0xb2ddc(self) at this site
 *   (f03124) with the same use (1 -> the 13/x follow-up, else 2/10). 0xb2ddc checks GU's own target (u16 id this+0x7416,
 *   area this+0x73fb, kept by GU's 13/1 13/2 handlers, which run: KEEP): an enemy in 14/1, 11/8 or 11/9 -> 1, a map
 *   record with +8 != 0 and +0xb == 6 -> 1, other states -> 0, no target -> 1 (4U: no partner and no map object -> 0;
 *   4U falls back to the map objects when the partner is in category 12, GU returns 0).
 * No sound, shell or effect post in these handlers (C: no 0x2fcc50 / 0x662904 / 0x6629bc / 0x6639a0 / 0x6620c4 call). */
#include "em057_01.h"

/* GU callees and fields used only here */
typedef void (*jointShift_t)(void *self, uint32_t joint, uint32_t ang, const float *scale);
#define jointShift  FN(jointShift_t, 0xb0eb0)   /* [0x94461c(this, joint, ang)] */
#define SHIFT_SCALE ((const float *)MAIN(0x191e860))    /* its scale (GOT slot 0x1839bdc), S: {1, 1, 1} */
typedef void (*restPoint_t)(void *self, float *pos, uint16_t *ang, float dist);
#define restPoint   FN(restPoint_t, 0xc43bc)    /* [0x936ac0] */
typedef void (*movePoint_t)(void *self, const float *pos, uint32_t slot);
#define movePoint   FN(movePoint_t, 0xc46c8)    /* [0x92d0d4] = game.h wanderPoint: its 0xc4ba8 copies a non-null pos
                                                   into the slot (C), null = a random point */
#define restTarget  FN(selfInt_t, 0xb2ddc)      /* GU's check at the site of [class 0x852d74(this, 0)] (G) */
#define WK_ANG44    0x44    /* u32 x3: the angle triple at the jump [4U work+0x44..0x4c] */
#define REC_REST36C 0x36c   /* u8, 1 every frame of 13/3 [4U W+0x3e4] */

/* 4U turn table 0xe0d06c (GU 0x16a639c): turn in 0-38 by at most 180 degrees, motion 0x222 both ways (straight: motion
 * 0), blend 4 */
static const seq_rec k_seq_e0d06c = {0.0f, 38.0f, 0.0f, 0x00008000,
                                     {{0, 4.0f, 0.0f, 0}, {0x222, 4.0f, 0.0f, 0}, {0x222, 4.0f, 0.0f, 0}}};

/* 4U 0x94461c(this, joint, ang) through GU 0xb0eb0; logs the GU scale vector once (x 1000) */
static void joint_shift(void *self, uint32_t joint, uint32_t ang)
{
    static uint8_t s_logged;
    const float *k = SHIFT_SCALE;
    if (!s_logged) {
        s_logged = 1;
        logf("szport: 7/205 0xb0eb0 scale %d %d %d x1000 (S: expect 1000 1000 1000)", (int32_t)(k[0] * 1000.0f),
             (int32_t)(k[1] * 1000.0f), (int32_t)(k[2] * 1000.0f));
    }
    jointShift(self, joint, ang, k);
}

/* ---- 7/205 7/209: 4U 0x84a59c(r1, r2): leap. Motion 0x20c (r2 0: blend 4 / frame 46, 3: 14 / 60, else 4 / 0), speed
 * 1.2 charged, attack slot 0 index 9 with param 3; turn in 0-24 (x 2) while the motion is 0x20c; at its end the jump
 * (0x208, restApply 254, velocity (-9.0322, 0, 120.5111) turned by the angles, which work+0x44 keeps, speed 1.25
 * charged); from frame 18 the root motion of joint 0x263 and the fall (vel y -8, z 25, accel y -1) until landed (298);
 * the landing 0x20d (slow state) / 0x209; attack slot 0 reset at frame 26; then by r2: 2 -> 7/4 (r1 != 0) / 7/5 from
 * frame 70, 4 -> 7/206 from frame 68, 5 -> 7/210 from frame 68, else the end of the action at the motion end. */
void szmv_84a59c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t r1 = p[0], r2 = p[1];
    float out = 0.0f;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        if (r2 == 1 || r2 == 2 || r2 == 4 || r2 == 5) setMotion(self, 0x20c, 4.0f, 0.0f);
        else if (r2 == 3) setMotion(self, 0x20c, 14.0f, 60.0f);
        else setMotion(self, 0x20c, 4.0f, 46.0f);
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        attackEx(self, 0, 9, 3);
        return;
    case 1:
        if (curMotion(self) == 0x20c && motionCheck(self, 9, &out, 0.0f, 24.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 2.0f * (out * 65536.0f) * 0.0027777778f), 0);
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        stopMove(self);
        setMotion(self, 0x208, 0.0f, 0.0f);
        restApply(self, 254.0f);
        sleepFlagB(self);
        setMotionSpeed(self, isCharged(self) ? 1.25f : 1.0f);
        RF(rec, REC_VEL) = -9.03219986f;
        RF(rec, REC_VEL + 8) = 120.511101f;
        rotateVel(self, &RU(rec, REC_ANGLES), 0);
        RU(work, WK_ANG44) = RU(rec, REC_ANGLES);
        RU(work, WK_ANG44 + 4) = RU(rec, REC_ANGLES + 4);
        RU(work, WK_ANG44 + 8) = RU(rec, REC_ANGLES + 8);
        return;
    case 2: {
        sleepFlagB(self);
        joint_shift(self, 0x263, RU(rec, REC_YAW) & 0xffff);
        if (!motionCheck(self, 1, 0, 18.0f, 0.0f)) return;
        uint8_t s1 = rec[REC_STEP1];
        if (s1 == 0) {
            rec[REC_STEP1] = 1;
            RF(rec, REC_ACCEL_Y) = -1.0f;
            RF(rec, REC_VEL + 4) = -8.0f;
            RF(rec, REC_VEL + 8) = 25.0f;
        }
        if (s1 == 0 || s1 == 1) accelVel(self, &RU(rec, REC_ANGLES), 0);
        if (!landCheck(self, 298.0f)) return;
        rec[REC_STEP0]++;
        stopMove(self);
        setTargetMode(self, 0);
        setMotion(self, slowState(self) ? 0x20d : 0x209, 0.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.25f : 1.0f);
        return;
    }
    case 3:
        if (atFrame(self, 26.0f)) attackFlag(self, 0);
        if (r2 == 2) {
            if (motionCheck(self, 1, 0, 70.0f, 0.0f)) chain(self, 7, r1 ? 4 : 5);
        } else if (r2 == 4) {
            if (motionCheck(self, 1, 0, 68.0f, 0.0f)) chain(self, 7, 206);
        } else if (r2 == 5) {
            if (motionCheck(self, 1, 0, 68.0f, 0.0f)) chain(self, 7, 210);
        } else if (isMotionEnd(self)) {
            setTargetMode(self, 0);
            end_action(self);
        }
        return;
    default:
        return;
    }
}

/* 4U class helper 0x855c38(this, ang, a, b, dist, lo, hi, vmin, vmax), whole: in the motion window a..b (mode 9, step
 * fraction out) and when dist >= lo: stopMove, forward speed (vmin + (vmax - vmin) * t) / ((b - a) / 2) with t = (dist -
 * lo) / (hi - lo), at most 1, turned by ang; position x / z += vel * dt * size factor * out */
static void lunge_855c38(void *self, uint32_t ang, float a, float b, float dist, float lo, float hi, float vmin,
                         float vmax)
{
    uint8_t *rec = REC(self);
    float out = 0.0f, k;
    union { float f; int32_t i; } t;
    if (!motionCheck(self, 9, &out, a, b)) return;
    if (!(lo <= dist)) return;                              /* 4U: vcmpe lo, dist; bhi (also when unordered) */
    t.f = (dist - lo) / (hi - lo);
    if (t.i > 0x3f800000) t.f = 1.0f;                       /* 4U: signed compare of the bits with 1.0f */
    stopMove(self);
    RF(rec, REC_VEL + 8) = (vmin + t.f * (vmax - vmin)) / ((b - a) * 0.5f);
    rot_y(&RF(rec, REC_VEL), ang);
    k = sizeFactor(self) * out;
    RF(rec, REC_POS_X) += RF(rec, REC_VEL) * FIELD(float, self, EN_DT) * k;
    k = sizeFactor(self) * out;
    RF(rec, REC_POS_Z) += RF(rec, REC_VEL + 8) * FIELD(float, self, EN_DT) * k;
}

/* ---- 7/192-197 7/204: 4U 0x84bad8(cat, num): lunge (motion 0x21d blend 2, attack slot 0 index 17 with param 8 and
 * slot 1 index 18 with param 24, speed 1.15 charged); turn in 12-22 (x 3 below rank 4, else x 5); at frame 30 the xz
 * distance and angle to the target slot into work+0x20 / 0x18; every frame lunge_855c38 toward that angle (window
 * 40-58, distance 0..600 -> speed 0..160); then the follow-up cat / num from frame 80 (cat 255: the end of the action at
 * the motion end, 7/40 on GU efeb30). */
void szmv_84bad8(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t cat = p[0], num = p[1];
    float out = 0.0f;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x21d, 2.0f, 0.0f);
        attackEx(self, 0, 17, 8);
        attackEx(self, 1, 18, 24);
        setMotionSpeed(self, isCharged(self) ? 1.15f : 1.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 9, &out, 12.0f, 22.0f)) {
        void *q = QUEST_GLOBAL;
        float k = (q ? questRank(q) : 0) < 4 ? 3.0f : 5.0f;
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * k * (out * 65536.0f) * 0.0027777778f), 0);
    }
    if (atFrame(self, 30.0f)) {
        RF(work, WK_DIST) = dist_xz(&RF(rec, REC_POS_X), &RF(rec, REC_TARGET));
        RU(work, WK_ANG) = angle_to_target(rec);
    }
    lunge_855c38(self, RU(work, WK_ANG), 40.0f, 58.0f, RF(work, WK_DIST), 0.0f, 600.0f, 0.0f, 160.0f);
    if (cat == 255) {
        if (isMotionEnd(self)) end_action(self);
        return;
    }
    if (motionCheck(self, 1, 0, 80.0f, 0.0f)) chain(self, cat, num);
}

/* ---- 7/203 7/206: 4U 0x84d488(r1, r2): hop back (motion 0x21e; r1 1: blend 10 / frame 10, 2: 10 / 38, else 2 / 0),
 * speed 0.9 (0.95 from frame 40), attack slot 0 index 24; r1 2: stopMove, else the approach (-1200 clamped to -1500..0,
 * / 20 for r1 1, else / 30); move in 10-30 (r1 1) / 0-30; in 46-62 a second approach (-1200, -2000..500, / 16) and
 * move; turn toward the target slot + 32000 (its back to it) in 0-40 (x 5 for r1 1, else x 4), else in 40-64 (x 6 for
 * r1 2, else x 1.5); then by r2: 1 -> 7/5 from frame 144, 2 -> 7/207 from frame 106, else the end of the action at the
 * motion end. */
void szmv_84d488(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0], r2 = p[1];
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        if (r1 == 1) setMotion(self, 0x21e, 10.0f, 10.0f);
        else if (r1 == 2) setMotion(self, 0x21e, 10.0f, 38.0f);
        else setMotion(self, 0x21e, 2.0f, 0.0f);
        setMotionSpeed(self, 0.9f);
        attack(self, 0, 24);
        if (r1 == 1) approach(self, 0, -1200.0f, -1500.0f, 0.0f, 20.0f);
        else if (r1 == 2) stopMove(self);
        else approach(self, 0, -1200.0f, -1500.0f, 0.0f, 30.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 0, 0, 40.0f, 40.0f)) setMotionSpeed(self, 0.95f);
    if (motionCheck(self, 3, 0, r1 == 1 ? 10.0f : 0.0f, 30.0f)) moveByVel(self);
    if (motionCheck(self, 3, 0, 46.0f, 62.0f)) {
        uint8_t s1 = rec[REC_STEP1];
        if (s1 == 0) {
            rec[REC_STEP1] = 1;
            approach(self, 0, -1200.0f, -2000.0f, 500.0f, 16.0f);
        }
        if (s1 == 0 || s1 == 1) moveByVel(self);
    }
    if (motionCheck(self, 3, 0, 0.0f, 40.0f))
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * (r1 == 1 ? 5.0f : 4.0f) * 182.04445f), 32000);
    else if (motionCheck(self, 3, 0, 40.0f, 64.0f))
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * (r1 == 2 ? 6.0f : 1.5f) * 182.04445f), 32000);
    if (r2 == 1) {
        if (motionCheck(self, 1, 0, 144.0f, 0.0f)) chain(self, 7, 5);
    } else if (r2 == 2) {
        if (motionCheck(self, 1, 0, 106.0f, 0.0f)) chain(self, 7, 207);
    } else if (isMotionEnd(self)) {
        end_action(self);
    }
}

/* 4U class helper 0x852d74(this, 0), the path 0x842b44 reaches (its flag r1 = 0: the distance test 0x852e00.. is not
 * reached): 1 while the rest target is valid. Through GU 0xb2ddc (G, header); each answer logs, 4 lines at most. */
static int rest_target_852d74(void *self)
{
    static uint8_t s_lines;
    int r = restTarget(self) == 1;
    if (s_lines < 4) {
        s_lines++;
        logf("szport: 13/3 rest target %d -> %s (4U class 0x852d74 via GU 0xb2ddc, G)", r, r ? "13/4" : "2/10");
    }
    return r;
}

/* ---- 13/3: 4U 0x842b44 (r1 3, unused): rest walk. Every frame sleepFlagA and rec+0x36c = 1. Motion 0x219: the point
 * 336 short of the target slot (and the angle to the slot) becomes target slot 0, the turn sequence k_seq_e0d06c starts
 * at that angle, velocity = (point - position) x 0.02 x the motion speed (y 0); in 12-62 move and poll the turn; at the
 * motion end the action timer 180 and motion 0xd from frame 68; next frame on the controlling machine: 13/4 while the
 * rest target is valid, else 2/10 (the timer is left to 13/4). */
void szmv_842b44(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    float pt[4] = { 0.0f, 0.0f, 0.0f, 0.0f };
    (void)p;
    sleepFlagA(self);
    rec[REC_REST36C] = 1;
    switch (rec[REC_STEP0]) {
    case 0: {
        uint16_t ang = 0;
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        setMotion(self, 0x219, 0.0f, 0.0f);
        restPoint(self, pt, &ang, 336.0f);
        float dx = pt[0] - RF(rec, REC_POS_X), dz = pt[2] - RF(rec, REC_POS_Z);
        movePoint(self, pt, 0);
        seqStart1(self, &k_seq_e0d06c, 2, 1, ang);
        resetVel(self);
        RF(rec, REC_VEL) = motionSpeed(self) * 0.02f * dx;
        RF(rec, REC_VEL + 8) = motionSpeed(self) * 0.02f * dz;
        RF(rec, REC_VEL + 4) = 0.0f;
        return;
    }
    case 1:
        if (motionCheck(self, 3, 0, 12.0f, 62.0f)) {
            moveByVel(self);
            seqPoll1(self, &k_seq_e0d06c);
        }
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0] = 2;
        RF(rec, REC_TIMER) = 180.0f;
        setMotion(self, 0xd, 0.0f, 68.0f);
        return;
    case 2:
        if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) RF(rec, REC_TIMER) = 0.0f;
        if (FIELD(uint8_t, self, EN_CONTROLLED) != 1) return;
        if (rest_target_852d74(self)) chain(self, 13, 4);
        else chain(self, 2, 10);
        return;
    default:
        return;
    }
}
