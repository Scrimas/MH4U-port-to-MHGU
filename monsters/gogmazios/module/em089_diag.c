/* em089_diag.c: Gogmazios damage diagnostics (moved from module/main.c when the core became multi-monster). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

/* diagnostics for "HP never drops" (in-game test 2026-10-17: blood and crits, but rec+0x370 constant). In the enemy
 * damage update (around 0x98a5c): pending damage s16 rec+0x5d66 is subtracted at 0x98afc unless 0x8187c (rec+0x1a8
 * bit 0 / virtual slot 175) diverts to a special path at 0x98ac4. */
int dmg_sub_c(uint32_t *regs)       /* 0x98af4: r0 = pending damage, r1 = record */
{
    static uint32_t s_n;
    if (++s_n <= 30)
        logf("gogport: dmg sub %d hp %d / %d", (int32_t)regs[R0], FIELD(int32_t, regs[R1], 0x370),
             FIELD(int32_t, regs[R1], 0x374));
    return 0;
}

int dmg_special_c(uint32_t *regs)   /* 0x98ac4: 0x8187c returned nonzero, no HP subtraction */
{
    static uint32_t s_n;
    (void)regs;
    if (++s_n <= 5 || s_n % 600 == 0) logf("gogport: dmg special path x%u", s_n);
    return 0;
}

/* 0x9a764 setHP(enemy, value) (clamped to [max * rec+0x380, max]) and 0x9a7b8 addHP(enemy, delta): the
 * 0x5d66 pending-damage path above is poison only; do hit damages arrive here, and with which value? */
int set_hp_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (FIELD(uint16_t, regs[R0], EN_ID) == EM089_ID && ++s_n <= 30)
        logf("gogport: setHP %d (hp %d) lr=%x", (int32_t)regs[R1], FIELD(int32_t, FIELD(uint32_t, regs[R0], 0x1428), 0x370),
             regs[LR] - MAIN_BASE);
    return 0;
}

int add_hp_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (FIELD(uint16_t, regs[R0], EN_ID) == EM089_ID && ++s_n <= 30)
        logf("gogport: addHP %d (hp %d) lr=%x", (int32_t)regs[R1], FIELD(int32_t, FIELD(uint32_t, regs[R0], 0x1428), 0x370),
             regs[LR] - MAIN_BASE);
    return 0;
}

/* 0x9d6f8(monster, part, damage, kind): monster damage receiver (cheats project notes). part >= 8 goes to vt+0x310
 * and adds nothing to HP; parts 0..7 are scaled by rec+0x388 (float) and summed into rec+0x488 + 2 * part. setHP /
 * addHP were never called for em089 although hits show blood and crits (in-game test 2026-10-17). */
int em089_pile_hit_window(void);   /* em089_pile.c: 1 while the pile-hit shell lives */

int dmg_recv_c(uint32_t *regs)
{
    static uint32_t s_n, s_pile;
    if (FIELD(uint16_t, regs[R0], EN_ID) == EM089_ID &&
        (++s_n <= 40 || (em089_pile_hit_window() && ++s_pile <= 40)))   /* the pile's hits: always (diagnostic) */
        logf("gogport: dmg recv part %u damage %d kind %u rate x1000 %d", regs[R1], (int32_t)regs[R2], regs[R3],
             (int32_t)(FIELD(float, FIELD(uint32_t, regs[R0], 0x1428), 0x388) * 1000.0f));
    return 0;
}
