/* uShellEm089Gnd: the generic MH4U ground shell uShell051 (event type 51, posters 0x663d88 / 0x663a60 -> 0x662b44;
 * ctor 0xc90914, init 0xc8fda4, per frame 0xc90048) for the subtypes em089's shells post, as a GU class derived from
 * uShellEnemy with the same framework calls as em089_shell.c (notes/port-checklist.md "Ground shells uShell051").
 *
 * 4U behaviour ported:
 *  - ctor: pos = event pointer +8, angles = event pointer +0xc (blob: zero vector; attack shells: their own angles),
 *    area, owner.
 *  - init: prev = pos, x / z angles cleared (yaw kept); attack 0x9ab120(shell, records 0x1031ca4 + 52 + 40 * subtype,
 *    volumes 0x1031ca4, table 0x1031b28[subtype] = (2, 23 / 31 / 16)) -> our HDS entries 10..19 / HTS groups 4..9
 *    (spheres on bone 255 = the shell, radius 220 / 250 / 214 / 260 / 105 / 175); subtypes 2 / 13 / 15: velocity
 *    (0, 0, 6) rotated by the yaw; 6 / 17 / 19 / 20: timer 58; sound table 0x1031bfc: 3, 9-15 -> id 207 following
 *    the shell (0x304d3c), the blob splashes none.
 *  - per frame: age += dt (2 / 3 / 13 / 14 / 15: the owner's motion step, 0x94460c); age >= 660 -> end; 3 / 9-12 /
 *    13 / 14 / 15 grow the hit-volume scale (4U shell +380 = attack slot 0 + 20 = GU this+0x13bc, the slot scale that
 *    GU slot 80 writes): 3 / 9-12 to 3.4 (+0.024 dt, 3.4 from age 140), 13 / 15 to 3 (+0.02 dt, 3 from age 135),
 *    14 to 3.4 (+0.1 dt, from age 34); 19 / 20 fixed scale 1.2 / 1.5; 13 / 15 move while age < 100; ends: 3 at
 *    220, 13 at 155, 14 at 120, 15 at 142; 6 / 17 / 19 / 20: at timer 58 -> sound 220 at the position (this replaces
 *    em089_snd_splash's delay queue: the splash plays it itself, only while it lives).
 *  - the attack windows come from the HDS records (s16 +0 start / +2 length: blob splash 8..208, puddles 58..78,
 *    explosions 0..160..172, scorch 0..142 / 155, finale 0..220).
 *  - end 0xc906d8 (vtable slot 24, see s051_end): follow-up uShell051 4 / 5 / 8 / 18 at the shell position + camera
 *    shake; 16 / 17: an enemy item drop. The follow-ups (HDS entries 21..24 / HTS groups 11..14: power 100 / 80 /
 *    80 / 80, attack type 3, spheres radius 300 / 562.5 / 500 / 560, windows 0..88 / 20 / 15 / 20) have no velocity
 *    or timer; init: sound 208 at the position (table 0x1031bfc type 2 -> 0xc8ffe4, 0x312484); per frame they only
 *    grow the scale (jump table 0xc900b8): 4 to 7 (+0.35 dt, 7 from age 20, 0xc9025c), 5 / 18 to 2 (+0.33 dt, from
 *    age 6, 0xc90330), 8 to 1.8 (+0.3 dt, from age 6, 0xc90368); they end at age 660 and post nothing themselves.
 * Effects (0xc904d0): see s051_slot_kill below (effects agent).
 * Not ported: the area check 0x6c5e88 (1 / 6 / 16 / 17 / 19 / 20 end when it is non-zero; stage-object state),
 * the material byte. */
#include "game.h"
#include "util.h"
#include "em089_shell051.h"
#include "em089_snd.h"
#include "em089_efx.h"
#include "em089.h"

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
#define SHELL_MGR            (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR             (*(void **)MAIN(0x2126f48))
#define DTI_PARAM            ((MtDTI *)MAIN(0x188cb88))
#define VT_PARAM             MAIN(0x17556a0)
#define ZERO_VEC             MAIN(0x191e850)
/* camera shake at a position: 4U 0xbfe98c(mgr, owner, id, pos) = GU 0x49eac(owner, id, pos, 0) (as em089_shell016.c) */
typedef void (*cam_shake_pos_t)(void *owner, uint32_t id, const float *pos, uint32_t zero);
#define camShakePos          FN(cam_shake_pos_t, 0x49eac)
typedef uint32_t (*player_area_t)(void);
#define playerArea           FN(player_area_t, 0x4971c)
/* enemy item drop at a position: 4U 0x911f58(enemy, pos, chance %, 0) = GU 0xac0ec (same argument list: rand % 100
 * against the chance, remaining-drop counter 4U W+0x7a64 = GU rec+0x5d54, returns 1 when it dropped) */
typedef int (*enemy_drop_t)(void *enemy, const float *pos, uint32_t chance, uint32_t zero);
#define enemyDrop            FN(enemy_drop_t, 0xac0ec)
#define SHELL_MAX_LIVE   144
#define SHELL_LIVE_LIST  0x6d8c
#define SLOT_KILL        16
#define SLOT_MOVE        9
#define SLOT_SETUP       79
#define SLOT_ARM_ATTACK  80
#define SH_POS           0x40
#define SH_POS2          0x1000
#define SH_ANGLES        0xfe8
#define SH_DT            28
#define SH_AREA          0x1054
#define SH_ATK0_SCALE    0x13bc   /* attack slot 0 + 0x14: volume scale [4U shell +380 = slot +20] */
#define REC_MOT_SPEED    0x398

#ifndef EM089_SHELL_FILE
#define EM089_SHELL_FILE 0x1071du
#endif
#define EM089_SHELL_ID   175u

#define S_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)
#define S_ARMED   (SIZE_uShellEnemy + 0x02)
#define S_AGE     (SIZE_uShellEnemy + 0x04)   /* float [+316] */
#define S_SCALE   (SIZE_uShellEnemy + 0x08)   /* float 4U slot scale [+380] */
#define S_BASE    (SIZE_uShellEnemy + 0x0c)   /* float GU slot scale after arming (multiplied by S_SCALE) */
#define S_VEL     (SIZE_uShellEnemy + 0x10)   /* float[3] [+320] */
#define S_TIMER   (SIZE_uShellEnemy + 0x1c)   /* float [+652] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x20)
#define S_EFX     (SIZE_uShellEnemy + 0x24)   /* effect handle [+0x290] (effects agent) */
#define S_DYING   (SIZE_uShellEnemy + 0x28)   /* u8 1 = killed, waiting for the effect (as em089_shell.c) */
#define S_DIE_T   (SIZE_uShellEnemy + 0x2c)   /* float frames spent waiting */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x30)
#define EFX_DIE_MAX 300.0f
#define uShell_kill          FN(shell_fn_t, 0x4a247c)     /* base slot 16 */

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;
static uint32_t s_serial;

#define VEC(p, off) (&FIELD(float, p, off))

/* subtype -> HDS entry (4U record = subtype), slot-80 argument (table 0x1031b28 byte 1), end of the attack window =
 * record s16 +0 start + s16 +2 length: 4U's attack object (shell +0x168, update 0xb6ff88) counts both down and clears
 * its active byte +5 = shell +0x16d (0xb700a8), and the per frame 0xc9008c ends the shell when that byte is 0 */
typedef struct { uint8_t sub, hds, arg, end; } s051_t;
static const s051_t k_sub[] = {
    {1, 10, 23, 208}, {3, 11, 31, 220}, {6, 12, 31, 78}, {9, 13, 31, 160}, {10, 14, 31, 160}, {11, 15, 31, 165},
    {12, 16, 31, 172}, {13, 17, 31, 155}, {14, 18, 16, 220}, {15, 19, 31, 142}, {16, 10, 23, 208}, {17, 12, 31, 78},
    {19, 12, 31, 78}, {20, 12, 31, 78},
    {4, 21, 31, 88}, {5, 22, 31, 20}, {8, 23, 31, 15}, {18, 24, 31, 20},     /* end posts of 0xc906d8 */
};

static const s051_t *sub_info(uint32_t sub)
{
    for (uint32_t i = 0; i < sizeof k_sub / sizeof k_sub[0]; i++)
        if (k_sub[i].sub == sub) return &k_sub[i];
    return 0;
}

static int moves_with_owner(uint32_t sub) { return sub == 2 || sub == 3 || sub == 13 || sub == 14 || sub == 15; }
static int is_puddle(uint32_t sub) { return sub == 6 || sub == 17 || sub == 19 || sub == 20; }

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }

static void *s051_owner(void *self) { return *(void **)(FIELD(uint8_t *, self, 0x136c) + 0xc); }

/* 4U end 0xc906d8 = vtable slot 24, run by the base move 0x9aae2c once the per frame set state +0xf1 = 2 (or the
 * base alive flag +0x16d dropped). Switch on subtype - 2 < 16: a follow-up uShell051 0x6635e8(mgr, owner, sub,
 * shell +0x100, [sp] area +0x130, [sp+4] 0xffff) (-> 0x662b44, event angles = zero vector) and, with an owner whose
 * area W+0x14c is the player's (global +0xc90), camera shake 0xbfe98c(mgr, owner, id, shell +0x100):
 *   2 / 13 / 15 -> sub 4, shake 4;  3 -> sub 5, shake 4;  14 -> sub 18, shake 7;  7 / 9 / 10 / 11 / 12 -> sub 8,
 *   shake 7;  16 / 17 [0xc908b0] (owner only): work T+0xed = 1 (T = owner+0x8d88, the drip helper's rare-drip flag;
 *   read by the item drop's table choice: set 1 = the shiny table, em089_drop_set) and the item drop
 *   0x911f58(owner, shell +0x100, 100, 0);  others: nothing.
 * Then all paths 0x9ab16c (kill) + finish the effect +0x290 (0xc470dc) = our kill slot (s051_slot_kill).
 * Not ported: 4U still posts after the base move dropped a
 * dead owner (+0x134 = 0, no shake / drop), ours needs the owner (s051_move stops without one). The follow-up posts
 * from inside this shell's move, like em089_shell016.c does; it never ends in the same frame (no recursion). */
static void s051_end(void *self)
{
    static uint32_t s_n;
    void *owner = s051_owner(self);
    if (!owner) return;
    uint32_t sub = FIELD(uint8_t, self, S_SUB), next, shake;
    const float *p = VEC(self, SH_POS);
    switch (sub) {
    case 2: case 13: case 15:                         next = 4;  shake = 4; break;   /* 0xc90740 */
    case 3:                                           next = 5;  shake = 4; break;   /* 0xc9078c */
    case 14:                                          next = 18; shake = 7; break;   /* 0xc907f8 */
    case 7: case 9: case 10: case 11: case 12:        next = 8;  shake = 7; break;   /* 0xc90844 */
    case 16: case 17: {                                                              /* 0xc908b0 */
        em089_set_drop_flag(owner, 1);
        int got = enemyDrop(owner, p, 100, 0);
        if (++s_n <= 40) logf("gogport: em089 ground shell %u (sub %u) end: item drop at %d %d %d -> %d",
                              FIELD(uint32_t, self, S_SERIAL), sub, (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], got);
        return;
    }
    default:
        return;
    }
    void *sh = em089_shell051_post(owner, next, p, 0);
    uint32_t in_area = FIELD(uint8_t, owner, SH_AREA) == playerArea();
    if (in_area) camShakePos(owner, shake, p, 0);
    if (++s_n <= 40) logf("gogport: em089 ground shell %u (sub %u) end: post sub %u -> %x at %d %d %d, shake %u%s",
                          FIELD(uint32_t, self, S_SERIAL), sub, next, (uint32_t)sh, (int32_t)p[0], (int32_t)p[1],
                          (int32_t)p[2], shake, in_area ? "" : " (other area: none)");
}

static void s051_kill(void *self, const char *why)
{
    static uint32_t s_n;
    if (++s_n <= 40) logf("gogport: em089 ground shell %u (sub %u) end: %s", FIELD(uint32_t, self, S_SERIAL),
                          FIELD(uint8_t, self, S_SUB), why);
    FIELD(uint8_t, self, S_STATE) = 2;
    s051_end(self);                                          /* 0xc906d8, then its kill + effect finish */
    VCALL0(self, SLOT_KILL);
}

/* effects (effects agent). 4U 0xc904d0 (end of the init): effect manager 0xc08628 with table 0x1031b54[subtype] =
 * {group 65, file, mask} (1 / 16 em089_002, 3 / 9-12 / 14 em089_015, 6 / 17 / 19 / 20 em089_008, 13 / 15 em089_013,
 * mask -1), scale table 0x1032020 (9-12 0.5, 14 0.7, 19 1.2, 20 1.5, else 1), at the shell position with its angles
 * (yaw only, x / z cleared), not attached; handle +0x290 dropped when dead (0xc90418), finished by the kill slot
 * (0xc906d8 -> 0xc470dc). GU: PEL 5100 + subtype (scale baked, tools/efl4u2gu.py) posted with THIS shell as attach
 * target (em089_efx_post_on = GU shells' own post 0x4a1d34: target = unit vt+0x130, flags 3, the unit's position).
 * Test 4: posted on the owner at the position, the heaps / explosions came out far too big and floated during the
 * 1800 hover: the owner's attach model (2.5 model scale, hover height) was the reference. Deviation: the effect now
 * follows the shell, so the moving 2 / 13 / 15 carry it (4U leaves it where it was posted). The effect reads its
 * target every frame, so slot 16 keeps the shell until the effect is dead (em089_shell.c pattern). Not mapped: the
 * material byte +0x274 (desc +0x18), the subtype-14 / 18 effect field +256 (2.0 / 1.25). */
static void s051_slot_kill(void *self)   /* slot 16: stop the effect, base kill once it is dead */
{
    void *h = FIELD(void *, self, S_EFX);
    if (h && !em089_efx_alive(h)) FIELD(void *, self, S_EFX) = h = 0;
    if (!h) { FIELD(uint8_t, self, S_DYING) = 0; uShell_kill(self); return; }
    if (FIELD(uint8_t, self, S_DYING)) return;
    FIELD(uint8_t, self, S_DYING) = 1;
    FIELD(uint8_t, self, S_STATE) = 2;
    FIELD(float, self, S_DIE_T) = 0.0f;
    FIELD(uint8_t, self, 0x13ae) = 255; FIELD(uint8_t, self, 0x13ad) = 0;   /* 0x4a247c: attack slots off */
    FIELD(uint8_t, self, 0x1466) = 255; FIELD(uint8_t, self, 0x1465) = 0;
    FIELD(uint8_t, self, 0x151e) = 255; FIELD(uint8_t, self, 0x151d) = 0;
    em089_efx_stop(h);
}

/* per frame while S_DYING: base kill once the effect is dead (forced after EFX_DIE_MAX frames) */
static void s051_dying(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    float *t = &FIELD(float, self, S_DIE_T);
    *t += FIELD(float, self, SH_DT);
    if (h && em089_efx_alive(h) && *t >= EFX_DIE_MAX && *t < EFX_DIE_MAX + 1000.0f) {
        em089_efx_kill(h);
        *t = EFX_DIE_MAX + 1000.0f;           /* one more frame for the effect's own kill, then the shell goes */
        return;
    }
    if (h && em089_efx_alive(h) && *t < EFX_DIE_MAX + 1000.0f + 30.0f) return;
    FIELD(void *, self, S_EFX) = 0;
    FIELD(uint8_t, self, S_DYING) = 0;
    uShell_kill(self);
}

static void s051_apply_scale(void *self)
{
    FIELD(float, self, SH_ATK0_SCALE) = FIELD(float, self, S_BASE) * FIELD(float, self, S_SCALE);
}

/* slot 79: base setup + 4U init 0xc8fda4 */
static int s051_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    const s051_t *k = sub_info(sub);
    FIELD(uint8_t, self, S_STATE) = 1;
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    q[0] = p[0]; q[1] = p[1]; q[2] = p[2];
    if (uShell_hasHitData(self) == 1) {
        typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
        arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
        arm(self, 0, k->hds, -1, k->arg, 2, 0xffff, FIELD(float, self, SH_ATK0_SCALE));
        FIELD(uint8_t, self, S_ARMED) = 1;
    }
    FIELD(float, self, S_BASE) = FIELD(float, self, SH_ATK0_SCALE);
    FIELD(float, self, S_SCALE) = sub == 19 ? 1.2f : sub == 20 ? 1.5f : 1.0f;
    s051_apply_scale(self);
    if (sub == 2 || sub == 13 || sub == 15) {               /* (0, 0, 6) rotated by the yaw (x / z cleared) */
        float a = ang_rad(FIELD(uint32_t, self, SH_ANGLES + 4));
        float *v = VEC(self, S_VEL);
        v[0] = 6.0f * sinf_gu(a); v[1] = 0.0f; v[2] = 6.0f * cosf_gu(a);
    }
    if (is_puddle(sub)) FIELD(float, self, S_TIMER) = 58.0f;
    if (sub == 3 || (sub >= 9 && sub <= 15)) em089_snd_obj(owner, 207, self, FIELD(uint8_t, self, SH_AREA));
    else if (sub == 4 || sub == 5 || sub == 8 || sub == 18)  /* 0xc8ffe4: 208 at the position (0x312484) */
        em089_snd_pos(owner, 208, p, FIELD(uint8_t, self, SH_AREA));
    FIELD(void *, self, S_EFX) = em089_efx_post_on(owner, EM089_EFX_S051 + sub, self);   /* 0xc904d0 */
    {   /* test 5: transform scale / position of the shell-attached effect (eff +0x150 = transform, +0x60 scale) */
        static uint32_t s_x;
        void *e = FIELD(void *, self, S_EFX), *xf = e ? FIELD(void *, e, 0x150) : 0;
        if (xf && ++s_x <= 8)
            logf("gogport: em089 ground shell sub %u effect scale x1000 %d %d %d pos %d %d %d", sub,
                 (int32_t)(FIELD(float, xf, 0x60) * 1000.0f), (int32_t)(FIELD(float, xf, 0x64) * 1000.0f),
                 (int32_t)(FIELD(float, xf, 0x68) * 1000.0f), (int32_t)FIELD(float, xf, 0x40),
                 (int32_t)FIELD(float, xf, 0x44), (int32_t)FIELD(float, xf, 0x48));
    }
    static uint32_t s_n;
    if (++s_n <= 60)
        logf("gogport: em089 ground shell %u spawn sub %u hds %u hit %u at %d %d %d (scale %d/1000)",
             FIELD(uint32_t, self, S_SERIAL), sub, k->hds, FIELD(uint8_t, self, S_ARMED), (int32_t)p[0], (int32_t)p[1],
             (int32_t)p[2], (int32_t)(FIELD(float, self, SH_ATK0_SCALE) * 1000.0f));
    return 1;
}

/* grow the 4U scale toward cap: past age `full` -> cap, else += rate * dt (capped) */
static void grow(void *self, float age, float full, float rate, float cap, float dt)
{
    float *s = &FIELD(float, self, S_SCALE);
    if (age > full) *s = cap;
    else { *s += dt * rate; if (*s > cap) *s = cap; }
}

/* slot 9 = 4U 0xc90048 */
static void s051_move(void *self)
{
    if (FIELD(uint8_t, self, S_DYING)) { s051_dying(self); return; }
    uShell_move(self);
    if (FIELD(void *, self, S_EFX) && !em089_efx_alive(FIELD(void *, self, S_EFX))) FIELD(void *, self, S_EFX) = 0;
    if (FIELD(uint8_t, self, S_STATE) != 1 || (FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    void *owner = s051_owner(self);
    if (!owner) return;
    uint32_t sub = FIELD(uint8_t, self, S_SUB);
    float dt = FIELD(float, self, SH_DT);
    float *age = &FIELD(float, self, S_AGE);
    if (moves_with_owner(sub))
        *age += FIELD(float, FIELD(uint8_t *, owner, EN_RECORD), REC_MOT_SPEED) * FIELD(float, owner, EN_DT);
    else *age += dt;
    if (*age >= 660.0f) { s051_kill(self, "age 660"); return; }
    {   /* 4U +0x16d == 0: the attack window is over (counted with the same step as the age here) */
        const s051_t *k = sub_info(sub);
        if (k && *age >= (float)k->end) { s051_kill(self, "attack window end"); return; }
    }
    float a = *age;
    switch (sub) {
    case 3: case 9: case 10: case 11: case 12:
        if (sub == 3 && a >= 220.0f) { s051_kill(self, "age 220"); return; }
        grow(self, a, 140.0f, 0.024f, 3.4f, dt);
        break;
    case 13: case 15:
        grow(self, a, 135.0f, 0.02f, 3.0f, dt);
        if (a < 100.0f) {                                    /* 0x9ab05c: pos += vel * dt */
            float *p = VEC(self, SH_POS), *v = VEC(self, S_VEL);
            for (int i = 0; i < 3; i++) p[i] += v[i] * dt;
        }
        if (a >= (sub == 13 ? 155.0f : 142.0f)) { s051_kill(self, "life out"); return; }
        break;
    case 14:
        if (a >= 120.0f) { s051_kill(self, "age 120"); return; }
        grow(self, a, 34.0f, 0.1f, 3.4f, dt);
        break;
    case 4:                                                  /* 0xc9025c (end post of 2 / 13 / 15) */
        grow(self, a, 20.0f, 0.35f, 7.0f, dt);
        break;
    case 5: case 18:                                         /* 0xc90330 (end posts of 3 / 14) */
        grow(self, a, 6.0f, 0.33f, 2.0f, dt);
        break;
    case 8:                                                  /* 0xc90368 (end post of 7 / 9-12) */
        grow(self, a, 6.0f, 0.3f, 1.8f, dt);
        break;
    default:
        break;
    }
    s051_apply_scale(self);
    float *p = VEC(self, SH_POS), *q = VEC(self, SH_POS2);
    q[0] = p[0]; q[1] = p[1]; q[2] = p[2];
    if (is_puddle(sub)) {                                    /* 0xc903a4: sound 220 at timer 58 */
        float *t = &FIELD(float, self, S_TIMER);
        if (*t >= 0.0f) {
            *t -= dt;
            if (*t <= 0.0f) {
                *t = -1.0f;
                em089_snd_pos(owner, 220, p, FIELD(uint8_t, self, SH_AREA));
            }
        }
    }
}

static void *s051_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static void s051_delete(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (em089_efx_alive(h)) em089_efx_kill(h);   /* attached to us: deleted without our kill (area / quest teardown) */
    FIELD(void *, self, S_EFX) = 0;
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *s051_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void s051_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&s051_delete;
    s_vt[2 + 5] = (uint32_t)&s051_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&s051_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&s051_setup;
    s_vt[2 + SLOT_KILL] = (uint32_t)&s051_slot_kill;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&s051_new;
    MtDTI_ctor(&s_dti, "uShellEm089Gnd", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("gogport: uShellEm089Gnd DTI %x id %x size %x", (uint32_t)&s_dti, s_dti.w[7], SHELL_SIZE);
}

void *em089_shell051_post(void *owner, uint32_t subtype, const float *pos, uint32_t yaw)
{
    static uint32_t s_fail;
    const s051_t *k = sub_info(subtype);
    if (!s_registered) s051_register();
    uint8_t *mgr = SHELL_MGR;
    if (!owner || !k || !mgr || !pos) {
        if (++s_fail <= 20) logf("gogport: em089 ground shell dropped (owner %x sub %u mgr %x)", (uint32_t)owner,
                                 subtype, (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("gogport: em089 ground shell dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = EM089_SHELL_ID;
    FIELD(void *, param, 0xc) = owner;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = s051_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    FIELD(uint8_t, shell, S_SUB) = (uint8_t)subtype;
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    float *p = VEC(shell, SH_POS);
    p[0] = pos[0]; p[1] = pos[1]; p[2] = pos[2];
    FIELD(uint32_t, shell, SH_ANGLES) = 0;
    FIELD(uint32_t, shell, SH_ANGLES + 4) = yaw & 0xffff;
    FIELD(uint32_t, shell, SH_ANGLES + 8) = 0;
    uShell_setResource(shell, fileResource(0, EM089_SHELL_FILE));
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        if (++s_fail <= 20) logf("gogport: em089 ground shell setup failed (owner type %u)", FIELD(uint8_t, owner, 0x1052));
        s051_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
