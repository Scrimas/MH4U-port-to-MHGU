/* em057_01_vt77.c: the sounds of 4U vt77 0x857ba8 (Zinogre class uEm048, per frame) that GU's twin vt170 ef27b0
 * lost. C = read in code, S = strong, G = guess.
 *
 * GU's vt170 kept vt77's tree (C, read 2026-10-28): the preamble's repeat timer work+44 (130) and the toggle byte
 * work+0x35 for actions 10/100 and 11/18, the work+0x58 object release of actions 10/7 20 32 167 210 217, the move
 * class 1 while charged in motions 0x225 / 0x226 (4U this+0xca8 |= 2), the paw-slam hit and the orb events (posted
 * for variant 0 / 4 only: em057_01_mv_d.c, em057_01_posts.c), but no sound call at all (no 0x4efd74 / 0x4efb98 /
 * 0x4efe58 call in ef27b0..ef3200). 4U's sounds there, all for em 49 (C):
 * - preamble 0x857c48..0x857cb8: when the timer runs out the byte flips, then sound 137 (byte 1) or 138 (byte 0) at
 *   joint 4. GU flips the byte as 4U does (C: ef2814..ef2838), so the flip is watched here and the sound follows it.
 * - motion tree 0x857f2c..: (motion, frames, charged only, sound, where)
 *     0x219 (0x857ff8 -> 0x858000): charged, 81 or 119 -> 208 at joint 2 (0x85853c)
 *     0x21a (0x85856c): charged, 71 / 76 / 81 -> 208 at joint 1 (0x8585c8)
 *     0x225 / 0x226 (0x858050): charged, 146 -> 204 at joint 140 (0x8580a0)
 *     0x218 (0x858668): charged, 2 -> 222 at (x, ground y, z) of the monster (0x8586e0: W+408 with y = W+0x624)
 *     0x308 (0x85873c): 118 / 138 / 178 / 224 -> 207 at joint 2 (0x8584f4)
 *     0x309 (0x858108): 60 -> 223 at the position + Ry(yaw) Rx(pitch) Rz(roll) (0, 0, 300) (0x858204); 16 / 36 / 56 /
 *     76 -> 207 at joint 2
 *   The frame register s18 is 81 below motion 0x21a and 138 above it (reloaded at 0x858030), as 0x225 / 0x226's orb
 *   events at 138 show (em057_01_posts.c).
 * Sounds: 4U 0x2fcc50 at a joint = sz_snd; 0x312484 at a point = sz_snd_at (GU 0x4efb98); the request keeps 4U's ids.
 * W+0x624 = GU rec+0x5b4 (S: Gogmazios' em089_shell005.c). Every machine plays them (sounds are local), as 4U. */
#include "em057_01.h"

#define SZ_N(a) (sizeof(a) / sizeof((a)[0]))
#define REC_GROUND_Y  0x5b4   /* ground height under the monster [4U W+0x624] (S) */
#define WK_TOGGLE     0x35    /* u8 flipped by the repeat timer [4U work+0x35] */

typedef int (*actIs_t)(void *self, uint32_t cat, uint32_t num);
#define actIs       FN(actIs_t, 0x6ff44)        /* [0x94d788] the current action is (cat, num) (C: GU ef27cc) */

enum { AT_JOINT, AT_GROUND, AT_FRONT };

static const struct {
    uint16_t mot, id;
    uint8_t charged, where, joint, n;
    float frames[4];
    uint32_t site;
} k_snd[] = {
    {0x219, 208, 1, AT_JOINT, 2, 2, {81.0f, 119.0f}, 0x85853c},
    {0x21a, 208, 1, AT_JOINT, 1, 3, {71.0f, 76.0f, 81.0f}, 0x8585e8},
    {0x225, 204, 1, AT_JOINT, 140, 1, {146.0f}, 0x8580a4},
    {0x226, 204, 1, AT_JOINT, 140, 1, {146.0f}, 0x8580a4},
    {0x218, 222, 1, AT_GROUND, 0, 1, {2.0f}, 0x8586e0},
    {0x308, 207, 0, AT_JOINT, 2, 4, {118.0f, 138.0f, 178.0f, 224.0f}, 0x858514},
    {0x309, 223, 0, AT_FRONT, 0, 1, {60.0f}, 0x858204},
    {0x309, 207, 0, AT_JOINT, 2, 4, {16.0f, 36.0f, 56.0f, 76.0f}, 0x858514},
};

/* the toggle byte last seen, per Stygian (more than four: the first slot is reused) */
static struct {
    void *self;
    uint8_t seen;
} s_tog[4];

static void toggle_sound(void *self)
{
    uint8_t now = FIELD(uint8_t, WORK(self), WK_TOGGLE);
    uint32_t i = 0;
    while (i < SZ_N(s_tog) && s_tog[i].self && s_tog[i].self != self) i++;
    if (i == SZ_N(s_tog)) i = 0;
    if (s_tog[i].self != self) {
        s_tog[i].self = self;
        s_tog[i].seen = now;
        return;
    }
    if (now == s_tog[i].seen) return;
    s_tog[i].seen = now;
    if (actIs(self, 10, 100) || actIs(self, 11, 18)) sz_snd(self, now ? 137 : 138, 4, 0x857cb8);
}

/* Ry(ay) Rx(ax) Rz(az) (0, 0, 300): 0x858130..0x8581b0 (Rz leaves (0, 0, z) as is) */
static void front_point(void *self, float *p)
{
    const uint8_t *rec = REC(self);
    float a = (float)(RU(rec, REC_ANGLES) & 0xffff) * 0x1.921fb6p-14f, v[3];
    v[0] = 0.0f;
    v[1] = -300.0f * sinf_gu(a);
    v[2] = 300.0f * cosf_gu(a);
    rot_y(v, RU(rec, REC_ANGLES + 4));
    for (int i = 0; i < 3; i++) p[i] = RF(rec, REC_POS_X + 4 * i) + v[i];
    p[3] = 0.0f;
}

void em057_01_vt77_frame(void *self)
{
    uint32_t mot = curMotion(self), charged = isCharged(self) != 0;
    toggle_sound(self);
    for (uint32_t i = 0; i < SZ_N(k_snd); i++) {
        if (k_snd[i].mot != mot || (k_snd[i].charged && !charged)) continue;
        for (uint32_t f = 0; f < k_snd[i].n; f++) {
            float p[4];
            if (!atFrame(self, k_snd[i].frames[f])) continue;
            if (k_snd[i].where == AT_JOINT) {
                sz_snd(self, k_snd[i].id, k_snd[i].joint, k_snd[i].site);
            } else {
                const uint8_t *rec = REC(self);
                if (k_snd[i].where == AT_FRONT) front_point(self, p);
                else {
                    p[0] = RF(rec, REC_POS_X);
                    p[1] = RF(rec, REC_GROUND_Y);
                    p[2] = RF(rec, REC_POS_X + 8);
                    p[3] = 0.0f;
                }
                sz_snd_at(self, k_snd[i].id, p, FIELD(uint8_t, self, EN_AREA));
            }
            break;
        }
    }
}
