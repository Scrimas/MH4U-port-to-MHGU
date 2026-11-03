/* em005_01_beam.c: Black Gravios' own branch of 4U's beam handler (4U uEm038 0x8050e0, its em 41 sites 805320 and
 * 805920; notes/plan.md "4U behaviour of em 41"). C = confirmed in code, S = strong, G = guess. 4U = MH4U v1.1,
 * GU = MHGU 1.4.
 *
 * GU's beam handler d2e0b4 is 4U's 0x8050e0 (C: motion 7 / 89-90, motionCheck(3, 34, 134), the rank table byte 5, the
 * beam volley at frame 105 = 4U's two at 100 / 105, the step counters rec+0x1a2 / 0x1a3 = 4U W+0x145 / 0x146) without
 * 4U's em-41 branch. Both games join every frame of step 1 at the motion-end check (4U 805918, GU d2e3ec), and 4U's
 * branch runs there, so the hook at d2e3ec runs it for variant 1, with 4U's frames (the same timing in both games, C):
 *  - 4U 805300: frame 10, state bit 2 set and bit 4 clear: effect request 8 (0x809ae0(this, 8, 0)); Gravios posts none
 *    there. GU posts 4U's ungated request 8 of the other handlers as its message id 10 | state bit 0 (d2d88c = 4U
 *    0x803dc8: the same attack at 350; S).
 *  - 4U 805998: 0x808410(this, 1, 120.0): frame 120 the heat burst effect (request 6 = (50, 6) = em040_013, mask
 *    1 << 0, 1 << 8 with state bit 4; the forced path r1 == 1, so no state bit needed) and sound 216, frame 140 its
 *    attack attackEx(0, 26, or 57 with state bit 4, 4096). Gravios skips all of it here (4U em 40: 805930 -> 8059f0, C).
 *    GU posts no effect for request 6 anywhere: its own bursts (d2ba30 7/12 7/17 heated, d2bd2c 7/50 forced at frame
 *    100) arm attack 26 / 57 alone, and its message at d2ba30 (ids 3 / 7 / 8 / 9 by state bit 0 and 0x8172c) is that
 *    move's request 8 = (50, 8) = em040_020, the gas (4U 0x802498 posts it unconditionally, the burst only when
 *    heated, C). So the burst is attack 26 / 57 alone at frame 140, as GU's own; until test 2026-11-01 frame 120 posted
 *    message 3 (the gas: user "explosion and sleep gas at the same time"). The attack indexes are 4U's in every GU
 *    copy (d2bc88 d2d9e8 d2e030, C). In 4U every beam of a series (7/73 -> 7/89 -> 7/89 .., 0x805a90) ends this way.
 *  - not ported: 4U's sound 216 at frame 120 (GU's class posts no sounds: they are motion data, G).
 *  - 0.4.7 (maintainer test 2026-11-03: died to "a wrong hitbox" in the 7/73 -> 7/89 series; log: attack 26 at 4:40.114,
 *    the cart tally 9 ms later): the burst's 4U look is posted at frame 120 as PEL list-2 records 4045 / 4046
 *    (em040_013 k 0 / k 8; em040_013 has no element 8, so the heated request shows nothing in 4U either, S), not GU's
 *    gas message 3 of 0.4.1.
 * State byte: GU work+0x24 = 4U [this+0x8c88]+0x28 (C: GU d2bca4 / 4U 0x808440 test the same bits 2 and 4).
 * The spit 7/13 7/14 7/50 (4U 0x802768, GU d2bd2c) is in em005_01_spit.c. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define WK_STATE    0x24        /* u8 state bits [4U work+0x28]: 2 and 4 select the heat burst (meaning G) */
#define EN_EFX_OWNER 0xcacc     /* u32 the message's +4 (GU d2bbb4 / d2d93c) */
#define MSG_MGR     0x1892550   /* its manager, *(void **) (GOT 0x1838da0) */
#define MSG_VT      0x175585c   /* the message vtable symbol (+8 = the vtable; GOT 0x183cd64) */
#define MSG_VEC     0x191e850   /* u32[3] copied to +0x10..+0x18 (GOT 0x1838b4c) */

typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)      /* [0x941dbc] */
typedef void *(*alloc_t)(uint32_t size, uint32_t align);
#define msgAlloc    FN(alloc_t, 0x3fc428)       /* new(48, 16) as d2bb9c */
typedef void (*post_t)(void *mgr, void *msg, uint32_t a, uint32_t b);
#define msgPost     FN(post_t, 0x48c4f0)

typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)     /* PEL u list 2 (em005_01_spit.c) */
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)

static int is_black_gravios(const void *self)
{
    return self && FIELD(uint16_t, self, EN_ID) == BLACK_GRAVIOS_EM_ID;
}

/* GU d2bb88..d2bc2c / d2d910..d2d9a0: the effect request message {vtable, owner, id, this, vector, 0, u16 0, 0xffff} */
static void post_request(void *self, uint32_t id, uint32_t site)
{
    static uint32_t s_lines;
    void *mgr = *(void **)MAIN(MSG_MGR);
    const uint32_t *v = (const uint32_t *)MAIN(MSG_VEC);
    uint8_t *m;
    if (!mgr || !(m = msgAlloc(48, 16))) return;
    FIELD(uint32_t, m, 0x00) = MAIN(MSG_VT) + 8;
    FIELD(uint32_t, m, 0x04) = FIELD(uint32_t, self, EN_EFX_OWNER);
    FIELD(uint32_t, m, 0x08) = id;
    FIELD(void *, m, 0x0c) = self;
    FIELD(uint32_t, m, 0x10) = v[0];
    FIELD(uint32_t, m, 0x14) = v[1];
    FIELD(uint32_t, m, 0x18) = v[2];
    FIELD(uint32_t, m, 0x1c) = 0;
    FIELD(uint16_t, m, 0x20) = 0;
    FIELD(uint32_t, m, 0x24) = 0xffff;
    msgPost(mgr, m, 0, 0);
    if (++s_lines <= 20) logf("bgport: beam request %u (4U %x)", id, site);
}

/* GU 0xd2e3ec (r4 = this): d2e0b4 step 1, every frame, before the motion-end check */
int em005_01_beam_c(uint32_t *regs)
{
    static uint32_t s_lines;
    void *self = (void *)regs[R4];
    uint32_t st;
    if (!is_black_gravios(self)) return 0;
    st = FIELD(uint8_t, FIELD(uint8_t *, self, EN_WORK), WK_STATE);
    if (atFrame(self, 10.0f) && (st & 2) && !(st & 4))
        post_request(self, 10 | (st & 1), 0x80536c);
    if (atFrame(self, 120.0f)) {          /* 4U 0x808428: request 6 = em040_013 on the monster (records 4045 / 4046) */
        uint32_t buf[0x100 / 4 + 4];
        void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
        efx_req_ctor(req);
        void *e = efx_post_u(self, 2, (st & 4) ? 4046u : 4045u, req);
        efx_req_dtor(req);
        if (++s_lines <= 20) logf("bgport: beam heat burst look em040_013 k %u -> %x", (st & 4) ? 8u : 0u, (uint32_t)e);
    }
    if (atFrame(self, 140.0f)) {
        uint32_t idx = (st & 4) ? 57 : 26;
        attackEx(self, 0, idx, 4096);
        if (++s_lines <= 20) logf("bgport: beam heat burst attack %u (state %x, 4U 0x8084cc)", idx, st);
    }
    return 0;
}
