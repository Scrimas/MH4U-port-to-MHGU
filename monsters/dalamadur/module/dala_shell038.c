/* dala_shell038.c: Dalamadur's meteor scale, the mining point the mining meteor leaves (source of Shattered Omen):
 * literal translation of 4U uShell038 (type 38 of the poster 0x660e88, request 0x6626e8 from uShell029's impact of
 * kinds 3 / 6, dala_meteor.c; init 0xc846c0, per frame 0xc8489c, kill 0xc84920) as a GU uShellEnemy subclass
 * (dala_shell.c). C = read in code, S = strong, G = guess.
 *
 * 4U (C): request {owner, kind 0 / Shah 1 (+0xfd), area (+0x130), &pos (+0x100), yaw (+0x114), ground byte (+0x26c:
 * byte 3 of the meteor's map-test info = the kobj it hit)}. Init: state 1, +0xfc = 1, timer +316 = 1800.0,
 * 0xbdc1f8(this+0x200, 0x102fac4, 2, this, 0) (not traced, not ported), +0x236 |= 1, effect 0xc08698 {0x102faac[kind]
 * = group 35 / 81 element 5 = em024_006 / em110_006, mask all, target this, joint 255} (handle not kept: it goes with
 * its target); with the owner present, alive and not leaving (0x917620) the point 0x9357ec(owner, record 0x102fab4,
 * &pos, area, 0) -> +0x26e (dala_gather.c); then slot 23 once. Per frame (slot 23 0xc8489c): state 2 when the owner
 * is gone / not alive / leaving (0x917620: W+0x140 == 0 or W+0x143 >= 2), when the timer runs out (0x9aad4c), or when
 * 0x6c5e88(stage, area, kobj +0x26c) holds (the kobj's +0xb1 in 3..8 / 10: the floor piece under it breaks). Kill
 * (slot 24 0xc84920, every end): em024_007 / em110_007 (0x102fab0[kind] = {35 / 81, 6}) placed at the position
 * (0xc08628, area +0x130), sound 214 at the position (0x312484) while the owner is alive, the point released
 * (0x5b90c0 + 0x5b9ebc), base kill 0x9ab16c.
 * Port: the point = GU type 2 (mining), icon 0, radius 350, height 200, 1 gather, the meteor list of the quest's rank
 * (dala_gather.c). Effects = PEL records DALA_EFX_SCALE / DALA_EFX_SCALE_END of the owner's PEL (the variant's file,
 * as every Dalamadur shell; kind only logged). Leaving / dead = the owner's unit state (uShell_move calls slot 16 when
 * the owner is gone) or its death actions 11, 14 and 12/255 (S: W+0x143 >= 2 = dead / captured / leaving).
 * Floor piece (deviation, the kobj is unknown: dala_meteor.c passes no info block to GU's map test): the shell probes
 * the ground under its point every frame (map segment y -100 .. +100, mask 16, as the meteor's impact) and ends once
 * none is found, i.e. when a break took the piece's collision away (GU swaps parts 2 * mId - 1 off / 2 * mId on at
 * the break start, dala_stage.c: k00 / k02 leave a plane at y -5000, k01 a floor ~800 lower; 4U 0x6c5e88 holds from
 * the same start, S). Only when the init found ground there (else timer and owner only, logged). G: if GU's map test
 * sees Dalamadur's walk pieces (the same sCollision, dala_walk.c), a scale that landed on the body ends once the body
 * moves away.
 * Multiplayer: per machine, as 4U (no net calls in the shell or the point manager, C); every machine's meteor lands
 * at the synced spot (the action random, dala_meteor.c), so every machine makes the same scale and its own point. */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"
#include "dala_efx.h"
#include "dala_gather.h"

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

#define G_KIND    (DALA_SH_FIELDS + 0x00)   /* u8 0 / Shah 1 [+0xfd] */
#define G_STATE   (DALA_SH_FIELDS + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1], 3 kill run */
#define G_AREA    (DALA_SH_FIELDS + 0x02)   /* u8 request area [+0x130] */
#define G_GROUND  (DALA_SH_FIELDS + 0x03)   /* u8 1 = ground under the point at the init: the floor test runs */
#define G_POINT   (DALA_SH_FIELDS + 0x04)   /* s32 point handle, -1 = none [+0x26e] */
#define G_SERIAL  (DALA_SH_FIELDS + 0x08)
#define G_TIME    (DALA_SH_FIELDS + 0x0c)   /* float timer [+316] */
#define G_EFX     (DALA_SH_FIELDS + 0x10)   /* void * em024_006 (dropped when dead) */
#define G_START   (DALA_SH_FIELDS + 0x14)   /* float[3] request position [+0x100] */
#define G_YAW     (DALA_SH_FIELDS + 0x20)   /* u32 request yaw [+0x114] */
#define G_WHY     (DALA_SH_FIELDS + 0x24)   /* const char * end reason (log) */
#define G_SIZE    (DALA_SH_FIELDS + 0x30)
#define G_LIFE    1800.0f                   /* 4U frames (0xc846d4), paced by the shell's +28 */
#define SND_END   214u                      /* 4U request id, as dala_meteor.c's 213 / 204 */
#define LOG_MAX   40

static dala_shcls_t s_cls;
static uint32_t s_serial, s_log;

/* 4U 0x917620 and the alive test: present, unit state 1 / 2, not in a death action (dala.c half_dead, + capture) */
static int owner_ok(void *owner)
{
    if (!owner || (FIELD(uint32_t, owner, 0xc) & 7) - 1 >= 2) return 0;
    uint32_t cat = FIELD(uint8_t, owner, EN_ACT_CAT), num = FIELD(uint8_t, owner, EN_ACT_NUM);
    return !(cat == 11 || cat == 14 || (cat == 12 && num == 255));
}

/* the floor test standing in for 0x6c5e88 (see the header) */
static int ground_at(void *self)
{
    const float *p = VEC(self, SH_POS);
    float lo[4] = {p[0], p[1] - 100.0f, p[2], 0.0f}, hi[4] = {p[0], p[1] + 100.0f, p[2], 0.0f}, out[4] = {0};
    void *col = COL_MGR;
    return col && (mapSegment(col, lo, hi, FIELD(uint8_t, self, SH_AREA), out, 0, 16, uShell_colFlags(self)) & 17);
}

/* state 2 (4U strb 2, [this, #0xf1]); the next slot 9 runs the kill, as 4U's shell manager */
static void s038_end(void *self, const char *why)
{
    FIELD(const char *, self, G_WHY) = why;
    FIELD(uint8_t, self, G_STATE) = 2;
}

/* 4U slot 23 0xc8489c */
static void s038_step(void *self, void *owner)
{
    if (!owner_ok(owner)) { s038_end(self, "owner gone or dead"); return; }
    if (dala_shell_timer(self, &FIELD(float, self, G_TIME))) { s038_end(self, "1800 frames"); return; }
    if (FIELD(uint8_t, self, G_GROUND) && !ground_at(self)) s038_end(self, "the floor under it broke (no ground)");
}

/* slot 16 = 4U slot 24 0xc84920 (every end; also uShell_move's owner-gone kill): end effect, sound, point, base kill */
static void s038_slot_kill(void *self)
{
    if (FIELD(uint8_t, self, G_STATE) != 3) {
        const char *why = FIELD(const char *, self, G_WHY) ? FIELD(const char *, self, G_WHY) : "killed (owner gone)";
        void *owner = dala_shell_owner(self);
        int live = dala_shell_live(owner);
        const float *pos = VEC(self, SH_POS);
        uint32_t area = FIELD(uint8_t, self, SH_AREA);
        FIELD(uint8_t, self, G_STATE) = 3;
        void *e = live ? dala_efx_post_at(owner, DALA_EFX_SCALE_END, pos, area) : 0;   /* the owner's PEL */
        if (live) dala_snd_pos(owner, SND_END, pos, area);
        dala_gather_free(FIELD(int32_t, self, G_POINT), why);
        FIELD(int32_t, self, G_POINT) = -1;
        void *h = FIELD(void *, self, G_EFX);
        if (dala_efx_alive(h)) dala_efx_stop(h);
        FIELD(void *, self, G_EFX) = 0;
        if (++s_log <= LOG_MAX)
            logf("dalaport: gather scale %u end: %s, %d frames left, end effect %x, sound %u %s",
                 FIELD(uint32_t, self, G_SERIAL), why, (int)FIELD(float, self, G_TIME), (uint32_t)e, SND_END,
                 live ? "posted" : "skipped (no owner)");
    }
    uShell_kill(self);
}

/* slot 79: base set-up + init 0xc846c0 */
static int s038_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint32_t area = FIELD(uint8_t, self, G_AREA);
    FIELD(uint8_t, self, SH_AREA) = (uint8_t)area;
    float *pos = VEC(self, SH_POS), *st = VEC(self, G_START), *p2 = VEC(self, SH_POS2);
    for (int i = 0; i < 3; i++) pos[i] = p2[i] = st[i];
    FIELD(uint32_t, self, SH_ANGLES) = 0;
    FIELD(uint32_t, self, SH_ANGLES + 4) = FIELD(uint32_t, self, G_YAW);
    FIELD(uint32_t, self, SH_ANGLES + 8) = 0;
    FIELD(uint8_t, self, G_STATE) = 1;
    FIELD(float, self, G_TIME) = G_LIFE;
    FIELD(void *, self, G_EFX) = dala_efx_post_on(owner, DALA_EFX_SCALE, self);
    FIELD(uint8_t, self, G_GROUND) = (uint8_t)ground_at(self);
    if (owner_ok(owner))
        FIELD(int32_t, self, G_POINT) = dala_gather_new(owner, DALA_GL_METEOR, DALA_GP_MINING, 0, 350.0f, 200.0f, 1,
                                                        pos, area, "meteor scale");
    if (++s_log <= LOG_MAX)
        logf("dalaport: gather scale %u spawn kind %u at %d %d %d area %u efx %x point %d, floor test %s",
             FIELD(uint32_t, self, G_SERIAL), FIELD(uint8_t, self, G_KIND), (int)pos[0], (int)pos[1], (int)pos[2], area,
             (uint32_t)FIELD(void *, self, G_EFX), FIELD(int32_t, self, G_POINT),
             FIELD(uint8_t, self, G_GROUND) ? "on" : "off (no ground under the point)");
    s038_step(self, owner);                                 /* the init's tail call of slot 23 */
    return 1;
}

/* slot 9 */
static void s038_move(void *self)
{
    if (FIELD(void *, self, G_EFX) && !dala_efx_alive(FIELD(void *, self, G_EFX))) FIELD(void *, self, G_EFX) = 0;
    uShell_move(self);                                      /* owner gone -> slot 16 */
    if (!dala_shell_live(self)) return;
    if (FIELD(uint8_t, self, G_STATE) == 1) s038_step(self, dala_shell_owner(self));
    if (FIELD(uint8_t, self, G_STATE) == 2) VCALL0(self, SLOT_KILL);
}

static void *s038_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls); }
static MtDTI *s038_dti(void *self) { (void)self; return &s_cls.dti; }

/* slot 1: deleted without a kill (area / quest teardown): no point or effect handle outlives the shell */
static void s038_delete(void *self)
{
    if (FIELD(int32_t, self, G_POINT) != -1) dala_gather_free(FIELD(int32_t, self, G_POINT), "scale deleted");
    void *h = FIELD(void *, self, G_EFX);
    if (dala_efx_alive(h)) dala_efx_kill(h);
    FIELD(void *, self, G_EFX) = 0;
    dala_shell_free(&s_cls, self);
}

void *dala_shell038_post(void *owner, uint32_t kind, const float *pos, uint32_t area, uint32_t yaw)
{
    if (kind > 1 || !pos) return 0;
    if (!s_cls.registered)
        dala_shell_register(&s_cls, "uShellDala038", G_SIZE, s038_new, s038_delete, s038_dti, s038_move, s038_setup,
                            s038_slot_kill);
    void *param = dala_shell_param(owner, "meteor scale");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls);
    if (!shell) { dala_shell_param_free(param); return 0; }
    FIELD(uint8_t, shell, G_KIND) = (uint8_t)kind;
    FIELD(uint8_t, shell, G_AREA) = (uint8_t)area;
    FIELD(int32_t, shell, G_POINT) = -1;
    FIELD(uint32_t, shell, G_YAW) = yaw;
    float *st = VEC(shell, G_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    FIELD(uint32_t, shell, G_SERIAL) = ++s_serial;
    return dala_shell_start(shell, param, "meteor scale");
}
