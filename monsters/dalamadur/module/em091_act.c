/* uEm091_00 (tail half = 4U uEm083) actions: GU slot 125 = 4U slot 44 0x8a1e6c. Each handler is a literal
 * translation of the 4U handler named in its comment, 4U frames / timers unchanged (the GU helpers scale them).
 * Motions are the shared em024 ids (bank << 8 | index): the tail's are the head's + 100 for the shared moves.
 * After every action the 4U dispatcher writes W+0x79a9, W+0x628, W+0x978 and W+0x55b = 1 (0x8a1f9c..): W+0x55b is
 * GU rec+0x529 (dala_state_frame); the other three are not mapped yet (logged once, dala_stub). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"
#include "dala_shell.h"   /* the tail's tremor shell (goal D5) */

void dala_react_tail(void *self, uint32_t cat);   /* dala_react.c */
void dala_ai_tally(void *self, uint32_t tail, uint32_t cat, uint32_t num);   /* dala_ai.c: next-test log */

/* isAction(enemy, cat, num) [4U 0x94d788 = GU 0x6ff44] (C, apimap 99) */
typedef int (*isAction_t)(void *self, uint32_t cat, uint32_t num);
#define isAction FN(isAction_t, 0x6ff44)

/* work struct [this+0x8d88]: +0 u8 "following the head" (1.50 start; read by slot 48, still to port) */
#define W_FOLLOW 0

/* 1.0-1.2 / 1.6-1.8 / 0.0-0.1 [0x8a00f8(var, timed)]: idle of placement var (motions 101 / 121 / 141, kept when
 * already playing); timed: ends after 60 frames, else at the motion end */
static void act_idle(void *self, uint32_t var, uint32_t timed)
{
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        if (var <= 2) {
            MODE(self) = (uint8_t)var;
            dala_motion_keep(self, 101 + 20 * var, 1, 20.0f, 0.0f);
        }
        TIMER(self) = 60.0f;
        return;
    }
    if (STEP(self) != 1) return;
    if (timed ? dala_timer(self) : isMotionEnd(self)) dala_end(self);
}

/* 1.3-1.5 [0x8a0224(var)]: motion 102 / 122 / 142 of placement var once */
static void act_1_3(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        if (var <= 2) {
            MODE(self) = (uint8_t)var;
            dala_motion_keep(self, 102 + 20 * var, 1, 20.0f, 0.0f);
        }
        return;
    }
    if (STEP(self) == 1 && isMotionEnd(self)) dala_end(self);
}

/* the follow table 4U 0xff5cd8 {head cat, head num, tail cat, tail num}: while the head runs the first pair the tail
 * starts the second (39 rows, C) */
static const uint8_t k_follow[][4] = {
    {2, 0, 2, 0}, {2, 1, 2, 1}, {2, 2, 2, 2}, {2, 3, 2, 3}, {2, 4, 2, 4}, {2, 5, 2, 5}, {7, 60, 7, 60},
    {7, 61, 7, 61}, {7, 62, 7, 62}, {1, 9, 1, 3}, {1, 10, 1, 4}, {1, 11, 1, 5}, {7, 65, 7, 65}, {7, 66, 7, 66},
    {7, 67, 7, 67}, {7, 68, 7, 68}, {7, 69, 7, 69}, {1, 6, 1, 3}, {1, 7, 1, 4}, {1, 8, 1, 5}, {7, 70, 7, 70},
    {7, 71, 7, 71}, {7, 72, 7, 72}, {7, 73, 7, 73}, {7, 74, 7, 74}, {7, 75, 7, 75}, {7, 76, 7, 76},
    {7, 77, 7, 77}, {7, 78, 7, 78}, {7, 79, 7, 79}, {1, 3, 1, 3}, {1, 4, 1, 4}, {1, 5, 1, 5}, {7, 80, 7, 80},
    {7, 81, 7, 81}, {7, 82, 7, 82}, {7, 83, 7, 83}, {7, 84, 7, 84}, {7, 85, 7, 85},
};

/* 1.50-1.52 [0x8a03e8(var)]: idle of placement var for up to 1800 frames, polling the head each frame. 4U starts
 * the mapped action with 0x92b178 (setAction mode 1, unconditional); the port uses setActionNext (dala_chain), which
 * GU itself queues as a local replay on machines that do not control the tail (MP: every machine follows its head
 * copy, the controller's message carries the same action). */
static void act_follow(void *self, uint32_t var)
{
    sleepFlagA(self);
    sleepFlagB(self);
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        if (var <= 2) {
            MODE(self) = (uint8_t)var;
            dala_motion_keep(self, 101 + 20 * var, 1, 20.0f, 0.0f);
        }
        DALA_WORK(uint8_t, self, W_FOLLOW) = 1;
        TIMER(self) = 1800.0f;
        return;
    }
    if (STEP(self) != 1) return;
    void *head = dala_partner(self);
    if (head)
        for (uint32_t i = 0; i < sizeof k_follow / sizeof *k_follow; i++)
            if (isAction(head, k_follow[i][0], k_follow[i][1])) {
                dala_chain(self, k_follow[i][2], k_follow[i][3]);
                return;
            }
    if (dala_timer(self)) dala_end(self);
}

/* 2.0-2.5 [0x89fb34(var)]: move between body placements: 2.0 0 -> 1, 2.1 1 -> 2, 2.2 2 -> 0, 2.3 0 -> 2,
 * 2.4 1 -> 0, 2.5 2 -> 1 (start motion of the old placement, then the transfer motion; 2.0 / 2.3 add a third) */
static void act_2(void *self, uint32_t var)
{
    static const uint16_t k_mot2[6] = {103, 162, 163, 103, 165, 166};
    static const uint8_t k_mode2[6] = {0, 2, 0, 0, 0, 1};
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        if (var > 5) return;
        MODE(self) = (uint8_t)(var % 3);
        dala_motion_keep(self, 102 + 20 * (var % 3), 1, 20.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        STEP1(self) = 1;
        setTargetMode(self, 0);
        if (var > 5) return;
        if (var == 0 || var == 3) STEP1(self) = 0;
        MODE(self) = k_mode2[var];
        setMotionEx(self, k_mot2[var], 1, 20.0f, 0.0f);
        return;
    case 2:
        if (STEP1(self)) { if (isMotionEnd(self)) dala_end(self); return; }
        if (!isMotionEnd(self)) return;
        STEP1(self)++;
        if (var == 0) { MODE(self) = 1; setMotionEx(self, 161, 1, 20.0f, 0.0f); }
        else if (var == 3) { MODE(self) = 2; setMotionEx(self, 164, 1, 20.0f, 0.0f); }
        return;
    }
}

/* 7.0 [0x8a05c0]: tail attack (motion 613), attack slots 0 / 1 = attackdata 1 / 7; at frame 218 the uShell005
 * tremor 0x661d18(mgr, this, &(-805, 489, -1105), subtype 4, 0xffff, scale 1.0) (dala_shell005.c) and camera
 * shake 6 at (-1006, 1500, -1105) */
typedef void (*camShakePos_t)(void *owner, uint32_t id, const float *pos, uint32_t zero);
#define camShakePos FN(camShakePos_t, 0x49eac)   /* [0xbfe98c(mgr, owner, id, pos)] (Gogmazios em089_shell016.c) */
static void act_7_0(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 613, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 1, 0);
        dala_attack(self, 1, 7, 0);
        return;
    }
    if (STEP(self) != 1) return;
    if (dala_at(self, 218.0f)) {
        static const float shake[4] = {-1006.0f, 1500.0f, -1105.0f, 0.0f};
        static const float tremor[4] = {-805.0f, 489.0f, -1105.0f, 0.0f};
        dala_shell005_post(self, 4, tremor, 1.0f);
        camShakePos(self, 6, shake, 0);
    }
    if (isMotionEnd(self)) dala_end(self);
}

/* 7.1 / 7.2 [0x8a0740(var)]: motion 614 (attackdata 2), 360 frames, then 615 (7.1) or 617 + attackdata 8 (7.2) */
static void act_7_1(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 614, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 2, 0);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = 360.0f;
        return;
    case 2:
        if (!dala_timer(self)) return;
        STEP(self)++;
        if (var) { setMotion(self, 617, 0.0f, 0.0f); dala_attack(self, 0, 8, 0); }
        else setMotion(self, 615, 0.0f, 0.0f);
        return;
    case 3:
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* one-motion attacks inlined in the 4U category-7 dispatcher 0x8a1604: 7.3 (motion 616, attackdata 21, placement
 * 0), 7.20 (633, 3, placement 1), 7.21 (634, 9, 1), 7.40 (653, 4, 2) */
static void act_one(void *self, uint32_t motion, uint32_t mode, uint32_t atk)
{
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = (uint8_t)mode;
        setMotionEx(self, motion, 1, 20.0f, 0.0f);
        dala_attack(self, 0, atk, 0);
        return;
    }
    if (STEP(self) == 1 && isMotionEnd(self)) dala_end(self);
}

/* arena breaks: stage command 4U 0x6c3400(stage, area W+0x14c, mId, 0, 0) breaks kobj mId (k00 = mId 1 at 7.60
 * frame 1238, k01 = mId 2 at 7.61 frame 810; speartip-crag.md, dala_stage.c) */
void dala_arena_break(void *self, uint32_t mid);
#define arena_break dala_arena_break

/* 7.60 [0x8a08bc]: motion 623 (placement 0); attack slot 0 = attackdata 5 (param 2) at frames 420 / 730 / 1220,
 * re-armed (attackReset) at 444 / 756 / 1300; at 1238 the k00 break */
static void act_7_60(void *self, uint32_t var)
{
    (void)var;
    sleepFlagA(self);
    sleepFlagB(self);
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 623, 1, 20.0f, 0.0f);
        return;
    }
    if (STEP(self) != 1) return;
    if (dala_at(self, 420.0f)) dala_attack(self, 0, 5, 2);
    else if (dala_at(self, 444.0f)) attackFlag(self, 0);
    else if (dala_at(self, 730.0f)) dala_attack(self, 0, 5, 2);
    else if (dala_at(self, 756.0f)) attackFlag(self, 0);
    else if (dala_at(self, 1220.0f)) dala_attack(self, 0, 5, 2);
    else if (dala_at(self, 1300.0f)) attackFlag(self, 0);
    if (dala_at(self, 1238.0f)) arena_break(self, 1);
    if (isMotionEnd(self)) dala_end(self);
}

/* 7.61 [inline in 0x8a1604]: motion 624 (placement 0), attackdata 6; at frame 810 the k01 break */
static void act_7_61(void *self, uint32_t var)
{
    (void)var;
    sleepFlagA(self);
    sleepFlagB(self);
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 624, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 6, 0);
        return;
    }
    if (STEP(self) != 1) return;
    if (dala_at(self, 810.0f)) arena_break(self, 2);
    if (isMotionEnd(self)) dala_end(self);
}

/* 7.62 [0x8a0aec]: motion 663 (placement 2), then 664, then 675 back in placement 0 */
static void act_7_62(void *self, uint32_t var)
{
    (void)var;
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        setMotionEx(self, 663, 1, 20.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, 664, 0.0f, 0.0f);
        return;
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        MODE(self) = 0;
        setMotion(self, 675, 0.0f, 0.0f);
        return;
    case 3:
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* placement start of the 7.65.. / 7.68.. / 7.80.. moves: placement 1 / 2 play 679 / 663 (placement 0 none);
 * then timer t0 / t1 / t2 by placement */
static void move_start(void *self, uint32_t var, float t0, float t1, float t2)
{
    dala_begin(self);
    setTargetMode(self, 0);
    if (var == 0) { MODE(self) = 0; TIMER(self) = t0; }
    else if (var == 1) { MODE(self) = 1; setMotionEx(self, 679, 1, 20.0f, 0.0f); TIMER(self) = t1; }
    else if (var == 2) { MODE(self) = 2; setMotionEx(self, 663, 1, 20.0f, 0.0f); TIMER(self) = t2; }
}

/* 7.65-67 (var 2) / 7.70-72 (var 0) / 7.75-77 (var 1) [0x8a0c3c(var)]: wait (420 / 480 / 540), 673, wait 420,
 * 674, then 675 back in placement 0 */
static void act_7_65(void *self, uint32_t var)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0: move_start(self, var, 420.0f, 480.0f, 540.0f); return;
    case 1: if (dala_timer(self)) STEP(self)++; return;
    case 2: if (isMotionEnd(self)) { STEP(self)++; setMotion(self, 673, 0.0f, 0.0f); } return;
    case 3: if (isMotionEnd(self)) { STEP(self)++; TIMER(self) = 420.0f; } return;
    case 4: if (dala_timer(self)) { STEP(self)++; setMotion(self, 674, 0.0f, 0.0f); } return;
    case 5: if (isMotionEnd(self)) { STEP(self)++; MODE(self) = 0; setMotion(self, 675, 0.0f, 0.0f); } return;
    case 6: if (isMotionEnd(self)) dala_end(self); return;
    }
}

/* 7.68-69 (var 2) / 7.73-74 (var 0) / 7.78-79 (var 1) [0x8a0ed0(var)]: wait (540 / 600 / 660), 676, wait 480,
 * 677, then 675 back in placement 0 */
static void act_7_68(void *self, uint32_t var)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0: move_start(self, var, 540.0f, 600.0f, 660.0f); return;
    case 1: if (dala_timer(self)) STEP(self)++; return;
    case 2: if (isMotionEnd(self)) { STEP(self)++; setMotion(self, 676, 0.0f, 0.0f); } return;
    case 3: if (isMotionEnd(self)) { STEP(self)++; TIMER(self) = 480.0f; } return;
    case 4: if (dala_timer(self)) { STEP(self)++; setMotion(self, 677, 0.0f, 0.0f); } return;
    case 5: if (isMotionEnd(self)) { STEP(self)++; MODE(self) = 0; setMotion(self, 675, 0.0f, 0.0f); } return;
    case 6: if (isMotionEnd(self)) dala_end(self); return;
    }
}

/* 7.80-85 [0x8a1154(var, a, b, c)]: up to three coil passes; pass kind 3 / 4 = 676 + wait + 677, other = 673 +
 * wait + 674; c == 255 ends after the second pass. (var, a, b, c): 80 (2, 3, 4, 255), 81 (2, 3, 0, 255),
 * 82 (1, 3, 0, 255), 83 (2, 1, 2, 255), 84 (2, 3, 4, 2), 85 (2, 4, 3, 2) */
static int long_kind(uint32_t k) { return k == 3 || k == 4; }
static void act_7_80(void *self, uint32_t var, uint32_t a, uint32_t b, uint32_t c)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        if (var > 2) { dala_begin(self); setTargetMode(self, 0); return; }
        move_start(self, var, long_kind(a) ? 540.0f : 420.0f, long_kind(a) ? 600.0f : 480.0f,
                   long_kind(a) ? 660.0f : 540.0f);
        return;
    case 1: if (dala_timer(self)) STEP(self)++; return;
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, long_kind(a) ? 676 : 673, 0.0f, 0.0f);
        return;
    case 3:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, long_kind(a) ? 677 : 674, 0.0f, 0.0f);
        return;
    case 4:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = (a == 1 && b == 2) ? 120.0f : 0.0f;
        return;
    case 5:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, long_kind(b) ? 676 : 673, 0.0f, 0.0f);
        return;
    case 6:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = c != 255 ? 0.0f : long_kind(b) ? 660.0f : 540.0f;
        return;
    case 7:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, long_kind(b) ? 677 : 674, 0.0f, 0.0f);
        return;
    case 8:
        if (!isMotionEnd(self)) return;
        if (c == 255) { STEP(self) = 12; MODE(self) = 0; setMotion(self, 675, 0.0f, 0.0f); return; }
        STEP(self)++;
        setMotion(self, long_kind(c) ? 676 : 673, 0.0f, 0.0f);
        return;
    case 9:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = long_kind(c) ? 660.0f : 540.0f;
        return;
    case 10:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, long_kind(c) ? 677 : 674, 0.0f, 0.0f);
        return;
    case 11:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        MODE(self) = 0;
        setMotion(self, 675, 0.0f, 0.0f);
        return;
    case 12:
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* category 7 [0x8a1604] */
static void act_7(void *self, uint32_t num)
{
    static const uint8_t k80[6][4] = {{2, 3, 4, 255}, {2, 3, 0, 255}, {1, 3, 0, 255}, {2, 1, 2, 255},
                                      {2, 3, 4, 2}, {2, 4, 3, 2}};
    switch (num) {
    case 0: act_7_0(self, 0); return;
    case 1: act_7_1(self, 0); return;
    case 2: act_7_1(self, 1); return;
    case 3: act_one(self, 616, 0, 21); return;
    case 20: act_one(self, 633, 1, 3); return;
    case 21: act_one(self, 634, 1, 9); return;
    case 40: act_one(self, 653, 2, 4); return;
    case 60: act_7_60(self, 0); return;
    case 61: act_7_61(self, 0); return;
    case 62: act_7_62(self, 0); return;
    case 65: case 66: case 67: act_7_65(self, 2); return;
    case 68: case 69: act_7_68(self, 2); return;
    case 70: case 71: case 72: act_7_65(self, 0); return;
    case 73: case 74: act_7_68(self, 0); return;
    case 75: case 76: case 77: act_7_65(self, 1); return;
    case 78: case 79: act_7_68(self, 1); return;
    }
    if (num >= 80 && num <= 85) {
        const uint8_t *p = k80[num - 80];
        act_7_80(self, p[0], p[1], p[2], p[3]);
        return;
    }
    /* 4U: other numbers return without ending (the AI never picks them); end them here so the AI keeps running */
    dala_log_action(self, "tail", "unknown 7 -> end");
    dala_end(self);
}

/* category 1 [0x8a030c]: 0-2 idle until the motion end, 6-8 idle for 60 frames, 3-5 one motion, 50-52 follow */
static void act_1(void *self, uint32_t num)
{
    if (num <= 2) act_idle(self, num, 0);
    else if (num <= 5) act_1_3(self, num - 3);
    else if (num <= 8) act_idle(self, num - 6, 1);
    else if (num >= 50 && num <= 52) act_follow(self, num - 50);
    else { dala_log_action(self, "tail", "unknown 1 -> end"); dala_end(self); }
}

/* GU slot 119 = 4U slot 40 0x8a0050 (per frame): the push flag (4U slot 44 tail), the head's rage copied
 * (rage set 0x93399c(this, 1) = GU 0xbce6c, calm 0x91ad80 = GU 0xbd128; callee map C / S) and the stage-8 hold
 * (dala_stage.c) */
#define rageSet  FN(void (*)(void *, uint32_t), 0xbce6c)
#define rageCalm FN(act_base_t, 0xbd128)
#define rageOn   FN(int (*)(void *), 0x8172c)       /* [4U 0x954e48] */
void em091_state_frame(void *self)
{
    dala_state_frame(self);
    void *head = dala_partner(self);
    if (head) {
        if (rageOn(head)) rageSet(self, 1);
        else rageCalm(self);
    }
    dala_arena_frame(self);
    dala_efx_frame(self);            /* the 10/114 smoke's end (dala_efx.c) */
    dala_efx_arrows_frame(self);     /* the end of 4U slot 77 */
    dala_carcass_log(self);
    dala_psl_watch(self);
}

/* GU slot 129 = 4U slot 47 0x8a265c (this, cat, num): the follow flag drops at every action start; 10/114 with hit
 * direction 7 posts qe013_002 on joint 157 (offset (0, 0, -950), scale 4.5) through the effect manager 0xc088d8 and
 * tints it (0xc48378): dala_efx_tail_smoke. Not ported: the call before it, 0x94e39c(this, 0, 0, &point) with point
 * (1784, 232, 2397), placement 1 (-1080, 641, 3750) (no GU mapping checked). */
void em091_action_start(void *self, uint32_t cat, uint32_t num)
{
    dala_ai_tally(self, 1, cat, num);
    DALA_WORK(uint8_t, self, W_FOLLOW) = 0;
    if (cat == 10 && num == 114 && FN(uint32_t (*)(void *), 0x9e994)(self) == 7)
        dala_efx_tail_smoke(self);
}

int dala_hp_band(void *self);    /* em090_act.c */
int dala_broken(void *self);     /* dala_stage.c */
int dala_floor_class(void *self, uint32_t tail);   /* dala_ai.c: 4U 0x93e074 -> 0x9463d0 = GU 0x979cc */

/* GU slot 133 = 4U slot 51 0x8a2864: AI conditions of the tail's command table */
int em091_cond(void *self, uint32_t id)
{
    void *head;
    switch (id) {
    case 0: return MODE(self);
    case 1: head = dala_partner(self); return head ? DALA_WORK(uint8_t, head, 0) : 0;   /* head waits (1.50..) */
    case 2: return dala_broken(self);
    case 3: return dala_hp_band(self);
    case 4:
        /* [0x8a2984] the target's floor as 0..4 (tail table: floor 8 -> 1, 7 -> 0); 0 when slot 0 is empty */
        return dala_floor_class(self, 1);
    case 5: {
        /* 4U 0x775370(head): 0 while the head runs one of its attacks 7.0 / 1 / 20-22 / 40-42 / 86-88 (table
         * 0xfdc838) for less than 120 frames (head work+4), else 1 */
        static const uint8_t k_atk[] = {0, 1, 20, 21, 22, 40, 41, 42, 86, 87, 88};
        head = dala_partner(self);
        if (!head) return 0;
        for (uint32_t i = 0; i < sizeof k_atk; i++)
            if (isAction(head, 7, k_atk[i])) return DALA_WORK(float, head, 4) >= 120.0f;
        return 1;
    }
    }
    return 0;
}

/* GU slot 125 = 4U slot 44 0x8a1e6c: category 0 (0 / 1) -> 1.0 handler, 1, 2 (0-5), 7, 10, 11, 17 (GU base) */
void em091_act_run(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    dala_log_action(self, "tail", "run");
    switch (cat) {
    case 0:
        if (num <= 1) act_idle(self, 0, 0);
        else dala_end(self);                  /* GU end slot 247 may request 0/2 (port-only) */
        break;
    case 1: act_1(self, num); break;
    case 2: if (num <= 5) act_2(self, num); else dala_end(self); break;
    case 7: act_7(self, num); break;
    case 10: case 11: dala_react_tail(self, cat); break;
    case 17: action_base17(self); break;
    default: dala_end(self); break;
    }
}
