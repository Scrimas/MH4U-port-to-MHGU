/* Battlequarters as a Fortress-typed alias stage (notes/stage.md, plan A).
 *
 * The converted Battlequarters arcs keep the Fortress' INTERNAL paths (stage\m26d\..., relation\m26\...), so every
 * file ID the game computes for stage 26 resolves (by path hash, 0x152960) to our resources. They ship at new RomFS
 * paths (nativeNX/arc/stage/m28d/{m28d,a00..a03}.arc, nativeNX/loc/arc/stage/map_com/m28.arc); the Fortress files
 * stay untouched. The arc path redirect (m28 for m26 while our quest runs), the quest-start KowareObj hold and the
 * map records are the core's (module/stage_alias.c, from allocations.toml stage_alias and package.toml [stage]: kinds
 * 49 / 54 / 55 / 56 / 58, area 2 held, the 4U m19 map records of tools/mapui4u2gu.py); this file keeps the
 * Battlequarters-only parts: the quest test, the gimmick spawner log and the stage-setup serial.
 *
 * Define TEST_STAGE_ALIAS = stage_alias_active() always true (the gimmick hooks; test builds only). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"                /* quest ownership; allocations.toml stage_alias (alloc.h) */

enum { R0, R1, R2, R3, R4, R5, R12, LR, SP0 };   /* SP0 = first stack argument (p2) */

uint32_t gog_quest_id(void) { return port_quest_id(); }

/* 1 = quest 11491 (4U m11014), 2 = quest 11492 (4U m11035) while Gogmazios is installed, 0 = another quest or none */
int gog_quest_index(void)
{
    int which, m = port_running_quest(&which);
    return m == GOGMAZIOS_PORT ? which + 1 : 0;
}

int stage_alias_active(void)
{
#ifdef TEST_STAGE_ALIAS
    return 1;
#elif !defined(NO_GOG_STAGE_ALIAS)
    /* on by default since 2026-10-21: the quests are built for the alias (build_gog_quest.py --bq, its default), so
     * a build without it sent them to the plain Fortress (test 2026-10-21). GOG_STAGE_ALIAS is still accepted. */
    return gog_quest_index() != 0;
#else
    /* NO_GOG_STAGE_ALIAS: for quests built with --legacy / --siege / --plain (Fortress data) */
    return 0;
#endif
}

/* 0x50249c(this): stage gimmick spawner, run at stage setup (notes/stage.md section 11). Per-stage flag word
 * u16[stage] at 0x162bd60 (stage 26 = 0x3ec): bit 4 -> st003 Dragonator spears (Fortress: 4, positions = st003 FUP
 * vec 3..6), bits 0x88 -> one st004 ballista per SIS point kind 3 / one st008 per kind 6, 0x20 -> st006 cart x2,
 * 0x40 -> st007 gate. For the alias the shells run on OUR map_com data (m28.arc: 4U ballista points, spears moved
 * under 4U's Dragonator switch, cart parked at 4U's station). Log only. */
#define STAGE_GIMMICK_FLAGS 0x162bd60u
#define STAGE_BYTE_PTR      0x188ca48u   /* [[0x188ca48]+0x48] = current stage, +0x49 = area (sStage) */

/* Stage-setup serial: bumped every time the spawner runs (0x4feb40 stage setup, called once per stage load from
 * 0x4fe394) -> module gimmick drivers (stage_cart.c, stage_cannon.c, stage_doors.c) reset their static state when it
 * changes, also when a new quest's objects land at the old addresses. */
static uint32_t s_setup_serial;
uint32_t stage_setup_serial(void) { return s_setup_serial; }

int stage_gimmicks_c(uint32_t *regs)
{
    static uint32_t s_n;
    s_setup_serial++;
    void *st = *(void **)MAIN(STAGE_BYTE_PTR);
    uint32_t stage = st ? FIELD(uint8_t, st, 0x48) : 0xff;
    if (stage < 28 && ++s_n <= 8)
        logf("gogport: stage gimmicks: spawner this=%x stage %u flags %x alias %u (quest %u) mode %u", regs[R0], stage,
             *(volatile uint16_t *)MAIN(STAGE_GIMMICK_FLAGS + 2 * stage), stage_alias_active(), gog_quest_id(),
             FIELD(uint32_t, st, 0x1c));   /* sStage+0x1c 3 / 6: uStageSet camera checks need mControlFlag bit 3 */
    return 0;
}

/* the quests themselves (board slots, unlock, clear write) are core: module/quest.c */
