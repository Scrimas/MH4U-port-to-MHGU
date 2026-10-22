/* Stage aliases (core): a ported arena as an alias of a GU stage (monsters/gogmazios/notes/stage.md "Alias design",
 * monsters/dalamadur/notes/speartip-crag.md section 6).
 *
 * A package's converted stage arcs keep the GU stage's INTERNAL paths (stage\m26d\..., stage\m18d\...), so every file
 * ID the game computes for that stage resolves (by path hash, 0x152960) to them; they ship at new RomFS paths (folder
 * m<NN>, allocations.toml stage_alias = [GU stage, folder]) and the GU stage's own files stay untouched. While a quest
 * of that monster runs, the arc path builder writes the folder number for the GU stage number (stage_path_c) for the
 * kinds the package lists (package.toml [stage] kinds), and GU's quest-start KowareObj command 0 is held for the
 * areas it lists (hold_kobj_areas: 4U stages start with their breakables intact, GU opens every one).
 *
 * Hook stage_path @0x15339c(_, String *out, kind, p1 = stage, [sp] p2 = area) -> bool, the arc path builder of the
 * resource-request list (caller 0x1529a8(mgr, kind, p1, p2, owner); records keyed by (kind, p1, p2, owner), released by
 * key at 0x152ef8, so the key keeps the GU stage and only the path string changes). Stage kinds, p1 = stage:
 *   49 "stage\mapUI\m%02dd\a%02d_ui_%s"  54 "stage\map_com\m%02d"     55 "stage\map_com\m%02d_%s"
 *   56 "stage\m%02dd\m%02dd"             57 "stage\m%02dn\m%02dn"     58 "stage\m%02dd\a%02d"   59 "stage\m%02dn\a%02d"
 * Stage requests come from 0x50373c (stage = byte [[0x188ca48]+0x48], set at 0x6c0380 from the quest record of the
 * accepted quest; release 0x503854), so "the alias stage and our quest" go together by construction.
 * Hook stage_kobj_bcast @0x500d18 (inside 0x500cb4, r0 = kobj): GU's quest start (0x42e8 -> 0x500cb4, host, non-siege)
 * sends command 0 to EVERY kobj; for a held area it becomes command 1 (no case in 0x514f9c: returns).
 * Hooks stage_maprec / stage_wholerec: the map records of the converted mapUI / whole-map arcs (kinds 49 / 55; see
 * there and monsters/gogmazios/notes/port-checklist.md "Arena 4", Map UI). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR, SP0 };   /* SP0 = first stack argument (p2) */

#define KOBJ_AREA 0x182u                         /* uKowareObj u8 mAreaNo (0x516b34) */
#define KOBJ_ID   0x188u                         /* u8 mId */

/* the running quest's monster when it has a stage alias, else -1 */
static int alias_port(void)
{
    int m = port_running_quest(0);
    return m >= 0 && port_monsters[m].stage_folder ? m : -1;
}

int stage_path_c(uint32_t *regs)
{
    uint32_t kind = regs[R2];
    int m = alias_port();
    if (m < 0 || regs[R3] != port_monsters[m].stage_from || kind < 48 || kind >= 80 ||
        !(port_monsters[m].stage_kinds >> (kind - 48) & 1)) return 0;
    regs[R3] = port_monsters[m].stage_folder;
    logf("port: %s stage path kind %u area %u -> m%u (quest %u)", port_monsters[m].name, kind, regs[SP0],
         regs[R3], port_quest_id());
    return 0;
}

int stage_kobj_bcast_c(uint32_t *regs)
{
    static uint32_t s_n;
    uint8_t *k = (uint8_t *)(uintptr_t)regs[R0];
    int m = alias_port();
    if (!k || m < 0 || k[KOBJ_AREA] >= 8 || !(port_monsters[m].stage_hold >> k[KOBJ_AREA] & 1)) return 0;
    regs[R1] = 1;                     /* command 1: no case in 0x514f9c (returns) */
    if (++s_n <= 8) logf("port: %s stage: quest-start command 0 held for area-%u KowareObj %x (mId %u)",
                         port_monsters[m].name, k[KOBJ_AREA], (uint32_t)k, k[KOBJ_ID]);
    return 0;
}

/* Area map placement (tools/mapui4u2gu.py, monsters/dalamadur/tools/build_speartip_ui.py). cUIOEnlargeMap setup
 * 0x61c318 (this = r4, stage +0x94, area +0x98) loads r0 = table[stage][area] (0x1774dec, 14 pointers per stage) and
 * stores it at this+0x15c (site 0x61c394). Record (0x34 B, .rodata): +0..+0x10 GUI file IDs per language (0x61c288),
 * +0x1c / +0x24 / +0x28 GUI object ids, +0x2c f32 k, +0x30 / +0x32 s16 offset; icons 0x61cacc: map = world x / z *
 * (k * 128 / 10000) + 2 * offset, HD px from the map texture centre (scale stored at 0x61c5f4). Same formula as 4U
 * (0x5a5f14 + 0xb82e38: u = off + (x * k + 10000) / 20000 * 128), so the alias record = GU's copy with the 4U stage's
 * k / offset (4U table 0xeebe0c + 0x18 * stage, package.toml [stage] maprec) over the 2x 4U map picture. C */
#define MAPREC_SIZE 0x34u
static uint32_t s_maprec[4][MAPREC_SIZE / 4];

int stage_maprec_c(uint32_t *regs)
{
    uint32_t stage = FIELD(uint32_t, regs[R4], 0x94), area = FIELD(uint32_t, regs[R4], 0x98), i;
    const uint32_t *src = (const uint32_t *)(uintptr_t)regs[R0];
    int m = alias_port();
    if (m < 0 || stage != port_monsters[m].stage_from || area >= port_monsters[m].map_n || !src) return 0;
    for (i = 0; i < MAPREC_SIZE / 4; i++) s_maprec[area][i] = src[i];
    FIELD(float, s_maprec[area], 0x2c) = port_monsters[m].map_k[area];
    FIELD(int16_t, s_maprec[area], 0x30) = port_monsters[m].map_x[area];
    FIELD(int16_t, s_maprec[area], 0x32) = port_monsters[m].map_y[area];
    regs[R0] = (uint32_t)(uintptr_t)s_maprec[area];
    logf("port: %s area map record area %u -> k %d/100 off (%d, %d)", port_monsters[m].name, area,
         (int)(port_monsters[m].map_k[area] * 100.0f + 0.5f), port_monsters[m].map_x[area],
         port_monsters[m].map_y[area]);
    return 0;
}

/* Whole map placement (tools/stage4u2gu.py "whole-map area offsets", tools/mapui4u2gu.py wholemap()). cUIOEnlargeMap
 * setup 0x61b5ac (this = r4, stage +0x94) loads the whole-map record r0 = table[stage] (0x1774cf0; 0x1774d60 when
 * 0x55df28 < 3; r0 = 0 for stage > 27) and stores it at this+0xe0 (site 0x61b608). Record (0x44 B, .rodata): +0..+0x10
 * GUI file IDs per language, +0x34 / +0x38 f32 k, +0x3c / +0x40 f32 offset; icons 0x61bde8: map = (world + area offset
 * of the stage's map_com stage\mNNd\mNNd) * 256 * k / dims[stage].w + 2 * offset, HD px from the texture centre
 * (dims: 0x5058d0, stage 18 = 40000, 26 = 60000; scale stored at 0x61b964). 4U: u = (world + offset + W / 2) / W * 128
 * (0xb832ac, W from the stage class: m08 30000, m19 40000) -> k = dims / W (package.toml [stage] wholemap_k) over the
 * 2x 4U picture: map = 2 * (u - 64). C */
#define WHOLEREC_SIZE 0x44u
static uint32_t s_wholerec[WHOLEREC_SIZE / 4];

int stage_wholerec_c(uint32_t *regs)
{
    const uint32_t *src = (const uint32_t *)(uintptr_t)regs[R0];
    uint32_t i;
    int m = alias_port();
    if (m < 0 || FIELD(uint32_t, regs[R4], 0x94) != port_monsters[m].stage_from || !port_monsters[m].whole_k || !src)
        return 0;
    for (i = 0; i < WHOLEREC_SIZE / 4; i++) s_wholerec[i] = src[i];
    FIELD(float, s_wholerec, 0x34) = port_monsters[m].whole_k;
    FIELD(float, s_wholerec, 0x38) = port_monsters[m].whole_k;
    FIELD(float, s_wholerec, 0x3c) = 0.0f;
    FIELD(float, s_wholerec, 0x40) = 0.0f;
    regs[R0] = (uint32_t)(uintptr_t)s_wholerec;
    logf("port: %s whole map record -> k %d/1000", port_monsters[m].name,
         (int)(port_monsters[m].whole_k * 1000.0f + 0.5f));
    return 0;
}
