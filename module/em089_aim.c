/* em089 head aim (em089_aim.h): faithful translation of the 4U layer-1 blocks of 7/105 [0x8bdd2c], 7/135
 * [0x8c02b0], 7/110 [0x8be434 r1 = 1] and 1/33-1/34 [0x8bb0f4] onto the GU layer-1 API (game.h, all C):
 *   4U 0x9200a4 -> 0xb03e8, 0xb07ba4 -> 0xb000c, 0x935ff0 -> 0xb0694, 0xb054e0 / 0xb052d8 -> 0x726dc / 0x726f8,
 *   0x918e80 -> 0xb07d0 (rec+0x308 = W+916), 0x918f28 -> 0xafeec, 0x93093c -> 0xc1708, this+656 -> 0xb09e4.
 * The aim poses are full layer-1 animations synchronised with the main motion (0x26b / 0x241 both 429 frames,
 * 0x255 / 0x256 / 0x247 925): the head angle comes from the layer weight, not from the frame.
 * Target = the targeted hunter's root joint (as em089_act.c target_pos; 4U reads the target slot W+536). */
#include "game.h"
#include "util.h"
#include "em089.h"
#include "em089_aim.h"

#define REC(self) FIELD(uint8_t *, self, EN_RECORD)

#define MOT_PITCH_UP   0x26b   /* 7/105 layer pose (bank 2) */
#define MOT_PITCH_DOWN 0x27f   /* 7/135 */
#define MOT_YAW_A      0x255   /* 7/110, weight >= 0 */
#define MOT_YAW_B      0x256   /* 7/110, weight < 0 */
#define AIM_JOINT      3       /* 4U 0x93093c(this, 3, out): joint id 3 (ids unchanged by tools/mod4u2gu.py) */

/* 4U constants: u16 angle -> degrees (360 * 1/65536), then / limit */
#define U16_DEG(a) ((float)(int32_t)(int16_t)(a) * 360.0f * 1.52588e-05f)

static uint32_t s_log;

static float fsqrt(float x)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));   /* -fno-builtin: no libm sqrtf in the module */
    return r;
}

/* radians -> 4U u16 angle (atan2 0x568c8c returns the u16 form) */
static uint32_t u16_angle(float rad)
{
    float v = rad * 10430.378f;   /* 65536 / 2pi */
    return (uint32_t)(int32_t)(v + (v < 0.0f ? -0.5f : 0.5f)) & 0xffff;
}

/* the targeted hunter's root joint, else the engine target slot rec+464 (as em089_act.c target_pos) */
static void target_pos(void *self, float *out)
{
    void *pl = em089_target_hunter(self);
    if (pl) { jointPos(pl, 0, out); return; }
    const float *t = (const float *)(REC(self) + REC_TARGET);
    for (int i = 0; i < 4; i++) out[i] = t[i];
}

/* 4U pitch block (7/105 0x8bde2c.., 7/135 0x8c040c..): joint 3 -> target (+ up), a = atan2(-dy, horizontal) as a
 * u16 angle. Returns the layer weight, or -1 when 4U skips the layer call. */
static float pitch_weight(void *self, uint32_t kind)
{
    float p[4], t[4];
    jointPos(self, AIM_JOINT, p);
    target_pos(self, t);
    float up = kind == EM089_AIM_PITCH_DOWN ? 100.0f : 0.0f;
    float dx = t[0] - p[0], dy = t[1] + up - p[1], dz = t[2] - p[2];
    if (kind == EM089_AIM_PITCH_UP) {
        if (dy < 0.0f) return -1.0f;                         /* target below the head: no aim */
        uint32_t a = u16_angle(atan2f_gu(-dy, fsqrt(dx * dx + dz * dz)));
        if (a < 0x8000) return 0.0f;                          /* (dy == 0) */
        a = 0x10000 - a;
        if (a > 0x1555) a = 0x1555;                           /* 30 degrees */
        return U16_DEG(a) * 0.0333333f;
    }
    uint32_t a = u16_angle(atan2f_gu(-dy, fsqrt(dx * dx + dz * dz)));
    if (a > 0x8000 || a == 0) return -1.0f;                   /* target above: no aim */
    if (a > 0x2000) a = 0x2000;                               /* 45 degrees */
    return U16_DEG(a) * 0.0222222f;
}

/* 4U 7/110 step 2 (0x8be6ac..0x8be74c): relative yaw to the target / 20 degrees, smoothed into rec+0x308 */
static void yaw_smooth(void *self)
{
    float t[4];
    uint8_t *rec = REC(self);
    target_pos(self, t);
    uint32_t a = (u16_angle(atan2f_gu(t[0] - FIELD(float, rec, REC_POS_X), t[2] - FIELD(float, rec, REC_POS_Z))) -
                  FIELD(uint32_t, rec, REC_YAW)) & 0xffff;
    aimSmooth(self, a ? U16_DEG(a) * 0.05f : 0.0f, 0.3f);
}

static void yaw_pair(void *self)
{
    float frame = (float)(int32_t)motionFrame(self);   /* 4U vcvt.s32 / vcvt.f32 of this+656 */
    layer1Pair(self, MOT_YAW_A, MOT_YAW_B, frame, FIELD(float, REC(self), REC_AIM_W));
}

void em089_aim_start(void *self, uint32_t kind)
{
    if (kind == EM089_AIM_PITCH_UP || kind == EM089_AIM_PITCH_DOWN) {
        float w = pitch_weight(self, kind);
        if (++s_log <= 40)
            logf("gogport: em089 aim start %u weight %d/1000", kind, w < 0.0f ? -1 : (int32_t)(w * 1000.0f));
        if (w < 0.0f) return;
        layer1MotionW(self, kind == EM089_AIM_PITCH_UP ? MOT_PITCH_UP : MOT_PITCH_DOWN, 0.0f, 1.0f - w);
        return;
    }
    aimReset(self);
}

void em089_aim_update(void *self, uint32_t kind)
{
    if (kind == EM089_AIM_PITCH_UP || kind == EM089_AIM_PITCH_DOWN) {
        if (layer1Weight(self) == 0.0f) return;
        float w = pitch_weight(self, kind);
        if (++s_log <= 40) logf("gogport: em089 aim update %u weight %d/1000", kind, w < 0.0f ? -1 : (int32_t)(w * 1000.0f));
        if (w >= 0.0f) layer1SetWeight(self, w);
        return;
    }
    if (kind == EM089_AIM_YAW) yaw_smooth(self);
    yaw_pair(self);
    static uint32_t s_n;
    if ((s_n++ % 60) == 0 && ++s_log <= 40)
        logf("gogport: em089 aim yaw %u w %d/1000 frame %d", kind, (int32_t)(FIELD(float, REC(self), REC_AIM_W) * 1000.0f),
             (int32_t)motionFrame(self));
}

void em089_aim_stop(void *self) { aimReset(self); }

float em089_aim_weight(void *self) { return layer1Weight(self); }

void em089_aim_layer(void *self, uint32_t motion, uint32_t flags, float blend, float start, float weight)
{
    layer1Motion(self, motion, flags, blend, start);
    layer1SetWeight(self, weight);
    if (++s_log <= 40) logf("gogport: em089 aim layer motion %x weight %d/1000", motion, (int32_t)(weight * 1000.0f));
}
