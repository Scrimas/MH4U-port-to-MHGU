/* em005_01_shell016.c: the hits of Black Gravios' laser 7/57 / 7/71 and spin beam 7/79 = MH4U uShell016 subtypes
 * 33 / 35 and 43 / 44, as a GU class derived from uShellEnemy (framework of Tigerstripe's em067_01_shell016.c and
 * Gogmazios' em089_shell016.c: own DTI, own request, slot 79 setup, slot 9 per frame). Their look is
 * em005_01_laser.c. C = confirmed in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Why (user test 2026-11-03: laser hits "inconsistent", spin beam "doesn't hurt"):
 *  - GU's laser (d2da3c, d2dfe4) posts shell02 entry 4 / 12 = class uShellEm005_sp_02 (DTI 0x1892f28, vtable
 *    0x17a02a4): its setup 0xd33cfc places it once from the owner joint, then the shared projectile move 0x3fca34
 *    drives it (C). 4U's capsule follows the head every frame (0xc6b848, C), and so does the beam we draw: the hit and
 *    the beam part. GU's spin beam (d2ef2c) posts no shell at all (C).
 *  - 4U (C): uShell016 at joint 3, Q = J3 + M3 off, P = Q + M3 (0, 0, 6400) every frame (M3 = joint 3's matrix);
 *    33 / 35: off (0, 0, 180), life 162 (0x804380); 43 / 44: off (0, -50, 100), life 100, 7/79 frame 99 (0x806170);
 *    life -= owner motion step, end at life 0 or when the owner's motion changes (0xc6e8d4). Attack records (index
 *    table 0x102bad8 u32[subtype]): 29 / 30 / 43 / 44 at 0x102b370 + 96, volumes (byte 0x19 -> 0x102b370[v]): bone
 *    1001 capsules r 360 / 240 / 180 / 110.
 *  - GU's own shell02 family (file 0x89bc, row 110) already holds them, converted by Capcom (C, compared byte for byte
 *    but +2 / +3 (99 -> 999) and +0x1a): HDS entries 5 / 6 = records 29 / 30 (HTS groups 2 / 3: bone 1001 r 360 /
 *    240), entries 1 / 3 = records 43 / 44 (groups 0 / 1: r 180 / 110). Bone 1001 = the segment this+0x40 ->
 *    this+0x1000 (GU 0x16e46c, em089_shell016.c). So no data change: this class arms those entries.
 * GU's own laser post is skipped (hook em005_01_laser at d2dfe0, MID_EXIT d2dfe8) and its message freed. */
#include <stdint.h>
#include "game.h"
#include "util.h"

/* ---- GU addresses (main offsets), as em067_01_shell016.c ---- */
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
#define REC_MOT_SPEED    0x398

#define SHELL02_FILE  0x89bcu     /* shell\em\em005_00_shell02\em005_00_02 */
#define SHELL02_ROW   110u        /* its shell-table row (uShellEm005_sp_02) */
#define BEAM_JOINT    3u
#define BEAM_LEN      6400.0f

/* ---- our fields after the uShellEnemy object (4U uShell016 offset in brackets) ---- */
#define S_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define S_ARMED   (SIZE_uShellEnemy + 0x02)
#define S_LIFE    (SIZE_uShellEnemy + 0x04)   /* float [+0x13c] */
#define S_MOTION  (SIZE_uShellEnemy + 0x08)   /* u32 owner motion at spawn [+0x2a0] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x0c)
#define S_OFFY    (SIZE_uShellEnemy + 0x10)   /* float offset y, z [+0x274 / +0x278] */
#define S_OFFZ    (SIZE_uShellEnemy + 0x14)
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

static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
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

/* 4U 0xc6b848 (cases 0x21 / 0x23 / 0x2b / 0x2c): Q = J + M (0, y, z); P = Q + M (0, 0, len) */
static void place(void *self, void *owner)
{
    float j[4], m[16];
    jointPos(owner, BEAM_JOINT, j);
    jointMtx(owner, BEAM_JOINT, m);
    float oy = FIELD(float, self, S_OFFY), oz = FIELD(float, self, S_OFFZ);
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) {
        q[i] = j[i] + oy * m[4 + i] + oz * m[8 + i];
        p[i] = q[i] + BEAM_LEN * m[8 + i];
    }
}

static void orient(void *self)   /* segment angles Q -> P as u16 (0xc6e944) */
{
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
    FIELD(uint32_t, self, SH_ANGLES) = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));
    FIELD(uint32_t, self, SH_ANGLES + 4) = rad_ang(atan2f_gu(dx, dz));
}

static void kill(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 30) logf("bgport: beam hit %u (sub %u) end: %s", FIELD(uint32_t, self, S_SERIAL),
                          FIELD(uint8_t, self, S_SUB), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* GU shell02 HDS entry of each subtype (see above) */
static uint32_t sub_hds(uint32_t sub) { return sub == 33 ? 5 : sub == 35 ? 6 : sub == 43 ? 1 : 3; }

/* slot 79: base setup, then the 4U init 0xc69ddc (first placement, life, attack) */
static int setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    place(self, owner);
    orient(self);
    FIELD(float, self, S_LIFE) = sub == 33 || sub == 35 ? 162.0f : 100.0f;   /* 0x102bbbc */
    FIELD(uint8_t, self, S_STATE) = 1;
    uint32_t hds = sub_hds(sub);
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, uint32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        arm(self, 0, hds, -1, 31, 2, 0xffff, FIELD(float, self, SH_ATK0_F14));
        FIELD(uint8_t, self, S_ARMED) = 1;
    }
    static uint32_t s_n;
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    if (++s_n <= 30)
        logf("bgport: beam hit %u spawn sub %u hds %u armed %u, %d %d %d -> %d %d %d", FIELD(uint32_t, self, S_SERIAL),
             sub, hds, FIELD(uint8_t, self, S_ARMED), (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], (int32_t)p[0],
             (int32_t)p[1], (int32_t)p[2]);
    return 1;
}

/* slot 9 = 4U slot 23 [0xc6ac64]: placement + the common tail 0xc6e8d4 */
static void move(void *self)
{
    uShell_move(self);                                                /* owner gone -> kill (4U 0x917620) */
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    void *owner = *(void **)(FIELD(uint8_t *, self, 0x136c) + 0xc);   /* param owner (uShell 0x4a1b6c) */
    if (!owner) return;
    place(self, owner);
    float *life = &FIELD(float, self, S_LIFE);
    *life -= owner_step(owner);
    if (*life < 0.0f) *life = 0.0f;
    if (curMotion(owner) != FIELD(uint32_t, self, S_MOTION)) { kill(self, "owner motion changed"); return; }
    if (FIELD(int32_t, FIELD(uint8_t *, owner, EN_RECORD), REC_HP) <= 0) { kill(self, "owner HP 0"); return; }
    if (*life <= 0.0f) { kill(self, "life out"); return; }
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
    MtDTI_ctor(&s_dti, "uShellEm005BgBeam", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("bgport: uShellEm005BgBeam DTI %x id %x size %x, resource file %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE,
         SHELL02_FILE);
}

/* 4U 0x6620c4 + uShell016 ctor 0xc6f900 for subtype 33 / 35 / 43 / 44 */
void *em005_01_beam_hit_post(void *self, uint32_t subtype)
{
    static uint32_t s_fail;
    if (!s_registered) do_register();
    uint8_t *mgr = SHELL_MGR;
    if (!self || !mgr || (subtype != 33 && subtype != 35 && subtype != 43 && subtype != 44)) {
        if (++s_fail <= 20) logf("bgport: beam hit dropped (owner %x sub %u mgr %x)", (uint32_t)self, subtype,
                                 (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("bgport: beam hit dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = SHELL02_ROW;
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
    int laser = subtype == 33 || subtype == 35;
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(float, shell, S_OFFY) = laser ? 0.0f : -50.0f;
    FIELD(float, shell, S_OFFZ) = laser ? 180.0f : 100.0f;
    FIELD(uint32_t, shell, S_MOTION) = curMotion(self);
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    uShell_setResource(shell, fileResource(0, SHELL02_FILE));
    shell_setup_t setup_fn = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup_fn(shell, param) != 1) {
        if (++s_fail <= 20) logf("bgport: beam hit setup failed (sub %u)", subtype);
        shell_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
