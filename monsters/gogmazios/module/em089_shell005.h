/* em089_shell005.h: the MH4U quake / tremor shell uShell005 posted by the ground impact 0x954e5c (em089_shell005.c). */
#pragma once
#include <stdint.h>

/* the shell part of 4U 0x954e5c(this, kind, _, off, scale, height): nothing when the monster is more than `height`
 * above the ground; else a uShell005 at (pos.x, ground y, pos.z) + yaw-rotated off * size factor * scale, with the
 * subtype of `kind` (1 -> 1, 2 -> 2, 3 -> 11, 4 -> 12, 5 -> 26, 6 -> 27, 7 -> 28; only 1, the 2/35 one, has hit data
 * here) and hit-volume scale = size factor * scale. em089 2/35: em089_shell005_ground_impact(self, 1, {0, 0, 800},
 * 0.8, 900). Returns the shell or 0. */
void *em089_shell005_ground_impact(void *self, uint32_t kind, const float *off, float scale, float height);
