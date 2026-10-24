/* em089_pile.c: the fallen Dragonator spear (notes/port-checklist.md "Falling Dragonator spear").
 *
 * 4U (C, static trace; spec + port in em089_pile_port.c): severing part 1 (the Dragonator spear in the back) launches
 * em089 cut object 1 (type 3, emd word 36 record: 160 fall frames, gravity -0.45) from joint 200; it lands, and one
 * frame later registers an interaction record of kind 36 (0x926044). A hunter's switch press there (player action
 * 172 = switch action type 7 -> 0x5ba3cc -> 0x6a1f18) sets stage flag +0xdd29 bit 1 once and spawns uShell022 kind 10
 * owned by that hunter. The flag runs the hidden m19 uStageGimmick type 2 sub 3 ("pile": spin-up, thrust 180, hold),
 * whose matrix the spear copies into its joint 2; the shell hits 4 times with the arena Dragonator record (sphere 500
 * on the pile tip); then the spear explodes, collapses, sinks and is hidden for good.
 * GU port:
 *  - object: GU cut slot 1 (manifest field 2 = em089_gekiryusou; setup 0xb9fb4 types it 2), spawned with
 *    spawnCutPart(this, 1, 0, 200, 0). Type 2 sets detached bit 2 and reward flag 6; 4U's type 3 sets bit 8 and
 *    reward flag 8, a no-op in 4U 0x6a8920 -> flag 6 is pre-set around the call (0x9d458 skips a set flag), bit 8
 *    is set by em089_break.c as before (visibility rows).
 *  - motion: the object gets a copy of GU's cut-object vtable whose move (slot 10, 0x74e4c -> 0x7383c = Capcom's port
 *    of 4U slot 10 0xc2f9e8 -> 0xc2d364, without its em89 branches) runs the 4U port instead; draw flag +0xc bit 11
 *    as GU 0x7506c / 4U 0xc2fabc (detached, in the player's area, not hidden).
 *  - prompt: GU has no kind 36 -> a kind-11 record (the Dragonator switch prompt and switch action) at the landing
 *    point, routed by stage_cannon.c's ready / fire hooks.
 *  - hit: uShellEm089Pile (uShellEnemy class as em089_shell005.c) with HDS entry 25 / HTS group 15 (4U uShell022 kind
 *    10 record and volume, tools/build_em089_arc.py), armed with 4U's own (2, 8) = GU's player-shell side; spawned
 *    only on the pressing hunter's machine (4U: the shell belongs to that hunter).
 *  - effects / sounds: PEL 6200 + k (em089_024, element mask 1 << k), em089 request ids as in 4U.
 * Deviations: kind-11 prompt and player motion (GU's Dragonator switch) instead of 4U's kind 36 / motion 0x20f; the
 * hit shell is owned by the monster (GU uShellEnemy), not by the hunter. */
#include "game.h"
#include "util.h"
#include "em089_break.h"
#include "em089_efx.h"
#include "em089_snd.h"
#include "em089_pile.h"
#include "em089_pile_port.h"

/* ---- GU cut object (embedded in the enemy: this + 0x7720 + k * 0x14f0) ---- */
#define CUT1_OFF         0x8c10u
#define CUT_FLAGS        0xcu      /* unit flags: bit 11 = drawn (GU 0x750c0, 4U obj+4 bit 0x800) */
#define CUT_DT           28u       /* unit time scale */
#define CUT_POS          0x40u
#define CUT_QUAT         0x50u     /* x, y, z, w (GU 0x73d1c) */
#define CUT_SCALE        0x60u     /* x, y, z, 0 (GU 0x73a20) */
#define CUT_GROUPS       0x110u    /* uModel mesh-group display bits, word 0 (4U uModel+0x108; GU 0x89079c) */
#define REC_GROUND_Y     0x5b4u    /* enemy record: ground height under the monster [4U W+0x624] (em089_shell005.c) */
#define CUT_AREA         0x1054u
#define CUT_INIT         0x139cu   /* u8 1 after the init 0x736b8 (4U obj+0xd2c) */
#define CUT_TYPE         0x1474u   /* u8 1 / 2 / 3 (setup 0xb9f4c / 0xb9fc0 / 0xba030) */
#define CUT_BIT          2u        /* rec+0x3b4 bit of type 2 (spawnCutPart 0xc2378) */
#define REWARD_FLAG      6u        /* 0x9d458 flag of type 2 */
#define VT_CUT           MAIN(0x17345e8)   /* GU cut-object vtable address point: 82 slots, no RTTI */
#define VT_CUT_SLOTS     82
#define SLOT_CUT_MOVE    10
#define cutMoveGU        FN(shell_fn_t, 0x74e4c)
typedef void (*shell_fn_t)(void *self);
/* GU's slot 10 ends by rebuilding the drawn matrices (0x75020..0x75038): world matrix from pos / quat / scale
 * (0x94e224 = slot 19), joint matrices (0x94e250 = slot 20), then slot 24 (0x88f62c). Without them the spear kept
 * its spawn matrix: flat, wrong size, stale joint positions (test 2026-10-20 17:34). */
#define cutWorldMatrix   FN(shell_fn_t, 0x94e224)
#define cutJointMatrices FN(shell_fn_t, 0x94e250)
#define SLOT_CUT_AFTER   24
typedef void (*mat_quat_t)(float *q, const float *m);
#define matToQuat        FN(mat_quat_t, 0x72ea8)   /* row-vector matrix -> quaternion (0x72438's body) */
typedef void (*joint_set_t)(void *model, uint32_t joint, const float *mtx);
#define joint_set        FN(joint_set_t, 0x72438)
typedef uint32_t (*area_t)(void);
#define playerArea       FN(area_t, 0x4971c)       /* the local hunter's area (0x75084 / 0xc2508) */
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment       FN(map_segment_t, 0x1838fc)
#define COL_MGR          (*(void **)MAIN(0x21270e0))
typedef int (*is_local_t)(void *player);
#define is_local         FN(is_local_t, 0x27bcd0)

/* ---- GU interaction records (as stage_cannon.c) ---- */
#define INTER_MGR        0x1889ec0u
typedef uint8_t *(*rec_alloc_t)(void *mgr);
#define rec_alloc        FN(rec_alloc_t, 0x31aa6c)
typedef void (*rec_area_t)(void *rec, uint32_t area);
#define rec_area         FN(rec_area_t, 0x3191a0)
typedef void (*rec_flag_t)(void *rec, uint32_t v);
#define rec_flag         FN(rec_flag_t, 0x3191d8)
typedef void (*rec_reg_t)(void *mgr, void *rec, uint32_t z);
#define rec_register     FN(rec_reg_t, 0x31abac)
typedef void (*rec_free_t)(void *mgr, void *rec);
#define rec_free         FN(rec_free_t, 0x31aaf4)
#define KIND_SWITCH      11u

static uint32_t s_cut_vt[2 + VT_CUT_SLOTS];
static struct {
    void *self, *obj;
    uint8_t live;
    uint8_t pending;           /* a remote press arrived before our spear landed */
    float ground;              /* last ground height found (pj_ground_y) */
    uint32_t rays;
    int32_t clock;             /* clock_dt of the spear */
    struct { void *h; float left; } efx[6];   /* em089_024 posts stopped after a time (see pj_efx) */
    uint8_t *rec;              /* kind-11 record (4U kind 36, 0x926044) */
    float rec_pos[3], rec_r;
    void *shell;               /* our hit shell (4U uShell022 kind 10) */
    uint32_t logs;
    pile_t p;
} s_pl;

static uint8_t *rec_of(void *self) { return FIELD(uint8_t *, self, EN_RECORD); }

/* 4U frames (30 per second) since the last call with this `last`: the quest countdown sQuest+0x1c runs at the target
 * fps [[0x2126764]+56] (stage_cannon.c; its cooldowns matched the wall clock, test 2026-10-20 17:34). Test 17:34 also
 * showed the unit time field +28 advancing the spear and the hit shell 1.0 per 60 Hz tick, i.e. twice 4U's speed;
 * this clock is real time and gives 0 to a second call in the same frame. */
#define GAME_PTR         0x2126764u
#define SQUEST_PTR       0x188ad90u
static float clock_dt(int32_t *last)
{
    uint8_t *q = *(uint8_t **)MAIN(SQUEST_PTR), *g = *(uint8_t **)MAIN(GAME_PTR);
    if (!q || !g) return 0.0f;
    int32_t r = (int32_t)FIELD(uint32_t, q, 0x1c);
    float fps = FIELD(float, g, 56), dt = 0.0f;
    if (*last && fps > 1.0f) dt = (float)(*last - r) * 30.0f / fps;
    *last = r ? r : -1;
    return dt < 0.0f ? 0.0f : dt > 4.0f ? 4.0f : dt;
}

static void zero(void *p, uint32_t n) { for (uint32_t i = 0; i < n; i++) ((uint8_t *)p)[i] = 0; }

/* ------------------------------------------------------------------ pj_* (the port's GU side) */

float pj_sin(float rad) { return sinf_gu(rad); }
float pj_cos(float rad) { return cosf_gu(rad); }
float pj_sqrt(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));   /* -fno-builtin: no libm */
    return r;
}

/* joint local matrix (row vectors, translation in row 3) from the joint's quaternion +96 and translation +0x80, the
 * inverse of 0x72ea8 (x = (m12 - m21) / 4w ...) = 4U 0xb052ec */
void pj_joint_get_local(void *obj, int joint, float m[16])
{
    for (int i = 0; i < 16; i++) m[i] = (i % 5) ? 0.0f : 1.0f;
    uint8_t *ids = FIELD(uint8_t *, obj, 0x498), *joints = FIELD(uint8_t *, obj, 0x494);
    if (!ids || !joints || joint < 0 || ids[joint] == 255) return;
    const float *q = (const float *)(joints + 160u * ids[joint] + 96);
    const float *t = (const float *)(joints + 160u * ids[joint] + 0x80);
    float x = q[0], y = q[1], z = q[2], w = q[3];
    m[0] = 1.0f - 2.0f * (y * y + z * z); m[1] = 2.0f * (x * y + z * w);        m[2] = 2.0f * (x * z - y * w);
    m[4] = 2.0f * (x * y - z * w);        m[5] = 1.0f - 2.0f * (x * x + z * z); m[6] = 2.0f * (y * z + x * w);
    m[8] = 2.0f * (x * z + y * w);        m[9] = 2.0f * (y * z - x * w);        m[10] = 1.0f - 2.0f * (x * x + y * y);
    m[12] = t[0]; m[13] = t[1]; m[14] = t[2];
}

void pj_joint_set_local(void *obj, int joint, const float m[16]) { joint_set(obj, (uint32_t)joint, m); }

void pj_joint_world_pos(void *obj, int joint, float out[3])
{
    float p[4];
    jointPos(obj, (uint32_t)joint, p);
    out[0] = p[0]; out[1] = p[1]; out[2] = p[2];
}

void pj_obj_set_world(void *obj, const float m[16])
{
    FIELD(float, obj, CUT_POS) = m[12];
    FIELD(float, obj, CUT_POS + 4) = m[13];
    FIELD(float, obj, CUT_POS + 8) = m[14];
    FIELD(float, obj, CUT_POS + 12) = 0.0f;
    matToQuat(&FIELD(float, obj, CUT_QUAT), m);
}

/* Ground below `from`. Test 2026-10-20 17:34: every top-down mapSegment missed and the port's ground follow then
 * raised the spear 20 * scale per frame. Now the lower point goes first, as em089_shell.c's working impact test
 * passes it, then the reverse; a miss answers the last ground found (first: the monster's ground rec+0x5b4 at the
 * sever, which is 4U's launch target), so the port never sees a miss. */
float pj_ground_y(const float from[3], float max_drop, int *hit)
{
    float lo[3] = {from[0], from[1] - (max_drop < 0.0f ? 5000.0f : max_drop), from[2]}, out[4] = {0, 0, 0, 0};
    void *col = COL_MGR;
    uint32_t area = s_pl.self ? FIELD(uint8_t, s_pl.self, CUT_AREA) : 0, r = 0;
    if (col) {
        r = mapSegment(col, lo, from, area, out, 0, 48, 192);
        if (!r) r = mapSegment(col, from, lo, area, out, 0, 48, 192);
    }
    if (r) s_pl.ground = out[1];
    if (++s_pl.rays <= 8 || (!r && s_pl.rays % 600 == 0))
        logf("gogport: em089 pile: ground ray at %d %d %d -> %s %d", (int32_t)from[0], (int32_t)from[1],
             (int32_t)from[2], r ? "hit" : "miss, last ground", (int32_t)s_pl.ground);
    if (hit) *hit = 1;
    return s_pl.ground;
}

void pj_se(int id, const float pos[3])
{
    if (s_pl.self) em089_snd_pos(s_pl.self, (uint32_t)id, pos, FIELD(uint8_t, s_pl.self, CUT_AREA));
}

/* PEL 6200 + k = em089_024 element mask 1 << k (tools/efl4u2gu.py extra_records). Root posts (masks 2 / 4) follow
 * the spear object (its attach model, vt slot 76); joint posts (masks 8 / 16, short bursts) are posted at the joint's
 * world position with the offset in the object frame (the joint frame is not exposed by GU's attach); world posts
 * (mask 1) take pos and the rotation in degrees. */
void *pj_efx(uint32_t mask, uint32_t flags, const float pos[3], const float rot_deg[3], int attach_joint,
             const float off[3])
{
    uint32_t k = 0;
    while (k < 5 && !(mask >> k & 1)) k++;
    if (k == 5 || !s_pl.self) return 0;
    void *h;
    if (attach_joint == PILE_ATTACH_ROOT) {
        h = em089_efx_post_on(s_pl.self, 6200 + k, s_pl.obj);
    } else {
        float p[3] = {pos[0], pos[1], pos[2]}, rot[3] = {0, 0, 0};
        if (rot_deg) { rot[0] = rot_deg[0]; rot[1] = rot_deg[1]; rot[2] = rot_deg[2]; }
        if (attach_joint >= 0) {
            float m[16];
            pile_obj_world(&s_pl.p, m, 0);
            if (off)
                for (int i = 0; i < 3; i++) p[i] += off[0] * m[i] + off[1] * m[4 + i] + off[2] * m[8 + i];
            rot[0] = (float)(s_pl.p.ang[0] & 0xffff) * (360.0f / 65536.0f);
            rot[1] = (float)(s_pl.p.ang[1] & 0xffff) * (360.0f / 65536.0f);
        } else if (off) {
            p[0] += off[0]; p[1] += off[1]; p[2] += off[2];
        }
        h = em089_efx_post_ex(s_pl.self, 6200 + k, p, rot, 0);
    }
    if (++s_pl.logs <= 60)
        logf("gogport: em089 pile: effect mask %u flags %x attach %d at %d %d %d -> %x", mask, flags, attach_joint,
             (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], (uint32_t)h);
    /* In 4U these em089_024 elements end by themselves (the controller even waits for the explosion's end before
     * the sink); converted, the landing dust and the explosion looped forever (test 2026-10-20 18:32: two permanent
     * effects, no sink). Graceful stop after a time (G: 4U's own lengths not decoded): dust / collapse 90 frames,
     * wobble flash 60, explosion 296 (the collapse length, after which 4U waits for it); the charge (mask 2) is
     * killed by the port at the explosion. */
    float life = mask == 1 ? 90.0f : mask == 4 ? 296.0f : mask == 8 ? 90.0f : mask == 16 ? 60.0f : 0.0f;
    for (int i = 0; h && life > 0.0f && i < 6; i++)
        if (!s_pl.efx[i].h) { s_pl.efx[i].h = h; s_pl.efx[i].left = life; break; }
    return h;
}

static void efx_timers(float dt)
{
    for (int i = 0; i < 6; i++) {
        void *h = s_pl.efx[i].h;
        if (!h || (s_pl.efx[i].left -= dt) > 0.0f) continue;
        if (em089_efx_alive(h)) { em089_efx_stop(h); logf("gogport: em089 pile: effect %x stopped (timed)", (uint32_t)h); }
        s_pl.efx[i].h = 0;
    }
}

int pj_efx_alive(void *h) { return em089_efx_alive(h); }
void pj_efx_kill(void *h) { em089_efx_kill(h); }

void pj_record_create(const float pos[3], float radius, float height)
{
    void *im = *(void **)MAIN(INTER_MGR);
    if (s_pl.rec || !im || !s_pl.self) return;
    uint8_t *r = rec_alloc(im);
    if (!r) { logf("gogport: em089 pile: no free interaction record"); return; }
    uint32_t area = FIELD(uint8_t, s_pl.self, CUT_AREA);
    FIELD(uint32_t, r, 0x60) = 4;
    rec_area(r, area);
    FIELD(uint16_t, r, 0x4e) = 0xffff;
    FIELD(uint16_t, r, 0x50) = 0xffff;
    /* in-range test 0x319278 (C): +0x44 = horizontal radius, +0x48 = height (|dy| < h / 2); swapped until 2026-10-24
     * (prompt out to 300 while near_pile matched 100 * scale + 60: a press in between fired GU's Dragonator) */
    FIELD(float, r, 0x48) = height;
    rec_flag(r, 0);
    FIELD(uint8_t, r, 0x56) = 0;
    FIELD(float, r, 0x44) = radius;
    FIELD(uint32_t, r, 0x64) = KIND_SWITCH;
    FIELD(uint8_t, r, 0x58) = (uint8_t)area;
    for (int i = 0; i < 3; i++) { FIELD(float, r, 4 + 4 * i) = pos[i]; s_pl.rec_pos[i] = pos[i]; }
    rec_register(im, r, 0);
    s_pl.rec = r;
    s_pl.rec_r = radius;
    logf("gogport: em089 pile: interaction record (kind 11 for 4U kind 36) at %d %d %d r %d area %u -> %x",
         (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], (int32_t)radius, area, (uint32_t)r);
}

static void free_record(void)
{
    void *im = *(void **)MAIN(INTER_MGR);
    uint8_t *r = s_pl.rec;
    if (im && r && FIELD(uint32_t, r, 0x64) == KIND_SWITCH && FIELD(float, r, 4) == s_pl.rec_pos[0]) rec_free(im, r);
    s_pl.rec = 0;
}

void pj_record_disable(void)
{
    if (s_pl.rec) logf("gogport: em089 pile: interaction record released");
    free_record();
}

/* ------------------------------------------------------------------ the hit: uShellEm089Pile (4U uShell022 kind 10) */

#define DTI_uShellEnemy      ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy       MAIN(0x175b268)
#define VT_uShellEnemy_SLOTS 83
#define DTIVT_uShellEnemy    MAIN(0x175b3bc)
#define SIZE_uShellEnemy     0x15d0u
#define uShellEnemy_ctor     FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor     FN(ctor_t, 0x43b488)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)
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
#define SH_DT            28
#define SH_ATK0_SCALE    0x13bc
#ifndef EM089_SHELL_FILE
#define EM089_SHELL_FILE 0x1071du
#endif
#define EM089_SHELL_ID   175u
#define HDS_PILE         25u      /* uShell022 kind 10 record (tools/build_em089_arc.py S022_PILE) */
/* 4U 0x102c998[10] = (4 hits, 8 frames), 0x102c754[10] = 195 (life), first hit after 158 (0xc764ec) */
#define PILE_HITS        4
#define PILE_INTERVAL    8.0f
#define PILE_FIRST       158.0f
#define PILE_LIFE        195.0f

#define S_STATE   (SIZE_uShellEnemy + 0x00)   /* u8 1 live, 2 done */
#define S_HITS    (SIZE_uShellEnemy + 0x01)   /* u8 hits left [+0x26d] */
#define S_TIMER   (SIZE_uShellEnemy + 0x04)   /* float [+0x278] */
#define S_NEXT    (SIZE_uShellEnemy + 0x08)   /* float interval countdown [+0x27c] */
#define S_CLOCK   (SIZE_uShellEnemy + 0x0c)   /* int32 clock_dt state */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x10)

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static void hit_place(void *self)
{
    float t[3];
    if (!s_pl.live) return;
    pile_tip(&s_pl.p, t);
    for (int i = 0; i < 3; i++) FIELD(float, self, SH_POS + 4 * i) = FIELD(float, self, SH_POS2 + 4 * i) = t[i];
}

static void hit_kill(void *self, const char *why)
{
    logf("gogport: em089 pile hit shell end: %s", why);
    FIELD(uint8_t, self, S_STATE) = 2;
    if (s_pl.shell == self) s_pl.shell = 0;
    VCALL0(self, SLOT_KILL);
}

/* slot 79: base setup + 4U init 0xc753c0 (hits 4, interval 8, position = the pile point 0x6c15d0) */
static int hit_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    FIELD(uint8_t, self, S_STATE) = 1;
    FIELD(uint8_t, self, S_HITS) = PILE_HITS;
    FIELD(float, self, S_TIMER) = 0.0f;
    FIELD(float, self, S_NEXT) = PILE_INTERVAL;
    hit_place(self);
    return 1;
}

/* slot 9 = 4U 0xc764ec: follow the pile point; after 158 frames one attack every 8 frames (4 in all); end at 195 */
static void hit_move(void *self)
{
    uShell_move(self);                        /* owner gone -> kill */
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    hit_place(self);
    float dt = clock_dt(&FIELD(int32_t, self, S_CLOCK));
    float *t = &FIELD(float, self, S_TIMER);
    *t += dt;                                 /* 4U: while the pile gimmick is enabled, i.e. always here */
    if (*t > PILE_FIRST && FIELD(uint8_t, self, S_HITS)) {
        float *n = &FIELD(float, self, S_NEXT);
        *n -= dt;
        if (*n <= 0.0f) {
            if (uShell_hasHitData(self) == 1) {
                typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
                arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
                arm(self, 0, HDS_PILE, -1, 2, 8, 0xffff, FIELD(float, self, SH_ATK0_SCALE));   /* 4U (2, 8) */
            }
            FIELD(uint8_t, self, S_HITS)--;
            *n += PILE_INTERVAL;
            /* diagnostic (test 18:32: no damage seen): where the monster is, and its HP, at each hit */
            uint8_t *mr = s_pl.self ? rec_of(s_pl.self) : 0;
            float dx = mr ? FIELD(float, mr, 0x40) - FIELD(float, self, SH_POS) : 0.0f;
            float dy = mr ? FIELD(float, mr, 0x44) - FIELD(float, self, SH_POS + 4) : 0.0f;
            float dz = mr ? FIELD(float, mr, 0x48) - FIELD(float, self, SH_POS + 8) : 0.0f;
            logf("gogport: em089 pile hit %u/%u at %d %d %d (t %d); monster at %d %d %d, %d from the tip, HP %d, "
                 "controller %u", PILE_HITS - FIELD(uint8_t, self, S_HITS), PILE_HITS,
                 (int32_t)FIELD(float, self, SH_POS), (int32_t)FIELD(float, self, SH_POS + 4),
                 (int32_t)FIELD(float, self, SH_POS + 8), (int32_t)*t, mr ? (int32_t)FIELD(float, mr, 0x40) : 0,
                 mr ? (int32_t)FIELD(float, mr, 0x44) : 0, mr ? (int32_t)FIELD(float, mr, 0x48) : 0,
                 (int32_t)pj_sqrt(dx * dx + dy * dy + dz * dz), mr ? FIELD(int32_t, mr, REC_HP) : 0,
                 s_pl.self ? FIELD(uint8_t, s_pl.self, EN_CONTROLLED) : 0u);
        }
    }
    if (*t >= PILE_LIFE) hit_kill(self, "life");
}

static void *hit_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static void hit_delete(void *self)
{
    if (s_pl.shell == self) s_pl.shell = 0;
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *hit_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void hit_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&hit_delete;
    s_vt[2 + 5] = (uint32_t)&hit_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&hit_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&hit_setup;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&hit_new;
    MtDTI_ctor(&s_dti, "uShellEm089Pile", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("gogport: uShellEm089Pile DTI %x id %x size %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE);
}

static void *hit_spawn(void *self)
{
    if (!s_registered) hit_register();
    uint8_t *mgr = SHELL_MGR;
    if (!mgr || !self) return 0;
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) return 0;
    float t[3];
    pile_tip(&s_pl.p, t);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = EM089_SHELL_ID;
    FIELD(void *, param, 0xc) = self;
    for (int i = 0; i < 3; i++) FIELD(float, param, 0x10 + 4 * i) = t[i];
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = hit_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    for (int i = 0; i < 3; i++) FIELD(float, shell, SH_POS + 4 * i) = t[i];
    uShell_setResource(shell, fileResource(0, EM089_SHELL_FILE));
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        logf("gogport: em089 pile hit shell setup failed");
        hit_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}

/* ------------------------------------------------------------------ the spear object */

static void activate(void *player, int local);

static void cut_matrices(void *obj)
{
    cutWorldMatrix(obj);
    cutJointMatrices(obj);
    VCALL0(obj, SLOT_CUT_AFTER);
}

/* object slot 10 of the spear (GU 0x74e4c replaced): the 4U port, then the draw flag (GU 0x7506c / 4U 0xc2fabc) */
static void cut_move(void *obj)
{
    if (!s_pl.live || obj != s_pl.obj) { cutMoveGU(obj); return; }
    uint8_t *rec = rec_of(s_pl.self);
    if (rec) pile_set_monster_yaw(&s_pl.p, (uint16_t)FIELD(uint32_t, rec, REC_YAW));   /* 4U reads it live */
    float dt = clock_dt(&s_pl.clock);
    if (dt > 0.0f) { pile_frame(&s_pl.p, obj, dt); efx_timers(dt); }
    cut_matrices(obj);
    if (s_pl.rec && s_pl.p.rec_live)                          /* 4U c2e3d4: the record follows the spear */
        for (int i = 0; i < 3; i++) FIELD(float, s_pl.rec, 4 + 4 * i) = s_pl.rec_pos[i] = s_pl.p.rec_pos[i];
    if (s_pl.pending && pile_ready(&s_pl.p)) { s_pl.pending = 0; activate(0, 0); }
    float sp[3];
    int se = pile_se_follow(&s_pl.p, sp);
    if (se) em089_snd_move(s_pl.self, (uint32_t)se, sp);       /* 4U 0x301074: SE 210 follows the falling spear */
    FIELD(uint32_t, obj, CUT_GROUPS) = s_pl.p.model_flags;     /* 4U uModel+0x108 word 0 = GU +0x110 */
    int vis = !pile_hidden(&s_pl.p) && FIELD(uint8_t, obj, CUT_INIT) && rec &&
              (FIELD(uint16_t, rec, BRK_REC_DETACHED) & CUT_BIT) && FIELD(uint8_t, obj, CUT_AREA) == playerArea();
    uint32_t f = FIELD(uint32_t, obj, CUT_FLAGS);
    FIELD(uint32_t, obj, CUT_FLAGS) = vis ? (f | 0x800u) : (f & ~0x800u);
}

/* 4U "·scale" = W+0x1b8 * W+0x1bc (0x911cb4) = GU 0xbe5d4, which GU's own cut setup (0x73a14) also writes into
 * the cut object's scale +0x60 */
typedef float (*scale_t)(void *self);
#define enemyScale       FN(scale_t, 0xbe5d4)

void em089_pile_sever(void *self)
{
    if (!self || (s_pl.live && s_pl.self == self)) return;
    void *obj = (uint8_t *)self + CUT1_OFF;
    uint8_t *rec = rec_of(self);
    if (!rec) return;
    if (FIELD(uint8_t, obj, CUT_TYPE) != 2) {
        static uint8_t s_once;
        if (!s_once) { s_once = 1; logf("gogport: em089 pile: cut slot 1 has type %u, not 2 (manifest field 2?)",
                                         FIELD(uint8_t, obj, CUT_TYPE)); }
        return;
    }
    if (!(FIELD(uint16_t, rec, BRK_REC_DETACHED) & CUT_BIT)) {
        uint8_t had = rec[BRK_REC_FLAGS] & (1u << REWARD_FLAG);
        rec[BRK_REC_FLAGS] |= 1u << REWARD_FLAG;            /* 0x9d458 skips a set flag: no reward (4U: none) */
        spawnCutPart(self, 1, 0, 200, 0);
        if (!had) rec[BRK_REC_FLAGS] &= (uint8_t)~(1u << REWARD_FLAG);
    }
    const uint32_t *base = (const uint32_t *)VT_CUT;
    for (int i = 0; i < 2 + VT_CUT_SLOTS; i++) s_cut_vt[i] = base[i - 2];
    s_cut_vt[2 + SLOT_CUT_MOVE] = (uint32_t)&cut_move;
    FIELD(uint32_t, obj, 0) = (uint32_t)&s_cut_vt[2];
    zero(&s_pl.p, sizeof s_pl.p);
    s_pl.self = self;
    s_pl.obj = obj;
    s_pl.rec = 0;
    s_pl.shell = 0;
    s_pl.pending = 0;
    float j[4], s = enemyScale(self);
    jointPos(self, 200, j);
    for (int i = 0; i < 3; i++) FIELD(float, obj, CUT_SCALE + 4 * i) = s;   /* GU 0x73a20 / 4U 0xc2d33c */
    FIELD(float, obj, CUT_SCALE + 12) = 0.0f;
    s_pl.ground = FIELD(float, rec, REC_GROUND_Y);         /* ground under the monster = 4U's landing target */
    s_pl.rays = 0;
    s_pl.clock = 0;
    zero(s_pl.efx, sizeof s_pl.efx);
    pile_init_ex(&s_pl.p, j, &FIELD(float, rec, REC_POS_X), (uint16_t)FIELD(uint32_t, rec, REC_YAW), s);
    s_pl.p.model_flags = FIELD(uint32_t, obj, CUT_GROUPS);   /* the port edits bits 1..4 of the live word */
    float m[16];
    pile_obj_world(&s_pl.p, m, 0);                         /* 4U draws the launch frame at the start position */
    pj_obj_set_world(obj, m);
    cut_matrices(obj);
    s_pl.live = 1;
    logf("gogport: em089 pile: spear launched from joint 200 (%d %d %d), scale %d/1000, groups %x, cut object %x, "
         "detached %x, flags %x", (int32_t)j[0], (int32_t)j[1], (int32_t)j[2], (int32_t)(s * 1000.0f),
         s_pl.p.model_flags, (uint32_t)obj, FIELD(uint16_t, rec, BRK_REC_DETACHED), (uint32_t)rec[BRK_REC_FLAGS]);
}

/* hunter within the record radius + extra of c (x / z), and within 500 in height (keeps the Dragonator switch ledge
 * out) */
static int near_pile(void *pl, const float *c, float extra)
{
    float p[4];
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, p);
    float dx = p[0] - c[0], dz = p[2] - c[2], r = 100.0f * s_pl.p.scale + extra;
    return dx * dx + dz * dz <= r * r && p[1] - c[1] < 500.0f && c[1] - p[1] < 500.0f;
}

int em089_pile_ready(void *hunter)
{
    if (!s_pl.live || !s_pl.rec || !near_pile(hunter, s_pl.rec_pos, 60.0f)) return -1;
    return pile_ready(&s_pl.p);
}

/* Online (GU, C): every machine tests hits on its own monster copy, but only the controlling machine (enemy+0x7420)
 * turns them into HP / part damage (0x97ddc returns elsewhere) and sends the result in its action messages. So the
 * hit shell is spawned on every machine for every press, local or replayed: the controller's copy deals the damage
 * once, the others show the hits. */
static void activate(void *player, int local)
{
    pile_activate(&s_pl.p);                                  /* 4U 0x6a1f18: +0xdd29 |= 2 (one shot) */
    if (!s_pl.shell) s_pl.shell = hit_spawn(s_pl.self);
    logf("gogport: em089 pile: ACTIVATED by %s hunter %x, hit shell %x", local ? "the local" : "a remote",
         (uint32_t)player, (uint32_t)s_pl.shell);
}

int em089_pile_fire(void *player, int remote)
{
    if (!s_pl.live || pile_hidden(&s_pl.p)) return 0;
    if (!remote) {
        if (!s_pl.rec || !near_pile(player, s_pl.rec_pos, 60.0f)) return 0;
        if (!pile_ready(&s_pl.p)) { logf("gogport: em089 pile: switch pressed but not ready"); return 1; }
        activate(player, 1);
        return 1;
    }
    /* another machine's press (the cannons were tried first): its spear may sit away from ours (each machine lands
     * its own copy from its own monster position), or ours may still fall. Wide radius; the height check keeps the
     * Dragonator switch ledge out. The controller must not drop it: its hit shell is the one that deals damage. */
    float tgt[3] = {s_pl.p.tgt[0], s_pl.p.tgt[1] - 20.0f * s_pl.p.scale, s_pl.p.tgt[2]};
    if (!near_pile(player, s_pl.rec ? s_pl.rec_pos : tgt, 1500.0f)) return 0;
    if (pile_ready(&s_pl.p)) activate(player, 0);
    else if (!s_pl.p.dd29) { s_pl.pending = 1; logf("gogport: em089 pile: remote press queued until our spear lands"); }
    return 1;
}

int em089_pile_hit_window(void) { return s_pl.shell != 0; }

void em089_pile_cleanup(void)
{
    if (s_pl.rec) { free_record(); logf("gogport: em089 pile: interaction record freed (stage cleanup)"); }
}

void em089_pile_forget(void *self)
{
    if (s_pl.self != self) return;
    free_record();
    uint32_t logs = s_pl.logs;
    zero(&s_pl, sizeof s_pl);
    s_pl.logs = logs;
}
