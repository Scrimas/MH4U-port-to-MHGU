/* The head's look system (goal E): dala_look.c. 4U uEm024 / em110 W+0x79be..0x7a12 = GU uEnemy +0x7520..0x7570. */
#pragma once
#include <stdint.h>

/* per frame, head and tail (the tail returns at once): installs the 4U look joint list into the shared dtbparts
 * object (once per loaded resource), registers this head's look joints for GU's joint callback (once per instance),
 * and logs the look state (small budget). Run it after GU's look 0xa79f8 (slot 130 does: 0xae830 > 0xae218). */
void dala_look_install(void *self);
/* 4U 0x76ec80 (set 0) / 0x76fce8 (set 1) look set-up, written every frame by the 7.x handlers */
void dala_look_setup(void *self, uint32_t set);
/* 4U 0x93e974(this, NULL, 0) = GU 0xc2884(this, NULL, 0): look point = target slot 0 */
void dala_look_point(void *self);
/* 4U W+0x79d0 = mode (3 = step tables) = GU this+0x7548 */
void dala_look_mode(void *self, uint32_t mode);
