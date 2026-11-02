/* em005_01_laser.c: the 4U look of Black Gravios' laser 7/57 / 7/71 (4U uEm038 0x803e6c r1 0 / 2, GU d2da3c; notes/
 * plan.md "Test of 0.4.5"). C = confirmed in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Both games fire the shell at frame 160 (4U 0x804380, GU d2df48, C). 4U's is a uShell016 (subtype 33 / 35 by state
 * bit 0; life 162, table 0x102bbbc) posted at joint 3, offset (0, 0, 180), length 6400, angles 0 (0x8043f4). Every
 * frame (0xc6b848) it is re-placed on the head: Q = J3 + M3 (0, 0, 180), P = Q + M3 (0, 0, 6400) (M3 = joint 3's
 * matrix), so the beam sweeps with the head (user: "hits in front first, then he lifts his face"). Its init 0xc6a378
 * posts uEffect002 id 41 twice on the shell, element masks 1 and 2, scale 1.0; id 41 = 0xfd0b94 -> flat group 51
 * file 19 = em041_101, Black Gravios' own file (no MEF record names it: this laser only). The shell ends when its
 * life (minus the owner's motion step each frame) runs out or the owner's motion changes (0xc6e8d4).
 * GU (C): d2da3c posts shell02 entry 4 / 12 (life 162, ef effect id 0xffff = none) at d2dfe4: the hit with no look.
 * Here GU's shell stays and em041_101 is posted as PEL list-2 world records 4043 / 4044 (k 0 / 1,
 * build_em005_01_arc.py CODE_FX) at Q along Q -> P, re-placed every frame from 4U's formula (Gogmazios'
 * em089_efx.c s016_post / em089_efx_shell016_move: the uShell016 effects sit at the capsule start along the capsule,
 * world records with the moving-beam request, C in its tests), stopped with 4U's end rule (tick from
 * em005_01_act_c). Hook: before GU's post (d2dfe0: mov r0, r6; bl 0x48c4f0; r1 = the message, r4 = this). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define REC_MOT_SPEED 0x398     /* float motion speed (em067_01_shell016.c owner_step) */
#define LASER_JOINT 3u          /* 0x8043f4 post: joint 3, offset (0, 0, 180), length 6400 */
#define LASER_OFF_Z 180.0f
#define LASER_LIFE  162.0f      /* 0x102bbbc[33] = [35] */
#define FX_LASER_A  4043u       /* PEL list 2: em041_101 k 0 (uEffect002 41, mask 1) */
#define FX_LASER_B  4044u       /* em041_101 k 1 (mask 2) */

/* jointMtx(unit, joint, float out[16]): world matrix of a joint [4U 0x930894] (em089_shell016.c, C) */
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx    FN(joint_mtx_t, 0xc1660)
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
#define EFX_XF       0x150
#define EFX_REQ_SIZE 0x100
#define A16_RAD      (6.28318531f / 65536.0f)

static struct {
    void *owner, *eff[2];
    uint32_t motion;
    float life;
} s_laser;

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

/* 0xc6b848: Q = J3 + M3 (0, 0, 180), direction Q -> P = M3's z axis; angles as em089_efx.c s016_seg */
static void place(void *self, float *q, uint32_t *pitch, uint32_t *yaw)
{
    float j[4], m[16];
    jointPos(self, LASER_JOINT, j);
    jointMtx(self, LASER_JOINT, m);
    for (int i = 0; i < 3; i++) q[i] = j[i] + LASER_OFF_Z * m[8 + i];
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

static void stop_all(void)
{
    for (int k = 0; k < 2; k++) {
        if (efx_alive(s_laser.eff[k])) efx_stop(s_laser.eff[k], 0);
        s_laser.eff[k] = 0;
    }
    s_laser.owner = 0;
}

/* a new quest: the old handles died with the old one's effects */
void em005_01_laser_reset(void)
{
    s_laser.owner = s_laser.eff[0] = s_laser.eff[1] = 0;
}

/* every frame (em005_01_act_c): 4U 0xc6b848 placement + the shell's end 0xc6e8d4 (HP 0 too: the death action runs
 * outside slot 125, so its motion change may never be seen here) */
void em005_01_laser_tick(void *self)
{
    if (s_laser.owner != self) return;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    s_laser.life -= FIELD(float, rec, REC_MOT_SPEED) * FIELD(float, self, EN_DT);
    if (s_laser.life <= 0.0f || curMotion(self) != s_laser.motion || FIELD(int32_t, rec, REC_HP) <= 0) {
        static uint32_t s_lines;
        if (++s_lines <= 20)
            logf("bgport: laser end (%s, life %d)", s_laser.life <= 0.0f ? "life" : "motion / HP", (int32_t)s_laser.life);
        stop_all();
        return;
    }
    float q[4];
    uint32_t pitch, yaw;
    place(self, q, &pitch, &yaw);
    float rot[4] = {(float)pitch * A16_RAD, (float)yaw * A16_RAD, 0.0f, 0.0f};
    for (int k = 0; k < 2; k++) {
        void *eff = s_laser.eff[k];
        if (!efx_alive(eff)) continue;
        efx_set_pos(eff, q, 0);
        void *xf = FIELD(void *, eff, EFX_XF);
        if (xf) efx_set_rot(xf, rot);
    }
}

/* GU 0xd2dfe0 (r1 = the shell message, r4 = this): d2da3c's frame-160 shell post, before the request */
int em005_01_laser_c(uint32_t *regs)
{
    static uint32_t s_lines;
    void *self = (void *)regs[R4];
    if (!self || FIELD(uint16_t, self, EN_ID) != BLACK_GRAVIOS_EM_ID) return 0;
    if (s_laser.owner) stop_all();
    float q[4];
    uint32_t pitch, yaw;
    place(self, q, &pitch, &yaw);
    s_laser.owner = self;
    s_laser.motion = curMotion(self);
    s_laser.life = LASER_LIFE;
    s_laser.eff[0] = post_at(self, FX_LASER_A, q, pitch, yaw);
    s_laser.eff[1] = post_at(self, FX_LASER_B, q, pitch, yaw);
    void *xf = efx_alive(s_laser.eff[0]) ? FIELD(void *, s_laser.eff[0], EFX_XF) : 0;
    if (++s_lines <= 20)
        logf("bgport: laser em041_101 (entry %u) at %d %d %d pitch %x yaw %x -> %x %x, scale x1000 %d %d %d",
             FIELD(uint32_t, (void *)regs[R1], 0x8), (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], pitch, yaw,
             (uint32_t)s_laser.eff[0], (uint32_t)s_laser.eff[1],
             xf ? (int32_t)(FIELD(float, xf, 0x60) * 1000.0f) : -1, xf ? (int32_t)(FIELD(float, xf, 0x64) * 1000.0f) : -1,
             xf ? (int32_t)(FIELD(float, xf, 0x68) * 1000.0f) : -1);
    return 0;
}
