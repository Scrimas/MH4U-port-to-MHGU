/* uShellEm089: Gogmazios' tar blobs. Translation of MH4U uShell050 (vtable 0xe6e86c: slot 22 init 0xc8e938, slot 23
 * per frame 0xc8f028, slot 24 kill 0xc8fc18; ctor 0xc8fc1c) as a GU class derived from uShellEnemy (0x43b3f8, 0x15d0
 * bytes). notes/port-checklist.md "Tar shells (shell agent)" has the full 4U / GU analysis.
 *
 * GU shell framework used here:
 *  - request: our own copy of 0x48c4f0 (the shell table 0x1763448 has no free row and ids are capped at 412 by the
 *    manager layout): live count < 144, newInstance, 0x4a1c84(shell, resource), vt+0x13c (slot 79) setup(param),
 *    0xc067ec(unit manager, 18, shell, 0, 0), 0x48c6c8(shell manager, shell).
 *  - param: a cSetupParamEmBase01 (allocator of its DTI 0x188cb88, vtable 0x1755698 + 8), filled like Rathian's
 *    fireball (0xcf560c): +4 id, +8 kind (resource entry), +0xc owner. The uShell dtor deletes it (+0x136c).
 *  - hits: uShellEnemy slot 80 (0x43b51c -> 0x4a2790(this, slot, HDS index, -1, 31, 2, 0xffff)) arms the shell's
 *    184-byte attack slot 0 (this+0x13a8) from the resource's hit data (HDS) and hit volumes (HTS); the base updates
 *    it every frame (slot 11 0x4a2360). 4U uShell050 has its own inline attack records (0x1031990, record =
 *    {0,1,2,3,2,3,0,1,1,1}[kind], power 5 / 40): the same index is used as the HDS entry.
 *  - resource: EM089_SHELL_FILE (a file ID, fetched with 0x152960 = our file_id hook for our IDs). Until em089's own
 *    shell family exists it is Kushala's family 00 (0x8a02, shell\em\em024_00_shell00\em024_00_00, loaded with our
 *    arc): HDS powers 80 / 100 / 80 / 100 instead of 4U's 5 / 40 / 5 / 40. No resource = the blob flies without hits.
 *  - map: segment test 0x1838fc(collision manager *0x21270e0, from, to, area this+0x1054, out, 0, mask, flags
 *    0x4a2a8c(this)) = 4U 0x2b96e4 (same signature; EmBase classes use it for their ground checks).
 *  - kill: vt slot 16 (0x4a247c: attack slots off, unit state 3).
 * Attached effect (effects agent): 4U group 65 element 2 (em089_003) for drips, 14 (em089_016) for shots (per-kind
 * table 0x1031694, mask -1, scale 1.0) = PEL 3000 / 3001 posted on the owner with this shell as attach target
 * (em089_efx_post_on). The effect reads its target every frame, so the shell outlives it like GU's EmBase shells do
 * (0x3fa540 waits for its +0x1628 handle): slot 16 is ours, it disarms the attack slots (0x4a247c's bytes), stops the
 * effect (0x32a400(h, 0)) and keeps the shell (S_DYING) until the effect is dead, then runs the base kill; after
 * EFX_DIE_MAX frames it forces 0x32a400(h, 1). Every death path (life, impact, owner gone via uShell_move) goes
 * through slot 16; the dtor kills a live effect at once.
 * Not ported: the ground shadow marker 0xc07d54. */
#include "game.h"
#include "util.h"
#include "em089_shell.h"
#include "em089_snd.h"
#include "em089_shell051.h"
#include "em089_efx.h"

/* ---- GU addresses (main offsets) ---- */
#define DTI_uShellEnemy      ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy       MAIN(0x175b268)   /* object vtable address point (0x175b260 + 8), 83 slots */
#define VT_uShellEnemy_SLOTS 83
#define DTIVT_uShellEnemy    MAIN(0x175b3bc)   /* DTI vtable address point (0x175b3b4 + 8), 3 slots */
#define SIZE_uShellEnemy     0x15d0u
#define uShellEnemy_ctor     FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor     FN(ctor_t, 0x43b488)    /* slot 0: b 0x4a18b4 (uShell dtor: param, effects, resource) */
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)  /* slot 79: uShell setup 0x4a24f8 + owner+0x1052 == 1 */
typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)     /* slot 9: kills the shell when the owner is gone */
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource   FN(shell_res_t, 0x4a1c84)    /* this+0x1384 = res (addref / release) */
typedef int (*shell_hashit_t)(void *self);
#define uShell_hasHitData    FN(shell_hashit_t, 0x4a2744) /* resource has HDS and HTS */
typedef uint32_t (*shell_flags_t)(void *self);
#define uShell_colFlags      FN(shell_flags_t, 0x4a2a8c)  /* 64 | (this+0x1374 & 1) << 24 */
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource         FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd              FN(unit_add_t, 0xc067ec)
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd          FN(shell_mgr_add_t, 0x48c6c8)
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment           FN(map_segment_t, 0x1838fc)
#define SHELL_MGR            (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR             (*(void **)MAIN(0x2126f48))
#define COL_MGR              (*(void **)MAIN(0x21270e0))
#define DTI_PARAM            ((MtDTI *)MAIN(0x188cb88))   /* uShellEmBase01::cSetupParamEmBase01 */
#define VT_PARAM             MAIN(0x17556a0)              /* 0x1755698 + 8 */
#define ZERO_VEC             MAIN(0x191e850)

#define SHELL_MAX_LIVE   144
#define SHELL_LIVE_LIST  0x6d8c   /* shell manager: 144 live shells */
#define SLOT_KILL        16
#define SLOT_MOVE        9
#define SLOT_SETUP       79
#define SLOT_ARM_ATTACK  80
#define SH_POS           0x40     /* float x, y, z (cUnit position) */
#define SH_POS2          0x1000   /* bone-1001 hit capsule second point (GU 0x16e46c; GU shells write it themselves) */
#define SH_ANGLES        0xfe8    /* u32 x, y, z angle triple (u16 angles) */
#define SH_DT            28       /* float time scale (same field as the monsters' this+28) */
#define SH_AREA          0x1054   /* u8 map area (copied from the owner by the uShell setup) */
#define SH_ATK0_F14      0x13bc   /* attack slot 0 + 0x14 (float; EmBase01 passes it in s0 to slot 80) */

#ifndef EM089_SHELL_FILE
#define EM089_SHELL_FILE 0x1071du /* em089's own family shell\em\em089_00_shell00 (EM089_FILE_SHELL00) */
#endif
#define EM089_SHELL_ID   175u     /* that family's row id (param+4, read by base code through 0x4a1b38) */

/* ---- our fields after the uShellEnemy object (4U uShell050 offset in brackets) ---- */
#define S_KIND    (SIZE_uShellEnemy + 0x00)   /* u8 kind [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 flying, 2 done [+0xf1] */
#define S_ARMED   (SIZE_uShellEnemy + 0x02)   /* u8 attack slot armed */
#define S_JOINT   (SIZE_uShellEnemy + 0x04)   /* u32 spawn joint, 255 = owner position [+0x270] */
#define S_VEL     (SIZE_uShellEnemy + 0x08)   /* float[3] velocity [+320] */
#define S_ACC     (SIZE_uShellEnemy + 0x14)   /* float[3] acceleration [+336] */
#define S_PREV    (SIZE_uShellEnemy + 0x20)   /* float[3] previous position [+0x120] */
#define S_TARGET  (SIZE_uShellEnemy + 0x2c)   /* float[3] landing point of kinds 4 / 5 [+656] */
#define S_LIFE    (SIZE_uShellEnemy + 0x38)   /* float lifetime [+620, = +0x26c table: 480] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x3c)   /* u32 spawn number (log) */
#define S_EFX     (SIZE_uShellEnemy + 0x40)   /* attached effect handle [4U uShell050 effect pointer] */
#define S_DIE_T   (SIZE_uShellEnemy + 0x44)   /* float frames spent waiting for the effect to end */
#define S_DYING   (SIZE_uShellEnemy + 0x48)   /* u8 1 = killed, waiting for the effect */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x50)
#define EFX_DIE_MAX 300.0f
#define uShell_kill          FN(shell_fn_t, 0x4a247c)     /* base slot 16: attack slots off, 0x539de0 unit kill */

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;
static uint32_t s_serial;

#define VEC(p, off) (&FIELD(float, p, off))

/* ---- 4U uShell050 per-kind tables (static init 0xd38d44 into bss 0x10bc378 / 0x10bc3f0) ---- */
static const float k_vel[EM089_SHELL_KINDS][3] = {
    {0, 0, 0}, {0, 0, 0}, {0, 15, 20}, {0, 15, 20}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
};
static const float k_acc_y[EM089_SHELL_KINDS] = {-0.2f, -0.2f, -1.4f, -1.4f, -0.7f, -0.7f, -0.2f, -0.2f, -0.2f, -0.2f};
/* inline attack record per kind (0x1031a30 table: 0x9ab120's r3) = HDS entry index here */
static const uint8_t k_hit_rec[EM089_SHELL_KINDS] = {0, 1, 2, 3, 2, 3, 0, 1, 1, 1};
/* uShell051 subtype posted on a ground impact (jump tables 0xc8f200 / 0xc8f3e0), for the log */
static const uint8_t k_splash[EM089_SHELL_KINDS] = {1, 6, 1, 6, 1, 6, 16, 17, 19, 20};

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static void shell_kill(void *self)
{
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 16 (see the header): deferred kill while the attached effect lives */
static void shell_slot_kill(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (h && !em089_efx_alive(h)) FIELD(void *, self, S_EFX) = h = 0;
    if (!h) { FIELD(uint8_t, self, S_DYING) = 0; uShell_kill(self); return; }
    if (FIELD(uint8_t, self, S_DYING)) return;
    FIELD(uint8_t, self, S_DYING) = 1;
    FIELD(uint8_t, self, S_STATE) = 2;
    FIELD(float, self, S_DIE_T) = 0.0f;
    FIELD(uint8_t, self, 0x13ae) = 255; FIELD(uint8_t, self, 0x13ad) = 0;   /* 0x4a247c: attack slots off */
    FIELD(uint8_t, self, 0x1466) = 255; FIELD(uint8_t, self, 0x1465) = 0;
    FIELD(uint8_t, self, 0x151e) = 255; FIELD(uint8_t, self, 0x151d) = 0;
    em089_efx_stop(h);
}

/* per frame while S_DYING: base kill once the effect is dead (forced after EFX_DIE_MAX frames) */
static void shell_dying(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    float *t = &FIELD(float, self, S_DIE_T);
    *t += FIELD(float, self, SH_DT);
    if (h && em089_efx_alive(h) && *t >= EFX_DIE_MAX && *t < EFX_DIE_MAX + 1000.0f) {
        static uint32_t s_n;
        if (++s_n <= 20) logf("gogport: em089 efx shell %u: effect still alive after %d frames, forced stop",
                              FIELD(uint32_t, self, S_SERIAL), (int32_t)EFX_DIE_MAX);
        em089_efx_kill(h);
        *t = EFX_DIE_MAX + 1000.0f;           /* one more frame for the effect's own kill, then the shell goes */
        return;
    }
    if (h && em089_efx_alive(h) && *t < EFX_DIE_MAX + 1000.0f + 30.0f) return;
    FIELD(void *, self, S_EFX) = 0;
    FIELD(uint8_t, self, S_DYING) = 0;
    uShell_kill(self);
}

/* u16 angle -> radians; atan2 result -> u16 angle (4U 0x568c8c returns the u16 angle directly) */
static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }
static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }

static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* 4U slot 22 [0xc8e938]: position at the joint + (0, -50, 0) rotated by the owner yaw, velocity / acceleration from
 * the kind tables rotated by the shell angles (x 0, y = owner yaw, z 0), kinds 4 / 5 ballistic to the target. */
static void shell_init(void *self, void *owner)
{
    uint32_t kind = FIELD(uint8_t, self, S_KIND), joint = FIELD(uint32_t, self, S_JOINT);
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    float *pos = VEC(self, SH_POS), *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC);
    float j[4];
    if (joint != 255) jointPos(owner, joint, j);
    else { j[0] = FIELD(float, rec, REC_POS_X); j[1] = FIELD(float, rec, REC_POS_X + 4); j[2] = FIELD(float, rec, REC_POS_Z); }
    uint32_t yaw = FIELD(uint32_t, rec, REC_YAW) & 0xffff;
    float s = sinf_gu(ang_rad(yaw)), c = cosf_gu(ang_rad(yaw));
    /* offset (ox, oy, oz) = param +8..+0x10 = (0, -50, 0): x += c*ox + s*oz, y += oy, z += c*oz - s*ox */
    pos[0] = j[0]; pos[1] = j[1] - 50.0f; pos[2] = j[2];
    const float *v = k_vel[kind];
    vel[0] = c * v[0] + s * v[2]; vel[1] = v[1]; vel[2] = c * v[2] - s * v[0];
    acc[0] = 0.0f; acc[1] = k_acc_y[kind]; acc[2] = 0.0f;
    FIELD(uint32_t, self, SH_ANGLES) = 0;
    FIELD(uint32_t, self, SH_ANGLES + 4) = yaw;
    FIELD(uint32_t, self, SH_ANGLES + 8) = 0;
    if (kind == 4 || kind == 5) {
        const float *t = VEC(self, S_TARGET);
        float dx = t[0] - pos[0], dz = t[2] - pos[2], dy = t[1] - pos[1];
        float len = sqrt_f(dx * dx + dz * dz);
        if (len > 2750.0f) { dx *= 2750.0f / len; dz *= 2750.0f / len; len = 2750.0f; }
        float speed = (len * (1.0f / 75.0f) < 80.0f) ? len * 0.0125f : 75.0f;   /* 0xc8edac..0xc8edc8 */
        float time = speed > 0.0f ? len / speed : 80.0f;
        float k = len > 0.0f ? speed / len : 0.0f;
        vel[0] = dx * k; vel[2] = dz * k;
        vel[1] = (dy - acc[1] * time * (time * 0.5f)) / time;
    }
    FIELD(float, self, S_LIFE) = 480.0f;   /* +0x26c table: 0x43f00000 for every kind */
    float *prev = VEC(self, S_PREV), *p2 = VEC(self, SH_POS2);
    prev[0] = pos[0]; prev[1] = pos[1]; prev[2] = pos[2];
    p2[0] = pos[0]; p2[1] = pos[1]; p2[2] = pos[2];
}

/* slot 79: base setup, then the 4U init and the attack slot */
static int shell_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    shell_init(self, owner);
    FIELD(uint8_t, self, S_STATE) = 1;
    uint32_t kind = FIELD(uint8_t, self, S_KIND);
    em089_snd_shell_spawn(self, owner, kind, FIELD(uint8_t, self, SH_AREA));
    /* attached effect (4U table 0x1031694: kinds 2-5 element 14, the others element 2) */
    FIELD(void *, self, S_EFX) = em089_efx_post_on(owner, (kind >= 2 && kind <= 5) ? EM089_EFX_BLOB_SHOT :
                                                   EM089_EFX_BLOB_DRIP, self);
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        arm(self, 0, k_hit_rec[kind], -1, 31, 2, 0xffff, FIELD(float, self, SH_ATK0_F14));
        FIELD(uint8_t, self, S_ARMED) = 1;
    } else {
        static uint8_t s_once;
        if (!s_once) { s_once = 1; logf("gogport: em089 shell: resource %x has no hit data, blobs do not hit",
                                         FIELD(uint32_t, self, 0x1384)); }
    }
    static uint32_t s_n;
    const float *p = VEC(self, SH_POS), *v = VEC(self, S_VEL);
    if (++s_n <= 60)
        logf("gogport: em089 shell %u spawn kind %u joint %u pos %d %d %d vel %d %d %d hit %u", FIELD(uint32_t, self, S_SERIAL),
             kind, FIELD(uint32_t, self, S_JOINT), (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], (int32_t)(v[0] * 100.0f),
             (int32_t)(v[1] * 100.0f), (int32_t)(v[2] * 100.0f), FIELD(uint8_t, self, S_ARMED));
    return 1;
}

/* slot 9 = 4U slot 23 [0xc8f028]: lifetime, integration, map segment test, orientation */
static void shell_move(void *self)
{
    /* drop a dead effect handle every frame (GU EmBase shells 0x3fa330..0x3fa36c: (h+0xc & 7) - 1 >= 2 -> h = 0),
     * so no later check reads an effect the unit manager has freed */
    if (FIELD(void *, self, S_EFX) && !em089_efx_alive(FIELD(void *, self, S_EFX))) FIELD(void *, self, S_EFX) = 0;
    uShell_move(self);                        /* owner gone -> kill (4U 0x917620 check) */
    if (FIELD(uint8_t, self, S_DYING)) { shell_dying(self); return; }
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    float dt = FIELD(float, self, SH_DT);
    float *life = &FIELD(float, self, S_LIFE);
    *life -= dt;
    uint32_t kind = FIELD(uint8_t, self, S_KIND), serial = FIELD(uint32_t, self, S_SERIAL);
    if (*life <= 0.0f) {
        static uint32_t s_n;
        if (++s_n <= 30) logf("gogport: em089 shell %u kind %u timed out", serial, kind);
        shell_kill(self);
        return;
    }
    float *pos = VEC(self, SH_POS), *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC), *prev = VEC(self, S_PREV);
    prev[0] = pos[0]; prev[1] = pos[1]; prev[2] = pos[2];
    float h = dt * dt * 0.5f;                 /* 0x9a94f4: pos += v dt + a dt^2 / 2; 0x9ab0a0: v += a dt */
    for (int i = 0; i < 3; i++) { pos[i] += vel[i] * dt + acc[i] * h; vel[i] += acc[i] * dt; }
    float *p2 = VEC(self, SH_POS2);           /* bone-1001 capsule end = previous position (4U +0x120) */
    p2[0] = prev[0]; p2[1] = prev[1]; p2[2] = prev[2];
    float out[4] = {0, 0, 0, 0};
    void *col = COL_MGR;
    uint32_t r = col ? mapSegment(col, pos, prev, FIELD(uint8_t, self, SH_AREA), out, 0, 48,
                                  uShell_colFlags(self) | 128) : 0;
    if (r) {
        pos[0] = out[0]; pos[1] = out[1]; pos[2] = out[2];
        uint32_t ground = (r & 34) == 0;
        static uint32_t s_n;
        if (++s_n <= 60)
            logf("gogport: em089 shell %u kind %u impact %s (%x) at %d %d %d%s", serial, kind, ground ? "ground" : "wall",
                 r, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
                 ground ? " -> uShell051 splash" : "");
        em089_snd_shell_land(self, FIELD(void *, FIELD(void *, self, 0x136c), 0xc), kind, pos,
                             FIELD(uint8_t, self, SH_AREA));
        if (ground)    /* uShell051 splash (em089_shell051.c): own attack, lifetime and sound 220 at its frame 58 */
            em089_shell051_post(FIELD(void *, FIELD(void *, self, 0x136c), 0xc), k_splash[kind], pos, 0);
        shell_kill(self);
        return;
    }
    if (kind >= 2 && kind <= 5) {             /* orient along the velocity (0xc8f284) */
        float hz = sqrt_f(vel[0] * vel[0] + vel[2] * vel[2]);
        FIELD(uint32_t, self, SH_ANGLES) = rad_ang(atan2f_gu(-vel[1], hz));
        FIELD(uint32_t, self, SH_ANGLES + 4) = rad_ang(atan2f_gu(vel[0], vel[2]));
        FIELD(uint32_t, self, SH_ANGLES + 8) = rad_ang(atan2f_gu(-vel[0], vel[1]));
    }
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
    void *h = FIELD(void *, self, S_EFX);
    if (em089_efx_alive(h)) em089_efx_kill(h);   /* deleted without our kill (area / quest teardown) */
    FIELD(void *, self, S_EFX) = 0;
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *shell_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void shell_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&shell_delete;
    s_vt[2 + 5] = (uint32_t)&shell_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&shell_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&shell_setup;
    s_vt[2 + SLOT_KILL] = (uint32_t)&shell_slot_kill;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&shell_new;
    MtDTI_ctor(&s_dti, "uShellEm089", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("gogport: uShellEm089 DTI %x id %x size %x, resource file %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE,
         EM089_SHELL_FILE);
}

/* GU 0x48c4f0 for our class (see the header) */
void *em089_shell_post(void *owner, uint32_t kind, uint32_t joint, const float *target)
{
    static uint32_t s_fail;
    if (!s_registered) shell_register();
    uint8_t *mgr = SHELL_MGR;
    if (!owner || kind >= EM089_SHELL_KINDS || !mgr) {
        if (++s_fail <= 20) logf("gogport: em089 shell post dropped (owner %x kind %u mgr %x)", (uint32_t)owner, kind,
                                 (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("gogport: em089 shell post dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = EM089_SHELL_ID;
    FIELD(uint32_t, param, 8) = 0;            /* resource entry 0 (exists in every family) */
    FIELD(void *, param, 0xc) = owner;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint32_t, param, 0x30) = FIELD(uint32_t, owner, 0xfe8);
    FIELD(uint32_t, param, 0x34) = FIELD(uint32_t, owner, 0xfec);
    FIELD(uint32_t, param, 0x38) = FIELD(uint32_t, owner, 0xff0);
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = shell_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    FIELD(uint8_t, shell, S_KIND) = (uint8_t)kind;
    FIELD(uint32_t, shell, S_JOINT) = joint;
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    {   /* rate check (test 5: "more drips than usual in phase 2"): per-kind totals every 64 blobs */
        static uint16_t s_kn[EM089_SHELL_KINDS];
        s_kn[kind]++;
        if ((s_serial & 63) == 0 && s_serial <= 64 * 40)
            logf("gogport: em089 shell posts: %u (kinds 0-9: %u %u %u %u %u %u %u %u %u %u)", s_serial, s_kn[0],
                 s_kn[1], s_kn[2], s_kn[3], s_kn[4], s_kn[5], s_kn[6], s_kn[7], s_kn[8], s_kn[9]);
    }
    if (target) { float *t = VEC(shell, S_TARGET); t[0] = target[0]; t[1] = target[1]; t[2] = target[2]; }
    void *res = fileResource(0, EM089_SHELL_FILE);
    uShell_setResource(shell, res);
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {           /* the uShell setup stored param: the dtor deletes it */
        if (++s_fail <= 20) logf("gogport: em089 shell setup failed (owner type %u)", FIELD(uint8_t, owner, 0x1052));
        shell_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
