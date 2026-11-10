/* savefile.c: the mod's own save files in the game (notes/mod-save-format.md "In the module"; modsave.c does the
 * split and the merge). GU's save image is the save scene's buffer (5,159,064 B: the 3 slots' offsets at +0x10 + 4k,
 * their used bytes at +4..+6, C: NEWSAVE R1). Every path between a live character and its slot's bytes goes through
 * 0x3e0ea4 (pack) and 0x3e0db8 (parse), and every file goes through the save thread's write 0x877c20 / read 0x8778cc.
 *
 * - pack (0x3e0ea4 entry): the slot is marked; the image stays complete.
 * - write (0x877c58, mounted): for a marked slot of the image being written, the split; its file written whole (in
 *   the commit GU makes after its own write), then the slot cleaned in place, link record "split". If the file can't
 *   be written, the slot stays complete and its link record says "full" (today's layout; the next save tries again).
 *   One file per GU write at most: a second changed slot stays complete this time (the journal holds about 5 blocks
 *   past GU's own file).
 * - read (0x877b60, still mounted): after GU read `system` (or `system_backup`, which GU writes from the same buffer
 *   and reads when `system` is damaged), each slot's file goes to a cache, which then mirrors the file on disk (the
 *   write updates it); the image's marks are dropped (they never split bytes that came from disk).
 * - parse (0x3e0db8 entry / 0x3e0e64): a slot whose link says "split" gets its cached file merged in before GU parses
 *   it, and is put back as read right after (the journal), so a later write of that buffer is still clean.
 * - A slot whose file exists but could not be read, checked or merged this session never has that file overwritten
 *   (s_keep stays set until the game closes, whatever a later read finds). */
#include "port.h"
#include "game.h"
#include "util.h"
#include "modsave.h"
#include "modsave_quests.h"         /* module/build.py: MS_QUESTS[], MS_QUEST_N (tools/modsave.py quest_bits) */

enum { R0, R1, R2, R3, R4, R5, R12, LR };

typedef struct { void *h; } fs_file;
typedef uint32_t (*fs_open_t)(fs_file *out, const char *path, int mode);
typedef uint32_t (*fs_create_t)(const char *path, int64_t size);
typedef uint32_t (*fs_size_t)(int64_t *out, fs_file f);
typedef uint32_t (*fs_read_t)(uint32_t *out, fs_file f, int64_t offset, void *buf, uint32_t size);
typedef uint32_t (*fs_write_t)(fs_file f, int64_t offset, const void *buf, uint32_t size, const int *option);
typedef uint32_t (*fs_flush_t)(fs_file f);
typedef void (*fs_close_t)(fs_file f);
#define fs_open FN(fs_open_t, 0x13f04b4)       /* nn::fs::OpenFile (1 read, 2 write) */
#define fs_create FN(fs_create_t, 0x13f04a8)   /* nn::fs::CreateFile(path, size) */
#define fs_size FN(fs_size_t, 0x13f043c)
#define fs_read FN(fs_read_t, 0x13f0448)
#define fs_write FN(fs_write_t, 0x13f0454)     /* nn::fs::WriteFile(handle, offset, buf, size, const WriteOption &) */
#define fs_flush FN(fs_flush_t, 0x13f0460)
#define fs_close FN(fs_close_t, 0x13f046c)

#define IMAGE_SIZE 0x4EB898u
#define SLOTS 3
#define JOURNAL (96u * 1024u)
#define ASIDE_CAP 2048u

static const struct ms_quest s_quests[] = MS_QUESTS;

static uint8_t s_cache[SLOTS][MS_FILE_SIZE], s_out[MS_FILE_SIZE], s_journal[JOURNAL], s_aside[SLOTS][ASIDE_CAP];
static uint32_t s_cache_n[SLOTS];          /* bytes read (0: no file) */
static uint8_t s_cache_state[SLOTS];       /* 0 none, 1 read, 2 could not be read (keep it) */
static uint8_t s_keep[SLOTS];              /* this session never overwrites that slot's file */
static uint32_t s_aside_n[SLOTS], s_link[SLOTS], s_gen[SLOTS], s_body[SLOTS];   /* s_body: FNV of the last file's records */
static volatile uint32_t s_marked_image;   /* the image whose slots s_marked holds */
static volatile uint8_t s_marked[SLOTS];
static uint8_t *s_merged;                  /* the slot a parse merged into (put back at 0x3e0e64) */
static uint32_t s_merged_k, s_jlen;

static void path_of(char *p, uint32_t k)   /* GU's own form: savedata:\system */
{
    const char *s = "savedata:\\mhgu_de_";
    while (*s) *p++ = *s++;
    *p++ = (char)('1' + k);
    s = ".bin";
    while (*s) *p++ = *s++;
    *p = 0;
}

static int name_is(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

/* slot k of an image whose slot starts at ptr, or -1 */
static int slot_of(uint32_t base, uint32_t ptr)
{
    if (!base || ptr < base || ptr >= base + IMAGE_SIZE) return -1;
    for (int k = 0; k < SLOTS; k++) {
        uint32_t off = FIELD(uint32_t, base, 0x10 + 4 * k);
        if (off && off + MS_SLOT_SIZE <= IMAGE_SIZE && base + off == ptr) return k;
    }
    return -1;
}

static uint8_t *slot_ptr(uint32_t base, int k)
{
    uint32_t off = FIELD(uint32_t, base, 0x10 + 4 * k);
    return off && off + MS_SLOT_SIZE <= IMAGE_SIZE ? (uint8_t *)(uintptr_t)(base + off) : 0;
}

static uint32_t tick(void)
{
    register uint32_t r0 __asm__("r0"), r1 __asm__("r1");
    __asm__ volatile("svc #0x1e" : "=r"(r0), "=r"(r1) : : "memory");
    return r0 ^ (r1 << 7);
}

static uint32_t us_since(uint32_t t0)      /* the system tick runs at 19.2 MHz */
{
    register uint32_t r0 __asm__("r0"), r1 __asm__("r1");
    __asm__ volatile("svc #0x1e" : "=r"(r0), "=r"(r1) : : "memory");
    (void)r1;
    return (r0 - t0) / 192u * 10u;
}

static uint32_t tick0(void)
{
    register uint32_t r0 __asm__("r0"), r1 __asm__("r1");
    __asm__ volatile("svc #0x1e" : "=r"(r0), "=r"(r1) : : "memory");
    (void)r1;
    return r0;
}

/* ---------------------------------------------------------------------------------------------- pack */

/* 0x3e0ea4(scene, stream {vtable, bit, pointer, image}, flag): one character packed into its slot */
int save_pack_c(uint32_t *regs)
{
    uint32_t st = regs[R1], base = st ? FIELD(uint32_t, st, 12) : 0;
    int k = st ? slot_of(base, FIELD(uint32_t, st, 8)) : -1;
    if (k < 0) return 0;
    if (s_marked_image != base) {
        for (int j = 0; j < SLOTS; j++) s_marked[j] = 0;
        s_marked_image = base;
    }
    s_marked[k] = 1;
    return 0;
}

/* ---------------------------------------------------------------------------------------------- write */

static int write_file(uint32_t k, const uint8_t *f, uint32_t n)
{
    char path[40];
    fs_file h;
    int opt = 0;
    path_of(path, k);
    if (fs_open(&h, path, 2)) {
        uint32_t r = fs_create(path, MS_FILE_SIZE);
        if (r || fs_open(&h, path, 2)) {
            logf("mhgu-de: save: slot %u: %s could not be created (%x)", k + 1, path, r);
            return 0;
        }
    }
    uint32_t r = fs_write(h, 0, f, n, &opt);
    if (!r) r = fs_flush(h);
    fs_close(h);
    if (r) logf("mhgu-de: save: slot %u: writing %s failed (%x)", k + 1, path, r);
    return !r;
}

/* 0x877c58 (r4 = the save manager, savedata mounted): GU is about to write its fields to the file named at +0xe98 */
int save_write_c(uint32_t *regs)
{
    uint32_t mgr = regs[R4];
    if (!mgr || FIELD(int32_t, mgr, 0xcc4) < 1 || FIELD(uint32_t, mgr, 0x4c) != 0xc || FIELD(uint32_t, mgr, 0x48) != IMAGE_SIZE)
        return 0;
    uint32_t base = FIELD(uint32_t, mgr, 0x44);
    const char *name = (const char *)(uintptr_t)(mgr + 0xe98);
    if (!base || base != s_marked_image) return 0;
    int written = 0;
    for (uint32_t k = 0; k < SLOTS; k++) {
        if (!s_marked[k]) continue;
        s_marked[k] = 0;
        uint8_t *slot = slot_ptr(base, (int)k);
        if (!slot || !FIELD(uint8_t, base, 4 + k)) continue;
        uint32_t link, gen, state, left = 0, has_file = s_cache_n[k] || s_body[k];
        if (s_keep[k]) {                            /* the live character lacks that file's things: touch nothing */
            logf("mhgu-de: save: slot %u: its file could not be read this session: slot and file left as they are", k + 1);
            continue;
        }
        if (!ms_link(slot, &link, &gen, &state)) link = s_link[k], gen = s_gen[k];
        if (!link) link = (tick() * 2654435761u ^ (k + 1) * 0x9E3779B9u) | 1u;
        if (gen < s_gen[k]) gen = s_gen[k];
        uint32_t t0 = tick0();
        int n = ms_split(slot, s_quests, MS_QUEST_N, link, gen + 1, s_aside[k], s_aside_n[k], s_out, MS_FILE_SIZE, 0, &left);
        if (n < 0) {
            logf("mhgu-de: save: slot %u: not split (the hunter holds an added weapon and the box has no room): full", k + 1);
            ms_set_link(slot, link, gen, MS_FULL);
            continue;
        }
        if (n == (int)MS_HEADER && !has_file) continue;   /* nothing added, no file: GU's slot is already vanilla */
        uint32_t body = ms_fnv(s_out + MS_HEADER, (uint32_t)n - MS_HEADER, link);
        int need = !has_file || body != s_body[k];
        if (need && written) {
            logf("mhgu-de: save: slot %u: a second file in one commit: the slot stays full until its next save", k + 1);
            ms_set_link(slot, link, gen, MS_FULL);
            continue;
        }
        n = ms_split(slot, s_quests, MS_QUEST_N, link, gen + 1, s_aside[k], s_aside_n[k], s_out, MS_FILE_SIZE, 1, &left);
        if (need && !write_file(k, s_out, (uint32_t)n)) {
            struct ms_stats st;                     /* everything back into the slot: it stays full */
            uint32_t jl, al;
            int r = ms_merge(slot, s_out, (uint32_t)n, s_quests, MS_QUEST_N, s_journal, JOURNAL, &jl, s_aside[k],
                             ASIDE_CAP, &al, &st);
            ms_set_link(slot, link, gen, MS_FULL);
            if (!r) s_aside_n[k] = al;
            logf("mhgu-de: save: slot %u: file not written before %s: the slot keeps everything (merge %d, %u placed, "
                 "%s)", k + 1, name, r, st.placed, st.exact ? "exact" : "NOT exact");
            continue;
        }
        written |= need;
        if (need) {                                 /* the cache mirrors the file: a parse later this session merges it */
            for (uint32_t i = 0; i < (uint32_t)n; i++) s_cache[k][i] = s_out[i];
            s_cache_state[k] = 1;
        }
        s_cache_n[k] = (uint32_t)n;
        s_body[k] = body;
        s_link[k] = link;
        s_gen[k] = gen + 1;
        s_aside_n[k] = 0;
        logf("mhgu-de: save: slot %u split before %s: %u of %u bytes (link %x, generation %u, slot hash %x), %u "
             "record(s) left in the slot by the budget, file %s, %u us", k + 1, name, (uint32_t)n, MS_FILE_SIZE, link,
             gen + 1, FIELD(uint32_t, s_out, 24), left, need ? "written" : "unchanged", us_since(t0));
    }
    return 0;
}

/* ---------------------------------------------------------------------------------------------- read */

/* 0x877b60 (r4 = the save manager, still mounted): GU's read of the file named at +0xe98 ended, result at +0x24 */
int save_read_c(uint32_t *regs)
{
    uint32_t mgr = regs[R4];
    if (!mgr || FIELD(int32_t, mgr, 0xcc4) < 1 || FIELD(uint32_t, mgr, 0x48) != IMAGE_SIZE) return 0;
    uint32_t base = FIELD(uint32_t, mgr, 0x44);
    if (base == s_marked_image) {
        for (int j = 0; j < SLOTS; j++) s_marked[j] = 0;
        s_marked_image = 0;
    }
    const char *name = (const char *)(uintptr_t)(mgr + 0xe98);
    if (FIELD(uint32_t, mgr, 0x24) || !(name_is(name, "system") || name_is(name, "system_backup"))) return 0;
    for (uint32_t k = 0; k < SLOTS; k++) {
        char path[40];
        fs_file h;
        int64_t size = 0;
        uint32_t got = 0;
        path_of(path, k);
        s_cache_n[k] = 0;
        s_cache_state[k] = 0;
        s_body[k] = 0;
        uint32_t r = fs_open(&h, path, 1);
        if (r) {                                       /* no file (a used slot's open result logged) */
            if (base && FIELD(uint8_t, base, 4 + k)) logf("mhgu-de: save: %s: none after %s (open %x)", path, name, r);
            continue;
        }
        int ok = !fs_size(&size, h) && size >= MS_HEADER && size <= MS_FILE_SIZE &&
                 !fs_read(&got, h, 0, s_cache[k], (uint32_t)size) && got == (uint32_t)size;
        fs_close(h);
        uint32_t used, link, gen, hash;
        if (!ok) {
            s_cache_state[k] = 2;
            s_keep[k] = 1;
            logf("mhgu-de: save: %s could not be read: kept as it is this session", path);
            continue;
        }
        if (ms_parse(s_cache[k], got, &used, &link, &gen, &hash)) {
            s_cache_state[k] = 2;
            s_keep[k] = 1;
            logf("mhgu-de: save: %s is damaged or of a newer format (check word, size, version): not merged, kept as "
                 "it is this session", path);
            continue;
        }
        s_cache_n[k] = used;
        s_cache_state[k] = 1;
        s_body[k] = ms_fnv(s_cache[k] + MS_HEADER, used - MS_HEADER, link);
        if (gen > s_gen[k]) s_gen[k] = gen;
        logf("mhgu-de: save: %s read after %s: %u bytes, link %x, generation %u, slot hash %x", path, name, used, link,
             gen, hash);
    }
    return 0;
}

/* ---------------------------------------------------------------------------------------------- parse */

/* 0x3e0db8(scene, stream): one slot parsed into the live character */
int save_parse_c(uint32_t *regs)
{
    uint32_t st = regs[R1], base = st ? FIELD(uint32_t, st, 12) : 0;
    int k = st ? slot_of(base, FIELD(uint32_t, st, 8)) : -1;
    s_merged = 0;
    if (k < 0) return 0;
    uint8_t *slot = slot_ptr(base, k);
    uint32_t link = 0, gen = 0, state = 0, used, flink, fgen, hash;
    int linked = ms_link(slot, &link, &gen, &state);
    if (s_cache_state[k] != 1 || ms_parse(s_cache[k], s_cache_n[k], &used, &flink, &fgen, &hash)) {
        if (linked && state == MS_SPLIT)
            logf("mhgu-de: save: slot %u says split (link %x) but has no readable file: nothing to merge", k + 1, link);
        return 0;
    }
    if (linked && state == MS_FULL) {
        logf("mhgu-de: save: slot %u is full (its last file write failed): file not merged", k + 1);
        return 0;
    }
    if (linked && link != flink) {
        logf("mhgu-de: save: slot %u (link %x) and its file (link %x) are another character's: not merged", k + 1,
             link, flink);
        return 0;
    }
    if (!linked) {                                     /* a restored save of before the split (D11), or a new character */
        uint8_t probe[64];                             /* any record (or one the tiny budget left) = added things */
        uint32_t left = 0;
        int n = ms_split(slot, s_quests, MS_QUEST_N, flink, fgen, 0, 0, probe, sizeof probe, 0, &left);
        if (n >= 0 && n <= (int)MS_HEADER && !left) {   /* -1: an added weapon held: added things */
            logf("mhgu-de: save: slot %u has no link and nothing added: its file (link %x) is not this character's",
                 k + 1, flink);
            return 0;
        }
        logf("mhgu-de: save: slot %u has no link but holds added things: merging its file too (D11)", k + 1);
    }
    struct ms_stats ms;
    uint32_t jl = 0, al = 0, t0 = tick0(), h0 = ms_fnv(slot, MS_SLOT_SIZE, 0x811C9DC5u);
    int r = ms_merge(slot, s_cache[k], s_cache_n[k], s_quests, MS_QUEST_N, s_journal, JOURNAL, &jl, s_aside[k],
                     ASIDE_CAP, &al, &ms);
    if (r) {
        s_keep[k] = 1;
        logf("mhgu-de: save: slot %u: merge refused (%d): the file is kept as it is this session", k + 1, r);
        return 0;
    }
    s_aside_n[k] = al;
    s_merged = slot;
    s_merged_k = (uint32_t)k;
    s_jlen = jl;
    s_link[k] = flink;
    logf("mhgu-de: save: slot %u merged (%s, slot hash %x): %u placed, %u moved, %u kept as GU has them, %u aside, "
         "journal %u bytes, %u us", k + 1, ms.exact ? "exact" : "careful", h0,
         ms.placed, ms.moved, ms.kept, ms.aside, jl, us_since(t0));
    return 0;
}

/* 0x3e0e64: right after the slot's parse (0x3e77b0): the slot back as read */
int save_parsed_c(uint32_t *regs)
{
    (void)regs;
    if (!s_merged) return 0;
    ms_restore(s_merged, s_journal, s_jlen);
    s_merged = 0;
    return 0;
}
