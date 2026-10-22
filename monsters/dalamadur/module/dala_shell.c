/* dala_shell.c: the framework of Dalamadur's attack shells (dala_shell.h). Same GU calls as dala_meteor.c (which
 * keeps its own copy) and Gogmazios' em089_shell*.c, where they were found (C there). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"

#define DTI_uShellEnemy      ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy       MAIN(0x175b268)
#define DTIVT_uShellEnemy    MAIN(0x175b3bc)
#define uShellEnemy_ctor     FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor     FN(ctor_t, 0x43b488)
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource   FN(shell_res_t, 0x4a1c84)
typedef int (*shell_hashit_t)(void *self);
#define uShell_hasHitData    FN(shell_hashit_t, 0x4a2744)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource         FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd              FN(unit_add_t, 0xc067ec)      /* = 4U 0x64608c(mgr, 18, shell) */
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd          FN(shell_mgr_add_t, 0x48c6c8)
#define SHELL_MGR            (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR             (*(void **)MAIN(0x2126f48))
#define DTI_PARAM            ((MtDTI *)MAIN(0x188cb88))
#define VT_PARAM             MAIN(0x17556a0)
#define ZERO_VEC             MAIN(0x191e850)
#define SHELL_MAX_LIVE       144
#define SHELL_LIVE_LIST      0x6d8c
#define SLOT_DEL             1
#define SLOT_DTI             5
#define SLOT_MOVE            9
#define SLOT_KILL            16
#define SLOT_SETUP           79
#define SLOT_ARM_ATTACK      80
typedef int (*shell_setup_t)(void *self, void *param);
/* sounds: mgr 4U *0xfccd6c = GU *(main + 0x1896f5c) (C, Gogmazios em089_snd.h) */
#define SND_MGR              (*(void **)MAIN(0x1896f5c))
typedef void *(*snd_obj_t)(void *mgr, uint32_t id, void *obj, int32_t joint, void *owner, uint32_t area, void *obj2);
typedef void *(*snd_pos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
typedef void (*snd_move_t)(void *mgr, uint32_t id, void *owner, void *owner2, const float *pos);
#define snd_req_obj          FN(snd_obj_t, 0x4efe58)
#define snd_req_pos          FN(snd_pos_t, 0x4efb98)
#define snd_req_move         FN(snd_move_t, 0x4eff24)
typedef void (*cam_shake_pos_t)(void *owner, uint32_t id, const float *pos, uint32_t zero);
#define camShakePos          FN(cam_shake_pos_t, 0x49eac)
typedef uint32_t (*player_area_t)(void);
#define playerArea           FN(player_area_t, 0x4971c)
#define REC_MOT_SPEED        0x398    /* owner motion speed multiplier [4U +668] (em089_shell016.c) */

static void *alloc_dti(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

void dala_shell_register(dala_shcls_t *c, const char *name, uint32_t size, void *(*new_fn)(MtDTI *),
                         void (*del)(void *), MtDTI *(*get_dti)(void *), void (*move)(void *),
                         int (*setup)(void *, void *), void (*kill)(void *))
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) c->vt[i] = base_vt[i - 2];
    c->vt[2 + SLOT_DEL] = (uint32_t)del;
    c->vt[2 + SLOT_DTI] = (uint32_t)get_dti;
    if (move) c->vt[2 + SLOT_MOVE] = (uint32_t)move;
    if (setup) c->vt[2 + SLOT_SETUP] = (uint32_t)setup;
    if (kill) c->vt[2 + SLOT_KILL] = (uint32_t)kill;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) c->dti_vt[i] = base_dvt[i - 2];
    c->dti_vt[2 + 2] = (uint32_t)new_fn;
    c->size = size;
    MtDTI_ctor(&c->dti, name, DTI_uShellEnemy, size, 0, 0, 0);
    c->dti.w[0] = (uint32_t)&c->dti_vt[2];
    c->registered = 1;
    logf("dalaport: %s DTI %x id %x size %x, resource file %x (row %u)", name, (uint32_t)&c->dti, c->dti.w[7], size,
         DALA_SHELL_FILE, DALA_SHELL_ID);
}

void *dala_shell_new(dala_shcls_t *c)
{
    void *mem = alloc_dti(&c->dti, c->size);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&c->vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < c->size; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

void dala_shell_free(dala_shcls_t *c, void *self)
{
    uShellEnemy_dtor(self);
    void *a = get_allocator(&c->dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

void *dala_shell_param(void *owner, const char *what)
{
    static uint32_t s_fail;
    uint8_t *mgr = SHELL_MGR;
    if (!owner || !mgr) {
        if (++s_fail <= 30) logf("dalaport: %s post dropped (owner %x mgr %x)", what, (uint32_t)owner, (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, SH_STATE) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 30) logf("dalaport: %s post dropped: %u live shells", what, live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    uint8_t *param = alloc_dti(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = DALA_SHELL_ID;
    FIELD(uint32_t, param, 8) = 0;            /* resource entry 0 */
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
    return param;
}

void dala_shell_param_free(void *param)
{
    if (param) ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
}

void *dala_shell_start(void *shell, void *param, const char *what)
{
    static uint32_t s_fail;
    uShell_setResource(shell, fileResource(0, DALA_SHELL_FILE));
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        if (++s_fail <= 20) logf("dalaport: %s setup failed", what);
        VCALL0(shell, SLOT_DEL);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(SHELL_MGR, shell);
    return shell;
}

int dala_shell_arm(void *self, uint32_t hds, uint32_t a, uint32_t b, uint32_t group)
{
    if (uShell_hasHitData(self) != 1) {
        static uint32_t s_n;
        if (++s_n <= 5) logf("dalaport: shell %x: resource %x has no hit data (family %x not loaded?), no hit",
                             (uint32_t)self, FIELD(uint32_t, self, 0x1384), DALA_SHELL_FILE);
        return 0;
    }
    typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
    arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
    arm(self, 0, (int32_t)hds, -1, a, b, group & 0xffff, FIELD(float, self, SH_ATK0 + ATK_F14));
    return 1;
}

void dala_shell_slots_off(void *self)
{
    FIELD(uint8_t, self, 0x13ae) = 255; FIELD(uint8_t, self, 0x13ad) = 0;   /* 0x4a247c: attack slots 0..2 off */
    FIELD(uint8_t, self, 0x1466) = 255; FIELD(uint8_t, self, 0x1465) = 0;
    FIELD(uint8_t, self, 0x151e) = 255; FIELD(uint8_t, self, 0x151d) = 0;
}

void *dala_shell_owner(void *self)
{
    void *param = FIELD(void *, self, SH_PARAM);
    return param ? FIELD(void *, param, 0xc) : 0;
}

int dala_shell_live(void *self)
{
    return self && (FIELD(uint32_t, self, SH_STATE) & 7) - 1 < 2;
}

/* 4U frames per game tick for every Dalamadur shell = the shell's own GU time field +28 (as GU's own shells). User's
 * 4U footage (2026-10-21): a meteor takes about 2 s from the sky to the impact = this pace (kind 4: 9300 in 2.19 s);
 * the real-time clock (30-fps frames) made it 4.4 s, "2x slower". The earlier "too fast" was the visual / blast
 * mismatch (blast at the head's origin, dala_shell003.c). */
float dala_shell_dt(void *self) { return FIELD(float, self, SH_DT); }

int dala_shell_timer(void *self, float *t)
{
    if (*t <= 0.0f) { *t = 0.0f; return 1; }
    *t -= dala_shell_dt(self);
    if (*t > 0.0f) return 0;
    *t = 0.0f;
    return 1;
}

uint32_t dala_shell_group(void *self)
{
    return FIELD(uint16_t, self, SH_ATK0 + ATK_GROUP);
}

float dala_shell_owner_step(void *owner)
{
    return FIELD(float, FIELD(uint8_t *, owner, EN_RECORD), REC_MOT_SPEED) * FIELD(float, owner, EN_DT);
}

int dala_listener_pos(float *out)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, out);
    return 1;
}

void dala_snd_pos(void *owner, uint32_t id, const float *pos, uint32_t area)
{
    void *m = SND_MGR;
    if (m && owner && pos) snd_req_pos(m, id, owner, pos, area & 0xff, -2);
}

void dala_snd_obj(void *owner, uint32_t id, void *obj, uint32_t area)
{
    void *m = SND_MGR;
    if (m && owner && obj) snd_req_obj(m, id, obj, -1, owner, area & 0xff, obj);
}

void dala_snd_move(void *owner, uint32_t id, const float *pos)
{
    void *m = SND_MGR;
    if (m && owner && pos) snd_req_move(m, id, owner, owner, pos);
}

void dala_snd_joint_pos(void *owner, uint32_t id, uint32_t joint, uint32_t area)
{
    if (!owner) return;
    float p[4];
    jointPos(owner, joint, p);
    dala_snd_pos(owner, id, p, area);
}

void dala_cam_shake_pos(void *owner, uint32_t id, const float *pos, uint32_t area)
{
    if (owner && pos && area == playerArea()) camShakePos(owner, id, pos, 0);
}
