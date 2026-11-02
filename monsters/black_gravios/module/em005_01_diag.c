/* em005_01_diag.c: Black Gravios diagnostics (logs, prefix "bgport:").
 *
 * Hook 0xd31128 = uEm004_00 vtable slot 125, the action dispatcher (= 4U uEm038 slot 44 0x807e5c, every frame; the
 * death action 12/255 runs in the framework, not here). For the first Gravios variant 1 (ID 0x105) of each quest, it
 * logs each new action (category / number, enemy +0x73e0 / +0x73e1)
 * and each new motion (curMotion, bank << 8 | index). His AI table is 4U em040_cmd for em 41 (notes/plan.md "His AI"),
 * so a test shows his own picks: 7/71 (his 7/57), 7/79 / 7/80 and the actions of his selectors g0 s17 s18 s20, which
 * GU's Gravios table never asks for; 7/75 7/76 7/82..7/85 would show that something picks g1 s59 (plan.md). The first
 * line also logs the record GU 0x9cf7c takes 1/18's stamina cost from ([this+0x75f0]+196; 4U: 20 for em 41, 30 for
 * em 40, plan.md), whose resource is not identified. Logs only: GU's dispatch always runs (return 0). */
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
#define EN_COSTREC 0x75f0           /* record pointer: 1/18 stamina cost float at +196, a factor at +200 (GU 0x9cf7c) */

void em005_01_laser_tick(void *self);       /* the 7/57 laser's 4U effect (em005_01_laser.c) */
void em005_01_laser_reset(void);

int em005_01_act_c(uint32_t *regs)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines, s_quest;
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != BLACK_GRAVIOS_EM_ID) return 0;
    if (port_quest_id() != s_quest) {                      /* each quest logs its first Black Gravios (test 1 logged
                                                              the first quest only) */
        s_quest = port_quest_id();
        s_self = 0;
        s_lines = 0;
        em005_01_laser_reset();
    }
    em005_01_laser_tick(self);
#ifdef BG_TEST_HP_PCT
    {   /* test builds (GOG_DEFINES=BG_TEST_HP_PCT=n): each Black Gravios starts at n % of his max HP once, so a kill
         * test is short (as Stygian's TEST_HP_PCT) */
        static void *s_hp_set;
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, r, REC_HP), mx = FIELD(int32_t, r, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, r, REC_HP) = mx * BG_TEST_HP_PCT / 100;
            logf("bgport: em005_01 test HP %d / %d", mx * BG_TEST_HP_PCT / 100, mx);
        }
    }
#endif
    if (s_lines >= MAX_LINES) return 0;
    if (!s_self) {
        s_self = self;
        s_act = s_mot = ~0u;
        s_lines++;
        logf("bgport: em005_01 %x first dispatch, variant %u, index %u, quest %u", (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6), s_quest);
        const uint8_t *cr = FIELD(const uint8_t *, self, EN_COSTREC);
        if (cr)
            logf("bgport: em005_01 stamina cost record %x: +196 %d, +200 %d (x1000)", (uint32_t)(uintptr_t)cr,
                 (int)(FIELD(float, cr, 196) * 1000.0f), (int)(FIELD(float, cr, 200) * 1000.0f));
    }
    if (self != s_self) return 0;                          /* the first instance only (two in quest 1025) */
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    {   /* the death action runs in the framework, not here: log the frame his HP reaches 0 */
        static void *s_dead;
        if (s_dead != self && FIELD(int32_t, rec, REC_HP) <= 0) {
            s_dead = self;
            s_lines++;
            logf("bgport: em005_01 HP 0 in action %u/%u (motion %x) area %u", act >> 8, act & 0xff, mot,
                 FIELD(uint8_t, self, EN_AREA));
        }
    }
    if (act != s_act) {
        int32_t hp = FIELD(int32_t, rec, REC_HP), mx = FIELD(int32_t, rec, REC_HP + 4);
        s_lines++;
        /* EN_SCRIPT: the AI's current (group, script) pair (GU think 0x829e0 reads groups[g][i] from them; 0x7340 /
         * 0x7350 hold the call stack), i.e. the script that asked for this action (S) */
        logf("bgport: em005_01 action %u/%u (motion %x) area %u mode %x hp %d%% script g%u s%u", act >> 8, act & 0xff,
             mot, FIELD(uint8_t, self, EN_AREA), rec[0x1bb], mx > 0 ? hp * 100 / mx : 0, FIELD(uint8_t, self, EN_SCRIPT),
             FIELD(uint8_t, self, EN_SCRIPT + 1));
    } else if (mot != s_mot) {
        s_lines++;
        logf("bgport: em005_01 motion %x (action %u/%u)", mot, act >> 8, act & 0xff);
    }
    s_act = act;
    s_mot = mot;
    return 0;
}

/* GU 0x3a7ed8, right after the objective loop of the quest tally 0x3a75c8(quest, id, kind, ..) (r4 = id, r5 = the
 * quest object, kind spilled to the function's [sp+0x3c]): logs his objectives' state. Test 2026-11-01: killing him
 * in the capture quest 10783 cleared it. GU's objective flags come from the type table 0x162a760 (type 1 hunt 0x1, 2
 * capture 0x81, | 8 at setup 0x3abf98, C); slain (kind 0) with flag 0x80 sets 0x40 and quest+0x5e = 1 (0x3a798c, C),
 * so a slain capture target should fail it; this shows what the loop saw for him.
 * User 2026-11-02: still "killed in the capture quest, not failed". So after the loop GU's own rule is applied once
 * more for him: an objective with the capture flag 0x80 on his ID, tallied with any kind but 1 (captured), not failed
 * yet -> fail flag 0x40 (its done flag 0x20 cleared) and quest+0x5e = 1, as 0x3a798c does, before the completion check
 * 0x3a400c that follows. A no-op when GU's loop already failed it. */
#define OBJ_FLAGS(q, k)  FIELD(uint32_t, q, 0xec + 12 * (k))
#define OBJ_TARGET(q, k) FIELD(uint16_t, q, 0xf0 + 12 * (k))
int em005_01_objlog_c(uint32_t *regs)
{
    static uint32_t s_lines;
    uint8_t *q = (uint8_t *)regs[R5];
    uint32_t kind = FIELD(uint32_t, regs, 32 + 0x3c);
    if (!q) return 0;
    if ((regs[R4] & 0xffff) != BLACK_GRAVIOS_EM_ID) {   /* another ID tallied in one of his quests (stand-in?): log */
        for (int k = 0; k < 3; k++)
            if (OBJ_TARGET(q, k) == BLACK_GRAVIOS_EM_ID && ++s_lines <= 16)
                logf("bgport: tally id %x kind %u in his quest (objective %d flags %x)", regs[R4] & 0xffff, kind, k,
                     OBJ_FLAGS(q, k));
        return 0;
    }
    if (++s_lines <= 16)
        logf("bgport: tally id %x kind %u: objective 0 flags %x target %x n %u, 1 flags %x target %x, 2 flags %x "
             "target %x; quest +0x5e %u +0x5f %u", regs[R4] & 0xffff, kind, OBJ_FLAGS(q, 0), OBJ_TARGET(q, 0),
             FIELD(uint16_t, q, 0xf2), OBJ_FLAGS(q, 1), OBJ_TARGET(q, 1), OBJ_FLAGS(q, 2), OBJ_TARGET(q, 2), q[0x5e],
             q[0x5f]);
    if (kind == 1) return 0;
    for (int k = 0; k < 3; k++) {
        uint32_t f = OBJ_FLAGS(q, k);
        if ((f & 9) != 9 || !(f & 0x80) || (f & 0x40) || OBJ_TARGET(q, k) != BLACK_GRAVIOS_EM_ID) continue;
        OBJ_FLAGS(q, k) = (f | 0x40) & ~0x20u;
        q[0x5e] = 1;
        logf("bgport: capture objective %d: he was slain (kind %u), quest failed as GU's 0x3a798c (flags %x -> %x)", k,
             kind, f, OBJ_FLAGS(q, k));
    }
    return 0;
}
