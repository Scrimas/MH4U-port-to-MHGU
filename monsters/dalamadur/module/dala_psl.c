/* dala_psl.c: test log of the motion-synced effects (PSL posts, 4U LMT event group 2 / cMhMotionEffect) of both
 * halves: which record each motion posts, and when GU stops it. C = read in code, S = strong, G = guess.
 * 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Why (test 2026-10-21): a purple fire burned on forever where the head died. The death motion 0x33d posts MEF record
 * 253 (em024_012 element 1, joint 6 + (0, 600, 500), frames 35-72, MEF slot mode 1). 4U kills a slot-mode-1 effect
 * when its event range ends (cMhMotionEffect 0x39170c / 0x391a18 / 0x390b40, C). GU stops a PSL-posted effect on the
 * range end only when its PEL record has end mode 1 (+0x3a; 0x329dbc), else only on a motion change or wrap (C), and
 * our dead head holds 0x33d on its last frame (dala_react.c): no change ever came. Fix in the data
 * (build_dalamadur_arc.py pel_slot_end: slot mode 1 -> end mode 1); this file only logs it. It also gives every post
 * 4U's ground set (ground_flags below, issue #6) and logs the breath-charge placement (charge_track).
 *
 * GU (C): uFestaEnemy slot 75 (vt+0x12c) = 0x70028(this, list 1, PSL entry data, slot, request): the PSL post (uCharacter
 * 0x53b7e0 calls it with the request; S that this is the PSL player's only route: Capcom's own override 0xe022a4 wraps
 * it); kind data+0x44[slot] (4 = PEL u list 1), id = u16 data+4[slot]; returns the uMHProofEffect or 0 (no post in
 * 12/255). The PSL player (0x31d218 / 0x31d530) then sets effect+0x194 = &controller+0xc4[slot] (0x31d1d4) and pulses
 * bit 2 there on the run's falling edge, 4 on a motion change, 8 on a wrap; the effect (0x329668) latches them into
 * +0x198 / +0x199 / +0x19a. Effect: +0x30 u8 state (5 ended, 6 stopped; 3 = ended in end mode 1, run as state 0: S),
 * +0xc6 = record +0x36 (transform),
 * +0xca = record +0x3a (end mode), unit state +0xc & 7 (1 / 2 = alive, dala_efx_alive).
 * Logs (local, read-only; MP: every machine posts its own effects): "psl post" per post during a death (11 / 12 / 14)
 * and per end-mode-1 post otherwise (capped), "psl fx" when a tracked effect's state / latches change or it ends. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

typedef void *(*psl_post_t)(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req);
#define pslPostBase FN(psl_post_t, 0x70028)

#define TRACK 12
static struct { void *eff, *owner; uint16_t id, slot; uint32_t sig; } s_fx[TRACK];
static uint32_t s_n_post, s_n_fx;

static int is_tail(void *self) { return (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff); }
static int alive(void *eff) { return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2; }

/* Ground sets (issue #6, as Gogmazios' em089_efx.c ground_flags; C unless marked): 4U's motion post (0x391b50 ->
 * 0xc09908, enemy branch) takes the ground kind from the monster's ground record W+0x5f0 (attribute word +8, the
 * 0xc094e8 bits) and the effect keeps the EFL elements whose ground word meets (2 << kind) | 1. GU's records and
 * requests default to -1 = every set at once; the PSL player's request (0x53b7e0: fresh on its stack per post)
 * takes the override at req+0x14 bit 19 / req+0x6c. Sets: the qe006 dust records 11 16-18 50-53 150-155 201 202 250
 * 255 1008 (2611 Shah) (soil 0x22, 0x54, 0x14, lava 0x8). Speartip Crag's arena (4U m08a01d) is kind 5 (0x800000)
 * on 652 of its 868 floor triangles (the 0x54 set), kind 0 on the rest; the camp kind 0. GU's twin of W+0x5f0 is
 * not identified: the Stygian slam ray (0x183ad0, mask 64) through the ground under the monster (rec+0x5b4) (S). */
typedef float (*ground_ray_t)(void *mgr, const float *from, const float *to, uint32_t area, uint8_t *hit, void *out,
                              uint32_t mask);
#define groundRay    FN(ground_ray_t, 0x183ad0)  /* [0x2bad24] */
#define COLL_MGR     (*(void **)MAIN(0x21270e0)) /* its manager [*0x10574fc] */
#define REC_GROUND_Y 0x5b4
#define REQ_FIELDS   0x14
#define REQ_GROUND   0x6c
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx     FN(joint_mtx_t, 0xc1660)    /* = 4U 0x930894 (dala_head25.c) */

static uint32_t ground_flags(void *self)
{
    static uint32_t s_key[2], s_n;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    uint32_t out[16] = {0}, w = 0, kind, t = is_tail(self);
    uint8_t hit = 0;
    float gy = FIELD(float, rec, REC_GROUND_Y);
    float from[4] = {FIELD(float, rec, REC_POS_X), gy + 100.0f, FIELD(float, rec, REC_POS_Z), 0.0f};
    float to[4] = {from[0], gy - 300.0f, from[2], 0.0f};
    void *mgr = COLL_MGR;
    if (mgr) groundRay(mgr, from, to, FIELD(uint8_t, self, 0x1054), &hit, out, 64);
    if (hit) w = out[2];
    if (w & 0x800000) kind = 5;
    else if (w & 0x200) kind = 3;
    else if (w & 6) kind = 1;
    else if (w & 0x1040) kind = 2;
    else kind = (w & 8) ? 4 : 0;
    if ((w ^ (uint32_t)!hit << 31) != s_key[t] && ++s_n <= 40) {
        s_key[t] = w ^ (uint32_t)!hit << 31;
        logf("dalaport: psl ground %s %s word %x -> kind %u at %d %d %d", t ? "tail" : "head",
             hit ? "hit" : "none (kind 0)", w, kind, (int)from[0], (int)gy, (int)from[2]);
    }
    return (2u << kind) | 1u;
}

/* Issue #6 Dalamadur 1, test log: where GU draws the breath charges. 4U MEF (C, efl4u2gu.mef_records of em024 /
 * em110 _0): 3 / 4 = em024_002 elements 0 / 2 on joint 6 + (0, 600, 500) / (0, 800, 800), 5 = element 3 on joint
 * 137 + (0, -500, -1000) (motions 513 522 534 537 542 555 559, the wind-up before the fireball shell), 12 em024_030 /
 * 13 em024_015 / 21 em024_031 on joint 6, 19 em024_031 on joint 16, 157 em024_021 on joint 11; all with the MEF
 * local-space flag (bit 0) -> efl4u2gu PEL_TAIL_LOCAL (transform mode 1, from one Capcom pair: S). 4U draws their
 * units in the joint's space (0x391b50 bit 0 -> 0xc4800c, base = the joint's world matrix, 0xc4838c). Logged 4
 * frames after the post: the joint's world matrix (0xc1660) applied to the record offset = 4U's point, the effect
 * node +0x40 (the position 0x32a45c writes; world or parent-relative not traced for mode 1) and, on the first post of
 * an id, the node's first 16 floats. */
static const struct { uint16_t id, joint; float off[3]; } k_charge[] = {
    {3, 6, {0.0f, 600.0f, 500.0f}}, {4, 6, {0.0f, 800.0f, 800.0f}}, {5, 137, {0.0f, -500.0f, -1000.0f}},
    {12, 6, {0.0f, 0.0f, 0.0f}}, {13, 6, {0.0f, 0.0f, 0.0f}}, {19, 16, {0.0f, 0.0f, 0.0f}},
    {21, 6, {0.0f, 0.0f, 0.0f}}, {157, 11, {0.0f, 0.0f, 0.0f}}};
#define N_CHARGE (sizeof k_charge / sizeof k_charge[0])
#define PL_TRACK 4
static struct { void *eff, *owner; uint8_t k, age; } s_pl[PL_TRACK];
static uint8_t s_pl_n[N_CHARGE];

static void charge_track(void *self, uint32_t id, void *eff)
{
    uint32_t k = 0, i = 0;
    while (k < N_CHARGE && k_charge[k].id != id) k++;
    if (k == N_CHARGE || !eff || s_pl_n[k] >= 3) return;
    while (i < PL_TRACK && s_pl[i].eff) i++;
    if (i == PL_TRACK) return;
    s_pl_n[k]++;
    s_pl[i].eff = eff; s_pl[i].owner = self; s_pl[i].k = (uint8_t)k; s_pl[i].age = 0;
}

static void charge_watch(void *self)
{
    for (uint32_t i = 0; i < PL_TRACK; i++) {
        if (!s_pl[i].eff || s_pl[i].owner != self || ++s_pl[i].age < 4) continue;
        void *eff = s_pl[i].eff;
        uint32_t k = s_pl[i].k;
        s_pl[i].eff = 0;
        uint8_t *node = alive(eff) ? FIELD(uint8_t *, eff, 0x150) : 0;
        if (!node) { logf("dalaport: charge id %u: effect gone before frame 4", k_charge[k].id); continue; }
        float mt[16], x[3];
        const float *n = (const float *)(node + 0x40), *o = k_charge[k].off;
        jointMtx(self, k_charge[k].joint, mt);
        for (int c = 0; c < 3; c++) x[c] = mt[c] * o[0] + mt[4 + c] * o[1] + mt[8 + c] * o[2] + mt[12 + c];
        logf("dalaport: charge %s id %u motion %x frame %d transform %u: joint %u at %d %d %d, 4U point (joint "
             "matrix * offset %d %d %d) %d %d %d, node %d %d %d (node - 4U point %d %d %d)",
             is_tail(self) ? "tail" : "head", k_charge[k].id, curMotion(self), (int)motionFrame(self),
             ((uint8_t *)eff)[0xc6], k_charge[k].joint, (int)mt[12], (int)mt[13], (int)mt[14], (int)o[0], (int)o[1],
             (int)o[2], (int)x[0], (int)x[1], (int)x[2], (int)n[0], (int)n[1], (int)n[2], (int)(n[0] - x[0]),
             (int)(n[1] - x[1]), (int)(n[2] - x[2]));
        if (s_pl_n[k] == 1) {
            const float *m = (const float *)node;
            logf("dalaport: charge id %u node words x100: %d %d %d %d | %d %d %d %d | %d %d %d %d | %d %d %d %d",
                 k_charge[k].id, (int)(m[0] * 100), (int)(m[1] * 100), (int)(m[2] * 100), (int)(m[3] * 100),
                 (int)(m[4] * 100), (int)(m[5] * 100), (int)(m[6] * 100), (int)(m[7] * 100), (int)(m[8] * 100),
                 (int)(m[9] * 100), (int)(m[10] * 100), (int)(m[11] * 100), (int)(m[12] * 100), (int)(m[13] * 100),
                 (int)(m[14] * 100), (int)(m[15] * 100));
        }
    }
}

static int dead(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat == 11 || cat == 12 || cat == 14;
}
static uint32_t fx_sig(void *eff)
{
    uint8_t *e = (uint8_t *)eff;
    return 0x80000000u | (uint32_t)alive(eff) << 24 | (uint32_t)e[0x30] << 16 | (uint32_t)e[0x198] << 8 |
           (uint32_t)e[0x199] << 4 | e[0x19a];
}

void *dala_psl_post(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req)
{
    if (req) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 0x80000u;
        FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self);
    }
    void *eff = pslPostBase(self, list, data, slot, req);
    if (!data || slot >= 32) return eff;
    uint32_t id = FIELD(uint16_t, data, 4 + 2 * slot), kind = FIELD(uint32_t, data, 0x44 + 4 * slot);
    charge_track(self, id, eff);
    uint32_t end = eff ? ((uint8_t *)eff)[0xca] : 0xff, d = dead(self);
    if (!d && (end != 1 || s_n_post >= 60)) return eff;
    if (s_n_post++ < 160)
        logf("dalaport: psl post %s %u/%u motion %x frame %d slot %u id %u kind %u -> eff %x end mode %u transform %u",
             is_tail(self) ? "tail" : "head", FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM),
             curMotion(self), (int)motionFrame(self), slot, id, kind, (uint32_t)eff, end,
             eff ? ((uint8_t *)eff)[0xc6] : 0xff);
    if (!eff) return eff;
    int k = 0;
    while (k < TRACK && s_fx[k].eff && alive(s_fx[k].eff)) k++;
    if (k == TRACK) return eff;
    s_fx[k].eff = eff; s_fx[k].owner = self; s_fx[k].id = (uint16_t)id; s_fx[k].slot = (uint16_t)slot;
    s_fx[k].sig = fx_sig(eff);
    return eff;
}

/* GU slot 119, both halves: the tracked effects this half posted */
void dala_psl_watch(void *self)
{
    charge_watch(self);
    for (int k = 0; k < TRACK; k++) {
        if (!s_fx[k].eff || s_fx[k].owner != self) continue;
        void *eff = s_fx[k].eff;
        uint32_t sig = fx_sig(eff), was = s_fx[k].sig;
        if (sig == was) continue;
        s_fx[k].sig = sig;
        if (++s_n_fx <= 160)
            logf("dalaport: psl fx %s id %u slot %u eff %x: alive %u state %u -> %u, stop latches range end %u motion "
                 "%u wrap %u, end mode %u | %u/%u motion %x frame %d", is_tail(self) ? "tail" : "head", s_fx[k].id,
                 s_fx[k].slot, (uint32_t)eff, sig >> 24 & 1, was >> 16 & 0xff, sig >> 16 & 0xff, sig >> 8 & 0xf,
                 sig >> 4 & 0xf, sig & 0xf, ((uint8_t *)eff)[0xca], FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM), curMotion(self), (int)motionFrame(self));
        if (!(sig >> 24 & 1)) s_fx[k].eff = 0;        /* ended: forget it (the unit may be freed and reused) */
    }
}
