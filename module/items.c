/* Ported monsters' materials in GU's unused "DUMMY" items 2977.., their jewels in the DUMMY decorations 2889..
 * (data file section ITEM, monsters/<name>/tools/items_*.py; notes/content-plan.md "Rewards" of Gogmazios), their
 * names (ITEM text), the monsterName entry (NAME) and break rewards (BUI). Both GU item tables live in
 * loc/arc/resident.arc and <lang>/arc/resident_<lang>.arc, which UI mods replace (the user's HD UI v4 ships both),
 * so the loaded copies are patched instead of shipping arcs.
 * - rItemData (load = vt 11 0x192340): records [this+0x6c], 56 B each, count this+0x64, parsed from the 44-byte file
 *   records by 0x185694. Memory offset (file offset): +0x08 id (+0), +0x0d rarity-1 (+5), +0x0e carry (+6),
 *   +0x18 icon (+0x10), +0x19 colour (+0x11), +0x1c sell (+0x13), +0x20 buy (+0x17), +0x24 category (+0x1b).
 *   The DUMMY records are type 0 (decorations: 3), flags 0 and in no monster group (+0x26, 8 x u16) already.
 * - rGUIMessage (load 0xb839a8): path this+0x8 ("eng\table\itemData_eng"), name [this+0x8c] ("itemData"), string
 *   count +0x88, string pointers [this+0x98]: item k = name 2k, description 2k+1. Repointing them covers every reader
 *   (getter 0xb84114 and the direct ones). monsterName (268 strings): entry k = registry index k.
 * Both hooks sit on the load's common exit (`mov r0, r8; add sp, sp, #24`), r4 = this. A slot that is not DUMMY any
 * more (another mod) is left alone. Items and names apply whether the monster is installed or not (port.h). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define ITEM_REC 56
#define ITEM_DATA 20        /* ITEM section record: u16 id, u8 rarity, icon, colour, category, dummy icon, 0,
                               u32 dummy sell, sell, buy */
void gmd_text_loaded(uint8_t *m, const char *name, uint32_t lang);   /* gear.c: every TXTA append */
void ms_text_loaded(uint8_t *m, const char *name, uint32_t lang);    /* weapons/magnet_spike (MS_SLICE builds) */
void gear_tables_loaded(void *res);                                 /* gear.c: every TBLA append */
static const char *const LANGS[] = { "eng", "fre", "ger", "ita", "spa" };   /* data file text order */

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

/* 0x19237c: rItemData load done (the first data use at boot: every data file is read here). Items appended past
 * GU's 2991 (TBLA blocks, notes/items-append.md) go in first: the append replaces the record array. */
int item_data_loaded_c(uint32_t *regs)
{
    if (!FIELD(uint8_t *, regs[R4], 0x6c)) return 0;
    port_load_all();
    gear_tables_loaded((void *)regs[R4]);
    uint8_t *recs = FIELD(uint8_t *, regs[R4], 0x6c);
    uint32_t n = FIELD(uint32_t, regs[R4], 0x64);
    for (int m = 0; m < PORT_N; m++) {
        const uint8_t *s = port_section(m, "ITEM", 0, 0);
        uint32_t cnt = s ? PORT_U32(s, 0) : 0, done = 0;
        for (uint32_t i = 0; i < cnt; i++) {
            const uint8_t *it = s + 4 + ITEM_DATA * i;
            uint32_t id = FIELD(uint16_t, it, 0);
            uint8_t *r = recs + ITEM_REC * id;
            if (id >= n || FIELD(uint32_t, r, 0x08) != id || r[0x18] != it[6] ||
                FIELD(uint32_t, r, 0x1c) != PORT_U32(it, 8)) {
                logf("mh4uport: %s item %u is not a DUMMY record, left alone", port_monsters[m].name, id);
                continue;
            }
            r[0x0d] = it[2] - 1;
            r[0x0e] = 99;
            r[0x18] = it[3];
            r[0x19] = it[4];
            FIELD(uint32_t, r, 0x1c) = PORT_U32(it, 12);
            FIELD(uint32_t, r, 0x20) = PORT_U32(it, 16);
            r[0x24] = it[5];
            done++;
        }
        if (s) logf("mh4uport: item data (%u records): %u %s items set", n, done, port_monsters[m].name);
    }
    return 0;
}

/* names of the ITEM records (u32 text[lang][item][name, description] after the records) */
static void item_names(int m, const char **str, uint32_t n, uint32_t lang, const char *path)
{
    const uint8_t *s = port_section(m, "ITEM", 0, 0);
    uint32_t cnt = s ? PORT_U32(s, 0) : 0, done = 0, t = 4 + ITEM_DATA * cnt;
    for (uint32_t i = 0; i < cnt; i++) {
        uint32_t k = 2u * FIELD(uint16_t, s + 4 + ITEM_DATA * i, 0);
        if (k + 1 >= n || !str[k] || !str_eq(str[k], "DUMMY")) continue;
        str[k] = PORT_STR(s, t + 4 * (2 * (lang * cnt + i)));
        str[k + 1] = PORT_STR(s, t + 4 * (2 * (lang * cnt + i) + 1));
        done++;
    }
    if (s) logf("mh4uport: item text %s: %u %s names set", path, done, port_monsters[m].name);
}

static int is_dummy(const char *s)       /* GU's unused names 'dummy1'..'dummy7' */
{
    return s && s[0] == 'd' && s[1] == 'u' && s[2] == 'm' && s[3] == 'm' && s[4] == 'y' && s[5] >= '1' &&
           s[5] <= '9' && !s[6];
}

/* NAME: u32 monsterName entry, u32 name[lang]; replaced only while the entry still holds a dummy name */
static void monster_name(int m, const char **str, uint32_t n, uint32_t lang)
{
    const uint8_t *s = port_section(m, "NAME", 0, 0);
    if (!s) return;
    uint32_t e = PORT_U32(s, 0);
    if (e >= n || !is_dummy(str[e])) {
        logf("mh4uport: %s name entry %u is not a dummy entry, left alone", port_monsters[m].name, e);
        return;
    }
    str[e] = PORT_STR(s, 4 + 4 * lang);
    logf("mh4uport: monster name entry %u = %s", e, str[e]);
}

/* ---- items obtained (notes/items-append.md) ----
 * sItem +0x9c: 94 x u32, bit = item ID, IDs 0..3007; set 0x1943d4 / clear 0x194408 (IDs 1..2990), test 0x19443c (no
 * bound). With items appended past 2990 (PORT_ITEM_COUNT, build.py hooks them only then), IDs up to 3007 keep GU's
 * map and IDs from 3008 use the reserved zero block of the save object sUserInfo ([0x1897f78] +0x3684..+0x43f8:
 * zeroed by its initialiser 0x51cb08, copied by save / load, read by nothing else; MHGU_Editor save map). The three
 * are replaced (build.py REPLACE_HOOKS): r0 = sItem, r1 = item ID (u16, as GU's uxth / ubfx). */
#define OBTAINED_MAP 0x9c
#define OBTAINED_BITS 3008u
#define OBTAINED_EXT 0x3700u                /* sUserInfo offset of our bits (IDs 3008..), 512 bytes */
#define OBTAINED_EXT_BITS (512u * 8u)

static uint32_t *obtained_word(uint32_t sitem, uint32_t id, uint32_t *bit)
{
    *bit = 1u << (id & 31);
    if (id < OBTAINED_BITS) return &FIELD(uint32_t, sitem, OBTAINED_MAP + 4 * (id >> 5));
    uint8_t *s = *(uint8_t **)MAIN(0x1897f78);
    id -= OBTAINED_BITS;
    if (!s || id >= OBTAINED_EXT_BITS) return 0;
    *bit = 1u << (id & 31);
    return &FIELD(uint32_t, s, OBTAINED_EXT + 4 * (id >> 5));
}

static int obtained_valid(uint32_t id)       /* GU: (u16)(id - 1) <= count - 2, i.e. 1..count - 1 */
{
    return (uint16_t)(id - 1) <= PORT_ITEM_COUNT - 2u;
}

int obtained_set_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff, bit, *w = obtained_valid(id) ? obtained_word(regs[R0], id, &bit) : 0;
    if (w) *w |= bit;
    return 1;
}

int obtained_clear_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff, bit, *w = obtained_valid(id) ? obtained_word(regs[R0], id, &bit) : 0;
    if (w) *w &= ~bit;
    return 1;
}

int obtained_test_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff, bit, *w = id < PORT_ITEM_COUNT ? obtained_word(regs[R0], id, &bit) : 0;
    regs[R0] = w && (*w & bit) ? 1 : 0;      /* 0 / 1 as GU's test (`movwne r0, #1`): callers `cmp r0, #1` */
    return 1;
}

/* 0xb83c48: rGUIMessage load done */
int item_text_loaded_c(uint32_t *regs)
{
    uint8_t *msg = (uint8_t *)regs[R4];
    const char *name = FIELD(const char *, msg, 0x8c), *path = (const char *)(msg + 0x8), *suffix = 0;
    uint32_t lang = 0;
    if (!name || !FIELD(const char **, msg, 0x98)) return 0;
    for (const char *p = path; p < path + 64 && *p; p++)
        if (*p == '_') suffix = p + 1;
    for (uint32_t k = 0; suffix && k < sizeof(LANGS) / sizeof(LANGS[0]); k++)
        if (str_eq(suffix, LANGS[k])) lang = k;          /* chS / chT / others: English */
    gmd_text_loaded(msg, name, lang);                    /* gear, skill, weapon, Notes texts (gear.c) */
#ifdef MS_SLICE
    ms_text_loaded(msg, name, lang);                     /* the forge's Magnet Spike label, its class name */
#endif
    /* read the string table only now: a TXTA append (appended items' itemData) replaces it with a grown copy, and
     * names written into the old one were lost (test 2026-10-21: every DUMMY material named DUMMY) */
    const char **str = FIELD(const char **, msg, 0x98);
    uint32_t n = FIELD(uint32_t, msg, 0x88);
    for (int m = 0; m < PORT_N; m++) {
        if (str_eq(name, "itemData")) item_names(m, str, n, lang, path);
        else if (str_eq(name, "monsterName")) monster_name(m, str, n, lang);
    }
    return 0;
}

/* ---- break rewards ----
 * GU: result.arc quest\bui\bui_s<rank> (rBui: 462-byte file records -> 468-byte records, count +0x64, array +0x6c),
 * searched by monster ID at the reward screen: 0x3a3874(quest, em id) (one caller, 0x3829a0, walking the quest's
 * break list quest+0x566 {u16 em id, u8 cond, u8 count, u16}). Record: +4 u16 em id, +6 u8 cond[18], +0x18 u8
 * count[18], +0x2a entries {u8 chance, u8 count, u16 item}, each group closed by chance 255 (group lookup 0x354484).
 * cond = table 0x162a736 {10, 20, .., 60}[break group] (list adder 0x3a6f54; tail sever = 10). No GU record has a
 * ported monster's ID: the hook answers with the monster's own record, also for its save-slot ID (main.c stats_add
 * counts it under it) and for its quests' stand-in ID while they run. The rank: GU's file is bui_s<rank>, file ID
 * 0xf05f + s8 [[quest + 0xa4] + 44] (C, 0x3a3884..0x3a38cc; GU's data: s1 Low, s2 High, s4 G, e.g. Kushala's Daora
 * Horn / Horn+ / Hardhorn). The record is the monster's BUI<rank> section ('BUI2' = High ...), else its BUI section
 * (every rank: Gogmazios, Tigerstripe). */
#define BUI_REC 468
static uint8_t s_bui[PORT_N][BUI_REC];
static int8_t s_bui_rank[PORT_N];   /* rank + 1 the record was built for (0 = not built) */

static int bui_build(int m, int rank)
{
    uint8_t *b = s_bui[m];
    uint32_t size;
    const char tag[4] = {'B', 'U', 'I', (char)(rank >= 0 && rank <= 9 ? '0' + rank : ' ')};
    const uint8_t *s = port_section(m, tag, 0, &size);
    if (!s) s = port_section(m, "BUI ", 0, &size);
    if (!s) return 0;
    uint32_t groups = PORT_U32(s, 0), ents = PORT_U32(s, 4), o = 8 + ((2 * groups + 3) & ~3u);
    if (groups > 18 || 0x2a + 4 * ents > BUI_REC || o + 4 * ents > size) return 0;
    for (uint32_t k = 0; k < BUI_REC; k++) b[k] = 0;   /* another rank's record may have had more groups */
    for (uint32_t g = 0; g < groups; g++) {
        b[0x06 + g] = s[8 + g];
        b[0x18 + g] = s[8 + groups + g];
    }
    for (uint32_t e = 0; e < 4 * ents; e++) b[0x2a + e] = s[o + e];
    FIELD(uint16_t, b, 4) = port_monsters[m].em_id;
    s_bui_rank[m] = (int8_t)(rank + 1);
    return 1;
}

/* 0x3a3874(quest, em id) -> break reward record */
int bui_record_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff;
    int k = -1, q = port_running_quest(&k);
    const uint8_t *info = (const uint8_t *)FIELD(uint32_t, (void *)regs[R0], 0xa4);
    int rank = info ? (int8_t)info[44] : -1;      /* GU returns no record without it */
    for (int m = 0; m < PORT_N; m++) {
        const struct port_monster *p = &port_monsters[m];
        if (id != p->em_id && id != p->save_id && !(q == m && port_standin(m, k) && id == port_standin(m, k)))
            continue;
        if ((!FIELD(uint16_t, s_bui[m], 4) || s_bui_rank[m] != rank + 1) && !bui_build(m, rank)) return 0;
        regs[R0] = (uint32_t)s_bui[m];
        logf("mh4uport: break rewards for id %x: %s record (rank %d)", id, p->name, rank);
        return 1;
    }
    return 0;
}
