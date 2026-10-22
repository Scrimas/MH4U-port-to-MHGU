/* dala_efx.h: Dalamadur's code-posted effects (dala_efx.c) on GU's proof-effect system, keyed by the 4U posts.
 * Independent of Gogmazios' em089_efx.c (same GU calls, own copy). */
#pragma once
#include <stdint.h>

/* PEL u list-2 ids of the 4U code posts. Both PELs (em090_00u = em024 family, em090_01u = em110 family) hold the
 * same ids; the tail halves post their head's PEL (manifest field 17 is shared, C: monsters/dalamadur/tools/em091_0x_manifest.json).
 * 4U code posts never select an MEF record: they name an EFL directly (flat table 0xef895c[group][element], or the
 * uEffect002 id table 0xfd0b94 {u8 group, u8 element}), so each id below needs an `extra` record in
 * build_dalamadur_arc.py effects(); the record data is listed in dala_efx.c. Until a record exists the post returns
 * 0 (GU 0x3267d0 finds no id, 0x40978 frees its effect and returns 0, C) and is logged. */
enum {
    DALA_EFX_BODY_J200 = 2800,       /* uEffect002 28, head joint 200 (cm000_002, element 2, scale 8) */
    DALA_EFX_BODY_J5 = 2801,         /* uEffect002 28, head joint 5 */
    DALA_EFX_BODY_J142 = 2802,       /* uEffect002 28, tail joint 142 */
    DALA_EFX_METEOR = 2900,          /* uShell029 attached effect: em024_003 / em110_003, all elements, on the shell */
    DALA_EFX_TAIL_SMOKE = 2910,      /* tail 10/114: qe013_002 joint 157, colour of em 83 */
    DALA_EFX_TAIL_SMOKE_SHAH = 2911, /* same, colour of em 111 */
    /* the attack shells (dala_shell*.c; flat table 0xef895c group 35 = em024 list, 81 = em110 list, C) */
    DALA_EFX_FIREBALL = 2920,        /* uShell001 24 / 25 / 88 / 89: em024_000 / em110_000 on the shell, scale 3.5 */
    DALA_EFX_FIREBALL_WALL = 2921,   /* its wall hit, kinds 24 / 88: em024_001 / em110_001 element 1, scale 1.0 */
    DALA_EFX_FIREBALL_WALL_L = 2922, /* wall hit, kinds 25 / 89: the same at scale 1.2 */
    DALA_EFX_FIREBALL_GROUND = 2923, /* ground hit, kinds 25 / 89: em024_001 / em110_001 element 0, scale 1.2 */
    DALA_EFX_BLAST = 2930,           /* uShell003 113 / 126 / 160 / 162: em024_005 / em110_005, scale 1.2 */
    DALA_EFX_BURN = 2931,            /* uShell003 112 / 159: em024_001 / em110_001 element 0, scale 1.5 */
    DALA_EFX_BEAM = 2940,            /* uShell016 21 / 39: em024_009 / em110_009 along the capsule */
    DALA_EFX_SCALE = 2950,           /* uShell038 meteor scale: em024_006 / em110_006 on the shell (placed once) */
    DALA_EFX_SCALE_END = 2951,       /* its end: em024_007 / em110_007 at the point */
    DALA_EFX_HEAT_J4 = 2960,         /* heat aura zone 0: em024_016 / em110_016 mask 8, joint 4 (0, -500, 1100) */
    DALA_EFX_HEAT_J101 = 2961,       /* zone 1: the same file, mask 16, joint 101 (500, 1300, -700) */
    /* Shah's crimson zones (dala_shah.c; em090_01u only, em090_00u holds placeholders never posted): uEffect003
     * subtypes 4 / 5 / 6 = flat table group 81 elements 23 / 26 / 27 = em110_200 / _203 / _204, mask 1, world
     * position 0 (placed once), scale 1; the expiry post 0x775f2c = the same files, mask 2 */
    DALA_EFX_SHAH_ZONE0 = 2970,      /* zone 0 while armed: em110_200 element 0 */
    DALA_EFX_SHAH_ZONE1 = 2971,      /* zone 1: em110_203 element 0 */
    DALA_EFX_SHAH_ZONE2 = 2972,      /* zone 2: em110_204 element 0 */
    DALA_EFX_SHAH_END0 = 2973,       /* zone 0 expiry: em110_200 element 1 */
    DALA_EFX_SHAH_END1 = 2974,       /* zone 1 expiry: em110_203 element 1 */
    DALA_EFX_SHAH_END2 = 2975,       /* zone 2 expiry: em110_204 element 1 */
};

/* post PEL record `id` on this monster (attach model = the owner, joint / offset / scale / element mask from the
 * record). Returns the uMHProofEffect or 0 (no record, no PEL, dead). */
void *dala_efx_post(void *self, uint32_t id);
/* same, attached to another unit (a shell: target = its attach model vt+0x130, request flags 3, its position and
 * area); the unit must outlive the effect (dala_meteor.c's deferred kill) */
void *dala_efx_post_on(void *owner, uint32_t id, void *unit);
/* same, at a world position (request flags 1 + position, as em089_efx.c's ground splashes; the record's joint is
 * -1): blasts and impacts. area = the 4U post's, unused (the request keeps the owner's, the same area) */
void *dala_efx_post_at(void *owner, uint32_t id, const float *pos, uint32_t area);
/* same at a world position with a rotation (u16 pitch / yaw), GU's moving-beam request (em089_efx.c's beams); move
 * it every frame with dala_efx_place (GU live setters 0x32a45c position / 0x8a7dc4 rotation). The record must place
 * once (follow false): with the following tail Gogmazios' laser was not drawn (efl4u2gu.py pel_follows) */
void *dala_efx_post_beam(void *owner, uint32_t id, const float *pos, uint32_t pitch, uint32_t yaw);
void dala_efx_place(void *eff, const float *pos, uint32_t pitch, uint32_t yaw);
void dala_efx_stop(void *eff);      /* GU 0x32a400(eff, 0): stop emitting, the effect ends on its own */
void dala_efx_kill(void *eff);      /* GU 0x32a400(eff, 1): immediate */
int dala_efx_alive(void *eff);      /* unit state 1 / 2 */

/* 4U slot 39 spawn (head 0x76d77c: joints 200 / 5; tail 0x89ffe0: joint 142): uEffect002 28 on the body */
void dala_efx_body_spawn(void *self, uint32_t tail);
/* the same arrows shown (posted) or hidden (killed) */
void dala_efx_body_walk(void *self, uint32_t tail, uint32_t walkable);
/* per frame, both halves (GU slot 119): the arrows by 4U slot 77's rule (actions, head part 0 broken) */
void dala_efx_arrows_frame(void *self);
/* 4U tail slot 47 0x8a265c, action 10/114 with hit direction 7: 0xc088d8 qe013_002 on joint 157 + 0xc48378 colour */
void dala_efx_tail_smoke(void *self);
/* 4U 0xc0819c (head 1.3-1.11 / 2.x at the attack frame): radial blur filter at joint 5, local player's area only;
 * not ported (logged), as Gogmazios' roar blur */
void dala_efx_radial_blur(void *self);
/* 4U uShell029 init 0xc7cedc: the meteor's attached effect (kinds 2..7) */
void *dala_efx_meteor(void *owner, void *shell, uint32_t kind);
/* 4U uMhEftCtrl004 0x326a6c: the heat aura of the head's heat-zone bits (8 / 16 = 4U work+0x54), per frame */
void dala_efx_heat(void *self, uint32_t bits);
/* per frame from the tail's GU slot 119 (em091_state_frame): the tail smoke's end (see dala_efx.c) */
void dala_efx_frame(void *self);
