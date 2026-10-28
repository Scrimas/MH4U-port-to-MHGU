/* The ported monsters' quests on GU's boards (monsters/gogmazios/notes/stage.md section 8; for Gogmazios quests
 * 11491 / 11492, monsters/gogmazios/tools/build_gog_quest.py). Two ways (allocations.toml): quest_slots = each
 * installed monster's quests take unused DUMMY entries of the quest list (a monster that is not installed keeps them
 * DUMMY); quest_append = its quests are new entries after GU's (quest_group_append, monsters/stygian_zinogre/notes/
 * quests.md 3). quest_group (loc/arc/village/common.arc) in memory: [[0x188ad90]+0xb4], count +0x64, entries +0x6c
 * (12 B: +4 quest ID, +8 group byte, +9, +10 name colour row). The loader step 0x3b7de8 walks it and loads loose
 * questData_%07d.ext for Hub G-rank IDs, then 0x3bb318 sorts them onto the star boards. Nothing real is replaced. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

/* entry byte +10 = the row of the quest name's colours on the boards (C: 0x3b22dc returns it, 1 for an ID not listed;
 * the board rows 0x6173c4 / 0x618644 index table 0x1635230 {unselected, selected} with it: 0 -> colours 0x13 / 0x0b,
 * 1 -> 0x11 / 0x12, 2 -> 0x09 / 0x14). GU's list (C, v1.0): Hub IDs 10101..10774 0 (300 of 313, the 13 others are
 * special quests), Hub G-rank IDs 11101..11457 1 (all), village IDs 0..641 0, 701..1055 1 (all) */
static uint8_t qg_colour(uint32_t id)
{
    return id < 700 || (id >= 10000 && id < 11000) ? 0 : 1;
}

static void quest_group_rename(void)
{
    uint32_t mgr = *(volatile uint32_t *)MAIN(0x188ad90u), grp, n, e, i, k;
    if (!mgr || !(grp = FIELD(uint32_t, mgr, 0xb4))) return;
    n = FIELD(uint32_t, grp, 0x64);
    e = FIELD(uint32_t, grp, 0x6c);
    if (!e) return;
    for (i = 0; i < n; i++) {
        volatile uint8_t *p = (volatile uint8_t *)(uintptr_t)(e + 12 * i);
        uint32_t id = *(volatile uint32_t *)(p + 4);
        for (int m = 0; m < PORT_N; m++)
            for (k = 0; k < PORT_QUESTS; k++) {
                const struct port_monster *pm = &port_monsters[m];
                /* slot 0 = none (a quest_append entry has no slots): GU's own quest 0 is entry 0 */
                if (!pm->quest_slots[k] || id != pm->quest_slots[k] || !pm->quests[k] || !port_installed(m)) continue;
                *(volatile uint32_t *)(p + 4) = pm->quests[k];
                p[8] = 0;                              /* group: regular */
                p[10] = qg_colour(pm->quests[k]);      /* the DUMMY slot's 1 -> GU's row for the quest's rank */
                logf("mh4uport: quest_group entry %u: %u -> %u (%s)", i, pm->quest_slots[k], pm->quests[k], pm->name);
            }
    }
}

/* 0x3b7de8: quest list loader step (runs repeatedly; the rename is idempotent) */
int quest_group_fix_c(uint32_t *regs)
{
    (void)regs;
    quest_group_rename();
    return 0;
}

/* 0x388d40(this): the results scene's clear write (results state machine 0x384848 -> 0x384af0 -> 0x384f8c): looks
 * the running quest [mgr+0xe0] up in the quest list and sets its bit in the cleared map [0x1897f78]+0x42c (0x523f30;
 * failed map +0x62c via 0x526b98 on state 4). The results scene loads its own fresh list (0x6a1f64 -> 0x3b190c) that
 * the loader-step rename never sees, so 11491 was not found and the clear went to bit 0 (quest-clear helper, C).
 * Renaming here puts it at its slot's index (11491 at 1412, 11492 at 1407), the bit the board and the Notes read.
 * Logged for a ported quest: the list index it is found at = the bit the write sets (an appended quest: 1509..). */
int quest_clear_fix_c(uint32_t *regs)
{
    uint32_t mgr = *(volatile uint32_t *)MAIN(0x188ad90u), grp, id = port_quest_id(), n, e, i;
    (void)regs;
    quest_group_rename();
    if (mgr && (grp = FIELD(uint32_t, mgr, 0xb4)) && port_quest_owner(id, 0) >= 0) {
        n = FIELD(uint32_t, grp, 0x64);
        e = FIELD(uint32_t, grp, 0x6c);
        for (i = 0; e && i < n && *(volatile uint32_t *)(uintptr_t)(e + 12 * i + 4) != id; i++) ;
        logf("mh4uport: clear write for quest %u: list index %u of %u", id, i, n);
    }
    return 0;
}

typedef void *(*qg_new_t)(uint32_t size, uint32_t align);
typedef void *(*qg_entry_t)(void *e);
typedef void (*qg_delete_t)(void *block);
#define qg_new FN(qg_new_t, 0x37a5ec)        /* new[](size, 16): the parser's allocator */
#define qg_ctor FN(qg_entry_t, 0x37a654)     /* entry ctor: vtable, +4 / +8..+10 = 0 */
#define qg_dtor FN(qg_entry_t, 0x37a684)     /* entry dtor */
#define qg_delete FN(qg_delete_t, 0x37a628)  /* delete[](entries - 8) */
#define QG_MAX (PORT_N * PORT_QUESTS)
#define QG_PLACEHOLDER 1111010u              /* a vanilla DUMMY entry (index 1460, group 127, +10 = 1): in no
                                                quest_slots list (tools/alloc.py QUEST_PLACEHOLDER) */

/* 0x39bb6c: quest_group's parser 0x39bb30 (f32 4.0, u32 count, count x {u32 ID, u8 group, u8, u8}) at its common exit
 * `mov r0, r8` (r4 = this). Every load passes here (the boards' list and the results scene's fresh list, both via
 * 0x3b190c), so both get the appended block without a rename. The entries are rebuilt the parser's way (new[] with
 * the cookie {12, n + N} before them, ctor each), GU's copied and ours after; the old block is freed as the release
 * 0x39b9a8 frees it (dtor from the last, delete[]), and the game frees ours later the same way. The block = every
 * quest_append entry's quests in registry order, installed or not: a quest whose monster or questData file is missing
 * takes the placeholder, so no quest's index (its cleared / failed bit) ever moves. */
int quest_group_append_c(uint32_t *regs)
{
    static uint32_t s_logged;
    uint8_t *grp = (uint8_t *)(uintptr_t)regs[R4], g[QG_MAX], c[QG_MAX], *e, *blk, *ne;
    uint32_t id[QG_MAX], n, N = 0, i;
    for (int m = 0; m < PORT_N; m++) {
        if (!port_monsters[m].quest_append) continue;
        for (int k = 0; k < PORT_QUESTS; k++) {
            uint32_t q = port_monsters[m].quests[k];
            if (!q) continue;
            int on = port_installed(m) && port_quest_present(m, k);
            id[N] = on ? q : QG_PLACEHOLDER;
            g[N] = on ? 0 : 127;                       /* group: regular / DUMMY */
            c[N++] = on ? qg_colour(q) : 1;
        }
    }
    n = FIELD(uint32_t, grp, 0x64);
    e = (uint8_t *)(uintptr_t)FIELD(uint32_t, grp, 0x6c);
    if (!N || !n || !e) return 0;
    for (i = 0; n >= N && i < N; i++)                  /* already there (a failed parse keeps the list it had) */
        if (FIELD(uint32_t, e, 12 * (n - N + i) + 4) != id[i] || e[12 * (n - N + i) + 8] != g[i]) break;
    if (n >= N && i == N) return 0;
    blk = qg_new(12 * (n + N) + 8, 16);
    if (!blk) {
        logf("mh4uport: quest_group: new[] failed, %u quests not appended", N);
        return 0;
    }
    FIELD(uint32_t, blk, 0) = 12;
    FIELD(uint32_t, blk, 4) = n + N;
    ne = blk + 8;
    for (i = 0; i < n + N; i++) {
        uint8_t *p = ne + 12 * i;
        qg_ctor(p);
        if (i < n) {
            FIELD(uint32_t, p, 4) = FIELD(uint32_t, e, 12 * i + 4);
            p[8] = e[12 * i + 8], p[9] = e[12 * i + 9], p[10] = e[12 * i + 10];
        } else {
            FIELD(uint32_t, p, 4) = id[i - n];
            p[8] = g[i - n], p[9] = 0, p[10] = c[i - n];
        }
    }
    for (i = n; i-- > 0;) qg_dtor(e + 12 * i);
    qg_delete(e - 8);
    FIELD(uint32_t, grp, 0x6c) = (uint32_t)(uintptr_t)ne;
    FIELD(uint32_t, grp, 0x64) = n + N;
    if (s_logged++ < 4) logf("mh4uport: quest_group: %u entries + %u appended (indexes %u..%u)", n, N, n, n + N - 1);
    return 0;
}

/* 0x3b2174(_, id) -> bool: "quest unlocked?" (script check_quest_unlocked has no rule for our IDs) */
int quest_unlocked_c(uint32_t *regs)
{
    int m = port_quest_owner(regs[R1], 0);
    if (m < 0 || !port_installed(m)) return 0;
    regs[R0] = 1;
    return 1;
}

/* 0x7ca340(out, const char *s, n): UTF-8 helper (8 callers), strlen(s) first. Abandoning the Gogmazios quest crashed
 * here with s = NULL while the quest setup had been skipped (null questLink, fixed in the arc layout). Safety net: a
 * null string becomes "" (the helper's own length-0 path), logged with the caller so a remaining source can be
 * found. */
int utf8_null_guard_c(uint32_t *regs)
{
    static const char empty[1];
    static uint32_t s_n;
    if (regs[R1]) return 0;
    regs[R1] = (uint32_t)(uintptr_t)empty;
    if (++s_n <= 20) logf("mh4uport: null string to 0x7ca340 from lr=%x (quest %u)", regs[LR] - MAIN_BASE,
                          port_quest_id());
    return 0;
}
