/* em089_efx.h: Gogmazios effect posting on GU's proof-effect system + the 4U slot-75 joint-200 port. */
#pragma once
#include <stdint.h>

/* Post the PEL u list-2 record `id` (tools/efl4u2gu.py: PEL record id = the 4U MEF id; joint, offset, scale,
 * element mask come from the record) on this monster. Returns the uMHProofEffect (or 0: dead, unknown id, no PEL).
 * Keep the handle only for looping effects and stop them with em089_efx_stop before dropping it. */
void *em089_efx_post(void *self, uint32_t id);
/* same, at a world position (request flag 1 + position, GU monster pattern 0xd3f5a0) instead of the record joint */
void *em089_efx_post_at(void *self, uint32_t id, const float *pos);
/* same, attached to another unit's attach model (unit vt+0x130, e.g. a shell: req+0xd0 + flag 2); the unit must stay
 * alive until the effect is dead (the effect reads its target every frame), see em089_shell.c's deferred kill */
void *em089_efx_post_on(void *owner, uint32_t id, void *unit);
/* stop a posted effect (GU 0x32a400(eff, 0), as Kushala / every GU monster does for its looping effects) */
void em089_efx_stop(void *eff);
/* immediate stop (GU 0x32a400(eff, 1), the proof effect's own "target lost" path 0x43274) */
void em089_efx_kill(void *eff);
/* unit state 1 / 2 (the check GU shells do on their effect handles) */
int em089_efx_alive(void *eff);

/* PEL ids of the code posts (tools/efl4u2gu.py extra_records) */
enum {
    EM089_EFX_BLOB_DRIP = 3000,   /* uShell050 kinds 0, 1, 6-9: em089_003 on the shell */
    EM089_EFX_BLOB_SHOT = 3001,   /* uShell050 kinds 2-5: em089_016 on the shell */
    EM089_EFX_IMPACT = 3100,      /* 0x954e5c kind 1: qe006_000 */
    EM089_EFX_TAIL_BREAK = 3300,  /* slot 64 0x8c67c0: qe013_002 on joint 143 */
    EM089_EFX_S051 = 5100,        /* + uShell051 subtype: ground shell effect (world position) */
};

/* hook for em089_shell016.c (em089_shell016_fx): the 4U uShell016 uEffect002 posts (first call = init, second call
 * for the same shell = the end effect at life <= 10); the effect's end follows the 4U shell rule (owner motion change /
 * life) and em089_efx_shell016_end. em089_efx_init() installs the hook (also done lazily every frame). */
void em089_efx_shell016_fx(void *shell, void *owner, uint32_t subtype, uint32_t efx_id);
void em089_efx_shell016_end(void *shell);
/* every frame after the shell placed its capsule: its effects follow the capsule start / direction (4U 0x1b5ba0) */
void em089_efx_shell016_move(void *shell);
void em089_efx_init(void);
/* uEffect002 57 (phase-2 aura): register once at the 4U post (1/25 / 1/31 roar); ca = work+0xca, e4 = work+0xe4 */
void em089_efx_aura(void *self, const uint8_t *ca, const uint8_t *e4);
/* 4U 0xc0819c roar radial blur (player's area only): PEL 3200 on joint 3 */
void em089_efx_roar_blur(void *self);
/* any PEL record with optional world position (req+0x1c bit 0), rotation override in degrees and scale multiplier */
void *em089_efx_post_ex(void *self, uint32_t id, const float *pos, const float *rot_deg, const float *scale);
/* 4U 0x954e5c ground impact (2/35: kind 1, offset {0, 0, 800}, scale 0.8, height 900) */
void em089_efx_ground_impact(void *self, uint32_t kind, const float *off, float scale, float height);
/* 4U slot 64 tail first break: PEL 3300 on joint 143 (the record holds offset / scale) */
void em089_efx_tail_break(void *self);

/* Battlequarters stage effects (for stage code; posted on the last em089 that ran a frame, 0 if none):
 * 4U scheduler event CreateKowareEft(index) of an "Effect" scheduler with KowareEftGroup = group (0..2),
 * KowareEftPos = pos (world), KowareEftAreaNo = area (255 = any). Indices: 2 qe016_003, 11 m19a03_000,
 * 12..17 m19a03_001 / 002 / 003 / 004 / 008 / 009. m19a03d-e01 / e02 / e03 (breakables k01 / k02 / k03, groups 0 /
 * 1 / 2): 11 at frames 10 and 20, 2 at 201 and 226; e04: 12 at 3935 and 13445; e05 / e06: 2 at 201 / 226 (group 1);
 * e08: 16 at frame 2. KowareEftColor / JimenType are not representable (GU PEL has no tint / material input). */
void *em089_efx_stage_kowareeft(uint32_t index, uint32_t group, const float *pos, uint32_t area);
/* any of the 14 arena EFLs m19a03_NNN (n 0..13, all elements) at a world position */
void *em089_efx_stage_efl(uint32_t n, const float *pos);
/* same, attached to a unit (follows it; the unit must outlive the effect: em089_efx_stop, then wait until
 * !em089_efx_alive before the unit dies, as em089_shell.c does). 4U uShell022 subtype 9 (quest-fired arena projectile,
 * per frame 0xc74b78): m19a03_006 at launch, m19a03_012 trail (looping, handle +0x288), m19a03_007 at impact. */
void *em089_efx_stage_efl_on(uint32_t n, void *unit);

/* 4U uEm089 slot 75 (0x8c3ca0) = GU object slot 168 (vt+0x2a0, per-frame joint-override hook after the motion
 * update, called from the enemy update 0xae1f4; Rajang 0xde5f80 and em0xx 0xd53f64 use it the same way with the
 * joint setter 0x72438). Register: s_vt[2 + 168] = (uint32_t)&em089_slot75. */
void em089_slot75(void *self);
/* the 4U gate W+0x434 (1 = active, 0 / >= 2 = off; written in 4U by the status/net code 0x834964 / 0x91d29c, GU
 * counterpart not identified): default 0, i.e. the joint-200 animation stays off until someone maps the state. */
void em089_slot75_state(void *self, uint32_t state);
/* review agent: drop all handles / slots keyed to this monster (call from its deleting destructor, em089.c) */
void em089_efx_forget(void *self);
