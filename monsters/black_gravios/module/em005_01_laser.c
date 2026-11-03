/* em005_01_laser.c: the 4U look of Black Gravios' two em041_101 beams (notes/plan.md "Test of 0.4.6"): the laser
 * 7/57 / 7/71 (4U uEm038 0x803e6c, GU d2da3c) and the spin beam 7/79 (4U 0x805eec, GU d2ef2c). C = confirmed in
 * code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Laser (C): both games fire the shell at frame 160 (4U 0x804380, GU d2df48). 4U's is a uShell016 (subtype 33 / 35 by
 * state bit 0 = [this+0x8d88]+0x28 = GU work+0x24; life 162, table 0x102bbbc) posted at joint 3, offset (0, 0, 180),
 * length 6400, angles 0 (0x8043f4). Every frame (0xc6b848) it is re-placed on the head: Q = J3 + M3 (0, 0, 180),
 * P = Q + M3 (0, 0, 6400) (M3 = joint 3's matrix), so the beam sweeps with the head. Its init 0xc6a378 posts
 * uEffect002 id 41 twice on the shell, element masks 1 and 2; id 41 = 0xfd0b94 -> flat group 51 file 19 =
 * em041_101, his own file (a model unit beam, EFL unit type 5; no MEF record names it). The shell ends when its life
 * (minus the owner's motion step each frame) runs out or the owner's motion changes (0xc6e8d4).
 * Every frame uEffect002 0x1b5ba0 (case 41, 0x1b5aa0) puts the effect at Q along Q -> P and sets its transform scale
 * x = y = curve(t) (0xaac930; z kept at the post's 1.0), then t += the owner's motion step (0x94460c):
 *   mask 1: 0xfd0f3c (all subtypes); mask 2: 0xfd0e4c (33) / 0xfd0f0c (35) (tables below).
 * GU (C): d2da3c posts shell02 entry 4 / 12 (life 162, ef effect id 0xffff = none) at d2dfe4: the hit with no look.
 *
 * Spin beam (C): 4U 0x805eec plays motion 0x232 for 7/79 (r1 0) and 7/80 (r1 1); in its step 2 (from frame 40),
 * 7/79 only, at frame 99 it posts uShell016 43 / 44 (state bit 0; life 100) at joint 3, offset (0, -50, 100), length
 * 6400 (0x806170), placed every frame as the laser (0xc6b848 shares the case). Its init (0xc6a4c0) posts two
 * uEffect015 (0xc07ecc): kind 16 (em041_101 mask 1) and kind 14 / 15 (em041_101 mask 2) (kind -> u16 0xfd16ac =
 * 0x1333, records 0xfd16d0). uEffect015 0x1c4fd0: attached to the shell at Q (flag 4: offset -(0, 0, |P - Q|)), t +=
 * dt, then scale x = y = curve A(t); when the shell is gone (0x1c4b84) kind 16 (no curve B) is released, kinds 14 / 15
 * stay at the last spot with x = y = curve B(t) (t from 0, + the owner's motion step) and end at scale 0.
 * GU (C): d2ef2c posts no shell at all (attackEx at d2f300 / d2f4ec only): no look.
 *
 * Here GU's shells / attacks stay. em041_101 is posted as PEL list-2 world records 4043 / 4044 (k 0 / 1 = masks 1 /
 * 2, build_em005_01_arc.py CODE_FX) at Q along Q -> P, re-placed, re-scaled and ended every frame with 4U's rules
 * (tick from em005_01_act_c; the spin beam is posted from there too). 0.4.6 posted the laser without the curves, at
 * scale 1 (x 1/13 of 4U's width at its peak: user test 2026-11-03 "condensed, not full height / width"), and had no
 * spin beam ("some lasers are just absent"). Hook: before GU's laser post (d2dfe0: mov r0, r6; bl 0x48c4f0; r1 = the
 * message, r4 = this). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define REC_MOT_SPEED 0x398     /* float motion speed (em067_01_shell016.c owner_step) */
#define WK_STATE    0x24        /* u8 [4U [this+0x8d88]+0x28]: bit 0 = subtype 35 / 44 (em005_01_beam.c) */
#define BEAM_JOINT  3u
#define FX_K0       4043u       /* PEL list 2: em041_101 k 0 (mask 1) */
#define FX_K1       4044u       /* em041_101 k 1 (mask 2) */
#define SPIN_MOTION 0x232u      /* 4U 0x8061ec */
#define SPIN_FRAME  99.0f       /* 4U 0x806218 */
void *em005_01_beam_hit_post(void *self, uint32_t subtype);   /* em005_01_shell016.c: 4U's head-following capsule */

/* jointMtx(unit, joint, float out[16]): world matrix of a joint [4U 0x930894] (em089_shell016.c, C) */
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx    FN(joint_mtx_t, 0xc1660)
typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)      /* [0x941dbc] */
/* effects (em089_efx.c: PEL list-2 posts through the owner, live transform setters as GU's beam 0x10ab3d8) */
typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
typedef void (*efx_stop_t)(void *eff, uint32_t now);
#define efx_stop     FN(efx_stop_t, 0x32a400)   /* now 0: stop emitting */
typedef void (*efx_set_pos_t)(void *eff, const float *pos, int32_t k);
#define efx_set_pos  FN(efx_set_pos_t, 0x32a45c)
typedef void (*efx_set_rot_t)(void *xf, const float *rot);
#define efx_set_rot  FN(efx_set_rot_t, 0x8a7dc4)
#define EFX_XF       0x150      /* transform objects +0x150 / +0x154 (0x32a45c writes both): position +0x40, scale +0x60 */
#define XF_SCALE     0x60
#define EFX_REQ_SIZE 0x100
#define A16_RAD      (6.28318531f / 65536.0f)

/* 4U 0xaac930 curves: {key, value} pairs, a negative key ends the table and gives its value (em089_pile_port.c) */
typedef struct { float k, v; } curve_key_t;
static const curve_key_t K_MASK1[] = {{0.0f, 1.0f}, {20.0f, 3.0f}, {40.0f, 13.0f}, {-1.0f, 13.0f}};  /* 0xfd0f3c = 0xfd153c */
static const curve_key_t K_L33[] = {{0.0f, 1.0f}, {22.0f, 6.0f}, {30.0f, 3.2f}, {147.0f, 3.2f}, {162.0f, 0.0f},
                              {-1.0f, 0.0f}};                                                  /* 0xfd0e4c */
static const curve_key_t K_L35[] = {{0.0f, 1.0f}, {22.0f, 6.0f}, {30.0f, 1.6f}, {147.0f, 1.6f}, {162.0f, 0.0f},
                              {-1.0f, 0.0f}};                                                  /* 0xfd0f0c */
static const curve_key_t K_S14[] = {{0.0f, 1.0f}, {22.0f, 6.0f}, {30.0f, 3.2f}, {-1.0f, 3.2f}};  /* kind 14 A 0xfd1644 */
static const curve_key_t K_S15[] = {{0.0f, 1.0f}, {22.0f, 6.0f}, {30.0f, 1.6f}, {-1.0f, 1.6f}};  /* kind 15 A 0xfd1664 */
static const curve_key_t K_E14[] = {{0.0f, 3.2f}, {15.0f, 0.0f}, {-1.0f, 0.0f}};                 /* kind 14 B 0xfd1684 */
static const curve_key_t K_E15[] = {{0.0f, 1.6f}, {15.0f, 0.0f}, {-1.0f, 0.0f}};                 /* kind 15 B 0xfd15fc */

static float curve(const curve_key_t *c, float t)
{
    for (;;) {
        if (c[0].k < 0.0f) return c[0].v;
        if (t >= c[0].k && c[1].k >= t)
            return c[0].v + (c[1].v - c[0].v) * ((t - c[0].k) / (c[1].k - c[0].k));
        c++;
    }
}

enum { LASER, SPIN, NBEAM };
typedef struct {
    void *owner, *eff[2];
    const curve_key_t *run[2], *end1;  /* per element: curve while the shell lives; k 1's curve after it (spin only) */
    float off[3], life, t;
    uint32_t motion, ending, lines;
    uint32_t vt[2], xf[2][2];    /* per element: the vtable at the post, the transform pointers when first alive */
} beam_t;
static beam_t s_beam[NBEAM];
static const char *const k_name[NBEAM] = {"laser", "spin beam"};

static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
static float a16_deg(uint32_t a)
{
    a &= 0xffffu;
    return (float)(a >= 0x8000u ? (int32_t)a - 0x10000 : (int32_t)a) * (360.0f / 65536.0f);
}
static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}
static int efx_alive(void *eff) { return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2; }

/* Our handles are raw pointers: GU can free an effect (and reuse its memory) without telling us. Test 2026-11-03
 * crashed in efx_set_pos (0x32a45c) on the 8th laser: the handle's +0x150 held a float (0xc39750..). So an element
 * is used only while its object keeps the vtable it had at the post, is in state 1 / 2 and keeps the same transform
 * pointers (plausible heap addresses) it had on its first alive frame; otherwise the handle is dropped untouched. */
static int ptr_ok(uint32_t p) { return !(p & 3) && p >= 0x01000000u && p < 0x80000000u; }
static int beam_ok(beam_t *b, int k)
{
    void *eff = b->eff[k];
    if (!eff) return 0;
    uint32_t a = FIELD(uint32_t, eff, EFX_XF), c = FIELD(uint32_t, eff, EFX_XF + 4);
    int ok = FIELD(uint32_t, eff, 0) == b->vt[k] && efx_alive(eff) && ptr_ok(a) && (!c || ptr_ok(c));
    if (ok && !b->xf[k][0]) { b->xf[k][0] = a; b->xf[k][1] = c; }
    else if (ok) ok = a == b->xf[k][0] && c == b->xf[k][1];
    if (!ok && (FIELD(uint32_t, eff, 0) != b->vt[k] || b->xf[k][0])) {    /* gone (not merely not started yet) */
        static uint32_t s_n;
        if (++s_n <= 20) logf("bgport: beam effect %x k %d no longer ours (dropped)", (uint32_t)eff, k);
        b->eff[k] = 0;
    }
    return ok;
}
static float owner_step(void *self)   /* 4U 0x94460c */
{
    return FIELD(float, FIELD(uint8_t *, self, EN_RECORD), REC_MOT_SPEED) * FIELD(float, self, EN_DT);
}

/* 0xc6b848: Q = J3 + M3 off, direction Q -> P = M3's z axis; angles as em089_efx.c s016_seg */
static void place(void *self, const float *off, float *q, uint32_t *pitch, uint32_t *yaw)
{
    float j[4], m[16];
    jointPos(self, BEAM_JOINT, j);
    jointMtx(self, BEAM_JOINT, m);
    for (int i = 0; i < 3; i++) q[i] = j[i] + off[0] * m[i] + off[1] * m[4 + i] + off[2] * m[8 + i];
    q[3] = 0.0f;
    float dx = m[8], dy = m[9], dz = m[10];
    *yaw = rad_ang(atan2f_gu(dx, dz));
    *pitch = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));
}

static void *post_at(void *self, uint32_t id, const float *q, uint32_t pitch, uint32_t yaw)
{
    uint32_t buf[EFX_REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    efx_req_ctor(req);
    FIELD(uint32_t, req, 0x14) |= 0x80000u;                           /* ground set: 4U's code posts, kind 0 */
    FIELD(uint32_t, req, 0x6c) = 3u;
    FIELD(uint32_t, req, 0x8) = 3;                                    /* GU's moving beam 0x10b04c4 */
    FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, self, 0x1054);
    FIELD(uint32_t, req, 0x14) |= 2u;                                 /* rotation in degrees */
    FIELD(float, req, 0x30) = a16_deg(pitch);
    FIELD(float, req, 0x34) = a16_deg(yaw);
    FIELD(float, req, 0x38) = 0.0f;
    FIELD(float, req, 0x3c) = 0.0f;
    FIELD(uint32_t, req, 0x1c) |= 1u;                                 /* world position */
    for (int i = 0; i < 3; i++) FIELD(float, req, 0xc0 + 4 * i) = q[i];
    FIELD(float, req, 0xcc) = 0.0f;
    void *eff = efx_post_u(self, 2, id, req);
    efx_req_dtor(req);
    return eff;
}

/* 4U writes x = y = s and keeps z at the post's 1.0 on an effect whose parent is the shell (scale 1). GU's transform
 * of a post through the monster starts from the monster's model scale (em089 test 4, efl4u2gu), so all three are set:
 * (s, s, 1) as 4U's. Both transform objects, as 0x32a45c does for the position. */
static void set_scale(void *eff, float s)
{
    for (int k = 0; k < 2; k++) {
        void *xf = FIELD(void *, eff, EFX_XF + 4 * k);
        if (!xf) continue;
        FIELD(float, xf, XF_SCALE) = s;
        FIELD(float, xf, XF_SCALE + 4) = s;
        FIELD(float, xf, XF_SCALE + 8) = 1.0f;
    }
}

static void stop_eff(beam_t *b, int k)
{
    if (beam_ok(b, k)) efx_stop(b->eff[k], 0);
    b->eff[k] = 0;
}

static void finish(beam_t *b)
{
    stop_eff(b, 0);
    stop_eff(b, 1);
    b->owner = 0;
}

/* a new quest: the old handles died with the old one's effects */
void em005_01_laser_reset(void)
{
    for (int i = 0; i < NBEAM; i++) {
        uint32_t lines = s_beam[i].lines;
        for (uint32_t k = 0; k < sizeof s_beam[i]; k++) ((uint8_t *)&s_beam[i])[k] = 0;
        s_beam[i].lines = lines;
    }
}

static void start(void *self, int which, uint32_t sub, float life, float oy, float oz, const curve_key_t *k0,
                  const curve_key_t *k1, const curve_key_t *end1)
{
    beam_t *b = &s_beam[which];
    if (b->owner) finish(b);
    b->off[0] = 0.0f; b->off[1] = oy; b->off[2] = oz;
    float q[4];
    uint32_t pitch, yaw;
    place(self, b->off, q, &pitch, &yaw);
    b->owner = self;
    b->motion = curMotion(self);
    b->life = life;
    b->t = 0.0f;
    b->ending = 0;
    b->run[0] = k0; b->run[1] = k1; b->end1 = end1;
    b->eff[0] = post_at(self, FX_K0, q, pitch, yaw);
    b->eff[1] = post_at(self, FX_K1, q, pitch, yaw);
    for (int k = 0; k < 2; k++) {
        b->vt[k] = b->eff[k] ? FIELD(uint32_t, b->eff[k], 0) : 0;
        b->xf[k][0] = b->xf[k][1] = 0;
    }
    if (++b->lines <= 20)
        logf("bgport: %s em041_101 (4U subtype %u) at %d %d %d pitch %x yaw %x -> %x %x", k_name[which], sub,
             (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], pitch, yaw, (uint32_t)b->eff[0], (uint32_t)b->eff[1]);
}

static void tick_one(void *self, int which)
{
    beam_t *b = &s_beam[which];
    if (b->owner != self) return;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    float step = owner_step(self);
    if (b->ending) {                     /* spin: 0x1c4b84, k 1 at the last spot, x = y = B(t), ends at scale 0 */
        float s = curve(b->end1, b->t);
        if (s <= 0.0f || !beam_ok(b, 1)) {
            if (++b->lines <= 40) logf("bgport: %s end (curve B done)", k_name[which]);
            finish(b);
            return;
        }
        set_scale(b->eff[1], s);
        b->t += step;
        return;
    }
    b->life -= step;
    if (b->life <= 0.0f || curMotion(self) != b->motion || FIELD(int32_t, rec, REC_HP) <= 0) {
        if (++b->lines <= 40)
            logf("bgport: %s shell end (%s, life %d)", k_name[which], b->life <= 0.0f ? "life" : "motion / HP",
                 (int32_t)b->life);
        if (which == SPIN && b->end1 && beam_ok(b, 1) && FIELD(int32_t, rec, REC_HP) > 0) {
            stop_eff(b, 0);              /* kind 16 has no curve B: released */
            b->ending = 1;
            b->t = 0.0f;
            return;
        }
        finish(b);
        return;
    }
    float q[4];
    uint32_t pitch, yaw;
    place(self, b->off, q, &pitch, &yaw);
    float rot[4] = {(float)pitch * A16_RAD, (float)yaw * A16_RAD, 0.0f, 0.0f};
    if (which == SPIN) b->t += FIELD(float, self, EN_DT);    /* uEffect015: t += dt, then the curve */
    for (int k = 0; k < 2; k++) {
        if (!beam_ok(b, k)) continue;
        void *eff = b->eff[k];
        efx_set_pos(eff, q, 0);
        void *xf = FIELD(void *, eff, EFX_XF);
        if (xf) efx_set_rot(xf, rot);
        set_scale(eff, curve(b->run[k], b->t));
    }
    if (which == LASER) b->t += step;    /* uEffect002 41: the curve, then t += the owner's motion step */
    {
        static uint32_t s_n;
        void *xf = beam_ok(b, 0) ? FIELD(void *, b->eff[0], EFX_XF) : 0;
        if (xf && ++s_n <= 12)
            logf("bgport: %s t %d scale x1000 k0 %d k1 %d (states %u %u)", k_name[which], (int32_t)b->t,
                 (int32_t)(FIELD(float, xf, XF_SCALE) * 1000.0f), (int32_t)(curve(b->run[1], b->t) * 1000.0f),
                 FIELD(uint32_t, b->eff[0], 0xc) & 7, beam_ok(b, 1) ? FIELD(uint32_t, b->eff[1], 0xc) & 7 : 9);
    }
}

/* every frame (em005_01_act_c, before GU's dispatch): the spin beam's post (4U 0x806170: 7/79 only, motion 0x232,
 * frame 99), then 4U 0xc6b848 placement + the effects' scale and end for both beams (HP 0 too: the death action runs
 * outside slot 125, so its motion change may never be seen here) */
void em005_01_laser_tick(void *self)
{
    if (FIELD(uint8_t, self, EN_ACT_CAT) == 7 && FIELD(uint8_t, self, EN_ACT_NUM) == 79 &&
        curMotion(self) == SPIN_MOTION && atFrame(self, SPIN_FRAME)) {
        int b0 = FIELD(uint8_t, FIELD(uint8_t *, self, EN_WORK), WK_STATE) & 1;
        start(self, SPIN, b0 ? 44 : 43, 100.0f, -50.0f, 100.0f, K_MASK1, b0 ? K_S15 : K_S14, b0 ? K_E15 : K_E14);
        em005_01_beam_hit_post(self, b0 ? 44 : 43);
    }
    tick_one(self, LASER);
    tick_one(self, SPIN);
}

/* GU 0xd2dfe0 (r1 = the shell message, r4 = this): d2da3c's frame-160 shell post, before the request; GU's entry 4 /
 * 12 = 4U subtype 33 / 35 (d2dfe4: 4 | state bit 0 << 3). For him GU's shell (uShellEm005_sp_02, a projectile that
 * does not follow the head) is replaced by 4U's capsule (em005_01_shell016.c): the message is deleted unposted and
 * the hook exits past the post (MID_EXIT d2dfe8). */
int em005_01_laser_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (!self || FIELD(uint16_t, self, EN_ID) != BLACK_GRAVIOS_EM_ID) return 0;
    void *msg = (void *)regs[R1];
    int b0 = (FIELD(uint32_t, msg, 0x8) & 8) != 0;
    start(self, LASER, b0 ? 35 : 33, 162.0f, 0.0f, 180.0f, K_MASK1, b0 ? K_L35 : K_L33, 0);
    if (!em005_01_beam_hit_post(self, b0 ? 35 : 33)) return 0;    /* ours failed: GU's shell after all */
    VCALL0(msg, 1);                                               /* deleting dtor */
    return 1;
}
