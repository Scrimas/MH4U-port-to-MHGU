/* uEm090_00 (Dalamadur / Shah Dalamadur, head half = 4U uEm024): a new monster class derived from uFestaEnemy.
 * Goal D2: the 4U actions, action start, AI conditions and end slot (em090_act.c, dala.c, dala_react.c). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"
#include "dala_gather.h"
#include "dala_shah.h"

MtDTI g_em090_dti;                                /* referenced by the registry class table (tables.S) */
static uint32_t s_dti_vt[2 + 3];                  /* 2 header words + 3 slots; address point = &s_dti_vt[2] */
static uint32_t s_vt[2 + VT_uFestaEnemy_SLOTS];   /* copy of uFestaEnemy's object vtable with our overrides */

void em090_action_start(void *self, uint32_t cat, uint32_t num);   /* em090_act.c */
int em090_cond(void *self, uint32_t id);
void em090_state_frame(void *self);
void dala_bgm_register(void);         /* dala_bgm.c */

#define SLOT_END 247          /* = 4U slot 89 (vt+0x164), dala_end_slot */

static void *em090_ctor(void *self)
{
    uFestaEnemy_ctor(self);
    FIELD(uint32_t, self, 0) = (uint32_t)&s_vt[2];
    FIELD(uint32_t, self, EN_WORK) = FIELD(uint32_t, self, EN_RECORD) + 96;
    dala_fields_init(self);
    DALA_WORK(int32_t, self, DALA_W_GATHER) = -1;   /* no on-body point yet (handle 0 is a valid point) */
    return self;
}

/* DTI slot 2 */
static void *em090_new_instance(MtDTI *dti)
{
    (void)dti;
    void *a = get_allocator(&g_em090_dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    void *mem = alloc(a, DALA_SIZE, 16, g_em090_dti.w[7]);
    logf("dalaport: uEm090_00 new_instance -> %x", (uint32_t)mem);
    return mem ? em090_ctor(mem) : 0;
}

/* object slot 1: deleting destructor */
static void em090_delete(void *self)
{
    dala_forget_half(self);
    dala_walk_release(self);
    dala_head_point_release(self);   /* 4U never releases it; here no handle outlives the head */
    dala_shah_release(self);         /* the zone effects still alive (port-only) */
    uFestaEnemy_dtor(self);
    void *a = get_allocator(&g_em090_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

/* object slot 125: run the current action, per frame */
static void em090_action(void *self)
{
    em090_act_run(self);
    dala_ctl_log(self, "head");
    dala_place_log(self);
}

/* object slot 118: spawn setup (from 0xb8c54, after every mesh group was set visible). The field-3 XFS of each half
 * holds its 4U spawn visibility in every state (tools/build_dalamadur_arc.py, 4U masks 0x76d5a0 / 0x89fe4c).
 * 4U slot 39 0x76d5a0 also: placement 0, walk set 2 (goal D4), work +0 / +4 / +8 / +0x10 / +0x3c = 0, +0xc =
 * placement; the body effects uEffect002 28 at joints 200 / 5 (0x76d77c -> 0xc0a9d4: dala_efx_body_spawn); the
 * on-body carve point 0x9357ec -> work+0x50 (0x76d848, dala_gather.c); the material animations "breath" / "usually"
 * (0x76d668: materials of type 1 / 2, work +0x44 / +0x48, dala_mat.c). Not ported: the effect-manager object
 * 0xc0c5b8 (work+0x68; its heat aura: dala_efx_heat) and 0xc08374, Shah's effect slots 0xc07bb8 (goal D8). */
static void em090_spawn_setup(void *self, uint32_t flag)
{
    void *pm = FIELD(void *, self, EN_PARTS_MGR);
    applyPartsState(self, 0);
    dala_state_frame(self);          /* no push before the first update (the setup cleared the flag, 0xb9d2c) */
    FIELD(float, REC(self), REC_POS_X + 4) = 0.0f;   /* 4U's spawn point y (build_dalamadur_quest.py: (0, 0, 0)) */
    dala_register_half(self, 0);
    MODE(self) = 0;
    DALA_WORK(uint8_t, self, 0x0c) = 0;
    dala_mat_spawn(self);            /* 0x76d668, before the body effects */
    dala_efx_body_spawn(self, 0);    /* 4U order: before 0x91b158 */
    dala_head_point_spawn(self);     /* 0x76d848, also before 0x91b158 */
    setBattleState(self, 1);
    dala_shah_spawn(self);           /* 0x76d8ac (returns at once for Dalamadur) */
    dala_walk_spawn(self);
    logf("dalaport: em090 spawn setup flag %u variant %u parts %x states %d groups %x %x %x %x", flag,
         FIELD(uint8_t, self, EN_VARIANT), (uint32_t)pm, pm ? FIELD(int32_t, pm, 0x68) : 0,
         FIELD(uint32_t, self, EN_GROUP_VIS), FIELD(uint32_t, self, EN_GROUP_VIS + 4),
         FIELD(uint32_t, self, EN_GROUP_VIS + 8), FIELD(uint32_t, self, EN_GROUP_VIS + 12));
}

/* object slot 5: getDTI */
static MtDTI *em090_get_dti(void *self)
{
    (void)self;
    return &g_em090_dti;
}

void em090_register_class(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uFestaEnemy;
    for (int i = 0; i < 2 + VT_uFestaEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + SLOT_DTOR_DELETE] = (uint32_t)&em090_delete;
    s_vt[2 + SLOT_GET_DTI] = (uint32_t)&em090_get_dti;
    s_vt[2 + SLOT_ACTION] = (uint32_t)&em090_action;
    s_vt[2 + SLOT_SPAWN_SETUP] = (uint32_t)&em090_spawn_setup;
    s_vt[2 + SLOT_THINK_BLOCKED] = (uint32_t)&dala_think_blocked;
    s_vt[2 + SLOT_STATE_FRAME] = (uint32_t)&em090_state_frame;
    s_vt[2 + SLOT_ACTION_START] = (uint32_t)&em090_action_start;
    s_vt[2 + SLOT_AI_COND] = (uint32_t)&em090_cond;
    s_vt[2 + SLOT_END] = (uint32_t)&dala_end_slot;
    s_vt[2 + SLOT_WALK] = (uint32_t)&dala_walk_frame;
    s_vt[2 + SLOT_MOTION_FRAME] = (uint32_t)&dala_parts_frame;
    s_vt[2 + SLOT_PAINT] = (uint32_t)&dala_paint;
    s_vt[2 + SLOT_CARVE] = (uint32_t)&dala_carve_point;
    s_vt[2 + SLOT_PSL_POST] = (uint32_t)&dala_psl_post;
    s_vt[2 + SLOT_HIT_LANDED] = (uint32_t)&dala_hit_landed;
    s_vt[2 + SLOT_HIT_OK] = (uint32_t)&dala_hit_ok;
    s_vt[2 + SLOT_BREAK_FLINCH] = (uint32_t)&dala_break_flinch;
    s_vt[2 + SLOT_PART_OK] = (uint32_t)&dala_part_ok;
    s_vt[2 + SLOT_DEATH_KIND] = (uint32_t)&dala_death_kind_ok;
    s_vt[2 + DALA_SLOT_NET_GET] = (uint32_t)&dala_shah_net_get;   /* 4U slots 78 / 79 (Shah's crimson bytes) */
    s_vt[2 + DALA_SLOT_NET_SET] = (uint32_t)&dala_shah_net_set;
    dala_bgm_register();               /* both variants' theme (core module/bgm.c) */

    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uEm001_00;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&em090_new_instance;

    MtDTI_ctor(&g_em090_dti, "uEm090_00", DTI_uFestaEnemy, DALA_SIZE, 0, 0, 0);
    g_em090_dti.w[0] = (uint32_t)&s_dti_vt[2];
    logf("dalaport: uEm090_00 DTI %x id %x size %x", (uint32_t)&g_em090_dti, g_em090_dti.w[7], DALA_SIZE);
}
