/* em057_01_ai.c: Stygian Zinogre AI conditions and ops (notes/plan.md B7). The AI table is 4U em048_cmd for em 49 in
 * GU's language (build_em057_01_arc.py cmdtbl()); GU's EMC interpreter runs it (op dispatch 0x837a8, block evaluator
 * 0x8e144 = 4U 0x92b50c, same condition types). 4U em 49 vs GU uEm057_00 variant 1, read 2026-10-28:
 *
 * Monster conditions, op 0x6f -> 4U uEm048 slot 51 0x8579fc (12 ids) / GU uEm057_00 slot 133 0xef2fd0 (16 ids; GU
 * 0x81ff8 is a plain vcall of slot 133, the only reference to 0xef2fd0 is that vtable slot, C):
 * - id 0: charged, 4U 0x90f90c (W+0x7e6b) = GU 0x81790 (rec+0x5df3) -> 0 / 1. SAME (C), no variant test.
 * - id 5: charge counter (s16 at work+0: 4U this+0x8c88 -> work, GU EN_WORK) >= 100 -> set to 100, 1; else 0. SAME (C).
 * - id 10: not charged and counter >= 100 -> 1. SAME (C: GU `> 99`).
 * - id 11: 4U 0x857b48: W+0x544 || W+0x545 -> 1; GU: constant 0 (0xef31d8). DIFFERENT (C). Used by g16 s0: 0 -> 1/35
 *   (lying wait), else 1/39 (0x847274 r1 3, a roar; GU's g16 s0 has no else). Stores (C): W+0x544 = 1 at the vt47
 *   starts of 1/36 1/39 (0x85728c 0x8572a4) and in 0x937664 where it ends W+0x53a (0x9379f8 + 0x937a00, 0x937a8c +
 *   0x937a94, 0x937b3c + 0x937b44: W+0x53a = 0, W+0x544 = 1); W+0x545 = 1 at the starts of 1/41 1/43 (0x8572d4
 *   0x857314); 0x93f6e4 clears both (0x93f758 0x93f760) and sets them in its spawn states (0x93f820 0x93f8ac ...).
 *   Meaning G: rest / woken flags ("rest flags" below). GU has no field for them (batch S: no GU site).
 *
 * Ops (engine ops: em / variant not involved unless noted):
 * - 0x79 (g0 s3): 4U 0x9532b8 value (s16) 0x934620 -> 0x93ed2c(this, 0, W+0x278, W+0x27a, W+0x27c), type 11; GU
 *   0x85084 (s16) 0xb72a8 -> 0xb73c8(this, 0, rec+0x230, +0x232, +0x234), type 11 = all bits of the case's big-endian
 *   word set (GU 0x8eb3c). Same flag function (C for its first part: state class 1 / 5 / 6 -> 16 / 4 / 8, else 1 | 2;
 *   0x8ebe0 = 4U 0x94a524 -> 64 (+128 / +256), 512, 1536). GU adds two early 0x1000 answers (target in another area,
 *   this+0x1406 & 2): no case of our g0 s3 tests 0x1000, so they reach its default `20 0e`, as 4U's own 0x1000
 *   answers do (0x93ee7c, 0x93eee8). GU's own g0 s3 has the same 0x79 cases and targets (C). SAME (S).
 * - 0x82 arg 0 (g0 s3): value = the arg (target slot 0), type 25 in both (4U 0x953610, GU 0x85174 -> 0x859b4): height
 *   of the target slot above the ground under it (4U 0x92ba58 W+536 + 16 * slot, ground query with area W+0x14c; GU
 *   0x8e644 rec+464 + 16 * slot, 0x49b4c with area this+0x1054), case value x 100. GU's g0 s3 has the same block. SAME
 *   (S; C for the structure).
 * - 0x87 (g0 s12): 4U 0x953818 / GU 0x8a088: target (type 1 / 2, index, W+0x27c / rec+0x234 != 255) in our area
 *   (W+0x14c / this+0x1054) and a map test of two of its bytes (4U 0x6c4ee4, GU 0x497ac); GU also asks the target object
 *   vt+0x88 (valid) first (engine-wide). GU's own g0 s12 opens with the identical block (C). SAME (S).
 * - 0x80 (g0 s3): 4U 0x953500: if ((s8) W+0x53a) [0x93731c] body, else skip to the else; GU 0xc9b58: always skips to
 *   the else (no test). DIFFERENT (C). W+0x53a: set to 1 by the vt47 starts of 1/36 1/39 (0x857268 0x8572ac), written
 *   per hit in 0x9244e0 (0x924b18: r11 when the hit has flag 0x100000, else 0), cleared by 0x937664 (which then sets
 *   W+0x544, above); no GU field (GU 0xc6e14 = 4U 0x916bcc drops its W+0x53a / bit-32 test too, C).
 * - 0x91 (g0 s3, the else of 0x80): 4U 0x953ef8: if (W+0x7e80 & 32) [0x936418(this, 32)]; GU 0x852bc: a switch on
 *   the em number (this+0xb5f4, 0x83378) whose body, with no case token, never runs (0x8e044 stops at `91 02`). GU's
 *   g0 s3 drops the block. DIFFERENT (C). W+0x7e80 = GU rec+0x5e08 (C: GU a1fc8 = 4U 0x936418, same body); GU sets
 *   its bits 1 2 4 8 16 but no setter of bit 32 was found (S, batch S).
 *   In play: g0 s3's body R (weights 2 / 2 / 1 of 100: op 0x01 sets target slot 0 to kind 5 with 1 / 0 / 2, 10; G for
 *   the kind's meaning) runs in 4U while the rest flag or bit 32 is set, never in GU.
 * - Query 0x9431f4 cases 64 / 65 (uEm048 slot 94 0x857b6c): not reached by the AI script (C). The EMC interpreter
 *   (dispatch 0x94f8cc, block evaluator 0x92b50c, conditions 0x9238e8 = slot 51) never calls slot 94; the only virtual
 *   call of slot 94 in 4U is 0x3d9c4c in 0x3d9b84, another bytecode evaluator (ops 84 / 90 / 103, no direct caller).
 *
 * Fixes: cmdtbl() merges g0 s3's 0x80 block and its 0x91 else (R twice, the same bytes) into one 0x80 block: if
 * (W+0x53a || bit 32) R. The two hooks below answer 4U's tests for Stygian; every other monster and id keeps GU's code.
 * The rest flags have no GU field and their 4U setters and clears are not ported (em057_01_start.c logs the 1/39 1/41
 * 1/43 stores; 1/36 is a KEEP row; 0x93f6e4, 0x937664, 0x924b18 have no port), so sz_rest_w4u() answers 0 for now (a
 * logged gap) and the hooks give GU's values until the rest state is ported: id 11 -> 0, op 0x80 -> rec+0x5e08 & 32.
 * Multiplayer: conditions and ops run where the AI runs (the controlling machine, this+0x7420); nothing changes for
 * the others.
 *
 * Quest rank (C): op 0x6a = 4U 0x952d04 / GU 0x84ec8, value = the quest rank (4U 0x69ae70: quest file byte 0x8b, S;
 * GU 0x3a8d68: quest byte +15 -> 1 / 3 / 5, else 0), evaluator type 26 (4U 0x92bd08 / GU 0x8e970): a case matches
 * when its value <= the rank. Stygian's selectors g0 s15 (uncharged) and s16 (charged) open with `6a 01 05`: paw slams
 * only from rank 5 (g1 s4 s5 s33 s93, 7/195); g1 s84's `6a 01 04` gives the charged 7/14 -> 7/15 -> 7/16 lead-in from
 * rank 4. Below 4 no script or chain reaches a slam. 4U ranks: LR hub 1, HR caravan 2, HR hub 3, G 5 (his HR quests 3
 * and 2, his G quests 5); GU's HR quests are 3. Test builds with TEST_QUEST_RANK give his quests that rank (below). */
#include "em057_01.h"
#include "alloc.h"
#ifdef TEST_QUEST_RANK
#include "port.h"
#endif

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define AI_SITES 8

/* rate limit: a 4U site logs its first 4 lines (as em057_01_start.c); noinline as there */
__attribute__((noinline)) static int ai_line(uint32_t site)
{
    static uint32_t s_site[AI_SITES];
    static uint8_t s_lines[AI_SITES];
    uint32_t i = 0;
    while (i < AI_SITES && s_site[i] && s_site[i] != site) i++;
    if (i == AI_SITES || s_lines[i] >= 4) return 0;
    s_site[i] = site;
    s_lines[i]++;
    return 1;
}

static int is_stygian(void *self) { return self && FIELD(uint16_t, self, EN_ID) == STYGIAN_ZINOGRE_EM_ID; }

#ifdef TEST_QUEST_RANK
/* test builds: GU 0x3a8d68(quest mgr) entry (the quest rank, file header) answers TEST_QUEST_RANK while one of
 * Stygian's quests runs, so the AI's op 0x6a, the G-rank gates of the ported handlers (questRank) and GU's own rank
 * readers all see that rank (5 = his G-rank AI). Other quests keep GU's answer. */
int em057_01_rank_c(uint32_t *regs)
{
    static uint32_t s_lines;
    int m = port_running_quest(0);
    if (m < 0 || port_monsters[m].em_id != STYGIAN_ZINOGRE_EM_ID) return 0;
    if (s_lines < 4) {
        s_lines++;
        logf("szport: test quest rank %d (quest %u)", TEST_QUEST_RANK, port_quest_id());
    }
    regs[R0] = TEST_QUEST_RANK;
    return 1;
}
#endif

/* 4U rest flags with no GU field (W+0x53a, W+0x544, W+0x545): read as 0 until their setters and clears are ported
 * (file header); site = the 4U read */
uint32_t sz_rest_w4u(void *self, uint32_t field, uint32_t site)
{
    (void)self;
    if (ai_line(site)) logf("szport: AI reads 4U W+0x%x as 0: rest state not ported, no GU field (4U %x)", field, site);
    return 0;
}

/* GU uEm057_00 slot 133 0xef2fd0(self, id) entry: id 11 answers 4U 0x857b48 for Stygian; other ids are the same in
 * both games (file header) and keep GU's code */
int em057_01_cond_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (regs[R1] != 11 || !is_stygian(self)) return 0;
    regs[R0] = sz_rest_w4u(self, 0x544, 0x857b50) || sz_rest_w4u(self, 0x545, 0x857b58);
    return 1;
}

/* GU EMC op 0x80 handler 0xc9b58(self, p) entry, p = the token's sub-code (0 open, 2 else, 0xff end). Stygian's one
 * 0x80 block is cmdtbl()'s merge of 4U's 0x80 and 0x91 tests. At the open, true (4U 0x953528 W+0x53a, then 0x953f24
 * W+0x7e80 & 32 = rec+0x5e08) returns 0 to the interpreter: no skip, the body runs; false keeps GU's skip to the else
 * (= 4U's false path). The else (skip to the end after the body) and the end are the same in both (GU 0xc9bc0 = 4U
 * 0x953568). */
int em057_01_op80_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    const uint8_t *p = (const uint8_t *)regs[R1];
    if (!is_stygian(self) || *p != 0) return 0;
    if (!sz_rest_w4u(self, 0x53a, 0x953528) && !(REC(self)[REC_STATUS] & 32)) return 0;
    regs[R0] = 0;
    return 1;
}
