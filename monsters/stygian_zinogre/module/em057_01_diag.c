/* em057_01_diag.c: Stygian Zinogre diagnostics (logs, prefix "szport:").
 *
 * Hook 0xf03620 = uEm057_00 vtable slot 125, the action dispatcher (= 4U slot 44, every frame). It also runs 4U's
 * aura controller (em057_01_efx_frame, em057_01_efx.c), 4U vt77's paw-slam ground hit (em057_01_slam_fx_frame,
 * em057_01_mv_d.c) and orb events (em057_01_orb_event_frame, em057_01_posts.c) and
 * Stygian's own actions: em057_01_moves_run (em057_01_moves.c) decides on every call whether GU's dispatch is
 * skipped (return 1). Logs: for the first Zinogre
 * variant 1 (ID 0x139) it meets, log each new action (category / number, enemy +0x73e0 / +0x73e1) and each new
 * motion (curMotion, bank << 8 | index), with the mode byte rec+0x1bb (4U W+0x1c9). A test then shows which actions
 * the AI table reaches (the ones GU lacks fall to the dispatcher's default case), and that the motions variant 1
 * asks for play from our 4U em048 motion lists (notes/phase1-assets.md 2). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "em057_01.h"

enum { R0 };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */
#define EN_AREA    0x1054           /* u8 current area */
#define MAX_LINES  3000u            /* a few minutes of fight (AI tests) */

int em057_01_moves_run(void *self);   /* em057_01_moves.c: 1 = our handler ran, GU's dispatch is skipped */

int em057_01_act_c(uint32_t *regs)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines;
    void *self = (void *)regs[R0];
    if (FIELD(uint16_t, self, EN_ID) != STYGIAN_ZINOGRE_EM_ID) return 0;
    em057_01_efx_frame(self);
    em057_01_slam_fx_frame(self);
    em057_01_orb_event_frame(self);
    em057_01_vt77_frame(self);
#ifdef TEST_HP_PCT
    {   /* test builds: start at TEST_HP_PCT % of max HP once (as Gogmazios' em089_act.c) */
        static void *s_hp_set;
        uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, rec, REC_HP), mx = FIELD(int32_t, rec, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, rec, REC_HP) = mx * TEST_HP_PCT / 100;
            logf("szport: em057_01 test HP %d / %d", mx * TEST_HP_PCT / 100, mx);
        }
    }
#endif
    if (s_lines >= MAX_LINES) return em057_01_moves_run(self);
    if (!s_self) {
        s_self = self;
        s_act = s_mot = ~0u;
        s_lines++;
        logf("szport: em057_01 %x first dispatch, variant %u, index %u", (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6));
    }
    if (self != s_self) return em057_01_moves_run(self);   /* logs: the first instance only (TEST_SWAP quests) */
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if (act != s_act) {
        int32_t hp = FIELD(int32_t, rec, REC_HP), mx = FIELD(int32_t, rec, REC_HP + 4);
        s_lines++;
        logf("szport: em057_01 action %u/%u (motion %x) area %u mode %x hp %d%% charge %d%s", act >> 8, act & 0xff,
             mot, FIELD(uint8_t, self, EN_AREA), rec[0x1bb], mx > 0 ? hp * 100 / mx : 0,
             (int32_t)FIELD(int16_t, WORK(self), 0), isCharged(self) ? " charged" : "");
    } else if (mot != s_mot) {
        s_lines++;
        logf("szport: em057_01 motion %x (action %u/%u) mode %x", mot, act >> 8, act & 0xff, rec[0x1bb]);
    }
    s_act = act;
    s_mot = mot;
    return em057_01_moves_run(self);
}
