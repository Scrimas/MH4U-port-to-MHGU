/* modsave.c: the split and the merge of one character's slot (notes/mod-save-format.md). Pure: no game call, no
 * memcpy (freestanding). tools/modsave.py is the reference: every record, in the same order, byte for byte
 * (tools/test_modsave.py runs this code under unicorn on the same slots and compares the files). */
#include "modsave.h"

#define BOX 0x278u
#define BOX_N 2300u
#define POUCH 0x27BFu
#define POUCH_N 32u
#define LOADOUTS 0x17CFu
#define LOADOUT_N 24u
#define LOADOUT_SZ 170u
#define LOADOUT_ITEMS 42u
#define OBTAINED 0x22497u
#define EQBOX 0x62EEu
#define EQBOX_N 2000u
#define ENTRY 36u
#define WORN 0x23B39u
#define MYSETS 0x208C8u
#define MYSET_N 40u
#define MYSET 0x88u
#define WORN_CACHE 0x10Cu
#define CARD_GEAR 0xC7211u
#define CARD_HISTORY 0xC7AD5u
#define HISTORY_N 10u
#define HISTORY 160u
#define MELDING 0x227A7u
#define MELDING_N 10u
#define MELDING_SZ 420u
#define RESERVED_N 3444u
#define QUEST_MAP_BITS 0x800u
#define NONE 0xFFFFu

#define GU_ITEM_FIRST_ADDED 2977u
#define GU_DECO_LO 2889u
#define GU_DECO_HI 2899u
#define GU_ARMOR 1287u
#define GU_DECO_CREATE 275u
#define STARTER_CLASS 1u
#define STARTER_ID 1u

enum { K_ITEM = 1, K_GEAR, K_BYTES, K_REGION, K_BITS, K_QUESTS, K_ASIDE };

static const uint16_t GU_WEAPONS[15] = { 137, 129, 132, 127, 109, 0, 110, 127, 110, 115, 108, 126, 112, 83, 81 };
static const uint16_t GU_ARMOR_CREATE[5] = { 563, 554, 538, 517, 548 };
static const uint16_t GU_WEAPON_CREATE[15] = { 95, 82, 84, 86, 84, 0, 98, 82, 81, 80, 90, 86, 75, 66, 63 };
static const uint32_t WEAPON_CLASS[2] = { 0x240u, 0x23B47u };
static const uint32_t QUEST_MAPS[3] = { 0x2C77u, 0x2D77u, 0x2E77u };
static const uint32_t REGISTER[2][2] = { { 0x11D05Au, 2u }, { 0x11D05Eu, 4u } };
static const uint32_t TALLIES[3][2] = { { 0x5EA6u, 2u }, { 0x5FB8u, 2u }, { 0x60CAu, 4u } };
static const uint8_t LINK_MAGIC[4] = { 'M', 'H', 'D', 'L' };

/* ---------------------------------------------------------------------------------------------- helpers */

uint32_t ms_fnv(const uint8_t *p, uint32_t n, uint32_t h)
{
    for (uint32_t i = 0; i < n; i++) h = (h ^ p[i]) * 0x01000193u;
    return h;
}

static uint32_t rd16(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8; }
static uint32_t rd32(const uint8_t *p) { return rd16(p) | rd16(p + 2) << 16; }
static void wr16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void wr32(uint8_t *p, uint32_t v) { wr16(p, v); wr16(p + 2, v >> 16); }
static void cpy(uint8_t *d, const uint8_t *s, uint32_t n) { while (n--) *d++ = *s++; }
static void zero(uint8_t *d, uint32_t n) { while (n--) *d++ = 0; }
static int same(const uint8_t *a, const uint8_t *b, uint32_t n) { while (n--) if (*a++ != *b++) return 0; return 1; }
static int any(const uint8_t *a, uint32_t n) { while (n--) if (*a++) return 1; return 0; }

static uint32_t getbit(const uint8_t *s, uint32_t o, uint32_t b) { return s[o + (b >> 3)] >> (b & 7) & 1u; }
static void setbit(uint8_t *s, uint32_t o, uint32_t b, uint32_t v)
{
    uint8_t *p = s + o + (b >> 3), m = (uint8_t)(1u << (b & 7));
    *p = v ? (uint8_t)(*p | m) : (uint8_t)(*p & ~m);
}
static uint32_t getbits(const uint8_t *s, uint32_t o, uint32_t b, uint32_t n)
{
    uint32_t v = 0;
    for (uint32_t i = 0; i < n; i++) v |= getbit(s, o, b + i) << i;
    return v;
}
static void setbits(uint8_t *s, uint32_t o, uint32_t b, uint32_t n, uint32_t v)
{
    for (uint32_t i = 0; i < n; i++) setbit(s, o, b + i, v >> i & 1u);
}

static int item_added(uint32_t i) { return i >= GU_ITEM_FIRST_ADDED || (i >= GU_DECO_LO && i <= GU_DECO_HI); }

/* entry kind: 0 empty, 1 armor (part in *c), 2 talisman, 3 weapon (class in *c), 4 other */
static int kind_of(const uint8_t *e, uint32_t *c)
{
    uint32_t t = rd16(e) & 0x1Fu;
    *c = 0;
    if (!t) return 0;
    if (t <= 5) { *c = t; return 1; }
    if (t == 6) return 2;
    if (t <= 21) { *c = t - 7; return 3; }
    *c = t;
    return 4;
}

static int entry_added(const uint8_t *e)
{
    uint32_t c, k = (uint32_t)kind_of(e, &c), i = rd16(e + 2);
    return (k == 1 && i >= GU_ARMOR) || (k == 3 && i >= GU_WEAPONS[c]);
}

static void jewels_clean(uint8_t *j)            /* 3 x u16: the vanilla ones kept packed from the first */
{
    uint32_t d[3], n = 0;
    for (uint32_t x = 0; x < 3; x++) {
        uint32_t v = rd16(j + 2 * x);
        if (v && !item_added(v)) d[n++] = v;
    }
    for (uint32_t x = 0; x < 3; x++) wr16(j + 2 * x, x < n ? d[x] : 0);
}

static void entry_clean(const uint8_t *e, uint8_t *out)
{
    uint32_t c;
    cpy(out, e, ENTRY);
    jewels_clean(out + 6);
    if (kind_of(out, &c) == 1 && rd16(out + 4) >= GU_ARMOR) {
        wr16(out + 4, 0);
        wr16(out, rd16(out) & ~(0x1Fu << 10));
    }
}

static void starter_entry(uint8_t *e)
{
    zero(e, ENTRY);
    wr16(e, 7 + STARTER_CLASS);
    wr16(e + 2, STARTER_ID);
}

/* the bit maps keyed by an added ID: (offset, first added bit, bits), the order of tools/modsave.py bit_ranges() */
static uint32_t bit_range(uint32_t k, uint32_t *o, uint32_t *first)
{
    if (k == 0) { *o = OBTAINED; *first = GU_ITEM_FIRST_ADDED; return 3008; }
    k--;
    if (k < 10) {
        uint32_t p = k / 2, listed = 4u * GU_ARMOR_CREATE[p];
        *o = 0x3907u + 576u * p + (k & 1 ? 288u : 0);
        *first = k & 1 ? (listed > GU_ARMOR ? listed : GU_ARMOR) : listed;
        return 288 * 8;
    }
    k -= 10;
    if (k < 45) {
        uint32_t t = k / 3, w = k % 3;
        if (w == 0) { *o = 0x36AFu + 40u * t; *first = GU_WEAPON_CREATE[t]; return 160; }
        if (w == 1) {
            *o = 0x36AFu + 40u * t + 20;
            *first = GU_WEAPONS[t] > GU_WEAPON_CREATE[t] ? GU_WEAPONS[t] : GU_WEAPON_CREATE[t];
            return 160;
        }
        *o = 0x45DFu + 128u * t; *first = GU_WEAPONS[t]; return 1024;
    }
    k -= 45;
    switch (k) {
    case 0: *o = 0x4D5Fu; *first = GU_ARMOR; return 5248;
    case 1: *o = 0x31A7u; *first = GU_DECO_CREATE; return 288;
    case 2: *o = 0x31CBu; *first = GU_DECO_CREATE; return 288;
    case 3: *o = 0x32B7u; *first = 123; return 128;
    case 4: *o = 0x32C7u; *first = 123; return 128;
    case 5: case 6: case 7: *o = 0x11CFD4u + 12u * (k - 5); *first = 89; return 96;
    }
    return 0;
}
#define BIT_RANGES (1u + 10u + 45u + 8u)

/* ---------------------------------------------------------------------------------------------- split */

struct out { uint8_t *f; uint32_t cap, n, left; uint8_t *slot; int clean; };

/* a record header + payload into the file when it fits; 1 = written (its change is then made) */
static int put(struct out *w, uint32_t kind, uint32_t len)
{
    if (w->n + 4 + len > w->cap) { w->left++; return 0; }
    w->f[w->n] = (uint8_t)kind;
    w->f[w->n + 1] = 0;
    wr16(w->f + w->n + 2, len);
    return 1;
}
#define PAY(w) ((w)->f + (w)->n + 4)
#define DONE(w, len) ((w)->n += 4 + (len))

/* bytes: (offset, n, original, vanilla); the vanilla bytes go to the slot */
static void put_bytes(struct out *w, uint32_t o, uint32_t n, const uint8_t *van)
{
    if (!put(w, K_BYTES, 6 + 2 * n)) return;
    uint8_t *p = PAY(w);
    wr32(p, o); wr16(p + 4, n);
    cpy(p + 6, w->slot + o, n);
    cpy(p + 6 + n, van, n);
    DONE(w, 6 + 2 * n);
    if (w->clean) cpy(w->slot + o, van, n);
}

static void put_region(struct out *w, uint32_t o, uint32_t n)
{
    if (!put(w, K_REGION, 6 + n)) return;
    uint8_t *p = PAY(w);
    wr32(p, o); wr16(p + 4, n);
    cpy(p + 6, w->slot + o, n);
    DONE(w, 6 + n);
    if (w->clean) zero(w->slot + o, n);
}

static uint8_t s_added[EQBOX_N], s_empty0[EQBOX_N];

int ms_split(uint8_t *slot, const struct ms_quest *q, uint32_t qn, uint32_t link, uint32_t gen,
             const uint8_t *aside, uint32_t aside_n, uint8_t *file, uint32_t cap, int clean, uint32_t *left)
{
    struct out w = { file, cap, MS_HEADER, 0, slot, clean };
    uint8_t v[MYSET], e[ENTRY];
    uint32_t worn[7], van[7], i, k, j, placeholder = NONE, c;
    if (cap < MS_HEADER) return -1;
    for (i = 0; i < EQBOX_N; i++) {
        s_added[i] = (uint8_t)entry_added(slot + EQBOX + ENTRY * i);
        s_empty0[i] = (uint8_t)!any(slot + EQBOX + ENTRY * i, ENTRY);
    }
    /* the worn gear */
    int hit = 0;
    for (k = 0; k < 7; k++) {
        worn[k] = van[k] = rd16(slot + WORN + 2 * k);
        if (worn[k] != NONE && worn[k] < EQBOX_N && s_added[worn[k]]) hit = 1;
    }
    if (hit) {
        uint32_t starter_at = NONE, cls_new = 0, wcls = 0;
        for (k = 1; k < 7; k++)
            if (van[k] != NONE && van[k] < EQBOX_N && s_added[van[k]]) van[k] = NONE;
        if (worn[0] != NONE && worn[0] < EQBOX_N && s_added[worn[0]]) {
            uint32_t got = NONE;
            kind_of(slot + EQBOX + ENTRY * worn[0], &wcls);
            for (int pass = 0; pass < 2 && got == NONE; pass++)
                for (j = 0; j < EQBOX_N; j++) {
                    if (kind_of(slot + EQBOX + ENTRY * j, &c) == 3 && !s_added[j] && (pass || c == wcls)) {
                        got = j, cls_new = c;
                        break;
                    }
                }
            if (got == NONE) {
                for (j = 0; j < EQBOX_N && !s_empty0[j]; j++) ;
                if (j == EQBOX_N) return -1;            /* nothing for the hunter to hold */
                got = starter_at = j, cls_new = STARTER_CLASS;
            }
            van[0] = got;
        }
        for (k = 0; k < 7; k++) wr16(v + 2 * k, van[k]);
        put_bytes(&w, WORN, 14, v);
        if (starter_at != NONE) {
            starter_entry(e);
            put_bytes(&w, EQBOX + ENTRY * starter_at, ENTRY, e);
        }
        if (van[0] != worn[0])
            for (k = 0; k < 2; k++)
                if (slot[WEAPON_CLASS[k]] != cls_new) {
                    uint8_t b = (uint8_t)cls_new;
                    put_bytes(&w, WEAPON_CLASS[k], 1, &b);
                }
        if (van[0] != worn[0]) placeholder = van[0];
    }
    /* the slot header's copies of the worn pieces */
    for (k = 0; k < 7; k++) {
        uint32_t o = WORN_CACHE + 44 * k + 4;
        if (!any(slot + o, ENTRY)) continue;
        if (entry_added(slot + o)) {
            if (k == 0 && placeholder != NONE) {
                const uint8_t *p = slot + EQBOX + ENTRY * placeholder;
                if (!any(p, ENTRY)) starter_entry(e); else entry_clean(p, e);
            } else zero(e, ENTRY);
        } else entry_clean(slot + o, e);
        if (!same(e, slot + o, ENTRY)) put_bytes(&w, o, ENTRY, e);
    }
    /* the own Guild Card's equipment snapshot */
    for (k = 0; k < 7; k++) {
        uint32_t o = CARD_GEAR + 44 * k;
        uint8_t cg[44], e36[ENTRY];
        if (!any(slot + o, 44)) continue;
        cpy(cg, slot + o, 44);
        zero(e36, ENTRY);
        cpy(e36, cg, 4);
        if (entry_added(e36)) zero(cg, 44);
        else {
            jewels_clean(cg + 8);
            if (kind_of(e36, &c) == 1 && rd16(cg + 0x28) >= GU_ARMOR) wr16(cg + 0x28, 0);
        }
        if (!same(cg, slot + o, 44)) put_bytes(&w, o, 44, cg);
    }
    /* the card's quest history */
    for (k = 0; k < HISTORY_N; k++) {
        uint32_t o = CARD_HISTORY + HISTORY * k, id = rd16(slot + o + 6);
        for (j = 0; j < qn && q[j].id != id; j++) ;
        if (j < qn) {
            uint8_t z[HISTORY];
            zero(z, HISTORY);
            put_bytes(&w, o, HISTORY, z);
        }
    }
    /* the Item Register touch panels */
    for (k = 0; k < 2; k++)
        for (j = 0; j < REGISTER[k][1]; j++) {
            uint32_t o = REGISTER[k][0] + 2 * j;
            uint8_t z[2] = { 0, 0 };
            if (rd16(slot + o) && item_added(rd16(slot + o))) put_bytes(&w, o, 2, z);
        }
    /* the Melding Pot's talismans */
    for (k = 0; k < MELDING_N; k++)
        for (j = 0; j < 3; j++) {
            uint32_t o = MELDING + MELDING_SZ * k + 4 + ENTRY * j;
            if (!any(slot + o, ENTRY)) continue;
            entry_clean(slot + o, e);
            if (!same(e, slot + o, ENTRY)) put_bytes(&w, o, ENTRY, e);
        }
    /* the dummy entries' tallies (D2) */
    for (k = 0; k < 3; k++) {
        uint32_t o = TALLIES[k][0] + TALLIES[k][1] * 105, n = TALLIES[k][1] * 7;
        if (any(slot + o, n)) put_region(&w, o, n);
    }
    /* My Sets */
    for (k = 0; k < MYSET_N; k++) {
        uint32_t o = MYSETS + MYSET * k;
        cpy(v, slot + o, MYSET);
        for (j = 0; j < 7; j++) {
            uint32_t b = rd16(v + 0x30 + 2 * j);
            if (b != NONE && b < EQBOX_N && s_added[b]) {
                wr16(v + 0x30 + 2 * j, NONE);
                zero(v + 0x3E + 6 * j, 6);
            }
            jewels_clean(v + 0x3E + 6 * j);
        }
        if (!same(v, slot + o, MYSET)) put_bytes(&w, o, MYSET, v);
    }
    /* the reserved block past the link record: runs of non-zero bytes, gaps under 8 zeros inside a run */
    {
        uint32_t lo = MS_RESERVED + MS_LINK_N, hi = MS_RESERVED + RESERVED_N, a = lo;
        while (a < hi) {
            if (!slot[a]) { a++; continue; }
            uint32_t b = a, z = 0;
            while (b < hi && z < 8) { z = slot[b] ? 0 : z + 1; b++; }
            b -= z;
            put_region(&w, a, b - a);
            a = b;
        }
    }
    /* bit maps: runs of set bits */
    for (k = 0; k < BIT_RANGES; k++) {
        uint32_t o, first, n = bit_range(k, &o, &first), b = first;
        while (b < n) {
            if (!getbit(slot, o, b)) { b++; continue; }
            uint32_t x = b;
            while (x < n && x - b < 0xFFFF && getbit(slot, o, x)) x++;
            if (put(&w, K_BITS, 8)) {
                uint8_t *p = PAY(&w);
                wr32(p, o); wr16(p + 4, b); wr16(p + 6, x - b);
                DONE(&w, 8);
                if (clean) for (uint32_t y = b; y < x; y++) setbit(slot, o, y, 0);
            }
            b = x;
        }
    }
    /* quest bits by quest ID */
    for (k = 0; k < 3; k++) {
        uint32_t n = 0;
        for (j = 0; j < qn; j++) if (q[j].index < QUEST_MAP_BITS && getbit(slot, QUEST_MAPS[k], q[j].index)) n++;
        if (!n || !put(&w, K_QUESTS, 3 + 4 * n)) continue;
        uint8_t *p = PAY(&w);
        p[0] = (uint8_t)k; wr16(p + 1, n);
        n = 0;
        for (j = 0; j < qn; j++)
            if (q[j].index < QUEST_MAP_BITS && getbit(slot, QUEST_MAPS[k], q[j].index)) wr32(p + 3 + 4 * n++, q[j].id);
        DONE(&w, 3 + 4 * n);
        if (clean)
            for (j = 0; j < qn; j++) if (q[j].index < QUEST_MAP_BITS) setbit(slot, QUEST_MAPS[k], q[j].index, 0);
    }
    /* gear */
    for (i = 0; i < EQBOX_N; i++) {
        uint32_t o = EQBOX + ENTRY * i;
        if (s_added[i]) {
            if (!put(&w, K_GEAR, 2 + ENTRY)) continue;
            wr16(PAY(&w), i);
            cpy(PAY(&w) + 2, slot + o, ENTRY);
            DONE(&w, 2 + ENTRY);
            if (clean) zero(slot + o, ENTRY);
        } else if (kind_of(slot + o, &c) != 0) {
            entry_clean(slot + o, e);
            if (!same(e, slot + o, ENTRY)) put_bytes(&w, o, ENTRY, e);
        }
    }
    /* items */
    for (k = 0; k < 2; k++) {
        uint32_t o = k ? POUCH : BOX, n = k ? POUCH_N : BOX_N;
        for (i = 0; i < n; i++) {
            uint32_t id = getbits(slot, o, 19 * i, 12), cnt = getbits(slot, o, 19 * i + 12, 7);
            if (!id || !item_added(id) || !put(&w, K_ITEM, 6)) continue;
            uint8_t *p = PAY(&w);
            p[0] = (uint8_t)k; wr16(p + 1, i); wr16(p + 3, id); p[5] = (uint8_t)cnt;
            DONE(&w, 6);
            if (clean) setbits(slot, o, 19 * i, 19, 0);
        }
    }
    for (k = 0; k < LOADOUT_N; k++)
        for (j = 0; j < 32; j++) {
            uint32_t o = LOADOUTS + LOADOUT_SZ * k + LOADOUT_ITEMS + 4 * j, id = rd16(slot + o);
            if (!id || !item_added(id) || !put(&w, K_ITEM, 6)) continue;
            uint8_t *p = PAY(&w);
            p[0] = 2; wr16(p + 1, 32 * k + j); wr16(p + 3, id); p[5] = (uint8_t)rd16(slot + o + 2);
            DONE(&w, 6);
            if (clean) zero(slot + o, 4);
        }
    /* records the last merge could not place */
    for (i = 0; i + 4 <= aside_n;) {
        uint32_t n = 4 + rd16(aside + i + 2);
        if (i + n > aside_n) break;
        if (put(&w, K_ASIDE, n)) { cpy(PAY(&w), aside + i, n); DONE(&w, n); }
        i += n;
    }
    if (clean) ms_set_link(slot, link, gen, MS_SPLIT);
    /* the header */
    uint8_t *f = file;
    f[0] = 'M'; f[1] = 'H'; f[2] = 'D'; f[3] = 'E';
    wr16(f + 4, 1); wr16(f + 6, 0); wr32(f + 8, w.n);
    wr32(f + 16, link); wr32(f + 20, gen); wr32(f + 24, clean ? ms_fnv(slot, MS_SLOT_SIZE, 0x811C9DC5u) : 0);
    wr32(f + 28, 0);
    wr32(f + 12, ms_fnv(f + 16, w.n - 16, ms_fnv(f, 12, 0x811C9DC5u)));
    if (left) *left = w.left;
    return (int)w.n;
}

/* ---------------------------------------------------------------------------------------------- link */

int ms_link(const uint8_t *slot, uint32_t *link, uint32_t *gen, uint32_t *state)
{
    const uint8_t *p = slot + MS_RESERVED;
    if (!same(p, LINK_MAGIC, 4)) return 0;
    *link = rd32(p + 4); *gen = rd32(p + 8); *state = p[12];
    return 1;
}

void ms_set_link(uint8_t *slot, uint32_t link, uint32_t gen, uint32_t state)
{
    uint8_t *p = slot + MS_RESERVED;
    cpy(p, LINK_MAGIC, 4);
    wr32(p + 4, link); wr32(p + 8, gen);
    p[12] = (uint8_t)state; p[13] = p[14] = p[15] = 0;
}

/* ---------------------------------------------------------------------------------------------- merge */

int ms_parse(const uint8_t *f, uint32_t len, uint32_t *used, uint32_t *link, uint32_t *gen, uint32_t *slot_hash)
{
    if (len < MS_HEADER || f[0] != 'M' || f[1] != 'H' || f[2] != 'D' || f[3] != 'E') return -1;
    uint32_t n = rd32(f + 8);
    if (n < MS_HEADER || n > len) return -1;
    if (rd32(f + 12) != ms_fnv(f + 16, n - 16, ms_fnv(f, 12, 0x811C9DC5u))) return -1;
    for (uint32_t o = MS_HEADER; o < n;) {                  /* every record inside the bytes used */
        if (o + 4 > n || o + 4 + rd16(f + o + 2) > n) return -1;
        o += 4 + rd16(f + o + 2);
    }
    *used = n; *link = rd32(f + 16); *gen = rd32(f + 20); *slot_hash = rd32(f + 24);
    return 0;
}

struct jrn { uint8_t *b; uint32_t cap, n; int full; };

/* journal the bytes [o, o + n) of the slot, then they may be written */
static int jsave(struct jrn *j, const uint8_t *slot, uint32_t o, uint32_t n)
{
    if (j->full || j->n + 8 + n > j->cap) { j->full = 1; return 0; }
    wr32(j->b + j->n, o); wr16(j->b + j->n + 4, n);
    cpy(j->b + j->n + 6, slot + o, n);
    wr16(j->b + j->n + 6 + n, n);
    j->n += 8 + n;
    return 1;
}

void ms_restore(uint8_t *slot, const uint8_t *journal, uint32_t jlen)
{
    uint32_t end = jlen;
    while (end >= 8) {
        uint32_t n = rd16(journal + end - 2), at = end - 8 - n, o = rd32(journal + at);
        cpy(slot + o, journal + at + 6, n);
        end = at;
    }
}

struct asd { uint8_t *b; uint32_t cap, n; int full; };

static void aside_put(struct asd *a, uint32_t kind, uint32_t flags, const uint8_t *p, uint32_t len)
{
    if (a->full || a->n + 4 + len > a->cap) { a->full = 1; return; }
    a->b[a->n] = (uint8_t)kind; a->b[a->n + 1] = (uint8_t)flags; wr16(a->b + a->n + 2, len);
    cpy(a->b + a->n + 4, p, len);
    a->n += 4 + len;
}

static uint16_t s_moved[EQBOX_N];

/* record r of the file (aside records unwrapped): kind, flags, payload, length; 0 when past the end */
static uint32_t rec_at(const uint8_t *f, uint32_t used, uint32_t *o, uint32_t *kind, uint32_t *flags,
                       const uint8_t **p, uint32_t *len)
{
    if (*o + 4 > used) return 0;
    *kind = f[*o]; *flags = f[*o + 1]; *len = rd16(f + *o + 2); *p = f + *o + 4;
    *o += 4 + *len;
    if (*kind == K_ASIDE && *len >= 4) {
        *kind = (*p)[0]; *flags = (*p)[1];
        uint32_t n = rd16(*p + 2);
        *p += 4;
        *len = n;
    }
    return 1;
}

int ms_merge(uint8_t *slot, const uint8_t *f, uint32_t len, const struct ms_quest *q, uint32_t qn,
             uint8_t *journal, uint32_t jcap, uint32_t *jlen, uint8_t *aside, uint32_t acap, uint32_t *alen,
             struct ms_stats *st)
{
    uint32_t used, link, gen, h, o, kind, fl, n, i, j;
    const uint8_t *p;
    struct jrn jr = { journal, jcap, 0, 0 };
    struct asd as = { aside, acap, 0, 0 };
    *jlen = 0; *alen = 0;
    zero((uint8_t *)st, sizeof *st);
    if (ms_parse(f, len, &used, &link, &gen, &h)) return -1;
    st->exact = ms_fnv(slot, MS_SLOT_SIZE, 0x811C9DC5u) == h;
    for (i = 0; i < EQBOX_N; i++) s_moved[i] = NONE;
    /* gear first: the references follow a piece that had to move */
    for (o = MS_HEADER; rec_at(f, used, &o, &kind, &fl, &p, &n);) {
        if (kind != K_GEAR || n < 2 + ENTRY) continue;
        i = rd16(p);
        if (i >= EQBOX_N) { aside_put(&as, kind, fl, p, n); continue; }
        if (same(slot + EQBOX + ENTRY * i, p + 2, ENTRY)) { s_moved[i] = (uint16_t)i; continue; }
        if (!any(slot + EQBOX + ENTRY * i, ENTRY)) j = i;
        else for (j = 0; j < EQBOX_N && any(slot + EQBOX + ENTRY * j, ENTRY); j++) ;
        if (j == EQBOX_N) { aside_put(&as, kind, fl, p, n); continue; }
        if (!jsave(&jr, slot, EQBOX + ENTRY * j, ENTRY)) break;
        cpy(slot + EQBOX + ENTRY * j, p + 2, ENTRY);
        s_moved[i] = (uint16_t)j;
        st->placed++;
        st->moved += j != i;
    }
    for (o = MS_HEADER; !jr.full && rec_at(f, used, &o, &kind, &fl, &p, &n);) {
        if (kind == K_BYTES) {
            uint32_t at = rd32(p), m = rd16(p + 4);
            if (n < 6 + 2 * m || at + m > MS_SLOT_SIZE) { aside_put(&as, kind, fl, p, n); continue; }
            const uint8_t *orig = p + 6, *van = p + 6 + m;
            if (same(slot + at, orig, m)) continue;
            if (!same(slot + at, van, m)) { st->kept++; continue; }
            if (!jsave(&jr, slot, at, m)) break;
            cpy(slot + at, orig, m);
            if (at == WORN && m == 14) {
                for (uint32_t x = 0; x < 7; x++) {
                    uint32_t b = rd16(orig + 2 * x);
                    if (b < EQBOX_N && s_moved[b] != NONE) wr16(slot + at + 2 * x, s_moved[b]);
                }
            } else if (at >= MYSETS && at < MYSETS + MYSET * MYSET_N && m == MYSET) {
                for (uint32_t x = 0; x < 7; x++) {
                    uint32_t b = rd16(orig + 0x30 + 2 * x);
                    if (b < EQBOX_N && s_moved[b] != NONE) wr16(slot + at + 0x30 + 2 * x, s_moved[b]);
                }
            }
            st->placed++;
        } else if (kind == K_REGION) {
            uint32_t at = rd32(p), m = rd16(p + 4);
            if (n < 6 + m || at + m > MS_SLOT_SIZE) { aside_put(&as, kind, fl, p, n); continue; }
            if (same(slot + at, p + 6, m)) continue;
            if (any(slot + at, m)) { st->kept++; continue; }
            if (!jsave(&jr, slot, at, m)) break;
            cpy(slot + at, p + 6, m);
            st->placed++;
        } else if (kind == K_BITS) {
            uint32_t at = rd32(p), b = rd16(p + 4), m = rd16(p + 6);
            if (n < 8 || at + ((b + m + 7) >> 3) > MS_SLOT_SIZE) { aside_put(&as, kind, fl, p, n); continue; }
            if (m && !jsave(&jr, slot, at + (b >> 3), ((b + m + 7) >> 3) - (b >> 3))) break;
            for (uint32_t x = b; x < b + m; x++) setbit(slot, at, x, 1);
            st->placed++;
        } else if (kind == K_QUESTS) {
            uint32_t m = p[0], c = rd16(p + 1);
            if (n < 3 + 4 * c || m > 2) { aside_put(&as, kind, fl, p, n); continue; }
            for (uint32_t x = 0; x < c; x++) {
                uint32_t id = rd32(p + 3 + 4 * x);
                for (j = 0; j < qn && q[j].id != id; j++) ;
                if (j < qn && q[j].index < QUEST_MAP_BITS) {
                    if (!jsave(&jr, slot, QUEST_MAPS[m] + (q[j].index >> 3), 1)) break;
                    setbit(slot, QUEST_MAPS[m], q[j].index, 1);
                } else {
                    uint8_t one[7];
                    one[0] = (uint8_t)m; wr16(one + 1, 1); wr32(one + 3, id);
                    aside_put(&as, K_QUESTS, 0, one, 7);
                }
            }
            st->placed++;
        } else if (kind == K_ITEM) {
            uint32_t s_ = p[0], at = rd16(p + 1), id = rd16(p + 3), cnt = p[5];
            if (n < 6) { aside_put(&as, kind, fl, p, n); continue; }
            if (s_ < 2) {
                uint32_t base = s_ ? POUCH : BOX, cap = s_ ? POUCH_N : BOX_N;
                if (at >= cap) { aside_put(&as, kind, fl, p, n); continue; }
                if (getbits(slot, base, 19 * at, 12) == id && getbits(slot, base, 19 * at + 12, 7) == cnt) continue;
                if (!getbits(slot, base, 19 * at, 12)) j = at;
                else for (j = 0; j < cap && getbits(slot, base, 19 * j, 12); j++) ;
                if (j == cap) { aside_put(&as, kind, fl, p, n); continue; }
                if (!jsave(&jr, slot, base + (19 * j >> 3), ((19 * j + 19 + 7) >> 3) - (19 * j >> 3))) break;
                setbits(slot, base, 19 * j, 12, id);
                setbits(slot, base, 19 * j + 12, 7, cnt);
            } else {
                if (s_ != 2 || at >= 32 * LOADOUT_N) { aside_put(&as, kind, fl, p, n); continue; }
                uint32_t lo = LOADOUTS + LOADOUT_SZ * (at / 32) + LOADOUT_ITEMS + 4 * (at % 32);
                if (rd16(slot + lo) == id && rd16(slot + lo + 2) == cnt) continue;
                if (rd16(slot + lo)) { aside_put(&as, kind, fl, p, n); continue; }
                if (!jsave(&jr, slot, lo, 4)) break;
                wr16(slot + lo, id); wr16(slot + lo + 2, cnt);
                j = at;
            }
            st->placed++;
            st->moved += j != at;
        } else if (kind != K_GEAR) {
            aside_put(&as, kind, fl, p, n);                 /* a kind this core doesn't know: kept */
        }
    }
    if (jr.full || as.full) {
        ms_restore(slot, journal, jr.n);
        return -2;
    }
    *jlen = jr.n; *alen = as.n;
    st->aside = 0;
    for (i = 0; i + 4 <= as.n; i += 4 + rd16(aside + i + 2)) st->aside++;
    return 0;
}
