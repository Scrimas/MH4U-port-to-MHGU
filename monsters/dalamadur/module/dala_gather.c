/* dala_gather.c: GU gather / carve points created at runtime for Dalamadur (dala_gather.h): the meteor scales' mining
 * points (4U uShell038, dala_shell038.c) and the head's on-body carve point (4U uEm024 slot 39 / 48).
 * C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4. Research: notes/plan.md section 6
 * ("Meteor scale research", "Mining helper").
 *
 * 4U (C): 0x9357ec(owner, record, &pos, area, b) = point kind 1 of the manager (0x5b90fc(mgr, 1)): +0x34 position,
 * +0x2f area, +0x4c radius = rec f0, +0x50 height = rec f4, +0x54 type = rec b8, +0x2e = rec b9, u16 +0x30 = rec h10,
 * +0x1a = 1, register 0x5b9aa8; item list +0x28 = [0x1002a5c + 4 * (u16 0x1003ed4[em] + 4 * rec b12 + rank 0x6bc55c)]
 * ({u8 weight, u8 qty, u16 item} closed by weight 0xff); no list for the rank -> the point is released (0x5b9ebc)
 * and -1 returned (0x9358dc). Records: meteor scale 0x102fab4 {350, 200, type 29, 4, 1 gather, list 0}, head
 * 0xfdc924 {400, 600, type 1, -, 2, list 1} (its counts are set again to 2 + the carve-skill bonus, 0x76d878).
 * GU (C, the same manager design; creators 0xaba9c (carcass carve) and uEm056 0xee4a68): p = 0x31b6e0(mgr, 0) (128
 * points of 128 B at mgr+0x24, sets +0x70 bit 0, handle s16 +0x4c = running counter & 0x7fff, +0x60 = 3), area
 * 0x3191a0, position +0x4, icon 0x3191d8 (+0x68), radius +0x44, height +0x48, type +0x64, +0x56 |= 1, u16 +0x4e /
 * +0x50 gathers, item table 0x319358(p, table, 0) (kept at +0x38 and rolled per gather by 0x31b37c: the same list
 * format, weighted by the sum of the weights), life +0x40 (0 = none), register 0x31abac(mgr, p, 0). Release:
 * 0x31b16c(mgr, h) (the registered list, 0 = none) then 0x31aaf4(mgr, p); a used-up point frees itself 20 frames
 * later (0x318b9c -> 0x31aaf4), so a release looks the handle up first. Types (GU dispatch 0x3007c4): 1 / 17 carve,
 * 2 / 18 mining (no pickaxe in GU); 4U's meteor type 29 acts as 2 there (S) and GU's 29 is another kind: type 2.
 * Icon 0 = none, as 4U leaves +0x55 unset (S; user 2026-10-21: no icon).
 * Item lists: data file section GPTS of the head entry of the variant (monsters/dalamadur/tools/gather_em090.py: the
 * 4U lists through items_em090.py's item mapping), picked by the running quest's GU rank s8 [[quest]+0xa4]+44]
 * (module/items.c; +0xa4 written by the quest setup 0x3adea8, C): 2 High, 4 G; any other rank: no point, as 4U.
 * Multiplayer: the point manager has no net calls (C): every machine makes its own points, as 4U (per machine);
 * the meteors land at the synced spot (the action random, dala_meteor.c) and the head point exists on every machine.
 * Nothing is synced. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"
#include "em090.h"
#include "dala_gather.h"

/* GU carve / gather point manager (C, 0xaba9c -> 0x31b6e0(*[GOT 0x1838d94 = 0x1889ec0], kind 0)): +0x24 = 128 points
 * of 128 B (tested by 0x31aaf4 before a release), +0x5c the registered points (+0x2c next) */
#define CPT_MGR    (*(uint8_t **)MAIN(0x1889ec0))
#define CPT_ARRAY  0x24
#define CPT_COUNT  128
#define PT_POS     0x04    /* float x, y, z */
#define PT_LIFE    0x40    /* float frames left, 0 = none */
#define PT_RADIUS  0x44
#define PT_HEIGHT  0x48
#define PT_HANDLE  0x4c    /* s16 */
#define PT_MAX     0x4e    /* u16 max gathers */
#define PT_SURE    0x50    /* u16 sure gathers */
#define PT_FLAGS2  0x56    /* u8: bit 0 set by both GU runtime creators (0xabcac, 0xee4b78; G: runtime point) */
#define PT_TYPE    0x64    /* u32 */
#define PT_USED    0x70    /* u8 bit 0 in use (0x31b768), bit 1 registered */
typedef uint8_t *(*pt_alloc_t)(void *mgr, uint32_t kind);
#define ptAlloc    FN(pt_alloc_t, 0x31b6e0)
typedef void (*pt_set_t)(void *pt, uint32_t v);
#define ptArea     FN(pt_set_t, 0x3191a0)
#define ptIcon     FN(pt_set_t, 0x3191d8)
typedef void (*pt_items_t)(void *pt, const void *table, uint32_t roll_now);
#define ptItems    FN(pt_items_t, 0x319358)
typedef void (*pt_reg_t)(void *mgr, void *pt, uint32_t zero);
#define ptRegister FN(pt_reg_t, 0x31abac)
typedef uint8_t *(*pt_find_t)(void *mgr, int32_t h);
#define ptFind     FN(pt_find_t, 0x31b16c)
typedef void (*pt_free_t)(void *mgr, void *pt);
#define ptFree     FN(pt_free_t, 0x31aaf4)
/* the local hunter's carving-skill bonus (0xaba9c: 0x69bfc(*[GOT = 0x1851fe0]), C) = 4U 0x68b3f8 (S) */
typedef uint32_t (*carve_bonus_t)(void *obj);
#define carveBonus FN(carve_bonus_t, 0x69bfc)
#define CARVE_OBJ  (*(void **)MAIN(0x1851fe0))
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx   FN(joint_mtx_t, 0xc1660)   /* = 4U 0x930894 */
#define QUEST_RUN  (*(uint8_t **)MAIN(0x188ad90))   /* the running quest (module/port.c) */
#define EN_AREA    0x1054
#define LOG_MAX    60

static uint32_t s_log;

static int quest_rank(void)
{
    uint8_t *q = QUEST_RUN;
    const uint8_t *info = q ? FIELD(const uint8_t *, q, 0xa4) : 0;
    return info ? (int8_t)info[44] : -1;
}

/* GPTS: u32 n, n x {u8 GU rank, u8 list, u16 0, u32 offset}, lists {u8 weight, u8 qty, u16 item} closed by weight
 * 0xff; the head entry of the owner's variant */
static const uint8_t *item_list(void *owner, uint32_t list, int rank)
{
    int m = FIELD(uint8_t, owner, EN_VARIANT) ? SHAH_DALAMADUR_PORT : DALAMADUR_PORT;
    uint32_t size = 0;
    const uint8_t *s = port_section(m, "GPTS", 0, &size);
    uint32_t n = s && size >= 4 ? PORT_U32(s, 0) : 0;
    for (uint32_t i = 0; i < n && 4 + 8 * (i + 1) <= size; i++) {
        const uint8_t *e = s + 4 + 8 * i;
        if ((int)e[0] == rank && e[1] == list && PORT_U32(e, 4) + 4 <= size) return s + PORT_U32(e, 4);
    }
    return 0;
}

int32_t dala_gather_new(void *owner, uint32_t list, uint32_t type, uint32_t icon, float radius, float height,
                        uint32_t gathers, const float *pos, uint32_t area, const char *what)
{
    int rank = quest_rank();
    const uint8_t *items = owner ? item_list(owner, list, rank) : 0;
    uint8_t *mgr = CPT_MGR, *p = 0;
    if (items && mgr && pos) p = ptAlloc(mgr, 0);
    if (!p) {                             /* 4U 0x9358dc: no list for the rank -> no point */
        if (++s_log <= LOG_MAX)
            logf("dalaport: gather %s: no point (rank %d, list %u %s, manager %x%s)", what, rank, list,
                 items ? "found" : "missing", (uint32_t)mgr, items && mgr && pos ? ", full: 128 points" : "");
        return -1;
    }
    ptArea(p, area);
    for (int i = 0; i < 3; i++) FIELD(float, p, PT_POS + 4 * i) = pos[i];
    ptIcon(p, icon);
    FIELD(float, p, PT_RADIUS) = radius;
    FIELD(float, p, PT_HEIGHT) = height;
    FIELD(uint32_t, p, PT_TYPE) = type;
    p[PT_FLAGS2] |= 1;
    FIELD(uint16_t, p, PT_MAX) = (uint16_t)gathers;
    FIELD(uint16_t, p, PT_SURE) = (uint16_t)gathers;
    ptItems(p, items, 0);
    FIELD(float, p, PT_LIFE) = 0.0f;
    int32_t h = FIELD(int16_t, p, PT_HANDLE);
    ptRegister(mgr, p, 0);
    if (++s_log <= LOG_MAX) {
        uint32_t n = 0, sum = 0;
        for (const uint8_t *e = items; e[0] != 0xff && n < 16; e += 4, n++) sum += e[0];
        logf("dalaport: gather %s point %d: type %u icon %u radius %d height %d gathers %u at %d %d %d area %u, "
             "rank %d list %u (%u items, weights %u, first %u x%u %u%%)", what, h, type, icon, (int)radius,
             (int)height, gathers, (int)pos[0], (int)pos[1], (int)pos[2], area, rank, list, n, sum,
             FIELD(uint16_t, items, 2), items[1], items[0]);
    }
    return h;
}

int dala_gather_free(int32_t h, const char *why)
{
    uint8_t *mgr = CPT_MGR;
    uint8_t *p = h != -1 && mgr && FIELD(void *, mgr, CPT_ARRAY) ? ptFind(mgr, h) : 0;
    if (p) ptFree(mgr, p);
    if (h != -1 && ++s_log <= LOG_MAX)
        logf("dalaport: gather point %d %s (%s)", h, p ? "freed" : "already gone", why);
    return p != 0;
}

float *dala_gather_pos(int32_t h)
{
    uint8_t *mgr = CPT_MGR, *pts = mgr ? FIELD(uint8_t *, mgr, CPT_ARRAY) : 0;
    for (uint32_t i = 0; pts && h != -1 && i < CPT_COUNT; i++) {
        uint8_t *p = pts + i * 128;
        if ((p[PT_USED] & 1) && FIELD(int16_t, p, PT_HANDLE) == h) return &FIELD(float, p, PT_POS);
    }
    return 0;
}

/* 4U slot 39 0x76d830..0x76d888: 0x9357ec(this, 0xfdc924, &W+0x198 (the object position), area W+0x14c, 0) ->
 * work+0x50; then u16 +0x30 / +0x32 = 0x68b3f8(..) + rec h10 2 (GU: 2 + 0x69bfc, as 0xaba9c). Read on this machine:
 * the local hunter's skill, as both games. */
void dala_head_point_spawn(void *self)
{
    int32_t *h = &DALA_WORK(int32_t, self, DALA_W_GATHER);
    if (*h != -1) dala_gather_free(*h, "head spawned again");
    void *o = CARVE_OBJ;
    uint32_t bonus = o ? carveBonus(o) : 0;
    *h = dala_gather_new(self, DALA_GL_HEAD, DALA_GP_CARVE, 0, 400.0f, 600.0f, 2 + bonus,
                         &FIELD(float, REC(self), REC_POS_X), FIELD(uint8_t, self, EN_AREA), "head on-body");
}

/* 4U slot 48 0x773c24..0x773cc4: the point of work+0x50 (0x5b90c0, none once used up) at joint 5 * (0, 350, 400):
 * 0x930894's rows 0 / 1 / 2 times 0 (s16, 0x77333c) / 350 / 400 plus row 3 (C). 4U never releases it; once it is gone
 * the handle is dropped here (same result: 0x5b90c0 finds nothing). */
void dala_head_point_frame(void *self)
{
    static uint32_t s_t, s_n;
    int32_t *h = &DALA_WORK(int32_t, self, DALA_W_GATHER);
    float *pt = *h != -1 ? dala_gather_pos(*h) : 0;
    if (!pt) {
        if (*h != -1 && ++s_log <= LOG_MAX) logf("dalaport: gather head on-body point %d gone (used up)", *h);
        *h = -1;
        return;
    }
    float m[16];
    jointMtx(self, 5, m);
    for (int i = 0; i < 3; i++) pt[i] = m[4 + i] * 350.0f + m[8 + i] * 400.0f + m[12 + i];
    if (++s_t % 600 == 1 && ++s_n <= 12) {   /* test log: the point and its gathers left */
        const uint8_t *p = (const uint8_t *)pt - PT_POS;
        logf("dalaport: gather head on-body point %d at %d %d %d, gathers %u / %u", *h, (int)pt[0], (int)pt[1],
             (int)pt[2], FIELD(uint16_t, p, PT_MAX), FIELD(uint16_t, p, PT_SURE));
    }
}

void dala_head_point_release(void *self)
{
    int32_t *h = &DALA_WORK(int32_t, self, DALA_W_GATHER);
    if (*h != -1) dala_gather_free(*h, "head dead / deleted");
    *h = -1;
}
