/* em007_01_diag.c: Monoblos diagnostics (logs, prefix "mbport:").
 *
 * Hook 0xd35e58 = uEm007_00 vtable slot 125, the action dispatcher (= 4U uEm099 slot 44 0x8d41b8, every frame; the
 * death action 12/255 runs in the framework, not here; its first two instructions push / mov: displaceable). Since
 * 0.4.0 his own 4U AI table runs him (tools/build_em007_01_arc.py cmdtbl): GU's Diablos handlers for his twin actions,
 * his ported 4U handlers (em007_01_moves.c) for the rest, which show here as numbers 208 + his 4U number. The log
 * shows which actions he takes and which motions play: his own 4U animations show as motions 0x404 / 0x40e (GU bank 0
 * slots 4 / 14 = his roar and idle, ours) and 0x4xx (bank 4 = 4U em101_4, manifest field 8).
 * For the first Diablos variant 1 (ID 0x107) of each quest it logs each new action (category / number, enemy +0x73e0 /
 * +0x73e1, the AI script that asked for it) and each new motion (curMotion, bank << 8 | index), and the frame his HP
 * reaches 0. The hook returns em007_01_moves_run's answer: 1 = his port ran (GU's dispatch skipped). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */
#define EN_AREA    0x1054           /* u8 current area */
#define MAX_LINES  3000u            /* a few minutes of fight */
#define EN_SCRIPT  0x72fc           /* u8 group, u8 script of the running AI script */

int em007_01_moves_run(void *self);                         /* em007_01_moves.c: his ported 4U actions */

static void diag(void *self);

int em007_01_act_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != MONOBLOS_EM_ID) return 0;
    diag(self);
    return em007_01_moves_run(self);                       /* 1: his port ran, GU's dispatch is skipped */
}

static void diag(void *self)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines, s_quest;
    if (port_quest_id() != s_quest) {                      /* each quest logs its first Monoblos */
        s_quest = port_quest_id();
        s_self = 0;
        s_lines = 0;
    }
#ifdef MB_TEST_HP_PCT
    {   /* test builds (GOG_DEFINES=MB_TEST_HP_PCT=n): each Monoblos starts at n % of his max HP once (short kill and
         * capture tests, as Black Gravios' BG_TEST_HP_PCT) */
        static void *s_hp_set;
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, r, REC_HP), mx = FIELD(int32_t, r, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, r, REC_HP) = mx * MB_TEST_HP_PCT / 100;
            logf("mbport: em007_01 test HP %d / %d", mx * MB_TEST_HP_PCT / 100, mx);
        }
    }
#endif
    if (s_lines >= MAX_LINES) return;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!s_self) {
        s_self = self;
        s_act = s_mot = ~0u;
        s_lines++;
        logf("mbport: em007_01 %x first dispatch, variant %u, index %u, quest %u, hp %d", (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6), s_quest, FIELD(int32_t, rec, REC_HP + 4));
    }
    if (self != s_self) return;                            /* the first instance only */
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    {   /* the death action runs in the framework, not here: log the frame his HP reaches 0 */
        static void *s_dead;
        if (s_dead != self && FIELD(int32_t, rec, REC_HP) <= 0) {
            s_dead = self;
            s_lines++;
            logf("mbport: em007_01 HP 0 in action %u/%u (motion %x) area %u", act >> 8, act & 0xff, mot,
                 FIELD(uint8_t, self, EN_AREA));
        }
    }
    {   /* the sonic bomb's conditions (em007_01_moves.c sonic_check): rage changes, and every shell hit while burrowed
         * or of a sonic type, so that a test log shows why he did or did not react */
        static uint32_t s_rage = ~0u, s_hits;
        uint32_t t = rec[0x484] - 33u;
        if (rec[0x518] != s_rage) {
            s_rage = rec[0x518];
            s_lines++;
            logf("mbport: em007_01 rage state %u (action %u/%u)", s_rage, act >> 8, act & 0xff);
        }
        if (rec[0x444] && s_hits < 60 && (rec[0x1ba] == 4 || (t <= 14 && ((0x7ff1u >> t) & 1)))) {
            s_hits++;
            s_lines++;
            logf("mbport: em007_01 hit type %u: target mode %u rage %u area move %u data flag %u action %u/%u",
                 rec[0x484], rec[0x1ba], rec[0x518], FIELD(uint8_t, self, 0x73f0), rec[0x3a8] & 16, act >> 8, act & 0xff);
        }
    }
    if (act != s_act) {
        int32_t hp = FIELD(int32_t, rec, REC_HP), mx = FIELD(int32_t, rec, REC_HP + 4);
        s_lines++;
        logf("mbport: em007_01 action %u/%u (motion %x) area %u mode %x tm %u rage %u hp %d%% script g%u s%u", act >> 8,
             act & 0xff, mot, FIELD(uint8_t, self, EN_AREA), rec[0x1bb], rec[0x1ba], rec[0x518],
             mx > 0 ? hp * 100 / mx : 0, FIELD(uint8_t, self, EN_SCRIPT), FIELD(uint8_t, self, EN_SCRIPT + 1));
        if (act == (10u << 8 | 92)) {
            s_lines++;
            logf("mbport: em007_01 sonic reaction, count work+0xa = %u (GU adds 1 at its start)",
                 FIELD(uint8_t *, self, EN_WORK)[0xa]);
        }
    } else if (mot != s_mot) {
        s_lines++;
        logf("mbport: em007_01 motion %x (action %u/%u)", mot, act >> 8, act & 0xff);
    }
    s_act = act;
    s_mot = mot;
}
