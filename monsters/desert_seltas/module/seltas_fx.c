/* seltas_fx.c: Desert Seltas' and Desert Seltas Queen's motion effects on the ground (Tidal Najarala's way: monsters/tidal_najarala/module/em068_01_fx.c has
 * the code reading; C unless marked, 4U addresses read 2026-11-09).
 * 4U: their MEF records with the ground flag (bit 1) are placed every frame at x, z = the joint + the record offset turned by their yaw, y = their ground
 * (4U 0x391b50 copies the flags into the effect; joint -1 = their own place), the scale x their size (bit 5), and keep the elements whose ground word meets
 * (2 << kind) | 1 of the ground under them (0xc08060). GU's records have no such tail: tools/build_seltas_arc.py pel_ground_records makes them world
 * records, and this hook on the PSL post names the point, the size and the ground set. GU's common effects (PEL c) of their GU motions take the same set:
 * without one, every set draws at once (Shrouded Nerscylla's discovery glitter). The ground kind comes from the ground word under them by 4U's bit
 * rule on GU's word (Tidal Najarala's ray; S that GU's word means what 4U's does: the log line below shows the words met).
 * The two hook sites are Tidal Najarala's (0x700d4 PEL u, 0x70068 PEL c; one hook per site): her handlers call these first, which answer 1 only for
 * Desert Seltas or the Queen, so nothing of hers changes.
 * Multiplayer: every machine plays its own motions and posts its own effects, as GU's PSL player. All addresses through MAIN / FN.
 * Logs: "dsport: ground word", "dsport: ground post", "dsport: common post". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };
#define ARG5_AT_SITE (8 + 8)        /* regs[8] = sp[0] at the site; 0x70028 pushed 6 registers and took 8 bytes: its fifth argument is 8 words up */

#define IS_DS(p)     ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_EM_ID)
#define IS_DSQ(p)    ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_QUEEN_EM_ID)
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

struct ground { uint16_t id; int16_t joint, x, z; };
/* their MEF records with the ground flag {id, joint (-1: its own place), offset x, offset z}, in MEF order; tools/build_seltas_arc.py pel_ground_records
 * asserts each table against 4U's file */
static const struct ground k_ground_em076_01[] = {
    {4, 0, 0, 0}, {6, -1, 0, 1700}, {7, -1, 0, 1700}, {10, -1, 0, 0}, {11, -1, 0, 0}, {500, -1, 0, 0}, {501, -1, 0, 200}, {513, -1, 0, 0}, {515, -1, 0, 0},
    {516, -1, 0, -600}, {517, 0, 0, 800}, {518, -1, 0, 0}, {519, -1, 200, 0}, {520, -1, -200, 0}, {521, -1, -80, 300},
};
static const struct ground k_ground_em069_01[] = {
    {6, 200, 0, 800}, {7, -1, 0, 500}, {15, -1, 0, 400}, {17, 144, 0, 0}, {21, 144, 0, 0}, {23, 144, 0, -400}, {25, 0, 0, -400}, {26, 144, 0, -350},
    {101, 0, 0, 0}, {500, 0, 0, 0}, {501, 1, 0, 0}, {502, 144, 0, -400}, {503, -1, 0, 0}, {504, 0, 0, 0}, {507, 40, 0, 200}, {508, 50, 0, 200},
    {509, 40, 0, 0}, {510, 50, 0, 0}, {511, 80, 0, 0}, {512, 90, 0, 0}, {513, -1, 0, 0}, {514, 144, 0, -400}, {517, -1, 0, 0}, {519, 40, 0, 0},
    {520, 50, 0, 0}, {521, 80, 0, 0}, {522, 40, 0, 0}, {523, 50, 0, 0}, {524, 90, 0, 0}, {525, 144, 0, -500}, {526, -1, 0, 0}, {527, -1, 0, 0},
    {528, 144, 0, -400}, {534, 1, 0, 0},
};
#define N_OF(t) (sizeof (t) / sizeof (t)[0])

/* 4U's ground kind rule on the word under them -> the set of elements to draw ((2 << kind) | 1) */
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
    else if (w & 0x1040) kind = 0;     /* the rule's lava: neither the Dunes nor the Steppe has any (Tidal's guard) */
    else kind = (w & 8) ? 4 : 0;
    if (w != s_word && s_n < GROUND_LINES) {
        s_word = w;
        s_n++;
        logf("dsport: ground word %x (%s) -> kind %u at %d %d %d, area %u, %s", w, hit ? "hit" : "no ground", kind, (int32_t)from[0], (int32_t)gy,
             (int32_t)from[2], FIELD(uint8_t, self, EN_AREA), IS_DS(self) ? "desert_seltas" : "desert_seltas_queen");
    }
    return (2u << kind) | 1u;
}

/* from em068_01_pslc_c (the one hook of the site 0x70068, kind 3 = PEL c, GU's common effects): 1 = it was one of them */
int seltas_pslc(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R5];
    uint8_t *req = (uint8_t *)regs[ARG5_AT_SITE], *rec;
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3];
    if (!IS_DS(self) && !IS_DSQ(self)) return 0;
    if (!req || !data || slot >= 32) return 1;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return 1;
    FIELD(uint32_t, req, REQ_FIELDS) |= BIT_GROUND;
    FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self, rec);
    if (++s_n <= COMMON_LINES)
        logf("dsport: common post %u motion %x frame %d set %x (%s)", FIELD(uint16_t, data, 4 + 2 * slot), curMotion(self), (int32_t)motionFrame(self),
             FIELD(uint32_t, req, REQ_GROUND), IS_DS(self) ? "desert_seltas" : "desert_seltas_queen");
    return 1;
}

/* from em068_01_psl_c (the one hook of the site 0x700d4, kind 4 = PEL u): 1 = it was one of them */
int seltas_psl(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R5];
    uint8_t *req = (uint8_t *)regs[ARG5_AT_SITE], *rec;
    const uint8_t *data = (const uint8_t *)regs[R2];
    uint32_t slot = regs[R3], id, n;
    const struct ground *t;
    if (IS_DS(self)) { t = k_ground_em076_01; n = N_OF(k_ground_em076_01); }
    else if (IS_DSQ(self)) { t = k_ground_em069_01; n = N_OF(k_ground_em069_01); }
    else return 0;
    if (!req || !data || slot >= 32) return 1;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return 1;
    id = FIELD(uint16_t, data, 4 + 2 * slot);
    FIELD(uint32_t, req, REQ_FIELDS) |= BIT_GROUND;
    FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self, rec);
    for (uint32_t i = 0; i < n; i++) {
        float p[4], size, r, s, c;
        if (t[i].id != id) continue;
        if (t[i].joint >= 0) jointPos(self, (uint32_t)t[i].joint, p);
        else {
            p[0] = FIELD(float, rec, REC_POS_X);
            p[1] = FIELD(float, rec, REC_POS_X + 4);
            p[2] = FIELD(float, rec, REC_POS_Z);
        }
        r = (float)(FIELD(uint32_t, rec, REC_YAW) & 0xffff) * 0x1.921fb6p-14f;
        s = sinf_gu(r);
        c = cosf_gu(r);
        FIELD(float, req, REQ_POS) = p[0] + c * (float)t[i].x + s * (float)t[i].z;
        FIELD(float, req, REQ_POS + 4) = FIELD(float, rec, REC_GROUND_Y);
        FIELD(float, req, REQ_POS + 8) = p[2] + c * (float)t[i].z - s * (float)t[i].x;
        FIELD(float, req, REQ_POS + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
        size = speedFactor(self);
        for (int k = 0; k < 3; k++) FIELD(float, req, REQ_SCALE + 4 * k) = size;
        FIELD(float, req, REQ_SCALE + 12) = 0.0f;
        FIELD(uint32_t, req, REQ_FIELDS) |= BIT_SCALE;
        if (++s_n <= POST_LINES)
            logf("dsport: ground post %u joint %d motion %x frame %d at %d %d %d (joint y %d) set %x size %d%% (%s)", id, t[i].joint, curMotion(self),
                 (int32_t)motionFrame(self), (int32_t)FIELD(float, req, REQ_POS), (int32_t)FIELD(float, req, REQ_POS + 4),
                 (int32_t)FIELD(float, req, REQ_POS + 8), (int32_t)p[1], FIELD(uint32_t, req, REQ_GROUND), (int32_t)(size * 100.0f),
                 IS_DS(self) ? "desert_seltas" : "desert_seltas_queen");
        break;
    }
    return 1;
}
