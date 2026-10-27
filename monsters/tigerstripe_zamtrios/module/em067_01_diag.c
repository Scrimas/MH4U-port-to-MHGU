/* em067_01_diag.c: Tigerstripe Zamtrios diagnostics (logs, prefix "tzport:"), and the per-frame tick of the 7/70
 * blast's end effect (em067_01_shell016_tick).
 *
 * Hook 0xf78f98 = uEm067_00 vtable slot 125, the action dispatcher (= 4U slot 44, every frame): for the first
 * Zamtrios variant 1 (ID 0x143) it meets, log each new action (category / number, enemy +0x73e0 / +0x73e1) and each
 * new motion (curMotion, bank << 8 | index). A test session then shows which actions 4U em092's command table really
 * reaches (porting plan Phase 3.1: the ones GU lacks fall to the dispatcher's default case, base 0xca118) and that
 * the variant-1 motions GU's code asks for (0x462..0x46e, 0x370, 0x372) play from our em092 motion lists. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0 };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */

void em067_01_shell016_tick(void *owner);

#define EM067_VTABLE 0x17e4800u     /* uEm067_00 object vtable */
#define EN_AREA      0x1054         /* u8 current area */

static int is_ts(void *self)
{
    return self && FIELD(uint32_t, self, 0) == MAIN(EM067_VTABLE) && FIELD(uint8_t, self, EN_VARIANT) == 1;
}

/* area moves (notes/area-move.md): 0x8f004 = setup of GU's EMC op 0x94 (next area from area_select, move type from
 * area_act_tbl), 0xb5d6c = the transfer on arrival (writes the area byte). Generic enemy code: logs for Tigerstripe. */
int em067_01_amove_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    static uint32_t s_n;
    if (is_ts(self) && ++s_n <= 30)
        logf("tzport: em067_01 area move setup in area %u (request %u, forced next %u)", FIELD(uint8_t, self, EN_AREA),
             FIELD(uint8_t, self, 0x73f3), FIELD(uint8_t, self, 0x73f6));
    return 0;
}

int em067_01_atransfer_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    static uint32_t s_n;
    if (is_ts(self) && ++s_n <= 30)
        logf("tzport: em067_01 area transfer from area %u (r1 %u, next %u, move type %u)", FIELD(uint8_t, self, EN_AREA),
             regs[1], FIELD(uint8_t, self, 0x73f8), FIELD(uint8_t, self, 0xba4e));
    return 0;
}
#define MAX_LINES  600u

/* Clipping while inflated (user 2026-10-27): the volumes, the mask (rec+0x3b4 bit 15 clear in mode 2
 * = bodydata / cambodydata record 1 on, bone 201 r100 / r110) and bone 201's animated scale (~5, 4U em092 = em022)
 * match GU Zamtrios (C). This tells the two remaining cases apart: the local hunter INSIDE that sphere (push not
 * applied) or outside it while clipping (sphere smaller than the inflated mesh). Joint record: 160 B, 0x53ab30 returns
 * +64 = world position, so the world matrix is +16..+79 (S: rows 0..2 give the joint's scale). */
static float sqrt_f(float x)
{
    if (x <= 0.0f) return 0.0f;
    float r = x > 1.0f ? x : 1.0f;
    for (int i = 0; i < 24; i++) r = 0.5f * (r + x / r);
    return r;
}

static void inflated_probe(void *self)
{
    static uint32_t s_n, s_tick;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if ((rec[0x1bb] & 3) != 2 || s_n >= 80 || ++s_tick % 10) return;
    void *root = *(void **)PLAYER_ROOT;
    uint8_t *pl = root ? *(uint8_t **)((uint8_t *)root + 0x58) : 0;
    uint8_t *idx = FIELD(uint8_t *, self, 0x498), *joints = FIELD(uint8_t *, self, 0x494);
    if (!pl || !FIELD(void *, pl, 0x498) || !FIELD(void *, pl, 0x494) || !idx || !joints || idx[201] == 255) return;
    const float *m = (const float *)(joints + 160u * idx[201] + 16);
    float h[4], s = sqrt_f(m[0] * m[0] + m[1] * m[1] + m[2] * m[2]);
    float s2 = sqrt_f(m[4] * m[4] + m[5] * m[5] + m[6] * m[6]);
    jointPos(pl, 0, h);
    float dx = h[0] - m[12], dy = h[1] - m[13], dz = h[2] - m[14];
    float d = sqrt_f(dx * dx + dy * dy + dz * dz), r = 110.0f * s;
    if (d > 2.0f * r + 300.0f) return;
    s_n++;
    logf("tzport: inflated probe: hunter %d from bone 201 (%s), sphere r %d (scale %d / %d %%), dy %d, motion %x "
         "mask %x", (int)d, d < r ? "INSIDE" : "outside", (int)r, (int)(s * 100.0f), (int)(s2 * 100.0f), (int)dy,
         curMotion(self), FIELD(uint16_t, rec, 0x3b4));
}

int em067_01_act_c(uint32_t *regs)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines;
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != TIGERSTRIPE_ZAMTRIOS_EM_ID) return 0;
    em067_01_shell016_tick(self);                 /* the 7/70 blast's end effect (em067_01_shell016.c) */
#ifdef TEST_HP_PCT
    {   /* test builds: start at TEST_HP_PCT % of max HP once (as Gogmazios' em089_act.c) */
        static void *s_hp_set;
        uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, rec, REC_HP), mx = FIELD(int32_t, rec, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, rec, REC_HP) = mx * TEST_HP_PCT / 100;
            logf("tzport: em067_01 test HP %d / %d", mx * TEST_HP_PCT / 100, mx);
        }
    }
#endif
    inflated_probe(self);
    if (s_lines >= MAX_LINES) return 0;
    if (!s_self) {
        s_self = self;
        s_act = s_mot = ~0u;
        s_lines++;
        logf("tzport: em067_01 %x first dispatch, variant %u, index %u", (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6));
    }
    if (self != s_self) return 0;                 /* other instances (TEST_SWAP quests): the first one only */
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    if (act != s_act) {
        /* mode rec+0x1bb (& 3 == 2: inflated) and the volume mask rec+0x3b4 that slot 170 -> 0xf79200 derives from it
         * (bit 0x8000 clear = bodydata record 1 on: the inflated sphere, bone 201 r100 x its scale; user 2026-10-26:
         * "we clip inside him in his big form") */
        uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
        s_lines++;
        logf("tzport: em067_01 action %u/%u (motion %x) area %u mode %x mask %x", act >> 8, act & 0xff, mot,
             FIELD(uint8_t, self, EN_AREA), rec[0x1bb], FIELD(uint16_t, rec, 0x3b4));
    } else if (mot != s_mot) {
        s_lines++;
        logf("tzport: em067_01 motion %x (action %u/%u)", mot, act >> 8, act & 0xff);
    }
    s_act = act;
    s_mot = mot;
    return 0;
}
