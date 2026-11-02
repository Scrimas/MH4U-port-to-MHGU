/* em005_01_fx.c: Black Gravios' motion-effect conditions and his eating cost (notes/plan.md "His own AI and effects",
 * test 2026-11-01: head / body / mouth effects doubled). C = confirmed in code, S = strong, G = guess. 4U = MH4U v1.1,
 * GU = MHGU 1.4.
 *
 * Effect conditions (C): every record of his MEF em041_1 has a condition bit in byte 0 (b0 1, 2, 6, 7, 9, 10): 4U's
 * motion-effect component (this+0xc78; 0x391a18 / 0x391b04) posts a record only when bit b0 of its mask (component
 * +0x30 = this+0xca8) is set, and the handlers set that mask every frame for the variant they run (r1 = the
 * dispatcher's first parameter): 0x8050e0 beam 7/73 7/89 -> 1, 7/74 -> 2; 0x805eec 7/79 -> 1, 7/80 -> 2 (GU keeps it
 * as this+0xb5f8 = 1 / 2 in d2ef2c, C); 0x803e6c 7/57 7/71 -> 1, 7/58 -> 2; 0x803c90 7/52 -> 1, 7/56 -> 2; 0x802768
 * 7/14 7/50 -> 1, 7/13 -> 2; 0x802498 7/17 -> 1, 7/12 -> 2; 0x7ff32c 13/1 -> 1; 0x801d94 (table 0x802084) 7/10 -> 6,
 * 7/7 -> 7, 7/60 -> 9, 7/59 -> 10; 0x803230 7/27 7/40 7/41 7/75 7/76 7/82..85 -> 6 (the bits his records do not use are
 * left out; the action -> 4U handler + parameter pairs are the dispatcher emulation of 0x807e5c, and GU dispatches every
 * one of them to the paired GU handler with the same parameter, C). Since 0.4.2 his motions play all of 4U's records
 * (em040_0's too, build_em005_01_arc.py effects()); five of em040_0's are conditioned: 31 32 -> bit 16 (0x802e8c 7/26
 * 7/29), 33 -> bit 17 (0x80774c case 3 = 6/3, S), 500 / 501 -> bits 30 / 31 (the component's own ground bits, by 4U
 * stage and area: ground_bits). The mask is cleared after each frame's posts
 * (0x393524), so a record plays only during its variant's action. GU's PSLs have no per-slot condition (one non-zero
 * of 14000 slots in GU), so his records (PEL u list 1, PSL slot kind 4, build_em005_01_arc.py effects()) are gated
 * here: a mid hook in uFestaEnemy slot 75 0x70028 (the PSL post, every monster's) at 0x70050 (r5 = this, r2 = the PSL
 * entry data, r3 = the slot) skips the post (exit 0x7016c: return 0, GU's own no-post path) when his record's bit is
 * not in the 4U mask of the current action. GU's own records (other ids) are never touched.
 *
 * Eating cost (C): 1/18 (4U 0x800d60, GU d27c8c, motions 18 / 19 / 20) heals and takes a cost from a gauge: 4U
 * 0x93bac0(this, 1, cost) with cost 20 for em 39 / 41 and 30 for em 38 / 40 / 115 (0x800e60); GU 0x9cf7c(this, 1)
 * takes the cost from its record [this+0x75f0]+196, 30.0 for Black Gravios too (test log 2026-11-01: the same
 * record as Gravios', file not identified). A hook before the call (d27d58) sets 20.0 there for Black Gravios and
 * one after it (d27d64, also reached when GU skips the call) puts GU's value back: the record is shared with
 * Gravios, and nothing else runs between the two (one thread). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_COSTREC  0x75f0      /* record pointer: 1/18 cost float at +196 */
#define COST_OFF    196
#define COST_4U     20.0f       /* 4U 0x800e74: em 39 / 41 (GU's 30.0 = 4U em 40's 0x800e90) */
#define PSL_KIND    0x44        /* PSL entry data: u32 kind[32] at +0x44, u16 id[32] at +4 */
#define KIND_PEL_U  4
#define EN_AREA_FX  0x1054      /* u8 current area */

/* the conditioned records of MEF em040_0 (Gravios') and em041_1 (his): record id -> condition bit b0, in MEF order
 * (build_em005_01_arc.py asserts this table against the MEFs) */
static const struct { uint16_t id; uint8_t b0; } s_b0[] = {
    {31, 16}, {32, 16}, {33, 17}, {500, 30}, {501, 31},
    {2004, 6}, {2005, 6}, {2006, 7}, {2007, 7}, {2013, 9}, {2014, 9}, {2015, 10}, {2016, 10}, {2030, 1}, {2031, 1},
    {2032, 1}, {2033, 2}, {2034, 2}, {2035, 2}, {2041, 1}, {2042, 2}, {2043, 1}, {2044, 2}, {2045, 1}, {2046, 2},
    {2050, 1}, {2051, 1}, {2052, 1}, {2053, 2}, {2054, 2}, {2055, 2}, {2061, 1}, {2062, 2},
};

/* 4U mask bit of the current action (category 7 unless noted), 0 = none of his bits */
static const struct { uint8_t cat, num, bit; } s_mask[] = {
    {7, 73, 1}, {7, 89, 1}, {7, 74, 2}, {7, 79, 1}, {7, 80, 2}, {7, 57, 1}, {7, 71, 1}, {7, 58, 2}, {7, 52, 1},
    {7, 56, 2}, {7, 14, 1}, {7, 50, 1}, {7, 13, 2}, {7, 17, 1}, {7, 12, 2}, {13, 1, 1}, {7, 10, 6}, {7, 7, 7},
    {7, 60, 9}, {7, 59, 10}, {7, 27, 6}, {7, 40, 6}, {7, 41, 6}, {7, 75, 6}, {7, 76, 6}, {7, 82, 6}, {7, 83, 6},
    {7, 84, 6}, {7, 85, 6}, {7, 26, 16}, {7, 29, 16}, {6, 3, 17},
};

#define STAGE_MGR   0x188ca48   /* [main+]: its byte +0x48 = the quest's stage (module/stage_alias.c) */

/* 4U's own ground bits (component update 0x3934b8, every frame for a monster): W+0x14b = the 4U stage, W+0x14c the
 * area: stages 1 5 12 13 -> bit 30, 2 15 -> bit 31, 3 (Primal Forest): areas 2 6 -> 30, 7 -> 31. GU stages of his
 * quests: 12 = 4U 15 (Volcanic Hollow), 13 = 4U 3 (Primal Forest, the same area numbers, S); others none (G). */
static uint32_t ground_bits(const void *self)
{
    const uint8_t *mgr = *(const uint8_t **)MAIN(STAGE_MGR);
    uint32_t area = FIELD(uint8_t, self, EN_AREA_FX);
    if (!mgr) return 0;
    switch (mgr[0x48]) {
    case 12: return 1u << 31;
    case 13: return area == 2 || area == 6 ? 1u << 30 : area == 7 ? 1u << 31 : 0;
    default: return 0;
    }
}

static int is_black_gravios(const void *self)
{
    return self && FIELD(uint16_t, self, EN_ID) == BLACK_GRAVIOS_EM_ID;
}

uint32_t em005_01_mask4u(const void *self)
{
    uint8_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t m = ground_bits(self);
    for (uint32_t i = 0; i < sizeof s_mask / sizeof s_mask[0]; i++)
        if (s_mask[i].cat == cat && s_mask[i].num == num) return m | 1u << s_mask[i].bit;
    return m;
}

/* GU 0x70050 (mid hook in 0x70028; r5 = this, r2 = PSL entry data, r3 = slot): 1 = skip the post (exit 0x7016c) */
int em005_01_pslgate_c(uint32_t *regs)
{
    static uint32_t s_lines;
    void *self = (void *)regs[R5];
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3], id, mask;
    if (!is_black_gravios(self) || !data || slot >= 32) return 0;
    if (FIELD(uint32_t, data, PSL_KIND + 4 * slot) != KIND_PEL_U) return 0;
    id = FIELD(uint16_t, data, 4 + 2 * slot);
    for (uint32_t i = 0; i < sizeof s_b0 / sizeof s_b0[0]; i++) {
        if (s_b0[i].id != id) continue;
        mask = em005_01_mask4u(self);
        if (++s_lines <= 60)
            logf("bgport: effect %u (4U bit %u) in action %u/%u: %s", id, s_b0[i].b0, FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM), mask >> s_b0[i].b0 & 1 ? "posted" : "skipped (4U condition)");
        return !(mask >> s_b0[i].b0 & 1);
    }
    return 0;
}

static float *s_cost;           /* the record's cost while our value is in, else 0 */
static float s_cost_gu;

/* GU 0xd27d58 (d27c8c, before `bl 0x9cf7c(this, 1)`; r4 = this) */
int em005_01_eat_pre_c(uint32_t *regs)
{
    static uint32_t s_lines;
    void *self = (void *)regs[R4];
    uint8_t *rec;
    if (!is_black_gravios(self) || !(rec = FIELD(uint8_t *, self, EN_COSTREC))) return 0;
    s_cost = &FIELD(float, rec, COST_OFF);
    s_cost_gu = *s_cost;
    *s_cost = COST_4U;
    if (++s_lines <= 8)
        logf("bgport: eat 1/18 cost %d -> %d (4U 0x800e60)", (int)s_cost_gu, (int)COST_4U);
    return 0;
}

/* GU 0xd27d64 (after the call, also where GU skips it): GU's value back */
int em005_01_eat_post_c(uint32_t *regs)
{
    (void)regs;
    if (s_cost) {
        *s_cost = s_cost_gu;
        s_cost = 0;
    }
    return 0;
}
