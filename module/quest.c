/* The ported monsters' quests on GU's boards (monsters/gogmazios/notes/stage.md section 8; for Gogmazios quests
 * 11491 / 11492, monsters/gogmazios/tools/build_gog_quest.py). Each installed monster's quests take unused DUMMY
 * entries of the quest list (allocations.toml quest_slots); a monster that is not installed keeps them DUMMY.
 * quest_group (loc/arc/village/common.arc) in memory: [[0x188ad90]+0xb4], count +0x64, entries +0x6c (12 B: +4 quest
 * ID, +8 group byte). The loader step 0x3b7de8 walks it and loads loose questData_%07d.ext for Hub G-rank IDs, then
 * 0x3bb318 sorts them onto the star boards. Nothing real is replaced. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

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
                if (id != pm->quest_slots[k] || !pm->quests[k] || !port_installed(m)) continue;
                *(volatile uint32_t *)(p + 4) = pm->quests[k];
                p[8] = 0;                              /* group: regular */
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
 * Renaming here puts it at its slot's index (11491 at 1412, 11492 at 1407), the bit the board and the Notes read. */
int quest_clear_fix_c(uint32_t *regs)
{
    (void)regs;
    quest_group_rename();
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
