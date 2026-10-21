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

int em067_01_act_c(uint32_t *regs)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines;
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != TIGERSTRIPE_ZAMTRIOS_EM_ID) return 0;
    em067_01_shell016_tick(self);                 /* the 7/70 blast's end effect (em067_01_shell016.c) */
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
        s_lines++;
        logf("tzport: em067_01 action %u/%u (motion %x) area %u", act >> 8, act & 0xff, mot,
             FIELD(uint8_t, self, EN_AREA));
    } else if (mot != s_mot) {
        s_lines++;
        logf("tzport: em067_01 motion %x (action %u/%u)", mot, act >> 8, act & 0xff);
    }
    s_act = act;
    s_mot = mot;
    return 0;
}
