/* em067_01_shells.c: Tigerstripe Zamtrios' paralysis balls (notes/shells.md). 4U Tigerstripe fires uShell012
 * subtypes 40-43, which run the same code as Zamtrios' 8-11 with other data; GU's uEm067_00 posts Zamtrios' ball
 * (shell id 292, uShellEm067_sp_13) at three sites but skips each post for variant != 0, so Tigerstripe fired nothing
 * visible. Here GU posts its own request for variant 1 too: a mid hook just before each variant test sets the variant
 * byte (EN_ID + 5) to 0, and em067_01_post_c (em067_01_gaps.c, the 0x48c4f0 entry) sets it back to 1 at the post
 * itself. The code between is straight-line (C, notes/shells.md 5a). Tigerstripe's own shell data (4U hit records,
 * em092 effects) comes from its shell arc (manifest field 25), not from this file.
 * Multiplayer: GU's action handlers run on every machine and shells are local to each, so nothing here is gated on
 * the controlling machine. Mid hooks always return 0 (a nonzero return would leave GU's function). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_VARIANT (EN_ID + 5)

void *g_tz_ball_owner;              /* the monster whose variant byte is 0 until its ball post (em067_01_gaps.c) */

static void hide_variant(void *self, const char *site)
{
    if (!self || FIELD(uint16_t, self, EN_ID) != TIGERSTRIPE_ZAMTRIOS_EM_ID || FIELD(uint8_t, self, EN_VARIANT) != 1)
        return;
    FIELD(uint8_t, self, EN_VARIANT) = 0;
    g_tz_ball_owner = self;
    static uint32_t s_n;
    if (++s_n <= 20) logf("tzport: em067_01 ball post at %s (GU's variant-0 path)", site);
}

/* 0xf72700 (movw r1, #0xb5f5; ldrb r1, [r4, r1]): mode-0 / mode-2 balls (4U 0x74e288 subtypes 40 / 41), r4 = monster */
int em067_01_ball_c(uint32_t *regs)
{
    hide_variant((void *)regs[R4], "f72700");
    return 0;
}

/* 0xf735c0 (movw r0, #0xb5f5; mov r1, r4): the large ball (4U subtype 43), r4 = monster */
int em067_01_ball43_c(uint32_t *regs)
{
    hide_variant((void *)regs[R4], "f735c0");
    return 0;
}

/* 0xf73870 (ldr r0, [sp, #0xc]; ldrb r0, [r0]): the twin balls (4U subtype 42); [sp + 0xc] = &variant, the caller's
 * sp being just above the 8 registers the trampoline saved */
int em067_01_ball42_c(uint32_t *regs)
{
    uint8_t *pv = FIELD(uint8_t *, regs, 32 + 0xc);
    hide_variant(pv ? pv - EN_VARIANT : 0, "f73870");
    return 0;
}
