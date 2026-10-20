/* Gogmazios in the Hunter's Notes large-monster list (tools/notes_em089.py -> notes_em089.inc).
 * The three GU tables (list, unlock conditions, display order) are module copies with Gogmazios as entry 123:
 * the list through data word 0x183ec4c (main.c module_init), the other two through literal patches, and the
 * 123-entry loop bounds patched to 124 (build.py LIT_PATCHES / WORD_PATCHES). Save bit 123 of S+0x35b0 is free.
 * Here: the two HN_MonsterListMsg strings the entry names (description, tips page). */
#include <stdint.h>
#include "util.h"
#include "game.h"

#include "notes_em089.inc"

void gmd_append(uint8_t *m, uint32_t expect, const char *const *strs, uint32_t n, const char *what);   /* gear.c */

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

/* called by items.c for every rGUIMessage load */
void notes_text_loaded(uint8_t *m, const char *name, uint32_t lang)
{
    if (str_eq(name, "HN_MonsterListMsg"))
        gmd_append(m, NOTES_TEXT_FIRST, notes_text[lang], 2, "notes text");
}

/* 0x554da4(entry) -> 1 when the entry's unlock condition holds. Called by talk action 6 (the loop at 0x247ae4 that
 * sets the unlock bits S+0x35b0) and talk condition 44, i.e. only from NPC dialogue scripts. Diagnostic (test
 * 2026-10-20 18:32: quest 11491 marked cleared, entry still hidden): log Gogmazios' check and whether the cleared
 * map [0x1897f78]+0x42c holds quest 11491 (0x523da4, the same lookup the condition uses). */
typedef int (*quest_cleared_t)(void *bitmap, uint32_t id);
#define questCleared FN(quest_cleared_t, 0x523da4)
enum { R0, R1, R2, R3, R4, R5, R12, LR };
int notes_unlock_check_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (regs[R0] != NOTES_COUNT || ++s_n > 10) return 0;
    uint8_t *save = *(uint8_t **)MAIN(0x1897f78);
    logf("gogport: hunter's notes: unlock check of entry %u (lr %x), quest 11491 cleared %d", regs[R0],
         regs[LR] - MAIN_BASE, save ? questCleared(save + 0x42c, 11491) : -1);
    return 0;
}
