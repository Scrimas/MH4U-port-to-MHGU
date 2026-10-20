/* em067_01_gaps.c: Tigerstripe Zamtrios (GU Zamtrios variant 1, run by GU's uEm067_00) where GU's variant-1 code
 * differs from 4U's Tigerstripe code (notes/phase1-variant-map.md; porting plan Phase 3). Logs start "tzport:".
 *
 * Tremor of action 2/7: 4U 0x749670 posts uShell005 subtype 13 (scale 1.3) for Zamtrios at 0x7496b4 and skips it for
 * Tigerstripe; GU's counterpart posts request 0x122 at 0xf6e5c8 for both variants, while its other tremor sites test
 * variant == 0 (0xf71ef0, 0xf6c598, 0xf73e6c, 0xf77ef8). Hook 0x48c4f0 = the shell request post (904 callers): the
 * call returning to 0xf6e5cc with a variant-1 Zamtrios in r4 (the monster, also the request's owner) returns at once;
 * that caller reloads r0 right after, so the result is unused. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define TREMOR_2_7_RET 0xf6e5ccu    /* return address of the 2/7 tremor post (bl 0x48c4f0 at 0xf6e5c8) */

int em067_01_post_c(uint32_t *regs)
{
    if (regs[LR] - MAIN_BASE != TREMOR_2_7_RET) return 0;
    if (FIELD(uint16_t, (void *)regs[R4], EN_ID) != TIGERSTRIPE_ZAMTRIOS_EM_ID) return 0;
    static uint32_t s_n;
    if (++s_n <= 10) logf("tzport: em067_01 2/7 tremor not posted (4U Tigerstripe posts none)");
    regs[R0] = 0;
    return 1;
}
