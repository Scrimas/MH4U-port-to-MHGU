/* em007_01_mv_i.c: Monoblos, ported 4U uEm101 handler, batch I: the charge's spin turn 2/13 2/15 (4U 0x8d8cc0).
 * Literal translation (MH4U v1.1), run by em007_01_moves_run. GU's Diablos has a GU version, 0xd3d1ec (its 2/19 2/20:
 * the same steps, motions 0x419 / 0x41a, constants 7.4 / 1.6 / 0.0625 / 1.4 / 1.7, the root move of joint 0x20f), but
 * it attacks with Diablos' records (55) and scales the root move by 1.6 where 4U scales his by 0.8 (GU's retune of its
 * Diablos; his 4U value is kept). Its field offsets are the evidence below. C = confirmed in code, S = strong.
 * - 4U W+0x248 = rec+0x200 (C: GU d3d370; with the scrape's W+0x24c = rec+0x204).
 * - 4U this+0xd58 = GU this+0x13b8 (C: GU d3d840, the yaw update's factor; GU's spinWindow reads it too).
 * - 4U 0x936960(this, joint, out) = GU 0xb0c40 (C: the same body: the joint's position at layer-0 frame this+0x4fc
 *   minus at this+0x500, 4U this+652 / 656).
 * - 4U this+668 = the layer-0 motion speed, GU getter 0xb09bc (stygian em057_01_mv_a.c).
 * - 4U class work +0x60 (u16), +0x64..0x6c (angle triple), +0x70..0x7c (vector), +0x80 (s32 angle): GU's version keeps
 *   them at GU work +0x20..0x48; ours live in mb_state (only this action uses them).
 * - Sine / cosine: 4U's u16 angle tables, GU's sinf / cosf on ang * 2pi / 65536 (as GU's version). */
#include "em007_01.h"

typedef float (*speedGet_t)(void *self);
#define motionSpeed  FN(speedGet_t, 0xb09bc)    /* [this+668] */
typedef void (*jointDelta_t)(void *self, uint32_t joint, float *out);
#define jointDelta   FN(jointDelta_t, 0xb0c40)  /* [0x936960] */
typedef void (*self_t2)(void *self);
#define pin13a0      FN(self_t2, 0xc0644)       /* [0xb05184] this+0x13a0 = 1.0 (stygian em057_01.h) */
#define REC_SPIN_ANG 0x200                      /* [4U W+0x248] */
#define EN_TURN_K    0x13b8                     /* [4U this+0xd58] */

static inline void sincos_u16(uint32_t ang, float *s, float *c)
{
    float a = (float)(ang & 0xffff) * 0x1.921fb6p-14f;
    *s = sinf_gu(a);
    *c = cosf_gu(a);
}

/* ---- 2/13 2/15: 4U 0x8d8cc0(kind = r1 0 / 1), chained from the charge (7/24 kind 4, setActionNow): two wander
 * points every frame; attack 53 at once, at frame 118 (kind 1: 148) of the running motion target mode 0, then the
 * spin (motion 0x419 / 0x41a with attack 51) toward the target, clamped to a half turn; the motion's push (velocity =
 * the vector x 1.6 at frame 115), the root move of joint 0x20f over frames 120..150 (x 0.8, speed capped), the turn
 * over frames 4..20 and toward the target over 50..150; at its end the charge resumes (7/26 / 7/27 = the charge's
 * kinds 6 / 7) */
void mbmv_8d8cc0(void *self, const uint8_t *p)
{
    uint8_t *rec;
    struct mb_state *st = mb_state(self);
    uint32_t kind = p[0];
    float s, c;
    for (uint32_t i = 0; i < 2; i++) wanderPoint(self, 0, i);
    rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        attackEx(self, 0, MB_ATK(53), 26);
        rec[REC_STEP0]++;
        return;
    case 1:
        if (!motionCheck(self, 0, 0, kind ? 148.0f : 118.0f, 0.0f)) return;
        setTargetMode(self, 0);
        rec[REC_STEP0]++;
        return;
    case 2: {
        const float *pos = &RF(rec, REC_POS_X), *t = &RF(rec, REC_TARGET);
        float k, x, z;
        uint32_t ang;
        rec[REC_STEP0] = 3;
        k = speedFactor(self) * 7.4f;
        k = k * motionSpeed(self);
        sincos_u16(RU(rec, REC_YAW), &s, &c);
        x = c * 0.0f;
        x += s * k;
        z = c * k;
        z -= s * 0.0f;
        st->v70[0] = x;
        st->v70[1] = 0.0f;
        st->v70[2] = z;
        st->v70[3] = 0.0f;
        sincos_u16(RU(rec, REC_YAW), &s, &c);
        x = c * 0.0f;
        z = x;
        x += s * 0.0f;
        z -= s * 0.0f;
        x += pos[0];
        z += pos[2];
        ang = atan_u16(t[0] - x, t[2] - z);
        RU(rec, REC_SPIN_ANG) = ang;
        st->a80 = (int32_t)((ang - RU(rec, REC_YAW)) & 0xffff);
        if (kind == 0) {
            if (st->a80 > 0x8000) st->a80 = 0x8000;
            setMotion(self, 0x419, 2.0f, 0.0f);
            attackEx(self, 0, MB_ATK(51), 24);
        } else {
            if (st->a80 <= 0x8000) st->a80 = 0x8000;
            setMotion(self, 0x41a, 2.0f, 0.0f);
            attackEx(self, 0, MB_ATK(51), 24);
            st->a80 = (int32_t)((0x10000 - (uint32_t)st->a80) & 0xffff);
            st->a80 = -st->a80;
        }
        st->a80 = (int32_t)((float)st->a80 * 0.0625f);
        st->ang64[0] = st->ang64[1] = st->ang64[2] = 0;
        RF(rec, REC_VEL) = st->v70[0];
        RF(rec, REC_VEL + 4) = st->v70[1];
        RF(rec, REC_VEL + 8) = st->v70[2];
        RF(rec, REC_VEL + 12) = 0.0f;
        st->w60 = (uint16_t)atan_u16(-(pos[2] - t[2]), pos[0] - t[0]);
        return;
    }
    case 3: {
        float out;
        pin13a0(self);
        if (motionCheck(self, 3, 0, 0.0f, 110.0f)) rotateVel(self, st->ang64, 0);
        if (motionCheck(self, 0, 0, 115.0f, 0.0f)) {
            RF(rec, REC_VEL + 8) = st->v70[2] * 1.6f;
            RF(rec, REC_VEL + 12) = 0.0f;
            RF(rec, REC_VEL) = st->v70[0] * 1.6f;
            RF(rec, REC_VEL + 4) = st->v70[1] * 1.6f;
        }
        if (motionCheck(self, 3, 0, 120.0f, 150.0f)) {
            float v[4], x, y, z, sp, m;
            jointDelta(self, 0x20f, v);
            sincos_u16(RU(rec, REC_ANGLES + 8), &s, &c);    /* z angle (4U W+0x1b0) */
            x = c * v[0];
            x -= s * v[1];
            y = s * v[0];
            y += c * v[1];
            sincos_u16(RU(rec, REC_ANGLES), &s, &c);        /* x angle (4U W+424) */
            z = s * y;
            z += c * v[2];
            y = c * y;
            y -= s * v[2];
            sincos_u16(RU(rec, REC_ANGLES + 4), &s, &c);    /* yaw (4U W+428) */
            {
                float x2 = c * x;
                float z2 = c * z;
                x2 += s * z;
                z2 -= s * x;
                x = x2;
                z = z2;
            }
            RF(rec, REC_POS_X) += (speedFactor(self) * x) * 0.8f;
            RF(rec, REC_POS_X + 4) += (speedFactor(self) * y) * 0.8f;
            RF(rec, REC_POS_X + 8) += (speedFactor(self) * z) * 0.8f;
            sp = layerSpeed(self);
            m = 1.4f;
            if (sp * 1.4f > 1.7f) m = 1.7f / sp;
            setMotionSpeed(self, m);
        }
        if (motionCheck(self, 9, &out, 4.0f, 20.0f)) {
            float d = (float)st->a80 * out;
            d = FIELD(float, self, EN_TURN_K) * d;
            RU(rec, REC_YAW) = (RU(rec, REC_YAW) + (uint32_t)(int32_t)d) & 0xffff;
        }
        if (motionCheck(self, 9, &out, 50.0f, 150.0f)) {
            float a = motionSpeed(self) * (out * 35.0f);
            a = a * 0.01f;
            a = a * 65536.0f;
            turnToTarget(self, (uint32_t)(int32_t)(0.5f + a * 0x1.6c16c2p-9f) & 0xffff, 0);
        }
        if (isMotionEnd(self)) rec[REC_STEP0]++;
        return;
    }
    case 4:
        st->w488 = st->w488 - 1.0f;
        mb_chain_now(self, 7, kind ? 27 : 26);
        return;
    default:
        return;
    }
}
