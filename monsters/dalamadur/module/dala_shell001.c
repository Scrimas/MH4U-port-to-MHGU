/* dala_shell001.c: Dalamadur's fireball (goal D5). Literal translation of
 *  (A) the head's aim + post 4U 0x77250c(this, kind, lim, ang, flag) with its spawn data 0x773e00, called by the 7.x
 *      handlers at fixed frames (em090_act7.c shell());
 *  (B) the 4U shell uShell001 (type 1 of the poster 0x660e88 via 0x661bec; 704 B, vtable 0xe6d2fc: ctor 0xc4fd84,
 *      slot 22 init 0xc4c54c, slot 23 per frame 0xc4d940, slot 24 kill 0xc4fcf0) for the kinds Dalamadur posts:
 *      24 / 25 (em 24) and 88 / 89 (Shah), all four take the same paths (C: init case 0xc4cf3c, frame 0xc4e338 ->
 *      default tails 0xc4ead4) and differ only by table data;
 * as a GU uShellEnemy subclass (dala_shell.c framework). C = read in code, S = strong, G = guess.
 *
 * 4U data per kind (C; bss tables from the static init 0xd34794, emulated: scratchpad e/emu2.py):
 *   effect 0x1017980[k] {35 / 81, 0, mask -1} = em024_000 / em110_000 at scale 0x101b214[2k] = 3.5, colour
 *   0x10ba3fc[k] = 0xffffffff (none); velocity 0x10ba5ec[k] = (0, 0, 120), acceleration 0x10babbc[k] = 0; life
 *   0x101b024[k] = 300; attack 0x9ab120(records 0x1019f30, volumes 0x1019e50, 0x101ae30[k] = 64 / 62 / 81 / 82, 31,
 *   2) (record 64 = 82: power 80, byte 0xb 60; 62 = 81: power 80, byte 0xb 40; window 0 + 99; volume 39 = sphere on
 *   bone 1001, radius 600); spawn sound 0x1018520[k] {2, joint 6, 202}; loop sound 0x10194a0[k] {2, 35.0, 211};
 *   impact sounds 0x1018900[k] = 203 (wall / ground); impact effects 0x1018140[k] {35 / 81, 1, mask 2} (wall) and
 *   0x1017d60[k] (ground: kinds 24 / 88 none, 25 / 89 {35 / 81, 1, mask 1}) at scale 0x101b214[2k + 1] = 1.0 (24 /
 *   88) / 1.2 (25 / 89); follow-ups (0xc4f13c) wall 0x1019c60[k] = {1, 114 / Shah 161} -> uShell003, ground
 *   0x1019a70[k] = 24: {2, 1} -> uShell009 1, 88: {2, 2} -> uShell009 2, 25 / 89: uShell003 114 / 161; camera shake
 *   byte 3 = 0 -> id 1 at every impact.
 * Map hit (0xc4e450): 0x2b96e4(pos, prev, area, out, info, mask 48, 0x9aad8c); bits 0x22 -> "wall" (r5 = 0), else
 * "ground" (r5 = 1): S (the meteor's floor test is & 17; the wall row posts the plain blast, the ground row the
 * burn sequence).
 * End conditions (all traced): owner gone (0x917620 -> state 3, uShell_move here); life 300 out (0xc4da10: state 2,
 * life 10; the frame still moves and tests the map once more, as here); map hit (0xc4e4c4: state 2). Hunter hits
 * do not end it (no path reads the attack slot for these kinds). State 2 = killed by the next frame.
 * Effect: 4U's kill 0xc4fcf0 releases +0x290 only for kinds 110..113, so the fireball effect outlives the shell;
 * here (dala_meteor.c pattern) the kill stops it and the shell waits for it (attack off), forced after 300 frames.
 * 4U kills the shell when the effect cannot be made (0xc4c670); here a missing PEL record is a port gap: logged,
 * the shell lives.
 * Not ported: the effect's ground-normal rotation of the ground impact (0xc4ec28 / 0xd076b0: a fixed PEL record
 * cannot take it, G), 0xc09908's owner class byte +0x288 (effect request +0x70: no PEL field).
 * Multiplayer: 0x77250c has no net test (C) and is called from the 7.x handlers, which GU replays on every machine;
 * the aim reads target slot 0 (4U W+0x218 = GU rec+464) locally, as 4U. Each machine flies its own fireball. */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"
#include "dala_efx.h"

typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx             FN(joint_mtx_t, 0xc1660)     /* = 4U 0x930894 (C, em089_shell016.c) */
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
#define REC_STATE_ID         0x1ba    /* u8 state class [4U W+0x1c8] (game.h REC_STATE) */

/* our fields (4U uShell001 offset in brackets) */
#define S_KIND    (DALA_SH_FIELDS + 0x00)   /* u8 kind [+0xfd] */
#define S_STATE   (DALA_SH_FIELDS + 0x01)   /* u8 0 new, 1 flying, 2 done [+0xf1] */
#define S_ARMED   (DALA_SH_FIELDS + 0x02)
#define S_DYING   (DALA_SH_FIELDS + 0x03)   /* u8 1 = killed, waiting for the effect */
#define S_SERIAL  (DALA_SH_FIELDS + 0x04)
#define S_LIFE    (DALA_SH_FIELDS + 0x08)   /* float [+0x26c] */
#define S_SND_T   (DALA_SH_FIELDS + 0x0c)   /* float loop-sound timer [+0x28c] */
#define S_VEL     (DALA_SH_FIELDS + 0x10)   /* float[3] [+0x140] */
#define S_ACC     (DALA_SH_FIELDS + 0x1c)   /* float[3] [+0x150] */
#define S_PREV    (DALA_SH_FIELDS + 0x28)   /* float[3] [+0x120] */
#define S_START   (DALA_SH_FIELDS + 0x34)   /* float[3] request position (data +8) */
#define S_PITCH   (DALA_SH_FIELDS + 0x40)   /* u32 request x angle (data +26) */
#define S_YAW     (DALA_SH_FIELDS + 0x44)   /* u32 request yaw (data +28) */
#define S_EFX     (DALA_SH_FIELDS + 0x48)   /* void * attached effect [+0x290] */
#define S_DIE_T   (DALA_SH_FIELDS + 0x4c)   /* float frames waited for the effect */
#define SHELL_SIZE (DALA_SH_FIELDS + 0x60)
#define EFX_DIE_MAX 300.0f

#define VEC(p, off) (&FIELD(float, p, off))

static dala_shcls_t s_cls;
static uint32_t s_serial;

static int is_shah_kind(uint32_t k) { return k == 88 || k == 89; }
static int hi_kind(uint32_t k) { return k == 24 || k == 89; }   /* records 64 / 82 (byte 0xb 60) */
static int big_kind(uint32_t k) { return k == 25 || k == 89; }  /* 0x101b214[2k + 1] = 1.2, ground effect present */

static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }
static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffff; }
static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* 0xaad5b0(v, a): rotate (x, z) by a */
static void rot_y(float *v, uint32_t a)
{
    float s = sinf_gu(ang_rad(a)), c = cosf_gu(ang_rad(a)), x = c * v[0] + s * v[2], z = c * v[2] - s * v[0];
    v[0] = x; v[2] = z;
}

/* M * (0, a, b, 1) with the 4U projective divide (w == 0 -> 0) */
static void mtx_point(const float *m, float a, float b, float *out)
{
    float w = m[7] * a + m[11] * b + m[15], k = w != 0.0f ? 1.0f / w : 0.0f;
    for (int i = 0; i < 3; i++) out[i] = (m[4 + i] * a + m[8 + i] * b + m[12 + i]) * k;
    out[3] = 0.0f;
}

/* ================================================================== (A) the head's aim 0x77250c ============= */

void dala_head_fireball(void *self, uint32_t kind, uint32_t lim, uint32_t ang, uint32_t flag)
{
    float m[16], p[4], q[4];
    jointMtx(self, 5, m);
    mtx_point(m, -573.0f, 100.0f, p);                       /* aim origin: joint 5 * (0, -573, 100) */
    uint32_t jyaw = rad_ang(atan2f_gu(m[8], m[10]));        /* r4: yaw of the joint's z axis */
    const float *t = (const float *)(REC(self) + REC_TARGET);   /* target slot 0 W+0x218 */
    float dx = t[0] - p[0], dy = t[1] + 100.0f - p[1], dz = t[2] - p[2];
    uint32_t yaw = rad_ang(atan2f_gu(dx, dz));               /* r9 */
    uint32_t pitch = rad_ang(atan2f_gu(-dy, sqrt_f(dx * dx + dz * dz)));   /* r3 */
    uint32_t r1 = (65536u - lim) & 0xffffffffu, r2 = 16384u - lim;
    uint32_t rel = (yaw - jyaw) & 0xffff;
    if (!flag && rel - 16384u <= 32768u) {                  /* 0x772674: behind the joint -> at least 90 deg down */
        if (pitch < 16384) pitch = 16384;
    } else if (pitch >= 32768) {                            /* aiming up: no more than lim */
        if (r1 > pitch) pitch = r1 & 0xffff;
    } else if ((int32_t)r2 < (int32_t)pitch) {              /* aiming down: no more than 90 deg - lim */
        pitch = r2 & 0xffff;
    }
    if (rel >= 32768) {                                     /* 0x7726c0: yaw within ang of the joint's */
        if (65536u - rel > ang) yaw = (jyaw - ang) & 0xffff;
    } else if (ang < rel) {
        yaw = (jyaw + ang) & 0xffff;
    }
    /* 0x773e00(this, &data, 1, pitch, yaw): data {joint 5, joint 5 * (0, -573, 100) (action 86: (0, 300, 250)),
     * byte 0x18 = 1, u16 +26 pitch, u16 +28 yaw}; 0x661bec(mgr, this, &data, kind, 0xffff) */
    if (FIELD(uint8_t, self, EN_ACT_NUM) == 86) mtx_point(m, 300.0f, 250.0f, q);   /* W+0x1cb = the action number */
    else mtx_point(m, -573.0f, 100.0f, q);
    dala_shell001_post(self, kind, q, pitch, yaw);
}

/* ================================================================== (B) the shell uShell001 ================= */

static void *s001_owner(void *self) { return dala_shell_owner(self); }

/* 0xc4eb80 + 0xc4f13c for these kinds: impact effect / sound, camera shake, follow-up shell */
static void s001_impact(void *self, void *owner, uint32_t ground)
{
    uint32_t kind = FIELD(uint8_t, self, S_KIND), area = FIELD(uint8_t, self, SH_AREA), shah = is_shah_kind(kind);
    const float *pos = VEC(self, SH_POS);
    FIELD(float, self, S_LIFE) = 36.0f;                     /* 0xc4ebb4 */
    /* effect at the hit point: wall 0x1018140 (element 1 of em024_001), ground 0x1017d60 (25 / 89 only) */
    /* on this shell, which sits at the hit point (a world-position post attaches the owner's model: dala_shell003.c) */
    if (!ground) dala_efx_post_on(owner, big_kind(kind) ? DALA_EFX_FIREBALL_WALL_L : DALA_EFX_FIREBALL_WALL, self);
    else if (big_kind(kind)) dala_efx_post_on(owner, DALA_EFX_FIREBALL_GROUND, self);
    dala_snd_pos(owner, 203, pos, area);                    /* 0x1018900 + 24 k [+0 / +8] = (2, 203) */
    dala_cam_shake_pos(owner, 1, pos, area);                /* 0xc4f168: byte 3 = 0 -> 0xbfd568(mgr, 1, &pos) */
    uint32_t group = dala_shell_group(self);                /* 4U r7 + 156 = +0x19c */
    if (ground && (kind == 24 || kind == 88))               /* 0x1019a70 {2, 1 / 2} -> 0x661ea0 type 9 */
        dala_shell009_post(owner, kind == 88 ? 2 : 1, pos, area, group, &FIELD(uint32_t, self, SH_ANGLES));
    else                                                     /* {1, 114 / 161, 0} -> 0x663220 type 3 */
        dala_shell003_post(owner, shah ? 161 : 114, pos, area, group);
}

/* 4U slot 23 [0xc4d940] for kinds 24 / 25 / 88 / 89, after the owner test: 1 = done (state 2) */
static int s001_step(void *self, void *owner)
{
    uint32_t kind = FIELD(uint8_t, self, S_KIND), serial = FIELD(uint32_t, self, S_SERIAL);
    int done = 0;
    float *life = &FIELD(float, self, S_LIFE);
    dala_shell_timer(self, life);
    if (*life <= 0.0f) {                                    /* 0xc4da10: state 2, life 10, the frame goes on */
        *life = 10.0f;
        done = 1;
        static uint32_t s_n;
        if (++s_n <= 30) logf("dalaport: fireball %u kind %u timed out", serial, kind);
    }
    float *pos = VEC(self, SH_POS), *prev = VEC(self, S_PREV), *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC);
    prev[0] = pos[0]; prev[1] = pos[1]; prev[2] = pos[2];   /* 0xc4df70 (kind != 4) */
    FIELD(float, self, SH_ATK0 + ATK_TIME) = 100.0f;        /* 0xc4df90: +0x1c0 = 100 every frame */
    float dt = dala_shell_dt(self), h = dt * dt * 0.5f;   /* 0x9ab0a0 */
    for (int i = 0; i < 3; i++) { pos[i] += vel[i] * dt + acc[i] * h; vel[i] += acc[i] * dt; }
    float *p2 = VEC(self, SH_POS2);
    p2[0] = prev[0]; p2[1] = prev[1]; p2[2] = prev[2];
    float out[4] = {0, 0, 0, 0};
    void *col = COL_MGR;
    /* 0xc4e450: 0x2b96e4(col, pos, prev, area, out, info, 48, 0x9aad8c(this)); the info block (0xc4eb80's normal,
     * 0xc094e8's ground attribute) is not passed: GU's layout is not checked */
    uint32_t r = col ? mapSegment(col, pos, prev, FIELD(uint8_t, self, SH_AREA), out, 0, 48, uShell_colFlags(self)) : 0;
    if (r) {
        uint32_t ground = (r & 34) ? 0 : 1;                 /* 0xc4e4ac */
        pos[0] = out[0]; pos[1] = out[1]; pos[2] = out[2];
        static uint32_t s_n;
        if (++s_n <= 60) logf("dalaport: fireball %u kind %u hit %s (%x) at %d %d %d", serial, kind,
                              ground ? "ground" : "wall", r, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2]);
        s001_impact(self, owner, ground);
        done = 1;
    } else if (dala_shell_timer(self, &FIELD(float, self, S_SND_T))) {   /* 0xc4f9bc: 211 every 35 frames */
        FIELD(float, self, S_SND_T) = 35.0f;
        dala_snd_obj(owner, 211, self, FIELD(uint8_t, self, SH_AREA));
    }
    /* 0xc4eb1c: angles from the velocity */
    float hz = sqrt_f(vel[0] * vel[0] + vel[2] * vel[2]);
    FIELD(uint32_t, self, SH_ANGLES) = rad_ang(atan2f_gu(-vel[1], hz));
    FIELD(uint32_t, self, SH_ANGLES + 4) = rad_ang(atan2f_gu(vel[0], vel[2]));
    FIELD(uint32_t, self, SH_ANGLES + 8) = rad_ang(atan2f_gu(-vel[0], vel[1]));
    return done;
}

/* slot 16: deferred kill while the attached effect lives (dala_meteor.c) */
static void s001_slot_kill(void *self)
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

static void s001_dying(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    float *t = &FIELD(float, self, S_DIE_T);
    *t += dala_shell_dt(self);
    if (h && dala_efx_alive(h) && *t >= EFX_DIE_MAX && *t < EFX_DIE_MAX + 1000.0f) {
        dala_efx_kill(h);
        *t = EFX_DIE_MAX + 1000.0f;           /* one more frame for the effect's own kill */
        return;
    }
    if (h && dala_efx_alive(h) && *t < EFX_DIE_MAX + 1000.0f + 30.0f) return;
    FIELD(void *, self, S_EFX) = 0;
    FIELD(uint8_t, self, S_DYING) = 0;
    uShell_kill(self);
}

/* slot 79: base set-up, the ctor 0xc4fd84 fields, init 0xc4c54c (case 0xc4cf3c) and its first slot-23 call */
static int s001_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    uint32_t kind = FIELD(uint8_t, self, S_KIND);
    /* ctor: +0x110 = data +26 (+ owner x angle W+0x1a8 unless W+0x1c8 == 5), +0x114 = owner yaw W+0x1ac + data +28,
     * +0x118 = 0; position = data +8 (case 0xc4cf3c keeps it); the area is the owner's W+0x14c (base copy) */
    uint32_t xa = FIELD(uint32_t, self, S_PITCH) + (FIELD(uint8_t, rec, REC_STATE_ID) == 5 ? 0 : FIELD(uint32_t, rec, REC_ANGLES));
    FIELD(uint32_t, self, SH_ANGLES) = xa & 0xffff;
    FIELD(uint32_t, self, SH_ANGLES + 4) = (FIELD(uint32_t, rec, REC_YAW) + FIELD(uint32_t, self, S_YAW)) & 0xffff;
    FIELD(uint32_t, self, SH_ANGLES + 8) = 0;
    float *pos = VEC(self, SH_POS), *st = VEC(self, S_START), *prev = VEC(self, S_PREV), *p2 = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) pos[i] = prev[i] = p2[i] = st[i];
    /* velocity 0x10ba5ec[k] = (0, 0, 120) rotated by z (+0x118), x (+0x110), then y (+0x114, 0xaad5b0); the
     * acceleration (0) by y only */
    float *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC);
    vel[0] = 0.0f; vel[1] = 0.0f; vel[2] = 120.0f;
    acc[0] = acc[1] = acc[2] = 0.0f;
    float s = sinf_gu(ang_rad(xa)), c = cosf_gu(ang_rad(xa)), y = c * vel[1] - s * vel[2], z = s * vel[1] + c * vel[2];
    vel[1] = y; vel[2] = z;
    rot_y(vel, FIELD(uint32_t, self, SH_ANGLES + 4));
    FIELD(float, self, S_LIFE) = 300.0f;                    /* 0x101b024[k] */
    FIELD(uint8_t, self, S_ARMED) = (uint8_t)dala_shell_arm(self, hi_kind(kind) ? DALA_HDS_S001_HI : DALA_HDS_S001_LO,
                                                            31, 2, 0xffff);
    FIELD(float, self, S_SND_T) = 0.0f;                     /* +0x28c */
    dala_snd_joint_pos(owner, 202, 6, FIELD(uint8_t, self, SH_AREA));   /* 0x304c34(mgr, 202, owner, 6, area, -2) */
    /* the effect (4U posts it first; GU's first effect update reads the shell: post once it is placed) */
    FIELD(void *, self, S_EFX) = dala_efx_post_on(owner, DALA_EFX_FIREBALL, self);
    FIELD(uint8_t, self, S_STATE) = 1;
    static uint32_t s_n;
    if (++s_n <= 40)
        logf("dalaport: fireball %u spawn kind %u at %d %d %d angles %x %x hit %u efx %x", FIELD(uint32_t, self, S_SERIAL),
             kind, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], FIELD(uint32_t, self, SH_ANGLES),
             FIELD(uint32_t, self, SH_ANGLES + 4), FIELD(uint8_t, self, S_ARMED), (uint32_t)FIELD(void *, self, S_EFX));
    if (s001_step(self, owner)) FIELD(uint8_t, self, S_STATE) = 2;   /* the init's tail call of slot 23 */
    return 1;
}

/* slot 9 = 4U slot 23 */
static void s001_move(void *self)
{
    if (FIELD(void *, self, S_EFX) && !dala_efx_alive(FIELD(void *, self, S_EFX))) FIELD(void *, self, S_EFX) = 0;
    uShell_move(self);                        /* owner gone -> kill (4U 0xc4d9b0: state 3) */
    if (FIELD(uint8_t, self, S_DYING)) { s001_dying(self); return; }
    if (!dala_shell_live(self)) return;
    if (FIELD(uint8_t, self, S_STATE) == 2) { VCALL0(self, SLOT_KILL); return; }
    if (FIELD(uint8_t, self, S_STATE) != 1) return;
    void *owner = s001_owner(self);
    if (!owner) return;
    if (s001_step(self, owner)) FIELD(uint8_t, self, S_STATE) = 2;
}

static void *s001_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls); }
static MtDTI *s001_dti(void *self) { (void)self; return &s_cls.dti; }

static void s001_delete(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (dala_efx_alive(h)) dala_efx_kill(h);   /* deleted without our kill (area / quest teardown) */
    FIELD(void *, self, S_EFX) = 0;
    dala_shell_free(&s_cls, self);
}

/* 0x661bec(mgr, owner, &data, kind, 0xffff) -> 0x660e88 type 1 -> ctor 0xc4fd84 */
void *dala_shell001_post(void *owner, uint32_t kind, const float *pos, uint32_t pitch, uint32_t yaw)
{
    if (kind != 24 && kind != 25 && kind != 88 && kind != 89) {
        static uint32_t s_n;
        if (++s_n <= 10) logf("dalaport: fireball kind %u is not Dalamadur's: dropped", kind);
        return 0;
    }
    if (!s_cls.registered)
        dala_shell_register(&s_cls, "uShellDala001", SHELL_SIZE, s001_new, s001_delete, s001_dti, s001_move, s001_setup,
                            s001_slot_kill);
    void *param = dala_shell_param(owner, "fireball");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls);
    if (!shell) { dala_shell_param_free(param); return 0; }
    FIELD(uint8_t, shell, S_KIND) = (uint8_t)kind;
    float *st = VEC(shell, S_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    FIELD(uint32_t, shell, S_PITCH) = pitch & 0xffff;
    FIELD(uint32_t, shell, S_YAW) = yaw & 0xffff;
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    return dala_shell_start(shell, param, "fireball");
}
