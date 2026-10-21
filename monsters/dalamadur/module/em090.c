/* uEm090_00 (Dalamadur / Shah Dalamadur, head half = 4U uEm024): a new monster class derived from uFestaEnemy.
 * Goal D1: registers, spawns with its tail half, shows its own mesh groups and holds the idle motion (AI off). */
#include "game.h"
#include "util.h"
#include "em090.h"

#define MOT_IDLE 1          /* 4U motion 1 (bank 0): idle, mode 0 body placement (class-study.md "Modes") */

MtDTI g_em090_dti;                                /* referenced by the registry class table (tables.S) */
static uint32_t s_dti_vt[2 + 3];                  /* 2 header words + 3 slots; address point = &s_dti_vt[2] */
static uint32_t s_vt[2 + VT_uFestaEnemy_SLOTS];   /* copy of uFestaEnemy's object vtable with our overrides */

static void *em090_ctor(void *self)
{
    uFestaEnemy_ctor(self);
    FIELD(uint32_t, self, 0) = (uint32_t)&s_vt[2];
    FIELD(uint32_t, self, EN_WORK) = FIELD(uint32_t, self, EN_RECORD) + 96;
    dala_fields_init(self);
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
    uFestaEnemy_dtor(self);
    void *a = get_allocator(&g_em090_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

/* object slot 125: run the current action, per frame */
static void em090_action(void *self)
{
    dala_idle(self, MOT_IDLE);
    dala_ctl_log(self, "head");
}

/* object slot 253: AI think blocked (goal D1: no AI) */
static int em090_think_blocked(void *self)
{
    (void)self;
    return 1;
}

/* object slot 118: spawn setup (from 0xb8c54, after every mesh group was set visible). The field-3 XFS of each half
 * holds its 4U spawn visibility in every state (tools/build_dalamadur_arc.py, 4U masks 0x76d5a0 / 0x89fe4c) */
static void em090_spawn_setup(void *self, uint32_t flag)
{
    void *pm = FIELD(void *, self, EN_PARTS_MGR);
    applyPartsState(self, 0);
    dala_state_frame(self);          /* no push before the first update (the setup cleared the flag, 0xb9d2c) */
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
    s_vt[2 + SLOT_THINK_BLOCKED] = (uint32_t)&em090_think_blocked;
    s_vt[2 + SLOT_STATE_FRAME] = (uint32_t)&dala_state_frame;

    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uEm001_00;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&em090_new_instance;

    MtDTI_ctor(&g_em090_dti, "uEm090_00", DTI_uFestaEnemy, DALA_SIZE, 0, 0, 0);
    g_em090_dti.w[0] = (uint32_t)&s_dti_vt[2];
    logf("dalaport: uEm090_00 DTI %x id %x size %x", (uint32_t)&g_em090_dti, g_em090_dti.w[7], DALA_SIZE);
}
