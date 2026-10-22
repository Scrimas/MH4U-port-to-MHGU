/* dala_shell005.c: Dalamadur's tail tremor (goal D5): literal translation of 4U uShell005 (type 5 via 0x661d18; 632 B,
 * vtable 0xe6d4bc: ctor 0xc59944, slot 22 init 0xc59698, slot 23 per frame 0xc598d0) for subtype 4, the one post
 * of the tail (7.0 at motion frame 218, 4U 0x8a064c), as a GU uShellEnemy subclass (dala_shell.c; Gogmazios'
 * em089_shell005.c is the model). C = read in code, S = strong, G = guess.
 *
 * Post (C): 0x661d18(mgr, this, &(-805, 489, -1105, 0), 4, 0xffff, s0 1.0) -> request {byte 0 = 0, owner, byte 8 = 1,
 * subtype, &pos, angles W+424, area W+0x14c, scale, group}: a fixed arena point (the tail's slam spot; camera shake 6
 * at (-1006, 1500, -1105) is em091_act.c's). The callee map's "GU request 0x48c4f0 shell 0x122" is GU's generic
 * request, not a GU uShell005 class: as Gogmazios, our own class on our copy of that request (dala_shell.c).
 * Ctor (owner-posted, Gogmazios C): +0x270 = size factor (0x923fc8 = GU 0xbecf0) * scale; angles = W+424.
 * Init 0xc59698 (C): life +316 = 100; attack 0x9ab120(records 0x1025b58 + 112, volumes 0x1025b58, subtype 4, 7 (5
 * only for 5 / 9 / 13), 2) = record 4: power 0, attack type 19, window 0 + 10, byte 0x1c = 1, volume 22 = capsule
 * on bone 255 (the shell) from (0, 0, 0) to (0, 2292, 0), radius 1077; slot scale +0x17c = +0x270; the stage-16
 * effect is only for subtypes 0 / 11 / 12.
 * Per frame 0xc598d0 (C, Gogmazios): owner gone -> end; life -= dt, end at <= 0; end when the attack slot's active
 * byte drops (window end 10 frames: taken from the record, as em089_shell005.c).
 * Multiplayer: no net test in 7.0 or the class (C); every machine replays 7.0 and posts its own tremor. */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_shell.h"

typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)
typedef float (*size_factor_t)(void *self);
#define sizeFactor           FN(size_factor_t, 0xbecf0)   /* = 4U 0x923fc8 (C, apimap; em089_shell005.c) */
#define SLOT_KILL            16
#define WINDOW_END           10.0f    /* record 4: s16 +0 = 0, s16 +2 = 10 */

#define S_SUB     (DALA_SH_FIELDS + 0x00)   /* u8 [+0xfd] */
#define S_STATE   (DALA_SH_FIELDS + 0x01)
#define S_ARMED   (DALA_SH_FIELDS + 0x02)
#define S_LIFE    (DALA_SH_FIELDS + 0x04)   /* float [+316] */
#define S_SCALE   (DALA_SH_FIELDS + 0x08)   /* float size factor * scale [+0x270] */
#define S_SERIAL  (DALA_SH_FIELDS + 0x0c)
#define S_START   (DALA_SH_FIELDS + 0x10)   /* float[3] request position */
#define SHELL_SIZE (DALA_SH_FIELDS + 0x20)

#define VEC(p, off) (&FIELD(float, p, off))

static dala_shcls_t s_cls;
static uint32_t s_serial;

static void s005_end(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 20) logf("dalaport: tremor %u end: %s", FIELD(uint32_t, self, S_SERIAL), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

static int s005_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2), *st = VEC(self, S_START);
    for (int i = 0; i < 3; i++) p[i] = q[i] = st[i];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, self, SH_ANGLES + 4 * i) = FIELD(uint32_t, rec, REC_ANGLES + 4 * i);
    FIELD(uint8_t, self, S_STATE) = 1;
    FIELD(float, self, S_LIFE) = 100.0f;
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    if (dala_shell_arm(self, DALA_HDS_S005_4, (sub == 5 || sub == 9 || sub == 13) ? 5 : 7, 2, 0xffff))
        FIELD(uint8_t, self, S_ARMED) = 1;
    /* +0x17c = +0x270: the slot scale (times the value GU leaves there after arming, as em089_shell005.c) */
    FIELD(float, self, SH_ATK0 + ATK_F14) = FIELD(float, self, SH_ATK0 + ATK_F14) * FIELD(float, self, S_SCALE);
    static uint32_t s_n;
    if (++s_n <= 20)
        logf("dalaport: tremor %u spawn sub %u hit %u at %d %d %d scale %d/1000", FIELD(uint32_t, self, S_SERIAL), sub,
             FIELD(uint8_t, self, S_ARMED), (int32_t)p[0], (int32_t)p[1], (int32_t)p[2],
             (int32_t)(FIELD(float, self, SH_ATK0 + ATK_F14) * 1000.0f));
    return 1;
}

static void s005_move(void *self)
{
    uShell_move(self);                                      /* owner gone -> kill */
    if (!dala_shell_live(self) || FIELD(uint8_t, self, S_STATE) != 1) return;
    float *life = &FIELD(float, self, S_LIFE);
    *life -= dala_shell_dt(self);
    if (*life <= 0.0f) { s005_end(self, "life out"); return; }
    if (100.0f - *life >= WINDOW_END) s005_end(self, "attack window over");
}

static void *s005_new(MtDTI *dti) { (void)dti; return dala_shell_new(&s_cls); }
static MtDTI *s005_dti(void *self) { (void)self; return &s_cls.dti; }
static void s005_delete(void *self) { dala_shell_free(&s_cls, self); }

void *dala_shell005_post(void *owner, uint32_t subtype, const float *pos, float scale)
{
    if (subtype != 4 || !owner || !pos) {
        static uint32_t s_n;
        if (++s_n <= 10) logf("dalaport: tremor subtype %u has no hit data here (only 4): dropped", subtype);
        return 0;
    }
    if (!s_cls.registered)
        dala_shell_register(&s_cls, "uShellDala005", SHELL_SIZE, s005_new, s005_delete, s005_dti, s005_move, s005_setup, 0);
    void *param = dala_shell_param(owner, "tremor");
    if (!param) return 0;
    void *shell = dala_shell_new(&s_cls);
    if (!shell) { dala_shell_param_free(param); return 0; }
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(float, shell, S_SCALE) = sizeFactor(owner) * scale;   /* ctor 0xc59a20 */
    float *st = VEC(shell, S_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    return dala_shell_start(shell, param, "tremor");
}
