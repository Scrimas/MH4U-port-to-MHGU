/* em057_01_start.c: Stygian Zinogre, the 4U action-start work of the ported actions (batch S, notes/plan.md "Gap found
 * 2026-10-28"). Both games run a class virtual once when setAction starts an action: 4U vt47 0x857060(this, cat, num),
 * GU vt129 0xeefed0 (same arguments, SLOT_ACTION_START). GU reused action numbers, so for an s_moves row GU's vt129
 * does the start work of GU's meaning of that number (or none). sz_action_start does the 4U part GU lacks; it runs
 * from an entry hook on vt129 (em057_01_start_c, user's OK 2026-10-28), so at the action start itself, before GU's
 * own start work, on every machine that starts the action. C = confirmed in code, S = strong, G = guess.
 *
 * 4U vt47 (C, MH4U v1.1): the head 0x857060..0x8570c4 picks the charge-gain row (rank, Stygian +20); then by cat: 1
 * (table 0x857118, num 3..43), 2 (0x857340, num 38..42), 3 (num 6 8 9), 10, 11 (returns at 0x85782c / 0x857860); then,
 * except for cat 11, the tail 0x857914: cat 7 -> 0x858cec(this, num) (charge drain), charged -> work+0 += the case's
 * gain (0 for every s_moves row), work+0 <= 0 -> 0 and, when charged, the discharge 0x856344, work+0x118 / +0x11a =
 * 0xffff. So "cats 1 2 3 10 11 only" (notes/plan.md, the gap) misses the cat-7 drain of the tail.
 * GU vt129 (C, MHGU 1.4): the same head (row eeff08, phase1-variant-map.md D); by cat: 1 (num 3..33 only), 2 (38..42),
 * 10, 11, no cat 3; the tail ef0688: work+0x58 handle release (GU only, every action), cat 7 -> ef0c68(self, num), the
 * same charge add / reset / discharge (eefca0) and work+0x11e / +0x120 = 0xffff, then effect handles this+0xcb08..
 * 0xcb10 by the charged state (GU only, every action).
 * Per s_moves row (C):
 * - 2/47-52 61-70 72 73 75-77 79 80 and 13/3: no case in either game, same tail: nothing to do.
 * - cat 7: 0x858cec = ef0c68 (same body: charged (0x90f90c / isCharged), work+0 s16 >= 1, a per-number cost -1 / -3 /
 *   -5; rank (0x69ae70 / questRank, GU site ef10c0, same GOT slot as QUEST_GLOBAL) >= 2: -5 -> -2, -3 -> -1, -1 -> none;
 *   work+0 += cost, clamped to 1..100), but GU's cost table (ef0cb4, 249 rows) is not 4U's (0x858d50, 0x858e5c and the
 *   compare tree 0x858d20..0x858e48). GU's cost is 0 where 4U drains for 7/2 3 21 31 166-169 172-177 186-189 200 215
 *   216; every other row is equal (7/4 5 35 36 160-165 170 171 205 209: -1; 7/87 203 206: -3; 7/113 115: -5; the rest
 *   0 in both). No ported row is drained by GU and not by 4U: nothing to undo. drain_4u = 4U's cost for the GU-0 rows.
 * - 1/39-43: 4U cases 0x8572a4 0x8572c4 0x8572d4 0x857304 0x857314; GU none (its cat-1 table ends at 1/33) and GU does
 *   nothing else for these numbers. Their fields and calls have no GU site (sz_unmapped_939c00 / sz_unmapped_94c980):
 *   logged, no effect. W+0x790d = the sound manager's byte (no GU field, em057_01_mv_f.c).
 * Once per action: vt129 runs once per setAction (C: slot 129 of vtable 0x17d19bc; r1 = cat, r2 = num kept in r10 /
 * r5 at eefee0 / eefee4). Every action of a Stygian comes through; drain_4u and the cat-1 cases list s_moves numbers
 * only, so the others are no-ops (C by construction). Before the hook (batch S) this ran on a row's first dispatch
 * frame and had to skip while setActionNext's request was pending (7/176 177's G-rank branch leaves the step byte 0).
 * Order: 4U drains in vt47's tail, GU's start work then adds the gain (0 for our rows) and discharges at work+0 <= 0;
 * the drain clamps to >= 1, so running it first changes nothing (C).
 * Multiplayer: vt47 / vt129 and this run on every machine; 0x858cec has no controller test (C), nor the 1/39-43
 * cases. Only 0x939c00's tail 0x91de40 has a controller-only part (W+0x1d9 == 1; unmapped, not run). */
#include "em057_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define START_SITES 24

/* rate limit: a 4U site logs its first 4 lines (as em057_01_mv_f.c); noinline as there */
__attribute__((noinline)) static int start_line(uint32_t site)
{
    static uint32_t s_site[START_SITES];
    static uint8_t s_lines[START_SITES];
    uint32_t i = 0;
    while (i < START_SITES && s_site[i] && s_site[i] != site) i++;
    if (i == START_SITES || s_lines[i] >= 4) return 0;
    s_site[i] = site;
    s_lines[i]++;
    return 1;
}

/* ---- stub: 4U 0x939c00(this, f) (C, body): W+0x7e80 |= f, W+0x7e81 &= ~f, and for f & 32 a tail call 0x91de40(this):
 * when W+0x7e80 & 32 is set: on the controlling machine (W+0x1d9 == 1) W+0x5e4 = W+0x5dc = 0.0 and, for W+0x7e80 & 2,
 * 0x923c3c; 0x9306e4 -> W+0x7ac0 = 0.0; 0x9239fc -> W+0x7a34 = 0.0; W+0x7e81 = 0 (0x94815c); W+0x7e80 &= 32
 * (0x941b5c(223)): bit 32 ends the other status bits and their timers. Fields: W+0x7e80 / +0x7e81 = GU rec+0x5e08 /
 * +0x5e09 (C: GU a1fac a1fc8 a1fe4 = 4U 0x941b5c 0x936418 0x94815c, same bodies; the 0x2078 shift of W+0x7e6b ->
 * rec+0x5df3). Site method, no GU site: GU vt129 has no 1/41 case, the GU look-alikes of 4U's other callers ef45e0 (=
 * 0x847274) and de7610 (= 4U 0x7302e4, the same wake-roar path) drop the call, and no GU code calls a function with 32
 * and then a second one as 4U does (C: every `mov r1, #32` followed by two calls). GU sets bits 1 2 4 8 16 of
 * rec+0x5e08 (a2908 a24a4 a2c4c a3930 a2f54) and tests bit 32 at 50 sites, but no setter of bit 32 was found (S).
 * Meaning G: a rested state after waking, not rage (rage is W+0x530 == 1; emd mesh condition 10 is W+0x53a or this bit,
 * monsters/dalamadur/notes/class-study.md); 4U also sets it in the spawn state 9 of 0x93f6e4 (with 94c980 and
 * W+0x545 = 1). Logged, no effect (1/41 here, 1/43 in em057_01_mv_f.c). */
void sz_unmapped_939c00(void *self, uint32_t f, uint32_t site)
{
    (void)self;
    if (start_line(site)) logf("szport: unmapped 4U 939c00(%u) skipped (4U %x, no GU site)", f, site);
}

/* ---- stub: 4U 0x94c980(this) (C, body): W+0x540 = 60.0 x an s16 per-em table (quest ids 0x55f5 0x55f6 0xeeb6 0xef16
 * 0xef17: 0xfff468, else 0xfff090; 60 for em 48 / 49: 3600.0). 4U 0x9482d4 (1/39) is the same body with the tables
 * 0xfff372 / 0xffef9a (also 60). W+0x540 counts down by the frame delta to 0 (0x947620..0x947648) and while it is above
 * 0 0x93732c (a status build-up routine that also tests bits 32 4 1 16 of W+0x7e80) skips a branch (0x937440). No GU
 * site (as 0x939c00) and no GU field found. Meaning G: the timer of the rested state. Logged, no effect. */
void sz_unmapped_94c980(void *self, uint32_t site)
{
    (void)self;
    if (start_line(site)) logf("szport: unmapped 4U 94c980 (W+0x540 = 3600) skipped (4U %x, no GU site)", site);
}

/* 4U vt47 cat-1 stores with no GU field (W+0x53a, W+0x544, W+0x545: no GU site; W+0x790d: em057_01_mv_f.c) */
static void start_store(uint32_t num, uint32_t field, uint32_t v, uint32_t site)
{
    if (start_line(site)) logf("szport: start 1/%u: 4U W+0x%x = %u skipped (4U %x, no GU field)", num, field, v, site);
}

/* 4U 0x858cec's cost for the cat-7 rows whose cost in GU ef0c68 is 0 (C, file header) */
static int32_t drain_4u(uint32_t num)
{
    switch (num) {
    case 2: case 3: case 21: case 31: case 166: case 167: case 168: case 169: case 172: case 173: case 174: case 175:
    case 176: case 177: case 188: case 189: case 200:
        return -1;
    case 186: case 187: case 215: case 216:
        return -5;
    default:
        return 0;
    }
}

/* 4U 0x858cec(this, num) with drain_4u's cost (C: the body of GU ef0c68 for a non-variant-4 monster) */
static void drain(void *self, uint32_t num)
{
    int16_t *cnt = &FIELD(int16_t, WORK(self), 0);     /* the charge counter [4U work+0 s16] */
    int32_t cost = drain_4u(num);
    if (!isCharged(self) || *cnt <= 0) return;          /* 4U 0x858cfc / 0x858d1c */
    void *q = QUEST_GLOBAL;
    if (q && questRank(q) >= 2) {                       /* 4U 0x858f50 */
        if (cost == -5) cost = -2;
        else if (cost == -3) cost = -1;
        else if (cost == -1) return;
    }
    if (cost == 0) return;
    int32_t was = *cnt;
    int16_t v = (int16_t)(was + cost);
    *cnt = v;
    if (v >= 100) *cnt = 100;                           /* 4U 0x858f9c */
    else if (v <= 1) *cnt = 1;
    if (start_line(0x85792c)) logf("szport: start 7/%u charge %d -> %d (4U 858cec)", num, was, (int32_t)*cnt);
}

static void sz_action_start(void *self, uint8_t cat, uint8_t num)
{
    if (cat == 7) {
        drain(self, num);                               /* the vt47 tail 0x857914 */
        return;
    }
    if (cat != 1) return;
    switch (num) {
    case 39:                                            /* 4U 0x8572a4 */
        start_store(39, 0x544, 1, 0x8572a4);
        start_store(39, 0x53a, 1, 0x8572ac);
        if (start_line(0x8572b4))
            logf("szport: start 1/39: unmapped 4U 9482d4 (W+0x540 = 3600) skipped (4U %x, no GU site)", 0x8572b4);
        start_store(39, 0x790d, 4, 0x8572bc);
        return;
    case 40:                                            /* 4U 0x8572c4 */
        start_store(40, 0x790d, 6, 0x8572cc);
        return;
    case 41:                                            /* 4U 0x8572d4 */
        start_store(41, 0x545, 1, 0x8572d4);
        sz_unmapped_939c00(self, 32, 0x8572e0);
        sz_unmapped_94c980(self, 0x8572ec);
        start_store(41, 0x790d, 8, 0x8572f4);
        return;
    case 42:                                            /* 4U 0x857304 */
        start_store(42, 0x790d, 9, 0x85730c);
        return;
    case 43:                                            /* 4U 0x857314 */
        start_store(43, 0x545, 1, 0x857314);
        start_store(43, 0x790d, 9, 0x85731c);
        return;
    default:
        return;
    }
}

/* GU uEm057_00 slot 129 0xeefed0(self, cat, num) entry: 4U's start work for a Stygian, then GU's own */
int em057_01_start_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (self && FIELD(uint16_t, self, EN_ID) == STYGIAN_ZINOGRE_EM_ID)
        sz_action_start(self, (uint8_t)regs[R1], (uint8_t)regs[R2]);
    return 0;
}
