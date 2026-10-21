/* em067_01_shell016.c: Tigerstripe's 7/70 sand / air blast = MH4U uShell016 subtypes 38 (Dunes) / 49 (other stages)
 * (notes/blast.md), as a GU class derived from uShellEnemy with the framework of Gogmazios' uShell016 port
 * (monsters/gogmazios/module/em089_shell016.c: own DTI, own request instead of the shell table, slot 79 setup,
 * slot 9 per frame).
 *
 * 4U behaviour ported (38 and 49 run the same code; data differs):
 *  - ctor: x angle = the 7/70 site's clamped pitch + owner x angle, y = owner yaw, owner motion at spawn.
 *  - init: life 21, attack record 33 / 39 = our HDS entries 1 / 2 of GU's breath family sp_02 (file 0x8a76,
 *    build_em067_01_arc.py BLAST: capsules on bone 1001, r208 / r260, hit window frames 7..21), sound 201 at owner
 *    joint 3, effect em092_001 element 1 (PEL list-2 record 4238 / 4249: scale (0.8, 0.8, 1.0) / 1.0).
 *  - per frame (0xc6be68): start Q = joint 131 + M (0, -60, 0) (M = the joint's matrix), far point P = joint 131 +
 *    Ry(y) Rx(x) (0, -60, 4000) in WORLD axes (the identity matrix 0x10e6448, angles frozen at spawn); the effect sits
 *    at Q along Q -> P; sounds 205 + 210 at the capsule point nearest to the listener (started once, then moved);
 *    life -= owner motion step; end when the owner's motion changed or the life is out (0xc6e8d4).
 *  - end (uEffect015 slot 19): the effect stops and em092_200 (record 4300, uEffect002 49) plays at its last place.
 * No map test, ground post or camera shake for these subtypes (4U has none). Multiplayer: posted from the 7/70 handler
 * on every machine, as 4U (no controller test anywhere in 38 / 49); each machine tests its own hunters. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

/* ---- GU addresses (main offsets), as em089_shell016.c ---- */
#define DTI_uShellEnemy      ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy       MAIN(0x175b268)
#define VT_uShellEnemy_SLOTS 83
#define DTIVT_uShellEnemy    MAIN(0x175b3bc)
#define SIZE_uShellEnemy     0x15d0u
#define uShellEnemy_ctor     FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor     FN(ctor_t, 0x43b488)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)
typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource   FN(shell_res_t, 0x4a1c84)
typedef int (*shell_hashit_t)(void *self);
#define uShell_hasHitData    FN(shell_hashit_t, 0x4a2744)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource         FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd              FN(unit_add_t, 0xc067ec)
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd          FN(shell_mgr_add_t, 0x48c6c8)
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx             FN(joint_mtx_t, 0xc1660)     /* [0x930894] */
#define SHELL_MGR            (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR             (*(void **)MAIN(0x2126f48))
#define DTI_PARAM            ((MtDTI *)MAIN(0x188cb88))
#define VT_PARAM             MAIN(0x17556a0)
#define ZERO_VEC             MAIN(0x191e850)
#define SHELL_MAX_LIVE   144
#define SHELL_LIVE_LIST  0x6d8c
#define SLOT_KILL        16
#define SLOT_MOVE        9
#define SLOT_SETUP       79
#define SLOT_ARM_ATTACK  80
#define SH_POS           0x40     /* capsule far point P [4U +0x100] */
#define SH_POS2          0x1000   /* capsule start Q [4U +0x120] */
#define SH_ANGLES        0xfe8
#define SH_ATK0_F14      0x13bc
#define SH_AREA          0x1054
#define SH_DT            28
#define REC_MOT_SPEED    0x398

/* sounds (em089_snd.c: the GU twins of 4U's sSoundControl calls) */
typedef void *(*snd_joint_t)(void *mgr, uint32_t id, void *owner, uint32_t joint, uint32_t area, int32_t m2);
typedef void *(*snd_pos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
typedef void (*snd_move_t)(void *mgr, uint32_t id, void *owner, void *owner2, const float *pos);
#define snd_req_joint FN(snd_joint_t, 0x4efd74)   /* = 4U 0x2fcc50 */
#define snd_req_pos   FN(snd_pos_t, 0x4efb98)     /* = 4U 0x312484 */
#define snd_req_move  FN(snd_move_t, 0x4eff24)    /* = 4U 0x301074 */
#define SND_MGR       (*(void **)MAIN(0x1896f5c))

/* effects (em089_efx.c: PEL list-2 posts through the owner, live transform setters as GU's beam 0x10ab3d8) */
typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
typedef void (*efx_stop_t)(void *eff, uint32_t now);
#define efx_stop     FN(efx_stop_t, 0x32a400)
typedef void (*efx_set_pos_t)(void *eff, const float *pos, int32_t k);
#define efx_set_pos  FN(efx_set_pos_t, 0x32a45c)
typedef void (*efx_set_rot_t)(void *xf, const float *rot);
#define efx_set_rot  FN(efx_set_rot_t, 0x8a7dc4)
#define EFX_XF       0x150

#define BREATH_FILE   0x8a76u     /* shell\em\em067_00_shell02\em067_00_02 (asserted in build_em067_01_arc.py) */
#define BREATH_ID     291u        /* its shell-table row (uShellEm067_sp_02) */
#define BLAST_JOINT   131u
#define BLAST_OFF_Y   (-60.0f)
#define BLAST_LEN     4000.0f
#define BLAST_LIFE    21.0f
#define FX_END        4300u       /* em092_200 */
#define FX_END_FRAMES 3.0f        /* 4U uEffect002 event +0x40 (G: duration) */

/* ---- our fields after the uShellEnemy object (4U uShell016 offset in brackets) ---- */
#define S_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype 38 / 49 [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define S_ARMED   (SIZE_uShellEnemy + 0x02)
#define S_XANG    (SIZE_uShellEnemy + 0x04)   /* u32 [+0x290] */
#define S_YANG    (SIZE_uShellEnemy + 0x08)   /* u32 [+0x294] */
#define S_LIFE    (SIZE_uShellEnemy + 0x0c)   /* float [+0x13c] */
#define S_MOTION  (SIZE_uShellEnemy + 0x10)   /* u32 owner motion at spawn [+0x2a0] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x14)
#define S_EFF     (SIZE_uShellEnemy + 0x18)   /* uMHProofEffect* em092_001 */
#define S_SND     (SIZE_uShellEnemy + 0x1c)   /* u8 205 / 210 started [+0xf4] */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x20)

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;
static uint32_t s_serial;

#define VEC(p, off) (&FIELD(float, p, off))

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }
static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
static float a16_deg(uint32_t a) { a &= 0xffffu; return (float)(int32_t)(a >= 0x8000u ? (int32_t)a - 0x10000 : (int32_t)a) * (360.0f / 65536.0f); }
static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}
static float owner_step(void *owner)   /* 4U 0x94460c: owner motion speed * dt */
{
    return FIELD(float, FIELD(uint8_t *, owner, EN_RECORD), REC_MOT_SPEED) * FIELD(float, owner, EN_DT);
}
static int efx_alive(void *eff) { return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2; }

/* 4U 0xc6be68: Q = J + M (0, -60, 0); P = J + Ry(y) Rx(x) (0, -60, 4000) in world axes */
static void place(void *self, void *owner)
{
    float j[4], m[16];
    jointPos(owner, BLAST_JOINT, j);
    jointMtx(owner, BLAST_JOINT, m);
    float v[3] = {0.0f, BLAST_OFF_Y, BLAST_LEN};
    float s = sinf_gu(ang_rad(FIELD(uint32_t, self, S_XANG))), c = cosf_gu(ang_rad(FIELD(uint32_t, self, S_XANG)));
    float y = c * v[1] - s * v[2], z = s * v[1] + c * v[2];          /* 0xaad560: rotate (y, z) */
    v[1] = y; v[2] = z;
    s = sinf_gu(ang_rad(FIELD(uint32_t, self, S_YANG))); c = cosf_gu(ang_rad(FIELD(uint32_t, self, S_YANG)));
    float x = c * v[0] + s * v[2];                                    /* 0xaad5b0: rotate (x, z) */
    v[2] = c * v[2] - s * v[0];
    v[0] = x;
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) {
        q[i] = j[i] + BLAST_OFF_Y * m[4 + i];
        p[i] = j[i] + v[i];
    }
}

/* segment angles Q -> P as u16 (pitch = atan2(-dy, horizontal), yaw = atan2(dx, dz)) (0xc6e944) */
static void seg_angles(void *self, uint32_t *pitch, uint32_t *yaw)
{
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
    *yaw = rad_ang(atan2f_gu(dx, dz));
    *pitch = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));
}

static void orient(void *self)
{
    uint32_t pa, ya;
    seg_angles(self, &pa, &ya);
    FIELD(uint32_t, self, SH_ANGLES) = pa;
    FIELD(uint32_t, self, SH_ANGLES + 4) = ya;
}

/* ---- effects: PEL list-2 world records at Q along the blast (em089_efx.c post_full / s016_post) */
static void *fx_post(void *owner, void *self, uint32_t id)
{
    uint32_t buf[0x100 / 4 + 4], pa, ya;
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    const float *q = VEC(self, SH_POS2);
    seg_angles(self, &pa, &ya);
    efx_req_ctor(req);
    FIELD(uint32_t, req, 0x8) = 3;                                    /* GU's moving beam 0x10b04c4 */
    FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, owner, SH_AREA);
    FIELD(uint32_t, req, 0x14) |= 2u;                                 /* rotation in degrees */
    FIELD(float, req, 0x30) = a16_deg(pa); FIELD(float, req, 0x34) = a16_deg(ya);
    FIELD(float, req, 0x38) = 0.0f; FIELD(float, req, 0x3c) = 0.0f;
    FIELD(uint32_t, req, 0x1c) |= 1u;                                 /* world position */
    for (int i = 0; i < 3; i++) FIELD(float, req, 0xc0 + 4 * i) = q[i];
    FIELD(float, req, 0xcc) = 0.0f;
    void *eff = efx_post_u(owner, 2, id, req);
    efx_req_dtor(req);
    static uint32_t s_n;
    void *xf = eff ? FIELD(void *, eff, EFX_XF) : 0;
    if (++s_n <= 12)
        logf("tzport: em067_01 blast efx %u -> %x, scale x1000 %d %d %d", id, (uint32_t)eff,
             xf ? (int32_t)(FIELD(float, xf, 0x60) * 1000.0f) : -1, xf ? (int32_t)(FIELD(float, xf, 0x64) * 1000.0f) : -1,
             xf ? (int32_t)(FIELD(float, xf, 0x68) * 1000.0f) : -1);
    return eff;
}

static void fx_move(void *self)
{
    void *eff = FIELD(void *, self, S_EFF);
    if (!efx_alive(eff)) return;
    uint32_t pa, ya;
    seg_angles(self, &pa, &ya);
    float rot[4] = {ang_rad(pa), ang_rad(ya), 0.0f, 0.0f};
    efx_set_pos(eff, VEC(self, SH_POS2), 0);
    void *xf = FIELD(void *, eff, EFX_XF);
    if (xf) efx_set_rot(xf, rot);
}

/* the end effect em092_200: stopped after FX_END_FRAMES owner frames by em067_01_shell016_tick */
static struct { void *owner, *eff; float t; } s_end[4];

static void fx_end(void *self, void *owner)
{
    void *eff = FIELD(void *, self, S_EFF);
    if (efx_alive(eff)) efx_stop(eff, 0);
    FIELD(void *, self, S_EFF) = 0;
    void *e = fx_post(owner, self, FX_END);
    if (!e) return;
    uint32_t i = 0;
    while (i < 3 && s_end[i].eff) i++;
    if (s_end[i].eff && efx_alive(s_end[i].eff)) efx_stop(s_end[i].eff, 0);
    s_end[i].owner = owner; s_end[i].eff = e; s_end[i].t = FX_END_FRAMES;
}

void em067_01_shell016_tick(void *owner)
{
    for (uint32_t i = 0; i < 4; i++) {
        if (!s_end[i].eff || s_end[i].owner != owner) continue;
        if (!efx_alive(s_end[i].eff)) { s_end[i].eff = 0; continue; }
        s_end[i].t -= owner_step(owner);
        if (s_end[i].t <= 0.0f) { efx_stop(s_end[i].eff, 0); s_end[i].eff = 0; }
    }
}

/* ---- sounds (0xc6e9b4 case 0xc6ee98): 205 + 210 at the capsule point nearest to the listener */
static int listener_pos(float *out)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, out);
    return 1;
}

static void sound(void *self, void *owner)
{
    float l[4], pt[4] = {0};
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float d[3] = {q[0] - p[0], q[1] - p[1], q[2] - p[2]}, tt = 0.0f;
    if (listener_pos(l)) {
        float dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
        if (dd > 0.0f) tt = ((l[0] - p[0]) * d[0] + (l[1] - p[1]) * d[1] + (l[2] - p[2]) * d[2]) / dd;
        if (tt < 0.0f) tt = 0.0f;
        if (tt > 1.0f) tt = 1.0f;
    }
    for (int i = 0; i < 3; i++) pt[i] = p[i] + tt * d[i];
    void *m = SND_MGR;
    if (!m) return;
    if (FIELD(uint8_t, self, S_SND)) {
        snd_req_move(m, 205, owner, owner, pt);
        snd_req_move(m, 210, owner, owner, pt);
        return;
    }
    FIELD(uint8_t, self, S_SND) = 1;
    snd_req_pos(m, 205, owner, pt, FIELD(uint8_t, self, SH_AREA), -2);
    snd_req_pos(m, 210, owner, pt, FIELD(uint8_t, self, SH_AREA), -2);
}

static void kill(void *self, void *owner, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 20) logf("tzport: em067_01 blast %u (sub %u) end: %s", FIELD(uint32_t, self, S_SERIAL),
                          FIELD(uint8_t, self, S_SUB), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    if (owner) fx_end(self, owner);
    VCALL0(self, SLOT_KILL);
}

/* slot 79: base setup, then the 4U init 0xc69ddc (+ its tail call of the per-frame code: first placement / sounds) */
static int setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    place(self, owner);
    orient(self);
    FIELD(float, self, S_LIFE) = BLAST_LIFE;
    FIELD(uint8_t, self, S_STATE) = 1;
    void *m = SND_MGR;
    if (m) snd_req_joint(m, 201, owner, 3, FIELD(uint8_t, owner, SH_AREA), -2);
    sound(self, owner);
    FIELD(void *, self, S_EFF) = fx_post(owner, self, sub == 38 ? 4238 : 4249);
    uint32_t hds = sub == 38 ? 1 : 2;                                 /* build_em067_01_arc.py BLAST_HDS0 */
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        arm(self, 0, hds, -1, 31, 2, 0xffff, FIELD(float, self, SH_ATK0_F14));
        FIELD(uint8_t, self, S_ARMED) = 1;
    }
    static uint32_t s_n;
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    if (++s_n <= 30)
        logf("tzport: em067_01 blast %u spawn sub %u hds %u hit %u, %d %d %d -> %d %d %d",
             FIELD(uint32_t, self, S_SERIAL), sub, hds, FIELD(uint8_t, self, S_ARMED),
             (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], (int32_t)p[0], (int32_t)p[1], (int32_t)p[2]);
    return 1;
}

/* slot 9 = 4U slot 23 [0xc6ac64], case 0xc6be68 + the common tail 0xc6e8d4 */
static void move(void *self)
{
    uShell_move(self);                                                /* owner gone -> kill (4U 0x917620) */
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    void *owner = *(void **)(FIELD(uint8_t *, self, 0x136c) + 0xc);   /* param owner (uShell 0x4a1b6c) */
    if (!owner) return;
    place(self, owner);
    fx_move(self);
    sound(self, owner);
    float *life = &FIELD(float, self, S_LIFE);
    *life -= owner_step(owner);
    if (*life < 0.0f) *life = 0.0f;
    if (curMotion(owner) != FIELD(uint32_t, self, S_MOTION)) { kill(self, owner, "owner motion changed"); return; }
    if (*life <= 0.0f) { kill(self, owner, "life out"); return; }
    orient(self);
}

static void *shell_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static void shell_delete(void *self)
{
    void *eff = FIELD(void *, self, S_EFF);
    if (efx_alive(eff)) efx_stop(eff, 0);
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void do_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&shell_delete;
    s_vt[2 + 5] = (uint32_t)&get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&setup;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&shell_new;
    MtDTI_ctor(&s_dti, "uShellEm067TsBlast", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("tzport: uShellEm067TsBlast DTI %x id %x size %x, resource file %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE,
         BREATH_FILE);
}

/* 4U 0x6620c4 + uShell016 ctor 0xc6f900 for subtype 38 / 49: x = the site's clamped pitch d (+ owner x angle) */
void *em067_01_blast_post(void *self, uint32_t subtype, uint32_t d)
{
    static uint32_t s_fail;
    if (!s_registered) do_register();
    uint8_t *mgr = SHELL_MGR;
    if (!self || !mgr || (subtype != 38 && subtype != 49)) {
        if (++s_fail <= 20) logf("tzport: em067_01 blast dropped (owner %x sub %u mgr %x)", (uint32_t)self, subtype,
                                 (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("tzport: em067_01 blast dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = BREATH_ID;
    FIELD(uint32_t, param, 8) = 0;
    FIELD(void *, param, 0xc) = self;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint32_t, param, 0x30) = FIELD(uint32_t, self, 0xfe8);
    FIELD(uint32_t, param, 0x34) = FIELD(uint32_t, self, 0xfec);
    FIELD(uint32_t, param, 0x38) = FIELD(uint32_t, self, 0xff0);
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = shell_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(uint32_t, shell, S_XANG) = (d + FIELD(uint32_t, rec, REC_ANGLES)) & 0xffff;
    FIELD(uint32_t, shell, S_YANG) = FIELD(uint32_t, rec, REC_YAW) & 0xffff;
    FIELD(uint32_t, shell, S_MOTION) = curMotion(self);
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    uShell_setResource(shell, fileResource(0, BREATH_FILE));
    shell_setup_t setup_fn = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup_fn(shell, param) != 1) {
        if (++s_fail <= 20) logf("tzport: em067_01 blast setup failed (owner type %u)", FIELD(uint8_t, self, 0x1052));
        shell_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
