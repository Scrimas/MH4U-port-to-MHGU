/* Gogmazios port module (subsdk1).
 * Hook C functions: int name_c(uint32_t *regs) with regs = saved r0-r5, r12, lr.
 * Return 0 to run the game's function (with any changed regs), nonzero to return to its caller with regs[0]. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

extern uint32_t reg_files[], reg_mapicon[];   /* tables.S */
extern const uint8_t notes_list[];            /* notes_em089.inc (notes.c) */

/* data words (GOT-like) through which every reader reaches a table: point them at our extended copies */
static void redirect(const char *what, uint32_t word, uint32_t orig, uint32_t *copy)
{
    volatile uint32_t *p = (volatile uint32_t *)MAIN(word);
    if (*p == MAIN(orig)) {
        *p = (uint32_t)copy;
        logf("gogport: %s table -> %x (readback %x)", what, (uint32_t)copy, *p);
    } else {
        logf("gogport: word %x holds %x, expected %x: %s table NOT relocated", MAIN(word), *p, MAIN(orig), what);
    }
}

void module_init(void)
{
    logf("gogport: module_init, base %x", (uint32_t)(uintptr_t)&module_init);
    em089_register_class();
    redirect("file manifest", 0x1839618, 0x1732a68, reg_files);   /* ~40 readers, index 137 */
    redirect("map icon size", 0x183fff0, 0x1635354, reg_mapicon); /* cUIOQuestMapIcon 0x61a994, em 89 */
    redirect("hunter's notes", 0x183ec4c, 0x162d9f0, (uint32_t *)notes_list);   /* 6 readers, entry 123 */
}

#ifdef TEST_SWAP
/* test builds only: every large monster of a quest becomes the new monster */
static uint32_t swap_id(uint32_t id)
{
    return (id < 0x1000 && id != EM089_ID) ? EM089_ID : id;
}
#endif

/* Gogmazios quests 11491 / 11492 (tools/build_gog_quest.py): their boss record names Kushala (0x18), a stand-in kept
 * out of the quest setup's per-monster tables; it is swapped to 0x59 at spawn prep and creation while they run.
 * Quest ID: gog_quest_id() (stage.c) = accepted quest [[0x188ae38]+0xd68] until the setup 0x3ade34, then the running
 * quest [[0x188ad90]+0xe0] (the spawn loader's r4 is that object; [quest+0xa4] is the parsed 272-byte questData
 * record, ID at +8, not +0xc). */
#define GOG_STANDIN 0x18u
uint32_t gog_quest_id(void);   /* stage.c */
int gog_quest_index(void);     /* stage.c: 1 = quest 11491, 2 = quest 11492 (same stand-in), 0 = other */
static int gog_quest(void) { return gog_quest_index() != 0; }

/* 0x4ebcc(id, serial, spawn data, r3): monster factory */
int em_create_c(uint32_t *regs)
{
#ifdef TEST_SWAP
    regs[R0] = swap_id(regs[R0] & 0xffff);
#endif
    if ((regs[R0] & 0xffff) == GOG_STANDIN && gog_quest()) regs[R0] = EM089_ID;
    if ((regs[R0] & 0xffff) == EM089_ID)
        logf("gogport: em_create id=%x serial=%x lr=%x", regs[R0], regs[R1], regs[LR] - MAIN_BASE);
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
        if (++s_n <= 20) logf("gogport: quest_prep quest %u (obj %u) id=%x", gog_quest_id(),
                              FIELD(uint32_t, regs[R4], 0xe0), regs[R1]);
    }
    if ((regs[R1] & 0xffff) == GOG_STANDIN && gog_quest()) regs[R1] = EM089_ID;
    if ((regs[R1] & 0xffff) == EM089_ID)
        logf("gogport: quest_prep id=%x lr=%x", regs[R1], regs[LR] - MAIN_BASE);
    return 0;
}

/* 0x15334c(mgr, id): requests nativeNX/arc/enemy/em%03d_%02d.arc (kind 48); the quest loader's path */
int em_arc_request_c(uint32_t *regs)
{
#ifdef TEST_SWAP
    regs[R1] = swap_id(regs[R1] & 0xffff);
#endif
    if ((regs[R1] & 0xffff) == EM089_ID)
        logf("gogport: em_arc_request id=%x lr=%x", regs[R1], regs[LR] - MAIN_BASE);
    /* the quest is not known here (preload list 0x3b512c): with the stand-in, also request our arc, so it is
     * resident before the spawn-prep swap (the original call re-enters this hook with 0x59 and passes through) */
    if ((regs[R1] & 0xffff) == GOG_STANDIN) {
        /* skip the 19 MB arc in other Kushala quests, but only when another quest is KNOWN (0 = unknown: load) */
        if (gog_quest_id() && !gog_quest()) return 0;
        FN(void (*)(uint32_t, uint32_t), 0x15334c)(regs[R0], EM089_ID);
    }
    return 0;
}

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

/* 0x69c258(res, index): record of a per-monster array resource (count at res+0x68, 137 entries);
 * null for index 137 -> enemy+0x7628 = 0 -> crash at 0x69c1cc. Borrow the donor's record for now. */
int em_record_c(uint32_t *regs)
{
    if (regs[R1] == EM089_INDEX) {
#ifdef CLONE_RATHIAN
        regs[R1] = 0;
#else
        regs[R1] = EM089_DONOR_INDEX;
#endif
        logf("gogport: em_record index 137 (count %u) -> %u", FIELD(uint32_t, regs[R0], 0x68), regs[R1]);
    }
    return 0;
}

/* 0x3a75c8(obj, id, kind, r3): quest-end tally into the quest's 137-entry array (obj+0x110 + index*8: size,
 * hunts +0x114, captures +0x116; index = 0x50b64(id), no bound). At the end the writer 0x38da40 walks all 137
 * indexes, turns each back into an ID (0x50bdc) and adds it to the save (0x526d94 hunts, 0x526e00 captures,
 * 0x526eb0 / 0x526ef8 size records). Index 137 would overflow, so Gogmazios is counted as EM089_SAVE_ID (dummy1,
 * index 105): its records land in the save's unused slot 105, which no game screen lists (large-monster list
 * 0x162bf0c, Guild Card log table) and the save editor can show.
 * Hook 0x3a75fc, right after `bl 0x50b64`: only the index (r0) is remapped. The ID (r4) must stay 0x59: the
 * objective loop of the same function compares it with each objective's target (obj+0xf0, 0x3a7960) and marks the
 * hunt done there. Test 2026-10-20 10:24: remapping the ID at the entry tallied the kill but the quest never ended. */
#define EM089_SAVE_INDEX 105u
int stats_add_c(uint32_t *regs)
{
    if (regs[R0] != EM089_INDEX) return 0;
    regs[R0] = EM089_SAVE_INDEX;
    /* kind = r2 at the entry, spilled to [sp+0x3c]; the caller's sp is just above the 8 saved registers */
    logf("gogport: quest-end tally kind %u -> save slot %x (index %u)", FIELD(uint32_t, regs, 32 + 0x3c),
         EM089_SAVE_ID, EM089_SAVE_INDEX);
    return 0;
}

/* 0x55bda4(mgr, id) -> monsterName GMD entry, = 0x50b64(id) (entry k = registry index k). Entry 137 already
 * starts the GMD's second list (Rathian), so index 137 reads entry 105, the unused 'dummy1' that
 * tools/ui_em089.py renames to Gogmazios in the romfs copies. Replacement hook (build.py REPLACE_HOOKS). */
#define EM089_NAME_ENTRY 105
typedef int (*em_index_t)(uint32_t id);
#define em_index FN(em_index_t, 0x50b64)
int name_index_c(uint32_t *regs)
{
    int idx = em_index(regs[R1] & 0xffff);
    regs[R0] = (uint32_t)(idx == (int)EM089_INDEX ? EM089_NAME_ENTRY : idx);
    return 1;
}

/* 0x3a3930(obj, id): "hunted or captured?" from the same array -> Gogmazios' entry is EM089_SAVE_ID's */
int stats_hunted_c(uint32_t *regs)
{
    if ((regs[R1] & 0xffff) == EM089_ID) regs[R1] = (regs[R1] & ~0xffffu) | EM089_SAVE_ID;
    return 0;
}

/* 0x523104(save tallies, id) -> hunts + captures from the save (index from 0x50b64, > 136 answers 0): the Hunter's
 * Notes page (0x560058) and 8 other callers. Gogmazios' save slot is EM089_SAVE_ID's (stats_add). */
int save_hunts_c(uint32_t *regs)
{
    if ((regs[R1] & 0xffff) == EM089_ID) regs[R1] = (regs[R1] & ~0xffffu) | EM089_SAVE_ID;
    return 0;
}
