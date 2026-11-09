/* test_save.c: test harness for module/save.c, run as ARM code under unicorn by tools/test_save.py (no game files,
 * no GU code). A fake character (sUserInfo) whose bytes all carry a pattern, except GU's reserved block (zero, as
 * GU's initialisers leave it), a fake quest object, the 8 registry entries of v1.8.0 with their real IDs and two
 * test lessees. Every test checks that no byte of the character outside the store changes; test_save.py checks the
 * store's bytes again on its own (header, check word, records). A failed check logs "FAIL <line> <what>". */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define USERINFO 0x1897f78u
#define USER_SIZE 0x4500u
#define RESERVED 0x3682u                    /* GU's initialisers zero +0x3682..+0x43f7 */
#define STORE_OFF 0x3900u
#define STORE_END 0x43f8u
#define TALLIES 0x72cu
#define LESSEE 8
#define LESSEE2 9

uint32_t g_main_base;
static uint32_t s_userinfo;                 /* the word at MAIN(0x1897f78): the character, 0 = none */
uint8_t g_user[USER_SIZE] __attribute__((aligned(16)));
static uint8_t s_copy[USER_SIZE];
uint8_t g_quest[0x110 + 8 * 137 + 16] __attribute__((aligned(8)));
uint32_t reg_icon[160];
static int s_dress[7];                      /* the last size_slot_dress(105 + k, m) per slot, -2 = none */
static uint32_t s_q;                        /* port_quest_id() */
static uint32_t R[8];
int g_fails;

const struct port_monster port_monsters[] = {
    { .name = "gogmazios", .em_id = 0x59, .index = 137, .save_index = 105, .save_id = 0x1064, .name_entry = 105,
      .quests = { 11491, 11492 }, .owner = -1 },
    { .name = "tigerstripe_zamtrios", .em_id = 0x143, .index = 138, .save_index = 106, .save_id = 0x1065,
      .name_entry = 106, .quests = { 11493 }, .owner = -1 },
    { .name = "dalamadur", .em_id = 0x5a, .index = 139, .save_index = 107, .save_id = 0x1066, .name_entry = 107,
      .quests = { 10790 }, .owner = -1 },
    { .name = "shah_dalamadur", .em_id = 0x15a, .index = 140, .save_index = 108, .save_id = 0x1067,
      .name_entry = 108, .quests = { 10791 }, .owner = -1 },
    { .name = "dalamadur_tail", .em_id = 0x5b, .index = 141, .save_index = 109, .save_id = 0x1068, .name_entry = 107,
      .owner = 2 },
    { .name = "shah_dalamadur_tail", .em_id = 0x15b, .index = 142, .save_index = 109, .save_id = 0x1068,
      .name_entry = 108, .owner = 3 },
    { .name = "stygian_zinogre", .em_id = 0x139, .index = 143, .save_index = 110, .save_id = 0x1069,
      .name_entry = 110, .quests = { 10775 }, .owner = -1 },
    { .name = "black_gravios", .em_id = 0x105, .index = 144, .save_index = 111, .save_id = 0x106a, .name_entry = 111,
      .quests = { 10780 }, .owner = -1 },
    { .name = "test_lessee", .em_id = 0x65, .index = 145, .name_entry = 109, .quests = { 99001 }, .owner = -1,
      .lease = 1, .size = { 2163.6f, 0.9f, 1.15f, 1.23f } },
    { .name = "test_lessee2", .em_id = 0x66, .index = 146, .name_entry = 109, .quests = { 99002 }, .owner = -1,
      .lease = 1 },
};

int port_by_em(uint32_t em_id)
{
    for (int m = 0; m < PORT_N; m++)
        if (port_monsters[m].em_id == em_id) return m;
    return -1;
}

uint32_t port_quest_id(void) { return s_q; }

int port_quest_owner(uint32_t quest_id, int *which)
{
    for (int m = 0; quest_id && m < PORT_N; m++)
        for (int k = 0; k < PORT_QUESTS; k++)
            if (port_monsters[m].quests[k] == quest_id) {
                if (which) *which = k;
                return m;
            }
    return -1;
}

void size_slot_dress(uint32_t slot, int m)
{
    if (slot >= 105 && slot <= 111) s_dress[slot - 105] = m;
}

#define CHECK(c, what) do { if (!(c)) { logf("FAIL %d %s", __LINE__, what); g_fails++; } } while (0)

static uint32_t hook(int (*f)(uint32_t *), uint32_t r0, uint32_t r1, uint32_t r2, int *ret)
{
    for (int i = 0; i < 8; i++) R[i] = 0;
    R[R0] = r0, R[R1] = r1, R[R2] = r2;
    *ret = f(R);
    return R[R0];
}

static void snapshot(void)
{
    for (uint32_t i = 0; i < USER_SIZE; i++) s_copy[i] = g_user[i];
}

/* bytes of the character that differ from the snapshot outside [lo, hi) */
static uint32_t changed_outside(uint32_t lo, uint32_t hi)
{
    uint32_t n = 0;
    for (uint32_t i = 0; i < USER_SIZE; i++)
        if ((i < lo || i >= hi) && g_user[i] != s_copy[i]) n++;
    return n;
}

static void fresh(void)                     /* a new character, a new quest, the slots as built */
{
    for (uint32_t i = 0; i < USER_SIZE; i++)
        g_user[i] = i >= RESERVED && i < STORE_END ? 0 : (uint8_t)(i * 7 + 3);
    for (uint32_t i = 0; i < sizeof g_quest; i++) g_quest[i] = 0;
    s_userinfo = (uint32_t)g_user;
    g_main_base = (uint32_t)&s_userinfo - USERINFO;
    for (int i = 0; i < 160; i++) reg_icon[i] = 1000 + i;
    for (int k = 0; k < 7; k++) s_dress[k] = -2;
    int r;
    hook(save_loaded_c, 0, 0, 0, &r);      /* character load: no leases */
    for (int k = 0; k < 7; k++) s_dress[k] = -2;
    snapshot();
}

static void quest(uint32_t q)               /* a new quest: its object's tallies start empty */
{
    s_q = q;
    for (uint32_t i = 0; i < sizeof g_quest; i++) g_quest[i] = 0;
}

static void gu_tally(uint32_t idx, uint16_t hunts, uint16_t captures, uint16_t size)   /* as 0x3a75c8 */
{
    uint8_t *e = g_quest + 0x110 + 8 * idx;
    FIELD(uint16_t, e, 4) += hunts;
    FIELD(uint16_t, e, 6) += captures;
    if (FIELD(uint16_t, e, 0) < size) FIELD(uint16_t, e, 0) = size;
    if ((uint16_t)(FIELD(uint16_t, e, 2) - 1) >= size) FIELD(uint16_t, e, 2) = size;
}

/* the quest-end writer 0x38d990 for one index, with its call order: hunts, captures, largest / smallest read, largest
 * / smallest write; returns the new-record flags (bit 0 largest, bit 1 smallest), -1 = a hook let GU write */
static int gu_writer(uint32_t idx)
{
    uint8_t *e = g_quest + 0x110 + 8 * idx;
    uint32_t id = 0x1064 + idx - 105, T = (uint32_t)g_user + TALLIES;
    int r, all = 1, flags = 0;
    hook(save_add_hunts_c, T, id, FIELD(uint16_t, e, 4), &r); all &= r;
    hook(save_add_captures_c, T, id, FIELD(uint16_t, e, 6), &r); all &= r;
    hook(save_size_read_c, T, id, 1, &r); all &= r;
    hook(save_size_read_c, T, id, 0, &r); all &= r;
    if (hook(save_size_max_c, T, id, FIELD(uint16_t, e, 0), &r)) flags |= 1;
    all &= r;
    if (hook(save_size_min_c, T, id, FIELD(uint16_t, e, 2), &r)) flags |= 2;
    all &= r;
    return all ? flags : -1;
}

static uint32_t fnv(uint32_t h, const uint8_t *p, uint32_t n)
{
    while (n--) h = (h ^ *p++) * 16777619u;
    return h;
}

static void store_build(uint32_t n, uint16_t em0, uint16_t version)   /* a valid store of n records em0.. */
{
    uint8_t *b = g_user + STORE_OFF;
    FIELD(uint32_t, b, 0) = 0x5334484du;
    FIELD(uint16_t, b, 4) = version;
    FIELD(uint16_t, b, 6) = (uint16_t)n;
    FIELD(uint32_t, b, 12) = 0;
    for (uint32_t i = 0; i < n; i++) {
        uint8_t *r = b + 16 + 12 * i;
        FIELD(uint16_t, r, 0) = (uint16_t)(em0 + i);
        FIELD(uint16_t, r, 2) = (uint16_t)(i + 1);
        FIELD(uint16_t, r, 4) = 0;
        FIELD(uint16_t, r, 6) = 900;
        FIELD(uint16_t, r, 8) = 1100;
        FIELD(uint16_t, r, 10) = 0;
    }
    FIELD(uint32_t, b, 8) = fnv(fnv(2166136261u, b + 4, 4), b + 16, 12 * n);
}

/* a character of v1.8.0 hunting its monsters with fixed slots: no byte of the character is written by save.c */
int test_fixed(void)
{
    int r;
    fresh();
    for (int m = 0; m < 8; m++) {
        quest(m < 4 || m > 5 ? port_monsters[m].quests[0] : port_monsters[port_monsters[m].owner].quests[0]);
        uint32_t idx = save_slot_tally(m, g_quest);
        CHECK(idx == port_monsters[m].save_index, "a fixed-slot monster counts in its own slot");
        gu_tally(idx, 1, 0, 1000);
        CHECK(gu_writer(idx) == -1, "a fixed slot: GU writes its own record (no hook answers)");
        hook(save_hunts_c, 0, port_monsters[m].em_id, 0, &r);
        CHECK(!r && (R[R1] & 0xffff) == port_monsters[m].save_id, "Notes total by em ID -> its slot ID");
        hook(save_hunts_id_c, 0, port_monsters[m].em_id, 0, &r);
        CHECK(!r && (R[R1] & 0xffff) == port_monsters[m].save_id, "hunts by em ID -> its slot ID");
        hook(save_captures_id_c, 0, port_monsters[m].em_id, 0, &r);
        CHECK(!r && (R[R1] & 0xffff) == port_monsters[m].save_id, "captures by em ID -> its slot ID");
        hook(save_size_read_c, 0, port_monsters[m].em_id, 1, &r);
        CHECK(!r && (R[R1] & 0xffff) == port_monsters[m].save_id, "size by em ID -> its slot ID (no index past 136)");
        hook(stats_hunted_c, (uint32_t)g_quest, port_monsters[m].em_id, 0, &r);
        CHECK(!r && (R[R1] & 0xffff) == port_monsters[m].save_id, "hunted in this quest -> its slot ID");
        CHECK(save_slot_user(port_monsters[m].save_id) == (m == 5 ? 4 : m), "break rewards: slot ID -> its owner");
    }
    hook(save_hunts_c, 0, 0x01, 0, &r);
    CHECK(!r && R[R1] == 0x01, "a GU monster ID passes through");
    hook(save_size_read_c, 0, 0x1064, 1, &r);
    CHECK(!r && R[R1] == 0x1064, "an unleased slot ID passes through");
    CHECK(changed_outside(0, 0) == 0, "no byte of the character changed");
    for (int k = 0; k < 7; k++) CHECK(s_dress[k] == -2 && reg_icon[105 + k] == 1000u + 105 + k, "slots as built");
    return g_fails;
}

/* a lessee's first quest: slot 109, the store created, GU's records untouched */
int test_lessee(void)
{
    int r;
    fresh();
    quest(99001);
    uint32_t idx = save_slot_tally(LESSEE, g_quest);
    CHECK(idx == 109, "the first lease is slot 109");
    CHECK(save_lessee_of_index(109) == LESSEE, "slot 109 stands for the lessee (name_index)");
    CHECK(save_slot_user(0x1068) == LESSEE, "break rewards: slot ID 0x1068 -> the lessee");
    CHECK(reg_icon[109] == reg_icon[145], "slot 109 shows the lessee's icon");
    CHECK(s_dress[4] == LESSEE, "slot 109's size record shows the lessee");
    gu_tally(idx, 1, 0, 1200);
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "a second tally in the same quest keeps the lease");
    gu_tally(idx, 0, 1, 1250);
    hook(stats_hunted_c, (uint32_t)g_quest, 0x65, 0, &r);
    CHECK(!r && (R[R1] & 0xffff) == 0x1068, "hunted in this quest -> the leased slot");
    CHECK(gu_writer(idx) == 3, "quest end: new largest and smallest");
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 1, "hunts by em ID from the store");
    hook(save_captures_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 1, "captures by em ID from the store");
    hook(save_hunts_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 2, "hunts + captures by em ID from the store");
    hook(save_size_read_c, 0, 0x65, 1, &r);
    CHECK(r && R[R0] == 1250, "largest by em ID from the store");
    hook(save_size_read_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 1200, "smallest by em ID from the store");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed (GU's slot 109 included)");
    quest(99001);                           /* the same quest again: bigger and smaller */
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "a replay keeps slot 109");
    gu_tally(109, 2, 0, 1300);
    gu_tally(109, 0, 0, 1100);
    CHECK(gu_writer(109) == 3, "second quest: new largest 1300 and smallest 1100");
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1150);
    CHECK(gu_writer(109) == 0, "third quest: size 1150 sets no record");
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 4, "4 hunts in the store");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed");
    return g_fails;                         /* test_save.py then reads the store bytes itself */
}

/* the owner of slot 109 (a tail) counts again: the lease ends, the slot is its own */
int test_takeback(void)
{
    int r;
    test_lessee();
    snapshot();
    quest(10790);                           /* Dalamadur's quest */
    CHECK(save_slot_tally(4, g_quest) == 109, "the tail counts in its slot 109");
    CHECK(save_lessee_of_index(109) == -1 && save_slot_user(0x1068) == 4, "slot 109 is the tail's again");
    CHECK(reg_icon[109] == 1000u + 109 && s_dress[4] == -1, "slot 109 as built again");
    gu_tally(109, 1, 0, 0);
    CHECK(gu_writer(109) == -1, "GU writes the tail's own record");
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 4, "the lessee's numbers stay in the store");
    CHECK(changed_outside(0, 0) == 0, "no byte changed");
    return g_fails;
}

/* an owner counted in its slot while a lessee holds it in the same quest: the lessee's entry moves */
int test_conflict(void)
{
    fresh();
    quest(99001);
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "lease 109");
    gu_tally(109, 1, 0, 1000);
    CHECK(save_slot_tally(4, g_quest) == 109, "the tail takes 109 back");
    CHECK(save_lessee_of_index(111) == LESSEE, "the lessee moved to slot 111");
    CHECK(FIELD(uint16_t, g_quest, 0x110 + 8 * 111 + 4) == 1 && FIELD(uint32_t, g_quest, 0x110 + 8 * 109 + 4) == 0,
          "its quest entry moved with it");
    CHECK(save_slot_tally(LESSEE, g_quest) == 111, "its next tally counts in 111");
    return g_fails;
}

/* two lessees in one quest, then the next quest's lessee reuses the slot */
int test_two(void)
{
    fresh();
    quest(99001);
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "lessee 1 -> 109");
    gu_tally(109, 1, 0, 1000);
    CHECK(save_slot_tally(LESSEE2, g_quest) == 111, "lessee 2 -> 111 (109 counted in this quest)");
    CHECK(reg_icon[111] == reg_icon[146], "slot 111 shows lessee 2");
    gu_tally(111, 1, 0, 1000);
    CHECK(gu_writer(109) == 3 && gu_writer(111) == 3, "both written to the store");
    quest(99002);
    CHECK(save_slot_tally(LESSEE2, g_quest) == 111, "a lessee keeps its slot when it is free");
    quest(99001);
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "lessee 1 takes 109 again");
    CHECK(save_lessee_of_index(111) == LESSEE2, "lessee 2's old lease stays until needed");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed");
    return g_fails;
}

/* data in the block that is not a store (no magic): never written, lessees not recorded */
int test_foreign(void)
{
    int r;
    fresh();
    for (uint32_t i = STORE_OFF + 8; i < STORE_OFF + 64; i++) g_user[i] = (uint8_t)i;
    snapshot();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 0, "hooks answer (GU's slot not written), no record set");
    hook(save_hunts_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 0, "reads 0");
    CHECK(changed_outside(0, 0) == 0, "no byte changed");
    return g_fails;
}

/* a valid store whose bytes were changed by someone else (check word wrong), and a newer version: left alone */
int test_damaged(void)
{
    fresh();
    store_build(3, 0x65, 1);
    g_user[STORE_OFF + 16 + 2] ^= 0x40;
    snapshot();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 0, "damaged: hooks answer, nothing recorded");
    CHECK(changed_outside(0, 0) == 0, "damaged: no byte changed");
    fresh();
    store_build(3, 0x65, 2);
    snapshot();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 0, "version 2: hooks answer, nothing recorded");
    CHECK(changed_outside(0, 0) == 0, "version 2: no byte changed");
    return g_fails;
}

/* a full store (232 records): a new monster is not recorded, nothing written past the reserved block */
int test_full(void)
{
    int r;
    fresh();
    store_build(232, 0x2000, 1);
    snapshot();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 0, "full: hooks answer, nothing recorded");
    CHECK(changed_outside(0, 0) == 0, "full: no byte changed");
    fresh();
    store_build(231, 0x2000, 1);
    snapshot();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 3, "231 records: the 232nd is added");
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 1 && FIELD(uint16_t, g_user, STORE_OFF + 6) == 232, "record 232 added");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed");
    return g_fails;
}

/* GU's count cap: 9998 + 5 = 9999 */
int test_cap(void)
{
    int r;
    fresh();
    store_build(1, 0x65, 1);
    FIELD(uint16_t, g_user, STORE_OFF + 16 + 2) = 9998;
    FIELD(uint32_t, g_user, STORE_OFF + 8) = fnv(fnv(2166136261u, g_user + STORE_OFF + 4, 4), g_user + STORE_OFF + 16, 12);
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 5, 0, 0);
    gu_writer(109);
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 9999, "hunts capped at 9999");
    return g_fails;
}

/* no character loaded: the hooks neither crash nor write */
int test_nochar(void)
{
    int r;
    fresh();
    s_userinfo = 0;
    quest(99001);
    CHECK(save_slot_tally(LESSEE, g_quest) == 109, "a lease without a character");
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 0, "hooks answer, nothing recorded");
    hook(save_hunts_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 0, "reads 0");
    hook(save_writing_c, 0, 0, 0, &r);
    s_userinfo = (uint32_t)g_user;
    CHECK(changed_outside(0, 0) == 0, "no byte changed");
    return g_fails;
}

/* a character load ends every lease */
int test_loaded(void)
{
    int r;
    fresh();
    quest(99001);
    save_slot_tally(LESSEE, g_quest);
    hook(save_loaded_c, 0, 0, 0, &r);
    CHECK(save_lessee_of_index(109) == -1 && reg_icon[109] == 1000u + 109 && s_dress[4] == -1, "lease ended");
    return g_fails;
}

/* a size record's crown and cm (0x67310), as the Notes page asks by the monster's ID */
static void size_call(uint32_t id, uint32_t size, uint8_t *out, int *ret)
{
    for (int i = 0; i < 8; i++) R[i] = 0;
    R[R1] = id, R[R2] = size, R[R3] = (uint32_t)out;
    out[0] = 0x55;
    FIELD(float, out, 4) = -1.0f;
    *ret = size_lookup_c(R);
}

int test_size(void)
{
    static const struct { uint16_t size; uint8_t crown; } rows[] = {
        { 90, 3 }, { 91, 255 }, { 98, 255 }, { 114, 255 }, { 115, 2 }, { 122, 2 }, { 123, 1 }, { 130, 1 } };
    uint8_t out[8] __attribute__((aligned(4)));
    int r;
    fresh();
    size_call(0x105, 100, out, &r);
    CHECK(!r && (R[R1] & 0xffff) == 0x106a && out[0] == 0x55, "a fixed slot: GU's function, under its slot's ID");
    size_call(0x01, 100, out, &r);
    CHECK(!r && R[R1] == 0x01 && out[0] == 0x55, "a GU monster ID passes through");
    size_call(0x1068, 100, out, &r);
    CHECK(!r && R[R1] == 0x1068 && out[0] == 0x55, "a slot ID (the quest result) passes through");
    for (uint32_t i = 0; i < sizeof rows / sizeof rows[0]; i++) {
        size_call(0x65, rows[i].size, out, &r);
        float want = (float)rows[i].size * 21.636f, diff = FIELD(float, out, 4) - want;
        CHECK(r && out[0] == rows[i].crown, "a lessee: the crown by its [size] ratios");
        CHECK(diff < 0.01f && diff > -0.01f, "a lessee: size % x its base size");
    }
    size_call(0x65, 0, out, &r);
    CHECK(r && out[0] == 255 && FIELD(float, out, 4) == -1.0f, "no record: no crown, cm not written");
    size_call(0x66, 100, out, &r);
    CHECK(r && out[0] == 255 && FIELD(float, out, 4) == -1.0f, "a lessee without size data: no crown, cm not written");
    return g_fails;
}

/* a few bits under a key no monster has (the armor "listed" bits past GU's arrays, module/gear.c) */
int save_bits_get(uint32_t key, uint32_t bit);
void save_bits_set(uint32_t key, uint32_t bit);

int test_bits(void)
{
    int r;
    fresh();
    CHECK(!save_bits_get(0xf001, 0), "no store yet: a bit reads 0");
    CHECK(changed_outside(0, 0) == 0, "reading writes nothing, the block stays empty");
    save_bits_set(0xf001, 0);
    CHECK(save_bits_get(0xf001, 0) && !save_bits_get(0xf001, 1) && !save_bits_get(0xf002, 0), "that bit of that key only");
    save_bits_set(0xf001, 17);
    save_bits_set(0xf001, 79);
    CHECK(save_bits_get(0xf001, 0) && save_bits_get(0xf001, 17) && save_bits_get(0xf001, 79), "all kept (the check word still fits, or they would read 0)");
    CHECK(FIELD(uint16_t, g_user, STORE_OFF + 6) == 1 && FIELD(uint16_t, g_user, STORE_OFF + 16) == 0xf001, "one record, under the key");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed");
    snapshot();
    save_bits_set(0xf001, 80);
    CHECK(!save_bits_get(0xf001, 80) && changed_outside(0, 0) == 0, "a bit past the record: not kept, no byte changed");
    quest(99001);                           /* a monster's record next to the key's */
    save_slot_tally(LESSEE, g_quest);
    gu_tally(109, 1, 0, 1000);
    CHECK(gu_writer(109) == 3, "the monster's record is added");
    save_bits_set(0xf002, 3);
    hook(save_hunts_id_c, 0, 0x65, 0, &r);
    CHECK(r && R[R0] == 1 && save_bits_get(0xf001, 79) && save_bits_get(0xf002, 3), "both keys and the monster's numbers stay");
    CHECK(changed_outside(STORE_OFF, STORE_END) == 0, "nothing outside the store changed");
    fresh();                                /* data in the block that is not a store */
    for (uint32_t i = STORE_OFF + 8; i < STORE_OFF + 64; i++) g_user[i] = (uint8_t)i;
    snapshot();
    save_bits_set(0xf001, 0);
    CHECK(!save_bits_get(0xf001, 0) && changed_outside(0, 0) == 0, "not a store: left alone");
    fresh();                                /* a full store */
    store_build(232, 0x2000, 1);
    snapshot();
    save_bits_set(0xf001, 0);
    CHECK(!save_bits_get(0xf001, 0) && changed_outside(0, 0) == 0, "full: dropped, no byte changed");
    fresh();                                /* no character */
    s_userinfo = 0;
    save_bits_set(0xf001, 0);
    CHECK(!save_bits_get(0xf001, 0), "no character: reads 0");
    s_userinfo = (uint32_t)g_user;
    CHECK(changed_outside(0, 0) == 0, "no character: no byte changed");
    return g_fails;
}

/* the store as test_lessee leaves it, for test_save.py */
uint8_t *store_bytes(void) { return g_user + STORE_OFF; }
