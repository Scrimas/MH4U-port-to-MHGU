/* Gogma armor and the Arcana skill as records appended to GU's loaded tables (tools/gear_em089.py ->
 * gear_em089.inc; notes/content-plan.md). The tables live in loc/arc/resident.arc (replaced by UI mods) and
 * arc/facility/blacksmith.arc (v1.0 here: shipping it could undo update changes), so the loaded copies grow instead.
 *
 * Every GU table class here shares one generated loader (C, checked on 10 classes): f32 version, u32 count, array
 * new[] {u32 element size, u32 count} + elements, each built by the element ctor and filled by a per-record parse
 * function from a buffered reader; count at res+0x64, array at res+0x6c; the load returns through
 * `mov r0, r8; add sp, sp, #24` at load+0x3c with r4 = res (hook site). tbl_append moves the elements into a larger
 * array from the class's own allocator, runs the ctor and the GAME's parser on our file-format records (a reader whose
 * buffer holds them all plus zero padding never refills), frees the old array (its elements moved, no dtor) and
 * checks the parser consumed exactly our bytes. A table whose count is not the expected v1.0 one is left alone. */
#include <stdint.h>
#include "util.h"
#include "game.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#include "gear_em089.inc"

/* element alloc(size, align) / free(base) / ctor(e) -> e / parse(e, reader), main offsets; in-memory record size */
struct tbl_cls { uint32_t alloc, free, ctor, parse; uint16_t size; };
static const struct tbl_cls CLS_ARMOR_SERIES  = {0xd4768, 0xd47a4, 0xd47d0, 0xd75fc, 140};
static const struct tbl_cls CLS_ARMOR_CREATE  = {0x4a7f4c, 0x4a7f88, 0x4a7fb4, 0x4a8c68, 48};
static const struct tbl_cls CLS_ARMOR_PROCESS = {0x4a94f8, 0x4a9534, 0x4a9560, 0x4aa02c, 44};
static const struct tbl_cls CLS_SKILL_TYPE    = {0x4cd4e0, 0x4cd51c, 0x4cd548, 0x4cda28, 24};
static const struct tbl_cls CLS_SKILL         = {0x4cc3fc, 0x4cc438, 0x4cc464, 0x4ccc10, 24};
static const struct tbl_cls CLS_DECO          = {0x184140, 0x18417c, 0x1841a8, 0x184484, 12};
static const struct tbl_cls CLS_DECO_CREATE   = {0x4aacd4, 0x4aad10, 0x4aad3c, 0x4ab294, 20};

typedef uint8_t *(*tbl_alloc_t)(uint32_t size, uint32_t align);
typedef void (*tbl_free_t)(void *base);
typedef void *(*tbl_ctor_t)(void *e);
typedef void (*tbl_parse_t)(void *e, void *reader);

/* buffered reader (ctor 0x8260d4): vtable, source stream, buffer, position, filled size, capacity */
struct reader { uint32_t vt; void *src; uint8_t *buf; uint32_t pos, size, cap; };
#define READER_VT MAIN(0x1787ad0 + 8)
#define PAD 64
static uint8_t s_buf[2048];

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

static int path_is(void *res, const char *path)
{
    return str_eq((const char *)res + 0x8, path);
}

static int tbl_append(void *res, const struct tbl_cls *c, const uint8_t *recs, uint32_t n, uint32_t rec_bytes,
                      uint32_t expect, const char *what)
{
    uint32_t count = FIELD(uint32_t, res, 0x64), len = n * rec_bytes, i;
    uint8_t *old = FIELD(uint8_t *, res, 0x6c), *base, *arr;
    if (count != expect || !old || len + PAD > sizeof s_buf) {
        logf("gogport: gear %s: table has %u records, expected %u: nothing appended", what, count, expect);
        return 0;
    }
    base = FN(tbl_alloc_t, c->alloc)((count + n) * c->size + 8, 16);
    if (!base) return 0;
    FIELD(uint32_t, base, 0) = c->size;
    FIELD(uint32_t, base, 4) = count + n;
    arr = base + 8;
    for (i = 0; i < count * c->size; i++) arr[i] = old[i];
    for (i = 0; i < len; i++) s_buf[i] = recs[i];
    for (; i < len + PAD; i++) s_buf[i] = 0;
    struct reader r = {READER_VT, 0, s_buf, 0, len + PAD, len + PAD};
    for (i = 0; i < n; i++) {
        uint8_t *e = arr + (count + i) * c->size;
        FN(tbl_ctor_t, c->ctor)(e);
        FN(tbl_parse_t, c->parse)(e, &r);
    }
    if (r.pos != len) {          /* record layout wrong: keep the game's table */
        logf("gogport: gear %s: the parser read %u bytes of %u, append undone", what, r.pos, len);
        FN(tbl_free_t, c->free)(base);
        return 0;
    }
    FN(tbl_free_t, c->free)(old - 8);
    FIELD(uint8_t *, res, 0x6c) = arr;
    FIELD(uint32_t, res, 0x64) = count + n;
    logf("gogport: gear %s: %u -> %u records", what, count, count + n);
    return 1;
}

/* 0x129994: rArmorSeriesData load exit */
int gear_armor_series_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\armorSeriesData"))
        tbl_append(res, &CLS_ARMOR_SERIES, gear_armor_series, 2, 127, GEAR_SERIES_FIRST, "armor series");
    return 0;
}

/* 0x4bfee0: rArmorCreateData load exit (armorCreateA00..A04, one per part) */
int gear_armor_create_c(uint32_t *regs)
{
    static const char prefix[] = "table\\armorCreateA0";
    const char *path = (const char *)regs[R4] + 0x8;
    uint32_t i = 0, part;
    while (prefix[i] && path[i] == prefix[i]) i++;
    if (prefix[i] || path[i] < '0' || path[i] > '4' || path[i + 1]) return 0;
    part = (uint32_t)(path[i] - '0');
    tbl_append((void *)regs[R4], &CLS_ARMOR_CREATE, gear_armor_create[part], 1, 42, gear_create_count[part],
               "armor recipe");
    return 0;
}

/* 0x4c0360: rArmorProcessData load exit */
int gear_armor_process_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\armorProcessA00"))
        tbl_append(res, &CLS_ARMOR_PROCESS, gear_armor_process[0], GEAR_ARMOR_LEVELS, 38, GEAR_PROCESS_COUNT,
                   "armor levels");
    return 0;
}

/* 0x4cee64 / 0x4ce98c: rSkillTypeData / rSkillData load exits: the Arcana tree, Enlightened Blade */
int gear_skill_type_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\skillTypeData"))
        tbl_append(res, &CLS_SKILL_TYPE, gear_skilltype, 1, 19, GEAR_TREE_ID, "skill tree");
    return 0;
}

int gear_skill_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\skillData"))
        tbl_append(res, &CLS_SKILL, gear_skill, 1, 18, GEAR_SKILL_ID, "skill");
    return 0;
}

/* 0x191a20 / 0x4c0cb0: rDecoData / rDecoCreateData load exits: the Arcane jewels (items 2889.., items.c). decoData
 * record k = item 2638 + k; its getter 0x194230 accepts items up to 2899 and checks k against the loaded count
 * (0x191bd4), and the decoration lists loop over that count (0x195264). The smithy's decoration bits (save, 288)
 * hold the 4 recipes past GU's 275. */
int gear_deco_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\decoData"))
        tbl_append(res, &CLS_DECO, gear_deco, GEAR_DECOS, 5, GEAR_DECO_COUNT, "decorations");
    return 0;
}

int gear_deco_create_c(uint32_t *regs)
{
    void *res = (void *)regs[R4];
    if (path_is(res, "table\\decoCreate"))
        tbl_append(res, &CLS_DECO_CREATE, gear_deco_create, GEAR_DECOS, 16, GEAR_DECO_CREATE_COUNT,
                   "decoration recipes");
    return 0;
}

/* names: rGUIMessage string pointers [m+0x98], count m+0x88 (items.c); the larger array comes from the resource's
 * own allocator (vt+0x40, as the load uses), the old one stays allocated (a few KB, resident tables) */
typedef void *(*res_alloc_t)(void *res, uint32_t size);
void gmd_append(uint8_t *m, uint32_t expect, const char *const *strs, uint32_t n, const char *what)   /* + notes.c */
{
    uint32_t count = FIELD(uint32_t, m, 0x88), i;
    const char **old = FIELD(const char **, m, 0x98), **arr;
    if (count != expect || !old) {
        logf("gogport: gear %s: %u strings, expected %u: nothing appended", what, count, expect);
        return;
    }
    arr = ((res_alloc_t)(*(uint32_t **)m)[0x40 / 4])(m, (count + n) * 4);
    if (!arr) return;
    for (i = 0; i < count; i++) arr[i] = old[i];
    for (i = 0; i < n; i++) arr[count + i] = strs[i];
    FIELD(const char **, m, 0x98) = arr;
    FIELD(uint32_t, m, 0x88) = count + n;
    logf("gogport: gear %s: %u -> %u strings", what, count, count + n);
}

/* ---- weapons (tools/gear_weapons_em089.py -> gear_weapons_em089.inc): tables by resource path suffix (the
 * per-language name index tables share one entry), one load-exit hook per table class (module/gear_hooks.txt) ---- */
struct gear_tbl { const char *path; uint32_t alloc, free, ctor, parse; uint16_t size, rec_bytes, expect, n;
                  const uint8_t *recs; };
struct gear_text { const char *name; uint16_t expect, n; const char *const *strs[5]; };
static void gear_tables_loaded(void *res) __attribute__((unused));   /* unused without the weapon .inc */
#define GEAR_HOOK(name) int name##_c(uint32_t *regs) { gear_tables_loaded((void *)regs[R4]); return 0; }
#if __has_include("gear_weapons_em089.inc")
#include "gear_weapons_em089.inc"
#else
static const struct gear_tbl gear_weapon_tables[1];
static const struct gear_text gear_weapon_text[1];
#define GEAR_WEAPON_TABLES 0u
#define GEAR_WEAPON_TEXTS 0u
#endif

static int path_ends(void *res, const char *suffix)
{
    const char *p = (const char *)res + 0x8;
    uint32_t lp = 0, ls = 0;
    while (lp < 64 && p[lp]) lp++;
    while (suffix[ls]) ls++;
    return ls <= lp && str_eq(p + lp - ls, suffix);
}

/* the LevelData rows use the sharpness entries kireajiData 164..166 that we append: a refused kireaji append (count
 * changed by another mod) would leave them out of range, so later LevelData appends are skipped too. */
static void gear_tables_loaded(void *res)
{
    static int s_kire;       /* 0 not loaded, 1 appended, -1 refused */
    for (uint32_t i = 0; i < GEAR_WEAPON_TABLES; i++) {
        const struct gear_tbl *t = &gear_weapon_tables[i];
        if (!path_ends(res, t->path)) continue;
        int kire = path_ends(res, "kireajiData");
        if (!kire && path_ends(res, "LevelData") && s_kire < 0) {
            logf("gogport: gear %s: kireaji append refused, Gogma levels not appended", t->path);
            return;
        }
        struct tbl_cls c = {t->alloc, t->free, t->ctor, t->parse, t->size};
        int ok = tbl_append(res, &c, t->recs, t->n, t->rec_bytes, t->expect, t->path);
        if (kire) s_kire = ok ? 1 : -1;
        return;
    }
}

/* 0x272910: rPlayerWeaponList (weapon\wNN\pwl\pl_wNN) load exit. One 20-B record per model number, +4 mGmkMotNo =
 * the weapon motion set (arc/weapon/wNN/gNN.arc; 4U's per-model gimmick byte, equal on the shared models). Every
 * Gogma model number already has a record carrying 4U's value, except two (tools/weapon4u2gu.py report):
 * HBG 40: GU 1 (g01 serves only GU model 22, another skeleton) -> 4U 0 = g00, used by 69 HBGs with hbg040's bones;
 * SA 77: 8 (GU has no g08.arc) -> 20, the set of all 20 GU axes with axe077's 4-bone skeleton. */
static const struct { const char *path; uint16_t model; uint8_t from, to; } k_pwl_fix[] = {
    {"pl_w04", 40, 1, 0}, {"pl_w08", 77, 8, 20},
};
int gear_pwl_c(uint32_t *regs)
{
    uint8_t *res = (uint8_t *)regs[R4], *recs = FIELD(uint8_t *, res, 0x6c);
    uint32_t n = FIELD(uint32_t, res, 0x64);
    for (uint32_t i = 0; i < sizeof k_pwl_fix / sizeof k_pwl_fix[0]; i++) {
        if (!path_ends(res, k_pwl_fix[i].path)) continue;
        uint32_t *mot = recs && k_pwl_fix[i].model < n ? &FIELD(uint32_t, recs, 20 * k_pwl_fix[i].model + 4) : 0;
        if (mot && *mot == k_pwl_fix[i].from) *mot = k_pwl_fix[i].to;
        logf("gogport: gear %s model %u: motion set %d (expected %u -> %u)", k_pwl_fix[i].path, k_pwl_fix[i].model,
             mot ? (int)*mot : -1, k_pwl_fix[i].from, k_pwl_fix[i].to);
    }
    return 0;
}

/* called by items.c for every rGUIMessage load (name = GMD internal name, lang = items.c language index) */
void gear_text_loaded(uint8_t *m, const char *name, uint32_t lang)
{
    for (uint32_t i = 0; i < GEAR_WEAPON_TEXTS; i++)
        if (str_eq(name, gear_weapon_text[i].name)) {
            gmd_append(m, gear_weapon_text[i].expect, gear_weapon_text[i].strs[lang], gear_weapon_text[i].n, name);
            return;
        }
    if (str_eq(name, "armorSeriesData"))
        gmd_append(m, GEAR_SERIES_FIRST * 10, gear_armor_text[lang], 20, "armor names");
    else if (str_eq(name, "skillTypeData"))
        gmd_append(m, GEAR_TREE_ID * 2, gear_skill_text[lang], 2, "skill tree names");
    else if (str_eq(name, "skillData"))
        gmd_append(m, GEAR_SKILL_ID * 2, gear_skill_text[lang] + 2, 2, "skill names");
}

/* 0xe0da0(skills, id) -> has skill: bit id of [skills+0x188]+0x3dc (11 words, 352 bits, C). GU combined skills are
 * explicit ORs at each check site (e.g. 0x2fb854: 217 || 319); Enlightened Blade (4U: Awaken + Element Atk Up +
 * Status Atk Up) answers yes for Element Atk Up (76) and Status Atk +1 (79). GU has no Awaken. */
#define SKILL_ELEMENT_UP 76u
#define SKILL_STATUS_UP1 79u
int gear_has_skill_c(uint32_t *regs)
{
    uint8_t *o;
    if (regs[R1] != SKILL_ELEMENT_UP && regs[R1] != SKILL_STATUS_UP1) return 0;
    o = FIELD(uint8_t *, regs[R0], 0x188);
    if (!o || !(FIELD(uint32_t, o, 0x3dc + 4 * (GEAR_SKILL_ID / 32)) & (1u << (GEAR_SKILL_ID % 32)))) return 0;
    regs[R0] = 1;
    return 1;
}
