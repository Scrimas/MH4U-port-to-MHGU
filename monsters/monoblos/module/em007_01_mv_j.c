/* em007_01_mv_j.c: Monoblos, the attacks tied to his motions: port of the motion part of 4U uEm101 slot 48 0x8df784
 * (every frame, switch on the motion; C, literal), all 24 attack calls his action handlers do not make. Until 0.4.5
 * they were missing (found 2026-11-05 after the user's test: he stood on the burrowing monster, blocking, and nothing
 * happened): his feet, tail and body hit nothing while he walked or turned, nor while he travelled under the hunter or
 * burst out of the ground.
 *
 * GU's counterpart is class slot 130 0xd38c0c: GU moved most of them into its action handlers (which he does not run)
 * and keeps attacks there only on motions 5, 11 and 12, with Diablos' records and hit shapes. So the hook on that slot
 * runs this first and skips GU's function on those three motions (every call of it there is an attack, a shake of the
 * same motion, or a test for them); on the others GU's function goes on: its camera shakes and ground effects are GU's
 * look of the same animations (4U's ground impact 0x954e5c = GU's 0xd39854 there, C: the same frames on motions 24, 33,
 * 43, 46). 4U's shakes are ported where GU has no case for the motion (9, 10) or was skipped (5).
 *
 * 4U frame constants: 0x8dfab8.. (C). 0x93906c = motionCheckB, 0x91ab1c = motionCheck, 0x910c6c = camShakeJoint. */
#include "em007_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define PORT_BASE    208            /* em007_01_moves.c */
#define REC_TMODE    0x1ba          /* target mode [4U W+0x1c8] (C: GU 0xbc960) */
#define SLOT_STAGE   39             /* vt+0x9c: the stage number (C: GU's version of this choice, 0xd426cc) */
#define STAGE_DUNES  5              /* with 248: GU d426dc..d426f0 in place of 4U's maps 17 / 18 */
#define STAGE_DUNES2 248
#define STAGE_OTHER  250            /* GU d42708 in place of 4U's map 13 */

static int at(void *self, float f)  { return motionCheckB(self, 0, 0, f, 0.0f); }
static int atA(void *self, float f) { return motionCheck(self, 0, 0, f, 0.0f); }
static void shake(void *self) { camShakeJoint(self, 0, 1, 0); }

/* 0x8df894: motion 0x20f (his charge and the burrowed travels, which start it at frame 100): one attack at frame 106.
 * By the action's number (his 4U number): 2, 3, 4 = attack 14, or under the ground (6/4) attack 46, the root sphere of
 * radius 330 with power 0 that throws a hunter above him; the others attack 34 */
static void motion_20f(void *self)
{
    uint32_t n = FIELD(uint8_t, self, EN_ACT_NUM);
    if (n >= PORT_BASE) n -= PORT_BASE;
    if (!at(self, 106.0f)) return;
    if (n == 2 || n == 3 || n == 4) {
        if (REC(self)[REC_TMODE] == 4) attackEx(self, 0, MB_ATK(46), 10);
        else attackEx(self, 0, MB_ATK(14), 138);
    } else {
        attackEx(self, 0, MB_ATK(34), 138);
    }
}

/* 0x8e004c: motion 0x212, bursting out of the ground: attack 56 at frame 10 (attack 21 on two 4U maps, area 10 of the
 * Dunes and area 12 of map 13; GU's own Diablos makes the same choice with its stage numbers), attack 33 at frame 40 */
static void motion_212(void *self)
{
    if (atA(self, 10.0f)) {
        uint32_t stage = ((uint32_t (*)(void *))(*(uint32_t **)self)[SLOT_STAGE])(self);
        uint32_t area = FIELD(uint8_t, self, EN_AREA);
        if (((stage == STAGE_DUNES || stage == STAGE_DUNES2) && area == 10) || (stage == STAGE_OTHER && area == 12))
            attackEx(self, 0, MB_ATK(21), 8);
        else
            attackEx(self, 0, MB_ATK(56), 8);
    }
    if (atA(self, 40.0f)) attackEx(self, 0, MB_ATK(33), 8);
}

/* the switch of 0x8df784; 1 = GU's slot 130 must not run on this motion */
static int motion_frame(void *self)
{
    switch (curMotion(self)) {
    case 5:                                         /* 0x8df9a8 */
        if (at(self, 52.0f)) shake(self);
        if (at(self, 116.0f)) shake(self);
        if (at(self, 2.0f)) attack(self, 0, MB_ATK(2));
        if (at(self, 50.0f)) attack(self, 1, MB_ATK(3));
        if (at(self, 120.0f)) attack(self, 0, MB_ATK(4));
        return 1;
    case 6:                                         /* 0x8dfaf0 */
        if (at(self, 2.0f)) attackEx(self, 0, MB_ATK(26), 8);
        if (at(self, 42.0f)) attackEx(self, 1, MB_ATK(25), 8);
        if (at(self, 74.0f)) attackEx(self, 0, MB_ATK(26), 8);
        return 0;
    case 9:                                         /* 0x8dfba4 */
        if (at(self, 2.0f)) attackEx(self, 0, MB_ATK(5), 8);
        if (at(self, 30.0f)) attackEx(self, 1, MB_ATK(6), 8);
        if (at(self, 60.0f)) shake(self);
        return 0;
    case 10:                                        /* 0x8dfc3c */
        if (at(self, 2.0f)) attackEx(self, 0, MB_ATK(8), 8);
        if (at(self, 30.0f)) attackEx(self, 1, MB_ATK(7), 8);
        if (at(self, 60.0f)) shake(self);
        return 0;
    case 11:                                        /* 0x8dfcec */
        if (at(self, 2.0f)) attackEx(self, 0, MB_ATK(11), 16);
        if (at(self, 18.0f)) attackEx(self, 1, MB_ATK(12), 16);
        return 1;
    case 12:                                        /* 0x8dfd68 */
        if (at(self, 2.0f)) attackEx(self, 0, MB_ATK(10), 16);
        if (at(self, 18.0f)) attackEx(self, 1, MB_ATK(9), 16);
        return 1;
    case 22:                                        /* 0x8dfde4 */
        if (atA(self, 2.0f)) attackEx(self, 0, MB_ATK(27), 5);
        if (atA(self, 56.0f)) attackEx(self, 1, MB_ATK(28), 5);
        if (atA(self, 168.0f)) attackEx(self, 0, MB_ATK(27), 5);
        return 0;
    case 23:                                        /* 0x8dff78 */
        if (atA(self, 2.0f)) attackEx(self, 0, MB_ATK(32), 8);
        return 0;
    case 0x113:                                     /* 0x8dfef4, then 0x8dff34 */
    case 0x30e:                                     /* 0x8dff34 */
        if (atA(self, 148.0f)) attackEx(self, 0, MB_ATK(15), 8);
        return 0;
    case 0x20f:
        motion_20f(self);
        return 0;
    case 0x210:                                     /* 0x8df964 */
        if (at(self, 10.0f)) attackEx(self, 0, MB_ATK(22), 24);
        return 0;
    case 0x212:
        motion_212(self);
        return 0;
    default:
        return 0;
    }
}

/* hook on GU's slot 130 entry; 1 = GU's function is skipped */
int em007_01_motion_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != MONOBLOS_EM_ID) return 0;
    return motion_frame(self);
}
