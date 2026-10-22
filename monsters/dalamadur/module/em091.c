/* uEm091_00 (Dalamadur / Shah Dalamadur, tail half = 4U uEm083): a new monster class derived from uFestaEnemy.
 * Goal D2: the 4U actions (follow table), action start, AI conditions and end slot (em091_act.c, dala.c,
 * dala_react.c). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"

MtDTI g_em091_dti;                                /* referenced by the registry class table (tables.S) */
static uint32_t s_dti_vt[2 + 3];                  /* 2 header words + 3 slots; address point = &s_dti_vt[2] */
static uint32_t s_vt[2 + VT_uFestaEnemy_SLOTS];   /* copy of uFestaEnemy's object vtable with our overrides */

void em091_action_start(void *self, uint32_t cat, uint32_t num);   /* em091_act.c */
int em091_cond(void *self, uint32_t id);

#define SLOT_END 247          /* = 4U slot 89 (vt+0x164), dala_end_slot */

static void *em091_ctor(void *self)
{
    uFestaEnemy_ctor(self);
    FIELD(uint32_t, self, 0) = (uint32_t)&s_vt[2];
    FIELD(uint32_t, self, EN_WORK) = FIELD(uint32_t, self, EN_RECORD) + 96;
    dala_fields_init(self);
    return self;
}

/* DTI slot 2 */
static void *em091_new_instance(MtDTI *dti)
{
    (void)dti;
    void *a = get_allocator(&g_em091_dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    void *mem = alloc(a, DALA_SIZE, 16, g_em091_dti.w[7]);
    logf("dalaport: uEm091_00 new_instance -> %x", (uint32_t)mem);
    return mem ? em091_ctor(mem) : 0;
}

/* object slot 1: deleting destructor */
static void em091_delete(void *self)
{
    dala_forget_half(self);
    dala_walk_release(self);
    uFestaEnemy_dtor(self);
    void *a = get_allocator(&g_em091_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

/* object slot 125: run the current action, per frame */
static void em091_action(void *self)
{
    em091_act_run(self);
    dala_ctl_log(self, "tail");
    dala_place_log(self);
}

/* object slot 118: spawn setup, as the head's (em090.c). 4U slot 39 0x89fe4c also: placement 0, walk set 1
 * (goal D4), work +0 = 0, target slot 0 = the head (0x9554c8 mode 4: goal D3), Shah state W+0x7a14 = 0, body
 * effect uEffect002 28 at joint 142 (0x89ffe0 -> 0xc0a9d4: dala_efx_body_spawn). */
static void em091_spawn_setup(void *self, uint32_t flag)
{
    void *pm = FIELD(void *, self, EN_PARTS_MGR);
    applyPartsState(self, 0);
    dala_state_frame(self);          /* no push before the first update (em090.c) */
    FIELD(float, REC(self), REC_POS_X + 4) = 0.0f;   /* 4U's spawn point y (em090.c) */
    dala_register_half(self, 1);
    MODE(self) = 0;
    setBattleState(self, 1);
    dala_efx_body_spawn(self, 1);    /* 4U order: after 0x91b158 */
    dala_walk_spawn(self);
    logf("dalaport: em091 spawn setup flag %u variant %u parts %x states %d groups %x %x %x %x", flag,
         FIELD(uint8_t, self, EN_VARIANT), (uint32_t)pm, pm ? FIELD(int32_t, pm, 0x68) : 0,
         FIELD(uint32_t, self, EN_GROUP_VIS), FIELD(uint32_t, self, EN_GROUP_VIS + 4),
         FIELD(uint32_t, self, EN_GROUP_VIS + 8), FIELD(uint32_t, self, EN_GROUP_VIS + 12));
}

/* object slot 5: getDTI */
static MtDTI *em091_get_dti(void *self)
{
    (void)self;
    return &g_em091_dti;
}

void em091_register_class(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uFestaEnemy;
    for (int i = 0; i < 2 + VT_uFestaEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + SLOT_DTOR_DELETE] = (uint32_t)&em091_delete;
    s_vt[2 + SLOT_GET_DTI] = (uint32_t)&em091_get_dti;
    s_vt[2 + SLOT_ACTION] = (uint32_t)&em091_action;
    s_vt[2 + SLOT_SPAWN_SETUP] = (uint32_t)&em091_spawn_setup;
    s_vt[2 + SLOT_THINK_BLOCKED] = (uint32_t)&dala_think_blocked;
    s_vt[2 + SLOT_STATE_FRAME] = (uint32_t)&em091_state_frame;
    s_vt[2 + SLOT_ACTION_START] = (uint32_t)&em091_action_start;
    s_vt[2 + SLOT_AI_COND] = (uint32_t)&em091_cond;
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

    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uEm001_00;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&em091_new_instance;

    MtDTI_ctor(&g_em091_dti, "uEm091_00", DTI_uFestaEnemy, DALA_SIZE, 0, 0, 0);
    g_em091_dti.w[0] = (uint32_t)&s_dti_vt[2];
    logf("dalaport: uEm091_00 DTI %x id %x size %x", (uint32_t)&g_em091_dti, g_em091_dti.w[7], DALA_SIZE);
}
