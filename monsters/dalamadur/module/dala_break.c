/* Part-break records of both halves (goal D6b): the dtbparts break records GU checks when a part's break count
 * goes up. C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * 4U (C): the part table is species row +0x78 (0x91df20() + 0x78 = emd word 32), 32-byte records {u8 part, u8 break
 * count required, u8, u8, u8 group, .., u32 joint +8, f32 offset / scale +0xc.., u8 0xff, RGB +0x1d (break effect
 * colour)}, closed by part 0xff. 0x944e80 (break adder call 0x9453b0) on a part reaching a record's count: group byte
 * bit 0x80 (r10 = 1) = reward only once EVERY record of the group is broken, else only the first broken record of
 * the group rewards; flag bit 1 << (group & 0x7f) at W+0x7987 once; 0x6a8920(mgr, em, group, 0) adds {em, group} to
 * the quest-end list, whose reader 0xabf818 -> 0x68effc(?, em, group) refuses group 8 (no reward) and indexes the
 * break-reward tables [0xf386c0 + 4 * (s32 [0xf384d0 + 4 * em] + 4 * group + rank)] (monsters/tigerstripe_zamtrios/
 * notes/content-data.md section 0). em024 / em110 (head):
 *     part 0 count 1 group 8, part 0 count 4 group 0 (head: Gazer), parts 1 / 2 count 3 group 0x83 (both claws:
 *     Talon / Ripper), part 3 count 1 group 8, part 3 count 2 group 1 (chest: Pectus), part 4 count 1 group 8,
 *     part 4 count 2 group 2 (back: Fanblade);
 * em083 / em111 (tail): part 5 count 1 group 0 (Vortex Bone / Glaive / Tail Scale), part 6 count 1 group 1 (Tail
 *     Shell), part 7 count 1 group 8. Part names from the reward items (S).
 *
 * GU (C, 0x99f98, run by the generic damage code when a break count goes up): record {u8 part, u8 LR count, u8 HR
 * count, s8 group} (dtbparts object enemy+0x75f0: records +0x64, count +0x8c; rank 0x3a8d68() > 4 -> HR count);
 * count == required -> 0xa44e8 (controller only: the break sound 6 + 5 * part + count through this+0xb640 vt+0x1d0);
 * then a NEGATIVE group waits until every other record of the group is broken, a positive one rewards only the first
 * = 4U's 0x80 rule exactly; flag bit (group & 127) of rec+0x5cbe once -> 0x49964 (net + quest list, cond = table
 * 0x162a736 {10, 20, 30, 40, 50, 60, 0, 0}[group]: module/items.c BUI). Differences kept out:
 *   - 4U group 8 (no reward) would read past that table and its bit 1 << 8 cannot be stored in the s8 flag byte (so
 *     0x49964 would run on every later break): those records are left out. They only gave the break sound here;
 *     break counts go up without records (0x97ddc) and the visibility rows read the counts (dala_parts.c).
 *   - groups shifted by one (4U g -> GU g + 1), as Gogmazios (em089_break.c): cond 10 is also GU's tail sever.
 * The four arcs share one dtbparts resource (build_dalamadur_arc.py: Kushala's placeholder under em090_00), so both
 * halves install the same combined list (parts 0..4 head, 5..7 tail: no overlap; a part without dttune HP never
 * counts up, so the other half's records never fire). Reward lists per GU cond: BUI section, goal F. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

#define EN_DTBPARTS   0x75f0   /* enemy: dtbparts object (setter 0x70a4c) */
#define DTP_RECORDS   0x64
#define DTP_COUNT     0x8c
/* MT heap new[] / delete[] [0x7af3a0 / 0x7af3e4]: what the dtbparts loader 0x5575c / clear 0x56180 use, so the
 * array must come from there (the resource frees it) */
#define gu_new    FN(void *(*)(uint32_t), 0x7af3a0)
#define gu_delete FN(void (*)(void *), 0x7af3e4)

#define N_BREAKS 7
static const uint8_t k_breaks[N_BREAKS][4] = {
    {0, 4, 4, 1},         /* head, count 4: 4U group 0 */
    {1, 3, 3, 0x84},      /* claws, count 3, both: 4U group 0x83 */
    {2, 3, 3, 0x84},
    {3, 2, 2, 2},         /* chest, count 2: 4U group 1 */
    {4, 2, 2, 3},         /* back, count 2: 4U group 2 */
    {5, 1, 1, 1},         /* tail half: 4U em083 group 0 */
    {6, 1, 1, 2},         /* tail half: 4U em083 group 1 */
};

static void *s_dtp;    /* the object the records went into (one shared resource) */

void dala_break_install(void *self)
{
    uint8_t *obj = FIELD(uint8_t *, self, EN_DTBPARTS);
    if (!obj || obj == s_dtp) return;
    s_dtp = obj;
    uint8_t *old = FIELD(uint8_t *, obj, DTP_RECORDS);
    uint32_t n = obj[DTP_COUNT], same = (n == N_BREAKS && old);
    for (uint32_t i = 0; same && i < 4 * N_BREAKS; i++) same = old[i] == k_breaks[i / 4][i % 4];
    if (same) return;
    uint8_t *mem = gu_new(4 * N_BREAKS);
    if (!mem) { logf("dalaport: break records: alloc failed"); return; }
    for (uint32_t i = 0; i < 4 * N_BREAKS; i++) mem[i] = k_breaks[i / 4][i % 4];
    FIELD(uint8_t *, obj, DTP_RECORDS) = mem;
    obj[DTP_COUNT] = N_BREAKS;
    logf("dalaport: break records: dtbparts %x had %u (first part %u group %d), now %u", (uint32_t)obj, n,
         n && old ? old[0] : 0, n && old ? (int8_t)old[3] : 0, N_BREAKS);
    if (old) gu_delete(old);
}

/* test log: break counts of parts 0..7 and the reward flags whenever they change (both halves) */
void dala_break_log(void *self, uint32_t tail)
{
    static uint32_t s_last[2] = {0xffffffffu, 0xffffffffu}, s_n;
    uint8_t *rec = REC(self);
    uint32_t sig = rec[0x5cbe];
    for (uint32_t p = 0; p < 8; p++) sig = sig * 31u + rec[0x3bc + 12 * p];
    if (sig == s_last[tail] || ++s_n > 60) return;
    s_last[tail] = sig;
    logf("dalaport: %s breaks %u %u %u %u %u %u %u %u flags %x", tail ? "tail" : "head", rec[0x3bc], rec[0x3bc + 12],
         rec[0x3bc + 24], rec[0x3bc + 36], rec[0x3bc + 48], rec[0x3bc + 60], rec[0x3bc + 72], rec[0x3bc + 84],
         (uint32_t)rec[0x5cbe]);
}
