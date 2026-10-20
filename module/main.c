/* MH4U monster ports: core module (subsdk1). The ported monsters are port_monsters[] (port.h).
 * Hook C functions: int name_c(uint32_t *regs) with regs = saved r0-r5, r12, lr.
 * Return 0 to run the game's function (with any changed regs), nonzero to return to its caller with regs[0]. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

extern uint32_t reg_files[], reg_mapicon[];   /* tables.S */
extern uint8_t notes_list[];                  /* notes.c */
void notes_init(void);                        /* notes.c */

/* data words (GOT-like) through which every reader reaches a table: point them at our extended copies */
static void redirect(const char *what, uint32_t word, uint32_t orig, uint32_t *copy)
{
    volatile uint32_t *p = (volatile uint32_t *)MAIN(word);
    if (*p == MAIN(orig)) {
        *p = (uint32_t)copy;
        logf("mh4uport: %s table -> %x (readback %x)", what, (uint32_t)copy, *p);
    } else {
        logf("mh4uport: word %x holds %x, expected %x: %s table NOT relocated", MAIN(word), *p, MAIN(orig), what);
    }
}

#define GU_FILES 0x1732a68u     /* GU's registry file manifests (pointers, per index) */

void module_init(void)
{
    logf("mh4uport: module_init, base %x, %d monster(s)", (uint32_t)(uintptr_t)&module_init, PORT_N);
    for (int m = 0; m < PORT_N; m++) {
        /* a monster's manifest is its donor's until its data file is read (port.c load) */
#ifdef CLONE_RATHIAN
        const uint32_t *donor = ((const uint32_t **)MAIN(GU_FILES))[0];
#else
        const uint32_t *donor = ((const uint32_t **)MAIN(GU_FILES))[port_monsters[m].donor_index];
#endif
        for (int k = 0; k < 51; k++) port_manifests[m][k] = donor[k];
        port_monsters[m].register_class();
    }
    redirect("file manifest", 0x1839618, GU_FILES, reg_files);   /* ~40 readers, indexes 137.. */
    redirect("map icon size", 0x183fff0, 0x1635354, reg_mapicon); /* cUIOQuestMapIcon 0x61a994, by em number */
    notes_init();
    redirect("hunter's notes", 0x183ec4c, 0x162d9f0, (uint32_t *)notes_list);   /* 6 readers, entries 123.. */
}

#ifdef TEST_SWAP
/* test builds only: every large monster of a quest becomes the first ported monster */
static uint32_t swap_id(uint32_t id)
{
    uint32_t t = port_monsters[0].em_id;
    return (id < 0x1000 && id != t) ? t : id;
}
#endif

/* A ported monster's quests name a GU stand-in boss (allocations.toml standin_id, e.g. Kushala 0x18 for Gogmazios),
 * kept out of the quest setup's per-monster tables; it is swapped to the monster at spawn prep and creation while
 * one of its quests runs (port_running_quest: quest ID [[0x188ae38]+0xd68] until the setup 0x3ade34, then the
 * running quest [[0x188ad90]+0xe0]; the spawn loader's r4 is that object). */
static uint32_t standin_swap(uint32_t id)
{
    int m = port_running_quest(0);
    if (m < 0 || !port_monsters[m].standin_id || (id & 0xffff) != port_monsters[m].standin_id) return id;
    return port_monsters[m].em_id;
}

/* 0x4ebcc(id, serial, spawn data, r3): monster factory */
int em_create_c(uint32_t *regs)
{
#ifdef TEST_SWAP
    regs[R0] = swap_id(regs[R0] & 0xffff);
#endif
    regs[R0] = standin_swap(regs[R0]);
    int m = port_by_em(regs[R0] & 0xffff);
    if (m >= 0)
        logf("mh4uport: em_create %s id=%x serial=%x lr=%x", port_monsters[m].name, regs[R0], regs[R1],
             regs[LR] - MAIN_BASE);
    return 0;
}

/* 0x68a70(quest, id): spawn prep, requests the monster's arc */
int quest_prep_c(uint32_t *regs)
{
#ifdef TEST_SWAP
    regs[R1] = swap_id(regs[R1] & 0xffff);
#endif
    if (regs[LR] - MAIN_BASE == 0x3adcf8) {   /* the quest loader's call: r4 = quest object [0x188ad90] */
        static uint32_t s_n;
        if (++s_n <= 20) logf("mh4uport: quest_prep quest %u (obj %u) id=%x", port_quest_id(),
                              FIELD(uint32_t, regs[R4], 0xe0), regs[R1]);
    }
    regs[R1] = standin_swap(regs[R1]);
    int m = port_by_em(regs[R1] & 0xffff);
    if (m >= 0) logf("mh4uport: quest_prep %s id=%x lr=%x", port_monsters[m].name, regs[R1], regs[LR] - MAIN_BASE);
    return 0;
}

/* 0x15334c(mgr, id): requests nativeNX/arc/enemy/em%03d_%02d.arc (kind 48); the quest loader's path */
int em_arc_request_c(uint32_t *regs)
{
#ifdef TEST_SWAP
    regs[R1] = swap_id(regs[R1] & 0xffff);
#endif
    uint32_t id = regs[R1] & 0xffff, q = port_quest_id();
    int m = port_by_em(id);
    if (m >= 0) logf("mh4uport: em_arc_request %s id=%x lr=%x", port_monsters[m].name, regs[R1], regs[LR] - MAIN_BASE);
    /* the quest is not known here (preload list 0x3b512c): with a stand-in, also request the arc of each installed
     * monster it stands in for, so it is resident before the spawn-prep swap (the call re-enters this hook with the
     * monster's ID and passes through). Its other quests skip the arc, but only when the quest is KNOWN (0 = load) */
    for (m = 0; m < PORT_N; m++) {
        const struct port_monster *p = &port_monsters[m];
        if (!p->standin_id || id != p->standin_id || !port_installed(m)) continue;
        if (q && port_quest_owner(q, 0) != m) continue;
        FN(void (*)(uint32_t, uint32_t), 0x15334c)(regs[R0], p->em_id);
    }
    return 0;
}

/* 0x69c258(res, index): record of a per-monster array resource (count at res+0x68, 137 entries); null for a ported
 * index -> enemy+0x7628 = 0 -> crash at 0x69c1cc. The monster borrows its donor's record. */
int em_record_c(uint32_t *regs)
{
    int m = port_by_index(regs[R1]);
    if (m < 0) return 0;
#ifdef CLONE_RATHIAN
    regs[R1] = 0;
#else
    regs[R1] = port_monsters[m].donor_index;
#endif
    logf("mh4uport: em_record index %u (count %u) -> %u", port_monsters[m].index, FIELD(uint32_t, regs[R0], 0x68),
         regs[R1]);
    return 0;
}

/* 0x3a75c8(obj, id, kind, r3): quest-end tally into the quest's 137-entry array (obj+0x110 + index*8: size,
 * hunts +0x114, captures +0x116; index = 0x50b64(id), no bound). At the end the writer 0x38da40 walks all 137
 * indexes, turns each back into an ID (0x50bdc) and adds it to the save (0x526d94 hunts, 0x526e00 captures,
 * 0x526eb0 / 0x526ef8 size records). A ported index would overflow, so each monster is counted in its save slot
 * (allocations.toml save_index: an unused 'dummy' registry index, e.g. 105 for Gogmazios), which no game screen
 * lists (large-monster list 0x162bf0c, Guild Card log table) and the save editor can show.
 * Hook 0x3a75fc, right after `bl 0x50b64`: only the index (r0) is remapped. The ID (r4) must stay the monster's:
 * the objective loop of the same function compares it with each objective's target (obj+0xf0, 0x3a7960) and marks
 * the hunt done there. Test 2026-10-20 10:24: remapping the ID at the entry tallied the kill, quest never ended. */
int stats_add_c(uint32_t *regs)
{
    int m = port_by_index(regs[R0]);
    if (m < 0) return 0;
    regs[R0] = port_monsters[m].save_index;
    /* kind = r2 at the entry, spilled to [sp+0x3c]; the caller's sp is just above the 8 saved registers */
    logf("mh4uport: %s quest-end tally kind %u -> save slot %x (index %u)", port_monsters[m].name,
         FIELD(uint32_t, regs, 32 + 0x3c), port_monsters[m].save_id, port_monsters[m].save_index);
    return 0;
}

/* 0x55bda4(mgr, id) -> monsterName GMD entry, = 0x50b64(id) (entry k = registry index k). Entry 137 already
 * starts the GMD's second list (Rathian), so a ported index reads its name_entry (an unused 'dummy' entry that
 * items.c renames in the loaded GMD). Replacement hook (build.py REPLACE_HOOKS). */
typedef int (*em_index_t)(uint32_t id);
#define em_index FN(em_index_t, 0x50b64)
int name_index_c(uint32_t *regs)
{
    int idx = em_index(regs[R1] & 0xffff), m = idx >= 0 ? port_by_index((uint32_t)idx) : -1;
    regs[R0] = (uint32_t)(m >= 0 ? (int)port_monsters[m].name_entry : idx);
    return 1;
}

/* 0x3a3930(obj, id): "hunted or captured?" from the same array -> a ported monster's entry is its save slot's */
int stats_hunted_c(uint32_t *regs)
{
    int m = port_by_em(regs[R1] & 0xffff);
    if (m >= 0) regs[R1] = (regs[R1] & ~0xffffu) | port_monsters[m].save_id;
    return 0;
}

/* 0x523104(save tallies, id) -> hunts + captures from the save (index from 0x50b64, > 136 answers 0): the Hunter's
 * Notes page (0x560058) and 8 other callers. A ported monster's tally is its save slot's (stats_add). */
int save_hunts_c(uint32_t *regs)
{
    int m = port_by_em(regs[R1] & 0xffff);
    if (m >= 0) regs[R1] = (regs[R1] & ~0xffffu) | port_monsters[m].save_id;
    return 0;
}
