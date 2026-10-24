/* Battlequarters alias: the 4U Demolisher, the gate cannon m19a03d-a00 behind the south wall (notes/stage.md,
 * "Demolisher").
 *
 * 4U (traced, C; stage logic `this`):
 *  - trigger: a hunter USES Dense Marcoal (4U items 1730 / 1917 / 1935, item use 0xb282ec -> 0xb28e44) in the cart's
 *    fire-point record (kind 31, cart-relative (0, 165, -105), radius 150) -> player action 170 (the shared switch
 *    body 0xb5b2a0, motion 0x20f) -> 0x5ba3cc -> 0x6b93b0 type 5 (0x6b958c), when 0x6b56e4 allows it: the cart
 *    parked at S (idle after 44 / 50 / 51), no fire since the last re-arm (+0xdce8, bit 0x10000), flags & 0x18 clear.
 *  - fire 0x6b958c: gimmick camera 0xc01d64(cam, 6) for the local hunter (table 0xf2d440 record 6: eye (2325,
 *    3390, -8790), target (0, 1880, -5300), fov 50, 372 frames), KowareObj (area 3, mId 2) command 36 = action 53
 *    (raise, frames 0..150) via 0x6c3400, +0xdce4 = 0 (shot pending), +0xdce6 = the player, +0x38 |= 0x10000,
 *    +0xdce8 = the quest countdown.
 *  - per frame 0x6b985c: gate kobj (0x6c4064(this, 22)) idle after action 53 and +0xdce4 == 0 -> uShell022 kind 9
 *    (0x662238: owner = the player of +0xdce6, area 3), then +0xdce4 = +0xdce6 = -1. Gate idle after action 55 (or
 *    at 255) with bit 0x10000 -> HUD 0x5aa0f0(20) "The Demolisher is ready for use." and the bit cleared; fps * 600
 *    frames of countdown after the fire -> command 38 = action 55 (re-arm) [0x6b9de8..0x6b9e90].
 *  - uShell022 kind 9 (init 0xc75500 / 0xc75904, update 0xc74b78): start = gate model matrix * (0, 0, 2230) + model
 *    position, angles = the model's rotation; launch (0, -1.5, 108) per frame in that frame, gravity -1.8; at launch
 *    it sends the gate command 37 = action 54 (fire, quake 9, barrel recoil); effects m19a03_006 (launch), _012
 *    (trail), _007 (impact), explosion attack record 31 (0x9ab120), SE 316.
 * Port (user's rule, 2026-10-23 evening: no item, ONE use per quest: 4U's Dense Marcoal is not in the box at the
 * start; an item version through GU's own Marcoal path (kind-29 record, ready 0x5048e8, switch type 5 0x5048fc,
 * camera 0x50491c; notes/stage.md section 15) was built but never reached in a test and is removed):
 *  - gate scheduler: tools/stage4u2gu.py GATE_KOWARE ships the converted m19a03d-a00 as m26a03d-k02 (file 0xc134);
 *    created here at stage load (stage_cannon.c's stage_kobj_extra hook) with 0x500bb4(mgr, area 2, slot 6, file).
 *  - prompt: a kind-11 record (GU's Dragonator switch prompt and motion, as the floor cannons) at the cart's fire point
 *    at S, radius 150 / height 100 (the cart's own fire-point record; its kind-26 cart shot is off at S, stage_cart.c);
 *    stage_cannon.c's 0x503b88 / 0x503bb0 hooks ask stage_demolisher_ready / stage_demolisher_fire first. Usable
 *    with 4U's 0x6b56e4 conditions: the cart parked at S (reachable once the doors are open), the gate idle.
 *  - fire: 4U record 6 camera (stage_gimmick_camera), action 53, then the shot when action 53 has ended. No re-arm.
 *  - shot: GU's Demolisher shell uShellPlcom_011 (shell type 31, the Fortress st007's shot) = Capcom's port of
 *    uShell022 kind 9 (C): mode 0 = same launch speed 108 along the barrel, gravity -1.8 (+0x1024), 20-frame wait
 *    before the launch (0x4668a8, 4U state 1 timer 20), SE 316 at launch and 323 at the impact (0x467074, 4U
 *    0xc75344), explosion HDS 0 power 2500 / HTS 0 radius 1000 (4U 0x102c9b0 / 0x102cbb8: 2500, radius 1000; type 74
 *    for 4U 68 = Capcom's renumbering, as the cannon's 75 for 64). Posted as st007 does (0x4981c0: param 0x4660b4(24,
 *    16) {vt 0x175fae0 + 8, 31, mode 0, player, 0, st007}); with no st007 (+0x14 = 0) its setup 0x466124 takes the
 *    owner's position, then the hooks put 4U's values in:
 *    stage_demolisher_pose @0x466618 (end of the mode-0 init case of 0x4664f0, r4 = shell, before the state step):
 *      4U 0xc75904 start: gate model position (0, 2200, -8110) + M * (0, 0, 2230), angles = the model's (-0.261799
 *      rad = the m19a03d-a00 mRot key at frame 150, the end of action 53; yaw / roll 0) -> pitch u16 0xf556
 *      (truncated as 0xc759c0); 4U 0xc74cec velocity (0, -1.5, 108) rotated by pitch then yaw (GU: -1.25; GU's own
 *      start = st007 matrix * (0, 65, 2230)).
 *    stage_demolisher_efx @0x466b9c (the shell's effect post, r1 = 0 launch / 1, 2 impact): 4U's effects instead of
 *      pl_com_011's (GU's own cm060 / cm072 / cm073 set, not conversions of 4U's): launch m19a03_006 at the muzzle with
 *      the barrel rotation + m19a03_012 trail on the shell (4U 0xc74e98, handle +0x288) + gate action 54 (4U command
 *      37, 0xc74e38); impact m19a03_007 at the hit point (0xc75144), trail stopped and kept in +0x15a4 so the shell's
 *      end state (0x466684) waits for it, as GU's own trail.
 * Deviations: no Dense Marcoal (user's rule), one use per quest, no re-arm (4U: 10 min, action 55, QDialog 20); GU's
 * switch motion 0x7df for 4U's 0x20f; 4U's 0x6b9f84 object test not ported; online, every machine
 * runs the replayed switch press (each posts its own shot, as the floor cannons); 4U's in-flight hit (0xc74f94: HDS
 * 0x102c920 power 2500 type 67, HTS radius 500 set at 0xc74ce8) is absent: GU mode 0 only attacks in the explosion
 * (pl_com_011 has no such record); 4U's impact check on em089 (0xc75270: target em 89 and stage byte +0x1838 == 1
 * -> 0x6b27d4 or byte = 2) not traced / not ported.
 * Define STAGE_DEMOLISHER_OFF: no scheduler, record or driver. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089_efx.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

int stage_alias_active(void);        /* stage.c */
uint32_t stage_setup_serial(void);   /* stage.c */
int stage_cart_parked_at(uint32_t station);   /* stage_cart.c */
int stage_doors_opened(void);        /* stage_doors.c */
int stage_gimmick_camera(void *mgr, float *rec, float frames);   /* stage_gimmick.c */

#define STAGE_GIMMICK_MGR 0x18977a0u
#define MGR_KOBJ          0x21cu
#define KOBJ_AREA         0x182u
#define KOBJ_STATUS       0x184u
#define KOBJ_ACT          0x185u
#define KOBJ_ID           0x188u
#define ARENA_AREA        2u
#define KOBJ_TYPE         0x189u      /* u8 mType */
#define GATE_TYPE         22u         /* 4U's Demolisher gate type; mId 6 in our k02 (tools/stage4u2gu.py GATE_MID) */
#define GATE_FILE_ID      0xc134u     /* stage\m26d\m26a03d\sdl\m26a03d-k02 = converted 4U m19a03d-a00 */
#define GATE_SLOT         6u          /* mgr+0x1bc + 4 * slot (0x4fe9c0: 1..4, s04: 5), freed by 0x4ff074 */
#define ACT_RAISE         53u
#define ACT_FIRE          54u
#define ACT_LOWER         55u
#define STATION_S         2u
/* The gate's actions (4U a00 action list = the converted k02: 53 frames 0..150, 54 150..400 quake 9, 55 400..700)
 * play through GU's KowareObj (0x515328 -> status 3, start 0x513d3c finds the id in the action list, 6 / 7 while
 * playing, the end path sets 2 and keeps the id for ids > 39; quake / SE come with it). Tests 20:37 / 20:59 drove
 * the BREAKABLE m26a02d-k02 instead (also area 2 / mId 2, created first): no action 53 in its list -> closed at
 * once (0x51479c), and an idle kobj's scheduler is not evaluated (0x513508 clears its +0xc bit 0x400), so frame
 * writes did nothing (gate helper gu8, C). */
typedef void (*kobj_play_t)(void *kobj, uint32_t id, uint32_t a, uint32_t b, uint32_t c);
#define kobj_play FN(kobj_play_t, 0x515328)
#define RAISE_WAIT        600.0f      /* time units a raise may take before the shot goes anyway (logged) */
/* Time base (helper gu10, C): both games advance units by delta = real seconds * 60 (4U [0x1057194]+0x5c, GU
 * [0x2126764]+0x68 = elapsed * 60.0 (+0x38); unit +0x1c = it * line scale): 2 per frame at 30 fps, 0.5 at 120. 4U
 * frame counts, per-frame velocities and gravity port 1:1; our own waits count this delta, not ticks. */
#define GAME_PTR          0x2126764u
#define GAME_DELTA        0x68u
/* 4U uShell022 state 1 (0xc74d6c): the shell waits until its timer +0x278 (+= delta, 0x9a95c0) reaches 20 before
 * the launch. GU uShellPlcom_011 runs its 20-unit wait (0x4668a8) only when the spawn byte ([+0x136c]+8) is 1, and
 * mode 0 is chosen only when it is 0 (0x4664c8): GU's shot launches on its first update (test 08:43: 7 ms after the
 * post). The shell has no model in either game (4U 0xc75520 skips it for kind 9), so the wait is invisible: the
 * post itself is delayed by 20 units. */
#define LAUNCH_WAIT       20.0f
typedef void *(*sched_create_t)(void *mgr, uint32_t area, uint32_t slot, uint32_t file_id, uint32_t play, uint32_t z);
#define sched_create FN(sched_create_t, 0x500bb4)

/* 4U's use spot: the cart's fire-point record (4U kind 31 = GU st006 kind 26, cart-relative (0, 165, -105), radius
 * 150, 0x5ba4e0) with the cart parked at S (4U s00 keys at frames 3950 / 13450: (0, 1700, -5210), yaw 0) */
static const float k_fire_pt[3] = {0.0f, 1865.0f, -5315.0f};
#define FIRE_RADIUS       150.0f
#define FIRE_HEIGHT       100.0f      /* st006's records: 0x495ab4 */

/* The prompt: an interaction record of kind 11 (GU's Dragonator switch, as the floor cannons: stage_cannon.c's
 * 0x503b88 / 0x503bb0 hooks ask stage_demolisher_ready / stage_demolisher_fire first). Fields as st006's own records
 * (0x495a8c..0x495b0c); in-range test 0x319278: +0x44 = horizontal radius, +0x48 = height (|dy| < h / 2); the
 * per-frame cache 0x31a348 keeps the last in-range active record per kind for the local hunter. */
#define INTER_MGR         0x1889ec0u
typedef uint8_t *(*rec_alloc_t)(void *mgr);
#define rec_alloc FN(rec_alloc_t, 0x31aa6c)
typedef void (*rec_area_t)(void *rec, uint32_t area);
#define rec_area FN(rec_area_t, 0x3191a0)
typedef void (*rec_flag_t)(void *rec, uint32_t v);
#define rec_flag FN(rec_flag_t, 0x3191d8)
typedef void (*rec_reg_t)(void *mgr, void *rec, uint32_t z);
#define rec_register FN(rec_reg_t, 0x31abac)
typedef void (*rec_free_t)(void *mgr, void *rec);
#define rec_free FN(rec_free_t, 0x31aaf4)
#define KIND_SWITCH       11u

/* GU camera record layout (fov, pad x3, eye, target, up) <- 4U 0xf2d440 record 6 (static init 0xd48f90 +192 / +204,
 * fov / duration in .data) */
static float s_cam6[16] __attribute__((aligned(16))) = {
    50.0f, 0.0f, 0.0f, 0.0f,
    2325.0f, 3390.0f, -8790.0f, 0.0f,
    0.0f, 1880.0f, -5300.0f, 0.0f,
    0.0f, 1.0f, 0.0f, 0.0f,
};
#define CAM6_FRAMES       372.0f

#define SHELL_MGR         0x1892550u
typedef uint8_t *(*param_alloc_t)(uint32_t size, uint32_t align);
#define param_alloc FN(param_alloc_t, 0x4660b4)   /* st007 0x4981d4 */
typedef void (*shell_post_t)(void *mgr, void *param);
#define shell_post FN(shell_post_t, 0x48c4f0)
#define VT_PARAM_011      0x175fae0u  /* +8 = vtable (0x4981fc) */
#define SHELL_PL_COM_011  31u
#define SH_POS            0x40u
#define SH_PREV           0x1000u     /* previous position (0x466464) */
#define SH_PITCH          0xfe8u
#define SH_YAW            0xfecu
#define SH_ROLL           0xff0u
#define SH_VEL            0x1010u
#define SH_EFX            0x15a4u     /* trail effect handle, the end state waits for it (0x466684) */
#define ACT_FIRE_DONE     90.0f       /* frames a posted shot may take to initialise (as stage_cannon.c) */
/* 4U 0xc75904 with the m19a03d-a00 model after action 53: position (mOffset), pitch (mRot x key at frame 150) */
static const float k_gate_pos[3] = {0.0f, 2200.0f, -8110.0f};
#define GATE_PITCH        (-0.26179900765419006f)
#define MUZZLE            2230.0f     /* 0xc75a28 */
#define VY0               (-1.5f)     /* 0xc74f14 */
#define VZ0               108.0f      /* 0xc74f18 */
#define TRAIL_EFL         12u         /* m19a03_012 */
#define LAUNCH_EFL        6u          /* m19a03_006 */
#define IMPACT_EFL        7u          /* m19a03_007 */

static struct {
    uint32_t serial;
    uint8_t fired;        /* 4U this+0x38 bit 0x10000; never cleared here: one use per quest (user's rule) */
    uint8_t pending;      /* 4U +0xdce4 == 0: the shot waits for the end of action 53 */
    uint8_t made;
    void *player;         /* 4U +0xdce6: the shot's owner */
    uint8_t *rec;         /* our kind-11 record */
    uint8_t raise_seen;   /* action 53 seen playing (status 6 / 7) since the press */
    float raise_wait;     /* time since the press while the raise has not ended */
    float launch_wait;    /* > 0: the raise has ended, 4U's 20-unit shell wait runs before the post */
    float post_wait;      /* > 0: a shot was posted and its shell not initialised yet */
    void *shell, *trail;
    uint16_t act_seen;    /* last gate action / status logged (+1, 0 = none yet; u16: action 255 + 1) */
    uint8_t st_seen;
    uint32_t logs;
} s_m;

static void reset(void)
{
    uint32_t logs = s_m.logs;
    for (uint32_t i = 0; i < sizeof s_m; i++) ((uint8_t *)&s_m)[i] = 0;
    s_m.serial = stage_setup_serial();
    s_m.logs = logs;
}

static uint8_t *gate_kobj(void)
{
    uint8_t *mgr = *(uint8_t **)MAIN(STAGE_GIMMICK_MGR);
    if (!mgr) return 0;
    for (uint32_t i = 0; i < 24; i++) {
        uint8_t *o = FIELD(uint8_t *, mgr, MGR_KOBJ + 4 * i);
        if (o && o[KOBJ_AREA] == ARENA_AREA && o[KOBJ_TYPE] == GATE_TYPE) return o;
    }
    return 0;
}

/* GU kobj status: 4 / 5 requested (0x515438), 6 / 7 playing (0x513e28 / 0x5138f8); 3 = the state a kobj sits in
 * before its first action (the gate after its creation: test 2026-10-23, never "ready" while 3 counted as busy) */
static int kobj_busy(const uint8_t *o) { return o[KOBJ_STATUS] >= 4 && o[KOBJ_STATUS] <= 7; }

/* 4U 0x6b4fe0's gate part (stage_cart.c): no cart leg while the gate raises, waits raised for its shot or fires
 * (4U: idle after 53, or moving with another action than 55) */
int stage_demolisher_holds_cart(void)
{
    uint8_t *o = stage_alias_active() && s_m.serial == stage_setup_serial() ? gate_kobj() : 0;
    if (!o) return 0;
    int playing = o[KOBJ_STATUS] == 6 || o[KOBJ_STATUS] == 7;
    return s_m.pending || (playing && o[KOBJ_ACT] != ACT_LOWER);
}

/* the hunter stands in the cart's fire-point record at S (a replayed remote use gets a 300 margin: synced position) */
static int at_fire_point(void *pl, float margin)
{
    float p[4];
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, p);
    float dx = p[0] - k_fire_pt[0], dz = p[2] - k_fire_pt[2], r = FIRE_RADIUS + margin;
    return dx * dx + dz * dz <= r * r && p[1] > k_fire_pt[1] - 400.0f && p[1] < k_fire_pt[1] + 400.0f;
}

/* 4U 0x6b56e4: the cart parked at S (idle after 44 / 50 / 51; S is reachable only once the doors have opened,
 * stage_cart.c) and not fired yet (4U: since the last re-arm; here once per quest). Not ported: its 0x6b9f84 /
 * 0x6c3a8c(mgr, 3, 3, 0) object test (+0xc79 / +0xc78 states, object not identified) and the quest-1002 rule. */
static int use_ok(void)
{
    uint8_t *o = gate_kobj();
    return !s_m.fired && o && !kobj_busy(o) && stage_cart_parked_at(STATION_S);
}

/* a static kind-11 record at the S fire point, on every machine (+0x58 = the area, as st006's records) */
static void make_record(void)
{
    void *im = *(void **)MAIN(INTER_MGR);
    if (!im || s_m.rec) return;
    uint8_t *r = rec_alloc(im);
    if (!r) { if (++s_m.logs <= 40) logf("gogport: stage demolisher: no free interaction record"); return; }
    FIELD(uint32_t, r, 0x60) = 4;
    rec_area(r, ARENA_AREA);
    FIELD(uint16_t, r, 0x4e) = 0xffff;
    FIELD(uint16_t, r, 0x50) = 0xffff;
    FIELD(float, r, 0x48) = FIRE_HEIGHT;
    rec_flag(r, 0);
    FIELD(uint8_t, r, 0x56) = 0;
    FIELD(float, r, 0x44) = FIRE_RADIUS;
    FIELD(uint32_t, r, 0x64) = KIND_SWITCH;
    FIELD(uint8_t, r, 0x58) = ARENA_AREA;
    for (int i = 0; i < 3; i++) FIELD(float, r, 4 + 4 * i) = k_fire_pt[i];
    rec_register(im, r, 0);
    s_m.rec = r;
    logf("gogport: stage demolisher: switch record (kind 11) at the cart's S fire point (0, 1865, -5315) %x",
         (uint32_t)r);
}

/* stage_cannon.c's 0x503b88 hook (kind-11 prompt check of the local hunter): -1 = not ours, else the answer */
int stage_demolisher_ready(void *local)
{
#ifdef STAGE_DEMOLISHER_OFF
    (void)local;
    return -1;
#else
    static uint32_t s_n, s_last = 2;
    if (!stage_alias_active() || !s_m.rec || !at_fire_point(local, 60.0f)) return -1;
    uint32_t r = use_ok();
    if (r != s_last && ++s_n <= 40)
        logf("gogport: stage demolisher: prompt check -> %u (fired %u, cart at S %d)", r, s_m.fired,
             stage_cart_parked_at(STATION_S));
    s_last = r;
    return (int)r;
#endif
}

static void post_shot(void *player)
{
    uint8_t *p = param_alloc(24, 16);
    if (!p || !player) {
        logf("gogport: stage demolisher: shot not posted (param %x, player %x)", (uint32_t)p, (uint32_t)player);
        return;
    }
    FIELD(uint32_t, p, 0) = MAIN(VT_PARAM_011) + 8;
    FIELD(uint32_t, p, 4) = SHELL_PL_COM_011;
    FIELD(uint32_t, p, 8) = 0;                        /* mode 0 (st007 Demolisher shot) */
    FIELD(void *, p, 0xc) = player;
    FIELD(uint32_t, p, 0x10) = 0;
    FIELD(uint32_t, p, 0x14) = 0;                     /* no st007: start from the owner, then stage_demolisher_pose */
    s_m.post_wait = ACT_FIRE_DONE;
    s_m.shell = 0;
    shell_post(*(void **)MAIN(SHELL_MGR), p);
    logf("gogport: stage demolisher: shot posted (uShellPlcom_011 mode 0, owner %x)", (uint32_t)player);
}

static uint32_t rad_ang(float r) { return (uint32_t)(int32_t)(r * 10430.3779f + 0.5f) & 0xffff; }   /* 0xc759b0 */
static float ang_rad(uint32_t a) { return (float)(a & 0xffff) * (6.28318531f / 65536.0f); }

/* 0x466618 in 0x4664f0 (uShellPlcom_011 mode 0, init case; r4 = shell): 4U start, angles and launch velocity */
int stage_demolisher_pose_c(uint32_t *regs)
{
    uint8_t *sh = (uint8_t *)(uintptr_t)regs[R4];
    if (!sh || !(s_m.post_wait > 0.0f) || s_m.shell) return 0;
    s_m.shell = sh;
    s_m.post_wait = 0.0f;
    float s = sinf_gu(GATE_PITCH), c = cosf_gu(GATE_PITCH);
    float pos[3] = {k_gate_pos[0], k_gate_pos[1] - s * MUZZLE, k_gate_pos[2] + c * MUZZLE};   /* row 2 of Rx */
    for (int i = 0; i < 3; i++) FIELD(float, sh, SH_POS + 4 * i) = FIELD(float, sh, SH_PREV + 4 * i) = pos[i];
    FIELD(float, sh, SH_POS + 12) = 0.0f;
    uint32_t pitch = rad_ang(GATE_PITCH), yaw = rad_ang(0.0f);
    FIELD(uint32_t, sh, SH_PITCH) = pitch;
    FIELD(uint32_t, sh, SH_YAW) = yaw;
    FIELD(uint32_t, sh, SH_ROLL) = rad_ang(0.0f);
    float sp = sinf_gu(ang_rad(pitch)), cp = cosf_gu(ang_rad(pitch));
    float vy = cp * VY0 - sp * VZ0, vz = sp * VY0 + cp * VZ0;            /* 0xc74cec: x angle */
    float sy = sinf_gu(ang_rad(yaw)), cy = cosf_gu(ang_rad(yaw));
    float vx = sy * vz, vz2 = cy * vz;                                   /* 0xc74d28: y angle (vx 0 before) */
    FIELD(float, sh, SH_VEL) = vx;
    FIELD(float, sh, SH_VEL + 4) = vy;
    FIELD(float, sh, SH_VEL + 8) = vz2;
    logf("gogport: stage demolisher: shell %x start (%d, %d, %d) pitch %x yaw %x vel (%d, %d, %d)/1000", (uint32_t)sh,
         (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], pitch, yaw, (int32_t)(vx * 1000.0f),
         (int32_t)(vy * 1000.0f), (int32_t)(vz2 * 1000.0f));
    return 0;
}

/* 0x466b9c(shell, k): the shell's effect post (k 0 = launch, 1 / 2 = impact); ours -> 4U's effects, GU's skipped */
int stage_demolisher_efx_c(uint32_t *regs)
{
    uint8_t *sh = (uint8_t *)(uintptr_t)regs[R0];
    uint32_t k = regs[R1];
    if (!sh || sh != s_m.shell) return 0;
    float *pos = &FIELD(float, sh, SH_POS);
    if (k == 0) {
        float rot[3] = {(float)FIELD(uint32_t, sh, SH_PITCH) * (360.0f / 65536.0f),
                        (float)FIELD(uint32_t, sh, SH_YAW) * (360.0f / 65536.0f), 0.0f};
        void *l = em089_efx_stage_efl_rot(LAUNCH_EFL, pos, rot);
        /* 4U 0xc74ea4: the trail attached to the shell. Attached here (vt+0x130) it found no shell model and stayed
         * put (test 08:43): posted at the shell and moved onto it every frame (trail_follow) */
        s_m.trail = em089_efx_stage_efl_track(TRAIL_EFL, pos, rot);
        uint8_t *o = gate_kobj();
        if (o) kobj_play(o, ACT_FIRE, 0, 0, 0);        /* 4U command 37 at the launch (0xc74e38) */
        logf("gogport: stage demolisher: launch at (%d, %d, %d): m19a03_006 %x, trail m19a03_012 %x, gate action %u",
             (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], (uint32_t)l, (uint32_t)s_m.trail, ACT_FIRE);
    } else {
        void *e = em089_efx_stage_efl(IMPACT_EFL, pos);
        if (s_m.trail && em089_efx_alive(s_m.trail)) {
            em089_efx_stop(s_m.trail);
            FIELD(void *, sh, SH_EFX) = s_m.trail;    /* the end state 0x466684 waits until it has faded */
        }
        logf("gogport: stage demolisher: impact %u at (%d, %d, %d): m19a03_007 %x", k, (int32_t)pos[0],
             (int32_t)pos[1], (int32_t)pos[2], (uint32_t)e);
    }
    return 1;
}

static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* the trail onto the flying shell, along its velocity (pitch from -vy as the launch angles, 0x466b9c) */
static void trail_follow(void)
{
    uint8_t *sh = s_m.shell;
    if (!sh || !s_m.trail || !em089_efx_alive(s_m.trail)) return;
    const float *v = &FIELD(float, sh, SH_VEL);
    float rot[3] = {atan2f_gu(-v[1], sqrt_f(v[0] * v[0] + v[2] * v[2])), atan2f_gu(v[0], v[2]), 0.0f};
    em089_efx_place(s_m.trail, &FIELD(float, sh, SH_POS), rot);
}

static float game_delta(void)
{
    uint8_t *g = *(uint8_t **)MAIN(GAME_PTR);
    float d = g ? FIELD(float, g, GAME_DELTA) : 1.0f;
    return d > 0.0f && d <= 16.0f ? d : 1.0f;
}

/* stage_cannon.c's 0x4a18b4 hook (uShell base dtor) */
void stage_demolisher_shell_gone(void *sh)
{
    if (!sh || sh != s_m.shell) return;
    if (s_m.trail && em089_efx_alive(s_m.trail)) em089_efx_kill(s_m.trail);   /* timed out without an impact */
    if (FIELD(void *, sh, SH_EFX) == s_m.trail) FIELD(void *, sh, SH_EFX) = 0;
    s_m.shell = s_m.trail = 0;
    logf("gogport: stage demolisher: shell %x gone", (uint32_t)sh);
}

/* stage_cannon.c's 0x503bb0 hook (switch action fire, r4 = the pressing player; 4U: Dense Marcoal use -> action
 * 170 -> stage type 5 = 0x6b958c): 1 = handled */
int stage_demolisher_fire(void *player, int local)
{
#ifdef STAGE_DEMOLISHER_OFF
    (void)player; (void)local;
    return 0;
#else
    if (!stage_alias_active() || !s_m.rec || !at_fire_point(player, local ? 60.0f : 300.0f)) return 0;
    uint8_t *o = gate_kobj();
    if (!(local ? use_ok() : (!s_m.fired && o))) {
        logf("gogport: stage demolisher: switch pressed but not ready (fired %u gate %x act %u status %u, cart at S %d)",
             s_m.fired, (uint32_t)o, o ? o[KOBJ_ACT] : 0u, o ? o[KOBJ_STATUS] : 0u, stage_cart_parked_at(STATION_S));
        return 1;
    }
    if (local) {
        void *mgr = *(void **)MAIN(STAGE_GIMMICK_MGR);
        int r = stage_gimmick_camera(mgr, s_cam6, CAM6_FRAMES);
        logf("gogport: stage demolisher: camera 4U record 6 eye (2325, 3390, -8790) target (0, 1880, -5300) for %u "
             "frames -> push %d", (uint32_t)CAM6_FRAMES, r);
    }
    kobj_play(o, ACT_RAISE, 0, 0, 0);               /* 4U command 36 */
    s_m.raise_seen = 0;
    s_m.raise_wait = 0.0f;
    s_m.launch_wait = 0.0f;
    s_m.fired = s_m.pending = 1;
    s_m.player = player;
    logf("gogport: stage demolisher: FIRE by %x (%s): gate action %u (raise)", (uint32_t)player,
         local ? "local" : "replayed", ACT_RAISE);
    return 1;
#endif
}

/* stage_doors.c's stage_frame (0x503c7c) tick: 4U 0x6b985c's gate part */
void stage_demolisher_tick(void)
{
#ifndef STAGE_DEMOLISHER_OFF
    if (s_m.serial != stage_setup_serial()) reset();
    if (!s_m.rec && *(void **)MAIN(INTER_MGR)) make_record();
    uint8_t *o = gate_kobj();
    if (!o) {
        if (!s_m.made && ++s_m.logs == 1) logf("gogport: stage demolisher: no gate KowareObj (area 2, mType 22)");
        return;
    }
    s_m.made = 1;
    if ((o[KOBJ_ACT] + 1u != s_m.act_seen || o[KOBJ_STATUS] != s_m.st_seen) && ++s_m.logs <= 60)
        logf("gogport: stage demolisher: gate action %u status %u", o[KOBJ_ACT], o[KOBJ_STATUS]);
    s_m.act_seen = (uint16_t)(o[KOBJ_ACT] + 1u);
    s_m.st_seen = o[KOBJ_STATUS];
    /* 0x6b9d28: idle after action 53 -> the shot. "Idle after 53" = seen playing (6 / 7), then out of 3..7 with id 53
     * kept (GU's end path for ids > 39); RAISE_WAIT units without that -> the shot anyway, logged. Then 4U's 20-unit
     * shell wait (LAUNCH_WAIT) before the post. */
    float dt = game_delta();
    if (s_m.pending && !(s_m.launch_wait > 0.0f)) {
        int st = o[KOBJ_STATUS];
        if (st == 6 || st == 7) s_m.raise_seen = 1;
        int ended = s_m.raise_seen && o[KOBJ_ACT] == ACT_RAISE && !(st >= 3 && st <= 7);
        if (!ended && (s_m.raise_wait += dt) >= RAISE_WAIT)
            logf("gogport: stage demolisher: raise not seen ending (seen %u, act %u status %u): shot anyway",
                 s_m.raise_seen, o[KOBJ_ACT], st);
        if (ended || s_m.raise_wait >= RAISE_WAIT) s_m.launch_wait = LAUNCH_WAIT;
    } else if (s_m.pending && (s_m.launch_wait -= dt) <= 0.0f) {
        s_m.pending = 0;
        s_m.launch_wait = 0.0f;
        post_shot(s_m.player);
    }
    if (s_m.post_wait > 0.0f && (s_m.post_wait -= dt) <= 0.0f)
        logf("gogport: stage demolisher: posted shot never initialised (%u units)", (uint32_t)ACT_FIRE_DONE);
    trail_follow();
    /* 4U's re-arm (fps * 600 frames after the fire: command 38 = action 55, then QDialog 20) is not run: one use per
     * quest (user's rule 2026-10-23) */
#endif
}

/* stage_cannon.c's 0x4fdf7c hook (stage load, after 0x4fe9c0): the gate's scheduler */
void stage_demolisher_create(void *mgr)
{
#ifndef STAGE_DEMOLISHER_OFF
    void *s = sched_create(mgr, ARENA_AREA, GATE_SLOT, GATE_FILE_ID, 1, 0);
    logf("gogport: stage demolisher: gate scheduler (file %x) -> %x", GATE_FILE_ID, (uint32_t)s);
#else
    (void)mgr;
#endif
}

/* stage_cannon.c's 0x4ff074 hook (stage manager cleanup, quest end) */
void stage_demolisher_cleanup(void)
{
    void *im = *(void **)MAIN(INTER_MGR);
    uint8_t *r = s_m.rec;
    if (im && r && FIELD(uint32_t, r, 0x64) == KIND_SWITCH && FIELD(float, r, 4) == k_fire_pt[0]
        && FIELD(float, r, 12) == k_fire_pt[2]) {
        rec_free(im, r);
        logf("gogport: stage demolisher: switch record freed (stage cleanup)");
    }
    reset();
    s_m.serial = 0xffffffffu;
}
