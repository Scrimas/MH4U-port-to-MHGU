/* em005_01_spit.c: the 4U gas puff of Black Gravios' spit 7/13 7/14 7/50 (4U uEm038 0x802768, GU d2bd2c; notes/plan.md
 * "Test of 0.4.4" / "Test of 0.4.5"). C = confirmed in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Frame 150 of step 1: 4U posts request 8 = (50, 8) = em040_020 on the monster (0x809ae0(this, 8, 0): joint 255,
 * element mask 1, effect only, C), always for r2 == 1 (7/50) and with state bit 2 but not 4 for the others
 * (0x802988..0x8029e0, C). GU posts nothing there. Until 0.4.4 this hook posted GU's gas shell 3 (a hit 4U does not
 * have); now our PEL list-2 record 4042 (em040_020, k 0) on the monster, no hit.
 * The spit's shell keeps GU's look: GU gives it its own effect (shell02 entries 1 2 5 6 -> 130 / 131), so 4U's
 * uShell016 effects (em024_009 + em040_100) stay out (0.4.5 posted them: "a huge blue explosion at the head", user
 * test 2026-11-02). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define WK_STATE    0x24        /* u8 state bits [4U work+0x28] */
#define FX_PUFF     4042u       /* PEL list 2: em040_020 k 0 (request 8) */

typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)      /* [0x941dbc] */
typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
#define EFX_REQ_SIZE 0x100

/* GU 0xd2c734 (r4 = this, r5 = the action's r2): d2bd2c step 1, every frame, before the motion-end check */
int em005_01_spit_c(uint32_t *regs)
{
    static uint32_t s_lines;
    void *self = (void *)regs[R4];
    if (!self || FIELD(uint16_t, self, EN_ID) != BLACK_GRAVIOS_EM_ID || !atFrame(self, 150.0f)) return 0;
    uint32_t st = FIELD(uint8_t, FIELD(uint8_t *, self, EN_WORK), WK_STATE);
    if (regs[R5] != 1 && (!(st & 2) || (st & 4))) return 0;
    uint32_t buf[EFX_REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    efx_req_ctor(req);                          /* on the monster (record joint -1), as em089_efx_post */
    void *e = efx_post_u(self, 2, FX_PUFF, req);
    efx_req_dtor(req);
    if (++s_lines <= 20) logf("bgport: spit puff em040_020 -> %x (4U 0x8029e0, state %x)", (uint32_t)e, st);
    return 0;
}
