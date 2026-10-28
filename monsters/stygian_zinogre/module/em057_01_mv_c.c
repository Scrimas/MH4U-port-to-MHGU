/* em057_01_mv_c.c: Stygian Zinogre, ported 4U uEm048 handlers, batch C (the second paw slams 7/160-175 that follow
 * 0x848310, and 7/176 7/177).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case (GU reused the numbers: 7/160-171 are its own moves efd5e0 /
 * efd9ac, 7/172-177 end at once). Each handler is a literal translation of the 4U function named in its comment
 * (MH4U v1.1, dump/mh4u.asm), in 4U call order with 4U frame / timer / angle values; em==49 branches take the
 * Stygian side (phase1-variant-map.md 1B: attack indices 57 / 58, 61 / 62; GU's code has no such branch). Verdicts
 * and parameters: notes/phase2-actions.md 2. C = confirmed in code, S = strong, G = guess.
 * Parameters (C): the 4U cat-7 stubs (0x852374..0x8524f0 for 0x853704, 0x8524f4..0x852510 for 0x854088) pop their
 * frame and pass r1..r3 only; neither handler reads a stack argument (its only [sp] is its own out float), so there
 * is no [sp] parameter and no [sp] gate.
 *
 * 4U -> GU, beyond the batch A / B lists (em057_01_mv_a.c, em057_01_mv_b.c headers; "site" = GU's look-alike handler
 * does the same call at the same place: eff878 for 0x854088 (GU's own copy: same turn, approach, windows and speed
 * frames, other follow-ups), efd5e0 for 0x853704's turn and lead-in):
 * - 4U this+0xca8 = 0 (the normal paths, every frame) -> GU this+0xb5f8 = 0 (C: GU's no-class value; the GU base
 *   clears it so every frame at 0x6f640, and GU's handlers store only nonzero classes).
 * - 0x90f994 current motion = curMotion 0xb0a00 (C: game.h, api-map).
 * - callees mapped in batch A / B, at these sites (C): setMotion eff8e4 effa8c effb00 efd7bc; approach efc550 eff900
 *   (same -300 / 0 / 500 / 8); work+0x18 - yaw eff90c..eff91c; angle to the target slot efd7dc, targetSide eff928
 *   efd804, the +16384 clamp efd830; motionCheck + turnToTarget eff958 / eff99c (26-36, x 4) and efd69c / efd6d8
 *   (mode 9, 26-46); moveByVel eff9c4 (36-44); setMotionSpeed eff9f0 effa10 (frame 64 -> 0.85, 130 -> 0.9); end of
 *   action vt+0x3dc effa24 (4U vt+0x164); spinWindow effa54 efd74c (10-22); isCharged effab8; setTargetMode efd668;
 *   setActionNext 0x76984 efd988.
 * - attack: 4U 0x914dfc = attack 0x7df94 (attackEx param 0, batch B); GU's eff878 passes 8 to attackEx 0x7dc2c
 *   (GU-only combo link): 4U's 0 kept.
 * - sounds: class helper 0x8565cc = sz_snd_pair (G: 4U request ids and joints; sz_snd logs each site).
 * - work+0x115..0x117 = WK_217 (batch B, S): 0x853704's lead-in stores (side, r2, r3) there for 7/218.
 * No shell or effect post in these handlers (C: no 0x662904 / 0x6629bc / 0x6639a0 / 0x6620c4 call). */
#include "em057_01.h"

/* 4U step 0 of 0x853704 (normal path and lead-in): motion 0x229 (side != 0) / 0x228, the turn to the target slot into
 * work+0x1c: toward the target side, at most 90 degrees the positive way (no lower clamp) */
static void turn_228(void *self, uint32_t side)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    setMotion(self, side ? 0x229 : 0x228, 0.0f, 0.0f);
    uint32_t d = angle_to_target(rec) - RU(rec, REC_YAW), v;
    if (targetSide(self, 0)) v = d & 0xffff;               /* positive turn */
    else v = d | 0xffff0000u;                              /* negative turn */
    RU(work, WK_TURN) = v;
    if ((int32_t)v > 16384) v = 16384;
    RU(work, WK_TURN) = v;
}

/* 4U 0x853d24..: 0x853704's G-rank branch, the lead-in of 7/218. Not lead_217's code (0x8489c8) with another
 * follow-up: it starts with the turn (motion 0x229 / 0x228, the turn in 10-22), then motion 0x23a / 0x23b from frame
 * 24 (no setTargetMode, no approach), turn in 26-46, then 0x23e / 0x23f until the controlling machine moves on to
 * 7/218; sound pair by side == 0, and (side, r2, r3) for 7/218 in work+0x115..0x117. */
static void lead_218(void *self, uint32_t side, uint32_t r2, uint32_t r3)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    float out = 0.0f;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        turn_228(self, side);
        sz_snd_pair(self, side == 0);
        work[WK_217] = (uint8_t)side;
        work[WK_217 + 1] = (uint8_t)r2;
        work[WK_217 + 2] = (uint8_t)r3;
        return;
    case 1:
        spinWindow(self, RU(work, WK_TURN), 10.0f, 22.0f);
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        setMotion(self, side ? 0x23a : 0x23b, 0.0f, 24.0f);
        return;
    case 2:
        if (motionCheck(self, 9, &out, 26.0f, 46.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * out * 182.04445f), 0);
        if (!isMotionEnd(self)) return;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) {
            chain(self, 7, 218);
            return;
        }
        setMotion(self, side ? 0x23e : 0x23f, 0.0f, 0.0f);
        rec[REC_STEP0]++;
        return;
    case 3:
        if (!isMotionEnd(self)) return;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) chain(self, 7, 218);
        else setMotion(self, side ? 0x23e : 0x23f, 0.0f, 0.0f);
        return;
    default:
        return;
    }
}

/* ---- 7/160-175: 4U 0x853704(side, r2, r3): second paw slam. Turn (motion 0x229 / 0x228 by side, the turn to the
 * target slot in 10-22), then motion 0x201 (side != 0) / 0x202 from frame 24 with attack slot 0 index 57 / 58 charged
 * (Stygian; em 48 / 114: 36 / 37), 22 / 23 not, and an approach; turn in 26-36, move in 36-44. r2 == 1 (7/160-167):
 * speed 0.85 at frame 64, 0.9 at 130, end at the motion end (r3 unused). r2 == 2: r3 == 3 from frame 80 7/135 (side
 * 0) / 7/136; r3 == 0 at frame 102 7/176 (side 0) / 7/177; at frame 110 r3 == 1: 7/0 (motion 0x202) / 7/1, else 7/202.
 * G rank (rank >= 5, action serial % 100 >= 50; 4U tests no [sp] here, C: 0x853760..0x85379c): lead_218 instead. */
void szmv_853704(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = p[0], r2 = p[1], r3 = p[2];
    float out = 0.0f;
    uint32_t roll = FIELD(uint16_t, self, EN_ACT_SERIAL) % 100;
    void *q = QUEST_GLOBAL;
    int32_t rank = q ? questRank(q) : 0;
    if (rank >= 5 && roll >= 50) {
        lead_218(self, side, r2, r3);
        return;
    }
    FIELD(uint8_t, self, EN_MOVECLASS) = 0;                 /* 4U this+0xca8 = 0 */
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        turn_228(self, side);
        return;
    case 1:
        spinWindow(self, RU(work, WK_TURN), 10.0f, 22.0f);
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        if (side) {
            setMotion(self, 0x201, 0.0f, 24.0f);
            attack(self, 0, isCharged(self) ? 57 : 22);
        } else {
            setMotion(self, 0x202, 0.0f, 24.0f);
            attack(self, 0, isCharged(self) ? 58 : 23);
        }
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        approach(self, 0, -300.0f, 0.0f, 500.0f, 8.0f);
        return;
    case 2:
        if (motionCheck(self, 3, &out, 26.0f, 36.0f))      /* 4U: mode 3 with the out here (0x854088: mode 9) */
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 4.0f * (out * 65536.0f) * 0.0027777778f), 0);
        if (motionCheck(self, 3, 0, 36.0f, 44.0f)) moveByVel(self);
        if (r2 < 2) {
            if (motionCheck(self, 0, 0, 64.0f, 64.0f)) setMotionSpeed(self, 0.85f);
            if (motionCheck(self, 0, 0, 130.0f, 130.0f)) setMotionSpeed(self, 0.9f);
            if (isMotionEnd(self)) end_action(self);
            return;
        }
        if (r3 == 3 && motionCheck(self, 1, 0, 80.0f, 0.0f)) {
            chain(self, 7, side ? 136 : 135);
            return;
        }
        if (atFrame(self, 102.0f) && r3 == 0) {
            chain(self, 7, side == 1 ? 177 : 176);
            return;
        }
        if (!motionCheck(self, 0, 0, 110.0f, 110.0f)) return;
        if (r3 == 1) chain(self, 7, curMotion(self) == 0x202 ? 0 : 1);
        else chain(self, 7, 202);
        return;
    default:
        return;
    }
}

/* ---- 7/176 7/177: 4U 0x854088(side, r2): turn (motion 0x228 (side != 0) / 0x229, approach to the target slot, the
 * turn toward the target side clamped to +-90 degrees, in 10-22; r2 == 1: speed 0.47, r2 != 0: a fixed turn step in
 * 0-20 instead), then motion 0x202 (side 1) / 0x201 from frame 24 with attack slot 0 index 62 / 61 charged (Stygian;
 * em 48 / 114: 44 / 43), 23 / 22 not; speed 0.85 at frame 64, 0.9 at 130, turn in 26-36, move in 36-44, end at the
 * motion end. G rank (rank >= 5, action serial % 100 > 50): 7/215 (side 0) / 7/216 and the sound pair, every frame. */
void szmv_854088(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = p[0], r2 = p[1];
    float out = 0.0f;
    uint32_t roll = FIELD(uint16_t, self, EN_ACT_SERIAL) % 100;
    void *q = QUEST_GLOBAL;
    int32_t rank = q ? questRank(q) : 0;
    if (rank >= 5 && roll > 50) {                           /* 4U: > 50 here (bls), >= 50 in 0x853704 (bhs) */
        chain(self, 7, side ? 216 : 215);
        sz_snd_pair(self, side);
        return;
    }
    FIELD(uint8_t, self, EN_MOVECLASS) = 0;                 /* 4U this+0xca8 = 0 */
    switch (rec[REC_STEP0]) {
    case 0: {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, side ? 0x228 : 0x229, 0.0f, 0.0f);
        approach(self, 0, -300.0f, 0.0f, 500.0f, 8.0f);
        uint32_t d = RU(work, WK_ANG) - RU(rec, REC_YAW), v;   /* work+0x18: the approach's angle */
        if (targetSide(self, 0)) {
            v = d & 0xffff;                                 /* positive turn, at most 90 degrees */
            RU(work, WK_TURN) = v;
            if ((int32_t)v > 16384) v = 16384;
        } else {
            v = d | 0xffff0000u;                            /* negative turn, at most 90 degrees */
            RU(work, WK_TURN) = v;
            if ((int32_t)v <= -16384) v = 0xffffc000u;
        }
        RU(work, WK_TURN) = v;
        if (r2 == 1) setMotionSpeed(self, 0.47f);
        return;
    }
    case 1:
        if (r2 == 0) spinWindow(self, RU(work, WK_TURN), 10.0f, 22.0f);
        else if (motionCheck(self, 3, 0, 0.0f, 20.0f)) turnToTarget(self, 182, 0);
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        if (side == 1) {
            setMotion(self, 0x202, 0.0f, 24.0f);
            attack(self, 0, isCharged(self) ? 62 : 23);
        } else {
            setMotion(self, 0x201, 0.0f, 24.0f);
            attack(self, 0, isCharged(self) ? 61 : 22);
        }
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        return;
    case 2:
        if (motionCheck(self, 0, 0, 64.0f, 64.0f)) setMotionSpeed(self, 0.85f);
        if (motionCheck(self, 0, 0, 130.0f, 130.0f)) setMotionSpeed(self, 0.9f);
        if (motionCheck(self, 9, &out, 26.0f, 36.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 4.0f * (out * 65536.0f) * 0.0027777778f), 0);
        if (motionCheck(self, 3, 0, 36.0f, 44.0f)) moveByVel(self);
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}
