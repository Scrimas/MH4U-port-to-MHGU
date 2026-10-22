/* uEm090_00 (head half = 4U uEm024) category 7 (attacks and paired moves): 4U dispatcher 0x771e60. Each handler
 * is a literal translation of the 4U handler named in its comment (framework: em090.h / dala.c, conventions as in
 * em090_act.c and em091_act.c). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"   /* the attack shells (goal D5) */
#include "dala_shah.h"    /* Shah's crimson states (goal D8) */
#include "dala_look.h"    /* the head's look system (goal E) */

typedef int (*isAction_t)(void *self, uint32_t cat, uint32_t num);
#define isAction FN(isAction_t, 0x6ff44)          /* [0x94d788] */
void dala_arena_break(void *self, uint32_t mid);  /* dala_stage.c [0x6c3400] */
int dala_broken(void *self);                      /* dala_stage.c [0x7731a4(area)]: highest broken arena piece */

/* GU calls not in game.h (4U address in brackets; tigerstripe notes/missing-actions.md, callee map) */
#define rageOn     FN(int (*)(void *), 0x8172c)    /* [0x954e48] rage byte (C) */
typedef void (*spinWin_t)(void *self, uint32_t ang, float a, float b);
#define spinWindow FN(spinWin_t, 0x76e8c)          /* [0x9175a8] yaw += ang spread over frames a..b (C) */
#define groundSnap FN(act_base_t, 0x7b5f8)         /* [0x955478] (C, 7/10 pairing) */
/* sound at a joint [0x2fcc50(mgr *0xfccd6c, id, owner, joint, area W+0x14c, -2)] = GU 0x4efd74(mgr *(main+0x1896f5c),
 * ..., unit area +0x1054, -2) (callee map C; Gogmazios em089_snd.c). The ids are the 4U request ids. */
typedef void *(*sndJoint_t)(void *mgr, uint32_t id, void *owner, uint32_t joint, uint32_t area, int32_t m2);
#define sndJoint   FN(sndJoint_t, 0x4efd74)

/* 4U W+0x7a14: the Shah head state word (bits 1 / 2 / 4 = part effect states, written by 0x772cf0) = F_STATE7
 * (dala_parts.c). Always 0 for Dalamadur. */
#define STATE7(self) FIELD(uint32_t, self, F_STATE7)
/* the 4U em test "W+0x1c0 == 24": value d for Dalamadur, s for Shah (em 110) */
static uint32_t by_em(void *self, uint32_t d, uint32_t s) { return FIELD(uint8_t, self, EN_VARIANT) ? s : d; }

/* the head's look system (dala_look.c): 4U writes W+0x79d1 = 1, the fixed origin W+0x79e8, the yaw W+0x79f8 and the
 * u16 step tables W+0x79fc..0x7a12 every frame (set 0: 7.0-7.4 / 7.86, plus the rate W+0x79cc = 0.005; set 1:
 * 7.41-7.46 / 7.88), the look point W+0x79d8 = target slot 0 through 0x93e974(this, NULL, 0) and the mode byte
 * W+0x79d0 = 3 (GU uEnemy this+0x7520..0x7570; the base resets mode / flag / rate every frame in both games) */
static void look_setup(void *self, uint32_t set) { dala_look_setup(self, set); }
static void look_point(void *self) { dala_look_point(self); }
static void look_mode(void *self) { dala_look_mode(self, 3); }

/* 4U this+0xca8 |= bits every frame before the step switch (0x800 / 0x1000 / 0x4000). No effect (C, 2026-10-22): the
 * word is per-class scratch: no 4U base code reads it on an enemy, other 4U classes keep their own values in it
 * (GU's Capcom twins write the bit index into this+0xb5f8 instead, read only by class code: pairs 0x6df15c / 0xd008e8,
 * 0x6e07c8 / 0xd0137c, 0x6f0fb0 / 0xd4f440), and Dalamadur's class never tests it (head / tail ranges scanned). */
static void render_flag(void *self, uint32_t bits) { (void)self; (void)bits; }

/* 4U 0x77250c(this, kind, lim, ang, flag): the fireball uShell001 of kind (24 / 25 Dalamadur, 88 / 89 Shah) from the
 * joint 5 matrix toward target slot 0 W+0x218 (direction clamped by lim / ang, spawn data 0x773e00), posted through
 * 0x661bec(mgr *0xef3cf0, this, &data, kind, 0xffff). Only a post (no monster state): dala_shell001.c. */
static void shell(void *self, uint32_t kind, uint32_t lim, uint32_t ang, uint32_t flag)
{
    dala_head_fireball(self, kind, lim, ang, flag);
}

/* 4U 0x6620c4(mgr *0xef3cf0, this, &{5, (0, -273, 751, 0), 0, 0xe39, 0}, subtype 21 / Shah 39, 0xffff, 0, 0, 12000):
 * the uShell016 mouth beam of the sink passes (C: subtypes 21 / 39 = a capsule from joint 5, not a quake; earlier
 * notes called it the quake post): dala_shell016.c */
static void quake(void *self)
{
    static const float off[3] = {0.0f, -273.0f, 751.0f};
    dala_shell016_post(self, by_em(self, 21, 39), 5, off, 0xe39, 0, 12000.0f);
}

/* 4U 0x7756d4(this, -, k, value): returns at once for em 24; Shah arms effect slot k (work +120 + 48 k = state 110 + k,
 * a fixed point by k, value, 1200), clearing the other active slots first (0x775f2c): dala_shah.c (goal D8). */
static void shah_slot(void *self, uint32_t k, float v) { dala_shah_slot(self, k, v); }

static void se_joint(void *self, uint32_t id, uint32_t joint)
{
    void *mgr = *(void **)MAIN(0x1896f5c);
    if (mgr) sndJoint(mgr, id, self, joint, FIELD(uint8_t, self, 0x1054), -2);
}

/* 4U 0x93947c(this, mot, mot1, flags, blend, start): setMotionEx, then the layer-1 motion mot1 with the same flags /
 * blend (callee map S: GU 0xafda4 + 0xb000c) */
static void motion_layer(void *self, uint32_t mot, uint32_t mot1, uint32_t flags, float blend, float start)
{
    setMotionEx(self, mot, flags, blend, start);
    layer1Motion(self, mot1, flags, blend, start);
}

/* 4U 0x948800(this, from, to = target slot W+0x218 = GU rec+464, yaw, limit): the angle from `from` to the target
 * minus yaw (u16), over limit, clamped to 1; 0 when the angle lies on the other side than limit's sign. Only Dalamadur
 * calls it and GU has no counterpart (callee map G): translated here. atan2 0x568c8c = libm atan2f -> u16 angle
 * (api-map S, as em089_aim.c). The result goes to the layer-1 weight [0xb054e0 = layer1SetWeight]. */
static float aim_weight(void *self, const float *from, uint32_t yaw, int32_t limit)
{
    const float *to = (const float *)(REC(self) + REC_TARGET);
    float v = atan2f_gu(to[0] - from[0], to[2] - from[2]) * 10430.378f;   /* 65536 / 2pi */
    uint32_t d = ((uint32_t)(int32_t)(v + (v < 0.0f ? -0.5f : 0.5f)) - yaw) & 0xffff;
    if (d > 0x8000) {
        if (limit > 0) return 0.0f;
        limit = -limit;
        d = 0x10000 - d;
    } else if (limit <= 0) return 0.0f;
    float w = ((float)d * 360.0f * (1.0f / 65536.0f)) / ((float)limit * 360.0f * (1.0f / 65536.0f));
    return w > 1.0f ? 1.0f : w;
}

/* 7.0 / 7.3 (var 0), 7.2 / 7.4 (var 1) [0x76ec80(var)]: motion 513 (placement 0), attack slot 0 = attackdata 47; at
 * frame 318 the shell 0x77250c (kind 25 / Shah 89, var 1: 24 / 88); slot 1 = attackdata 10 (param 2) at 250, reset
 * at 320. Look set 0 every frame, look point at the start, look mode inside frames 0..322. */
static void act_7_0(void *self, uint32_t var)
{
    look_setup(self, 0);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 513, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 47, 0);
        look_point(self);
        return;
    case 1:
        if (motionCheck(self, 3, 0, 0.0f, 322.0f)) look_mode(self);
        if (dala_at(self, 318.0f)) shell(self, var == 1 ? by_em(self, 24, 88) : by_em(self, 25, 89), 0xe39, 0xdc73, 0);
        if (dala_at(self, 250.0f)) dala_attack(self, 1, 10, 2);
        else if (dala_at(self, 320.0f)) attackFlag(self, 1);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.1 [0x76efc8]: motion 516 (placement 0), attack slots 0 / 1 = attackdata 7 / 48; slot 0 = attackdata 58 (param 2)
 * at frame 208, reset at 318 */
static void act_7_1(void *self)
{
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 516, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 7, 0);
        dala_attack(self, 1, 48, 0);
        return;
    case 1:
        if (dala_at(self, 208.0f)) dala_attack(self, 0, 58, 2);
        else if (dala_at(self, 318.0f)) attackFlag(self, 0);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.20 / 7.24 [0x76f158]: motion 533 (placement 1), attack slots 0 / 1 = attackdata 2 / 42; slot 0 = attackdata 59
 * at frame 290 (reset 356) and 55 at 386 (reset 418), param 2; then a 0-frame wait and motion 535 (blend 8). Shah
 * state bit 1: sound 216 at joint 4 at 160, effect slot 0 at 260. Render flag 0x800 (state bit 1, < 2 pieces broken)
 * or 0x1000. */
static void act_7_20(void *self)
{
    render_flag(self, ((STATE7(self) & 1) && dala_broken(self) < 2) ? 0x800 : 0x1000);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 1;
        setMotionEx(self, 533, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 2, 0);
        dala_attack(self, 1, 42, 0);
        return;
    case 1:
        if (dala_at(self, 290.0f)) dala_attack(self, 0, 59, 2);
        else if (dala_at(self, 356.0f)) attackFlag(self, 0);
        else if (dala_at(self, 386.0f)) dala_attack(self, 0, 55, 2);
        else if (dala_at(self, 418.0f)) attackFlag(self, 0);
        if (STATE7(self) & 1) {
            if (dala_at(self, 160.0f)) se_joint(self, 216, 4);
            if (dala_at(self, 260.0f)) shah_slot(self, 0, 500.0f);
        }
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = 0.0f;
        return;
    case 2:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, 535, 8.0f, 0.0f);
        return;
    case 3:
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.21 / 7.25 (var 0), 7.23 / 7.26 (var 1) [0x76f518(var)]: motion 534 + layer-1 537 (placement 1, flags 17), the
 * layer aimed from (4031.3, 0, 2735.28) at the target (yaw 0xa4cd, limit 0x45de); attack slot 0 = attackdata 43; at
 * frame 382 the shell 0x77250c (kind 25 / Shah 89, var 1: 24 / 88; flag 1) */
static void act_7_21(void *self, uint32_t var)
{
    static const float from[4] = {4031.3f, 0.0f, 2735.28f, 0.0f};
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 1;
        motion_layer(self, 534, 537, 17, 20.0f, 0.0f);
        layer1SetWeight(self, aim_weight(self, from, 0xa4cd, 0x45de));
        dala_attack(self, 0, 43, 0);
        return;
    case 1:
        if (dala_at(self, 382.0f)) shell(self, var == 1 ? by_em(self, 24, 88) : by_em(self, 25, 89), 0x11c7, 0x31c7, 1);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.22 [0x76f6bc]: motion 536 (placement 1), attack slot 0 = attackdata 4. Shah state bit 2: sound 215 at joint 10 at
 * frame 120, effect slot 0 at 270. Render flag 0x800 (state bit 2, < 2 pieces broken) or 0x1000. */
static void act_7_22(void *self)
{
    render_flag(self, ((STATE7(self) & 2) && dala_broken(self) < 2) ? 0x800 : 0x1000);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 1;
        setMotionEx(self, 536, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 4, 0);
        return;
    case 1:
        if (STATE7(self) & 2) {
            if (dala_at(self, 120.0f)) se_joint(self, 215, 10);
            if (dala_at(self, 270.0f)) shah_slot(self, 0, 1000.0f);
        }
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.40 / 7.44 [0x76f898]: motion 553 + layer-1 554 (placement 2, flags 17), the layer aimed from (-1327.54, 0,
 * 3504.52) (yaw 0x419a, limit 0x2c44); attack slot 0 = attackdata 3, then 60 at frame 290 (reset 358); slot 1 =
 * attackdata 44 at 300 (reset 350) and 45 at 380 (reset 420), param 2. Shah state bit 1: sound 216 at joint 4 at 210,
 * effect slot 1 at 220. Render flag: state bit 1 -> 0x4000 when joint 6 is less than 400 above the ground probe
 * 0x2b9fa8 (callee map G, not mapped), else 0x800; no bit -> 0x1000. */
static void act_7_40(void *self)
{
    static const float from[4] = {-1327.54f, 0.0f, 3504.52f, 0.0f};
    render_flag(self, (STATE7(self) & 1) ? 0x4800 : 0x1000);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        motion_layer(self, 553, 554, 17, 20.0f, 0.0f);
        layer1SetWeight(self, aim_weight(self, from, 0x419a, 0x2c44));
        dala_attack(self, 0, 3, 0);
        return;
    case 1:
        if (dala_at(self, 290.0f)) dala_attack(self, 0, 60, 0);
        else if (dala_at(self, 358.0f)) attackFlag(self, 0);
        if (dala_at(self, 300.0f)) dala_attack(self, 1, 44, 2);
        else if (dala_at(self, 350.0f)) attackFlag(self, 1);
        else if (dala_at(self, 380.0f)) dala_attack(self, 1, 45, 2);
        else if (dala_at(self, 420.0f)) attackFlag(self, 1);
        if (STATE7(self) & 1) {
            if (dala_at(self, 210.0f)) se_joint(self, 216, 4);
            if (dala_at(self, 220.0f)) shah_slot(self, 1, 500.0f);
        }
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.41 / 7.45 (var 0), 7.43 / 7.46 (var 1) [0x76fce8(var)]: motion 555 (placement 2), attack slot 0 = attackdata
 * 57; at frame 380 the shell 0x77250c (kind 25 / Shah 89, var 1: 24 / 88; flag 2); slot 1 = attackdata 49 at 84, 57
 * at 144 (reset 166), 50 at 170 (reset 200). Look set 1 every frame, look point at the start, look mode inside frames
 * 0..392. */
static void act_7_41(void *self, uint32_t var)
{
    look_setup(self, 1);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        setMotionEx(self, 555, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 57, 0);
        look_point(self);
        return;
    case 1:
        if (motionCheck(self, 3, 0, 0.0f, 392.0f)) look_mode(self);
        if (dala_at(self, 380.0f)) shell(self, var == 1 ? by_em(self, 24, 88) : by_em(self, 25, 89), 0x11c7, 0x238e, 2);
        if (dala_at(self, 84.0f)) dala_attack(self, 1, 49, 0);
        else if (dala_at(self, 144.0f)) dala_attack(self, 1, 57, 0);
        else if (dala_at(self, 166.0f)) attackFlag(self, 1);
        else if (dala_at(self, 170.0f)) dala_attack(self, 1, 50, 0);
        else if (dala_at(self, 200.0f)) attackFlag(self, 1);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.42 [0x7700c4]: motion 557 (placement 2), attack slots 0 / 1 = attackdata 51 / 52; slot 0 = attackdata 53 at frame
 * 110 (reset 128) and 5 at 180 (reset 290), param 2. Shah state bit 4: sound 215 at joint 15 at 115, effect slot 2
 * at 145. Render flag 0x800 (state bit 4) or 0x1000. */
static void act_7_42(void *self)
{
    render_flag(self, (STATE7(self) & 4) ? 0x800 : 0x1000);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        setMotionEx(self, 557, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 51, 0);
        dala_attack(self, 1, 52, 0);
        return;
    case 1:
        if (dala_at(self, 110.0f)) dala_attack(self, 0, 53, 2);
        else if (dala_at(self, 128.0f)) attackFlag(self, 0);
        else if (dala_at(self, 180.0f)) dala_attack(self, 0, 5, 2);
        else if (dala_at(self, 290.0f)) attackFlag(self, 0);
        if (STATE7(self) & 4) {
            if (dala_at(self, 115.0f)) se_joint(self, 215, 15);
            if (dala_at(self, 145.0f)) shah_slot(self, 2, 1000.0f);
        }
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.60 / 7.61 [0x7703d4 / 0x7704f0]: the head holds its placement-0 idle while the tail breaks k00 / k01 (its own
 * 7.60 / 7.61), and ends once the tail's action is over */
static void act_7_60(void *self, uint32_t num)
{
    void *tail = dala_partner(self);
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        dala_motion_keep(self, 1, 1, 20.0f, 0.0f);
        return;
    case 1:
        if (isMotionEnd(self)) STEP(self)++;
        return;
    case 2:
        if (!tail || !isAction(tail, 7, num)) dala_end(self);
        return;
    }
}

/* 7.62 [0x77060c]: the spire k02: motion 563 (placement 2), then 564 with attack slot 0 = attackdata 63 (param 2)
 * at frames 488 / 688 / 940 (reset at 498 / 704 / 1112) and the k02 break at 1082, then 575 back in placement 0 */
static void act_7_62(void *self)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        setMotionEx(self, 563, 1, 20.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, 564, 0.0f, 0.0f);
        return;
    case 2:
        if (dala_at(self, 488.0f)) dala_attack(self, 0, 63, 2);
        else if (dala_at(self, 498.0f)) attackFlag(self, 0);
        else if (dala_at(self, 688.0f)) dala_attack(self, 0, 63, 2);
        else if (dala_at(self, 704.0f)) attackFlag(self, 0);
        else if (dala_at(self, 940.0f)) dala_attack(self, 0, 63, 2);
        else if (dala_at(self, 1112.0f)) attackFlag(self, 0);
        if (dala_at(self, 1082.0f)) dala_arena_break(self, 3);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        MODE(self) = 0;
        setMotion(self, 575, 0.0f, 0.0f);
        return;
    case 3:
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* warp: 4U writes the vector to both W+0x150 and the position W+0x198 and the yaw to W+0x1ac; GU's warps write the
 * same pair, rec+0x0 and the position rec+0x40 (e.g. 0xe2fd28 / 0xe30164, paired with 4U 0x70bcec), C */
void dala_warp(void *self, float x, float y, float z, uint32_t yaw)
{
    uint8_t *rec = REC(self);
    float *a = &FIELD(float, rec, 0x0), *p = &FIELD(float, rec, REC_POS_X);
    a[0] = p[0] = x; a[1] = p[1] = y; a[2] = p[2] = z; a[3] = p[3] = 0.0f;
    FIELD(uint32_t, rec, REC_YAW) = yaw;
}

/* 7.65-67 / 7.70-72 / 7.75-77 [0x770954(sub, placement)]: the coil attack. Wait in the placement (420 / 480 /
 * 540 frames; placements 1 / 2 play 579 / 563 first), then motion 573 at one of three points off the arena (sub 0..2,
 * warp), attack slot 0 = attackdata 6 (param 2) at frames 170 / 250 (reset 190 / 294), wait 420, motion 574, then
 * 575 back at the arena origin in placement 0. (sub, placement): 65 (0, 2), 66 (1, 2), 67 (2, 2), 70 (0, 0), 71 (1,
 * 0), 72 (2, 0), 75 (0, 1), 76 (1, 1), 77 (2, 1) */
static void act_7_65(void *self, uint32_t sub, uint32_t mode)
{
    static const float k_pos[3][3] = {{8921, -14539, 1773}, {-1474, -14250, 11693}, {-9810, -14100, 4360}};
    static const uint16_t k_yaw[3] = {0xbf76, 0x79c7, 0x49f5};
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        if (mode == 0) { MODE(self) = 0; TIMER(self) = 420.0f; }
        else if (mode == 1) { MODE(self) = 1; setMotionEx(self, 579, 1, 20.0f, 0.0f); TIMER(self) = 480.0f; }
        else if (mode == 2) { MODE(self) = 2; setMotionEx(self, 563, 1, 20.0f, 0.0f); TIMER(self) = 540.0f; }
        return;
    case 1:
        if (dala_timer(self)) STEP(self)++;
        return;
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, 573, 0.0f, 0.0f);
        if (sub <= 2) dala_warp(self, k_pos[sub][0], k_pos[sub][1], k_pos[sub][2], k_yaw[sub]);
        return;
    case 3:
        if (dala_at(self, 170.0f)) dala_attack(self, 0, 6, 2);
        else if (dala_at(self, 190.0f)) attackFlag(self, 0);
        else if (dala_at(self, 250.0f)) dala_attack(self, 0, 6, 2);
        else if (dala_at(self, 294.0f)) attackFlag(self, 0);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = 420.0f;
        return;
    case 4:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, 574, 0.0f, 0.0f);
        return;
    case 5:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        MODE(self) = 0;
        setMotion(self, 575, 0.0f, 0.0f);
        dala_warp(self, 0.0f, 0.0f, 0.0f, 0);
        return;
    case 6:
        if (!isMotionEnd(self)) return;
        dala_shah_reset(self, 0);   /* 4U 0x7753f4 (returns at once for Dalamadur) */
        dala_end(self);
        return;
    }
}

/* 4U: vertical speed W+356 (GU rec+0x14) = (-16969 - height W+412 (rec+0x44)) / 58, after the warp to the second
 * sink point (0x770ec0 sub 1, 0x7759e8 kind 4) */
static void rise(void *self)
{
    uint8_t *rec = REC(self);
    FIELD(float, rec, REC_VEL + 4) = (-16969.0f - FIELD(float, rec, REC_POS_X + 4)) * 0.0172413792f;
}

/* the second sink pass, per frame [0x770ec0 step 3 sub 1 = 0x775cbc kind 4]: turn by 0xfffff444 over frames 280..380,
 * 0x955478 inside 448..506, height W+412 = -16969 at 506 */
static void coil_sink(void *self)
{
    spinWindow(self, 0xfffff444u, 280.0f, 380.0f);
    if (motionCheck(self, 3, 0, 448.0f, 506.0f)) groundSnap(self);
    if (dala_at(self, 506.0f)) FIELD(float, REC(self), REC_POS_X + 4) = -16969.0f;
}

/* 7.68-69 / 7.73-74 / 7.78-79 [0x770ec0(sub, placement)]: the sink attack. Wait in the placement (540 / 600 / 660
 * frames; placements 1 / 2 play 579 / 563 first), then motion 576 at one of two sink points (sub 0 / 1, warp; sub 1
 * stops and rises toward -16969, turns over 280..380 and lands at 506), the quake post at 248, wait 480, motion 577,
 * then 575 back at the arena origin in placement 0. (sub, placement): 68 (0, 2), 69 (1, 2), 73 (0, 0), 74 (1, 0),
 * 78 (0, 1), 79 (1, 1) */
static void act_7_68(void *self, uint32_t sub, uint32_t mode)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        if (mode == 0) { MODE(self) = 0; TIMER(self) = 540.0f; }
        else if (mode == 1) { MODE(self) = 1; setMotionEx(self, 579, 1, 20.0f, 0.0f); TIMER(self) = 600.0f; }
        else if (mode == 2) { MODE(self) = 2; setMotionEx(self, 563, 1, 20.0f, 0.0f); TIMER(self) = 660.0f; }
        return;
    case 1:
        if (dala_timer(self)) STEP(self)++;
        return;
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, 576, 0.0f, 0.0f);
        if (sub == 0) dala_warp(self, 5224.0f, -17332.0f, -3455.0f, 0xeacf);
        else if (sub == 1) {
            dala_warp(self, -3321.0f, -17949.0f, 10261.0f, 0x7e02);
            stopMove(self);
            rise(self);
        }
        return;
    case 3:
        if (sub == 1) coil_sink(self);
        if (dala_at(self, 248.0f)) quake(self);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = 480.0f;
        return;
    case 4:
        if (!dala_timer(self)) return;
        STEP(self)++;
        setMotion(self, 577, 0.0f, 0.0f);
        return;
    case 5:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        MODE(self) = 0;
        setMotion(self, 575, 0.0f, 0.0f);
        dala_warp(self, 0.0f, 0.0f, 0.0f, 0);
        return;
    case 6:
        if (!isMotionEnd(self)) return;
        dala_shah_reset(self, 0);   /* 4U 0x7753f4 (returns at once for Dalamadur) */
        dala_end(self);
        return;
    }
}

/* one coil pass of 7.80-85, kind 0..2 = the three points off the arena (as 7.65), 3 / 4 = the two sink points (as
 * 7.68 sub 0 / 1). Start [0x7759e8(kind)]: stop, motion 573 / 576, warp; kind 4 rises. */
static void pass_start(void *self, uint32_t kind)
{
    static const float k_pos[5][3] = {{8921, -14539, 1773}, {-1474, -14250, 11693}, {-9810, -14100, 4360},
                                      {5224, -17332, -3455}, {-3321, -17949, 10261}};
    static const uint16_t k_yaw[5] = {0xbf76, 0x79c7, 0x49f5, 0xeacf, 0x7e02};
    stopMove(self);
    if (kind > 4) return;
    setMotion(self, kind <= 2 ? 573 : 576, 0.0f, 0.0f);
    dala_warp(self, k_pos[kind][0], k_pos[kind][1], k_pos[kind][2], k_yaw[kind]);
    if (kind == 4) rise(self);
}

/* per frame [0x775cbc(kind)]: kinds 0..2 attack slot 0 = attackdata 6 (param 2) at frames 170 / 250 (reset 190 /
 * 294); kind 4 the sink turn / landing; kinds 3 / 4 the quake post at 248 */
static void pass_frame(void *self, uint32_t kind)
{
    if (kind <= 2) {
        if (dala_at(self, 170.0f)) dala_attack(self, 0, 6, 2);
        else if (dala_at(self, 190.0f)) attackFlag(self, 0);
        else if (dala_at(self, 250.0f)) dala_attack(self, 0, 6, 2);
        else if (dala_at(self, 294.0f)) attackFlag(self, 0);
    }
    if (kind == 4) coil_sink(self);
    if ((kind == 3 || kind == 4) && dala_at(self, 248.0f)) quake(self);
}

/* the return motion of a pass (574 / 577) and the wait after it (540 / 660); kinds > 4 nothing (4U jump tables) */
static void pass_end(void *self, uint32_t kind)
{
    if (kind <= 2) setMotion(self, 574, 0.0f, 0.0f);
    else if (kind <= 4) setMotion(self, 577, 0.0f, 0.0f);
}
static void pass_wait(void *self, uint32_t kind)
{
    if (kind <= 2) TIMER(self) = 540.0f;
    else if (kind <= 4) TIMER(self) = 660.0f;
}

/* back at the arena origin in placement 0 (motion 575), the last step 12 */
static void pass_back(void *self)
{
    STEP(self) = 12;
    MODE(self) = 0;
    setMotion(self, 575, 0.0f, 0.0f);
    dala_warp(self, 0.0f, 0.0f, 0.0f, 0);
}

/* 7.80-85 [0x7713ec(placement, a, b, c)]: up to three coil passes of kinds a, b, c (the tail's twin 0x8a1154 =
 * em091_act.c act_7_80); c == 255 ends after the second pass. Wait in the placement (kind a 3 / 4: 540 / 600 / 660,
 * else 420 / 480 / 540), pass a, 120 frames when (a, b) = (1, 2), pass b, (c == 255: wait 540 / 660,) pass c, then
 * 575 back at the origin. (placement, a, b, c): 80 (2, 3, 4, 255), 81 (2, 3, 0, 255), 82 (1, 3, 0, 255), 83 (2, 1,
 * 2, 255), 84 (2, 3, 4, 2), 85 (2, 4, 3, 2) */
static int long_kind(uint32_t k) { return k == 3 || k == 4; }
static void act_7_80(void *self, uint32_t mode, uint32_t a, uint32_t b, uint32_t c)
{
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        if (mode == 0) { MODE(self) = 0; TIMER(self) = long_kind(a) ? 540.0f : 420.0f; }
        else if (mode == 1) {
            MODE(self) = 1;
            setMotionEx(self, 579, 1, 20.0f, 0.0f);
            TIMER(self) = long_kind(a) ? 600.0f : 480.0f;
        } else if (mode == 2) {
            MODE(self) = 2;
            setMotionEx(self, 563, 1, 20.0f, 0.0f);
            TIMER(self) = long_kind(a) ? 660.0f : 540.0f;
        }
        return;
    case 1:
        if (dala_timer(self)) STEP(self)++;
        return;
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        pass_start(self, a);
        return;
    case 3:
        pass_frame(self, a);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        pass_end(self, a);
        return;
    case 4:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        TIMER(self) = (a == 1 && b == 2) ? 120.0f : 0.0f;
        return;
    case 5:
        if (!dala_timer(self)) return;
        STEP(self)++;
        pass_start(self, b);
        return;
    case 6:
        pass_frame(self, b);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        if (c != 255) TIMER(self) = 0.0f;
        else pass_wait(self, b);
        return;
    case 7:
        if (!dala_timer(self)) return;
        STEP(self)++;
        pass_end(self, b);
        return;
    case 8:
        if (!isMotionEnd(self)) return;
        if (c == 255) { pass_back(self); return; }
        STEP(self)++;
        pass_start(self, c);
        return;
    case 9:
        pass_frame(self, c);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        pass_wait(self, c);
        return;
    case 10:
        if (!dala_timer(self)) return;
        STEP(self)++;
        pass_end(self, c);
        return;
    case 11:
        if (isMotionEnd(self)) pass_back(self);
        return;
    case 12:
        if (!isMotionEnd(self)) return;
        dala_shah_reset(self, 0);   /* 4U 0x7753f4 (returns at once for Dalamadur) */
        dala_end(self);
        return;
    }
}

/* 7.86 [0x77199c]: motion 522 (placement 0), attack slot 0 = attackdata 47; at frame 210 the shell 0x77250c (kind
 * raging 24 / Shah 88, else 25 / 89). Look set 0 every frame, look point at the start and inside motionCheck(2, 210),
 * look mode every frame of step 1. */
static void act_7_86(void *self)
{
    look_setup(self, 0);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 0;
        setMotionEx(self, 522, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 47, 0);
        look_point(self);
        return;
    case 1:
        if (motionCheck(self, 2, 0, 210.0f, 0.0f)) look_point(self);
        look_mode(self);
        if (dala_at(self, 210.0f))
            shell(self, rageOn(self) ? by_em(self, 24, 88) : by_em(self, 25, 89), 0xe39, 0xdc73, 0);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.87 [0x771cb4]: motion 542 + layer-1 547 (placement 1, flags 17), the layer aimed from (4031.3, 0, 2735.28) (yaw
 * 0xa4cd, limit 0x471c); attack slot 0 = attackdata 43; at frame 212 the shell 0x77250c (kind raging 24 / Shah 88,
 * else 25 / 89; flag 1) */
static void act_7_87(void *self)
{
    static const float from[4] = {4031.3f, 0.0f, 2735.28f, 0.0f};
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 1;
        motion_layer(self, 542, 547, 17, 20.0f, 0.0f);
        layer1SetWeight(self, aim_weight(self, from, 0xa4cd, 0x471c));
        dala_attack(self, 0, 43, 0);
        return;
    case 1:
        if (dala_at(self, 212.0f))
            shell(self, rageOn(self) ? by_em(self, 24, 88) : by_em(self, 25, 89), 0x11c7, 0x31c7, 1);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* 7.88 [0x772208]: motion 559 (placement 2), attack slot 0 = attackdata 49; at frame 204 the shell 0x77250c (kind
 * raging 24 / Shah 88, else 25 / 89; flag 2). Look set 1 every frame, look point at the start and inside
 * motionCheck(2, 228), look mode every frame of step 1. */
static void act_7_88(void *self)
{
    look_setup(self, 1);
    switch (STEP(self)) {
    case 0:
        dala_begin(self);
        setTargetMode(self, 0);
        MODE(self) = 2;
        setMotionEx(self, 559, 1, 20.0f, 0.0f);
        dala_attack(self, 0, 49, 0);
        look_point(self);
        return;
    case 1:
        if (motionCheck(self, 2, 0, 228.0f, 0.0f)) look_point(self);
        look_mode(self);
        if (dala_at(self, 204.0f))
            shell(self, rageOn(self) ? by_em(self, 24, 88) : by_em(self, 25, 89), 0x1555, 0xe39, 2);
        if (isMotionEnd(self)) dala_end(self);
        return;
    }
}

/* category 7 [0x771e60] */
void em090_act7(void *self, uint32_t num)
{
    static const uint8_t k80[6][4] = {{2, 3, 4, 255}, {2, 3, 0, 255}, {1, 3, 0, 255}, {2, 1, 2, 255},
                                      {2, 3, 4, 2}, {2, 4, 3, 2}};
    switch (num) {
    case 0: case 3: act_7_0(self, 0); return;
    case 2: case 4: act_7_0(self, 1); return;
    case 1: act_7_1(self); return;
    case 20: case 24: act_7_20(self); return;
    case 21: case 25: act_7_21(self, 0); return;
    case 23: case 26: act_7_21(self, 1); return;
    case 22: act_7_22(self); return;
    case 40: case 44: act_7_40(self); return;
    case 41: case 45: act_7_41(self, 0); return;
    case 43: case 46: act_7_41(self, 1); return;
    case 42: act_7_42(self); return;
    case 60: case 61: act_7_60(self, num); return;
    case 62: act_7_62(self); return;
    case 65: act_7_65(self, 0, 2); return;
    case 66: act_7_65(self, 1, 2); return;
    case 67: act_7_65(self, 2, 2); return;
    case 68: act_7_68(self, 0, 2); return;
    case 69: act_7_68(self, 1, 2); return;
    case 70: act_7_65(self, 0, 0); return;
    case 71: act_7_65(self, 1, 0); return;
    case 72: act_7_65(self, 2, 0); return;
    case 73: act_7_68(self, 0, 0); return;
    case 74: act_7_68(self, 1, 0); return;
    case 75: act_7_65(self, 0, 1); return;
    case 76: act_7_65(self, 1, 1); return;
    case 77: act_7_65(self, 2, 1); return;
    case 78: act_7_68(self, 0, 1); return;
    case 79: act_7_68(self, 1, 1); return;
    case 86: act_7_86(self); return;
    case 87: act_7_87(self); return;
    case 88: act_7_88(self); return;
    }
    if (num >= 80 && num <= 85) {
        const uint8_t *p = k80[num - 80];
        act_7_80(self, p[0], p[1], p[2], p[3]);
        return;
    }
    /* 4U: other numbers return without ending (the AI never picks them); end them so the AI keeps running */
    dala_log_action(self, "head", "unknown 7 -> end");
    dala_end(self);
}
