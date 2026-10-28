/* em057_01_moves.c: Stygian Zinogre (GU Zinogre variant 1, ID 0x139): the actions GU's uEm057_00 runs differently
 * from 4U, and 4U's action remap (notes/plan.md W1; verdicts and parameters: notes/phase2-actions.md).
 *
 * Dispatch: em057_01_act_c (em057_01_diag.c, hook on GU slot 125 0xf03620, the action dispatcher: a tail-branch switch
 * on the category with no common post-step, C) calls em057_01_moves_run first. For a variant-1 Zinogre whose current
 * action has an entry in s_moves it runs that entry and the hook returns 1, so GU's dispatch is skipped; every other
 * action goes on to GU's own handler (verdict KEEP: GU's same-number case runs the 4U logic).
 * - GU-PARAMS =: GU's handler called with 4U's parameters: 7/21 and 7/31 (GU effc00 = 4U 0x84a59c), 7/40 (GU efeb30 =
 *   4U 0x84bad8) and the orb family (GU efa930 = 4U 0x84c280; GU's same-number case f00c6c is a restructured copy).
 *   The orb family's variant-1 path posts no orb in GU; em057_01_posts.c posts Stygian's uShell046 orbs at its two
 *   post points (hooks in efa930, B5 step 7).
 * - Ported 4U handlers (verdicts PORT / PORT-chain / GU-PARAMS !=) are added to s_moves as they land.
 * - Action start: an entry hook on GU vt129 0xeefed0 (em057_01_start.c) does 4U vt47's start work that GU's vt129
 *   lacks for our rows: the cat-7 charge drain 0x858cec where GU's cost table has 0; the 1/39-43 stores have no GU
 *   field (logged).
 * Remap: entry hook on GU slot 127 0xeef31c (this, &category, &number; it rewrites the number in place), which GU's
 * setAction calls on the controlling machine. For variant 1 it runs 4U's slot 46 0x856a44 instead of GU's (GU keeps
 * only 7/207 <-> 208 of it, C): 2/63 <-> 64, 65 <-> 66, 67 <-> 68, 69 <-> 70, 7/4 <-> 5, 7/207 <-> 208 by the target side
 * (odd -> even when the side is not 0, even -> odd when it is 0), 7/186 -> 215 and 7/187 -> 216 in G rank (rank >= 5).
 * Multiplayer: the dispatcher runs every frame on every machine and so do these handlers, as GU's own; the remap runs
 * where GU's runs (the controlling machine) and the remapped action travels in GU's action message. */
#include "em057_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */

/* GU callees */
typedef void (*guHandler4_t)(void *self, uint32_t r1, uint32_t r2, uint32_t r3, uint32_t sp0);
typedef void (*guHandler2_t)(void *self, uint32_t r1, uint32_t r2);
#define guH_efa930   FN(guHandler4_t, 0xefa930)   /* GU 7/105-108 211-213 = 4U 0x84c280 (same parameters, C) */
#define guH_effc00   FN(guHandler2_t, 0xeffc00)   /* GU 7/20 86 205 209 = 4U 0x84a59c (r1 = start, r2 = follow-up) */
#define guH_efeb30   FN(guHandler2_t, 0xefeb30)   /* GU 7/204 7/230 = 4U 0x84bad8 */

static int is_sz(void *self)
{
    return self && FIELD(uint16_t, self, EN_ID) == STYGIAN_ZINOGRE_EM_ID;
}

/* ---- GU-PARAMS =: GU's handler with 4U's parameters (phase2-actions.md section 2) */
static void a_effc00(void *self, const uint8_t *p) { guH_effc00(self, p[0], p[1]); }
static void a_efeb30(void *self, const uint8_t *p) { guH_efeb30(self, p[0], p[1]); }
static void a_efa930(void *self, const uint8_t *p) { guH_efa930(self, p[0], p[1], p[2], p[3]); }

typedef void (*move_t)(void *self, const uint8_t *params);
struct move { uint8_t cat, num; move_t run; uint8_t p[4]; };

/* ported 4U handlers, batch A (em057_01_mv_a.c): p = the 4U dispatcher's (r1, r2, r3, [sp]) */
void szmv_845fe8(void *self, const uint8_t *p);    /* 2/47-52 2/61-70: turn, then 7/r2 */
void szmv_84383c(void *self, const uint8_t *p);    /* 2/72 73 75-77 79 80 (0x843d58 stubs): backstep, then r2/r3 */
void szmv_8499bc(void *self, const uint8_t *p);    /* 7/4 7/5: turn, then 7/20 / 7/21 */
void szmv_84a234(void *self, const uint8_t *p);    /* 7/14, then 7/15 */
void szmv_84a444(void *self, const uint8_t *p);    /* 7/15, then 7/16 */
/* ported 4U handlers, batch B (em057_01_mv_b.c) */
void szmv_848310(void *self, const uint8_t *p);    /* 7/2 3 6 7 16 68 69 188 189: then 7/160-175 / 186 / 187 or end */
void szmv_84f50c(void *self, const uint8_t *p);    /* 7/186 7/187, then 7/190 / 7/191 */
void szmv_84fbe4(void *self, const uint8_t *p);    /* 7/215 7/216, then 7/220 */
void szmv_84b548(void *self, const uint8_t *p);    /* 7/35 36 67 54 200: then 7/53 / 1/32 / 7/112 or end */
void szmv_84ab60(void *self, const uint8_t *p);    /* 7/51-53 7/202: then 7/126 or end */
/* ported 4U handlers, batch C (em057_01_mv_c.c) */
void szmv_853704(void *self, const uint8_t *p);    /* 7/160-175: end or 7/0 1 135 136 176 177 202; G rank 7/218 */
void szmv_854088(void *self, const uint8_t *p);    /* 7/176 7/177: end; G rank 7/215 / 7/216 */
/* ported 4U handlers, batch D (em057_01_mv_d.c) */
void szmv_84f744(void *self, const uint8_t *p);    /* 7/190 7/191: paw slam + ground shell; end */
void szmv_84ff7c(void *self, const uint8_t *p);    /* 7/217: slam + shell; end or 7/160-175 215 216 */
void szmv_850714(void *self, const uint8_t *p);    /* 7/218: slam + shell; end or 7/0 1 135 136 176 177 202 */
void szmv_852780(void *self, const uint8_t *p);    /* 7/220: slam + shell; end */
/* ported 4U handlers, batch E (em057_01_mv_e.c) */
void szmv_84a59c(void *self, const uint8_t *p);    /* 7/205 7/209: leap, then 7/206 / 7/210 */
void szmv_84bad8(void *self, const uint8_t *p);    /* 7/192-197 7/204: lunge, then p = (cat, num) */
void szmv_84d488(void *self, const uint8_t *p);    /* 7/203 7/206: hop back, then 7/5 / 7/207 */
void szmv_842b44(void *self, const uint8_t *p);    /* 13/3: rest walk, then 13/4 or 2/10 */
/* ported 4U handlers, batch F (em057_01_mv_f.c) */
void szmv_847274(void *self, const uint8_t *p);    /* 1/39 1/42 1/43: roar (motion 0x314); end */
void szmv_847a40(void *self, const uint8_t *p);    /* 1/40: lying wait (motion 0xf, timer 300), then 1/41 */
void szmv_847bdc(void *self, const uint8_t *p);    /* 1/41: stand-up (motion 0x305), then 1/42 */
void szmv_84dd44(void *self, const uint8_t *p);    /* 7/113 7/115: charge-up (uShell044 ring, burst); end */

static const struct move s_moves[] = {
    {7, 21, a_effc00, {2, 0}},              /* 4U 0x84a59c (1, 0) = GU 7/20's start */
    {7, 31, a_effc00, {1, 0}},              /* 4U 0x84a59c (0, 3) = GU 7/209's start */
    {7, 40, a_efeb30, {0, 0}},              /* 4U 0x84bad8 (255, 255) */
    {7, 32, a_efa930, {1, 0, 2, 0}},        /* the orb family: 4U 0x84c280 (r1, r2, r3, [sp]) */
    {7, 33, a_efa930, {0, 0, 3, 0}},
    {7, 34, a_efa930, {0, 0, 4, 0}},
    {7, 61, a_efa930, {1, 2, 2, 1}},
    {7, 62, a_efa930, {0, 2, 0, 1}},
    {7, 63, a_efa930, {1, 2, 0, 1}},
    {7, 66, a_efa930, {0, 0, 0, 0}},
    {7, 87, a_efa930, {1, 0, 0, 0}},
    {2, 47, szmv_845fe8, {0, 2, 0}},        /* 4U 0x845fe8 (side, follow-up 7/n, mode) */
    {2, 48, szmv_845fe8, {1, 3, 0}},
    {2, 49, szmv_845fe8, {0, 6, 0}},
    {2, 50, szmv_845fe8, {1, 7, 0}},
    {2, 51, szmv_845fe8, {0, 68, 0}},
    {2, 52, szmv_845fe8, {1, 69, 0}},
    {2, 61, szmv_845fe8, {0, 188, 0}},
    {2, 62, szmv_845fe8, {1, 189, 0}},
    {2, 63, szmv_845fe8, {0, 2, 1}},
    {2, 64, szmv_845fe8, {1, 3, 1}},
    {2, 65, szmv_845fe8, {0, 6, 1}},
    {2, 66, szmv_845fe8, {1, 7, 1}},
    {2, 67, szmv_845fe8, {0, 68, 1}},
    {2, 68, szmv_845fe8, {1, 69, 1}},
    {2, 69, szmv_845fe8, {0, 188, 1}},
    {2, 70, szmv_845fe8, {1, 189, 1}},
    {2, 72, szmv_84383c, {1, 7, 200, 0}},   /* 4U 0x843d58 stubs -> 0x84383c (1, 7, n, [sp] 0) */
    {2, 73, szmv_84383c, {1, 7, 201, 0}},
    {2, 75, szmv_84383c, {1, 7, 31, 0}},
    {2, 76, szmv_84383c, {1, 7, 32, 0}},
    {2, 77, szmv_84383c, {1, 7, 61, 0}},
    {2, 79, szmv_84383c, {1, 7, 52, 0}},
    {2, 80, szmv_84383c, {1, 7, 34, 0}},
    {7, 4, szmv_8499bc, {0, 7}},            /* 4U 0x8499bc (side; r2 unused) */
    {7, 5, szmv_8499bc, {1, 7}},
    {7, 14, szmv_84a234, {14, 7}},          /* 4U 0x84a234 (unused r1, r2) */
    {7, 15, szmv_84a444, {15, 7}},          /* 4U 0x84a444 (unused r1, r2) */
    {7, 2, szmv_848310, {0, 0, 0, 0}},      /* 4U 0x848310 (side, r2, r3, [sp]) */
    {7, 3, szmv_848310, {1, 0, 0, 0}},
    {7, 6, szmv_848310, {0, 1, 0, 0}},
    {7, 7, szmv_848310, {1, 1, 0, 0}},
    {7, 16, szmv_848310, {1, 1, 5, 1}},
    {7, 68, szmv_848310, {0, 2, 0, 0}},
    {7, 69, szmv_848310, {1, 2, 0, 0}},
    {7, 188, szmv_848310, {0, 1, 5, 0}},
    {7, 189, szmv_848310, {1, 1, 5, 0}},
    {7, 186, szmv_84f50c, {0, 7}},          /* 4U 0x84f50c (side; r2 unused) */
    {7, 187, szmv_84f50c, {1, 7}},
    {7, 215, szmv_84fbe4, {0, 7}},          /* 4U 0x84fbe4 (side; r2 unused) */
    {7, 216, szmv_84fbe4, {1, 7}},
    {7, 35, szmv_84b548, {0, 0, 0}},        /* 4U 0x84b548 (r1, r2, r3) */
    {7, 36, szmv_84b548, {1, 0, 0}},
    {7, 67, szmv_84b548, {0, 0, 1}},
    {7, 54, szmv_84b548, {0, 0, 2}},
    {7, 200, szmv_84b548, {0, 1, 0}},
    {7, 51, szmv_84ab60, {4, 7}},           /* 4U 0x84ab60 (r1; r2 unused); 7/22 112 201 stay on GU efbe1c */
    {7, 52, szmv_84ab60, {5, 7}},
    {7, 53, szmv_84ab60, {6, 7}},
    {7, 202, szmv_84ab60, {3, 7}},
    {7, 160, szmv_853704, {0, 1, 0}},       /* 4U 0x853704 (side, r2, r3); no [sp] */
    {7, 161, szmv_853704, {0, 1, 1}},
    {7, 162, szmv_853704, {0, 1, 2}},
    {7, 163, szmv_853704, {0, 1, 3}},
    {7, 164, szmv_853704, {1, 1, 0}},
    {7, 165, szmv_853704, {1, 1, 1}},
    {7, 166, szmv_853704, {1, 1, 2}},
    {7, 167, szmv_853704, {1, 1, 3}},
    {7, 168, szmv_853704, {0, 2, 0}},
    {7, 169, szmv_853704, {0, 2, 1}},
    {7, 170, szmv_853704, {0, 2, 2}},
    {7, 171, szmv_853704, {0, 2, 3}},
    {7, 172, szmv_853704, {1, 2, 0}},
    {7, 173, szmv_853704, {1, 2, 1}},
    {7, 174, szmv_853704, {1, 2, 2}},
    {7, 175, szmv_853704, {1, 2, 3}},
    {7, 176, szmv_854088, {0, 0}},          /* 4U 0x854088 (side, r2) */
    {7, 177, szmv_854088, {1, 0}},
    {7, 190, szmv_84f744, {0, 7}},          /* 4U 0x84f744 (side; r2 unused) */
    {7, 191, szmv_84f744, {1, 7}},
    {7, 217, szmv_84ff7c, {217, 7}},        /* 4U 0x84ff7c (unused r1, r2); reads work+0x115..0x117 */
    {7, 218, szmv_850714, {218, 7}},        /* 4U 0x850714 (unused r1, r2); reads work+0x115..0x117 */
    {7, 220, szmv_852780, {220, 7}},        /* 4U 0x852780 via 0x852778 (unused r1, r2); reads work+0x115 */
    {7, 205, szmv_84a59c, {0, 4}},          /* 4U 0x84a59c (r1, r2); 7/20 86 stay on GU effc00 */
    {7, 209, szmv_84a59c, {0, 5}},
    {7, 192, szmv_84bad8, {7, 198}},        /* 4U 0x84bad8 (follow-up cat, num) */
    {7, 193, szmv_84bad8, {2, 71}},
    {7, 194, szmv_84bad8, {2, 63}},
    {7, 195, szmv_84bad8, {2, 65}},
    {7, 196, szmv_84bad8, {2, 67}},
    {7, 197, szmv_84bad8, {2, 69}},
    {7, 204, szmv_84bad8, {7, 203}},
    {7, 203, szmv_84d488, {1, 1}},          /* 4U 0x84d488 (r1, r2); 7/85 198 210 stay on GU efc6cc */
    {7, 206, szmv_84d488, {2, 2}},
    {13, 3, szmv_842b44, {3}},              /* 4U 0x842b44 (r1 unused) */
    {1, 39, szmv_847274, {3, 1}},           /* 4U 0x847274 (r1; r2 unused); 1/9 34 37 38 stay on GU ef45e0 */
    {1, 42, szmv_847274, {4, 1}},
    {1, 43, szmv_847274, {5, 1}},
    {1, 40, szmv_847a40, {1, 1}},           /* 4U 0x847a40 (r1; r2 unused); 1/35 stays on GU ef4c74 */
    {1, 41, szmv_847bdc, {1, 1}},           /* 4U 0x847bdc (r1; r2 unused); 1/36 stays on GU ef4fd4(76) */
    {7, 113, szmv_84dd44, {1, 7}},          /* 4U 0x84dd44 (ring row; r2 unused) */
    {7, 115, szmv_84dd44, {3, 7}},
};

int em057_01_moves_run(void *self)
{
    if (!is_sz(self)) return 0;
    uint8_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    for (uint32_t i = 0; i < sizeof s_moves / sizeof s_moves[0]; i++)
        if (s_moves[i].cat == cat && s_moves[i].num == num) {
            s_moves[i].run(self, s_moves[i].p);
            return 1;
        }
    return 0;
}

/* ---- 4U's remap (slot 46 0x856a44) on GU slot 127 0xeef31c(this, u8 *cat, u8 *num) */
int em057_01_remap_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    uint8_t *cat = (uint8_t *)regs[R1], *num = (uint8_t *)regs[R2];
    if (!is_sz(self) || !cat || !num) return 0;
    uint8_t n = *num;
    if (*cat == 2 && n >= 63 && n <= 70) {
        uint32_t side = targetSide(self, 0);
        if ((n & 1) && side) *num = n + 1;              /* 63 / 65 / 67 / 69 -> 64 / 66 / 68 / 70 */
        else if (!(n & 1) && !side) *num = n - 1;       /* 64 / 66 / 68 / 70 -> 63 / 65 / 67 / 69 */
    } else if (*cat == 7) {
        if (n == 4 || n == 207) {
            if (targetSide(self, 0)) *num = n + 1;
        } else if (n == 5 || n == 208) {
            if (!targetSide(self, 0)) *num = n - 1;
        } else if (n == 186 || n == 187) {
            void *q = QUEST_GLOBAL;
            if (q && questRank(q) >= 5) *num = n == 186 ? 215 : 216;
        }
    }
    return 1;                                           /* GU's own remap is skipped for variant 1 */
}
