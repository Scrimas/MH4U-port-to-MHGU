/* uEm090_00 (head half = 4U uEm024) actions: GU slot 125 = 4U slot 44 0x772fcc, slot 129 = 4U slot 47 0x773f34,
 * slot 133 = 4U slot 51 0x774888. Each handler is a literal translation of the 4U handler named in its comment,
 * 4U frames / timers unchanged (the GU helpers scale them). Motions are em024's (bank << 8 | index).
 * Not ported here (logged): the attack-record byte +0x19 that 4U copies into work+0x58 / +0x5c whenever it arms
 * an attack (no reader found in 4U: dump/scratch/dalamadur-session/workread.py), the radial blur 0xc0819c at joint
 * 5 (1.3-1.11, 2.x: uMhRadialBlurFilter, no calibrated GU blur, dala_efx.c), Shah's effect reset 0x7753f4 (goal
 * D8). Meteor showers 0x77274c: dala_meteor.c. */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_meteor.h"
#include "dala_efx.h"
#include "dala_shah.h"
#include "dala_gather.h"

void dala_react_head(void *self, uint32_t cat);   /* dala_react.c */
int dala_cond_em(void *self);   /* dala_ai.c: 4U EMC op 0x46 (em switch), rebuilt on op 0x6f as id 70 */
void dala_ai_tally(void *self, uint32_t tail, uint32_t cat, uint32_t num);   /* dala_ai.c: next-test log */

typedef int (*isAction_t)(void *self, uint32_t cat, uint32_t num);
#define isAction FN(isAction_t, 0x6ff44)          /* [0x94d788] */
/* 4U 0x92203c (GU 0x7e084, apimap 99): attack reset of both slots (S: called once, 2.5 frame 1640) */
#define attackResetAll FN(act_base_t, 0x7e084)

/* work struct [this+0x8d88] (F_WORK) */
#define W_WAIT     0x00   /* u8: 1.50.. waiting for the tail (read by the tail's AI condition 1) */
#define W_T_ACT    0x04   /* float: frames in this action (0x72708 per frame, cleared at action start) */
#define W_T_MODE   0x08   /* float: frames in this body placement (cleared when the placement changes) */
#define W_MODE     0x0c   /* u8: placement at the last action start */

/* 4U 0x76c99c / 0x76e254: 0xc0819c(effect mgr, area W+0x14c, &joint-5 position) = radial blur (logged, not ported) */
static void net_obj(void *self)
{
    dala_efx_radial_blur(self);
}

/* 1.0-1.2, 0.0-0.1 [0x76df28(var)]: idle of placement var (motions 1 / 21 / 41, kept when already playing);
 * placement 1 arms attack slot 0 with attackdata 8 */
static void act_idle(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        if (var == 0) { MODE(self) = 0; dala_motion_keep(self, 1, 1, 20.0f, 0.0f); }
        else if (var == 1) { MODE(self) = 1; dala_motion_keep(self, 21, 1, 20.0f, 0.0f); dala_attack(self, 0, 8, 0); }
        else if (var == 2) { MODE(self) = 2; dala_motion_keep(self, 41, 1, 20.0f, 0.0f); }
        return;
    }
    if (STEP(self) == 1 && isMotionEnd(self)) dala_end(self);
}

/* the start of 1.3-1.11 and 2.x: idle-to-move motion of placement var (2 / 22 / 42), the attack frame in the timer
 * (168 / 228 / 208); placement 1 arms attackdata 62 */
static void move_enter(void *self, uint32_t var)
{
    dala_begin(self);
    setTargetMode(self, 0);
    if (var == 0) { MODE(self) = 0; dala_motion_keep(self, 2, 1, 20.0f, 0.0f); TIMER(self) = 168.0f; }
    else if (var == 1) {
        MODE(self) = 1;
        dala_motion_keep(self, 22, 1, 20.0f, 0.0f);
        TIMER(self) = 228.0f;
        dala_attack(self, 0, 62, 0);
    } else if (var == 2) { MODE(self) = 2; dala_motion_keep(self, 42, 1, 20.0f, 0.0f); TIMER(self) = 208.0f; }
}

/* 1.3-1.11 [0x76e050(var, kind)]: one head move in placement var; at the timer frame attack slot 0 = attackdata
 * 66 / 46 / 1 (kind 0 / 1 / 2) and the radial blur at joint 5; placement 0 also arms slot 1 = attackdata 10 at
 * frame 135 (param 2) and resets it at 185 */
static void act_1_3(void *self, uint32_t var, uint32_t kind)
{
    static const uint8_t k_atk[3] = {66, 46, 1};
    if (STEP(self) == 0) { move_enter(self, var); return; }
    if (STEP(self) != 1) return;
    if (dala_at(self, TIMER(self))) {
        if (kind <= 2) dala_attack(self, 0, k_atk[kind], 0);
        net_obj(self);
    }
    if (var == 0) {
        if (dala_at(self, 135.0f)) dala_attack(self, 1, 10, 2);
        else if (dala_at(self, 185.0f)) attackFlag(self, 1);
    }
    if (isMotionEnd(self)) dala_end(self);
}

/* 1.50-1.92 [0x76e754(var, k)]: idle of placement var for up to 1800 frames while waiting for the tail to follow
 * (the tail's W_FOLLOW, set by its own 1.50); then the paired action k (table below; the tail copies it through
 * its follow table). The (var, k) of each number are in k_1_50. */
static const uint8_t k_1_50[43][2] = {   /* 4U 0x76e7c4: k -> (cat, num); 0 = none */
    {2, 0}, {2, 1}, {2, 2}, {2, 3}, {2, 4}, {2, 5}, {0, 0}, {0, 0}, {0, 0}, {0, 0}, {7, 60}, {7, 61}, {7, 62},
    {1, 9}, {1, 10}, {1, 11}, {7, 65}, {7, 66}, {7, 67}, {7, 68}, {7, 69}, {1, 6}, {1, 7}, {1, 8}, {7, 70},
    {7, 71}, {7, 72}, {7, 73}, {7, 74}, {7, 75}, {7, 76}, {7, 77}, {7, 78}, {7, 79}, {1, 3}, {1, 4}, {1, 5},
    {7, 80}, {7, 81}, {7, 82}, {7, 83}, {7, 84}, {7, 85},
};
static void act_wait(void *self, uint32_t var, uint32_t k)
{
    if (STEP(self) == 0) {
        dala_begin(self);
        setTargetMode(self, 0);
        if (var <= 2) {
            MODE(self) = (uint8_t)var;
            dala_motion_keep(self, 1 + 20 * var, 1, 20.0f, 0.0f);
        }
        DALA_WORK(uint8_t, self, W_WAIT) = 1;
        TIMER(self) = 1800.0f;
        return;
    }
    if (STEP(self) != 1) return;
    void *tail = dala_partner(self);
    if (tail && DALA_WORK(uint8_t, tail, 0) && k < 43 && k_1_50[k][0]) {
        dala_chain(self, k_1_50[k][0], k_1_50[k][1]);
        return;
    }
    if (dala_timer(self)) dala_end(self);
}

/* 1.50.. number -> (var, k) [0x76e374] */
static const uint8_t k_1_wait[43][2] = {
    {0, 0}, {1, 1}, {2, 2}, {0, 3}, {1, 4}, {2, 5}, {9, 0}, {9, 0}, {9, 0}, {9, 0},           /* 50..59 */
    {0, 10}, {0, 11}, {2, 12}, {0, 13}, {1, 14}, {2, 15}, {2, 16}, {2, 17}, {2, 18}, {2, 19}, /* 60..69 */
    {2, 20}, {0, 21}, {1, 22}, {2, 23}, {0, 24}, {0, 25}, {0, 26}, {0, 27}, {0, 28}, {1, 29}, /* 70..79 */
    {1, 30}, {1, 31}, {1, 32}, {1, 33}, {0, 34}, {1, 35}, {2, 36}, {2, 37}, {2, 38}, {1, 39}, /* 80..89 */
    {2, 40}, {2, 41}, {2, 42},                                                                /* 90..92 */
};

/* attack frame schedules of the 2.x transfer motions [0x76c7b4 step 2]: {frame, slot, attackdata, kind}; kind 0 =
 * attackEx(slot, data, 2), 1 = attackReset(slot), 2 = both slots armed (data, data2), 3 = 0x92203c. The first
 * matching frame wins (4U else-if chain). */
typedef struct { uint16_t frame; uint8_t slot, atk, kind, atk2; } sched_t;
static const sched_t k_s0[] = {{40, 1, 12, 0, 0}, {468, 1, 0, 1, 0}, {526, 0, 14, 0, 0}, {590, 0, 0, 1, 0},
                               {1320, 0, 56, 0, 0}, {1340, 0, 25, 0, 0}, {1440, 0, 0, 1, 0}};
static const sched_t k_s1[] = {{180, 0, 15, 0, 0}, {500, 0, 0, 1, 0}, {1280, 0, 16, 0, 0}, {1356, 0, 0, 1, 0},
                               {1420, 0, 26, 0, 0}, {1480, 0, 0, 1, 0}};
static const sched_t k_s2[] = {{200, 1, 29, 0, 0}, {264, 1, 0, 1, 0}, {1150, 0, 30, 0, 0}, {1250, 0, 0, 1, 0},
                               {1586, 0, 18, 0, 0}, {1750, 0, 0, 1, 0}, {2200, 0, 18, 0, 0}};
static const sched_t k_s3[] = {{40, 1, 67, 0, 0}, {590, 1, 0, 1, 0}, {1380, 0, 20, 0, 0}, {1550, 0, 0, 1, 0},
                               {2240, 0, 31, 0, 0}, {2266, 0, 32, 0, 0}, {2406, 0, 0, 1, 0}};
static const sched_t k_s4[] = {{200, 0, 65, 2, 38}, {220, 0, 0, 1, 0}, {276, 1, 0, 1, 0}, {340, 0, 23, 0, 0},
                               {520, 0, 0, 1, 0}};
static const sched_t k_s5[] = {{216, 0, 34, 0, 0}, {246, 1, 61, 0, 0}, {252, 0, 21, 0, 0}, {260, 1, 0, 1, 0},
                               {688, 0, 0, 1, 0}, {1470, 0, 35, 2, 36}, {1556, 0, 0, 1, 0}, {1640, 0, 0, 3, 0}};
static const struct { const sched_t *s; uint32_t n; } k_sched[6] = {
    {k_s0, 7}, {k_s1, 6}, {k_s2, 7}, {k_s3, 7}, {k_s4, 5}, {k_s5, 8},
};
static void run_sched(void *self, uint32_t var)
{
    if (var > 5) return;
    for (uint32_t i = 0; i < k_sched[var].n; i++) {
        const sched_t *e = &k_sched[var].s[i];
        if (!dala_at(self, (float)e->frame)) continue;
        if (e->kind == 1) attackFlag(self, e->slot);
        else if (e->kind == 3) attackResetAll(self);
        else {
            dala_attack(self, e->slot, e->atk, 2);
            if (e->kind == 2) dala_attack(self, 1, e->atk2, 2);
        }
        return;
    }
}

/* 2.0-2.5 [0x76c7b4(var)]: move between body placements (2.0 0 -> 1 by motion 61, 2.1 1 -> 2 by 62, 2.2 2 -> 0 by
 * 63, 2.3 0 -> 2 by 64, 2.4 1 -> 0 by 65, 2.5 2 -> 1 by 66; 2.0 / 2.3 first play motion 3 in placement 0) */
static void act_2(void *self, uint32_t var)
{
    static const uint8_t k_mot[6] = {3, 62, 63, 3, 65, 66}, k_mode[6] = {0, 2, 0, 0, 0, 1};
    static const uint8_t k_atk[6] = {0, 27, 17, 0, 37, 33};
    sleepFlagA(self);
    sleepFlagB(self);
    switch (STEP(self)) {
    case 0:
        move_enter(self, var < 6 ? var % 3 : 3);
        return;
    case 1:
        if (dala_at(self, TIMER(self))) {
            dala_attack(self, 0, 66, 0);
            net_obj(self);
        }
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        STEP1(self) = 1;
        setTargetMode(self, 0);
        if (var > 5) return;
        if (var == 0 || var == 3) STEP1(self) = 0;
        MODE(self) = k_mode[var];
        setMotionEx(self, k_mot[var], 1, 0.0f, 0.0f);
        if (k_atk[var]) dala_attack(self, 0, k_atk[var], 0);
        return;
    case 2:
        if (STEP1(self) == 0) {
            if (!isMotionEnd(self)) return;
            STEP1(self)++;
            if (var == 0) { MODE(self) = 1; setMotionEx(self, 61, 1, 0.0f, 0.0f); dala_attack(self, 0, 11, 0); }
            else if (var == 3) { MODE(self) = 2; setMotionEx(self, 64, 1, 0.0f, 0.0f); dala_attack(self, 0, 19, 0); }
            return;
        }
        run_sched(self, var);
        if (!isMotionEnd(self)) return;
        dala_shah_reset(self, var);   /* 4U 0x7753f4 (returns at once for Dalamadur) */
        dala_end(self);
        return;
    }
}

/* category 1 [0x76e374] */
static void act_1(void *self, uint32_t num)
{
    if (num <= 2) act_idle(self, num);
    else if (num <= 11) act_1_3(self, (num - 3) % 3, (num - 3) / 3);
    else if (num >= 50 && num <= 92 && k_1_wait[num - 50][0] <= 2) act_wait(self, k_1_wait[num - 50][0], k_1_wait[num - 50][1]);
    else { dala_log_action(self, "head", "unknown 1 -> end"); dala_end(self); }
}

void em090_act7(void *self, uint32_t num);   /* em090_act7.c */

/* GU slot 125 = 4U slot 44 0x772fcc: category 0 (0 / 1) -> 1.0 handler, 1, 2 (0-5), 7, 10, 11, 17 (GU base) */
void em090_act_run(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    dala_log_action(self, "head", "run");
    switch (cat) {
    case 0:
        if (num <= 1) act_idle(self, 0);
        else dala_end(self);                  /* GU end slot 247 may request 0/2 (port-only) */
        break;
    case 1: act_1(self, num); break;
    case 2: if (num <= 5) act_2(self, num); else dala_end(self); break;
    case 7: em090_act7(self, num); break;
    case 10: case 11: dala_react_head(self, cat); break;
    case 17: action_base17(self); break;
    default: dala_end(self); break;
    }
}

/* ---- GU slot 129 = 4U slot 47 0x773f34 (this, cat, num): action start bookkeeping ---- */

/* meteor showers armed at action start [0x77274c(kind, pattern, duration, delay)] (dala_meteor.c) */
static void meteors(void *self, uint32_t kind, uint32_t pattern, float duration, float delay)
{
    dala_meteor_set(self, kind, pattern, duration, delay);
}

/* 4U 0x91ad80 (rage end; GU 0xbd128, class-study.md "Rage", S) */
#define rageEnd FN(act_base_t, 0xbd128)

void em090_action_start(void *self, uint32_t cat, uint32_t num)
{
    dala_ai_tally(self, 0, cat, num);
    uint8_t *rec = REC(self);
    DALA_WORK(uint8_t, self, W_WAIT) = 0;
    DALA_WORK(float, self, W_T_ACT) = 0.0f;
    if (MODE(self) != DALA_WORK(uint8_t, self, W_MODE)) DALA_WORK(float, self, W_T_MODE) = 0.0f;
    DALA_WORK(uint8_t, self, W_MODE) = MODE(self);
    /* both halves sit on the arena origin facing +z: 4U W+0x198 (position) = W+0x150 = zero vector 0x10e6378,
     * W+0x1ac (yaw) = 0 = GU rec+0x40 / rec+0x0 / rec+0x54 (dala_warp, em090_act7.c) */
    dala_warp(self, 0.0f, 0.0f, 0.0f, 0);
    if (cat == 1 && num >= 6 && num <= 11) {
        static const float d0[6] = {1200, 2100, 2100, 1200, 2100, 2100}, d1[6] = {216, 276, 250, 226, 282, 262};
        meteors(self, num <= 8 ? 1 : 3, (num - 6) % 3, d0[num - 6], d1[num - 6]);
    } else if (cat == 2 && num <= 5) {
        static const uint8_t k[6] = {4, 5, 6, 7, 5, 9};
        static const float d0[6] = {1680, 1440, 2580, 2460, 1380, 1560}, d1[6] = {960, 710, 800, 960, 710, 800};
        meteors(self, k[num], 2, d0[num], d1[num]);
    } else if (cat == 7) {
        if (num == 3 || num == 4) meteors(self, 2, 0, 480.0f, 30.0f);
        else if (num >= 24 && num <= 26) meteors(self, 2, 1, 480.0f, 30.0f);
        else if (num >= 44 && num <= 46) meteors(self, 2, 2, 480.0f, 30.0f);
        else if (num >= 65 && num <= 85) {
            /* 65-67 (1, 2), 68-69 (2, 2), 70-72 (1, 0), 73-74 (2, 0), 75-77 (1, 1), 78-79 (2, 1), 80-81 (2, 2),
             * 82 (2, 1), 83 (1, 2), 84-85 (2, 2) */
            static const uint8_t k[21][2] = {{1, 2}, {1, 2}, {1, 2}, {2, 2}, {2, 2}, {1, 0}, {1, 0}, {1, 0},
                                             {2, 0}, {2, 0}, {1, 1}, {1, 1}, {1, 1}, {2, 1}, {2, 1}, {2, 2},
                                             {2, 2}, {2, 1}, {1, 2}, {2, 2}, {2, 2}};
            meteors(self, k[num - 65][0], k[num - 65][1], 300.0f, 60.0f);
        }
    } else if (cat == 10) {
        /* flinches that end the rage: 10/7 by hit direction (placement 0: 0 or 5; 1 / 2: 5), 10/20, 10/148,
         * 10/180 in placement 0 */
        uint32_t m = MODE(self), end = 0;
        if (num == 7) {
            uint32_t d = FN(uint32_t (*)(void *), 0x9e994)(self);
            end = m == 0 ? (d == 0 || d == 5 || d >= 8) : (m <= 2 && d == 5);
        } else if (num == 20 || num == 148) end = 1;
        else if (num == 180) end = m == 0;
        if (end) rageEnd(self);
    } else if (cat == 11) {
        /* 4U head slot 52 0x773128, called by the base's death path 0x9263a4 (0x926f04): meteor machine reset
         * 0x772ac4, work +0x3c = 0, the on-body gathering point work+0x50 released (0x926014: point manager
         * 0x5b90c0 lookup -> 0x5b9ebc release, C; dala_gather.c) (test 2026-10-21: meteors kept falling after the death) */
        dala_meteor_reset(self);
        DALA_WORK(float, self, 0x3c) = 0.0f;
        dala_head_point_release(self);
    }
    /* HP floor: in the mode-0 waits / moves below (and every 10.x in placement 0) the HP cannot drop below its
     * ratio at the action start once that is under 17 %; else no floor (-1). 4U W+0x3f8 = GU rec+0x380 (setHP
     * 0x9a764 clamps HP to [max * rec+0x380, max]; 4U 0x91ad34 the same, both 0x78 after HP like max HP), copied to
     * the tail. */
    uint32_t floor_on = 0;
    if (cat == 1) {
        static const uint8_t k1[] = {0, 3, 6, 9, 53, 63, 71, 74, 75, 76, 77, 78, 84};
        for (uint32_t i = 0; i < sizeof k1; i++) if (num == k1[i]) floor_on = 1;
    } else if (cat == 2) floor_on = num == 3;
    else if (cat == 7) floor_on = num >= 70 && num <= 74;
    else if (cat == 10) floor_on = MODE(self) == 0;
    int32_t max = FIELD(int32_t, rec, REC_HP + 4);
    float r = max > 0 ? (float)FIELD(int32_t, rec, REC_HP) / (float)max : 1.0f;
    FIELD(float, rec, REC_HP_FLOOR) = (floor_on && r < 0.17f) ? r : -1.0f;
    void *tail = dala_partner(self);
    if (tail) FIELD(float, REC(tail), REC_HP_FLOOR) = FIELD(float, rec, REC_HP_FLOOR);
}

/* ---- GU slot 133 = 4U slot 51 0x774888: AI conditions ---- */

/* HP band of 4U conditions 2 (head) / 3 (tail): 4U uses the shared pool mgr+0x328 / max HP; GU keeps both halves'
 * HP equal on the controller (goal D3), so the half's own HP stands for the pool */
int dala_hp_band(void *self)
{
    const uint8_t *rec = REC(self);
    int32_t max = FIELD(int32_t, rec, REC_HP + 4);
    float r = max > 0 ? (float)FIELD(int32_t, rec, REC_HP) / (float)max : 1.0f;
    return r < 0.17f ? 6 : r < 0.44f ? 5 : r < 0.56f ? 4 : r < 0.62f ? 3 : r < 0.84f ? 2 : r < 0.9f ? 1 : 0;
}

int dala_broken(void *self);    /* dala_stage.c: 4U 0x7731a4, highest broken arena piece */
int dala_floor_class(void *self, uint32_t tail);   /* dala_ai.c: 4U 0x93e074 -> 0x9463d0 = GU 0x979cc */

int em090_cond(void *self, uint32_t id)
{
    switch (id) {
    case 0: return MODE(self);
    case 1: return dala_broken(self);
    case 2: return dala_hp_band(self);
    case 3:
        /* [0x774958] the target's floor (Speartip ledge / platform) as 0..4; 0 when target slot 0 is empty */
        return dala_floor_class(self, 0);
    case 4:
        return DALA_WORK(float, self, W_T_MODE) >= ((MODE(self) == 1 || MODE(self) == 2) ? 5400.0f : 2700.0f);
    case 70: return dala_cond_em(self);
    }
    return 0;
}

/* per-frame part of 4U slot 40 0x76da88 used by the actions: the action / placement timers (4U 0xb052c4 = GU
 * 0x72708: t += time scale, apimap 99), the stage-8 hold, then the meteor machine 0x76db4c..0x76de94 */
#define timerUp FN(int (*)(void *, float *), 0x72708)
void em090_state_frame(void *self)
{
    dala_state_frame(self);
    timerUp(self, &DALA_WORK(float, self, W_T_ACT));
    timerUp(self, &DALA_WORK(float, self, W_T_MODE));
    dala_arena_frame(self);
    dala_meteor_frame(self);
    dala_shah_frame(self);           /* 4U 0x76de94, right after the meteor machine */
    dala_head25_frame(self);
    dala_efx_arrows_frame(self);     /* the end of 4U slot 77 */
    dala_mat_frame(self);
    dala_hp_sync(self);
    dala_death_sync(self);
    dala_carcass_log(self);
    dala_psl_watch(self);
}
