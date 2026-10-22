/* Per-frame part logic of both halves: GU slot 130 = 4U slot 48 (head 0x773304, tail 0x8a1fec), the parts that do
 * not move collision (walk pieces: dala_walk.c, slot 168).
 *  - hitzones: rage / part-rank driven rows of the meat tables (partMeatBase / partMeatAlt, same calls and tables in
 *    both games, game.h), Shah by its effect-state bytes (head work +0x6c..+0x70, goal D8 sets them);
 *  - the flag halfword 4U W+0x42c = GU rec+0x3b4 (detached-part bits; bit 0 = tail severed, Gogmazios
 *    em089_break.h): 0x400 set while the body is not walkable (both halves), 0x80 / 0x40 by the head's motions
 *    810 / 811, 0x200 / 0x100 by the tail's idle motions. Bits other than 0 are not traced in GU (S: same field);
 *    -DDALA_NO_REC_FLAGS leaves them out;
 *  - the mesh-group visibility rows (4U 0x948378): broken-part pieces, rage glow, sever stump, Shah's state pieces,
 *    with the cond-7 state word 4U W+0x7a14 (0x7800 + 0x214 in 0x948378 / 0x772d18) kept in F_STATE7;
 *  - camera shakes at joint 154 in the tail's arena-break motions 623 / 624 (4U 0x910c6c(this, joint, id) = GU
 *    0xc24d8(this, joint, id, 0), Gogmazios em089_act.c). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_gather.h"
#include "dala_body.h"

#define rageOn    FN(int (*)(void *), 0x8172c)       /* [4U 0x954e48] rage byte (class-study.md) */
#define partRank  FN(uint32_t (*)(void *, uint32_t), 0x9d428)   /* [4U 0x94741c] */
typedef void (*camShakeJoint_t)(void *self, int32_t joint, uint32_t id, uint32_t zero);
#define camShakeJoint FN(camShakeJoint_t, 0xc24d8)
#define REC_FLAGS 0x3b4          /* u16 [4U W+0x42c] */
#define SEVERED(self) (FIELD(uint16_t, REC(self), REC_FLAGS) & 1)   /* [4U 0x91a884(this, 1)] */

uint32_t dala_walk_set(void *self);   /* dala_walk.c */
void dala_break_install(void *self);   /* dala_break.c: the break records into the shared dtbparts object */
void dala_look_install(void *self);    /* dala_look.c: the look joint list into it, look joints registered */
void dala_break_log(void *self, uint32_t tail);

/* ---- tail sever ----
 * 4U etd per-part table (word 5, 10-byte rows, converted into dttune +0x68): only part 7 has a second level
 * (levels 1, type byte 1, 2nd HP 1000) in both em024 and em083, i.e. the severable tail tip on the tail half
 * (rows: group 22 stump shown / 108 hidden by cond 1 bit 1). GU counts severs per part at rec+0x3bc + 12 * part + 1;
 * the cut object and the detached bit are monster code (Gogmazios em089_break.c, Kushala at 10/114): spawnCutPart
 * (0xc2330: cut slot 0 = manifest field 1, the shared em090_00_tail piece; sets rec+0x3b4 bit 1 and the reward flag
 * 7) from the 4U sever bone 157 (em083 emd word 35, first record), then setDetached(1) (0xa3c94) if still clear. */
#define SEVER_PART  7
#define SEVER_JOINT 157
typedef void (*spawnCutPart_t)(void *self, uint32_t k, uint32_t flags, uint32_t joint, const float *pos);
#define spawnCutPart FN(spawnCutPart_t, 0xc2330)
#define setDetached  FN(void (*)(void *, uint32_t), 0xa3c94)

static void tail_sever(void *self)
{
    uint8_t *rec = REC(self);
    if (!rec[0x3bc + 12 * SEVER_PART + 1] || SEVERED(self)) return;
    spawnCutPart(self, 0, 0, SEVER_JOINT, 0);
    if (!SEVERED(self)) setDetached(self, 1);
    logf("dalaport: tail severed: cut object %s, detached %x, reward flags %x",
         FIELD(uint8_t, self, 0x8b94) == 1 ? "spawned" : "missing", FIELD(uint16_t, rec, REC_FLAGS),
         (uint32_t)rec[0x5cbe]);
}

/* 4U 0x92213c(this, v) = GU 0xbd650 (rec+0x5d02 = 1, rec+0x5d00 = v; callee map S): 4U W+0x7a1a is the cond-0
 * condition of the visibility rows (group 23) */
#define cond0Set FN(void (*)(void *, uint32_t), 0xbd650)

/* the head's per-motion body attacks of 4U slot 48 (0x7734cc..0x773a0c): frame checks through 0x94a50c (GU
 * atFrameB), first match wins per motion. {frame, slot, attackdata, kind}: kind 0 = arm (param 2), 1 = reset */
typedef struct { uint16_t frame; uint8_t slot, atk, kind; } body_hit;
static const body_hit k_m21[] = {{10, 0, 8, 0}, {22, 0, 0, 1}, {32, 0, 8, 0}, {72, 0, 0, 1}, {590, 0, 8, 0},
                                 {600, 0, 0, 1}, {680, 0, 8, 0}, {690, 0, 0, 1}};
static const body_hit k_m41[] = {{8, 0, 9, 0}, {20, 0, 0, 1}, {40, 0, 9, 0}, {80, 0, 0, 1}, {136, 0, 9, 0},
                                 {146, 0, 0, 1}, {168, 0, 9, 0}, {212, 0, 0, 1}};
static void body_hits(void *self, const body_hit *h, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) {
        if (!atFrameB(self, (float)h[i].frame)) continue;
        if (h[i].kind) attackFlag(self, h[i].slot);
        else dala_attack(self, h[i].slot, h[i].atk, 2);
        return;
    }
}

static void head_motion(void *self, uint32_t m)
{
    if (m == 21) body_hits(self, k_m21, sizeof k_m21 / sizeof *k_m21);
    else if (m == 41) body_hits(self, k_m41, sizeof k_m41 / sizeof *k_m41);
    else if (m == 3) {
        if (atFrameB(self, 170.0f)) { dala_attack(self, 1, 10, 0); dala_attack(self, 0, 68, 0); }
    } else if (m >= 61 && m <= 66) {
        /* the long transfer motions: 0x910c6c(this, -1, 200) at frames 2 + 12k, k < 20 (id 200: outside the 0..9
         * shake ids seen in Gogmazios; kept as 4U) */
        for (uint32_t k = 0; k < 20; k++)
            if (atFrameB(self, 2.0f + 12.0f * (float)k)) camShakeJoint(self, -1, 200, 0);
    } else if (m == 769) {
        if (atFrameB(self, 2.0f)) { dala_attack(self, 0, 10, 0); dala_attack(self, 1, 41, 0); }
    } else if (m == 770) {
        if (atFrameB(self, 2.0f)) { dala_attack(self, 1, 10, 0); dala_attack(self, 0, 54, 0); }
    }
    /* not ported here: the hit bits work+0x54 (attack kinds of connecting slots in motions 61..66, heat-zone bits:
     * effects, goal D5). The gather point following joint 5 (0x773c24): dala_parts_frame -> dala_gather.c */
    if (m == 770 || m == 790 || m == 810) cond0Set(self, 2);
}

static void flag(void *self, uint16_t set, uint16_t clr)
{
#ifndef DALA_NO_REC_FLAGS
    uint16_t *f = &FIELD(uint16_t, REC(self), REC_FLAGS);
    *f = (uint16_t)((*f | set) & ~clr);
#else
    (void)self; (void)set; (void)clr;
#endif
}

/* ---- mesh-group visibility (4U 0x948378 per group, written into the masks by 0x942924) ----
 * Rows of each em's emd +0x88 (tools/emdata4u.py part_rows, dumped 2026-10-21): {group, cond, mode, param,
 * threshold}. A group with rows is drawn only if every row passes (mode 0: its condition is false, mode 1: true);
 * groups without rows keep their spawn state (field-3 XFS). Conditions used by Dalamadur, 4U -> GU:
 *   0 W+0x7a1a != 0 -> rec+0x5d02 (0x92213c = GU 0xbd650, S); 1 W+0x42c & p -> rec+0x3b4 & p; 6 part rank (p & 0xff)
 *   >= threshold (0x94741c = GU 0x9d428, C); 7 W+0x7a14 & p -> F_STATE7; 8 rage W+0x530 == 1 -> rec+0x518 == 1 (C). */
typedef struct { uint8_t group, cond, mode, param, thr; } vis_row;
static const vis_row k_vis024[] = {   /* em024, Dalamadur head */
    {23, 0, 1, 0, 0}, {24, 8, 1, 0, 0}, {101, 6, 0, 0, 1}, {2, 6, 1, 0, 1}, {102, 6, 0, 0, 1}, {3, 6, 1, 0, 1},
    {4, 6, 0, 0, 4}, {5, 6, 1, 0, 4}, {6, 6, 0, 1, 3}, {7, 6, 1, 1, 3}, {8, 6, 0, 2, 3}, {9, 6, 1, 2, 3},
    {103, 6, 0, 3, 1}, {10, 6, 1, 3, 1}, {11, 6, 0, 3, 2}, {12, 6, 1, 3, 2}, {104, 6, 0, 4, 1}, {13, 6, 1, 4, 1},
    {105, 6, 1, 4, 1}, {105, 6, 0, 4, 2}, {15, 6, 1, 4, 2},
};
static const vis_row k_vis110[] = {   /* em110, Shah head: em024's rows + the state pieces 30..45 */
    {23, 0, 1, 0, 0}, {24, 8, 1, 0, 0}, {101, 6, 0, 0, 1}, {2, 6, 1, 0, 1}, {102, 6, 0, 0, 1}, {3, 6, 1, 0, 1},
    {4, 6, 0, 0, 4}, {5, 6, 1, 0, 4}, {6, 6, 0, 1, 3}, {7, 6, 1, 1, 3}, {8, 6, 0, 2, 3}, {9, 6, 1, 2, 3},
    {103, 6, 0, 3, 1}, {10, 6, 1, 3, 1}, {11, 6, 0, 3, 2}, {12, 6, 1, 3, 2}, {104, 6, 0, 4, 1}, {13, 6, 1, 4, 1},
    {105, 6, 1, 4, 1}, {105, 6, 0, 4, 2}, {15, 6, 1, 4, 2}, {30, 7, 1, 1, 0}, {31, 7, 1, 1, 0}, {31, 6, 0, 0, 1},
    {32, 7, 1, 1, 0}, {32, 6, 0, 0, 1}, {40, 6, 1, 0, 1}, {40, 7, 1, 1, 0}, {41, 6, 1, 0, 1}, {41, 7, 1, 1, 0},
    {33, 7, 1, 2, 0}, {34, 7, 1, 2, 0}, {34, 6, 0, 1, 3}, {42, 6, 1, 1, 3}, {42, 7, 1, 2, 0}, {35, 7, 1, 4, 0},
    {36, 7, 1, 4, 0}, {36, 6, 0, 2, 3}, {43, 6, 1, 2, 3}, {43, 7, 1, 4, 0}, {37, 7, 1, 8, 0}, {37, 6, 0, 3, 1},
    {44, 6, 1, 3, 1}, {44, 7, 1, 8, 0}, {38, 7, 1, 16, 0}, {39, 7, 1, 16, 0}, {39, 6, 0, 4, 2}, {45, 6, 1, 4, 2},
    {45, 7, 1, 16, 0},
};
static const vis_row k_vis083[] = {   /* em083 = em111, the tail (both variants) */
    {25, 8, 1, 0, 0}, {108, 8, 1, 0, 0}, {108, 1, 0, 1, 0}, {16, 6, 0, 5, 1}, {17, 6, 1, 5, 1}, {18, 6, 0, 6, 1},
    {19, 6, 1, 6, 1}, {20, 6, 0, 7, 1}, {21, 6, 1, 7, 1}, {106, 7, 1, 1, 0}, {22, 1, 1, 1, 0},
};

static int vis_cond(void *self, const vis_row *r)
{
    const uint8_t *rec = REC(self);
    switch (r->cond) {
    case 0: return FIELD(uint8_t, rec, 0x5d02) != 0;
    case 1: return (FIELD(uint16_t, rec, REC_FLAGS) & r->param) != 0;
    case 6: return partRank(self, r->param) >= r->thr;
    case 7: return (FIELD(uint32_t, self, F_STATE7) & r->param) != 0;
    case 8: return FIELD(uint8_t, rec, 0x518) == 1;
    }
    return 0;                         /* 2 / 3 / 9 never; others unused by these rows */
}

static void vis_apply(void *self, const vis_row *rows, uint32_t n)
{
    uint32_t *bits = &FIELD(uint32_t, self, EN_GROUP_VIS);
    for (uint32_t i = 0; i < n; ) {
        uint32_t g = rows[i].group, show = 1;
        for (; i < n && rows[i].group == g; i++) {
            int c = vis_cond(self, &rows[i]);
            if (rows[i].mode == 0 ? c : !c) show = 0;
        }
        if (show) bits[g >> 5] |= 1u << (g & 31); else bits[g >> 5] &= ~(1u << (g & 31));
    }
}

/* 4U 0x772b44 (Dalamadur) / 0x772cf0 (Shah) */
static void head_hitzones(void *self)
{
    if (FIELD(uint8_t, self, EN_VARIANT) == 0) {
        if (rageOn(self)) {
            partMeatAlt(self, 0, 5); partMeatAlt(self, 1, 6); partMeatAlt(self, 2, 7);
            partMeatAlt(self, 3, 4); partMeatAlt(self, 4, 4); partMeatAlt(self, 5, 1);
            return;
        }
        if (partRank(self, 0)) partMeatAlt(self, 0, 0); else partMeatBase(self, 0);
        partMeatBase(self, 1);
        if (partRank(self, 3)) partMeatAlt(self, 2, 2); else partMeatBase(self, 2);
        if (partRank(self, 2) >= 3) partMeatAlt(self, 3, 3); else partMeatBase(self, 3);
        if (partRank(self, 1) >= 3) partMeatAlt(self, 4, 3); else partMeatBase(self, 4);
        partMeatBase(self, 5);
        return;
    }
    /* Shah: each part's effect state byte (work +0x6c..+0x70) picks its alternate row and sets its cond-7 bit
     * (W+0x7a14: 1, 0x10, 8, 4, 2) */
    const uint8_t *st = &DALA_WORK(uint8_t, self, 0x6c);
    static const uint8_t k_bit[5] = {1, 0x10, 8, 4, 2};
    for (uint32_t k = 0; k < 5; k++) {
        if (st[k] == 1) FIELD(uint32_t, self, F_STATE7) |= k_bit[k];
        else FIELD(uint32_t, self, F_STATE7) &= ~(uint32_t)k_bit[k];
    }
    if (st[0] == 1) partMeatAlt(self, 0, 1);
    else if (partRank(self, 0)) partMeatAlt(self, 0, 0); else partMeatBase(self, 0);
    if (st[1] == 1) partMeatAlt(self, 1, 4); else partMeatBase(self, 1);
    if (st[2] == 1) partMeatAlt(self, 2, 5);
    else if (partRank(self, 3)) partMeatAlt(self, 2, 2); else partMeatBase(self, 2);
    if (st[3] == 1) partMeatAlt(self, 3, 7);
    else if (partRank(self, 2) >= 3) partMeatAlt(self, 3, 3); else partMeatBase(self, 3);
    if (st[4] == 1) partMeatAlt(self, 4, 6);
    else if (partRank(self, 1) >= 3) partMeatAlt(self, 4, 3); else partMeatBase(self, 4);
}

/* 4U 0x8a1fec, hitzone part (Shah tail: no rage rows) */
static void tail_hitzones(void *self)
{
    if (FIELD(uint8_t, self, EN_VARIANT) == 0 && rageOn(self)) {
        partMeatAlt(self, 2, 3); partMeatAlt(self, 3, 4); partMeatAlt(self, 4, 5);
        return;
    }
    if (partRank(self, 7)) partMeatAlt(self, 2, 0); else partMeatBase(self, 2);
    if (SEVERED(self)) partMeatAlt(self, 3, 4);
    else if (partRank(self, 7)) partMeatAlt(self, 3, 1); else partMeatBase(self, 3);
    if (partRank(self, 5)) partMeatAlt(self, 4, 2); else partMeatBase(self, 4);
}

/* GU slot 130 (per frame from the enemy update 0xae830) = 4U slot 48 */
int dala_parts_frame(void *self)
{
    int tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff);
    uint32_t m = curMotion(self);
    dala_break_install(self);   /* once per loaded resource (cheap check per frame) */
    dala_look_install(self);    /* the same for the 4U look joint list (head only; after GU's look 0xa79f8) */
    dala_carve_install(self);   /* the same for the 4U carve points (dala_carve.c) */
    dala_break_log(self, tail);
    dala_body_frame(self);      /* read-only: shapes vs joints, part damage log (dala_body.c) */
    if (tail) tail_hitzones(self); else head_hitzones(self);
    if (dala_walk_set(self)) flag(self, 0, 0x400); else flag(self, 0x400, 0);
    if (!tail) {
        if (m == 810 || m == 811) flag(self, 0x80, 0x40); else flag(self, 0x40, 0x80);
        /* 4U head slot 64 0x77320c (on-break, part k; both variants, C): sets W+0x42c 0x4000 when part 0 ranks > 0,
         * 0x2000 part 1 >= 3, 0x1000 part 2 >= 3, 0x8000 part 3 > 0, 0x800 part 4 >= 2; nothing clears them. GU has
         * no on-break slot for it (slot 214 is a predicate, 0xa44e8), so they follow the ranks here every frame
         * (the same bits, as Gogmazios polls its breaks; readers: the generic flag test 0x91a884 = GU 0xa3cb0, S) */
        flag(self, (partRank(self, 0) ? 0x4000 : 0) | (partRank(self, 1) >= 3 ? 0x2000 : 0) |
                   (partRank(self, 2) >= 3 ? 0x1000 : 0) | (partRank(self, 3) ? 0x8000 : 0) |
                   (partRank(self, 4) >= 2 ? 0x800 : 0), 0);
        head_motion(self, m);
        dala_head_point_frame(self);   /* 4U 0x773c24: the on-body carve point at joint 5 * (0, 350, 400) */
        if (FIELD(uint8_t, self, EN_VARIANT)) vis_apply(self, k_vis110, sizeof k_vis110 / sizeof *k_vis110);
        else vis_apply(self, k_vis024, sizeof k_vis024 / sizeof *k_vis024);
        return 0;
    }
    tail_sever(self);
    /* tail cond-7 word: bit 0 while intact with part 7 broken (4U 0x8a2468..) */
    FIELD(uint32_t, self, F_STATE7) = (!SEVERED(self) && partRank(self, 7)) ? 1 : 0;
    vis_apply(self, k_vis083, sizeof k_vis083 / sizeof *k_vis083);
    /* tail: 4U 0x8a2248 sets 0x200 and clears 0x100 in motions 101..103, 613..617, 623, 624, 675, 869..872 (its
     * compare tree around 617 / 613), else the opposite. Not ported: W+0x1b79 cleared once severed outside motion
     * 872 (or past its frame 100): no GU field traced. */
    {
        static const uint16_t k_hold[] = {101, 102, 103, 613, 614, 615, 616, 617, 623, 624, 675, 869, 870, 871, 872};
        uint32_t hold = 0;
        for (uint32_t i = 0; i < sizeof k_hold / sizeof *k_hold; i++) if (m == k_hold[i]) hold = 1;
        if (hold) flag(self, 0x200, 0x100); else flag(self, 0x100, 0x200);
    }
    /* camera shakes in the arena-break motions: 623 (7.60) frames 442 / 540 / 690, 624 (7.61) 432 / 744 / 1132 */
    if (m == 623 && (motionCheckB(self, 0, 0, 442.0f, 0.0f) || motionCheckB(self, 0, 0, 540.0f, 0.0f) ||
                     motionCheckB(self, 0, 0, 690.0f, 0.0f))) camShakeJoint(self, 154, 6, 0);
    if (m == 624 && (motionCheckB(self, 0, 0, 432.0f, 0.0f) || motionCheckB(self, 0, 0, 744.0f, 0.0f) ||
                     motionCheckB(self, 0, 0, 1132.0f, 0.0f))) camShakeJoint(self, 154, 6, 0);
    return 0;
}
