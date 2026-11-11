/* em070_01.c: Shrouded Nerscylla (GU Nerscylla variant 1, GU's class uEm070_00 runs her; notes/plan.md). GU dropped 4U uEm027's tests of her: the class reads its variant byte in one place only (below), while 4U tests em 27 / 96 in 40 places
 * (C, the list and what each one needs: notes/plan.md "Species tests"). Her moves come from her AI table and GU's handlers, her shots are data (tools/build_em070_01_arc.py shell_data). This file holds what is left (C unless marked, 4U addresses read 2026-11-06):
 *  - her bite rows: 4U 13/1 13/2 13/3 2/33 2/35 2/36 2/43 2/46 2/47 7/10 7/11 (0x79c6a4 0x79c8d8 0x79cc44 0x79e5b4 0x79eaa8): em 27 attacks with (slot 0, index 23); she with (0, 44) and (1, 45), or (1, 46) once her poison spike is gone (W+0x42c bit 0x2000, set by slot
 *    64 0x7a79dc when part 1 has broken 3 times: GU's twin is rec+0x3b5 bit 5, read by GU's own 7/60 at 0xfab7e0). GU's handlers all post 23: GU's attackEx 0x7dc2c turns that into hers (site em057_01_atk: Stygian's handler calls this one first, a site has one hook).
 *    Index 23 appears nowhere else in GU's class (C, every 0x7dc2c / 0x7df94 call read).
 *  - GU's sound of her web line: 0xf9f2ec (slot 130, every frame) starts a sound by the state in work+0xb5, for variant 0 only (0xf9f3ec); GU's only variant test in this class, and with it she is silent there. Between two mid hooks she counts as variant 0, the Tidal Najarala way
 *    (em068_01_blast_c); the code between is straight-line reads and a motion check.
 * Multiplayer: GU's handlers run on every machine, the inputs are the action and her part counters, which GU keeps. All addresses go through MAIN / FN; no fixed ranges.
 * Logs: prefix "snport:". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */
#define EN_AREA    0x1054           /* u8 current area */
#define EN_SCRIPT  0x72fc           /* u8 group, u8 script of the running AI script */
#define MAX_LINES  3000u            /* a few minutes of fight */
#define IS_HER(p)  ((p) && FIELD(uint16_t, (p), EN_ID) == SHROUDED_NERSCYLLA_EM_ID)
#define RAGE_ON(p) (FN(int (*)(void *), 0x8172c)(p))        /* [4U 0x954e48] */

#define ATK_PLAIN  23u              /* GU's bite row, 4U's for em 27 */
#define ATK_BITE   44u              /* 4U 0x79c824 */
#define ATK_SPIKE  45u              /* slot 1, the record with her status (notes/plan.md): 4U 0x79c884 */
#define ATK_NO_SPIKE 46u            /* slot 1, the spike gone: 4U 0x79c84c */
#define REC_PARTBITS 0x3b5          /* GU's byte of 4U's W+0x42d: bit 5 = 4U 0x2000 (0xfab7e0) */
typedef void (*attack_ex_t)(void *self, uint32_t slot, uint32_t index, uint32_t mode);
#define attackExGu FN(attack_ex_t, 0x7dc2c)

/* from em057_01_atk_c (the one hook of attackEx 0x7dc2c(self, slot, index, mode)): her row for GU's 23 and the second row 4U adds. The nested call comes back here with slot 1, which passes */
void em070_01_atk(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R0];
    uint8_t *rec;
    uint32_t spike;
    if (!IS_HER(self) || regs[R1] != 0 || regs[R2] != ATK_PLAIN) return;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    spike = rec && (rec[REC_PARTBITS] & 32) ? ATK_NO_SPIKE : ATK_SPIKE;
    regs[R2] = ATK_BITE;
    attackExGu(self, 1, spike, regs[R3]);
    if (++s_n <= 60) logf("snport: bite rows 0 %u, 1 %u (action %u/%u)", ATK_BITE, spike, FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
}

/* 0xf9f3ec (movw r0, #0xb5f5; ldrb r0, [r4, r0]), r4 = monster, and 0xf9f534 (ldr r2, [r4, #0x498]; ldrb r3, [sp, #0x72]), where both paths meet. Mid hooks: always 0 */
static void *s_line_owner;

int em070_01_line_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R4];
    if (IS_HER(self) && FIELD(uint8_t, self, EN_VARIANT) == 1) {
        FIELD(uint8_t, self, EN_VARIANT) = 0;
        s_line_owner = self;
        if (++s_n <= 24) logf("snport: web line sound state %u (action %u/%u)", FIELD(uint8_t, FIELD(uint8_t *, self, EN_WORK), 0xb5), FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
    }
    return 0;
}

int em070_01_line2_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (self && self == s_line_owner) {
        FIELD(uint8_t, self, EN_VARIANT) = 1;
        s_line_owner = 0;
    }
    return 0;
}

/* her part counters (rec+0x3bc + 12 * part, GU 0x9d428): slot 132 shows a part as broken when its counter reaches its value (C: 0xf9ee88 parts 1, 2, 4). Log only: a line at each change, so that a test log shows the breaks, with the spike bit */
static void part_watch(void *self)
{
    static void *s_self;
    static uint8_t s_count[8];
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return;
    if (s_self != self) {
        s_self = self;
        for (int p = 0; p < 8; p++) s_count[p] = rec[0x3bc + 12 * p];
        return;
    }
    for (int p = 0; p < 8; p++) {
        uint8_t c = rec[0x3bc + 12 * p];
        if (c == s_count[p]) continue;
        s_count[p] = c;
        logf("snport: part %d count %u, bits %x (action %u/%u, area %u)", p, c, rec[REC_PARTBITS], FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint8_t, self, EN_AREA));
    }
}

/* Her travel under the ground (3/37, 3/39) shows nothing, as in 4U (C: 4U 0x915da0 posts no effect, motion 1 has no events). 0.1.1..0.1.8 played GU Diablos' trail there (his
 * element 1400; seen once the arc order was right, 0.1.7); the user, 2026-11-08: "Gar nichts, wie 4U". Removed in 0.1.9 (notes/plan.md "History" has the readings). */
#define N_UNITS 4                                /* one diag state per unit of hers (quest 11371 runs two at once, log 2026-11-08 12-33-26) */

static int unit_gone(void *u) { return !u || !FIELD(uint32_t, u, EN_ID); }

static void diag(void *self)
{
    static struct { void *self; uint32_t act, mot; } s_u[N_UNITS];    /* 0.1.7: per unit (11371 runs two at once; one shared state logged both every frame) */
    static uint32_t s_lines, s_quest;
    if (port_quest_id() != s_quest) {                      /* each quest logs its own lines */
        s_quest = port_quest_id();
        for (int i = 0; i < N_UNITS; i++) s_u[i].self = 0;
        s_lines = 0;
    }
#ifdef SN_TEST_HP_PCT
    {   /* test builds (GOG_DEFINES=SN_TEST_HP_PCT=n): she starts at n % of her max HP once (short kill / capture tests) */
        static void *s_hp_set;
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, r, REC_HP), mx = FIELD(int32_t, r, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, r, REC_HP) = mx * SN_TEST_HP_PCT / 100;
        }
    }
#endif
    if (s_lines >= MAX_LINES) return;
    __typeof__(&s_u[0]) u = 0;
    for (int i = 0; i < N_UNITS && !u; i++) if (s_u[i].self == self) u = &s_u[i];
    if (!u) {                                              /* a new unit of hers: a free or gone slot */
        for (int i = 0; i < N_UNITS && !u; i++) if (unit_gone(s_u[i].self)) u = &s_u[i];
        if (!u) u = &s_u[0];
        u->self = self;
        u->act = u->mot = ~0u;
        s_lines++;
        logf("snport: em070_01 %u = %x first dispatch, variant %u, index %u, quest %u", (uint32_t)(u - s_u), (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6), port_quest_id());
    }
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    if (act != u->act) {
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t mx = r ? FIELD(int32_t, r, REC_HP + 4) : 0;
        s_lines++;
        logf("snport: em070_01 %u action %u/%u (motion %x) area %u script %u/%u hp %d%% rage %u", (uint32_t)(u - s_u), act >> 8, act & 0xff, mot,
             FIELD(uint8_t, self, EN_AREA), FIELD(uint8_t, self, EN_SCRIPT), FIELD(uint8_t, self, EN_SCRIPT + 1),
             mx > 0 ? FIELD(int32_t, r, REC_HP) * 100 / mx : -1, (uint32_t)RAGE_ON(self));
    } else if (mot != u->mot) {
        s_lines++;
        logf("snport: em070_01 %u motion %x (action %u/%u)", (uint32_t)(u - s_u), mot, act >> 8, act & 0xff);
    }
    u->act = act;
    u->mot = mot;
}

/* 0xfae550 = slot 125 (action dispatcher, every frame): the log */
int em070_01_act_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!IS_HER(self)) return 0;
    diag(self);
    part_watch(self);
    return 0;
}
