/* em007_01_mv_c.c: Monoblos, ported 4U uEm101 handlers, batch C: the roars and the scrape before the charge.
 * Literal translations of the 4U functions named below (MH4U v1.1), run by em007_01_moves_run. GU's own Diablos has
 * GU versions: its roar 0xd3a748 (GU 1/0 1/15: no turn, GU's attack record, no head effect) and its scrape 0xd3c128
 * (setMotionEx 0x418 flags 2, the clamped turn at rec+0x204 into spinWindow, as 4U 0x8da77c). C = confirmed in code,
 * S = strong, G = guess.
 * - Roar motion: 0x404, his bank 4, as 4U (since 0.4.1: GU's em007 sound call keeps 4U em099's bank-4 records, his
 *   roar's sounds among them, and his bank-4 PSL gives his 4U effects; 0.4.0 played GU's slot 4 = the same animation
 *   with Diablos' events).
 * - 4U 0xc0819c(mgr *0x10572a4, area, pos) = the roar's radial blur at the head (joint 4: a new uMhRadialBlurFilter,
 *   area-gated; GU has no spawn helper for it, dalamadur dala_efx.c) and 4U 0x390f9c (this+0xc78, 0x402, -1) = 1/34's
 *   sound event: no GU site found (Stygian Zinogre's port stubs both too): logged, not played. Since 0.4.1 his roar
 *   shows GU's own roar air instead (cm202_050 on the head from his bank-4 PSL, the slot GU's Diablos plays in the
 *   same animation: tools/build_em007_01_arc.py roar_air, a DEVIATION). */
#include "em007_01.h"

#define MOT_ROAR 0x404                  /* his roar (see above) */

/* 4U turn record 0xe0e110 (s32 blend / start -> GU floats, game.h seq_rec): turn window 0..0, straight to frame 60,
 * angle 0x4000, straight angle 0x0e39; motions 0x0d / 0x09 / 0x0a */
static const seq_rec s_seq_e0e110 = {0.0f, 0.0f, 60.0f, 0x0e394000u,
                                     {{0x0d, 4.0f, 4.0f, 0}, {0x09, 10.0f, 0.0f, 0}, {0x0a, 10.0f, 0.0f, 0}}};

static void unported_once(uint32_t what, uint32_t site)
{
    static uint32_t s_done;
    if (s_done & what) return;
    s_done |= what;
    logf("mbport: em007_01 4U %x not ported (no GU site): skipped", site);
}

/* ---- 1/21 1/34: 4U 0x8d9c9c(kind = r1: 1 / 3; 2 too): turn (record 0xe0e110) unless kind 2 / 3, then the roar
 * (kind 1 with camera event 2), attack 19 at frame 112 with the head effect (kind 3: sound event 0x402) */
void mbmv_8d9c9c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (kind == 2 || kind == 3) {
            rec[REC_STEP0] = 2;
            return;
        }
        seqStart1(self, &s_seq_e0e110, 0, 0, 0);
        return;
    case 1:
        if (seqPoll1(self, &s_seq_e0e110)) rec[REC_STEP0]++;
        return;
    case 2:
        rec[REC_STEP0] = 3;
        setMotion(self, MOT_ROAR, 10.0f, 0.0f);
        if (kind == 1) camEvent(self, 2, 255, 0, 0.0f);
        return;
    case 3:
        if (motionCheck(self, 0, 0, 112.0f, 0.0f)) {
            attackEx(self, 1, MB_ATK(19), 5);
            if (kind == 3) unported_once(1, 0x390f9c);
            else unported_once(2, 0xc0819c);
        }
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 2/7: 4U 0x8d83a0: the same roar without a kind (turn, roar, attack 19 + head effect at frame 112) */
void mbmv_8d83a0(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        seqStart1(self, &s_seq_e0e110, 0, 0, 0);
        return;
    case 1:
        if (seqPoll1(self, &s_seq_e0e110)) rec[REC_STEP0]++;
        return;
    case 2:
        rec[REC_STEP0] = 3;
        setMotion(self, MOT_ROAR, 10.0f, 0.0f);
        return;
    case 3:
        if (motionCheck(self, 0, 0, 112.0f, 0.0f)) {
            attackEx(self, 1, MB_ATK(19), 5);
            unported_once(2, 0xc0819c);
        }
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 1/31: 4U 0x8da77c(kind = r1: 1), the scrape (motion 0x418, setMotionEx flags 2): the turn toward the target
 * clamped to +-0x4000 over frames 2..26, the target slot set to the target (0x8da42c's rule), turns at frames 26..80
 * and 110, then the charge 7/25 (kind 0: 7/10) */
void mbmv_8da77c(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0];
    float t[3], *slot;
    sleepFlagA(self);
    sleepFlagB(self);
    mb_target_pos(self, t);
    rec = REC(self);
    slot = &RF(rec, REC_TARGET);
    switch (rec[REC_STEP0]) {
    case 0: {
        const float *pos = &RF(rec, REC_POS_X);
        uint32_t a;
        int32_t d;
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotionEx(self, 0x418, 2, 2.0f, 0.0f);
        a = (atan_u16(slot[0] - pos[0], slot[2] - pos[2]) - RU(rec, REC_YAW)) & 0xffff;
        d = (int16_t)a;
        if (d < 0) d = -d;
        if (d < 0x4000) RU(rec, REC_TURN) = a;
        else RU(rec, REC_TURN) = a >= 0x8000 ? 0xc000 : 0x4000;
        return;
    }
    case 1: {
        uint32_t ang = RU(rec, REC_TURN);
        if (ang >= 0x8000) ang = (uint32_t)-(int32_t)((0x10000 - ang) & 0xffff);
        spinWindow(self, ang, 2.0f, 26.0f);
        if (atFrame(self, 26.0f)) {
            rec[REC_STEP0]++;
            slot[0] = t[0];
            slot[1] = t[1];
            slot[2] = t[2];
            slot[3] = 0.0f;
        }
        return;
    }
    case 2:
        if (motionCheck(self, 3, 0, 26.0f, 80.0f)) {
            slot[0] = t[0];
            slot[1] = t[1];
            slot[2] = t[2];
            slot[3] = 0.0f;
            turnToTarget(self, 67, 0);
        }
        if (motionCheck(self, 1, 0, 110.0f, 0.0f)) {
            slot[0] = t[0];
            slot[1] = t[1];
            slot[2] = t[2];
            slot[3] = 0.0f;
            turnToTarget(self, 65, 0);
        }
        if (isMotionEnd(self)) mb_chain(self, 7, kind == 0 ? 10 : 25);
        return;
    default:
        return;
    }
}
