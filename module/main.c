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

/* main's base check (position-independent build: game.h g_main_base = this module's base - build.py MAIN_GAP): the
 * icon setter's first word, `push {r4-r8, lr}`, must sit at MAIN(0x56ef50); "MISMATCH" = the loader put main and
 * this module at another distance than Ryujinx (issue #2: yuzu / Eden) */
#define CHECK_SITE 0x56ef50u
#define CHECK_WORD 0xe92d41f0u

void module_init(void)
{
    uint32_t w = *(volatile uint32_t *)MAIN(CHECK_SITE);
    logf("mh4uport: module_init, base %x, %d monster(s); main %x: %s (word %x)", (uint32_t)(uintptr_t)&module_init,
         PORT_N, MAIN_BASE, w == CHECK_WORD ? "ok" : "MISMATCH", w);
    for (int m = 0; m < PORT_N; m++) {
        /* a monster's manifest is its donor's until its data file is read (port.c load) */
#ifdef CLONE_RATHIAN
        const uint32_t *donor = ((const uint32_t **)MAIN(GU_FILES))[0];
#else
        const uint32_t *donor = ((const uint32_t **)MAIN(GU_FILES))[port_monsters[m].donor_index];
#endif
        for (int k = 0; k < 51; k++) port_manifests[m][k] = donor[k];
        if (port_monsters[m].register_class) port_monsters[m].register_class();   /* 0: a GU class runs it */
    }
    redirect("file manifest", 0x1839618, GU_FILES, reg_files);   /* ~40 readers, indexes 137.. */
    redirect("map icon size", 0x183fff0, 0x1635354, reg_mapicon); /* cUIOQuestMapIcon 0x61a994, by em number */
    notes_init();
    redirect("hunter's notes", 0x183ec4c, 0x162d9f0, (uint32_t *)notes_list);   /* 6 readers, entries 123.. */
}

#ifdef TEST_SWAP
/* test builds only: every large monster of a quest becomes ported monster TEST_SWAP_PORT (registry order, 0 =
 * the first; GOG_DEFINES="TEST_SWAP TEST_SWAP_PORT=1") */
#ifndef TEST_SWAP_PORT
#define TEST_SWAP_PORT 0
#endif
static uint32_t swap_id(uint32_t id)
{
    uint32_t t = port_monsters[TEST_SWAP_PORT].em_id;
    return (id < 0x1000 && id != t) ? t : id;
}
#endif

/* A ported monster's quests name a GU stand-in boss (allocations.toml standin_id, e.g. Kushala 0x18 for Gogmazios),
 * kept out of the quest setup's per-monster tables; it is swapped to the monster at spawn prep and creation while
 * one of its quests runs (port_running_quest: quest ID [[0x188ae38]+0xd68] until the setup 0x3ade34, then the
 * running quest [[0x188ad90]+0xe0]; the spawn loader's r4 is that object). Its companions (allocations.toml
 * companion_of, e.g. a tail half) are bosses of the same quests under stand-ins of their own. A quest listed in
 * standin_alt names the alternative stand-in instead (port_standin), and its standin_id boss stays a GU monster (e.g.
 * the Zinogre next to Stygian in 4U m10612). */
static uint32_t standin_swap(uint32_t id)
{
    int k = -1, q = port_running_quest(&k);
    for (int m = 0; q >= 0 && m < PORT_N; m++) {
        uint16_t s = PORT_OWNER(m) == q ? port_standin(m, k) : 0;
        if (s && (id & 0xffff) == s) return port_monsters[m].em_id;
    }
    return id;
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
        if (!((p->standin_id && id == p->standin_id) || (p->standin_alt && id == p->standin_alt)) ||
            !port_installed(m)) continue;
        if (q && port_quest_owner(q, 0) != PORT_OWNER(m)) continue;
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
    /* the quest clears when its rule's objectives are done (quest+0xe8 from questData +0x1d; check 0x3a027c): a
     * one-hunt quest needs +0x1d = 0 (Tigerstripe test 2026-10-21, monsters/tigerstripe_zamtrios/notes/plan.md) */
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

/* 0x687b0(mgr) caches the enemy resident tables (file IDs 0xde1a..0xde1f) in mgr+0x257c..0x2590 (C); hook 0x6880c,
 * r0 = em_size_scale_data (file 0xde1e): count +0x64, element k = 0x51904(res, k) = {+4 u32 registry index, +8 f32
 * base size (cm), +12 / +16 / +20 mini / silver / gold ratio, +24, +28}, read by the index of an ID (0x67310: size
 * and crown of a size %, 0x672bc). A ported monster's size record is filed under its save slot (stats_add), whose
 * GU element (a dummy) is all zero: the quest result showed a wrong size (user 2026-10-26). The slot's element =
 * the donor's with the 4U base size and crowns (package.toml [size]). 0x67310: mini if size % <= mini x 100, gold
 * if >= gold x 100, silver if >= silver x 100, so zeros would make every size gold: a monster without crowns in 4U
 * gets thresholds out of reach. */
typedef uint8_t *(*size_elem_t)(void *res, uint32_t k);
#define size_elem FN(size_elem_t, 0x51904)
int size_data_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *res = (void *)regs[R0];
    if (!res) return 0;
    uint32_t n = FIELD(uint32_t, res, 0x64);
    for (int m = 0; m < PORT_N; m++) {
        const struct port_monster *p = &port_monsters[m];
        if (p->owner >= 0 || p->size[0] <= 0.0f) continue;
        uint8_t *slot = 0, *donor = 0;
        for (uint32_t k = 0; k < n; k++) {
            uint8_t *e = size_elem(res, k);
            if (FIELD(uint32_t, e, 4) == p->save_index) slot = e;
            if (FIELD(uint32_t, e, 4) == p->donor_index) donor = e;
        }
        if (!slot) continue;
        if (donor)
            for (uint32_t o = 12; o < 32; o += 4) FIELD(float, slot, o) = FIELD(float, donor, o);
        FIELD(float, slot, 8) = p->size[0];
        FIELD(float, slot, 12) = p->size[1];
        FIELD(float, slot, 16) = p->size[1] > 0.0f ? p->size[2] : 100.0f;
        FIELD(float, slot, 20) = p->size[1] > 0.0f ? p->size[3] : 100.0f;
        if (++s_n <= 8)
            logf("mh4uport: %s size record: slot %u = base %d cm, crowns %d / %d / %d %%", p->name, p->save_index,
                 (int)p->size[0], (int)(p->size[1] * 100.0f), (int)(p->size[2] * 100.0f), (int)(p->size[3] * 100.0f));
    }
    return 0;
}
