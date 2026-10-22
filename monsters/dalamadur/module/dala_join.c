/* Joining the two halves into one body (test 2026-10-21: tail floating, a body section missing, an isolated
 * climbable piece near the arena centre).
 *
 * Data (4U em024.arc, C): one skeleton for both halves. Bone 0 (identity bind) is the junction: the head chain
 * 1..16 / 101.. / 120.. runs along +z from it, the tail chain 200 -> 140..150 (-1600 z steps) -> 151..157 along -z,
 * and both halves' open cut is one cross-section loop weighted 100 % to bone 0 (class-study.md "Where the body is
 * cut"). All 47 head motions (banks em024_0 / 2 / 3) animate bone 0; none of the 42 tail motions (N + 100) does:
 * they animate 200 (constant identity) and 140..157 only, i.e. the tail is authored in the frame of the head's bone 0.
 * Forward kinematics of head motion 1 + tail motion 101 (reference frames): with the tail's bone 0 at rest the tail
 * rises to y ~6000-6800 (joint 154 at 5995, as the GU log showed); with the head's bone-0 transform it continues
 * from the head's cut down to y ~-2700 and back up to ~3200 at the tip.
 * The 4U code that hands bone 0 to the tail was not found (classes, uEnemy init 0x94e6f4, emConstraint 0x91917c,
 * uCoord parent 0x6d3fd0, the draw-time parent skinning 0x95a4ec: none is set up for em 83).
 *
 * GU: every frame (slot 168, the per-frame joint hook after the motion update, called from the enemy update 0xae1f4;
 * Rajang's 0xde5f80 sets joint locals there with 0x72438, which writes the same fields as below: quaternion +0x60,
 * translation +0x80) the tail's bone 0 gets the head's bone-0 transform in world space:
 * tail j0 local = head j0 local x head world matrix x inverse(tail world matrix). While both objects stand on the same
 * point (the normal case) that is a plain copy of the head's local rotation and translation. Both halves call it
 * (head: writes into the tail, tail: reads from the head), so the tail is current whichever half updates first.
 * MP: computed per machine from the local head's replayed motion; no network data. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

#define J_IDS     0x498   /* u8[256] joint id -> index (0xff = none) */
#define J_ARRAY   0x494   /* joints, 160 bytes each */
#define J_SIZE    160u
#define J_WORLD   0x10    /* joint world matrix (16 floats, translation at +0x40) */
#define J_QUAT    0x60    /* local rotation quaternion x, y, z, w */
#define J_TRANS   0x80    /* local translation x, y, z, 0 */
#define CO_WMAT   0xb0    /* uCoord world matrix (0x8a8448: = local matrix +0x70 without a parent) */

typedef void (*mtxQuat_t)(float *quat, const float *m16);
#define mtxQuat   FN(mtxQuat_t, 0x72ea8)   /* row-vector matrix -> quaternion (0x72438's body) */

static float *joint_of(void *obj, uint32_t id)
{
    uint8_t *ids = FIELD(uint8_t *, obj, J_IDS), *joints = FIELD(uint8_t *, obj, J_ARRAY);
    if (!ids || !joints || ids[id] == 0xff) return 0;
    return (float *)(joints + J_SIZE * ids[id]);
}

static int is_tail(void *self) { return (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff); }

static float absf(float x) { return x < 0.0f ? -x : x; }

static float sqrt_f(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

/* row-vector 4x4 product o = a x b (affine: column 3 = 0, 0, 0, 1) */
static void mul4(float *o, const float *a, const float *b)
{
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            o[4 * i + j] = a[4 * i] * b[j] + a[4 * i + 1] * b[4 + j] + a[4 * i + 2] * b[8 + j] +
                           a[4 * i + 3] * b[12 + j];
}

/* inverse of an affine row-vector matrix (rows 0..2 = A, row 3 = t): [A^-1, 0; -t A^-1, 1]; 0 if singular */
static int inv_affine(float *o, const float *m)
{
    float a = m[0], b = m[1], c = m[2], d = m[4], e = m[5], f = m[6], g = m[8], h = m[9], k = m[10];
    float c0 = e * k - f * h, c1 = f * g - d * k, c2 = d * h - e * g;
    float det = a * c0 + b * c1 + c * c2;
    if (absf(det) < 1e-12f) return 0;
    float r = 1.0f / det;
    o[0] = c0 * r; o[1] = (c * h - b * k) * r; o[2] = (b * f - c * e) * r; o[3] = 0.0f;
    o[4] = c1 * r; o[5] = (a * k - c * g) * r; o[6] = (c * d - a * f) * r; o[7] = 0.0f;
    o[8] = c2 * r; o[9] = (b * g - a * h) * r; o[10] = (a * e - b * d) * r; o[11] = 0.0f;
    for (int j = 0; j < 3; j++) o[12 + j] = -(m[12] * o[j] + m[13] * o[4 + j] + m[14] * o[8 + j]);
    o[15] = 1.0f;
    return 1;
}

/* local matrix of a joint from its quaternion and translation (pj_joint_get_local, em089_pile.c) */
static void joint_local(const float *jt, float *m)
{
    const float *q = jt + J_QUAT / 4, *t = jt + J_TRANS / 4;
    float x = q[0], y = q[1], z = q[2], w = q[3];
    m[0] = 1.0f - 2.0f * (y * y + z * z); m[1] = 2.0f * (x * y + z * w);        m[2] = 2.0f * (x * z - y * w);
    m[4] = 2.0f * (x * y - z * w);        m[5] = 1.0f - 2.0f * (x * x + z * z); m[6] = 2.0f * (y * z + x * w);
    m[8] = 2.0f * (x * z + y * w);        m[9] = 2.0f * (y * z - x * w);        m[10] = 1.0f - 2.0f * (x * x + y * y);
    m[3] = m[7] = m[11] = 0.0f;
    m[12] = t[0]; m[13] = t[1]; m[14] = t[2]; m[15] = 1.0f;
}

static int same_coord(const float *a, const float *b)
{
    for (int i = 0; i < 15; i++) {
        if ((i & 3) == 3) continue;
        if (absf(a[i] - b[i]) > (i >= 12 ? 0.5f : 1e-4f)) return 0;
    }
    return 1;
}

static void join_log(void *head, void *tail, const float *hj, const float *tj, const char *path)
{
    static uint32_t s_n, s_frames;
    if (++s_frames % 300 != 31 || ++s_n > 8) return;
    const float *hw = hj + J_WORLD / 4 + 12, *tw = tj + J_WORLD / 4 + 12;
    float dx = hw[0] - tw[0], dy = hw[1] - tw[1], dz = hw[2] - tw[2];
    logf("dalaport: join %s head mot %x frame %d tail mot %x frame %d j0 head %d %d %d tail %d %d %d gap %d", path,
         curMotion(head), (int)motionFrame(head), curMotion(tail), (int)motionFrame(tail), (int)hw[0], (int)hw[1],
         (int)hw[2], (int)tw[0], (int)tw[1], (int)tw[2], (int)sqrt_f(dx * dx + dy * dy + dz * dz));
}

/* both halves, every frame, before dala_walk_frame (GU slot 168) */
void dala_join_frame(void *self)
{
    void *other = dala_partner(self);
    if (!other) return;
    void *head = is_tail(self) ? other : self, *tail = is_tail(self) ? self : other;
    float *hj = joint_of(head, 0), *tj = joint_of(tail, 0);
    if (!hj || !tj) return;
    const float *wh = &FIELD(float, head, CO_WMAT), *wt = &FIELD(float, tail, CO_WMAT);
    if (same_coord(wh, wt)) {                 /* both objects on the same point: copy the local transform */
        for (int i = 0; i < 4; i++) tj[J_QUAT / 4 + i] = hj[J_QUAT / 4 + i];
        for (int i = 0; i < 3; i++) tj[J_TRANS / 4 + i] = hj[J_TRANS / 4 + i];
        tj[J_TRANS / 4 + 3] = 0.0f;
        if (self == tail) join_log(head, tail, hj, tj, "copy");
        return;
    }
    float mh[16], p[16], wi[16], mt[16] __attribute__((aligned(16))), q[4] __attribute__((aligned(16)));
    if (!inv_affine(wi, wt)) return;
    joint_local(hj, mh);
    mul4(p, mh, wh);
    mul4(mt, p, wi);
    for (int r = 0; r < 3; r++) {             /* rotation rows to unit length (a size difference is not carried) */
        float *v = mt + 4 * r, n = sqrt_f(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
        if (n > 1e-6f) { v[0] /= n; v[1] /= n; v[2] /= n; }
    }
    mtxQuat(q, mt);
    for (int i = 0; i < 4; i++) tj[J_QUAT / 4 + i] = q[i];
    for (int i = 0; i < 3; i++) tj[J_TRANS / 4 + i] = mt[12 + i];
    tj[J_TRANS / 4 + 3] = 0.0f;
    if (self == tail) join_log(head, tail, hj, tj, "world");
}
