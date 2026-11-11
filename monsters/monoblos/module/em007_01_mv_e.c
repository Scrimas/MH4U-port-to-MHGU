/* em007_01_mv_e.c: Monoblos, ported 4U uEm101 handlers, batch E: the 4U category-1 sub-dispatcher 0x8ddf24's inline
 * cases (idles and looks). Literal translations (MH4U v1.1), run by em007_01_moves_run. C = confirmed in code, S =
 * strong, G = guess.
 * - His idle is 0x40e (bank 4), as 4U: its sounds come from GU's em007 sound call (4U em099's bank-4 records) and
 *   its effects from his bank-4 PSL (0.4.1; em007_01_mv_c.c's roar note). */
#include "em007_01.h"

/* ---- 1/1: case 1 (0x8de00c): idle loop (motion 1, setMotionLoop), the end with the motion on the controlling
 * machine. 4U compares the local player index (*0xfb6b7c + 47) with the owner index W+0x1da; GU keeps that test as
 * the controlled flag this+0x7420 (game.h EN_CONTROLLED, set where the two match, S) */
void mbmv_1_1(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotionLoop(self, 1, 10.0f, 0.0f);
    } else if (rec[REC_STEP0] == 1) {
        if (FIELD(uint8_t, self, EN_CONTROLLED) && isMotionEnd(self)) end_action(self);
    }
}

/* ---- 1/20: case 20 (0x8de2b0 / 0x8de3a0): the tail sweep (motion 0x31e, camera event 5): W+0x78bc = 1 over frames
 * 164..260 (= GU this+0x7588, C: GU's version 0xd3b6e0 (its 1/16) stores 1 there in the same window), attack 59 at
 * frame 150, turns of 0x71c7 over 192..234 and -0x71c7 over 242..300, the end with the motion. GU's version attacks
 * with Diablos' record 64: ported */
void mbmv_1_20(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x31e, 4.0f, 0.0f);
        camEvent(self, 5, 255, 0, 0.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 3, 0, 164.0f, 260.0f)) FIELD(uint8_t, self, 0x7588) = 1;
    if (atFrame(self, 150.0f)) attack(self, 0, MB_ATK(59));
    spinWindow(self, 0x71c7, 192.0f, 234.0f);
    spinWindow(self, 0xffff8e39u, 242.0f, 300.0f);
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 1/4 (case 4, 0x8de0cc / 0x8de180: motion 15), 1/6 (case 6, 0x8de110 / 0x8de250: motion 0x16, blend 6; GU's
 * version 0xd3ab78 attacks twice, his does not), 1/19 and 1/35 (cases 19 / 35, 0x8de280 / 0x8de7fc -> 0x8de83c: his
 * idle 0x40e, blend 6), 1/10 (4U 0x8da0f4: motion 0x310, blend 10) and 2/16 (sub 0x8dda24 case 16, 0x8ddc38: motion
 * 0x210, blend 4): one motion, the end with it. p[0] | p[2] << 8 = motion, p[1] = blend */
void mbmv_1_motion(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, p[0] | (uint32_t)p[2] << 8, (float)p[1], 0.0f);
    } else if (rec[REC_STEP0] == 1) {
        if (isMotionEnd(self)) end_action(self);
    }
}
