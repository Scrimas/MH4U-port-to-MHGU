/* save.c: the mod's own save store and per-quest leases of GU's dummy save slots (notes/save-store.md).
 *
 * GU keeps a monster's hunts, captures and size records in arrays of its 137 registry indexes (sUserInfo
 * [0x1897f78] +0x72c: u16 hunts[137], u16 captures[137] at +0x112, at +0x224 a vector of 137 size records {u16 *,
 * u32}, each -> u16 {smallest, largest}), and a quest counts its kills in 137 entries of the quest object (+0x110 +
 * index * 8: u16 largest size, smallest size, hunts, captures; tally 0x3a75c8). A ported index (137..) would run past
 * both (no bound check), so every ported monster is counted under one of GU's 7 unused 'dummy' indexes 105..111
 * (IDs 0x1064..0x106a) instead:
 *  - a monster with a fixed save slot (allocations.toml save_index: every monster up to v1.8.0) keeps it, and its
 *    numbers stay in GU's save record of that slot, as before;
 *  - a monster with `save = "lease"` borrows a slot for its quest, and its numbers go to the store below. The four GU
 *    functions that add a quest's result to the save (0x526d94 hunts, 0x526e00 captures, 0x526eb0 largest, 0x526ef8
 *    smallest: one caller each, the quest-end writer 0x38d990) and the size reader 0x526f48 are hooked: for a leased
 *    slot they work on the lessee's store record, so the owner's GU record is never written. While leased, the slot
 *    shows the lessee in the quest result: name (main.c name_index_c), icon (reg_icon), size and crowns (its
 *    em_size_scale_data element, main.c size_slot_dress) and break rewards (items.c bui_record_c). A ported monster
 *    only spawns in its own quests (main.c standin_swap), so an owner and a lessee of the same slot never meet in
 *    one quest; the owner's next tally takes the slot back (and moves a lessee counted there in the same quest).
 *
 * The store lives in the reserved block of sUserInfo (+0x3684..+0x43f7, 0xd74 bytes): zeroed by GU's initialisers
 * 0x51c91c / 0x51cbe4, written and read raw by the character save / load (0x51daa8 in 0x51d12c, 0x51e5c0 in 0x51dc40)
 * and touched by no other GU code (scan of every function that loads sUserInfo, notes/save-store.md); items.c keeps
 * the items-obtained bits of IDs 3008.. at +0x3700..+0x38ff. So the store is saved with the character, in the same
 * file and commit as GU's own data, on every platform GU's save works on, and an older core leaves it alone.
 * Format at STORE_OFF: header {u32 'MH4S', u16 version 1, u16 records, u32 FNV-1a of version, record count and the
 * records, u32 0}, then 12-byte records {u16 em ID, hunts, captures, smallest, largest, flags 0}. An all-zero block is
 * an empty store; a block that is neither empty nor a valid store (another tool's data, a newer format) is never
 * written: lessees' numbers are then not recorded (logged) and nothing else changes. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

extern uint32_t reg_icon[];                 /* tables.S: UI icon per registry index (build.py REG_TABLES) */

#define USERINFO    0x1897f78u              /* sUserInfo: the loaded character (items.c, notes.c) */
#define TALLIES     0x72cu                  /* its hunts[137] (+0), captures[137] (+0x112) */
#define STORE_OFF   0x3900u
#define STORE_END   0x43f8u                 /* end of the reserved block */
#define STORE_SIZE  (STORE_END - STORE_OFF) /* 2808 bytes */
#define STORE_MAGIC 0x5334484du             /* "MH4S" */
#define STORE_VERSION 1u
#define HDR 16u

struct store_rec { uint16_t em, hunts, captures, size_min, size_max, flags; };
#define REC_MAX ((STORE_SIZE - HDR) / (uint32_t)sizeof(struct store_rec))   /* 232 */
_Static_assert(sizeof(struct store_rec) == 12, "store record size");
_Static_assert(STORE_OFF >= 0x3700u + 512u, "the store overlaps items.c's obtained bits (+0x3700, 512 bytes)");
enum { F_HUNTS, F_CAPTURES, F_BOTH, F_MIN, F_MAX };

#define SLOT_FIRST 105u                     /* GU's unused registry indexes 105..111 ('dummy1'..'dummy7') */
#define SLOTS 7
#define SLOT_ID(k) (0x1064u + (uint32_t)(k))
#define CAP 9999u                           /* GU's cap of a hunt / capture count (0x526d94, 0x523104) */
#define QUEST_ENTRY(o, idx) ((uint8_t *)(o) + 0x110u + 8u * (idx))   /* a quest's tally of one index (0x3a75c8) */

/* ---- the store ---- */

/* FNV-1a 32 (a plain multiply loop: no CRC idiom the compiler could turn into ARMv8 CRC instructions, which not
 * every emulator or recompiler may run) */
static uint32_t fnv_bytes(uint32_t h, const uint8_t *p, uint32_t n)
{
    while (n--) h = (h ^ *p++) * 16777619u;
    return h;
}

static uint32_t store_check_word(const uint8_t *b)    /* FNV-1a of version, record count and the records */
{
    uint32_t n = FIELD(uint16_t, b, 6);
    if (n > REC_MAX) n = REC_MAX;
    return fnv_bytes(fnv_bytes(2166136261u, b + 4, 4), b + HDR, n * (uint32_t)sizeof(struct store_rec));
}

enum { ST_NONE, ST_EMPTY, ST_VALID, ST_FOREIGN };
static const char *const ST_NAME[] = { "no character loaded", "empty", "valid", "NOT a store: left alone" };

static uint8_t *store_block(void)
{
    uint8_t *s = *(uint8_t **)MAIN(USERINFO);
    return s ? s + STORE_OFF : 0;
}

static int store_state(const uint8_t *b)
{
    if (!b) return ST_NONE;
    if (!FIELD(uint32_t, b, 0)) {
        for (uint32_t i = 0; i < STORE_SIZE; i++)
            if (b[i]) return ST_FOREIGN;
        return ST_EMPTY;
    }
    if (FIELD(uint32_t, b, 0) != STORE_MAGIC || FIELD(uint16_t, b, 4) != STORE_VERSION ||
        FIELD(uint16_t, b, 6) > REC_MAX || FIELD(uint32_t, b, 12) || FIELD(uint32_t, b, 8) != store_check_word(b))
        return ST_FOREIGN;
    return ST_VALID;
}

/* the store's state, logged whenever it changes (a character loaded, the first record, another tool's data) */
static int store_check(uint8_t **out)
{
    static const uint8_t *s_blk;
    static int s_st = -1;
    uint8_t *b = store_block();
    int st = store_state(b);
    if (b != s_blk || st != s_st) {
        s_blk = b;
        s_st = st;
        logf("mh4uport: store sUserInfo+%x (%u bytes, %u records max): %s, %u record(s)", STORE_OFF, STORE_SIZE,
             REC_MAX, ST_NAME[st], st == ST_VALID ? FIELD(uint16_t, b, 6) : 0u);
    }
    *out = b;
    return st;
}

static struct store_rec *store_find(uint8_t *b, uint32_t em)
{
    struct store_rec *r = (struct store_rec *)(b + HDR);
    for (uint32_t i = 0, n = FIELD(uint16_t, b, 6); i < n; i++)
        if (r[i].em == em) return &r[i];
    return 0;
}

/* a value of monster em's record (0 when it has none, or the store is not valid) */
static uint32_t store_read(uint32_t em, int field)
{
    uint8_t *b;
    const struct store_rec *r = store_check(&b) == ST_VALID ? store_find(b, em) : 0;
    if (!r) return 0;
    switch (field) {
    case F_HUNTS: return r->hunts;
    case F_CAPTURES: return r->captures;
    case F_MIN: return r->size_min;
    case F_MAX: return r->size_max;
    default: {                              /* as 0x523104: sum, 9999 when (sum & 0xfff0) > 9999 */
        uint32_t s = (uint32_t)r->hunts + r->captures;
        return (s & 0xfff0u) > CAP ? CAP : (s & 0xffffu);
    }
    }
}

/* monster em's record to change (created when missing; an empty store gets its header first), 0 = the store cannot
 * be written (no character, not a store, full): the change is dropped. Call store_seal() right after the change. */
static struct store_rec *store_open(uint32_t em)
{
    uint8_t *b;
    int st = store_check(&b);
    if (st == ST_EMPTY) {
        FIELD(uint32_t, b, 0) = STORE_MAGIC;
        FIELD(uint16_t, b, 4) = STORE_VERSION;
        FIELD(uint16_t, b, 6) = 0;
        FIELD(uint32_t, b, 12) = 0;
        FIELD(uint32_t, b, 8) = store_check_word(b);
        st = store_check(&b);
    }
    if (st != ST_VALID) return 0;
    struct store_rec *r = store_find(b, em);
    if (r) return r;
    uint32_t n = FIELD(uint16_t, b, 6);
    if (n >= REC_MAX) {
        logf("mh4uport: store full (%u records): em %x not recorded", n, em);
        return 0;
    }
    r = (struct store_rec *)(b + HDR) + n;
    r->em = (uint16_t)em;
    r->hunts = r->captures = r->size_min = r->size_max = r->flags = 0;
    FIELD(uint16_t, b, 6) = (uint16_t)(n + 1);
    return r;
}

static void store_seal(void)
{
    uint8_t *b = store_block();
    if (b) FIELD(uint32_t, b, 8) = store_check_word(b);
}

static uint16_t add_capped(uint16_t v, uint32_t n)    /* as 0x526d94: (u16)(v + n), 9999 from 9999 on */
{
    uint32_t s = (uint32_t)v + n;
    return (uint16_t)((s & 0xffffu) < CAP ? s : CAP);
}

/* a few bits under a key that is no em ID (0xf001.. gear.c): a record's 5 u16 words, 80 bits; a bit past them answers 0 and is not kept (logged once) */
int save_bits_get(uint32_t key, uint32_t bit)
{
    uint8_t *b;
    struct store_rec *r = store_check(&b) == ST_VALID ? store_find(b, key) : 0;
    if (!r || bit >= 80u) return 0;
    return FIELD(uint16_t, r, 2u + 2u * (bit / 16u)) >> (bit % 16u) & 1;
}

void save_bits_set(uint32_t key, uint32_t bit)
{
    static uint32_t s_n;
    struct store_rec *r;
    if (bit >= 80u) {
        if (++s_n <= 8) logf("mh4uport: store bit %u of key %x past its record: not kept", bit, key);
        return;
    }
    r = store_open(key);
    if (!r) return;
    FIELD(uint16_t, r, 2u + 2u * (bit / 16u)) |= (uint16_t)(1u << (bit % 16u));
    store_seal();
}

/* ---- slot leases ---- */

int port_lease(int m)                      /* 1 = no fixed save slot (allocations.toml save = "lease") */
{
#ifdef TEST_LEASE
    if (m == TEST_LEASE) return 1;          /* test builds: that port index acts as a lessee (GOG_DEFINES TEST_LEASE=k) */
#endif
    return port_monsters[m].lease;
}

static int8_t s_user[SLOTS] = { -1, -1, -1, -1, -1, -1, -1 };     /* lessee (port index) of slot 105 + k, -1 = none */
static uint32_t s_lease_q[SLOTS];                                  /* the quest it was leased in (port_quest_id) */
static int8_t s_dressed[SLOTS] = { -1, -1, -1, -1, -1, -1, -1 };  /* monster slot 105 + k shows, -1 = as built */
static uint32_t s_icon_built[SLOTS];
static int s_icon_saved;
/* slot 109 first (the tails' shared slot: no icon, size or name entry of its own), then 111, 110, 108 .. 105 */
static const uint8_t PREF[SLOTS] = { 4, 6, 5, 3, 2, 1, 0 };

/* slot 105 + k shows monster m in the quest result (-1 = as built: its owner's icon and size data, GU's for 109) */
static void slot_dress(int k, int m)
{
    if (s_dressed[k] == m) return;
    if (!s_icon_saved) {
        for (int i = 0; i < SLOTS; i++) s_icon_built[i] = reg_icon[SLOT_FIRST + i];
        s_icon_saved = 1;
    }
    reg_icon[SLOT_FIRST + k] = m >= 0 ? reg_icon[port_monsters[m].index] : s_icon_built[k];
    size_slot_dress(SLOT_FIRST + k, m);
    s_dressed[k] = (int8_t)m;
    logf("mh4uport: save slot %u (id %x) shows %s", SLOT_FIRST + k, SLOT_ID(k),
         m >= 0 ? port_monsters[m].name : "its owner");
}

static int entry_used(const uint8_t *o, uint32_t idx)
{
    const uint8_t *e = QUEST_ENTRY(o, idx);
    return FIELD(uint32_t, e, 0) || FIELD(uint32_t, e, 4);
}

static int lease_of(int m)                 /* the slot lessee m holds (its last lease), -1 = none */
{
    for (int k = 0; k < SLOTS; k++)
        if (s_user[k] == m) return k;
    return -1;
}

/* slot 105 + k is free for lessee m in quest q (quest object o): no other lessee holds it in this quest, the quest
 * has counted nothing in it, and it is not the fixed slot of a monster of this quest (its owner or a companion) */
static int slot_free(int k, int m, uint32_t q, const uint8_t *o)
{
    int qo = port_quest_owner(q, 0);
    if (s_user[k] >= 0 && s_user[k] != m && s_lease_q[k] == q) return 0;
    if (o && entry_used(o, SLOT_FIRST + (uint32_t)k)) return 0;
    for (int j = 0; qo >= 0 && j < PORT_N; j++)
        if (PORT_OWNER(j) == qo && !port_lease(j) && port_monsters[j].save_index == SLOT_FIRST + (uint32_t)k) return 0;
    return 1;
}

/* a slot for lessee m in quest q, -1 = none: its slot of the last quest if still free, else the first free one */
static int lease_pick(int m, uint32_t q, const uint8_t *o, int except)
{
    int old = lease_of(m);
    if (old >= 0 && old != except && slot_free(old, m, q, o)) return old;
    for (int i = 0; i < SLOTS; i++)
        if (PREF[i] != except && slot_free(PREF[i], m, q, o)) return PREF[i];
    return -1;
}

/* main.c stats_add: the registry index port monster m's tally counts in (quest object o = the tally's r0) */
uint32_t save_slot_tally(int m, uint8_t *o)
{
    const struct port_monster *p = &port_monsters[m];
    uint32_t q = port_quest_id();
    if (!port_lease(m)) {                   /* a fixed slot: taken back from a lessee */
        int k = (int)p->save_index - (int)SLOT_FIRST, n = k >= 0 && k < SLOTS ? s_user[k] : -1;
        if (k < 0 || k >= SLOTS) return p->save_index;
        if (n >= 0 && n != m) {
            if (s_lease_q[k] == q && o && entry_used(o, p->save_index)) {   /* the lessee was counted here in this
                                                                              quest: move its entry */
                int k2 = lease_pick(n, q, o, k);
                if (k2 >= 0) {
                    uint8_t *a = QUEST_ENTRY(o, p->save_index), *d = QUEST_ENTRY(o, SLOT_FIRST + (uint32_t)k2);
                    FIELD(uint32_t, d, 0) = FIELD(uint32_t, a, 0);
                    FIELD(uint32_t, d, 4) = FIELD(uint32_t, a, 4);
                    FIELD(uint32_t, a, 0) = FIELD(uint32_t, a, 4) = 0;
                    s_user[k2] = (int8_t)n;
                    s_lease_q[k2] = q;
                    slot_dress(k2, n);
                    logf("mh4uport: %s moved from save slot %u to %u (its owner %s is counted)", port_monsters[n].name,
                         p->save_index, SLOT_FIRST + k2, p->name);
                } else {
                    logf("mh4uport: ERROR %s and %s share save slot %u in this quest", port_monsters[n].name, p->name,
                         p->save_index);
                }
            }
            s_user[k] = -1;
        }
        slot_dress(k, -1);
        return p->save_index;
    }
    int k = -1;
    for (int i = 0; i < SLOTS; i++)
        if (s_user[i] == m && s_lease_q[i] == q) k = i;
    if (k < 0) {
        k = lease_pick(m, q, o, -1);
        if (k < 0) {                        /* 7 ported monsters counted in one quest: never past index 136 */
            k = PREF[0];
            logf("mh4uport: ERROR no free save slot for %s: counted in slot %u with another monster", p->name,
                 SLOT_FIRST + k);
        }
        for (int i = 0; i < SLOTS; i++)
            if (s_user[i] == m && i != k) {     /* its lease of an earlier quest */
                s_user[i] = -1;
                slot_dress(i, -1);
            }
        s_user[k] = (int8_t)m;
        s_lease_q[k] = q;
        logf("mh4uport: %s leases save slot %u (id %x) for quest %u", p->name, SLOT_FIRST + k, SLOT_ID(k), q);
    }
    slot_dress(k, m);
    return SLOT_FIRST + (uint32_t)k;
}

/* the monster a dummy ID stands for: its lessee, else its fixed owner (companions included); -1 = not a dummy ID or
 * nobody's (items.c bui_record_c) */
int save_slot_user(uint32_t id)
{
    id &= 0xffff;
    if (id < SLOT_ID(0) || id >= SLOT_ID(SLOTS)) return -1;
    if (s_user[id - SLOT_ID(0)] >= 0) return s_user[id - SLOT_ID(0)];
    for (int m = 0; m < PORT_N; m++)
        if (!port_lease(m) && port_monsters[m].save_id == id) return m;
    return -1;
}

int save_lessee_of_index(uint32_t idx)     /* main.c name_index_c: the lessee slot idx stands for, -1 = none */
{
    return idx >= SLOT_FIRST && idx < SLOT_FIRST + SLOTS ? s_user[idx - SLOT_FIRST] : -1;
}

static int lessee_of_id(uint32_t id)
{
    id &= 0xffff;
    return id >= SLOT_ID(0) && id < SLOT_ID(SLOTS) ? s_user[id - SLOT_ID(0)] : -1;
}

/* ---- hooks ---- */

/* 0x3a3930(quest, id) -> hunted or captured in this quest (its entry's hunts / captures). Fixed slot: its slot's ID;
 * a lessee: its slot's, or no (it holds none: not counted in any quest since the character was loaded). */
int stats_hunted_c(uint32_t *regs)
{
    int m = port_by_em(regs[R1] & 0xffff), k;
    if (m < 0) return 0;
    if (!port_lease(m)) {
        regs[R1] = (regs[R1] & ~0xffffu) | port_monsters[m].save_id;
        return 0;
    }
    if ((k = lease_of(m)) < 0) {
        regs[R0] = 0;
        return 1;
    }
    regs[R1] = (regs[R1] & ~0xffffu) | SLOT_ID(k);
    return 0;
}

/* GU readers of the save by monster ID (index from 0x50b64; > 136 answers 0): a fixed slot's monster reads its slot,
 * a lessee is answered from the store. 0x523104 hunts + captures (the Hunter's Notes page 0x560058), 0x526dd4 hunts
 * (0x560418, 5 more callers), 0x526e44 captures (0x560238: the Notes page's "captured"). */
static int read_by_id(uint32_t *regs, int field)
{
    int m = port_by_em(regs[R1] & 0xffff);
    if (m < 0) return 0;
    if (!port_lease(m)) {
        regs[R1] = (regs[R1] & ~0xffffu) | port_monsters[m].save_id;
        return 0;
    }
    regs[R0] = store_read(port_monsters[m].em_id, field);
    return 1;
}
int save_hunts_c(uint32_t *regs) { return read_by_id(regs, F_BOTH); }
int save_hunts_id_c(uint32_t *regs) { return read_by_id(regs, F_HUNTS); }
int save_captures_id_c(uint32_t *regs) { return read_by_id(regs, F_CAPTURES); }

/* 0x526f48(tallies, id, which) -> size record (0 smallest, 1 largest), no bound on the index: the quest-end writer
 * asks with the slot's ID, the Notes page and two more with the monster's. A lessee (or its leased slot) is answered
 * from the store, a fixed slot's monster reads its slot (never an index past 136). */
int save_size_read_c(uint32_t *regs)
{
    uint32_t id = regs[R1] & 0xffff;
    int n = lessee_of_id(id);
    if (n < 0) {
        int m = port_by_em(id);
        if (m < 0) return 0;
        if (!port_lease(m)) {
            regs[R1] = (regs[R1] & ~0xffffu) | port_monsters[m].save_id;
            return 0;
        }
        n = m;
    }
    regs[R0] = store_read(port_monsters[n].em_id, regs[R2] ? F_MAX : F_MIN);
    return 1;
}

/* 0x67310(mgr, id, size, out {u8 crown, f32 cm at +4}): a size record's crown and cm, from the em_size_scale_data element of
 * the ID's registry index. The Notes page (0x5b285c, 0x5b2a04) and others ask by the monster's ID, and a ported index has no
 * element: GU's loop ends without writing, and the page shows 0 next to the record it has read (user's test 2026-11-06: 98 and
 * 114 in the store, 0 and 0 on Monoblos' page). A fixed slot's monster is asked under its slot's ID, whose element is its own
 * (main.c size_data). A lessee has no element: GU's rules here on its package.toml [size], as main.c size_set fills an element
 * (no size data: nothing written, as a negative base). */
int size_lookup_c(uint32_t *regs)
{
    int m = port_by_em(regs[R1] & 0xffff);
    if (m < 0) return 0;
    const struct port_monster *p = &port_monsters[m];
    if (!port_lease(m)) {
        regs[R1] = (regs[R1] & ~0xffffu) | p->save_id;
        return 0;
    }
    uint32_t size = regs[R2];
    uint8_t *out = (uint8_t *)regs[R3];
    float mini = p->size[1], silver = mini > 0.0f ? p->size[2] : 100.0f, gold = mini > 0.0f ? p->size[3] : 100.0f;
    out[0] = 255;
    if (!size || p->size[0] <= 0.0f) return 1;
    FIELD(float, out, 4) = (float)size / 100.0f * p->size[0];
    if (size <= (uint32_t)((mini + 0.005f) * 100.0f)) out[0] = 3;
    else if (size >= (uint32_t)((gold + 0.005f) * 100.0f)) out[0] = 1;
    else if (size >= (uint32_t)((silver + 0.005f) * 100.0f)) out[0] = 2;
    return 1;
}

/* quest end (0x38d990, per index with a hunt or capture): 0x526d94(tallies, id, hunts) / 0x526e00(.., captures).
 * A leased slot: added to its lessee's store record, GU's record of the slot (its owner's) is not written. */
static int add_count(uint32_t *regs, int captures)
{
    int n = lessee_of_id(regs[R1]);
    if (n < 0) return 0;
    struct store_rec *r = store_open(port_monsters[n].em_id);
    uint32_t v = 0;
    if (r) {
        if (captures) v = r->captures = add_capped(r->captures, regs[R2]);
        else v = r->hunts = add_capped(r->hunts, regs[R2]);
        store_seal();
    }
    logf("mh4uport: %s +%u %s -> store %d (slot %x untouched)", port_monsters[n].name, regs[R2],
         captures ? "capture(s)" : "hunt(s)", r ? (int)v : -1, regs[R1] & 0xffff);
    return 1;
}
int save_add_hunts_c(uint32_t *regs) { return add_count(regs, 0); }
int save_add_captures_c(uint32_t *regs) { return add_count(regs, 1); }

/* quest end: 0x526eb0(tallies, size id, size) -> 1 = a new largest, 0x526ef8(..) -> 1 = a new smallest (0 = none
 * yet); size 0 changes nothing. A leased slot: its lessee's store record, as GU's rules. */
static int size_record(uint32_t *regs, int largest)
{
    int n = lessee_of_id(regs[R1]);
    if (n < 0) return 0;
    uint32_t v = regs[R2] & 0xffff;
    struct store_rec *r = v ? store_open(port_monsters[n].em_id) : 0;
    regs[R0] = 0;
    if (r) {
        if (largest && r->size_max < v) {               /* 0x526eb0: stored < size */
            r->size_max = (uint16_t)v;
            regs[R0] = 1;
        }
        if (!largest && (uint16_t)(r->size_min - 1u) >= v) {   /* 0x526ef8: (u16)(stored - 1) >= size (0 = none) */
            r->size_min = (uint16_t)v;
            regs[R0] = 1;
        }
        store_seal();
    }
    logf("mh4uport: %s size %u: %s record %s", port_monsters[n].name, v, largest ? "largest" : "smallest",
         regs[R0] ? "new" : "kept");
    return 1;
}
int save_size_max_c(uint32_t *regs) { return size_record(regs, 1); }
int save_size_min_c(uint32_t *regs) { return size_record(regs, 0); }

/* log of the character's slot records and the store */
static void log_save(const char *when)
{
    uint8_t *s = *(uint8_t **)MAIN(USERINFO), *b;
    int st = store_check(&b);
    if (!s) return;
    for (int k = 0; k < SLOTS; k++)
        logf("mh4uport: %s: save slot %u: hunts %u, captures %u", when, SLOT_FIRST + k,
             FIELD(uint16_t, s, TALLIES + 2 * (SLOT_FIRST + k)), FIELD(uint16_t, s, TALLIES + 0x112 + 2 * (SLOT_FIRST + k)));
    for (uint32_t i = 0, n = st == ST_VALID ? FIELD(uint16_t, b, 6) : 0; i < n && i < 16; i++) {
        const struct store_rec *r = (const struct store_rec *)(b + HDR) + i;
        logf("mh4uport: %s: store em %x: hunts %u, captures %u, smallest %u, largest %u", when, r->em, r->hunts,
             r->captures, r->size_min, r->size_max);
    }
}

/* 0x3e77f0: right after the character load 0x51dbb4 (sUserInfo read from the save file): leases end with the
 * character, the slots show their owners again */
int save_loaded_c(uint32_t *regs)
{
    (void)regs;
    for (int k = 0; k < SLOTS; k++) {
        s_user[k] = -1;
        slot_dress(k, -1);
    }
    log_save("loaded");
    return 0;
}

/* 0x3e7630: right before the character save 0x51d0a0 (sUserInfo written to the save file) */
int save_writing_c(uint32_t *regs)
{
    (void)regs;
    log_save("saving");
    return 0;
}
