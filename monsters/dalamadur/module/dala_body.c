/* Dalamadur's hurt and push volumes in GU (user report 2026-10-22: hitboxes off the model, head passable, hits on
 * the toppled head not landing, carcass off). Static study, GU 1.4 / 4U 1.1:
 *
 * Which file (C): manifest field 30 (bodydata = 4U emd word 8) is loaded through callback enemy+0x76c0 = 0x709e0
 * into enemy+0x75cc (getter 0x710b0); field 31 (cambodydata = word 9) through enemy+0x76c8 = 0x709f0 into
 * +0x75d0 (getter 0x710d0). The cmdtbl slot +0x76f0 = 0x70a5c checks the mapping. So field 30 feeds BOTH the
 * hurt passes and sHitPush's player / enemy passes (0x17cf40, 0x17ea80); field 31 is only the quest camera's
 * (0x17f750, falls back to field 30 when empty). gu-walkable.md 6b / dala_walk.c had 31 for the push.
 *
 * Shape cache (C): sHit ([MAIN 0x1857830]) per frame 0x16ab4c: 0x16abac clears 256 slots (+0x1c type) and the
 * count +0x201c, adds every active attack object's volumes first (0x169c3c), one per hunter, then per enemy
 * (10 slots; +0xb5f9, 0x70824, 0x7e11c) rec+0x500 = count and every bodydata record in order WITHOUT filters
 * (0x16b9c0 -> 0x16de70); a record takes a slot only if the build returns a type (1 sphere, 2 capsule) and
 * count < 255. The hurt pass 0x16b15c -> 0x16c0c0 reads slot rec+0x500 + record index. 4U: the same scheme
 * (W+0x518, 0xbf4728 / 0xbee3a0).
 * Build (C, 0x16de70): joint by id (vt+0xd0 = 0x53aad8: ids this+0x498, joints this+0x494, 0xa0 each, matrix
 * joint+0x10); p = off x M + T (row vectors); shape 1: both offsets on bone A, shape 2: off2 on bone B, 0: sphere
 * at off1; radius x rec+0x1ac x rec+0x1b0 (0xbe5d4), or x |joint row| when +10 bit 0x1000.
 *
 * Per-record filters, identical in both games (C):
 *   hurt (GU 0x16c308.., 4U 0xbee3ec..): skip if 4U 0x91a884 / GU slot 220 (W+0x42c / rec+0x3b4 & +12) != 0; by
 *   attack kind (hit+0x3a): 8 / 69 need +10 & 3, 9 needs & 0x18, 37..47 need & 4, others skip +10 & 0x152 and
 *   with +10 & 0x8000 need 0xc03b8 (4U 0x92d774) and hit+0x30 & 4. +6 = hitzone row, +8 = part (damage code).
 *   push (GU 0x17d070, 4U 0xbbea80): skip +10 & 0x80d2, then the +12 test. camera: & 0x80b2, +12 test.
 *   Enemy gates (GU): hurt 0x16b420.. (0x70824, rec+0x1a0, 0x81a14 -> slot 209, rec+0x444, attack id list
 *   rec+0x448, same area +0x1054, 0x7e11c), push 0x17ca74.. (0x7e174, vt+0x88, rec+0x528 = 4U W+0x55a, area).
 *   0x7e11c / 0x7e174 drop dead enemies only when small (+0xb5f7): the carcass keeps hurt and push volumes.
 * +12 (C): GU base slot 220 0xa3cb0 = (rec+0x3b4 & bits) != 0 = 4U 0x91a884 (not virtual in 4U: em024 / em083
 *   cannot override it). Their bits are written by the classes (C, 4U writers): head 0x77320c (slot 64, on-break):
 *   0x8000 part 3 rank > 0 (records 27..29), 0x4000 part 0 (no record), 0x2000 part 1 >= 3 (38..41), 0x1000
 *   part 2 >= 3 (49..52), 0x800 part 4 >= 2 (19, 20); head 0x773304 (slot 48): 0x400 while not walkable
 *   (57..60, push only), 0x80 in motions 810 / 811 else 0x40 (legs 42..44 vs 45..47); tail 0x8a2248: 0x400
 *   (record 23), 0x200 / 0x100; bit 1 = tail severed (tail record 22); bit 2 (head record 5) has no writer.
 *   dala_parts.c already writes all of them into rec+0x3b4, so slot 220 needs no override.
 * +10 (C): 0x80 = hurt only (the larger twin), 0x100 = push only (the slimmer twin), 0 = both; same masks in 4U.
 *
 * This file is the runtime check the static study cannot replace: whether the cached shapes sit on the joints
 * (alignment / overflow / stale matrices) and which parts take the damage when the head is struck. Read only,
 * local log, no game state written (MP-neutral). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_body.h"

typedef const uint8_t *(*bodyRecs_t)(void *self);
#define bodyRecs    FN(bodyRecs_t, 0x710b0)   /* field 30 records (enemy+0x75cc), 44 B each, bone 0xffff ends */
#define HIT_MGR     0x1857830                 /* void *: sHit, the shape cache */
#define HM_COUNT    0x201c                    /* u32 slots used this frame (<= 255) */
#define REC_SHAPE0  0x500                     /* s32 first cache slot of this enemy */
#define REC_PARTOFF 0x3b4                     /* u16 +12 test bits [4U W+0x42c] */
#define REC_NOPUSH  0x528                     /* u8 player push off [4U W+0x55a] */
#define REC_PARTDMG 0x488                     /* u16[8] part damage counters (hit code 0x9d6f8) */
#define J_IDS       0x498
#define J_ARRAY     0x494
#define J_SIZE      160u
#define J_WORLD     0x10
#define TOL         300.0f                    /* one frame of motion between the cache and now */

static const float *jmat(void *self, uint32_t id)
{
    uint8_t *ids = FIELD(uint8_t *, self, J_IDS), *js = FIELD(uint8_t *, self, J_ARRAY);
    if (id > 255 || !ids || !js || ids[id] == 0xff) return 0;
    return (const float *)(js + J_SIZE * ids[id] + J_WORLD);
}

static void xform(const float *m, const float *o, float *p)
{
    for (int c = 0; c < 3; c++) p[c] = o[0] * m[c] + o[1] * m[4 + c] + o[2] * m[8 + c] + m[12 + c];
}

static float dist(const float *a, const float *b)
{
    float dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2], d2 = dx * dx + dy * dy + dz * dz, r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d2));
    return r;
}

static void *local_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* the cache against the joints: misses = records whose slot has no shape or sits > TOL from the rebuilt one */
static void cache_check(void *self, uint32_t tail)
{
    static uint32_t s_tick[2], s_n[2], s_last[2] = {0xffffffffu, 0xffffffffu};
    uint8_t *mgr = *(uint8_t **)MAIN(HIT_MGR), *rec = REC(self);
    const uint8_t *r = bodyRecs(self);
    if (!mgr || !r) return;
    int32_t base = FIELD(int32_t, rec, REC_SHAPE0);
    uint32_t count = FIELD(uint32_t, mgr, HM_COUNT), n = 0, miss = 0, worst = 0, wtype = 0;
    float size = FIELD(float, rec, 0x1ac) * FIELD(float, rec, 0x1b0), wdev = 0.0f, wc[3] = {0}, ww[3] = {0};
    for (; FIELD(uint16_t, r, 0) != 0xffff && n < 128; r += 44, n++) {
        uint32_t a = FIELD(uint16_t, r, 0), b = FIELD(uint16_t, r, 2), shape = FIELD(uint16_t, r, 4);
        const float *ma = jmat(self, a), *mb = shape == 2 ? jmat(self, b) : ma;
        int32_t slot = base + (int32_t)n;
        if (!ma || !mb || slot < 0 || slot > 255) { miss++; continue; }
        const uint8_t *c = mgr + 32u * (uint32_t)slot;
        float e0[3], e1[3], dev;
        xform(ma, &FIELD(float, r, 20), e0);
        xform(mb, &FIELD(float, r, 32), e1);
        uint32_t type = c[0x1c];
        if (!type) dev = 1.0e9f;
        else {
            dev = dist(&FIELD(float, c, 0x24), e0);
            if (shape) { float d1 = dist(&FIELD(float, c, 0x30), e1); if (d1 > dev) dev = d1; }
            float dr = FIELD(float, c, 0x20) - FIELD(float, r, 16) * size;
            if (dr < 0.0f) dr = -dr;
            if (dr > dev) dev = dr;
        }
        if (dev > TOL) miss++;
        if (dev > wdev) {
            wdev = dev; worst = n; wtype = type;
            for (int k = 0; k < 3; k++) { wc[k] = FIELD(float, c, 0x24 + 4 * k); ww[k] = e0[k]; }
        }
    }
    int periodic = ++s_tick[tail] % 120 == 0;
    if ((!periodic && miss == s_last[tail]) || s_n[tail] >= 60) return;
    s_n[tail]++;
    s_last[tail] = miss;
    const float *j5 = jmat(self, tail ? 140 : 5);
    logf("dalaport: body %s mot %x f %d act %u/%u mode %u base %d count %u flags %x nopush %u size %d: %u/%u off,"
         " worst rec %u type %u cache %d %d %d want %d %d %d dev %d, j%u %d %d %d",
         tail ? "tail" : "head", curMotion(self), (int)motionFrame(self), FIELD(uint8_t, self, EN_ACT_CAT),
         FIELD(uint8_t, self, EN_ACT_CAT + 1), MODE(self), base, count, FIELD(uint16_t, rec, REC_PARTOFF),
         FIELD(uint8_t, rec, REC_NOPUSH), (int)(size * 1000.0f), miss, n, worst, wtype, (int)wc[0], (int)wc[1],
         (int)wc[2], (int)ww[0], (int)ww[1], (int)ww[2], wdev > 99999.0f ? 99999 : (int)wdev, tail ? 140u : 5u,
         j5 ? (int)j5[12] : 0, j5 ? (int)j5[13] : 0, j5 ? (int)j5[14] : 0);
}

/* the local hunter inside a push volume (user, test 2026-10-22 23:44: "could still walk through the head", push on in
 * 50 of 60 checks): records with no +10 bit of 0x80d2 and no +12 bit set in rec+0x3b4, hunter point = feet + 90 */
static void push_check(void *self, uint32_t tail)
{
    static uint32_t s_n, s_t[2];
    void *pl = local_hunter();
    const uint8_t *r = bodyRecs(self), *rec = REC(self);
    if (!pl || !r || ++s_t[tail] % 10) return;
    float h[3] = {FIELD(float, pl, 0x40), FIELD(float, pl, 0x44) + 90.0f, FIELD(float, pl, 0x48)};
    float size = FIELD(float, rec, 0x1ac) * FIELD(float, rec, 0x1b0), best = 50.0f;
    uint32_t n = 0, bn = 0xffff, push = 0;
    for (; FIELD(uint16_t, r, 0) != 0xffff && n < 128; r += 44, n++) {
        if ((FIELD(uint16_t, r, 10) & 0x80d2) || (FIELD(uint16_t, r, 12) & FIELD(uint16_t, rec, REC_PARTOFF))) continue;
        push++;
        uint32_t shape = FIELD(uint16_t, r, 4);
        const float *ma = jmat(self, FIELD(uint16_t, r, 0)), *mb = shape == 2 ? jmat(self, FIELD(uint16_t, r, 2)) : ma;
        if (!ma || !mb) continue;
        float a[3], b[3], d[3], t = 0.0f, dd = 0.0f;
        xform(ma, &FIELD(float, r, 20), a);
        if (shape) xform(mb, &FIELD(float, r, 32), b); else for (int k = 0; k < 3; k++) b[k] = a[k];
        for (int k = 0; k < 3; k++) { d[k] = b[k] - a[k]; dd += d[k] * d[k]; }
        if (dd > 0.0f) t = ((h[0] - a[0]) * d[0] + (h[1] - a[1]) * d[1] + (h[2] - a[2]) * d[2]) / dd;
        if (t < 0.0f) t = 0.0f;
        if (t > 1.0f) t = 1.0f;
        float q[3] = {a[0] + t * d[0], a[1] + t * d[1], a[2] + t * d[2]};
        float depth = FIELD(float, r, 16) * size - dist(h, q);
        if (depth > best) { best = depth; bn = n; }
    }
    if (bn != 0xffff && ++s_n <= 80)
        logf("dalaport: body %s push: hunter %d %d %d inside rec %u by %d (%u push records) nopush %u act %u/%u mode %u",
             tail ? "tail" : "head", (int)h[0], (int)h[1], (int)h[2], bn, (int)best, push,
             FIELD(uint8_t, rec, REC_NOPUSH), FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_CAT + 1),
             MODE(self));
}

/* which part took the damage (counters rec+0x488 + 2 part; 0x9d6f8 adds the BDD record's part +8) */
static void part_log(void *self, uint32_t tail)
{
    static uint16_t s_dmg[2][8];
    static uint32_t s_n;
    const uint8_t *rec = REC(self);
    for (uint32_t p = 0; p < 8; p++) {
        uint16_t d = FIELD(uint16_t, rec, REC_PARTDMG + 2 * p);
        if (d == s_dmg[tail][p]) continue;
        if (++s_n <= 150) {
            void *pl = local_hunter();
            float h[4] = {0};
            if (pl) jointPos(pl, 0, h);
            logf("dalaport: body %s part %u dmg %u -> %u mot %x act %u/%u hunter %d %d %d", tail ? "tail" : "head",
                 p, s_dmg[tail][p], d, curMotion(self), FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_CAT + 1), (int)h[0], (int)h[1], (int)h[2]);
        }
        s_dmg[tail][p] = d;
    }
}

void dala_body_frame(void *self)
{
    uint32_t tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff);
    cache_check(self, tail);
    push_check(self, tail);
    part_log(self, tail);
}
