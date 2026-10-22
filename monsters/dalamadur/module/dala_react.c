/* Dalamadur reactions: categories 10 and 11 of both halves (4U head 0x772838 / 0x773124, tail 0x8a1bf8 /
 * 0x8a1fcc). Every case picks a reaction-sequence table by the body placement W+0x1c9 (and for 10/7 placement 0
 * by the hit direction 0x938620) and tail-calls the base player 0x9197c0(this, table, 0); other numbers end the
 * action (vt+0x164). GU 0xa134c is the same player (Gogmazios' em089_react.c header, C), so the tables are
 * converted to its format: 8-byte ops, 24-byte motion descriptors with float blend / start (4U s32).
 * Tables: dump/scratch/dalamadur-session/rxgen.py (4U 0xfdc9dc.. head, 0xff5d78.. tail; names = 4U addresses).
 * Ops used besides motions: 3 = timer W+468 / rec+0x1bc = arg (4U 0x931b7c, GU 0x9f568, C), 0x3a = rec+0x5a4 =
 * rec+0x5a8 if > 0 (4U 0x931ba0 W+0x5e4 / 0x5e8, GU 0x9fbfc, C); 0xff end. Category 11 plays one table for every
 * number in 4U (motion 0x33d / 0x3a1). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

typedef struct { uint32_t op; const void *arg; } rx_op;
typedef struct {
    uint16_t motion, pad;      /* +0 motion id (bank << 8 | index) */
    float blend, start;        /* +4 / +8 (4U s32) */
    uint32_t flags;            /* +0xc setMotionEx flags */
    uint16_t kind;             /* +0x10 */
    uint8_t move, b13;         /* +0x12 movement type, +0x13 */
    const void *mv;            /* +0x14 movement data */
} rx_desc;
_Static_assert(sizeof(rx_op) == 8, "rx_op");
_Static_assert(sizeof(rx_desc) == 24, "rx_desc");

/* reaction-sequence player (this, table, flag) [4U 0x9197c0] (C, em089_react.c) */
typedef void (*reactPlay_t)(void *self, const rx_op *table, uint32_t flag);
#define reactPlay FN(reactPlay_t, 0xa134c)
/* hit direction: bits 3..5 of rec+0x5ccb [4U 0x938620: W+0x7993] (C, em089_react.c) */
typedef uint32_t (*hitDir_t)(void *self);
#define hitDir FN(hitDir_t, 0x9e994)

/* ---- tables (rxgen.py output) ---- */
static const rx_desc D_fdcac0 = {0x301, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcad8 = {0x315, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcaf0 = {0x329, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcb08 = {0x302, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdcb20 = {0x303, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcb38 = {0x316, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdcb50 = {0x317, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcb68 = {0x32a, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdcb80 = {0x32b, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcb98 = {0x302, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdcbb0 = {0x303, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcbc8 = {0x304, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdcbe0 = {0x33d, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff5e28 = {0x365, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5e40 = {0x379, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5e58 = {0x38d, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5e70 = {0x366, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_ff5e88 = {0x367, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5ea0 = {0x37a, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_ff5eb8 = {0x37b, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5ed0 = {0x38e, 0, 50.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_ff5ee8 = {0x38f, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5f00 = {0x368, 0, 50.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff5f18 = {0x3a1, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_op T_fdc9dc[] = {{0x0, &D_fdcac0}, {0xff, (const void *)0x0}};
static const rx_op T_fdc9ec[] = {{0x0, &D_fdcad8}, {0xff, (const void *)0x0}};
static const rx_op T_fdc9fc[] = {{0x0, &D_fdcaf0}, {0xff, (const void *)0x0}};
static const rx_op T_fdca0c[] = {{0x3, (const void *)0x4ec}, {0x0, &D_fdcb08}, {0x0, &D_fdcb20}, {0xff, (const void *)0x0}};
static const rx_op T_fdca2c[] = {{0x3, (const void *)0x4ec}, {0x0, &D_fdcb38}, {0x0, &D_fdcb50}, {0xff, (const void *)0x0}};
static const rx_op T_fdca4c[] = {{0x3, (const void *)0x528}, {0x0, &D_fdcb68}, {0x0, &D_fdcb80}, {0xff, (const void *)0x0}};
static const rx_op T_fdca6c[] = {{0x3, (const void *)0x4ec}, {0x0, &D_fdcb98}, {0x0, &D_fdcbb0}, {0x3a, (const void *)0xf0}, {0xff, (const void *)0x0}};
static const rx_op T_fdca94[] = {{0x0, &D_fdcbc8}, {0xff, (const void *)0x0}};
/* category 11 (death): 4U {motion, 0xff}; GU's death tables end with op 7 before 0xff (Kushala 11/0 0x17bb4e8
 * {motion 0x312, op 7, 0xff}; Gogmazios test 2026-10-20: without op 7 no 12/255). Without it the sequence end goes
 * to slot 247, which does nothing in category 11 (0x75270), and the table restarts: the death motion 0x33d and its
 * mouth fire replayed forever (test 2026-10-21 sixth install, S). Op 7 hands the dead half to 12/255. */
static const rx_op T_fdcaa4[] = {{0x0, &D_fdcbe0}, {0x7, (const void *)0x0}, {0xff, (const void *)0x0}};
static const rx_op T_ff5d78[] = {{0x0, &D_ff5e28}, {0xff, (const void *)0x0}};
static const rx_op T_ff5d88[] = {{0x0, &D_ff5e40}, {0xff, (const void *)0x0}};
static const rx_op T_ff5d98[] = {{0x0, &D_ff5e58}, {0xff, (const void *)0x0}};
static const rx_op T_ff5da8[] = {{0x3, (const void *)0x4ec}, {0x0, &D_ff5e70}, {0x0, &D_ff5e88}, {0xff, (const void *)0x0}};
static const rx_op T_ff5dc8[] = {{0x3, (const void *)0x4ec}, {0x0, &D_ff5ea0}, {0x0, &D_ff5eb8}, {0xff, (const void *)0x0}};
static const rx_op T_ff5de8[] = {{0x3, (const void *)0x528}, {0x0, &D_ff5ed0}, {0x0, &D_ff5ee8}, {0xff, (const void *)0x0}};
static const rx_op T_ff5e08[] = {{0x0, &D_ff5f00}, {0xff, (const void *)0x0}};
static const rx_op T_ff5e18[] = {{0x0, &D_ff5f18}, {0x7, (const void *)0x0}, {0xff, (const void *)0x0}};   /* as T_fdcaa4 */

/* one half's tables, indexed like the 4U cases: hit (10/7 placement 0, direction 1..7), down0/1/2 (placement k),
 * long0/1/2 (10/20 and 10/148 by placement), r114 (10/114 placement 0), r210 (10/210 placement 0), cat 11 */
typedef struct {
    const rx_op *hit, *down[3], *lng[3], *r114, *r210, *c11;
} rx_set;
static const rx_set k_head = {T_fdc9dc, {T_fdca0c, T_fdc9ec, T_fdc9fc}, {T_fdca0c, T_fdca2c, T_fdca4c}, T_fdca94,
                              T_fdca6c, T_fdcaa4};
static const rx_set k_tail = {T_ff5d78, {T_ff5da8, T_ff5d88, T_ff5d98}, {T_ff5da8, T_ff5dc8, T_ff5de8}, T_ff5e08,
                              T_ff5da8, T_ff5e18};

/* 4U 0x772838 / 0x8a1bf8 (same shape; only 10/210 placement 0 differs). Placement outside 0..2: the 4U case
 * returns without a table and without ending (kept). */
static void react(void *self, const rx_set *s, uint32_t cat)
{
    uint32_t num = FIELD(uint8_t, self, EN_ACT_NUM), m = MODE(self);
    const rx_op *t = 0;
    if (cat == 11) t = s->c11;
    else if (num == 7) {
        if (m == 0) { uint32_t d = hitDir(self); t = (d >= 1 && d <= 7) ? s->hit : s->down[0]; }
        else if (m <= 2) t = s->down[m];
        else return;
    } else if (num == 20 || num == 148) {
        if (m <= 2) t = s->lng[m];
        else if (num == 20) return;
        else t = s->lng[0];                     /* 10/148: placement 1 / 2 or the 0 table */
    } else if (num == 114 || num == 180 || num == 210) {
        if (m > 2) return;
        t = m ? s->down[m] : num == 114 ? s->r114 : num == 210 ? s->r210 : s->down[0];
    }
    if (!t) { dala_end(self); return; }
    if (cat == 11 && FIELD(uint8_t, REC(self), 0x1a1) == 0) {   /* first frame of the sequence (step byte) */
        static uint32_t s_n;
        if (++s_n <= 20)
            logf("dalaport: death %s 11/%u motion %x (op 7 then 12/255) HP %d frame %u", s == &k_head ? "head" : "tail",
                 num, ((const rx_desc *)t[0].arg)->motion, FIELD(int32_t, REC(self), REC_HP),
                 FIELD(uint32_t, self, F_FRAMES));
    }
    reactPlay(self, t, 0);
    /* The carcass (test 2026-10-21 seventh install: fire at the dead head's mouth, coming back after the death
     * animation). GU's death ends in the player's step machine rec+0x550 (dala_carve.c): 0 while the death sequence
     * plays, >= 1 once it ended = the carcass, still category 11 (12/255 only when it goes, where 0xa6bb8 sets the
     * motion speed to 0). The only effects the dead head still owns are its death motion's PSL slots (no code post,
     * log C), and 0x33d's PSL posts the purple em024_012 at joint 6 (the mouth) at frames 35..122 (S: the fire).
     * 4U holds the last frame and posts nothing more; here the held motion is stopped (layer speed 0 through
     * setMotionSpeed 0xb0870 = rec+0x398, as the corpse state does) so its effect sequence cannot run again (G: the
     * replay mechanism; dala_carcass_log shows the frame). The carcass timer uses this+28, not the motion speed (C:
     * 0x53aa84), so the corpse still goes. Every machine stops its own replayed death the same way (MP). */
    uint8_t *rec = REC(self);
    if (cat == 11 && rec[0x550] && FIELD(float, rec, 0x398) != 0.0f) {
        static uint32_t s_n;
        if (++s_n <= 8)
            logf("dalaport: carcass %s: death sequence over (step %u), motion %x held at frame %d: speed 0",
                 s == &k_head ? "head" : "tail", rec[0x550], curMotion(self), (int)motionFrame(self));
        setMotionSpeed(self, 0.0f);
    }
}

void dala_react_head(void *self, uint32_t cat) { react(self, &k_head, cat); }
void dala_react_tail(void *self, uint32_t cat) { react(self, &k_tail, cat); }

/* ---- the halves' damage side (4U damage function 0x920104, its Dalamadur exits; common-branches.md) ----
 * GU's damage update 0x97ddc runs on the machine that controls the half (0x97e10) and ends in the reaction
 * dispatcher 0x9a828 (tail call 0x98e54, reached on frames without damage too). Core hook dala_dmg_end at 0x98e44:
 * after the rage add (0x98e20) and before the dispatcher, r0 = this. Both halves have one controller, so the head's
 * rage and both halves' reactions are written on that machine; the rest reach the others through GU's state and
 * action sync (MP). */
#define REC_RAGE      0x510   /* s16 rage meter [4U W+0x528] (C) */
#define REC_REQUEST   0x362   /* u16 request bits, 4 = enrage (GU 0x7fc40; 4U W+0x3d8, cleared by 0x92b2d0) (C) */
#define REC_RX_KIND   0x3ae   /* u16 pending reaction kind read by the dispatcher 0x9a828 [4U W+0x426] (C) */
#define REC_RX_PART   0x3b2   /* u8 its part (dispatcher: rec+0x5ccb bits 3..5), +1 the second part [4U W+0x42a /
                                 0x42b] (C) */
/* rage add (this, n): scaled by the HP ratio table, held by rec+0x521, at the threshold request 4 [4U 0x933b30] (C) */
typedef void (*rageAdd_t)(void *self, int32_t n);
#define rageAdd FN(rageAdd_t, 0xbcc04)

/* Shared reactions (4U 0x948b9c, from the damage function's Dalamadur exit 0x921de0, C): a half whose pending kind
 * W+0x426 is 1 / 3 / 31 / 45 / 46 (part W+0x42a) or 14 (part W+0x42b) posts it to the manager (0x68aa80); next frame
 * both halves run that kind through the same switch as the normal dispatcher. GU's dispatcher has the same kinds
 * (1 = death in both, C; 3 / 14 / 31 / 45 / 46 one call each in both tables, S). Port: the kind and both parts are
 * kept here when a half's update ends with one; the partner's next update takes them when it has no kind of its own
 * (its no-damage path rewrites the kind, so only this point is safe). Death (1) stays with dala_death_sync. 4U
 * starts both reactions one frame after the post; here the posting half reacts at once, the partner up to one frame
 * later. */
static struct { void *from; uint32_t frame; uint16_t kind; uint8_t part[2]; } s_rx;

int dala_dmg_end_c(uint32_t *regs)
{
    void *self = (void *)regs[0], *p = dala_partner(self);
    if (!p) return 0;
    uint8_t *rec = REC(self);
    static uint32_t s_n;
    /* Rage (4U 0x921d1c, C): the tail's meter delta goes to the manager (0x68e08c), its meter is set to 0 and its
     * enrage request cleared (0x92b2d0(this, 4)); the head adds the manager's value through its own rage add. The
     * tail's meter is always 0 between updates, so its value now is this update's delta. */
    if ((FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff)) {
        int32_t n = FIELD(int16_t, rec, REC_RAGE);
        FIELD(uint16_t, rec, REC_REQUEST) &= (uint16_t)~4u;
        if (n > 0) {
            int32_t before = FIELD(int16_t, REC(p), REC_RAGE);
            FIELD(int16_t, rec, REC_RAGE) = 0;
            rageAdd(p, n);
            if (++s_n <= 60)
                logf("dalaport: rage tail %d -> head meter %d -> %d (rage %u) frame %u", n, before,
                     FIELD(int16_t, REC(p), REC_RAGE), REC(p)[0x518], FIELD(uint32_t, self, F_FRAMES));
        }
    }
    uint32_t k = FIELD(uint16_t, rec, REC_RX_KIND);
    if (k == 3 || k == 14 || k == 31 || k == 45 || k == 46) {
        s_rx.from = self;
        s_rx.frame = FIELD(uint32_t, self, F_FRAMES);
        s_rx.kind = (uint16_t)k;
        s_rx.part[0] = rec[REC_RX_PART];
        s_rx.part[1] = rec[REC_RX_PART + 1];
        if (++s_n <= 60)
            logf("dalaport: shared reaction %u part %u / %u posted by %x action %u/%u frame %u", k, s_rx.part[0],
                 s_rx.part[1], (uint32_t)self, FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM),
                 s_rx.frame);
    } else if (s_rx.kind && s_rx.from == p) {
        uint32_t age = FIELD(uint32_t, p, F_FRAMES) - s_rx.frame;
        if (!k && age <= 2) {
            FIELD(uint16_t, rec, REC_RX_KIND) = s_rx.kind;
            rec[REC_RX_PART] = s_rx.part[0];
            rec[REC_RX_PART + 1] = s_rx.part[1];
        }
        if (++s_n <= 60)
            logf("dalaport: shared reaction %u -> %x %s (own kind %u, age %u) action %u/%u", s_rx.kind, (uint32_t)self,
                 !k && age <= 2 ? "taken" : "dropped", k, age, FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM));
        s_rx.kind = 0;
    }
    return 0;
}

/* Break flinch: GU slot 143 (vt+0x23c, base 0x6bf6c = 0) = 4U slot 60 (base 0x944d90 = 0). Both games ask it in the
 * flinch reaction (kind 3) with the flinch part (4U 0x947e68: W+0x42a; GU 0x9b030: rec+0x3b2) and play the break
 * reaction on 1 (4U 0x94b9e0, GU 0x9e83c: the same switch on the state byte, S) (C). Head 0x77503c and tail
 * 0x8a2e80 answer alike (C): parts 0..4 by the head's break count (0x94741c = GU 0x9d428): part 0 at 1 or 4, parts
 * 1 / 2 at 3, parts 3 / 4 at 1 or 2; part 7 by the tail's, at 1; anything else 0. The partner is the other half
 * (4U 0x68fd44); a missing head leaves only part 7. */
#define partRank FN(uint32_t (*)(void *, uint32_t), 0x9d428)
int dala_break_flinch(void *self, uint32_t part)
{
    void *p = dala_partner(self);
    int tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff), hit = 0;
    void *head = tail ? p : self, *tl = tail ? self : p;
    uint32_t r = 0;
    if (part <= 4 && head) {
        r = partRank(head, part);
        hit = part == 0 ? (r == 1 || r == 4) : part <= 2 ? r == 3 : (r == 1 || r == 2);
    } else if (part == 7 && tl) hit = (r = partRank(tl, 7)) == 1;
    static uint32_t s_n;
    if (++s_n <= 40)
        logf("dalaport: %s flinch part %u rank %u -> break flinch %d", tail ? "tail" : "head", part, r, hit);
    return hit;
}

/* Second-part filter: GU slot 140 (vt+0x230, base 0x6bf54 = 1) = 4U slot 57 (base 0x93f37c = 1). The damage
 * functions' per-part loop asks it with the part before keeping that part as the second part of reaction 14 (4U
 * 0x9208b8 -> W+0x42b, GU 0x989f4 -> rec+0x3b3: same tests after it, C). Head 0x773de4 and tail 0x8a2640 (C): 0
 * while the half is in category 10 (reaction) or 11 (death), else 1. */
int dala_part_ok(void *self, uint32_t part)
{
    (void)part;
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat != 10 && cat != 11;
}

/* GU slot 175 (vt+0x2bc, base 0x6c034 = 1) = 4U slot 82 (base 0x934b54 = 1): the last test of 4U 0x954778 = GU
 * 0x8187c (record flag bit 0, the 0x40 flag, a stage-zone test, then this slot as a tail call; C), which both damage
 * functions ask at HP <= 0 (4U 0x920b5c: reaction kind 38 instead of 1; GU 0x98cf4: 38 when rec+0x5a0 was set) and
 * after the status build-up (4U 0x920964). Head 0x773174: placement 2 and the arena's highest broken piece 3
 * (0x7731a4 = dala_broken); tail 0x8a1fd0: placement 2 (C). */
int dala_death_kind_ok(void *self)
{
    int tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff);
    return MODE(self) == 2 && (tail || dala_broken(self) == 3);
}

/* One attack damages one half only (4U: 0xbe9f88 sets hit record +0x95 bit 3 when it hits em 24 / 83 / 110 / 111,
 * the attack-vs-enemy loop skips those ems for a record carrying it, 0xbf4d28; C). GU has the same rule for Nakarkos
 * (em 84 / 99): after the enemy's hit call (slot 38, 0x16c98c) 0x16c990 sets hit +0xb5 |= 0x20, and its slot 209
 * (vt+0x344, base 0x6c18c = 1; asked by the per-enemy candidate test 0x81a14 <- 0x16b450 before any collision test)
 * rejects a record carrying it (0x106f964) (C). Both halves do the same with the same bit (only Nakarkos reads it). */
#define HIT_GROUP 0x20
typedef void (*hitLanded_t)(void *self, uint8_t *hit, void *attacker, uint32_t kind);
#define hitLanded FN(hitLanded_t, 0xafbbc)   /* uFestaEnemy slot 38 (C: vtable 0x1734d44) */
void dala_hit_landed(void *self, uint8_t *hit, void *attacker, uint32_t kind)
{
    hitLanded(self, hit, attacker, kind);
    if (hit) hit[0xb5] |= HIT_GROUP;
}
int dala_hit_ok(void *self, const uint8_t *hit)
{
    if (!hit || !(hit[0xb5] & HIT_GROUP)) return 1;
    static uint32_t s_n;
    if (++s_n <= 20) logf("dalaport: hit record %x already hit the other half: %x skipped", (uint32_t)hit, (uint32_t)self);
    return 0;
}
