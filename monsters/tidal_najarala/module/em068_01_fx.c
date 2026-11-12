/* em068_01_fx.c: her motion effects on the ground, the snow she throws up on every move (user's test of 0.2.1: "in mh4u kommen so schnee effekte ... immer wenn Sie sich bewegt, die fehlen
 * noch"). C unless marked, 4U addresses read 2026-11-06; notes/plan.md "Snow".
 * 4U: em093_003 on the records k_ground below, motion events of nearly every move. 0x391b50 posts it (slot mode 1: it ends with its event range, tools/build_em068_01_arc.py
 * pel_ground_records). MEF flags 0x227: bit 1 = every frame x, z from the joint + the offset turned by her angles, y = her ground W+0x624 (0xc4838c.., 0xc49a84); bit 5 = scale x her size
 * (0xc47f98). Ground kind from her ground record W+0x5f0, attribute word +8 (0xc09908: 0x800000 -> 5, 0x200 -> 3, 6 -> 1, 0x1040 -> 2, 8 -> 4, else 0); the effect keeps the elements
 * whose ground word meets (2 << kind) | 1 (0xc08060). em093_003's elements: 0x22 (kinds 0, 4), 0x54 (kinds 1, 3, 5). The colour is the stage's soil, baked (seaway_soil), and 4U's Intensity 1
 * doubles it: white (efl4u2gu.intensity_bake).
 * GU: no record tail sits on the ground, and every set draws at once unless the request names one (notes of Stygian's em057_01_psl). Hook on the PSL post 0x70028 where kind 4 (PEL u) is
 * sure: 0x700d4 (movw r0, #0x73e0; add r1, r2, r3, lsl #1), r5 = this, r2 = PSL entry data, r3 = slot, r7 = the request (the fifth argument, sp + 0x20 here). The request takes:
 *  - the ground set (req+0x14 bit 19, req+0x6c), by Stygian's ray (GU's twin of W+0x5f0 is not identified) and 4U's bit rule on GU's word (S). Map 14 has no lava, so a word that the
 *    rule reads as lava (0x1040, kind 2: em093_003 has no such set, nothing would draw) counts as kind 0 (a guard, GU's word is not proven to mean what 4U's means);
 *  - for k_ground's records, which pel_ground_records made world records (mode 3): the point (req+0x1c bit 0, req+0xc0): joint x, z + the offset turned by her yaw, y = rec+0x5b4, and the
 *    size (req+0x14 bit 30 multiplies req+0x40 into the record's scale: GU 0x31c858; a world post has no attach model to bring it). The rest of 0x70028 runs as GU's, so the PSL player
 *    keeps the effect and ends it with the event range.
 * Since 0.2.3 the snow on the records marked below is GU's own, cm202_002 (the user asked for GU's look; tools/build_em068_01_arc.py SNOW_EFL has the survey): GU's common dust files hold a set per
 * ground and ground word 0x100 is the white one (Capcom bakes 0x100 into the records of monsters that live on snow, Zamtrios' steps among them). Her ground word on the Frozen Seaway logs as 0
 * (log 21-51-59, area 2), so the attribute does not tell snow; her quests do: both are on map 14 (0.2.3..0.2.8 kept the plain set for the Arena quest 11497, gone in 0.2.9). GU's common effects (kind 3, 0x70068) take the
 * same set: how GU picks a set for its own records with -1 was not found (C: no request override on this path, S that the engine has one elsewhere), so it is named here. A word that says water
 * or the like keeps 4U's rule, which fits GU's sets (0x54).
 * Multiplayer: every machine plays its own motions and posts its own effects, as GU's PSL player. All addresses through MAIN / FN.
 * Logs: "tnport: ground word" per new ground word, "tnport: ground post" for the first posts, "tnport: common post" for GU's. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };
#define ARG5_AT_SITE (8 + 8)        /* regs[8] = sp[0] at the site; 0x70028 pushed 6 registers and took 8 bytes: its fifth argument is 8 words up */

#define IS_HER(p)    ((p) && FIELD(uint16_t, (p), EN_ID) == TIDAL_NAJARALA_EM_ID)
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
#define POST_LINES   60u
#define COMMON_LINES 30u
#define SET_PLAIN    3u             /* (2 << 0) | 1: 4U's rule for ordinary ground */
#define SET_SNOW     0x100u         /* the white elements of GU's common dust */

/* her MEF records with the ground flag and a joint {id, joint, offset x, offset z, 1 = GU's snow (0.2.7: also 4U's common dust qe006, the user saw it yellow-orange)}, in MEF order; tools/build_em068_01_arc.py pel_ground_records asserts this against 4U's files */
static const struct { uint16_t id; int16_t joint, x, z; uint8_t snow; } k_ground[] = {
    {400, 10, 0, 0, 1}, {401, 6, 0, 0, 1}, {402, 145, 0, 0, 1}, {403, 4, 0, 0, 1}, {405, 12, 0, 0, 1}, {406, 5, 0, 0, 1}, {407, 8, 0, 50, 1}, {408, 145, 0, -200, 1}, {409, 0, 0, 0, 1}, {410, 8, 0, 0, 1},
    {411, 13, 0, -120, 1}, {412, 13, 0, 150, 1}, {413, 8, 0, 0, 1}, {414, 140, 0, 0, 1}, {416, 142, 0, 0, 1}, {417, 100, 0, 0, 1}, {418, 144, 0, 0, 1},
    {2000, 11, 0, 100, 1}, {2002, 11, 0, 200, 1}, {2006, 10, 0, 50, 1}, {2008, 13, 0, 120, 0}, {2009, 13, 0, 0, 0}, {2011, 8, 230, 250, 1}, {2013, 10, 0, 100, 1}, {2014, 10, 0, 0, 1}, {2016, 13, 0, -350, 1},
    {2017, 145, 0, 0, 1}, {2018, 145, 0, 0, 1},
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
    else if (w & 0x1040) kind = 0;
    else kind = (w & 8) ? 4 : 0;
    if (w != s_word && s_n < GROUND_LINES) {
        s_word = w;
        s_n++;
        logf("tnport: ground word %x (%s) -> kind %u at %d %d %d, area %u", w, hit ? "hit" : "no ground", kind, (int32_t)from[0], (int32_t)gy, (int32_t)from[2], FIELD(uint8_t, self, EN_AREA));
    }
    return (2u << kind) | 1u;
}

/* the set for one of GU's common dust files: her quests are all on the Frozen Seaway */
static uint32_t gu_set(uint32_t flags)
{
    return flags == SET_PLAIN ? SET_SNOW : flags;
}

int seltas_pslc(uint32_t *regs);         /* monsters/desert_seltas/module/seltas_fx.c: a site has one hook */

/* 0x70068 (movw r0, #0x73e0; add r1, r2, r3, lsl #1): the same post, kind 3 = PEL c, GU's common effects */
int em068_01_pslc_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R5];
    uint8_t *req = (uint8_t *)regs[ARG5_AT_SITE], *rec;
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3];
    if (seltas_pslc(regs)) return 0;
    if (!IS_HER(self) || !req || !data || slot >= 32) return 0;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return 0;
    FIELD(uint32_t, req, REQ_FIELDS) |= BIT_GROUND;
    FIELD(uint32_t, req, REQ_GROUND) = gu_set(ground_flags(self, rec));
    if (++s_n <= COMMON_LINES)
        logf("tnport: common post %u motion %x frame %d set %x", FIELD(uint16_t, data, 4 + 2 * slot), curMotion(self), (int32_t)motionFrame(self), FIELD(uint32_t, req, REQ_GROUND));
    return 0;
}

int em070_01_psl(uint32_t *regs);        /* monsters/shrouded_nerscylla/module/em070_01_fx.c: a site has one hook */
int seltas_psl(uint32_t *regs);          /* monsters/desert_seltas/module/seltas_fx.c, the same */

int em068_01_psl_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R5];
    uint8_t *req = (uint8_t *)regs[ARG5_AT_SITE], *rec;
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3], id;
    if (em070_01_psl(regs) || seltas_psl(regs)) return 0;
    if (!IS_HER(self) || !req || !data || slot >= 32) return 0;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return 0;
    id = FIELD(uint16_t, data, 4 + 2 * slot);
    FIELD(uint32_t, req, REQ_FIELDS) |= BIT_GROUND;
    FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self, rec);
    for (uint32_t i = 0; i < N_GROUND; i++) {
        float p[4], size, s, c, r;
        if (k_ground[i].id != id) continue;
        jointPos(self, (uint32_t)k_ground[i].joint, p);
        r = (float)(FIELD(uint32_t, rec, REC_YAW) & 0xffff) * 0x1.921fb6p-14f;
        s = sinf_gu(r);
        c = cosf_gu(r);
        FIELD(float, req, REQ_POS) = p[0] + c * (float)k_ground[i].x + s * (float)k_ground[i].z;
        FIELD(float, req, REQ_POS + 4) = FIELD(float, rec, REC_GROUND_Y);
        FIELD(float, req, REQ_POS + 8) = p[2] + c * (float)k_ground[i].z - s * (float)k_ground[i].x;
        FIELD(float, req, REQ_POS + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
        size = speedFactor(self);
        for (int k = 0; k < 3; k++) FIELD(float, req, REQ_SCALE + 4 * k) = size;
        FIELD(float, req, REQ_SCALE + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FIELDS) |= BIT_SCALE;
        if (k_ground[i].snow) FIELD(uint32_t, req, REQ_GROUND) = gu_set(FIELD(uint32_t, req, REQ_GROUND));
        if (++s_n <= POST_LINES)
            logf("tnport: ground post %u joint %d motion %x frame %d at %d %d %d (joint y %d) set %x size %d%%", id, k_ground[i].joint, curMotion(self), (int32_t)motionFrame(self),
                 (int32_t)FIELD(float, req, REQ_POS), (int32_t)FIELD(float, req, REQ_POS + 4), (int32_t)FIELD(float, req, REQ_POS + 8), (int32_t)p[1], FIELD(uint32_t, req, REQ_GROUND),
                 (int32_t)(size * 100.0f));
        break;
    }
    return 0;
}
