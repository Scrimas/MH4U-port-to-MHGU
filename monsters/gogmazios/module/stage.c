/* Battlequarters as a Fortress-typed alias stage (notes/stage.md, plan A).
 *
 * The converted Battlequarters arcs keep the Fortress' INTERNAL paths (stage\m26d\..., relation\m26\...), so every
 * file ID the game computes for stage 26 resolves (by path hash, 0x152960) to our resources. They ship at new RomFS
 * paths (nativeNX/arc/stage/m28d/{m28d,a00..a03}.arc, nativeNX/loc/arc/stage/map_com/m28.arc); the Fortress files
 * stay untouched. The only runtime change: while our quest is active, the arc path builder writes m28 for m26.
 *
 * Hook: 0x15339c(_, String *out, kind, p1, [sp] p2) -> bool, the arc path builder of the resource-request list
 * (caller 0x1529a8(mgr, kind, p1, p2, owner); records keyed by (kind, p1, p2, owner), released by key at 0x152ef8,
 * so the key stays (kind, 26, ...) and only the path string changes). Stage kinds, p1 = stage, p2 = area:
 *   49 "stage\mapUI\m%02dd\a%02d_ui_%s"  54 "stage\map_com\m%02d"     55 "stage\map_com\m%02d_%s"
 *   56 "stage\m%02dd\m%02dd"             57 "stage\m%02dn\m%02dn"     58 "stage\m%02dd\a%02d"   59 "stage\m%02dn\a%02d"
 * Stage requests come from 0x50373c (stage = byte [[0x188ca48]+0x48], set at 0x6c0380 from the quest record of
 * quest ID [[0x188ae38]+0xd68]; release 0x503854).
 *
 * Defines: TEST_STAGE_ALIAS = alias EVERY Fortress load (test builds only);
 *          STAGE_ALIAS_UI (default on, -DNO_STAGE_ALIAS_UI = off) = also redirect the mapUI arcs (kind 49, built by
 *          tools/mapui4u2gu.py) and swap the per-area map records (stage_maprec); STAGE_ALIAS_WHOLEMAP (default on,
 *          -DNO_STAGE_ALIAS_WHOLEMAP = off) = also the language map_com (kind 55, whole map, m28_<lang>.arc built by
 *          tools/mapui4u2gu.py) and the whole-map record scale (stage_wholerec). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"                /* quest ownership; allocations.toml stage_alias (alloc.h) */

enum { R0, R1, R2, R3, R4, R5, R12, LR, SP0 };   /* SP0 = first stack argument (p2) */

#define STAGE_FORTRESS  GOGMAZIOS_STAGE_FROM
#define STAGE_ALIAS     GOGMAZIOS_STAGE_FOLDER   /* folder number of our files: m28d, map_com\m28 */
#if !defined(NO_STAGE_ALIAS_UI) && !defined(STAGE_ALIAS_UI)
#define STAGE_ALIAS_UI
#endif
#if !defined(NO_STAGE_ALIAS_WHOLEMAP) && !defined(STAGE_ALIAS_WHOLEMAP)
#define STAGE_ALIAS_WHOLEMAP
#endif

/* Quest IDs (module/port.c port_quest_id, static trace in notes/stage.md section 9): [[0x188ae38]+0xd68] = the
 * ACCEPTED quest until the setup 0x3ade34 clears it, then [[0x188ad90]+0xe0] = the RUNNING quest until quest end.
 * Both are logged by the stage path hook. */
#define QUESTSEL_PTR    0x188ae38u
#define QUESTSEL_ID     0xd68u
#define QUESTRUN_PTR    0x188ad90u
#define QUESTRUN_ID     0xe0u

static uint32_t quest_id(uint32_t ptr_word, uint32_t field)
{
    void *q = *(void **)MAIN(ptr_word);
    return q ? FIELD(uint32_t, q, field) : 0;
}

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

static int alias_kind(uint32_t kind)
{
    switch (kind) {
    case 54: case 56: case 58:   /* loc map_com (collision, SIS, cameras, nav, tables), stage + area geometry */
        return 1;
#ifdef STAGE_ALIAS_UI
    case 49:                     /* mapUI per area: <lang>/arc/stage/mapUI/m28d/a0N_ui_<lang>.arc */
        return 1;
#endif
#ifdef STAGE_ALIAS_WHOLEMAP
    case 55:                     /* language map_com (whole map): <lang>/arc/stage/map_com/m28_<lang>.arc */
        return 1;
#endif
    default:                     /* 57 / 59 night: the Fortress has no night version */
        return 0;
    }
}

/* 0x15339c(_, out, kind, stage, [sp] area): arc path builder */
int stage_path_c(uint32_t *regs)
{
    uint32_t kind = regs[R2];
    static uint32_t s_calls;
    if ((alias_kind(kind) || regs[R3] == STAGE_FORTRESS) && ++s_calls <= 200)   /* diagnostic: quest fails at once */
        logf("gogport: path req kind %u stage %u area %u alias %u (quest %u / %u)", kind, regs[R3], regs[SP0],
             stage_alias_active(), quest_id(QUESTSEL_PTR, QUESTSEL_ID), quest_id(QUESTRUN_PTR, QUESTRUN_ID));
    if (regs[R3] != STAGE_FORTRESS || !alias_kind(kind) || !stage_alias_active()) return 0;
    regs[R3] = STAGE_ALIAS;
    logf("gogport: stage path kind %u area %u -> m%u (quest %u / %u)", kind, regs[SP0], STAGE_ALIAS,
         quest_id(QUESTSEL_PTR, QUESTSEL_ID), quest_id(QUESTRUN_PTR, QUESTRUN_ID));
    return 0;
}

/* Area map placement (notes/port-checklist.md "Arena 4", Map UI; tools/mapui4u2gu.py). cUIOEnlargeMap setup 0x61c318
 * (this = r4, stage +0x94, area +0x98) loads r0 = table[stage][area] (0x1774dec, 14 pointers per stage) and stores it
 * at this+0x15c (site 0x61c394). Record (0x34 B, .rodata): +0..+0x10 GUI file IDs per language (0x61c288), +0x1c /
 * +0x24 / +0x28 GUI object ids, +0x2c f32 k, +0x30 / +0x32 s16 offset; icons 0x61cacc: map = world x / z *
 * (k * 128 / 10000) + 2 * offset, HD px from the map texture centre (scale stored at 0x61c5f4). Same formula as 4U
 * (0x5a5f14 + 0xb82e38: u = off + (x * k + 10000) / 20000 * 128), so the alias record = the Fortress copy with 4U m19's
 * k / offset (4U table 0xeebe0c + 0x18 * 19 -> 0xeebb10; alias areas 0, 1, 2 = 4U a00, a01, a03) over the 2x 4U map
 * picture of our mapUI arcs. C */
#ifdef STAGE_ALIAS_UI
#define MAPREC_SIZE 0x34u
static const struct { float k; int16_t x, y; } MAPREC[3] = {   /* keep in sync with tools/mapui4u2gu.py MAPREC */
    { 1.8f, 17, 11 }, { 2.0f, 0, -8 }, { 1.1f, 0, -1 },
};
static uint32_t s_maprec[3][MAPREC_SIZE / 4];

int stage_maprec_c(uint32_t *regs)
{
    uint32_t stage = FIELD(uint32_t, regs[R4], 0x94), area = FIELD(uint32_t, regs[R4], 0x98), i;
    const uint32_t *src = (const uint32_t *)(uintptr_t)regs[R0];
    if (stage != STAGE_FORTRESS || area >= 3 || !src || !stage_alias_active()) return 0;
    for (i = 0; i < MAPREC_SIZE / 4; i++) s_maprec[area][i] = src[i];
    FIELD(float, s_maprec[area], 0x2c) = MAPREC[area].k;
    FIELD(int16_t, s_maprec[area], 0x30) = MAPREC[area].x;
    FIELD(int16_t, s_maprec[area], 0x32) = MAPREC[area].y;
    regs[R0] = (uint32_t)(uintptr_t)s_maprec[area];
    logf("gogport: area map record area %u -> k %d/10 off (%d, %d)", area, (int)(MAPREC[area].k * 10.0f + 0.5f),
         MAPREC[area].x, MAPREC[area].y);
    return 0;
}
#else
int stage_maprec_c(uint32_t *regs) { (void)regs; return 0; }
#endif

/* Whole map placement (tools/stage4u2gu.py "whole-map area offsets", tools/mapui4u2gu.py wholemap). cUIOEnlargeMap
 * setup 0x61b5ac (this = r4, stage +0x94) loads the whole-map record r0 = table[stage] (0x1774cf0; 0x1774d60 when
 * 0x55df28 < 3; r0 = 0 for stage > 27) and stores it at this+0xe0 (site 0x61b608). Record (0x44 B, .rodata): +0..+0x10
 * GUI file IDs per language, +0x34 / +0x38 f32 k, +0x3c / +0x40 f32 offset; icons 0x61bde8: map = (world + area offset
 * of m28.arc stage\m26d\m26d) * 256 * k / dims[stage].w + 2 * offset, HD px from the texture centre (dims[26] = 60000,
 * 0x5058d0; scale stored at 0x61b964). 4U m19: u = (world + offset + 20000) / 40000 * 128 (0xb832ac, W from 0x6596dc)
 * -> k = 60000 / 40000 with 4U's offsets over the 2x 4U picture: map = 2 * (4U u - 64). C */
#ifdef STAGE_ALIAS_WHOLEMAP
#define WHOLEREC_SIZE 0x44u
#define WHOLEREC_K    1.5f       /* 60000 / 40000: keep in sync with tools/mapui4u2gu.py WMAP_K */
static uint32_t s_wholerec[WHOLEREC_SIZE / 4];

int stage_wholerec_c(uint32_t *regs)
{
    const uint32_t *src = (const uint32_t *)(uintptr_t)regs[R0];
    uint32_t i;
    if (FIELD(uint32_t, regs[R4], 0x94) != STAGE_FORTRESS || !src || !stage_alias_active()) return 0;
    for (i = 0; i < WHOLEREC_SIZE / 4; i++) s_wholerec[i] = src[i];
    FIELD(float, s_wholerec, 0x34) = WHOLEREC_K;
    FIELD(float, s_wholerec, 0x38) = WHOLEREC_K;
    FIELD(float, s_wholerec, 0x3c) = 0.0f;
    FIELD(float, s_wholerec, 0x40) = 0.0f;
    regs[R0] = (uint32_t)(uintptr_t)s_wholerec;
    logf("gogport: whole map record -> k %d/10", (int)(WHOLEREC_K * 10.0f + 0.5f));
    return 0;
}
#else
int stage_wholerec_c(uint32_t *regs) { (void)regs; return 0; }
#endif

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
