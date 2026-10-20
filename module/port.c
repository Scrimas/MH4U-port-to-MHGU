/* port.c: the ported monsters' data files, installed check, file IDs and quest ownership (port.h).
 *
 * Files are read through main's nn::fs import stubs (dump/gu_plt.json); GU mounts its RomFS as "app" (MountRom
 * calls 0xb860f4 / 0xb86228, name "app" at 0x157aadf), so mod RomFS files are app:/nativeNX/... too. The first
 * caller loads a data file, whatever its thread (an atomic state per monster); the first hooks that need data run
 * at boot (rItemData load), long after the mount. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

typedef struct { void *h; } fs_file;
typedef uint32_t (*fs_entry_type_t)(uint32_t *type, const char *path);
typedef uint32_t (*fs_open_t)(fs_file *out, const char *path, int mode);
typedef uint32_t (*fs_size_t)(int64_t *out, fs_file f);
typedef uint32_t (*fs_read_t)(uint32_t *out, fs_file f, int64_t offset, void *buf, uint32_t size);
typedef void (*fs_close_t)(fs_file f);
#define fs_entry_type FN(fs_entry_type_t, 0x13f049c)   /* nn::fs::GetEntryType */
#define fs_open FN(fs_open_t, 0x13f04b4)               /* nn::fs::OpenFile (mode 1 = read) */
#define fs_size FN(fs_size_t, 0x13f043c)               /* nn::fs::GetFileSize */
#define fs_read FN(fs_read_t, 0x13f0448)               /* nn::fs::ReadFile(size_t *, handle, offset, buf, size) */
#define fs_close FN(fs_close_t, 0x13f046c)             /* nn::fs::CloseFile */

#define DATA_DIR "app:/nativeNX/mh4uport/"
#define POOL_SIZE (256u * 1024u)       /* every monster's data file (Gogmazios: 37.6 KB) */
#define FORMAT 1u
static uint8_t s_pool[POOL_SIZE] __attribute__((aligned(16)));
static uint32_t s_pool_used;
static const uint8_t *s_data[PORT_N];
static uint32_t s_state[PORT_N];        /* 0 not tried, 1 loading, 2 loaded, 3 missing / invalid */
static uint32_t s_installed[PORT_N];    /* 0 not checked, 1 yes, 2 no */
uint32_t port_manifests[PORT_N][51] __attribute__((aligned(4)));

static char *put(char *p, const char *s) { while (*s) *p++ = *s++; *p = 0; return p; }

static int str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

static void sleep_ns(uint32_t ns)          /* svcSleepThread */
{
    register uint32_t r0 __asm__("r0") = ns, r1 __asm__("r1") = 0;
    __asm__ volatile("svc #0x0b" : "+r"(r0), "+r"(r1) : : "memory");
}

/* header 32 B {"MH4P", u16 format, u16 sections, char name[16], u32 version, u32 em_id}, sections 12 B each
 * {tag, offset, size} (tools/portdata.py) */
static int valid(int m, const uint8_t *d, uint32_t size)
{
    const struct port_monster *p = &port_monsters[m];
    uint32_t n = size >= 32 ? FIELD(uint16_t, d, 6) : 0;
    if (size < 32 || FIELD(uint32_t, d, 0) != 0x5034484du || FIELD(uint16_t, d, 4) != FORMAT ||
        !str_eq((const char *)d + 8, p->name) || FIELD(uint32_t, d, 28) != p->em_id || 32 + 12 * n > size) {
        logf("mh4uport: %s data: bad header (format %u, em %x), not used", p->name, size >= 32 ? d[4] : 0,
             size >= 32 ? FIELD(uint32_t, d, 28) : 0);
        return 0;
    }
    for (uint32_t k = 0; k < n; k++) {
        uint32_t off = FIELD(uint32_t, d, 36 + 12 * k), len = FIELD(uint32_t, d, 40 + 12 * k);
        if ((off & 3) || off > size || len > size - off) {
            logf("mh4uport: %s data: section %u outside the file, not used", p->name, k);
            return 0;
        }
    }
    return 1;
}

static const uint8_t *section_of(const uint8_t *d, const char *tag, int nth, uint32_t *size)
{
    uint32_t n = FIELD(uint16_t, d, 6), t = (uint32_t)(uint8_t)tag[0] | (uint32_t)(uint8_t)tag[1] << 8 |
                 (uint32_t)(uint8_t)tag[2] << 16 | (uint32_t)(uint8_t)tag[3] << 24;
    for (uint32_t k = 0; k < n; k++) {
        if (FIELD(uint32_t, d, 32 + 12 * k) != t || nth-- > 0) continue;
        if (size) *size = FIELD(uint32_t, d, 40 + 12 * k);
        return d + FIELD(uint32_t, d, 36 + 12 * k);
    }
    return 0;
}

static int load(int m)
{
    const struct port_monster *p = &port_monsters[m];
    char path[80];
    fs_file f;
    int64_t size = 0;
    uint32_t got = 0, base = 0;
    put(put(put(path, DATA_DIR), p->name), ".bin");
    if (fs_open(&f, path, 1)) {
        logf("mh4uport: %s: no data file %s: its gear / items / quests stay off, later monsters' tables too", p->name,
             path);
        return 0;
    }
    int ok = !fs_size(&size, f) && size > 0 && size <= POOL_SIZE;
    if (ok) {
        uint32_t need = ((uint32_t)size + 15u) & ~15u;
        base = __atomic_fetch_add(&s_pool_used, need, __ATOMIC_ACQ_REL);
        ok = base + need <= POOL_SIZE && !fs_read(&got, f, 0, s_pool + base, (uint32_t)size) && got == (uint32_t)size;
    }
    fs_close(f);
    if (!ok || !valid(m, s_pool + base, (uint32_t)size)) {
        logf("mh4uport: %s: data file %s unreadable (size %u, read %u)", p->name, path, (uint32_t)size, got);
        return 0;
    }
    s_data[m] = s_pool + base;
    uint32_t v = FIELD(uint32_t, s_data[m], 24);
    logf("mh4uport: %s data %u.%u.%u loaded (%u bytes, %u sections)", p->name, v >> 16, (v >> 8) & 0xff, v & 0xff,
         (uint32_t)size, FIELD(uint16_t, s_data[m], 6));
    /* the registry manifest of its index (reg_files[index] = port_manifests[m]) */
    uint32_t fsz;
    const uint8_t *fs = section_of(s_data[m], "FILE", 0, &fsz);
    if (fs && fsz >= 8 + 51 * 4) {
#ifndef NATIVE_DONOR
        for (int k = 0; k < 51; k++) port_manifests[m][k] = PORT_U32(fs, 8 + 4 * k);
#endif
    }
    return 1;
}

int port_data(int m)
{
    uint32_t st = __atomic_load_n(&s_state[m], __ATOMIC_ACQUIRE), zero = 0;
    if (st >= 2) return st == 2;
    if (__atomic_compare_exchange_n(&s_state[m], &zero, 1, 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        int ok = load(m);
        __atomic_store_n(&s_state[m], ok ? 2u : 3u, __ATOMIC_RELEASE);
        if (ok) notes_data_loaded(m);      /* after the state: it reads the data through port_section */
        return ok;
    }
    while ((st = __atomic_load_n(&s_state[m], __ATOMIC_ACQUIRE)) == 1) sleep_ns(100000);
    return st == 2;
}

void port_load_all(void)
{
    for (int m = 0; m < PORT_N; m++) port_data(m);
}

const uint8_t *port_section(int m, const char *tag, int nth, uint32_t *size)
{
    return port_data(m) ? section_of(s_data[m], tag, nth, size) : 0;
}

/* installed = its monster arc nativeNX/arc/enemy/emNNN_VV.arc exists (id = variant << 8 | em) */
int port_installed(int m)
{
    if (s_installed[m]) return s_installed[m] == 1;
    uint32_t id = port_monsters[m].em_id, em = id & 0xff, var = id >> 8, type = 0;
    char path[64], *p = put(path, "app:/nativeNX/arc/enemy/em");
    *p++ = (char)('0' + em / 100); *p++ = (char)('0' + em / 10 % 10); *p++ = (char)('0' + em % 10); *p++ = '_';
    *p++ = (char)('0' + var / 10 % 10); *p++ = (char)('0' + var % 10);
    put(p, ".arc");
    uint32_t r = fs_entry_type(&type, path);
    s_installed[m] = !r && type == 1 ? 1 : 2;        /* DirectoryEntryType_File */
    logf("mh4uport: %s %s (%s)", port_monsters[m].name, s_installed[m] == 1 ? "installed" : "NOT installed", path);
    return s_installed[m] == 1;
}

int port_by_em(uint32_t em_id)
{
    for (int m = 0; m < PORT_N; m++)
        if (port_monsters[m].em_id == em_id) return m;
    return -1;
}

int port_by_index(uint32_t index)
{
    for (int m = 0; m < PORT_N; m++)
        if (port_monsters[m].index == index) return m;
    return -1;
}

/* Quest ID sources (static trace, monsters/gogmazios/notes/stage.md section 9):
 *  - [[0x188ae38]+0xd68] = the ACCEPTED quest: written by the board accept 0x784e94 (0x784ec8), read by the quest
 *    start state machine 0x5d74 (q%07d.arc request 0x60d0, stage byte 0x6c0380 via 0x3bd2a8), and CLEARED at
 *    0x7608 right after the quest setup 0x3ade34 -> reads 0 from then on.
 *  - [[0x188ad90]+0xe0] = the RUNNING quest: set by the setup 0x3ade34 (0x3adf1c, from questData record +8), cleared
 *    at quest end (0x39f230). The setup and the spawn loader 0x3adbcc work on this object (r4).
 * port_quest_id() = the first while it is set, else the second: valid from accept to quest end. */
static uint32_t quest_word(uint32_t ptr_word, uint32_t field)
{
    void *q = *(void **)MAIN(ptr_word);
    return q ? FIELD(uint32_t, q, field) : 0;
}

uint32_t port_quest_id(void)
{
    uint32_t id = quest_word(0x188ae38u, 0xd68u);
    return id ? id : quest_word(0x188ad90u, 0xe0u);
}

int port_quest_owner(uint32_t quest_id, int *which)
{
    for (int m = 0; quest_id && m < PORT_N; m++)
        for (int k = 0; k < 2; k++)
            if (port_monsters[m].quests[k] == quest_id) {
                if (which) *which = k;
                return m;
            }
    return -1;
}

int port_running_quest(int *which)
{
    int m = port_quest_owner(port_quest_id(), which);
    return m >= 0 && port_installed(m) ? m : -1;
}

/* hook 0x152960(_, fileId) -> resource. The game indexes its (path hash, type) table with IDs up to 0x106d0,
 * then tail-calls mgr->vt[0x38/4](mgr, <that function>, hash, type); IDs from PORT_FILE_ID_MIN are the ported
 * monsters' (data file section FILE: first ID, count, manifest[51], {hash, type}[count]). */
int file_id_c(uint32_t *regs)
{
    if (regs[R1] < PORT_FILE_ID_MIN) return 0;
    for (int m = 0; m < PORT_N; m++) {
        uint32_t size;
        const uint8_t *fs = port_section(m, "FILE", 0, &size);
        if (!fs) continue;
        uint32_t k = regs[R1] - PORT_U32(fs, 0), n = PORT_U32(fs, 4);
        if (k >= n || 212 + 8 * n > size) continue;
        uint32_t hash = PORT_U32(fs, 212 + 8 * k), type = PORT_U32(fs, 216 + 8 * k);
        void *mgr = *(void **)MAIN(0x2126a64);                /* behind GOT 0x1839450 */
        typedef void *(*find_t)(void *, uint32_t, uint32_t, uint32_t);
        find_t find = (*(find_t **)mgr)[0x38 / 4];
        regs[R0] = (uint32_t)find(mgr, (uint32_t)find, hash, type);
        static uint32_t s_logged[PORT_N][8], s_misses;
        if ((k < 256 && !(s_logged[m][k / 32] & (1u << (k % 32)))) || (!regs[R0] && ++s_misses <= 40)) {
            if (k < 256) s_logged[m][k / 32] |= 1u << (k % 32);
            logf("mh4uport: %s file %x (hash %x type %x) -> %x lr=%x", port_monsters[m].name, regs[R1], hash, type,
                 regs[R0], regs[LR] - MAIN_BASE);
        }
        return 1;
    }
    return 0;
}
