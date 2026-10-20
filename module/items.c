/* Gogmazios materials (4U items 1528-1535 + Scrap+ 1713) in GU's unused "DUMMY" items 2977.., the Arcane jewels (4U
 * 1838-1841) in the DUMMY decorations 2889.. (tools/items_em089.py, notes/content-plan.md "Rewards"). Both GU tables live in loc/arc/resident.arc and <lang>/arc/resident_<lang>.arc,
 * which UI mods replace (the user's HD UI v4 ships both), so the loaded copies are patched instead of shipping arcs.
 * - rItemData (load = vt 11 0x192340): records [this+0x6c], 56 B each, count this+0x64, parsed from the 44-byte file
 *   records by 0x185694. Memory offset (file offset): +0x08 id (+0), +0x0d rarity-1 (+5), +0x0e carry (+6),
 *   +0x18 icon (+0x10), +0x19 colour (+0x11), +0x1c sell (+0x13), +0x20 buy (+0x17), +0x24 category (+0x1b).
 *   The DUMMY records are type 0 (decorations: 3), flags 0 and in no monster group (+0x26, 8 x u16) already.
 * - rGUIMessage (load 0xb839a8): path this+0x8 ("eng\table\itemData_eng"), name [this+0x8c] ("itemData"), string
 *   count +0x88, string pointers [this+0x98]: item k = name 2k, description 2k+1. Repointing them covers every reader
 *   (getter 0xb84114 and the direct ones).
 * Both hooks sit on the load's common exit (`mov r0, r8; add sp, sp, #24`), r4 = this. A slot that is not DUMMY any
 * more (another mod) is left alone. */
#include <stdint.h>
#include "util.h"
#include "game.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

struct em089_item { uint16_t id; uint8_t rarity, icon, colour, category, dummy_icon; uint32_t dummy_sell, sell, buy; };
struct em089_bui_entry { uint8_t chance, count; uint16_t item; };
#include "items_em089.inc"
#include "em089.h"

#define ITEM_REC 56
void gear_text_loaded(uint8_t *m, const char *name, uint32_t lang);   /* gear.c */
void notes_text_loaded(uint8_t *m, const char *name, uint32_t lang);  /* notes.c */
static const char *const LANGS[] = { "eng", "fre", "ger", "ita", "spa" };   /* em089_item_text order */

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

/* 0x19237c: rItemData load done */
int item_data_loaded_c(uint32_t *regs)
{
    uint8_t *recs = FIELD(uint8_t *, regs[R4], 0x6c);
    uint32_t n = FIELD(uint32_t, regs[R4], 0x64), done = 0;
    if (!recs) return 0;
    for (int i = 0; i < EM089_ITEMS; i++) {
        const struct em089_item *it = &em089_items[i];
        uint8_t *r = recs + ITEM_REC * it->id;
        if (it->id >= n || FIELD(uint32_t, r, 0x08) != it->id || r[0x18] != it->dummy_icon ||
            FIELD(uint32_t, r, 0x1c) != it->dummy_sell) {
            logf("gogport: item %u is not a DUMMY record, left alone", it->id);
            continue;
        }
        r[0x0d] = it->rarity - 1;
        r[0x0e] = 99;
        r[0x18] = it->icon;
        r[0x19] = it->colour;
        FIELD(uint32_t, r, 0x1c) = it->sell;
        FIELD(uint32_t, r, 0x20) = it->buy;
        r[0x24] = it->category;
        done++;
    }
    logf("gogport: item data (%u records): %u Gogmazios items set", n, done);
    return 0;
}

/* 0xb83c48: rGUIMessage load done */
int item_text_loaded_c(uint32_t *regs)
{
    uint8_t *m = (uint8_t *)regs[R4];
    const char *name = FIELD(const char *, m, 0x8c), *path = (const char *)(m + 0x8), *suffix = 0;
    const char **str = FIELD(const char **, m, 0x98);
    uint32_t n = FIELD(uint32_t, m, 0x88), lang = 0, done = 0;
    if (!name || !str) return 0;
    for (const char *p = path; p < path + 64 && *p; p++)
        if (*p == '_') suffix = p + 1;
    for (uint32_t k = 0; suffix && k < sizeof(LANGS) / sizeof(LANGS[0]); k++)
        if (str_eq(suffix, LANGS[k])) lang = k;          /* chS / chT / others: English */
    gear_text_loaded(m, name, lang);                     /* armor / skill names (gear.c) */
    notes_text_loaded(m, name, lang);                    /* Hunter's Notes entry (notes.c) */
    if (!str_eq(name, "itemData")) return 0;
    for (int i = 0; i < EM089_ITEMS; i++) {
        uint32_t s = 2u * em089_items[i].id;
        if (s + 1 >= n || !str[s] || !str_eq(str[s], "DUMMY")) continue;
        str[s] = em089_item_text[lang][i][0];
        str[s + 1] = em089_item_text[lang][i][1];
        done++;
    }
    logf("gogport: item text %s: %u Gogmazios names set", path, done);
    return 0;
}

/* ---- break rewards ----
 * GU: result.arc quest\bui\bui_s<rank> (rBui: 462-byte file records -> 468-byte records, count +0x64, array +0x6c),
 * searched by monster ID at the reward screen: 0x3a3874(quest, em id) (one caller, 0x3829a0, walking the quest's
 * break list quest+0x566 {u16 em id, u8 cond, u8 count, u16}). Record: +4 u16 em id, +6 u8 cond[18], +0x18 u8
 * count[18], +0x2a entries {u8 chance, u8 count, u16 item}, each group closed by chance 255 (group lookup 0x354484).
 * cond = table 0x162a736 {10, 20, .., 60}[break group] (list adder 0x3a6f54; tail sever = 10); the groups are the
 * dtbparts record groups (em089_break.c). No GU record has Gogmazios' ID: the hook answers with em089's own record,
 * whatever the rank (G-only monster), also for EM089_SAVE_ID (main.c stats_add counts Gogmazios under it; no GU
 * record has it). Kushala (the quest's stand-in ID) never spawns in quests 11491 / 11492. */
#define GOG_STANDIN 0x18u
int gog_quest_index(void);     /* stage.c: 1 / 2 = our quests, 0 = other */
#define BUI_REC 468
static uint8_t s_bui[BUI_REC];

static void bui_build(void)
{
    uint32_t e = 0;
    for (int g = 0; g < EM089_BUI_GROUPS; g++) {
        s_bui[0x06 + g] = em089_bui_cond[g];
        s_bui[0x18 + g] = em089_bui_count[g];
        for (uint32_t k = 0; k <= em089_bui_count[g]; k++, e++) {
            uint8_t *d = s_bui + 0x2a + 4 * e;
            d[0] = em089_bui[e].chance;
            d[1] = em089_bui[e].count;
            FIELD(uint16_t, d, 2) = em089_bui[e].item;
        }
    }
    FIELD(uint16_t, s_bui, 4) = EM089_ID;
}

/* 0x3a3874(quest, em id) -> break reward record */
int bui_record_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff;
    if (id != EM089_ID && id != EM089_SAVE_ID && !(id == GOG_STANDIN && gog_quest_index())) return 0;
    if (!FIELD(uint16_t, s_bui, 4)) bui_build();
    regs[R0] = (uint32_t)s_bui;
    logf("gogport: break rewards for id %x: em089 record", id);
    return 1;
}
