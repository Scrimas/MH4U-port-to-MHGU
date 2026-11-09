/* Ported monsters in the Hunter's Notes large-monster list (data file section NOTE; the two texts per entry are a
 * TXTA append of HN_MonsterListMsg, gear.c). The three GU tables (list 0x162d9f0 16 B, unlock conditions 0x162d1f8
 * 8 B {u32 value, u8 kind}, display order 0x1631ef4 u32) are copied from GU's own at module_init with one more entry
 * per ported monster (allocations.toml notes_entry, consecutive from 123; companions have none): the list through
 * data word 0x183ec4c
 * (main.c), the other two through literal patches, the 123-entry loop bounds patched (build.py LIT_PATCHES /
 * WORD_PATCHES; two loops are unrolled by two and read one record past the end: a padding record follows).
 * Save bits 123..127 of S+0x35b0 are free. Until its data file is read, a monster's entry is a padding record
 * (em 0xffff, type 0xff: no lookup matches it) listed last; notes_data_loaded fills it and moves it after its anchor
 * entry. The data applies whether the monster is installed or not (port.h): its quest unlocks the entry.
 *
 * Entries past the save map (notes_entry >= 128, end of this file): no save bit at all. Their state is computed from
 * what the save already holds (a quest of the monster cleared), so nothing is written for them and a save that loses
 * the mod holds no trace of them. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

#define GU_LIST    0x162d9f0u
#define GU_UNLOCK  0x162d1f8u
#define GU_ORDER   0x1631ef4u
#define GU_COUNT   123
#define NOTES_COUNT (GU_COUNT + (int)PORT_NOTES_COUNT)

uint8_t notes_list[(NOTES_COUNT + 1) * 16] __attribute__((aligned(4)));   /* + the padding record */
uint8_t notes_unlock[NOTES_COUNT * 8] __attribute__((aligned(4)));
uint32_t notes_order[NOTES_COUNT];

static void padding(uint8_t *r)            /* u32 0, u16 em 0xffff, u8 type 0xff, u8 0xff, 8 x 0 */
{
    for (int i = 0; i < 16; i++) r[i] = 0;
    FIELD(uint16_t, r, 4) = 0xffff;
    r[6] = r[7] = 0xff;
}

void notes_init(void)
{
    const uint8_t *list = (const uint8_t *)MAIN(GU_LIST), *unl = (const uint8_t *)MAIN(GU_UNLOCK);
    for (int i = 0; i < GU_COUNT * 16; i++) notes_list[i] = list[i];
    for (int i = 0; i < GU_COUNT * 8; i++) notes_unlock[i] = unl[i];
    for (int i = 0; i < GU_COUNT; i++) notes_order[i] = ((const uint32_t *)MAIN(GU_ORDER))[i];
    for (int m = 0; m < PORT_N; m++) {
        uint32_t e = port_monsters[m].notes_entry;
        if (!e) continue;
        padding(notes_list + 16 * e);
        FIELD(uint32_t, notes_unlock, 8 * e) = port_monsters[m].quests[0];
        notes_unlock[8 * e + 4] = 2;           /* kind 2 = that quest cleared */
        notes_order[e] = e;
    }
    padding(notes_list + 16 * NOTES_COUNT);
}

/* NOTE: u8 list record[16], u8 unlock record[8], u32 the entry it is listed after (port.c, once per monster) */
void notes_data_loaded(int m)
{
    uint32_t size, e = port_monsters[m].notes_entry, k, at = NOTES_COUNT;
    const uint8_t *s = port_section(m, "NOTE", 0, &size);
    if (!s || size < 28 || e < GU_COUNT || e >= NOTES_COUNT) return;
    for (int i = 0; i < 16; i++) notes_list[16 * e + i] = s[i];
    for (int i = 0; i < 8; i++) notes_unlock[8 * e + i] = s[16 + i];
    for (k = 0; k < NOTES_COUNT && notes_order[k] != e; k++) ;
    for (; k + 1 < NOTES_COUNT; k++) notes_order[k] = notes_order[k + 1];     /* take it out (it was last) */
    for (k = 0; k + 1 < NOTES_COUNT; k++)
        if (notes_order[k] == PORT_U32(s, 24)) at = k + 1;
    if (at > NOTES_COUNT - 1) at = NOTES_COUNT - 1;
    for (k = NOTES_COUNT - 1; k > at; k--) notes_order[k] = notes_order[k - 1];
    notes_order[at] = e;
    logf("mhgu-de: hunter's notes entry %u = %s (em %x), listed at %u after entry %u", e, port_monsters[m].name,
         FIELD(uint16_t, notes_list + 16 * e, 4), at, PORT_U32(s, 24));
}

/* 0x554da4(entry) -> 1 when the entry's unlock condition holds. Called by talk action 6 (the loop at 0x247ae4 that
 * sets the unlock bits S+0x35b0) and talk condition 44, i.e. only from NPC dialogue scripts. Diagnostic (test
 * 2026-10-20 18:32: quest 11491 marked cleared, entry still hidden): log a ported entry's check and whether the
 * cleared map [0x1897f78]+0x42c holds its quest (0x523da4, the same lookup the condition uses). */
typedef int (*quest_cleared_t)(void *bitmap, uint32_t id);
#define questCleared FN(quest_cleared_t, 0x523da4)
enum { R0, R1, R2, R3, R4, R5, R12, LR };
int notes_unlock_check_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (regs[R0] < GU_COUNT || regs[R0] >= NOTES_COUNT || ++s_n > 10) return 0;
    uint8_t *save = *(uint8_t **)MAIN(0x1897f78);
    uint32_t q = FIELD(uint32_t, notes_unlock, 8 * regs[R0]);
    logf("mhgu-de: hunter's notes: unlock check of entry %u (lr %x), quest %u cleared %d", regs[R0],
         regs[LR] - MAIN_BASE, q, save ? questCleared(save + 0x42c, q) : -1);
    return 0;
}

/* Entries past the 128 bits of S+0x35b0. Every use of an entry's bit, C (all 13 code sites loading 0x35b0, 7 of 0x35c0):
 * - S+0x35b0 unlocked, S+0x35c0 NEW, 16 bytes each, then S+0x35d0 (another list's map): an entry >= 128 would read and
 *   write those. The two talk loops (condition 44 0x245848, action 6 0x247ae4, the only writers of S+0x35b0) stop at
 *   128 (build.py WORD_PATCHES), so such an entry is never "due" and never set.
 * - list screen 0x5b0b48: visible 0x5b0bbc (hook below), its NEW mark 0x5b0a38 (below), the mark cleared on selection
 *   0x5b0ad4 (below, the write is skipped).
 * - 0x524728(S, em ID), one caller 0x161e28: below. 0x524660 stops at em IDs above 56, ours are higher. The other
 *   readers (0x5565xx, 0x55686c) take fixed GU entries.
 * Unlocked = any quest of the monster cleared (the cleared map S+0x42c, written by GU for every quest), as the entry
 * would be after talking to the NPC; no NEW mark. Nothing here writes. */
#define NOTES_SAVE_BITS 128u
#define NOTES_ZERO_WORD 49u                /* (S+0x3684 - S+0x35c0) / 4: the reserved block's start, never written
                                            * (notes/save-store.md); read as "no NEW mark" */

static int notes_live(uint32_t e)
{
    uint8_t *save = *(uint8_t **)MAIN(0x1897f78);
    if (!save) return 0;
    for (int m = 0; m < PORT_N; m++) {
        if (port_monsters[m].notes_entry != e) continue;
        for (int k = 0; k < PORT_QUESTS; k++)
            if (port_monsters[m].quests[k] && questCleared(save + 0x42c, port_monsters[m].quests[k])) return 1;
    }
    return 0;
}

int notes_list_visible_c(uint32_t *regs)   /* 0x5b0bd4: r0 = the map word, r5 = position in the display order */
{
    uint32_t e = notes_order[regs[R5]];
    if (e >= NOTES_SAVE_BITS) regs[R0] = notes_live(e) ? ~0u : 0u;
    return 0;
}

int notes_list_new_c(uint32_t *regs)       /* 0x5b0a44: r0 = entry, r1 = its word index in S+0x35c0 */
{
    if (regs[R0] >= NOTES_SAVE_BITS) regs[R1] = NOTES_ZERO_WORD;
    return 0;
}

int notes_new_clear_c(uint32_t *regs)      /* 0x5b0ad4: r0 = entry; nonzero: past the write (MID_EXIT 0x5b0af4) */
{
    return regs[R0] >= NOTES_SAVE_BITS;
}

int notes_em_unlocked_c(uint32_t *regs)    /* 0x524770: r12 = entry; nonzero: returns regs[R0] (MID_EXIT bx lr) */
{
    if (regs[R12] < NOTES_SAVE_BITS) return 0;
    regs[R0] = (uint32_t)notes_live(regs[R12]);
    return 1;
}
