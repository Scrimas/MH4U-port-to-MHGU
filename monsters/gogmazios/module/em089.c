/* uEm089_00 (Gogmazios): a new monster class derived from uFestaEnemy.
 * Stage 1: inert monster (base behaviour), so the spawn path, files and registration can be tested. */
#include "game.h"
#include "util.h"
#include "em089.h"           /* its files: data file section FILE, served by module/port.c (file_id) */
#include "em089_tar.h"      /* tar material animations (tar agent) */
#include "em089_break.h"     /* part breaks, tail sever (break agent) */
#include "em089_snd.h"       /* code-triggered sounds (sound agent) */
#include "em089_efx.h"       /* effect posts, slot 75 (effects agent) */
#include "em089_pile.h"      /* the fallen Dragonator spear */

#define EM089_SIZE (SIZE_uFestaEnemy + 0x98)     /* base + our own fields (F_END in em089_act.c) */
/* our fields after the base object (0xcac0 = work pointer, set by the ctor): +4..+0x8f used by em089_act.c
 * (action bookkeeping, the em089 aim point / turn rate / latches / tar amounts / AI state of the 4U work struct) */

MtDTI g_em089_dti;                                /* referenced by the registry class table (tables.S) */
static uint32_t g_em089_dti_vt[2 + 3];                  /* 2 header words + 3 slots; address point = &g_em089_dti_vt[2] */
static uint32_t s_vt[2 + VT_uFestaEnemy_SLOTS];   /* copy of uFestaEnemy's object vtable with our overrides */

static void *em089_ctor(void *self)
{
    uFestaEnemy_ctor(self);
    FIELD(uint32_t, self, 0) = (uint32_t)&s_vt[2];
    FIELD(uint32_t, self, EN_WORK) = FIELD(uint32_t, self, EN_RECORD) + 96;
    em089_fields_init(self);
    em089_efx_forget(self);          /* review agent: a previous em089 at this address (quest retry) */
    return self;
}

/* object slot 119 (base bx lr, per frame from 0xadb3c) = 4U slot 40: per-frame state logic */
static void em089_slot119(void *self) { em089_state_update(self); }

/* object slot 129 (base bx lr, from setAction's bookkeeping 0x755b4 with (cat, num)) = 4U slot 47 */
static void em089_slot129(void *self, uint32_t cat, uint32_t num) { em089_action_start(self, cat, num); }

/* object slot 127 (base bx lr; setAction 0x76154 calls it in a loop with (&cat, &num) until stable) = 4U slot 46 */
#define SLOT_ACTION_REMAP 127
static void em089_slot127(void *self, uint8_t *cat, uint8_t *num) { em089_action_remap(self, cat, num); }

/* object slot 130 (base return 0; per frame from the enemy update 0xae830, result unused) = 4U slot 48 */
#define SLOT_MOTION_FRAME 130
static int em089_slot130(void *self) { return em089_motion_frame(self); }

/* object slot 132 (base bx lr, per frame from 0xae42c; em049 drives its material animations here) = 4U slot 50
 * [0x8c8da0, per-part material loop]: tar material animations (em089_tar.c) */
static void em089_slot132(void *self)
{
    em089_tar_steady(self, em089_tar_update(self));
    em089_break_update(self);        /* after the tar code: tar_vis rewrites break/sever group bits */
    em089_snd_tick(self, FIELD(float, self, EN_DT));   /* delayed splash sounds (sound 220) */
}

/* object slots 171 / 172 (base 0xb17d8 / 0xb17f4) = 4U slots 78 / 79: em089's bytes in the network action message
 * (em089_act.c em089_net_get / em089_net_set) */
#define SLOT_NET_GET 171
#define SLOT_NET_SET 172

/* object slot 133 (base 0x6bf2c = 0; called by the AI opcode 0x6f through 0x81ff8 with the condition id) = 4U slot 51 */
static int em089_slot133(void *self, uint32_t id) { return em089_cond(self, id); }

/* DTI slot 2 */
static void *em089_new_instance(MtDTI *dti)
{
    (void)dti;
    void *a = get_allocator(&g_em089_dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    void *mem = alloc(a, EM089_SIZE, 16, g_em089_dti.w[7]);
    logf("gogport: uEm089_00 new_instance -> %x", (uint32_t)mem);
    return mem ? em089_ctor(mem) : 0;
}

/* object slot 1: deleting destructor */
static void em089_delete(void *self)
{
    em089_efx_forget(self);          /* review agent: no stale effect handles keyed to this address */
    em089_pile_forget(self);         /* the fallen spear's state / record */
    uFestaEnemy_dtor(self);
    void *a = get_allocator(&g_em089_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

/* object slot 125: run the current action, per frame (action framework in em089_act.c) */
static void em089_action(void *self)
{
#ifdef NO_MOTION
    (void)self;
    return;   /* diagnostic: keep the bind pose (skinning check) */
#else
    em089_act_run(self);
#endif
}

/* object slot 118: spawn setup (from 0xb8c54, after every mesh group was set visible). Apply the spawn visibility of
 * the field-3 XFS, as each GU monster does itself (Rathian @0xcf5a18). Without it every group is drawn, including
 * the 4U alternates (tar chest 4 / 22, the broken-part and severed-tail pieces) on top of each other.
 * State layout = tools/emdata4u.partsvis (Kushala's): 0 base, 2..4 break parts intact, 5 tail intact
 * (7..9 / 10 broken / severed, unused until breaks are ported). The base comes from the 4U cond-7 rows, i.e. the
 * tar state word W+0x7814 that 4U slot 39 sets at spawn [0x8b9dc0..0x8b9e0c: 0x8c69b8(this, mode, part) =
 * part 0, 7 mode 1; parts 2, 3, 6 mode 0 -> 0x7c]. */
#define XFS_BASE         0
#define XFS_INTACT_FIRST 2
#define XFS_TAIL_INTACT  5
static void em089_spawn_setup(void *self, uint32_t flag)
{
    void *pm = FIELD(void *, self, EN_PARTS_MGR);
    int32_t n = pm ? FIELD(int32_t, pm, 0x68) : 0;
    applyPartsState(self, XFS_BASE);
    for (int32_t s = XFS_INTACT_FIRST; s <= XFS_TAIL_INTACT; s++) applyPartsState(self, s);
    em089_tar_machine_spawn(self);   /* 4U slot 39 tar part: amounts, modes, hitzones, W+0x7814 -> group bits */
    logf("gogport: em089 spawn setup flag %u parts %x states %d groups %x %x %x %x", flag, (uint32_t)pm, n,
         FIELD(uint32_t, self, 0x110), FIELD(uint32_t, self, 0x114), FIELD(uint32_t, self, 0x118),
         FIELD(uint32_t, self, 0x11c));
    em089_tar_spawn(self);
    em089_break_spawn(self);
}

/* object slot 5: getDTI */
static MtDTI *em089_get_dti(void *self)
{
    (void)self;
    return &g_em089_dti;
}

MtDTI *em089_dti(void) { return &g_em089_dti; }

void *em089_create_object(void) { return em089_new_instance(&g_em089_dti); }

void em089_register_class(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uFestaEnemy;
    for (int i = 0; i < 2 + VT_uFestaEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + SLOT_DTOR_DELETE] = (uint32_t)&em089_delete;
    s_vt[2 + SLOT_GET_DTI] = (uint32_t)&em089_get_dti;
    s_vt[2 + SLOT_ACTION] = (uint32_t)&em089_action;
    s_vt[2 + SLOT_SPAWN_SETUP] = (uint32_t)&em089_spawn_setup;
    s_vt[2 + SLOT_THINK_BLOCKED] = (uint32_t)&em089_think_blocked;
    s_vt[2 + SLOT_STATE_FRAME] = (uint32_t)&em089_slot119;
    s_vt[2 + SLOT_ACTION_START] = (uint32_t)&em089_slot129;
    s_vt[2 + SLOT_ACTION_REMAP] = (uint32_t)&em089_slot127;
    s_vt[2 + SLOT_MOTION_FRAME] = (uint32_t)&em089_slot130;
    s_vt[2 + SLOT_PARTS_FRAME] = (uint32_t)&em089_slot132;
    s_vt[2 + SLOT_AI_COND] = (uint32_t)&em089_slot133;
    s_vt[2 + SLOT_NET_GET] = (uint32_t)&em089_net_get;
    s_vt[2 + SLOT_NET_SET] = (uint32_t)&em089_net_set;
    s_vt[2 + 168] = (uint32_t)&em089_slot75;   /* 4U slot 75 joint-200 drive (em089_efx.c), while part 1 count == 1 */
    s_vt[2 + 149] = (uint32_t)&em089_drop_set; /* item-drop table set (4U 0x930bdc em 89: work+0xed), em089_act.c */
    em089_efx_init();                          /* uShell016 effect hook (also installed lazily per frame) */

    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uEm001_00;
    for (int i = 0; i < 2 + 3; i++) g_em089_dti_vt[i] = base_dvt[i - 2];
    g_em089_dti_vt[2 + 2] = (uint32_t)&em089_new_instance;

    MtDTI_ctor(&g_em089_dti, "uEm089_00", DTI_uFestaEnemy, EM089_SIZE, 0, 0, 0);
    g_em089_dti.w[0] = (uint32_t)&g_em089_dti_vt[2];
    logf("gogport: uEm089_00 DTI %x id %x size %x", (uint32_t)&g_em089_dti, g_em089_dti.w[7], EM089_SIZE);
}
