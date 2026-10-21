/* em067_01_moves.c: Tigerstripe Zamtrios' actions that GU's uEm067_00 has no handler for (notes/missing-actions.md).
 * 4U em092's command table asks for them (3/3, 3/4, 7/70, 7/77, 7/78, 7/200, 7/201); GU's slot-125 dispatcher sends
 * an unknown action to its default case, the base thunks 0xca118 (categories 3, 4, 5, 9, 14, 15, > 17) / 0xca10c
 * (category-7 numbers without a case), which only call virtual slot 247 (vt+0x3dc, end of action), so the action
 * ended the same frame. Entry hooks on both thunks: for a uEm067_00 (vtable 0x17e4800) of variant 1 whose current
 * action has a handler here, run the handler and return 1 (the thunk is skipped and control goes back into GU's
 * dispatcher, which then runs its own post-step: the TS speed flag work[0x10] -> motion speed x 0.95). Every other
 * call goes on to slot 247 as before.
 *
 * Each handler is a step-by-step translation of the 4U uEm022 handler named in its comment, with the GU callees and
 * fields of notes/missing-actions.md section 2 (step bytes rec+0x1a1..0x1a3). Not ported: 4U W+0x7948 = 1 while
 * airborne (no GU field found). 7/70's uShell016 38 / 49 shot: em067_01_shell016.c (notes/blast.md).
 * Multiplayer: GU's pre-step has already run and these handlers run on every machine, as GU's own do; none calls
 * setAction (all end through slot 247), damage stays with GU's attack slots (notes section 6). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EM067_VTABLE 0x17e4800u     /* uEm067_00 object vtable (slot 125 = 0xf78f98, slot 247 = 0xf7a308) */
#define EN_VARIANT   (EN_ID + 5)
#define EN_WORK      0xcac0         /* uEm067_00 work block: +0 inflate timer, +0xc inflate count, +0x10 TS flag */
#define REC(self)    FIELD(uint8_t *, self, EN_RECORD)
#define RF(rec, off) FIELD(float, rec, off)

/* ---- GU callees not in game.h (notes/missing-actions.md 2a) */
typedef void (*attack_t)(void *self, uint32_t slot, uint32_t index);
#define attack       FN(attack_t, 0x7df94)        /* [0x914dfc] attackEx with param 0 */
typedef void (*selfF_t)(void *self, float v);
#define vertSet      FN(selfF_t, 0xbf7bc)         /* rec+0x5c = v, rec+0x1b9 = 1 [0x916140] */
typedef int (*onGround_t)(void *self, float h);
#define onGround     FN(onGround_t, 0xbf5e8)      /* pos.y <= ground (+ h * size) [0x93e4e8] */
typedef void (*self_t)(void *self);
#define ballistic    FN(self_t, 0x7d718)          /* pos += v dt + a dt^2 / 2, v += a dt (world) [0x9110c8] */
#define groundSnap   FN(self_t, 0x7b5f8)          /* [0x955478] */
#define statusReset  FN(self_t, 0xb7584)          /* this+0x73f3..0x73f6 [W+0x1f1..0x1f4] */
typedef void (*statusTimer_t)(void *self, uint32_t n);
#define statusTimer  FN(statusTimer_t, 0x9d104)   /* [0x93cfd4] */
typedef float *(*vecOf_t)(void *self);
#define restPoint    FN(vecOf_t, 0x712a4)         /* [0x91df20 -> +0x48] */
typedef float (*groundAt_t)(void *self, int32_t point, float s);
#define groundAt     FN(groundAt_t, 0xa77b0)      /* ground y at a map point [0x924040] */
typedef void (*spinWin_t)(void *self, uint32_t ang, float a, float b);
#define spinWindow   FN(spinWin_t, 0x76e8c)       /* yaw += ang / (b - a) per frame inside a..b [0x9175a8] */
typedef void (*actRoll_t)(void *self, const float *pos, uint32_t a, uint32_t b);
#define actionRoll   FN(actRoll_t, 0xac0ec)       /* action-start roll [0x911f58] */
typedef void (*camShake_t)(void *self, int32_t joint, uint32_t id, uint32_t zero);
#define camShakeJoint FN(camShake_t, 0xc24d8)     /* [0x910c6c] */
typedef void *(*paramAlloc_t)(uint32_t size, uint32_t align);
#define paramAlloc   FN(paramAlloc_t, 0x3faf28)
typedef void *(*shellRequest_t)(void *mgr, void *param, uint32_t a, uint32_t b);
#define shellRequest FN(shellRequest_t, 0x48c4f0)
#define SHELL_MGR    (*(void **)MAIN(0x1892550))

static void flag(void *self) { FIELD(uint8_t *, self, EN_WORK)[0x10] = 1; }    /* TS speed flag (4U wrappers) */
static int mc(void *self, uint32_t kind, float a, float b) { return motionCheck(self, kind, 0, a, b); }
static int at_frame(void *self, float f) { return motionCheck(self, 0, 0, f, 0.0f); }
static void end_action(void *self) { VCALL0(self, SLOT_ACTION_END); }
static int32_t find_point(void *self, int32_t m1, uint32_t m2) { return findTargetEx(self, 0, m1, m2, 4); }

/* the 4U uShell005 tremor (subtype 13 x 1.65 = GU sp_01 kind 2, r990): copy of GU's post f71ef8..f71fb4 */
static void tremor(void *self, uint32_t kind)
{
    const uint32_t *rec = (const uint32_t *)REC(self), *v = (const uint32_t *)MAIN(0x191e850);
    uint32_t *p = paramAlloc(64, 16);
    if (!p) return;
    p[0] = MAIN(0x1755698) + 8; p[1] = 0x122; p[2] = kind; p[3] = (uint32_t)(uintptr_t)self;
    p[4] = rec[0x40 / 4]; p[5] = rec[0x44 / 4]; p[6] = rec[0x48 / 4]; p[7] = 0;
    p[8] = v[0]; p[9] = v[1]; p[10] = v[2]; p[11] = 0;
    p[12] = rec[0x50 / 4]; p[13] = rec[0x54 / 4]; p[14] = rec[0x58 / 4];
    FIELD(uint16_t, p, 0x3c) = 0xffff;
    shellRequest(SHELL_MGR, p, 0, 0);
}

/* 4U 3/x frame 24 = GU's mode-2 entry f69e88..f69f70 (Tigerstripe skips the anger reset 0xbd128) */
static void mode2_enter(void *self)
{
    uint8_t *rec = REC(self), *work = FIELD(uint8_t *, self, EN_WORK);
    rec[REC_MODE] = 2;
    FIELD(float, work, 0) = 4800.0f;
    for (uint32_t r = 0; r < 8; r++) partMeatBase(self, r);
    if (++work[0xc] >= 3) work[0xc] = 2;
    statusTimer(self, 1000);
    statusReset(self);
    RF(rec, 0x5d24) = 0.0f; rec[0x5df8] = 0; FIELD(uint16_t, rec, 0x5d28) = 0;
}

/* ---- 3/0..3/3, 4U 0x747a78(v = num) and 3/4, 4U 0x747554: Tigerstripe's jumps (3/3 / 3/4 aimed at the target) */
static const float k_jump_h[4] = { 870.0f, 1540.0f, 545.0f, 1500.0f };

/* the crouch before the jump: 3/x step 1 = 3/4 step 2 (no frame-24 mode change there) */
static void jump_crouch(void *self, uint32_t v, int mode2)
{
    uint8_t *rec = REC(self);
    setMotionSpeed(self, 0.85f); flag(self);
    if (mc(self, 9, 28.0f, 64.0f) && v == 3) turnToTarget(self, 455, 0);
    if (mc(self, 1, 68.0f, 0.0f)) { FIELD(uint8_t, self, 0x7452) = 0; FIELD(uint8_t, self, 0x7453) = 0; rec[0x5b58] = 1; }
    rec[0x52a] = 1;
    if (mode2 && at_frame(self, 24.0f)) mode2_enter(self);
    if (!isMotionEnd(self)) return;
    rec[REC_STEP0]++;
    sleepFlagB(self);
    restApply(self, 556.0f);
    vertSet(self, FIELD(float, self, EN_DT) * 350.0f - 700.0f);
    setMotion(self, 0x451, 1e-7f, 0.0f); flag(self);
    float h = v < 4 ? k_jump_h[v] : 300.0f;
    if (v == 3) {                                         /* aimed: reach the target's xz at the apex + 30 frames */
        const float *t = (const float *)(rec + REC_TARGET);
        RF(rec, 0x10) = (t[0] - RF(rec, 0x40)) / 60.0f;
        RF(rec, 0x14) = 0.0f;
        RF(rec, 0x18) = (t[2] - RF(rec, 0x48)) / 60.0f;
        RF(rec, 0x1c) = 0.0f;
    }
    RF(rec, 0x24) = -2.0f * h / 900.0f;
    RF(rec, 0x14) = 2.0f * h / 30.0f;
}

/* airborne until the landing: 3/x step 2 = 3/4 step 3 */
static void jump_air(void *self, uint32_t v)
{
    uint8_t *rec = REC(self);
    vertSet(self, 0.0f);
    rec[0x919] = 1; rec[0x52a] = 1;
    sleepFlagB(self);
    if (v == 3) ballistic(self); else accelVel(self, rec + 0x50, 1);
    if (mc(self, 9, 0.0f, 60.0f)) turnToTarget(self, 273, 0);
    if (!(RF(rec, 0x14) < 0.0f && onGround(self, 556.0f))) return;
    rec[REC_STEP0]++;
    setTargetMode(self, 0);
    setMotion(self, 0x452, 0.0f, 0.0f); flag(self);
    attack(self, 0, 54);
    attackEx(self, 1, 67, 64);
    tremor(self, 2);
    camShakeJoint(self, -1, 1, 0);
}

static void act_jump(void *self, uint32_t v)                       /* 3/0..3/3 */
{
    uint8_t *rec = REC(self);
    sleepFlagA(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0); rec[0x52a] = 1; stopMove(self);
        setMotionEx(self, 0x450, 2, 4.0f, 0.0f); flag(self);
        if (v < 3) { static const float vy[3] = { 66.0f, 110.0f, 40.0f }; RF(rec, 0x14) = vy[v]; RF(rec, 0x18) = 20.0f; }
        break;
    case 1: jump_crouch(self, v, 1); break;
    case 2: jump_air(self, v); break;
    default: if (isMotionEnd(self)) end_action(self); break;
    }
}

static void act_3_0(void *self) { act_jump(self, 0); }
static void act_3_1(void *self) { act_jump(self, 1); }
static void act_3_2(void *self) { act_jump(self, 2); }
static void act_3_3(void *self) { act_jump(self, 3); }

static void act_3_4(void *self)                                    /* 4U 0x747554 */
{
    uint8_t *rec = REC(self);
    sleepFlagA(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0); rec[0x52a] = 1;
        setMotionEx(self, 0x46b, 2, 6.0f, 0.0f); flag(self);
        break;
    case 1:
        setMotionSpeed(self, 0.85f); flag(self); rec[0x52a] = 1;
        if (at_frame(self, 4.0f)) layer1MotionW(self, 0x450, 4.0f, 0.0f);
        if (mc(self, 3, 4.0f, 28.0f)) layer1SetWeight(self, 1.0f - (28.0f - motionFrame(self)) / 24.0f);
        if (at_frame(self, 28.0f)) {
            rec[REC_STEP0] = 2;
            setTargetMode(self, 0); stopMove(self);
            setMotion(self, 0x450, 0.0f, 28.0f); flag(self);
        }
        break;
    case 2: jump_crouch(self, 3, 0); break;
    case 3: jump_air(self, 3); break;
    default: if (isMotionEnd(self)) end_action(self); break;
    }
}

/* ---- 7/70, 4U 0x74ff88: turn, the sand / air blast at frame 90 (em067_01_shell016.c), leave mode 2 at frame 134 */
void *em067_01_blast_post(void *self, uint32_t subtype, uint32_t d);
typedef void (*jointMtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx     FN(jointMtx_t, 0xc1660)      /* [0x930894] */
#define STAGE_PTR    0x188ca48u                   /* [[ ]+0x48] = current stage (gogmazios/module/stage.c) */
#define STAGE_DUNES  5u                           /* 4U W+0x14b == 17 */

/* 4U 0x750144..0x7501f4: pitch from the mouth (joint 131 + M (0, -60, 0)) to the target + 100 up, relative to the
 * body pitch, clamped to +20 / -15 deg; 4U subtracts the angles snapshot this+0x8d20 (previous frame's W+0x1a8), here
 * the current rec+0x50 (notes/blast.md 3a) */
static void blast(void *self)
{
    uint8_t *rec = REC(self);
    float j[4], m[16], p[3], h;
    jointPos(self, 131, j);
    jointMtx(self, 131, m);
    for (int i = 0; i < 3; i++) p[i] = j[i] - 60.0f * m[4 + i];
    const float *t = (const float *)(rec + REC_TARGET);
    float dx = t[0] - p[0], dy = t[1] + 100.0f - p[1], dz = t[2] - p[2];
    h = dx * dx + dz * dz;
    __asm__("vsqrt.f32 %0, %1" : "=t"(h) : "t"(h));
    uint32_t a = (uint32_t)(int32_t)(atan2f_gu(-dy, h) * (65536.0f / 6.28318531f)) & 0xffff;
    uint32_t d = (a - FIELD(uint32_t, rec, REC_ANGLES)) & 0xffff;
    if (d < 0x8000) { if (d > 0xe39) d = 0xe39; }
    else if (d < 0xf555) d = 0xf555;
    const uint8_t *st = *(const uint8_t **)MAIN(STAGE_PTR);
    em067_01_blast_post(self, st && st[0x48] == STAGE_DUNES ? 38 : 49, d);
}

static void act_7_70(void *self)
{
    uint8_t *rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x455, 4.0f, 0.0f); flag(self);
        break;
    case 1:
        turnToTarget(self, 242, 0);
        if (at_frame(self, 90.0f)) { rec[REC_STEP0] = 2; blast(self); }
        break;
    default:
        if (at_frame(self, 134.0f)) rec[REC_MODE] = 0;
        if (isMotionEnd(self)) end_action(self);
        break;
    }
}

/* ---- 7/77, 7/78, 4U 0x751464(v = 0 / 1): rolling along walls with ledge steps (GU's 7/10 variant-1 step,
 * f71894..f71c44, with Tigerstripe's masks, window and wall loop) */
static void turn_yaw(void *self, uint32_t target)
{
    uint8_t *rec = REC(self);
    uint32_t step = (uint32_t)(FIELD(float, self, EN_DT) * 1280.0f), yaw = FIELD(uint32_t, rec, 0x54);
    uint32_t d = (target - yaw) & 0xffff;
    if (d < 0x8000) yaw = d >= step ? (yaw + step) & 0xffff : target & 0xffff;
    else yaw = 0x10000 - d >= step ? (yaw - step) & 0xffff : target & 0xffff;
    FIELD(uint32_t, rec, 0x54) = yaw;
}

static void act_roll(void *self, uint32_t v)
{
    uint8_t *rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1; rec[REC_STEP1] = 0;
        setTargetMode(self, 0);
        setMotion(self, v ? 0x456 : 0x454, 4.0f, 0.0f); flag(self);
        attack(self, 0, v ? 66 : 65);
        actionRoll(self, (const float *)(rec + 0x40), 3, 0);  /* 4U action start 0x75bb10 (GU's list lacks 7/77-78) */
        return;
    }
    if (rec[REC_STEP1]) {                                     /* stepping up / down a ledge */
        sleepFlagA(self); sleepFlagB(self);
        rec[0x528] = 1; rec[0x5b58] = 1; rec[0x5bc] = 1;
        if (rec[REC_STEP1] == 2) rec[0x919] = 1;
        if (find_point(self, 66560, 20480) == -1)
            for (uint32_t i = 0; i < rec[0x8f0]; i++) {       /* wall loop: roll along the walls met */
                uint32_t a = FIELD(uint32_t, rec, 0x7bc + 32 * i);
                if (a - 8193 < 0x3fff) turn_yaw(self, a + (v ? 0x4000 : 0xc000));
                if (a - 40961 < 0x2fff) turn_yaw(self, a + (v ? 0xc000 : 0x4000));
            }
        groundSnap(self);
        if (RF(rec, 0x34) <= RF(rec, 0x44) && rec[REC_STEP1] == 1) { stopMove(self); RF(rec, 0x44) = RF(rec, 0x34); }
        if (RF(rec, 0x44) <= RF(rec, 0x34) && rec[REC_STEP1] == 2) { stopMove(self); RF(rec, 0x44) = RF(rec, 0x34); }
        if (timerDown(self, &RF(rec, 0x1bc), 1.0f)) {
            stopMove(self);
            RF(rec, 0x44) = RF(rec, 0x34);
            const float *p = restPoint(self);
            RF(rec, 0x900) = p[0]; RF(rec, 0x904) = p[1]; RF(rec, 0x908) = p[2]; RF(rec, 0x90c) = 0.0f;
            rec[REC_STEP1] = 0;
        }
    } else if (mc(self, 9, 105.0f, 137.0f)) {                 /* look for a ledge ahead */
        int32_t r = find_point(self, 1024, 20480);
        if (r != -1) rec[REC_STEP1] = 1;
        else if ((r = find_point(self, 65536, 20480)) != -1) rec[REC_STEP1] = 2;
        if (r != -1) {
            float g = groundAt(self, r, 1.8f), dy;
            RF(rec, 0x34) = g;
            dy = g - RF(rec, 0x44);
            if (dy > 700.0f || dy < -700.0f) { rec[REC_STEP1] = 0; return; }
            stopMove(self);
            if (rec[REC_STEP1] == 1) {
                RF(rec, 0x14) = dy / 34.0f;
                const float *p = restPoint(self);
                RF(rec, 0x900) = p[0]; RF(rec, 0x904) = p[1] + dy + 100.0f; RF(rec, 0x908) = p[2];
                RF(rec, 0x90c) = 0.0f;
            } else
                RF(rec, 0x14) = dy / 68.0f;
            RF(rec, 0x1bc) = 68.0f;
        }
    }
    if (isMotionEnd(self)) end_action(self);
}

static void act_7_77(void *self) { act_roll(self, 0); }
static void act_7_78(void *self) { act_roll(self, 1); }

/* ---- 7/200, 4U 0x7549a4: slow spin until the timer runs out or a map point is found */
static void act_7_200(void *self)
{
    uint8_t *rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        setMotion(self, 0x46a, 6.0f, 0.0f); flag(self);
        attackEx(self, 0, 59, 2);
        RF(rec, 0x1bc) = 600.0f;
        break;
    case 1:
        if (mc(self, 1, 140.0f, 0.0f)) rec[REC_STEP0] = 2;
        break;
    case 2:
        spinWindow(self, 0xff4a, 0.0f, 600.0f);
        if (!timerDown(self, &RF(rec, 0x1bc), 1.0f) && find_point(self, 66560, 8192) == -1) break;
        if (mc(self, 1, 310.0f, 0.0f)) {
            rec[REC_STEP0] = 3;
            setMotion(self, 0x466, 20.0f, 0.0f); flag(self);
        }
        break;
    default:
        if (isMotionEnd(self)) end_action(self);
        break;
    }
}

/* ---- 7/201, 4U 0x754be8: up to three side slides, alternating (Tigerstripe skips Zamtrios' frame-190 tremor) */
static void act_7_201(void *self)
{
    uint8_t *rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        rec[REC_STEP1] = 3; rec[REC_STEP2] = 0;
        stopMove(self);
        float s = speedFactor(self);
        RF(rec, 0x10) = -10.8f * s; RF(rec, 0x14) = 0.0f; RF(rec, 0x18) = 16.6667f * s; RF(rec, 0x1c) = 0.0f;
        setMotion(self, 0x46b, 6.0f, 0.0f); flag(self);
        return;
    }
    if (rec[REC_STEP0] == 1) {
        rec[REC_STEP0] = 2;
        attack(self, 0, 61);
    }
    if (mc(self, 9, 115.0f, 175.0f)) { sleepFlagB(self); rotateVel(self, rec + 0x50, 1); }
    if (at_frame(self, 172.0f)) camShakeJoint(self, -1, 5, 0);
    if (rec[REC_STEP2] == 0 && find_point(self, 66560, 8192) != -1) {
        rec[REC_STEP2]++;
        rec[REC_STEP1] = 1;
    } else if (rec[REC_STEP1] > 1 && mc(self, 1, 210.0f, 0.0f)) {
        rec[REC_STEP0] = 1;
        rec[REC_STEP1]--;
        RF(rec, 0x10) = -RF(rec, 0x10);
        setMotion(self, 0x46b, 20.0f, 80.0f); flag(self);
    }
    if (isMotionEnd(self)) end_action(self);
}

typedef void (*move_fn)(void *self);
static const struct { uint8_t cat, num; move_fn fn; } s_moves[] = {
    { 3, 0, act_3_0 }, { 3, 1, act_3_1 }, { 3, 2, act_3_2 },  /* ledge chain only: unreachable for em092 (notes 4) */
    { 3, 3, act_3_3 }, { 3, 4, act_3_4 },
    { 7, 70, act_7_70 }, { 7, 77, act_7_77 }, { 7, 78, act_7_78 }, { 7, 200, act_7_200 }, { 7, 201, act_7_201 },
    { 0, 0, 0 },
};

/* only the dispatcher's own no-case calls run a move: ca118 from f790d8 (bl, category default) returns to f790dc,
 * ca10c from f75b38 (tail call inside 0xf75678, called by f790f0) to f790f4. Any other caller of these generic
 * end-of-action thunks (an interrupt, an AI reset) really ends the move: running it instead left the AI resuming from
 * a null script pointer (test 2026-10-21 08:20, crash in the EMC decoder 0x50ce0 after 7/54). */
static int run_move(uint32_t *regs, uint32_t ret)
{
    void *self = (void *)regs[R0];
    if (!self || FIELD(uint32_t, self, 0) != MAIN(EM067_VTABLE) || FIELD(uint8_t, self, EN_VARIANT) != 1)
        return 0;
    uint8_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_CAT + 1);
    for (uint32_t i = 0; s_moves[i].fn; i++)
        if (s_moves[i].cat == cat && s_moves[i].num == num) {
            if (regs[LR] - MAIN_BASE != ret) {
                static uint32_t s_end;
                if (++s_end <= 20) logf("tzport: em067_01 ported move %u/%u ended by %x", cat, num, regs[LR] - MAIN_BASE);
                return 0;
            }
            static uint32_t s_n;
            if (REC(self)[REC_STEP0] == 0 && ++s_n <= 40) logf("tzport: em067_01 ported move %u/%u starts", cat, num);
            s_moves[i].fn(self);
            return 1;
        }
    return 0;
}

int em067_01_end_c(uint32_t *regs) { return run_move(regs, 0xf790dcu); }     /* 0xca118: categories without a case */
int em067_01_end7_c(uint32_t *regs) { return run_move(regs, 0xf790f4u); }    /* 0xca10c: category-7 numbers */
