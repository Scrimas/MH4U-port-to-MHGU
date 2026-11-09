/* em070_01_fx.c: her motion effects on the ground (Tidal Najarala's way, monsters/tidal_najarala/module/em068_01_fx.c has the code reading). C unless marked, 4U addresses read 2026-11-06.
 * 4U: em096_040 (id 50), qe006_001 / 010 (500, 501, 504) and em096_200 (503) carry the MEF ground flag: every frame x, z from the joint + the offset, y = her ground; scale x her size (bit 5). Ground kind from her ground
 * record, the effect keeps the elements whose ground word meets (2 << kind) | 1.
 * GU: no record tail sits on the ground, and every set draws at once unless the request names one (notes of Stygian's em057_01_psl). The PSL post 0x70028 where kind 4 (PEL u) is sure: 0x700d4 (em068_01_psl's site: Tidal's handler
 * calls this one first, a site has one hook), r5 = this, r2 = PSL entry data, r3 = slot, the request = the fifth argument. The request takes the ground set (req+0x14 bit 19, req+0x6c), by Stygian's ray and 4U's bit rule on GU's word (S), and
 * for k_ground's records, which tools/build_em070_01_arc.py pel_ground_records made world records (mode 3): the point (req+0x1c bit 0, req+0xc0) and the size (req+0x14 bit 30, req+0x40).
 * GU's common effects (kind 3, PEL c) stay as GU posts them: its records are the same as those of GU's monsters on the Dunes (C: em007_00c against em070_00c), so they look as there. Multiplayer: every machine plays its own motions and
 * posts its own effects. All addresses through MAIN / FN. Logs: "snport: ground word", "snport: ground post". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };
#define ARG5_AT_SITE (8 + 8)        /* regs[8] = sp[0] at the site; 0x70028 pushed 6 registers and took 8 bytes: its fifth argument is 8 words up */

#define IS_HER(p)    ((p) && FIELD(uint16_t, (p), EN_ID) == SHROUDED_NERSCYLLA_EM_ID)
#define EN_AREA      0x1054

typedef float (*ground_ray_t)(void *mgr, const float *from, const float *to, uint32_t area, uint8_t *hit, void *out, uint32_t mask);
#define groundRay    FN(ground_ray_t, 0x183ad0)     /* [0x2bad24] */
#define COLL_MGR     (*(void **)MAIN(0x21270e0))
#define REC_GROUND_Y 0x5b4
#define REQ_FIELDS   0x14
#define REQ_SCALE    0x40           /* float[4], bit 30 */
#define REQ_GROUND   0x6c           /* u32, bit 19 */
#define REQ_FLAGS    0x1c           /* bit 0: world position */
#define REQ_POS      0xc0
#define BIT_SCALE    0x40000000u
#define BIT_GROUND   0x80000u
#define GROUND_LINES 24u
#define POST_LINES   40u

/* her MEF records with the ground flag {id, joint (-1: her own place), offset z}, in MEF order; tools/build_em070_01_arc.py pel_ground_records asserts this against 4U's file (1008 is a 4U code post, no motion names it) */
static const struct { uint16_t id; int16_t joint, z; } k_ground[] = {
    {50, 0, 0}, {500, 0, 240}, {501, 0, 0}, {503, -1, 100}, {504, 0, 0},
};
#define N_GROUND (sizeof k_ground / sizeof k_ground[0])

static uint32_t ground_flags(void *self, const uint8_t *rec)
{
    static uint32_t s_word = ~0u, s_n;
    uint32_t out[16] = { 0 }, w, kind;
    uint8_t hit = 0;
    float gy = FIELD(float, rec, REC_GROUND_Y);
    float from[4] = { FIELD(float, rec, REC_POS_X), gy + 100.0f, FIELD(float, rec, REC_POS_Z), 0.0f };
    float to[4] = { from[0], gy - 300.0f, from[2], 0.0f };
    void *mgr = COLL_MGR;
    if (mgr) groundRay(mgr, from, to, FIELD(uint8_t, self, EN_AREA), &hit, out, 64);
    w = hit ? out[2] : 0;
    if (w & 0x800000) kind = 5;
    else if (w & 0x200) kind = 3;
    else if (w & 6) kind = 1;
    else if (w & 0x1040) kind = 0;     /* the rule's lava: the Dunes have none (Tidal's guard) */
    else kind = (w & 8) ? 4 : 0;
    if (w != s_word && s_n < GROUND_LINES) {
        s_word = w;
        s_n++;
        logf("snport: ground word %x (%s) -> kind %u at %d %d %d, area %u", w, hit ? "hit" : "no ground", kind, (int32_t)from[0], (int32_t)gy, (int32_t)from[2], FIELD(uint8_t, self, EN_AREA));
    }
    return (2u << kind) | 1u;
}

/* from em068_01_psl_c (the one hook of the site 0x700d4): 1 = it was her */
int em070_01_psl(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R5];
    uint8_t *req = (uint8_t *)regs[ARG5_AT_SITE], *rec;
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3], id;
    if (!IS_HER(self)) return 0;
    if (!req || !data || slot >= 32) return 1;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return 1;
    id = FIELD(uint16_t, data, 4 + 2 * slot);
    FIELD(uint32_t, req, REQ_FIELDS) |= BIT_GROUND;
    FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self, rec);
    for (uint32_t i = 0; i < N_GROUND; i++) {
        float p[4], size, r;
        if (k_ground[i].id != id) continue;
        if (k_ground[i].joint >= 0) jointPos(self, (uint32_t)k_ground[i].joint, p);
        else {
            p[0] = FIELD(float, rec, REC_POS_X);
            p[1] = FIELD(float, rec, REC_POS_X + 4);
            p[2] = FIELD(float, rec, REC_POS_Z);
        }
        r = (float)(FIELD(uint32_t, rec, REC_YAW) & 0xffff) * 0x1.921fb6p-14f;
        FIELD(float, req, REQ_POS) = p[0] + sinf_gu(r) * (float)k_ground[i].z;
        FIELD(float, req, REQ_POS + 4) = FIELD(float, rec, REC_GROUND_Y);
        FIELD(float, req, REQ_POS + 8) = p[2] + cosf_gu(r) * (float)k_ground[i].z;
        FIELD(float, req, REQ_POS + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
        size = speedFactor(self);
        for (int k = 0; k < 3; k++) FIELD(float, req, REQ_SCALE + 4 * k) = size;
        FIELD(float, req, REQ_SCALE + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FIELDS) |= BIT_SCALE;
        if (++s_n <= POST_LINES)
            logf("snport: ground post %u joint %d motion %x frame %d at %d %d %d (joint y %d) set %x size %d%%", id, k_ground[i].joint, curMotion(self), (int32_t)motionFrame(self),
                 (int32_t)FIELD(float, req, REQ_POS), (int32_t)FIELD(float, req, REQ_POS + 4), (int32_t)FIELD(float, req, REQ_POS + 8), (int32_t)p[1], FIELD(uint32_t, req, REQ_GROUND),
                 (int32_t)(size * 100.0f));
        break;
    }
    return 1;
}
