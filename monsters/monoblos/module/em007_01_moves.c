/* em007_01_moves.c: Monoblos (GU Diablos variant 1, ID 0x107): his ported 4U actions (notes/actions.md).
 *
 * His AI table (tools/build_em007_01_arc.py cmdtbl) starts his 4U action (c, n) as GU's twin action where GU's Diablos
 * has one (TW rows below = the build's TWINS, checked there), else as (c, PORT_BASE + n): numbers GU's uEm007_00
 * dispatchers never handle (cat 1 0..35, 2 0..200, 3 0..9, 6 0..50, 7 0..200, C). GU's slot-127 remap only touches
 * category-2 numbers <= 16 and its slot-129 start code switches on bounded number ranges (0xd35318 / 0xd3545c, C), so
 * ours pass both untouched.
 * Dispatch: em007_01_act_c (em007_01_diag.c, entry hook on GU slot 125 0xd35e58) calls em007_01_moves_run. For a
 * Monoblos in one of our numbers it does what GU's slot 125 does around a handler: work+8 = 0 (0xd35e70), the handler
 * (the MV row of the 4U number: a literal port of his 4U handler with the 4U dispatcher's parameters), then GU's common
 * tail 0xd35f9c (gu_tail), and returns 1 (GU's dispatch skipped). A 4U action without a row yet ends at once (logged).
 * 4U's own dispatcher (slot 44 0x8df448) tail-calls its sub-dispatchers and has no common tail (C); GU's tail keeps
 * GU's own bookkeeping (work+9, the work+12 timer and its limit work+16) running as for every GU action.
 * Multiplayer: slot 125 runs every frame on every machine, as GU's own handlers. */
#include "em007_01.h"
#include "alloc.h"
#include "port.h"

#define PORT_BASE 208

/* GU callees */
typedef int (*isAction_t)(void *self, uint32_t cat, uint32_t num);
#define isAction    FN(isAction_t, 0x6ff44)
typedef int (*selfInt_t)(void *self);
#define slowState   FN(selfInt_t, 0x816d0)      /* [0x92e998] rec+0x505 in {2, 3} */
#define GU_DT       (*(float *)(**(uint8_t ***)MAIN(0x1838d84) + 104))     /* GU 0xd36050..0xd36060 */

/* 4U action -> GU's twin (= TWINS of tools/build_em007_01_arc.py, which checks these rows) */
#define TW(c, n, gc, gn) {c, n, gc, gn}
static const uint8_t s_twins[][4] = {
    TW(0, 2, 0, 2), TW(1, 25, 1, 3),
    TW(3, 0, 3, 3), TW(3, 7, 3, 7), TW(6, 14, 6, 26),
};

static void gu_action(uint32_t cat, uint32_t n, uint32_t *gc, uint32_t *gn)
{
    for (uint32_t i = 0; i < sizeof s_twins / sizeof s_twins[0]; i++)
        if (s_twins[i][0] == cat && s_twins[i][1] == n) {
            *gc = s_twins[i][2];
            *gn = s_twins[i][3];
            return;
        }
    *gc = cat;
    *gn = PORT_BASE + n;
}

void mb_chain(void *self, uint32_t cat, uint32_t n)
{
    uint32_t gc, gn;
    gu_action(cat, n, &gc, &gn);
    setActionNext(self, gc, gn);
}

void mb_chain_now(void *self, uint32_t cat, uint32_t n)
{
    uint32_t gc, gn;
    gu_action(cat, n, &gc, &gn);
    setActionNow(self, gc, gn);
}

struct mb_state *mb_state(void *self)
{
    static struct mb_state s[4];
    static uint32_t next;
    uint32_t q = port_quest_id();
    struct mb_state *p = 0;
    for (uint32_t i = 0; i < 4 && !p; i++)
        if (s[i].self == self) p = &s[i];
    if (p && p->quest == q) return p;
    if (!p) p = &s[next++ & 3];
    *p = (struct mb_state){0};                              /* new, or a new quest: its handles died with the old one */
    p->self = self;
    p->quest = q;
    return p;
}

/* ---- ported 4U handlers (p = the 4U sub-dispatcher's r1, r2, r3, [sp]) */
typedef void (*move_t)(void *self, const uint8_t *p);
void mbmv_8db41c(void *self, const uint8_t *p);    /* em007_01_mv_a.c: horn charge 7/3 10 24 25 34 */
void mbmv_8d9af8(void *self, const uint8_t *p);    /* em007_01_mv_a.c: stuck horn 1/2, then 1/27 */
void mbmv_1_27(void *self, const uint8_t *p);      /* em007_01_mv_a.c: horn pulled out (sub 0x8ddf24 case 27) */
void mbmv_8da42c(void *self, const uint8_t *p);    /* em007_01_mv_b.c: digging in 1/28 29 32 33, then 7/14 15 29 30 */
void mbmv_8dc13c(void *self, const uint8_t *p);    /* em007_01_mv_b.c: underground attack 7/13 14 15 28 29 30 33 */
void mbmv_8d9c9c(void *self, const uint8_t *p);    /* em007_01_mv_c.c: roar 1/21 1/34 */
void mbmv_8d83a0(void *self, const uint8_t *p);    /* em007_01_mv_c.c: roar 2/7 */
void mbmv_8da77c(void *self, const uint8_t *p);    /* em007_01_mv_c.c: scrape 1/31, then 7/25 */
void mbmv_8d7d8c(void *self, const uint8_t *p);    /* em007_01_mv_d.c: walk 2/0 21 25 26 */
void mbmv_8d81d0(void *self, const uint8_t *p);    /* em007_01_mv_d.c: run 2/6 22 */
void mbmv_8d93c4(void *self, const uint8_t *p);    /* em007_01_mv_d.c: approach 2/19 20 23 */
void mbmv_2_turn(void *self, const uint8_t *p);    /* em007_01_mv_d.c: turns 2/3 5 17 24 (sub 0x8dda24 inline) */
void mbmv_8d7f08(void *self, const uint8_t *p);    /* em007_01_mv_a.c: charge run 2/2 */
void mbmv_8d8518(void *self, const uint8_t *p);    /* em007_01_mv_a.c: fast charge run 2/10 */
void mbmv_1_1(void *self, const uint8_t *p);       /* em007_01_mv_e.c: idle loop 1/1 (sub 0x8ddf24 inline) */
void mbmv_1_motion(void *self, const uint8_t *p);  /* em007_01_mv_e.c: one motion 1/4 19 35 (sub 0x8ddf24 inline) */
void mbmv_8dabd8(void *self, const uint8_t *p);    /* em007_01_mv_f.c: double horn swing 7/2 7/19 */
void mbmv_8dbf80(void *self, const uint8_t *p);    /* em007_01_mv_f.c: half-turn horn swing 7/31 7/32 */
void mbmv_7_1(void *self, const uint8_t *p);       /* em007_01_mv_f.c: horn swing 7/1 (sub 0x8db020 inline) */
void mbmv_7_8(void *self, const uint8_t *p);       /* em007_01_mv_f.c: 7/8 (sub 0x8db020 inline) */
void mbmv_8db998(void *self, const uint8_t *p);    /* em007_01_mv_a.c: charge run into a thrust 7/4 7/21 */
void mbmv_8d89d0(void *self, const uint8_t *p);    /* em007_01_mv_d.c: stalk 2/12 14 18 */
void mbmv_3_1(void *self, const uint8_t *p);       /* em007_01_mv_g.c: settle and turn 3/1 (sub 0x8d9688 inline) */
void mbmv_8d6a74(void *self, const uint8_t *p);    /* em007_01_mv_g.c: climb toward the target 3/2 */
void mbmv_8d6c80(void *self, const uint8_t *p);    /* em007_01_mv_g.c: walk to the target 3/3 */
void mbmv_8d6e04(void *self, const uint8_t *p);    /* em007_01_mv_g.c: fall and land 3/4 */
void mbmv_6_rest(void *self, const uint8_t *p);    /* em007_01_mv_h.c: rest 6/1 6/7 (sub 0x8dc83c inline) */
void mbmv_6_turn(void *self, const uint8_t *p);    /* em007_01_mv_h.c: resting turn 6/3 6/13, 6/11 18 19 (0x8dd624) */
void mbmv_8dc708(void *self, const uint8_t *p);    /* em007_01_mv_h.c: waking up 6/2 */
void mbmv_8dd310(void *self, const uint8_t *p);    /* em007_01_mv_h.c: lying burrowed 6/8 6/9 */
void mbmv_8dd704(void *self, const uint8_t *p);    /* em007_01_mv_h.c: burrowed run 6/12 */
void mbmv_8dcc80(void *self, const uint8_t *p);    /* em007_01_mv_h.c: burrowed travel 6/4 15 16 20 */
void mbmv_8daa48(void *self, const uint8_t *p);    /* em007_01_mv_f.c: horn swing with a turn 7/0 7/18 */
void mbmv_8dbbbc(void *self, const uint8_t *p);    /* em007_01_mv_f.c: horn thrust with a turn 7/5 7/22 */
void mbmv_8dbd0c(void *self, const uint8_t *p);    /* em007_01_mv_f.c: horn sweep with a turn 7/6 7/20 */
void mbmv_8dbe34(void *self, const uint8_t *p);    /* em007_01_mv_f.c: roaring horn sweep 7/7 */
void mbmv_8dae90(void *self, const uint8_t *p);    /* em007_01_mv_f.c: horn upswing 7/9 */
void mbmv_1_20(void *self, const uint8_t *p);      /* em007_01_mv_e.c: tail sweep 1/20 (sub 0x8ddf24 inline) */
void mbmv_8dc5b4(void *self, const uint8_t *p);    /* em007_01_mv_h.c: lying down 6/0 6/17 */
void mbmv_8d8cc0(void *self, const uint8_t *p);    /* em007_01_mv_i.c: the charge's spin turn 2/13 2/15 */

struct move { uint8_t cat, num; move_t run; uint8_t p[4]; uint32_t site; };
#define MV(c, n, fn, a, b, d, e, site) {c, n, fn, {a, b, d, e}, site}
static const struct move s_moves[] = {
    MV(7, 3, mbmv_8db41c, 0, 3, 0, 0, 0x8db41c),
    MV(7, 10, mbmv_8db41c, 1, 10, 24, 0, 0x8db41c),
    MV(7, 24, mbmv_8db41c, 4, 24, 24, 0, 0x8db41c),
    MV(7, 25, mbmv_8db41c, 5, 25, 24, 0, 0x8db41c),
    MV(7, 34, mbmv_8db41c, 8, 34, 24, 0, 0x8db41c),
    MV(1, 2, mbmv_8d9af8, 0, 1, 0, 0, 0x8d9af8),
    MV(1, 27, mbmv_1_27, 0, 0, 0, 0, 0x8de710),
    MV(1, 28, mbmv_8da42c, 0, 1, 0, 0, 0x8da42c),
    MV(1, 29, mbmv_8da42c, 1, 1, 0, 0, 0x8da42c),
    MV(1, 32, mbmv_8da42c, 2, 1, 0, 0, 0x8da42c),
    MV(1, 33, mbmv_8da42c, 3, 1, 0, 0, 0x8da42c),
    MV(7, 13, mbmv_8dc13c, 0, 13, 24, 0, 0x8dc13c),
    MV(7, 14, mbmv_8dc13c, 1, 14, 24, 0, 0x8dc13c),
    MV(7, 15, mbmv_8dc13c, 2, 15, 24, 0, 0x8dc13c),
    MV(7, 28, mbmv_8dc13c, 3, 28, 24, 0, 0x8dc13c),
    MV(7, 29, mbmv_8dc13c, 4, 29, 24, 0, 0x8dc13c),
    MV(7, 30, mbmv_8dc13c, 5, 30, 24, 0, 0x8dc13c),
    MV(7, 33, mbmv_8dc13c, 6, 33, 24, 0, 0x8dc13c),
    MV(1, 21, mbmv_8d9c9c, 1, 1, 0, 0, 0x8d9c9c),
    MV(1, 34, mbmv_8d9c9c, 3, 1, 0, 0, 0x8d9c9c),
    MV(2, 7, mbmv_8d83a0, 7, 2, 0, 0, 0x8d83a0),
    MV(1, 31, mbmv_8da77c, 1, 1, 0, 0, 0x8da77c),
    MV(2, 0, mbmv_8d7d8c, 0, 2, 0, 0, 0x8d7d8c),
    MV(2, 21, mbmv_8d7d8c, 1, 2, 0, 0, 0x8d7d8c),
    MV(2, 25, mbmv_8d7d8c, 2, 2, 0, 0, 0x8d7d8c),
    MV(2, 26, mbmv_8d7d8c, 3, 2, 0, 0, 0x8d7d8c),
    MV(2, 6, mbmv_8d81d0, 0, 2, 0, 0, 0x8d81d0),
    MV(2, 22, mbmv_8d81d0, 1, 2, 0, 0, 0x8d81d0),
    MV(2, 19, mbmv_8d93c4, 0, 2, 0, 0, 0x8d93c4),
    MV(2, 20, mbmv_8d93c4, 1, 2, 0, 0, 0x8d93c4),
    MV(2, 23, mbmv_8d93c4, 2, 2, 0, 0, 0x8d93c4),
    MV(2, 3, mbmv_2_turn, 1, 1, 0, 0, 0x8ddad4),          /* p = (record 0xe0e090?, flags, sleepFlagA) */
    MV(2, 5, mbmv_2_turn, 0, 0, 0, 0, 0x8ddb38),
    MV(2, 17, mbmv_2_turn, 0, 0, 0, 0, 0x8ddc90),
    MV(2, 24, mbmv_2_turn, 1, 1, 1, 0, 0x8ddd10),
    MV(2, 2, mbmv_8d7f08, 2, 2, 0, 0, 0x8d7f08),
    MV(2, 10, mbmv_8d8518, 10, 2, 0, 0, 0x8d8518),
    MV(1, 1, mbmv_1_1, 0, 0, 0, 0, 0x8de00c),
    MV(1, 4, mbmv_1_motion, 0x0f, 10, 0, 0, 0x8de0cc),     /* p = (motion, blend) */
    MV(1, 19, mbmv_1_motion, 0x0e, 6, 0x04, 0, 0x8de280),  /* his idle 0x40e */
    MV(1, 35, mbmv_1_motion, 0x0e, 6, 0x04, 0, 0x8de7fc),
    MV(7, 2, mbmv_8dabd8, 0, 2, 0, 0, 0x8dabd8),
    MV(7, 19, mbmv_8dabd8, 1, 19, 24, 0, 0x8dabd8),
    MV(7, 31, mbmv_8dbf80, 0, 31, 24, 0, 0x8dbf80),
    MV(7, 32, mbmv_8dbf80, 1, 32, 24, 0, 0x8dbf80),
    MV(7, 1, mbmv_7_1, 0, 0, 0, 0, 0x8db0d8),
    MV(7, 8, mbmv_7_8, 0, 0, 0, 0, 0x8db200),
    MV(7, 4, mbmv_8db998, 0, 4, 0, 0, 0x8db998),
    MV(7, 21, mbmv_8db998, 1, 21, 24, 0, 0x8db998),
    MV(1, 10, mbmv_1_motion, 0x10, 10, 0x03, 0, 0x8da0f4), /* motion 0x310 */
    MV(2, 12, mbmv_8d89d0, 0, 2, 0, 0, 0x8d89d0),
    MV(2, 14, mbmv_8d89d0, 1, 2, 0, 0, 0x8d89d0),
    MV(2, 18, mbmv_8d89d0, 2, 2, 0, 0, 0x8d89d0),
    MV(3, 1, mbmv_3_1, 0, 0, 0, 0, 0x8d96e4),
    MV(3, 2, mbmv_8d6a74, 2, 1, 0, 0, 0x8d6a74),
    MV(3, 3, mbmv_8d6c80, 3, 1, 0, 0, 0x8d6c80),
    MV(3, 4, mbmv_8d6e04, 4, 1, 0, 0, 0x8d6e04),
    MV(6, 1, mbmv_6_rest, 1, 0, 0, 0, 0x8dc8c4),          /* p[0] = case */
    MV(6, 7, mbmv_6_rest, 7, 0, 0, 0, 0x8dca74),
    MV(6, 3, mbmv_6_turn, 0, 0, 0, 0, 0x8dc96c),          /* p = (motion speed 10?, sleep flags) */
    MV(6, 13, mbmv_6_turn, 1, 0, 0, 0, 0x8dcb64),
    MV(6, 11, mbmv_6_turn, 1, 0, 0, 0, 0x8dd624),
    MV(6, 18, mbmv_6_turn, 1, 1, 0, 0, 0x8dd624),
    MV(6, 19, mbmv_6_turn, 1, 2, 0, 0, 0x8dd624),
    MV(6, 2, mbmv_8dc708, 2, 6, 0, 0, 0x8dc708),
    MV(6, 8, mbmv_8dd310, 0, 6, 0, 0, 0x8dd310),
    MV(6, 9, mbmv_8dd310, 1, 6, 0, 0, 0x8dd310),
    MV(6, 12, mbmv_8dd704, 12, 6, 0, 0, 0x8dd704),
    MV(6, 4, mbmv_8dcc80, 0, 6, 0, 0, 0x8dcc80),
    MV(6, 15, mbmv_8dcc80, 1, 6, 0, 0, 0x8dcc80),
    MV(6, 16, mbmv_8dcc80, 2, 6, 0, 0, 0x8dcc80),
    MV(6, 20, mbmv_8dcc80, 3, 6, 0, 0, 0x8dcc80),
    MV(7, 0, mbmv_8daa48, 0, 0, 0, 0, 0x8daa48),
    MV(7, 18, mbmv_8daa48, 1, 18, 24, 0, 0x8daa48),
    MV(7, 5, mbmv_8dbbbc, 0, 5, 0, 0, 0x8dbbbc),
    MV(7, 22, mbmv_8dbbbc, 1, 22, 24, 0, 0x8dbbbc),
    MV(7, 6, mbmv_8dbd0c, 0, 6, 0, 0, 0x8dbd0c),
    MV(7, 20, mbmv_8dbd0c, 1, 20, 24, 0, 0x8dbd0c),
    MV(7, 7, mbmv_8dbe34, 0, 7, 0, 0, 0x8dbe34),
    MV(7, 9, mbmv_8dae90, 0, 9, 24, 0, 0x8dae90),
    MV(1, 6, mbmv_1_motion, 0x16, 6, 0, 0, 0x8de110),
    MV(1, 20, mbmv_1_20, 0, 0, 0, 0, 0x8de2b0),
    MV(2, 16, mbmv_1_motion, 0x10, 4, 0x02, 0, 0x8ddc38),  /* motion 0x210 */
    MV(6, 0, mbmv_8dc5b4, 0, 6, 0, 0, 0x8dc5b4),
    MV(6, 17, mbmv_8dc5b4, 1, 6, 0, 0, 0x8dc5b4),
    MV(2, 13, mbmv_8d8cc0, 0, 2, 0, 0, 0x8d8cc0),
    MV(2, 15, mbmv_8d8cc0, 1, 2, 0, 0, 0x8d8cc0),
    MV(7, 26, mbmv_8db41c, 6, 26, 24, 0, 0x8db41c),        /* chained from 2/13 (sub 0x8db020 case 26) */
    MV(7, 27, mbmv_8db41c, 7, 27, 24, 0, 0x8db41c),        /* chained from 2/15 (case 27) */
};

/* GU slot 125's common tail 0xd35f9c (C), after the handler as in GU */
static void gu_tail(void *self)
{
    uint8_t *p = WORK(self);
    if (isAction(self, 7, 7) == 1) {
        if (p[9] == 0) p[9] = 1;
    } else if (FIELD(uint8_t, self, EN_ACT_CAT) != 0 && p[9] == 1) {
        p[9] = 0;
    }
    if (FIELD(uint8_t, self, EN_VARIANT) != 4) {
        float a, b;
        if (p[10] >= 3) p[10] = 2;
        if (p[10] == 2) { a = 600.0f; b = 300.0f; }         /* literals 0xd360bc / 0xd360c4 */
        else if (p[10] == 1) { a = 900.0f; b = 600.0f; }    /* 0xd360b8 / 0xd360bc */
        else { a = 1200.0f; b = 900.0f; }                   /* 0xd360c0 / 0xd360b8 */
        RF(p, 16) = slowState(self) ? a : b;                /* vseleq 0xd36034 */
    }
    if (p[8] == 1) {
        RF(p, 12) = 0.0f;
    } else {
        float t = RF(p, 12) + GU_DT;
        RF(p, 12) = t;
        if (t > RF(p, 16)) RF(p, 12) = RF(p, 16);
    }
}

/* Sonic bombs (C for the path, numbers from GU's frame code 0x97ddc at 0x998d4 and class slot 145 0xd3a5c8): a shell hit
 * this frame (rec+0x444) of type 33 or 37..47 (rec+0x484; 0x16c43c: only hurt volumes with bit 4, GU's bodydata, shared)
 * with data flag 16 (rec+0x3a8, dtbase +0x6c, shared), no status 32, while he is burrowed (target mode 4), not enraged
 * (rec+0x518 != 1) and no area move runs (this+0x73f0): pending reaction 11 = 0x9bfd0 -> (10, 92) for mode 4. Nothing
 * there looks at the action number, so GU's own path serves him as his Diablos, except while he lies burrowed: his 6/8
 * 6/9 (4U's 0x8dd310) set sleepFlagB every frame, rec+0x3a2 != 0 makes the frame code drop every pending reaction
 * (0x98dd4). 4U has the same rule, the user wants the reaction there too (test of 0.4.4: GU reacted out of 6/3, this code
 * out of 6/8). So this runs the same test after GU's: GU's reaction is then already running (category 10) or pending.
 * (10, 92) itself is GU's table and start code 0xd358f8 (work+0xa += 1: GU's tail shortens the burrow cooldown work+16
 * with it: 1200 / 900, 900 / 600, 600 / 300 frames, read by the AI through slot 133 case 1). */
#define sonicReact FN(selfInt_t, 0x9bfd0)
typedef int (*statusOn_t)(void *self, uint32_t bits);
#define statusOn   FN(statusOn_t, 0xa1fc8)          /* status bits test rec+0x5e08 */
static void sonic_check(void *self)
{
    static uint32_t s_lines;
    uint8_t *rec = REC(self);
    uint32_t t = rec[0x484] - 33u;
    if (!rec[0x444] || rec[0x1ba] != 4 || FIELD(uint8_t, self, EN_ACT_CAT) == 10) return;
    if (t > 14 || !((0x7ff1u >> t) & 1) || !(rec[0x3a8] & 16) || statusOn(self, 32)) return;
    if (FIELD(uint8_t, self, 0x73f0) || rec[0x518] == 1 || FIELD(uint8_t, self, 0x73e5)) return;
    if (s_lines < 16) {
        s_lines++;
        logf("mbport: em007_01 sonic hit type %u in action %u/%u while lying burrowed: reacting here",
             t + 33, FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
    }
    sonicReact(self);
}

int em007_01_moves_run(void *self)
{
    static uint8_t s_seen[8][256 / 8];
    uint32_t cat, num, n6;
    sonic_check(self);                                      /* first: setAction changes the action and clears the steps
                                                             * at once; his old handler must not run on them (0.4.4 did:
                                                             * step 1 without motion 0x315, he popped up later) */
    cat = FIELD(uint8_t, self, EN_ACT_CAT);
    num = FIELD(uint8_t, self, EN_ACT_NUM);
    n6 = cat == 6 && num >= PORT_BASE ? num - PORT_BASE : 255;
    mb_mound_frame(self, n6 >= 8 && n6 <= 10,               /* every action, GU's too */
                   n6 == 4 || n6 == 12 || n6 == 15 || n6 == 16 || n6 == 20);
    mb_angry_frame(self);                                   /* every action, GU's too */
    if (num < PORT_BASE || cat > 7) return 0;
    uint32_t n4 = num - PORT_BASE;
    const struct move *mv = 0;
    for (uint32_t i = 0; i < sizeof s_moves / sizeof s_moves[0]; i++)
        if (s_moves[i].cat == cat && s_moves[i].num == n4) { mv = &s_moves[i]; break; }
    if (!(s_seen[cat][n4 >> 3] & (1u << (n4 & 7)))) {       /* first run of each action: one log line */
        s_seen[cat][n4 >> 3] |= 1u << (n4 & 7);
        if (mv) logf("mbport: em007_01 4U action %u/%u runs as %u/%u (port of 4U %x)", cat, n4, cat, num, mv->site);
        else logf("mbport: em007_01 4U action %u/%u (%u/%u) has no port yet: ended", cat, n4, cat, num);
    }
    WORK(self)[8] = 0;                                       /* GU 0xd35e70 */
    if (mv) mv->run(self, mv->p);
    else end_action(self);
    gu_tail(self);
    return 1;
}
