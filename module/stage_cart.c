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
 *   stage_cart_avail @0x495b40 (st006, kind): kinds 25..28 unavailable while a 4U leg runs (4U 0x1cead4 ->
 *       0x1d1318 re-enables the station records at the end of an action); both levers available at every station
 *       (4U loop); kinds 25 / 26 otherwise GU's answer.
 *   stage_cart_tick @0x495d0c (inside the st006 update 0x495c20, after its state machine 0x495dac; r4 = st006):
 *       writes the path scheduler frame ([st006+0x15cc]: +0x34 frame, +0x38 last evaluated, +0x40 paused byte,
 *       +0x1c frame step; 0x966140 / 0x966164) each frame.
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

#define STAGE_GIMMICK_MGR  0x18977a0u   /* data word -> stage gimmick manager */
#define MGR_CART_AREA2     0x33cu       /* uShellSt006* of area 2 (0x5041ec) */
#define ST006_SCHED        0x15ccu      /* path scheduler unit */
#define SCHED_STEP         0x1cu        /* f32 frame step (0x966164: frame += speed * step) */
#define SCHED_FRAME        0x34u
#define SCHED_LAST         0x38u
#define SCHED_PAUSED       0x40u
#define LEG_DELAY          50.0f        /* 4U 0x1d2a0c: next action after a 50-frame timer */

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

static struct {
    void *cart;        /* instance the state belongs to (re-init on a new one) */
    int8_t leg;        /* k_legs index, -1 = parked */
    uint8_t station;
    uint8_t moving;    /* leg started (else waiting for the delay) */
    float t;           /* delay countdown / leg time */
    float frame;
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
    logf("gogport: stage cart: 4U loop driver on st006 %x (start N, frame 0)", (uint32_t)st006);
}

/* 0x497040(st006, request, player) */
int stage_cart_request_c(uint32_t *regs)
{
    void *st = (void *)(uintptr_t)regs[R0];
    uint32_t req = regs[R1];
    if (!is_our_cart(st) || req > 1) return 0;
    if (s_c.cart != st || s_c.serial != stage_setup_serial()) cart_init(st);
    if (s_c.leg >= 0) { regs[R0] = 0; return 1; }      /* already travelling */
    s_c.leg = (int8_t)((req == 0 ? 0 : 4) + s_c.station);
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
    return 0;                                           /* load / fire: GU's rule */
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
    return 0;
}
