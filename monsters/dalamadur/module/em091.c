/* uEm091_00 (Dalamadur / Shah Dalamadur, tail half = 4U uEm083): a new monster class derived from uFestaEnemy.
 * Goal D1: registers, spawns with its head half, shows its own mesh groups and holds the idle motion (AI off). */
#include "game.h"
#include "util.h"
#include "em090.h"

#define MOT_IDLE 101        /* 4U motion 101 (bank 0): the head's idle + 100, as every tail motion (class-study.md) */

MtDTI g_em091_dti;                                /* referenced by the registry class table (tables.S) */
static uint32_t s_dti_vt[2 + 3];                  /* 2 header words + 3 slots; address point = &s_dti_vt[2] */
static uint32_t s_vt[2 + VT_uFestaEnemy_SLOTS];   /* copy of uFestaEnemy's object vtable with our overrides */

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
    uFestaEnemy_dtor(self);
    void *a = get_allocator(&g_em091_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

/* object slot 125: run the current action, per frame */
static void em091_action(void *self)
{
    dala_idle(self, MOT_IDLE);
    dala_ctl_log(self, "tail");
}

/* object slot 253: AI think blocked (goal D1: no AI) */
static int em091_think_blocked(void *self)
{
    (void)self;
    return 1;
}

/* object slot 118: spawn setup, as the head's (em090.c) */
static void em091_spawn_setup(void *self, uint32_t flag)
{
    void *pm = FIELD(void *, self, EN_PARTS_MGR);
    applyPartsState(self, 0);
    dala_state_frame(self);          /* no push before the first update (em090.c) */
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
    s_vt[2 + SLOT_THINK_BLOCKED] = (uint32_t)&em091_think_blocked;
    s_vt[2 + SLOT_STATE_FRAME] = (uint32_t)&dala_state_frame;

    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uEm001_00;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&em091_new_instance;

    MtDTI_ctor(&g_em091_dti, "uEm091_00", DTI_uFestaEnemy, DALA_SIZE, 0, 0, 0);
    g_em091_dti.w[0] = (uint32_t)&s_dti_vt[2];
    logf("dalaport: uEm091_00 DTI %x id %x size %x", (uint32_t)&g_em091_dti, g_em091_dti.w[7], DALA_SIZE);
}
