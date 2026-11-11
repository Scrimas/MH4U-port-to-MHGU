/* em007_01_mv_b.c: Monoblos, ported 4U uEm101 handlers, batch B: digging in and the underground attacks.
 * Literal translations of the 4U functions named below (MH4U v1.1), run by em007_01_moves_run. GU's own Diablos has
 * GU versions of both: 0xd3c3c8 (GU 1/32..35) = 4U 0x8da42c and 0xd435fc (GU 7/64..70) = 4U 0x8dc13c, with the same
 * motion windows and turn formulas, but GU dropped 4U's target-position copy and plays other motions; their field
 * offsets are the evidence below. C = confirmed in code, S = strong, G = guess.
 * - 4U this+0xd38 = GU this+0x13a8 (C: both store 1.0 there before motion 0x424 / 0x425, GU d3c430 / d3c4f8).
 * - 4U this+668 (layer-0 motion speed) = GU getter 0xb09bc (C: GU d3c47c at the same turn).
 * - target slot 0: kind W+0x278 / sub W+0x27a / param W+0x27c = rec+0x230 / 0x232 / 0x234 (game.h REC_TGT_KIND, S),
 *   position W+536 = rec+0x1d0 (C).
 * - sleepFlagA / B = 4U 0x922cd8 / 0x93c6c8 (C: GU d3c3dc / d3c3e4 at the same place). */
#include "em007_01.h"

#define REC_D38      0x13a8     /* this offset (not the record): [4U this+0xd38] float, 1.0 for some dig motions */
#define REC_TGT_SUB  (REC_TGT_KIND + 2)
#define REC_TGT_PAR  (REC_TGT_KIND + 4)
#define PL_POS       0x40       /* a hunter's position (C: 4U [t+0xe30]+0x10 = GU pl+0x40, em057_01_shell046.c) */

typedef void *(*tgtHunter_t)(void *self, uint32_t sub, uint32_t param);
#define tgtHunter    FN(tgtHunter_t, 0xc2eb4)   /* [0x92c960] target slot 0's hunter (stygian em057_01_shell046.c) */
typedef float (*speedGet_t)(void *self);
#define motionSpeed  FN(speedGet_t, 0xb09bc)    /* [this+668] layer-0 motion speed */

/* the 4U target position of these handlers (0x8da42c / 0x8dc13c, the same code): by target slot 0's kind,
 * 1 = its hunter (0x92c960 -> [t+0xe30]+16), 2 = its Palico or monster (0x92c90c -> [t+0xe28]+8), 6 = the slot's own
 * position, else player 0 of the player manager (0xaf9ab0(*0xfb83e8, 0) -> [p+0xe30]+16); none found: the 4U global
 * vector 0x10e6378 (4U data, not dumped: zero, G). GU deviations: kind 2 keeps the slot's own position (GU's Palico
 * position field not mapped, G) and player 0 is the local hunter ([[main+0x2126f48]+0x58]; GU's player-slot lookup
 * not found; the same hunter in single player). */
void mb_target_pos(void *self, float *out)
{
    uint8_t *rec = REC(self);
    const float *src = 0;
    out[0] = out[1] = out[2] = 0.0f;
    switch (rec[REC_TGT_KIND]) {
    case 1: {
        uint8_t *t = tgtHunter(self, rec[REC_TGT_SUB], rec[REC_TGT_PAR]);
        if (t) src = &RF(t, PL_POS);
        break;
    }
    case 2:
    case 6:
        src = &RF(rec, REC_TARGET);
        break;
    default: {
        void *root = *(void **)PLAYER_ROOT;
        uint8_t *pl = root ? *(uint8_t **)((uint8_t *)root + 0x58) : 0;
        if (pl) src = &RF(pl, PL_POS);
        break;
    }
    }
    if (src) {
        out[0] = src[0];
        out[1] = src[1];
        out[2] = src[2];
    }
}

/* ---- 1/28 1/29 1/32 1/33: 4U 0x8da42c(kind = r1 0..3), digging in (motion 0x41e / 0x41f / 0x424 / 0x425): turn toward
 * the target during frames 26..56, then underground 7/14 / 7/15 / 7/29 / 7/30 at the motion end */
void mbmv_8da42c(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0];
    float t[3];
    sleepFlagA(self);
    sleepFlagB(self);
    mb_target_pos(self, t);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (motionPlaying(self, 0x414) || motionPlaying(self, 0x421))     /* 4U 0xb059a4 */
            rootMove(self, curMotion(self) & 0xffff, &RU(rec, REC_ANGLES), ROOT_MOVE_OFFSET);
        if (kind == 1) {
            setMotion(self, 0x41f, 0.0f, 0.0f);
        } else if (kind == 2) {
            FIELD(float, self, REC_D38) = 1.0f;
            setMotion(self, 0x424, 0.0f, 0.0f);
        } else if (kind == 3) {
            FIELD(float, self, REC_D38) = 1.0f;
            setMotion(self, 0x425, 0.0f, 0.0f);
        } else {
            setMotion(self, 0x41e, 0.0f, 0.0f);
        }
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    {
        float *slot = &RF(rec, REC_TARGET), w;
        slot[0] = t[0];
        slot[1] = t[1];
        slot[2] = t[2];
        slot[3] = 0.0f;
        if (motionCheck(self, 9, &w, 26.0f, 56.0f)) {
            float a = motionSpeed(self) * (w * 68.0f);
            a = a * 0x1.111112p-5f;             /* 4U literals 0x8da750 (1/30), 65536, 0x8da758 (1/360) */
            a = a * 65536.0f;
            turnToTarget(self, (uint32_t)(int32_t)(0.5f + a * 0x1.6c16c2p-9f) & 0xffff, 0);
        }
    }
    if (!isMotionEnd(self)) return;
    if (kind == 1) mb_chain(self, 7, 15);
    else if (kind == 2) mb_chain(self, 7, 29);
    else if (kind == 3) mb_chain(self, 7, 30);
    else mb_chain(self, 7, 14);
}

/* ---- 7/13 7/14 7/15 7/28 7/29 7/30 7/33: 4U 0x8dc13c(kind = r1 0..6), the underground attack: motion 0x414 / 0x415 /
 * 0x421 / 0x422 with his attacks 44 + 54 or 45 + 55 from the start; the target slot follows the target, a turn window
 * per kind; kinds 0 and 3 end at frame 78, all at the motion end */
void mbmv_8dc13c(void *self, const uint8_t *p)
{
    uint8_t *rec;
    uint32_t kind = p[0];
    float t[3];
    mb_target_pos(self, t);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        switch (kind) {                                     /* 4U jump table 0x8dc270 */
        case 0:
            setMotion(self, 0x414, 4.0f, 0.0f);
            RF(rec, REC_TIMER) = 2.0f;
            attackEx(self, 0, MB_ATK(44), 8);
            attackEx(self, 1, MB_ATK(54), 24);
            return;
        case 1:
            setMotion(self, 0x415, 0.0f, 0.0f);
            attackEx(self, 0, MB_ATK(45), 8);
            attackEx(self, 1, MB_ATK(55), 24);
            return;
        case 2:
            setMotion(self, 0x414, 0.0f, 46.0f);
            attackEx(self, 0, MB_ATK(44), 8);
            attackEx(self, 1, MB_ATK(54), 24);
            return;
        case 3:
            setMotion(self, 0x421, 4.0f, 0.0f);
            RF(rec, REC_TIMER) = 2.0f;
            attackEx(self, 0, MB_ATK(44), 8);
            attackEx(self, 1, MB_ATK(54), 24);
            return;
        case 4:
            setMotion(self, 0x422, 0.0f, 0.0f);
            attackEx(self, 0, MB_ATK(45), 8);
            attackEx(self, 1, MB_ATK(55), 24);
            return;
        case 5:
            setMotion(self, 0x421, 0.0f, 46.0f);
            attackEx(self, 0, MB_ATK(44), 8);
            attackEx(self, 1, MB_ATK(54), 24);
            return;
        case 6:
            setMotion(self, 0x421, 4.0f, 0.0f);
            RF(rec, REC_TIMER) = 0.0f;
            attackEx(self, 0, MB_ATK(44), 8);
            attackEx(self, 1, MB_ATK(54), 24);
            return;
        default:
            return;
        }
    }
    if (rec[REC_STEP0] != 1) return;
    {
        float *slot = &RF(rec, REC_TARGET);
        slot[3] = 0.0f;
        slot[0] = t[0];
        slot[1] = t[1];
        slot[2] = t[2];
    }
    if (kind < 7) {                                         /* 4U jump table 0x8dc1dc */
        float hi = 0.0f;
        if (kind == 3 || kind == 4 || kind == 5 || kind == 6) FIELD(float, self, REC_D38) = 1.0f;
        if (kind == 0 || kind == 3 || kind == 6) hi = 18.0f;
        else if (kind == 1 || kind == 4) hi = 26.0f;
        else hi = 83.0f;                                    /* 2, 5 */
        if (motionCheckB(self, 3, 0, 0.0f, hi))
            turnToTarget(self, (uint32_t)(motionSpeed(self) * 112.0f) & 0xffff, 0);
    }
    if ((kind == 0 || kind == 3) && motionCheckB(self, 1, 0, 78.0f, 0.0f)) end_action(self);
    if (isMotionEnd(self)) end_action(self);
}
