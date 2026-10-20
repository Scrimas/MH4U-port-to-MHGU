/* em089 part breaks: break records, break / sever visibility, cut tail, detach bits (see em089_break.h). */
#include "game.h"
#include "util.h"
#include "em089_break.h"
#include "em089_snd.h"
#include "em089_efx.h"
#include "em089.h"
#include "em089_pile.h"

/* enemy item drop at a position: 4U 0x911f58(enemy, pos, chance %, 0) = GU 0xac0ec (em089_shell051.c) */
typedef int (*enemy_drop_t)(void *enemy, const float *pos, uint32_t chance, uint32_t zero);
#define enemyDrop FN(enemy_drop_t, 0xac0ec)

/* ---- break records for the dtbparts object (GU format {part, LR count, HR count, group}) ----
 * Parts and counts = the 4U em089 emd cond-6 rows (part = param, required count = threshold, all 1): head 0,
 * back 1, wings 2 / 3, tail 6, chest 7 (names: k_part_names). 4U has no reward grouping in these files, so the groups
 * follow GU's conventions: positive group = flag on the first broken record of the group (0x99f98), wings share
 * one (Rathian: wings group 2). Groups 1 / 2 are the bits Kushala (donor of the per-index reward tables) uses for
 * head / wings; 3..5 have no donor reward list. The file still holds Kushala's 2 records (0, 255, 255, 1),
 * (5, 1, 1, 2): head never breaks, hind legs give the wing flag. */
#define N_BREAKS 6
static const uint8_t k_breaks[N_BREAKS][4] = {
    {0, 1, 1, 1}, {2, 1, 1, 2}, {3, 1, 1, 2}, {1, 1, 1, 3}, {6, 1, 1, 4}, {7, 1, 1, 5},
};

/* ---- 4U em089 emd +0x88 rows with cond 6 (break count(param) >= t) / cond 1 (detached bits & param) ----
 * {group, cond, mode (0: hidden while it holds, 1: hidden while it does not), param, only_clear}. only_clear = the
 * group also has a tar cond-7 row (written by tar_vis in em089_act.c): break / sever may only hide it. Every other
 * group listed has no other row, so its bit is the exact 4U value. g35 has two rows (tail broken, not severed). */
#define N_ROWS 22
static const uint8_t k_rows[N_ROWS][5] = {
    {13, 1, 0, 1, 1}, {14, 1, 0, 1, 1}, {19, 1, 0, 1, 1}, {34, 6, 0, 0, 1},      /* + tar rows */
    {26, 6, 0, 0, 0}, {27, 6, 1, 0, 0},                                           /* head (part 0) */
    {104, 6, 0, 1, 0}, {16, 6, 1, 1, 0},                                          /* neck / chest (1) */
    {30, 6, 0, 2, 0}, {31, 6, 1, 2, 0}, {28, 6, 0, 3, 0}, {29, 6, 1, 3, 0},       /* wings (2, 3) */
    {105, 6, 0, 6, 0}, {35, 6, 1, 6, 0}, {35, 1, 0, 1, 0},                        /* tail tip (6) */
    {32, 6, 0, 7, 0}, {33, 6, 1, 7, 0},                                           /* part 7 */
    {25, 1, 1, 1, 0}, {103, 1, 0, 1, 0},                                          /* tail severed */
    {20, 1, 0, 8, 0}, {21, 1, 1, 8, 0}, {101, 1, 0, 8, 0},                        /* spear detached */
};
#define BREAK_THRESHOLD 1   /* every em089 cond-6 row: threshold 1 */

/* XFS states of field 3 (tools/emdata4u.partsvis, Kushala layout): break pairs for parts 0, 1, 2 = 2-4 intact /
 * 7-9 broken, tail 5 / 10. Parts 3, 6, 7 and the spear have no state: k_rows only. */
#define XFS_BROKEN_FIRST 7
#define XFS_TAIL_SEVERED 10

/* 4U part order = Kiranico's MH4U stagger list (head, back, left / right wing limb, front legs / abdominal,
 * rear legs / waist, tail, chest); part 1 carries the Dragonator spear joint (bone 200), part 7 bone 205 */
static const char k_part_names[8][12] = {"head", "back", "l_wing", "r_wing", "front/belly", "rear/waist", "tail",
                                         "chest"};
static const char *part_name(uint32_t p) { return p < 8 ? k_part_names[p] : "?"; }

/* ---- per-monster state (no object fields: em089.c owns the layout). Keyed by pointer; a count that went down
 * = a new monster at a recycled address -> re-init. ---- */
typedef struct {
    void *self;
    void *dtp;           /* dtbparts object the records were installed into */
    uint8_t cnt[8];      /* last break counts */
    uint8_t sev[8];      /* last sever counts */
    uint16_t det;        /* last detached bits */
    uint8_t used;
} brk_t;
static brk_t s_brk[4];
static uint32_t s_next;

static void brk_reset(brk_t *b, void *self)
{
    b->self = self;
    b->dtp = 0;
    for (uint32_t p = 0; p < 8; p++) b->cnt[p] = b->sev[p] = 0;
    b->det = 0;
    b->used = 1;
}

static brk_t *brk_of(void *self)
{
    for (uint32_t i = 0; i < 4; i++)
        if (s_brk[i].used && s_brk[i].self == self) return &s_brk[i];
    brk_t *b = &s_brk[s_next++ & 3];
    brk_reset(b, self);
    return b;
}

static uint8_t *rec_of(void *self) { return FIELD(uint8_t *, self, EN_RECORD); }
static uint32_t break_count(uint8_t *rec, uint32_t p) { return rec[BRK_REC_PART + 12 * p]; }
static uint32_t sever_count(uint8_t *rec, uint32_t p) { return rec[BRK_REC_PART + 12 * p + 1]; }
static uint32_t detached(uint8_t *rec) { return FIELD(uint16_t, rec, BRK_REC_DETACHED); }

/* install k_breaks into the dtbparts object: new array from the MT heap (the resource's clear 0x56180 frees
 * obj+0x64 with 0x7af3e4, so a module array would be freed by the game), old one freed. Idempotent. */
static void install_records(brk_t *b, void *self)
{
    uint8_t *obj = FIELD(uint8_t *, self, BRK_EN_DTBPARTS);
    if (!obj || obj == b->dtp) return;
    b->dtp = obj;
    uint8_t *old = FIELD(uint8_t *, obj, BRK_DTP_RECORDS);
    uint32_t n = obj[BRK_DTP_COUNT], same = (n == N_BREAKS && old);
    for (uint32_t i = 0; same && i < 4 * N_BREAKS; i++) same = old[i] == k_breaks[i / 4][i % 4];
    if (same) return;
    uint8_t *mem = gu_new(4 * N_BREAKS);
    if (!mem) { logf("gogport: em089 break records: alloc failed"); return; }
    for (uint32_t i = 0; i < 4 * N_BREAKS; i++) mem[i] = k_breaks[i / 4][i % 4];
    FIELD(uint8_t *, obj, BRK_DTP_RECORDS) = mem;
    obj[BRK_DTP_COUNT] = N_BREAKS;
    logf("gogport: em089 break records: dtbparts %x had %u (first part %u group %d), now %u", (uint32_t)obj, n,
         n && old ? old[0] : 0, n && old ? (int8_t)old[3] : 0, N_BREAKS);
    if (old) gu_delete(old);
}

/* the 4U row evaluation for the break / sever groups, written into the visibility bits this+0x110 */
static void apply_rows(void *self, uint8_t *rec)
{
    uint32_t det = detached(rec);
    for (uint32_t w = 0; w < 4; w++) {   /* groups < 128 */
        uint32_t hide = 0, touch = 0, only_clear = 0;
        for (uint32_t i = 0; i < N_ROWS; i++) {
            uint32_t g = k_rows[i][0], c = k_rows[i][1], m = k_rows[i][2], prm = k_rows[i][3];
            if (g >> 5 != w) continue;
            uint32_t holds = c == 6 ? break_count(rec, prm) >= BREAK_THRESHOLD : (det & prm) != 0;
            uint32_t bit = 1u << (g & 31);
            touch |= bit;
            if (k_rows[i][4]) only_clear |= bit;
            if (m == 0 ? holds : !holds) hide |= bit;
        }
        if (!touch) continue;
        uint32_t *bits = &FIELD(uint32_t, self, EN_GROUP_VIS + 4 * w);
        uint32_t exact = touch & ~only_clear;
        *bits = (*bits & ~exact & ~(hide & only_clear)) | (exact & ~hide);
    }
}

void em089_break_spawn(void *self)
{
    brk_t *b = brk_of(self);
    brk_reset(b, self);
    install_records(b, self);
}

void em089_break_update(void *self)
{
    uint8_t *rec = rec_of(self);
    if (!rec) return;
    brk_t *b = brk_of(self);
    for (uint32_t p = 0; p < 8; p++)
        if (break_count(rec, p) < b->cnt[p] || sever_count(rec, p) < b->sev[p]) {   /* recycled address */
            logf("gogport: em089 break state reset (part %u count %u < %u)", p, break_count(rec, p), b->cnt[p]);
            em089_break_spawn(self);
            break;
        }
    install_records(b, self);

    /* breaks: framework count went up */
    for (uint32_t p = 0; p < 8; p++) {
        uint32_t c = break_count(rec, p);
        if (c == b->cnt[p]) continue;
        logf("gogport: em089 part %u (%s) flinch count %u -> %u%s, flags %x", p, part_name(p), b->cnt[p], c,
             b->cnt[p] < BREAK_THRESHOLD && c >= BREAK_THRESHOLD ? " BROKEN" : "",
             (uint32_t)rec[BRK_REC_FLAGS]);
        if (b->cnt[p] < BREAK_THRESHOLD && c >= BREAK_THRESHOLD) {
            if (p <= 2) applyPartsState(self, XFS_BROKEN_FIRST + (int32_t)p);
            if (p == BRK_TAIL_PART) { /* 4U slot 64 0x8c67c0 (GU slot 214 counterpart), tail, first break */
                /* [this+0x8d88]+0xed = 0 (0x8c67f8: drop table set 0 = One-shot Binder), then the item drop
                 * 0x911f58(this, W+408, 100, 0) = GU 0xac0ec (capped by the drop counter rec+0x5d54) */
                em089_set_drop_flag(self, 0);
                int got = enemyDrop(self, &FIELD(float, rec, REC_POS_X), 100, 0);
                em089_efx_tail_break(self);   /* 0xc088d8: qe013_002 on joint 143 */
                em089_snd_tail_break(self);   /* event 0x2fcc50 = sound 0 at joint 143 */
                logf("gogport: em089 tail break: item drop -> %d, effect 3300, sound", got);
            }
            /* 4U slot 64 tail for every part: clears flag bit 4 of the part's hurt volumes (W+0x574 = bodydata
             * records, u16 @8 part, u16 @12 flags); GU field / bit meaning not checked */
            logf("gogport: em089 stub: hurt-volume flag 4 of part %u not cleared", p);
        }
        b->cnt[p] = (uint8_t)c;
    }

    /* severs: framework count went up -> cut object / detach bit (Kushala does it at action (10, 114) start) */
    for (uint32_t p = 0; p < 8; p++) {
        uint32_t s = sever_count(rec, p);
        if (s == b->sev[p]) continue;
        logf("gogport: em089 part %u (%s) sever count %u -> %u, detached %x", p, part_name(p), b->sev[p], s,
             detached(rec));
        b->sev[p] = (uint8_t)s;
    }
    if (sever_count(rec, BRK_TAIL_PART) && !(detached(rec) & BRK_DETACH_TAIL)) {
        spawnCutPart(self, 0, 0, BRK_TAIL_JOINT, 0);
        logf("gogport: em089 tail severed: cut object %s, detached %x, flags %x",
             FIELD(uint8_t, self, 0x8b94) == 1 ? "spawned" : "missing (no field-1 model)", detached(rec),
             (uint32_t)rec[BRK_REC_FLAGS]);
        if (!(detached(rec) & BRK_DETACH_TAIL)) setDetached(self, BRK_DETACH_TAIL);
    }
    if (sever_count(rec, BRK_SPEAR_PART)) {
        if (!(detached(rec) & BRK_DETACH_SPEAR)) {
            setDetached(self, BRK_DETACH_SPEAR);
            logf("gogport: em089 Dragonator spear detached (bit 8, groups 20/101 off, 21 on)");
        }
        em089_pile_sever(self);   /* the falling spear = cut slot 1 (em089_pile.c; no-op once started) */
    }
    if (detached(rec) != b->det) {
        if ((detached(rec) & BRK_DETACH_TAIL) && !(b->det & BRK_DETACH_TAIL))
            applyPartsState(self, XFS_TAIL_SEVERED);
        b->det = (uint16_t)detached(rec);
    }

    apply_rows(self, rec);   /* every frame: survives tar_vis rewriting g13 / g14 / g19 / g34 */
}

uint32_t em089_break_state(void *self)
{
    uint8_t *rec = rec_of(self);
    if (!rec) return 0;
    uint32_t m = detached(rec) << 8;
    for (uint32_t p = 0; p < 8; p++)
        if (break_count(rec, p) >= BREAK_THRESHOLD) m |= 1u << p;
    return m;
}
