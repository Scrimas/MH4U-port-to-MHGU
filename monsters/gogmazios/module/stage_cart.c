/* Battlequarters alias: the rail-cannon cart on 4U's 4-station loop (notes/stage.md section 13, arena-3 agent).
 *
 * GU st006 (shell 0x197) is Capcom's port of the 4U cart: its 5 interaction points (static table 0x18929a0, built in
 * 0x495924) are 4U's cart-relative records of 0x5ba4e0 with the same offsets and radii (GU kind 27 (340, 165, 170) =
 * 4U 33, 28 (-340, 165, 170) = 4U 32, 25 (+-280, 0, -415) = 4U 30, 26 (0, 165, -105) = 4U 31): load / fire / two
 * travel levers. Only the TRACK differs: GU = linear rail with stops (states 0..3 area 1, 10 / 11 area 2, stop frames
 * = st006 FUP ints, request handler 0x497040: 0 = towards the lower stop (lever kind 27), 1 = higher (kind 28)), 4U =
 * a loop N (895, 1700, 4355) -> W (-3097, 950, 590) -> S (0, 1700, -5210) -> E (3535, 950, 840) -> N driven by
 * KowareObj (mType 21) commands: lever 4U kind 33 -> cmd 33 -> action 43 + station (N0 W1 S2 E3: 43 N->W, 44 W->S,
 * 45 S->E, 46 E->N), lever kind 32 -> cmd 32 -> action 47 + station (47 N->E, 48 W->N, 49 S->W, 50 E->S)
 * (0x5ba3cc -> 0x6b93b0 types 3 / 4 -> 0x1d23a0 -> 0x1d290c / 0x1d2950), started after a 50-frame timer
 * (0x1d2a0c); each action plays scheduler m19a03d-s00 frames [startFrame, startFrame + moveFrame] (action list).
 * tools/stage4u2gu.py writes the 4U s00 keys (mOffset / mRot, 118 keys, same frame numbers) into the GU path
 * scheduler m26d-etc-a00 ("Model" mPos / mAngle), so a scheduler frame here = the 4U frame.
 *
 * Hooks (alias + the area-2 cart = stage gimmick manager [0x18977a0]+0x33c only):
 *   stage_cart_request @0x497040 (st006, request, player): requests 0 / 1 start 4U legs (lever 27 = 4U 33 ->
 *       43 + station, lever 28 = 4U 32 -> 47 + station) instead of GU's linear moves; GU's state stays a stop.
 *       Refused as 4U's lever check 0x6b4fe0: legs into S before the doors have opened, any leg while the Demolisher
 *       gate is raised for its shot or moving (except action 55).
 *   stage_cart_avail @0x495b40 (st006, kind): kinds 25..28 unavailable while a 4U leg runs (4U 0x1cead4 ->
 *       0x1d1318 re-enables the station records at the end of an action); both levers available at every station
 *       (4U loop); kinds 25 / 26 otherwise GU's answer.
 *   stage_cart_tick @0x495d0c (inside the st006 update 0x495c20, after its state machine 0x495dac; r4 = st006):
 *       writes the path scheduler frame ([st006+0x15cc]: +0x34 frame, +0x38 last evaluated, +0x40 paused byte,
 *       +0x1c frame step; 0x966140 / 0x966164) each frame, and bit 6 of st006+0x15e7 = the collision's STILL /
 *       teleport flag (helper gu6, C; GU sets it for its own whole move 0x495f80 / 0x49600c .. 0x49665c, so GU's
 *       cart carries walkers through nothing but the lever attachment): 0x495d48 passes it to the placement
 *       0xc4754c -> 0xb13638: entry+0x33 = 1, +0x34 = flag | matrix unchanged | sticky +0x50; with 0 and a changed
 *       matrix the move is continuous and 0xc1a548 files the entry in the moving tree sCol+0x8d8, the only one the
 *       ground-carry probe 0x4f57f0 searches (gate 0xc3ee74: +0x33 != 0, +0x34 == 0, type & 1). Here: ALWAYS set
 *       (since 2026-10-24), riders are moved by stage_cart_place instead (see "Riders" below). History: bit set
 *       while moving (until 2026-10-23 evening): only lever-attached hunters rode (log 18:44); bit 0 on continuous
 *       frames (GU's carry, until 2026-10-24): riders lost the carry on turns (logs 20:37 / 20:59 / 08:43).
 *   stage_cart_place @0x495d6c (between the g00 and the w00 placement, r4 = st006): carries the riders with the
 *       pose just placed.
 *   stage_cart_ground @0x2e85a4 / stage_cart_air @0x2e86fc (hunter ground function): deck backstop for riders and
 *       the airborne log.
 * Network: requests are not sent to other players (GU's 0x497040 does that) -> single player only. */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089_efx.h"

/* 4U s00 "Effect" controller: CreateKowareEft index 12 (m19a03_001), group 0, area 3, KowareEftPos (0, 1270, -5100)
 * at scheduler frames 3935 and 13445 = the ends of legs 44 (W -> S) and 50 (E -> S): arrival at the south station */
static const uint16_t k_eft_frames[2] = {3935, 13445};
static const float k_eft_pos[3] = {0.0f, 1270.0f, -5100.0f};
#define EFT_INDEX 12u
#define EFT_GROUP 0u
#define EFT_AREA  2u      /* 4U KowareEftAreaNo 3 = GU area 2 (em089_efx_stage_kowareeft compares with GU playerArea) */
enum { R0, R1, R2, R3, R4, R5, R12, LR };

int stage_alias_active(void);   /* stage.c */
int stage_doors_opened(void);   /* stage_doors.c */
int stage_demolisher_holds_cart(void);   /* stage_demolisher.c */

#define STAGE_GIMMICK_MGR  0x18977a0u   /* data word -> stage gimmick manager */
#define MGR_CART_AREA2     0x33cu       /* uShellSt006* of area 2 (0x5041ec) */
#define ST006_SCHED        0x15ccu      /* path scheduler unit */
#define SCHED_STEP         0x1cu        /* f32 frame step (0x966164: frame += speed * step) */
#define SCHED_FRAME        0x34u
#define SCHED_LAST         0x38u
#define SCHED_PAUSED       0x40u
#define ST006_FLAGS        0x15e7u      /* bit 6 = collision still / teleport (0x495d48), bit 7 = points built */
#define ST006_STILL        0x40u        /* collision handles st006+0x15c4 g00 (type 17) / +0x15c8 w00 (type 34) */
#define LEG_DELAY         50.0f        /* 4U 0x1d2a0c: next action after a 50-frame timer */

/* 4U m19a03d-s00 action list: action id -> (startFrame, moveFrame); destination station (N0 W1 S2 E3) */
static const struct { uint16_t start, move; uint8_t from, to; } k_legs[8] = {
    {0, 800, 0, 1},       /* 43 N -> W */
    {3000, 950, 1, 2},    /* 44 W -> S */
    {11000, 950, 2, 3},   /* 45 S -> E */
    {7000, 800, 3, 0},    /* 46 E -> N */
    {8500, 800, 0, 3},    /* 47 N -> E */
    {1000, 800, 1, 0},    /* 48 W -> N */
    {4500, 950, 2, 1},    /* 49 S -> W */
    {12500, 950, 3, 2},   /* 50 E -> S */
};
static const char k_station[4][2] = {"N", "W", "S", "E"};

/* 4U m19a03d-s02 (the barrel, child of s01 at (0, 220, 45)) mRot x keys of the s00 scheduler, {frame, centidegrees},
 * interpolation 3 on all 66: folded to -75 deg while travelling, N -16, W 15, S 90 (out of the Demolisher's way), E 0.
 * GU's barrel = st006+0x15a4 (m26d-s01, same local offset), pitched once at its init (0x495324: st006 FUP float
 * -2 / 10 deg) and never again (GU helper, C) -> written here every frame with 0x8a7dc4(model, Euler rad). */
static const struct { uint16_t f; int16_t cd; } k_barrel[] = {
    {0, -1600}, {70, -5485}, {85, -7700}, {88, -7500}, {700, -7500}, {770, -2000}, {785, 1700}, {788, 1500},
    {1000, 1500}, {1070, -5500}, {1085, -7700}, {1088, -7500}, {1700, -7500}, {1770, -4000}, {1785, -1400},
    {1788, -1600}, {3000, 1500}, {3070, -5850}, {3085, -7700}, {3088, -7500}, {3850, -7500}, {3920, 1500},
    {3935, 9300}, {3938, 9000}, {3950, 9000}, {4500, 9000}, {4570, -5550}, {4585, -7700}, {4588, -7500},
    {5350, -7500}, {5420, -2000}, {5435, 1700}, {5438, 1500}, {7000, 0}, {7070, -5850}, {7085, -7700},
    {7088, -7500}, {7700, -7500}, {7770, -4000}, {7785, -1400}, {7788, -1600}, {8500, -1600}, {8570, -5485},
    {8585, -7700}, {8588, -7500}, {9200, -7500}, {9270, -2500}, {9285, 200}, {9288, 0}, {11000, 9000},
    {11070, -5550}, {11085, -7700}, {11088, -7500}, {11850, -7500}, {11920, -2500}, {11935, 200}, {11938, 0},
    {12500, 0}, {12570, -5485}, {12585, -7700}, {12588, -7500}, {13350, -7500}, {13430, 1500}, {13445, 9300},
    {13448, 9000}, {13450, 9000},
};
#define ST006_BARREL       0x15a4u      /* m26d-s01 child model (alloc 0x51a6f4, model 0xd423) */
typedef void (*model_euler_t)(void *model, const float *e);
#define modelEuler FN(model_euler_t, 0x8a7dc4)   /* Euler radians (x = pitch) -> quaternion +0x50 */

static float barrel_deg(float frame)
{
    const uint32_t n = sizeof k_barrel / sizeof k_barrel[0];
    if (frame <= (float)k_barrel[0].f) return (float)k_barrel[0].cd * 0.01f;
    for (uint32_t i = 1; i < n; i++)
        if (frame < (float)k_barrel[i].f) {
            float f0 = (float)k_barrel[i - 1].f, t = (frame - f0) / ((float)k_barrel[i].f - f0);
            return ((float)k_barrel[i - 1].cd + t * (float)(k_barrel[i].cd - k_barrel[i - 1].cd)) * 0.01f;
        }
    return (float)k_barrel[n - 1].cd * 0.01f;
}

static struct {
    void *cart;        /* instance the state belongs to (re-init on a new one) */
    int8_t leg;        /* k_legs index, -1 = parked */
    uint8_t station;
    uint8_t moving;    /* leg started (else waiting for the delay) */
    float t;           /* delay countdown / leg time */
    float frame;
    float pt[3], pq[4];   /* pose (st006+0x40 / quaternion +0x50) of the last collision placement */
    uint8_t pose_ok;
    void *rider;          /* the hunter carried by the last placement that moved the cart, 0 = none */
    uint32_t serial;   /* stage_setup_serial() of the stage the state belongs to (reset per quest / stage load) */
    uint32_t logs;
} s_c;

uint32_t stage_setup_serial(void);   /* stage.c */

static void *cart_area2(void)
{
    uint8_t *mgr = *(uint8_t **)MAIN(STAGE_GIMMICK_MGR);
    return mgr ? FIELD(void *, mgr, MGR_CART_AREA2) : 0;
}

static int is_our_cart(void *st006)
{
#ifdef STAGE_CART_PARKED
    (void)st006;
    return 0;
#else
    return st006 && stage_alias_active() && st006 == cart_area2();
#endif
}

static void cart_init(void *st006)
{
    s_c.cart = st006;
    s_c.serial = stage_setup_serial();
    s_c.leg = -1;
    s_c.station = 0;          /* 4U start: north station, scheduler frame 0 */
    s_c.moving = 0;
    s_c.frame = 0.0f;
    s_c.pose_ok = 0;
    s_c.rider = 0;
    logf("gogport: stage cart: 4U loop driver on st006 %x (start N, frame 0)", (uint32_t)st006);
}

/* 1 while our cart stands at station (N0 W1 S2 E3) of this stage load (stage_demolisher.c: the prompt at S) */
int stage_cart_parked_at(uint32_t station)
{
    return s_c.cart && s_c.serial == stage_setup_serial() && s_c.leg < 0 && s_c.station == station;
}

/* 0x497040(st006, request, player) */
int stage_cart_request_c(uint32_t *regs)
{
    void *st = (void *)(uintptr_t)regs[R0];
    uint32_t req = regs[R1];
    if (!is_our_cart(st) || req > 1) return 0;
    if (s_c.cart != st || s_c.serial != stage_setup_serial()) cart_init(st);
    if (s_c.leg >= 0) { regs[R0] = 0; return 1; }      /* already travelling */
    int l = (req == 0 ? 0 : 4) + s_c.station;
    /* 4U 0x6b4fe0: the legs into S (44 W -> S, 50 E -> S) wait for the doors; no leg while the gate is raised for its
     * shot or moving with another action than 55 */
    int doors = k_legs[l].to != 2 || stage_doors_opened(), gate = !stage_demolisher_holds_cart();
    if (!doors || !gate) {
        if (++s_c.logs <= 40)
            logf("gogport: stage cart: lever %u at %s refused (%s)", req == 0 ? 27u : 28u, k_station[s_c.station],
                 !doors ? "doors closed: no leg into S" : "Demolisher gate busy");
        regs[R0] = 0;
        return 1;
    }
    s_c.leg = (int8_t)l;
    s_c.moving = 0;
    s_c.t = LEG_DELAY;
    if (++s_c.logs <= 40)
        logf("gogport: stage cart: lever %u -> 4U action %u (%s -> %s) after %u frames", req == 0 ? 27u : 28u,
             43u + (uint32_t)s_c.leg, k_station[s_c.station], k_station[k_legs[(int)s_c.leg].to], (uint32_t)LEG_DELAY);
    regs[R0] = 1;
    return 1;
}

/* 0x495b40(st006, kind) -> availability of interaction kind 25..28 */
int stage_cart_avail_c(uint32_t *regs)
{
    void *st = (void *)(uintptr_t)regs[R0];
    uint32_t kind = regs[R1];
    if (kind < 25 || kind > 28 || !is_our_cart(st)) return 0;
    if (s_c.cart != st || s_c.serial != stage_setup_serial()) cart_init(st);
    if (s_c.leg >= 0) { regs[R0] = 0; return 1; }
    if (kind >= 27) { regs[R0] = 1; return 1; }        /* loop: both levers at every station */
    /* 4U: no cart shot at S, where the same fire-point record takes Dense Marcoal (stage_demolisher.c's kind 29) */
    if (kind == 26 && s_c.station == 2) { regs[R0] = 0; return 1; }
    return 0;                                           /* load / fire: GU's rule */
}

/* Diagnostics of test 2026-10-23: (1) Cannon Ammo still "held" after a hit / a cart load. GU (helper gu5, C): carry
 * = a carry item 2105..2115 in the pouch found by 0x3000c8 -> 0x19cf50 (skips slots 24..31 unless the weapon class
 * is 4 / 5 / 6 / 10, 0x27c7ec); player+0x32a0 carry state (1 / 2 carrying, 3 / 4 drop, 5 loaded), +0x32a4 held shell;
 * 0x2ffedc runs EVERY FRAME: state 2 outside the carry action group (+0x2506 == 0x1000) -> 3 (the ball falls), and in
 * states 0 / 3 / 4 / 5 a carry item found in the pouch is removed (vt+0x360 -> 0x19b7fc), unless the quest phase byte
 * [0x188ad90]+0x50 is 4..7 / 9 (2 = playing). 4U removes it the same way (0xb17d0c). Logged on change with a raw scan
 * of all 50 slots. */
#define QUEST_STATE  0x188ad90u
#define POUCH_VAR    0x18584b8u    /* -> pouch owner, 50 slots {u16 id, s16 count} at +0x1a (0x3000dc, 0x19cf50) */
#define CARRY_FIRST  2105u
#define CARRY_LAST   2115u
typedef uint32_t (*carry_scan_t)(void *player);
#define carryScan FN(carry_scan_t, 0x3000c8)   /* local hunter: first carry item of the pouch, 0xffff = none */

/* first carry item in any of the 50 pouch slots: id | slot << 16 | count << 24, 0 = none, 0xffffffff = no pouch */
static uint32_t pouch_carry_raw(void)
{
    uint8_t *p = *(uint8_t **)MAIN(POUCH_VAR);
    if (!p) return 0xffffffffu;
    for (uint32_t i = 0; i < 50; i++) {
        uint32_t id = FIELD(uint16_t, p, 0x1a + 4 * i);
        int32_t n = FIELD(int16_t, p, 0x1c + 4 * i);
        if (id >= CARRY_FIRST && id <= CARRY_LAST && n > 0) return id | i << 16 | (uint32_t)(n & 0xff) << 24;
    }
    return 0;
}

static void diag_local(void)
{
    static uint32_t s_carry = 0xffffffffu, s_raw = 0xfffffffeu, s_scan = 0xfffffffeu, s_n1;
    uint8_t *root = *(uint8_t **)PLAYER_ROOT;
    uint8_t *pl = root ? FIELD(uint8_t *, root, 0x58) : 0;
    if (!pl) return;
    uint32_t raw = pouch_carry_raw(), scan = carryScan(pl) & 0xffff;
    uint32_t carry = FIELD(uint16_t, pl, 0x32a0) | (FIELD(uint32_t, pl, 0x32a4) ? 0x10000u : 0u);
    if ((carry != s_carry || raw != s_raw || scan != s_scan) && ++s_n1 <= 80) {
        uint8_t *q = *(uint8_t **)MAIN(QUEST_STATE);
        uint8_t *w = FIELD(uint8_t *, pl, 0x13c4);
        logf("gogport: diag carry: state %u held shell %x | GU scan %x | pouch item %u slot %u count %u | group %x "
             "action %u weapon %u quest byte50 %u", carry & 0xffff, FIELD(uint32_t, pl, 0x32a4), scan,
             raw == 0xffffffffu ? 0u : raw & 0xffff, (raw >> 16) & 0xff, raw == 0xffffffffu ? 0u : raw >> 24,
             FIELD(uint16_t, pl, 0x2506), FIELD(uint16_t, pl, 0x250a), w ? w[0x4d4] : 0xffu, q ? q[0x50] : 0xffu);
    }
    s_carry = carry; s_raw = raw; s_scan = scan;
}

/* Riders (helper gu9 + logs, C unless marked):
 * - hunter frame: move update, ground function vt+0x368 = 0x2e846c, carry probe 0x4f57f0 (+-30), carry slot 10
 *   0x29c368, wall sweep 0x182374 from player+0x1000 (the pre-carry position), ground function again.
 * - the ground function's ray query 0x18192c searches the still AND the moving tree (type 1: g00, never w00), keeps
 *   the highest hit up to y + 100; a grounded hunter more than 30 above it goes airborne (0x2e86fc, vt+0x300(pl, 2))
 *   and falls (0x2831e0(pl, 4, 29 / 30)).
 * - GU's carry (moving collision, until 2026-10-24): slot 10 adds a delta only when 0x4f594c(player+0x2f00) returns
 *   1; it asks 0xc3eb0c, which moves the contact point by the entry's old -> new matrix and SWEEPS the hunter to it,
 *   refusing the carry when the sweep is blocked. Log 08:43 (N -> W, frame 300..332, the cart starting its turn and
 *   rise): contact on, no carry, the hunter stood still in the world while the deck slid under him (user: "stay on
 *   the platform but positioned as if on the ground not moving"), through the rear fence (local x -450) and off.
 *   Same at 20:59 (N -> E frame 8686). With w00 still (20:52 .. 21:40) the fence also crossed riders (S).
 * Now: both collisions always still (teleported, GU's carry never engages; the ground query sees still entries:
 * hunters stand on the parked cart), and stage_cart_place moves the local hunter rigidly with the pose just placed
 * (old pose -> new pose, position and facing) in the same update that moves the collision, so no wall ever crosses
 * him. Riders = not lever-attached (player+0x3274: GU moves those, 0x2f6a34), over the deck (local x / z within the
 * fence + 20) and at most 40 below / 80 above it (local y). Single player: the local hunter only.
 * Backstop while a leg runs: the deck plane = GU m26d-a-g00-s00 (all at local y 165 over x -446..451, z -337..310,
 * inside the fence), posed by st006+0x40 / quaternion +0x50 (what 0x495d48 places the collision with; 0xc4754c rows =
 * the local axes). It replaces GU's result only when GU missed (no hit, or 150+ below the deck) and the hunter is
 * within 100 of the deck, so a deck GU found is never moved. */
#define DECK_Y     165.0f
#define DECK_X0   -446.0f
#define DECK_X1    451.0f
#define DECK_Z0   -337.0f
#define DECK_Z1    310.0f
#define YAW_UNITS  10430.378f   /* 65536 / 2 pi: player+0xfec (0x29c57c) */

/* quaternion (x, y, z, w) -> world images of the local x / y / z axes (0xc4754c's matrix rows) */
static void quat_axes(const float *q, float *ax, float *up, float *az)
{
    float x = q[0], y = q[1], z = q[2], w = q[3];
    ax[0] = 1.0f - 2.0f * (y * y + z * z); ax[1] = 2.0f * (x * y + z * w); ax[2] = 2.0f * (x * z - y * w);
    up[0] = 2.0f * (x * y - z * w); up[1] = 1.0f - 2.0f * (x * x + z * z); up[2] = 2.0f * (y * z + x * w);
    az[0] = 2.0f * (x * z + y * w); az[1] = 2.0f * (y * z - x * w); az[2] = 1.0f - 2.0f * (x * x + y * y);
}

/* o = a * b (Hamilton product, (x, y, z, w)) */
static void quat_mul(float *o, const float *a, const float *b)
{
    float r[4] = {a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
                  a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
                  a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
                  a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]};
    for (uint32_t i = 0; i < 4; i++) o[i] = r[i];
}

static float dot3(const float *a, const float *b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

/* deck height under world point p (x, z) -> *h, the point's cart-local x / z; 1 = over the deck */
static int deck_height(const uint8_t *st, const float *p, float *h, float *lx, float *lz)
{
    const float *t = &FIELD(float, st, 0x40);
    float ax[3], up[3], az[3];
    quat_axes(&FIELD(float, st, 0x50), ax, up, az);
    if (!(up[1] > 0.5f)) return 0;
    float qx = t[0] + DECK_Y * up[0], qy = t[1] + DECK_Y * up[1], qz = t[2] + DECK_Y * up[2];
    *h = qy - (up[0] * (p[0] - qx) + up[2] * (p[2] - qz)) / up[1];
    float d[3] = {p[0] - t[0], *h - t[1], p[2] - t[2]};
    *lx = dot3(d, ax);
    *lz = dot3(d, az);
    return *lx >= DECK_X0 && *lx <= DECK_X1 && *lz >= DECK_Z0 && *lz <= DECK_Z1;
}

/* the local hunter rigidly from pose (t0, q0) to (t1, q1); 1 = carried */
static int carry_rider(uint8_t *pl, const float *t0, const float *q0, const float *t1, const float *q1)
{
    if (FIELD(uint8_t, pl, 0x3274)) return 0;            /* lever-attached: GU's attachment moves him */
    float *p = &FIELD(float, pl, 0x40);
    float a0[3], u0[3], z0[3], a1[3], u1[3], z1[3];
    quat_axes(q0, a0, u0, z0);
    float d[3] = {p[0] - t0[0], p[1] - t0[1], p[2] - t0[2]};
    float lx = dot3(d, a0), ly = dot3(d, u0), lz = dot3(d, z0);
    if (lx < DECK_X0 - 20.0f || lx > DECK_X1 + 20.0f || lz < DECK_Z0 - 20.0f || lz > DECK_Z1 + 20.0f ||
        ly < DECK_Y - 40.0f || ly > DECK_Y + 80.0f)
        return 0;
    quat_axes(q1, a1, u1, z1);
    for (uint32_t i = 0; i < 3; i++) p[i] = t1[i] + lx * a1[i] + ly * u1[i] + lz * z1[i];
    /* facing as GU's carry (0x29c520..0x29c5b4): rotation +0x50 turned by the cart's, yaw +0xfec from its z axis,
     * the target yaw +0x14a0 shifted by the same step */
    float qc[4] = {-q0[0], -q0[1], -q0[2], q0[3]}, qd[4], *qp = &FIELD(float, pl, 0x50);
    quat_mul(qd, q1, qc);
    quat_mul(qp, qd, qp);
    float fx = 2.0f * (qp[0] * qp[2] + qp[1] * qp[3]), fz = 1.0f - 2.0f * (qp[0] * qp[0] + qp[1] * qp[1]);
    uint32_t yaw = (uint32_t)(int32_t)(0.5f + atan2f_gu(fx, fz) * YAW_UNITS) & 0xffff;
    FIELD(uint32_t, pl, 0x14a0) = (FIELD(uint32_t, pl, 0x14a0) + yaw - FIELD(uint32_t, pl, 0xfec)) & 0xffff;
    FIELD(uint32_t, pl, 0xfec) = yaw;
    return 1;
}

/* 0x495d6c (st006's update, after the g00 placement 0x495d54, before the w00 one; r4 = st006): the pose
 * st006+0x40 / +0x50 just placed */
int stage_cart_place_c(uint32_t *regs)
{
    uint8_t *st = (uint8_t *)(uintptr_t)regs[R4];
    if (!is_our_cart(st) || s_c.cart != st || s_c.serial != stage_setup_serial()) return 0;
    const float *t = &FIELD(float, st, 0x40), *q = &FIELD(float, st, 0x50);
    float dt[3] = {t[0] - s_c.pt[0], t[1] - s_c.pt[1], t[2] - s_c.pt[2]};
    int moved = s_c.pose_ok && (dot3(dt, dt) > 0.0f || q[0] != s_c.pq[0] || q[1] != s_c.pq[1] || q[2] != s_c.pq[2] ||
                                q[3] != s_c.pq[3]);
    if (moved && dot3(dt, dt) < 150.0f * 150.0f) {       /* no carry across a teleport */
        uint8_t *root = *(uint8_t **)PLAYER_ROOT;
        uint8_t *pl = root ? FIELD(uint8_t *, root, 0x58) : 0;
        static uint8_t s_on;
        static uint32_t s_n, s_t;
        uint8_t on = pl && carry_rider(pl, s_c.pt, s_c.pq, t, q);
        if ((on != s_on || (on && s_t++ % 120 == 0)) && ++s_n <= 80) {
            const float *p = pl ? &FIELD(float, pl, 0x40) : t;
            logf("gogport: stage cart: rider %s (hunter %d, %d, %d, action %u, cart frame %u)",
                 on ? "carried" : "not on the deck", (int32_t)p[0], (int32_t)p[1], (int32_t)p[2],
                 pl ? FIELD(uint16_t, pl, 0x250a) : 0u, (uint32_t)s_c.frame);
        }
        s_on = on;
        s_c.rider = on ? pl : 0;
    }
    for (uint32_t i = 0; i < 3; i++) s_c.pt[i] = t[i];
    for (uint32_t i = 0; i < 4; i++) s_c.pq[i] = q[i];
    s_c.pose_ok = 1;
    return 0;
}

static uint8_t *riding_cart(void)
{
    uint8_t *st = cart_area2();
    return st && is_our_cart(st) && s_c.cart == st && s_c.serial == stage_setup_serial() && s_c.leg >= 0 ? st : 0;
}

/* 0x2e85a4 (return of the query 0x18192c, before `ldr r1, [sp, #0x1c]`: r0 = 1 hit, r4 = hunter); the caller's
 * sp+0x1c (the ground y) = regs[15] (trampoline: 8 saved words, then the caller's stack) */
int stage_cart_ground_c(uint32_t *regs)
{
    uint8_t *st = riding_cart();
    if (!st) return 0;
    uint8_t *pl = (uint8_t *)(uintptr_t)regs[R4];
    const float *p = &FIELD(float, pl, 0x40);
    float h, lx, lz, *ground = (float *)&regs[15];
    if (!deck_height(st, p, &h, &lx, &lz)) return 0;
    int hit = regs[R0] == 1;
    float dy = p[1] - h;
    /* a rider (carried by the last placement) keeps the deck as ground: test 09:49, N -> E frame 8679..8695, the
     * banked deck's low side dipped under the N platform (y 1700): GU's query (highest hit up to y + 100) gave the
     * platform, the hunter was set onto it and the cart left without him */
    float gap = hit ? *ground - h : -1000.0f;
    if (pl == s_c.rider && dy <= 100.0f && dy >= -100.0f && (gap > 5.0f || gap < -5.0f)) {   /* `deck check`: GU's
                                                                         deck hits equal ours to the unit */
        static uint32_t s_kept;
        if (++s_kept <= 40)
            logf("gogport: stage cart: deck kept for the rider: GU ground %d%s, deck %d, hunter y %d (local %d, %d), "
                 "frame %u", hit ? (int32_t)*ground : 0, hit ? "" : " (no hit)", (int32_t)h, (int32_t)p[1],
                 (int32_t)lx, (int32_t)lz, (uint32_t)s_c.frame);
        *ground = h;
        regs[R0] = 1;
        return 0;
    }
    static uint32_t s_chk, s_n;
    if (hit && *ground > h - 150.0f) {
        /* self-check of the pose maths against GU's own hit on the deck */
        if (s_chk++ % 240 == 0 && s_n < 16 && ++s_n)
            logf("gogport: stage cart: deck check GU %d ours %d (local %d, %d, frame %u)", (int32_t)*ground,
                 (int32_t)h, (int32_t)lx, (int32_t)lz, (uint32_t)s_c.frame);
        return 0;
    }
    if (dy > 100.0f || dy < -100.0f) return 0;
    static uint32_t s_snaps;
    if (++s_snaps <= 60)
        logf("gogport: stage cart: deck backstop: GU ground %d%s, deck %d, hunter y %d (local %d, %d), action %u "
             "group %x, frame %u", hit ? (int32_t)*ground : 0, hit ? "" : " (no hit)", (int32_t)h, (int32_t)p[1],
             (int32_t)lx, (int32_t)lz, FIELD(uint16_t, pl, 0x250a), FIELD(uint16_t, pl, 0x2506), (uint32_t)s_c.frame);
    *ground = h;
    regs[R0] = 1;
    return 0;
}

/* 0x2e86fc (a grounded hunter more than 30 above the ground is set airborne, r4 = hunter): logged while a leg runs */
int stage_cart_air_c(uint32_t *regs)
{
    uint8_t *st = riding_cart();
    if (!st) return 0;
    uint8_t *pl = (uint8_t *)(uintptr_t)regs[R4];
    const float *p = &FIELD(float, pl, 0x40);
    float h = 0.0f, lx = 0.0f, lz = 0.0f;
    int over = deck_height(st, p, &h, &lx, &lz);
    static uint32_t s_n;
    if (++s_n <= 40)
        logf("gogport: stage cart: hunter airborne (y %d, ground %d, deck %d %s, local %d, %d, action %u group %x, "
             "contact %u, frame %u)", (int32_t)p[1], (int32_t)FIELD(float, pl, 0x10f0), (int32_t)h,
             over ? "over" : "off", (int32_t)lx, (int32_t)lz, FIELD(uint16_t, pl, 0x250a), FIELD(uint16_t, pl, 0x2506),
             FIELD(uint8_t, pl, 0x3000), (uint32_t)s_c.frame);
    return 0;
}

/* inside 0x495c20 at 0x495d0c: r4 = st006 */
int stage_cart_tick_c(uint32_t *regs)
{
    void *st = (void *)(uintptr_t)regs[R4];
    if (!is_our_cart(st)) return 0;
    if (s_c.cart != st || s_c.serial != stage_setup_serial()) cart_init(st);
    uint8_t *sch = FIELD(uint8_t *, st, ST006_SCHED);
    if (!sch) return 0;
    float step = FIELD(float, sch, SCHED_STEP);
    if (!(step > 0.0f && step <= 4.0f)) step = 1.0f;
    if (s_c.leg >= 0) {
        int l = s_c.leg;
        if (!s_c.moving) {
            s_c.t -= step;
            if (s_c.t <= 0.0f) { s_c.moving = 1; s_c.t = 0.0f; }
            s_c.frame = (float)k_legs[l].start;
        } else {
            float f0 = (float)k_legs[l].start + s_c.t;
            s_c.t += step;
            float f1 = (float)k_legs[l].start + s_c.t;
            for (uint32_t i = 0; i < 2; i++)
                if (f0 < (float)k_eft_frames[i] && f1 >= (float)k_eft_frames[i]) {
                    void *h = em089_efx_stage_kowareeft(EFT_INDEX, EFT_GROUP, k_eft_pos, EFT_AREA);
                    if (++s_c.logs <= 40)
                        logf("gogport: stage cart: 4U s00 effect m19a03_001 at frame %u (%s)", (uint32_t)k_eft_frames[i],
                             h ? "posted" : "no em089 yet");
                }
            if (s_c.t >= (float)k_legs[l].move) {
                s_c.frame = (float)(k_legs[l].start + k_legs[l].move);
                s_c.station = k_legs[l].to;
                s_c.leg = -1;
                s_c.rider = 0;
                if (++s_c.logs <= 40)
                    logf("gogport: stage cart: arrived %s (frame %u)", k_station[s_c.station], (uint32_t)s_c.frame);
            } else {
                s_c.frame = (float)k_legs[l].start + s_c.t;
            }
        }
    }
    FIELD(uint8_t, sch, SCHED_PAUSED) = 1;              /* GU never advances it; we write the frame */
    if (FIELD(float, sch, SCHED_FRAME) != s_c.frame) {
        FIELD(float, sch, SCHED_FRAME) = s_c.frame;
        FIELD(float, sch, SCHED_LAST) = s_c.frame - 1.0f;   /* 0x966164 re-evaluates when last != frame */
    }
    FIELD(uint8_t, st, ST006_FLAGS) |= ST006_STILL;     /* collision teleported: riders = stage_cart_place */
    void *barrel = FIELD(void *, st, ST006_BARREL);
    if (barrel) {
        float e[4] __attribute__((aligned(16))) = {barrel_deg(s_c.frame) * (3.14159265f / 180.0f), 0.0f, 0.0f, 0.0f};
        modelEuler(barrel, e);
    }
    diag_local();
    return 0;
}
