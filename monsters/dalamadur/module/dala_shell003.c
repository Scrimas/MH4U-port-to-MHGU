/* dala_shell003.c: Dalamadur's blasts (goal D5): literal translations of
 *  (A) 4U uShell003 (type 3 of the poster 0x660e88, request 0x663220 -> 0x661c5c; 696 B, vtable 0xe6d3dc: ctor
 *      0xc55b10, slot 22 init 0xc544d0, slot 23 per frame 0xc54b04, slot 24 kill 0xc5598c) for the subtypes
 *      Dalamadur's shells post: 113 / 126 (meteor kinds 2, 3 / 4), Shah 160 / 162 (5, 6 / 7), 114 / 161 (fireball
 *      impacts), 112 / 159 (posted by the burn sequence below);
 *  (B) 4U uShell009 (type 9 via 0x661ea0; 648 B, vtable 0xe6d67c: ctor 0xc5f188, init 0xc5edc8, per frame
 *      0xc5ee0c, kill 0xc5f184 = base) subtypes 1 / 2: the raging fireball's ground burn, a timed list of uShell003
 *      posts;
 * as GU uShellEnemy subclasses (dala_shell.c). C = read in code, S = strong, G = guess.
 *
 * uShell003 (C): request from 0x663220 {owner, 1, subtype, flags +6 = 0, &pos, &zero angles, area, 255, group,
 * flags +0x14 = 0, scale 1.0, ...}; init: state 1, age +316 = 0, attack 0x9ab120(records 0x101f230 + 40 * subtype,
 * volumes 0x101efbc, subtype, 0x101ddcc[2 sub + 1] = 31, [2 sub] = 2), request group (unless 0xffff) to the slot;
 * our subtypes take the switch default: effect 0xc5540c (table 0x101dfcc[sub] {group, element, mask}, scale
 * 0x1021a08[sub], at the position, angles 0), sound 0xc54f48 (table 0x101e7c4[sub]: -1 for all ours), 0xc55034
 * (power / flag changes, all gated on request flags +0x14 = 0: nothing). Per frame: age += dt; state 2 (end) when
 * the attack slot's active byte (+0x16d) is 0 or age >= 200 (0xc54b88); the active byte drops at the record's window
 * end (start s16 +0, length s16 +2), here taken from the records (GU's own clearing of slot +5 not traced, as
 * Gogmazios' em089_shell005.c). Kill 0xc5598c releases the effect +0x29c (0xc470dc) -> dala_efx_stop.
 * Records (power / window / volume): 112 = 159: 100, 4 + 20, sphere bone 255 r 450; 113 = 160: 45, 4 + 10, r 450;
 * 114 = 161: 80, 4 + 20, r 700; 126 = 162: 50, 4 + 10, r 450 (all type 2; byte 0x1c = 29, see the build).
 * Effects: 112 / 159 em024_001 / em110_001 mask 1, scale 1.5; 113 / 126 / 160 / 162 em024_005 / em110_005 (group 35 /
 * 81 element 4), scale 1.2; 114 / 161 none.
 *
 * uShell009 (C): ctor: subtype, position, angles (request +32), area (+0x2e), group (+44 -> +0x27e); init: subtype
 * >= 5 dies; list 0x1026afc[sub] of 20-B steps {f32 time, u8 skip, u8 uShell003 subtype, -, f32 offset x, y, z}
 * (sub 1: 112 at 0 / 25 / 40 / 55, sub 2: 159 at the same times, then time -1). Per frame: owner gone -> dead;
 * step time < 0 -> end; age += dt, > 300 -> end; once age passes the step's time: offset turned by the yaw +0x114
 * (0xaad5b0), for 1 / 2 the ground under it (0x2b96e4 from y - 600 to y + 600 around the last post's height, mask
 * 16; no ground -> end, nothing posted), uShell003 there with the group, sound 0x1026950[sub] (255: none), next step.
 * One step per frame.
 * Multiplayer: no net test in either class (C); each machine runs its own copy from its own fireball / meteor. */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"
#include "dala_efx.h"

typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment           FN(map_segment_t, 0x1838fc)  /* = 4U 0x2b96e4 */
typedef uint32_t (*shell_flags_t)(void *self);
#define uShell_colFlags      FN(shell_flags_t, 0x4a2a8c)  /* = 4U 0x9aad8c */
typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)
#define uShell_kill          FN(shell_fn_t, 0x4a247c)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)
#define COL_MGR              (*(void **)MAIN(0x21270e0))
#define SLOT_KILL            16

#define VEC(p, off) (&FIELD(float, p, off))

/* ================================================================== (A) uShell003 ========================== */

#define B_SUB     (DALA_SH_FIELDS + 0x00)   /* u8 subtype [+0xfd] */
#define B_STATE   (DALA_SH_FIELDS + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define B_ARMED   (DALA_SH_FIELDS + 0x02)
#define B_AREA    (DALA_SH_FIELDS + 0x03)   /* u8 request area [+0x130] */
#define B_GROUP   (DALA_SH_FIELDS + 0x04)   /* u16 request group [+0x26e] */
#define B_SERIAL  (DALA_SH_FIELDS + 0x08)
#define B_AGE     (DALA_SH_FIELDS + 0x0c)   /* float [+316] */
#define B_END     (DALA_SH_FIELDS + 0x10)   /* float window end (record start + length) */
#define B_EFX     (DALA_SH_FIELDS + 0x14)   /* void * [+0x29c] */
#define B_START   (DALA_SH_FIELDS + 0x18)   /* float[3] request position */
#define B_SIZE    (DALA_SH_FIELDS + 0x30)

typedef struct { uint8_t sub, hds, shah; uint16_t efx; float end; } s003_t;
static const s003_t k_s003[] = {
    {112, DALA_HDS_S003_112, 0, DALA_EFX_BURN, 24.0f},  {159, DALA_HDS_S003_112, 1, DALA_EFX_BURN, 24.0f},
    {113, DALA_HDS_S003_113, 0, DALA_EFX_BLAST, 14.0f}, {160, DALA_HDS_S003_113, 1, DALA_EFX_BLAST, 14.0f},
    {114, DALA_HDS_S003_114, 0, 0, 24.0f},              {161, DALA_HDS_S003_114, 1, 0, 24.0f},
    {126, DALA_HDS_S003_126, 0, DALA_EFX_BLAST, 14.0f}, {162, DALA_HDS_S003_126, 1, DALA_EFX_BLAST, 14.0f},
};

static const s003_t *s003_info(uint32_t sub)
{
    for (uint32_t i = 0; i < sizeof k_s003 / sizeof k_s003[0]; i++)
        if (k_s003[i].sub == sub) return &k_s003[i];
    return 0;
}

static dala_shcls_t s_cls003;
static uint32_t s_serial003;

static void s003_end(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 40) logf("dalaport: blast %u sub %u end: %s", FIELD(uint32_t, self, B_SERIAL), FIELD(uint8_t, self, B_SUB),
                          why);
    FIELD(uint8_t, self, B_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 16 = 4U slot 24 0xc5598c: the effect is released, then the base kill */
static void s003_slot_kill(void *self)
{
    void *h = FIELD(void *, self, B_EFX);
    if (dala_efx_alive(h)) dala_efx_stop(h);
    FIELD(void *, self, B_EFX) = 0;
    uShell_kill(self);
}

/* slot 79: base set-up + init 0xc544d0 (default case) */
static int s003_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    const s003_t *k = s003_info(FIELD(uint8_t, self, B_SUB));
    FIELD(uint8_t, self, SH_AREA) = FIELD(uint8_t, self, B_AREA);
    float *pos = VEC(self, SH_POS), *st = VEC(self, B_START), *p2 = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) pos[i] = p2[i] = st[i];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, self, SH_ANGLES + 4 * i) = 0;   /* request angles = zero vector */
    FIELD(uint8_t, self, B_STATE) = 1;
    FIELD(float, self, B_AGE) = 0.0f;
    FIELD(float, self, B_END) = k->end;
    FIELD(uint8_t, self, B_ARMED) = (uint8_t)dala_shell_arm(self, k->hds, 31, 2, FIELD(uint16_t, self, B_GROUP));
    /* posted on this shell (4U 0xc5540c posts from the shell, C): a world-position post (dala_efx_post_at) leaves the
     * request's attach target empty, GU then attaches the owner's model and the blast showed at the head's origin,
     * one fixed arena point (test 2026-10-21); the record places once, here = the impact point */
    if (k->efx) FIELD(void *, self, B_EFX) = dala_efx_post_on(owner, k->efx, self);
    static uint32_t s_n;
    if (++s_n <= 40)
        logf("dalaport: blast %u spawn sub %u at %d %d %d area %u group %x hit %u efx %x", FIELD(uint32_t, self, B_SERIAL),
             k->sub, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], FIELD(uint8_t, self, SH_AREA),
             FIELD(uint16_t, self, B_GROUP), FIELD(uint8_t, self, B_ARMED), (uint32_t)FIELD(void *, self, B_EFX));
    return 1;
}

/* slot 9 = 4U slot 23 0xc54b04 */
static void s003_move(void *self)
{
    if (FIELD(void *, self, B_EFX) && !dala_efx_alive(FIELD(void *, self, B_EFX))) FIELD(void *, self, B_EFX) = 0;
    uShell_move(self);
    if (!dala_shell_live(self) || FIELD(uint8_t, self, B_STATE) != 1) return;
    float *age = &FIELD(float, self, B_AGE);
    *age += dala_shell_dt(self);
    if (*age >= FIELD(float, self, B_END)) { s003_end(self, "attack window over"); return; }
    if (*age >= 200.0f) s003_end(self, "age 200");
}

static void *s003_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls003); }
static MtDTI *s003_dti(void *self) { (void)self; return &s_cls003.dti; }

static void s003_delete(void *self)
{
    void *h = FIELD(void *, self, B_EFX);
    if (dala_efx_alive(h)) dala_efx_stop(h);
    FIELD(void *, self, B_EFX) = 0;
    dala_shell_free(&s_cls003, self);
}

void *dala_shell003_post(void *owner, uint32_t subtype, const float *pos, uint32_t area, uint32_t group)
{
    const s003_t *k = s003_info(subtype);
    if (!k || !pos) {
        static uint32_t s_n;
        if (++s_n <= 10) logf("dalaport: blast subtype %u is not Dalamadur's: dropped", subtype);
        return 0;
    }
    if (owner && k->shah != (FIELD(uint8_t, owner, EN_VARIANT) != 0)) {
        static uint32_t s_n;
        if (++s_n <= 5) logf("dalaport: blast subtype %u from variant %u: the PEL holds the variant's file", subtype,
                             FIELD(uint8_t, owner, EN_VARIANT));
    }
    if (!s_cls003.registered)
        dala_shell_register(&s_cls003, "uShellDala003", B_SIZE, s003_new, s003_delete, s003_dti, s003_move, s003_setup,
                            s003_slot_kill);
    void *param = dala_shell_param(owner, "blast");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls003);
    if (!shell) { dala_shell_param_free(param); return 0; }
    FIELD(uint8_t, shell, B_SUB) = (uint8_t)subtype;
    FIELD(uint8_t, shell, B_AREA) = (uint8_t)area;
    FIELD(uint16_t, shell, B_GROUP) = (uint16_t)group;
    float *st = VEC(shell, B_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    FIELD(uint32_t, shell, B_SERIAL) = ++s_serial003;
    return dala_shell_start(shell, param, "blast");
}

/* ================================================================== (B) uShell009 ========================== */

#define Q_SUB     (DALA_SH_FIELDS + 0x00)   /* u8 subtype [+0xfd] */
#define Q_STATE   (DALA_SH_FIELDS + 0x01)   /* u8 [+0xf1] */
#define Q_IDX     (DALA_SH_FIELDS + 0x02)   /* u8 step [+0x27c] */
#define Q_AREA    (DALA_SH_FIELDS + 0x03)   /* u8 [+0x130] */
#define Q_GROUP   (DALA_SH_FIELDS + 0x04)   /* u16 [+0x27e] */
#define Q_SERIAL  (DALA_SH_FIELDS + 0x08)
#define Q_AGE     (DALA_SH_FIELDS + 0x0c)   /* float [+316] */
#define Q_PREV    (DALA_SH_FIELDS + 0x10)   /* float[3] last post [+0x120] */
#define Q_START   (DALA_SH_FIELDS + 0x1c)   /* float[3] request position */
#define Q_ANG     (DALA_SH_FIELDS + 0x28)   /* u32[3] request angles (request +32) */
#define Q_SIZE    (DALA_SH_FIELDS + 0x40)

typedef struct { float t; uint8_t skip, sub3; float off[3]; } s009_step_t;
/* 0x1026afc[1] = 0x10269bc, [2] = 0x1026a20 (C) */
static const s009_step_t k_s009_1[] = {
    {0.0f, 0, 112, {0, 0, 0}}, {25.0f, 0, 112, {0, 0, 0}}, {40.0f, 0, 112, {0, 0, 0}}, {55.0f, 0, 112, {0, 0, 0}},
    {-1.0f, 255, 0, {0, 0, 0}},
};
static const s009_step_t k_s009_2[] = {
    {0.0f, 0, 159, {0, 0, 0}}, {25.0f, 0, 159, {0, 0, 0}}, {40.0f, 0, 159, {0, 0, 0}}, {55.0f, 0, 159, {0, 0, 0}},
    {-1.0f, 255, 0, {0, 0, 0}},
};

static dala_shcls_t s_cls009;
static uint32_t s_serial009;

static void s009_end(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 30) logf("dalaport: burn %u sub %u end after %u steps: %s", FIELD(uint32_t, self, Q_SERIAL),
                          FIELD(uint8_t, self, Q_SUB), FIELD(uint8_t, self, Q_IDX), why);
    FIELD(uint8_t, self, Q_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* 4U slot 23 0xc5ee0c after the owner test */
static void s009_step(void *self, void *owner)
{
    const s009_step_t *list = FIELD(uint8_t, self, Q_SUB) == 2 ? k_s009_2 : k_s009_1;
    const s009_step_t *e = &list[FIELD(uint8_t, self, Q_IDX)];
    if (e->t < 0.0f) { s009_end(self, "list end"); return; }
    float *age = &FIELD(float, self, Q_AGE);
    *age += dala_shell_dt(self);
    if (*age > 300.0f) { s009_end(self, "age 300"); return; }
    if (e->t >= *age) return;
    if (!e->skip) {
        float a = (float)(FIELD(uint32_t, self, SH_ANGLES + 4) & 0xffff) * (6.28318531f / 65536.0f);
        float s = sinf_gu(a), c = cosf_gu(a);
        const float *p = VEC(self, SH_POS);
        float q[4] = {p[0] + c * e->off[0] + s * e->off[2], p[1] + e->off[1], p[2] + c * e->off[2] - s * e->off[0], 0};
        float *prev = VEC(self, Q_PREV);
        float from[4] = {q[0], prev[1] - 600.0f, q[2], 0}, to[4] = {q[0], prev[1] + 600.0f, q[2], 0}, out[4] = {0};
        void *col = COL_MGR;
        uint32_t r = col ? mapSegment(col, from, to, FIELD(uint8_t, self, SH_AREA), out, 0, 16, uShell_colFlags(self)) : 0;
        if (!r) { s009_end(self, "no ground under the step"); return; }
        q[0] = out[0]; q[1] = out[1]; q[2] = out[2];
        dala_shell003_post(owner, e->sub3, q, FIELD(uint8_t, self, SH_AREA), FIELD(uint16_t, self, Q_GROUP));
        prev[0] = q[0]; prev[1] = q[1]; prev[2] = q[2];
    }
    FIELD(uint8_t, self, Q_IDX)++;
}

static int s009_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    FIELD(uint8_t, self, SH_AREA) = FIELD(uint8_t, self, Q_AREA);
    float *pos = VEC(self, SH_POS), *st = VEC(self, Q_START), *prev = VEC(self, Q_PREV), *p2 = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) pos[i] = prev[i] = p2[i] = st[i];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, self, SH_ANGLES + 4 * i) = FIELD(uint32_t, self, Q_ANG + 4 * i);
    FIELD(uint8_t, self, Q_IDX) = 0;
    FIELD(float, self, Q_AGE) = 0.0f;
    FIELD(uint8_t, self, Q_STATE) = 1;
    static uint32_t s_n;
    if (++s_n <= 30) logf("dalaport: burn %u spawn sub %u at %d %d %d", FIELD(uint32_t, self, Q_SERIAL),
                          FIELD(uint8_t, self, Q_SUB), (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2]);
    s009_step(self, FIELD(void *, param, 0xc));             /* the init's tail call of slot 23 */
    return 1;
}

static void s009_move(void *self)
{
    uShell_move(self);
    if (!dala_shell_live(self) || FIELD(uint8_t, self, Q_STATE) != 1) return;
    void *owner = dala_shell_owner(self);
    if (owner) s009_step(self, owner);
}

static void *s009_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls009); }
static MtDTI *s009_dti(void *self) { (void)self; return &s_cls009.dti; }
static void s009_delete(void *self) { dala_shell_free(&s_cls009, self); }

void *dala_shell009_post(void *owner, uint32_t subtype, const float *pos, uint32_t area, uint32_t group,
                         const uint32_t *angles)
{
    if ((subtype != 1 && subtype != 2) || !pos) return 0;  /* the init kills >= 5; 0 / 3 / 4 are not Dalamadur's */
    if (!s_cls009.registered)
        dala_shell_register(&s_cls009, "uShellDala009", Q_SIZE, s009_new, s009_delete, s009_dti, s009_move, s009_setup, 0);
    void *param = dala_shell_param(owner, "burn");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls009);
    if (!shell) { dala_shell_param_free(param); return 0; }
    FIELD(uint8_t, shell, Q_SUB) = (uint8_t)subtype;
    FIELD(uint8_t, shell, Q_AREA) = (uint8_t)area;
    FIELD(uint16_t, shell, Q_GROUP) = (uint16_t)group;
    float *st = VEC(shell, Q_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, shell, Q_ANG + 4 * i) = angles ? angles[i] : 0;
    FIELD(uint32_t, shell, Q_SERIAL) = ++s_serial009;
    return dala_shell_start(shell, param, "burn");
}
