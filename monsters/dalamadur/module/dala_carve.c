/* dala_carve.c: the carcass carve points of both halves (4U carve points) and the carcass test log.
 * C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * GU (C): a death ends in the reaction player 0xa134c: at the sequence end (0xa16d4, category 11 / 14) a step machine
 * on rec+0x550 runs. Step 0 (0xa1734): carcass timer rec+0x1bc (0x4953c), then, for every 11/n but 16..18 / 38..40
 * (0x81640 == 0) and no point yet (rec+0x5d38 == -1), vt slot 264 (base 0xac6c4) = the first dtbparts carve record
 * of kind 0 -> 0xaba9c(this, record, flags 1, 0) -> rec+0x5d38. Step 1 is the carcass (0xa0f30 case 1 waits on the
 * point's carves / the timer); step 1 -> 2 releases the point (0xac898), 2 -> 3 fades the motion (0xbef30 0 / 120),
 * 3 -> 4 = 12/255 (0x76908 / 0x76a10). 12/255 (0xa6bb8) = motion speed 0, rec+0x5ac = 1.
 * Carve records (dtbparts object enemy+0x75f0: pointer +0x6c, u8 count +0x8e; loader 0x5575c, C) are 12 bytes:
 * {u8 kind (0 body, 1 severed part, 2), u8 carves, u16 0, f32 radius, u8 0, u8 joint (255 = object position), u8 0,
 * u8 0}. 0xaba9c (C): position = joint x / z with y = rec+0x5b4 (GU's ground probe 0xbdf1c) for flags 1, the cut
 * part for flags 2 (0xac730, the severed tail's record of kind 1), the object position rec+0x40 for joint 255;
 * radius = record * speedFactor 0xbe5d4 (x 1.5 when this+0x1068 bit 3), height window 300, carves = record + skill
 * bonus 0x69bfc. Hunter test 0x319278 (S: the gather point range test): |dy| < 150 and x / z distance <= radius.
 * The four arcs share Kushala's placeholder dtbparts (build_dalamadur_arc.py): {kind 0, 4 carves, radius 600,
 * joint 255} + {kind 1, 1, 200, 255} -> both halves' carcass point sat on the object position = the arena origin
 * (0, 0, 0), inside the spire and under the floor: nobody could carve (test 2026-10-21, user).
 *
 * 4U (C, tools/hagi4u.py CARVE_POINTS_4U 0x1003bec: 16-B records {u16 table base, u16 carves, f32 radius, .., u8 joint
 * +0xb}; reaction player 0x9197c0 end, step 0: 0x926044(this, point 0, flags 1, 0) -> W+0x7a48, the same flags-1 rule
 * with y = its ground probe W+0x624): em024 / em110 point 0 = 4 carves, radius 1200, joint 5 (head); em083 / em111
 * point 0 = 4 carves, radius 1700, joint 101; point 1 (severed tail) = 1 carve, radius 350, joint 255. Same numbers
 * for Shah, so one record list serves all four arcs.
 * Port: the records go into the shared object (as dala_break.c's break records); each class overrides slot 264 to
 * create its own half's record (the base takes the first kind-0 record: the head's). y: 4U's W+0x624 for an object
 * held at the origin is not known here (G); our objects skip GU's ground probe (REC_NO_GROUND), so rec+0x5b4 is set
 * to the stage floor under the joint (map segment 0x1838fc down from the joint) right before 0xaba9c (deviation:
 * the floor where the dead head / tail lies, so a hunter standing next to it is inside the 150 window).
 * Multiplayer: GU replays the death action on every machine and each machine's reaction player creates its own point
 * (carves are per hunter); the position comes from the replayed motion's joint and the shared stage collision, so all
 * machines put it at the same place. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_gather.h"

#define EN_DTBPARTS   0x75f0   /* enemy: dtbparts object (dala_break.c) */
#define DTP_CARVES    0x6c     /* carve records (12 B) */
#define DTP_NCARVE    0x8e     /* u8 their count */
#define EN_AREA       0x1054   /* u8 map area */
#define REC_CARVE_H   0x5d38   /* s32 carcass carve point handle, -1 = none */
#define REC_GROUND_Y  0x5b4    /* float ground probe y: flags-1 points take their y from it */
#define REC_END_STEP  0x550    /* u8 reaction player end machine step (death: 1 = carcass) */
#define REC_RAGE      0x518    /* u8 rage */
#define LAYER1_MOT    0x5f4    /* u16 layer-1 motion (layer 0 0x4b4 + 0x140) */
#define LAYER1_FRAME  0x640    /* float layer-1 frame (layer 0 0x500 + 0x140) */
#define gu_new    FN(void *(*)(uint32_t), 0x7af3a0)   /* MT heap new[] / delete[] (the loader's, dala_break.c) */
#define gu_delete FN(void (*)(void *), 0x7af3e4)
typedef int32_t (*carvePoint_t)(void *self, uint32_t record, uint32_t flags, uint32_t part);
#define carvePoint FN(carvePoint_t, 0xaba9c)
#define carveFirst FN(act_base_t, 0xac6c4)            /* base slot 264 */
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment FN(map_segment_t, 0x1838fc)        /* = 4U 0x2b96e4 (dala_shell003.c ground test) */
#define COL_MGR    (*(void **)MAIN(0x21270e0))
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx   FN(joint_mtx_t, 0xc1660)           /* = 4U 0x930894 (dala_gather.c) */
/* the GU point manager and a point's fields: dala_gather.c (dala_gather_pos = the live point of a handle) */

typedef struct {
    uint8_t kind, carves;
    uint16_t pad;
    float radius;
    uint8_t b8, joint, b10, b11;
} carve_t;
_Static_assert(sizeof(carve_t) == 12, "carve_t");

#define K_HEAD 0
#define K_TAIL 2
#define N_CARVES 3
static const carve_t k_carves[N_CARVES] = {
    {0, 4, 0, 1200.0f, 0, 5, 0, 0},       /* head body: 4U em024 / em110 point 0 */
    {1, 1, 0, 350.0f, 0, 255, 0, 0},      /* severed tail: em083 / em111 point 1 (GU cut part, 0xac730) */
    {0, 4, 0, 1700.0f, 0, 101, 0, 0},     /* tail half body: em083 / em111 point 0 (our tail's slot 264) */
};

static void *s_dtp;    /* the shared object the records went into */

static int same(const carve_t *a, const carve_t *b)
{
    return a->kind == b->kind && a->carves == b->carves && a->radius == b->radius && a->joint == b->joint;
}

/* both halves, every frame from slot 130 (next to dala_break_install): once per loaded resource */
void dala_carve_install(void *self)
{
    uint8_t *obj = FIELD(uint8_t *, self, EN_DTBPARTS);
    if (!obj || obj == s_dtp) return;
    s_dtp = obj;
    carve_t *old = FIELD(carve_t *, obj, DTP_CARVES);
    uint32_t n = obj[DTP_NCARVE], ok = n == N_CARVES && old;
    for (uint32_t i = 0; ok && i < N_CARVES; i++) ok = same(&old[i], &k_carves[i]);
    if (ok) return;
    carve_t *mem = gu_new(sizeof k_carves);
    if (!mem) { logf("dalaport: carve records: alloc failed"); return; }
    for (uint32_t i = 0; i < N_CARVES; i++) mem[i] = k_carves[i];
    FIELD(carve_t *, obj, DTP_CARVES) = mem;
    obj[DTP_NCARVE] = N_CARVES;
    logf("dalaport: carve records: dtbparts %x had %u (first kind %u carves %u radius %d joint %u), now %u", (uint32_t)obj,
         n, n && old ? old[0].kind : 0, n && old ? old[0].carves : 0, n && old ? (int)old[0].radius : 0,
         n && old ? old[0].joint : 0, N_CARVES);
    if (old) gu_delete(old);
}

static int is_tail(void *self) { return (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff); }

static float s_pt[2][4];     /* the carve point each half created (test log), y = window centre */
static float s_rad[2];

/* GU slot 264 (both classes, from the death sequence end 0xa19ec, this machine): the half's own 4U carve point */
void dala_carve_point(void *self)
{
    uint32_t tail = is_tail(self), idx = tail ? K_TAIL : K_HEAD;
    uint8_t *rec = REC(self), *obj = FIELD(uint8_t *, self, EN_DTBPARTS);
    const carve_t *c = obj ? FIELD(const carve_t *, obj, DTP_CARVES) : 0;
    if (!c || obj[DTP_NCARVE] <= idx || !same(&c[idx], &k_carves[idx])) {
        logf("dalaport: carve %s: no 4U record (dtbparts %x count %u): base slot 264", tail ? "tail" : "head",
             (uint32_t)obj, obj ? obj[DTP_NCARVE] : 0);
        carveFirst(self);
        return;
    }
    float j[4] = {0, 0, 0, 0}, out[4] = {0, 0, 0, 0};
    /* the tail's record names head joint 101: the tail half holds its head bones in the rest pose (dala_join.c), so
     * its own joint 101 sat at (-5690, 3723, 2900), in the air off the arena (test 2026-10-21, no floor below).
     * Taken from the head's posed skeleton, as the 4U tail class does for its body gather point (slot 77 0x8a2a68
     * reads the head's joint 101, C); user: two carve spots on the head part (S) */
    void *head = tail ? dala_partner(self) : 0;
    jointPos(head && c[idx].joint > 0 && c[idx].joint < 139 ? head : self, c[idx].joint, j);
    if (!tail) {
        /* 4U slot 48 0x773cc8..0x773d98 moves the head's carcass point W+0x7a48 every frame to joint 5's rows 0 / 1 /
         * 2 times 80 / 150 / 200 plus row 3 (C; the 80 = s17 [0x773668], loaded earlier in the slot, S). The dead
         * head holds its last frame by now (dala_react.c), so placing it once here gives the same point. y: the
         * floor under it, as before (4U keeps the joint height; GU's hunter window is +-150 around the point and a
         * joint-height point was out of reach, test 2026-10-21: deviation) */
        float m[16];
        jointMtx(self, c[idx].joint, m);
        for (int i = 0; i < 3; i++) j[i] = m[i] * 80.0f + m[4 + i] * 150.0f + m[8 + i] * 200.0f + m[12 + i];
    }
    float from[4] = {j[0], j[1], j[2], 0.0f}, to[4] = {j[0], j[1] - 8000.0f, j[2], 0.0f};
    void *col = COL_MGR;
    /* end point first, start second: the working callers pass the lower point first (meteor (pos, prev), blast
     * (y - 600, y + 600)); (joint, joint - 8000) cast upward and found no floor (test 2026-10-21: "floor none",
     * point y 490 = the joint, the hunter at y ~220 outside GU's 150 window) */
    uint32_t hit = col ? mapSegment(col, to, from, FIELD(uint8_t, self, EN_AREA), out, 0, 16, 64) : 0;
    float y = hit ? out[1] : j[1];
    FIELD(float, rec, REC_GROUND_Y) = y;
    int32_t h = carvePoint(self, idx, 1, 0);
    FIELD(int32_t, rec, REC_CARVE_H) = h;
    /* 0xaba9c takes x / z from this instance's own joint (0xc1708(this, joint) at 0xabbb0, C): for the tail the
     * rest-pose joint 101, so the point stayed off the arena whatever we probed (test 2026-10-21 tenth install: tail
     * point handle 1, the hunter inside the tested window at the head's joint, no carve). Moved to the joint used
     * above after its creation; the rest of 0xaba9c and its registration 0x31abac never read the position (C) */
    float *pt = dala_gather_pos(h), was[2] = {pt ? pt[0] : 0.0f, pt ? pt[2] : 0.0f};
    if (pt) { pt[0] = j[0]; pt[2] = j[2]; }
    logf("dalaport: carve %s point %d: %s, GU x / z %d %d -> %d %d", tail ? "tail" : "head", h,
         pt ? "moved" : "NOT FOUND", (int)was[0], (int)was[1], (int)j[0], (int)j[2]);
    s_pt[tail][0] = j[0]; s_pt[tail][1] = y; s_pt[tail][2] = j[2];
    s_rad[tail] = c[idx].radius * speedFactor(self);
    logf("dalaport: carve %s point %d: record %u (%u carves, radius %d x scale %d/1000 = %d), joint %u at %d %d %d, "
         "floor %s %d, area %u, %u/%u frame %u", tail ? "tail" : "head", h, idx, c[idx].carves, (int)c[idx].radius,
         (int)(speedFactor(self) * 1000.0f), (int)s_rad[tail], c[idx].joint, (int)j[0], (int)j[1], (int)j[2],
         hit ? "hit" : "none (joint y)", (int)y, FIELD(uint8_t, self, EN_AREA), FIELD(uint8_t, self, EN_ACT_CAT),
         FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint32_t, self, F_FRAMES));
}

/* the local hunter (dala.c local_hunter); its position = unit +0x40 (G: the cUnit position the shells use) */
static void *hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* Test log, both halves, GU slot 119 (runs every frame, also in 12/255 where slot 125 is skipped): one line per
 * change of action / end step / carve handle while dead, then every 120 frames the motion state (post-death fire:
 * a restarting layer-0 frame or a layer-1 motion = motion effects, rage = GU state effects) and the hunter against
 * the carve point (the 0x319278 test: dxz <= radius, |dy| < 150). */
void dala_carcass_log(void *self)
{
    static uint32_t s_sig[2], s_t[2], s_n, s_m;
    uint32_t tail = is_tail(self), cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    uint8_t *rec = REC(self);
    if (cat != 11 && cat != 14 && !(cat == 12 && num == 255)) { s_sig[tail] = 0; s_t[tail] = 0; return; }
    int32_t h = FIELD(int32_t, rec, REC_CARVE_H);
    uint32_t sig = 0x80000000u | cat << 20 | num << 12 | (uint32_t)rec[REC_END_STEP] << 4 | (h != -1);
    if (sig != s_sig[tail] && ++s_n <= 40) {
        s_sig[tail] = sig;
        logf("dalaport: carcass %s %u/%u step %u carve %d timer %d motion %x frame %d speed %d/1000 frame %u",
             tail ? "tail" : "head", cat, num, rec[REC_END_STEP], h, (int)FIELD(float, rec, REC_TIMER), curMotion(self),
             (int)motionFrame(self), (int)(FIELD(float, self, MOT_SPEED) * 1000.0f), FIELD(uint32_t, self, F_FRAMES));
    }
    {   /* the death -> carcass jump (user, 2026-10-22: the model shifts between the death motion's end and the
         * carcass): this+0x40 and two joints (head 0 / 5, tail 0 / 142), logged when one moves > 300 in a frame
         * (test 2026-10-22: the death motion itself moves up to ~210 a frame; its first frame snaps 2861 = 4U's
         * blend 0, D_fdcbe0) */
        static float s_last[2][9];
        static uint32_t s_nj;
        float now[12];
        for (int i = 0; i < 3; i++) now[i] = FIELD(float, self, 0x40 + 4 * i);
        jointPos(self, 0, &now[3]);
        jointPos(self, tail ? 142 : 5, &now[6]);
        float *l = s_last[tail], worst = 0.0f;
        for (int i = 0; i < 9; i++) { float d = now[i] - l[i]; d = d < 0 ? -d : d; if (d > worst) worst = d; }
        if (s_t[tail] && worst > 300.0f && ++s_nj <= 30)
            logf("dalaport: carcass %s jump %d: pos %d %d %d -> %d %d %d, j0 %d %d %d -> %d %d %d, j%u %d %d %d -> %d %d "
                 "%d | %u/%u step %u motion %x frame %d", tail ? "tail" : "head", (int)worst, (int)l[0], (int)l[1],
                 (int)l[2], (int)now[0], (int)now[1], (int)now[2], (int)l[3], (int)l[4], (int)l[5], (int)now[3],
                 (int)now[4], (int)now[5], tail ? 142u : 5u, (int)l[6], (int)l[7], (int)l[8], (int)now[6], (int)now[7],
                 (int)now[8], cat, num, rec[REC_END_STEP], curMotion(self), (int)motionFrame(self));
        for (int i = 0; i < 9; i++) l[i] = now[i];
    }
    if (++s_t[tail] % 120 != 1 || ++s_m > 80) return;
    void *pl = hunter();
    const float *p = pl ? &FIELD(float, pl, 0x40) : 0, *c = s_pt[tail];
    float dx = p ? p[0] - c[0] : 0.0f, dz = p ? p[2] - c[2] : 0.0f, dd = dx * dx + dz * dz, d = 0.0f;
    if (dd > 0.0f) __asm__("vsqrt.f32 %0, %1" : "=t"(d) : "t"(dd));
    logf("dalaport: carcass %s motion %x frame %d layer1 %x frame %d weight %d/1000 rage %u | hunter %d %d %d: dxz %d "
         "dy %d radius %d point %d %d %d", tail ? "tail" : "head", curMotion(self), (int)motionFrame(self),
         FIELD(uint16_t, self, LAYER1_MOT), (int)FIELD(float, self, LAYER1_FRAME), (int)(layer1Weight(self) * 1000.0f),
         rec[REC_RAGE], p ? (int)p[0] : 0, p ? (int)p[1] : 0, p ? (int)p[2] : 0, (int)d, p ? (int)(p[1] - c[1]) : 0,
         (int)s_rad[tail], (int)c[0], (int)c[1], (int)c[2]);
}
