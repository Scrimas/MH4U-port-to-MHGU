/* Walking on Dalamadur's body (goal D4; class-study.md "Walking on the body", gu-walkable.md).
 *
 * 4U: emd word 10 holds walk sets of bone-local ground strips; the class picks the active set every frame (slot 48:
 * head 0x773304, tail 0x8a1fec) into W+0x28e and the enemy manager copies it into its walk slots (0x94cd6c), where the
 * player's ground queries find it. GU has no such engine; its walkable monsters (em012, em084, em087) register their
 * own SBC files in sCollision as ground entries owned by the monster and move them with a joint matrix every frame.
 * tools/walk4u2gu.py turned each 4U joint's strips into one ground SBC (bone-local), shipped in the halves' arcs.
 *
 * Here, as Nakarkos (0x1068220 register, 0x1067e.. release) and Lao-Shan (0xd79a98 move): at spawn each file is
 * fetched by file ID (0x152960 with rCollision; our file_id hook serves the IDs), registered as ground (0xc47f68
 * type 1, the monster's area), owned by the half (0xc47dc8: the owner's own queries skip it) and disabled (0xc47dec).
 * Every frame (GU slot 168, em012's slot) the 4U set rule enables the pieces of the active set and each enabled piece
 * follows its joint (joint matrix 0xc1660 -> quaternion 0x72ea8 -> move request 0xc4754c). On delete the entries are
 * released (0xc482a0) and the resources dropped (0x887660). Every machine runs its own collision; the rule reads only
 * the replayed motion and placement, so all machines agree (MP).
 * On top of GU's own ground (2026-10-25, user: junction back / tail not walkable, no invisible wall at the end of the
 * back, camera stuck on the back): 4U's ground rule in GU's hunter ground function (dala_ground_c), the push volumes
 * left on as in 4U (no rec+0x528), and the walk pieces hidden from the camera's collision sweep (dala_cam_*).
 * Second pass (test 2026-10-25 15:58: junction still not walkable, camera still stuck): the pieces are placed as still
 * entries (teleport flag 1, as Gogmazios' rail cart, stage_cart.c: GU's carry moves a hunter only when its sweep is
 * not blocked, else he stays put while the ground slides under him). Continuous moves filed the tail pieces in GU's
 * moving tree: the log shows the hunter's contact on j141 flipping every 1-2 frames, i.e. airborne half the time, so
 * he never landed on the overlapping j140 (20..100 higher over the last 300 of j141 in motions 2 / 102 and bank 3's
 * 1 / 101, FK of the 4U keys) and ran on under it. 4U has no carry either: its strip query only sets the hunter's
 * height (C, 0x681c84).
 * Third pass (test 2026-10-25 17:27: no ledge jump off the junction's side, camera still stuck vertically): the
 * pieces are off for every hunter's ground ray and for the camera's terrain-tilt ray too; the body counts only
 * through 4U's windows (local and remote players, dala_ground_c), as 4U's strips are not stage collision.
 *
 * Sets (4U data, C): head set 1 = joints 1..5, set 2 = joints 1..4; tail set 1 = joints 140..142; set 0 = none. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "port.h"
#include "em090.h"
#include "dala_efx.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define SRES_PTR   0x18571e8u   /* sResource singleton (em084 0x1068234) */
#define DTI_RCOLL  0x2125dd4u   /* rCollision DTI */
#define SCOL_PTR   0x21270e0u   /* sCollision singleton */
#define EN_AREA    0x1054u      /* u8 the monster's area (em084 registers with it) */
typedef void *(*resGet_t)(void *sres, uint32_t file_id, void *dti);
#define resGet     FN(resGet_t, 0x152960)
typedef void (*resRef_t)(void *res);
#define resAddRef  FN(resRef_t, 0x887648)
#define resRelease FN(resRef_t, 0x887660)
typedef int32_t (*colAdd_t)(void *scol, void *res, uint32_t type, uint32_t area, uint32_t a5, uint32_t a6);
#define colAdd     FN(colAdd_t, 0xc47f68)
typedef void (*colOwner_t)(void *scol, void *owner, int32_t h);
#define colOwner   FN(colOwner_t, 0xc47dc8)
typedef void (*colEnable_t)(void *scol, uint32_t on, int32_t h);
#define colEnable  FN(colEnable_t, 0xc47dec)
typedef void (*colMove_t)(void *scol, int32_t h, const float *pos, const float *quat, uint32_t flag);
#define colMove    FN(colMove_t, 0xc4754c)
typedef void (*colDel_t)(void *scol, int32_t h);
#define colDel     FN(colDel_t, 0xc482a0)
typedef void (*jointMtx_t)(void *self, uint32_t joint, float *out16);
#define jointMtx   FN(jointMtx_t, 0xc1660)
typedef void (*mtxQuat_t)(float *quat, const float *m16);
#define mtxQuat    FN(mtxQuat_t, 0x72ea8)

/* walk SBC file IDs (monsters/dalamadur/tools/em090_00 / em091_00 manifests, extras walk_bNNN; Shah's arcs carry the
 * same files); joints = 4U joint IDs = our model's */
#define WALK_MAX 5
static const uint32_t k_head_ids[5] = {0x107a1, 0x107a2, 0x107a3, 0x107a4, 0x107a5};
static const uint8_t k_head_joints[5] = {1, 2, 3, 4, 5};
static const uint32_t k_tail_ids[3] = {0x10888, 0x10889, 0x1088a};
static const uint8_t k_tail_joints[3] = {140, 141, 142};

static void *s_obj[2];        /* this machine's live halves with walk pieces: [0] head, [1] tail */
#define WALKERS 4
static struct { void *pl; uint32_t on; } s_walker[WALKERS];   /* remote hunters' 4U +0x9a8 (dala_ground_c) */

static void *scol(void) { return *(void **)MAIN(SCOL_PTR); }

static int is_tail(void *self) { return (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff); }

void dala_walk_spawn(void *self)
{
    uint32_t tail = is_tail(self), n = tail ? 3 : 5;
    const uint32_t *ids = tail ? k_tail_ids : k_head_ids;
    void *sres = *(void **)MAIN(SRES_PTR), *sc = scol();
    FIELD(uint8_t, self, F_WALK_SET) = 0xff;
    for (uint32_t i = 0; i < WALK_MAX; i++) {
        FIELD(int32_t, self, F_WALK_H + 4 * i) = -1;
        FIELD(void *, self, F_WALK_R + 4 * i) = 0;
    }
    s_obj[tail] = self;
    for (uint32_t i = 0; i < WALKERS; i++) s_walker[i].pl = 0;
    if (!sres || !sc) { logf("dalaport: walk: no sResource / sCollision (%x %x)", (uint32_t)sres, (uint32_t)sc); return; }
    for (uint32_t i = 0; i < n; i++) {
        void *res = resGet(sres, ids[i], (void *)MAIN(DTI_RCOLL));
        if (!res) { logf("dalaport: walk: file %x not loaded", ids[i]); continue; }
        resAddRef(res);
        resRelease(res);                      /* as em084: store, addref + release; released once on delete */
        FIELD(void *, self, F_WALK_R + 4 * i) = res;
        int32_t h = colAdd(sc, res, 1, FIELD(uint8_t, self, EN_AREA), 1, 0);
        colOwner(sc, self, h);
        colEnable(sc, 0, h);
        FIELD(int32_t, self, F_WALK_H + 4 * i) = h;
    }
    logf("dalaport: walk %s: %u pieces, handles %d %d %d area %u", tail ? "tail" : "head", n,
         FIELD(int32_t, self, F_WALK_H), FIELD(int32_t, self, F_WALK_H + 4), FIELD(int32_t, self, F_WALK_H + 8),
         FIELD(uint8_t, self, EN_AREA));
}

void dala_walk_release(void *self)
{
    void *sc = scol();
    if (s_obj[is_tail(self)] == self) s_obj[is_tail(self)] = 0;
    for (uint32_t i = 0; i < WALK_MAX; i++) {
        int32_t h = FIELD(int32_t, self, F_WALK_H + 4 * i);
        void *res = FIELD(void *, self, F_WALK_R + 4 * i);
        if (h != -1 && sc) colDel(sc, h);
        if (res) resRelease(res);
        FIELD(int32_t, self, F_WALK_H + 4 * i) = -1;
        FIELD(void *, self, F_WALK_R + 4 * i) = 0;
    }
}

/* the 4U set rule (C): placement != 0 -> none. Head: motions 63, 65, 573..577, 770, 771, 829 -> none; motion 3
 * only while motionCheckB(2, 186) (4U 0x93906c) else none; otherwise head part 0 rank != 0 -> set 1, else set 2.
 * Tail: motions 163, 165, 673..677, 870, 871, 929 -> none; motion 103 as the head's 3; otherwise set 1. */
static uint32_t walk_set(void *self, uint32_t tail)
{
    if (MODE(self) != 0) return 0;
    uint32_t m = curMotion(self), o = tail ? 100 : 0;
    if (m == 63 + o || m == 65 + o || (m >= 573 + o && m <= 577 + o) || m == 770 + o || m == 771 + o ||
        m == 829 + o) return 0;
    if (m == 3 + o && !motionCheckB(self, 2, 0, 186.0f, 0.0f)) return 0;
    if (tail) return 1;
    return FN(uint32_t (*)(void *, uint32_t), 0x9d428)(self, 0) ? 1 : 2;   /* part rank [4U 0x94741c] */
}

uint32_t dala_walk_set(void *self) { return walk_set(self, is_tail(self)); }

/* piece i of a half in the active set (set 2 leaves the head piece j5 out) */
static int piece_on(uint32_t set, const uint8_t *joints, uint32_t i)
{
    return set != 0 && set != 0xff && !(set == 2 && joints[i] == 5);
}

/* every piece of both halves off (0) or back to its set (1), around the GU queries 4U's strips never meet */
static void walk_enable_all(uint32_t on)
{
    void *sc = scol();
    if (!sc) return;
    for (uint32_t tail = 0; tail < 2; tail++) {
        void *self = s_obj[tail];
        if (!self) continue;
        uint32_t set = FIELD(uint8_t, self, F_WALK_SET), n = tail ? 3 : 5;
        const uint8_t *joints = tail ? k_tail_joints : k_head_joints;
        for (uint32_t i = 0; i < n; i++) {
            int32_t h = FIELD(int32_t, self, F_WALK_H + 4 * i);
            if (h != -1) colEnable(sc, on && piece_on(set, joints, i), h);
        }
    }
}

/* Push volumes (2026-10-25): left on while the hunter walks on the body, as in 4U (C): the player pass 0xbbe688 ->
 * 0xbbf4d8 gates only on the local player (0xd04fbc), W+0x55a (never written for em024 / em083) and the area
 * (0x91f8bc), and pushes horizontally unless the player state +0x370 is 2; GU's 0x17cf40 keeps only the x / z of the
 * hunter's push vector (0x17d548..0x17d5a8, C). The volumes 4U switches on only while the body is walkable (+12 bit
 * 0x400, written by head slot 48 0x773304 / tail 0x8a2248: head bodydata records 57..60, push only, radius 200 / 800
 * at the snout tip and over the chest; tail record 23, radius 800 past joint 142) are the invisible walls at the
 * ends of the walkable back and tail. The port's earlier rule (rec+0x528 set on the half under the local hunter)
 * removed those walls and the head's volumes ("walk through the head", "no invisible wall"); with the bodydata's
 * off2.z restored (tools/emdata4u.py) they stand where 4U puts them. */
static void *walk_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* 4U's ground query on the body (C, 0x681e44 -> 0x681c84 -> 0x5a4680, 0x6821c8; gu-walkable.md 6b): a vertical
 * segment from y + 50 g down to y - 300 - 50 g (the -300 for em024 / em083 only; g = [global+0x5c], 2 = the 60-unit
 * time base: +100 / -400), the HIGHEST triangle of every strip of every active piece of BOTH halves (the manager's two
 * slots) whose XZ projection holds the hunter, two-sided, no slope limit. Data: section WALK = the walk SBC vertices
 * per joint (tools/walk_em090.py), posed with each half's joint matrices. 1 = found, *y = its height, *bj = joint. */
#define STEP_UP   100.0f
#define STEP_DOWN 400.0f
#define NO_Y      (-1.0e30f)
/* any (optional): per joint 140 / 141 / 1, the highest triangle at the hunter's XZ whatever its height (log) */
static int strip_query(const float *p, float *y_out, uint32_t *bj, float *any)
{
    float best = NO_Y;
    for (uint32_t tail = 0; tail < 2; tail++) {
        void *self = s_obj[tail];
        if (!self) continue;
        uint32_t set = FIELD(uint8_t, self, F_WALK_SET), n = tail ? 3 : 5, size = 0;
        const uint8_t *joints = tail ? k_tail_joints : k_head_joints;
        if (!set || set == 0xff) continue;
        const uint8_t *s = port_section(FIELD(uint8_t, self, EN_VARIANT) ? SHAH_DALAMADUR_PORT : DALAMADUR_PORT,
                                        "WALK", 0, &size);
        if (!s || size < 4) continue;
        for (uint32_t k = 0, np = PORT_U32(s, 0); k < np && 4 + 8 * (k + 1) <= size; k++) {
            const uint8_t *e = s + 4 + 8 * k;
            uint32_t j = *(const uint16_t *)e, nt = *(const uint16_t *)(e + 2), off = PORT_U32(e, 4), i;
            for (i = 0; i < n && joints[i] != j; i++) ;
            if (i == n || FIELD(int32_t, self, F_WALK_H + 4 * i) == -1 || !piece_on(set, joints, i) ||
                off + 36 * nt > size)
                continue;
            float m[16] __attribute__((aligned(16)));
            jointMtx(self, j, m);
            const float *t = (const float *)(s + off);
            for (uint32_t q = 0; q < nt; q++, t += 9) {
                float w[3][3];
                for (int v = 0; v < 3; v++)
                    for (int c = 0; c < 3; c++)
                        w[v][c] = t[3 * v] * m[c] + t[3 * v + 1] * m[4 + c] + t[3 * v + 2] * m[8 + c] + m[12 + c];
                float d = (w[1][2] - w[2][2]) * (w[0][0] - w[2][0]) + (w[2][0] - w[1][0]) * (w[0][2] - w[2][2]);
                if (d > -1e-6f && d < 1e-6f) continue;
                float l1 = ((w[1][2] - w[2][2]) * (p[0] - w[2][0]) + (w[2][0] - w[1][0]) * (p[2] - w[2][2])) / d;
                float l2 = ((w[2][2] - w[0][2]) * (p[0] - w[2][0]) + (w[0][0] - w[2][0]) * (p[2] - w[2][2])) / d;
                float l3 = 1.0f - l1 - l2;
                if (l1 < 0.0f || l2 < 0.0f || l3 < 0.0f) continue;
                float y = l1 * w[0][1] + l2 * w[1][1] + l3 * w[2][1];
                if (any) {
                    float *a = j == 140 ? &any[0] : j == 141 ? &any[1] : j == 1 ? &any[2] : 0;
                    if (a && y > *a) *a = y;
                }
                if (y <= p[1] + STEP_UP && y >= p[1] - STEP_DOWN && y > best) { best = y; *bj = j; }
            }
        }
    }
    if (best < -1.0e29f) return 0;
    *y_out = best;
    return 1;
}

/* GU's hunter ground function 0x2e846c (Gogmazios' stage_cart.c notes, C), a virtual of every hunter class (vtables
 * 0x1749524..), so it runs for each hunter on the machine: ray query 0x18192c over the still and moving type-1 trees,
 * the highest hit up to y + 100 -> [sp+0x1c] (r5 points at it) and r0 = 1; hunter+0x10f0 = r1; a grounded hunter
 * (hunter+0x2505 != 2) more than 30 above r1 goes airborne (0x2e86fc), within 30 snaps to it; any hunter below
 * [sp+0x1c] is put on it, which is how an airborne one lands (0x2e88e4 / 0x2e8908). Hooks: dala_ground_pre at
 * 0x2e8590 (before the query) and dala_ground at 0x2e85ac (after it and the cart hook at 0x2e85a4, before the store:
 * r0 = hit, r1 = the ground y, r4 = the hunter, r5 = &[sp+0x1c]).
 * 4U (C, 0x681e44 -> 0x6821a0..0x682300, every player each frame): the highest strip between y + 50 g and y - 30 - 50 g
 * (y - 60 - 50 g for the local player who stood on the monster last frame, +0x9a8; y - 300 - 50 g for a remote one on
 * em024 / em083, -120 on other monsters) sets his height (0x6822c8); outside that window the strip does not exist for
 * him and his ground is the stage's. g = the step [sMain+0x5c], 2 at 4U's 30 fps.
 * Third pass (test 2026-10-25 17:27, user: running off near the junction to climb the wall plays no jump): GU's ray
 * saw the pieces at any depth. Off j140's 83 deg side it found the side 100..300 below him, and GU's airborne choice
 * for a moving hunter with a drop <= 300 (0x2e8a84) is a plain fall (0x2a01d8, no animation) instead of the ledge
 * jump (action 4/1, 0x2e8ab8, S); 4U's hunter sees the floor there (-848). Now the pieces are off for every hunter's
 * ray and the body is 4U's window only: found -> r0 / r1 / [sp+0x1c] = its height, and a grounded hunter more than 30
 * above it is put on it. The local window is counted per 4U frame (2 time units of hunter+0x1c, C 0x2e9a54): the drop
 * from his highest height over the last 4U frame, so at 120 fps he leaves the 83 deg side where 4U's 30-fps hunter
 * does (S; a per-call window would keep a dashing hunter on it down to its edge). Remote hunters (user's side note:
 * 4U's partner rule) get the remote window per call: their position is the owner's, synced, so this only keeps them
 * on the moving body on this screen (MP). Logs: piece changes, leaving / released and the action on the call after
 * (4/1 = ledge jump), remote hunters landing on the body, and a trace while tail j140 lies over or under the local
 * hunter (every 6th call, <= 400 lines). */
#define PL_AIR_STATE  0x2505   /* u8: 2 = airborne (the ground function's branch at 0x2e85c8) */
#define PL_DT         0x1c     /* f32 the hunter's step in 60-fps frames (pos += vel * dt, 0x2e9a54) */
#define PL_ACT_CAT    0x2506   /* u16 current action category / number (0x2e8770, 0x2a05b8; S) */
#define PL_ACT_NUM    0x250a
#define WIN_G         50.0f    /* 4U 0x682228: 50 g above and below */
#define WIN_OFF       30.0f    /* 4U 0x682224: not on the monster last frame */
#define WIN_ON        60.0f    /* 4U 0x682218: the local player on it */
#define WIN_REMOTE    300.0f   /* 4U 0x68221c: a remote player on em024 / em083 */
#define FRAME_4U      2.0f     /* 4U's step at its 30 fps */
#define HIST          8
static uint32_t s_on, s_hidden;            /* the local hunter on the body (last call); pieces off for a ray */
static float s_hist_y[HIST], s_hist_dt[HIST];
static uint32_t s_hist_n, s_hist_k;

static float pl_dt(void *pl)
{
    float dt = FIELD(float, pl, PL_DT);
    return dt > 0.0f && dt < 60.0f ? dt : 1.0f;
}

/* the local hunter's highest height on the body over the last 4U frame before this call */
static float hist_top(float y, float span, float dt)
{
    float top = y, t = dt;
    for (uint32_t i = 0; i < s_hist_n && t < span; i++) {
        uint32_t k = (s_hist_k + HIST - 1 - i) % HIST;
        if (s_hist_y[k] > top) top = s_hist_y[k];
        t += s_hist_dt[k];
    }
    return top;
}

static void hist_add(float y, float dt)
{
    s_hist_y[s_hist_k] = y;
    s_hist_dt[s_hist_k] = dt;
    s_hist_k = (s_hist_k + 1) % HIST;
    if (s_hist_n < HIST) s_hist_n++;
}

/* the strip as this call's ground: r0 / r1 and the query's slot that the landing test reads (r5; the trampoline
 * keeps r0..r5, r12, lr at regs with the hooked frame's sp right above them, so [sp+0x1c] = regs + 60) */
static void report(uint32_t *regs, float h)
{
    static uint32_t s_n;
    union { uint32_t u; float f; } v;
    v.f = h;
    regs[R0] = 1;
    regs[R1] = v.u;
    if (regs[R5] == (uint32_t)(uintptr_t)regs + 60) *(float *)(uintptr_t)regs[R5] = h;
    else if (++s_n <= 5)
        logf("dalaport: walk ground: r5 %x is not [sp+0x1c] (%x), landing slot kept", regs[R5],
             (uint32_t)(uintptr_t)regs + 60);
}

/* a remote hunter: 4U's remote window, per call */
static void ground_remote(uint32_t *regs, uint8_t *pl)
{
    static uint32_t s_n;
    uint32_t i, bj = 0, was, air = FIELD(uint8_t, pl, PL_AIR_STATE);
    for (i = 0; i < WALKERS && s_walker[i].pl != pl; i++) ;
    if (i == WALKERS) {
        for (i = 0; i < WALKERS && s_walker[i].pl; i++) ;
        if (i == WALKERS) i = 0;
        s_walker[i].pl = pl;
        s_walker[i].on = 0;
    }
    float *p = &FIELD(float, pl, 0x40), h = 0.0f, dt = pl_dt(pl), span = dt > FRAME_4U ? dt : FRAME_4U;
    union { uint32_t u; float f; } gu = {regs[R1]};
    was = s_walker[i].on;
    s_walker[i].on = 0;
    if (!strip_query(p, &h, &bj, 0) || (regs[R0] == 1 && gu.f >= h - 1.0f) ||
        h < p[1] - (was ? WIN_REMOTE : WIN_OFF) - WIN_G * span)
        return;
    if (air != 2 && h < p[1] - 30.0f) p[1] = h;
    report(regs, h);
    s_walker[i].on = air != 2;
    if (!was && s_walker[i].on && ++s_n <= 40)
        logf("dalaport: walk ground remote hunter %x on j%u at %d %d %d", (uint32_t)(uintptr_t)pl, bj, (int)p[0],
             (int)p[1], (int)p[2]);
}

int dala_ground_pre_c(uint32_t *regs)
{
    (void)regs;
    if (s_obj[0] || s_obj[1]) {
        walk_enable_all(0);
        s_hidden = 1;
    }
    return 0;
}

int dala_ground_c(uint32_t *regs)
{
    static uint32_t s_bj, s_n, s_ns, s_nt, s_tick, s_left;
    uint8_t *pl = (uint8_t *)(uintptr_t)regs[R4];
    if (s_hidden) {
        walk_enable_all(1);
        s_hidden = 0;
    }
    if (!s_obj[0] && !s_obj[1]) return 0;
    if (pl != walk_hunter()) {
        ground_remote(regs, pl);
        return 0;
    }
    float *p = &FIELD(float, pl, 0x40), h = 0.0f, g, dt = pl_dt(pl), span = dt > FRAME_4U ? dt : FRAME_4U;
    float any[3] = {NO_Y, NO_Y, NO_Y};
    uint32_t bj = 0, hit = regs[R0] == 1, was = s_on, air = FIELD(uint8_t, pl, PL_AIR_STATE);
    union { uint32_t u; float f; } gu = {regs[R1]};
    g = gu.f;
    if (s_left) {                              /* the call after leaving: GU's choice there (4/1 = the ledge jump) */
        s_left = 0;
        if (++s_n <= 200)
            logf("dalaport: walk ground after leaving: action %u/%u air %u at %d %d %d (step %d/100)",
                 FIELD(uint16_t, pl, PL_ACT_CAT), FIELD(uint16_t, pl, PL_ACT_NUM), air, (int)p[0], (int)p[1],
                 (int)p[2], (int)(dt * 100.0f));
    }
    int found = strip_query(p, &h, &bj, any);
    if (any[0] > NO_Y && ++s_tick % 6 == 0 && ++s_nt <= 400)
        logf("dalaport: walk trace at %d %d %d air %u | GU %s %d | body %s j%u %d | j140 %d j141 %d j1 %d",
             (int)p[0], (int)p[1], (int)p[2], air, hit ? "hit" : "none", hit ? (int)g : 0, found ? "on" : "off",
             found ? bj : 0, found ? (int)h : 0, (int)any[0], any[1] > NO_Y ? (int)any[1] : 0,
             any[2] > NO_Y ? (int)any[2] : 0);
    s_on = 0;
    if (!found || (hit && g >= h - 1.0f)) {   /* no strip in reach, or the stage ground at its height or higher */
        if (was && ++s_n <= 200)
            logf("dalaport: walk ground off the body at %d %d %d air %u (GU ground %s %d)", (int)p[0], (int)p[1],
                 (int)p[2], air, hit ? "hit" : "none", hit ? (int)g : 0);
        s_left = was;
        s_hist_n = 0;
        return 0;
    }
    float top = was && air != 2 ? hist_top(p[1], span, dt) : p[1];
    float low = top - (was && air != 2 ? WIN_ON : WIN_OFF) - WIN_G * span;
    if (h < low) {                            /* below 4U's window: the stage's ground */
        if (was && ++s_n <= 200)
            logf("dalaport: walk ground j%u released %d below his height over the last 4U frame (window %d) at "
                 "%d %d %d air %u (GU ground %s %d)", bj, (int)(top - h), (int)(top - low), (int)p[0], (int)p[1],
                 (int)p[2], air, hit ? "hit" : "none", hit ? (int)g : 0);
        s_left = was;
        s_hist_n = 0;
        return 0;
    }
    if (air != 2 && h < p[1] - 30.0f) {       /* 4U sets his height; GU would make him airborne */
        if (++s_ns <= 60)
            logf("dalaport: walk ground j%u: hunter kept on the body %d below (%d %d %d)", bj, (int)(p[1] - h),
                 (int)p[0], (int)p[1], (int)p[2]);
        p[1] = h;
    }
    report(regs, h);
    if (air == 2) return 0;                   /* over the body in the air: GU lands him when he reaches it */
    s_on = 1;
    hist_add(h, dt);
    if ((!was || bj != s_bj) && ++s_n <= 200)
        logf("dalaport: walk ground j%u at %d %d %d: %d air %u (GU ground %s %d)", bj, (int)p[0], (int)p[1], (int)p[2],
             (int)h, air, hit ? "hit" : "none", hit ? (int)g : 0);
    s_bj = bj;
    return 0;
}

/* GU's quest camera collision step 0x26934 (uQuestCamera; flags bit 1 = the monsters' camera bodies 0x17fa4c, bit 2 =
 * the stage sweep 0x183724 with type mask 3, C) sees our type-1 walk ground like stage floor; 4U's walk strips are
 * not stage collision: its camera tests only the monsters' word-9 camera bodies (0xc02444 -> 0xbbe810 -> 0xbbfc1c
 * mode 1, no exception for em024 / em083, C). Hooks at the step's entry and its only exit 0x26e34 (`sub sp, r11, #96`
 * .. pop pc) switch the pieces off for the sweep and back on. The camera bodies stay on, as in 4U: the 15:58 pass
 * skipped them (rec+0x528) while the hunter was on the body, which did not free the camera (test 17:27); removed.
 * Test 2026-10-25 17:27, still no vertical control on the back. GU's camera adds the slope under the hunter to its
 * pitch (C): every 4 frames 0x238e0 casts a ground ray (0x182f70, type 1) from y + 100 to y - 3000 under him, keeps
 * the hit's normal (cam+0xa40) and turns it into a pitch along the view (cam+0xa54); 0x23d80 eases it (cam+0xa5c) and
 * adds it to the base pitch cam+0x9e0 (the stick's), the tilt scaled by (8192 - |base|) / 8192 while the hunter's
 * state word +0x2510 has bit 0 and cam+0xa30 is 0: pitch = T (1 - |u| / 8192) + u, which stops moving with u at
 * T = 45 deg. The ray met our pieces (back 20..45 deg, chest 35..55, flanks 60..90; S: the cause); on 4U's body its
 * camera has no such ground under the hunter. Hooks at 0x238e0's entry and its only exit 0x23938 switch the pieces
 * off for it; the exit logs the tilt while the local hunter is on the body (every 60th call, <= 80 lines). */
int dala_cam_begin_c(uint32_t *regs)
{
    (void)regs;
    walk_enable_all(0);
    return 0;
}

int dala_cam_end_c(uint32_t *regs)
{
    (void)regs;
    walk_enable_all(1);
    return 0;
}

int dala_camtilt_begin_c(uint32_t *regs)
{
    (void)regs;
    walk_enable_all(0);
    return 0;
}

static int cam_deg(uint32_t a) { return (int)(int16_t)(uint16_t)a * 360 / 65536; }

int dala_camtilt_end_c(uint32_t *regs)
{
    static uint32_t s_n, s_tick;
    uint8_t *cam = (uint8_t *)(uintptr_t)regs[R4];
    walk_enable_all(1);
    if (s_on && ++s_tick % 60 == 0 && ++s_n <= 80)
        logf("dalaport: cam tilt %d deg (ground normal %d %d %d / 1000), base pitch %d, pitch %d",
             cam_deg(FIELD(uint32_t, cam, 0xa54)), (int)(FIELD(float, cam, 0xa40) * 1000.0f),
             (int)(FIELD(float, cam, 0xa44) * 1000.0f), (int)(FIELD(float, cam, 0xa48) * 1000.0f),
             cam_deg(FIELD(uint32_t, cam, 0x9e0)), cam_deg(FIELD(uint32_t, cam, 0x9d8)));
    return 0;
}

/* GU slot 168 (per frame, em012's collision slot) */
void dala_walk_frame(void *self)
{
    static const float k_w1[4] = {0.0f, 0.0f, 0.0f, 1.0f};
    dala_join_frame(self);           /* the tail's bone 0 = the head's (dala_join.c), before the joint matrices */
    dala_carcass_lock(self);         /* dala_carve.c: the dead body holds the pose its death motion ended in */
    uint32_t tail = is_tail(self), n = tail ? 3 : 5, set = walk_set(self, tail);
    const uint8_t *joints = tail ? k_tail_joints : k_head_joints;
    void *sc = scol();
    if (!sc) return;
    if (set != FIELD(uint8_t, self, F_WALK_SET)) {
        static uint32_t s_n;
        if (++s_n <= 60) logf("dalaport: walk %s set %u -> %u motion %x mode %u", tail ? "tail" : "head",
                              FIELD(uint8_t, self, F_WALK_SET), set, curMotion(self), MODE(self));
        FIELD(uint8_t, self, F_WALK_SET) = (uint8_t)set;
        for (uint32_t i = 0; i < n; i++) {
            int32_t h = FIELD(int32_t, self, F_WALK_H + 4 * i);
            if (h != -1) colEnable(sc, piece_on(set, joints, i), h);
        }
    }
    if (!set) return;
    for (uint32_t i = 0; i < n; i++) {
        int32_t h = FIELD(int32_t, self, F_WALK_H + 4 * i);
        if (h == -1 || !piece_on(set, joints, i)) continue;
        float m[16] __attribute__((aligned(16))), q[4] __attribute__((aligned(16))), pos[4];
        jointMtx(self, joints[i], m);
        pos[0] = m[12]; pos[1] = m[13]; pos[2] = m[14]; pos[3] = m[15];
        m[12] = k_w1[0]; m[13] = k_w1[1]; m[14] = k_w1[2]; m[15] = k_w1[3];
        mtxQuat(q, m);
        colMove(sc, h, pos, q, 1);   /* still entry (teleport): no GU carry, the ground query still sees it */
    }
}
