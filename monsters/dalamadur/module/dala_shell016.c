/* dala_shell016.c: Dalamadur's mouth beam (goal D5): literal translation of 4U uShell016 (type 16 via 0x6620c4;
 * 704 B, vtable 0xe6d98c: ctor 0xc6f900, slot 22 init 0xc69ddc, slot 23 per frame 0xc6ac64) for subtypes 21
 * (Dalamadur) / 39 (Shah), posted by the head's sink passes at motion frame 248 (4U 0x7711f8 in 0x770ec0 and
 * 0x775e70 in 0x775cbc kinds 3 / 4; em090_act7.c beam()). My earlier "quake post" name was wrong: 21 / 39 are a beam
 * capsule from the mouth, the same family as Gogmazios' 37 / 41 (em089_shell016.c). As a GU uShellEnemy subclass
 * (dala_shell.c). C = read in code, S = strong, G = guess.
 *
 * Post (C, both sites): 0x6620c4(mgr, this, &{joint 5, offset (0, -273, 751, 0), byte 0, x 0xe39, y 0}, 21 / 39,
 * group 0xffff, 0, 0, length 12000).
 * Ctor 0xc6f900 (default case for 21 / 39, C): x angle +0x290 = 0xe39 + owner x angle W+0x1a8, y +0x294 = 0 + owner
 * yaw W+0x1ac, joint +0x2a4, offset +0x270, length +0x29c, owner motion at spawn +0x2a0, group +0x2ac.
 * Init 0xc69ddc (cases 19 / 37 -> 0xc6a6b8 / 0xc6a6ec, C): life +0x13c = 0x102bbbc[sub] = 320; effect 0xc07ecc(mgr,
 * type 15, id 2 / 6) = a uEffect015 controller (ctor 0x1c538c, slots 18 / 20) that attaches flat-table file
 * 0xfd16ac[id] = {35, 7} / {81, 7} = em024_009 / em110_009 to the shell (vt+0x48, joint -1) and stretches its z
 * scale to (capsule length - 0) / 0xfd16d0[id] +12 (1000.0) = 12, x / y from the curve 0xfd16d0[id] +4 = 0xfd1514
 * = constant 13 (C; PEL 2940 scale (13, 13, 12)); it ends when the shell is no longer alive (0x1c4da0 state test).
 * Attack 0x9ab120(records
 * 0x102b3d0, volumes 0x102b370, 0x102bad8[sub] = 14 / 34, 31, 2): power 120, window 0 + 99, volume 17 = capsule on
 * bone 1001, radius 800 (its float +24 = 0); +688 = 600; no init sound.
 * Per frame 0xc6c050 (cases 19 / 37): at owner motion frame 380 re-arm with record 18 / 35 (power 150, same
 * volume); slot +88 = 100; second point +0x120 = joint + M (offset + (0, 0, vol +24)), point +0x100 = joint + M
 * rotX(x angle)(offset + (0, 0, vol +24 + length)) (M = joint matrix 0x930894); then the common tail 0xc6e8d4:
 * sound 0xc6f0ac (+688 += dt; at >= 48: 208 and 212 at the capsule point nearest the listener, +688 = 0; else both
 * moved there), life -= owner motion step (0x94460c), end when the owner's motion is not the spawn motion or life
 * <= 0, angles from the segment. Owner gone -> end (0xc6ac94).
 * Multiplayer: no net test in the post sites or the class (C); GU replays the sink-pass action on every machine,
 * each machine places its own beam on its own replay of the head's motion (as 4U, local shell). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"
#include "dala_efx.h"

typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx             FN(joint_mtx_t, 0xc1660)     /* = 4U 0x930894 */
typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)
#define uShell_kill          FN(shell_fn_t, 0x4a247c)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)
#define SLOT_KILL            16
#define VOL17_Z              0.0f     /* volume 17 (0x102b190) float +24 */

/* our fields (4U uShell016 offset in brackets) */
#define S_SUB     (DALA_SH_FIELDS + 0x00)   /* u8 [+0xfd] */
#define S_STATE   (DALA_SH_FIELDS + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define S_ARMED   (DALA_SH_FIELDS + 0x02)   /* u8 1 = record 14 / 34, 2 = re-armed 18 / 35 */
#define S_DYING   (DALA_SH_FIELDS + 0x03)
#define S_JOINT   (DALA_SH_FIELDS + 0x04)   /* u32 [+0x2a4] */
#define S_OFF     (DALA_SH_FIELDS + 0x08)   /* float[3] [+0x270] */
#define S_LEN     (DALA_SH_FIELDS + 0x14)   /* float [+0x29c] */
#define S_XANG    (DALA_SH_FIELDS + 0x18)   /* u32 [+0x290] */
#define S_YANG    (DALA_SH_FIELDS + 0x1c)   /* u32 [+0x294] */
#define S_LIFE    (DALA_SH_FIELDS + 0x20)   /* float [+0x13c] */
#define S_MOTION  (DALA_SH_FIELDS + 0x24)   /* u32 owner motion at spawn [+0x2a0] */
#define S_SERIAL  (DALA_SH_FIELDS + 0x28)
#define S_SND_T   (DALA_SH_FIELDS + 0x2c)   /* float [+688] */
#define S_EFX     (DALA_SH_FIELDS + 0x30)   /* void * the controller's child effect */
#define S_DIE_T   (DALA_SH_FIELDS + 0x34)
#define SHELL_SIZE (DALA_SH_FIELDS + 0x40)
#define EFX_DIE_MAX 300.0f

#define VEC(p, off) (&FIELD(float, p, off))

static dala_shcls_t s_cls;
static uint32_t s_serial;

static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }
static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* 0xc6c0a4..0xc6c27c: second point and point from the joint */
static void s016_place(void *self, void *owner)
{
    uint32_t joint = FIELD(uint32_t, self, S_JOINT);
    float j[4], m[16];
    jointPos(owner, joint, j);
    jointMtx(owner, joint, m);
    const float *off = VEC(self, S_OFF);
    float o[3] = {off[0], off[1], off[2] + VOL17_Z};
    float v[3] = {off[0], off[1], off[2] + VOL17_Z + FIELD(float, self, S_LEN)};
    float s = sinf_gu(ang_rad(FIELD(uint32_t, self, S_XANG))), c = cosf_gu(ang_rad(FIELD(uint32_t, self, S_XANG)));
    float y = c * v[1] - s * v[2], z = s * v[1] + c * v[2];   /* 0xaad560: rotate (y, z) */
    v[1] = y; v[2] = z;
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) {
        q[i] = j[i] + o[0] * m[i] + o[1] * m[4 + i] + o[2] * m[8 + i];
        p[i] = j[i] + v[0] * m[i] + v[1] * m[4 + i] + v[2] * m[8 + i];
    }
}

/* 0xc6e944: y = atan2(dx, dz), x = atan2(-dy, horizontal), z = 0 of point - second point */
static void s016_orient(void *self)
{
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
    FIELD(uint32_t, self, SH_ANGLES + 4) = rad_ang(atan2f_gu(dx, dz));
    FIELD(uint32_t, self, SH_ANGLES) = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));
    FIELD(uint32_t, self, SH_ANGLES + 8) = 0;
}

/* 0xc6f0ac: 208 + 212 at the capsule point nearest to the listener (0xbdf918 / 0x1dfddc, t in [0, 1]) */
static void s016_sound(void *self, void *owner)
{
    float *t = &FIELD(float, self, S_SND_T);
    *t += dala_shell_dt(self);                              /* 0x9a95c0 */
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    float d[3] = {q[0] - p[0], q[1] - p[1], q[2] - p[2]}, l[4], k = 0.0f, pt[4] = {p[0], p[1], p[2], 0.0f};
    if (dala_listener_pos(l)) {
        float dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
        if (dd > 0.0f) k = ((l[0] - p[0]) * d[0] + (l[1] - p[1]) * d[1] + (l[2] - p[2]) * d[2]) / dd;
        if (k < 0.0f) k = 0.0f;
        if (k > 1.0f) k = 1.0f;
        for (int i = 0; i < 3; i++) pt[i] = p[i] + k * d[i];
    }
    uint32_t area = FIELD(uint8_t, self, SH_AREA);
    if (*t >= 48.0f) {
        *t = 0.0f;
        dala_snd_pos(owner, 208, pt, area);
        dala_snd_pos(owner, 212, pt, area);
    } else {
        dala_snd_move(owner, 208, pt);
        dala_snd_move(owner, 212, pt);
    }
}

static void s016_end(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 30) logf("dalaport: beam %u (sub %u) end: %s", FIELD(uint32_t, self, S_SERIAL), FIELD(uint8_t, self, S_SUB),
                          why);
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* one 4U slot-23 frame after the owner test (0xc6c050 + 0xc6e8d4) */
static void s016_frame(void *self, void *owner)
{
    if (motionCheck(owner, 0, 0, 380.0f, 0.0f)) {           /* 0xc6c068: re-arm with record 18 / 35 */
        if (dala_shell_arm(self, DALA_HDS_S016_18, 31, 2, 0xffff)) FIELD(uint8_t, self, S_ARMED) = 2;
    }
    FIELD(float, self, SH_ATK0 + ATK_TIME) = 100.0f;        /* +448 = 100 */
    s016_place(self, owner);
    s016_sound(self, owner);
    float *life = &FIELD(float, self, S_LIFE);
    *life -= dala_shell_owner_step(owner);
    if (*life < 0.0f) *life = 0.0f;
    s016_orient(self);
    dala_efx_place(FIELD(void *, self, S_EFX), VEC(self, SH_POS2), FIELD(uint32_t, self, SH_ANGLES),
                   FIELD(uint32_t, self, SH_ANGLES + 4));
    if (curMotion(owner) != FIELD(uint32_t, self, S_MOTION)) { s016_end(self, "owner motion changed"); return; }
    /* deviation (test 2026-10-21: the beam stayed after the death): in 4U the death motion ends it through the
     * motion test above; here the death (category 11, dala_react.c) can play the beam's own motion 0x329 and the
     * stopped body no longer drains life, so the owner's death ends it */
    if (FIELD(uint8_t, owner, EN_ACT_CAT) == 11) { s016_end(self, "owner dead"); return; }
    if (*life <= 0.0f) s016_end(self, "life out");
}

/* slot 16: the controller ends with the shell (0x1c4da0); the effect is attached, so the shell waits for it */
static void s016_slot_kill(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (h && !dala_efx_alive(h)) FIELD(void *, self, S_EFX) = h = 0;
    if (!h) { FIELD(uint8_t, self, S_DYING) = 0; uShell_kill(self); return; }
    if (FIELD(uint8_t, self, S_DYING)) return;
    FIELD(uint8_t, self, S_DYING) = 1;
    FIELD(uint8_t, self, S_STATE) = 2;
    FIELD(float, self, S_DIE_T) = 0.0f;
    dala_shell_slots_off(self);
    dala_efx_stop(h);
}

static void s016_dying(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    float *t = &FIELD(float, self, S_DIE_T);
    *t += dala_shell_dt(self);
    if (h && dala_efx_alive(h) && *t >= EFX_DIE_MAX && *t < EFX_DIE_MAX + 1000.0f) {
        dala_efx_kill(h);
        *t = EFX_DIE_MAX + 1000.0f;
        return;
    }
    if (h && dala_efx_alive(h) && *t < EFX_DIE_MAX + 1000.0f + 30.0f) return;
    FIELD(void *, self, S_EFX) = 0;
    FIELD(uint8_t, self, S_DYING) = 0;
    uShell_kill(self);
}

/* slot 79: base set-up, ctor fields, init 0xc69ddc and its first slot-23 call */
static int s016_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    FIELD(float, self, S_LIFE) = 320.0f;                    /* 0x102bbbc[21 / 39] */
    FIELD(uint8_t, self, S_STATE) = 1;
    if (dala_shell_arm(self, DALA_HDS_S016_14, 31, 2, 0xffff)) FIELD(uint8_t, self, S_ARMED) = 1;
    FIELD(float, self, S_SND_T) = 600.0f;                   /* +688 */
    s016_place(self, owner);
    s016_orient(self);
    /* the controller's child effect. 4U attaches it to the shell; here, as Gogmazios' working beams (em089_efx.c
     * s016_post / em089_efx_shell016_move), it is posted at the capsule start with the segment's pitch / yaw and moved
     * there every frame (s016_frame): attached to the shell (follow record, dala_efx_post_on) it was not drawn (user,
     * test 2026-10-22: "the beam is missing, ghost hits"; log: posted, handle valid) */
    FIELD(void *, self, S_EFX) = dala_efx_post_beam(owner, DALA_EFX_BEAM, VEC(self, SH_POS2),
                                                    FIELD(uint32_t, self, SH_ANGLES), FIELD(uint32_t, self, SH_ANGLES + 4));
    static uint32_t s_n;
    const float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    if (++s_n <= 30)
        logf("dalaport: beam %u spawn sub %u hit %u efx %x, %d %d %d -> %d %d %d", FIELD(uint32_t, self, S_SERIAL),
             FIELD(uint8_t, self, S_SUB), FIELD(uint8_t, self, S_ARMED), (uint32_t)FIELD(void *, self, S_EFX),
             (int32_t)q[0], (int32_t)q[1], (int32_t)q[2], (int32_t)p[0], (int32_t)p[1], (int32_t)p[2]);
    s016_frame(self, owner);                                /* the init's tail call of slot 23 */
    return 1;
}

/* slot 9 = 4U slot 23 */
static void s016_move(void *self)
{
    if (FIELD(void *, self, S_EFX) && !dala_efx_alive(FIELD(void *, self, S_EFX))) FIELD(void *, self, S_EFX) = 0;
    uShell_move(self);                                      /* owner gone -> kill (4U 0xc6ac94) */
    if (FIELD(uint8_t, self, S_DYING)) { s016_dying(self); return; }
    if (!dala_shell_live(self) || FIELD(uint8_t, self, S_STATE) != 1) return;
    void *owner = dala_shell_owner(self);
    if (owner) s016_frame(self, owner);
}

static void *s016_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls); }
static MtDTI *s016_dti(void *self) { (void)self; return &s_cls.dti; }

static void s016_delete(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (dala_efx_alive(h)) dala_efx_kill(h);
    FIELD(void *, self, S_EFX) = 0;
    dala_shell_free(&s_cls, self);
}

void *dala_shell016_post(void *owner, uint32_t subtype, uint32_t joint, const float *off, uint32_t xang,
                         uint32_t yang, float length)
{
    if ((subtype != 21 && subtype != 39) || !owner || !off) return 0;
    if (!s_cls.registered)
        dala_shell_register(&s_cls, "uShellDala016", SHELL_SIZE, s016_new, s016_delete, s016_dti, s016_move, s016_setup,
                            s016_slot_kill);
    void *param = dala_shell_param(owner, "beam");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls);
    if (!shell) { dala_shell_param_free(param); return 0; }
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(uint32_t, shell, S_JOINT) = joint;
    float *o = VEC(shell, S_OFF);
    o[0] = off[0]; o[1] = off[1]; o[2] = off[2];
    FIELD(float, shell, S_LEN) = length;
    FIELD(uint32_t, shell, S_XANG) = (xang + FIELD(uint32_t, rec, REC_ANGLES)) & 0xffff;   /* + W+0x1a8 */
    FIELD(uint32_t, shell, S_YANG) = (yang + FIELD(uint32_t, rec, REC_YAW)) & 0xffff;      /* + W+0x1ac */
    FIELD(uint32_t, shell, S_MOTION) = curMotion(owner);
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    return dala_shell_start(shell, param, "beam");
}
