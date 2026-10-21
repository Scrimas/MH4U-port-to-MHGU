/* Ported gear (armor, skills, jewels, weapons, sharpness) as records appended to GU's loaded tables, and every text
 * append, from the monsters' data files (sections TBLA / TXTA / SKIL / PWLF, tools/portdata.py; for Gogmazios
 * monsters/gogmazios/tools/gear_em089.py and gear_weapons_em089.py, notes/content-plan.md). The tables live in
 * loc/arc/resident.arc (replaced by UI mods) and arc/facility/blacksmith.arc (v1.0 here: shipping it could undo
 * update changes), so the loaded copies grow instead.
 *
 * Every GU table class here shares one generated loader (C, checked on 10 classes): f32 version, u32 count, array
 * new[] {u32 element size, u32 count} + elements, each built by the element ctor and filled by a per-record parse
 * function from a buffered reader; count at res+0x64, array at res+0x6c; the load returns through
 * `mov r0, r8; add sp, sp, #24` at load+0x3c with r4 = res (hook site, one per class: build.py HOOKS + gear_hooks.txt).
 * tbl_append moves the elements into a larger array from the class's own allocator, runs the ctor and the GAME's
 * parser on our file-format records (a reader whose buffer holds them all plus zero padding never refills), frees the
 * old array (its elements moved, no dtor) and checks the parser consumed exactly our bytes.
 * Several monsters: their blocks are appended in registry order (allocations.toml); each block carries the count it
 * expects (TBLA base), so a table that holds another count (another mod, or a missing data file before it) is left
 * alone and no ID ever shifts. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

/* element alloc(size, align) / free(base) / ctor(e) -> e / parse(e, reader), main offsets; in-memory record size */
struct tbl_cls { uint32_t alloc, free, ctor, parse; uint16_t size; };
typedef uint8_t *(*tbl_alloc_t)(uint32_t size, uint32_t align);
typedef void (*tbl_free_t)(void *base);
typedef void *(*tbl_ctor_t)(void *e);
typedef void (*tbl_parse_t)(void *e, void *reader);

/* buffered reader (ctor 0x8260d4): vtable, source stream, buffer, position, filled size, capacity */
struct reader { uint32_t vt; void *src; uint8_t *buf; uint32_t pos, size, cap; };
#define READER_VT MAIN(0x1787ad0 + 8)
#define PAD 64
static uint8_t s_buf[4096];

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

static int path_ends(void *res, const char *suffix)
{
    const char *p = (const char *)res + 0x8;
    uint32_t lp = 0, ls = 0;
    while (lp < 64 && p[lp]) lp++;
    while (suffix[ls]) ls++;
    return ls <= lp && str_eq(p + lp - ls, suffix);
}

static int tbl_append(void *res, const struct tbl_cls *c, const uint8_t *recs, uint32_t n, uint32_t rec_bytes,
                      uint32_t expect, const char *what)
{
    uint32_t count = FIELD(uint32_t, res, 0x64), len = n * rec_bytes, i;
    uint8_t *old = FIELD(uint8_t *, res, 0x6c), *base, *arr;
    if (count != expect || !old || len + PAD > sizeof s_buf) {
        logf("mh4uport: gear %s: table has %u records, expected %u: nothing appended", what, count, expect);
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
        logf("mh4uport: gear %s: the parser read %u bytes of %u, append undone", what, r.pos, len);
        FN(tbl_free_t, c->free)(base);
        return 0;
    }
    FN(tbl_free_t, c->free)(old - 8);
    FIELD(uint8_t *, res, 0x6c) = arr;
    FIELD(uint32_t, res, 0x64) = count + n;
    logf("mh4uport: gear %s: %u -> %u records", what, count, count + n);
    return 1;
}

/* TBLA entry (40 B): path, flags, alloc, free, ctor, parse, u16 mem size, u16 record bytes, base, count, records */
#define TBL_KIREAJI 1u          /* the sharpness table */
#define TBL_NEEDS_KIREAJI 2u    /* LevelData rows use the monster's sharpness entries: skipped if those were refused */
static int s_kire[PORT_N];      /* 0 not loaded, 1 appended, -1 refused */

void gear_tables_loaded(void *res)        /* also items.c: the item table's TBLA blocks (appended items) */
{
    for (int m = 0; m < PORT_N; m++) {
        const uint8_t *s;
        for (int k = 0; (s = port_section(m, "TBLA", k, 0)) != 0; k++) {
            for (uint32_t i = 0, n = PORT_U32(s, 0); i < n; i++) {
                const uint8_t *t = s + 4 + 40 * i;
                const char *path = (const char *)s + PORT_U32(t, 0);     /* offsets are section-relative */
                if (!path_ends(res, path)) continue;
                uint32_t flags = PORT_U32(t, 4);
                if ((flags & TBL_NEEDS_KIREAJI) && s_kire[m] < 0) {
                    logf("mh4uport: gear %s: %s sharpness refused, its levels not appended", path, port_monsters[m].name);
                    continue;
                }
                struct tbl_cls c = {PORT_U32(t, 8), PORT_U32(t, 12), PORT_U32(t, 16), PORT_U32(t, 20),
                                    FIELD(uint16_t, t, 24)};
                int ok = tbl_append(res, &c, s + PORT_U32(t, 36), PORT_U32(t, 32), FIELD(uint16_t, t, 26),
                                    PORT_U32(t, 28), path);
                if (flags & TBL_KIREAJI) s_kire[m] = ok ? 1 : -1;
            }
        }
    }
}

/* one load-exit hook per table class: armor (build.py HOOKS) and weapons / sharpness (gear_hooks.txt) */
#define GEAR_HOOK(name) int name##_c(uint32_t *regs) { gear_tables_loaded((void *)regs[R4]); return 0; }
GEAR_HOOK(gear_armor_series)     /* 0x129994 rArmorSeriesData */
GEAR_HOOK(gear_armor_create)     /* 0x4bfee0 rArmorCreateData (armorCreateA00..A04) */
GEAR_HOOK(gear_armor_process)    /* 0x4c0360 rArmorProcessData */
GEAR_HOOK(gear_skill_type)       /* 0x4cee64 rSkillTypeData */
GEAR_HOOK(gear_skill)            /* 0x4ce98c rSkillData */
GEAR_HOOK(gear_deco)             /* 0x191a20 rDecoData: record k = item 2638 + k (getter 0x194230 up to 2899, bound =
                                    the loaded count 0x191bd4; the decoration lists loop over that count 0x195264) */
GEAR_HOOK(gear_deco_create)      /* 0x4c0cb0 rDecoCreateData (the smithy's decoration bits: save, 288) */
#include "gear_hooks.inc"        /* build.py: GEAR_HOOK(name) for each line of gear_hooks.txt */

/* names: rGUIMessage string pointers [m+0x98], count m+0x88 (items.c); the larger array comes from the resource's
 * own allocator (vt+0x40, as the load uses), the old one stays allocated (a few KB, resident tables) */
typedef void *(*res_alloc_t)(void *res, uint32_t size);
static void gmd_append(uint8_t *m, uint32_t expect, const uint8_t *sec, const uint8_t *offs, uint32_t n,
                       const char *what)
{
    uint32_t count = FIELD(uint32_t, m, 0x88), i;
    const char **old = FIELD(const char **, m, 0x98), **arr;
    if (count != expect || !old) {
        logf("mh4uport: text %s: %u strings, expected %u: nothing appended", what, count, expect);
        return;
    }
    arr = ((res_alloc_t)(*(uint32_t **)m)[0x40 / 4])(m, (count + n) * 4);
    if (!arr) return;
    for (i = 0; i < count; i++) arr[i] = old[i];
    for (i = 0; i < n; i++) arr[count + i] = (const char *)sec + PORT_U32(offs, 4 * i);
    FIELD(const char **, m, 0x98) = arr;
    FIELD(uint32_t, m, 0x88) = count + n;
    logf("mh4uport: text %s: %u -> %u strings", what, count, count + n);
}

/* called by items.c for every rGUIMessage load (name = GMD internal name, lang = data file language index).
 * TXTA entry (16 B): GMD name, base (expected string count), count, strings (u32 offsets [5][count]) */
void gmd_text_loaded(uint8_t *msg, const char *name, uint32_t lang)
{
    for (int m = 0; m < PORT_N; m++) {
        const uint8_t *s;
        for (int k = 0; (s = port_section(m, "TXTA", k, 0)) != 0; k++)
            for (uint32_t i = 0, n = PORT_U32(s, 0); i < n; i++) {
                const uint8_t *t = s + 4 + 16 * i;
                if (!str_eq(name, (const char *)s + PORT_U32(t, 0))) continue;
                uint32_t cnt = PORT_U32(t, 8);
                gmd_append(msg, PORT_U32(t, 4), s, s + PORT_U32(t, 12) + 4 * cnt * lang, cnt, name);
            }
    }
}

/* 0x272910: rPlayerWeaponList (weapon\wNN\pwl\pl_wNN) load exit. One 20-B record per model number, +4 mGmkMotNo =
 * the weapon motion set (arc/weapon/wNN/gNN.arc; 4U's per-model gimmick byte). PWLF entry (8 B): path suffix, u16
 * model, u8 GU value, u8 ours (the data file says why, e.g. gear_weapons_em089.py PWL_FIX). */
int gear_pwl_c(uint32_t *regs)
{
    uint8_t *res = (uint8_t *)regs[R4], *recs = FIELD(uint8_t *, res, 0x6c);
    uint32_t n = FIELD(uint32_t, res, 0x64);
    for (int m = 0; m < PORT_N; m++) {
        const uint8_t *s = port_section(m, "PWLF", 0, 0);
        for (uint32_t i = 0, cnt = s ? PORT_U32(s, 0) : 0; i < cnt; i++) {
            const uint8_t *f = s + 4 + 8 * i;
            uint32_t model = FIELD(uint16_t, f, 4), from = f[6], to = f[7];
            if (!path_ends(res, (const char *)s + PORT_U32(f, 0))) continue;
            uint32_t *mot = recs && model < n ? &FIELD(uint32_t, recs, 20 * model + 4) : 0;
            if (mot && *mot == from) *mot = to;
            logf("mh4uport: gear %s model %u: motion set %d (expected %u -> %u)", (const char *)s + PORT_U32(f, 0),
                 model, mot ? (int)*mot : -1, from, to);
        }
    }
    return 0;
}

/* 0xe0da0(skills, id) -> has skill: bit id of [skills+0x188]+0x3dc (11 words, 352 bits, C). GU combined skills are
 * explicit ORs at each check site (e.g. 0x2fb854: 217 || 319); a ported compound skill (SKIL entry 16 B: skill,
 * grants[3], 0xffffffff = none) answers yes for the GU skills it grants (Gogmazios: Enlightened Blade = Element Atk
 * Up 76 + Status Atk +1 79; GU has no Awaken). */
int gear_has_skill_c(uint32_t *regs)
{
    for (int m = 0; m < PORT_N; m++) {
        const uint8_t *s = port_section(m, "SKIL", 0, 0);
        for (uint32_t i = 0, cnt = s ? PORT_U32(s, 0) : 0; i < cnt; i++) {
            const uint8_t *e = s + 4 + 16 * i;
            uint32_t skill = PORT_U32(e, 0);
            if (PORT_U32(e, 4) != regs[R1] && PORT_U32(e, 8) != regs[R1] && PORT_U32(e, 12) != regs[R1]) continue;
            uint8_t *o = FIELD(uint8_t *, regs[R0], 0x188);
            if (!o || skill >= 352 || !(FIELD(uint32_t, o, 0x3dc + 4 * (skill / 32)) & (1u << (skill % 32)))) continue;
            regs[R0] = 1;
            return 1;
        }
    }
    return 0;
}
