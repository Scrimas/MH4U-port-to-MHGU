/* dala_psl.c: test log of the motion-synced effects (PSL posts, 4U LMT event group 2 / cMhMotionEffect) of both
 * halves: which record each motion posts, and when GU stops it. C = read in code, S = strong, G = guess.
 * 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * Why (test 2026-10-21): a purple fire burned on forever where the head died. The death motion 0x33d posts MEF record
 * 253 (em024_012 element 1, joint 6 + (0, 600, 500), frames 35-72, MEF slot mode 1). 4U kills a slot-mode-1 effect
 * when its event range ends (cMhMotionEffect 0x39170c / 0x391a18 / 0x390b40, C). GU stops a PSL-posted effect on the
 * range end only when its PEL record has end mode 1 (+0x3a; 0x329dbc), else only on a motion change or wrap (C), and
 * our dead head holds 0x33d on its last frame (dala_react.c): no change ever came. Fix in the data
 * (build_dalamadur_arc.py pel_slot_end: slot mode 1 -> end mode 1); this file only logs it.
 *
 * GU (C): uFestaEnemy slot 75 (vt+0x12c) = 0x70028(this, list 1, PSL entry data, slot, request): the PSL post (uCharacter
 * 0x53b7e0 calls it with the request; S that this is the PSL player's only route: Capcom's own override 0xe022a4 wraps
 * it); kind data+0x44[slot] (4 = PEL u list 1), id = u16 data+4[slot]; returns the uMHProofEffect or 0 (no post in
 * 12/255). The PSL player (0x31d218 / 0x31d530) then sets effect+0x194 = &controller+0xc4[slot] (0x31d1d4) and pulses
 * bit 2 there on the run's falling edge, 4 on a motion change, 8 on a wrap; the effect (0x329668) latches them into
 * +0x198 / +0x199 / +0x19a. Effect: +0x30 u8 state (5 ended, 6 stopped; 3 = ended in end mode 1, run as state 0: S),
 * +0xc6 = record +0x36 (transform),
 * +0xca = record +0x3a (end mode), unit state +0xc & 7 (1 / 2 = alive, dala_efx_alive).
 * Logs (local, read-only; MP: every machine posts its own effects): "psl post" per post during a death (11 / 12 / 14)
 * and per end-mode-1 post otherwise (capped), "psl fx" when a tracked effect's state / latches change or it ends. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

typedef void *(*psl_post_t)(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req);
#define pslPostBase FN(psl_post_t, 0x70028)

#define TRACK 12
static struct { void *eff, *owner; uint16_t id, slot; uint32_t sig; } s_fx[TRACK];
static uint32_t s_n_post, s_n_fx;

static int is_tail(void *self) { return (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff); }
static int dead(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat == 11 || cat == 12 || cat == 14;
}
static int alive(void *eff) { return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2; }
static uint32_t fx_sig(void *eff)
{
    uint8_t *e = (uint8_t *)eff;
    return 0x80000000u | (uint32_t)alive(eff) << 24 | (uint32_t)e[0x30] << 16 | (uint32_t)e[0x198] << 8 |
           (uint32_t)e[0x199] << 4 | e[0x19a];
}

void *dala_psl_post(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req)
{
    void *eff = pslPostBase(self, list, data, slot, req);
    if (!data || slot >= 32) return eff;
    uint32_t id = FIELD(uint16_t, data, 4 + 2 * slot), kind = FIELD(uint32_t, data, 0x44 + 4 * slot);
    uint32_t end = eff ? ((uint8_t *)eff)[0xca] : 0xff, d = dead(self);
    if (!d && (end != 1 || s_n_post >= 60)) return eff;
    if (s_n_post++ < 160)
        logf("dalaport: psl post %s %u/%u motion %x frame %d slot %u id %u kind %u -> eff %x end mode %u transform %u",
             is_tail(self) ? "tail" : "head", FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM),
             curMotion(self), (int)motionFrame(self), slot, id, kind, (uint32_t)eff, end,
             eff ? ((uint8_t *)eff)[0xc6] : 0xff);
    if (!eff) return eff;
    int k = 0;
    while (k < TRACK && s_fx[k].eff && alive(s_fx[k].eff)) k++;
    if (k == TRACK) return eff;
    s_fx[k].eff = eff; s_fx[k].owner = self; s_fx[k].id = (uint16_t)id; s_fx[k].slot = (uint16_t)slot;
    s_fx[k].sig = fx_sig(eff);
    return eff;
}

/* GU slot 119, both halves: the tracked effects this half posted */
void dala_psl_watch(void *self)
{
    for (int k = 0; k < TRACK; k++) {
        if (!s_fx[k].eff || s_fx[k].owner != self) continue;
        void *eff = s_fx[k].eff;
        uint32_t sig = fx_sig(eff), was = s_fx[k].sig;
        if (sig == was) continue;
        s_fx[k].sig = sig;
        if (++s_n_fx <= 160)
            logf("dalaport: psl fx %s id %u slot %u eff %x: alive %u state %u -> %u, stop latches range end %u motion "
                 "%u wrap %u, end mode %u | %u/%u motion %x frame %d", is_tail(self) ? "tail" : "head", s_fx[k].id,
                 s_fx[k].slot, (uint32_t)eff, sig >> 24 & 1, was >> 16 & 0xff, sig >> 16 & 0xff, sig >> 8 & 0xf,
                 sig >> 4 & 0xf, sig & 0xf, ((uint8_t *)eff)[0xca], FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM), curMotion(self), (int)motionFrame(self));
        if (!(sig >> 24 & 1)) s_fx[k].eff = 0;        /* ended: forget it (the unit may be freed and reused) */
    }
}
