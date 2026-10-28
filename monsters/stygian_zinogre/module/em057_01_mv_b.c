/* em057_01_mv_b.c: Stygian Zinogre, ported 4U uEm048 handlers, batch B (the follow-ups of batch A's turns and 7/15,
 * 7/186 187, 7/215 216, the 0x84b548 rush family, 0x84ab60's 7/51-53 and 7/202).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case. Each handler is a literal translation of the 4U function named
 * in its comment (MH4U v1.1, dump/mh4u.asm), in 4U call order with 4U frame / timer / angle values; em==49 branches
 * take the Stygian side (phase1-variant-map.md 1B: attack indices 55 / 56, 60, 50). Verdicts and parameters:
 * notes/phase2-actions.md 2. C = confirmed in code, S = strong, G = guess.
 *
 * 4U -> GU, beyond batch A's list (em057_01_mv_a.c header; "site" = GU's look-alike handler does the same call at the
 * same place: efeedc for 0x848310, f004c8 for 0x84f50c, efcfe8 for 0x84b548, efbe1c for 0x84ab60):
 * - work: 4U [this+0x8d88] = W (C: uEm048 ctor 0x859a0c), GU [this+0xcac0] = rec + 96 (C: ctor eee964); the class
 *   keeps the offsets (batch A). work+44 = sound timer (C: phase1 group A, GU ef5ae8 uses work+0x2c the same way).
 *   work+0x115..0x117 (the lead-in's side, r2, r3, read only by the 4U 7/217-220 handlers) at the same offsets
 *   (S: GU's class never touches work+0x115..0x117).
 * - W+468 timer = rec+0x1bc, W+372 accel y = rec+0x24 (site efbfd4), W+0x814 = rec+0x7a4 (site efd138), W+0x1d9
 *   controller = this+0x7420 (game.h), W+0x1d2 action serial = this+0x73e8 (S, api-map), this+656 motion frame =
 *   motionFrame (site efbf50).
 * - 4U this+0xca8 move-class bits -> GU enum byte this+0xb5f8 (phase1 group A: bit k -> k): bit 1 -> 1 (C: site
 *   efd01c), bit 9 (512) -> 9 (C: site f004e0; also GU efd9ac for 4U 7/217; GU vt79 f05914 tests 9 for the motions
 *   0x201 0x202 0x228-0x22c). Stored every frame where 4U ORs it, as GU's handlers do.
 * - callees: 0x955478 = 0x7b5f8 (site eff008); class helper 0x856d6c = GU class efc550 (C: same body, site eff194);
 *   0x92e998 = 0x816d0 (site efd3c8); 0x942258 = 0xbf178 (site efbff0); 0x910c6c(j, id) = 0xc24d8(j, id, 0) (site
 *   efc08c); 0x941dbc = atFrame 0xb0a30; 0xb0709c(&t) = timerDown(&t, 1.0) (site efd1d8); 0x93c6c8 = sleepFlagB
 *   (site efbf48); 0x92dc88 / 0x92dd04 = setStopDist / inRange (sites efd2c8 efd354); 0x90f934 = attackFlag (site
 *   efd0f8); 0x92e9d4 = restApply (S: tigerstripe callee map, same state test {0, 3, 6}; GU's efbe1c inlines only its
 *   pos.y part); 0x91e130(this, 0) = targetSide 0xc7ef8 (C: same body, u16 angle to target slot - yaw < 0x8000);
 *   0x69ae70 = questRank (S, as em057_01_moves.c).
 * - attack: 4U 0x914dfc = attackEx(slot, idx, 0) (C: `mov r3, #0; b 0x933144`) = GU attack 0x7df94 (site efc508);
 *   GU's 0x848310 look-alike efeedc passes flags 8 instead (GU attackEx 0x7df30: keep the slot's hit group in
 *   rec+0xb0a / 0xb08 for a later attack with flag 16; GU-only combo link): 4U's 0 kept.
 * - sounds: class helper 0x8565cc and 0x84f50c post through 0x2fcc50(mgr *0xfccd6c, id, this, joint, W+0x14c, -2) =
 *   GU 0x4efd74(mgr *(main+0x1896f5c), id, self, joint, this+0x1054, -2) (C: callee map, em089_snd.c); the ids and
 *   joints are 4U's (G: GU's em057 request not checked), each site logs a few lines (szport: snd).
 * No shell or effect post in these handlers (C: no 0x662904 / 0x6629bc / 0x6639a0 / 0x6620c4 call). */
#include "em057_01.h"

#define SND_SITES   16

/* 4U 0x2fcc50(*0xfccd6c, id, this, joint, W+0x14c, -2); site = the 4U call, which logs its first 4 posts */
void sz_snd(void *self, uint32_t id, uint32_t joint, uint32_t site)
{
    static uint32_t s_site[SND_SITES];
    static uint8_t s_lines[SND_SITES];
    void *mgr = *(void **)MAIN(SND_MGR);
    uint32_t i = 0;
    if (mgr) sndJoint(mgr, id, self, joint, FIELD(uint8_t, self, EN_AREA), -2);
    while (i < SND_SITES && s_site[i] && s_site[i] != site) i++;
    if (i == SND_SITES || s_lines[i] >= 4) return;
    s_site[i] = site;
    s_lines[i]++;
    logf("szport: snd %u joint %u (4U %x, G: 4U request id)", id, joint, site);
}

/* 4U class helper 0x8565cc(this, sel, unused): ids 209 then 225 at joint 13 (sel != 0) or 9 */
void sz_snd_pair(void *self, uint32_t sel)
{
    uint32_t j = sel ? 13 : 9;
    sz_snd(self, 209, j, 0x856610);
    sz_snd(self, 225, j, 0x856630);
}

/* 4U 0x8489c8..: 0x848310's G-rank branch, the lead-in of 7/217 (motion 0x23a / 0x23b, then 0x23e / 0x23f until
 * the controlling machine moves on to 7/217) */
static void lead_217(void *self, uint32_t side, uint32_t r2, uint32_t r3)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    float out = 0.0f;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    uint8_t step = rec[REC_STEP0];
    if (step == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, side ? 0x23b : 0x23a, 0.0f, 0.0f);
        work[WK_217] = (uint8_t)side;                       /* 4U strb r6 / r7 / r5 = 0x848310's r1 / r2 / r3 */
        work[WK_217 + 1] = (uint8_t)r2;
        work[WK_217 + 2] = (uint8_t)r3;
        sz_snd_pair(self, side);
        return;
    }
    if (step == 1) {
        if (motionCheck(self, 9, &out, 26.0f, 46.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * out * 182.04445f), 0);
        if (!isMotionEnd(self)) return;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) {
            chain(self, 7, 217);
            return;
        }
        setMotion(self, side ? 0x23f : 0x23e, 0.0f, 0.0f);
        rec[REC_STEP0]++;
        return;
    }
    if (step != 2 || !isMotionEnd(self)) return;
    if (FIELD(uint8_t, self, EN_CONTROLLED)) chain(self, 7, 217);
    else setMotion(self, side ? 0x23f : 0x23e, 0.0f, 0.0f);
}

/* ---- 7/2 3 6 7 16 68 69 188 189: 4U 0x848310(side, r2, r3, [sp] sp0): paw slam (motion 0x201 / 0x202; side 1
 * with sp0 starts at frame 42), attack slot 0 index 55 / 56 charged (Stygian; em 48 / 114: 34 / 35), 4 / 7 not;
 * approach the target slot; turn in 0-20, move in 24-36; r2 == 0: end at the motion end (frame 120 if r3 == 4); else at
 * frame 102 the follow-up by side / r2 / r3: 7/160-175, or for r3 == 5 the sound pair and 7/187 (side 0) / 7/186.
 * G rank (rank >= 5, sp0 != 1, action serial % 100 >= 50): lead_217 instead. */
void szmv_848310(void *self, const uint8_t *p)
{
    static const uint8_t s_next[2][2][6] = {                /* [side][r2 != 1][r3]; 0 = none (4U returns) */
        {{160, 161, 162, 163, 0, 187}, {168, 169, 170, 171, 0, 187}},   /* 4U tables 0x84872c 0x848708 */
        {{164, 165, 166, 167, 0, 186}, {172, 173, 174, 175, 0, 186}},   /* 4U tables 0x84884c 0x8486d0 */
    };
    uint8_t *rec = REC(self);
    uint32_t side = p[0], r2 = p[1], r3 = p[2], sp0 = p[3];
    float out = 0.0f;
    uint32_t roll = FIELD(uint16_t, self, EN_ACT_SERIAL) % 100;
    void *q = QUEST_GLOBAL;
    int32_t rank = q ? questRank(q) : 0;
    if (rank >= 5 && sp0 != 1 && roll >= 50) {
        lead_217(self, side, r2, r3);
        return;
    }
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (side) {
            setMotion(self, 0x202, 0.0f, sp0 ? 42.0f : 0.0f);
            attack(self, 0, isCharged(self) ? 56 : 7);
        } else {
            setMotion(self, 0x201, 0.0f, 0.0f);
            attack(self, 0, isCharged(self) ? 55 : 4);
        }
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        /* 4U computes the angle to the target slot (0x568c8c) here and drops it (pure): omitted */
        approach(self, 0, -800.0f, 0.0f, 500.0f, 12.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 9, &out, 0.0f, 20.0f))
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 1.5f * (out * 65536.0f) * 0.0027777778f), 0);
    if (motionCheck(self, 3, 0, 24.0f, 36.0f)) moveByVel(self);
    if (r2 == 0) {
        if (r3 == 4 ? motionCheck(self, 0, 0, 120.0f, 120.0f) : isMotionEnd(self)) end_action(self);
        return;
    }
    if (!motionCheck(self, 0, 0, 102.0f, 102.0f)) return;
    if (r3 == 5) sz_snd_pair(self, side == 0);
    uint32_t n = r3 < 6 ? s_next[side != 0][r2 != 1][r3] : 0;
    static uint8_t s_nolog;
    if (n) chain(self, 7, n);
    else if (s_nolog < 4) {                                 /* r3 4 or >= 6: no 4U caller passes them */
        s_nolog++;
        logf("szport: 7/2 family frame 102, no follow-up for side %u r2 %u r3 %u", side, r2, r3);
    }
}

/* ---- 7/186 7/187: 4U 0x84f50c(side): motion 0x22c / 0x22b held for 51 frames: id 225 at joint 2 every 15 frames
 * (from the first frame), id 209 at frame 2 of the first loop, turn in 16-21 after it; then 7/190 (side 0) / 7/191.
 * r2 (7) is unused. */
void szmv_84f50c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = p[0];
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        RF(rec, REC_TIMER) = 51.0f;
        RF(work, WK_SNDT) = 0.0f;
        setTargetMode(self, 0);
        setMotion(self, side ? 0x22b : 0x22c, 0.0f, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (timerDown(self, &RF(work, WK_SNDT), 1.0f)) {
        RF(work, WK_SNDT) = 15.0f;
        sz_snd(self, 225, 2, 0x84f5a4);
    }
    if (rec[REC_STEP1] == 0) {
        if (atFrame(self, 2.0f)) sz_snd(self, 209, 2, 0x84f6a0);
    } else if (motionCheck(self, 3, 0, 16.0f, 21.0f)) {
        turnToTarget(self, 0x4fa, 0);
    }
    if (isMotionEnd(self)) rec[REC_STEP1] = 1;
    if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) chain(self, 7, side ? 191 : 190);
}

/* ---- 7/215 7/216: 4U 0x84fbe4(side): turn (motion 0x229 / 0x228, the turn to the target slot in 10-22: toward
 * the target side, at most 90 degrees that way), then motion 0x23a / 0x23b from frame 24 with an approach, turn in
 * 26-46, then 0x23e / 0x23f until the controlling machine moves on to 7/220. r2 (7) is unused. */
void szmv_84fbe4(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = p[0];
    float out = 0.0f;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    switch (rec[REC_STEP0]) {
    case 0: {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, side ? 0x228 : 0x229, 0.0f, 0.0f);
        uint32_t d = angle_to_target(rec) - RU(rec, REC_YAW), v;
        if (targetSide(self, 0)) v = d & 0xffff;           /* positive turn */
        else v = d | 0xffff0000u;                          /* negative turn (4U: no lower clamp) */
        RU(work, WK_TURN) = v;
        if ((int32_t)v > 16384) v = 16384;
        RU(work, WK_TURN) = v;
        work[WK_217] = (uint8_t)side;
        work[WK_217 + 1] = 0;
        work[WK_217 + 2] = 0;
        return;
    }
    case 1:
        spinWindow(self, RU(work, WK_TURN), 10.0f, 22.0f);
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        setMotion(self, side ? 0x23b : 0x23a, 0.0f, 24.0f);
        approach(self, 0, -300.0f, 0.0f, 500.0f, 12.0f);
        return;
    case 2:
        if (motionCheck(self, 9, &out, 26.0f, 46.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * out * 182.04445f), 0);
        if (!isMotionEnd(self)) return;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) {
            chain(self, 7, 220);
            return;
        }
        setMotion(self, side ? 0x23f : 0x23e, 0.0f, 0.0f);
        rec[REC_STEP0]++;
        return;
    case 3:
        if (!isMotionEnd(self)) return;
        if (FIELD(uint8_t, self, EN_CONTROLLED)) chain(self, 7, 220);
        else setMotion(self, side ? 0x23f : 0x23e, 0.0f, 0.0f);
        return;
    default:
        return;
    }
}

/* ---- 7/35 36 67 54 200: 4U 0x84b548(r1, r2, r3): charge run (motion 0x219; r2 == 1: blend 10 / frame 50) toward
 * the target slot (stop distance -2000, run loop from frame 114 until in range), attack slot 0 index 60 charged
 * (Stygian; em 48 / 114: 41) / 11 at frame 68 (param 3), turn in 0-20; then the stop: r3 == 0 motion 0x21b (two
 * turns 8-24, 42-62), else 0x21c (half turn 0-60, then 7/112 if r3 == 1, else 7/53 at its end); r1 == 1: 1/32 from
 * frame 80, r1 == 2: 7/198 from frame 70, else the end of the action at the motion end. */
void szmv_84b548(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t r1 = p[0], r2 = p[1], r3 = p[2];
    float out = 0.0f;
    if ((rec[REC_STEP0] == 0 || rec[REC_STEP0] == 1) && isCharged(self))
        FIELD(uint8_t, self, EN_MOVECLASS) = 1;             /* 4U this+0xca8 |= 2 */
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        rec[REC_STEP2] = 0;
        setTargetMode(self, 0);
        if (r2 == 1) setMotion(self, 0x219, 10.0f, 50.0f);
        else setMotion(self, 0x219, 2.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.25f : 1.0f);
        setStopDist(self, 0, 0, -2000.0f);
        RF(rec, REC_TIMER) = 0.0f;
        return;
    case 1: {
        if (RU(rec, REC_CNTUP)) RF(rec, REC_TIMER) += FIELD(float, self, EN_DT);
        else timerDown(self, &RF(rec, REC_TIMER), 1.0f);
        if (rec[REC_STEP1] == 0 && atFrame(self, 68.0f)) {
            rec[REC_STEP1] = 1;
            attackEx(self, 0, isCharged(self) ? 60 : 11, 3);
        }
        if (motionCheck(self, 9, &out, 0.0f, 20.0f))
            turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * out * 163840.0f * 0.0027777778f), 0);
        int end = isMotionEnd(self);
        int in = inRange(self, 0, 0);                       /* every frame: also steers (game.h) */
        if (!end) return;
        if (!in) {
            setMotion(self, 0x219, 0.0f, 114.0f);
            return;
        }
        rec[REC_STEP0]++;
        if (r3) setMotion(self, 0x21c, 2.0f, 0.0f);
        else setMotion(self, 0x21b, 0.0f, 0.0f);
        if (slowState(self)) setMotionSpeed(self, 0.75f);
        else setMotionSpeed(self, isCharged(self) ? 1.15f : 1.0f);
        return;
    }
    case 2:
        if (motionCheck(self, 0, 0, 10.0f, 10.0f)) attackFlag(self, 0);
        if (curMotion(self) != 0x21b) {
            spinWindow(self, 0xffff8000u, 0.0f, 60.0f);
            if (isMotionEnd(self)) {
                chain(self, 7, r3 == 1 ? 112 : 53);
                return;
            }
        } else {
            spinWindow(self, 0xffffac17u, 8.0f, 24.0f);
            spinWindow(self, 0xffffd3e9u, 42.0f, 62.0f);
        }
        if (r1 == 1) {
            if (motionCheck(self, 1, 0, 80.0f, 0.0f)) chain(self, 1, 32);
        } else if (r1 == 2) {
            if (motionCheck(self, 1, 0, 70.0f, 0.0f)) chain(self, 7, 198);
        } else if (isMotionEnd(self)) {
            end_action(self);
        }
        return;
    default:
        return;
    }
}

/* ---- 7/51-53 7/202 (7/22 7/112 7/201 stay on GU efbe1c): 4U 0x84ab60(r1): leap (motion 0x216 / 0x215 by r1,
 * r1 == 3: blend 16 / frame 24), turn in 20-30 and 100-110 (r1 == 0: 20-30 only, 5 x); at the end the jump (0x217,
 * restApply 490.69, approach up to 2200 without the turn), from frame 40 the fall (accel y -6) until landed (66);
 * the landing 0x218 turned around with attack slot 0 index 50 (Stygian; em 48 / 114: 10), camera shake at frame 8;
 * then 7/126 from frame 194 (r1 4-6) or the end of the action at the motion end. r2 (7) is unused. */
void szmv_84ab60(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t r1 = p[0];
    float out = 0.0f;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        switch (r1) {                                       /* 4U jump table 0x84ac48 */
        case 0: case 4: setMotion(self, 0x216, 4.0f, 0.0f); break;
        case 1: case 6: setMotion(self, 0x215, 0.0f, 46.0f); break;
        case 2: case 5: setMotion(self, 0x216, 10.0f, 100.0f); break;
        case 3: setMotion(self, 0x216, 16.0f, 24.0f); break;
        default: break;
        }
        setMotionSpeed(self, isCharged(self) ? 1.25f : 1.0f);
        RF(work, WK_DIST) = dist_xz(&RF(rec, REC_POS_X), &RF(rec, REC_TARGET));
        RU(work, WK_ANG) = angle_to_target(rec);
        return;
    case 1:
        if (r1 == 0) {
            if (motionCheck(self, 9, &out, 20.0f, 30.0f))
                turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 5.0f * (out * 65536.0f) * 0.0027777778f), 0);
        } else {
            if (motionCheck(self, 9, &out, 20.0f, 30.0f))
                turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 1.5f * (out * 65536.0f) * 0.0027777778f), 0);
            if (motionCheck(self, 9, &out, 100.0f, 110.0f))
                turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 1.5f * (out * 65536.0f) * 0.0027777778f), 0);
        }
        if (!isMotionEnd(self)) return;
        rec[REC_STEP0]++;
        restApply(self, 490.69f);
        sleepFlagB(self);
        setMotion(self, 0x217, 0.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.15f : 1.0f);
        approach(self, 1, 0.0f, 0.0f, 2200.0f, 32.0f);
        return;
    case 2: {
        sleepFlagB(self);
        union { float f; int32_t i; } fr = { motionFrame(self) };
        if (motionCheck(self, 3, 0, 0.0f, 32.0f)) rotateVel(self, &RU(rec, REC_ANGLES), 0);
        if (fr.i < 0x42200000) return;                      /* 4U: signed compare of the frame's bits with 40.0f */
        uint8_t s1 = rec[REC_STEP1];
        if (s1 == 0) {
            rec[REC_STEP1] = 1;
            stopMove(self);
        }
        if (s1 == 0 || s1 == 1) {
            RF(rec, REC_ACCEL_Y) = -6.0f;
            accelVel(self, &RU(rec, REC_ANGLES), 0);
        }
        if (!landCheck(self, 66.0f)) return;
        rec[REC_STEP0]++;
        setTargetMode(self, 0);
        setMotion(self, 0x218, 0.0f, 0.0f);
        setMotionSpeed(self, isCharged(self) ? 1.15f : 1.0f);
        attack(self, 0, 50);
        RU(rec, REC_YAW) += 32768;
        return;
    }
    case 3:
        if (atFrame(self, 8.0f)) camShakeJoint(self, 142, 9, 0);
        if (r1 == 4 || r1 == 5 || r1 == 6) {
            if (motionCheck(self, 1, 0, 194.0f, 0.0f)) chain(self, 7, 126);
            return;
        }
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}
