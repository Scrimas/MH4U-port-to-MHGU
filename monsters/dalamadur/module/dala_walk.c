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
 *
 * Sets (4U data, C): head set 1 = joints 1..5, set 2 = joints 1..4; tail set 1 = joints 140..142; set 0 = none. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "port.h"
#include "em090.h"
#include "dala_efx.h"

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

/* The hunter standing on the body is not pushed by it (walk study 2026-10-22, gu-walkable.md 6b).
 * - Correction (2026-10-22, hurtbox study, C): the push volumes are field 30 (bodydata = 4U emd word 8, enemy+0x75cc,
 *   getter 0x710b0, also read by the hurtbox cache 0x16abac and the hurt pass 0x16c1bc), records whose +10 has no bit
 *   of 0x80d2 (+10 0x80 = hurt only, 0x100 = push only). Field 31 (cambodydata, word 9, +0x75d0, getter 0x710d0) is
 *   read only by the quest camera's sphere (0x17f750, falling back to field 30). sHitPush's player pass 0x17c9d0 (->
 *   0x17cf40) and the camera skip an enemy whose rec+0x528 is set (0x17caa4, 0x17fabc); the update clears it every
 *   frame (0xa5334) before slot 168 (0xae1f4) runs. 4U Dalamadur never writes its twin W+0x55a (C).
 * - The walk study measured the strips against word 9 (wrong list): the push effect on a hunter standing on the back
 *   is S only, but the test after this rule (2026-10-22 21:58) climbed much further than before.
 * - Port (G for 4U's own rule, not traced): while the LOCAL hunter's ground contact is one of the walk pieces (plus
 *   WALK_HOLD frames for jumps between pieces), the half that owns that piece sets rec+0x528. Local only: the flag is
 *   not synced and only the local hunter's push and camera read it on this machine; remote hunters move by net sync (S).
 * - Per half since 2026-10-23 (C, code): one shared hold used to set it on BOTH halves, so standing on the tail (the
 *   only contacts in the 21:58 / 22:57 / 23:44 logs: tail j141) removed every push volume of the head half; test
 *   23:44 hit head part 3 from j141 with the head's nopush 1 (user: "could still walk through the head"). 4U never
 *   turns a push volume off: pass 0xbbe554 gates on +0xb29 (local hunter), W+0x55a (never written for em024 / em083),
 *   the area (0x91f860) and the em list / 0x9a6dc0 timer (C). The lift query (walk_step) keeps the shared hold.
 * Contact (S, static): the hunter's ground helper is hunter+0x2f00 (0x29c288 -> probe 0x4f57f0, type mask 1, owner =
 *   the hunter, segment y +-30, +-300 in one state); +0x100 = contact found (0x4f5924); its contact record +0x10
 *   holds the sCollision handle at +8 and a non-zero +0x34 for an SBC contact (0xc1d5f0 / 0xc3eb0c, carry-along). */
#define REC_NO_PLAYER_PUSH 0x528
#define PL_GROUND     0x2f00                  /* hunter's ground-contact helper */
#define PL_HAS_GROUND (PL_GROUND + 0x100)     /* u8 */
#define PL_CONTACT_H  (PL_GROUND + 0x10 + 8)  /* s32 handle */
#define PL_CONTACT_S  (PL_GROUND + 0x10 + 0x34)
#define WALK_HOLD     45                      /* frames the push stays off after the last contact */

static void *walk_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

static uint32_t walk_push(void *self, uint32_t tail, uint32_t set, uint32_t n, const uint8_t *joints)
{
    static uint32_t s_hold, s_half[2], s_on, s_nlog, s_nraw, s_tick;
    void *pl = walk_hunter();
    int32_t piece = -1;
    if (pl && set && FIELD(uint8_t, pl, PL_HAS_GROUND) && FIELD(uint32_t, pl, PL_CONTACT_S)) {
        int32_t hc = FIELD(int32_t, pl, PL_CONTACT_H);
        for (uint32_t i = 0; i < n; i++)
            if (hc != -1 && hc == FIELD(int32_t, self, F_WALK_H + 4 * i) && !(set == 2 && joints[i] == 5)) piece = i;
    }
    float h[4] = {0};
    if (pl) jointPos(pl, 0, h);
    if (!tail && pl && set && ++s_tick % 120 == 0 && s_nraw < 20) {   /* offsets check (S) */
        s_nraw++;
        logf("dalaport: walk probe hunter %d %d %d (position y %d) contact %u handle %d sbc %x", (int)h[0], (int)h[1],
             (int)h[2], (int)FIELD(float, pl, 0x44), FIELD(uint8_t, pl, PL_HAS_GROUND), FIELD(int32_t, pl, PL_CONTACT_H),
             FIELD(uint32_t, pl, PL_CONTACT_S));
    }
    if (piece >= 0) {
        if (!s_half[tail] && s_nlog < 200) {
            s_nlog++;
            logf("dalaport: walk hunter on %s j%u at %d %d %d (%s push off)", tail ? "tail" : "head", joints[piece],
                 (int)h[0], (int)h[1], (int)h[2], tail ? "tail" : "head");
        } else if (s_on && ++s_on % 30 == 0 && s_nlog < 200) {
            s_nlog++;
            logf("dalaport: walk hunter %s j%u at %d %d %d", tail ? "tail" : "head", joints[piece], (int)h[0],
                 (int)h[1], (int)h[2]);
        }
        if (!s_on) s_on = 1;
        s_hold = 2 * WALK_HOLD;               /* the lift query (walk_step): both halves count it down, 2 calls/frame */
        s_half[tail] = WALK_HOLD;             /* the push: this half's only, one call per frame */
    } else if (s_hold && !--s_hold) {
        if (s_nlog < 200) {
            s_nlog++;
            logf("dalaport: walk hunter off the body at %d %d %d", (int)h[0], (int)h[1], (int)h[2]);
        }
        s_on = 0;
    }
    if (s_half[tail]) {
        FIELD(uint8_t, FIELD(uint8_t *, self, EN_RECORD), REC_NO_PLAYER_PUSH) = 1;
        if (!--s_half[tail] && s_nlog < 200) {
            s_nlog++;
            logf("dalaport: walk %s push on (hunter %d %d %d)", tail ? "tail" : "head", (int)h[0], (int)h[1], (int)h[2]);
        }
    }
    return s_hold != 0;
}

/* 4U's ground query on the body (C, 0x681e44 -> 0x681c84 -> 0x5a4680; gu-walkable.md 6b): a vertical segment from
 * y + 50 down to y - 300 (em024 / em083), the HIGHEST strip triangle whose XZ projection holds the hunter wins, every
 * strip of every piece of the active set (two-sided, no slope limit). GU's ground does not step up onto an
 * overlapping piece (test 2026-10-22: stopped on tail j141 under j140's edge, 35..70 above the feet; the probe
 * 0x4f57f0 looks 30 up), so while the local hunter is on the body (walk_push) each half runs that query on its
 * enabled pieces (data file section WALK = the walk SBC vertices, tools/walk_em090.py) and lifts him onto a higher
 * hit; GU's own ground then holds him there. Lift only: 4U's 300 down (the body sinking under him) is left to GU's
 * carry-along. The hunter's position (this+0x40) is his feet (S). Local hunter only, his position is synced (MP). */
/* 4U 0x6821c8 (C): g = [global+0x5c]; g >= 1: top y + 50 g, bottom y - 300 - 50 g (em024 / em083; -30 / -60 / -120
 * otherwise); g < 1: y + 50 / y - 80. g is the frame step (S: 2 = 4U's 30 Hz logic on 60 fps motions; test
 * 2026-10-22 23:44: with 50 the hunter never got onto j140 and fell under its edge twice) */
#define STEP_UP   100.0f
#define STEP_DOWN 400.0f
static void walk_step(void *self, uint32_t tail, uint32_t set, uint32_t n, const uint8_t *joints)
{
    static uint32_t s_n, s_q[2], s_nq;
    void *pl = walk_hunter();
    uint32_t size = 0;
    int32_t qdy[WALK_MAX];                    /* per piece: highest hit - feet in [-400, +300], or 9999 */
    for (uint32_t i = 0; i < WALK_MAX; i++) qdy[i] = 9999;
    const uint8_t *s = pl ? port_section(FIELD(uint8_t, self, EN_VARIANT) ? SHAH_DALAMADUR_PORT : DALAMADUR_PORT,
                                         "WALK", 0, &size) : 0;
    if (!s || size < 4) return;
    float *p = &FIELD(float, pl, 0x40), best = -1.0e30f;
    uint32_t np = PORT_U32(s, 0), bj = 0;
    for (uint32_t k = 0; k < np && 4 + 8 * (k + 1) <= size; k++) {
        const uint8_t *e = s + 4 + 8 * k;
        uint32_t j = *(const uint16_t *)e, nt = *(const uint16_t *)(e + 2), off = PORT_U32(e, 4), i;
        for (i = 0; i < n && joints[i] != j; i++) ;
        if (i == n || FIELD(int32_t, self, F_WALK_H + 4 * i) == -1 || (set == 2 && j == 5) || off + 36 * nt > size)
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
            if (y <= p[1] + STEP_UP && y >= p[1] - STEP_DOWN && y > best) { best = y; bj = j; }
            int32_t dy = (int32_t)(y - p[1]);
            if (dy >= -400 && dy <= 300 && (qdy[i] == 9999 || dy > qdy[i])) qdy[i] = dy;
        }
    }
    if (++s_q[tail] % 15 == 1 && s_nq < 200) {   /* every 15 frames per half: highest hit - feet per piece (9999 =
                                                * none in [-400, +300]) */
        s_nq++;
        if (tail)
            logf("dalaport: walk query tail feet %d %d %d: j140 %d, j141 %d, j142 %d", (int)p[0], (int)p[1], (int)p[2],
                 qdy[0], qdy[1], qdy[2]);
        else
            logf("dalaport: walk query head feet %d %d %d: j1 %d, j2 %d, j3 %d, j4 %d, j5 %d", (int)p[0], (int)p[1],
                 (int)p[2], qdy[0], qdy[1], qdy[2], qdy[3], qdy[4]);
    }
    if (best > p[1] + 1.0f) {
        if (++s_n <= 60)
            logf("dalaport: walk step %s j%u: hunter %d %d %d lifted +%d", tail ? "tail" : "head", bj, (int)p[0],
                 (int)p[1], (int)p[2], (int)(best - p[1]));
        p[1] = best;
    }
}

/* GU slot 168 (per frame, em012's collision slot) */
void dala_walk_frame(void *self)
{
    static const float k_w1[4] = {0.0f, 0.0f, 0.0f, 1.0f};
    dala_join_frame(self);           /* the tail's bone 0 = the head's (dala_join.c), before the joint matrices */
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
            if (h != -1) colEnable(sc, set != 0 && !(set == 2 && joints[i] == 5), h);
        }
    }
    uint32_t on = walk_push(self, tail, set, n, joints);
    if (!set) return;
    for (uint32_t i = 0; i < n; i++) {
        int32_t h = FIELD(int32_t, self, F_WALK_H + 4 * i);
        if (h == -1 || (set == 2 && joints[i] == 5)) continue;
        float m[16] __attribute__((aligned(16))), q[4] __attribute__((aligned(16))), pos[4];
        jointMtx(self, joints[i], m);
        pos[0] = m[12]; pos[1] = m[13]; pos[2] = m[14]; pos[3] = m[15];
        m[12] = k_w1[0]; m[13] = k_w1[1]; m[14] = k_w1[2]; m[15] = k_w1[3];
        mtxQuat(q, m);
        colMove(sc, h, pos, q, 0);
    }
    if (on) walk_step(self, tail, set, n, joints);
}
