/* em007_01_mv_f.c: Monoblos, ported 4U uEm101 handlers, batch F: his horn attacks of category 7 (motions 0x201 0x203
 * 0x204 0x213..0x216 0x219). Literal translations (MH4U v1.1), run by em007_01_moves_run. GU's Diablos has no action
 * with motion 0x203 / 0x204 (scratch twins.py); 7/0 7/5 7/6 7/7 7/9 have GU actions with the same motions (GU 7/0
 * 7/131 7/6 7/7 7/5), but those attack with Diablos' records, so his handlers are ported here too. C = confirmed in
 * code, S = strong, G = guess.
 * - 4U this+0xca8 |= 4 / 2 (by the severed-tail bit W+0x42c & 1) = GU's move class this+0xb5f8 = 2 / 1 (Stygian's
 *   rule: 4U bit k -> class k, S).
 * - Camera events 0 / 1 (4U 0x93457c) name the camera list of manifest field 11, which is still GU em007_00's
 *   (shared): an id the list lacks does nothing (gogmazios em089_act.c); which camera GU's list holds there is OPEN. */
#include "em007_01.h"

typedef int (*selfInt_t)(void *self);
#define slowState    FN(selfInt_t, 0x816d0)     /* [0x92e998] */

static void move_class(void *self)
{
    FIELD(uint8_t, self, EN_MOVECLASS) = (FIELD(uint16_t, REC(self), REC_FLAGS) & 1) ? 2 : 1;
}

/* attack 17 at frame 30 (slot), camera shakes at frames 44 and 73 */
static void horn_hits(void *self, uint32_t slot)
{
    if (motionCheckB(self, 0, 0, 30.0f, 0.0f)) attackEx(self, slot, MB_ATK(17), 8);
    if (motionCheckB(self, 0, 0, 44.0f, 0.0f)) camShakeJoint(self, 0, 1, 0);
    if (motionCheckB(self, 0, 0, 73.0f, 0.0f)) camShakeJoint(self, 0, 1, 0);
}

/* ---- 7/2 7/19: 4U 0x8dabd8(kind = r1 0 / 1), the double horn swing: motion 0x204 twice (kind 1 starts it at frame
 * 10), a half turn (-0x8000) over frames 0..116 / 0..120, attack 17 (slot 0, then slot 1) at frame 30 */
void mbmv_8dabd8(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0];
    move_class(self);
    rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (kind == 1) setMotion(self, 0x204, 10.0f, 10.0f);
        else setMotion(self, 0x204, 8.0f, 0.0f);
        return;
    case 1:
        spinWindow11(self, 0xffff8000u, 0.0f, 116.0f);
        horn_hits(self, 0);
        if (isMotionEnd(self)) {
            rec[REC_STEP0]++;
            setMotion(self, 0x204, 8.0f, 0.0f);
        }
        return;
    case 2:
        spinWindow11(self, 0xffff8000u, 0.0f, 120.0f);
        horn_hits(self, 1);
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 7/31 7/32: 4U 0x8dbf80(kind = r1 0 / 1), the half-turn horn swing (kind 0: motion 0x204, -0x8000, camera
 * event 1; kind 1: motion 0x203, +0x8000, camera event 0) at speed 1.3, attack 17 at frame 30 */
void mbmv_8dbf80(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0], mot = kind == 1 ? 0x203 : 0x204, ang = kind == 1 ? 0x8000u : 0xffff8000u;
    move_class(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, mot, 8.0f, 0.0f);
        camEvent(self, kind == 1 ? 0 : 1, 255, 0, 0.0f);
        setMotionSpeed(self, 1.3f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    spinWindow11(self, ang, 0.0f, 116.0f);
    horn_hits(self, 0);
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/1: the 4U sub-dispatcher 0x8db020's case 1 (0x8db0d8): motion 0x201 (blend 8), attack 31 (slot 1) at frame
 * 46 and 1 (slot 0) at frame 50, the end with the motion (7/0's swing without its turn) */
void mbmv_7_1(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x201, 8.0f, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheckB(self, 0, 0, 46.0f, 0.0f)) attack(self, 1, MB_ATK(31));
    if (motionCheckB(self, 0, 0, 50.0f, 0.0f)) attack(self, 0, MB_ATK(1));
    if (isMotionEnd(self)) end_action(self);
}

/* the 4U turn record 0xe0e090 (em007_01_mv_d.c has the same copy) */
static const seq_rec s_seq_e0e090 = {0.0f, 90.0f, 0.0f, 0x0e394000u,
                                     {{0x0d, 4.0f, 4.0f, 0}, {0x09, 10.0f, 0.0f, 0}, {0x0a, 10.0f, 0.0f, 0}}};

/* ---- 7/0 7/18: 4U 0x8daa48(kind = r1 0 / 1), the horn swing with a turn (record 0xe0e090, flags 1): motion 0x201
 * (kind 1 from frame 10; kind 0 at 0.8 when slowed), attack 31 (slot 1) at frame 46 and 1 (slot 0) at frame 50 */
void mbmv_8daa48(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    if (rec[REC_STEP0] == 0) {
        setTargetMode(self, 0);
        seqStart1(self, &s_seq_e0e090, 0, 1, 0);
        rec[REC_STEP0]++;
        if (kind == 1) {
            setMotion(self, 0x201, 10.0f, 10.0f);
        } else {
            setMotion(self, 0x201, 8.0f, 0.0f);
            if (slowState(self)) setMotionSpeed(self, 0.8f);
        }
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheckB(self, 0, 0, 46.0f, 0.0f)) attack(self, 1, MB_ATK(31));
    if (motionCheckB(self, 0, 0, 50.0f, 0.0f)) attack(self, 0, MB_ATK(1));
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/5 7/22: 4U 0x8dbbbc(kind = r1 0 / 1), the horn thrust with a turn (record 0xe0e090, flags 1): motion 0x213
 * (kind 1 from frame 10), attack 16 (kind 1: 57) at frame 50 */
void mbmv_8dbbbc(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        seqStart1(self, &s_seq_e0e090, 0, 1, 0);
        if (kind == 1) setMotion(self, 0x213, 10.0f, 10.0f);
        else setMotion(self, 0x213, 6.0f, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheckB(self, 0, 0, 50.0f, 0.0f)) attackEx(self, 0, MB_ATK(kind == 1 ? 57 : 16), 8);
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/6 7/20: 4U 0x8dbd0c(kind = r1 0 / 1), the horn sweep with a turn (record 0xe0e090, flags 1): motion 0x215
 * (kind 1 from frame 10), attack 30 (slot 1) at frame 54 */
void mbmv_8dbd0c(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        seqStart1(self, &s_seq_e0e090, 0, 1, 0);
        if (kind == 1) setMotion(self, 0x215, 10.0f, 10.0f);
        else setMotion(self, 0x215, 6.0f, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheckB(self, 0, 0, 54.0f, 0.0f)) attack(self, 1, MB_ATK(30));
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/7: 4U 0x8dbe34, the roaring horn sweep (motion 0x216, timer 0): attack 19 (slot 1) at frame 112, attack 8
 * (slot 0, param 5) at frame 110 with the head effect (4U 0xc0819c: not ported, see em007_01_mv_c.c), the end with
 * the motion */
void mbmv_8dbe34(void *self, const uint8_t *p)
{
    static uint32_t s_logged;
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x216, 6.0f, 0.0f);
        RF(rec, REC_TIMER) = 0.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheckB(self, 0, 0, 112.0f, 0.0f)) attack(self, 1, MB_ATK(19));
    if (motionCheck(self, 0, 0, 110.0f, 0.0f)) {
        attackEx(self, 0, MB_ATK(8), 5);
        if (!s_logged++) logf("mbport: em007_01 4U c0819c not ported (no GU site): skipped");
    }
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/9: 4U 0x8dae90, the horn upswing (motion 0x214, 0.8 when slowed) with attacks 41 (slot 0) and 42 (slot 1)
 * from the start; at frame 108 on the 4U Dunes (stage 17) area 7 it plays a stage object's action (4U 0x6c3400 on
 * *0xfcf45c with W+0x5f3 == 2, unless 0x6c5090 says busy): no GU counterpart mapped (GU's Dunes is stage 5): logged,
 * not played */
void mbmv_8dae90(void *self, const uint8_t *p)
{
    static uint32_t s_logged;
    uint8_t *rec;
    (void)p;
    move_class(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x214, 6.0f, 0.0f);
        if (slowState(self)) setMotionSpeed(self, 0.8f);
        attack(self, 0, MB_ATK(41));
        attack(self, 1, MB_ATK(42));
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 0, 0, 108.0f, 0.0f) && !s_logged++)
        logf("mbport: em007_01 4U 6c3400 (stage object action at frame 108) not ported: skipped");
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/8: case 8 (0x8db200): motion 0x219 with attacks 35 (slot 0) and 36 (slot 1) from the start, the end with it */
void mbmv_7_8(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x219, 0.0f, 0.0f);
        attackEx(self, 0, MB_ATK(35), 8);
        attackEx(self, 1, MB_ATK(36), 24);
        return;
    }
    if (rec[REC_STEP0] == 1 && isMotionEnd(self)) end_action(self);
}
