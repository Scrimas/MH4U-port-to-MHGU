/* dala_efx.c: Dalamadur's code-posted effects (goal D5), adapted from Gogmazios' em089_efx.c (own copy: the packages
 * are independent). C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * GU post (C, em089_efx.c): uEnemy 0x6ff74(this, mode 2, id, req) posts PEL u (this+0xb624) list-2 record `id`
 * through sFestaProofEffect 0x40978; the request object is 0x40b10 / dtor 0x40b50, req+0xd0 = attach model (filled
 * with vt+0x130(this) when 0), req+0x1c flags (1 world position req+0xc0, 2 attach), req+0x4 unit, req+0xc area.
 * An id without a record: 0x3267d0 returns 0, 0x40978 deletes its new effect and returns 0 (C).
 *
 * How 4U picks the EFL of a code post (C): never through an MEF record. em024's MEF _1 (ids 2000..2023, all
 * em024_020, mostly world positions) is not named by any class post. The class posts name the file directly:
 *   - flat table 0xef895c[group][element] -> path (0xc0a2f8 / 0xc088d8 requests {u16 group, u16 element}):
 *     group 35 = em024 list (element 3 = em024_003, 14 = em024_016 ...), group 81 = em110 list (same order + the
 *     em110_2xx files), group 1 = qe000.. list (element 138 = qe013_002, Gogmazios' tail smoke);
 *   - uEffect002 (0xc0765c type 2, ctor 0x1b6fb0, init 0x1b2fe4): id -> u16 table 0xfd0b94 {u8 group, u8 element}
 *     of the same flat table; 28 -> 0x0200 = group 0 element 2 = effect\efl\cm\cm000\cm000_002 (the table also gives
 *     Gogmazios' 48 / 50 -> em089_005, 53 / 54 -> em089_012, 57 -> em089_050 and Zamtrios' 49 -> em092_200, as
 *     those ports found).
 * The element mask of a post is the PEL record's k (mask = 1 << k, -1 = all).
 *
 * Records the build must add (build_dalamadur_arc.py effects() `extra`, both PELs unless noted; 4U sources):
 *   2800 cm000_002 joint 200, offset (3850, -945, -805), rot 0, scale 8.0, k 2   [0x76d77c; joint table 0xfdc828
 *        {200, 5}; offsets bss 0x10b6560 / 0x10b6570 written by the static init 0xd25968; s0 = 8.0; mask 4]
 *   2801 cm000_002 joint 5, offset (0, 500, 1000), scale 8.0, k 2                [same post, i = 1]
 *   2802 cm000_002 joint 142, offset (970, -110, 865), scale 8.0, k 2            [tail 0x89ffe0; bss 0x10b7b68
 *        written by the static init 0xd2a860; s0 = 8.0, mask r8 = 4]
 *   2900 em024_003 (em090_00u) / em110_003 (em090_01u), joint -1, offset 0, scale 1.0, k -1 [uShell029 init
 *        0xc7cf18: table 0x102e124 {35, 3} kinds 2..4, {81, 3} kinds 5..7; 0xc08060(mgr, file, area, 0, -1, mask -1);
 *        attach vt+0x48(eff, shell, joint -1)]
 *   2910 qe013_002 joint 157, offset (0, 0, -950), rot 0, scale 4.5, k -1, colour (120, 85, 80, 255) (em090_00u)
 *   2911 the same with colour (143, 76, 58, 255) (em090_01u)   [tail 0x8a27d0: 0xc088d8 request {vtable 0xe7f918,
 *        area 255, group 1, element 138, offset +0x28, scale +0x48 = 4.5, +0x58 0 / +0x59 1 / +0x5a 0, owner +0x5c,
 *        joint +0x60 = 157}; 0xc48378(eff, rgba) with 0x785550ff for em 83, else 0x8f4c3aff (bytes R, G, B, A)]
 * The attack shells' records (dala_shell*.c; em090_00u gets the em024 file, em090_01u the em110 file; the flat
 * table 0xef895c group 35 / 81 elements 0 / 1 / 4 / 7 = files _000 / _001 / _005 / _009, C):
 *   2920 em024_000 / em110_000, joint -1 (on the shell, follows it), scale 3.5, k -1   [uShell001 init 0xc4c54c:
 *        0x1017980[k] {35 / 81, 0, mask -1}, scale 0x101b214[2k] = 3.5, colour 0x10ba3fc[k] = 0xffffffff (none)]
 *   2921 em024_001 / em110_001, world position (joint -1, placed once), scale 1.0, k 1   [uShell001 wall hit
 *        0xc4ecd4: 0x1018140[k] {35 / 81, 1, mask 2}, scale 0x101b214[2k + 1] = 1.0 for kinds 24 / 88]
 *   2922 the same at scale 1.2 (kinds 25 / 89)
 *   2923 em024_001 / em110_001, world position, scale 1.2, k 0   [ground hit 0xc4ede8: 0x1017d60[k] {35 / 81, 1,
 *        mask 1} for kinds 25 / 89 only; 4U turns it to the ground normal (0xd076b0), not ported]
 *   2930 em024_005 / em110_005, world position, scale 1.2, k -1   [uShell003 0xc5540c: 0x101dfcc[113 / 126 / 160 /
 *        162] {35 / 81, 4, mask -1}, scale 0x1021a08[sub] = 1.2, angles 0]
 *   2931 em024_001 / em110_001, world position, scale 1.5, k 0   [same, subtypes 112 / 159: {35 / 81, 1, mask 1},
 *        scale 1.5]
 *   2940 em024_009 / em110_009, joint -1, placed once (world post + rotation, moved every frame by dala_shell016.c:
 *        attached to the shell it was not drawn), scale (13.0, 13.0, 12.0), k -1   [uShell016 21 /
 *        39: uEffect015 controller ids 2 / 6 -> 0xfd16ac {35, 7} / {81, 7}, attached to the shell (vt+0x48, -1);
 *        z scale = capsule length 12000 / 0xfd16d0[id] +12 (1000.0); x / y = records 2 / 6 (20 B each) +4 =
 *        curve 0xfd1514 {(0, 13), (-1, 13)} = constant 13 (C, user 2026-10-22: "a very large beam")]
 *   2950 em024_006 / em110_006, joint -1, scale 1.0, k -1, placed once   [uShell038 init 0xc847bc: table 0x102faac
 *        [kind] {35 / 81, 5}, request +0x10 / +0x14 = -1 (mask all), target +0x5c = the shell, joint +0x60 255,
 *        offset / rotation = zero vector 0x10e6378, scale = bss vector 0x10e6388 (S: (1, 1, 1), the constant after
 *        the zero vector); 0xc08698 attaches it to the shell, which never moves: placing once on it is the same]
 *   2951 em024_007 / em110_007, world position, scale 1.0, k -1   [uShell038 end 0xc849d4: table 0x102fab0 {35 / 81,
 *        6}, 0xc08628 at the shell's position +0x100, area +0x130, rotation 0xd00cc0(shell) (S: its angles = the
 *        meteor's yaw +0x114, always 0), scale 0x10e6388]
 * No colour block for any of them (0x10ba3fc = 0xffffffff for the fireball; the others post no 0xc48378). The
 * world-position ones are posted with request flags 1 (dala_efx_post_at): they need the record tail that places once
 * (not PEL_TAIL_PREV).
 * All six are attached in 4U (joint / shell), so they need the record tail that follows its target (efl4u2gu.py
 * PEL_TAIL_PREV, what pel_follows() gives em089's 3000 / 3001 on their shell; PEL_TAIL places once, test-4 /
 * test-5 of Gogmazios: G for joints, C-by-test for shells), and 2910 / 2911 need their CODE_COLOUR (qe013_002 has
 * the colour block that pel_colour() reads).
 *
 * Conditions (C): uEffect002 28 has no area gate (0xc0a614 passes r3 = 1, 0xc0765c then skips the player-area
 * test); 0xc08060 has none; 0xc088d8 posts only when the owner's area (0xc09cd8, S) is the local player's (request
 * +0xc bit 8 clear) -> kept with GU's area byte this+0x1054 and player area 0x4971c (Gogmazios' pairing).
 * uEffect002 28 per frame (0x1b648c): while the global test 0x19fbf0(*0xfb5edc) holds it clears the effect's draw
 * bits 1024 / 2048 every frame (the same bits 0x251ebc(eff, 0) clears = hidden); no GU counterpart of 0x19fbf0 is
 * known (it reads game-state bytes, G: a scene / lighting state): NOT ported, the effects always draw. The 4U class
 * keeps the 28 handles (head work +0x60 / +0x64, tail work +4) only for its slot 41 (head 0x7752f4, tail 0x8a2fe8:
 * hide them, plus the head's work+0x68 object); slot 41's caller / GU counterpart is not traced, so the handles are
 * not kept here (GU kills a target's effects when the target unit goes, proof effect path 0x43274).
 * Multiplayer: every post is local (spawn setup and the action start run on every machine, meteors are local
 * shells), as in 4U (effect manager requests, no net send).
 */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"

typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)     /* PEL u (this+0xb624), returns uMHProofEffect* or 0 */
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
typedef void (*efx_stop_t)(void *eff, uint32_t now);
#define efx_stop_fn  FN(efx_stop_t, 0x32a400)
typedef uint32_t (*player_area_t)(void);
#define playerArea   FN(player_area_t, 0x4971c)  /* the local player's area (em089_efx.c roar blur) */

#define EFX_MODE_CODE  2u       /* PEL list 2 = code posts */
#define REQ_SIZE       0x100u   /* request object ~0xd8 B */
#define REQ_FLAGS      0x1c
#define REQ_POS        0xc0
#define REQ_TARGET     0xd0
#define VT_ATTACH      0x130    /* unit slot 76: attach model getter (monsters and shells) */
#define UNIT_AREA      0x1054   /* u8 map area of a monster / shell */

/* tail work fields of the port (4U uEm083's work struct only uses +0 / +4: C, scan of 0x89fab8..0x8a3160) */
#define W_SMOKE        0x40     /* void *: the 10/114 smoke (handle dropped when dead) */
#define W_SMOKE_T      0x44     /* float: frames until the port stops it */
#define SMOKE_FRAMES   120.0f   /* one cycle of qe013_002 (Gogmazios' tail smoke: it loops in GU, test 4) */

/* rotation (degrees, req+0x14 bit 1) and GU's moving-beam request bytes (req+8 = 3, req+0xc = the area; GU's own
 * beam 0x10b04c4): em089_efx.c post_full, which draws Gogmazios' beams */
#define REQ_FIELDS     0x14
#define REQ_ROT        0x30
typedef void (*efx_set_pos_t)(void *eff, const float *pos, int32_t k);
#define efx_set_pos    FN(efx_set_pos_t, 0x32a45c)
typedef void (*efx_set_rot_t)(void *xf, const float *rot);
#define efx_set_rot    FN(efx_set_rot_t, 0x8a7dc4)
#define EFX_XF         0x150

static void *post_full(void *self, uint32_t id, void *unit, const float *pos, const float *rot)
{
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    efx_req_ctor(req);
    if (rot) {
        FIELD(uint32_t, req, 0x8) = 3;
        FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, self, UNIT_AREA);
        FIELD(uint32_t, req, REQ_FIELDS) |= 2u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_ROT + 4 * i) = rot[i];
        FIELD(float, req, REQ_ROT + 12) = 0.0f;
    }
    if (unit) {   /* GU shells' own request (0x4a1d34): attach model + position + unit + area (em089_efx.c) */
        typedef void *(*attach_t)(void *);
        FIELD(void *, req, REQ_TARGET) = ((attach_t)((*(uint32_t **)unit)[VT_ATTACH / 4]))(unit);
        FIELD(uint32_t, req, REQ_FLAGS) |= 3u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = FIELD(float, unit, 0x40 + 4 * i);
        FIELD(float, req, REQ_POS + 12) = 0.0f;
        FIELD(void *, req, 0x4) = unit;
        FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, unit, UNIT_AREA);
    }
    if (pos) {    /* world position (req+0x1c bit 0) only, as em089_efx.c's ground splashes (the owner's area: the
                   * shells' areas are their owner's) */
        FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = pos[i];
        FIELD(float, req, REQ_POS + 12) = 0.0f;
    }
    void *eff = efx_post_u(self, EFX_MODE_CODE, id, req);
    efx_req_dtor(req);
    static uint32_t s_n, s_freq;                   /* meteors / blasts are frequent: own small budget */
    int freq = id == DALA_EFX_METEOR || id == DALA_EFX_BLAST || id == DALA_EFX_BURN;
    if (freq ? ++s_freq <= 16 : ++s_n <= 60)
        logf("dalaport: efx post id %u%s%s -> %x%s", id, unit ? " (on unit)" : "", pos ? " (at pos)" : "",
             (uint32_t)eff, eff ? "" : " (no PEL record: build_dalamadur_arc.py effects() extra, see dala_efx.c)");
    return eff;
}

void *dala_efx_post(void *self, uint32_t id) { return self ? post_full(self, id, 0, 0, 0) : 0; }
void *dala_efx_post_on(void *owner, uint32_t id, void *unit)
{
    return owner && unit ? post_full(owner, id, unit, 0, 0) : 0;
}

static float a16_deg(uint32_t a)
{
    a &= 0xffffu;
    return (float)(a >= 0x8000u ? (int32_t)a - 0x10000 : (int32_t)a) * (360.0f / 65536.0f);
}

void *dala_efx_post_beam(void *owner, uint32_t id, const float *pos, uint32_t pitch, uint32_t yaw)
{
    float rot[3] = {a16_deg(pitch), a16_deg(yaw), 0.0f};
    return owner && pos ? post_full(owner, id, 0, pos, rot) : 0;
}

void dala_efx_place(void *eff, const float *pos, uint32_t pitch, uint32_t yaw)
{
    if (!dala_efx_alive(eff)) return;
    float p[4] = {pos[0], pos[1], pos[2], 0.0f};
    float rot[4] = {(float)(pitch & 0xffffu) * (6.28318531f / 65536.0f), (float)(yaw & 0xffffu) * (6.28318531f / 65536.0f),
                    0.0f, 0.0f};
    efx_set_pos(eff, p, 0);
    void *xf = FIELD(void *, eff, EFX_XF);
    if (xf) efx_set_rot(xf, rot);
}

void *dala_efx_post_at(void *owner, uint32_t id, const float *pos, uint32_t area)
{
    (void)area;   /* the request keeps the owner's area (em089_efx.c's world posts); the shells' are the owner's */
    return owner && pos ? post_full(owner, id, 0, pos, 0) : 0;
}

void dala_efx_stop(void *eff)
{
    if (eff) efx_stop_fn(eff, 0);
}

void dala_efx_kill(void *eff)
{
    if (eff) efx_stop_fn(eff, 1);
}

int dala_efx_alive(void *eff)
{
    return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2;
}

/* 4U head slot 39 0x76d730..0x76d7a4: for i = 0, 1: 0xc0a9d4(mgr, 28, area, this, s0 8.0, s1 0.0, joint
 * 0xfdc828[i] = 200 / 5, &offset 0x10b6560 + 16 i, mask 4, 0) -> work+0x60 + 4 i; tail slot 39 0x89ffa0..0x8a0000:
 * one post, joint 142, &offset 0x10b7b68, mask 4 -> work+4. 0xc0a9d4 -> 0xc0a614 -> 0xc0765c(mgr, 2, req, 1):
 * uEffect002 {id 28, sub 0, area, target this, joint, offset, rotation 0, scale (8, 8, 8), +0x40 0.0, mask 4}
 * (ctor 0x1b6fb0 field copy); init case 28 (0x1b31b8) attaches it: vt+0x48(eff, target, joint), offset eff+0x160.
 * The handles go where 4U keeps them (head work +0x60 / +0x64, tail work +4). */
void dala_efx_body_spawn(void *self, uint32_t tail)
{
    if (!tail) {
        DALA_WORK(void *, self, 0x60) = dala_efx_post(self, DALA_EFX_BODY_J200);
        DALA_WORK(void *, self, 0x64) = dala_efx_post(self, DALA_EFX_BODY_J5);
    } else {
        DALA_WORK(void *, self, 0x04) = dala_efx_post(self, DALA_EFX_BODY_J142);
    }
}

/* The cm000_002 arrows (user, 2026-10-21: in 4U "they appear and stay as long as the walkable part stays walkable";
 * 2026-10-22: the head is walkable whenever the back is, as far as the user remembers, no proof either way).
 * 4U (C, 2026-10-22) shows / hides them every frame at the end of slot 77 (head 0x774ea0.., tail 0x8a2d30..; draw
 * bit 2048 + 0x251ebc(eff, on)): head arrows (work+0x60 / +0x64, joints 200 / 5) while the action is 1/{0, 3, 6, 9,
 * 50, 53, 60, 61, 63, 71, 84} or 7/{0..4, 60, 61, 86} and head part 0 has a break count (0x94741c(this, 0)); the
 * tail arrow (work+4, joint 142) while 1/{0, 3, 6, 50} or 7/{0..3, 60, 61}; neither while 0x19fbf0 ([0xfb5edc] +0x2b
 * test, no GU counterpart: taken as 0, G). It matches the walk rule (dala_walk.c): joint 5 (the head) is walkable
 * only once part 0 is broken (set 1). Slot 41 (head 0x7752f4, tail 0x8a2fe8) hides them too; no caller found.
 * The port posts / kills instead of toggling the draw bit (an arrow posted again restarts its animation). Local on
 * every machine (action and break counts are synced). */
static int has(const uint8_t *l, uint32_t n, uint32_t v)
{
    for (uint32_t i = 0; i < n; i++) if (l[i] == v) return 1;
    return 0;
}
static int arrows_on(void *self, uint32_t tail)
{
    static const uint8_t h1[] = {0, 3, 6, 9, 50, 53, 60, 61, 63, 71, 84}, h7[] = {0, 1, 2, 3, 4, 60, 61, 86},
                         t1[] = {0, 3, 6, 50}, t7[] = {0, 1, 2, 3, 60, 61};
    uint32_t c = FIELD(uint8_t, self, EN_ACT_CAT), n = FIELD(uint8_t, self, EN_ACT_NUM), on;
    if (tail) on = c == 1 ? has(t1, sizeof t1, n) : c == 7 ? has(t7, sizeof t7, n) : 0;
    else on = (c == 1 ? has(h1, sizeof h1, n) : c == 7 ? has(h7, sizeof h7, n) : 0) &&
              FN(uint32_t (*)(void *, uint32_t), 0x9d428)(self, 0) != 0;   /* part rank [4U 0x94741c] */
    return (int)on;
}
void dala_efx_arrows_frame(void *self)
{
    uint32_t tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff), on = (uint32_t)arrows_on(self, tail);
    uint8_t *last = &FIELD(uint8_t, self, F_ARROWS);
    if (*last != on + 1) {
        static uint32_t s_n;
        if (++s_n <= 40) logf("dalaport: arrows %s %s (action %u/%u)", tail ? "tail" : "head", on ? "on" : "off",
                              FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
        *last = (uint8_t)(on + 1);
    }
    dala_efx_body_walk(self, tail, on);
}

void dala_efx_body_walk(void *self, uint32_t tail, uint32_t walkable)
{
    static const uint16_t k_off[3] = {0x60, 0x64, 0x04};
    static const uint32_t k_id[3] = {DALA_EFX_BODY_J200, DALA_EFX_BODY_J5, DALA_EFX_BODY_J142};
    for (uint32_t i = tail ? 2 : 0; i < (tail ? 3u : 2u); i++) {
        void **h = &DALA_WORK(void *, self, k_off[i]);
        if (*h && !dala_efx_alive(*h)) *h = 0;          /* GU ended it (e.g. the unit's effects at an area change) */
        if (walkable && !*h) *h = dala_efx_post(self, k_id[i]);
        else if (!walkable && *h) { dala_efx_kill(*h); *h = 0; }
    }
}

/* 4U 0x8a269c..0x8a2818 (tail slot 47, 10/114, hit direction 7). The port stops the effect after SMOKE_FRAMES
 * (deviation, as em089_efx.c tail_tick: the converted qe013_002 loops in GU; 4U's request bytes +0x58 / +0x59 have
 * no PEL field). */
void dala_efx_tail_smoke(void *self)
{
    static uint32_t s_n;
    uint32_t area = FIELD(uint8_t, self, UNIT_AREA), pa = playerArea();
    if (area != pa) {                     /* 0xc089cc: other area -> no effect */
        if (++s_n <= 10) logf("dalaport: efx tail smoke skipped: tail area %u, player area %u", area, pa);
        return;
    }
    void *old = DALA_WORK(void *, self, W_SMOKE);
    if (dala_efx_alive(old)) dala_efx_stop(old);
    DALA_WORK(void *, self, W_SMOKE) = dala_efx_post(self, FIELD(uint8_t, self, EN_VARIANT) ? DALA_EFX_TAIL_SMOKE_SHAH
                                                                                              : DALA_EFX_TAIL_SMOKE);
    DALA_WORK(float, self, W_SMOKE_T) = SMOKE_FRAMES;
}

/* Heat aura: uMhEftCtrl004 (4U 0x326a6c / 0x326c40, em 24 / 110; C). Per frame it reads the head's work+0x54, which
 * slot 48 rebuilds every frame (0x773a14): bits 0..2 = attack slots connecting in motions 61..66 (kinds 1 / 12 -> 1,
 * 8 / 14 / 20 / 24 -> 2, 4 / 13 -> 1 | 4), bit 3 / 4 = the heat pulse in zone 0 / 1 (0x773be4; dala_head25.c). When
 * bits 3..4 change it releases its effect (0xc470dc) and, if any is set, posts group 35 / 81 element 14 =
 * em024_016 / em110_016 (flat table 0xef895c, C) with those bits as the element mask: bit 3 at joint 4 + (0, -500,
 * 1100), bit 4 at joint 101 + (500, 1300, -700) = the heat zones themselves. A handle that is no longer valid
 * (0x37ecd4) resets the remembered bits, so a still-set zone posts again. Bits 0..2 (the same file without a joint,
 * 0x326c40) are not ported: the attack-slot test 0xb6fc4c has no GU mapping yet. Every machine runs it (MP). */
#define W_HEAT_BITS    0x54     /* u8: [4U work+0x54] bits 3..4 posted */
#define W_HEAT_EFX     0x68     /* void *: [4U uMhEftCtrl004 +0x40] */
void dala_efx_heat(void *self, uint32_t bits)
{
    uint8_t *last = &DALA_WORK(uint8_t, self, W_HEAT_BITS);
    void **h = &DALA_WORK(void *, self, W_HEAT_EFX);
    bits &= 24;
    if (*h && !dala_efx_alive(*h)) { *h = 0; *last = 0; }
    if (*last == bits) return;
    if (*h) { dala_efx_stop(*h); *h = 0; }
    if (bits) *h = dala_efx_post(self, bits & 8 ? DALA_EFX_HEAT_J4 : DALA_EFX_HEAT_J101);
    *last = (uint8_t)bits;
}

void dala_efx_frame(void *self)
{
    void *h = DALA_WORK(void *, self, W_SMOKE);
    if (!h) return;
    if (!dala_efx_alive(h)) { DALA_WORK(void *, self, W_SMOKE) = 0; return; }   /* never read a freed effect */
    float *t = &DALA_WORK(float, self, W_SMOKE_T);
    *t -= FIELD(float, self, EN_DT);
    if (*t > 0.0f) return;
    dala_efx_stop(h);
    DALA_WORK(void *, self, W_SMOKE) = 0;
}

/* 4U 0xc0819c(mgr, area W+0x14c, &joint-5 position 0x93093c): only when the area is the local player's (global
 * +0xc90), new uMhRadialBlurFilter (200 B, ctor 0x3e3cbc; Gogmazios' notes: vtable 0xe6313c, line 20). GU has
 * uRadialBlurFilter but no spawn helper and no calibration to 4U's code blur (em089_efx.c em089_efx_roar_blur):
 * not ported, logged with the same area gate. */
void dala_efx_radial_blur(void *self)
{
    static uint32_t s_n;
    uint32_t area = FIELD(uint8_t, self, UNIT_AREA), pa = playerArea();
    if (++s_n <= 10)
        logf("dalaport: efx radial blur 0xc0819c joint 5 (motion %x): %s", curMotion(self),
             area == pa ? "not ported, no calibrated GU blur" : "other area, 4U posts nothing");
}

/* 4U uShell029 init 0xc7cf18..0xc7cf8c: 0xc0a2f8(mgr, group, element) = getResource(rEffectList, 0xef895c[group]
 * [element]) -> 0xc08060(mgr, file, area +0x130, 0, -1, mask -1) -> +0x274; +0x228 |= 8 (no PEL field);
 * vt+0x48(eff, shell, -1) attach; 0xc4800c(eff, 1). Released by slot 24 0xc7da24 (0xc470dc) at the shell's end:
 * here dala_meteor.c stops it at the kill and keeps the shell until it is dead. 4U kills the shell when the file
 * is missing; a missing PEL record here is a port gap, so the meteor lives (dala_meteor.c). */
void *dala_efx_meteor(void *owner, void *shell, uint32_t kind)
{
    if (kind < 2 || kind > 7) return 0;           /* kinds 0 / 1 ({60, 14} / {40, 26}) are not Dalamadur's */
    uint32_t shah = kind >= 5;
    if (owner && shah != FIELD(uint8_t, owner, EN_VARIANT)) {
        static uint32_t s_n;
        if (++s_n <= 5) logf("dalaport: efx meteor kind %u from variant %u: the PEL holds the variant's file",
                             kind, FIELD(uint8_t, owner, EN_VARIANT));
    }
    return dala_efx_post_on(owner, DALA_EFX_METEOR, shell);
}
