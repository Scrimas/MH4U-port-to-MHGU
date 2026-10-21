/* Code shared by both Dalamadur halves (em090.h). */
#include "game.h"
#include "util.h"
#include "em090.h"

void dala_fields_init(void *self)
{
    for (uint32_t o = SIZE_uFestaEnemy + 4; o < DALA_SIZE; o++) FIELD(uint8_t, self, o) = 0;
    FIELD(uint8_t, self, F_CTL) = 0xff;
}

/* GU slot 119 (per frame from 0xade84, after the update's flag clear 0xa5198): the halves never push each other or
 * other monsters apart; both stay on their common spawn point as in 4U (em090.h REC_NO_ENEMY_PUSH) */
void dala_state_frame(void *self)
{
    FIELD(uint8_t, FIELD(uint8_t *, self, EN_RECORD), REC_NO_ENEMY_PUSH) = 1;
}

/* One line whenever this machine's control of the half changes (GU writers: spawn 0xb167c, takeover 0xb16e0,
 * message 0xb161c). Both halves must always name the same owner (plan.md, multiplayer rules). */
void dala_ctl_log(void *self, const char *half)
{
    uint8_t ctl = FIELD(uint8_t, self, EN_CONTROLLED), owner = FIELD(uint8_t, self, EN_OWNER);
    if (ctl == FIELD(uint8_t, self, F_CTL) && owner == FIELD(uint8_t, self, F_OWNER)) return;
    FIELD(uint8_t, self, F_CTL) = ctl;
    FIELD(uint8_t, self, F_OWNER) = owner;
    logf("dalaport: ctl %s %x variant %u controlled %u owner %u frame %u", half, (uint32_t)self,
         FIELD(uint8_t, self, EN_VARIANT), ctl, owner, FIELD(uint32_t, self, F_FRAMES));
}

/* the local hunter (main+0x2126F48 chain, as Gogmazios' stage_cannon.c), 0 while its joints are not set up */
static void *local_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* goal D1 test: where the body is (object, joints 0 / 200 = body root, 107 / 154 = 4U map icon joints of head /
 * tail) against the local hunter, every 300 frames, 6 times */
static void place_log(void *self)
{
    static const uint32_t joints[] = {0, 200, 107, 154};
    const float *o = (const float *)(FIELD(uint8_t *, self, EN_RECORD) + REC_POS_X);
    float p[4], h[4] = {0, 0, 0, 0};
    void *pl = local_hunter();
    if (pl) jointPos(pl, 0, h);
    logf("dalaport: place %x variant %u obj %d %d %d hunter %d %d %d", (uint32_t)self, FIELD(uint8_t, self, EN_VARIANT),
         (int)o[0], (int)o[1], (int)o[2], (int)h[0], (int)h[1], (int)h[2]);
    for (uint32_t k = 0; k < sizeof joints / sizeof *joints; k++) {
        jointPos(self, joints[k], p);
        logf("dalaport: place %x joint %u at %d %d %d", (uint32_t)self, joints[k], (int)p[0], (int)p[1], (int)p[2]);
    }
}

/* Goal D1 action: the idle motion, restarted when it ends or something else replaced it */
void dala_idle(void *self, uint32_t motion)
{
    if (curMotion(self) != motion || isMotionEnd(self)) setMotionLoop(self, motion, 0.0f, 0.0f);
    uint32_t f = ++FIELD(uint32_t, self, F_FRAMES);
    if (f % 300 == 30 && f < 1800) place_log(self);
}
