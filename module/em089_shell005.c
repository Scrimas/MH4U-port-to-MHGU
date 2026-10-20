/* uShellEm089Quake: the MH4U quake / tremor shell uShell005 (event type 5, poster 0x661d18; 632 B, vtable 0xe6d4bc:
 * ctor 0xc59944, slot 22 init 0xc59698, slot 23 per frame 0xc598d0), posted by the uEnemy ground impact 0x954e5c
 * (em089 2/35), as a GU class derived from uShellEnemy with the same framework calls as em089_shell.c
 * (notes/port-checklist.md "Quake shell uShell005").
 *
 * 4U 0x954e5c (shell part): return when W+412 (pos y) > W+0x624 (ground y under the monster) + height; position =
 * (W+0x198, W+0x624, W+0x1a0) + off * size factor (0x923fc8 = GU 0xbecf0) * scale rotated by the yaw W+0x1ac
 * (0xaad5b0); kind 1..7 -> subtype 1, 2, 11, 12, 26, 27, 28; event scale = scale, u16 0xffff. W+0x624 -> GU rec+0x5b4
 * (S: GU Rathian passes (rec+0x40, rec+0x5b4, rec+0x48) to its shell requests where 4U Rathian passes (W+0x198,
 * W+0x624, W+0x1a0) to 0x661d18 at 0x6ea7d4).
 * uShell005: ctor: owner-posted (event byte 8 = 1, byte 0 = 0) -> +0x270 = size factor * scale; init: life +316 =
 * 100, attack 0x9ab120(records 0x1025b58 + 112, volumes 0x1025b58, record = subtype, 7 (5 for subtypes 5 / 9 / 13),
 * 2) -> our HDS entry 20 (subtype 1: attack type 6 = tremor, power 0, active frames 14..24) / HTS group 10 (sphere
 * on bone 255, radius 600), slot scale +0x17c (= attack slot 0 + 20 = GU this+0x13bc) = +0x270; per frame: life -=
 * dt, end at <= 0 or when the owner is gone. Not ported: the stage-16 effect of subtypes 0 / 11 / 12 (not em089's). */
#include "game.h"
#include "util.h"
#include "em089_shell005.h"

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
typedef float (*size_factor_t)(void *self);
#define sizeFactor           FN(size_factor_t, 0xbecf0)   /* = 4U 0x923fc8 (C, apimap 99/99) */
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
#define SH_POS           0x40
#define SH_POS2          0x1000
#define SH_ANGLES        0xfe8
#define SH_DT            28
#define SH_ATK0_SCALE    0x13bc
#define REC_GROUND_Y     0x5b4    /* ground height under the monster [4U W+0x624] (S) */

#ifndef EM089_SHELL_FILE
#define EM089_SHELL_FILE 0x1071du
#endif
#define EM089_SHELL_ID   175u
#define HDS_QUAKE        20u      /* uShell005 record 1 */

#define S_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)
#define S_ARMED   (SIZE_uShellEnemy + 0x02)
#define S_LIFE    (SIZE_uShellEnemy + 0x04)   /* float [+316] */
#define S_SCALE   (SIZE_uShellEnemy + 0x08)   /* float size factor * event scale [+0x270] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x0c)
#define SHELL_SIZE (SIZE_uShellEnemy + 0x10)

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

static void s005_kill(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 20) logf("gogport: em089 quake shell %u end: %s", FIELD(uint32_t, self, S_SERIAL), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 79: base setup + 4U init 0xc59698 */
static int s005_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    FIELD(uint8_t, self, S_STATE) = 1;
    FIELD(float, self, S_LIFE) = 100.0f;
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    q[0] = p[0]; q[1] = p[1]; q[2] = p[2];
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        uint32_t a = (sub == 5 || sub == 9 || sub == 13) ? 5 : 7;
        arm(self, 0, HDS_QUAKE, -1, a, 2, 0xffff, FIELD(float, self, SH_ATK0_SCALE));
        FIELD(uint8_t, self, S_ARMED) = 1;
    }
    /* +0x17c = +0x270: the slot scale (times the value GU leaves there after arming) */
    FIELD(float, self, SH_ATK0_SCALE) = FIELD(float, self, SH_ATK0_SCALE) * FIELD(float, self, S_SCALE);
    static uint32_t s_n;
    if (++s_n <= 20)
        logf("gogport: em089 quake shell %u spawn sub %u hit %u at %d %d %d scale %d/1000", FIELD(uint32_t, self, S_SERIAL),
             sub, FIELD(uint8_t, self, S_ARMED), (int32_t)p[0], (int32_t)p[1], (int32_t)p[2],
             (int32_t)(FIELD(float, self, SH_ATK0_SCALE) * 1000.0f));
    return 1;
}

/* slot 9 = 4U 0xc598d0 */
static void s005_move(void *self)
{
    uShell_move(self);                                    /* owner gone -> kill (4U 0x1d5880 owner check) */
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    float *life = &FIELD(float, self, S_LIFE);
    *life -= FIELD(float, self, SH_DT);
    if (*life <= 0.0f) { s005_kill(self, "life out"); return; }
    /* 0xc598f4: also ends when the attack object's active byte (+0x16d, cleared by 0xb700a8 when the window is
     * over) is 0: record 1 = start 14 + length 10 -> 24 frames */
    if (100.0f - *life >= 24.0f) s005_kill(self, "attack window end");
}

static void *s005_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static void s005_delete(void *self)
{
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *s005_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void s005_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&s005_delete;
    s_vt[2 + 5] = (uint32_t)&s005_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&s005_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&s005_setup;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&s005_new;
    MtDTI_ctor(&s_dti, "uShellEm089Quake", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("gogport: uShellEm089Quake DTI %x id %x size %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE);
}

void *em089_shell005_ground_impact(void *self, uint32_t kind, const float *off, float scale, float height)
{
    static const uint8_t k_kind_sub[8] = {0, 1, 2, 11, 12, 26, 27, 28};
    static uint32_t s_fail;
    if (!self || kind < 1 || kind > 7) return 0;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    float gy = FIELD(float, rec, REC_GROUND_Y);
    if (FIELD(float, rec, REC_POS_X + 4) > gy + height) {        /* too high above the ground: no quake */
        if (++s_fail <= 20) logf("gogport: em089 quake: monster too high (y %d ground %d)",
                                 (int32_t)FIELD(float, rec, REC_POS_X + 4), (int32_t)gy);
        return 0;
    }
    uint32_t sub = k_kind_sub[kind];
    if (sub != 1) {
        if (++s_fail <= 20) logf("gogport: em089 quake subtype %u has no hit data (only 1)", sub);
        return 0;
    }
    if (!s_registered) s005_register();
    uint8_t *mgr = SHELL_MGR;
    if (!mgr) return 0;
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) return 0;
    float size = sizeFactor(self);
    float pos[3] = {FIELD(float, rec, REC_POS_X), gy, FIELD(float, rec, REC_POS_Z)};
    if (off) {                                                   /* 0x954ecc: off * size * scale, rotated by the yaw */
        float k = size * scale, ox = off[0] * k, oy = off[1] * k, oz = off[2] * k;
        float a = (float)(FIELD(uint32_t, rec, REC_YAW) & 0xffff) * (6.28318531f / 65536.0f);
        float s = sinf_gu(a), c = cosf_gu(a);
        pos[0] += c * ox + s * oz; pos[1] += oy; pos[2] += c * oz - s * ox;
    }
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = EM089_SHELL_ID;
    FIELD(void *, param, 0xc) = self;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = s005_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)sub;
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    FIELD(float, shell, S_SCALE) = size * scale;                 /* ctor 0xc59a20 */
    float *p = VEC(shell, SH_POS);
    p[0] = pos[0]; p[1] = pos[1]; p[2] = pos[2];
    FIELD(uint32_t, shell, SH_ANGLES) = FIELD(uint32_t, rec, REC_ANGLES);   /* angles = W+424 (event +0x10) */
    FIELD(uint32_t, shell, SH_ANGLES + 4) = FIELD(uint32_t, rec, REC_YAW);
    FIELD(uint32_t, shell, SH_ANGLES + 8) = FIELD(uint32_t, rec, REC_YAW + 4);
    uShell_setResource(shell, fileResource(0, EM089_SHELL_FILE));
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        if (++s_fail <= 20) logf("gogport: em089 quake shell setup failed");
        s005_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
