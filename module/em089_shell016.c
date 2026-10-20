/* uShellEm089Atk: Gogmazios' breath / beam / explosion attack shells. Translation of MH4U uShell016 (type 16 of the
 * event poster 0x660e88, posted by 0x6620c4; 704 B, vtable 0xe6d98c: ctor 0xc6f900, slot 22 init 0xc69ddc, slot 23
 * per frame 0xc6ac64) for the subtypes em089 uses (36, 37, 41, 51-56), as a GU class derived from uShellEnemy, with
 * the same framework calls as em089_shell.c (own request instead of the 412-row shell table; notes/port-checklist.md
 * "Tar shells (shell agent)" and "Attack shells uShell016 (shell agent)").
 *
 * 4U behaviour ported:
 *  - ctor: joint P+0, offset P+8 (+0x270), length = event float +0x10 (+0x29c, 10000 at every em089 site), angles
 *    x = P+26 (+ owner x angle W+0x1a8 except 36), y = P+28 (+ owner yaw W+0x1ac except 36 / 53), owner motion at
 *    spawn (+0x2a0).
 *  - init: life +0x13c = table 0x102bbbc[subtype] (36 / 53: 120, 37: 128, 41: 150, 51: 260, 52 / 55 / 56: 680, 54:
 *    139), attack 0x9ab120(records 0x102b370 + 96, index table 0x102bad8[subtype], 31, 2) -> our HDS entries 4..9
 *    (shell family em089_00_shell00), uEffect002 post (hook em089_shell016_fx), 36 / 53 placed once (53: rotated
 *    by y too and flattened to the joint height).
 *  - per frame (37, 41, 51, 52, 54-56): placed at the joint every frame: second point = joint + M * offset, point =
 *    joint + M * rotX(x angle)(offset + (0, 0, length)), M = the joint's matrix (0x930894 = GU 0xc1660); 36 / 53
 *    stay where they were spawned. Common tail 0xc6e8d4: life -= owner motion step (0x94460c: owner +668 * dt), the
 *    shell ends when the owner's motion is not the spawn motion any more or the life is out; angles from the segment.
 *  - hit volume: every record uses a capsule on bone 1001 (4U volume table 0x102b370[byte 0x19]: 18 r 330, 20 r 70,
 *    22 r 30), which is the segment (point, second point) in both games: 4U +0x100 / +0x120, GU this+0x40 /
 *    this+0x1000 (GU 0x16e46c: bone 1001 -> capsule from +0x40 to +0x1000 for char-type owners).
 * Not ported (logged / noted): effects and sounds (0xc6e9b4: sound 209 at the point of the segment nearest to the
 * listener), the map segment tests of 41 / 51 / 52 / 54-56 and their uShell051 ground posts (subtype 15, explosions
 * along the ground for 51 at motion frames 242..), camera shakes 0xbfe98c, the one-time effect 53 of 41 / 54. */
#include "game.h"
#include "util.h"
#include "em089_shell016.h"
#include "em089_shell051.h"
#include "em089_snd.h"
#include "em089_efx.h"

/* ---- GU addresses (main offsets), as em089_shell.c ---- */
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
/* jointMtx(unit, joint, float out[16]): world matrix of a joint (unknown id -> joint 0) [4U 0x930894] (C) */
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx             FN(joint_mtx_t, 0xc1660)
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment           FN(map_segment_t, 0x1838fc)  /* = 4U 0x2b96e4 */
typedef float (*ground_y_t)(void *mgr, const float *pos, const float *ref, uint32_t area, uint8_t *hit, void *info,
                            uint32_t flags);
#define groundY              FN(ground_y_t, 0x183ad0)     /* = 4U 0x2bad24 (same argument list, returns y) */
typedef uint32_t (*shell_flags_t)(void *self);
#define uShell_colFlags      FN(shell_flags_t, 0x4a2a8c)  /* = 4U 0x9aad8c */
/* camera shake at a position: 4U 0xbfe98c(mgr, owner, id, pos) = GU 0x49eac(owner, id, pos, 0) (GU jointFx 0xc24d8
 * calls it after the same "owner in the player's area" test, with the player area from 0x4971c) */
typedef void (*cam_shake_pos_t)(void *owner, uint32_t id, const float *pos, uint32_t zero);
#define camShakePos          FN(cam_shake_pos_t, 0x49eac)
typedef uint32_t (*player_area_t)(void);
#define playerArea           FN(player_area_t, 0x4971c)
#define COL_MGR              (*(void **)MAIN(0x21270e0))
#define SH_AREA              0x1054
#define SH_DT                28
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
#define SH_POS           0x40     /* capsule point [4U +0x100] */
#define SH_POS2          0x1000   /* capsule second point [4U +0x120] */
#define SH_ANGLES        0xfe8
#define SH_ATK0_F14      0x13bc
#define REC_MOT_SPEED    0x398    /* owner motion speed multiplier (setMotionSpeed) */

#ifndef EM089_SHELL_FILE
#define EM089_SHELL_FILE 0x1071du /* shell\em\em089_00_shell00 (HDS entries 4..9 / HTS groups 1..3 = uShell016) */
#endif
#define EM089_SHELL_ID   175u

/* ---- our fields after the uShellEnemy object (4U uShell016 offset in brackets) ---- */
#define S_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define S_ARMED   (SIZE_uShellEnemy + 0x02)
#define S_JOINT   (SIZE_uShellEnemy + 0x04)   /* u32 [+0x2a4] */
#define S_OFF     (SIZE_uShellEnemy + 0x08)   /* float[3] [+0x270] */
#define S_LEN     (SIZE_uShellEnemy + 0x14)   /* float [+0x29c] */
#define S_XANG    (SIZE_uShellEnemy + 0x18)   /* u32 [+0x290] */
#define S_YANG    (SIZE_uShellEnemy + 0x1c)   /* u32 [+0x294] */
#define S_LIFE    (SIZE_uShellEnemy + 0x20)   /* float [+0x13c] */
#define S_MOTION  (SIZE_uShellEnemy + 0x24)   /* u32 owner motion at spawn [+0x2a0] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x28)
#define S_TIMER   (SIZE_uShellEnemy + 0x2c)   /* float ground-post timer [+696] */
#define S_POSTS   (SIZE_uShellEnemy + 0x30)   /* u32 posts / end-effect flag [+0x2bc] */
#define S_SND     (SIZE_uShellEnemy + 0x34)   /* u8 sound started [+0xf4] */
#define S_SND_T   (SIZE_uShellEnemy + 0x38)   /* float repeat timer of 202 [+688] */
#define S_HIT     (SIZE_uShellEnemy + 0x3c)   /* float[4] map hit point of the capsule (4U sp+704) */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x50)

void (*em089_shell016_fx)(void *shell, void *owner, uint32_t subtype, uint32_t efx_id);

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;
static uint32_t s_serial;

#define VEC(p, off) (&FIELD(float, p, off))

/* per subtype: life (0x102bbbc), HDS entry (4U record 0x102bad8[subtype] -> our entry), uEffect002 id, x angle
 * offset P+26, whether x / y add the owner's angles, 4U offset kind (0 = (0, 0, 0), 1 = (0, -50, 130)) */
typedef struct { uint8_t sub, hds, efx, off_kind; uint16_t xang, yang; float life; uint8_t add_x, add_y; } s016_t;
static const s016_t k_sub[] = {
    {36, 4, 48, 0, 0x1556, 0, 120.0f, 0, 0},   /* 4U record 31 */
    {37, 5, 50, 0, 0x1c00, 0, 128.0f, 1, 1},   /* record 32 */
    {41, 6, 53, 1, 0x1800, 0, 150.0f, 1, 1},   /* record 36 */
    {51, 7, 54, 1, 0x1800, 0, 260.0f, 1, 1},   /* record 40 */
    {52, 8, 53, 1, 0x1800, 0, 680.0f, 1, 1},   /* record 41 */
    {53, 4, 48, 0, 0, 0xf400, 120.0f, 1, 0},   /* record 31 */
    {54, 9, 53, 1, 0x1800, 0, 139.0f, 1, 1},   /* record 42 */
    {55, 8, 53, 1, 0x1800, 0, 680.0f, 1, 1},
    {56, 8, 53, 1, 0x1800, 0, 680.0f, 1, 1},
};

static const s016_t *sub_info(uint32_t sub)
{
    for (uint32_t i = 0; i < sizeof k_sub / sizeof k_sub[0]; i++)
        if (k_sub[i].sub == sub) return &k_sub[i];
    return 0;
}

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }
static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* place the capsule at the joint (4U 0xc6c904.. / 0xc6a720..). with_y: 53's extra y rotation + flattening. */
static void s016_place(void *self, void *owner, int with_y)
{
    uint32_t joint = FIELD(uint32_t, self, S_JOINT);
    float j[4], m[16];
    jointPos(owner, joint, j);
    jointMtx(owner, joint, m);
    const float *off = VEC(self, S_OFF);
    float v[3] = {off[0], off[1], off[2] + FIELD(float, self, S_LEN)};
    float s = sinf_gu(ang_rad(FIELD(uint32_t, self, S_XANG))), c = cosf_gu(ang_rad(FIELD(uint32_t, self, S_XANG)));
    float y = c * v[1] - s * v[2], z = s * v[1] + c * v[2];          /* 0xaad560: rotate (y, z) */
    v[1] = y; v[2] = z;
    if (with_y) {                                                     /* 0xaad5b0: rotate (x, z) */
        s = sinf_gu(ang_rad(FIELD(uint32_t, self, S_YANG))); c = cosf_gu(ang_rad(FIELD(uint32_t, self, S_YANG)));
        float x = c * v[0] + s * v[2];
        z = c * v[2] - s * v[0];
        v[0] = x; v[2] = z;
    }
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) {
        q[i] = j[i] + off[0] * m[i] + off[1] * m[4 + i] + off[2] * m[8 + i];
        p[i] = j[i] + v[0] * m[i] + v[1] * m[4 + i] + v[2] * m[8 + i];
    }
    if (with_y) p[1] = q[1];
}

/* angles from the segment (0xc6e944): y = atan2(dx, dz), x = atan2(-dy, horizontal) */
static void s016_orient(void *self)
{
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
    FIELD(uint32_t, self, SH_ANGLES + 4) = rad_ang(atan2f_gu(dx, dz));
    FIELD(uint32_t, self, SH_ANGLES) = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));
}

static void s016_kill(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 40) logf("gogport: em089 attack shell %u (sub %u) end: %s", FIELD(uint32_t, self, S_SERIAL),
                          FIELD(uint8_t, self, S_SUB), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    em089_efx_shell016_end(self);   /* effects agent: finish the attached effect with the shell (idempotent) */
    VCALL0(self, SLOT_KILL);
}

/* ---- per-frame extras of 41 / 51 / 52 / 54-56 and the sound (4U 0xc6c904.., 0xc6d250.., 0xc6e54c.., 0xc6e9b4) ---- */

static float owner_step(void *owner)   /* 4U 0x94460c: owner +668 * dt */
{
    return FIELD(float, FIELD(uint8_t *, owner, EN_RECORD), REC_MOT_SPEED) * FIELD(float, owner, EN_DT);
}

/* the capsule's map test (tip -> start, mask 16) into S_HIT; returns the 4U result word */
static uint32_t s016_map(void *self)
{
    void *col = COL_MGR;
    if (!col) return 0;
    return mapSegment(col, VEC(self, SH_POS), VEC(self, SH_POS2), FIELD(uint8_t, self, SH_AREA), VEC(self, S_HIT), 0,
                      16, uShell_colFlags(self));
}

/* ground post at the map hit point: y = ground height there (0x2bad24), uShell051 of subtype sub with our yaw */
static void s016_ground_post(void *self, void *owner, uint32_t sub)
{
    void *col = COL_MGR;
    float *h = VEC(self, S_HIT);
    if (col) h[1] = groundY(col, h, 0, FIELD(uint8_t, self, SH_AREA), 0, 0, uShell_colFlags(self));
    em089_shell051_post(owner, sub, h, FIELD(uint32_t, self, SH_ANGLES + 4));
}

/* camera shakes at the hit point at owner motion frames (0xbfe98c): first frame id 1, then every 10 frames id 7 */
static void s016_shakes(void *self, void *owner, uint32_t r, float last)
{
    if (!(r & 17) || FIELD(uint8_t, owner, SH_AREA) != playerArea()) return;
    for (float f = 242.0f; f <= last; f += 10.0f)
        if (motionCheck(owner, 0, 0, f, 0.0f)) camShakePos(owner, f == 242.0f ? 1 : 7, VEC(self, S_HIT), 0);
}

/* the end effect (41 / 54: id 53, 51: id 54, 52 / 55 / 56: id 53) once the life is down to 10 */
static void s016_end_fx(void *self, void *owner, uint32_t want, uint32_t efx)
{
    uint32_t *n = &FIELD(uint32_t, self, S_POSTS);
    if (FIELD(float, self, S_LIFE) > 10.0f || *n != want) return;
    *n = want + 1;
    if (em089_shell016_fx) em089_shell016_fx(self, owner, FIELD(uint8_t, self, S_SUB), efx);
}

/* 7/136 explosions (0xc6d4dc..): at owner frames, segment B -> A (mask 48) from owner-relative points scaled by
 * speedFactor, x mirrored for motion 0x266, rotated by the yaw, + owner position; a hit posts uShell051 9..12 */
static const struct { float frame, a[3], b[3]; uint8_t sub; } k_boom[] = {
    {473, {-92, 532, 440}, {210, -30, 530}, 9}, {483, {-340, 670, 277}, {-120, -30, 720}, 10},
    {488, {-439, 688, 168}, {-500, -30, 840}, 11}, {491, {-464, 761, 12}, {-890, -30, 780}, 12},
};
static void s016_booms(void *self, void *owner)
{
    void *col = COL_MGR;
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    for (uint32_t i = 0; i < sizeof k_boom / sizeof k_boom[0]; i++) {
        if (!motionCheck(owner, 0, 0, k_boom[i].frame, 0.0f) || !col) continue;
        float k = speedFactor(owner), mir = curMotion(owner) == 0x266 ? -1.0f : 1.0f;
        float y = ang_rad(FIELD(uint32_t, rec, REC_YAW)), s = sinf_gu(y), c = cosf_gu(y);
        float a[3], b[3], out[4] = {0, 0, 0, 0};
        const float *pa = k_boom[i].a, *pb = k_boom[i].b, *o = (const float *)(rec + REC_POS_X);
        float ax = pa[0] * k * mir, az = pa[2] * k, bx = pb[0] * k * mir, bz = pb[2] * k;
        a[0] = c * ax + s * az + o[0]; a[1] = pa[1] * k + o[1]; a[2] = c * az - s * ax + o[2];
        b[0] = c * bx + s * bz + o[0]; b[1] = pb[1] * k + o[1]; b[2] = c * bz - s * bx + o[2];
        uint32_t r = mapSegment(col, b, a, FIELD(uint8_t, self, SH_AREA), out, 0, 48, uShell_colFlags(self));
        if (r & 17) em089_shell051_post(owner, k_boom[i].sub, out, FIELD(uint32_t, self, SH_ANGLES + 4));
    }
}

static void s016_extras(void *self, void *owner, uint32_t sub)
{
    float *t = &FIELD(float, self, S_TIMER);
    uint32_t r = s016_map(self);
    *t -= owner_step(owner);
    if (*t < 0.0f) *t = 0.0f;
    switch (sub) {
    case 41: case 54:
        if (*t <= 0.0f && (r & 17)) { s016_ground_post(self, owner, 15); *t = 9999.0f; }
        s016_end_fx(self, owner, 0, 53);
        s016_shakes(self, owner, r, 362.0f);
        break;
    case 51:
        if (motionCheck(owner, 0, 0, 242.0f, 0.0f) && (r & 17)) s016_ground_post(self, owner, 3);
        s016_booms(self, owner);
        s016_end_fx(self, owner, 0, 54);
        s016_shakes(self, owner, r, 442.0f);
        break;
    case 52: case 55: case 56:
        if (*t <= 0.0f) {
            uint32_t *n = &FIELD(uint32_t, self, S_POSTS);
            if (*n) {
                if (r & 17) { s016_ground_post(self, owner, 14); *t = sub == 52 ? 24.0f : sub == 55 ? 25.0f : 26.0f; }
            } else {
                if (r & 17) { s016_ground_post(self, owner, 13); *t = 171.0f; }
                (*n)++;
            }
        }
        s016_end_fx(self, owner, 1, 53);
        break;
    default:
        break;
    }
}

/* the local hunter's position (listener stand-in for 4U 0xaf79a4's object +0xe30 + 16) */
static int listener_pos(float *out)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, out);
    return 1;
}

/* 0xc6e9b4: sound at the capsule point nearest to the listener: 36 / 37 / 53 id 209, 41 / 51 / 54 id 201, started
 * once and then moved there every frame (0x301074 = GU 0x4eff24); 52 / 55 / 56 also 202, started at 340 and every
 * 167 frames after, moved in between (timer 173..340) */
static void s016_sound(void *self, void *owner, uint32_t sub)
{
    float l[4], pt[4] = {0};
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float d[3] = {q[0] - p[0], q[1] - p[1], q[2] - p[2]}, tt = 0.0f;
    if (listener_pos(l)) {
        float dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
        if (dd > 0.0f) tt = ((l[0] - p[0]) * d[0] + (l[1] - p[1]) * d[1] + (l[2] - p[2]) * d[2]) / dd;
        if (tt < 0.0f) tt = 0.0f;
        if (tt > 1.0f) tt = 1.0f;
    }
    for (int i = 0; i < 3; i++) pt[i] = p[i] + tt * d[i];
    uint32_t area = FIELD(uint8_t, self, SH_AREA);
    uint8_t *started = &FIELD(uint8_t, self, S_SND);
    if ((sub == 52 || sub == 55 || sub == 56) && *started) {
        float *t = &FIELD(float, self, S_SND_T);
        *t += FIELD(float, self, SH_DT);
        if (*t >= 340.0f) { em089_snd_pos(owner, 202, pt, area); *t = 173.0f; }
        else if (*t >= 173.0f) em089_snd_move(owner, 202, pt);
    }
    uint32_t id = (sub == 36 || sub == 37 || sub == 53) ? 209 : 201;
    if (*started) { em089_snd_move(owner, id, pt); return; }
    *started = 1;
    em089_snd_pos(owner, id, pt, area);
}

/* slot 79: base setup, then the 4U init 0xc69ddc */
static int s016_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    const s016_t *k = sub_info(sub);
    if (sub == 36 || sub == 53) s016_place(self, owner, sub == 53);
    else s016_place(self, owner, 0);                                  /* 4U: the per-frame call at the init's end */
    s016_orient(self);
    /* 4U posts the effect before placing, but the effect's first update (0x1b5ba0) reads the placed capsule: post
     * after placing so the effect starts at the capsule */
    if (em089_shell016_fx) em089_shell016_fx(self, owner, sub, k->efx);
    FIELD(float, self, S_LIFE) = k->life;
    FIELD(uint8_t, self, S_STATE) = 1;
    /* +696: 41 / 52 / 54-56 8, 51 4 (0xc6a904 / 0xc6a994); +688: 52 / 55 / 56 0 (0xc6ac18) */
    FIELD(float, self, S_TIMER) = sub == 51 ? 4.0f : (sub == 36 || sub == 37 || sub == 53) ? 0.0f : 8.0f;
    FIELD(float, self, S_SND_T) = (sub == 52 || sub == 55 || sub == 56) ? 0.0f : 600.0f;
    s016_sound(self, owner, sub);
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        arm(self, 0, k->hds, -1, 31, 2, 0xffff, FIELD(float, self, SH_ATK0_F14));
        FIELD(uint8_t, self, S_ARMED) = 1;
    }
    static uint32_t s_n;
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    if (++s_n <= 60)
        logf("gogport: em089 attack shell %u spawn sub %u hds %u hit %u life %u, %d %d %d -> %d %d %d",
             FIELD(uint32_t, self, S_SERIAL), sub, k->hds, FIELD(uint8_t, self, S_ARMED), (uint32_t)k->life,
             (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], (int32_t)p[0], (int32_t)p[1], (int32_t)p[2]);
    return 1;
}

/* slot 9 = 4U slot 23 [0xc6ac64] for our subtypes */
static void s016_move(void *self)
{
    uShell_move(self);                                                /* owner gone -> kill (4U 0x917620) */
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    void *owner = *(void **)(FIELD(uint8_t *, self, 0x136c) + 0xc);   /* param owner (uShell 0x4a1b6c) */
    if (!owner) return;
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    if (sub != 36 && sub != 53) s016_place(self, owner, 0);
    /* effects follow the capsule (0x1b5ba0). 36 / 53 keep their placed capsule, but test 9 showed the 53 beam drawn
     * behind him while it hit in front: the post's position / rotation alone does not hold, so set them every frame
     * as for 37 (correct in test 9) */
    em089_efx_shell016_move(self);
    if (sub != 36 && sub != 37 && sub != 53) s016_extras(self, owner, sub);
    s016_sound(self, owner, sub);
    float *life = &FIELD(float, self, S_LIFE);
    *life -= owner_step(owner);
    if (*life < 0.0f) *life = 0.0f;
    if (curMotion(owner) != FIELD(uint32_t, self, S_MOTION)) { s016_kill(self, "owner motion changed"); return; }
    if (*life <= 0.0f) { s016_kill(self, "life out"); return; }
    s016_orient(self);
}

static void *s016_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static void s016_delete(void *self)
{
    em089_efx_shell016_end(self);
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *s016_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void s016_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&s016_delete;
    s_vt[2 + 5] = (uint32_t)&s016_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&s016_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&s016_setup;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&s016_new;
    MtDTI_ctor(&s_dti, "uShellEm089Atk", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("gogport: uShellEm089Atk DTI %x id %x size %x, resource file %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE,
         EM089_SHELL_FILE);
}

/* 4U 0x6620c4 + uShell016 ctor 0xc6f900, through our copy of the GU request 0x48c4f0 */
void *em089_shell016_post(void *self, uint32_t subtype, const float *pos)
{
    static uint32_t s_fail;
    const s016_t *k = sub_info(subtype);
    if (!s_registered) s016_register();
    uint8_t *mgr = SHELL_MGR;
    if (!self || !k || !mgr) {
        if (++s_fail <= 20) logf("gogport: em089 attack shell dropped (owner %x sub %u mgr %x)", (uint32_t)self, subtype,
                                 (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("gogport: em089 attack shell dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = EM089_SHELL_ID;
    FIELD(uint32_t, param, 8) = 0;
    FIELD(void *, param, 0xc) = self;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint32_t, param, 0x30) = FIELD(uint32_t, self, 0xfe8);
    FIELD(uint32_t, param, 0x34) = FIELD(uint32_t, self, 0xfec);
    FIELD(uint32_t, param, 0x38) = FIELD(uint32_t, self, 0xff0);
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = s016_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    /* ctor fields (0xc6f948..0xc6fb70) */
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(uint32_t, shell, S_JOINT) = 3;
    float *off = VEC(shell, S_OFF);
    if (pos) { off[0] = pos[0]; off[1] = pos[1]; off[2] = pos[2]; }
    else if (k->off_kind) { off[0] = 0.0f; off[1] = -50.0f; off[2] = 130.0f; }
    FIELD(float, shell, S_LEN) = 10000.0f;
    FIELD(uint32_t, shell, S_XANG) = (k->xang + (k->add_x ? FIELD(uint32_t, rec, REC_ANGLES) : 0)) & 0xffff;
    FIELD(uint32_t, shell, S_YANG) = (k->yang + (k->add_y ? FIELD(uint32_t, rec, REC_YAW) : 0)) & 0xffff;
    FIELD(uint32_t, shell, S_MOTION) = curMotion(self);
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    uShell_setResource(shell, fileResource(0, EM089_SHELL_FILE));
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        if (++s_fail <= 20) logf("gogport: em089 attack shell setup failed (owner type %u)", FIELD(uint8_t, self, 0x1052));
        s016_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
