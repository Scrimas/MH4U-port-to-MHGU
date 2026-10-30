/* dala_shah.c: Shah Dalamadur's crimson part states and their zones (goal D8). 4U em110 runs uEm024's code; every
 * routine below returns at once for em 24 (Dalamadur), as in 4U. C = read in code, S = strong, G = guess.
 *
 * 1. Crimson states (C): head work +0x6c..+0x70 = one byte per hitzone part 0..4 (1 = crimson). Readers: slot 48
 *    0x772cf0 only (alternate hitzone rows + the cond-7 word W+0x7a14 bits 1 / 0x10 / 8 / 4 / 2: dala_parts.c
 *    head_hitzones). Writers: spawn 0x76da60 (all 0), the re-roll 0x7753f4, slot 79 0x7751a4 (net), slot 36
 *    0x776074 (stage byte 48: all 1, placement 2, motion 41: not ported, slot 36 has no GU wiring). Scan of
 *    0x76c000..0x778000 for +0x6c..+0x70 / #108 (C).
 * 2. Re-roll 0x7753f4(this, var), called on motion end right before the end slot (vt+0x164) by the cat-2 handler
 *    0x76c7b4 (var = its 2.x number) and 0x770954 / 0x770ec0 / 0x7713ec (var 0), Shah only (C):
 *    - every machine: W+0x7a14 = 0;
 *    - only the controller (W+0x1d9 = GU this+0x7420, C): clear the 5 bytes (remember which were 1), draw the count
 *      n with 0x7751fc from 0xfdc830[rage] (calm {15, 40, 35, 10, 0}, enraged {0, 0, 50, 35, 15} percent for n = 1..5;
 *      zero weights skipped); n = 5 -> all five; else draw parts from 0xfdcab4[mode] until n are set, mode = var
 *      0..5 -> 1, 2, 0, 2, 0, 1, else 0 (for 2.x the placement the move ends in; the 7.x handlers pass 0, so
 *      mode 1 although they end in placement 0, C): mode 0 {15, 60, 10, 5, 10}, 1 {25, 5,
 *      25, 10, 35}, 2 {35, 5, 15, 35, 10}; a lone part (n = 1) is never part 3 in mode 0 nor part 1 in modes 1 / 2;
 *      a part crimson before is re-drawn up to 3 times (counters 0x7756b8). Random = 0x2b568c(*0xfb6b7c, 1) % 100 + 1.
 *      Here GU's general random 0x496f0 (the one setAction draws from, C): only the controller draws (S: any RNG).
 * 3. Multiplayer (C): 4U slot 78 0x7751cc copies the 5 bytes into the action message, slot 79 0x7751a4 back (em 24:
 *    nothing). The controller re-rolls just before the end slot picks the next action, so the next action message
 *    carries the new bytes and every machine runs that action with the same states (hitzones, the attacks' zone
 *    arming and sounds gated by W+0x7a14). GU: slots 171 / 172 (base 0xb17d8 / 0xb17f4 write bytes 0 / 1 =
 *    this+0x7305 / 0x7306, kept); ours = bytes 2..6 of the 20. Unpack 0xcc154 calls slot 172 before it applies the
 *    action (S: 0xcc830, the action bytes read after). Between the controller's re-roll and the next message the
 *    others keep the old bytes for the message latency, as in 4U.
 * 4. Zones (C): three 48-byte records at work +120 + 48 k {+0 u8 state (255 off, 110 + k armed), +1 u8 area
 *    (W+0x14c at spawn), +8 vec4 point, +36 f32 value, +40 f32 timer, +44 f32}. Spawn 0x76d8ac: state 255, point 0,
 *    value 500, timer 1200; each gets a uEffect003 (0xc07bb8(effmgr, subtype 4 + k, this, rec) -> 0xc0765c type 3,
 *    ctor 0x1b7548) and joins the stage list 0x684b00(mgr, rec) (mgr+0x30c, 6 entries). Arm 0x7756d4(this, -, k,
 *    value), called by the head's 7.20 / 7.22 (k 0), 7.40 (k 1), 7.42 (k 2) when their state bit is set, on every
 *    machine: em 24 -> return; k 0 and arena piece >= 2 broken (0x7731a4) -> return; already armed -> return; the
 *    other armed zones expire (0x775f2c) and go 255; then state 110 + k, point k0 (163, -5, 760) / k1 (-1119, 698,
 *    2950) / k2 (857, 218, 3492), value, timer 1200. Slot 40 0x76de94 (every machine): armed zone whose timer
 *    (timerDown 0xb0709c) runs out -> 0x775f2c, state 255.
 *    Effects: uEffect003 4 / 5 / 6 shows group 81 element 23 / 26 / 27 (id table 0xfd114c) = em110_200 / _203 /
 *    _204, mask 1 (+0x98, C), at its record point read once at its setup 0x1b7150 = the spawn's zero vector
 *    0x10e6378 (S: bss zero vector); for states >= 110 its update 0x1b72e8 never moves it (scale 0x10e6388, S: 1),
 *    so the files are authored in world space. A state change restarts it (model vt+0x74, alpha 1, shown); state
 *    255 fades it over 40 (subtype 4) / 20 frames (0xc472e4) and hides it. The expiry 0x775f2c posts the same file
 *    through 0xc08628 with mask 2 at position 0, only in the local player's area (C).
 *    Readers of the point / value: the stage list test 0x687280 (player in an armed zone of its area: box around
 *    the point, half sizes (2300, 350, 1100) / (1180, 550, 1000) / (1100, 150, 1850) for 110 / 111 / 112, plus a
 *    player-state test 0x77586c on player W+0x475 / W+0x4a3 / 0xd05d2c), called from player code 0xb30050 (with Shah
 *    present: player flag +0x1f8 |= 0x1000, a timer, effect 114, sound 36, 0xb1ac40(player, -2, 0): G, a forced
 *    reaction of a hunter in the zone). NOT ported: player code, needs a core player hook and GU's twins of those
 *    player fields. value is read only for other monsters' states (110..112 use constants): stored, unused.
 * Port: the bytes at 4U's work +0x6c; the zone records compacted to 20 bytes at work +0x78 (4U +120: the 4U stride
 * does not fit the 0x100-byte work): point / zero fields left out (constant by k, no reader in the port). The
 * uEffect003 is replaced by a PEL post at arm (DALA_EFX_SHAH_ZONE0 + k) that is stopped at expiry and killed after
 * 4U's fade frames (GU fade not mapped: the stop ends emission, the kill hides what is left). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"
#include "dala_shah.h"

int dala_broken(void *self);                             /* dala_stage.c [0x7731a4(area)] */
#define rageOn     FN(int (*)(void *), 0x8172c)           /* [0x954e48] rage byte (C) */
#define rand16     FN(uint32_t (*)(void), 0x496f0)        /* GU global random u16 (setAction's, C) */
#define playerArea FN(uint32_t (*)(void), 0x4971c)        /* local player's area (dala_efx.c) */
typedef void (*net_bytes_t)(void *self, uint8_t *buf, uint32_t size);
#define netGetBase FN(net_bytes_t, 0xb17d8)
#define netSetBase FN(net_bytes_t, 0xb17f4)
#define UNIT_AREA  0x1054                                 /* u8 map area of a monster (dala_efx.c) */

#define W_ST       0x6c       /* u8[5] crimson state per part [4U work+0x6c..+0x70] */
#define W_ZONE     0x78       /* zone k record at W_ZONE + ZONE_SZ k [4U work+120 + 48 k] */
#define ZONE_SZ    20
#define Z_STATE    0          /* u8 255 off, 110 + k armed [rec+0] */
#define Z_AREA     1          /* u8 [rec+1] */
#define Z_VALUE    4          /* f32 [rec+36] */
#define Z_TIMER    8          /* f32 frames left [rec+40] */
#define Z_EFF      12         /* void *: the armed / fading PEL effect (port) */
#define Z_FADE     16         /* f32 frames until the fading effect is killed (port) */
#define NET_OFF    2          /* our bytes after GU's base bytes 0 / 1 */
#define ZONE_FRAMES 1200.0f   /* 0x775868 / 0x76d9d4 */
#define STATE_OFF  0xffu
#define ARMED(s)   ((s) >= 110 && (s) <= 112)   /* 4U tests != 255; 4U writes only 255 / 110 + k (C), our ctor 0 */

static const uint8_t k_count[2][5] = {{15, 40, 35, 10, 0}, {0, 0, 50, 35, 15}};    /* 0xfdcbf8 / 0xfdcc0c */
static const uint8_t k_weight[3][5] = {{15, 60, 10, 5, 10}, {25, 5, 25, 10, 35}, {35, 5, 15, 35, 10}};   /* 0xfdcc20.. */
static const uint8_t k_mode[6] = {1, 2, 0, 2, 0, 1};    /* jump table 0x775454 */
static const float k_fade[3] = {40.0f, 20.0f, 20.0f};   /* 0x1b753c (subtype 4) / 0x1b7538 (5, 6) */

static int shah(void *self) { return FIELD(uint8_t, self, EN_VARIANT) != 0; }
static uint8_t *zone(void *self, uint32_t k) { return &DALA_WORK(uint8_t, self, W_ZONE + ZONE_SZ * k); }
#define ZF(T, z, off) (*(T *)((z) + (off)))

static uint32_t roll(void) { return rand16() % 100u + 1u; }   /* 1..100 */

/* 0x7751fc(this, table, 0): count n = i + 1 of the bucket lo < r <= hi; zero weights skipped (lo then adds only
 * w[i - 1], 4U's own sum, exact for these tables); 0 = none */
static uint32_t pick_count(const uint8_t *w)
{
    uint32_t r = roll(), lo = 0, hi = 0;
    for (uint32_t i = 0; i < 5; i++) {
        if (w[i] == 0) continue;
        lo = i == 0 ? 0 : (uint8_t)(lo + w[i - 1]);
        hi = (uint8_t)(hi + w[i]);
        if (r > lo && r <= hi) return i + 1;
    }
    return 0;
}

/* the same pick inline in 0x7753f4 (r4 = 1: no skip, index returned as is; none -> 0) */
static uint32_t pick_part(const uint8_t *w)
{
    uint32_t r = roll(), lo = 0, hi = 0;
    for (uint32_t i = 0; i < 5; i++) {
        lo = i == 0 ? 0 : (uint8_t)(lo + w[i - 1]);
        hi = (uint8_t)(hi + w[i]);
        if (r > lo && r <= hi) return i;
    }
    return 0;
}

/* 0x7753f4(this, var) */
void dala_shah_reset(void *self, uint32_t var)
{
    static uint32_t s_n;
    if (!shah(self)) return;                              /* the call sites test W+0x1c0 == 110 */
    FIELD(uint32_t, self, F_STATE7) = 0;                  /* W+0x7a14 = 0 (dala_parts.c rebuilds it per frame) */
    if (!FIELD(uint8_t, self, EN_CONTROLLED)) return;     /* W+0x1d9 */
    uint32_t mode = var < 6 ? k_mode[var] : 0;
    uint8_t *st = &DALA_WORK(uint8_t, self, W_ST);
    uint8_t was[5], retry[5] = {3, 3, 3, 3, 3};
    for (uint32_t i = 0; i < 5; i++) { was[i] = st[i] == 1; st[i] = 0; }
    uint32_t rage = rageOn(self) ? 1 : 0;
    uint32_t n = pick_count(k_count[rage]), n0 = n;
    if (n == 5) for (uint32_t i = 0; i < 5; i++) st[i] = 1;   /* 0xd12024(work+0x6c, 1) */
    else if (n) {
        uint32_t single = n == 1, guard = 0;
        while (n && ++guard < 1000) {                     /* the guard is the port's (4U loops until done) */
            uint32_t i = pick_part(k_weight[mode]);
            if (single && (mode == 0 ? i == 3 : i == 1)) continue;
            if (was[i] && retry[i]) { retry[i]--; continue; }
            if (st[i] == 0) { n--; st[i] = 1; }
        }
    }
    if (++s_n <= 40)
        logf("dalaport: %x shah re-roll var %u mode %u rage %u n %u -> %u %u %u %u %u (action %u/%u)", (uint32_t)self,
             var, mode, rage, n0, st[0], st[1], st[2], st[3], st[4], FIELD(uint8_t, self, EN_ACT_CAT),
             FIELD(uint8_t, self, EN_ACT_NUM));
}

/* the effect of zone k going off: 0x775f2c's post + the uEffect003's fade (see the header comment) */
static void expire(void *self, uint32_t k)
{
    static uint32_t s_n;
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    uint8_t *z = zone(self, k);
    uint32_t area = FIELD(uint8_t, self, UNIT_AREA), pa = playerArea();
    void *end = area == pa ? dala_efx_post_at(self, DALA_EFX_SHAH_END0 + k, zero, area) : 0;
    void *eff = ZF(void *, z, Z_EFF);
    if (eff && dala_efx_alive(eff)) { dala_efx_stop(eff); ZF(float, z, Z_FADE) = k_fade[k]; }
    else ZF(void *, z, Z_EFF) = 0;
    if (++s_n <= 20)
        logf("dalaport: %x shah zone %u expires (timer %d) end effect %x%s", (uint32_t)self, k,
             (int)ZF(float, z, Z_TIMER), (uint32_t)end, area == pa ? "" : " (other area: 4U posts nothing)");
}

/* 0x7756d4(this, -, k, value) */
void dala_shah_slot(void *self, uint32_t k, float value)
{
    static uint32_t s_n;
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    if (!shah(self) || k > 2) return;
    if (k == 0 && dala_broken(self) >= 2) return;
    uint8_t *z = zone(self, k);
    if (ARMED(z[Z_STATE])) return;
    for (uint32_t i = 0; i < 3; i++) {
        if (i == k || !ARMED(zone(self, i)[Z_STATE])) continue;
        expire(self, i);
        zone(self, i)[Z_STATE] = STATE_OFF;
    }
    z[Z_STATE] = (uint8_t)(110 + k);
    ZF(float, z, Z_VALUE) = value;
    ZF(float, z, Z_TIMER) = ZONE_FRAMES;
    /* the uEffect003 restarts on the state change: a fading one of this zone goes, a new one starts */
    void *old = ZF(void *, z, Z_EFF);
    if (old && dala_efx_alive(old)) dala_efx_kill(old);
    ZF(void *, z, Z_EFF) = dala_efx_post_at(self, DALA_EFX_SHAH_ZONE0 + k, zero, FIELD(uint8_t, self, UNIT_AREA));
    ZF(float, z, Z_FADE) = 0.0f;
    if (++s_n <= 20)
        logf("dalaport: %x shah zone %u armed value %d effect %x (action %u/%u, state7 %x, ctl %u)", (uint32_t)self, k,
             (int)value, (uint32_t)ZF(void *, z, Z_EFF), FIELD(uint8_t, self, EN_ACT_CAT),
             FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint32_t, self, F_STATE7), FIELD(uint8_t, self, EN_CONTROLLED));
}

/* slot 40 0x76de94..0x76df08, after the meteor machine; plus the port's effect bookkeeping */
void dala_shah_frame(void *self)
{
    if (!shah(self)) return;
    for (uint32_t k = 0; k < 3; k++) {
        uint8_t *z = zone(self, k);
        void *eff = ZF(void *, z, Z_EFF);
        if (eff && !dala_efx_alive(eff)) ZF(void *, z, Z_EFF) = eff = 0;
        if (eff && !ARMED(z[Z_STATE]) && timerDown(self, &ZF(float, z, Z_FADE), 1.0f)) {
            dala_efx_kill(eff);                           /* 4U: hidden at the end of the fade (+0x22d = 1) */
            ZF(void *, z, Z_EFF) = 0;
        }
        if (!ARMED(z[Z_STATE]) || !timerDown(self, &ZF(float, z, Z_TIMER), 1.0f)) continue;
        expire(self, k);
        z[Z_STATE] = STATE_OFF;
    }
}

/* slot 39 0x76d8ac..0x76da78 (after setBattleState 0x91b158 and 0xc08374) */
void dala_shah_spawn(void *self)
{
    if (shah(self)) {
        for (uint32_t k = 0; k < 3; k++) {
            uint8_t *z = zone(self, k);
            z[Z_STATE] = STATE_OFF;
            z[Z_AREA] = FIELD(uint8_t, self, UNIT_AREA);  /* W+0x14c */
            ZF(float, z, Z_VALUE) = 500.0f;               /* 0x76d9d0 */
            ZF(float, z, Z_TIMER) = ZONE_FRAMES;
            ZF(void *, z, Z_EFF) = 0;
            ZF(float, z, Z_FADE) = 0.0f;
        }
        for (uint32_t i = 0; i < 5; i++) DALA_WORK(uint8_t, self, W_ST + i) = 0;   /* 0xd11f24(work+0x6c) */
        logf("dalaport: %x shah spawn: 3 zones off, crimson bytes 0 (ctl %u)", (uint32_t)self,
             FIELD(uint8_t, self, EN_CONTROLLED));
    }
    FIELD(uint32_t, self, F_STATE7) = 0;                  /* W+0x7a14 = 0, both variants (0x76da6c) */
}

/* delete (port): no zone effect outlives the head */
void dala_shah_release(void *self)
{
    if (!shah(self)) return;
    for (uint32_t k = 0; k < 3; k++) {
        uint8_t *z = zone(self, k);
        void *eff = ZF(void *, z, Z_EFF);
        if (eff && dala_efx_alive(eff)) dala_efx_kill(eff);
        ZF(void *, z, Z_EFF) = 0;
    }
}

/* GU slot 171 = 4U slot 78 0x7751cc (em 24: nothing) */
void dala_shah_net_get(void *self, uint8_t *out, uint32_t size)
{
    static uint32_t s_n;
    netGetBase(self, out, size);
    if (!shah(self) || size < NET_OFF + 5) return;
    const uint8_t *st = &DALA_WORK(uint8_t, self, W_ST);
    for (uint32_t i = 0; i < 5; i++) out[NET_OFF + i] = st[i];
    if (++s_n <= 30)
        logf("dalaport: %x shah net send %u %u %u %u %u (action %u/%u)", (uint32_t)self, st[0], st[1], st[2], st[3],
             st[4], FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
}

/* GU slot 172 = 4U slot 79 0x7751a4 */
void dala_shah_net_set(void *self, const uint8_t *in, uint32_t size)
{
    static uint32_t s_n;
    netSetBase(self, (uint8_t *)in, size);
    if (!shah(self) || size < NET_OFF + 5) return;
    uint8_t *st = &DALA_WORK(uint8_t, self, W_ST);
    for (uint32_t i = 0; i < 5; i++) st[i] = in[NET_OFF + i];
    if (++s_n <= 30)
        logf("dalaport: %x shah net receive %u %u %u %u %u", (uint32_t)self, st[0], st[1], st[2], st[3], st[4]);
}

/* The hunter's side of an armed zone (4U, C): the heat tick 0xb2f73c.. asks 0x687280(mgr, player) at 0xb30050 when
 * a Shah (em 110) exists; it tests every armed zone record in the hunter's area with the box 0x77586c: |dy| <= h,
 * |dx| <= x, |dz| <= z around the zone point (0x7756d4's), sizes by k (0x6873f8..): k0 x 2300 z 1100 h 350, k1 x 1180
 * z 1000 h 550, k2 x 1100 z 1850 h 150; then the hunter's floor (ground record +0x475): k0 floor 2, k1 floor 6 (or
 * 5 in player state 0xd05d2c), k2 floor 5 (not in that state); state 0xd05d2c has no GU counterpart and is taken as
 * false (as dala_ai.c). Inside, the tick (skill 218 / effect 47 skip it, the heat ones) runs a timer, effect 114,
 * sound 36 and damage 0xb1ac40(player, -2, 0). Port: the zone counts as heat for GU's heat tick through the core
 * hook dala_heat_zone (GU 0x6a160, dala_head25.c; GU floor byte = hunter this+0x1065, as dala_ai.c). Deviation: GU's
 * heat tick (Teostra's) replaces 4U's own timer / effect / damage values (S: same skill / drink exemptions). */
int dala_shah_zone_hit(void *head, const float *pos, uint32_t area, uint32_t floor)
{
    static const float k_pt[3][3] = {{163.0f, -5.0f, 760.0f}, {-1119.0f, 698.0f, 2950.0f}, {857.0f, 218.0f, 3492.0f}};
    static const float k_box[3][3] = {{2300.0f, 1100.0f, 350.0f}, {1180.0f, 1000.0f, 550.0f}, {1100.0f, 1850.0f, 150.0f}};
    static const uint8_t k_floor[3] = {2, 6, 5};
    if (!head || !shah(head) || FIELD(uint8_t, head, UNIT_AREA) != area) return 0;
    for (uint32_t k = 0; k < 3; k++) {
        if (zone(head, k)[Z_STATE] != 110 + k) continue;
        float dx = pos[0] - k_pt[k][0], dy = pos[1] - k_pt[k][1], dz = pos[2] - k_pt[k][2];
        if (dy > k_box[k][2] || dy < -k_box[k][2] || dx * dx > k_box[k][0] * k_box[k][0] ||
            dz * dz > k_box[k][1] * k_box[k][1]) continue;
        if (floor != k_floor[k]) {     /* issue #6 (Shah's burn not on every surface): in the box, another floor */
            static uint32_t s_m, s_key;
            uint32_t key = k << 8 | floor;
            if (key != s_key && ++s_m <= 30) {
                s_key = key;
                logf("dalaport: shah zone %u box at %d %d %d but floor %u (burns on floor %u only)", k, (int)pos[0],
                     (int)pos[1], (int)pos[2], floor, k_floor[k]);
            }
            continue;
        }
        static uint32_t s_n;
        if (++s_n <= 20)
            logf("dalaport: shah zone %u hit at %d %d %d floor %u", k, (int)pos[0], (int)pos[1], (int)pos[2], floor);
        return 1;
    }
    return 0;
}
